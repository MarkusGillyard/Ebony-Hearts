"""Ashka Rook's canon outfit (character sheet of 2026-11-09): white long-sleeved shirt, black tie, black
trousers and brown penny loafers. The shirt is a full shell over torso and arms, gently draped (it falls
from the bust and blouses a little above the waistband) and tucked into the trousers, with a collar,
cuffs and a tie that hangs to the waistband.

The long black trench coat of the earlier sheet is no longer canon and is not built; its builders below
(drape, skirt, lapels, collar, belt, buttons, cuff straps) are kept for reference only. Its tail chains
stay in the rig, unweighted, so the shipped skeleton is unchanged (coat_chains_from_rest).

Coat (former): torso and sleeves are a shell grown from the body (inheriting skin weights) and then draped:
every horizontal slice is pushed out to a hanging envelope of the body (cloth falls from the bust
and shoulder blades instead of shrink-wrapping the waist) and the sleeves are rounded towards a
tube. A double-breasted front closes from the belt to the V, where real lapels (roll, notch,
thickness) and a two-part collar (stand + fall) open onto shirt and tie. Below the hip a lofted
skirt hangs almost straight with drape folds, split into four panels (front opening, two side vents
and a back vent), each skinned to its own 3-bone chain. Belt with knot and tails, buttons, cuff
straps, hems with thickness.
Shirt collar with stand and points, cuffs at the wrists, a four-in-hand knot and a tapered blade that
hangs from the knot. Trousers fall straight with a front crease and a break over
the shoe. Loafers are built on a last fitted to the foot: upper with a vamp, saddle strap and heel
counter, a welt and a sole with a stacked heel."""
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

PANELS = (("fl", math.pi * 0.25, "l"), ("bl", math.pi * 0.75, "l"),
          ("br", math.pi * 1.25, "r"), ("fr", math.pi * 1.75, "r"))


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

    # ------------------------------------------------------------------ waistline (trousers' top edge)
    zw = np.where(front, zp + 0.045, zp + 0.06)
    zw_front = zp + 0.045

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
    _settle_shirt(shirt, rig, collider_body, zp, o)
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
    scollar = _shirt_collar(body, rig, cfg)
    _weights_from(scollar, shirt)
    shirt = M.join([shirt] + cuffs + [scollar], "shirt")
    out["shirt"] = shirt
    tie_ob = tie(rig, cfg, shirt, f)
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
        # a clean waistline (front 4.5 cm, back 6 cm above the pelvis joint, blended round the sides)
        ff = 1 - M.smoothstep(-0.03, 0.03, P[:, 1] - G.spine_y(rig, P[:, 2]))
        return zp + 0.06 - 0.015 * ff - P[:, 2]

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
        lo = loafer(body, rig, cfg, s, W, V)
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

    out["_info"] = info
    return out, hide, None


# ----------------------------------------------------------------------------- helpers

def _settle_shirt(shirt, rig, collider, zp, o):
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
    zw = zp + 0.06 - 0.015 * ff
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

def _skirt(coat, loop, rig, cfg, leg_objs):
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
                    r[j] = max(r[j], rb[sel].max() + o["skirt_clear"])
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
            u0, u1 = ucum[j], ucum[j + 1]
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
    centers = np.array([p[1] for p in PANELS])
    Wp = np.maximum(np.cos(A[:, None] - centers[None, :]), 0) ** 2
    Wp /= Wp.sum(1, keepdims=True)
    hard = np.zeros((n, 4))
    hard[np.arange(n), panel_of] = 1
    slit_depth = np.zeros(n)
    for c, nr in split_col.values():
        top_row = max(1, Rn + 1 - nr)
        dcol = np.minimum(np.abs(colj - c), N - np.abs(colj - c))
        near = np.exp(-(dcol / 2.5) ** 2) * M.smoothstep(top_row - 2.0, top_row + 0.5, rowi)
        slit_depth = np.maximum(slit_depth, near)
    Wpanel = Wp * (1 - slit_depth[:, None]) + hard * slit_depth[:, None]
    Wpanel /= Wpanel.sum(1, keepdims=True)
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
    for pi_, (key, center, side) in enumerate(PANELS):
        Wc_ = R.chain_weights(s_m, bounds, chains[key]["names"])
        for nm, w in Wc_.items():
            Wall[nm] = Wall.get(nm, 0) + w * Wpanel[:, pi_] * k_hand
    M.set_weights(ob, M.normalize_limit(Wall, 8))
    G.set_part_attr(ob, "part", COAT_SKIRT)
    sk = np.zeros(n, np.float32)
    sk[:] = s_m / max(L, 1e-6)
    G.set_float_attr(ob, "skirt_t", sk)
    M.solidify(ob, o["skirt_thickness"], offset=-1.0)
    return ob, {"chains": chains, "length": L, "yc": yc}


