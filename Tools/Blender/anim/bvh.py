"""Reads BVH motion capture (the ACCAD Open Motion Project takes and similar) and gives joint positions per frame.

The hierarchy's OFFSETs and each joint's rotation channels (applied in the order listed, e.g. Z then X then Y) are run
through forward kinematics. Positions come out in Blender space (Z up, metres): BVH is Y up, so (x, y, z) becomes
(x, -z, y), then the clip's heading turn and an optional left/right mirror are applied. End sites are named
"<joint>.end".
"""
import math

from mathutils import Matrix, Vector

AXES = {"X": "X", "Y": "Y", "Z": "Z"}
TO_BLENDER = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
MIRROR = Matrix(((-1, 0, 0), (0, 1, 0), (0, 0, 1)))


class Joint:
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent
        self.offset = Vector((0, 0, 0))
        self.channels = []
        self.end = None
        self.children = []


def mirror_name(name):
    if name.startswith("Left"):
        return "Right" + name[4:]
    if name.startswith("Right"):
        return "Left" + name[5:]
    return name


class BVH:
    def __init__(self, path, heading_deg=0.0, mirror=False, unit=0.01):
        self.joints = []
        self.frames = []
        self.frame_time = 1.0 / 30.0
        with open(path, encoding="latin-1") as f:
            tokens = f.read().split()
        i = 0
        stack = []
        cur = None
        while i < len(tokens):
            t = tokens[i]
            if t in ("ROOT", "JOINT"):
                cur = Joint(tokens[i + 1], stack[-1] if stack else None)
                if cur.parent:
                    cur.parent.children.append(cur)
                self.joints.append(cur)
                i += 2
            elif t == "End":
                # End Site { OFFSET x y z }
                j = i
                while tokens[j] != "OFFSET":
                    j += 1
                stack[-1].end = Vector([float(v) for v in tokens[j + 1:j + 4]])
                j += 4
                while tokens[j] != "}":
                    j += 1
                i = j + 1
            elif t == "{":
                stack.append(cur)
                i += 1
            elif t == "}":
                stack.pop()
                cur = stack[-1] if stack else None
                i += 1
            elif t == "OFFSET":
                cur.offset = Vector([float(v) for v in tokens[i + 1:i + 4]])
                i += 4
            elif t == "CHANNELS":
                n = int(tokens[i + 1])
                cur.channels = tokens[i + 2:i + 2 + n]
                i += 2 + n
            elif t == "MOTION":
                count = int(tokens[i + 2])
                self.frame_time = float(tokens[i + 5])
                width = sum(len(j.channels) for j in self.joints)
                data = tokens[i + 6:]
                self.frames = [[float(v) for v in data[k * width:(k + 1) * width]] for k in range(count)]
                break
            else:
                i += 1
        turn = Matrix.Rotation(math.radians(heading_deg), 3, "Z")
        self.space = turn @ TO_BLENDER
        if mirror:
            self.space = MIRROR @ self.space
        self.mirror = mirror
        self.unit = unit
        self.fps = 1.0 / self.frame_time
        self.count = len(self.frames)

    def points(self, k):
        """Joint and end-site positions of frame k: {name: Vector}, Blender space, metres."""
        return self.pose(k)[0]

    def pose(self, k):
        """Positions as points() gives them, and each joint's world rotation {name: 3x3} as the clip's space times the
        BVH rotation. Only products R_a @ R_b.inverted() are meaningful (with a mirror the space is improper)."""
        values = self.frames[k]
        world = {}
        out = {}
        rots = {}
        c = 0
        for j in self.joints:
            pos = Vector(j.offset)
            rot = Matrix.Identity(3)
            for ch in j.channels:
                v = values[c]
                c += 1
                kind = ch[0].upper()
                if ch.endswith("position"):
                    pos[{"X": 0, "Y": 1, "Z": 2}[kind]] = v if j.parent is None else pos[{"X": 0, "Y": 1, "Z": 2}[kind]] + v
                else:
                    rot = rot @ Matrix.Rotation(math.radians(v), 3, kind)
            local = Matrix.Translation(pos) @ rot.to_4x4()
            world[j.name] = (world[j.parent.name] @ local) if j.parent else local
            name = mirror_name(j.name) if self.mirror else j.name
            out[name] = self.space @ (world[j.name].translation * self.unit)
            rots[name] = self.space @ world[j.name].to_3x3()
            if j.end is not None:
                out[name + ".end"] = self.space @ ((world[j.name] @ Matrix.Translation(j.end)).translation * self.unit)
        return out, rots
