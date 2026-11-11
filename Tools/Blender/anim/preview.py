"""Renders review frames of authored animations from the game's camera side (Workbench, fast)."""
import math
import os

import bpy
from mathutils import Vector


def setup_camera(target_height=1.0, distance=4.2, turn_deg=12.0):
    scene = bpy.context.scene
    cam = bpy.data.objects.get("ReviewCam")
    if cam is None:
        cam = bpy.data.objects.new("ReviewCam", bpy.data.cameras.new("ReviewCam"))
        scene.collection.objects.link(cam)
    # The game camera sees the fighter's right side (character faces -Y, right is -X) with a slight turn toward it.
    ang = math.radians(turn_deg)
    cam.location = Vector((-distance * math.cos(ang), -distance * math.sin(ang), target_height + 0.2))
    direction = Vector((0, 0, target_height)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = 480
    scene.render.resolution_y = 640
    scene.render.film_transparent = False
    return cam


def render_frames(frames, out_dir, tag):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for f in frames:
        bpy.context.scene.frame_set(f)
        path = os.path.join(out_dir, f"{tag}_{f:03d}.png")
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths.append(path)
    return paths


def render_closeups(arm, frames, out_dir, tag, parts=(("hand_l", 0.5), ("hand_r", 0.5), ("head", 0.7))):
    """Close-ups of the hands and head (wrists, fists, neck) from the game camera's side and from the front."""
    scene = bpy.context.scene
    cam = setup_camera()
    rx, ry, lens = scene.render.resolution_x, scene.render.resolution_y, cam.data.lens
    scene.render.resolution_x = scene.render.resolution_y = 400
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for f in frames:
        scene.frame_set(f)
        print("JOINTS", tag, f, joint_report(arm))
        for bone, dist in parts:
            p = arm.matrix_world @ arm.pose.bones[bone].head
            if bone == "head":
                p = p + Vector((0, 0, 0.05))
            for view, off in (("side", Vector((-1.0, -0.3, 0.15))), ("front", Vector((-0.3, -1.0, 0.1)))):
                cam.location = p + off.normalized() * dist
                cam.rotation_euler = (p - cam.location).to_track_quat("-Z", "Y").to_euler()
                path = os.path.join(out_dir, f"{tag}_{f:03d}_{bone}_{view}.png")
                scene.render.filepath = path
                bpy.ops.render.render(write_still=True)
                paths.append(path)
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    return paths


def bend(arm, parent, child):
    """Degrees between two bones' long axes in the pose, minus the same at rest (0 = as straight as the rest pose)."""
    y = Vector((0, 1, 0))
    now = (arm.pose.bones[parent].matrix.to_3x3() @ y).angle(arm.pose.bones[child].matrix.to_3x3() @ y)
    rest = (arm.data.bones[parent].matrix_local.to_3x3() @ y).angle(arm.data.bones[child].matrix_local.to_3x3() @ y)
    return math.degrees(now - rest)


def joint_report(arm):
    """Wrist bends off the forearm, neck and head off the chest, and how far each thumb tip sits from the curled index."""
    out = [f"wrist_{s} {bend(arm, f'lowerarm_{s}', f'hand_{s}'):+5.1f}" for s in ("l", "r")]
    out.append(f"neck {bend(arm, 'spine_03', 'neck_01'):+5.1f} head {bend(arm, 'neck_01', 'head'):+5.1f} "
               f"chest-head {bend(arm, 'spine_03', 'head'):+5.1f}")
    for s in ("l", "r"):
        pb = arm.pose.bones
        tip = pb[f"thumb_03_{s}"].tail
        idx = (pb[f"index_02_{s}"].head + pb[f"middle_02_{s}"].head) * 0.5
        out.append(f"thumb_{s} {(tip - idx).length * 100:4.1f}cm")
    return " | ".join(out)


def joint_max(arm, total):
    """The worst wrist bend (either hand) and neck-to-head bend off the chest over a clip, with their frames."""
    worst = {"wrist": (0.0, 0, ""), "neck": (0.0, 0)}
    for f in range(1, total + 1):
        bpy.context.scene.frame_set(f)
        for s in ("l", "r"):
            b = abs(bend(arm, f"lowerarm_{s}", f"hand_{s}"))
            if b > worst["wrist"][0]:
                worst["wrist"] = (b, f, s)
        b = abs(bend(arm, "spine_03", "head"))
        if b > worst["neck"][0]:
            worst["neck"] = (b, f)
    return worst
