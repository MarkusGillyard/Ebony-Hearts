"""Ashka Rook's canon outfit (character sheet version 2, 2026-11-09): a Gothic-Victorian ensemble.

Frock coat: torso and sleeves are a shell grown from the body (inheriting skin weights), draped so the cloth
falls from the bust and shoulder blades, fitted at the waist, with structured shoulders and rounded sleeves. The
fronts meet at a single waist button and open above it to a high standing collar; below the waist seam the
coattails are a lofted skirt that ends just above the knee, split into four panels (front opening, two side slits,
a back vent), each skinned to its own 3-bone chain (coat_fl/fr/bl/br, the chains the rig always had). The tails'
crimson lining is its own inner layer joined by a turned edge along the hem and splits. Silver buttons and a small
crimson gem brooch. Piping, embroidery and the ice-white cuff and collar trim are painted (eh_specs).
Under it: an ice-white blouse (a full shell, smoothed and tucked) with a high stand collar, a brocade waistcoat with
silver buttons and a chain, and a crimson cravat (knot, puffed front, dark-silver clasp). High-waisted trousers fall
straight with a front crease and a break over the boot. Ankle boots are built on the fitted last of the earlier
loafers (upper, welt, sole with a low stacked heel) with a shaft to above the ankle.

The previous outfits (sheet version 1's shirt, tie and loafers; the earlier trench coat with lapels, belt and cuff
straps) are no longer canon; their builders were removed (see the repository history)."""
import math

import bpy
import numpy as np

import eh_garment as G
import eh_mesh as M
import eh_rig as R

# part tags
COAT_MAIN, COAT_LAPEL, COAT_COLLAR, COAT_BELT, COAT_BUCKLE, COAT_SKIRT, COAT_CUFF, COAT_BUTTON = 1, 2, 3, 4, 5, 6, 7, 8
SHIRT, SHIRT_COLLAR, SHIRT_CUFF, TIE, PANTS, LOAFER, LOAFER_SOLE = 11, 12, 13, 14, 15, 16, 17
LOAFER_WELT, LOAFER_STRAP, TIE_KNOT = 18, 19, 20
COAT_LINING, WAISTCOAT, WAISTCOAT_BUTTON, CRAVAT_CLASP, CHAIN, GEM, GEM_SETTING = 9, 21, 22, 23, 24, 25, 26

PANELS = (("fl", math.pi * 0.25, "l"), ("bl", math.pi * 0.75, "l"),
          ("br", math.pi * 1.25, "r"), ("fr", math.pi * 1.75, "r"))
GRID_COLUMNS = 12      # cloth columns round the coat's tails (coat_c01..c12), three per panel


def landmarks(rig, cfg):
    o = cfg["outfit"]
    f = {}
    f["zc"] = rig.data.bones["clavicle_l"].head_local[2]
    f["zp"] = rig.data.bones["pelvis"].head_local[2]
    f["zn"] = rig.data.bones["neck_01"].head_local[2]
    f["zb"] = f["zp"] + o["belt_above_pelvis"]
    f["zvb"] = f["zp"] + o["v_bottom_above_pelvis"]
    f["z_vtop"] = f["zc"] + 0.07
    f["z_cut"] = f["zp"] + o["skirt_top_rel_pelvis"]
    return f


def vline(z, f, o):
    """Half-width of the coat's V opening at height z (0 at the top button)."""
    return np.clip((np.asarray(z) - f["zvb"]) / (f["z_vtop"] - f["zvb"]), 0, None) ** 1.1 * o["v_halfwidth_top"]


def build(body, rig, cfg, collider_body):
    o = cfg["outfit"]
    V = M.co(body)
    W = M.weights(body)
    X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
    ax = np.abs(X)
    f = landmarks(rig, cfg)
    zc, zp, zn = f["zc"], f["zp"], f["zn"]
    sy = G.spine_y(rig, Z)
    front = Y < sy
    out = {}
    hide = np.zeros(len(body.data.polygons), bool)
    handw = {s: G.wsum(W, G.side_names(G.HAND, s)) for s in "lr"}
    tfa = {s: G.limb_param(rig, "lowerarm_" + s, V)[0] for s in "lr"}
    armw = {s: G.wsum(W, G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], s))
            for s in "lr"}
    is_arm = (armw["l"] > 0.5) | (armw["r"] > 0.5)
    arm_t = np.where(X > 0, tfa["l"], tfa["r"])
    hand = (handw["l"] > 0.4) | (handw["r"] > 0.4)
    neck_cut = np.where(front, zn - 0.035 + 18 * ax ** 2, zn - 0.005 + 10 * ax ** 2)
    headw = W.get("head", np.zeros(len(V)))
    info = {"landmarks": f}

    # ------------------------------------------------------------------ waistline (high-waisted trousers' top edge)
    zwf, zwb = zp + o["waist_front_above_pelvis"], zp + o["waist_back_above_pelvis"]
    zw = np.where(front, zwf, zwb)
    zw_front = zwf

    # ------------------------------------------------------------------ shirt: full, long-sleeved, tucked in
    cuff_t = o["cuff_start_t"]
    z_tuck = zw_front - o["shirt_tuck_depth"]
    region = (Z >= z_tuck - 0.04) & (Z < neck_cut + 0.012) & ~hand & (headw < 0.3) \
        & ~(is_arm & (arm_t > cuff_t + 0.08))
    t_arm = np.where(is_arm, arm_t, 0.0)
    off = np.where(is_arm, o["shirt_sleeve_offset"] + 0.004 * M.smoothstep(0.3, 1.0, t_arm),
                   o["shirt_offset"] + o["shirt_blouse"] * np.exp(-((Z - (zw_front + 0.035)) / 0.035) ** 2))

    def tuck(P):
        return P[:, 2] - z_tuck

    cuts = (tuck, _limb_cut(rig, "lowerarm_l", cuff_t + 0.02), _limb_cut(rig, "lowerarm_r", cuff_t + 0.02))
    shirt, src, fm = G.shell(body, region, "shirt", off, collider_body, relax_iters=12, relax_factor=0.5,
                             smooth_offset=6, lip=0.0, soft=3, implicit=cuts, edge_smooth=0)
    shirt_cover = fm & M.face_mask_from_verts(body, ~(is_arm & (arm_t > cuff_t - 0.02)), "all")
    f_sh = dict(f, z_cut=z_tuck, zb=zw_front + 0.02)
    o_sh = dict(o, drape_slope=o["shirt_drape_slope"], drape_slope_side=o["shirt_drape_slope_side"],
                drape_reach=o["shirt_drape_reach"], drape_ease=o["shirt_drape_ease"],
                belt_ease=o["shirt_waist_ease"], belt_blouse=o["shirt_waist_blouse"])
    _drape_torso(shirt, body, rig, f_sh, {"outfit": o_sh}, collider_body)
    for s_ in "lr":
        _round_sleeve(shirt, rig, s_, {"sleeve_round": o["shirt_sleeve_round"]})
    _settle_shirt(shirt, rig, collider_body, zwf, zwb, o)
    Wsh = M.weights(shirt)                # torso shell: no thigh influence
    for s_ in "lr":
        for nm in ("thigh_" + s_, "thigh_twist_01_" + s_, "thigh_half_" + s_):
            if nm in Wsh:
                Wsh["pelvis"] = Wsh.get("pelvis", 0) + Wsh.pop(nm)
    Wsh = M.smooth_weights(Wsh, M.adjacency(shirt), 3, 0.5)
    M.set_weights(shirt, M.normalize_limit(Wsh, 8))
    _tags(shirt, SHIRT)
    hide |= G.hidden_face_mask(body, shirt_cover, garment=shirt, margin_m=0.012)
    cuffs = []
    for s in "lr":
        side = (X > 0) if s == "l" else (X < 0)
        vm = side & (armw[s] + handw[s] > 0.4) & (tfa[s] > cuff_t - 0.06) & (tfa[s] < 1.08)
        c, src, fm = G.shell(body, vm, "cuff_" + s, 0.0072, collider_body, relax_iters=3, lip=0.003,
                             implicit=(_limb_cut(rig, "lowerarm_" + s, cuff_t, keep_after=True),
                                       _limb_cut(rig, "lowerarm_" + s, 1.0)), edge_smooth=0)
        _round_limb(c, rig, "lowerarm_" + s, 0.7, 0.003)
        _tags(c, SHIRT_CUFF)
        cuffs.append(c)
        hide |= G.hidden_face_mask(body, fm, garment=c, margin_m=0.025)
    scollar = _blouse_collar(body, rig, cfg)
    _weights_from(scollar, shirt)
    shirt = M.join([shirt] + cuffs + [scollar], "shirt")
    out["shirt"] = shirt
    tie_ob = cravat(rig, cfg, shirt, f)
    _weights_from(tie_ob, shirt)
    out["tie"] = tie_ob

    # ------------------------------------------------------------------ trousers (over the tucked shirt)
    legs = np.zeros(len(V), bool)
    for s in "lr":
        legs |= G.wsum(W, G.side_names(["thigh", "thigh_twist_01", "calf"], s)) > 0.5
    footw = G.wsum(W, G.side_names(["foot", "ball"], "l") + G.side_names(["foot", "ball"], "r"))
    z_ank = rig.data.bones["foot_l"].head_local[2]
    sole = cfg["sole_m"]
    vm = (Z <= zw + 0.02) & (Z >= sole + 0.015) & ~((footw >= 0.5) & (Z < z_ank - 0.02)) & ~is_arm & ~hand
    tcalf = np.where(X > 0, G.limb_param(rig, "calf_l", V)[0], G.limb_param(rig, "calf_r", V)[0])
    off = 0.0055 + 0.006 * M.smoothstep(0.15, 0.6, tcalf) * legs \
        + o["pants_waist_ease"] * M.smoothstep(z_tuck - 0.03, z_tuck + 0.01, Z)

    def straighten(P, src_):
        # trousers hang straight below the knee: push out to a minimum radius about the shin line
        out_ = np.zeros_like(P)
        for s in "lr":
            b = rig.data.bones["calf_" + s]
            h, t = np.array(b.head_local), np.array(b.tail_local)
            d = t - h
            tt = ((P - h) @ d) / (d @ d)
            foot = h + np.outer(np.clip(tt, 0, 1), d)
            r = P - foot
            r[:, 2] = 0
            rn = np.linalg.norm(r, axis=1)
            mine = ((P[:, 0] > 0) if s == "l" else (P[:, 0] < 0)) & (tt > 0.05)
            rmin = o["pants_min_radius"] * M.smoothstep(0.0, 0.5, tt)
            push = np.maximum(rmin - rn, 0) * mine
            out_ += r / np.maximum(rn, 1e-6)[:, None] * push[:, None]
        return out_

    hem_cuts = tuple(_hem_cut(rig, s, cfg) for s in "lr")

    def waist_cut(P):
        # a clean, high waistline (blended from the back's height to the front's round the sides)
        ff = 1 - M.smoothstep(-0.03, 0.03, P[:, 1] - G.spine_y(rig, P[:, 2]))
        return zwb - (zwb - zwf) * ff - P[:, 2]

    pants, src, fm = G.shell(body, vm, "pants", off, collider_body, relax_iters=14, relax_factor=0.5,
                             smooth_offset=5, lip=0.0045, extra_push=straighten, implicit=hem_cuts + (waist_cut,),
                             edge_smooth=0)
    _crease_and_break(pants, rig, cfg)
    _tags(pants, PANTS)
    hide |= G.hidden_face_mask(body, fm, garment=pants)
    out["pants"] = pants

    # ------------------------------------------------------------------ loafers
    loafers = []
    for s in "lr":
        lo = loafer(body, rig, cfg, s, W, V, boot=True)
        loafers.append(lo)
        side = (X > 0) if s == "l" else (X < 0)
        fm = M.face_mask_from_verts(body, side & (footw > 0.3) & (Z < z_ank + 0.01), "all")
        hide |= G.hidden_face_mask(body, fm, garment=lo, margin_m=0.004)
    out["loafers"] = M.join(loafers, "loafers")
    info["loafer"] = {"sole": sole, "frames": {}}
    for s in "lr":
        ank = np.array(rig.data.bones["foot_" + s].head_local)
        bp = np.array(rig.data.bones["ball_" + s].head_local)
        fwd = bp - ank
        fwd[2] = 0
        fwd /= np.linalg.norm(fwd)
        info["loafer"]["frames"][s] = (ank, fwd)

    # ------------------------------------------------------------------ waistcoat over the blouse
    out["waistcoat"] = _waistcoat(body, rig, cfg, f, collider_body, out["shirt"], zwf, hide, is_arm, hand, headw, Z,
                                  neck_cut)
    # ------------------------------------------------------------------ frock coat over everything
    f_coat = dict(f, z_cut=zp + o["coat_waist_above_pelvis"], zb=zp + o["coat_waist_above_pelvis"],
                  zvb=zp + o["v_bottom_above_pelvis"])
    coat, skirt_info = _frock_coat(body, rig, cfg, f_coat, collider_body, [out["shirt"], out["waistcoat"], out["tie"]],
                                   hide, is_arm, arm_t, hand, Z, neck_cut, [out["pants"], out["loafers"]])
    out["coat"] = coat
    info["coat_landmarks"] = f_coat
    out["_info"] = info
    return out, hide, skirt_info


