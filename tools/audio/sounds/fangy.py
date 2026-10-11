"""
Fangy (notte 5, stare zitti): il bambino che giocava a Marco Polo a occhi chiusi e vinceva sempre, ora un mastino
degli abissi blu notte, curvo e basso, col testone del pesce dente di sciabola, le zanne del pesce vipera che pendono
fuori dalla bocca, le fossette per sentire e gli occhialini da piscina dipinti di nero affondati nella carne. È cieco
e caccia a orecchio. Lo annuncia una fila di lucine azzurre che arriva sott'acqua; sale accanto alla barca, dietro il
pescatore, e ascolta. A ogni rumore gira la testa di scatto; al terzo è addosso. Non parla. Mono (si spazializza nel
gioco), tranne il jumpscare.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

BOY = 1.32        # scala delle formanti: un bambino (la voce che resta sotto il ringhio)
MASTIFF = 0.62    # una gola enorme


def _finish(y, rng, room=0.12, lp=10000.0):
    return roomify(lowpass(highpass(y, 35, 2), lp, 2), rng, room)


def _breath(rng, dur, inhale=True, size=1.0, wet_amt=0.5):
    """Un fiato lungo da un muso grande attraverso le zanne: soffio nasale e di gola (risonanze basse), il fischio
    sottile fra i denti, la saliva che crepita. inhale: l'aria che entra (sale), altrimenti che esce (cala)."""
    n = ns(dur)
    nz = rng.standard_normal(n)
    f = 1.0 / max(size, 0.4) ** 0.5
    body = 0.6 * resonate(nz, 420 * f, 2.0) + 0.5 * resonate(nz, 980 * f, 2.6) + 0.3 * resonate(nz, 2100 * f, 3.0)
    # il petto grande: sotto, un brontolio d'aria che vibra appena nella gola
    rumble = lowpass(nz, 160 * f, 2) * (0.7 + 0.3 * np.abs(rand_curve(n, 18.0, rng)))
    body = lowpass(highpass(body, 110, 2), 2600, 4) + 0.5 * normalize(rumble) * np.max(np.abs(body))
    # il fischio fra le zanne: rumore a banda stretta che vaga
    fw = curve(n, [(0, 2600), (dur, 3300 if inhale else 2300)], 'log') * cents(60 * rand_curve(n, 2.0, rng))
    whistle = tv_bandpass(nz, fw, fw * 0.06)
    y = normalize(body) + 0.12 * normalize(whistle)
    pts = [(0, 0), (dur * 0.4, 0.6), (dur * 0.85, 1.0), (dur, 0)] if inhale else \
        [(0, 0), (dur * 0.15, 1.0), (dur * 0.55, 0.55), (dur, 0)]
    y = y * curve(n, pts)
    if wet_amt:
        y = y + wet_amt * 0.18 * saliva(rng, dur, rate=50, f_lo=700, f_hi=3200, env_pts=pts)
    return normalize(y)


def _fang_tick(rng, amp=1.0):
    """Le zanne lunghe che si toccano: pochi aghi d'osso, secchi."""
    return amp * teeth_clack(rng, count=int(rng.integers(2, 5)), spread=0.003, glass=0.15, dur=0.08)


# ───────────────────────── le lucine che arrivano ─────────────────────────

def _approach(s, rng):
    """Le lucine che arrivano sott'acqua dal largo: un pulsare grave e lento (le pinne del corpo grande che spingono
    l'acqua) che si avvicina e si fa più chiaro, il ronzio sottile e freddo delle lucine che respirano, le bolle che
    salgono dal fondo. Tutto ovattato, sotto il pelo dell'acqua."""
    n, d = s.n, s.dur
    t = tvec(n)
    y = np.zeros(n)
    # il pulsare: colpi d'acqua sordi, sempre più vicini e più frequenti
    tt = 0.15
    k = 0
    while tt < d - 0.2:
        g = 0.35 + 0.65 * (tt / d) ** 1.4
        m = ns(0.5)
        thump = lowpass(rng.standard_normal(m), 70 + 110 * tt / d, 2) * exp_env(m, 0.22, attack=0.03)
        place(y, g * normalize(thump), tt)
        tt += 0.62 - 0.22 * tt / d + rng.uniform(-0.03, 0.03)
        k += 1
    # l'acqua spinta: fruscio scuro che si apre mentre arriva
    fc = curve(n, [(0, 220), (d, 900)], 'log')
    swash = tv_lowpass(spectral_noise(n, rng, lambda f: bw_bp(f, 60, 2000, 2), exponent=1.0), fc)
    y += 0.25 * normalize(swash) * curve(n, [(0, 0), (0.6, 0.4), (d - 0.3, 1.0), (d, 0.6)])
    # il ronzio delle lucine: un filo freddo e acuto che respira (lento, poi più in fretta)
    br = 0.5 + 0.5 * np.sin(TWO_PI * np.cumsum(curve(n, [(0, 0.35), (d, 0.7)])) / SR)
    hum = np.sin(TWO_PI * phase_of(np.full(n, 2350.0) * cents(8 * rand_curve(n, 1.0, rng))))
    hum += 0.4 * np.sin(TWO_PI * phase_of(np.full(n, 3530.0) * cents(10 * rand_curve(n, 1.3, rng))))
    y += 0.035 * hum * br * curve(n, [(0, 0), (1.0, 0.5), (d, 1.0)])
    # bolle che salgono
    for tb in poisson_times(rng, 5.0, 0.1, d - 0.15):
        place(y, bubble(float(loguniform(rng, 260, 900)), xi=rng.uniform(0.02, 0.2), amp=rng.uniform(0.04, 0.12)), tb)
    y = lowpass(y, 2600, 2) + 0.6 * highpass(0.035 * hum * br, 1800, 2) * curve(n, [(0, 0), (d, 1)])
    return _finish(y, rng, room=0.2, lp=5000.0)


