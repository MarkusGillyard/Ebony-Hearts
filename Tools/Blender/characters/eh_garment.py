"""Garment construction shared by both fighters: shells grown from body regions (they inherit the
body's skin weights and UVs exactly, so they move with the skin), offset fields, cloth-like tension
relaxation against the body, hems, removal of the body faces a garment hides, and a deterministic
UV island packer for material atlases."""
import math

import bpy
import numpy as np

import eh_mesh as M


def body_frame(rig):
    """Landmarks used by every garment (armature space, metres)."""
    B = {b.name: (np.array(b.head_local), np.array(b.tail_local)) for b in rig.data.bones}
    f = {k: v for k, v in B.items()}
    f["z_clav"] = B["clavicle_l"][0][2]
    f["z_pelvis"] = B["pelvis"][0][2]
    f["z_hip"] = B["thigh_l"][0][2]
    f["z_knee"] = B["calf_l"][0][2]
    f["z_ankle"] = B["foot_l"][0][2]
    f["z_neck"] = B["neck_01"][0][2]
    f["z_head"] = B["head"][0][2]
    f["z_top"] = B["head"][1][2]
    return f


def spine_y(rig, z):
    """Y of the spine line at height z (interpolated through pelvis..head heads)."""
    names = ["pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head"]
    zs = np.array([rig.data.bones[n].head_local[2] for n in names])
    ys = np.array([rig.data.bones[n].head_local[1] for n in names])
    return np.interp(z, zs, ys)


def limb_param(rig, bone, P):
    b = rig.data.bones[bone]
    h, t = np.array(b.head_local), np.array(b.tail_local)
    d = t - h
    tt = ((P - h) @ d) / (d @ d)
    foot = h + np.outer(tt, d)
    r = np.linalg.norm(P - foot, axis=1)
    return tt, r, foot


def wsum(W, names):
    out = None
    for n in names:
        if n in W:
            out = W[n].copy() if out is None else out + W[n]
    if out is None:
        out = np.zeros(len(next(iter(W.values()))))
    return out


def side_names(base, s):
    return ["%s_%s" % (b, s) for b in base]


ARM = ["clavicle", "upperarm", "upperarm_twist_01", "lowerarm", "lowerarm_twist_01", "hand"]
HAND = ["hand", "thumb_01", "thumb_02", "thumb_03", "index_01", "index_02", "index_03", "middle_01",
        "middle_02", "middle_03", "ring_01", "ring_02", "ring_03", "pinky_01", "pinky_02", "pinky_03"]
LEG = ["thigh", "thigh_twist_01", "calf", "foot", "ball"]


def drop_small_islands(g, min_faces=24):
    """Removes disconnected scraps a region selection can leave (tiny islands of faces)."""
    ls, lt, lv = M.polys(g)
    nf = len(ls)
    parent = np.arange(len(g.data.vertices))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for e in M.edges(g):
        ra, rb = find(int(e[0])), find(int(e[1]))
        if ra != rb:
            parent[ra] = rb
    root = np.array([find(i) for i in range(len(parent))])
    froot = root[lv[ls]]
    ids, counts = np.unique(froot, return_counts=True)
    small = set(ids[counts < min_faces].tolist())
    if small and len(ids) > 1:
        M.delete_faces(g, np.array([r in small for r in froot]))