# ----------------------------------------------------------------------------- helpers

def _settle_shirt(shirt, rig, collider, zwf, zwb, o):
    """Shirt over the torso: Laplacian passes even out small bumps the shell copied from the body (the
    shirt spans them), then a minimum gap off the body; below the trousers' waistband (front zp + 4.5
    cm, back zp + 6 cm) it is tucked in, so it is pulled to a thin layer that the waistband covers."""
    P = M.co(shirt)
    adj = M.adjacency(shirt)
    Wc = M.weights(shirt)
    arm = G.wsum(Wc, G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], "l")
                 + G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], "r"))
    fixed = M.boundary_vmask(shirt) | (arm > 0.35)
    P = M.smooth(P, adj, o["shirt_smooth_iters"], 0.5, fixed=fixed)
    P, _ = collider.push_out(P, o["shirt_offset"])
    d, loc, dirv = collider.signed_distance(P)
    ff = 1 - M.smoothstep(-0.03, 0.03, P[:, 1] - G.spine_y(rig, P[:, 2]))     # 1 at the front (as the waist cut)
    zw = zwb - (zwb - zwf) * ff
    tucked = 1 - M.smoothstep(zw - 0.004, zw + 0.022, P[:, 2])
    gap = d + (np.minimum(d, o["shirt_tucked_gap"]) - d) * tucked
    M.set_co(shirt, loc + dirv * gap[:, None])


def _limb_cut(rig, bone, t_end, radius=0.12, keep_after=False):
    """Implicit cut across a limb: removes the part beyond fraction t_end of `bone` (or before it with
    keep_after) within `radius` of the bone axis."""
    b = rig.data.bones[bone]
    h, t = np.array(b.head_local), np.array(b.tail_local)
    d = (t - h) / np.linalg.norm(t - h)
    p0 = h + (t - h) * t_end

    def fn(P):
        along = (P - p0) @ d
        foot = p0 + np.outer(along, d)
        dist = np.linalg.norm(P - foot, axis=1)
        return np.maximum(along if keep_after else -along, dist - radius)
    return fn


def _round_limb(ob, rig, bone, k, ease):
    """Pulls a tube-like garment towards a round cross-section about the bone axis (k: 0..1)."""
    b = rig.data.bones[bone]
    h, t = np.array(b.head_local), np.array(b.tail_local)
    d = (t - h) / np.linalg.norm(t - h)
    P = M.co(ob)
    along = (P - h) @ d
    foot = h + np.outer(along, d)
    rad = P - foot
    r = np.linalg.norm(rad, axis=1)
    bins = np.round(along / 0.01).astype(int)
    rmax = np.zeros_like(r)
    for bi in np.unique(bins):
        m = bins == bi
        rmax[m] = r[m].max()
    rt = r + (rmax - r) * k + ease
    P = foot + rad / np.maximum(r, 1e-6)[:, None] * rt[:, None]
    M.set_co(ob, P)


def _tags(ob, value):
    G.set_part_attr(ob, "part", np.full(len(ob.data.vertices), value, np.int32))


def _weights_from(dst, src):
    Wd = M.transfer_weights_nearest(dst, M.co(src), M.weights(src), k=4)
    M.set_weights(dst, M.normalize_limit(Wd, 8))


def _weld_points(ob, pts, dist=2e-4):
    """Welds coincident vertices only at the given positions (skirt top row onto the hip loop)."""
    import bmesh
    from mathutils.kdtree import KDTree
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    sel = [v for v in bm.verts if kd.find(v.co)[2] < dist]
    bmesh.ops.remove_doubles(bm, verts=sel, dist=dist)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def _grid(name, P, closed_u=False):
    """Quad grid object from points P (rows, cols, 3); UVs in metres along the grid lines."""
    nr, nc = P.shape[:2]
    verts = P.reshape(-1, 3)
    du = np.linalg.norm(np.diff(P, axis=1), axis=2).mean(0)
    dv = np.linalg.norm(np.diff(P, axis=0), axis=2).mean(1)
    us = np.r_[0, np.cumsum(du)]
    vs = np.r_[0, np.cumsum(dv)]
    faces, uvs = [], []
    cols = nc if closed_u else nc - 1
    for i in range(nr - 1):
        for j in range(cols):
            j2 = (j + 1) % nc
            faces.append((i * nc + j, i * nc + j2, (i + 1) * nc + j2, (i + 1) * nc + j))
            u0, u1 = us[j], (us[j + 1] if j + 1 < len(us) else us[-1] + du[-1])
            uvs.append([(u0, vs[i]), (u1, vs[i]), (u1, vs[i + 1]), (u0, vs[i + 1])])
    return M.make_object(name, verts, faces, uvs)


# ----------------------------------------------------------------------------- coat drape

