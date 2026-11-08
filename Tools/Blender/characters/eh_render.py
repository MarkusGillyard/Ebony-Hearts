"""Review renders with three light rigs: "stage" (dark blue-grey, cool key, warm rims, soft fill),
"neutral" (grey studio, white key/fill/rim, for judging materials) and "chapel" (Drowned Chapel-like:
cool moonlight from high behind, weak cool front fill, warm candles to the sides, near-black nave);
orthographic turnarounds, perspective close-ups and the fighting-game camera (6 m, 30 degree vertical FOV)."""
import math

import bpy
import numpy as np
from mathutils import Vector

import eh_mesh as M

BG = (0.035, 0.045, 0.06)     # linear, reads as a dark blue-grey
RIGS = {
    "stage": {"bg": BG, "floor": (0.03, 0.036, 0.046)},
    "neutral": {"bg": (0.11, 0.11, 0.11), "floor": (0.16, 0.16, 0.16)},
    "chapel": {"bg": (0.006, 0.009, 0.014), "floor": (0.045, 0.05, 0.06)},
}


def setup_stage(res=(1024, 1024), samples=48, floor=True, fill=0.35, rim=1.0, rig="stage"):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.taa_render_samples = samples
    except AttributeError:
        pass
    for attr, val in (("use_shadows", True), ("use_raytracing", True)):
        if hasattr(sc.eevee, attr):
            setattr(sc.eevee, attr, val)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = 0.0
    world = sc.world or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bgn = world.node_tree.nodes.get("Background")
    bgn.inputs["Color"].default_value = (*RIGS[rig]["bg"], 1.0)
    bgn.inputs["Strength"].default_value = 1.0
    for ob in list(bpy.data.objects):
        if ob.name.startswith("STAGE_") and ob.type != "CAMERA":
            bpy.data.objects.remove(ob)

    def area(name, energy, color, loc, target, size):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.color = color
        ld.size = size
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(ob)
        return ob

    def point(name, energy, color, loc, radius):
        ld = bpy.data.lights.new(name, "POINT")
        ld.energy = energy
        ld.color = color
        ld.shadow_soft_size = radius
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        sc.collection.objects.link(ob)
        return ob

    if rig == "stage":
        area("STAGE_KeyCool", 560, (0.78, 0.87, 1.0), (-2.6, -3.2, 3.6), (0, 0, 1.0), 2.2)
        area("STAGE_RimWarm", 800 * rim, (1.0, 0.72, 0.45), (2.4, 3.0, 2.6), (0, 0, 1.2), 1.5)
        area("STAGE_RimWarm2", 350 * rim, (1.0, 0.78, 0.55), (-2.8, 2.2, 2.2), (0, 0, 1.2), 1.2)
        if fill:
            area("STAGE_Fill", 360 * fill, (0.9, 0.93, 1.0), (1.8, -4.0, 1.4), (0, 0, 1.0), 4.0)
    elif rig == "neutral":
        area("STAGE_Key", 620, (1.0, 1.0, 1.0), (-2.4, -3.4, 3.2), (0, 0, 1.0), 2.4)
        area("STAGE_Fill", 260, (1.0, 1.0, 1.0), (2.6, -3.2, 1.6), (0, 0, 1.0), 3.5)
        area("STAGE_Rim", 520, (1.0, 1.0, 1.0), (1.2, 3.4, 2.8), (0, 0, 1.2), 2.0)
        area("STAGE_Top", 160, (1.0, 1.0, 1.0), (0.0, 0.0, 4.0), (0, 0, 0.0), 3.0)
    elif rig == "chapel":
        # moon through the rose window: high behind (+Y), travelling towards the camera
        ld = bpy.data.lights.new("STAGE_Moon", "SUN")
        ld.energy = 2.2
        ld.color = (0.6, 0.7, 1.0)
        ld.angle = math.radians(3.0)
        ob = bpy.data.objects.new("STAGE_Moon", ld)
        ob.rotation_euler = Vector((-0.03, -0.8656, -0.4998)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(ob)
        area("STAGE_CoolFill", 140, (0.55, 0.65, 0.85), (0.0, -5.5, 4.5), (0, 2.0, 1.0), 6.0)
        point("STAGE_CandleL", 14, (1.0, 0.56, 0.24), (-2.2, 0.6, 1.1), 0.05)
        point("STAGE_CandleR", 10, (1.0, 0.56, 0.24), (2.4, 1.4, 0.9), 0.05)
    else:
        raise KeyError(rig)
    if floor:
        me = bpy.data.meshes.new("STAGE_Floor")
        me.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
        fl = bpy.data.objects.new("STAGE_Floor", me)
        mat = bpy.data.materials.new("STAGE_FloorMat")
        mat.use_nodes = True
        p = mat.node_tree.nodes["Principled BSDF"]
        p.inputs["Base Color"].default_value = (*RIGS[rig]["floor"], 1)
        p.inputs["Roughness"].default_value = 0.7
        me.materials.append(mat)
        sc.collection.objects.link(fl)
    cam = bpy.data.objects.get("STAGE_Cam")
    if cam is None:
        cam = bpy.data.objects.new("STAGE_Cam", bpy.data.cameras.new("STAGE_Cam"))
        sc.collection.objects.link(cam)
    cam.data.clip_start, cam.data.clip_end = 0.02, 200
    sc.camera = cam
    return cam


UE_RIM = (0.35, 0.42, 0.60)


def add_ue_rim(materials, intensity=0.35):
    """Adds the game's stylised rim to character materials for the evidence renders: Unreal's
    M_Character master adds RimColor * Fresnel(exponent 4) * RimIntensity (0.35; 0 on eyes) as
    emission (Tools/Unreal/build_characters.py). Applied identically to every build rendered."""
    for mat in materials:
        if mat is None or not mat.use_nodes or mat.get("eh_rim") or mat.name.endswith("_Eyes"):
            continue
        nt = mat.node_tree
        p = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if p is None:
            continue
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.5
        nm = next((n for n in nt.nodes if n.type == "NORMAL_MAP"), None)
        if nm is not None:
            nt.links.new(nm.outputs["Normal"], lw.inputs["Normal"])
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = 4.0
        nt.links.new(lw.outputs["Facing"], pw.inputs[0])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = intensity
        nt.links.new(pw.outputs[0], mul.inputs[0])
        p.inputs["Emission Color"].default_value = (*UE_RIM, 1.0)
        nt.links.new(mul.outputs[0], p.inputs["Emission Strength"])
        mat["eh_rim"] = 1


def look_at(cam, eye, target):
    cam.location = Vector(eye)
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def bbox(objs):
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in objs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        a = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", a)
        ev.to_mesh_clear()
        Mw = np.array(ob.matrix_world)
        P = a.reshape(-1, 3) @ Mw[:3, :3].T + Mw[:3, 3]
        if len(P):
            lo = np.minimum(lo, P.min(0))
            hi = np.maximum(hi, P.max(0))
    return lo, hi


def ortho_view(cam, center, view_dir, height, aspect=1.0):
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = height * max(1.0, aspect)
    v = Vector(view_dir).normalized()
    look_at(cam, Vector(center) + v * 15, Vector(center))


def persp_view(cam, eye, target, fov_v_deg=None, lens=None):
    cam.data.type = "PERSP"
    cam.data.sensor_fit = "VERTICAL"
    if fov_v_deg is not None:
        cam.data.angle_y = math.radians(fov_v_deg)
    if lens is not None:
        cam.data.lens = lens
    look_at(cam, eye, target)


def hide(objs, hidden=True):
    for o in objs:
        o.hide_render = hidden
        o.hide_viewport = hidden
