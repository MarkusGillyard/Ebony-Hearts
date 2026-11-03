"""Unique mesh pieces of The Drowned Chapel.

Every builder returns a chapel_geo.Piece whose local origin is the piece's base
centre (floor line for architecture that has a buried footing).  Each piece is
exported once; placement happens in chapel_layout.py.
"""
import math
import random

import bmesh
from mathutils import Matrix, Vector

import chapel_config as C
import chapel_geo as G
import chapel_rose as R
from chapel_geo import (Piece, UV_BOX, UV_CYL, UV_KEEP, UV_PLANAR_XZ, UV_WOOD,
                        TO_XZ, TO_YZ, mat_rx, mat_ry, mat_rz, mat_s, mat_t)

ASH = "M_StoneAshlar"
DRS = "M_StoneDressed"
FLR = "M_FloorFlags"
WOD = "M_WoodPew"
IRN = "M_IronAged"
WAX = "M_CandleWax"
FLM = "M_CandleFlame"
GRS = "M_GlassRose"
GLN = "M_GlassLancet"
WAT = "M_Water"
CLO = "M_ClothAltar"
DEC = "M_DecalGrime"

ALL_MATERIALS = [ASH, DRS, FLR, WOD, IRN, WAX, FLM, GRS, GLN, WAT, CLO, DEC]


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------
# Shared shapes
# ---------------------------------------------------------------------------
CORE_R = 0.30
SHAFTS = [(0, 0.29, 0.11), (90, 0.29, 0.11), (180, 0.29, 0.11), (270, 0.29, 0.11),
          (45, 0.31, 0.065), (135, 0.31, 0.065), (225, 0.31, 0.065), (315, 0.31, 0.065)]


def cluster_r(a):
    ux, uy = math.cos(a), math.sin(a)
    t = CORE_R
    for deg, d, r in SHAFTS:
        cx, cy = d * math.cos(math.radians(deg)), d * math.sin(math.radians(deg))
        b = ux * cx + uy * cy
        disc = r * r - (cx * cx + cy * cy - b * b)
        if disc >= 0:
            t = max(t, b + math.sqrt(disc))
    return t


# (z, radial offset) bottom -> top for the clustered pier mouldings
BASE_PROFILE = [(0.30, 0.10), (0.33, 0.125), (0.39, 0.125), (0.42, 0.085), (0.45, 0.04), (0.49, 0.03),
                (0.52, 0.07), (0.56, 0.07), (0.59, 0.03), (0.62, 0.0)]
SHAFT_PROFILE = [(1.2, 0.0), (2.2, 0.0), (3.25, 0.0), (3.27, 0.03), (3.37, 0.03), (3.39, 0.0), (4.6, 0.0),
                 (5.92, 0.0), (5.94, 0.035), (6.02, 0.035), (6.04, 0.0), (6.10, 0.01), (6.24, 0.055),
                 (6.34, 0.12), (6.40, 0.16)]


def cluster_rings(profile, n, a0=0.0, a1=2 * math.pi, closed=True, scale=1.0):
    rings = []
    count = n if closed else n + 1
    for z, d in profile:
        ring = []
        for i in range(count):
            a = a0 + (a1 - a0) * i / n
            r = (cluster_r(a) + d) * scale
            ring.append((r * math.cos(a), r * math.sin(a), z))
        rings.append(ring)
    return rings


def half_loft(rings):
    """Loft open (half) rings and cap the ends with fans to the axis."""
    bm = G.bm_loft(rings, cap_start=False, cap_end=False, closed=False)
    n = len(rings[0])
    for ring, top in ((rings[0], False), (rings[-1], True)):
        z = ring[0][2]
        vs = [bm.verts.new(p) for p in ring]
        c = bm.verts.new((0.0, 0.0, z))
        for i in range(n - 1):
            if top:
                bm.faces.new([c, vs[i], vs[i + 1]])
            else:
                bm.faces.new([c, vs[i + 1], vs[i]])
    return bm


def octagon_slab(apothem, z0, z1, chamfer=0.03, phase=math.radians(22.5)):
    R_ = apothem / math.cos(math.radians(22.5))
    prof = [(R_, z0), (R_, z1 - chamfer), (R_ - chamfer * 1.2, z1)]
    return G.bm_lathe(prof, n=8, phase=phase)


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

def build_column():
    p = Piece("SM_Column_Clustered")
    n = 80
    p.add(octagon_slab(0.55, -0.45, 0.30, 0.04), DRS, UV_BOX)
    p.add(G.bm_loft(cluster_rings(BASE_PROFILE + SHAFT_PROFILE, n)), DRS, UV_CYL)
    R_ab = 0.62 / math.cos(math.radians(22.5))
    p.add(G.bm_lathe([(R_ab - 0.05, 6.40), (R_ab, 6.45), (R_ab, 6.56), (R_ab - 0.03, C.SPRING_Z)], n=8,
                     phase=math.radians(22.5)), DRS, UV_BOX)
    return p


def build_respond():
    """Engaged half pier; local -Y faces the room, the back half is omitted (buried)."""
    p = Piece("SM_WallRespond")
    n = 40
    p.add(octagon_slab(0.55, -0.45, 0.30, 0.04), DRS, UV_BOX)
    p.add(half_loft(cluster_rings(BASE_PROFILE + SHAFT_PROFILE, n, math.pi, 2 * math.pi, closed=False)),
          DRS, UV_CYL)
    R_ab = 0.62 / math.cos(math.radians(22.5))
    p.add(G.bm_lathe([(R_ab - 0.05, 6.40), (R_ab, 6.45), (R_ab, 6.56), (R_ab - 0.03, C.SPRING_Z)], n=8,
                     phase=math.radians(22.5)), DRS, UV_BOX)
    return p


def build_vault_shaft():
    p = Piece("SM_VaultShaft", grounded=False)
    h = C.NAVE_VAULT_SPRING - C.SPRING_Z
    p.add(G.bm_lathe([(0.14, 0.0), (0.14, 0.08), (0.10, 0.14), (0.10, h - 0.30), (0.12, h - 0.26),
                      (0.12, h - 0.20), (0.10, h - 0.18), (0.16, h - 0.06), (0.17, h)], n=12), DRS, UV_CYL)
    return p


ARC_A = C.ARCADE_HALF_OPEN
ARC_RHO = 2.3 * ARC_A


def nave_top(x):
    return (C.NAVE_VAULT_SPRING - C.SPRING_Z) + G.pointed_height(min(abs(x), 2.0), 2.0, 2.6) + 0.25


