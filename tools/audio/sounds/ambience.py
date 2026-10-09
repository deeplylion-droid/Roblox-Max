"""
Ambienti in loop (stereo). Tutto è costruito in modo circolare: rumori sintetizzati nel dominio della
frequenza (periodici), eventi che escono dalla fine e rientrano dall'inizio, oscillatori con un numero
intero di cicli, riverberi per convoluzione circolare. Il punto di loop è quindi continuo per costruzione.
"""
from __future__ import annotations

from instruments import *  # noqa: F401,F403
from sounds import sound


# ───────────────────────── mare ─────────────────────────

def sea_texture(n, rng, swell_cycles, lap_rate=0.22, splashes=0, bed=1.0, bright=1.0, width=0.8, hull=0.35,
                glug_rate=0.3, lap_gain=0.6, follow=0.7, babble=1.5, precursor=0.4):
    """Sciabordio contro lo scafo (loop): il mare respira con l'onda lunga (swell_cycles cicli nel loop). A ogni
    cresta l'acqua sbatte su un fianco e, poco dopo e più piano, sull'altro (l'onda passa sotto la barca); a
    volte un colpetto la precede. Nel cavo quasi silenzio: qualche gorgoglio fra le tavole, bollicine.
    Sotto, un letto d'acqua lontano che segue l'onda (basso: i colpi devono staccarsi)."""
    dur = n / SR
    t = tvec(n)
    out = np.zeros((2, n))
    period = dur / swell_cycles
    swell = 0.5 + 0.5 * np.sin(TWO_PI * swell_cycles * t / dur)
    for c in range(2):
        body = spectral_noise(n, rng, lambda f: bw_bp(f, 60, 800 * bright, 2), exponent=1.0)
        fine = spectral_noise(n, rng, lambda f: bw_bp(f, 900, 5000 * bright, 2), exponent=0.5)
        env = 0.15 + 0.85 * np.roll(swell, c * ns(0.35)) ** 2
        out[c] += bed * (0.012 * body * env + 0.003 * fine * env)
    events = []
    side = 1.0
    for k in range(swell_cycles):
        crest = (k + 0.25) * period + rng.normal(0, 0.08 * period)
        side = float(rng.choice([-1.0, 1.0])) if rng.random() < 0.35 else -side
        st = rng.uniform(0.6, 1.0)
        events.append((crest, st, side))
        if rng.random() < follow:
            events.append((crest + rng.uniform(0.25, 0.6), st * rng.uniform(0.4, 0.7), -side))
        if rng.random() < precursor:
            events.append((crest - rng.uniform(0.2, 0.5), rng.uniform(0.2, 0.4), side))
    for te in poisson_times(rng, lap_rate, 0.0, dur):
        events.append((te, rng.uniform(0.15, 0.4), float(rng.choice([-1.0, 1.0]))))
    for te, st, sd in events:
        y = lap(rng, st, dur=1.0, hull=hull, bright=bright)
        place(out, pan(y, sd * rng.uniform(0.3, width)) * lap_gain * st, te % dur, wrap=True)
    for _ in range(splashes):
        y = splash(rng, size=rng.uniform(0.08, 0.18), dur=0.8)
        place(out, pan(y, rng.uniform(-width, width)) * 0.22, rng.uniform(0, dur), wrap=True)
    # gorgoglii fra le tavole e sotto la chiglia: 'glug' bassi a gruppetti
    for te in poisson_times(rng, glug_rate, 0.0, dur):
        p = rng.uniform(-width, width)
        for j in range(int(rng.integers(1, 4))):
            b = bubble(float(loguniform(rng, 140, 420)), rng.uniform(0.02, 0.15), 0.12 * rng.lognormal(0, 0.3),
                       decay_mult=rng.uniform(0.4, 0.7))
            place(out, pan(b, p + rng.uniform(-0.1, 0.1)), te + j * rng.uniform(0.06, 0.14), wrap=True)
    # bollicine isolate qua e là
    for te in poisson_times(rng, babble, 0.0, dur):
        b = bubble(float(loguniform(rng, 600, 2600)), rng.uniform(0.02, 0.3), 0.035 * rng.lognormal(0, 0.4))
        place(out, pan(b, rng.uniform(-width, width)), te, wrap=True)
    return out


