"""Builds fighter animations from CMU motion capture (see mocap.py and mocap_clips.json).

Run: bin/blender.sh anim Tools/Blender/anim/build_mocap.py -- --blend <Char.blend> --char wren|ashka
         --data Content/Data/Fighters/<char>.json --mocap <dir of NN.asf / NN_TT.amc> --out <dir>
         [--only Idle,L1] [--review] [--no-export]
     ... --analyze 13_29 [--heading 0] [--mirror]   prints a timeline of one clip to choose segments
Writes <out>/A_<Char>_<Key>.fbx like build_anims.py, so the Unreal import is unchanged.
"""
import argparse
import json
import math
import os
import sys
import types

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import animlib as A  # noqa: E402
import mocap as M  # noqa: E402
import preview  # noqa: E402
from build_anims import export_action, load_chains, review_frames  # noqa: E402


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True)
    p.add_argument("--char", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--mocap", required=True)
    p.add_argument("--bvh", default="", help="folder of BVH takes (ACCAD); default <mocap>/../ACCAD/extracted")
    p.add_argument("--mixamo", default="", help="folder of Mixamo FBX clips; default <mocap>/../Mixamo")
    p.add_argument("--clips", default=os.path.join(HERE, "mocap_clips.json"))
    p.add_argument("--out", default="")
    p.add_argument("--only", default="")
    p.add_argument("--review", action="store_true")
    p.add_argument("--review-frames", default="", help='with --review: "all", or a comma list of frames')
    p.add_argument("--no-export", action="store_true")
    p.add_argument("--height", type=float, default=0.0)
    p.add_argument("--video", action="store_true", help="render every frame (loops three times) for review footage")
    p.add_argument("--analyze", default="")
    p.add_argument("--heading", type=float, default=0.0)
    p.add_argument("--mirror", action="store_true")
    p.add_argument("--t0", type=float, default=0.0)
    p.add_argument("--t1", type=float, default=1e9)
    p.add_argument("--step", type=int, default=6)
    p.add_argument("--punches", action="store_true", help="with --analyze: list every straight punch")
    p.add_argument("--segments", action="store_true", help="with --analyze: idle / step runs")
    return p.parse_args(argv)


def heading_of(v):
    """The --heading that turns horizontal vector v to face the opponent (-Y)."""
    return math.degrees(math.atan2(-v.x, -v.y))


def rt_scale(arm, a):
    """Stance values are written for a 1.75 m body; scale them to this fighter (same rule as animlib.Rig)."""
    if a.height:
        return a.height / 1.75
    top = max(b.tail_local.z for b in arm.data.bones)
    return top / 1.643


def stances():
    with open(os.path.join(HERE, "stances.json")) as f:
        return json.load(f)


def stance_targets(st, idle=False, overrides=None):
    """The stance layer's targets from a fighter's stance pose (stances.json), as mocap.apply_stance expects them."""
    t = {"pelvis": st["pelvis"], "pelvis_yaw": st["pelvis_rot"][0], "chest_yaw": st["pelvis_rot"][0] + st["chest"][0],
         "foot_l": st["foot_l"][:2], "foot_r": st["foot_r"][:2], "foot_l_yaw": st["foot_l_rot"][0], "foot_r_yaw": st["foot_r_rot"][0],
         "hand_l": st["hand_l"], "hand_r": st["hand_r"], "elbow_l": st["elbow_l"], "elbow_r": st["elbow_r"],
         "knee_l": st["knee_l"], "knee_r": st["knee_r"]}
    for key in ("lean", "head_pitch", "head_yaw", "clavicle"):
        if key in st:
            t[key] = st[key]
    if idle:
        # The idle's motion gains (softer bounce, quieter hands) and the Muay Thai rock apply to the idle only; walks
        # and strikes keep their full captured motion.
        t.update(st.get("idle", {}).get("motion", {}))
        if "rock" in st.get("idle", {}):
            t["rock"] = st["idle"]["rock"]
    t.update(overrides or {})
    return t


def emit_clip(a, arm, chains, hair, prefix, key, spec, move, poses, total, loop):
    """Keys a finished clip on the armature, bakes the coat and the hair, and renders and exports it."""
    action = bpy.data.actions.new(prefix + key)
    arm.animation_data_create()
    arm.animation_data.action = action
    for frame, pose in enumerate(poses, start=1):
        M.key_pose(arm, pose, frame)
    M.bake_tracked(arm, total)
    if chains:
        A.bake_secondary(hair, chains, total, loop)
    print(f"BUILDMOCAP {prefix}{key} clip={spec.get('clip') or spec.get('bvh') or spec.get('fbx') or 'scripted'} "
          f"src={spec.get('anchors') or spec.get('src')} frames={total} loop={loop}")
    if a.review:
        preview.setup_camera()
        if a.review_frames == "all":
            frames = list(range(1, total + 1))
        elif a.review_frames:
            frames = [f for f in (int(x) for x in a.review_frames.split(",")) if 1 <= f <= total]
        else:
            frames = review_frames(key, total, move)
        paths = preview.render_frames(frames, os.path.join(a.out, "review", "frames"), prefix + key)
        print("REVIEW", prefix + key, ",".join(str(f) for f in frames), "|".join(paths))
    if a.video:
        preview.setup_camera()
        reps = 3 if loop else 1
        frames = [f for _ in range(reps) for f in range(1, total + 1)]
        vdir = os.path.join(a.out, "video", prefix + key)
        os.makedirs(vdir, exist_ok=True)
        for k, f in enumerate(frames):
            bpy.context.scene.frame_set(f)
            bpy.context.scene.render.filepath = os.path.join(vdir, f"{k:04d}.png")
            bpy.ops.render.render(write_still=True)
        print("VIDEO", prefix + key, vdir, len(frames))
    if not a.no_export:
        export_action(arm, action, os.path.join(a.out, prefix + key + ".fbx"))


def save_idle_pose(a, pose):
    """The idle's first pose (local bone transforms) beside the exported clips, for the throw build: a grabbed fighter's
    throw animation eases out of it."""
    if a.no_export or not a.out:
        return
    data = {name: {"loc": list(loc), "rot": [q.w, q.x, q.y, q.z]} for name, (loc, q) in pose.items()}
    with open(os.path.join(a.out, "idle_pose.json"), "w") as f:
        json.dump(data, f)


def scripted_clip(a, arm, data, key):
    """Every frame of a scripted move (moves.py) as local poses, authored with the scripted build's IK rig and its
    travel; every constraint is muted again afterwards. Returns (poses, total)."""
    import moves
    defs = moves.wren_moves(data) if a.char == "wren" else moves.ashka_moves(data)
    keys, total, travel, _ = defs[key]
    rig = A.Rig(arm, a.char, a.height or None)
    A.mute_constraints(rig, False)
    rig.reset()
    action = bpy.data.actions.new("scripted_" + key)
    arm.animation_data_create()
    arm.animation_data.action = action
    A.author([(rig, keys, travel)], total)
    A.mute_constraints(rig, True)
    poses = []
    for frame in range(1, total + 1):
        bpy.context.scene.frame_set(frame)
        poses.append({pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in arm.pose.bones})
    arm.animation_data.action = None
    bpy.data.actions.remove(action)
    return poses, total


def scripted_poses(a, arm, data, wanted):
    """Poses of scripted moves (moves.py) at given frames, {(key, frame): local pose}, for clips layered onto a
    scripted pose ("additive") or ending in one ("end_pose"). Authored with the scripted build's IK rig, then every
    constraint is muted again for the captured clips."""
    if not wanted:
        return {}
    import moves
    defs = moves.wren_moves(data) if a.char == "wren" else moves.ashka_moves(data)
    rig = A.Rig(arm, a.char, a.height or None)
    out = {}
    for key, frame in sorted(wanted):
        keys, total, travel, loop = defs[key]
        A.mute_constraints(rig, False)
        rig.reset()
        action = bpy.data.actions.new("scripted_" + key)
        arm.animation_data_create()
        arm.animation_data.action = action
        A.author([(rig, keys, travel)], frame)
        out[(key, frame)] = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in arm.pose.bones}
        arm.animation_data.action = None
        bpy.data.actions.remove(action)
    for pb in arm.pose.bones:
        for c in pb.constraints:
            c.mute = True
    return out


