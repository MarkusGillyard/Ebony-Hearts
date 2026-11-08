"""Deformation test poses (temporary keyframes): head-height roundhouse, deep stance, high guard,
extended punch, 60 degree torso twist, knee strike, back bend, deep crouch (heels down, ankles
dorsiflexed), teep (push kick, ankle and toes dorsiflexed), pointed-foot instep kick (plantarflexed)
and tiptoe (heels up, toes bent). Poses are built with world-space
rotations and an analytic two-bone IK; secondary chains (braids, strands, coat tails) are settled
by a small gravity-and-collision solver that stands in for in-engine physics.
The character faces -Y; its left is +X."""
import math

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

POSES = ("rest", "roundhouse", "stance", "guard", "punch", "twist", "knee", "backbend", "crouch", "teep",
         "kick_point", "tiptoe")


def upd():
    bpy.context.view_layer.update()


def reset(arm):
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    upd()


def head(arm, b):
    return np.array(arm.pose.bones[b].head)


def tail(arm, b):
    return np.array(arm.pose.bones[b].tail)


def rot(arm, b, axis, deg, pivot=None):
    """Rotates bone b (and so its children) about a world axis through its head (or pivot)."""
    upd()
    pb = arm.pose.bones[b]
    Mp = pb.matrix.copy()
    p = Vector(pivot) if pivot is not None else Mp.translation.copy()
    R = Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized())
    pb.matrix = Matrix.Translation(p) @ R @ Matrix.Translation(-p) @ Mp
    upd()


def aim(arm, b, target):
    upd()
    h, t = head(arm, b), tail(arm, b)
    cur = (t - h) / np.linalg.norm(t - h)
    des = np.asarray(target) - h
    des /= np.linalg.norm(des)
    ax = np.cross(cur, des)
    s = np.linalg.norm(ax)
    if s < 1e-7:
        return
    ang = math.degrees(math.atan2(s, float(cur @ des)))
    rot(arm, b, ax / s, ang)


def ik2(arm, upper, lower, target, pole):
    upd()
    A = head(arm, upper)
    la = np.linalg.norm(tail(arm, upper) - A)
    lb = np.linalg.norm(tail(arm, lower) - head(arm, lower))
    d = np.asarray(target, float) - A
    dist = float(np.clip(np.linalg.norm(d), 0.05, la + lb - 1e-4))
    dn = d / np.linalg.norm(d)
    ca = (la * la + dist * dist - lb * lb) / (2 * la * dist)
    sa = math.sqrt(max(0.0, 1 - ca * ca))
    p = np.asarray(pole, float)
    p = p - dn * (p @ dn)
    p /= max(np.linalg.norm(p), 1e-9)
    elbow = A + dn * la * ca + p * la * sa
    aim(arm, upper, elbow)
    aim(arm, lower, A + dn * dist)


def twist(arm, b, deg):
    upd()
    h, t = head(arm, b), tail(arm, b)
    rot(arm, b, t - h, deg)


def fist(arm, s, amount=1.0):
    """Curls the fingers into a fist (tips toward the palm)."""
    upd()
    hb = arm.pose.bones["hand_" + s]
    wrist = head(arm, "hand_" + s)
    kn = np.mean([head(arm, "%s_01_%s" % (f, s)) for f in ("index", "middle", "ring", "pinky")], 0)
    ax = (kn - wrist) / np.linalg.norm(kn - wrist)
    across = head(arm, "index_01_" + s) - head(arm, "pinky_01_" + s)
    n = np.cross(ax, across)
    n /= np.linalg.norm(n)
    tt = tail(arm, "thumb_03_" + s)
    if (tt - wrist) @ n < 0:
        n = -n                                   # n points to the palm side
    for f in ("index", "middle", "ring", "pinky"):
        for k, ang in ((1, 80), (2, 95), (3, 60)):
            b = "%s_%02d_%s" % (f, k, s)
            h, t = head(arm, b), tail(arm, b)
            d = (t - h) / np.linalg.norm(t - h)
            axis = np.cross(d, n)
            rot(arm, b, axis, ang * amount)
    for k, ang in ((2, 35), (3, 45)):
        b = "thumb_%02d_%s" % (k, s)
        h, t = head(arm, b), tail(arm, b)
        d = (t - h) / np.linalg.norm(t - h)
        rot(arm, b, np.cross(d, n), ang * amount)


