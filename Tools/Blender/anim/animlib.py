"""Effector-driven animation authoring for the game_engine skeleton (Blender 5.2).

Poses are written in *character space*: f = forward (toward the opponent), l = the character's left, u = up, metres,
with the root on the floor at the origin. Each animation is a list of keyed poses; the engine interpolates them per
frame with chosen easing, poses pelvis/spine/head/clavicles analytically, drives arms and legs with IK, compensates
planted feet for the root travel the combat simulation applies, then bakes to FK keys at 60 fps for export.
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

FPS = 60
SPINE = (("spine_01", 0.30), ("spine_02", 0.30), ("spine_03", 0.40))
NECK = (("neck_01", 0.40), ("head", 0.60))
FINGERS = ("index", "middle", "ring", "pinky")


def V(f, l, u):
    """Character space (character faces -Y, left is +X) to armature space."""
    return Vector((l, -f, u))


def rot(yaw=0.0, pitch=0.0, roll=0.0):
    """Yaw turns toward the character's left, pitch leans forward, roll tilts the top toward the left."""
    return (Quaternion((0, 0, 1), math.radians(yaw)) @ Quaternion((1, 0, 0), math.radians(pitch))
            @ Quaternion((0, 1, 0), math.radians(roll)))


# ---------------------------------------------------------------------------------------------------- easing
def ease(kind, t):
    t = max(0.0, min(1.0, t))
    if kind == "linear":
        return t
    if kind == "in":          # slow start, fast finish (wind-up into a strike)
        return t * t * t
    if kind == "out":         # fast start, soft finish (strike snapping out)
        return 1.0 - (1.0 - t) ** 3
    if kind == "snap":        # very fast out
        return 1.0 - (1.0 - t) ** 5
    if kind == "hold":
        return 0.0
    return t * t * (3.0 - 2.0 * t)   # smooth


def lerp(a, b, t):
    if isinstance(a, (int, float)):
        return a + (b - a) * t
    return tuple(x + (y - x) * t for x, y in zip(a, b))


class Pose(dict):
    """A key pose. Unspecified channels inherit from the previous key during interpolation."""

    def __call__(self, **changes):
        p = Pose(self)
        p.update(changes)
        return p


def blend(a, b, t):
    out = Pose()
    for k in set(a) | set(b):
        if k in a and k in b:
            va, vb = a[k], b[k]
            numeric = isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool) and not isinstance(vb, bool)
            tuples = isinstance(va, tuple) and isinstance(vb, tuple) and len(va) == len(vb)
            if numeric or tuples:
                out[k] = lerp(va, vb, t)
            else:
                # Switching between kinds of control (e.g. world foot to character foot) happens at the key itself.
                out[k] = vb if t >= 1.0 - 1e-9 else va
        else:
            out[k] = a.get(k, b.get(k))
    return out


def sample(keys, frame):
    """keys: list of (frame, Pose, easing-into-this-key). Returns the interpolated pose at frame."""
    full = []
    acc = Pose()
    for f, p, e in keys:
        acc = acc(**p)
        full.append((f, acc, e))
    if frame <= full[0][0]:
        return full[0][1]
    for (f0, p0, _), (f1, p1, e1) in zip(full, full[1:]):
        if f0 <= frame <= f1:
            return blend(p0, p1, ease(e1, (frame - f0) / max(1e-6, f1 - f0)))
    return full[-1][1]


