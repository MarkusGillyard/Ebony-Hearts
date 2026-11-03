"""Core DSP for the Ebony Hearts audio build. numpy only, fully deterministic.

Conventions
- Sample rate is SR (48 kHz). Mono signals are 1-D arrays, stereo signals are (n, 2).
- Static filters are RBJ biquads applied as their exact complex frequency response in the FFT
  domain (zero-padded for one-shots = linear filtering; unpadded for loops = steady-state
  circular filtering, which is exactly right for a periodic signal).
- Time-varying filtering of noise is done by STFT spectral shaping.
"""
import math
import zlib

import numpy as np

SR = 48000
TAU = 2.0 * math.pi


# ----------------------------------------------------------------------------- basics
def ns(sec):
    return int(round(sec * SR))


def tvec(n):
    return np.arange(n) / SR


def rng_for(name, salt=0):
    return np.random.default_rng((zlib.crc32(name.encode("utf-8")) * 2654435761 + salt) & 0xFFFFFFFFFFFF)


def db(x):
    return 20.0 * np.log10(np.maximum(np.abs(x), 1e-15))


def undb(d):
    return 10.0 ** (np.asarray(d, dtype=np.float64) / 20.0)


def midi_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=np.float64) - 69.0) / 12.0)


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.0


def peak(x):
    return float(np.max(np.abs(x))) if x.size else 0.0


def normalize(x, target=1.0):
    p = peak(x)
    return x * (target / p) if p > 0 else x


def fit(x, n):
    """Pad with zeros or cut to exactly n samples (axis 0)."""
    if len(x) >= n:
        return x[:n].copy()
    pad = [(0, n - len(x))] + [(0, 0)] * (x.ndim - 1)
    return np.pad(x, pad)


def place(buf, sig, start):
    """Add sig into buf at sample offset start (linear, clipped at the buffer ends)."""
    start = int(start)
    if start >= len(buf):
        return buf
    s0 = max(0, -start)
    s1 = min(len(sig), len(buf) - start)
    if s1 > s0:
        buf[start + s0:start + s1] += sig[s0:s1]
    return buf


def place_circ(buf, sig, start):
    """Add sig into buf at offset start, wrapping around the end (for seamless loops)."""
    n = len(buf)
    start = int(start) % n
    pos = 0
    while pos < len(sig):
        take = min(len(sig) - pos, n - start)
        buf[start:start + take] += sig[pos:pos + take]
        pos += take
        start = 0
    return buf


def pan(sig, p):
    """Constant-power pan, p in [-1, 1]. Returns (n, 2)."""
    a = (p + 1.0) * math.pi / 4.0
    return np.stack([sig * math.cos(a), sig * math.sin(a)], axis=1)


def fade(x, fade_in=0.0, fade_out=0.0):
    """Raised-cosine fades (seconds) applied in place on a copy."""
    y = x.copy()
    fi, fo = ns(fade_in), ns(fade_out)
    if fi > 0:
        w = 0.5 - 0.5 * np.cos(np.linspace(0.0, math.pi, fi))
        y[:fi] *= w if y.ndim == 1 else w[:, None]
    if fo > 0:
        w = 0.5 + 0.5 * np.cos(np.linspace(0.0, math.pi, fo))
        y[-fo:] *= w if y.ndim == 1 else w[:, None]
    return y


def trim_onset(x, thresh_db=-45.0, preroll=0.0005):
    """Drop leading near-silence (relative to the peak) but keep a short pre-roll."""
    a = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    p = a.max() if a.size else 0.0
    if p <= 0:
        return x
    idx = np.nonzero(a > p * 10 ** (thresh_db / 20.0))[0]
    if idx.size == 0:
        return x
    s = max(0, idx[0] - ns(preroll))
    return x[s:].copy()


def endfade(y, frac=0.25, max_s=0.03):
    """Raised-cosine fade over the end of a generated layer so truncation never clicks."""
    k = min(int(len(y) * frac), ns(max_s))
    if k > 1:
        w = 0.5 + 0.5 * np.cos(np.linspace(0.0, math.pi, k))
        y = y.copy()
        y[-k:] *= w if y.ndim == 1 else w[:, None]
    return y


