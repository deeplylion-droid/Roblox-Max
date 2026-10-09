"""
Ambienti in loop (stereo). Tutto è costruito in modo circolare: rumori sintetizzati nel dominio della
frequenza (periodici), eventi che escono dalla fine e rientrano dall'inizio, oscillatori con un numero
intero di cicli, riverberi per convoluzione circolare. Il punto di loop è quindi continuo per costruzione.
"""
from __future__ import annotations

from instruments import *  # noqa: F401,F403
from sounds import sound


# ───────────────────────── mare ─────────────────────────

def sea_texture(n, rng, swell_cycles, lap_rate=0.75, laps_per_wave=(2, 3), splashes=0, bed=1.0,
                bright=1.0, width=0.8, hull=0.35, babble=3.0, lap_gain=0.6):
    """Sciabordio contro lo scafo (loop): letto d'acqua che respira col moto ondoso, colpi d'onda
    vicino alle creste (a destra e a sinistra), colpi sparsi più piccoli, bollicine e qualche schizzo."""
    dur = n / SR
    t = tvec(n)
    out = np.zeros((2, n))
    period = dur / swell_cycles
    swell = 0.5 + 0.5 * np.sin(TWO_PI * swell_cycles * t / dur)
    slow = 0.5 + 0.5 * np.sin(TWO_PI * 3 * t / dur + 1.3)
    for c in range(2):
        body = spectral_noise(n, rng, lambda f: bw_bp(f, 55, 900 * bright, 2), exponent=1.0)
        fine = spectral_noise(n, rng, lambda f: bw_bp(f, 900, 5000 * bright, 2), exponent=0.5)
        env = 0.35 + 0.65 * np.roll(swell, c * ns(0.35)) ** 1.5
        out[c] += bed * (0.022 * body * env + 0.005 * fine * env * (0.6 + 0.4 * slow))
    events = []
    for k in range(swell_cycles):
        crest = (k + 0.25) * period
        for _ in range(int(rng.integers(laps_per_wave[0], laps_per_wave[1] + 1))):
            events.append((crest + rng.normal(0, 0.18 * period), rng.uniform(0.5, 1.0)))
    for te in poisson_times(rng, lap_rate, 0.0, dur):
        events.append((te, rng.uniform(0.15, 0.5)))
    for te, st in events:
        y = lap(rng, st, dur=1.0, hull=hull, bright=bright)
        p = rng.choice([-1.0, 1.0]) * rng.uniform(0.25, width)
        place(out, pan(y, p) * lap_gain * st, te % dur, wrap=True)
    for _ in range(splashes):
        y = splash(rng, size=rng.uniform(0.08, 0.18), dur=0.8)
        place(out, pan(y, rng.uniform(-width, width)) * 0.25, rng.uniform(0, dur), wrap=True)
    # gorgoglii sparsi: bollicine isolate qua e là
    for te in poisson_times(rng, babble, 0.0, dur):
        b = bubble(float(loguniform(rng, 500, 2400)), rng.uniform(0.1, 0.6), 0.05 * rng.lognormal(0, 0.4))
        place(out, pan(b, rng.uniform(-width, width)), te, wrap=True)
    return out


@sound('amb_sea', 32.0, loop=True, channels=2, category='amb', gain=0.85, rms=-26.0)
def amb_sea(s, rng):
    n = s.n
    out = sea_texture(n, rng, swell_cycles=8, splashes=3)
    # onde lontane sugli scogli: un respiro largo e basso, sfasato rispetto al mare vicino
    t = tvec(n)
    far = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 60, 700, 2), exponent=1.0) for _ in range(2)])
    far *= 0.4 + 0.6 * (0.5 + 0.5 * np.sin(TWO_PI * 8 * t / s.dur + 2.2)) ** 2
    out += 0.01 * far
    # bassi presenti ma non rimbombanti
    out = circular(lambda x: eq(highpass(x, 45, 2), 'lowshelf', 110, gain_db=-3.0), out)
    return out


# ───────────────────────── vento ─────────────────────────

@sound('amb_wind', 30.0, loop=True, channels=2, category='amb', gain=0.5, rms=-30.0)
def amb_wind(s, rng):
    out = wind_layer(s.n, rng, gust_rate=0.11, low=0.5, mid=0.33, high=0.1, whistle=0.018, whistle_f=760)
    return circular(lambda x: highpass(x, 30, 2), out)


# ───────────────────────── lampada a pressione ─────────────────────────

