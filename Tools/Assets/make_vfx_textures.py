"""Generates the original effect textures (white RGB, shape in alpha) used by M_VFX_Additive.

Usage: python3 make_vfx_textures.py <output-dir>
Everything is procedural and deterministic; no third-party imagery is used.
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image

SIZE = 256


def save(name, alpha_fn, out):
    img = Image.new("RGBA", (SIZE, SIZE))
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            u = (x + 0.5) / SIZE * 2.0 - 1.0
            v = (y + 0.5) / SIZE * 2.0 - 1.0
            a = max(0.0, min(1.0, alpha_fn(u, v)))
            px[x, y] = (255, 255, 255, int(a * 255 + 0.5))
    img.save(out / f"T_FX_{name}.png")


def glow(u, v):
    r = math.hypot(u, v)
    return math.exp(-r * r * 6.0) * (1.0 - min(1.0, r))


def streak(u, v):
    # Long horizontal sliver: bright core, tapered ends.
    taper = max(0.0, 1.0 - abs(u)) ** 0.8
    return math.exp(-(v * v) / (0.012 * taper + 1e-4)) * taper


def ring(u, v):
    r = math.hypot(u, v)
    return math.exp(-((r - 0.78) ** 2) / 0.004) * (1.0 if r < 1.0 else 0.0)


def spark(u, v):
    # Four-point star with a hot centre.
    r = math.hypot(u, v)
    arms = max(math.exp(-(v * v) / 0.0025) * max(0.0, 1 - abs(u)), math.exp(-(u * u) / 0.0025) * max(0.0, 1 - abs(v)))
    return min(1.0, arms + math.exp(-r * r * 30.0))


def make_flame(out):
    # Teardrop flame with turbulent edges, deterministic noise.
    rng = random.Random(7)
    phases = [rng.uniform(0, math.tau) for _ in range(6)]

    def flame(u, v):
        y = (v + 1.0) / 2.0          # 0 top, 1 bottom
        height = 1.0 - y
        width = 0.55 * math.sin(math.pi * min(1.0, y * 1.1)) ** 0.8 * (0.35 + 0.65 * y)
        wobble = sum(0.06 / (i + 1) * math.sin(height * (5 + 3 * i) + phases[i]) for i in range(6)) * height
        d = abs(u - wobble) / max(width, 1e-3)
        body = max(0.0, 1.0 - d ** 1.6)
        core = math.exp(-((u - wobble) ** 2) / 0.02) * y ** 1.5
        return min(1.0, body * (0.55 + 0.45 * y) + core * 0.6)

    save("Flame", flame, out)


def make_splash(out):
    rng = random.Random(11)
    drops = [(rng.uniform(-0.4, 0.4), rng.uniform(-0.6, 0.5), rng.uniform(0.08, 0.2)) for _ in range(7)]

    def splash(u, v):
        a = 0.0
        for cx, cy, r in drops:
            d = math.hypot((u - cx) / r, (v - cy) / (r * 1.4))
            a = max(a, max(0.0, 1.0 - d * d))
        return a * 0.9

    save("Splash", splash, out)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    save("Glow", glow, out)
    save("Streak", streak, out)
    save("Ring", ring, out)
    save("Spark", spark, out)
    make_flame(out)
    make_splash(out)
    print("wrote", sorted(p.name for p in out.glob("T_FX_*.png")))


if __name__ == "__main__":
    main()
