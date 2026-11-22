"""Imports the placeholder wolf's parts (Tools/Blender/wolf/make_wolf.py) and its coat material /Game/Wolf/M_PH_Wolf.
Headless:
    EH_WOLF_FBX_DIR=<folder with SM_PH_Wolf_*.fbx> bin/editor_py.sh Tools/Unreal/import_wolf.py
The coat is drawn by the material from the surface's direction (dark back, pale belly; the parts' vertex colours
did not survive import), rough and matte, broken up by the effects' noise texture. A placeholder: no wolf model
exists yet.
"""
import os

import unreal

DIR = "/Game/Wolf"
FBX_DIR = os.environ["EH_WOLF_FBX_DIR"]
PARTS = ("SM_PH_Wolf_Body", "SM_PH_Wolf_Head", "SM_PH_Wolf_Leg", "SM_PH_Wolf_Tail")

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


def log(msg):
    unreal.log("EHWOLF " + msg)


def setp(obj, name, value):
    obj.set_editor_property(name, value)


def material():
    path = f"{DIR}/M_PH_Wolf"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    mat = tools.create_asset("M_PH_Wolf", DIR, unreal.Material, unreal.MaterialFactoryNew())
    # Coat: dark grey where the surface faces up (the back, the top of the head), pale where it faces down (belly,
    # chin, the insides of the legs).
    wn = mel.create_material_expression(mat, unreal.MaterialExpressionVertexNormalWS, -1300, 0)
    up = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -1150, 0)
    setp(up, "r", False); setp(up, "g", False); setp(up, "b", True)
    mel.connect_material_expressions(wn, "", up, "")
    up01 = mel.create_material_expression(mat, unreal.MaterialExpressionSmoothStep, -1000, 0)
    setp(up01, "const_min", -0.6); setp(up01, "const_max", 0.5)
    mel.connect_material_expressions(up, "", up01, "Value")
    belly = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -1000, -150)
    setp(belly, "constant", unreal.LinearColor(0.42, 0.38, 0.33, 1))
    back = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -1000, -80)
    setp(back, "constant", unreal.LinearColor(0.09, 0.085, 0.09, 1))
    vc = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -800, 0)
    mel.connect_material_expressions(belly, "", vc, "A"); mel.connect_material_expressions(back, "", vc, "B")
    mel.connect_material_expressions(up01, "", vc, "Alpha")
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1000, 250)
    setp(uv, "u_tiling", 6.0); setp(uv, "v_tiling", 6.0)
    nz = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -800, 250)
    setp(nz, "texture", unreal.load_asset("/Game/VFX/T_FX_Noise"))
    mel.connect_material_expressions(uv, "", nz, "UVs")
    # Fur-ish breakup: the coat colour times 0.75..1.15 by noise.
    rng = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -550, 250)
    a = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -700, 400); setp(a, "r", 0.75)
    b = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -700, 470); setp(b, "r", 1.15)
    mel.connect_material_expressions(a, "", rng, "A"); mel.connect_material_expressions(b, "", rng, "B")
    mel.connect_material_expressions(nz, "R", rng, "Alpha")
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -350, 0)
    mel.connect_material_expressions(vc, "", mul, "A"); mel.connect_material_expressions(rng, "", mul, "B")
    mel.connect_material_property(mul, "", MP.MP_BASE_COLOR)
    r = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -350, 200); setp(r, "r", 0.88)
    mel.connect_material_property(r, "", MP.MP_ROUGHNESS)
    sp = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -350, 300); setp(sp, "r", 0.25)
    mel.connect_material_property(sp, "", MP.MP_SPECULAR)
    mel.recompile_material(mat)
    eal.save_asset(path, only_if_is_dirty=False)
    return mat


def main():
    mat = material()
    for name in PARTS:
        # A fresh import every time: re-importing over an asset keeps its old import settings (vertex colours lost).
        if eal.does_asset_exist(f"{DIR}/{name}"):
            eal.delete_asset(f"{DIR}/{name}")
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
        tools.import_asset_tasks([task])
        mesh = unreal.load_asset(f"{DIR}/{name}")
        if mesh is None:
            raise RuntimeError(f"import failed {name}")
        mesh.set_material(0, mat)
        b = mesh.get_bounds()
        log(f"{name} vertex_colours={unreal.EditorStaticMeshLibrary.has_vertex_colors(mesh)} origin=({b.origin.x:.0f},{b.origin.y:.0f},{b.origin.z:.0f}) extent=({b.box_extent.x:.0f},{b.box_extent.y:.0f},{b.box_extent.z:.0f})")
        eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    log("DONE")


main()
