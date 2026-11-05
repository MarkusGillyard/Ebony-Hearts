"""Imports the generated sound set (sourceart/audio/<Combat|UI|Ambience|Music>/S_*.wav) into /Game/Audio.
Ambience and music are looping; everything else is a one-shot. Re-running replaces the assets."""
import os

import unreal

WS = os.environ["EH_WS"]
SRC = os.path.join(WS, "sourceart", "audio")
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary

count = 0
for cat in ("Combat", "UI", "Ambience", "Music"):
    folder = os.path.join(SRC, cat)
    for f in sorted(os.listdir(folder)):
        if not (f.startswith("S_") and f.endswith(".wav")):
            continue
        name = os.path.splitext(f)[0]
        task = unreal.AssetImportTask()
        task.filename = os.path.join(folder, f)
        task.destination_path = f"/Game/Audio/{cat}"
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        tools.import_asset_tasks([task])
        wave = unreal.load_asset(f"/Game/Audio/{cat}/{name}")
        if wave is None:
            unreal.log_error(f"EHAUDIO FAIL {f}")
            continue
        looping = cat in ("Ambience", "Music")
        wave.set_editor_property("looping", looping)
        wave.set_editor_property("compression_quality", 70 if looping else 85)
        eal.save_asset(wave.get_path_name(), only_if_is_dirty=False)
        count += 1
unreal.log(f"EHAUDIO imported {count}")
