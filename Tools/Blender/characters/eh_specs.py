"""Paint specifications (colours, CC0 detail surfaces, trims, stitching) for the garment materials,
plus the few garment details painted from 3D landmarks (glove quilting, coat buttons, loafer strap)."""
import numpy as np

import math

import eh_ashka as A
import eh_garment as G
import eh_mesh as M
import eh_tex as T
import eh_wren as Wr


def wren(cfg):
    """Distinct surfaces: matte compression knit (top), smoother woven shorts with blue side panels,
    ribbed elastic bands, neoprene-like under-wrap, crepe bandage wrap bands (blue anchor), leather
    gloves with a matte palm and webbing straps. Blacks are lifted to real black-cloth albedo."""
    p = cfg["palette"]
    blk, blk2, blue, blue_d = p["fab_black"], p["fab_black2"], p["blue"], p["blue_dark"]
    st_grey = p["stitch_grey"]
    knit = ("Fabric034", 0.22, 0.035, 0.35)
    woven = ("Fabric040", 0.16, 0.03, 0.45)
    crepe = ("Fabric001", 0.09, 0.07, 1.5)
    outfit = {
        Wr.TOP_MAIN: dict(color=blk, rough=0.84, detail=knit, weave=("jersey", 0.0016, 0.00008), mottle=0.03,
                          hem=dict(w=0.009, color=blk2, rough=0.84, stitch=[(0.003, st_grey), (0.0065, st_grey)])),
        Wr.TOP_BAND: dict(color=blue, rough=0.72, detail=knit, weave=("rib", 0.0022, 0.00016),
                          hem=dict(w=0.004, color=blue_d, stitch=[(0.0025, blue_d)])),
        Wr.SHORTS_MAIN: dict(color=blk, rough=0.72, rough_var=0.03, detail=woven, weave=("twill", 0.0014, 0.00006),
                             mottle=0.025, hem=dict(w=0.016, stitch=[(0.012, st_grey), (0.0145, st_grey)])),
        Wr.SHORTS_PANEL: dict(color=blue, rough=0.7, detail=woven, weave=("twill", 0.0014, 0.00006),
                              hem=dict(w=0.016, stitch=[(0.012, blue_d), (0.0145, blue_d)])),
        Wr.SHORTS_BAND: dict(color=blk2, rough=0.82, detail=knit, weave=("rib", 0.0024, 0.00018),
                             hem=dict(w=0.005, color=blue, stitch=[(0.0025, blue_d)])),
        Wr.WRAP: dict(color="#131417", rough=0.84, detail=("Fabric034", 0.12, 0.05, 0.8), roll=0.0008),
        Wr.WRAP_BAND: dict(color=blk2, rough=0.93, rough_var=0.05, detail=crepe, weave=("edge_rib", 0.0028, 0.00011),
                           mottle=0.06, edge_wear=0.3, roll=0.0006),
        Wr.WRAP_ACCENT: dict(color=blue, rough=0.9, rough_var=0.05, detail=crepe, weave=("edge_rib", 0.0028, 0.00011),
                             mottle=0.05, edge_wear=0.18, roll=0.0006),
        "_zones": Wr.zones3d,
        "_attrs": ("g_dorsal", "g_sk", "g_tfa", "g_strap"),
        "_seams": [_shorts_seams, _top_seams],
    }
    leather = ("Leather026", 0.2, 0.06, 0.7)
    gloves = {
        Wr.GLOVE_PAD: dict(color="#17181b", rough=0.42, rough_var=0.06, detail=leather, edge_wear=0.2,
                           stitch=[(0.003, p["blue_light"])]),
        Wr.GLOVE_PALM: dict(color="#202125", rough=0.78, detail=("Leather021", 0.12, 0.05, 0.9),
                            weave=("plain", 0.002, 0.00006)),
        Wr.GLOVE_LOOP: dict(color="#17181b", rough=0.48, detail=leather, edge_wear=0.25),
        Wr.GLOVE_CUFF: dict(color="#17181b", rough=0.46, detail=leather,
                            hem=dict(w=0.006, color=blue, rough=0.6, stitch=[(0.0035, blue_d)])),
        Wr.GLOVE_STRAP: dict(color=blue, rough=0.72, detail=woven, weave=("rib_h", 0.0016, 0.00012),
                             hem=dict(w=0.003, color=p["blue_light"], stitch=[(0.002, blue_d)])),
        "_zones": Wr.zones3d,
        "_attrs": ("g_dorsal", "g_sk", "g_tfa", "g_strap"),
        "_extra": [_glove_quilt],
    }
    return outfit, gloves


