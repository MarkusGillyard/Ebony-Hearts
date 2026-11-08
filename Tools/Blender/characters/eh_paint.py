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
    # cavities (toe and finger gaps, knuckles, ear folds, lid creases): darker and warmer
    cav = rs.vattr([cavity(body)])
    feet = rs.vattr([sum(M.weights(body, ["ball_l", "ball_r"]).values())])
    k_cav = np.clip(cav / 0.0012, 0, 1) * (0.22 + 0.35 * np.clip(feet * 2, 0, 1))
    col = T.mix(col, col * np.array([0.62, 0.48, 0.45]), k_cav)
    ao = ao * (1 - 0.35 * k_cav)
    # ambient occlusion, warm in the shadow
    sh = np.clip(ao, 0, 1) ** 1.3
    col = col * (0.85 + 0.15 * sh[:, None]) * T.mix(np.ones((K, 3), np.float32), pal["skin_shadow"] / pal["skin"],
                                                    (1 - sh) * 0.15)
    nrm = Nw.copy()
    rough = 0.6 + 0.06 * midf - 0.12 * lw - 0.2 * nails
    if cfg.get("face"):
        col, nrm, rough = _face_detail(rs, cfg, ctx, col, nrm, rough, lw, pal)
    # canon features
    if cfg.get("abs"):
        col, nrm = _abs(rs, cfg, ctx, col, nrm)
    if cfg.get("tattoo"):
        col, rough = _tattoo(rs, cfg, ctx, col, rough)
    D = np.clip(col, 0, 1)
    N = rs.tangent_space(nrm)
    ORM = np.stack([np.clip(ao * 0.85 + 0.15, 0, 1), np.clip(rough, 0.25, 0.9), np.zeros(K)], 1)
    return D, N, ORM


def _face_detail(rs, cfg, ctx, col, nrm, rough, lw, pal):
    """Facial structure in paint and normal: soft contour under the cheekbones, at the temples and
    under the jaw, light on the nose bridge, forehead and cheekbone tops; upper-lid crease, lip line
    and vermilion border; T-zone sheen; fine skin relief."""
    fc = cfg["face"]
    P = rs.P
    hi = ctx["head"]
    el, er = hi["eye_l"], hi["eye_r"]
    nose = hi["nose_tip"]
    K = rs.K
    shade = np.zeros(K, np.float32)
    light = np.zeros(K, np.float32)
    for e, sg in ((el, 1.0), (er, -1.0)):
        shade += 0.35 * gauss(P, e + np.array([sg * 0.04, 0.03, -0.05]), 0.018)         # under the cheekbone
        shade += 0.5 * gauss(P, e + np.array([sg * 0.045, 0.03, 0.01]), 0.018)          # temple
        shade += 0.35 * gauss(P, e + np.array([-sg * 0.012, 0.004, 0.0]), 0.008)        # inner socket
        light += 0.6 * gauss(P, e + np.array([sg * 0.018, -0.006, -0.026]), 0.016)     # cheekbone top
    light += 0.7 * gauss(P, np.array([0.0, nose[1] + 0.012, el[2] - 0.012]), 0.009)    # nose bridge
    light += 0.5 * gauss(P, np.array([0.0, el[1] + 0.005, el[2] + 0.05]), 0.025)        # forehead
    head_z = hi["head"][2]
    face = M.smoothstep(head_z - 0.14, head_z - 0.06, P[:, 2]) * M.smoothstep(hi["head"][1] + 0.05, hi["head"][1] - 0.01, P[:, 1])
    shade *= face
    light *= face
    col = col * (1 - fc["contour"] * np.clip(shade, 0, 1))[:, None] * np.array([1.0, 0.97, 0.97])
    col = col * (1 + fc["highlight"] * np.clip(light, 0, 1))[:, None]
    # upper-lid crease
    for e in (ctx["eyes"]["l"], ctx["eyes"]["r"]):
        c = e["center"]
        d = np.linalg.norm(P - (c + np.array([0, -0.004, 0.012])), axis=1) - e["radius"]
        crease = np.exp(-(d / 0.0016) ** 2) * (P[:, 2] > c[2] + 0.006) * (P[:, 1] < c[1])
        col = col * (1 - 0.18 * crease)[:, None]
    # lips: vermilion border and the line between the lips
    lip_b = np.clip(lw, 0, 1)
    border = lip_b * (1 - lip_b) * 4
    col = col * (1 - 0.1 * border)[:, None]
    mz = float(np.mean(P[lw > 0.6, 2])) if (lw > 0.6).any() else nose[2] - 0.03
    line = np.exp(-((P[:, 2] - mz) / 0.0012) ** 2) * (lw > 0.25)
    col = col * (1 - 0.35 * line)[:, None]
    rough = rough - 0.06 * lip_b * (P[:, 2] < mz)
    # T-zone sheen, fine relief
    tz = (gauss(P, np.array([0.0, el[1], el[2] + 0.04]), 0.03) + gauss(P, nose, 0.018)) * face
    rough = rough - fc["tzone"] * np.clip(tz, 0, 1)
    idx = face > 0.01
    gr = T.grad3(lambda Q: T.fbm(Q, 900.0, 2, seed=77), P[idx], 0.0004)
    nrm = nrm.copy()
    nrm[idx] = T.perturb(nrm[idx], gr, fc["relief"])
    return col, nrm, rough


