"""Imports placeholder first-person arms (Tools/Blender/fparms/cut_fp_arms.py) onto an existing character skeleton,
using that character's materials. Headless:
    EH_FPARMS_FBX=<SK_FPArms_Wren.fbx> bin/editor_py.sh Tools/Unreal/import_fp_arms.py
"""
import os

import unreal

FBX = os.environ["EH_FPARMS_FBX"]
CHAR = os.environ.get("EH_FPARMS_CHAR", "Wren")
DEST = "/Game/Characters/FPArms"
NAME = f"SK_FPArms_{CHAR}"

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary


def log(msg):
    unreal.log("EHFPARMS " + msg)


def main():
    skel = unreal.load_asset(f"/Game/Characters/{CHAR}/SK_{CHAR}_Skeleton")
    if skel is None:
        raise RuntimeError("skeleton missing")
    task = unreal.AssetImportTask()
    task.filename = FBX
    task.destination_path = DEST
    task.destination_name = NAME
    task.replace_existing = True
    task.automated = True
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = True
    opts.import_materials = False
    opts.import_textures = False
    opts.import_animations = False
    opts.create_physics_asset = False
    opts.skeleton = skel
    opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    smd = opts.skeletal_mesh_import_data
    smd.set_editor_property("convert_scene", True)
    smd.set_editor_property("force_front_x_axis", False)
    smd.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
    task.options = opts
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(f"{DEST}/{NAME}")
    if mesh is None:
        raise RuntimeError("import failed")
    if mesh.get_editor_property("skeleton") != skel:
        raise RuntimeError("arms did not land on the character skeleton")
    mats = list(mesh.materials)
    for i, m in enumerate(mats):
        slot = str(m.material_slot_name)
        key = slot.split("_")[-1]   # M_Wren_Skin -> Skin
        mi = unreal.load_asset(f"/Game/Characters/{CHAR}/Materials/MI_{CHAR}_{key}")
        if mi is None:
            raise RuntimeError(f"no material for slot {slot}")
        m.material_interface = mi
        mats[i] = m
        log(f"slot {slot} -> MI_{CHAR}_{key}")
    mesh.materials = mats
    eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    log(f"DONE {mesh.get_path_name()} slots={len(mats)}")


main()
