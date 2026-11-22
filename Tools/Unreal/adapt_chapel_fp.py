"""Adapts /Game/Maps/DrownedChapel for first-person play. Run in the full editor after build_level.py:
    bin/editor_py.sh Tools/Unreal/adapt_chapel_fp.py editor
Environment:
    EH_FP_STAGE=collision   only gives the walkable and blocking pieces collision (the audit's "before" map)
    EH_FP_STAGE=full        also places the labelled placeholder blockouts (default)
    EH_FP_STAGE=nav         only (re)places the navigation bounds the wolves walk inside (milestone 5)
    EH_FP_REPORT=<file>     writes every actor's label, mesh, collision and bounds as JSON

The 2.5D slice imported every Chapel piece without collision (the fighters stood on a fixed plane). First person
walks the whole nave, so floors, walls, piers and loose dressing block the player with their render geometry
(complex as simple), and the openings the side-on camera never saw are closed with grey placeholder boxes named
PH_Blockout_*, which the asset ledger lists as placeholders.
"""
import json
import os

import unreal

MAP = "/Game/Maps/DrownedChapel"
PH_DIR = "/Game/Chapel/Placeholder"
STAGE = os.environ.get("EH_FP_STAGE", "full")

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty

# Pieces the player stands on or walks into. Everything else (vaults, upper walls, glass, chains, censers, candles,
# decals, water) stays without collision: out of reach, or too small to be worth snagging on.
SOLID = {
    "SM_Floor_Strip", "SM_Floor_Basin", "SM_AisleWallBay", "SM_ApseWall", "SM_WallRespond", "SM_Column_Clustered",
    "SM_Altar", "SM_AltarSteps", "SM_Pew_Broken", "SM_Pew_Intact", "SM_Pew_Overturned", "SM_Rubble_Block",
    "SM_Rubble_Drum", "SM_Rubble_Pile", "SM_Rubble_Slab", "SM_Debris_Planks", "SM_FG_BrokenBase", "SM_FG_RubbleHeap",
    "SM_CandleStand",
}

# The shell's vault webs and upper walls are single-sided; seen side-on that never mattered, but from inside the nave
# the low moon shone through them onto the west end. Casting their shadows two-sided lets moonlight in only through the
# glass (rose window, lancets, clerestory).
SHELL = {
    "SM_Vault_NaveBay", "SM_Vault_AisleBay", "SM_NaveBayUpper", "SM_Arch_AisleTransverse", "SM_VaultShaft",
    "SM_AisleWallBay", "SM_ApseWall", "SM_RoseFrame", "SM_WallRespond", "SM_Column_Clustered",
}

# Placeholder blockouts, centre and half size in cm (Unreal axes: the nave runs along -Y from the entrance at +Y to the
# apse; X is across the nave). See Docs/FirstPerson.md for why each one exists.
# (The grey west-wall blockout that closed the open west end is gone: the interior's west wall, Threshold Hall and loft
# replace it. Tools/Unreal/build_chapel_interior.py.)
BLOCKOUTS = []


def log(msg):
    unreal.log("EHFP " + msg)


def setp(obj, name, value):
    try:
        obj.set_editor_property(name, value)
        return True
    except Exception as exc:
        log(f"WARN property {type(obj).__name__}.{name}: {exc}")
        return False


