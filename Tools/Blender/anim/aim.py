"""Position-aimed retargeting: drives the game_engine rig from captured joint positions (BVH or any source that gives
points), so the source skeleton's rest pose does not matter.

Each target bone is aimed along the matching source segment, and its twist comes from a side reference built the same
way on both skeletons: the hip line for the pelvis, a blend of hip and shoulder lines up the spine, the elbow or knee
hinge for limbs. The rest correction (target rest frame -> target bone rest rotation) is measured once on the target's
own rest skeleton with the same rules, so a captured frame maps onto each bone the same way the rest pose does.
"""
import math

from mathutils import Matrix, Quaternion, Vector

# target bone: (from joint, to joint, side rule)
# The spine pairs joints at matching heights on both skeletons (ACCAD's ToSpine sits beside the hips, not above them,
# so it is not used): hips to mid-spine for the pelvis and lowest spine bone, then mid-spine, chest and neck.
RULES = {
    "pelvis": ("Hips", "Spine", "hips"),
    "spine_01": ("Hips", "Spine", "spine0"),
    "spine_02": ("Spine", "Spine1", "spine1"),
    "spine_03": ("Spine1", "Neck", "shoulders"),
    "neck_01": ("Neck", "Head", "shoulders"),
    "head": ("Head", "Head.end", "shoulders"),
}
for _s, _S in (("l", "Left"), ("r", "Right")):
    RULES.update({
        f"clavicle_{_s}": (f"{_S}Shoulder", f"{_S}Arm", "chest_up"),
        f"upperarm_{_s}": (f"{_S}Arm", f"{_S}ForeArm", f"elbow_{_s}"),
        f"lowerarm_{_s}": (f"{_S}ForeArm", f"{_S}Hand", f"elbow_{_s}"),
        f"hand_{_s}": (f"{_S}Hand", f"{_S}Hand.end", f"elbow_{_s}"),
        f"thigh_{_s}": (f"{_S}UpLeg", f"{_S}Leg", f"knee_{_s}"),
        f"calf_{_s}": (f"{_S}Leg", f"{_S}Foot", f"knee_{_s}"),
        f"foot_{_s}": (f"{_S}Foot", f"{_S}ToeBase", f"knee_{_s}"),
        f"ball_{_s}": (f"{_S}ToeBase", f"{_S}ToeBase.end", f"knee_{_s}"),
    })

# The same joints on the target rig: (bone head or tail).
TARGET_POINTS = {"Hips": ("pelvis", "head"), "ToSpine": ("pelvis", "tail"), "Spine": ("spine_01", "tail"),
                 "Spine1": ("spine_02", "tail"), "Neck": ("neck_01", "head"), "Head": ("head", "head"), "Head.end": ("head", "tail")}
for _s, _S in (("l", "Left"), ("r", "Right")):
    TARGET_POINTS.update({
        f"{_S}Shoulder": (f"clavicle_{_s}", "head"), f"{_S}Arm": (f"upperarm_{_s}", "head"), f"{_S}ForeArm": (f"lowerarm_{_s}", "head"),
        f"{_S}Hand": (f"hand_{_s}", "head"), f"{_S}Hand.end": (f"hand_{_s}", "tail"), f"{_S}UpLeg": (f"thigh_{_s}", "head"),
        f"{_S}Leg": (f"calf_{_s}", "head"), f"{_S}Foot": (f"foot_{_s}", "head"), f"{_S}ToeBase": (f"ball_{_s}", "head"),
        f"{_S}ToeBase.end": (f"ball_{_s}", "tail"),
    })

# The source joint whose rotation carries each target bone (aim joint names; "SpineLow" is the bone between the hips
# and the first spine joint: ACCAD's ToSpine, Mixamo's Spine).
OWNER = {"pelvis": "Hips", "spine_01": "SpineLow", "spine_02": "Spine", "spine_03": "Spine1", "neck_01": "Neck",
         "head": "Head"}
for _s, _S in (("l", "Left"), ("r", "Right")):
    OWNER.update({f"clavicle_{_s}": f"{_S}Shoulder", f"upperarm_{_s}": f"{_S}Arm", f"lowerarm_{_s}": f"{_S}ForeArm",
                  f"hand_{_s}": f"{_S}Hand", f"thigh_{_s}": f"{_S}UpLeg", f"calf_{_s}": f"{_S}Leg",
                  f"foot_{_s}": f"{_S}Foot", f"ball_{_s}": f"{_S}ToeBase"})

STRAIGHT = 0.12   # below this sine of the joint angle a limb counts as straight; its hinge comes from the last frame

# Bones whose joints sit in different places on different skeletons (a source's shoulder joint near the neck makes its
# collarbone slope steeply; neck and head joints vary too). Matching their directions would copy that difference onto
# the target, so with a neutral pose these bones take the source's change from neutral, applied to the target's rest.
CALIBRATED = ("clavicle_l", "clavicle_r", "neck_01", "head")


def frame(direction, side):
    """Orthonormal frame with Y along `direction` and X toward `side` (columns X, Y, Z)."""
    y = direction.normalized()
    x = side - y * side.dot(y)
    if x.length < 1e-6:
        x = Vector((1, 0, 0)) - y * y.x
    x.normalize()
    z = x.cross(y)
    return Matrix((x, y, z)).transposed()


