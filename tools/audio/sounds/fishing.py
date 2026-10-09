"""
Pesca e oggetti di bordo (mono, salvo indicazione): lancio, esca, campanellino, mulinello, lenza,
pesce, secchio, lampara, telone, cuore, sonar, radio.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403  (instruments + modelli dei corpi bagnati)
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
    """Il lancio: l'archetto del mulinello che si apre (scatto metallico), la frusta della canna (un fruscio
    netto che sale e ricade con la velocità della punta, e il fischio sottile della vetta), poi il filo che
    corre via dalla bobina: un sibilo fino che sfarfalla contro il primo anello e rallenta."""
    n = s.n
    y = np.zeros(n)
    exc = np.zeros(ns(0.06))
    exc[0], exc[1] = 1.0, -0.5
    bail = modal(exc, [2300, 3650, 5200, 7400], [0.03, 0.022, 0.015, 0.01], [1, 0.7, 0.45, 0.3])
    y[:len(exc)] += 0.45 * normalize(bail + 0.4 * modal(exc, [880, 1350], [0.025, 0.02]))
    sw, v = _whoosh(rng, 0.34, [(0, 0.15), (0.1, 0.45), (0.17, 1.0), (0.23, 0.4), (0.34, 0.0)], 380, 3200, 0.5)
    tone = np.sin(TWO_PI * phase_of(2600 + 2400 * v)) * v ** 3
    body, _ = _whoosh(rng, 0.34, [(0, 0.1), (0.16, 1.0), (0.26, 0.25), (0.34, 0)], 140, 650, 0.6)
    place(y, 0.9 * sw + 0.1 * tone + 0.3 * body, 0.02)
    nz = ns(0.85)
    rot = curve(nz, [(0, 8), (0.05, 52), (0.4, 36), (0.85, 10)], 'lin')
    flap = 0.5 + 0.5 * np.sin(TWO_PI * phase_of(rot * 2.0)) ** 2
    hiss = bandpass(rng.standard_normal(nz), 3200, 10000) * flap
    tick = highpass(stick_slip(nz, rng, rot * 2.0, 1.0, jitter=0.03), 2500)
    env = curve(nz, [(0, 0), (0.05, 1), (0.45, 0.55), (0.85, 0)])
    place(y, (0.28 * normalize(hiss) + 0.1 * normalize(tick)) * env, 0.2)
    return y


@sound('plop', 0.4, category='sfx', gain=0.7, rms=-18.0, max_gr=6.0)
def plop(s, rng):
    """Il piombo con l'esca che entra in acqua: il tic dell'impatto, la cavità che si richiude in un 'plup'
    corto (poca salita di tono), due bollicine e qualche goccia."""
    n = s.n
    y = np.zeros(n)
    k = ns(0.0012)
    y[:k] += 0.45 * bandpass(rng.standard_normal(k + 32), 800, 9000)[:k] * np.linspace(1, 0, k)
    place(y, bubble(rng.uniform(430, 560), xi=0.13, amp=0.9, decay_mult=0.5), 0.005)
    for _ in range(3):
        place(y, bubble(float(loguniform(rng, 900, 2600)), rng.uniform(0.04, 0.3), rng.uniform(0.06, 0.15)),
              rng.uniform(0.02, 0.1))
    for _ in range(4):
        place(y, droplet(rng, amp=rng.uniform(0.03, 0.08), tonal=0.3), rng.uniform(0.04, 0.25))
    y += 0.05 * highpass(rng.standard_normal(n), 2500) * exp_env(n, 0.07, attack=0.001)
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


@sound('line_tension', 2.0, loop=True, category='sfx', gain=0.5, rms=-21.0, max_gr=6.0)
def line_tension(s, rng):
    """La lenza sotto sforzo (loop): la canna che si flette e scricchiola a strappi, la frizione del mulinello
    che slitta a scatti ('zzzt', quando il pesce tira), il filo teso che taglia l'acqua e canta appena."""
    n = s.n
    # la canna: scricchiolii del grezzo, stick-slip lento e irregolare su risonanze medie
    rate = 52.0 * cents(450 * rand_curve(n, 0.9, rng))
    amp = np.clip(0.5 + 0.6 * rand_curve(n, 1.3, rng), 0.0, 1.2) ** 1.5
    exc = stick_slip(n, rng, rate, amp, jitter=0.12)
    f_m, T_m, g_m = wood_modes(rng, 390.0, 8, 0.05, 1.3)
    crk = circular(lambda x: modal(x, f_m, T_m, g_m), exc, pad=0.5)
    # la frizione che slitta: raffiche di scatti metallici fitti
    gate = circular(lambda x: lowpass(x, 30.0, 1), (rand_curve(n, 1.7, rng) > 0.5).astype(float), pad=0.5)
    clicks = stick_slip(n, rng, 68.0 * cents(150 * rand_curve(n, 3.0, rng)), np.clip(gate, 0, 1), jitter=0.04)
    drag = circular(lambda x: modal(x, [2650.0, 4150.0, 6300.0, 8800.0], [0.009, 0.007, 0.005, 0.003], [1.0, 0.7, 0.45, 0.3]),
                    clicks, pad=0.2)
    # il filo: sibilo dove taglia l'acqua, e un canto sottile che vaga
    hiss = spectral_noise(n, rng, lambda f: bw_bp(f, 2500, 9000, 2)) * np.clip(0.55 + 0.5 * rand_curve(n, 2.2, rng), 0.1, 1.3)
    fs = periodic_freq(1850.0 * cents(90 * rand_curve(n, 0.7, rng)))
    sing = np.sin(TWO_PI * phase_of(fs)) * np.clip(rand_curve(n, 1.1, rng), 0.0, 1.0)
    return 0.55 * normalize(crk) + 0.4 * normalize(drag) + 0.1 * hiss / (np.max(np.abs(hiss)) + 1e-9) + 0.05 * sing


