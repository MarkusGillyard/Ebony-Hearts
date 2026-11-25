"""Horse-sized Chapel Wolf (canon: Markus's "Chapel Wolves" doc, 2026-11-23):
- Enormous, muscular body (~1.50 m at the shoulder, ~2.85 m nose to tail), quiet and graceful;
- Dense charcoal, silver and ash coat, with black and blue-grey along the spine;
- Heavy pale-silver ceremonial mane (separate part so hackles/mane rise in hostility);
- Pale amber eyes (separate material slot), battle scars, torn right ear, wet dark paws, long thick plumed tail.

All geometry is sculpted in Blender and all textures are hand-coded painterly brush-stroke canvases (no generative AI).
Each part's origin is its joint so EHWolf.cpp poses and animates it cleanly.

Usage: blender -b --factory-startup -P make_wolf.py -- <out dir>
Writes:
  SM_PH_Wolf_Body.fbx, SM_PH_Wolf_Mane.fbx, SM_PH_Wolf_Head.fbx, SM_PH_Wolf_Leg.fbx, SM_PH_Wolf_Tail.fbx
  T_Wolf_Coat_BC.png, T_Wolf_Coat_R.png, T_Wolf_Coat_N.png
  T_Wolf_Mane_BC.png, T_Wolf_Mane_R.png, T_Wolf_Mane_N.png
  T_Wolf_Leg_BC.png,  T_Wolf_Leg_R.png
"""
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

FBX_SETTINGS = dict(
    use_selection=True, object_types={"MESH"}, global_scale=1.0, apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y", bake_space_transform=True,
    use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=False, use_triangles=True, colors_type="SRGB",
    prioritize_active_color=False, use_custom_props=False, add_leaf_bones=False, bake_anim=False, path_mode="STRIP",
    embed_textures=False, batch_mode="OFF")


def save_png(path, arr, srgb=True):
    """Writes an HxWx4 float32 [0..1] array to PNG via Blender's image writer."""
    h, w, _ = arr.shape
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    # Blender image pixels are bottom-up RGBA flat float list.
    flipped = np.flipud(np.clip(arr, 0.0, 1.0)).astype(np.float32)
    img.pixels.foreach_set(flipped.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def height_to_normal(height, strength=3.0):
    """Converts a 2D heightfield [0..1] into a tangent-space normal map RGBA [0..1]."""
    gx = np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)
    gy = np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)
    nx = -gx * strength
    ny = -gy * strength
    nz = np.ones_like(height)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    out = np.empty((height.shape[0], height.shape[1], 4), dtype=np.float32)
    out[..., 0] = nx * inv * 0.5 + 0.5
    out[..., 1] = ny * inv * 0.5 + 0.5
    out[..., 2] = nz * inv * 0.5 + 0.5
    out[..., 3] = 1.0
    return out


