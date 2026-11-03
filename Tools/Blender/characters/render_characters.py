"""Evidence renders for the built fighters (reads sourceart/characters/<id>/<Name>.blend).

    run_blender.sh render_characters.py [wren] [ashka] [--what turn,face,poses,tattoo,lineup]

Writes to <slice>/evidence/characters/: <id>_{front,side,back,face}.png, <id>_pose_<pose>_<view>.png,
<id>_pose_metrics.json, ashka_tattoo_check.png, lineup_fight.png, lineup_front.png.
Pose tests use temporary keyframes on a throw-away copy of the scene (the .blend is never saved)."""
import json
import math
import os
import sys
sys.dont_write_bytecode = True

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eh_mesh as M      # noqa: E402
import eh_pose as PS     # noqa: E402
import eh_render as RR   # noqa: E402

SLICE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
SRC = os.path.join(SLICE, "sourceart", "characters")
EVI = os.path.join(SLICE, "evidence", "characters")
NAMES = {"wren": "Wren", "ashka": "Ashka"}


def open_char(cid):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, cid, NAMES[cid] + ".blend"))
    arm = bpy.data.objects["Armature"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent is arm]
    return arm, meshes


def landmarks(arm, meshes):
    eyes = next(o for o in meshes if o.name.endswith("_Eyes"))
    V = M.co(eyes)
    lo, hi = RR.bbox(meshes)
    return {"eye_z": float(V[:, 2].mean()), "eye_y": float(V[:, 1].min()), "height": float(hi[2] - lo[2]),
            "top": float(hi[2])}


def turnaround(cid, arm, meshes, res=(900, 1400)):
    cam = RR.setup_stage(res, samples=48, fill=0.6, rim=0.35)
    lo, hi = RR.bbox(meshes)
    c = (lo + hi) / 2
    h = (hi[2] - lo[2]) * 1.06
    out = []
    for nm, v in (("front", (0, -1, 0)), ("side", (1, 0, 0)), ("back", (0, 1, 0))):
        RR.ortho_view(cam, c, v, h)
        cam.data.sensor_fit = "VERTICAL"
        out.append(RR.render(os.path.join(EVI, "%s_%s.png" % (cid, nm))))
    return out


def face(cid, arm, meshes, L):
    cam = RR.setup_stage((1000, 1000), samples=64, fill=0.6)
    tgt = Vector((0, L["eye_y"] + 0.07, L["eye_z"] - 0.025))
    eye = tgt + Vector((math.sin(math.radians(22)), -math.cos(math.radians(22)), 0.05)) * 0.95
    RR.persp_view(cam, eye, tgt, lens=105)
    cam.data.sensor_fit = "VERTICAL"
    return RR.render(os.path.join(EVI, "%s_face.png" % cid))


def tattoo_check(arm, meshes, L):
    cam = RR.setup_stage((900, 900), samples=48, fill=0.25)
    bpy.context.scene.view_settings.exposure = -0.6
    for o in meshes:
        if not o.name.endswith(("_Body", "_Eyes")):
            RR.hide([o])
    body = next(o for o in meshes if o.name.endswith("_Body"))
    zc = arm.data.bones["clavicle_l"].head_local[2]
    tgt = Vector((0, -0.08, zc - 0.075))
    RR.persp_view(cam, tgt + Vector((0.03, -0.45, 0.02)), tgt, lens=135)
    path = RR.render(os.path.join(EVI, "ashka_tattoo_check.png"))
    bpy.context.scene.view_settings.exposure = 0.0
    for o in meshes:
        RR.hide([o], False)
    return path


def chains(arm):
    out = {}
    for b in arm.data.bones:
        for pre in ("braid_", "strand_", "coat_"):
            if b.name.startswith(pre):
                key = b.name.rsplit("_", 1)[0]
                out.setdefault(key, []).append(b.name)
    for k in out:
        out[k].sort()
    return out


def settle(arm, meshes, cid):
    body = next(o for o in meshes if o.name.endswith("_Body"))
    others = [o for o in meshes if o.name.endswith(("_Outfit", "_Coat", "_Clothes"))]
    for key, names in chains(arm).items():
        if key.startswith("coat"):
            legs = [body] + [o for o in meshes if o.name.endswith("_Clothes")]
            PS.hang_chain(arm, names, legs, clear=0.03, keep=0.55)
        else:
            PS.hang_chain(arm, names, [body] + others, clear=0.015, keep=0.6)


