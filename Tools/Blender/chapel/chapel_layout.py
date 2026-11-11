"""Instance layout, suggested lights and camera keys for The Drowned Chapel.

All transforms are in the Blender frame (metres, X right, +Y depth, Z up, XYZ Euler
degrees).  UE equivalents are derived in ue_transform(): UE location (cm) =
(x, -y, z) * 100, rotation converted by mirroring Y (S R S with S = diag(1, -1, 1)).
"""
import math
import random

from mathutils import Euler, Matrix, Vector

import chapel_config as C
import chapel_pieces as P


def ue_transform(loc, rot_deg, scale):
    R = Euler([math.radians(a) for a in rot_deg], "XYZ").to_matrix()
    S = Matrix.Diagonal((1.0, -1.0, 1.0))
    Ru = S @ R @ S
    X = Vector((Ru[0][0], Ru[1][0], Ru[2][0]))
    Y = Vector((Ru[0][1], Ru[1][1], Ru[2][1]))
    Z = Vector((Ru[0][2], Ru[1][2], Ru[2][2]))
    pitch = math.atan2(X.z, math.sqrt(X.x * X.x + X.y * X.y))
    yaw = math.atan2(X.y, X.x)
    sy = Vector((-math.sin(yaw), math.cos(yaw), 0.0))
    roll = math.atan2(Z.dot(sy), Y.dot(sy))
    r = [round(math.degrees(v), 4) + 0.0 for v in (pitch, yaw, roll)]
    return {"location_cm": [round(loc[0] * 100, 3), round(-loc[1] * 100, 3) + 0.0, round(loc[2] * 100, 3)],
            "rotation_pitch_yaw_roll_deg": r, "scale": [round(s, 5) for s in scale]}


class Layout:
    def __init__(self):
        self.items = []

    def add(self, mesh, loc, rot=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0), tag=""):
        self.items.append({"mesh": mesh, "location_m": [round(v, 5) + 0.0 for v in loc],
                           "rotation_deg": [round(v, 4) + 0.0 for v in rot],
                           "scale": [round(v, 5) for v in scale], "tag": tag})
        return self.items[-1]


def matrix_of(item):
    loc = Vector(item["location_m"])
    rot = Euler([math.radians(a) for a in item["rotation_deg"]], "XYZ").to_matrix().to_4x4()
    sc = Matrix.Diagonal(Vector(item["scale"] + [1.0]))
    return Matrix.Translation(loc) @ rot @ sc


def wall_point(wall_loc, rot_z, local):
    """World position of a point given in a wall's local frame."""
    m = Matrix.Translation(Vector(wall_loc)) @ Matrix.Rotation(math.radians(rot_z), 4, "Z")
    return tuple(m @ Vector(local))


# pew rows: (Y, left variant, right variant); variants: I intact, B broken, O overturned, - none, D debris
PEW_ROWS = [
    (3.50, "D", "O"),
    (4.75, "B", "I"),
    (6.00, "I", "B"),
    (7.25, "O", "I"),
    (8.50, "I", "I"),
    (9.75, "B", "O"),
    (11.00, "I", "I"),
    (12.25, "D", "I"),
    (13.50, "I", "B"),
]
PEW_MESH = {"I": "SM_Pew_Intact", "B": "SM_Pew_Broken", "O": "SM_Pew_Overturned", "D": "SM_Debris_Planks"}


