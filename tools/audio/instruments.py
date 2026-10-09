"""
Modelli sonori di medio livello per WHAT IS BELOW, costruiti sui mattoni di dsp.py:
  - acqua: bolle (risonanza di Minnaert), gocce, schizzi, colpi d'onda sullo scafo, fiotti;
  - legno: modi di una tavola, attrito stick-slip (scricchiolii), colpi;
  - corpi bagnati: schiaffi, risucchi, applausi;
  - metallo: campana di bronzo (parziali inarmoniche con battimenti), lamelle di carillon,
    glockenspiel, campanellino d'ottone;
  - voce: gargarismo, "bagnato", filtro radio, richiami (balena, gabbiano), respiro, fiuto, canne.
Ogni funzione riceve un np.random.Generator: a parità di seme il risultato è identico.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from dsp import *  # noqa: F401,F403  (mattoni DSP: filtri, inviluppi, rumori, voce...)
from dsp import SR, NYQ, TWO_PI


def loguniform(rng, lo, hi, size=None):
    return np.exp(rng.uniform(np.log(lo), np.log(hi), size))


# ═════════════════════════ ACQUA ═════════════════════════

def bubble(f0: float, xi: float = 0.1, amp: float = 1.0, decay_mult: float = 1.0, max_dur: float = 1.0):
    """Bolla d'aria che risuona alla frequenza di Minnaert e sale verso la superficie
    (modello di K. van den Doel): seno smorzato la cui frequenza cresce nel tempo.
    xi = salita di tono (0.1 bolla profonda, 1–3 'bloop' vicino alla superficie)."""
    d = (0.043 * f0 + 0.0014 * f0 ** 1.5) / decay_mult
    n = max(32, int(min(6.9 / d, max_dur) * SR))
    t = tvec(n)
    f = f0 * (1.0 + xi * d * t)
    y = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-d * t)
    return amp * y


def bubble_burst(buf, rng, t0, count, spread, f_lo, f_hi, amp, xi=(0.05, 0.4), wrap=False,
                 pan_range=None, decay_mult=1.0):
    """Gruppo di bolle dopo t0 (istanti esponenziali con media `spread`), frequenze log-uniformi."""
    for _ in range(int(count)):
        t = t0 + rng.exponential(spread)
        f = float(loguniform(rng, f_lo, f_hi))
        a = amp * (f_lo / f) ** 0.3 * rng.lognormal(0.0, 0.4)
        b = bubble(f, rng.uniform(*xi), a, decay_mult)
        if buf.ndim == 2:
            b = pan(b, rng.uniform(*(pan_range or (-0.3, 0.3))))
        place(buf, b, t, wrap=wrap)


def droplet(rng, f=None, amp=1.0):
    """Goccia che ricade sull'acqua: minuscolo impatto + bollicina con forte salita di tono ('plink')."""
    f = f or float(loguniform(rng, 1400, 5200))
    b = bubble(f, xi=rng.uniform(0.3, 1.2), amp=1.0)
    k = ns(0.0006)
    b[:k] += rng.standard_normal(k) * np.linspace(1, 0, k) * 0.2
    return amp * b


def splash(rng, size=0.5, dur=None):
    """Schizzo d'acqua; size 0..1 (0 = spruzzo, 1 = tonfo pesante)."""
    dur = dur or (0.35 + 1.2 * size)
    n = ns(dur)
    y = np.zeros(n)
    # 1) impatto: rumore a banda larga, attacco istantaneo, coda breve
    ni = min(n, ns(0.04 + 0.3 * size))
    burst = rng.standard_normal(ni) * exp_env(ni, 0.05 + 0.35 * size, attack=0.0015)
    burst = bandpass(burst, 300 - 200 * size, 9000, 2)
    y[:ni] += normalize(burst) * 0.9
    # 2) corona: secondo fiotto più morbido
    nc = ns(0.06 + 0.3 * size)
    crown = rng.standard_normal(nc) * curve(nc, [(0, 0), (0.008, 1), (0.06 + 0.3 * size, 0)])
    place(y, normalize(bandpass(crown, 600, 7000)) * 0.45, rng.uniform(0.012, 0.03 + 0.05 * size))
    # 3) la cavità d'aria si richiude: bolla grande con forte salita di tono ('bloop')
    if size > 0.2:
        fb = rng.uniform(380, 650) * (1.35 - size)
        place(y, bubble(fb, xi=rng.uniform(0.8, 2.0), amp=0.8 * size), rng.uniform(0.03, 0.08 + 0.1 * size))
    # 4) bolle intrappolate
    bubble_burst(y, rng, 0.01, 6 + 40 * size, 0.04 + 0.12 * size, 500, 3500, 0.22, xi=(0.1, 0.6))
    # 5) gocce che ricadono
    for _ in range(int(4 + 40 * size)):
        place(y, droplet(rng, amp=rng.uniform(0.04, 0.22)), rng.uniform(0.08, 0.12 + 0.9 * size))
    # 6) frizzio di schiuma
    fz = rng.standard_normal(n) * exp_env(n, 0.25 + 0.8 * size, attack=0.02)
    y += highpass(fz, 2500, 2) * 0.04
    return y


