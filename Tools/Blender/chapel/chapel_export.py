"""FBX export (one file per unique piece) and gameplay/technical validation."""
import math
import os

import bpy
from mathutils import Vector

import chapel_config as C
import chapel_layout as LAY

FBX_SETTINGS = dict(
    use_selection=True,
    object_types={"MESH"},
    global_scale=1.0,
    apply_unit_scale=True,
    apply_scale_options="FBX_SCALE_NONE",
    axis_forward="-Z",
    axis_up="Y",
    bake_space_transform=True,
    use_mesh_modifiers=True,
    mesh_smooth_type="FACE",
    use_tspace=False,
    use_triangles=True,
    colors_type="SRGB",
    prioritize_active_color=False,
    use_custom_props=False,
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="STRIP",
    embed_textures=False,
    batch_mode="OFF",
    use_metadata=True,
)


def mesh_stats(me):
    me.calc_loop_triangles()
    tris = len(me.loop_triangles)
    ngons = sum(1 for p in me.polygons if len(p.vertices) > 4)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    bounds = [[round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)],
              [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)]]
    return {"triangles": tris, "vertices": len(me.vertices), "ngons": ngons, "bounds_m": bounds,
            "material_slots": [m.name for m in me.materials],
            "uv_layers": [u.name for u in me.uv_layers],
            "color_attributes": [c.name for c in me.color_attributes]}


def export_pieces(piece_objs):
    os.makedirs(C.EXPORT_DIR, exist_ok=True)
    vl = bpy.context.view_layer
    vl.update()
    out = {}
    for name, obj in piece_objs.items():
        for o in vl.objects:
            if o is not None:
                o.select_set(False)
        obj.hide_set(False)
        obj.select_set(True)
        vl.objects.active = obj
        path = os.path.join(C.EXPORT_DIR, name + ".fbx")
        bpy.ops.export_scene.fbx(filepath=path, **FBX_SETTINGS)
        obj.select_set(False)
        out[name] = os.path.relpath(path, C.OUT_DIR)
    return out


def _world_aabb(item, bounds):
    m = LAY.matrix_of(item)
    (x0, y0, z0), (x1, y1, z1) = bounds
    pts = [m @ Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    return ([min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)])


def _overlap(a_min, a_max, box):
    return all(a_min[i] < box[i][1] and a_max[i] > box[i][0] for i in range(3))


