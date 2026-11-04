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


class Noise:
    """Smooth value noise on an integer lattice, optionally periodic (tileable), deterministic for a seed."""

    def __init__(self, seed, period=None):
        rng = random.Random(seed)
        self.table = [rng.random() for _ in range(4096)]
        self.period = period

    def lattice(self, i, j):
        if self.period:
            i %= self.period
            j %= self.period
        return self.table[(i * 1619 + j * 31337 + (i * j) % 977) % 4096]

    def __call__(self, x, y):
        i, j = math.floor(x), math.floor(y)
        fx, fy = x - i, y - j
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a, b = self.lattice(i, j), self.lattice(i + 1, j)
        c, d = self.lattice(i, j + 1), self.lattice(i + 1, j + 1)
        return (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy

    def fbm(self, x, y, octaves=4):
        total, amp, norm = 0.0, 0.5, 0.0
        for o in range(octaves):
            f = 2 ** o
            if self.period:
                total += amp * Noise.__call__(self._octave(o), x * f, y * f)
            else:
                total += amp * self(x * f + 17.0 * o, y * f + 31.0 * o)
            norm += amp
            amp *= 0.5
        return total / norm

    def _octave(self, o):
        # A periodic octave needs its own period (period * 2^o) so the sum still tiles.
        cache = self.__dict__.setdefault("_oct", {})
        if o not in cache:
            n = Noise.__new__(Noise)
            n.table = self.table
            n.period = self.period * 2 ** o
            cache[o] = n
        return cache[o]


def bolt(u, v):
    # Cross-section of a lightning ribbon (U across, V along): a hot thin core inside a soft glow.
    return min(1.0, math.exp(-u * u * 90.0) + 0.55 * math.exp(-u * u * 5.0) * (1.0 - u * u))


def make_noise(out):
    # Tileable wispy noise for the aura shell, stretched along V so it reads as rising streaks once panned upward.
    n = Noise(23, period=8)

    def wisps(u, v):
        x, y = (u + 1.0) / 2.0 * 8.0, (v + 1.0) / 2.0 * 8.0
        a = n.fbm(x, y, 4)
        return max(0.0, min(1.0, (a - 0.32) * 2.4)) ** 1.6

    save("Noise", wisps, out)


def make_fire_sheet(out, frames=4, cell=128):
    """A 4 x 4 flipbook of one flame tongue living out its life: it licks upward on scrolling, warped noise, its base
    narrows and it breaks up and fades by the last frame. Density in alpha; the material maps it from crimson edges to
    a hot core."""
    n = Noise(41)
    w = Noise(97)
    size = frames * cell
    img = Image.new("RGBA", (size, size))
    px = img.load()
    for f in range(frames * frames):
        t = f / (frames * frames - 1)
        ox, oy = (f % frames) * cell, (f // frames) * cell
        for y in range(cell):
            h = 1.0 - (y + 0.5) / cell            # 0 at the bottom, 1 at the top
            for x in range(cell):
                u = (x + 0.5) / cell * 2.0 - 1.0
                # Domain warp: the flame sways and licks as the noise scrolls upward with age.
                wx = (w.fbm(u * 1.4 + 3.0, h * 2.0 - t * 2.6, 3) - 0.5) * 0.8 * h
                uu = u + wx
                width = (0.58 * (1.0 - h) ** 0.5 + 0.06) * (1.0 - 0.3 * t)
                body = max(0.0, 1.0 - (abs(uu) / max(width, 1e-3)) ** 1.5)
                turb = n.fbm(uu * 2.8 + 5.0, h * 3.6 - t * 4.5, 4)
                # Erosion rises with height and age, so the tip tears into licks and the tongue breaks up at the end.
                d = body - (h ** 1.3 * 0.6 + t * 0.45) + (turb - 0.5) * 1.1
                base = min(1.0, (1.0 - h) * 5.0)  # soft bottom edge
                a = max(0.0, min(1.0, d * 1.4)) * body ** 0.4 * base * (1.0 - t ** 3)
                px[ox + x, oy + y] = (255, 255, 255, int(a * 255 + 0.5))
    img.save(out / "T_FX_FireSheet.png")


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    save("Glow", glow, out)
    save("Streak", streak, out)
    save("Ring", ring, out)
    save("Spark", spark, out)
    make_flame(out)
    make_splash(out)
    save("Bolt", bolt, out)
    make_noise(out)
    make_fire_sheet(out)
    print("wrote", sorted(p.name for p in out.glob("T_FX_*.png")))


if __name__ == "__main__":
    main()
