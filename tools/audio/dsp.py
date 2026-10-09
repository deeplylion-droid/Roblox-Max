"""
Mattoni DSP riutilizzabili della pipeline audio di SPLASHLAND IS CLOSED! (solo numpy + scipy, nessun campione esterno).

Convenzioni:
  - frequenza di campionamento SR = 48000 Hz, segnali float64 nominalmente in [-1, 1];
  - mono = array 1-D (n,), stereo = array 2-D (2, n) (i canali sulla prima dimensione);
  - i tempi nelle API sono in secondi, le frequenze in Hz;
  - i loop si costruiscono in modo "circolare": eventi, filtri e riverberi che escono dalla fine
    rientrano dall'inizio, così il punto di loop è continuo per costruzione (niente dissolvenze).
"""
from __future__ import annotations

import zlib

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

SR = 48000
NYQ = SR / 2
TWO_PI = 2.0 * np.pi


# ───────────────────────── basi ─────────────────────────

def ns(dur: float) -> int:
    """Secondi → numero di campioni."""
    return int(round(dur * SR))


def tvec(n: int) -> np.ndarray:
    return np.arange(n) / SR


def db_to_lin(d):
    return 10.0 ** (np.asarray(d, dtype=float) / 20.0)


def lin_to_db(x):
    return 20.0 * np.log10(np.maximum(np.abs(x), 1e-12))


def cents(c):
    """Rapporto di frequenza corrispondente a c centesimi."""
    return 2.0 ** (np.asarray(c, dtype=float) / 1200.0)


def midi_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def rng_for(key: str, salt: int = 0) -> np.random.Generator:
    """Generatore deterministico derivato da una chiave testuale (di solito l'id del suono)."""
    return np.random.default_rng([zlib.crc32(key.encode('utf-8')), salt])


def stereo(x: np.ndarray) -> np.ndarray:
    """Mono → stereo centrato (lascia invariato uno stereo)."""
    return x if x.ndim == 2 else np.stack([x, x])


def mono(x: np.ndarray) -> np.ndarray:
    return x if x.ndim == 1 else x.mean(axis=0)


def normalize(x: np.ndarray, peak: float = 1.0) -> np.ndarray:
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.0


# ───────────────────────── curve e inviluppi ─────────────────────────

def interp_cos(t, ts, vs):
    """Interpolazione a tratti con raccordo cosinusoidale (derivata nulla nei punti)."""
    ts = np.asarray(ts, dtype=float)
    vs = np.asarray(vs, dtype=float)
    if len(ts) == 1:
        return np.full_like(np.asarray(t, dtype=float), vs[0])
    i = np.clip(np.searchsorted(ts, t, side='right') - 1, 0, len(ts) - 2)
    span = np.maximum(ts[i + 1] - ts[i], 1e-12)
    u = np.clip((t - ts[i]) / span, 0.0, 1.0)
    w = 0.5 - 0.5 * np.cos(np.pi * u)
    return vs[i] + (vs[i + 1] - vs[i]) * w


def curve(n: int, pts, kind: str = 'cos') -> np.ndarray:
    """Curva per campione da punti (t_s, valore). kind: 'cos', 'lin' o 'log' (interpolazione geometrica)."""
    t = tvec(n)
    ts = [p[0] for p in pts]
    vs = [p[1] for p in pts]
    if kind == 'lin':
        return np.interp(t, ts, vs)
    if kind == 'log':
        return np.exp(interp_cos(t, ts, np.log(np.maximum(vs, 1e-9))))
    return interp_cos(t, ts, vs)


def exp_env(n: int, t60: float, attack: float = 0.0005, delay: float = 0.0) -> np.ndarray:
    """Attacco lineare breve + decadimento esponenziale (t60 = tempo per scendere di 60 dB)."""
    t = tvec(n) - delay
    env = np.exp(-6.907755 * np.maximum(t, 0.0) / max(t60, 1e-6))
    if attack > 0:
        env *= np.clip(t / attack, 0.0, 1.0)
    else:
        env *= (t >= 0)
    return env


def fade(x: np.ndarray, fin: float = 0.0, fout: float = 0.0) -> np.ndarray:
    """Dissolvenze a coseno rialzato in testa e in coda."""
    y = x.copy()
    n = y.shape[-1]
    a = min(ns(fin), n)
    b = min(ns(fout), n)
    if a > 0:
        y[..., :a] *= 0.5 - 0.5 * np.cos(np.pi * (np.arange(a) + 0.5) / a)
    if b > 0:
        y[..., n - b:] *= 0.5 + 0.5 * np.cos(np.pi * (np.arange(b) + 0.5) / b)
    return y


def gate_env(n: int, t0: float, t1: float, att: float = 0.005, rel: float = 0.01) -> np.ndarray:
    """Inviluppo trapezoidale (raccordi a coseno) acceso fra t0 e t1."""
    return curve(n, [(0, 0), (t0, 0), (t0 + att, 1), (max(t1, t0 + att), 1), (max(t1, t0 + att) + rel, 0)])


