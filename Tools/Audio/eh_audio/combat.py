"""Combat one-shots for The Drowned Chapel. Each builder returns (mono_signal, duration_s, fade_out_s)."""
import math

import numpy as np

from . import dsp, synth
from .dsp import filt, ns, place, tvec
from .synth import burst, cut_at, hf_onset, room, thump

# Short stone-room early reflections (combat/water). Kept sparse and low so impacts stay punchy.
ROOM_EARLY = [(0.0072, 0.30), (0.0104, 0.24), (0.0139, 0.22), (0.0181, 0.19), (0.0236, 0.16),
              (0.0297, 0.13), (0.0366, 0.11), (0.0448, 0.09), (0.0541, 0.07), (0.0663, 0.05)]
CHAPEL_EARLY = [(0.019, 0.20), (0.027, 0.17), (0.038, 0.15), (0.049, 0.12), (0.063, 0.10), (0.081, 0.08)]


class Ctx:
    def __init__(self, kenney):
        self.k = kenney
        self.room_ir = dsp.make_ir(dsp.rng_for("ir:stone_room"), 0.32, 0.40, 0.33, 0.20, predelay=0.012,
                                   early=ROOM_EARLY, lp=8000, density_ramp=0.02)
        self.chapel_ir = dsp.make_ir(dsp.rng_for("ir:chapel_mono"), 3.0, 2.7, 2.1, 1.1, predelay=0.022,
                                     early=CHAPEL_EARLY, lp=6500, density_ramp=0.05)

    def kload(self, stem, used_by, pitch=1.0, stages=(), at_onset=False, trim_db=-45.0, tail=None, note=""):
        """Load a Kenney file (mono, 48 kHz) with light processing; every use is logged for NOTES.md.

        tail=(hold_s, tau_s) applies an exponential decay after hold_s (removes noise-floor tails)."""
        x = self.k.load(stem, used_by=used_by, pitch=pitch, trim_db=trim_db)
        if at_onset:
            x = cut_at(x, hf_onset(x))
        if stages:
            x = filt(x, list(stages), tail=0.2)
        if tail:
            tk = tvec(len(x))
            x = x * np.exp(-np.maximum(tk - tail[0], 0.0) / tail[1])
        self.k.log.append({"output": used_by, "stem": stem, "pitch": pitch, "stages": list(stages),
                           "onset_cut": at_onset, "trim_db": trim_db, "tail": tail, "note": note})
        return dsp.normalize(x)


# ============================================================================ impacts
def hit_light(c, v):
    name = f"HitLight_{v + 1:02d}"
    rng = dsp.rng_for(name)
    stem = ["impactPunch_medium_000", "impactPunch_medium_002", "impactPunch_medium_004"][v]
    out = np.zeros(ns(0.5))
    k = c.kload(stem, name, pitch=[1.06, 1.0, 1.12][v], at_onset=True, tail=(0.025, 0.045),
                stages=[("hp", 70, 2), ("peak", 190, 0.9, 2.0), ("lp", 9000, 2)])
    place(out, k * 0.85, 0)
    smack = burst(rng, 0.06, 0.0004, 0.006 + 0.0015 * v,
                  [("hp", 1100, 2), ("peak", 3000 + 450 * v, 1.2, 4.0), ("lp", 7500, 2)])
    place(out, smack * 0.55, ns(0.003))
    glove = burst(rng, 0.05, 0.0006, 0.012, [("bp", 650 + 80 * v, 1.1)])
    place(out, glove * 0.3, ns(0.003))
    place(out, thump(0.12, 175 + 15 * v, 92 + 10 * v, 0.018, 0.045, drive=1.4) * 0.55, ns(0.003))
    return room(out, c.room_ir, 0.22), 0.27, 0.06