def _drape_torso(coat, body, rig, f, cfg, collider):
    """Pushes the coat torso out to a hanging envelope of the body: per horizontal slice and angle
    the body's outer radius, then cloth falling from every higher point with a limited inward slope
    (steeper at the sides), drawn in by the belt."""
    o = cfg["outfit"]
    Vb = M.co(body)
    Wb = M.weights(body)
    armw = G.wsum(Wb, G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], "l")
                  + G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], "r")
                  + ["upperarm_half_l", "upperarm_half_r"])
    z0, z1 = f["z_cut"] - 0.05, f["zc"] + 0.02
    torso = (armw < 0.25) & (Vb[:, 2] > z0 - 0.1) & (Vb[:, 2] < z1 + 0.05) & (np.abs(Vb[:, 0]) < 0.25)
    dz, na = 0.015, 72
    zs = np.arange(z0 - 0.06, z1 + 0.08, dz)
    nz = len(zs)
    # cross-section centre: midway between the body's front and back at the centre line
    cy = np.zeros(nz)
    for i, z in enumerate(zs):
        m = torso & (np.abs(Vb[:, 2] - z) < dz) & (np.abs(Vb[:, 0]) < 0.04)
        cy[i] = 0.5 * (Vb[m, 1].min() + Vb[m, 1].max()) if m.sum() > 2 else G.spine_y(rig, np.array([z]))[0] - 0.08

    def polar(P):
        yc = np.interp(P[:, 2], zs, cy)
        a = np.arctan2(P[:, 0], -(P[:, 1] - yc))
        return a, np.hypot(P[:, 0], P[:, 1] - yc), yc

    Bv = Vb[torso]
    a, r, _ = polar(Bv)
    zi = np.clip(np.round((Bv[:, 2] - zs[0]) / dz).astype(int), 0, nz - 1)
    ai = np.round((a + math.pi) / (2 * math.pi) * na).astype(int) % na
    H = np.zeros((nz, na))
    np.maximum.at(H, (zi, ai), r)
    for i in range(nz):                       # fill empty angle bins (circular interpolation)
        row = H[i]
        ok = row > 0
        if ok.sum() < 3:
            H[i] = H[i - 1] if i else 0.1
            continue
        idx = np.nonzero(ok)[0]
        H[i] = np.interp(np.arange(na), np.r_[idx - na, idx, idx + na], np.r_[row[idx], row[idx], row[idx]])
    for _ in range(3):
        H = 0.5 * H + 0.25 * (np.roll(H, 1, 1) + np.roll(H, -1, 1))
    ang = (np.arange(na) / na) * 2 * math.pi - math.pi
    slope = o["drape_slope"] + o["drape_slope_side"] * np.sin(ang) ** 2
    D = H.copy()
    for k in range(1, int(o["drape_reach"] / dz)):
        D[:-k] = np.maximum(D[:-k], H[k:] - slope[None, :] * k * dz)
    ib = int(np.clip(round((f["zb"] - zs[0]) / dz), 0, nz - 1))
    Bc = H[ib][None, :] + o["belt_ease"] + o["belt_blouse"] * np.abs(zs - f["zb"])[:, None]
    D = np.minimum(D, np.maximum(Bc, H))
    for _ in range(2):
        D[1:-1] = 0.5 * D[1:-1] + 0.25 * (D[2:] + D[:-2])
    # apply to the coat shell (torso vertices only, fading out towards the arms and the neck)
    P = M.co(coat)
    Wc = M.weights(coat)
    armc = G.wsum(Wc, G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], "l")
                  + G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], "r")
                  + ["upperarm_half_l", "upperarm_half_r"])
    a, r, yc = polar(P)
    zi = np.clip((P[:, 2] - zs[0]) / dz, 0, nz - 1.001)
    i0 = zi.astype(int)
    tz = zi - i0
    af = (a + math.pi) / (2 * math.pi) * na
    a0 = np.floor(af).astype(int)
    ta = af - a0
    a0 %= na
    a1 = (a0 + 1) % na
    Dv = (D[i0, a0] * (1 - ta) + D[i0, a1] * ta) * (1 - tz) + (D[i0 + 1, a0] * (1 - ta) + D[i0 + 1, a1] * ta) * tz
    k = (1 - M.smoothstep(0.15, 0.6, armc)) * (1 - M.smoothstep(f["zc"] - 0.02, f["zc"] + 0.04, P[:, 2]))
    rt = np.maximum(r, Dv + o["drape_ease"])
    rn = r + (rt - r) * k
    dirv = np.stack([P[:, 0], P[:, 1] - yc, np.zeros(len(P))], 1) / np.maximum(r, 1e-6)[:, None]
    P = np.stack([np.zeros(len(P)), yc, P[:, 2]], 1) + dirv * rn[:, None]
    adj = M.adjacency(coat)
    P = M.relax_shell(P, adj, collider, 0.008, iters=6, factor=0.35, pinned=M.boundary_vmask(coat))
    M.set_co(coat, P)


def _round_sleeve(coat, rig, s, o):
    """Coat sleeve: rounder and looser than the arm (a tube, widening a little to the cuff)."""
    P = M.co(coat)
    Wc = M.weights(coat)
    arm = G.wsum(Wc, G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], s))
    side = (P[:, 0] > 0) if s == "l" else (P[:, 0] < 0)
    sel = side & (arm > 0.1)
    if not sel.any():
        return
    Pn = P.copy()
    best = np.full(len(P), np.inf)
    for bone, k_ease in (("upperarm_" + s, 0.004), ("lowerarm_" + s, 0.01)):
        b = rig.data.bones[bone]
        h, t = np.array(b.head_local), np.array(b.tail_local)
        L = np.linalg.norm(t - h)
        d = (t - h) / L
        along = (P - h) @ d
        tt = along / L
        foot = h + np.outer(along, d)
        rad = P - foot
        r = np.linalg.norm(rad, axis=1)
        inside = sel & (tt > -0.1) & (tt < 1.15)
        bins = np.round(along / 0.012).astype(int)
        rmax = np.zeros_like(r)
        for bi in np.unique(bins[inside]):
            m = inside & (bins == bi)
            rmax[m] = r[m].max()
        rt = r + (rmax - r) * o["sleeve_round"] + k_ease * np.clip(tt, 0, 1)
        cand = foot + rad / np.maximum(r, 1e-6)[:, None] * rt[:, None]
        use = inside & (r < best)
        best = np.where(use, r, best)
        Pn[use] = cand[use]
    w = M.smoothstep(0.2, 0.75, arm)[:, None]
    P = P + (Pn - P) * w
    M.set_co(coat, M.smooth(P, M.adjacency(coat), 2, 0.3, fixed=M.boundary_vmask(coat) | ~sel))


# ----------------------------------------------------------------------------- skirt

