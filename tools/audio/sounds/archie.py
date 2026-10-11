"""
Archie (notte 3, spegne la luce): il bambino che alle feste di compleanno del parco spegneva lui le candeline degli
altri, ora il serpente di mare: un collo lunghissimo e sottile, giallo a bande nere, la testa da serpente coi denti
fuori dalle labbra, e la trombetta da festa (la lingua di suocera di carta a strisce, con la piuma in punta) fusa nel
bocchino. Sale dal mare accanto alla prua; prende fiato nella trombetta al contrario (l'ancia che strilla strozzata,
la carta che si arrotola stretta, la gola che si gonfia come un pallone); se la lampara è accesa soffia a tutto fiato
e il vetro esplode; al buio la trombetta si sgonfia in un lamento, e dopo un po' si rituffa. Non parla: la sua voce è
la trombetta. Mono (si spazializza nel gioco), tranne il jumpscare.

Il gioco: archie_inhale dura quanto il risucchio (4,5 s, poi soffia), archie_relight quanto il risucchio più corto
quando riaccendi (2,2 s); sfx.ts li ferma con una dissolvenza quando smette (al buio o quando soffia), quindi il
culmine sta alla fine e dopo c'è solo un attimo in più. glass_break suona dalla lampara 0,12 s dopo archie_blow.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

INHALE = 4.5       # s: il risucchio (config.ts, NIGHTS[3].archie.inhale)
RELIGHT = 2.2      # s: il risucchio quando riaccendi (archie.relight)


def _finish(y, rng, room=0.12, lp=12000.0):
    return roomify(lowpass(highpass(y, 40, 2), lp, 2), rng, room)


# ═════════════════════════ la trombetta da festa ═════════════════════════

def _reed(rng, dur, f_pts, amp_pts, sharp=3.0, stall=0.0, breath=0.3, wobble=18.0, tube=1.0):
    """L'ancia della trombetta da festa: una linguetta di plastica che sbatte nel bocchino (impulsi d'aria stretti,
    ricchissimi di armoniche: il ronzio nasale da kazoo), il tubo di carta che risuona (formanti larghe), l'aria che
    passa. sharp: quanto sono stretti gli impulsi (più alto, più ronzio); stall: quanto si inceppa l'ancia (a
    strappi, come con poco fiato o al contrario); wobble: l'intonazione che non sta mai ferma (centesimi)."""
    n = ns(dur)
    f = curve(n, f_pts, 'log') * cents(wobble * rand_curve(n, 6.0, rng))
    ph = phase_of(f)
    opening = np.maximum(0.0, np.sin(TWO_PI * ph)) ** sharp
    flow = lowpass(opening, 9000, 2)
    buzz = np.diff(flow, prepend=0.0)
    buzz = normalize(np.tanh(2.2 * normalize(buzz)))
    if stall:
        st = np.clip(0.5 + 0.9 * rand_curve(n, 16.0, rng), 0.0, 1.0)
        buzz = buzz * (1.0 - stall + stall * st)
    # il tubo di carta arrotolato: risonanze larghe e nasali
    horn = (0.55 * resonate(buzz, 480 * tube, 1.6) + resonate(buzz, 1150 * tube, 2.6) + 0.8 * resonate(buzz, 2350 * tube, 3.2)
            + 0.45 * resonate(buzz, 3700 * tube, 3.5) + 0.25 * buzz)
    air = tv_bandpass(rng.standard_normal(n), f * 2.0, f * 0.9) + 0.4 * highpass(rng.standard_normal(n), 2500)
    env = curve(n, amp_pts)
    return (normalize(horn) + breath * normalize(air)) * env


def _paper(rng, dur, env_pts, density=500.0, a=1.0, wet_=0.3):
    """La carta della trombetta che si arrotola o si srotola: scatti fitti della carta a strisce, un fruscio, e
    (bagnata dal mare) un po' molle."""
    y = crinkle(rng, dur, env_pts, density=density, f_lo=1100.0, f_hi=7500.0, res=3100.0, swish=0.3)
    if wet_:
        y = (1 - wet_) * y + wet_ * lowpass(y, 3500, 2)
    return a * normalize(y)