# ----------------------------------------------------------------------------- lapels / collar / belt

def _lapels(coat, rig, f, cfg):
    """Notched lapels: each folds out from the V edge (roll line) and lies on the chest, widest below
    the collar, with a notch under the collar's end; a little roll lift near the roll line; real
    thickness from a solidify with rim."""
    o = cfg["outfit"]
    col = M.Collider([coat])
    parts = []
    n, nw = 22, 5
    z0, z1 = f["zvb"] - 0.004, f["z_vtop"] - 0.012
    zs = np.linspace(z0, z1, n)
    t = (zs - z0) / (z1 - z0)
    for sg in (1.0, -1.0):
        e, nn = [], []
        for z in zs:
            x = sg * (float(vline(np.array([z]), f, o)[0]) + 0.002)
            r = col.ray(np.array([x, -0.6, z]), np.array([0, 1.0, 0]), 1.2)
            if r[0] is None:
                loc, nrm, _ = col.nearest(np.array([[x, -0.1, z]]))
                e.append(loc[0])
                nn.append(nrm[0])
            else:
                e.append(np.array(r[0]))
                nn.append(np.array(r[1]))
        e, nn = np.array(e), np.array(nn)
        nn /= np.linalg.norm(nn, axis=1, keepdims=True)
        for _ in range(2):
            nn[1:-1] = 0.5 * nn[1:-1] + 0.25 * (nn[2:] + nn[:-2])
            nn /= np.linalg.norm(nn, axis=1, keepdims=True)
        # outline: grows to the widest point, runs straight up, then the notch steps in
        wmax = o["lapel_width"]
        width = wmax * np.clip(t / 0.62, 0, 1) ** 0.85
        notch = M.smoothstep(0.84, 0.9, t)
        width = width * (1 - 0.45 * notch) * (1 - 0.35 * M.smoothstep(0.93, 1.0, t))
        lat = np.array([sg, 0.0, 0.0])
        out_dir = lat - nn * (nn @ lat)[:, None]
        out_dir /= np.linalg.norm(out_dir, axis=1, keepdims=True)
        rows = []
        for k in range(nw):
            fw = k / (nw - 1)
            lift = 0.0035 + o["lapel_roll"] * (1 - fw) ** 2 * (0.3 + 0.7 * t)
            p = e + out_dir * (width * fw)[:, None] + nn * lift[:, None]
            # settle onto the coat surface away from the roll line
            if k:
                hit = col.nearest(p)[0]
                p = p * (1 - fw * 0.6) + (hit + nn * 0.0038) * (fw * 0.6)
            rows.append(p)
        P = np.stack(rows, 1)                       # (n, nw, 3)
        if sg < 0:
            P = P[:, ::-1]
        g = _grid("lapel", P)
        parts.append(g)
    ob = M.join(parts, "lapels")
    M.solidify(ob, 0.0034, offset=-1.0)
    G.set_part_attr(ob, "part", COAT_LAPEL)
    return ob


