"""Authors, reviews and exports every animation for one fighter.

Run: bin/blender.sh anim Tools/Blender/anim/build_anims.py -- --blend <Char.blend> --char wren|ashka
         --data Content/Data/Fighters/<char>.json --out <dir> [--only L1,H] [--review] [--no-export]
Writes <out>/A_<Char>_<Key>.fbx (armature + one action each) and, with --review, contact sheets of each animation's
key frames to <out>/review/.
"""
import argparse
import json
import math
import os
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import animlib as A  # noqa: E402
import mocap as M  # noqa: E402
import moves  # noqa: E402
import preview  # noqa: E402
import throws  # noqa: E402


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True)
    p.add_argument("--char", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--only", default="")
    p.add_argument("--review", action="store_true")
    p.add_argument("--review-frames", default="", help="with --review: comma-separated frames, or 'all' (default: key frames)")
    p.add_argument("--no-export", action="store_true")
    p.add_argument("--height", type=float, default=0.0)
    p.add_argument("--victim-blend", default="")
    p.add_argument("--victim-char", default="")
    p.add_argument("--victim-height", type=float, default=0.0)
    p.add_argument("--skip-attacker", action="store_true", help="only export victim animations")
    return p.parse_args(argv)


def append_armature(blend, tag):
    """Appends the armature (and its meshes, for review) from another character file; returns the armature."""
    if os.path.abspath(blend) == os.path.abspath(bpy.data.filepath):
        # Mirror matches append from the open file itself; Blender only loads from another file, so use a copy.
        copy = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"victim_copy_{os.getpid()}.blend")
        shutil.copyfile(blend, copy)
        blend = copy
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.objects = list(src.objects)
    arm = None
    for o in dst.objects:
        if o is None:
            continue
        bpy.context.scene.collection.objects.link(o)
        if o.type == "ARMATURE":
            arm = o
    arm.name = f"Armature_{tag}"
    return arm