def hit_heavy(c, v):
    name = f"HitHeavy_{v + 1:02d}"
    rng = dsp.rng_for(name)
    stem = ["impactPunch_heavy_000", "impactPunch_heavy_002", "impactPunch_heavy_004"][v]
    out = np.zeros(ns(0.7))
    k = c.kload(stem, name, pitch=[1.0, 0.94, 1.04][v], at_onset=True,
                stages=[("hp", 40, 2), ("peak", 95, 0.8, 2.0), ("lp", 7000, 2)])
    place(out, k * 0.75, 0)
    sub = thump(0.45, 125, 43 + 3 * v, 0.03, 0.13, drive=2.0)
    place(out, sub * 0.85, ns(0.002))
    crack = burst(rng, 0.07, 0.0004, 0.011, [("hp", 700, 2), ("peak", 2100 + 300 * v, 1.0, 3.0), ("lp", 6000, 2)])
    place(out, crack * 0.5, ns(0.003))
    body = burst(rng, 0.25, 0.002, 0.05, [("lp", 450, 4), ("hp", 60, 2)])
    place(out, body * 0.45, ns(0.003))
    leather = burst(rng, 0.06, 0.0008, 0.018, [("bp", 900 - 60 * v, 1.2)])
    place(out, leather * 0.28, ns(0.003))
    return room(out, c.room_ir, 0.25), 0.46, 0.09


def block(c, v):
    name = f"Block_{v + 1:02d}"
    rng = dsp.rng_for(name)
    out = np.zeros(ns(0.45))
    stem = ["impactSoft_medium_001", "impactSoft_heavy_003"][v]
    k = c.kload(stem, name, pitch=[1.1, 1.25][v], stages=[("hp", 60, 2), ("lp", 2200, 2)])
    place(out, k * 0.75, 0)
    place(out, thump(0.1, 200 - 20 * v, 125 - 10 * v, 0.012, 0.035, drive=1.2) * 0.5, ns(0.001))
    pad = burst(rng, 0.06, 0.001, 0.014 + 0.004 * v, [("bp", 620 - 60 * v, 0.9), ("lp", 2000, 2)])
    place(out, pad * 0.5, ns(0.001))
    tick = c.kload(["impactGeneric_light_002", "impactGeneric_light_004"][v], name, tail=(0.03, 0.02),
                   stages=[("hp", 200, 2), ("lp", 3000, 2)])
    place(out, tick * 0.28, ns(0.001))
    return room(out, c.room_ir, 0.2), 0.28, 0.06


def deflect(c):
    name = "Deflect"
    rng = dsp.rng_for(name)
    out = np.zeros(ns(0.9))
    f0 = 2650.0
    ting = dsp.modal(ns(0.85), [(f0, 1.0, 0.36), (f0 * 2.32, 0.5, 0.2), (f0 * 4.25, 0.26, 0.11),
                                (f0 * 6.63, 0.1, 0.06), (f0 * 0.5, 0.18, 0.16)],
                     attack=0.0003, rng=rng, doublet=3.0)
    place(out, dsp.normalize(ting) * 0.42, ns(0.001))
    spark = burst(rng, 0.02, 0.0002, 0.0018, [("hp", 5000, 2)])
    place(out, spark * 0.3, 0)
    soft = c.kload("impactGeneric_light_001", name, tail=(0.03, 0.02), stages=[("hp", 120, 2), ("lp", 2500, 2)])
    place(out, soft * 0.6, 0)
    body = c.kload("impactSoft_medium_002", name, pitch=1.15, stages=[("lp", 1500, 2)])
    place(out, body * 0.5, 0)
    return room(out, c.room_ir, 0.18), 0.65, 0.15


def grab(c):
    name = "Grab"
    rng = dsp.rng_for(name)
    out = np.zeros(ns(0.6))
    cl = c.kload("cloth1", name, pitch=1.08, trim_db=-22.0, stages=[("hp", 150, 2), ("lp", 9000, 2)])
    place(out, cl * 0.55, 0)
    cl2 = c.kload("cloth3", name, pitch=1.15, trim_db=-20.0, stages=[("hp", 200, 2)])
    place(out, cl2 * 0.35, ns(0.035))
    contact = c.kload("impactSoft_medium_003", name, pitch=1.2, stages=[("lp", 1200, 2)])
    place(out, contact * 0.6, ns(0.008))
    snap = burst(rng, 0.05, 0.0008, 0.015, [("bp", 2600, 0.7)])
    place(out, snap * 0.3, ns(0.004))
    m = ns(0.3)
    rustle = dsp.white(rng, m) * np.abs(np.clip(dsp.lfo_noise(rng, m, 70.0), -3, 3)) ** 1.5
    rustle = filt(rustle * dsp.env_ad(m, 0.01, 0.08), [("hp", 1200, 2), ("lp", 6000, 2)])
    place(out, dsp.normalize(rustle) * 0.22, ns(0.01))
    return room(out, c.room_ir, 0.2), 0.45, 0.08


