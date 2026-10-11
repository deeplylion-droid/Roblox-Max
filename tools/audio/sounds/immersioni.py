"""
Le immersioni all'alba (docs/IMMERSIONI.md): si scende con le bombole nelle grotte naturali sotto lo scoglio
dell'edicola, dove la Madre ha rifatto le camerette dei bambini-mostri. Niente pericoli: i mostri dormono. Solo
atmosfera, e il respiro del pescatore nell'erogatore.

  - l'ambiente della grotta (loop stereo): il silenzio pesante dell'acqua, il mare lontano sopra, la grotta che
    rimbomba piano con la risacca, sassolini che rotolano, gamberetti che schioccano, la roccia che geme;
  - l'erogatore (loop stereo, il gioco lo accelera col playbackRate): dentro il sibilo della valvola a domanda,
    fuori il borbottio della valvola di scarico e la colonna di bolle che sale; la variante affannata ad aria bassa;
  - le dissolvenze (stereo): la discesa, la nuotata, le bolle, l'avviso del manometro, l'aria che finisce, la
    risalita;
  - le sette tane (mono, si spazializzano): il respiro nel sonno di ogni mostro (loop) e il mostro che si muove
    nel sonno; l'offerta del pesce; il respiro della Madre dal fondo della grotta grande.

Sott'acqua l'orecchio umano sente ovattato (arriva per le ossa del cranio): gli acuti calano ma non spariscono, e i
versi tengono un filo di contenuto acuto (bollicine, schiocchi) perché in cuffia si capisca da dove arrivano. Le
bolle sono profonde: poca salita di tono (xi ≤ 0,06: le bolle grosse vivono a lungo e salirebbero
anche di un'ottava), niente «bloop» da cartone. Nessun mostro parla.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

GIANT = 0.56      # Gulpy (come in gulpy.py)
CHILD = 1.4       # Molly
BABY = 1.55       # Lampy
BOY = 1.32        # la voce di bambino sotto i versi
MASTIFF = 0.62    # Fangy


# ═════════════════════════ mattoni sott'acqua ═════════════════════════

def _cave_ir(rng, rt60=2.8, stereo_out=True):
    """La grotta grande: roccia dura e acqua, una coda lunga e scura, poche prime riflessioni dalle pareti."""
    return reverb_ir(rt60, rng, lo=1.4, hi=0.25, attack=0.03, sparse=0.2, lp=2600, stereo_out=stereo_out,
                     early=[(0.019, 0.4, -0.5), (0.037, 0.3, 0.6), (0.066, 0.22, -0.2), (0.11, 0.14, 0.3)])


def _den_ir(rng, rt60=0.9):
    """Una tana: una grotta laterale piccola, piena di roba (il letto, i giocattoli) che spezza le eco."""
    return reverb_ir(rt60, rng, lo=1.3, hi=0.3, attack=0.008, lp=3800, stereo_out=False,
                     early=[(0.008, 0.4, 0.0), (0.015, 0.3, 0.0), (0.026, 0.2, 0.0)])


def _uw(x, lp=3200.0, hp=35.0):
    """Ovattato come lo sente l'orecchio sott'acqua (si usa sugli eventi singoli)."""
    return lowpass(highpass(x, hp, 2), lp, 2)


def _den_loop(y, rng, wet=0.3, lp=4200.0, rt60=0.9):
    """Chiude un loop di una tana: ovattato e con la grotta attorno, tutto in regime circolare."""
    y = circular(lambda x: lowpass(highpass(x, 38, 2), lp, 2), y)
    return y + wet * convolve(y, _den_ir(rng, rt60), circular=True)


def _den_shot(y, rng, wet=0.3, lp=4200.0, rt60=0.9):
    y = lowpass(highpass(y, 38, 2), lp, 2)
    return y + wet * convolve(y, _den_ir(rng, rt60))


def _deep_bubbles(buf, rng, t0, count, spread, f_lo, f_hi, amp, wrap=False, xi=(0.0, 0.05), decay=(0.45, 0.8),
                  pan_range=(-0.3, 0.3)):
    """Bolle d'aria che escono da una bocca o da una valvola sott'acqua: istanti esponenziali dopo t0, frequenze
    log-uniformi, salita di tono minima (sono profonde) e un po' più lunghe di quelle di superficie."""
    for _ in range(int(count)):
        t = t0 + rng.exponential(spread)
        f = float(loguniform(rng, f_lo, f_hi))
        a = amp * (f_lo / f) ** 0.35 * rng.lognormal(0.0, 0.35)
        b = bubble(f, rng.uniform(*xi), a, decay_mult=rng.uniform(*decay), max_dur=0.4)
        if buf.ndim == 2:
            b = pan(b, rng.uniform(*pan_range))
        place(buf, b, t, wrap=wrap)


def _stone_click(rng, a=1.0, size=1.0):
    """Un sassolino che urta la roccia: un tic secco con due o tre modi duri, corto (l'acqua lo smorza)."""
    m = ns(0.04)
    exc = np.zeros(m)
    k = max(2, ns(rng.uniform(0.0002, 0.0005) * size))
    exc[:k] = np.sin(np.pi * (np.arange(k) + 0.5) / k)
    f0 = float(loguniform(rng, 1300, 3600)) / size ** 0.5
    y = modal(exc, [f0, f0 * 1.71, f0 * 2.63], [0.012, 0.008, 0.005], [1.0, 0.6, 0.35])
    return a * normalize(y)


def _pebbles(rng, count=None, a=1.0):
    """Sassolini che rotolano giù per la roccia: urti sempre più fitti e più deboli, poi uno o due rimbalzi."""
    count = count or int(rng.integers(5, 13))
    y = np.zeros(ns(2.2))
    t, gap, amp = 0.0, rng.uniform(0.12, 0.22), 1.0
    for _ in range(count):
        place(y, _stone_click(rng, amp * rng.uniform(0.6, 1.0), size=rng.uniform(0.7, 1.4)), t)
        if rng.random() < 0.3:
            place(y, _stone_click(rng, amp * 0.4), t + rng.uniform(0.01, 0.03))
        t += gap * rng.uniform(0.7, 1.2)
        gap *= rng.uniform(0.78, 0.92)
        amp *= rng.uniform(0.8, 0.95)
        if t > 2.0:
            break
    return a * y


def _shrimp(n, rng, rate=22.0, wrap_loop=True):
    """Lo schiocco dei gamberetti pistola sulla roccia: impulsi secchi, rari e sparsi, a banda larga ma corti
    (un crepitio, non un fruscio), che si addensano e si diradano a chiazze."""
    y = np.zeros(n)
    dur = n / SR
    dens = np.clip(0.4 + 0.8 * rand_curve(n, 0.15, rng), 0.05, 1.5)
    t_ = tvec(n)
    for tc in poisson_times(rng, lambda tt: rate * np.interp(tt, t_, dens) + 1e-3, 0.0, dur):
        k = max(3, ns(rng.uniform(0.00015, 0.0006)))
        g = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 2.5))
        place(y, g * rng.lognormal(-0.3, 0.8), tc, wrap=wrap_loop)
    return y


def _rock_groan(rng, dur):
    """La roccia che geme lontano (la risacca che spinge sullo scoglio): un attrito lentissimo e grave che eccita
    pochi modi duri e bassi, con la pietra che non risuona quasi."""
    m = ns(dur)
    rate = curve(m, [(0, 3.5), (dur * 0.35, 9.0), (dur * 0.7, 6.0), (dur, 2.5)], 'log') * (1 + 0.2 * rand_curve(m, 2.0, rng))
    amp = curve(m, [(0, 0), (dur * 0.25, 1), (dur * 0.7, 0.7), (dur, 0)]) * \
        (0.35 + 0.65 * np.abs(np.tanh(2 * rand_curve(m, 4.0, rng))))
    exc = stick_slip(m, rng, rate, amp, jitter=0.25, grain=0.002)
    fr = np.sort(loguniform(rng, 45, 420, 10))
    g = modal(exc, fr, rng.uniform(0.15, 0.6, 10), rng.uniform(0.3, 1.0, 10))
    return normalize(lowpass(g, 420, 2))


def _demand(rng, dur, flow_pts, strain=0.0):
    """La valvola a domanda dell'erogatore quando tiri il fiato: lo scatto della leva, il sibilo dell'aria che
    entra (rumore con le due risonanze del boccaglio), sotto la gola e la bocca che prendono aria. strain: quanto
    tira duro (aria bassa): il sibilo si fa stretto e balbetta."""
    n = ns(dur)
    nz = rng.standard_normal(n)
    flow = curve(n, flow_pts)
    if strain:
        st = np.clip(0.55 + 0.9 * rand_curve(n, 11.0 + 8 * strain, rng), 0.0, 1.0)
        flow = flow * (1.0 - 0.7 * strain + 0.7 * strain * st)
    q = 3.0 + 5.0 * strain
    hiss = (0.8 * resonate(nz, 2900 * (1 + 0.15 * strain), q) + 0.55 * resonate(nz, 4700, q + 1.0)
            + 0.35 * resonate(nz, 1450, 2.4) + 0.15 * bandpass(nz, 1500, 6500, 2))
    hiss = normalize(lowpass(hiss, 5200, 4))
    throat = tract_noise(rng, dur, [(0, 'o'), (dur, 'u')], scale=1.0, amp_pts=None, hiss=0.05)
    throat = normalize(lowpass(throat, 1800, 2))
    y = (hiss * (0.25 + 0.75 * flow ** 1.3) + 0.5 * throat) * flow
    # lo scatto della leva quando apre: un tic di plastica e metallo, ovattato
    m = ns(0.03)
    exc = np.zeros(m)
    exc[:3] = [1.0, -0.6, 0.3]
    tick = modal(exc, [1850, 3150, 4400], [0.01, 0.007, 0.005], [1.0, 0.6, 0.3])
    place(y, 0.25 * normalize(tick), 0.0)
    return normalize(y)


