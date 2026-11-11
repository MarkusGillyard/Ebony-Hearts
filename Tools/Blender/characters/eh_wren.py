"""Wren Ku's primary outfit (canon: black-and-ocean-blue MMA fight gear): a sports top that leaves
the abdominal muscles visible, fight shorts with side slits, open-finger 4 oz MMA gloves with blue
wrist straps, and ankle wraps over bare feet. Every piece is a shell grown from the body, so it
carries the body's skin weights; part tags drive the painter."""
import numpy as np

import eh_garment as G
import eh_mesh as M

# part tags (vertex attribute "part") used by the painter
TOP_MAIN, TOP_BAND, TOP_TRIM = 1, 2, 3
SHORTS_MAIN, SHORTS_BAND, SHORTS_PANEL = 4, 5, 6
WRAP, WRAP_BAND, WRAP_ACCENT = 7, 8, 9
GLOVE_PALM, GLOVE_PAD, GLOVE_STRAP, GLOVE_CUFF, GLOVE_LOOP = 11, 12, 13, 14, 15


def bust_apex(body, rig, W):
    V = M.co(body)
    armw = G.wsum(W, G.side_names(G.ARM[1:], "l") + G.side_names(G.ARM[1:], "r"))
    zc = rig.data.bones["clavicle_l"].head_local[2]
    sel = ((np.abs(V[:, 0]) > 0.03) & (np.abs(V[:, 0]) < 0.13) & (V[:, 2] > zc - 0.3) & (V[:, 2] < zc - 0.04)
           & (armw < 0.2))
    i = np.nonzero(sel)[0][np.argmin(V[sel, 1])]
    return V[i]


