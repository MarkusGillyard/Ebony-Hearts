"""Procedural, painterly-clean texture painters for the fighters. Every painter works on the texels
of one material (eh_tex.Raster), mostly as functions of the rest-pose 3D surface, and returns
D (sRGB colour [+ alpha]), N (OpenGL tangent-space) and ORM (AO, roughness, metallic) arrays."""
import math
import os

import numpy as np

import eh_body as Bd
import eh_garment as G
import eh_hair as H
import eh_mesh as M
import eh_tex as T

ACG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..",
                   "downloads", "thirdparty", "ambientCG")


def acg(name, kind):
    p = os.path.abspath(os.path.join(ACG, name, name + "_1K-JPG", "%s_1K-JPG_%s.jpg" % (name, kind)))
    return T.load_image(p)


_ACG_CACHE = {}


def acg_detail(name, uv, metres_per_uv, tile_m):
    """Samples a CC0 surface (luminance and OpenGL normal) tiled at tile_m metres."""
    if name not in _ACG_CACHE:
        col = acg(name, "Color")[..., :3]
        lum = col @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        _ACG_CACHE[name] = (lum[..., None], acg(name, "NormalGL")[..., :3])
    lum, nrm = _ACG_CACHE[name]
    tuv = uv * (metres_per_uv / tile_m)
    l = T.sample(lum, tuv)[:, 0]
    n = T.sample(nrm, tuv)
    return (l - l.mean()) / max(l.std(), 1e-4), n


def flat_n(K):
    n = np.zeros((K, 3), np.float32)
    n[:, :] = (0.5, 0.5, 1.0)
    return n


def gauss(P, c, r):
    return np.exp(-((P - np.asarray(c)) ** 2).sum(1) / (r * r))


# ============================================================================ skin