def _exhaust(rng, dur, amp_pts, wild=0.0):
    """Il fiato che esce dalla valvola di scarico: la membrana di gomma che sbatte (un borbottio grave a scatti),
    e la colonna di bolle che parte dal boccaglio e sale accanto alle orecchie. Mono: lo spazio lo dà chi lo usa."""
    n = ns(dur)
    env = curve(n, amp_pts)
    nz = rng.standard_normal(n)
    flap = lowpass(nz, 700, 2) * rough_mod(n, rng, 26.0 + 10 * wild, 0.85, wobble=0.4)
    flap = normalize(resonate(flap, 240, 1.4) + 0.6 * lowpass(flap, 300, 2)) * env
    y = 0.55 * flap
    t_ = tvec(n)
    bub = np.zeros(n)
    for tb in poisson_times(rng, lambda tt: (160.0 + 120 * wild) * np.interp(tt, t_, env) + 1e-3, 0.0, dur):
        f = float(loguniform(rng, 140, 1300))
        b = bubble(f, rng.uniform(0.0, 0.05), rng.lognormal(0, 0.4) * (140 / f) ** 0.25 * np.interp(tb, t_, env),
                   decay_mult=rng.uniform(0.4, 0.75), max_dur=0.3)
        place(bub, b, tb)
    y = y + 0.9 * normalize(bub)
    return normalize(lowpass(y, 4500, 2))


def _column(rng, dur, amp=1.0):
    """La colonna di bolle che, uscita dal boccaglio, sale e si allontana sopra la testa: bolle sempre più rade,
    più piccole e più lontane (il tono resta basso: salgono, ma non «cantano»)."""
    n = ns(dur)
    y = np.zeros(n)
    for tb in poisson_times(rng, lambda tt: 70.0 * np.exp(-tt / (dur * 0.35)) + 1e-3, 0.0, dur):
        f = float(loguniform(rng, 300, 2200))
        a = 0.5 * np.exp(-tb / (dur * 0.45)) * rng.lognormal(0, 0.4) * (300 / f) ** 0.25
        place(y, bubble(f, rng.uniform(0.0, 0.05), a, decay_mult=rng.uniform(0.5, 0.9), max_dur=0.2), tb)
    return amp * lowpass(y, 3800, 2)


def _kick(rng, dur=0.8, a=1.0):
    """Un colpo di pinne: l'acqua spinta via (un «vuum» grave con l'attacco lento), la pala che flette e frulla."""
    n = ns(dur)
    nz = rng.standard_normal(n)
    env = curve(n, [(0, 0.3), (dur * 0.35, 1), (dur * 0.6, 0.6), (dur, 0)])
    fc = curve(n, [(0, 120), (dur * 0.35, 380), (dur, 140)], 'log')
    push = tv_lowpass(nz, fc, 0.9) * env
    flex = bandpass(nz, 300, 1400, 2) * rough_mod(n, rng, 18.0, 0.7) * curve(n, [(0, 0), (dur * 0.3, 1), (dur * 0.55, 0)])
    return a * normalize(normalize(push) + 0.2 * normalize(flex))


def _body_shift(rng, dur=2.0, size=1.0):
    """Un corpo grosso che si gira nel sonno sott'acqua: l'acqua spostata (un'onda lenta e grave che passa), la
    pelle che sfrega sul letto, un velo di limo che si alza e ricade."""
    n = ns(dur)
    nz = rng.standard_normal(n)
    env = curve(n, [(0, 0.3), (dur * 0.3, 1), (dur * 0.65, 0.6), (dur, 0)])
    fc = curve(n, [(0, 90), (dur * 0.35, 260 + 120 * (1 - size)), (dur, 100)], 'log')
    y = normalize(tv_lowpass(nz, fc, 0.8)) * env
    rub = bandpass(nz, 250, 1800, 2) * np.clip(0.3 + 0.8 * rand_curve(n, 7.0, rng), 0, None) * env
    y += 0.25 * normalize(rub)
    silt = bandpass(rng.standard_normal(n), 1800, 6000, 2) * curve(n, [(0, 0), (dur * 0.45, 1), (dur, 0)])
    y += 0.04 * normalize(silt)
    _deep_bubbles(y, rng, dur * 0.2, 6, 0.4, 250, 1200, 0.15)
    return normalize(y)


def _clink(rng, f, a=1.0, t60=0.1):
    """Una conchiglia appesa che tocca l'altra: un tintinnio di guscio (pochi modi inarmonici), smorzato
    dall'acqua."""
    m = ns(min(0.4, t60 * 3))
    exc = np.zeros(m)
    exc[0], exc[1] = 1.0, -0.7
    r = np.array([1.0, 1.83, 2.94, 4.3]) * rng.uniform(0.97, 1.03, 4)
    y = modal(exc, f * r, [t60, t60 * 0.6, t60 * 0.4, t60 * 0.25], [1.0, 0.5, 0.3, 0.15])
    return a * normalize(y)


def _drum_purr(rng, dur, rate_pts, env_pts, f=165.0):
    """Il tamburo della vescica natatoria di Robin (robin.py), piano e lento: fusa d'acqua nel sonno."""
    n = ns(dur)
    t_ = tvec(n)
    rate = curve(n, rate_pts, 'log')
    amp = curve(n, env_pts)
    y = np.zeros(n)
    t = 0.0
    while t < dur - 0.01:
        a = float(np.interp(t, t_, amp))
        if a > 0.01:
            m = ns(0.06)
            exc = np.zeros(m)
            k = max(2, ns(rng.uniform(0.002, 0.0035)))
            exc[:k] = np.sin(np.pi * (np.arange(k) + 0.5) / k)
            ff = f * rng.uniform(0.94, 1.06)
            body = modal(exc, [ff, ff * 1.93, ff * 3.05], [0.02, 0.012, 0.007], [1.0, 0.45, 0.2])
            place(y, a * rng.lognormal(0, 0.2) * normalize(body), t)
        r = float(np.interp(t, t_, rate))
        t += (1.0 / r) * (1.0 + 0.15 * rng.standard_normal())
    return normalize(y)


def _reed_sleep(rng, dur, f_pts, amp_pts, stall=0.6):
    """L'ancia della trombetta di Archie (archie.py) con un filo di fiato: un ronzio nasale debole che s'inceppa."""
    n = ns(dur)
    f = curve(n, f_pts, 'log') * cents(25 * rand_curve(n, 6.0, rng))
    ph = phase_of(f)
    opening = np.maximum(0.0, np.sin(TWO_PI * ph)) ** 2.5
    buzz = normalize(np.tanh(2.0 * normalize(np.diff(lowpass(opening, 8000, 2), prepend=0.0))))
    st = np.clip(0.5 + 0.9 * rand_curve(n, 14.0, rng), 0.0, 1.0)
    buzz = buzz * (1.0 - stall + stall * st)
    horn = (0.55 * resonate(buzz, 480, 1.6) + resonate(buzz, 1150, 2.6) + 0.7 * resonate(buzz, 2350, 3.2) + 0.2 * buzz)
    air = bandpass(rng.standard_normal(n), 700, 4000, 2)
    return (normalize(horn) + 0.35 * normalize(air)) * curve(n, amp_pts)


def _wet_paper(rng, dur, env_pts, density=260.0, a=1.0):
    """La carta fradicia della trombetta che si srotola o si riavvolge: scatti molli, più fruscio che crepitio."""
    y = crinkle(rng, dur, env_pts, density=density, f_lo=900.0, f_hi=5000.0, res=2400.0, swish=0.45)
    return a * normalize(lowpass(y, 3200, 2))


def _coil(rng, n, f=3870.0):
    """Il fischio sottile della bobina del giocattolo di Hatch (hatch.py): rumore a banda strettissima, mai un
    tono pulito."""
    nz = rng.standard_normal(n)
    return normalize(tv_bandpass(nz, np.full(n, f) * cents(25 * rand_curve(n, 0.7, rng)), np.full(n, 40.0)))


# ═════════════════════════ l'ambiente della grotta ═════════════════════════

