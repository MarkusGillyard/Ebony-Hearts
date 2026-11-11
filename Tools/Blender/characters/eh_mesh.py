"""Geometry helpers for the character build: numpy access to meshes, face extraction (keeps UVs and
skin weights), adjacency smoothing, garment "tension" relaxation against a collider, boundary lips,
procedural mesh creation and skin-weight utilities."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


# ----------------------------------------------------------------------------- access

def co(ob):
    a = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def set_co(ob, a):
    ob.data.vertices.foreach_set("co", np.ascontiguousarray(a, dtype=np.float64).ravel())
    ob.data.update()


def vnormals(ob):
    ob.data.update()
    a = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("normal", a)
    return a.reshape(-1, 3)


def polys(ob):
    me = ob.data
    n = len(me.polygons)
    ls, lt = np.empty(n, np.int64), np.empty(n, np.int64)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    return ls, lt, lv


def poly_list(ob):
    ls, lt, lv = polys(ob)
    return [lv[s:s + t] for s, t in zip(ls, lt)]


def edges(ob):
    a = np.empty(len(ob.data.edges) * 2, np.int64)
    ob.data.edges.foreach_get("vertices", a)
    return a.reshape(-1, 2)


def tri_count(ob, evaluated=True):
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        ev.to_mesh_clear()
        return n
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def loop_tris(ob):
    """(tri vertex indices (n,3), tri loop indices (n,3), tri polygon index (n,))."""
    me = ob.data
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    v = np.empty(n * 3, np.int64)
    lo = np.empty(n * 3, np.int64)
    p = np.empty(n, np.int64)
    me.loop_triangles.foreach_get("vertices", v)
    me.loop_triangles.foreach_get("loops", lo)
    me.loop_triangles.foreach_get("polygon_index", p)
    return v.reshape(-1, 3), lo.reshape(-1, 3), p


def loop_uvs(ob, name=None):
    me = ob.data
    uvl = me.uv_layers[name] if name else me.uv_layers.active
    a = np.empty(len(me.loops) * 2)
    uvl.data.foreach_get("uv", a)
    return a.reshape(-1, 2)


def set_loop_uvs(ob, uv, name="UVMap"):
    me = ob.data
    uvl = me.uv_layers.get(name) or me.uv_layers.new(name=name)
    uvl.data.foreach_set("uv", np.ascontiguousarray(uv, dtype=np.float64).ravel())
    return uvl


def face_mask_from_verts(ob, vmask, mode="all"):
    ls, lt, lv = polys(ob)
    vals = vmask[lv].astype(np.int64)
    s = np.add.reduceat(vals, ls) if len(ls) else np.zeros(0)
    return (s == lt) if mode == "all" else (s > 0)


def poly_centers(ob):
    ls, lt, lv = polys(ob)
    V = co(ob)
    c = np.add.reduceat(V[lv], ls, axis=0)
    return c / lt[:, None]


# ----------------------------------------------------------------------------- adjacency

def adjacency(ob):
    """CSR vertex adjacency (indptr, indices) from mesh edges."""
    n = len(ob.data.vertices)
    E = edges(ob)
    a = np.concatenate([E[:, 0], E[:, 1]])
    b = np.concatenate([E[:, 1], E[:, 0]])
    order = np.argsort(a, kind="stable")
    a, b = a[order], b[order]
    indptr = np.zeros(n + 1, np.int64)
    np.add.at(indptr, a + 1, 1)
    indptr = np.cumsum(indptr)
    return indptr, b


def neighbour_mean(X, adj):
    indptr, idx = adj
    cnt = np.diff(indptr)
    s = np.add.reduceat(X[idx], indptr[:-1], axis=0) if len(idx) else np.zeros_like(X)
    s[cnt == 0] = X[cnt == 0]
    cnt = np.maximum(cnt, 1)
    return s / (cnt[:, None] if X.ndim == 2 else cnt)


def smooth(X, adj, iters=1, factor=0.5, fixed=None):
    X = X.copy()
    for _ in range(iters):
        m = neighbour_mean(X, adj)
        Y = X + factor * (m - X)
        if fixed is not None:
            Y[fixed] = X[fixed]
        X = Y
    return X


def boundary_edges(ob):
    me = ob.data
    E = edges(ob)
    ls, lt, lv = polys(ob)
    le = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("edge_index", le)
    cnt = np.bincount(le, minlength=len(E))
    return E[cnt == 1]


def boundary_vmask(ob):
    m = np.zeros(len(ob.data.vertices), bool)
    be = boundary_edges(ob)
    m[be.ravel()] = True
    return m


def boundary_loops(ob):
    """Ordered vertex loops along open boundaries."""
    be = boundary_edges(ob)
    nb = {}
    for a, b in be:
        nb.setdefault(int(a), []).append(int(b))
        nb.setdefault(int(b), []).append(int(a))
    seen = set()
    loops = []
    for start in nb:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = None, start
        while True:
            nxt = [x for x in nb[cur] if x != prev and x not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(np.array(loop))
    return loops


def grow_vmask(adj, mask, rings):
    indptr, idx = adj
    m = mask.copy()
    for _ in range(rings):
        src = np.repeat(np.arange(len(m)), np.diff(indptr))
        hit = np.zeros(len(m), bool)
        hit[src[m[idx]]] = True
        m = m | hit
    return m


def shrink_vmask(adj, mask, rings):
    return ~grow_vmask(adj, ~mask, rings)


def ring_distance(adj, seed, max_rings=64):
    """Edge-hop distance from the seed vertex mask (inf beyond max_rings)."""
    d = np.full(len(seed), np.inf)
    d[seed] = 0
    cur = seed.copy()
    for r in range(1, max_rings + 1):
        nxt = grow_vmask(adj, cur, 1) & ~cur
        if not nxt.any():
            break
        d[nxt] = r
        cur = cur | nxt
    return d


def geodesic_from(ob, seed, max_dist=1.0, iters=200):
    """Approximate surface distance (metres) from seed vertices by edge-length relaxation."""
    V = co(ob)
    E = edges(ob)
    L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    d = np.where(seed, 0.0, np.inf)
    for _ in range(iters):
        a = d[E[:, 0]] + L
        b = d[E[:, 1]] + L
        nd = d.copy()
        np.minimum.at(nd, E[:, 1], a)
        np.minimum.at(nd, E[:, 0], b)
        if np.allclose(np.nan_to_num(nd, posinf=9), np.nan_to_num(d, posinf=9)):
            break
        d = nd
    return np.minimum(d, max_dist)


# ----------------------------------------------------------------------------- objects

def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def make_object(name, verts, faces, uvs=None, coll=None, smooth_shade=True):
    """uvs: per-face lists of (u, v) matching faces, or None."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(map(int, f)) for f in faces])
    me.validate(clean_customdata=False)
    if uvs is not None:
        flat = np.array([uv for f in uvs for uv in f], dtype=np.float64)
        uvl = me.uv_layers.new(name="UVMap")
        uvl.data.foreach_set("uv", flat.ravel())
    if smooth_shade:
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    ob = bpy.data.objects.new(name, me)
    link(ob, coll)
    return ob