def _feather(rng, dur, env_pts, rate=45.0):
    """La piuma in punta che frulla nell'aria del soffio: fruscio acuto a colpetti veloci."""
    n = ns(dur)
    nz = bandpass(rng.standard_normal(n), 2500, 9000, 2)
    m = rough_mod(n, rng, rate, 0.85, wobble=0.3)
    return normalize(nz * m) * curve(n, env_pts)


def _hiss(rng, dur, amp_pts, inhale=False):
    """Il fiato del serpente fra i denti: un soffio stretto ('sss') con la bocca che sa di 'i'."""
    y = tract_noise(rng, dur, [(0, 'i'), (dur, 'e')], scale=0.9, amp_pts=amp_pts, hiss=0.9 if not inhale else 0.6)
    return normalize(highpass(y, 600, 2)) * curve(ns(dur), amp_pts)


def _balloon(rng, dur, f_pts, env_pts):
    """La gola che si gonfia come un pallone: la pelle tesa che cigola (gomma bagnata) e la sacca d'aria che rimbomba
    sempre più grave mentre cresce."""
    n = ns(dur)
    sq = rubber_squeal(rng, dur, rate_pts=[(0, 140), (dur * 0.5, 210), (dur, 170)], env_pts=env_pts, bright=0.6)
    fc = curve(n, f_pts, 'log')
    cav = tv_bandpass(rng.standard_normal(n), fc, fc * 0.25) * curve(n, env_pts)
    return 0.35 * normalize(sq) + normalize(cav)


# ───────────────────────── sale dall'acqua ─────────────────────────

def _rise(s, rng):
    """Il mare che si apre accanto alla prua e il collo che sale dritto: l'acqua che si gonfia e si rompe, poi che
    scorre giù per tutto il collo lunghissimo (un rivolo lungo che si assottiglia) e gocciola dall'alto sul mare; la
    pelle che scivola mentre si piega in cima, la carta fradicia della trombetta, un soffio fra i denti."""
    n = s.n
    d = s.dur
    y = np.zeros(n)
    place(y, 0.65 * splash(rng, size=0.42, dur=1.0), 0.0)
    place(y, bubble(170, xi=0.2, amp=0.45, decay_mult=0.6), 0.02)
    m = ns(2.3)
    place(y, 0.42 * gush(m, rng, curve(m, [(0, 0.3), (0.25, 1.0), (1.0, 0.55), (2.3, 0)]), bubble_rate=150, f_lo=450,
                         f_hi=3800), 0.1)
    # le gocce cadono da più in alto, sempre più rade: plink sul mare
    for t in poisson_times(rng, lambda tt: 26 * np.exp(-np.maximum(tt - 0.6, 0) / 1.1) + 3, 0.5, d - 0.05):
        place(y, droplet(rng, amp=rng.uniform(0.03, 0.12), tonal=0.55), t)
    place(y, 0.3 * squelch(rng, 0.18, 300, 1800, rate=30.0, density=900.0), 0.55)
    place(y, 0.25 * squelch(rng, 0.22, 250, 1500, rate=25.0, density=800.0), 1.15)
    place(y, 0.3 * _paper(rng, 0.6, [(0, 0), (0.15, 1), (0.6, 0)], density=220, wet_=0.6), 1.3)
    place(y, 0.3 * _hiss(rng, 0.6, [(0, 0), (0.25, 1), (0.6, 0)]), d - 0.68)
    return _finish(y, rng)


register('archie_rise', _rise, 2.8, category='mon', gain=0.85, rms=-17.0, max_gr=6.0)


# ───────────────────────── prende fiato nella trombetta ─────────────────────────

