"""Builds the Drowned Chapel's interior additions (stage 1, the core layout) into /Game/Maps/DrownedChapel.
Headless:
    EH_IX_FBX_DIR=<folder with SM_IX_*.fbx> bin/editor_py.sh Tools/Unreal/build_chapel_interior.py
then the navigation stage (EH_FP_STAGE=nav Tools/Unreal/adapt_chapel_fp.py), which also places the new rooms' stand-ins.

It imports the pieces made by Tools/Blender/chapel/chapel_interior.py with the Chapel's own material instances, takes
out what the new rooms replace (the grey west-wall blockout, four aisle wall bays opened into the transepts, the north
aisle's east end wall opened onto the way down, and the candles, glass and grime on those walls), places the pieces,
gives the solid ones collision from their render geometry, and lights the new rooms. Re-running it replaces its own
actors (labels IX_*); the removed originals are not restored.
"""
import json
import os

import unreal

WS = os.environ["EH_WS"]
SRC = os.environ.get("EH_IX_FBX_DIR", os.path.join(WS, "sourceart", "chapel_interior"))
MAP = "/Game/Maps/DrownedChapel"
DIR = "/Game/Chapel/Interior"
MATS = "/Game/Chapel/Materials"
CRYPT_Z = -300.0

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

NO_COLLISION = {"SM_IX_TransGlass", "SM_IX_DownGlass", "SM_IX_UnderWater"}
# The aisle wall bays the transepts open (centre of each, cm) and the north aisle's east end bay (the way down).
TRANS_BAYS = [(-1228, -600), (-1228, -1000), (1228, -600), (1228, -1000)]
DOWN_BAY = (-1000, -2028)


def log(msg):
    unreal.log("EHIX " + msg)


