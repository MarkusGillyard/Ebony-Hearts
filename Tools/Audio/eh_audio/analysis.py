"""Measurements (peak, RMS, loudness, DC, mono drop, loop seams) and PNG spectrograms (no PIL)."""
import math
import struct
import zlib

import numpy as np

from . import dsp
from .dsp import SR, ns


# ----------------------------------------------------------------------------- measurements
def measure(x, loop=False, grid=None):
    st = x if x.ndim == 2 else x[:, None]
    n = len(st)
    m = {
        "duration": n / SR,
        "channels": st.shape[1],
        "sample_peak_db": float(dsp.db(np.max(np.abs(st)))),
        "true_peak_db": float(dsp.db(dsp.true_peak(x, circular=loop))),
        "rms_db": float(dsp.db(np.sqrt(np.mean(st ** 2)))),
        "dc": float(np.max(np.abs(np.mean(st, axis=0)))),
        "mono_drop_db": dsp.mono_drop_db(x) if x.ndim == 2 else None,
        "first_sample": float(np.max(np.abs(st[0]))),
        "last_sample": float(np.max(np.abs(st[-1]))),
        "edge_rms_db": float(dsp.db(max(dsp.rms(st[:ns(0.002)]), dsp.rms(st[-ns(0.002):])))),
    }
    if loop:
        m["lufs"] = dsp.loudness_integrated(x, circular=True)
        m.update(loop_check(x, grid))
    else:
        m["lufs_m_max"] = dsp.loudness_momentary_max(x)
        # RMS over the active part (samples within 40 dB of the 10 ms-envelope peak)
        k = ns(0.01)
        e = np.sqrt(np.convolve(np.mean(st ** 2, axis=1), np.ones(k) / k, mode="same"))
        act = e > e.max() * 0.01
        m["active_rms_db"] = float(dsp.db(np.sqrt(np.mean(st[act] ** 2))))
    return m


def _logspec(frame):
    w = np.hanning(len(frame))
    X = np.abs(np.fft.rfft(frame * w[:, None], axis=0)).sum(axis=1) if frame.ndim == 2 else \
        np.abs(np.fft.rfft(frame * w))
    return 20 * np.log10(X + 1e-9)