def skin(rs, body, rig, cfg, ctx):
    pal = {k: T.hexrgb(v) for k, v in cfg["palette"].items()}
    P, Nw = rs.P, rs.N
    K = rs.K
    reg = {r: rs.vattr([Bd.region(body, r)]) for r in ("lips", "fingernails", "toenails", "ears")}
    ao = rs.vattr([ctx["ao"]["body"]])
    hi = ctx["head"]
    base = np.tile(pal["skin"], (K, 1))
    lowf = T.fbm(P, 7.0, 3, seed=3)
    midf = T.fbm(P, 38.0, 2, seed=9)
    col = base * (1 + 0.035 * lowf[:, None] + 0.012 * midf[:, None])
    warm = np.array([0.86, 0.47, 0.40], np.float32)
    red = np.zeros(K, np.float32)
    eye_l, eye_r = hi["eye_l"], hi["eye_r"]
    for e, sg in ((eye_l, 1), (eye_r, -1)):
        red += 0.55 * gauss(P, e + np.array([0.012 * sg, -0.012, -0.036]), 0.022)       # cheeks
    red += 0.45 * gauss(P, hi["nose_tip"], 0.012)
    red += 0.35 * reg["ears"]
    B = {b.name: (np.array(b.head_local), np.array(b.tail_local)) for b in rig.data.bones}
    for s in "lr":
        red += 0.30 * gauss(P, B["calf_" + s][0] + np.array([0, -0.04, 0]), 0.045)       # knees
        red += 0.22 * gauss(P, B["lowerarm_" + s][0], 0.035)                               # elbows
        for f in ("index", "middle", "ring", "pinky"):
            red += 0.25 * gauss(P, B["%s_01_%s" % (f, s)][0], 0.012)                       # knuckles
            red += 0.25 * gauss(P, B["%s_03_%s" % (f, s)][1], 0.010)                       # finger tips
        red += 0.3 * gauss(P, B["ball_" + s][1], 0.03)                                     # toes
    col = T.mix(col, (col * 0.9 + warm * 0.1) * np.array([1.02, 0.9, 0.88]), np.clip(red, 0, 1) * 0.55)
    # lips
    lw = np.clip(M.smoothstep(0.15, 0.75, reg["lips"]), 0, 1)
    col = T.mix(col, pal["lips"] * (1 + 0.05 * midf[:, None]), lw * 0.78)
    # nails
    nails = np.clip(np.maximum(reg["fingernails"], reg["toenails"]), 0, 1)
    col = T.mix(col, np.clip(pal["skin"] * np.array([1.05, 0.96, 0.96]) + 0.06, 0, 1), nails * 0.8)
    # eyes: lid line, soft upper-lid shadow
    lid = np.zeros(K, np.float32)
    socket = np.zeros(K, np.float32)
    for e in (ctx["eyes"]["l"], ctx["eyes"]["r"]):
        d = np.linalg.norm(P - e["center"], axis=1) - e["radius"]
        front = (P[:, 1] < e["center"][1] + 0.002)
        up = M.smoothstep(e["center"][2] - 0.004, e["center"][2] + 0.004, P[:, 2])
        lid = np.maximum(lid, np.exp(-np.maximum(d, 0) / 0.0011) * front * (0.35 + 0.65 * up))
        socket = np.maximum(socket, gauss(P, e["center"] + np.array([0, -0.008, 0.008]), 0.017) * up)
    col = T.mix(col, col * np.array([0.42, 0.33, 0.33]), np.clip(lid, 0, 1) * 0.6)
    col = T.mix(col, col * np.array([0.86, 0.78, 0.78]), socket * 0.22)
    # brows root shading and hairline tint (skin under hair edges takes the hair colour)
    if ctx.get("brows_P") is not None:
        db = _nearest_dist(P, ctx["brows_P"], sel=P[:, 2] > hi["eye_l"][2])
        col = T.mix(col, pal["hair_dark"], np.exp(-db / 0.0025) * 0.35)
    if ctx.get("cap_collider") is not None:
        sel = P[:, 2] > hi["ear_l"][2] - 0.08
        d = np.full(K, 1.0, np.float32)
        d[sel] = _dist_to(ctx["cap_collider"], P[sel])
        col = T.mix(col, pal["hair"] * 0.9, np.exp(-d / 0.003) * 0.55)
    # ambient occlusion, warm in the shadow
    sh = np.clip(ao, 0, 1) ** 1.3
    col = col * (0.85 + 0.15 * sh[:, None]) * T.mix(np.ones((K, 3), np.float32), pal["skin_shadow"] / pal["skin"],
                                                    (1 - sh) * 0.15)
    nrm = Nw.copy()
    rough = 0.6 + 0.06 * midf - 0.12 * lw - 0.2 * nails
    # canon features
    if cfg.get("abs"):
        col, nrm = _abs(rs, cfg, ctx, col, nrm)
    if cfg.get("tattoo"):
        col, rough = _tattoo(rs, cfg, ctx, col, rough)
    D = np.clip(col, 0, 1)
    N = rs.tangent_space(nrm)
    ORM = np.stack([np.clip(ao * 0.85 + 0.15, 0, 1), np.clip(rough, 0.25, 0.9), np.zeros(K)], 1)
    return D, N, ORM


def _nearest_dist(P, Q, sel=None):
    from mathutils.kdtree import KDTree
    kd = KDTree(len(Q))
    for i, q in enumerate(Q):
        kd.insert(q, i)
    kd.balance()
    out = np.full(len(P), 1.0, np.float32)
    idx = np.nonzero(sel)[0] if sel is not None else range(len(P))
    for i in idx:
        out[i] = kd.find(P[i])[2]
    return out


def _dist_to(col, P):
    from mathutils import Vector
    out = np.empty(len(P), np.float32)
    for i, p in enumerate(P):
        r = col.bvh.find_nearest(Vector(p))
        out[i] = r[3] if r[0] is not None else 1.0
    return out


