"""
Pesca e oggetti di bordo (mono, salvo indicazione): lancio, esca, campanellino, mulinello, lenza,
pesce, secchio, lampara, telone, cuore, sonar, radio.
"""
from __future__ import annotations

from instruments import *  # noqa: F401,F403
from sounds import register, sound


def _whoosh(rng, dur, pts, f_lo=300.0, f_hi=2600.0, q=0.7):
    """Fruscio d'aria: rumore in banda il cui centro e il cui livello seguono la velocità v(t) ∈ [0, 1]."""
    n = ns(dur)
    v = curve(n, pts)
    fc = f_lo + (f_hi - f_lo) * v
    return normalize(tv_bandpass(rng.standard_normal(n), fc, fc * q) * v ** 1.5), v


# ───────────────────────── lancio e attesa ─────────────────────────

@sound('cast', 1.1, category='sfx', gain=0.7, rms=-18.0)
def cast(s, rng):
    n = s.n
    y = np.zeros(n)
    # l'archetto del mulinello che si apre: scatto metallico secco (filo libero)
    exc = np.zeros(ns(0.06))
    exc[0], exc[1] = 1.0, -0.5
    bail = modal(exc, [2300, 3650, 5200, 7400], [0.03, 0.022, 0.015, 0.01], [1, 0.7, 0.45, 0.3])
    y[:len(exc)] += 0.45 * normalize(bail + 0.4 * modal(exc, [880, 1350], [0.025, 0.02]))
    # la frusta della canna: il centro del fruscio segue la velocità della punta
    sw, v = _whoosh(rng, 0.45, [(0, 0.25), (0.1, 0.4), (0.19, 1.0), (0.27, 0.45), (0.45, 0.0)], 300, 2700)
    tone = np.sin(TWO_PI * phase_of(2200 + 2600 * v)) * v ** 3          # fischio eolico della punta sottile
    body, _ = _whoosh(rng, 0.45, [(0, 0.1), (0.17, 1.0), (0.3, 0.3), (0.45, 0)], 120, 600)
    place(y, 0.85 * sw + 0.12 * tone + 0.35 * body, 0.0)
    # il filo che corre: la bobina libera gira veloce e rallenta (spire che si svolgono + sibilo negli anelli)
    nz = ns(0.92)
    rot = curve(nz, [(0, 5), (0.05, 48), (0.45, 34), (0.92, 9)], 'lin')
    am = 0.55 + 0.45 * np.sin(TWO_PI * phase_of(rot * 6)) ** 2
    hiss = bandpass(rng.standard_normal(nz), 2200, 9000) * am
    zz = resonate(rng.standard_normal(nz), 3600, 6.0) * am
    tick = stick_slip(nz, rng, rot, 1.0, jitter=0.02)                   # il filo che sfiora il bordo della bobina
    tick = highpass(tick, 1500)
    env = curve(nz, [(0, 0), (0.04, 1), (0.5, 0.6), (0.92, 0)])
    place(y, (0.5 * normalize(hiss) + 0.3 * normalize(zz) + 0.12 * normalize(tick)) * env, 0.13)
    return y


@sound('plop', 0.4, category='sfx', gain=0.7, rms=-18.0)
def plop(s, rng):
    n = s.n
    y = np.zeros(n)
    k = ns(0.0015)
    y[:k] += 0.4 * rng.standard_normal(k) * np.linspace(1, 0, k)       # il piombo che tocca l'acqua
    place(y, bubble(560, xi=0.5, amp=1.0, decay_mult=0.6), 0.003)     # la cavità che si richiude: 'bloop'
    for _ in range(3):
        place(y, bubble(float(loguniform(rng, 900, 2400)), rng.uniform(0.1, 0.5), rng.uniform(0.1, 0.25)),
              rng.uniform(0.02, 0.12))
    y += 0.07 * highpass(rng.standard_normal(n), 2500) * exp_env(n, 0.08, attack=0.001)
    return y


