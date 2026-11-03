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
WRAP = 7
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
    z_bottom = apex[2] - 0.115
    z_armpit = rig.data.bones["upperarm_l"].head_local[2] - 0.095
    x_out = np.where(Z < z_armpit, 1.0, 0.17 - 0.04 * M.smoothstep(z_armpit, z_armpit + 0.085, Z))
    neck_f = zc - 0.04 + 30.0 * np.maximum(ax - 0.025, 0) ** 2
    neck_b = zc - 0.03 + 26.0 * np.maximum(ax - 0.02, 0) ** 2
    armw = G.wsum(W, G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "hand"], "l")
                  + G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "hand"], "r"))
    vm = ((Z >= z_bottom - 0.025) & (Z <= np.where(front, neck_f, neck_b)) & (ax <= x_out) & (armw < 0.3)
          & (Z < zc + 0.07))
    top, src, fm = G.shell(body, vm, "top", 0.0045, collider, relax_iters=30, relax_factor=0.5,
                           lip=0.003, cuts=[((0, 0, z_bottom), (0, 0, 1.0))])
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
                              smooth_offset=6, lip=0.004,
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
    for s in "lr":
        tc, rc, _ = G.limb_param(rig, "calf_" + s, V)
        tf, rf, _ = G.limb_param(rig, "foot_" + s, V)
        side = (X > 0) if s == "l" else (X < 0)
        legw = G.wsum(W, G.side_names(["calf", "foot", "ball"], s))
        ankle = np.array(rig.data.bones["foot_" + s].head_local)
        heel = (Y > ankle[1] + 0.012) & (Z < ankle[2] - 0.015)
        vm = side & (legw > 0.4) & (((tc > 0.88) & (tc <= 1.0)) | ((tf > -0.25) & (tf < 0.36))) \
            & ~heel & (Z > 0.006)
        w, src, fm = G.shell(body, vm, "wrap_" + s, 0.0028, collider, relax_iters=4, lip=0.0025)
        part = np.full(len(src), WRAP)
        _tag_lip(w, part)
        wraps.append(w)
        hide |= G.hidden_face_mask(body, fm, garment=w, margin_m=0.008)
    out["wraps"] = M.join(wraps, "wraps")
    return out, hide


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


def zones(part, a, rs):
    """Painter-side zone classification (see eh_specs)."""
    p = part.copy()
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
