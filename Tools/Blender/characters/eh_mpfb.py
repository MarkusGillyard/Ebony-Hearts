"""MPFB access for the Ebony Hearts character build: enabling the extension headless, locating
MakeHuman CC0 assets, creating the base human (macros, region targets, expression units, height
fit) and attaching the game_engine skeleton."""
import importlib
import json
import os
import time

import bpy
import numpy as np

ADDON = "bl_ext.user_default.mpfb"
HERE = os.path.dirname(os.path.abspath(__file__))
SLICE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
T0 = time.time()

# Files the provenance record flags (PNG metadata names another author); never used.
FLAGGED_ASSETS = {"bob01", "bob02", "eyebrow009", "eyebrow010", "eyebrow011"}


def log(*a):
    print("[eh %7.2fs]" % (time.time() - T0), *a, flush=True)


def mpfb(mod, name):
    return getattr(importlib.import_module(ADDON + "." + mod), name)


def enable_mpfb(use_installed_pack=True):
    if ADDON not in bpy.context.preferences.addons:
        if bpy.ops.preferences.addon_enable(module=ADDON) != {"FINISHED"}:
            raise RuntimeError("could not enable " + ADDON)
    bpy.context.preferences.filepaths.save_version = 0
    if use_installed_pack:
        AS = mpfb("services.assetservice", "AssetService")
        AS.update_all_asset_lists()
        if not AS.system_assets_pack_is_installed():
            raise RuntimeError("MakeHuman system assets are not installed: run setup_mpfb.sh first")


def find_asset(filename, subdir):
    stem = os.path.splitext(os.path.basename(filename))[0]
    if stem in FLAGGED_ASSETS:
        raise ValueError("asset %s is provenance-flagged and must not be used" % stem)
    p = mpfb("services.assetservice", "AssetService").find_asset_absolute_path(filename, asset_subdir=subdir)
    if not p or not os.path.isfile(p):
        raise FileNotFoundError("%s/%s" % (subdir, filename))
    return p


def clean_scene():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                 bpy.data.lights, bpy.data.images, bpy.data.armatures, bpy.data.actions,
                 bpy.data.node_groups, bpy.data.textures):
        for idb in list(coll):
            coll.remove(idb)


def with_active(obj, extra=()):
    sel = [obj] + list(extra)
    bpy.context.view_layer.objects.active = obj
    return bpy.context.temp_override(object=obj, active_object=obj, selected_objects=sel,
                                     selected_editable_objects=sel)


# ----------------------------------------------------------------------------- shape