def build_nave_bay_upper():
    """Arcade arch + spandrel + clerestory wall for one 4 m bay (local X along the bay)."""
    p = Piece("SM_NaveBayUpper", grounded=False)
    outline = [(-2.0, 0.0), (-ARC_A, 0.0)]
    outline += G.pointed_arch_pts(ARC_A, 0.0, ARC_RHO, 16)[::-1][1:-1]
    outline += [(ARC_A, 0.0), (2.0, 0.0)]
    n_top = 24
    for i in range(n_top + 1):
        x = 2.0 - 4.0 * i / n_top
        outline.append((x, nave_top(x)))
    cl = G.lancet_outline(0.42, 4.6, 7.0, rho_k=2.2, n=10)
    p.add(G.bm_profile_solid([outline, cl], C.NAVE_WALL_T, bevel=0.03, bevel_res=1), ASH, UV_BOX,
          matrix=TO_XZ)
    # two orders of arch mouldings (stepped soffit) and a hood mould
    p.add(G.bm_profile_solid([G.arch_band(ARC_A - 0.03, 0.26, 0.0, ARC_RHO - 0.03, 16)],
                             C.NAVE_WALL_T + 0.16, bevel=0.035), DRS, UV_BOX, matrix=TO_XZ)
    p.add(G.bm_profile_solid([G.arch_band(ARC_A - 0.13, 0.12, 0.0, ARC_RHO - 0.13, 16)],
                             C.NAVE_WALL_T - 0.22, bevel=0.03), DRS, UV_BOX, matrix=TO_XZ)
    p.add(G.bm_profile_solid([G.arch_band(ARC_A + 0.36, 0.09, 0.0, ARC_RHO + 0.36, 16)],
                             C.NAVE_WALL_T + 0.24, bevel=0.03), DRS, UV_BOX, matrix=TO_XZ)
    # clerestory surround + sill + string course
    p.add(G.bm_profile_solid([G.arch_band(0.40, 0.11, 7.0, 0.40 * 2.2, 10, foot=7.0 - 4.6)],
                             C.NAVE_WALL_T + 0.12, bevel=0.025), DRS, UV_BOX, matrix=TO_XZ)
    p.add(G.bm_box(4.0, C.NAVE_WALL_T + 0.24, 0.20, 0, 0, 4.42, bevel=0.05), DRS, UV_BOX)
    return p


def build_arch_aisle():
    p = Piece("SM_Arch_AisleTransverse", grounded=False)
    a_in, w = 1.45, 0.30
    rho_out = (3.8 ** 2 + (a_in + w) ** 2) / (2 * (a_in + w))
    p.add(G.bm_profile_solid([G.arch_band(a_in, w, 0.0, rho_out - w, 16)], 0.46, bevel=0.04), DRS, UV_BOX,
          matrix=TO_XZ)
    p.add(G.bm_profile_solid([G.arch_band(a_in - 0.10, 0.12, 0.0, rho_out - w - 0.10, 16)], 0.26, bevel=0.03),
          DRS, UV_BOX, matrix=TO_XZ)
    return p


def aisle_top(x):
    return C.SPRING_Z + G.pointed_height(min(abs(x), 2.0), 2.0, C.AISLE_VAULT_APEX - C.SPRING_Z) + 0.25


AISLE_WIN = dict(half_w=0.62, sill=2.2, spring=7.2, rho_k=2.4)


def build_aisle_wall_bay():
    """Outer wall bay with a tall lancet; local -Y is the room side."""
    p = Piece("SM_AisleWallBay")
    t = C.OUTER_WALL_T
    W = AISLE_WIN
    outline = [(-2.0, -0.45), (2.0, -0.45)]
    n_top = 24
    for i in range(n_top + 1):
        x = 2.0 - 4.0 * i / n_top
        outline.append((x, aisle_top(x)))
    win = G.lancet_outline(W["half_w"], W["sill"], W["spring"], W["rho_k"], 12)
    # wall centred so that its room face sits at local y = 0 (thickness goes +Y)
    p.add(G.bm_profile_solid([outline, win], t, bevel=0.03), ASH, UV_BOX, matrix=mat_t(0, t / 2, 0) @ TO_XZ)
    # window surround (inner face) and sill
    rho = W["rho_k"] * W["half_w"]
    p.add(G.bm_profile_solid([G.arch_band(W["half_w"] - 0.02, 0.15, W["spring"], rho - 0.02, 12,
                                          foot=W["spring"] - W["sill"])], 0.16, bevel=0.03),
          DRS, UV_BOX, matrix=mat_t(0, 0.02, 0) @ TO_XZ)
    p.add(G.bm_box(1.62, 0.34, 0.12, 0, -0.05, W["sill"] - 0.05, bevel=0.03), DRS, UV_BOX)
    # stone bench along the base
    p.add(G.bm_box(4.0, 0.36, 0.95, 0, -0.16, -0.025, bevel=0.05), DRS, UV_BOX)
    # pivot at the base centre: centre of the wall thickness on the floor line
    bmesh.ops.translate(p.bm, vec=(0, -t / 2, 0), verts=p.bm.verts)
    p.extra["room_face_y_local"] = -t / 2
    return p


def build_lancet_glass():
    p = Piece("SM_LancetGlass", grounded=False)
    W = AISLE_WIN
    hw = W["half_w"] + 0.04
    z0 = 0.0
    spring = W["spring"] - W["sill"] + 0.04
    rho = W["rho_k"] * W["half_w"] + 0.04
    pts = [(-hw, z0), (hw, z0)] + G.pointed_arch_pts(hw, spring, rho, 16)
    bm = G.bm_flat([pts])
    _planar_uv(bm, lambda x, z: ((x + hw) / (2 * hw), z / (2 * hw)))
    p.add(bm, GLN, UV_KEEP, matrix=TO_XZ)
    p.extra["offset_from_sill"] = -0.04
    return p


def build_clerestory_glass():
    p = Piece("SM_ClerestoryGlass", grounded=False)
    hw = 0.42 + 0.04
    spring = 7.0 - 4.6 + 0.04
    rho = 0.42 * 2.2 + 0.04
    pts = [(-hw, 0.0), (hw, 0.0)] + G.pointed_arch_pts(hw, spring, rho, 12)
    bm = G.bm_flat([pts])
    _planar_uv(bm, lambda x, z: ((x + hw) / (2 * hw), z / (2 * hw)))
    p.add(bm, GLN, UV_KEEP, matrix=TO_XZ)
    return p


def _planar_uv(bm, fn):
    """Assign UVs on an XY-plane bmesh before it is rotated into XZ (y acts as z)."""
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = fn(l.vert.co.x, l.vert.co.y)


