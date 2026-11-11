"""Script-generated hair: a hair cap grown from the body's scalp region, three-strand braids
(woven tube geometry), bangs and face-framing strands as tapered clumps, ties, plus the MakeHuman
eyebrow/eyelash cards remapped into the hair atlas.

Hair atlas (one 1024 texture per fighter):
  CAP    u 0.00-0.50  hair cap, strands run along v
  BRAID  u 0.50-0.75  braid strand tubes (shared, phase-aligned so lobe shading is consistent)
  STRAND u 0.75-0.9375 v 0-0.75  bangs, face strands, tassels, wisps
  TIE    u 0.9375-1   v 0-0.75   hair ties
  BROW   u 0.75-1     v 0.75-0.875
  LASH   u 0.75-1     v 0.875-1"""
import math

import numpy as np

import eh_body as Bd
import eh_garment as G
import eh_mesh as M

CAP = (0.0, 0.0, 0.5, 1.0)
BRAID = (0.5, 0.0, 0.75, 1.0)
STRAND = (0.75, 0.0, 0.9375, 0.75)
TIE = (0.9375, 0.0, 1.0, 0.75)
BROW = (0.75, 0.75, 1.0, 0.875)
LASH = (0.75, 0.875, 1.0, 1.0)
CARD = None

P_CAP, P_BRAID, P_STRAND, P_TIE, P_BROW, P_LASH, P_BANG, P_CARD = 1, 2, 3, 4, 5, 6, 7, 8

# Atlas layouts. "cards" (Ashka): CAP u 0-0.4, BRAID 0.4-0.6, CARD 0.6-0.9375 (v 0-0.75): alpha strand
# cards for bangs, face-framing strands, braid flyaways and the nape gather (also used by tubes).
LAYOUTS = {
    "default": {"CAP": (0.0, 0.0, 0.5, 1.0), "BRAID": (0.5, 0.0, 0.75, 1.0), "STRAND": (0.75, 0.0, 0.9375, 0.75),
                "CARD": None},
    "cards": {"CAP": (0.0, 0.0, 0.4, 1.0), "BRAID": (0.4, 0.0, 0.6, 1.0), "STRAND": (0.6, 0.0, 0.9375, 0.75),
              "CARD": (0.6, 0.0, 0.9375, 0.75)},
}


def set_layout(name):
    globals().update(LAYOUTS[name])


def rect_map(uv, rect):
    x0, y0, x1, y1 = rect
    return np.stack([x0 + uv[:, 0] * (x1 - x0), y0 + uv[:, 1] * (y1 - y0)], 1)


def head_info(body, rig, parts):
    V = M.co(body)
    ears = Bd.region(body, "ears") > 0.3
    eyes = Bd.eye_centers(parts["eyes"])
    brows = M.co(parts["brows"])
    hb = rig.data.bones["head"]
    info = {
        "ear_l": V[ears & (V[:, 0] > 0)].mean(0),
        "ear_r": V[ears & (V[:, 0] < 0)].mean(0),
        "eye_l": eyes["l"]["center"], "eye_r": eyes["r"]["center"],
        "brow_z": float(brows[:, 2].mean()),
        "brow_top": float(brows[:, 2].max()),
        "head_top": float(V[:, 2].max()),
        "neck": np.array(rig.data.bones["neck_01"].head_local),
        "head": np.array(hb.head_local),
    }
    info["center"] = np.array([0.0, (info["ear_l"][1] + info["ear_r"][1]) / 2 + 0.005,
                               (info["brow_z"] + info["ear_l"][2]) / 2 + 0.01])
    return info


# ----------------------------------------------------------------------------- cap