def duplicate(ob, name):
    d = ob.copy()
    d.data = ob.data.copy()
    d.name = d.data.name = name
    for c in ob.users_collection:
        c.objects.link(d)
        break
    else:
        link(d)
    return d


def extract(ob, face_mask, name):
    """New object with the masked faces of ob (UVs, weights, attributes kept). Returns (obj, src_vi)."""
    d = duplicate(ob, name)
    me = d.data
    attr = me.attributes.get("src_vi") or me.attributes.new("src_vi", "INT", "POINT")
    attr.data.foreach_set("value", np.arange(len(me.vertices), dtype=np.int32))
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    kill = [f for f, keep in zip(bm.faces, face_mask) if not keep]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()
    src = np.empty(len(me.vertices), np.int32)
    me.attributes["src_vi"].data.foreach_get("value", src)
    for m in list(d.modifiers):
        if m.type != "ARMATURE":
            d.modifiers.remove(m)
    return d, src.astype(np.int64)


def delete_faces(ob, face_mask):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    kill = [f for f, k in zip(bm.faces, face_mask) if k]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()


def delete_verts(ob, vmask):
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [v for v, k in zip(bm.verts, vmask) if k]
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()


def bisect_keep_above(ob, z, normal=(0, 0, 1)):
    """Cuts the mesh with a plane through (0,0,z) and removes the part below it."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=normal, clear_inner=True)
    bm.to_mesh(me)
    bm.free()
    me.update()


def bisect_keep(ob, point, normal):
    """Cuts with a plane and keeps the side the normal points to (clean straight hems)."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=tuple(point), plane_no=tuple(normal), clear_inner=True)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()