register('fangy_approach', _approach, 3.6, category='mon', gain=0.7, rms=-22.0, max_gr=5.0)


# ───────────────────────── sale accanto alla barca ─────────────────────────

def _rise(s, rng):
    """Sale accanto alla barca, dietro di te: l'acqua che si apre piano e gli cola di dosso a lungo, le nocche che
    toccano la fiancata (un colpo sordo, vicinissimo), le zanne che gocciolano, e un fiato lungo dentro il muso: annusa
    l'aria con le fossette, in ascolto."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    place(y, 0.75 * splash(rng, size=0.55, dur=1.4), 0.0)
    # l'acqua che gli cola di dosso
    m = ns(1.6)
    pour = bandpass(rng.standard_normal(m), 500, 6000, 2) * (0.5 + 0.5 * np.abs(np.tanh(2 * rand_curve(m, 25.0, rng))))
    place(y, 0.22 * normalize(pour) * curve(m, [(0, 0), (0.15, 1), (0.9, 0.6), (1.6, 0)]), 0.2)
    for td in poisson_times(rng, 9.0, 0.3, d - 0.1):
        place(y, droplet(rng, amp=rng.uniform(0.05, 0.16), tonal=0.4), td)
    # le nocche sulla fiancata
    place(y, 0.7 * knuckle_knock(rng, force=0.0013, dur=0.45, wet_amt=0.6, hard=0.6), 0.55)
    # il fiato lungo
    place(y, 0.55 * _breath(rng, 1.1, inhale=True, size=1.3), 0.95)
    place(y, _fang_tick(rng, 0.25), 1.75)
    return _finish(y, rng, room=0.14)


register('fangy_rise', _rise, 2.4, category='mon', gain=0.85, rms=-18.5, max_gr=6.0)


# ───────────────────────── ascolta ─────────────────────────

def _listen(s, rng):
    """Mentre ascolta (in loop, il gioco ne regola il volume): un respiro lento e bagnato fra le zanne, trattenuto
    ogni tanto per sentire meglio, l'acqua che gli sciaborda contro il petto, le gocce che cadono dalle zanne nel mare,
    e di rado le zanne che si toccano. Basso e vicino: lo senti dietro le spalle."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    # tre respiri in 9 s: dentro lungo, fuori lungo, poi una pausa trattenuta
    for t0 in (0.0, 3.0, 6.0):
        place(y, 0.5 * _breath(rng, 1.15, inhale=True, size=1.4, wet_amt=0.4), t0 + 0.1, wrap=True)
        place(y, 0.42 * _breath(rng, 1.3, inhale=False, size=1.4, wet_amt=0.6), t0 + 1.35, wrap=True)
    # l'acqua contro il petto
    for tl in np.arange(0.4, d, 1.8) + rng.uniform(-0.2, 0.2, len(np.arange(0.4, d, 1.8))):
        place(y, 0.22 * lap(rng, 0.6, dur=0.9, hull=0.0, clop_prob=0.5, bright=0.8), float(tl) % d, wrap=True)
    for td in poisson_times(rng, 1.6, 0.0, d):
        place(y, droplet(rng, amp=rng.uniform(0.04, 0.1), tonal=0.55), td, wrap=True)
    for tk in (2.6, 8.1):
        place(y, _fang_tick(rng, 0.18), tk + rng.uniform(-0.1, 0.1), wrap=True)
    y = circular(lambda x: lowpass(highpass(x, 40, 2), 9000, 2), y)
    return y


register('fangy_listen', _listen, 9.0, loop=True, category='mon', gain=0.6, rms=-25.0, max_gr=4.0)


# ───────────────────────── ti ha sentito ─────────────────────────

