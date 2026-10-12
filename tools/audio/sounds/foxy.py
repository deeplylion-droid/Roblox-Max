"""
L'animatore (il «Foxy» del gioco; il nome lo sceglie l'utente, intanto gli id sono foxy_*): l'animatore di
Splashland annegato dentro il costume di Mama Marina, la balena-mamma blu col pancione crema. Variante B «Fradicio»:
il costume gonfio d'acqua che cede, il peluche fradicio e la gommapiuma marcia, la testa crollata di lato, le sue
mani grigie dalle pinne sfondate, la faccia gonfia spinta fuori dalla bocca e un occhio di plastica da cartone (di
quelli con la pupilla libera dentro) che penzola. Faceva lo spettacolo della mascotte, che finiva sempre con un
abbraccio: nel pancione c'è ancora la scatoletta sonora che suonava la sigla quando i bambini lo stringevano.

Sta lontano, in uno dei due posti del binocolo (la torre degli scivoli a 460 m, il relitto a 170 m). Non parla: solo
fiato, gorgoglio e il costume. Mono (si spazializza nel gioco dal suo posto), tranne il jumpscare.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

MAN = 0.94        # scala delle formanti: un uomo adulto (la gola un po' gonfia d'acqua)


def _finish(y, rng, room=0.12, lp=10000.0):
    return roomify(lowpass(highpass(y, 35, 2), lp, 2), rng, room)


# ───────────────────────── il costume ─────────────────────────

def _eye(rng, amp=1.0, rattle=True):
    """L'occhio di plastica da cartone che sbatte contro la testa: la cupola di plastica vuota che risuona (un 'toc'
    secco e chiaro) e, subito dopo, la pupilla libera che ci sbatacchia dentro (tre o quattro tic sempre più piccoli).
    È il suo segno più acuto: in cuffia aiuta a dire da dove arriva."""
    n = ns(0.16)
    exc = np.zeros(n)
    k = max(2, ns(0.00035))
    exc[:k] = np.hanning(k + 2)[1:-1]
    sh = rng.uniform(0.93, 1.07)
    dome = modal(exc, np.array([1720.0, 2930.0, 4180.0, 5650.0]) * sh, [0.035, 0.025, 0.018, 0.012], [1.0, 0.7, 0.45, 0.25])
    y = normalize(dome) + 0.25 * normalize(highpass(exc + 0.3 * rng.standard_normal(n) * exp_env(n, 0.004), 2500))
    if rattle:
        t = rng.uniform(0.012, 0.02)
        a = 0.45
        for _ in range(int(rng.integers(3, 6))):
            m = ns(0.05)
            e = np.zeros(m)
            e[:2] = 1.0
            tic = modal(e, np.array([3900.0, 6100.0, 8300.0]) * rng.uniform(0.95, 1.05), [0.01, 0.008, 0.006], [1, 0.6, 0.3])
            place(y, a * normalize(tic), t)
            t += rng.uniform(0.012, 0.03)
            a *= rng.uniform(0.45, 0.7)
    return amp * normalize(y)


def _sodden(rng, dur, size=1.0, pour=1.0):
    """Il peluche fradicio e la gommapiuma marcia che si schiacciano: un risucchio fitto e appiccicoso (le celle della
    gommapiuma che si svuotano), l'acqua che ne esce strizzata a fiotti e cola, un tonfo sordo e molle sotto."""
    n = ns(dur)
    y = np.zeros(n)
    # la gommapiuma che si svuota: crepitio molle e fitto
    sq = squelch(rng, dur, 220 + 120 * (1 - size), 1500 + 600 * (1 - size), rate=30.0, density=1400.0)
    y += 0.7 * sq * curve(n, [(0, 0), (0.02, 1), (dur * 0.45, 0.7), (dur, 0)])
    # l'acqua strizzata fuori: fiotti con bolle
    gi = curve(n, [(0, 0), (0.03, 1.0), (dur * 0.5, 0.6), (dur, 0.0)])
    y += 0.55 * pour * normalize(gush(n, rng, gi, bubble_rate=160.0, f_lo=300.0, f_hi=2600.0)) * 0.8
    # il tonfo molle del corpo dentro il costume
    m = ns(min(dur, 0.35))
    thud = lowpass(rng.standard_normal(m), 180 + 80 * (1 - size), 2) * exp_env(m, 0.12 + 0.08 * size, attack=0.006)
    place(y, 0.8 * size * normalize(thud), 0.0)
    return y


