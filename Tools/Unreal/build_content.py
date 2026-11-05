"""Builds code-referenced content: effect textures/materials, the marker material and UI textures.

Run headless through the editor's Python commandlet (see Docs/Production.md). Inputs are read from
$EH_WS/sourceart; re-running replaces the generated assets.
"""
import os
import unreal

WS = os.environ["EH_WS"]
SRC_VFX = os.path.join(WS, "sourceart", "vfx")
SRC_UI = os.path.join(WS, "sourceart", "ui")

tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary


def log(msg):
    unreal.log("EHBUILD " + msg)


def import_texture(path, dest, name, srgb=True, compression=None, mips=True):
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = dest
    task.destination_name = name
    task.replace_existing = True
    task.automated = True
    task.save = False
    tools.import_asset_tasks([task])
    tex = unreal.load_asset(f"{dest}/{name}")
    if tex is None:
        raise RuntimeError(f"import failed: {path}")
    tex.set_editor_property("srgb", srgb)
    if compression is not None:
        tex.set_editor_property("compression_settings", compression)
    if not mips:
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_EFFECTS if dest.startswith("/Game/VFX") else unreal.TextureGroup.TEXTUREGROUP_UI)
    eal.save_asset(tex.get_path_name(), only_if_is_dirty=False)
    return tex


def new_material(path, name):
    full = f"{path}/{name}"
    if eal.does_asset_exist(full):
        eal.delete_asset(full)
    return tools.create_asset(name, path, unreal.Material, unreal.MaterialFactoryNew())


