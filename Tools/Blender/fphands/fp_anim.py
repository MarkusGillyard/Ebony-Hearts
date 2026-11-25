"""Keys the first-person hand clips on the realistic hands' rig, as seen from the game's eye, and exports them.

Each clip (fp_clips.py) is a list of key poses at chosen frames (60 fps, on the game's frame data). A key gives, per
hand and in view space (centimetres, X forward, Y right, Z up, as the game's camera):
- p: where the middle knuckle is;
- f: the direction the knuckles point; n: the direction the palm faces;
- c: how closed the hand is (0 open, 1 a fist); s: how spread an open hand is; st: how straight the wrist is kept
  (a fist's knuckles in line with the forearm);
- pro: how far the shoulder blade carries the shoulder forward (degrees), for reach.
The segment into a key has an ease: "io" (in and out), "in" (speeding up), "out" (slowing down), "snap" (a strike's
release: most of the distance in its last frames), "lin".

Between keys the hand travels a smooth path through its keys (Catmull-Rom) on the segment's ease. Every frame is
then posed with hand and arm anatomy (the first-person hands study, 2026-11-23):
- the arm reaches the wrist with the elbow bending only on its hinge, its pole down and out;
- the hand is aimed (knuckles, palm), and a fist's wrist is straightened toward the forearm;
- the hand's turn about the forearm is shared along it by the two twist bones (as the radius rolls round the ulna);
- the fingers draw together and bend on their own hinges (92, 105 and 65 degrees at a full fist), a relaxed hand
  falls into a cascade, a hand closes from the little finger and opens from the index (a short wave), and the thumb
  wraps across the index and middle fingers or swings out when the hand opens.

Usage:
  blender -b -P fp_anim.py -- <FPHands_rig.blend> <out dir> <preview|export|both> [clip,clip,...]
Writes <out dir>/A_FPH_<Clip>.fbx (export) and <out dir>/preview/<clip>_sheet.png (preview).
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fp_clips  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
RIG_BLEND, OUT, MODE = args[0], args[1], args[2]
ONLY = set(args[3].split(",")) if len(args) > 3 and args[3] != "all" else None
FPS = 60

bpy.ops.wm.open_mainfile(filepath=RIG_BLEND)
for o in list(bpy.data.objects):
    if o.type not in ("ARMATURE", "MESH") or o.name.startswith("Sphere"):
        bpy.data.objects.remove(o, do_unlink=True)
rig = bpy.data.objects["FPHands"]
mesh = bpy.data.objects["FPHands_Mesh"]
sc = bpy.context.scene
sc.render.fps = FPS
REST = {b.name: b.matrix_local.copy() for b in rig.data.bones}


def T(name):
    return REST[name].translation.copy()


HEAD = T("head")
EYE = HEAD + Vector((0.0, -0.04, -0.01))   # the game puts the head bone 4 cm behind and 1 cm above the eye
AHEAD = Vector((0.0, -1.0, 0.0))            # the model faces -Y


def VP(v):
    """View-space centimetres (X forward, Y right, Z up) to the rig's space (metres)."""
    return EYE + Vector((-v[1], -v[0], v[2])) / 100.0


def VD(v):
    return Vector((-v[1], -v[0], v[2])).normalized()


def basis(x, y):
    x = x.normalized()
    y = (y - x * y.dot(x)).normalized()
    m = Matrix((x, y, x.cross(y))).transposed()
    return m


def rot4(r3, pivot):
    return Matrix.Translation(pivot) @ r3.to_4x4() @ Matrix.Translation(-pivot)


FINGERS = ["index", "middle", "ring", "pinky"]


class HandRest:
    def __init__(self, s):
        self.s = s
        self.wrist = T(f"hand_{s}")
        self.knuckle = T(f"middle_01_{s}")
        self.K = (self.knuckle - self.wrist).normalized()
        self.lat = (T(f"pinky_01_{s}") - T(f"index_01_{s}")).normalized()
        hd = (T(f"middle_03_{s}") - self.wrist).normalized()
        n = hd.cross(self.lat).normalized()
        if n.dot(T(f"thumb_03_{s}") - self.wrist) < 0:
            n = -n
        self.N = n
        self.flex = 1.0 if self.lat.cross(hd).dot(n) >= 0 else -1.0
        self.spread_sign = 1.0 if n.cross(hd).dot(self.lat) >= 0 else -1.0
        tdir = (T(f"thumb_03_{s}") - T(f"thumb_01_{s}")).normalized()
        self.sweep_sign = 1.0 if n.cross(tdir).dot(self.lat) >= 0 else -1.0
        across = (self.K - n * self.K.dot(n)).normalized()
        conv = [1.0, 0.3, -0.3, -1.0]
        self.d0, self.draw_in = [], []
        for i, f in enumerate(FINGERS):
            d = T(f"{f}_02_{s}") - T(f"{f}_01_{s}")
            d = (d - n * d.dot(n)).normalized()
            want = Quaternion(n, math.radians(6.0 * conv[i] * self.spread_sign)) @ across
            self.d0.append(d)
            self.draw_in.append(d.rotation_difference(want))
        self.shoulder = T(f"upperarm_{s}")
        self.elbow = T(f"lowerarm_{s}")
        self.clav = T(f"clavicle_{s}")
        self.u0 = (self.elbow - self.shoulder).normalized()
        self.l0 = (self.wrist - self.elbow).normalized()
        self.h0u = self.u0.cross(AHEAD).normalized()
        self.h0l = self.l0.cross(AHEAD).normalized()
        self.A = (self.elbow - self.shoulder).length
        self.B = (self.wrist - self.elbow).length
        self.HL = (self.knuckle - self.wrist).length
        self.side = -1.0 if s == "l" else 1.0   # view Y of this hand's side