def _stroke(rng, size=1.0):
    """Una bracciata (o un passo, dove tocca il fondo) del costume fradicio sull'acqua: la pinna sfondata che sbatte
    piatta sulla superficie (schiaffo spugnoso, non secco), l'acqua spinta via, il peluche che si strizza e cola."""
    dur = 0.55
    n = ns(dur)
    y = np.zeros(n)
    # lo schiaffo piatto e molle sull'acqua
    m = ns(0.12)
    sl = rng.standard_normal(m) * exp_env(m, rng.uniform(0.035, 0.06), attack=rng.uniform(0.003, 0.008))
    y[:m] += 0.75 * normalize(bandpass(sl, 160, 3800, 2) + 0.6 * lowpass(sl, 260, 2))
    place(y, 0.5 * splash(rng, size=0.32 + 0.25 * size, dur=0.5), 0.004)
    # il costume che si strizza e l'acqua che ne esce
    place(y, 0.45 * _sodden(rng, 0.38, size=size, pour=0.8), 0.02)
    # l'acqua spinta via dal corpo: un 'whoosh' scuro e turbolento
    gi = curve(n, [(0, 0), (0.06, 1), (0.3, 0.4), (dur, 0)])
    place(y, 0.35 * normalize(gush(n, rng, gi, bubble_rate=120.0, f_lo=180.0, f_hi=1200.0)), 0.0)
    return y


def _gasp(rng, dur=0.42, out=True, amp=1.0):
    """Un fiato pesante dalla faccia spinta fuori dalla bocca del costume: un uomo che corre coi polmoni pieni
    d'acqua. Niente parole: soffio di gola che gorgoglia, un'ombra di voce rotta dentro."""
    vowels = [(0, 'a'), (dur, '@')] if out else [(0, '@'), (dur, 'O')]
    br = tract_noise(rng, dur, vowels, scale=MAN, amp_pts=[(0, 0), (0.03, 1), (dur * 0.6, 0.6), (dur, 0)], bw=1.5, hiss=0.2)
    vc = vox(rng, dur, [(0, 125), (dur * 0.3, 140), (dur, 95)], vowels, scale=MAN,
             amp_pts=[(0, 0), (0.05, 0.7), (dur * 0.5, 0.4), (dur, 0)], oq=0.5, jitter=0.05, shimmer=0.3,
             breath=0.8, rough=0.5, rough_rate=35.0, voicing=curve(ns(dur), [(0, 0.2), (0.08, 0.6), (dur, 0.1)]))
    y = normalize(br) + 0.35 * vc
    y = wet_throat(y, rng, rate=26.0, depth=0.65, bubbles=0.6, flange=0.35)
    return amp * normalize(y)


def _distance(x, rng, near: float):
    """Il suono che arriva da lontano sull'acqua: near 0 = laggiù (solo i bassi e tanta coda), 1 = sotto la barca."""
    fc = 650.0 * (14.0 ** near)
    return lowpass(x, fc, 2) * (0.35 + 0.65 * near ** 0.8)


# ───────────────────────── lascia il posto e corre ─────────────────────────