def groin_vault(ax, ay, hA, hB, N=16, M=16):
    """Quadripartite groin vault surface z = max(hA(x), hB(y)), normals facing down.
    Returns (bmesh, groin_points[(x, y, z)] for the +x/+y quadrant)."""
    H = hA(0.0)
    groin = []
    for k in range(N + 1):
        s = k / N
        y = ay * (1 - s)
        target = hB(y)
        lo, hi = 0.0, ax
        for _ in range(50):
            mid = (lo + hi) / 2
            if hA(mid) > target:
                lo = mid
            else:
                hi = mid
        groin.append(((lo + hi) / 2 if k < N else 0.0, y, target if k < N else H))
    bm = bmesh.new()

    def tri_or_quad(vs):
        uniq = []
        for v in vs:
            if v not in uniq:
                uniq.append(v)
        if len(uniq) >= 3:
            try:
                bm.faces.new(uniq)
            except ValueError:
                pass

    cache = {}

    def V(x, y, z):
        key = (round(x, 6), round(y, 6), round(z, 6))
        if key not in cache:
            cache[key] = bm.verts.new(key)
        return cache[key]

    # region A (z = hA(x)) : rows at y = +-y_k spanning x in [-x_k, x_k]
    for sgn in (1, -1):
        rows = []
        for (gx, gy, gz) in groin:
            rows.append([V(-gx + 2 * gx * i / M, sgn * gy, hA(-gx + 2 * gx * i / M) if gx > 0 else H)
                         for i in range(M + 1)])
        for k in range(N):
            a, b = rows[k], rows[k + 1]
            for i in range(M):
                quad = [a[i], b[i], b[i + 1], a[i + 1]] if sgn > 0 else [a[i], a[i + 1], b[i + 1], b[i]]
                tri_or_quad(quad)
    # region B (z = hB(y)) : columns at x = +-x_k spanning y in [-y_k, y_k]
    for sgn in (1, -1):
        cols = []
        for (gx, gy, gz) in groin:
            cols.append([V(sgn * gx, -gy + 2 * gy * i / M, hB(-gy + 2 * gy * i / M) if gy > 0 else H)
                         for i in range(M + 1)])
        for k in range(N):
            a, b = cols[k], cols[k + 1]
            for i in range(M):
                quad = [a[i], a[i + 1], b[i + 1], b[i]] if sgn > 0 else [a[i], b[i], b[i + 1], a[i + 1]]
                tri_or_quad(quad)
    bm.normal_update()
    down = sum(f.normal.z * f.calc_area() for f in bm.faces)
    if down > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm, groin


def _vault_ribs(p, ax, ay, hA, groin, rib_w, rib_d, transverse=True):
    prof = [(rib_w / 2, 0.03), (-rib_w / 2, 0.03), (-rib_w / 2, -rib_d + 0.05), (-rib_w / 2 + 0.05, -rib_d),
            (rib_w / 2 - 0.05, -rib_d), (rib_w / 2, -rib_d + 0.05)]
    for sx in (1, -1):
        for sy in (1, -1):
            path = [(sx * gx, sy * gy, gz) for (gx, gy, gz) in groin]
            p.add(G.bm_sweep(path, prof, up=(0, 0, 1)), DRS, UV_BOX)
    if transverse:
        n = 32
        path = [(-ax + 2 * ax * i / n, -ay, hA(-ax + 2 * ax * i / n)) for i in range(n + 1)]
        p.add(G.bm_sweep(path, [(a * 1.3, b * 1.2) for (a, b) in prof], up=(0, 0, 1)), DRS, UV_BOX)
    # central boss
    H = hA(0.0)
    p.add(G.bm_lathe([(0.0001, H - 0.32), (0.16, H - 0.28), (0.24, H - 0.16), (0.22, H - 0.04), (0.18, H + 0.02)],
                     n=8, phase=math.radians(22.5)), DRS, UV_BOX)


def build_vault_nave():
    p = Piece("SM_Vault_NaveBay", grounded=False)
    ax, ay = C.NAVE_X, C.BAY / 2
    rise = C.NAVE_VAULT_APEX - C.NAVE_VAULT_SPRING

    def hA(x):
        return G.segmental_pointed(min(abs(x), ax), ax, rise, 1.6)

    def hB(y):
        return G.pointed_height(min(abs(y), ay), ay, rise)

    bm, groin = groin_vault(ax, ay, hA, hB, N=18, M=20)
    p.add(bm, ASH, UV_BOX)
    _vault_ribs(p, ax, ay, hA, groin, 0.24, 0.26)
    return p


def build_vault_aisle():
    p = Piece("SM_Vault_AisleBay", grounded=False)
    ax = ay = C.BAY / 2
    rise = C.AISLE_VAULT_APEX - C.SPRING_Z

    def h(v):
        return G.pointed_height(min(abs(v), ax), ax, rise)

    bm, groin = groin_vault(ax, ay, h, h, N=14, M=12)
    p.add(bm, ASH, UV_BOX)
    _vault_ribs(p, ax, ay, h, groin, 0.18, 0.20, transverse=False)
    return p


def apse_top(x):
    ax = C.NAVE_X
    return C.NAVE_VAULT_SPRING + G.segmental_pointed(min(abs(x), ax), ax,
                                                     C.NAVE_VAULT_APEX - C.NAVE_VAULT_SPRING, 1.6) + 0.35


def circle(cx, cz, r, n, phase=0.0):
    return [(cx + r * math.cos(phase + 2 * math.pi * i / n), cz + r * math.sin(phase + 2 * math.pi * i / n))
            for i in range(n)]