@sound('line_snap', 0.6, category='sfx', gain=0.8, rms=-17.0, max_gr=6.0)
def line_snap(s, rng):
    """Il filo che cede: uno schiocco secco e brillante (il nylon che si spezza sotto carico), il moncone che
    frusta l'aria e sbatte sugli anelli, la canna che torna su di scatto (fruscio grave e un colpetto nel
    mulinello); solo un'ombra di vibrazione, smorzata e stonata (il nylon non 'canta' come una corda)."""
    n = s.n
    y = np.zeros(n)
    k = ns(0.0015)
    crack = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 4.0))
    crack[0] += 2.5
    crack = bandpass(np.pad(crack, (0, ns(0.02))), 900, 12000, 2)
    place(y, normalize(crack), 0.0)
    place(y, 0.35 * modal(np.pad(crack[:k], (0, ns(0.05))), [2400.0, 3900.0, 5600.0], [0.02, 0.012, 0.008], [1.0, 0.6, 0.4]), 0.0)
    # il moncone che frusta e picchietta sugli anelli
    wh, _ = _whoosh(rng, 0.2, [(0, 1.0), (0.06, 0.6), (0.2, 0.0)], 1800, 6000, 0.6)
    place(y, 0.4 * wh, 0.003)
    for i, t0 in enumerate([0.03, 0.055, 0.09, 0.14]):
        tick = knock(rng, force=0.0003, base=rng.uniform(1600, 2400), t60=0.02, count=5, bright=1.5, dur=0.05)
        place(y, 0.18 * 0.75 ** i * tick, t0 + rng.uniform(-0.004, 0.004))
    # un'ombra di vibrazione del moncone, smorzata e inarmonica
    m = ns(0.25)
    f0 = curve(m, [(0, 420), (0.05, 260), (0.25, 240)], 'log')
    tw = (np.sin(TWO_PI * phase_of(f0)) + 0.4 * np.sin(TWO_PI * phase_of(f0 * 2.07)) + 0.2 * np.sin(TWO_PI * phase_of(f0 * 3.2))) \
        * exp_env(m, 0.12, attack=0.001)
    place(y, 0.18 * tw, 0.004)
    # la canna che torna su: fruscio grave e un colpetto del mulinello
    sw, _ = _whoosh(rng, 0.3, [(0, 0.3), (0.08, 1.0), (0.3, 0.0)], 200, 900, 0.7)
    place(y, 0.45 * sw, 0.02)
    place(y, 0.25 * knock(rng, 0.0015, base=260, t60=0.06, dur=0.2), 0.12)
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


def _shell_modes(rng, lo, hi, count, t60, bright=1.0):
    """Modi fitti e inarmonici di una lamiera sottile (secchio zincato): più lunghi i gravi."""
    f = np.exp(np.linspace(np.log(lo), np.log(hi), count)) * rng.uniform(0.95, 1.05, count)
    T = t60 * (lo / f) ** 0.45 * rng.uniform(0.7, 1.3, count)
    g = (1.0 / np.arange(1, count + 1) ** (0.5 / bright)) * rng.uniform(0.5, 1.2, count)
    return f, T, g