@sound('amb_sea', 32.0, loop=True, channels=2, category='amb', gain=0.85, rms=-26.0)
def amb_sea(s, rng):
    n = s.n
    out = sea_texture(n, rng, swell_cycles=8, splashes=2)
    # onde lontane sugli scogli: un respiro largo e basso, sfasato rispetto al mare vicino
    t = tvec(n)
    far = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 60, 700, 2), exponent=1.0) for _ in range(2)])
    far *= 0.3 + 0.7 * (0.5 + 0.5 * np.sin(TWO_PI * 8 * t / s.dur + 2.2)) ** 2
    out += 0.006 * far
    # bassi presenti ma non rimbombanti
    out = circular(lambda x: eq(highpass(x, 45, 2), 'lowshelf', 110, gain_db=-3.0), out)
    return out


# ───────────────────────── vento ─────────────────────────

def _circ(fn, x, *arrs, pad=1.5):
    """Come circular(), ma con dei parametri per campione (tagli, centri di banda) che girano insieme al segnale."""
    n = x.shape[-1]
    p = min(ns(pad), n)
    tile = lambda a: np.concatenate([a[..., n - p:], a, a[..., :p]], axis=-1)
    return fn(tile(x), *[tile(a) for a in arrs])[..., p:p + n]


@sound('amb_wind', 30.0, loop=True, channels=2, category='amb', gain=0.5, rms=-30.0)
def amb_wind(s, rng):
    """Vento notturno debole sul mare aperto. Raffiche lente che arrivano da un lato e passano all'altro;
    con la raffica il soffio si schiarisce e l'acqua fruscia sotto; le cime e il palo della lampara cantano
    appena (toni eolici che salgono e scendono con la velocità dell'aria); nelle raffiche più forti il bordo
    del telone sbatacchia piano e la cima tocca il palo."""
    n, dur = s.n, s.dur
    swell = rand_curve(n, 0.035, rng)
    gust = rand_curve(n, 0.11, rng)
    G = np.clip(0.48 + 0.2 * swell + 0.3 * gust, 0.06, 1.25)
    lag = ns(0.4)
    out = np.zeros((2, n))
    for c, g in enumerate((G, np.roll(G, lag))):
        # il soffio: rumore rosa che si schiarisce con la raffica
        base = spectral_noise(n, rng, lambda f: bw_bp(f, 35, 7000, 2), exponent=1.1)
        body = _circ(lambda z, fc: tv_lowpass(z, fc, 0.6), base, 320 + 2100 * g ** 1.7)
        # l'acqua che fruscia sotto la raffica (increspature), con un tremolio veloce
        spray = spectral_noise(n, rng, lambda f: bw_bp(f, 1800, 9000, 2)) * \
            np.clip(g - 0.35, 0, None) ** 2.2 * (1 + 0.35 * rand_curve(n, 9.0, rng))
        y = 0.9 * body * g ** 0.9 + 0.5 * spray
        # toni eolici: cima da 8 mm, sartia da 5 mm, lenza sottile (f = 0,2·U/d), solo quando "agganciano"
        for f_ref, amt, q_bw in ((180.0, 0.05, 6.0), (290.0, 0.035, 8.0), (2600.0, 0.012, 60.0)):
            fc = f_ref * (0.55 + 0.55 * g) * cents(15 * rand_curve(n, 0.3, rng))
            lock = np.clip(rand_curve(n, 0.15, rng) * 0.8 + (g - 0.55) * 2.0, 0, None) ** 1.5
            tone = _circ(lambda z, f: tv_bandpass(z, f, q_bw), rng.standard_normal(n), fc)
            y += amt * normalize(tone) * lock
        out[c] = y
    # il bordo del telone e la cima sul palo, solo nelle raffiche forti (eventi circolari)
    t = tvec(n)
    strong = np.clip(G - 0.8, 0, None)
    for tc in poisson_times(rng, lambda tt: 1.6 * np.interp(tt, t, strong) / 0.45, 0.0, dur):
        k = ns(rng.uniform(0.05, 0.11))
        flap = lowpass(rng.standard_normal(k), rng.uniform(500, 900), 2) * exp_env(k, k / SR * 0.8, attack=0.004)
        place(out, pan(0.18 * normalize(flap) * rng.uniform(0.5, 1.0), rng.uniform(-0.3, 0.3)), tc, wrap=True)
    for tc in poisson_times(rng, lambda tt: 0.5 * np.interp(tt, t, strong) / 0.45, 0.0, dur):
        place(out, pan(0.05 * knock(rng, 0.0008, base=420, t60=0.04, dur=0.12), 0.1), tc, wrap=True)
    return circular(lambda x: highpass(x, 30, 2), out)


