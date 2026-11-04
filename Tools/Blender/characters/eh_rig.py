"""Skeleton work on top of MPFB's game_engine rig: UE-style root name, the shared twist bones,
per-character secondary chains (hair, coat tails), Blender-side helper constraints and the bone list.

Core skeleton (identical on every Ebony Hearts fighter): the 53 game_engine bones with 'Root' renamed
'root', plus upperarm_twist_01_l/r, lowerarm_twist_01_l/r and thigh_twist_01_l/r (UE mannequin names).
Twist bones are deform bones driven in Blender by Transformation constraints (swing/twist extraction)
so animation exported with baking carries their motion; secondary chains are plain FK bones."""
import json
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

import eh_mesh as M

TWIST = (
    # name, parent (also the bone whose length the twist runs along), driver bone, factor, head_t, tail_t
    ("upperarm_twist_01", "upperarm", "upperarm", -0.5, 0.0, 0.5),
    ("lowerarm_twist_01", "lowerarm", "hand", 0.5, 0.5, 1.0),
    ("thigh_twist_01", "thigh", "thigh", -0.5, 0.0, 0.5),
)


def edit(rig):
    bpy.context.view_layer.objects.active = rig
    for o in bpy.context.view_layer.objects:
        o.select_set(o is rig)
    bpy.ops.object.mode_set(mode="EDIT")
    return rig.data.edit_bones


def obj_mode():
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")


def prepare(rig, name):
    rig.name = "Armature"
    rig.data.name = name + "_Skeleton"
    if "Root" in rig.data.bones:
        rig.data.bones["Root"].name = "root"
    rig.location = (0, 0, 0)
    rig.rotation_euler = (0, 0, 0)
    rig.scale = (1, 1, 1)
    rig.data.display_type = "STICK"
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"


def add_twist_bones(rig):
    eb = edit(rig)
    for name, parent, driver, factor, h, t in TWIST:
        for s in "lr":
            p = eb["%s_%s" % (parent, s)]
            b = eb.new("%s_%s" % (name, s))
            b.head = p.head.lerp(p.tail, h)
            b.tail = p.head.lerp(p.tail, t)
            b.roll = p.roll
            b.parent = p
            b.use_connect = False
            b.use_deform = True
    obj_mode()


def twist_constraints(rig):
    for name, parent, driver, factor, h, t in TWIST:
        for s in "lr":
            pb = rig.pose.bones["%s_%s" % (name, s)]
            for c in list(pb.constraints):
                pb.constraints.remove(c)
            c = pb.constraints.new("TRANSFORM")
            c.name = "twist_from_" + driver
            c.target = rig
            c.subtarget = "%s_%s" % (driver, s)
            c.target_space = "LOCAL"
            c.owner_space = "LOCAL"
            c.map_from = "ROTATION"
            c.map_to = "ROTATION"
            c.from_rotation_mode = "SWING_TWIST_Y"
            c.from_min_y_rot, c.from_max_y_rot = -math.pi, math.pi
            c.from_min_x_rot = c.from_min_z_rot = -math.pi
            c.from_max_x_rot = c.from_max_z_rot = math.pi
            c.map_to_x_from, c.map_to_y_from, c.map_to_z_from = "X", "Y", "Z"
            c.to_min_x_rot = c.to_max_x_rot = 0.0
            c.to_min_z_rot = c.to_max_z_rot = 0.0
            c.to_min_y_rot = -math.pi * factor
            c.to_max_y_rot = math.pi * factor
            c.mix_mode_rot = "REPLACE"


# Half joints: a short bone at the shoulder and hip joints that turns half as far as the limb. Skin around the joint
# blends through it, so a raised arm or a high kick bends the shoulder and hip round instead of folding them flat
# (plain linear skinning collapses there). The animation builders key them at half the limb's rotation.
HALF = (
    # name, limb, parent of both (no side for pelvis), parent-side weight groups
    ("upperarm_half", "upperarm", "clavicle", ("clavicle", "spine_03")),
    ("thigh_half", "thigh", "pelvis", ("pelvis", "spine_01")),
)
CENTRE_BONES = ("pelvis", "spine_01", "spine_02", "spine_03")


def _sided(name, s):
    return name if name in CENTRE_BONES else "%s_%s" % (name, s)


