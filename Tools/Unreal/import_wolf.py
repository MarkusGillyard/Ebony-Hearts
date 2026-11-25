"""Imports the horse-sized Chapel wolf's sculpted parts (Tools/Blender/wolf/make_wolf.py), its painterly textures,
and builds its Unreal materials:
  - /Game/Wolf/M_PH_Wolf    (charcoal/silver/ash coat, dark blue-grey spine, scars, CoatTint parameter)
  - /Game/Wolf/M_Wolf_Mane  (pale-silver ceremonial mantle, ManeTint parameter)
  - /Game/Wolf/M_Wolf_Leg   (fur transitioning to dark glossy wet paws, CoatTint parameter)
  - /Game/Wolf/M_Wolf_Eyes  (pale amber eyes with subtle moonlight gleam)

Headless:
    EH_WOLF_FBX_DIR=/home/cinqic/EH-Proto/sourceart/wolf bin/editor_py.sh Tools/Unreal/import_wolf.py
"""
import os
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_checked import import_checked, require_sources, save_checked

DIR = "/Game/Wolf"
FBX_DIR = os.environ["EH_WOLF_FBX_DIR"]
PARTS = ("SM_PH_Wolf_Body", "SM_PH_Wolf_Mane", "SM_PH_Wolf_Head", "SM_PH_Wolf_Leg", "SM_PH_Wolf_Tail")
TEXTURES = (
    ("T_Wolf_Coat_BC", True, unreal.TextureCompressionSettings.TC_DEFAULT),
    ("T_Wolf_Coat_R", False, unreal.TextureCompressionSettings.TC_MASKS),
    ("T_Wolf_Coat_N", False, unreal.TextureCompressionSettings.TC_NORMALMAP),
    ("T_Wolf_Mane_BC", True, unreal.TextureCompressionSettings.TC_DEFAULT),
    ("T_Wolf_Mane_R", False, unreal.TextureCompressionSettings.TC_MASKS),
    ("T_Wolf_Mane_N", False, unreal.TextureCompressionSettings.TC_NORMALMAP),
    ("T_Wolf_Leg_BC", True, unreal.TextureCompressionSettings.TC_DEFAULT),
    ("T_Wolf_Leg_R", False, unreal.TextureCompressionSettings.TC_MASKS),
)

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


def log(msg):
    unreal.log("EHWOLF " + msg)


def setp(obj, name, value):
    obj.set_editor_property(name, value)


def import_textures():
    out = {}
    for name, srgb, comp in TEXTURES:
        task = unreal.AssetImportTask()
        task.filename = os.path.join(FBX_DIR, name + ".png")
        task.destination_path = DIR
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        tex = import_checked(task, unreal.Texture2D)
        setp(tex, "srgb", srgb)
        setp(tex, "compression_settings", comp)
        save_checked(tex)
        out[name] = tex
        log(f"texture {name} srgb={srgb}")
    return out


def get_material(name):
    path = f"{DIR}/{name}"
    if eal.does_asset_exist(path):
        mat = unreal.load_asset(path)
        if not isinstance(mat, unreal.Material):
            raise RuntimeError(f"Expected a Material at {path}")
        mel.delete_all_material_expressions(mat)
        return mat
    mat = tools.create_asset(name, DIR, unreal.Material, unreal.MaterialFactoryNew())
    if not isinstance(mat, unreal.Material):
        raise RuntimeError(f"Could not create {path}")
    return mat