def _rod_bell(s, rng):
    """Campanellino doppio d'ottone sulla punta: ogni scossa fa battere il battaglio 2-4 volte."""
    n = s.n
    sa, sb = [], []
    for t0, k in s.params['shakes']:
        t = t0
        a = rng.uniform(0.75, 1.0)
        for i in range(k):
            (sa if (i == 0 or rng.random() < 0.55) else sb).append((t, a))
            t += rng.uniform(0.018, 0.055)
            a *= rng.uniform(0.55, 0.85)
    y = small_bell(rng, 2380.0, n, sa, t60=1.0) + 0.85 * small_bell(rng, 2960.0, n, sb, t60=0.9)
    return highpass(y, 400, 2)


register('rod_bell_1', _rod_bell, 1.2, category='sfx', gain=0.8, rms=-18.0,
         params={'shakes': [(0.0, 3), (0.2, 2), (0.47, 3)]})
register('rod_bell_2', _rod_bell, 1.2, category='sfx', gain=0.8, rms=-18.0,
         params={'shakes': [(0.0, 4), (0.31, 3), (0.52, 1)]})


# ───────────────────────── recupero ─────────────────────────

@sound('reel_loop', 0.48, loop=True, category='sfx', gain=0.6, rms=-20.0, max_gr=7.0, release=0.012)
def reel_loop(s, rng):
    n = s.n                                    # 23040 campioni: 12 scatti da 40 ms (un giro di manovella)
    t = tvec(n)
    y = np.zeros(n)
    hand = 1.0 + 0.2 * np.sin(TWO_PI * t / s.dur)
    for i in range(12):
        tt = i * 0.04
        a = (1.0 if i % 2 == 0 else 0.84) * (0.9 + 0.1 * np.sin(TWO_PI * i / 12)) * rng.uniform(0.95, 1.05)
        exc = np.zeros(ns(0.05))
        exc[0], exc[1] = 1.0, -0.6
        pawl = modal(exc, np.array([2850, 4630, 7150, 9800]) * rng.uniform(0.98, 1.02, 4),
                     [0.012, 0.009, 0.006, 0.004], [1.0, 0.7, 0.45, 0.3])
        body = modal(exc, [920, 1480], [0.02, 0.015], [1.0, 0.6])
        place(y, a * (normalize(pawl) + 0.45 * normalize(body)), tt, wrap=True)
    # ingranaggi: rumore pettinato alla frequenza dei denti (312,5 Hz → 150 cicli nel loop)
    teeth = (0.5 + 0.5 * np.cos(TWO_PI * 312.5 * t)) ** 4
    whir = spectral_noise(n, rng, lambda f: bw_bp(f, 900, 4500, 2)) * teeth
    line = spectral_noise(n, rng, lambda f: bw_bp(f, 3000, 9000, 2))
    return y + (0.07 * whir + 0.025 * line) * hand


@sound('line_tension', 2.0, loop=True, category='sfx', gain=0.5, rms=-21.0)
def line_tension(s, rng):
    n = s.n
    # il nylon teso che sfrega negli anelli: moto di Helmholtz (dente di sega) a ~1,1 kHz che vaga
    f = periodic_freq(1050.0 * cents(60 * rand_curve(n, 1.5, rng) + 15 * rand_curve(n, 9.0, rng)))
    ph = phase_of(f)
    saw = sum(np.sin(TWO_PI * k * ph) / k ** 1.2 for k in range(1, 8))
    amp = np.clip(0.55 + 0.5 * rand_curve(n, 2.0, rng), 0.0, 1.3) ** 2
    squeal = circular(lambda x: resonate(x, 2300, 2.0) + 0.6 * resonate(x, 4100, 3.0) + 0.3 * x, saw * amp)
    # cigolio della canna che si flette (stick-slip lento sull'impugnatura)
    rate = 70.0 * cents(400 * rand_curve(n, 0.8, rng))
    a2 = np.clip(0.6 + 0.5 * rand_curve(n, 1.2, rng), 0.05, 1.2)
    exc = stick_slip(n, rng, rate, a2, jitter=0.08)
    f_m, T_m, g_m = wood_modes(rng, 420.0, 7, 0.05, 1.2)
    crk = circular(lambda x: modal(x, f_m, T_m, g_m), exc, pad=0.5)
    # il filo che vibra grave sotto tensione
    hum = np.sin(TWO_PI * phase_of(periodic_freq(np.full(n, 187.0)))) * (0.5 + 0.3 * rand_curve(n, 3.0, rng))
    return 0.55 * normalize(squeal) + 0.35 * normalize(crk) + 0.025 * hum