def cap(body, rig, hi, collider, style, thick=0.009, grow=2):
    V = M.co(body)
    adj = M.adjacency(body)
    scalp = Bd.region(body, "scalp") > 0.5
    ears = M.grow_vmask(adj, Bd.region(body, "ears") > 0.05, 2)
    grown = M.grow_vmask(adj, scalp, grow + (1 if style != "part" else 0))
    # do not grow down the forehead: only behind the temples or above the brow line + 4.5 cm
    ok = (V[:, 1] > hi["eye_l"][1] + 0.035) | (V[:, 2] > hi["brow_top"] + (0.036 if style == "part" else 0.026))
    vm = (scalp | (grown & ok)) & ~ears
    if style == "part":
        # temples/sideburns: allow a little more in front of the ears
        side = M.grow_vmask(adj, vm, 1) & (V[:, 2] > hi["ear_l"][2] - 0.01) & ~ears & ok
        vm |= side
    inside_d = M.ring_distance(adj, ~vm, 12)
    t = thick * M.smoothstep(0.0, 4.5, inside_d) + 0.0007
    if style == "part":
        top = M.smoothstep(hi["brow_top"] + 0.05, hi["head_top"] - 0.01, V[:, 2])
        t *= 1 - 0.45 * np.exp(-(V[:, 0] / 0.007) ** 2) * top * (V[:, 1] < hi["center"][1] + 0.04)
        for e in ("ear_l", "ear_r"):
            a = hi[e] + np.array([0, 0.035, -0.03])
            t += 0.006 * np.exp(-((V - a) ** 2).sum(1) / 0.035 ** 2)
    else:
        nape = np.array([0, hi["center"][1] + 0.08, hi["ear_l"][2] - 0.035])
        t += 0.008 * np.exp(-((V - nape) ** 2).sum(1) / 0.04 ** 2)
        crown = np.array([0, hi["center"][1] + 0.03, hi["head_top"] - 0.02])
        t += 0.004 * np.exp(-((V - crown) ** 2).sum(1) / 0.06 ** 2)
    g, src, fm = G.shell(body, vm, "hair_cap", t, collider, relax_iters=10, relax_factor=0.45,
                         smooth_offset=4, lip=0.0, min_frac=0.6, edge_smooth=24, edge_clamp=0.016)
    _cap_uv(g, hi, style)
    G.set_part_attr(g, "part", P_CAP)
    G.set_float_attr(g, "edge_d", M.geodesic_from(g, M.boundary_vmask(g), max_dist=0.05))
    return g


def _cap_uv(g, hi, style):
    V = M.co(g)
    ls, lt, lv = M.polys(g)
    C = hi["center"]
    fc = M.poly_centers(g)
    fidx = np.repeat(np.arange(len(ls)), lt)
    P = V[lv] - C
    n = np.linalg.norm(P, axis=1)
    if style == "part":
        s = np.where(fc[fidx, 0] >= 0, 1.0, -1.0)
        a = np.stack([s, 0 * s, 0 * s], 1)
        e1 = np.array([0, 0, 1.0])
        e2 = np.cross(a, e1)
        theta = np.arccos(np.clip((P * a).sum(1) / n, -1, 1))
        phi = np.arctan2((P * e2).sum(1), P @ e1)
        v = np.clip((math.pi / 2 - theta) / 1.25, 0, 1)        # 0 at the part, down to the side
        u = np.clip((phi + math.pi * 0.95) / (2 * math.pi * 0.95), 0, 1)
        u = np.where(s > 0, u * 0.5, 0.5 + u * 0.5)
    else:
        a = np.array([0, -0.55, 0.83])
        a /= np.linalg.norm(a)
        e1 = -np.cross([1.0, 0, 0], a)
        e2 = np.cross(a, e1)
        theta = np.arccos(np.clip(P @ a / n, -1, 1))
        phi = np.arctan2(P @ e2, P @ e1)
        v = np.clip(theta / math.pi * 1.25, 0, 1)
        u = np.clip((phi + math.pi) / (2 * math.pi), 0, 1)
    uv = rect_map(np.stack([u, v], 1), CAP)
    M.set_loop_uvs(g, uv)


# ----------------------------------------------------------------------------- braids