# ---------------------------------------------------------------------------------------------------- rig
class Rig:
    def __init__(self, arm, prefix, height=None):
        self.arm = arm
        self.prefix = prefix
        self.pb = arm.pose.bones
        self.bones = arm.data.bones
        self.rest = {b.name: b.matrix_local.copy() for b in arm.data.bones}
        self.restq = {n: m.to_quaternion() for n, m in self.rest.items()}
        for pb in self.pb:
            pb.rotation_mode = "QUATERNION"
        self.targets = {}
        # Poses are authored for a 1.75 m body; positions scale with the character's height.
        top = max(b.tail_local.z for b in arm.data.bones)
        self.scale = (height / 1.75) if height else (top / 1.643)
        self._setup_ik()

    def head(self, name):
        return self.rest[name].translation.copy()

    def _empty(self, name):
        full = f"{self.prefix}_{name}"
        e = bpy.data.objects.get(full)
        if e is None:
            e = bpy.data.objects.new(full, None)
            bpy.context.scene.collection.objects.link(e)
            e.empty_display_size = 0.05
        e.parent = self.arm
        e.rotation_mode = "QUATERNION"
        self.targets[name] = e
        return e

    def _setup_ik(self):
        for side in ("l", "r"):
            for limb, mid, end in (("arm", f"lowerarm_{side}", f"hand_{side}"), ("leg", f"calf_{side}", f"foot_{side}")):
                tgt = self._empty(f"{limb}_{side}")
                pole = self._empty(f"{limb}_{side}_pole")
                pb = self.pb[mid]
                for c in list(pb.constraints):
                    pb.constraints.remove(c)
                ik = pb.constraints.new("IK")
                ik.target = tgt
                ik.pole_target = pole
                ik.chain_count = 2
                ik.use_stretch = False
                if limb == "leg":
                    foot = self.pb[end]
                    for c in list(foot.constraints):
                        foot.constraints.remove(c)
                    cr = foot.constraints.new("COPY_ROTATION")
                    cr.target = tgt
                    cr.mix_mode = "REPLACE"
        self._calibrate_poles()

    def _calibrate_poles(self):
        """Pick each IK pole angle so the rest pose solves back onto itself."""
        self.reset()
        for side in ("l", "r"):
            for limb, upper, mid, end, hint in (("arm", f"upperarm_{side}", f"lowerarm_{side}", f"hand_{side}", V(-0.2, 0.0, -0.4)),
                                                ("leg", f"thigh_{side}", f"calf_{side}", f"foot_{side}", V(0.5, 0.0, 0.0))):
                tgt, pole = self.targets[f"{limb}_{side}"], self.targets[f"{limb}_{side}_pole"]
                tgt.location = self.head(end)
                tgt.rotation_quaternion = self.restq[end]
                pole.location = self.head(mid) + hint
                want = self.head(mid)
                best = None
                for ang in range(-180, 180, 5):
                    self.pb[mid].constraints[0].pole_angle = math.radians(ang)
                    bpy.context.view_layer.update()
                    err = ((self.arm.matrix_world.inverted() @ self.pb[mid].head) if False else self.pb[mid].head - want).length
                    if best is None or err < best[0]:
                        best = (err, ang)
                self.pb[mid].constraints[0].pole_angle = math.radians(best[1])
                print(f"ANIMLIB pole {self.prefix} {limb}_{side} {best[1]} err {best[0]:.4f}")

    def reset(self):
        for pb in self.pb:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.scale = (1, 1, 1)

    def set_world_rot(self, bone, w_parent, w_bone):
        """Local rotation that gives `bone` the armature-space rotation w_bone @ rest, given its parent's w_parent."""
        r = self.restq[bone]
        self.pb[bone].rotation_quaternion = r.inverted() @ w_parent.inverted() @ w_bone @ r

    # Default channel values; character poses override them.
    DEFAULTS = {
        "pelvis": (0.0, 0.0, 0.0), "pelvis_rot": (0.0, 0.0, 0.0), "chest": (0.0, 0.0, 0.0), "head": (0.0, 0.0, 0.0),
        "spin": 0.0, "pivot": (0.0, 0.0), "clav_l": (0.0, 0.0, 0.0), "clav_r": (0.0, 0.0, 0.0), "fist": 0.0,
        "ball_l": 0.0, "ball_r": 0.0, "foot_l_rot": (0.0, 0.0, 0.0), "foot_r_rot": (0.0, 0.0, 0.0),
        "elbow_l": (-0.2, 0.25, -0.4), "elbow_r": (-0.2, -0.25, -0.4), "knee_l": (0.6, 0.1, 0.0), "knee_r": (0.6, -0.1, 0.0),
        "wrist_l": (0.0, 0.0, 0.0), "wrist_r": (0.0, 0.0, 0.0), "gaze": 0.0, "root_f": 0.0,
    }

    def apply(self, pose, travel=0.0):
        """Poses the rig. `travel` is the simulation's cumulative forward root motion (m) at this frame; feet keyed
        with *_world are held in place relative to the starting root position."""
        p = dict(self.DEFAULTS)
        p.update(pose)
        k = self.scale

        def S(t):
            return tuple(c * k for c in t)

        spin = rot(yaw=p["spin"])
        pf, pl = p["pivot"]
        if p.get("pivot_world"):
            pf -= travel
        pivot = V(pf * k, pl * k, 0.0)

        def place(vec):
            return pivot + spin @ (vec - pivot)

        # Pelvis: head position offset from rest plus rotation, both spun about the pivot.
        pr = rot(*p["pelvis_rot"])
        pel_rest = self.head("pelvis")
        pel_pos = place(pel_rest + V(*S(p["pelvis"])))
        w_pel = spin @ pr
        r = self.restq["pelvis"]
        self.pb["pelvis"].rotation_quaternion = r.inverted() @ w_pel @ r
        self.pb["pelvis"].location = r.inverted() @ (pel_pos - pel_rest)
        # Spine shares the chest rotation; neck and head share the head rotation (relative to the chest).
        chest = rot(*p["chest"])
        w_prev = w_pel
        for name, share in SPINE:
            part = Quaternion().slerp(chest, share)
            w = w_prev @ part
            self.set_world_rot(name, w_prev, w)
            w_prev = w
        w_chest = w_prev
        head_q = rot(*p["head"])
        if p["gaze"] > 0.0:
            # Keep the face toward the opponent: undo some of the body's yaw.
            total_yaw = p["pelvis_rot"][0] + p["chest"][0] + p["spin"]
            head_q = rot(yaw=-total_yaw * p["gaze"]) @ head_q
        w_prev2 = w_chest
        for name, share in NECK:
            w = w_prev2 @ Quaternion().slerp(head_q, share)
            self.set_world_rot(name, w_prev2, w)
            w_prev2 = w
        for side in ("l", "r"):
            self.set_world_rot(f"clavicle_{side}", w_chest, w_chest @ rot(*p[f"clav_{side}"]))
        # Arms: hand targets are character-space positions, spun with the body.
        def rel(vec):
            # Offset in the pelvis frame (follows the pelvis through rolls, falls and lying poses).
            return pel_pos + w_pel @ V(*S(vec))

        for side in ("l", "r"):
            if p.get(f"hand_{side}_rel") is not None:
                hand_pos = rel(p[f"hand_{side}_rel"])
            elif p.get(f"hand_{side}_abs") is not None:
                hand_pos = V(*S(p[f"hand_{side}_abs"]))
            elif p.get(f"hand_{side}") is not None:
                hand_pos = place(V(*S(p[f"hand_{side}"])))
            else:
                hand_pos = None
            if hand_pos is not None:
                self.targets[f"arm_{side}"].location = hand_pos
            shoulder = place(self.head(f"upperarm_{side}") + V(*S(p["pelvis"])))
            self.targets[f"arm_{side}_pole"].location = shoulder + spin @ V(*p[f"elbow_{side}"])
        # Legs: feet in character space, or held in the world while the root travels.
        ankle = Vector((0, 0, self.head("foot_l").z))
        for side in ("l", "r"):
            fr = rot(*p[f"foot_{side}_rot"])
            tgt = self.targets[f"leg_{side}"]
            if p.get(f"foot_{side}_rel") is not None:
                tgt.location = rel(p[f"foot_{side}_rel"])
                tgt.rotation_quaternion = w_pel @ fr @ self.restq[f"foot_{side}"]
            elif p.get(f"foot_{side}_abs") is not None:
                tgt.location = V(*S(p[f"foot_{side}_abs"])) + ankle
                tgt.rotation_quaternion = fr @ self.restq[f"foot_{side}"]
            else:
                foot = p.get(f"foot_{side}")
                world = p.get(f"foot_{side}_world")
                if world is not None:
                    f, l, u = world
                    foot = (f - travel / k, l, u)
                if foot is not None:
                    tgt.location = place(V(*S(foot)) + ankle)
                    tgt.rotation_quaternion = spin @ fr @ self.restq[f"foot_{side}"]
            hip = place(self.head(f"thigh_{side}") + V(*S(p["pelvis"])))
            self.targets[f"leg_{side}_pole"].location = hip + spin @ w_pel @ V(*p[f"knee_{side}"]) if p.get("knee_follow_pelvis") else hip + spin @ V(*p[f"knee_{side}"])
        # Toes, wrists and fists are simple local rotations.
        for side in ("l", "r"):
            b = self.pb.get(f"ball_{side}")
            if b is not None:
                b.rotation_quaternion = Quaternion((1, 0, 0), math.radians(p[f"ball_{side}"]))
            wr = self.pb[f"hand_{side}"]
            y, pt, rl = p[f"wrist_{side}"]
            wr.rotation_quaternion = Quaternion((0, 1, 0), math.radians(rl)) @ Quaternion((1, 0, 0), math.radians(pt)) @ Quaternion((0, 0, 1), math.radians(y))
            curl = p["fist"]
            for fing in FINGERS:
                for seg, amount in ((1, 75), (2, 95), (3, 70)):
                    fb = self.pb.get(f"{fing}_0{seg}_{side}")
                    if fb is not None:
                        fb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(amount * curl))
            for seg, amount in ((1, 25), (2, 40), (3, 35)):
                tb = self.pb.get(f"thumb_0{seg}_{side}")
                if tb is not None:
                    tb.rotation_quaternion = Quaternion((0, 0, 1), math.radians(-amount * curl if side == "l" else amount * curl))


