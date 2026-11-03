"""Original music loops for Ebony Hearts: Theme (menus), Battle and Training.

Palette (shared): dark detuned wavetable pads, a synthesised formant "choir" pad (additive vowels,
no voice samples), a soft chapel bell, synthesised taiko / frame drums and a low pulsing ostinato,
all in D minor (aeolian with a phrygian Eb colour), placed in a synthetic stone-chapel reverb.

Seamless loops: every note is written on a circle of exactly LOOP samples (tails wrap into the
start) and the reverb is a circular convolution, so the rendered loop is a periodic signal.
"""
import math

import numpy as np

from . import dsp, synth
from .dsp import SR, filt, ns, place_circ, tvec

MUSIC_EARLY = [(0.017, 0.2), (0.026, 0.17), (0.037, 0.15), (0.051, 0.12), (0.066, 0.1), (0.088, 0.08),
               (0.11, 0.06)]
TARGET_LUFS = -18.0


# ============================================================================ instruments
def _table(amps, rng):
    tab = dsp.wavetable(list(amps), size=4096, phases=rng.uniform(0, 2 * math.pi, len(amps)))
    return tab / (np.max(np.abs(tab)) + 1e-12)


def saw_amps(f0, rolloff, odd=1.0, fmax=12000.0):
    nh = max(1, int(min(fmax, SR * 0.45) / f0))
    k = np.arange(1, nh + 1)
    a = (1.0 / k) * np.exp(-rolloff * (k - 1))
    a[1::2] *= odd  # even harmonics (k = 2, 4, ...) scaled
    return a


def wt_voice(tab_a, tab_b, freq, mix):
    """Read two tables with one phase and crossfade by mix (0 -> a, 1 -> b)."""
    ph = np.cumsum(freq) / SR
    return dsp.wt_read(tab_a, ph) * (1.0 - mix) + dsp.wt_read(tab_b, ph) * mix


def amp_env(n, attack, release, curve=1.0):
    t = tvec(n)
    dur = n / SR
    a = dsp.smoothstep(t / max(attack, 1e-4)) ** curve
    r = dsp.smoothstep((dur - t) / max(release, 1e-4))
    return a * r


def pad_note(rng, midi, dur, attack=1.5, release=2.5, dark=0.45, bright=0.16, voices=3, detune=7.0,
             spread=0.6, sub=0.0):
    """Detuned wavetable pad. Brightness opens over the attack and closes slowly. Stereo (n, 2)."""
    n = ns(dur)
    t = tvec(n)
    f0 = float(dsp.midi_hz(midi))
    ta = _table(saw_amps(f0 * 1.02, dark, 0.7), rng)
    tb = _table(saw_amps(f0 * 1.02, bright, 0.7), rng)
    mix = dsp.smoothstep(t / max(attack, 1e-3)) * (0.75 + 0.25 * np.exp(-t / max(dur * 0.6, 0.1)))
    out = np.zeros((n, 2))
    for v in range(voices):
        cents = (v - (voices - 1) / 2) * detune + rng.uniform(-1.5, 1.5)
        drift = 1.0 + 0.0012 * np.clip(dsp.lfo_noise(rng, n, 0.4), -2, 2)
        y = wt_voice(ta, tb, f0 * 2 ** (cents / 1200.0) * drift, mix)
        p = 0.0 if voices == 1 else spread * (2 * v / (voices - 1) - 1)
        out += dsp.pan(y, p)
    out /= voices
    if sub > 0:  # reinforce the fundamental (centre) so low notes stay solid in mono
        out += sub * dsp.pan(np.sin(2 * math.pi * f0 * t + rng.uniform(0, 6)), 0.0)
    return out * amp_env(n, attack, release)[:, None]


# alto-range formants: (freq Hz, bandwidth Hz, gain dB)
VOWELS = {
    "a": [(800, 80, 0), (1150, 90, -4), (2800, 120, -20), (3500, 130, -36), (4950, 140, -60)],
    "o": [(450, 70, 0), (800, 80, -9), (2830, 100, -16), (3500, 130, -28), (4950, 135, -55)],
    "u": [(325, 50, 0), (700, 60, -12), (2530, 170, -30), (3500, 180, -40), (4950, 200, -64)],
}


