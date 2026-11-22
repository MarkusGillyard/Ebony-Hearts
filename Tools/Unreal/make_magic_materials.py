"""Creates the placeholder material for the Ice Wall and frozen water: /Game/Magic/M_PH_Ice. Headless:
    bin/editor_py.sh Tools/Unreal/make_magic_materials.py
Pale translucent blue, glossy, thicker-looking at grazing angles and faintly mottled by the effects' noise texture, with
a small cold glow so it reads in the dark nave. Final ice is the creator's to author.
"""
import unreal

DIR = "/Game/Magic"
NAME = "M_PH_Ice"

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


def log(msg):
    unreal.log("EHMAGIC " + msg)


def setp(obj, name, value):
    obj.set_editor_property(name, value)


def const3(mat, rgb, x, y):
    e = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, x, y)
    setp(e, "constant", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1))
    return e


def const(mat, v, x, y):
    e = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, x, y)
    setp(e, "r", v)
    return e


def main():
    path = f"{DIR}/{NAME}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    mat = tools.create_asset(NAME, DIR, unreal.Material, unreal.MaterialFactoryNew())
    setp(mat, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    setp(mat, "translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    setp(mat, "two_sided", False)

    # Mottling: the effects' noise texture projected along world XY and XZ at a 1.5 m scale.
    noise_tex = unreal.load_asset("/Game/VFX/T_FX_Noise")
    wpos = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -1400, 200)
    div = mel.create_material_expression(mat, unreal.MaterialExpressionDivide, -1250, 200)
    mel.connect_material_expressions(wpos, "", div, "A")
    setp(div, "const_b", 150.0)
    xz = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -1100, 200)
    setp(xz, "r", True); setp(xz, "g", False); setp(xz, "b", True)
    mel.connect_material_expressions(div, "", xz, "")
    yz = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -1100, 320)
    setp(yz, "r", False); setp(yz, "g", True); setp(yz, "b", True)
    mel.connect_material_expressions(div, "", yz, "")
    s1 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -950, 200)
    setp(s1, "texture", noise_tex)
    mel.connect_material_expressions(xz, "", s1, "UVs")
    s2 = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -950, 380)
    setp(s2, "texture", noise_tex)
    mel.connect_material_expressions(yz, "", s2, "UVs")
    avg = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -760, 280)
    mel.connect_material_expressions(s1, "R", avg, "A")
    mel.connect_material_expressions(s2, "R", avg, "B")
    half = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -640, 280)
    mel.connect_material_expressions(avg, "", half, "A")
    setp(half, "const_b", 0.5)

    fres = mel.create_material_expression(mat, unreal.MaterialExpressionFresnel, -760, 0)
    setp(fres, "exponent", 2.5)
    setp(fres, "base_reflect_fraction", 0.15)

    # Base colour: deep blue in the body, paler where the mottling is light.
    deep = const3(mat, (0.05, 0.14, 0.26), -520, -300)
    pale = const3(mat, (0.32, 0.52, 0.70), -520, -200)
    base = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -300, -250)
    mel.connect_material_expressions(deep, "", base, "A")
    mel.connect_material_expressions(pale, "", base, "B")
    mel.connect_material_expressions(half, "", base, "Alpha")
    mel.connect_material_property(base, "", MP.MP_BASE_COLOR)
    mel.connect_material_property(const(mat, 0.08, -300, -100), "", MP.MP_ROUGHNESS)
    mel.connect_material_property(const(mat, 1.0, -300, -40), "", MP.MP_SPECULAR)

    # Opacity: 0.3 face on, near solid at the edges, a little denser where the mottling is light.
    op1 = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -300, 60)
    mel.connect_material_expressions(const(mat, 0.3, -520, 20), "", op1, "A")
    mel.connect_material_expressions(const(mat, 0.92, -520, 80), "", op1, "B")
    mel.connect_material_expressions(fres, "", op1, "Alpha")
    op2 = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -160, 60)
    mel.connect_material_expressions(op1, "", op2, "A")
    opn = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 160)
    mel.connect_material_expressions(half, "", opn, "A")
    setp(opn, "const_b", 0.15)
    mel.connect_material_expressions(opn, "", op2, "B")
    # "Opacity" scales it per use (the frozen water is a thinner sheet than the wall).
    op_param = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -160, 200)
    setp(op_param, "parameter_name", "Opacity")
    setp(op_param, "default_value", 1.0)
    op3 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -40, 60)
    mel.connect_material_expressions(op2, "", op3, "A")
    mel.connect_material_expressions(op_param, "", op3, "B")
    mel.connect_material_property(op3, "", MP.MP_OPACITY)

    # A faint cold glow, stronger at the rim.
    glow = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -160, -160)
    mel.connect_material_expressions(const3(mat, (0.03, 0.09, 0.17), -300, -180), "", glow, "A")
    rim = mel.create_material_expression(mat, unreal.MaterialExpressionAdd, -300, -60)
    mel.connect_material_expressions(fres, "", rim, "A")
    setp(rim, "const_b", 0.35)
    mel.connect_material_expressions(rim, "", glow, "B")
    glow_param = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -160, -240)
    setp(glow_param, "parameter_name", "Glow")
    setp(glow_param, "default_value", 1.0)
    glow2 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -40, -160)
    mel.connect_material_expressions(glow, "", glow2, "A")
    mel.connect_material_expressions(glow_param, "", glow2, "B")
    mel.connect_material_property(glow2, "", MP.MP_EMISSIVE_COLOR)

    mel.recompile_material(mat)
    eal.save_asset(path, only_if_is_dirty=False)
    log(f"DONE {path}")


main()
