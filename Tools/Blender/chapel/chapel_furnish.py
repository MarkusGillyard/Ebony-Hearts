"""The Drowned Chapel's furnishings (interior stage 2), built with the Chapel kit's helpers so they share its look.
Placeholders made with AI assistance; the creator authors the final art (the mural and devotional boards are blank
slots for his illustrations; Dwar is a grey placeholder figure).

World pieces (Blender metres, the nave's frame; Unreal = (x, -y, z) * 100), placed at the origin:
  SM_IX_Kneeler      the sanctuary's kneeler: a kneeling board, a desk carrying a cracked heart, and a white-to-black
                     inlay of nine stones at the platform's edge
  SM_IX_ForgeHearth  the forge's hearth, hood and flue, its embers and a bellows (north transept)
  SM_IX_ForgeWork    the anvil on its stump, the quench trough, the counter and its goods, a weapon rack
  SM_IX_ForgeWater   the trough's water
  SM_IX_Dwar         Dwar's stand-in (a plain figure in the placeholder grid material)
  SM_IX_Mural        the Hall of the Six's end-wall panel (blank, framed: an illustration slot)
  SM_IX_Camp         the present occupants' camp: bedrolls, a brazier with embers, crates, a sack, a pot
Local pieces (origin given per piece; placed by Tools/Unreal/build_chapel_interior.py):
  SM_IX_Saintess     the Ebony Saintess: one veiled figure on a slim plinth (origin: plinth base centre; faces -Y)
  SM_IX_Alcove       one of the Hall of the Six's alcoves (origin: on the floor at the wall face; the room is -Y)
  SM_IX_Trace_*      the traces in the alcoves (origin: the plinth top's centre): Wren, Ashka, Mirela, Nix, Bram
  SM_IX_Board        a devotional board (origin: its bottom centre at the wall; faces -Y): an illustration slot

Usage: blender -b --factory-startup -P chapel_furnish.py -- <out dir>
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chapel_geo as G      # noqa: E402
import chapel_pieces as P   # noqa: E402
from chapel_geo import Piece, UV_BOX, UV_CYL, UV_WOOD, TO_XZ, TO_YZ, mat_t, mat_rx, mat_ry, mat_rz   # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)

ASH, DRS, FLR, WOD, IRN, WAX, CLO, WAT = P.ASH, P.DRS, P.FLR, P.WOD, P.IRN, P.WAX, P.CLO, P.WAT
CLOTH_BLACK, CLOTH_BLUE, CLOTH_PALE, CLOTH_DUN = "M_IX_ClothBlack", "M_IX_ClothBlue", "M_IX_ClothPale", "M_IX_ClothDun"
EMBER, LIME, FLARE, PH = "M_IX_Ember", "M_IX_LimeWater", "M_IX_FlareRed", "M_PH_Blockout"
PLASTER = "M_IX_Plaster"
G.MAT_TILE.update({CLOTH_BLACK: 0.8, CLOTH_BLUE: 0.8, CLOTH_PALE: 0.8, CLOTH_DUN: 0.8, EMBER: 0.5, LIME: 0.5, FLARE: 0.4, PH: 1.0, PLASTER: 1.5})

FBX = dict(use_selection=True, object_types={"MESH"}, global_scale=1.0, apply_unit_scale=True,
           apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y", bake_space_transform=True,
           use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=False, use_triangles=True, colors_type="SRGB",
           prioritize_active_color=False, use_custom_props=False, add_leaf_bones=False, bake_anim=False,
           path_mode="STRIP", embed_textures=False, batch_mode="OFF")

PLATFORM_Z = 0.44
TR_FLOOR = 0.45


def box(x0, x1, y0, y1, z0, z1, bevel=0.0):
    return G.bm_box(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, bevel=bevel)


def cyl(r, z0, z1, cx=0.0, cy=0.0, n=10, r_top=None):
    return G.bm_cylinder(r, z0, z1, n, cx, cy, r_top=r_top)


def heart_point(t, scale):
    x = 16 * math.sin(t) ** 3
    z = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
    return (x * scale / 16.0, z * scale / 16.0)


def split_heart(scale, gap=0.014, seed=3, n=24):
    """The heart in two halves along a jagged crack from the top notch (t = 0) to the point (t = pi)."""
    rng = random.Random(seed)
    top, bottom = heart_point(0.0, scale), heart_point(math.pi, scale)
    crack = [top] + [(rng.uniform(-0.12, 0.12) * scale, top[1] + (bottom[1] - top[1]) * i / 6) for i in range(1, 6)] + [bottom]
    right = [heart_point(math.pi * i / n, scale) for i in range(1, n)]
    left = [heart_point(math.pi + math.pi * i / n, scale) for i in range(1, n)]
    rpoly = [(x + gap / 2, z) for (x, z) in crack] [:1] + right + [(x + gap / 2, z) for (x, z) in crack[::-1]][:-1]
    lpoly = left + [(x - gap / 2, z) for (x, z) in crack]
    return _ccw(lpoly), _ccw(rpoly)


def _ccw(pts):
    a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return pts if a > 0 else pts[::-1]


# ------------------------------------------------------------------ the sanctuary
def kneeler():
    p = Piece("SM_IX_Kneeler")
    z = PLATFORM_Z
    # kneeling board (worn wood) and the desk in front of it, toward the altar
    p.add(box(-0.75, 0.75, 17.48, 17.78, z, z + 0.12, 0.02), WOD, UV_WOOD)
    p.add(box(-0.7, 0.7, 17.5, 17.76, z + 0.12, z + 0.15, 0.01), CLO, UV_BOX)
    p.add(box(-0.62, 0.62, 17.9, 18.06, z, z + 0.78, 0.02), WOD, UV_WOOD)
    p.add(box(-0.72, 0.72, 17.86, 18.14, z + 0.78, z + 0.84, 0.015), WOD, UV_WOOD)
    # the cracked heart on the desk's face, toward the kneeler
    for half in split_heart(0.2):
        p.add(G.bm_profile_solid([half], 0.03, bevel=0.006), DRS, UV_BOX, matrix=mat_t(0, 17.885, z + 0.46) @ TO_XZ)
    # nine stones at the platform's edge, white to black (wax, stone, iron)
    for i in range(9):
        x0 = -1.35 + i * 0.3
        mat = PLASTER if i < 3 else (DRS if i < 6 else IRN)
        p.add(box(x0 + 0.01, x0 + 0.29, 17.33, 17.45, z - 0.02, z + 0.004, 0.005), mat, UV_BOX)
    return p


def saintess():
    """The Ebony Saintess: one veiled figure, faceless, hands folded under the veil, on a slim plinth behind the altar
    and beneath the rose window (the space there is about half a metre deep, so she is flattened front to back).
    Origin: the plinth's base centre on the sanctuary platform. Faces -Y."""
    p = Piece("SM_IX_Saintess")
    p.add(box(-0.45, 0.45, -0.22, 0.22, 0.0, 1.15, 0.03), DRS, UV_BOX)
    p.add(box(-0.5, 0.5, -0.25, 0.25, 1.1, 1.2, 0.03), DRS, UV_BOX)
    figure(p, 1.2, depth=0.62)
    return p


