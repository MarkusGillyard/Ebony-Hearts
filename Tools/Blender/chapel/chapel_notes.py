"""Writes sourceart/chapel/NOTES.md from the build report (numbers are always live)."""
import os

import chapel_config as C

COLLISION = {
    "SM_Floor_Strip": "simple box (top at Z=0) - the only surface fighters stand on",
    "SM_Floor_Basin": "none needed (outside the fighting strip)",
    "SM_Water": "NO collision (visual only)",
}

DESCRIPTIONS = {
    "SM_Column_Clustered": "clustered pier: octagonal plinth, moulded base, 4+4 attached shafts, shaft ring, bell capital",
    "SM_WallRespond": "engaged half pier for walls (back half omitted, buried)",
    "SM_VaultShaft": "slender vaulting shaft from capital to vault springing",
    "SM_NaveBayUpper": "arcade arch (two orders + hood mould), spandrel and clerestory wall for one 4 m bay",
    "SM_Arch_AisleTransverse": "pointed transverse arch across an aisle (faces the camera)",
    "SM_AisleWallBay": "outer wall bay with tall lancet opening, surround, sill and stone bench",
    "SM_LancetGlass": "aisle lancet glazing",
    "SM_ClerestoryGlass": "clerestory lancet glazing",
    "SM_Vault_NaveBay": "quadripartite nave vault bay (16 x 4 m) with ribs and boss",
    "SM_Vault_AisleBay": "quadripartite aisle vault bay (4 x 4 m) with ribs and boss",
    "SM_ApseWall": "east wall: rose opening, embrasure arch, blind arcade, dado, string course, blind lancets",
    "SM_RoseFrame": "rose window stone tracery (12 petals, 24 quatrefoil roundels, sexfoil hub) + splayed surround",
    "SM_RoseGlass": "rose window glass disc (procedural stained glass, emissive)",
    "SM_Floor_Strip": "flat wet flags, Y -6..2, exactly Z = 0",
    "SM_Floor_Basin": "flooded nave floor Y 2..20.2, dips to about -0.35 at the pews",
    "SM_Water": "water surface plane (UE water material), 1 UV unit = 4 m",
    "SM_Pew_Intact": "pew with pointed pew ends",
    "SM_Pew_Broken": "pew snapped in two, one half sagging, end panel fallen",
    "SM_Pew_Overturned": "pew toppled onto its back",
    "SM_Debris_Planks": "loose floating boards",
    "SM_CandleCluster_A": "5 mixed candles on a wax puddle (flame cards included)",
    "SM_CandleCluster_B": "3 tall candles (stands, altar)",
    "SM_CandleCluster_C": "7 stubs on a wide puddle (steps, benches)",
    "SM_CandleCluster_Rail": "3 candles in a line for pew top rails",
    "SM_CandleStand": "iron tripod pricket stand (cluster sits on its pan)",
    "SM_Censer": "censer with ember band and suspension rods",
    "SM_Chain_1m": "1 m chain segment, stacked to the vault",
    "SM_AltarSteps": "two steps and platform",
    "SM_Altar": "altar block with blind niches and tattered cloth",
    "SM_Rubble_Block": "fallen ashlar block",
    "SM_Rubble_Drum": "fallen column drum",
    "SM_Rubble_Pile": "small stone pile",
    "SM_Rubble_Slab": "lifted floor slab",
    "SM_FG_BrokenBase": "foreground silhouette: broken column stump (<= 1.1 m)",
    "SM_FG_RubbleHeap": "foreground silhouette: rubble heap (<= 0.9 m)",
    "SM_Decal_Drip": "mesh decal: drip streaks under windows",
    "SM_Decal_Tide": "mesh decal: tide mark at the waterline",
    "SM_Decal_Moss": "mesh decal: moss patch",
    "SM_Decal_Silt": "mesh decal: silt patch on the flooded floor",
}


def collision_hint(name):
    return COLLISION.get(name, "NO collision (dressing never blocks fighters)")


def _fmt_bool(v):
    return "PASS" if v else "FAIL"