def ashka(cfg):
    """Coat: black cotton gabardine (twill), top-stitched edges, real seams (shoulder, side, centre
    back, storm-flap yoke, armholes, pocket flaps), horn buttons. Clothes: white poplin shirt with
    placket, black silk tie (fine twill, self-stripe in the roughness), black wool trousers with a
    pressed crease, brown leather loafers (burnished toe/heel, moc-toe apron, saddle strap, welt,
    stacked sole). Tonal steps keep the blacks apart: coat charcoal-black, trousers deeper, tie
    deepest but glossiest."""
    p = cfg["palette"]
    gab = ("Fabric066", 0.3, 0.05, 0.7)
    coat_st = [(0.0065, p["coat_stitch"])]
    coat = {
        A.COAT_MAIN: dict(color=p["coat"], rough=0.74, rough_var=0.03, detail=gab, weave=("twill", 0.0042, 0.00005),
                          mottle=0.035, hem=dict(w=0.012, stitch=coat_st), edge_wear=0.12),
        A.COAT_SKIRT: dict(color=p["coat"], rough=0.74, rough_var=0.03, detail=gab, weave=("twill", 0.0042, 0.00005),
                           mottle=0.035, hem=dict(w=0.028, stitch=[(0.022, p["coat_stitch"])], ridge=1.5),
                           edge_wear=0.15),
        A.COAT_CUFF: dict(color=p["coat"], rough=0.72, detail=gab, weave=("twill", 0.0042, 0.00005),
                          hem=dict(w=0.012, stitch=coat_st), edge_wear=0.15),
        A.COAT_LAPEL: dict(color=p["coat"], rough=0.72, detail=gab, weave=("twill", 0.0042, 0.00005),
                           stitch=coat_st, edge_wear=0.18, roll=0.0016),
        A.COAT_COLLAR: dict(color=p["coat"], rough=0.72, detail=gab, weave=("twill", 0.0042, 0.00005),
                            stitch=coat_st, edge_wear=0.18, roll=0.0016),
        A.COAT_BELT: dict(color=p["coat_dark"], rough=0.7, detail=gab, weave=("twill", 0.0042, 0.00005),
                          stitch=[(0.004, p["coat_stitch"])], edge_wear=0.2),
        A.COAT_BUTTON: dict(color=p["button"], rough=0.42, mottle=0.25, roll=0.0),
        "_zones": _ashka_zones,
        "_seams": [_coat_seams],
        "_height": [_coat_flaps, _coat_folds],
        "_extra": [_button_holes],
    }
    wool = ("Fabric066", 0.25, 0.05, 0.7)
    clothes = {
        A.SHIRT: dict(color=p["shirt"], rough=0.68, detail=("Fabric040", 0.12, 0.02, 0.3), mottle=0.01),
        A.SHIRT_COLLAR: dict(color=p["shirt"], rough=0.66, detail=("Fabric040", 0.12, 0.02, 0.3),
                             stitch=[(0.004, p["shirt_stitch"])], roll=0.0012),
        A.SHIRT_CUFF: dict(color=p["shirt"], rough=0.66, detail=("Fabric040", 0.12, 0.02, 0.3),
                           hem=dict(w=0.006, stitch=[(0.004, p["shirt_stitch"])])),
        A.TIE: dict(color=p["tie"], rough=0.4, rough_var=0.02, detail=("Fabric040", 0.08, 0.015, 0.2), roll=0.0015),
        A.TIE_KNOT: dict(color=p["tie"], rough=0.38, detail=("Fabric040", 0.08, 0.015, 0.2), roll=0.0),
        A.PANTS: dict(color=p["pants"], rough=0.76, rough_var=0.03, detail=wool, weave=("twill", 0.0042, 0.00005),
                      mottle=0.03, hem=dict(w=0.008)),
        A.LOAFER: dict(color=p["loafer"], rough=0.46, rough_var=0.06, detail=("Leather021", 0.14, 0.08, 0.5),
                       mottle=0.08, edge_wear=0.25, roll=0.0015),
        A.LOAFER_STRAP: dict(color=p["loafer"], rough=0.42, detail=("Leather021", 0.14, 0.08, 0.5),
                             stitch=[(0.0025, p["loafer_dark"])], edge_wear=0.2, roll=0.001),
        A.LOAFER_WELT: dict(color=p["welt"], rough=0.5, detail=("Leather021", 0.14, 0.05, 0.4)),
        A.LOAFER_SOLE: dict(color=p["sole"], rough=0.62, detail=("Leather021", 0.14, 0.05, 0.6)),
        "_zones": _ashka_zones,
        "_seams": [_pants_seams, _shirt_placket, _loafer_seams],
        "_height": [_pants_crease],
        "_extra": [_loafer_burnish, _tie_stripe, _shirt_buttons],
    }
    return coat, clothes


