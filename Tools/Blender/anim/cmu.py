"""Reads CMU Graphics Lab motion capture: an ASF skeleton and its AMC motion (Acclaim format, 120 fps).

Forward kinematics follows the Acclaim convention: each bone has a rest axis frame C (Euler XYZ, degrees), motion
rotations R are Euler XYZ in that frame, and a bone's world rotation is parent @ C @ R @ C^-1. At rest every bone's world
rotation is the identity and the skeleton stands in the ASF's T-pose, so a rotation here is also the bone's change from
rest. Positions are metres in CMU world space (Y up).
"""
import math

from mathutils import Euler, Matrix, Vector

INCH = 0.0254


def _euler(values_deg, order="XYZ"):
    return Euler([math.radians(v) for v in values_deg], order).to_matrix()


class Bone:
    def __init__(self, name):
        self.name = name
        self.direction = Vector((0, 0, 0))
        self.length = 0.0
        self.C = Matrix.Identity(3)
        self.Cinv = Matrix.Identity(3)
        self.dof = []
        self.parent = None
        self.children = []


class Skeleton:
    def __init__(self, path):
        self.bones = {}
        self.unit = 0.45
        self.root_order = ["TX", "TY", "TZ", "RX", "RY", "RZ"]
        self.root_C = Matrix.Identity(3)
        root = Bone("root")
        self.bones["root"] = root
        section = None
        cur = None
        with open(path, encoding="latin-1") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith(":"):
                    words = line.split()
                    section = words[0][1:]
                    continue
                words = line.split()
                if section == "units" and words[0] == "length":
                    self.unit = float(words[1])
                elif section == "root":
                    if words[0] == "order":
                        self.root_order = [w.upper() for w in words[1:]]
                    elif words[0] == "orientation":
                        self.root_C = _euler([float(w) for w in words[1:4]])
                elif section == "bonedata":
                    if words[0] == "begin":
                        cur = None
                    elif words[0] == "name":
                        cur = Bone(words[1])
                        self.bones[cur.name] = cur
                    elif cur is None or words[0] == "end":
                        continue
                    elif words[0] == "direction":
                        cur.direction = Vector([float(w) for w in words[1:4]]).normalized()
                    elif words[0] == "length":
                        cur.length = float(words[1]) / self.unit * INCH
                    elif words[0] == "axis":
                        cur.C = _euler([float(w) for w in words[1:4]], words[4] if len(words) > 4 else "XYZ")
                        cur.Cinv = cur.C.inverted()
                    elif words[0] == "dof":
                        cur.dof = [w.lower() for w in words[1:]]
                elif section == "hierarchy":
                    if words[0] in ("begin", "end"):
                        continue
                    parent = self.bones[words[0]]
                    for child in words[1:]:
                        self.bones[child].parent = parent
                        parent.children.append(self.bones[child])
        root.Cinv = self.root_C.inverted()
        root.C = self.root_C
        self.order = []
        stack = [root]
        while stack:
            b = stack.pop(0)
            self.order.append(b)
            stack.extend(b.children)

    def rest_positions(self):
        """Joint positions of the T-pose: name -> (start, end), metres, root at the origin."""
        out = {"root": (Vector((0, 0, 0)), Vector((0, 0, 0)))}
        for b in self.order[1:]:
            start = out[b.parent.name][1]
            out[b.name] = (start, start + b.direction * b.length)
        return out


def read_amc(path):
    """List of frames, each {bone: [values...]} in file order."""
    frames = []
    cur = None
    with open(path, encoding="latin-1") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith(":"):
                continue
            words = line.split()
            if len(words) == 1 and words[0].isdigit():
                cur = {}
                frames.append(cur)
                continue
            if cur is not None:
                cur[words[0]] = [float(w) for w in words[1:]]
    return frames


def pose(skel, frame):
    """World rotation (3x3, change from rest) and joint positions for one AMC frame.

    Returns (rot, start, end): dicts keyed by bone name; root's start/end are both the root position."""
    rot, start, end = {}, {}, {}
    root = skel.bones["root"]
    vals = dict(zip(skel.root_order, frame.get("root", [0.0] * 6)))
    pos = Vector((vals.get("TX", 0.0), vals.get("TY", 0.0), vals.get("TZ", 0.0))) / skel.unit * INCH
    r = _euler([vals.get("RX", 0.0), vals.get("RY", 0.0), vals.get("RZ", 0.0)])
    rot["root"] = root.C @ r @ root.Cinv
    start["root"] = end["root"] = pos
    for b in skel.order[1:]:
        angles = {"rx": 0.0, "ry": 0.0, "rz": 0.0}
        for axis, value in zip(b.dof, frame.get(b.name, [])):
            angles[axis] = value
        m = rot[b.parent.name] @ b.C @ _euler([angles["rx"], angles["ry"], angles["rz"]]) @ b.Cinv
        rot[b.name] = m
        start[b.name] = end[b.parent.name]
        end[b.name] = start[b.name] + m @ (b.direction * b.length)
    return rot, start, end