def _skirt(coat, loop, rig, cfg, leg_objs, lining_part=None):
    o = cfg["outfit"]
    Pc = M.co(coat)
    Wc = M.weights(coat)
    q = Pc[loop]
    yc = float(q[:, 1].mean())
    ang = np.mod(np.arctan2(q[:, 0], -(q[:, 1] - yc)), 2 * math.pi)       # 0 front, +pi/2 left
    order = np.argsort(ang)
    loop = loop[order]
    q = Pc[loop]
    ang = ang[order]
    N = len(loop)
    z_top = q[:, 2]
    z_hem = o["hem_z"] + cfg["sole_m"]
    Rn = o["skirt_rows"]
    radial = np.stack([q[:, 0], q[:, 1] - yc], 1)
    r_top = np.linalg.norm(radial, axis=1)
    dirs = radial / r_top[:, None]
    LP = np.concatenate([M.co(ob) for ob in leg_objs])
    rows = []
    r_prev = r_top.copy()
    frontness = np.cos(ang) ** 2 * (np.cos(ang) > 0)
    for i in range(Rn + 1):
        t = i / Rn
        z = z_top + (z_hem - z_top) * t
        flare = o["skirt_flare"] * t ** 1.4 * (1 + 0.3 * np.abs(np.sin(ang)))
        r = r_top + flare
        band = LP[np.abs(LP[:, 2] - z.mean()) < 0.035]
        if len(band):
            rel = np.stack([band[:, 0], band[:, 1] - yc], 1)
            rb = np.linalg.norm(rel, axis=1)
            ab = np.mod(np.arctan2(rel[:, 0], -rel[:, 1]), 2 * math.pi)
            for j in range(N):
                dd = np.abs((ab - ang[j] + math.pi) % (2 * math.pi) - math.pi)
                sel = dd < 0.22
                if sel.any():
                    # close over the hips under the waist seam, more room towards the hem for the legs
                    r[j] = max(r[j], rb[sel].max() + o["skirt_clear"] * (0.35 + 0.65 * M.smoothstep(0.1, 0.6, t)))
        for _ in range(6):
            r = 0.5 * r + 0.25 * (np.roll(r, 1) + np.roll(r, -1))
        r = np.maximum(r, r_prev - 0.004)          # cloth hangs: never tucks in under the buttocks
        r_prev = r.copy()
        # drape folds, deeper at the back and sides and towards the hem
        amp = o["fold_amp"] * M.smoothstep(0.05, 1.0, t) * (1 - 0.65 * frontness)
        folds = amp * (np.sin(ang * o["fold_count"] + 0.7 * np.sin(ang * 3.0)) * 0.7
                       + 0.3 * np.sin(ang * o["fold_count"] * 1.9 + 1.3))
        r = r + folds
        P = np.stack([dirs[:, 0] * r, yc + dirs[:, 1] * r, z], 1)
        if i == 0:
            P = q.copy()
        rows.append(P)
    rows = np.array(rows)                                    # (Rn+1, N, 3)
    splits = {"front": (0.0, Rn + 1), "left": (math.pi / 2, o["side_slit_rows"]),
              "back": (math.pi, o["back_vent_rows"]), "right": (1.5 * math.pi, o["side_slit_rows"])}
    split_col = {}
    for k, (a, nrows) in splits.items():
        d = np.abs((ang - a + math.pi) % (2 * math.pi) - math.pi)
        split_col[k] = (int(np.argmin(d)), nrows)
    verts = [rows[i, j] for i in range(Rn + 1) for j in range(N)]
    vid = lambda i, j: i * N + j
    dup = {}
    for k, (c, nrows) in split_col.items():
        first = max(1, Rn + 1 - nrows)
        for i in range(first, Rn + 1):
            dup[(i, c)] = len(verts)
            verts.append(rows[i, c].copy())
    verts = np.array(verts)
    faces, uvs = [], []
    col_panel = np.zeros(N, int)
    for j in range(N):
        col_panel[j] = int(ang[j] // (math.pi / 2)) % 4
    split_cols = {c for c, _ in split_col.values()}
    seglen_u = np.linalg.norm(np.diff(np.vstack([rows[Rn // 2], rows[Rn // 2][:1]]), axis=0), axis=1)
    ucum = np.r_[0, np.cumsum(seglen_u)]
    vlen = np.linalg.norm(np.diff(rows[:, 0], axis=0), axis=1)
    vcum = np.r_[0, np.cumsum(vlen)]
    # UV panels: the tails' map is cut at the four split columns (front, slits, vent), so it packs as four
    # quarter-width islands instead of one long band
    cs = sorted(split_cols)
    uv_panel = np.array([sum(1 for c in cs if c <= j) % len(cs) for j in range(N)])
    for i in range(Rn):
        for j in range(N):
            j2 = (j + 1) % N
            a, b, c_, d = vid(i, j), vid(i, j2), vid(i + 1, j2), vid(i + 1, j)
            if j in split_cols:
                if (i, j) in dup:
                    a = dup[(i, j)]
                if (i + 1, j) in dup:
                    d = dup[(i + 1, j)]
            faces.append((a, d, c_, b))
            u0, u1 = ucum[j] + 0.05 * uv_panel[j], ucum[j + 1] + 0.05 * uv_panel[j]
            uvs.append([(u0, -vcum[i]), (u0, -vcum[i + 1]), (u1, -vcum[i + 1]), (u1, -vcum[i])])
    for key, (c, nrows) in split_col.items():
        n_out = np.array([dirs[c, 0], dirs[c, 1], 0.0])
        for i in range(max(1, Rn + 1 - nrows), Rn + 1):
            t = i / Rn
            oid = dup[(i, c)]
            if key == "front":
                gap = o["front_gap"] * t ** 1.3 - 0.008      # slight overlap under the belt, parted at the hem
                verts[oid] += n_out * 0.003 + np.array([gap * 0.5, 0, 0])
                verts[vid(i, c)] += np.array([-gap * 0.5, 0, 0])
            else:
                verts[oid] += n_out * 0.0018
    ob = M.make_object("skirt", verts, faces, uvs)
    n = len(verts)
    colj = np.zeros(n, int)
    rowi = np.zeros(n, int)
    for i in range(Rn + 1):
        for j in range(N):
            colj[vid(i, j)] = j
            rowi[vid(i, j)] = i
    for (i, j), k in dup.items():
        colj[k] = j
        rowi[k] = i
    seglen = np.linalg.norm(np.diff(rows, axis=0), axis=2)
    cum = np.vstack([np.zeros((1, N)), np.cumsum(seglen, axis=0)])
    s_m = cum[rowi, colj]
    L = float(cum[-1].mean())
    panel_of = np.array([col_panel[c] for c in colj])
    for (i, j), k in dup.items():
        panel_of[k] = col_panel[(j + 1) % N]
        panel_of[vid(i, j)] = col_panel[(j - 1) % N]
    A = ang[colj]
    chains = {}
    for pi_, (key, center, side) in enumerate(PANELS):
        jc = int(np.argmin(np.abs((ang - center + math.pi) % (2 * math.pi) - math.pi)))
        # chain line: the panel's centre column without the drape folds
        pts = []
        for fr in (0.0, 1 / 3, 2 / 3, 1.0):
            i = int(round(Rn * fr))
            js = [(jc + dj) % N for dj in range(-3, 4)]
            pts.append(rows[i, js].mean(0))
        chains[key] = {"points": pts, "side": side, "col": jc,
                       "names": ["coat_%s_%02d" % (key, k + 1) for k in range(3)]}
    bounds = [0.0, L / 3, 2 * L / 3, L]
    Wtop = {k: v[loop] for k, v in Wc.items()}
    for s_ in "lr":                       # the coat hangs from the pelvis; the tails follow the legs
        for nm in ("thigh_" + s_, "thigh_twist_01_" + s_, "thigh_half_" + s_):
            if nm in Wtop:
                Wtop["pelvis"] = Wtop.get("pelvis", 0) + Wtop.pop(nm)
    Wall = {}
    k_hand = M.smoothstep(0.0, 0.16, s_m)
    for name, w in Wtop.items():
        Wall[name] = w[colj] * (1 - k_hand)
    # Cloth columns (2026-11-09): the tails hang from GRID_COLUMNS chains round the skirt, every 30 degrees from 15
    # (three in each panel, so the front opening, the slits and the vent fall between columns); the animation build
    # simulates them as one cloth grid (Tools/Blender/anim/animlib.py, _step_coat_grid). Each vertex follows the two
    # nearest columns of its own panel, never one across an opening. The four panel chains above stay in the rig,
    # unweighted, so the skeleton keeps every earlier bone where it was.
    columns = {}
    for k in range(GRID_COLUMNS):
        ca = math.radians(15.0 + 30.0 * k)
        jc = int(np.argmin(np.abs((ang - ca + math.pi) % (2 * math.pi) - math.pi)))
        pts = []
        for fr in (0.0, 1 / 3, 2 / 3, 1.0):
            i = int(round(Rn * fr))
            pts.append(rows[i, [(jc + dj) % N for dj in (-1, 0, 1)]].mean(0))
        key = "c%02d" % (k + 1)
        columns[key] = {"points": pts, "angle": ca, "side": "l" if math.sin(ca) > 0 else "r",
                        "names": ["coat_%s_%02d" % (key, j + 1) for j in range(3)]}
    a_deg = np.degrees(A)
    rel = np.mod(a_deg - 90.0 * panel_of + 180.0, 360.0) - 180.0
    u = np.clip((rel - 15.0) / 30.0, 0.0, 2.0)
    i0 = np.minimum(np.floor(u).astype(int), 1)
    fpart = u - i0
    Wcol = np.zeros((n, GRID_COLUMNS))
    rows_idx = np.arange(n)
    Wcol[rows_idx, 3 * panel_of + i0] += 1.0 - fpart
    Wcol[rows_idx, 3 * panel_of + i0 + 1] += fpart
    for k, (key, col) in enumerate(columns.items()):
        Wc_ = R.chain_weights(s_m, bounds, col["names"])
        for nm, w in Wc_.items():
            Wall[nm] = Wall.get(nm, 0) + w * Wcol[:, k] * k_hand
    # Optional thigh weights (tail_thigh_follow, 2026-11-09): the cloth in front of and beside each thigh partly follows
    # it, most in the upper half of the tails and less toward the hem. Off (0.0) since the tails became a simulated
    # cloth, which keeps them over the thighs itself.
    follow_max = o.get("tail_thigh_follow", 0.0)
    if follow_max > 0.0:
        Vv = np.asarray(verts, dtype=float)
        front = M.smoothstep(-0.35, 0.25, np.cos(A))
        prof = M.smoothstep(0.02, 0.12, s_m) * (1.0 - 0.75 * M.smoothstep(0.3, 1.0, s_m / max(L, 1e-6)))
        follow = {}
        for s_ in "lr":
            bone = rig.data.bones["thigh_" + s_]
            hd, tl = np.array(bone.head_local), np.array(bone.tail_local)
            seg_len = float(np.linalg.norm(tl - hd))
            dv = (tl - hd) / seg_len
            tt = np.clip((Vv - hd) @ dv / seg_len, 0.0, 1.0)
            lat = np.linalg.norm((Vv - (hd + np.outer(tt * seg_len, dv)))[:, :2], axis=1)
            follow["thigh_" + s_] = follow_max * np.exp(-(lat / o.get("tail_thigh_reach", 0.12)) ** 2) * front * prof
        tot = follow["thigh_l"] + follow["thigh_r"]
        cap = np.where(tot > follow_max, follow_max / np.maximum(tot, 1e-9), 1.0)
        for k in follow:
            follow[k] = follow[k] * cap
        tot = follow["thigh_l"] + follow["thigh_r"]
        for k in list(Wall):
            Wall[k] = Wall[k] * (1.0 - tot)
        for k, w in follow.items():
            Wall[k] = Wall.get(k, 0) + w
    M.set_weights(ob, M.normalize_limit(Wall, 8))
    G.set_part_attr(ob, "part", COAT_SKIRT)
    sk = np.zeros(n, np.float32)
    sk[:] = s_m / max(L, 1e-6)
    G.set_float_attr(ob, "skirt_t", sk)
    if lining_part is None:
        M.solidify(ob, o["skirt_thickness"], offset=-1.0)
    else:
        ob = _skirt_lining(ob, rowi, yc, o["skirt_thickness"], lining_part)
    return ob, {"chains": chains, "columns": columns, "length": L, "yc": yc}


def _skirt_lining(ob, rowi, yc, thick, lining_part):
    """Sheet v2: the coattails' crimson lining is its own inner layer (faces turned inward, its own UV island,
    so its colour never shares texels with the outer cloth) joined to the outer layer by a narrow turned edge
    along the hem, the slits and the vent (the waist edge stays open inside the coat). The inner layer's vertex
    order matches the outer one, so weights and attributes carry over one to one."""
    P = M.co(ob)
    n = len(P)
    Nv = M.vnormals(ob)
    radial = np.stack([P[:, 0], P[:, 1] - yc, np.zeros(n)], 1)
    if (Nv * radial).sum() < 0:            # make the normals point away from the legs
        Nv = -Nv
    Pin = P - Nv * thick
    ls, lt, lv = M.polys(ob)
    uv = M.loop_uvs(ob)
    faces = [tuple(int(x) for x in lv[s_:s_ + t][::-1]) for s_, t in zip(ls, lt)]
    uvs = [[tuple(map(float, q)) for q in uv[s_:s_ + t][::-1]] for s_, t in zip(ls, lt)]
    # which outer face owns each boundary edge (to turn the edge strip outward)
    edge_face = {}
    for fi, (s_, t) in enumerate(zip(ls, lt)):
        fv = lv[s_:s_ + t]
        for k in range(t):
            e = tuple(sorted((int(fv[k]), int(fv[(k + 1) % t]))))
            edge_face.setdefault(e, []).append(fi)
    cent = np.array([P[lv[s_:s_ + t]].mean(0) for s_, t in zip(ls, lt)])
    verts = list(Pin)
    src = list(range(n))
    for lp in M.boundary_loops(ob):
        closed = np.r_[lp, lp[:1]]
        runs, cur = [], []
        for k in range(len(closed) - 1):           # boundary edges below the waist row form the turned edge
            a, b = int(closed[k]), int(closed[k + 1])
            if rowi[a] == 0 and rowi[b] == 0:
                if cur:
                    runs.append(cur)
                cur = []
                continue
            if not cur:
                cur = [a]
            cur.append(b)
        if cur:
            runs.append(cur)
        for run in runs:
            base = len(verts)
            verts += list(P[run])
            src += list(run)
            seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P[run], axis=0), axis=1))]
            for k in range(len(run) - 1):
                a, b = int(run[k]), int(run[k + 1])
                q = (base + k, base + k + 1, b, a)            # outer copy, outer copy, inner, inner
                # short UV pieces (a new island every 0.3 m) so the strip never limits the atlas packing
                c0 = 0.3 * math.floor(seg[k] / 0.3) - 0.07 * math.floor(seg[k] / 0.3)
                uq = {base + k: (seg[k] - c0, 0.0), base + k + 1: (seg[k + 1] - c0, 0.0), b: (seg[k + 1] - c0, -3 * thick),
                      a: (seg[k] - c0, -3 * thick)}
                nq = np.cross(P[b] - P[a], Pin[a] - P[a])
                fo = edge_face.get(tuple(sorted((a, b))), [None])[0]
                out = 0.5 * (P[a] + P[b]) - (cent[fo] if fo is not None else P.mean(0))
                if np.dot(nq, out) < 0:
                    q = q[::-1]
                faces.append(q)
                uvs.append([uq[x] for x in q])
    lin = M.make_object("skirt_lining", np.array(verts), faces, uvs)
    src = np.array(src)
    W = M.weights(ob)
    M.set_weights(lin, {k: v[src] for k, v in W.items()})
    G.set_float_attr(lin, "skirt_t", G.get_attr(ob, "skirt_t")[src])
    G.set_part_attr(lin, "part", lining_part)
    return M.join([ob, lin], "skirt")


# ----------------------------------------------------------------------------- trousers

def _hem_cut(rig, s, cfg):
    """Slanted trouser hem: rests on the loafer's vamp at the front, longer at the heel."""
    ank = np.array(rig.data.bones["foot_" + s].head_local)
    sole = cfg["sole_m"]
    zf, zb = sole + cfg["outfit"]["hem_front_z"], sole + cfg["outfit"]["hem_back_z"]

    def fn(P):
        mine = (P[:, 0] > 0) if s == "l" else (P[:, 0] < 0)
        k = np.clip((P[:, 1] - (ank[1] - 0.06)) / 0.12, 0, 1)     # 0 front .. 1 back
        zh = zf + (zb - zf) * k
        return np.where(mine, P[:, 2] - zh, 1.0)
    return fn


def _crease_and_break(pants, rig, cfg):
    """Pressed front crease (a ridge on the front centre line of each leg) and a break (fold) where
    the hem rests on the shoe."""
    o = cfg["outfit"]
    P = M.co(pants)
    sole = cfg["sole_m"]
    for s, sg in (("l", 1.0), ("r", -1.0)):
        mine = P[:, 0] * sg > 0.02
        for bone in ("thigh_" + s, "calf_" + s):
            b = rig.data.bones[bone]
            h, t = np.array(b.head_local), np.array(b.tail_local)
            d = (t - h) / np.linalg.norm(t - h)
            tt = ((P - h) @ d) / np.linalg.norm(t - h)
            foot = h + np.outer(tt * np.linalg.norm(t - h), d)
            rad = P - foot
            rn = np.maximum(np.linalg.norm(rad, axis=1), 1e-6)
            fwd = -rad[:, 1] / rn                          # 1 on the front centre line
            on = mine & (tt > (0.25 if bone.startswith("thigh") else -0.02)) & (tt < 1.02)
            ridge = np.exp(-((1 - np.clip(fwd, -1, 1)) / 0.035)) * on
            back = np.exp(-((1 + np.clip(fwd, -1, 1)) / 0.05)) * on * 0.5
            push = o["crease_depth"] * (ridge + back)
            P = P + rad / rn[:, None] * push[:, None]
        ank = np.array(rig.data.bones["foot_" + s].head_local)
        zbk = sole + o["hem_front_z"] + 0.035
        fold = np.exp(-((P[:, 2] - zbk) / 0.012) ** 2) * M.smoothstep(ank[1] + 0.02, ank[1] - 0.04, P[:, 1]) * mine
        c = np.array([ank[0], ank[1], 0])
        rad = P - c
        rad[:, 2] = 0
        rn = np.maximum(np.linalg.norm(rad, axis=1), 1e-6)
        P = P + rad / rn[:, None] * (0.004 * fold)[:, None]
    M.set_co(pants, P)


# ----------------------------------------------------------------------------- loafers

def loafer(body, rig, cfg, s, W, V, boot=False):
    """Penny loafer on a last fitted to the foot: the upper is lofted over the foot's sections (with
    clearance, toe room, rounded toe and heel), opened at the topline round the ankle; a saddle strap
    lies across the vamp; a welted sole with a stacked heel. Weights: foot behind the ball joint,
    ball in front, blended over the flex line."""
    o = cfg["outfit"]
    sole = cfg["sole_m"]
    ank = np.array(rig.data.bones["foot_" + s].head_local)
    ballp = np.array(rig.data.bones["ball_" + s].head_local)
    fwd = ballp - ank
    fwd[2] = 0
    fwd /= np.linalg.norm(fwd)
    outw = np.array([1.0, 0, 0]) if s == "l" else np.array([-1.0, 0, 0])
    outw = outw - fwd * (outw @ fwd)
    outw /= np.linalg.norm(outw)
    side = (V[:, 0] > 0) if s == "l" else (V[:, 0] < 0)
    fw = G.wsum(W, G.side_names(["foot", "ball"], s))
    sel = side & (fw > 0.3) & (V[:, 2] < ank[2] + 0.025)
    Q = V[sel] - np.array([ank[0], ank[1], 0.0])
    qf, qo, qz = Q @ fwd, Q @ outw, V[sel, 2]
    f_heel, f_toe = qf.min(), qf.max()
    f_ball = float((ballp - ank) @ fwd)
    fs = np.linspace(f_heel - o["loafer_heel_room"], f_toe + o["loafer_toe_room"], o["loafer_sections"])
    # section extents of the foot
    lo_o, hi_o, top = np.zeros(len(fs)), np.zeros(len(fs)), np.zeros(len(fs))
    for i, fv in enumerate(fs):
        m = np.abs(qf - np.clip(fv, f_heel + 0.006, f_toe - 0.006)) < 0.009
        lo_o[i], hi_o[i] = qo[m].min(), qo[m].max()
        top[i] = qz[m].max()
    for arr in (lo_o, hi_o, top):
        for _ in range(3):
            arr[1:-1] = 0.5 * arr[1:-1] + 0.25 * (arr[2:] + arr[:-2])
    clear = 0.0042
    cen = 0.5 * (lo_o + hi_o)
    a_foot = 0.5 * (hi_o - lo_o) + clear
    a_foot = np.where(fs > f_toe, 0.0, a_foot)
    # plan: the last tapers over the toes to an almond toe (never inside the foot), rounded heel
    f_t0 = f_toe - o["loafer_toe_taper"]
    i_t0 = int(np.argmin(np.abs(fs - f_t0)))
    a_t0 = a_foot[i_t0]
    tt = np.clip((fs - f_t0) / (fs[-1] - f_t0), 0, 1)
    a_taper = a_t0 * np.maximum(np.clip(1 - tt ** 2, 0, 1) ** 0.55, 0.42)
    a = np.where(fs > f_t0, np.maximum(a_taper, a_foot), a_foot)
    heel_t = np.clip(((f_heel + 0.03) - fs) / ((f_heel + 0.03) - fs[0]), 0, 1)
    a = a * np.sqrt(np.clip(1 - heel_t ** 2.6, 0.0, 1))
    a = np.maximum(a, 0.003)
    i_toe = int(np.argmin(np.abs(fs - f_toe)))
    cen = np.where(fs > f_toe, cen[i_toe], cen)
    z_bot = sole * 0.55 + sole * 0.45 * M.smoothstep(f_ball - 0.01, f_heel + 0.07, fs)
    z_foot = np.where(fs <= f_toe, top + clear + 0.001, 0.0)
    fwd_part = fs > f_ball - 0.02             # forefoot: smooth envelope falling towards the toe
    env = np.maximum.accumulate(z_foot[::-1])[::-1]
    z_foot = np.where(fwd_part, env, z_foot)
    for _ in range(4):
        z_foot[1:-1] = np.maximum(z_foot[1:-1], 0.5 * z_foot[1:-1] + 0.25 * (z_foot[2:] + z_foot[:-2]))
    z_top = np.maximum(z_foot, z_bot + 0.02)
    # toe box profile: slopes down smoothly from the toes' root to a rounded nose ~1.6 cm high
    i_t1 = int(np.argmin(np.abs(fs - (f_toe - 0.045))))
    h0 = z_top[i_t1]
    tz = np.clip((fs - fs[i_t1]) / (fs[-1] - fs[i_t1]), 0, 1)
    nose = z_bot + 0.016
    prof = nose + (h0 - nose) * np.cos(0.5 * math.pi * tz) ** 0.7
    prof = np.where(tz > 0.9, z_bot + (prof - z_bot) * np.sqrt(np.clip(1 - ((tz - 0.9) / 0.1) ** 2, 0.35, 1)), prof)
    z_top = np.where(tz > 0, np.maximum(prof, np.where(fs <= f_toe, z_foot, 0.0)), z_top)
    z_top = np.maximum(z_top, z_bot + 0.004)
    nr = o["loafer_ring"]
    rings = []
    for i in range(len(fs)):
        ring = []
        b = z_top[i] - z_bot[i]
        for k in range(nr):
            ph = 2 * math.pi * k / nr                      # 0 = outer side, pi/2 = top
            c, sn = math.cos(ph), math.sin(ph)
            ex = 2.0 / 2.7
            x = a[i] * np.sign(c) * abs(c) ** ex
            if sn >= 0:
                z = z_bot[i] + 0.006 + (b - 0.006) * abs(sn) ** ex
            else:
                z = z_bot[i] + 0.006 * (1 - abs(sn) ** 0.5)
            p = np.array([ank[0], ank[1], 0.0]) + fwd * fs[i] + outw * (cen[i] + x)
            p[2] = z
            ring.append(p)
        rings.append(ring)
    Pr = np.array(rings)                                      # (sections, ring, 3)
    # close heel and toe with rings shrunk towards their centre (rounded ends, no crease)
    def cap(ring, push, k):
        c = ring.mean(0)
        c[2] = ring[:, 2].min() + 0.5 * np.ptp(ring[:, 2])
        return c + (ring - c) * k + push

    def dome(ring, direction, r):
        return [cap(ring, direction * r * math.sin(t), math.cos(t)) for t in np.radians((35, 62, 84))]
    Pr = np.concatenate([np.array(dome(Pr[0], -fwd, 0.006)[::-1]), Pr, np.array(dome(Pr[-1], fwd, 0.009))], 0)
    upper = _grid("loafer_upper_" + s, Pr, closed_u=True)
    M.subdivide(upper, 1)
    # topline: opening round the ankle in front of the heel counter, behind the vamp

    def topline(P):
        d = P - np.array([ank[0], ank[1], 0.0])
        fp, op = d @ fwd, d @ outw
        f_v = o["loafer_vamp_f"] - 0.03 * np.clip(op / 0.04, -1.2, 1.2) ** 2      # throat: U open to the heel
        z_line = sole + o["loafer_topline_heel"] - o["loafer_topline_dip"] * np.exp(-((fp - 0.0) / 0.035) ** 2) \
            + 0.006 * M.smoothstep(f_v - 0.02, f_v, fp)
        return np.maximum(z_line - P[:, 2], fp - f_v)
    if not boot:                          # a Victorian ankle boot (sheet v2) closes over the instep: no topline
        M.cut_implicit(upper, topline)
    G.drop_small_islands(upper, 20)
    G.keep_largest(upper)
    G.set_part_attr(upper, "part", LOAFER)
    n_upper = len(upper.data.vertices)
    M.add_boundary_lip(upper, 0.003)
    lipf = np.zeros(len(upper.data.vertices), np.float32)
    lipf[n_upper:] = 1
    G.set_float_attr(upper, "lip", lipf)
    # saddle strap across the vamp (loafers only)
    strap = M.duplicate(upper, "loafer_strap_" + s)
    if boot:
        M.delete_verts(strap, np.ones(len(strap.data.vertices), bool))

    def sband(P):
        d = P - np.array([ank[0], ank[1], 0.0])
        fp, op = d @ fwd, d @ outw
        f_v = o["loafer_vamp_f"] - 0.03 * np.clip(op / 0.04, -1.2, 1.2) ** 2
        return np.minimum(0.0135 - np.abs(fp - (f_v + 0.006 + 0.0135)), P[:, 2] - (sole + 0.026))
    Ps = M.co(strap)
    if len(Ps):
        M.delete_verts(strap, np.arange(len(Ps)) >= n_upper)          # drop the turned-under topline lip
        M.cut_implicit(strap, sband)
        G.drop_small_islands(strap, 6)
    if len(strap.data.vertices):
        Ps = M.co(strap)
        Ns = M.vnormals(strap)
        M.set_co(strap, Ps + Ns * 0.0018)
        M.add_boundary_lip(strap, 0.0018)
        G.set_part_attr(strap, "part", LOAFER_STRAP)
    # welted sole with a stacked heel
    sole_ob = _loafer_sole(Pr[1:-1], fs, a, cen, ank, fwd, outw, z_bot, f_heel, s, o)
    pieces = [upper, strap, sole_ob] if len(strap.data.vertices) else [upper, sole_ob]
    if not len(strap.data.vertices):
        bpy.data.objects.remove(strap)
    shoe = M.join(pieces, "loafer_" + s)
    # weights
    P = M.co(shoe)
    fp = (P - np.array([ank[0], ank[1], 0.0])) @ fwd
    wb = M.smoothstep(f_ball - 0.012, f_ball + 0.018, fp)
    M.set_weights(shoe, {"foot_" + s: 1 - wb, "ball_" + s: wb})
    if boot:
        # the boot's shaft: a shell round the ankle and the foot of the shin, under the trouser hem
        side = (V[:, 0] > 0) if s == "l" else (V[:, 0] < 0)
        legw = G.wsum(W, G.side_names(["calf", "calf_twist_01", "foot"], s))
        vm = side & (legw > 0.4) & (V[:, 2] > ank[2] - 0.035) & (V[:, 2] < ank[2] + o["boot_shaft_above_ankle"])
        shaft, _, _ = G.shell(body, vm, "boot_shaft_" + s, 0.0055, None, relax_iters=4, lip=0.0025, edge_smooth=0)
        G.set_part_attr(shaft, "part", LOAFER)
        shoe = M.join([shoe, shaft], "loafer_" + s)
    shoe.data.materials.clear()
    return shoe


def _loafer_sole(Pr, fs, a, cen, ank, fwd, outw, z_bot, f_heel, s, o):
    """Sole: welt ledge round the upper, a straight edge with crisp corners, flat bottom with a slight
    shank arch and toe spring; the heel part is the full stack height."""
    nseg = len(fs)
    base = np.array([ank[0], ank[1], 0.0])
    welt = o["loafer_welt"]
    heel_front = f_heel + o["loafer_heel_len"]
    rings = [[], [], [], []]                 # top, top edge, bottom edge, bottom (each right..left)
    for side_sgn, idx in ((1, range(nseg)), (-1, range(nseg - 1, -1, -1))):
        for i in idx:
            w = a[i] + welt
            p = base + fwd * fs[i] + outw * (cen[i] + side_sgn * w)
            spring = 0.005 * M.smoothstep(0.82, 1.0, i / (nseg - 1)) ** 2
            arch = 0.0035 * M.smoothstep(heel_front - 0.005, heel_front + 0.03, fs[i]) \
                * (1 - M.smoothstep(heel_front + 0.05, heel_front + 0.1, fs[i]))
            zt = z_bot[i] + 0.0015
            zb_ = spring + arch
            inset = -outw * side_sgn * 0.0009
            for k, (z, ins) in enumerate(((zt, 0.0), (zt - 0.0012, 0.25), (zb_ + 0.0012, 0.9), (zb_, 1.4))):
                q = p + inset * ins
                q = q.copy()
                q[2] = z
                rings[k].append(q)
    rings = [np.array(r) for r in rings]
    nring = len(rings[0])
    verts = np.concatenate(rings)
    faces, uvs = [], []
    per = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([rings[0], rings[0][:1]]), axis=0), axis=1))]
    vz = [0.0, -0.0012, -0.01, -0.012]
    for k in range(3):
        for j in range(nring):
            j2 = (j + 1) % nring
            faces.append((k * nring + j, k * nring + j2, (k + 1) * nring + j2, (k + 1) * nring + j))
            uvs.append([(per[j], vz[k]), (per[j + 1], vz[k]), (per[j + 1], vz[k + 1]), (per[j], vz[k + 1])])
    ob = M.make_object("loafer_sole_" + s, verts, faces, uvs)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    top = [bm.verts[i] for i in range(nring)]
    bot = [bm.verts[3 * nring + i] for i in range(nring)]
    ft = bm.faces.new(top[::-1])
    fb = bm.faces.new(bot)
    res = bmesh.ops.triangulate(bm, faces=[ft, fb])
    uvl = bm.loops.layers.uv.active
    for fc in res["faces"]:
        for lp in fc.loops:
            lp[uvl].uv = (lp.vert.co.x * 3.0 + 2.0, lp.vert.co.y * 3.0)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    M.shade_smooth(ob)
    part = np.zeros(len(ob.data.vertices), np.int32)
    part[:] = LOAFER_SOLE
    part[:2 * nring] = LOAFER_WELT
    G.set_part_attr(ob, "part", part)
    return ob