def vowel_amps(f0, vowel, fmax=6000.0):
    nh = max(1, int(fmax / f0))
    fk = f0 * np.arange(1, nh + 1)
    env = np.zeros(nh)
    for F, B, g in VOWELS[vowel]:
        env += dsp.undb(g) / np.sqrt(1.0 + ((fk - F) / (B / 2.0)) ** 2)
    return (np.arange(1, nh + 1) ** -1.3) * env


def choir_note(rng, midi, dur, v_from="u", v_to="a", attack=2.0, release=2.5, voices=6):
    """Formant-synthesised ensemble 'aah/ooh' (no recorded voice). Stereo (n, 2)."""
    n = ns(dur)
    t = tvec(n)
    f0 = float(dsp.midi_hz(midi))
    ta = _table(vowel_amps(f0, v_from), rng)
    tb = _table(vowel_amps(f0, v_to), rng)
    morph = dsp.smoothstep((t - 0.15 * dur) / (0.6 * dur))
    out = np.zeros((n, 2))
    for v in range(voices):
        cents = rng.uniform(-9, 9)
        rate = rng.uniform(4.6, 5.6)
        depth = rng.uniform(12, 22) * dsp.smoothstep((t - 0.4) / 1.5)
        vib = depth * np.sin(2 * math.pi * rate * t + rng.uniform(0, 6))
        drift = 5.0 * np.clip(dsp.lfo_noise(rng, n, 0.3), -2, 2) / 2
        f = f0 * 2 ** ((cents + vib + drift) / 1200.0)
        y = wt_voice(ta, tb, f, morph)
        y *= 0.8 + 0.2 * np.clip(dsp.lfo_noise(rng, n, 0.6), -2, 2) / 2
        out += dsp.pan(y, rng.uniform(-0.7, 0.7))
    # breath: a little formant-coloured noise
    breath = filt(dsp.white(rng, n), [("bp", VOWELS[v_from][0][0], 2.0), ("bp", VOWELS[v_to][1][0], 1.5)])
    out += dsp.pan(dsp.normalize(breath) * 0.04, 0.0)
    return out / voices * amp_env(n, attack, release)[:, None]


def bell_note(rng, midi, dur=4.0):
    """Soft chapel bell for the motif (mallet on a small bell)."""
    f = float(dsp.midi_hz(midi))
    s = (440.0 / f) ** 0.3
    parts = [(1.0, 1.0, 3.0), (2.0, 0.38, 1.7), (2.76, 0.26, 1.15), (4.07, 0.12, 0.7), (5.43, 0.07, 0.45),
             (8.9, 0.025, 0.2)]
    y = dsp.modal(ns(dur), [(f * r, a, tau * s) for r, a, tau in parts], attack=0.0025, rng=rng, doublet=0.7)
    strike = synth.burst(rng, 0.02, 0.0005, 0.003, [("bp", min(f * 3, 9000), 1.0)])
    dsp.place(y, strike * 0.08, 0)
    return dsp.endfade(y, max_s=0.5)


def ostinato_note(rng, midi, dur, vel, bright=1.0, sub=0.35):
    """Plucked/bowed low string pulse: bright attack decaying to dark; mono."""
    n = ns(dur)
    t = tvec(n)
    f0 = float(dsp.midi_hz(midi))
    ta = _table(saw_amps(f0, 0.5, 0.8, fmax=3000), rng)
    tb = _table(saw_amps(f0, 0.12 / bright, 0.8, fmax=3000), rng)
    mix = np.exp(-t / (0.05 + 0.04 * vel)) * min(1.0, 0.5 + 0.5 * vel)
    y = 0.5 * (wt_voice(ta, tb, np.full(n, f0 * 2 ** (-4 / 1200)), mix)
               + wt_voice(ta, tb, np.full(n, f0 * 2 ** (4 / 1200)), mix))
    y += sub * np.sin(2 * math.pi * f0 * t)
    env = dsp.smoothstep(t / 0.006) * (0.45 + 0.55 * np.exp(-t / 0.09)) * dsp.smoothstep((dur - t) / 0.04)
    return y * env * vel


