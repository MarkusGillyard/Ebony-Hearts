"""Placeholder ice for the Ice Wall: imports the shard meshes made by Tools/Blender/magic/make_ice.py and builds the ice
material /Game/Magic/M_PH_Ice. Headless:
    EH_ICE_FBX_DIR=<folder with SM_PH_Ice*.fbx> bin/editor_py.sh Tools/Unreal/make_magic_materials.py

The material is clear blue ice that bends what is behind it (refraction from a rippled normal), lit per pixel so the
facets catch the candles and the moon, deep blue in its thickness, near clear face on and denser at grazing angles,
and frosted white where the mesh's vertex colour marks frost (the mound and the shards' feet) and in streaks of the
effects' noise texture. "Opacity" and "Glow" scale it per use (the frozen water is a thinner sheet than the wall).
Final ice is the creator's to author.
"""
import os

import unreal

DIR = "/Game/Magic"
NAME = "M_PH_Ice"
FBX_DIR = os.environ.get("EH_ICE_FBX_DIR", "")
MESHES = ("SM_PH_IceWall", "SM_PH_IceSheet", "SM_PH_IceCuff")

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


def log(msg):
    unreal.log("EHMAGIC " + msg)


def setp(obj, name, value):
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception as exc:
        log(f"WARN {type(obj).__name__}.{name}: {exc}")
        return False


def expr(mat, cls, x, y, **props):
    e = mel.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        setp(e, k, v)
    return e


def const3(mat, rgb, x, y):
    return expr(mat, unreal.MaterialExpressionConstant3Vector, x, y, constant=unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1))


def const(mat, v, x, y):
    return expr(mat, unreal.MaterialExpressionConstant, x, y, r=v)


def link(a, a_out, b, b_in):
    mel.connect_material_expressions(a, a_out, b, b_in)


def lerp(mat, a, b, alpha, x, y):
    e = expr(mat, unreal.MaterialExpressionLinearInterpolate, x, y)
    link(a, "", e, "A")
    link(b, "", e, "B")
    link(alpha, "", e, "Alpha")
    return e


def mul(mat, a, b, x, y):
    e = expr(mat, unreal.MaterialExpressionMultiply, x, y)
    link(a, "", e, "A")
    link(b, "", e, "B")
    return e


def enum_value(enum, *names):
    for n in names:
        if hasattr(enum, n):
            return getattr(enum, n)
    log(f"WARN none of {names} in {enum}")
    return None


