# -*- coding: utf-8 -*-
"""
FBX Import/Export tool for Blender to match Maya settings.
Designed for WAUR 3D Pipeline (Wolf Among Us Remaster).
Author: Chucky
"""

bl_info = {
    "name": "Maya FBX Import/Export",
    "author": "Chucky",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "category": "Import-Export",
    "description": "Import/Export FBX files with Maya-compatible settings",
}

import bpy
from bpy.types import Operator, Panel
from bpy.props import BoolProperty, StringProperty

# ---------- IMPORT OPERATOR ----------

class IMPORT_OT_fbx_maya(bpy.types.Operator):
    bl_idname = "import_scene.fbx_maya"
    bl_label = "Import FBX (from Maya)"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
        bpy.ops.import_scene.fbx(
            filepath=self.filepath,
            global_scale=100.0,
            use_custom_normals=True,
            use_prepost_rot=True,
            use_anim=False,
            use_manual_orientation=True,
            axis_forward='X',
            axis_up='Y'
        )

        for obj in bpy.context.selected_objects:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# ---------- WARNING POPUP OPERATOR ----------

class FBX_OT_warning_popup(bpy.types.Operator):
    bl_idname = "fbx.warning_popup"
    bl_label = "Export Error"
    bl_options = {'INTERNAL'}

    message: StringProperty(default="")

    def draw(self, context):
        layout = self.layout
        layout.label(text=self.message, icon='ERROR')

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)

# ---------- EXPORT OPERATOR ----------

class EXPORT_OT_fbx_maya(bpy.types.Operator):
    bl_idname = "export_scene.fbx_maya"
    bl_label = "Export FBX (to Maya)"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    use_mesh: BoolProperty(name="Mesh", default=True)
    use_armature: BoolProperty(name="Armature", default=False)
    use_empty: BoolProperty(name="Empty", default=True)
    use_camera: BoolProperty(name="Camera", default=False)
    use_light: BoolProperty(name="Light", default=False)

    def invoke(self, context, event):
        selected_objects = context.selected_objects
        export_objects = []

        for obj in selected_objects:
            if (
                (self.use_mesh and obj.type == 'MESH') or
                (self.use_empty and obj.type == 'EMPTY') or
                (self.use_camera and obj.type == 'CAMERA') or
                (self.use_light and obj.type == 'LIGHT')
            ):
                export_objects.append(obj)

        if not export_objects:
            bpy.ops.fbx.warning_popup('INVOKE_DEFAULT', message="Select something to export first.")
            return {'CANCELLED'}

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        bpy.ops.export_scene.fbx(
            filepath=self.filepath,
            use_selection=True,
            global_scale=0.01,
            apply_unit_scale=True,
            use_space_transform=True,
            apply_scale_options='FBX_SCALE_ALL',
            bake_space_transform=True,
            axis_forward='X',
            axis_up='Y'
        )
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.label(text="Include Object Types:")
        layout.prop(self, "use_mesh")

        row = layout.row()
        row.enabled = False
        row.prop(self, "use_armature")
        row.label(text="(Unsupported)", icon='ERROR')

        layout.prop(self, "use_empty")
        layout.prop(self, "use_camera")
        layout.prop(self, "use_light")

# ---------- UI PANEL ----------

class VIEW3D_PT_fbx_maya_panel(Panel):
    bl_label = "FBX: Maya Workflow"
    bl_idname = "VIEW3D_PT_fbx_maya_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FBX <-> Maya"

    def draw(self, context):
        layout = self.layout
        layout.operator("import_scene.fbx_maya", icon="IMPORT")
        layout.operator("export_scene.fbx_maya", icon="EXPORT")
		
# ---------- UTILITY FUNCTIONS ----------

def export_fbx_maya(filepath, use_selection=True):
    """
    Export selected objects to FBX with Maya-compatible settings.

    Args:
        filepath (str): Destination path for the exported FBX.
        use_selection (bool): If True, export only selected objects. Otherwise, export all.
    """
    import bpy

    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=use_selection,
        global_scale=0.01,
        apply_unit_scale=True,
        use_space_transform=True,
        apply_scale_options='FBX_SCALE_ALL',
        bake_space_transform=True,
        axis_forward='X',
        axis_up='Y'
    )

# ---------- REGISTER ----------

classes = (
    IMPORT_OT_fbx_maya,
    EXPORT_OT_fbx_maya,
    FBX_OT_warning_popup,
    VIEW3D_PT_fbx_maya_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