def make_source(a, spec, arm):
    if "fbx" in spec:
        path = os.path.join(a.mixamo, spec["fbx"])
        return M.FbxSource(path, arm, heading_deg=spec.get("heading", 0.0), mirror=spec.get("mirror", False))
    if "bvh" in spec:
        path = os.path.join(a.bvh, spec["bvh"] + ".bvh")
        return M.BvhSource(path, arm, heading_deg=spec.get("heading", 0.0), mirror=spec.get("mirror", False))
    return M.Source(*clip_paths(a.mocap, spec["clip"]), heading_deg=spec.get("heading", 0.0), mirror=spec.get("mirror", False))


def clip_paths(mocap, clip):
    subject = clip.split("_")[0]
    return os.path.join(mocap, f"{subject}.asf"), os.path.join(mocap, f"{clip}.amc")


def analyze(a):
    """Timeline at 20 Hz: hip heading, root travel, and each hand's reach forward of the chest (Blender space)."""
    src = M.Source(*clip_paths(a.mocap, a.analyze), heading_deg=a.heading, mirror=a.mirror)
    print(f"ANALYZE {a.analyze} frames={src.count} ({src.count / M.SRC_FPS:.2f}s) leg={src.leg:.3f} floor={src.floor:.3f}")
    p0 = src.pos[0]
    a0, a1 = int(a.t0 * M.SRC_FPS), min(src.count, int(a.t1 * M.SRC_FPS) + 1)
    for i in range(a0, a1, a.step):
        e = src.ends[i]
        left = (e["lfemur"] - e["rfemur"]) if "lfemur" in e else Vector((1, 0, 0))
        hips_l = (src.ends[i]["lhipjoint"] - src.ends[i]["rhipjoint"])
        fwd = hips_l.cross(Vector((0, 0, 1)))
        heading = math.degrees(math.atan2(-fwd.x, -fwd.y))
        chest = e["thorax"]
        reach = []
        for s in ("l", "r"):
            d = e[f"{s}hand"] - chest
            reach.append(f"{s}:{-d.y:+.2f}/{d.z:+.2f}@{heading_of(d):+4.0f}")
        feet = e["ltoes"] - e["rtoes"]
        r = src.pos[i] - p0
        j = min(src.count - 1, i + a.step)
        vel = (src.pos[j] - src.pos[i]) * (M.SRC_FPS / max(1, j - i))
        vel.z = 0.0
        stance = heading_of(e["ltoes"] - e["rtoes"]) if feet.y < 0 else heading_of(e["rtoes"] - e["ltoes"])
        ank = []
        for s in ("l", "r"):
            p1 = src.ends[i][f"{s}tibia"]
            p2 = src.ends[j][f"{s}tibia"]
            sp = (p2 - p1).xy.length * (M.SRC_FPS / max(1, j - i))
            ank.append(f"{s}{(p1.z - src.floor) * 100:3.0f}cm/{sp:.2f}")
        print(f"  f{i:5d} t={i / M.SRC_FPS:6.2f} head={heading:+6.0f} root=({r.x:+.2f},{r.y:+.2f},{src.pos[i].z:.2f}) "
              f"v={vel.length:.2f}@{heading_of(vel):+4.0f} reach {reach[0]} {reach[1]}  feet(l-r)=({feet.x:+.2f},{feet.y:+.2f}) "
              f"stance@{stance:+4.0f} ankles {ank[0]} {ank[1]} lft={left.length:.2f}")