def braid(ctrl, collider, depth_hint, width=(0.034, 0.022), period=0.055, tassel=0.05,
          amp_lat=0.30, amp_depth=0.17, r_lat=0.34, r_depth=0.27, sides=8, seg_per_period=18,
          clear=0.006, loose=0.0, seed=0):
    """Three interwoven strand tubes along control points. Returns geometry parts, the centre path,
    its length, per-vertex arc parameters and a description used by the painter."""
    L0 = float(np.sum(np.linalg.norm(np.diff(np.asarray(ctrl), axis=0), axis=1)))
    n = max(int(L0 / period * seg_per_period), 24)
    path, L = M.catmull_rom(ctrl, n)
    # keep the braid off the body/garments
    wmax = width[0]
    for _ in range(3):
        path, _ = collider.push_out(path, wmax * (amp_depth + r_depth) + clear)
        path = np.vstack([path[:1], M.smooth(path, _chain_adj(len(path)), 1, 0.5)[1:-1], path[-1:]])
    path, L = M.catmull_rom(path[::max(1, len(path) // 40)].tolist() + [path[-1].tolist()], n)
    s = np.linspace(0, L, n)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    hint = depth_hint(path) if callable(depth_hint) else np.broadcast_to(np.asarray(depth_hint, float), path.shape)
    D = hint - T * (hint * T).sum(1, keepdims=True)
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    Lv = np.cross(T, D)
    w = width[0] + (width[1] - width[0]) * M.smoothstep(0.0, L, s)
    gather = M.smoothstep(0.0, 0.025, s)
    # tassel continues the centre line beyond L
    nt = max(int(tassel / period * seg_per_period * 0.8), 6)
    st = np.linspace(L, L + tassel, nt + 1)[1:]
    pt = path[-1] + np.outer(st - L, T[-1])
    parts, arcs, strands = [], [], []
    tie_i = len(s)
    s_all = np.r_[s, st]
    P_all_c = np.vstack([path, pt])
    T_all = np.vstack([T, np.repeat(T[-1:], nt, 0)])
    D_all = np.vstack([D, np.repeat(D[-1:], nt, 0)])
    L_all = np.vstack([Lv, np.repeat(Lv[-1:], nt, 0)])
    w_all = np.r_[w, np.full(nt, width[1])]
    rng = np.random.default_rng(seed)
    n_per = (L + period) / period
    for k in range(3):
        ph = 2 * math.pi * k / 3
        th = 2 * math.pi * s_all / period + ph
        th_t = np.where(s_all > L, 2 * math.pi * L / period + ph, th)
        ga = np.r_[gather, np.ones(nt)]
        lat = amp_lat * w_all * np.sin(th_t) * ga
        dep = amp_depth * w_all * np.sin(2 * th_t) * ga
        splay = np.where(s_all > L, (s_all - L) / tassel, 0.0)
        lat = lat * (1 + 0.6 * splay)
        if loose:
            lat = lat + loose * w_all * np.sin(s_all * 23.0 + rng.random() * 6) * 0.15
            dep = dep + loose * w_all * np.sin(s_all * 17.0 + rng.random() * 6) * 0.12
        Pk = P_all_c + L_all * lat[:, None] + D_all * dep[:, None]
        tk = np.gradient(Pk, axis=0)
        tk /= np.linalg.norm(tk, axis=1, keepdims=True)
        b = D_all - tk * (D_all * tk).sum(1, keepdims=True)
        b /= np.linalg.norm(b, axis=1, keepdims=True)
        a = np.cross(tk, b)
        taper = 1 - 0.85 * M.smoothstep(L + tassel * 0.15, L + tassel, s_all)
        tie_pinch = 1 - 0.35 * np.exp(-((s_all - L) / 0.008) ** 2)
        root = 0.55 + 0.45 * M.smoothstep(0.0, 0.02, s_all)
        ra = r_lat * w_all * taper * tie_pinch * root
        rb = r_depth * w_all * taper * tie_pinch * root
        # v phase-aligned across strands: depth phase depends on v only
        v0 = (ph / (2 * math.pi)) * period
        vr = ((s_all + v0) / (L + tassel + period),)
        verts, faces, uvs = M.tube(Pk, ra, rb, sides, a, b, cap_start=False, cap_end=True,
                                   u_range=(0, 1), v_range=(0, 1))
        # replace v by the phase-aligned arc parameter per ring
        vv = (s_all + v0) / (L + tassel + period)
        uvs = _retarget_tube_v(uvs, vv, sides, len(Pk))
        uvs = [[tuple(rect_map(np.array([uv]), BRAID)[0]) for uv in f] for f in uvs]
        parts.append((verts, faces, uvs))
        arcs.append(np.r_[np.repeat(s_all, sides), s_all[-1]])
        strands.append(Pk)
    # tie
    tv, tf, tuv = M.tube(np.array([P_all_c[tie_i - 3], P_all_c[min(tie_i + 2, len(P_all_c) - 1)]]),
                         np.full(2, width[1] * 0.62), np.full(2, width[1] * 0.5), 10,
                         np.repeat(L_all[tie_i - 1:tie_i], 2, 0), np.repeat(D_all[tie_i - 1:tie_i], 2, 0),
                         cap_start=False, cap_end=False)
    tuv = [[tuple(rect_map(np.array([uv]), TIE)[0]) for uv in f] for f in tuv]
    parts.append((tv, tf, tuv))
    arcs.append(np.full(len(tv), L))
    desc = {"length": L, "period": period, "periods_in_v": (L + tassel + period) / period,
            "tassel": tassel, "path": P_all_c}
    return parts, arcs, desc


def _retarget_tube_v(uvs, vv, sides, n):
    out = []
    i = 0
    for ring in range(n - 1):
        for j in range(sides):
            f = uvs[i]
            out.append([(f[0][0], vv[ring]), (f[1][0], vv[ring]), (f[2][0], vv[ring + 1]), (f[3][0], vv[ring + 1])])
            i += 1
    for f in uvs[i:]:
        out.append([(uv[0], vv[-1]) for uv in f])
    return out


def _chain_adj(n):
    idx = np.arange(n)
    a = np.r_[idx[:-1], idx[1:]]
    b = np.r_[idx[1:], idx[:-1]]
    order = np.argsort(a, kind="stable")
    a, b = a[order], b[order]
    indptr = np.zeros(n + 1, np.int64)
    np.add.at(indptr, a + 1, 1)
    return np.cumsum(indptr), b


# ----------------------------------------------------------------------------- clumps

def clump(ctrl, width, thick, collider, clear, sides=6, segs=12, normal_hint=None, tip=0.12):
    """A tapered, flattened hair clump along control points (bangs, face strands, wisps)."""
    path, L = M.catmull_rom(ctrl, segs)
    if collider is not None:
        for _ in range(2):
            p2, _ = collider.push_out(path, clear + thick)
            path = np.vstack([path[:1], p2[1:]])
    s = np.linspace(0, 1, segs)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    if normal_hint is None:
        normal_hint = np.array([0, -1.0, 0])
    hint = np.broadcast_to(np.asarray(normal_hint, float), path.shape)
    D = hint - T * (hint * T).sum(1, keepdims=True)
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    A = np.cross(T, D)
    taper = 1 - (1 - tip) * M.smoothstep(0.25, 1.0, s)
    wa = width * taper * (0.75 + 0.25 * M.smoothstep(0, 0.2, s))
    wb = thick * taper
    verts, faces, uvs = M.tube(path, wa * 0.5, wb * 0.5, sides, A, D, cap_start=False, cap_end=True)
    uvs = [[tuple(rect_map(np.array([uv]), STRAND)[0]) for uv in f] for f in uvs]
    arc = np.r_[np.repeat(s * L, sides), L]
    return (verts, faces, uvs), arc, path, L


# ----------------------------------------------------------------------------- cards

def card(path, width, normal_hint, n_across=3, cup=0.0015, window=(0.0, 1.0), tip=0.35, flip=1.0):
    """Hair card: a ribbon along `path` (root first) facing `normal_hint`, slightly cupped, tapering to
    `tip` of its width; UVs map across the card to `window` of the CARD texture (strand clumps with
    alpha) and from root (v 0) to tip (v 1)."""
    n = len(path)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    hint = np.broadcast_to(np.asarray(normal_hint, float), path.shape)
    D = hint - T * (hint * T).sum(1, keepdims=True)
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    Ac = np.cross(T, D) * flip
    sv = np.linspace(0, 1, n)
    wv = width * (1 - (1 - tip) * M.smoothstep(0.35, 1.0, sv)) * (0.8 + 0.2 * M.smoothstep(0.0, 0.15, sv))
    verts, faces, uvs = [], [], []
    for i in range(n):
        for k in range(n_across):
            c = -1 + 2 * k / (n_across - 1)
            verts.append(path[i] + Ac[i] * c * wv[i] * 0.5 + D[i] * cup * (1 - c * c))
    for i in range(n - 1):
        for k in range(n_across - 1):
            a, b = i * n_across + k, i * n_across + k + 1
            faces.append((a, b, b + n_across, a + n_across))
            u0 = window[0] + (window[1] - window[0]) * k / (n_across - 1)
            u1 = window[0] + (window[1] - window[0]) * (k + 1) / (n_across - 1)
            uvs.append([tuple(rect_map(np.array([[u0, sv[i]]]), CARD)[0]),
                        tuple(rect_map(np.array([[u1, sv[i]]]), CARD)[0]),
                        tuple(rect_map(np.array([[u1, sv[i + 1]]]), CARD)[0]),
                        tuple(rect_map(np.array([[u0, sv[i + 1]]]), CARD)[0])])
    return np.array(verts), faces, uvs


# ----------------------------------------------------------------------------- brows / lashes

def remap_card(ob, rect, part):
    uv = M.loop_uvs(ob)
    M.set_loop_uvs(ob, rect_map(np.clip(uv, 0, 1), rect))
    G.set_part_attr(ob, "part", part)
    ob.data.materials.clear()


def surface_point(collider, p, direction, back=0.3):
    """First hit of a ray cast from p - direction*back towards direction (None if missed)."""
    d = np.asarray(direction, float)
    d /= np.linalg.norm(d)
    r = collider.ray(p - d * back, d, back * 2)
    return None if r[0] is None else np.array(r[0])
