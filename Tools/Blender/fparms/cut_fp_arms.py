"""Cuts placeholder first-person arms out of a character's exported mesh: the skin, wraps and sleeves weighted to the
upper arms and everything below them, on the character's own skeleton, so the game can drive them with that
character's clips and its arm IK. It starts from the pipeline's SK_<Char>.fbx (the bind pose the game already uses;
the editable .blend's bind pose differs) and only reads it.

Usage: blender -b --factory-startup -P cut_fp_arms.py -- <SK_Char.fbx> <out.fbx> [min arm weight, default 0.5]
"""
import sys

import bmesh
import bpy

args = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = args[0], args[1]
MIN_WEIGHT = float(args[2]) if len(args) > 2 else 0.5
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC, use_anim=False, ignore_leaf_bones=False, automatic_bone_orientation=False,
                         primary_bone_axis="Y", secondary_bone_axis="X", use_custom_normals=True)

# Same export settings as Tools/Blender/characters/build_characters.py, so the skeleton matches the imported one.
FBX_SETTINGS = dict(
    use_selection=True, object_types={"ARMATURE", "MESH"},
    apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0,
    axis_forward="Y", axis_up="Z", bake_space_transform=False,
    use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=True, use_triangles=False,
    use_custom_props=False, add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
    use_armature_deform_only=True, armature_nodetype="NULL", bake_anim=False,
    path_mode="STRIP", embed_textures=False, colors_type="NONE")

rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")


def descendants(name):
    out = set()
    stack = [rig.data.bones[name]]
    while stack:
        b = stack.pop()
        out.add(b.name)
        stack.extend(b.children)
    return out


ARM = descendants("upperarm_l") | descendants("upperarm_r")
kept = []
for ob in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    groups = {g.index: g.name for g in ob.vertex_groups}
    keep = set()
    for v in ob.data.vertices:
        arm = sum(g.weight for g in v.groups if groups.get(g.group) in ARM)
        total = sum(g.weight for g in v.groups) or 1.0
        if arm / total >= MIN_WEIGHT:
            keep.add(v.index)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    print("FPARMS", ob.name, "kept", len(ob.data.vertices))
    if len(ob.data.vertices) > 0:
        kept.append(ob)
    else:
        bpy.data.objects.remove(ob)

bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
for o in kept:
    o.select_set(True)
bpy.context.view_layer.objects.active = rig
rig.data.pose_position = "REST"
bpy.ops.export_scene.fbx(filepath=OUT, **FBX_SETTINGS)
print("FPARMS exported", OUT, [o.name for o in kept])