def build_throws(a, data):
    """Paired thrower/victim authoring for each of the thrower's throws against one victim character.

    Both are authored in the thrower's space, the victim standing at holdX in front of it and turned to face it. The
    game shows each fighter in its own space, opened toward the camera and mirrored when facing left, so the victim's
    animation is moved into the space it is drawn in (stage_transforms) and each body ends exactly where the
    animation after the throw starts, as drawn after the landing."""
    victim_arm = append_armature(a.victim_blend, "victim")
    thrower_arm = bpy.data.objects["Armature"]
    t_rig = A.Rig(thrower_arm, a.char, a.height or None)
    v_rig = A.Rig(victim_arm, "victim_" + a.victim_char, a.victim_height or None)
    t_prefix = "A_" + a.char.capitalize() + "_"
    v_prefix = "A_" + a.victim_char.capitalize() + "_"
    grab_pose = grab_connect_pose(a, data, t_rig)
    victim_idle = load_idle_pose(os.path.join(os.path.dirname(os.path.normpath(a.out)), a.victim_char, "idle_pose.json"))
    for td in data["throws"]:
        build = throws.THROWS[(a.char, td["id"])]
        t_keys, v_keys = build(throws.stance_of(a.victim_char), td)
        hold = td["holdX"] / 100.0
        total = td["duration"]
        cap = captured_throws().get(td["id"])
        # Victim stands at holdX in front of the thrower (thrower faces -Y), facing back toward it.
        victim_arm.matrix_world = Matrix.Translation((0.0, -hold, 0.0)) @ Matrix.Rotation(math.pi, 4, "Z")
        ends, shown_v, to_own = stage_transforms(a, td, t_rig, v_rig)
        for rig in (t_rig, v_rig):
            A.mute_constraints(rig, False)
            rig.reset()
        t_act = bpy.data.actions.new(t_prefix + td["attackerAnim"])
        v_act = bpy.data.actions.new(v_prefix + td["victimAnim"])
        thrower_arm.animation_data_create()
        victim_arm.animation_data_create()
        thrower_arm.animation_data.action = t_act
        victim_arm.animation_data.action = v_act
        if cap:
            t_poses, v_poses = capture_throw(a, td, cap, t_rig, v_rig, ends)
            thrower_arm.animation_data.action = t_act
            victim_arm.animation_data.action = v_act
        else:
            A.author([(t_rig, t_keys, None), (v_rig, v_keys, None)], total)
            A.mute_constraints(t_rig, True)
            A.mute_constraints(v_rig, True)
            t_poses, v_poses = read_poses(thrower_arm, total), read_poses(victim_arm, total)
            # The scripted keys end on the old landing poses; settle into the exact ones.
            for poses, arm, n_end in ((t_poses, thrower_arm, 14), (v_poses, victim_arm, 12)):
                for i in range(n_end):
                    k = total - n_end + i
                    poses[k] = M.blend_pose(poses[k], ends[arm.name], A.ease("smooth", (i + 1) / n_end))
        # The throw starts where the grab connects (its first active frame), so the thrower eases out of the grab's
        # own pose instead of jumping to the throw's first frame (65 cm for Wren's captured double-leg).
        n_in = min(8, total)
        for i in range(n_in):
            t_poses[i] = M.blend_pose(grab_pose, t_poses[i], A.ease("smooth", i / n_in))
        v_poses = [transform_pose(victim_arm, pose, to_own) for pose in v_poses]
        # The grabbed fighter was standing in its idle (or guard): ease out of the idle's first pose instead of
        # jumping to the throw's first frame (50-86 cm, the drawn-space stance has the feet the other way round).
        if victim_idle:
            for i in range(min(10, total)):
                v_poses[i] = M.blend_pose(victim_idle, v_poses[i], A.ease("smooth", i / 10))
        report_handoff(td, t_rig, v_rig, t_poses[-1], v_poses[-1], shown_v)
        A.mute_constraints(t_rig, True)
        A.mute_constraints(v_rig, True)
        for arm, act, poses in ((thrower_arm, t_act, t_poses), (victim_arm, v_act, v_poses)):
            # Fresh action under the same name (the scripted build keyed the old one).
            name = act.name
            act.name = name + "_authored"
            fresh = bpy.data.actions.new(name)
            arm.animation_data.action = fresh
            bpy.data.actions.remove(act)
            for frame, pose in enumerate(poses, start=1):
                M.key_pose(arm, pose, frame)
            M.bake_tracked(arm, total)
        t_act, v_act = thrower_arm.animation_data.action, victim_arm.animation_data.action
        # Hair and coat in each body's own space (unmirrored: the springs are symmetric).
        victim_arm.matrix_world = Matrix.Identity(4)
        for rig, blend in ((t_rig, a.blend), (v_rig, a.victim_blend)):
            ch = load_chains(blend, rig.arm)
            if ch:
                A.bake_secondary(rig, ch, total, False)
        print(f"BUILDANIM {t_act.name} + {v_act.name} frames={total}")
        # Review: the victim's own space where the game draws it, seen from the thrower's.
        victim_arm.matrix_world = shown_v
        if a.review:
            preview.setup_camera(distance=5.0)
            if a.review_frames:
                frames = [f for f in (int(x) for x in a.review_frames.split(",")) if 1 <= f <= total]
            else:
                frames = sorted({1, 6, td["damageFrame"] - 10, td["damageFrame"], total})
            preview.render_frames(frames, os.path.join(a.out, "review", "frames"), f"{t_act.name}_vs_{a.victim_char}")
        if not a.no_export:
            if not a.skip_attacker:
                export_action(thrower_arm, t_act, os.path.join(a.out, t_act.name + ".fbx"))
            victim_arm.matrix_world = Matrix.Identity(4)
            export_action(victim_arm, v_act, os.path.join(a.out, "victim_" + a.victim_char, v_act.name + ".fbx"))
    print("BUILDANIM throws done")


TURN_TOWARD_CAMERA = 12.0   # EHFighterVisual: each fighter is shown opened this far toward the camera


def shown(facing, s):
    """Where the game draws a fighter's animation space, in the thrower's (its spot at the origin, facing -Y, the
    camera off its right at -X): s metres along the thrower's forward, turned toward the camera, and mirrored along
    the fight axis when facing the other way (EHFighterVisual mirrors a fighter facing left instead of turning it)."""
    m = Matrix.Translation((0.0, -s, 0.0)) @ Matrix.Rotation(math.radians(-TURN_TOWARD_CAMERA * facing), 4, "Z")
    return m @ Matrix.Scale(-1.0, 4, (0.0, 1.0, 0.0)) if facing < 0 else m