def coat_chains_from_rest(rest):
    """The coat's tail chains as coat_rig expects them, from the shipped rest pose alone. The coat is no
    longer built (2026-11-09 canon), but its chains stay in the rig, unweighted, so the exported
    skeleton keeps every bone in the same place."""
    chains = {}
    for key, _, side in PANELS:
        names = ["coat_%s_%02d" % (key, k + 1) for k in range(3)]
        pts = R.rest_points(rest, names)
        if pts is None:
            raise RuntimeError("rest_chains has no %s chain; the coat chains can only be kept from rest" % key)
        chains[key] = {"names": names, "points": pts, "side": side}
    yc = float(np.mean([chains[k]["points"][0][1] for k in chains]))
    return {"chains": chains, "yc": yc}


def coat_rig(rig, skirt_info, rest=None):
    """Coat tail chains (pelvis children) and thigh-follow helpers (Blender-only, not exported); with
    `rest` the shipped rest pose of the chains and helpers is kept."""
    for key, ch in skirt_info["chains"].items():
        pts = R.rest_points(rest, ch["names"]) or ch["points"]
        out = pts[0] - np.array([0, skirt_info["yc"], pts[0][2]])
        out[2] = 0
        out /= max(np.linalg.norm(out), 1e-6)
        R.add_chain(rig, ch["names"], pts, "pelvis", roll_up=tuple(out), connect=True, rest=rest)
        helper = "helper_coat_" + key
        tail = np.array(pts[1])
        R.add_helper(rig, helper, "thigh_" + ch["side"], tail, tail + np.array([0, 0, -0.05]), rest=rest)
        infl = 1.0 if key.startswith("f") else 0.55
        R.damped_follow(rig, ch["names"][0], helper, infl)
    # The cloth columns: each hangs from the pelvis; in front of the hips the first bone leans after the thigh on its
    # side (fully at the front opening, fading to nothing at the side seams). The back columns hang free: a thigh
    # raised forward would swing them under the seat. The animation build simulates all of them as one grid against
    # the legs.
    for key, ch in skirt_info.get("columns", {}).items():
        out = (math.sin(ch["angle"]), -math.cos(ch["angle"]), 0.0)
        R.add_chain(rig, ch["names"], ch["points"], "pelvis", roll_up=out, connect=True, rest=rest)
        infl = max(0.0, math.cos(ch["angle"]))
        if infl < 0.05:
            continue
        # The helper lies on the column's first bone, extended to twice its length (about mid-thigh): close to the
        # hip joint a raised thigh would lift it above and behind the waist and turn the column backwards.
        helper = "helper_coat_" + key
        p0, p1 = np.array(ch["points"][0]), np.array(ch["points"][1])
        tail = p0 + (p1 - p0) * 2.0
        R.add_helper(rig, helper, "thigh_" + ch["side"], tail, tail + np.array([0, 0, -0.05]), rest=rest)
        R.damped_follow(rig, ch["names"][0], helper, infl)