def _amb_dive(s, rng):
    """Sott'acqua nella grotta (loop): il silenzio pesante dell'acqua che preme sulle orecchie, il mare lontano
    sopra che respira con l'onda lunga, la grotta che rimbomba piano quando la risacca entra dall'imboccatura,
    sassolini che rotolano giù per la roccia, il crepitio dei gamberetti, due volte la roccia che geme lontano e una
    volta un pezzo del parco (un rottame di scivolo) che la corrente fa toccare sulla pietra."""
    n, d = s.n, s.dur
    t = tvec(n)
    cycles = 6                                         # l'onda lunga: 8 s, cicli interi nel loop
    swell = 0.5 + 0.5 * np.sin(TWO_PI * cycles * t / d)
    out = np.zeros((2, n))
    for c in range(2):
        # il silenzio pesante: un letto grave e scurissimo (la pressione), quasi immobile
        bed = spectral_noise(n, rng, lambda f: bw_bp(f, 20, 260, 2), exponent=1.6)
        # il mare sopra: lo sciabordio della superficie sentito da sotto, ovattato, che segue l'onda
        sea = spectral_noise(n, rng, lambda f: bw_bp(f, 70, 900, 2), exponent=1.0)
        sw = np.roll(swell, c * ns(0.6))
        out[c] += 0.05 * bed * (0.8 + 0.2 * sw) + 0.018 * sea * (0.2 + 0.8 * sw ** 2)
        # la grotta che rimbomba: la risacca che entra e spinge l'acqua dentro (risonanze gravi della sala)
        surge = spectral_noise(n, rng, lambda f: peak_shape(f, 38.0, 3.0, 9.0) + peak_shape(f, 57.0, 4.0, 5.0)
                               + 0.2 * bw_bp(f, 25, 140, 2) - 1.0)
        out[c] += 0.03 * surge * np.roll(swell, ns(1.2) + c * ns(0.3)) ** 3
    # il colpo sordo della risacca sull'imboccatura, tre volte, dentro la grotta
    hits = np.zeros(n)
    for k in (0, 2, 4):
        th = (k + 0.15) * d / cycles + rng.uniform(-0.3, 0.3)
        m = ns(1.6)
        thump = lowpass(rng.standard_normal(m), 85, 2) * curve(m, [(0, 0), (0.12, 1), (0.5, 0.4), (1.6, 0)])
        place(hits, 0.6 * normalize(thump), th, wrap=True)
    # sassolini che rotolano (sparsi nella grotta, a destra e a sinistra)
    peb = np.zeros((2, n))
    for tp in poisson_times(rng, 0.13, 0.0, d):
        place(peb, pan(_pebbles(rng, a=rng.uniform(0.3, 0.7)), rng.uniform(-0.8, 0.8)), tp, wrap=True)
    peb = circular(lambda x: lowpass(x, 3600, 2), peb)
    # i gamberetti: un crepitio rado, lontano (gli acuti si spengono nell'acqua)
    shr = np.stack([_shrimp(n, rng, rate=5.0) for _ in range(2)])
    shr = circular(lambda x: lowpass(highpass(x, 1800, 2), 5000, 2), shr)
    # la roccia che geme lontano, due volte
    groan = np.zeros(n)
    for tg, dg in ((rng.uniform(6, 12), 3.4), (rng.uniform(28, 34), 2.8)):
        place(groan, _rock_groan(rng, dg), tg, wrap=True)
    # un pezzo del parco che tocca la roccia: la vetroresina di uno scivolo, sorda e cava
    debris = np.zeros(n)
    for j, td in enumerate((rng.uniform(18, 22), )):
        for r in range(int(rng.integers(2, 4))):
            k = knock(rng, force=0.003, base=rng.uniform(110, 150), t60=0.25, count=7, bright=0.6, dur=0.9)
            place(debris, (0.7 ** r) * lowpass(k, 900, 2), td + r * rng.uniform(0.35, 0.6), wrap=True)
    # tutto passa per la grotta
    far = hits + 0.5 * groan + 0.35 * debris
    far = circular(lambda x: lowpass(x, 900, 2), far)
    ir = _cave_ir(rng, 3.2)
    wet = convolve(far, ir, circular=True) + 0.25 * stereo(far)
    wet *= rms(out) * db_to_lin(-6.0) / db_to_lin(active_rms_db(wet))
    near = peb + 0.6 * convolve(mono(peb), _cave_ir(rng, 2.2), circular=True)
    near *= rms(out) * db_to_lin(-14.0) / db_to_lin(active_rms_db(near))
    shr *= rms(out) * db_to_lin(-30.0) / (rms(shr) + 1e-12)
    # il mare sopra e il letto arrivano solo gravi: niente fruscio a banda larga sopra i 2 kHz
    out = circular(lambda x: lowpass(x, 700, 4), out)
    out = out + wet + near + shr
    return circular(lambda x: highpass(x, 22, 2), out)


register('amb_dive', _amb_dive, 48.0, loop=True, channels=2, category='amb', gain=0.8, rms=-28.0)


# ═════════════════════════ l'erogatore ═════════════════════════

def _breath_loop(rng, d, t_in, d_in, t_out, d_out, strain=0.0, wild=0.0):
    """Un ciclo di respiro nell'erogatore, circolare: dentro (valvola a domanda), fuori (scarico e colonna di
    bolle che sale e si allontana sopra la testa, un po' allargata)."""
    n = ns(d)
    out = np.zeros((2, n))
    inh = _demand(rng, d_in, [(0, 0), (0.08, 0.8), (d_in * 0.6, 1.0), (d_in * 0.9, 0.6), (d_in, 0)], strain=strain)
    place(out, 0.55 * inh, t_in, wrap=True)
    ex = _exhaust(rng, d_out, [(0, 0), (0.1, 1.0), (d_out * 0.5, 0.8), (d_out * 0.85, 0.4), (d_out, 0)], wild=wild)
    place(out, 0.8 * ex, t_out, wrap=True)
    # la colonna di bolle, diversa per ogni orecchio (sale accanto alla testa, un po' allargata)
    for c in range(2):
        cc = np.zeros(n)
        place(cc, _column(rng, 1.8), t_out + d_out * 0.3 + 0.02 * c, wrap=True)
        out[c] += 0.35 * cc
    return out


def _dive_breath(s, rng):
    """Il respiro calmo nell'erogatore (loop da 5,2 s, 11-12 respiri al minuto): dentro il sibilo della valvola a
    domanda con lo scatto della leva, fuori il borbottio della membrana di scarico e la colonna di bolle che sale
    accanto alle orecchie e si allontana. Il gioco lo accelera col playbackRate quando l'aria cala."""
    out = _breath_loop(rng, s.dur, 0.0, 1.55, 1.85, 2.0)
    return circular(lambda x: highpass(x, 40, 2), out)


register('dive_breath', _dive_breath, 5.2, loop=True, channels=2, category='sfx', gain=0.6, rms=-22.0,
         params={'rotate_max': 0.2})


def _dive_breath_fast(s, rng):
    """Il respiro affannato ad aria bassa (loop da 3,0 s, 20 al minuto): l'inspiro corto che tira duro (il sibilo
    stretto e balbettante della valvola), l'espiro di colpo con un'esplosione di bolle."""
    out = _breath_loop(rng, s.dur, 0.0, 0.95, 1.05, 1.5, strain=0.6, wild=0.8)
    return circular(lambda x: highpass(x, 40, 2), out)


register('dive_breath_fast', _dive_breath_fast, 3.0, loop=True, channels=2, category='sfx', gain=0.65, rms=-21.0,
         params={'rotate_max': 0.2})


# ═════════════════════════ le dissolvenze ═════════════════════════

def _dive_down(s, rng):
    """La discesa: ci si lascia cadere all'indietro dalla barca (il tonfo e subito il mondo che si chiude sopra la
    testa), la nuvola di bolle che ti avvolge e ti risale addosso, poi il silenzio pesante; il primo respiro
    nell'erogatore, le orecchie che si compensano (due piccoli schiocchi), il mare sopra sempre più lontano mentre
    scendi lungo la cima dell'ancora."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    # il tonfo: lo schizzo sentito già da sotto (il colpo largo, subito ovattato)
    sp = splash(rng, size=0.9, dur=1.6)
    m = len(sp)
    sp = tv_lowpass(sp, curve(m, [(0, 9000), (0.06, 2500), (0.3, 900), (1.6, 600)], 'log'), 0.7)
    place(out, 0.9 * sp, 0.0)
    m = ns(0.9)
    whump = lowpass(rng.standard_normal(m), 160, 2) * curve(m, [(0, 0), (0.02, 1), (0.25, 0.4), (0.9, 0)])
    place(out, 0.8 * normalize(whump), 0.0)
    # la nuvola di bolle che ti avvolge (fitta, a destra e a sinistra, poi si dirada salendo)
    _deep_bubbles(out, rng, 0.02, 320, 0.45, 180, 2600, 0.12, pan_range=(-0.9, 0.9))
    m = ns(2.4)
    roar = bandpass(rng.standard_normal(m), 200, 2200, 2) * curve(m, [(0, 0), (0.05, 1), (0.6, 0.45), (2.4, 0)])
    place(out, 0.25 * normalize(roar), 0.02)
    # il silenzio pesante che arriva, e il mare sopra che si allontana
    bed = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 20, 260, 2), exponent=1.6) for _ in range(2)])
    sea = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 70, 1600, 2), exponent=1.0) for _ in range(2)])
    fc = curve(n, [(0, 1600), (1.5, 1200), (d, 350)], 'log')
    sea = np.stack([tv_lowpass(sea[c], fc, 0.7) for c in range(2)])
    out += 0.06 * bed * curve(n, [(0, 0), (1.2, 0.6), (d, 1.0)]) + \
        0.05 * sea * curve(n, [(0, 0), (0.6, 1.0), (d * 0.6, 0.5), (d, 0.25)])
    # il primo respiro nell'erogatore (si è appena infilato il boccaglio)
    place(out, 0.5 * _demand(rng, 1.3, [(0, 0), (0.08, 0.8), (0.8, 1.0), (1.1, 0.6), (1.3, 0)]), 2.3)
    ex = _exhaust(rng, 1.8, [(0, 0), (0.1, 1.0), (0.9, 0.8), (1.5, 0.4), (1.8, 0)])
    place(out, 0.7 * ex, 3.85)
    for c in range(2):
        cc = np.zeros(n)
        place(cc, _column(rng, 1.8), 4.4 + 0.02 * c)
        out[c] += 0.35 * cc
    # le orecchie che si compensano: due schiocchi piccoli e sordi dentro la testa
    for te in (2.0, 5.7):
        k = ns(0.02)
        pop = lowpass(rng.standard_normal(k), 900, 2) * exp_env(k, 0.008, attack=0.0005)
        place(out, 0.25 * normalize(pop), te + rng.uniform(-0.05, 0.05))
    # la cima dell'ancora che sfrega sulla mano mentre scendi
    m = ns(1.8)
    rope = bandpass(rng.standard_normal(m), 300, 2500, 2) * np.clip(0.3 + 0.9 * rand_curve(m, 6.0, rng), 0, None) \
        * curve(m, [(0, 0), (0.4, 1), (1.4, 0.7), (1.8, 0)])
    place(out, pan(0.05 * normalize(rope), 0.35), 5.5)
    return highpass(out, 25, 2)


register('dive_down', _dive_down, 8.0, channels=2, category='sfx', gain=0.8, rms=-21.0, max_gr=5.0)


def _swim(s, rng):
    """La nuotata fra un posto e l'altro (copre la dissolvenza): tre colpi di pinne lenti, il corpo che fende
    l'acqua (un fruscio che passa), un espiro con la colonna di bolle che ti scivola lungo le orecchie, e alla
    fine l'arrivo (l'acqua che si ferma)."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    tk = 0.0
    for k in range(3):
        place(out, pan(0.7 * _kick(rng, 0.85, 1.0 - 0.15 * k), (-0.25 if k % 2 else 0.25)), tk)
        tk += rng.uniform(0.62, 0.74)
    for c in range(2):
        m = ns(d)
        glide = bandpass(rng.standard_normal(m), 120, 900, 2) * curve(m, [(0, 0), (0.6, 1), (d - 0.6, 0.6), (d, 0)])
        out[c] += 0.12 * normalize(glide)
    ex = _exhaust(rng, 1.1, [(0, 0), (0.08, 1.0), (0.6, 0.7), (1.1, 0)])
    place(out, 0.45 * ex, s.params.get('ex', 0.6))
    _deep_bubbles(out, rng, s.params.get('ex', 0.6) + 0.3, 70, 0.4, 300, 2000, 0.07, pan_range=(-0.8, 0.8))
    return highpass(out, 30, 2)


