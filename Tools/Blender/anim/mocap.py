"""Retargets CMU motion capture onto the game_engine rig and fits it to the combat data.

Retargeting copies each source bone's world rotation change from rest onto the mapped target bone. The target's rest
pose (MPFB A-pose) is first rotated bone by bone onto the source's T-pose directions, so a source rotation moves the
target bone along the same world direction. The pelvis also takes the source root's position, scaled by leg length.
Twist bones take their share of the limb's twist, fingers hold a fist, and the hair is simulated afterwards.

Clip timing is a piecewise-linear map from target frames (60 fps) to source time, anchored on the move's data (start,
first active frame, end), so contact lands on the active frame whatever the performer's speed.
"""
import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector

import aim
import animlib as A
import bvh
import cmu

SRC_FPS = 120.0

# target bone: (source bone whose world rotation it takes, source bones whose combined rest direction it aligns to)
MAP = {
    "pelvis": ("root", None),
    "spine_01": ("lowerback", ["lowerback"]),
    "spine_02": ("upperback", ["upperback"]),
    "spine_03": ("thorax", ["thorax"]),
    "neck_01": ("lowerneck", ["lowerneck", "upperneck"]),
    "head": ("head", ["head"]),
}
for _s in ("l", "r"):
    MAP.update({
        f"clavicle_{_s}": (f"{_s}clavicle", [f"{_s}clavicle"]),
        f"upperarm_{_s}": (f"{_s}humerus", [f"{_s}humerus"]),
        f"lowerarm_{_s}": (f"{_s}radius", [f"{_s}radius", f"{_s}wrist"]),
        f"hand_{_s}": (f"{_s}hand", [f"{_s}hand"]),
        f"thigh_{_s}": (f"{_s}femur", [f"{_s}femur"]),
        f"calf_{_s}": (f"{_s}tibia", [f"{_s}tibia"]),
        f"foot_{_s}": (f"{_s}foot", [f"{_s}foot"]),
        f"ball_{_s}": (f"{_s}toes", [f"{_s}toes"]),
    })

# CMU world (Y up, right-handed) to Blender armature space (Z up), before the clip's heading turn.
TO_BLENDER = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
MIRROR = Matrix(((-1, 0, 0), (0, 1, 0), (0, 0, 1)))


def swap_side(name):
    if name.startswith("l") and name[1:] in ("clavicle", "humerus", "radius", "wrist", "hand", "fingers", "thumb",
                                              "hipjoint", "femur", "tibia", "foot", "toes"):
        return "r" + name[1:]
    if name.startswith("r") and name[1:] in ("clavicle", "humerus", "radius", "wrist", "hand", "fingers", "thumb",
                                              "hipjoint", "femur", "tibia", "foot", "toes"):
        return "l" + name[1:]
    return name


def twist_angle(q, axis=Vector((0, 1, 0))):
    """Signed twist of a local rotation about the bone axis (swing-twist decomposition)."""
    v = Vector((q.x, q.y, q.z))
    p = axis * v.dot(axis)
    t = Quaternion((q.w, p.x, p.y, p.z))
    if t.magnitude < 1e-9:
        return 0.0
    t.normalize()
    ang = 2.0 * math.atan2(Vector((t.x, t.y, t.z)).dot(axis), t.w)
    return (ang + math.pi) % (2 * math.pi) - math.pi


class Source:
    """One CMU clip in Blender space: per-frame world rotations (quaternions) and root positions."""

    def __init__(self, asf, amc, heading_deg=0.0, mirror=False):
        self.skel = cmu.Skeleton(asf)
        frames = cmu.read_amc(amc)
        turn = Matrix.Rotation(math.radians(heading_deg), 3, "Z")
        S = turn @ TO_BLENDER
        if mirror:
            S = MIRROR @ S
        self.mirror = mirror
        Sinv = S.inverted()
        self.rot, self.pos, self.ends = [], [], []
        for fr in frames:
            rot, start, end = cmu.pose(self.skel, fr)
            q, e = {}, {}
            for name, m in rot.items():
                tgt = swap_side(name) if mirror else name
                q[tgt] = (S @ m @ Sinv).to_quaternion()
                e[tgt] = S @ end[name]
            self.rot.append(q)
            self.pos.append(S @ start["root"])
            self.ends.append(e)
        rest = self.skel.rest_positions()
        self.rest_dir = {}
        for name, (a, b) in rest.items():
            tgt = swap_side(name) if mirror else name
            self.rest_dir[tgt] = (S @ (b - a), S @ a, S @ b)
        self.count = len(frames)
        self.leg = sum(self.skel.bones[n].length for n in ("lfemur", "ltibia"))
        self.floor = min(min(e[f"{s}toes"].z for s in ("l", "r")) for e in self.ends)

    def sample(self, t):
        """Rotations and root position at source frame t (float, 0-based), interpolated."""
        t = max(0.0, min(self.count - 1.0, t))
        i = int(math.floor(t))
        j = min(i + 1, self.count - 1)
        a = t - i
        q = {n: self.rot[i][n].slerp(self.rot[j][n], a) for n in self.rot[i]}
        p = self.pos[i].lerp(self.pos[j], a)
        return q, p

    def chain_dir(self, names):
        d = Vector((0, 0, 0))
        for n in names:
            d += self.rest_dir[n][0]
        return d.normalized()


