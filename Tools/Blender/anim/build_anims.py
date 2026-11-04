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
    """Paired thrower/victim authoring for each of the thrower's throws against one victim character."""
    victim_arm = append_armature(a.victim_blend, "victim")
    thrower_arm = bpy.data.objects["Armature"]
    t_rig = A.Rig(thrower_arm, a.char, a.height or None)
    v_rig = A.Rig(victim_arm, "victim_" + a.victim_char, a.victim_height or None)
    t_prefix = "A_" + a.char.capitalize() + "_"
    v_prefix = "A_" + a.victim_char.capitalize() + "_"
    for td in data["throws"]:
        build = throws.THROWS[(a.char, td["id"])]
        t_keys, v_keys = build(throws.stance_of(a.victim_char), td)
        hold = td["holdX"] / 100.0
        cap = captured_throws().get(td["id"])
        # Victim stands at holdX in front of the thrower (thrower faces -Y), facing back toward it.
        victim_arm.location = (0.0, -hold, 0.0)
        victim_arm.rotation_euler = (0.0, 0.0, 3.14159265)
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
            t_poses, v_poses = capture_throw(a, td, cap, t_rig, v_rig)
            thrower_arm.animation_data.action = t_act
            victim_arm.animation_data.action = v_act
            for arm, poses in ((thrower_arm, t_poses), (victim_arm, v_poses)):
                for frame, pose in enumerate(poses, start=1):
                    M.key_pose(arm, pose, frame)
                M.bake_tracked(arm, td["duration"])
        else:
            A.author([(t_rig, t_keys, None), (v_rig, v_keys, None)], td["duration"])
        A.mute_constraints(t_rig, True)
        A.mute_constraints(v_rig, True)
        for rig, blend in ((t_rig, a.blend), (v_rig, a.victim_blend)):
            ch = load_chains(blend, rig.arm)
            if ch:
                A.bake_secondary(rig, ch, td["duration"], False)
        print(f"BUILDANIM {t_act.name} + {v_act.name} frames={td['duration']}")
        if a.review:
            preview.setup_camera(distance=5.0)
            if a.review_frames:
                frames = [f for f in (int(x) for x in a.review_frames.split(",")) if 1 <= f <= td["duration"]]
            else:
                frames = sorted({1, 6, td["damageFrame"] - 10, td["damageFrame"], td["duration"]})
            preview.render_frames(frames, os.path.join(a.out, "review", "frames"), f"{t_act.name}_vs_{a.victim_char}")
        if not a.no_export:
            if not a.skip_attacker:
                export_action(thrower_arm, t_act, os.path.join(a.out, t_act.name + ".fbx"))
            victim_arm.location = (0.0, 0.0, 0.0)
            victim_arm.rotation_euler = (0.0, 0.0, 0.0)
            export_action(victim_arm, v_act, os.path.join(a.out, "victim_" + a.victim_char, v_act.name + ".fbx"))
    print("BUILDANIM throws done")


def captured_throws():
    with open(os.path.join(HERE, "mocap_clips.json")) as f:
        return json.load(f).get("throws", {})


def capture_throw(a, td, cap, t_rig, v_rig):
    """A throw from a captured attacker/victim pair (mocap_clips.json "throws"), as local poses for frames 1..duration.

    The pair's clips are exported separately, so the victim is placed by turning it to face the attacker and shifting
    it so the attacker's hands meet its knees over the grip frames. The grip, the moment the victim lands and the end
    of the attacker's stand-up are mapped to frame 1, the throw's damage frame and its last frame. Each body's travel
    is scaled ("root_scale") so the victim lands near the throw's landX; the victim stands at the distance the capture
    has (the simulation holds it at holdX), ends in the lying pose the knockdown starts from, and the thrower ends back
    in its stance on its own spot."""
    folder = os.path.join(os.environ.get("EH_WS", ""), "downloads", "thirdparty", "Mixamo")
    hold = td["holdX"] / 100.0
    # Scripted end poses, authored on the IK rigs before they are muted for the captured keys.
    t_end = throws.world_feet(throws.stance_of(a.char))
    v_end = throws.landed(throws.stance_of(a.victim_char), hold, td["landX"] / 100.0)
    ends = {}
    for rig, pose in ((t_rig, t_end), (v_rig, v_end)):
        A.mute_constraints(rig, False)
        rig.reset()
        tmp = bpy.data.actions.new("throw_end_tmp")
        rig.arm.animation_data_create()
        rig.arm.animation_data.action = tmp
        A.author([(rig, [(1, pose, "smooth")], None)], 1)
        ends[rig.arm.name] = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in rig.arm.pose.bones}
        rig.arm.animation_data.action = None
        bpy.data.actions.remove(tmp)
        A.mute_constraints(rig, True)
    src_a = M.FbxSource(os.path.join(folder, cap["attacker"]), t_rig.arm)
    src_v = M.FbxSource(os.path.join(folder, cap["victim"]), v_rig.arm)
    rt_a, rt_v = M.Retarget(t_rig.arm, src_a), M.Retarget(v_rig.arm, src_v)
    g, land_src, end_src = cap["src"]
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
