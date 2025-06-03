# -*- coding: ascii -*-
# ma_bridge_sender.py

import os
import json
import socket
import maya.cmds as mc
from ma_bridge_session import (
    get_scene_name,
    get_object_name,
    get_temp_fbx_path,
    get_temp_json_path
)

def send_selected_object_to_blender():
    obj_name = get_object_name()
    if not obj_name:
        mc.warning("No object selected to send to Blender.")
        return

    scene_name = get_scene_name()
    fbx_path = get_temp_fbx_path(scene_name, obj_name, direction="toBlender")
    json_path = get_temp_json_path(scene_name, obj_name, direction="toBlender")

    full_obj_path = mc.ls(selection=True, long=True)[0]
    temp_name = obj_name + "_bledit"
    temp_copy = mc.duplicate(full_obj_path, name=temp_name)[0]

    if mc.listRelatives(temp_copy, parent=True):
        try:
            mc.parent(temp_copy, world=True)
        except Exception as e:
            print("[Bridge] Warning: Could not unparent '{}': {}".format(temp_copy, e))

    world_matrix = mc.xform(full_obj_path, q=True, matrix=True, worldSpace=True)
    parent = mc.listRelatives(full_obj_path, parent=True, fullPath=True)

    linked = mc.lightlink(object=full_obj_path, q=True) or []
    unlinked = []

    # Obtener informacion de materiales
    material_data = []
    shapes = mc.listRelatives(full_obj_path, shapes=True, fullPath=True) or []
    for shape in shapes:
        # Obtener shading groups del shape
        shading_groups = mc.listConnections(shape, type='shadingEngine') or []
        
        for sg in shading_groups:
            if sg == 'initialShadingGroup':
                continue
                
            # Obtener las caras asignadas a este shading group
            faces = mc.sets(sg, q=True) or []
            # Filtrar solo las caras de este objeto
            obj_faces = [f for f in faces if shape in f]
            
            if obj_faces:
                material_data.append({
                    "shape": shape,
                    "shading_group": sg,
                    "faces": obj_faces
                })
                print("[Bridge] Captured material {} with {} faces".format(sg, len(obj_faces)))

    metadata = {
        "object": full_obj_path,
        "parent": parent[0] if parent else None,
        "world_matrix": world_matrix,
        "materials": material_data,
        "light_links": {
            "linked": linked,
            "unlinked": unlinked
        }
    }

    with open(json_path, "w") as f:
        json.dump(metadata, f)

    print("[Bridge] Metadata written to {}".format(json_path))

    for attr in ['translateX', 'translateY', 'translateZ',
                 'rotateX', 'rotateY', 'rotateZ',
                 'scaleX', 'scaleY', 'scaleZ']:
        try:
            mc.setAttr(temp_copy + "." + attr, 0 if 'translate' in attr or 'rotate' in attr else 1)
        except:
            pass

    try:
        # Asegurar que el plugin FBX este cargado silenciosamente
        try:
            mc.loadPlugin('fbxmaya', quiet=True)
        except:
            pass  # Ya esta cargado
            
        mc.select(temp_copy, replace=True)
        # Usar wrapper con opciones para minimizar verbosidad
        mc.file(fbx_path, force=True, options="v=0;", typ="FBX export", 
                pr=True, es=True, prompt=False)
        print("[Bridge] Exported object to {}".format(fbx_path))
    except Exception as e:
        mc.warning("Export failed: {}".format(e))
        return
    finally:
        if mc.objExists(temp_copy):
            mc.delete(temp_copy)
        mc.select(full_obj_path, replace=True)

    try:
        host = "127.0.0.1"
        port = 6000
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        command = "IMPORT|{}".format(fbx_path.replace("\\", "/"))
        sock.sendall(command.encode("utf-8"))
        sock.close()
        print("[Bridge] Command sent to Blender on port {}: {}".format(port, command))
    except Exception as e:
        mc.warning("Could not connect to Blender on port 6000: {}".format(e))


