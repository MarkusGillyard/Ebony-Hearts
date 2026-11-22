"""The Drowned Chapel's interior additions (stage 1: the core layout), built with the Chapel kit's own helpers and
materials so the new rooms read as the same building. Placeholders made with AI assistance; the creator authors the
final architecture.

Pieces (Blender metres, X across the nave, +Y toward the apse, Z up; Unreal = (x, -y, z) * 100):
  SM_IX_WestWall      the nave's west wall with the great arch and the loft opening (replaces the grey blockout)
  SM_IX_Narthex       the Threshold Hall: walls, floor with its seep channel, ceiling, beams, stair, loft room and vault
  SM_IX_LoftBalcony   the loft's balcony in the nave, its parapet and two columns
  SM_IX_ThresholdDoor the closed Threshold Door (two leaves bound in iron)
  SM_IX_TransArchBay  an aisle wall bay opened by a tall arch into a transept (instanced four times)
  SM_IX_Transept      a transept room: steps up from the aisle, floor, walls, vault and end window (south side;
                      the north one is the same piece mirrored)
  SM_IX_TransGlass    the transept's end-window glass
  SM_IX_DownDoorBay   the north aisle's east end wall with the doorway to the way down, and a window above it
  SM_IX_DownGlass     that window's glass
  SM_IX_DownStair     the way down: landing, 17 steps, side walls and the sloping ceiling
  SM_IX_Undercroft    the crypt (local floor at 0; placed 3 m down): walls, floor, the central arcade, two vaults,
                      the Hearted Dungeons gate opening and the sealed door's niche
  SM_IX_UnderGate     the gate (iron bars in a frame)
  SM_IX_SealedDoor    the sealed door: one smooth slab, no handle, no lock
  SM_IX_UnderWater    the crypt's water sheet (local 0.6 m)

Usage: blender -b --factory-startup -P chapel_interior.py -- <out dir>
Writes one FBX per piece and interior.json (material slots per piece, bounds).
"""
import json
import math
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chapel_config as C   # noqa: E402
import chapel_geo as G      # noqa: E402
import chapel_pieces as P   # noqa: E402
from chapel_geo import Piece, UV_BOX, UV_WOOD, TO_XZ, TO_YZ, mat_t, mat_rz, mat_s   # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)

ASH, DRS, FLR, WOD, IRN, GLN, WAT = P.ASH, P.DRS, P.FLR, P.WOD, P.IRN, P.GLN, P.WAT

FBX = dict(use_selection=True, object_types={"MESH"}, global_scale=1.0, apply_unit_scale=True,
           apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y", bake_space_transform=True,
           use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=False, use_triangles=True, colors_type="SRGB",
           prioritize_active_color=False, use_custom_props=False, add_leaf_bones=False, bake_anim=False,
           path_mode="STRIP", embed_textures=False, batch_mode="OFF")

# ------------------------------------------------------------------ layout constants (Blender metres)
WEST_FACE = -4.15          # the nave's west wall, room face
WEST_T = 1.2
NX_IN = 5.0                # Threshold Hall inner half width
NX_Y1 = WEST_FACE - WEST_T  # -5.35: the hall starts behind the west wall
NX_Y0 = NX_Y1 - 8.0         # -13.35: the hall's west (door) wall, inner face
NX_WALL = 0.9
CEIL_Z0, CEIL_Z1 = 4.6, 4.9  # the hall's ceiling slab = the loft's floor
LOFT_VAULT_SPRING, LOFT_VAULT_APEX = 7.2, 9.0
STAIR_X0, STAIR_X1 = -NX_IN, -3.6
STAIR_N = 27
STAIR_RISE = CEIL_Z1 / STAIR_N
STAIR_TREAD = 0.24
STAIR_Y_BOTTOM = NX_Y0 + 0.75
STAIR_Y_TOP = STAIR_Y_BOTTOM + STAIR_N * STAIR_TREAD
BALC_Y = -2.2
TR_FACE = 12.73            # outer face of the aisle wall
TR_Y0, TR_Y1 = 4.4, 11.6   # transept inner faces
TR_END = 21.9
TR_FLOOR = 0.45
TR_SPRING, TR_APEX = 6.2, 9.0
DOWN_X = -10.0
DOWN_WALL_OUT = 20.73      # outer face of the aisle's east end wall
DOWN_TOP_Z = -0.05
DOWN_N = 17
DOWN_RISE = (3.0 + DOWN_TOP_Z) / DOWN_N
DOWN_TREAD = 0.30
DOWN_Y_STEP0 = DOWN_WALL_OUT + 0.57
CRYPT_Y0, CRYPT_Y1 = 27.0, 35.0
CRYPT_X0, CRYPT_X1 = -13.0, -1.0
CRYPT_ARCADE_X = -7.0
CRYPT_DEPTH = 3.0
CRYPT_WATER = 0.6


