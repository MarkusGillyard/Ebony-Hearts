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
    if kind == "fall":        # accelerating like a falling body: twice its mean speed at the end ("in" reaches three times)
        return t * t
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


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _slope(values, frames, i):
    """Monotone cubic tangent (units per frame) at key i: zero where the channel turns back or at the ends, otherwise a
    weighted harmonic mean of the neighbouring slopes (Fritsch-Butland), so the curve never overshoots a key."""
    if i <= 0 or i >= len(values) - 1 or not all(_number(v) for v in values[i - 1:i + 2]):
        return 0.0
    h0, h1 = frames[i] - frames[i - 1], frames[i + 1] - frames[i]
    d0, d1 = (values[i] - values[i - 1]) / h0, (values[i + 1] - values[i]) / h1
    if d0 * d1 <= 0.0:
        return 0.0
    w0, w1 = 2.0 * h1 + h0, h1 + 2.0 * h0
    return (w0 + w1) / (w0 / d0 + w1 / d1)


def _flow(full, j, frame):
    """Pose between keys j and j+1 of a "smooth" segment. Each channel follows a cubic through the keys: it passes
    through a key without stopping when the neighbouring segment is also smooth and the channel keeps going the same
    way, and eases to rest at a key where it turns back, at the first and last keys, and next to a key with a
    deliberate ease (snap, in, out, linear, hold). With no flow at either end this is exactly the old smoothstep."""
    f0, p0, _ = full[j]
    f1, p1, _ = full[j + 1]
    h = float(f1 - f0)
    t = (frame - f0) / max(1e-6, h)
    flow0 = j > 0 and full[j][2] == "smooth"
    flow1 = j + 2 < len(full) and full[j + 2][2] == "smooth"
    frames = [k[0] for k in full]
    out = Pose()
    h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
    for key in set(p0) | set(p1):
        va, vb = p0.get(key), p1.get(key)
        if key not in p0 or key not in p1:
            out[key] = va if key in p0 else vb
            continue
        tuples = isinstance(va, tuple) and isinstance(vb, tuple) and len(va) == len(vb)
        if not (tuples or (_number(va) and _number(vb))):
            out[key] = vb if t >= 1.0 - 1e-9 else va
            continue
        comps = len(va) if tuples else 1
        res = []
        for c in range(comps):
            series = [(k[1].get(key)[c] if tuples and isinstance(k[1].get(key), tuple) and len(k[1].get(key)) == comps else
                       (k[1].get(key) if not tuples else None)) for k in full]
            a = va[c] if tuples else va
            b = vb[c] if tuples else vb
            m0 = _slope(series, frames, j) if flow0 else 0.0
            m1 = _slope(series, frames, j + 1) if flow1 else 0.0
            res.append(h00 * a + h10 * h * m0 + h01 * b + h11 * h * m1)
        out[key] = tuple(res) if tuples else res[0]
    return out


def sample(keys, frame):
    """keys: list of (frame, Pose, easing-into-this-key). Returns the interpolated pose at frame. "smooth" segments
    flow through keys (see _flow); the other easings shape their segment as written."""
    full = []
    acc = Pose()
    for f, p, e in keys:
        acc = acc(**p)
        full.append((f, acc, e))
    if frame <= full[0][0]:
        return full[0][1]
    for j, ((f0, p0, _), (f1, p1, e1)) in enumerate(zip(full, full[1:])):
        if f0 <= frame <= f1:
            t = (frame - f0) / max(1e-6, f1 - f0)
            if e1 == "smooth":
                return _switches(_flow(full, j, frame), p0, p1, t * t * (3.0 - 2.0 * t))
            w = ease(e1, t)
            return _switches(blend(p0, p1, w), p0, p1, w)
    return full[-1][1]


def _control(p, limb):
    """Which control a hand or foot is under in a pose, in the rig's order of precedence."""
    side = limb[-1]
    kinds = [f"{limb}_rel", f"{limb}_abs"] + ([f"foot_{side}_world"] if limb.startswith("foot") else []) + [limb]
    return next((k for k in kinds if p.get(k) is not None), None)