def build(info):
    """info: dict mesh name -> Piece.extra.  Returns (Layout, lights, cameras)."""
    L = Layout()
    rng = random.Random(C.SEED + 501)
    ys_cols = C.COLUMN_YS

    # --- structure -------------------------------------------------------
    for y in ys_cols:
        for sx in (-1, 1):
            L.add("SM_Column_Clustered", (sx * C.NAVE_X, y, 0.0), tag="column")
            L.add("SM_WallRespond", (sx * C.AISLE_WALL_X, y, 0.0), (0, 0, -90 * sx), tag="respond")
            L.add("SM_VaultShaft", (sx * (C.NAVE_X - 0.45), y, C.SPRING_Z), tag="vault_shaft")
            L.add("SM_Arch_AisleTransverse", (sx * (C.NAVE_X + C.AISLE_WALL_X) / 2, y, C.SPRING_Z), tag="arch")
    for sx in (-1, 1):
        L.add("SM_WallRespond", (sx * C.NAVE_X, C.APSE_Y, 0.0), tag="respond")
        L.add("SM_VaultShaft", (sx * (C.NAVE_X - 0.45), C.APSE_Y - 0.25, C.SPRING_Z), tag="vault_shaft")
        L.add("SM_WallRespond", (sx * C.AISLE_WALL_X, C.APSE_Y, 0.0), (0, 0, -45 * sx), tag="respond")

    win = P.AISLE_WIN
    for yc in C.BAY_CENTRES:
        for sx in (-1, 1):
            rz = -90 * sx
            L.add("SM_NaveBayUpper", (sx * C.NAVE_X, yc, C.SPRING_Z), (0, 0, rz), tag="nave_wall")
            L.add("SM_ClerestoryGlass", (sx * C.NAVE_X, yc, C.SPRING_Z + 4.6 - 0.04), (0, 0, rz), tag="glass")
            L.add("SM_Vault_AisleBay", (sx * (C.NAVE_X + C.AISLE_WALL_X) / 2, yc, C.SPRING_Z), tag="vault")
            wl = (sx * C.AISLE_WALL_X, yc, 0.0)            # point on the room face
            L.add("SM_AisleWallBay", wall_point(wl, rz, (0, C.OUTER_WALL_T / 2, 0)), (0, 0, rz), tag="outer_wall")
            L.add("SM_LancetGlass", wall_point(wl, rz, (0, C.OUTER_WALL_T / 2, win["sill"] - 0.04)), (0, 0, rz),
                  tag="glass")
        L.add("SM_Vault_NaveBay", (0.0, yc, C.NAVE_VAULT_SPRING), tag="vault")
    for sx in (-1, 1):
        wl = (sx * (C.NAVE_X + C.AISLE_WALL_X) / 2, C.APSE_Y, 0.0)
        L.add("SM_AisleWallBay", wall_point(wl, 0, (0, C.OUTER_WALL_T / 2, 0)), tag="aisle_end_wall")
        L.add("SM_LancetGlass", wall_point(wl, 0, (0, C.OUTER_WALL_T / 2, win["sill"] - 0.04)), tag="glass")

    L.add("SM_ApseWall", (0.0, C.APSE_Y + C.APSE_WALL_T / 2, 0.0), tag="apse")
    rf = info["SM_RoseFrame"]["centre_z_local"]
    L.add("SM_RoseFrame", (0.0, C.ROSE_PLANE_Y, C.ROSE_Z - rf), tag="rose")
    rg = info["SM_RoseGlass"]["centre_z_local"]
    L.add("SM_RoseGlass", (0.0, C.ROSE_PLANE_Y + 0.02, C.ROSE_Z - rg), tag="glass")

    L.add("SM_Floor_Strip", (0.0, (C.FLAT_FLOOR_Y[0] + C.FLAT_FLOOR_Y[1]) / 2, 0.0), tag="floor")
    L.add("SM_Floor_Basin", (0.0, info["SM_Floor_Basin"]["centre_y"], 0.0), tag="floor")
    L.add("SM_Water", (0.0, info["SM_Water"]["centre_y"], C.WATER_Z), tag="water")
    L.add("SM_AltarSteps", (0.0, P.STEPS_YC, 0.0), tag="altar")
    altar_y = 19.0
    L.add("SM_Altar", (0.0, altar_y, P.PLATFORM_Z), tag="altar")

    # --- pews ------------------------------------------------------------
    for (y, lv, rv) in PEW_ROWS:
        for sx, v in ((-1, lv), (1, rv)):
            if v == "-":
                continue
            x = sx * 3.30 + rng.uniform(-0.15, 0.15)
            yy = y + rng.uniform(-0.12, 0.12)
            yaw = rng.uniform(-3.5, 3.5)
            roll = rng.uniform(-1.5, 1.5)
            if v == "O":
                yaw += sx * rng.uniform(10, 22)
                x -= sx * 0.35
            if v == "D":
                yaw = rng.uniform(-40, 40)
            z = P.basin_z(x, yy) - rng.uniform(0.0, 0.05)
            if sx > 0 and v != "D":
                yaw += 0.0
            L.add(PEW_MESH[v], (x, yy, z), (roll, 0.0, yaw), tag="pew")

    # --- candles ---------------------------------------------------------
    stand_top = info["SM_CandleStand"]["top_z"]
    altar_top = P.PLATFORM_Z + info["SM_Altar"]["top_z"]
    stands = [(-9.35, 2.70), (9.35, 2.70), (-10.3, 9.20), (10.3, 8.80), (-10.4, 14.6), (10.4, 14.4),
              (-5.30, 17.55), (5.30, 17.55)]
    for (x, y) in stands:
        z = P.PLATFORM_Z if y > 17.3 else P.basin_z(x, y)
        L.add("SM_CandleStand", (x, y, z), (0, 0, rng.uniform(0, 120)), tag="stand")
        L.add("SM_CandleCluster_B", (x, y, z + stand_top), (0, 0, rng.uniform(0, 360)), tag="candles")
    L.add("SM_CandleCluster_A", (0.0, altar_y + 0.05, altar_top), (0, 0, 15), tag="candles")
    for sx in (-1, 1):
        L.add("SM_CandleCluster_B", (sx * 1.05, altar_y + 0.15, altar_top), (0, 0, 40 * sx), tag="candles")
        L.add("SM_CandleCluster_C", (sx * 2.3, 16.62, 0.08), (0, 0, 70 * sx), tag="candles")
        L.add("SM_CandleCluster_C", (sx * 4.35, 16.62, 0.08), (0, 0, 20 * sx), tag="candles")
        L.add("SM_CandleCluster_B", (sx * 6.9, C.APSE_Y - 0.25, 0.55), (0, 0, 10), tag="candles")
        L.add("SM_CandleCluster_A", (sx * 11.70, 6.0, 0.45), (0, 0, 33 * sx), tag="candles")
        L.add("SM_CandleCluster_C", (sx * 11.72, 12.1, 0.45), (0, 0, 80), tag="candles")
    # candles on the top rails of every other intact pew, at the outer (wall-side) end so the
    # bright points stay away from the fighters' silhouettes in the centre of the frame
    rail_rows = []
    for it in L.items:
        if it["mesh"] == "SM_Pew_Intact":
            rail_rows.append(it)
    for it in rail_rows[::2]:
        m = matrix_of(it)
        x_end = 1.25 if it["location_m"][0] > 0 else -1.25        # outer end of the pew
        pos = m @ Vector((x_end, -0.28, 0.97))
        L.add("SM_CandleCluster_Rail", tuple(pos), (it["rotation_deg"][0], 0, it["rotation_deg"][2]), tag="candles")
    # --- rubble ------------------------------------------------------------
    rub = [("SM_Rubble_Block", -9.6, 1.9, 22), ("SM_Rubble_Block", 9.9, 5.4, -14), ("SM_Rubble_Drum", 10.2, 7.0, 64),
           ("SM_Rubble_Pile", -10.6, 10.6, 0), ("SM_Rubble_Pile", 10.7, 16.2, 40), ("SM_Rubble_Block", -10.9, 16.8, 71),
           ("SM_Rubble_Drum", -6.3, 14.9, -18), ("SM_Rubble_Slab", -5.7, 3.25, 9), ("SM_Rubble_Slab", 6.3, 9.1, -27),
           ("SM_Rubble_Slab", 0.7, 15.2, 12), ("SM_Rubble_Block", 6.6, 15.6, 38), ("SM_Rubble_Pile", -9.2, 4.6, 120)]
    for (m, x, y, yaw) in rub:
        z = P.basin_z(x, y)
        rot = (rng.uniform(-6, 6), rng.uniform(-6, 6), yaw)
        if m == "SM_Rubble_Slab":
            rot = (rng.uniform(-14, -6), rng.uniform(4, 11), yaw)
            z += 0.05
        L.add(m, (x, y, z - 0.03), rot, tag="rubble")
    L.add("SM_CandleCluster_C", (9.9, 5.4, P.basin_z(9.9, 5.4) - 0.03 + 0.40), (0, 0, 30), tag="candles")
    L.add("SM_CandleCluster_A", (-9.6, 1.9, 0.40), (0, 0, -20), tag="candles")
    L.add("SM_FG_BrokenBase", (-9.15, -3.1, 0.0), (0, 0, 12), tag="foreground")
    L.add("SM_FG_RubbleHeap", (9.35, -2.7, 0.0), (0, 0, -16), tag="foreground")

    # --- censers -------------------------------------------------------------
    censers = [(-3.6, 5.2, 4.25), (3.9, 7.6, 4.55), (-4.6, 10.8, 4.80), (3.4, 12.8, 4.35), (-2.9, 15.6, 5.10)]
    ctop = info["SM_Censer"]["top_z"]
    for (x, y, z) in censers:
        L.add("SM_Censer", (x, y, z), (0, 0, rng.uniform(0, 120)), tag="censer")
        zz = z + ctop
        vault_z = C.NAVE_VAULT_APEX + 0.3
        k = 0
        while zz < vault_z:
            L.add("SM_Chain_1m", (x, y, zz), (0, 0, 45 * (k % 2)), tag="chain")
            zz += 1.0
            k += 1

    # --- decals ----------------------------------------------------------------
    for yc in C.BAY_CENTRES:
        for sx in (-1, 1):
            rz = -90 * sx
            wl = (sx * C.AISLE_WALL_X, yc, 0.0)
            if yc > 0:
                L.add("SM_Decal_Drip", wall_point(wl, rz, (0, -0.015, -0.2)), (0, 0, rz), tag="decal")
            L.add("SM_Decal_Tide", wall_point(wl, rz, (0, -0.355, -0.55)), (0, 0, rz), tag="decal")
    for x in (-6.2, -2.1, 2.1, 6.2):
        L.add("SM_Decal_Tide", (x, C.APSE_Y - 0.385, -0.55), tag="decal")
    for (x, y, rz) in ((-11.99, 7.3, 90), (11.99, 11.2, -90), (-11.99, 15.4, 90)):
        L.add("SM_Decal_Moss", (x, y, 0.42), (0, 0, rz), tag="decal")
    for (x, y) in ((-3.4, 4.2), (2.7, 5.6), (-1.0, 8.7), (4.8, 11.6), (-4.9, 12.9), (1.6, 14.0), (-9.8, 8.0), (9.6, 12.6)):
        L.add("SM_Decal_Silt", (x, y, P.basin_z(x, y) + 0.015), (0, 0, rng.uniform(0, 360)), tag="decal")

    lights = suggested_lights(L, info)
    cams = camera_keys()
    return L, lights, cams