register('dive_swim_1', _swim, 2.6, channels=2, category='sfx', gain=0.7, rms=-22.0, params={'ex': 0.6})
register('dive_swim_2', _swim, 2.6, channels=2, category='sfx', gain=0.7, rms=-22.0, params={'ex': 1.1})


def _bubbles(s, rng):
    """Le bolle della dissolvenza: un espiro forte e la nuvola che passa davanti alla maschera da sinistra a
    destra (per i tagli secchi fra un posto e l'altro)."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    ex = _exhaust(rng, 0.8, [(0, 0), (0.05, 1.0), (0.5, 0.6), (0.8, 0)], wild=0.5)
    place(out, 0.6 * ex, 0.0)
    for k in range(220):
        tb = rng.uniform(0.02, 1.0) ** 1.3
        p = -0.9 + 1.8 * tb / 1.0 + rng.uniform(-0.25, 0.25)
        f = float(loguniform(rng, 220, 2400))
        b = bubble(f, rng.uniform(0.0, 0.05), 0.12 * rng.lognormal(0, 0.4) * (220 / f) ** 0.3,
                   decay_mult=rng.uniform(0.5, 0.85), max_dur=0.25)
        place(out, pan(b, p), tb)
    return lowpass(highpass(out, 40, 2), 4500, 2)


register('dive_bubbles', _bubbles, 1.4, channels=2, category='sfx', gain=0.7, rms=-21.0)


def _air_low(s, rng):
    """L'avviso dell'aria (a metà del ritorno): il pescatore picchietta due volte col dito sul vetro del manometro
    (l'ago, come quello del voltmetro, che trema e si assesta con un tic), poi un respiro che tira duro: la
    valvola a domanda sibila stretta e balbetta, la membrana che cigola."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    # il dito sul vetro: due colpetti duri e sordi (vetro e ottone sott'acqua)
    for k, te in enumerate((0.0, 0.24)):
        m = ns(0.08)
        exc = np.zeros(m)
        exc[:2] = [1.0, -0.5]
        tap = modal(exc, np.array([1650, 2780, 4300]) * rng.uniform(0.98, 1.02), [0.02, 0.012, 0.008], [1.0, 0.5, 0.3])
        place(out, pan(0.5 * normalize(tap) * (1.0 - 0.15 * k), 0.15), te)
    # l'ago che trema e si assesta: due tic sottili
    for te in (0.52, 0.61):
        m = ns(0.02)
        exc = np.zeros(m)
        exc[0] = 1.0
        place(out, pan(0.12 * normalize(modal(exc, [5200, 7400], [0.004, 0.003], [1, 0.5])), 0.15), te)
    # il respiro che tira duro
    inh = _demand(rng, 1.3, [(0, 0), (0.1, 0.9), (0.7, 0.6), (1.1, 0.8), (1.3, 0)], strain=1.0)
    place(out, 0.6 * inh, 0.85)
    sq = rubber_squeal(rng, 0.35, rate_pts=[(0, 260), (0.35, 330)], env_pts=[(0, 0), (0.05, 1), (0.35, 0)], bright=0.7)
    place(out, 0.08 * lowpass(sq, 3000, 2), 1.7)
    return highpass(out, 40, 2)


register('dive_air_low', _air_low, 2.4, channels=2, category='sfx', gain=0.8, rms=-20.0)


def _air_out(s, rng):
    """L'aria che finisce: un ultimo inspiro che dà poco e poi niente (il sibilo che si strozza, la membrana che si
    incolla con uno schiocco di gomma, il risucchio a vuoto), un secondo tentativo a vuoto, e lo scarico che
    borbotta l'ultima aria. Poi si risale da soli (dive_up)."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    inh = _demand(rng, 0.9, [(0, 0), (0.06, 0.8), (0.35, 0.5), (0.6, 0.1), (0.9, 0)], strain=1.0)
    place(out, 0.6 * inh, 0.0)
    for te, a in ((0.85, 1.0), (1.5, 0.7)):
        # la membrana risucchiata che si incolla: uno schiocco di gomma sordo e un risucchio secco
        m = ns(0.12)
        flop = lowpass(rng.standard_normal(m), 600, 2) * exp_env(m, 0.04, attack=0.002)
        place(out, 0.35 * a * normalize(flop), te)
        place(out, 0.18 * a * squish(rng, 0.1, 300, 1500, density=700, sticky=0.8), te + 0.01)
    # l'ultima aria che esce dallo scarico, poca
    ex = _exhaust(rng, 0.8, [(0, 0), (0.05, 0.7), (0.4, 0.3), (0.8, 0)])
    place(out, 0.45 * ex, 1.85)
    return lowpass(highpass(out, 40, 2), 6000, 2)


register('dive_air_out', _air_out, 2.8, channels=2, category='sfx', gain=0.8, rms=-21.0)


def _dive_up(s, rng):
    """La risalita: due soffi del gav che si gonfia (l'aria della frusta a bassa pressione), i colpi di pinne verso
    la luce, le bolle che salgono con te, il mare sopra che si fa sempre più vicino e più chiaro; la testa che
    rompe il pelo dell'acqua: il mondo che si riapre di colpo, l'acqua che ti cola dalla maschera, il boccaglio
    sputato e un respiro grande nell'aria dell'alba, le onde contro la barca."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    t_s = 5.2                                           # la superficie
    # il gav che si gonfia: due soffi d'aria compressa, ovattati
    for te, dd in ((0.0, 0.45), (0.65, 0.35)):
        m = ns(dd)
        hs = lowpass(bandpass(rng.standard_normal(m), 700, 3500, 2), 3000, 4) * \
            curve(m, [(0, 0), (0.01, 1), (dd * 0.8, 0.8), (dd, 0)])
        place(out, pan(0.3 * normalize(hs), -0.3), te)
        _deep_bubbles(out, rng, te + 0.05, 25, 0.15, 260, 1500, 0.06, pan_range=(-0.6, 0.0))
    # i colpi di pinne
    for k, tk in enumerate((1.2, 2.0, 2.8, 3.6)):
        place(out, pan(0.55 * _kick(rng, 0.8), 0.25 if k % 2 else -0.25), tk)
    # l'espiro lungo mentre sali (si risale buttando fuori l'aria), e le bolle che salgono con te
    place(out, 0.5 * _exhaust(rng, 2.2, [(0, 0), (0.1, 0.8), (1.6, 0.6), (2.2, 0)]), 1.5)
    _deep_bubbles(out, rng, 1.6, 120, 1.2, 280, 2400, 0.05, pan_range=(-0.8, 0.8))
    # il mare sopra che si avvicina e si schiarisce, fino alla superficie
    sea = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 60, 3500, 2), exponent=1.2) for _ in range(2)])
    fc = curve(n, [(0, 350), (t_s - 0.05, 1400), (t_s + 0.05, 3800), (d, 3800)], 'log')
    sea = np.stack([tv_lowpass(sea[c], fc, 0.7) for c in range(2)])
    out += 0.06 * sea * curve(n, [(0, 0.3), (t_s - 0.1, 1.0), (t_s + 0.1, 0.25), (d, 0.15)])
    bed = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 20, 260, 2), exponent=1.6) for _ in range(2)])
    out += 0.06 * bed * curve(n, [(0, 1.0), (t_s - 0.2, 0.7), (t_s, 0.0), (d, 0.0)])
    # la superficie: la testa che rompe il pelo dell'acqua
    place(out, 0.7 * splash(rng, size=0.45, dur=1.0), t_s)
    for _ in range(int(rng.integers(10, 16))):
        place(out, pan(droplet(rng, amp=rng.uniform(0.04, 0.12), tonal=0.4), rng.uniform(-0.6, 0.6)),
              t_s + rng.uniform(0.15, 1.4))
    # le onde contro la barca, qui accanto
    for te in (t_s + 0.4, t_s + 1.6):
        place(out, pan(0.3 * lap(rng, 0.5, dur=1.0, hull=0.4), 0.45), te)
    # il boccaglio sputato e il respiro grande nell'aria
    place(out, 0.3 * squish(rng, 0.08, 400, 2200, density=900, sticky=0.6), t_s + 0.45)
    place(out, 0.45 * breath(rng, 0.85, inhale=True, amp_pts=[(0, 0), (0.15, 1), (0.6, 0.9), (0.85, 0)], tremor=0.2),
          t_s + 0.55)
    place(out, 0.3 * breath(rng, 1.0, inhale=False, amp_pts=[(0, 0), (0.1, 1), (0.5, 0.6), (1.0, 0)]), t_s + 1.5)
    return highpass(out, 30, 2)


register('dive_up', _dive_up, 7.6, channels=2, category='sfx', gain=0.8, rms=-21.0, max_gr=5.0)


# ═════════════════════════ l'offerta ═════════════════════════

