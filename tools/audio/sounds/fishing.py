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


def _tick(rng, base=5200.0, t60=0.012):
    """Tic metallico secco (la molletta d'acciaio, un fermo)."""
    exc = np.zeros(ns(0.03))
    exc[0], exc[1] = 1.0, -0.8
    return normalize(modal(exc, base * np.array([1, 1.53, 2.21]) * rng.uniform(0.95, 1.05, 3), [t60, t60 * 0.7, t60 * 0.5],
                           [1, 0.6, 0.35]))


def _rod_bell(s, rng):
    """Due campanellini d'ottone su una molletta in punta alla canna. Ogni strattone del pesce fa oscillare la
    vetta (5 volte al secondo circa, sempre meno): il battaglio colpisce agli estremi dell'oscillazione, forte e
    ribattuto all'inizio, poi sempre più piano; i due campanellini non suonano mai insieme uguali; la molletta
    ticchetta sulla vetta."""
    n, dur = s.n, s.dur
    sa, sb = [], []
    y_clip = np.zeros(n)
    for t0, force in s.params['pulls']:
        f_tip = rng.uniform(4.3, 5.5)
        tau = rng.uniform(0.17, 0.28)
        k = 0
        while True:
            th = t0 + (k + 0.5) / (2 * f_tip) + rng.normal(0, 0.004)
            a = force * np.exp(-(th - t0) / tau)
            if a < 0.07 or th > dur - 0.08:
                break
            nb = 1 + int(rng.random() < a) + int(rng.random() < a * 0.45)     # il battaglio rimbalza
            tb = th
            for j in range(nb):
                first = (k % 2 == 0) == (j == 0)
                (sa if first else sb).append((tb, a * 0.62 ** j * rng.uniform(0.85, 1.1)))
                tb += rng.uniform(0.011, 0.028)
            place(y_clip, 0.12 * a * _tick(rng), th + rng.uniform(-0.003, 0.003))
            k += 1
    y = small_bell(rng, 2380.0, n, sa, t60=1.1, beat=5.0) + 0.8 * small_bell(rng, 3020.0, n, sb, t60=0.95, beat=6.5)
    return highpass(normalize(y) + y_clip, 400, 2)


register('rod_bell_1', _rod_bell, 1.2, category='sfx', gain=0.8, rms=-18.0,
         params={'pulls': [(0.0, 1.0), (0.46, 0.75)]})
register('rod_bell_2', _rod_bell, 1.2, category='sfx', gain=0.8, rms=-18.0,
         params={'pulls': [(0.0, 0.45), (0.15, 0.4), (0.29, 0.55), (0.52, 1.0)]})


# ───────────────────────── recupero ─────────────────────────