def box(x0, x1, y0, y1, z0, z1, bevel=0.0):
    return G.bm_box(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, bevel=bevel)


def wall_x(loops, y_centre, t, bevel=0.03):
    """A wall in the X-Z plane (profile loops in x, z), thickness t along Y centred on y_centre."""
    return G.bm_profile_solid(loops, t, bevel=bevel), mat_t(0, y_centre, 0) @ TO_XZ


def wall_y(loops, x_centre, t, bevel=0.03):
    """A wall in the Y-Z plane (profile loops in y, z), thickness t along X centred on x_centre."""
    return G.bm_profile_solid(loops, t, bevel=bevel), mat_t(x_centre, 0, 0) @ TO_YZ


def add_wall(p, mat, spec):
    bm, m = spec
    p.add(bm, mat, UV_BOX, matrix=m)


def door_hole(a, bottom, spring, rho, n=14):
    return [(-a, bottom), (a, bottom)] + G.pointed_arch_pts(a, spring, rho, n)


def shift(loop, dx=0.0, dz=0.0):
    return [(x + dx, z + dz) for (x, z) in loop]


def vault_profile(a, spring, h, thick, e=0.5, n=20):
    """Closed profile (x, z) of a gently pointed barrel vault: intrados over half span a, rise h, then the extrados."""
    inner = [(-a + 2 * a * i / n, spring + G.segmental_pointed(-a + 2 * a * i / n, a, h, e)) for i in range(n + 1)]
    outer = [(x * (a + thick) / a, z + thick) for (x, z) in reversed(inner)]
    return inner + [(a + thick, spring)] + outer[1:-1] + [(-(a + thick), spring)]


# ------------------------------------------------------------------ pieces
def west_wall():
    p = Piece("SM_IX_WestWall")
    out = [(-12.9, -0.3), (12.9, -0.3), (12.9, 11.6), (8.6, 11.6), (8.6, 17.2), (-8.6, 17.2), (-8.6, 11.6), (-12.9, 11.6)]
    great = door_hole(2.0, -0.3, 2.3, 2.1)
    upper = door_hole(3.5, CEIL_Z0, 7.0, 4.0)
    yc = WEST_FACE - WEST_T / 2
    add_wall(p, ASH, wall_x([out, great, upper], yc, WEST_T))
    # dressed arch bands on both faces of the great arch, and on the nave face of the loft opening
    for face in (WEST_FACE + 0.04, NX_Y1 - 0.04):
        add_wall(p, DRS, wall_x([G.arch_band(2.0 - 0.02, 0.32, 2.3, 2.1 - 0.02, 14, foot=2.6)], face, 0.18))
    add_wall(p, DRS, wall_x([G.arch_band(3.5 - 0.02, 0.4, 7.0, 4.0 - 0.02, 16, foot=7.0 - CEIL_Z0)], WEST_FACE + 0.05, 0.2))
    # a string course at the loft's floor line, across the nave face
    p.add(box(-8.4, -3.9, WEST_FACE - 0.05, WEST_FACE + 0.22, CEIL_Z0 - 0.25, CEIL_Z0, 0.03), DRS, UV_BOX)
    p.add(box(3.9, 8.4, WEST_FACE - 0.05, WEST_FACE + 0.22, CEIL_Z0 - 0.25, CEIL_Z0, 0.03), DRS, UV_BOX)
    return p


