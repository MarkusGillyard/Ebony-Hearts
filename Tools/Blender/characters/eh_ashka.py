"""Ashka Rook's canon outfit: white long-sleeved shirt (built only where it can show: the coat's
V opening, collar and cuffs), black tie, black trousers, brown loafers and a long black trench coat.

The coat: torso and sleeves are a shell grown from the body (inheriting skin weights); a V opening
with lapels shows shirt and tie; a stand collar and a belt; below the hip a lofted A-line skirt split
into four panels (front-left, front-right, back-left, back-right) by the front opening, two side
vents and a back vent, each panel skinned to its own 3-bone tail chain. At rest the split edges meet,
so the silhouette reads as one long coat; in motion the panels part instead of stretching."""
import math

import bpy
import numpy as np

import eh_garment as G
import eh_mesh as M
import eh_rig as R

# part tags
COAT_MAIN, COAT_LAPEL, COAT_COLLAR, COAT_BELT, COAT_BUCKLE, COAT_SKIRT, COAT_CUFF = 1, 2, 3, 4, 5, 6, 7
SHIRT, SHIRT_COLLAR, SHIRT_CUFF, TIE, PANTS, LOAFER, LOAFER_SOLE = 11, 12, 13, 14, 15, 16, 17

PANELS = (("fl", math.pi * 0.25, "l"), ("bl", math.pi * 0.75, "l"),
          ("br", math.pi * 1.25, "r"), ("fr", math.pi * 1.75, "r"))


def v_halfwidth(z, z_button, z_top, w_top):
    return np.clip((z - z_button) / (z_top - z_button), 0, None) ** 1.1 * w_top