def _inhale(s, rng):
    """Il risucchio, lungo quanto dura nel gioco e sempre più forte fino al culmine: l'aria tirata al contrario
    nella trombetta (un soffio che sale), l'ancia che strilla strozzata e s'inceppa, la carta che si arrotola sempre
    più stretta scricchiolando, la gola che si gonfia come un pallone (la pelle che cigola, la sacca che rimbomba
    sempre più grave), la saliva fra i denti."""
    p = s.params
    n = s.n
    d = s.dur
    T = p['T']
    k = p['k']
    y = np.zeros(n)
    rise = [(0, 0.0), (min(0.35, T * 0.12), 0.35), (T * 0.6, 0.62), (T, 1.0), (d, 1.0)]
    # l'aria al contrario: il soffio che sale di tono (la bocca stretta sul bocchino)
    m = n
    fc = curve(m, [(0, 380 * k), (T, 1900 * k), (d, 2000 * k)], 'log')
    air = tv_bandpass(rng.standard_normal(m), fc, fc * 0.5) + 0.3 * highpass(rng.standard_normal(m), 3000)
    y += 0.55 * normalize(air) * curve(m, rise)
    # l'ancia che strilla al contrario: acuta, strozzata, a strappi
    reed = _reed(rng, d, [(0, 520 * k), (T, 980 * k), (d, 1010 * k)],
                 [(0, 0.0), (0.4, 0.15), (T * 0.5, 0.35), (T, 1.0), (d, 0.95)], sharp=4.0, stall=0.75, breath=0.5,
                 wobble=45.0, tube=1.15)
    y += 0.6 * reed
    # la carta che si arrotola stretta
    y += 0.35 * _paper(rng, d, [(0, 0.1), (T * 0.5, 0.5), (T, 1.0), (d, 0.8)], density=380 * k, wet_=0.25)
    # la gola che si gonfia
    y += 0.22 * highpass(_balloon(rng, d, [(0, 320), (T, 150), (d, 145)], [(0, 0), (T * 0.3, 0.4), (T, 1.0), (d, 0.9)]),
                         90, 2)
    y += 0.12 * saliva(rng, d, rate=70, f_lo=1500, f_hi=6000, env_pts=[(0, 0.2), (T, 1.0), (d, 0.8)])
    return _finish(y, rng, room=0.1)


register('archie_inhale', _inhale, INHALE + 0.35, category='mon', gain=0.9, rms=-17.5, max_gr=6.0,
         params={'T': INHALE, 'k': 1.0})
register('archie_relight', _inhale, RELIGHT + 0.3, category='mon', gain=0.95, rms=-16.5, max_gr=6.0,
         params={'T': RELIGHT, 'k': 1.22})


# ───────────────────────── al buio: la trombetta che si sgonfia ─────────────────────────

def _wait(s, rng):
    """La lampara si è spenta prima che soffiasse: la trombetta si sgonfia in un lamento che scende (l'ancia che
    perde fiato e s'inceppa), la carta che si riavvolge, la gola che si svuota in un sospiro, uno schiocco umido
    delle labbra sul bocchino. Poi aspetta, in silenzio."""
    n = s.n
    d = s.dur
    y = np.zeros(n)
    reed = _reed(rng, 1.25, [(0, 440), (0.35, 360), (1.0, 175), (1.25, 140)],
                 [(0, 0), (0.03, 1.0), (0.5, 0.75), (1.0, 0.3), (1.25, 0)], sharp=3.0, stall=0.55, breath=0.45,
                 wobble=30.0, tube=0.95)
    place(y, 0.6 * reed, 0.0)
    place(y, 0.35 * _paper(rng, 0.9, [(0, 0.2), (0.2, 1.0), (0.9, 0)], density=300, wet_=0.3), 0.15)
    ex = tract_noise(rng, 1.2, [(0, 'o'), (1.2, 'u')], scale=0.8, amp_pts=[(0, 0), (0.15, 1), (0.8, 0.5), (1.2, 0)],
                     hiss=0.3)
    place(y, 0.35 * normalize(lowpass(ex, 3000, 2)), 0.1)
    place(y, 0.2 * _balloon(rng, 1.0, [(0, 150), (1.0, 300)], [(0, 0.8), (0.6, 0.4), (1.0, 0)]), 0.1)
    place(y, 0.18 * squish(rng, 0.08, 600, 2600, density=1300, sticky=0.6), d - 0.32)
    return _finish(y, rng)