# ───────────────────────── lampara ─────────────────────────

@sound('amb_lamp', 20.0, loop=True, channels=2, category='amb', gain=0.45, rms=-29.0)
def amb_lamp(s, rng):
    """La lampara accesa sul buttafuori, sopra la tua testa. Il sibilo sottile della lampada, che "frigge"
    appena a 100 Hz come tutte le lampade a scarica; il ronzio del reattore (100 Hz e armoniche, un po'
    ruvido) che respira con la tensione della batteria; i tic del metallo caldo della campana; due volte
    una falena che sbatte contro il vetro e riparte."""
    n, dur = s.n, s.dur
    t = tvec(n)
    breathe = 1.0 + 0.05 * rand_curve(n, 0.25, rng) + 0.02 * rand_curve(n, 3.0, rng)
    ripple = np.abs(np.sin(TWO_PI * 50.0 * t))           # la scarica pulsa a 100 Hz (1000 cicli nel loop)
    out = np.zeros((2, n))
    for c in range(2):
        hiss = spectral_noise(n, rng, lambda f: bw_bp(f, 1500, 11000, 2) * peak_shape(f, 4300, 1.4, 1.9))
        fry = hiss * (0.72 + 0.28 * ripple)
        air = spectral_noise(n, rng, lambda f: bw_bp(f, 300, 1400, 2))
        out[c] = (0.30 * fry + 0.05 * air) * breathe
    # il reattore: 100 Hz con armoniche, saturato appena (lamierini che vibrano)
    hum = np.zeros(n)
    for k, a in [(1, 1.0), (2, 0.42), (3, 0.3), (4, 0.16), (5, 0.1), (6, 0.08), (8, 0.04), (10, 0.025)]:
        hum += a * np.sin(TWO_PI * 100.0 * k * t + rng.uniform(0, TWO_PI))
    hum = np.tanh(1.6 * hum / np.max(np.abs(hum))) * breathe
    out += 0.035 * hum
    # tic del metallo caldo
    for tc in poisson_times(rng, 0.35, 0.0, dur):
        exc = np.zeros(ns(0.06))
        exc[0] = 1.0
        tick = modal(exc, rng.uniform(2600, 5200) * np.array([1, 1.71, 2.6]), [0.03, 0.02, 0.012], [1, 0.5, 0.3])
        place(out, pan(0.02 * normalize(tick) * rng.uniform(0.4, 1.0), rng.uniform(-0.3, 0.3)), tc, wrap=True)
    # la falena: ali a ~35 battiti al secondo, qualche colpetto sul vetro, poi via
    for t0 in (rng.uniform(3.0, 6.0), rng.uniform(12.0, 16.0)):
        d = rng.uniform(1.0, 1.6)
        m = ns(d)
        tt = tvec(m)
        wing = 0.5 + 0.5 * np.sin(TWO_PI * phase_of(rng.uniform(32, 40) * (1 + 0.08 * rand_curve(m, 3.0, rng))))
        flut = bandpass(rng.standard_normal(m), 250, 2600) * wing ** 3 * curve(m, [(0, 0), (0.15, 1), (d - 0.3, 0.8), (d, 0)])
        y = 0.05 * normalize(flut)
        tap_t = 0.2 + np.cumsum(rng.uniform(0.07, 0.3, int(rng.integers(2, 5))))
        for tp in tap_t[tap_t < d - 0.1]:
            exc = np.zeros(ns(0.04))
            exc[0], exc[1] = 1.0, -0.7
            glass = modal(exc, rng.uniform(2200, 3000) * np.array([1, 2.3, 3.9]), [0.018, 0.012, 0.008], [1, 0.6, 0.35])
            place(y, 0.035 * normalize(glass) * rng.uniform(0.5, 1.0), tp)
        p0 = rng.uniform(-0.4, 0.4)
        place(out, pan(y, p0), t0, wrap=True)
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
    # il relitto del peschereccio, lontano sott'acqua: la lamiera che si piega e geme (due volte nel loop)
    wreck = np.zeros(n)
    for t0, d in [(9.0, 3.2), (20.5, 2.6)]:
        m = ns(d)
        rate = curve(m, [(0, 7), (d * 0.4, 16), (d * 0.75, 11), (d, 5)], 'log') * (1 + 0.15 * rand_curve(m, 3.0, rng))
        amp = curve(m, [(0, 0), (d * 0.2, 1), (d * 0.7, 0.8), (d, 0)]) * (0.4 + 0.6 * np.abs(np.tanh(2 * rand_curve(m, 5.0, rng))))
        exc = stick_slip(m, rng, rate, amp, jitter=0.15, grain=0.001)
        fr = np.sort(rng.uniform(70, 900, 14))
        g = modal(exc, fr, rng.uniform(0.8, 2.5, 14), rng.uniform(0.3, 1.0, 14))
        place(wreck, normalize(g), t0, wrap=True)
    wreck = circular(lambda x: lowpass(x, 650, 2), wreck)
    wr = convolve(wreck, reverb_ir(4.0, rng, lo=1.2, hi=0.3, attack=0.06, lp=1200), circular=True)
    wr = 0.2 * stereo(wreck) + wr
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
    # un velo: livello 'attivo' del richiamo ~13 dB sotto il bordone, la lamiera ~15 dB sotto
    w *= rms(out) * db_to_lin(-13.0) / db_to_lin(active_rms_db(w))
    wr *= rms(out) * db_to_lin(-15.0) / db_to_lin(active_rms_db(wr))
    out = out + w + wr
    # pressione dell'acqua profonda: un soffio appena percettibile (30 dB sotto). Serve anche al codec:
    # senza contenuto acuto l'errore di codifica ai bordi del file diventerebbe un tic alla giunzione
    air = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 200, 12000, 1), exponent=1.0) for _ in range(2)])
    return out + air * rms(out) * db_to_lin(-24.0)