def _abs(rs, cfg, ctx, col, nrm):
    """Wren: defined abdominal muscles, painted and in the normal map (height field in 3D)."""
    a = cfg["abs"]
    zn = ctx["navel_z"]
    zt = ctx["underbust_z"]
    yf = ctx["spine_y_fn"]

    def h(P):
        x, z = P[:, 0], P[:, 2]
        ax = np.abs(x)
        region = M.smoothstep(zn - 0.06, zn - 0.02, z) * (1 - M.smoothstep(zt - 0.005, zt + 0.02, z)) \
            * (1 - M.smoothstep(0.075, 0.1, ax)) * (P[:, 1] < yf(z) - 0.03)
        g = np.exp(-(x / 0.0055) ** 2) * M.smoothstep(zn - 0.04, zn + 0.01, z)
        rows = 0
        for zi, wi in ((zn + 0.04, 0.85), (zn + 0.095, 1.0), (zn + 0.15, 0.9)):
            rows = rows + wi * np.exp(-((z - zi) / 0.0065) ** 2) * (1 - M.smoothstep(0.045, 0.068, ax))
        lat = np.exp(-((ax - 0.072) / 0.009) ** 2) * M.smoothstep(zn - 0.05, zn, z)
        bump = np.sin(np.clip((ax - 0.004) / 0.066, 0, 1) * math.pi) * 0.35
        return region * (bump - 1.0 * g - 0.9 * rows - 0.8 * lat)

    hv = h(rs.P)
    gr = T.grad3(h, rs.P, 0.002)
    nrm = T.perturb(nrm, gr, a["normal_strength"])
    shade = np.clip(hv, -1, 1)
    col = col * (1 + a["paint_strength"] * shade[:, None])
    return col, nrm


def tattoo_mask(u, v):
    """The lantern-cross emblem: signed-distance shapes in centimetre units (u right, v up)."""
    def box(cx, cy, hx, hy):
        return np.maximum(np.abs(u - cx) - hx, np.abs(v - cy) - hy)

    def rbox(cx, cy, hx, hy, r):
        qx = np.abs(u - cx) - hx + r
        qy = np.abs(v - cy) - hy + r
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

    ring = np.abs(np.hypot(u, v - 3.15) - 0.5) - 0.11
    stem = box(0, 2.25, 0.13, 0.42)
    bar = box(0, 1.7, 2.05, 0.2)
    caps = np.minimum(np.hypot(u - 2.05, v - 1.7) - 0.3, np.hypot(u + 2.05, v - 1.7) - 0.3)
    cage = np.abs(rbox(0, -0.1, 1.1, 1.45, 0.45)) - 0.14
    post_top = box(0, 1.1, 0.1, 0.35)
    base = box(0, -1.75, 1.45, 0.17)
    tail = np.maximum(box(0, -2.85, 0.24, 1.0), -(v + 3.85 - 2.2 * np.abs(u)))
    fl_v = (v + 0.55) / 1.25
    flame = np.hypot(u / (0.48 * np.clip(1 - fl_v ** 2, 0, 1) ** 0.5 * (1 - 0.45 * fl_v) + 1e-3), 1.0) - 1.0
    flame = np.where((fl_v > -1) & (fl_v < 1), np.abs(u) - 0.48 * np.sqrt(np.clip(1 - fl_v ** 2, 0, 1)) * (1 - 0.4 * fl_v), 1.0)
    inner = np.where((fl_v > -0.6) & (fl_v < 0.5), np.abs(u) - 0.18 * np.sqrt(np.clip(1 - ((fl_v + 0.05) / 0.55) ** 2, 0, 1)), 1.0)
    flame = np.maximum(flame, -inner + 0.0)
    d = np.minimum.reduce([ring, stem, bar, caps, cage, post_top, base, tail, flame])
    return d


def _tattoo(rs, cfg, ctx, col, rough):
    t = cfg["tattoo"]
    c = ctx["tattoo_center"]
    s = t["size_cm"] / 7.0          # the design is ~7 units tall
    u = (rs.P[:, 0] - c[0]) * 100 / s
    v = (rs.P[:, 2] - c[2]) * 100 / s
    front = M.smoothstep(0.2, 0.5, -rs.N[:, 1])
    d = tattoo_mask(u, v)
    a = (1 - M.smoothstep(-0.03, 0.07, d)) * front * (np.abs(u) < 5) * (np.abs(v) < 5)
    ink = T.hexrgb(cfg["palette"]["tattoo"])
    var = 1 + 0.05 * T.vnoise3(rs.P, 900.0, 4)
    col = T.mix(col, (col * 0.12 + ink * 0.88) * var[:, None], a * 0.96)
    return col, rough - 0.04 * a