class BvhSource:
    """A BVH clip (e.g. ACCAD) seen through the position-aimed retarget: sample() gives target-bone world rotations
    directly, so Retarget uses them as they are."""
    target_space = True

    NEUTRAL = "Male2_A1_Stand.bvh"   # relaxed standing take beside the clips, for aim.CALIBRATED

    def __init__(self, path, arm, heading_deg=0.0, mirror=False):
        self.clip = bvh.BVH(path, heading_deg=heading_deg, mirror=mirror)
        # The neutral standing take is read unturned: the clip's heading then turns every bone, the calibrated ones too.
        stand = bvh.BVH(os.path.join(os.path.dirname(path), self.NEUTRAL), mirror=mirror)
        neutral, neutral_rot = stand.pose(stand.count // 2)
        neutral_rot["SpineLow"] = neutral_rot["ToSpine"]
        self.aim = aim.AimRetarget(arm, neutral)
        self.aim.carry(neutral, neutral_rot)
        self.fps = self.clip.fps
        self.count = self.clip.count
        poses = [self.clip.pose(k) for k in range(self.count)]
        self.points = [p for p, _ in poses]
        self.pos = [p["Hips"].copy() for p in self.points]
        p0 = self.points[0]
        self.leg = ((p0["LeftLeg"] - p0["LeftUpLeg"]).length + (p0["LeftFoot"] - p0["LeftLeg"]).length)
        self.floor = min(min(p[f"{s}ToeBase.end"].z for s in ("Left", "Right")) for p in self.points)
        self.rot = []
        for p, r in poses:
            r["SpineLow"] = r["ToSpine"]
            self.rot.append(self.aim.carried(r, p))

    def sample(self, t):
        t = max(0.0, min(self.count - 1.0, t))
        i = int(math.floor(t))
        j = min(i + 1, self.count - 1)
        a = t - i
        q = {}
        for n, qa in self.rot[i].items():
            qb = self.rot[j][n]
            if qa.dot(qb) < 0:
                qb = -qb
            q[n] = qa.slerp(qb, a)
        return q, self.pos[i].lerp(self.pos[j], a)

    def point(self, t, name):
        t = max(0.0, min(self.count - 1.0, t))
        i = int(math.floor(t))
        j = min(i + 1, self.count - 1)
        return self.points[i][name].lerp(self.points[j][name], t - i)


# Mixamo joints named as the BVH joints the position-aimed retarget (aim.RULES) expects. Mixamo's spine has three
# bones; its middle and chest joints stand in for the BVH Spine and Spine1.
MIXAMO_JOINTS = {"Hips": "Hips", "Spine": "Spine1", "Spine1": "Spine2", "Neck": "Neck", "Head": "Head",
                 "Head.end": "HeadTop_End"}
for _S in ("Left", "Right"):
    MIXAMO_JOINTS.update({f"{_S}Shoulder": f"{_S}Shoulder", f"{_S}Arm": f"{_S}Arm", f"{_S}ForeArm": f"{_S}ForeArm",
                          f"{_S}Hand": f"{_S}Hand", f"{_S}Hand.end": f"{_S}HandMiddle1", f"{_S}UpLeg": f"{_S}UpLeg",
                          f"{_S}Leg": f"{_S}Leg", f"{_S}Foot": f"{_S}Foot", f"{_S}ToeBase": f"{_S}ToeBase",
                          f"{_S}ToeBase.end": f"{_S}Toe_End"})


MIXAMO_ROT = {k: v for k, v in MIXAMO_JOINTS.items() if not k.endswith(".end")}
MIXAMO_ROT["SpineLow"] = "Spine"


def fbx_pose(path, heading_deg=0.0, mirror=False):
    """Every frame of a Mixamo FBX as (joint positions, joint world rotations): positions in Blender metres (facing
    -Y, left +X), rotations as 3x3 matrices keyed like the positions (plus "SpineLow"). Like bvh.BVH.pose, a mirrored
    rotation is the mirror times the rotation, so only products R_a @ R_b.inverted() are meaningful. Read by importing
    the file into the open scene and removing it again; the scene's frame rate and range are left as they were."""
    scene = bpy.context.scene
    keep = (scene.render.fps, scene.render.fps_base, scene.frame_start, scene.frame_end, scene.frame_current)
    before = set(bpy.data.objects)
    actions_before = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False)
    new = [o for o in bpy.data.objects if o not in before]
    src = next(o for o in new if o.type == "ARMATURE")
    f0, f1 = (int(round(v)) for v in src.animation_data.action.frame_range)
    turn = Matrix.Rotation(math.radians(heading_deg), 4, "Z")
    space = (MIRROR if mirror else Matrix.Identity(3)) @ turn.to_3x3()
    frames = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        mw = src.matrix_world
        pts, rots = {}, {}
        for name, bone in MIXAMO_JOINTS.items():
            pb = src.pose.bones.get("mixamorig:" + bone)
            if pb is None:
                continue
            pts[name] = space @ (mw @ pb.head)
        for name, bone in MIXAMO_ROT.items():
            pb = src.pose.bones.get("mixamorig:" + bone)
            if pb is not None:
                rots[name] = space @ (mw @ pb.matrix).to_3x3().normalized()
        if mirror:
            def swap(n):
                return n.replace("Left", "@").replace("Right", "Left").replace("@", "Right")
            pts = {swap(n): v for n, v in pts.items()}
            rots = {swap(n): m for n, m in rots.items()}
        frames.append((pts, rots))
    for o in new:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and data.users == 0:
            (bpy.data.armatures if isinstance(data, bpy.types.Armature) else bpy.data.meshes).remove(data)
    for a in set(bpy.data.actions) - actions_before:
        bpy.data.actions.remove(a)
    scene.render.fps, scene.render.fps_base, scene.frame_start, scene.frame_end = keep[:4]
    scene.frame_set(keep[4])
    return frames


class FbxSource(BvhSource):
    """A Mixamo FBX clip through the position-aimed retarget (same interface as BvhSource). Mixamo exports at 30 fps."""
    NEUTRAL = "Rig_XBot_TPose.fbx"

    def __init__(self, path, arm, heading_deg=0.0, mirror=False):
        poses = fbx_pose(path, heading_deg, mirror)
        # The T-pose is read unturned: the clip's heading then turns every bone, the calibrated ones too.
        neutral, neutral_rot = fbx_pose(os.path.join(os.path.dirname(path), self.NEUTRAL), 0.0, mirror)[0]
        self.aim = aim.AimRetarget(arm, neutral)
        self.aim.carry(neutral, neutral_rot)
        self.fps = 30.0
        self.points = [p for p, _ in poses]
        self.count = len(self.points)
        self.pos = [p["Hips"].copy() for p in self.points]
        p0 = self.points[0]
        self.leg = ((p0["LeftLeg"] - p0["LeftUpLeg"]).length + (p0["LeftFoot"] - p0["LeftLeg"]).length)
        self.floor = min(min(p[f"{s}ToeBase.end"].z for s in ("Left", "Right")) for p in self.points)
        self.rot = [self.aim.carried(r, p) for p, r in poses]