# ───────────────────────── sotto il telone ─────────────────────────

@sound('amb_tarp', 16.0, loop=True, channels=2, category='amb', gain=0.8, rms=-28.0)
def amb_tarp(s, rng):
    n, dur = s.n, s.dur
    sea = sea_texture(n, rng, swell_cycles=4, lap_rate=0.3, bed=1.6, bright=0.8, babble=1.0, lap_gain=0.3)
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
    """L'alba: il mare si è calmato (colpetti radi e leggeri), la risacca sulla riva lontana, una brezza, i
    gabbiani che si chiamano dalla baia. I livelli si fissano sull'RMS di ogni strato: i gabbiani devono
    sentirsi, il resto è un letto morbido."""
    n, dur = s.n, s.dur
    t = tvec(n)
    sea = sea_texture(n, rng, swell_cycles=6, lap_rate=0.15, bed=1.0, bright=1.1, hull=0.25, babble=1.5,
                      lap_gain=0.22, follow=0.4, precursor=0.1, glug_rate=0.15)
    # la risacca sulla riva lontana: fruscio largo che sale e si ritira
    shore = np.zeros((2, n))
    for c in range(2):
        sh = spectral_noise(n, rng, lambda f: bw_bp(f, 160, 2400, 2), exponent=0.9)
        ph = TWO_PI * 4 * t / dur + c * 0.6
        env = np.clip(np.sin(ph), 0, None) ** 3 + 0.25 * np.clip(np.sin(ph + 0.5), 0, None) ** 6
        shore[c] = sh * (0.12 + env)
    breeze = wind_layer(n, rng, gust_rate=0.15, low=0.2, mid=0.3, high=0.08, whistle=0.0, bright=1.0)
    gulls = np.zeros((2, n))
    for (tg, p, kind, fb, g) in [(2.2, -0.65, 'long', 1150, 0.9), (9.6, 0.55, 'short', 1250, 0.7),
                                 (14.8, -0.15, 'long', 1050, 0.65), (20.5, 0.75, 'short', 1180, 0.55)]:
        y = gull_call(rng, kind, fb)
        place(gulls, pan(y, p) * g, tg, wrap=True)
    gulls = circular(lambda x: lowpass(x, 4200, 2), gulls)
    ir = reverb_ir(2.4, rng, lo=1.1, hi=0.5, sparse=0.6, early=[(0.33, 0.3, 0.4), (0.7, 0.2, -0.5)])
    gw = gulls + 0.6 * convolve(gulls.mean(axis=0), ir, circular=True)
    ref = rms(sea)
    out = sea + shore * ref / rms(shore) * db_to_lin(-6.0) + breeze * ref / rms(breeze) * db_to_lin(-9.0)
    # i gabbiani: livello 'attivo' appena sotto quello del mare (si sentono, lontani)
    out += gw * ref / db_to_lin(active_rms_db(gw)) * db_to_lin(-2.0)
    return circular(lambda x: highpass(x, 40, 2), out)