# ============================================================================ eyes

def eyes(rs, cfg, ctx):
    pal = {k: T.hexrgb(v) for k, v in cfg["palette"].items()}
    K = rs.K
    P = rs.P
    col = np.zeros((K, 3), np.float32)
    rough = np.full(K, 0.22, np.float32)
    for side in ("l", "r"):
        e = ctx["eyes"][side]
        sel = (P[:, 0] > 0) if side == "l" else (P[:, 0] <= 0)
        d = P[sel] - e["center"]
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        f = np.array([0, -1.0, 0])
        th = np.arccos(np.clip(d @ f, -1, 1))
        a1 = np.cross(f, [0, 0, 1.0])
        phi = np.arctan2(d @ np.array([0, 0, 1.0]), d @ a1)
        ti = cfg["eye"]["iris_angle"]
        tp = cfg["eye"]["pupil_angle"]
        r = th / ti
        fib = 0.5 + 0.5 * np.sin(phi * 37 + 3 * np.sin(phi * 7)) * np.sin(phi * 61 + 1.3)
        ring = M.smoothstep(0.78, 1.0, r)
        iris = T.mix(pal["iris"] * 1.25, pal["iris"], M.smoothstep(0.25, 0.7, r))
        iris = T.mix(iris, pal["iris_dark"], ring * 0.85)
        iris = iris * (0.72 + 0.28 * fib[:, None] * (1 - ring[:, None]))
        iris = np.clip(iris, 0, 1)
        pupil = M.smoothstep(tp / ti + 0.04, tp / ti - 0.02, r)
        iris = T.mix(iris, np.array([0.02, 0.02, 0.025]), pupil)
        scl = np.array([0.86, 0.84, 0.81], np.float32) * (1 - 0.12 * M.smoothstep(1.2, 2.2, th))[:, None]
        scl = T.mix(scl, np.array([0.9, 0.72, 0.7]), M.smoothstep(1.1, 1.6, th) * np.abs(np.cos(phi)) * 0.4)
        inside = M.smoothstep(1.03, 0.98, r)
        c = T.mix(scl, iris, inside)
        col[sel] = c
        rough[sel] = 0.12 + 0.1 * (1 - inside)
    D = col
    N = flat_n(K)
    ORM = np.stack([np.ones(K), rough, np.zeros(K)], 1)
    return D, N, ORM


# ============================================================================ hair

