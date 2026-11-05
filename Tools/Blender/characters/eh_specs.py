"""Paint specifications (colours, CC0 detail surfaces, trims, stitching) for the garment materials,
plus the few garment details painted from 3D landmarks (glove quilting, coat buttons, loafer strap)."""
import numpy as np

import eh_ashka as A
import eh_mesh as M
import eh_tex as T
import eh_wren as Wr


def wren(cfg):
    p = cfg["palette"]
    outfit = {
        Wr.TOP_MAIN: dict(color=p["black"], rough=0.86, fabric="Fabric034", tile=0.09, fabric_lum=0.07,
                          fabric_n=0.8, trim=p["blue"], trim_lo=0.5, trim_hi=0.72),
        Wr.TOP_BAND: dict(color=p["blue"], rough=0.78, fabric="Fabric034", tile=0.05, fabric_lum=0.05,
                          trim=p["black"], trim_lo=0.55, trim_hi=0.8),
        Wr.SHORTS_MAIN: dict(color=p["black"], rough=0.7, fabric="Fabric040", tile=0.1, fabric_lum=0.05,
                             fabric_n=0.6, trim=p["blue"], trim_lo=0.5, trim_hi=0.72),
        Wr.SHORTS_BAND: dict(color=p["black_light"], rough=0.66, fabric="Fabric034", tile=0.05,
                             trim=p["blue"], trim_lo=0.5, trim_hi=0.75),
        Wr.SHORTS_PANEL: dict(color=p["blue"], rough=0.62, fabric="Fabric040", tile=0.1, fabric_lum=0.05,
                              trim=p["blue_light"], trim_lo=0.5, trim_hi=0.72),
        Wr.WRAP: dict(color=p["black_light"], rough=0.85, fabric="Fabric001", tile=0.04, fabric_lum=0.12,
                      fabric_n=1.2, trim=p["blue"], trim_lo=0.55, trim_hi=0.8),
        "_extra": [_shorts_side_stripe],
        "_zones": (Wr.zones, ["zone_band", "zone_panel", "g_dorsal", "g_sk", "g_tfa", "g_strap"]),
    }
    gloves = {
        Wr.GLOVE_PAD: dict(color=p["black"], rough=0.4, fabric="Leather026", tile=0.07, fabric_lum=0.07,
                           stitch=p["blue_light"], stitch_at=0.3),
        Wr.GLOVE_PALM: dict(color=p["black_light"], rough=0.55, fabric="Leather026", tile=0.05),
        Wr.GLOVE_LOOP: dict(color=p["black"], rough=0.5, fabric="Leather026", tile=0.05,
                            trim=p["blue"], trim_lo=0.6, trim_hi=0.85),
        Wr.GLOVE_CUFF: dict(color=p["black"], rough=0.5, fabric="Leather026", tile=0.05,
                            trim=p["blue"], trim_lo=0.6, trim_hi=0.85),
        Wr.GLOVE_STRAP: dict(color=p["blue"], rough=0.55, fabric="Fabric040", tile=0.035, fabric_lum=0.06,
                             trim=p["blue_light"], trim_lo=0.6, trim_hi=0.9),
        "_extra": [_glove_quilt],
        "_zones": (Wr.zones, ["zone_band", "zone_panel", "g_dorsal", "g_sk", "g_tfa", "g_strap"]),
    }
    return outfit, gloves


