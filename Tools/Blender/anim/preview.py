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