@sound('line_snap', 0.6, category='sfx', gain=0.8, rms=-17.0)
def line_snap(s, rng):
    n = s.n
    y = np.zeros(n)
    # schiocco secco del nylon che cede
    k = ns(0.0008)
    crack = rng.standard_normal(k) * np.linspace(1, 0, k)
    crack[0] += 3.0
    y[:k] += 0.9 * normalize(crack)
    # twang: il moncone libero vibra mentre la tensione crolla (il tono precipita)
    m = ns(0.45)
    f0 = curve(m, [(0, 820), (0.035, 360), (0.12, 190), (0.45, 172)], 'log')
    tw = additive(f0, [1, 0.6, 0.45, 0.3, 0.2, 0.12, 0.08]) * exp_env(m, 0.3, attack=0.0005)
    place(y, 0.6 * normalize(tw), 0.002)
    # la frustata del filo nell'aria e il colpo della canna che si raddrizza
    wh, _ = _whoosh(rng, 0.18, [(0, 1.0), (0.18, 0.0)], 1500, 4000, 0.8)
    place(y, 0.35 * wh, 0.004)
    place(y, 0.25 * knock(rng, 0.002, base=240, t60=0.06, dur=0.2), 0.01)
    return y


# ───────────────────────── pesce ─────────────────────────

def _flap(rng, a=1.0):
    """Colpo di coda in aria: schiocco bagnato senza superficie dura + spruzzi."""
    return a * wet_slap(rng, size=0.3, surface='none', dur=0.22, drops=0.6)


@sound('fish_out', 1.2, category='sfx', gain=0.7, rms=-18.0)
def fish_out(s, rng):
    n = s.n
    y = np.zeros(n)
    # la superficie che si rompe e il risucchio che si stacca
    nr = ns(0.25)
    r = bandpass(rng.standard_normal(nr), 300, 6000) * curve(nr, [(0, 0.3), (0.06, 1), (0.25, 0)])
    y[:nr] += 0.7 * normalize(r)
    place(y, bubble(320, xi=0.5, amp=0.6, decay_mult=0.5), 0.02)
    # l'acqua che cola: gocce sempre più rade
    for t in poisson_times(rng, lambda tt: 70 * np.exp(-tt / 0.3) + 4, 0.05, 1.1):
        place(y, droplet(rng, amp=rng.uniform(0.05, 0.2)), t)
    # guizzi
    for i, t in enumerate([0.24, 0.36, 0.47, 0.6, 0.76]):
        place(y, _flap(rng, 0.75 * 0.85 ** i), t + rng.uniform(-0.015, 0.015))
    nt = ns(0.7)
    tr = bandpass(rng.standard_normal(nt), 1200, 5000) * curve(nt, [(0, 0), (0.1, 1), (0.7, 0)])
    place(y, 0.06 * normalize(tr), 0.1)
    return y


BUCKET = (np.array([285, 452, 664, 870, 1130, 1420, 1765, 2150, 2610, 3120, 3700], dtype=float),
          np.array([0.5, 0.45, 0.4, 0.35, 0.3, 0.26, 0.22, 0.18, 0.15, 0.12, 0.1]),
          np.array([1.0, 0.8, 0.75, 0.6, 0.5, 0.45, 0.35, 0.3, 0.22, 0.18, 0.12]))


def _bucket_hit(rng, n, force, damp, gain):
    exc = np.zeros(n)
    k = max(2, ns(force))
    exc[:k] = np.sin(np.pi * (np.arange(k) + 0.5) / k)
    f, T, g = BUCKET
    return gain * normalize(modal(exc, f * rng.uniform(0.985, 1.015, len(f)), T * damp, g * rng.uniform(0.7, 1.2, len(g))))


