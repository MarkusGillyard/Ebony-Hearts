"""Reusable synthesis primitives: thumps, bubbles/splashes, whooshes, electric sparks, fire, bells."""
import math

import numpy as np

from . import dsp
from .dsp import SR, TAU, filt, ns, place, tvec


# ----------------------------------------------------------------------------- generic
def burst(rng, dur, attack, decay, stages=(), exponent=0.0):
    n = ns(dur)
    src = dsp.white(rng, n) if exponent == 0 else dsp.colored(rng, n, exponent)
    y = src * dsp.env_ad(n, attack, decay)
    return dsp.endfade(dsp.normalize(filt(y, list(stages))))


def thump(dur, f0, f1, sweep, decay, attack=0.0008, drive=1.0):
    """Pitch-dropping sine thump (kick/body/sub)."""
    n = ns(dur)
    t = tvec(n)
    f = f1 + (f0 - f1) * np.exp(-t / sweep)
    y = np.sin(TAU * np.cumsum(f) / SR) * dsp.env_ad(n, attack, decay)
    if drive > 1.0:
        y = dsp.softclip(y, drive)
    return dsp.endfade(y)


def hf_onset(x, fc=2000.0, rel_db=-12.0):
    """Sample index of the main high-frequency transient (where the 'crack' is)."""
    h = np.abs(filt(x, [("hp", fc, 4)]))
    k = ns(0.001)
    e = np.convolve(h, np.ones(k) / k, mode="same")
    idx = np.nonzero(e > e.max() * dsp.undb(rel_db))[0]
    return int(idx[0]) if idx.size else 0


def cut_at(x, idx, pre=0.003):
    """Start x shortly before idx with a raised-cosine fade over the pre-roll."""
    s = max(0, idx - ns(pre))
    y = x[s:].copy()
    k = idx - s
    if k > 1:
        y[:k] *= 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, k))
    return y


def room(x, ir, wet, tail=0.0):
    """Dry + wet early reflections (ir has unit energy). Output length len(x)+tail."""
    n = len(x) + ns(tail)
    y = dsp.fit(x, n)
    w = dsp.fftconv(x, ir)
    return y + wet * dsp.fit(w, n)


# ----------------------------------------------------------------------------- water
def bubble(f0, amp, rise=0.1, max_len=0.25):
    """Single resonating bubble (Minnaert-style damped sine with upward chirp)."""
    d = 0.13 * f0 + 0.0072 * f0 ** 1.5
    n = max(8, ns(min(6.5 / d, max_len)))
    t = tvec(n)
    f = f0 * (1.0 + rise * d * t)
    y = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-d * t)
    y *= np.clip(t / 0.0003, 0.0, 1.0)
    return amp * y


def drip(rng, f0, amp=1.0, plink=True, rise=1.0):
    """Water drop into a pool: tiny contact tick plus a strongly rising 'plink' bubble."""
    n = ns(0.12)
    y = np.zeros(n)
    tick = dsp.white(rng, ns(0.002)) * dsp.env_ad(ns(0.002), 0.0001, 0.0004)
    tick = filt(tick, [("hp", 1500, 2), ("lp", 9000, 2)])
    place(y, dsp.normalize(tick) * 0.25, 0)
    if plink:
        m = ns(0.09)
        t = tvec(m)
        tau = rng.uniform(0.012, 0.022)
        f = f0 * (1.0 + rise * rng.uniform(0.35, 0.8) * (1 - np.exp(-t / 0.018)))
        b = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-t / tau) * np.clip(t / 0.0004, 0, 1)
        place(y, b, ns(rng.uniform(0.0005, 0.002)))
    return amp * dsp.endfade(y)