class Retarget:
    def __init__(self, arm, src):
        self.arm = arm
        self.src = src
        self.bones = arm.data.bones
        self.pb = arm.pose.bones
        for pb in self.pb:
            pb.rotation_mode = "QUATERNION"
        self.rest = {b.name: b.matrix_local.copy() for b in self.bones}
        self.order = []
        stack = [b for b in self.bones if b.parent is None]
        while stack:
            b = stack.pop(0)
            self.order.append(b.name)
            stack.extend(b.children)
        # Source rotations per target bone: CMU gives source-bone rotation changes from its T-pose, applied to the
        # target rest turned onto the T-pose directions; a BVH source gives the target bones' world rotations directly.
        self.aligned = {}
        self.src_key = {}
        if getattr(src, "target_space", False):
            for tgt in src.aim.correction:
                self.aligned[tgt] = Quaternion()
                self.src_key[tgt] = tgt
        for tgt, (srcb, chain) in ({} if self.src_key else MAP).items():
            if tgt not in self.rest:
                continue
            rq = self.rest[tgt].to_quaternion()
            if chain:
                b = self.bones[tgt]
                dt = (b.tail_local - b.head_local).normalized()
                ds = src.chain_dir(chain)
                rq = dt.rotation_difference(ds) @ rq
            self.aligned[tgt] = rq
            self.src_key[tgt] = srcb
        tgt_leg = sum((self.bones[n].tail_local - self.bones[n].head_local).length for n in ("thigh_l", "calf_l"))
        self.scale = tgt_leg / src.leg
        self.pelvis_rest = self.rest["pelvis"].translation.copy()
        self.rel = {}
        for name in self.order:
            b = self.bones[name]
            self.rel[name] = self.rest[b.parent.name].inverted() @ self.rest[name] if b.parent else self.rest[name].copy()

    def fk(self, out):
        """World (armature-space) matrices of a local pose."""
        world = {}
        for name in self.order:
            loc, q = out[name]
            basis = Matrix.Translation(loc) @ q.to_matrix().to_4x4()
            b = self.bones[name]
            world[name] = (world[b.parent.name] @ self.rel[name] if b.parent else self.rel[name]) @ basis
        return world

    def shift_pelvis(self, out, delta):
        """Moves the pelvis by `delta` in armature space (its local translation is in the bone's own rest frame)."""
        loc, q = out["pelvis"]
        frame = self.rel["root"] @ self.rel["pelvis"]
        m = frame @ Matrix.Translation(loc) @ q.to_matrix().to_4x4()
        m.translation = m.translation - delta
        nloc, nq, _ = (frame.inverted() @ m).decompose()
        out["pelvis"] = (nloc, nq)

    def set_world(self, out, world, name, m):
        """Writes bone `name` so its world matrix becomes m (children keep their local transforms)."""
        b = self.bones[name]
        basis = (world[b.parent.name] @ self.rel[name]).inverted() @ m
        loc, q, _ = basis.decompose()
        out[name] = (loc, q)
        world[name] = m

    def two_bone_ik(self, out, world, upper, lower, end, target_pos, pole=None, end_rot=None):
        """Moves `end`'s head to target_pos by turning `upper` and `lower`. The middle joint stays in the plane of its
        current bend, or bends toward `pole` (a world direction) if given. `end` keeps its world orientation
        (or takes end_rot, a 3x3 world rotation)."""
        root = world[upper].translation
        mid0 = world[lower].translation
        end0 = world[end].translation
        end_m = end_rot if end_rot is not None else world[end].to_3x3()
        a = (mid0 - root).length
        b = (end0 - mid0).length
        to = target_pos - root
        d = max(abs(a - b) + 1e-4, min(a + b - 1e-4, to.length))
        u = to.normalized()
        bend = pole if pole is not None else (mid0 - root)
        w = bend - u * bend.dot(u)
        if w.length < 1e-6:
            w = Vector((0, -1, 0)) - u * Vector((0, -1, 0)).dot(u)
        w.normalize()
        cos_a = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
        mid = root + (u * cos_a + w * math.sqrt(max(0.0, 1 - cos_a * cos_a))) * a
        reach = root + u * d
        r1 = (mid0 - root).rotation_difference(mid - root)
        self.set_world(out, world, upper, Matrix.Translation(root) @ (r1.to_matrix() @ world[upper].to_3x3()).to_4x4())
        world[lower] = world[upper] @ self.rel[lower] @ (Matrix.Translation(out[lower][0]) @ out[lower][1].to_matrix().to_4x4())
        m_now = world[lower].translation
        r2 = (world[lower].to_3x3() @ Vector((0, 1, 0))).rotation_difference(reach - m_now)
        self.set_world(out, world, lower, Matrix.Translation(m_now) @ (r2.to_matrix() @ world[lower].to_3x3()).to_4x4())
        world[end] = world[lower] @ self.rel[end] @ (Matrix.Translation(out[end][0]) @ out[end][1].to_matrix().to_4x4())
        self.set_world(out, world, end, Matrix.Translation(world[end].translation) @ end_m.to_4x4())

    def leg_ik(self, out, world, side, ankle, pole=None, foot_rot=None):
        """Places the ankle, keeping the knee in its captured plane (or toward `pole`) and the foot's orientation."""
        th = f"thigh_{side}"
        self.two_bone_ik(out, world, th, f"calf_{side}", f"foot_{side}", ankle, pole, foot_rot)
        tw = f"thigh_twist_01_{side}"
        if tw in out:
            out[tw] = (out[tw][0], Quaternion((0, 1, 0), twist_angle(out[th][1]) * -0.5))

    def arm_ik(self, out, world, side, wrist, pole=None, hand_rot=None):
        """Places the wrist, keeping the elbow in its captured plane (or toward `pole`) and the hand's orientation."""
        ua, la, hd = f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"
        self.two_bone_ik(out, world, ua, la, hd, wrist, pole, hand_rot)
        for twist, driver, factor in (("upperarm_twist_01", ua, -0.5), ("lowerarm_twist_01", hd, 0.5)):
            tn = f"{twist}_{side}"
            if tn in out:
                out[tn] = (out[tn][0], Quaternion((0, 1, 0), twist_angle(out[driver][1]) * factor))

    def local_pose(self, q_src, root_pos, root_offset):
        """Target pose for one sample: {bone: (location, quaternion)} in pose-bone local space."""
        world = {}
        out = {}
        for name in self.order:
            b = self.bones[name]
            rest = self.rest[name]
            if b.parent is None:
                world[name] = rest.copy()
                out[name] = (Vector((0, 0, 0)), Quaternion())
                continue
            prest = self.rest[b.parent.name]
            pworld = world[b.parent.name]
            rel = prest.inverted() @ rest
            head = (pworld @ rel).translation
            if name in self.aligned:
                q = q_src[self.src_key[name]] @ self.aligned[name]
                if name == "pelvis":
                    head = Vector((root_pos.x, root_pos.y, 0.0)) * self.scale + root_offset
                    head.z = (root_pos.z - self.src.floor) * self.scale + root_offset.z
                m = Matrix.Translation(head) @ q.to_matrix().to_4x4()
            else:
                m = pworld @ rel
            world[name] = m
            basis = (pworld @ rel).inverted() @ m
            loc, rq, _ = basis.decompose()
            out[name] = (loc, rq)
        # Twist bones share their limb's twist so forearms and upper arms don't pinch.
        for side in ("l", "r"):
            for twist, driver, factor in (("upperarm_twist_01", "upperarm", -0.5), ("lowerarm_twist_01", "hand", 0.5),
                                          ("thigh_twist_01", "thigh", -0.5)):
                tn, dn = f"{twist}_{side}", f"{driver}_{side}"
                if tn in out and dn in out:
                    ang = twist_angle(out[dn][1]) * factor
                    out[tn] = (out[tn][0], Quaternion((0, 1, 0), ang))
        return out


def plant_feet(rt, poses, sim, cap, loop, speed=0.0055, lift=0.045, debug=False, steps=None, step_lift=0.05):
    """Pins each foot where the performer kept it planted, so the gap between the captured travel and the
    simulation's travel goes into the steps instead of sliding the feet.

    steps: {side: [first, last]} (1-based frames) for a move the game carries forward while the performer stays on
    the spot: that foot steps (lifted up to step_lift metres) over those frames and lands one travel ahead, so the
    legs don't trail the travel. [first, last, "body"] lands it where the body puts it instead, for a foot the
    performer slid back into stance.

    poses: local poses (anim space, the actor's root at the origin). sim[i]: actor travel vector at frame i (i in 0..n,
    n = one past the end). cap[i]: captured pelvis travel (scaled), same indexing. Loops are solved over three unrolled
    cycles and the middle one is kept, so the result repeats seamlessly."""
    n = len(poses)
    worlds = [rt.fk(p) for p in poses]
    cycles = 3 if loop else 1
    ds, dc = sim[n] - sim[0], cap[n] - cap[0]
    N = cycles * n
    for side in ("l", "r"):
        ft = f"foot_{side}"
        corr, acap, bcap, s_u = [], [], [], []
        for j in range(N):
            i, k = j % n, j // n
            s = sim[i] + ds * k
            c = cap[i] + dc * k
            co = worlds[i]["pelvis"].translation + s - c
            co.z = 0.0
            corr.append(co)
            acap.append(worlds[i][ft].translation + s - co)
            # Fighters stay on the balls of their feet, so contact is judged at the ball, not the bobbing ankle.
            bcap.append(worlds[i][f"ball_{side}"].translation + s - co)
            s_u.append(s)
        floor = min(b.z for b in bcap)
        planted = []
        for j in range(N):
            v = max((bcap[min(N - 1, j + 1)] - bcap[j]).xy.length, (bcap[j] - bcap[max(0, j - 1)]).xy.length)
            forced = steps and side in steps and not loop and steps[side][0] <= j + 1 <= steps[side][1]
            planted.append(v < speed and bcap[j].z - floor < lift and not forced)
            if debug and j < n + (n if loop else 0) and j >= (n if loop else 0):
                print(f"    {side} f{j % n + 1:3d} ball z={(bcap[j].z - floor) * 100:5.1f}cm v={v * 6000:5.1f}cm/s {'PLANT' if planted[-1] else ''}")
        plants = []
        j = 0
        while j < N:
            if planted[j]:
                s0 = j
                while j < N and planted[j]:
                    j += 1
                if j - s0 >= 2:
                    plants.append((s0, j - 1))
            else:
                j += 1
        off = list(corr)
        for s0, e0 in plants:
            for j in range(s0, e0 + 1):
                off[j] = corr[s0]
        if steps and side in steps and not loop and steps[side][2:] != ["body"]:
            # The forced step lands the foot ahead of where it left by the actor's whole travel, so once the travel
            # ends it is back on its spot under the fighter.
            a0, b0 = steps[side][0] - 1, steps[side][1] - 1
            before = [p for p in plants if p[1] < a0]
            after = [p for p in plants if p[0] > b0]
            if after:
                left = before[-1][1] if before else 0
                land = acap[left] + off[left] + ds - acap[after[0][0]]
                land.z = 0.0
                for j in range(after[0][0], after[0][1] + 1):
                    off[j] = land
        bounds = [(-1, None)] + plants + [(N, None)]
        for (ps, pe), (ns, ne) in zip(bounds, bounds[1:]):
            a = pe if pe is not None else ps
            if ns - a <= 1:
                continue
            o_a = off[a] if a >= 0 else corr[0]
            o_b = off[ns] if ns < N else corr[N - 1]
            for j in range(max(0, a + 1), min(N, ns)):
                t = (j - a) / (ns - a)
                off[j] = o_a.lerp(o_b, t * t * (3 - 2 * t))
        base = n if loop else 0
        for i in range(n):
            j = base + i
            target = acap[j] + off[j] - s_u[j]
            if steps and side in steps and not loop:
                a, b = steps[side][:2]
                if a <= i + 1 <= b:
                    target.z += step_lift * math.sin(math.pi * (i + 1 - a + 0.5) / (b - a + 1))
            rt.leg_ik(poses[i], worlds[i], side, target)
        print(f"  feet {side}: {len(plants)} plants over {N} frames (loop={loop})")