def _hit(rng, n, force, modes, gain):
    exc = np.zeros(n)
    k = max(2, ns(force))
    exc[:k] = np.sin(np.pi * (np.arange(k) + 0.5) / k)
    f, T, g = modes
    return gain * normalize(modal(exc, f, T, g * rng.uniform(0.7, 1.2, len(g))))


@sound('fish_bucket', 0.95, category='sfx', gain=0.75, rms=-17.0, max_gr=8.0, release=0.015)
def fish_bucket(s, rng):
    """Il pesce (morbido e pesante) sul fondo di un secchio di lamiera zincata con un dito d'acqua: un tonfo
    carnoso, la lamiera che risuona smorzata dal corpo bagnato; poi i colpi di coda contro le pareti (più
    acuti, sempre più deboli) e l'acqua che sciaguatta."""
    n = s.n
    y = np.zeros(n)
    bottom = _shell_modes(rng, 240, 2400, 18, 0.22, bright=0.8)
    wall = _shell_modes(rng, 520, 7200, 26, 0.16, bright=1.2)
    y += _hit(rng, n, 0.007, bottom, 0.5)
    y += 0.5 * wet_slap(rng, size=0.7, surface='flesh', dur=s.dur, drops=0.5)
    for i, t in enumerate([0.17, 0.28, 0.36, 0.47, 0.61]):
        a = 0.7 * 0.8 ** i
        m = n - ns(t)
        hit = _hit(rng, m, rng.uniform(0.002, 0.004), wall, 0.3) + 0.6 * wet_slap(rng, size=0.25, surface='none',
                                                                                    dur=m / SR, drops=0.4)
        place(y, a * hit, t + rng.uniform(-0.01, 0.01))
    sl = bandpass(rng.standard_normal(n), 300, 2500) * curve(n, [(0, 0), (0.03, 1), (0.4, 0.4), (s.dur, 0)])
    sl *= 0.6 + 0.4 * np.abs(rand_curve(n, 14.0, rng))
    y += 0.07 * normalize(sl)
    return y


@sound('fish_throw', 0.7, category='sfx', gain=0.7, rms=-18.0)
def fish_throw(s, rng):
    """Il lancio di un pesce a Gulpy: il pesce afferrato nel secchio (scivola bagnato, la coda tocca la
    lamiera), il braccio che lancia (fruscio), il pesce che vola perdendo gocce e sbattendo la coda.
    L'arrivo non c'è: lo fanno il tonfo in acqua (splash_big) o il morso di Gulpy (gulpy_eat)."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.45 * squish(rng, 0.12, 400, 2600, density=1000, sticky=0.5), 0.0)
    exc = np.zeros(ns(0.3))
    exc[:ns(0.002)] = 1.0
    rim = modal(exc, [690.0, 1180.0, 1730.0, 2600.0, 3900.0], [0.12, 0.09, 0.07, 0.05, 0.035], [1.0, 0.7, 0.5, 0.35, 0.2])
    place(y, 0.12 * normalize(rim), 0.02)
    sw, v = _whoosh(rng, 0.34, [(0, 0.2), (0.12, 1.0), (0.24, 0.45), (0.34, 0)], 380, 2200, 0.6)
    place(y, 0.75 * sw, 0.1)
    place(y, 0.3 * wet_slap(rng, size=0.2, surface='none', dur=0.2, drops=0.6), 0.32)
    for _ in range(6):
        place(y, droplet(rng, amp=rng.uniform(0.03, 0.08), tonal=0.2), rng.uniform(0.15, 0.6))
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

@sound('heartbeat', 1.0, loop=True, category='sfx', gain=0.8, rms=-17.0)
def heartbeat(s, rng):
    """Il battito sentito da dentro (loop di un secondo: 60 al minuto, il gioco lo accelera col playbackRate):
    'lub' grave e pieno, 'dub' più corto e un po' più alto, il sangue che pulsa nelle orecchie."""
    n = s.n
    y = np.zeros(n)
    for t0, f1, f2, T, a in [(0.0, 54.0, 39.0, 0.26, 1.0), (0.27, 70.0, 52.0, 0.18, 0.72)]:
        m = ns(0.32)
        f = curve(m, [(0, f1), (0.05, f2), (0.32, f2 * 0.96)], 'log')
        thump = osc(f) * exp_env(m, T, attack=0.007) + 0.3 * osc(f * 2.3) * exp_env(m, T * 0.5, attack=0.005)
        nz = lowpass(rng.standard_normal(m), 150, 2) * exp_env(m, 0.1, attack=0.005)
        knock_ = bandpass(rng.standard_normal(m), 120, 420) * exp_env(m, 0.05, attack=0.003)
        place(y, a * (thump + 0.45 * normalize(nz) + 0.12 * normalize(knock_)), t0, wrap=True)
    t = tvec(n)
    pulse = np.exp(-((t - 0.06) / 0.12) ** 2) + 0.6 * np.exp(-((t - 0.33) / 0.1) ** 2)
    whoosh = spectral_noise(n, rng, lambda f: bw_bp(f, 40, 260, 2), exponent=1.0) * (0.25 + pulse)
    y = y + 0.06 * whoosh / (np.max(np.abs(whoosh)) + 1e-9)
    return circular(lambda x: lowpass(x, 380, 2), y)