HANDS = {"l": HandRest("l"), "r": HandRest("r")}
JOINT = (92.0, 105.0, 65.0)
FAN = (-13.0, -2.0, 8.0, 18.0)
THUMB_WANT = ((0.75, 0.60, 0.18), (0.28, 0.45, 0.85), (-0.12, 0.32, 0.95))


def finger_mats(h, curls, spread):
    """The hand's digits posed in the rest frame: name -> 4x4 (rig space, before the hand's own move)."""
    out = {}
    for i, f in enumerate(FINGERS):
        names = [f"{f}_0{k}_{h.s}" for k in (1, 2, 3)]
        mats = [REST[n].copy() for n in names]
        ci = curls[i]
        draw = Quaternion().slerp(h.draw_in[i], min(1.0, max(0.0, ci * 1.3)) * (1.0 - min(1.0, spread)))
        fan = Quaternion(h.N, math.radians(FAN[i] * spread * h.spread_sign))
        base = fan @ draw
        hinge = (base @ h.d0[i]).cross(h.N).normalized()
        if hinge.dot(h.lat) < 0:
            hinge = -hinge
        ce = ci * (1.0 + 0.04 * i) + 0.05 * i * (1.0 - min(1.0, ci)) * (1.0 - spread)
        for k in range(3):
            r = Quaternion(hinge, math.radians(JOINT[k] * ce * h.flex))
            if k == 0:
                r = r @ base
            m = rot4(r.to_matrix(), mats[k].translation)
            for j in range(k, 3):
                mats[j] = m @ mats[j]
        out.update(zip(names, mats))
    # Thumb.
    c = max(0.0, min(1.0, sum(curls) / 4.0))
    names = [f"thumb_0{k}_{h.s}" for k in (1, 2, 3)]
    mats = [REST[n].copy() for n in names]
    pts = [T(n) for n in names]
    rest_dir = [(pts[1] - pts[0]).normalized(), (pts[2] - pts[1]).normalized(), (pts[2] - pts[1]).normalized()]
    above = Quaternion()
    if spread > 0.01:
        above = Quaternion(h.N, math.radians(-24.0 * spread * h.sweep_sign))
        m = rot4(above.to_matrix(), mats[0].translation)
        mats = [m @ x for x in mats]
    for k in range(3):
        w = THUMB_WANT[k]
        want = (h.K * w[0] + h.N * w[1] + h.lat * w[2]).normalized()
        q = Quaternion().slerp((above @ rest_dir[k]).rotation_difference(want), c)
        m = rot4(q.to_matrix(), mats[k].translation)
        for j in range(k, 3):
            mats[j] = m @ mats[j]
        above = q @ above
    out.update(zip(names, mats))
    return out


def twist_of(q, axis):
    v = Vector((q.x, q.y, q.z))
    along = v.dot(axis)
    t = Quaternion((q.w, axis.x * along, axis.y * along, axis.z * along))
    if t.magnitude < 1e-9:
        return 0.0
    t.normalize()
    ang = 2.0 * math.atan2(Vector((t.x, t.y, t.z)).length, t.w)
    if Vector((t.x, t.y, t.z)).dot(axis) < 0:
        ang = -ang
    return math.atan2(math.sin(ang), math.cos(ang))