def guard_arms(arm, eye_z, spread=0.075, fwd=0.17, up=0.0):
    for s, sg in (("l", 1), ("r", -1)):
        sh = head(arm, "upperarm_" + s)
        target = np.array([sg * spread, sh[1] - fwd, eye_z + up])
        # keep the target relative to the (possibly turned) chest
        ik2(arm, "upperarm_" + s, "lowerarm_" + s, target, np.array([sg * 0.3, -0.2, -1.0]))
        fist(arm, s)


def chest_frame(arm):
    upd()
    M3 = arm.pose.bones["spine_03"].matrix.to_3x3() @ arm.data.bones["spine_03"].matrix_local.to_3x3().inverted()
    return np.array(M3)


def guard_in_chest(arm, eye_z, spread=0.075, fwd=0.17, up=0.0):
    """High guard expressed in the chest's frame (follows torso twists/leans)."""
    R = chest_frame(arm)
    c = head(arm, "spine_03")
    rest_c = np.array(arm.data.bones["spine_03"].head_local)
    for s, sg in (("l", 1), ("r", -1)):
        rest_sh = np.array(arm.data.bones["upperarm_" + s].head_local)
        local = np.array([sg * spread, rest_sh[1] - fwd, eye_z + up]) - rest_c
        target = c + R @ local
        pole = R @ np.array([sg * 0.3, -0.2, -1.0])
        ik2(arm, "upperarm_" + s, "lowerarm_" + s, target, pole)
        fist(arm, s)


def plant_feet(arm, feet):
    for s, (target, pole) in feet.items():
        ik2(arm, "thigh_" + s, "calf_" + s, target, pole)


def rest_ankle(arm, s):
    return np.array(arm.data.bones["foot_" + s].head_local)


def rest_dir(arm, b):
    bb = arm.data.bones[b]
    d = np.array(bb.tail_local) - np.array(bb.head_local)
    return d / np.linalg.norm(d)


def ankle_axis(arm, s):
    """World axis about which a positive rotation of foot_<s> points the toes (plantarflexion)."""
    upd()
    shin_up = head(arm, "calf_" + s) - tail(arm, "calf_" + s)
    fd = tail(arm, "foot_" + s) - head(arm, "foot_" + s)
    a = np.cross(shin_up, fd)
    return a / np.linalg.norm(a)


def flex_foot(arm, s, ankle_deg, toe_deg=0.0):
    """ankle_deg > 0 plantarflexes (points), < 0 dorsiflexes; toe_deg > 0 curls the toes down."""
    ax = ankle_axis(arm, s)
    rot(arm, "foot_" + s, ax, ankle_deg)
    if toe_deg:
        rot(arm, "ball_" + s, ankle_axis(arm, s), toe_deg)


def flat_foot(arm, s, toe_flat=True):
    """Sole back to its rest orientation in the world (after IK moved the shin)."""
    h = head(arm, "foot_" + s)
    aim(arm, "foot_" + s, h + rest_dir(arm, "foot_" + s))
    if toe_flat:
        aim(arm, "ball_" + s, head(arm, "ball_" + s) + rest_dir(arm, "ball_" + s))


# ----------------------------------------------------------------------------- poses

