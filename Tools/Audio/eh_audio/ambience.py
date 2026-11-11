"""The Drowned Chapel ambience bed (stereo, seamless loop).

Loop construction
- Continuous textures (room tone, wind) are rendered LOOP + XFADE long and folded with an internal
  equal-power crossfade: the last XFADE seconds are faded into the first XFADE seconds, so the
  final sample flows into sample 0.
- Discrete events (drips, lapping, censer creaks) are scheduled on a circle: an event near the
  end wraps its tail into the start, and periodic drip sources keep their period across the seam.
- The stone-room reverb is a circular convolution, so tails crossing the loop point wrap too.
"""
import math

import numpy as np

from . import dsp, synth
from .dsp import filt, ns, place_circ, tvec

LOOP = 72.0
XFADE = 4.0
CHAPEL_EARLY = [(0.021, 0.18), (0.031, 0.15), (0.043, 0.14), (0.058, 0.12), (0.074, 0.1), (0.095, 0.08),
                (0.12, 0.06)]


def loop_crossfade(x, n, xf):
    """x has n + xf samples; fold the overrun into the head with an equal-power crossfade."""
    a = np.linspace(0.0, 1.0, xf)
    w_in = np.sin(0.5 * math.pi * a)
    w_out = np.cos(0.5 * math.pi * a)
    y = x[:n].copy()
    if x.ndim == 2:
        w_in, w_out = w_in[:, None], w_out[:, None]
    y[:xf] = x[:xf] * w_in + x[n:n + xf] * w_out
    return y


def circular_times(rng, total, period, jitter):
    """Quasi-periodic event times on a circle of length total (period preserved across the seam)."""
    k = max(1, int(round(total / period)))
    base = (np.arange(k) + 0.5) * total / k
    return np.sort((base + rng.uniform(-jitter, jitter, k)) % total)


def circular_poisson(rng, total, mean_gap, min_gap):
    """Poisson-like event times on a circle: gaps are rescaled to sum to exactly `total`, so the
    gap across the loop seam is just another gap from the same distribution."""
    gaps = []
    while sum(gaps) < total:
        gaps.append(min_gap + rng.exponential(mean_gap - min_gap))
    gaps = np.array(gaps)
    gaps *= total / gaps.sum()
    return np.sort((np.cumsum(gaps) + rng.uniform(0, total)) % total)


def chain_creak(rng, dur=0.9, pitch=1.0):
    """Censer chain under load: stick-slip pulse train exciting metal link resonances."""
    n = ns(dur)
    t = tvec(n)
    rate = (38 + 32 * np.sin(math.pi * t / dur)) * (1 + 0.15 * np.clip(dsp.lfo_noise(rng, n, 25), -2, 2))
    ph = np.cumsum(rate) / dsp.SR
    idx = np.nonzero(np.diff(np.floor(ph)) > 0)[0]
    exc = np.zeros(n)
    env = np.sin(math.pi * t / dur) ** 1.5
    exc[idx] = env[idx] * rng.uniform(0.4, 1.0, idx.size)
    modes = [(1150 * pitch, 1.0, 0.012), (1870 * pitch, 0.7, 0.009), (2930 * pitch, 0.5, 0.007),
             (4410 * pitch, 0.3, 0.005), (430 * pitch, 0.6, 0.02)]
    ir = dsp.modal(ns(0.06), modes, rng=rng)
    y = dsp.fit(dsp.fftconv(exc, ir), n)
    for _ in range(int(rng.integers(1, 3))):  # a link or two settling after the swing
        clink = dsp.modal(ns(0.12), [(3200 * pitch, 1.0, 0.03), (5100 * pitch, 0.6, 0.02),
                                     (7400 * pitch, 0.3, 0.012)], rng=rng)
        tt = ns(rng.uniform(0.55, 0.85) * dur)
        dsp.place(y, clink * rng.uniform(0.15, 0.3) * dsp.peak(y), tt)
    return dsp.endfade(y)