def paint_strokes(rgb, rough, height, rng, count, u_range, v_range, length_px, width_px, color_lo, color_hi,
                  rough_val, h_delta, angle_rad=0.0, angle_jitter=0.18, alpha=0.45):
    """Paints layered directional painterly fur brush strokes onto the canvas."""
    h, w, _ = rgb.shape
    for _ in range(count):
        cx = rng.uniform(u_range[0], u_range[1]) * w
        cy = rng.uniform(v_range[0], v_range[1]) * h
        L = rng.uniform(length_px[0], length_px[1])
        W = rng.uniform(width_px[0], width_px[1])
        ang = angle_rad + rng.uniform(-angle_jitter, angle_jitter)
        ca, sa = math.cos(ang), math.sin(ang)
        t_col = rng.random()
        col = np.array([color_lo[k] + (color_hi[k] - color_lo[k]) * t_col for k in range(3)], dtype=np.float32)
        # Bounding box in pixel coords
        rx = abs(ca) * L * 0.6 + abs(sa) * W * 0.6 + 2.0
        ry = abs(sa) * L * 0.6 + abs(ca) * W * 0.6 + 2.0
        x0 = max(0, int(cx - rx)); x1 = min(w, int(cx + rx) + 1)
        y0 = max(0, int(cy - ry)); y1 = min(h, int(cy + ry) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        xs = np.arange(x0, x1, dtype=np.float32) - cx
        ys = np.arange(y0, y1, dtype=np.float32) - cy
        dx = xs[None, :] * ca + ys[:, None] * sa
        dy = -xs[None, :] * sa + ys[:, None] * ca
        # Tapered painterly bristle mask
        d2 = (dx / (L * 0.5 + 1e-4)) ** 2 + (dy / (W * 0.5 + 1e-4)) ** 2
        m = np.clip(1.0 - d2, 0.0, 1.0)
        if not np.any(m > 0.01):
            continue
        m = (m * m) * alpha
        sub = rgb[y0:y1, x0:x1]
        rgb[y0:y1, x0:x1] = sub * (1.0 - m[..., None]) + col[None, None, :] * m[..., None]
        rough[y0:y1, x0:x1] = rough[y0:y1, x0:x1] * (1.0 - m * 0.6) + rough_val * (m * 0.6)
        height[y0:y1, x0:x1] = np.clip(height[y0:y1, x0:x1] + h_delta * m, 0.0, 1.0)


def generate_textures():
    """Generates painterly coat, mane and wet-paw leg textures (1024x1024)."""
    S = 1024
    rng = random.Random(20261124)

    # 1) COAT (Body, Head, Tail): U = back-to-front (0..1), V = girth (0 & 1 = belly/chin, 0.5 = spine/crown)
    ys = np.linspace(0.0, 1.0, S, dtype=np.float32)[:, None]
    xs = np.linspace(0.0, 1.0, S, dtype=np.float32)[None, :]
    spine = np.exp(-((ys - 0.5) / 0.16) ** 2)        # dark charcoal/blue-grey dorsal ridge
    flank = np.exp(-((np.abs(ys - 0.5) - 0.24) / 0.14) ** 2)  # silver-ash mid flank
    belly = np.clip(1.0 - np.exp(-((ys - 0.5) / 0.36) ** 2), 0.0, 1.0)

    rgb = np.zeros((S, S, 3), dtype=np.float32)
    # Base painterly underpainting: charcoal-ash flanks, deep blue-black spine, pale ash belly
    base_mid = np.array([0.22, 0.23, 0.25], dtype=np.float32)
    base_spine = np.array([0.055, 0.062, 0.082], dtype=np.float32)
    base_flank = np.array([0.36, 0.37, 0.39], dtype=np.float32)
    base_belly = np.array([0.48, 0.46, 0.43], dtype=np.float32)
    rgb[:] = base_mid
    rgb = rgb * (1.0 - flank[..., None] * 0.55) + base_flank * (flank[..., None] * 0.55)
    rgb = rgb * (1.0 - belly[..., None] * 0.72) + base_belly * (belly[..., None] * 0.72)
    rgb = rgb * (1.0 - spine[..., None] * 0.85) + base_spine * (spine[..., None] * 0.85)

    rough = np.full((S, S), 0.86, dtype=np.float32)
    height = np.full((S, S), 0.5, dtype=np.float32)

    # Broad painterly charcoal & ash fur blocks along U (back-to-front grain)
    paint_strokes(rgb, rough, height, rng, 1800, (0, 1), (0.0, 1.0), (36, 90), (8, 20),
                  (0.14, 0.15, 0.17), (0.34, 0.35, 0.37), 0.86, 0.14, angle_rad=0.0, angle_jitter=0.14, alpha=0.32)
    # Deep black & blue-grey spine streaks
    paint_strokes(rgb, rough, height, rng, 1100, (0, 1), (0.36, 0.64), (40, 100), (6, 16),
                  (0.03, 0.035, 0.05), (0.11, 0.13, 0.18), 0.82, 0.18, angle_rad=0.0, angle_jitter=0.10, alpha=0.45)
    # Silver & ash highlights along flanks and shoulders
    paint_strokes(rgb, rough, height, rng, 1200, (0.15, 0.95), (0.16, 0.84), (24, 65), (4, 11),
                  (0.42, 0.44, 0.47), (0.68, 0.70, 0.73), 0.80, 0.22, angle_rad=0.0, angle_jitter=0.16, alpha=0.34)
    # Fine fur bristles
    paint_strokes(rgb, rough, height, rng, 2400, (0, 1), (0.0, 1.0), (14, 34), (2.2, 5.0),
                  (0.08, 0.09, 0.11), (0.56, 0.58, 0.60), 0.84, 0.16, angle_rad=0.0, angle_jitter=0.12, alpha=0.28)
    # Battle scars across shoulder & muzzle (pale weathered pinkish-ash slashes)
    paint_strokes(rgb, rough, height, rng, 16, (0.55, 0.88), (0.28, 0.72), (38, 95), (3.0, 6.5),
                  (0.56, 0.46, 0.44), (0.72, 0.64, 0.60), 0.52, -0.35, angle_rad=0.55, angle_jitter=0.25, alpha=0.68)

    bc = np.concatenate([rgb, np.ones((S, S, 1), dtype=np.float32)], axis=-1)
    r_img = np.stack([rough, rough, rough, np.ones_like(rough)], axis=-1)
    n_img = height_to_normal(height, strength=3.4)
    save_png(os.path.join(OUT, "T_Wolf_Coat_BC.png"), bc, srgb=True)
    save_png(os.path.join(OUT, "T_Wolf_Coat_R.png"), r_img, srgb=False)
    save_png(os.path.join(OUT, "T_Wolf_Coat_N.png"), n_img, srgb=False)

    # 2) CEREMONIAL MANE: heavy pale-silver mantle (U = root-to-tip 0..1; roots charcoal-ash, tips bright pale silver)
    m_rgb = np.zeros((S, S, 3), dtype=np.float32)
    root_col = np.array([0.24, 0.26, 0.29], dtype=np.float32)
    tip_col = np.array([0.78, 0.80, 0.83], dtype=np.float32)
    t_u = np.clip(xs ** 0.75, 0.0, 1.0)
    m_rgb[:] = root_col * (1.0 - t_u[..., None]) + tip_col * t_u[..., None]
    m_rough = np.full((S, S), 0.76, dtype=np.float32)
    m_height = np.full((S, S), 0.5, dtype=np.float32)

    paint_strokes(m_rgb, m_rough, m_height, rng, 1800, (0, 1), (0, 1), (48, 120), (6, 16),
                  (0.54, 0.57, 0.61), (0.88, 0.90, 0.93), 0.74, 0.22, angle_rad=0.0, angle_jitter=0.08, alpha=0.40)
    paint_strokes(m_rgb, m_rough, m_height, rng, 900, (0, 0.45), (0, 1), (36, 85), (5, 13),
                  (0.14, 0.16, 0.20), (0.34, 0.36, 0.40), 0.82, -0.15, angle_rad=0.0, angle_jitter=0.10, alpha=0.38)
    paint_strokes(m_rgb, m_rough, m_height, rng, 1800, (0.2, 1.0), (0, 1), (22, 60), (2.5, 5.5),
                  (0.76, 0.79, 0.84), (0.94, 0.95, 0.97), 0.70, 0.25, angle_rad=0.0, angle_jitter=0.07, alpha=0.35)

    m_bc = np.concatenate([m_rgb, np.ones((S, S, 1), dtype=np.float32)], axis=-1)
    m_r = np.stack([m_rough, m_rough, m_rough, np.ones_like(m_rough)], axis=-1)
    m_n = height_to_normal(m_height, strength=4.0)
    save_png(os.path.join(OUT, "T_Wolf_Mane_BC.png"), m_bc, srgb=True)
    save_png(os.path.join(OUT, "T_Wolf_Mane_R.png"), m_r, srgb=False)
    save_png(os.path.join(OUT, "T_Wolf_Mane_N.png"), m_n, srgb=False)

    # 3) LEG & WET PAWS: V = 0 (paw bottom, row S-1 after flipud -> ys ~ 1.0) to 1 (shoulder, ys ~ 0.0).
    l_rgb = np.zeros((S, S, 3), dtype=np.float32)
    wet = np.clip((ys - 0.72) / 0.22, 0.0, 1.0)
    wet = wet * wet * (3.0 - 2.0 * wet)
    paw_col = np.array([0.04, 0.045, 0.055], dtype=np.float32)
    leg_col = np.array([0.24, 0.25, 0.27], dtype=np.float32)
    upper_col = np.array([0.34, 0.35, 0.37], dtype=np.float32)
    l_rgb[:] = upper_col * (1.0 - ys[..., None]) + leg_col * ys[..., None]
    l_rgb = l_rgb * (1.0 - wet[..., None]) + paw_col * wet[..., None]
    l_rough = np.broadcast_to(0.85 * (1.0 - wet) + 0.18 * wet, (S, S)).copy()
    l_height = np.full((S, S), 0.5, dtype=np.float32)

    paint_strokes(l_rgb, l_rough, l_height, rng, 1500, (0, 1), (0.0, 0.78), (30, 80), (5, 14),
                  (0.14, 0.15, 0.17), (0.48, 0.50, 0.52), 0.84, 0.16, angle_rad=math.pi * 0.5, angle_jitter=0.14, alpha=0.36)
    paint_strokes(l_rgb, l_rough, l_height, rng, 700, (0, 1), (0.72, 1.0), (18, 45), (4, 10),
                  (0.02, 0.025, 0.035), (0.08, 0.09, 0.11), 0.18, 0.12, angle_rad=math.pi * 0.5, angle_jitter=0.16, alpha=0.45)

    l_bc = np.concatenate([l_rgb, np.ones((S, S, 1), dtype=np.float32)], axis=-1)
    l_r = np.stack([l_rough, l_rough, l_rough, np.ones_like(l_rough)], axis=-1)
    save_png(os.path.join(OUT, "T_Wolf_Leg_BC.png"), l_bc, srgb=True)
    save_png(os.path.join(OUT, "T_Wolf_Leg_R.png"), l_r, srgb=False)
    print("WOLF TEXTURES DONE")


def loft_uv(bm, uv_layer, rings, axis="x", sides=22, cap=True, mat_idx=0, v_mode="girth", deform=None):
    """Smooth sculpted loft with clean anatomical UV coordinates."""
    verts = []
    n_rings = len(rings)
    for r_idx, (t, oa, ob, ra, rb) in enumerate(rings):
        ring = []
        for i in range(sides):
            ang = 2.0 * math.pi * i / sides
            ca, sa = math.cos(ang), math.sin(ang)
            a = oa + ca * ra
            b = ob + sa * rb
            if deform is not None:
                a, b = deform(r_idx / max(1, n_rings - 1), ang, a, b)
            co = (t, a, b) if axis == "x" else (a, b, t) if axis == "z" else (a, t, b)
            ring.append(bm.verts.new(co))
        verts.append(ring)

    for r_idx in range(n_rings - 1):
        u0 = r_idx / max(1, n_rings - 1)
        u1 = (r_idx + 1) / max(1, n_rings - 1)
        r0, r1 = verts[r_idx], verts[r_idx + 1]
        for i in range(sides):
            j = (i + 1) % sides
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat_idx
            f.smooth = True
            # V: 0.5 at +Z (spine/top, ang = pi/2), 0 & 1 at -Z (belly/bottom)
            a0 = 2.0 * math.pi * i / sides
            a1 = 2.0 * math.pi * (i + 1) / sides
            if v_mode == "girth":
                # Map angle so sin=+1 (top) -> 0.5, sin=-1 (bottom) -> 0 or 1
                v0 = 0.5 + 0.5 * math.cos(a0 - math.pi * 0.5) * (1.0 if math.cos(a0) >= 0 else -1.0)
                # Continuous wrap: shift angle so bottom (-pi/2) is 0..1 and top (+pi/2) is 0.5
                v0 = ((a0 + math.pi * 0.5) / (2.0 * math.pi)) % 1.0
                v1 = ((a1 + math.pi * 0.5) / (2.0 * math.pi)) % 1.0
                if v1 < v0 and i == sides - 1:
                    v1 = 1.0
                uvs = [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
            elif v_mode == "leg":
                # V = height (1 at top, 0 at bottom paw), U = wrap around leg
                tu0 = i / sides
                tu1 = (i + 1) / sides
                tv0 = 1.0 - u0
                tv1 = 1.0 - u1
                uvs = [(tu0, tv0), (tu1, tv0), (tu1, tv1), (tu0, tv1)]
            else:
                v0 = i / sides
                v1 = (i + 1) / sides
                uvs = [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
            for loop, uv in zip(f.loops, uvs):
                loop[uv_layer].uv = uv

    if cap:
        for end_ring, rev, u_val in ((verts[0], True, 0.0), (verts[-1], False, 1.0)):
            c = sum((v.co for v in end_ring), Vector()) / len(end_ring)
            cv = bm.verts.new(c)
            for i in range(sides):
                j = (i + 1) % sides
                tri = (end_ring[j], end_ring[i], cv) if rev else (end_ring[i], end_ring[j], cv)
                f = bm.faces.new(tri)
                f.material_index = mat_idx
                f.smooth = True
                for loop in f.loops:
                    loop[uv_layer].uv = (u_val, 0.5)
    return verts


def add_fur_lock(bm, uv_layer, base, dir_vec, side_vec, up_vec, length, width, thickness, mat_idx=0):
    """Adds a sculpted, tapering fur lock / mantle plume with U=0 at root, U=1 at tip."""
    segs = 4
    rings = []
    for s in range(segs):
        t = s / (segs - 1)
        # Slight graceful droop along the lock
        p = base + dir_vec * (length * t) - up_vec * (length * 0.14 * t * t)
        w = width * (1.0 - 0.72 * (t ** 1.3))
        th = thickness * (1.0 - 0.80 * t)
        r = [
            bm.verts.new(p - side_vec * w),
            bm.verts.new(p + up_vec * th),
            bm.verts.new(p + side_vec * w),
            bm.verts.new(p - up_vec * th * 0.45),
        ]
        rings.append(r)
    tip = bm.verts.new(base + dir_vec * (length * 1.12) - up_vec * (length * 0.20))
    for s in range(segs - 1):
        u0 = s / segs
        u1 = (s + 1) / segs
        r0, r1 = rings[s], rings[s + 1]
        for i in range(4):
            j = (i + 1) % 4
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat_idx
            f.smooth = True
            for loop, uv in zip(f.loops, [(u0, i / 4.0), (u0, (i + 1) / 4.0), (u1, (i + 1) / 4.0), (u1, i / 4.0)]):
                loop[uv_layer].uv = uv
    r_last = rings[-1]
    for i in range(4):
        j = (i + 1) % 4
        f = bm.faces.new((r_last[i], r_last[j], tip))
        f.material_index = mat_idx
        f.smooth = True
        for loop, uv in zip(f.loops, [(0.85, i / 4.0), (0.85, (i + 1) / 4.0), (1.0, 0.5)]):
            loop[uv_layer].uv = uv


def export_part(bm, name, subdiv=1, mat_names=("M_PH_Wolf",)):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mname in mat_names:
        mat = bpy.data.materials.get(mname) or bpy.data.materials.new(mname)
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if subdiv > 0:
        mod = ob.modifiers.new("Subsurf", "SUBSURF")
        mod.levels = subdiv
        mod.render_levels = subdiv
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), **FBX_SETTINGS)
    xs = [v.co.x for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    print(f"WOLF {name} base_faces={len(me.polygons)} x={min(xs):.2f}..{max(xs):.2f} z={min(zs):.2f}..{max(zs):.2f}")
    return ob


def build_body():
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # Horse-sized muscular torso: ~1.88 m long, deep chest, tucked loins, powerful haunches, proud withers ridge.
    def body_deform(u, ang, a, b):
        # Prominent muscular spine ridge along the top (sin(ang) > 0.7) and flat-ish sternum at bottom
        sa = math.sin(ang)
        if sa > 0.65:
            # Withers peak around u=0.68..0.82
            withers = math.exp(-((u - 0.74) / 0.18) ** 2)
            b += (sa - 0.65) * (0.06 + 0.08 * withers)
        return a, b

    rings = [
        (-0.94, 0.0,  0.04, 0.11, 0.12),
        (-0.84, 0.0,  0.05, 0.22, 0.24),
        (-0.66, 0.0,  0.04, 0.28, 0.30),  # powerful haunches
        (-0.42, 0.0,  0.02, 0.26, 0.27),
        (-0.14, 0.0,  0.02, 0.23, 0.24),  # tucked loins
        ( 0.16, 0.0, -0.01, 0.27, 0.31),  # deep ribcage
        ( 0.44, 0.0, -0.02, 0.32, 0.36),  # broad muscular chest
        ( 0.68, 0.0,  0.01, 0.30, 0.35),  # shoulders
        ( 0.84, 0.0,  0.06, 0.23, 0.26),  # neck base
        ( 0.94, 0.0,  0.10, 0.13, 0.15),
    ]
    loft_uv(bm, uv, rings, axis="x", sides=24, cap=True, v_mode="girth", deform=body_deform)
    export_part(bm, "SM_PH_Wolf_Body", subdiv=1, mat_names=("M_PH_Wolf",))


def build_mane():
    """Heavy pale-silver ceremonial mantle over the shoulders & neck (separate part so hackles rise!)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rng = random.Random(77)

    # Inner mantle collar shell (tucked inside the fur locks so the silhouette is pure layered fur, not a smooth ring)
    rings = [
        (-0.46, 0.0,  0.02, 0.22, 0.20),
        (-0.22, 0.0,  0.04, 0.30, 0.29),
        ( 0.04, 0.0,  0.05, 0.31, 0.31),
        ( 0.24, 0.0,  0.07, 0.26, 0.27),
        ( 0.38, 0.0,  0.11, 0.19, 0.20),
    ]
    loft_uv(bm, uv, rings, axis="x", sides=18, cap=True, v_mode="default")

    # Four layered tiers of dramatic swept-back ceremonial fur locks (including front ruff framing the neck)
    tiers = [
        (0.36, 0.21, 0.22, 22, 0.36, 0.068, 0.042, 0.18),  # front neck ruff
        (0.22, 0.28, 0.29, 24, 0.48, 0.078, 0.048, 0.14),  # upper ceremonial mantle
        (0.02, 0.33, 0.33, 24, 0.58, 0.088, 0.052, 0.10),  # mid shoulder mantle
        (-0.18, 0.32, 0.30, 22, 0.54, 0.080, 0.046, 0.06), # lower shoulder fringe
    ]
    for x0, ry, rz, n_locks, length, width, thick, lift in tiers:
        for i in range(n_locks):
            ang = 2.0 * math.pi * i / n_locks + rng.uniform(-0.08, 0.08)
            ca, sa = math.cos(ang), math.sin(ang)
            # Keep belly slightly lighter so chest ruff frames the front gracefully
            scale = 1.0 if sa > -0.4 else 0.72
            base = Vector((x0 + rng.uniform(-0.04, 0.04), ca * ry * 0.92, 0.05 + sa * rz * 0.92))
            out_rad = Vector((0.0, ca, sa)).normalized()
            dir_v = (Vector((-1.0, 0.0, lift * (0.4 + 0.6 * max(0.0, sa)))) + out_rad * 0.32).normalized()
            side_v = dir_v.cross(out_rad).normalized()
            up_v = side_v.cross(dir_v).normalized()
            add_fur_lock(bm, uv, base, dir_v, side_v, up_v,
                         length * scale * rng.uniform(0.85, 1.18),
                         width * rng.uniform(0.85, 1.15),
                         thick, mat_idx=0)
    export_part(bm, "SM_PH_Wolf_Mane", subdiv=0, mat_names=("M_Wolf_Mane",))


def build_head():
    """Sculpted horse-sized wolf head: arching neck, brow ridge, cheek ruffs, snout, jaw, torn right ear, pale amber eyes."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")

    # Neck -> skull -> snout
    def head_deform(u, ang, a, b):
        sa = math.sin(ang)
        ca = math.cos(ang)
        # Brow ridge & cheekbones around skull (u=0.45..0.60)
        if 0.42 < u < 0.62 and sa > 0.25:
            brow = math.exp(-((u - 0.52) / 0.07) ** 2)
            b += 0.045 * brow * sa
            a += 0.03 * brow * (1.0 if ca >= 0 else -1.0) * abs(ca)
        # Flattened bridge of snout
        if u > 0.65 and sa > 0.4:
            b -= 0.012 * (sa - 0.4)
        return a, b

    rings = [
        (0.00, 0.0, 0.00, 0.21, 0.24),  # neck root
        (0.14, 0.0, 0.11, 0.19, 0.22),
        (0.28, 0.0, 0.21, 0.18, 0.20),  # back of skull
        (0.42, 0.0, 0.25, 0.20, 0.19),  # broad cranium & cheeks
        (0.54, 0.0, 0.23, 0.16, 0.16),  # brow / eye sockets
        (0.66, 0.0, 0.19, 0.105, 0.105), # upper snout
        (0.79, 0.0, 0.17, 0.075, 0.078), # muzzle
        (0.88, 0.0, 0.16, 0.052, 0.055), # nose pad
    ]
    loft_uv(bm, uv, rings, axis="x", sides=22, cap=True, mat_idx=0, v_mode="girth", deform=head_deform)

    # Distinct lower jaw
    jaw_rings = [
        (0.42, 0.0, 0.12, 0.12, 0.065),
        (0.58, 0.0, 0.10, 0.085, 0.052),
        (0.74, 0.0, 0.10, 0.058, 0.042),
        (0.83, 0.0, 0.11, 0.038, 0.030),
    ]
    loft_uv(bm, uv, jaw_rings, axis="x", sides=14, cap=True, mat_idx=0, v_mode="girth")

    # Cheek ruffs (two swept-back tufts on each side of the jaw)
    for side in (-1.0, 1.0):
        for k, (xo, zo, ang_z) in enumerate(((0.40, 0.18, 0.05), (0.34, 0.13, -0.10))):
            base = Vector((xo, side * 0.17, zo))
            dir_v = Vector((-0.85, side * 0.45, ang_z)).normalized()
            side_v = Vector((0.0, 0.0, 1.0))
            up_v = side_v.cross(dir_v).normalized()
            add_fur_lock(bm, uv, base, dir_v, side_v, up_v, 0.22 - k * 0.03, 0.055, 0.03, mat_idx=0)

    # Pointed wolf ears: left ear (side=+1) intact; right ear (side=-1) has a battle-torn notch!
    for side in (-1.0, 1.0):
        ear_rings = [
            (0.00, 0.0, 0.0, 0.075, 0.042),
            (0.07, 0.0, 0.0, 0.068, 0.036),
            (0.14, 0.0, 0.0, 0.052 if side > 0 else 0.032, 0.026),  # torn notch on right ear
            (0.21, 0.0, 0.0, 0.028 if side > 0 else 0.018, 0.016),
            (0.26, 0.0, 0.0, 0.008, 0.008),
        ]
        # Build ear in local space then place on skull
        e_verts = []
        base_pos = Vector((0.36, side * 0.115, 0.39))
        tilt = Vector((-0.18, side * 0.24, 1.0)).normalized()
        s_vec = Vector((0.0, 1.0, 0.0)).cross(tilt).normalized()
        f_vec = tilt.cross(s_vec).normalized()
        for r_idx, (h_e, _, _, rw, rt) in enumerate(ear_rings):
            # Slight notch offset on right ear
            notch_shift = -0.018 if (side < 0 and r_idx == 2) else 0.0
            ring = []
            for i in range(10):
                ang = 2.0 * math.pi * i / 10
                co = base_pos + tilt * h_e + s_vec * (math.cos(ang) * rt) + f_vec * (math.sin(ang) * rw + notch_shift)
                ring.append(bm.verts.new(co))
            e_verts.append(ring)
        for r0, r1 in zip(e_verts, e_verts[1:]):
            for i in range(10):
                j = (i + 1) % 10
                f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
                f.material_index = 0
                f.smooth = True
                for loop in f.loops:
                    loop[uv].uv = (0.35, 0.50)

    # Pale amber eyes (material slot 1 -> M_Wolf_Eyes), set proud under the brow so they gleam in moonlight
    for side in (-1.0, 1.0):
        ret = bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=10, radius=0.036)
        eye_center = Vector((0.578, side * 0.130, 0.266))
        for v in ret["verts"]:
            v.co = Vector((v.co.x * 1.15, v.co.y * 0.90, v.co.z * 0.92)) + eye_center
        for f in bm.faces:
            if all(v in ret["verts"] for v in f.verts):
                f.material_index = 1
                f.smooth = True
                for loop in f.loops:
                    loop[uv].uv = (0.5, 0.5)

    export_part(bm, "SM_PH_Wolf_Head", subdiv=1, mat_names=("M_PH_Wolf", "M_Wolf_Eyes"))