def narthex():
    p = Piece("SM_IX_Narthex")
    top = LOFT_VAULT_APEX + 0.6
    # side walls and the door wall (the hall and the loft room above it share them)
    for xc in (-NX_IN - NX_WALL / 2, NX_IN + NX_WALL / 2):
        add_wall(p, ASH, wall_y([[(NX_Y0 - NX_WALL, -0.3), (NX_Y1, -0.3), (NX_Y1, top), (NX_Y0 - NX_WALL, top)]], xc, NX_WALL))
    door = door_hole(1.6, -0.3, 2.8, 1.7)
    win = G.lancet_outline(0.6, 5.8, 7.6, 2.4, 12)
    yc = NX_Y0 - NX_WALL / 2
    add_wall(p, ASH, wall_x([[(-NX_IN, -0.3), (NX_IN, -0.3), (NX_IN, top), (-NX_IN, top)], door, win], yc, NX_WALL))
    add_wall(p, DRS, wall_x([G.arch_band(1.6 - 0.02, 0.3, 2.8, 1.7 - 0.02, 14, foot=3.1)], NX_Y0 + 0.04, 0.16))
    add_wall(p, DRS, wall_x([G.arch_band(0.6 - 0.02, 0.14, 7.6, 0.6 * 2.4 - 0.02, 12, foot=1.8)], NX_Y0 + 0.03, 0.14))
    # floor: flags with a shallow channel down the middle that carries the seep from the door toward the nave
    ch = 0.18
    fy1 = -6.0   # the nave's floor strip already reaches under the west wall to here
    p.add(box(-NX_IN, -ch, NX_Y0, fy1, -0.3, 0.0), FLR, UV_BOX)
    p.add(box(ch, NX_IN, NX_Y0, fy1, -0.3, 0.0), FLR, UV_BOX)
    p.add(box(-ch, ch, NX_Y0, fy1, -0.3, -0.06), DRS, UV_BOX)
    p.add(box(-1.6, 1.6, NX_Y0 - NX_WALL, NX_Y0, -0.3, 0.06, 0.02), DRS, UV_BOX)      # threshold stone
    # ceiling slab (the loft's floor) with the stair's opening
    # the opening starts where a standing player's head (1.8 m, plus the capsule's reach) would meet the slab
    hole_y0 = STAIR_Y_BOTTOM + STAIR_TREAD * math.ceil((CEIL_Z0 - 2.2) / STAIR_RISE) - 0.7
    p.add(box(-NX_IN, NX_IN, NX_Y0, hole_y0, CEIL_Z0, CEIL_Z1), DRS, UV_BOX)
    p.add(box(STAIR_X1, NX_IN, hole_y0, STAIR_Y_TOP, CEIL_Z0, CEIL_Z1), DRS, UV_BOX)
    p.add(box(-NX_IN, NX_IN, STAIR_Y_TOP, NX_Y1, CEIL_Z0, CEIL_Z1), DRS, UV_BOX)
    # timber beams under the ceiling
    for y in (NX_Y0 + 1.1, NX_Y0 + 2.7, NX_Y0 + 4.3, NX_Y0 + 5.9, NX_Y0 + 7.4):
        x0 = STAIR_X1 if hole_y0 - 0.2 < y < STAIR_Y_TOP + 0.2 else -NX_IN
        p.add(box(x0, NX_IN, y - 0.15, y + 0.15, CEIL_Z0 - 0.34, CEIL_Z0), WOD, UV_WOOD)
    # the stair: solid stone steps rising toward the nave along the north wall, a parapet on its open side
    for i in range(STAIR_N):
        y0 = STAIR_Y_BOTTOM + i * STAIR_TREAD
        p.add(box(STAIR_X0, STAIR_X1, y0, STAIR_Y_TOP if i == STAIR_N - 1 else y0 + STAIR_TREAD + 0.02, -0.3,
                  (i + 1) * STAIR_RISE, 0.01), DRS, UV_BOX)
    para = [(STAIR_Y_BOTTOM, -0.3), (STAIR_Y_TOP, CEIL_Z1 - 0.02), (STAIR_Y_TOP, CEIL_Z1 + 0.95),
            (STAIR_Y_BOTTOM, 0.95), (STAIR_Y_BOTTOM - 0.25, 0.95), (STAIR_Y_BOTTOM - 0.25, -0.3)]
    add_wall(p, DRS, wall_y([para], STAIR_X1 + 0.11, 0.22, bevel=0.02))
    # a parapet along the opening's west edge, on the loft
    p.add(box(STAIR_X0, STAIR_X1 + 0.22, hole_y0 - 0.22, hole_y0, CEIL_Z1, CEIL_Z1 + 0.95, 0.02), DRS, UV_BOX)
    # the loft room's vault (a gently pointed barrel along Y)
    prof = vault_profile(NX_IN, LOFT_VAULT_SPRING, LOFT_VAULT_APEX - LOFT_VAULT_SPRING, 0.45, e=0.6)
    L = NX_Y1 - NX_Y0
    p.add(G.bm_profile_solid([prof], L, bevel=0.0), ASH, UV_BOX, matrix=mat_t(0, (NX_Y0 + NX_Y1) / 2, 0) @ TO_XZ)
    # a cornice where the vault springs
    for (x0, x1) in ((-NX_IN, -NX_IN + 0.25), (NX_IN - 0.25, NX_IN)):
        p.add(box(x0, x1, NX_Y0, NX_Y1, LOFT_VAULT_SPRING - 0.25, LOFT_VAULT_SPRING, 0.03), DRS, UV_BOX)
    return p


