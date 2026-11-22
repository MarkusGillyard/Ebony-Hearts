"""Furnishes the Drowned Chapel's interior (stage 2) in /Game/Maps/DrownedChapel. Headless:
    EH_FX_FBX_DIR=<folder with the furnishings' FBX> bin/editor_py.sh Tools/Unreal/build_chapel_furnish.py
then the navigation stage (EH_FP_STAGE=nav Tools/Unreal/adapt_chapel_fp.py). Run after build_chapel_interior.py.

It makes the few material instances the kit lacks (cloth tints, an ember glow, faintly lime-green water, a red flare),
imports the pieces made by Tools/Blender/chapel/chapel_furnish.py, and places them: the kneeler, the two veiled
statues, the forge (hearth, anvil, trough, counter, rack, Dwar's stand-in), the Hall of the Six's six alcoves with
their traces and the blank mural, two devotional boards on the piers, the camp, and a few of the kit's own candles.
Re-running it replaces its own actors (labels FX_*, FXL_*).
"""
import json
import os

import unreal

WS = os.environ["EH_WS"]
SRC = os.environ.get("EH_FX_FBX_DIR", os.path.join(WS, "sourceart", "chapel_furnish"))
MAP = "/Game/Maps/DrownedChapel"
DIR = "/Game/Chapel/Interior"
MATS = "/Game/Chapel/Materials"
TEX = "/Game/Chapel/Textures"

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary

# pieces without collision: small things on shelves, panels on walls, water
NO_COLLISION = {"SM_IX_ForgeWater", "SM_IX_Mural", "SM_IX_Board", "SM_IX_Trace_Wren", "SM_IX_Trace_Ashka",
                "SM_IX_Trace_Mirela", "SM_IX_Trace_Nix", "SM_IX_Trace_Bram"}
HALL_X = (1500, 1740, 1980)
# the Hall of the Six: three alcoves on each side wall, each with its trace; Gorm Tallow's is left empty (no sheet yet)
TRACES = {("W", 1500): "SM_IX_Trace_Wren", ("W", 1740): "SM_IX_Trace_Ashka", ("W", 1980): "SM_IX_Trace_Mirela",
          ("E", 1500): "SM_IX_Trace_Nix", ("E", 1740): "SM_IX_Trace_Bram"}


def log(msg):
    unreal.log("EHFX " + msg)


def setp(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception as exc:
        log(f"WARN {type(obj).__name__}.{name}: {exc}")


def glow_master():
    path = f"{MATS}/M_IX_Glow"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    mat = tools.create_asset("M_IX_Glow", MATS, unreal.Material, unreal.MaterialFactoryNew())
    col = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -700, 0)
    setp(col, "parameter_name", "Color")
    setp(col, "default_value", unreal.LinearColor(1.0, 0.35, 0.08, 1.0))
    k = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 200)
    setp(k, "parameter_name", "Intensity")
    setp(k, "default_value", 6.0)
    em = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, 100)
    mel.connect_material_expressions(col, "", em, "A")
    mel.connect_material_expressions(k, "", em, "B")
    mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    dim = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, -100)
    sc = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -700, -150)
    setp(sc, "r", 0.08)
    mel.connect_material_expressions(col, "", dim, "A")
    mel.connect_material_expressions(sc, "", dim, "B")
    mel.connect_material_property(dim, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -400, 300)
    setp(r, "parameter_name", "Roughness")
    setp(r, "default_value", 0.6)
    mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_asset(path, only_if_is_dirty=False)
    return mat


def instance(name, parent):
    path = f"{MATS}/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    mi = tools.create_asset(name, MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", parent)
    return mi, path


def make_materials():
    surface = unreal.load_asset(f"{MATS}/M_ChapelSurface")
    out = {}
    # cloth (and the blank plaster of the illustration slots): the wax's pale base under a tint, the altar cloth's weave; dry
    for name, tint in (("MI_IX_ClothBlack", (0.03, 0.03, 0.035)), ("MI_IX_ClothBlue", (0.04, 0.16, 0.32)),
                       ("MI_IX_ClothPale", (0.62, 0.6, 0.55)), ("MI_IX_ClothDun", (0.26, 0.2, 0.14)),
                       ("MI_IX_FlareRed", (0.45, 0.05, 0.03)), ("MI_IX_Plaster", (0.5, 0.49, 0.46))):
        mi, path = instance(name, surface)
        mel.set_material_instance_texture_parameter_value(mi, "BaseColor", unreal.load_asset(f"{TEX}/T_CandleWax_D"))
        mel.set_material_instance_texture_parameter_value(mi, "Normal", unreal.load_asset(f"{TEX}/T_ClothAltar_N"))
        mel.set_material_instance_texture_parameter_value(mi, "ORM", unreal.load_asset(f"{TEX}/T_ClothAltar_ORM"))
        mel.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(tint[0], tint[1], tint[2], 1.0))
        mel.set_material_instance_scalar_parameter_value(mi, "WetHeight", 0.001)
        mel.set_material_instance_scalar_parameter_value(mi, "WetDarken", 1.0)
        eal.save_asset(path, only_if_is_dirty=False)
        out["M_" + name[3:]] = mi
    glow = glow_master()
    for name, col, k, rough in (("MI_IX_Ember", (1.0, 0.32, 0.06), 7.0, 0.8), ("MI_IX_LimeWater", (0.42, 0.95, 0.18), 0.9, 0.08)):
        mi, path = instance(name, glow)
        mel.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(col[0], col[1], col[2], 1.0))
        mel.set_material_instance_scalar_parameter_value(mi, "Intensity", k)
        mel.set_material_instance_scalar_parameter_value(mi, "Roughness", rough)
        eal.save_asset(path, only_if_is_dirty=False)
        out["M_" + name[3:]] = mi
    out["M_PH_Blockout"] = unreal.load_asset("/Game/Chapel/Placeholder/M_PH_Blockout")
    log(f"materials {sorted(out)}")
    return out


