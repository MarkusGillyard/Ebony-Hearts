"""Evidence renders for the built fighters (reads <EH_CHAR_OUT or sourceart/characters>/<id>/<Name>.blend).

    run_blender.sh render_characters.py [wren] [ashka] [--what=turn,face,detail,feet,poses,tattoo,lineup]
                                        [--light=neutral,chapel] [--poses=rest,crouch,...]

Writes to EH_CHAR_EVI (default <slice>/evidence/characters): <id>_<view>_<light>.png turnarounds
(front, side, back, 3q), <id>_face_{3q,front}_<light>.png, <id>_detail_<name>.png, <id>_feet_<view>.png,
<id>_pose_<pose>_<view>.png, <id>_pose_metrics.json, ashka_tattoo_check.png, lineup_{front,fight}_<light>.png.
Every camera is framed from bones or fixed numbers (never from mesh bounds), so renders of two builds of
the same skeleton compare 1:1. Pose tests use temporary keyframes on a throw-away copy of the scene (the
.blend is never saved)."""
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
SRC = os.environ.get("EH_CHAR_OUT") or os.path.join(SLICE, "sourceart", "characters")
EVI = os.environ.get("EH_CHAR_EVI") or os.path.join(SLICE, "evidence", "characters")
NAMES = {"wren": "Wren", "ashka": "Ashka"}
FRAME_H = 2.0          # turnaround frame height (m), same for both fighters
FRAME_Z = 0.96


def open_char(cid):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, cid, NAMES[cid] + ".blend"))
    arm = bpy.data.objects["Armature"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent is arm]
    RR.add_ue_rim({m for o in meshes for m in o.data.materials})
    return arm, meshes


def landmarks(arm, meshes):
    """Rest-pose landmarks from bones only (identical for every build of the same skeleton)."""
    hb = arm.data.bones["head"]
    hz = hb.head_local[2]
    hl = hb.length
    return {"eye_z": float(hz + 0.224 * hl), "eye_y": float(hb.head_local[1] - 0.093), "height": 1.75,
            "head_z": float(hz)}


def turnaround(cid, arm, meshes, light, res=(900, 1400)):
    cam = RR.setup_stage(res, samples=48, fill=0.6, rim=0.35, rig=light)
    c = Vector((0, 0, FRAME_Z))
    out = []
    for nm, v in (("front", (0, -1, 0)), ("side", (1, 0, 0)), ("back", (0, 1, 0))):
        RR.ortho_view(cam, c, v, FRAME_H)
        cam.data.sensor_fit = "VERTICAL"
        out.append(RR.render(os.path.join(EVI, "%s_%s_%s.png" % (cid, nm, light))))
    a = math.radians(35)
    RR.persp_view(cam, Vector((math.sin(a) * 6.5, -math.cos(a) * 6.5, 1.2)), Vector((0, 0, FRAME_Z)), lens=85)
    out.append(RR.render(os.path.join(EVI, "%s_3q_%s.png" % (cid, light))))
    return out


def face(cid, arm, meshes, L, light):
    cam = RR.setup_stage((1000, 1000), samples=64, fill=0.6, rig=light)
    tgt = Vector((0, L["eye_y"] + 0.07, L["eye_z"] - 0.025))
    out = []
    for nm, az in (("3q", 22), ("front", 0)):
        eye = tgt + Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0.05)) * 0.95
        RR.persp_view(cam, eye, tgt, lens=105)
        out.append(RR.render(os.path.join(EVI, "%s_face_%s_%s.png" % (cid, nm, light))))
    return out