register('archie_wait', _wait, 1.7, category='mon', gain=0.85, rms=-18.0, max_gr=6.0)


# ───────────────────────── soffia ─────────────────────────

def _blow(s, rng):
    """Il soffio a tutto fiato sulla lampara: la trombetta che si srotola di scatto (la carta che sbatte), l'ancia
    che strepita forte e nasale, la piuma che frulla in punta, l'aria che si rovescia sul vetro. Il vetro che
    esplode è glass_break, dalla lampara."""
    n = s.n
    y = np.zeros(n)
    reed = _reed(rng, 1.05, [(0, 290), (0.12, 335), (0.8, 345), (1.05, 300)],
                 [(0, 0), (0.025, 1.0), (0.8, 0.9), (1.05, 0)], sharp=3.2, stall=0.12, breath=0.35, wobble=14.0)
    y_r = softclip(normalize(reed) * 1.4, 1.6)
    place(y, 0.75 * y_r, 0.0)
    # una seconda voce appena scordata: il ronzio si fa più grasso
    reed2 = _reed(rng, 1.0, [(0, 300), (0.12, 342), (1.0, 350)], [(0, 0), (0.04, 0.8), (0.75, 0.7), (1.0, 0)],
                  sharp=2.6, stall=0.2, breath=0.2, wobble=20.0, tube=1.05)
    place(y, 0.3 * reed2, 0.01)
    place(y, 0.45 * _paper(rng, 0.3, [(0, 1.0), (0.08, 0.8), (0.3, 0)], density=1600, wet_=0.2), 0.0)
    place(y, 0.25 * _feather(rng, 0.85, [(0, 0), (0.1, 1), (0.7, 0.7), (0.85, 0)], rate=48.0), 0.05)
    gust = bandpass(rng.standard_normal(ns(0.9)), 300, 5000) * curve(ns(0.9), [(0, 0), (0.05, 1), (0.7, 0.6), (0.9, 0)])
    place(y, 0.22 * normalize(gust), 0.0)
    return _finish(y, rng, room=0.1)


register('archie_blow', _blow, 1.3, category='mon', gain=1.0, rms=-15.0, max_gr=6.0)


# ───────────────────────── il vetro della lampara che esplode ─────────────────────────

def _shard(rng, a=1.0, hi=1.0):
    """Una scheggia di vetro: un tic duro e un tintinnio acuto e corto (modi inarmonici)."""
    m = ns(0.16)
    exc = np.zeros(m)
    k = max(2, ns(rng.uniform(0.0001, 0.0004)))
    exc[:k] = rng.standard_normal(k)
    f = float(loguniform(rng, 2600, 8000)) * hi
    T = rng.uniform(0.015, 0.09)
    ring = modal(exc, [f, f * rng.uniform(1.5, 1.75), f * rng.uniform(2.3, 2.7), f * rng.uniform(3.1, 3.6)],
                 [T, T * 0.7, T * 0.5, T * 0.35], [1.0, 0.6, 0.4, 0.25])
    return a * normalize(normalize(ring) + 0.5 * normalize(exc))