HULL_MODES = ([105.0, 168.0, 243.0, 331.0, 452.0, 610.0], [0.20, 0.15, 0.12, 0.09, 0.07, 0.05],
              [1.0, 0.75, 0.55, 0.4, 0.28, 0.18])


def lap(rng, strength=1.0, dur=1.0, hull=0.35, clop_prob=0.8, bright=1.0):
    """Un colpo d'acqua contro lo scafo (mare calmo): l'acqua che risale il fasciame, lo schiaffo morbido,
    il legno che risponde, la sacca d'aria che si chiude ('clop'), le bollicine e lo scolo."""
    n = ns(dur)
    y = np.zeros(n)
    rise = rng.uniform(0.04, 0.14)
    # l'acqua che sale lungo il fasciame: fruscio scuro con inviluppo lento
    nr = min(n, ns(rise + 0.35))
    w = bandpass(rng.standard_normal(nr), 130, 900 * bright, 2)
    env = curve(nr, [(0, 0), (rise, 1), (rise + 0.07, 0.45), (rise + 0.35, 0)])
    y[:nr] += 0.3 * normalize(w * env)
    # schiaffo morbido (acqua contro legno, non contro roccia)
    nsl = ns(0.16)
    slap = rng.standard_normal(nsl) * exp_env(nsl, rng.uniform(0.05, 0.12), attack=rng.uniform(0.004, 0.012))
    slap = normalize(bandpass(slap, 200, (1700 + 900 * strength) * bright, 2))
    place(y, 0.42 * slap * strength, rise)
    # risposta del legno dello scafo (modi bassi, smorzati)
    if hull > 0:
        f, T, g = HULL_MODES
        f = np.array(f) * rng.uniform(0.93, 1.07, len(f))
        place(y, hull * normalize(modal(slap, f, T, g)) * strength, rise)
    # la sacca d'aria che si chiude: 'clop' breve con il tono che sale
    if rng.random() < clop_prob:
        fc = float(loguniform(rng, 170, 460))
        b = bubble(fc, xi=rng.uniform(0.25, 0.6), amp=rng.uniform(0.45, 0.9) * strength,
                   decay_mult=rng.uniform(0.3, 0.55))
        place(y, b, rise + rng.uniform(0.0, 0.025))
    # 'plip' liquidi attorno all'impatto
    for _ in range(int(rng.integers(2, 7))):
        b = bubble(float(loguniform(rng, 380, 1500)), rng.uniform(0.1, 0.45),
                   rng.uniform(0.12, 0.32) * strength, decay_mult=rng.uniform(0.5, 1.0))
        place(y, b, rise + rng.exponential(0.05))
    # scolo: bollicine rade e un filo di fruscio
    bubble_burst(y, rng, rise + 0.08, rng.integers(2, 7), 0.18, 900, 3000, 0.06 * strength, xi=(0.05, 0.4))
    nd = ns(0.5)
    drain = bandpass(rng.standard_normal(nd), 900, 3800) * exp_env(nd, 0.35, attack=0.03)
    place(y, 0.035 * normalize(drain) * strength * bright, rise + 0.05)
    return y


def gush(n, rng, intensity, bubble_rate=220.0, f_lo=140.0, f_hi=1600.0):
    """Acqua che entra a fiotti: rumore turbolento 'a bolle' + molte bolle; intensity: array 0..1."""
    t = tvec(n)
    nz = bandpass(rng.standard_normal(n), 140, 4500)
    am = 0.55 + 0.45 * np.tanh(1.5 * rand_curve(n, 45.0, rng))
    y = 0.5 * normalize(nz * am) * intensity
    times = poisson_times(rng, lambda tt: bubble_rate * np.interp(tt, t, intensity) + 1e-3, 0.0, n / SR)
    buf = np.zeros(n)
    for tb in times:
        f = float(loguniform(rng, f_lo, f_hi))
        place(buf, bubble(f, rng.uniform(0.1, 1.2), rng.lognormal(0, 0.4) * (f_lo / f) ** 0.25), tb)
    return y + 0.6 * buf / (np.sqrt(bubble_rate) * 0.12 + 1e-9)