def placeholder_material():
    """Matte grey with a 1 m world grid, so blockouts read as unfinished at a glance."""
    path = f"{PH_DIR}/M_PH_Blockout"
    if eal.does_asset_exist(path):
        return unreal.load_asset(path)
    mat = tools.create_asset("M_PH_Blockout", PH_DIR, unreal.Material, unreal.MaterialFactoryNew())
    wpos = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -1200, 0)
    div = mel.create_material_expression(mat, unreal.MaterialExpressionDivide, -1000, 0)
    mel.connect_material_expressions(wpos, "", div, "A")
    setp(div, "const_b", 100.0)
    frac = mel.create_material_expression(mat, unreal.MaterialExpressionFrac, -850, 0)
    mel.connect_material_expressions(div, "", frac, "")
    # Grid lines where any axis' fraction is near 0: 1 - smooth step of the distance to the nearest line.
    sub = mel.create_material_expression(mat, unreal.MaterialExpressionSubtract, -700, 0)
    mel.connect_material_expressions(frac, "", sub, "A")
    setp(sub, "const_b", 0.5)
    absn = mel.create_material_expression(mat, unreal.MaterialExpressionAbs, -560, 0)
    mel.connect_material_expressions(sub, "", absn, "")
    mx = mel.create_material_expression(mat, unreal.MaterialExpressionMax, -420, 0)
    r = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -560, 150)
    setp(r, "r", True); setp(r, "g", False); setp(r, "b", False)
    g = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -560, 250)
    setp(g, "r", False); setp(g, "g", True); setp(g, "b", False)
    b = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -560, 350)
    setp(b, "r", False); setp(b, "g", False); setp(b, "b", True)
    for m in (r, g, b):
        mel.connect_material_expressions(absn, "", m, "")
    mel.connect_material_expressions(r, "", mx, "A")
    mel.connect_material_expressions(g, "", mx, "B")
    mx2 = mel.create_material_expression(mat, unreal.MaterialExpressionMax, -300, 100)
    mel.connect_material_expressions(mx, "", mx2, "A")
    mel.connect_material_expressions(b, "", mx2, "B")
    step = mel.create_material_expression(mat, unreal.MaterialExpressionSmoothStep, -160, 100)
    mel.connect_material_expressions(mx2, "", step, "Value")
    setp(step, "const_min", 0.47)
    setp(step, "const_max", 0.49)
    lerp = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, 0, 0)
    base = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -160, -150)
    setp(base, "constant", unreal.LinearColor(0.055, 0.058, 0.065, 1))
    line = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -160, -60)
    setp(line, "constant", unreal.LinearColor(0.16, 0.16, 0.17, 1))
    mel.connect_material_expressions(base, "", lerp, "A")
    mel.connect_material_expressions(line, "", lerp, "B")
    mel.connect_material_expressions(step, "", lerp, "Alpha")
    mel.connect_material_property(lerp, "", MP.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -160, 300)
    setp(rough, "r", 0.92)
    mel.connect_material_property(rough, "", MP.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_asset(path, only_if_is_dirty=False)
    return mat


def mesh_of(actor):
    if not isinstance(actor, unreal.StaticMeshActor):
        return None
    sm = actor.static_mesh_component.static_mesh
    return sm.get_name() if sm else None


def enable_collision(actors):
    done_meshes = set()
    count = 0
    for a in actors:
        name = mesh_of(a)
        if name not in SOLID:
            continue
        sm = a.static_mesh_component.static_mesh
        if name not in done_meshes:
            body = sm.get_editor_property("body_setup")
            if body is None:
                log(f"FAIL {name} has no body setup")
                continue
            setp(body, "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            eal.save_asset(sm.get_path_name(), only_if_is_dirty=False)
            done_meshes.add(name)
        comp = a.static_mesh_component
        comp.set_collision_profile_name("BlockAll")
        comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        count += 1
    log(f"collision on {count} actors, {len(done_meshes)} meshes")


def seal_shell_shadows(actors):
    count = 0
    for a in actors:
        if mesh_of(a) in SHELL:
            a.static_mesh_component.set_editor_property("cast_shadow_as_two_sided", True)
            count += 1
    log(f"two-sided shadows on {count} shell actors")


def place_blockouts(eas):
    mat = placeholder_material()
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    for label, centre, half in BLOCKOUTS:
        for old in [x for x in eas.get_all_level_actors() if x.get_actor_label() == label]:
            eas.destroy_actor(old)
        a = eas.spawn_actor_from_object(cube, unreal.Vector(*centre), unreal.Rotator(0, 0, 0))
        a.set_actor_label(label)
        a.set_actor_scale3d(unreal.Vector(half[0] / 50.0, half[1] / 50.0, half[2] / 50.0))
        comp = a.static_mesh_component
        comp.set_material(0, mat)
        comp.set_mobility(unreal.ComponentMobility.STATIC)
        comp.set_collision_profile_name("BlockAll")
        a.tags = [unreal.Name("EHPlaceholder")]
    log(f"blockouts {len(BLOCKOUTS)}")


# Where the wolves can walk: the whole nave, aisles, basin and altar, floor to well above head height. The navigation
# mesh itself is generated at run time (RecastNavMesh RuntimeGeneration=Dynamic, Config/DefaultEngine.ini), so an Ice
# Wall cuts it the moment it rises and gives the way back when it melts.
NAV_BOUNDS = ("EH_NavBounds_Chapel", (0.0, -1050.0, 150.0), (2350.0, 2600.0, 520.0))

# The interior's rooms (Tools/Unreal/build_chapel_interior.py) as navigation stand-ins, centre and half size in cm, and
# a roll in degrees for the stairs' ramps: floors are slabs whose tops are the walking height, the wall stubs beside
# each opening are obstacles.
IX_NAV = [
    ("IX_NarthexFloor", (0, 935, -10), (500, 400, 10), 0),
    ("IX_LoftFloor", (70, 935, 480), (430, 400, 10), 0),
    ("IX_LoftLanding", (-430, 574, 480), (70, 39, 10), 0),
    ("IX_LoftBack", (-430, 1150, 480), (70, 185, 10), 0),
    ("IX_Balcony", (0, 377, 480), (380, 158, 10), 0),
    ("IX_BalconyColumnL", (-340, 185, 110), (25, 25, 110), 0),
    ("IX_BalconyColumnR", (340, 185, 110), (25, 25, 110), 0),
    ("IX_TransS_Step1", (1288, -800, -5), (15, 360, 10), 0),
    ("IX_TransS_Step2", (1318, -800, 15), (15, 360, 10), 0),
    ("IX_TransS_Floor", (1762, -800, 35), (429, 360, 10), 0),
    ("IX_TransN_Step1", (-1288, -800, -5), (15, 360, 10), 0),
    ("IX_TransN_Step2", (-1318, -800, 15), (15, 360, 10), 0),
    ("IX_TransN_Floor", (-1762, -800, 35), (429, 360, 10), 0),
    ("IX_DownLanding", (-1000, -2065, -15), (90, 65, 10), 0),        # from the aisle's floor through the doorway
    ("IX_DownFoot", (-1000, -2670, -310), (90, 30, 10), 0),           # the last step's run into the crypt
    ("IX_CryptFloor", (-700, -3100, -310), (600, 400, 10), 0),
    ("IX_CryptPierA", (-700, -2970, -150), (40, 40, 150), 0),
    ("IX_CryptPierB", (-700, -3230, -150), (40, 40, 150), 0),
]
# The furnishings (Tools/Unreal/build_chapel_furnish.py) as obstacles.
IX_NAV += [
    ("FX_Hearth", (-2122, -800, 94), (68, 150, 50), 0),
    ("FX_Counter", (-1655, -487, 95), (195, 43, 50), 0),
    ("FX_Anvil", (-1850, -820, 90), (35, 35, 45), 0),
    ("FX_Trough", (-1980, -1117, 80), (80, 33, 35), 0),
    ("FX_Rack", (-1575, -1132, 125), (115, 15, 80), 0),
    ("FX_Dwar", (-1980, -680, 125), (40, 55, 80), 0),
    ("FX_StatueN", (-390, -1945, 74), (56, 56, 30), 0),
    ("FX_StatueS", (390, -1945, 74), (56, 56, 30), 0),
    ("FX_KneelerDesk", (0, -1798, 86), (72, 14, 42), 0),
    ("FX_CampCrates", (1125, -95, 50), (35, 70, 50), 0),
    ("FX_Brazier", (960, 140, 40), (36, 36, 40), 0),
]
for _x in (1500, 1740, 1980):
    IX_NAV.append((f"FX_AlcoveW{_x}", (_x, -465, 80), (75, 28, 35), 0))
    IX_NAV.append((f"FX_AlcoveE{_x}", (_x, -1135, 80), (75, 28, 35), 0))
# The wall stubs either side of each opening in the replaced bays (the arch bays' 1.5 m half openings, the way down's
# 0.9 m), as obstacles from the floor to 2.2 m.
for _x in (-1228, 1228):
    for _y, _h in ((-425, 25), (-800, 50), (-1175, 25)):
        IX_NAV.append((f"IX_TransPier_{_x}_{_y}", (_x, _y, 110), (45, _h, 110), 0))
# The stairs, one slab per step (the Threshold Hall's 27 steps of 18 cm up to the loft; the way down's 17 of 17 cm).
for _i in range(27):
    _y0 = 1260 - 24 * _i
    IX_NAV.append((f"IX_HallStep{_i:02d}", (-430, _y0 - 12, (_i + 1) * 18.15 - 10), (70, 12, 10), 0))
for _i in range(1, 18):
    _y0 = -2130 - 30 * (_i - 1)
    IX_NAV.append((f"IX_DownStep{_i:02d}", (-1000, _y0 - 15, -5 - _i * 17.35 - 10), (90, 15, 10), 0))
IX_NAV.append(("IX_DownJambL", (-1145, -2028, 110), (55, 45, 110), 0))
IX_NAV.append(("IX_DownJambR", (-855, -2028, 110), (55, 45, 110), 0))


def place_nav_bounds(eas):
    label, centre, half = NAV_BOUNDS
    for old in [x for x in eas.get_all_level_actors() if x.get_actor_label() == label]:
        eas.destroy_actor(old)
    vol = eas.spawn_actor_from_class(unreal.NavMeshBoundsVolume, unreal.Vector(*centre), unreal.Rotator(0, 0, 0))
    vol.set_actor_label(label)
    # The default brush is a 200 cm cube.
    vol.set_actor_scale3d(unreal.Vector(half[0] / 100.0, half[1] / 100.0, half[2] / 100.0))
    log(f"nav bounds {centre} half {half}")
    # The navigation data actor the game fills in at run time (its tiles are generated as the level loads).
    if not [x for x in eas.get_all_level_actors() if isinstance(x, unreal.RecastNavMesh)]:
        nav = eas.spawn_actor_from_class(unreal.RecastNavMesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        nav.set_actor_label("EH_RecastNavMesh")
        log("navigation data actor placed")


# Navigation proxies. The Chapel's pieces collide with their render geometry (complex as simple), which this engine
# does not hand to the navigation mesh at run time, so every walkable or blocking piece gets an invisible box that only
# navigation sees: hidden in game, never drawn, blocking only the unused vehicle channel. Floors become slabs at their walking
# height; anything standing on the floor becomes a box from the floor up to 2.2 m. Flat debris is left out: walked over.
NAV_FLOORS = {"SM_Floor_Strip": 0.0, "SM_Floor_Basin": -12.0, "SM_AltarSteps": None}
NAV_SKIP_BELOW = 15.0   # pieces lower than this (planks) are walked over


def nav_only(p):
    p.set_actor_hidden_in_game(True)
    comp = p.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    # The cube's own collision profile (block all) would otherwise win over the settings below.
    setp(comp, "use_default_collision", False)
    comp.set_collision_profile_name("Custom")
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
    # A type no game probe asks for (the floor, wall and water probes query world static and dynamic objects).
    comp.set_collision_object_type(unreal.CollisionChannel.ECC_VEHICLE)
    comp.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
    # Navigation only reads pieces that block pawns or vehicles: block the vehicle channel, which nothing in the game
    # moves or traces on, so the player, the wolf and every probe pass through.
    comp.set_collision_response_to_channel(unreal.CollisionChannel.ECC_VEHICLE, unreal.CollisionResponseType.ECR_BLOCK)
    setp(comp, "can_ever_affect_navigation", True)
    setp(comp, "cast_shadow", False)
    setp(comp, "visible", False)
    p.tags = [unreal.Name("EHNavProxy")]


def place_nav_proxies(eas, actors):
    for old in [x for x in eas.get_all_level_actors() if x.get_actor_label().startswith("EH_NavProxy_")]:
        eas.destroy_actor(old)
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    count = 0
    for a in actors:
        name = mesh_of(a)
        if name not in SOLID:
            continue
        origin, extent = a.get_actor_bounds(False)
        if name in NAV_FLOORS:
            top = NAV_FLOORS[name] if NAV_FLOORS[name] is not None else origin.z + extent.z
            lo, hi = top - 20.0, top
        else:
            if extent.z * 2.0 < NAV_SKIP_BELOW:
                continue
            lo, hi = max(origin.z - extent.z, -45.0), min(origin.z + extent.z, 220.0)
            if hi <= lo:
                continue
        centre = unreal.Vector(origin.x, origin.y, (lo + hi) / 2.0)
        p = eas.spawn_actor_from_class(unreal.StaticMeshActor, centre, unreal.Rotator(0, 0, 0))
        if p is None:
            log(f"WARN proxy for {name} not spawned")
            continue
        p.static_mesh_component.set_static_mesh(cube)
        count += 1
        p.set_actor_label(f"EH_NavProxy_{count:03d}_{name}")
        p.set_actor_scale3d(unreal.Vector(max(extent.x, 5.0) / 50.0, max(extent.y, 5.0) / 50.0, (hi - lo) / 100.0))
        nav_only(p)
    for name, centre, half, roll in IX_NAV:
        p = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*centre), unreal.Rotator(roll=roll))
        p.static_mesh_component.set_static_mesh(cube)
        count += 1
        p.set_actor_label(f"EH_NavProxy_{count:03d}_{name}")
        p.set_actor_scale3d(unreal.Vector(half[0] / 50.0, half[1] / 50.0, half[2] / 50.0))
        nav_only(p)
    log(f"nav proxies {count}")


def report(actors, path):
    rows = []
    for a in actors:
        origin, extent = a.get_actor_bounds(False)
        row = {"label": a.get_actor_label(), "class": a.get_class().get_name(),
               "origin": [round(origin.x, 1), round(origin.y, 1), round(origin.z, 1)],
               "extent": [round(extent.x, 1), round(extent.y, 1), round(extent.z, 1)]}
        m = mesh_of(a)
        if m:
            row["mesh"] = m
            row["collision"] = str(a.static_mesh_component.get_collision_enabled())
        rows.append(row)
    with open(path, "w") as f:
        json.dump(rows, f, indent=1)
    log(f"report {len(rows)} actors -> {path}")


def main():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if not les.load_level(MAP):
        raise RuntimeError("load_level failed")
    actors = eas.get_all_level_actors()
    if STAGE == "nav":
        place_nav_bounds(eas)
        place_nav_proxies(eas, actors)
        if not les.save_current_level():
            raise RuntimeError("save failed")
        log("DONE nav")
        return
    enable_collision(actors)
    place_nav_bounds(eas)
    if STAGE == "full":
        seal_shell_shadows(actors)
        place_blockouts(eas)
    if os.environ.get("EH_FP_REPORT"):
        report(eas.get_all_level_actors(), os.environ["EH_FP_REPORT"])
    if not les.save_current_level():
        raise RuntimeError("save failed")
    log("DONE " + STAGE)


try:
    main()
except Exception as exc:
    unreal.log_error("EHFP FAIL " + repr(exc))
    raise
finally:
    if os.environ.get("EH_QUIT_EDITOR") == "1":
        unreal.SystemLibrary.quit_editor()