def punches(a):
    """Every straight punch in a clip: hand, peak frame, reach, aim, and the root's forward travel around it."""
    src = M.Source(*clip_paths(a.mocap, a.analyze), heading_deg=a.heading, mirror=a.mirror)
    print(f"PUNCHES {a.analyze} frames={src.count}")
    reach = {s: [] for s in ("l", "r")}
    for e in src.ends:
        for s in ("l", "r"):
            d = e[f"{s}hand"] - e["thorax"]
            reach[s].append(d)
    for s in ("l", "r"):
        o = "r" if s == "l" else "l"
        r = [math.hypot(d.x, d.y) for d in reach[s]]
        for i in range(12, src.count - 12):
            if r[i] < 0.45 or r[i] < max(r[i - 12:i + 13]):
                continue
            start = next((k for k in range(i, max(0, i - 60), -1) if r[k] < 0.32), max(0, i - 60))
            end = next((k for k in range(i, min(src.count, i + 90)) if r[k] < 0.36), min(src.count - 1, i + 90))
            aim = heading_of(reach[s][i])
            fwd = Vector((-math.sin(math.radians(aim)), -math.cos(math.radians(aim)), 0))
            tr_in = (src.pos[i] - src.pos[start]).dot(fwd)
            tr_out = (src.pos[end] - src.pos[start]).dot(fwd)
            feet = src.ends[i]["ltoes"] - src.ends[i]["rtoes"]
            lead = "l" if feet.dot(fwd) > 0 else "r"
            kind = "JAB  " if s == lead else "CROSS"
            other = math.hypot(reach[o][i].x, reach[o][i].y)
            print(f"  {kind} hand={s} peak=f{i} t={i / M.SRC_FPS:.2f} src=[{start},{i},{end}] reach={r[i]:.2f} "
                  f"z={reach[s][i].z:+.2f} aim@{aim:+4.0f} travel_in={tr_in * 100:+.0f}cm travel_total={tr_out * 100:+.0f}cm "
                  f"other_hand={other:.2f} root_z={src.pos[i].z:.2f}")


