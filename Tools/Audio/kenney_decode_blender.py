"""Decode Kenney CC0 OGG files to 32-bit PCM WAV using Blender's bundled audaspace (`aud`).

Run inside Blender (the standalone Python interpreter has no OGG decoder):
    blender --background --factory-startup --python kenney_decode_blender.py -- <out_dir> <src.ogg> [<src.ogg> ...]

The source sample rate and channel count are kept; resampling to 48 kHz happens in the build
script so it is under deterministic numpy control. Source files are only read, never modified.
Some Kenney files decode slightly above full scale, so the cache is 32-bit PCM where float 1.0
maps to 2**29 (12 dB of headroom, nothing clips). Readers divide by HEADROOM_SCALE.
"""
import sys
import wave
from pathlib import Path

import aud
import numpy as np

HEADROOM_SCALE = 2 ** 29


def main(argv):
    if "--" not in argv:
        raise SystemExit("usage: blender --background --python kenney_decode_blender.py -- <out_dir> <src.ogg>...")
    args = argv[argv.index("--") + 1:]
    out_dir = Path(args[0])
    out_dir.mkdir(parents=True, exist_ok=True)
    for src in args[1:]:
        src = Path(src)
        sound = aud.Sound(str(src))
        rate, channels = sound.specs
        data = np.asarray(sound.data(), dtype=np.float64)
        if data.ndim == 1:
            data = data[:, None]
        pcm = np.clip(np.round(data * HEADROOM_SCALE), -2 ** 31, 2 ** 31 - 1).astype("<i4")
        dst = out_dir / (src.stem + ".wav")
        with wave.open(str(dst), "wb") as w:
            w.setnchannels(int(data.shape[1]))
            w.setsampwidth(4)
            w.setframerate(int(round(rate)))
            w.writeframes(pcm.tobytes())
        print(f"decoded {src.name} -> {dst.name} ({int(rate)} Hz, {data.shape[1]} ch, {data.shape[0]} frames)")


if __name__ == "__main__":
    main(sys.argv)