@sound('reel_loop', 0.48, loop=True, category='sfx', gain=0.6, rms=-20.0, max_gr=7.0, release=0.012)
def reel_loop(s, rng):
    """Un giro di manovella del mulinello (loop esatto). La mano accelera e rallenta nel giro, e tutto la segue:
    il cricchetto dell'antiritorno scatta 12 volte (più fitto dove la mano va veloce), gli ingranaggi girano con
    il loro fischio di denti, il filo si avvolge sulla bobina, il rullino dell'archetto cigola appena una volta."""
    n = s.n                                     # 23040 campioni
    t = tvec(n)
    w = TWO_PI * t / s.dur
    speed = 1 + 0.2 * np.sin(w + 0.6) + 0.05 * np.sin(2 * w + 1.3)
    phi = np.cumsum(speed)
    phi = (phi - phi[0]) / (phi[-1] - phi[0] + speed[0])          # 0 → 1 in un giro, periodico
    y = np.zeros(n)
    for k in range(12):
        i = int(np.searchsorted(phi, k / 12))
        a = (1.0 if k % 2 == 0 else 0.86) * rng.uniform(0.93, 1.05) * (0.75 + 0.25 * speed[min(i, n - 1)])
        exc = np.zeros(ns(0.05))
        exc[0], exc[1] = 1.0, -0.6
        pawl = modal(exc, np.array([2850, 4630, 7150, 9800]) * rng.uniform(0.98, 1.02, 4),
                     [0.012, 0.009, 0.006, 0.004], [1.0, 0.7, 0.45, 0.3])
        body = modal(exc, [920, 1480, 2210], [0.024, 0.017, 0.011], [1.0, 0.6, 0.35])
        place(y, a * (normalize(pawl) + 0.5 * normalize(body)), i / SR, wrap=True)
    # ingranaggi: 150 denti al giro, fase intera → il fischio segue la velocità e il loop resta continuo
    mesh = TWO_PI * 150 * phi
    teeth = (0.5 + 0.5 * np.cos(mesh)) ** 4
    whir = spectral_noise(n, rng, lambda f: bw_bp(f, 900, 4500, 2)) * teeth * speed
    whine = (np.sin(mesh) + 0.35 * np.sin(2 * mesh + 0.7)) * speed
    line = spectral_noise(n, rng, lambda f: bw_bp(f, 3000, 9000, 2)) * (0.85 + 0.15 * np.sin(TWO_PI * 2 * phi))
    # il rullino: un cigolio corto a metà giro (attrito a strappi)
    m = ns(0.06)
    sq = stick_slip(m, rng, 2900.0, curve(m, [(0, 0), (0.01, 1), (0.06, 0)]), jitter=0.1, grain=0.0002)
    place(y, 0.05 * normalize(bandpass(sq, 2000, 8000)), 0.22, wrap=True)
    return y + 0.07 * whir + 0.007 * whine + 0.025 * line


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
    """Il pesce tirato fuori: la superficie che si rompe con un risucchio (la cavità lasciata dal pesce che si
    richiude), il pesce che si dibatte in aria e ogni colpo di coda che lancia una manciata di gocce che
    ricadono sul mare poco dopo; l'acqua che gli cola di dosso; il filo che sibila negli anelli."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.75 * splash(rng, size=0.3, dur=0.6), 0.0)
    place(y, bubble(300, xi=0.45, amp=0.5, decay_mult=0.6), 0.03)
    m = ns(0.14)
    fc = curve(m, [(0, 420), (0.14, 1000)], 'log')
    slurp = tv_bandpass(rng.standard_normal(m), fc, fc * 0.35) * curve(m, [(0, 0), (0.015, 1), (0.14, 0)])
    place(y, 0.18 * normalize(slurp), 0.05)
    for i, t in enumerate([0.22, 0.33, 0.45, 0.6, 0.78]):
        a = 0.8 * 0.85 ** i
        tt = t + rng.uniform(-0.015, 0.015)
        place(y, _flap(rng, a), tt)
        for _ in range(int(rng.integers(5, 10))):
            place(y, droplet(rng, amp=rng.uniform(0.04, 0.14) * a), tt + rng.uniform(0.2, 0.42))
    for t in poisson_times(rng, lambda tt: 50 * np.exp(-tt / 0.35) + 3, 0.1, 1.15):
        place(y, droplet(rng, amp=rng.uniform(0.03, 0.11)), t)
    nt = ns(0.6)
    tr = bandpass(rng.standard_normal(nt), 2500, 7000) * curve(nt, [(0, 0), (0.08, 1), (0.6, 0)])
    place(y, 0.05 * normalize(tr), 0.05)
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

@sound('lamp_switch', 0.3, category='sfx', gain=0.6, rms=-19.0, max_gr=8.0, release=0.012)
def lamp_switch(s, rng):
    """Il commutatore della lampara: la manopola di bachelite che gira sulla camma (un tic) e scatta sulla
    tacca (un clac secco con la scatola che risuona), il contatto che sfrigola un attimo, il reattore che
    cambia ronzio."""
    n = s.n
    y = np.zeros(n)
    for t, a, base in [(0.0, 0.4, 3700.0), (0.026, 1.0, 2450.0)]:
        exc = np.zeros(ns(0.08))
        exc[0], exc[1] = 1.0, -0.7
        snap = modal(exc, base * np.array([1, 1.58, 2.31, 3.4]), [0.02, 0.014, 0.01, 0.007], [1, 0.6, 0.4, 0.25])
        box = modal(exc, [760, 1330, 2050], [0.03, 0.02, 0.014], [1, 0.7, 0.4])
        place(y, a * (normalize(snap) + 0.7 * normalize(box)), t)
    k = ns(0.02)
    arc = highpass(rng.standard_normal(k), 2500) * (rng.random(k) < 0.25) * np.linspace(1, 0, k)
    place(y, 0.22 * normalize(arc), 0.029)
    m = ns(0.26)
    tt = tvec(m)
    hum = np.sin(TWO_PI * 100 * tt) + 0.45 * np.sin(TWO_PI * 200 * tt + 1) + 0.3 * np.sin(TWO_PI * 300 * tt + 2)
    hum = np.tanh(2.0 * hum) * curve(m, [(0, 0), (0.012, 1), (0.26, 0)])
    place(y, 0.09 * normalize(hum), 0.032)
    return y


@sound('lamp_flicker', 0.7, category='sfx', gain=0.6, rms=-19.0, max_gr=6.0)
def lamp_flicker(s, rng):
    """La lampara che tremola: la scarica s'interrompe e riprende a scatti (il sibilo e il ronzio cadono e
    tornano), a ogni ripresa il contatto crepita, e nei cali di tensione il reattore ronza ruvido."""
    n = s.n
    t = tvec(n)
    gate = np.ones(n)
    ons = []
    tc = 0.03
    while tc < 0.48:
        off = rng.uniform(0.015, 0.06)
        on = rng.uniform(0.025, 0.09)
        gate[ns(tc):ns(tc + off)] = rng.uniform(0.0, 0.3)
        ons.append(tc + off)
        tc += off + on
    gate = lowpass(gate, 250, 2)
    ripple = np.abs(np.sin(TWO_PI * 50 * t))
    hiss = bandpass(rng.standard_normal(n), 1500, 10000) * (0.7 + 0.3 * ripple)
    hum = np.tanh(2 * (np.sin(TWO_PI * 100 * t) + 0.5 * np.sin(TWO_PI * 200 * t + 1) + 0.3 * np.sin(TWO_PI * 300 * t + 2)))
    env = curve(n, [(0, 1), (0.5, 1), (0.7, 0)])
    y = (0.4 * normalize(hiss) + 0.22 * hum) * gate * env
    buzz = np.tanh(5 * np.sin(TWO_PI * 100 * t)) * np.clip(1 - gate, 0, 1) * env
    y += 0.18 * bandpass(buzz, 100, 5000)
    for to in ons:
        for _ in range(int(rng.integers(2, 5))):
            k = max(4, ns(rng.uniform(0.0002, 0.001)))
            pop = highpass(rng.standard_normal(k + 64), 1500)[:k + 64] * np.exp(-np.arange(k + 64) / k)
            place(y, 0.45 * pop * rng.lognormal(-0.8, 0.5), to + rng.uniform(0, 0.008))
    return y


# ───────────────────────── telone ─────────────────────────

@sound('tarp_in', 1.1, category='sfx', gain=0.7, rms=-18.0)
def tarp_in(s, rng):
    """Ci si infila sotto il telone di tela cerata: la mano che afferra la tela (uno scricchiolio rigido), il
    telone tirato su e sopra la testa (fruscio pesante e aria spostata), le ginocchia sulle tavole e il corpo
    che scivola sul pagliolo, il telone che ricade sopra con un tonfo morbido e si assesta; alla fine i rumori
    sono già ovattati, perché sei sotto."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.5 * crinkle(rng, 0.12, [(0, 1.0), (0.05, 0.8), (0.12, 0)], density=1800, f_lo=700, f_hi=6000, res=1700,
                           swish=0.2), 0.0)
    place(y, 0.9 * crinkle(rng, 0.55, [(0, 0.3), (0.12, 1.0), (0.32, 0.9), (0.45, 0.4), (0.55, 0)], density=1200,
                           f_lo=450, f_hi=5500, res=1400, swish=0.6), 0.06)
    sw, _ = _whoosh(rng, 0.4, [(0, 0.1), (0.18, 1.0), (0.4, 0)], 150, 900, 0.9)
    place(y, 0.35 * sw, 0.08)
    place(y, 0.3 * knock(rng, 0.01, base=110, t60=0.1, dur=0.3), 0.2)
    place(y, 0.22 * knock(rng, 0.008, base=125, t60=0.09, dur=0.3), 0.31)
    m = ns(0.3)
    slide = stick_slip(m, rng, curve(m, [(0, 40), (0.3, 25)]), curve(m, [(0, 0), (0.05, 1), (0.3, 0)]), jitter=0.2,
                       grain=0.002)
    place(y, 0.3 * normalize(bandpass(slide, 150, 2500)), 0.33)
    nf = ns(0.35)
    flap = lowpass(rng.standard_normal(nf), 280, 2) * exp_env(nf, 0.22, attack=0.02)
    place(y, 0.6 * normalize(flap), 0.62)
    settle = crinkle(rng, 0.42, [(0, 0.8), (0.1, 0.4), (0.42, 0)], density=500, f_lo=400, f_hi=4000, res=1200, swish=0.3)
    place(y, 0.35 * lowpass(settle, 2200, 2), 0.66)
    return y