# ───────────────────────── rumore e curve casuali ─────────────────────────

def spectral_noise(n: int, rng: np.random.Generator, gain_fn=None, exponent: float = 0.0) -> np.ndarray:
    """Rumore costruito nel dominio della frequenza (dunque periodico su n campioni), varianza unitaria.
    Spettro di potenza ∝ 1/f^exponent, moltiplicato in ampiezza per gain_fn(f) se fornito."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = np.ones_like(f)
    if exponent:
        g = np.maximum(f, 1.0) ** (-exponent / 2.0)
    if gain_fn is not None:
        g = g * gain_fn(f)
    g[0] = 0.0
    x = np.fft.irfft(spec * g, n)
    s = np.std(x)
    return x / s if s > 0 else x


def pink(n, rng):
    return spectral_noise(n, rng, exponent=1.0)


def brown(n, rng):
    return spectral_noise(n, rng, exponent=2.0)


def rand_curve(n: int, rate: float, rng: np.random.Generator) -> np.ndarray:
    """Curva casuale liscia (deviazione standard 1) con banda ~rate Hz; periodica su n campioni."""
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = np.exp(-0.5 * (f / max(rate, 1e-6)) ** 2)
    g[0] = 0.0
    if len(g) > 2:
        g[1] = max(g[1], 0.05)      # anche per curve brevissime resta almeno un'oscillazione
    x = np.fft.irfft(spec * g, n)
    s = np.std(x)
    return x / s if s > 0 else x


def hold_noise(n: int, rate: float, rng: np.random.Generator) -> np.ndarray:
    """Rumore campiona-e-tieni (gradini casuali a ~rate Hz), deviazione standard 1."""
    step = max(1, int(SR / rate))
    k = n // step + 2
    v = rng.standard_normal(k)
    return np.repeat(v, step)[:n]


def poisson_times(rng, rate, t0: float, t1: float) -> np.ndarray:
    """Istanti di un processo di Poisson; rate può essere costante o una funzione del tempo (s → eventi/s)."""
    if t1 <= t0:
        return np.zeros(0)
    if callable(rate):
        tt = np.linspace(t0, t1, 512)
        rmax = float(np.max(rate(tt))) * 1.05 + 1e-9
        k = rng.poisson(rmax * (t1 - t0))
        cand = np.sort(rng.uniform(t0, t1, k))
        keep = rng.uniform(0, rmax, k) < rate(cand)
        return cand[keep]
    k = rng.poisson(rate * (t1 - t0))
    return np.sort(rng.uniform(t0, t1, k))


# ───────────────────────── filtri ─────────────────────────

def bw_lp(f, fc, order=2):
    """Modulo di un passa-basso di Butterworth (per i filtri spettrali)."""
    return 1.0 / np.sqrt(1.0 + (np.asarray(f) / fc) ** (2 * order))


def bw_hp(f, fc, order=2):
    f = np.maximum(np.asarray(f, dtype=float), 1e-9)
    return 1.0 / np.sqrt(1.0 + (fc / f) ** (2 * order))


def bw_bp(f, lo, hi, order=2):
    return bw_hp(f, lo, order) * bw_lp(f, hi, order)


def peak_shape(f, fc, q, gain):
    """Picco risonante moltiplicativo (1 lontano da fc, `gain` in fc)."""
    f = np.maximum(np.asarray(f, dtype=float), 1e-9)
    return 1.0 + (gain - 1.0) / (1.0 + (q * (f / fc - fc / f)) ** 2)


def fft_filter(x: np.ndarray, gain_fn) -> np.ndarray:
    """Filtro a fase zero e circolare: moltiplica lo spettro per gain_fn(f)."""
    n = x.shape[-1]
    X = np.fft.rfft(x, axis=-1)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    return np.fft.irfft(X * gain_fn(f), n, axis=-1)


def _sos(kind, fc, order):
    if kind == 'bandpass':
        lo, hi = fc
        return signal.butter(order, [max(lo, 1.0), min(hi, NYQ * 0.98)], btype='bandpass', fs=SR, output='sos')
    return signal.butter(order, min(fc, NYQ * 0.98), btype=kind, fs=SR, output='sos')


def lowpass(x, fc, order=2):
    return signal.sosfilt(_sos('lowpass', fc, order), x, axis=-1)


def highpass(x, fc, order=2):
    return signal.sosfilt(_sos('highpass', fc, order), x, axis=-1)


def bandpass(x, lo, hi, order=2):
    return signal.sosfilt(_sos('bandpass', (lo, hi), order), x, axis=-1)


def rbj(kind: str, f: float, q: float = 0.7071, gain_db: float = 0.0):
    """Biquad del 'cookbook' di R. Bristow-Johnson. kind: peak, bandpass (0 dB), notch,
    lowpass, highpass, lowshelf, highshelf."""
    A = 10.0 ** (gain_db / 40.0)
    w = TWO_PI * min(f, NYQ * 0.98) / SR
    cw, sw = np.cos(w), np.sin(w)
    al = sw / (2.0 * q)
    sA = np.sqrt(A)
    if kind == 'peak':
        b = [1 + al * A, -2 * cw, 1 - al * A]
        a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == 'bandpass':
        b = [al, 0.0, -al]
        a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'notch':
        b = [1.0, -2 * cw, 1.0]
        a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'lowpass':
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
        a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'highpass':
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        a = [1 + al, -2 * cw, 1 - al]
    elif kind == 'lowshelf':
        b = [A * ((A + 1) - (A - 1) * cw + 2 * sA * al), 2 * A * ((A - 1) - (A + 1) * cw),
             A * ((A + 1) - (A - 1) * cw - 2 * sA * al)]
        a = [(A + 1) + (A - 1) * cw + 2 * sA * al, -2 * ((A - 1) + (A + 1) * cw),
             (A + 1) + (A - 1) * cw - 2 * sA * al]
    elif kind == 'highshelf':
        b = [A * ((A + 1) + (A - 1) * cw + 2 * sA * al), -2 * A * ((A - 1) + (A + 1) * cw),
             A * ((A + 1) + (A - 1) * cw - 2 * sA * al)]
        a = [(A + 1) - (A - 1) * cw + 2 * sA * al, 2 * ((A - 1) - (A + 1) * cw),
             (A + 1) - (A - 1) * cw - 2 * sA * al]
    else:
        raise ValueError(kind)
    b = np.asarray(b) / a[0]
    a = np.asarray(a) / a[0]
    return b, a


def eq(x, kind, f, q=0.7071, gain_db=0.0):
    b, a = rbj(kind, f, q, gain_db)
    return signal.lfilter(b, a, x, axis=-1)


def resonate(x, f, q, gain=1.0):
    """Passa-banda risonante a guadagno unitario sul picco."""
    return gain * eq(x, 'bandpass', f, q)


def circular(fn, x: np.ndarray, pad: float | None = 2.0) -> np.ndarray:
    """Applica un'elaborazione `fn` (filtro, saturazione sovracampionata...) a un segnale periodico
    in regime stazionario: elabora [coda | x | testa] e tiene la parte centrale (il loop resta continuo)."""
    n = x.shape[-1]
    p = n if pad is None else min(ns(pad), n)
    y = fn(np.concatenate([x[..., n - p:], x, x[..., :p]], axis=-1))
    return y[..., p:p + n]


def tv_biquad(x, b0, b1, b2, a1, a2, block: int = 32) -> np.ndarray:
    """Biquad tempo-variante a blocchi: coefficienti per blocco (array lunghi ceil(n/block)).
    A ogni cambio di coefficienti lo stato viene ricostruito dagli ultimi campioni (forma diretta I),
    quindi le variazioni non producono transitori."""
    n = len(x)
    y = np.empty(n)
    x1 = x2 = y1 = y2 = 0.0
    nb = (n + block - 1) // block
    lf = signal.lfilter
    for i in range(nb):
        s = i * block
        e = min(n, s + block)
        B0, B1, B2, A1, A2 = b0[i], b1[i], b2[i], a1[i], a2[i]
        zi = np.array([B1 * x1 + B2 * x2 - A1 * y1 - A2 * y2, B2 * x1 - A2 * y1])
        yb, _ = lf((B0, B1, B2), (1.0, A1, A2), x[s:e], zi=zi)
        y[s:e] = yb
        if e - s >= 2:
            x1, x2, y1, y2 = x[e - 1], x[e - 2], yb[-1], yb[-2]
        else:
            x2, x1, y2, y1 = x1, x[e - 1], y1, yb[-1]
    return y


def _block_idx(n, block):
    return np.minimum(np.arange(0, n, block) + block // 2, n - 1)


def reson_coefs(f, bw):
    """Risonatore a due poli di Klatt (guadagno unitario in continua): usato in cascata per le formanti."""
    f = np.asarray(f, dtype=float)
    r = np.exp(-np.pi * np.asarray(bw, dtype=float) / SR)
    a1 = -2.0 * r * np.cos(TWO_PI * f / SR)
    a2 = r * r
    b0 = 1.0 + a1 + a2
    z = np.zeros_like(b0)
    return b0, z, z, a1, a2


def bp_coefs(f, bw):
    """Passa-banda RBJ a 0 dB di picco (per filtri paralleli tempo-varianti)."""
    f = np.minimum(np.asarray(f, dtype=float), NYQ * 0.95)
    w = TWO_PI * f / SR
    q = f / np.maximum(np.asarray(bw, dtype=float), 1.0)
    al = np.sin(w) / (2.0 * q)
    a0 = 1.0 + al
    z = np.zeros_like(a0)
    return al / a0, z, -al / a0, -2.0 * np.cos(w) / a0, (1.0 - al) / a0


def tv_bandpass(x, f, bw, block=32):
    """Passa-banda con centro f(t) e banda bw(t) variabili (array per campione o scalari)."""
    n = len(x)
    idx = _block_idx(n, block)
    f = np.broadcast_to(np.asarray(f, dtype=float), (n,))[idx]
    bw = np.broadcast_to(np.asarray(bw, dtype=float), (n,))[idx]
    return tv_biquad(x, *bp_coefs(f, bw), block=block)


def tv_lowpass(x, fc, q=0.7071, block=32):
    """Passa-basso risonante con taglio fc(t) variabile."""
    n = len(x)
    idx = _block_idx(n, block)
    fc = np.minimum(np.broadcast_to(np.asarray(fc, dtype=float), (n,))[idx], NYQ * 0.95)
    w = TWO_PI * fc / SR
    cw = np.cos(w)
    al = np.sin(w) / (2 * q)
    a0 = 1 + al
    return tv_biquad(x, (1 - cw) / 2 / a0, (1 - cw) / a0, (1 - cw) / 2 / a0, -2 * cw / a0, (1 - al) / a0, block)


def formant_cascade(x, F, B, block: int = 32) -> np.ndarray:
    """Cascata di risonatori tempo-varianti (sintesi a formanti alla Klatt). F, B: (k, n)."""
    n = len(x)
    idx = _block_idx(n, block)
    y = x
    for k in range(F.shape[0]):
        y = tv_biquad(y, *reson_coefs(F[k, idx], B[k, idx]), block=block)
    return y


def formant_parallel(x, F, B, gains, block: int = 32) -> np.ndarray:
    """Banco parallelo di passa-banda tempo-varianti (per rumori 'vocalici', fricative, soffi)."""
    n = len(x)
    idx = _block_idx(n, block)
    y = np.zeros(n)
    for k in range(F.shape[0]):
        if gains[k] == 0:
            continue
        y += gains[k] * tv_biquad(x, *bp_coefs(F[k, idx], B[k, idx]), block=block)
    return y


def modal(x, freqs, t60s, gains=None) -> np.ndarray:
    """Banco di modi risonanti (sintesi modale): ogni modo è un seno smorzato eccitato da x.
    La risposta all'impulso unitario di ogni modo è r^n sin(wn) (ampiezza 1)."""
    y = np.zeros(x.shape)
    gains = np.ones(len(freqs)) if gains is None else gains
    for f, T, g in zip(freqs, t60s, gains):
        if f <= 0 or f >= NYQ * 0.95 or g == 0:
            continue
        r = 10.0 ** (-3.0 / (max(T, 1e-4) * SR))
        w = TWO_PI * f / SR
        y += g * signal.lfilter([0.0, r * np.sin(w)], [1.0, -2.0 * r * np.cos(w), r * r], x, axis=-1)
    return y


