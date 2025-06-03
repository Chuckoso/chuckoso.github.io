# -*- coding: utf-8 -*-

import maya.standalone
maya.standalone.initialize(name='python')

import maya.cmds as mc
import os
import sys
import json

import ma_model_profiler as profiler

def import_fbx(fbx_path):
    if not mc.pluginInfo("fbxmaya", query=True, loaded=True):
        try:
            mc.loadPlugin("fbxmaya")
            print("[INFO] FBX Plugin loaded successfully.")
        except Exception as e:
            print("[ERROR] Could not load FBX plugin:", e)
            sys.exit(2)

    try:
        mc.file(fbx_path, i=True, type="FBX", ignoreVersion=True, ra=True,
                mergeNamespacesOnClash=False, options="fbx", pr=True)
        print("[INFO] FBX imported successfully.")
        return True
    except Exception as e:
        print("[ERROR] Failed to import FBX:", e)
        return False

def select_imported_meshes():
    all_meshes = mc.ls(type="mesh", long=True)
    if not all_meshes:
        print("[WARNING] No meshes found after import.")
    else:
        transforms = mc.listRelatives(all_meshes, parent=True, fullPath=True) or []
        if transforms:
            mc.select(transforms, replace=True)
            print("[INFO] Imported meshes selected.")
        else:
            print("[WARNING] No transforms found for meshes.")

def save_results_to_json(results, output_json_path):
    output = {k: {"passed": v[0], "message": v[1]} for k, v in results.items()}
    with open(output_json_path, "w") as f:
        json.dump(output, f, indent=4)

def main(args):
    if len(args) != 2:
        print("[ERROR] ma_validate_fbx.py requires exactly 2 arguments: <input_fbx> <output_json>")
        sys.exit(1)

    fbx_path = args[0]
    output_json_path = args[1]

    if not os.path.exists(fbx_path):
        print("[ERROR] FBX file does not exist:", fbx_path)
        sys.exit(1)

    if import_fbx(fbx_path):
        select_imported_meshes()

        results = profiler.run_all_checks()

        if "error" in results:
            passed, message = results["error"]
            print("[ERROR] Validation error:", message)
            sys.exit(1)

        save_results_to_json(results, output_json_path)
        print("[SUCCESS] Validation completed successfully.")
    else:
        print("[ERROR] FBX import failed.")
        sys.exit(2)