def _leave(s, rng):
    """Lascia il posto: un tonfo pesante laggiù (si butta in acqua col costume gonfio), poi qualcosa che arriva di
    corsa verso la barca, mezzo nuotando e mezzo correndo dove tocca: bracciate spugnose sempre più fitte, vicine e
    chiare, l'acqua spinta via che ribolle, i fiati che gorgogliano, l'occhio di plastica che sbatte. Gli ultimi
    0,3 s sono lo slancio fuori dall'acqua: alla fine del file il gioco fa partire il jumpscare."""
    n, d = s.n, s.dur
    far = np.zeros(n)          # tutto ciò che è lontano passa per una coda lunga sull'acqua
    y = np.zeros(n)
    # il tonfo laggiù: il corpo gonfio d'acqua che si butta, la cavità che collassa, lo scroscio che ricade
    m = ns(1.6)
    boom = lowpass(rng.standard_normal(m), 110, 2) * exp_env(m, 0.5, attack=0.012)
    tonfo = 0.9 * splash(rng, size=1.0, dur=1.6) + 0.9 * normalize(boom)
    place(tonfo, 0.4 * splash(rng, size=0.6, dur=0.9), 0.32)    # il getto che ricade
    place(far, lowpass(tonfo, 900, 2), 0.0)
    # la corsa: bracciate che accelerano, ognuna più vicina
    t = 0.62
    k = 0
    while t < d - 0.32:
        u = (t - 0.62) / (d - 0.95)                   # 0 → 1 lungo la corsa
        near = float(np.clip(u, 0, 1)) ** 1.3
        st = _stroke(rng, size=0.7 + 0.3 * (k % 2))
        st = _distance(st, rng, near)
        place(y, st * (0.55 + 0.45 * near), t)
        place(far, st * (1.0 - near) * 0.8, t)
        # il corpo tira fuori l'acqua fra una bracciata e l'altra: fiati e gorgoglio, solo da vicino
        if near > 0.45 and k % 2 == 1:
            place(y, _distance(_gasp(rng, 0.3, out=True, amp=0.45 * near), rng, near), t + 0.06)
        if near > 0.55 and rng.random() < 0.8:
            place(y, _distance(_eye(rng, amp=0.28 * near), rng, near), t + rng.uniform(0.05, 0.12))
        t += 0.46 - 0.24 * u + rng.uniform(-0.02, 0.02)
        k += 1
    # la scia: l'acqua che ribolle davanti a lui, sempre più forte e più chiara
    gi = curve(n, [(0, 0), (0.6, 0.0), (1.2, 0.25), (d - 0.4, 1.0), (d, 0.6)])
    wake = gush(n, rng, gi, bubble_rate=200.0, f_lo=160.0, f_hi=1800.0)
    wake = tv_lowpass(wake, curve(n, [(0, 500), (1.2, 650), (d, 6000)], 'log'))
    y += 0.3 * normalize(highpass(wake, 110, 2)) * curve(n, [(0, 0), (1.0, 0.15), (d, 1.0)])
    # lo slancio: il corpo che si solleva dall'acqua e l'acqua che gli cade di dosso, il costume che si gonfia
    t1 = d - 0.36
    m = ns(0.36)
    lift = gush(m, rng, curve(m, [(0, 0.3), (0.2, 1), (0.36, 0.7)]), bubble_rate=260.0, f_lo=250.0, f_hi=3200.0)
    place(y, 0.55 * normalize(lift), t1)
    place(y, 0.6 * _gasp(rng, 0.34, out=False, amp=1.0), t1 + 0.02)    # un inspiro gorgogliante, a bocca piena
    place(y, _eye(rng, amp=0.4), t1 + 0.16)
    # la coda sull'acqua aperta per tutto ciò che è lontano
    ir = reverb_ir(1.8, rng, lo=0.8, hi=0.3, predelay=0.03, attack=0.02, sparse=0.6, lp=2500, stereo_out=False,
                   early=[(0.09, 0.35, 0.0), (0.21, 0.2, 0.0)])
    y = y + 0.7 * far + 0.9 * convolve(highpass(far, 120, 2), ir)[:n]
    return _finish(y, rng, room=0.1, lp=11000.0)


register('foxy_leave', _leave, 3.2, category='mon', gain=0.9, rms=-17.0, max_gr=6.0)


# ───────────────────────── si sporge (quando non lo guardi) ─────────────────────────