def setp(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception as exc:
        log(f"WARN {type(obj).__name__}.{name}: {exc}")


def import_pieces(report):
    meshes = {}
    for name, info in sorted(report.items()):
        if name.startswith("_"):
            continue
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
            mi = unreal.load_asset(f"{MATS}/MI_{m[2:]}")
            if mi is None:
                raise RuntimeError(f"no material instance for {m}")
            mesh.set_material(i, mi)
        if name not in NO_COLLISION:
            body = mesh.get_editor_property("body_setup")
            setp(body, "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
        meshes[name] = mesh
    log(f"imported {len(meshes)}")
    return meshes


def mesh_of(a):
    if isinstance(a, unreal.StaticMeshActor) and a.static_mesh_component.static_mesh:
        return a.static_mesh_component.static_mesh.get_name()
    return ""


def near(a, x, y, r):
    l = a.get_actor_location()
    return abs(l.x - x) <= r and abs(l.y - y) <= r


def clear(eas):
    """Takes out the new rooms' earlier actors and what the new rooms replace; returns the replaced bays' transforms."""
    bays = {}
    removed = []
    for a in eas.get_all_level_actors():
        lab = a.get_actor_label()
        m = mesh_of(a)
        l = a.get_actor_location()
        kill = lab.startswith("IX_") or lab.startswith("IXL_") or lab == "PH_Blockout_WestWall"
        if m == "SM_AisleWallBay":
            for key in TRANS_BAYS + [DOWN_BAY]:
                if near(a, key[0], key[1], 40):
                    bays[key] = (a.get_actor_location(), a.get_actor_rotation())
                    kill = True
        if m == "SM_LancetGlass" and any(near(a, x, y, 120) for (x, y) in TRANS_BAYS + [DOWN_BAY]):
            kill = True
        # candles, their lights and grime on the opened walls
        if (m.startswith("SM_CandleCluster") or m.startswith("SM_Decal") or isinstance(a, unreal.PointLight)) and \
                abs(l.x) > 1080 and -1150 < l.y < -450:
            kill = True
        if kill:
            removed.append(f"{lab}({m})" if m else lab)
            eas.destroy_actor(a)
    log(f"removed {len(removed)}: {', '.join(sorted(removed))}")
    missing = [k for k in TRANS_BAYS + [DOWN_BAY] if k not in bays]
    return bays, missing


def place(eas, mesh, label, loc, rot=unreal.Rotator(0, 0, 0), scale=unreal.Vector(1, 1, 1)):
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_label(label)
    a.set_actor_scale3d(scale)
    comp = a.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    if mesh.get_name() in NO_COLLISION:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        comp.set_editor_property("cast_shadow", False)
    else:
        comp.set_collision_profile_name("BlockAll")
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        comp.set_editor_property("cast_shadow_as_two_sided", True)
    a.tags = [unreal.Name("EHInterior")]
    return a


def light(eas, cls, label, loc, colour, intensity, radius, shadows=False, rot=unreal.Rotator(0, 0, 0)):
    a = eas.spawn_actor_from_class(cls, loc, rot)
    a.set_actor_label(label)
    c = a.get_component_by_class(unreal.LocalLightComponent)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    c.set_editor_property("intensity", intensity)
    c.set_editor_property("light_color", unreal.Color(r=colour[0], g=colour[1], b=colour[2], a=255))
    c.set_editor_property("attenuation_radius", radius)
    c.set_editor_property("cast_shadows", shadows)
    a.tags = [unreal.Name("EHInterior")]
    return a


def main():
    report = json.load(open(os.path.join(SRC, "interior.json")))
    meshes = import_pieces(report)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not les.load_level(MAP):
        raise RuntimeError("load_level failed")
    # the slice's camera-side fill sat where the west wall now stands: bring it in front of the wall
    for a in eas.get_all_level_actors():
        if a.get_actor_label() == "CameraSideCoolFill":
            a.set_actor_location(unreal.Vector(0, 200, 400), False, False)
    # The world clock (Source/EbonyHearts/Game/EHWorldClock.h) drives the Chapel's general fills as daylight through the
    # windows: tag them so the game finds them (labels do not exist in packaged builds).
    for a in eas.get_all_level_actors():
        if a.get_actor_label() in ("NaveSkyFill", "NaveApseFill", "CameraSideCoolFill"):
            tags = [t for t in a.tags if str(t) != "EHSkyFill"]
            a.tags = tags + [unreal.Name("EHSkyFill")]
    for a in eas.get_all_level_actors():
        if a.get_actor_label() in ("Candle_08", "Candle_00", "NaveApseFill"):
            c = a.get_component_by_class(unreal.LocalLightComponent)
            log(f"ref light {a.get_actor_label()} units={c.get_editor_property('intensity_units')} "
                f"intensity={c.get_editor_property('intensity')} radius={c.get_editor_property('attenuation_radius')} "
                f"shadows={c.get_editor_property('cast_shadows')} mobility={c.mobility}")
    bays, missing = clear(eas)
    if missing:
        log(f"WARN bays not found (already replaced?): {missing}")
        prev = json.load(open(os.path.join(SRC, "bays.json"))) if os.path.exists(os.path.join(SRC, "bays.json")) else {}
        for k in missing:
            v = prev.get(f"{k[0]},{k[1]}")
            if v:
                bays[k] = (unreal.Vector(*v[0]), unreal.Rotator(pitch=v[1][0], yaw=v[1][1], roll=v[1][2]))
    json.dump({f"{k[0]},{k[1]}": [[l.x, l.y, l.z], [r.pitch, r.yaw, r.roll]] for k, (l, r) in bays.items()},
              open(os.path.join(SRC, "bays.json"), "w"))
    O = unreal.Vector(0, 0, 0)
    for n in ("SM_IX_WestWall", "SM_IX_Narthex", "SM_IX_LoftBalcony", "SM_IX_ThresholdDoor", "SM_IX_DownStair"):
        place(eas, meshes[n], "IX_" + n[6:], O)
    place(eas, meshes["SM_IX_Transept"], "IX_Transept_South", O)
    place(eas, meshes["SM_IX_Transept"], "IX_Transept_North", O, scale=unreal.Vector(-1, 1, 1))
    place(eas, meshes["SM_IX_TransGlass"], "IX_TransGlass_South", O)
    place(eas, meshes["SM_IX_TransGlass"], "IX_TransGlass_North", O, scale=unreal.Vector(-1, 1, 1))
    for i, k in enumerate(TRANS_BAYS):
        l, r = bays[k]
        place(eas, meshes["SM_IX_TransArchBay"], f"IX_TransArchBay_{i}", l, r)
    l, r = bays[DOWN_BAY]
    place(eas, meshes["SM_IX_DownDoorBay"], "IX_DownDoorBay", l, r)
    place(eas, meshes["SM_IX_DownGlass"], "IX_DownGlass", l, r)
    C = unreal.Vector(0, 0, CRYPT_Z)
    for n in ("SM_IX_Undercroft", "SM_IX_UnderGate", "SM_IX_SealedDoor", "SM_IX_UnderWater"):
        place(eas, meshes[n], "IX_" + n[6:], C)
    # light: warm in the hall and the transepts, the forge brightest (its one shadowed light), cold blue below
    light(eas, unreal.PointLight, "IXL_HallCandle", unreal.Vector(380, 760, 190), (255, 168, 96), 20.0, 700.0)
    light(eas, unreal.RectLight, "IXL_DoorSeam", unreal.Vector(0, 1430, 210), (210, 222, 255), 60.0, 1100.0, True,
          unreal.Rotator(0, -90, 0))
    light(eas, unreal.PointLight, "IXL_LoftFill", unreal.Vector(0, 900, 720), (150, 170, 215), 6.0, 800.0)
    light(eas, unreal.PointLight, "IXL_Forge", unreal.Vector(-2000, -800, 140), (255, 120, 48), 60.0, 1300.0, True)
    light(eas, unreal.PointLight, "IXL_HallOfSix", unreal.Vector(1700, -800, 430), (255, 176, 104), 18.0, 1000.0)
    light(eas, unreal.PointLight, "IXL_WayDown", unreal.Vector(-1000, -2400, -90), (96, 150, 190), 8.0, 650.0)
    light(eas, unreal.PointLight, "IXL_Crypt", unreal.Vector(-700, -3100, -130), (90, 150, 185), 16.0, 1300.0)
    for side in (-1, 1):
        light(eas, unreal.PointLight, f"IXL_WestArch_{'N' if side < 0 else 'S'}", unreal.Vector(side * 330, 330, 160),
              (255, 172, 100), 10.0, 520.0)
    light(eas, unreal.PointLight, "IXL_SealedDoor", unreal.Vector(-1180, -3100, -150), (255, 196, 150), 3.0, 260.0)
    light(eas, unreal.PointLight, "IXL_Gate", unreal.Vector(-400, -3420, -170), (190, 22, 26), 10.0, 520.0)
    if not les.save_current_level():
        raise RuntimeError("save failed")
    log("DONE")


try:
    main()
except Exception as exc:
    unreal.log_error("EHIX FAIL " + repr(exc))
    raise
finally:
    if os.environ.get("EH_QUIT_EDITOR") == "1":
        unreal.SystemLibrary.quit_editor()