def comb(x, delay: float, g: float) -> np.ndarray:
    """Filtro a pettine in retroazione (ritardo fisso e breve): risonanze 'metalliche' o 'tubo'."""
    d = max(1, int(round(delay * SR)))
    a = np.zeros(d + 1)
    a[0] = 1.0
    a[d] = -g
    return signal.lfilter([1.0 - abs(g)], a, x, axis=-1)


# ───────────────────────── ritardi modulati, tempo ─────────────────────────

def frac_read(x: np.ndarray, pos: np.ndarray, wrap: bool = False) -> np.ndarray:
    """Lettura a posizione frazionaria con interpolazione cubica (Catmull-Rom)."""
    n = x.shape[-1]
    i = np.floor(pos).astype(np.int64)
    u = pos - i
    if wrap:
        im1, i0, i1, i2 = (i - 1) % n, i % n, (i + 1) % n, (i + 2) % n
        xm1, x0, x1, x2 = x[..., im1], x[..., i0], x[..., i1], x[..., i2]
    else:
        xp = np.concatenate([np.zeros(x.shape[:-1] + (2,)), x, np.zeros(x.shape[:-1] + (3,))], axis=-1)
        j = np.clip(i, -2, n) + 2
        xm1, x0, x1, x2 = xp[..., j - 1 + 0], xp[..., j], xp[..., j + 1], xp[..., j + 2]
    c0 = x0
    c1 = 0.5 * (x1 - xm1)
    c2 = xm1 - 2.5 * x0 + 2.0 * x1 - 0.5 * x2
    c3 = 0.5 * (x2 - xm1) + 1.5 * (x0 - x1)
    return ((c3 * u + c2) * u + c1) * u + c0