# ----------------------------------------------------------------------------- extras

def _shorts_seams(rs, ctx):
    """Seams of the fight shorts: centre front/back and the panel borders (piped, double-stitched)."""
    P = rs.P
    d = np.full(rs.K, 1.0, np.float32)
    along = P[:, 2].astype(np.float32)
    d = np.minimum(d, np.abs(P[:, 0]))
    rig = ctx["rig"]
    for s_, sg in (("l", 1.0), ("r", -1.0)):
        tt, r, foot = G.limb_param(rig, "thigh_" + s_, P)
        rad = P - foot
        rn = np.maximum(np.hypot(rad[:, 0], rad[:, 1]), 1e-6)
        lat = rad[:, 0] * sg / rn
        mine = P[:, 0] * sg > 0.02
        dd = np.abs(np.arccos(np.clip(lat, -1, 1)) - np.arccos(0.74)) * rn
        d = np.where(mine, np.minimum(d, dd), d)
    return [Wr.SHORTS_MAIN, Wr.SHORTS_PANEL], d, along, {"stitch": [(0.0035, ctx["wren_pal"]["stitch_grey"])]}


def _top_seams(rs, ctx):
    """The under-bust band is sewn on: coverstitched seam along its top edge."""
    d = (rs.P[:, 2] - ctx["wren"]["top_band_z"]).astype(np.float32)
    ang = np.arctan2(rs.P[:, 0], -(rs.P[:, 1] - G.spine_y(ctx["rig"], rs.P[:, 2]))) * 0.12
    st = ctx["wren_pal"]["stitch_grey"]
    return [Wr.TOP_MAIN, Wr.TOP_BAND], d, ang.astype(np.float32), {"stitch": [(0.003, st), (0.006, st)]}


def _glove_quilt(rs, part, col, dn, rough, metal, ctx):
    m = part == Wr.GLOVE_PAD
    if not m.any():
        return col, dn, rough, metal
    P = rs.P[m]
    g = np.zeros(m.sum(), np.float32)
    for s, (kn, ax) in ctx["glove_frames"].items():
        side = (P[:, 0] > 0) if s == "l" else (P[:, 0] <= 0)
        sk = (P - kn) @ ax
        lines = np.exp(-((np.mod(sk + 0.004, 0.017) - 0.0085) / 0.0011) ** 2) * (sk < -0.005) * (sk > -0.075)
        g = np.where(side, lines, g)
    col[m] = col[m] * (1 - 0.45 * g[:, None])
    n = dn[m].copy()
    n[:, 1] -= g * 0.5
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    dn[m] = n
    return col, dn, rough, metal


def _ashka_zones(part, rs, ctx, attrs):
    return part