# ----------------------------------------------------------------------------- sheet v2 (2026-11-09): Victorian ensemble

def _frock_coat(body, rig, cfg, f, collider, under, hide, is_arm, arm_t, hand, Z, neck_cut, leg_objs):
    """Jet-black Victorian frock coat: torso and sleeves grown from the body and draped (fitted at the waist,
    structured shoulders), the fronts meeting at a single waist button and open above it to a high standing
    collar; below the waist seam long split coattails (front opening, side slits, back vent) end just above the
    knee, their inner layer the crimson lining; ornamental silver buttons; a small crimson gemstone brooch on
    the left breast. Piping, embroidery and the ice-white cuff and collar trim are painted (eh_specs)."""
    o = cfg["outfit"]
    zc = f["zc"]
    sleeve_end = o["sleeve_end_t"]
    z_cut = f["z_cut"]
    region = (Z >= z_cut - 0.04) & (Z < neck_cut + 0.012) & ~hand & ~(is_arm & (arm_t > sleeve_end + 0.08))
    t_arm = np.where(is_arm, arm_t, 0.0)
    zb = f["zb"]
    off = np.where(is_arm, 0.010 + 0.005 * M.smoothstep(0.3, 1.0, t_arm),
                   o["coat_offset"] * (1 - 0.45 * np.exp(-((Z - zb) / 0.06) ** 2)))
    off = off + 0.006 * M.smoothstep(zc - 0.06, zc + 0.03, Z) * (~is_arm)       # structured shoulders

    def waist(P):
        return P[:, 2] - z_cut

    def v_open(P):
        return np.maximum.reduce([np.abs(P[:, 0]) - vline(P[:, 2], f, o), f["zvb"] + 0.006 - P[:, 2],
                                  P[:, 1] - G.spine_y(rig, P[:, 2]) + 0.03])

    cuts = (waist, v_open, _limb_cut(rig, "lowerarm_l", sleeve_end), _limb_cut(rig, "lowerarm_r", sleeve_end))
    coat, src, fm = G.shell(body, region, "coat", off, collider, relax_iters=12, relax_factor=0.5,
                            smooth_offset=6, lip=0.0, soft=3, implicit=cuts, edge_smooth=0)
    coat_cover = fm & M.face_mask_from_verts(body, ~(is_arm & (arm_t > sleeve_end - 0.02)), "all")
    _drape_torso(coat, body, rig, f, cfg, collider)
    # keep the coat off the waistcoat and blouse under it
    Pc = M.co(coat)
    Pc, _ = M.Collider(under).push_out(Pc, 0.004)
    M.set_co(coat, Pc)
    for s in "lr":
        _round_sleeve(coat, rig, s, o)
    Wcs = M.weights(coat)
    for s_ in "lr":
        for nm in ("thigh_" + s_, "thigh_twist_01_" + s_, "thigh_half_" + s_):
            if nm in Wcs:
                Wcs["pelvis"] = Wcs.get("pelvis", 0) + Wcs.pop(nm)
    Wcs = M.smooth_weights(Wcs, M.adjacency(coat), 3, 0.5)
    M.set_weights(coat, M.normalize_limit(Wcs, 8))
    Pc = M.co(coat)
    src_c = G.nearest_src(body, Pc)
    part = np.where(is_arm[src_c] & (arm_t[src_c] > sleeve_end - 0.07), COAT_CUFF, COAT_MAIN)
    G.set_part_attr(coat, "part", part.astype(np.int32))
    loops = M.boundary_loops(coat)
    best = None
    for lp in loops:
        q = Pc[lp]
        if np.abs(q[:, 0]).max() < 0.35 and np.abs(q[:, 0].mean()) < 0.05 and len(lp) > 20 and np.ptp(q[:, 2]) < 0.03:
            if best is None or q[:, 2].mean() < Pc[best][:, 2].mean():
                best = lp
    if best is None:
        raise RuntimeError("no waist loop on the coat shell")
    skirt, skirt_info = _skirt(coat, best, rig, cfg, leg_objs, lining_part=COAT_LINING)
    collar_ob = _stand_collar(body, rig, cfg, coat, f)
    buttons = _coat_buttons(coat, f, cfg)
    brooch = _brooch(coat, f, cfg)
    for ob in [collar_ob, buttons, brooch]:
        _weights_from(ob, coat)
    loop_pos = M.co(coat)[best]
    hipm = np.zeros(len(M.co(coat)), bool)
    hipm[best] = True
    n0 = len(coat.data.vertices)
    M.add_boundary_lip(coat, 0.0045, vmask=~hipm)
    lipf = np.zeros(len(coat.data.vertices), np.float32)
    lipf[n0:] = 1
    G.set_float_attr(coat, "lip", lipf)
    # the lip turned in round the front opening shows the lining
    part = G.get_attr(coat, "part").astype(np.int32)
    part[n0:] = np.where(part[n0:] == COAT_MAIN, COAT_LINING, part[n0:])
    G.set_part_attr(coat, "part", part)
    coat = M.join([coat, skirt, collar_ob, buttons, brooch], "coat")
    _weld_points(coat, loop_pos)
    _clear_waist(coat, M.Collider(list(under) + list(leg_objs[:1])), z_cut)
    hide |= G.hidden_face_mask(body, coat_cover, garment=coat, margin_m=0.015)
    return coat, skirt_info


