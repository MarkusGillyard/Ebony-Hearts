"""Finishing (fades, DC, normalisation, limiting) and 16-bit WAV I/O."""
import math
import wave

import numpy as np

from . import dsp
from .dsp import SR, ns

ONESHOT_TP_DB = -1.0


def finish_oneshot(x, dur=None, pre=0.002, fade_in=0.002, fade_out=0.005, hp=22.0):
    """Mono one-shot: 2 ms pre-roll, DC/subsonic high-pass, raised-cosine fades, -1 dBTP peak."""
    x = np.concatenate([np.zeros(ns(pre)), np.asarray(x, dtype=np.float64)])
    if dur is not None:
        x = dsp.fit(x, ns(dur))
    x = dsp.filt(x, [("hp", hp, 2)])
    w = dsp.fade(np.ones(len(x)), fade_in, max(fade_out, 0.002))
    x = x * w
    x = x - (np.mean(x) / np.mean(w)) * w  # remove DC exactly, shaped like the fades (ends stay 0)
    tp = dsp.true_peak(x)
    return x * (dsp.undb(ONESHOT_TP_DB) / tp)


def finish_ui(trans, body, dur=None, target_lufs_m=-20.0, fade_out=0.005, g_range=(0.05, 6.0)):
    """UI one-shot: peak-normalised to -1 dBTP like every one-shot, AND loudness-matched to
    -20 LUFS (momentary max) by solving the body-layer gain (crest factor) by bisection.
    Returns (signal, momentary loudness, body gain)."""
    n = max(len(trans), len(body))
    trans, body = dsp.fit(trans, n), dsp.fit(body, n)

    def render(g):
        y = finish_oneshot(trans + g * body, dur, fade_out=fade_out)
        return y, dsp.loudness_momentary_max(y)

    lo, hi = math.log(g_range[0]), math.log(g_range[1])
    y, l = render(math.exp(hi))
    if l < target_lufs_m:
        return y, l, math.exp(hi)
    y, l = render(math.exp(lo))
    if l > target_lufs_m:
        return y, l, math.exp(lo)
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        y, l = render(math.exp(mid))
        if abs(l - target_lufs_m) < 0.05:
            break
        if l < target_lufs_m:
            lo = mid
        else:
            hi = mid
    return y, l, math.exp(mid)


def finish_loop(x, target_lufs, ceiling_db=-1.0, hp=24.0, max_side_ratio=0.5):
    """Stereo seamless loop (periodic signal): circular DC/subsonic HP, side-level safety for mono
    compatibility, loudness normalisation (gated BS.1770 on the circular signal), circular
    look-ahead limiting to the true-peak ceiling. Returns (signal, info dict)."""
    x = dsp.filt(x, [("hp", hp, 2)], circular=True)
    x = x - np.mean(x, axis=0)
    mid = 0.5 * (x[:, 0] + x[:, 1])
    side = 0.5 * (x[:, 0] - x[:, 1])
    pm, ps = np.mean(mid ** 2), np.mean(side ** 2)
    side_scale = 1.0
    if ps > max_side_ratio * pm:
        side_scale = math.sqrt(max_side_ratio * pm / ps)
        side = side * side_scale
        x = np.stack([mid + side, mid - side], axis=1)
    info = {"side_scale_db": float(dsp.db(side_scale))}
    lufs = dsp.loudness_integrated(x, circular=True)
    x = x * dsp.undb(target_lufs - lufs)
    ceiling = dsp.undb(ceiling_db)
    gr_total = 0.0
    c = ceiling * 0.98
    for _ in range(8):
        if dsp.true_peak(x, circular=True) <= ceiling * 0.999:
            break
        x, gr = dsp.limit(x, c, circular=True)  # sample-peak limiting; tighten until true peak fits
        gr_total = max(gr_total, gr)
        c *= 0.97
    info["limiter_gr_db"] = gr_total
    return x, info


def write_wav(path, x, seed_name):
    """16-bit PCM, 48 kHz, TPDF dither (seeded; tapered to zero over the first/last 5 ms)."""
    x = np.asarray(x, dtype=np.float64)
    ch = 1 if x.ndim == 1 else x.shape[1]
    rng = dsp.rng_for("dither:" + seed_name)
    d = (rng.uniform(-0.5, 0.5, x.shape) + rng.uniform(-0.5, 0.5, x.shape))
    taper = np.ones(len(x))
    k = min(ns(0.005), len(x) // 2)
    if k > 0:
        ramp = np.linspace(0.0, 1.0, k)
        taper[:k] = ramp
        taper[-k:] = ramp[::-1]
    d *= taper if x.ndim == 1 else taper[:, None]
    q = np.clip(np.round(x * 32768.0 + d), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(q.tobytes())


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        assert sw == 2
        data = np.frombuffer(w.readframes(n), dtype="<i2").astype(np.float64) / 32768.0
    data = data.reshape(-1, ch)
    return (data[:, 0] if ch == 1 else data), sr