def pose_arm(h, st, mats):
    """One arm posed from its state (view space); fills mats with rig-space 4x4s."""
    # The shoulder blade carries the shoulder forward (protraction) about the vertical at the clavicle's root.
    pro = math.radians(st["pro"]) * (1.0 if h.s == "r" else -1.0)
    rc = Matrix.Rotation(pro, 3, "Z")
    mats[f"clavicle_{h.s}"] = rot4(rc, h.clav) @ REST[f"clavicle_{h.s}"]
    S = h.clav + rc @ (h.shoulder - h.clav)
    u0, h0u = rc @ h.u0, rc @ h.h0u
    # The hand: knuckle position and aim (rest knuckle line and palm turned to the wanted ones).
    fwd, palm = VD(st["f"]), VD(st["n"])
    R_aim = basis(fwd, palm) @ basis(h.K, h.N).inverted()
    knuckle = VP(st["p"])
    W = knuckle - (R_aim @ h.K) * h.HL
    # Two-bone reach with the elbow on its hinge.
    pole = VD((0.0, h.side * 0.55, -1.0))
    to = W - S
    d = max(abs(h.A - h.B) + 0.001, min(to.length, h.A + h.B - 0.0005))
    dr = to.normalized()
    pp = (pole - dr * pole.dot(dr)).normalized()
    x = (h.A * h.A - h.B * h.B + d * d) / (2.0 * d)
    hh = math.sqrt(max(0.0, h.A * h.A - x * x))
    E = S + dr * x + pp * hh
    W2 = S + dr * d
    hinge = pp.cross(dr).normalized()
    R_u = basis(E - S, hinge) @ basis(u0, h0u).inverted()
    R_u = R_u @ rc
    R_l = basis(W2 - E, hinge) @ basis(h.l0, h.h0l).inverted()
    mats[f"upperarm_{h.s}"] = Matrix.Translation(S) @ (R_u @ REST[f"upperarm_{h.s}"].to_3x3()).to_4x4()
    mats[f"lowerarm_{h.s}"] = Matrix.Translation(E) @ (R_l @ REST[f"lowerarm_{h.s}"].to_3x3()).to_4x4()
    # A closed fist keeps its wrist straight: the knuckle line turned toward the forearm's line.
    R_h = R_aim
    fore = (W2 - E).normalized()
    if st["st"] > 0.001:
        q = (R_h @ h.K).rotation_difference(fore)
        R_h = Quaternion().slerp(q, st["st"]).to_matrix() @ R_h
    mats[f"hand_{h.s}"] = Matrix.Translation(W2) @ (R_h @ REST[f"hand_{h.s}"].to_3x3()).to_4x4()
    # The forearm's twist bones share the hand's turn about the forearm.
    turn = (R_h @ R_l.inverted()).to_quaternion()
    ang = twist_of(turn, fore)
    for name, share in ((f"lowerarm_twist_01_{h.s}", 0.5), (f"lowerarm_twist_02_{h.s}", 0.85)):
        head = E + R_l @ (T(name) - h.elbow)
        r = Matrix.Rotation(ang * share, 3, fore) @ R_l @ REST[name].to_3x3()
        mats[name] = Matrix.Translation(head) @ r.to_4x4()
    # Digits, carried by the hand.
    carry = Matrix.Translation(W2) @ R_h.to_4x4() @ Matrix.Translation(-h.wrist)
    for n, m in finger_mats(h, st["curls"], st["s"]).items():
        mats[n] = carry @ m
    return W2


# --- Key interpolation --------------------------------------------------------------------------------------------------
def ease(kind, u):
    u = max(0.0, min(1.0, u))
    if kind == "lin":
        return u
    if kind == "in":
        return u * u
    if kind == "out":
        return 1.0 - (1.0 - u) * (1.0 - u)
    if kind == "snap":
        return u * u * u * (0.35 + 0.65 * u) / 1.0 if u < 1.0 else 1.0
    return u * u * (3.0 - 2.0 * u)


CHANNELS = ("p", "f", "n", "c", "s", "st", "pro")
DEFAULTS = {"s": 0.0, "st": 0.0, "pro": 0.0}


def filled(keys, side):
    """Each key's full state for one hand (missing channels carry the previous key's)."""
    out, last = [], {}
    for k in keys:
        st = dict(last)
        for ch in CHANNELS:
            if ch in k.get(side, {}):
                st[ch] = k[side][ch]
        for ch, v in DEFAULTS.items():
            st.setdefault(ch, v)
        out.append((k["t"], k.get("e", "io"), st))
        last = st
    return out


def catmull(p0, p1, p2, p3, u):
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