# name: (bone, offset from the bone head (m), azimuth deg (0 = front), elevation (m), distance (m), lens)
DETAILS = {
    "wren": {
        "top_front": ("spine_03", (0, 0, 0.0), 20, 0.05, 1.0, 85),
        "shorts_side": ("pelvis", (0.0, 0, -0.08), 70, 0.0, 1.2, 85),
        "glove_back": ("hand_l", (0, 0, 0), 60, 0.1, 0.55, 85),
        "fabric_macro": ("spine_03", (0.06, -0.11, 0.07), 15, 0.0, 0.45, 100),
        "wrap_macro": ("foot_l", (0.0, -0.03, 0.01), 60, 0.02, 0.4, 100),
    },
    "ashka": {
        "chest_front": ("spine_03", (0, -0.02, 0.06), 15, 0.05, 1.05, 85),
        "collar_3q": ("neck_01", (0, 0, -0.02), 40, 0.04, 0.75, 85),
        "cuff_hand": ("hand_r", (0, 0, 0.02), -60, 0.05, 0.6, 85),
        "waist_belt": ("pelvis", (0, -0.05, 0.08), 25, 0.05, 1.1, 85),
        "hem_back": ("pelvis", (0, 0.05, -0.55), 160, 0.1, 1.5, 85),
        "fabric_macro": ("spine_02", (0.1, -0.1, 0.02), 25, 0.0, 0.45, 100),
    },
}


def detail(cid, arm, meshes, light):
    cam = RR.setup_stage((1000, 1000), samples=48, fill=0.6, rig=light)
    out = []
    for nm, (bn, off, az, el, dist, lens) in DETAILS[cid].items():
        tgt = Vector(arm.data.bones[bn].head_local) + Vector(off)
        a = math.radians(az)
        eye = tgt + Vector((math.sin(a) * dist, -math.cos(a) * dist, el))
        RR.persp_view(cam, eye, tgt, lens=lens)
        out.append(RR.render(os.path.join(EVI, "%s_detail_%s_%s.png" % (cid, nm, light))))
    return out


FEET_VIEWS = (("front", 25, 0.12, 1.25), ("side", 90, 0.05, 1.25), ("back", 160, 0.12, 1.25),
              ("inner", -40, 0.04, 0.85), ("top", 10, 0.45, 0.75))


def feet(cid, arm, meshes, tag="rest", light="neutral", views=FEET_VIEWS, side="l"):
    """Close-ups of the feet (foot `side` centred) from the current pose's ankle positions."""
    cam = RR.setup_stage((1000, 800), samples=48, fill=0.6, rig=light)
    bpy.context.view_layer.update()
    al = np.array(arm.pose.bones["foot_" + side].head) @ np.array(arm.matrix_world)[:3, :3].T + np.array(arm.matrix_world)[:3, 3]
    ar = np.array(arm.pose.bones["foot_" + ("r" if side == "l" else "l")].head) @ np.array(arm.matrix_world)[:3, :3].T + np.array(arm.matrix_world)[:3, 3]
    out = []
    for nm, az, el, dist in views:
        tgt = Vector(al + np.array([0.0, -0.03, -0.035])) if nm != "front" else Vector((al + ar) / 2 + np.array([0, -0.04, -0.03]))
        a = math.radians(az)
        d = dist if nm == "front" else dist * 0.6
        if nm == "top":
            eye = tgt + Vector((math.sin(a) * 0.12, -math.cos(a) * 0.12 - 0.05, el))
        else:
            eye = tgt + Vector((math.sin(a) * d, -math.cos(a) * d, el))
        RR.persp_view(cam, eye, tgt, lens=70)
        out.append(RR.render(os.path.join(EVI, "%s_feet_%s_%s.png" % (cid, tag, nm))))
    return out


def tattoo_check(arm, meshes, L):
    cam = RR.setup_stage((900, 900), samples=48, fill=0.25)
    bpy.context.scene.view_settings.exposure = -0.6
    for o in meshes:
        if not o.name.endswith(("_Body", "_Eyes")):
            RR.hide([o])
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


def settle(arm, meshes, cid, keep_hair=0.6, keep_coat=0.55):
    body = next(o for o in meshes if o.name.endswith("_Body"))
    others = [o for o in meshes if o.name.endswith(("_Outfit", "_Coat", "_Clothes"))]
    for key, names in chains(arm).items():
        if key.startswith("coat"):
            legs = [body] + [o for o in meshes if o.name.endswith("_Clothes")]
            PS.hang_chain(arm, names, legs, clear=0.03, keep=keep_coat)
        else:
            PS.hang_chain(arm, names, [body] + others, clear=0.015, keep=keep_hair)


