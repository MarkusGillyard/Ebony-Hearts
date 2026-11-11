"""Review set-up for The Drowned Chapel: approximate moonlight + candle lighting,
stand-in fighter capsules and EEVEE renders from the gameplay camera keys.
Nothing here is exported; it lives in the 'Review' collection of the .blend."""
import math
import os

import bmesh
import bpy
from mathutils import Vector

import chapel_config as C
import chapel_geo as G


def _coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def _capsule(name, height, radius, x, coll, mat):
    prof = []
    n_h = 6
    for i in range(n_h + 1):
        a = -math.pi / 2 + (math.pi / 2) * i / n_h
        prof.append((max(radius * math.cos(a), 1e-4), radius + radius * math.sin(a)))
    for i in range(n_h + 1):
        a = (math.pi / 2) * i / n_h
        prof.append((max(radius * math.cos(a), 1e-4), height - radius + radius * math.sin(a)))
    bm = G.bm_lathe(prof, n=24)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = (x, 0.0, 0.0)
    coll.objects.link(ob)
    return ob


def _point(name, loc, watts, colour, radius, coll, shadow=True):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = watts
    ld.color = colour
    ld.shadow_soft_size = radius
    ld.use_shadow = shadow
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def _aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup(lights, cams, look=None):
    look = look or {}
    sc = bpy.context.scene
    coll = _coll("Review")
    # fighter stand-ins: dark neutral grey
    mat = bpy.data.materials.new("Review_FighterGrey")
    try:
        mat.use_nodes = True
    except Exception:
        pass
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    g = look.get("fighter_grey", 0.05)
    bsdf.inputs["Base Color"].default_value = (g, g, g, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.55
    _capsule("Fighter_178", 1.78, 0.27, -1.4, coll, mat)
    _capsule("Fighter_170", 1.70, 0.26, 1.4, coll, mat)

    # moonlight (sun)
    moon = lights["moonlight"]
    sd = bpy.data.lights.new("Moonlight", "SUN")
    sd.energy = look.get("moon_strength", moon["blender_sun_strength"])
    sd.color = moon["color_linear"]
    sd.angle = math.radians(0.6)
    sd.use_shadow = True
    sun = bpy.data.objects.new("Moonlight", sd)
    sun.rotation_euler = Vector(moon["travel_direction_blender"]).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(sun)

    cs = look.get("candle_scale", 1.0)
    for i, c in enumerate(lights["candles"]):
        _point("Candle_%02d" % i, c["location_m"], c["blender_watts"] * cs, c["color_linear"], 0.04, coll,
               shadow=c["cast_shadows"])
    for f in lights["cool_fills"]:
        if f["type"].startswith("rect"):
            ld = bpy.data.lights.new(f["name"], "AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = f["size_m"]
            ld.energy = f["blender_watts"] * look.get("fill_scale", 1.0)
            ld.color = f["color_linear"]
            ld.use_shadow = f["cast_shadows"]
            ld.volume_factor = f.get("volume_factor", 0.0)
            ob = bpy.data.objects.new(f["name"], ld)
            ob.location = f["location_m"]
            _aim(ob, f["aim_at_m"])
            coll.objects.link(ob)
        else:
            ob = _point(f["name"], f["location_m"], f["blender_watts"] * look.get("fill_scale", 1.0),
                        f["color_linear"], f["radius_m"], coll, shadow=f["cast_shadows"])
            ob.data.volume_factor = f.get("volume_factor", 0.0)

    # world: near-black blue ambient + thin volumetric haze
    w = bpy.data.worlds.new("Review_World")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    bg = nt.nodes.get("Background")
    a = look.get("ambient", 0.010)
    bg.inputs["Color"].default_value = (a * 0.7, a * 0.85, a * 1.4, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.get("World Output")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = look.get("fog_density", 0.010)
    vol.inputs["Anisotropy"].default_value = look.get("fog_anisotropy", 0.45)
    vol.inputs["Color"].default_value = (0.70, 0.78, 1.0, 1.0)
    nt.links.new(vol.outputs[0], out.inputs["Volume"])

    # cameras
    for ck in cams:
        cd = bpy.data.cameras.new("CAM_" + ck["name"])
        cd.sensor_fit = "VERTICAL"
        cd.angle_y = math.radians(ck["vertical_fov_deg"])
        cd.clip_start = 0.1
        cd.clip_end = 200.0
        ob = bpy.data.objects.new("CAM_" + ck["name"], cd)
        ob.location = ck["location_m"]
        ob.rotation_euler = [math.radians(v) for v in ck["rotation_deg"]]
        coll.objects.link(ob)
    wide = look.get("wide", {"loc": (-7.4, -6.6, 3.2), "target": (1.2, 15.0, 7.2), "vfov": 58.0})
    cd = bpy.data.cameras.new("CAM_wide_establishing")
    cd.sensor_fit = "VERTICAL"
    cd.angle_y = math.radians(wide["vfov"])
    cd.clip_end = 200.0
    ob = bpy.data.objects.new("CAM_wide_establishing", cd)
    ob.location = wide["loc"]
    _aim(ob, wide["target"])
    coll.objects.link(ob)

    # render settings
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"
    ee = sc.eevee
    ee.taa_render_samples = look.get("samples", 64)
    ee.use_raytracing = True
    try:
        ee.ray_tracing_method = "SCREEN"
        ee.ray_tracing_options.resolution_scale = "1"
        ee.ray_tracing_options.trace_max_roughness = 0.5
    except Exception as e:
        print("[render] raytrace option:", e)
    ee.use_shadows = True
    ee.shadow_ray_count = 2
    ee.shadow_step_count = 8
    ee.use_volumetric_shadows = True
    ee.volumetric_tile_size = "4"
    ee.volumetric_samples = 64
    ee.volumetric_start = 0.5
    ee.volumetric_end = 70.0
    ee.use_fast_gi = True
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = look.get("agx_look", "AgX - Medium High Contrast")
    except Exception as e:
        print("[render] colour management:", e)
    sc.view_settings.exposure = look.get("exposure", 0.0)
    # glass, water and decals must not block moonlight
    no_shadow = {"M_GlassRose", "M_GlassLancet", "M_Water", "M_DecalGrime"}
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.data.materials and all(m and m.name in no_shadow for m in ob.data.materials):
            ob.visible_shadow = False
    return coll


def render(names, prefix=""):
    sc = bpy.context.scene
    os.makedirs(C.EVIDENCE_DIR, exist_ok=True)
    out = []
    for n in names:
        cam = bpy.data.objects.get("CAM_" + n)
        sc.camera = cam
        path = os.path.join(C.EVIDENCE_DIR, "%s%s.png" % (prefix, n))
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print("[render] wrote", path)
    return out
