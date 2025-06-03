# -*- coding: utf-8 -*-

import maya.cmds as mc

# Configurable prefixes and suffixes
REQUIRED_PREFIXES = ['geo_', 'mesh_']
REQUIRED_SUFFIXES = ['_geo', '_mesh']

def check_instances(meshes):
    problematic = []
    for mesh in meshes:
        paths = mc.ls(mesh, long=True, dag=True)
        if len(paths) > 1:
            problematic.append(mesh)
    if not problematic:
        return True, "No instances"
    return False, "Instances in model: {}".format(", ".join(problematic))

def check_ngons(meshes):
    ngons = []
    for mesh in meshes:
        face_count = mc.polyEvaluate(mesh, face=True)
        for i in range(face_count):
            try:
                info = mc.polyInfo("{}.f[{}]".format(mesh, i), faceToVertex=True)
                if info:
                    vtx_count = len(info[0].split()) - 2
                    if vtx_count > 4:
                        ngons.append("{}.f[{}]".format(mesh, i))
            except:
                continue
    if not ngons:
        return True, "OK Passed"
    return False, "Fail: {} ngons found".format(len(ngons))

def check_namespaces(selection):
    namespaces = set()
    for node in selection:
        if ":" in node:
            namespaces.add(node.split(":"[0]))
    if not namespaces:
        return True, "OK Passed"
    return False, "Namespaces found: {}".format(", ".join(namespaces))

def check_polycount(meshes):
    total_faces = 0
    total_tris = 0
    for mesh in meshes:
        total_faces += mc.polyEvaluate(mesh, face=True)
        total_tris += mc.polyEvaluate(mesh, triangle=True)
    return True, "Polygons: {}, Triangles: {}".format(total_faces, total_tris)

def check_hidden_meshes(meshes):
    hidden = []
    for mesh in meshes:
        transform = mc.listRelatives(mesh, parent=True, fullPath=True)[0]
        if not mc.getAttr(transform + ".visibility"):
            hidden.append(transform)
    if not hidden:
        return True, "OK Passed"
    return False, "Fail: Hidden meshes found"

def check_naming(selection):
    bad_names = []
    for t in selection:
        name = t.split("|")[-1]
        if not any(name.startswith(prefix) for prefix in REQUIRED_PREFIXES) or not any(name.endswith(suffix) for suffix in REQUIRED_SUFFIXES):
            bad_names.append(name)
    if not bad_names:
        return True, "OK Passed"
    return False, "Fail: Invalid names: {}".format(", ".join(bad_names))

def check_history(selection):
    with_history = []
    ignored_types = ['transform', 'shadingEngine', 'materialInfo', 'groupId', 'groupParts', 'objectSet', 'polySurfaceShape']

    for node in selection:
        history = mc.listHistory(node, pruneDagObjects=True) or []
        construction = [h for h in history if mc.nodeType(h) not in ignored_types]
        if construction:
            with_history.append(node)

    if not with_history:
        return True, "OK Passed"
    return False, "Fail: History found in: {}".format(", ".join(with_history))

def check_multiple_materials(meshes):
    problematic = []
    for mesh in meshes:
        shading_grps = mc.listConnections(mesh, type='shadingEngine') or []
        if len(shading_grps) > 2:
            problematic.append(mesh)
    if not problematic:
        return True, "OK Passed"
    return False, "Fail: Meshes with >2 materials: {}".format(", ".join(problematic))

def check_duplicate_materials():
    materials = mc.ls(materials=True)
    seen = {}
    duplicates = []
    for mat in materials:
        name = mat.split("|")[-1]
        if name in seen:
            duplicates.append(mat)
        else:
            seen[name] = True
    if not duplicates:
        return True, "OK Passed"
    return False, "Fail: Duplicate materials: {}".format(", ".join(duplicates))

def check_transform_zero(selection):
    non_zero = []
    for t in selection:
        for attr in ["translate", "rotate"]:
            for axis in ["X", "Y", "Z"]:
                val = mc.getAttr("{}.{}{}".format(t, attr, axis))
                if abs(val) > 1e-4:
                    non_zero.append(t)
                    break
        scale_vals = [mc.getAttr("{}.scale{}".format(t, axis)) for axis in ["X", "Y", "Z"]]
        if any(abs(s - 1) > 1e-4 for s in scale_vals):
            non_zero.append(t)
    if not non_zero:
        return True, "OK Passed"
    return False, "Fail: Transforms not reset: {}".format(", ".join(set(non_zero)))

def run_all_checks():
    selection = mc.ls(sl=True, long=True)
    if not selection:
        return {"error": (False, "Nothing selected! Please select a model to check.")}

    meshes = mc.listRelatives(selection, allDescendents=True, type='mesh', fullPath=True) or []
    meshes = list(set(meshes))

    return {
        "instances": check_instances(meshes),
        "ngons": check_ngons(meshes),
        "namespaces": check_namespaces(selection),
        "polycount": check_polycount(meshes),
        "hidden_meshes": check_hidden_meshes(meshes),
        "naming": check_naming(selection),
        "history": check_history(selection),
        "multiple_materials": check_multiple_materials(meshes),
        "duplicate_materials": check_duplicate_materials(),
        "transforms_reset": check_transform_zero(selection)
    }