def smooth_boundaries(g, V, iters=10, collider=None, min_d=None, clamp=0.007):
    """Taubin smoothing along every open boundary loop (no shrinkage): removes the stair steps a
    face-based selection leaves on necklines, hems and openings. Keeps the edge off the collider."""
    loops = M.boundary_loops(g)
    V0 = V.copy()
    E = set(map(tuple, np.sort(M.boundary_edges(g), axis=1).tolist()))
    for _ in range(iters):
        for lam in (0.5, -0.53):
            for lp in loops:
                if len(lp) < 4:
                    continue
                closed = tuple(sorted((int(lp[0]), int(lp[-1])))) in E
                P = V[lp]
                if closed:
                    avg = 0.5 * (np.roll(P, 1, 0) + np.roll(P, -1, 0))
                    V[lp] = P + lam * (avg - P)
                else:
                    avg = 0.5 * (P[:-2] + P[2:])
                    V[lp[1:-1]] = P[1:-1] + lam * (avg - P[1:-1])
        if collider is not None:
            b = np.unique(np.concatenate(loops))
            V[b], _ = collider.push_out(V[b], min_d[b] if min_d is not None else 0.0)
    if loops:
        b = np.unique(np.concatenate(loops))
        d = V[b] - V0[b]
        n = np.linalg.norm(d, axis=1, keepdims=True)
        V[b] = V0[b] + d * np.minimum(1.0, clamp / np.maximum(n, 1e-9))
    return V


def shell(body, vmask, name, offset, collider=None, relax_iters=0, relax_factor=0.5,
          smooth_offset=3, lip=0.0, min_frac=0.85, extra_push=None, edge_smooth=10, presmooth=0, cuts=(),
          edge_clamp=0.007):
    """Garment surface over the body faces whose vertices are all in vmask.

    offset: scalar or per-body-vertex array (metres along the body normal). Returns
    (garment object, src body vertex index per garment vertex, body face mask used)."""
    fmask = M.face_mask_from_verts(body, vmask, "all")
    g, src = M.extract(body, fmask, name)
    drop_small_islands(g)
    src = get_attr(g, "src_vi", np.int64)
    N = M.vnormals(body)[src]
    off = np.broadcast_to(np.asarray(offset, float), (len(body.data.vertices),))[src].copy()
    adj = M.adjacency(g)
    if smooth_offset:
        off = M.smooth(off, adj, smooth_offset, 0.5)
    V = M.co(g) + N * off[:, None]
    if extra_push is not None:
        V = V + extra_push(V, src)
    if presmooth:
        V = M.smooth(V, adj, presmooth, 0.5)
    if relax_iters and collider is not None:
        V = M.relax_shell(V, adj, collider, off * min_frac, iters=relax_iters, factor=relax_factor,
                          pinned=M.boundary_vmask(g))
    if edge_smooth:
        V = smooth_boundaries(g, V, edge_smooth, collider, off * min_frac, clamp=edge_clamp)
    M.set_co(g, V)
    for point, normal in cuts:
        M.bisect_keep(g, point, normal)
    n0 = len(g.data.vertices)
    if lip:
        M.add_boundary_lip(g, lip)
    lipf = np.zeros(len(g.data.vertices), np.float32)
    lipf[n0:] = 1
    set_float_attr(g, "lip", lipf)
    for a in list(g.data.attributes):
        if a.name.startswith("reg_"):
            g.data.attributes.remove(a)
    g.data.materials.clear()
    return g, src, fmask


