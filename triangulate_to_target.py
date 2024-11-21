bl_info = {
    "name": "Triangulate to Target",
    "author": "MattGPT",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Object Menu",
    "description": "Optimizes quad face triangulation based on distance to a target surface",
    "warning": "",
    "doc_url": "",
    "category": "Object",
}

import bpy
import bmesh
import blf
from bpy.props import FloatProperty, PointerProperty, StringProperty
from bpy.types import Operator, PropertyGroup, Panel
from mathutils import Vector
from mathutils.bvhtree import BVHTree

class CustomModifierProperties(PropertyGroup):
    target_object: PointerProperty(
        type=bpy.types.Object,
        name="Target Object",
        description="Object to measure distance to"
    )
    max_distance: FloatProperty(
        name="Max Distance",
        description="Maximum distance to search for target surface",
        default=1.0,
        min=0.0,
        soft_max=10.0
    )
    planarity_threshold: FloatProperty(
        name="Planarity Threshold",
        description="If the difference between diagonal options is below this value, keep the face as a quad",
        default=0.001,
        min=0.0,
        soft_max=1.0,
        precision=4
    )

class TriangulateDebugProps(PropertyGroup):
    debug_line1: StringProperty(default="")
    debug_line2: StringProperty(default="")
    debug_line3: StringProperty(default="")
    debug_line4: StringProperty(default="")

class MESH_OT_custom_modifier(Operator):
    bl_idname = "mesh.triangulate_to_target"
    bl_label = "Triangulate to Target"
    bl_options = {'REGISTER', 'UNDO'}
    
    def __init__(self):
        self.bm = None
        self.quad_faces = []
        self.current_face_index = 0
        self._handle = None
        self._timer = None
    
    def modal(self, context, event):
        if event.type == 'ESC':
            self.finish(context)
            return {'CANCELLED'}
            
        if event.type == 'TIMER' or event.type == 'MOUSEMOVE':
            if self.current_face_index >= len(self.quad_faces):
                self.finish(context)
                return {'FINISHED'}
            
            face = self.quad_faces[self.current_face_index]
            self.process_face(face, context)
            self.current_face_index += 1
            
            # Force a redraw to ensure UI updates
            context.area.tag_redraw()
        
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        if context.active_object is None or context.active_object.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object")
            return {'CANCELLED'}
        
        props = context.active_object.custom_modifier_props
        
        if not props.target_object:
            self.report({'ERROR'}, "No target object selected")
            return {'CANCELLED'}
        
        # Initialize BMesh based on current mode
        obj = context.active_object
        is_edit_mode = obj.mode == 'EDIT'
        
        if is_edit_mode:
            self.bm = bmesh.from_edit_mesh(obj.data)
            # In edit mode, only process selected quad faces
            self.quad_faces = [f for f in self.bm.faces if len(f.verts) == 4 and f.select]
        else:
            self.bm = bmesh.new()
            self.bm.from_mesh(obj.data)
            # In object mode, process all quad faces
            self.quad_faces = [f for f in self.bm.faces if len(f.verts) == 4]
        
        if not self.quad_faces:
            self.report({'WARNING'}, "No quad faces found" + (" (in selection)" if is_edit_mode else ""))
            if not is_edit_mode:
                self.bm.free()
            return {'CANCELLED'}
        
        # Add the debug drawing handler
        args = (self, context)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
        
        # Add timer for continuous updates
        self._timer = context.window_manager.event_timer_add(0.001, window=context.window)
        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def finish(self, context):
        # Finish up
        obj = context.active_object
        is_edit_mode = obj.mode == 'EDIT'
        
        if is_edit_mode:
            bmesh.update_edit_mesh(obj.data)
        else:
            self.bm.to_mesh(obj.data)
            self.bm.free()
            obj.data.update()
        
        # Clean up
        if self._handle:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
            
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        
        # Clear debug info
        update_debug_info(context, ["", "", "", ""])

    def process_face(self, face, context):
        """Process a single face, measuring diagonals and updating visualization"""
        verts = list(face.verts)
        props = context.active_object.custom_modifier_props
        max_distance = props.max_distance if props.max_distance > 0 else float('inf')
        
        # Calculate centers of both diagonal options
        diag_02_center = (verts[0].co + verts[2].co) / 2
        diag_13_center = (verts[1].co + verts[3].co) / 2
        
        # Calculate distance between diagonal centers
        center_distance = (diag_02_center - diag_13_center).length
        
        # If the diagonals are close enough, keep as quad
        if center_distance <= props.planarity_threshold:
            debug_lines = [
                f"Face: {self.current_face_index + 1}/{len(self.quad_faces)}",
                f"Diagonal center distance: {center_distance:.4f}",
                f"Below threshold: {props.planarity_threshold:.4f}",
                f"Keeping as quad"
            ]
            update_debug_info(context, debug_lines)
            context.area.tag_redraw()
            return
        
        # Otherwise, proceed with measuring distances to target
        dist_02 = measure_diagonal_distance(face, verts[0], verts[2], props.target_object, max_distance)
        
        debug_lines = [
            f"Face: {self.current_face_index + 1}/{len(self.quad_faces)}",
            f"Testing diagonal 0-2",
            f"Distance: {dist_02:.4f}",
            f"Center dist: {center_distance:.4f}"
        ]
        
        update_debug_info(context, debug_lines)
        context.area.tag_redraw()
        
        # Then measure diagonal 1-3
        dist_13 = measure_diagonal_distance(face, verts[1], verts[3], props.target_object, max_distance)
        
        # Update debug info with results
        selected_diagonal = "0-2" if dist_02 <= dist_13 else "1-3"
        debug_lines = [
            f"Face: {self.current_face_index + 1}/{len(self.quad_faces)}",
            f"Center distance: {center_distance:.4f}",
            f"Above threshold: {props.planarity_threshold:.4f}",
            f"Selected: {selected_diagonal}"
        ]
        
        # Split the face using the better diagonal
        if dist_02 <= dist_13:
            edge = bmesh.ops.connect_verts(self.bm, verts=[verts[0], verts[2]])
        else:
            edge = bmesh.ops.connect_verts(self.bm, verts=[verts[1], verts[3]])
        
        update_debug_info(context, debug_lines)
        
        # Ensure proper mesh updates
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        
        # Update the mesh to show the new edge
        if context.active_object.mode == 'EDIT':
            bmesh.update_edit_mesh(context.active_object.data)
        else:
            self.bm.to_mesh(context.active_object.data)
            context.active_object.data.update()
        
        context.area.tag_redraw()
        