def cavity(ob, smooth_iters=2):
    """Per-vertex concavity (m): how far the one-ring average lies above the vertex along its normal."""
    adj = M.adjacency(ob)
    V = M.co(ob)
    lap = M.neighbour_mean(V, adj) - V
    c = (lap * M.vnormals(ob)).sum(1)
    return M.smooth(np.maximum(c, 0), adj, smooth_iters, 0.5).astype(np.float32)


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
        iris = T.mix(pal["iris"] * cfg["eye"].get("iris_center", 1.25), pal["iris"], M.smoothstep(0.25, 0.7, r))
        iris = T.mix(iris, pal["iris_dark"], ring * 0.85)
        iris = iris * (0.72 + 0.28 * fib[:, None] * (1 - ring[:, None]))
        iris = np.clip(iris, 0, 1)
        pupil = M.smoothstep(tp / ti + 0.04, tp / ti - 0.02, r)
        iris = T.mix(iris, np.array([0.02, 0.02, 0.025]), pupil)
        scl = np.array([0.86, 0.84, 0.81], np.float32) * (1 - 0.12 * M.smoothstep(1.2, 2.2, th))[:, None]
        scl = T.mix(scl, np.array([0.9, 0.72, 0.7]), M.smoothstep(1.1, 1.6, th) * np.abs(np.cos(phi)) * 0.4)
        inside = M.smoothstep(1.03, 0.98, r)
        c = T.mix(scl, iris, inside)
        if cfg["eye"].get("lid_shadow"):
            el = d @ np.array([0, 0, 1.0])
            c = c * (1 - cfg["eye"]["lid_shadow"] * M.smoothstep(0.05, 0.42, el))[:, None]
            c = c * (1 - 0.15 * M.smoothstep(-0.2, -0.5, el))[:, None]
            c = T.mix(c, np.array([0.8, 0.55, 0.52]), M.smoothstep(1.25, 1.65, th) * 0.35)
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
    s = streaks(u[m] / (H.CAP[2] - H.CAP[0]), v[m], 260.0, 11)
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
    if H.CARD is not None:
        m = in_rect(H.CARD)
        uu = (u[m] - H.CARD[0]) / (H.CARD[2] - H.CARD[0])
        vv = (v[m] - H.CARD[1]) / (H.CARD[3] - H.CARD[1])
        a_c, tone, hc = _card_strands(uu, vv, (H.CARD[2] - H.CARD[0]) * rs.res)
        base = T.mix(pal["hair_dark"], pal["hair"], np.clip(0.35 + 0.65 * tone, 0, 1))
        base = T.mix(base, pal["hair_dark"], (1 - M.smoothstep(0.0, 0.25, vv)) * 0.45)
        col[m] = T.mix(base, pal["hair_light"], M.smoothstep(0.55, 1.0, tone) * 0.45 * M.smoothstep(0.1, 0.5, vv))
        alpha[m] = a_c
        ao[m] = 0.62 + 0.38 * a_c
        h[m] = hc
        rough[m] = 0.62
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