def _coat_seams(rs, ctx):
    """Coat seams in 3D: centre back, side seams, shoulder seams, the storm-flap yoke edge at the back
    and the armhole rings."""
    P, rig, f = rs.P, ctx["rig"], ctx["ashka"]["landmarks"]
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    sy = G.spine_y(rig, z)
    back = y > sy
    torso = np.abs(x) < 0.2
    d = np.full(rs.K, 1.0, np.float32)
    along = z.astype(np.float32).copy()
    cb = np.where(back & (z < f["zc"] + 0.02), np.abs(x), 1.0)
    d = np.minimum(d, cb)
    side = np.where(torso & (z < f["zc"] - 0.05), np.abs(y - (sy - 0.035)) + (np.abs(x) < 0.08), 1.0)
    d = np.minimum(d, side)
    sh = np.where((z > f["zc"] - 0.04) & (np.abs(x) > 0.05) & (np.abs(x) < 0.17), np.abs(y - sy + 0.005), 1.0)
    d = np.minimum(d, sh)
    yoke = np.where(back & (np.abs(x) < 0.17), np.abs(z - (f["zc"] - 0.14)), 1.0)
    along = np.where(yoke < d, x, along)
    d = np.minimum(d, yoke)
    for s_ in "lr":
        b = rig.data.bones["upperarm_" + s_]
        h, t = np.array(b.head_local), np.array(b.tail_local)
        dd = (t - h) / np.linalg.norm(t - h)
        ring = np.abs((P - h) @ dd - 0.025)
        mine = (x > 0.08) if s_ == "l" else (x < -0.08)
        ring = np.where(mine, ring, 1.0)
        along = np.where(ring < d, np.arctan2(P[:, 1] - h[1], P[:, 2] - h[2]) * 0.05, along)
        d = np.minimum(d, ring)
    pal = ctx["ashka_pal"]
    return [A.COAT_MAIN, A.COAT_SKIRT, A.COAT_CUFF], d.astype(np.float32), along.astype(np.float32), \
        {"stitch": [(0.004, pal["coat_stitch"])]}


def _flap_sdf(P, f):
    """Signed distance (m) to the two slanted pocket flaps on the skirt front (negative inside)."""
    best = np.full(len(P), 1.0, np.float32)
    for sg in (1.0, -1.0):
        c = np.array([sg * 0.115, f["zp"] - 0.075])
        ang = math.radians(-14) * sg
        u = (P[:, 0] - c[0]) * math.cos(ang) + (P[:, 2] - c[1]) * math.sin(ang)
        v = -(P[:, 0] - c[0]) * math.sin(ang) + (P[:, 2] - c[1]) * math.cos(ang)
        dx, dz = np.abs(u) - 0.075, np.abs(v) - 0.026
        sd = np.hypot(np.maximum(dx, 0), np.maximum(dz, 0)) + np.minimum(np.maximum(dx, dz), 0) - 0.004
        front = P[:, 1] < -0.02
        best = np.where(front & (P[:, 0] * sg > 0), np.minimum(best, sd), best)
    return best


def _coat_flaps(rs, part, ctx):
    f = ctx["ashka"]["landmarks"]
    sd = _flap_sdf(rs.P, f)
    m = np.isin(part, [A.COAT_SKIRT, A.COAT_MAIN])
    h = (1 - M.smoothstep(-0.0015, 0.0005, sd)) * 0.0009 * m
    # storm-flap yoke: the back panel above the yoke edge stands a little proud
    sy = G.spine_y(ctx["rig"], rs.P[:, 2])
    yoke = (rs.P[:, 1] > sy) & (np.abs(rs.P[:, 0]) < 0.17) & m
    h += yoke * M.smoothstep(f["zc"] - 0.142, f["zc"] - 0.136, rs.P[:, 2]) * 0.0008
    return h.astype(np.float32)