def mod_delay(x: np.ndarray, d: np.ndarray, wrap: bool = False) -> np.ndarray:
    """y[n] = x[n - d[n]] con d in campioni (frazionario)."""
    n = x.shape[-1]
    return frac_read(x, np.arange(n) - d, wrap)


def flanger(x, rng, base_ms=1.6, depth_ms=0.7, rate=0.8, mix=0.6, wrap=False):
    """Pettine in avanti con ritardo che vaga lentamente: colorazione 'acquosa'/'bagnata'."""
    n = x.shape[-1]
    d = (base_ms + depth_ms * np.tanh(rand_curve(n, rate, rng))) * 1e-3 * SR
    return x + mix * mod_delay(x, d, wrap)


def time_warp(x: np.ndarray, ratio: np.ndarray, circular: bool = True) -> np.ndarray:
    """Lettura a velocità variabile (wow/flutter di un nastro). ratio = velocità istantanea.
    Per i loop la media di ratio viene forzata a 1: la posizione di lettura resta periodica."""
    n = x.shape[-1]
    if circular:
        ratio = ratio * (n / np.sum(ratio))
    pos = np.concatenate([[0.0], np.cumsum(ratio)[:-1]])
    return frac_read(x, pos, wrap=circular)


# ───────────────────────── oscillatori ─────────────────────────