def _card_strands(uu, vv, width_px, n_clumps=11, per=9, seed=13):
    """Alpha texture for hair cards (uu across 0..1, vv root 0 .. tip 1): clumps of strands that
    converge towards each clump's tip (varied lengths, slight waves), solid at the root and separating
    into points towards the tips. Returns (alpha, tone 0..1, height)."""
    rng = np.random.default_rng(seed)
    alpha = np.zeros(len(uu), np.float32)
    tone = np.zeros(len(uu), np.float32)
    hgt = np.zeros(len(uu), np.float32)
    for c in range(n_clumps):
        cu = (c + 0.5 + (rng.random() - 0.5) * 0.4) / n_clumps
        L = 0.7 + 0.3 * rng.random()
        halfw = (0.55 + 0.35 * rng.random()) / n_clumps
        wave = rng.random() * 6.28
        cline = cu + 0.012 * np.sin(vv * 7.0 + wave)
        prof = np.clip(1 - (vv / L) ** 1.6, 0, 1) ** 0.6           # clump narrows to its tip
        dclump = np.abs(((uu - cline) + 0.5) % 1.0 - 0.5)
        inside = M.smoothstep(halfw * prof + 1.2 / width_px, halfw * prof - 0.6 / width_px, dclump)
        inside *= (vv < L)
        # individual strands inside the clump (fine lines with gaps)
        lines = np.zeros(len(uu), np.float32)
        for k in range(per):
            off = (k / (per - 1) - 0.5) * 2 * halfw * prof * 0.9
            w = (0.7 + 0.8 * rng.random()) / width_px
            dl = np.abs(((uu - cline - off) + 0.5) % 1.0 - 0.5)
            lines = np.maximum(lines, np.exp(-(dl / w) ** 2))
        a = inside * np.clip(0.55 + 0.6 * lines, 0, 1)
        t_c = rng.random()
        better = a > alpha
        tone = np.where(better, t_c * 0.6 + 0.4 * lines, tone)
        hgt = np.maximum(hgt, inside * (0.5 + 0.5 * lines) * prof)
        alpha = np.maximum(alpha, a)
    root = 1 - M.smoothstep(0.05, 0.3, vv)
    alpha = np.clip(np.maximum(alpha, root), 0, 1)
    # cards use the halves [0, .5] or [.5, 1]: fade towards those borders so no card shows a straight edge
    de = np.minimum.reduce([uu, np.abs(uu - 0.5), 1 - uu])
    alpha = alpha * M.smoothstep(0.0, 0.07, de) ** 0.7
    return alpha.astype(np.float32), tone.astype(np.float32), hgt.astype(np.float32)


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

_DETAIL = {}


def detail_tex(name):
    """CC0 surface as one (h, w, 4) array: normalised luminance + OpenGL normal (-1..1)."""
    if name not in _DETAIL:
        col = acg(name, "Color")[..., :3]
        lum = col @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        lum = (lum - lum.mean()) / max(lum.std(), 1e-4)
        nrm = acg(name, "NormalGL")[..., :3] * 2 - 1
        _DETAIL[name] = np.concatenate([lum[..., None], nrm], -1).astype(np.float32)
    return _DETAIL[name]


def sample_detail(name, grain, tile_m, texel_m, sel=None):
    """Prefiltered CC0 detail in grain space: (luminance (K,), tangent-space normal (K,3) in -1..1)."""
    gu, gv, c, s_ = (g if sel is None else g[sel] for g in grain)
    img = detail_tex(name)
    foot = texel_m / (tile_m / img.shape[1])
    smp = T.sample_filtered(name, img, np.stack([gu / tile_m, gv / tile_m], 1), foot)
    n = smp[:, 1:4]
    nx = n[:, 0] * c + n[:, 1] * s_
    ny = -n[:, 0] * s_ + n[:, 1] * c
    return smp[:, 0], np.stack([nx, ny, np.maximum(n[:, 2], 0.05)], 1)


def weave(kind, gu, gv, pitch, texel_m, ed=None, es=None):
    """Procedural cloth relief (unit amplitude) in grain coordinates (edge_* kinds run parallel /
    across the nearest edge: bandage threads); fades out where a period would span fewer than ~4
    texels (no aliasing)."""
    k = 2 * math.pi / pitch
    fade = M.smoothstep(3.0, 5.5, pitch / texel_m)
    if kind == "twill":
        h = np.sin(k * (gu + gv) / math.sqrt(2))
    elif kind == "rib":
        h = np.sin(k * gu)
    elif kind == "rib_h":
        h = np.sin(k * gv)
    elif kind == "plain":
        h = np.sin(k * gu) * np.sin(k * gv)
    elif kind == "jersey":
        h = np.abs(np.sin(k * 0.5 * gu)) * 2 - 1 + 0.35 * np.sin(k * gv * 0.8 + 1.5 * np.sin(k * 0.5 * gu))
    elif kind == "edge_rib":
        h = np.sin(k * ed) * 0.8 + 0.2 * np.sin(k * 0.45 * es)
    elif kind == "crepe":
        h = 0.6 * np.sin(k * gu) * np.sin(k * gv) + 0.4 * T.vnoise2(np.stack([gu, gv], 1), 2.5 / pitch, 5)
    else:
        h = np.zeros_like(gu)
    return (h * fade).astype(np.float32)