def hidden_face_mask(body, fmask, margin_rings=2, garment=None, margin_m=0.012):
    """Body faces hidden by a garment. With `garment`, a body vertex counts as hidden only if a ray
    along its normal hits the garment within 4 cm and it lies more than margin_m from the garment's
    final edge; a face is removed only when all its vertices are hidden (and it is in fmask)."""
    if garment is not None:
        from mathutils import Vector
        from mathutils.kdtree import KDTree
        Vg = M.co(garment)
        edge = M.boundary_vmask(garment) | (get_attr(garment, "lip") > 0.5)
        pts = Vg[edge]
        kd = KDTree(max(len(pts), 1))
        for i, p in enumerate(pts):
            kd.insert(p, i)
        kd.balance()
        col = M.Collider([garment])
        Vb = M.co(body)
        Nb = M.vnormals(body)
        ls, lt, lv = M.polys(body)
        fidx = np.repeat(np.arange(len(ls)), lt)
        cand = np.zeros(len(Vb), bool)
        cand[lv[fmask[fidx]]] = True
        hid = np.zeros(len(Vb), bool)
        for i in np.nonzero(cand)[0]:
            p = Vb[i]
            r = col.bvh.ray_cast(Vector(p - Nb[i] * 0.002), Vector(Nb[i]), 0.04)
            if r[0] is not None and (len(pts) == 0 or kd.find(p)[2] > margin_m):
                hid[i] = True
        return fmask & M.face_mask_from_verts(body, hid, "all")
    adj = M.adjacency(body)
    covered_v = np.zeros(len(body.data.vertices), bool)
    ls, lt, lv = M.polys(body)
    fidx = np.repeat(np.arange(len(ls)), lt)
    covered_v[lv[fmask[fidx]]] = True
    edge_v = covered_v & M.grow_vmask(adj, ~covered_v, 1)
    keep_v = M.grow_vmask(adj, edge_v, margin_rings)
    keep_f = M.face_mask_from_verts(body, keep_v, "any")
    return fmask & ~keep_f


def weights_cleanup(ob, limit=8, smooth_iters=0):
    W = M.weights(ob)
    if smooth_iters:
        W = M.smooth_weights(W, M.adjacency(ob), smooth_iters, 0.5)
    W = M.normalize_limit(W, limit)
    M.set_weights(ob, W)
    return W


# ----------------------------------------------------------------------------- UV islands

def uv_islands(ob, uv_name="UVMap"):
    """Face islands: faces sharing a (vertex, uv) corner belong together. Returns face->island ids."""
    ls, lt, lv = M.polys(ob)
    uv = M.loop_uvs(ob, uv_name)
    nf = len(ls)
    parent = np.arange(nf)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    key = {}
    fidx = np.repeat(np.arange(nf), lt)
    kq = np.round(uv * 2 ** 16).astype(np.int64)
    for li in range(len(lv)):
        k = (int(lv[li]), int(kq[li, 0]), int(kq[li, 1]))
        f = int(fidx[li])
        if k in key:
            ra, rb = find(f), find(key[k])
            if ra != rb:
                parent[ra] = rb
        else:
            key[k] = f
    roots = np.array([find(i) for i in range(nf)])
    _, ids = np.unique(roots, return_inverse=True)
    return ids