def _clear_waist(coat, col, z_cut, band=0.1):
    """The waistcoat ends at the coat's waist seam and the trousers rise high under it: keep the bodice, the
    tails and their lining clear of both around the seam (a smooth push, then a strict one)."""
    P = M.co(coat)
    part = G.get_attr(coat, "part").astype(np.int32)
    near = np.abs(P[:, 2] - z_cut) < band
    clear = {COAT_MAIN: 0.005, COAT_SKIRT: 0.005, COAT_CUFF: 0.005, COAT_LINING: 0.0015}
    D = np.zeros_like(P)
    sel_all = np.zeros(len(P), bool)
    for pid, d in clear.items():
        sel = near & (part == pid)
        if sel.any():
            Q, _ = col.push_out(P[sel], d)
            D[sel] = Q - P[sel]
            sel_all |= sel
    if not sel_all.any():
        return
    D = M.smooth(D, M.adjacency(coat), 4, 0.5)          # spread the push over a few rings, no creases
    P = P + D
    for pid, d in clear.items():
        sel = near & (part == pid)
        if sel.any():
            P[sel], _ = col.push_out(P[sel], d)
    M.set_co(coat, P)


def _stand_collar(body, rig, cfg, coat, f):
    """High standing collar: a band rising round the back and sides of the neck, ending where the coat's
    fronts open (no fall, no lapels); thickness from a solidify."""
    o = cfg["outfit"]
    zn = f["zn"]
    nb = rig.data.bones["neck_01"]
    axis_y = nb.head_local[1]
    col = M.Collider([body])
    angs = np.linspace(-math.radians(118), math.radians(118), 33)    # 0 = back of the neck (+Y)
    hs = o["stand_collar_height"]
    prof = [(0.0, 0.0), (0.002, 0.35 * hs), (0.004, 0.75 * hs), (0.007, hs), (0.011, hs + 0.002)]
    rows = []
    for dr, dz in prof:
        ring = []
        for a in angs:
            d = np.array([math.sin(a), math.cos(a), 0.0])
            front = 1 - 0.5 * (1 + math.cos(a))
            z = zn - 0.032 + 0.026 * front + dz * (1 - 0.3 * front)
            o_ = np.array([0, axis_y, z])
            r = col.ray(o_ + d * 0.3, -d, 0.35)
            p = np.array(r[0]) if r[0] is not None else o_ + d * 0.06
            ring.append(p + d * (0.018 + dr + 0.006 * front))
        rows.append(ring)
    ob = _grid("stand_collar", np.array(rows)[:, ::-1])
    M.solidify(ob, 0.003, offset=-1.0)
    G.set_part_attr(ob, "part", COAT_COLLAR)
    return ob


