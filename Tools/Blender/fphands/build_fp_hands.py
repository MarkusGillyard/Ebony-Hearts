"""Builds the first-person hands from the Blender Foundation's Human Base Meshes bundle (CC0): the realistic male body's
arms and hands, cut at the shoulders, rigged on a small skeleton that uses the same bone names as the game's
characters (root, spine, clavicles, arms, hands and three bones per finger, neck and head), so the first-person arm
code drives it unchanged. Joints are found from the mesh itself: arm centre lines from cross-sections, the wrist at the
forearm's narrowest point, fingers by splitting the hand into its five digits and walking each one's centre line.

Anatomy (see the first-person hands study): finger bones in the proportions of real phalanges (proximal : middle :
distal about 0.49 : 0.30 : 0.21 of knuckle-to-tip), the knuckle joint well behind the finger web, and two forearm twist
bones per arm. Forearm rotation (palm down or up) happens along the whole forearm, not at the wrist, so the forearm skin
is shared out between the elbow end, the two twist bones and the wrist end; the game turns each twist bone by part of
the hand's rotation. Each finger's skin follows only its own bones and the hand.

Usage:
  blender -b --factory-startup -P build_fp_hands.py -- <human_base_meshes_bundle.blend> <out.fbx> [preview dir]
"""
import math
import sys
from collections import defaultdict

import bmesh
import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = args[0], args[1]
PREVIEW = args[2] if len(args) > 2 else None
SUBDIV = 2            # multires level kept (0 = base, about 10.5k vertices for the whole body)

bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(SRC, link=False) as (src, dst):
    dst.objects = ["GEO-body_male_realistic"]
body = bpy.data.objects["GEO-body_male_realistic"]
bpy.context.scene.collection.objects.link(body)
body.parent = None
body.location = (0, 0, 0)
body.rotation_euler = (0, 0, 0)
bpy.context.view_layer.objects.active = body
for md in list(body.modifiers):
    if md.type == "MULTIRES":
        md.levels = SUBDIV
        md.render_levels = SUBDIV
        bpy.ops.object.multires_apply_base(modifier=md.name) if SUBDIV == 0 else None
        bpy.ops.object.modifier_apply(modifier=md.name)
    else:
        bpy.ops.object.modifier_apply(modifier=md.name)
me = body.data
V = [v.co.copy() for v in me.vertices]
adj = defaultdict(set)
for e in me.edges:
    a, b = e.vertices
    adj[a].add(b)
    adj[b].add(a)
print(f"FPHANDS body vertices {len(V)}")


def components(idx):
    idx = set(idx)
    seen, out = set(), []
    for s in idx:
        if s in seen:
            continue
        comp, stack = [], [s]
        seen.add(s)
        while stack:
            v = stack.pop()
            comp.append(v)
            for n in adj[v]:
                if n in idx and n not in seen:
                    seen.add(n)
                    stack.append(n)
        out.append(comp)
    return out


def centroid(idx):
    return sum((V[i] for i in idx), Vector()) / max(1, len(idx))


# --- The right arm (character's right is -X; the body faces -Y, Z up) -----------------------------------------------
# Below the armpit, a horizontal slice through the right side holds two islands, torso and arm; the arm is the outer
# one. Walk down slice by slice, keeping the outer island's centre: the arm's centre line, down to the fingertips.
right = [i for i, p in enumerate(V) if p.x < -0.02]
zs = [V[i].z for i in right]
line = []   # (z, centre, width)
arm_verts = set()
z = 1.30
while z > 0.66:
    sl = [i for i in right if z - 0.012 <= V[i].z < z]
    if sl:
        comps = components(sl)
        comps = [c for c in comps if len(c) > 3]
        if len(comps) >= 2 or (line and comps):
            outer = min(comps, key=lambda c: centroid(c).x)   # most negative x
            arm_verts.update(outer)
            c = centroid(outer)
            w = max(V[i].x for i in outer) - min(V[i].x for i in outer)
            line.append((z, c, w))
    z -= 0.01
