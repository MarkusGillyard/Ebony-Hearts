"""Builds /Game/Maps/DrownedChapel from the Chapel source export (sourceart/chapel: export/*.fbx, textures/*.png,
layout.json) and sets up materials, lighting, fog and post-processing. Run in the editor:
    bin/editor_py.sh Tools/Unreal/build_level.py editor
Without the source export it builds a clearly labelled graybox so the game remains runnable.
"""
import json
import os

import unreal

WS = os.environ["EH_WS"]
CHAPEL = os.path.join(WS, "sourceart", "chapel")
MAP = "/Game/Maps/DrownedChapel"
MATS = "/Game/Chapel/Materials"

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


def log(msg):
    unreal.log("EHLEVEL " + msg)


def setp(obj, name, value):
    """Sets an editor property, reporting (not failing on) names that differ between engine versions."""
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception as exc:
        log(f"WARN property {type(obj).__name__}.{name}: {exc}")
        return False


def to_ue(loc_m):
    return unreal.Vector(loc_m[0] * 100.0, -loc_m[1] * 100.0, loc_m[2] * 100.0)


def spawn(cls, loc, rot=unreal.Rotator(0, 0, 0), label=None):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = eas.spawn_actor_from_class(cls, loc, rot)
    if label:
        a.set_actor_label(label)
    return a


def spawn_mesh(mesh, loc, rot, scale, label=None, cast_shadow=True):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    a = eas.spawn_actor_from_object(mesh, loc, rot)
    a.set_actor_scale3d(scale)
    if label:
        a.set_actor_label(label)
    comp = a.static_mesh_component
    comp.set_editor_property("cast_shadow", cast_shadow)
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    return a


# ------------------------------------------------------------------------------------------------ materials
WHITE = "/Engine/EngineResources/WhiteSquareTexture"
FLATN = "/Engine/EngineMaterials/DefaultNormal"


def fresh_material(name):
    path = f"{MATS}/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    return tools.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())


def tex_param(mat, name, x, y, default, sampler=None):
    t = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    t.set_editor_property("parameter_name", name)
    if sampler is not None:
        t.set_editor_property("sampler_type", sampler)
    t.set_editor_property("texture", unreal.load_asset(default))
    return t


def scalar(mat, name, value, x, y):
    s = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
    s.set_editor_property("parameter_name", name)
    s.set_editor_property("default_value", value)
    return s


def const(mat, value, x, y):
    c = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, x, y)
    c.set_editor_property("r", value)
    return c


def op(mat, cls, a, b, x, y, a_out="", b_out=""):
    e = mel.create_material_expression(mat, cls, x, y)
    mel.connect_material_expressions(a, a_out, e, "A")
    mel.connect_material_expressions(b, b_out, e, "B")
    return e


def lerp3(mat, a, b, alpha, x, y, a_out="", b_out="", alpha_out=""):
    e = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, x, y)
    mel.connect_material_expressions(a, a_out, e, "A")
    mel.connect_material_expressions(b, b_out, e, "B")
    mel.connect_material_expressions(alpha, alpha_out, e, "Alpha")
    return e