# ═════════════════════════ LEGNO ═════════════════════════

WOOD_RATIOS = np.array([1.0, 2.31, 3.86, 5.6, 7.7, 10.1, 12.9, 16.1, 19.6, 23.4])


def wood_modes(rng, base=180.0, count=8, t60=0.1, bright=1.0):
    """Modi di una tavola di legno (rapporti inarmonici), più smorzati verso l'acuto."""
    r = WOOD_RATIOS[:count] * rng.uniform(0.94, 1.06, count)
    r[0] = 1.0
    f = base * r
    T = t60 * (base / f) ** 0.55 * rng.uniform(0.8, 1.2, count)
    g = (1.0 / np.sqrt(np.arange(1, count + 1))) ** (1.0 / bright) * rng.uniform(0.6, 1.2, count)
    return f, T, g


def stick_slip(n, rng, rate, amp, jitter=0.06, grain=0.0004):
    """Treno di impulsi d'attrito (stick-slip) con frequenza rate(t) e ampiezza amp(t)."""
    rate = np.broadcast_to(np.asarray(rate, dtype=float), (n,))
    amp = np.broadcast_to(np.asarray(amp, dtype=float), (n,))
    jit = 1.0 + jitter * hold_noise(n, max(float(np.mean(rate)), 5.0), rng)
    ph = np.cumsum(rate * jit) / SR
    idx = np.nonzero(np.diff(np.floor(ph)))[0] + 1
    x = np.zeros(n)
    if len(idx):
        x[idx] = amp[idx] * rng.lognormal(0.0, 0.3, len(idx))
    k = max(2, ns(grain))
    ker = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 3.0))
    ker[0] = abs(ker[0]) + 1.0
    return signal.lfilter(ker, [1.0], x)


def creak(rng, dur, rate_pts, env_pts, base=180.0, t60=0.1, bright=1.0, jitter=0.06, count=8, hiss=0.15):
    """Scricchiolio: attrito stick-slip (frequenza che varia) che eccita i modi di una tavola."""
    n = ns(dur)
    rate = curve(n, rate_pts, 'log')
    amp = curve(n, env_pts)
    exc = stick_slip(n, rng, rate, amp, jitter)
    exc += hiss * 0.3 * amp * highpass(rng.standard_normal(n), 900)
    f, T, g = wood_modes(rng, base, count, t60, bright)
    return normalize(modal(exc, f, T, g))


def knock(rng, force=0.002, base=160.0, t60=0.1, count=8, bright=1.0, dur=0.5, rough=0.1, cavity=None):
    """Colpo su una tavola: forza a mezzo seno lunga `force` s (più lunga = colpo più sordo) sui modi del legno.
    cavity = (f, t60, livello) aggiunge la risonanza d'aria di una cavità (lo scafo)."""
    n = ns(dur)
    exc = np.zeros(n)
    k = max(2, ns(force))
    exc[:k] = np.sin(np.pi * (np.arange(k) + 0.5) / k)
    exc[:k] += rough * rng.standard_normal(k)
    f, T, g = wood_modes(rng, base, count, t60, bright)
    y = normalize(modal(exc, f, T, g))
    if cavity:
        y += cavity[2] * normalize(modal(exc, [cavity[0]], [cavity[1]]))
    return normalize(y)


# ═════════════════════════ CORPI BAGNATI ═════════════════════════

def squelch(rng, dur=0.12, f_lo=600.0, f_hi=3000.0, rate=60.0, density=500.0):
    """Risucchio viscido: micro-granuli di rumore filtrati da una risonanza che salta (cavità bagnate)."""
    n = ns(dur)
    x = np.zeros(n)
    for t in poisson_times(rng, density, 0.0, dur):
        g = max(4, ns(rng.uniform(0.0005, 0.003)))
        place(x, rng.standard_normal(g) * np.hanning(g) * rng.lognormal(0, 0.6), t)
    fc = np.exp(np.log(f_lo) + (np.log(f_hi) - np.log(f_lo)) * (0.5 + 0.5 * np.tanh(rand_curve(n, rate, rng))))
    y = tv_bandpass(x, fc, fc / 3.0)
    env = curve(n, [(0, 0), (min(0.005, dur / 4), 1), (dur * 0.5, 0.6), (dur, 0)])
    return normalize(y * env)