@sound('tarp_out', 0.9, category='sfx', gain=0.7, rms=-18.0)
def tarp_out(s, rng):
    """Si esce dal telone: la tela spinta su di colpo (scricchiolio forte), buttata indietro con un colpo
    d'aria, che ricade dietro sul banco; l'aria aperta torna, più chiara."""
    n = s.n
    y = 0.85 * crinkle(rng, s.dur, [(0, 1.0), (0.08, 1.0), (0.25, 0.6), (0.45, 0.25), (0.9, 0)], density=1200,
                       f_lo=450, f_hi=5500, res=1500, swish=0.55)
    sw, _ = _whoosh(rng, 0.32, [(0, 0.3), (0.1, 1.0), (0.32, 0)], 180, 1300, 0.9)
    place(y, 0.5 * sw, 0.02)
    nf = ns(0.3)
    flap = lowpass(rng.standard_normal(nf), 350, 2) * exp_env(nf, 0.16, attack=0.01)
    place(y, 0.55 * normalize(flap), 0.3)
    place(y, 0.15 * knock(rng, 0.004, base=140, t60=0.08, dur=0.25), 0.33)
    na = ns(0.55)
    air = bandpass(rng.standard_normal(na), 1500, 7000) * curve(na, [(0, 0), (0.25, 1), (0.55, 0)])
    place(y, 0.05 * normalize(air), 0.35)
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