def sample(clip, side, t):
    ks = filled(clip["keys"], side)
    n = len(ks)
    loop = clip.get("loop", False)
    if t <= ks[0][0]:
        i = 0
    elif t >= ks[-1][0]:
        i = n - 2
    else:
        i = max(j for j in range(n - 1) if ks[j][0] <= t)
    t0, _, a = ks[i]
    t1, e, b = ks[i + 1]
    u = ease(e, (t - t0) / max(1e-6, t1 - t0))

    def nb(j):
        if 0 <= j < n:
            return ks[j][2]
        if loop:
            return ks[(j + (n - 1)) % (n - 1)][2] if j < 0 else ks[(j - (n - 1)) % (n - 1)][2]
        return ks[max(0, min(n - 1, j))][2]

    st = {}
    P = [Vector(nb(i + o)["p"]) for o in (-1, 0, 1, 2)]
    st["p"] = catmull(*P, u)
    for ch in ("f", "n"):
        va, vb = Vector(a[ch]).normalized(), Vector(b[ch]).normalized()
        st[ch] = (va.lerp(vb, u)).normalized()
    for ch in ("c", "s", "st", "pro"):
        st[ch] = a[ch] + (b[ch] - a[ch]) * u
    return st


def state_at(clip, side, t):
    st = sample(clip, side, t)
    # The finger wave: a closing hand leads with the little finger, an opening one with the index.
    c_prev = sample(clip, side, max(0.0, t - 1.0))["c"]
    closing = st["c"] >= c_prev
    curls = []
    for i in range(4):
        lag = 0.9 * ((3 - i) if closing else i)
        curls.append(sample(clip, side, max(clip["keys"][0]["t"], t - lag))["c"])
    st["curls"] = curls
    return st


def pose_frame(clip, t):
    mats = {}
    for side in ("l", "r"):
        pose_arm(HANDS[side], state_at(clip, side, t), mats)
    return mats


ORDER = [b.name for b in rig.data.bones]   # parents come before children in Blender's list


def apply(mats):
    for name in ORDER:
        pb = rig.pose.bones[name]
        pb.matrix = mats.get(name, REST[name])
        bpy.context.view_layer.update()


def key_clip(name, clip):
    act = bpy.data.actions.new(f"A_FPH_{name}")
    rig.animation_data_create()
    rig.animation_data.action = act
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    length = clip["keys"][-1]["t"]
    for fr in range(0, int(length) + 1):
        apply(pose_frame(clip, float(fr)))
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=fr)
            pb.keyframe_insert("location", frame=fr)
    return act, int(length)


# --- Preview from the game's eye -----------------------------------------------------------------------------------------
def setup_preview():
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 640, 360
    mat = mesh.data.materials[0] if mesh.data.materials else bpy.data.materials.new("skin")
    mat.diffuse_color = (0.72, 0.52, 0.42, 1.0)
    world = bpy.data.worlds.new("w")
    world.color = (0.08, 0.08, 0.10)
    sc.world = world
    cam = bpy.data.cameras.new("eye")
    cam.sensor_fit = "HORIZONTAL"
    cam.angle = math.radians(72.0)   # the game's first-person field of view for the arms
    cam.clip_start = 0.01
    co = bpy.data.objects.new("eye", cam)
    sc.collection.objects.link(co)
    co.location = EYE
    co.rotation_euler = (math.radians(90.0), 0.0, math.radians(180.0))
    sc.camera = co
    # A floor and a target post for scale.
    bpy.ops.mesh.primitive_plane_add(size=6.0, location=(0.0, 0.0, 0.0))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=1.6, location=(0.0, -1.1, 0.8))


def preview(name, clip, length):
    import subprocess
    pdir = os.path.join(OUT, "preview")
    os.makedirs(pdir, exist_ok=True)
    frames = clip.get("sheet") or list(range(0, length + 1, max(1, length // 11)))
    paths = []
    for fr in frames:
        sc.frame_set(fr)
        p = os.path.join(pdir, f"{name}_{fr:03d}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        paths.append(p)
    return paths


def export(name, act, length):
    rig.animation_data.action = act
    sc.frame_start, sc.frame_end = 0, length
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = rig
    out = os.path.join(OUT, f"A_FPH_{name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=out, use_selection=True, object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
        axis_forward="Y", axis_up="Z", bake_space_transform=False,
        use_mesh_modifiers=True, mesh_smooth_type="FACE", add_leaf_bones=False, primary_bone_axis="Y",
        secondary_bone_axis="X", use_armature_deform_only=False, armature_nodetype="NULL",
        bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
        path_mode="STRIP", embed_textures=False, colors_type="NONE")
    print(f"FPANIM wrote {out} frames=0..{length}")


os.makedirs(OUT, exist_ok=True)
if MODE in ("preview", "both"):
    setup_preview()
for name, clip in fp_clips.CLIPS.items():
    if ONLY and name not in ONLY:
        continue
    act, length = key_clip(name, clip)
    print(f"FPANIM keyed {name} 0..{length}")
    if MODE in ("preview", "both"):
        preview(name, clip, length)
    if MODE in ("export", "both"):
        export(name, act, length)
