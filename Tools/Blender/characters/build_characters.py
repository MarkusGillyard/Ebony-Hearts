"""Rebuilds the Ebony Hearts fighters (Wren Ku, Ashka Rook) from MPFB + MakeHuman CC0 inputs.

    Tools/Blender/characters/run_blender.sh Tools/Blender/characters/build_characters.py [wren] [ashka]

Per character, into <slice>/sourceart/characters/<id>/:
  <Name>.blend            editable source (armature object "Armature", meshes per material)
  SK_<Name>.fbx           LOD0 mesh + armature, no animation (UE: cm, Z-up, faces +Y like SK_Mannequin)
  SK_<Name>_LOD1.fbx      ~50% triangles (decimated copy, same skeleton)
  textures/T_<Name>_<Mat>_{D,N,ORM}.png   (N is OpenGL; ORM = AO, roughness, metallic)
  bones.json, build_report.json
Deterministic: no randomness without fixed seeds; all geometry, hair and garments are generated here.
"""
import json
import os
import sys
sys.dont_write_bytecode = True
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eh_ashka as A          # noqa: E402
import eh_body as Bd          # noqa: E402
import eh_garment as G        # noqa: E402
import eh_hair as H           # noqa: E402
import eh_hairstyles as HS    # noqa: E402
import eh_mesh as M           # noqa: E402
import eh_mpfb as E           # noqa: E402
import eh_paint as PT         # noqa: E402
import eh_rig as R            # noqa: E402
import eh_specs as SP         # noqa: E402
import eh_tex as T            # noqa: E402
import eh_wren as Wr          # noqa: E402

SLICE = E.SLICE
OUT_ROOT = os.path.join(SLICE, "sourceart", "characters")

FBX_SETTINGS = dict(
    use_selection=True, object_types={"ARMATURE", "MESH"},
    apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
    axis_forward="Y", axis_up="Z", bake_space_transform=False,
    use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True, use_triangles=False,
    use_custom_props=False, add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
    use_armature_deform_only=True, armature_nodetype="NULL", bake_anim=False,
    path_mode="STRIP", embed_textures=False, colors_type="NONE")


def load_cfg(cid):
    with open(os.path.join(HERE, "characters.json")) as f:
        doc = json.load(f)
    cfg = dict(doc["common"])
    cfg.update(doc["characters"][cid])
    cfg["id"] = cid
    return cfg


def finalize_weights(ob, rig, limit):
    deform = {b.name for b in rig.data.bones if b.use_deform}
    W = {k: v for k, v in M.weights(ob).items() if k in deform}
    W = M.normalize_limit(W, limit)
    M.set_weights(ob, W)
    unweighted = int((np.stack(list(W.values()), 1).sum(1) < 0.99).sum()) if W else len(ob.data.vertices)
    return unweighted


def head_ctx(body, rig, parts):
    hi = H.head_info(body, rig, parts)
    V = M.co(body)
    sel = (np.abs(V[:, 0]) < 0.012) & (V[:, 2] < hi["eye_l"][2]) & (V[:, 2] > hi["eye_l"][2] - 0.07)
    hi["nose_tip"] = V[sel][np.argmin(V[sel, 1])]
    return hi