def pack_uvs(objs, uv_name="UVMap", margin=0.006, island_scale=None, rotate=True):
    """Deterministic shelf packer over the islands of several objects (one shared atlas).

    Islands are first scaled to a common texel density (3D area / UV area), optionally multiplied by
    island_scale(ob, face_ids, island_id) -> factor, rotated to their minimum bounding box, then shelf
    packed into 0..1 with a binary-searched global scale."""
    isl = []
    for oi, ob in enumerate(objs):
        uv = M.loop_uvs(ob, uv_name)
        ls, lt, lv = M.polys(ob)
        ids = uv_islands(ob, uv_name)
        V = M.co(ob)
        fidx = np.repeat(np.arange(len(ls)), lt)
        for k in range(ids.max() + 1 if len(ids) else 0):
            faces = np.nonzero(ids == k)[0]
            loops = np.nonzero(np.isin(fidx, faces))[0]
            # density
            a3 = a2 = 0.0
            for f in faces:
                s, t = ls[f], lt[f]
                p = V[lv[s:s + t]]
                q = uv[s:s + t]
                for j in range(1, t - 1):
                    a3 += 0.5 * np.linalg.norm(np.cross(p[j] - p[0], p[j + 1] - p[0]))
                    e1, e2 = q[j] - q[0], q[j + 1] - q[0]
                    a2 += 0.5 * abs(e1[0] * e2[1] - e1[1] * e2[0])
            if a2 < 1e-12:
                continue
            dens = math.sqrt(a3 / a2)
            if island_scale is not None:
                dens *= island_scale(ob, faces, k)
            pts = (uv[loops] - uv[loops].mean(0)) * dens
            best = (1e9, 0.0)
            if rotate:
                for ang in np.radians(np.arange(0, 180, 7.5)):
                    c, s_ = math.cos(ang), math.sin(ang)
                    r = pts @ np.array([[c, -s_], [s_, c]]).T
                    ext = r.max(0) - r.min(0)
                    area = ext[0] * ext[1] + 0.001 * ext[1]
                    if area < best[0] - 1e-9:
                        best = (area, ang)
            c, s_ = math.cos(best[1]), math.sin(best[1])
            r = pts @ np.array([[c, -s_], [s_, c]]).T
            if np.ptp(r[:, 0]) < np.ptp(r[:, 1]):     # lay islands wide
                r = r[:, ::-1] * np.array([1, -1])
            r -= r.min(0)
            isl.append({"obj": oi, "loops": loops, "pts": r, "w": r[:, 0].max(), "h": r[:, 1].max()})
    order = sorted(range(len(isl)), key=lambda i: -isl[i]["h"])

    def place(scale):
        x = y = row_h = 0.0
        pos = {}
        for i in order:
            w, h = isl[i]["w"] * scale, isl[i]["h"] * scale
            if w + 2 * margin > 1.0:
                return None
            if x + w + margin > 1.0:
                x = 0.0
                y += row_h + margin
                row_h = 0.0
            pos[i] = (x + margin, y + margin)
            x += w + margin
            row_h = max(row_h, h)
        if y + row_h + 2 * margin > 1.0:
            return None
        return pos

    lo, hi = 1e-4, 100.0
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        if place(mid) is None:
            hi = mid
        else:
            lo = mid
    pos = place(lo)
    new = [M.loop_uvs(ob, uv_name).copy() for ob in objs]
    for i, (px, py) in pos.items():
        d = isl[i]
        new[d["obj"]][d["loops"]] = d["pts"] * lo + np.array([px, py])
    for ob, uv in zip(objs, new):
        M.set_loop_uvs(ob, uv, uv_name)
    return lo


def uv_scale_m(ob, uv_name="UVMap"):
    """Metres of surface per UV unit (sqrt of area ratio) for tiling sampled detail."""
    ls, lt, lv = M.polys(ob)
    uv = M.loop_uvs(ob, uv_name)
    V = M.co(ob)
    a3 = a2 = 0.0
    for f in range(0, len(ls), max(1, len(ls) // 2000)):
        s, t = ls[f], lt[f]
        p = V[lv[s:s + t]]
        q = uv[s:s + t]
        for j in range(1, t - 1):
            a3 += 0.5 * np.linalg.norm(np.cross(p[j] - p[0], p[j + 1] - p[0]))
            e1, e2 = q[j] - q[0], q[j + 1] - q[0]
            a2 += 0.5 * abs(e1[0] * e2[1] - e1[1] * e2[0])
    return math.sqrt(a3 / max(a2, 1e-12))


def set_part_attr(ob, name, value):
    """Integer per-vertex 'part' tag (used by painters to tell garment pieces apart)."""
    a = ob.data.attributes.get(name) or ob.data.attributes.new(name, "INT", "POINT")
    v = np.broadcast_to(np.asarray(value, np.int32), (len(ob.data.vertices),)).copy()
    a.data.foreach_set("value", v)


def get_attr(ob, name, dtype=np.float32, default=0):
    a = ob.data.attributes.get(name)
    n = len(ob.data.vertices)
    if a is None:
        return np.full(n, default, dtype)
    v = np.empty(n, np.int32 if a.data_type == "INT" else np.float32)
    a.data.foreach_get("value", v)
    return v.astype(dtype)


def set_float_attr(ob, name, values):
    a = ob.data.attributes.get(name) or ob.data.attributes.new(name, "FLOAT", "POINT")
    a.data.foreach_set("value", np.asarray(values, np.float32))