def splash(rng, size, dur, bright=1.0):
    """Shallow-water splash. size ~0.15 (footstep) .. 1.0 (body slam)."""
    n = ns(dur)
    out = np.zeros(n)
    # 1. slap of the contact on the water surface
    s = burst(rng, 0.08, 0.0005, 0.004 + 0.012 * size,
              [("hp", 300, 2), ("peak", 900, 0.8, 3.0), ("lp", (2600 + 3800 * size) * bright, 2)])
    place(out, s * (0.55 + 0.35 * size), 0)
    # 2. liquid slosh: falling band of noise with granular amplitude modulation
    m = min(n, ns(0.1 + 0.6 * size))
    dec = 0.035 + 0.17 * size

    def g(t, f):
        tt = np.maximum(t, 0.0)
        e = dsp.smoothstep(tt / 0.006) * np.exp(-tt / dec)
        fc = (500 + 1300 * np.exp(-tt / 0.06)) * bright
        return e * (dsp.mag_bp(f, fc, 0.9) + 0.25 * dsp.mag_lp2(f, 350.0)) * dsp.mag_hp(f, 90, 2)

    sl = dsp.shaped_noise(rng, m, g, nfft=512, hop=128)
    am = np.clip(dsp.lfo_noise(rng, m, 45.0), -2.0, 2.0)
    sl *= 0.45 + 0.55 * np.abs(am) / 2.0
    place(out, dsp.normalize(sl) * (0.35 + 0.25 * size), 0)
    # 3. bubble cloud right after contact
    count = int(8 + 110 * size)
    fmin, fmax = 2300 - 1700 * size, 4800 - 1800 * size
    for _ in range(count):
        tb = rng.gamma(1.4, 0.012 + 0.05 * size)
        if tb >= dur - 0.02:
            continue
        f0 = math.exp(rng.uniform(math.log(fmin), math.log(fmax)))
        a = rng.uniform(0.04, 0.22) * (1000.0 / f0) ** 0.3 * math.exp(-tb / (0.08 + 0.25 * size))
        place(out, bubble(f0, a, rng.uniform(0.04, 0.25)), ns(tb))
    # 4. droplets falling back
    cnt = int(2 + 32 * size)
    for _ in range(cnt):
        td = 0.05 + rng.gamma(2.0, 0.04 + 0.11 * size)
        if td >= dur - 0.03:
            continue
        a = rng.uniform(0.02, 0.09) * (0.6 + 0.4 * size)
        place(out, drip(rng, rng.uniform(1800, 5200), a, plink=rng.uniform() < 0.35, rise=0.25), ns(td))
    # 5. spray hiss and low plop for bigger splashes
    if size > 0.35:
        sp = burst(rng, 0.4 * size + 0.1, 0.004, 0.06 + 0.1 * size, [("hp", 3500, 2), ("lp", 11000, 2)])
        place(out, sp * 0.12 * size, ns(0.004))
        place(out, thump(0.2, 140, 65, 0.02, 0.05) * 0.35 * size, 0)
    return out


# ----------------------------------------------------------------------------- air
def whoosh(rng, dur, peak_t, f_lo, f_hi, q=1.4, rise_pow=2.0, fall_tau=0.05, body=0.35,
           exponent=0.6, flutter=0.0, flutter_hz=60.0, nfft=512, hop=128):
    """Band-passed noise whose centre and level follow a limb-speed profile."""
    n = ns(dur)
    t = tvec(n)
    v = np.where(t < peak_t, (t / peak_t) ** rise_pow, np.exp(-(t - peak_t) / fall_tau))
    v = v * dsp.fade(np.ones(n), 0.0, min(0.03, dur * 0.2))

    def g(tt, f):
        vv = np.interp(tt, t, v)
        fc = f_lo + (f_hi - f_lo) * vv
        return vv ** 1.2 * (dsp.mag_bp(f, fc, q) + body * dsp.mag_lp2(f, fc * 0.55)) * dsp.mag_hp(f, 70, 2)

    y = dsp.shaped_noise(rng, n, g, exponent, nfft=nfft, hop=hop)
    if flutter > 0:
        fl = np.clip(dsp.lfo_noise(rng, n, flutter_hz), -2, 2) / 2
        y *= 1.0 + flutter * fl * v
    return y


def spin_whoosh(rng, dur, rate0, rate1, passes_peak, f_lo, f_hi, doppler=0.35, q=1.5):
    """Rotating whoosh: periodic passes with a Doppler-like pitch swing around each pass."""
    n = ns(dur)
    t = tvec(n)
    rate = rate0 + (rate1 - rate0) * (t / dur)
    phi = np.cumsum(rate) / SR
    p_at_peak = float(np.interp(passes_peak, t, phi))
    phi += math.ceil(p_at_peak) - p_at_peak  # a pass (closest approach) lands exactly at the peak
    swell = dsp.env_points(n, [(0, 0.0), (dur * 0.15, 0.35), (passes_peak * 0.85, 0.85),
                               (passes_peak, 1.0), (min(dur, passes_peak + 0.12), 0.25), (dur, 0.0)])
    close = 0.5 + 0.5 * np.cos(TAU * phi)
    radial = np.sin(TAU * phi)  # >0 approaching (before the pass) -> pitch up
    amp = swell * (0.1 + 0.9 * close ** 3)
    fc = (f_lo + (f_hi - f_lo) * swell) * (1.0 + doppler * radial) * (0.75 + 0.5 * close)

    def g(tt, f):
        a = np.interp(tt, t, amp)
        c = np.interp(tt, t, fc)
        return a * (dsp.mag_bp(f, c, q) + 0.3 * dsp.mag_lp2(f, c * 0.5)) * dsp.mag_hp(f, 70, 2)

    return dsp.shaped_noise(rng, n, g, 0.6, nfft=512, hop=128)


