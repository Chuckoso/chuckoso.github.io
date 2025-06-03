# -*- coding: utf-8 -*-

import sys
import os
import traceback
import maya.standalone
import maya.cmds as mc
import ma_capture_uv  # Captura UV básica
reload(ma_capture_uv)
# Importamos el compositor con las dos funciones separadas
import ma_image_composer  
reload(ma_image_composer)

# Opción para decidir si eliminar los PNG básicos después de la mejora
DELETE_BASIC_PNG_AFTER_ENHANCE = True 

def main():
    print("[DEBUG] Script reached main()")

    if len(sys.argv) < 4:
        print("[ERROR] Expected arguments: <input_fbx_path> <output_folder> <texture_path_or_None>")
        sys.exit(1)

    input_fbx = os.path.normpath(sys.argv[1])
    output_folder = os.path.normpath(sys.argv[2])
    texture_file_arg = sys.argv[3] # Puede ser una ruta o la cadena "None"

    # Validar la ruta de textura SÓLO si no es "None"
    texture_file = None
    if texture_file_arg.lower() != "none":
         norm_texture_path = os.path.normpath(texture_file_arg)
         if os.path.isfile(norm_texture_path):
              texture_file = norm_texture_path
              print("[INFO] Valid texture file provided: {}".format(texture_file))
         else:
              print("[WARNING] Texture file specified but not found: {}".format(norm_texture_path))
              print("[INFO] Composition will be skipped.")
    else:
         print("[INFO] No texture file provided ('None'). Composition will be skipped.")

    print("[INFO] Importing FBX: {}".format(input_fbx))

    if not mc.pluginInfo("fbxmaya", query=True, loaded=True):
        try:
            mc.loadPlugin("fbxmaya")
            print("[INFO] FBX plugin loaded.")
        except Exception as e:
            print("[ERROR] Could not load FBX plugin: {}".format(str(e)))
            sys.exit(1) # Salir si no se puede cargar FBX

    try:
        mc.file(input_fbx, i=True, type="FBX", ignoreVersion=True, ra=True,
                mergeNamespacesOnClash=False, options="fbx", pr=True)
        print("[INFO] FBX imported successfully.")
    except Exception as e:
        print("[ERROR] Failed to import FBX: {}".format(str(e)))
        # Intentar continuar? O salir? Por ahora salimos si falla la importación.
        sys.exit(1) 

    meshes = mc.ls(type="mesh", long=True) or []
    transforms = list(set(mc.listRelatives(meshes, parent=True, fullPath=True) or []))

    if not transforms:
        print("[WARNING] No mesh transforms found in the imported FBX.")
        # No necesariamente un error, podría ser un archivo vacío. Salir limpiamente.
        sys.exit(0) 

    # --- Procesamiento por Malla ---
    for mesh_transform in transforms:
        print("\n" + "-"*10 + " Processing Mesh: {}".format(mesh_transform) + "-"*10)
        
        # --- PASO 1: Captura UV Básica ---
        resolution = 1024 # Definir resolución aquí
        # ma_capture_uv ya crea la carpeta si no existe y maneja errores internos
        ma_capture_uv.capture_all_uv_sets(mesh_transform, output_folder, resolution=resolution)

        # --- PASO 2: Mejora de UV (Siempre) ---
        # Necesitamos saber los UV sets para encontrar los PNGs básicos generados
        try:
             uv_sets = mc.polyUVSet(mesh_transform, query=True, allUVSets=True) or []
        except Exception as e:
             print("[ERROR] Could not query UV sets again for mesh '{}' to enhance. Skipping enhancement/composition. Error: {}".format(mesh_transform, e))
             continue # Saltar al siguiente mesh

        if not uv_sets:
            print("[INFO] No UV sets found for mesh '{}' after capture. Nothing to enhance/compose.".format(mesh_transform))
            continue # Saltar al siguiente mesh
            
        print("[INFO] Starting enhancement/composition phase for {} UV sets...".format(len(uv_sets)))

        for uv_set in uv_sets:
            print("--- Processing UV Set: {} ---".format(uv_set))
            
            # Construir nombres de archivo (coincidiendo con ma_capture_uv.py)
            safe_mesh_name = mesh_transform.replace("|", "_").replace(":", "_")
            safe_uv_set_name = uv_set.replace(":", "_").replace(" ", "_")
            
            basic_png_filename = "{}_{}_uv.png".format(safe_mesh_name, safe_uv_set_name)
            basic_png_path = os.path.join(output_folder, basic_png_filename)
            
            # Definir nombre para el archivo mejorado
            enhanced_png_filename = "{}_{}_enhanced_uv.png".format(safe_mesh_name, safe_uv_set_name)
            enhanced_png_path = os.path.join(output_folder, enhanced_png_filename)

            # Verificar si el PNG básico existe antes de intentar mejorarlo
            if not os.path.isfile(basic_png_path):
                 print("[WARNING] Basic UV snapshot '{}' not found. Cannot enhance/compose.".format(basic_png_path))
                 continue # Saltar al siguiente UV set

            # --- Llamada a la función de mejora (SIEMPRE) ---
            enhancement_success = ma_image_composer.enhance_uv_snapshot(
                basic_png_path, 
                enhanced_png_path
            )

            if enhancement_success and DELETE_BASIC_PNG_AFTER_ENHANCE:
                 try:
                      os.remove(basic_png_path)
                      print("[INFO] Deleted basic PNG: {}".format(basic_png_path))
                 except Exception as e_del:
                      print("[WARNING] Failed to delete basic PNG '{}': {}".format(basic_png_path, e_del))
            elif not enhancement_success:
                 print("[ERROR] Enhancement failed for {}. Composition will be skipped.".format(basic_png_path))
                 continue # Saltar al siguiente UV set si la mejora falló

            # --- PASO 3: Composición (Condicional) ---
            # Comprobar si tenemos una ruta de textura válida Y la mejora fue exitosa
            if texture_file and enhancement_success:
                 composed_jpg_filename = "{}_{}_composed.jpg".format(safe_mesh_name, safe_uv_set_name)
                 composed_jpg_path = os.path.join(output_folder, composed_jpg_filename)

                 # --- Llamada a la función de composición ---
                 ma_image_composer.compose_uv_over_texture(
                      enhanced_png_path,   # Usar el PNG mejorado como entrada
                      texture_file,
                      composed_jpg_path,
                      resolution,          # Pasar resolución para redimensionar textura
                      resolution
                 )
            elif not texture_file:
                print("[INFO] Skipping composition for UV set '{}' as no valid texture was provided.".format(uv_set))
            # (El caso de enhancement_success == False ya se maneja arriba)


    print("\n[SUCCESS] UV snapshot enhancement and optional composition completed for all meshes.")

# --- Bloque main (sin cambios) ---
if __name__ == "__main__":
    try:
        print("[DEBUG] Initializing Maya Standalone...")
        maya.standalone.initialize(name="python")
        print("[DEBUG] Maya Standalone Initialized.")
        main()
    except Exception as e:
        print("\n" + "="*20 + " STANDALONE SCRIPT CRASH " + "="*20)
        print("[EXCEPTION] Script crashed:")
        # Imprimir el error directamente también puede ser útil
        print("        Error Type: {}".format(type(e).__name__))
        print("        Error Details: {}".format(str(e)))
        print("        Traceback:")
        print(traceback.format_exc())
        print("="*68 + "\n")
        sys.exit(1) # Salir con código de error si el script principal falla
    finally:
        try:
            print("[DEBUG] Uninitializing Maya Standalone...")
            maya.standalone.uninitialize()
            print("[DEBUG] Maya Standalone Uninitialized.")
        except Exception as e_uninit:
             # Esto es menos crítico, pero bueno saberlo si falla
             print("[ERROR] Failed to uninitialize Maya Standalone: {}".format(e_uninit))