def build(body, rig, cfg, collider):
    V = M.co(body)
    W = M.weights(body)
    X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
    ax = np.abs(X)
    zc = rig.data.bones["clavicle_l"].head_local[2]
    front = Y < G.spine_y(rig, Z)
    apex = bust_apex(body, rig, W)
    out = {}
    hide = np.zeros(len(body.data.polygons), bool)

    # ------------------------------------------------------------------ sports top
    # scoop neck front and back, armholes cut by an ellipsoid round each shoulder joint (wide straps
    # over the trapezius), straight hem under the bust band
    z_bottom = apex[2] - 0.115
    armw = G.wsum(W, G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "hand"], "l")
                  + G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "hand"], "r"))
    headw = W.get("head", np.zeros(len(V))) + W.get("neck_01", np.zeros(len(V)))
    vm = (Z >= z_bottom - 0.03) & (Z < zc + 0.1) & (armw < 0.6) & (headw < 0.5) & (ax < 0.22)
    sh = {s_: np.array(rig.data.bones["upperarm_" + s_].head_local) for s_ in "lr"}
    o_top = cfg["outfit"]

    def neckline(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        k = M.smoothstep(-0.03, 0.03, y - G.spine_y(rig, z))
        zf = zc - o_top["neck_front_drop"] + o_top["neck_front_curve"] * x ** 2
        zb = zc - o_top["neck_back_drop"] + o_top["neck_back_curve"] * x ** 2
        return zf * (1 - k) + zb * k - z

    def armholes(P):
        out_ = np.full(len(P), 1e3)
        for s_, sg in (("l", 1.0), ("r", -1.0)):
            c = sh[s_] + np.array([sg * o_top["armhole_dx"], 0.0, o_top["armhole_dz"]])
            r = o_top["armhole_r"]
            e = ((P[:, 0] - c[0]) / r[0]) ** 2 + ((P[:, 1] - c[1]) / r[1]) ** 2 + ((P[:, 2] - c[2]) / r[2]) ** 2
            out_ = np.minimum(out_, (np.sqrt(e) - 1.0) * r[0])
        return out_

    top, src, fm = G.shell(body, vm, "top", 0.0045, collider, relax_iters=30, relax_factor=0.5,
                           lip=0.0045, subdiv=1, edge_smooth=0, implicit=(neckline, armholes),
                           cuts=[((0, 0, z_bottom), (0, 0, 1.0))])
    G.keep_largest(top)
    # compression knit bridges the bust apex (no nipple detail through the fabric)
    Pt = M.co(top)
    wsm = sum(np.exp(-((Pt - apex * np.array([sx, 1, 1])) ** 2).sum(1) / 0.035 ** 2) for sx in (1.0, -1.0))
    sm = M.smooth(Pt, M.adjacency(top), 14, 0.5)
    Pt = Pt + (sm - Pt) * np.clip(wsm, 0, 1)[:, None]
    Pt, _ = collider.push_out(Pt, 0.0035)
    M.set_co(top, Pt)
    Pt = M.co(top)
    G.set_part_attr(top, "part", np.full(len(Pt), TOP_MAIN, np.int32))
    G.set_float_attr(top, "zone_band", (z_bottom + 0.045) - Pt[:, 2])
    hide |= G.hidden_face_mask(body, fm, garment=top)
    out["top"] = top

    # ------------------------------------------------------------------ fight shorts
    zp = rig.data.bones["pelvis"].head_local[2]
    z_waist = np.where(front, zp + 0.055, zp + 0.075)
    legs = np.zeros(len(V), bool)
    tt_all = np.zeros(len(V))
    lat_all = np.zeros(len(V))
    for s, sg in (("l", 1.0), ("r", -1.0)):
        tt, r, foot = G.limb_param(rig, "thigh_" + s, V)
        lw = G.wsum(W, G.side_names(G.LEG, s))
        on = lw > 0.5
        lat = (X - foot[:, 0]) * sg / np.maximum(r, 1e-6)
        legs |= on
        tt_all = np.where(on, tt, tt_all)
        lat_all = np.where(on, lat, lat_all)
    t_hem = cfg["outfit"]["shorts_hem"]
    hip = np.array(rig.data.bones["thigh_l"].head_local)
    knee = np.array(rig.data.bones["thigh_l"].tail_local)
    z_hem = float(hip[2] + (knee[2] - hip[2]) * t_hem)
    vm = (Z <= z_waist + 0.025) & (~legs | (tt_all <= t_hem + 0.08)) & (Z > rig.data.bones["calf_l"].head_local[2])
    off = 0.005 + 0.02 * M.smoothstep(0.05, t_hem, np.where(legs, tt_all, 0.0))
    yf = float(Y[front & (np.abs(X) < 0.02) & (np.abs(Z - zp) < 0.05)].min()) if (front & (np.abs(X) < 0.02)).any() else -0.1
    waist_n = np.array([0.0, 0.1, -1.0]) / np.linalg.norm([0.0, 0.1, -1.0])
    shorts, src, fm = G.shell(body, vm, "shorts", off, collider, relax_iters=20, relax_factor=0.5,
                              smooth_offset=6, lip=0.0065, soft=3, edge_smooth=4,
                              cuts=[((0, yf, zp + 0.055), tuple(waist_n)), ((0, 0, z_hem), (0, 0, 1.0))])
    Ps = M.co(shorts)
    G.set_part_attr(shorts, "part", np.full(len(Ps), SHORTS_MAIN, np.int32))
    fr = Ps[:, 1] < G.spine_y(rig, Ps[:, 2])
    zw_s = np.where(fr, zp + 0.055, zp + 0.075) + 0.1 * (Ps[:, 1] - yf) * fr
    G.set_float_attr(shorts, "zone_band", Ps[:, 2] - (zw_s - 0.045))
    latp = np.full(len(Ps), -1.0)
    for s_, sg_ in (("l", 1.0), ("r", -1.0)):
        tt, r, foot = G.limb_param(rig, "thigh_" + s_, Ps)
        mine = (Ps[:, 0] * sg_ > 0.03) & (tt > 0.05)
        latp = np.where(mine, (Ps[:, 0] - foot[:, 0]) * sg_ / np.maximum(r, 1e-6) - 0.55, latp)
    G.set_float_attr(shorts, "zone_panel", latp)
    hide |= G.hidden_face_mask(body, fm, garment=shorts)
    out["shorts"] = shorts

    # ------------------------------------------------------------------ gloves
    gloves = []
    for s in "lr":
        g, fm = _glove(body, rig, W, V, s, collider)
        gloves.append(g)
        hide |= G.hidden_face_mask(body, fm, garment=g, margin_m=0.008)
    out["gloves"] = M.join(gloves, "gloves")

    # ------------------------------------------------------------------ ankle wraps
    wraps = []
    for s_ in "lr":
        pieces, fm = _ankle_wrap(body, rig, W, V, s_, collider)
        wraps += pieces
        hide |= G.hidden_face_mask(body, fm, garment=pieces[0], margin_m=0.007)
    out["wraps"] = M.join(wraps, "wraps")
    out["_info"] = {"top_band_z": float(z_bottom + 0.045), "z_pelvis": float(zp), "y_front": float(yf),
                    "shorts_band_h": 0.05}
    return out, hide


# Wrap bands in the foot frame: (name, three points (forward, outward, z above the floor) the band's
# centre plane passes through, width m). Order = wrapping order (later bands lie on top).
WRAP_BANDS = (
    ("arch", ((0.068, 0.0, 0.075), (0.086, 0.03, 0.0), (0.086, -0.03, 0.0)), 0.034),
    ("fig8_in", ((0.07, -0.03, 0.0), (0.032, 0.0, 0.085), (-0.035, 0.035, 0.112)), 0.03),
    ("fig8_out", ((0.07, 0.03, 0.0), (0.032, 0.0, 0.085), (-0.035, -0.035, 0.112)), 0.03),
    ("ankle", ((0.0, 0.05, 0.095), (0.0, -0.05, 0.095), (-0.05, 0.0, 0.1)), 0.03),
    ("anchor", ((0.0, 0.05, 0.124), (0.0, -0.05, 0.124), (-0.05, 0.0, 0.128)), 0.026),
)
WRAP_UNDER, WRAP_LAYER = 0.0016, 0.0009


def _foot_frame(rig, s):
    ank = np.array(rig.data.bones["foot_" + s].head_local)
    ball = np.array(rig.data.bones["ball_" + s].head_local)
    fwd = ball - ank
    fwd[2] = 0
    fwd /= np.linalg.norm(fwd)
    outw = np.array([1.0, 0, 0]) if s == "l" else np.array([-1.0, 0, 0])
    outw = outw - fwd * (outw @ fwd)
    outw /= np.linalg.norm(outw)
    return ank, fwd, outw


def _ankle_wrap(body, rig, W, V, s, collider):
    """Ankle support over the bare foot: a thin under-wrap from the lower shin to the midfoot (heel
    and forefoot left free) with five overlapping wrap bands on top (arch loop, figure-eight across
    the instep, two anchor rounds; the top anchor is the ocean-blue accent). Every edge is an analytic
    cut, every band steps over the bands under it and has a turned edge for thickness."""
    ank, fwd, outw = _foot_frame(rig, s)
    up = np.array([0, 0, 1.0])

    def fp(f, o, z):
        return np.array([ank[0], ank[1], 0.0]) + fwd * f + outw * o + up * z

    side = (V[:, 0] > 0) if s == "l" else (V[:, 0] < 0)
    legw = G.wsum(W, G.side_names(["calf", "foot", "ball"], s))
    vm = side & (legw > 0.3) & (V[:, 2] < ank[2] + 0.085)
    g, _ = M.extract(body, M.face_mask_from_verts(body, vm, "any"), "wrap_" + s)
    G.drop_small_islands(g)

    def rel(P):
        d = P - np.array([ank[0], ank[1], 0.0])
        return d @ fwd, d @ outw, P[:, 2]

    def top(P):
        f, o, z = rel(P)
        return ank[2] + 0.062 - 0.08 * f - z

    def front(P):
        a, b = fp(0.074, 0.0, 0.07), fp(0.096, 0.0, 0.0)
        n = np.cross(b - a, outw)
        n /= np.linalg.norm(n)
        if n @ fwd > 0:
            n = -n
        return (P - a) @ n

    def heel(P):
        f, o, z = rel(P)
        return ((f + 0.046) / 0.052) ** 2 + (o / 0.05) ** 2 + ((z - 0.022) / 0.05) ** 2 - 1.0

    for fn in (top, front, heel):
        M.cut_implicit(g, fn)
    G.drop_small_islands(g, 40)
    base = M.co(g).copy()
    Nn = M.vnormals(g)
    fm_used = M.face_mask_from_verts(body, vm & (V[:, 2] < ank[2] + 0.07), "all")

    def slab(name, pts, wdt):
        a, b, c = (fp(*p) for p in pts)
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n)
        cen = (a + b + c) / 3
        return lambda P, w=wdt: w / 2 - np.abs((P - cen) @ n)

    slabs = [(nm, slab(nm, pts, w)) for nm, pts, w in WRAP_BANDS]
    pieces = []
    under = g
    P = base + Nn * WRAP_UNDER
    P[:, 2] = np.maximum(P[:, 2], 0.0006)
    M.set_co(under, P)
    G.set_part_attr(under, "part", WRAP)
    for k, (nm, fn) in enumerate(slabs):
        b = M.duplicate(g, "wrapband_%s_%s" % (nm, s))
        M.set_co(b, base)
        M.cut_implicit(b, fn)
        G.drop_small_islands(b, 12)
        if not len(b.data.vertices):
            continue
        Pb = M.co(b)
        Nb = M.vnormals(b)
        below = np.zeros(len(Pb)) + sum(np.clip(f2(Pb) / 0.004 + 0.5, 0, 1) for _, f2 in slabs[:k])
        off = WRAP_UNDER + WRAP_LAYER * (1.0 + below)
        Pb = Pb + Nb * off[:, None]
        Pb[:, 2] = np.maximum(Pb[:, 2], 0.0008)
        M.set_co(b, Pb)
        M.add_boundary_lip(b, WRAP_LAYER)
        G.set_part_attr(b, "part", WRAP_ACCENT if nm == "anchor" else WRAP_BAND)
        pieces.append(b)
    M.add_boundary_lip(under, 0.0012)
    G.set_part_attr(under, "part", WRAP)
    for ob in [under] + pieces:
        M.transfer_weights_surface(body, ob)
        for a in list(ob.data.attributes):
            if a.name.startswith("reg_") or a.name == "src_vi":
                ob.data.attributes.remove(a)
        ob.data.materials.clear()
    return [under] + pieces, fm_used