def pose(arm, name, L):
    reset(arm)
    eye_z = L["eye_z"]
    if name == "rest":
        return
    if name == "roundhouse":
        al = rest_ankle(arm, "l")
        rot(arm, "pelvis", (0, 0, 1), 40)
        rot(arm, "pelvis", (0, 1, 0), 18)                      # hips tilt: right hip rises
        for b in ("spine_01", "spine_02", "spine_03"):
            rot(arm, b, (0, 1, 0), -11)                        # lean the torso away (to +X)
        plant_feet(arm, {"l": (al + np.array([0.03, 0.0, 0.0]), np.array([0.3, -1, 0]))})
        hip = head(arm, "thigh_r")
        down = tail(arm, "thigh_r") - hip
        down /= np.linalg.norm(down)
        kick = np.array([-0.55, -0.8, 0.0])
        kick /= np.linalg.norm(kick)
        ax = np.cross(down, kick)
        rot(arm, "thigh_r", ax, 100)
        aim(arm, "calf_r", head(arm, "calf_r") + (tail(arm, "thigh_r") - hip) / np.linalg.norm(tail(arm, "thigh_r") - hip) + np.array([0, 0, 0.05]))
        rot(arm, "foot_r", np.cross(tail(arm, "foot_r") - head(arm, "foot_r"), [0, 0, 1]), 40)
        guard_in_chest(arm, eye_z - 0.02)
        rot(arm, "neck_01", (0, 0, 1), -25)
        rot(arm, "head", (0, 1, 0), 12)
        return
    if name == "stance":
        drop = L["height"] * 0.11
        arm.pose.bones["pelvis"].matrix = Matrix.Translation((0, 0.02, -drop)) @ arm.pose.bones["pelvis"].matrix
        upd()
        rot(arm, "pelvis", (0, 0, 1), 28)
        rot(arm, "spine_01", (0, 0, 1), -8)
        rot(arm, "spine_02", (1, 0, 0), -6)
        sl = L["height"] * 0.21
        plant_feet(arm, {"l": (np.array([0.14, -sl, rest_ankle(arm, "l")[2]]), np.array([0.25, -1, 0.1])),
                         "r": (np.array([-0.2, sl * 0.95, rest_ankle(arm, "r")[2]]), np.array([-0.5, -1, 0.1]))})
        guard_in_chest(arm, eye_z - 0.05, fwd=0.2)
        rot(arm, "neck_01", (0, 0, 1), -18)
        return
    if name == "guard":
        guard_in_chest(arm, eye_z + 0.01, spread=0.07, fwd=0.15)
        return
    if name == "punch":
        rot(arm, "pelvis", (0, 0, 1), 20)
        rot(arm, "spine_02", (0, 0, 1), 12)
        rot(arm, "spine_03", (0, 0, 1), 10)
        plant_feet(arm, {s: (rest_ankle(arm, s), np.array([0, -1, 0])) for s in "lr"})
        R = chest_frame(arm)
        c = head(arm, "spine_03")
        rest_c = np.array(arm.data.bones["spine_03"].head_local)
        lsh = np.array(arm.data.bones["upperarm_l"].head_local)
        ik2(arm, "upperarm_l", "lowerarm_l", c + R @ (np.array([0.07, lsh[1] - 0.16, eye_z - 0.02]) - rest_c),
            R @ np.array([0.3, -0.2, -1.0]))
        fist(arm, "l")
        sh = head(arm, "upperarm_r")
        target = sh + np.array([0.13, -0.8, -0.01])
        ik2(arm, "upperarm_r", "lowerarm_r", target, np.array([-0.4, 0.2, -1.0]))
        fist(arm, "r")
        twist(arm, "hand_r", -80)
        rot(arm, "clavicle_r", (0, 0, 1), 8)
        return
    if name == "twist":
        for b in ("spine_01", "spine_02", "spine_03"):
            rot(arm, b, (0, 0, 1), 20)
        guard_in_chest(arm, eye_z, spread=0.075, fwd=0.17)
        rot(arm, "neck_01", (0, 0, 1), -30)
        return
    if name == "knee":
        rot(arm, "pelvis", (1, 0, 0), -12)
        al = rest_ankle(arm, "l")
        plant_feet(arm, {"l": (al + np.array([0, 0.03, 0.0]), np.array([0, -1, 0]))})
        rot(arm, "thigh_r", (1, 0, 0), -110)                   # -X turns the thigh forward (faces -Y)
        rot(arm, "calf_r", (1, 0, 0), 125)
        flex_foot(arm, "r", 30.0, 10.0)
        for b in ("spine_02", "spine_03"):
            rot(arm, b, (1, 0, 0), 9)
        for s, sg in (("l", 1), ("r", -1)):
            sh = head(arm, "upperarm_" + s)
            ik2(arm, "upperarm_" + s, "lowerarm_" + s, np.array([sg * 0.08, sh[1] - 0.42, eye_z - 0.04]),
                np.array([sg * 0.6, 0, -1.0]))
            fist(arm, s, 0.6)
        return
    if name == "backbend":
        arm.pose.bones["pelvis"].matrix = Matrix.Translation((0, -0.05, -0.04)) @ arm.pose.bones["pelvis"].matrix
        upd()
        rot(arm, "pelvis", (1, 0, 0), -8)
        for b in ("spine_01", "spine_02", "spine_03"):
            rot(arm, b, (1, 0, 0), -15)
        rot(arm, "neck_01", (1, 0, 0), -10)
        rot(arm, "head", (1, 0, 0), -10)
        plant_feet(arm, {s: (rest_ankle(arm, s), np.array([0, -1, 0])) for s in "lr"})
        for s, sg in (("l", 1), ("r", -1)):
            rot(arm, "upperarm_" + s, (0, 1, 0), -sg * 70)
            rot(arm, "upperarm_" + s, (1, 0, 0), -25)
            rot(arm, "lowerarm_" + s, (0, 1, 0), -sg * 15)
        return
    if name == "crouch":
        drop = 0.42
        arm.pose.bones["pelvis"].matrix = Matrix.Translation((0, 0.1, -drop)) @ arm.pose.bones["pelvis"].matrix
        upd()
        rot(arm, "pelvis", (1, 0, 0), 22)
        for b in ("spine_02", "spine_03"):
            rot(arm, b, (1, 0, 0), -6)
        for s, sg in (("l", 1), ("r", -1)):
            a = rest_ankle(arm, s)
            plant_feet(arm, {s: (a + np.array([sg * 0.05, 0.0, 0.0]), np.array([sg * 0.45, -1, 0.0]))})
            flat_foot(arm, s)
        guard_in_chest(arm, eye_z - 0.02, fwd=0.2)
        rot(arm, "neck_01", (1, 0, 0), -14)
        return
    if name == "teep":
        rot(arm, "pelvis", (1, 0, 0), -8)
        for b in ("spine_01", "spine_02", "spine_03"):
            rot(arm, b, (1, 0, 0), -6)
        al = rest_ankle(arm, "l")
        plant_feet(arm, {"l": (al + np.array([0, 0.05, 0.0]), np.array([0, -1, 0]))})
        flat_foot(arm, "l")
        hip = head(arm, "thigh_r")
        ll = np.linalg.norm(tail(arm, "thigh_r") - hip) + np.linalg.norm(tail(arm, "calf_r") - head(arm, "calf_r"))
        tgt = hip + np.array([-0.02, -0.92, 0.12]) / np.linalg.norm([-0.02, -0.92, 0.12]) * ll * 0.97
        ik2(arm, "thigh_r", "calf_r", tgt, np.array([0, -0.3, 1.0]))
        h = head(arm, "foot_r")
        aim(arm, "foot_r", h + np.array([0, -0.25, 1.0]))          # sole faces the target
        flex_foot(arm, "r", 0.0, -35.0)                              # toes pulled back
        guard_in_chest(arm, eye_z - 0.03, fwd=0.2)
        return
    if name == "kick_point":
        al = rest_ankle(arm, "l")
        rot(arm, "pelvis", (0, 0, 1), 15)
        plant_feet(arm, {"l": (al + np.array([0.02, 0.02, 0.0]), np.array([0.2, -1, 0]))})
        flat_foot(arm, "l")
        rot(arm, "thigh_r", (1, 0, 0), -80)
        rot(arm, "calf_r", (1, 0, 0), 25)
        flex_foot(arm, "r", 55.0, 20.0)
        for b in ("spine_02", "spine_03"):
            rot(arm, b, (1, 0, 0), -7)
        guard_in_chest(arm, eye_z - 0.03, fwd=0.2)
        return
    if name == "tiptoe":
        lift = math.radians(42.0)
        for s in "lr":
            a = rest_ankle(arm, s)
            b = np.array(arm.data.bones["ball_" + s].head_local)
            v = a - b
            ax = np.cross(rest_dir(arm, "foot_" + s), [0, 0, 1.0])
            ax /= np.linalg.norm(ax)
            Rm = np.array(Matrix.Rotation(lift, 3, Vector(ax)))
            a2 = b + Rm @ v
            if a2[2] < a[2]:
                Rm = np.array(Matrix.Rotation(-lift, 3, Vector(ax)))
                a2 = b + Rm @ v
            if s == "l":
                dz = a2[2] - a[2]
                arm.pose.bones["pelvis"].matrix = Matrix.Translation((0, 0.01, dz - 0.01)) @ arm.pose.bones["pelvis"].matrix
                upd()
            plant_feet(arm, {s: (a2, np.array([0, -1, 0]))})
            aim(arm, "foot_" + s, b)
            aim(arm, "ball_" + s, head(arm, "ball_" + s) + rest_dir(arm, "ball_" + s))
        for s, sg in (("l", 1), ("r", -1)):
            rot(arm, "upperarm_" + s, (0, 1, 0), -sg * 30)
        return
    raise KeyError(name)


