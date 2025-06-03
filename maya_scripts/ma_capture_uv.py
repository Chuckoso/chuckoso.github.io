# -*- coding: utf-8 -*-
import maya.cmds as mc
import os
import traceback

def capture_all_uv_sets(obj, output_folder, resolution):
    """
    Captures all UV sets of a given object and saves each as a PNG image.

    :param obj: The transform node of the object.
    :param output_folder: Folder where the UV snapshots will be saved.
    :param resolution: Resolution for the UV snapshot (square).
    """
    # Get all UV sets for the object
    try:
        # Verificar si el objeto existe en la escena standalone
        if not mc.objExists(obj):
             print("[ERROR] Object '{}' does not exist in the current scene.".format(obj))
             return # Salir si el objeto no existe
             
        uv_sets = mc.polyUVSet(obj, query=True, allUVSets=True)
        
    except Exception as e:
         print("[ERROR] Could not query UV sets for object: {}".format(obj))
         print("Specific Error: {}".format(str(e)))
         uv_sets = [] # Asignar lista vacía para evitar error posterior

    if not uv_sets:
        # Este mensaje es más preciso ahora que comprobamos objExists primero
        print("[WARNING] No UV sets found on existing object: {}".format(obj)) 
        return

    # Crear la carpeta de salida si no existe
    if not os.path.exists(output_folder):
         try:
              os.makedirs(output_folder)
              print("[INFO] Created output directory: {}".format(output_folder))
         except Exception as e:
              print("[ERROR] Could not create output directory '{}': {}".format(output_folder, e))
              return 

    print("[INFO] Processing UV sets for object: {}".format(obj)) 

    for uv_set in uv_sets:
        # Build output file path
        # Usar replace para manejar barras y dos puntos (namespaces)
        safe_obj_name = obj.replace("|", "_").replace(":", "_") 
        # Asegurarse de que el nombre del UV set también sea seguro para un nombre de archivo
        safe_uv_set_name = uv_set.replace(":", "_").replace(" ", "_") # Añadir reemplazo de espacios por si acaso
        filename = "{}_{}_uv.png".format(safe_obj_name, safe_uv_set_name)
        output_path = os.path.join(output_folder, filename)
        output_path = os.path.normpath(output_path)

        print("[DEBUG] Attempting UV snapshot:")
        print("[DEBUG]   Object: {}".format(obj))
        print("[DEBUG]   UV Set: {}".format(uv_set))
        print("[DEBUG]   Output Path: {}".format(output_path))
        print("[DEBUG]   Resolution: {}".format(resolution))
        
        # Verificar si el UV set realmente existe
        try:
            current_sets = mc.polyUVSet(obj, q=True, auv=True) or []
            if uv_set not in current_sets:
                 print("[ERROR] UV set '{}' no longer exists on object '{}' before snapshot.".format(uv_set, obj))
                 continue 
            print("[DEBUG]   UV Set Exists Check: OK")
        except Exception as e_verify:
            print("[WARNING] Could not re-verify UV set existence for '{}': {}".format(uv_set, e_verify))

        # Set the current UV set (opcional, puede ayudar)
        try:
            mc.polyUVSet(obj, currentUVSet=True, uvSet=uv_set)
            print("[DEBUG]   Set current UV set to: {}".format(uv_set))
        except Exception as e_set:
            print("[WARNING] Could not set UV set '{}' as current: {}".format(uv_set, e_set))
        
        # Capture the UV snapshot
        try:
            # --- *** SOLUCIÓN: Seleccionar el objeto ANTES de llamar a uvSnapshot *** ---
            # Primero, verificar si el objeto todavía existe antes de intentar seleccionarlo
            if not mc.objExists(obj):
                print("[ERROR] Object '{}' disappeared before selection for snapshot.".format(obj))
                continue # Saltar al siguiente UV set

            mc.select(obj, replace=True) 
            print("[DEBUG]   Selected object: {}".format(obj))
            
            mc.uvSnapshot(
                o=True,              
                name=output_path,    
                xr=resolution,       
                yr=resolution,       
                aa=True,             
                ff="png",            
                uvSetName=uv_set,    
                redColor=0,          # Verde
                greenColor=255,      # Verde
                blueColor=0          # Verde
            )
            
            # Verificar si el archivo realmente se creó
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0: 
                 print("[INFO] UV snapshot saved: {}".format(output_path))
            else:
                 # Intentar obtener más información si falló
                 error_info = "Unknown reason."
                 if not os.path.exists(output_path):
                      error_info = "Output file was NOT found."
                 elif os.path.getsize(output_path) == 0:
                      error_info = "Output file has size 0."
                 
                 # Verificar permisos de escritura en la carpeta
                 can_write = os.access(output_folder, os.W_OK)
                 print("[ERROR] mc.uvSnapshot command ran for '{}' but failed. {} Can write to folder: {}".format(output_path, error_info, can_write))
                 print("[ERROR] Possible issues: File permissions, invalid path/filename chars, disk full, internal Maya error.")

        except Exception as e: 
            print("\n" + "="*20 + " SNAPSHOT ERROR " + "="*20)
            print("[ERROR] Failed to capture UV set '{}' for object '{}'".format(uv_set, obj))
            print("        Attempted Path: {}".format(output_path))
            print("        Specific Maya Error: {}".format(str(e))) 
            print("        Traceback:")
            print(traceback.format_exc()) 
            print("="*54 + "\n")
            continue # Continuar con el siguiente UV set si falla

    # Deseleccionar todo al final del procesamiento del objeto (buena práctica)
    try:
        mc.select(clear=True)
        print("[DEBUG] Cleared selection after processing object.")
    except Exception as e_sel:
         print("[WARNING] Could not clear selection: {}".format(e_sel))
         
    # Mover este print aquí tiene más sentido que fuera del bucle de objetos
    print("[INFO] Finished processing UV sets for object: {}".format(obj)) 

# No debe haber código ejecutable aquí fuera de las definiciones de funciones/clases