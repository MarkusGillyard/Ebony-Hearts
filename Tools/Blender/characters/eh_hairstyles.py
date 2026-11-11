"""The two canon hairstyles, assembled from eh_hair pieces, with their secondary bone chains.

Wren: long brown hair, centre part, two neat braids from behind the ears down the upper back
      (chains braid_l_01..04, braid_r_01..04 under head).
Ashka: long, silky crimson hair with waves toward the ends, swept back into one loose ponytail tied with a small
      black ribbon at the nape (sheet v2 of 2026-11-09; it rides the former braid's chain, braid_01..05 under head,
      so the skeleton is unchanged), soft, slightly parted bangs ending just past the eyebrows, two longer
      face-framing strands (strand_l_01..02, strand_r_01..02 under head)."""
import math

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
    """Bangs just past the eyebrows and two longer face-framing side bangs are layered alpha cards
    (strand clumps, tapered tips). The loose ponytail (character sheet of 2026-11-09) is a soft core
    under layered strand cards of varied length, gathered by a hair tie at the nape, with cards from
    the occipital hair into the tie. It follows the shipped braid_01..05 chain (same bones, same rest
    pose), so every clip keeps working."""
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
            # sheet v2: slightly parted at the centre (the middle cards step aside, sweeping away from the part)
            near_c = max(0.0, 1 - abs(x) / span)
            x += math.copysign(0.5 * h.get("bang_part", 0.0) * near_c, x)
            curve = (x / span) ** 2
            near = capV[np.abs(capV[:, 0] - x) < 0.008]
            z_edge = near[near[:, 1] < hi["center"][1] - 0.04][:, 2].min() if len(near) else hi["brow_top"] + 0.05
            z_root = z_edge + 0.03 + 0.006 * row + rng.random() * 0.014
            z_mid = hi["brow_top"] + 0.01 + rng.random() * 0.006
            tip_z = hi["brow_z"] - h["bang_past_brow"] + 0.012 * curve - rng.random() * 0.012 + 0.005 * row
            out = h["bang_clear"] + out_add
            sweep = (rng.random() - 0.5) * 0.016 + 0.01 * np.sign(x) * curve + 0.008 * np.sign(x) * near_c ** 2
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
    # ---- loose ponytail from the nape (on the shipped braid_01..05 chain)
    nape_z = hi["ear_l"][2] - h["nape_down"]
    c0 = _back(capc, 0.0, nape_z, -0.008)
    c1 = c0 + np.array([0.0, 0.016, -0.055])
    c2 = _back(col_all, 0.004, zn - 0.03, h["clear"] + 0.01)
    c3 = _back(col_all, 0.01, zc - 0.12, h["clear"])
    c4 = _back(col_all, 0.016, zc - 0.28, h["clear"])
    c5 = _back(col_all, 0.012, zc - h["drop"], h["clear"])
    names = ["braid_%02d" % k for k in range(1, 6)]          # bone names kept from the braid: skeleton unchanged
    rest = cfg.get("rest_chains")
    ctrl = R.rest_points(rest, names) or [c0, c1, c2, c3, c4, c5]
    pt = h["ponytail"]
    n = 64
    path, L = M.catmull_rom(ctrl, n)
    for _ in range(3):                                      # keep the tail off the shirt and the back
        path, _ = col_all.push_out(path, pt["depth"] * pt["width_max"] + h["clear"])
        path = np.vstack([path[:1], M.smooth(path, H._chain_adj(len(path)), 1, 0.5)[1:-1], path[-1:]])
    path, L = M.catmull_rom(path[::max(1, len(path) // 24)].tolist() + [path[-1].tolist()], n)
    sp = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    Tv = np.gradient(path, axis=0)
    Tv /= np.linalg.norm(Tv, axis=1, keepdims=True)
    Dv = np.array([0.0, 1.0, 0.05]) - Tv * (Tv @ np.array([0.0, 1.0, 0.05]))[:, None]   # away from the back
    Dv /= np.linalg.norm(Dv, axis=1, keepdims=True)
    Lv = np.cross(Tv, Dv)
    tie_s = pt["tie_at"]
    # half-width: pinched at the tie, swelling just below it, tapering to a soft end
    w = np.where(sp < tie_s, pt["width_tie"],
                 pt["width_tie"] + (pt["width_max"] - pt["width_tie"]) * M.smoothstep(tie_s, tie_s + 0.07, sp))
    w = w * (1 - (1 - pt["width_tip"] / pt["width_max"]) * M.smoothstep(0.3 * L, L, sp))
    rng_p = np.random.default_rng(11)
    sway = (np.sin(sp * 19.0 + 1.3) * 0.25 + np.sin(sp * 37.0) * 0.12) * w * 0.25      # a loose, uneven fall
    # sheet v2: silky waves toward the ends (soft S-bends that grow from wave_start of the length to the tip)
    wave_ramp = M.smoothstep(pt.get("wave_start", 1.0) * L, L, sp)
    wph = sp * (2 * math.pi / pt.get("wave_period", 0.075))
    wave = pt.get("wave_amp", 0.0) * wave_ramp
    core_path = path + Lv * (sway + wave * np.sin(wph + 0.6))[:, None] + Dv * (0.35 * wave * np.cos(wph + 0.6))[:, None]
    verts, faces, uvs = M.tube(core_path, w * 0.82, w * pt["depth"] * 0.82, 10, Lv, Dv, cap_start=False, cap_end=True)
    uvs = [[tuple(H.rect_map(np.array([uv]), H.BRAID)[0]) for uv in f] for f in uvs]
    core = M.make_object("ponytail_core", *M.merge_parts([(verts, faces, uvs)])[:3])
    G.set_part_attr(core, "part", np.full(len(core.data.vertices), H.P_BRAID, np.int32))
    core_arc = np.r_[np.repeat(sp, 10), sp[-1]]
    # layered strand cards around the core, each its own length, splaying slightly towards the ends
    cards, carc = [], []
    nc = pt["cards"]
    for k in range(nc):
        ang = 2 * math.pi * (k + 0.5 * rng_p.random()) / nc
        lat_c, dep_c = math.cos(ang), math.sin(ang)
        a_end = L * (0.72 + 0.34 * rng_p.random())
        i_end = int(np.searchsorted(sp, min(a_end, sp[-1])))
        i_beg = int(np.searchsorted(sp, tie_s * (0.6 + 0.8 * rng_p.random())))
        if i_end - i_beg < 6:
            continue
        idx = np.arange(i_beg, i_end + 1)
        tt = (sp[idx] - sp[i_beg]) / max(sp[i_end] - sp[i_beg], 1e-6)
        spread = 1.0 + 0.22 * tt + 0.08 * rng_p.random()
        off = (Lv[idx] * (lat_c * w[idx] * spread)[:, None]
               + Dv[idx] * (dep_c * w[idx] * pt["depth"] * spread + 0.0015)[:, None])
        # each strand clump waves a little out of step with the others
        off += Lv[idx] * (0.3 * wave[idx] * np.sin(wph[idx] * 1.3 + ang * 2.0))[:, None]
        cp = core_path[idx] + off
        cp = cp[::max(1, len(cp) // 28)].tolist() + [cp[-1].tolist()]
        cpath, _ = M.catmull_rom(cp, max(10, len(cp)))
        nrm = Lv[idx[len(idx) // 2]] * lat_c + Dv[idx[len(idx) // 2]] * dep_c
        u0 = 0.5 * (rng_p.random() > 0.5)
        cards.append(H.card(cpath, pt["card_width"] * (0.8 + 0.4 * rng_p.random()), _norm(nrm),
                            window=(u0, u0 + 0.5), tip=0.2 + 0.15 * rng_p.random(), cup=0.0015))
        carc.append(np.repeat(np.linspace(sp[i_beg], sp[i_end], len(cpath)), 3))
    # hair tie: a short band round the gather point
    i_t = int(np.searchsorted(sp, tie_s))
    band = core_path[max(i_t - 1, 0):i_t + 2]
    tv, tf, tuv = M.tube(band, np.full(len(band), pt["width_tie"] * 1.12), np.full(len(band), pt["width_tie"] * pt["depth"] * 1.25),
                         12, Lv[max(i_t - 1, 0):i_t + 2], Dv[max(i_t - 1, 0):i_t + 2], cap_start=False, cap_end=False)
    tuv = [[tuple(H.rect_map(np.array([uv]), H.TIE)[0]) for uv in f] for f in tuv]
    tie_ob = M.make_object("ponytail_tie", *M.merge_parts([(tv, tf, tuv)])[:3])
    G.set_part_attr(tie_ob, "part", np.full(len(tie_ob.data.vertices), H.P_TIE, np.int32))
    # weights follow the stored joints projected onto the path
    rp = R.rest_points(rest, names)
    if rp is not None:
        bounds = [float(sp[np.argmin(np.linalg.norm(path - j, axis=1))]) for j in rp]
        bounds[0], bounds[-1] = 0.0, L
    else:
        bounds = list(np.linspace(0, L, 6))
    pts = _path_points(path, bounds)
    R.add_chain(rig, names, pts, "head", roll_up=(1, 0, 0), rest=rest)
    M.set_weights(core, M.normalize_limit(R.chain_weights(core_arc, bounds, names, "head", 0.04), 8))
    M.set_weights(tie_ob, M.normalize_limit(R.chain_weights(np.full(len(tie_ob.data.vertices), tie_s), bounds, names, "head", 0.04), 8))
    bow = _ribbon_bow(core_path, Lv, Dv, Tv, i_t, pt)
    M.set_weights(bow, M.normalize_limit(R.chain_weights(np.full(len(bow.data.vertices), tie_s), bounds, names, "head", 0.04), 8))
    pieces += [core, tie_ob, bow]
    # nape gather: cards from the occipital hair into the tie
    for k in range(9):
        ang = (k - 4) / 4.0
        start = _onto(capc, np.array([ang * 0.055, hi["center"][1] + 0.07, hi["ear_l"][2] + 0.02 + 0.017 * (1 - abs(ang))]),
                      inset=-0.004)
        end = core_path[i_t] + Lv[i_t] * ang * pt["width_tie"] * 0.8 + Dv[i_t] * 0.002
        mid = _onto(capc, 0.5 * (start + end), inset=-0.005)
        gpath, _ = M.catmull_rom([start, mid, end], 7)
        u0 = 0.5 * (k % 2)
        cards.append(H.card(gpath, 0.028, _norm(np.array([0, 1.0, 0.25])), window=(u0, u0 + 0.5), tip=0.55, cup=0.002))
        carc.append(np.zeros(len(gpath) * 3))
    flo = _card_object("ponytail_cards", cards)
    M.set_weights(flo, M.normalize_limit(R.chain_weights(np.concatenate(carc), bounds, names, "head", 0.04), 8))
    pieces.append(flo)
    info["ponytail"] = {"length_m": round(float(L), 3), "cards": len(carc), "tie_at_m": tie_s}
    return _finish(pieces, parts, cfg), info


def _ribbon_strip(path, width_dir, widths, thick=0.0007):
    """A flat ribbon (a thin elliptical tube) along path; width_dir is per point, in the ribbon's plane."""
    Tg = np.gradient(path, axis=0)
    Tg /= np.linalg.norm(Tg, axis=1, keepdims=True)
    Wd = width_dir - Tg * (width_dir * Tg).sum(1, keepdims=True)
    Wd /= np.linalg.norm(Wd, axis=1, keepdims=True)
    Nd = np.cross(Tg, Wd)
    v, f, uv = M.tube(path, 0.5 * np.asarray(widths), np.full(len(path), thick), 8, Wd, Nd, cap_start=True, cap_end=True)
    uv = [[tuple(H.rect_map(np.array([q]), H.TIE)[0]) for q in face] for face in uv]
    return v, f, uv


def _ribbon_bow(core_path, Lv, Dv, Tv, i_t, pt):
    """Sheet v2: the ponytail is tied with a black ribbon; a small bow on the back of the gather, two flat
    loops out to the sides and two tails hanging down over the ponytail (the hair tie's black, part P_TIE)."""
    K = core_path[i_t] + Dv[i_t] * (pt["width_tie"] * pt["depth"] * 1.25 + 0.002)
    L, D, T = Lv[i_t], Dv[i_t], Tv[i_t]          # sideways, away from the back, down the tail
    rw, loop, tail = pt["ribbon_width"], pt["ribbon_loop"], pt["ribbon_tail"]
    parts = []
    for sg in (1.0, -1.0):
        # a flattened loop: out along the front layer, round the fold, back along the rear layer
        t = np.linspace(0, 1, 24)
        a = np.sin(math.pi * t) * loop * (0.55 + 0.45 * np.sin(0.5 * math.pi * t))
        lift = -0.25 * loop * np.sin(math.pi * t)
        sep = 0.0045 * np.sin(math.pi * t) * np.cos(math.pi * t)
        path = K + np.outer(sg * a, L) + np.outer(lift, T) + np.outer(sep + 0.0015, D)
        widths = rw * (0.75 + 0.6 * np.sin(math.pi * t))
        wdir = np.tile(T - 0.3 * D, (len(path), 1))
        parts.append(_ribbon_strip(path, wdir, widths))
        # a tail, slightly splayed, with a little wave and a tapered end
        s = np.linspace(0, 1, 16)
        tpath = (K + np.outer(sg * (0.004 + 0.016 * s), L) + np.outer(0.004 + tail * s, T)
                 + np.outer(0.002 + 0.004 * np.sin(math.pi * s) + 0.002 * np.sin(5 * s + sg), D))
        parts.append(_ribbon_strip(tpath, np.tile(L + 0.2 * sg * T, (len(tpath), 1)), rw * (1 - 0.45 * s ** 2)))
    # the knot: a short wrapped band across the middle of the bow
    kpath = K + np.outer(np.linspace(-1, 1, 6) * rw * 0.45, L) + np.outer(np.full(6, 0.0025), D)
    parts.append(_ribbon_strip(kpath, np.tile(T, (6, 1)), np.full(6, rw * 0.9), thick=0.0022))
    bow = M.make_object("ponytail_ribbon", *M.merge_parts(parts)[:3])
    G.set_part_attr(bow, "part", np.full(len(bow.data.vertices), H.P_TIE, np.int32))
    return bow


def _finish(pieces, parts, cfg):
    H.remap_card(parts["brows"], H.BROW, H.P_BROW)
    H.remap_card(parts["lashes"], H.LASH, H.P_LASH)
    for ob in pieces:
        for a in list(ob.data.attributes):
            if a.name == "src_vi":
                ob.data.attributes.remove(a)
    hair = M.join(pieces + [parts["brows"], parts["lashes"]], cfg["name"] + "_Hair")
    return hair