hand_bottom = min(V[i].z for i in right if V[i].x < -0.30)
print(f"FPHANDS arm slices {len(line)}, hand bottom z={hand_bottom:.3f}")

# Shoulder: the head of the humerus sits inside the deltoid, about level with the top of the armpit.
arm_top = line[0][1]
shoulder = Vector((arm_top.x + 0.035, arm_top.y, line[0][0] + 0.115))
# Wrist: the narrowest slice in the lower forearm, above where the hand widens again.
fore = [(z, c, w) for (z, c, w) in line if 0.80 < z < 1.02]
wz, wrist, ww = min(fore, key=lambda t: t[2])
# Elbow: 55% of the way from shoulder to wrist (humerus about 30 cm, forearm about 25 cm in this body).
seg = wrist - shoulder
elbow_guess = shoulder + seg * 0.545
elbow = min(line, key=lambda t: abs(t[0] - elbow_guess.z))[1].copy()
elbow.y += 0.012   # the joint sits toward the back of the elbow
print(f"FPHANDS shoulder {tuple(round(v, 3) for v in shoulder)} elbow {tuple(round(v, 3) for v in elbow)} "
      f"wrist {tuple(round(v, 3) for v in wrist)} (width {ww:.3f})")

# --- The hand and its fingers -----------------------------------------------------------------------------------------
hand_axis = Vector((0, 0, -1))
tip_dir = (centroid([i for i in right if V[i].z < hand_bottom + 0.02 and V[i].x < -0.30]) - wrist).normalized()
hand_idx = [i for i in right if (V[i] - wrist).dot(tip_dir) > -0.005 and V[i].x < -0.28]
L = max((V[i] - wrist).dot(tip_dir) for i in hand_idx)
print(f"FPHANDS hand vertices {len(hand_idx)}, length {L:.3f}")

# Raise a cut across the hand until the part beyond it falls into separate digits.
fingers = None
for f in [x / 100 for x in range(30, 80)]:
    beyond = [i for i in hand_idx if (V[i] - wrist).dot(tip_dir) > f * L]
    comps = [c for c in components(beyond) if len(c) > 15]
    if len(comps) == 4:
        fingers = comps
        cut4 = f
        break
if fingers is None:
    raise RuntimeError("could not separate the four fingers")
# The thumb branches off nearer the wrist, toward the front (-Y): take the lower cut where a fifth digit appears.
thumb = None
for f in [x / 100 for x in range(20, int(cut4 * 100))]:
    beyond = [i for i in hand_idx if (V[i] - wrist).dot(tip_dir) > f * L]
    comps = [c for c in components(beyond) if len(c) > 15]
    if len(comps) >= 2:
        cand = min(comps, key=lambda c: centroid(c).y)
        if len(comps) == 2 and len(cand) < len(max(comps, key=len)):
            thumb = cand
            break
if thumb is None:
    raise RuntimeError("could not separate the thumb")
thumb_set = set(thumb)
fingers = [[i for i in c if i not in thumb_set] for c in fingers]
fingers = [c for c in fingers if len(c) > 15]
# Order index -> pinky: the index is nearest the thumb (front, -Y).
fingers.sort(key=lambda c: centroid(c).y)
NAMES = ["index", "middle", "ring", "pinky"]
print(f"FPHANDS fingers {[len(c) for c in fingers]}, thumb {len(thumb)}, cut {cut4:.2f}")