def _offer(s, rng):
    """Il pesce lasciato accanto al mostro: la mano che lo lascia andare (l'acqua che scivola via), il pesce che si
    posa nella sabbia con un tonfo morbido e grave, la sabbia che si solleva in uno sbuffo fine e ricade piano, una
    bollicina dalle branchie."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    m = ns(0.5)
    let = lowpass(bandpass(rng.standard_normal(m), 200, 1200, 2), 1200, 4) * curve(m, [(0, 0), (0.1, 1), (0.5, 0)])
    place(y, 0.2 * normalize(let), 0.0)
    # il tonfo nella sabbia
    t0 = 0.42
    m = ns(0.35)
    thud = lowpass(rng.standard_normal(m), 180, 2) * curve(m, [(0, 0), (0.008, 1), (0.08, 0.35), (0.35, 0)])
    place(y, 0.9 * normalize(thud), t0)
    place(y, 0.35 * squish(rng, 0.12, 250, 1400, density=600, sticky=0.3), t0 + 0.005)
    # la sabbia: uno sbuffo di granelli (crepitio fitto e debole), poi la ricaduta lenta
    m = ns(1.3)
    grains = np.zeros(m)
    for tg in poisson_times(rng, lambda tt: 900.0 * np.exp(-tt / 0.25) + 40.0 * np.exp(-tt / 0.8), 0.0, 1.3):
        k = max(2, ns(rng.uniform(0.0001, 0.0003)))
        place(grains, rng.standard_normal(k) * rng.lognormal(-1.0, 0.6), tg)
    grains = bandpass(grains, 1500, 6500, 2)
    place(y, 0.18 * normalize(grains), t0 + 0.01)
    # la coda che sbatte una volta sola sulla sabbia (è morto, ma la coda molle ricade)
    m = ns(0.12)
    flap = lowpass(rng.standard_normal(m), 400, 2) * exp_env(m, 0.04, attack=0.003)
    place(y, 0.3 * normalize(flap), t0 + 0.38)
    for tb in (t0 + 0.55, t0 + 0.9):
        place(y, bubble(float(loguniform(rng, 700, 1300)), xi=0.04, amp=0.06, decay_mult=0.9), tb)
    return _den_shot(y, rng, wet=0.35, lp=5000.0)


register('offer_fish', _offer, 1.9, category='sfx', gain=0.85, rms=-20.0)


# ═════════════════════════ il respiro nel sonno ═════════════════════════
# Mono, loop. Ognuno con i tratti dei suoi versi sulla barca, ma addormentato: lento, basso, sott'acqua.

def _sleep_gulpy(s, rng):
    """Gulpy che dorme raggomitolato sul materasso di salvagenti con la mascella che pende aperta: due russate
    enormi nel loop. Dentro: il russare grave e bagnato (il fry della gola gigante, il palato molle che sbatte);
    fuori: dalla bocca spalancata escono bolle grosse e lente, una dopo l'altra, con le labbra molli che
    sbattono; a volte la paperella di gomma del collo che cigola quando il petto si gonfia."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    cyc = d / 2
    for k in range(2):
        t0 = k * cyc
        din = 2.6
        sn = vox(rng, din, [(0, 30 + 3 * k), (din * 0.6, 36), (din, 33)], [(0, 'O'), (din * 0.5, 'a'), (din, 'O')],
                 scale=GIANT, amp_pts=[(0, 0), (din * 0.5, 0.7), (din * 0.85, 1.0), (din, 0)], oq=0.35, jitter=0.12,
                 shimmer=0.35, sub=0.6, breath=0.9, rough=0.65, rough_rate=19.0 + 4 * k, wander=20.0)
        nz = tract_noise(rng, din, [(0, 'O'), (din, 'a')], scale=GIANT, amp_pts=[(0, 0), (din * 0.8, 1), (din, 0)],
                         hiss=0.1)
        nz = lip_flutter(nz, rng, rate=21.0, depth=0.75)
        inh = wet_throat(0.7 * sn + 0.5 * nz, rng, rate=24, depth=0.55, bubbles=0.35, flange=0.4, f_lo=100, f_hi=420)
        place(y, 0.8 * normalize(lowpass(inh, 1800, 2)), t0 + 0.1, wrap=True)
        # fuori: le bolle grosse dalla bocca aperta, le labbra molli che sbattono
        dex = 2.4
        ex = tract_noise(rng, dex, [(0, 'o'), (dex, 'u')], scale=GIANT, amp_pts=[(0, 0), (0.15, 1), (dex * 0.6, 0.5),
                                                                                 (dex, 0)], hiss=0.08)
        ex = lip_flutter(ex, rng, rate=13.0, depth=0.8)
        place(y, 0.35 * normalize(lowpass(ex, 1200, 2)), t0 + 2.85, wrap=True)
        tb = t0 + 2.9
        for j in range(int(rng.integers(5, 8))):
            f = float(loguniform(rng, 75, 190))
            place(y, bubble(f, xi=rng.uniform(0.0, 0.06), amp=0.55 * rng.uniform(0.6, 1.0) * (0.85 ** j),
                            decay_mult=rng.uniform(0.35, 0.55), max_dur=0.5), tb, wrap=True)
            # ogni bollona si porta dietro qualche bollicina (il filo acuto)
            _deep_bubbles(y, rng, tb + 0.02, 3, 0.05, 600, 1800, 0.05, wrap=True)
            tb += rng.uniform(0.22, 0.4)
        if k == 1:
            sq = rubber_squeal(rng, 0.5, rate_pts=[(0, 300), (0.25, 420), (0.5, 330)],
                               env_pts=[(0, 0), (0.1, 1), (0.5, 0)], bright=0.6)
            place(y, 0.06 * lowpass(sq, 2500, 2), t0 + 1.9, wrap=True)
        place(y, 0.12 * saliva(rng, 0.6, rate=40, f_lo=900, f_hi=3000), t0 + 2.4, wrap=True)
    return _den_loop(y, rng, wet=0.3, lp=4000.0)


register('sleep_gulpy', _sleep_gulpy, 13.0, loop=True, category='mon', gain=0.7, rms=-23.0)


def _sleep_molly(s, rng):
    """Molly che dorme su un fianco abbracciata ai braccioli: tre respiri piccoli e lenti di bambina (dal naso, con
    un filo di soffio), a ogni espiro due o tre bollicine dalla bocca; al secondo respiro un mugolio nel sonno, e
    sotto, appena, la stessa voce da una gola più grande; i braccioli di plastica che stridono una volta quando li
    stringe."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    cyc = d / 3
    for k in range(3):
        t0 = k * cyc
        din, dex = 1.2, 1.6
        inh = tract_noise(rng, din, [(0, 'm'), (din, 'u')], scale=CHILD, amp_pts=[(0, 0), (din * 0.7, 1), (din, 0)],
                          hiss=0.25)
        place(y, 0.45 * normalize(lowpass(inh, 3500, 2)), t0, wrap=True)
        ex = tract_noise(rng, dex, [(0, 'u'), (dex, '@')], scale=CHILD, amp_pts=[(0, 0), (0.15, 1), (dex, 0)], hiss=0.2)
        place(y, 0.4 * normalize(lowpass(ex, 3000, 2)), t0 + din + 0.15, wrap=True)
        _deep_bubbles(y, rng, t0 + din + 0.3, int(rng.integers(2, 4)), 0.25, 500, 1500, 0.18, wrap=True,
                      decay=(0.6, 0.9))
        if k == 1:
            dm = 1.1
            mm = vox(rng, dm, [(0, 330), (0.4, 360), (dm, 290)], [(0, 'm'), (dm, 'm')], scale=CHILD,
                     amp_pts=[(0, 0), (0.2, 1), (0.7, 0.7), (dm, 0)], oq=0.6, jitter=0.03, shimmer=0.15, breath=0.6,
                     breath_base=0.5, bw=1.6, wander=20.0)
            gh = vox(rng, dm, [(0, 330 * 0.47), (0.4, 360 * 0.47), (dm, 290 * 0.47)], [(0, 'm'), (dm, 'u')],
                     scale=0.95, amp_pts=[(0, 0), (0.3, 1), (dm, 0)], oq=0.5, sub=0.4, breath=0.3, wander=20.0)
            mv = wet(normalize(mm) + 0.25 * normalize(gh), rng, rate=20.0, depth=0.3, bubbles=0.2, flange=0.4,
                     f_lo=500, f_hi=1500)
            place(y, 0.22 * normalize(lowpass(mv, 2500, 2)), t0 + din + 0.25, wrap=True)
        if k == 2:
            sq = rubber_squeal(rng, 0.3, rate_pts=[(0, 520), (0.15, 700), (0.3, 560)],
                               env_pts=[(0, 0), (0.05, 1), (0.3, 0)], bright=1.2)
            place(y, 0.06 * sq, t0 + 0.5, wrap=True)
    return _den_loop(y, rng, wet=0.35, lp=4500.0)


register('sleep_molly', _sleep_molly, 11.4, loop=True, category='mon', gain=0.7, rms=-25.0)


def _sleep_hatch(s, rng):
    """Hatch rannicchiato dentro l'armadio aperto: due respiri lunghi dalle narici grandi (un'aspirata lenta e
    bagnata), e fuori le branchie che sbattono piano sotto la mascella con qualche bolla; l'esca del giocattolo
    che si accende e si spegne piano (il fischio sottile della bobina che sale e cala, lo scatto del contatto), i
    denti di vetro che tintinnano una volta, il legno dell'armadio che geme sordo."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    cyc = d / 2
    for k in range(2):
        t0 = k * cyc
        din = 1.8
        nz = rng.standard_normal(ns(din))
        sn = (0.6 * resonate(nz, 1250, 2.5) + 0.5 * resonate(nz, 2300, 3.0) + 0.3 * resonate(nz, 3600, 3.0))
        sn = normalize(lowpass(sn, 3800, 2)) * curve(ns(din), [(0, 0), (din * 0.7, 1), (din * 0.95, 0.8), (din, 0)])
        sn = sn + 0.25 * saliva(rng, din, rate=60, f_lo=900, f_hi=3500, env_pts=[(0, 0.2), (din, 1)])
        place(y, 0.4 * sn, t0, wrap=True)
        dex = 2.4
        gill = tract_noise(rng, dex, [(0, 'o'), (dex, 'u')], scale=0.8, amp_pts=[(0, 0), (0.2, 1), (dex, 0)], hiss=0.05)
        gill = lip_flutter(normalize(lowpass(gill, 1500, 2)), rng, rate=9.0, depth=0.85)
        place(y, 0.4 * gill, t0 + din + 0.3, wrap=True)
        _deep_bubbles(y, rng, t0 + din + 0.5, 6, 0.4, 220, 900, 0.12, wrap=True)
    # l'esca che si accende e si spegne piano: la bobina che fischia (lontana e fioca) e lo scatto del contatto
    lure = np.zeros(n)
    t_ = tvec(n)
    glow = np.zeros(n)
    for ta, db in ((1.5, 3.2), (8.6, 2.6)):
        m = ns(db)
        place(glow, curve(m, [(0, 0), (db * 0.4, 1), (db * 0.6, 1), (db, 0)]), ta, wrap=True)
        exc = np.zeros(ns(0.02))
        exc[:2] = [1.0, -0.6]
        place(lure, 0.15 * normalize(modal(exc, [2100, 3700], [0.006, 0.004], [1, 0.5])), ta, wrap=True)
    lure += 0.05 * _coil(rng, n) * glow
    y += lure
    # i denti di vetro che si toccano, una volta
    place(y, 0.08 * teeth_clack(rng, count=3, spread=0.01, glass=0.7, dur=0.1), 5.2, wrap=True)
    # il legno dell'armadio che geme, sordo
    cr = creak(rng, 0.9, [(0, 9), (0.4, 16), (0.9, 7)], [(0, 0), (0.2, 1), (0.9, 0)], base=150, t60=0.12, bright=0.5)
    place(y, 0.1 * lowpass(cr, 1500, 2), 10.4, wrap=True)
    return _den_loop(y, rng, wet=0.3, lp=4500.0)