# ───────────────────────── sonar ─────────────────────────

def _ping(rng, m, f, t60=0.9):
    """Il ping del trasduttore: un tono che cala appena, il tic d'attacco, due parziali metalliche."""
    t = tvec(m)
    fr = f * (1 + 0.006 * np.exp(-t / 0.08))
    ph = phase_of(fr)
    y = (np.sin(TWO_PI * ph) * exp_env(m, t60, attack=0.004)
         + 0.1 * np.sin(TWO_PI * 2 * ph) * exp_env(m, t60 * 0.4, attack=0.004)
         + 0.04 * np.sin(TWO_PI * 2.76 * ph + 1.0) * exp_env(m, t60 * 0.2, attack=0.004))
    k = ns(0.002)
    y[:k] += 0.25 * bandpass(rng.standard_normal(k), 2000, 9000) * np.linspace(1, 0, k)
    return y


@sound('sonar_ping', 2.2, channels=2, category='sfx', gain=0.5, rms=-20.0)
def sonar_ping(s, rng):
    """Ping dell'ecoscandaglio: il tono che parte, la coda d'acqua (un riverbero denso che ondeggia), l'eco
    che torna dal fondo più scura e più grave, sotto il crepitio dei gamberetti (il mare caldo di notte)."""
    n = s.n
    dry = np.zeros(n)
    place(dry, _ping(rng, ns(1.3), 1180.0), 0.0)
    echo = np.zeros(n)
    place(echo, lowpass(_ping(rng, ns(1.0), 1173.0, 0.7), 2400, 2) * 0.24, 0.78)
    place(echo, lowpass(_ping(rng, ns(0.7), 1169.0, 0.5), 1700, 2) * 0.09, 1.42)
    ir = reverb_ir(2.1, rng, lo=1.0, hi=0.55, attack=0.03, lp=5500)
    wet = convolve(dry + echo, ir)
    wet = np.stack([time_warp(c, 1 + 0.0025 * rand_curve(n, 0.8, rng), circular=False) for c in wet])
    crackle = np.zeros(n)
    for tc in poisson_times(rng, 35.0, 0.0, s.dur):
        k = max(3, ns(rng.uniform(0.0002, 0.0008)))
        place(crackle, rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 3.0)) * rng.lognormal(-1.5, 0.8), tc)
    crackle = bandpass(crackle, 2000, 10000)
    return pan(dry, 0.0) + pan(echo, 0.3) + 0.38 * wet + 0.05 * pan(crackle, -0.2)


@sound('sonar_blip', 0.15, category='sfx', gain=0.5, rms=-20.0)
def sonar_blip(s, rng):
    """Il bip di un contatto: il cicalino piezoelettrico dell'apparecchio (onda quasi quadra, risonanza acuta)."""
    n = s.n
    f = curve(n, [(0, 1720), (0.008, 1760), (0.15, 1760)])
    ph = phase_of(f)
    sq = np.sin(TWO_PI * ph) + 0.22 * np.sin(3 * TWO_PI * ph) + 0.08 * np.sin(5 * TWO_PI * ph)
    y = (sq + 0.4 * resonate(sq, 3600, 2.0)) * exp_env(n, 0.12, attack=0.0015)
    return lowpass(y, 9000, 2)