CLOSE = {"roundhouse": ("thigh_r", -40, 1.0), "stance": ("pelvis", 30, 1.1), "guard": ("spine_03", 25, 0.9),
         "punch": ("upperarm_r", -65, 0.9), "twist": ("spine_02", 20, 1.0), "knee": ("calf_r", -70, 0.9),
         "backbend": ("spine_02", -90, 1.1), "crouch": ("pelvis", 35, 1.2), "teep": ("calf_r", -75, 1.1),
         "kick_point": ("foot_r", -80, 0.7), "tiptoe": ("foot_l", 60, 0.75)}
FEET_POSES = {"rest", "roundhouse", "stance", "crouch", "teep", "kick_point", "tiptoe", "knee"}


def poses(cid, arm, meshes, L, res=(700, 900), names=None):
    names = [p for p in PS.POSES if names is None or p in names]
    cam = RR.setup_stage(res, samples=32, rig="neutral")
    scene = bpy.context.scene
    arm.animation_data_create()
    act = bpy.data.actions.new("TEMP_pose_tests")
    arm.animation_data.action = act
    metrics = {}
    body = next(o for o in meshes if o.name.endswith("_Body"))
    garments = [o for o in meshes if o.name.endswith(("_Outfit", "_Coat", "_Clothes", "_Gloves"))]
    hair = next(o for o in meshes if o.name.endswith("_Hair"))
    for i, pn in enumerate(names):
        PS.pose(arm, pn, L)
        if pn != "rest":
            settle(arm, meshes, cid)
        PS.key_all(arm, i + 1)
    files = []
    rest_masks = {}
    pm = {}
    for i, pn in enumerate(names):
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
            if pn == "rest" or key not in rest_masks:
                rest_masks.setdefault(key, mask if pn == "rest" else np.zeros_like(mask))
            new = mask & ~rest_masks[key]
            m[key + "_new_inside"] = [int(new.sum()), round(float(new.mean()), 4)]
        for b in ("upperarm_twist_01_r", "lowerarm_twist_01_r", "thigh_twist_01_r"):
            m[b + "_turn_deg"] = round(PS.local_turn_deg(arm, b), 1)
        lo, hi = RR.bbox(meshes)
        m["lowest_z_m"] = round(float(lo[2]), 4)
        m["ankle_l_deg"] = round(PS.local_turn_deg(arm, "foot_l"), 1)
        m["ankle_r_deg"] = round(PS.local_turn_deg(arm, "foot_r"), 1)
        m["ball_l_deg"] = round(PS.local_turn_deg(arm, "ball_l"), 1)
        metrics[pn] = m
        pel = np.array(arm.pose.bones["pelvis"].head)
        c = np.array([pel[0], pel[1], 0.9])
        size = 1.9
        views = [("3q", 35, c, size * 2.7, 50), ("side", -90, c, size * 2.7, 50)]
        if pn in CLOSE:
            bn, az, dist = CLOSE[pn]
            views.append(("close", az, np.array(arm.pose.bones[bn].head), dist, 50))
        for vn, az, cc, d, lens in views:
            a = math.radians(az)
            eye = Vector((cc[0] + math.sin(a) * d, cc[1] - math.cos(a) * d, cc[2] + (0.15 if vn != "close" else 0.05)))
            RR.persp_view(cam, eye, Vector(cc), lens=lens)
            files.append(RR.render(os.path.join(EVI, "%s_pose_%s_%s.png" % (cid, pn, vn))))
        if cid == "wren" and pn == "guard":
            hc = (np.array(arm.pose.bones["hand_l"].head) + np.array(arm.pose.bones["hand_r"].head)) / 2
            RR.persp_view(cam, Vector((hc[0] + 0.12, hc[1] - 0.55, hc[2] + 0.02)), Vector(hc), lens=70)
            files.append(RR.render(os.path.join(EVI, "wren_gloves_fists.png")))
        if pn in FEET_POSES and pn != "rest":
            kick = pn in ("teep", "kick_point", "roundhouse", "knee")
            fv = (("front", 25, 0.12, 1.25), ("side", 90, 0.05, 1.25), ("inner", -40, 0.04, 0.85))
            if kick:
                fv = (("front", -30, 0.05, 1.0), ("side", -90, 0.03, 1.2), ("inner", 60, 0.04, 0.85))
            pm[pn] = feet(cid, arm, meshes, tag=pn, views=fv, side="r" if kick else "l")
            cam = RR.setup_stage(res, samples=32, rig="neutral")
    with open(os.path.join(EVI, "%s_pose_metrics.json" % cid), "w") as f:
        json.dump(metrics, f, indent=1)
    return files


