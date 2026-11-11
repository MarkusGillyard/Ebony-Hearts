"""Access to the CC0 Kenney packs (read-only) through a decoded-WAV cache.

OGG decoding needs Blender's audaspace, so missing cache entries are produced by running
`kenney_decode_blender.py` inside Blender. Everything else here is plain numpy.
"""
import os
import subprocess
import wave
from pathlib import Path

import numpy as np

from . import dsp

HEADROOM_SCALE = 2 ** 29  # must match kenney_decode_blender.py

PACKS = {
    "impact": "impact-sounds/kenney_impact-sounds/Audio",
    "ui": "interface-sounds/kenney_interface-sounds/Audio",
    "rpg": "rpg-audio/kenney_rpg-audio/Audio",
}

# Every Kenney file the build may use (pack, stem). Keep in sync with NOTES.md (generated).
NEEDED = (
    [("impact", f"impactPunch_medium_{i:03d}") for i in range(5)]
    + [("impact", f"impactPunch_heavy_{i:03d}") for i in range(5)]
    + [("impact", f"impactSoft_medium_{i:03d}") for i in range(5)]
    + [("impact", f"impactSoft_heavy_{i:03d}") for i in range(5)]
    + [("impact", f"impactGeneric_light_{i:03d}") for i in range(5)]
    + [("impact", f"footstep_concrete_{i:03d}") for i in range(5)]
    + [("rpg", n) for n in ("cloth1", "cloth2", "cloth3", "cloth4", "clothBelt", "clothBelt2",
                            "creak1", "creak2", "creak3", "dropLeather", "handleSmallLeather")]
    + [("rpg", f"footstep{i:02d}") for i in range(10)]
    + [("ui", n) for n in ("click_001", "click_002", "click_003", "click_004", "click_005",
                           "tick_001", "tick_002", "tick_004",
                           "select_001", "select_002", "select_003", "select_004",
                           "back_001", "back_002", "back_003", "back_004",
                           "open_001", "open_002", "open_003", "open_004",
                           "close_001", "close_002", "close_003", "close_004",
                           "confirmation_001", "confirmation_002", "confirmation_003", "confirmation_004")]
)


class Kenney:
    def __init__(self, kenney_root, cache_dir, blender_exe, decode_script):
        self.root = Path(kenney_root)
        self.cache = Path(cache_dir)
        self.blender = blender_exe
        self.decode_script = Path(decode_script)
        self.used = {}  # stem -> set of output names (for the NOTES attribution table)
        self.log = []   # every processed use (filled by combat.Ctx.kload)
        self._mem = {}

    def source_path(self, pack, stem):
        return self.root / PACKS[pack] / f"{stem}.ogg"

    def _cache_ok(self, stem):
        path = self.cache / f"{stem}.wav"
        if not path.exists():
            return False
        try:
            with wave.open(str(path), "rb") as w:
                return w.getsampwidth() == 4 and w.getnframes() > 0
        except (wave.Error, EOFError):
            return False

    def ensure_decoded(self, items=NEEDED):
        missing = [(p, s) for p, s in items if not self._cache_ok(s)]
        if not missing:
            return 0
        srcs = [str(self.source_path(p, s)) for p, s in missing]
        for s in srcs:
            if not Path(s).exists():
                raise FileNotFoundError(s)
        self.cache.mkdir(parents=True, exist_ok=True)
        cmd = [self.blender, "--background", "--factory-startup", "--python", str(self.decode_script),
               "--", str(self.cache)] + srcs
        env = dict(os.environ)
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if res.returncode != 0:
            raise RuntimeError("Blender OGG decode failed:\n" + res.stdout[-2000:] + res.stderr[-2000:])
        still = [s for _, s in missing if not self._cache_ok(s)]
        if still:
            raise RuntimeError(f"decode did not produce: {still}")
        return len(missing)

    def raw(self, stem):
        """(float64 array (n, ch), sample rate) straight from the decoded cache."""
        if stem not in self._mem:
            with wave.open(str(self.cache / f"{stem}.wav"), "rb") as w:
                sr = w.getframerate()
                ch = w.getnchannels()
                data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i4").astype(np.float64) / HEADROOM_SCALE
            self._mem[stem] = (data.reshape(-1, ch), sr)
        return self._mem[stem]

    def load(self, stem, used_by=None, pitch=1.0, trim_db=-45.0, mono=True):
        """Mono 48 kHz float copy, varispeed by `pitch` (>1 = higher and shorter), onset-trimmed."""
        data, sr = self.raw(stem)
        x = data.mean(axis=1) if mono else data
        x = dsp.resample(x, sr * pitch, dsp.SR)
        if trim_db is not None:
            x = dsp.trim_onset(x, trim_db)
        if used_by:
            self.used.setdefault(stem, set()).add(used_by)
        return x