def build_apse_wall():
    """East wall of the nave; room face at local y = 0 (thickness +Y).  Rose opening, embrasure
    arch, blind arcade, dado, string course and flanking blind lancets."""
    p = Piece("SM_ApseWall")
    t = C.APSE_WALL_T
    hx = C.NAVE_X + 0.4
    outline = [(-hx, -0.45), (hx, -0.45)]
    n_top = 40
    for i in range(n_top + 1):
        x = hx - 2 * hx * i / n_top
        outline.append((x, apse_top(x)))
    hole = circle(0.0, C.ROSE_Z, C.ROSE_R_SURROUND, 96)
    p.add(G.bm_profile_solid([outline, hole], t, bevel=0.03), ASH, UV_BOX, matrix=mat_t(0, t / 2, 0) @ TO_XZ)

    def relief(loops, depth, z_off=0.0, bevel=0.025, mat=DRS, proud=None):
        # relief sits on the room face: centred so it protrudes `proud` in -Y
        pr = depth / 2 if proud is None else proud
        p.add(G.bm_profile_solid(loops, depth, bevel=bevel), mat, UV_BOX,
              matrix=mat_t(0, depth / 2 - pr, z_off) @ TO_XZ)

    # dado / bench
    p.add(G.bm_box(2 * hx, 0.50, 0.60, 0, -0.12, 0.30 - 0.25, bevel=0.05), DRS, UV_BOX)
    # string course under the rose
    p.add(G.bm_box(2 * hx, 0.34, 0.20, 0, -0.06, 4.05, bevel=0.05), DRS, UV_BOX)
    # embrasure: tall pointed frame around the rose, legs to the dado
    a_in, w = 3.85, 0.32
    spring = C.ROSE_Z
    rho = (4.2 ** 2 + a_in ** 2) / (2 * a_in)
    relief([G.arch_band(a_in, w, spring, rho, 24, foot=spring - 0.55)], 0.40, proud=0.20)
    relief([G.arch_band(a_in + w + 0.10, 0.10, spring, rho + w + 0.10, 24, foot=spring - 4.15)], 0.30, proud=0.16)
    # embrasure colonnettes
    for sx in (-1, 1):
        x = sx * (a_in + w / 2)
        p.add(G.bm_cylinder(0.10, 0.55, 4.0, n=12, cx=x, cy=-0.24), DRS, UV_CYL)
        p.add(G.bm_lathe([(0.10, 3.86), (0.16, 3.98), (0.18, 4.05)], n=12, cx=x, cy=-0.24), DRS, UV_BOX)
    # blind arcade: 5 niches inside the embrasure, 2 either side outside it
    def niche(cx, hw, z0, spring_z):
        relief([[(x + cx, z) for (x, z) in G.arch_band(hw, 0.09, spring_z, hw * 2.3, 10, foot=spring_z - z0)]],
               0.16, proud=0.10)

    inner = 2 * a_in / 5.0
    for i in range(5):
        cx = -a_in + inner * (i + 0.5)
        niche(cx, inner / 2 - 0.13, 0.60, 2.95)
    for sx in (-1, 1):
        for cxi in (5.15, 6.85):
            niche(sx * cxi, 0.62, 0.60, 2.95)
    # flanking blind lancets above the string course
    for sx in (-1, 1):
        cx = sx * 6.0
        relief([[(x + cx, z) for (x, z) in G.arch_band(0.55, 0.13, 8.8, 0.55 * 2.4, 12, foot=8.8 - 4.25)]],
               0.22, proud=0.12)
    bmesh.ops.translate(p.bm, vec=(0, -t / 2, 0), verts=p.bm.verts)
    p.extra["room_face_y_local"] = -t / 2
    return p


def build_rose_frame():
    p = Piece("SM_RoseFrame", grounded=False)
    outer = circle(0.0, 0.0, R.R_TRACERY, 128)
    loops = [outer] + R.opening_outlines()
    lift = C.ROSE_R_HOOD
    p.add(G.bm_profile_solid(loops, 0.30, bevel=0.03), DRS, UV_BOX, matrix=mat_t(0, 0, lift) @ TO_XZ)
    # raised moulded rings on the face
    for r_c, w, d in ((0.595, 0.05, 0.40), (2.225, 0.06, 0.42), (2.935, 0.06, 0.44)):
        ann = [circle(0, 0, r_c + w, 96), circle(0, 0, r_c - w, 96)]
        p.add(G.bm_profile_solid(ann, d, bevel=0.02), DRS, UV_BOX, matrix=mat_t(0, 0, lift) @ TO_XZ)
    # splayed surround from the tracery to the wall face (wall face at local y = -0.6)
    prof = [(R.R_TRACERY - 0.08, 0.10), (R.R_TRACERY - 0.02, -0.15), (3.14, -0.19), (3.18, -0.32),
            (3.30, -0.36), (3.36, -0.50), (C.ROSE_R_SURROUND, -0.56), (C.ROSE_R_SURROUND, -0.62),
            (3.50, -0.70), (3.58, -0.72), (C.ROSE_R_HOOD, -0.66), (C.ROSE_R_HOOD + 0.02, -0.56)]
    n = 96
    rings = []
    for r_, y in prof:
        rings.append([(r_ * math.cos(2 * math.pi * i / n), y, lift + r_ * math.sin(2 * math.pi * i / n))
                      for i in range(n)])
    bm = G.bm_loft(rings, cap_start=False, cap_end=False)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    p.add(bm, DRS, UV_BOX)
    p.extra["centre_z_local"] = lift
    return p


def build_rose_glass():
    p = Piece("SM_RoseGlass", grounded=False)
    r = R.R_OPEN + 0.08
    n = 128
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    lift = r
    c = bm.verts.new((0, 0, lift))
    rim = [bm.verts.new((r * math.cos(2 * math.pi * i / n), 0.0, lift + r * math.sin(2 * math.pi * i / n)))
           for i in range(n)]
    mid = [bm.verts.new((0.5 * r * math.cos(2 * math.pi * i / n), 0.0, lift + 0.5 * r * math.sin(2 * math.pi * i / n)))
           for i in range(n)]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([c, mid[j], mid[i]])
        bm.faces.new([mid[i], mid[j], rim[j], rim[i]])
    for f in bm.faces:
        for l in f.loops:
            x, z = l.vert.co.x, l.vert.co.z - lift
            l[uv].uv = (0.5 + x / (2 * C.ROSE_TEX_R), 0.5 + z / (2 * C.ROSE_TEX_R))
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    p.add(bm, GRS, UV_KEEP)
    p.extra["centre_z_local"] = lift
    return p


# ---------------------------------------------------------------------------
# Floor and water
# ---------------------------------------------------------------------------

def basin_z(X, Y):
    if Y <= C.FLAT_FLOOR_Y[1]:
        return 0.0
    fin = smoothstep(2.0, 4.8, Y)
    fout = smoothstep(16.6, 13.4, Y)
    d = C.BASIN_DEPTH * fin * fout + 0.12 * fin * (1 - fout)
    fx = 1.0 - 0.55 * smoothstep(5.8, 7.8, abs(X))
    wob = 0.022 * math.sin(X * 0.9 + 1.3) * math.sin(Y * 0.7 + 0.4) + 0.012 * math.sin(X * 2.3 + Y * 1.7)
    return -(d * fx) + wob * fin


def build_floor_strip():
    p = Piece("SM_Floor_Strip", grounded=False)
    y0, y1 = C.FLAT_FLOOR_Y
    L = y1 - y0
    p.add(G.bm_grid(26, 8, lambda x, y: 0.0, -12.9, 12.9, -L / 2, L / 2), FLR, UV_BOX)
    return p


BASIN_Y0, BASIN_Y1 = C.FLAT_FLOOR_Y[1], C.APSE_Y + 0.2


def build_floor_basin():
    p = Piece("SM_Floor_Basin", grounded=False)
    yc = (BASIN_Y0 + BASIN_Y1) / 2
    L = BASIN_Y1 - BASIN_Y0
    p.add(G.bm_grid(52, 37, lambda x, y: basin_z(x, y + yc), -12.9, 12.9, -L / 2, L / 2), FLR, UV_BOX)
    p.extra["centre_y"] = yc
    return p


