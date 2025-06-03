# -*- coding: ascii -*-
# ma_bridge_session.py
# Modulo central para identificar sesiones y estandarizar paths temporales entre Maya y Blender.

import os
import maya.cmds as mc

# Carpeta temporal compartida entre Maya y Blender
TEMP_DIR = "C:/Telltale/temp"

def get_scene_name():
    #Devuelve el nombre base de la escena de Maya, sin extension.
    scene = mc.file(q=True, sn=True, shortName=True)
    return os.path.splitext(scene)[0] if scene else "unsaved"

def get_object_name():
    #Devuelve el nombre corto del primer objeto seleccionado.
    selection = mc.ls(selection=True, long=True)
    if not selection:
        return None
    return selection[0].split("|")[-1]

def get_session_name(scene, obj):
    #Genera un nombre de sesion unico por escena y objeto.
    return "{}_{}".format(scene, obj)

def get_temp_fbx_path(scene, obj, direction="toBlender"):
    #Devuelve el path del FBX temporal para esta sesion.
    base = get_session_name(scene, obj)
    return os.path.join(TEMP_DIR, "{}_{}.fbx".format(base, direction))

def get_temp_json_path(scene, obj, direction="toBlender"):
    #Devuelve el path del JSON de metadatos para esta sesion.
    base = get_session_name(scene, obj)
    return os.path.join(TEMP_DIR, "{}_{}_meta.json".format(base, direction))