def figure(p, base, depth=1.0):
    """The veiled figure from base upward, its depth (Y) scaled."""
    sy = depth
    # robe: a lathe from the hem up to the shoulders, slightly flared and pleated
    prof = [(0.36, 0.0), (0.33, 0.25), (0.27, 0.9), (0.23, 1.35), (0.24, 1.6), (0.2, 1.75), (0.11, 1.82)]
    rings = []
    for (r, h) in prof:
        ring = G.ring(lambda a, r=r: r * (1.0 + 0.04 * math.sin(a * 9)) * (1.0 + 0.12 * max(0.0, -math.sin(a))), base + h, 18)
        rings.append([(x, y * sy, z) for (x, y, z) in ring])
    p.add(G.bm_loft(rings), DRS, UV_CYL)
    # head under the veil, the veil falling to the shoulders and the back
    p.add(G.bm_lathe([(0.0, base + 1.8), (0.11, base + 1.84), (0.13, base + 1.96), (0.12, base + 2.08), (0.07, base + 2.16),
                      (0.0, base + 2.18)], 14), DRS, UV_CYL, matrix=G.mat_s(1.0, max(sy, 0.85), 1.0))
    veil = [(0.0, base + 2.22), (0.15, base + 2.12), (0.19, base + 1.96), (0.25, base + 1.78), (0.31, base + 1.55),
            (0.33, base + 1.2)]
    p.add(G.bm_lathe(veil, 16), DRS, UV_CYL, matrix=mat_t(0, 0.03 * sy, 0) @ G.mat_s(1.0, sy, 1.0))
    # folded hands, a fold of the veil across the chest
    p.add(box(-0.13, 0.13, -0.3 * sy, -0.18 * sy, base + 1.12, base + 1.3, 0.05), DRS, UV_BOX)