class Sides:
    """Side references for one pose, with hinge continuity across frames."""

    def __init__(self):
        self.last = {}

    def compute(self, P, rest=False):
        hips = (P["LeftUpLeg"] - P["RightUpLeg"]).normalized()
        shoulders = (P["LeftArm"] - P["RightArm"]).normalized()
        out = {"hips": hips, "shoulders": shoulders, "spine0": hips.lerp(shoulders, 0.33), "spine1": hips.lerp(shoulders, 0.67),
               "chest_up": (P["Neck"] - P["Spine1"]).normalized()}
        for s, S in (("l", "Left"), ("r", "Right")):
            upper = P[f"{S}ForeArm"] - P[f"{S}Arm"]
            fore = P[f"{S}Hand"] - P[f"{S}ForeArm"]
            h = upper.normalized().cross(fore.normalized())
            key = f"elbow_{s}"
            if h.length > STRAIGHT:
                out[key] = h.normalized()
            else:
                out[key] = self.last.get(key, out["chest_up"])
            self.last[key] = out[key]
            thigh = P[f"{S}Leg"] - P[f"{S}UpLeg"]
            calf = P[f"{S}Foot"] - P[f"{S}Leg"]
            k = thigh.normalized().cross(calf.normalized())
            key = f"knee_{s}"
            if rest or k.length < STRAIGHT:
                out[key] = hips   # a straight leg's hinge lines up with the hips
            else:
                out[key] = k.normalized() if k.dot(hips) >= 0 else -k.normalized()
        return out


class AimRetarget:
    def __init__(self, arm, neutral=None):
        """neutral: the source's joint points in a relaxed standing pose, for the CALIBRATED bones."""
        bones = arm.data.bones
        P = {}
        for joint, (bone, end) in TARGET_POINTS.items():
            b = bones[bone]
            P[joint] = (b.head_local if end == "head" else b.tail_local).copy()
        self.target_points = P
        self.rest_rot = {b.name: b.matrix_local.to_3x3() for b in bones}
        sides = Sides().compute(P, rest=True)
        self.correction = {}
        for bone, (a, b, side) in RULES.items():
            if bone not in bones:
                continue
            F = frame(P[b] - P[a], sides[side])
            self.correction[bone] = F.transposed() @ bones[bone].matrix_local.to_3x3()
        if neutral is not None:
            s0 = Sides().compute(neutral, rest=True)
            for bone in CALIBRATED:
                if bone in self.correction:
                    a, b, side = RULES[bone]
                    self.correction[bone] = frame(neutral[b] - neutral[a], s0[side]).transposed() @ bones[bone].matrix_local.to_3x3()
        self.sides = Sides()

    def carry(self, neutral, neutral_rot):
        """Rotation transfer for sources that record joint rotations (BVH, FBX). Each target bone takes the frame the
        aim rules give it on the source's neutral pose (joint points `neutral`), and from there turns exactly as its
        source joint has turned since that pose (`neutral_rot`, world rotations by aim joint name). So bones point as
        the aim would point them, but keep the performer's own twist: wrists, forearms, the head turning on the neck,
        the feet rolling. The aim rebuilds twist from hinge planes and loses those."""
        def still(P):
            # A nearly straight arm in a reference pose has no reliable hinge (a T-pose elbow can bend a degree either
            # way), so both skeletons' reference frames take the chest's up direction there instead.
            sides = Sides().compute(P, rest=True)
            for s in ("l", "r"):
                sides[f"elbow_{s}"] = sides["chest_up"]
            return sides
        ns, ts = still(neutral), still(self.target_points)
        self.basis = {}
        for bone, C in self.correction.items():
            a, b, side = RULES[bone]
            if bone in CALIBRATED:
                self.basis[bone] = frame(neutral[b] - neutral[a], ns[side]) @ C
            else:
                T = self.target_points
                C = frame(T[b] - T[a], ts[side]).transposed() @ self.rest_rot[bone]
                self.basis[bone] = frame(neutral[b] - neutral[a], ns[side]) @ C
        self.neutral_inv = {k: m.inverted() for k, m in neutral_rot.items()}

    def carried(self, R, P):
        """World rotation (quaternion) of every mapped target bone for captured joint rotations R and points P (see
        carry). The elbow is a hinge, and the two skeletons' arms rest with their forearms rolled differently, so the
        upper arm and forearm keep the aim's hinge-plane roll. The hand points where the aim points it and turns about
        its own axis as the performer's hand turned from their forearm (the forearm rotation the aim loses)."""
        out = {bone: (R[OWNER[bone]] @ self.neutral_inv[OWNER[bone]] @ B).to_quaternion() for bone, B in self.basis.items()}
        aimed = self.rotations(P)
        for s in ("l", "r"):
            ua, la, hd = f"upperarm_{s}", f"lowerarm_{s}", f"hand_{s}"
            if hd in out:
                h = aimed[la] @ out[la].inverted() @ out[hd]
                y = Vector((0.0, 1.0, 0.0))
                out[hd] = (h @ y).rotation_difference(aimed[hd] @ y) @ h
            out[ua], out[la] = aimed[ua], aimed[la]
        return out

    def rotations(self, P):
        """World rotation (quaternion) of every mapped target bone for captured points P."""
        sides = self.sides.compute(P)
        out = {}
        for bone, C in self.correction.items():
            a, b, side = RULES[bone]
            out[bone] = (frame(P[b] - P[a], sides[side]) @ C).to_quaternion()
        return out
