"""Adapts /Game/Maps/DrownedChapel for first-person play. Run in the full editor after build_level.py:
    bin/editor_py.sh Tools/Unreal/adapt_chapel_fp.py editor
Environment:
    EH_FP_STAGE=collision   only gives the walkable and blocking pieces collision (the audit's "before" map)
    EH_FP_STAGE=full        also places the labelled placeholder blockouts (default)
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
BLOCKOUTS = [
    # The 2.5D camera looked from +Y, so the Chapel has no west (entrance) wall. Its inner face (Y = +415) meets the
    # ends of the first bay's vaults, arcades and aisle walls (Y = +400..+416), so no gap shows above them, and it
    # half-buries the westmost piers like the wall responds elsewhere. It rises past the nave vault's apex (16 m).
    ("PH_Blockout_WestWall", (0.0, 475.0, 825.0), (1340.0, 60.0, 875.0)),
]


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
    enable_collision(actors)
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