def loft_balcony():
    p = Piece("SM_IX_LoftBalcony")
    hx = 3.8
    p.add(box(-hx, hx, WEST_FACE - WEST_T, BALC_Y, CEIL_Z0, CEIL_Z1, 0.02), DRS, UV_BOX)
    # parapet: front and returns, with a coping
    p.add(box(-hx, hx, BALC_Y - 0.25, BALC_Y, CEIL_Z1, CEIL_Z1 + 0.9, 0.02), DRS, UV_BOX)
    for xs in (-1, 1):
        x0, x1 = (xs * hx - 0.25, xs * hx) if xs > 0 else (xs * hx, xs * hx + 0.25)
        p.add(box(x0, x1, WEST_FACE, BALC_Y, CEIL_Z1, CEIL_Z1 + 0.9, 0.02), DRS, UV_BOX)
    p.add(box(-hx - 0.06, hx + 0.06, BALC_Y - 0.31, BALC_Y + 0.06, CEIL_Z1 + 0.9, CEIL_Z1 + 1.0, 0.02), DRS, UV_BOX)
    # a moulded edge under the slab
    p.add(box(-hx - 0.08, hx + 0.08, BALC_Y - 0.08, BALC_Y + 0.08, CEIL_Z0 - 0.2, CEIL_Z0 + 0.02, 0.03), DRS, UV_BOX)
    # two columns carrying the front
    for xs in (-1, 1):
        cx, cy = xs * (hx - 0.4), BALC_Y + 0.35
        p.add(G.bm_cylinder(0.2, 0.0, CEIL_Z0 - 0.35, 10, cx, cy), DRS, P.UV_CYL)
        p.add(box(cx - 0.32, cx + 0.32, cy - 0.32, cy + 0.32, 0.0, 0.3, 0.03), DRS, UV_BOX)
        p.add(box(cx - 0.34, cx + 0.34, cy - 0.34, cy + 0.34, CEIL_Z0 - 0.35, CEIL_Z0 - 0.2, 0.03), DRS, UV_BOX)
    return p


def threshold_door():
    p = Piece("SM_IX_ThresholdDoor")
    yc = NX_Y0 - NX_WALL * 0.6
    shape = door_hole(1.6, 0.06, 2.8, 1.7)
    # two leaves with a narrow seam between them; light comes through it
    for side in (-1, 1):
        leaf = [(x, z) for (x, z) in shape]
        clip = []
        for (x, z) in leaf:
            clip.append((max(x, 0.012) if side > 0 else min(x, -0.012), z))
        bm = G.bm_profile_solid([clip], 0.14, bevel=0.01)
        p.add(bm, WOD, UV_WOOD, matrix=mat_t(0, yc, 0) @ TO_XZ)
    # iron straps and a ring
    for z in (0.7, 1.8, 2.9):
        for side in (-1, 1):
            x0, x1 = (0.05, 1.45) if side > 0 else (-1.45, -0.05)
            p.add(box(x0, x1, yc + 0.07, yc + 0.11, z - 0.06, z + 0.06, 0.01), IRN, UV_BOX)
    p.add(G.bm_cylinder(0.09, 0.0, 0.03, 10), IRN, UV_BOX, matrix=mat_t(0.22, yc + 0.11, 1.45) @ G.mat_rx(-90))
    return p


