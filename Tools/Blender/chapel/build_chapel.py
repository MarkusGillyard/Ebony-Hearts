"""Build The Drowned Chapel from scratch (textures, meshes, layout, FBX, .blend, renders).

Run (see run_build.sh, which also sets the sandboxed Blender user folder):

  BLENDER_USER_RESOURCES=<slice>/userdata/blender-chapel \\
  blender --background --factory-startup -t 6 --python build_chapel.py -- [options]

Options (after "--"):
  --no-render        skip the EEVEE review renders
  --skip-textures    reuse existing PNGs in sourceart/chapel/textures (faster iteration)
  --only NAME[,..]   render only these camera keys (centre,left_corner,right_corner,wide_establishing)
  --no-fbx-check     skip the FBX re-import round-trip check
"""
import sys

sys.dont_write_bytecode = True
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy

import chapel_config as C
import chapel_export as X
import chapel_geo as G
import chapel_layout as LAY
import chapel_materials as M
import chapel_notes as N
import chapel_pieces as P
import chapel_render as RND
import chapel_textures as T

RENDER_KEYS = ["centre", "left_corner", "right_corner", "wide_establishing"]

# Review-render look (lighting is approximate; the real lighting happens in UE)
LOOK = {
    "fighter_grey": 0.05,
    "moon_strength": 11.0,
    "candle_scale": 1.0,
    "fill_scale": 1.0,
    "ambient": 0.010,
    "fog_density": 0.015,
    "fog_anisotropy": 0.65,
    "exposure": 0.0,
    "samples": 64,
    "wide": {"loc": (-2.4, -6.2, 3.4), "target": (0.6, 15.0, 7.4), "vfov": 62.0},
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"render": True, "skip_textures": False, "only": None, "fbx_check": True}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-render":
            opts["render"] = False
        elif a == "--skip-textures":
            opts["skip_textures"] = True
        elif a == "--only":
            opts["only"] = argv[i + 1].split(",")
            i += 1
        elif a == "--no-fbx-check":
            opts["fbx_check"] = False
        i += 1
    return opts


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "DrownedChapel"
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"