def loop_check(x, grid=None):
    """Seam analysis for a seamless loop (signal end flows into its start).

    Reference positions are random in-file points; for music, `grid` (sample positions of the other
    bar downbeats) gives a like-for-like reference, since the loop point is itself a downbeat."""
    st = x if x.ndim == 2 else x[:, None]
    n = len(st)
    d = np.abs(np.diff(st, axis=0))
    seam = np.abs(st[0] - st[-1])
    p999 = np.percentile(d, 99.9, axis=0)
    med = np.median(d, axis=0)
    # second difference (curvature) at the seam vs. typical
    dd = np.abs(st[2:] - 2 * st[1:-1] + st[:-2])
    seam2 = np.abs(st[1] - 2 * st[0] + st[-1])
    # spectral flux across the seam vs. flux at 400 evenly spaced in-file positions
    N = 2048
    hop = 512

    def flux_at(pos):
        idx = (np.arange(pos - N - hop // 2, pos + N) % n)
        seg = st[idx]
        a = _logspec(seg[:N])
        b = _logspec(seg[hop:hop + N])
        band = slice(4, int(16000 / (SR / N)))
        return float(np.sqrt(np.mean((a[band] - b[band]) ** 2)))

    seam_flux = flux_at(0)
    rng = np.random.default_rng(12345)
    pos = rng.integers(N * 2, n - N * 2, 400)
    flux = np.array([flux_at(int(p)) for p in pos])
    # log-spectral distance between the last and first 0.5 s vs. adjacent 0.5 s windows in-file
    W = ns(0.5)

    def lsd(a, b):
        return float(np.sqrt(np.mean((_logspec(a)[4:2000] - _logspec(b)[4:2000]) ** 2)))

    seam_lsd = lsd(st[-W:], st[:W])
    ref = [lsd(st[p - W:p], st[p:p + W]) for p in rng.integers(W, n - W, 60)]
    out = {}
    if grid is not None and len(grid):
        g = np.asarray(grid, dtype=int)
        w5 = ns(0.005)

        def win_step(p):  # largest sample step within +-5 ms of position p (wrapping)
            idx = np.arange(p - w5, p + w5 + 1) % n
            return float(np.max(np.abs(np.diff(st[idx], axis=0))))

        gstep = np.array([win_step(int(p)) for p in g])
        seam_win = win_step(0)
        gflux = np.array([flux_at(int(p)) for p in g])
        glsd = np.array([lsd(st[p - W:p], st[p:p + W]) for p in g])
        out = {
            "grid_n": int(len(g)),
            "seam_win_step_vs_grid_median": float(seam_win / max(np.median(gstep), 1e-12)),
            "seam_flux_grid_pct": float((gflux < seam_flux).mean() * 100),
            "grid_flux_median_db": float(np.median(gflux)),
            "grid_lsd_median_db": float(np.median(glsd)),
        }
    return {
        **out,
        "seam_step": float(seam.max()),
        "seam_step_vs_p999": float(np.max(seam / np.maximum(p999, 1e-12))),
        "seam_step_vs_median": float(np.max(seam / np.maximum(med, 1e-12))),
        "seam_curv_vs_p999": float(np.max(seam2 / np.maximum(np.percentile(dd, 99.9, axis=0), 1e-12))),
        "seam_flux_db": seam_flux,
        "seam_flux_pct": float((flux < seam_flux).mean() * 100),
        "seam_lsd_db": seam_lsd,
        "ref_lsd_median_db": float(np.median(ref)),
    }


# ----------------------------------------------------------------------------- PNG
def write_png(path, rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].astype(np.uint8).tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


_FONT = {  # 3x5 glyphs
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
    "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001010010010",
    "8": "111101111101111", "9": "111101111001111", "k": "100101110101101", "s": "000011010001110",
    ".": "000000000000010", "-": "000000111000000", "d": "001001111101111", "B": "110101110101110",
    "H": "101101111101101", "z": "000111001010111", " ": "000000000000000",
}


def _text(img, x, y, s, color, scale=2):
    for ch in s:
        g = _FONT.get(ch, _FONT[" "])
        for i in range(5):
            for j in range(3):
                if g[i * 3 + j] == "1":
                    img[y + i * scale:y + (i + 1) * scale, x + j * scale:x + (j + 1) * scale] = color
        x += 4 * scale


_CMAP = np.array([(0, 0, 4), (40, 11, 84), (101, 21, 110), (159, 42, 99), (212, 72, 66),
                  (245, 125, 21), (250, 193, 39), (252, 255, 164)], dtype=np.float64)


def _colormap(v):
    v = np.clip(v, 0, 1) * (len(_CMAP) - 1)
    i = np.minimum(np.floor(v).astype(int), len(_CMAP) - 2)
    f = (v - i)[..., None]
    return _CMAP[i] * (1 - f) + _CMAP[i + 1] * f


def spectrogram_png(path, x, seconds=None, width=1200, height=420, wave_h=110, fmin=20.0, fmax=24000.0,
                    floor_db=-110.0):
    """Log-frequency spectrogram (mono mix) with a waveform/peak strip; red marks samples >= -0.1 dBFS."""
    st = x if x.ndim == 2 else x[:, None]
    if seconds:
        st = st[:ns(seconds)]
    mono = st.mean(axis=1)
    n = len(mono)
    dur = n / SR
    centers = np.linspace(0, n, width, endpoint=False) + n / width / 2
    rows = np.geomspace(fmax, fmin, height)
    edges = np.geomspace(fmax * 1.0035, fmin / 1.0035, height + 1)
    img_spec = np.empty((height, width))
    # multi-resolution: long window below 300 Hz (frequency detail), short above (transient detail)
    short_n = 1024 if dur < 3.0 else 2048
    for N, band in ((4096, (0.0, 300.0)), (short_n, (300.0, 1e9))):
        win = np.hanning(N)
        pad = np.concatenate([np.zeros(N), mono, np.zeros(N)])
        idx = (centers.astype(int)[:, None] + np.arange(N)[None, :] + N // 2)
        S = np.abs(np.fft.rfft(pad[idx] * win, axis=1)) * 2 / win.sum()
        S = 20 * np.log10(S + 1e-12)
        freqs = np.fft.rfftfreq(N, 1 / SR)
        for r in range(height):
            if not (band[0] <= rows[r] < band[1]):
                continue
            hi, lo = edges[r], edges[r + 1]
            sel = (freqs >= lo) & (freqs < hi)
            if sel.sum() >= 1:
                img_spec[r] = S[:, sel].max(axis=1)
            else:  # band narrower than one bin: interpolate between bins
                kf = rows[r] / (SR / N)
                k0 = int(math.floor(kf))
                fr = kf - k0
                img_spec[r] = S[:, k0] * (1 - fr) + S[:, k0 + 1] * fr
    col = _colormap((img_spec - floor_db) / (0 - floor_db))
    left, top_pad, bottom = 52, 6, 22
    H = top_pad + wave_h + 6 + height + bottom
    W = left + width + 8
    img = np.full((H, W, 3), 18.0)
    y0 = top_pad + wave_h + 6
    img[y0:y0 + height, left:left + width] = col
    # frequency grid
    for fq, lab in ((50, "50"), (100, "100"), (200, "200"), (500, "500"), (1000, "1k"), (2000, "2k"),
                    (5000, "5k"), (10000, "10k"), (20000, "20k")):
        r = int(round((math.log(fmax) - math.log(fq)) / (math.log(fmax) - math.log(fmin)) * (height - 1)))
        img[y0 + r, left:left + width:4] = (150, 150, 150)
        _text(img, 4, y0 + r - 5, lab, (200, 200, 200))
    # waveform strip: per-column min/max with -1 dBFS guide lines and clip marks
    wv = np.full((wave_h, width, 3), 28.0)
    mid = wave_h // 2
    ed = np.linspace(0, n, width + 1).astype(int)
    for cidx in range(width):
        seg = st[ed[cidx]:max(ed[cidx + 1], ed[cidx] + 1)]
        if seg.size == 0:
            continue
        lo, hi = seg.min(), seg.max()
        a = int(round(mid - hi * (mid - 2)))
        b = int(round(mid - lo * (mid - 2)))
        clip = np.max(np.abs(seg)) >= 0.989
        wv[max(a, 0):min(b + 1, wave_h), cidx] = (230, 60, 60) if clip else (120, 190, 230)
    g = int(round((mid - 2) * dsp.undb(-1.0)))
    wv[mid - g, ::3] = (90, 90, 90)
    wv[mid + g, ::3] = (90, 90, 90)
    wv[mid, :] = (60, 60, 60)
    img[top_pad:top_pad + wave_h, left:left + width] = wv
    # time ticks
    step = 0.1 if dur <= 1.5 else 0.5 if dur <= 4 else 1 if dur <= 12 else 5
    tt = 0.0
    while tt <= dur + 1e-9:
        cx = left + int(round(tt / dur * (width - 1)))
        img[y0 + height:y0 + height + 4, cx] = (200, 200, 200)
        lab = (f"{tt:.1f}" if step < 1 else f"{int(round(tt))}") + "s"
        _text(img, min(cx + 2, W - 30), y0 + height + 6, lab, (200, 200, 200))
        tt += step
    img = np.clip(img, 0, 255).astype(np.uint8)
    if path:
        write_png(path, img)
    return img