def draw_callback_px(self, context):
    """Draw debug information in the 3D viewport"""
    if not context.scene.triangulate_debug:
        return
        
    # Draw text debug info
    font_id = 0
    font_size = 32
    
    # Position in bottom-left corner with padding
    x = 20
    y = 60  # Add some padding from the bottom
    
    # Draw debug info
    blf.size(font_id, font_size)
    blf.color(font_id, 1, 1, 1, 1)
    
    debug = context.scene.triangulate_debug
    # Draw lines from bottom to top
    lines = [debug.debug_line1, debug.debug_line2, debug.debug_line3, debug.debug_line4]
    for i, line in enumerate(reversed(lines)):  # Reverse the lines so they build up from bottom
        if line:
            blf.position(font_id, x, y + i*40, 0)
            blf.draw(font_id, line)

class VIEW3D_PT_triangulate_to_target(Panel):
    bl_label = "Triangulate to Target"
    bl_idname = "VIEW3D_PT_triangulate_to_target"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    
    def draw(self, context):
        layout = self.layout
        props = context.active_object.custom_modifier_props if context.active_object else None
        
        if props:
            layout.prop(props, "target_object")
            layout.prop(props, "max_distance")
            layout.prop(props, "planarity_threshold")
            layout.operator(MESH_OT_custom_modifier.bl_idname)
        else:
            layout.label(text="No active object")

def menu_func(self, context):
    self.layout.operator(MESH_OT_custom_modifier.bl_idname)

