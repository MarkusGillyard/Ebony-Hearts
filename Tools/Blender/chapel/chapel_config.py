"""Shared configuration for The Drowned Chapel build.

All dimensions are Blender metres, Z up.  X is the fighting axis (screen left/right),
+Y runs away from the gameplay camera into depth.  Fighters stand on Z = 0 at Y = 0.
"""
import os

# ---------------------------------------------------------------------------
# Paths.  The slice root is derived from this file's location
# (<root>/repo/Ebony-Hearts/Tools/Blender/chapel) and can be overridden with
# the CHAPEL_SLICE_ROOT environment variable.
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_default_root = os.path.abspath(os.path.join(SCRIPT_DIR, *([os.pardir] * 5)))
ROOT = os.environ.get("CHAPEL_SLICE_ROOT", _default_root)

THIRDPARTY = os.path.join(ROOT, "downloads", "thirdparty")
OUT_DIR = os.path.join(ROOT, "sourceart", "chapel")
TEX_DIR = os.path.join(OUT_DIR, "textures")
EXPORT_DIR = os.path.join(OUT_DIR, "export")
LAYOUT_PATH = os.path.join(OUT_DIR, "layout.json")
BLEND_PATH = os.path.join(OUT_DIR, "DrownedChapel.blend")
NOTES_PATH = os.path.join(OUT_DIR, "NOTES.md")
REPORT_PATH = os.path.join(OUT_DIR, "build_report.json")
EVIDENCE_DIR = os.path.join(ROOT, "evidence", "chapel")

PH = os.path.join(THIRDPARTY, "PolyHaven", "textures")
ACG = os.path.join(THIRDPARTY, "ambientCG")

# ---------------------------------------------------------------------------
# Gameplay contract
# ---------------------------------------------------------------------------
PLAY_EDGE_X = 7.0
CLEAR_BOX = ((-7.0, 7.0), (-1.3, 1.3), (0.0, 3.2))   # must stay empty except floor top at Z=0
HANG_BOX = ((-7.0, 7.0), (-1.3, 1.3), (0.0, 3.4))    # nothing may hang below 3.4 above the strip
CENSER_MIN_Z = 4.0
FLAT_FLOOR_Y = (-6.0, 2.0)                           # floor is exactly Z=0 here
WATER_Z = 0.03
WATER_UV_METRES = 4.0                                # 1 UV unit = 4 m

# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------
BAY = 4.0
NAVE_X = 8.0                    # column centre lines; inner face at 7.6
COL_REACH = 0.40                # clustered shaft outer reach
AISLE_WALL_X = 12.0             # inner face of the outer walls
COLUMN_YS = [-4.0, 0.0, 4.0, 8.0, 12.0, 16.0]
BAY_CENTRES = [-2.0, 2.0, 6.0, 10.0, 14.0, 18.0]
APSE_Y = 20.0                   # inner face of the apse (east) wall
FLOOR_Y0 = -6.0
SPRING_Z = 6.6                  # capital top / arch springing
ARCADE_HALF_OPEN = 1.45         # half clear span of the arcade arches
NAVE_VAULT_SPRING = 13.4
NAVE_VAULT_APEX = 16.0
AISLE_VAULT_APEX = 10.4
NAVE_WALL_T = 0.70
OUTER_WALL_T = 0.90
APSE_WALL_T = 1.20

# Rose window (focal point).  See NOTES.md: centre lowered from the brief's ~9 m so
# the whole window reads under the HUD in the gameplay framing.
ROSE_Z = 7.7
ROSE_R_OPEN = 2.82              # outer radius of the glazed field
ROSE_R_TRACERY = 3.05           # outer radius of the tracery ring
ROSE_R_SURROUND = 3.45          # splayed moulding radius at the wall face
ROSE_R_HOOD = 3.62              # hood moulding outer radius
ROSE_TEX_R = 3.06               # half-size of the area covered by the glass texture
ROSE_PLANE_Y = APSE_Y + 0.6     # tracery mid-plane (inside the wall thickness)

# Floor basin: dips below Z=0 behind Y=2
BASIN_DEPTH = 0.35

# ---------------------------------------------------------------------------
# Cameras (gameplay keys).  Vertical FOV 30 deg.
# ---------------------------------------------------------------------------
CAM_Y = -8.4
CAM_Z = 1.35
CAM_PITCH_DEG = 3.25
CAM_VFOV_DEG = 30.0
CAM_PAN_X = 4.5                 # fully panned left/right frames the corner pillars

# Texture sizes
TEX_BIG = 2048
TEX_STD = 1024
TEX_SMALL = 512

SEED = 20261102
