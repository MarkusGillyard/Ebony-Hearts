"""Creates a plain MPFB body on the game_engine skeleton for developing animation tooling before final characters exist.

Run: bin/blender.sh anim Tools/Blender/anim/make_dev_rig.py -- <out.blend> <height_m>
Not shipped; final animations are authored on the real character rigs.
"""
import importlib
import sys

import bpy

ADDON = "bl_ext.user_default.mpfb"


def mpfb(mod, name):
    return getattr(importlib.import_module(ADDON + "." + mod), name)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out, height = argv[0], float(argv[1])
    if ADDON not in bpy.context.preferences.addons:
        bpy.ops.preferences.addon_enable(module=ADDON)
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.armatures):
        for idb in list(coll):
            coll.remove(idb)
    HS = mpfb("services.humanservice", "HumanService")
    TS = mpfb("services.targetservice", "TargetService")
    macro = TS.get_default_macro_info_dict()
    macro["gender"] = 0.0
    macro["muscle"] = 0.7
    macro["weight"] = 0.45
    body = HS.create_human(macro_detail_dict=macro)
    rig = HS.add_builtin_rig(body, "game_engine")
    rig.name = "Armature"
    bpy.context.view_layer.update()
    zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
    scale = height / (max(zs) - min(zs))
    rig.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    with bpy.context.temp_override(selected_editable_objects=[rig], active_object=rig, object=rig):
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    print("DEVRIG bones", len(rig.data.bones), "height", height)
    for b in rig.data.bones:
        if b.parent is None or b.name in ("pelvis", "thigh_l", "upperarm_l", "hand_l", "foot_l", "head"):
            print("DEVRIG", b.name, tuple(round(c, 3) for c in b.head_local), tuple(round(c, 3) for c in b.tail_local), round(b.matrix_local.to_euler().z, 3))
    bpy.ops.wm.save_as_mainfile(filepath=out)


main()