def _glass(s, rng):
    """Il vetro della lampara che esplode sotto il soffio: lo schianto (il vetro caldo che cede tutto insieme), la
    lampadina che scoppia col suo tonfo e l'arco che sfrigola un attimo mentre il reattore si spegne con un colpo
    sordo; poi le schegge che piovono sul pagliolo e sul banco, e qualcuna in mare."""
    n = s.n
    d = s.dur
    y = np.zeros(n)
    # lo schianto: crepitio duro a banda larga
    nc = ns(0.04)
    crack = bandpass(rng.standard_normal(nc), 1500, 14000, 2) * exp_env(nc, 0.03, attack=0.0003)
    place(y, 0.9 * normalize(crack), 0.0)
    for _ in range(46):
        place(y, _shard(rng, rng.uniform(0.3, 1.0)), abs(rng.normal(0.0, 0.025)))
    # la lampadina che scoppia: un tonfo d'aria
    m = ns(0.2)
    pop = osc(curve(m, [(0, 160), (0.2, 70)], 'log')) * exp_env(m, 0.06, attack=0.001)
    pop += lowpass(rng.standard_normal(m), 400, 2) * exp_env(m, 0.04, attack=0.0005)
    place(y, 0.55 * normalize(pop), 0.004)
    # l'arco che sfrigola e il reattore che si spegne
    m = ns(0.3)
    t_ = tvec(m)
    fz = highpass(rng.standard_normal(m), 2500, 2) * (0.5 + 0.5 * np.sign(np.sin(TWO_PI * 100.0 * t_)))
    fz *= np.clip(0.4 + 0.8 * rand_curve(m, 40.0, rng), 0, 1) * curve(m, [(0, 1), (0.25, 0.2), (0.3, 0)])
    place(y, 0.2 * normalize(fz), 0.01)
    hum = (np.sin(TWO_PI * 100.0 * t_) + 0.4 * np.sin(TWO_PI * 200.0 * t_)) * curve(m, [(0, 1), (0.2, 0.3), (0.3, 0)])
    place(y, 0.15 * hum, 0.0)
    place(y, 0.25 * knock(rng, 0.004, base=140, t60=0.05, dur=0.2), 0.27)
    # la pioggia di schegge: sul legno (tintinnio e tic del pagliolo) e in mare (plink)
    for _ in range(70):
        t = 0.06 + rng.gamma(1.6, 0.22)
        if t > d - 0.08:
            continue
        a = rng.uniform(0.08, 0.4) * np.exp(-t / 0.7)
        if rng.random() < 0.8:
            place(y, _shard(rng, a, hi=rng.uniform(0.8, 1.2)), t)
            if rng.random() < 0.4:
                place(y, 0.3 * a * knock(rng, 0.0003, base=rng.uniform(900, 1400), t60=0.02, count=5, bright=1.6,
                                         dur=0.05), t)
        else:
            place(y, droplet(rng, amp=a * 0.8, tonal=0.8), t)
    return _finish(y, rng, room=0.1, lp=15000.0)


register('glass_break', _glass, 1.7, category='sfx', gain=0.95, rms=-16.0, max_gr=8.0, release=0.02)


# ───────────────────────── si rituffa ─────────────────────────

def _dive(s, rng):
    """Si rituffa: la testa che si piega giù (la pelle che scivola, un soffio), poi il collo lunghissimo che rientra
    in mare tutto di seguito ('shhhllup' lungo, l'acqua che si apre attorno e gorgoglia), la testa che va sotto
    con un tonfo e le bolle che risalgono; le onde che arrivano allo scafo."""
    n = s.n
    d = s.dur
    y = np.zeros(n)
    place(y, 0.3 * _hiss(rng, 0.45, [(0, 0), (0.15, 1), (0.45, 0)]), 0.0)
    place(y, 0.25 * squelch(rng, 0.2, 280, 1600, rate=28.0, density=900.0), 0.12)
    m = ns(1.5)
    place(y, 0.55 * gush(m, rng, curve(m, [(0, 0.0), (0.2, 0.8), (0.9, 1.0), (1.5, 0)]), bubble_rate=180, f_lo=160,
                         f_hi=1400), 0.3)
    fc = curve(m, [(0, 1600), (1.5, 380)], 'log')
    sw = tv_bandpass(rng.standard_normal(m), fc, fc * 0.4) * curve(m, [(0, 0), (0.25, 1), (1.2, 0.7), (1.5, 0)])
    place(y, 0.3 * normalize(sw), 0.3)
    place(y, bubble(240, xi=0.3, amp=0.5, decay_mult=0.7), 1.72)
    place(y, 0.4 * splash(rng, size=0.22, dur=0.5), 1.7)
    bubble_burst(y, rng, 1.75, 18, 0.15, 200, 1200, 0.18, xi=(0.1, 0.5))
    place(y, 0.3 * lap(rng, strength=0.5, dur=0.6, hull=0.4), d - 0.62)
    return _finish(y, rng)


