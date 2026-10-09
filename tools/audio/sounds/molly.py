"""
Molly (fianchi, va fissata): la bambina che dal trampolino gridava «Guardami!», ora una testa piatta da
pesce luna con gli occhi bianchi, i braccioli gonfiabili e le dita lunghissime. Bussa sullo scafo con le
nocche, ride, piagnucola, fa i capricci e dondola la barca. La voce è di bambina (tratto vocale corto:
formanti alte, tanto soffio) ma bagnata e "doppia": sotto, a tratti, la stessa voce da una gola molto più
grande, mai esattamente all'ottava. Niente parole: solo versi. Mono (si spazializza nel gioco), tranne
il dondolio della barca e il jumpscare.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

CHILD = 1.4      # scala delle formanti: una bambina di sette anni


def _child(rng, d, f0_pts=None, vowels=((0.0, '@'),), amp_pts=None, **kw):
    """Voce di bambina: formanti alte e larghe, molto soffio, un filo di tremolio."""
    kw.setdefault('scale', CHILD)
    kw.setdefault('oq', 0.58)
    kw.setdefault('jitter', 0.028)
    kw.setdefault('shimmer', 0.14)
    kw.setdefault('breath', 0.5)
    kw.setdefault('breath_base', 0.5)
    kw.setdefault('bw', 1.6)
    kw.setdefault('wander', 22.0)
    return vox(rng, d, f0_pts, vowels, amp_pts=amp_pts, **kw)


def _ghost(rng, d, f0_pts, vowels=((0.0, '@'),), amp_pts=None, ratio=0.47, **kw):
    """La stessa frase da una gola più grande, sotto (rapporto mai d'ottava esatta: suona sbagliato)."""
    kw.setdefault('scale', 0.95)
    kw.setdefault('oq', 0.5)
    kw.setdefault('jitter', 0.03)
    kw.setdefault('shimmer', 0.15)
    kw.setdefault('sub', 0.4)
    kw.setdefault('breath', 0.3)
    kw.setdefault('bw', 1.3)
    kw.setdefault('wander', 20.0)
    pts = [(t, f * ratio) for t, f in f0_pts]
    return vox(rng, d, pts, vowels, amp_pts=amp_pts, **kw)


def _finish(y, rng, room=0.14, lp=9000.0):
    return roomify(lowpass(highpass(y, 90, 2), lp, 2), rng, room)


# ───────────────────────── nocche sullo scafo ─────────────────────────

def _knocks(s, rng):
    p = s.params
    y = np.zeros(s.n)
    for t0, a in p['pattern']:
        k = knuckle_knock(rng, force=rng.uniform(0.0008, 0.0013), dur=0.45, wet_amt=0.35, hard=rng.uniform(0.8, 1.1))
        place(y, a * rng.uniform(0.9, 1.0) * k, t0 + rng.uniform(-0.008, 0.008))
    if p.get('scrape'):
        t0, d = p['scrape']
        sc = nail_scrape(rng, d, [(0, 300), (d * 0.3, 620), (d, 420)], [(0, 0), (0.05, 1), (d * 0.6, 0.7), (d, 0)])
        place(y, 0.32 * sc, t0)
        place(y, 0.18 * squish(rng, 0.08, 500, 2500, density=900, sticky=0.3), t0 + d - 0.02)
    return _finish(y, rng, room=0.1)


for _sid, _d, _p in [
    # tre colpi lenti e regolari: la pazienza di chi sa che prima o poi ti giri
    ('molly_knock_1', 1.3, {'pattern': [(0.0, 1.0), (0.43, 0.88), (0.88, 1.0)]}),
    # "toc-toc ... toc"
    ('molly_knock_2', 1.1, {'pattern': [(0.0, 0.95), (0.155, 0.78), (0.64, 1.0)]}),
    # quattro colpi che accelerano, poi le unghie che grattano giù per il fasciame
    ('molly_knock_3', 1.65, {'pattern': [(0.0, 0.8), (0.3, 0.88), (0.52, 0.95), (0.68, 1.0)], 'scrape': (0.86, 0.7)}),
]:
    register(_sid, _knocks, _d, category='mon', gain=0.9, rms=-16.0, max_gr=6.0, release=0.02, params=_p)


# ───────────────────────── risatine ─────────────────────────

def _giggle_1(s, rng):
    """«Hi-hi-hi-hi-hiii»: cinque sillabe che scendono, l'ultima lunga che crolla di un'ottava come un nastro
    che rallenta e finisce in un gorgoglio. Sotto, sempre più presente, l'altra gola."""
    d = 1.15
    n = ns(d)
    ons = [0.0, 0.135, 0.275, 0.425, 0.585]
    durs = [0.09, 0.09, 0.095, 0.1, 0.42]
    f0_pts = []
    for i, t0 in enumerate(ons):
        f = 590 * 0.95 ** i
        f0_pts += [(t0 + 0.005, f * 1.04), (t0 + durs[i] * 0.8, f * 0.9)]
    f0_pts += [(d, 330)]
    vowels = [(0, 'E'), (0.3, 'e'), (0.6, 'E'), (0.75, 'ae'), (d, '@')]
    voiced = pulses(n, [o + 0.025 for o in ons], [x - 0.025 for x in durs], att=0.008, rel=0.018)
    hn = pulses(n, ons, [0.032] * 5, att=0.003, rel=0.012, levels=[1.0, 0.9, 0.9, 0.85, 0.8])
    amp = np.maximum(voiced, 0.55 * hn) * curve(n, [(0, 1), (0.6, 0.9), (d, 0.7)])
    v = _child(rng, d, f0_pts, vowels, amp_pts=amp, voicing=voiced, hnoise=2.4 * hn, breath=0.65, rough=0.3,
               rough_rate=38.0, rough_fm=25.0)
    g = _ghost(rng, d, f0_pts, vowels, amp_pts=amp * curve(n, [(0, 0.1), (0.5, 0.5), (d, 1.0)]), voicing=voiced,
               hnoise=0.4 * hn)
    y = v + 0.3 * g
    y = tape_bend(y, [(0, 1.0), (0.66, 1.0), (0.82, 0.8), (d, 0.55)])
    y = wet_throat(y, rng, rate=14, depth=0.25, bubbles=0.2, flange=0.1, f_lo=300, f_hi=1100)
    out = np.zeros(s.n)
    place(out, y, 0.0)
    place(out, 0.35 * throat_bubbles(rng, 0.45, rate=40, f_lo=250, f_hi=900, env_pts=[(0, 0), (0.1, 1), (0.45, 0)]), 0.82)
    return _finish(out, rng)


def _giggle_2(s, rng):
    """Risata trattenuta e inspirata («hhk-hhk-hhk», stridula), poi due «he-he» espirati più in basso e un
    sospiro con le bolle."""
    out = np.zeros(s.n)
    d = 0.5
    n = ns(d)
    ons = [0.0, 0.12, 0.245, 0.375]
    durs = [0.075] * 4
    f0_pts = []
    for i, t0 in enumerate(ons):
        f = 820 * 0.97 ** i
        f0_pts += [(t0 + 0.004, f), (t0 + 0.07, f * 1.06)]
    f0_pts += [(d, 760)]
    voiced = pulses(n, ons, durs, att=0.006, rel=0.02)
    v = _child(rng, d, f0_pts, [(0, 'e'), (d, 'i')], amp_pts=voiced, voicing=0.6 * voiced, hnoise=1.8 * voiced,
               breath=0.9, jitter=0.05, shimmer=0.22, oq=0.45, rough=0.35, rough_rate=45.0)
    place(out, 0.85 * v, 0.0)
    d2 = 0.42
    n2 = ns(d2)
    ons2 = [0.0, 0.17]
    durs2 = [0.12, 0.2]
    f2 = [(0.0, 470), (0.1, 430), (0.17, 450), (0.33, 380), (d2, 350)]
    voiced2 = pulses(n2, [o + 0.03 for o in ons2], [x - 0.03 for x in durs2], att=0.01, rel=0.04)
    hn2 = pulses(n2, ons2, [0.05, 0.05], att=0.004, rel=0.02)
    v2 = _child(rng, d2, f2, [(0, 'e'), (d2, 'E')], amp_pts=np.maximum(voiced2, 0.7 * hn2), voicing=voiced2, hnoise=2.0 * hn2)
    g2 = _ghost(rng, d2, f2, [(0, 'e'), (d2, 'E')], amp_pts=voiced2, voicing=voiced2, ratio=0.45)
    place(out, v2 + 0.35 * g2, 0.56)
    sig = tract_noise(rng, 0.45, [(0, 'a'), (0.45, '@')], scale=CHILD, amp_pts=[(0, 0), (0.08, 1), (0.45, 0)], hiss=0.2)
    sig = wet_throat(sig, rng, rate=24, depth=0.6, bubbles=0.6, f_lo=250, f_hi=900)
    place(out, 0.4 * sig, 1.0)
    return _finish(out, rng)


register('molly_giggle_1', _giggle_1, 1.3, category='mon', gain=0.8, rms=-17.0)
register('molly_giggle_2', _giggle_2, 1.5, category='mon', gain=0.8, rms=-17.0)


# ───────────────────────── piagnucolio ─────────────────────────

def _sob(rng, d, f0_pts, vowels, amp_pts, crack_at=None, trem=0.35, ghost=0.18):
    """Un singhiozzo lamentoso con il tremito del pianto; crack_at: la voce che si spezza (salto in basso)."""
    n = ns(d)
    f0 = curve(n, f0_pts, 'log')
    if crack_at is not None:
        f0 = f0 * (1 - 0.42 * gate_env(n, crack_at, crack_at + 0.07, 0.006, 0.012))
    tr = 1 + trem * np.tanh(1.5 * rand_curve(n, 6.5, rng))
    v = _child(rng, d, f0=f0, vowels=vowels, amp_pts=curve(n, amp_pts) * tr, breath=0.6, jitter=0.035,
               shimmer=0.16, vib=(45.0, 6.2), wander=40.0, rough=0.2, rough_rate=33.0, rough_fm=20.0)
    g = _ghost(rng, d, f0_pts, vowels, amp_pts=amp_pts, ratio=0.46)
    return v + ghost * g


def _gasps(rng, times, dur=0.07):
    """Inspiri a scatti del pianto (singulti)."""
    y = np.zeros(ns(max(times) + dur + 0.05))
    for i, t0 in enumerate(times):
        g = tract_noise(rng, dur, [(0, 'i'), (dur, 'e')], scale=CHILD, amp_pts=[(0, 0.2), (dur * 0.6, 1), (dur, 0)],
                        bw=1.2, hiss=0.5)
        place(y, g * (0.8 + 0.2 * i), t0)
    return normalize(y)


def _whine_1(s, rng):
    """«Uuuh… uuh»: due singhiozzi, in mezzo i singulti, il secondo con la voce che si spezza."""
    out = np.zeros(s.n)
    place(out, _sob(rng, 0.78, [(0, 470), (0.16, 545), (0.5, 505), (0.78, 380)], [(0, 'o'), (0.4, '@'), (0.78, 'O')],
                    [(0, 0.35), (0.06, 1), (0.55, 0.8), (0.78, 0)]), 0.0)
    place(out, 0.35 * _gasps(rng, [0.0, 0.11, 0.2]), 0.8)
    place(out, 0.9 * _sob(rng, 0.85, [(0, 450), (0.25, 480), (0.85, 330)], [(0, 'o'), (0.5, 'u'), (0.85, '@')],
                          [(0, 0), (0.1, 1), (0.6, 0.7), (0.85, 0)], crack_at=0.48, ghost=0.25), 1.08)
    y = wet_throat(out, rng, rate=12, depth=0.25, bubbles=0.25, flange=0.2, f_lo=300, f_hi=1000)
    return _finish(y, rng)


def _whine_2(s, rng):
    """«Mmmh-mm… uuh»: piagnucolio a bocca chiusa (nasale) che trema, poi si apre in un lamento."""
    out = np.zeros(s.n)
    place(out, _sob(rng, 0.65, [(0, 400), (0.2, 455), (0.4, 410), (0.65, 430)], [(0, 'm'), (0.65, 'n')],
                    [(0, 0), (0.06, 0.9), (0.5, 1), (0.65, 0.3)], trem=0.45, ghost=0.12), 0.0)
    place(out, 0.8 * _sob(rng, 0.3, [(0, 430), (0.3, 395)], [(0, 'm'), (0.3, 'm')], [(0, 0.3), (0.1, 1), (0.3, 0)], ghost=0.1), 0.68)
    place(out, 0.3 * _gasps(rng, [0.0, 0.09]), 1.02)
    place(out, _sob(rng, 0.6, [(0, 520), (0.12, 560), (0.6, 360)], [(0, 'u'), (0.3, 'o'), (0.6, 'u')],
                    [(0, 0), (0.07, 1), (0.6, 0)], ghost=0.3), 1.22)
    # il fiato dal naso e dalla bocca che trema (si sente da dove viene)
    nose = tract_noise(rng, 1.85, [(0, 'n'), (1.1, 'm'), (1.3, 'u'), (1.85, 'u')], scale=CHILD,
                       amp_pts=[(0, 0.3), (0.3, 0.8), (1.0, 0.6), (1.3, 1.0), (1.85, 0)], hiss=0.8)
    place(out, 0.12 * nose, 0.0)
    y = wet_throat(out, rng, rate=12, depth=0.25, bubbles=0.25, flange=0.2, f_lo=300, f_hi=1000)
    return _finish(y, rng)


register('molly_whine_1', _whine_1, 2.05, category='mon', gain=0.8, rms=-17.0)
register('molly_whine_2', _whine_2, 1.95, category='mon', gain=0.8, rms=-17.0)


# ───────────────────────── capriccio ─────────────────────────

def _scream(rng, d, f0_pts, vowels, amp_pts, *, crack_at=None, chaos=(0.35, 0.65), rough=0.6, rough_rate=62.0,
            ghost=0.3, scale=CHILD):
    """Strillo di bambina: voce tesa (oq basso), ruvidità a ~60 Hz, un tratto caotico (subarmoniche e
    jitter forte) nel mezzo; sotto, la gola grande."""
    n = ns(d)
    f0 = curve(n, f0_pts, 'log')
    if crack_at is not None:
        f0 = f0 * (1 + 0.3 * gate_env(n, crack_at, crack_at + 0.09, 0.004, 0.02))
    ch = gate_env(n, chaos[0] * d, chaos[1] * d, 0.04, 0.06)
    v = vox(rng, d, f0=f0, vowels=vowels, scale=scale, amp_pts=amp_pts, oq=0.4, jitter=0.025 + 0.08 * ch,
            shimmer=0.12 + 0.2 * ch, sub=0.2 + 0.4 * ch, breath=0.5, breath_base=0.5, bw=1.5,
            rough=rough + 0.25 * ch, rough_rate=rough_rate, rough_fm=40.0 + 60.0 * ch, wander=35)
    g = _ghost(rng, d, f0_pts, vowels, amp_pts=amp_pts, ratio=0.44, oq=0.42, rough=0.4, rough_rate=31.0)
    return v + ghost * g


def _slam(rng, size=1.0):
    """Il palmo e i pugni sullo scafo, con l'acqua che schizza."""
    y = np.zeros(ns(0.6))
    place(y, wet_slap(rng, size=size, surface='wood', dur=0.5, wood_base=135.0, drops=1.0), 0.0)
    place(y, 0.6 * knuckle_knock(rng, force=0.004, base=170, dur=0.4, wet_amt=0.6), 0.003)
    place(y, 0.35 * splash(rng, size=0.18, dur=0.5), 0.01)
    return normalize(y)


def _rock_groan(rng, d=1.2, base=125.0):
    """Il fasciame che geme quando la barca si inclina."""
    return creak(rng, d, [(0, 18), (d * 0.4, 34), (d * 0.8, 27), (d, 15)], [(0, 0), (0.15, 0.8), (d * 0.6, 1), (d, 0)],
                 base=base, t60=0.14, bright=0.75, jitter=0.12, hiss=0.1)


def _tantrum_1(s, rng):
    """Uno schiaffo sullo scafo, «AAAH!», due pugni, «AAAH-AH!» con la voce che si spezza, il fasciame che
    geme mentre la barca dondola, un singhiozzo."""
    out = np.zeros(s.n)
    place(out, _slam(rng, 1.0), 0.0)
    place(out, _scream(rng, 0.9, [(0, 640), (0.1, 880), (0.5, 940), (0.78, 830), (0.9, 690)],
                       [(0, 'ae'), (0.1, 'a'), (0.9, 'a')], [(0, 0), (0.05, 1), (0.75, 0.9), (0.9, 0)]), 0.05)
    for t0, sz in [(1.0, 0.9), (1.21, 1.0)]:
        place(out, 0.9 * _slam(rng, sz), t0)
    place(out, _scream(rng, 0.92, [(0, 700), (0.12, 1000), (0.45, 960), (0.62, 1060), (0.92, 640)],
                       [(0, 'a'), (0.6, 'ae'), (0.92, 'a')], [(0, 0), (0.04, 1), (0.8, 0.85), (0.92, 0)],
                       crack_at=0.55, ghost=0.4), 1.3)
    place(out, 0.7 * _rock_groan(rng, 1.3), 1.05)
    for t0 in (1.1, 1.45, 2.1):
        place(out, 0.35 * lap(rng, 1.0, dur=0.9, hull=0.5), t0)
    place(out, 0.6 * _sob(rng, 0.55, [(0, 540), (0.15, 520), (0.55, 360)], [(0, 'u'), (0.55, '@')],
                          [(0, 0), (0.06, 1), (0.55, 0)], ghost=0.35), 2.28)
    y = wet_throat(out, rng, rate=10, depth=0.2, bubbles=0.15, flange=0.15, f_lo=300, f_hi=1100)
    return _finish(y, rng, room=0.12)


def _tantrum_2(s, rng):
    """Calci nell'acqua, un lungo strillo, il singhiozzo col singulto, un ultimo pugno sul legno."""
    out = np.zeros(s.n)
    for t0, sz in [(0.0, 0.3), (0.16, 0.25), (0.3, 0.35)]:
        place(out, 0.7 * splash(rng, size=sz, dur=0.6), t0)
    place(out, 0.5 * _slam(rng, 0.7), 0.02)
    place(out, _scream(rng, 1.25, [(0, 600), (0.12, 900), (0.6, 1010), (1.0, 900), (1.25, 600)],
                       [(0, 'ae'), (0.15, 'a'), (1.0, 'a'), (1.25, '@')], [(0, 0), (0.06, 1), (1.0, 0.85), (1.25, 0)],
                       chaos=(0.4, 0.75), rough=0.5, rough_rate=68.0, ghost=0.35), 0.12)
    place(out, 0.7 * _rock_groan(rng, 1.1, base=140.0), 0.9)
    place(out, 0.3 * _gasps(rng, [0.0, 0.1, 0.18]), 1.45)
    place(out, 0.75 * _sob(rng, 0.6, [(0, 560), (0.2, 520), (0.6, 380)], [(0, 'a'), (0.3, 'u'), (0.6, 'u')],
                           [(0, 0), (0.06, 1), (0.6, 0)], ghost=0.3), 1.7)
    place(out, 0.95 * _slam(rng, 1.0), 2.3)
    place(out, 0.3 * lap(rng, 1.0, dur=0.6, hull=0.5), 2.32)
    y = wet_throat(out, rng, rate=10, depth=0.2, bubbles=0.15, flange=0.15, f_lo=300, f_hi=1100)
    return _finish(y, rng, room=0.12)


register('molly_tantrum_1', _tantrum_1, 2.95, category='mon', gain=0.9, rms=-15.0, max_gr=5.0)
register('molly_tantrum_2', _tantrum_2, 2.9, category='mon', gain=0.9, rms=-15.0, max_gr=5.0)


# ───────────────────────── la barca che dondola (loop) ─────────────────────────

def _clink(rng, f=1850.0):
    """Il manico del secchio di lamiera che sbatte."""
    n = ns(0.5)
    exc = np.zeros(n)
    exc[:2] = [1.0, -0.4]
    fr = f * np.array([1.0, 1.52, 2.27, 2.9, 3.8])
    return normalize(modal(exc, fr * rng.uniform(0.98, 1.02, 5), [0.18, 0.12, 0.08, 0.06, 0.04], [1, 0.6, 0.45, 0.3, 0.2]))


def _rock(s, rng):
    """Quattro inclinazioni (2,4 s l'una), una per lato: il fasciame che geme verso il lato che scende,
    l'acqua che sbatte su quel fianco, quella di sentina che corre sotto il pagliolo, la roba di bordo che
    si sposta. Sotto, senza pause, il mare smosso contro lo scafo (il loop non ha buchi: il gioco ne
    regola il volume con la forza del dondolio)."""
    n, dur = s.n, s.dur
    t = tvec(n)
    out = np.zeros((2, n))
    period = dur / 4
    # mare smosso: letto continuo che segue il dondolio (più forte sul lato che scende)
    roll = np.sin(TWO_PI * 2 * t / dur)              # un ciclo completo ogni due inclinazioni
    for c, sgn in enumerate((-1.0, 1.0)):
        bed = spectral_noise(n, rng, lambda f: bw_bp(f, 90, 1600, 2), exponent=1.0)
        bed *= 0.5 + 0.5 * np.clip(sgn * roll, 0, 1) ** 1.5 + 0.25 * np.abs(rand_curve(n, 3.0, rng))
        out[c] += 0.03 * bed
    for k in range(4):
        side = -1.0 if k % 2 == 0 else 1.0
        t0 = k * period
        g = _rock_groan(rng, rng.uniform(1.3, 1.9), base=rng.uniform(105, 150))
        place(out, pan(g, 0.55 * side) * rng.uniform(0.75, 1.0), t0 + rng.uniform(0.0, 0.2), wrap=True)
        # un secondo gemito, più acuto e corto, dal lato opposto (la barca torna su)
        g2 = creak(rng, 0.6, [(0, 60), (0.3, 120), (0.6, 70)], [(0, 0), (0.1, 1), (0.6, 0)], base=rng.uniform(210, 260),
                   t60=0.08, bright=1.0, jitter=0.1)
        place(out, pan(g2, -0.4 * side) * 0.35, t0 + period * rng.uniform(0.55, 0.75), wrap=True)
        for _ in range(3):
            ll = lap(rng, rng.uniform(0.7, 1.0), dur=1.0, hull=0.6, clop_prob=0.9)
            place(out, pan(ll, 0.7 * side) * 0.5, t0 + 0.25 + rng.uniform(0.0, 1.4), wrap=True)
        m = ns(period * 1.1)
        wash = bandpass(rng.standard_normal(m), 180, 1400) * curve(m, [(0, 0), (0.35, 1), (period * 1.1, 0)])
        wash = wash * (0.7 + 0.3 * np.tanh(rand_curve(m, 12, rng)))
        sweep = np.linspace(-side, side, m) * 0.6
        L = wash * np.cos((sweep + 1) * np.pi / 4)
        R = wash * np.sin((sweep + 1) * np.pi / 4)
        place(out, 0.14 * np.stack([L, R]) / (np.max(np.abs(wash)) + 1e-9), t0 + 0.1, wrap=True)
        if rng.random() < 0.85:
            place(out, pan(_clink(rng, rng.uniform(1700, 2100)), 0.3) * 0.05, t0 + rng.uniform(0.3, 1.2), wrap=True)
        kn = knock(rng, force=0.003, base=rng.uniform(260, 330), t60=0.06, dur=0.3)
        place(out, pan(kn, -0.4 * side) * 0.12, t0 + rng.uniform(0.4, 1.6), wrap=True)
    return circular(lambda x: lowpass(highpass(x, 45, 2), 8000, 2), out)


register('molly_rock', _rock, 9.6, loop=True, channels=2, category='mon', gain=0.8, rms=-20.0)


# ───────────────────────── jumpscare ─────────────────────────

def _js_molly(s, rng):
    """Esce dall'acqua addosso al pescatore: l'acqua che esplode, i braccioli di plastica che stridono, uno
    strillo altissimo di bambina con sotto la gola enorme (a un intervallo stonato), ruvido e bagnato."""
    n = s.n
    d = s.dur
    f0_pts = [(0, 880), (0.06, 1250), (0.45, 1170), (0.8, 1320), (1.1, 1180), (d, 900)]
    vowels = [(0, 'i'), (0.08, 'ae'), (0.3, 'a'), (1.0, 'a'), (d, 'ae')]
    amp = [(0, 0.7), (0.03, 1), (1.15, 0.95), (d, 0.5)]
    v = np.zeros(n)
    for k, det in enumerate((-14.0, 0.0, 17.0)):
        pts = [(t, f * cents(det)) for t, f in f0_pts]
        v += (1.0 if k == 1 else 0.55) * vox(rng, d, pts, vowels, scale=1.45, amp_pts=amp, oq=0.38, jitter=0.07,
                                              shimmer=0.22, sub=0.45, breath=0.55, breath_base=0.5, bw=1.6, rough=0.8,
                                              rough_rate=84.0, rough_fm=90.0, wander=55)
    g = _ghost(rng, d, f0_pts, vowels, amp_pts=amp, ratio=0.42, oq=0.4, rough=0.55, rough_rate=41.0, sub=0.6)
    y = normalize(v) + 0.55 * normalize(g)
    y = wet_throat(y, rng, rate=20, depth=0.3, bubbles=0.25, flange=0.3, f_lo=300, f_hi=1200)
    place(y, 0.7 * splash(rng, size=0.75, dur=1.0), 0.0)
    place(y, 0.25 * rubber_squeal(rng, 0.5, [(0, 700), (0.2, 1100), (0.5, 800)], bright=1.6), 0.02)
    ir = near_room(rng, 0.45, stereo_out=True)
    out = stereo(y) * np.sqrt(0.5) + 0.22 * convolve(y, ir)
    out = lowpass(highpass(out, 60, 2), 11000, 2)
    return scream_master(out, drive=2.25)


register('js_molly', _js_molly, 1.35, channels=2, category='mon', gain=1.0, rms=-6.6, max_gr=6.0, release=0.03)


# ───────────────────────── si affaccia ─────────────────────────

def _peek(s, rng):
    """Si affaccia sul bordo: la testa che rompe il pelo dell'acqua e l'acqua che le cola di dosso, le dita
    lunghe che si posano bagnate sul capodibanda una dopo l'altra, i braccioli di plastica che stridono appena,
    un fiato piccolo e umido dalla bocca a becco."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.7 * splash(rng, size=0.22, dur=0.7), 0.0)
    m = ns(0.9)
    place(y, 0.2 * gush(m, rng, curve(m, [(0, 0.6), (0.15, 1.0), (0.9, 0)]), bubble_rate=120, f_lo=500, f_hi=3000), 0.05)
    for i, t0 in enumerate([0.28, 0.36, 0.43, 0.52]):
        k = wet_slap(rng, size=0.18, surface='wood', dur=0.25, wood_base=240.0, drops=0.3)
        place(y, (0.22 + 0.03 * i) * k, t0 + rng.uniform(-0.01, 0.01))
    place(y, 0.18 * rubber_squeal(rng, 0.3, [(0, 900), (0.15, 1300), (0.3, 1000)], bright=1.5), 0.4)
    d = 0.55
    br = tract_noise(rng, d, [(0, 'u'), (d, '@')], scale=CHILD, amp_pts=[(0, 0), (0.1, 1), (d, 0)], hiss=0.6)
    br = wet_throat(br, rng, rate=20, depth=0.5, bubbles=0.4, f_lo=300, f_hi=1100)
    place(y, 0.3 * br, 0.7)
    return _finish(y, rng, room=0.1)


register('molly_peek', _peek, 1.35, category='mon', gain=0.8, rms=-18.0, max_gr=6.0)