def char_space(f, l, u):
    """Character space (f toward the opponent, l the character's left, u up) to armature space."""
    return Vector((l, -f, u))


def line_yaw(v):
    """Yaw (degrees, toward the character's left) of a left-pointing line such as the hips or the shoulders."""
    return math.degrees(math.atan2(v.y, v.x))


def turn_about(m, pivot, degrees):
    r = Matrix.Rotation(math.radians(degrees), 4, "Z")
    return Matrix.Translation(pivot) @ r @ Matrix.Translation(-pivot) @ m


def apply_stance(rt, poses, st, k, anchor="mean", hands=True):
    """Puts a clip onto a designed stance while keeping its captured motion.

    The clip's average pelvis position, hip and chest turn, foot and hand positions are moved to the stance's values;
    each frame's movement around those averages is kept (scaled by st['bounce'], st['sway'], st['hand_motion']). So
    the rhythm, weight shifts and micro-motion come from the capture, and the shape comes from the stance.
    anchor "start" measures movement from the first frame instead (one-shot moves start in the stance and keep their
    captured steps); hands=False leaves the arms as captured (strikes), and a list of sides ("l", "r") holds only those
    hands at the guard (the hand that is not striking keeps covering the face).
    Stance values use the scripted poses' character space (metres for a 1.75 m body, scaled by k):
      pelvis (f, l, u) offset from the rest pelvis; pelvis_yaw and chest_yaw in degrees toward the character's left
      (an orthodox stance is negative); foot_l / foot_r (f, l) ankle positions on the floor; hand_l / hand_r (f, l, u)
      wrist positions; optional elbow_l / elbow_r (f, l, u) elbow directions; foot_l_yaw / foot_r_yaw toe directions.
    """
    n = len(poses)
    worlds = [rt.fk(p) for p in poses]
    pel_rest = rt.rest["pelvis"].translation.copy()
    # Foot heights as captured, measured before the pelvis moves to the stance height: each ankle keeps its height
    # above the capture's lowest ankle, put on the target's own planted ankle height. (Measured after the move, any
    # difference between the performer's and the stance's hip height would lift the feet off the floor or sink them.)
    cap_ank = {s: [w[f"foot_{s}"].translation.z for w in worlds] for s in ("l", "r")}
    ank_floor = min(min(v) for v in cap_ank.values())

    def mean(vals):
        if anchor == "start":
            return vals[0].copy()
        return sum(vals, Vector((0, 0, 0))) / len(vals)

    def mean_f(vals):
        return vals[0] if anchor == "start" else sum(vals) / len(vals)

    # 1. Pelvis: stance height and position, captured bounce and sway around it.
    pel = [w["pelvis"].translation.copy() for w in worlds]
    pmean = mean(pel)
    want = pel_rest + char_space(*st["pelvis"]) * k
    rock = st.get("rock") if anchor == "mean" else None

    def phase(i):
        return 2.0 * math.pi * rock["cycles"] * i / n

    for i in range(n):
        dev = pel[i] - pmean
        target = want + Vector((dev.x * st.get("sway", 1.0), dev.y * st.get("sway", 1.0), dev.z * st.get("bounce", 1.0)))
        if rock:
            # Muay Thai rock: weight rolls forward and back, with a small dip as each leg takes it.
            ph = phase(i)
            target += char_space(rock["fore"] * math.sin(ph), 0.0, 0.0) * k
            target.z -= rock["dip"] * k * 0.5 * (1.0 - math.cos(2.0 * ph))
        rt.shift_pelvis(poses[i], pel[i] - target)
    # 2. Turn: hips to the stance's angle, the chest's extra turn spread up the spine.
    worlds = [rt.fk(p) for p in poses]
    hip_yaw = mean_f([line_yaw(w["thigh_l"].translation - w["thigh_r"].translation) for w in worlds])
    d_pel = st.get("pelvis_yaw", hip_yaw) - hip_yaw
    for i in range(n):
        w = worlds[i]
        rt.set_world(poses[i], w, "pelvis", turn_about(w["pelvis"], w["pelvis"].translation, d_pel))
    worlds = [rt.fk(p) for p in poses]
    chest_yaw = mean_f([line_yaw(w["upperarm_l"].translation - w["upperarm_r"].translation) for w in worlds])
    d_chest = st.get("chest_yaw", chest_yaw) - chest_yaw
    for i in range(n):
        for name, share in (("spine_01", 0.3), ("spine_02", 0.3), ("spine_03", 0.4)):
            w = rt.fk(poses[i])
            rt.set_world(poses[i], w, name, turn_about(w[name], w[name].translation, d_chest * share))
    # 2b. Posture: torso lean and head angle, measured in the vertical plane toward the opponent (positive = forward).
    forward = Vector((0, -1, 0))
    lateral = Vector((1, 0, 0))

    def lean(v):
        return math.degrees(math.atan2(v.dot(forward), v.z))

    def tilt(name, w, deg, pivot):
        r = Matrix.Rotation(math.radians(deg), 4, lateral)
        return Matrix.Translation(pivot) @ r @ Matrix.Translation(-pivot) @ w[name]

    if "lean" in st:
        worlds = [rt.fk(p) for p in poses]
        cap = mean_f([lean(w["neck_01"].translation - w["pelvis"].translation) for w in worlds])
        d = st["lean"] - cap
        for i in range(n):
            for name, share in (("spine_01", 0.3), ("spine_02", 0.3), ("spine_03", 0.4)):
                w = rt.fk(poses[i])
                rt.set_world(poses[i], w, name, tilt(name, w, d * share, w[name].translation))
    if "head_pitch" in st or "head_yaw" in st:
        worlds = [rt.fk(p) for p in poses]
        rest_head = rt.rest["head"].to_3x3()
        face_local = rest_head.inverted() @ forward   # the head axis that faces the opponent at rest
        d_pitch = 0.0
        d_yaw = 0.0
        if "head_pitch" in st:
            d_pitch = st["head_pitch"] - mean_f([lean(w["head"].to_3x3() @ Vector((0, 1, 0))) for w in worlds])
        if "head_yaw" in st:
            faces = [w["head"].to_3x3() @ face_local for w in worlds]
            d_yaw = st["head_yaw"] - mean_f([math.degrees(math.atan2(f.x, -f.y)) for f in faces])
        for i in range(n):
            for name, share in (("neck_01", 0.4), ("head", 0.6)):
                w = rt.fk(poses[i])
                m = tilt(name, w, d_pitch * share, w[name].translation)
                m = turn_about(m, w[name].translation, d_yaw * share)
                rt.set_world(poses[i], w, name, m)
    # 2c. Shoulders: each collarbone's average slope (degrees above horizontal) set to the stance's; captured shrugs
    # and shoulder rolls kept around it. A raised collarbone hides the neck, so the guard's shrug is designed, not copied.
    if "clavicle" in st:
        def slope(w, side):
            d = w[f"upperarm_{side}"].translation - w[f"clavicle_{side}"].translation
            return math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
        worlds = [rt.fk(p) for p in poses]
        for side in ("l", "r"):
            delta = st["clavicle"] - mean_f([slope(w, side) for w in worlds])
            for i in range(n):
                w = rt.fk(poses[i])
                c = w[f"clavicle_{side}"]
                d = w[f"upperarm_{side}"].translation - c.translation
                axis = Vector((d.x, d.y, 0.0)).cross(Vector((0.0, 0.0, 1.0)))
                if axis.length < 1e-6:
                    continue
                r = Matrix.Rotation(math.radians(delta), 4, axis.normalized())
                rt.set_world(poses[i], w, f"clavicle_{side}", Matrix.Translation(c.translation) @ r @ Matrix.Translation(-c.translation) @ c)
    # 3. Feet: stance positions and toe directions; captured steps and heel lifts kept around them.
    worlds = [rt.fk(p) for p in poses]
    for side in ("l", "r"):
        ft = f"foot_{side}"
        ank = [w[ft].translation.copy() for w in worlds]
        amean = mean(ank)
        fwant = char_space(st[ft][0], st[ft][1], 0.0) * k
        yaw_key = f"{ft}_yaw"
        toe_yaw = None
        if yaw_key in st:
            toes = [(w[f"ball_{side}"].translation - w[ft].translation) for w in worlds]
            cap = mean_f([math.degrees(math.atan2(t.x, -t.y)) for t in toes])   # 0 = toes toward the opponent
            toe_yaw = st[yaw_key] - cap
        gain = st.get("foot_motion", 1.0)
        rest_ank = rt.rest[ft].translation.z
        hip_line = [line_yaw(w["thigh_l"].translation - w["thigh_r"].translation) for w in worlds]
        hips0 = mean_f(hip_line)
        for i in range(n):
            w = rt.fk(poses[i])
            dev = ank[i] - amean
            lift = cap_ank[side][i] - ank_floor
            target = Vector((fwant.x + dev.x * gain, fwant.y + dev.y * gain, rest_ank + lift))
            # A foot off the floor (a kick, a knee) keeps its captured knee direction and toe angle; the stance's knee
            # pole and toe turn apply to planted feet and fade out over the first 15 cm of lift.
            air = A.ease("smooth", max(0.0, min(1.0, (lift - 0.04) / 0.15)))
            rot = None
            if toe_yaw is not None and air < 1.0:
                rot = Matrix.Rotation(math.radians(toe_yaw * (1.0 - air)), 3, "Z") @ w[ft].to_3x3()
            if rock and side == "l":
                # The lead foot goes light as the weight rocks back: the heel lifts, the ball stays down.
                heel = rock["lead_heel"] * k * max(0.0, -math.sin(phase(i))) ** 1.5
                if heel > 1e-4:
                    base = rot if rot is not None else w[ft].to_3x3()
                    toe = (w[f"ball_{side}"].translation - w[ft].translation)
                    axis = toe.cross(Vector((0, 0, 1)))
                    if axis.length > 1e-6:
                        ang = math.asin(min(0.9, heel / max(0.05, toe.length)))
                        rot = Matrix.Rotation(-ang, 3, axis.normalized()) @ base
                    target.z += heel
            pole = char_space(*st[f"knee_{side}"]).normalized() if f"knee_{side}" in st else None
            if pole is not None:
                # The stance's knee direction turns with the hips, so a spinning move does not bend the knee sideways.
                turn = line_yaw(w["thigh_l"].translation - w["thigh_r"].translation) - hips0
                pole = Matrix.Rotation(math.radians(turn), 3, "Z") @ pole
            if pole is not None and air > 0.0:
                knee = (w[f"calf_{side}"].translation - w[f"thigh_{side}"].translation).normalized()
                pole = pole.lerp(knee, air)
            rt.leg_ik(poses[i], w, side, target, pole, rot)
    # 4. Hands: stance guard positions that ride with the chest, turning and leaning with it (a guard hand that only
    # followed the chest's position floated in place while the body twisted into a strike); the captured hand motion
    # is kept around them, measured in the chest's own turning frame.
    if not hands:
        return
    sides = ("l", "r") if hands is True else tuple(hands)
    worlds = [rt.fk(p) for p in poses]
    # (anchor, the parameter, says "start" or "mean": one-shots measure from their first frame.)
    chest_at = [w["spine_03"].translation.copy() for w in worlds]
    amean = mean(chest_at)
    chest_q = [w["spine_03"].to_quaternion() for w in worlds]
    if anchor == "start":
        ref_q = chest_q[0].copy()
    else:
        acc = Quaternion((0.0, 0.0, 0.0, 0.0))
        for q in chest_q:
            acc = acc + (q if q.dot(chest_q[0]) >= 0 else -q)
        ref_q = acc.normalized()
    follow = st.get("hand_follow", 1.0)
    turn = [Quaternion().slerp(q @ ref_q.inverted(), follow) for q in chest_q]
    for side in sides:
        hd = f"hand_{side}"
        rel = [t.inverted() @ (w[hd].translation - a) for w, a, t in zip(worlds, chest_at, turn)]
        rmean = mean(rel)
        hwant = char_space(*st[hd]) * k
        gain = st.get("hand_motion", 1.0)
        pole = char_space(*st[f"elbow_{side}"]) if f"elbow_{side}" in st else None
        for i in range(n):
            w = rt.fk(poses[i])
            target = chest_at[i] + turn[i] @ ((hwant - amean) + (rel[i] - rmean) * gain)
            rt.arm_ik(poses[i], w, side, target, None if pole is None else turn[i] @ pole)