def stitch_line(d, along, at, width=0.0005, dash=0.0035, duty=0.62):
    """Running stitch: a dashed line `at` metres from an edge (d = distance to the edge)."""
    line = np.exp(-((d - at) / width) ** 2)
    ph = np.mod(along / dash, 1.0)
    return line * M.smoothstep(0.0, 0.12, ph) * (1 - M.smoothstep(duty, duty + 0.12, ph))


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


def garment_edges(ob):
    """edge_d / edge_s attributes (see eh_mesh.edge_fields) with the turned-under lip as edge."""
    lip = G.get_attr(ob, "lip") > 0.5
    d, s_ = M.edge_fields(ob, extra_seed=lip)
    G.set_float_attr(ob, "edge_d", d)
    G.set_float_attr(ob, "edge_s", s_)


def garments(rs, cfg, ctx, objs, spec):
    """Garment painter. spec[part] = dict(
        color, rough, metal               base values (sRGB hex, 0..1)
        rough_var                         roughness variation with the detail luminance
        detail=(name, tile_m, lum, n)     CC0 surface in grain space, prefiltered
        weave=(kind, pitch_m, height_m)   procedural relief (see weave)
        mottle                            low-frequency tonal variation (dye/wear), 0..1
        hem=dict(w, color, rough, stitch=[(at, color)], roll)   edge binding / turned hem (metres)
        stitch=[(at_m, color)]            stitch lines parallel to every edge
        edge_wear                         lightening of the outermost mm of edges
        sheen                             lowers roughness on grazing (in this painter: a flat bias)
    ); spec["_zones"] = fn(part, rs, ctx, attrs) for 3D zone splits, spec["_seams"] = [fn(rs, ctx) ->
    (mask_part_ids, signed distance m, along m)], spec["_height"] = [fn(rs, part, ctx) -> metres],
    spec["_extra"] = [fn(rs, part, col, nts, rough, metal, ctx)]. Returns D, N, ORM."""
    K = rs.K
    texel_m = ctx["texel_m"]
    ao = rs.vattr([ctx["ao"].get(o.name) for o in objs])
    part = np.rint(rs.vattr([G.get_attr(o, "part").astype(np.float32) for o in objs])).astype(int)
    attrs = {}
    for nm in ("edge_d", "edge_s", "lip") + tuple(spec.get("_attrs", ())):
        attrs[nm] = rs.vattr([G.get_attr(o, nm) for o in objs])
    if "_zones" in spec:
        fn = spec["_zones"]
        if isinstance(fn, tuple):        # legacy (fn, names): fn(part, attrs, rs)
            f, names = fn
            part = f(part, {nm: rs.vattr([G.get_attr(o, nm) for o in objs]) for nm in names}, rs)
        else:
            part = fn(part, rs, ctx, attrs)
    mpu = ctx["mpu"]
    grain = rs.grain(mpu)
    gu, gv = grain[0], grain[1]
    col = np.zeros((K, 3), np.float32)
    rough = np.zeros(K, np.float32)
    metal = np.zeros(K, np.float32)
    height = np.zeros(K, np.float32)
    dn = np.zeros((K, 3), np.float32)
    dn[:, 2] = 1.0
    ed = attrs["edge_d"]
    es = attrs["edge_s"]
    lf = T.fbm(rs.P, 9.0, 3, seed=41)
    for pid, sp in spec.items():
        if not isinstance(pid, (int, np.integer)):
            continue
        m = part == pid
        if not m.any():
            continue
        c = np.tile(T.hexrgb(sp["color"]), (m.sum(), 1))
        r = np.full(m.sum(), sp.get("rough", 0.7), np.float32)
        if sp.get("detail"):
            name, tile, la, na = sp["detail"]
            lum, n = sample_detail(name, grain, tile, texel_m, m)
            c = c * (1 + la * np.clip(lum, -2.5, 2.5)[:, None])
            r = r + sp.get("rough_var", 0.04) * np.clip(lum, -2.5, 2.5)
            n[:, :2] *= na
            dn[m] = n
        if sp.get("weave"):
            kind, pitch, hgt = sp["weave"]
            wv = weave(kind, gu[m], gv[m], pitch, texel_m, ed[m], es[m])
            height[m] += wv * hgt
            c = c * (1 + 0.05 * wv[:, None] * sp.get("weave_tone", 1.0))
        if sp.get("mottle"):
            c = c * (1 + sp["mottle"] * lf[m][:, None])
        if sp.get("hem"):
            hm = sp["hem"]
            band = 1 - M.smoothstep(hm["w"] - 0.0007, hm["w"] + 0.0004, ed[m])
            if hm.get("color"):
                c = T.mix(c, T.hexrgb(hm["color"]), band * hm.get("amount", 1.0))
            if hm.get("rough") is not None:
                r = r * (1 - band) + hm["rough"] * band
            if hm.get("weave"):
                kind, pitch, hgt = hm["weave"]
                height[m] += band * weave(kind, gu[m], gv[m], pitch, texel_m) * hgt
            # the hem's inner edge (turned seam allowance) shows as a soft ridge
            height[m] += 0.00025 * np.exp(-((ed[m] - hm["w"]) / 0.0012) ** 2) * hm.get("ridge", 1.0)
            for at, scol in hm.get("stitch", ()):
                st = stitch_line(ed[m], es[m], at)
                c = T.mix(c, T.hexrgb(scol), st * 0.85)
                height[m] -= st * 0.00012
        for at, scol in sp.get("stitch", ()):
            st = stitch_line(ed[m], es[m], at)
            c = T.mix(c, T.hexrgb(scol), st * 0.8)
            height[m] -= st * 0.00012
        roll = sp.get("roll", 0.0012)
        if roll:
            # rounded fold at the edge: falls away over the last `roll` metres
            height[m] -= 0.0006 * (1 - M.smoothstep(0.0, roll, ed[m])) ** 2
        if sp.get("edge_wear"):
            wear = (1 - M.smoothstep(0.0, 0.0025, ed[m])) * (0.6 + 0.4 * lf[m])
            c = c * (1 + sp["edge_wear"] * wear[:, None])
            r = r + 0.06 * wear
        col[m] = c
        rough[m] = r
        metal[m] = sp.get("metal", 0.0)
    for fn in spec.get("_seams", []):
        pids, dist, along, sp2 = fn(rs, ctx)
        m = np.isin(part, pids)
        groove = np.exp(-(dist / 0.0011) ** 2) * m
        height -= groove * 0.0005
        col *= (1 - 0.18 * groove)[:, None]
        for at, scol in sp2.get("stitch", ()):
            st = (stitch_line(np.abs(dist), along, at)) * m
            col = T.mix(col, T.hexrgb(scol), st * 0.8)
            height -= st * 0.0001
    for fn in spec.get("_height", []):
        height += fn(rs, part, ctx)
    for fn in spec.get("_extra", []):
        col, dn, rough, metal = fn(rs, part, col, dn, rough, metal, ctx)
    nh = rs.height_normals(height, texel_m)
    N = T.blend_ts(nh, dn * 0.5 + 0.5, 1.0)
    sh = np.clip(ao, 0, 1)
    col = col * (0.72 + 0.28 * sh[:, None])
    col, rough = zone_aa(rs, part, col, rough)
    D = np.clip(col, 0, 1)
    ORM = np.stack([np.clip(sh * 0.85 + 0.15, 0, 1), np.clip(rough, 0.05, 1), np.clip(metal, 0, 1)], 1)
    return D, N, ORM


def zone_aa(rs, part, col, rough):
    """One-texel anti-aliasing of colour/roughness where the zone id changes between neighbours
    (zone borders are hard per-texel decisions)."""
    res = rs.res
    pid = np.full(res * res, -1, np.int64)
    pid[rs.pix] = part
    pid = pid.reshape(res, res)
    edge = np.zeros((res, res), bool)
    for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        nb = np.roll(np.roll(pid, dy, 0), dx, 1)
        edge |= (nb != pid) & (nb >= 0) & (pid >= 0)
    e = edge.reshape(-1)[rs.pix]
    if not e.any():
        return col, rough
    for arr in (col, rough):
        ch = arr.shape[1] if arr.ndim == 2 else 1
        img, cov = rs.to_image(arr, ch)
        acc = np.zeros_like(img)
        cnt = np.zeros(cov.shape, np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                acc += np.roll(np.roll(img * cov[..., None], dy, 0), dx, 1)
                cnt += np.roll(np.roll(cov, dy, 0), dx, 1)
        blur = (acc / np.maximum(cnt, 1)[..., None]).reshape(-1, ch)[rs.pix]
        if arr.ndim == 2:
            arr[e] = blur[e]
        else:
            arr[e] = blur[e, 0]
    return col, rough