def _collar(body, rig, cfg, coat, f):
    """Coat collar: a stand round the back of the neck and a fall folded down over it (two layers,
    so the edge shows its thickness), ending at the lapels' notches."""
    o = cfg["outfit"]
    zn = f["zn"]
    nb = rig.data.bones["neck_01"]
    axis_y = nb.head_local[1]
    col = M.Collider([body])
    colc = M.Collider([coat])
    a_end = math.radians(o["collar_end_deg"])
    angs = np.linspace(-a_end, a_end, 31)                     # 0 = back of the neck (+Y)
    hs, hf = o["collar_height"], o["collar_fall"]
    prof = [(0.0, 0.0), (0.004, 0.45 * hs), (0.006, hs), (0.012, hs + 0.006), (0.02, hs - 0.25 * hf),
            (0.03, hs - hf)]
    rows = []
    for (dr, dz) in prof:
        ring = []
        for a in angs:
            d = np.array([math.sin(a), math.cos(a), 0.0])
            front = 1 - 0.5 * (1 + math.cos(a))               # 0 back .. 1 front
            z = zn - 0.025 + 0.03 * front + dz * (1 - 0.25 * front)
            o_ = np.array([0, axis_y, z])
            r = col.ray(o_ + d * 0.3, -d, 0.35)
            p = np.array(r[0]) if r[0] is not None else o_ + d * 0.06
            ring.append(p + d * (0.016 + dr + 0.01 * front))
        rows.append(ring)
    P = np.array(rows)
    # the fall's lower edge spreads onto the coat's shoulders and lapels
    for j in range(P.shape[1]):
        low = P[-1, j]
        hit = colc.nearest(low[None])[0][0]
        if np.linalg.norm(low - hit) < 0.02:
            P[-1, j] = hit + (low - hit) / max(np.linalg.norm(low - hit), 1e-6) * 0.004
    ob = _grid("collar", P[:, ::-1])
    M.solidify(ob, 0.003, offset=-1.0)
    G.set_part_attr(ob, "part", COAT_COLLAR)
    return ob


def _shirt_collar(body, rig, cfg):
    """Shirt collar: a band round the neck (open at the front for the knot) and a fall with two
    pointed tips that spread onto the shirt front beside the tie knot."""
    zn = rig.data.bones["neck_01"].head_local[2]
    yn = rig.data.bones["neck_01"].head_local[1]
    col = M.Collider([body])
    angs = np.radians(np.linspace(-162, 162, 37))          # 0 = back (+Y)
    prof = [(0.0, 0.0), (0.002, 0.018), (0.003, 0.033), (0.008, 0.036), (0.012, 0.02), (0.016, 0.006)]
    rows = []
    for dr, dz in prof:
        ring = []
        for a in angs:
            d = np.array([np.sin(a), np.cos(a), 0.0])
            front = 0.5 * (1 - np.cos(a))
            z = zn - 0.034 + 0.018 * front + dz * (1 - 0.15 * front)
            o_ = np.array([0, yn, z])
            r = col.ray(o_ + d * 0.25, -d, 0.3)
            p = np.array(r[0]) if r[0] is not None else o_ + d * 0.055
            ring.append(p + d * (0.0045 + dr))
        rows.append(ring)
    P = np.array(rows)
    # collar points: the fall's front ends extend down and out over the shirt front
    for j0, sg in ((0, -1.0), (len(angs) - 1, 1.0)):
        for k, j in enumerate((j0, j0 + int(sg) * -1, j0 + int(sg) * -2)):
            w = (1.0, 0.55, 0.2)[k]
            P[-1, j] += np.array([sg * 0.012, -0.01, -0.036]) * w
            P[-2, j] += np.array([sg * 0.006, -0.006, -0.018]) * w
    ob = _grid("shirt_collar", P[:, ::-1])
    M.solidify(ob, 0.0022, offset=-1.0)
    G.set_part_attr(ob, "part", SHIRT_COLLAR)
    return ob