WATER_Y0, WATER_Y1 = C.FLOOR_Y0, C.APSE_Y


def build_water():
    p = Piece("SM_Water", grounded=False)
    L = WATER_Y1 - WATER_Y0
    bm = G.bm_grid(12, 13, lambda x, y: 0.0, -12.0, 12.0, -L / 2, L / 2)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / C.WATER_UV_METRES, l.vert.co.y / C.WATER_UV_METRES)
    p.add(bm, WAT, UV_KEEP)
    p.extra["centre_y"] = (WATER_Y0 + WATER_Y1) / 2
    return p


# ---------------------------------------------------------------------------
# Furniture
# ---------------------------------------------------------------------------
PEW_L = 3.6


def _board(x0, x1, y0, y1, z0, z1, jag=None, rng=None, plane="XY"):
    """Box-like board; jag = 'x0' or 'x1' gives a splintered end."""
    if jag is None:
        return G.bm_box(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, bevel=0.012)
    if plane == "XY":     # horizontal board: outline in XY, thickness Z
        a0, a1, b0, b1, t0, t1 = x0, x1, y0, y1, z0, z1
    else:                 # vertical board: outline in XZ, thickness Y
        a0, a1, b0, b1, t0, t1 = x0, x1, z0, z1, y0, y1
    teeth = 5
    pts = []
    if jag == "x1":
        pts.append((a0, b0))
        for i in range(teeth + 1):
            b = b0 + (b1 - b0) * i / teeth
            pts.append((a1 + (rng.uniform(0.02, 0.16) if i % 2 else -rng.uniform(0.0, 0.05)), b))
        pts.append((a0, b1))
    else:
        pts.append((a1, b1))
        for i in range(teeth + 1):
            b = b1 - (b1 - b0) * i / teeth
            pts.append((a0 - (rng.uniform(0.02, 0.16) if i % 2 else -rng.uniform(0.0, 0.05)), b))
        pts.append((a1, b0))
    pts = _ccw(pts)
    bm = G.bm_profile_solid([pts], t1 - t0, bevel=0.008, bevel_res=0)
    if plane == "XY":
        bmesh.ops.translate(bm, vec=(0, 0, (t0 + t1) / 2), verts=bm.verts)
    else:
        bmesh.ops.transform(bm, matrix=mat_t(0, (t0 + t1) / 2, 0) @ TO_XZ, verts=bm.verts)
    return bm


def _ccw(pts):
    area = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        area += x0 * y1 - x1 * y0
    return pts if area > 0 else pts[::-1]


PEW_END = [(0.31, 0.0), (0.31, 0.60), (0.29, 0.64), (0.22, 0.665), (0.10, 0.675), (0.0, 0.70), (-0.07, 0.74),
           (-0.11, 0.81), (-0.13, 0.90), (-0.13, 1.00), (-0.16, 1.05), (-0.22, 1.17), (-0.28, 1.05),
           (-0.31, 1.00), (-0.31, 0.0)]


def _pew_end(x):
    bm = G.bm_profile_solid([_ccw(PEW_END)], 0.075, bevel=0.012)
    bmesh.ops.transform(bm, matrix=mat_t(x, 0, 0) @ TO_YZ, verts=bm.verts)
    return bm


def pew_parts(L=PEW_L, break_at=None, rng=None):
    """List of (bmesh, side) where side is 'L', 'R' or 'C' relative to break_at."""
    hx = L / 2
    parts = []
    if break_at is None:
        parts.append((_pew_end(-hx + 0.04), "L"))
        parts.append((_pew_end(hx - 0.04), "R"))
        parts.append((_board(-hx + 0.05, hx - 0.05, -0.25, 0.22, 0.42, 0.47), "C"))
        parts.append((_board(-hx + 0.05, hx - 0.05, -0.30, -0.255, 0.48, 0.92), "C"))
        parts.append((_board(-hx + 0.02, hx - 0.02, -0.33, -0.23, 0.90, 0.97), "C"))
        parts.append((_board(-hx + 0.06, hx - 0.06, -0.45, -0.30, 0.765, 0.79), "C"))
        parts.append((_board(-hx + 0.06, hx - 0.06, 0.17, 0.22, 0.34, 0.42), "C"))
        parts.append((_board(-0.035, 0.035, -0.22, 0.18, 0.0, 0.42), "C"))
        return parts
    b = break_at
    parts.append((_pew_end(-hx + 0.04), "L"))
    parts.append((_board(-hx + 0.05, b, -0.25, 0.22, 0.42, 0.47, "x1", rng), "L"))
    parts.append((_board(-hx + 0.05, b - 0.15, -0.30, -0.255, 0.48, 0.92, "x1", rng, "XZ"), "L"))
    parts.append((_board(-hx + 0.02, b + 0.20, -0.33, -0.23, 0.90, 0.97, "x1", rng), "L"))
    parts.append((_board(-hx + 0.06, b - 0.30, -0.45, -0.30, 0.765, 0.79, "x1", rng), "L"))
    parts.append((_board(-0.035 + b - 0.6, 0.035 + b - 0.6, -0.22, 0.18, 0.0, 0.42), "L"))
    parts.append((_board(b + 0.06, hx - 0.05, -0.25, 0.22, 0.42, 0.47, "x0", rng), "R"))
    parts.append((_board(b - 0.05, hx - 0.05, -0.30, -0.255, 0.48, 0.92, "x0", rng, "XZ"), "R"))
    parts.append((_board(b + 0.30, hx - 0.02, -0.33, -0.23, 0.90, 0.97, "x0", rng), "R"))
    return parts


def build_pew_intact():
    p = Piece("SM_Pew_Intact")
    for bm, _ in pew_parts():
        p.add(bm, WOD, UV_WOOD)
    return p


def build_pew_broken():
    p = Piece("SM_Pew_Broken")
    rng = random.Random(C.SEED + 101)
    b = 0.35
    sag = mat_t(b, 0, 0.45) @ mat_ry(13.0) @ mat_t(-b, 0, -0.45)
    for bm, side in pew_parts(break_at=b, rng=rng):
        if side == "R":
            bmesh.ops.transform(bm, matrix=sag, verts=bm.verts)
        p.add(bm, WOD, UV_WOOD)
    # the lost end panel lies flat beside the sagging half
    end = _pew_end(0.0)
    bmesh.ops.transform(end, matrix=mat_t(2.0, -0.70, 0.04) @ mat_ry(-90) @ mat_rz(8), verts=end.verts)
    p.add(end, WOD, UV_WOOD)
    _drop_to_ground(p, centre=True)
    return p


