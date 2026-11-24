"""Imports the first-person hands (Tools/Blender/fphands/build_fp_hands.py) as a skeletal mesh on their own skeleton,
with a plain skin material until the creator paints one. Headless:
    EH_FPHANDS_FBX=<SK_FPHands.fbx> bin/editor_py.sh Tools/Unreal/import_fp_hands.py
"""
import os
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_checked import import_checked, require_sources, save_checked

FBX = os.environ["EH_FPHANDS_FBX"]
DEST = "/Game/Characters/FPHands"
NAME = "SK_FPHands"
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


def log(msg):
    unreal.log("EHFPHANDS " + msg)


def setp(obj, name, value):
    obj.set_editor_property(name, value)


def skin_material(noise):
    path = f"{DEST}/M_FPHands_Skin"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mat = unreal.load_asset(path)
        if not isinstance(mat, unreal.Material):
            raise RuntimeError(f"Expected a Material at {path}")
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset("M_FPHands_Skin", DEST, unreal.Material, unreal.MaterialFactoryNew())
        if not isinstance(mat, unreal.Material):
            raise RuntimeError(f"Could not create {path}")
    # A warm, slightly varied skin with soft light bleeding through thin parts (subsurface), no texture yet.
    base = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -900, -100)
    setp(base, "parameter_name", "SkinColor")
    setp(base, "default_value", unreal.LinearColor(0.42, 0.27, 0.20, 1))
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1100, 150)
    setp(uv, "u_tiling", 9.0)
    setp(uv, "v_tiling", 9.0)
    nz = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -900, 150)
    setp(nz, "texture", noise)
    mel.connect_material_expressions(uv, "", nz, "UVs")
    rng = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -650, 150)
    a = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -800, 300)
    setp(a, "r", 0.90)
    b = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -800, 370)
    setp(b, "r", 1.06)
    mel.connect_material_expressions(a, "", rng, "A")
    mel.connect_material_expressions(b, "", rng, "B")
    mel.connect_material_expressions(nz, "R", rng, "Alpha")
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -450, 0)
    mel.connect_material_expressions(base, "", mul, "A")
    mel.connect_material_expressions(rng, "", mul, "B")
    mel.connect_material_property(mul, "", MP.MP_BASE_COLOR)
    r = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -450, 200)
    setp(r, "parameter_name", "Roughness")
    setp(r, "default_value", 0.58)
    mel.connect_material_property(r, "", MP.MP_ROUGHNESS)
    sp = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -450, 300)
    setp(sp, "r", 0.35)
    mel.connect_material_property(sp, "", MP.MP_SPECULAR)
    setp(mat, "shading_model", unreal.MaterialShadingModel.MSM_SUBSURFACE)
    ss = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -450, 400)
    setp(ss, "constant", unreal.LinearColor(0.55, 0.12, 0.07, 1))
    mel.connect_material_property(ss, "", MP.MP_SUBSURFACE_COLOR)
    op = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -450, 500)
    setp(op, "r", 0.35)
    mel.connect_material_property(op, "", MP.MP_OPACITY)
    setp(mat, "used_with_skeletal_mesh", True)
    mel.recompile_material(mat)
    save_checked(mat)
    return mat


def main():
    require_sources([FBX])
    noise = unreal.load_asset("/Game/VFX/T_FX_Noise")
    if not isinstance(noise, unreal.Texture2D):
        raise RuntimeError("Missing first-person hand texture /Game/VFX/T_FX_Noise")
    skeleton_path = f"{DEST}/{NAME}_Skeleton"
    skeleton = None
    if unreal.EditorAssetLibrary.does_asset_exist(skeleton_path):
        skeleton = unreal.load_asset(skeleton_path)
        if not isinstance(skeleton, unreal.Skeleton):
            raise RuntimeError(f"Expected a Skeleton at {skeleton_path}")
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
    if skeleton is not None:
        opts.skeleton = skeleton
    opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    smd = opts.skeletal_mesh_import_data
    smd.set_editor_property("convert_scene", True)
    smd.set_editor_property("force_front_x_axis", False)
    smd.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS)
    task.options = opts
    mesh = import_checked(task, unreal.SkeletalMesh, legacy_fbx=True)
    skel = mesh.get_editor_property("skeleton")
    if not isinstance(skel, unreal.Skeleton) or skel.get_path_name() != f"{skeleton_path}.{NAME}_Skeleton":
        raise RuntimeError(f"Unexpected skeleton on {mesh.get_path_name()}")
    mats = list(mesh.materials)
    if len(mats) != 1:
        raise RuntimeError(f"Expected one material slot on {mesh.get_path_name()}, got {len(mats)}")
    slot = mats[0]
    slot.material_interface = skin_material(noise)
    mesh.materials = [slot]
    save_checked(skel)
    save_checked(mesh)
    log(f"DONE {mesh.get_path_name()} skeleton={skel.get_path_name()} slots={len(mats)}")


main()