@sound('fish_bucket', 0.9, category='sfx', gain=0.75, rms=-17.0, max_gr=8.0, release=0.015)
def fish_bucket(s, rng):
    n = s.n
    y = np.zeros(n)
    # il pesce (morbido e pesante) sul fondo di lamiera zincata: tonfo carnoso + lamiera smorzata
    y += _bucket_hit(rng, n, 0.006, 0.55, 0.55)
    y += 0.5 * wet_slap(rng, size=0.7, surface='flesh', dur=s.dur, drops=0.5)
    # colpi di coda contro le pareti, sempre più deboli
    for i, t in enumerate([0.17, 0.27, 0.35, 0.46, 0.6]):
        a = 0.75 * 0.8 ** i
        m = n - ns(t)
        hit = _bucket_hit(rng, m, 0.003, 0.35, 0.35) + 0.6 * wet_slap(rng, size=0.25, surface='none', dur=m / SR,
                                                                       drops=0.4)
        place(y, a * hit, t + rng.uniform(-0.01, 0.01))
    # un dito d'acqua sul fondo che sciaguatta
    sl = bandpass(rng.standard_normal(n), 300, 2500) * curve(n, [(0, 0), (0.03, 1), (0.4, 0.4), (0.9, 0)])
    y += 0.06 * normalize(sl)
    return y


@sound('fish_throw', 0.8, category='sfx', gain=0.7, rms=-18.0)
def fish_throw(s, rng):
    n = s.n
    y = np.zeros(n)
    # il pesce che taglia l'aria (e perde gocce)
    sw, v = _whoosh(rng, 0.38, [(0, 0.25), (0.12, 1.0), (0.3, 0.5), (0.38, 0)], 400, 2000, 0.8)
    place(y, 0.7 * sw, 0.0)
    m = len(v)
    place(y, 0.08 * normalize(highpass(rng.standard_normal(m), 3000)) * v, 0.0)
    # arrivo: schiaffo bagnato sulla carne
    place(y, wet_slap(rng, size=0.6, surface='flesh', dur=0.38), 0.42)
    return y


# ───────────────────────── lampara ─────────────────────────

@sound('lamp_switch', 0.25, category='sfx', gain=0.6, rms=-19.0, max_gr=8.0, release=0.012)
def lamp_switch(s, rng):
    n = s.n
    y = np.zeros(n)
    # leva della valvola d'ottone: due scatti metallici (contatto e fermo)
    for t, a, base in [(0.0, 1.0, 2900.0), (0.019, 0.7, 3400.0)]:
        exc = np.zeros(ns(0.08))
        exc[0], exc[1] = 1.0, -0.6
        m = modal(exc, base * np.array([1, 1.62, 2.37, 3.13, 4.2]), [0.035, 0.025, 0.018, 0.012, 0.008],
                  [1, 0.7, 0.5, 0.35, 0.2])
        body = modal(exc, [1150, 1900], [0.02, 0.015], [1, 0.6])
        place(y, a * (normalize(m) + 0.5 * normalize(body)), t)
    # il gas che cambia flusso: breve soffio
    nh = ns(0.2)
    h = bandpass(rng.standard_normal(nh), 2000, 9000) * curve(nh, [(0, 0), (0.01, 1), (0.2, 0)])
    place(y, 0.22 * normalize(h), 0.012)
    return y


@sound('lamp_flicker', 0.6, category='sfx', gain=0.6, rms=-19.0, max_gr=6.0)
def lamp_flicker(s, rng):
    n = s.n
    t = tvec(n)
    # il soffio che sputacchia: buchi e picchi irregolari
    hiss = bandpass(rng.standard_normal(n), 1000, 9000) + 0.4 * bandpass(rng.standard_normal(n), 120, 600)
    gate = lowpass(0.3 + 0.7 * np.clip(hold_noise(n, 28.0, rng) * 0.5 + 0.5, 0, 1), 180.0, 2)
    env = curve(n, [(0, 1), (0.45, 0.8), (0.6, 0)])
    y = 0.45 * normalize(hiss) * gate * env
    # scoppiettii secchi
    for tc in poisson_times(rng, 40.0, 0.0, 0.5):
        k = max(4, ns(rng.uniform(0.0003, 0.001)))
        pop = highpass(rng.standard_normal(k + 64), 1500)[:k + 64] * np.exp(-np.arange(k + 64) / k)
        place(y, 0.5 * pop * rng.lognormal(-1.0, 0.6), tc)
    # sfrigolio elettrico: brevi raffiche di ronzio a 100 Hz
    for t0, d in [(0.05, 0.06), (0.21, 0.04), (0.33, 0.09)]:
        m = ns(d)
        tt = tvec(m)
        bz = np.tanh(4 * np.sin(TWO_PI * 100 * tt)) + 0.3 * np.sin(TWO_PI * 300 * tt + 1)
        bz = bandpass(bz + 0.3 * rng.standard_normal(m), 100, 6000) * gate_env(m, 0, d - 0.006, 0.003, 0.006)
        place(y, 0.25 * normalize(bz), t0)
    return y