def _coat_folds(rs, part, ctx):
    """Cloth folds in the normal map: gathers above and below the belt, compression folds in the
    inner elbow, bunching above the cuffs, drag lines from the armpits."""
    P, rig, f = rs.P, ctx["rig"], ctx["ashka"]["landmarks"]
    o = ctx["ashka_cfg"]["outfit"]
    m = np.isin(part, [A.COAT_MAIN, A.COAT_SKIRT, A.COAT_CUFF]).astype(np.float32)
    h = np.zeros(rs.K, np.float32)
    ang = np.arctan2(P[:, 0], -(P[:, 1] - G.spine_y(rig, P[:, 2])))
    dzb = P[:, 2] - f["zb"]
    near = np.exp(-((np.abs(dzb) - o["belt_height"] * 0.5 - 0.02) / 0.022) ** 2) * (np.abs(P[:, 0]) < 0.25)
    h += 0.0005 * near * np.sin(ang * 30.0 + 2.5 * np.sin(ang * 5.0)) * (0.5 + 0.5 * T.vnoise3(P, 30.0, 9))
    for s_ in "lr":
        side = (P[:, 0] > 0.12) if s_ == "l" else (P[:, 0] < -0.12)
        b = rig.data.bones["lowerarm_" + s_]
        hd, tl = np.array(b.head_local), np.array(b.tail_local)
        L = np.linalg.norm(tl - hd)
        d = (tl - hd) / L
        along = (P - hd) @ d
        foot = hd + np.outer(along, d)
        rad = P - foot
        up = np.array(rig.data.bones["upperarm_" + s_].head_local) - hd
        up -= d * (up @ d)
        up /= np.linalg.norm(up)
        inner = M.smoothstep(0.0, 0.7, -(rad @ up) / np.maximum(np.linalg.norm(rad, axis=1), 1e-6))
        elbow = np.exp(-(along / 0.05) ** 2) * inner * side
        h += 0.0009 * elbow * np.sin(along / 0.011 * 2 * math.pi + 1.5 * np.sin(np.arctan2(rad[:, 2], rad[:, 1]) * 2))
        t = along / L
        cuff = M.smoothstep(0.55, 0.75, t) * (1 - M.smoothstep(0.86, 0.9, t)) * side
        h += 0.0006 * cuff * np.sin(along / 0.017 * 2 * math.pi + 2.0 * np.sin(np.arctan2(rad[:, 2], rad[:, 0]) * 3))
        sh = np.array(rig.data.bones["upperarm_" + s_].head_local)
        dd = P - (sh + np.array([0, 0, -0.06]))
        drag = np.exp(-((np.linalg.norm(dd, axis=1) - 0.08) / 0.03) ** 2) * (np.abs(P[:, 0]) < np.abs(sh[0]) - 0.02)
        h += 0.0005 * drag * np.sin((dd[:, 1] * 0.8 + dd[:, 2]) / 0.02 * 2 * math.pi)
    return (h * m).astype(np.float32)


def _button_holes(rs, part, col, dn, rough, metal, ctx):
    """Four holes and a raised rim on each button; flap outlines get stitched (seam set handles the
    groove)."""
    m = part == A.COAT_BUTTON
    f = ctx["ashka"]["landmarks"]
    sd = _flap_sdf(rs.P, f)
    fl = np.exp(-((sd - 0.0) / 0.0009) ** 2) * np.isin(part, [A.COAT_SKIRT, A.COAT_MAIN])
    col = col * (1 - 0.25 * fl)[:, None]
    st = np.exp(-((sd + 0.005) / 0.0005) ** 2) * (np.mod((rs.P[:, 0] + rs.P[:, 2]) / 0.0035, 1) < 0.62) \
        * np.isin(part, [A.COAT_SKIRT, A.COAT_MAIN])
    col = T.mix(col, T.hexrgb(ctx["ashka_pal"]["coat_stitch"]), st * 0.7)
    if m.any():
        # tone variation in horn
        col[m] = col[m] * (1 + 0.18 * T.fbm(rs.P[m], 260.0, 3, seed=5)[:, None])
    return col, dn, rough, metal


