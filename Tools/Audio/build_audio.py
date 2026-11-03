"""Build every Ebony Hearts sound (combat, UI, ambience, music) deterministically.

Run with Blender's bundled Python (it has numpy):
    "/home/cinqic/.local/opt/blender-5.2.2-linux-x64/5.2/python/bin/python3.13" -I build_audio.py

Options:
    --only REGEX     build only matching names (NOTES.md is then not rewritten)
    --jobs N         worker processes (default: min(8, cpu count)); output is identical for any N
    --no-spectra     skip the PNG spectrograms
    --out DIR        output root (default: <slice>/sourceart/audio)
    --kenney DIR     Kenney packs root (default: <slice>/downloads/thirdparty/Kenney)
    --blender EXE    Blender executable used only to decode OGG (default: $EH_BLENDER or the slice's Blender)

Kenney OGGs are decoded once (through Blender's audaspace) into <out>/_cache/kenney.
All randomness is seeded from the sound name, so every run produces identical WAVs.
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True  # keep the repo free of __pycache__

from eh_audio import analysis, combat, dsp, kenney, master, music, ambience, notes, ui  # noqa: E402

SLICE = HERE.parents[3]
DEFAULT_BLENDER = "/home/cinqic/.local/opt/blender-5.2.2-linux-x64/blender"

SPECTRA = [("Combat", "HitHeavy_01", None), ("Combat", "Deflect", None), ("Combat", "AuraIgnite", None),
           ("Combat", "FlameRoar_01", None), ("Ambience", "ChapelBed", 20.0), ("Music", "Theme", 30.0),
           ("Music", "Battle", 30.0)]


def all_items():
    items = [("Combat", n, "oneshot") for n, _ in combat.builders()]
    items += [("UI", n, "ui") for n, _ in ui.builders()]
    items += [("Ambience", n, "loop") for n, _ in ambience.builders()]
    items += [("Music", n, "loop") for n, _ in music.builders()]
    return items


_CTX = {}


def _ctx(cfg):
    if "c" not in _CTX:
        k = kenney.Kenney(cfg["kenney"], cfg["cache"], cfg["blender"], HERE / "kenney_decode_blender.py")
        _CTX["c"] = combat.Ctx(k)
    return _CTX["c"]


def build_one(cfg, cat, name, kind):
    t0 = time.time()
    c = _ctx(cfg)
    c.k.used = {}
    c.k.log = []
    path = Path(cfg["out"]) / cat / f"S_{name}.wav"
    info = {}
    grid = None
    if kind in ("oneshot", "ui"):
        table = dict(combat.builders() if kind == "oneshot" else ui.builders())
        if kind == "oneshot":
            sig, dur, fade_out = table[name](c)
            y = master.finish_oneshot(sig, dur, fade_out=fade_out)
        else:
            trans, body, dur, fade_out = table[name](c)
            y, _, gain = master.finish_ui(trans, body, dur, fade_out=fade_out)
            info["ui_body_gain"] = gain
    else:
        table = dict(ambience.builders() if cat == "Ambience" else music.builders())
        res = table[name](c)
        sig, target = res[0], res[1]
        bar = res[2] if len(res) > 2 else None
        y, info = master.finish_loop(sig, target, hp=30.0 if cat == "Music" else 24.0)
        info["target_lufs"] = target
        if bar:
            grid = np.arange(1, int(round(len(y) / dsp.ns(bar)))) * dsp.ns(bar)
    master.write_wav(path, y, name)
    back, sr = master.read_wav(path)
    assert sr == dsp.SR
    m = analysis.measure(back, loop=(kind == "loop"), grid=grid)
    m.update(info)
    m.update({"category": cat, "name": name, "kind": kind, "file": str(path.relative_to(cfg["out"])),
              "build_s": round(time.time() - t0, 2)})
    return m, list(c.k.log)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only")
    ap.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--no-spectra", action="store_true")
    ap.add_argument("--out", default=str(SLICE / "sourceart" / "audio"))
    ap.add_argument("--kenney", default=str(SLICE / "downloads" / "thirdparty" / "Kenney"))
    ap.add_argument("--blender", default=os.environ.get("EH_BLENDER", DEFAULT_BLENDER))
    a = ap.parse_args()
    out = Path(a.out)
    for sub in ("Combat", "UI", "Ambience", "Music", "spectra", "_cache"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    cfg = {"out": str(out), "kenney": a.kenney, "cache": str(out / "_cache" / "kenney"), "blender": a.blender}
    k = kenney.Kenney(cfg["kenney"], cfg["cache"], cfg["blender"], HERE / "kenney_decode_blender.py")
    nd = k.ensure_decoded()
    if nd:
        print(f"decoded {nd} Kenney OGG files into {cfg['cache']}")

    items = all_items()
    if a.only:
        rx = re.compile(a.only)
        items = [it for it in items if rx.search(it[1])]
    t0 = time.time()
    results, usage = [], []
    # longest jobs first so the pool stays busy
    order = sorted(items, key=lambda it: {"loop": 0, "oneshot": 1, "ui": 2}[it[2]])
    if a.jobs > 1 and len(order) > 1:
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            futs = [ex.submit(build_one, cfg, *it) for it in order]
            for f in futs:
                m, used = f.result()
                results.append(m)
                usage.extend(used)
                print(f"  {m['file']:34s} {m['duration']:6.2f}s  TP {m['true_peak_db']:6.2f} dBTP  "
                      f"RMS {m['rms_db']:6.1f}  ({m['build_s']}s)", flush=True)
    else:
        for it in order:
            m, used = build_one(cfg, *it)
            results.append(m)
            usage.extend(used)
            print(f"  {m['file']:34s} {m['duration']:6.2f}s  TP {m['true_peak_db']:6.2f} dBTP  "
                  f"RMS {m['rms_db']:6.1f}  ({m['build_s']}s)", flush=True)
    print(f"built {len(results)} files in {time.time() - t0:.1f}s")

    if not a.no_spectra:
        for cat, name, secs in SPECTRA:
            p = out / cat / f"S_{name}.wav"
            if p.exists() and (not a.only or re.search(a.only, name)):
                x, _ = master.read_wav(p)
                analysis.spectrogram_png(out / "spectra" / f"S_{name}.png", x, seconds=secs)
                print(f"  spectrogram spectra/S_{name}.png")

    order_idx = {it[1]: i for i, it in enumerate(all_items())}
    results.sort(key=lambda m: order_idx[m["name"]])
    if not a.only:
        report = {"results": results, "kenney_usage": usage}
        (out / "_cache" / "build_report.json").write_text(json.dumps(report, indent=1))
        notes.write_notes(out / "NOTES.md", results, usage, k)
        print(f"wrote {out / 'NOTES.md'}")
    else:
        for m in results:
            print(json.dumps({k2: (round(v, 3) if isinstance(v, float) else v) for k2, v in m.items()}))


if __name__ == "__main__":
    main()
