"""Strict, synchronous imports of named prototype assets and their saves."""

from pathlib import Path

import unreal


def require_sources(paths):
    missing = [str(path) for path in paths if not Path(path).is_file()]
    if missing:
        raise RuntimeError("Missing source files: " + ", ".join(missing))


def import_checked(task, asset_type, *, legacy_fbx=False):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    library = unreal.EditorAssetLibrary
    package = f"{task.destination_path}/{task.destination_name}"
    object_path = f"{package}.{task.destination_name}"
    reimport_event = None
    reimported = False

    def on_reimport(asset):
        nonlocal reimported
        if asset.get_path_name() == object_path:
            reimported = True

    if legacy_fbx and library.does_asset_exist(package):
        # The legacy FBX factory may return the old asset after a failed reimport.
        reimport_event = unreal.get_editor_subsystem(unreal.ImportSubsystem).on_asset_reimport
        reimport_event.add_callable(on_reimport)
    try:
        tools.import_asset_tasks([task])
    finally:
        if reimport_event is not None:
            reimport_event.remove_callable(on_reimport)

    for asset in task.get_objects():
        if isinstance(asset, asset_type) and asset.get_path_name() == object_path:
            if reimport_event is None or reimported:
                return asset
    raise RuntimeError(f"Import failed for {task.filename} -> {object_path}")


def save_checked(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"Could not save {asset.get_path_name()}")