def _pants_seams(rs, ctx):
    """Outer side seam of each trouser leg."""
    P, rig = rs.P, ctx["rig"]
    d = np.full(rs.K, 1.0, np.float32)
    along = P[:, 2].astype(np.float32)
    for s_, sg in (("l", 1.0), ("r", -1.0)):
        for bone in ("thigh_" + s_, "calf_" + s_):
            tt, r, foot = G.limb_param(rig, bone, P)
            rad = P - foot
            rn = np.maximum(np.hypot(rad[:, 0], rad[:, 1]), 1e-6)
            lat = rad[:, 0] * sg / rn
            on = (P[:, 0] * sg > 0.03) & (tt > -0.05) & (tt < 1.05)
            dd = np.abs(np.arccos(np.clip(lat, -1, 1))) * rn
            d = np.where(on, np.minimum(d, dd), d)
    return [A.PANTS], d, along, {"stitch": []}


def _pants_crease(rs, part, ctx):
    """Pressed crease: a sharp ridge on the front (and back) centre line of each leg."""
    P, rig = rs.P, ctx["rig"]
    h = np.zeros(rs.K, np.float32)
    m = part == A.PANTS
    for s_, sg in (("l", 1.0), ("r", -1.0)):
        for bone, t0 in (("thigh_" + s_, 0.3), ("calf_" + s_, -0.05)):
            tt, r, foot = G.limb_param(rig, bone, P)
            rad = P - foot
            rn = np.maximum(np.hypot(rad[:, 0], rad[:, 1]), 1e-6)
            fwd = -rad[:, 1] / rn
            on = m & (P[:, 0] * sg > 0.02) & (tt > t0) & (tt < 1.02)
            ang_d = np.arccos(np.clip(fwd, -1, 1)) * rn
            bk = np.arccos(np.clip(-fwd, -1, 1)) * rn
            h += on * (0.0012 * np.exp(-ang_d / 0.0025) + 0.0006 * np.exp(-bk / 0.003))
        # the break: soft folds above the hem where the trousers rest on the shoe; behind the knee
        ank = np.array(rig.data.bones["foot_" + s_].head_local)
        sole = ctx["ashka"]["loafer"]["sole"]
        z0 = sole + ctx["ashka_cfg"]["outfit"]["hem_front_z"]
        fr = M.smoothstep(ank[1] + 0.03, ank[1] - 0.03, P[:, 1]) * (P[:, 0] * sg > 0.02) * m
        band = M.smoothstep(z0, z0 + 0.015, P[:, 2]) * (1 - M.smoothstep(z0 + 0.07, z0 + 0.1, P[:, 2]))
        h += 0.00045 * fr * band * np.sin((P[:, 2] - z0) / 0.03 * 2 * math.pi + 1.5 * np.sin(P[:, 0] * 90)) \
            * (0.5 + 0.5 * T.vnoise3(P, 40.0, 3))
        kn = np.array(rig.data.bones["calf_" + s_].head_local)
        bk_knee = np.exp(-((P[:, 2] - kn[2]) / 0.05) ** 2) * M.smoothstep(kn[1], kn[1] + 0.04, P[:, 1]) \
            * (P[:, 0] * sg > 0.02) * m
        h += 0.0005 * bk_knee * np.sin((P[:, 2] - kn[2]) / 0.02 * 2 * math.pi + 2 * np.sin(P[:, 0] * 60))
    return h


def _shirt_placket(rs, ctx):
    P = rs.P
    d = np.abs(np.abs(P[:, 0]) - 0.016).astype(np.float32)
    d = np.where(P[:, 1] < -0.02, d, 1.0).astype(np.float32)
    return [A.SHIRT], d, P[:, 2].astype(np.float32), {"stitch": [(0.0035, ctx["ashka_pal"]["shirt_stitch"])]}


def _shirt_buttons(rs, part, col, dn, rough, metal, ctx):
    m = part == A.SHIRT
    f = ctx["ashka"]["landmarks"]
    P = rs.P
    acc = np.zeros(rs.K, np.float32)
    for z in np.arange(f["zp"] + 0.07, f["zn"], 0.075):         # waistband to collar
        dd = np.hypot(P[:, 0], P[:, 2] - z)
        acc = np.maximum(acc, 1 - M.smoothstep(0.0045, 0.0055, dd))
    acc *= m & (P[:, 1] < -0.02)
    col = T.mix(col, np.array([0.86, 0.85, 0.82], np.float32), acc * 0.8)
    rough = rough * (1 - acc) + 0.3 * acc
    return col, dn, rough, metal