def env_ad(n, attack, decay, curve=1.0):
    """Attack (linear-ish rise, seconds) then exponential decay with time constant `decay`."""
    t = tvec(n)
    a = np.clip(t / max(attack, 1e-6), 0.0, 1.0) ** curve
    return a * np.exp(-np.maximum(t - attack, 0.0) / max(decay, 1e-6))


def env_points(n, points):
    """Piecewise-linear envelope from [(time_s, value), ...]."""
    t = tvec(n)
    pts = np.asarray(points, dtype=np.float64)
    return np.interp(t, pts[:, 0], pts[:, 1])


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def softclip(x, drive=1.0):
    return np.tanh(drive * x) / math.tanh(drive)


# ----------------------------------------------------------------------------- noise
def white(rng, n, ch=None):
    return rng.standard_normal(n if ch is None else (n, ch))


def colored(rng, n, exponent=1.0, ch=None, lo=10.0):
    """Noise with power spectrum ~ 1/f^exponent (1 = pink, 2 = brown). Periodic over n, unit RMS."""
    w = white(rng, n, ch)
    X = np.fft.rfft(w, axis=0)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = 1.0 / np.maximum(f, lo) ** (exponent / 2.0)
    g[0] = 0.0
    X *= g if X.ndim == 1 else g[:, None]
    y = np.fft.irfft(X, n, axis=0)
    return y / (np.sqrt(np.mean(y * y, axis=0)) + 1e-15)


def lfo_noise(rng, n, cutoff_hz, ch=None):
    """Smooth random modulation signal (gaussian-lowpassed white noise), unit std, periodic over n."""
    w = white(rng, n, ch)
    X = np.fft.rfft(w, axis=0)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = np.exp(-0.5 * (f / max(cutoff_hz, 1e-6)) ** 2)
    g[0] = 0.0
    X *= g if X.ndim == 1 else g[:, None]
    y = np.fft.irfft(X, n, axis=0)
    return y / (np.std(y, axis=0) + 1e-15)


# ----------------------------------------------------------------------------- biquads
def biquad(kind, fc, q=0.7071, gain_db=0.0):
    fc = min(max(fc, 1.0), SR * 0.49)
    w0 = TAU * fc / SR
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2.0 * q)
    A = 10.0 ** (gain_db / 40.0)
    if kind == "lp":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "bp":
        b = [alpha, 0.0, -alpha]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "notch":
        b = [1.0, -2 * cw, 1.0]
        a = [1 + alpha, -2 * cw, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * A, -2 * cw, 1 - alpha * A]
        a = [1 + alpha / A, -2 * cw, 1 - alpha / A]
    elif kind == "ls":
        sA = 2 * math.sqrt(A) * alpha
        b = [A * ((A + 1) - (A - 1) * cw + sA), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sA)]
        a = [(A + 1) + (A - 1) * cw + sA, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sA]
    elif kind == "hs":
        sA = 2 * math.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * cw + sA), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sA)]
        a = [(A + 1) - (A - 1) * cw + sA, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sA]
    elif kind == "lp1":
        k = math.tan(w0 / 2)
        b = [k, k, 0.0]
        a = [1 + k, k - 1, 0.0]
    elif kind == "hp1":
        k = math.tan(w0 / 2)
        b = [1.0, -1.0, 0.0]
        a = [1 + k, k - 1, 0.0]
    else:
        raise ValueError(kind)
    a0 = a[0]
    return np.array(b) / a0, np.array(a) / a0


