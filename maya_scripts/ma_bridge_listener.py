# -*- coding: ascii -*-
# ma_bridge_listener.py

import socket
import threading
import maya.cmds as mc
from ma_bridge_sender import replace_object_from_blender

HOST = "127.0.0.1"
PORT = 6001  # Maya escucha en 6001
BUFFER_SIZE = 4096

_is_listening = False
_server_thread = None
_on_connect_callback = None

def set_on_connect_callback(callback):
    global _on_connect_callback
    _on_connect_callback = callback

def is_running():
    return _is_listening

def handle_command(command):
    parts = command.strip().split("|")
    cmd = parts[0].upper()

    if cmd == "PING":
        return "PONG|Maya bridge ready"

    elif cmd == "REPLACE" and len(parts) >= 2:
        # Puede venir como REPLACE|object o REPLACE|scene|object
        if len(parts) >= 3:
            # Formato: REPLACE|scene|object
            scene_name = parts[1]
            object_name = parts[2]
            scene_and_object = "{}|{}".format(scene_name, object_name)
        else:
            # Formato: REPLACE|object (retrocompatibilidad)
            scene_and_object = parts[1]
        
        result = replace_object_from_blender(scene_and_object)
        return result

    elif cmd == "PLACEHOLDER" and len(parts) > 1:
        print("[Bridge] Placeholder received: {}".format(parts[1]))
        return "OK|Placeholder"

    return "ERR|Unknown or incomplete command: {}".format(command)

def start_listener():
    global _is_listening, _server_thread

    if _is_listening:
        print("[Bridge] Listener already running")
        return

    _is_listening = True

    def run():
        print("[Bridge] Maya listening on {}:{}".format(HOST, PORT))
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)

        while _is_listening:
            try:
                conn, addr = server.accept()
                print("[Bridge] Connection from", addr)

                if _on_connect_callback:
                    try:
                        _on_connect_callback()
                    except Exception as e:
                        print("[Bridge] Callback error: {}".format(e))

                data = conn.recv(BUFFER_SIZE)
                if data:
                    command = data.decode("utf-8").strip()
                    print("[Bridge] Received command:", command)

                    def handle_and_reply():
                        result = handle_command(command)
                        try:
                            conn.sendall(result.encode("utf-8"))
                        except:
                            pass

                    import maya.utils
                    maya.utils.executeDeferred(handle_and_reply)

            except Exception as e:
                print("[Bridge] Server error: {}".format(e))

    _server_thread = threading.Thread(target=run)
    _server_thread.daemon = True
    _server_thread.start()

def stop_listener():
    global _is_listening
    _is_listening = False
    print("[Bridge] Listener stopped")