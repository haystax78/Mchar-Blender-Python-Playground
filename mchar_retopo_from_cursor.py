#Addon to quickly setup a retopo mesh and material.

bl_info = {
    "name": "Retopo from Cursor",
    "author": "mchar",
    "version": (0, 1),
    "blender": (3, 1, 0),
    "description": "Adds a retopo starter mesh at the 3d cursor",
    "location": "Spacebar Search -> Retopo at Cursor",
    "category": "Add Mesh",
}

import bpy
import bpy.props


def new_material(id):

    mat = bpy.data.materials.get(id)

    if mat is None:
        mat = bpy.data.materials.new(name=id)

    mat.use_nodes = True

    if mat.node_tree:
        mat.node_tree.links.clear()
        mat.node_tree.nodes.clear()

    return mat


def new_shader(id, r, g, b):

    mat = new_material(id)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    output = nodes.new(type='ShaderNodeOutputMaterial')

    shader = nodes.new(type='ShaderNodeBsdfDiffuse')
    nodes["Diffuse BSDF"].inputs[0].default_value = (r, g, b, 1)

    links.new(shader.outputs[0], output.inputs[0])

    return mat


def draw_object():

    mat = new_shader("RetopoShader1", 1, 1, 1)
    bpy.ops.mesh.primitive_plane_add(size=2, enter_editmode=False, align='CURSOR', location=(bpy.context.scene.cursor.location), scale=(1, 1, 1))
    bpy.context.active_object.data.materials.append(mat)
    


#Set preferred material and display options for retopo
def setup_vis():
    bpy.context.space_data.shading.show_backface_culling = True
    bpy.context.scene.tool_settings.use_snap = True
    bpy.context.scene.tool_settings.snap_elements = {'FACE'}
    bpy.context.scene.tool_settings.use_snap_backface_culling = True
    bpy.context.scene.tool_settings.use_snap_project = True
    bpy.context.scene.tool_settings.use_snap_translate = True
    bpy.context.scene.tool_settings.use_snap_scale = True
    bpy.context.object.display.show_shadows = False
    bpy.context.object.show_in_front = True



def main(context):
    draw_object()
    setup_vis()
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.editmode_toggle()



class retopo_from_cursor(bpy.types.Operator):
    """Start a new retopo mesh from the 3dCursor location"""
    bl_idname = "mesh.retopo_from_cursor"
    bl_label = "Retopo from Cursor [mchar]"
    bl_options = {'REGISTER', 'UNDO'}

#REDO PANEL PROPERTIES    
    my_scaler: bpy.props.FloatProperty(
        name="Starting Scale",
        description="Scale of the Starting Quad",
        min=0,
        max=100,
        default=1
    )
    my_color: bpy.props.FloatVectorProperty(
        name="Retopo Color",
        subtype='COLOR_GAMMA',
        size=4,
        min=0,
        max=1,
        default=(0.035, 0.25, 0.8, 0.47),
        description="Viewport Display Color of the Retopo Mesh"
    )
    wire_bool: bpy.props.BoolProperty(
        name="Show Wire",
        description="Show Wireframe in Object Mode",
        default=True
    )
    add_wrap: bpy.props.BoolProperty(
        name="Sub-D & Shrinkwrap",
        description="Add Sub-d and Shrinkwrap Modifiers with the selected object as the wrap target",
        default=False
    )



    def execute(self, context):
        wrap_target=(bpy.context.active_object)
        main(context)
        bpy.ops.transform.resize(value=(1 * self.my_scaler, 1 * self.my_scaler, 1 * self.my_scaler))
        bpy.context.object.active_material.diffuse_color = (self.my_color)
        bpy.context.object.show_wire = (self.wire_bool)
        if (self.add_wrap):
            bpy.ops.object.subdivision_set(level=1)
            bpy.ops.object.modifier_add(type='SHRINKWRAP')
            bpy.context.object.modifiers["Shrinkwrap"].target = (wrap_target)
            bpy.context.object.modifiers["Subdivision"].show_only_control_edges = False
        
        return {'FINISHED'}




def register():
    bpy.utils.register_class(retopo_from_cursor)

    
def unregister():
    bpy.utils.unregister_class(retopo_from_cursor)