def build_pew_overturned():
    p = Piece("SM_Pew_Overturned")
    for bm, side in pew_parts():
        bmesh.ops.transform(bm, matrix=mat_rx(97.0), verts=bm.verts)
        p.add(bm, WOD, UV_WOOD)
    _drop_to_ground(p, centre=True)
    return p


def _drop_to_ground(p, centre=False):
    """Pivot = base centre: lowest point on Z = 0, bounding box centred in X and Y."""
    zs = [v.co.z for v in p.bm.verts]
    dz = -min(zs)
    dx = dy = 0.0
    if centre:
        xs = [v.co.x for v in p.bm.verts]
        ys = [v.co.y for v in p.bm.verts]
        dx = -(min(xs) + max(xs)) / 2
        dy = -(min(ys) + max(ys)) / 2
    bmesh.ops.translate(p.bm, vec=(dx, dy, dz), verts=p.bm.verts)


def build_debris_planks():
    p = Piece("SM_Debris_Planks")
    rng = random.Random(C.SEED + 111)
    specs = [(-0.6, 0.9, -0.12, 0.10, 0.0, 0.05, 6), (-0.8, 0.5, 0.15, 0.37, 0.0, 0.045, -9),
             (-0.3, 1.0, -0.1, 0.12, 0.045, 0.09, 31)]
    for (x0, x1, y0, y1, z0, z1, rot) in specs:
        bm = _board(x0, x1, y0, y1, z0, z1, "x1", rng)
        bmesh.ops.transform(bm, matrix=mat_rz(rot), verts=bm.verts)
        p.add(bm, WOD, UV_WOOD)
    _drop_to_ground(p, centre=True)
    return p


# ---------------------------------------------------------------------------
# Candles, stands, censers, chains
# ---------------------------------------------------------------------------

def _candle(p, rng, x, y, h, r, flames, variant):
    n = 10
    prof = [(r * 1.08, 0.0), (r, 0.015), (r * 0.985, h * 0.45), (r * 0.97, h - 0.014),
            (r * 1.03, h - 0.004), (r * 0.82, h), (r * 0.5, h - 0.010)]
    rings = [G.ring(lambda a, rr=rr: rr * (1 + 0.05 * math.sin(3 * a + x * 40)), z, n, 0.0, x, y)
             for (rr, z) in prof]
    p.add(G.bm_loft(rings, cap_start=True, cap_end=True), WAX, UV_CYL, tile=0.25)
    # drips
    for _ in range(rng.randint(1, 3)):
        a = rng.uniform(0, 2 * math.pi)
        dl = rng.uniform(0.25, 0.7) * h
        dx, dy = math.cos(a), math.sin(a)
        path = [(x + dx * r * 0.98, y + dy * r * 0.98, h - 0.01 - dl * t) for t in (0.0, 0.5, 1.0)]
        p.add(G.bm_sweep(path, G.circle_profile(0.008, 5), up=(1, 0, 0), scales=[1.0, 0.9, 0.5]),
              WAX, UV_BOX, tile=0.25)
    # wick
    p.add(G.bm_cylinder(0.003, h - 0.01, h + 0.012, n=4, cx=x, cy=y), IRN, UV_BOX)
    # flame: two crossed cards
    fh = 0.075 + 0.6 * r
    fw = fh * 0.42
    z0 = h + 0.004
    u0 = 0.0 if variant == 0 else 0.5
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    for ang in (0.0, 90.0):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        vs = [bm.verts.new((x - ca * fw / 2, y - sa * fw / 2, z0)), bm.verts.new((x + ca * fw / 2, y + sa * fw / 2, z0)),
              bm.verts.new((x + ca * fw / 2, y + sa * fw / 2, z0 + fh)), bm.verts.new((x - ca * fw / 2, y - sa * fw / 2, z0 + fh))]
        f = bm.faces.new(vs)
        for l, (u, v) in zip(f.loops, ((u0, 0.0), (u0 + 0.5, 0.0), (u0 + 0.5, 1.0), (u0, 1.0))):
            l[uv].uv = (u, v)
    p.add(bm, FLM, UV_KEEP)
    flames.append((x, y, z0 + fh * 0.35))


def _puddle(p, rng, rx, ry, h=0.014, cx=0.0, cy=0.0):
    n = 18
    radii = [1.0 + 0.18 * math.sin(i * 1.7 + rng.uniform(0, 1)) for i in range(n)]

    rings = []
    for (s, z) in ((1.0, 0.0), (0.97, h * 0.6), (0.85, h)):
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            ring.append((cx + rx * s * radii[i] * math.cos(a), cy + ry * s * radii[i] * math.sin(a), z))
        rings.append(ring)
    p.add(G.bm_loft(rings), WAX, UV_BOX, tile=0.25)


CLUSTERS = {
    "A": dict(puddle=(0.15, 0.13), candles=[(0.00, 0.02, 0.30, 0.040), (-0.08, -0.04, 0.22, 0.036),
                                           (0.07, -0.05, 0.16, 0.034), (0.06, 0.07, 0.12, 0.032),
                                           (-0.07, 0.07, 0.26, 0.038)]),
    "B": dict(puddle=(0.11, 0.10), candles=[(0.0, 0.03, 0.46, 0.045), (-0.055, -0.04, 0.36, 0.042),
                                           (0.06, -0.03, 0.28, 0.040)]),
    "C": dict(puddle=(0.19, 0.16), candles=[(0.0, 0.0, 0.14, 0.045), (-0.10, 0.03, 0.08, 0.040),
                                           (0.09, 0.05, 0.11, 0.038), (0.05, -0.09, 0.06, 0.042),
                                           (-0.05, -0.08, 0.10, 0.034), (0.13, -0.04, 0.05, 0.03),
                                           (-0.13, -0.05, 0.04, 0.032)]),
    "Rail": dict(puddle=(0.24, 0.05), candles=[(-0.15, 0.0, 0.18, 0.032), (0.0, 0.0, 0.26, 0.034),
                                              (0.14, 0.0, 0.12, 0.031)]),
}


def build_candle_cluster(key):
    spec = CLUSTERS[key]
    p = Piece("SM_CandleCluster_%s" % key, grounded=False)
    rng = random.Random(C.SEED + sum(map(ord, key)))
    _puddle(p, rng, *spec["puddle"])
    flames = []
    for i, (x, y, h, r) in enumerate(spec["candles"]):
        _candle(p, rng, x, y, h + 0.012, r, flames, i % 2)
    p.extra["flames"] = flames
    return p