def chapel_bed(c):
    rng = dsp.rng_for("ChapelBed")
    n = ns(LOOP)
    xf = ns(XFADE)
    m = n + xf
    t = tvec(m)

    # ---------------- textures: room tone + distant wind (crossfade-looped)
    common = dsp.colored(rng, m, 1.7)
    tone = np.stack([0.75 * common + 0.66 * dsp.colored(rng, m, 1.7),
                     0.75 * common + 0.66 * dsp.colored(rng, m, 1.7)], axis=1)
    tone = filt(tone, [("hp", 28, 2), ("lp", 420, 2), ("peak", 95, 0.9, 3.0)])
    tone *= (1.0 + 0.12 * np.clip(dsp.lfo_noise(rng, m, 0.06), -2.5, 2.5))[:, None]
    tone = tone / dsp.rms(tone) * dsp.undb(-42)

    lf1 = np.clip(dsp.lfo_noise(rng, m, 0.07), -2.5, 2.5) / 2.5
    lf2 = np.clip(dsp.lfo_noise(rng, m, 0.04), -2.5, 2.5) / 2.5
    lf3 = np.clip(dsp.lfo_noise(rng, m, 0.025), -2.5, 2.5) / 2.5
    gust = np.clip(0.42 + 0.58 * lf1, 0.04, 1.0) ** 2.0
    fcw = 300 + 140 * lf2
    fwh = 640 + 110 * lf3
    wind = []
    for ch, lag in ((0, 0.0), (1, 0.9)):
        g_t = np.interp(t - lag, t, gust, period=t[-1])

        def g(tt, f, g_t=g_t):
            gg = np.interp(tt, t, g_t)
            fc = np.interp(tt, t, fcw)
            fw = np.interp(tt, t, fwh) * (1.0 + 0.04 * ch)
            return (gg * dsp.mag_bp(f, fc, 0.75) + 0.2 * gg ** 2 * dsp.mag_bp(f, fw, 16.0)) * dsp.mag_hp(f, 60, 2)

        wind.append(dsp.shaped_noise(rng, m, g, 0.5, nfft=2048, hop=512))
    wind = np.stack(wind, axis=1)
    wind = 0.65 * wind + 0.35 * wind.mean(axis=1, keepdims=True)  # partly shared: keeps mono-safe
    wind = filt(wind, [("lp", 1800, 2)])
    wind = wind / dsp.rms(wind) * dsp.undb(-34)

    textures = loop_crossfade(tone + wind, n, xf)
    wind_send = loop_crossfade(wind, n, xf)

    # ---------------- events on the loop circle (dry, stereo)
    events = np.zeros((n, 2))
    sends = np.zeros((n, 2))

    def add(sig, at, pan, dry, send):
        st = dsp.pan(sig, pan)
        place_circ(events, st * dry, ns(at))
        place_circ(sends, st * send, ns(at))

    # three drip sources with their own pitch, rhythm and distance
    drip_lp = [("lp", 7000, 2), ("hp", 200, 2)]
    for tt in circular_times(rng, LOOP, 2.9, 0.35):
        d = synth.drip(rng, 1350 * rng.uniform(0.97, 1.03), 1.0)
        add(filt(d, drip_lp), tt, -0.45, 0.11, 0.16)
        if rng.uniform() < 0.15:
            add(filt(synth.drip(rng, 1400 * rng.uniform(0.97, 1.03), 0.6), drip_lp),
                tt + rng.uniform(0.09, 0.2), -0.45, 0.11, 0.16)
    for tt in circular_poisson(rng, LOOP, 5.5, 1.3):
        d = synth.drip(rng, rng.uniform(880, 1150), rng.uniform(0.5, 0.8), plink=rng.uniform() < 0.85)
        add(filt(d, drip_lp), tt, 0.55, 0.09, 0.17)
    for tt in circular_times(rng, LOOP, 7.6, 1.0):
        d = synth.drip(rng, 2100 * rng.uniform(0.98, 1.02), 0.45)
        add(filt(d, [("lp", 4500, 2), ("hp", 300, 2)]), tt, 0.1, 0.035, 0.19)

    # faint lapping against the walls
    for tt in circular_poisson(rng, LOOP, 3.1, 1.6):
        dur = rng.uniform(0.6, 1.2)
        k = ns(dur)
        fc0 = rng.uniform(320, 650)

        def g(tq, f, dur=dur, fc0=fc0):
            e = dsp.smoothstep(tq / (0.35 * dur)) * np.exp(-np.maximum(tq - 0.35 * dur, 0) / (0.25 * dur))
            return e * (dsp.mag_bp(f, fc0, 0.8) + 0.25 * dsp.mag_bp(f, fc0 * 2.6, 1.4))

        lap = dsp.shaped_noise(rng, k, g, 0.8, nfft=1024, hop=256)
        lap *= 0.6 + 0.4 * np.abs(np.clip(dsp.lfo_noise(rng, k, 18.0), -2, 2)) / 2
        lap = dsp.normalize(lap) * rng.uniform(0.35, 0.7)
        for _ in range(int(rng.integers(2, 6))):
            dsp.place(lap, synth.bubble(rng.uniform(350, 1100), rng.uniform(0.05, 0.15), 0.1),
                      ns(rng.uniform(0.3, 0.7) * dur))
        add(dsp.endfade(lap), tt, rng.uniform(-0.6, 0.3), 0.13, 0.05)

    # very soft distant censer/chain creaks: two swings each, twice per loop
    for k_i, (tt, stem, pan) in enumerate(((21.3, "creak1", -0.3), (53.8, "creak3", 0.35))):
        for sw, (dt, amp) in enumerate(((0.0, 1.0), (1.7, 0.6))):
            cr = chain_creak(rng, rng.uniform(0.8, 1.0), pitch=0.85 + 0.05 * k_i)
            cr = dsp.normalize(filt(cr, [("lp", 3000, 2), ("hp", 250, 2)]))
            if sw == 0:
                kc = c.kload(stem, "ChapelBed", pitch=0.7, stages=[("lp", 2200, 2), ("hp", 300, 2)])
                cr = dsp.fit(cr, max(len(cr), len(kc)))
                cr[:len(kc)] += 0.45 * kc
            add(dsp.normalize(cr) * amp, tt + dt, pan, 0.035, 0.08)

    # ---------------- stone-room reverb (circular) and mix
    ir = dsp.make_ir(dsp.rng_for("ir:chapel_amb"), 4.2, 3.4, 2.8, 1.4, predelay=0.03, early=CHAPEL_EARLY,
                     stereo=True, corr=0.4, lp=6000, density_ramp=0.08)
    wet = dsp.cconv(sends + 0.25 * wind_send, ir)
    mix = textures + events + wet
    return mix, -26.0


def builders():
    return [("ChapelBed", chapel_bed)]
