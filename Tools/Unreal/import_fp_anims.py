"""Imports the first-person hand clips (Tools/Blender/fphands/fp_anim.py) onto the realistic hands' skeleton.
Headless:
    EH_FPANIM_DIR=<dir with A_FPH_*.fbx> bin/editor_py.sh Tools/Unreal/import_fp_anims.py
Each clip is sampled at 60 fps over its exported frames, keys kept as authored, into /Game/Characters/FPHands/Anims.
"""
import glob
import os

import unreal

SRC = os.environ["EH_FPANIM_DIR"]
DEST = "/Game/Characters/FPHands/Anims"
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary


def log(msg):
    unreal.log("EHFPANIM " + msg)


def setp(obj, name, value):
    obj.set_editor_property(name, value)


def main():
    skel = unreal.load_asset("/Game/Characters/FPHands/SK_FPHands_Skeleton")
    if skel is None:
        raise RuntimeError("no skeleton: import the hands first (import_fp_hands.py)")
    files = sorted(glob.glob(os.path.join(SRC, "A_FPH_*.fbx")))
    count = 0
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        if eal.does_asset_exist(f"{DEST}/{name}"):
            eal.delete_asset(f"{DEST}/{name}")
        task = unreal.AssetImportTask()
        task.filename = f
        task.destination_path = DEST
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        opts = unreal.FbxImportUI()
        opts.import_mesh = False
        opts.import_as_skeletal = True
        opts.import_animations = True
        opts.import_materials = False
        opts.import_textures = False
        opts.skeleton = skel
        opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
        ad = opts.anim_sequence_import_data
        setp(ad, "animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        setp(ad, "use_default_sample_rate", False)
        setp(ad, "custom_sample_rate", 60)
        setp(ad, "remove_redundant_keys", False)
        setp(ad, "import_meshes_in_bone_hierarchy", False)
        setp(ad, "convert_scene", True)
        setp(ad, "force_front_x_axis", False)
        task.options = opts
        tools.import_asset_tasks([task])
        anim = unreal.load_asset(f"{DEST}/{name}")
        if anim is None:
            log(f"FAIL {f}")
            continue
        eal.save_asset(anim.get_path_name(), only_if_is_dirty=False)
        log(f"{name} length={anim.get_editor_property('sequence_length') if hasattr(anim, 'get_editor_property') else '?'}")
        count += 1
    eal.save_directory(DEST, only_if_is_dirty=False, recursive=True)
    log(f"DONE {count}/{len(files)}")
    if count != len(files) or not files:
        raise RuntimeError(f"clip import incomplete: {count}/{len(files)}")


main()