def _near(s, rng):
    """Si sporge verso di te mentre non lo guardi: laggiù il costume fradicio si piega in avanti e l'acqua ne esce
    tutta insieme (uno scroscio lungo che cade sul mare, l'unica cosa che da lassù arriva fin qui sull'acqua
    ferma), la gommapiuma che si strizza, due colpetti dell'occhio di plastica. Lontano e appena udibile."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    # il peluche che si piega e si strizza
    place(y, 0.7 * _sodden(rng, 0.9, size=0.8, pour=0.4), 0.0)
    # lo scroscio che cade dal costume sul mare
    gi = curve(ns(1.6), [(0, 0), (0.2, 1.0), (0.8, 0.7), (1.6, 0)])
    pour = gush(ns(1.6), rng, gi, bubble_rate=300.0, f_lo=300.0, f_hi=2400.0)
    place(y, 0.6 * normalize(pour), 0.15)
    for td in poisson_times(rng, 6.0, 0.9, d - 0.2):
        place(y, droplet(rng, amp=rng.uniform(0.04, 0.1), tonal=0.4), td)
    # l'occhio che penzola e batte due volte
    place(y, _eye(rng, amp=0.55), 0.55)
    place(y, _eye(rng, amp=0.4, rattle=False), 0.98)
    # lontano: pochi acuti (ma un filo, per la direzione) e la coda dell'acqua aperta
    y = lowpass(y, 2400, 2) + 0.15 * highpass(y, 2400, 2)
    ir = reverb_ir(1.5, rng, lo=1.2, hi=0.3, predelay=0.02, attack=0.02, sparse=0.6, lp=3000, stereo_out=False)
    y = y + 0.6 * convolve(y, ir)[:n]
    return highpass(y, 60, 2)


register('foxy_near', _near, 2.2, category='mon', gain=0.5, rms=-24.0, max_gr=4.0)


# ───────────────────────── jumpscare ─────────────────────────

def _songbox(rng, dur):
    """La scatoletta sonora nel pancione, che suonava la sigla dello spettacolo quando i bambini abbracciavano Mama
    Marina: schiacciata dall'abbraccio parte l'ultimo «ta-daaa» (Sol, poi l'accordo di Do), ma l'altoparlantino è
    pieno d'acqua: il cono gracchia e gorgoglia, la pila è quasi andata e la nota crolla storta."""
    n = ns(dur)
    t = tvec(n)
    y = np.zeros(n)
    # «ta» corto
    m = ns(0.13)
    f_ta = np.full(m, 392.0) * cents(-30 + 10 * rand_curve(m, 8.0, rng))
    ta = additive(f_ta, [1, 0.6, 0.45, 0.3, 0.22, 0.15, 0.1]) * curve(m, [(0, 0), (0.01, 1), (0.1, 0.8), (0.13, 0)])
    place(y, normalize(ta), 0.0)
    # «daaa»: l'accordo di Do che si storce e crolla mentre la pila muore
    t0 = 0.16
    m = n - ns(t0)
    sag = curve(m, [(0, 0), (0.25, -20), (0.6, -140), ((m / SR), -420)], 'cos')
    wob = 25 * np.sin(TWO_PI * 5.2 * tvec(m)) + 18 * rand_curve(m, 6.0, rng)
    chord = np.zeros(m)
    for f, a, det in ((523.25, 1.0, 0.0), (659.25, 0.7, -35.0), (783.99, 0.6, 22.0)):
        chord += a * additive(np.full(m, f) * cents(sag + wob + det), [1, 0.55, 0.4, 0.25, 0.18, 0.1])
    chord *= curve(m, [(0, 0), (0.012, 1), (0.5, 0.85), ((m / SR) * 0.85, 0.5), (m / SR, 0)])
    # la pila: il suono che salta a tratti
    chord *= 0.75 + 0.25 * np.tanh(4 * rand_curve(m, 14.0, rng))
    place(y, normalize(chord), t0)
    # l'altoparlantino bagnato: banda stretta, il cono che gracchia, l'acqua che gorgoglia sopra
    y = bandpass(y, 520, 3600, 2)
    y = softclip(normalize(y), 3.5, asym=0.2)
    y = wet(y, rng, rate=18.0, depth=0.45, bubbles=0.3, flange=0.4, f_lo=500, f_hi=1600)
    buzz = highpass(rng.standard_normal(n), 1500) * np.abs(y) * (0.5 + 0.5 * np.abs(rand_curve(n, 30.0, rng)))
    y = normalize(y) + 0.35 * normalize(buzz)
    return normalize(resonate(y, 1150, 2.5) * 0.4 + y)


def _js_foxy(s, rng):
    """Ti salta addosso e ti abbraccia: lo slancio fuori dall'acqua e il costume zuppo che sbatte sul capodibanda (la
    barca che sobbalza e geme), il peluche che si schiaccia contro di te strizzando acqua, l'urlo di un uomo annegato
    dentro la testa del costume (soffocato dalla gommapiuma, gorgogliante, che affoga in un rantolo), l'occhio di
    plastica che sbatte da un lato e, schiacciata dall'abbraccio, la scatoletta sonora nel pancione che suona storta
    l'ultimo «ta-daaa» dello spettacolo."""
    n, d = s.n, s.dur
    L = np.zeros((2, n))
    # 1) lo slancio e l'impatto sul bordo
    place(L, pan(0.8 * splash(rng, size=1.0, dur=1.4), 0.0), 0.0)
    place(L, pan(0.9 * wet_slap(rng, size=1.0, surface='wood', dur=0.5, wood_base=130.0, drops=1.5), -0.15), 0.025)
    place(L, pan(0.55 * knock(rng, force=0.004, base=110.0, t60=0.18, dur=0.6, cavity=(95.0, 0.25, 0.8)), 0.0), 0.03)
    place(L, pan(0.35 * creak(rng, 0.7, [(0, 30), (0.3, 60), (0.7, 25)], [(0, 0), (0.05, 1), (0.4, 0.6), (0.7, 0)],
                              base=150.0), 0.3), 0.1)
    # 2) il peluche che ti si schiaccia addosso: il tonfo molle e l'acqua strizzata, vicinissima, larga
    sod = _sodden(rng, 1.3, size=1.0, pour=1.2)
    place(L, np.stack([sod, np.roll(sod, ns(0.006))]) * 0.6, 0.06)
    place(L, np.stack([np.roll(sod, ns(0.004)), sod]) * 0.35, 0.75)      # l'abbraccio che stringe ancora
    # 3) l'urlo dentro la testa del costume
    sc = d - 0.12
    f0_pts = [(0, 150), (0.06, 260), (0.3, 330), (0.6, 300), (0.85, 345), (1.15, 280), (1.45, 170), (sc, 110)]
    voicing = curve(ns(sc), [(0, 0.6), (0.06, 1), (1.1, 1), (1.4, 0.45), (1.6, 0.15), (sc, 0.05)])
    amp = [(0, 0), (0.05, 1), (1.05, 0.95), (1.45, 0.6), (sc, 0.15)]
    voice = np.zeros(ns(sc))
    for k, det in enumerate((-18.0, 0.0, 16.0)):
        pts = [(tt, f * cents(det)) for tt, f in f0_pts]
        voice += (1.0 if k == 1 else 0.5) * vox(rng, sc, pts, [(0, 'a'), (0.1, 'ae'), (0.9, 'a'), (1.4, 'O'), (sc, 'u')],
                                               scale=MAN, amp_pts=amp, oq=0.42, jitter=0.05, shimmer=0.25, sub=0.35,
                                               breath=0.6, bw=1.4, rough=0.7, rough_rate=48.0, rough_fm=60.0,
                                               wander=40.0, voicing=voicing)
    # i polmoni pieni d'acqua: gargarismo forte, che alla fine affoga la voce
    voice = wet_throat(voice, rng, rate=30.0, depth=0.7, bubbles=0.7, flange=0.35)
    gg = throat_bubbles(rng, sc, rate=55.0, f_lo=150.0, f_hi=600.0, env_pts=[(0, 0.2), (1.0, 0.4), (1.5, 1.0), (sc, 0.6)])
    voice = normalize(voice) + 0.35 * normalize(gg)
    # dentro la testa: la gommapiuma si mangia gli acuti, la cavità rimbomba; un filo esce dalla bocca del costume
    muff = lowpass(voice, 1300, 2)
    muff = muff + 0.5 * resonate(muff, 340, 3.0) + 0.3 * resonate(muff, 720, 4.0)
    outv = highpass(voice, 500, 2)
    sc_y = 0.85 * normalize(muff) + 0.32 * normalize(outv)
    place(L, pan(sc_y, -0.08), 0.07)
    # 4) l'occhio di plastica che sbatte, dal lato dove la testa è crollata
    te = 0.05
    a = 0.75
    while te < 1.6:
        place(L, pan(_eye(rng, amp=a), -0.55), te)
        te += rng.uniform(0.07, 0.11) + 0.12 * te
        a *= 0.9
    # 5) la scatoletta sonora nel pancione, schiacciata dall'abbraccio
    sb = _songbox(rng, d - 0.62)
    place(L, pan(0.42 * sb, 0.1), 0.6)
    ir = near_room(rng, 0.4, stereo_out=True)
    mono_mix = L.mean(axis=0)
    out = L + 0.18 * convolve(mono_mix, ir)[..., :n]
    out = lowpass(highpass(out, 70, 2), 12500, 2)
    return scream_master(out, drive=2.4)


register('js_foxy', _js_foxy, 2.0, channels=2, category='mon', gain=1.0, rms=-6.4, max_gr=6.5, release=0.03)
