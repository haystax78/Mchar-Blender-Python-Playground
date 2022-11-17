#Addon that allow duplication and movement of active mesh object from inside Sculpt mode.
#Find in the sculpt menu. Works best when bound to a hotkey (I use shift+D).

bl_info = {
    "name": "Sculpt Mode Duplicate",
    "author": "mchar",
    "version": (0, 2, 2),
    "blender": (3, 1, 0),
    "location": "View3D > Sculpt > Duplicate Sculpt Object",
    "description": "Duplicates Active Sculpt Mesh",
    "warning": "",
    "doc_url": "",
    "category": "Sculpt",
}

import bpy

def find_mesh():
    for o in bpy.data.objects:
        if o.type == "MESH":
            print(f"found...{o.name}")
            bpy.data.objects[o.name].select_set(True); 
            return ("Selected first mesh object found")

def main(context):
    #if x-sym is disabled, new object will be repositioned along with it's origin
    bpy.ops.sculpt.sculptmode_toggle()
    if len(bpy.context.selected_objects) == 0:
        find_mesh()    
    if bpy.context.object.use_mesh_mirror_x == False:
        bpy.ops.object.duplicate_move('INVOKE_DEFAULT')
        bpy.ops.sculpt.sculptmode_toggle()
    #if x-sym is enabled, new object origin will remain in position and only the mesh data will be translated
    elif bpy.context.object.use_mesh_mirror_x == True:
        bpy.ops.object.duplicate()
        bpy.ops.sculpt.sculptmode_toggle()
        bpy.ops.transform.translate('INVOKE_DEFAULT')
        
class SculptModeDuplicate(bpy.types.Operator):
    """Duplicates the Active Mesh in Sculpt Mode"""
    bl_idname = "sculpt.sculpt_mode_duplicate"
    bl_label = "Sculpt Mode Duplicate [mchar]"
    bl_options = {'REGISTER'}

    def execute(self, context):
        main(context)
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(SculptModeDuplicate.bl_idname)

def register():
    bpy.utils.register_class(SculptModeDuplicate)
    bpy.types.VIEW3D_MT_sculpt.append(menu_func)

def unregister():
    bpy.utils.unregister_class(SculptModeDuplicate)
    bpy.types.VIEW3D_MT_sculpt.remove(menu_func)