def chain(comp, base_extra, ratios, start=None):
    """Joints along a digit: from its root (behind the web by base_extra of its free length) to the tip."""
    pts = [V[i] for i in comp]
    c = sum(pts, Vector()) / len(pts)
    # Principal axis by power iteration on the covariance.
    cov = [[sum((p[a] - c[a]) * (p[b] - c[b]) for p in pts) for b in range(3)] for a in range(3)]
    ax = tip_dir.copy()
    for _ in range(30):
        ax = Vector([sum(cov[a][b] * ax[b] for b in range(3)) for a in range(3)]).normalized()
    if ax.dot(tip_dir) < 0:
        ax = -ax
    proj = [(p - c).dot(ax) for p in pts]
    lo, hi = min(proj), max(proj)
    free = hi - lo

    def centre_at(t):
        band = [p for p, s in zip(pts, proj) if abs(s - t) < 0.004]
        if len(band) < 3:
            band = sorted(pts, key=lambda p: abs((p - c).dot(ax) - t))[:6]
        return sum(band, Vector()) / len(band)

    web = centre_at(lo + 0.003)
    tip = c + ax * hi
    root = start if start is not None else web - ax * (free * base_extra)
    total = (tip - root).length
    joints = [root]
    acc = 0.0
    for r in ratios[:-1]:
        acc += r
        t_world = root + (tip - root) * acc
        t = (t_world - c).dot(ax)
        joints.append(centre_at(t) if t > lo + 0.002 else t_world)
    joints.append(tip)
    return joints, ax


finger_chains = {}
for name, comp in zip(NAMES, fingers):
    j, ax = chain(comp, 0.28, [0.49, 0.30, 0.21])
    finger_chains[name] = j
# Thumb: its metacarpal starts near the wrist on the thumb side; the free digit gives the two phalanges.
tj, tax = chain(thumb, 0.0, [0.55, 0.45])
cmc = wrist + (tj[0] - wrist) * 0.35
finger_chains["thumb"] = [cmc, tj[0], tj[1], tj[2]]
for k, j in finger_chains.items():
    print(f"FPHANDS {k}: " + " ".join(str(tuple(round(v, 3) for v in p)) for p in j))
knuckles = sum((finger_chains[n][0] for n in NAMES), Vector()) / 4

# Tag each digit's vertices (beyond the webs) so its skin can be kept to its own bones after binding.
digit_attr = me.attributes.new("eh_digit", "INT", "POINT")
for n, comp in enumerate(fingers):
    for i in comp:
        digit_attr.data[i].value = n + 1
for i in thumb:
    digit_attr.data[i].value = 5

# --- Keep only the arms (and a little of each shoulder) ---------------------------------------------------------------
bm = bmesh.new()
bm.from_mesh(me)
keep_x = shoulder.x + 0.05     # right side; mirrored for the left


# The arm: everything within a capsule round its bones (shoulder to elbow to wrist to knuckles, and each digit), kept
# to the piece connected to the hand, so neither the torso at the armpit nor the hips beside the hand come with it.
def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.length_squared)))
    return (p - (a + ab * t)).length


segs = [(shoulder + (shoulder - elbow).normalized() * 0.03, elbow, 0.075), (elbow, wrist, 0.062),
        (wrist, knuckles, 0.07), (wrist, finger_chains["thumb"][1], 0.04)]
for j in finger_chains.values():
    segs += [(j[k], j[k + 1], 0.022) for k in range(len(j) - 1)]
near = [i for i in right if any(seg_dist(V[i], a, b) < r for a, b, r in segs)]
tip_vertex = min(fingers[1], key=lambda i: V[i].z)
arm_r = next(set(c) for c in components(near) if tip_vertex in c)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.verts[i] for i in range(len(V)) if i not in arm_r], context="VERTS")
bm.to_mesh(me)
bm.free()
me.update()
print(f"FPHANDS arms mesh vertices {len(me.vertices)}")

# --- The skeleton -----------------------------------------------------------------------------------------------------
arm = bpy.data.armatures.new("FPHands")
rig = bpy.data.objects.new("FPHands", arm)
bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
eb = arm.edit_bones
lateral = (finger_chains["pinky"][0] - finger_chains["index"][0]).normalized()   # across the right hand


def bone(name, head, tail, parent=None, roll_axis=None):
    b = eb.new(name)
    b.head, b.tail = head, tail
    if parent:
        b.parent = eb[parent]
        b.use_connect = False
    if roll_axis is not None:
        b.align_roll(roll_axis)
    return b


def mirror(p):
    return Vector((-p.x, p.y, p.z))