# ---------------------------------------------------------------------------------------------------- authoring
def travel_curve(segments, total):
    """Cumulative forward travel in metres per frame from combat-data travel segments (cm/frame)."""
    out = [0.0] * (total + 2)
    acc = 0.0
    for f in range(1, total + 1):
        out[f] = acc
        for seg in segments:
            a, b = seg["frames"]
            if a <= f <= b:
                acc += seg["vx"] / 100.0
        out[f] = acc
    out[total + 1] = acc
    return out


def author(rigs_and_keys, total, loop=False):
    """rigs_and_keys: list of (Rig, keys, travel_per_frame or None). Keys frames on all bones, frame 1..total."""
    scene = bpy.context.scene
    scene.render.fps = FPS
    actions = []
    for rig, keys, travel in rigs_and_keys:
        if rig.arm.animation_data is None:
            rig.arm.animation_data_create()
    curves = []
    for rig, keys, travel in rigs_and_keys:
        if travel and isinstance(travel[0], dict):
            travel = travel_curve(travel, total)
        curves.append(travel)
    for frame in range(1, total + 1):
        sample_frame = frame
        for (rig, keys, _), travel in zip(rigs_and_keys, curves):
            t = travel[min(frame, len(travel) - 1)] if travel else 0.0
            rig.apply(sample(keys, sample_frame), t)
        bpy.context.view_layer.update()
        for rig, keys, travel in rigs_and_keys:
            # Read the solved pose (including IK) and key it as FK.
            for pb in rig.pb:
                m = rig.arm.convert_space(pose_bone=pb, matrix=pb.matrix, from_space="POSE", to_space="LOCAL")
                loc, q, _ = m.decompose()
                pb.location = loc
                pb.rotation_quaternion = q
                pb.keyframe_insert("location", frame=frame)
                pb.keyframe_insert("rotation_quaternion", frame=frame)
    for rig, _, _ in rigs_and_keys:
        actions.append(rig.arm.animation_data.action)
    return actions