def ashka(cfg):
    p = cfg["palette"]
    fab = dict(fabric="Fabric066", tile=0.012, fabric_lum=0.015, fabric_n=0.15)
    coat = {
        A.COAT_MAIN: dict(color=p["coat"], rough=0.7, stitch=p["coat_light"], stitch_at=0.3, **fab),
        A.COAT_SKIRT: dict(color=p["coat"], rough=0.7, stitch=p["coat_light"], stitch_at=0.3, **fab),
        A.COAT_CUFF: dict(color=p["coat"], rough=0.66, stitch=p["coat_light"], stitch_at=0.3, **fab),
        A.COAT_LAPEL: dict(color=p["coat"], rough=0.66, **fab),
        A.COAT_COLLAR: dict(color=p["coat"], rough=0.62, stitch=p["coat_light"], stitch_at=0.4, **fab),
        A.COAT_BELT: dict(color="#131316", rough=0.58, fabric="Leather026", tile=0.05, fabric_lum=0.05,
                          stitch="#3c3c42", stitch_at=0.3),
        A.COAT_BUCKLE: dict(color=p["metal"], rough=0.32, metal=1.0),
        "_extra": [_coat_buttons],
    }
    clothes = {
        A.SHIRT: dict(color=p["shirt"], rough=0.75, fabric="Fabric001", tile=0.05, fabric_lum=0.05),
        A.SHIRT_COLLAR: dict(color=p["shirt"], rough=0.72, fabric="Fabric001", tile=0.04, fabric_lum=0.05,
                             stitch="#c9c8c2", stitch_at=0.35),
        A.SHIRT_CUFF: dict(color=p["shirt"], rough=0.72, fabric="Fabric001", tile=0.04, fabric_lum=0.05),
        A.TIE: dict(color=p["tie"], rough=0.32, fabric="Fabric040", tile=0.03, fabric_lum=0.04, fabric_n=0.35),
        A.PANTS: dict(color=p["pants"], rough=0.72, fabric="Fabric066", tile=0.02, fabric_lum=0.03, fabric_n=0.4),
        A.LOAFER: dict(color=p["loafer"], rough=0.4, fabric="Leather021", tile=0.06, fabric_lum=0.12,
                       stitch=p["loafer_dark"], stitch_at=0.3),
        A.LOAFER_SOLE: dict(color=p["loafer_dark"], rough=0.6),
        "_extra": [_loafer_strap],
    }
    return coat, clothes


# ----------------------------------------------------------------------------- extras

def _shorts_side_stripe(rs, part, col, nts, rough, metal, ctx):
    return col, nts, rough, metal


def _glove_quilt(rs, part, col, nts, rough, metal, ctx):
    m = part == Wr.GLOVE_PAD
    if not m.any():
        return col, nts, rough, metal
    P = rs.P[m]
    g = np.zeros(m.sum(), np.float32)
    for s, (kn, ax) in ctx["glove_frames"].items():
        side = (P[:, 0] > 0) if s == "l" else (P[:, 0] <= 0)
        sk = (P - kn) @ ax
        lines = np.exp(-((np.mod(sk + 0.004, 0.017) - 0.0085) / 0.0011) ** 2) * (sk < -0.005) * (sk > -0.075)
        g = np.where(side, lines, g)
    col[m] = col[m] * (1 - 0.45 * g[:, None])
    n = nts[m] * 2 - 1
    n[:, 1] -= g * 0.5
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    nts[m] = n * 0.5 + 0.5
    return col, nts, rough, metal


def _coat_buttons(rs, part, col, nts, rough, metal, ctx):
    m = (part == A.COAT_MAIN) | (part == A.COAT_SKIRT)
    P = rs.P
    front = -rs.N[:, 1] > 0.5
    zb = ctx["z_button"]
    acc = np.zeros(rs.K, np.float32)
    for x in (0.058, -0.058):
        for z in (zb - 0.015, zb - 0.085):
            d = np.hypot(P[:, 0] - x, P[:, 2] - z)
            acc = np.maximum(acc, 1 - M.smoothstep(0.0075, 0.0095, d))
    acc *= m & front
    btn = T.hexrgb("#1c1a19")
    col = T.mix(col, btn, acc * 0.95)
    rough = rough * (1 - acc) + 0.35 * acc
    return col, nts, rough, metal


def _loafer_strap(rs, part, col, nts, rough, metal, ctx):
    m = part == A.LOAFER
    P = rs.P
    acc = np.zeros(rs.K, np.float32)
    for s, ank in ctx["ankles"].items():
        side = (P[:, 0] > 0) if s == "l" else (P[:, 0] <= 0)
        band = np.exp(-((P[:, 1] - (ank[1] - 0.062)) / 0.007) ** 2) * (P[:, 2] > ctx["sole"] + 0.03)
        acc = np.maximum(acc, band * side)
    acc *= m
    col = T.mix(col, T.hexrgb(ctx["loafer_dark"]) * 1.3, acc * 0.8)
    return col, nts, rough, metal