def stage_transforms(a, td, t_rig, v_rig):
    """End poses for both bodies and the victim's placement, from how the game draws the pair.

    During the throw the thrower is drawn at shown(+1, 0) and the victim at shown(-1, holdX); the victim is authored at
    holdX in front of the thrower facing it (its authoring space), so its animation is carried into its own drawn
    space by to_own, a turn plus a mirror. After the landing both face each other again, a back throw switching sides
    (EHMatch FaceOpponent): the thrower in its stance (as Idle starts) at shown(+-1, 0) and the victim lying (as
    KnockdownLie starts) at shown(-+1, landX). The game cuts rather than blends when the facing flips, so a back throw
    has to end exactly on what is drawn next. Returns ({armature name: end pose in the space it is authored in},
    the victim's drawn space in the thrower's, to_own)."""
    hold, land = td["holdX"] / 100.0, td["landX"] / 100.0
    back = land < 0
    auth_v = Matrix.Translation((0.0, -hold, 0.0)) @ Matrix.Rotation(math.pi, 4, "Z")
    during_t, during_v = shown(1, 0.0), shown(-1, hold)
    after_t, after_v = shown(-1 if back else 1, 0.0), shown(1 if back else -1, land)
    stance = author_pose(t_rig, throws.world_feet(throws.stance_of(a.char)))
    # The victim ends as KnockdownLie starts, or as KnockdownLieRev starts when it lands head toward the thrower.
    lie_spec = throws.lying(throws.stance_of(a.victim_char))
    lie = author_pose(v_rig, lie_spec(spin=180.0) if td.get("landsHeadToward") else lie_spec)
    HANDOFF.update(t=stance, v=lie)
    ends = {t_rig.arm.name: transform_pose(t_rig.arm, stance, during_t.inverted() @ after_t),
            v_rig.arm.name: transform_pose(v_rig.arm, lie, (during_t @ auth_v).inverted() @ after_v)}
    to_own = during_v.inverted() @ during_t @ auth_v
    return ends, during_t.inverted() @ during_v, to_own


def report_handoff(td, t_rig, v_rig, t_last, v_last, shown_v):
    """How far each body's last throw frame, as drawn, is from the first frame of what is drawn after the landing
    (bone heads; a mirror swaps a bone with its partner)."""
    land = td["landX"] / 100.0
    back = land < 0
    t_next = shown(1, 0.0).inverted() @ shown(-1 if back else 1, 0.0)
    v_next = shown(1, 0.0).inverted() @ shown(1 if back else -1, land)
    worst = []
    for rig, last, place, nxt, nxt_pose in ((t_rig, t_last, Matrix.Identity(4), t_next, HANDOFF.get("t")),
                                            (v_rig, v_last, shown_v, v_next, HANDOFF.get("v"))):
        a_w, b_w = pose_world(rig.arm, last), pose_world(rig.arm, nxt_pose)
        err = (0.0, "")
        for n in a_w:
            if rig.arm.data.bones[n].parent is None:
                continue                  # the root bone stays on the actor's spot and draws nothing
            pa = (place @ a_w[n]).translation
            e = min(((nxt @ b_w[m]).translation - pa).length for m in {n, other_side(n)} if m in b_w)
            err = max(err, (e, n))
        worst.append(err)
    print(f"BUILDANIM {td['id']} handoff: thrower {worst[0][0] * 1000:.0f} mm ({worst[0][1]}), "
          f"victim {worst[1][0] * 1000:.0f} mm ({worst[1][1]})")


HANDOFF = {}


def pose_world(arm, pose):
    bones = arm.data.bones
    rest = {b.name: b.matrix_local for b in bones}
    world, stack = {}, [b for b in bones if b.parent is None]
    while stack:
        b = stack.pop(0)
        loc, q = pose[b.name]
        basis = Matrix.Translation(loc) @ q.to_matrix().to_4x4()
        world[b.name] = (world[b.parent.name] @ (rest[b.parent.name].inverted() @ rest[b.name]) if b.parent else rest[b.name]) @ basis
        stack.extend(b.children)
    return world