def main():
    t0 = time.time()
    opts = parse_args()
    reset_scene()
    for d in (C.OUT_DIR, C.TEX_DIR, C.EXPORT_DIR, C.EVIDENCE_DIR):
        os.makedirs(d, exist_ok=True)

    # 1. textures
    tex_report_path = os.path.join(C.OUT_DIR, "_tmp", "texture_cache.json")
    os.makedirs(os.path.dirname(tex_report_path), exist_ok=True)
    if opts["skip_textures"] and os.path.exists(tex_report_path):
        with open(tex_report_path) as f:
            saved = json.load(f)
        tex_report, inputs_used = saved["textures"], saved["inputs"]
    else:
        tex_report, inputs_used = T.build_all()
        with open(tex_report_path, "w") as f:
            json.dump({"textures": tex_report, "inputs": inputs_used}, f, indent=1, sort_keys=True)
    print("[build] textures ready (%.1fs)" % (time.time() - t0))

    # 2. materials
    M.build_all()

    # 3. pieces
    pieces = P.build_all()
    pc = bpy.data.collections.new("Chapel_Pieces")
    bpy.context.scene.collection.children.link(pc)
    meshes, objs, info = {}, {}, {}
    for p in pieces:
        me = p.finalize()
        ob = bpy.data.objects.new(p.name, me)
        pc.objects.link(ob)
        meshes[p.name] = me
        objs[p.name] = ob
        info[p.name] = p.extra
    scratch = bpy.data.collections.get("_scratch")
    if scratch:
        bpy.data.collections.remove(scratch)
    stats = {n: X.mesh_stats(m) for n, m in meshes.items()}
    print("[build] %d unique pieces (%.1fs)" % (len(pieces), time.time() - t0))

    # 4. layout
    layout, lights, cams = LAY.build(info)
    lc = bpy.data.collections.new("Chapel_Layout")
    bpy.context.scene.collection.children.link(lc)
    for i, it in enumerate(layout.items):
        ob = bpy.data.objects.new("%s__%03d" % (it["mesh"], i), meshes[it["mesh"]])
        ob.matrix_world = LAY.matrix_of(it)
        lc.objects.link(ob)

    # 5. validate
    checks, issues, counts, total = X.validate(layout, stats, meshes)
    for k, v in checks.items():
        print("[check] %-28s %s" % (k, "PASS" if v.get("pass") else "FAIL"))
    for msg in issues:
        print("[check] ISSUE:", msg)

    # 6. export
    fbx = X.export_pieces(objs)
    pc.hide_render = True
    for ob in objs.values():
        ob.hide_set(True)

    # 7. data files
    ue_items = []
    for it in layout.items:
        d = dict(it)
        d["ue"] = LAY.ue_transform(it["location_m"], it["rotation_deg"], it["scale"])
        ue_items.append(d)
    mesh_table = {}
    for n in sorted(stats):
        s = stats[n]
        mesh_table[n] = {"fbx": fbx[n], "triangles": s["triangles"], "instances": counts.get(n, 0),
                         "instanced_triangles": s["triangles"] * counts.get(n, 0),
                         "material_slots": s["material_slots"], "bounds_m": s["bounds_m"],
                         "collision": N.collision_hint(n), "extra": info.get(n, {})}
    layout_json = {
        "stage": "The Drowned Chapel",
        "frame": {"units": "metres", "axes": "Blender: +X screen right (fighting axis), +Y depth away from the "
                  "gameplay camera, +Z up; rotations are XYZ Euler degrees",
                  "ue_conversion": "UE location_cm = (x*100, -y*100, z*100); every instance also carries a "
                  "precomputed 'ue' block (FRotator pitch/yaw/roll) assuming the FBX settings in NOTES.md"},
        "gameplay": {"floor_z": 0.0, "playable_x": [-C.PLAY_EDGE_X, C.PLAY_EDGE_X],
                     "clear_volume_m": {"x": list(C.CLEAR_BOX[0]), "y": list(C.CLEAR_BOX[1]),
                                        "z": list(C.CLEAR_BOX[2])},
                     "no_hang_below_z_m": C.HANG_BOX[2][1], "water_surface_z": C.WATER_Z,
                     "water_collides": False,
                     "suggested_blocking": [{"name": "StageBound_L", "center_m": [-C.PLAY_EDGE_X - 0.25, 0, 2.0],
                                             "extent_m": [0.25, 3.0, 4.0]},
                                            {"name": "StageBound_R", "center_m": [C.PLAY_EDGE_X + 0.25, 0, 2.0],
                                             "extent_m": [0.25, 3.0, 4.0]}]},
        "meshes": mesh_table,
        "material_slots": {n: stats[n]["material_slots"] for n in sorted(stats)},
        "instances": ue_items,
        "lights": lights,
        "cameras": cams,
        "validation": checks,
    }
    with open(C.LAYOUT_PATH, "w") as f:
        json.dump(layout_json, f, indent=1)

    # 8. review set-up, save .blend
    RND.setup(lights, cams, LOOK)
    bpy.ops.wm.save_as_mainfile(filepath=C.BLEND_PATH, compress=True)
    try:
        bpy.ops.file.make_paths_relative()
        bpy.ops.wm.save_mainfile(compress=True)
    except Exception as e:
        print("[build] make_paths_relative:", e)
    blend1 = C.BLEND_PATH + "1"
    if os.path.isfile(blend1):
        os.remove(blend1)

    # 9. renders
    renders = []
    if opts["render"]:
        keys = opts["only"] or RENDER_KEYS
        renders = RND.render(keys)

    # 10. FBX round trip (after saving, so the imported copies never reach the .blend)
    roundtrip = X.fbx_roundtrip(stats) if opts["fbx_check"] else {}

    report = {"checks": checks, "issues": issues, "instanced_triangles": total, "instances": len(layout.items),
              "meshes": mesh_table, "textures": tex_report, "inputs": inputs_used, "fbx_settings":
              {k: (sorted(v) if isinstance(v, set) else v) for k, v in X.FBX_SETTINGS.items()},
              "fbx_roundtrip": roundtrip, "renders": [os.path.relpath(r, C.ROOT) for r in renders],
              "lights": lights, "cameras": cams, "look": LOOK,
              "build_seconds": round(time.time() - t0, 1), "blender": bpy.app.version_string}
    with open(C.REPORT_PATH, "w") as f:
        json.dump(report, f, indent=1)
    N.write(report)
    print("[build] done in %.1fs; instanced triangles %d; issues %d" % (time.time() - t0, total, len(issues)))


if __name__ == "__main__":
    main()