def cut_implicit(ob, fn):
    """Cuts the mesh along the zero set of fn(P) (P: (n,3) vertex positions) and deletes the side where
    fn < 0. New vertices sit on the zero set (linear interpolation along each cut edge) and interpolate
    UVs, weights and attributes, so a garment edge follows a smooth analytic curve instead of the body's
    face boundaries. Returns the number of cut edges."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    P = np.array([v.co[:] for v in bm.verts])
    if not len(P):
        bm.free()
        return 0
    f = np.asarray(fn(P), float)
    if len(f) != len(P):
        raise ValueError("cut_implicit: field size mismatch")
    f = np.where(np.abs(f) < 1e-7, 1e-7, f)
    fval = {v: float(f[i]) for i, v in enumerate(bm.verts)}
    cut = [e for e in bm.edges if fval[e.verts[0]] * fval[e.verts[1]] < 0]
    new = []
    for e in cut:
        a, b = e.verts
        t = fval[a] / (fval[a] - fval[b])
        _, nv = bmesh.utils.edge_split(e, a, t)
        fval[nv] = 0.0
        new.append(nv)
    if new:
        bmesh.ops.connect_verts(bm, verts=new, check_degenerate=False)
    kill = [fc for fc in bm.faces if any(fval.get(v, 0.0) < 0 for v in fc.verts)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(cut)


def subdivide(ob, cuts=1):
    """Linear subdivision (no smoothing); UVs, weights and attributes are interpolated."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True, smooth=0.0)
    bm.to_mesh(me)
    bm.free()
    me.update()


def edge_fields(ob, extra_seed=None):
    """Per-vertex surface distance (m) to the nearest open edge or extra seed vertices (Dijkstra over
    edges) and an along-edge coordinate: the arc length (m) of the closest point on the nearest open
    boundary loop, so stitch dashes run evenly along hems."""
    import heapq
    V = co(ob)
    E = edges(ob)
    seed = boundary_vmask(ob)
    if extra_seed is not None:
        seed = seed | extra_seed
    nb = [[] for _ in range(len(V))]
    for a, b in E:
        L = float(np.linalg.norm(V[a] - V[b]))
        nb[a].append((b, L))
        nb[b].append((a, L))
    d = np.full(len(V), np.inf)
    h = [(0.0, int(i)) for i in np.nonzero(seed)[0]]
    for _, i in h:
        d[i] = 0.0
    heapq.heapify(h)
    while h:
        di, i = heapq.heappop(h)
        if di > d[i]:
            continue
        for j, L in nb[i]:
            nd = di + L
            if nd < d[j]:
                d[j] = nd
                heapq.heappush(h, (nd, j))
    d[~np.isfinite(d)] = 1.0
    A, B, S = [], [], []
    for lp in boundary_loops(ob):
        if len(lp) < 2:
            continue
        P = V[lp]
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        A.append(P[:-1])
        B.append(P[1:])
        S.append(np.r_[0, np.cumsum(seg)][:-1])
    s = np.zeros(len(V))
    if A:
        A, B, S = np.concatenate(A), np.concatenate(B), np.concatenate(S)
        AB = B - A
        L2 = np.maximum((AB * AB).sum(1), 1e-12)
        for k in range(0, len(V), 256):
            p = V[k:k + 256]
            t = np.clip(((p[:, None, :] - A[None]) * AB[None]).sum(-1) / L2[None], 0, 1)
            q = A[None] + t[..., None] * AB[None]
            dd = ((p[:, None, :] - q) ** 2).sum(-1)
            j = np.argmin(dd, 1)
            s[k:k + 256] = S[j] + t[np.arange(len(p)), j] * np.sqrt(L2[j])
    return d.astype(np.float32), s.astype(np.float32)


def join(objs, name):
    objs = [o for o in objs if o is not None]
    base = objs[0]
    with bpy.context.temp_override(object=base, active_object=base, selected_objects=objs,
                                   selected_editable_objects=objs):
        bpy.ops.object.join()
    base.name = base.data.name = name
    return base


def apply_modifier(ob, name):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob],
                                   selected_editable_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=name)