def _dome_button(p, nrm, radius, height, part):
    nrm = nrm / np.linalg.norm(nrm)
    a = np.cross(nrm, [0, 0, 1.0])
    if np.linalg.norm(a) < 1e-6:
        a = np.array([1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(nrm, a)
    path = np.array([p + nrm * 0.0004, p + nrm * height * 0.6, p + nrm * height])
    rad = np.array([radius, radius * 0.95, radius * 0.55])
    return M.tube(path, rad, rad, 14, np.repeat(a[None], 3, 0), np.repeat(b[None], 3, 0), cap_start=True, cap_end=True)


def _surface_hit(col, x, z, y0=-0.6):
    r = col.ray(np.array([x, y0, z]), np.array([0, 1.0, 0]), 1.2)
    if r[0] is None:
        return None, None
    nrm = np.array(r[1])
    if nrm[1] > 0:
        nrm = -nrm
    return np.array(r[0]), nrm


def _coat_buttons(coat, f, cfg):
    """Ornamental silver buttons: one at the waist where the fronts meet, two pairs up the open fronts."""
    o = cfg["outfit"]
    col = M.Collider([coat])
    pts = [(0.012, f["zvb"] + 0.014)]
    for dz in (0.075, 0.15):
        z = f["zvb"] + dz
        hw = float(vline(np.array([z]), f, o)[0])
        pts += [(hw + 0.024, z), (-(hw + 0.024), z)]
    parts = []
    for x, z in pts:
        p, nrm = _surface_hit(col, x, z)
        if p is not None:
            parts.append(_dome_button(p, nrm, 0.0085, 0.0055, COAT_BUTTON))
    V, F, U, _ = M.merge_parts(parts)
    ob = M.make_object("coat_buttons", V, F, U)
    G.set_part_attr(ob, "part", COAT_BUTTON)
    return ob


def _brooch(coat, f, cfg):
    """A small crimson gemstone in a silver setting on the coat's left breast."""
    o = cfg["outfit"]
    col = M.Collider([coat])
    z = f["zc"] - 0.06
    x = float(vline(np.array([z]), f, o)[0]) + 0.035
    p, nrm = _surface_hit(col, x, z)
    if p is None:
        p, nrm = np.array([x, -0.1, z]), np.array([0, -1.0, 0])
    setting = _dome_button(p, nrm, 0.0085, 0.0028, GEM_SETTING)
    gem = _dome_button(p + nrm * 0.0022, nrm, 0.0058, 0.0042, GEM)
    s_ob = M.make_object("brooch_setting", *M.merge_parts([setting])[:3])
    G.set_part_attr(s_ob, "part", GEM_SETTING)
    g_ob = M.make_object("brooch_gem", *M.merge_parts([gem])[:3])
    G.set_part_attr(g_ob, "part", GEM)
    return M.join([s_ob, g_ob], "brooch")


def _waistcoat(body, rig, cfg, f, collider, blouse, zwf, hide, is_arm, hand, headw, Z, neck_cut):
    """Fitted jet-black brocade waistcoat over the blouse: sleeveless, a V neckline showing the blouse's pleats
    and the cravat, a front hem with two points over the trousers' high waistband, a row of polished silver
    buttons and a slender silver chain from the middle button to the left pocket."""
    o = cfg["outfit"]
    zc = f["zc"]
    z_vb = zc - o["waistcoat_v_bottom_below_clav"]
    z_hem = zwf - o["waistcoat_hem_below_waist"]
    z_top = zc + 0.05
    region = (Z >= z_hem - 0.05) & (Z < neck_cut) & ~hand & (headw < 0.3) & ~is_arm

    def hem(P):
        ff = 1 - M.smoothstep(-0.03, 0.03, P[:, 1] - G.spine_y(rig, P[:, 2]))
        pts = 0.028 * np.exp(-((np.abs(P[:, 0]) - 0.045) / 0.028) ** 2) * ff
        return P[:, 2] - (z_hem - pts)

    def v_neck(P):
        hw = o["waistcoat_v_halfwidth"] * np.clip((P[:, 2] - z_vb) / (z_top - z_vb), 0, 1) ** 0.9
        return np.maximum.reduce([np.abs(P[:, 0]) - hw, z_vb - P[:, 2], P[:, 1] - G.spine_y(rig, P[:, 2]) + 0.03])

    def back_neck(P):
        back = P[:, 1] > G.spine_y(rig, P[:, 2])
        return np.where(back, (neck_cut.min() if np.ndim(neck_cut) else neck_cut) - 0.03 - P[:, 2], 1.0)

    def armhole(P):
        out_ = np.full(len(P), 1.0)
        for s_ in "lr":
            b = rig.data.bones["upperarm_" + s_]
            h = np.array(b.head_local)
            d = np.linalg.norm(P - h, axis=1)
            out_ = np.minimum(out_, d - 0.075)
        return out_

    off = np.full(len(Z), o["waistcoat_offset"])
    wc, src, fm = G.shell(body, region, "waistcoat", off, collider, relax_iters=10, relax_factor=0.5,
                          smooth_offset=6, lip=0.0, soft=3, implicit=(hem, v_neck, back_neck, armhole), edge_smooth=0)
    P = M.co(wc)
    P = M.smooth(P, M.adjacency(wc), 6, 0.5, fixed=M.boundary_vmask(wc))
    P, _ = M.Collider([blouse]).push_out(P, 0.003)
    M.set_co(wc, P)
    Ww = M.weights(wc)
    for s_ in "lr":
        for nm in ("thigh_" + s_, "thigh_twist_01_" + s_, "thigh_half_" + s_):
            if nm in Ww:
                Ww["pelvis"] = Ww.get("pelvis", 0) + Ww.pop(nm)
    M.set_weights(wc, M.normalize_limit(M.smooth_weights(Ww, M.adjacency(wc), 3, 0.5), 8))
    _tags(wc, WAISTCOAT)
    n0 = len(wc.data.vertices)
    M.add_boundary_lip(wc, 0.0035)
    col = M.Collider([wc])
    parts, btn = [], []
    zs = np.linspace(z_vb - 0.018, z_hem + 0.03, 6)
    for z in zs:
        p, nrm = _surface_hit(col, 0.0, z)
        if p is not None:
            parts.append(_dome_button(p, nrm, 0.0055, 0.004, WAISTCOAT_BUTTON))
            btn.append((p, nrm))
    bo = M.make_object("waistcoat_buttons", *M.merge_parts(parts)[:3])
    G.set_part_attr(bo, "part", WAISTCOAT_BUTTON)
    # chain: from the third button, sagging, to a pocket on her left
    if len(btn) >= 3:
        p0, n0_ = btn[2]
        end_z = z_hem + 0.045
        p1, n1 = _surface_hit(col, 0.085, end_z)
        if p1 is not None:
            ts = np.linspace(0, 1, 24)
            path = []
            for t in ts:
                x = 0.085 * t
                z = p0[2] + (end_z - p0[2]) * t - 0.03 * math.sin(math.pi * t)
                hp, hn = _surface_hit(col, x, z)
                path.append((hp + hn * 0.003) if hp is not None else p0 * (1 - t) + p1 * t)
            path = np.array(path)
            T_ = np.gradient(path, axis=0)
            T_ /= np.linalg.norm(T_, axis=1, keepdims=True)
            A_ = np.cross(T_, [0, -1.0, 0])
            A_ /= np.maximum(np.linalg.norm(A_, axis=1, keepdims=True), 1e-6)
            B_ = np.cross(T_, A_)
            cv, cf, cu = M.tube(path, np.full(len(path), 0.0011), np.full(len(path), 0.0011), 6, A_, B_, cap_start=True, cap_end=True)
            co = M.make_object("waistcoat_chain", cv, cf, cu)
            G.set_part_attr(co, "part", CHAIN)
            bo = M.join([bo, co], "waistcoat_hardware")
    _weights_from(bo, wc)
    return M.join([wc, bo], "waistcoat")


def _blouse_collar(body, rig, cfg):
    """The blouse's high band collar: rises up the neck all round, meeting under the cravat's knot."""
    o = cfg["outfit"]
    zn = rig.data.bones["neck_01"].head_local[2]
    yn = rig.data.bones["neck_01"].head_local[1]
    col = M.Collider([body])
    hc = o["blouse_collar_height"]
    angs = np.radians(np.linspace(-170, 170, 41))          # 0 = back (+Y)
    prof = [(0.0, 0.0), (0.0015, 0.4 * hc), (0.002, 0.8 * hc), (0.004, hc), (0.0065, hc - 0.0015)]
    rows = []
    for dr, dz in prof:
        ring = []
        for a in angs:
            d = np.array([np.sin(a), np.cos(a), 0.0])
            front = 0.5 * (1 - np.cos(a))
            z = zn - 0.03 + 0.016 * front + dz * (1 - 0.2 * front)
            o_ = np.array([0, yn, z])
            r = col.ray(o_ + d * 0.25, -d, 0.3)
            p = np.array(r[0]) if r[0] is not None else o_ + d * 0.055
            ring.append(p + d * (0.004 + dr))
        rows.append(ring)
    ob = _grid("blouse_collar", np.array(rows)[:, ::-1])
    M.solidify(ob, 0.0022, offset=-1.0)
    G.set_part_attr(ob, "part", SHIRT_COLLAR)
    return ob


def cravat(rig, cfg, blouse, f):
    """Crimson silk cravat: a full knot at the throat over the blouse collar, a wide puffed front falling
    inside the waistcoat's V, and a small dark-silver ornamental clasp at the knot."""
    o = cfg["outfit"]
    zn = f["zn"]
    col = M.Collider([blouse])

    last = [None]

    def front_y(z, x=0.0):
        # the blouse's front at height z; where the ray misses (above the collar's front), the last hit
        r = col.ray(np.array([x, -0.5, z]), np.array([0, 1.0, 0]), 1.0)
        if r[0] is not None:
            last[0] = r[0][1]
            return r[0][1]
        if last[0] is None:
            for dz in np.linspace(0.005, 0.08, 16):
                r2 = col.ray(np.array([x, -0.5, z - dz]), np.array([0, 1.0, 0]), 1.0)
                if r2[0] is not None:
                    last[0] = r2[0][1]
                    break
        return last[0] if last[0] is not None else -0.1

    z_knot = zn - 0.03
    kh = 0.045
    zs_k = np.linspace(z_knot + kh * 0.45, z_knot - kh * 0.55, 9)
    y_knot = front_y(z_knot) - 0.002        # one depth for the whole knot (its top would hit the stand collar)
    path, ra, rb, ax, ay = [], [], [], [], []
    for i, z in enumerate(zs_k):
        t = i / (len(zs_k) - 1)
        # closes over at the top; the bottom stays full, where the front comes out of it
        round_ = (math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2)) * 0.8 + 0.2) if t < 0.5 else 1.0 - 0.25 * (2 * t - 1) ** 2
        dep = 0.018 + 0.008 * math.sin(math.pi * t)
        path.append((0.0, y_knot - dep * 0.5, z))
        ra.append((0.025 - 0.006 * t) * round_)
        rb.append(dep * 0.5 * max(round_, 0.55))
        ax.append((1.0, 0.0, 0.0))
        ay.append((0.0, -1.0, 0.0))
    kv, kf, ku = M.tube(np.array(path), np.array(ra), np.array(rb), 18, np.array(ax), np.array(ay),
                        cap_start=True, cap_end=True)
    knot = M.make_object("cravat_knot", kv, kf, ku)
    G.set_part_attr(knot, "part", TIE_KNOT)
    # puffed front: widens below the knot and ends rounded, laid over the blouse
    z_top = zs_k[len(zs_k) // 2]                  # starts inside the knot's widest part
    z_end = z_top - o["cravat_length"]
    n = 22
    zs = np.linspace(z_top, z_end, n)
    yb = np.array([front_y(z) for z in zs]) - 0.004
    cols = np.linspace(-1, 1, 9)
    P = np.zeros((n, len(cols), 3))
    for i, z in enumerate(zs):
        t = i / (n - 1)
        # an ascot: broad from just under the knot, full in the middle, ending in a rounded edge (not a point)
        hw = 0.013 + (o["cravat_width"] / 2 - 0.013) * math.sin(min(t * 1.8, 1.0) * math.pi / 2)
        hw *= 1 - 0.22 * M.smoothstep(0.8, 1.0, t)
        for j, c in enumerate(cols):
            puff = (0.012 * (1 - c * c) ** 0.8 * math.sin(math.pi * min(t * 1.1, 1.0))
                    + 0.0022 * math.sin(c * 5.0 + t * 6.5) * (0.4 + 0.6 * t))           # soft diagonal folds
            P[i, j] = (c * hw, yb[i] - puff, z - 0.01 * M.smoothstep(0.75, 1.0, t) * math.sqrt(max(0.0, 1 - c * c)))
    front = _grid("cravat_front", P)
    M.solidify(front, 0.003, offset=-1.0)
    G.set_part_attr(front, "part", TIE)
    # clasp just under the knot
    zc_ = zs_k[-1] - 0.012
    hit = M.Collider([front]).ray(np.array([0.0, -0.5, zc_]), np.array([0, 1.0, 0]), 1.0)[0]
    p = np.array(hit) - np.array([0.0, 0.001, 0.0]) if hit is not None else np.array([0.0, front_y(zc_) - 0.02, zc_])
    cv, cf, cu = _dome_button(p, np.array([0, -1.0, 0]), 0.0085, 0.004, CRAVAT_CLASP)
    clasp = M.make_object("cravat_clasp", cv, cf, cu)
    G.set_part_attr(clasp, "part", CRAVAT_CLASP)
    return M.join([front, knot, clasp], "cravat")