def build(body, rig, cfg, collider_body):
    o = cfg["outfit"]
    V = M.co(body)
    Nb = M.vnormals(body)
    W = M.weights(body)
    X, Y, Z = V[:, 0], V[:, 1], V[:, 2]
    ax = np.abs(X)
    zc = rig.data.bones["clavicle_l"].head_local[2]
    zp = rig.data.bones["pelvis"].head_local[2]
    zn = rig.data.bones["neck_01"].head_local[2]
    sy = G.spine_y(rig, Z)
    front = Y < sy
    z_button = zp + o["button_above_pelvis"]
    z_vtop = zc + 0.01
    w_vtop = o["v_halfwidth_top"]
    vhalf = v_halfwidth(Z, z_button, z_vtop, w_vtop)
    out = {}
    hide = np.zeros(len(body.data.polygons), bool)
    keep = np.zeros(len(body.data.polygons), bool)
    handw = {s: G.wsum(W, G.side_names(G.HAND, s)) for s in "lr"}
    tfa = {s: G.limb_param(rig, "lowerarm_" + s, V)[0] for s in "lr"}
    armw = {s: G.wsum(W, G.side_names(["upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"], s))
            for s in "lr"}
    is_arm = (armw["l"] > 0.5) | (armw["r"] > 0.5)
    arm_t = np.where(X > 0, tfa["l"], tfa["r"])
    hand = (handw["l"] > 0.4) | (handw["r"] > 0.4)
    neck_cut = np.where(front, zn - 0.035 + 18 * ax ** 2, zn - 0.005 + 10 * ax ** 2)

    # ------------------------------------------------------------------ shirt (visible parts)
    headw0 = W.get("head", np.zeros(len(V)))
    shirt_front = front & (ax < vhalf + 0.09) & (Z > z_button - 0.07) & (Z < np.minimum(neck_cut + 0.04, zn + 0.01)) \
        & ~is_arm & (headw0 < 0.3)
    headw = W.get("head", np.zeros(len(V)))
    collar = (Z > neck_cut - 0.01) & (Z < neck_cut + 0.042) & ~is_arm & (Z > zc - 0.05) & (headw < 0.3) & (ax < 0.085)
    vm = shirt_front & ~hand
    shirt, src, fm = G.shell(body, vm, "shirt", 0.004, collider_body, relax_iters=10, lip=0.0025)
    _tags(shirt, np.full(len(src), SHIRT))
    hide |= G.hidden_face_mask(body, fm, garment=shirt)
    cuffs = []
    for s in "lr":
        side = (X > 0) if s == "l" else (X < 0)
        vm = side & (armw[s] > 0.4) & (tfa[s] > 0.84) & (tfa[s] < 1.02) & (handw[s] < 0.5)
        c, src, fm = G.shell(body, vm, "cuff_" + s, 0.0045, collider_body, relax_iters=3, lip=0.0025)
        _tags(c, np.full(len(src), SHIRT_CUFF))
        cuffs.append(c)
        hide |= G.hidden_face_mask(body, fm, garment=c, margin_m=0.008)
    scollar = _shirt_collar(body, rig, cfg)
    _weights_from(scollar, shirt)
    shirt = M.join([shirt] + cuffs + [scollar], "shirt")
    out["shirt"] = shirt
    tie_ob = tie(rig, cfg, shirt, z_button)
    _weights_from(tie_ob, shirt)
    out["tie"] = tie_ob
    # keep a sternum patch of skin under the shirt (the chest tattoo lives there)
    tat = np.array([0.0, 0.0, zc + o["tattoo_dz"]])
    ls, lt, lv = M.polys(body)
    fc = M.poly_centers(body)
    patch = (np.abs(fc[:, 0]) < 0.075) & (np.abs(fc[:, 2] - tat[2]) < 0.06) & (fc[:, 1] < G.spine_y(rig, fc[:, 2]))
    keep |= patch

    # ------------------------------------------------------------------ trousers
    zw = np.where(front, zp + 0.045, zp + 0.06)
    legs = np.zeros(len(V), bool)
    rad = np.zeros(len(V))
    for s in "lr":
        lw = G.wsum(W, G.side_names(["thigh", "thigh_twist_01", "calf"], s))
        legs |= lw > 0.5
    z_hem = o["pants_hem_z"] + cfg["sole_m"]
    footw = G.wsum(W, G.side_names(["foot", "ball"], "l") + G.side_names(["foot", "ball"], "r"))
    z_ank = rig.data.bones["foot_l"].head_local[2]
    vm = (Z <= zw) & (Z >= z_hem) & ~((footw >= 0.5) & (Z < z_ank - 0.005)) & ~is_arm & ~hand
    tcalf = np.where(X > 0, G.limb_param(rig, "calf_l", V)[0], G.limb_param(rig, "calf_r", V)[0])
    off = 0.0055 + 0.006 * M.smoothstep(0.15, 0.6, tcalf) * legs

    def straighten(P, src):
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

    pants, src, fm = G.shell(body, vm, "pants", off, collider_body, relax_iters=14, relax_factor=0.5,
                             smooth_offset=5, lip=0.003, extra_push=straighten)
    _tags(pants, np.full(len(src), PANTS))
    hide |= G.hidden_face_mask(body, fm, garment=pants)
    out["pants"] = pants

    # ------------------------------------------------------------------ loafers
    loafers = []
    for s in "lr":
        side = (X > 0) if s == "l" else (X < 0)
        fw = G.wsum(W, G.side_names(["foot", "ball", "calf"], s))
        ank = np.array(rig.data.bones["foot_" + s].head_local)
        instep = M.smoothstep(ank[1] + 0.01, ank[1] - 0.05, Y)
        cut = ank[2] - 0.012 + 0.03 * instep
        vm = side & (fw > 0.4) & (Z < cut)
        toe = M.smoothstep(ank[1] - 0.08, ank[1] - 0.15, Y)
        lo, src, fm = G.shell(body, vm, "loafer_" + s, 0.0042 + 0.011 * toe, collider_body, relax_iters=40,
                              relax_factor=0.5, smooth_offset=10, lip=0.003, presmooth=25)
        P = M.co(lo)
        sole = cfg["sole_m"]
        flat = P[:, 2] < sole + 0.009
        P[flat, 2] = 0.0
        low = (~flat) & (P[:, 2] < sole + 0.02)
        P[low, 2] = np.maximum(P[low, 2] - 0.01, 0.0)
        M.set_co(lo, P)
        part = np.where(P[:, 2] < sole + 0.002, LOAFER_SOLE, LOAFER)
        G.set_part_attr(lo, "part", part.astype(np.int32))
        loafers.append(lo)
        hide |= G.hidden_face_mask(body, fm, garment=lo, margin_m=0.006)
    out["loafers"] = M.join(loafers, "loafers")

    # ------------------------------------------------------------------ coat: torso + sleeves
    z_cut = zp + o["skirt_top_rel_pelvis"]
    sleeve_end = o["sleeve_end_t"]
    region = (Z >= z_cut) & (Z < neck_cut + 0.005) & ~hand & ~(is_arm & (arm_t > sleeve_end))
    t_arm = np.where(is_arm, arm_t, 0.0)
    zb = zp + o["belt_above_pelvis"]
    off = np.where(is_arm, 0.012 + 0.008 * M.smoothstep(0.3, 1.0, t_arm),
                   o["coat_offset"] * (1 - 0.4 * np.exp(-((Z - zb) / 0.06) ** 2)))
    off = off + 0.004 * M.smoothstep(zc - 0.06, zc + 0.03, Z) * (~is_arm)       # light shoulder structure
    coat, src, fm = G.shell(body, region, "coat", off, collider_body, relax_iters=28,
                            relax_factor=0.5, smooth_offset=6, lip=0.0)
    coat_cover = fm.copy()
    Wcs = M.weights(coat)                 # torso shell: no thigh influence either
    for s_ in "lr":
        for nm in ("thigh_" + s_, "thigh_twist_01_" + s_):
            if nm in Wcs:
                Wcs["pelvis"] = Wcs.get("pelvis", 0) + Wcs.pop(nm)
    M.set_weights(coat, M.normalize_limit(Wcs, 8))
    Pc = M.co(coat)
    # V opening (shirt and tie show through it)
    Vc = V[src]
    vhalf_c = v_halfwidth(Vc[:, 2], z_button, z_vtop + 0.06, w_vtop * 1.1)
    in_v = (Vc[:, 1] < G.spine_y(rig, Vc[:, 2])) & (np.abs(Vc[:, 0]) < vhalf_c) & (Vc[:, 2] > z_button)
    fmask_v = M.face_mask_from_verts(coat, in_v, "any")
    M.delete_faces(coat, fmask_v)
    Pc = M.co(coat)
    bnd = M.boundary_vmask(coat)
    sy_c = G.spine_y(rig, Pc[:, 2])
    vline = v_halfwidth(Pc[:, 2], z_button, z_vtop + 0.06, w_vtop * 1.1)
    snap = bnd & (Pc[:, 1] < sy_c - 0.02) & (Pc[:, 2] > z_button - 0.005) & (np.abs(np.abs(Pc[:, 0]) - vline) < 0.035) \
        & (Pc[:, 2] < z_vtop + 0.05)
    Pc[snap, 0] = np.sign(Pc[snap, 0] + 1e-9) * vline[snap]
    M.set_co(coat, Pc)
    src_attr = G.get_attr(coat, "src_vi", np.int64)
    G.set_part_attr(coat, "part", np.where(is_arm[src_attr] & (arm_t[src_attr] > sleeve_end - 0.06),
                                           COAT_CUFF, COAT_MAIN).astype(np.int32))
    # the shell's bottom loop around the hips becomes the skirt's top row
    loops = M.boundary_loops(coat)
    Pc = M.co(coat)
    best = None
    for lp in loops:
        q = Pc[lp]
        if np.abs(q[:, 0]).max() < 0.35 and np.abs(q[:, 0].mean()) < 0.05 and len(lp) > 20:
            if best is None or q[:, 2].mean() < Pc[best][:, 2].mean():
                best = lp
    if best is None:
        for lp in loops:
            q = Pc[lp]
            print("[coat loop]", len(lp), np.round(q.mean(0), 3), np.round(np.abs(q[:, 0]).max(), 3), np.round(q[:, 2].min(), 3))
        print("[coat] z_cut", z_cut)
        raise RuntimeError("no hip loop on the coat shell")
    skirt, skirt_info = _skirt(coat, best, rig, cfg, [pants, out["loafers"]])
    lapels = _lapels(coat, rig, z_button, cfg)
    collar_ob = _collar(body, rig, cfg, coat)
    belt = _belt(coat, rig, cfg, skirt)
    for ob in (lapels, collar_ob):
        _weights_from(ob, coat)
    _weights_from(belt, M.join([M.duplicate(coat, "tmp_c"), M.duplicate(skirt, "tmp_s")], "tmp_cs"))
    tmp = bpy.data.objects.get("tmp_cs")
    if tmp is not None:
        bpy.data.objects.remove(tmp)
    loop_pos = M.co(coat)[best]
    hip = np.zeros(len(M.co(coat)), bool)
    hip[best] = True
    M.add_boundary_lip(coat, 0.004, vmask=~hip)
    coat = M.join([coat, skirt, lapels, collar_ob, belt], "coat")
    _weld_points(coat, loop_pos)
    out["coat"] = coat
    # body faces hidden by the coat (exclude the V region, which the shirt covers)
    hide |= G.hidden_face_mask(body, coat_cover, garment=coat, margin_m=0.015)
    hide &= ~keep
    return out, hide, skirt_info


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


