"""Imports the first-person hand clips (Tools/Blender/fphands/fp_anim.py) onto the realistic hands' skeleton.
Headless:
    EH_FPANIM_DIR=<dir with A_FPH_*.fbx> bin/editor_py.sh Tools/Unreal/import_fp_anims.py
Each clip is sampled at 60 fps over its exported frames, keys kept as authored, into /Game/Characters/FPHands/Anims.
"""
import os
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_checked import import_checked, require_sources, save_checked

SRC = os.environ["EH_FPANIM_DIR"]
DEST = "/Game/Characters/FPHands/Anims"


def log(msg):
    unreal.log("EHFPANIM " + msg)


def setp(obj, name, value):
    obj.set_editor_property(name, value)


def main():
    clips = ("Ready", "Guard", "Jab", "Straight", "Fireball", "IceWall")
    files = [Path(SRC) / f"A_FPH_{clip}.fbx" for clip in clips]
    require_sources(files)
    skel = unreal.load_asset("/Game/Characters/FPHands/SK_FPHands_Skeleton")
    if not isinstance(skel, unreal.Skeleton):
        raise RuntimeError("no skeleton: import the hands first (import_fp_hands.py)")
    for source in files:
        path = f"{DEST}/{source.stem}"
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            existing = unreal.load_asset(path)
            if not isinstance(existing, unreal.AnimSequence) or existing.get_editor_property("skeleton") != skel:
                raise RuntimeError(f"Expected an animation on {skel.get_path_name()} at {path}")
    for source in files:
        name = source.stem
        task = unreal.AssetImportTask()
        task.filename = str(source)
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
        anim = import_checked(task, unreal.AnimSequence, legacy_fbx=True)
        if anim.get_editor_property("skeleton") != skel:
            raise RuntimeError(f"Imported {name} on the wrong skeleton")
        save_checked(anim)
        log(f"{name} length={anim.get_editor_property('sequence_length')}")
    log(f"DONE {len(files)}/{len(clips)}")


main()