def tech(c):
    name = "Tech"
    rng = dsp.rng_for(name)
    out = np.zeros(ns(0.5))
    clap_f = [("hp", 900, 2), ("peak", 1700, 1.0, 5.0), ("lp", 5500, 2)]
    for tt, a in ((0.0, 0.55), (0.008, 0.75), (0.017, 1.0)):
        place(out, burst(rng, 0.02, 0.0003, 0.0035, clap_f) * a, ns(0.004 + tt))
    place(out, burst(rng, 0.25, 0.0005, 0.045, clap_f) * 0.45, ns(0.021))
    push = dsp.white(rng, ns(0.14)) * dsp.env_points(ns(0.14), [(0, 0), (0.012, 1), (0.13, 0)])
    place(out, dsp.normalize(filt(push, [("lp", 1200, 2), ("hp", 120, 2)])) * 0.3, 0)
    place(out, thump(0.08, 165, 105, 0.01, 0.022, drive=1.3) * 0.3, ns(0.021))
    snap = c.kload("impactGeneric_light_000", name, pitch=1.1, tail=(0.02, 0.015), stages=[("hp", 400, 2)])
    place(out, snap * 0.35, ns(0.021))
    return room(out, c.room_ir, 0.22), 0.36, 0.07


# ============================================================================ falls / water
def body_slam(c, v):
    name = f"BodySlam_{v + 1:02d}"
    rng = dsp.rng_for(name)
    out = np.zeros(ns(1.6))
    place(out, thump(0.6, 95, 36 + 4 * v, 0.04, 0.17, drive=2.2) * 0.7, ns(0.002))
    k = c.kload(["impactSoft_heavy_000", "impactSoft_heavy_002"][v], name, pitch=[0.92, 1.0][v],
                stages=[("hp", 35, 2), ("lp", 3000, 2)])
    place(out, k * 0.75, 0)
    k2 = c.kload(["impactPunch_heavy_001", "impactPunch_heavy_003"][v], name, pitch=0.85, at_onset=True,
                 stages=[("lp", 1800, 2)])
    place(out, k2 * 0.35, 0)
    stone = burst(rng, 0.3, 0.001, 0.06, [("lp", 650, 2), ("hp", 50, 2), ("peak", 230, 1.5, 4.0)])
    place(out, stone * 0.4, ns(0.002))
    place(out, synth.splash(rng, 1.0, 1.3) * 1.5, ns(0.003))
    place(out, synth.splash(rng, 0.45, 0.9) * 0.7, ns(0.13 + 0.03 * v))
    return room(out, c.room_ir, 0.3), 1.3, 0.25


def body_fall(c, v):
    name = f"BodyFall_{v + 1:02d}"
    rng = dsp.rng_for(name)
    out = np.zeros(ns(1.2))
    place(out, thump(0.4, 120, 50 + 5 * v, 0.03, 0.1, drive=1.8) * 0.7, ns(0.002))
    k = c.kload(["impactSoft_heavy_001", "impactSoft_heavy_004"][v], name, pitch=1.1,
                stages=[("hp", 45, 2), ("lp", 2800, 2)])
    place(out, k * 0.6, 0)
    place(out, synth.splash(rng, 0.6, 0.95) * 1.3, ns(0.003))
    place(out, synth.splash(rng, 0.25, 0.6) * 0.55, ns(0.16 + 0.04 * v))
    return room(out, c.room_ir, 0.3), 0.95, 0.2