def world_co(obj, evaluated=True):
    if evaluated:
        dg = bpy.context.evaluated_depsgraph_get()
        ev = obj.evaluated_get(dg)
        me = ev.to_mesh()
    else:
        me = obj.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    if evaluated:
        ev.to_mesh_clear()
    M = np.array(obj.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


def body_extent(obj):
    co = world_co(obj)
    # helpers are masked by a modifier in the evaluated mesh, so this is the visible body only
    return float(co[:, 2].max() - co[:, 2].min()), float(co[:, 2].min())


_TARGET_INDEX = None


def target_index():
    global _TARGET_INDEX
    if _TARGET_INDEX is None:
        LS = mpfb("services.locationservice", "LocationService")
        with open(LS.get_mpfb_data("targets/target.json")) as f:
            tj = json.load(f)
        _TARGET_INDEX = {}
        for cat, block in tj.items():
            for c in block["categories"]:
                _TARGET_INDEX[cat + "/" + c["name"]] = c
    return _TARGET_INDEX


def apply_targets(basemesh, targets):
    """Region modifiers {'category/modifier': value in -1..1} loaded as MPFB target shape keys."""
    TS = mpfb("services.targetservice", "TargetService")
    LS = mpfb("services.locationservice", "LocationService")
    idx = target_index()
    applied = []
    for key, value in targets.items():
        if key not in idx:
            near = sorted(k for k in idx if k.split("/")[0] == key.split("/")[0])
            raise KeyError("unknown modifier %s; that category has: %s" % (key, near))
        c = idx[key]
        op = c.get("opposites", {})
        sign = "positive" if value >= 0 else "negative"
        if c.get("has_left_and_right"):
            names = [op.get(sign + "-left"), op.get(sign + "-right")]
        else:
            names = [op.get(sign + "-unsided")]
        names = [n for n in names if n]
        if not names:
            names = c["targets"][:1] if value >= 0 else []
        cat = key.split("/")[0]
        for n in names:
            path = LS.get_mpfb_data("targets/%s/%s.target.gz" % (cat, n))
            sk = TS.load_target(basemesh, path, weight=0.0, name=n)
            sk.slider_max = max(1.0, abs(value))
            sk.value = abs(value)
            applied.append((n, round(abs(value), 4)))
    return applied


def apply_expression(basemesh, expression):
    """Bakes facial expression units ({'race': 'caucasian', '<unit>': weight}) into the neutral head."""
    if not expression:
        return []
    TS = mpfb("services.targetservice", "TargetService")
    LS = mpfb("services.locationservice", "LocationService")
    race = expression["race"]
    out = []
    for name, value in expression.items():
        if name == "race":
            continue
        path = LS.get_mpfb_data("targets/expression/units/%s/%s.target.gz" % (race, name))
        TS.load_target(basemesh, path, weight=0.0, name=name).value = value
        out.append((name, value))
    return out


def set_height_macro(basemesh, value):
    HOP = mpfb("entities.objectproperties", "HumanObjectProperties")
    TS = mpfb("services.targetservice", "TargetService")
    HOP.set_value("height", value, entity_reference=basemesh)
    TS.reapply_macro_details(basemesh)
    return body_extent(basemesh)[0]


def fit_height(basemesh, target_m, macro_hint=None):
    """Bisects the height macro towards the target stature, then takes up the remainder with a
    uniform scale (MPFB's macro response is stepped and range-limited). Feet end at Z = 0."""
    lo, hi = 0.0, 1.0
    h_lo, h_hi = set_height_macro(basemesh, lo), set_height_macro(basemesh, hi)
    best = min([(abs(h_lo - target_m), lo, h_lo), (abs(h_hi - target_m), hi, h_hi)])
    if h_lo < target_m < h_hi:
        for _ in range(28):
            mid = 0.5 * (lo + hi)
            h = set_height_macro(basemesh, mid)
            best = min(best, (abs(h - target_m), mid, h))
            if abs(h - target_m) < 0.0003:
                break
            lo, hi = (mid, hi) if h < target_m else (lo, mid)
    _, macro, _ = best
    h = set_height_macro(basemesh, macro)
    info = {"height_macro_range_m": [round(h_lo, 4), round(h_hi, 4)], "height_macro": round(macro, 6),
            "height_before_scale_m": round(h, 5), "uniform_scale": round(target_m / h, 6)}
    s = target_m / h
    bpy.ops.object.select_all(action="DESELECT")
    basemesh.select_set(True)
    bpy.context.view_layer.objects.active = basemesh
    if abs(s - 1) > 1e-6:
        basemesh.scale = (s, s, s)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _, zmin = body_extent(basemesh)
    basemesh.location.z -= zmin
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    info["body_height_m"] = round(body_extent(basemesh)[0], 4)
    return info


def create_base_human(cfg):
    """MPFB human with macros, region targets and a baked expression at the canon height."""
    HS = mpfb("services.humanservice", "HumanService")
    TS = mpfb("services.targetservice", "TargetService")
    m = cfg["macros"]
    macro = TS.get_default_macro_info_dict()
    for k in ("gender", "age", "muscle", "weight", "proportions", "cupsize", "firmness"):
        if k in m:
            macro[k] = m[k]
    macro["race"] = dict(m.get("race", macro["race"]))
    basemesh = HS.create_human(macro_detail_dict=macro)
    applied = apply_targets(basemesh, cfg.get("targets", {}))
    expr = apply_expression(basemesh, cfg.get("expression"))
    hinfo = fit_height(basemesh, cfg["height_m"])
    hinfo["targets_applied"] = len(applied)
    hinfo["expression_units"] = expr
    return basemesh, hinfo


def add_rig(basemesh):
    HS = mpfb("services.humanservice", "HumanService")
    return HS.add_builtin_rig(basemesh, "game_engine")


def add_part(basemesh, filename, subdir, atype):
    HS = mpfb("services.humanservice", "HumanService")
    return HS.add_mhclo_asset(find_asset(filename, subdir), basemesh, asset_type=atype,
                              subdiv_levels=0, material_type="NONE")


def bake_shape(obj):
    TS = mpfb("services.targetservice", "TargetService")
    if obj.data.shape_keys:
        TS.bake_targets(obj)