@sound('sonar_warn', 0.9, category='sfx', gain=0.7, rms=-18.0)
def sonar_warn(s, rng):
    """L'avviso dell'ecoscandaglio quando sale qualcosa di grosso: due bip più gravi e sporchi, il secondo
    più basso, ognuno con un colpo sordo sotto (come se l'eco tornasse da qualcosa di enorme)."""
    n = s.n
    y = np.zeros(n)
    for t0, f in [(0.0, 520.0), (0.24, 390.0)]:
        m = ns(0.4)
        ph = phase_of(np.full(m, f) * cents(-25 * np.linspace(0, 1, m)))
        sq = np.tanh(2.2 * np.sin(TWO_PI * ph)) + 0.25 * np.sin(2 * TWO_PI * ph + 0.3)
        buzz = 1 + 0.25 * np.sin(TWO_PI * 50.0 * tvec(m))
        b = (sq * buzz + 0.3 * resonate(sq, 2800, 2.5)) * exp_env(m, 0.32, attack=0.003)
        th = osc(curve(m, [(0, 95), (0.15, 58)], 'log')) * exp_env(m, 0.22, attack=0.004)
        place(y, normalize(b) + 0.55 * th, t0)
    ir = reverb_ir(0.8, rng, lo=1.0, hi=0.5, attack=0.005, stereo_out=False)
    return lowpass(y + 0.15 * convolve(y, ir), 7000, 2)


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
    """Il segnale che salta (dopo il jumpscare): uno schiocco elettrico, neve televisiva piena che va a
    strappi, il ronzio a 50 Hz di un televisore che perde il quadro, fischi che strisciano come le righe di
    un nastro rovinato, e alla fine il tubo che si spegne."""
    n = s.n
    t = tvec(n)
    out = np.zeros((2, n))
    env = curve(n, [(0, 1.0), (0.85, 0.9), (1.2, 0.45), (1.5, 0.0)])
    common = rng.standard_normal(n)
    hum = sum(a * np.sin(TWO_PI * 50.0 * k * t + rng.uniform(0, TWO_PI))
              for k, a in [(1, 0.5), (2, 1.0), (3, 0.6), (4, 0.4), (6, 0.25), (8, 0.15)])
    hum = hum * curve(n, [(0, 1.0), (0.8, 0.6), (1.5, 0.0)])
    tears = np.zeros(n)
    for tc in poisson_times(rng, 3.0, 0.05, 1.2):
        d = rng.uniform(0.04, 0.15)
        m = ns(d)
        f = curve(m, [(0, float(loguniform(rng, 900, 6000))), (d, float(loguniform(rng, 900, 6000)))], 'log')
        place(tears, np.sin(TWO_PI * phase_of(f)) * gate_env(m, 0, d - 0.01, 0.003, 0.008), tc)
    for c in range(2):
        nz = normalize(bandpass(0.7 * common + 0.7 * rng.standard_normal(n), 150, 11000, 2))
        crushed = bitcrush(nz, bits=4, hold=7)
        sel = lowpass((np.sin(TWO_PI * 1.7 * t + c) > 0.3).astype(float), 60.0, 1)
        x = nz * (1 - sel) + 0.8 * crushed * sel
        chop = lowpass(0.35 + 0.65 * (hold_noise(n, rng.uniform(25, 40), rng) > -0.6), 400.0, 1)
        y = x * chop + 0.08 * hum + 0.2 * tears
        out[c] = softclip(2.6 * y, 2.0) * env
    # lo schiocco iniziale
    k = ns(0.012)
    pop = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 5.0))
    place(out, stereo(1.2 * pop), 0.0)
    nb = ns(0.25)
    place(out, stereo(0.6 * osc(curve(nb, [(0, 70), (0.2, 40)], 'log')) * exp_env(nb, 0.18, attack=0.002)), 0.0)
    for tc in poisson_times(rng, 25.0, 0.0, 1.3):
        kk = max(4, ns(rng.uniform(0.0003, 0.002)))
        pp = rng.standard_normal(kk) * np.exp(-np.arange(kk) / (kk / 4.0)) * rng.lognormal(0, 0.5)
        place(out, pan(pp, rng.uniform(-0.8, 0.8)) * 0.35, tc)
    # il tubo che si spegne: un fischio che scende e si chiude
    m = ns(0.35)
    whine = np.sin(TWO_PI * phase_of(curve(m, [(0, 15600), (0.35, 6000)], 'log'))) * curve(m, [(0, 0), (0.05, 1), (0.35, 0)])
    place(out, stereo(0.06 * whine), 1.1)
    return out