class DrumKit:
    """Synthesised taiko-family drums with a few cached variants per voice (seeded)."""

    SPEC = {  # f0, decay, slap, drop, beater, length
        "odaiko": (41.0, 0.55, 0.15, 0.3, 0.35, 2.2),
        "taiko": (58.0, 0.3, 0.3, 0.25, 0.45, 1.3),
        "mid": (96.0, 0.17, 0.4, 0.2, 0.4, 0.8),
        "frame": (172.0, 0.09, 0.7, 0.12, 0.25, 0.5),
    }

    def __init__(self, name):
        self.cache = {}
        self.rng = dsp.rng_for("drums:" + name)

    def hit(self, kind, vel):
        if kind not in self.cache:
            f0, dec, slap, drop, beater, length = self.SPEC[kind]
            vs = []
            for i in range(4):
                y = synth.taiko(self.rng, length, f0 * (1 + 0.012 * (i - 1.5)), decay=dec, slap=slap,
                                drop=drop, beater=beater)
                if kind == "frame":
                    y = filt(y, [("lp", 2600, 2)])
                vs.append(dsp.normalize(y))
            self.cache[kind] = vs
        vs = self.cache[kind]
        y = vs[int(self.rng.integers(0, len(vs)))]
        return y * vel


class Song:
    def __init__(self, name, loop_s):
        self.name = name
        self.n = ns(loop_s)
        self.loop_s = loop_s
        self.buses = {}
        self.rng = dsp.rng_for("song:" + name)

    def bus(self, b):
        if b not in self.buses:
            self.buses[b] = [np.zeros((self.n, 2)), 0.0]
        return self.buses[b]

    def add(self, b, sig, t, pan=0.0, gain=1.0):
        st = sig if sig.ndim == 2 else dsp.pan(sig, pan)
        place_circ(self.bus(b)[0], st * gain, ns(t % self.loop_s))

    def mix(self, settings, ir):
        """settings: bus -> (gain, reverb send, filter stages)."""
        dry = np.zeros((self.n, 2))
        send = np.zeros((self.n, 2))
        for b, (x, _) in self.buses.items():
            g, s, st = settings.get(b, (1.0, 0.2, []))
            y = filt(x, st, circular=True) if st else x
            dry += g * y
            send += g * s * y
        return dry + dsp.cconv(send, ir)


def music_ir(name, rt=(4.0, 3.3, 1.8)):
    return dsp.make_ir(dsp.rng_for("ir:music:" + name), 4.6, rt[0], rt[1], rt[2], predelay=0.028,
                       early=MUSIC_EARLY, stereo=True, corr=0.45, lp=7000, density_ramp=0.07)


