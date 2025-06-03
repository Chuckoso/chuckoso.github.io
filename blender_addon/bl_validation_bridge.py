# -*- coding: utf-8 -*-

bl_info = {
    "name": "WAUR Blender Validator",
    "author": "Chucky",
    "version": (2, 4, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Validation",
    "description": "Validate models for WAUR pipeline using Maya Standalone backend",
    "category": "3D View"
}

import bpy
import os
import subprocess
import tempfile
import json

# Importamos la función de exportación centralizada
from bl_fbx_io_maya import export_fbx_maya

# Property Group para un item de validación
class ValidationResultItem(bpy.types.PropertyGroup):
    passed: bpy.props.BoolProperty()
    check: bpy.props.StringProperty()
    message: bpy.props.StringProperty()

class ValidateModelOperator(bpy.types.Operator):
    bl_idname = "object.validate_model"
    bl_label = "Run Validation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not context.selected_objects:
            self.report({'WARNING'}, "No objects selected for validation.")
            return {'CANCELLED'}

        save_temps = context.scene.save_temps
        blend_dir = os.path.dirname(bpy.data.filepath)
        if not blend_dir:
            blend_dir = tempfile.gettempdir()

        if save_temps:
            temp_fbx_path = os.path.join(blend_dir, "temp_validation_model.fbx")
            temp_json_path = os.path.join(blend_dir, "validation_results.json")
        else:
            temp_fbx_path = os.path.join(tempfile.gettempdir(), "temp_validation_model.fbx")
            temp_json_path = os.path.join(tempfile.gettempdir(), "validation_results.json")

        # Export selected objects to FBX using the shared function
        export_fbx_maya(filepath=temp_fbx_path, use_selection=True)

        # Call Maya Standalone validation
        standalone_hub_path = os.path.expanduser("~/Documents/maya/2018/scripts/ma_standalone_hub.py")
        validate_script_path = os.path.expanduser("~/Documents/maya/2018/scripts/ma_validate_fbx.py")
        mayapy_path = r"C:\Program Files\Autodesk\Maya2018\bin\mayapy.exe"

        try:
            subprocess.check_call([
                mayapy_path,
                standalone_hub_path,
                "--script", validate_script_path,
                "--args", temp_fbx_path, temp_json_path
            ])
        except subprocess.CalledProcessError as e:
            self.report({'ERROR'}, "Validation failed: {}".format(e))
            return {'CANCELLED'}

        # Load validation results
        if not os.path.exists(temp_json_path):
            self.report({'ERROR'}, "Validation results not found.")
            return {'CANCELLED'}

        # Limpiar resultados anteriores
        context.scene.validation_results.clear()
        context.scene.issues_found = False
        context.scene.validation_ran = True

        with open(temp_json_path, "r") as f:
            results = json.load(f)

        for check, info in results.items():
            item = context.scene.validation_results.add()
            item.passed = info.get("passed", False)
            item.check = check
            item.message = info.get("message", "")
            if not item.passed:
                context.scene.issues_found = True

        # Clean temp files if not saving
        if not save_temps:
            try:
                os.remove(temp_fbx_path)
                os.remove(temp_json_path)
            except:
                pass

        return {'FINISHED'}


class ClearValidationResultsOperator(bpy.types.Operator):
    bl_idname = "object.clear_validation_results"
    bl_label = "Clear Results"

    def execute(self, context):
        context.scene.validation_results.clear()
        context.scene.issues_found = False
        context.scene.validation_ran = False
        return {'FINISHED'}


class ValidationResultsPanel(bpy.types.Panel):
    bl_label = "Validation"
    bl_idname = "OBJECT_PT_validation_results"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Validation"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator("object.validate_model", icon="PLAY")
        row.operator("object.clear_validation_results", icon="X")

        layout.prop(context.scene, "save_temps")

        layout.separator()

        box = layout.box()

        if not context.scene.validation_ran:
            row = box.row()
            row.label(text="🛈 Validation not run yet.", icon='INFO')
        elif context.scene.issues_found:
            row = box.row()
            row.alert = True
            row.label(text="❌ Issues found!", icon='ERROR')
        else:
            row = box.row()
            row.label(text="✅ All checks passed!", icon='CHECKMARK')

        layout.separator()

        if context.scene.validation_results:
            for item in context.scene.validation_results:
                row = layout.row()
                icon = 'CHECKMARK' if item.passed else 'CANCEL'
                row.label(text="[{}] {}".format(item.check.replace("_", " ").title(), item.message), icon=icon)


def register():
    bpy.utils.register_class(ValidationResultItem)
    bpy.utils.register_class(ValidateModelOperator)
    bpy.utils.register_class(ClearValidationResultsOperator)
    bpy.utils.register_class(ValidationResultsPanel)

    bpy.types.Scene.validation_results = bpy.props.CollectionProperty(type=ValidationResultItem)
    bpy.types.Scene.issues_found = bpy.props.BoolProperty(
        name="Issues Found",
        description="Whether any issues were found during validation",
        default=False
    )
    bpy.types.Scene.validation_ran = bpy.props.BoolProperty(
        name="Validation Ran",
        description="Whether validation has been executed",
        default=False
    )
    bpy.types.Scene.save_temps = bpy.props.BoolProperty(
        name="Save Temporary Files",
        description="Keep exported FBX and validation JSON next to .blend file",
        default=False
    )


def unregister():
    bpy.utils.unregister_class(ValidationResultItem)
    bpy.utils.unregister_class(ValidateModelOperator)
    bpy.utils.unregister_class(ClearValidationResultsOperator)
    bpy.utils.unregister_class(ValidationResultsPanel)

    del bpy.types.Scene.validation_results
    del bpy.types.Scene.issues_found
    del bpy.types.Scene.validation_ran
    del bpy.types.Scene.save_temps


if __name__ == "__main__":
    register()