register('sleep_hatch', _sleep_hatch, 12.0, loop=True, category='mon', gain=0.7, rms=-24.0)


def _sleep_robin(s, rng):
    """Robin disteso sul mucchio del bottino come un granchio: respira col tamburo della vescica natatoria, piano
    e lento (fuse d'acqua, un «rrr» sordo a ogni espiro), le branchie che soffiano bollicine; due volte le zampette
    dure che si muovono nel sonno e ticchettano sulle cose rubate (una scarpa di gomma, un giocattolo di latta), i
    biglietti fradici che ondeggiano; una volta, dal naso, l'ombra della risatina di chi l'ha fatta franca."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    cyc = d / 3
    for k in range(3):
        t0 = k * cyc
        din = 1.0
        inh = tract_noise(rng, din, [(0, 'u'), (din, 'o')], scale=1.2, amp_pts=[(0, 0), (din * 0.7, 1), (din, 0)],
                          hiss=0.15)
        place(y, 0.25 * normalize(lowpass(inh, 2500, 2)), t0, wrap=True)
        dp = 1.5
        pr = _drum_purr(rng, dp, [(0, 16), (dp * 0.4, 22), (dp, 13)], [(0, 0), (0.2, 1), (dp * 0.7, 0.6), (dp, 0)])
        place(y, 0.45 * lowpass(pr, 1500, 2), t0 + din + 0.1, wrap=True)
        _deep_bubbles(y, rng, t0 + din + 0.3, 4, 0.3, 400, 1400, 0.12, wrap=True)
    # le zampette che si muovono nel sonno sul bottino
    for tl in (2.3, 7.1):
        tt = tl
        for j in range(int(rng.integers(4, 8))):
            if rng.random() < 0.5:
                k_ = knock(rng, force=rng.uniform(0.0003, 0.0006), base=rng.uniform(600, 1000), t60=0.03, count=6,
                           bright=1.3, dur=0.06)
            else:
                m = ns(0.12)
                exc = np.zeros(m)
                exc[:2] = [1.0, -0.6]
                f0 = rng.uniform(1700, 2600)
                k_ = normalize(modal(exc, [f0, f0 * 1.47, f0 * 2.31], [0.03, 0.02, 0.012], [1, 0.6, 0.35]))
            place(y, 0.12 * k_ * rng.uniform(0.5, 1.0), tt, wrap=True)
            tt += rng.uniform(0.05, 0.14)
        tk = crinkle(rng, 0.6, [(0, 0), (0.2, 1), (0.6, 0)], density=200.0, f_lo=900.0, f_hi=4500.0, res=2200.0,
                     swish=0.5)
        place(y, 0.05 * lowpass(tk, 3200, 2), tl + 0.1, wrap=True)
    # l'ombra della risatina, dal naso, nel sonno
    ds = 0.55
    on = [0.03, 0.17, 0.31]
    env = pulses(ns(ds), on, [0.08, 0.08, 0.1], att=0.01, rel=0.04, levels=[0.8, 0.7, 0.5])
    sk = vox(rng, ds, [(0, 420), (ds, 350)], [(0, 'm'), (ds, 'n')], scale=1.35, amp_pts=env, oq=0.62, jitter=0.03,
             shimmer=0.15, breath=0.8, breath_base=0.6, bw=1.7, wander=25.0, hnoise=env * 0.8)
    place(y, 0.12 * normalize(lowpass(sk, 2500, 2)), 4.6, wrap=True)
    return _den_loop(y, rng, wet=0.3, lp=4500.0)


register('sleep_robin', _sleep_robin, 10.2, loop=True, category='mon', gain=0.7, rms=-25.0)


def _sleep_archie(s, rng):
    """Archie avvolto come un serpente attorno al tavolo della festa: due respiri lunghi. Dentro, un soffio fra i
    denti e la carta della trombetta che si riavvolge; fuori, la trombetta che si srotola un poco: un filo di
    fiato nell'ancia (un ronzio nasale debole che s'inceppa e cala), la carta fradicia che si stende, la piuma
    che ondeggia, le bolle che escono dalla punta; sotto, il corpo lungo che stringe e scivola sul tavolo."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    cyc = d / 2
    for k in range(2):
        t0 = k * cyc
        din = 1.9
        hs = tract_noise(rng, din, [(0, 'i'), (din, 'e')], scale=0.9, amp_pts=[(0, 0), (din * 0.7, 1), (din, 0)],
                         hiss=0.6)
        place(y, 0.25 * normalize(lowpass(highpass(hs, 500, 2), 3500, 2)), t0, wrap=True)
        place(y, 0.18 * _wet_paper(rng, din * 0.8, [(0, 0), (0.3, 1), (din * 0.8, 0)], density=160), t0 + 0.3,
              wrap=True)
        # fuori: la trombetta che si srotola un poco
        dr = 1.4 + 0.3 * k
        rd = _reed_sleep(rng, dr, [(0, 200), (dr * 0.3, 215), (dr, 150)],
                         [(0, 0), (0.15, 1), (dr * 0.6, 0.6), (dr, 0)], stall=0.65)
        place(y, 0.3 * normalize(lowpass(rd, 1600, 2)), t0 + din + 0.25, wrap=True)
        place(y, 0.25 * _wet_paper(rng, dr, [(0, 0), (0.2, 1), (dr * 0.5, 0.6), (dr, 0)], density=320),
              t0 + din + 0.3, wrap=True)
        _deep_bubbles(y, rng, t0 + din + 0.5, 8, 0.35, 320, 1100, 0.1, wrap=True)
        # il corpo che stringe e scivola sul legno del tavolo
        sl = squish(rng, 0.5, 200, 1200, density=300, sticky=0.3)
        place(y, 0.1 * sl, t0 + din + dr + 0.4, wrap=True)
    cr = creak(rng, 1.0, [(0, 7), (0.5, 12), (1.0, 6)], [(0, 0), (0.3, 1), (1.0, 0)], base=170, t60=0.1, bright=0.5)
    place(y, 0.08 * lowpass(cr, 1500, 2), 9.5, wrap=True)
    return _den_loop(y, rng, wet=0.3, lp=4500.0)


register('sleep_archie', _sleep_archie, 12.6, loop=True, category='mon', gain=0.7, rms=-24.5)


def _sleep_lampy(s, rng):
    """Lampy attaccata con la ventosa al soffitto sopra la culla, a occhi aperti: tre respiri piccoli e veloci da
    neonata, e a ogni respiro la ventosa che si riassesta sulla roccia (un risucchio umido); dalle sette fessure
    delle branchie esce una fila di bollicine; sotto, la giostrina di pesciolini della culla che la corrente fa
    girare e ticchettare piano."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    cyc = d / 3
    for k in range(3):
        t0 = k * cyc
        din, dex = 0.7, 0.9
        inh = tract_noise(rng, din, [(0, 'u'), (din, 'ae')], scale=BABY, amp_pts=[(0, 0), (din * 0.7, 1), (din, 0)],
                          hiss=0.3)
        place(y, 0.3 * normalize(lowpass(inh, 3500, 2)), t0, wrap=True)
        ex = tract_noise(rng, dex, [(0, 'ae'), (dex, '@')], scale=BABY, amp_pts=[(0, 0), (0.1, 1), (dex, 0)], hiss=0.2)
        place(y, 0.28 * normalize(lowpass(ex, 3000, 2)), t0 + din + 0.1, wrap=True)
        # la ventosa che si riassesta
        place(y, 0.14 * squish(rng, 0.16, 400, 2000, density=900, sticky=0.8), t0 + din * 0.9, wrap=True)
        # la fila di bollicine dalle sette fessure
        tb = t0 + din + 0.3
        for j in range(7):
            place(y, bubble(float(loguniform(rng, 900, 1700)), xi=rng.uniform(0.0, 0.05), amp=0.08 * rng.uniform(0.6, 1),
                            decay_mult=0.8, max_dur=0.1), tb + j * rng.uniform(0.04, 0.07), wrap=True)
    # la giostrina che gira e ticchetta (plastica, ovattata)
    for tm in (1.8, 4.9, 7.6):
        for r in range(2):
            m = ns(0.06)
            exc = np.zeros(m)
            exc[:2] = [1.0, -0.5]
            f0 = rng.uniform(1300, 1900)
            tk = normalize(modal(exc, [f0, f0 * 1.6, f0 * 2.7], [0.02, 0.012, 0.008], [1, 0.5, 0.3]))
            place(y, 0.05 * tk, tm + r * rng.uniform(0.25, 0.4), wrap=True)
    return _den_loop(y, rng, wet=0.35, lp=4500.0)


register('sleep_lampy', _sleep_lampy, 9.0, loop=True, category='mon', gain=0.7, rms=-26.0)


def _shells(y, rng, t0, count, a=1.0, wrap=True):
    """Le conchiglie appese attorno al letto di Fangy che si toccano: tintinnii radi e fini, a grappoli."""
    t = t0
    for _ in range(count):
        f = float(loguniform(rng, 1800, 4200))
        place(y, _clink(rng, f, a * rng.uniform(0.4, 1.0), t60=rng.uniform(0.05, 0.12)), t, wrap=wrap)
        t += rng.exponential(0.12) + 0.03


def _sleep_fangy(s, rng):
    """Fangy raggomitolato con gli occhialini neri: due respiri lentissimi del mastino (dentro un fiato lungo e
    grave dal muso, fuori un soffio fra le zanne che gorgoglia e lascia salire le bolle); l'acqua che si muove col
    suo respiro fa toccare le conchiglie appese attorno al letto, che tintinnano piano; le lucine del ventre quasi
    spente che respirano lentissime (un ronzio freddo appena percettibile)."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    cyc = d / 2
    t_ = tvec(n)
    for k in range(2):
        t0 = k * cyc
        din = 2.4
        nz = rng.standard_normal(ns(din))
        body = (0.6 * resonate(nz, 420 * 0.85, 2.0) + 0.5 * resonate(nz, 980 * 0.85, 2.6) + 0.3 * resonate(nz, 2000, 3.0))
        rumble = lowpass(nz, 140, 2)
        inh = normalize(lowpass(body, 2600, 2)) + 0.6 * normalize(rumble)
        inh = inh * curve(ns(din), [(0, 0), (din * 0.5, 0.6), (din * 0.88, 1.0), (din, 0)])
        place(y, 0.45 * normalize(inh), t0, wrap=True)
        dex = 2.8
        ex = tract_noise(rng, dex, [(0, 'a'), (dex, 'u')], scale=MASTIFF, amp_pts=[(0, 0), (0.2, 1), (dex * 0.6, 0.5),
                                                                                   (dex, 0)], hiss=0.12)
        ex = wet_throat(normalize(lowpass(ex, 2200, 2)), rng, rate=14.0, depth=0.45, bubbles=0.4, flange=0.3,
                        f_lo=120, f_hi=420)
        place(y, 0.42 * normalize(ex), t0 + din + 0.3, wrap=True)
        _deep_bubbles(y, rng, t0 + din + 0.6, 7, 0.45, 180, 800, 0.14, wrap=True)
        # le conchiglie: l'acqua mossa dal respiro le fa toccare
        _shells(y, rng, t0 + din + 1.1, int(rng.integers(4, 7)), a=0.3)
    # le lucine quasi spente: un ronzio freddo e fioco che respira lentissimo (cicli interi nel loop)
    glow = 0.5 + 0.5 * np.sin(TWO_PI * 2 * t_ / d - 1.2)
    f1 = 2350.0 * np.ones(n)
    hum = np.sin(TWO_PI * phase_of(periodic_freq(f1 * cents(6 * rand_curve(n, 0.5, rng)))))
    y += 0.006 * hum * glow ** 2
    return _den_loop(y, rng, wet=0.3, lp=5500.0)


