"""Imports both fighters (skeletal mesh, LOD1, textures, materials) and all their animations into /Game/Characters.

Inputs: $EH_WS/sourceart/characters/<char>/SK_<Char>.fbx (+_LOD1, textures/, alpha.json) and
$EH_WS/sourceart/anims/<char>/*.fbx. Each fighter gets its own skeleton; animations are sampled at 60 fps so frame N
of a move lands on simulation frame N. Run headless: bin/editor_py.sh Tools/Unreal/build_characters.py
Environment: EH_CHARS=wren,ashka (subset), EH_ANIMS_ONLY=1 (reimport clips only), EH_SKIP_ANIMS=1 (meshes only),
EH_ANIM_NAMES=A_Wren_L3,A_Ashka_H (import only these clips).
"""
import glob
import json
import os

import unreal

WS = os.environ["EH_WS"]
SRC = os.path.join(WS, "sourceart")
tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty
WHITE = "/Engine/EngineResources/WhiteSquareTexture"
FLATN = "/Engine/EngineMaterials/DefaultNormal"


def log(msg):
    unreal.log("EHCHAR " + msg)


def setp(obj, name, value):
    try:
        obj.set_editor_property(name, value)
    except Exception as exc:
        log(f"WARN {type(obj).__name__}.{name}: {exc}")


def fresh(path, name, cls, factory):
    full = f"{path}/{name}"
    if eal.does_asset_exist(full):
        eal.delete_asset(full)
    return tools.create_asset(name, path, cls, factory)


def tex_param(mat, name, x, y, default, sampler=None):
    t = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    setp(t, "parameter_name", name)
    if sampler is not None:
        setp(t, "sampler_type", sampler)
    setp(t, "texture", unreal.load_asset(default))
    return t


def scalar(mat, name, value, x, y):
    s = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, x, y)
    setp(s, "parameter_name", name)
    setp(s, "default_value", value)
    return s


def build_master(name, masked, two_sided=False):
    """Lit character surface with a soft stylised rim so fighters separate from the dark nave."""
    mat = fresh("/Game/Characters/Shared", name, unreal.Material, unreal.MaterialFactoryNew())
    setp(mat, "two_sided", masked or two_sided)
    # Without the usage flag a cooked or -game build silently swaps in the default material on skinned meshes.
    setp(mat, "used_with_skeletal_mesh", True)
    if masked:
        setp(mat, "blend_mode", unreal.BlendMode.BLEND_MASKED)
    d = tex_param(mat, "BaseColor", -1000, -200, WHITE)
    n = tex_param(mat, "Normal", -1000, 100, FLATN, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm = tex_param(mat, "ORM", -1000, 400, WHITE, unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -1000, -450)
    setp(tint, "parameter_name", "Tint")
    setp(tint, "default_value", unreal.LinearColor(1, 1, 1, 1))
    base = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -700, -250)
    mel.connect_material_expressions(d, "RGB", base, "A")
    mel.connect_material_expressions(tint, "", base, "B")
    mel.connect_material_property(base, "", MP.MP_BASE_COLOR)
    mel.connect_material_property(n, "RGB", MP.MP_NORMAL)
    mel.connect_material_property(orm, "R", MP.MP_AMBIENT_OCCLUSION)
    mel.connect_material_property(orm, "G", MP.MP_ROUGHNESS)
    mel.connect_material_property(orm, "B", MP.MP_METALLIC)
    fres = mel.create_material_expression(mat, unreal.MaterialExpressionFresnel, -700, 600)
    setp(fres, "exponent", 4.0)
    rim_col = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -700, 750)
    setp(rim_col, "parameter_name", "RimColor")
    setp(rim_col, "default_value", unreal.LinearColor(0.35, 0.42, 0.60, 1))
    rim = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -450, 650)
    mel.connect_material_expressions(fres, "", rim, "A")
    mel.connect_material_expressions(rim_col, "", rim, "B")
    rim2 = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -250, 650)
    mel.connect_material_expressions(rim, "", rim2, "A")
    mel.connect_material_expressions(scalar(mat, "RimIntensity", 0.35, -450, 800), "", rim2, "B")
    mel.connect_material_property(rim2, "", MP.MP_EMISSIVE_COLOR)
    if masked:
        mel.connect_material_property(d, "A", MP.MP_OPACITY_MASK)
    mel.recompile_material(mat)
    eal.save_asset(mat.get_path_name(), only_if_is_dirty=False)
    return mat


