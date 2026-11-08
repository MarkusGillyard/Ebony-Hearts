"""The two canon hairstyles, assembled from eh_hair pieces, with their secondary bone chains.

Wren: long brown hair, centre part, two neat braids from behind the ears down the upper back
      (chains braid_l_01..04, braid_r_01..04 under head).
Ashka: long crimson hair swept back into one loose braid from the nape (braid_01..05 under head),
      bangs ending just past the eyebrows, two longer face-framing strands (strand_l_01..02,
      strand_r_01..02 under head)."""
import numpy as np

import eh_garment as G
import eh_hair as H
import eh_mesh as M
import eh_rig as R


def _norm(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _onto(col, p, inset=0.0):
    """Nearest point on the collider surface to p, moved `inset` metres inside along its normal."""
    loc, nrm, ok = col.nearest(np.asarray(p, float)[None])
    return loc[0] - nrm[0] * inset


def _back(col, x, z, clear):
    r = col.ray(np.array([x, 0.6, z]), np.array([0, -1.0, 0]), 1.2)
    if r[0] is None:
        loc, nrm, _ = col.nearest(np.array([[x, 0.1, z]]))
        return loc[0] + nrm[0] * clear
    return np.array([x, r[0][1] + clear, z])


def _front(col, x, z, clear):
    r = col.ray(np.array([x, -0.6, z]), np.array([0, 1.0, 0]), 1.2)
    if r[0] is None:
        loc, nrm, _ = col.nearest(np.array([[x, -0.1, z]]))
        return loc[0] + nrm[0] * clear
    return np.array([x, r[0][1] - clear, z])


def _face_pt(col, x, z, off):
    """Front surface point at (x, z) moved `off` along its normal (and that normal)."""
    r = col.ray(np.array([x, -0.6, z]), np.array([0, 1.0, 0]), 1.2)
    if r[0] is None:
        loc, nrm, _ = col.nearest(np.array([[x, -0.1, z]]))
        return loc[0] + nrm[0] * off, nrm[0]
    n = np.array(r[1])
    return np.array(r[0]) + n * off, n


def _side_pt(col, sg, y, z, off):
    r = col.ray(np.array([sg * 0.4, y, z]), np.array([-sg, 0, 0]), 0.5)
    if r[0] is None:
        loc, nrm, _ = col.nearest(np.array([[sg * 0.08, y, z]]))
        return loc[0] + nrm[0] * off, nrm[0]
    n = np.array(r[1])
    return np.array(r[0]) + n * off, n


def _path_points(path, arc_targets):
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    return [np.array([np.interp(t, s, path[:, k]) for k in range(3)]) for t in arc_targets]


def _tube_object(name, parts, arcs, strand_part, tie_part=None):
    V, F, U, pid = M.merge_parts(parts)
    ob = M.make_object(name, V, F, U)
    tags = np.full(len(V), strand_part, np.int32)
    if tie_part is not None:
        tags[pid == pid.max()] = tie_part
    G.set_part_attr(ob, "part", tags)
    arc = np.concatenate(arcs)
    G.set_float_attr(ob, "arc", arc)
    return ob, arc


def head_extras(body, hi):
    V = M.co(body)
    sel = (np.abs(V[:, 0]) < 0.015) & (V[:, 1] < hi["center"][1] - 0.05) & (V[:, 2] > hi["neck"][2])
    hi["chin_z"] = float(V[sel, 2].min()) if sel.any() else hi["neck"][2] + 0.02
    return hi


def wren(body, rig, parts, garments, cfg):
    """Two Dutch braids: from the front hairline beside a centre part, lying on the head back to
    behind the ears, then hanging to mid-back. The on-head part is rigid to `head`; the hanging part
    rides the 4-bone chain."""
    H.set_layout("default")
    h = cfg["hair"]
    hi = head_extras(body, H.head_info(body, rig, parts))
    col_body = M.Collider([body])
    cap = H.cap(body, rig, hi, col_body, "part", thick=h["cap_thickness"], grow=2)
    capc = M.Collider([cap])
    col = M.Collider([body, cap] + garments)
    zc = rig.data.bones["clavicle_l"].head_local[2]
    C = hi["center"]
    top = hi["head_top"]
    pieces = [cap]
    info = {}
    for s, sg in (("l", 1.0), ("r", -1.0)):
        ear = hi["ear_" + s]
        hz = hi["brow_top"] + h["hairline_up"]
        way = [np.array([sg * 0.024, C[1] - 0.085, hz]),
               np.array([sg * 0.034, C[1] - 0.05, top - 0.018]),
               np.array([sg * 0.046, C[1] + 0.015, top - 0.012]),
               np.array([sg * 0.06, C[1] + 0.065, ear[2] + 0.035]),
               np.array([sg * 0.058, C[1] + 0.08, ear[2] - 0.03])]
        lift = h["width"][0] * 0.35
        on_head = [_onto(capc, w, inset=-lift) for w in way]
        hang = [_back(col, sg * 0.07, zc + 0.02, h["clear"] + 0.006),
                _back(col, sg * 0.08, zc - 0.11, h["clear"]),
                _back(col, sg * 0.086, zc - h["drop"], h["clear"])]
        ctrl = on_head + hang
        z_leave = ear[2] - 0.03

        def hint(path, sg=sg, z_leave=z_leave):
            out = path - C
            out /= np.linalg.norm(out, axis=1, keepdims=True)
            back = np.array([sg * 0.35, 1.0, 0.1])
            back /= np.linalg.norm(back)
            k = M.smoothstep(z_leave + 0.02, z_leave - 0.06, path[:, 2])[:, None]
            return out * (1 - k) + back * k

        parts_, arcs, desc = H.braid(ctrl, col, depth_hint=hint, width=tuple(h["width"]),
                                     period=h["period"], tassel=h["tassel"], sides=6, seg_per_period=14,
                                     clear=-0.004, seed=1 if s == "l" else 2)
        ob, arc = _tube_object("braid_" + s, parts_, arcs, H.P_BRAID, H.P_TIE)
        L = desc["length"]
        path = desc["path"]
        seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
        sp = np.r_[0, np.cumsum(seg)]
        s_leave = float(sp[np.argmin(np.linalg.norm(path - on_head[-1], axis=1))])
        bounds = [s_leave + (L - s_leave) * k / 4 for k in range(5)]
        names = ["braid_%s_%02d" % (s, k) for k in range(1, 5)]
        pts = _path_points(path, bounds)
        R.add_chain(rig, names, pts, "head", roll_up=(sg, 0, 0), rest=cfg.get("rest_chains"))
        M.set_weights(ob, M.normalize_limit(R.chain_weights(arc, bounds, names, "head", 0.04, s_leave), 8))
        pieces.append(ob)
        info["braid_" + s] = {"length_m": round(L, 3), "on_head_m": round(s_leave, 3),
                              "hanging_m": round(L - s_leave, 3), "periods_in_v": desc["periods_in_v"]}
    return _finish(pieces, parts, cfg), info


def _card_object(name, parts, part_id=None):
    V, F, U, pid = M.merge_parts(parts)
    ob = M.make_object(name, V, F, U)
    G.set_part_attr(ob, "part", np.full(len(V), H.P_CARD if part_id is None else part_id, np.int32))
    return ob


def ashka(body, rig, parts, garments, cfg):
    """Bangs and face-framing strands are layered alpha cards (strand clumps, tapered tips), the loose
    braid keeps woven strand tubes but gets flyaway cards along it and gathered cards from the nape
    into its top, so it is attached to the head with volume. Chains as before (same control paths)."""
    H.set_layout("cards")
    h = cfg["hair"]
    hi = head_extras(body, H.head_info(body, rig, parts))
    col_body = M.Collider([body])
    cap = H.cap(body, rig, hi, col_body, "back", thick=h["cap_thickness"], grow=2)
    capc = M.Collider([cap])
    col_all = M.Collider([body, cap] + garments)
    zc = rig.data.bones["clavicle_l"].head_local[2]
    zn = rig.data.bones["neck_01"].head_local[2]
    pieces = [cap]
    info = {}
    rng = np.random.default_rng(7)
    # ---- bangs: three staggered layers of cards over the forehead, tips just past the eyebrows
    bang_parts = []
    span = h["bang_span"]
    capV = M.co(cap)
    for row, n, wmul, out_add in ((0, h["bang_count"], 1.0, 0.0), (1, h["bang_count"] - 1, 0.95, 0.0035),
                                  (2, h["bang_count"] - 2, 0.7, 0.0065)):
        for i in range(n):
            fpos = (i + (0.5 if row == 1 else (0.25 if row == 2 else 0.0))) / (h["bang_count"] - 1)
            x = -span + 2 * span * fpos + (rng.random() - 0.5) * 0.006
            curve = (x / span) ** 2
            near = capV[np.abs(capV[:, 0] - x) < 0.008]
            z_edge = near[near[:, 1] < hi["center"][1] - 0.04][:, 2].min() if len(near) else hi["brow_top"] + 0.05
            z_root = z_edge + 0.03 + 0.006 * row + rng.random() * 0.014
            z_mid = hi["brow_top"] + 0.01 + rng.random() * 0.006
            tip_z = hi["brow_z"] - h["bang_past_brow"] + 0.012 * curve - rng.random() * 0.012 + 0.005 * row
            out = h["bang_clear"] + out_add
            sweep = (rng.random() - 0.5) * 0.016 + 0.01 * np.sign(x) * curve
            root, n0 = _face_pt(capc, x * 0.9, z_root + 0.012, 0.002)
            mid, n1 = _face_pt(col_body, x * 1.0 + sweep * 0.4, z_mid, out + 0.003)
            tip, n2 = _face_pt(col_body, x * (1.03 + 0.05 * curve) + sweep, tip_z, out + 0.001 + 0.002 * rng.random())
            q1 = root * 0.45 + mid * 0.55 + n1 * 0.004
            path, _ = M.catmull_rom([root, q1, mid, tip], 9)
            path[-3:] -= _norm(n2) * np.array([0.0, 0.0005, 0.0015])[:, None]       # tips curl in a little
            wdt = h["bang_width"] * wmul * (1 - 0.15 * curve) * (0.75 + 0.45 * rng.random())
            u0 = 0.5 * (rng.random() > 0.5)
            nh = _norm(n0 + n1 + n2) + np.array([(rng.random() - 0.5) * 0.4, 0, 0])
            bang_parts.append(H.card(path, wdt, _norm(nh), window=(u0, u0 + 0.5), tip=0.25 + 0.15 * rng.random(),
                                     cup=0.002))
    bangs = _card_object("bangs", bang_parts)
    M.set_weights(bangs, {"head": np.ones(len(bangs.data.vertices))})
    pieces.append(bangs)
    # ---- face-framing strands: from the temples, in front of the ears, past the jaw (2 cards each)
    for s, sg in (("l", 1.0), ("r", -1.0)):
        ear = hi["ear_" + s]
        y0 = ear[1] - 0.03
        p0, n0 = _side_pt(col_body, sg, y0 - 0.008, hi["brow_top"] + 0.03, 0.004)
        p1, n1 = _side_pt(col_body, sg, y0 - 0.012, hi["eye_l"][2] - 0.01, 0.011)
        p2, n2 = _side_pt(col_body, sg, y0 - 0.006, hi["chin_z"] + 0.025, 0.014)
        p3 = p2 + np.array([sg * 0.012, 0.004, -h["strand_drop"]])
        path, L = M.catmull_rom([p0, p1, p2, p3], 18)
        cps = []
        for k, (wmul, dx, dy, u0) in enumerate(((1.0, 0.0, 0.0, 0.0), (0.7, sg * 0.004, -0.004, 0.5),
                                                (0.55, sg * 0.002, 0.005, 0.0))):
            pk = path + np.array([dx, dy, 0.0]) * np.linspace(0.3, 1.0, len(path))[:, None]
            pk[:, 2] -= 0.012 * k * np.linspace(0, 1, len(path))
            cps.append(H.card(pk, h["strand_width"] * wmul, _norm(n1) * np.array([1, 1, 0.2]),
                              window=(u0, u0 + 0.5), tip=0.22, cup=0.0025))
        ob = _card_object("strand_" + s, cps)
        names = ["strand_%s_01" % s, "strand_%s_02" % s]
        bounds = [0, L * 0.45, L]
        pts = _path_points(path, bounds)
        R.add_chain(rig, names, pts, "head", roll_up=(0, -1, 0), rest=cfg.get("rest_chains"))
        Pc = M.co(ob)
        seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
        sp = np.r_[0, np.cumsum(seg)]
        arc = sp[np.argmin(((Pc[:, None, :] - path[None]) ** 2).sum(-1), axis=1)]
        M.set_weights(ob, M.normalize_limit(R.chain_weights(arc, bounds, names, "head", 0.04), 8))
        pieces.append(ob)
        info["strand_" + s] = {"length_m": round(L, 3)}
    # ---- loose braid from the nape
    nape_z = hi["ear_l"][2] - h["nape_down"]
    c0 = _back(capc, 0.0, nape_z, -0.008)
    c1 = c0 + np.array([0.0, 0.016, -0.055])
    c2 = _back(col_all, 0.004, zn - 0.03, h["clear"] + 0.01)
    c3 = _back(col_all, 0.01, zc - 0.12, h["clear"])
    c4 = _back(col_all, 0.016, zc - 0.28, h["clear"])
    c5 = _back(col_all, 0.012, zc - h["drop"], h["clear"])
    names = ["braid_%02d" % k for k in range(1, 6)]
    ctrl = R.rest_points(cfg.get("rest_chains"), names) or [c0, c1, c2, c3, c4, c5]
    parts_, arcs, desc = H.braid(ctrl, col_all, depth_hint=(0, 1.0, 0.05),
                                 width=tuple(h["width"]), period=h["period"], tassel=h["tassel"],
                                 amp_lat=0.33, amp_depth=0.2, r_lat=0.4, r_depth=0.27, loose=0.6, seed=5)
    ob, arc = _tube_object("braid", parts_, arcs, H.P_BRAID, H.P_TIE)
    L = desc["length"]
    rp = R.rest_points(cfg.get("rest_chains"), names)
    if rp is not None:                     # weights follow the stored joints projected onto the path
        bp_ = desc["path"]
        sp_ = np.r_[0, np.cumsum(np.linalg.norm(np.diff(bp_, axis=0), axis=1))]
        bounds = [float(sp_[np.argmin(np.linalg.norm(bp_ - j, axis=1))]) for j in rp]
        bounds[0], bounds[-1] = 0.0, L
    else:
        bounds = list(np.linspace(0, L, 6))
    pts = _path_points(desc["path"], bounds)
    R.add_chain(rig, names, pts, "head", roll_up=(1, 0, 0), rest=cfg.get("rest_chains"))
    M.set_weights(ob, M.normalize_limit(R.chain_weights(arc, bounds, names, "head", 0.04), 8))
    pieces.append(ob)
    # flyaway cards along the braid and a splayed tassel
    bp = desc["path"]
    seg = np.linalg.norm(np.diff(bp, axis=0), axis=1)
    sp = np.r_[0, np.cumsum(seg)]
    fly = []
    farc = []
    n_fly = int(L / (h["period"] * 0.5))
    for k in range(n_fly):
        a0 = (k + 0.5) / n_fly * L * 0.95 + 0.02
        i0 = int(np.searchsorted(sp, a0))
        i1 = int(np.searchsorted(sp, min(a0 + 0.06 + 0.04 * rng.random(), sp[-1])))
        if i1 - i0 < 3:
            continue
        side = (-1) ** k
        Tv = bp[min(i0 + 1, len(bp) - 1)] - bp[i0]
        Tv /= np.linalg.norm(Tv)
        lat = np.cross(Tv, [0, 1.0, 0])
        lat /= max(np.linalg.norm(lat), 1e-6)
        sub = bp[i0:i1 + 1].copy()
        tt = np.linspace(0, 1, len(sub))[:, None]
        sub = sub + lat * side * (h["width"][0] * 0.42 + 0.006 * tt) + np.array([0, 0.012, 0]) * (1 - tt) * 0.5
        path, _ = M.catmull_rom(sub[::max(1, len(sub) // 4)].tolist() + [sub[-1].tolist()], 6)
        u0 = 0.5 * (rng.random() > 0.5)
        fly.append(H.card(path, 0.014 + 0.008 * rng.random(), np.array([0, 1.0, 0.1]), window=(u0, u0 + 0.5),
                          tip=0.2, cup=0.001))
        farc.append(np.repeat(sp[i0] + np.linspace(0, sp[i1] - sp[i0], len(path)), 3))
    # nape gather: cards from the occipital hair into the braid's top
    for k in range(7):
        ang = (k - 3) / 3.0
        start = _onto(capc, np.array([ang * 0.05, hi["center"][1] + 0.07, hi["ear_l"][2] + 0.02 + 0.015 * (1 - abs(ang))]),
                      inset=-0.004)
        end = bp[int(np.searchsorted(sp, 0.05))] + np.array([ang * 0.008, 0.004, 0])
        mid = 0.5 * (start + end)
        mid = _onto(capc, mid, inset=-0.005)
        path, _ = M.catmull_rom([start, mid, end], 7)
        u0 = 0.5 * (k % 2)
        fly.append(H.card(path, 0.026, _norm(np.array([0, 1.0, 0.25])), window=(u0, u0 + 0.5), tip=0.55, cup=0.002))
        farc.append(np.zeros(len(path) * 3))
    flo = _card_object("braid_cards", fly)
    arcv = np.concatenate(farc)
    M.set_weights(flo, M.normalize_limit(R.chain_weights(arcv, bounds, names, "head", 0.04), 8))
    pieces.append(flo)
    info["braid"] = {"length_m": round(L, 3), "periods_in_v": desc["periods_in_v"], "flyaway_cards": len(farc)}
    return _finish(pieces, parts, cfg), info


def _finish(pieces, parts, cfg):
    H.remap_card(parts["brows"], H.BROW, H.P_BROW)
    H.remap_card(parts["lashes"], H.LASH, H.P_LASH)
    for ob in pieces:
        for a in list(ob.data.attributes):
            if a.name == "src_vi":
                ob.data.attributes.remove(a)
    hair = M.join(pieces + [parts["brows"], parts["lashes"]], cfg["name"] + "_Hair")
    return hair
