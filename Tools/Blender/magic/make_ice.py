"""Placeholder ice meshes for the Ice Wall (milestone 4): a wall of leaning crystal shards on a frozen mound, an
irregular frozen-water sheet, and a ring of small shards for frozen feet. Faceted on purpose (flat shading), so every
face catches light like broken ice. Vertex colour red marks frost (the mound, the shards' feet and the sheet's
rim); green marks the shards' tips. Deterministic (fixed seed).

Usage: blender -b --factory-startup -P make_ice.py -- <out dir>
Writes SM_PH_IceWall.fbx (3 m wide, 2.4 m tall, about 0.5 m deep, base at 0), SM_PH_IceSheet.fbx (1 m radius,
scaled in game) and SM_PH_IceCuff.fbx (0.3 m radius).
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

# The Chapel's export settings: metres in Blender become centimetres in Unreal.
FBX_SETTINGS = dict(
    use_selection=True, object_types={"MESH"}, global_scale=1.0, apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y", bake_space_transform=True,
    use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True, use_triangles=True, colors_type="SRGB",
    prioritize_active_color=False, use_custom_props=False, add_leaf_bones=False, bake_anim=False, path_mode="STRIP",
    embed_textures=False, batch_mode="OFF")


def shard(bm, base, radius, height, lean, sides, rng, frost_to=0.25):
    """A crystal: an irregular prism with a pointed, off-centre tip, leaning by the matrix lean."""
    ring_lo, ring_hi = [], []
    tip_h = height * rng.uniform(0.18, 0.32)
    body = height - tip_h
    rot = rng.uniform(0, math.tau)
    for i in range(sides):
        a = rot + math.tau * i / sides + rng.uniform(-0.25, 0.25)
        r = radius * rng.uniform(0.75, 1.15)
        p = Vector((math.cos(a) * r, math.sin(a) * r, 0.0))
        ring_lo.append(base + lean @ (p + Vector((0, 0, -0.12))))
        ring_hi.append(base + lean @ (p * rng.uniform(0.8, 1.0) + Vector((0, 0, body * rng.uniform(0.9, 1.0)))))
    tip = base + lean @ Vector((rng.uniform(-0.3, 0.3) * radius, rng.uniform(-0.3, 0.3) * radius, height))
    lo = [bm.verts.new(v) for v in ring_lo]
    hi = [bm.verts.new(v) for v in ring_hi]
    t = bm.verts.new(tip)
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((lo[i], lo[j], hi[j], hi[i])))
        faces.append(bm.faces.new((hi[i], hi[j], t)))
    faces.append(bm.faces.new(list(reversed(lo))))
    return lo, hi, [t], faces


def colour(obj, fn):
    """Vertex colour per corner from fn(world position, normal) -> (r, g)."""
    me = obj.data
    layer = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index]
            r, g = fn(v.co, poly.normal)
            layer.data[li].color = (r, g, 0.0, 1.0)


def finish(bm, name, fn):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    for p in me.polygons:
        p.use_smooth = False
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=1.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    colour(obj, fn)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, name + ".fbx"), **FBX_SETTINGS)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print(f"ICE {name} tris={tris} x={min(xs):.2f}..{max(xs):.2f} y={min(ys):.2f}..{max(ys):.2f} z={min(zs):.2f}..{max(zs):.2f}")
    obj.select_set(False)


def wall():
    rng = random.Random(41)
    bm = bmesh.new()
    W, H = 3.0, 2.4
    # The frozen mound: a low, lumpy ridge the shards grow out of.
    n = 14
    pts = []
    for i in range(n + 1):
        x = -W * 0.53 + W * 1.06 * i / n
        pts.append([Vector((x, y * rng.uniform(0.8, 1.2), z)) for y, z in ((-0.32, -0.05), (-0.18, rng.uniform(0.16, 0.26)), (0.0, rng.uniform(0.28, 0.4)), (0.18, rng.uniform(0.16, 0.26)), (0.32, -0.05))])
    rows = [[bm.verts.new(p) for p in col] for col in pts]
    for i in range(n):
        for k in range(4):
            bm.faces.new((rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]))
    # Shards: tallest near the middle, leaning outward and a little toward either face, overlapping into one mass.
    count = 26
    for i in range(count):
        u = (i + rng.uniform(-0.35, 0.35)) / (count - 1)
        x = -W * 0.45 + W * 0.9 * u
        profile = 0.55 + 0.45 * math.cos((u - 0.5) * math.pi * 0.95)
        height = H * profile * rng.uniform(0.72, 1.0)
        radius = rng.uniform(0.11, 0.24) * (0.8 + 0.4 * profile)
        y = rng.uniform(-0.1, 0.1)
        lean = Matrix.Rotation(math.radians((u - 0.5) * 16 + rng.uniform(-6, 6)), 3, "Y") @ \
            Matrix.Rotation(math.radians(rng.uniform(-5, 5) - y * 30), 3, "X")
        shard(bm, Vector((x, y, 0.0)), radius, height, lean, rng.choice((5, 6, 6, 7)), rng)
        # A smaller splinter beside some of them.
        if rng.random() < 0.55:
            s = rng.uniform(0.35, 0.6)
            lean2 = lean @ Matrix.Rotation(math.radians(rng.uniform(-25, 25)), 3, "Y") @ Matrix.Rotation(math.radians(rng.choice((-1, 1)) * rng.uniform(8, 16)), 3, "X")
            shard(bm, Vector((x + rng.uniform(-0.12, 0.12), y + rng.uniform(-0.06, 0.06), 0.0)), radius * 0.55, height * s, lean2, 5, rng)
    finish(bm, "SM_PH_IceWall", lambda p, nrm: (max(0.0, min(1.0, 1.0 - p.z / 0.55)), max(0.0, min(1.0, (p.z - 1.5) / 0.9))))


def sheet():
    rng = random.Random(7)
    bm = bmesh.new()
    n = 48
    centre_top = bm.verts.new((0, 0, 0.02))
    rim_top, rim_bot = [], []
    for i in range(n):
        a = math.tau * i / n
        r = 1.0 * (0.86 + 0.14 * math.sin(a * 3 + 1.3) * 0.5 + rng.uniform(-0.07, 0.06))
        rim_top.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, rng.uniform(0.005, 0.02))))
        rim_bot.append(bm.verts.new((math.cos(a) * r * 1.02, math.sin(a) * r * 1.02, -0.02)))
    # Plates: the top is split into slightly tilted cracked facets around the centre.
    mid = []
    for i in range(n):
        a = math.tau * i / n
        r = rng.uniform(0.35, 0.65)
        mid.append(bm.verts.new((math.cos(a) * r, math.sin(a) * r, rng.uniform(0.0, 0.03))))
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((centre_top, mid[i], mid[j]))
        bm.faces.new((mid[i], rim_top[i], rim_top[j], mid[j]))
        bm.faces.new((rim_top[i], rim_bot[i], rim_bot[j], rim_top[j]))
    finish(bm, "SM_PH_IceSheet", lambda p, nrm: (max(0.0, min(1.0, (p.length - 0.55) / 0.4)), 0.0))


def cuff():
    rng = random.Random(3)
    bm = bmesh.new()
    for i in range(11):
        a = math.tau * i / 11 + rng.uniform(-0.2, 0.2)
        r = rng.uniform(0.16, 0.3)
        out = Vector((math.cos(a), math.sin(a), 0))
        axis = Vector((-out.y, out.x, 0))
        lean = Matrix.Rotation(math.radians(rng.uniform(15, 35)), 3, axis)
        shard(bm, out * r, rng.uniform(0.05, 0.09), rng.uniform(0.16, 0.38), lean, 5, rng)
    finish(bm, "SM_PH_IceCuff", lambda p, nrm: (max(0.0, min(1.0, 1.0 - p.z / 0.2)), 0.0))


wall()
sheet()
cuff()
print("ICE DONE")