def _snap(s, rng):
    """Ti ha sentito: la testa che scatta sul collo verso il rumore (lo schiocco della cartilagine, il collo grosso che
    si torce nell'acqua), le zanne che sbattono, e un'annusata secca e forte dalle fossette."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.85 * bone_crack(rng, size=0.8, dur=0.25, bright=0.8), 0.0)
    m = ns(0.22)
    twist = bandpass(rng.standard_normal(m), 150, 1400, 2) * curve(m, [(0, 0), (0.02, 1), (0.22, 0)])
    place(y, 0.35 * normalize(twist), 0.0)
    place(y, 0.55 * teeth_clack(rng, count=int(rng.integers(5, 9)), spread=0.006, glass=0.2, dur=0.12), 0.03)
    place(y, 0.6 * big_sniff(rng, dur=rng.uniform(0.18, 0.26), f=0.7, wet_amt=0.7), 0.12)
    for td in rng.uniform(0.06, 0.4, 4):
        place(y, droplet(rng, amp=rng.uniform(0.05, 0.12), tonal=0.5), float(td))
    return _finish(y, rng, room=0.1)


for _k, _sid in enumerate(('fangy_snap', 'fangy_snap_2', 'fangy_snap_3')):
    register(_sid, _snap, 0.65, category='mon', gain=0.9, rms=-17.0, max_gr=6.0)


# ───────────────────────── torna giù ─────────────────────────

def _leave(s, rng):
    """Torna giù senza fretta: un fiato lungo che esce gorgogliando mentre il muso va sotto, l'acqua che si richiude
    sopra la testa (un tonfo morbido e grave), le bolle che risalgono, lo sciabordio contro la fiancata."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    ex = _breath(rng, 0.9, inhale=False, size=1.4, wet_amt=0.8)
    place(y, 0.5 * wet_throat(ex, rng, rate=16.0, depth=0.5, bubbles=0.5, flange=0.3), 0.0)
    place(y, 0.6 * splash(rng, size=0.35, dur=1.0), 0.7)
    place(y, 0.5 * bubble(rng.uniform(150, 210), xi=0.02, amp=1.0, decay_mult=1.2, max_dur=0.35), 0.78)
    bubble_burst(y, rng, 0.85, 14, 0.25, 220, 1100, 0.18, xi=(0.0, 0.06))
    place(y, 0.3 * lap(rng, 0.8, dur=1.0, hull=0.4), 1.15)
    return _finish(y, rng, room=0.16, lp=7000.0)


register('fangy_leave', _leave, 2.2, category='mon', gain=0.8, rms=-19.5, max_gr=6.0)


# ───────────────────────── jumpscare ─────────────────────────

def _js_fangy(s, rng):
    """Ti è addosso: l'acqua che esplode sulla fiancata, la bocca che si spalanca con lo schiocco della mascella e le
    zanne che sbattono, e il ruggito: un mastino enorme dentro una gola d'acqua, con sopra, alta e rotta, la voce di un
    bambino che strilla (il gioco è finito: ti ha preso)."""
    n, d = s.n, s.dur
    f0_pts = [(0, 85), (0.08, 128), (0.5, 118), (0.95, 132), (1.25, 104), (d, 70)]
    amp = [(0, 0.5), (0.05, 1), (1.2, 0.9), (d, 0.3)]
    roar = vox(rng, d, f0_pts, [(0, 'a'), (0.2, 'O'), (1.0, 'a'), (d, 'u')], scale=MASTIFF, amp_pts=amp, oq=0.4,
               jitter=0.06, shimmer=0.25, sub=0.6, breath=0.55, bw=1.5, rough=0.75, rough_rate=38.0, rough_fm=70.0,
               wander=45.0)
    roar = wet_throat(roar, rng, rate=24.0, depth=0.5, bubbles=0.45, flange=0.35)
    kid_pts = [(0, 620), (0.07, 940), (0.45, 1010), (0.9, 900), (1.2, 980), (d, 640)]
    kid = np.zeros(n)
    for k, det in enumerate((-15.0, 0.0, 14.0)):
        pts = [(t, f * cents(det)) for t, f in kid_pts]
        kid += (1.0 if k == 1 else 0.55) * vox(rng, d, pts, [(0, 'ae'), (0.12, 'a'), (1.0, 'a'), (d, '@')], scale=BOY,
                                              amp_pts=[(0, 0), (0.06, 1), (1.15, 0.9), (d, 0.3)], oq=0.42,
                                              jitter=0.05, shimmer=0.2, sub=0.25, breath=0.5, bw=1.4, rough=0.6,
                                              rough_rate=60.0, rough_fm=55.0, wander=35.0)
    y = 0.9 * normalize(roar) + 0.5 * normalize(kid)
    place(y, 0.7 * splash(rng, size=1.0, dur=1.3), 0.0)
    place(y, 0.8 * bone_crack(rng, size=1.0, dur=0.3, bright=0.7), 0.02)
    for t0 in (0.05, 0.4, 0.95):
        place(y, 0.3 * teeth_clack(rng, count=10, spread=0.01, glass=0.25, dur=0.2), t0)
    ir = near_room(rng, 0.45, stereo_out=True)
    out = stereo(y) * np.sqrt(0.5) + 0.22 * convolve(y, ir)
    out = lowpass(highpass(out, 50, 2), 12000, 2)
    return scream_master(out, drive=2.0)


register('js_fangy', _js_fangy, 1.6, channels=2, category='mon', gain=1.0, rms=-6.6, max_gr=6.5, release=0.03)