def _tie_stripe(rs, part, col, dn, rough, metal, ctx):
    """Black-on-black self stripe: diagonal bands of slightly different sheen."""
    m = (part == A.TIE) | (part == A.TIE_KNOT)
    P = rs.P[m]
    ph = np.mod((P[:, 0] + P[:, 2]) / 0.022, 1.0)
    st = M.smoothstep(0.0, 0.05, ph) * (1 - M.smoothstep(0.2, 0.25, ph))
    rough[m] = rough[m] + 0.08 * st
    col[m] = col[m] * (1 + 0.1 * st[:, None])
    return col, dn, rough, metal


def _loafer_frame(P, ctx):
    fr = ctx["ashka"]["loafer"]["frames"]
    fp = np.zeros(len(P))
    op = np.zeros(len(P))
    for s_, (ank, fwd) in fr.items():
        side = (P[:, 0] > 0) if s_ == "l" else (P[:, 0] <= 0)
        outw = np.array([1.0, 0, 0]) if s_ == "l" else np.array([-1.0, 0, 0])
        outw = outw - fwd * (outw @ fwd)
        outw /= np.linalg.norm(outw)
        d = P - np.array([ank[0], ank[1], 0.0])
        fp = np.where(side, d @ fwd, fp)
        op = np.where(side, d @ outw, op)
    return fp, op


def _loafer_seams(rs, ctx):
    """Moc-toe apron: a U-shaped raised seam over the forefoot."""
    P = rs.P
    fp, op = _loafer_frame(P, ctx)
    sole = ctx["ashka"]["loafer"]["sole"]
    ox = op - 0.004
    straight = np.where(fp < 0.135, np.abs(np.abs(ox) - 0.03), 1.0)
    straight = np.where(fp > 0.06, straight, 1.0)
    front = np.abs(np.hypot(ox, np.maximum(fp - 0.135, 0) * 1.2) - 0.03)
    front = np.where(fp >= 0.135, front, 1.0)
    d = np.minimum(straight, front)
    d = np.where(P[:, 2] > sole + 0.022, d, 1.0).astype(np.float32)
    return [A.LOAFER], d, (fp + op).astype(np.float32), {"stitch": [(0.0022, ctx["ashka_pal"]["loafer_dark"])]}


def _loafer_burnish(rs, part, col, dn, rough, metal, ctx):
    """Burnished (darker, glossier) toe cap and heel counter, darker creases over the flex line,
    penny slot on the strap, stacked-heel lines on the sole edge."""
    P = rs.P
    fp, op = _loafer_frame(P, ctx)
    pal = ctx["ashka_pal"]
    m = (part == A.LOAFER) | (part == A.LOAFER_STRAP)
    toe = M.smoothstep(0.13, 0.19, fp)
    heel = M.smoothstep(-0.03, -0.075, fp)
    b = np.clip(toe + heel, 0, 1) * m
    col = T.mix(col, T.hexrgb(pal["loafer_dark"]) * 1.15, b * 0.55)
    rough = rough - 0.14 * b
    crease = np.exp(-((fp - 0.11) / 0.012) ** 2) * m * (0.5 + 0.5 * np.sin(op * 900.0) ** 2)
    col = col * (1 - 0.12 * crease)[:, None]
    so = np.hypot(op / 0.011, (fp - (0.045 - 0.03 * np.clip(op / 0.04, -1.2, 1.2) ** 2 + 0.006 + 0.0135)) / 0.0042)
    slot = (1 - M.smoothstep(0.85, 1.0, so)) * (part == A.LOAFER_STRAP)
    col = col * (1 - 0.6 * slot)[:, None]
    rim = np.exp(-((so - 1.0) / 0.12) ** 2) * (part == A.LOAFER_STRAP)
    col = col * (1 + 0.15 * rim)[:, None]
    s_m = part == A.LOAFER_SOLE
    lines = (np.mod(P[:, 2] / 0.0042, 1.0) < 0.12) & (fp < -0.0)
    col[s_m & lines] *= 0.7
    return col, dn, rough, metal