def step_water(c, v):
    name = f"StepWater_{v + 1:02d}"
    rng = dsp.rng_for(name)
    out = np.zeros(ns(0.6))
    k = c.kload(["footstep_concrete_001", "footstep_concrete_002", "footstep_concrete_004"][v], name,
                pitch=0.9, stages=[("lp", 800, 2), ("hp", 60, 2)])
    place(out, k * 0.18, ns(0.004))
    place(out, synth.splash(rng, 0.17 + 0.03 * v, 0.35, bright=0.85) * 0.9, ns(0.002))
    lift_t = 0.17 + 0.025 * v
    m = ns(0.12)
    suck = dsp.white(rng, m) * dsp.env_points(m, [(0, 0), (0.05, 1), (0.11, 0)])
    place(out, dsp.normalize(filt(suck, [("bp", 700, 0.8)])) * 0.18, ns(lift_t))
    for _ in range(6 + v):
        place(out, synth.bubble(rng.uniform(1500, 3800), rng.uniform(0.05, 0.14), rng.uniform(0.1, 0.3)),
              ns(lift_t + rng.uniform(0.02, 0.12)))
    for _ in range(3):  # drops falling off the foot; all finish before the fade-out
        place(out, synth.drip(rng, rng.uniform(2200, 4500), rng.uniform(0.04, 0.09)),
              ns(lift_t + rng.uniform(0.05, 0.12)))
    out = filt(out, [("lp", 6500, 2)])
    return room(out, c.room_ir, 0.28), 0.42, 0.08


def roll(c, v):
    name = f"Roll_{v + 1:02d}"
    rng = dsp.rng_for(name)
    out = np.zeros(ns(1.0))
    times = [0.0, 0.2 + 0.02 * v, 0.42 + 0.03 * v]
    gains = [0.75, 1.0, 0.65]
    for tt, gg in zip(times, gains):
        place(out, synth.splash(rng, 0.32 + 0.05 * rng.uniform(), 0.4) * gg, ns(tt + 0.003))
    m = ns(0.65)

    def g(t, f):
        e = dsp.smoothstep(t / 0.08) * dsp.smoothstep((0.62 - t) / 0.2)
        fc = 900 + 400 * np.sin(2 * math.pi * 2.2 * t)
        return e * dsp.mag_bp(f, fc, 0.7) * dsp.mag_hp(f, 120, 2)

    slosh = dsp.shaped_noise(rng, m, g, 0.5, nfft=512, hop=128)
    slosh *= 0.5 + 0.5 * np.abs(np.clip(dsp.lfo_noise(rng, m, 30.0), -2, 2)) / 2
    place(out, dsp.normalize(slosh) * 0.3, 0)
    for tt, stem in ((0.04, "impactSoft_medium_000"), (0.27 + 0.02 * v, "impactSoft_medium_004")):
        place(out, c.kload(stem, name, pitch=1.0 + 0.08 * v, stages=[("lp", 900, 2)]) * 0.5, ns(tt))
    cl = c.kload(["cloth2", "cloth4", "cloth2"][v], name, pitch=[1.0, 1.0, 0.9][v], trim_db=-25.0,
                 stages=[("hp", 200, 2)])
    place(out, cl * 0.3, ns(0.02))
    return room(out, c.room_ir, 0.28), 0.75, 0.15


# ============================================================================ whooshes
def whoosh_light(c, v):
    rng = dsp.rng_for(f"WhooshLight_{v + 1:02d}")
    dur = [0.2, 0.18, 0.22][v]
    y = synth.whoosh(rng, dur, peak_t=dur * 0.62, f_lo=700 + 100 * v, f_hi=2600 + 300 * v, q=1.3,
                     rise_pow=2.2, fall_tau=0.025, body=0.25)
    return room(y, c.room_ir, 0.1), dur, 0.02