def build_candle_stand():
    p = Piece("SM_CandleStand")
    top = 1.50
    p.add(G.bm_lathe([(0.026, 0.30), (0.026, 0.86), (0.05, 0.90), (0.026, 0.94), (0.024, 1.38),
                      (0.045, 1.41), (0.03, 1.44)], n=8), IRN, UV_CYL)
    p.add(G.bm_lathe([(0.0001, 0.27), (0.06, 0.29), (0.065, 0.34), (0.04, 0.38), (0.026, 0.40)], n=8), IRN, UV_BOX)
    # drip pan
    p.add(G.bm_lathe([(0.03, 1.43), (0.15, 1.46), (0.20, 1.48), (0.205, 1.50), (0.19, 1.505), (0.17, 1.485),
                      (0.0001, 1.475)], n=16), IRN, UV_BOX)
    # tripod legs with curled feet
    for k in range(3):
        a = math.radians(90 + 120 * k)
        ca, sa = math.cos(a), math.sin(a)
        path = [(ca * 0.03, sa * 0.03, 0.33), (ca * 0.12, sa * 0.12, 0.22), (ca * 0.22, sa * 0.22, 0.08),
                (ca * 0.30, sa * 0.30, 0.02), (ca * 0.35, sa * 0.35, 0.03), (ca * 0.37, sa * 0.37, 0.07)]
        p.add(G.bm_sweep(path, G.rect_profile(0.03, 0.022, 0.006), up=(0, 0, 1)), IRN, UV_BOX)
    p.extra["top_z"] = 1.48
    return p


def build_censer():
    p = Piece("SM_Censer", grounded=False)
    prof = [(0.0001, 0.0), (0.05, 0.0), (0.07, 0.02), (0.055, 0.045), (0.075, 0.06), (0.13, 0.10), (0.155, 0.15),
            (0.165, 0.18)]
    p.add(G.bm_lathe(prof, n=16), IRN, UV_BOX)
    lid = [(0.16, 0.20), (0.168, 0.215), (0.145, 0.27), (0.11, 0.32), (0.07, 0.36), (0.045, 0.39),
           (0.03, 0.42), (0.04, 0.45), (0.0001, 0.49)]
    p.add(G.bm_lathe(lid, n=16), IRN, UV_BOX)
    # glowing ember band between bowl and lid
    bm = G.bm_cylinder(0.150, 0.184, 0.198, n=16, caps=False)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (0.343, 0.50)       # dim orange edge of the flame texture
    p.add(bm, FLM, UV_KEEP)
    # three suspension chains (stylised rods) to a top ring
    for k in range(3):
        a = math.radians(90 + 120 * k)
        path = [(0.162 * math.cos(a), 0.162 * math.sin(a), 0.19), (0.02 * math.cos(a), 0.02 * math.sin(a), 0.80)]
        p.add(G.bm_sweep(path, G.circle_profile(0.007, 4), up=(0, 0, 1)), IRN, UV_BOX)
    ring_path = [(0.04 * math.cos(2 * math.pi * i / 10), 0.0, 0.84 + 0.04 * math.sin(2 * math.pi * i / 10)) for i in range(10)]
    p.add(G.bm_sweep(ring_path, G.circle_profile(0.009, 4), up=(0, 1, 0), closed_path=True), IRN, UV_BOX)
    p.extra["top_z"] = 0.88
    p.extra["ember"] = (0.0, 0.0, 0.19)
    return p


def build_chain():
    p = Piece("SM_Chain_1m", grounded=False)
    pitch = 0.125
    L, W, wire = 0.165, 0.07, 0.012
    for k in range(8):
        zc = pitch * k + L / 2 - 0.02
        rot = 0 if k % 2 == 0 else 90
        path = []
        n = 8
        for i in range(n):
            a = 2 * math.pi * i / n
            path.append(((W / 2) * math.cos(a), 0.0, zc + (L / 2 - W / 2) * (1 if math.sin(a) >= 0 else -1) +
                         (W / 2) * math.sin(a)))
        bm = G.bm_sweep(path, G.circle_profile(wire, 3), up=(0, 1, 0), closed_path=True)
        bmesh.ops.transform(bm, matrix=mat_rz(rot), verts=bm.verts)
        p.add(bm, IRN, UV_BOX)
    return p


# ---------------------------------------------------------------------------
# Altar and steps
# ---------------------------------------------------------------------------
STEPS = [(16.40, 0.08), (16.85, 0.26), (17.30, 0.44)]   # (front edge Y, top Z)
STEPS_YC = (16.40 + C.APSE_Y) / 2
PLATFORM_Z = 0.44


def build_altar_steps():
    p = Piece("SM_AltarSteps")
    hx = 5.4
    for i, (y_front, top) in enumerate(STEPS):
        y0 = y_front - STEPS_YC
        y1 = C.APSE_Y - STEPS_YC + 0.2
        w = 2 * hx - i * 0.5
        p.add(G.bm_box(w, y1 - y0, top + 0.5, 0, (y0 + y1) / 2, (top - 0.5) / 2, bevel=0.035), DRS, UV_BOX)
    return p


def build_altar():
    p = Piece("SM_Altar")
    p.add(G.bm_box(2.95, 1.22, 0.16, 0, 0, 0.08, bevel=0.03), DRS, UV_BOX)
    p.add(G.bm_box(2.62, 0.96, 0.80, 0, 0, 0.55, bevel=0.03), DRS, UV_BOX)
    p.add(G.bm_box(2.98, 1.26, 0.14, 0, 0, 1.02, bevel=0.035), DRS, UV_BOX)
    # blind niches on the front face
    for cx in (-0.85, 0.0, 0.85):
        band = [(x + cx, z) for (x, z) in G.arch_band(0.24, 0.06, 0.62, 0.24 * 2.3, 8, foot=0.62 - 0.22)]
        p.add(G.bm_profile_solid([band], 0.08, bevel=0.012), DRS, UV_BOX, matrix=mat_t(0, -0.48 - 0.02, 0) @ TO_XZ)
    # altar cloth: top sheet + front fall with a tattered hem and folds
    rng = random.Random(C.SEED + 131)
    top_z = 1.09
    p.add(G.bm_box(2.40, 1.04, 0.012, 0, 0.0, top_z + 0.006, bevel=0.0), CLO, UV_BOX, tile=0.8)
    nx, nz = 24, 7
    hem = [0.50 + 0.10 * rng.random() + 0.05 * math.sin(i * 1.3) for i in range(nx + 1)]
    bm = bmesh.new()
    grid = []
    for j in range(nz + 1):
        row = []
        for i in range(nx + 1):
            x = -1.15 + 2.30 * i / nx
            s = j / nz                       # 0 at the fold, 1 at the hem
            if j == 0:
                y, z = -0.52, top_z + 0.012
            elif j == 1:
                y, z = -0.635, top_z - 0.01
            else:
                z = (top_z - 0.04) - (top_z - 0.04 - hem[i]) * (s - 1 / nz) / (1 - 1 / nz)
                y = -0.645 - 0.018 * math.sin(x * 9.0) * s
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(nz):
        for i in range(nx):
            bm.faces.new([grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]])
    bm.normal_update()
    if sum(f.normal.y for f in bm.faces) > 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    p.add(bm, CLO, UV_PLANAR_XZ, tile=0.8)
    p.extra["top_z"] = top_z + 0.012
    return p