register('sleep_fangy', _sleep_fangy, 14.0, loop=True, category='mon', gain=0.7, rms=-25.0)


def _madre_breath(s, rng):
    """Dal fondo della grotta grande, l'apertura enorme e buia: qualcosa di gigantesco respira (la Madre). Un solo
    respiro in 24 s: dentro, l'acqua della grotta che viene risucchiata verso il buio (una corrente grave che tira,
    i sassolini che rotolano verso l'apertura, la sabbia che scorre); fuori, l'acqua che torna indietro con una
    spinta lenta, bolle enormi e gravissime che salgono dal buio, e dentro, quasi sotto la soglia, il lamento della
    voce più grande che ci sia."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    t_ = tvec(n)
    din, tex, dex = 9.0, 10.5, 9.5
    pull = curve(n, [(0, 0), (din * 0.6, 0.8), (din, 1.0), (din + 0.8, 0.0), (tex, 0.0), (d, 0.0)])
    push = curve(n, [(0, 0), (tex, 0), (tex + 1.5, 1.0), (tex + dex * 0.6, 0.6), (tex + dex, 0.0), (d, 0)])
    base = spectral_noise(n, rng, lambda f: bw_bp(f, 18, 220, 2), exponent=1.3)
    y += 0.5 * base * (0.15 + pull) + 0.5 * np.roll(base, ns(3.0)) * push
    # la sabbia che scorre verso il buio
    sand = spectral_noise(n, rng, lambda f: bw_bp(f, 1200, 5000, 2), exponent=0.5) * np.clip(rand_curve(n, 3.0, rng) + 0.6, 0, None)
    y += 0.025 * sand * pull ** 2
    for tp in poisson_times(rng, 0.5, 2.0, din):
        place(y, _pebbles(rng, a=0.35 * float(np.interp(tp, t_, pull))), tp, wrap=True)
    # le bolle enormi e gravissime che salgono dal buio
    for tb in poisson_times(rng, 1.4, tex + 0.8, tex + dex - 1.0):
        f = float(loguniform(rng, 45, 110))
        place(y, bubble(f, xi=0.0, amp=0.5 * rng.uniform(0.5, 1.0), decay_mult=0.3, max_dur=0.8), tb, wrap=True)
        _deep_bubbles(y, rng, tb + 0.05, 4, 0.1, 300, 1000, 0.05, wrap=True)
    # il lamento, quasi sotto la soglia
    dm = 6.5
    mo = whale_moan(rng, dm, [(0, 34), (2.5, 41), (dm, 30)], [(0, 'u'), (3.0, 'o'), (dm, 'u')], scale=0.4,
                    amp_pts=[(0, 0), (2.0, 1), (4.5, 0.7), (dm, 0)], sub=0.3)
    place(y, 0.25 * lowpass(mo, 400, 2), tex + 1.6, wrap=True)
    y = circular(lambda x: lowpass(highpass(x, 18, 2), 3000, 2), y)
    return y + 0.4 * convolve(y, _cave_ir(rng, 3.5, stereo_out=False), circular=True)


register('madre_breath', _madre_breath, 24.0, loop=True, category='mon', gain=0.8, rms=-24.0)


# ═════════════════════════ si muovono nel sonno ═════════════════════════
# Mono, una volta ogni tanto (il gioco li suona sopra il respiro). Sembrano svegliarsi, ma non succede niente.

def _stir_gulpy(s, rng):
    """Gulpy si gira sul materasso di salvagenti: la gomma che cigola e stride sotto il peso, la mascella molle che
    sbatte con uno schiocco d'osso sordo, uno sbuffo russato che si interrompe e una bollona dalla bocca."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    place(y, 0.8 * _body_shift(rng, 2.2, size=1.4), 0.0)
    for te in (0.35, 0.9):
        sq = rubber_squeal(rng, 0.5, rate_pts=[(0, 260), (0.25, 380), (0.5, 300)], env_pts=[(0, 0), (0.1, 1), (0.5, 0)],
                           bright=0.55)
        place(y, 0.2 * sq, te)
    place(y, 0.35 * lowpass(bone_crack(rng, size=1.2, dur=0.25, bright=0.4), 1500, 2), 1.25)
    dsn = 0.7
    sn = vox(rng, dsn, [(0, 34), (dsn, 40)], [(0, 'O'), (dsn, 'a')], scale=GIANT,
             amp_pts=[(0, 0), (0.2, 1), (0.6, 0.9), (dsn, 0)], oq=0.35, jitter=0.12, shimmer=0.35, sub=0.6, breath=0.9,
             rough=0.7, rough_rate=18.0)
    place(y, 0.6 * normalize(lowpass(wet_throat(sn, rng, rate=24, depth=0.5, bubbles=0.3), 1600, 2)), 1.45)
    place(y, bubble(95.0, xi=0.02, amp=0.6, decay_mult=0.4, max_dur=0.5), 2.2)
    _deep_bubbles(y, rng, 2.22, 5, 0.08, 500, 1600, 0.05)
    return _den_shot(y, rng)


register('stir_gulpy', _stir_gulpy, 3.0, category='mon', gain=0.8, rms=-20.0)


def _stir_molly(s, rng):
    """Molly stringe i braccioli nel sonno: la plastica gonfia che stride e si piega, il corpo che si rannicchia,
    un piagnucolio piccolo a bocca chiusa (con l'altra gola sotto) che si spegne in un sospiro con le bollicine."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    place(y, 0.5 * _body_shift(rng, 1.6, size=0.6), 0.0)
    sq = rubber_squeal(rng, 0.45, rate_pts=[(0, 480), (0.2, 720), (0.45, 520)], env_pts=[(0, 0), (0.05, 1), (0.45, 0)],
                       bright=1.2)
    place(y, 0.25 * sq, 0.2)
    dw = 1.3
    f0 = [(0, 420), (0.4, 470), (0.9, 380), (dw, 330)]
    wh = vox(rng, dw, f0, [(0, 'm'), (0.6, 'u'), (dw, 'm')], scale=CHILD, amp_pts=[(0, 0), (0.15, 1), (0.9, 0.6), (dw, 0)],
             oq=0.58, jitter=0.03, shimmer=0.16, breath=0.6, breath_base=0.5, bw=1.6, wander=25.0, vib=(40.0, 6.0))
    gh = vox(rng, dw, [(t, f * 0.47) for t, f in f0], [(0, 'm'), (dw, 'u')], scale=0.95,
             amp_pts=[(0, 0), (0.3, 1), (dw, 0)], oq=0.5, sub=0.4, breath=0.3, wander=20.0)
    v = wet(normalize(wh) + 0.3 * normalize(gh), rng, rate=22.0, depth=0.35, bubbles=0.25, flange=0.4, f_lo=500,
            f_hi=1500)
    place(y, 0.5 * normalize(lowpass(v, 2800, 2)), 0.65)
    sg = tract_noise(rng, 0.8, [(0, '@'), (0.8, 'u')], scale=CHILD, amp_pts=[(0, 0), (0.1, 1), (0.8, 0)], hiss=0.2)
    place(y, 0.25 * normalize(lowpass(sg, 3000, 2)), 2.0)
    _deep_bubbles(y, rng, 2.15, 4, 0.2, 500, 1500, 0.15)
    return _den_shot(y, rng, wet=0.35)


register('stir_molly', _stir_molly, 3.0, category='mon', gain=0.8, rms=-21.0)


def _stir_hatch(s, rng):
    """Hatch si muove nell'armadio: le ante che sbattono piano e il legno che geme, l'esca che si accende di colpo
    (lo scatto del contatto, la bobina che fischia) e il chip che prova una nota sola, rallentata e calante, poi si
    spegne; un'annusata lunga, e torna giù."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    place(y, 0.5 * _body_shift(rng, 2.0, size=1.0), 0.0)
    place(y, 0.3 * lowpass(knock(rng, force=0.002, base=140, t60=0.12, count=8, bright=0.6, dur=0.5), 1500, 2), 0.3)
    cr = creak(rng, 0.8, [(0, 10), (0.4, 18), (0.8, 8)], [(0, 0), (0.2, 1), (0.8, 0)], base=150, t60=0.12, bright=0.5)
    place(y, 0.25 * lowpass(cr, 1600, 2), 0.45)
    # l'esca che si accende
    exc = np.zeros(ns(0.02))
    exc[:2] = [1.0, -0.6]
    place(y, 0.2 * normalize(modal(exc, [2100, 3700], [0.006, 0.004], [1, 0.5])), 1.0)
    m = ns(1.2)
    place(y, 0.05 * _coil(rng, m) * curve(m, [(0, 0), (0.05, 1), (0.9, 0.8), (1.2, 0)]), 1.0)
    m = ns(0.5)
    fr = 659.0 * curve(m, [(0, 1.0), (0.5, 0.9)], 'log')
    sqw = np.sign(np.sin(TWO_PI * phase_of(fr))) * curve(m, [(0, 0), (0.005, 1), (0.4, 0.8), (0.5, 0)])
    sqw = bandpass(softclip(bandpass(sqw, 500, 4500, 2), 2.5), 600, 3000, 2)
    place(y, 0.06 * sqw, 1.15)
    dsn = 0.9
    nz = rng.standard_normal(ns(dsn))
    sn = (0.6 * resonate(nz, 1250, 2.5) + 0.5 * resonate(nz, 2300, 3.0) + 0.3 * resonate(nz, 3600, 3.0))
    sn = normalize(lowpass(sn, 3800, 2)) * curve(ns(dsn), [(0, 0), (dsn * 0.7, 1), (dsn, 0)])
    place(y, 0.3 * sn, 1.9)
    return _den_shot(y, rng)