def whoosh_heavy(c, v):
    rng = dsp.rng_for(f"WhooshHeavy_{v + 1:02d}")
    dur = [0.42, 0.38, 0.45][v]
    y = synth.whoosh(rng, dur, peak_t=dur * 0.6, f_lo=260 + 30 * v, f_hi=950 + 80 * v, q=1.1,
                     rise_pow=2.0, fall_tau=0.05, body=0.55, exponent=0.9)
    y = dsp.normalize(y)
    air = synth.whoosh(rng, dur, peak_t=dur * 0.62, f_lo=1500, f_hi=3200, q=1.6, fall_tau=0.03, body=0.0)
    return room(y + 0.25 * dsp.normalize(air), c.room_ir, 0.1), dur, 0.03


def whoosh_kick(c, v):
    rng = dsp.rng_for(f"WhooshKick_{v + 1:02d}")
    dur = [0.3, 0.32, 0.28][v]
    y = synth.whoosh(rng, dur, peak_t=dur * 0.58, f_lo=480 + 40 * v, f_hi=1700 + 150 * v, q=1.3,
                     rise_pow=2.0, fall_tau=0.035, body=0.4, flutter=0.55, flutter_hz=55 + 10 * v)
    y = dsp.normalize(y)
    snap = burst(rng, 0.03, 0.0005, 0.004, [("bp", 2200, 0.9)])
    place(y, snap * 0.25, ns(dur * 0.6))
    return room(y, c.room_ir, 0.1), dur, 0.025


def whoosh_spin(c, v):
    rng = dsp.rng_for(f"WhooshSpin_{v + 1:02d}")
    dur = [0.85, 0.8, 0.9][v]
    y = synth.spin_whoosh(rng, dur, rate0=3.0 + 0.2 * v, rate1=4.6 + 0.2 * v, passes_peak=dur * 0.7,
                          f_lo=380 + 40 * v, f_hi=1500 + 120 * v, doppler=0.5, q=2.0)
    return room(y, c.room_ir, 0.1), dur, 0.05


# ============================================================================ Wren: golden lightning aura
def aura_charge(c, v):
    name = f"AuraCharge_{v + 1:02d}"
    rng = dsp.rng_for(name)
    dur = 0.6
    n = ns(dur)
    t = tvec(n)
    u = t / dur
    sp = synth.sparks(rng, dur, lambda tt: 15 + 340 * (tt / dur) ** 2.2, lambda tt: 0.35 + 0.65 * (tt / dur),
                      bright=1.0 + 0.08 * v)
    hum_f = (80 + 8 * v) * (1 + 1.1 * u ** 1.6)
    hum = synth.buzz(rng, dur, hum_f, dsp.smoothstep(u * 1.2) * 0.6)
    base = [293.66, 440.0, 587.33][v % 3]
    sh = synth.shimmer(rng, dur, [base, base * 1.5, base * 2], dsp.smoothstep(u) ** 1.5, trem=9.0, glide=0.12)
    y = dsp.normalize(sp) * 0.7 + dsp.normalize(hum) * 0.45 + dsp.normalize(sh) * 0.3
    swell = synth.whoosh(rng, dur, peak_t=dur * 0.95, f_lo=600, f_hi=4200, q=0.9, rise_pow=2.5,
                         fall_tau=0.01, body=0.2)
    y += dsp.normalize(swell) * 0.25
    return room(y, c.room_ir, 0.12), dur, 0.02


def aura_ignite(c):
    name = "AuraIgnite"
    rng = dsp.rng_for(name)
    dur = 1.4
    n = ns(dur)
    t = tvec(n)
    out = np.zeros(n)
    crack = burst(rng, 0.08, 0.0002, 0.012, [("hp", 300, 2), ("peak", 3500, 0.8, 3.0)])
    place(out, crack * 0.85, 0)
    place(out, thump(0.2, 140, 62, 0.02, 0.06, drive=1.6) * 0.6, 0)
    place(out, dsp.normalize(synth.zap(0.15, 3200, 220, 0.03)) * 0.45, ns(0.002))
    sp = synth.sparks(rng, dur, lambda tt: 260 * np.exp(-tt / 0.35) + 6, lambda tt: np.exp(-tt / 0.7))
    out += dsp.normalize(sp) * 0.55
    sh_env = dsp.env_ad(n, 0.03, 0.55)
    sh = synth.shimmer(rng, dur, [293.66, 440.0, 659.26, 739.99], sh_env, trem=7.0, glide=0.015)
    out += dsp.normalize(sh) * 0.42
    hum = synth.buzz(rng, dur, np.full(n, 120.0), np.exp(-t / 0.25) * 0.5)
    out += dsp.normalize(hum) * 0.3
    return room(out, c.room_ir, 0.15), dur, 0.3


