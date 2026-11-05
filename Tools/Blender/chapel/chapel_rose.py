"""Rose window tracery definition, shared by the stone tracery mesh and the
procedural stained-glass texture so that openings and glass art line up exactly.

Coordinates are metres in the window plane: x right, z up, origin at the window
centre.  Angles are measured counter-clockwise from +x.
"""
import math
import numpy as np

N_PETAL = 12
PETAL_HALF = math.radians(15.0)        # half sector angle
R_HUB_OPEN = 0.52                      # glazed medallion radius
HUB_CUSPS = 6
HUB_CUSP_R = 0.11
R_HUB_STONE = 0.66                     # petals start here
S_SPRING = 1.42                        # petal arch springing (along the petal axis)
R_MID = 2.16                           # inner edge of the outer stone band
N_ROUNDEL = 24
ROUNDEL_RC = 2.55
ROUNDEL_R = 0.20
ROUNDEL_CUSP_R = 0.06
EYE_R = 0.085
EYE_RC = 2.00
R_OPEN = 2.82
R_TRACERY = 3.05


def spoke_half_width(s):
    t = (np.clip(s, R_HUB_STONE, R_MID) - R_HUB_STONE) / (R_MID - R_HUB_STONE)
    return 0.045 + 0.015 * t


def lateral_bound(s):
    """Half width of a petal opening at distance s along its axis (below the arch)."""
    return s * math.tan(PETAL_HALF) - spoke_half_width(s) / math.cos(PETAL_HALF)


W_SPRING = float(lateral_bound(S_SPRING))
RHO = 2.0 * W_SPRING                    # equilateral pointed head
T_C = W_SPRING - RHO                    # arc centre offset (lateral)
S_APEX = S_SPRING + math.sqrt(RHO ** 2 - T_C ** 2)


def petal_axis(k):
    return math.radians(90.0 + 30.0 * k)


def roundel_angle(j):
    return math.radians(90.0 + 15.0 * j)


def eye_angle(k):
    return math.radians(90.0 + 15.0 + 30.0 * k)


# ---------------------------------------------------------------------------
# Outlines (closed polylines) for the mesh
# ---------------------------------------------------------------------------

def _foil(cx, cz, radius, n_cusps, cusp_r, phase, samples):
    pts = []
    centres = [(radius * math.cos(phase + i * 2 * math.pi / n_cusps),
                radius * math.sin(phase + i * 2 * math.pi / n_cusps)) for i in range(n_cusps)]
    for i in range(samples):
        a = 2 * math.pi * i / samples
        ux, uz = math.cos(a), math.sin(a)
        t = radius
        for (px, pz) in centres:
            b = ux * px + uz * pz
            disc = cusp_r ** 2 - (px * px + pz * pz - b * b)
            if disc >= 0.0:
                ti = b - math.sqrt(disc)
                if 0.0 < ti < t:
                    t = ti
        pts.append((cx + ux * t, cz + uz * t))
    return pts


def _petal_local():
    """Petal outline in (s, t) petal coordinates, counter-clockwise."""
    # inner tip on the hub stone ring
    s0 = R_HUB_STONE
    for _ in range(8):
        t0 = float(lateral_bound(s0))
        s0 = math.sqrt(R_HUB_STONE ** 2 - t0 * t0)
    beta = math.atan2(t0, s0)
    pts = []
    # inner arc from right (-t) to left (+t)  -> traverse t from -t0 to +t0
    for i in range(5):
        a = -beta + 2 * beta * i / 4
        pts.append((R_HUB_STONE * math.cos(a), R_HUB_STONE * math.sin(a)))
    # left bound up to the spring
    n_line = 8
    for i in range(1, n_line + 1):
        s = s0 + (S_SPRING - s0) * i / n_line
        pts.append((s, float(lateral_bound(s))))
    # left arc spring -> apex
    g_a = math.acos((RHO - W_SPRING) / RHO)
    n_arc = 14
    for i in range(1, n_arc + 1):
        g = g_a * i / n_arc
        pts.append((S_SPRING + RHO * math.sin(g), T_C + RHO * math.cos(g)))
    # right arc apex -> spring (mirror)
    for i in range(n_arc - 1, -1, -1):
        g = g_a * i / n_arc
        pts.append((S_SPRING + RHO * math.sin(g), -(T_C + RHO * math.cos(g))))
    # right bound down to the tip (exclude endpoints shared with arcs)
    for i in range(n_line - 1, 0, -1):
        s = s0 + (S_SPRING - s0) * i / n_line
        pts.append((s, -float(lateral_bound(s))))
    # fix the apex duplicate
    out = []
    for p in pts:
        if not out or (abs(out[-1][0] - p[0]) > 1e-6 or abs(out[-1][1] - p[1]) > 1e-6):
            out.append(p)
    return out


