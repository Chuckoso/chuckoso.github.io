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

        print(f"[Bridge] FBX path: {fbx_path}")
        print(f"[Bridge] JSON path: {json_path}")

        if not os.path.exists(fbx_path):
            return f"ERR|FBX file not found: {fbx_path}"
        if not os.path.exists(json_path):
            return f"ERR|JSON file not found: {json_path}"

        # Leer metadata
        try:
            with open(json_path, "r") as f:
                meta = json.load(f)
            print(f"[Bridge] Metadata loaded: {meta}")
        except Exception as e:
            return f"ERR|Failed to read JSON: {e}"

        full_path = meta.get("object", "")
        object_short_name = full_path.split("|")[-1]

        # Derivar scene_name del nombre del archivo
        # Formato esperado: <scene>_<object>_toBlender_meta.json
        filename = os.path.basename(json_path)
        # Remover el sufijo
        base_name = filename.replace("_toBlender_meta.json", "")
        
        # El object_short_name ya lo tenemos del JSON
        # Entonces podemos extraer el scene_name removiendo _<object> del final
        if base_name.endswith(f"_{object_short_name}"):
            scene_name = base_name[:-len(f"_{object_short_name}")]
        else:
            # Fallback: usar todo antes del último underscore
            parts = base_name.rsplit("_", 1)
            scene_name = parts[0] if len(parts) > 1 else base_name

        print(f"[Bridge] Scene name: {scene_name}")
        print(f"[Bridge] Object name: {object_short_name}")

        # Guardar objetos antes de importar
        before_import = set(bpy.data.objects.keys())

        # Importar FBX usando el operador Maya
        try:
            print("[Bridge] Using FBX Maya importer")
            bpy.ops.import_scene.fbx_maya(filepath=fbx_path)
        except Exception as e:
            return f"ERR|FBX import failed: {e}"

        # Encontrar objetos nuevos
        after_import = set(bpy.data.objects.keys())
        new_objects = after_import - before_import
        print(f"[Bridge] New objects after import: {new_objects}")

        # Buscar el objeto mesh importado
        imported_obj = None
        
        # Primero buscar en los objetos seleccionados
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                imported_obj = obj
                break
        
        # Si no hay seleccionados, buscar en los nuevos objetos
        if not imported_obj:
            for obj_name in new_objects:
                obj = bpy.data.objects.get(obj_name)
                if obj and obj.type == 'MESH':
                    imported_obj = obj
                    break

        if imported_obj:
            # Guardar el nombre actual por si necesitamos revertir
            imported_name = imported_obj.name
            
            # Intentar renombrar al nombre esperado de Maya
            try:
                imported_obj.name = object_short_name
                print(f"[Bridge] Renamed object to: {object_short_name}")
            except:
                print(f"[Bridge] Warning: Could not rename to {object_short_name}, keeping {imported_obj.name}")
                # Si no se puede renombrar, al menos actualizar el atributo maya_object
                # para que coincida con el nombre actual
                object_short_name = imported_obj.name

            # Guardar metadata en el objeto
            imported_obj["maya_scene"] = scene_name
            imported_obj["maya_object"] = object_short_name
            
            # Tambien guardar el path completo por si acaso
            imported_obj["maya_full_path"] = full_path
            
            # Guardar el nombre original con el que llego de Maya
            imported_obj["maya_original_name"] = object_short_name
            
            print(f"[Bridge] Imported '{imported_obj.name}' with session data:")
            print(f"  - maya_scene: {scene_name}")
            print(f"  - maya_object: {object_short_name}")
            print(f"  - maya_original_name: {object_short_name}")
            print(f"  - maya_full_path: {full_path}")
            
            return f"OK|Imported {object_short_name}"
        else:
            return "ERR|No mesh object found in imported FBX"

    return f"ERR|Unknown command: {command}"

def start_listener():
    global _is_listening
    if _is_listening:
        print("[Bridge] Listener already running")
        return
    _is_listening = True

    def run():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server.bind((BRIDGE_HOST, BRIDGE_PORT))
            server.listen(1)
            print(f"[Bridge] Listening on {BRIDGE_HOST}:{BRIDGE_PORT}")
        except Exception as e:
            print(f"[Bridge] Failed to start server: {e}")
            global _is_listening
            _is_listening = False
            return

        while _is_listening:
            try:
                conn, addr = server.accept()
                print(f"[Bridge] Connection from {addr}")
                
                data = conn.recv(BUFFER_SIZE)
                if data:
                    command = data.decode("utf-8").strip()
                    print(f"[Bridge] Received command: {command}")

                    def handle_and_reply():
                        result = handle_command(command)
                        print(f"[Bridge] Response: {result}")
                        try:
                            conn.sendall(result.encode("utf-8"))
                        except Exception as e:
                            print(f"[Bridge] Error sending response: {e}")
                        finally:
                            conn.close()

                    # Ejecutar en el hilo principal de Blender
                    bpy.app.timers.register(handle_and_reply, first_interval=0.01)
                else:
                    conn.close()
                    
            except Exception as e:
                if _is_listening:
                    print(f"[Bridge] Server error: {e}")

        server.close()
        print("[Bridge] Server closed")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

def stop_listener():
    global _is_listening
    _is_listening = False
    print("[Bridge] Listener stopped")