def aisle_bay_outline():
    out = [(-2.0, -0.45), (2.0, -0.45)]
    for i in range(25):
        x = 2.0 - 4.0 * i / 24
        out.append((x, P.aisle_top(x)))
    return out


def trans_arch_bay():
    """Built like SM_AisleWallBay (local -Y is the room side, pivot on the floor at the wall's centre)."""
    p = Piece("SM_IX_TransArchBay")
    t = C.OUTER_WALL_T
    hole = door_hole(1.5, -0.45, 3.8, 3.0)
    add_wall(p, ASH, wall_x([aisle_bay_outline(), hole], t / 2, t))
    add_wall(p, DRS, wall_x([G.arch_band(1.5 - 0.02, 0.28, 3.8, 3.0 - 0.02, 16, foot=4.25)], 0.02, 0.18))
    bmesh.ops.translate(p.bm, vec=(0, -t / 2, 0), verts=p.bm.verts)
    return p


def down_door_bay():
    p = Piece("SM_IX_DownDoorBay")
    t = C.OUTER_WALL_T
    hole = door_hole(0.9, -0.45, 2.2, 1.0)
    W = DOWN_WIN
    win = G.lancet_outline(W["half_w"], W["sill"], W["spring"], W["rho_k"], 12)
    add_wall(p, ASH, wall_x([aisle_bay_outline(), hole, win], t / 2, t))
    add_wall(p, DRS, wall_x([G.arch_band(W["half_w"] - 0.02, 0.13, W["spring"], W["half_w"] * W["rho_k"] - 0.02, 12,
                                         foot=W["spring"] - W["sill"])], 0.02, 0.14))
    add_wall(p, DRS, wall_x([G.arch_band(0.9 - 0.02, 0.24, 2.2, 1.0 - 0.02, 12, foot=2.65)], 0.02, 0.16))
    p.add(box(-1.8, 1.8, -0.4, 0.0, -0.45, 0.0), DRS, UV_BOX)   # stone bench stub, kept low by the door
    bmesh.ops.translate(p.bm, vec=(0, -t / 2, 0), verts=p.bm.verts)
    return p


def transept():
    """The south transept (+X); the north one is this piece mirrored in X."""
    p = Piece("SM_IX_Transept")
    w = 0.9
    top = TR_APEX + 0.7
    for (y0, y1) in ((TR_Y0 - w, TR_Y0), (TR_Y1, TR_Y1 + w)):
        p.add(box(TR_FACE, TR_END + w, y0, y1, -0.4, top, 0.03), ASH, UV_BOX)
    win = G.lancet_outline(0.55, 4.6, 6.6, 2.4, 12)
    win_y = [((TR_Y0 + TR_Y1) / 2 + x, z) for (x, z) in win]
    add_wall(p, ASH, wall_y([[(TR_Y0, -0.4), (TR_Y1, -0.4), (TR_Y1, top), (TR_Y0, top)], win_y], TR_END + w / 2, w))
    add_wall(p, DRS, wall_y([[((TR_Y0 + TR_Y1) / 2 + x, z) for (x, z) in
                              G.arch_band(0.55 - 0.02, 0.14, 6.6, 0.55 * 2.4 - 0.02, 12, foot=2.0)]], TR_END - 0.03, 0.12))
    # floor and the three steps up from the aisle
    p.add(box(TR_FACE, TR_FACE + 0.3, TR_Y0, TR_Y1, -0.4, 0.05), DRS, UV_BOX)
    p.add(box(TR_FACE + 0.3, TR_FACE + 0.6, TR_Y0, TR_Y1, -0.4, 0.25), DRS, UV_BOX)
    p.add(box(TR_FACE + 0.6, TR_END, TR_Y0, TR_Y1, -0.4, TR_FLOOR), FLR, UV_BOX)
    # a low dressed plinth along the walls
    for (y0, y1) in ((TR_Y0, TR_Y0 + 0.3), (TR_Y1 - 0.3, TR_Y1)):
        p.add(box(TR_FACE + 0.6, TR_END, y0, y1, TR_FLOOR, TR_FLOOR + 0.35, 0.03), DRS, UV_BOX)
    # the vault, along X
    prof = vault_profile((TR_Y1 - TR_Y0) / 2, TR_SPRING, TR_APEX - TR_SPRING, 0.45, e=0.5)
    prof_y = [((TR_Y0 + TR_Y1) / 2 + x, z) for (x, z) in prof]
    L = TR_END - TR_FACE + 0.3
    p.add(G.bm_profile_solid([prof_y], L), ASH, UV_BOX, matrix=mat_t(TR_FACE - 0.3 + L / 2, 0, 0) @ TO_YZ)
    for y0, y1 in ((TR_Y0, TR_Y0 + 0.25), (TR_Y1 - 0.25, TR_Y1)):
        p.add(box(TR_FACE, TR_END, y0, y1, TR_SPRING - 0.25, TR_SPRING, 0.03), DRS, UV_BOX)
    # transverse ribs across the vault
    for x in (TR_FACE + 3.2, TR_FACE + 6.2):
        rib = [((TR_Y0 + TR_Y1) / 2 + u, z) for (u, z) in vault_profile((TR_Y1 - TR_Y0) / 2 - 0.02, TR_SPRING,
                                                                       TR_APEX - TR_SPRING - 0.18, 0.22, e=0.5)]
        p.add(G.bm_profile_solid([rib], 0.3, bevel=0.03), DRS, UV_BOX, matrix=mat_t(x, 0, 0) @ TO_YZ)
    return p