def phase_of(freq) -> np.ndarray:
    """Fase in cicli dall'integrale della frequenza istantanea."""
    return np.cumsum(freq) / SR


def osc(freq, phase0: float = 0.0) -> np.ndarray:
    return np.sin(TWO_PI * (phase_of(freq) + phase0))


def periodic_freq(freq: np.ndarray) -> np.ndarray:
    """Riscala leggermente una curva di frequenza perché faccia un numero intero di cicli
    nella lunghezza del segnale (fase continua al punto di loop)."""
    tot = np.sum(freq) / SR
    k = max(1, round(tot))
    return freq * (k / tot)


def additive(f0, amps, n_harm: int | None = None, phases=None) -> np.ndarray:
    """Somma di armoniche di una fondamentale variabile f0 (array), limitate sotto Nyquist.
    amps: lista di ampiezze o funzione k → ampiezza."""
    f0 = np.asarray(f0, dtype=float)
    ph = phase_of(f0)
    fmax = np.max(f0)
    K = n_harm or int(NYQ * 0.9 / max(fmax, 1.0))
    y = np.zeros_like(f0)
    for k in range(1, K + 1):
        a = amps(k) if callable(amps) else (amps[k - 1] if k - 1 < len(amps) else 0.0)
        if a == 0:
            continue
        # attenuazione dolce vicino a Nyquist (niente aliasing)
        lim = np.clip((NYQ * 0.92 - k * f0) / (NYQ * 0.08), 0.0, 1.0)
        p0 = 0.0 if phases is None else phases[k - 1]
        y += a * lim * np.sin(TWO_PI * (k * ph + p0))
    return y


def partials(n: int, freqs, amps, t60s, phases=None, attack: float = 0.0005) -> np.ndarray:
    """Somma di parziali sinusoidali che decadono indipendentemente (sintesi di oggetti percossi)."""
    t = tvec(n)
    y = np.zeros(n)
    for i, (f, a, T) in enumerate(zip(freqs, amps, t60s)):
        if f >= NYQ * 0.95 or a == 0:
            continue
        p = 0.0 if phases is None else phases[i]
        y += a * np.sin(TWO_PI * f * t + p) * np.exp(-6.907755 * t / T)
    if attack > 0:
        y *= np.clip(t / attack, 0, 1)
    return y


# ───────────────────────── voce: sorgente glottale e formanti ─────────────────────────

def glottal(f0, rng, oq=0.6, sq=2.5, jitter=0.01, shimmer=0.05, sub=0.0, os: int = 4):
    """Sorgente glottale col modello di Rosenberg, calcolata sovracampionata (niente aliasing).
    f0: array per campione. jitter/shimmer: perturbazioni casuali per ciclo (frazioni).
    sub: alternanza di ampiezza fra cicli pari e dispari (diplofonia → subarmonica f0/2, voce roca).
    oq e sub possono essere array per campione. Restituisce (eccitazione = derivata del flusso, flusso)."""
    f0 = np.asarray(f0, dtype=float)
    n = len(f0)
    m = n * os
    tt = (np.arange(m) + 0.5) / os - 0.5
    src_t = np.arange(n)
    fo = np.interp(tt, src_t, f0)
    ph0 = np.cumsum(fo) / (SR * os)
    ncyc = int(ph0[-1]) + 3
    jit = 1.0 + jitter * np.clip(rng.standard_normal(ncyc), -2.5, 2.5)
    fo = fo * jit[ph0.astype(np.int64)]
    ph = np.cumsum(fo) / (SR * os)
    cyc = ph.astype(np.int64)
    fr = ph - cyc
    oq_a = np.interp(tt, src_t, np.broadcast_to(np.asarray(oq, dtype=float), (n,)))
    tp = oq_a * sq / (1.0 + sq)
    tn = oq_a / (1.0 + sq)
    g = np.where(fr < tp, 0.5 * (1.0 - np.cos(np.pi * fr / tp)),
                 np.where(fr < tp + tn, np.cos(np.pi * (fr - tp) / (2.0 * tn)), 0.0))
    amp = np.maximum(1.0 + shimmer * np.clip(rng.standard_normal(ncyc + 2), -2.5, 2.5), 0.05)
    g = g * amp[cyc]
    if np.any(np.asarray(sub) != 0):
        sub_a = np.interp(tt, src_t, np.broadcast_to(np.asarray(sub, dtype=float), (n,)))
        g = g * (1.0 - sub_a * (cyc % 2))
    d = np.diff(g, prepend=0.0) * (SR * os) / np.maximum(fo, 1.0)
    exc = signal.resample_poly(d, 1, os)[:n]
    flow = signal.resample_poly(g, 1, os)[:n]
    return exc, flow