def register():
    bpy.utils.register_class(CustomModifierProperties)
    bpy.utils.register_class(TriangulateDebugProps)
    bpy.utils.register_class(MESH_OT_custom_modifier)
    bpy.utils.register_class(VIEW3D_PT_triangulate_to_target)
    bpy.types.Scene.triangulate_debug = bpy.props.PointerProperty(type=TriangulateDebugProps)
    bpy.types.Object.custom_modifier_props = bpy.props.PointerProperty(type=CustomModifierProperties)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    del bpy.types.Object.custom_modifier_props
    bpy.utils.unregister_class(VIEW3D_PT_triangulate_to_target)
    bpy.utils.unregister_class(MESH_OT_custom_modifier)
    del bpy.types.Scene.triangulate_debug
    bpy.utils.unregister_class(TriangulateDebugProps)
    bpy.utils.unregister_class(CustomModifierProperties)

if __name__ == "__main__":
    register()

def get_closest_point_on_target(point, target_obj, face_normal, max_distance):
    """Find the closest point on the target object's surface"""
    # Convert point to target object's local space
    local_point = target_obj.matrix_world.inverted() @ point
    
    # Create BVHTree for target object
    bm_target = bmesh.new()
    bm_target.from_mesh(target_obj.data)
    bvh = BVHTree.FromBMesh(bm_target)
    
    # Try both normal directions
    location1, normal1, index1, distance1 = bvh.find_nearest(local_point)
    
    # Try ray casting in both directions
    ray_location1, ray_normal1, ray_index1, ray_dist1 = bvh.ray_cast(local_point, face_normal)
    ray_location2, ray_normal2, ray_index2, ray_dist2 = bvh.ray_cast(local_point, -face_normal)
    
    bm_target.free()
    
    # Collect all valid results
    results = []
    if location1 is not None:
        world_loc1 = target_obj.matrix_world @ location1
        results.append((world_loc1, distance1))
    if ray_location1 is not None:
        world_loc2 = target_obj.matrix_world @ ray_location1
        results.append((world_loc2, ray_dist1))
    if ray_location2 is not None:
        world_loc3 = target_obj.matrix_world @ ray_location2
        results.append((world_loc3, ray_dist2))
    
    if not results:
        return None
    
    # Find the closest point among all valid results
    closest_location, min_distance = min(results, key=lambda x: x[1])
    
    if min_distance > max_distance and max_distance > 0:
        return None
        
    return closest_location

def measure_diagonal_distance(face, vert1, vert2, target_obj, max_distance):
    """
    Measure the distance from a potential diagonal to the target surface.
    Uses closest point on target surface from the diagonal center point.
    """
    if not target_obj:
        return float('inf')
    
    # Get all vertices of the quad face
    verts = list(face.verts)
    
    # Calculate center point of the diagonal
    diagonal_center = (vert1.co + vert2.co) / 2
    
    # Get the source object (the object being modified)
    source_obj = bpy.context.active_object
    
    # Convert diagonal center to world space using SOURCE object's matrix
    diagonal_center_world = source_obj.matrix_world @ diagonal_center
    
    # Create BVHTree for target object
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target_eval = target_obj.evaluated_get(depsgraph)
    
    # Create BVHTree from target mesh
    bvh = BVHTree.FromObject(target_eval, depsgraph)
    
    # Find closest point on target surface
    closest_point, normal, index, distance = bvh.find_nearest(diagonal_center_world)
    
    if closest_point is None:
        return float('inf')
    
    # Update debug info with more precise information
    debug_lines = [
        f"World center: ({diagonal_center_world.x:.3f}, {diagonal_center_world.y:.3f}, {diagonal_center_world.z:.3f})",
        f"Closest point: ({closest_point.x:.3f}, {closest_point.y:.3f}, {closest_point.z:.3f})",
        f"Distance: {distance:.3f}"
    ]
    update_debug_info(bpy.context, debug_lines)
    
    return distance

def update_debug_info(context, info_lines):
    """Update debug information in a safe way"""
    debug = context.scene.triangulate_debug
    for i, line in enumerate(info_lines[:4]):  # Limit to 4 lines
        setattr(debug, f"debug_line{i+1}", str(line))