def _tag_lip(ob, part_src):
    """Tags shell vertices; lip vertices added after the shell inherit from their source via
    nearest-original lookup (lip verts were appended at the end)."""
    n = len(ob.data.vertices)
    tags = np.zeros(n, np.int32)
    k = len(part_src)
    tags[:k] = part_src
    if n > k:
        V = M.co(ob)
        base = V[:k]
        for i in range(k, n):
            tags[i] = part_src[np.argmin(((base - V[i]) ** 2).sum(1))]
        lip = np.zeros(n, np.float32)
        lip[k:] = 1
        G.set_float_attr(ob, "lip", lip)
    G.set_part_attr(ob, "part", tags)


def _zone(ob, name, values_src):
    """Continuous per-vertex field (thresholded per texel by the painter); lip vertices take the
    value of their nearest original vertex."""
    n = len(ob.data.vertices)
    k = len(values_src)
    out = np.zeros(n, np.float32)
    out[:k] = values_src
    if n > k:
        Vv = M.co(ob)
        for i in range(k, n):
            out[i] = values_src[np.argmin(((Vv[:k] - Vv[i]) ** 2).sum(1))]
    G.set_float_attr(ob, name, out)


def zones3d(part, rs, ctx, attrs):
    """Painter-side zones from the rest-pose texel positions (clean analytic borders): the top's
    under-bust band, the shorts' waistband and blue side panels, then the glove zones."""
    p = part.copy()
    P, info, rig = rs.P, ctx["wren"], ctx["rig"]
    top = part == TOP_MAIN
    p[top & (P[:, 2] < info["top_band_z"])] = TOP_BAND
    sh = part == SHORTS_MAIN
    zp, yf = info["z_pelvis"], info["y_front"]
    kb = M.smoothstep(-0.04, 0.04, P[:, 1] - G.spine_y(rig, P[:, 2]))
    zw = (zp + 0.055 + 0.1 * np.minimum(P[:, 1] - yf, 0.2)) * (1 - kb) + (zp + 0.075) * kb
    for s_, sg in (("l", 1.0), ("r", -1.0)):
        tt, r, foot = G.limb_param(rig, "thigh_" + s_, P)
        rad = P - foot
        lat = rad[:, 0] * sg / np.maximum(np.hypot(rad[:, 0], rad[:, 1]), 1e-6)
        mine = (P[:, 0] * sg > 0.02)
        p[sh & mine & (lat > 0.74)] = SHORTS_PANEL
    p[sh & (P[:, 2] > zw - info["shorts_band_h"])] = SHORTS_BAND
    return zones(p, attrs, rs, legacy=False)


