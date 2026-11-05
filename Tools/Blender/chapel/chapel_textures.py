"""Texture generation for The Drowned Chapel.

Every material gets T_<Material>_D (base colour, sRGB), T_<Material>_N (OpenGL
normal, +Y up) and T_<Material>_ORM (R=AO, G=roughness, B=metallic) as PNG.

Photo-sourced materials are graded from CC0 inputs (read-only, decoded with
Blender's image loader).  Glass, flame, water and decal maps are fully procedural
and original.  PNGs are written by a tiny deterministic writer (zlib level 9),
so a rebuild produces byte-identical textures.
"""
import math
import os
import struct
import zlib

import numpy as np

import chapel_config as C
import chapel_rose as R

INPUTS_USED = {}   # material -> list of (source, asset id, folder, files)


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def write_png(path, arr):
    """arr: HxWxC (C in 1,3,4), float [0,1] or uint8, rows top -> bottom."""
    if arr.ndim == 2:
        arr = arr[:, :, None]
    if arr.dtype != np.uint8:
        arr = (np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    h, w, c = arr.shape
    ctype = {1: 0, 3: 2, 4: 6}[c]
    rows = arr.reshape(h, w * c).astype(np.int16)
    # PNG "Sub" filter on every row: deterministic and compresses well
    sub = rows.copy()
    sub[:, c:] = (rows[:, c:] - rows[:, :-c]) % 256
    raw = np.empty((h, w * c + 1), np.uint8)
    raw[:, 0] = 1
    raw[:, 1:] = sub.astype(np.uint8)
    data = zlib.compress(raw.tobytes(), 9)

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload +
                struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0)) +
           chunk(b"IDAT", data) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def load_image(path):
    """Decode an image with Blender; returns HxWx3 float32 (raw encoded values), top->bottom."""
    import bpy
    img = bpy.data.images.load(path, check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
    except Exception:
        pass
    w, h = img.size
    ch = img.channels
    buf = np.empty(w * h * ch, np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    arr = buf.reshape(h, w, ch)[::-1]
    if ch == 1:
        arr = np.repeat(arr, 3, axis=2)
    return np.ascontiguousarray(arr[:, :, :3])


def downsample(arr, size):
    while arr.shape[0] > size:
        arr = 0.25 * (arr[0::2, 0::2] + arr[1::2, 0::2] + arr[0::2, 1::2] + arr[1::2, 1::2])
    return arr


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def luminance(rgb):
    return rgb @ LUMA


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def box_blur(arr, r):
    """Separable wrap-around box blur (keeps textures tileable)."""
    if r <= 0:
        return arr
    out = arr.astype(np.float32)
    for axis in (0, 1):
        acc = np.zeros_like(out)
        for d in range(-r, r + 1):
            acc += np.roll(out, d, axis=axis)
        out = acc / (2 * r + 1)
    return out


def grade(rgb, sat=0.5, contrast=1.0, tint=(1, 1, 1), mean=None, simplify=0.0, blur_r=2):
    """Stylising colour grade on sRGB-encoded values."""
    rgb = rgb.astype(np.float32)
    if simplify > 0:
        rgb = rgb * (1 - simplify) + box_blur(rgb, blur_r) * simplify
    lum = luminance(rgb)[..., None]
    out = lum + (rgb - lum) * sat
    m = float(luminance(out).mean())
    out = (out - m) * contrast + m
    out = out * np.array(tint, np.float32)
    if mean is not None:
        cur = float(luminance(np.clip(out, 0, 1)).mean())
        out = out * (mean / max(cur, 1e-4))
    return np.clip(out, 0.0, 1.0)


def normal_from_dx(nrm):
    out = nrm.copy()
    out[..., 1] = 1.0 - out[..., 1]
    return out


def normal_scale(nrm, k):
    v = nrm * 2.0 - 1.0
    v[..., 0] *= k
    v[..., 1] *= k
    v /= np.linalg.norm(v, axis=2, keepdims=True) + 1e-8
    return v * 0.5 + 0.5


def normal_from_height(h, strength):
    """Tileable OpenGL normal from a height field (rows top->bottom, +Y = up in image)."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, 1, axis=0) - np.roll(h, -1, axis=0)) * 0.5   # up is row-1
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def normal_from_height_clamped(h, strength):
    """Non-tiling variant (edge clamped) for the rose window."""
    hp = np.pad(h, 1, mode="edge")
    dx = (hp[1:-1, 2:] - hp[1:-1, :-2]) * 0.5
    dy = (hp[:-2, 1:-1] - hp[2:, 1:-1]) * 0.5
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def renorm(nrm):
    v = nrm * 2.0 - 1.0
    v /= np.linalg.norm(v, axis=2, keepdims=True) + 1e-8
    return v * 0.5 + 0.5


def vnoise(size, cells, rng):
    lat = rng.random((cells, cells)).astype(np.float32)
    t = np.arange(size, dtype=np.float32) * cells / size
    i0 = np.floor(t).astype(np.int64)
    f = t - i0
    f = f * f * (3 - 2 * f)
    i0 %= cells
    i1 = (i0 + 1) % cells
    a = lat[i0][:, i0]
    b = lat[i0][:, i1]
    c = lat[i1][:, i0]
    d = lat[i1][:, i1]
    fx = f[None, :]
    fy = f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(size, cells, octaves, rng, gain=0.5):
    acc = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        acc += amp * vnoise(size, cells * 2 ** o, rng)
        tot += amp
        amp *= gain
    return acc / tot


def sample_bilinear(img, u, v):
    """Wrap-around bilinear sample of HxW(xC) img at pixel coords u (x), v (y)."""
    h, w = img.shape[:2]
    x0 = np.floor(u).astype(np.int64)
    y0 = np.floor(v).astype(np.int64)
    fx = (u - x0)[..., None] if img.ndim == 3 else (u - x0)
    fy = (v - y0)[..., None] if img.ndim == 3 else (v - y0)
    x0 %= w
    y0 %= h
    x1 = (x0 + 1) % w
    y1 = (y0 + 1) % h
    return ((img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) +
            (img[y1, x0] * (1 - fx) + img[y1, x1] * fx) * fy)


def voronoi(xs, ys, cell, rng_seed, jitter=0.9):
    """Jittered-grid Voronoi over arbitrary coordinates (metres).
    Returns (cell_id, edge_distance_in_metres, d1)."""
    gx = xs / cell
    gy = ys / cell
    ci = np.floor(gx).astype(np.int64)
    cj = np.floor(gy).astype(np.int64)
    best1 = np.full(xs.shape, 1e9, np.float32)
    best2 = np.full(xs.shape, 1e9, np.float32)
    p1x = np.zeros(xs.shape, np.float32)
    p1y = np.zeros(xs.shape, np.float32)
    p2x = np.zeros(xs.shape, np.float32)
    p2y = np.zeros(xs.shape, np.float32)
    id1 = np.zeros(xs.shape, np.int64)

    def hash2(i, j, salt):
        hsh = (i * 73856093) ^ (j * 19349663) ^ (rng_seed * 83492791 + salt)
        hsh = (hsh ^ (hsh >> 13)) * 1274126177
        hsh = hsh ^ (hsh >> 16)
        return (hsh & 0xFFFFFF).astype(np.float32) / float(0xFFFFFF)

    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ni = ci + di
            nj = cj + dj
            px = ni + 0.5 + (hash2(ni, nj, 1) - 0.5) * jitter
            py = nj + 0.5 + (hash2(ni, nj, 2) - 0.5) * jitter
            d = np.hypot(gx - px, gy - py)
            cid = ni * 100003 + nj
            closer = d < best1
            second = (~closer) & (d < best2)
            # shift best1 -> best2 where closer
            best2 = np.where(closer, best1, np.where(second, d, best2))
            p2x = np.where(closer, p1x, np.where(second, px, p2x))
            p2y = np.where(closer, p1y, np.where(second, py, p2y))
            best1 = np.where(closer, d, best1)
            p1x = np.where(closer, px, p1x)
            p1y = np.where(closer, py, p1y)
            id1 = np.where(closer, cid, id1)
    # perpendicular distance to the bisector between the two nearest sites
    mx = (p1x + p2x) * 0.5
    my = (p1y + p2y) * 0.5
    nx = p2x - p1x
    ny = p2y - p1y
    nl = np.hypot(nx, ny) + 1e-6
    edge = np.abs((gx - mx) * nx / nl + (gy - my) * ny / nl) * cell
    return id1, edge, best1 * cell


def hash_float(ids, salt):
    h = (ids.astype(np.int64) * 2654435761 + salt * 40503) & 0xFFFFFFFF
    h = (h ^ (h >> 15)) * 2246822519 & 0xFFFFFFFF
    h = h ^ (h >> 13)
    return (h & 0xFFFF).astype(np.float32) / 65535.0


def pack_orm(ao, rough, metal):
    return np.stack([ao, rough, metal], axis=2).astype(np.float32)


def save_set(name, d, n, orm, report):
    paths = {}
    for suffix, arr in (("D", d), ("N", n), ("ORM", orm)):
        p = os.path.join(C.TEX_DIR, "T_%s_%s.png" % (name, suffix))
        write_png(p, arr)
        paths[suffix] = os.path.basename(p)
    report[name] = {"files": paths, "size": [int(d.shape[1]), int(d.shape[0])]}


# ---------------------------------------------------------------------------
# Photo-sourced materials
# ---------------------------------------------------------------------------

def _ph(asset, res):
    folder = os.path.join(C.PH, asset, "%s_%s_jpg" % (asset, res))
    return lambda m: os.path.join(folder, "%s_%s_%s.jpg" % (asset, m, res))


def _acg(asset, res):
    folder = os.path.join(C.ACG, asset, "%s_%s-JPG" % (asset, res))
    return lambda m: os.path.join(folder, "%s_%s-JPG_%s.jpg" % (asset, res, m))


def _record(material, source, asset, files):
    INPUTS_USED.setdefault(material, []).append({
        "source": source, "asset_id": asset,
        "folder": os.path.relpath(os.path.dirname(files[0]), C.THIRDPARTY),
        "files": [os.path.basename(f) for f in files]})


def tex_stone_ashlar(report):
    f = _ph("medieval_blocks_03", "2k")
    files = [f("diff"), f("nor_dx"), f("arm")]
    _record("StoneAshlar", "Poly Haven", "medieval_blocks_03", files)
    d = load_image(files[0])
    n = normal_from_dx(load_image(files[1]))
    arm = load_image(files[2])
    d = grade(d, sat=0.30, contrast=0.85, tint=(0.93, 0.98, 1.07), mean=0.34, simplify=0.45, blur_r=2)
    rough = np.clip(arm[..., 1] * 0.9 + 0.08, 0.0, 1.0)
    orm = pack_orm(arm[..., 0], rough, np.zeros_like(rough))
    save_set("StoneAshlar", d, normal_scale(n, 0.9), orm, report)


def tex_stone_dressed(report):
    f = _acg("Rock035", "1K")
    files = [f("Color"), f("NormalGL"), f("Roughness"), f("AmbientOcclusion")]
    _record("StoneDressed", "ambientCG", "Rock035", files)
    d = load_image(files[0])
    n = load_image(files[1])
    rough = load_image(files[2])[..., 0]
    ao = load_image(files[3])[..., 0]
    d = grade(d, sat=0.30, contrast=0.40, tint=(0.95, 1.0, 1.06), mean=0.24, simplify=0.92, blur_r=6)
    # compress the white veins: stylised dark slate rather than marble
    lum = luminance(d)
    cap = float(lum.mean()) * 1.25
    d = d * (np.minimum(lum, cap) / np.maximum(lum, 1e-4))[..., None]
    d = grade(d, sat=1.0, contrast=1.0, mean=0.24)
    orm = pack_orm(0.6 + 0.4 * ao, np.clip(rough * 0.85 + 0.1, 0, 1), np.zeros_like(rough))
    n = renorm(n * 0.55 + box_blur(n, 3) * 0.45)
    save_set("StoneDressed", d, normal_scale(n, 0.30), orm, report)


def tex_floor(report):
    f = _ph("monastery_stone_floor", "2k")
    files = [f("diff"), f("nor_dx"), f("arm"), f("disp")]
    _record("FloorFlags", "Poly Haven", "monastery_stone_floor", files)
    d = load_image(files[0])
    n = normal_from_dx(load_image(files[1]))
    arm = load_image(files[2])
    disp = load_image(files[3])[..., 0]
    disp = box_blur(disp[..., None], 3)[..., 0]
    wet = smoothstep(0.42, 0.22, disp)          # low spots hold water
    d = grade(d, sat=0.32, contrast=0.9, tint=(0.92, 0.97, 1.05), mean=0.26, simplify=0.35, blur_r=2)
    d = d * (1.0 - 0.28 * wet[..., None])
    rough = np.clip(arm[..., 1] * 0.55, 0.06, 1.0)
    rough = rough * (1 - wet) + 0.05 * wet
    orm = pack_orm(arm[..., 0], rough, np.zeros_like(rough))
    save_set("FloorFlags", d, normal_scale(n, 1.0), orm, report)


def tex_wood(report):
    f = _ph("weathered_planks", "2k")
    files = [f("diff"), f("nor_dx"), f("arm")]
    _record("WoodPew", "Poly Haven", "weathered_planks", files)
    d = downsample(load_image(files[0]), C.TEX_STD)
    n = renorm(downsample(normal_from_dx(load_image(files[1])), C.TEX_STD))
    arm = downsample(load_image(files[2]), C.TEX_STD)
    d = grade(d, sat=0.45, contrast=0.9, tint=(1.0, 0.94, 0.88), mean=0.19, simplify=0.3, blur_r=1)
    orm = pack_orm(arm[..., 0], np.clip(arm[..., 1] * 0.95, 0.3, 1.0), np.zeros_like(arm[..., 0]))
    save_set("WoodPew", d, n, orm, report)


def tex_iron(report):
    f = _ph("rusty_metal_04", "1k")
    files = [f("diff"), f("nor_dx"), f("arm")]
    _record("IronAged", "Poly Haven", "rusty_metal_04", files)
    d = load_image(files[0])
    n = normal_from_dx(load_image(files[1]))
    arm = load_image(files[2])
    d = grade(d, sat=0.28, contrast=0.8, tint=(1.0, 0.96, 0.93), mean=0.15, simplify=0.3, blur_r=1)
    orm = pack_orm(arm[..., 0], np.clip(arm[..., 1], 0.35, 1.0), np.clip(arm[..., 2] * 0.85, 0, 1))
    save_set("IronAged", d, normal_scale(n, 0.8), orm, report)


def tex_wax(report):
    f = _acg("Ivory001B", "1K")
    files = [f("Color"), f("NormalGL"), f("Roughness")]
    _record("CandleWax", "ambientCG", "Ivory001B", files)
    d = downsample(load_image(files[0]), C.TEX_SMALL)
    n = renorm(downsample(load_image(files[1]), C.TEX_SMALL))
    rough = downsample(load_image(files[2]), C.TEX_SMALL)[..., 0]
    d = grade(d, sat=0.55, contrast=1.0, tint=(1.0, 0.92, 0.78), mean=0.70)
    orm = pack_orm(np.ones_like(rough), np.clip(rough * 0.6 + 0.2, 0, 1), np.zeros_like(rough))
    save_set("CandleWax", d, normal_scale(n, 0.5), orm, report)


def tex_cloth(report):
    f = _acg("Fabric066", "1K")
    files = [f("Color"), f("NormalGL"), f("Roughness"), f("AmbientOcclusion")]
    _record("ClothAltar", "ambientCG", "Fabric066", files)
    src = load_image(files[0])
    n = load_image(files[1])
    rough = load_image(files[2])[..., 0]
    ao = load_image(files[3])[..., 0]
    lum = luminance(src)
    lum = (lum - lum.mean()) * 1.4 + 0.5
    lo = np.array([0.06, 0.012, 0.018], np.float32)
    hi = np.array([0.36, 0.055, 0.07], np.float32)
    d = lo + (hi - lo) * np.clip(lum, 0, 1)[..., None]
    rng = np.random.default_rng(C.SEED + 7)
    stain = fbm(d.shape[0], 4, 4, rng)
    d = d * (0.75 + 0.35 * stain[..., None])
    orm = pack_orm(ao, np.clip(rough * 0.2 + 0.78, 0, 1), np.zeros_like(rough))
    save_set("ClothAltar", np.clip(d, 0, 1), normal_scale(n, 0.8), orm, report)


# ---------------------------------------------------------------------------
# Procedural materials
# ---------------------------------------------------------------------------

def tex_rose_glass(report):
    S = C.TEX_BIG
    half = C.ROSE_TEX_R
    pix = (np.arange(S, dtype=np.float32) + 0.5) / S * 2 * half - half
    x = np.broadcast_to(pix[None, :], (S, S))
    z = np.broadcast_to(pix[::-1][:, None], (S, S))        # row 0 is the top
    x = np.ascontiguousarray(x)
    z = np.ascontiguousarray(z)
    label, ls, lt = R.label_grid(x, z)
    r = np.hypot(x, z)
    rng = np.random.default_rng(C.SEED + 11)

    pal = {
        "deep_blue": (0.035, 0.085, 0.36), "blue": (0.07, 0.17, 0.58), "cobalt": (0.10, 0.25, 0.78),
        "ice": (0.32, 0.50, 0.85), "violet": (0.30, 0.10, 0.55), "deep_violet": (0.17, 0.05, 0.36),
        "crimson": (0.62, 0.05, 0.09), "gold": (0.90, 0.62, 0.16), "amber": (0.82, 0.40, 0.07),
        "teal": (0.09, 0.36, 0.48),
    }

    def col(name):
        return np.array(pal[name], np.float32)

    # glass pieces
    cell_id, edge, _ = voronoi(x, z, 0.12, 31)
    piece_rand = hash_float(cell_id, 3)
    piece_rand2 = hash_float(cell_id, 5)

    out = np.zeros((S, S, 3), np.float32)
    motif_edge = np.full((S, S), 1.0, np.float32)    # distance to designed lead lines (m)

    # --- petals: blue field, violet/crimson lozenge spine, gold bead in the head
    pet = (label >= 100) & (label < 200)
    blues = np.stack([col("deep_blue"), col("blue"), col("cobalt"), col("blue"), col("teal")])
    pick = np.minimum((piece_rand * 4.6).astype(np.int64), 4)
    field = blues[pick]
    out[pet] = field[pet]
    # lozenges along the axis
    period = 0.30
    sp = np.mod(ls - 0.80, period) - period / 2
    lz = np.abs(sp) / 0.15 + np.abs(lt) / (0.07 + 0.05 * np.clip((ls - 0.8) / 0.8, 0, 1))
    loz = pet & (lz <= 1.0) & (ls > 0.80) & (ls < S_LOZ_END())
    idx = np.floor((ls - 0.80) / period).astype(np.int64)
    alt = np.where(np.mod(idx, 2) == 0, 1.0, 0.0)[..., None]
    loz_col = col("violet") * alt + col("crimson") * (1 - alt)
    out[loz] = loz_col[loz]
    motif_edge = np.where(pet, np.minimum(motif_edge, np.abs(lz - 1.0) * 0.07), motif_edge)
    # bead
    bead_s = R.S_APEX - 0.30
    bd = np.hypot(ls - bead_s, lt)
    bead = pet & (bd < 0.085)
    out[bead] = col("gold")
    motif_edge = np.where(pet, np.minimum(motif_edge, np.abs(bd - 0.085)), motif_edge)
    # side lights in the petal head, violet
    head = pet & (ls > R.S_SPRING) & ~bead & (bd > 0.11)
    out[head] = (col("deep_violet") * 0.6 + field * 0.4)[head]

    # --- hub: sunburst
    hub = label == 1
    ang = np.arctan2(z, x)
    wedge = np.floor((ang + math.pi) / (2 * math.pi) * 12).astype(np.int64)
    wcol = np.where((np.mod(wedge, 2) == 0)[..., None], col("gold"), col("amber"))
    out[hub] = wcol[hub]
    ring = hub & (r > 0.36)
    out[ring] = col("crimson")
    core = hub & (r < 0.13)
    out[core] = col("deep_violet")
    wedge_frac = (ang + math.pi) / (2 * math.pi) * 12
    wedge_line = np.abs(wedge_frac - np.round(wedge_frac)) * (2 * math.pi / 12) * r
    hub_edges = np.minimum(np.minimum(np.abs(r - 0.36), np.abs(r - 0.13)), np.where(r > 0.13, wedge_line, 1.0))
    motif_edge = np.where(hub, np.minimum(motif_edge, hub_edges), motif_edge)

    # --- eyes: alternate gold / crimson
    eye = (label >= 200) & (label < 300)
    ek = np.mod(label - 200, 2)[..., None]
    out[eye] = np.where(ek == 0, col("gold"), col("crimson"))[eye]

    # --- roundels: violet/blue quarters, crimson or gold heart
    rnd = label >= 300
    rj = (label - 300)
    rr = np.hypot(ls, lt)
    quarter = (np.where(ls * lt >= 0, 1, 0))[..., None]
    rcol = np.where(quarter == 1, col("violet"), col("blue"))
    out[rnd] = rcol[rnd]
    heart = rnd & (rr < 0.075)
    hcol = np.where((np.mod(rj, 3) == 0)[..., None], col("gold"), col("crimson"))
    out[heart] = hcol[heart]
    cross = np.minimum(np.abs(ls), np.abs(lt))
    rnd_edges = np.minimum(np.abs(rr - 0.075), np.where(rr > 0.075, cross, 1.0))
    motif_edge = np.where(rnd, np.minimum(motif_edge, rnd_edges), motif_edge)

    glass = label > 0
    # per-piece value variation and streaky antique-glass texture
    streak = fbm(S, 24, 4, rng)
    streak2 = vnoise(S, 160, rng)
    shade = (0.78 + 0.34 * piece_rand2) * (0.86 + 0.22 * streak) * (0.95 + 0.1 * streak2)
    out *= shade[..., None]
    # matting: darker paint toward lead lines
    lead_d = np.minimum(edge, motif_edge)
    out *= (0.55 + 0.45 * smoothstep(0.0, 0.05, lead_d))[..., None]
    # lead cames
    lead = smoothstep(0.012, 0.006, lead_d)
    # stone areas (behind tracery) are painted as lead so any misalignment reads dark
    lead = np.where(glass, lead, 1.0)
    # soft fade toward the outer rim for the moulding overlap
    lead_col = np.array([0.02, 0.02, 0.025], np.float32)
    d = out * (1 - lead[..., None]) + lead_col * lead[..., None]

    # ORM
    rough = 0.12 * (1 - lead) + 0.6 * lead
    metal = 0.3 * lead
    orm = pack_orm(np.ones_like(rough), rough, metal)
    # normal: tilted panes + raised lead
    tilt = (hash_float(cell_id, 9) - 0.5) * 0.004 * (x / 0.12) + (hash_float(cell_id, 13) - 0.5) * 0.004 * (z / 0.12)
    height = tilt * 0.0 + streak * 0.6 + lead * 1.5
    n = normal_from_height_clamped(height.astype(np.float32), 1.2)
    save_set("GlassRose", np.clip(d, 0, 1), n, orm, report)
    report["GlassRose"]["note"] = "Procedural, original. Use _D as emissive colour (x ~8-20)."


def S_LOZ_END():
    return R.S_APEX - 0.45


def tex_lancet_glass(report):
    """Grisaille quarry glazing; tiles vertically, u spans the window width."""
    S = C.TEX_STD
    rng = np.random.default_rng(C.SEED + 21)
    u = (np.arange(S, dtype=np.float32) + 0.5) / S
    v = (np.arange(S, dtype=np.float32) + 0.5) / S
    U = np.broadcast_to(u[None, :], (S, S))
    V = np.broadcast_to(v[::-1][:, None], (S, S))
    border = 0.11
    inner = (U > border) & (U < 1 - border)
    # diamond lattice inside the border: 3 quarries across, 4 down per tile
    qu = (U - border) / (1 - 2 * border) * 3.0
    qv = V * 4.0
    a = qu + qv
    b = qu - qv
    da = np.abs(a - np.round(a))
    db = np.abs(b - np.round(b))
    qid = (np.floor(a).astype(np.int64) * 131 + np.floor(b).astype(np.int64) * 71)
    qr = hash_float(qid, 1)
    qr2 = hash_float(qid, 2)
    base = np.array([0.20, 0.25, 0.33], np.float32)
    colq = base * (0.75 + 0.4 * qr)[..., None]
    special = qr2 > 0.93
    colq = np.where(special[..., None], np.array([0.10, 0.18, 0.55], np.float32), colq)
    gold = qr2 > 0.985
    colq = np.where(gold[..., None], np.array([0.75, 0.50, 0.15], np.float32), colq)
    # painted quatrefoil dot in each quarry
    fa = a - np.floor(a) - 0.5
    fb = b - np.floor(b) - 0.5
    dot = np.hypot(fa, fb)
    paint = smoothstep(0.13, 0.09, dot) * 0.45
    colq = colq * (1 - paint[..., None])
    lead_inner = smoothstep(0.035, 0.018, np.minimum(da, db) / 1.0)
    # border: deep blue band with gold beads
    bcol = np.array([0.06, 0.10, 0.42], np.float32)
    bead_v = np.mod(V * 4.0, 1.0) - 0.5
    bu = np.where(U < 0.5, U - border / 2, U - (1 - border / 2))
    bead = np.hypot(bu / border * 2, bead_v * 2.2) < 0.55
    border_col = np.where(bead[..., None], np.array([0.80, 0.55, 0.15], np.float32), bcol)
    out = np.where(inner[..., None], colq, border_col)
    edge_lines = smoothstep(0.012, 0.005, np.minimum(np.abs(U - border), np.abs(U - (1 - border))))
    rim = smoothstep(0.012, 0.004, np.minimum(U, 1 - U))
    lead = np.clip(np.where(inner, lead_inner, 0.0) + edge_lines + rim, 0, 1)
    streak = fbm(S, 8, 4, rng)
    out = out * (0.85 + 0.25 * streak[..., None])
    d = out * (1 - lead[..., None]) + np.array([0.02, 0.02, 0.025]) * lead[..., None]
    rough = 0.15 * (1 - lead) + 0.6 * lead
    orm = pack_orm(np.ones_like(rough), rough, 0.3 * lead)
    n = normal_from_height(streak * 0.5 + lead * 1.5, 1.5)
    save_set("GlassLancet", np.clip(d, 0, 1).astype(np.float32), n, orm, report)
    report["GlassLancet"]["note"] = "Procedural, original. U spans the window width, tiles in V. Emissive use."


def tex_flame(report):
    """Two candle-flame variants side by side (RGBA, alpha = mask)."""
    W, H = C.TEX_SMALL, C.TEX_SMALL
    img = np.zeros((H, W, 4), np.float32)
    ys = 1.0 - (np.arange(H, dtype=np.float32) + 0.5) / H         # 0 bottom .. 1 top
    for vi in range(2):
        x0 = vi * W // 2
        xs = (np.arange(W // 2, dtype=np.float32) + 0.5) / (W // 2) * 2 - 1
        X, Y = np.meshgrid(xs, ys)
        lean = 0.0 if vi == 0 else 0.10
        Xc = X - lean * Y ** 2
        yy = np.clip((Y - 0.06) / 0.86, 0, 1)
        width = 0.62 * np.sin(np.pi * np.clip(yy, 0, 1) ** 0.62) * (1 - 0.15 * yy)
        width = np.maximum(width, 1e-3)
        d = np.abs(Xc) / width
        body = smoothstep(1.0, 0.55, d) * smoothstep(0.0, 0.08, yy) * smoothstep(1.0, 0.82, yy)
        core = smoothstep(0.75, 0.2, d) * smoothstep(0.62, 0.15, yy) * smoothstep(0.02, 0.15, yy)
        blue = smoothstep(0.6, 0.0, d) * smoothstep(0.16, 0.04, yy) * smoothstep(0.0, 0.05, yy)
        outer = np.stack([np.full_like(d, 1.0), 0.42 + 0.25 * (1 - yy), 0.08 + 0.05 * (1 - yy)], 2)
        corec = np.array([1.0, 0.93, 0.70], np.float32)
        bluec = np.array([0.25, 0.35, 0.9], np.float32)
        rgb = outer * (1 - core[..., None]) + corec * core[..., None]
        rgb = rgb * (1 - blue[..., None] * 0.6) + bluec * blue[..., None] * 0.6
        alpha = np.clip(body + blue * 0.5, 0, 1)
        img[:, x0:x0 + W // 2, :3] = rgb * alpha[..., None]
        img[:, x0:x0 + W // 2, 3] = alpha
    n = np.zeros((H, W, 3), np.float32)
    n[..., 0] = 0.5
    n[..., 1] = 0.5
    n[..., 2] = 1.0
    orm = pack_orm(np.ones((H, W), np.float32), np.ones((H, W), np.float32), np.zeros((H, W), np.float32))
    save_set("CandleFlame", np.clip(img, 0, 1), n, orm, report)
    report["CandleFlame"]["note"] = "Procedural, original. RGBA: premultiplied colour + alpha mask; left/right halves are two variants."


def tex_water(report):
    S = C.TEX_STD
    rng = np.random.default_rng(C.SEED + 31)
    t = (np.arange(S, dtype=np.float32) + 0.5) / S * 2 * math.pi
    X, Y = np.meshgrid(t, t)
    h = np.zeros((S, S), np.float32)
    for (fx, fy, amp, ph) in ((3, 1, 0.5, 0.3), (-2, 4, 0.35, 1.1), (5, -3, 0.25, 2.0), (1, 7, 0.18, 0.7), (8, 5, 0.1, 2.9)):
        h += amp * np.sin(fx * X + fy * Y + ph)
    h += 0.6 * fbm(S, 8, 4, rng)
    h = (h - h.min()) / (h.max() - h.min())
    n = normal_from_height(h, 6.0)
    d = np.zeros((S, S, 3), np.float32)
    d[...] = np.array([0.045, 0.06, 0.065], np.float32)
    d *= (0.9 + 0.2 * h)[..., None]
    orm = pack_orm(np.ones((S, S), np.float32), np.full((S, S), 0.04, np.float32), np.zeros((S, S), np.float32))
    save_set("Water", d, n, orm, report)
    report["Water"]["note"] = "Procedural ripple normal, tileable; 1 UV unit = 4 m on SM_Water."


def tex_decals(report):
    """2x2 atlas: [drip streaks | tide band] / [moss patch | silt patch]; alpha in D.A."""
    S = C.TEX_STD
    c = S // 2
    rng = np.random.default_rng(C.SEED + 41)
    rgba = np.zeros((S, S, 4), np.float32)
    rough = np.ones((S, S), np.float32)
    height = np.zeros((S, S), np.float32)
    yy, xx = np.mgrid[0:c, 0:c].astype(np.float32) / c
    window = (smoothstep(0.0, 0.08, xx) * smoothstep(1.0, 0.92, xx) *
              smoothstep(0.0, 0.06, yy) * smoothstep(1.0, 0.94, yy))
    n1 = fbm(c, 6, 4, rng)

    # drip streaks (top-left): long vertical streaks, strongest near the top
    a = np.zeros((c, c), np.float32)
    for i in range(46):
        x0 = rng.uniform(0.08, 0.92)
        w = rng.uniform(0.004, 0.02)
        L = rng.uniform(0.3, 0.95)
        s = rng.uniform(0.3, 1.0)
        wob = 0.01 * np.sin(yy * rng.uniform(6, 14) + rng.uniform(0, 6))
        prof = np.exp(-((xx - x0 - wob) / w) ** 2)
        fade = smoothstep(L, 0.02, yy)
        a = np.maximum(a, prof * fade * s)
    a = np.clip(a * (0.7 + 0.5 * n1), 0, 1) * window
    rgba[:c, :c, :3] = np.array([0.09, 0.10, 0.085])
    rgba[:c, :c, 3] = a
    rough[:c, :c] = 0.45
    height[:c, :c] = a * 0.3

    # tide band (top-right): sharp salt line with a diffuse stain below
    n2 = fbm(c, 8, 4, rng)
    line_y = 0.32 + 0.04 * (n2 - 0.5)
    salt = smoothstep(0.018, 0.0, np.abs(yy - line_y))
    stain = smoothstep(line_y - 0.01, line_y + 0.04, yy) * smoothstep(0.98, 0.55, yy) * (0.55 + 0.45 * n2)
    vwin = smoothstep(0.0, 0.06, yy) * smoothstep(1.0, 0.94, yy)          # tiles horizontally
    a2 = np.clip(salt * 0.8 + stain * 0.75, 0, 1) * vwin
    colr = (np.array([0.13, 0.13, 0.11]) * (1 - salt[..., None]) + np.array([0.46, 0.47, 0.44]) * salt[..., None])
    rgba[:c, c:, :3] = colr
    rgba[:c, c:, 3] = a2
    rough[:c, c:] = 0.55
    height[:c, c:] = salt * 0.4

    # moss patch (bottom-left)
    n3 = fbm(c, 5, 5, rng)
    rad = np.hypot(xx - 0.5, yy - 0.5)
    m = smoothstep(0.30, 0.55, n3 + 0.45 - rad * 0.9)
    a3 = np.clip(m, 0, 1) * window
    mc = np.array([0.07, 0.11, 0.05]) * (0.7 + 0.6 * n3[..., None])
    rgba[c:, :c, :3] = mc
    rgba[c:, :c, 3] = a3
    rough[c:, :c] = 0.92
    height[c:, :c] = a3 * n3

    # silt patch for the flooded floor (bottom-right)
    n4 = fbm(c, 4, 5, rng)
    s4 = smoothstep(0.35, 0.65, n4 + 0.35 - rad * 0.8)
    a4 = np.clip(s4 * 0.85, 0, 1) * window
    rgba[c:, c:, :3] = np.array([0.12, 0.115, 0.085]) * (0.8 + 0.4 * n4[..., None])
    rgba[c:, c:, 3] = a4
    rough[c:, c:] = 0.3
    height[c:, c:] = a4 * 0.3

    n = normal_from_height(height, 4.0)
    orm = pack_orm(np.ones((S, S), np.float32), rough, np.zeros((S, S), np.float32))
    save_set("DecalGrime", np.clip(rgba, 0, 1), n, orm, report)
    report["DecalGrime"]["note"] = ("Procedural, original 2x2 atlas: TL drip streaks, TR tide band, "
                                     "BL moss, BR silt. Alpha in T_DecalGrime_D.A.")


def build_all():
    os.makedirs(C.TEX_DIR, exist_ok=True)
    INPUTS_USED.clear()
    report = {}
    for fn in (tex_stone_ashlar, tex_stone_dressed, tex_floor, tex_wood, tex_iron, tex_wax, tex_cloth,
               tex_rose_glass, tex_lancet_glass, tex_flame, tex_water, tex_decals):
        fn(report)
        print("[tex] %s done" % fn.__name__)
    return report, dict(INPUTS_USED)