def aura_hit(c):
    name = "AuraHit"
    rng = dsp.rng_for(name)
    dur = 0.32
    n = ns(dur)
    out = np.zeros(n)
    place(out, burst(rng, 0.03, 0.0001, 0.0035, [("hp", 1000, 2)]) * 0.8, 0)
    place(out, dsp.normalize(synth.zap(0.1, 2600, 300, 0.018)) * 0.55, ns(0.001))
    sp = synth.sparks(rng, dur, lambda tt: 420 * np.exp(-tt / 0.06) + 15, lambda tt: np.exp(-tt / 0.12))
    out += dsp.normalize(sp) * 0.5
    ping = synth.shimmer(rng, dur, [880.0, 1318.5], dsp.env_ad(n, 0.002, 0.07), trem=11.0)
    out += dsp.normalize(ping) * 0.22
    return room(out, c.room_ir, 0.15), dur, 0.05


def aura_fade(c):
    name = "AuraFade"
    rng = dsp.rng_for(name)
    dur = 1.1
    n = ns(dur)
    t = tvec(n)
    u = t / dur
    sp = synth.sparks(rng, dur, lambda tt: 140 * np.exp(-tt / 0.3) + 3, lambda tt: np.exp(-tt / 0.5))
    hum = synth.buzz(rng, dur, 150 * (1 - 0.5 * u), np.exp(-t / 0.3) * 0.5)
    sh = synth.shimmer(rng, dur, [440.0, 659.26], 0.6 * np.exp(-t / 0.35), trem=6.0, glide=-0.08)
    y = dsp.normalize(sp) * 0.75 + dsp.normalize(hum) * 0.4 + dsp.normalize(sh) * 0.3
    return room(y, c.room_ir, 0.12), dur, 0.25


# ============================================================================ Ashka: crimson flame
def _flame_tone(dur, env_pts, f=55.0):
    """Faint dark tonal core that gives Ashka's flame a magical identity."""
    n = ns(dur)
    t = tvec(n)
    y = np.sin(2 * math.pi * f * t) + 0.5 * np.sin(2 * math.pi * 2 * f * t + 0.3) + 0.25 * np.sin(2 * math.pi * 3.01 * f * t)
    return dsp.softclip(y, 1.5) * dsp.env_points(n, env_pts)


def flame_ignite(c):
    name = "FlameIgnite"
    rng = dsp.rng_for(name)
    dur = 1.05
    n = ns(dur)
    out = np.zeros(n)
    t0 = 0.07
    pre = synth.whoosh(rng, t0 + 0.02, peak_t=t0, f_lo=800, f_hi=3000, q=0.8, rise_pow=2.5, fall_tau=0.01)
    place(out, dsp.normalize(pre) * 0.25, 0)

    def g(tt, f):
        x = np.maximum(tt - t0, 0) / 0.07
        e = dsp.smoothstep((tt - t0) / 0.022) * np.exp(-np.maximum(tt - t0, 0) / 0.28)
        fc = 140 + 1500 * x * np.exp(1 - x)
        return e * dsp.mag_lp2(f, fc, 1.1) * dsp.mag_hp(f, 30, 2)

    whoomp = dsp.shaped_noise(rng, n, g, 1.0)
    out += dsp.normalize(whoomp) * 0.9
    tt = tvec(n)
    sub_f = 46 + 34 * np.exp(-np.maximum(tt - t0, 0) / 0.09)
    sub = np.sin(2 * math.pi * np.cumsum(sub_f) / dsp.SR) * dsp.smoothstep((tt - t0) / 0.025) * np.exp(-np.maximum(tt - t0, 0) / 0.2)
    out += sub * 0.6
    roar = synth.fire_roar(rng, dur, [(0, 0), (t0, 0), (t0 + 0.05, 0.8), (0.5, 0.35), (dur, 0.0)],
                           [(0, 900), (t0 + 0.05, 2200), (dur, 700)], turb=0.6)
    out += dsp.normalize(roar) * 0.4
    cr = synth.crackle(rng, dur, lambda x: np.where(x > t0, 45 * np.exp(-(x - t0) / 0.5), 0),
                       lambda x: np.exp(-(x - t0) / 0.6))
    out += dsp.normalize(cr) * 0.3
    out += _flame_tone(dur, [(0, 0), (t0, 0), (t0 + 0.04, 0.25), (dur, 0)]) * 0.5
    return room(out, c.room_ir, 0.12), dur, 0.2