def load_idle_pose(path):
    """A fighter's idle first pose saved by build_mocap (None if it has not been built yet)."""
    if not os.path.exists(path):
        print(f"BUILDANIM no idle pose at {path}: victims start on their throw's first frame")
        return None
    with open(path) as f:
        data = json.load(f)
    from mathutils import Quaternion
    return {name: (Vector(v["loc"]), Quaternion(v["rot"])) for name, v in data.items()}


def grab_connect_pose(a, data, rig):
    """The thrower's grab (the scripted T move) at its first active frame, where a throw takes over."""
    defs = moves.wren_moves(data) if a.char == "wren" else moves.ashka_moves(data)
    keys, total, travel, _ = defs["T"]
    move = next(m for m in data["moves"] if m["id"] == "T")
    frame = move["hits"][0]["frames"][0]
    A.mute_constraints(rig, False)
    rig.reset()
    keep = rig.arm.animation_data.action if rig.arm.animation_data else None
    tmp = bpy.data.actions.new("grab_tmp")
    rig.arm.animation_data_create()
    rig.arm.animation_data.action = tmp
    A.author([(rig, keys, travel)], frame)
    bpy.context.scene.frame_set(frame)
    pose = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in rig.arm.pose.bones}
    rig.arm.animation_data.action = keep
    bpy.data.actions.remove(tmp)
    A.mute_constraints(rig, True)
    return pose


def author_pose(rig, spec):
    """One scripted pose solved on the IK rig, as a local pose."""
    A.mute_constraints(rig, False)
    rig.reset()
    keep = rig.arm.animation_data.action if rig.arm.animation_data else None
    tmp = bpy.data.actions.new("pose_tmp")
    rig.arm.animation_data_create()
    rig.arm.animation_data.action = tmp
    A.author([(rig, [(1, spec, "smooth")], None)], 1)
    bpy.context.scene.frame_set(1)
    pose = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in rig.arm.pose.bones}
    rig.arm.animation_data.action = keep
    bpy.data.actions.remove(tmp)
    A.mute_constraints(rig, True)
    return pose


def read_poses(arm, total):
    """The keyed local pose of every bone at frames 1..total (constraints muted)."""
    scene = bpy.context.scene
    out = []
    for frame in range(1, total + 1):
        scene.frame_set(frame)
        out.append({pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in arm.pose.bones})
    return out


SIDE_TOKENS = {"l": "r", "r": "l", "fl": "fr", "fr": "fl", "bl": "br", "br": "bl"}


def other_side(name):
    return "_".join(SIDE_TOKENS.get(t, t) for t in name.split("_"))


def transform_pose(arm, pose, xf):
    """A local pose moved rigidly by the armature-space transform xf, which may mirror. Under a mirror each bone takes
    its partner's world matrix, mirrored, with the partner's rest turned onto its own; the skeletons are symmetric.
    The root bone stays where it is: the pelvis carries the move."""
    bones = arm.data.bones
    rest = {b.name: b.matrix_local.copy() for b in bones}
    order, stack = [], [b for b in bones if b.parent is None]
    while stack:
        b = stack.pop(0)
        order.append(b.name)
        stack.extend(b.children)
    world = {}
    for n in order:
        b = bones[n]
        loc, q = pose[n]
        basis = Matrix.Translation(loc) @ q.to_matrix().to_4x4()
        rel = rest[b.parent.name].inverted() @ rest[n] if b.parent else rest[n]
        world[n] = (world[b.parent.name] @ rel if b.parent else rel) @ basis
    mirror = xf.to_3x3().determinant() < 0
    flip = Matrix.Scale(-1.0, 4, (1.0, 0.0, 0.0))
    moved = {}
    for n in order:
        if bones[n].parent is None:
            moved[n] = world[n]
        elif mirror:
            o = other_side(n) if other_side(n) in rest else n
            moved[n] = xf @ world[o] @ (rest[o].inverted() @ flip @ rest[n]).to_3x3().to_4x4()
        else:
            moved[n] = xf @ world[n]
    out = {}
    for n in order:
        b = bones[n]
        if b.parent is None:
            out[n] = pose[n]
            continue
        rel = rest[b.parent.name].inverted() @ rest[n]
        loc, q, _ = ((moved[b.parent.name] @ rel).inverted() @ moved[n]).decompose()
        out[n] = (loc, q)
    return out