def _speaker(x):
    """Il piccolo altoparlante del baracchino: niente bassi, il cono che risuona, un filo di distorsione."""
    y = eq(highpass(x, 260, 2), 'peak', 750, 1.2, 3.0)
    return lowpass(np.tanh(1.4 * y) / np.tanh(1.4), 4300, 2)


def _knob(rng, base=1800.0, a=0.5):
    exc = np.zeros(ns(0.03))
    exc[0], exc[1] = 1.0, -0.5
    return a * normalize(modal(exc, base * np.array([1, 1.72, 2.6]) * rng.uniform(0.97, 1.03, 3), [0.012, 0.008, 0.005],
                               [1, 0.6, 0.3]))


@sound('radio_on', 0.45, category='sfx', gain=0.5, rms=-19.0)
def radio_on(s, rng):
    """Il baracchino si apre: lo scatto del pulsante, lo squelch che si apre di colpo ('kshh'), poi la portante
    che aggancia: il fruscio crolla con un piccolo tonfo nel cono e resta un filo di ronzio."""
    n = s.n
    y = np.zeros(n)
    place(y, _knob(rng, 1800.0, 0.5), 0.0)
    env = curve(n, [(0, 0), (0.004, 1), (0.08, 0.9), (0.12, 0.1), (0.4, 0.06), (0.45, 0)])
    y += 0.8 * _radio_noise(rng, n) * env * (1 + 0.2 * rand_curve(n, 25.0, rng))
    m = ns(0.06)
    thump = np.sin(TWO_PI * phase_of(curve(m, [(0, 180), (0.06, 90)], 'log'))) * curve(m, [(0, 0), (0.005, 1), (0.06, 0)])
    place(y, 0.1 * thump, 0.105)
    tt = tvec(n)
    carrier = (np.sin(TWO_PI * 100 * tt) + 0.3 * np.sin(TWO_PI * 300 * tt)) * curve(n, [(0, 0), (0.11, 0), (0.15, 1), (0.45, 0.8)])
    y += 0.012 * carrier
    return _speaker(y)


@sound('radio_off', 0.4, category='sfx', gain=0.5, rms=-19.0)
def radio_off(s, rng):
    """La trasmissione finisce: la coda dello squelch ('kshhht'), che si chiude secca, e lo scatto del pulsante."""
    n = s.n
    env = curve(n, [(0, 0.35), (0.008, 1.0), (0.2, 0.95), (0.225, 0.0), (0.4, 0.0)])
    y = 0.85 * _radio_noise(rng, n) * env * (1 + 0.2 * rand_curve(n, 30.0, rng))
    y = _speaker(y)
    place(y, _knob(rng, 1650.0, 0.45), 0.228)
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