def _belt(coat, rig, cfg, skirt=None):
    o = cfg["outfit"]
    zp = rig.data.bones["pelvis"].head_local[2]
    zb = zp + o["belt_above_pelvis"]
    col = M.Collider([coat])
    yc = G.spine_y(rig, np.array([zb]))[0] - 0.01
    n = 64
    angs = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rows = []
    for dz in (-o["belt_height"] / 2, 0.0, o["belt_height"] / 2):
        ring = []
        for a in angs:
            d = np.array([math.sin(a), -math.cos(a), 0.0])
            org = np.array([0, yc, zb + dz])
            r = col.ray(org + d * 0.5, -d, 0.6)
            p = np.array(r[0]) if r[0] is not None else org + d * 0.15
            ring.append(p + d * 0.0035)
        rows.append(ring)
    rows = np.array(rows)
    rows[1] += (rows[1] - np.array([0, yc, zb])) * np.array([1, 1, 0]) * 0.012   # slightly domed
    ob = _grid("belt", rows, closed_u=True)
    M.solidify(ob, 0.003, offset=-1.0)
    G.set_part_attr(ob, "part", COAT_BELT)
    # tied knot and two hanging tails, front-left of centre
    col = M.Collider([coat] + ([skirt] if skirt is not None else []))
    kx = o["belt_knot_x"]
    r = col.ray(np.array([kx, -0.6, zb]), np.array([0, 1.0, 0]), 1.2)
    ky = (r[0][1] if r[0] is not None else yc - 0.12) - 0.012
    knot_v, knot_f, knot_u = M.tube(np.array([[kx - 0.02, ky, zb], [kx, ky - 0.004, zb], [kx + 0.02, ky, zb]]),
                                   np.full(3, 0.018), np.array([0.011, 0.013, 0.011]), 10,
                                   np.array([[0, 0, 1.0]] * 3), np.array([[0, -1.0, 0]] * 3), cap_start=True,
                                   cap_end=True)
    parts = [(knot_v, knot_f, knot_u)]
    for dx, length, ang in ((-0.008, 0.21, 0.08), (0.014, 0.17, -0.2)):
        pts = []
        for t in np.linspace(0, 1, 9):
            z = zb - 0.012 - length * t
            x = kx + dx + np.sin(ang) * length * t
            rr = col.ray(np.array([x, -0.6, z]), np.array([0, 1.0, 0]), 1.2)
            y = (rr[0][1] if rr[0] is not None else ky) - 0.007 - 0.004 * (1 - t)
            pts.append((x, y, z))
        pts = np.array(pts)
        hw = o["belt_height"] * 0.45
        tv, tf, tu = [], [], []
        for k, p in enumerate(pts):
            tv += [p + np.array([-hw, 0, 0]), p + np.array([0, -0.0015, 0]), p + np.array([hw, 0, 0])]
        for k in range(len(pts) - 1):
            a = 3 * k
            tf += [(a, a + 1, a + 4, a + 3), (a + 1, a + 2, a + 5, a + 4)]
            tu += [[(0, k / 8), (0.5, k / 8), (0.5, (k + 1) / 8), (0, (k + 1) / 8)],
                   [(0.5, k / 8), (1, k / 8), (1, (k + 1) / 8), (0.5, (k + 1) / 8)]]
        tip = len(tv)
        last = 3 * (len(pts) - 1)
        tv.append(pts[-1] + np.array([0, 0, -0.028]))
        tf += [(last, last + 1, tip), (last + 1, last + 2, tip)]
        tu += [[(0, 1), (0.5, 1), (0.5, 1.1)], [(0.5, 1), (1, 1), (0.5, 1.1)]]
        parts.append((np.array(tv), tf, tu))
    V, F, U, _ = M.merge_parts(parts)
    tails = M.make_object("belt_tie", V, F, U)
    M.solidify(tails, 0.003, offset=-1.0)
    G.set_part_attr(tails, "part", COAT_BELT)
    return M.join([ob, tails], "belt")