def _tags(ob, part_src):
    n = len(ob.data.vertices)
    tags = np.zeros(n, np.int32)
    k = len(part_src)
    tags[:k] = part_src
    if n > k:
        V = M.co(ob)
        for i in range(k, n):
            tags[i] = part_src[np.argmin(((V[:k] - V[i]) ** 2).sum(1))]
    G.set_part_attr(ob, "part", tags)


def _weights_from(dst, src):
    Wd = M.transfer_weights_nearest(dst, M.co(src), M.weights(src), k=4)
    M.set_weights(dst, M.normalize_limit(Wd, 8))


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
    # leg/trouser extents per column direction and height
    LP = np.concatenate([M.co(ob) for ob in leg_objs])
    rows = []
    for i in range(Rn + 1):
        t = i / Rn
        z = z_top + (z_hem - z_top) * t
        flare = o["skirt_flare"] * t ** 1.1 * (1 + 0.2 * np.abs(np.sin(ang)))
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
        r = np.maximum(r, r_top + flare * 0.7)
        P = np.stack([dirs[:, 0] * r, yc + dirs[:, 1] * r, z], 1)
        if i == 0:
            P = q.copy()
        rows.append(P)
    rows = np.array(rows)                                    # (Rn+1, N, 3)
    # split columns: front, sides, back
    splits = {"front": (0.0, Rn + 1), "left": (math.pi / 2, o["side_slit_rows"]),
              "back": (math.pi, o["back_vent_rows"]), "right": (1.5 * math.pi, o["side_slit_rows"])}
    split_col = {}
    for k, (a, nrows) in splits.items():
        d = np.abs((ang - a + math.pi) % (2 * math.pi) - math.pi)
        split_col[k] = (int(np.argmin(d)), nrows)
    # vertices: grid ids, plus duplicates for split columns on rows >= Rn+1-nrows (row 0 never split)
    verts = [rows[i, j] for i in range(Rn + 1) for j in range(N)]
    vid = lambda i, j: i * N + j
    dup = {}
    for k, (c, nrows) in split_col.items():
        first = max(1, Rn + 1 - nrows)
        for i in range(first, Rn + 1):
            dup[(i, c)] = len(verts)
            verts.append(rows[i, c].copy())
    verts = np.array(verts)
    faces, uvs, fpanel = [], [], []
    col_panel = np.zeros(N, int)
    for j in range(N):
        a = ang[j]
        col_panel[j] = int(a // (math.pi / 2)) % 4
    split_cols = {c for c, _ in split_col.values()}
    for i in range(Rn):
        for j in range(N):
            j2 = (j + 1) % N
            a, b, c_, d = vid(i, j), vid(i, j2), vid(i + 1, j2), vid(i + 1, j)
            # faces to the right of a split column (j2 == split) use the original vertex; faces to the
            # left of it (j == split) use the duplicate
            if j in split_cols:
                if (i, j) in dup:
                    a = dup[(i, j)]
                if (i + 1, j) in dup:
                    d = dup[(i + 1, j)]
            faces.append((a, d, c_, b))
            uvs.append([(j / N, 1 - i / Rn), (j / N, 1 - (i + 1) / Rn), ((j + 1) / N, 1 - (i + 1) / Rn), ((j + 1) / N, 1 - i / Rn)])
            fpanel.append(col_panel[j])
    # split edges: the higher-angle panel's edge sits a little outside the other one; at the front the
    # left panel (+X) also laps across the centre over the right panel
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
                verts[oid] += n_out * 0.0015
    ob = M.make_object("skirt", verts, faces, uvs)
    # weights: top row keeps the shell weights, then hands over to the panel chains
    n = len(verts)
    s_m = np.zeros(n)
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
    # panel membership: duplicates belong to the panel on the left of the split (higher angle side)
    panel_of = np.array([col_panel[c] for c in colj])
    for (i, j), k in dup.items():
        panel_of[k] = col_panel[(j + 1) % N]
        panel_of[vid(i, j)] = col_panel[(j - 1) % N]
    # above the slit tops blend panels by angle
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
        pts = [rows[int(round(Rn * f)), jc] for f in (0.0, 1 / 3, 2 / 3, 1.0)]
        chains[key] = {"points": pts, "side": side, "col": jc,
                       "names": ["coat_%s_%02d" % (key, k + 1) for k in range(3)]}
    bounds = [0.0, L / 3, 2 * L / 3, L]
    Wtop = {k: v[loop] for k, v in Wc.items()}
    for s_ in "lr":                       # the coat hangs from the pelvis; the tails follow the legs
        for nm in ("thigh_" + s_, "thigh_twist_01_" + s_):
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

def _lapels(coat, rig, z_button, cfg):
    """Lapels laid along the analytic V line (clean edges), folded over the coat chest."""
    o = cfg["outfit"]
    zc = rig.data.bones["clavicle_l"].head_local[2]
    z_top = zc + 0.01
    col = M.Collider([coat])
    parts = []
    n = 16
    zs = np.linspace(z_button + 0.004, z_top + 0.045, n)
    for sg in (1.0, -1.0):
        e, nn = [], []
        for z in zs:
            x = sg * (float(v_halfwidth(np.array([z]), z_button, z_top + 0.06, o["v_halfwidth_top"] * 1.1)[0]) + 0.003)
            r = col.ray(np.array([x, -0.6, z]), np.array([0, 1.0, 0]), 1.2)
            if r[0] is None:
                loc, nrm, _ = col.nearest(np.array([[x, -0.1, z]]))
                e.append(loc[0]); nn.append(nrm[0])
            else:
                e.append(np.array(r[0])); nn.append(np.array(r[1]))
        e, nn = np.array(e), np.array(nn)
        nn /= np.linalg.norm(nn, axis=1, keepdims=True)
        t = np.linspace(0, 1, n)
        width = o["lapel_width"] * (np.sin(np.clip(t * 1.15, 0, 1) * np.pi * 0.5) ** 0.9) * (1 - 0.55 * M.smoothstep(0.86, 1.0, t))
        lat = np.array([sg, 0.0, 0.0])
        out_dir = lat - nn * (nn @ lat)[:, None]
        out_dir /= np.linalg.norm(out_dir, axis=1, keepdims=True)
        inner = e + nn * 0.003
        outer = e + out_dir * width[:, None] + nn * 0.0045
        mid = inner * 0.5 + outer * 0.5 + nn * 0.0015
        verts = np.vstack([inner, mid, outer])
        faces, uvs = [], []
        for i in range(n - 1):
            for r_ in range(2):
                a, b = r_ * n + i, r_ * n + i + 1
                c, d = (r_ + 1) * n + i + 1, (r_ + 1) * n + i
                uv = [(r_ / 2, i / (n - 1)), (r_ / 2, (i + 1) / (n - 1)), ((r_ + 1) / 2, (i + 1) / (n - 1)), ((r_ + 1) / 2, i / (n - 1))]
                if sg > 0:
                    faces.append((a, b, c, d)); uvs.append(uv)
                else:
                    faces.append((a, d, c, b)); uvs.append([uv[0], uv[3], uv[2], uv[1]])
        parts.append((verts, faces, uvs))
    V, F, U, _ = M.merge_parts(parts)
    ob = M.make_object("lapels", V, F, U)
    M.solidify(ob, 0.0025, offset=-1.0)
    G.set_part_attr(ob, "part", COAT_LAPEL)
    return ob


def _shirt_collar(body, rig, cfg):
    """Shirt collar: a clean band round the neck, open at the front, with two collar points."""
    zn = rig.data.bones["neck_01"].head_local[2]
    yn = rig.data.bones["neck_01"].head_local[1]
    col = M.Collider([body])
    angs = np.radians(np.linspace(-160, 160, 33))          # 0 = back (+Y)
    rows = []
    for k, hgt in enumerate((0.0, 0.016, 0.032)):
        ring = []
        for a in angs:
            d = np.array([np.sin(a), np.cos(a), 0.0])
            z = zn - 0.032 + 0.016 * (1 - np.cos(a)) * 0.5 + hgt
            o_ = np.array([0, yn, z])
            r = col.ray(o_ + d * 0.25, -d, 0.3)
            p = np.array(r[0]) if r[0] is not None else o_ + d * 0.055
            ring.append(p + d * (0.006 + 0.004 * k))
        rows.append(ring)
    rows = np.array(rows)
    nR, nA = rows.shape[:2]
    verts = list(rows.reshape(-1, 3))
    faces, uvs = [], []
    for i in range(nR - 1):
        for j in range(nA - 1):
            a, b, c, d = i * nA + j, i * nA + j + 1, (i + 1) * nA + j + 1, (i + 1) * nA + j
            faces.append((a, d, c, b))
            uvs.append([(j / (nA - 1), i / (nR - 1)), (j / (nA - 1), (i + 1) / (nR - 1)),
                        ((j + 1) / (nA - 1), (i + 1) / (nR - 1)), ((j + 1) / (nA - 1), i / (nR - 1))])
    # collar points: from each front end of the band down over the shirt front
    for j0, sg in ((0, -1.0), (nA - 1, 1.0)):
        top = rows[2, j0]
        bot = rows[0, j0]
        tip = bot + np.array([sg * 0.012, -0.012, -0.048])
        base = len(verts)
        verts += [top, bot, tip]
        faces.append((base, base + 1, base + 2) if sg > 0 else (base, base + 2, base + 1))
        uvs.append([(0.0, 1.0), (0.0, 0.0), (0.5, 0.0)] if sg > 0 else [(0.0, 1.0), (0.5, 0.0), (0.0, 0.0)])
    ob = M.make_object("shirt_collar", np.array(verts), faces, uvs)
    M.solidify(ob, 0.0022, offset=-1.0)
    G.set_part_attr(ob, "part", SHIRT_COLLAR)
    return ob


def _collar(body, rig, cfg, coat):
    o = cfg["outfit"]
    zn = rig.data.bones["neck_01"].head_local[2]
    nb = rig.data.bones["neck_01"]
    axis_y = nb.head_local[1]
    col = M.Collider([body])
    rings = []
    angs = np.linspace(math.radians(-118), math.radians(118), 25)     # around the back of the neck
    heights = [0.0, 0.018, 0.036, o["collar_height"]]
    Pc = M.co(coat)
    for hgt in heights:
        ring = []
        for a in angs:
            d = np.array([math.sin(a), math.cos(a), 0.0])           # a=0 points to the back (+Y)
            z = zn - 0.02 + 0.012 * (1 - math.cos(a)) + hgt
            o_ = np.array([0, axis_y, z])
            r = col.ray(o_ + d * 0.25, -d, 0.3)
            p = np.array(r[0]) if r[0] is not None else o_ + d * 0.06
            ring.append(p + d * (0.017 + hgt * 0.35))
        rings.append(ring)
    rings = np.array(rings)
    nR, nA = rings.shape[:2]
    verts = rings.reshape(-1, 3)
    faces, uvs = [], []
    for i in range(nR - 1):
        for j in range(nA - 1):
            a, b, c, d = i * nA + j, i * nA + j + 1, (i + 1) * nA + j + 1, (i + 1) * nA + j
            faces.append((a, d, c, b))
            uvs.append([(j / (nA - 1), i / (nR - 1)), (j / (nA - 1), (i + 1) / (nR - 1)),
                        ((j + 1) / (nA - 1), (i + 1) / (nR - 1)), ((j + 1) / (nA - 1), i / (nR - 1))])
    ob = M.make_object("collar", verts, faces, uvs)
    M.solidify(ob, 0.003, offset=-1.0)
    G.set_part_attr(ob, "part", COAT_COLLAR)
    return ob


def _belt(coat, rig, cfg, skirt=None):
    o = cfg["outfit"]
    zp = rig.data.bones["pelvis"].head_local[2]
    zb = zp + o["belt_above_pelvis"]
    col = M.Collider([coat])
    yc = G.spine_y(rig, np.array([zb]))[0] - 0.01
    n = 56
    angs = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rows = []
    for dz in (-o["belt_height"] / 2, 0.0, o["belt_height"] / 2):
        ring = []
        for a in angs:
            d = np.array([math.sin(a), -math.cos(a), 0.0])
            org = np.array([0, yc, zb + dz])
            r = col.ray(org + d * 0.5, -d, 0.6)
            p = np.array(r[0]) if r[0] is not None else org + d * 0.15
            ring.append(p + d * 0.0032)
        rows.append(ring)
    rows = np.array(rows)
    verts = rows.reshape(-1, 3)
    faces, uvs = [], []
    for i in range(2):
        for j in range(n):
            j2 = (j + 1) % n
            a, b, c, d = i * n + j, i * n + j2, (i + 1) * n + j2, (i + 1) * n + j
            faces.append((a, b, c, d))
            uvs.append([(j / n, i / 2), ((j + 1) / n, i / 2), ((j + 1) / n, (i + 1) / 2), (j / n, (i + 1) / 2)])
    ob = M.make_object("belt", verts, faces, uvs)
    M.solidify(ob, 0.0025, offset=-1.0)
    G.set_part_attr(ob, "part", COAT_BELT)
    # tied knot and two hanging tails, front-left of centre
    col = M.Collider([coat] + ([skirt] if skirt is not None else []))
    kx = o["belt_knot_x"]
    r = col.ray(np.array([kx, -0.6, zb]), np.array([0, 1.0, 0]), 1.2)
    ky = (r[0][1] if r[0] is not None else yc - 0.12) - 0.012
    knot_v, knot_f, knot_u = M.tube(np.array([[kx - 0.018, ky, zb], [kx + 0.018, ky, zb]]),
                                   np.full(2, 0.016), np.full(2, 0.011), 8,
                                   np.array([[0, 0, 1.0]] * 2), np.array([[0, -1.0, 0]] * 2), cap_start=True, cap_end=True)
    parts = [(knot_v, knot_f, knot_u)]
    for dx, length, ang in ((-0.008, 0.2, 0.08), (0.012, 0.16, -0.18)):
        pts = []
        for t in np.linspace(0, 1, 7):
            z = zb - 0.01 - length * t
            x = kx + dx + np.sin(ang) * length * t
            rr = col.ray(np.array([x, -0.6, z]), np.array([0, 1.0, 0]), 1.2)
            y = (rr[0][1] if rr[0] is not None else ky) - 0.006 - 0.004 * (1 - t)
            pts.append((x, y, z))
        pts = np.array(pts)
        hw = o["belt_height"] * 0.42
        tv, tf, tu = [], [], []
        for k, p in enumerate(pts):
            tv += [p + np.array([-hw, 0, 0]), p + np.array([hw, 0, 0])]
        for k in range(len(pts) - 1):
            a = 2 * k
            tf.append((a, a + 1, a + 3, a + 2))
            tu.append([(0, k / 6), (1, k / 6), (1, (k + 1) / 6), (0, (k + 1) / 6)])
        tip = len(tv)
        tv.append(pts[-1] + np.array([0, 0, -0.025]))
        tf.append((2 * (len(pts) - 1), 2 * (len(pts) - 1) + 1, tip))
        tu.append([(0, 1), (1, 1), (0.5, 1)])
        parts.append((np.array(tv), tf, tu))
    V, F, U, _ = M.merge_parts(parts)
    tails = M.make_object("belt_tie", V, F, U)
    M.solidify(tails, 0.0025, offset=-1.0)
    G.set_part_attr(tails, "part", COAT_BELT)
    return M.join([ob, tails], "belt")


# ----------------------------------------------------------------------------- tie

def tie(rig, cfg, shirt, z_button):
    o = cfg["outfit"]
    zn = rig.data.bones["neck_01"].head_local[2]
    col = M.Collider([shirt])
    z_knot = zn - 0.03
    rows = np.linspace(z_knot - 0.035, z_button - 0.015, 16)
    cols = np.linspace(-1, 1, 5)
    verts = []
    for k, z in enumerate(rows):
        t = k / (len(rows) - 1)
        hw = 0.018 + (o["tie_width"] / 2 - 0.018) * t ** 0.8
        for c in cols:
            x = c * hw
            org = np.array([x, -0.5, z])
            r = col.ray(org, np.array([0, 1.0, 0]), 1.0)
            y = r[0][1] - 0.0045 if r[0] is not None else -0.1
            verts.append((x, y, z - (0.012 * (1 - abs(c)) if k == len(rows) - 1 else 0)))
    verts = np.array(verts)
    nc = len(cols)
    faces, uvs = [], []
    for i in range(len(rows) - 1):
        for j in range(nc - 1):
            a, b, c, d = i * nc + j, i * nc + j + 1, (i + 1) * nc + j + 1, (i + 1) * nc + j
            faces.append((a, d, c, b))
            uvs.append([(j / (nc - 1), 1 - i / len(rows)), (j / (nc - 1), 1 - (i + 1) / len(rows)),
                        ((j + 1) / (nc - 1), 1 - (i + 1) / len(rows)), ((j + 1) / (nc - 1), 1 - i / len(rows))])
    # knot: a small tapered block at the collar
    kc = np.array([0.0, 0, z_knot - 0.012])
    r = col.ray(np.array([0, -0.5, kc[2]]), np.array([0, 1.0, 0]), 1.0)
    ky = r[0][1] - 0.006 if r[0] is not None else -0.1
    kv = []
    for z, hw, dy in ((z_knot + 0.006, 0.017, 0.0), (z_knot - 0.012, 0.015, -0.012), (z_knot - 0.03, 0.01, -0.004)):
        for x, yy in ((-hw, 0.0), (-hw * 0.6, -0.006), (hw * 0.6, -0.006), (hw, 0.0)):
            kv.append((x, ky + yy + dy * 0.4, z))
    base = len(verts)
    verts = np.vstack([verts, np.array(kv)])
    for i in range(2):
        for j in range(3):
            a, b = base + i * 4 + j, base + i * 4 + j + 1
            c, d = base + (i + 1) * 4 + j + 1, base + (i + 1) * 4 + j
            faces.append((a, d, c, b))
            uvs.append([(0.8 + j * 0.05, 0.9 - i * 0.05), (0.8 + j * 0.05, 0.85 - i * 0.05),
                        (0.85 + j * 0.05, 0.85 - i * 0.05), (0.85 + j * 0.05, 0.9 - i * 0.05)])
    ob = M.make_object("tie", verts, faces, uvs)
    M.solidify(ob, 0.0025, offset=-1.0)
    G.set_part_attr(ob, "part", TIE)
    return ob


def coat_rig(rig, skirt_info):
    """Coat tail chains (pelvis children) and thigh-follow helpers (Blender-only, not exported)."""
    for key, ch in skirt_info["chains"].items():
        pts = ch["points"]
        out = pts[0] - np.array([0, skirt_info["yc"], pts[0][2]])
        out[2] = 0
        out /= max(np.linalg.norm(out), 1e-6)
        R.add_chain(rig, ch["names"], pts, "pelvis", roll_up=tuple(out), connect=True)
        helper = "helper_coat_" + key
        tail = np.array(pts[1])
        R.add_helper(rig, helper, "thigh_" + ch["side"], tail, tail + np.array([0, 0, -0.05]))
        infl = 1.0 if key.startswith("f") else 0.55
        R.damped_follow(rig, ch["names"][0], helper, infl)