# ---------------------------------------------------------------------------
# Rubble and foreground silhouettes
# ---------------------------------------------------------------------------

def _rock(rng, sx, sy, sz, cx, cy, cz, jitter=0.18, rot=0.0):
    bm = G.bm_box(sx, sy, sz, 0, 0, 0, bevel=min(sx, sy, sz) * 0.18, segments=1)
    for v in bm.verts:
        v.co.x += rng.uniform(-jitter, jitter) * sx * 0.3
        v.co.y += rng.uniform(-jitter, jitter) * sy * 0.3
        v.co.z += rng.uniform(-jitter, jitter) * sz * 0.3
    bmesh.ops.transform(bm, matrix=mat_t(cx, cy, cz) @ mat_rz(rot), verts=bm.verts)
    return bm


def build_rubble_block():
    p = Piece("SM_Rubble_Block")
    rng = random.Random(C.SEED + 201)
    p.add(_rock(rng, 0.66, 0.44, 0.38, 0, 0, 0.19, 0.2), DRS, UV_BOX)
    _drop_to_ground(p, centre=True)
    return p


def build_rubble_drum():
    p = Piece("SM_Rubble_Drum")
    rng = random.Random(C.SEED + 211)
    prof = [(0.0, 0.0), (0.56, 0.0)]
    rings = cluster_rings(prof, 40)
    # broken top: jitter the top ring
    rings[1] = [(x, y, z + rng.uniform(-0.12, 0.08)) for (x, y, z) in rings[1]]
    bm = G.bm_loft(rings)
    bmesh.ops.transform(bm, matrix=mat_rx(90) @ mat_rz(10), verts=bm.verts)
    p.add(bm, DRS, UV_BOX)
    _drop_to_ground(p, centre=True)
    return p


def build_rubble_pile():
    p = Piece("SM_Rubble_Pile")
    rng = random.Random(C.SEED + 221)
    for i in range(8):
        a = rng.uniform(0, 2 * math.pi)
        d = rng.uniform(0.0, 0.45)
        s = rng.uniform(0.16, 0.34)
        p.add(_rock(rng, s * 1.3, s, s * 0.8, d * math.cos(a), d * math.sin(a), s * 0.35 + (0.45 - d) * 0.25,
                    rot=rng.uniform(0, 90)), DRS, UV_BOX)
    _drop_to_ground(p, centre=True)
    return p


def build_rubble_slab():
    p = Piece("SM_Rubble_Slab")
    rng = random.Random(C.SEED + 231)
    p.add(_rock(rng, 1.05, 0.72, 0.13, 0, 0, 0.065, 0.08), FLR, UV_BOX, tile=3.0)
    _drop_to_ground(p, centre=True)
    return p


def build_fg_broken_base():
    p = Piece("SM_FG_BrokenBase")
    rng = random.Random(C.SEED + 241)
    p.add(octagon_slab(0.55, -0.30, 0.30, 0.04), DRS, UV_BOX)
    prof = BASE_PROFILE + [(0.80, 0.0), (1.02, 0.0)]
    rings = cluster_rings(prof, 48)
    rings[-1] = [(x, y, z + rng.uniform(-0.26, 0.12) * (0.6 + 0.4 * math.cos(math.atan2(y, x) * 2)))
                 for (x, y, z) in rings[-1]]
    p.add(G.bm_loft(rings), DRS, UV_CYL)
    p.add(_rock(rng, 0.42, 0.34, 0.26, 0.62, -0.30, 0.13, rot=24), DRS, UV_BOX)
    return p


def build_fg_rubble_heap():
    p = Piece("SM_FG_RubbleHeap")
    rng = random.Random(C.SEED + 251)
    for i in range(13):
        x = rng.uniform(-0.85, 0.85)
        y = rng.uniform(-0.55, 0.55)
        s = rng.uniform(0.22, 0.55)
        h = max(0.0, 0.85 - (abs(x) * 0.7 + abs(y) * 0.6)) * 0.55
        p.add(_rock(rng, s * 1.25, s, s * 0.75, x, y, h + s * 0.3, rot=rng.uniform(0, 90)), DRS, UV_BOX)
    _drop_to_ground(p, centre=True)
    return p


# ---------------------------------------------------------------------------
# Decals (single quads into the 2x2 atlas)
# ---------------------------------------------------------------------------

def _decal(name, w, h, cell, plane="XZ"):
    p = Piece(name, grounded=False)
    u0, v0 = {"TL": (0.0, 0.5), "TR": (0.5, 0.5), "BL": (0.0, 0.0), "BR": (0.5, 0.0)}[cell]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    if plane == "XZ":
        co = [(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)]
    else:
        co = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    vs = [bm.verts.new(c) for c in co]
    f = bm.faces.new(vs)
    for l, (u, v) in zip(f.loops, ((u0, v0), (u0 + 0.5, v0), (u0 + 0.5, v0 + 0.5), (u0, v0 + 0.5))):
        l[uv].uv = (u, v)
    bm.normal_update()
    assert (plane == "XZ" and f.normal.y < 0) or (plane == "XY" and f.normal.z > 0)
    p.add(bm, DEC, UV_KEEP)
    return p


def build_decals():
    return [_decal("SM_Decal_Drip", 1.4, 2.4, "TL"), _decal("SM_Decal_Tide", 4.0, 0.9, "TR"),
            _decal("SM_Decal_Moss", 1.1, 1.1, "BL"), _decal("SM_Decal_Silt", 2.4, 2.4, "BR", plane="XY")]


# ---------------------------------------------------------------------------
def build_all():
    pieces = [build_column(), build_respond(), build_vault_shaft(), build_nave_bay_upper(), build_arch_aisle(),
              build_aisle_wall_bay(), build_lancet_glass(), build_clerestory_glass(), build_vault_nave(),
              build_vault_aisle(), build_apse_wall(), build_rose_frame(), build_rose_glass(),
              build_floor_strip(), build_floor_basin(), build_water(),
              build_pew_intact(), build_pew_broken(), build_pew_overturned(), build_debris_planks(),
              build_candle_cluster("A"), build_candle_cluster("B"), build_candle_cluster("C"),
              build_candle_cluster("Rail"), build_candle_stand(), build_censer(), build_chain(),
              build_altar_steps(), build_altar(),
              build_rubble_block(), build_rubble_drum(), build_rubble_pile(), build_rubble_slab(),
              build_fg_broken_base(), build_fg_rubble_heap()]
    pieces += build_decals()
    return pieces