def build_surface_master():
    """Lit opaque surface: vertex R = cavity AO, G = edge wear; below WetHeight (world cm) it darkens and gets glossy."""
    mat = fresh_material("M_ChapelSurface")
    d = tex_param(mat, "BaseColor", -1400, -300, WHITE)
    n = tex_param(mat, "Normal", -1400, 100, FLATN, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm = tex_param(mat, "ORM", -1400, 400, WHITE, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    vc = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -1400, 700)
    one = const(mat, 1.0, -1200, 800)
    ao = lerp3(mat, one, vc, scalar(mat, "AOStrength", 0.6, -1200, 700), -1000, 700, "", "R")
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -1200, -500)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    base = op(mat, unreal.MaterialExpressionMultiply, d, tint, -1000, -350, "RGB")
    base = op(mat, unreal.MaterialExpressionMultiply, base, ao, -850, -300)
    edge = op(mat, unreal.MaterialExpressionMultiply, vc, scalar(mat, "EdgeLift", 0.10, -1200, 900), -1000, 900, "G")
    base = op(mat, unreal.MaterialExpressionAdd, base, edge, -700, -250)
    wpos = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -1500, 1100)
    z = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -1350, 1100)
    z.set_editor_property("r", False)
    z.set_editor_property("g", False)
    z.set_editor_property("b", True)
    mel.connect_material_expressions(wpos, "", z, "")
    wet_h = scalar(mat, "WetHeight", 30.0, -1350, 1250)
    diff = op(mat, unreal.MaterialExpressionSubtract, wet_h, z, -1150, 1150)
    wet = op(mat, unreal.MaterialExpressionDivide, diff, wet_h, -1000, 1150)
    sat = mel.create_material_expression(mat, unreal.MaterialExpressionSaturate, -850, 1150)
    mel.connect_material_expressions(wet, "", sat, "")
    dark = lerp3(mat, one, scalar(mat, "WetDarken", 0.55, -1000, 1300), sat, -700, 1100)
    base = op(mat, unreal.MaterialExpressionMultiply, base, dark, -500, -200)
    mel.connect_material_property(base, "", MP.MP_BASE_COLOR)
    mel.connect_material_property(n, "RGB", MP.MP_NORMAL)
    mel.connect_material_property(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    rough = op(mat, unreal.MaterialExpressionMultiply, orm, scalar(mat, "RoughnessScale", 1.0, -1200, 500), -1000, 450, "G")
    rough2 = lerp3(mat, rough, scalar(mat, "WetRoughness", 0.18, -1000, 600), sat, -700, 450)
    mel.connect_material_property(rough2, "", MP.MP_ROUGHNESS)
    mel.connect_material_property(orm, "B", MP.MP_METALLIC)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


def build_emissive_master():
    mat = fresh_material("M_ChapelGlass")
    setp(mat, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    d = tex_param(mat, "BaseColor", -600, 0, WHITE)
    e = op(mat, unreal.MaterialExpressionMultiply, d, scalar(mat, "Emissive", 10.0, -600, 250), -300, 50, "RGB")
    mel.connect_material_property(e, "", MP.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


def build_flame_master():
    mat = fresh_material("M_ChapelFlame")
    setp(mat, "shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    setp(mat, "blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    setp(mat, "two_sided", True)
    d = tex_param(mat, "BaseColor", -700, 0, WHITE)
    rgb = op(mat, unreal.MaterialExpressionMultiply, d, d, -450, 0, "RGB", "A")
    e = op(mat, unreal.MaterialExpressionMultiply, rgb, scalar(mat, "Emissive", 12.0, -700, 250), -250, 50)
    mel.connect_material_property(e, "", MP.MP_EMISSIVE_COLOR)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


def build_decal_master():
    mat = fresh_material("M_ChapelDecal")
    setp(mat, "blend_mode", unreal.BlendMode.BLEND_MASKED)
    d = tex_param(mat, "BaseColor", -600, 0, WHITE)
    orm = tex_param(mat, "ORM", -600, 300, WHITE, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    mel.connect_material_property(d, "RGB", MP.MP_BASE_COLOR)
    mel.connect_material_property(d, "A", MP.MP_OPACITY_MASK)
    mel.connect_material_property(orm, "G", MP.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


def build_water_master(normal_tex):
    """Thin translucent sheen: drifting ripple speculars over the wet floor, low opacity so feet stay readable."""
    mat = fresh_material("M_ChapelWater")
    setp(mat, "blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    setp(mat, "translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
    tc = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1300, 0)
    samples = []
    for i, (sx, sy) in enumerate(((0.006, 0.004), (-0.005, 0.007))):
        pan = mel.create_material_expression(mat, unreal.MaterialExpressionPanner, -1100, -100 + 250 * i)
        setp(pan, "speed_x", sx)
        setp(pan, "speed_y", sy)
        mel.connect_material_expressions(tc, "", pan, "Coordinate")
        smp = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -900, -100 + 250 * i)
        setp(smp, "texture", normal_tex)
        setp(smp, "sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        mel.connect_material_expressions(pan, "", smp, "UVs")
        samples.append(smp)
    nsum = op(mat, unreal.MaterialExpressionAdd, samples[0], samples[1], -650, 0, "RGB", "RGB")
    nn = mel.create_material_expression(mat, unreal.MaterialExpressionNormalize, -500, 0)
    mel.connect_material_expressions(nsum, "", nn, "")
    mel.connect_material_property(nn, "", MP.MP_NORMAL)
    col = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -500, -250)
    setp(col, "parameter_name", "Tint")
    setp(col, "default_value", unreal.LinearColor(0.012, 0.018, 0.026, 1))
    mel.connect_material_property(col, "", MP.MP_BASE_COLOR)
    mel.connect_material_property(scalar(mat, "Roughness", 0.06, -500, 250), "", MP.MP_ROUGHNESS)
    mel.connect_material_property(scalar(mat, "Specular", 0.6, -500, 350), "", MP.MP_SPECULAR)
    mel.connect_material_property(scalar(mat, "Opacity", 0.22, -500, 450), "", MP.MP_OPACITY)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


SURFACE_PARAMS = {
    # material: (AOStrength, EdgeLift, WetHeight cm (0 = no wet line), RoughnessScale, tint)
    "M_StoneAshlar": (0.7, 0.04, 30.0, 1.0, (0.90, 0.92, 1.0)),
    "M_StoneDressed": (0.6, 0.12, 30.0, 1.0, (0.92, 0.94, 1.0)),
    "M_FloorFlags": (0.5, 0.0, 0.0, 0.85, (0.85, 0.88, 0.95)),
    "M_WoodPew": (0.5, 0.05, 30.0, 1.0, (0.85, 0.85, 0.9)),
    "M_IronAged": (0.5, 0.06, 0.0, 1.0, (1.0, 1.0, 1.0)),
    "M_ClothAltar": (0.5, 0.0, 0.0, 1.0, (1.0, 1.0, 1.0)),
    "M_CandleWax": (0.3, 0.0, 0.0, 1.0, (1.0, 1.0, 1.0)),
}


def import_textures():
    tex_dir = os.path.join(CHAPEL, "textures")
    textures = {}
    for f in sorted(os.listdir(tex_dir)):
        if not f.lower().endswith(".png"):
            continue
        name = os.path.splitext(f)[0]
        task = unreal.AssetImportTask()
        task.filename = os.path.join(tex_dir, f)
        task.destination_path = "/Game/Chapel/Textures"
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        tools.import_asset_tasks([task])
        tex = unreal.load_asset(f"/Game/Chapel/Textures/{name}")
        if name.endswith("_N"):
            setp(tex, "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            setp(tex, "srgb", False)
            setp(tex, "flip_green_channel", True)   # source maps are OpenGL; Unreal expects DirectX
        elif name.endswith("_ORM"):
            setp(tex, "compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
            setp(tex, "srgb", False)
        setp(tex, "lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
        eal.save_asset(tex.get_path_name(), only_if_is_dirty=False)
        textures[name] = tex
    log(f"textures {len(textures)}")
    return textures


def make_instances(textures, layout):
    masters = {
        "surface": build_surface_master(),
        "glass": build_emissive_master(),
        "flame": build_flame_master(),
        "decal": build_decal_master(),
        "water": build_water_master(textures.get("T_Water_N")),
    }
    emissive = layout.get("lights", {}).get("window_emissive", {})
    names = sorted({m for slots in layout["material_slots"].values() for m in slots})
    out = {}
    for m in names:
        short = m[2:] if m.startswith("M_") else m
        kind = "glass" if m.startswith("M_Glass") else ("flame" if m == "M_CandleFlame" else ("decal" if m == "M_DecalGrime" else ("water" if m == "M_Water" else "surface")))
        mi_path = f"{MATS}/MI_{short}"
        if eal.does_asset_exist(mi_path):
            eal.delete_asset(mi_path)
        mi = tools.create_asset(f"MI_{short}", MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", masters[kind])
        if kind != "water":
            for suffix, param in (("_D", "BaseColor"), ("_N", "Normal"), ("_ORM", "ORM")):
                t = textures.get(f"T_{short}{suffix}")
                if t is not None and (kind in ("surface", "decal") or param == "BaseColor") and not (kind == "decal" and param == "Normal"):
                    mel.set_material_instance_texture_parameter_value(mi, param, t)
        if kind in ("glass", "flame"):
            mel.set_material_instance_scalar_parameter_value(mi, "Emissive", float(emissive.get(m, {}).get("emissive_scale", 6.0)))
        if kind == "surface" and m in SURFACE_PARAMS:
            ao, edge, wet, rough, tint = SURFACE_PARAMS[m]
            mel.set_material_instance_scalar_parameter_value(mi, "AOStrength", ao)
            mel.set_material_instance_scalar_parameter_value(mi, "EdgeLift", edge)
            mel.set_material_instance_scalar_parameter_value(mi, "WetHeight", max(wet, 0.001))
            mel.set_material_instance_scalar_parameter_value(mi, "RoughnessScale", rough)
            mel.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(tint[0], tint[1], tint[2], 1.0))
            if wet <= 0.0:
                mel.set_material_instance_scalar_parameter_value(mi, "WetDarken", 1.0)
        eal.save_asset(mi_path, only_if_is_dirty=False)
        out[m] = mi
    log(f"material instances {len(out)}")
    return out


def import_meshes(materials, layout):
    meshes = {}
    for name, info in sorted(layout["meshes"].items()):
        task = unreal.AssetImportTask()
        task.filename = os.path.join(CHAPEL, info["fbx"])
        task.destination_path = "/Game/Chapel/Meshes"
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        opts = unreal.FbxImportUI()
        opts.import_mesh = True
        opts.import_materials = False
        opts.import_textures = False
        opts.import_as_skeletal = False
        smd = opts.static_mesh_import_data
        smd.combine_meshes = True
        smd.generate_lightmap_u_vs = False
        smd.auto_generate_collision = False
        smd.import_uniform_scale = 1.0
        setp(smd, "normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        setp(smd, "vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
        setp(smd, "convert_scene", True)
        setp(smd, "force_front_x_axis", False)
        task.options = opts
        tools.import_asset_tasks([task])
        mesh = unreal.load_asset(f"/Game/Chapel/Meshes/{name}")
        if mesh is None:
            log(f"FAIL import {name}")
            continue
        for i, m in enumerate(layout["material_slots"].get(name, [])):
            if m in materials:
                mesh.set_material(i, materials[m])
        eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
        meshes[name] = mesh
    log(f"meshes {len(meshes)}")
    return meshes


def place(meshes, layout):
    placed = 0
    for i, inst in enumerate(layout["instances"]):
        mesh = meshes.get(inst["mesh"])
        if mesh is None:
            continue
        ue = inst["ue"]
        p, y, r = ue["rotation_pitch_yaw_roll_deg"]
        no_shadow = inst["mesh"] in ("SM_Water", "SM_RoseGlass", "SM_LancetGlass", "SM_ClerestoryGlass") or inst["mesh"].startswith("SM_Decal")
        spawn_mesh(mesh, unreal.Vector(*ue["location_cm"]), unreal.Rotator(roll=r, pitch=p, yaw=y), unreal.Vector(*ue["scale"]),
                   f"{inst['mesh']}_{i:03d}", cast_shadow=not no_shadow)
        placed += 1
    log(f"placed {placed}")


def build_graybox():
    plane = unreal.load_asset("/Engine/BasicShapes/Plane")
    spawn_mesh(plane, unreal.Vector(0, -600, 0), unreal.Rotator(0, 0, 0), unreal.Vector(40, 40, 1), "GRAYBOX_Floor", False)
    log("graybox placed")


def set_color(comp, c):
    comp.set_light_color(unreal.LinearColor(c[0], c[1], c[2], 1.0), True)


def build_lighting(layout):
    L = (layout or {}).get("lights", {})
    moon = L.get("moonlight", {})
    mp, my, mr = moon.get("ue_rotation_pitch_yaw_roll_deg", [-21.15, 92.16, 0.0])
    a = spawn(unreal.DirectionalLight, unreal.Vector(0, -1500, 1500), unreal.Rotator(roll=mr, pitch=mp, yaw=my), "Moonlight")
    c = a.light_component
    setp(c, "intensity", float(moon.get("ue_intensity_lux", 4.0)))
    set_color(c, moon.get("color_linear", [0.6, 0.7, 1.0]))
    setp(c, "cast_shadows", True)
    setp(c, "dynamic_shadow_distance_movable_light", 3600.0)
    setp(c, "dynamic_shadow_cascades", 2)
    setp(c, "forward_shading_priority", 1)   # the moon drives translucency/fog; fills must not compete
    # Camera-side fill keeps the fighters' fronts readable against the backlit nave; it casts no shadows.
    fill = spawn(unreal.DirectionalLight, unreal.Vector(0, 800, 600), unreal.Rotator(roll=0, pitch=-18, yaw=-100), "FighterFill")
    setp(fill.light_component, "intensity", float(os.environ.get("EH_FILL_LUX", "0.8")))
    set_color(fill.light_component, [0.55, 0.65, 0.85])
    setp(fill.light_component, "cast_shadows", False)
    for fl in L.get("cool_fills", []):
        loc = to_ue(fl["location_m"])
        if fl.get("type", "").startswith("rect"):
            rot = unreal.MathLibrary.find_look_at_rotation(loc, to_ue(fl["aim_at_m"]))
            ra = spawn(unreal.RectLight, loc, rot, fl["name"])
            lc = ra.light_component
            setp(lc, "source_width", fl["size_m"][0] * 100.0)
            setp(lc, "source_height", fl["size_m"][1] * 100.0)
        else:
            ra = spawn(unreal.PointLight, loc, unreal.Rotator(0, 0, 0), fl["name"])
            lc = ra.light_component
            setp(lc, "source_radius", fl.get("radius_m", 1.0) * 100.0)
        setp(lc, "intensity_units", unreal.LightUnits.CANDELAS)
        setp(lc, "intensity", float(fl.get("ue_intensity_cd", 10.0)))
        set_color(lc, fl["color_linear"])
        setp(lc, "cast_shadows", False)
        setp(lc, "attenuation_radius", float(fl.get("ue_attenuation_radius_cm", 2400.0)))
    for i, cd in enumerate(L.get("candles", [])):
        pl = spawn(unreal.PointLight, unreal.Vector(*cd["ue"]), unreal.Rotator(0, 0, 0), f"Candle_{i:02d}")
        lc = pl.light_component
        setp(lc, "intensity_units", unreal.LightUnits.CANDELAS)
        setp(lc, "intensity", float(cd.get("ue_intensity_cd", 8.0)))
        set_color(lc, cd["color_linear"])
        setp(lc, "attenuation_radius", float(cd.get("ue_attenuation_radius_cm", 350)))
        setp(lc, "source_radius", float(cd.get("source_radius_cm", 2.0)))
        setp(lc, "cast_shadows", False)
    fog_cfg = L.get("fog", {})
    fog = spawn(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -50), unreal.Rotator(0, 0, 0), "NaveFog")
    fc = fog.component
    setp(fc, "fog_density", float(fog_cfg.get("exponential_height_fog_density", 0.02)))
    setp(fc, "fog_height_falloff", 0.3)
    setp(fc, "fog_inscattering_luminance", unreal.LinearColor(0.008, 0.011, 0.018, 1))
    setp(fc, "start_distance", 900.0)
    ppv = spawn(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0), "ChapelGrade")
    setp(ppv, "unbound", True)
    s = ppv.settings
    for name, value in (
        ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
        ("auto_exposure_apply_physical_camera_exposure", False),
        ("auto_exposure_bias", float(os.environ.get("EH_EXPOSURE_BIAS", "1.0"))),
        ("bloom_intensity", 0.6),
        ("bloom_threshold", 1.0),
        ("vignette_intensity", 0.5),
        ("film_grain_intensity", 0.0),
        ("scene_fringe_intensity", 0.0),
        ("color_saturation", unreal.Vector4(0.9, 0.93, 1.0, 1.0)),
        ("color_gain_shadows", unreal.Vector4(0.9, 0.96, 1.1, 1.0)),
        ("color_gain_highlights", unreal.Vector4(1.06, 1.0, 0.94, 1.0)),
        ("ambient_occlusion_intensity", 0.6),
        ("screen_space_reflection_intensity", 100.0),
        ("screen_space_reflection_quality", 50.0),
    ):
        setp(s, "override_" + name, True)
        setp(s, name, value)
    ppv.settings = s
    log("lighting placed")


def main():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if eal.does_asset_exist(MAP):
        # The map may be the open startup map, so it is cleared in place rather than deleted.
        if not les.load_level(MAP):
            raise RuntimeError("load_level failed")
        # Keep the world settings and the level's builder brush, but not volumes: a post-process volume is a brush too,
        # and leaving old ones behind stacks several unbound grades that blend in no defined order.
        doomed = [a for a in eas.get_all_level_actors()
                  if not isinstance(a, unreal.WorldSettings) and (not isinstance(a, unreal.Brush) or isinstance(a, unreal.Volume))]
        eas.destroy_actors(doomed)
        log(f"cleared {len(doomed)} actors")
    elif not les.new_level(MAP):
        raise RuntimeError("new_level failed")
    layout = None
    layout_path = os.path.join(CHAPEL, "layout.json")
    if os.path.exists(layout_path):
        with open(layout_path) as f:
            layout = json.load(f)
        textures = import_textures()
        materials = make_instances(textures, layout)
        meshes = import_meshes(materials, layout)
        place(meshes, layout)
    else:
        build_graybox()
    build_lighting(layout)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    setp(world.get_world_settings(), "default_game_mode", unreal.load_class(None, "/Script/EbonyHearts.EHGameMode"))
    if not les.save_current_level():
        raise RuntimeError("save failed")
    log("DONE " + ("chapel" if layout else "graybox"))


try:
    main()
except Exception as exc:  # report and still close the editor so the build script does not hang
    unreal.log_error("EHLEVEL FAIL " + repr(exc))
    raise
finally:
    if os.environ.get("EH_QUIT_EDITOR") == "1":
        unreal.SystemLibrary.quit_editor()