# ───────────────────────── telone ─────────────────────────

@sound('tarp_in', 0.9, category='sfx', gain=0.7, rms=-18.0)
def tarp_in(s, rng):
    y = 0.8 * crinkle(rng, s.dur, [(0, 0.5), (0.1, 0.9), (0.35, 1.0), (0.55, 0.8), (0.62, 0.35), (0.9, 0)],
                      density=1100, f_lo=500, f_hi=5500, res=1500, swish=0.55)
    # il telone pesante che ricade sopra: 'fwump' d'aria spostata
    nf = ns(0.35)
    flap = lowpass(rng.standard_normal(nf), 300, 2) * exp_env(nf, 0.22, attack=0.025)
    place(y, 0.6 * normalize(flap), 0.5)
    place(y, 0.3 * knock(rng, 0.01, base=110, t60=0.1, dur=0.3), 0.12)        # ginocchia sul legno
    return y


@sound('tarp_out', 0.8, category='sfx', gain=0.7, rms=-18.0)
def tarp_out(s, rng):
    y = 0.8 * crinkle(rng, s.dur, [(0, 1.0), (0.08, 1.0), (0.25, 0.6), (0.45, 0.25), (0.8, 0)],
                      density=1100, f_lo=500, f_hi=5500, res=1500, swish=0.55)
    sw, _ = _whoosh(rng, 0.25, [(0, 0.4), (0.08, 1.0), (0.25, 0)], 200, 1200, 0.9)
    place(y, 0.5 * sw, 0.0)
    nf = ns(0.3)
    flap = lowpass(rng.standard_normal(nf), 350, 2) * exp_env(nf, 0.18, attack=0.012)
    place(y, 0.55 * normalize(flap), 0.12)
    return y


# ───────────────────────── corpo ─────────────────────────

@sound('heartbeat', 1.0, category='sfx', gain=0.8, rms=-17.0)
def heartbeat(s, rng):
    n = s.n
    y = np.zeros(n)
    # lub (S1) e dub (S2): toni smorzati con caduta di tono + tonfo filtrato, tutto ovattato
    for t0, f1, f2, T, a in [(0.0, 58.0, 44.0, 0.16, 1.0), (0.27, 72.0, 58.0, 0.11, 0.75)]:
        m = ns(0.35)
        f = curve(m, [(0, f1), (0.08, f2), (0.35, f2)], 'log')
        thump = osc(f) * exp_env(m, T, attack=0.004) + 0.35 * osc(f * 2.1) * exp_env(m, T * 0.6, attack=0.003)
        nz = lowpass(rng.standard_normal(m), 160, 2) * exp_env(m, 0.06, attack=0.003)
        place(y, a * (thump + 0.4 * normalize(nz)), t0)
    return lowpass(y, 230, 2)


# ───────────────────────── sonar ─────────────────────────

def _ping(m, f):
    t = tvec(m)
    fr = f * (1 + 0.004 * np.exp(-t / 0.1))
    ph = phase_of(fr)
    return (np.sin(TWO_PI * ph) * exp_env(m, 0.9, attack=0.004)
            + 0.12 * np.sin(TWO_PI * 2 * ph) * exp_env(m, 0.4, attack=0.004)
            + 0.05 * np.sin(TWO_PI * 3.07 * ph) * exp_env(m, 0.15, attack=0.004))


@sound('sonar_ping', 2.2, channels=2, category='sfx', gain=0.5, rms=-20.0)
def sonar_ping(s, rng):
    n = s.n
    dry = np.zeros(n)
    place(dry, _ping(ns(1.2), 1180.0), 0.0)
    # eco di ritorno dal fondo: più debole, più scura, un filo più grave
    echo = np.zeros(n)
    place(echo, lowpass(_ping(ns(1.0), 1174.0), 2500, 2) * 0.25, 0.78)
    place(echo, lowpass(_ping(ns(0.7), 1171.0), 1800, 2) * 0.1, 1.42)
    ir = reverb_ir(2.0, rng, lo=1.0, hi=0.5, attack=0.03, lp=5000)
    return pan(dry, 0.0) + pan(echo, 0.3) + 0.35 * convolve(dry + echo, ir)