def suggested_lights(L, info):
    flames = []
    for it in L.items:
        if it["mesh"].startswith("SM_CandleCluster_"):
            m = matrix_of(it)
            pts = [m @ Vector(f) for f in info[it["mesh"]]["flames"]]
            c = sum(pts, Vector((0, 0, 0))) / len(pts)
            flames.append((it, c, len(pts)))
    candles = []
    for it, c, n in flames:
        pos = (round(c.x, 3), round(c.y, 3), round(c.z + 0.06, 3))
        candles.append({"location_m": list(pos), "color_linear": [1.0, 0.56, 0.24], "temperature_k": 1850,
                        "blender_watts": round(6.5 + 3.5 * n, 2), "ue_intensity_cd": round(4.0 + 2.0 * n, 1),
                        "ue_attenuation_radius_cm": 450 if n >= 5 else 350, "source_radius_cm": 2.0,
                        "cast_shadows": n >= 5, "ue": ue_transform(pos, (0, 0, 0), (1, 1, 1))["location_cm"]})
    moon_dir = Vector((-0.03, -0.866, -0.50)).normalized()      # direction the light travels
    pitch = math.degrees(math.asin(moon_dir.z))
    yaw_ue = math.degrees(math.atan2(-moon_dir.y, moon_dir.x))
    moon = {"type": "directional", "travel_direction_blender": [round(v, 4) for v in moon_dir],
            "travel_direction_ue": [round(moon_dir.x, 4), round(-moon_dir.y, 4), round(moon_dir.z, 4)],
            "ue_rotation_pitch_yaw_roll_deg": [round(pitch, 2), round(yaw_ue, 2), 0.0],
            "elevation_deg": round(-pitch, 2),
            "note": "Enters through the rose window (centre %.1f m) from high behind the apse and lays the tracery "
                    "pattern down the central aisle over the pews and water just behind the fighting strip "
                    "(Y ~1.5-13), so the fighters read against a lit band and are rim-lit from behind." %
                    C.ROSE_Z,
            "color_linear": [0.60, 0.70, 1.0], "blender_sun_strength": 11.0, "ue_intensity_lux": 4.0,
            "ue_light_shaft_bloom": True, "volumetric_scattering_intensity": 1.5}
    fills = [
        {"name": "CameraSideCoolFill", "type": "rect/area", "location_m": [0.0, -5.5, 4.5],
         "aim_at_m": [0.0, 2.0, 1.0], "size_m": [8.0, 3.0], "color_linear": [0.55, 0.65, 0.85],
         "blender_watts": 900.0, "ue_intensity_cd": 12.0, "cast_shadows": False,
         "purpose": "keeps the fighters' fronts readable against the backlit nave"},
        {"name": "NaveSkyFill", "type": "rect/area", "location_m": [0.0, 9.0, 12.0], "aim_at_m": [0.0, 9.0, 0.0],
         "size_m": [13.0, 20.0], "color_linear": [0.45, 0.55, 0.80], "blender_watts": 2600.0,
         "ue_intensity_cd": 22.0, "ue_attenuation_radius_cm": 2600, "cast_shadows": False, "volume_factor": 0.3,
         "purpose": "soft top-down cool fill: lifts the floor around the fighters' feet and the pews so silhouettes read"},
        # The moon backlights the nave, so without this the apse wall and altar go black in Unreal and the fighters'
        # dark clothing loses its backdrop. Matches the fill used in the first in-engine review.
        {"name": "NaveApseFill", "type": "point/sphere", "location_m": [0.0, 10.0, 11.5], "radius_m": 3.0,
         "color_linear": [0.45, 0.55, 0.80], "blender_watts": 2500.0, "ue_intensity_cd": 25.0,
         "ue_attenuation_radius_cm": 2400, "cast_shadows": False,
         "purpose": "cool wash on the apse wall, altar and back pews behind the fighting strip"},
    ]
    return {"moonlight": moon, "candles": candles, "cool_fills": fills,
            "window_emissive": {"M_GlassRose": {"emissive_scale": 10.0}, "M_GlassLancet": {"emissive_scale": 2.5},
                                "M_CandleFlame": {"emissive_scale": 12.0}},
            "fog": {"exponential_height_fog_density": 0.02, "volumetric": True, "albedo_linear": [0.55, 0.62, 0.78],
                    "note": "low cool haze; keep the strip itself clear so fighters stay crisp"}}


def camera_key(name, x, y=C.CAM_Y, z=C.CAM_Z, pitch=C.CAM_PITCH_DEG, vfov=C.CAM_VFOV_DEG):
    aspect = 16.0 / 9.0
    hfov = math.degrees(2 * math.atan(math.tan(math.radians(vfov / 2)) * aspect))
    return {"name": name, "location_m": [x, y, z], "rotation_deg": [90.0 + pitch, 0.0, 0.0],
            "vertical_fov_deg": vfov, "horizontal_fov_deg_16x9": round(hfov, 3),
            "ue": {"location_cm": [x * 100, -y * 100, z * 100], "rotation_pitch_yaw_roll_deg": [pitch, -90.0, 0.0],
                   "fov_deg_horizontal": round(hfov, 3)},
            "note": "Blender camera looks down its -Z; rotation X = 90 + pitch looks along +Y."}


def camera_keys():
    return [camera_key("centre", 0.0), camera_key("left_corner", -C.CAM_PAN_X),
            camera_key("right_corner", C.CAM_PAN_X)]