def flame_hit(c):
    name = "FlameHit"
    rng = dsp.rng_for(name)
    dur = 0.6
    n = ns(dur)
    out = np.zeros(n)
    roar = synth.fire_roar(rng, dur, [(0, 0), (0.008, 1.0), (0.12, 0.55), (dur, 0)],
                           [(0, 3200), (0.1, 1400), (dur, 700)], turb=0.7, hiss=0.25)
    out += dsp.normalize(roar) * 0.85
    place(out, thump(0.25, 110, 52, 0.02, 0.07, drive=1.8) * 0.6, 0)
    place(out, burst(rng, 0.05, 0.0003, 0.006, [("hp", 1500, 2), ("lp", 8000, 2)]) * 0.35, 0)
    cr = synth.crackle(rng, dur, lambda x: 160 * np.exp(-x / 0.15) + 5, lambda x: np.exp(-x / 0.25))
    out += dsp.normalize(cr) * 0.38
    out += _flame_tone(dur, [(0, 0), (0.01, 0.3), (dur, 0)], 58.0) * 0.4
    return room(out, c.room_ir, 0.14), dur, 0.12


def flame_roar(c, v):
    name = f"FlameRoar_{v + 1:02d}"
    rng = dsp.rng_for(name)
    dur = 0.85
    n = ns(dur)
    a = [0.06, 0.05, 0.08][v]
    roar = synth.fire_roar(rng, dur, [(0, 0), (a, 1.0), (0.45, 0.8), (dur, 0)],
                           [(0, 2200), (a, 1600 + 150 * v), (dur, 650)], turb=0.6, hiss=0.2)
    rumble = synth.fire_roar(rng, dur, [(0, 0), (a * 1.5, 1.0), (0.5, 0.6), (dur, 0)],
                             [(0, 160), (dur, 110)], turb=0.4, hiss=0.0)
    cr = synth.crackle(rng, dur, lambda x: 40 + 60 * np.exp(-x / 0.3), lambda x: 1.0 - 0.6 * x / dur)
    y = dsp.normalize(roar) * 0.85 + dsp.normalize(rumble) * 0.55 + dsp.normalize(cr) * 0.3
    y += _flame_tone(dur, [(0, 0), (a, 0.3), (0.5, 0.2), (dur, 0)], [55.0, 52.0, 58.27][v]) * 0.45
    return room(y, c.room_ir, 0.14), dur, 0.15


# ============================================================================ stingers
def round_bell(c):
    rng = dsp.rng_for("RoundBell")
    dur = 2.6
    y = synth.bell(dur + 0.5, 196.0, rng, strike=0.45, decay_scale=1.0)
    y = dsp.normalize(y)
    wet = dsp.fit(dsp.fftconv(y, c.chapel_ir), len(y))
    return y + 0.45 * wet, dur, 0.9