def wet_slap(rng, size=1.0, surface='wood', dur=0.5, wood_base=150.0, drops=1.0):
    """Schiaffo bagnato di una mano/pinna/pancia su legno ('wood'), carne ('flesh') o metallo ('none')."""
    n = ns(dur)
    y = np.zeros(n)
    force = 0.003 + 0.006 * size
    if surface == 'wood':
        body = knock(rng, force, base=wood_base * (1.1 - 0.3 * size), t60=0.08 + 0.06 * size, dur=dur, rough=0.05)
        y += 0.6 * body
    elif surface == 'flesh':
        exc = np.zeros(n)
        k = ns(force * 1.5)
        exc[:k] = np.sin(np.pi * (np.arange(k) + 0.5) / k)
        y += 0.6 * normalize(modal(exc, [130, 240, 390], [0.07, 0.05, 0.035], [1, 0.6, 0.35]))
    # schiocco della pelle bagnata (aria espulsa fra superfici bagnate)
    nsn = min(n, ns(0.09))
    snap = rng.standard_normal(nsn) * exp_env(nsn, 0.03 + 0.04 * size, attack=0.0004)
    snap = bandpass(snap, 650, 9000) + 0.5 * resonate(snap, 1500 + 600 * (1 - size), 1.4)
    y[:nsn] += 0.85 * normalize(snap)
    # risucchio subito dopo
    place(y, 0.3 * squelch(rng, 0.06 + 0.1 * size), 0.004)
    # gocce e spruzzi
    for _ in range(int((3 + 8 * size) * drops)):
        place(y, droplet(rng, amp=rng.uniform(0.03, 0.11)), rng.uniform(0.02, 0.25 + 0.2 * size))
    fz = highpass(rng.standard_normal(n), 3000) * exp_env(n, 0.12 + 0.1 * size, attack=0.001)
    y += 0.05 * fz
    return y


def clap(rng, size=1.0, wet=0.5, dur=0.25):
    """Battito di mani: più micro-impatti in pochi ms, risonanza della sacca d'aria fra i palmi."""
    n = ns(dur)
    y = np.zeros(n)
    fc = rng.uniform(1100, 1600) / size
    for _ in range(int(rng.integers(2, 5))):
        nb = ns(0.035)
        b = rng.standard_normal(nb) * exp_env(nb, rng.uniform(0.02, 0.04), attack=0.0003)
        b = resonate(b, fc * rng.uniform(0.85, 1.15), 2.2) + 0.35 * highpass(b, 2500)
        place(y, b * rng.uniform(0.5, 1.0), rng.uniform(0, 0.004))
    y = normalize(y)
    if wet:
        place(y, wet * 0.45 * squelch(rng, 0.07, 700, 3500), 0.003)
        for _ in range(int(4 * wet + 1)):
            place(y, droplet(rng, amp=rng.uniform(0.04, 0.12) * wet), rng.uniform(0.01, 0.15))
    return y


# ═════════════════════════ METALLO ═════════════════════════

# campana di bronzo: (rapporto col prime, ampiezza, frazione del T60) — hum, prime, terza minore (tierce),
# quinta (quint), nominale, decima, undecima, duodecima, doppia ottava e parziali alte
CHURCH_BELL = [
    (0.500, 0.55, 1.00), (1.000, 0.85, 0.62), (1.183, 0.60, 0.45), (1.506, 0.32, 0.36),
    (2.000, 1.00, 0.33), (2.514, 0.42, 0.22), (2.662, 0.28, 0.19), (3.011, 0.30, 0.15),
    (4.166, 0.20, 0.10), (5.433, 0.12, 0.08), (6.796, 0.08, 0.06), (8.215, 0.05, 0.045),
]


def church_bell(rng, prime, dur, t60=9.0, bright=1.0, beat=1.0, strike=0.5):
    """Rintocco di campana di bronzo: parziali inarmoniche, ognuna sdoppiata in due componenti vicine
    (asimmetrie della fusione → battimenti lenti) e con il proprio decadimento; colpo del battaglio."""
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    for ratio, a, tf in CHURCH_BELL:
        f = prime * ratio * (1 + rng.normal(0, 0.0015))
        if f > NYQ * 0.9:
            continue
        T = t60 * tf
        amp = a * bright ** np.log2(ratio)
        df = beat * rng.uniform(0.25, 1.0) * (0.6 + 0.4 * ratio)
        a2 = rng.uniform(0.35, 0.8)
        p1, p2 = rng.uniform(0, TWO_PI, 2)
        comp = np.sin(TWO_PI * (f - df / 2) * t + p1) + a2 * np.sin(TWO_PI * (f + df / 2) * t + p2)
        y += amp * comp / (1 + a2) * np.exp(-6.907755 * t / T)
    # colpo del battaglio: parziali molto alte che muoiono subito + rumore metallico
    for _ in range(7):
        f = prime * rng.uniform(9, 22)
        if f < NYQ * 0.9:
            y += strike * 0.08 * bright * np.sin(TWO_PI * f * t + rng.uniform(0, TWO_PI)) * np.exp(-6.9 * t / rng.uniform(0.04, 0.15))
    k = ns(0.004)
    y[:k] += strike * 0.5 * bandpass(rng.standard_normal(k), 900, 6000) * np.linspace(1, 0, k)
    y *= np.clip(t / 0.0015, 0, 1)
    return y