def add_air(rt, poses, frames, height, spin=0.0, spin_frames=None, tuck=None, tuck_share=0.8):
    """Turns a grounded capture into a jumping one: between `frames` (first, last; 1-based) the whole body rises on a
    parabola `height` metres high, turns an extra `spin` degrees about its own vertical axis (eased over `spin_frames`,
    default the whole jump; a whole number of turns so the body ends facing as captured), and the `tuck` side's leg
    folds up under the hips. The capture's own limbs, including the kicking leg, are kept."""
    a, b = frames
    s0, s1 = spin_frames or frames
    assert abs(spin) % 360.0 < 1e-6, "extra spin must be whole turns"
    for i in range(len(poses)):
        f = i + 1
        lift = 0.0
        if a < f < b:
            t = (f - a) / float(b - a)
            lift = height * 4.0 * t * (1.0 - t)
        ang = 0.0
        if spin and s0 < f < s1:
            ang = spin * A.ease("smooth", (f - s0) / float(s1 - s0))
        if lift == 0.0 and ang == 0.0:
            continue
        w = rt.fk(poses[i])
        pel = w["pelvis"]
        m = Matrix.Translation((0.0, 0.0, lift)) @ turn_about(pel, pel.translation.copy(), ang)
        rt.set_world(poses[i], w, "pelvis", m)
        if tuck and lift > 0.0:
            w = rt.fk(poses[i])
            ft = f"foot_{tuck}"
            target = w[ft].translation + Vector((0.0, 0.0, lift * tuck_share))
            knee = w[f"calf_{tuck}"].translation - w[f"thigh_{tuck}"].translation
            rt.leg_ik(poses[i], w, tuck, target, knee.normalized())
    # The landing takes the weight: hips sink and come back over the next frames, feet stay where they land.
    land_dip(rt, poses, b, depth=0.07 * height / 0.3 if height > 0 else 0.0)