def _switches(out, p0, p1, w):
    """A hand or foot whose control changes kind between two keys (character space, pelvis-relative, absolute or held
    in the world) moves from where the first key's control puts it to where the second's does. Without this it held
    on one control and jumped on a key: a channel missing from a key takes the next key's value, and a switch between
    kinds happens on the key itself (60-80 cm in one frame in the clinch throws)."""
    if 0.0 < w < 1.0:
        for limb in ("hand_l", "hand_r", "foot_l", "foot_r"):
            k0, k1 = _control(p0, limb), _control(p1, limb)
            if k0 and k1 and k0 != k1:
                out[f"{limb}_switch"] = (k0, p0[k0], k1, p1[k1], w)
    return out


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

        def hand_at(kind, vec):
            if kind.endswith("_rel"):
                return rel(vec)
            if kind.endswith("_abs"):
                return V(*S(vec))
            return place(V(*S(vec)))

        for side in ("l", "r"):
            switch = p.get(f"hand_{side}_switch")
            kind = _control(p, f"hand_{side}")
            if switch:
                k0, v0, k1, v1, w = switch
                hand_pos = hand_at(k0, v0).lerp(hand_at(k1, v1), w)
            elif kind:
                hand_pos = hand_at(kind, p[kind])
            else:
                hand_pos = None
            if hand_pos is not None:
                self.targets[f"arm_{side}"].location = hand_pos
            shoulder = place(self.head(f"upperarm_{side}") + V(*S(p["pelvis"])))
            self.targets[f"arm_{side}_pole"].location = shoulder + spin @ V(*p[f"elbow_{side}"])
        # Legs: feet in character space, or held in the world while the root travels. The limb IK starts from the rest
        # pose every frame: started from the last frame's baked limb it can stick (a straight planted leg would not fold
        # into a raised knee; hands missed their targets by up to 27 cm).
        for side in ("l", "r"):
            for name in ("thigh", "calf", "upperarm", "lowerarm"):
                self.pb[f"{name}_{side}"].rotation_quaternion = (1, 0, 0, 0)
        ankle = Vector((0, 0, self.head("foot_l").z))
        def foot_at(kind, vec, side, fr):
            restq = self.restq[f"foot_{side}"]
            if kind.endswith("_rel"):
                return rel(vec), w_pel @ fr @ restq
            if kind.endswith("_abs"):
                return V(*S(vec)) + ankle, fr @ restq
            if kind.endswith("_world"):
                f, l, u = vec
                vec = (f - travel / k, l, u)
            return place(V(*S(vec)) + ankle), spin @ fr @ restq

        for side in ("l", "r"):
            fr = rot(*p[f"foot_{side}_rot"])
            tgt = self.targets[f"leg_{side}"]
            switch = p.get(f"foot_{side}_switch")
            kind = _control(p, f"foot_{side}")
            if switch:
                k0, v0, k1, v1, w = switch
                (l0, q0), (l1, q1) = foot_at(k0, v0, side, fr), foot_at(k1, v1, side, fr)
                tgt.location, tgt.rotation_quaternion = l0.lerp(l1, w), q0.slerp(q1, w)
            elif kind:
                tgt.location, tgt.rotation_quaternion = foot_at(kind, p[kind], side, fr)
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


# Overlap: the body moves in sequence, not as one block. The chest follows the hips a frame late and the head two;
# hands are placed by their own targets, so strikes still land on their keyed frames.
HALF_JOINTS = (("upperarm_half", "upperarm"), ("thigh_half", "thigh"))   # characters/eh_rig.HALF

TRAIL = {"chest": 1, "head": 2, "gaze": 2}


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


def trailed(keys, frame, loop):
    pose = sample(keys, frame)
    if loop:
        return pose
    for channel, lag in TRAIL.items():
        if channel in pose:
            earlier = sample(keys, max(1, frame - lag))
            if channel in earlier:
                pose[channel] = earlier[channel]
    return pose


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
    half_prev = {}
    for frame in range(1, total + 1):
        sample_frame = frame
        for (rig, keys, _), travel in zip(rigs_and_keys, curves):
            t = travel[min(frame, len(travel) - 1)] if travel else 0.0
            rig.apply(trailed(keys, sample_frame, loop), t)
        bpy.context.view_layer.update()
        for rig, keys, travel in rigs_and_keys:
            # Read the solved pose (including IK) and key it as FK.
            local = {}
            for pb in rig.pb:
                m = rig.arm.convert_space(pose_bone=pb, matrix=pb.matrix, from_space="POSE", to_space="LOCAL")
                loc, q, _ = m.decompose()
                local[pb.name] = (loc, q)
            # Half joints take exactly half their limb's rotation (a half-influence constraint flips near 180 deg),
            # continuing the way they were turning.
            prev = half_prev.setdefault(rig.arm.name, {})
            for half, limb in HALF_JOINTS:
                for side in ("l", "r"):
                    h, l = f"{half}_{side}", f"{limb}_{side}"
                    if h in local and l in local:
                        q = half_rotation(local[l][1], prev.get(h))
                        prev[h] = q
                        local[h] = (local[h][0], q)
            for pb in rig.pb:
                loc, q = local[pb.name]
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


COAT_SWING = math.radians(50.0)   # furthest a coat tail's target swings from hanging straight down


def _hang(rigid, q_target):
    """A coat tail follows its thigh (rig helper) only so far: when the thigh would lift the tail's first segment more
    than COAT_SWING from hanging down (knees drawn up while sitting, a high knee), the whole target chain turns back
    about the tail's root to that limit, and the spring simulation drapes it from there."""
    seg = rigid[1] - rigid[0]
    down = Vector((0.0, 0.0, -1.0))
    if seg.length < 1e-6:
        return rigid, q_target
    over = seg.angle(down) - COAT_SWING
    axis = seg.cross(down)
    if over <= 0.0 or axis.length < 1e-6:
        return rigid, q_target
    turn = Quaternion(axis.normalized(), over)
    root = rigid[0]
    return [root + turn @ (p - root) for p in rigid], [turn @ q for q in q_target]


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
                if name.startswith("coat"):
                    rigid, q_target = _hang(rigid, q_target)
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