def _buttons(coat, rig, f, cfg):
    """Double-breasted front: a pair of horn buttons under the V, one pair above the belt."""
    o = cfg["outfit"]
    col = M.Collider([coat])
    parts = []
    zs = [f["zvb"] - 0.03]
    for z in zs:
        for x in (o["button_x"], -o["button_x"]):
            r = col.ray(np.array([x, -0.6, z]), np.array([0, 1.0, 0]), 1.2)
            if r[0] is None:
                continue
            p, nrm = np.array(r[0]), -np.array(r[1]) if np.array(r[1])[1] > 0 else np.array(r[1])
            nrm = nrm / np.linalg.norm(nrm)
            a = np.cross(nrm, [0, 0, 1.0])
            a /= np.linalg.norm(a)
            b = np.cross(nrm, a)
            path = np.array([p + nrm * 0.0005, p + nrm * 0.0035, p + nrm * 0.0048])
            rad = np.array([0.0105, 0.0105, 0.008])
            v, fc, uv = M.tube(path, rad, rad, 12, np.repeat(a[None], 3, 0), np.repeat(b[None], 3, 0),
                               cap_start=True, cap_end=True)
            parts.append((v, fc, uv))
    V, F, U, _ = M.merge_parts(parts)
    ob = M.make_object("buttons", V, F, U)
    G.set_part_attr(ob, "part", COAT_BUTTON)
    return ob


def _cuff_strap(coat, rig, s, o):
    """Trench cuff strap round the sleeve a little above its end (a raised band with an edge)."""
    b = rig.data.bones["lowerarm_" + s]
    h, t = np.array(b.head_local), np.array(b.tail_local)
    d = (t - h) / np.linalg.norm(t - h)
    c = h + (t - h) * (o["sleeve_end_t"] - 0.2)
    g = M.duplicate(coat, "strap_" + s)
    P = M.co(g)
    side = (P[:, 0] > 0) if s == "l" else (P[:, 0] < 0)
    M.delete_verts(g, ~side | (np.abs((P - c) @ d) > 0.04))
    wdt = 0.026

    def slab(Q):
        along = (Q - c) @ d
        foot = c + np.outer(along, d)
        return np.minimum(wdt / 2 - np.abs(along), 0.14 - np.linalg.norm(Q - foot, axis=1))
    M.cut_implicit(g, slab)
    G.drop_small_islands(g, 8)
    P = M.co(g)
    along = (P - c) @ d
    foot = c + np.outer(along, d)
    rad = P - foot
    P = P + rad / np.maximum(np.linalg.norm(rad, axis=1), 1e-6)[:, None] * 0.003
    M.set_co(g, P)
    M.add_boundary_lip(g, 0.0025)
    for a in list(g.data.attributes):
        if a.name in ("lip", "skirt_t"):
            g.data.attributes.remove(a)
    G.set_part_attr(g, "part", COAT_CUFF)
    return g


# ----------------------------------------------------------------------------- tie