def segments(a):
    """Labels 0.1 s windows (IDLE / FWD / BACK / PUNCH / OTHER, forward = -Y after --heading) and prints the runs."""
    src = M.Source(*clip_paths(a.mocap, a.analyze), heading_deg=a.heading, mirror=a.mirror)
    win = 12
    labels = []
    for i in range(0, src.count - win, win):
        v = (src.pos[i + win] - src.pos[i]) * (M.SRC_FPS / win)
        e = src.ends[i + win // 2]
        reach = max(math.hypot(*(e[f"{s}hand"] - e["thorax"]).xy) for s in ("l", "r"))
        fwd, side = -v.y, v.x
        if reach > 0.45:
            lab = "PUNCH"
        elif abs(side) > 0.35:
            lab = "OTHER"
        elif fwd > 0.2:
            lab = "FWD"
        elif fwd < -0.2:
            lab = "BACK"
        elif math.hypot(v.x, v.y) < 0.15:
            lab = "IDLE"
        else:
            lab = "OTHER"
        labels.append((i, lab))
    runs = []
    for i, lab in labels:
        if runs and runs[-1][0] == lab:
            runs[-1][2] = i + win
        else:
            runs.append([lab, i, i + win])
    print(f"SEGMENTS {a.analyze} heading={a.heading}")
    for lab, s, e in runs:
        if lab == "OTHER" or e - s < 36:
            continue
        d = src.pos[e] - src.pos[s]
        zs = [src.pos[k].z for k in range(s, e)]
        feet = src.ends[s]["ltoes"] - src.ends[s]["rtoes"]
        hips = []
        for k in range(s, e, 6):
            hl = src.ends[k]["lhipjoint"] - src.ends[k]["rhipjoint"]
            hips.append(heading_of(hl.cross(Vector((0, 0, 1)))))
        print(f"  {lab:5} f{s}-{e} ({(e - s) / M.SRC_FPS:.2f}s) fwd={-d.y * 100:+.0f}cm side={d.x * 100:+.0f}cm "
              f"z={min(zs):.2f}-{max(zs):.2f} lead={'L' if feet.y < 0 else 'R'} hips={min(hips):+.0f}..{max(hips):+.0f}")


def build(a):
    with open(a.clips) as f:
        table = json.load(f)[a.char]
    stance_table = stances()
    if not a.bvh:
        a.bvh = os.path.join(os.path.dirname(os.path.abspath(a.mocap)), "ACCAD", "extracted")
    if not a.mixamo:
        a.mixamo = os.path.join(os.path.dirname(os.path.abspath(a.mocap)), "Mixamo")
    with open(a.data) as f:
        data = json.load(f)
    by_id = {m["id"]: m for m in data["moves"]}
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    arm = bpy.data.objects["Armature"]
    for pb in arm.pose.bones:
        for c in pb.constraints:
            c.mute = True
    chains = load_chains(a.blend, arm)
    hair = types.SimpleNamespace(arm=arm, restq={b.name: b.matrix_local.to_quaternion() for b in arm.data.bones})
    only = set(x for x in a.only.split(",") if x)
    prefix = "A_" + a.char.capitalize() + "_"
    bpy.context.scene.render.fps = A.FPS
    guard_pose = None
    wanted = set()
    for key, spec in table.items():
        if only and key not in only:
            continue
        if spec.get("additive"):
            wanted.add((spec["additive"], 1))
        for edge in ("start_pose", "end_pose"):
            if spec.get(edge):
                wanted.add((spec[edge]["key"], spec[edge].get("frame", 1)))
    scripted = scripted_poses(a, arm, data, wanted)
    order = sorted(table, key=lambda k: 0 if table[k].get("loop") and k == "Idle" else 1)
    built = {}
    for key in order:
        spec = table[key]
        if only and key not in only and not (key == "Idle" and guard_pose is None):
            continue
        if spec.get("scripted"):
            continue
        src = make_source(a, spec, arm)
        src_fps = getattr(src, "fps", M.SRC_FPS)
        rt = M.Retarget(arm, src)
        # A string's own follow-up ("L2_from_L1") takes its move's timing from "move".
        move = by_id.get(spec.get("move", key))
        loop = bool(spec.get("loop"))
        if spec.get("anchors"):
            # Explicit (game frame, source frame) pairs, for reactions whose impact and recovery need their own pace.
            anchors = [tuple(p) for p in spec["anchors"]]
            s0, s1 = anchors[0][1], anchors[-1][1]
            total = move["total"] if move else spec.get("frames") or anchors[-1][0]
        elif move:
            s0, s1 = spec["src"][0], spec["src"][-1]
            total = move["total"]
            first_active = move["hits"][0]["frames"][0] if move.get("hits") else total // 3
            anchors = [(1, s0), (first_active, spec["src"][1]), (total, s1)]
        else:
            s0, s1 = spec["src"][0], spec["src"][-1]
            total = spec.get("frames") or max(2, round((s1 - s0) / src_fps * A.FPS / spec.get("rate", 1.0)))
            anchors = [(1, s0), (total + (1 if loop else 0), s1)]
        tmap = M.warp(anchors)
        travel = A.travel_curve(move["travel"], total) if move and move.get("travel") else None
        # The root is measured from the clip's first frame, or from its last ("root_anchor": "end") for a move that has
        # to finish on the fighter's spot, such as a get-up that rises forward from where the fall left the body.
        start_xy = src.pos[int(s1 if spec.get("root_anchor") == "end" else s0)].copy()
        # root_scale: share of the performer's (sideways, forward[, up]) travel kept, e.g. a fall that carries too far
        # or a jump that goes too high.
        rs = list(spec.get("root_scale", (1.0, 1.0)))
        rsx, rsy, rsz = rs[0], rs[1], (rs[2] if len(rs) > 2 else 1.0)

        def sample(frame):
            q, p = src.sample(tmap(frame))
            p = Vector((start_xy.x + (p.x - start_xy.x) * rsx, start_xy.y + (p.y - start_xy.y) * rsy,
                        start_xy.z + (p.z - start_xy.z) * rsz))
            return q, p

        def sim_at(frame):
            if spec.get("sim_speed"):          # walks: the simulation moves the root at a constant speed (cm/frame)
                return spec["sim_speed"] / 100.0 * (frame - 1)
            return travel[max(0, min(frame, len(travel) - 1))] if travel else 0.0

        sim_vec, cap_vec = [], []
        for frame in range(1, total + 2):
            _, p = sample(frame)
            sim_vec.append(Vector((0.0, -sim_at(frame), 0.0)))
            cap_vec.append(Vector(((p.x - start_xy.x) * rt.scale, (p.y - start_xy.y) * rt.scale, 0.0)))
        # Return one-shots to the same root spot, and make loops end where they start, so nothing pops. The pelvis
        # follows the capture minus the simulation's travel, so its drift is known exactly from the two curves.
        last = total if loop else total - 1
        drift = (cap_vec[last] - cap_vec[0]) - (sim_vec[last] - sim_vec[0])
        drift.z = 0.0

        def pose_at(frame):
            q, p = sample(frame)
            off = Vector((-start_xy.x * rt.scale, -start_xy.y * rt.scale + sim_at(frame), spec.get("z", 0.0)))
            pose = rt.local_pose(q, p, off)
            if move or loop:
                w = (frame - 1) / total if loop else A.ease("smooth", (frame - 1) / max(1, total - 1))
                if spec.get("follow_travel") and travel and abs(sim_at(total)) > 1e-4:
                    # A stepping move: the body keeps up with the game's travel instead of catching up over the clip.
                    w = max(0.0, min(1.0, sim_at(frame) / sim_at(total)))
                rt.shift_pelvis(pose, drift * w)
            return pose

        poses = [pose_at(frame) for frame in range(1, total + 1)]
        if loop:
            # Blend the cycle's tail into the motion just before frame 1, so the last frame leads straight into the first.
            n = min(spec.get("loop_blend", 12), total // 3)
            before = [pose_at(frame) for frame in range(1 - n, 1)]
            for i in range(n):
                k = total - n + i
                poses[k] = M.blend_pose(poses[k], before[i], A.ease("smooth", (i + 1) / n))
        if spec.get("plant", True):
            M.plant_feet(rt, poses, sim_vec, cap_vec, loop, speed=spec.get("plant_speed", 0.0055),
                         debug=bool(os.environ.get("EH_PLANT_DEBUG")), steps=spec.get("steps"),
                         step_lift=spec.get("step_lift", 0.05))
        if spec.get("stance"):
            # Designed stance (stances.json) with the capture's own motion around it; one-shots start in the stance.
            # "guard": sides whose hand stays at the stance guard during a strike, with only guard_gain of its captured
            # motion (the performer's dropped guard is not copied).
            hands = spec.get("guard") or spec.get("stance_hands", True)
            overrides = dict(spec.get("stance_motion") or {})
            if spec.get("guard"):
                overrides["hand_motion"] = spec.get("guard_gain", 0.6)
            M.apply_stance(rt, poses, stance_targets(stance_table[spec["stance"]], key == "Idle", overrides), rt_scale(arm, a),
                           anchor="mean" if loop else "start", hands=hands)
        if spec.get("fold"):
            # Elbow and knee strikes from captured hooks and kicks (mocap.fold_limb).
            fold = spec["fold"]
            M.fold_limb(rt, poses, fold["limb"], fold["side"], fold.get("angle", 150.0))
        if spec.get("settle"):
            M.settle_feet(rt, poses, spec["settle"]["feet"], spec["settle"].get("frames", 10))
        if spec.get("air") and move and move.get("airborne"):
            # Jumping moves built from grounded captures: the jump, any extra spin and the tucked leg (mocap.add_air).
            air = spec["air"]
            M.add_air(rt, poses, move["airborne"], air.get("height", 0.3) * rt_scale(arm, a), spin=air.get("spin", 0.0),
                      spin_frames=air.get("spin_frames"), tuck=air.get("tuck"), tuck_share=air.get("tuck_share", 0.8))
        if spec.get("additive"):
            poses = M.additive(rt, poses, scripted[(spec["additive"], 1)])
        if spec.get("reach") and move and move.get("hits"):
            # Strikes reach their hitbox: the fist, elbow, knee or foot is where the hit lands (mocap.reach).
            r = spec["reach"]
            a_, b_ = move["hits"][0]["frames"]
            got = M.reach(rt, poses, r["part"], r["to"] * rt_scale(arm, a), a_, b_, max_shift=r.get("max_shift", 0.35),
                          max_lean=r.get("max_lean", 0.6), skid=r.get("skid", 0.0), balance=r.get("balance", 0.0))
            print(f"BUILDMOCAP reach {key} {r['part']} -> {got:.2f} m (target {r['to'] * rt_scale(arm, a):.2f})")
        if spec.get("extend") and move and move.get("hits"):
            # A kick that drives out to a straight leg on its active frames (mocap.extend).
            e = spec["extend"]
            a_, b_ = move["hits"][0]["frames"]
            k = rt_scale(arm, a)
            got = M.extend(rt, poses, e["foot"], e["to"] * k, e["height"] * k, a_, b_, e.get("ramp_in", 5), e.get("ramp_out", 6))
            print(f"BUILDMOCAP extend {key} foot_{e['foot']} -> {got:.2f} m")
        if spec.get("turn"):
            # Rises facing away and pivots round over its feet to face the other way (the get-up from lying head toward
            # the opponent): from the turn's first frame the body turns about the point between the feet, eased over
            # the turn, and drifts back so it still ends on its own spot.
            t0, t1 = spec["turn"]["frames"]
            deg = spec["turn"]["deg"]
            w0 = rt.fk(poses[t0 - 1])
            pivot = (w0["foot_l"].translation + w0["foot_r"].translation) / 2.0
            pivot.z = 0.0
            end = rt.fk(poses[-1])["pelvis"].translation
            drift = M.turn_about(Matrix.Translation(end), pivot, deg).translation - end
            drift.z = 0.0
            for i in range(t0 - 1, total):
                k = A.ease("smooth", min(1.0, (i + 1 - t0) / max(1, t1 - t0)))
                world = rt.fk(poses[i])
                m = Matrix.Translation(-drift * k) @ M.turn_about(world["pelvis"], pivot, deg * k)
                rt.set_world(poses[i], world, "pelvis", m)
        if guard_pose is not None and not loop:
            nin, nout = spec.get("blend_in", 3), spec.get("blend_out", 6)
            for i in range(min(nin, total)):
                poses[i] = M.blend_pose(guard_pose, poses[i], A.ease("smooth", (i + 1) / (nin + 1)))
            for i in range(min(nout, total)):
                k = total - nout + i
                poses[k] = M.blend_pose(poses[k], guard_pose, A.ease("smooth", (i + 1) / nout))
        if spec.get("start_from"):
            # Starts from another clip's pose (a string's follow-up from the frame the first hit is cancelled on), so
            # the two hits join where the game cuts from one to the other.
            sf = spec["start_from"]
            source = built[sf["key"]][sf["frame"] - 1]
            n = min(sf.get("frames", 6), total)
            for i in range(n):
                poses[i] = M.blend_pose(source, poses[i], A.ease("smooth", i / n))
        if spec.get("start_pose"):
            # Starts from a scripted pose (the get-up rises out of the lying pose the knockdown ends in).
            sp = spec["start_pose"]
            source = scripted[(sp["key"], sp.get("frame", 1))]
            n = min(sp.get("frames", 10), total)
            for i in range(n):
                poses[i] = M.blend_pose(source, poses[i], A.ease("smooth", i / n))
        if spec.get("end_pose"):
            # Ends in a scripted pose (a knockdown settles into the lying pose the get-up starts from).
            ep = spec["end_pose"]
            target = scripted[(ep["key"], ep.get("frame", 1))]
            n = min(ep.get("frames", 12), total)
            for i in range(n):
                k = total - n + i
                poses[k] = M.blend_pose(poses[k], target, A.ease("smooth", (i + 1) / n))
        if loop and spec.get("start_frame"):
            # Loops restart from their first frame whenever they follow another animation: start the cycle on the
            # frame closest to the idle's pose (feet nearest the stance), so a walk does not open with a foot jump.
            k = spec["start_frame"] - 1
            poses = poses[k:] + poses[:k]
        M.overlap(poses, loop)
        half_prev = {}
        for pose in poses:
            M.fist(pose, spec.get("fist", 1.0))
            M.half_joints(pose, half_prev)
        if key == "Idle":
            guard_pose = poses[0]
            save_idle_pose(a, guard_pose)
        built[key] = poses
        if only and key not in only:
            continue
        emit_clip(a, arm, chains, hair, prefix, key, spec, move, poses, total, loop)
    for key, spec in table.items():
        if not spec.get("scripted") or (only and key not in only):
            continue
        # A move keyed by script (moves.py) on the scripted stance, eased in from and out into the idle's first pose
        # like the captured moves, so it hands over to and from the captured idle without a jump.
        poses, total = scripted_clip(a, arm, data, key)
        nin, nout = spec.get("blend_in", 4), spec.get("blend_out", 10)
        for i in range(min(nin, total)):
            poses[i] = M.blend_pose(guard_pose, poses[i], A.ease("smooth", (i + 1) / (nin + 1)))
        for i in range(min(nout, total)):
            k = total - nout + i
            poses[k] = M.blend_pose(poses[k], guard_pose, A.ease("smooth", (i + 1) / nout))
        emit_clip(a, arm, chains, hair, prefix, key, spec, by_id.get(key), poses, total, False)
    print("BUILDMOCAP done")


def main():
    a = args()
    if a.analyze and a.punches:
        punches(a)
    elif a.analyze and a.segments:
        segments(a)
    elif a.analyze:
        analyze(a)
    else:
        build(a)


main()
