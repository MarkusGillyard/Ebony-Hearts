"""Placeholder wolf for the first-person prototype (milestone 5): low-poly, faceted parts that the game poses and
animates in code (no skeleton): a body, a head with its neck and ears, one leg (used four times) and a tail. Each
part's origin is its joint, so turning the part swings it about that joint. The wolf faces +X; about 80 cm at the
shoulder and 1.6 m nose to tail. The parts also carry a vertex-colour coat; the game's material draws its own (import_wolf.py). No wolf model
exists yet; the creator authors the real one.

Usage: blender -b --factory-startup -P make_wolf.py -- <out dir>
Writes SM_PH_Wolf_Body.fbx, SM_PH_Wolf_Head.fbx, SM_PH_Wolf_Leg.fbx, SM_PH_Wolf_Tail.fbx.
"""
import math
import os
import sys

import bmesh
import bpy
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

SIDES = 9
BACK = (0.16, 0.15, 0.16)    # dark grey along the back
BELLY = (0.52, 0.48, 0.43)   # pale under the chin, chest and belly


def loft(bm, rings, axis="x", sides=SIDES, cap=True, jag=0.0, seed=1):
    """A tube through rings (position along the axis, offset a, offset b, radius a, radius b); faceted like cut stone."""
    import random
    rng = random.Random(seed)
    verts = []
    for (t, oa, ob, ra, rb) in rings:
        ring = []
        for i in range(sides):
            ang = 2 * math.pi * i / sides
            j = 1.0 + rng.uniform(-jag, jag)
            a = oa + math.cos(ang) * ra * j
            b = ob + math.sin(ang) * rb * j
            co = (t, a, b) if axis == "x" else (a, b, t) if axis == "z" else (a, t, b)
            ring.append(bm.verts.new(co))
        verts.append(ring)
    for r0, r1 in zip(verts, verts[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if cap:
        bm.faces.new(list(reversed(verts[0])))
        bm.faces.new(verts[-1])
    return verts


def cone(bm, base_c, base_r, tip, sides=4, flat=1.0):
    base = []
    for i in range(sides):
        ang = 2 * math.pi * i / sides + math.pi / 4
        base.append(bm.verts.new(base_c + Vector((math.cos(ang) * base_r, math.sin(ang) * base_r * flat, 0))))
    t = bm.verts.new(tip)
    for i in range(sides):
        bm.faces.new((base[i], base[(i + 1) % sides], t))
    bm.faces.new(list(reversed(base)))


def finish(bm, name, top, bottom):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = False
    layer = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    me.color_attributes.active_color = layer
    me.color_attributes.render_color_index = me.color_attributes.active_color_index
    for poly in me.polygons:
        # Coat: dark on top-facing and high faces, pale on low and downward faces.
        z = sum(me.vertices[v].co.z for v in poly.vertices) / len(poly.vertices)
        h = max(0.0, min(1.0, (z - bottom) / max(1e-4, top - bottom)))
        f = max(0.0, min(1.0, 0.55 * h + 0.45 * (poly.normal.z * 0.5 + 0.5)))
        c = tuple(BELLY[k] + (BACK[k] - BELLY[k]) * f for k in range(3))
        for li in poly.loop_indices:
            layer.data[li].color = (c[0], c[1], c[2], 1.0)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), **FBX_SETTINGS)
    xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print(f"WOLF {name} faces={len(me.polygons)} x={min(xs):.2f}..{max(xs):.2f} z={min(zs):.2f}..{max(zs):.2f}")


def body():
    bm = bmesh.new()
    # Rump to chest: deep in the chest, tucked at the waist, a ruff over the shoulders.
    loft(bm, [(-0.60, 0, 0.03, 0.08, 0.09), (-0.52, 0, 0.04, 0.15, 0.16), (-0.34, 0, 0.03, 0.17, 0.17),
              (-0.10, 0, 0.01, 0.15, 0.16), (0.14, 0, 0.0, 0.18, 0.21), (0.34, 0, 0.01, 0.21, 0.24),
              (0.48, 0, 0.04, 0.16, 0.19), (0.56, 0, 0.07, 0.08, 0.10)], jag=0.06, seed=3)
    finish(bm, "SM_PH_Wolf_Body", 0.25, -0.24)


def head():
    bm = bmesh.new()
    # From the neck's root (the joint) up and forward to the skull, then the long snout.
    loft(bm, [(0.00, 0, 0.00, 0.13, 0.15), (0.10, 0, 0.07, 0.12, 0.13), (0.20, 0, 0.13, 0.11, 0.12),
              (0.29, 0, 0.16, 0.12, 0.12), (0.37, 0, 0.15, 0.09, 0.10), (0.47, 0, 0.12, 0.055, 0.06),
              (0.55, 0, 0.10, 0.035, 0.04)], jag=0.05, seed=5)
    for side in (-1, 1):
        cone(bm, Vector((0.26, side * 0.065, 0.25)), 0.04, Vector((0.24, side * 0.08, 0.37)), sides=4, flat=0.6)
    finish(bm, "SM_PH_Wolf_Head", 0.36, 0.0)


def leg():
    bm = bmesh.new()
    # From the hip or shoulder (the joint) down to the paw, along -Z.
    loft(bm, [(0.00, 0.00, 0, 0.075, 0.085), (-0.20, 0.00, 0, 0.055, 0.065), (-0.40, 0.012, 0, 0.035, 0.04),
              (-0.56, 0.02, 0, 0.035, 0.038), (-0.62, 0.05, 0, 0.05, 0.04)], axis="z", sides=7, jag=0.04, seed=7)
    finish(bm, "SM_PH_Wolf_Leg", 0.0, -0.62)


def tail():
    bm = bmesh.new()
    # From its root (the joint) back and down: bushy, then thinning to a point.
    loft(bm, [(0.00, 0, 0.00, 0.035, 0.04), (-0.12, 0, -0.03, 0.065, 0.07), (-0.26, 0, -0.08, 0.075, 0.075),
              (-0.38, 0, -0.15, 0.055, 0.055), (-0.47, 0, -0.20, 0.015, 0.015)], sides=7, jag=0.12, seed=9)
    finish(bm, "SM_PH_Wolf_Tail", 0.0, -0.22)


body(); head(); leg(); tail()
print("WOLF DONE")
