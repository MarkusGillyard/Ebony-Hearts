"""Numerical audit of exported fighter clips (A_<Char>_<Key>.fbx), one CSV row per clip.

Run: <blender> -b --factory-startup -P Tools/Blender/anim/audit_clips.py -- <out.csv> <anims dir> [<anims dir> ...]
(each dir is scanned for A_*.fbx, not recursively; pass the victim_<char> folders too).

Per clip, from the baked bones as exported (what Unreal imports), positions in cm in the clip's own space:
- frames, the fastest joint step between consecutive frames and the joint, and how many steps exceed 40 cm
  (a real fist or foot peaks near 25-35 cm a frame at 60 fps);
- pops: a step over 15 cm that is more than 3 times the mean of the steps either side of it (a jump in an otherwise
  continuous motion, which a fast strike's smooth peak is not);
- held: the share of frames where no main joint moves 0.05 cm (frozen or duplicated samples);
- flips: an elbow or knee that moves at least 20 cm and 2.5 times as far as both joints either side of it;
- floor: the lowest point of the body (feet, hands, knees, hips, head top) and the frame; below -2 cm goes through
  the floor;
- seam: the largest joint gap between the last and the first frame (meaningful for loops);
- head top height range, for checking crouching clips against their hurtbox.
"""
import csv
import glob
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out_csv, dirs = argv[0], argv[1:]
J = ["pelvis", "spine_03", "head", "hand_l", "hand_r", "lowerarm_l", "lowerarm_r", "calf_l", "calf_r", "foot_l", "foot_r", "ball_l", "ball_r"]
LIMBS = [("upperarm_l", "lowerarm_l", "hand_l"), ("upperarm_r", "lowerarm_r", "hand_r"),
         ("thigh_l", "calf_l", "foot_l"), ("thigh_r", "calf_r", "foot_r")]
rows = []
for d in dirs:
    for path in sorted(glob.glob(os.path.join(d, "A_*.fbx"))):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False)
        new = [o for o in bpy.data.objects if o not in before]
        arm = next(o for o in new if o.type == "ARMATURE")
        act = arm.animation_data.action if arm.animation_data else None
        if act is None:
            for o in new:
                bpy.data.objects.remove(o, do_unlink=True)
            continue
        f0, f1 = (int(round(v)) for v in act.frame_range)
        names = set(J) | {b for limb in LIMBS for b in limb}
        pts, tops = [], []
        for f in range(f0, f1 + 1):
            bpy.context.scene.frame_set(f)
            pb = arm.pose.bones
            p = {j: (arm.matrix_world @ pb[j].head) * 100.0 for j in names if j in pb}
            p["head_top"] = (arm.matrix_world @ pb["head"].tail) * 100.0
            pts.append(p)
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
        for a in list(bpy.data.actions):
            if a.users == 0:
                bpy.data.actions.remove(a)
        n = len(pts)
        steps = []
        for i in range(1, n):
            j = max(J, key=lambda k: (pts[i][k] - pts[i - 1][k]).length)
            steps.append(((pts[i][j] - pts[i - 1][j]).length, j, i + f0))
        fast = max(steps, default=(0.0, "-", 0))
        over40 = sum(1 for s in steps if s[0] > 40.0)
        pops = []
        for i in range(1, len(steps) - 1):
            dist, j, fr = steps[i]
            around = (steps[i - 1][0] + steps[i + 1][0]) / 2.0
            if dist > 15.0 and dist > 3.0 * max(around, 1e-3):
                pops.append(f"f{fr}:{j}:{dist:.0f}")
        held = sum(1 for s in steps if s[0] < 0.05) / max(1, len(steps))
        flips = []
        for i in range(1, n):
            for a_, m_, b_ in LIMBS:
                if m_ not in pts[i] or a_ not in pts[i] or b_ not in pts[i]:
                    continue
                dm = (pts[i][m_] - pts[i - 1][m_]).length
                da = (pts[i][a_] - pts[i - 1][a_]).length
                db = (pts[i][b_] - pts[i - 1][b_]).length
                if dm >= 20.0 and dm >= 2.5 * max(da, db):
                    flips.append(f"f{i + f0}:{m_}:{dm:.0f}")
        low = min(((min(p[k].z for k in ("foot_l", "foot_r", "hand_l", "hand_r", "calf_l", "calf_r", "pelvis", "head_top")), i + f0) for i, p in enumerate(pts)), default=(0.0, 0))
        seam = max((pts[-1][k] - pts[0][k]).length for k in J) if n > 1 else 0.0
        ztop = [p["head_top"].z for p in pts]
        rows.append({
            "dir": os.path.basename(os.path.normpath(d)), "clip": os.path.basename(path)[:-4], "frames": n,
            "fastest_cm": f"{fast[0]:.1f}", "fastest_joint": fast[1], "fastest_frame": fast[2], "steps_over_40": over40,
            "pops": " ".join(pops[:6]), "held_pct": f"{held * 100:.0f}", "flips": " ".join(flips[:6]),
            "lowest_cm": f"{low[0]:.1f}", "lowest_frame": low[1], "seam_cm": f"{seam:.1f}",
            "head_top_min": f"{min(ztop):.0f}", "head_top_max": f"{max(ztop):.0f}",
        })
        print(f"AUDIT {rows[-1]['dir']}/{rows[-1]['clip']} frames={n} fast={fast[0]:.1f} pops={len(pops)} flips={len(flips)} low={low[0]:.1f}")
with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("AUDIT wrote", out_csv, len(rows))
