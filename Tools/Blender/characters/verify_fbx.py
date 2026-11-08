"""Re-imports the exported FBX files into an empty scene and reports what Unreal will receive:
bones, root, meshes, materials, triangle counts, extents (cm in the file -> m after import), actions."""
import json
import os
import sys
sys.dont_write_bytecode = True

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get("EH_CHAR_OUT") or os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", "..", "sourceart", "characters"))
out = {}
for cid, name in (("wren", "Wren"), ("ashka", "Ashka")):
    for fbx in ("SK_%s.fbx" % name, "SK_%s_LOD1.fbx" % name):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=os.path.join(SRC, cid, fbx))
        arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        dg = bpy.context.evaluated_depsgraph_get()
        tris, zs = 0, []
        for o in meshes:
            me = o.data
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
            M = np.array(o.matrix_world)
            co = np.array([v.co[:] for v in me.vertices])
            zs.append((co @ M[:3, :3].T + M[:3, 3])[:, 2])
        z = np.concatenate(zs)
        arm = arms[0]
        roots = [b.name for b in arm.data.bones if b.parent is None]
        out[fbx] = {"armature_object": arm.name, "bones": len(arm.data.bones), "root_bones": roots,
                    "meshes": len(meshes), "materials": sorted({s.material.name for o in meshes for s in o.material_slots if s.material}),
                    "triangles": tris, "min_z_m": round(float(z.min()), 4), "max_z_m": round(float(z.max()), 4),
                    "actions": len(bpy.data.actions),
                    "helper_bones_present": [b.name for b in arm.data.bones if b.name.startswith("helper_")]}
for k, v in out.items():
    print("VERIFY", k, json.dumps(v))