def build_leg():
    """Muscular articulated horse-sized wolf leg (~1.16 m) with hock angle and broad 4-toed wet paw."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings = [
        ( 0.00,  0.00, 0.0, 0.145, 0.130),  # shoulder / thigh joint
        (-0.24, -0.02, 0.0, 0.125, 0.112),  # muscular upper leg
        (-0.48, -0.05, 0.0, 0.092, 0.084),  # knee / elbow
        (-0.72, -0.06, 0.0, 0.072, 0.068),  # hock / forearm
        (-0.96, -0.01, 0.0, 0.062, 0.060),  # pastern / wrist
        (-1.08,  0.05, 0.0, 0.088, 0.078),  # broad paw arch
        (-1.16,  0.08, 0.0, 0.105, 0.088),  # broad heavy paw base
    ]
    loft_uv(bm, uv, rings, axis="z", sides=18, cap=True, mat_idx=0, v_mode="leg")

    # Four sculpted toes extending slightly forward from the paw
    for ty, tx, tr in ((-0.055, 0.14, 0.028), (-0.019, 0.165, 0.030), (0.019, 0.165, 0.030), (0.055, 0.14, 0.028)):
        ret = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=tr)
        for v in ret["verts"]:
            v.co = Vector((v.co.x * 1.65 + tx, v.co.y * 0.9 + ty, v.co.z * 0.8 - 1.13))
        for f in bm.faces:
            if all(v in ret["verts"] for v in f.verts):
                f.material_index = 0
                f.smooth = True
                for loop in f.loops:
                    loop[uv].uv = (0.5, 0.05)

    export_part(bm, "SM_PH_Wolf_Leg", subdiv=1, mat_names=("M_Wolf_Leg",))


def build_tail():
    """Long, thick, plumed wolf tail (~0.98 m) with layered fur locks."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings = [
        ( 0.00, 0.0,  0.00, 0.065, 0.070),
        (-0.18, 0.0, -0.04, 0.115, 0.125),
        (-0.42, 0.0, -0.12, 0.138, 0.148),
        (-0.68, 0.0, -0.22, 0.118, 0.125),
        (-0.88, 0.0, -0.32, 0.062, 0.068),
        (-0.98, 0.0, -0.37, 0.020, 0.022),
    ]
    loft_uv(bm, uv, rings, axis="x", sides=16, cap=True, mat_idx=0, v_mode="girth")
    # Plume locks draping along underside of tail
    for x, z, L in ((-0.20, -0.11, 0.24), (-0.42, -0.20, 0.28), (-0.64, -0.29, 0.24)):
        add_fur_lock(bm, uv, Vector((x, 0.0, z)), Vector((-0.82, 0.0, -0.57)).normalized(),
                     Vector((0.0, 1.0, 0.0)), Vector((-0.57, 0.0, 0.82)).normalized(), L, 0.075, 0.045, mat_idx=0)
    export_part(bm, "SM_PH_Wolf_Tail", subdiv=1, mat_names=("M_PH_Wolf",))


generate_textures()
build_body()
build_mane()
build_head()
build_leg()
build_tail()
print("WOLF HORSE-SIZED DONE")