def tie(rig, cfg, shirt, f):
    """Four-in-hand knot under the collar and a blade that hangs from it (over the bust it bridges
    instead of following the body), tapering to the wide end with a pointed tip at the waistband."""
    o = cfg["outfit"]
    zn = f["zn"]
    col = M.Collider([shirt])

    def front_y(z, x=0.0):
        r = col.ray(np.array([x, -0.5, z]), np.array([0, 1.0, 0]), 1.0)
        return r[0][1] if r[0] is not None else -0.1

    z_knot = zn - 0.036
    kh = 0.048
    zs_k = np.linspace(z_knot + kh * 0.45, z_knot - kh * 0.55, 6)
    rings = []
    for i, z in enumerate(zs_k):
        t = i / (len(zs_k) - 1)
        hw = 0.02 - 0.012 * t ** 1.3
        dep = 0.011 + 0.006 * math.sin(math.pi * t)
        yb = front_y(z) - 0.002
        ring = []
        for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
            c, s_ = math.cos(a), math.sin(a)
            x = hw * np.sign(c) * abs(c) ** 0.8
            y = yb - dep * 0.5 - dep * 0.5 * np.sign(s_) * abs(s_) ** 0.8
            if s_ < 0 and abs(x) < hw * 0.35:
                y -= 0.0012 * (1 - abs(x) / (hw * 0.35)) * math.sin(math.pi * t)    # the dimple
            ring.append((x, y, z))
        rings.append(ring)
    K = np.array(rings)
    knot = _grid("tie_knot", K, closed_u=True)
    G.set_part_attr(knot, "part", TIE_KNOT)
    # blade
    z_top = zs_k[-1] + 0.006
    z_tip = f["zp"] + o["tie_tip_above_pelvis"]
    n = 30
    zs = np.linspace(z_top, z_tip, n)
    yb = np.array([front_y(z) for z in zs]) - 0.0035
    hang = yb.copy()
    for i in range(1, n):                     # hangs from the highest forward point (limited slope)
        hang[i] = min(yb[i], hang[i - 1] + 0.12 * (zs[i - 1] - zs[i]))
    settle = M.smoothstep(z_tip + 0.09, z_tip + 0.01, zs)        # the wide end settles onto the shirt
    hang = hang + (yb - hang) * settle * o["tie_settle"]
    cols = np.linspace(-1, 1, 7)
    P = np.zeros((n, len(cols), 3))
    for i, z in enumerate(zs):
        t = i / (n - 1)
        hw = 0.016 + (o["tie_width"] / 2 - 0.016) * t ** 0.85 - 0.007 * (1 - M.smoothstep(0.0, 0.08, t))
        tip = M.smoothstep(0.9, 1.0, t)
        for j, c in enumerate(cols):
            zz = z - 0.03 * tip * (1 - abs(c))
            y = hang[i] - 0.0016 * (1 - c * c) + 0.0006 * abs(c)
            P[i, j] = (c * hw, y, zz)
    P[-1, :, 2] = z_tip - 0.034 * (1 - np.abs(cols))          # pointed tip, laid back onto the shirt
    P[-2:, :, 1] += 0.003
    blade = _grid("tie_blade", P)
    M.solidify(blade, 0.0032, offset=-1.0)
    G.set_part_attr(blade, "part", TIE)
    return M.join([blade, knot], "tie")


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

def loafer(body, rig, cfg, s, W, V):
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
    M.cut_implicit(upper, topline)
    G.drop_small_islands(upper, 20)
    G.keep_largest(upper)
    G.set_part_attr(upper, "part", LOAFER)
    n_upper = len(upper.data.vertices)
    M.add_boundary_lip(upper, 0.003)
    lipf = np.zeros(len(upper.data.vertices), np.float32)
    lipf[n_upper:] = 1
    G.set_float_attr(upper, "lip", lipf)
    # saddle strap across the vamp
    strap = M.duplicate(upper, "loafer_strap_" + s)

    def sband(P):
        d = P - np.array([ank[0], ank[1], 0.0])
        fp, op = d @ fwd, d @ outw
        f_v = o["loafer_vamp_f"] - 0.03 * np.clip(op / 0.04, -1.2, 1.2) ** 2
        return np.minimum(0.0135 - np.abs(fp - (f_v + 0.006 + 0.0135)), P[:, 2] - (sole + 0.026))
    Ps = M.co(strap)
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
    shoe = M.join([upper, strap, sole_ob] if len(strap.data.vertices) else [upper, sole_ob], "loafer_" + s)
    # weights
    P = M.co(shoe)
    fp = (P - np.array([ank[0], ank[1], 0.0])) @ fwd
    wb = M.smoothstep(f_ball - 0.012, f_ball + 0.018, fp)
    M.set_weights(shoe, {"foot_" + s: 1 - wb, "ball_" + s: wb})
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