# ----------------------------------------------------------------------------- electric
def sparks(rng, dur, rate_fn, amp_fn, bright=1.0):
    """Crackle of electric sparks: clusters of micro-impulses at an inhomogeneous Poisson rate."""
    n = ns(dur)
    t = tvec(n)
    r = rate_fn(t)
    rmax = max(float(r.max()), 1e-6)
    cand = rng.uniform(0, dur, rng.poisson(rmax * dur))
    cand.sort()
    keep = cand[rng.uniform(0, 1, cand.size) < np.interp(cand, t, r) / rmax]
    y = np.zeros(n)
    for ti in keep:
        a0 = float(amp_fn(np.array([ti]))[0]) * rng.uniform(0.15, 1.0) ** 1.6
        for _ in range(int(rng.integers(1, 6))):
            pos = ns(ti + rng.uniform(0, 0.0014))
            if pos < n:
                y[pos] += a0 * rng.uniform(0.3, 1.0) * (1 if rng.uniform() < 0.5 else -1)
    y = filt(y, [("hp", 1100 * bright, 2), ("peak", 4200 * bright, 1.1, 6.0), ("lp", 15000, 2)])
    # short metallic sizzle ring on each spark
    ring = np.sin(TAU * 7300 * bright * tvec(ns(0.004))) * np.exp(-tvec(ns(0.004)) / 0.0008)
    y = y + 0.35 * dsp.fit(dsp.fftconv(y, ring), n)
    return y


def saw_table(nh, rolloff=0.0):
    k = np.arange(1, nh + 1)
    return dsp.wavetable(list((1.0 / k) * np.exp(-rolloff * k)))


def buzz(rng, dur, f_curve, amp_curve, jitter=0.03, grit=2.5):
    """Gritty electric hum/sizzle: jittered band-limited saw, saturated, flickering."""
    n = ns(dur)
    fj = f_curve * (1.0 + jitter * np.clip(dsp.lfo_noise(rng, n, 300.0), -3, 3))
    nh = int(9000 / float(np.max(f_curve)))
    y = dsp.wt_read(saw_table(max(nh, 4)), np.cumsum(fj) / SR)
    y = dsp.softclip(y * grit, 1.0)
    y = filt(y, [("hp", 160, 2), ("peak", 1900, 0.8, 4.0), ("lp", 7500, 2)])
    flick = 0.55 + 0.45 * np.clip(dsp.lfo_noise(rng, n, 38.0), -2.5, 2.5) / 2.5
    return y * amp_curve * flick


def zap(dur, f0, f1, tau, nh=40):
    """Descending electric zap (saw chirp)."""
    n = ns(dur)
    t = tvec(n)
    f = f1 + (f0 - f1) * np.exp(-t / tau)
    y = dsp.wt_read(saw_table(nh, 0.02), np.cumsum(f) / SR)
    y *= np.exp(-t / (tau * 1.8)) * np.clip(t / 0.0004, 0, 1)
    return dsp.endfade(filt(y, [("hp", 250, 2), ("lp", 12000, 2)]))


def shimmer(rng, dur, freqs, amp_curve, trem=7.0, glide=0.0, detune_cents=4.0):
    """Warm tonal shimmer: detuned sine pairs with tremolo and an optional pitch glide."""
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    gl = 1.0 + glide * (t / dur)
    for i, fq in enumerate(freqs):
        for s in (-1, 1):
            f = fq * 2 ** (s * detune_cents / 1200.0) * gl
            ph = rng.uniform(0, 1)
            tr = 0.72 + 0.28 * np.sin(TAU * (trem * (1 + 0.07 * i) * t + rng.uniform(0, 1)))
            y += (np.sin(TAU * (np.cumsum(f) / SR + ph)) + 0.12 * np.sin(TAU * (2 * np.cumsum(f) / SR + ph))) * tr
    return y / (2 * len(freqs)) * amp_curve