def fight_stinger(c):
    rng = dsp.rng_for("FightStinger")
    dur = 1.2
    n = ns(1.6)
    out = np.zeros(n)
    drum = synth.taiko(rng, 1.2, 62.0, decay=0.2, slap=0.35, beater=0.5)
    place(out, dsp.normalize(drum) * 0.9, 0)
    place(out, burst(rng, 0.6, 0.002, 0.12, [("hp", 2500, 2), ("lp", 9000, 2)]) * 0.12, 0)
    # low brass-like swell: detuned saw stack whose brightness follows its loudness
    t = tvec(n)
    env = dsp.env_points(n, [(0, 0), (0.04, 0.15), (0.5, 1.0), (0.75, 0.7), (1.1, 0.0)])
    dark = synth.saw_table(60, 0.22)
    bright = synth.saw_table(60, 0.06)
    brass = np.zeros(n)
    for m in (38, 45, 50, 53):  # D2 A2 D3 F3
        f0 = float(dsp.midi_hz(m))
        for d in (-6, 0, 6):
            scoop = 2 ** ((-35 * np.exp(-t / 0.08) + d) / 1200.0)
            ph = np.cumsum(f0 * scoop) / dsp.SR + rng.uniform()
            brass += dsp.wt_read(dark, ph) * (1 - env) + dsp.wt_read(bright, ph) * env
    brass = filt(brass * env, [("lp", 2400, 2), ("hp", 50, 2)])
    out += dsp.normalize(brass) * 0.85
    wet = dsp.fit(dsp.fftconv(out, c.chapel_ir), n)
    return out + 0.22 * wet, dur, 0.15


def ko(c):
    rng = dsp.rng_for("KO")
    dur = 2.6
    n = ns(3.0)
    out = np.zeros(n)
    place(out, thump(1.6, 78, 27, 0.12, 0.55, drive=2.4) * 0.9, 0)
    k = c.kload("impactPunch_heavy_001", "KO", pitch=0.8, at_onset=True, stages=[("lp", 3000, 2)])
    place(out, k * 0.6, 0)
    place(out, dsp.normalize(synth.taiko(rng, 1.5, 48.0, decay=0.45, slap=0.2)) * 0.6, 0)
    place(out, burst(rng, 0.4, 0.0005, 0.03, [("hp", 500, 2), ("lp", 5000, 2)]) * 0.3, 0)
    rumble = burst(rng, 2.0, 0.02, 0.6, [("lp", 220, 4), ("hp", 25, 2)], exponent=1.0)
    place(out, rumble * 0.35, 0)
    wet = dsp.fit(dsp.fftconv(out, c.chapel_ir), n)
    return out + 0.5 * wet, dur, 0.8


def builders():
    """(name, builder) list for every combat one-shot."""
    out = []
    for v in range(3):
        out.append((f"HitLight_{v + 1:02d}", lambda c, v=v: hit_light(c, v)))
    for v in range(3):
        out.append((f"HitHeavy_{v + 1:02d}", lambda c, v=v: hit_heavy(c, v)))
    for v in range(2):
        out.append((f"Block_{v + 1:02d}", lambda c, v=v: block(c, v)))
    out += [("Deflect", deflect), ("Grab", grab), ("Tech", tech)]
    for v in range(2):
        out.append((f"BodySlam_{v + 1:02d}", lambda c, v=v: body_slam(c, v)))
    for v in range(2):
        out.append((f"BodyFall_{v + 1:02d}", lambda c, v=v: body_fall(c, v)))
    for v in range(3):
        out.append((f"StepWater_{v + 1:02d}", lambda c, v=v: step_water(c, v)))
    for v in range(3):
        out.append((f"Roll_{v + 1:02d}", lambda c, v=v: roll(c, v)))
    for base, fn in (("WhooshLight", whoosh_light), ("WhooshHeavy", whoosh_heavy),
                     ("WhooshKick", whoosh_kick), ("WhooshSpin", whoosh_spin)):
        for v in range(3):
            out.append((f"{base}_{v + 1:02d}", lambda c, v=v, fn=fn: fn(c, v)))
    for v in range(3):
        out.append((f"AuraCharge_{v + 1:02d}", lambda c, v=v: aura_charge(c, v)))
    out += [("AuraIgnite", aura_ignite), ("AuraHit", aura_hit), ("AuraFade", aura_fade),
            ("FlameIgnite", flame_ignite), ("FlameHit", flame_hit)]
    for v in range(3):
        out.append((f"FlameRoar_{v + 1:02d}", lambda c, v=v: flame_roar(c, v)))
    out += [("RoundBell", round_bell), ("FightStinger", fight_stinger), ("KO", ko)]
    return out