def tine(rng, f, vel=1.0, dur=3.0, t60=None, bright=1.0, detune=0.0):
    """Lamella di carillon pizzicata: fondamentale quasi pura con doppio decadimento (accoppiamento
    col pettine), debole seconda armonica (non linearità) e modi inarmonici della lamella che si spengono subito."""
    n = ns(dur)
    t = tvec(n)
    f = f * cents(detune)
    T1 = t60 or float(np.clip(3.0 * (440.0 / f) ** 0.55, 0.8, 5.0))
    env1 = 0.72 * np.exp(-6.907755 * t / T1) + 0.28 * np.exp(-6.907755 * t / (T1 * 0.12))
    y = env1 * np.sin(TWO_PI * f * t)
    parts = [(2.0, 0.05, 0.45), (3.0, 0.015, 0.3), (2.756, 0.03, 0.12), (5.404, 0.06, 0.06),
             (6.27, 0.07, 0.05), (8.93, 0.025, 0.03), (17.6, 0.02, 0.015)]
    for r, a, tf in parts:
        fr = f * r * (1 + rng.normal(0, 0.003))
        if fr > NYQ * 0.9:
            continue
        y += a * bright * np.sqrt(vel) * np.sin(TWO_PI * fr * t + rng.uniform(0, TWO_PI)) * \
            np.exp(-6.907755 * t / max(T1 * tf, 0.012))
    k = ns(0.0015)
    y[:k] += bandpass(rng.standard_normal(k), 2000, 12000) * np.linspace(1, 0, k) * 0.06 * vel
    y *= np.clip(t / 0.0004, 0, 1)
    return vel * y


def glock(rng, f, vel=1.0, dur=2.5, t60=None, bright=1.0):
    """Barretta libera-libera (glockenspiel/celesta): parziali 1, 2.756, 5.404, 8.933."""
    n = ns(dur)
    t = tvec(n)
    T1 = t60 or float(np.clip(2.5 * (880.0 / f) ** 0.5, 0.6, 4.0))
    y = np.zeros(n)
    for r, a, tf in [(1.0, 1.0, 1.0), (2.756, 0.28, 0.3), (5.404, 0.1, 0.12), (8.933, 0.04, 0.06)]:
        fr = f * r
        if fr < NYQ * 0.9:
            y += a * (bright if r > 1 else 1.0) * np.sin(TWO_PI * fr * t) * np.exp(-6.907755 * t / (T1 * tf))
    k = ns(0.0007)
    y[:k] += np.sin(np.pi * (np.arange(k) + 0.5) / k) * 0.15
    y *= np.clip(t / 0.0005, 0, 1)
    return vel * y


SMALL_BELL = [(1.0, 1.0, 1.0), (2.32, 0.55, 0.6), (3.68, 0.38, 0.42), (5.25, 0.24, 0.3),
              (6.9, 0.14, 0.22), (8.7, 0.08, 0.16)]


def small_bell(rng, f, n, strikes, t60=1.0, beat=6.0, click=0.15):
    """Campanellino d'ottone colpito più volte. strikes = [(t_s, ampiezza)]. Ogni colpo eccita i modi
    (doppietti che battono) con pesi un po' diversi (il battaglio colpisce in punti diversi)."""
    y = np.zeros(n)
    modes = []
    for r, a, tf in SMALL_BELL:
        fr = f * r * (1 + rng.normal(0, 0.004))
        if fr > NYQ * 0.9:
            continue
        modes.append((fr, beat * rng.uniform(0.3, 1.0) * r, a, t60 * tf, rng.uniform(0.4, 0.8)))
    for ts, sa in strikes:
        i0 = ns(ts)
        if i0 >= n:
            continue
        m = n - i0
        tt = tvec(m)
        seg = np.zeros(m)
        for fr, df, a, T, a2 in modes:
            w = rng.uniform(0.6, 1.4)
            seg += a * w * (np.sin(TWO_PI * (fr - df / 2) * tt) + a2 * np.sin(TWO_PI * (fr + df / 2) * tt)) / (1 + a2) \
                * np.exp(-6.907755 * tt / T)
        k = min(m, ns(0.0008))
        seg[:k] += click * highpass(rng.standard_normal(k), 3000) * np.linspace(1, 0, k)
        y[i0:] += sa * seg
    return y