def add_half_joints(rig):
    eb = edit(rig)
    for name, limb, parent, _ in HALF:
        for s in "lr":
            c = eb["%s_%s" % (limb, s)]
            b = eb.new("%s_%s" % (name, s))
            b.head = c.head.copy()
            b.tail = c.head + (c.tail - c.head) * 0.25
            b.roll = c.roll
            b.parent = eb[_sided(parent, s)]
            b.use_connect = False
            b.use_deform = True
    obj_mode()


def half_constraints(rig):
    for name, limb, parent, _ in HALF:
        for s in "lr":
            pb = rig.pose.bones["%s_%s" % (name, s)]
            pb.rotation_mode = "QUATERNION"
            for c in list(pb.constraints):
                pb.constraints.remove(c)
            c = pb.constraints.new("COPY_ROTATION")
            c.name = "half_of_" + limb
            c.target = rig
            c.subtarget = "%s_%s" % (limb, s)
            c.target_space = "LOCAL"
            c.owner_space = "LOCAL"
            c.influence = 0.5


def split_half_weights(ob, rig, W=None):
    """Where skin blends between the trunk and a limb (both carry weight), a share of up to 70 % moves to the half
    joint, taken from both sides in proportion. Returns the new weight dict."""
    W = M.weights(ob) if W is None else W
    n = len(M.co(ob))
    twist = {t[1]: t[0] for t in TWIST}
    for name, limb, parent, trunk in HALF:
        for s in "lr":
            child = [g for g in ("%s_%s" % (limb, s), "%s_%s" % (twist.get(limb, ""), s)) if g in W]
            par = [g for g in dict.fromkeys(_sided(p, s) for p in trunk) if g in W]
            if not child or not par:
                continue
            wc = sum(W[g] for g in child)
            wp = sum(W[g] for g in par)
            share = np.minimum(0.7, 2.0 * np.minimum(wc, wp))
            tot = np.maximum(wc + wp, 1e-9)
            take_c, take_p = share * wc / tot, share * wp / tot
            for g in child:
                W[g] = W[g] - take_c * np.where(wc > 0, W[g] / np.maximum(wc, 1e-9), 0.0)
            for g in par:
                W[g] = W[g] - take_p * np.where(wp > 0, W[g] / np.maximum(wp, 1e-9), 0.0)
            hn = "%s_%s" % (name, s)
            W[hn] = W.get(hn, np.zeros(n)) + share
    return W


def bone_param(rig, bone, P):
    b = rig.data.bones[bone]
    h, t = np.array(b.head_local), np.array(b.tail_local)
    d = t - h
    return ((P - h) @ d) / (d @ d)


def split_twist_weights(ob, rig, W=None):
    """Moves part of upperarm/lowerarm/thigh weight onto the twist bones with a smooth ramp along
    the limb: shoulder and hip skin take the half-twist bone, the forearm's distal half the hand-driven
    one. Returns the new weight dict (also written to ob)."""
    W = M.weights(ob) if W is None else W
    V = M.co(ob)
    ramps = {
        "upperarm": lambda t: 1 - M.smoothstep(0.12, 0.62, t),
        "lowerarm": lambda t: M.smoothstep(0.25, 0.9, t),
        "thigh": lambda t: 1 - M.smoothstep(0.08, 0.55, t),
    }
    for name, parent, driver, factor, h, t in TWIST:
        for s in "lr":
            pb = "%s_%s" % (parent, s)
            tw = "%s_%s" % (name, s)
            if pb not in W:
                continue
            tt = bone_param(rig, pb, V)
            f = ramps[parent](tt)
            W[tw] = W.get(tw, np.zeros(len(V))) + W[pb] * f
            W[pb] = W[pb] * (1 - f)
    return W


# ----------------------------------------------------------------------------- secondary chains

def add_chain(rig, names, points, parent, roll_up=(0, 1, 0), connect=True, deform=True):
    """Bones along points (len(names)+1 points, armature space). Returns the bone names."""
    eb = edit(rig)
    prev = eb[parent] if parent else None
    for i, nm in enumerate(names):
        b = eb.new(nm)
        b.head = Vector(points[i])
        b.tail = Vector(points[i + 1])
        b.align_roll(Vector(roll_up))
        b.parent = prev
        b.use_connect = bool(connect and i > 0)
        b.use_deform = deform
        prev = b
    obj_mode()
    for nm in names:
        rig.pose.bones[nm].rotation_mode = "QUATERNION"
    return names