def import_textures(char_id, cap):
    out = {}
    for f in sorted(glob.glob(os.path.join(SRC, "characters", char_id, "textures", "*.png"))):
        name = os.path.splitext(os.path.basename(f))[0]
        task = unreal.AssetImportTask()
        task.filename = f
        task.destination_path = f"/Game/Characters/{cap}/Textures"
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        tools.import_asset_tasks([task])
        tex = unreal.load_asset(f"/Game/Characters/{cap}/Textures/{name}")
        if name.endswith("_N"):
            setp(tex, "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            setp(tex, "srgb", False)
            setp(tex, "flip_green_channel", True)
        elif name.endswith("_ORM"):
            setp(tex, "compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
            setp(tex, "srgb", False)
        setp(tex, "lod_group", unreal.TextureGroup.TEXTUREGROUP_CHARACTER)
        eal.save_asset(tex.get_path_name(), only_if_is_dirty=False)
        out[name] = tex
    return out


def import_mesh(char_id, cap):
    fbx = os.path.join(SRC, "characters", char_id, f"SK_{cap}.fbx")
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = f"/Game/Characters/{cap}"
    task.destination_name = f"SK_{cap}"
    task.replace_existing = True
    task.automated = True
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = True
    opts.import_materials = False
    opts.import_textures = False
    opts.import_animations = False
    opts.create_physics_asset = False
    opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    smd = opts.skeletal_mesh_import_data
    setp(smd, "import_morph_targets", True)
    setp(smd, "convert_scene", True)
    setp(smd, "force_front_x_axis", False)
    setp(smd, "normal_import_method", unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
    task.options = opts
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(f"/Game/Characters/{cap}/SK_{cap}")
    if mesh is None:
        raise RuntimeError(f"skeletal mesh import failed: {fbx}")
    skel = mesh.get_editor_property("skeleton")
    # The importer creates the skeleton package in memory only; animations and the cook need it on disk.
    eal.save_asset(skel.get_path_name(), only_if_is_dirty=False)
    eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    log(f"mesh {cap} skeleton={skel.get_path_name()} materials={len(mesh.materials)}")
    return mesh, skel


# Cloth whose openings, turned hems and wrap-band edges are single surfaces (shoe openings, coat and shorts hems).
TWO_SIDED = {"Coat", "Outfit", "Clothes"}


def assign_materials(mesh, char_id, cap, textures, masters, alpha):
    mats = list(mesh.materials)
    for i, sm in enumerate(mats):
        slot = str(sm.material_slot_name)
        key = slot
        for pre in ("MI_", "M_", f"{cap}_", f"{char_id}_"):
            if key.startswith(pre):
                key = key[len(pre):]
        tex_base = f"T_{cap}_{key}"
        masked = alpha.get(tex_base + "_D", False)
        mi = fresh(f"/Game/Characters/{cap}/Materials", f"MI_{cap}_{key}", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mi.set_editor_property("parent", masters["masked" if masked else ("two_sided" if key in TWO_SIDED else "opaque")])
        for suffix, param in (("_D", "BaseColor"), ("_N", "Normal"), ("_ORM", "ORM")):
            t = textures.get(tex_base + suffix)
            if t is not None:
                mel.set_material_instance_texture_parameter_value(mi, param, t)
            else:
                log(f"WARN missing texture {tex_base}{suffix} for slot {slot}")
        if key.lower().startswith("eye"):
            mel.set_material_instance_scalar_parameter_value(mi, "RimIntensity", 0.0)
        eal.save_asset(mi.get_path_name(), only_if_is_dirty=False)
        sm.material_interface = mi
        mats[i] = sm
        log(f"slot {slot} -> MI_{cap}_{key} masked={masked}")
    mesh.set_editor_property("materials", mats)
    eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)


def import_lod1(mesh, char_id, cap):
    lod = os.path.join(SRC, "characters", char_id, f"SK_{cap}_LOD1.fbx")
    if not os.path.exists(lod):
        return
    try:
        sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        idx = sub.import_lod(mesh, 1, lod)
        log(f"lod1 {cap} -> {idx}")
        eal.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    except Exception as exc:
        log(f"WARN lod1 {cap}: {exc}")


def import_anims(char_id, cap, skel):
    files = sorted(glob.glob(os.path.join(SRC, "anims", char_id, "*.fbx")))
    files += sorted(glob.glob(os.path.join(SRC, "anims", "*", f"victim_{char_id}", "*.fbx")))
    names = [n for n in os.environ.get("EH_ANIM_NAMES", "").split(",") if n]
    if names:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in names]
    count = 0
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        task = unreal.AssetImportTask()
        task.filename = f
        task.destination_path = f"/Game/Characters/{cap}/Anims"
        task.destination_name = name
        task.replace_existing = True
        task.automated = True
        opts = unreal.FbxImportUI()
        opts.import_mesh = False
        opts.import_as_skeletal = True
        opts.import_animations = True
        opts.import_materials = False
        opts.import_textures = False
        opts.skeleton = skel
        opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
        ad = opts.anim_sequence_import_data
        setp(ad, "animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        setp(ad, "use_default_sample_rate", False)
        setp(ad, "custom_sample_rate", 60)
        setp(ad, "remove_redundant_keys", False)
        setp(ad, "import_meshes_in_bone_hierarchy", False)
        setp(ad, "convert_scene", True)
        setp(ad, "force_front_x_axis", False)
        task.options = opts
        tools.import_asset_tasks([task])
        anim = unreal.load_asset(f"/Game/Characters/{cap}/Anims/{name}")
        if anim is None:
            log(f"FAIL anim {f}")
            continue
        eal.save_asset(anim.get_path_name(), only_if_is_dirty=False)
        count += 1
    log(f"anims {cap} {count}/{len(files)}")


def main():
    anims_only = os.environ.get("EH_ANIMS_ONLY") == "1"
    masters = None if anims_only else {"opaque": build_master("M_Character", False), "masked": build_master("M_CharacterMasked", True),
                                       "two_sided": build_master("M_CharacterTwoSided", False, True)}
    only = os.environ.get("EH_CHARS", "wren,ashka").split(",")
    for char_id in only:
        cap = char_id.capitalize()
        alpha_path = os.path.join(SRC, "characters", char_id, "alpha.json")
        alpha = json.load(open(alpha_path)) if os.path.exists(alpha_path) else {}
        if not anims_only:
            textures = import_textures(char_id, cap)
            mesh, skel = import_mesh(char_id, cap)
            assign_materials(mesh, char_id, cap, textures, masters, alpha)
            import_lod1(mesh, char_id, cap)
        else:
            mesh = unreal.load_asset(f"/Game/Characters/{cap}/SK_{cap}")
            skel = mesh.get_editor_property("skeleton")
        if os.environ.get("EH_SKIP_ANIMS") != "1":
            import_anims(char_id, cap, skel)
        if not os.environ.get("EH_ANIM_NAMES"):   # a named subset saves only its clips (import_anims saves each)
            eal.save_directory(f"/Game/Characters/{cap}", only_if_is_dirty=False, recursive=True)
    if not os.environ.get("EH_ANIM_NAMES"):
        eal.save_directory("/Game/Characters/Shared", only_if_is_dirty=False, recursive=True)
    log("DONE")


main()
