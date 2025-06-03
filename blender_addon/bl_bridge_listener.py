import bpy
import socket
import threading
import json
import os

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 6000
BUFFER_SIZE = 4096

_is_listening = False

def handle_command(command):
    parts = command.strip().split("|")
    cmd = parts[0].upper()

    if cmd == "PING":
        return "PONG|Blender bridge ready"

    elif cmd == "IMPORT" and len(parts) > 1:
        fbx_path = parts[1].replace("\\", "/")
        json_path = fbx_path.replace("_toBlender.fbx", "_toBlender_meta.json")

        if not os.path.exists(fbx_path) or not os.path.exists(json_path):
            return "ERR|Missing FBX or JSON file."

        with open(json_path, "r") as f:
            meta = json.load(f)

        full_path = meta.get("object", "")
        object_short_name = full_path.split("|")[-1]

        filename = os.path.basename(json_path)
        session_base = filename.replace("_toBlender_meta.json", "")
        scene_name = "_".join(session_base.split("_")[:-1])

        # Importar FBX
        try:
            bpy.ops.import_scene.fbx_maya(filepath=fbx_path)
        except Exception as e:
            return f"ERR|FBX import failed: {e}"

        imported_obj = None
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                obj.name = object_short_name
                imported_obj = obj
                break

        if imported_obj:
            imported_obj["maya_scene"] = scene_name
            imported_obj["maya_object"] = object_short_name
            print(f"[Bridge] Imported '{object_short_name}' with session '{scene_name}'.")
            return f"OK|Imported {object_short_name}"

        return "ERR|Imported object not found"

    return "ERR|Command not recognized"

def start_listener():
    global _is_listening
    if _is_listening:
        print("[Bridge] Listener already running")
        return
    _is_listening = True

    def run():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((BRIDGE_HOST, BRIDGE_PORT))
        server.listen(1)
        print(f"[Bridge] Listening on {BRIDGE_HOST}:{BRIDGE_PORT}")

        while _is_listening:
            conn, addr = server.accept()
            print("[Bridge] Connection from", addr)
            data = conn.recv(BUFFER_SIZE)
            if data:
                command = data.decode("utf-8").strip()
                print("[Bridge] Received command:", command)

                def handle_and_reply():
                    result = handle_command(command)
                    conn.sendall(result.encode("utf-8"))
                    conn.close()

                bpy.app.timers.register(handle_and_reply, first_interval=0.01)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

def stop_listener():
    global _is_listening
    _is_listening = False
    print("[Bridge] Listener stopped")
