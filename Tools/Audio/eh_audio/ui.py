"""Menu / pause UI one-shots.

Each builder returns (transient_layer, body_layer, duration_s, fade_out_s). The finisher scales the
body layer so the result peaks at -1 dBTP AND sits at -20 LUFS momentary loudness.
"""
import numpy as np

from . import dsp
from .dsp import filt, ns, place, tvec
from .synth import burst


def mallet(f, dur, tau=0.3, bright=1.0, rng=None):
    """Soft mallet/glass tone used across the UI (warm, slightly inharmonic)."""
    return dsp.modal(ns(dur), [(f, 1.0, tau), (f * 2.0, 0.22 * bright, tau * 0.5),
                               (f * 3.01, 0.08 * bright, tau * 0.3), (f * 4.17, 0.04 * bright, tau * 0.2)],
                     attack=0.0015, rng=rng)


def felt(rng, lp=3000.0, dur=0.006):
    """Soft felt-mallet contact click (the transient layer)."""
    return burst(rng, dur, 0.0002, dur / 5, [("lp", lp, 2), ("hp", 250, 2)])


def ui_move(c):
    rng = dsp.rng_for("UiMove")
    n = ns(0.12)
    tr, body = np.zeros(n), np.zeros(n)
    place(tr, felt(rng, 6000, 0.004) * 0.5, 0)
    k = c.kload("click_002", "UiMove", pitch=0.9, stages=[("lp", 5000, 2), ("hp", 200, 2)])
    place(tr, k * 0.6, 0)
    tock = dsp.modal(ns(0.1), [(1350, 1.0, 0.022), (1350 * 2.9, 0.25, 0.007)], attack=0.0004, rng=rng)
    place(body, tock, 0)
    return tr, body, 0.1, 0.02


def ui_confirm(c):
    rng = dsp.rng_for("UiConfirm")
    n = ns(0.7)
    tr, body = np.zeros(n), np.zeros(n)
    place(tr, felt(rng, 3500) * 0.8, 0)
    place(tr, felt(rng, 3500) * 0.9, ns(0.075))
    k = c.kload("select_002", "UiConfirm", pitch=0.85, stages=[("lp", 4500, 2), ("hp", 300, 2)])
    place(tr, k * 0.5, 0)
    place(body, mallet(440.0, 0.6, 0.16, rng=rng) * 0.8, 0)
    place(body, mallet(587.33, 0.55, 0.2, rng=rng), ns(0.075))
    place(body, mallet(880.0, 0.4, 0.12, 0.5, rng=rng) * 0.2, ns(0.075))
    return filt(tr, [("lp", 5000, 2)]), filt(body, [("lp", 5000, 2)]), 0.55, 0.15


def ui_back(c):
    rng = dsp.rng_for("UiBack")
    n = ns(0.16)
    tr, body = np.zeros(n), np.zeros(n)
    place(tr, felt(rng, 2500, 0.006) * 0.6, 0)
    k = c.kload("back_002", "UiBack", pitch=0.85, stages=[("lp", 3000, 2), ("hp", 150, 2)])
    place(tr, k * 0.6, 0)
    m = ns(0.12)
    t = tvec(m)
    f = 520 - 60 * (1 - np.exp(-t / 0.02))
    tone = np.sin(2 * np.pi * np.cumsum(f) / dsp.SR) * dsp.env_ad(m, 0.0008, 0.026)
    place(body, dsp.endfade(tone), 0)
    return tr, body, 0.14, 0.03


def ui_open(c):
    rng = dsp.rng_for("UiOpen")
    dur = 0.65
    n = ns(0.8)
    tr, body = np.zeros(n), np.zeros(n)
    t_ch = 0.27
    tt = tvec(n)

    def g(t, f):
        e = dsp.smoothstep(t / t_ch) * np.exp(-np.maximum(t - t_ch, 0) / 0.06)
        fc = 500 + 2000 * dsp.smoothstep(t / t_ch)
        return e * dsp.mag_bp(f, fc, 1.2)

    body += dsp.normalize(dsp.shaped_noise(rng, n, g, 0.5)) * 0.25
    pad_env = dsp.smoothstep(tt / t_ch) * np.exp(-np.maximum(tt - t_ch, 0) / 0.1)
    pad = sum(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6)) for f in (293.66, 440.0, 587.33)) / 3
    body += pad * pad_env * 0.25
    place(body, mallet(587.33, 0.5, 0.18, 0.8, rng=rng) * 0.6, ns(t_ch))
    place(body, mallet(880.0, 0.4, 0.14, 0.5, rng=rng) * 0.2, ns(t_ch + 0.004))
    place(tr, felt(rng, 4000) * 0.9, ns(t_ch))
    k = c.kload("open_002", "UiOpen", stages=[("lp", 3500, 2), ("hp", 400, 2)], trim_db=None)
    place(body, k * 0.07, ns(t_ch) - len(k))
    return filt(tr, [("lp", 6000, 2)]), filt(body, [("lp", 6000, 2)]), dur, 0.12


