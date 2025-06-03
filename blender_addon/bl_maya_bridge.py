bl_info = {
    "name": "BL Maya Bridge",
    "author": "Chucky",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Bridge",
    "description": "Bridge between Blender and Maya",
    "category": "Import-Export",
}

import bpy
import socket
import os

BRIDGE_HOST = "127.0.0.1"
MAYA_PORT = 6001  # Maya escucha en 6001
BLENDER_PORT = 6000  # Blender escucha en 6000
TEMP_DIR = "C:/Telltale/temp"

bpy.types.Scene.bridge_connected = bpy.props.BoolProperty(
    name="Connected to Maya",
    description="Indicates if Blender is connected to Maya",
    default=False
)

class BRIDGE_OT_ConnectToMaya(bpy.types.Operator):
    bl_idname = "bridge.connect_to_maya"
    bl_label = "Connect to Maya"

    def execute(self, context):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((BRIDGE_HOST, MAYA_PORT))  # Conectar a Maya en 6001
            sock.sendall(b"PING|hello_from_blender")
            response = sock.recv(4096).decode("utf-8")
            sock.close()
            context.scene.bridge_connected = True
            self.report({'INFO'}, f"Connected to Maya: {response}")
            return {'FINISHED'}
        except Exception as e:
            context.scene.bridge_connected = False
            self.report({'ERROR'}, f"Connection to Maya failed: {e}")
            return {'CANCELLED'}

class BRIDGE_OT_SendToMaya(bpy.types.Operator):
    bl_idname = "bridge.send_to_maya"
    bl_label = "Send Model to Maya"

    def execute(self, context):
        selected = context.selected_objects
        if not selected:
            self.report({'WARNING'}, "No object selected.")
            return {'CANCELLED'}

        obj = selected[0]

        scene_name = obj.get("maya_scene", "unsaved")
        object_name = obj.get("maya_object", "unknown")

        if scene_name == "unsaved" or object_name == "unknown":
            self.report({'ERROR'}, "Object has no session data.")
            return {'CANCELLED'}

        filename = f"{scene_name}_{object_name}_fromBlender.fbx"
        path = os.path.join(TEMP_DIR, filename)

        try:
            bpy.ops.export_scene.fbx_maya(filepath=path)
            self.report({'INFO'}, f"Exported FBX: {path}")
        except Exception as e:
            self.report({'ERROR'}, f"FBX export failed: {e}")
            return {'CANCELLED'}

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((BRIDGE_HOST, MAYA_PORT))  # Conectar a Maya en 6001
            # Enviar escena|objeto para que Maya pueda encontrar el archivo correcto
            command = f"REPLACE|{scene_name}|{object_name}"
            sock.sendall(command.encode("utf-8"))
            sock.close()
            self.report({'INFO'}, f"Sent to Maya: {scene_name}|{object_name}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to connect to Maya on port {MAYA_PORT}: {e}")
            return {'CANCELLED'}

class BRIDGE_PT_MainPanel(bpy.types.Panel):
    bl_label = "Maya Bridge"
    bl_idname = "BRIDGE_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bridge'

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row()
        row.operator("bridge.connect_to_maya", icon="LINKED")
        status = context.scene.bridge_connected
        row = col.row()
        row.label(text="Connected" if status else "Not Connected",
                  icon='CHECKMARK' if status else 'CANCEL')
        col.separator()
        col.operator("bridge.send_to_maya", icon="EXPORT")

classes = (
    BRIDGE_PT_MainPanel,
    BRIDGE_OT_ConnectToMaya,
    BRIDGE_OT_SendToMaya,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bridge_connected = bpy.props.BoolProperty(
        name="Connected to Maya", default=False)
    try:
        import bl_bridge_listener
        bl_bridge_listener.start_listener()
        print("[Bridge] Blender listener started on port 6000.")
    except:
        print("[Bridge] Listener not available.")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.bridge_connected

if __name__ == "__main__":
    register()