bone("root", Vector((0, 0, 0)), Vector((0, 0.1, 0)))
bone("pelvis", Vector((0, 0, 0.95)), Vector((0, 0, 1.05)), "root")
bone("spine_01", Vector((0, 0, 1.05)), Vector((0, 0, 1.18)), "pelvis")
bone("spine_02", Vector((0, 0, 1.18)), Vector((0, 0, 1.30)), "spine_01")
bone("spine_03", Vector((0, 0, 1.30)), Vector((0, 0, 1.44)), "spine_02")
# The head bone sits about 21 cm above the shoulder joints, as on the game's character skeletons: the first-person arm
# code places the model by its head bone, so the shoulders land where it expects.
head_z = shoulder.z + 0.211
bone("neck_01", Vector((0, -0.02, head_z - 0.09)), Vector((0, -0.03, head_z - 0.01)), "spine_03")
bone("head", Vector((0, -0.04, head_z)), Vector((0, -0.04, head_z + 0.10)), "neck_01")
for side, f in (("r", lambda p: p), ("l", mirror)):
    bone(f"clavicle_{side}", f(Vector((-0.02, -0.04, 1.43))), f(shoulder), "spine_03")
    bone(f"upperarm_{side}", f(shoulder), f(elbow), f"clavicle_{side}", roll_axis=Vector((0, -1, 0)))
    bone(f"lowerarm_{side}", f(elbow), f(wrist), f"upperarm_{side}", roll_axis=Vector((0, -1, 0)))
    # Twist bones along the forearm (children of the forearm, deforming only): one at its middle, one near the wrist.
    for tn, a, b in (("lowerarm_twist_01", 0.50, 0.70), ("lowerarm_twist_02", 0.85, 1.0)):
        bone(f"{tn}_{side}", f(elbow + (wrist - elbow) * a), f(elbow + (wrist - elbow) * b), f"lowerarm_{side}",
             roll_axis=Vector((0, -1, 0)))
    bone(f"hand_{side}", f(wrist), f(knuckles), f"lowerarm_{side}",
         roll_axis=f(lateral) if side == "r" else mirror(lateral))
    for n in NAMES + ["thumb"]:
        j = finger_chains[n]
        parent = f"hand_{side}"
        for k in range(3):
            nm = f"{n}_0{k + 1}_{side}"
            lat = f(lateral) if side == "r" else mirror(lateral)
            bone(nm, f(j[k]), f(j[k + 1]), parent, roll_axis=lat)
            parent = nm
bpy.ops.object.mode_set(mode="OBJECT")

# --- Mirror the mesh to make the left arm, then bind ------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body
body.name = "FPHands_Mesh"
mod = body.modifiers.new("Mirror", "MIRROR")
mod.use_axis[0] = True
mod.use_clip = False
mod.use_mirror_merge = False
bpy.ops.object.modifier_apply(modifier=mod.name)
mat = bpy.data.materials.new("M_FPHands_Skin")
body.data.materials.clear()
body.data.materials.append(mat)

bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
groups = [g.name for g in body.vertex_groups]
print(f"FPHANDS bound with {len(groups)} vertex groups")

# --- Weights: share the forearm out for twisting, and keep each digit to its own bones ---------------------------------
G = {g.name: g.index for g in body.vertex_groups}
for nm in ("lowerarm_twist_01_r", "lowerarm_twist_02_r", "lowerarm_twist_01_l", "lowerarm_twist_02_l"):
    if nm not in G:
        G[nm] = body.vertex_groups.new(name=nm).index
INV = {v: k for k, v in G.items()}
DIGIT_BONES = {1: "index", 2: "middle", 3: "ring", 4: "pinky", 5: "thumb"}
tags = body.data.attributes["eh_digit"].data
KNOTS = ((0.22, 0), (0.55, 1), (0.90, 2))   # forearm position (elbow 0 .. wrist 1) where each bone has full weight