def land_dip(rt, poses, frame, depth, length=10):
    """Absorbs a landing at `frame` (1-based): the pelvis sinks `depth` metres and returns over `length` frames (fast
    down, slower up) while feet on the ground stay planted (leg IK back to where they were)."""
    if depth <= 0.0:
        return
    for k in range(1, length + 1):
        i = frame - 1 + k
        if i >= len(poses):
            break
        t = k / float(length)
        d = depth * math.sin(math.pi * min(1.0, t ** 0.6))
        w = rt.fk(poses[i])
        feet = {s: (w[f"foot_{s}"].translation.copy(), w[f"foot_{s}"].to_3x3()) for s in ("l", "r")}
        rt.shift_pelvis(poses[i], Vector((0.0, 0.0, d)))
        w = rt.fk(poses[i])
        for s, (pos, rot) in feet.items():
            if pos.z < 0.16:
                knee = w[f"calf_{s}"].translation - w[f"thigh_{s}"].translation
                rt.leg_ik(poses[i], w, s, pos, knee.normalized(), rot)
                w = rt.fk(poses[i])


def fold_limb(rt, poses, kind, side, angle):
    """Turns a hook into an elbow strike, or a front kick into a knee: the lower segment folds toward the upper one until
    the joint is bent `angle` degrees (180 = flat), most when the limb is furthest out. The upper segment, and so the
    elbow or knee point that lands, stays as captured; the hand or foot turns with the folded segment."""
    if kind == "arm":
        upper, lower, end = f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"
    else:
        upper, lower, end = f"thigh_{side}", f"calf_{side}", f"foot_{side}"
    worlds = [rt.fk(p) for p in poses]
    if kind == "arm":
        reach = [(w[end].translation - w["spine_03"].translation).length for w in worlds]
    else:
        reach = [w[lower].translation.z for w in worlds]   # knee height
    r0, r1 = reach[0], max(reach)
    for i, w in enumerate(worlds):
        weight = A.ease("smooth", (reach[i] - r0) / max(1e-4, r1 - r0))
        if weight <= 0.0:
            continue
        S, E, W = w[upper].translation, w[lower].translation, w[end].translation
        du, df = (E - S).normalized(), (W - E)
        length, df = df.length, df.normalized()
        bend = math.degrees(math.acos(max(-1.0, min(1.0, du.dot(df)))))
        want = bend + (max(bend, angle) - bend) * weight
        if kind == "leg" or bend < 15.0:
            # A straight limb has no bending plane of its own: a knee folds about the hip line (shin down and back),
            # an arm about the vertical.
            axis = (w["thigh_l"].translation - w["thigh_r"].translation) if kind == "leg" else Vector((0.0, 0.0, 1.0))
            axis.normalize()
            back = Vector((0.0, 1.0, -1.0)).normalized() if kind == "leg" else (S - E).normalized()
            cand = [Matrix.Rotation(math.radians(want), 3, ax) @ du for ax in (axis, -axis)]
            new = max(cand, key=lambda v: v.dot(back))
        else:
            new = Matrix.Rotation(math.radians(want), 3, du.cross(df).normalized()) @ du
        turn = df.rotation_difference(new).to_matrix()
        target = E + new * length
        end_rot = turn @ w[end].to_3x3()
        if kind == "arm":
            rt.arm_ik(poses[i], w, side, target, E - S, end_rot)
        else:
            rt.leg_ik(poses[i], w, side, target, E - S, end_rot)


def settle_feet(rt, poses, sides, frames, lift=0.06):
    """Steps feet that end a capture away from where they started (a teep that lands forward) back to their first
    frame's place over the last `frames` frames, lifting a little on the way."""
    n = len(poses)
    first = rt.fk(poses[0])
    start = max(1, n - frames - 1)
    begin = rt.fk(poses[start])
    for side in sides:
        ft = f"foot_{side}"
        d = first[ft].translation - begin[ft].translation
        d.z = 0.0
        if d.length < 0.02:
            continue
        for k in range(1, n - start):
            i = start + k
            t = k / float(n - 1 - start)
            w = rt.fk(poses[i])
            target = w[ft].translation + d * A.ease("smooth", t)
            target.z += lift * math.sin(math.pi * min(1.0, t))
            rt.leg_ik(poses[i], w, side, target)


HALF_JOINTS = (("upperarm_half", "upperarm"), ("thigh_half", "thigh"))


def half_rotation(q, prev=None):
    """Half of local rotation q's swing: the bone direction (local Y) is moved halfway along the arc from rest to where
    the limb points. Twist is left to the twist bones, so the half joint stays on the joint's bend. Near a half turn
    the arc's axis is ambiguous; the previous frame's half (prev) then picks the same way round."""
    y = Vector((0.0, 1.0, 0.0))
    d = q @ y
    axis, angle = y.rotation_difference(d).to_axis_angle()
    h = Quaternion(axis, angle * 0.5)
    if prev is not None and angle > 2.8:
        pa, _ = prev.to_axis_angle()
        pa = pa - y * pa.dot(y)
        if pa.length > 1e-6:
            h = Quaternion(pa.normalized(), angle * 0.5)
    return h


def half_joints(out, prev=None):
    """Shoulder and hip half joints (characters' eh_rig.HALF) turn half as far as their limb, so the skin around the
    joint bends round. They share the limb's parent and rest frame, so half its local rotation is theirs. prev: dict
    carried from frame to frame for continuity."""
    for half, limb in HALF_JOINTS:
        for side in ("l", "r"):
            h, l = f"{half}_{side}", f"{limb}_{side}"
            if h in out and l in out:
                q = half_rotation(out[l][1], None if prev is None else prev.get(h))
                out[h] = (Vector((0.0, 0.0, 0.0)), q)
                if prev is not None:
                    prev[h] = q


REACH_PARTS = {"hand_l": "hand_l", "hand_r": "hand_r", "elbow_l": "lowerarm_l", "elbow_r": "lowerarm_r",
               "knee_l": "calf_l", "knee_r": "calf_r", "foot_l": "ball_l", "foot_r": "ball_r"}