def hair(rs, cfg, ctx, hair_ob):
    pal = {k: T.hexrgb(v) for k, v in cfg["palette"].items()}
    K = rs.K
    uv = rs.uv()
    u, v = uv[:, 0], uv[:, 1]
    part = np.rint(rs.vattr([G.get_attr(hair_ob, "part")])).astype(int)
    ao_v = rs.vattr([ctx["ao"]["hair"]])
    col = np.zeros((K, 3), np.float32)
    alpha = np.ones(K, np.float32)
    rough = np.full(K, 0.72, np.float32)
    h = np.zeros(K, np.float32)
    ao = np.ones(K, np.float32)

    def streaks(uu, vv, freq, seed):
        n1 = T.vnoise2(np.stack([uu * freq, vv * 3.0], 1), 1.0, seed)
        n2 = T.vnoise2(np.stack([uu * freq * 2.7, vv * 7.0], 1), 1.0, seed + 1)
        return 0.6 * n1 + 0.4 * n2

    def in_rect(rc):
        return (u >= rc[0]) & (u < rc[2]) & (v >= rc[1]) & (v < rc[3])

    # cap: strands along v
    m = in_rect(H.CAP)
    s = streaks(u[m] / 0.5, v[m], 260.0, 11)
    base = T.mix(pal["hair_dark"], pal["hair"], 0.5 + 0.5 * s)
    hl = M.smoothstep(0.45, 0.95, s) * 0.3
    col[m] = T.mix(base, pal["hair_light"], hl)
    h[m] = s
    ao[m] = np.clip(ao_v[m], 0, 1)
    ed = rs.vattr([G.get_attr(hair_ob, "edge_d")])[m]
    rag = T.vnoise2(np.stack([u[m] * 420, v[m] * 30], 1), 1.0, 77)
    alpha[m] = M.smoothstep(0.002, 0.006, ed + 0.003 * rag)
    # braid strip: strands along v, lobe shading periodic in v
    m = in_rect(H.BRAID)
    uu = (u[m] - H.BRAID[0]) / (H.BRAID[2] - H.BRAID[0])
    per = ctx["braid_periods"]
    depth = np.sin(4 * math.pi * v[m] * per)
    side = 0.5 + 0.5 * np.cos((uu - 0.25) * 2 * math.pi)          # 1 on the outer face
    s = streaks(uu, v[m] * per * 0.5, 60.0, 21)
    lobe = M.smoothstep(-0.9, 0.7, depth)
    base = T.mix(pal["hair_dark"], pal["hair"], 0.45 + 0.35 * s + 0.2 * lobe)
    col[m] = T.mix(base, pal["hair_light"], M.smoothstep(0.2, 0.9, s) * lobe * side * 0.55)
    ao[m] = (0.45 + 0.55 * lobe) * (0.7 + 0.3 * side)
    h[m] = s * 0.6 + lobe * 0.8
    # loose strands (bangs, face strands, tassels)
    m = in_rect(H.STRAND)
    uu = (u[m] - H.STRAND[0]) / (H.STRAND[2] - H.STRAND[0])
    vv = (v[m] - H.STRAND[1]) / (H.STRAND[3] - H.STRAND[1])
    s = streaks(uu, vv, 70.0, 31)
    side = 0.5 + 0.5 * np.cos((uu - 0.25) * 2 * math.pi)
    base = T.mix(pal["hair_dark"], pal["hair"], 0.45 + 0.4 * s)
    base = T.mix(base, pal["hair_dark"], (1 - M.smoothstep(0.0, 0.3, vv)) * 0.35)
    col[m] = T.mix(base, pal["hair_light"], M.smoothstep(0.25, 0.9, s) * side * 0.35)
    ao[m] = 0.7 + 0.3 * side
    h[m] = s
    # ties
    m = in_rect(H.TIE)
    tie = np.tile(T.hexrgb(cfg["hair"]["tie_color"]), (m.sum(), 1))
    if cfg["hair"].get("tie_stripe"):
        vv = (v[m] - H.TIE[1]) / (H.TIE[3] - H.TIE[1])
        stripe = (np.abs(((u[m] - H.TIE[0]) / (H.TIE[2] - H.TIE[0])) * 10 % 1 - 0.5) < 0.18)
        tie = T.mix(tie, T.hexrgb(cfg["hair"]["tie_stripe"]), stripe.astype(np.float32))
    col[m] = tie
    rough[m] = 0.55
    # brows and lashes: CC0 MakeHuman alpha masks resampled into the atlas, tinted
    for rect, img, tint in ((H.BROW, ctx["brow_png"], pal["hair_dark"] * 0.8 + pal["hair"] * 0.2),
                            (H.LASH, ctx["lash_png"], pal["hair_dark"] * 0.35)):
        m = in_rect(rect)
        uu = (u[m] - rect[0]) / (rect[2] - rect[0])
        vv = (v[m] - rect[1]) / (rect[3] - rect[1])
        a = np.clip(T.sample(img, np.stack([uu, vv], 1), wrap=False)[:, 3] * 1.9, 0, 1)
        col[m] = tint
        alpha[m] = a
        rough[m] = 0.5
    # normal map from the strand height field (UV space, so tangent space directly)
    N = _uv_height_normals(rs, h, 0.6)
    col = col * (0.55 + 0.45 * np.clip(ao, 0, 1))[:, None]
    D = np.concatenate([np.clip(col, 0, 1), alpha[:, None]], 1)
    ORM = np.stack([np.clip(ao, 0, 1), np.clip(rough + 0.05 * h, 0.3, 0.8), np.zeros(K)], 1)
    return D, N, ORM