def share(s):
    """Weights for (lowerarm, twist_01, twist_02) at forearm position s: piecewise linear between the knots."""
    out = [0.0, 0.0, 0.0]
    if s <= KNOTS[0][0]:
        out[0] = 1.0
    elif s >= KNOTS[-1][0]:
        out[2] = 1.0
    else:
        for (s0, a), (s1, b) in zip(KNOTS, KNOTS[1:]):
            if s0 <= s <= s1:
                t = (s - s0) / (s1 - s0)
                t = t * t * (3 - 2 * t)
                out[a] = 1.0 - t
                out[b] = t
                break
    return out


moved = cleaned = 0
for v in body.data.vertices:
    side = "r" if v.co.x < 0 else "l"
    sgn = 1.0 if side == "r" else -1.0
    e = Vector((elbow.x * sgn, elbow.y, elbow.z))
    w = Vector((wrist.x * sgn, wrist.y, wrist.z))
    ws = {INV[g.group]: g.weight for g in v.groups if g.weight > 0.0}
    fore = [f"lowerarm_{side}", f"lowerarm_twist_01_{side}", f"lowerarm_twist_02_{side}"]
    total = sum(ws.get(n, 0.0) for n in fore)
    if total > 1e-4:
        s = (v.co - e).dot(w - e) / (w - e).length_squared
        for n, k in zip(fore, share(max(0.0, min(1.0, s)))):
            ws[n] = total * k
        moved += 1
    d = tags[v.index].value
    if d:
        own = DIGIT_BONES[d]
        keep = {n: x for n, x in ws.items()
                if n.startswith(own + "_") or n == f"hand_{side}" or not any(n.startswith(o + "_") for o in DIGIT_BONES.values())}
        if len(keep) != len(ws):
            cleaned += 1
        ws = keep
    tot = sum(ws.values())
    if tot <= 1e-6:
        continue
    for g in list(v.groups):
        body.vertex_groups[g.group].remove([v.index])
    for n, x in ws.items():
        if x / tot > 1e-4:
            body.vertex_groups[G[n]].add([v.index], x / tot, "REPLACE")
print(f"FPHANDS weights: forearm shared on {moved} vertices, {cleaned} digit vertices cleaned of other digits")
body.data.attributes.remove(body.data.attributes["eh_digit"])

if PREVIEW:
    import os
    os.makedirs(PREVIEW, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.render.resolution_x = sc.render.resolution_y = 900
    arm.display_type = "STICK"
    rig.show_in_front = True
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    co = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(co)
    sc.camera = co
    sc.render.film_transparent = False

    def shot(loc, rot, scale, name):
        co.location = loc
        co.rotation_euler = rot
        cam.ortho_scale = scale
        sc.render.filepath = os.path.join(PREVIEW, name)
        bpy.ops.render.opengl(write_still=True) if False else bpy.ops.render.render(write_still=True)

    joints = [shoulder, elbow, wrist, knuckles] + [p for j in finger_chains.values() for p in j]
    mk = bpy.data.materials.new("marker")
    mk.diffuse_color = (1.0, 0.15, 0.1, 1.0)
    sc.display.shading.color_type = "MATERIAL"
    for p in joints:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0045, location=p, segments=10, ring_count=6)
        bpy.context.active_object.data.materials.append(mk)
        bpy.context.active_object.show_in_front = True
    hc = (wrist + knuckles) / 2
    shot((hc.x - 1.0, hc.y, hc.z), (math.radians(90), 0, math.radians(-90)), 0.30, "hand_side.png")
    shot((hc.x, hc.y - 1.0, hc.z), (math.radians(90), 0, 0), 0.30, "hand_front.png")
    shot((0, -3, 1.1), (math.radians(90), 0, 0), 1.2, "arms_front.png")

bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
rig.select_set(True)
bpy.ops.export_scene.fbx(
    filepath=OUT, use_selection=True, object_types={"ARMATURE", "MESH"},
    apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
    axis_forward="Y", axis_up="Z", bake_space_transform=False,
    use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True, use_triangles=False,
    use_custom_props=False, add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
    use_armature_deform_only=False, armature_nodetype="NULL", bake_anim=False,
    path_mode="STRIP", embed_textures=False, colors_type="NONE")
print(f"FPHANDS wrote {OUT}")
