"""The MPFB body for one fighter: macros/targets/expression at canon height, game_engine rig with
MPFB weights, MakeHuman CC0 eyes/eyelashes/eyebrows fitted by MPFB, shape keys baked, helper geometry
removed. MakeHuman region groups (lips, nails, ears, scalp) are kept as float attributes for painting."""
import bpy
import numpy as np

import eh_mesh as M
import eh_mpfb as E
import eh_rig as R

REGIONS = ("lips", "fingernails", "toenails", "ears", "scalp", "nipple", "genitals")


def landmarks(rig):
    out = {}
    for b in rig.data.bones:
        out[b.name] = (np.array(b.head_local), np.array(b.tail_local))
    return out


def build(cfg, name):
    E.clean_scene()
    bm, hinfo = E.create_base_human(cfg)
    sole = cfg.get("sole_m", 0.0)
    if sole:
        bm.location.z += sole
        with E.with_active(bm):
            bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    rig = E.add_rig(bm)
    parts = {}
    for key, (asset, sub, atype) in (("eyes", (cfg["eyes"], "eyes", "Eyes")),
                                     ("lashes", (cfg["eyelashes"], "eyelashes", "Eyelashes")),
                                     ("brows", (cfg["eyebrows"], "eyebrows", "Eyebrows"))):
        parts[key] = E.add_part(bm, asset + ".mhclo", sub, atype)
    # bake shapes, drop helpers
    E.bake_shape(bm)
    for ob in parts.values():
        E.bake_shape(ob)
    for m in list(bm.modifiers):
        if m.type == "MASK":
            with bpy.context.temp_override(object=bm, active_object=bm):
                bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
            M.apply_modifier(bm, m.name)
    Wr = M.weights(bm, REGIONS)
    for r in REGIONS:
        a = bm.data.attributes.new("reg_" + r, "FLOAT", "POINT")
        a.data.foreach_set("value", Wr[r].astype(np.float32))
    R.prepare(rig, name)
    deform = {b.name for b in rig.data.bones if b.use_deform}
    for ob in [bm] + list(parts.values()):
        for vg in list(ob.vertex_groups):
            if vg.name not in deform:
                ob.vertex_groups.remove(vg)
        for m in list(ob.modifiers):
            if m.type != "ARMATURE":
                ob.modifiers.remove(m)
        ob.data.materials.clear()
    # root at the origin (the shoes raise the body, not the root)
    eb = R.edit(rig)
    r = eb["root"]
    ln = r.length
    r.head = (0, 0, 0)
    r.tail = (0, ln, 0)
    R.obj_mode()
    bm.name = bm.data.name = name + "_Body"
    for k, ob in parts.items():
        ob.name = ob.data.name = name + "_" + k.capitalize()
    hinfo["sole_m"] = sole
    return bm, rig, parts, hinfo


def region(ob, r):
    a = ob.data.attributes.get("reg_" + r)
    v = np.zeros(len(ob.data.vertices), np.float32)
    if a is not None:
        a.data.foreach_get("value", v)
    return v


def eye_centers(eyes_ob):
    """Centres and forward points of the two eyeballs (split by X sign)."""
    V = M.co(eyes_ob)
    out = {}
    for s, sel in (("l", V[:, 0] > 0), ("r", V[:, 0] < 0)):
        P = V[sel]
        c = (P.max(0) + P.min(0)) / 2
        front = P[np.argmin(P[:, 1])]
        rad = (P.max(0) - P.min(0)).max() / 2
        out[s] = {"center": c, "front": front, "radius": float(rad)}
    return out