@sound('amb_lamp', 8.0, loop=True, channels=2, category='amb', gain=0.45, rms=-29.0)
def amb_lamp(s, rng):
    n = s.n
    t = tvec(n)
    out = np.zeros((2, n))
    # il getto di vapore nel reticella: soffio stabile con leggero tremolio della fiamma
    flick = 1.0 + 0.06 * rand_curve(n, 3.0, rng) + 0.03 * rand_curve(n, 11.0, rng)
    for c in range(2):
        hiss = spectral_noise(n, rng, lambda f: bw_bp(f, 1100, 9500, 2) * peak_shape(f, 3300, 1.2, 1.8))
        mid = spectral_noise(n, rng, lambda f: bw_bp(f, 400, 1500, 2))
        roar = spectral_noise(n, rng, lambda f: bw_bp(f, 70, 400, 2), exponent=1.0)
        out[c] = 0.30 * hiss * flick + 0.09 * mid * flick + 0.13 * roar * flick ** 2
    # ronzio elettrico: 50 Hz con armoniche, 100 Hz dominante (magnetostrizione del trasformatore)
    hum = np.zeros(n)
    for k, a in [(1, 0.35), (2, 1.0), (3, 0.3), (4, 0.45), (5, 0.12), (6, 0.22), (8, 0.08), (10, 0.05), (12, 0.03)]:
        hum += a * np.sin(TWO_PI * 50.0 * k * t + rng.uniform(0, TWO_PI))
    hum *= 1.0 + 0.05 * np.sin(TWO_PI * 0.25 * t)
    out += 0.022 * hum
    return out


# ───────────────────────── bordone ─────────────────────────

@sound('amb_drone', 24.0, loop=True, channels=2, category='amb', gain=0.7, rms=-26.0)
def amb_drone(s, rng):
    n, dur = s.n, s.dur
    t = tvec(n)
    out = np.zeros((2, n))
    # coppie di seni con battimenti lentissimi; frequenze multiple di 1/24 Hz → cicli interi nel loop.
    # Si 0 – Mi 1 – La 1 – Mi 2: quarte sovrapposte, nessuna terza (né maggiore né minore: inquieto)
    pairs = [(30.875, 31.0, 0.7), (41.25, 41.5, 1.0), (55.0, 55.125, 0.8), (82.5, 82.625, 0.3)]
    for c in range(2):
        y = np.zeros(n)
        for i, (f1, f2, a) in enumerate(pairs):
            breath_ = 0.75 + 0.25 * np.sin(TWO_PI * (i + 1) * t / dur + rng.uniform(0, TWO_PI))
            y += a * breath_ * (np.sin(TWO_PI * f1 * t + rng.uniform(0, TWO_PI))
                                + 0.8 * np.sin(TWO_PI * f2 * t + rng.uniform(0, TWO_PI)))
        y = circular(lambda x: softclip(x * 0.35, 1.8, asym=0.15), y, pad=0.1)   # armoniche: si sente anche su casse piccole
        y = circular(lambda x: lowpass(x, 260, 2), y)
        rumble = spectral_noise(n, rng, lambda f: bw_bp(f, 18, 90, 4), exponent=2.0)
        out[c] = y + 0.12 * rumble
    # 'canto di balena' lontanissimo: due richiami filtrati dall'acqua e immersi in un riverbero enorme
    whale = np.zeros(n)
    w1 = whale_moan(rng, 4.6, [(0, 105), (1.4, 205), (2.6, 180), (4.6, 92)],
                    [(0, 'u'), (1.6, 'o'), (2.8, 'a'), (4.6, 'u')], scale=0.6,
                    amp_pts=[(0, 0), (0.8, 1), (3.6, 0.8), (4.6, 0)])
    w2 = whale_moan(rng, 3.4, [(0, 78), (1.8, 150), (3.4, 120)], [(0, 'o'), (2.0, 'u'), (3.4, 'u')],
                    scale=0.55, amp_pts=[(0, 0), (1.0, 0.8), (2.6, 1.0), (3.4, 0)])
    place(whale, w1, 4.0, wrap=True)
    place(whale, w2, 15.5, wrap=True)
    whale = circular(lambda x: lowpass(x, 750, 2), whale)
    ir = reverb_ir(4.5, rng, lo=1.2, hi=0.3, attack=0.05, lp=1500)
    w = 0.25 * stereo(whale) + convolve(whale, ir, circular=True)
    # un velo: livello 'attivo' del richiamo ~13 dB sotto il bordone
    w *= rms(out) * db_to_lin(-13.0) / db_to_lin(active_rms_db(w))
    out = out + w
    # pressione dell'acqua profonda: un soffio appena percettibile (30 dB sotto). Serve anche al codec:
    # senza contenuto acuto l'errore di codifica ai bordi del file diventerebbe un tic alla giunzione
    air = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 200, 12000, 1), exponent=1.0) for _ in range(2)])
    return out + air * rms(out) * db_to_lin(-30.0)


# ───────────────────────── sotto il telone ─────────────────────────