def captured_throws():
    with open(os.path.join(HERE, "mocap_clips.json")) as f:
        return json.load(f).get("throws", {})


def capture_throw(a, td, cap, t_rig, v_rig, ends):
    """A throw from a captured attacker/victim pair (mocap_clips.json "throws"), as local poses for frames 1..duration.

    The pair's clips are exported separately, so the victim is placed by turning it to face the attacker and shifting
    it so the attacker's hands meet its knees over the grip frames. The grip, the moment the victim lands and the end
    of the attacker's stand-up are mapped to frame 1, the throw's damage frame and its last frame. Each body's travel
    is scaled ("root_scale") so the victim lands near the throw's landX; the victim stands at the distance the capture
    has (the simulation holds it at holdX), and both blend into their end poses (ends, from stage_transforms)."""
    folder = os.path.join(os.environ.get("EH_WS", ""), "downloads", "thirdparty", "Mixamo")
    hold = td["holdX"] / 100.0
    g, land_src, end_src = cap["src"]
    if cap.get("shared"):
        return capture_shared(a, td, cap, t_rig, v_rig, folder, ends)
    src_a = M.FbxSource(os.path.join(folder, cap["attacker"]), t_rig.arm)
    src_v = M.FbxSource(os.path.join(folder, cap["victim"]), v_rig.arm)
    rt_a, rt_v = M.Retarget(t_rig.arm, src_a), M.Retarget(v_rig.arm, src_v)
    # Victim placement: turned 180 degrees, shifted so hands meet knees over the grip window (least squares).
    turn = Matrix.Rotation(math.pi, 3, "Z")
    acc, n = Vector((0, 0, 0)), 0
    for k in range(g, min(g + 12, src_a.count, src_v.count)):
        for hand, knee in (("LeftHand", "RightLeg"), ("RightHand", "LeftLeg")):
            acc += src_a.points[k][hand] - turn @ src_v.points[k][knee]
            n += 1
    shift = acc / n
    gap = src_a.pos[g].y - (turn @ src_v.pos[g] + shift).y      # victim hips ahead of the attacker's (forward is -Y)
    extra = gap * rt_a.scale - hold                              # the capture's distance beyond holdX
    tmap = M.warp([(1, g), (td["damageFrame"], land_src), (td["duration"], end_src)])
    total = td["duration"]
    out = []
    for src, rt, scale, back in ((src_a, rt_a, cap["root_scale"][0], 0.0), (src_v, rt_v, cap["root_scale"][1], extra)):
        start = src.pos[g].copy()
        off = Vector((-start.x * rt.scale, -start.y * rt.scale + back, 0.0))
        poses = []
        for frame in range(1, total + 1):
            q, p = src.sample(tmap(frame))
            p = Vector((start.x + (p.x - start.x) * scale, start.y + (p.y - start.y) * scale, p.z))
            poses.append(rt.local_pose(q, p, off))
        out.append(poses)
    for poses, arm, n_end, curl in ((out[0], t_rig.arm, cap["end_frames"][0], cap["fist"][0]),
                                    (out[1], v_rig.arm, cap["end_frames"][1], cap["fist"][1])):
        n_end = min(n_end, total)
        for i in range(n_end):
            k = total - n_end + i
            poses[k] = M.blend_pose(poses[k], ends[arm.name], A.ease("smooth", (i + 1) / n_end))
        half_prev = {}
        for pose in poses:
            M.fist(pose, curl)
            M.half_joints(pose, half_prev)
    print(f"BUILDANIM capture {td['id']}: gap {gap:.2f} m (holdX {hold:.2f}), victim set back {extra:+.2f} m")
    return out[0], out[1]


def facing_deg(p):
    """Facing of a captured body (degrees, 0 = facing -Y with its left along +X, positive turning left), from its hip
    line."""
    left = p["LeftUpLeg"] - p["RightUpLeg"]
    return math.degrees(math.atan2(left.y, left.x))