# ───────────────────────── statica radio ─────────────────────────

@sound('radio_static', 10.0, loop=True, channels=2, category='amb', gain=0.35, rms=-27.0)
def radio_static(s, rng):
    """Il baracchino VHF aperto senza segnale: il fruscio dell'FM (rumore bianco nella banda della radio,
    attraverso il piccolo altoparlante), che a tratti sfarfalla quando il segnale va e viene; ogni tanto un
    crepitio secco (scariche lontane) e, debolissimo, il fischio di una portante che va alla deriva."""
    n, dur = s.n, s.dur
    t = tvec(n)
    hiss = spectral_noise(n, rng, lambda f: bw_bp(f, 280, 3600, 3) * peak_shape(f, 2300, 1.0, 1.3))
    # sfarfallio (multipath): tratti in cui il fruscio pulsa a 8-14 Hz
    flick_amt = np.clip(rand_curve(n, 0.25, rng) - 0.4, 0, None) * 0.9
    flick = 1.0 - flick_amt * (0.5 + 0.5 * np.sin(TWO_PI * phase_of(periodic_freq(11.0 + 3.0 * rand_curve(n, 0.5, rng)))))
    y = 0.3 * hiss * flick * (1 + 0.08 * rand_curve(n, 2.0, rng))
    # crepitii: singoli e a grappoli, con l'altoparlante che risuona
    times = list(poisson_times(rng, 1.4, 0.0, dur))
    for _ in range(3):
        c0 = rng.uniform(0, dur)
        times += list(c0 + np.cumsum(rng.exponential(0.015, int(rng.integers(3, 8)))))
    crack = np.zeros(n)
    for tc in times:
        k = max(4, ns(rng.uniform(0.0002, 0.0015)))
        imp = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 4.0))
        place(crack, imp * rng.lognormal(-0.3, 0.7), tc % dur, wrap=True)
    crack = circular(lambda x: resonate(x, 720, 1.6) + 0.6 * bandpass(x, 400, 4500), crack)
    y = y + 0.45 * crack
    # la portante lontana: un fischio debolissimo che vaga (cicli interi nel loop)
    fw = periodic_freq(1350.0 * cents(120 * rand_curve(n, 0.08, rng)))
    het = np.sin(TWO_PI * phase_of(fw)) * np.clip(rand_curve(n, 0.1, rng) - 0.3, 0, None)
    y = y + 0.012 * het
    # altoparlante piccolo: niente bassi, un po' di cono
    y = circular(lambda x: lowpass(eq(highpass(x, 260, 2), 'peak', 750, 1.2, 3.0), 4600, 2), y)
    side = spectral_noise(n, rng, lambda f: bw_bp(f, 300, 3500, 2))
    return np.stack([y + 0.02 * side, y - 0.02 * side])