def add_helper(rig, name, parent, head, tail):
    eb = edit(rig)
    b = eb.new(name)
    b.head = Vector(head)
    b.tail = Vector(tail)
    b.parent = eb[parent]
    b.use_deform = False
    obj_mode()
    rig.pose.bones[name].rotation_mode = "QUATERNION"
    return name


def chain_weights(s, bounds, names, parent=None, root_blend=0.0, root_start=0.0):
    """Linear blend along a chain. s: per-vertex arc parameter (metres from chain root); bounds: arc
    positions of the bone joints (len(names)+1). Bones blend between their midpoints; the first
    `root_blend` metres blend in from `parent`."""
    s = np.asarray(s, float)
    mids = [(bounds[i] + bounds[i + 1]) * 0.5 for i in range(len(names))]
    W = {nm: np.zeros(len(s)) for nm in names}
    if len(names) == 1:
        W[names[0]][:] = 1
    else:
        for i, nm in enumerate(names):
            w = np.zeros(len(s))
            if i == 0:
                w = np.where(s <= mids[0], 1.0, w)
            else:
                a, b = mids[i - 1], mids[i]
                w = np.where((s > a) & (s <= b), (s - a) / (b - a), w)
            if i == len(names) - 1:
                w = np.where(s > mids[-1], 1.0, w)
            else:
                a, b = mids[i], mids[i + 1]
                w = np.where((s > a) & (s <= b), 1 - (s - a) / (b - a), w)
            W[nm] = w
    if parent and root_blend > 0:
        k = M.smoothstep(root_start, root_start + root_blend, s)
        for nm in names:
            W[nm] = W[nm] * k
        W[parent] = 1 - k
    return W


def damped_follow(rig, bone, helper, influence):
    pb = rig.pose.bones[bone]
    c = pb.constraints.new("DAMPED_TRACK")
    c.name = "follow_" + helper
    c.target = rig
    c.subtarget = helper
    c.track_axis = "TRACK_Y"
    c.influence = influence
    return c


# ----------------------------------------------------------------------------- reporting

CORE_CATEGORIES = ("core", "twist")


def bone_category(name):
    if name.startswith("helper_"):
        return "helper"
    for tw in TWIST:
        if name.startswith(tw[0]):
            return "twist"
    for pre in ("braid_", "strand_", "coat_"):
        if name.startswith(pre):
            return "secondary"
    return "core"


def bone_table(rig):
    out = []
    for b in rig.data.bones:
        mat = b.matrix_local
        out.append({
            "name": b.name,
            "parent": b.parent.name if b.parent else None,
            "category": bone_category(b.name),
            "deform": bool(b.use_deform),
            "exported": bool(b.use_deform),
            "head_cm": [round(x * 100, 3) for x in b.head_local],
            "tail_cm": [round(x * 100, 3) for x in b.tail_local],
            "length_cm": round(b.length * 100, 3),
            "x_axis": [round(x, 4) for x in mat.col[0][:3]],
            "constraints": [c.type + ":" + (getattr(c, "subtarget", "") or "")
                            for c in rig.pose.bones[b.name].constraints],
        })
    return out


def core_signature(rig):
    return [(b.name, b.parent.name if b.parent else None) for b in rig.data.bones
            if bone_category(b.name) in CORE_CATEGORIES]


def write_bones_json(rig, path, char, extra=None):
    table = bone_table(rig)
    doc = {
        "character": char,
        "armature_object": rig.name,
        "units": "Blender metres (positions below in cm, armature space, rest pose)",
        "rest_pose": "A-pose (MPFB/MakeHuman default): upper arms about 47 deg below horizontal, palms in",
        "facing": "Blender -Y (character's left is +X, up +Z). FBX written Z-up/identity; imports into UE "
                  "facing +Y like SK_Mannequin",
        "root_bone": "root",
        "bone_axis": "Y along the bone (Blender convention), FBX primary Y / secondary X",
        "core_bone_count": sum(1 for b in table if b["category"] in CORE_CATEGORIES),
        "secondary_chains": {},
        "bones": table,
    }
    chains = {}
    for b in table:
        if b["category"] == "secondary":
            key = b["name"].rsplit("_", 1)[0]
            chains.setdefault(key, []).append(b["name"])
    doc["secondary_chains"] = {k: {"bones": v, "parent": next(x["parent"] for x in table if x["name"] == v[0])}
                               for k, v in chains.items()}
    if extra:
        doc.update(extra)
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return doc