def ui_close(c):
    rng = dsp.rng_for("UiClose")
    dur = 0.42
    n = ns(0.55)
    tr, body = np.zeros(n), np.zeros(n)
    place(tr, felt(rng, 3500) * 0.9, 0)
    place(tr, felt(rng, 2500) * 0.6, ns(0.07))
    place(body, mallet(440.0, 0.35, 0.12, 0.7, rng=rng) * 0.85, 0)
    place(body, mallet(293.66, 0.4, 0.15, 0.6, rng=rng) * 0.6, ns(0.07))

    def g(t, f):
        e = dsp.smoothstep(t / 0.02) * np.exp(-np.maximum(t, 0) / 0.09)
        fc = 2200 * np.exp(-np.maximum(t, 0) / 0.12) + 400
        return e * dsp.mag_bp(f, fc, 1.1)

    body += dsp.normalize(dsp.shaped_noise(rng, n, g, 0.5)) * 0.15
    k = c.kload("close_002", "UiClose", pitch=0.8, stages=[("lp", 3000, 2), ("hp", 300, 2)])
    place(body, k * 0.07, 0)
    return filt(tr, [("lp", 5500, 2)]), filt(body, [("lp", 5500, 2)]), dur, 0.1


def ui_lock(c):
    """Locking in a fighter: a low, round chord with a slow bloom under it (heavier than a confirm)."""
    rng = dsp.rng_for("UiLock")
    dur = 0.8
    n = ns(0.95)
    tr, body = np.zeros(n), np.zeros(n)
    place(tr, felt(rng, 2500, 0.008) * 0.9, 0)
    place(body, mallet(293.66, 0.75, 0.24, 0.7, rng=rng) * 0.8, 0)
    place(body, mallet(440.0, 0.7, 0.2, 0.6, rng=rng) * 0.55, ns(0.012))
    place(body, mallet(587.33, 0.6, 0.16, 0.4, rng=rng) * 0.3, ns(0.024))
    tt = tvec(n)
    bloom = np.sin(2 * np.pi * 146.83 * tt) * dsp.smoothstep(tt / 0.05) * np.exp(-tt / 0.28)
    body += bloom * 0.18
    return filt(tr, [("lp", 4000, 2)]), filt(body, [("lp", 4200, 2)]), dur, 0.16


def ui_denied(c):
    """Something that cannot be done: a short, dull knock, lower and drier than a move."""
    rng = dsp.rng_for("UiDenied")
    n = ns(0.2)
    tr, body = np.zeros(n), np.zeros(n)
    place(tr, felt(rng, 1500, 0.008) * 0.8, 0)
    place(body, mallet(196.0, 0.16, 0.05, 0.25, rng=rng), 0)
    place(body, mallet(185.0, 0.14, 0.045, 0.2, rng=rng) * 0.6, ns(0.006))
    return filt(tr, [("lp", 2200, 2)]), filt(body, [("lp", 2000, 2)]), 0.16, 0.04


def ui_apply(c):
    """Applying settings: three rising mallet notes, quick and bright."""
    rng = dsp.rng_for("UiApply")
    dur = 0.7
    n = ns(0.85)
    tr, body = np.zeros(n), np.zeros(n)
    for i, (f, amp) in enumerate(((440.0, 0.7), (587.33, 0.8), (880.0, 0.6))):
        at = ns(0.06 * i)
        place(tr, felt(rng, 4000) * 0.6, at)
        place(body, mallet(f, 0.5, 0.15, 0.7, rng=rng) * amp, at)
    return filt(tr, [("lp", 5500, 2)]), filt(body, [("lp", 5500, 2)]), dur, 0.15


def ui_warn(c):
    """A warning (a controller lost, a display change about to revert): two low, close notes."""
    rng = dsp.rng_for("UiWarn")
    dur = 0.45
    n = ns(0.6)
    tr, body = np.zeros(n), np.zeros(n)
    place(tr, felt(rng, 2500) * 0.8, 0)
    place(tr, felt(rng, 2500) * 0.8, ns(0.14))
    place(body, mallet(220.0, 0.3, 0.1, 0.5, rng=rng) * 0.9, 0)
    place(body, mallet(207.65, 0.32, 0.12, 0.5, rng=rng) * 0.9, ns(0.14))
    return filt(tr, [("lp", 3500, 2)]), filt(body, [("lp", 3500, 2)]), dur, 0.12


def builders():
    return [("UiMove", ui_move), ("UiConfirm", ui_confirm), ("UiBack", ui_back),
            ("UiOpen", ui_open), ("UiClose", ui_close), ("UiLock", ui_lock), ("UiDenied", ui_denied),
            ("UiApply", ui_apply), ("UiWarn", ui_warn)]