def trans_glass():
    p = Piece("SM_IX_TransGlass", grounded=False)
    win = G.lancet_outline(0.55, 4.6, 6.6, 2.4, 12)
    win_y = [((TR_Y0 + TR_Y1) / 2 + x, z) for (x, z) in win]
    bm = G.bm_flat([win_y])
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    p.add(bm, GLN, UV_BOX, matrix=mat_t(TR_END + 0.45, 0, 0) @ TO_YZ)
    return p


DOWN_WIN = dict(half_w=0.5, sill=4.0, spring=6.6, rho_k=2.4)


def down_glass():
    """The way down's end wall keeps a window, set higher than the aisle's so the doorway fits under it."""
    p = Piece("SM_IX_DownGlass", grounded=False)
    W = DOWN_WIN
    bm = G.bm_flat([G.lancet_outline(W["half_w"], W["sill"], W["spring"], W["rho_k"], 12)])
    p.add(bm, GLN, UV_BOX, matrix=mat_t(0, 0.0, 0) @ TO_XZ)
    return p


def down_stair():
    p = Piece("SM_IX_DownStair", grounded=False)
    x0, x1 = DOWN_X - 0.9, DOWN_X + 0.9
    p.add(box(x0, x1, DOWN_WALL_OUT - 0.02, DOWN_Y_STEP0, -3.5, DOWN_TOP_Z), DRS, UV_BOX)
    for i in range(1, DOWN_N + 1):
        y0 = DOWN_Y_STEP0 + (i - 1) * DOWN_TREAD
        y1 = y0 + DOWN_TREAD + (0.6 if i == DOWN_N else 0.0)
        p.add(box(x0, x1, y0, y1, -3.5, DOWN_TOP_Z - i * DOWN_RISE, 0.01), DRS, UV_BOX)
    y_end = DOWN_Y_STEP0 + DOWN_N * DOWN_TREAD + 0.6
    for xc in (x0 - 0.45, x1 + 0.45):
        add_wall(p, ASH, wall_y([[(DOWN_WALL_OUT, -3.5), (y_end, -3.5), (y_end, 0.9), (DOWN_Y_STEP0 + 2.0, 3.8),
                                  (DOWN_WALL_OUT, 3.8)]], xc, 0.9))
    hi = DOWN_TOP_Z + 3.3
    lo_y = DOWN_Y_STEP0 + DOWN_N * DOWN_TREAD
    lo = DOWN_TOP_Z - 3.0 + 0.1 + 2.95
    ceil = [(DOWN_WALL_OUT, hi), (DOWN_Y_STEP0 + 0.3, hi), (lo_y, lo), (y_end, lo), (y_end, lo + 0.45),
            (lo_y, lo + 0.45), (DOWN_Y_STEP0 + 0.3, hi + 0.45), (DOWN_WALL_OUT, hi + 0.45)]
    add_wall(p, ASH, wall_y([ceil], DOWN_X, 3.6, bevel=0.0))
    return p


