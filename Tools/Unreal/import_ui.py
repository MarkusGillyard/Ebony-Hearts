"""Imports the interface textures into /Game/UI (UI/UX overhaul, 2026-11-09).

Inputs: $EH_WS/sourceart/ui/T_Logo.png and T_LogoSmall.png (made by Tools/Assets/make_ui_textures.py from the
creator's supplied logo). Run headless: bin/editor_py.sh Tools/Unreal/import_ui.py

Each texture is sRGB, BC7 (good alpha at 1 byte per pixel; both sizes are multiples of 4), without mips (the logo is
never drawn smaller than about half its size, and each use picks the nearer of the two sizes), in the UI texture
group so it is never streamed out mid-screen.
"""
import os

import unreal

WS = os.environ["EH_WS"]
SRC_UI = os.path.join(WS, "sourceart", "ui")
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary


def log(msg):
    unreal.log("EHUI " + msg)


def import_ui_texture(name):
    path = os.path.join(SRC_UI, f"{name}.png")
    if not os.path.exists(path):
        raise RuntimeError(f"missing {path}")
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = "/Game/UI"
    task.destination_name = name
    task.replace_existing = True
    task.automated = True
    task.save = False
    tools.import_asset_tasks([task])
    tex = unreal.load_asset(f"/Game/UI/{name}")
    if tex is None:
        raise RuntimeError(f"import failed: {path}")
    tex.set_editor_property("srgb", True)
    tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_BC7)
    tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
    eal.save_asset(tex.get_path_name(), only_if_is_dirty=False)
    log(f"{name} {tex.blueprint_get_size_x()}x{tex.blueprint_get_size_y()}")


def main():
    for name in ("T_Logo", "T_LogoSmall"):
        import_ui_texture(name)
    log("DONE")


main()