# ============================================================================ Theme (menus)
def theme(c):
    bpm = 60.0
    beat = 60.0 / bpm
    bar = 4 * beat
    s = Song("Theme", 20 * bar)
    rng = s.rng
    chords = [  # bar, bars, bass, pad voicing, choir voicing
        (0, 2, 38, [50, 57, 65], None),          # Dm
        (2, 2, 34, [50, 53, 58], None),          # Bb
        (4, 2, 31, [50, 55, 58], [55, 58, 62]),  # Gm (+choir)
        (6, 2, 38, [53, 57, 62], [57, 62, 65]),  # Dm (+choir)
        (8, 2, 38, [51, 55, 58], None),          # Eb/D (phrygian colour)
        (10, 2, 36, [48, 55, 63], None),         # Cm
        (12, 2, 31, [50, 55, 58], [55, 58, 62]), # Gm (+choir)
        (14, 2, 34, [50, 53, 57], [53, 57, 62]), # Bbmaj7 (+choir)
        (16, 2, 31, [50, 55, 58], None),         # Gm
        (18, 1, 33, [50, 52, 57], None),         # Asus4
        (19, 1, 33, [49, 52, 57], None),         # A (leads back to Dm at the loop point)
    ]
    for b0, nb, bass, pad, choir in chords:
        t0 = b0 * bar - 0.6
        dur = nb * bar + 3.2
        s.add("bass", pad_note(rng, bass, dur, attack=1.6, release=3.0, dark=0.6, bright=0.3, voices=2,
                               detune=5, spread=0.2, sub=0.45), t0, gain=0.55)
        for m in pad:
            s.add("pad", pad_note(rng, m, dur, attack=1.8, release=3.0, dark=0.5, bright=0.22, voices=3,
                                  detune=8, spread=0.65), t0, gain=0.24)
        if choir:
            for i, m in enumerate(choir):
                s.add("choir", choir_note(rng, m, nb * bar + 2.5, ["u", "o", "u"][i], ["o", "a", "o"][i],
                                          attack=2.6, release=2.5), b0 * bar + 0.3, gain=0.3)
    motif = [  # (time in beats, midi)
        (4.0, 69), (5.5, 65), (6.0, 67), (7.0, 62),
        (20.0, 74), (21.0, 72), (21.5, 69), (23.0, 70),
        (36.0, 70), (37.0, 67), (38.5, 75), (39.0, 74),
        (52.0, 74), (53.5, 70), (54.0, 69), (55.0, 67),
        (68.0, 67), (70.0, 74),
        (76.0, 69), (77.0, 74), (78.0, 73),
    ]
    for i, (tb, m) in enumerate(motif):
        s.add("bell", bell_note(rng, m, 5.0), tb * beat, pan=0.3 if i % 2 else -0.25, gain=0.32)
    ir = music_ir("Theme", (4.4, 3.6, 2.0))
    mix = s.mix({
        "bass": (1.0, 0.15, [("lp", 900, 2)]),
        "pad": (1.0, 0.35, [("lp", 2600, 2), ("hp", 90, 2)]),
        "choir": (0.9, 0.55, [("hp", 150, 2)]),
        "bell": (1.0, 0.75, [("hp", 200, 2)]),
    }, ir)
    return mix, TARGET_LUFS, bar


# ============================================================================ Battle
QUAL = {  # pad voicings (octave 2-3, kept low and sparse)
    "Dm": (38, [50, 53, 57]), "Bb": (34, [46, 50, 53]), "C": (36, [48, 52, 55]),
    "Eb": (39, [46, 51, 55]), "Gm": (31, [46, 50, 55]), "A": (33, [45, 49, 52]),
}