def _uv_height_normals(rs, h, strength):
    img, cov = rs.to_image(h, 1)
    img = T.dilate(img, cov, 4)[..., 0]
    gx = (np.roll(img, -1, 1) - np.roll(img, 1, 1)) * 0.5
    gy = (np.roll(img, -1, 0) - np.roll(img, 1, 0)) * 0.5
    n = np.stack([-gx * strength, -gy * strength, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n = n.reshape(-1, 3)[rs.pix]
    return n * 0.5 + 0.5


# ============================================================================ garments

def boundary_band(ob, rings=1.5):
    """Per-vertex 0..1: 1 on open edges (and the turned-under lip), fading over `rings` edge rings."""
    adj = M.adjacency(ob)
    b = M.boundary_vmask(ob) | (G.get_attr(ob, "lip") > 0.5)
    d = M.ring_distance(adj, b, 6)
    return np.exp(-np.minimum(d, 6) / rings).astype(np.float32)


def fabric(rs, ob_list, name, tile_m, uvs, strength=0.6):
    mpu = np.mean([G.uv_scale_m(ob) for ob in ob_list])
    lum, nrm = acg_detail(name, uvs, mpu, tile_m)
    return lum, nrm, mpu


def garments(rs, cfg, ctx, objs, spec):
    """Generic garment painter. spec[part] = dict(color, rough, metal, fabric, tile, trim, trim_color,
    detail, stitch). Returns D, N, ORM."""
    K = rs.K
    uv = rs.uv()
    part = np.zeros(K, int)
    band = np.zeros(K, np.float32)
    ao = rs.vattr([ctx["ao"].get(o.name) for o in objs])
    parts = rs.vattr([G.get_attr(o, "part").astype(np.float32) for o in objs])
    part = np.rint(parts).astype(int)
    if "_zones" in spec:
        fn, names = spec["_zones"]
        attrs = {nm: rs.vattr([G.get_attr(o, nm) for o in objs]) for nm in names}
        part = fn(part, attrs, rs)
    band = rs.vattr([boundary_band(o) for o in objs])
    col = np.zeros((K, 3), np.float32)
    rough = np.zeros(K, np.float32)
    metal = np.zeros(K, np.float32)
    nts = flat_n(K)
    lf = T.fbm(rs.P, 12.0, 2, seed=41)
    mpu = np.mean([G.uv_scale_m(o) for o in objs])
    for pid, sp in spec.items():
        if not isinstance(pid, int):
            continue
        m = part == pid
        if not m.any():
            continue
        c = np.tile(T.hexrgb(sp["color"]), (m.sum(), 1))
        r = np.full(m.sum(), sp.get("rough", 0.7), np.float32)
        if sp.get("fabric"):
            lum, n = acg_detail(sp["fabric"], uv[m], mpu, sp.get("tile", 0.12))
            c = c * (1 + sp.get("fabric_lum", 0.06) * lum[:, None])
            n = n * 2 - 1
            n[:, :2] *= sp.get("fabric_n", 1.0)
            n /= np.linalg.norm(n, axis=1, keepdims=True)
            nts[m] = n * 0.5 + 0.5
            r = r + 0.05 * lum
        if sp.get("trim"):
            t = M.smoothstep(sp.get("trim_lo", 0.55), sp.get("trim_hi", 0.8), band[m])
            c = T.mix(c, T.hexrgb(sp["trim"]), t)
        if sp.get("stitch"):
            st = np.exp(-((band[m] - sp.get("stitch_at", 0.32)) / 0.03) ** 2)
            dash = (np.sin((rs.P[m] @ np.array([1.0, 0.7, 1.3])) * 900) > -0.2)
            c = T.mix(c, T.hexrgb(sp["stitch"]), st * dash * 0.75)
        c = c * (1 + 0.04 * lf[m][:, None])
        col[m] = c
        rough[m] = r
        metal[m] = sp.get("metal", 0.0)
    for fn in spec.get("_extra", []):
        col, nts, rough, metal = fn(rs, part, col, nts, rough, metal, ctx)
    sh = np.clip(ao, 0, 1)
    col = col * (0.6 + 0.4 * sh[:, None])
    D = np.clip(col, 0, 1)
    ORM = np.stack([np.clip(sh * 0.85 + 0.15, 0, 1), np.clip(rough, 0.05, 1), np.clip(metal, 0, 1)], 1)
    return D, nts, ORM