# ----------------------------------------------------------------------------- fire
def fire_roar(rng, dur, env_pts, fc_pts, turb=0.5, hiss=0.15):
    n = ns(dur)
    t = tvec(n)
    env = dsp.env_points(n, env_pts)
    fcs = dsp.env_points(n, fc_pts)

    def g(tt, f):
        e = np.interp(tt, t, env)
        fc = np.interp(tt, t, fcs)
        return e * (dsp.mag_lp2(f, fc, 0.9) + hiss * dsp.mag_bp(f, 3200, 0.7)) * dsp.mag_hp(f, 35, 2)

    y = dsp.shaped_noise(rng, n, g, 0.8)
    m1 = 1.0 + turb * np.clip(dsp.lfo_noise(rng, n, 13.0), -2, 2) / 2
    m2 = 1.0 + 0.5 * turb * np.clip(dsp.lfo_noise(rng, n, 40.0), -2, 2) / 2
    return y * m1 * m2


def crackle(rng, dur, rate_fn, amp_fn):
    """Fire crackle: irregular short pops, some with a low 'pock'."""
    n = ns(dur)
    t = tvec(n)
    r = rate_fn(t)
    rmax = max(float(r.max()), 1e-6)
    cand = np.sort(rng.uniform(0, dur, rng.poisson(rmax * dur)))
    keep = cand[rng.uniform(0, 1, cand.size) < np.interp(cand, t, r) / rmax]
    y = np.zeros(n)
    for ti in keep:
        a = float(amp_fn(np.array([ti]))[0]) * rng.uniform(0.1, 1.0) ** 2
        m = ns(rng.uniform(0.0006, 0.0035))
        p = dsp.white(rng, m) * np.exp(-tvec(m) / (m / SR / 3))
        place(y, p * a, ns(ti))
        if rng.uniform() < 0.25:
            place(y, thump(0.008, rng.uniform(500, 900), 300, 0.003, 0.002) * a * 0.6, ns(ti))
    return filt(y, [("hp", 600, 2), ("peak", 2600, 0.8, 4.0), ("lp", 9500, 2)])


# ----------------------------------------------------------------------------- tonal
def bell(dur, f_nominal, rng, strike=0.4, decay_scale=1.0, partials=None):
    """Church-bell modal model (ratios relative to the nominal / strike note)."""
    if partials is None:
        partials = [  # ratio, amp, tau(s)
            (0.25, 0.55, 1.15), (0.5, 0.60, 0.95), (0.6, 0.55, 0.75), (0.75, 0.25, 0.55),
            (1.0, 0.80, 0.60), (1.25, 0.30, 0.42), (1.5, 0.25, 0.32), (2.0, 0.20, 0.24),
            (2.5, 0.12, 0.17), (2.66, 0.10, 0.15), (3.2, 0.08, 0.11), (4.1, 0.05, 0.08),
        ]
    n = ns(dur)
    y = dsp.modal(n, [(f_nominal * r, a, tau * decay_scale) for r, a, tau in partials], attack=0.0006,
                  rng=rng, doublet=0.9)
    hit = burst(rng, 0.05, 0.0002, 0.004, [("hp", 900, 2), ("peak", 3500, 0.9, 4.0), ("lp", 9000, 2)])
    clank = dsp.modal(ns(0.15), [(f_nominal * r, 0.3, 0.025) for r in (5.3, 6.9, 8.4, 10.7)], rng=rng)
    place(y, hit * strike, 0)
    place(y, clank * strike * 0.6, 0)
    return y


def taiko(rng, dur, f0, decay=0.35, slap=0.25, drop=0.25, beater=0.4):
    """Synthesised large drum: membrane modes with a tension pitch drop, beater and skin slap."""
    n = ns(dur)
    t = tvec(n)
    ratios = [(1.0, 1.0, 1.0), (1.594, 0.45, 0.55), (2.136, 0.3, 0.4), (2.296, 0.22, 0.35),
              (2.653, 0.15, 0.28), (2.918, 0.1, 0.22), (3.156, 0.08, 0.18)]
    bend = 1.0 + drop * np.exp(-t / 0.035)
    y = np.zeros(n)
    for r, a, dmul in ratios:
        f = f0 * r * bend
        y += a * np.sin(TAU * (np.cumsum(f) / SR + rng.uniform(0, 0.02))) * np.exp(-t / (decay * dmul))
    y *= np.clip(t / 0.0015, 0, 1)
    b = burst(rng, 0.03, 0.0003, 0.003, [("lp", 1600, 2), ("hp", 60, 2)])
    s = burst(rng, 0.06, 0.0004, 0.012, [("hp", 280, 2), ("lp", 1400, 2)])
    place(y, b * beater, 0)
    place(y, s * slap, 0)
    return dsp.endfade(dsp.softclip(y * 0.8, 1.3), max_s=0.08)
