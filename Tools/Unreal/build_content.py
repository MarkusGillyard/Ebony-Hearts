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
    for name in ["Glow", "Streak", "Ring", "Flame", "Spark", "Splash"]:
        textures[name] = import_texture(os.path.join(SRC_VFX, f"T_FX_{name}.png"), "/Game/VFX", f"T_FX_{name}",
                                        srgb=False, compression=unreal.TextureCompressionSettings.TC_DEFAULT)
        log(f"T_FX_{name}")
    build_additive(textures["Glow"])
    build_marker(textures["Ring"])
    title = os.path.join(SRC_UI, "T_TitleCard.png")
    if os.path.exists(title):
        import_texture(title, "/Game/UI", "T_TitleCard", srgb=True, compression=unreal.TextureCompressionSettings.TC_EDITOR_ICON, mips=False)
        log("T_TitleCard")
    log("DONE")


main()