def replace_object_from_blender(scene_and_object=None):
    """
    Replace object from Blender. 
    Args:
        scene_and_object: String in format "scene|object" or just "object"
    """
    current_scene = get_scene_name()
    
    if scene_and_object and "|" in scene_and_object:
        # Si viene con formato "scene|object", separarlo
        parts = scene_and_object.split("|")
        if len(parts) >= 2:
            provided_scene = parts[0]
            object_name = parts[1]
            # Usar la escena proporcionada
            scene_name = provided_scene
            print("[Bridge] Using provided scene: '{}', object: '{}'".format(scene_name, object_name))
        else:
            # Formato incorrecto, usar como nombre de objeto
            scene_name = current_scene
            object_name = scene_and_object
    elif scene_and_object:
        # Solo viene el nombre del objeto
        scene_name = current_scene
        object_name = scene_and_object
    else:
        # No se proporciono nada, usar objeto seleccionado
        scene_name = current_scene
        object_name = get_object_name()
        if not object_name:
            mc.warning("No object selected to replace.")
            return "ERR|No object selected"

    print("[Bridge] Replacing - Scene: '{}', Object: '{}'".format(scene_name, object_name))
    
    fbx_path = get_temp_fbx_path(scene_name, object_name, direction="fromBlender")
    json_path = get_temp_json_path(scene_name, object_name, direction="toBlender")

    print("[Bridge] Looking for FBX: {}".format(fbx_path))
    print("[Bridge] Looking for JSON: {}".format(json_path))

    if not os.path.exists(fbx_path):
        return "ERR|File not found: {}".format(fbx_path)
    if not os.path.exists(json_path):
        return "ERR|Metadata file not found: {}".format(json_path)
        
    # Verificar el tamano del archivo FBX
    fbx_size = os.path.getsize(fbx_path)
    print("[Bridge] FBX file size: {} bytes".format(fbx_size))
    if fbx_size == 0:
        return "ERR|FBX file is empty"

    try:
        with open(json_path, "r") as f:
            meta = json.load(f)

        original_name = meta.get("object")
        parent_name = meta.get("parent")
        world_matrix = meta.get("world_matrix")
        material_data = meta.get("materials", [])
        light_links = meta.get("light_links", {})

        print("[Bridge] Original object path: {}".format(original_name))
        
        if not original_name:
            return "ERR|No object name in metadata"
            
        if not mc.objExists(original_name):
            # Intentar buscar por nombre corto si el path completo no existe
            short_name = original_name.split("|")[-1]
            print("[Bridge] Original path not found, searching for: {}".format(short_name))
            found_objects = mc.ls(short_name, long=True)
            if found_objects:
                original_name = found_objects[0]
                print("[Bridge] Found object at: {}".format(original_name))
            else:
                return "ERR|Original object {} not found in scene".format(original_name)

        # IMPORTANTE: Borrar el objeto original ANTES de importar
        print("[Bridge] Deleting original object BEFORE import: {}".format(original_name))
        try:
            if mc.objExists(original_name):
                mc.delete(original_name)
                print("[Bridge] Original deleted successfully")
            else:
                print("[Bridge] Warning: Original object not found for deletion")
        except Exception as e:
            print("[Bridge] Error deleting original: {}".format(e))
            return "ERR|Could not delete original object: {}".format(e)

        print("[Bridge] Importing FBX...")
        
        # Asegurar que el plugin FBX este cargado silenciosamente
        try:
            mc.loadPlugin('fbxmaya', quiet=True)
        except:
            pass  # Ya esta cargado
        
        # Guardar el estado de evaluacion actual
        current_eval_mode = mc.evaluationManager(query=True, mode=True)[0]
        
        # Guardar seleccion actual
        current_selection = mc.ls(selection=True, long=True)
        
        # Obtener lista de todos los objetos antes de importar
        before_all = set(mc.ls(long=True))
        
        # Importar el FBX con minima verbosidad
        mc.file(fbx_path, i=True, type="FBX", ignoreVersion=True, 
                pr=True, prompt=False, options="v=0;")
        
        # Restaurar modo de evaluacion si cambio
        if mc.evaluationManager(query=True, mode=True)[0] != current_eval_mode:
            mc.evaluationManager(mode=current_eval_mode)
        
        # Obtener lista despues de importar
        after_all = set(mc.ls(long=True))
        new_objects = list(after_all - before_all)
        
        print("[Bridge] New objects after import: {}".format(len(new_objects)))
        if new_objects:
            print("[Bridge] First few: {}".format(new_objects[:5]))
        
        # El FBX puede haber importado con seleccion
        imported_selection = mc.ls(selection=True, long=True)
        if imported_selection:
            print("[Bridge] Imported with selection: {}".format(imported_selection))

        # Buscar el objeto mesh importado
        new_obj = None
        
        # Buscar en los nuevos objetos
        for obj in new_objects:
            if mc.objExists(obj) and mc.objectType(obj) == "transform":
                shapes = mc.listRelatives(obj, shapes=True, fullPath=True) or []
                if any(mc.objectType(s) == "mesh" for s in shapes):
                    new_obj = obj
                    print("[Bridge] Found mesh object: {}".format(obj))
                    break
        
        # Si no encontramos transform con mesh, buscar por nombre esperado
        if not new_obj:
            expected_name = object_name
            for obj in new_objects:
                if expected_name in obj and mc.objExists(obj):
                    if mc.objectType(obj) == "transform":
                        shapes = mc.listRelatives(obj, shapes=True, fullPath=True) or []
                        if any(mc.objectType(s) == "mesh" for s in shapes):
                            new_obj = obj
                            print("[Bridge] Found object by name match: {}".format(obj))
                            break

        if not new_obj:
            return "ERR|No mesh object found in imported FBX"

        print("[Bridge] Processing imported object: {}".format(new_obj))
        
        # Aplicar transformaciones
        print("[Bridge] Applying transformations...")
        if parent_name and mc.objExists(parent_name):
            try:
                # Parent devuelve el nuevo path del objeto
                new_obj = mc.parent(new_obj, parent_name)[0]
                print("[Bridge] Parented to: {}".format(parent_name))
                print("[Bridge] New path after parent: {}".format(new_obj))
            except Exception as e:
                print("[Bridge] Could not parent: {}".format(e))
                
        if world_matrix:
            try:
                mc.xform(new_obj, matrix=world_matrix, worldSpace=True)
                print("[Bridge] Applied world matrix")
            except Exception as e:
                print("[Bridge] Could not apply matrix: {}".format(e))

        # Intentar renombrar si es necesario
        try:
            target_name = original_name.split("|")[-1]
            current_name = new_obj.split("|")[-1]
            if current_name != target_name:
                # El rename tambien devuelve el nuevo path
                new_obj = mc.rename(new_obj, target_name)
                print("[Bridge] Renamed to: {}".format(new_obj))
        except Exception as e:
            print("[Bridge] Could not rename: {}".format(e))

        # Procesar shaders
        print("[Bridge] Processing shaders...")
        shapes = mc.listRelatives(new_obj, shapes=True, fullPath=True) or []
        
        if not shapes:
            print("[Bridge] WARNING: No shapes found in object")
        else:
            print("[Bridge] Found {} shapes".format(len(shapes)))
        
        # Primero limpiar cualquier shader que venga del FBX
        for shape in shapes:
            # Obtener shading groups actuales del shape importado
            current_sgs = mc.listConnections(shape, type='shadingEngine') or []
            for sg in current_sgs:
                # Si es un shader creado por FBX (generalmente tienen sufijos), removerlo
                if sg != 'initialShadingGroup' and ('fbx' in sg.lower() or 'blender' in sg.lower() or 'SG2' in sg):
                    try:
                        # Remover todas las caras de este SG
                        mc.sets(shape, e=True, remove=sg)
                    except:
                        pass
        
        # Si hay datos de materiales, aplicarlos
        if material_data:
            print("[Bridge] Restoring {} materials from metadata...".format(len(material_data)))
            materials_applied = False
            
            for entry in material_data:
                shape_path = entry.get("shape", "")
                sg = entry.get("shading_group", "")
                faces = entry.get("faces", [])
                
                if not sg or not mc.objExists(sg):
                    print("[Bridge] WARNING: Shading group {} does not exist".format(sg))
                    continue
                
                if shape_path and faces:
                    # Obtener el nombre del shape sin path
                    old_shape_name = shape_path.split("|")[-1]
                    
                    # Buscar el shape correspondiente en el nuevo objeto
                    for shape in shapes:
                        if old_shape_name in shape:
                            # Actualizar los paths de las caras
                            new_faces = []
                            for face in faces:
                                # Extraer el componente de cara (.f[X:Y])
                                if ".f[" in face:
                                    face_component = ".f[" + face.split(".f[")[1]
                                    new_face = shape + face_component
                                    new_faces.append(new_face)
                            
                            if new_faces:
                                try:
                                    # IMPORTANTE: Usar el shading group EXISTENTE, no crear uno nuevo
                                    mc.sets(new_faces, e=True, forceElement=sg)
                                    print("[Bridge] Applied existing SG '{}' to {} faces on shape {}".format(
                                        sg, len(new_faces), shape.split("|")[-1]))
                                    materials_applied = True
                                except Exception as e:
                                    print("[Bridge] Failed to apply {}: {}".format(sg, e))
                            break
            
            if not materials_applied:
                print("[Bridge] WARNING: No materials were successfully applied")
                # Si no hay materiales especificos, aplicar el default
                if shapes:
                    try:
                        mc.sets(shapes[0], e=True, forceElement='initialShadingGroup')
                        print("[Bridge] Applied default shader as fallback")
                    except:
                        pass
        else:
            print("[Bridge] No material data in metadata - keeping imported shaders")
            # Si no hay datos de materiales, limpiar los shaders del FBX y aplicar default
            if shapes:
                # Verificar si el objeto importado tiene shaders custom del FBX
                has_fbx_shaders = False
                for shape in shapes:
                    sgs = mc.listConnections(shape, type='shadingEngine') or []
                    for sg in sgs:
                        if sg != 'initialShadingGroup' and any(x in sg.lower() for x in ['fbx', 'blender', '_fromblender']):
                            has_fbx_shaders = True
                            break
                
                if has_fbx_shaders:
                    print("[Bridge] Cleaning FBX shaders and applying default")
                    try:
                        mc.sets(shapes[0], e=True, forceElement='initialShadingGroup')
                    except:
                        pass

        # Restaurar light linking
        print("[Bridge] Restoring light linking...")
        
        # Usar el path esperado del JSON
        expected_path = original_name
        if mc.objExists(expected_path):
            new_obj = expected_path
            print("[Bridge] Using expected path for light linking: {}".format(new_obj))
        else:
            print("[Bridge] WARNING: Expected path {} does not exist, using: {}".format(expected_path, new_obj))
        
        try:
            linked = light_links.get("linked", [])
            unlinked = light_links.get("unlinked", [])
            
            # Filtrar solo items que son realmente luces (transforms o shapes)
            linked_lights = []
            for item in linked:
                if mc.objExists(item):
                    if mc.nodeType(item) in ['directionalLight', 'pointLight', 'spotLight', 'areaLight', 'volumeLight']:
                        # Es un shape de luz, obtener su transform
                        parent = mc.listRelatives(item, parent=True, fullPath=True)
                        if parent:
                            linked_lights.append(parent[0])
                    elif mc.objectType(item) == 'transform':
                        # Verificar si es transform de luz
                        shapes = mc.listRelatives(item, shapes=True) or []
                        if shapes and mc.nodeType(shapes[0]) in ['directionalLight', 'pointLight', 'spotLight', 'areaLight', 'volumeLight']:
                            linked_lights.append(item)
                    # Ignorar sets, grupos, y otros items
            
            # Eliminar duplicados
            linked_lights = list(set(linked_lights))
            
            print("[Bridge] {} valid lights to link (from {} items)".format(len(linked_lights), len(linked)))
            
            # Verificar que el objeto existe
            if not mc.objExists(new_obj):
                print("[Bridge] ERROR: Object does not exist for light linking")
                return "ERR|Object lost after transformations"
            
            # Obtener todas las luces de la escena (transforms)
            all_light_shapes = mc.ls(lights=True, long=True)
            all_light_transforms = []
            for shape in all_light_shapes:
                parent = mc.listRelatives(shape, parent=True, fullPath=True)
                if parent:
                    all_light_transforms.append(parent[0])
            all_light_transforms = list(set(all_light_transforms))
            
            print("[Bridge] Total light transforms in scene: {}".format(len(all_light_transforms)))
            
            # Primero romper todos los links existentes
            for light in all_light_transforms:
                try:
                    mc.lightlink(light=light, object=new_obj, b=True)
                except:
                    pass
                    
            # Luego crear los links especificados
            links_created = 0
            links_failed = 0
            
            for light in linked_lights:
                if mc.objExists(light):
                    try:
                        # Break first to ensure clean state
                        mc.lightlink(light=light, object=new_obj, b=True)
                        # Then make the link
                        mc.lightlink(light=light, object=new_obj, make=True)
                        links_created += 1
                    except Exception as e:
                        links_failed += 1
                        if links_failed <= 3:
                            print("[Bridge] Failed to link light {}: {}".format(light, e))
            
            print("[Bridge] Light linking completed:")
            print("[Bridge]   - Valid lights requested: {}".format(len(linked_lights)))
            print("[Bridge]   - Successfully linked: {}".format(links_created))
            if links_failed > 0:
                print("[Bridge]   - Failed: {}".format(links_failed))
                
        except Exception as e:
            print("[Bridge] Failed to restore light links: {}".format(e))

        # NO eliminar el objeto original aqui - ya lo borramos antes!
        # Solo seleccionar el nuevo objeto
        mc.select(new_obj, replace=True)

        print("[Bridge] Replacement completed!")
        return "OK|Replaced with {}".format(new_obj)

    except Exception as e:
        import traceback
        print("[Bridge] Error in replace_object_from_blender:")
        print(traceback.format_exc())
        return "ERR|Replace failed: {}".format(e)