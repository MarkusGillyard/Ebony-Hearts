"""Blender preview materials for The Drowned Chapel (used for the .blend and the
review renders).  They mirror the intended UE setup: D/N/ORM textures, vertex
colour (R=AO, G=edge wear, B=base grime) and a world-height wetness line."""
import os

import bpy

import chapel_config as C
import chapel_pieces as P

# per-material look parameters
PARAMS = {
    P.ASH: dict(wear=0.30, grime=0.30, ao=0.8, wet=True),
    P.DRS: dict(wear=0.45, grime=0.30, ao=0.6, wet=True, nstr=0.7),
    P.FLR: dict(wear=0.0, grime=0.0, ao=0.3, wet=False, nstr=0.6),
    P.WOD: dict(wear=0.25, grime=0.25, ao=0.7, wet=True),
    P.IRN: dict(wear=0.5, grime=0.1, ao=0.6, wet=False),
    P.WAX: dict(wear=0.0, grime=0.0, ao=0.3, wet=False),
    P.CLO: dict(wear=0.0, grime=0.0, ao=0.5, wet=False),
}


def _img(name, colour):
    path = os.path.join(C.TEX_DIR, name)
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def _tex(nt, name, colour, x, y):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = _img(name, colour)
    n.location = (x, y)
    n.interpolation = "Linear"
    return n


def _math(nt, op, a=None, b=None, x=0, y=0, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    n.location = (x, y)
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _vmul(nt, col, fac, x=0, y=0):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = "SCALE"
    n.location = (x, y)
    nt.links.new(col, n.inputs[0])
    if isinstance(fac, (int, float)):
        n.inputs["Scale"].default_value = fac
    else:
        nt.links.new(fac, n.inputs["Scale"])
    return n.outputs[0]


def _new_material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (600, 0)
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return mat, nt, bsdf


def _pbr(name, prm):
    mat, nt, bsdf = _new_material(name)
    base = name[2:]
    d = _tex(nt, "T_%s_D.png" % base, True, -900, 300)
    n = _tex(nt, "T_%s_N.png" % base, False, -900, -300)
    orm = _tex(nt, "T_%s_ORM.png" % base, False, -900, 0)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.location = (-600, 0)
    nt.links.new(orm.outputs["Color"], sep.inputs[0])
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    vc.location = (-900, 600)
    vsep = nt.nodes.new("ShaderNodeSeparateColor")
    vsep.location = (-650, 600)
    nt.links.new(vc.outputs["Color"], vsep.inputs[0])
    # factor = lerp(1, aoTex, k) * lerp(1, vcAO, 0.8) * (1 + wear*G) * (1 - grime*B)
    ao_t = _math(nt, "MULTIPLY_ADD", sep.outputs[0], prm["ao"], -400, 200)       # ao*k + (1-k)
    ao_t.node.inputs[2].default_value = 1.0 - prm["ao"]
    ao_v = _math(nt, "MULTIPLY_ADD", vsep.outputs[0], 0.8, -400, 400)
    ao_v.node.inputs[2].default_value = 0.2
    wear = _math(nt, "MULTIPLY_ADD", vsep.outputs[1], prm["wear"], -400, 600)
    wear.node.inputs[2].default_value = 1.0
    grime = _math(nt, "MULTIPLY_ADD", vsep.outputs[2], -prm["grime"], -400, 800)
    grime.node.inputs[2].default_value = 1.0
    f = _math(nt, "MULTIPLY", ao_t, ao_v, -200, 300)
    f = _math(nt, "MULTIPLY", f, wear, -100, 400)
    f = _math(nt, "MULTIPLY", f, grime, 0, 500)
    rough = sep.outputs[1]
    if prm["wet"]:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        geo.location = (-900, 900)
        sxyz = nt.nodes.new("ShaderNodeSeparateXYZ")
        sxyz.location = (-700, 900)
        nt.links.new(geo.outputs["Position"], sxyz.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.location = (-500, 900)
        mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = 0.32
        mr.inputs["From Max"].default_value = 0.0
        nt.links.new(sxyz.outputs["Z"], mr.inputs["Value"])
        wet = mr.outputs["Result"]
        darken = _math(nt, "MULTIPLY_ADD", wet, -0.38, -300, 900)
        darken.node.inputs[2].default_value = 1.0
        f = _math(nt, "MULTIPLY", f, darken, 100, 600)
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "FLOAT"
        mix.location = (200, -100)
        nt.links.new(wet, mix.inputs["Factor"])
        nt.links.new(rough, mix.inputs["A"])
        mix.inputs["B"].default_value = 0.08
        rough = mix.outputs["Result"]
    col = _vmul(nt, d.outputs["Color"], f, 300, 300)
    nt.links.new(col, bsdf.inputs["Base Color"])
    nt.links.new(rough, bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = prm.get("nstr", 1.0)
    nm.location = (300, -300)
    nt.links.new(n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _emissive(name, strength, alpha=False, base_scale=0.05):
    mat, nt, bsdf = _new_material(name)
    base = name[2:]
    d = _tex(nt, "T_%s_D.png" % base, True, -700, 200)
    orm = _tex(nt, "T_%s_ORM.png" % base, False, -700, -100)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs[0])
    nt.links.new(_vmul(nt, d.outputs["Color"], base_scale, -300, 300), bsdf.inputs["Base Color"])
    nt.links.new(d.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    if alpha:
        d.image.alpha_mode = "PREMUL"
        nt.links.new(d.outputs["Alpha"], bsdf.inputs["Alpha"])
        mat.surface_render_method = "BLENDED"
        try:
            mat.use_transparent_shadow = True
        except Exception:
            pass
    return mat


def _water():
    mat, nt, bsdf = _new_material(P.WAT)
    d = _tex(nt, "T_Water_D.png", True, -700, 200)
    n = _tex(nt, "T_Water_N.png", False, -700, -200)
    nt.links.new(d.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.035
    bsdf.inputs["Alpha"].default_value = 0.28
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.35
    nt.links.new(n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat.surface_render_method = "DITHERED"
    return mat


def _decal():
    mat, nt, bsdf = _new_material(P.DEC)
    d = _tex(nt, "T_DecalGrime_D.png", True, -700, 200)
    orm = _tex(nt, "T_DecalGrime_ORM.png", False, -700, -100)
    n = _tex(nt, "T_DecalGrime_N.png", False, -700, -400)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs[0])
    nt.links.new(d.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(d.outputs["Alpha"], bsdf.inputs["Alpha"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mat.surface_render_method = "BLENDED"
    return mat


def build_all():
    mats = {}
    for name, prm in PARAMS.items():
        mats[name] = _pbr(name, prm)
    mats[P.GRS] = _emissive(P.GRS, 7.0)
    mats[P.GLN] = _emissive(P.GLN, 1.1)
    mats[P.FLM] = _emissive(P.FLM, 14.0, alpha=True, base_scale=0.0)
    mats[P.WAT] = _water()
    mats[P.DEC] = _decal()
    return mats