def aspiration(flow: np.ndarray, rng, base: float = 0.35) -> np.ndarray:
    """Rumore di soffio modulato dal flusso glottale (rumore 'pulsante' come nella voce reale)."""
    nz = highpass(rng.standard_normal(len(flow)), 300.0)
    fl = flow / (np.max(np.abs(flow)) + 1e-9)
    return nz * (base + (1.0 - base) * np.clip(fl, 0, 1))


# formanti indicative di voce maschile adulta (Hz) e larghezze di banda
VOWELS = {
    'a':  ((760, 1260, 2500, 3500, 4400), (90, 100, 130, 200, 260)),
    'e':  ((430, 1950, 2550, 3450, 4400), (70, 100, 140, 200, 260)),
    'E':  ((580, 1750, 2500, 3450, 4400), (80, 100, 140, 200, 260)),
    'i':  ((290, 2250, 2950, 3600, 4400), (60, 100, 150, 200, 260)),
    'o':  ((470, 880, 2450, 3400, 4400), (80, 90, 130, 200, 260)),
    'O':  ((590, 960, 2500, 3400, 4400), (80, 90, 130, 200, 260)),
    'u':  ((320, 760, 2350, 3350, 4300), (70, 80, 130, 200, 260)),
    '@':  ((500, 1450, 2500, 3450, 4400), (80, 100, 140, 200, 260)),
    'ae': ((690, 1700, 2450, 3450, 4400), (90, 110, 140, 200, 260)),
    'n':  ((270, 1550, 2600, 3400, 4300), (60, 300, 300, 350, 400)),
    'm':  ((250, 1100, 2400, 3300, 4300), (60, 300, 300, 350, 400)),
    'ny': ((260, 2000, 2700, 3500, 4300), (60, 250, 300, 350, 400)),
    'l':  ((360, 1100, 2700, 3400, 4300), (70, 120, 160, 250, 300)),
    'r':  ((450, 1300, 1700, 3300, 4300), (90, 120, 160, 250, 300)),
}


def formant_track(n: int, keys, scale=1.0, bw_scale=1.0):
    """Tracce delle formanti per campione da chiavi [(t_s, vocale), ...] (raccordi a coseno).
    scale: moltiplica tutte le formanti (tratto vocale più corto > 1, più lungo < 1); può essere un array."""
    t = tvec(n)
    ts = [k[0] for k in keys]
    Fs = np.array([VOWELS[k[1]][0] for k in keys], dtype=float)
    Bs = np.array([VOWELS[k[1]][1] for k in keys], dtype=float)
    F = np.stack([interp_cos(t, ts, Fs[:, j]) for j in range(Fs.shape[1])])
    B = np.stack([interp_cos(t, ts, Bs[:, j]) for j in range(Bs.shape[1])])
    F = np.minimum(F * scale, NYQ * 0.9)
    return F, B * bw_scale


def voice(f0, F, B, rng, amp=None, oq=0.6, sq=2.5, jitter=0.01, shimmer=0.05, sub=0.0,
          breath=0.08, breath_base=0.35, n_formants: int | None = None):
    """Voce a formanti: sorgente glottale + soffio pulsante filtrati dalla cascata di formanti."""
    exc, flow = glottal(f0, rng, oq=oq, sq=sq, jitter=jitter, shimmer=shimmer, sub=sub)
    exc = exc / (np.max(np.abs(exc)) + 1e-9)
    src = exc + breath * aspiration(flow, rng, breath_base)
    if amp is not None:
        src = src * amp
    k = n_formants or F.shape[0]
    return formant_cascade(src, F[:k], B[:k])


# ───────────────────────── spazio: panorama, riverberi ─────────────────────────

def pan(x: np.ndarray, p: float, itd: float = 0.0004) -> np.ndarray:
    """Panorama a potenza costante (p in [-1, 1]) + piccolo ritardo interaurale."""
    p = float(np.clip(p, -1, 1))
    th = (p + 1.0) * np.pi / 4.0
    L = x * np.cos(th)
    R = x * np.sin(th)
    d = int(round(abs(p) * itd * SR))
    if d > 0:
        if p > 0:
            L = np.concatenate([np.zeros(d), L[:-d]])
        else:
            R = np.concatenate([np.zeros(d), R[:-d]])
    return np.stack([L, R])


