"""Imports the generated sound set (sourceart/audio/<Combat|UI|Ambience|Music>/S_*.wav) into /Game/Audio.
Ambience and music are looping; everything else is a one-shot. Re-running replaces the assets.
EH_AUDIO_NAMES=S_UiLock,S_UiWarn imports only those (the others are left untouched)."""
import os

import unreal

WS = os.environ["EH_WS"]
SRC = os.path.join(WS, "sourceart", "audio")
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary

ONLY = set(n for n in os.environ.get("EH_AUDIO_NAMES", "").split(",") if n)
# Check the complete requested set before modifying any existing assets.
found = {os.path.splitext(f)[0] for cat in ("Combat", "UI", "Ambience", "Music")
         for f in os.listdir(os.path.join(SRC, cat)) if f.startswith("S_") and f.endswith(".wav")}
if not found:
    raise RuntimeError("no audio WAV sources found")
if ONLY:
    missing = ONLY - found
    if missing:
        raise RuntimeError("requested audio WAV missing: " + ", ".join(sorted(missing)))
count = 0
for cat in ("Combat", "UI", "Ambience", "Music"):
    folder = os.path.join(SRC, cat)
    for f in sorted(os.listdir(folder)):
        if not (f.startswith("S_") and f.endswith(".wav")):
            continue
        name = os.path.splitext(f)[0]
        if ONLY and name not in ONLY:
            continue
        task = unreal.AssetImportTask()
        task.filename = os.path.join(folder, f)
        task.destination_path = f"/Game/Audio/{cat}"
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        tools.import_asset_tasks([task])
        wave = unreal.load_asset(f"/Game/Audio/{cat}/{name}")
        # Loading alone can return the previous asset after a failed reimport.
        if not task.imported_object_paths or wave is None:
            raise RuntimeError(f"audio import failed: {task.filename}")
        looping = cat in ("Ambience", "Music")
        wave.set_editor_property("looping", looping)
        wave.set_editor_property("compression_quality", 70 if looping else 85)
        if not eal.save_asset(wave.get_path_name(), only_if_is_dirty=False):
            raise RuntimeError(f"audio save failed: {task.destination_path}/{name}")
        count += 1
unreal.log(f"EHAUDIO imported {count}")
