# -*- coding: utf-8 -*-
import sys
import os
import tempfile
import uuid
import subprocess # Necesario para llamar a mayapy
import maya.cmds as mc
import maya.mel as mel # Para obtener la ubicación de Maya
from PySide2 import QtWidgets, QtGui, QtCore

class UVSnapshotTool(QtWidgets.QWidget):
    def __init__(self):
        super(UVSnapshotTool, self).__init__()

        # Ventana principal
        self.setWindowTitle("UV Snapshot Tool (Standalone Test Harness)")
        self.setGeometry(300, 300, 500, 370) # Un poco más de alto para el checkbox

        # Layout
        self.layout = QtWidgets.QVBoxLayout()

        # Botón para ejecutar el proceso standalone simulado
        self.capture_button = QtWidgets.QPushButton("Run Standalone UV Capture Process", self)
        self.capture_button.clicked.connect(self.run_standalone_process)
        self.layout.addWidget(self.capture_button)

        # --- Checkbox Restaurado ---
        self.compose_checkbox = QtWidgets.QCheckBox("Compose with texture (if found)", self)
        self.compose_checkbox.setChecked(True) # Por defecto, intentar componer
        self.layout.addWidget(self.compose_checkbox)
        # ---------------------------

        # Ventana de salida para logs
        self.output_log = QtWidgets.QTextEdit(self)
        self.output_log.setReadOnly(True)
        self.output_log.setFontFamily("Consolas") 
        self.layout.addWidget(self.output_log)

        self.setLayout(self.layout)
        
        # --- Búsqueda de mayapy y script (sin cambios) ---
        self.mayapy_path = self.find_mayapy()
        if not self.mayapy_path:
             self.output_log.append("[CRITICAL ERROR] Could not find mayapy.exe. Standalone process cannot be launched.")
             self.capture_button.setEnabled(False)
        else:
             self.output_log.append("Found mayapy at: {}".format(self.mayapy_path))
             
        self.standalone_script_path = self.find_standalone_script()
        if not self.standalone_script_path:
             self.output_log.append("[CRITICAL ERROR] Could not find ma_uvshot_capture_standalone.py.")
             if self.mayapy_path: 
                 self.capture_button.setEnabled(False)
        else:
             self.output_log.append("Found standalone script at: {}".format(self.standalone_script_path))


    def find_mayapy(self):
        """Intenta encontrar la ruta de mayapy.exe"""
        # --- (Sin cambios en esta función) ---
        try:
            maya_location = os.path.dirname(sys.executable)
            mayapy = os.path.join(maya_location, "mayapy.exe")
            if os.path.isfile(mayapy): return os.path.normpath(mayapy)
            maya_location_env = os.environ.get('MAYA_LOCATION')
            if maya_location_env:
                mayapy = os.path.join(maya_location_env, "bin", "mayapy.exe")
                if os.path.isfile(mayapy): return os.path.normpath(mayapy)
            maya_location_mel = mel.eval('getenv MAYA_LOCATION;')
            if maya_location_mel:
                mayapy = os.path.join(maya_location_mel, "bin", "mayapy.exe")
                if os.path.isfile(mayapy): return os.path.normpath(mayapy)
        except Exception as e:
            self.output_log.append("[ERROR] Error while searching for mayapy: {}".format(e))
        self.output_log.append("[WARNING] Could not automatically determine mayapy.exe location.")
        return None

    def find_standalone_script(self):
        """Intenta encontrar ma_uvshot_capture_standalone.py en las rutas de script."""
         # --- (Sin cambios en esta función) ---
        script_name = "ma_uvshot_capture_standalone.py"
        try:
            import inspect
            current_script_path = inspect.getfile(inspect.currentframe())
            current_script_dir = os.path.dirname(current_script_path)
            potential_path = os.path.join(current_script_dir, script_name)
            if os.path.isfile(potential_path): return os.path.normpath(potential_path)
        except:
             self.output_log.append("[DEBUG] Could not determine current script directory reliably.")
        maya_script_paths = os.environ.get('MAYA_SCRIPT_PATH', '').split(os.pathsep)
        for path in sys.path:
            if path and path not in maya_script_paths: maya_script_paths.append(path)
        for path_dir in maya_script_paths:
            if not path_dir: continue 
            try:
                potential_path = os.path.join(path_dir, script_name)
                if os.path.isfile(potential_path): return os.path.normpath(potential_path)
            except Exception as e: 
                 self.output_log.append("[DEBUG] Error checking script path '{}': {}".format(path_dir, e))
        self.output_log.append("[WARNING] Could not find '{}' in script paths.".format(script_name))
        return None

    def run_standalone_process(self):
        """
        Prepara los argumentos y lanza ma_uvshot_capture_standalone.py 
        usando mayapy.exe en un proceso separado.
        """
        self.output_log.clear()
        
        # Re-verificar rutas
        if not self.mayapy_path:
            self.output_log.append("[ERROR] mayapy.exe path not found. Cannot proceed.")
            self.mayapy_path = self.find_mayapy()
            if not self.mayapy_path: return 
            self.output_log.append("Re-found mayapy at: {}".format(self.mayapy_path))
        if not self.standalone_script_path:
            self.output_log.append("[ERROR] Standalone script path not found. Cannot proceed.")
            self.standalone_script_path = self.find_standalone_script()
            if not self.standalone_script_path: return 
            self.output_log.append("Re-found standalone script at: {}".format(self.standalone_script_path))

        # Selección
        selection = mc.ls(selection=True, long=True, type='transform')
        if not selection:
            self.output_log.append("[ERROR] No mesh selected. Please select one mesh object.")
            return
        mesh_transform = selection[0] 
        shapes = mc.listRelatives(mesh_transform, shapes=True, type='mesh', fullPath=True)
        if not shapes:
             self.output_log.append("[ERROR] Selected object '{}' has no mesh shape.".format(mesh_transform))
             return

        # Carpeta de salida
        output_folder_list = mc.fileDialog2(caption="Choose folder for Standalone Output", fileMode=3, okCaption="Select Folder")
        if not output_folder_list:
            self.output_log.append("No folder selected. Cancelling.")
            return
        output_folder = os.path.normpath(output_folder_list[0])
        self.output_log.append("Output folder: {}".format(output_folder))

        # --- Exportar el mesh ---
        self.output_log.append("Attempting to export mesh...")
        # Cambiamos la lógica: exportamos primero, luego buscamos textura si es necesario
        temp_fbx_path = self.export_mesh_to_fbx(mesh_transform) # Nueva función simplificada
        
        if not temp_fbx_path:
            self.output_log.append("[ERROR] Failed to export mesh to temporary FBX. Aborting.")
            return
        
        # --- Obtener textura y decidir si pasarla ---
        texture_path_to_pass = "None" # Valor por defecto si no se compone
        should_compose = self.compose_checkbox.isChecked() # Leer el checkbox
        
        if should_compose:
            self.output_log.append("Composition requested. Searching for texture...")
            texture_file = self.get_texture_from_mesh(mesh_transform)
            if texture_file:
                 self.output_log.append("Texture found: {}".format(texture_file))
                 texture_path_to_pass = texture_file # Usar la textura encontrada
            else:
                 self.output_log.append("[INFO] Composition requested, but no valid texture found. Will skip composition.")
                 # texture_path_to_pass sigue siendo "None"
        else:
            self.output_log.append("Composition NOT requested.")
            # texture_path_to_pass sigue siendo "None"

        # --- Preparar y ejecutar el proceso standalone ---
        self.output_log.append("\n--- Starting Standalone Process ---")
        self.output_log.append("Using script: {}".format(self.standalone_script_path))
        self.output_log.append("FBX Input: {}".format(temp_fbx_path))
        self.output_log.append("Output Folder: {}".format(output_folder))
        self.output_log.append("Texture Input (to standalone): {}".format(texture_path_to_pass)) # Mostrar lo que se pasa

        # Construir el comando
        command = [
            self.mayapy_path,
            self.standalone_script_path,
            temp_fbx_path,
            output_folder,
            texture_path_to_pass # Pasar la ruta o "None"
        ]

        formatted_command = " ".join(['"{}"'.format(c) if ' ' in c else c for c in command])
        self.output_log.append("Executing command: {}".format(formatted_command))

        try:
            # --- Ejecución de subprocess (sin cambios) ---
            startupinfo = None
            if os.name == 'nt': 
                 startupinfo = subprocess.STARTUPINFO()
                 startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                 startupinfo.wShowWindow = subprocess.SW_HIDE 
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                startupinfo=startupinfo, bufsize=1, universal_newlines=True 
            )
            self.output_log.append("\n--- Standalone Script Output ---")
            while True:
                line = process.stdout.readline()
                if not line: break
                self.output_log.insertPlainText(line) 
                self.output_log.moveCursor(QtGui.QTextCursor.End) 
                QtWidgets.QApplication.processEvents() 
            process.wait() 
            self.output_log.append("------------------------------")
            if process.returncode == 0:
                self.output_log.append("--- Standalone Process Completed Successfully ---")
            else:
                self.output_log.append("\n[ERROR] --- Standalone Process Failed (Return Code: {}) ---".format(process.returncode))
        except Exception as e:
            self.output_log.append("\n[CRITICAL ERROR] Failed to execute standalone process:")
            import traceback
            self.output_log.append(traceback.format_exc())
        finally:
            # --- Limpieza del FBX temporal (sin cambios) ---
            if temp_fbx_path and os.path.exists(temp_fbx_path):
                try:
                    os.remove(temp_fbx_path)
                    self.output_log.append("Cleaned up temporary FBX: {}".format(temp_fbx_path))
                except Exception as e:
                    self.output_log.append("[WARNING] Could not delete temporary FBX file '{}': {}".format(temp_fbx_path, e))

    # --- Función de Exportación Simplificada ---
    def export_mesh_to_fbx(self, mesh_transform):
        """
        Exporta el mesh seleccionado a un archivo FBX temporal.
        Devuelve ruta_fbx_temporal o None en caso de fallo.
        """
        unique_id = uuid.uuid4().hex
        temp_dir = tempfile.gettempdir()
        temp_fbx_path = os.path.normpath(os.path.join(temp_dir, "temp_uvshot_export_{}.fbx".format(unique_id)))
        
        self.output_log.append("Exporting selected mesh '{}' to temporary FBX...".format(mesh_transform))
        self.output_log.append("Target FBX: {}".format(temp_fbx_path))
        
        try:
            if not mc.pluginInfo("fbxmaya", query=True, loaded=True):
                self.output_log.append("[INFO] Loading fbxmaya plugin...")
                mc.loadPlugin("fbxmaya")
                self.output_log.append("[INFO] fbxmaya plugin loaded.")

            mc.select(mesh_transform, replace=True) 
            
            mc.file(
                temp_fbx_path, force=True, options="v=0;", 
                type="FBX export", preserveReferences=True, exportSelected=True 
            )
            
            if os.path.exists(temp_fbx_path):
                self.output_log.append("Temporary FBX export successful.")
                return temp_fbx_path # Solo devolver la ruta del FBX
            else:
                 self.output_log.append("[ERROR] FBX export command ran but file not found at destination!")
                 return None
        except Exception as e:
            self.output_log.append("[ERROR] FBX export failed:")
            import traceback
            self.output_log.append(traceback.format_exc())
            if os.path.exists(temp_fbx_path):
                try: os.remove(temp_fbx_path)
                except: pass
            return None

    # --- Función para obtener textura (sin cambios significativos) ---
    def get_texture_from_mesh(self, mesh):
        """Obtiene la ruta de la textura asociada a un mesh"""
        # --- (Esta función es idéntica a la versión anterior, no necesita cambios) ---
        shapes = mc.listRelatives(mesh, shapes=True, fullPath=True, type='mesh') 
        if not shapes:
            self.output_log.append("[WARNING] No mesh shape found for transform: {}".format(mesh))
            return None
        for s in shapes:
            shading_groups = mc.listConnections(s, type='shadingEngine') or []
            if not shading_groups:
                self.output_log.append("[INFO] No shading groups found for shape: {}".format(s))
                continue 
            for sg in shading_groups:
                shader_connections = mc.listConnections(sg + ".surfaceShader", source=True, destination=False) or []
                if not shader_connections:
                     self.output_log.append("[INFO] No surface shader connected to SG: {}".format(sg))
                     continue
                shader = shader_connections[0]
                self.output_log.append("[DEBUG] Checking shader: {}".format(shader))
                color_attrs_to_check = ['baseColor', 'color', 'TEX_color_map', 'diffuseColor', 'diffuse_color'] 
                found_file_node = None
                for attr in color_attrs_to_check:
                    if mc.attributeQuery(attr, node=shader, exists=True):
                        connection = "{}.{}".format(shader, attr)
                        if mc.connectionInfo(connection, isDestination=True):
                            connected_nodes = mc.listConnections(connection, s=True, d=False, type='file')
                            if connected_nodes:
                                current_file_node = connected_nodes[0] 
                                node_type = mc.nodeType(shader, inherited=True)
                                if 'StingrayPBS' in node_type and attr == 'TEX_color_map':
                                    try: 
                                        if not mc.getAttr(shader + '.use_color_map'):
                                            self.output_log.append("[DEBUG] Found connection to TEX_color_map on '{}' but use_color_map is OFF.".format(shader))
                                            continue 
                                    except Exception as e:
                                         self.output_log.append("[DEBUG] Could not check use_color_map for shader '{}': {}".format(shader, e))
                                         pass 
                                found_file_node = current_file_node
                                self.output_log.append("[DEBUG] Found file node '{}' connected to attribute '{}' on shader '{}'".format(found_file_node, attr, shader))
                                break 
                if found_file_node:
                    try:
                        texture_file = mc.getAttr(found_file_node + ".fileTextureName")
                        try:
                             expanded_path = mc.workspace(expandName=texture_file)
                             if expanded_path: texture_file = expanded_path
                        except Exception as we:
                             self.output_log.append("[DEBUG] Could not expand workspace path for '{}': {}".format(texture_file, we))
                        texture_file_norm = os.path.normpath(texture_file)
                        if texture_file_norm and os.path.isfile(texture_file_norm):
                            self.output_log.append("[DEBUG] Texture file path validated: {}".format(texture_file_norm))
                            return texture_file_norm 
                        else:
                            self.output_log.append("[WARNING] File path '{}' from node '{}' (normalized: '{}') does not exist or path is empty.".format(texture_file, found_file_node, texture_file_norm))
                    except Exception as e:
                         self.output_log.append("[WARNING] Could not get 'fileTextureName' from node '{}': {}".format(found_file_node, e))
                if not found_file_node: 
                    all_file_nodes = mc.listConnections(shader, type='file', source=True, destination=False) or []
                    if all_file_nodes:
                        fallback_node = all_file_nodes[0]
                        self.output_log.append("[DEBUG] Trying fallback: Found file node '{}' via general search on shader '{}'.".format(fallback_node, shader))
                        try:
                            texture_file = mc.getAttr(fallback_node + ".fileTextureName")
                            try:
                                expanded_path = mc.workspace(expandName=texture_file)
                                if expanded_path: texture_file = expanded_path
                            except Exception as we:
                                 self.output_log.append("[DEBUG] Could not expand workspace path for fallback '{}': {}".format(texture_file, we))
                            texture_file_norm = os.path.normpath(texture_file)
                            if texture_file_norm and os.path.isfile(texture_file_norm):
                                self.output_log.append("[DEBUG] Fallback texture file path validated: {}".format(texture_file_norm))
                                return texture_file_norm 
                            else:
                                self.output_log.append("[WARNING] Fallback file path '{}' from node '{}' (normalized: '{}') does not exist.".format(texture_file, fallback_node, texture_file_norm))
                        except Exception as e:
                             self.output_log.append("[WARNING] Could not get 'fileTextureName' from fallback node '{}': {}".format(fallback_node, e))
        self.output_log.append("[INFO] No validated texture file path found for mesh: {}".format(mesh))
        return None 


# --- Bloque para Ejecutar la UI (sin cambios) ---
uv_snapshot_tool_window = None

def show_ui():
    global uv_snapshot_tool_window
    main_window = None
    window_object_name = "UVSnapshotToolStandaloneTestHarnessWindow" 
    try:
        app = QtWidgets.QApplication.instance()
        if app:
            all_windows = app.topLevelWidgets()
            for widget in all_windows:
                if widget.objectName() == window_object_name:
                     main_window = widget
                     break
        if main_window:
            main_window.close()
            main_window.deleteLater() 
            print("Closed existing UV Snapshot Tool window.")
    except Exception as e:
        print("Error closing existing window: {}".format(e))
    try:
        uv_snapshot_tool_window = UVSnapshotTool()
        uv_snapshot_tool_window.setObjectName(window_object_name) 
        uv_snapshot_tool_window.show()
        print("Launched UV Snapshot Tool (Standalone Test Harness).")
    except Exception as e:
         print("Error launching UV Snapshot Tool window:")
         import traceback
         traceback.print_exc()

if __name__ == "__main__":
   show_ui()