def place(buf: np.ndarray, x: np.ndarray, t0: float, gain: float = 1.0, wrap: bool = False) -> None:
    """Somma x dentro buf a partire dal tempo t0 (s). Con wrap=True ciò che esce dalla fine rientra
    dall'inizio (composizione circolare dei loop). Un x mono in un buf stereo va al centro."""
    if x.ndim == 1 and buf.ndim == 2:
        x = np.stack([x, x]) * np.sqrt(0.5)
    n = buf.shape[-1]
    m = x.shape[-1]
    i0 = int(round(t0 * SR))
    if wrap:
        pos = 0
        i0 %= n
        while pos < m:
            s = (i0 + pos) % n
            take = min(m - pos, n - s)
            buf[..., s:s + take] += gain * x[..., pos:pos + take]
            pos += take
        return
    if i0 < 0:
        x = x[..., -i0:]
        i0 = 0
    take = min(x.shape[-1], n - i0)
    if take > 0:
        buf[..., i0:i0 + take] += gain * x[..., :take]


def reverb_ir(rt60: float, rng, dur: float | None = None, lo: float = 1.3, hi: float = 0.35,
              predelay: float = 0.0, attack: float = 0.008, early=(), stereo_out: bool = True,
              sparse: float = 0.0, lp: float | None = None) -> np.ndarray:
    """Risposta all'impulso sintetica: rumore in bande d'ottava che decadono con T60 diversi
    (lo = moltiplicatore del T60 sui bassi, hi = sugli acuti), coda che si costruisce in `attack` s,
    riflessioni discrete `early` = [(t_s, guadagno, pan), ...], e "granulosità" iniziale `sparse`
    (0 = coda densa, 1 = eco rade che si infittiscono: spazi aperti). Energia normalizzata a 1."""
    dur = dur or min(rt60 * 1.1 + predelay, 10.0)
    n = ns(dur)
    t = tvec(n)
    centers = np.array([63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000], dtype=float)
    mult = np.where(centers <= 1000,
                    np.interp(np.log2(centers), np.log2([125, 1000]), [lo, 1.0]),
                    np.interp(np.log2(centers), np.log2([1000, 8000]), [1.0, hi]))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    lf = np.log2(np.maximum(f, 1.0))
    lc = np.log2(centers)
    masks = []
    for k in range(len(centers)):
        m = np.zeros_like(f)
        if k > 0:
            sel = (lf >= lc[k - 1]) & (lf <= lc[k])
            m[sel] = 0.5 - 0.5 * np.cos(np.pi * (lf[sel] - lc[k - 1]) / (lc[k] - lc[k - 1]))
        else:
            m[lf <= lc[0]] = 1.0
        if k < len(centers) - 1:
            sel = (lf > lc[k]) & (lf <= lc[k + 1])
            m[sel] = 0.5 + 0.5 * np.cos(np.pi * (lf[sel] - lc[k]) / (lc[k + 1] - lc[k]))
        else:
            m[lf > lc[k]] = 1.0
        masks.append(m)
    chans = []
    for _c in range(2 if stereo_out else 1):
        X = np.fft.rfft(rng.standard_normal(n))
        out = np.zeros(n)
        for k in range(len(centers)):
            out += np.fft.irfft(X * masks[k], n) * np.exp(-6.907755 * t / (rt60 * mult[k]))
        if sparse > 0:
            # eco rade all'inizio: la densità cresce col tempo (velvet noise sempre più fitto)
            dens = np.clip((t / (0.25 * rt60 + 1e-3)) ** 2, 0.0, 1.0) * (1 - sparse) + sparse * np.clip(t / (0.6 * rt60 + 1e-3), 0.002, 1.0) ** 2
            dens = np.clip(dens, 0.002, 1.0)
            keep = rng.uniform(0, 1, n) < dens
            out = np.where(keep, out / np.sqrt(dens), 0.0)
        out *= np.clip(t / max(attack, 1e-4), 0.0, 1.0)
        chans.append(out)
    ir = np.array(chans)
    if lp:
        ir = lowpass(ir, lp, 2)
    ir /= np.sqrt(np.sum(ir ** 2) / ir.shape[0]) + 1e-12
    d = ns(predelay)
    if d > 0:
        ir = np.concatenate([np.zeros((ir.shape[0], d)), ir], axis=1)[:, :n]
    # riflessioni discrete (un po' sbavate da un passa-basso): relative all'energia della coda
    for (te, ge, pe) in early:
        k = ns(te)
        if k >= n:
            continue
        tap = np.zeros(n)
        tap[k] = 1.0
        tap = lowpass(tap, 3500, 1)
        if ir.shape[0] == 2:
            th = (np.clip(pe, -1, 1) + 1) * np.pi / 4
            ir[0] += ge * np.cos(th) * tap * np.sqrt(2)
            ir[1] += ge * np.sin(th) * tap * np.sqrt(2)
        else:
            ir[0] += ge * tap
    return ir if stereo_out else ir[0]