def build_material():
    path = f"{DIR}/{NAME}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    mat = tools.create_asset(NAME, DIR, unreal.Material, unreal.MaterialFactoryNew())
    setp(mat, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    lm = enum_value(unreal.TranslucencyLightingMode, "TLM_SURFACE_PER_PIXEL_LIGHTING", "TLM_SURFACE")
    if lm is not None:
        setp(mat, "translucency_lighting_mode", lm)
    rm = enum_value(unreal.RefractionMode, "RM_PIXEL_NORMAL_OFFSET", "RM_INDEX_OF_REFRACTION")
    if rm is not None:
        setp(mat, "refraction_method", rm)
    setp(mat, "two_sided", False)

    # Ripples inside the ice: the Chapel's water normal map on the mesh's box-projected UVs.
    water_n = unreal.load_asset("/Game/Chapel/Textures/T_Water_N")
    noise = unreal.load_asset("/Game/VFX/T_FX_Noise")
    uv = expr(mat, unreal.MaterialExpressionTextureCoordinate, -1700, 400, u_tiling=1.3, v_tiling=1.3)
    uv2 = expr(mat, unreal.MaterialExpressionTextureCoordinate, -1700, 560, u_tiling=0.45, v_tiling=0.7)
    n1 = expr(mat, unreal.MaterialExpressionTextureSample, -1500, 400, texture=water_n,
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    link(uv, "", n1, "UVs")
    flatten = expr(mat, unreal.MaterialExpressionLinearInterpolate, -1250, 400)
    link(const3(mat, (0, 0, 1), -1400, 330), "", flatten, "A")
    link(n1, "RGB", flatten, "B")
    link(const(mat, 0.55, -1400, 480), "", flatten, "Alpha")
    mel.connect_material_property(flatten, "", MP.MP_NORMAL)

    # Frost: the mesh's frost colour broken up by noise, plus sharp noise streaks over the whole surface.
    vc = expr(mat, unreal.MaterialExpressionVertexColor, -1500, -400)
    nz = expr(mat, unreal.MaterialExpressionTextureSample, -1500, 640, texture=noise)
    link(uv2, "", nz, "UVs")
    nz_sharp = expr(mat, unreal.MaterialExpressionPower, -1300, 640, const_exponent=2.0)
    link(nz, "R", nz_sharp, "Base")
    frost_a = expr(mat, unreal.MaterialExpressionMultiply, -1250, -480)
    link(vc, "R", frost_a, "A")
    link(nz, "R", frost_a, "B")
    frost_a2 = mul(mat, frost_a, const(mat, 1.6, -1400, -560), -1100, -520)
    streak = mul(mat, nz_sharp, const(mat, 0.9, -1300, 720), -1150, 680)
    # Frost also settles on facets that face up (the mound's top, the sheet), as rime does.
    wn = expr(mat, unreal.MaterialExpressionVertexNormalWS, -1500, -700)
    up = expr(mat, unreal.MaterialExpressionComponentMask, -1350, -700, r=False, g=False, b=True, a=False)
    link(wn, "", up, "")
    up_s = expr(mat, unreal.MaterialExpressionSmoothStep, -1200, -700, const_min=0.55, const_max=0.95)
    link(up, "", up_s, "Value")
    up_n = mul(mat, up_s, nz, -1050, -700)
    frost_c = expr(mat, unreal.MaterialExpressionAdd, -960, -600)
    link(frost_a2, "", frost_c, "A")
    link(up_n, "", frost_c, "B")
    frost_b = expr(mat, unreal.MaterialExpressionAdd, -960, -440)
    link(frost_c, "", frost_b, "A")
    link(streak, "", frost_b, "B")
    frost_raw = expr(mat, unreal.MaterialExpressionSaturate, -820, -440)
    link(frost_b, "", frost_raw, "")
    # "Wet" (0 ice .. 1 water): melting, the frost goes first and the ice turns to clear, dark, glassy water.
    wet = expr(mat, unreal.MaterialExpressionScalarParameter, -820, -760, parameter_name="Wet", default_value=0.0)
    dry = expr(mat, unreal.MaterialExpressionOneMinus, -700, -760)
    link(wet, "", dry, "")
    frost = mul(mat, frost_raw, dry, -700, -440)

    fres = expr(mat, unreal.MaterialExpressionFresnel, -1250, 0, exponent=3.0, base_reflect_fraction=0.04)

    # Colour: deep blue body, paler cyan at the edges, white frost.
    deep = const3(mat, (0.03, 0.13, 0.24), -900, -300)
    edge = const3(mat, (0.28, 0.52, 0.7), -900, -220)
    body = lerp(mat, deep, edge, fres, -700, -260)
    frost_col = const3(mat, (0.85, 0.92, 0.97), -700, -160)
    base_ice = lerp(mat, body, frost_col, frost, -500, -220)
    base = lerp(mat, base_ice, const3(mat, (0.012, 0.025, 0.04), -500, -300), wet, -360, -240)
    mel.connect_material_property(base, "", MP.MP_BASE_COLOR)
    rough_ice = lerp(mat, const(mat, 0.03, -700, -60), const(mat, 0.55, -700, 0), frost, -500, -40)
    rough = lerp(mat, rough_ice, const(mat, 0.015, -500, 0), wet, -360, -40)
    mel.connect_material_property(rough, "", MP.MP_ROUGHNESS)
    mel.connect_material_property(const(mat, 1.0, -500, 40), "", MP.MP_SPECULAR)

    # Opacity: clear face on (0.12), dense at the rims, near solid where frosted; scaled by "Opacity".
    op_edge = lerp(mat, const(mat, 0.12, -900, 120), const(mat, 0.8, -900, 180), fres, -700, 140)
    op_frost = lerp(mat, op_edge, const(mat, 0.92, -700, 230), frost, -500, 160)
    op_param = expr(mat, unreal.MaterialExpressionScalarParameter, -500, 260, parameter_name="Opacity", default_value=1.0)
    op_wet = lerp(mat, op_frost, mul(mat, op_edge, const(mat, 0.55, -700, 290), -560, 300), wet, -420, 200)
    op = mul(mat, op_wet, op_param, -320, 180)
    sat = expr(mat, unreal.MaterialExpressionSaturate, -200, 180)
    link(op, "", sat, "")
    mel.connect_material_property(sat, "", MP.MP_OPACITY)

    # Refraction: ice bends light a little (index about 1.31), more at the rims.
    refr = lerp(mat, const(mat, 1.12, -700, 320), const(mat, 1.31, -700, 380), fres, -500, 340)
    mel.connect_material_property(refr, "", MP.MP_REFRACTION)

    # A faint cold glow at the rims, so the ice reads in the dark nave; scaled by "Glow".
    glow_param = expr(mat, unreal.MaterialExpressionScalarParameter, -700, -620, parameter_name="Glow", default_value=1.0)
    # A cold glow: a little everywhere (the ice holds the spell's light), more at the rims and in the frost.
    rim_a = expr(mat, unreal.MaterialExpressionAdd, -900, -500)
    link(fres, "", rim_a, "A")
    link(const(mat, 0.08, -1050, -520), "", rim_a, "B")
    rim_b = expr(mat, unreal.MaterialExpressionAdd, -800, -500)
    link(rim_a, "", rim_b, "A")
    link(mul(mat, frost, const(mat, 0.6, -1000, -460), -900, -440), "", rim_b, "B")
    rim = mul(mat, const3(mat, (0.02, 0.075, 0.14), -900, -560), rim_b, -700, -540)
    glow = mul(mat, rim, glow_param, -500, -560)
    mel.connect_material_property(glow, "", MP.MP_EMISSIVE_COLOR)

    mel.recompile_material(mat)
    eal.save_asset(path, only_if_is_dirty=False)
    log(f"material {path}")
    return mat


def import_meshes(mat):
    for name in MESHES:
        fbx = os.path.join(FBX_DIR, name + ".fbx")
        if not os.path.exists(fbx):
            raise RuntimeError(f"missing {fbx}")
        task = unreal.AssetImportTask()
        task.filename = fbx
        task.destination_path = DIR
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        opts = unreal.FbxImportUI()
        opts.import_mesh = True
        opts.import_materials = False
        opts.import_textures = False
        opts.import_as_skeletal = False
        smd = opts.static_mesh_import_data
        smd.combine_meshes = True
        smd.generate_lightmap_u_vs = False
        smd.auto_generate_collision = False
        smd.import_uniform_scale = 1.0
        setp(smd, "normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        setp(smd, "vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
        setp(smd, "convert_scene", True)
        setp(smd, "force_front_x_axis", False)
        task.options = opts
        tools.import_asset_tasks([task])
        mesh = unreal.load_asset(f"{DIR}/{name}")
        if mesh is None:
            raise RuntimeError(f"import failed {name}")
        mesh.set_material(0, mat)
        b = mesh.get_bounds()
        log(f"mesh {name} origin={b.origin} extent={b.box_extent}")
        eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)


def main():
    mat = build_material()
    if FBX_DIR:
        import_meshes(mat)
    log("DONE")


main()