# ------------------------------------------------------------------ the forge (north transept, -X)
def forge_hearth():
    p = Piece("SM_IX_ForgeHearth")
    f = TR_FLOOR
    x_wall = -21.9
    # the firebox, a recess on top for the coals
    p.add(box(x_wall, x_wall + 1.25, 6.6, 9.4, f, f + 0.85, 0.04), DRS, UV_BOX)
    p.add(box(x_wall, x_wall + 1.35, 6.5, 9.5, f + 0.85, f + 0.98, 0.03), DRS, UV_BOX)
    rng = random.Random(21)
    p.add(box(x_wall + 0.2, x_wall + 1.05, 7.0, 9.0, f + 0.9, f + 0.95), EMBER, UV_BOX)
    for _ in range(26):
        cx, cy = rng.uniform(x_wall + 0.3, x_wall + 0.95), rng.uniform(7.1, 8.9)
        s = rng.uniform(0.05, 0.11)
        p.add(G.bm_box(s, s * 1.2, s * 0.7, cx, cy, f + 0.98, bevel=s * 0.3),
              EMBER if rng.random() < 0.55 else IRN, UV_BOX, matrix=mat_t(cx, cy, f + 0.98) @ mat_rz(rng.uniform(0, 90)) @ mat_t(-cx, -cy, -(f + 0.98)))
    # the hood: a stone frustum over the fire, its back against the wall, an iron band at its lip, a flue into the wall
    lo, hi = f + 2.1, f + 3.7
    rings = [[(x_wall, 6.3, lo), (x_wall + 1.6, 6.3, lo), (x_wall + 1.6, 9.7, lo), (x_wall, 9.7, lo)],
             [(x_wall, 7.4, hi), (x_wall + 0.7, 7.4, hi), (x_wall + 0.7, 8.6, hi), (x_wall, 8.6, hi)]]
    bm = bmesh.new()
    vs = [[bm.verts.new(v) for v in r] for r in rings]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vs[0][i], vs[0][j], vs[1][j], vs[1][i]))
    bm.faces.new(vs[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.solidify(bm, geom=bm.faces, thickness=0.12)
    p.add(bm, DRS, UV_BOX)
    p.add(box(x_wall, x_wall + 1.66, 6.24, 9.76, lo - 0.12, lo + 0.02, 0.02), IRN, UV_BOX)
    # the bellows beside the hearth
    bel = [(-0.45, 0.0), (0.0, 0.26), (0.45, 0.0), (0.0, -0.26)]
    p.add(G.bm_profile_solid([bel], 0.32, bevel=0.03), WOD, UV_WOOD, matrix=mat_t(x_wall + 1.0, 10.1, f + 0.7) @ mat_ry(90) @ mat_rx(0))
    p.add(cyl(0.05, f, f + 0.6, x_wall + 1.0, 10.1, 6), WOD, UV_CYL)
    return p


def forge_work():
    p = Piece("SM_IX_ForgeWork")
    f = TR_FLOOR
    # the anvil on its stump
    ax, ay = -18.5, 8.2
    p.add(cyl(0.34, f, f + 0.52, ax, ay, 12, r_top=0.32), WOD, UV_CYL)
    p.add(box(ax - 0.18, ax + 0.18, ay - 0.13, ay + 0.13, f + 0.52, f + 0.62, 0.01), IRN, UV_BOX)
    p.add(box(ax - 0.12, ax + 0.12, ay - 0.09, ay + 0.09, f + 0.62, f + 0.74, 0.01), IRN, UV_BOX)
    p.add(box(ax - 0.3, ax + 0.26, ay - 0.12, ay + 0.12, f + 0.74, f + 0.88, 0.015), IRN, UV_BOX)
    horn = G.bm_cylinder(0.075, 0.0, 0.32, 10, r_top=0.008)
    p.add(horn, IRN, UV_BOX, matrix=mat_t(ax + 0.26, ay, f + 0.82) @ mat_ry(90))
    p.add(box(ax + 0.05, ax + 0.4, ay - 0.025, ay + 0.025, f + 0.885, f + 0.905), IRN, UV_BOX)   # a hammer on the face
    # the quench trough by the side wall, near the hearth
    tx0, tx1, ty0, ty1 = -20.6, -19.0, 10.85, 11.5
    for (x0, x1, y0, y1) in ((tx0, tx1, ty0, ty0 + 0.1), (tx0, tx1, ty1 - 0.1, ty1), (tx0, tx0 + 0.1, ty0, ty1), (tx1 - 0.1, tx1, ty0, ty1)):
        p.add(box(x0, x1, y0, y1, f, f + 0.7, 0.02), DRS, UV_BOX)
    p.add(box(tx0, tx1, ty0, ty1, f, f + 0.12), DRS, UV_BOX)
    # the counter (the shop) along the west side wall near the arches, and what stands on it
    cx0, cx1, cy0, cy1 = -18.5, -14.6, 4.45, 5.3
    p.add(box(cx0, cx1, cy0 + 0.05, cy1 - 0.05, f, f + 0.95, 0.02), WOD, UV_WOOD)
    p.add(box(cx0 - 0.05, cx1 + 0.05, cy0, cy1, f + 0.95, f + 1.02, 0.015), WOD, UV_WOOD)
    rng = random.Random(33)
    x = cx0 + 0.3
    while x < cx1 - 0.3:
        kind = rng.random()
        if kind < 0.4:
            h = rng.uniform(0.18, 0.32)
            p.add(cyl(rng.uniform(0.07, 0.11), f + 1.02, f + 1.02 + h, x, rng.uniform(4.75, 5.0), 10, r_top=0.05), DRS, UV_CYL)
            x += 0.32
        elif kind < 0.75:
            s = rng.uniform(0.22, 0.34)
            p.add(G.bm_box(s, s * 0.8, s * 0.7, x, 4.85, f + 1.02 + s * 0.35, bevel=0.01), WOD, UV_WOOD)
            x += s + 0.12
        else:
            p.add(cyl(0.12, f + 1.02, f + 1.1, x, 4.85, 12), CLOTH_DUN, UV_CYL)    # a bundle
            x += 0.34
    # the weapon rack on the east side wall: a frame and four plain blades waiting for work
    rx0, rx1, ry = -16.9, -14.6, 11.45
    for xx in (rx0, rx1):
        p.add(box(xx - 0.05, xx + 0.05, ry - 0.25, ry, f, f + 1.6, 0.01), WOD, UV_WOOD)
    for zz in (f + 0.35, f + 1.25):
        p.add(box(rx0, rx1, ry - 0.22, ry - 0.12, zz, zz + 0.06, 0.01), WOD, UV_WOOD)
    for i in range(4):
        bx = rx0 + 0.4 + i * 0.5
        p.add(box(bx - 0.025, bx + 0.025, ry - 0.2, ry - 0.15, f + 0.3, f + 1.4, 0.004), IRN, UV_BOX)
        p.add(box(bx - 0.1, bx + 0.1, ry - 0.21, ry - 0.14, f + 1.4, f + 1.44, 0.004), IRN, UV_BOX)
        p.add(cyl(0.022, f + 1.44, f + 1.62, bx, ry - 0.175, 6), WOD, UV_CYL)
    return p


def forge_water():
    p = Piece("SM_IX_ForgeWater", grounded=False)
    p.add(G.bm_grid(2, 1, lambda x, y: TR_FLOOR + 0.58, -20.5, -19.1, 10.95, 11.4), WAT, UV_BOX)
    return p


def dwar():
    """A plain stand-in figure (placeholder grid), facing +X toward the arches. Dwar is a Dwarf; his look, size and
    voice are the creator's to author."""
    p = Piece("SM_IX_Dwar")
    f = TR_FLOOR
    bx, by = -19.8, 6.8
    p.add(cyl(0.2, f, f + 0.7, bx, by - 0.14, 8), PH, UV_CYL)
    p.add(cyl(0.2, f, f + 0.7, bx, by + 0.14, 8), PH, UV_CYL)
    p.add(cyl(0.36, f + 0.65, f + 1.25, bx, by, 10, r_top=0.4), PH, UV_CYL)
    p.add(G.bm_lathe([(0.0, f + 1.25), (0.16, f + 1.27), (0.18, f + 1.42), (0.14, f + 1.55), (0.0, f + 1.58)], 10, cx=bx, cy=by), PH, UV_CYL)
    for s in (-1, 1):
        p.add(cyl(0.1, f + 0.7, f + 1.2, bx + 0.05, by + s * 0.45, 6), PH, UV_CYL)
    return p


# ------------------------------------------------------------------ the Hall of the Six (south transept, +X)
def alcove():
    """Origin on the floor at the wall face; the room is local -Y."""
    p = Piece("SM_IX_Alcove")
    p.add(box(-0.7, 0.7, -0.5, 0.0, 0.0, 0.6, 0.03), DRS, UV_BOX)
    p.add(box(-0.75, 0.75, -0.55, 0.0, 0.6, 0.67, 0.02), DRS, UV_BOX)
    # the back: a shallow arched panel with a dressed band, and a blank plaque on the plinth's face (names worn away)
    p.add(G.bm_profile_solid([G.lancet_outline(0.62, 0.67, 2.4, 1.6, 12)], 0.08, bevel=0.01), DRS, UV_BOX,
          matrix=mat_t(0, -0.04, 0) @ TO_XZ)
    p.add(G.bm_profile_solid([G.arch_band(0.62, 0.1, 2.4, 0.62 * 1.6, 12, foot=1.73)], 0.14, bevel=0.015), DRS, UV_BOX,
          matrix=mat_t(0, -0.1, 0) @ TO_XZ)
    p.add(box(-0.32, 0.32, -0.53, -0.5, 0.22, 0.42, 0.01), DRS, UV_BOX)
    return p


def trace_wren():
    """A black and ocean-blue cloth binding wound round a short striking post, its top worn smooth."""
    p = Piece("SM_IX_Trace_Wren")
    p.add(cyl(0.09, 0.0, 0.85, 0, -0.05, 10), WOD, UV_CYL)
    for i, z in enumerate((0.15, 0.27, 0.39, 0.51, 0.63)):
        p.add(cyl(0.104, z, z + 0.09, 0, -0.05, 12), CLOTH_BLACK if i % 2 == 0 else CLOTH_BLUE, UV_CYL)
    p.add(box(0.06, 0.4, -0.2, 0.1, 0.0, 0.02, 0.005), CLOTH_BLUE, UV_BOX)     # a loose end lying on the plinth
    return p


def trace_ashka():
    """An unlit cross-shaped lamp."""
    p = Piece("SM_IX_Trace_Ashka")
    p.add(box(-0.12, 0.12, -0.12, 0.12, 0.0, 0.04, 0.01), IRN, UV_BOX)
    p.add(box(-0.03, 0.03, -0.03, 0.03, 0.04, 0.62, 0.005), IRN, UV_BOX)
    p.add(box(-0.2, 0.2, -0.03, 0.03, 0.4, 0.46, 0.005), IRN, UV_BOX)
    for (x0, x1, z0, z1) in ((-0.09, 0.09, 0.2, 0.36),):
        for (a, b) in ((x0, x0 + 0.015), (x1 - 0.015, x1)):
            p.add(box(a, b, -0.09, 0.09, z0, z1), IRN, UV_BOX)
        p.add(box(x0, x1, -0.09, 0.09, z1, z1 + 0.015), IRN, UV_BOX)
    p.add(cyl(0.03, 0.2, 0.28, 0, 0, 8), WAX, UV_CYL)    # a cold wick in the cage
    return p


def trace_mirela():
    """A plain folded veil and a string of prayer beads."""
    p = Piece("SM_IX_Trace_Mirela")
    p.add(box(-0.22, 0.22, -0.16, 0.16, 0.0, 0.05, 0.02), CLOTH_PALE, UV_BOX)
    p.add(box(-0.2, 0.2, -0.14, 0.14, 0.05, 0.08, 0.015), CLOTH_PALE, UV_BOX)
    for i in range(22):
        a = 2 * math.pi * i / 22
        x, y = 0.3 + 0.1 * math.cos(a), -0.05 + 0.07 * math.sin(a)
        p.add(G.bm_box(0.022, 0.022, 0.022, x, y, 0.012, bevel=0.009), WOD, UV_BOX)
    return p


def trace_nix():
    """A broken kusarigama chain coiled round its sickle, beside a stone bowl of faintly lime-green water."""
    p = Piece("SM_IX_Trace_Nix")
    rng = random.Random(9)
    for i in range(18):
        a = i * 0.55
        r = 0.08 + i * 0.008
        x, y = -0.12 + r * math.cos(a), -0.02 + r * math.sin(a)
        link = G.bm_cylinder(0.022, -0.006, 0.006, 8)
        p.add(link, IRN, UV_BOX, matrix=mat_t(x, y, 0.015 + 0.004 * (i % 2)) @ mat_rz(math.degrees(a) + 90) @ mat_rx(90 * (i % 2)))
    blade = [(0.0, 0.0), (0.26, 0.02), (0.34, 0.09), (0.3, 0.12), (0.22, 0.05), (0.0, 0.03)]
    p.add(G.bm_profile_solid([blade], 0.01, bevel=0.002), IRN, UV_BOX, matrix=mat_t(-0.18, -0.1, 0.03))
    p.add(cyl(0.015, 0.025, 0.035, -0.3, -0.06, 6), WOD, UV_CYL)
    p.add(G.bm_lathe([(0.0, 0.0), (0.13, 0.0), (0.16, 0.06), (0.15, 0.1), (0.12, 0.1), (0.11, 0.03), (0.0, 0.03)], 14, cx=0.28, cy=0.0), DRS, UV_CYL)
    p.add(cyl(0.118, 0.07, 0.075, 0.28, 0.0, 14), LIME, UV_BOX)
    return p


def trace_bram():
    """Rolled hand wraps and a watchman's signal flare."""
    p = Piece("SM_IX_Trace_Bram")
    for (x, y) in ((-0.16, -0.03), (-0.02, 0.04)):
        roll = G.bm_cylinder(0.045, -0.06, 0.06, 10)
        p.add(roll, CLOTH_PALE, UV_CYL, matrix=mat_t(x, y, 0.045) @ mat_ry(90))
    p.add(box(-0.12, 0.08, -0.12, -0.08, 0.0, 0.006), CLOTH_PALE, UV_BOX)
    flare = G.bm_cylinder(0.025, 0.0, 0.26, 10)
    p.add(flare, FLARE, UV_CYL, matrix=mat_t(0.12, -0.02, 0.025) @ mat_rz(20) @ mat_ry(90))
    p.add(G.bm_cylinder(0.027, 0.0, 0.03, 10), IRN, UV_CYL, matrix=mat_t(0.12, -0.02, 0.025) @ mat_rz(20) @ mat_ry(90))
    return p


def mural():
    """The end wall's panel: blank weathered plaster in a dressed frame, for the creator's illustration."""
    p = Piece("SM_IX_Mural")
    x = 21.9
    p.add(box(x - 0.06, x, 5.9, 10.1, TR_FLOOR + 0.9, TR_FLOOR + 3.7), PLASTER, UV_BOX)
    for (y0, y1, z0, z1) in ((5.75, 5.9, 0.75, 3.85), (10.1, 10.25, 0.75, 3.85), (5.75, 10.25, 0.75, 0.9), (5.75, 10.25, 3.7, 3.85)):
        p.add(box(x - 0.14, x, y0, y1, TR_FLOOR + z0, TR_FLOOR + z1, 0.02), DRS, UV_BOX)
    return p


def board():
    """A devotional board on a pier: a dark frame and a blank panel for the creator's illustration. Faces -Y."""
    p = Piece("SM_IX_Board")
    p.add(box(-0.42, 0.42, -0.04, 0.0, 0.0, 1.3, 0.01), PLASTER, UV_BOX)
    for (x0, x1, z0, z1) in ((-0.48, -0.42, -0.06, 1.36), (0.42, 0.48, -0.06, 1.36), (-0.48, 0.48, -0.06, 0.0), (-0.48, 0.48, 1.3, 1.36)):
        p.add(box(x0, x1, -0.07, 0.0, z0, z1, 0.01), WOD, UV_WOOD)
    p.add(box(-0.5, 0.5, -0.1, 0.0, -0.12, -0.06, 0.01), WOD, UV_WOOD)   # a small ledge for offerings
    return p


# ------------------------------------------------------------------ the camp (south aisle, by the entrance)
def camp():
    p = Piece("SM_IX_Camp")
    rng = random.Random(44)
    for (cx, cy, yaw, mat) in ((10.6, -2.6, 8, CLOTH_DUN), (10.5, -0.4, -6, CLOTH_DUN), (9.3, 0.9, 80, CLOTH_BLACK)):
        bm = G.bm_box(0.78, 1.85, 0.07, 0, 0, 0.035, bevel=0.025)
        p.add(bm, mat, UV_BOX, matrix=mat_t(cx, cy, 0.0) @ mat_rz(yaw))
        pillow = G.bm_cylinder(0.11, -0.36, 0.36, 10)
        p.add(pillow, mat, UV_CYL, matrix=mat_t(cx, cy, 0.0) @ mat_rz(yaw) @ mat_t(0, 0.8, 0.12) @ mat_ry(90))
    # the brazier: an iron bowl on three legs, embers in it
    bx, by = 9.6, -1.4
    for i in range(3):
        a = 2 * math.pi * i / 3
        leg = G.bm_cylinder(0.02, 0.0, 0.5, 6)
        p.add(leg, IRN, UV_CYL, matrix=mat_t(bx + 0.24 * math.cos(a), by + 0.24 * math.sin(a), 0.0) @ mat_rz(math.degrees(a)) @ mat_ry(-12))
    p.add(G.bm_lathe([(0.0, 0.42), (0.3, 0.46), (0.36, 0.62), (0.33, 0.63), (0.27, 0.49), (0.0, 0.47)], 14, cx=bx, cy=by), IRN, UV_CYL)
    p.add(cyl(0.27, 0.5, 0.55, bx, by, 14), EMBER, UV_BOX)
    for _ in range(9):
        s = rng.uniform(0.05, 0.09)
        p.add(G.bm_box(s, s, s * 0.6, bx + rng.uniform(-0.18, 0.18), by + rng.uniform(-0.18, 0.18), 0.57, bevel=s * 0.3), IRN, UV_BOX)
    # crates, a sack and a pot
    for (cx, cy, cz, s) in ((11.2, 1.3, 0.0, 0.55), (11.25, 1.3, 0.55, 0.45), (11.3, 0.6, 0.0, 0.5)):
        p.add(G.bm_box(s, s, s, cx, cy, cz + s / 2, bevel=0.02), WOD, UV_WOOD)
    p.add(G.bm_lathe([(0.0, 0.0), (0.2, 0.02), (0.24, 0.2), (0.18, 0.42), (0.08, 0.5), (0.0, 0.5)], 10, cx=10.9, cy=1.95), CLOTH_DUN, UV_CYL)
    p.add(G.bm_lathe([(0.0, 0.0), (0.15, 0.0), (0.18, 0.12), (0.17, 0.2), (0.0, 0.2)], 12, cx=9.95, cy=-1.05), IRN, UV_CYL)
    return p


# ------------------------------------------------------------------ export
def export(piece, report):
    me = piece.finalize()
    ob = bpy.data.objects.new(piece.name, me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, piece.name + ".fbx"), **FBX)
    me.calc_loop_triangles()
    report[piece.name] = {"materials": [m.name for m in me.materials], "triangles": len(me.loop_triangles)}
    print(f"FX {piece.name} tris={len(me.loop_triangles)} mats={[m.name for m in me.materials]}")


bpy.ops.wm.read_factory_settings(use_empty=True)
report = {}
for build in (kneeler, saintess, forge_hearth, forge_work, forge_water, dwar, alcove, trace_wren, trace_ashka, trace_mirela,
              trace_nix, trace_bram, mural, board, camp):
    export(build(), report)
json.dump(report, open(os.path.join(OUT, "furnish.json"), "w"), indent=1)
print("FX DONE")