def battle(c):
    bpm = 112.5  # 25600 samples per beat: the loop is sample-exact
    beat = 60.0 / bpm
    bar = 4 * beat
    six = beat / 4
    prog = (["Dm", "Dm", "Bb", "C", "Dm", "Dm", "Eb", "C"]          # A  (bars 0-7)
            + ["Dm", "Dm", "Bb", "C", "Gm", "Gm", "A", "A"]         # B  (8-15)
            + ["Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "Eb", "Eb"]      # C  breakdown (16-23)
            + ["Dm", "Dm", "Bb", "C", "Dm", "Eb", "C", "A"]         # D  (24-31)
            + ["Dm", "Bb", "Gm", "A"])                              # tag (32-35)
    nbars = len(prog)
    s = Song("Battle", nbars * bar)
    rng = s.rng
    kit = DrumKit("Battle")

    def section(b):
        return "A" if b < 8 else "B" if b < 16 else "C" if b < 24 else "D" if b < 32 else "T"

    for b, ch in enumerate(prog):
        sec = section(b)
        t_bar = b * bar
        root = QUAL[ch][0]
        # ---- ostinato: 8ths, 3-3-2 accents, phrase-end pickup note
        vels = [1.0, 0.55, 0.7, 0.92, 0.55, 0.7, 0.95, 0.6]
        if sec == "C":
            vels = [0.8, 0.0, 0.45, 0.6, 0.0, 0.45, 0.7, 0.0]
        for e, v in enumerate(vels):
            if v <= 0:
                continue
            m = root
            if e == 7 and (b % 4 == 3):
                m = root + 7 if ch != "A" else root + 5
            v *= 1 + rng.uniform(-0.06, 0.06)
            tt = t_bar + e * 2 * six + rng.uniform(-0.002, 0.002)
            s.add("ost", ostinato_note(rng, m, 2 * six * 0.9, v, bright=1.0 if sec != "C" else 0.7, sub=0.2), tt)
            if sec in ("B", "D", "T") and e in (0, 3, 6):
                s.add("ost", ostinato_note(rng, m + 12, 2 * six * 0.8, v * 0.35, sub=0.0), tt)
        # ---- drums (16th grid)
        hits = []
        if b % 8 == 0:
            hits.append(("odaiko", 0, 1.0))
        if sec == "C":
            hits += [("taiko", 0, 0.85), ("taiko", 8, 0.7), ("mid", 12, 0.45), ("frame", 14, 0.35)]
        else:
            hits += [("taiko", 0, 1.0), ("taiko", 6, 0.8), ("taiko", 10, 0.85), ("taiko", 8, 0.45)]
            hits += [("frame", st, 0.4) for st in (2, 6, 10, 14)]
            if sec in ("B", "D", "T"):
                hits += [("frame", 7, 0.25), ("frame", 15, 0.28), ("frame", 3, 0.2)]
        fill = b in (7, 15, 23, 31, 35)
        if fill:
            hits += [("mid", st, 0.3 + 0.7 * (st - 8) / 7) for st in range(8, 16)]
        elif sec != "C":
            hits += [("mid", 4, 0.75), ("mid", 12, 0.8)]
        for kind, st, v in hits:
            v *= 1 + rng.uniform(-0.08, 0.08)
            s.add("drums_" + kind, kit.hit(kind, v), t_bar + st * six + rng.uniform(-0.002, 0.002),
                  pan={"odaiko": 0.0, "taiko": -0.12, "mid": 0.18, "frame": 0.3}[kind])
    # ---- dark pads (sections B, C, D, tag), one chord per bar group
    b = 0
    while b < nbars:
        ch = prog[b]
        nb = 1
        while b + nb < nbars and prog[b + nb] == ch:
            nb += 1
        if section(b) != "A":
            for m in QUAL[ch][1]:
                s.add("pad", pad_note(rng, m, nb * bar + 1.2, attack=0.5, release=1.0, dark=0.55, bright=0.3,
                                      voices=3, detune=9, spread=0.7), b * bar - 0.1,
                      gain=0.22 if section(b) != "C" else 0.3)
        if section(b) == "C" and ch in ("Dm", "Gm"):
            for i, m in enumerate([62, 65] if ch == "Dm" else [62, 67]):
                s.add("choir", choir_note(rng, m, nb * bar + 1.5, "u", "o", attack=1.2, release=1.5),
                      b * bar, gain=0.22)
        b += nb
    # ---- low brass swells at the start of section D and the tag
    for b0 in (24, 32):
        n = ns(2 * bar + 0.5)
        t = tvec(n)
        env = dsp.env_points(n, [(0, 0), (1.4 * bar, 1.0), (2 * bar, 0.0)])
        br = np.zeros(n)
        for m in (38, 45, 50):
            f0 = float(dsp.midi_hz(m))
            for d in (-7, 0, 7):
                ph = np.cumsum(np.full(n, f0 * 2 ** (d / 1200.0))) / SR + rng.uniform()
                tabd = synth.saw_table(int(2000 / f0), 0.25)
                tabb = synth.saw_table(int(2000 / f0), 0.07)
                br += dsp.wt_read(tabd, ph) * (1 - env) + dsp.wt_read(tabb, ph) * env
        s.add("brass", dsp.normalize(br * env), b0 * bar, gain=0.3)
    # ---- a sparse bell at section heads ties it to the theme
    for b0, m in ((8, 74), (24, 69), (26, 72)):
        s.add("bell", bell_note(rng, m, 4.0), b0 * bar, pan=0.25, gain=0.2)
    ir = music_ir("Battle", (3.2, 2.6, 1.4))
    mix = s.mix({
        "ost": (0.75, 0.08, [("lp", 1100, 2), ("hp", 32, 2)]),
        "drums_odaiko": (0.7, 0.3, [("hp", 32, 2)]),
        "drums_taiko": (0.8, 0.22, [("hp", 35, 2)]),
        "drums_mid": (0.55, 0.22, [("lp", 3500, 2)]),
        "drums_frame": (0.32, 0.25, [("lp", 3000, 2), ("hp", 90, 2)]),
        "pad": (0.9, 0.4, [("lp", 900, 2), ("hp", 110, 2)]),
        "choir": (0.8, 0.5, [("hp", 180, 2), ("lp", 2500, 2)]),
        "brass": (0.9, 0.3, [("lp", 1300, 2), ("hp", 60, 2)]),
        "bell": (0.9, 0.6, [("hp", 300, 2)]),
    }, ir)
    # carve the 1-4 kHz band slightly so combat SFX read clearly on top
    mix = filt(mix, [("peak", 2200, 0.7, -3.0)], circular=True)
    return mix, TARGET_LUFS, bar


# ============================================================================ Training
def training(c):
    bpm = 80.0  # 36000 samples per beat
    beat = 60.0 / bpm
    bar = 4 * beat
    prog = ["Dm", "Bb", "Gm", "Dm", "Dm", "Bbmaj7", "Gm", "A", "Dm", "Eb", "Gm", "A"]
    voic = {"Dm": (38, [50, 53, 57]), "Bb": (34, [50, 53, 58]), "Gm": (31, [50, 55, 58]),
            "Bbmaj7": (34, [50, 53, 57]), "A": (33, [49, 52, 57]), "Eb": (39, [51, 55, 58])}
    s = Song("Training", len(prog) * 2 * bar)
    rng = s.rng
    kit = DrumKit("Training")
    for i, ch in enumerate(prog):
        t0 = i * 2 * bar
        root, pad = voic[ch]
        for m in pad:
            s.add("pad", pad_note(rng, m, 2 * bar + 2.5, attack=1.5, release=2.5, dark=0.55, bright=0.28,
                                  voices=3, detune=8, spread=0.6), t0 - 0.4, gain=0.22)
        s.add("bass", pad_note(rng, root, 2 * bar + 2.5, attack=1.2, release=2.5, dark=0.65, bright=0.35,
                               voices=2, detune=5, spread=0.2, sub=0.4), t0 - 0.4, gain=0.4)
        for bb in range(2):
            tb = t0 + bb * bar
            for q in range(4):
                v = [0.75, 0.45, 0.6, 0.45][q] * (1 + rng.uniform(-0.05, 0.05))
                s.add("ost", ostinato_note(rng, root, beat * 0.8, v, bright=0.6, sub=0.3), tb + q * beat)
            s.add("drums_taiko", kit.hit("taiko", 0.55 if bb == 0 else 0.4), tb)
            s.add("drums_frame", kit.hit("frame", 0.35), tb + 2 * beat, pan=0.25)
            s.add("drums_frame", kit.hit("frame", 0.18), tb + 2.5 * beat, pan=0.25)
        if i % 2 == 1 or i == 0:
            mm = {"Dm": 69, "Bb": 70, "Gm": 67, "Bbmaj7": 69, "A": 73, "Eb": 70}[ch]
            s.add("bell", bell_note(rng, mm, 4.5), t0 + rng.choice([1.0, 2.0, 3.0]) * beat,
                  pan=rng.uniform(-0.3, 0.3), gain=0.25)
    ir = music_ir("Training", (3.6, 3.0, 1.6))
    mix = s.mix({
        "pad": (1.0, 0.35, [("lp", 1800, 2), ("hp", 90, 2)]),
        "bass": (1.0, 0.12, [("lp", 700, 2)]),
        "ost": (0.55, 0.12, [("lp", 800, 2), ("hp", 32, 2)]),
        "drums_taiko": (0.6, 0.25, []),
        "drums_frame": (0.3, 0.3, [("lp", 2800, 2), ("hp", 90, 2)]),
        "bell": (1.0, 0.7, [("hp", 200, 2)]),
    }, ir)
    return mix, TARGET_LUFS, bar


def builders():
    return [("Theme", theme), ("Battle", battle), ("Training", training)]