def capture_shared(a, td, cap, t_rig, v_rig, folder, ends):
    """A throw from a pair captured together ("shared": the two exports share one space, as Mixamo's paired clips
    do). The pair keeps its own placement: both are turned so the attacker faces -Y at the grip frame, the attacker's
    hips at the grip go to the thrower's spot, and the victim keeps its captured place relative to the attacker,
    expressed in its own frame (its actor stands at holdX in front of the thrower, facing it). Timing, travel scaling
    and the blend into the end poses are as for capture_throw."""
    hold = td["holdX"] / 100.0
    g, land_src, end_src = cap["src"]
    mirror = cap.get("mirror", False)
    path_a, path_v = os.path.join(folder, cap["attacker"]), os.path.join(folder, cap["victim"])
    heading = -facing_deg(M.fbx_pose(path_a)[g][0])
    src_a = M.FbxSource(path_a, t_rig.arm, heading, mirror)
    src_v = M.FbxSource(path_v, v_rig.arm, heading + 180.0, mirror)
    rt_a, rt_v = M.Retarget(t_rig.arm, src_a), M.Retarget(v_rig.arm, src_v)
    turn = Matrix.Rotation(math.pi, 3, "Z")
    # "yaw": [[source frame, degrees], ...] turns the whole pair about the attacker's grip-frame hips (positive turns
    # left), eased between keys, so a capture thrown off to one side can land on the fight line. The victim's source
    # is the attacker's turned 180 degrees, so its pivot is the attacker's turned with it.
    keys = sorted(cap.get("yaw", [[g, 0.0]]))

    def yaw_at(s):
        if s <= keys[0][0]:
            return keys[0][1]
        for (s0, y0), (s1, y1) in zip(keys, keys[1:]):
            if s <= s1:
                return y0 + (y1 - y0) * A.ease("smooth", (s - s0) / max(1e-6, s1 - s0))
        return keys[-1][1]

    def yawed(src, pivot, s):
        q, p = src.sample(s)
        r = Matrix.Rotation(math.radians(yaw_at(s)), 3, "Z")
        rq = r.to_quaternion()
        q = {n: rq @ v for n, v in q.items()}
        flat = Vector((p.x - pivot.x, p.y - pivot.y, 0.0))
        p = Vector((pivot.x, pivot.y, 0.0)) + r @ flat + Vector((0.0, 0.0, p.z))
        return q, p

    pivot_a = src_a.pos[g].copy()
    pivot_v = turn @ pivot_a
    # The victim's grip-frame hips in thrower space (attacker scale), then in the victim actor's frame.
    rel = (turn.inverted() @ yawed(src_v, pivot_v, g)[1] - pivot_a) * rt_a.scale
    rel.z = 0.0
    local_g = turn @ (rel - Vector((0.0, -hold, 0.0)))
    tmap = M.warp([(1, g), (td["damageFrame"], land_src), (td["duration"], end_src)])
    total = td["duration"]
    # "ease_in": the victim starts on its own spot (where the grab left it) and is drawn to its captured place.
    ease_in = cap.get("ease_in", 0)
    out = []
    for src, rt, scale, anchor, pivot, n_in in ((src_a, rt_a, cap["root_scale"][0], Vector((0.0, 0.0, 0.0)), pivot_a, 0),
                                                (src_v, rt_v, cap["root_scale"][1], local_g, pivot_v, ease_in)):
        start = yawed(src, pivot, g)[1]
        off = Vector((anchor.x - start.x * rt.scale, anchor.y - start.y * rt.scale, 0.0))
        poses = []
        for frame in range(1, total + 1):
            q, p = yawed(src, pivot, tmap(frame))
            p = Vector((start.x + (p.x - start.x) * scale, start.y + (p.y - start.y) * scale, p.z))
            w = A.ease("smooth", min(1.0, (frame - 1) / n_in)) if n_in else 1.0
            poses.append(rt.local_pose(q, p, off - anchor * (1.0 - w)))
        out.append(poses)
    for poses, arm, n_end, curl in ((out[0], t_rig.arm, cap["end_frames"][0], cap["fist"][0]),
                                    (out[1], v_rig.arm, cap["end_frames"][1], cap["fist"][1])):
        n_end = min(n_end, total)
        for i in range(n_end):
            k = total - n_end + i
            poses[k] = M.blend_pose(poses[k], ends[arm.name], A.ease("smooth", (i + 1) / n_end))
        half_prev = {}
        for pose in poses:
            M.fist(pose, curl)
            M.half_joints(pose, half_prev)
    print(f"BUILDANIM capture {td['id']} (shared): victim at the grip {-rel.y:.2f} m in front, {rel.x:+.2f} m to the "
          f"side (holdX {hold:.2f}); heading {heading:+.0f}")
    return out[0], out[1]