def butter_q(order):
    return [1.0 / (2.0 * math.cos((2 * k - 1) * math.pi / (2 * order))) for k in range(1, order // 2 + 1)]


def expand_stages(stages):
    """('lp', fc, order) / ('hp', fc, order) -> Butterworth cascades; others pass through.

    Stage forms: ('lp'|'hp', fc, order) with order 1..8, ('bp'|'notch', fc, q),
    ('peak', fc, q, gain_db), ('ls'|'hs', fc, gain_db[, q]).
    """
    out = []
    for st in stages:
        kind = st[0]
        if kind in ("lp", "hp"):
            fc = st[1]
            order = st[2] if len(st) > 2 else 2
            if order % 2:
                out.append(biquad(kind + "1", fc))
            for q in butter_q(order - (order % 2)) if order >= 2 else []:
                out.append(biquad(kind, fc, q))
        elif kind in ("bp", "notch"):
            out.append(biquad(kind, st[1], st[2]))
        elif kind == "peak":
            out.append(biquad("peak", st[1], st[2], st[3]))
        elif kind in ("ls", "hs"):
            out.append(biquad(kind, st[1], st[3] if len(st) > 3 else 0.7071, st[2]))
        else:
            raise ValueError(kind)
    return out


def response(stages, nfft):
    k = np.arange(nfft // 2 + 1)
    z1 = np.exp(-1j * TAU * k / nfft)
    z2 = z1 * z1
    H = np.ones(len(k), dtype=np.complex128)
    for b, a in expand_stages(stages):
        H *= (b[0] + b[1] * z1 + b[2] * z2) / (a[0] + a[1] * z1 + a[2] * z2)
    return H


def _next_fast(n):
    m = 1
    while m < n:
        m *= 2
    return m


def filt(x, stages, circular=False, tail=0.5):
    """Apply a cascade of biquads. Linear (zero-padded, output cut to len(x)) unless circular."""
    if not stages:
        return x.copy()
    n = len(x)
    nfft = n if circular else _next_fast(n + ns(tail))
    X = np.fft.rfft(x, nfft, axis=0)
    H = response(stages, nfft)
    X *= H if X.ndim == 1 else H[:, None]
    return np.fft.irfft(X, nfft, axis=0)[:n]


def mag_lp2(f, fc, q=0.7071):
    x = f / fc
    return 1.0 / np.sqrt((1 - x * x) ** 2 + (x / q) ** 2)


def mag_hp2(f, fc, q=0.7071):
    x = f / fc
    return x * x / np.sqrt((1 - x * x) ** 2 + (x / q) ** 2)


def mag_bp(f, fc, q=1.0):
    x = np.maximum(f, 1e-6) / fc
    return (x / q) / np.sqrt((1 - x * x) ** 2 + (x / q) ** 2)


def mag_lp(f, fc, order=2):
    return 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))


def mag_hp(f, fc, order=2):
    r = (np.maximum(f, 1e-6) / fc) ** (2 * order)
    return np.sqrt(r / (1.0 + r))


# ----------------------------------------------------------------------------- convolution
def fftconv(x, h):
    """Linear convolution (x and h 1-D, or x (n,ch) with h (m,) or (m,ch)). Output len(x)+len(h)-1."""
    n = len(x) + len(h) - 1
    nfft = _next_fast(n)
    X = np.fft.rfft(x, nfft, axis=0)
    Hh = np.fft.rfft(h, nfft, axis=0)
    if X.ndim == 2 and Hh.ndim == 1:
        Hh = Hh[:, None]
    if X.ndim == 1 and Hh.ndim == 2:
        X = X[:, None]
    return np.fft.irfft(X * Hh, nfft, axis=0)[:n]


def cconv(x, h):
    """Circular convolution with period len(x) (h shorter than x)."""
    n = len(x)
    X = np.fft.rfft(x, n, axis=0)
    Hh = np.fft.rfft(h, n, axis=0)
    if X.ndim == 2 and Hh.ndim == 1:
        Hh = Hh[:, None]
    if X.ndim == 1 and Hh.ndim == 2:
        X = X[:, None]
    return np.fft.irfft(X * Hh, n, axis=0)


# ----------------------------------------------------------------------------- STFT shaping
def stft_shape(x, gain_fn, nfft=1024, hop=256):
    """Multiply the STFT of x (1-D) by gain_fn(t[:,None], f[None,:]) and resynthesise (WOLA)."""
    n = len(x)
    assert nfft % hop == 0
    R = nfft // hop
    win = np.sqrt(0.5 - 0.5 * np.cos(TAU * np.arange(nfft) / nfft))
    pad = nfft
    total = pad + n + pad
    total += (-total) % hop
    xp = np.zeros(total)
    xp[pad:pad + n] = x
    nfr = (total - nfft) // hop + 1
    frames = np.lib.stride_tricks.sliding_window_view(xp, nfft)[::hop][:nfr] * win
    X = np.fft.rfft(frames, axis=1)
    del frames
    t = (np.arange(nfr) * hop + nfft / 2 - pad) / SR
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    G = gain_fn(t[:, None], f[None, :])
    X *= G
    del G
    Y = np.fft.irfft(X, nfft, axis=1)
    del X
    Y *= win
    blocks = np.zeros((nfr + R - 1, hop))
    wblocks = np.zeros((nfr + R - 1, hop))
    w2 = (win * win).reshape(R, hop)
    for r in range(R):
        blocks[r:r + nfr] += Y[:, r * hop:(r + 1) * hop]
        wblocks[r:r + nfr] += w2[r]
    out = blocks.ravel() / np.maximum(wblocks.ravel(), 1e-9)
    return out[pad:pad + n]


def shaped_noise(rng, n, gain_fn, exponent=0.0, nfft=1024, hop=256):
    src = white(rng, n) if exponent == 0 else colored(rng, n, exponent)
    return stft_shape(src, gain_fn, nfft, hop)


# ----------------------------------------------------------------------------- resampling
def resample(x, sr_in, sr_out):
    """FFT resampler (zero-padded so the ends do not wrap). Works on 1-D or (n, ch)."""
    if abs(sr_in - sr_out) < 1e-9:
        return x.copy()
    n = len(x)
    pad = 4096
    m = n + pad
    m_out = int(round(m * sr_out / sr_in))
    n_out = int(round(n * sr_out / sr_in))
    X = np.fft.rfft(x, m, axis=0)
    kout = m_out // 2 + 1
    Y = np.zeros((kout,) + X.shape[1:], dtype=np.complex128)
    k = min(len(X), kout)
    Y[:k] = X[:k]
    if kout < len(X):  # downsampling: taper the top 4 % of the kept band
        tw = max(1, int(k * 0.04))
        taper = 0.5 + 0.5 * np.cos(np.linspace(0, math.pi, tw))
        Y[k - tw:k] *= taper if Y.ndim == 1 else taper[:, None]
    y = np.fft.irfft(Y, m_out, axis=0) * (m_out / m)
    return y[:n_out]


# ----------------------------------------------------------------------------- oscillators
def phase_from_freq(freq, n=None, phase0=0.0):
    """Cycle phase (in cycles) from an instantaneous frequency (scalar or array)."""
    if np.isscalar(freq):
        return phase0 + freq * np.arange(n) / SR
    return phase0 + np.cumsum(freq) / SR


def sine(freq, n=None, phase0=0.0):
    return np.sin(TAU * phase_from_freq(freq, n, phase0))


def wavetable(harm_amps, size=4096, phases=None):
    """Single-cycle table from harmonic amplitudes (index 0 = fundamental)."""
    k = np.arange(1, len(harm_amps) + 1)
    ph = np.zeros(len(k)) if phases is None else phases
    x = np.arange(size) / size
    tab = np.zeros(size)
    for i in range(len(k)):
        if harm_amps[i] != 0.0:
            tab += harm_amps[i] * np.sin(TAU * k[i] * x + ph[i])
    return tab


def wt_read(table, phase_cycles):
    size = len(table)
    p = (phase_cycles % 1.0) * size
    i0 = np.floor(p).astype(np.int64)
    frac = p - i0
    i0 %= size
    i1 = (i0 + 1) % size
    return table[i0] * (1.0 - frac) + table[i1] * frac


def modal(n, partials, attack=0.0005, rng=None, doublet=0.0):
    """Sum of exponentially decaying sines: partials = [(freq, amp, tau_s), ...].

    doublet > 0 splits each partial into two (freq +- doublet/2 Hz) for a natural beating warble.
    """
    t = tvec(n)
    y = np.zeros(n)
    for i, (f, a, tau) in enumerate(partials):
        if f >= SR * 0.45:
            continue
        ph = 0.0 if rng is None else rng.uniform(0, 1)
        e = np.exp(-t / tau)
        if doublet > 0:
            d = doublet * (0.6 + 0.8 * (rng.uniform() if rng is not None else 0.5))
            y += a * e * 0.5 * (np.sin(TAU * ((f - d / 2) * t + ph)) + np.sin(TAU * ((f + d / 2) * t + ph + 0.13)))
        else:
            y += a * e * np.sin(TAU * (f * t + ph))
    if attack > 0:
        y *= np.clip(t / attack, 0, 1)
    return endfade(y)


# ----------------------------------------------------------------------------- reverb IRs
def make_ir(rng, length, rt_low, rt_mid, rt_high, predelay=0.01, early=(), stereo=False,
            corr=0.35, density_ramp=0.03, lp=9000.0):
    """Synthetic room impulse response.

    rt_*: RT60 (s) at ~100 Hz, ~1 kHz and ~8 kHz (interpolated in log frequency).
    early: list of (time_s, gain) discrete reflections (applied to both channels with jitter).
    stereo: (n, 2) with inter-channel correlation ~corr (keeps mono compatibility).
    The returned IR has unit energy per channel.
    """
    n = ns(length)
    lf = np.log10
    pts_f = np.array([lf(100.0), lf(1000.0), lf(8000.0)])
    pts_rt = np.array([rt_low, rt_mid, rt_high])

    def gain(t, f):
        rt = np.interp(lf(np.maximum(f, 20.0)), pts_f, pts_rt)
        tt = np.maximum(t - predelay, 0.0)
        g = np.exp(-6.907755 * tt / rt)
        g = g * smoothstep(tt / max(density_ramp, 1e-4)) * (t >= predelay)
        return g * mag_lp(f, lp, 2)

    chans = 2 if stereo else 1
    common = white(rng, n)
    out = []
    for c in range(chans):
        if stereo:
            src = math.sqrt(corr) * common + math.sqrt(1 - corr) * white(rng, n)
        else:
            src = common
        diff = stft_shape(src, gain, nfft=512, hop=128)
        er = np.zeros(n)
        for (te, ge) in early:
            jit = rng.uniform(-0.0012, 0.0012) if stereo else 0.0
            pos = ns(max(te + jit, 0.0))
            if pos < n:
                er[pos] += ge * (1 if rng.uniform() > 0.3 else -1)
        if early:
            er = filt(er, [("lp", 7000, 2)])
        ch = diff / (np.sqrt(np.sum(diff ** 2)) + 1e-15) + er
        out.append(ch)
    h = np.stack(out, axis=1) if stereo else out[0]
    e = np.sqrt(np.sum(h ** 2, axis=0))
    return h / e


# ----------------------------------------------------------------------------- measurement
_K1 = (np.array([1.53512485958697, -2.69169618940638, 1.19839281085285]),
       np.array([1.0, -1.69065929318241, 0.73248077421585]))
_K2 = (np.array([1.0, -2.0, 1.0]), np.array([1.0, -1.99004745483398, 0.99007225036621]))


def k_weight(x, circular=False):
    """ITU-R BS.1770 K-weighting (48 kHz coefficients) applied via the exact frequency response."""
    n = len(x)
    nfft = n if circular else _next_fast(n + SR)
    k = np.arange(nfft // 2 + 1)
    z1 = np.exp(-1j * TAU * k / nfft)
    z2 = z1 * z1
    H = np.ones(len(k), dtype=np.complex128)
    for b, a in (_K1, _K2):
        H *= (b[0] + b[1] * z1 + b[2] * z2) / (a[0] + a[1] * z1 + a[2] * z2)
    X = np.fft.rfft(x, nfft, axis=0)
    X *= H if X.ndim == 1 else H[:, None]
    y = np.fft.irfft(X, nfft, axis=0)
    return y if circular else y[:n + SR // 2]


def _block_powers(y, block, step):
    if y.ndim == 1:
        y = y[:, None]
    p = np.square(y)
    c = np.concatenate([np.zeros((1, p.shape[1])), np.cumsum(p, axis=0)], axis=0)
    starts = np.arange(0, len(y) - block + 1, step)
    if starts.size == 0:
        return np.zeros((0,))
    z = (c[starts + block] - c[starts]) / block
    return z.sum(axis=1)


def loudness_integrated(x, circular=False):
    """Gated integrated loudness (BS.1770-4 style), LUFS. circular=True for seamless loops."""
    y = k_weight(x, circular)
    if circular:  # wrap so blocks spanning the loop point are measured too
        y = np.concatenate([y, y[:ns(0.4)]], axis=0)
    z = _block_powers(y, ns(0.4), ns(0.1))
    if z.size == 0:
        return -math.inf
    lk = -0.691 + 10 * np.log10(np.maximum(z, 1e-20))
    z1 = z[lk > -70]
    if z1.size == 0:
        return -math.inf
    rel = -0.691 + 10 * np.log10(np.mean(z1)) - 10
    z2 = z[(lk > -70) & (lk > rel)]
    return float(-0.691 + 10 * np.log10(np.mean(z2)))


def loudness_momentary_max(x):
    pad = np.zeros((ns(0.4),) + x.shape[1:])
    y = k_weight(np.concatenate([pad, x, pad], axis=0))
    z = _block_powers(y, ns(0.4), ns(0.01))
    return float(-0.691 + 10 * np.log10(np.max(z) + 1e-20))


def true_peak(x, os=4, circular=False):
    """Peak of the 4x band-limited (FFT) interpolation, linear amplitude."""
    n = len(x)
    m = n if circular else n + 2048
    X = np.fft.rfft(x, m, axis=0)
    M = m * os
    Y = np.zeros((M // 2 + 1,) + X.shape[1:], dtype=np.complex128)
    Y[:len(X)] = X
    y = np.fft.irfft(Y, M, axis=0) * os
    return float(np.max(np.abs(y)))


def mono_drop_db(x):
    if x.ndim == 1:
        return 0.0
    st = np.sqrt(np.mean(np.square(x)))
    mid = 0.5 * (x[:, 0] + x[:, 1])
    return float(20 * np.log10(rms(mid) / (st + 1e-15) + 1e-15))


# ----------------------------------------------------------------------------- dynamics
def _sliding_min(g, w):
    """Exact sliding-window minimum over [i-w, i+w] using block decomposition (van Herk)."""
    n = len(g)
    size = 2 * w + 1
    padn = (-(n + 2 * w)) % size
    gp = np.concatenate([np.ones(w), g, np.ones(w + padn)])
    blocks = gp.reshape(-1, size)
    pre = np.minimum.accumulate(blocks, axis=1).ravel()
    suf = np.minimum.accumulate(blocks[:, ::-1], axis=1)[:, ::-1].ravel()
    i = np.arange(n)
    return np.minimum(suf[i], pre[i + 2 * w])


def limit(x, ceiling, window=0.004, circular=False):
    """Zero-phase look-ahead peak limiter: gain never exceeds what keeps |x| <= ceiling."""
    a = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=1)
    greq = np.minimum(1.0, ceiling / np.maximum(a, 1e-12))
    if greq.min() >= 1.0:
        return x.copy(), 0.0
    w = ns(window)
    if circular:
        ext = np.concatenate([greq[-2 * w:], greq, greq[:2 * w]])
        gmin = _sliding_min(ext, w)
        k = np.ones(w + 1) / (w + 1)
        gs = np.convolve(gmin, k, mode="same")[2 * w:-2 * w]
    else:
        gmin = _sliding_min(greq, w)
        k = np.ones(w + 1) / (w + 1)
        gs = np.convolve(np.concatenate([np.ones(w), gmin, np.ones(w)]), k, mode="same")[w:-w]
    gs = np.minimum(gs, 1.0)
    y = x * (gs if x.ndim == 1 else gs[:, None])
    return y, float(-db(gs.min()))