def validate(layout, stats, meshes):
    issues = []
    checks = {}
    box = (C.HANG_BOX[0], C.HANG_BOX[1], (0.0005, C.HANG_BOX[2][1]))
    hits = []
    for it in layout.items:
        if it["tag"] in ("floor", "water"):
            continue
        mn, mx = _world_aabb(it, stats[it["mesh"]]["bounds_m"])
        if _overlap(mn, mx, box):
            hits.append({"mesh": it["mesh"], "aabb_min": [round(v, 3) for v in mn], "aabb_max": [round(v, 3) for v in mx]})
    checks["clear_volume_and_hang_zone"] = {"box_m": [list(box[0]), list(box[1]), list(box[2])],
                                            "violations": hits, "pass": not hits}
    if hits:
        issues.append("objects intrude into the clear/hang volume: %s" % [h["mesh"] for h in hits])

    # flat floor top at exactly Z = 0 inside the strip
    strip = [it for it in layout.items if it["mesh"] == "SM_Floor_Strip"][0]
    m = LAY.matrix_of(strip)
    me = meshes["SM_Floor_Strip"]
    zs = []
    for v in me.vertices:
        w = m @ v.co
        if -7.5 <= w.x <= 7.5 and -1.8 <= w.y <= 1.8:
            zs.append(w.z)
    basin_ok = True
    b_item = [it for it in layout.items if it["mesh"] == "SM_Floor_Basin"][0]
    mb = LAY.matrix_of(b_item)
    for v in meshes["SM_Floor_Basin"].vertices:
        w = mb @ v.co
        if w.y <= C.FLAT_FLOOR_Y[1] + 1e-6 and abs(w.z) > 1e-6:
            basin_ok = False
    flat = bool(zs) and max(abs(z) for z in zs) < 1e-6
    checks["flat_floor_top_z0"] = {"samples": len(zs), "max_abs_z": max(abs(z) for z in zs) if zs else None,
                                   "basin_joins_at_z0": basin_ok, "pass": flat and basin_ok}
    if not (flat and basin_ok):
        issues.append("fighting floor is not flat at Z=0")

    cz = [round(it["location_m"][2] + stats["SM_Censer"]["bounds_m"][0][2], 3)
          for it in layout.items if it["mesh"] == "SM_Censer"]
    checks["censer_bottoms_m"] = {"values": cz, "min_required": C.CENSER_MIN_Z,
                                  "pass": all(z >= C.CENSER_MIN_Z for z in cz)}
    if not checks["censer_bottoms_m"]["pass"]:
        issues.append("censer below %.1f m" % C.CENSER_MIN_Z)

    # foreground silhouettes
    fg = []
    for it in layout.items:
        if it["tag"] == "foreground":
            mn, mx = _world_aabb(it, stats[it["mesh"]]["bounds_m"])
            ok = (min(abs(mn[0]), abs(mx[0])) >= 8.0 or mx[2] <= 1.2) and -5.0 <= it["location_m"][1] <= -2.0
            fg.append({"mesh": it["mesh"], "aabb_min": [round(v, 3) for v in mn],
                       "aabb_max": [round(v, 3) for v in mx], "pass": ok})
    checks["foreground_silhouettes"] = {"items": fg, "pass": all(f["pass"] for f in fg)}

    # how close does any loose dressing come to the strip (inside the nave piers)?
    near = None
    for it in layout.items:
        if it["tag"] not in ("pew", "rubble", "candles", "stand", "censer", "chain", "decal", "altar"):
            continue
        mn, mx = _world_aabb(it, stats[it["mesh"]]["bounds_m"])
        if mx[0] > -8.4 and mn[0] < 8.4:
            if near is None or mn[1] < near[0]:
                near = (round(mn[1], 3), it["mesh"])
    checks["nearest_dressing_inside_piers"] = {"min_y_m": near[0], "mesh": near[1], "pass": near[0] > C.CLEAR_BOX[1][1]}

    ng = {k: v["ngons"] for k, v in stats.items() if v["ngons"]}
    checks["no_ngons"] = {"offenders": ng, "pass": not ng}
    if ng:
        issues.append("n-gons in %s" % list(ng))
    mats = sorted({m for v in stats.values() for m in v["material_slots"]})
    checks["material_count"] = {"count": len(mats), "materials": mats, "pass": len(mats) <= 12}
    if len(mats) > 12:
        issues.append("too many materials")
    counts = {}
    for it in layout.items:
        counts[it["mesh"]] = counts.get(it["mesh"], 0) + 1
    total = sum(stats[m]["triangles"] * n for m, n in counts.items())
    checks["triangle_budget"] = {"instanced_total": total, "budget": 400000, "pass": total <= 400000}
    if total > 400000:
        issues.append("triangle budget exceeded")
    return checks, issues, counts, total


def fbx_roundtrip(stats):
    """Re-import every FBX with Blender's importer and compare triangle count and size."""
    res = {}
    for name in sorted(stats):
        path = os.path.join(C.EXPORT_DIR, name + ".fbx")
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        tris = 0
        mn = [1e9] * 3
        mx = [-1e9] * 3
        for o in new:
            if o.type != "MESH":
                continue
            me = o.data
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
            for v in me.vertices:
                w = o.matrix_world @ v.co
                for i in range(3):
                    mn[i] = min(mn[i], w[i])
                    mx[i] = max(mx[i], w[i])
        exp = stats[name]["bounds_m"]
        size_exp = [exp[1][i] - exp[0][i] for i in range(3)]
        size_got = [mx[i] - mn[i] for i in range(3)]
        ok = tris == stats[name]["triangles"] and all(abs(a - b) < 2e-3 for a, b in zip(size_exp, size_got))
        res[name] = {"triangles": tris, "size_m": [round(s, 4) for s in size_got], "pass": ok}
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
    return res