def undercroft():
    """Local coordinates: the crypt floor at z = 0 (placed CRYPT_DEPTH below the Chapel's floor)."""
    p = Piece("SM_IX_Undercroft")
    w = 0.9
    top = 4.6
    xm = (CRYPT_X0 + CRYPT_X1) / 2
    # west wall with the way in from the stair
    entry = [(DOWN_X - 0.9, -0.4), (DOWN_X + 0.9, -0.4), (DOWN_X + 0.9, 2.95), (DOWN_X - 0.9, 2.95)]
    add_wall(p, ASH, wall_x([[(CRYPT_X0 - w, -0.4), (CRYPT_X1 + w, -0.4), (CRYPT_X1 + w, top), (CRYPT_X0 - w, top)], entry],
                            CRYPT_Y0 - w / 2, w))
    # east wall with the gate's opening (centred on the east aisle)
    gx = (CRYPT_ARCADE_X + CRYPT_X1) / 2
    gate = shift(door_hole(1.4, -0.4, 2.0, 1.6), dx=gx)
    add_wall(p, ASH, wall_x([[(CRYPT_X0 - w, -0.4), (CRYPT_X1 + w, -0.4), (CRYPT_X1 + w, top), (CRYPT_X0 - w, top)], gate],
                            CRYPT_Y1 + w / 2, w))
    add_wall(p, DRS, wall_x([shift(G.arch_band(1.4 - 0.02, 0.3, 2.0, 1.6 - 0.02, 14, foot=2.4), dx=gx)], CRYPT_Y1 - 0.04, 0.16))
    # north (sealed door niche) and south walls
    yc = (CRYPT_Y0 + CRYPT_Y1) / 2
    niche = [((yc + u), z) for (u, z) in door_hole(0.85, -0.4, 2.0, 0.95)]
    p.add(box(CRYPT_X0 - w - 0.6, CRYPT_X0 - w, CRYPT_Y0 - w, CRYPT_Y1 + w, -0.4, top), ASH, UV_BOX)   # backing behind the niche
    add_wall(p, ASH, wall_y([[(CRYPT_Y0, -0.4), (CRYPT_Y1, -0.4), (CRYPT_Y1, top), (CRYPT_Y0, top)], niche], CRYPT_X0 - w / 2, w))
    add_wall(p, DRS, wall_y([[((yc + u), z) for (u, z) in G.arch_band(0.85 - 0.02, 0.22, 2.0, 0.95 - 0.02, 12, foot=2.4)]],
                            CRYPT_X0 + 0.04, 0.14))
    add_wall(p, ASH, wall_y([[(CRYPT_Y0, -0.4), (CRYPT_Y1, -0.4), (CRYPT_Y1, top), (CRYPT_Y0, top)]], CRYPT_X1 + w / 2, w))
    # floor
    p.add(box(CRYPT_X0, CRYPT_X1, CRYPT_Y0, CRYPT_Y1, -0.4, 0.0), FLR, UV_BOX)
    # the central arcade along Y: two squat piers, three arches
    arc_t = 0.8
    holes = []
    for (y0, y1) in ((CRYPT_Y0, 29.3), (30.1, 31.9), (32.7, CRYPT_Y1)):
        a = (y1 - y0) / 2
        holes.append([(u + (y0 + y1) / 2, z) for (u, z) in door_hole(a, -0.4, 1.6, a * 1.15)])
    add_wall(p, DRS, wall_y([[(CRYPT_Y0, -0.4), (CRYPT_Y1, -0.4), (CRYPT_Y1, 3.9), (CRYPT_Y0, 3.9)]] + holes, CRYPT_ARCADE_X, arc_t))
    # two vaults along Y over the two aisles
    for (xa, xb) in ((CRYPT_X0, CRYPT_ARCADE_X - arc_t / 2), (CRYPT_ARCADE_X + arc_t / 2, CRYPT_X1)):
        a = (xb - xa) / 2
        prof = [(x + (xa + xb) / 2, z) for (x, z) in vault_profile(a, 1.9, 1.6, 0.4, e=0.4)]
        p.add(G.bm_profile_solid([prof], CRYPT_Y1 - CRYPT_Y0), ASH, UV_BOX, matrix=mat_t(0, yc, 0) @ TO_XZ)
        for y in (29.7, 32.3):
            rib = [(x + (xa + xb) / 2, z) for (x, z) in vault_profile(a - 0.02, 1.9, 1.45, 0.2, e=0.4)]
            p.add(G.bm_profile_solid([rib], 0.28, bevel=0.03), DRS, UV_BOX, matrix=mat_t(0, y, 0) @ TO_XZ)
    # a ledge round the walls just above the water
    for (x0, x1, y0, y1) in ((CRYPT_X0, CRYPT_X1, CRYPT_Y1 - 0.35, CRYPT_Y1), (CRYPT_X1 - 0.35, CRYPT_X1, CRYPT_Y0, CRYPT_Y1)):
        p.add(box(x0, x1, y0, y1, 0.0, CRYPT_WATER + 0.12, 0.03), DRS, UV_BOX)
    return p