def _load_into(cid, prefix):
    with bpy.data.libraries.load(os.path.join(SRC, cid, NAMES[cid] + ".blend"), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith(("Armature", prefix))]
    coll = bpy.context.scene.collection
    arm, ms = None, []
    for o in dst.objects:
        if o is None:
            continue
        coll.objects.link(o)
        if o.type == "ARMATURE":
            arm = o
        else:
            ms.append(o)
    RR.add_ue_rim({m for o in ms for m in o.data.materials})
    return arm, ms


def lineup(lights):
    """Both fighters on one stage: fighting-game camera at 6 m, 30 degree vertical FOV."""
    arm_w, mw = open_char("wren")
    Lw = landmarks(arm_w, mw)
    arm_a, ma = _load_into("ashka", "Ashka_")
    La = landmarks(arm_a, ma)
    shots = {}
    arm_w.location = (-0.55, 0, 0)
    arm_a.location = (0.55, 0, 0)
    arm_w.rotation_euler = arm_a.rotation_euler = (0, 0, 0)
    for light in lights:
        cam = RR.setup_stage((1920, 1080), samples=64, rig=light)
        RR.persp_view(cam, Vector((0, -6.0, 1.0)), Vector((0, 0, 0.92)), fov_v_deg=30)
        shots["front_" + light] = RR.render(os.path.join(EVI, "lineup_front_%s.png" % light))
        RR.persp_view(cam, Vector((0, -2.6, 1.05)), Vector((0, 0, 0.95)), lens=50)
        shots["near_" + light] = RR.render(os.path.join(EVI, "lineup_near_%s.png" % light))
    for arm, meshes, L, x, yaw in ((arm_w, mw, Lw, -1.05, 72), (arm_a, ma, La, 1.05, -72)):
        arm.location = (0, 0, 0)
        arm.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        PS.pose(arm, "stance", L)
        body = next(o for o in meshes if o.name.endswith("_Body"))
        for key, names in chains(arm).items():
            cols = [body] + [o for o in meshes if o.name.endswith(("_Outfit", "_Coat", "_Clothes"))]
            PS.hang_chain(arm, names, cols if not key.startswith("coat") else [body] + [o for o in meshes if o.name.endswith("_Clothes")],
                          clear=0.02, keep=0.4)
        arm.matrix_world = Matrix.Translation((x, 0, 0)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")
        bpy.context.view_layer.update()
    for light in lights:
        cam = RR.setup_stage((1920, 1080), samples=64, rig=light)
        RR.persp_view(cam, Vector((0, -6.0, 1.0)), Vector((0, 0, 0.9)), fov_v_deg=30)
        shots["fight_" + light] = RR.render(os.path.join(EVI, "lineup_fight_%s.png" % light))
    return shots


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    what = {"turn", "face", "detail", "feet", "poses", "tattoo", "lineup"}
    lights = ["neutral", "chapel"]
    pose_names = None
    ids = []
    for a in argv:
        if a.startswith("--what="):
            what = set(a.split("=", 1)[1].split(","))
        elif a.startswith("--light="):
            lights = a.split("=", 1)[1].split(",")
        elif a.startswith("--poses="):
            pose_names = a.split("=", 1)[1].split(",")
        elif not a.startswith("-"):
            ids.append(a)
    ids = ids or ["wren", "ashka"]
    os.makedirs(EVI, exist_ok=True)
    print("[render] SRC", SRC, "EVI", EVI, flush=True)
    for cid in ids:
        arm, meshes = open_char(cid)
        L = landmarks(arm, meshes)
        for light in lights:
            if "turn" in what:
                turnaround(cid, arm, meshes, light)
            if "face" in what:
                face(cid, arm, meshes, L, light)
            if "detail" in what:
                detail(cid, arm, meshes, light)
        if "feet" in what:
            feet(cid, arm, meshes)
        if "tattoo" in what and cid == "ashka":
            tattoo_check(arm, meshes, L)
        if "poses" in what:
            poses(cid, arm, meshes, L, names=pose_names)
    if "lineup" in what:
        lineup(lights)


if __name__ == "__main__":
    main()