def strip_constraints(rig):
    for pb in rig.pb:
        for c in list(pb.constraints):
            pb.constraints.remove(c)


def mute_constraints(rig, mute):
    """Authoring needs IK; export and playback of the baked FK keys must not re-solve it."""
    for pb in rig.pb:
        for c in pb.constraints:
            c.mute = mute


# ---------------------------------------------------------------------------------------------------- secondary
CHAIN_SPRING = {
    # chain prefix: (stiffness toward the rigid pose, velocity damping, gravity per frame^2 in metres)
    "braid": (0.16, 0.86, 0.0004),
    "strand": (0.28, 0.80, 0.0002),
    "coat": (0.36, 0.78, 0.0003),
}
CHAIN_FLOOR = 0.025   # chain points never sink below this height (armature space, metres)


def bake_secondary(rig, chains, total, loop):
    """Simulates hair and coat chains against the keyed body motion and keys their rotations.

    The target for each chain is the pose authored for that frame (rigid follow for hair; coat tails already follow
    the thighs through the character rig's helper constraints, baked during authoring). Points are integrated with
    damped Verlet steps at 60 Hz, kept at bone length, and converted to minimal rotations away from the target.
    Loops run twice so the second cycle starts from a settled state.
    """
    pb = rig.arm.pose.bones
    scene = bpy.context.scene
    # 1. Record targets from the authored keys.
    targets = {}
    for frame in range(1, total + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        per = {}
        for name, ch in chains.items():
            bones = ch["bones"]
            per[name] = ([pb[bones[0]].head.copy()] + [pb[b].tail.copy() for b in bones],
                         [pb[b].matrix.to_quaternion() for b in bones],
                         pb[ch["parent"]].matrix.to_quaternion())
        targets[frame] = per
    # 2. Simulate and key.
    state = {}
    for pass_i in range(2 if loop else 1):
        for frame in range(1, total + 1):
            for name, ch in chains.items():
                bones = ch["bones"]
                kind = next((k for k in CHAIN_SPRING if name.startswith(k)), "braid")
                stiff, damp, grav = CHAIN_SPRING[kind]
                rigid, q_target, q_parent_target = targets[frame][name]
                lengths = [(rigid[i + 1] - rigid[i]).length for i in range(len(bones))]
                if name not in state:
                    state[name] = ([p.copy() for p in rigid], [p.copy() for p in rigid])
                cur, prev = state[name]
                cur[0] = rigid[0].copy()
                for i in range(1, len(cur)):
                    vel = (cur[i] - prev[i]) * damp
                    prev[i] = cur[i].copy()
                    cur[i] = cur[i] + vel + (rigid[i] - cur[i]) * stiff + Vector((0, 0, -grav))
                for i in range(1, len(cur)):
                    d = cur[i] - cur[i - 1]
                    if d.length > 1e-6:
                        cur[i] = cur[i - 1] + d.normalized() * lengths[i - 1]
                    if cur[i].z < CHAIN_FLOOR:
                        cur[i].z = CHAIN_FLOOR
                if pass_i < (1 if loop else 0):
                    continue
                q_parent_sim = q_parent_target
                q_parent_tgt = q_parent_target
                r_parent = rig.restq[ch["parent"]]
                for i, b in enumerate(bones):
                    # Keep the authored rotation relative to the parent, then swing the bone onto the simulated segment.
                    unposed = q_parent_sim @ q_parent_tgt.inverted() @ q_target[i]
                    axis = unposed @ Vector((0, 1, 0))
                    want = cur[i + 1] - cur[i]
                    q_world = (axis.rotation_difference(want) if want.length > 1e-6 else Quaternion()) @ unposed
                    r_bone = rig.restq[b]
                    pb[b].rotation_quaternion = (q_parent_sim @ r_parent.inverted() @ r_bone).inverted() @ q_world
                    pb[b].keyframe_insert("rotation_quaternion", frame=frame)
                    q_parent_sim, q_parent_tgt, r_parent = q_world, q_target[i], r_bone