def under_gate():
    p = Piece("SM_IX_UnderGate", grounded=False)
    gx = (CRYPT_ARCADE_X + CRYPT_X1) / 2
    y = CRYPT_Y1 + 0.25
    for i in range(-6, 7):
        x = gx + i * 0.2
        h = 2.0 + G.pointed_height(min(abs(x - gx), 1.38), 1.4, 1.5) if abs(x - gx) < 1.38 else 2.0
        p.add(box(x - 0.035, x + 0.035, y - 0.035, y + 0.035, -0.2, h - 0.05), IRN, UV_BOX)
    for z in (0.35, 1.25, 2.0):
        p.add(box(gx - 1.38, gx + 1.38, y - 0.05, y + 0.05, z - 0.06, z + 0.06), IRN, UV_BOX)
    p.add(box(gx - 0.32, gx + 0.32, y - 0.09, y - 0.05, 0.95, 1.55, 0.02), IRN, UV_BOX)   # the lock plate
    return p


def sealed_door():
    p = Piece("SM_IX_SealedDoor")
    yc = (CRYPT_Y0 + CRYPT_Y1) / 2
    slab = [((yc + u), z) for (u, z) in door_hole(0.84, 0.0, 2.0, 0.94)]
    add_wall(p, DRS, wall_y([slab], CRYPT_X0 - 0.55, 0.3, bevel=0.01))
    return p


def under_water():
    p = Piece("SM_IX_UnderWater", grounded=False)
    p.add(G.bm_grid(12, 8, lambda x, y: CRYPT_WATER, CRYPT_X0, CRYPT_X1, CRYPT_Y0 - 0.2, CRYPT_Y1), WAT, UV_BOX)
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
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    me.calc_loop_triangles()
    report[piece.name] = {"materials": [m.name for m in me.materials], "triangles": len(me.loop_triangles),
                          "bounds_m": [[round(min(xs), 2), round(min(ys), 2), round(min(zs), 2)],
                                       [round(max(xs), 2), round(max(ys), 2), round(max(zs), 2)]]}
    print(f"IX {piece.name} tris={len(me.loop_triangles)} mats={[m.name for m in me.materials]}")


bpy.ops.wm.read_factory_settings(use_empty=True)
report = {}
for build in (west_wall, narthex, loft_balcony, threshold_door, trans_arch_bay, transept, trans_glass, down_door_bay, down_glass,
              down_stair, undercroft, under_gate, sealed_door, under_water):
    export(build(), report)
report["_layout"] = {"stair_top_y": STAIR_Y_TOP, "stair_bottom_y": STAIR_Y_BOTTOM, "down_end_y": DOWN_Y_STEP0 + DOWN_N * DOWN_TREAD,
                     "crypt_depth": CRYPT_DEPTH, "crypt_water": CRYPT_WATER}
json.dump(report, open(os.path.join(OUT, "interior.json"), "w"), indent=1)
print("IX DONE")