def poses(cid, arm, meshes, L, res=(700, 900)):
    cam = RR.setup_stage(res, samples=32)
    scene = bpy.context.scene
    arm.animation_data_create()
    act = bpy.data.actions.new("TEMP_pose_tests")
    arm.animation_data.action = act
    metrics = {}
    body = next(o for o in meshes if o.name.endswith("_Body"))
    garments = [o for o in meshes if o.name.endswith(("_Outfit", "_Coat", "_Clothes", "_Gloves"))]
    hair = next(o for o in meshes if o.name.endswith("_Hair"))
    for i, pn in enumerate(PS.POSES):
        PS.pose(arm, pn, L)
        if pn != "rest":
            settle(arm, meshes, cid)
        PS.key_all(arm, i + 1)
    files = []
    rest_masks = {}
    CLOSE = {"roundhouse": ("thigh_r", -40, 1.0), "stance": ("pelvis", 30, 1.1), "guard": ("spine_03", 25, 0.9),
             "punch": ("upperarm_r", -65, 0.9), "twist": ("spine_02", 20, 1.0), "knee": ("calf_r", -70, 0.9),
             "backbend": ("spine_02", -90, 1.1)}
    for i, pn in enumerate(PS.POSES):
        scene.frame_set(i + 1)
        m = {}
        pairs = [(g, body, 0.004) for g in garments] + [(hair, body, 0.006)]
        if cid == "ashka":
            clothes = next(o for o in meshes if o.name.endswith("_Clothes"))
            coat = next(o for o in meshes if o.name.endswith("_Coat"))
            pairs.append((coat, clothes, 0.004))
        for g, b, tol in pairs:
            key = "%s_vs_%s" % (g.name, b.name)
            mask = PS.penetration(g, b, tol)
            if pn == "rest":
                rest_masks[key] = mask
            new = mask & ~rest_masks.get(key, np.zeros_like(mask))
            m[key + "_new_inside"] = [int(new.sum()), round(float(new.mean()), 4)]
        for b in ("upperarm_twist_01_r", "lowerarm_twist_01_r", "thigh_twist_01_r"):
            m[b + "_turn_deg"] = round(PS.local_turn_deg(arm, b), 1)
        metrics[pn] = m
        lo, hi = RR.bbox(meshes)
        c = (lo + hi) / 2
        size = max(hi[2] - lo[2], 1.0)
        views = [("3q", 35, c, size * 2.7, 50), ("side", -90, c, size * 2.7, 50)]
        if pn in CLOSE:
            bn, az, dist = CLOSE[pn]
            views.append(("close", az, np.array(arm.pose.bones[bn].head), dist, 50))
        for vn, az, cc, d, lens in views:
            a = math.radians(az)
            eye = Vector((cc[0] + math.sin(a) * d, cc[1] - math.cos(a) * d, cc[2] + (0.15 if vn != "close" else 0.05)))
            RR.persp_view(cam, eye, Vector(cc), lens=lens)
            cam.data.sensor_fit = "VERTICAL"
            files.append(RR.render(os.path.join(EVI, "%s_pose_%s_%s.png" % (cid, pn, vn))))
        if cid == "wren" and pn == "guard":
            hc = (np.array(arm.pose.bones["hand_l"].head) + np.array(arm.pose.bones["hand_r"].head)) / 2
            RR.persp_view(cam, Vector((hc[0] + 0.12, hc[1] - 0.55, hc[2] + 0.02)), Vector(hc), lens=70)
            files.append(RR.render(os.path.join(EVI, "wren_gloves_fists.png")))
    with open(os.path.join(EVI, "%s_pose_metrics.json" % cid), "w") as f:
        json.dump(metrics, f, indent=1)
    return files


def lineup():
    """Both fighters on one stage: fighting-game camera at 6 m, 30 degree vertical FOV."""
    arm_w, mw = open_char("wren")
    Lw = landmarks(arm_w, mw)
    with bpy.data.libraries.load(os.path.join(SRC, "ashka", "Ashka.blend"), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith(("Armature", "Ashka_"))]
    coll = bpy.context.scene.collection
    arm_a = None
    ma = []
    for o in dst.objects:
        if o is None:
            continue
        coll.objects.link(o)
        if o.type == "ARMATURE":
            arm_a = o
        else:
            ma.append(o)
    La = landmarks(arm_a, ma)
    shots = {}
    # (1) front lineup, rest pose: silhouette and palette side by side
    arm_w.location = (-0.55, 0, 0)
    arm_a.location = (0.55, 0, 0)
    arm_w.rotation_euler = arm_a.rotation_euler = (0, 0, 0)
    cam = RR.setup_stage((1920, 1080), samples=64)
    RR.persp_view(cam, Vector((0, -6.0, 1.0)), Vector((0, 0, 0.92)), fov_v_deg=30)
    shots["front"] = RR.render(os.path.join(EVI, "lineup_front.png"))
    # (2) facing each other in fighting stances
    for arm, meshes, L, x, yaw in ((arm_w, mw, Lw, -1.05, 72), (arm_a, ma, La, 1.05, -72)):
        arm.location = (0, 0, 0)
        arm.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        PS.pose(arm, "stance", L)
        if any(b.name.startswith(("braid", "coat", "strand")) for b in arm.data.bones):
            body = next(o for o in meshes if o.name.endswith("_Body"))
            for key, names in chains(arm).items():
                cols = [body] + [o for o in meshes if o.name.endswith(("_Outfit", "_Coat", "_Clothes"))]
                PS.hang_chain(arm, names, cols if not key.startswith("coat") else [body] + [o for o in meshes if o.name.endswith("_Clothes")],
                              clear=0.02, keep=0.4)
        arm.matrix_world = Matrix.Translation((x, 0, 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
        bpy.context.view_layer.update()
    RR.persp_view(cam, Vector((0, -6.0, 1.0)), Vector((0, 0, 0.9)), fov_v_deg=30)
    shots["fight"] = RR.render(os.path.join(EVI, "lineup_fight.png"))
    return shots


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    what = {"turn", "face", "poses", "tattoo", "lineup"}
    ids = []
    for a in argv:
        if a.startswith("--what="):
            what = set(a.split("=", 1)[1].split(","))
        elif not a.startswith("-"):
            ids.append(a)
    ids = ids or ["wren", "ashka"]
    os.makedirs(EVI, exist_ok=True)
    for cid in ids:
        arm, meshes = open_char(cid)
        L = landmarks(arm, meshes)
        if "turn" in what:
            turnaround(cid, arm, meshes)
        if "face" in what:
            face(cid, arm, meshes, L)
        if "tattoo" in what and cid == "ashka":
            tattoo_check(arm, meshes, L)
        if "poses" in what:
            poses(cid, arm, meshes, L)
    if "lineup" in what:
        lineup()


if __name__ == "__main__":
    main()