def straighten(rt, poses, side, first, last, angle=172.0, ramp_in=3, ramp_out=5):
    """Straightens a punching arm on its active frames (first..last, 1-based): the wrist moves out along the line from
    the shoulder until the elbow opens to `angle` degrees, keeping the elbow's captured bend plane and the hand's
    orientation, eased in over ramp_in frames and out over ramp_out. Captured boxing punches stop short of straight
    (134-150 degrees), which on screen reads as an arm that never extends. Returns the elbow angle on the first active
    frame."""
    ua, la, hd = f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}"
    w0 = rt.fk(poses[0])
    upper = (w0[la].translation - w0[ua].translation).length
    fore = (w0[hd].translation - w0[la].translation).length
    full = math.sqrt(upper * upper + fore * fore - 2.0 * upper * fore * math.cos(math.radians(angle)))
    for i, pose in enumerate(poses):
        f = i + 1
        if f < first:
            w = A.ease("smooth", max(0.0, 1.0 - (first - f) / max(1, ramp_in)))
        elif f <= last:
            w = 1.0
        else:
            w = A.ease("smooth", max(0.0, 1.0 - (f - last) / max(1, ramp_out)))
        if w <= 0.0:
            continue
        world = rt.fk(pose)
        sh, wrist = world[ua].translation, world[hd].translation
        d = wrist - sh
        if d.length < 1e-4 or d.length >= full:
            continue
        rt.arm_ik(pose, world, side, sh + d.normalized() * (d.length + (full - d.length) * w))
    w = rt.fk(poses[first - 1])
    u, v = w[ua].translation - w[la].translation, w[hd].translation - w[la].translation
    return math.degrees(u.angle(v))


def reach(rt, poses, part, to, first, last, ramp_in=6, ramp_out=10, max_shift=0.35, max_lean=0.6, skid=0.0,
          balance=0.0):
    """Carries a strike into its hitbox: on the active frames (first..last, 1-based) the striking part (a fist, elbow,
    knee or foot, REACH_PARTS) sits `to` metres in front of the fighter. The hips move toward the target (at most
    max_shift) while every foot that is on the floor stays planted (leg IK), so the fighter steps or lunges in; for
    an arm strike any distance left is covered by leaning the spine forward (at most asin(max_lean)). Eased in over
    ramp_in frames before the
    first active frame and out over ramp_out after the last. Returns the reach achieved on the first active frame.
    Kicks and knees stand on one leg, so two options keep the body over it: skid lets a planted foot slide forward
    with the hips (up to that many metres, the support foot's push-off skid), and balance leans the upper body back
    against the hips' remaining shift past the support foot (balance x shift metres at the chest)."""
    bone = REACH_PARTS[part]
    w0 = rt.fk(poses[first - 1])
    need = to - (-w0[bone].translation.y)
    ground = min(min(rt.fk(p)[f"ball_{s}"].translation.z for s in ("l", "r")) for p in poses)
    n = len(poses)
    for i in range(n):
        f = i + 1
        if f < first:
            w = A.ease("smooth", max(0.0, 1.0 - (first - f) / max(1, ramp_in)))
        elif f <= last:
            w = 1.0
        else:
            w = A.ease("smooth", max(0.0, 1.0 - (f - last) / max(1, ramp_out)))
        if w <= 0.0:
            continue
        pose = poses[i]
        world = rt.fk(pose)
        # A foot whose ball is on the floor stays planted; one in the air goes with the hips. In between it blends,
        # so a foot rising or landing during the strike doesn't pop between the two.
        planted = {}
        for s in ("l", "r"):
            h = world[f"ball_{s}"].translation.z - ground
            p = 1.0 if h < 0.03 else max(0.0, 1.0 - (h - 0.03) / 0.05)
            if p > 0.0:
                planted[s] = (world[f"foot_{s}"].copy(), p)
        shift = max(-max_shift, min(max_shift, need)) * w
        before = world["pelvis"].translation.copy()
        rt.shift_pelvis(pose, Vector((0.0, shift, 0.0)))
        moved = rt.fk(pose)["pelvis"].translation - before
        moved.z = 0.0
        slide = min(1.0, skid * w / abs(shift)) if skid and abs(shift) > 1e-4 else 0.0
        for s, (m, p) in planted.items():
            rt.leg_ik(pose, rt.fk(pose), s, m.translation + moved * (slide * p + 1.0 - p), None, m.to_3x3())
        if balance and any(p > 0.5 for _, p in planted.values()) and abs(shift) > 1e-4:
            # Lean the upper body back about the hips so the chest stays over the support foot.
            back = balance * abs(shift) * (1.0 - slide)
            world = rt.fk(pose)
            height = max(0.2, world["spine_03"].translation.z - world["spine_01"].translation.z)
            angle = -math.copysign(math.atan2(back, height), shift)
            for name, share in (("spine_01", 0.3), ("spine_02", 0.3), ("spine_03", 0.4)):
                w2 = rt.fk(pose)
                pv = w2[name].translation
                r = Matrix.Rotation(angle * share, 4, Vector((1.0, 0.0, 0.0)))
                rt.set_world(pose, w2, name, Matrix.Translation(pv) @ r @ Matrix.Translation(-pv) @ w2[name])
        rest = (need * w) - shift
        if part.startswith(("hand", "elbow")) and abs(rest) > 1e-3:
            # Lean the spine about the hips so the part moves the rest of the way.
            world = rt.fk(pose)
            pivot = world["spine_01"].translation
            arm = world[bone].translation - pivot
            lever = max(0.2, math.hypot(arm.y, arm.z))
            angle = math.asin(max(-max_lean, min(max_lean, rest / lever)))
            for name, share in (("spine_01", 0.3), ("spine_02", 0.3), ("spine_03", 0.4)):
                w2 = rt.fk(pose)
                pv = w2[name].translation
                r = Matrix.Rotation(angle * share, 4, Vector((1.0, 0.0, 0.0)))
                rt.set_world(pose, w2, name, Matrix.Translation(pv) @ r @ Matrix.Translation(-pv) @ w2[name])
    return -rt.fk(poses[first - 1])[bone].translation.y


def extend(rt, poses, side, to, height, first, last, ramp_in=5, ramp_out=6):
    """Drives a kick out to a straight leg on its active frames (first..last, 1-based): the ankle goes `to` metres in
    front of the hip joint at `height` metres, eased in over ramp_in frames and out over ramp_out, and the leg IK
    straightens the knee to get there. A captured chamber that never extends (the knee bent the same way from lift to
    retraction) then reads as a push kick. Returns the ankle's distance in front of the fighter on the first active
    frame."""
    foot, thigh = f"foot_{side}", f"thigh_{side}"
    for i, pose in enumerate(poses):
        f = i + 1
        if f < first:
            w = A.ease("smooth", max(0.0, 1.0 - (first - f) / max(1, ramp_in)))
        elif f <= last:
            w = 1.0
        else:
            w = A.ease("smooth", max(0.0, 1.0 - (f - last) / max(1, ramp_out)))
        if w <= 0.0:
            continue
        world = rt.fk(pose)
        ankle = world[foot].translation
        hip = world[thigh].translation
        target = Vector((ankle.x, hip.y - to, height))
        rt.leg_ik(pose, world, side, ankle.lerp(target, w), None, world[foot].to_3x3())
    return -rt.fk(poses[first - 1])[foot].translation.y


# Follow-through: (bone, frames of lag, share of the lagging rotation). The upper spine, neck and head trail the body's
# turns slightly, so the torso bends through a motion instead of turning as one piece.
OVERLAP = (("spine_03", 1, 0.3), ("neck_01", 1, 0.35), ("head", 2, 0.35))


def overlap(poses, loop):
    """Blends each OVERLAP bone's local rotation toward its rotation a frame or two earlier (loops wrap around), the
    successive breaking of joints that makes a body read as flexible. Light, so the capture's own motion leads."""
    src = [{n: p[n] for n, _, _ in OVERLAP if n in p} for p in poses]
    count = len(poses)
    for i, pose in enumerate(poses):
        for name, lag, share in OVERLAP:
            if name not in pose:
                continue
            j = (i - lag) % count if loop else max(0, i - lag)
            loc, q = pose[name]
            q_lag = src[j][name][1]
            if q.dot(q_lag) < 0:
                q_lag = -q_lag
            pose[name] = (loc, q.slerp(q_lag, share))