def convolve(x: np.ndarray, ir: np.ndarray, circular: bool = False) -> np.ndarray:
    """Convoluzione (FFT). circular=True: convoluzione circolare sulla lunghezza di x (per i loop)."""
    n = x.shape[-1]
    if ir.ndim == 2 and x.ndim == 1:
        x = np.stack([x, x])
    elif ir.ndim == 1 and x.ndim == 2:
        ir = np.stack([ir, ir])
    if circular:
        m = ir.shape[-1]
        folded = np.zeros(ir.shape[:-1] + (n,))
        for k in range(0, m, n):
            seg = ir[..., k:k + n]
            folded[..., :seg.shape[-1]] += seg
        return np.fft.irfft(np.fft.rfft(x, axis=-1) * np.fft.rfft(folded, axis=-1), n, axis=-1)
    return signal.fftconvolve(x, ir, axes=-1)[..., :n]


def reverb(x: np.ndarray, ir: np.ndarray, wet: float = 0.3, dry: float = 1.0, circular: bool = False):
    w = convolve(x, ir, circular)
    d = x if x.ndim == w.ndim else np.stack([x, x])
    return dry * d + wet * w


# ───────────────────────── dinamica e saturazione ─────────────────────────

def softclip(x: np.ndarray, drive: float = 2.0, os: int = 4, asym: float = 0.0) -> np.ndarray:
    """Saturazione tanh sovracampionata (asym > 0 aggiunge armoniche pari)."""
    n = x.shape[-1]
    up = signal.resample_poly(x, os, 1, axis=-1)
    y = np.tanh(drive * (up + asym)) - np.tanh(drive * asym)
    y /= np.tanh(drive)
    return signal.resample_poly(y, 1, os, axis=-1)[..., :n]


def limiter(x: np.ndarray, ceiling_db: float = -1.0, lookahead: float = 0.004, release: float = 0.06,
            circular: bool = False, block: int = 16) -> np.ndarray:
    """Limitatore di picco con anticipo: guadagno calcolato a blocchi, minimo sulla finestra di
    anticipo, rilascio esponenziale e media mobile (garantisce |y| ≤ soglia sui picchi)."""
    c = float(db_to_lin(ceiling_db))
    a = np.abs(x) if x.ndim == 1 else np.max(np.abs(x), axis=0)
    n = len(a)
    if np.max(a) <= c:
        return x.copy()
    g_req = np.minimum(1.0, c / np.maximum(a, 1e-12))
    nb = (n + block - 1) // block
    pad = nb * block - n
    gb = np.concatenate([g_req, np.ones(pad)]).reshape(nb, block).min(axis=1)
    la = max(1, int(round(lookahead * SR / block)))
    mode = 'wrap' if circular else 'nearest'
    # minimo su ±(la+1) blocchi, media mobile su ±la: la media (e l'interpolazione fra blocchi
    # adiacenti) usa solo valori ≤ al guadagno richiesto dal picco → nessun superamento
    gb = minimum_filter1d(gb, 2 * la + 3, mode=mode)
    r = np.exp(-block / (release * SR))
    out = np.empty(nb)
    passes = 2 if circular else 1
    env = 1.0
    for _p in range(passes):
        for i in range(nb):
            env = min(gb[i], 1.0 - (1.0 - env) * r)
            out[i] = env
    out = uniform_filter1d(out, 2 * la + 1, mode=mode)
    centers = np.arange(nb) * block + (block - 1) / 2.0
    g = np.interp(np.arange(n), centers, out)
    g = np.minimum(g, g_req)          # sicurezza (in teoria non interviene)
    return x * g


def bitcrush(x: np.ndarray, bits: float = 6, hold: int = 3) -> np.ndarray:
    q = 2.0 ** (bits - 1)
    y = np.round(x * q) / q
    if hold > 1:
        n = x.shape[-1]
        y = np.repeat(y[..., ::hold], hold, axis=-1)[..., :n]
    return y


# ───────────────────────── misure ─────────────────────────

def peak_db(x) -> float:
    return float(lin_to_db(np.max(np.abs(x))))


def rms_db(x) -> float:
    return float(lin_to_db(rms(x)))


def active_rms_db(x, win: float = 0.05, gate_db: float = 20.0) -> float:
    """RMS sulle sole finestre 'attive' (entro gate_db dalla finestra più forte): livello percepito
    dei suoni brevi o a impulsi, indipendente dal silenzio o dalle code."""
    m = mono(x) if x.ndim == 1 else np.sqrt(np.mean(x ** 2, axis=0))
    p = m ** 2
    w = max(1, ns(win))
    hop = max(1, w // 2)
    if len(p) < w:
        return rms_db(x)
    cs = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, len(p) - w + 1, hop)
    pw = (cs[starts + w] - cs[starts]) / w
    thr = pw.max() * 10 ** (-gate_db / 10)
    sel = pw[pw >= thr]
    return float(10 * np.log10(np.mean(sel) + 1e-24))