def make_pbr_material(name, bc_tex, r_tex, n_tex, tint_param, default_tint, spec=0.28):
    mat = get_material(name)

    bc = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -600, -100)
    setp(bc, "texture", bc_tex)
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -600, -320)
    setp(tint, "parameter_name", tint_param)
    setp(tint, "default_value", unreal.LinearColor(*default_tint))
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -320, -150)
    mel.connect_material_expressions(bc, "RGB", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", MP.MP_BASE_COLOR)

    r = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -600, 140)
    setp(r, "texture", r_tex)
    setp(r, "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    mel.connect_material_property(r, "R", MP.MP_ROUGHNESS)

    sp = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -320, 220)
    setp(sp, "r", spec)
    mel.connect_material_property(sp, "", MP.MP_SPECULAR)

    if n_tex is not None:
        n = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -600, 380)
        setp(n, "texture", n_tex)
        setp(n, "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        mel.connect_material_property(n, "", MP.MP_NORMAL)

    mel.recompile_material(mat)
    save_checked(mat)
    return mat


def make_eye_material():
    mat = get_material("M_Wolf_Eyes")
    base = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -500, -100)
    setp(base, "constant", unreal.LinearColor(0.88, 0.62, 0.20, 1.0))
    mel.connect_material_property(base, "", MP.MP_BASE_COLOR)
    em_mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -260, 40)
    em_str = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 120)
    setp(em_str, "r", 2.8)
    mel.connect_material_expressions(base, "", em_mul, "A")
    mel.connect_material_expressions(em_str, "", em_mul, "B")
    mel.connect_material_property(em_mul, "", MP.MP_EMISSIVE_COLOR)
    r = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -320, 240)
    setp(r, "r", 0.08)
    mel.connect_material_property(r, "", MP.MP_ROUGHNESS)
    sp = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -320, 320)
    setp(sp, "r", 0.75)
    mel.connect_material_property(sp, "", MP.MP_SPECULAR)
    mel.recompile_material(mat)
    save_checked(mat)
    return mat


def main():
    source = Path(FBX_DIR)
    require_sources([source / f"{name}.fbx" for name in PARTS] +
                    [source / f"{name}.png" for name, _, _ in TEXTURES])
    tex = import_textures()
    m_coat = make_pbr_material("M_PH_Wolf", tex["T_Wolf_Coat_BC"], tex["T_Wolf_Coat_R"], tex["T_Wolf_Coat_N"],
                               "CoatTint", (1.0, 1.0, 1.0, 1.0), spec=0.25)
    m_mane = make_pbr_material("M_Wolf_Mane", tex["T_Wolf_Mane_BC"], tex["T_Wolf_Mane_R"], tex["T_Wolf_Mane_N"],
                               "ManeTint", (1.0, 1.0, 1.0, 1.0), spec=0.32)
    m_leg = make_pbr_material("M_Wolf_Leg", tex["T_Wolf_Leg_BC"], tex["T_Wolf_Leg_R"], tex["T_Wolf_Coat_N"],
                              "CoatTint", (1.0, 1.0, 1.0, 1.0), spec=0.45)
    m_eyes = make_eye_material()

    part_mats = {
        "SM_PH_Wolf_Body": [m_coat],
        "SM_PH_Wolf_Mane": [m_mane],
        "SM_PH_Wolf_Head": [m_coat, m_eyes],
        "SM_PH_Wolf_Leg": [m_leg],
        "SM_PH_Wolf_Tail": [m_coat],
    }

    for name in PARTS:
        task = unreal.AssetImportTask()
        task.filename = os.path.join(FBX_DIR, name + ".fbx")
        task.destination_path = DIR
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        opts = unreal.FbxImportUI()
        opts.import_mesh = True; opts.import_materials = False; opts.import_textures = False; opts.import_as_skeletal = False
        smd = opts.static_mesh_import_data
        smd.combine_meshes = True; smd.generate_lightmap_u_vs = False; smd.auto_generate_collision = False
        smd.import_uniform_scale = 1.0
        smd.set_editor_property("normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        smd.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
        smd.set_editor_property("convert_scene", True)
        smd.set_editor_property("force_front_x_axis", False)
        task.options = opts
        mesh = import_checked(task, unreal.StaticMesh, legacy_fbx=True)
        if len(mesh.static_materials) != len(part_mats[name]):
            raise RuntimeError(f"{name} has {len(mesh.static_materials)} material slots; expected {len(part_mats[name])}")
        for idx, mat in enumerate(part_mats[name]):
            mesh.set_material(idx, mat)
        b = mesh.get_bounds()
        log(f"{name} mats={len(mesh.static_materials)} origin=({b.origin.x:.0f},{b.origin.y:.0f},{b.origin.z:.0f}) extent=({b.box_extent.x:.0f},{b.box_extent.y:.0f},{b.box_extent.z:.0f})")
        save_checked(mesh)
    log("DONE")


main()