@sound('amb_tarp', 16.0, loop=True, channels=2, category='amb', gain=0.8, rms=-28.0)
def amb_tarp(s, rng):
    n, dur = s.n, s.dur
    sea = sea_texture(n, rng, swell_cycles=4, lap_rate=0.4, bed=1.3, bright=0.8, babble=1.0, lap_gain=0.25)
    # la tela cerata filtra tutto: passa-basso ~600 Hz e una lieve risonanza dello spazio chiuso
    sea = circular(lambda x: eq(lowpass(x, 600, 4), 'peak', 170, 1.2, 4.0), sea)
    sea = circular(lambda x: highpass(x, 40, 2), sea)
    out = sea
    # la tela si muove appena: pochi fruscii vicini, non attutiti ma sottilissimi
    for _ in range(6):
        d = rng.uniform(0.3, 0.9)
        cr = crinkle(rng, d, [(0, 0), (d * 0.4, 1), (d, 0)], density=rng.uniform(150, 400), f_lo=600, f_hi=4500)
        place(out, pan(cr, rng.uniform(-0.8, 0.8)) * 0.012, rng.uniform(0, dur), wrap=True)
    # respiro trattenuto, bassissimo: inspiro breve dal naso, pausa, espiro lento e tremante
    br = np.zeros(n)
    t0 = 0.4
    for k in range(4):
        ti = rng.uniform(0.8, 1.1)
        hold = rng.uniform(0.3, 0.7)
        te = rng.uniform(1.4, 1.9)
        inh = breath(rng, ti, inhale=True, amp_pts=[(0, 0), (ti * 0.6, 1), (ti, 0)], dark=1.2)
        exh = breath(rng, te, inhale=False, amp_pts=[(0, 0), (0.25, 0.8), (te * 0.6, 0.55), (te, 0)],
                     tremor=0.35, dark=0.8)
        place(br, inh * 0.7, t0, wrap=True)
        place(br, exh, t0 + ti + hold, wrap=True)
        t0 += dur / 4 + rng.uniform(-0.3, 0.3)
    br = circular(lambda x: lowpass(x, 3500, 2), br)
    out += 0.016 * stereo(br)
    return out


# ───────────────────────── alba ─────────────────────────

@sound('amb_dawn', 24.0, loop=True, channels=2, category='amb', gain=0.8, rms=-26.0)
def amb_dawn(s, rng):
    n, dur = s.n, s.dur
    t = tvec(n)
    out = sea_texture(n, rng, swell_cycles=6, lap_rate=0.25, laps_per_wave=(0, 2), bed=1.2, bright=1.1,
                      hull=0.25, babble=1.5, lap_gain=0.18)
    # onde calme sulla riva lontana: fruscio largo che sale e si ritira
    for c in range(2):
        sh = spectral_noise(n, rng, lambda f: bw_bp(f, 140, 2600, 2), exponent=0.8)
        ph = TWO_PI * 4 * t / dur + c * 0.6
        env = np.clip(np.sin(ph), 0, None) ** 3 + 0.25 * np.clip(np.sin(ph + 0.5), 0, None) ** 6
        out[c] += 0.05 * sh * (0.2 + env)
    # brezza leggera
    out += 0.45 * wind_layer(n, rng, gust_rate=0.15, low=0.25, mid=0.3, high=0.16, whistle=0.0, bright=1.3)
    # gabbiani lontani (riverbero di baia, molto passa-basso)
    gulls = np.zeros((2, n))
    for (tg, p, kind, fb, g) in [(2.2, -0.65, 'long', 1150, 0.9), (9.6, 0.55, 'short', 1250, 0.7),
                                 (14.8, -0.15, 'long', 1050, 0.6), (20.5, 0.75, 'short', 1180, 0.5)]:
        y = gull_call(rng, kind, fb)
        place(gulls, pan(y, p) * g, tg, wrap=True)
    gulls = circular(lambda x: lowpass(x, 3800, 2), gulls)
    ir = reverb_ir(2.4, rng, lo=1.1, hi=0.5, sparse=0.6, early=[(0.33, 0.3, 0.4), (0.7, 0.2, -0.5)])
    gw = gulls + 0.6 * convolve(gulls.mean(axis=0), ir, circular=True)
    out += 0.035 * gw
    out = circular(lambda x: highpass(x, 40, 2), out)
    return out


# ───────────────────────── statica radio ─────────────────────────

@sound('radio_static', 6.0, loop=True, channels=2, category='amb', gain=0.35, rms=-27.0)
def radio_static(s, rng):
    n, dur = s.n, s.dur
    base = spectral_noise(n, rng, lambda f: bw_bp(f, 250, 4500, 3) * peak_shape(f, 2400, 1.0, 1.4))
    flutter = 1.0 + 0.15 * rand_curve(n, 2.0, rng) + 0.07 * rand_curve(n, 15.0, rng)
    hiss = base * flutter
    crack = np.zeros(n)
    times = list(poisson_times(rng, 7.0, 0.0, dur))
    for _ in range(5):        # qualche grappolo di crepitii
        c0 = rng.uniform(0, dur)
        times += list(c0 + np.cumsum(rng.exponential(0.012, int(rng.integers(3, 9)))))
    for tc in times:
        k = max(4, ns(rng.uniform(0.0003, 0.002)))
        imp = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 4.0))
        place(crack, imp * rng.lognormal(0, 0.7), tc, wrap=True)
    crack = circular(lambda x: bandpass(x, 300, 5000), crack)
    y = 0.25 * hiss + 0.35 * crack
    side = spectral_noise(n, rng, lambda f: bw_bp(f, 300, 4000, 2))
    return np.stack([y + 0.02 * side, y - 0.02 * side])