def build(cid):
    t0 = time.time()
    cfg = load_cfg(cid)
    name = cfg["name"]
    out = os.path.join(OUT_ROOT, cid)
    tex_dir = os.path.join(out, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    E.log("=== build", name)
    body, rig, parts, hinfo = Bd.build(cfg, name)
    R.add_twist_bones(rig)
    W = R.split_twist_weights(body, rig)
    R.add_half_joints(rig)
    W = R.split_half_weights(body, rig, W)
    M.set_weights(body, M.normalize_limit(W, cfg["weight_limit"]))
    hi = head_ctx(body, rig, parts)
    eyes_info = Bd.eye_centers(parts["eyes"])
    brows_P = M.co(parts["brows"]).copy()
    col_body = M.Collider([body])
    ctx = {"head": hi, "eyes": eyes_info, "brows_P": brows_P, "rig": rig}
    report = {"id": cid, "name": cfg["display_name"], "mpfb": hinfo}

    # ---------------------------------------------------------------- garments + hair
    if cid == "wren":
        garments, hide = Wr.build(body, rig, cfg, col_body)
        hair, hair_info = HS.wren(body, rig, parts, [garments["top"]], cfg)
        apex = Wr.bust_apex(body, rig, M.weights(body))
        ctx["underbust_z"] = float(apex[2] - 0.075)
        ctx["navel_z"] = float(cfg["height_m"] * cfg["abs"]["navel_frac"])
        ctx["spine_y_fn"] = lambda z: G.spine_y(rig, z)
        ctx["glove_frames"] = {}
        for s in "lr":
            wrist = np.array(rig.data.bones["hand_" + s].head_local)
            kn = np.mean([rig.data.bones["%s_01_%s" % (f, s)].head_local for f in ("index", "middle", "ring", "pinky")], 0)
            ctx["glove_frames"][s] = (kn, (kn - wrist) / np.linalg.norm(kn - wrist))
        mats = {
            "Skin": [body], "Hair": [hair],
            "Outfit": [M.join([garments["top"], garments["shorts"], garments["wraps"]], name + "_Outfit")],
            "Eyes": [parts["eyes"]], "Gloves": [garments["gloves"]],
        }
        mats["Gloves"][0].name = mats["Gloves"][0].data.name = name + "_Gloves"
        skirt_info = None
    else:
        garments, hide, skirt_info = A.build(body, rig, cfg, col_body)
        hair, hair_info = HS.ashka(body, rig, parts, [garments["coat"], garments["shirt"]], cfg)
        zc = rig.data.bones["clavicle_l"].head_local[2]
        Vb = M.co(body)
        sel = (np.abs(Vb[:, 0]) < 0.01) & (np.abs(Vb[:, 2] - (zc + cfg["outfit"]["tattoo_dz"])) < 0.01)
        ty = Vb[sel, 1].min() if sel.any() else -0.1
        ctx["tattoo_center"] = np.array([0.0, ty, zc + cfg["outfit"]["tattoo_dz"]])
        ctx["z_button"] = rig.data.bones["pelvis"].head_local[2] + cfg["outfit"]["button_above_pelvis"]
        ctx["ankles"] = {s: np.array(rig.data.bones["foot_" + s].head_local) for s in "lr"}
        ctx["sole"] = cfg["sole_m"]
        ctx["loafer_dark"] = cfg["palette"]["loafer_dark"]
        A.coat_rig(rig, skirt_info)
        coat = garments["coat"]
        coat.name = coat.data.name = name + "_Coat"
        clothes = M.join([garments["shirt"], garments["tie"], garments["pants"], garments["loafers"]], name + "_Clothes")
        mats = {"Skin": [body], "Hair": [hair], "Coat": [coat], "Eyes": [parts["eyes"]], "Clothes": [clothes]}
    report["hair"] = hair_info
    M.delete_faces(body, hide)
    R.twist_constraints(rig)
    R.half_constraints(rig)

    # ---------------------------------------------------------------- bind, weights
    objs = [o for lst in mats.values() for o in lst]
    unweighted = {}
    for ob in objs:
        M.bind(ob, rig)
        for a in list(ob.data.attributes):
            if a.name == "src_vi":
                ob.data.attributes.remove(a)
        M.shade_smooth(ob)
        unweighted[ob.name] = finalize_weights(ob, rig, cfg["weight_limit"])
    report["unweighted_vertices"] = unweighted

    # ---------------------------------------------------------------- UVs
    head_bone = "head"

    def skin_scale(ob, faces, k):
        Wh = M.weights(ob, [head_bone, "neck_01"])
        ls, lt, lv = M.polys(ob)
        vi = np.concatenate([lv[ls[f]:ls[f] + lt[f]] for f in faces[:200]])
        if Wh[head_bone][vi].mean() > 0.5:
            return cfg["uv"]["head_scale"]
        tc = ctx.get("tattoo_center")
        if tc is not None:
            P = M.co(ob)[vi]
            if np.abs(P[:, 2].mean() - tc[2]) < 0.08 and np.abs(P[:, 0].mean()) < 0.05 and P[:, 1].mean() < 0:
                return cfg["uv"].get("tattoo_scale", 1.0)
        return 1.0

    G.pack_uvs(mats["Skin"], margin=0.006, island_scale=skin_scale)
    for key in mats:
        if key in ("Skin", "Hair", "Eyes"):
            continue
        G.pack_uvs(mats[key], margin=0.008)

    # ---------------------------------------------------------------- AO
    E.log("ambient occlusion")
    keep = ~np.isin(G.get_attr(hair, "part").astype(int), [H.P_BROW, H.P_LASH])
    tmp = M.duplicate(hair, "tmp_occ")
    M.delete_verts(tmp, ~keep)
    static = [o for o in objs if o is not hair]
    aos = T.vertex_ao(static, static, rays=cfg["ao_rays"], dist=0.08)
    aos_h = T.vertex_ao([hair], static + [tmp], rays=cfg["ao_rays"], dist=0.08)
    bpy.data.objects.remove(tmp)
    ctx["ao"] = {}
    for ob, a in list(zip(static, aos)) + [(hair, aos_h[0])]:
        ctx["ao"][ob.name] = M.smooth(a, M.adjacency(ob), 4, 0.5)
    ctx["ao"]["body"] = ctx["ao"][body.name]
    ctx["ao"]["hair"] = ctx["ao"][hair.name]
    # hair cap collider (hairline tint on the skin)
    capo = M.duplicate(hair, "tmp_cap")
    M.delete_verts(capo, G.get_attr(hair, "part").astype(int) != H.P_CAP)
    ctx["cap_collider"] = M.Collider([capo])
    bpy.data.objects.remove(capo)
    ctx["braid_periods"] = max(v.get("periods_in_v", 0) for v in hair_info.values() if isinstance(v, dict))
    ctx["brow_png"] = T.load_image(_mh_png("eyebrows", cfg["eyebrows"]))
    ctx["lash_png"] = T.load_image(_mh_png("eyelashes", cfg["eyelashes"]))

    # ---------------------------------------------------------------- textures + materials
    sizes = cfg["texture_sizes"]
    if cid == "wren":
        outfit_spec, acc_spec = SP.wren(cfg)
        jobs = {"Skin": ("skin", None), "Hair": ("hair", None), "Eyes": ("eyes", None),
                "Outfit": ("outfit", outfit_spec), "Gloves": ("accessory", acc_spec)}
    else:
        outfit_spec, acc_spec = SP.ashka(cfg)
        jobs = {"Skin": ("skin", None), "Hair": ("hair", None), "Eyes": ("eyes", None),
                "Coat": ("outfit", outfit_spec), "Clothes": ("accessory", acc_spec)}
    report["materials"] = {}
    for mat_key, (kind, spec) in jobs.items():
        res = sizes[kind]
        E.log("paint", mat_key, res)
        rs = T.Raster(mats[mat_key], res)
        if mat_key == "Skin":
            cfg_s = dict(cfg)
            D, N, ORM = PT.skin(rs, body, rig, cfg_s, ctx)
        elif mat_key == "Eyes":
            D, N, ORM = PT.eyes(rs, cfg, ctx)
        elif mat_key == "Hair":
            D, N, ORM = PT.hair(rs, cfg, ctx, hair)
        else:
            D, N, ORM = PT.garments(rs, cfg, ctx, mats[mat_key], spec)
        maps = {}
        for suffix, arr, ch in (("D", D, D.shape[1]), ("N", N, 3), ("ORM", ORM, 3)):
            img, cov = rs.to_image(arr, ch)
            img = T.dilate(img, cov, 24)
            path = os.path.join(tex_dir, "T_%s_%s_%s.png" % (name, mat_key, suffix))
            T.save_png(img, path, alpha=(ch == 4))
            maps[suffix] = path
        mat = T.build_material("M_%s_%s" % (name, mat_key), maps, alpha_clip=(mat_key == "Hair"),
                               two_sided=mat_key in ("Hair", "Coat", "Outfit", "Clothes"),
                               sss=0.12 if mat_key == "Skin" else 0.0,
                               specular={"Hair": 0.12, "Skin": 0.35}.get(mat_key, 0.5))
        for ob in mats[mat_key]:
            ob.data.materials.clear()
            ob.data.materials.append(mat)
        report["materials"][mat.name] = {"objects": [o.name for o in mats[mat_key]], "texture_size": res,
                                         "maps": {k: os.path.relpath(v, out) for k, v in maps.items()}}

    # ---------------------------------------------------------------- stats, save, export
    tris = {ob.name: M.tri_count(ob, evaluated=False) for ob in objs}
    report["triangles"] = tris
    report["triangles_total"] = int(sum(tris.values()))
    allz = np.concatenate([M.co(o)[:, 2] for o in objs])
    report["lowest_z_m"] = round(float(allz.min()), 5)
    report["top_z_m"] = round(float(allz.max()), 4)
    report["body_height_m"] = round(float(M.co(body)[:, 2].max() - (0 if not cfg.get("sole_m") else 0)), 4)
    report["core_signature"] = R.core_signature(rig)
    report["bones"] = len(rig.data.bones)
    report["exported_bones"] = sum(1 for b in rig.data.bones if b.use_deform)
    for ob in objs:
        ob.select_set(False)
    bpy.context.scene.frame_set(1)
    blend = os.path.join(out, name + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    fbx = os.path.join(out, "SK_%s.fbx" % name)
    export_fbx(fbx, rig, objs)
    lod1 = os.path.join(out, "SK_%s_LOD1.fbx" % name)
    report["lod1_triangles"] = export_lod1(lod1, rig, objs, cfg["lod1_ratio"])
    R.write_bones_json(rig, os.path.join(out, "bones.json"), cfg["display_name"], extra={
        "twist_bones": {tw[0]: {"parent": tw[1], "driven_by": tw[2], "factor": tw[3]} for tw in R.TWIST},
        "half_joints": {h[0]: {"limb": h[1], "parent": h[2], "factor": 0.5} for h in R.HALF},
        "blender_only_helpers": [b.name for b in rig.data.bones if not b.use_deform],
    })
    report["fbx_settings"] = {k: (sorted(v) if isinstance(v, set) else v) for k, v in FBX_SETTINGS.items()}
    report["build_seconds"] = round(time.time() - t0, 1)
    with open(os.path.join(out, "build_report.json"), "w") as f:
        json.dump(report, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    E.log("SUMMARY", name, "tris", report["triangles_total"], "lod1", report["lod1_triangles"],
          "bones", report["bones"], "secs", report["build_seconds"])
    return report


def _mh_png(sub, asset):
    p = E.find_asset(asset + ".mhclo", sub)
    return os.path.join(os.path.dirname(p), asset + ".png")


def export_fbx(path, rig, objs):
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    rig.data.pose_position = "REST"
    bpy.ops.export_scene.fbx(filepath=path, **FBX_SETTINGS)
    rig.data.pose_position = "POSE"


def export_lod1(path, rig, objs, ratio):
    copies = []
    tot = 0
    for o in objs:
        c = M.duplicate(o, o.name + "_LOD1")
        c.parent = rig
        m = c.modifiers.new("Decimate", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = ratio
        m.use_collapse_triangulate = False
        with bpy.context.temp_override(object=c, active_object=c):
            bpy.ops.object.modifier_move_to_index(modifier="Decimate", index=0)
        M.apply_modifier(c, "Decimate")
        tot += M.tri_count(c, evaluated=False)
        copies.append(c)
    export_fbx(path, rig, copies)
    for c in copies:
        me = c.data
        bpy.data.objects.remove(c)
        bpy.data.meshes.remove(me)
    return tot


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ids = [a for a in argv if not a.startswith("-")] or ["wren", "ashka"]
    E.enable_mpfb()
    reports = {}
    for cid in ids:
        reports[cid] = build(cid)
    if len(reports) == 2:
        same = reports["wren"]["core_signature"] == reports["ashka"]["core_signature"]
        E.log("core skeleton identical:", same)


if __name__ == "__main__":
    main()