def load_chains(blend, arm):
    """Secondary chains from the character's bones.json (next to its .blend), filtered to bones that exist."""
    path = os.path.join(os.path.dirname(blend), "bones.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        chains = json.load(f).get("secondary_chains", {})
    return {k: v for k, v in chains.items() if all(b in arm.pose.bones for b in v["bones"]) and v.get("parent") in arm.pose.bones}


def review_frames(name, total, data_move):
    """Frames worth looking at: first, wind-up, contact, end of active, mid-recovery, last."""
    frames = {1, total}
    if data_move and data_move.get("hits"):
        a, b = data_move["hits"][0]["frames"]
        frames |= {max(1, a - 3), a, b, min(total, b + (total - b) // 2)}
    else:
        frames |= {max(1, total // 4), total // 2, (3 * total) // 4}
    return sorted(frames)


def export_action(arm, action, path):
    arm.animation_data.action = action
    start, end = action.frame_range
    bpy.context.scene.frame_start = int(start)
    bpy.context.scene.frame_end = int(end)
    for o in bpy.context.view_layer.objects:
        o.select_set(o == arm)
    bpy.context.view_layer.objects.active = arm
    # Must match the character mesh export (Tools/Blender/characters: FBX_SETTINGS) so bone spaces agree in Unreal.
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, object_types={"ARMATURE"}, add_leaf_bones=False, apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, axis_forward="Y", axis_up="Z", bake_space_transform=False,
        bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
        bake_anim_simplify_factor=0.0, bake_anim_step=1.0, use_armature_deform_only=True, armature_nodetype="NULL",
        primary_bone_axis="Y", secondary_bone_axis="X")


def main():
    a = args()
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    arm = bpy.data.objects["Armature"]
    with open(a.data) as f:
        data = json.load(f)
    os.makedirs(a.out, exist_ok=True)
    if a.victim_blend:
        os.makedirs(os.path.join(a.out, "victim_" + a.victim_char), exist_ok=True)
        build_throws(a, data)
        return
    defs = moves.wren_moves(data) if a.char == "wren" else moves.ashka_moves(data)
    by_id = {m["id"]: m for m in data["moves"]}
    rig = A.Rig(arm, a.char, a.height or None)
    chains = load_chains(a.blend, arm)
    only = set(x for x in a.only.split(",") if x)
    os.makedirs(a.out, exist_ok=True)
    prefix = "A_" + a.char.capitalize() + "_"
    made = []
    for key, (keys, total, travel, loop) in defs.items():
        if only and key not in only:
            continue
        A.mute_constraints(rig, False)
        rig.reset()
        action = bpy.data.actions.new(prefix + key)
        arm.animation_data_create()
        arm.animation_data.action = action
        A.author([(rig, keys, travel)], total)
        A.mute_constraints(rig, True)
        if chains:
            A.bake_secondary(rig, chains, total, loop)
        made.append((key, action, total))
        print(f"BUILDANIM {prefix}{key} frames={total} loop={loop}")
        if a.review:
            preview.setup_camera()
            if a.review_frames == "all":
                frames = list(range(1, total + 1))
            elif a.review_frames:
                frames = [f for f in (int(x) for x in a.review_frames.split(",")) if 1 <= f <= total]
            else:
                frames = review_frames(key, total, by_id.get(key))
            paths = preview.render_frames(frames, os.path.join(a.out, "review", "frames"), prefix + key)
            print("REVIEW", prefix + key, ",".join(str(f) for f in frames), "|".join(paths))
        if not a.no_export:
            export_action(arm, action, os.path.join(a.out, prefix + key + ".fbx"))
    print(f"BUILDANIM done {len(made)}")


if __name__ == "__main__":
    main()