def write(rep):
    L = []
    a = L.append
    a("# The Drowned Chapel - stage source art")
    a("")
    a("Ebony Hearts stage environment, built entirely by script from `Tools/Blender/chapel/` "
      "(Blender %s). Original stylised dark-fantasy design: a flooded gothic nave read straight down its "
      "axis, slender clustered piers repeating into depth, broken pews half drowned in still water, and a "
      "large rose window over the altar as the focal point. Palette: cold moonlit blue-greys and near-blacks, "
      "warm amber candle accents only." % rep["blender"])
    a("")
    a("## Rebuild")
    a("")
    a("One command (from anywhere):")
    a("")
    a("```")
    a("\"%s/repo/Ebony-Hearts/Tools/Blender/chapel/run_build.sh\"" % C.ROOT)
    a("```")
    a("")
    a("which runs")
    a("")
    a("```")
    a("BLENDER_USER_RESOURCES=\"<slice>/userdata/blender-chapel\" \\")
    a("  /home/cinqic/.local/opt/blender-5.2.2-linux-x64/blender --background --factory-startup -t 6 \\")
    a("  --python Tools/Blender/chapel/build_chapel.py -- [--no-render] [--skip-textures] [--only centre,...]")
    a("```")
    a("")
    a("The build is deterministic (fixed seeds, own PNG writer): it regenerates every texture, mesh, FBX, "
      "`layout.json`, `build_report.json`, this file, `DrownedChapel.blend` and the review renders. "
      "FBX files embed a creation timestamp, so they are geometry-identical but not byte-identical between runs. "
      "Build time this run: %.0f s." % rep["build_seconds"])
    a("")
    a("Script modules: `build_chapel.py` (entry), `chapel_config.py` (all dimensions/paths), `chapel_geo.py` "
      "(mesh helpers, UVs, vertex colours), `chapel_pieces.py` (every unique mesh), `chapel_rose.py` (rose "
      "tracery definition shared by mesh and glass texture), `chapel_textures.py`, `chapel_materials.py` "
      "(Blender preview shaders), `chapel_layout.py` (instances, lights, cameras, UE conversion), "
      "`chapel_export.py` (FBX + validation), `chapel_render.py` (review lighting/renders), `chapel_notes.py`.")
    a("")
    a("## Outputs")
    a("")
    a("| Path (under `sourceart/chapel/`) | Content |")
    a("|---|---|")
    a("| `export/SM_*.fbx` | one FBX per unique piece (%d files) |" % len(rep["meshes"]))
    a("| `textures/T_<Material>_{D,N,ORM}.png` | 12 materials x 3 maps |")
    a("| `layout.json` | instances, UE transforms, material slots, lights, cameras, validation |")
    a("| `DrownedChapel.blend` | editable source: `Chapel_Pieces` (masters at origin), `Chapel_Layout` (linked instances), `Review` (capsules, lights, cameras) |")
    a("| `build_report.json` | full machine-readable report |")
    a("")
    a("## Frame, gameplay contract and validation")
    a("")
    a("Blender metres, Z up; X = fighting axis, +Y = depth away from the camera. Fighting plane Y = 0, "
      "feet on Z = 0, playable X = +-7.0. Nave column inner faces at X = +-7.6 (piers centred on +-8.0), "
      "piers at Y = -4, 0, 4, 8, 12, 16, apse wall inner face Y = 20, outer walls X = +-12, "
      "arch springing Z = 6.6, aisle vaults to 10.4, nave vault 13.4 -> 16.0.")
    a("")
    ch = rep["checks"]
    a("| Check | Result |")
    a("|---|---|")
    a("| Clear volume X[-7,7] Y[-1.3,1.3] Z[0,3.2] and no-hang zone to Z 3.4 (instance AABBs, floor/water excluded) | %s |" % _fmt_bool(ch["clear_volume_and_hang_zone"]["pass"]))
    a("| Floor top exactly Z = 0 across the strip; basin joins at Z = 0 | %s (max abs z = %s) |" % (_fmt_bool(ch["flat_floor_top_z0"]["pass"]), ch["flat_floor_top_z0"]["max_abs_z"]))
    a("| Censer bottoms >= 4.0 m | %s (%s) |" % (_fmt_bool(ch["censer_bottoms_m"]["pass"]), ", ".join("%.2f" % v for v in ch["censer_bottoms_m"]["values"])))
    a("| Foreground silhouettes only beyond X = +-8, Y -5..-2, <= 1.2 m | %s |" % _fmt_bool(ch["foreground_silhouettes"]["pass"]))
    a("| No n-gons (all pieces) | %s |" % _fmt_bool(ch["no_ngons"]["pass"]))
    a("| Materials <= 12 | %s (%d) |" % (_fmt_bool(ch["material_count"]["pass"]), ch["material_count"]["count"]))
    a("| Visible triangles <= 400k after instancing | %s (%d) |" % (_fmt_bool(ch["triangle_budget"]["pass"]), rep["instanced_triangles"]))
    rt = rep.get("fbx_roundtrip") or {}
    if rt:
        ok = all(v["pass"] for v in rt.values())
        a("| FBX re-import round trip (triangles + size) | %s (%d files) |" % (_fmt_bool(ok), len(rt)))
    a("")
    nd = ch["nearest_dressing_inside_piers"]
    a("Between the piers (|X| < 8.4) the nearest loose dressing is `%s`, whose bounds start at Y = %.2f m, i.e. "
      "%.2f m behind the clear volume; corner candle stands and rubble sit beyond the piers (|X| > 8.5). Censers "
      "hang from Y >= 5.2. All dressing is flagged NO collision in `layout.json`; only the floor needs collision, "
      "plus the two suggested stage-bound blocking volumes at X = +-7.25." % (nd["mesh"], nd["min_y_m"],
                                                                              nd["min_y_m"] - C.CLEAR_BOX[1][1]))
    a("")
    a("### Deliberate deviation: rose window height")
    a("")
    a("The brief puts the rose centre at about Z = 9. With the gameplay camera (Y -8.4, Z 1.35, 30 deg vertical FOV) "
      "and the feet kept ~9%% above the bottom edge, the top of the frame at the apse (Y = 20) is only about "
      "Z = 10.7, so a 6 m window centred at 9 m would be cut in half under the HUD. The window is therefore "
      "6.1 m across (tracery) with its centre at Z = %.1f m; it sits wholly in frame above the fighters' heads. "
      "It is one constant (`ROSE_Z` in `chapel_config.py`); raising it only moves the frame, opening and glass." % C.ROSE_Z)
    a("")
    a("## FBX export settings (Blender -> UE 5.8)")
    a("")
    a("Each piece is exported alone from its master object at the world origin (identity transform, transforms "
      "applied). Pivots are at the base centre: footprint centre on the floor line for grounded pieces (buried "
      "footings extend below it), centre of the wall thickness for wall pieces, springing-line centre for arches "
      "and vaults, bottom centre for glass, censers, chains and decals, and the bottom of the hood moulding on the "
      "tracery mid-plane for `SM_RoseFrame`.")
    a("")
    a("| Setting | Value |")
    a("|---|---|")
    for k, v in rep["fbx_settings"].items():
        a("| `%s` | `%s` |" % (k, v))
    a("")
    a("Scene units: metric, unit scale 1.0, so 1 Blender metre = 100 UE units. `axis_forward=-Z, axis_up=Y` with "
      "*Apply Transform* (`bake_space_transform`) writes the standard Y-up FBX that UE's importer converts "
      "back to Z-up: pieces import upright, with Blender +X -> UE +X, Blender +Y -> UE -Y. Recommended UE "
      "import: Convert Scene ON, Force Front X Axis OFF, Import Uniform Scale 1.0, Normal Import Method = Import "
      "Normals, Generate Lightmap UVs OFF, Combine Meshes OFF, Auto Generate Collision OFF (add collision to "
      "`SM_Floor_Strip` only), Vertex Color Import = Replace.")
    a("")
    a("`layout.json` instances carry the Blender transform (`location_m`, `rotation_deg` XYZ Euler, `scale`) and a "
      "precomputed `ue` block: `location_cm = (x, -y, z) * 100` and an FRotator (pitch, yaw, roll) obtained by "
      "mirroring the rotation matrix in Y. Cameras give UE yaw -90 (looking down UE -Y = Blender +Y).")
    a("")
    a("## Pieces and triangle counts")
    a("")
    a("| Mesh | Triangles | Instances | Instanced tris | Material slots | Notes |")
    a("|---|---:|---:|---:|---|---|")
    tot_unique = 0
    for n, m in rep["meshes"].items():
        tot_unique += m["triangles"]
        a("| %s | %d | %d | %d | %s | %s |" % (n, m["triangles"], m["instances"], m["instanced_triangles"],
                                             ", ".join(m["material_slots"]), DESCRIPTIONS.get(n, "")))
    a("| **Total** | **%d** unique | **%d** | **%d** | | |" % (tot_unique, rep["instances"], rep["instanced_triangles"]))
    a("")
    a("All pieces: bevelled chunky forms, smooth shading split at 38 deg, one UV map (`UVMap`, world-scaled "
      "tiling, no lightmap UVs), one byte colour attribute `Col`: R = cheap AO (cavities and base), G = convex "
      "edge-wear mask, B = base grime (height-based on grounded pieces). Normals face outward; single-sided "
      "surfaces (vault webs, floor, water, glass, decals, flame cards) face the camera/room.")
    a("")
    a("## Materials and textures")
    a("")
    a("12 materials. Every one has `T_<Material>_D` (base colour, sRGB), `T_<Material>_N` (OpenGL normal) and "
      "`T_<Material>_ORM` (R = AO, G = roughness, B = metallic) in `textures/`. In UE set N to Normal map "
      "compression and **flip green** (UE expects DirectX normals), ORM to Masks (no sRGB).")
    a("")
    a("| Material | Size | Source | Use / UE notes |")
    a("|---|---|---|---|")
    uses = {
        "StoneAshlar": "walls, vault webs. Multiply D by vertex R; darken + lower roughness below world Z 0.3 (wet line)",
        "StoneDressed": "piers, arches, ribs, tracery, mouldings, altar, steps, rubble. Lift D with vertex G (edge wear)",
        "FloorFlags": "floor; roughness already wet (puddles in low spots)",
        "WoodPew": "pews and planks, grain runs along local X",
        "IronAged": "stands, censers, chains, wicks",
        "CandleWax": "candles and wax puddles",
        "CandleFlame": "flame cards and censer ember band: unlit additive/translucent, two-sided, emissive = D.rgb x 12, opacity = D.a",
        "GlassRose": "rose glass: emissive = D x 8-20 (the focal light source), no shadows",
        "GlassLancet": "lancet/clerestory glass: emissive = D x 2-3, U spans the window width and tiles in V",
        "Water": "reference maps for the UE water material (ripple normal, 1 UV = 4 m)",
        "ClothAltar": "altar cloth, two-sided",
        "DecalGrime": "mesh decals (translucent/masked, opacity = D.a): atlas TL drips, TR tide band, BL moss, BR silt",
    }
    for name, t in sorted(rep["textures"].items()):
        src = rep["inputs"].get(name)
        s = ", ".join("%s `%s`" % (i["source"], i["asset_id"]) for i in src) if src else "procedural (original)"
        a("| M_%s | %dx%d | %s | %s |" % (name, t["size"][0], t["size"][1], s, uses.get(name, "")))
    a("")
    a("Normal maps: the Poly Haven inputs ship DirectX normals only; those were converted to OpenGL by flipping "
      "green (`nor_dx` -> GL). ambientCG inputs used their `NormalGL` maps directly. Procedural normals are "
      "generated in OpenGL convention. Photo inputs are graded towards the cool palette, partly simplified "
      "(blurred blend) for the stylised look, and downsampled with a 2x2 box filter where noted.")
    a("")
    a("## Third-party inputs (CC0)")
    a("")
    a("Read-only, from `downloads/thirdparty/`; nothing was downloaded. All are CC0 1.0.")
    a("")
    a("| Material | Source | Asset id | Folder | Files used |")
    a("|---|---|---|---|---|")
    for name, lst in sorted(rep["inputs"].items()):
        for i in lst:
            a("| M_%s | %s | `%s` | `%s` | %s |" % (name, i["source"], i["asset_id"], i["folder"], ", ".join(i["files"])))
    a("")
    a("Original (script-generated, no third-party input): rose-window stained glass, lancet grisaille glass, "
      "candle flame, water ripple normal, decal atlas, all geometry.")
    a("")
    a("## Lights and cameras (suggestions in `layout.json`)")
    a("")
    mo = rep["lights"]["moonlight"]
    a("- Moonlight: directional, travel direction (Blender) %s, elevation %.1f deg, colour %s, ~%s lux in UE "
      "(UE rotator pitch/yaw %s). It enters through the rose window and lays its pattern down the central aisle; "
      "enable light shafts/volumetric fog." % (mo["travel_direction_blender"], mo["elevation_deg"],
                                               mo["color_linear"], mo["ue_intensity_lux"],
                                               mo["ue_rotation_pitch_yaw_roll_deg"][:2]))
    cds = [c["ue_intensity_cd"] for c in rep["lights"]["candles"]]
    a("- Candles: %d point lights, one per candle cluster (positions = flame centroids), colour ~1850 K, "
      "%.0f-%.0f cd, attenuation 3.5-4.5 m; only the larger clusters cast shadows." % (len(cds), min(cds), max(cds)))
    a("- Cool fills: a large soft camera-side rect light and a high nave sky fill (no shadows).")
    a("- Emissive: rose glass x10, lancets x2.5, flames x12.")
    a("- Camera keys: centre X = 0, left/right corner X = -+%.1f; all at Y = %.1f, Z = %.2f, pitch +%.2f deg, "
      "vertical FOV 30 deg (horizontal 50.9 deg at 16:9). The corner keys frame the corner piers at the screen edge." %
      (C.CAM_PAN_X, C.CAM_Y, C.CAM_Z, C.CAM_PITCH_DEG))
    a("")
    a("## Review renders")
    a("")
    for r in rep["renders"]:
        a("- `%s`" % r)
    a("")
    a("EEVEE, 1920x1080, approximate moonlight + candles + cool fills, thin volumetric haze, AgX. Stand-in "
      "capsules (1.78 m and 1.70 m, dark neutral grey) at X = -1.4 and +1.4 on the fighting plane.")
    a("")
    a("## Known limitations")
    a("")
    a("- Review lighting is a Blender approximation; EEVEE cannot project coloured stained-glass light, so the "
      "rose pattern on the floor is only the tracery shadow. In UE use a light function or a projected "
      "(coloured) rect light for the coloured pattern.")
    a("- The water in the renders is a simple dithered glossy plane; the shipped `SM_Water` is meant for a UE "
      "water material (depth fade, ripples from `T_Water_N`).")
    a("- Wetness/waterline darkening is done from world height in the material (Blender preview does this); "
      "UE materials need the same world-Z term (see material table).")
    a("- Vertex AO is a cheap curvature/height estimate, not a bake.")
    a("- Back faces and anything behind the camera (Y < -6) are not modelled; the nave is open towards the camera.")
    a("- Vault webs, floor and glass are single-sided by design.")
    a("- FBX files contain a creation timestamp, so re-exports differ byte-wise while the geometry is identical.")
    a("- The foreground silhouettes sit where the brief allows (|X| > 8, Y -5..-2); with the specified camera "
      "they only enter frame on wider/zoomed-out shots.")
    a("- The rose window centre is %.1f m rather than ~9 m (see above)." % C.ROSE_Z)
    with open(C.NOTES_PATH, "w") as f:
        f.write("\n".join(L) + "\n")