# ----------------------------------------------------------------------------- secondary motion

def posed_bvh(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, off = [], [], 0
    for ob in objs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        Mw = ob.matrix_world
        verts.extend([Mw @ v.co for v in me.vertices])
        polys.extend([[i + off for i in p.vertices] for p in me.polygons])
        off += len(me.vertices)
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def hang_chain(arm, names, colliders, clear=0.02, gravity=(0, 0, -1), keep=0.25, samples=4):
    """Settles a chain: each free bone turns toward gravity (keeping `keep` of its current
    direction) and away from the posed colliders; among collision-free directions within 80 degrees
    the one closest to the desired direction wins, else the one with the most clearance."""
    bvh = posed_bvh(colliders)
    g = np.asarray(gravity, float)
    for nm in names:
        pb = arm.pose.bones[nm]
        if any(c.type == "DAMPED_TRACK" and c.influence > 0.99 for c in pb.constraints):
            continue
        upd()
        h, t = head(arm, nm), tail(arm, nm)
        L = np.linalg.norm(t - h)
        cur = (t - h) / L
        des = cur * keep + g * (1 - keep)
        des /= np.linalg.norm(des)
        o1 = np.cross(des, [1, 0, 0] if abs(des[0]) < 0.9 else [0, 1, 0])
        o1 /= np.linalg.norm(o1)
        o2 = np.cross(des, o1)
        best, best_clear = None, -1e9
        cands = [des]
        for ring in range(1, 17):
            a = math.radians(5 * ring)
            for k in range(12):
                b = 2 * math.pi * k / 12
                cands.append(des * math.cos(a) + (o1 * math.cos(b) + o2 * math.sin(b)) * math.sin(a))
        fallback = des
        for cand in cands:
            worst = 1e9
            for f in np.linspace(0.25, 1.0, samples):
                p = Vector(h + cand * L * f)
                loc, nrm, _, dist = bvh.find_nearest(p)
                if loc is None:
                    continue
                sd = dist if (p - loc).dot(nrm) >= 0 else -dist
                worst = min(worst, sd)
            if worst >= clear:
                best = cand
                break
            if worst > best_clear:
                best_clear, fallback = worst, cand
        if best is None:
            best = fallback
        aim(arm, nm, h + best * L)


def key_all(arm, frame):
    for pb in arm.pose.bones:
        pb.keyframe_insert("location", frame=frame)
        pb.keyframe_insert("rotation_quaternion", frame=frame)


def penetration(garment, body, tol=0.004):
    """Garment vertices inside the posed body: boolean mask over the garment's vertices."""
    bvh = posed_bvh([body])
    dg = bpy.context.evaluated_depsgraph_get()
    ev = garment.evaluated_get(dg)
    me = ev.to_mesh()
    Mw = garment.matrix_world
    n = len(me.vertices)
    mask = np.zeros(n, bool)
    for v in me.vertices:
        p = Mw @ v.co
        loc, nrm, _, d = bvh.find_nearest(p, 0.08)
        if loc is not None and (p - loc).dot(nrm) < -tol:
            mask[v.index] = True
    ev.to_mesh_clear()
    return mask


def local_turn_deg(arm, name):
    """Evaluated (constraint-inclusive) rotation of a bone relative to its parent, in degrees."""
    upd()
    pb = arm.pose.bones[name]
    par = pb.parent
    rest_rel = par.bone.matrix_local.inverted() @ pb.bone.matrix_local
    pose_rel = par.matrix.inverted() @ pb.matrix
    return math.degrees((rest_rel.inverted() @ pose_rel).to_quaternion().angle)