register('archie_dive', _dive, 2.4, category='mon', gain=0.85, rms=-17.0, max_gr=6.0)


# ───────────────────────── jumpscare ─────────────────────────

def _js_archie(s, rng):
    """Nel buio, col vetro esploso, ti arriva in faccia: la trombetta che si riavvolge di scatto e frusta l'aria, e il
    grido dentro il bocchino: lo strillo di un bambino che passa per l'ancia e ne esce ronzante e nasale come da un
    kazoo enorme, con sotto il soffio del serpente fra i denti; le zanne che scattano a vuoto davanti alla faccia."""
    n = s.n
    d = s.dur
    f0_pts = [(0, 560), (0.06, 860), (0.4, 800), (0.8, 900), (1.15, 760), (d, 520)]
    amp = [(0, 0.6), (0.04, 1), (1.12, 0.95), (d, 0.4)]
    kid = np.zeros(n)
    for k, det in enumerate((-12.0, 0.0, 13.0)):
        pts = [(t, f * cents(det)) for t, f in f0_pts]
        kid += (1.0 if k == 1 else 0.6) * vox(rng, d, pts, [(0, 'a'), (0.12, 'ae'), (0.9, 'a'), (d, 'O')], scale=1.33,
                                             amp_pts=amp, oq=0.42, jitter=0.05, shimmer=0.2, sub=0.3, breath=0.5,
                                             bw=1.5, rough=0.65, rough_rate=52.0, rough_fm=60.0, wander=40.0)
    # l'ancia che ronza alla stessa altezza dello strillo: il grido passa per la trombetta
    reed = _reed(rng, d, f0_pts, amp, sharp=3.5, stall=0.25, breath=0.3, wobble=55.0)
    reed2 = _reed(rng, d, [(t, f * 0.5 * cents(8)) for t, f in f0_pts], amp, sharp=2.8, stall=0.3, breath=0.2,
                  wobble=40.0, tube=0.9)
    y = 0.55 * normalize(kid) + 0.6 * normalize(reed) + 0.3 * normalize(reed2)
    y += 0.3 * _hiss(rng, d, [(0, 0.5), (0.1, 1), (1.2, 0.8), (d, 0.3)])
    place(y, 0.4 * _paper(rng, 0.3, [(0, 1.0), (0.3, 0)], density=1800, wet_=0.2), 0.0)
    place(y, 0.25 * _feather(rng, 0.6, [(0, 0), (0.05, 1), (0.6, 0)], rate=55.0), 0.0)
    for t0, a in [(0.42, 0.6), (0.86, 0.7), (1.18, 0.8)]:
        place(y, a * 0.6 * teeth_clack(rng, count=14, spread=0.006, glass=0.0, dur=0.25), t0)
    sw = bandpass(rng.standard_normal(ns(0.3)), 400, 3500) * curve(ns(0.3), [(0, 0), (0.1, 1), (0.3, 0)])
    place(y, 0.25 * normalize(sw), 0.0)
    ir = near_room(rng, 0.45, stereo_out=True)
    out = stereo(y) * np.sqrt(0.5) + 0.22 * convolve(y, ir)
    out = lowpass(highpass(out, 60, 2), 12500, 2)
    return scream_master(out, drive=2.0)


register('js_archie', _js_archie, 1.4, channels=2, category='mon', gain=1.0, rms=-6.6, max_gr=6.5, release=0.03)