def build_additive(default_tex):
    mat = new_material("/Game/VFX", "M_VFX_Additive")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0)
    tex.set_editor_property("parameter_name", "Tex")
    tex.set_editor_property("texture", default_tex)
    color = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -700, 300)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    inten = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 450)
    inten.set_editor_property("parameter_name", "Intensity")
    inten.set_editor_property("default_value", 1.0)
    # Shape (alpha) x colour x intensity; a soft hot core whitens the brightest part.
    m1 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, 100)
    mel.connect_material_expressions(tex, "A", m1, "A")
    mel.connect_material_expressions(color, "", m1, "B")
    m2 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 150)
    mel.connect_material_expressions(m1, "", m2, "A")
    mel.connect_material_expressions(inten, "", m2, "B")
    vc = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -400, 350)
    m3 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -50, 200)
    mel.connect_material_expressions(m2, "", m3, "A")
    mel.connect_material_expressions(vc, "", m3, "B")
    mel.connect_material_property(m3, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    log("M_VFX_Additive")


def expr(mat, cls, x, y, **props):
    e = mel.create_material_expression(mat, cls, x, y)
    for k, v in props.items():
        e.set_editor_property(k, v)
    return e


def scalar(mat, name, value, x, y):
    return expr(mat, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=value)


def vector(mat, name, value, x, y):
    return expr(mat, unreal.MaterialExpressionVectorParameter, x, y, parameter_name=name, default_value=value)


def binop(mat, cls, a, b, x, y, a_out="", b_out=""):
    e = mel.create_material_expression(mat, cls, x, y)
    mel.connect_material_expressions(a, a_out, e, "A")
    mel.connect_material_expressions(b, b_out, e, "B")
    return e


def build_fire(sheet_tex):
    """M_VFX_Fire: one flame tongue from a 4 x 4 flipbook (Frame 0-15, set per particle from its age). The density in
    the texture's alpha is mapped from the dark crimson edge colour to the hot core colour, so a flame reads as fire
    with a bright heart rather than a flat tinted card."""
    mat = new_material("/Game/VFX", "M_VFX_Fire")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    frame = scalar(mat, "Frame", 0.0, -1400, 0)
    four = expr(mat, unreal.MaterialExpressionConstant, -1400, 120, r=4.0)
    col = binop(mat, unreal.MaterialExpressionFmod, frame, four, -1200, 0)
    row = expr(mat, unreal.MaterialExpressionFloor, -1050, 120)
    div = binop(mat, unreal.MaterialExpressionDivide, frame, four, -1200, 120)
    mel.connect_material_expressions(div, "", row, "")
    cell = binop(mat, unreal.MaterialExpressionAppendVector, col, row, -900, 60)
    uv = expr(mat, unreal.MaterialExpressionTextureCoordinate, -900, -100)
    shifted = binop(mat, unreal.MaterialExpressionAdd, uv, cell, -750, 0)
    scaled = binop(mat, unreal.MaterialExpressionDivide, shifted, four, -600, 0)
    tex = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -450, 0, parameter_name="Tex", texture=sheet_tex)
    mel.connect_material_expressions(scaled, "", tex, "UVs")
    edge = vector(mat, "EdgeColor", unreal.LinearColor(0.55, 0.0, 0.03, 1), -450, 250)
    core = vector(mat, "CoreColor", unreal.LinearColor(1.0, 0.55, 0.42, 1), -450, 400)
    power = expr(mat, unreal.MaterialExpressionPower, -250, 150)
    mel.connect_material_expressions(tex, "A", power, "Base")
    exp_ = expr(mat, unreal.MaterialExpressionConstant, -400, 550, r=2.2)
    mel.connect_material_expressions(exp_, "", power, "Exp")
    lerp = expr(mat, unreal.MaterialExpressionLinearInterpolate, -100, 250)
    mel.connect_material_expressions(edge, "", lerp, "A")
    mel.connect_material_expressions(core, "", lerp, "B")
    mel.connect_material_expressions(power, "", lerp, "Alpha")
    dens = binop(mat, unreal.MaterialExpressionMultiply, lerp, tex, 50, 200, b_out="A")
    inten = scalar(mat, "Intensity", 1.0, 50, 400)
    out = binop(mat, unreal.MaterialExpressionMultiply, dens, inten, 200, 250)
    mel.connect_material_property(out, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    log("M_VFX_Fire")


def build_aura_shell(noise_tex):
    """M_VFX_AuraShell: drawn over the fighter's own mesh (overlay material) while Spirit Enhanced Strikes is up. A
    fresnel rim, so the glow sits on the silhouette and the body keeps its own colours, carried by two layers of
    noise panned upward in world space (energy streaming off the body), pushed a little out along the normals."""
    mat = new_material("/Game/VFX", "M_VFX_AuraShell")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("used_with_skeletal_mesh", True)
    fres = expr(mat, unreal.MaterialExpressionFresnel, -700, -200, exponent=4.0, base_reflect_fraction=0.0)
    wp = expr(mat, unreal.MaterialExpressionWorldPosition, -1500, 100)
    xz = expr(mat, unreal.MaterialExpressionComponentMask, -1350, 100, r=True, g=False, b=True, a=False)
    mel.connect_material_expressions(wp, "", xz, "")
    time = expr(mat, unreal.MaterialExpressionTime, -1500, 300)
    layers = []
    for i, (sx, sz, speed) in enumerate(((1.0 / 38.0, 1.0 / 95.0, 0.55), (1.0 / 17.0, 1.0 / 41.0, 1.25))):
        y = 100 + 260 * i
        sc = expr(mat, unreal.MaterialExpressionConstant2Vector, -1350, y + 120, r=sx, g=sz)
        uvw = binop(mat, unreal.MaterialExpressionMultiply, xz, sc, -1200, y)
        k = expr(mat, unreal.MaterialExpressionConstant, -1350, y + 200, r=speed)
        tk = binop(mat, unreal.MaterialExpressionMultiply, time, k, -1200, y + 160)
        zero = expr(mat, unreal.MaterialExpressionConstant, -1200, y + 230, r=0.0)
        pan = binop(mat, unreal.MaterialExpressionAppendVector, zero, tk, -1050, y + 160)
        uvp = binop(mat, unreal.MaterialExpressionAdd, uvw, pan, -900, y)
        tex = expr(mat, unreal.MaterialExpressionTextureSample, -750, y, texture=noise_tex)
        mel.connect_material_expressions(uvp, "", tex, "UVs")
        layers.append(tex)
    energy = binop(mat, unreal.MaterialExpressionMultiply, layers[0], layers[1], -550, 250, a_out="A", b_out="A")
    gain = expr(mat, unreal.MaterialExpressionConstant, -550, 400, r=4.5)
    streams = binop(mat, unreal.MaterialExpressionMultiply, energy, gain, -400, 300)
    floor_ = expr(mat, unreal.MaterialExpressionConstant, -400, 450, r=0.08)
    lit = binop(mat, unreal.MaterialExpressionAdd, streams, floor_, -250, 300)
    shell = binop(mat, unreal.MaterialExpressionMultiply, fres, lit, -100, 0)
    color = vector(mat, "Color", unreal.LinearColor(1.0, 0.72, 0.22, 1), -100, 200)
    inten = scalar(mat, "Intensity", 0.0, -100, 350)
    ci = binop(mat, unreal.MaterialExpressionMultiply, color, inten, 50, 250)
    out = binop(mat, unreal.MaterialExpressionMultiply, shell, ci, 200, 100)
    mel.connect_material_property(out, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    normal = expr(mat, unreal.MaterialExpressionVertexNormalWS, -250, 600)
    puff = scalar(mat, "Puff", 1.2, -250, 700)
    wpo = binop(mat, unreal.MaterialExpressionMultiply, normal, puff, -50, 650)
    mel.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    log("M_VFX_AuraShell")


def build_marker(ring_tex):
    mat = new_material("/Game/VFX", "M_EH_Marker")
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    tex = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -600, 0)
    tex.set_editor_property("texture", ring_tex)
    color = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -600, 250)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("default_value", unreal.LinearColor(1, 0.7, 0.3, 1))
    em = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 200)
    mel.connect_material_expressions(color, "", em, "A")
    k = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 400)
    k.set_editor_property("r", 0.9)
    mel.connect_material_expressions(k, "", em, "B")
    mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    op = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 0)
    mel.connect_material_expressions(tex, "A", op, "A")
    k2 = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 120)
    k2.set_editor_property("r", 0.55)
    mel.connect_material_expressions(k2, "", op, "B")
    mel.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    log("M_EH_Marker")


def main():
    textures = {}
    for name in ["Glow", "Streak", "Ring", "Flame", "Spark", "Splash", "Bolt", "Noise", "FireSheet"]:
        textures[name] = import_texture(os.path.join(SRC_VFX, f"T_FX_{name}.png"), "/Game/VFX", f"T_FX_{name}",
                                        srgb=False, compression=unreal.TextureCompressionSettings.TC_DEFAULT)
        log(f"T_FX_{name}")
    build_additive(textures["Glow"])
    build_fire(textures["FireSheet"])
    build_aura_shell(textures["Noise"])
    build_marker(textures["Ring"])
    title = os.path.join(SRC_UI, "T_TitleCard.png")
    # The title card is the creator's own artwork: imported once and never replaced by a rebuild.
    if os.path.exists(title) and not eal.does_asset_exist("/Game/UI/T_TitleCard"):
        import_texture(title, "/Game/UI", "T_TitleCard", srgb=True, compression=unreal.TextureCompressionSettings.TC_EDITOR_ICON, mips=False)
        log("T_TitleCard")
    log("DONE")


main()