register('stir_hatch', _stir_hatch, 3.0, category='mon', gain=0.8, rms=-21.0)


def _stir_robin(s, rng):
    """Robin si sistema sul bottino: il mucchio che frana un poco sotto di lui (scarpe di gomma che rotolano, un
    giocattolo di latta, i biglietti), le zampette che raspano, un gracidio corto e assonnato del tamburo."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    place(y, 0.4 * _body_shift(rng, 1.8, size=0.7), 0.0)
    tt = 0.2
    for j in range(int(rng.integers(8, 13))):
        if rng.random() < 0.5:
            k_ = lowpass(knock(rng, force=rng.uniform(0.001, 0.002), base=rng.uniform(180, 320), t60=0.05, count=6,
                               bright=0.6, dur=0.2), 1800, 2)
        else:
            m = ns(0.15)
            exc = np.zeros(m)
            exc[:2] = [1.0, -0.6]
            f0 = rng.uniform(1500, 2600)
            k_ = normalize(modal(exc, [f0, f0 * 1.47, f0 * 2.31], [0.04, 0.025, 0.015], [1, 0.6, 0.35]))
        place(y, 0.25 * k_ * rng.uniform(0.5, 1.0) * (0.9 ** j), tt)
        tt += rng.exponential(0.09) + 0.03
    tk = crinkle(rng, 0.9, [(0, 0), (0.2, 1), (0.9, 0)], density=220.0, f_lo=900.0, f_hi=4500.0, res=2200.0, swish=0.5)
    place(y, 0.12 * lowpass(tk, 3200, 2), 0.4)
    dr = 0.6
    pr = _drum_purr(rng, dr, [(0, 30), (dr, 20)], [(0, 0), (0.05, 1), (dr, 0)])
    place(y, 0.5 * lowpass(pr, 1600, 2), 1.7)
    _deep_bubbles(y, rng, 1.9, 4, 0.2, 400, 1400, 0.1)
    return _den_shot(y, rng)


register('stir_robin', _stir_robin, 2.8, category='mon', gain=0.8, rms=-21.0)


def _stir_archie(s, rng):
    """Archie stringe le spire attorno al tavolo della festa: la pelle che scivola sul legno, il tavolo che
    scricchiola, un palloncino che strofina; la trombetta che si srotola di scatto nel sonno con un «prrt» corto e
    sfiatato, le bolle che escono dalla punta, la carta che si riavvolge piano."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    place(y, 0.45 * _body_shift(rng, 2.0, size=0.8), 0.0)
    place(y, 0.25 * squish(rng, 0.6, 200, 1200, density=400, sticky=0.3), 0.15)
    cr = creak(rng, 0.9, [(0, 8), (0.4, 15), (0.9, 7)], [(0, 0), (0.25, 1), (0.9, 0)], base=170, t60=0.1, bright=0.5)
    place(y, 0.3 * lowpass(cr, 1600, 2), 0.35)
    sq = rubber_squeal(rng, 0.35, rate_pts=[(0, 600), (0.35, 760)], env_pts=[(0, 0), (0.05, 1), (0.35, 0)], bright=1.1)
    place(y, 0.08 * sq, 0.9)
    dr = 0.55
    rd = _reed_sleep(rng, dr, [(0, 240), (0.15, 260), (dr, 190)], [(0, 0), (0.03, 1), (0.35, 0.7), (dr, 0)], stall=0.5)
    place(y, 0.45 * normalize(lowpass(rd, 2000, 2)), 1.3)
    place(y, 0.3 * _wet_paper(rng, 0.5, [(0, 0), (0.05, 1), (0.5, 0)], density=500), 1.3)
    _deep_bubbles(y, rng, 1.4, 10, 0.2, 320, 1200, 0.12)
    place(y, 0.18 * _wet_paper(rng, 0.9, [(0, 0), (0.3, 1), (0.9, 0)], density=180), 1.95)
    return _den_shot(y, rng)


register('stir_archie', _stir_archie, 3.0, category='mon', gain=0.8, rms=-21.0)


def _stir_lampy(s, rng):
    """Lampy si stacca un attimo dal soffitto: lo schiocco della ventosa che molla da un lato, il corpo che ondeggia
    nell'acqua sopra la culla, la ventosa che si riattacca con un bacio risucchiato; un versetto da neonata nel
    sonno, ovattato, con le bollicine; la giostrina che gira un giro."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    m = ns(0.012)
    pop = bandpass(rng.standard_normal(m), 500, 3500, 2) * exp_env(m, 0.006, attack=0.0003)
    place(y, 0.4 * normalize(pop), 0.0)
    place(y, 0.3 * bubble(420.0, xi=0.05, amp=1.0, decay_mult=1.4, max_dur=0.08), 0.002)
    place(y, 0.4 * _body_shift(rng, 1.6, size=0.5), 0.05)
    place(y, 0.35 * squish(rng, 0.2, 500, 2500, density=1200, sticky=0.8), 1.25)
    dc = 0.7
    env = pulses(ns(dc), [0.02, 0.22], [0.15, 0.3], att=0.02, rel=0.06, levels=[0.7, 1.0])
    co = vox(rng, dc, [(0, 520), (0.3, 580), (dc, 450)], [(0, 'u'), (0.3, 'ae'), (dc, '@')], scale=BABY, amp_pts=env,
             oq=0.6, jitter=0.03, shimmer=0.16, breath=0.6, breath_base=0.5, bw=1.6, wander=30.0)
    co = wet(normalize(co), rng, rate=26.0, depth=0.4, bubbles=0.35, flange=0.5, f_lo=500, f_hi=1600)
    place(y, 0.35 * normalize(lowpass(co, 1300, 2)), 1.55)
    for j in range(7):
        place(y, bubble(float(loguniform(rng, 900, 1700)), xi=rng.uniform(0.0, 0.05), amp=0.08, decay_mult=0.8,
                        max_dur=0.1), 1.7 + j * 0.06)
    for r in range(4):
        exc = np.zeros(ns(0.06))
        exc[:2] = [1.0, -0.5]
        f0 = rng.uniform(1300, 1900)
        place(y, 0.06 * normalize(modal(exc, [f0, f0 * 1.6, f0 * 2.7], [0.02, 0.012, 0.008], [1, 0.5, 0.3])),
              0.5 + r * 0.3)
    return _den_shot(y, rng, wet=0.35)


register('stir_lampy', _stir_lampy, 2.8, category='mon', gain=0.8, rms=-21.0)


def _stir_fangy(s, rng):
    """Fangy alza il testone nel sonno, come se avesse sentito qualcosa: il collo grosso che si torce nell'acqua, le
    conchiglie che tintinnano tutte insieme, un'annusata secca dalle fossette, le zanne che si toccano; poi un fiato
    lungo che gorgoglia, e la testa che si riposa."""
    n, d = s.n, s.dur
    y = np.zeros(n)
    place(y, 0.55 * _body_shift(rng, 2.0, size=1.2), 0.0)
    _shells(y, rng, 0.35, 12, a=0.3, wrap=False)
    place(y, 0.45 * lowpass(big_sniff(rng, dur=0.3, f=0.7, wet_amt=0.6), 3800, 2), 0.7)
    place(y, 0.15 * teeth_clack(rng, count=4, spread=0.004, glass=0.15, dur=0.08), 1.05)
    dex = 1.4
    ex = tract_noise(rng, dex, [(0, 'a'), (dex, 'u')], scale=MASTIFF, amp_pts=[(0, 0), (0.15, 1), (dex, 0)], hiss=0.12)
    ex = wet_throat(normalize(lowpass(ex, 2200, 2)), rng, rate=14.0, depth=0.45, bubbles=0.4, flange=0.3,
                    f_lo=120, f_hi=420)
    place(y, 0.4 * normalize(ex), 1.4)
    _deep_bubbles(y, rng, 1.7, 6, 0.3, 180, 800, 0.14)
    _shells(y, rng, 2.0, 4, a=0.12, wrap=False)
    return _den_shot(y, rng, lp=5500.0)


register('stir_fangy', _stir_fangy, 3.2, category='mon', gain=0.8, rms=-21.0)
