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
        R.add_chain(rig, names, pts, "head", roll_up=(sg, 0, 0))
        M.set_weights(ob, M.normalize_limit(R.chain_weights(arc, bounds, names, "head", 0.04, s_leave), 8))
        pieces.append(ob)
        info["braid_" + s] = {"length_m": round(L, 3), "on_head_m": round(s_leave, 3),
                              "hanging_m": round(L - s_leave, 3), "periods_in_v": desc["periods_in_v"]}
    return _finish(pieces, parts, cfg), info


def ashka(body, rig, parts, garments, cfg):
    h = cfg["hair"]
    hi = head_extras(body, H.head_info(body, rig, parts))
    col_body = M.Collider([body])
    cap = H.cap(body, rig, hi, col_body, "back", thick=h["cap_thickness"], grow=2)
    col_head = M.Collider([body, cap, parts["brows"]])
    col_all = M.Collider([body, cap] + garments)
    zc = rig.data.bones["clavicle_l"].head_local[2]
    zn = rig.data.bones["neck_01"].head_local[2]
    pieces = [cap]
    info = {}
    # ---- bangs: two staggered rows of wide, thin clumps that follow the forehead, tips just past
    # the eyebrows (offsets are explicit, so nothing is pushed around by collision)
    rng = np.random.default_rng(7)
    bang_parts, bang_arcs = [], []
    span = h["bang_span"]
    capV = M.co(cap)
    for row, n in ((0, h["bang_count"]), (1, h["bang_count"] - 1)):
        for i in range(n):
            f = (i + (0.5 if row else 0.0)) / (h["bang_count"] - 1)
            x = -span + 2 * span * f
            curve = (x / span) ** 2
            near = capV[np.abs(capV[:, 0] - x) < 0.008]
            z_edge = near[near[:, 1] < hi["center"][1] - 0.04][:, 2].min() if len(near) else hi["brow_top"] + 0.05
            z_root = z_edge + 0.03
            z_mid = hi["brow_top"] + 0.012
            tip_z = hi["brow_z"] - h["bang_past_brow"] + 0.012 * curve - rng.random() * 0.006 + 0.005 * row
            out = h["bang_clear"] + 0.002 * row
            root, n0 = _face_pt(col_body, x * 0.95, z_root, 0.002)
            mid, n1 = _face_pt(col_body, x * 1.0, z_mid, out + 0.002)
            tip, n2 = _face_pt(col_body, x * (1.03 + 0.05 * curve), tip_z, out)
            q1 = root * 0.45 + mid * 0.55 + n1 * 0.003
            ctrl = [root, q1, mid, tip]
            nrm = _norm(n0 + n1 + n2)
            wdt = h["bang_width"] * (1.0 - 0.12 * row) * (1 - 0.15 * curve)
            g, arc, path, L = H.clump(ctrl, wdt, h["bang_thick"], None, 0.0, sides=8, segs=12,
                                      normal_hint=nrm, tip=0.18)
            bang_parts.append(g)
            bang_arcs.append(arc)
    bangs, _ = _tube_object("bangs", bang_parts, bang_arcs, H.P_BANG)
    w = {"head": np.ones(len(bangs.data.vertices))}
    M.set_weights(bangs, w)
    pieces.append(bangs)
    # ---- face-framing strands: from the temples, in front of the ears, past the jaw
    for s, sg in (("l", 1.0), ("r", -1.0)):
        ear = hi["ear_" + s]
        y0 = ear[1] - 0.03
        p0, n0 = _side_pt(col_body, sg, y0 - 0.008, hi["brow_top"] + 0.03, 0.004)
        p1, n1 = _side_pt(col_body, sg, y0 - 0.012, hi["eye_l"][2] - 0.01, 0.011)
        p2, n2 = _side_pt(col_body, sg, y0 - 0.006, hi["chin_z"] + 0.025, 0.014)
        p3 = p2 + np.array([sg * 0.012, 0.004, -h["strand_drop"]])
        g, arc, path, L = H.clump([p0, p1, p2, p3], h["strand_width"], h["strand_thick"], None, 0.0,
                                  sides=8, segs=18, normal_hint=_norm(n1), tip=0.15)
        ob, arc = _tube_object("strand_" + s, [g], [arc], H.P_STRAND)
        names = ["strand_%s_01" % s, "strand_%s_02" % s]
        bounds = [0, L * 0.45, L]
        pts = _path_points(path, bounds)
        R.add_chain(rig, names, pts, "head", roll_up=(0, -1, 0))
        M.set_weights(ob, M.normalize_limit(R.chain_weights(arc, bounds, names, "head", 0.04), 8))
        pieces.append(ob)
        info["strand_" + s] = {"length_m": round(L, 3)}
    # ---- loose braid from the nape
    nape_z = hi["ear_l"][2] - h["nape_down"]
    c0 = _back(M.Collider([cap]), 0.0, nape_z, -0.008)
    c1 = c0 + np.array([0.0, 0.016, -0.055])
    c2 = _back(col_all, 0.004, zn - 0.03, h["clear"] + 0.01)
    c3 = _back(col_all, 0.01, zc - 0.12, h["clear"])
    c4 = _back(col_all, 0.016, zc - 0.28, h["clear"])
    c5 = _back(col_all, 0.012, zc - h["drop"], h["clear"])
    parts_, arcs, desc = H.braid([c0, c1, c2, c3, c4, c5], col_all, depth_hint=(0, 1.0, 0.05),
                                 width=tuple(h["width"]), period=h["period"], tassel=h["tassel"],
                                 amp_lat=0.33, amp_depth=0.2, r_lat=0.4, r_depth=0.27, loose=0.6, seed=5)
    ob, arc = _tube_object("braid", parts_, arcs, H.P_BRAID, H.P_TIE)
    L = desc["length"]
    bounds = list(np.linspace(0, L, 6))
    names = ["braid_%02d" % k for k in range(1, 6)]
    pts = _path_points(desc["path"], bounds)
    R.add_chain(rig, names, pts, "head", roll_up=(1, 0, 0))
    M.set_weights(ob, M.normalize_limit(R.chain_weights(arc, bounds, names, "head", 0.04), 8))
    pieces.append(ob)
    info["braid"] = {"length_m": round(L, 3), "periods_in_v": desc["periods_in_v"]}
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