def zones(part, a, rs, legacy=True):
    """Painter-side zone classification (see eh_specs)."""
    p = part.copy()
    if legacy:
        top = part == TOP_MAIN
        p[top & (a["zone_band"] > 0)] = TOP_BAND
        sh = part == SHORTS_MAIN
        p[sh & (a["zone_panel"] > 0)] = SHORTS_PANEL
        p[sh & (a["zone_band"] > 0)] = SHORTS_BAND
    gl = part == GLOVE_PALM
    p[gl & (a["g_dorsal"] > 0.3) & (a["g_sk"] > -0.09)] = GLOVE_PAD
    p[gl & (a["g_sk"] > 0.004)] = GLOVE_LOOP
    p[gl & (a["g_tfa"] > 0.74) & (a["g_sk"] < -0.05)] = GLOVE_CUFF
    p[gl & (a["g_strap"] > 0.5)] = GLOVE_STRAP
    return p


def _glove(body, rig, W, V, s, collider):
    X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
    hand_names = G.side_names(G.HAND, s)
    handw = G.wsum(W, hand_names)
    distal = G.wsum(W, G.side_names(["index_02", "index_03", "middle_02", "middle_03", "ring_02",
                                     "ring_03", "pinky_02", "pinky_03", "thumb_02", "thumb_03"], s))
    fa_w = G.wsum(W, G.side_names(["lowerarm", "lowerarm_twist_01", "hand"], s))
    tfa, rfa, _ = G.limb_param(rig, "lowerarm_" + s, V)
    wrist = np.array(rig.data.bones["hand_" + s].head_local)
    kn = np.mean([rig.data.bones["%s_01_%s" % (f, s)].head_local for f in ("index", "middle", "ring", "pinky")], 0)
    axis = (kn - wrist) / np.linalg.norm(kn - wrist)
    across = np.array(rig.data.bones["index_01_" + s].head_local) - np.array(rig.data.bones["pinky_01_" + s].head_local)
    nrm = np.cross(axis, across)
    nrm /= np.linalg.norm(nrm)
    thumb_tip = np.array(rig.data.bones["thumb_03_" + s].tail_local)
    if (thumb_tip - wrist) @ nrm > 0:
        nrm = -nrm                      # nrm now points out of the back of the hand
    sk = (V - kn) @ axis                # metres along the hand from the knuckle line
    prox_ok = np.ones(len(V), bool)
    for f in ("index", "middle", "ring", "pinky"):
        b = "%s_01_%s" % (f, s)
        tt, _, _ = G.limb_param(rig, b, V)
        mine = W.get(b, np.zeros(len(V))) > 0.5
        prox_ok &= ~(mine & (tt > 0.5))
    tt1, _, _ = G.limb_param(rig, "thumb_01_" + s, V)
    thumb_mine = W.get("thumb_01_" + s, np.zeros(len(V))) > 0.5
    prox_ok &= ~(thumb_mine & (tt1 > 0.75))
    side = (X > 0) if s == "l" else (X < 0)
    vm = side & (((handw > 0.45) & (distal < 0.35) & prox_ok) | ((fa_w > 0.5) & (tfa > 0.74)))
    Nb = M.vnormals(body)
    dorsal = M.smoothstep(0.05, 0.45, Nb @ nrm)
    pad = 0.0125 * M.smoothstep(-0.085, -0.03, sk) * (1 - M.smoothstep(-0.004, 0.016, sk)) * dorsal
    strap = M.smoothstep(0.76, 0.8, tfa) * (1 - M.smoothstep(0.93, 0.97, tfa)) * (sk < -0.05)
    off = 0.0026 + pad + 0.0045 * strap + 0.0022 * (tfa > 0.7) * (sk < -0.05)
    g, src, fm = G.shell(body, vm, "glove_" + s, off, collider, relax_iters=6, relax_factor=0.4,
                         smooth_offset=4, lip=0.0025)
    part = np.full(len(src), GLOVE_PALM)
    _tag_lip(g, part)
    _zone(g, "g_dorsal", dorsal[src])
    _zone(g, "g_sk", sk[src])
    _zone(g, "g_tfa", tfa[src])
    _zone(g, "g_strap", strap[src])
    return g, fm