# ═════════════════════════ VOCI, RESPIRI, RICHIAMI ═════════════════════════

def gargle(n, rng, rate=25.0, depth=0.6, width=0.008, wrap=False):
    """Gargarismo: buchi d'ampiezza irregolari (bolle che interrompono il flusso in gola).
    Restituisce (guadagno per campione, istanti delle bolle)."""
    times = poisson_times(rng, rate, 0.0, n / SR)
    imp = np.zeros(n)
    idx = np.minimum((times * SR).astype(np.int64), n - 1)
    np.add.at(imp, idx, rng.uniform(0.4, 1.0, len(idx)))
    k = max(3, ns(width))
    ker = np.hanning(k)
    if wrap:
        kk = np.zeros(n)
        kk[:k] = ker
        kk = np.roll(kk, -(k // 2))
        g = np.fft.irfft(np.fft.rfft(imp) * np.fft.rfft(kk), n)
    else:
        g = np.convolve(imp, ker)[k // 2:k // 2 + n]
    return 1.0 - depth * np.clip(g, 0.0, 1.0), times


def wet(x, rng, rate=22.0, depth=0.5, bubbles=0.35, flange=0.5, f_lo=250.0, f_hi=1100.0, wrap=False,
        width=0.008):
    """Rende 'bagnata' una voce: gargarismo, pettine acquoso che vaga, bolle che scoppiano in gola."""
    n = len(x)
    g, times = gargle(n, rng, rate, depth, width, wrap)
    y = x * g
    if flange:
        y = flanger(y, rng, base_ms=1.4, depth_ms=0.8, rate=1.2, mix=flange, wrap=wrap)
    if bubbles:
        env = lowpass(np.abs(x), 25.0)
        env /= np.max(env) + 1e-9
        for t in times:
            if rng.random() < 0.65:
                i = min(int(t * SR), n - 1)
                b = bubble(float(loguniform(rng, f_lo, f_hi)), xi=rng.uniform(0.15, 0.6),
                           amp=bubbles * env[i] * rng.uniform(0.5, 1.0) * np.max(np.abs(x)))
                place(y, b, t, wrap=wrap)
    return y


def creature(rng, dur, f0_pts, vowel_keys, scale=1.0, amp_pts=None, oq=0.6, jitter=0.015, shimmer=0.08,
             sub=0.0, breath=0.12, vib=(0.0, 5.5), bw_scale=1.0, wander=0.0, tremor=(0.0, 7.0)):
    """Voce di creatura: contorno di f0 (Hz, interpolato in scala logaritmica), vocali con formanti
    scalate (scale > 1 tratto vocale corto/piccolo, < 1 gola enorme), vibrato, tremolo e rugosità."""
    n = ns(dur)
    f0 = curve(n, f0_pts, 'log')
    t = tvec(n)
    if vib[0]:
        f0 = f0 * cents(vib[0] * np.sin(TWO_PI * vib[1] * t + rng.uniform(0, TWO_PI)))
    if wander:
        f0 = f0 * cents(wander * rand_curve(n, 3.0, rng))
    F, B = formant_track(n, vowel_keys, scale, bw_scale)
    amp = curve(n, amp_pts) if amp_pts else None
    y = voice(f0, F, B, rng, amp=amp, oq=oq, jitter=jitter, shimmer=shimmer, sub=sub, breath=breath)
    if tremor[0]:
        y *= 1.0 + tremor[0] * np.sin(TWO_PI * tremor[1] * t + rng.uniform(0, TWO_PI))
    return normalize(y)


def radio_fx(x, drive=2.2, lo=300.0, hi=3000.0):
    """Altoparlantino VHF: passa-banda stretto, leggera saturazione, di nuovo banda limitata."""
    y = bandpass(x, lo, hi, 4)
    y = softclip(normalize(y), drive)
    return bandpass(y, lo * 0.92, hi * 1.12, 2)


def breath(rng, dur, inhale=True, amp_pts=None, tremor=0.0, dark=1.0):
    """Respiro: rumore con risonanze del tratto vocale (bocca semichiusa); l'inspiro è più chiaro."""
    n = ns(dur)
    nz = rng.standard_normal(n)
    y = (0.55 * resonate(nz, 520 * dark, 2.2) + 0.4 * resonate(nz, 1350 * dark, 2.5)
         + 0.28 * resonate(nz, 2500 * dark, 3.0) + (0.22 if inhale else 0.08) * highpass(nz, 3200))
    env = curve(n, amp_pts or [(0, 0), (dur * 0.35, 1), (dur * 0.7, 0.8), (dur, 0)])
    if tremor:
        env = env * (1 + tremor * np.tanh(2 * rand_curve(n, 9.0, rng)))
    return normalize(y) * env


def sniff(rng, dur, strength=1.0, wet_amt=0.0):
    """Annusata: aria aspirata dal naso (risonanze nasali acute), finale netto."""
    n = ns(dur)
    nz = rng.standard_normal(n)
    y = (0.6 * resonate(nz, 1900, 3.0) + 0.5 * resonate(nz, 3300, 4.0) + 0.35 * resonate(nz, 5200, 3.0)
         + 0.25 * highpass(nz, 1500))
    env = curve(n, [(0, 0), (0.015, 0.55), (dur * 0.65, 1.0), (dur - 0.01, 0.9), (dur, 0)])
    y = normalize(y) * env * strength
    if wet_amt:
        snort = lowpass(rng.standard_normal(n), 400) * (0.5 + 0.5 * np.sign(np.sin(TWO_PI * 28 * tvec(n))))
        y += wet_amt * 0.5 * normalize(snort) * env
    return y


def whale_moan(rng, dur, f0_pts, vowel_keys, scale=0.6, amp_pts=None, sub=0.15, breath_amt=0.05):
    """Lamento di balena/creatura abissale: voce lentissima con glissati e formanti molto basse."""
    return creature(rng, dur, f0_pts, vowel_keys, scale=scale, amp_pts=amp_pts, oq=0.7, jitter=0.004,
                    shimmer=0.03, sub=sub, breath=breath_amt, wander=6.0, bw_scale=1.6)


def gull_note(rng, dur, f_peak, rough=0.3):
    """Nota di gabbiano ('kyow'): tono acuto e aspro che sale e ricade, formanti alte, rugosità."""
    n = ns(dur)
    f0 = curve(n, [(0, f_peak * 0.72), (dur * 0.3, f_peak), (dur, f_peak * 0.62)], 'log')
    exc, flow = glottal(f0, rng, oq=0.42, sq=3.0, jitter=0.02, shimmer=0.12, sub=0.2)
    src = normalize(exc) + 0.15 * aspiration(flow, rng)
    F = np.tile(np.array([[1350.0], [2650.0], [3900.0], [5200.0]]), (1, n)) * cents(30 * rand_curve(n, 4, rng))
    B = np.tile(np.array([[260.0], [380.0], [500.0], [700.0]]), (1, n))
    y = formant_cascade(src, F, B)
    y *= 1 + rough * np.sin(TWO_PI * 70 * tvec(n))
    y *= curve(n, [(0, 0), (0.015, 1), (dur * 0.6, 0.8), (dur, 0)])
    return normalize(y)


def pipe(rng, dur, f_pts, breath_amt=0.12, chiff=0.25, odd=(0.12, 0.03), wobble=8.0, att=0.03, rel=0.05):
    """Canna tappata (il fischietto di un orologio a cucù): fondamentale quasi pura, armoniche dispari
    deboli, soffio intonato e 'chiff' d'attacco."""
    n = ns(dur)
    f = curve(n, f_pts, 'log') * cents(wobble * rand_curve(n, 4.0, rng))
    ph = phase_of(f)
    y = np.sin(TWO_PI * ph) + odd[0] * np.sin(3 * TWO_PI * ph) + odd[1] * np.sin(5 * TWO_PI * ph)
    tuned = tv_bandpass(rng.standard_normal(n), f, f / 10.0)
    env = curve(n, [(0, 0), (att, 1), (max(dur - rel, att), 0.9), (dur, 0)])
    y = (y + breath_amt * normalize(tuned) * 1.5) * env
    nch_ = min(n, ns(0.04))
    ch = bandpass(rng.standard_normal(nch_), 1500, 6500) * exp_env(nch_, 0.035, attack=0.004)
    y[:nch_] += chiff * normalize(ch)
    return y


def boom(rng, dur=3.0, f_start=55.0, f_end=30.0, t60=2.0, thump=0.5):
    """Colpo basso cinematografico: seno con caduta di tono + tonfo di rumore filtrato."""
    n = ns(dur)
    f = curve(n, [(0, f_start), (0.35, f_end), (dur, f_end * 0.97)], 'log')
    y = osc(f) * exp_env(n, t60, attack=0.002)
    nt = min(n, ns(0.4))
    th = lowpass(rng.standard_normal(nt), 180, 2) * exp_env(nt, 0.25, attack=0.001)
    y[:nt] += thump * normalize(th)
    return softclip(y * 0.8, 1.5)


# ═════════════════════════ TELA, VENTO, GABBIANI ═════════════════════════

def crinkle(rng, dur, env_pts, density=900.0, f_lo=700.0, f_hi=5500.0, res=1800.0, swish=0.35):
    """Tela cerata che si piega: nuvola di micro-scatti (ampiezze log-normali, molto irregolari)
    + fruscio d'attrito continuo; la densità segue l'inviluppo del movimento."""
    n = ns(dur)
    t = tvec(n)
    env = curve(n, env_pts)
    times = poisson_times(rng, lambda tt: density * np.interp(tt, t, env) + 1e-6, 0.0, dur)
    x = np.zeros(n)
    for tg in times:
        g = max(3, ns(rng.uniform(0.0002, 0.0015)))
        a = rng.lognormal(0.0, 0.8) * np.interp(tg, t, env)
        place(x, a * rng.standard_normal(g) * np.exp(-np.arange(g) / (g / 3.0)), tg)
    y = bandpass(x, f_lo, f_hi) + 0.6 * resonate(x, res, 2.0)
    y = normalize(y)
    fr = bandpass(rng.standard_normal(n), 350, 3000) * env
    return y + swish * normalize(fr) * 0.6


def wind_layer(n, rng, gust_rate=0.12, low=0.5, mid=0.35, high=0.12, whistle=0.02, whistle_f=800.0,
               corr=0.75, bright=1.0):
    """Vento stereo periodico (loop): tre bande di rumore la cui intensità segue raffiche lente
    (le bande alte crescono più in fretta con la raffica) + un fischio leggero che segue le raffiche."""
    out = np.zeros((2, n))
    common = rand_curve(n, gust_rate, rng)
    t = tvec(n)
    for c in range(2):
        g = np.clip(0.55 + 0.33 * (corr * common + (1 - corr) * rand_curve(n, gust_rate * 1.3, rng)), 0.06, 1.3)
        lo_ = spectral_noise(n, rng, lambda f: bw_bp(f, 35, 220, 2), exponent=1.0)
        md_ = spectral_noise(n, rng, lambda f: bw_bp(f, 180, 950 * bright, 2), exponent=1.0)
        hi_ = spectral_noise(n, rng, lambda f: bw_bp(f, 700 * bright, 4000 * bright, 2), exponent=0.5)
        y = low * lo_ * g ** 0.7 + mid * md_ * g ** 1.3 + high * hi_ * g ** 2.2
        if whistle:
            fw = periodic_freq(whistle_f * (0.85 + 0.25 * g) * cents(25 * rand_curve(n, 0.6, rng)))
            tone = np.sin(TWO_PI * phase_of(fw) + rng.uniform(0, TWO_PI))
            nb = spectral_noise(n, rng, lambda f: peak_shape(f, whistle_f, 14.0, 2.0) - 1.0)
            y += whistle * (0.6 * tone + 0.8 * nb) * np.clip(g - 0.45, 0, None) ** 2.5 * 3.0
        out[c] = y
    return out


def gull_call(rng, kind='long', f_base=1100.0):
    """Richiamo di gabbiano: 'long' = kyoow + serie accelerata di kow; 'short' = 2-3 kyow."""
    notes = []
    if kind == 'long':
        notes.append((0.0, 0.34, f_base * 1.05))
        t = 0.42
        k = int(rng.integers(5, 8))
        for i in range(k):
            d = 0.2 - 0.012 * i
            notes.append((t, d, f_base * (0.98 - 0.025 * i) * rng.uniform(0.97, 1.03)))
            t += d + 0.07 - 0.004 * i
    else:
        t = 0.0
        for i in range(int(rng.integers(2, 4))):
            notes.append((t, 0.26, f_base * rng.uniform(0.95, 1.05)))
            t += rng.uniform(0.4, 0.6)
    total = notes[-1][0] + notes[-1][1] + 0.05
    y = np.zeros(ns(total))
    for t0, d, fp in notes:
        place(y, gull_note(rng, d, fp) * rng.uniform(0.75, 1.0), t0)
    return y
