"""Mesh-building helpers (bmesh based) for The Drowned Chapel.

A Piece accumulates sub-meshes with a material slot, a UV mode and a tile size.
finalize() computes UVs, vertex colours (R=AO, G=edge wear, B=base grime),
smoothing, and returns a bpy Mesh whose origin is the piece's base centre.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

UV_BOX, UV_CYL, UV_WOOD, UV_KEEP, UV_PLANAR_XZ = 0, 1, 2, 3, 4

# metres per UV unit, per material (used by UV_BOX / UV_CYL / UV_WOOD)
MAT_TILE = {
    "M_StoneAshlar": 2.5,
    "M_StoneDressed": 1.5,
    "M_FloorFlags": 3.0,
    "M_WoodPew": 1.6,
    "M_IronAged": 0.6,
    "M_CandleWax": 0.25,
    "M_ClothAltar": 0.8,
    "M_Water": 4.0,
}


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


class Piece:
    def __init__(self, name, grounded=True):
        self.name = name
        self.grounded = grounded
        self.bm = bmesh.new()
        self.mats = []
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.mode = self.bm.faces.layers.int.new("uvmode")
        self.tile = self.bm.faces.layers.float.new("uvtile")
        self.extra = {}

    def slot(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def add(self, src, mat, uvmode=UV_BOX, tile=None, matrix=None):
        """Merge bmesh `src` into the piece (src is freed)."""
        if matrix is not None:
            bmesh.ops.transform(src, matrix=matrix, verts=src.verts)
        mi = self.slot(mat)
        t = tile if tile is not None else MAT_TILE.get(mat, 1.0)
        src_uv = src.loops.layers.uv.active
        if src_uv is None and len(src.loops.layers.uv):
            src_uv = src.loops.layers.uv.values()[0]
        vmap = {v: self.bm.verts.new(v.co) for v in src.verts}
        for f in src.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = mi
            nf[self.mode] = uvmode
            nf[self.tile] = t
            nf.smooth = f.smooth
            if src_uv is not None and uvmode in (UV_KEEP,):
                for l_src, l_dst in zip(f.loops, nf.loops):
                    l_dst[self.uv].uv = l_src[src_uv].uv
        src.free()

    # ------------------------------------------------------------------
    def finalize(self, sharp_deg=38.0, merge_dist=0.0004, flip=False):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_dist)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
        # no n-gons: triangulate anything above 4 sides
        big = [f for f in bm.faces if len(f.verts) > 4]
        if big:
            bmesh.ops.triangulate(bm, faces=big, quad_method="BEAUTY", ngon_method="BEAUTY")
        if flip:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.normal_update()
        self._uvs()
        self._colours()
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            mat = bpy.data.materials.get(m) or bpy.data.materials.new(m)
            me.materials.append(mat)
        me.set_sharp_from_angle(angle=math.radians(sharp_deg))
        me.validate(clean_customdata=False)
        return me

    def _uvs(self):
        bm = self.bm
        uv = self.uv
        for f in bm.faces:
            mode = f[self.mode]
            if mode == UV_KEEP:
                continue
            t = f[self.tile] or 1.0
            n = f.normal
            ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
            if mode == UV_PLANAR_XZ:
                for l in f.loops:
                    co = l.vert.co
                    l[uv].uv = (co.x / t, co.z / t)
                continue
            if mode == UV_CYL and az < 0.7:
                angs = [math.atan2(l.vert.co.y, l.vert.co.x) for l in f.loops]
                if max(angs) - min(angs) > math.pi:
                    angs = [a + 2 * math.pi if a < 0 else a for a in angs]
                for l, a in zip(f.loops, angs):
                    l[uv].uv = (a * 0.35 / t, l.vert.co.z / t)
                continue
            for l in f.loops:
                co = l.vert.co
                if mode == UV_WOOD:
                    # grain along local X
                    if az >= ax and az >= ay:
                        u, v = co.y, co.x
                    elif ay >= ax:
                        u, v = co.z, co.x
                    else:
                        u, v = co.y, co.z
                else:
                    if az >= ax and az >= ay:
                        u, v = (co.x, co.y) if n.z >= 0 else (co.x, -co.y)
                    elif ax >= ay:
                        u, v = (co.y, co.z) if n.x >= 0 else (-co.y, co.z)
                    else:
                        u, v = (-co.x, co.z) if n.y >= 0 else (co.x, co.z)
                l[uv].uv = (u / t, v / t)

    def _colours(self):
        bm = self.bm
        col = bm.loops.layers.color.new("Col")
        conv = {}
        for v in bm.verts:
            acc, cnt = 0.0, 0
            for e in v.link_edges:
                if len(e.link_faces) == 2:
                    acc += e.calc_face_angle_signed(0.0)
                    cnt += 1
            conv[v] = acc / cnt if cnt else 0.0
        for v in bm.verts:
            c = conv[v]
            wear = smoothstep(0.12, 0.75, c)
            cav = smoothstep(0.12, 0.75, -c)
            ao = 1.0 - 0.45 * cav
            grime = 0.0
            if self.grounded:
                z = v.co.z
                ao *= 0.72 + 0.28 * smoothstep(0.0, 0.5, z)
                grime = smoothstep(1.4, 0.0, z)
            rgba = (ao, wear, grime, 1.0)
            for l in v.link_loops:
                l[col] = rgba


# ----------------------------------------------------------------------
# Primitive builders (all return a new bmesh)
# ----------------------------------------------------------------------

def bm_box(sx, sy, sz, cx=0.0, cy=0.0, cz=0.0, bevel=0.0, segments=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if bevel > 0:
        b = min(bevel, 0.45 * min(sx, sy, sz))
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=b, segments=segments, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
    bmesh.ops.translate(bm, vec=(cx, cy, cz), verts=bm.verts)
    return bm


def bm_loft(rings, cap_start=True, cap_end=True, closed=True):
    """rings: list of lists of 3D points (same count); rings CCW seen from the
    direction of travel -> outward normals."""
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    seg = n if closed else n - 1
    for a, b in zip(vr[:-1], vr[1:]):
        for i in range(seg):
            j = (i + 1) % n
            quad = [a[i], a[j], b[j], b[i]]
            if len({id(q) for q in quad}) == 4:
                bm.faces.new(quad)
    if closed and cap_start:
        c = Vector((0, 0, 0))
        for p in rings[0]:
            c += Vector(p)
        cv = bm.verts.new(c / n)
        for i in range(n):
            bm.faces.new([cv, vr[0][(i + 1) % n], vr[0][i]])
    if closed and cap_end:
        c = Vector((0, 0, 0))
        for p in rings[-1]:
            c += Vector(p)
        cv = bm.verts.new(c / n)
        for i in range(n):
            bm.faces.new([cv, vr[-1][i], vr[-1][(i + 1) % n]])
    return bm


def ring(radius_fn, z, n, phase=0.0, cx=0.0, cy=0.0):
    pts = []
    for i in range(n):
        a = phase + 2 * math.pi * i / n
        r = radius_fn(a) if callable(radius_fn) else radius_fn
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    return pts


def bm_cylinder(r, z0, z1, n=12, cx=0.0, cy=0.0, r_top=None, caps=True, phase=0.0):
    rt = r if r_top is None else r_top
    return bm_loft([ring(r, z0, n, phase, cx, cy), ring(rt, z1, n, phase, cx, cy)],
                   cap_start=caps, cap_end=caps)


def bm_lathe(profile, n=24, phase=0.0, cx=0.0, cy=0.0, cap_start=True, cap_end=True):
    """profile: list of (radius, z) bottom -> top."""
    rings = [ring(r, z, n, phase, cx, cy) for (r, z) in profile]
    return bm_loft(rings, cap_start=cap_start, cap_end=cap_end)


def frame_for(t, up):
    t = Vector(t).normalized()
    upv = Vector(up)
    if abs(t.dot(upv)) > 0.98:
        upv = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
    e1 = upv.cross(t).normalized()
    e2 = t.cross(e1).normalized()
    return e1, e2


def bm_sweep(path, profile, up=(0, 0, 1), closed_path=False, caps=True, scales=None):
    """Sweep a 2D profile [(a, b)] (CCW) along a 3D path."""
    rings = []
    m = len(path)
    for k in range(m):
        p = Vector(path[k])
        if closed_path:
            t = Vector(path[(k + 1) % m]) - Vector(path[k - 1])
        elif k == 0:
            t = Vector(path[1]) - p
        elif k == m - 1:
            t = p - Vector(path[k - 1])
        else:
            t = Vector(path[k + 1]) - Vector(path[k - 1])
        e1, e2 = frame_for(t, up)
        s = scales[k] if scales else 1.0
        rings.append([tuple(p + e1 * (a * s) + e2 * (b * s)) for (a, b) in profile])
    if closed_path:
        rings.append(rings[0])
        bm = bm_loft(rings, cap_start=False, cap_end=False)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        return bm
    return bm_loft(rings, cap_start=caps, cap_end=caps)


def circle_profile(r, n):
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rect_profile(w, h, chamfer=0.0):
    hw, hh = w / 2, h / 2
    if chamfer <= 0:
        return [(hw, -hh), (hw, hh), (-hw, hh), (-hw, -hh)]
    c = min(chamfer, 0.45 * min(w, h))
    return [(hw, -hh + c), (hw, hh - c), (hw - c, hh), (-hw + c, hh), (-hw, hh - c), (-hw, -hh + c),
            (-hw + c, -hh), (hw - c, -hh)]


_tmp_coll = None


def _scratch_collection():
    global _tmp_coll
    if _tmp_coll is None or _tmp_coll.name not in bpy.data.collections:
        _tmp_coll = bpy.data.collections.new("_scratch")
        bpy.context.scene.collection.children.link(_tmp_coll)
    return _tmp_coll


def bm_profile_solid(loops, depth, bevel=0.0, bevel_res=1):
    """Extrude 2D closed loops (outer + holes, even-odd) in the XY plane,
    centred on Z=0 with total thickness `depth`; rounded bevel keeps the
    silhouette exact.  Returns a bmesh (XY plane, thickness along Z)."""
    cu = bpy.data.curves.new("_prof", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    try:
        cu.fill_solver = "CDT"
        cu.fill_rule = "EVEN_ODD"
    except Exception:
        pass
    b = max(0.0, min(bevel, depth * 0.45))
    cu.extrude = max(depth / 2.0 - b, 1e-4)
    cu.bevel_depth = b
    cu.bevel_resolution = bevel_res
    cu.offset = -b
    cu.resolution_u = 1
    for loop in loops:
        sp = cu.splines.new("POLY")
        sp.points.add(len(loop) - 1)
        for p, (x, y) in zip(sp.points, loop):
            p.co = (x, y, 0.0, 1.0)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new("_prof", cu)
    coll = _scratch_collection()
    coll.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return bm


def bm_flat(loops):
    """Single-sided filled 2D shape in XY (normal +Z)."""
    cu = bpy.data.curves.new("_flat", "CURVE")
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    try:
        cu.fill_solver = "CDT"
        cu.fill_rule = "EVEN_ODD"
    except Exception:
        pass
    for loop in loops:
        sp = cu.splines.new("POLY")
        sp.points.add(len(loop) - 1)
        for p, (x, y) in zip(sp.points, loop):
            p.co = (x, y, 0.0, 1.0)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new("_flat", cu)
    _scratch_collection().objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.normal_update()
    if bm.faces and sum(f.normal.z for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


def bm_grid(nx, ny, fn, x0, x1, y0, y1):
    """Height-field grid (normal +Z). fn(x, y) -> z."""
    bm = bmesh.new()
    vs = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        row = []
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            row.append(bm.verts.new((x, y, fn(x, y))))
        vs.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new([vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]])
    return bm


# matrices that map the XY-plane profile builders into vertical planes
# XZ plane facing -Y (towards the gameplay camera): (x, y, z) -> (x, z, y)
TO_XZ = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
# YZ plane facing -X: (x, y, z) -> (z?, x, y)
TO_YZ = Matrix(((0, 0, 1, 0), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def mat_t(x, y, z):
    return Matrix.Translation((x, y, z))


def mat_rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Z")


def mat_rx(deg):
    return Matrix.Rotation(math.radians(deg), 4, "X")


def mat_ry(deg):
    return Matrix.Rotation(math.radians(deg), 4, "Y")


def mat_s(sx, sy, sz):
    return Matrix.Diagonal((sx, sy, sz, 1.0))


# ----------------------------------------------------------------------
# 2D shape helpers
# ----------------------------------------------------------------------

def pointed_arch_pts(a, spring, rho, n=14, reverse=False):
    """Pointed (two-centred) arch intrados from right spring (a, spring) over the apex
    to the left spring (-a, spring).  rho >= a."""
    xc = a - rho
    ga = math.acos(max(-1.0, min(1.0, (rho - a) / rho)))
    pts = []
    for i in range(n + 1):
        g = ga * i / n
        pts.append((xc + rho * math.cos(g), spring + rho * math.sin(g)))
    for i in range(n - 1, -1, -1):
        g = ga * i / n
        pts.append((-(xc + rho * math.cos(g)), spring + rho * math.sin(g)))
    return pts[::-1] if reverse else pts


def arch_apex(a, spring, rho):
    xc = a - rho
    return spring + math.sqrt(max(rho * rho - xc * xc, 0.0))


def lancet_outline(half_w, z0, spring, rho_k=2.4, n=12):
    """Closed lancet window outline (CCW): bottom edge, jambs, pointed head."""
    rho = max(rho_k * half_w, half_w)   # rho_k = 2 -> equilateral, > 2 -> lancet
    pts = [(-half_w, z0), (half_w, z0)]
    pts += pointed_arch_pts(half_w, spring, rho, n)
    return pts


def arch_band(a_in, w, spring, rho_in, n=14, foot=0.0):
    """Closed outline of a pointed arch band from the intrados (a_in, rho_in) out by w."""
    outer = pointed_arch_pts(a_in + w, spring, rho_in + w, n)
    inner = pointed_arch_pts(a_in, spring, rho_in, n)
    pts = []
    if foot > 0:
        pts.append((a_in + w, spring - foot))
    pts += outer
    if foot > 0:
        pts.append((-(a_in + w), spring - foot))
        pts.append((-a_in, spring - foot))
    pts += inner[::-1]
    if foot > 0:
        pts.append((a_in, spring - foot))
    return pts


def segmental_pointed(x, a, h, e):
    """Height (above springing) of a gently pointed segmental profile, half span a,
    rise h, pointedness e (arc centres offset by e past the centre line)."""
    zc = (h * h + e * e - (a + e) ** 2) / (2 * h)
    rho = math.sqrt((a + e) ** 2 + zc * zc)
    ax = abs(x)
    val = rho * rho - (ax + e) ** 2
    return zc + math.sqrt(max(val, 0.0))


def pointed_height(x, a, h):
    """Two-centred pointed arch height for |x| <= a, rise h >= a."""
    rho = (h * h + a * a) / (2 * a)
    xc = a - rho
    ax = abs(x)
    return math.sqrt(max(rho * rho - (ax - xc) ** 2, 0.0))
