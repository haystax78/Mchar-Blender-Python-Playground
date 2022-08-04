#Addon that allow duplication and movement of active mesh object from inside Sculpt mode.
#Find in the sculpt menu. Works best when bound to a hotkey.

bl_info = {
    "name": "Sculpt Mode Duplicate",
    "author": "mchar",
    "version": (0, 2),
    "blender": (3, 10, 0),
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
    bpy.ops.sculpt.sculptmode_toggle()
    if len(bpy.context.selected_objects) == 0:
        find_mesh()
    bpy.ops.object.duplicate_move('INVOKE_DEFAULT')
    bpy.ops.sculpt.sculptmode_toggle()


class SculptModeDuplicate(bpy.types.Operator):
    """Duplicates the Active Mesh in Sculpt Mode"""
    bl_idname = "sculpt.sculpt_mode_duplicate"
    bl_label = "Sculpt Mode Duplicate [mchar]"

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



if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.object.sculpt_mode_duplicate()