def solidify(ob, thickness, offset=-1.0, rim=True):
    m = ob.modifiers.new("Solid", "SOLIDIFY")
    m.thickness = thickness
    m.offset = offset
    m.use_rim = rim
    m.use_even_offset = True
    m.use_quality_normals = True
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_move_to_index(modifier="Solid", index=0)
    apply_modifier(ob, "Solid")


def shade_smooth(ob):
    ob.data.polygons.foreach_set("use_smooth", np.ones(len(ob.data.polygons), bool))


# ----------------------------------------------------------------------------- collider

class Collider:
    """Nearest-surface queries against a set of rest meshes (world space)."""

    def __init__(self, objs):
        Vs, Fs, off = [], [], 0
        for ob in objs:
            V = co(ob) @ np.array(ob.matrix_world)[:3, :3].T + np.array(ob.matrix_world)[:3, 3]
            Vs.append(V)
            Fs.extend([list(map(int, f + off)) for f in poly_list(ob)])
            off += len(V)
        self.V = np.concatenate(Vs)
        self.bvh = BVHTree.FromPolygons([tuple(v) for v in self.V], Fs, all_triangles=False)

    def nearest(self, P):
        loc = np.zeros_like(P)
        nrm = np.zeros_like(P)
        ok = np.zeros(len(P), bool)
        for i, p in enumerate(P):
            r = self.bvh.find_nearest(Vector(p))
            if r[0] is not None:
                loc[i] = r[0]
                nrm[i] = r[1]
                ok[i] = True
        return loc, nrm, ok

    def signed_distance(self, P):
        """Distance to the nearest surface point, negative inside, and the outward direction. Both come
        from the vector to the nearest point (the face normal only gives its sign), so a point nearest
        to an edge or vertex shared by several faces gets the same answer whichever face the BVH
        reports (keeps the build deterministic)."""
        loc, nrm, ok = self.nearest(P)
        v = P - loc
        dist = np.linalg.norm(v, axis=1)
        sgn = np.where(np.einsum("ij,ij->i", v, nrm) < 0, -1.0, 1.0)
        dirv = np.where(dist[:, None] > 1e-7, v / np.maximum(dist, 1e-12)[:, None] * sgn[:, None], nrm)
        d = dist * sgn
        d[~ok] = 1.0
        return d, loc, dirv

    def push_out(self, P, min_d):
        d, loc, dirv = self.signed_distance(P)
        min_d = np.broadcast_to(min_d, (len(P),))
        bad = d < min_d
        P = P.copy()
        P[bad] = loc[bad] + dirv[bad] * min_d[bad, None]
        return P, int(bad.sum())

    def ray(self, origin, direction, dist=10.0):
        r = self.bvh.ray_cast(Vector(origin), Vector(direction), dist)
        return r


def relax_shell(V, adj, collider, min_d, iters=20, factor=0.5, pinned=None, boundary=None,
                tangential_only=None):
    """Garment tension: smooth toward neighbours (bridging concavities), then push back out of the
    collider to at least min_d. Pinned vertices stay put; boundary vertices smooth along the boundary
    only if a boundary adjacency is given."""
    V = V.copy()
    for _ in range(iters):
        m = neighbour_mean(V, adj)
        step = factor * (m - V)
        if pinned is not None:
            step[pinned] = 0
        V = V + step
        V, _ = collider.push_out(V, min_d)
    return V


# ----------------------------------------------------------------------------- lips / thickness