def material_for(m, extra):
    if m in extra:
        return extra[m]
    mi = unreal.load_asset(f"{MATS}/MI_{m[2:]}")
    if mi is None:
        raise RuntimeError(f"no material instance for {m}")
    return mi


def import_pieces(report, extra):
    meshes = {}
    for name, info in sorted(report.items()):
        if eal.does_asset_exist(f"{DIR}/{name}"):
            eal.delete_asset(f"{DIR}/{name}")
        task = unreal.AssetImportTask()
        task.filename = os.path.join(SRC, name + ".fbx")
        task.destination_path = DIR
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
        mesh = unreal.load_asset(f"{DIR}/{name}")
        if mesh is None:
            raise RuntimeError(f"import failed {name}")
        for i, m in enumerate(info["materials"]):
            mesh.set_material(i, material_for(m, extra))
        if name not in NO_COLLISION:
            setp(mesh.get_editor_property("body_setup"), "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
        meshes[name] = mesh
    log(f"imported {len(meshes)}")
    return meshes


def place(eas, mesh, label, loc, yaw=0.0, scale=unreal.Vector(1, 1, 1)):
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, unreal.Rotator(pitch=0.0, yaw=yaw, roll=0.0))
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_label(label)
    a.set_actor_scale3d(scale)
    comp = a.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    if mesh.get_name() in NO_COLLISION or mesh.get_name().startswith("SM_Candle"):
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    else:
        comp.set_collision_profile_name("BlockAll")
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    a.tags = [unreal.Name("EHInterior")]
    return a


def main():
    report = json.load(open(os.path.join(SRC, "furnish.json")))
    extra = make_materials()
    meshes = import_pieces(report, extra)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not les.load_level(MAP):
        raise RuntimeError("load_level failed")
    gone = 0
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label()
        if lab.startswith("FX_") or lab.startswith("FXL_"):
            eas.destroy_actor(a)
            gone += 1
    log(f"removed {gone} earlier furnishings")
    V = unreal.Vector
    for n in ("SM_IX_Kneeler", "SM_IX_ForgeHearth", "SM_IX_ForgeWork", "SM_IX_ForgeWater", "SM_IX_Dwar", "SM_IX_Mural", "SM_IX_Camp"):
        place(eas, meshes[n], "FX_" + n[6:], V(0, 0, 0))
    for side in (-1, 1):
        place(eas, meshes["SM_IX_Statue"], f"FX_Statue_{'N' if side < 0 else 'S'}", V(side * 390, -1945, 44))
    for wall, y, yaw, inward in (("W", -440, 180.0, -25.0), ("E", -1160, 0.0, 25.0)):
        for x in HALL_X:
            place(eas, meshes["SM_IX_Alcove"], f"FX_Alcove_{wall}{x}", V(x, y, 45), yaw)
            t = TRACES.get((wall, x))
            if t:
                place(eas, meshes[t], f"FX_{t[6:]}", V(x, y + inward, 112), yaw)
            # the hall is tended: a cluster of the kit's candles on each plinth
            cand = unreal.load_asset("/Game/Chapel/Meshes/SM_CandleCluster_C")
            place(eas, cand, f"FX_Candles_{wall}{x}", V(x + 45, y + inward, 112), yaw)
    place(eas, meshes["SM_IX_Board"], "FX_Board_N", V(-738, -400, 160), -90.0)
    place(eas, meshes["SM_IX_Board"], "FX_Board_S", V(738, -400, 160), 90.0)
    # a candle stand by the Threshold Hall's stair, under the hall's light
    stand = unreal.load_asset("/Game/Chapel/Meshes/SM_CandleStand")
    place(eas, stand, "FX_HallCandleStand", V(380, 760, 0))
    l = eas.spawn_actor_from_class(unreal.PointLight, V(960, 140, 75), unreal.Rotator(0, 0, 0))
    l.set_actor_label("FXL_Brazier")
    c = l.get_component_by_class(unreal.LocalLightComponent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    c.set_editor_property("intensity", 8.0)
    c.set_editor_property("light_color", unreal.Color(r=255, g=140, b=70, a=255))
    c.set_editor_property("attenuation_radius", 380.0)
    c.set_editor_property("cast_shadows", False)
    l.tags = [unreal.Name("EHInterior")]
    if not les.save_current_level():
        raise RuntimeError("save failed")
    log("DONE")


try:
    main()
except Exception as exc:
    unreal.log_error("EHFX FAIL " + repr(exc))
    raise
finally:
    if os.environ.get("EH_QUIT_EDITOR") == "1":
        unreal.SystemLibrary.quit_editor()