def opening_outlines():
    """List of closed polylines [(x, z), ...] for every glazed opening."""
    outs = [_foil(0.0, 0.0, R_HUB_OPEN, HUB_CUSPS, HUB_CUSP_R, math.radians(90.0), 96)]
    local = _petal_local()
    for k in range(N_PETAL):
        psi = petal_axis(k)
        c, s_ = math.cos(psi), math.sin(psi)
        outs.append([(s * c - t * s_, s * s_ + t * c) for (s, t) in local])
    for k in range(N_PETAL):
        a = eye_angle(k)
        cx, cz = EYE_RC * math.cos(a), EYE_RC * math.sin(a)
        outs.append([(cx + EYE_R * math.cos(2 * math.pi * i / 20),
                      cz + EYE_R * math.sin(2 * math.pi * i / 20)) for i in range(20)])
    for j in range(N_ROUNDEL):
        a = roundel_angle(j)
        cx, cz = ROUNDEL_RC * math.cos(a), ROUNDEL_RC * math.sin(a)
        foil = _foil(0.0, 0.0, ROUNDEL_R, 4, ROUNDEL_CUSP_R, a + math.radians(45.0), 48)
        outs.append([(cx + x, cz + z) for (x, z) in foil])
    return outs


# ---------------------------------------------------------------------------
# Raster labels for the texture
# ---------------------------------------------------------------------------

def label_grid(x, z):
    """Return (label, local_s, local_t) arrays.
    label: 0 stone, 1 hub, 100+k petal k, 200+k eye k, 300+j roundel j."""
    r = np.hypot(x, z)
    th = np.arctan2(z, x)
    label = np.zeros(x.shape, np.int32)
    loc_s = np.zeros(x.shape, np.float32)
    loc_t = np.zeros(x.shape, np.float32)

    # hub
    hub = r <= R_HUB_OPEN
    for i in range(HUB_CUSPS):
        a = math.radians(90.0) + i * 2 * math.pi / HUB_CUSPS
        cx, cz = R_HUB_OPEN * math.cos(a), R_HUB_OPEN * math.sin(a)
        hub &= np.hypot(x - cx, z - cz) > HUB_CUSP_R
    label[hub] = 1
    loc_s[hub] = r[hub]

    # petals
    k = np.mod(np.round((th - math.radians(90.0)) / math.radians(30.0)).astype(np.int64), N_PETAL)
    psi = np.radians(90.0 + 30.0 * k)
    s = r * np.cos(th - psi)
    t = r * np.sin(th - psi)
    lb = s * math.tan(PETAL_HALF) - spoke_half_width(s) / math.cos(PETAL_HALF)
    inside = (r >= R_HUB_STONE) & (np.abs(t) <= lb)
    head = s > S_SPRING
    arc_ok = (np.abs(t) - T_C) ** 2 + (s - S_SPRING) ** 2 <= RHO ** 2
    petal = inside & (~head | arc_ok) & (s <= S_APEX + 1e-4)
    label[petal] = 100 + k[petal]
    loc_s[petal] = s[petal]
    loc_t[petal] = t[petal]

    # eyes
    ke = np.mod(np.round((th - math.radians(105.0)) / math.radians(30.0)).astype(np.int64), N_PETAL)
    ea = np.radians(105.0 + 30.0 * ke)
    ex, ez = EYE_RC * np.cos(ea), EYE_RC * np.sin(ea)
    eye = np.hypot(x - ex, z - ez) <= EYE_R
    label[eye] = 200 + ke[eye]
    loc_s[eye] = np.hypot(x - ex, z - ez)[eye]

    # roundels
    j = np.mod(np.round((th - math.radians(90.0)) / math.radians(15.0)).astype(np.int64), N_ROUNDEL)
    ra = np.radians(90.0 + 15.0 * j)
    cx, cz = ROUNDEL_RC * np.cos(ra), ROUNDEL_RC * np.sin(ra)
    dx, dz = x - cx, z - cz
    rd = np.hypot(dx, dz)
    rnd = rd <= ROUNDEL_R
    for i in range(4):
        ca = ra + math.radians(45.0) + i * math.pi / 2
        px, pz = cx + ROUNDEL_R * np.cos(ca), cz + ROUNDEL_R * np.sin(ca)
        rnd &= np.hypot(x - px, z - pz) > ROUNDEL_CUSP_R
    label[rnd] = 300 + j[rnd]
    # local frame: radial (s) / tangential (t) about the roundel centre
    loc_s[rnd] = (dx * np.cos(ra) + dz * np.sin(ra))[rnd]
    loc_t[rnd] = (-dx * np.sin(ra) + dz * np.cos(ra))[rnd]
    return label, loc_s, loc_t