def add_boundary_lip(ob, depth, vmask=None):
    """Turns open boundaries under by `depth` (towards -normal): a hem that reads as thickness.
    Only boundary edges whose two vertices are in vmask (default all) are turned. New vertices copy
    weights, UVs and attributes of their boundary vertex and are appended after the existing ones."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    deform = bm.verts.layers.deform.active
    uvl = bm.loops.layers.uv.active
    bedges = [e for e in bm.edges if e.is_boundary
              and (vmask is None or (vmask[e.verts[0].index] and vmask[e.verts[1].index]))]
    if not bedges:
        bm.free()
        return 0
    res = bmesh.ops.extrude_edge_only(bm, edges=bedges)
    new_verts = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in new_verts:
        src = [e.other_vert(v) for e in v.link_edges if e.other_vert(v) not in new_verts]
        n = Vector((0, 0, 0))
        for s in src:
            n += s.normal
        if n.length > 0:
            n.normalize()
        v.co = v.co - n * depth
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.update()
    shade_smooth(ob)
    return len(new_verts)


# ----------------------------------------------------------------------------- weights

def weights(ob, names=None):
    n = len(ob.data.vertices)
    idx = {vg.index: vg.name for vg in ob.vertex_groups}
    want = set(idx.values()) if names is None else set(names)
    out = {nm: np.zeros(n) for nm in want}
    for v in ob.data.vertices:
        for g in v.groups:
            nm = idx.get(g.group)
            if nm in out:
                out[nm][v.index] = g.weight
    return out


def set_weights(ob, W, threshold=1e-4):
    for vg in list(ob.vertex_groups):
        ob.vertex_groups.remove(vg)
    for bone, w in W.items():
        idx = np.nonzero(w > threshold)[0]
        if len(idx) == 0:
            continue
        g = ob.vertex_groups.new(name=bone)
        # group vertices by identical weight to cut Python calls
        vals = np.round(w[idx], 4)
        order = np.argsort(vals, kind="stable")
        idx, vals = idx[order], vals[order]
        splits = np.nonzero(np.diff(vals))[0] + 1
        for a, b in zip(np.r_[0, splits], np.r_[splits, len(vals)]):
            g.add(idx[a:b].tolist(), float(vals[a]), "REPLACE")


def normalize_limit(W, limit=8, threshold=0.004, keep=None):
    """Per-vertex: drop tiny weights, keep the `limit` largest, renormalise to 1."""
    names = list(W)
    if not names:
        return W
    M = np.stack([W[n] for n in names], axis=1)
    M[M < threshold] = 0
    if M.shape[1] > limit:
        part = np.argpartition(-M, limit - 1, axis=1)[:, limit:]
        np.put_along_axis(M, part, 0.0, axis=1)
    s = M.sum(1, keepdims=True)
    M = np.where(s > 0, M / np.maximum(s, 1e-12), M)
    return {n: M[:, i] for i, n in enumerate(names) if M[:, i].max() > 0}


def smooth_weights(W, adj, iters=2, factor=0.5, fixed=None):
    names = list(W)
    M = np.stack([W[n] for n in names], axis=1)
    M = smooth(M, adj, iters, factor, fixed)
    return {n: M[:, i] for i, n in enumerate(names)}


def weights_from_source(src_W, src_vi):
    return {k: v[src_vi] for k, v in src_W.items()}


def transfer_weights_nearest(dst, collider_obj_V, collider_W, points=None, k=4, power=2.0):
    """Inverse-distance weights from the k nearest source vertices (numpy brute force in chunks)."""
    P = co(dst) if points is None else points
    names = list(collider_W)
    M = np.stack([collider_W[n] for n in names], axis=1)
    out = np.zeros((len(P), len(names)))
    S = collider_obj_V
    for a in range(0, len(P), 512):
        p = P[a:a + 512]
        d2 = ((p[:, None, :] - S[None, :, :]) ** 2).sum(-1)
        nn = np.argpartition(d2, k, axis=1)[:, :k]
        dd = np.take_along_axis(d2, nn, 1)
        w = 1.0 / np.maximum(dd, 1e-10) ** (power / 2)
        w /= w.sum(1, keepdims=True)
        out[a:a + 512] = np.einsum("ij,ijk->ik", w, M[nn])
    return {n: out[:, i] for i, n in enumerate(names)}


def transfer_weights_surface(src, dst, mapping="POLYINTERP_NEAREST"):
    """Blender Data Transfer of all vertex groups from the nearest source face, interpolated."""
    for vg in list(dst.vertex_groups):
        dst.vertex_groups.remove(vg)
    for vg in src.vertex_groups:
        dst.vertex_groups.new(name=vg.name)
    mod = dst.modifiers.new("WT", "DATA_TRANSFER")
    mod.object = src
    mod.use_vert_data = True
    mod.data_types_verts = {"VGROUP_WEIGHTS"}
    mod.vert_mapping = mapping
    mod.layers_vgroup_select_src = "ALL"
    mod.layers_vgroup_select_dst = "NAME"
    with bpy.context.temp_override(object=dst, active_object=dst):
        bpy.ops.object.modifier_move_to_index(modifier="WT", index=0)
    apply_modifier(dst, "WT")


def bind(ob, rig):
    ob.parent = rig
    ob.matrix_parent_inverse.identity()
    for m in list(ob.modifiers):
        if m.type == "ARMATURE":
            ob.modifiers.remove(m)
    m = ob.modifiers.new("Armature", "ARMATURE")
    m.object = rig
    m.use_deform_preserve_volume = False
    return m


# ----------------------------------------------------------------------------- curves / tubes

def catmull_rom(points, n):
    """Centripetal-ish Catmull-Rom through control points, resampled to n points by arc length."""
    P = np.asarray(points, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    dense = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, 24, endpoint=False):
            t2, t3 = t * t, t * t * t
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    dense.append(P[-2])
    dense = np.array(dense)
    seg = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    t = np.linspace(0, s[-1], n)
    out = np.stack([np.interp(t, s, dense[:, k]) for k in range(3)], axis=1)
    return out, s[-1]


def frames_along(path, up_hint):
    """Rotation-minimising frames (T, N, B) along a polyline; N starts perpendicular to up_hint."""
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    n0 = np.cross(T[0], up_hint)
    if np.linalg.norm(n0) < 1e-6:
        n0 = np.cross(T[0], [1, 0, 0])
    n0 /= np.linalg.norm(n0)
    N = [n0]
    for i in range(1, len(path)):
        v1 = path[i] - path[i - 1]
        c1 = v1 @ v1
        if c1 < 1e-12:
            N.append(N[-1])
            continue
        rL = N[-1] - (2 / c1) * (v1 @ N[-1]) * v1
        tL = T[i - 1] - (2 / c1) * (v1 @ T[i - 1]) * v1
        v2 = T[i] - tL
        c2 = v2 @ v2
        n = rL - (2 / c2) * (v2 @ rL) * v2 if c2 > 1e-12 else rL
        n -= T[i] * (n @ T[i])
        N.append(n / np.linalg.norm(n))
    N = np.array(N)
    B = np.cross(T, N)
    return T, N, B


def tube(path, radii_a, radii_b, sides, axis_a, axis_b, cap_start=False, cap_end=True,
         u_range=(0.0, 1.0), v_range=(0.0, 1.0), twist=None):
    """Elliptical tube along path; axis_a/axis_b are per-point unit vectors spanning the section.
    Returns verts, faces (quads), per-face UVs (u around the section, v along the path)."""
    n = len(path)
    verts, faces, uvs = [], [], []
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    for i in range(n):
        tw = 0.0 if twist is None else twist[i]
        for a in ang:
            c, s = math.cos(a + tw), math.sin(a + tw)
            verts.append(path[i] + axis_a[i] * radii_a[i] * c + axis_b[i] * radii_b[i] * s)
    u0, u1 = u_range
    v0, v1 = v_range
    for i in range(n - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((i * sides + j, i * sides + j2, (i + 1) * sides + j2, (i + 1) * sides + j))
            ua = u0 + (u1 - u0) * j / sides
            ub = u0 + (u1 - u0) * (j + 1) / sides
            va = v0 + (v1 - v0) * i / (n - 1)
            vb = v0 + (v1 - v0) * (i + 1) / (n - 1)
            uvs.append([(ua, va), (ub, va), (ub, vb), (ua, vb)])
    if cap_end:
        c = len(verts)
        verts.append(path[-1] + (path[-1] - path[-2]) * 0.3)
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append(((n - 1) * sides + j, (n - 1) * sides + j2, c))
            uvs.append([(u0 + (u1 - u0) * j / sides, v1), (u0 + (u1 - u0) * (j + 1) / sides, v1),
                        (u0 + (u1 - u0) * (j + 0.5) / sides, v1)])
    if cap_start:
        c = len(verts)
        verts.append(path[0] - (path[1] - path[0]) * 0.3)
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((j2, j, c))
            uvs.append([(u0 + (u1 - u0) * (j + 1) / sides, v0), (u0 + (u1 - u0) * j / sides, v0),
                        (u0 + (u1 - u0) * (j + 0.5) / sides, v0)])
    return np.array(verts), faces, uvs


def merge_parts(parts):
    """parts: list of (verts, faces, uvs) -> combined (verts, faces, uvs, part_index_per_vertex)."""
    V, F, U, pid = [], [], [], []
    off = 0
    for k, (v, f, u) in enumerate(parts):
        V.append(np.asarray(v))
        F.extend([tuple(x + off for x in face) for face in f])
        U.extend(u)
        pid.extend([k] * len(v))
        off += len(v)
    return np.concatenate(V), F, U, np.array(pid)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)