def limit_wrists(out, max_swing=12.0):
    """Keeps each fist in line with its forearm: the wrist's bend off the rest line (its swing) is scaled down to
    max_swing degrees, its twist (the forearm turning the palm) kept. Arm IK holds a hand's captured world orientation
    while it moves the forearm (placing a guard, extending a punch), which left fists cocked back 20-60 degrees; a fist
    lands and guards with the wrist straight."""
    axis = Vector((0, 1, 0))
    for side in ("l", "r"):
        n = f"hand_{side}"
        if n not in out:
            continue
        loc, q = out[n]
        q = q.normalized()
        v = Vector((q.x, q.y, q.z))
        p = axis * v.dot(axis)
        t = Quaternion((q.w, p.x, p.y, p.z))
        t = t.normalized() if t.magnitude > 1e-9 else Quaternion()
        sw = q @ t.inverted()
        if sw.w < 0:
            sw = -sw
        ang = math.degrees(sw.angle)
        if ang > max_swing:
            sw = Quaternion().slerp(sw, max_swing / ang)
        out[n] = (loc, sw @ t)


def _swing_twist(q, axis=Vector((0, 1, 0))):
    q = q.normalized()
    v = Vector((q.x, q.y, q.z))
    p = axis * v.dot(axis)
    t = Quaternion((q.w, p.x, p.y, p.z))
    t = t.normalized() if t.magnitude > 1e-9 else Quaternion()
    sw = q @ t.inverted()
    return (-sw if sw.w < 0 else sw), t


def limit_neck(out, max_swing=30.0):
    """Keeps the head on a natural neck: the neck's and head's nod and tilt off the rest line (their swings, summed)
    are scaled down to max_swing degrees; turning the head left and right (their twists) is kept. Reaction captures
    and the stance layer's head correction had bent the neck 45-65 degrees off the chest."""
    parts = [(n, *_swing_twist(out[n][1])) for n in ("neck_01", "head") if n in out]
    total = sum(math.degrees(sw.angle) for _, sw, _ in parts)
    if total <= max_swing:
        return
    k = max_swing / total
    for n, sw, t in parts:
        out[n] = (out[n][0], Quaternion().slerp(sw, k) @ t)


def fist(out, curl=1.0):
    for side in ("l", "r"):
        for fing in A.FINGERS:
            for seg, amount in ((1, 75), (2, 95), (3, 70)):
                n = f"{fing}_0{seg}_{side}"
                if n in out:
                    out[n] = (out[n][0], Quaternion((1, 0, 0), math.radians(amount * curl)))
        for seg, amount in A.THUMB_WRAP:
            n = f"thumb_0{seg}_{side}"
            if n in out:
                out[n] = (out[n][0], Quaternion((1, 0, 0), math.radians(amount * curl)))


def blend_pose(a, b, t):
    """Per-bone blend of two local poses (t=0 gives a)."""
    out = {}
    for n in a:
        la, qa = a[n]
        lb, qb = b.get(n, a[n])
        if qa.dot(qb) < 0:
            qb = -qb
        out[n] = (la.lerp(lb, t), qa.slerp(qb, t))
    return out


def bake_tracked(arm, total):
    """Coat panels aim at helper bones on the thighs (DAMPED_TRACK). Solve those constraints on the keyed motion and key
    the result as FK, as the scripted build does, so the coat follows the legs."""
    tracked = [pb for pb in arm.pose.bones if any(c.type == "DAMPED_TRACK" for c in pb.constraints)]
    if not tracked:
        return
    for pb in tracked:
        for c in pb.constraints:
            c.mute = c.type != "DAMPED_TRACK"
    # Solve every frame first and key afterwards: a key inserted at one frame would hold over the next frame as the
    # bone's own pose and feed the solve back, building a part-influence follow up to a full one (2026-11-09).
    # (Unkeyed, they rest at their own rest pose; keyed, each frame_set evaluates their own keys.)
    for pb in tracked:
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    scene = bpy.context.scene
    solved = {}
    for frame in range(1, total + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        solved[frame] = [(pb, arm.convert_space(pose_bone=pb, matrix=pb.matrix, from_space="POSE", to_space="LOCAL").decompose())
                         for pb in tracked]
    for frame in range(1, total + 1):
        for pb, (loc, q, _) in solved[frame]:
            pb.location = loc
            pb.rotation_quaternion = q
            pb.keyframe_insert("location", frame=frame)
            pb.keyframe_insert("rotation_quaternion", frame=frame)
    for pb in tracked:
        for c in pb.constraints:
            c.mute = True


def warp(anchors):
    """Map target frame -> source frame through [(target_frame, source_frame), ...], linear beyond the ends. Between
    anchors it is a monotone cubic (Fritsch-Butland tangents at inner anchors, the end segments' slopes at the ends),
    so the playback speed changes gradually through an anchor such as the contact frame instead of jumping there."""
    pts = sorted(anchors)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    sec = [(ys[i + 1] - ys[i]) / max(1e-6, xs[i + 1] - xs[i]) for i in range(len(pts) - 1)]
    tan = [sec[0]] + [0.0] * (len(pts) - 2) + [sec[-1]]
    for i in range(1, len(pts) - 1):
        h0, h1 = xs[i] - xs[i - 1], xs[i + 1] - xs[i]
        d0, d1 = sec[i - 1], sec[i]
        if d0 * d1 > 0.0:
            w0, w1 = 2.0 * h1 + h0, h1 + 2.0 * h0
            tan[i] = (w0 + w1) / (w0 / d0 + w1 / d1)

    def f(x):
        if x <= xs[0]:
            return ys[0] + (x - xs[0]) * sec[0]
        if x >= xs[-1]:
            return ys[-1] + (x - xs[-1]) * sec[-1]
        i = max(k for k in range(len(xs) - 1) if xs[k] <= x)
        h = max(1e-6, xs[i + 1] - xs[i])
        t = (x - xs[i]) / h
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * tan[i] + (-2 * t3 + 3 * t2) * ys[i + 1]
                + (t3 - t2) * h * tan[i + 1])
    return f


def additive(rt, poses, base):
    """Layers a clip's motion onto a fixed pose (a scripted guard, say): every bone turns away from the base by the
    local rotation it turned through since the clip's first frame (the pelvis by the same world turn) and the pelvis
    moves as the clip's does. Each foot goes where the base has it plus the clip's foot movement, so planted feet stay
    planted; the knee keeps its bend plane."""
    first = poses[0]
    cap = [rt.fk(p) for p in poses]
    base_world = rt.fk(base)
    out = []
    for i, p in enumerate(poses):
        o = {}
        for name, (loc, q) in p.items():
            bl, bq = base.get(name, (loc, q))
            l0, q0 = first[name]
            nq = (q @ q0.inverted() @ bq) if name == "pelvis" else (bq @ q0.inverted() @ q)
            o[name] = (bl + (loc - l0), nq.normalized())
        for side in ("l", "r"):
            ft = f"foot_{side}"
            w = rt.fk(o)
            c0, ci = cap[0][ft], cap[i][ft]
            target = base_world[ft].translation + (ci.translation - c0.translation)
            rot = (ci.to_3x3() @ c0.to_3x3().inverted()) @ base_world[ft].to_3x3()
            rt.leg_ik(o, w, side, target, None, rot)
        out.append(o)
    return out


def key_pose(arm, pose, frame):
    for name, (loc, q) in pose.items():
        pb = arm.pose.bones[name]
        pb.location = loc
        pb.rotation_quaternion = q
        pb.keyframe_insert("location", frame=frame)
        pb.keyframe_insert("rotation_quaternion", frame=frame)