@sound('sonar_blip', 0.15, category='sfx', gain=0.5, rms=-20.0)
def sonar_blip(s, rng):
    n = s.n
    f = curve(n, [(0, 1700), (0.01, 1760), (0.15, 1760)])
    ph = phase_of(f)
    return (np.sin(TWO_PI * ph) + 0.08 * np.sin(TWO_PI * 2 * ph) + 0.03 * np.sin(TWO_PI * 3 * ph)) \
        * exp_env(n, 0.11, attack=0.0015)


# ───────────────────────── radio VHF ─────────────────────────

def _radio_noise(rng, n):
    nz = bandpass(rng.standard_normal(n), 300, 3400, 3)
    return normalize(eq(nz, 'peak', 2000, 1.0, 3.0))


@sound('radio_on', 0.4, category='sfx', gain=0.5, rms=-19.0)
def radio_on(s, rng):
    n = s.n
    y = np.zeros(n)
    exc = np.zeros(ns(0.03))
    exc[0] = 1.0
    y[:len(exc)] += 0.5 * normalize(modal(exc, [1800, 3100, 4700], [0.012, 0.008, 0.005]))   # scatto del relè
    # lo squelch si apre: soffio forte che si quieta quando la portante aggancia
    env = curve(n, [(0, 0), (0.003, 1), (0.08, 0.9), (0.13, 0.12), (0.36, 0.08), (0.4, 0)])
    y += 0.8 * _radio_noise(rng, n) * env
    m = ns(0.05)
    chirp = np.sin(TWO_PI * phase_of(curve(m, [(0, 1250), (0.05, 900)], 'log'))) * gate_env(m, 0, 0.04, 0.005, 0.01)
    place(y, 0.12 * chirp, 0.085)
    return y


@sound('radio_off', 0.4, category='sfx', gain=0.5, rms=-19.0)
def radio_off(s, rng):
    n = s.n
    # coda di squelch: 'kshhh', poi la chiusura secca con lo scatto
    env = curve(n, [(0, 0.4), (0.01, 1.0), (0.21, 0.95), (0.232, 0.0), (0.4, 0.0)])
    y = 0.85 * _radio_noise(rng, n) * env * (1 + 0.15 * rand_curve(n, 30.0, rng))
    exc = np.zeros(ns(0.03))
    exc[0] = 1.0
    place(y, 0.45 * normalize(modal(exc, [1700, 2900, 4400], [0.012, 0.008, 0.005])), 0.232)
    return y


@sound('static_burst', 1.5, channels=2, category='sfx', gain=0.7, rms=-14.0, max_gr=6.0)
def static_burst(s, rng):
    n = s.n
    t = tvec(n)
    out = np.zeros((2, n))
    env = curve(n, [(0, 1.0), (0.85, 0.9), (1.15, 0.45), (1.5, 0.0)])
    common = rng.standard_normal(n)
    for c in range(2):
        nz = normalize(bandpass(0.7 * common + 0.7 * rng.standard_normal(n), 150, 11000, 2))
        # interferenza: tratti "digitali" (quantizzati e tenuti) alternati al soffio pieno
        crushed = bitcrush(nz, bits=4, hold=7)
        sel = lowpass((np.sin(TWO_PI * 1.7 * t + c) > 0.3).astype(float), 60.0, 1)
        x = nz * (1 - sel) + 0.8 * crushed * sel
        chop = lowpass(0.35 + 0.65 * (hold_noise(n, rng.uniform(25, 40), rng) > -0.6), 400.0, 1)
        hum = lowpass(np.sign(np.sin(TWO_PI * 60 * t)), 2000, 2) * 0.12 * (t < 0.7)
        out[c] = softclip(3.0 * (x * chop + hum), 2.0) * env
    for tc in poisson_times(rng, 25.0, 0.0, 1.3):
        k = max(4, ns(rng.uniform(0.0003, 0.002)))
        pop = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 4.0)) * rng.lognormal(0, 0.5)
        place(out, pan(pop, rng.uniform(-0.8, 0.8)) * 0.35, tc)
    return out
