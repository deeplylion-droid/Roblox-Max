"""
Mondo e orologio: campana del campanile, scampanio dell'alba, sirena da nebbia lontana,
scricchiolii della barca, schizzi, tonfi e colpi sotto lo scafo.
"""
from __future__ import annotations

from scipy.signal import fftconvolve

from instruments import *  # noqa: F401,F403
from sounds import register, sound


def bay_ir(rng, rt60=2.8, far=1.0):
    """Riverbero della baia: coda rada (spazio aperto sull'acqua) + eco dai faraglioni e dal paese."""
    return reverb_ir(rt60, rng, lo=1.3, hi=0.4, attack=0.02, sparse=0.6, lp=4500,
                     early=[(0.42 * far, 0.35, 0.55), (0.86 * far, 0.22, -0.6), (1.31 * far, 0.12, 0.3)])


# ───────────────────────── campane ─────────────────────────

@sound('bell_toll', 8.0, channels=2, category='sfx', gain=0.8, rms=-20.0)
def bell_toll(s, rng):
    """Un rintocco del campanile del paese, dall'altra parte della baia. Campana grave di bronzo (Sol3):
    il colpo metallico del battaglio, poi le parziali che si spengono ognuna col suo tempo e l'hum che resta
    per ultimo. La distanza (circa un chilometro e mezzo) si mangia gli acuti; arrivano il riverbero del
    paese e l'eco dai faraglioni; la turbolenza dell'aria fa ondeggiare appena il livello."""
    n = s.n
    prime = 196.0
    b = church_bell(rng, prime, dur=s.dur, t60=12.0, bright=0.8, beat=0.7, strike=0.4)
    # il colpo del battaglio: un grappolo di parziali alte e un rumore metallico che muoiono subito
    k = ns(0.14)
    tt = tvec(k)
    clang = 0.7 * bandpass(rng.standard_normal(k), 1100, 7000) * np.exp(-tt / 0.005)
    for _ in range(10):
        f = prime * rng.uniform(5.5, 15.0)
        clang += rng.uniform(0.3, 1.0) * np.sin(TWO_PI * f * tt + rng.uniform(0, TWO_PI)) * \
            np.exp(-6.9 * tt / rng.uniform(0.025, 0.11))
    place(b, 0.3 * normalize(clang) * np.max(np.abs(b[:ns(0.5)])), 0.0)
    # la distanza: aria, tetti e alberi tolgono gli acuti; un filo di riflesso sull'acqua (pettine leggero)
    b = eq(lowpass(highpass(b, 70, 2), 2300, 2), 'highshelf', 1200, gain_db=-5.0)
    d = ns(0.0023)
    b = b + 0.3 * np.concatenate([np.zeros(d), b[:-d]])
    # turbolenza: ±2 dB lenti
    b = b * db_to_lin(1.8 * rand_curve(n, 0.6, rng))
    return 0.65 * pan(b, -0.12) + 0.7 * convolve(b, bay_ir(rng, rt60=3.2, far=1.1))


def _swing_strikes(rng, period, t_start, t_stop, ramp=1.3, fall=0.7):
    """Colpi del battaglio di una campana suonata a distesa: due per oscillazione (un lato e l'altro).
    All'inizio la campana prende slancio (colpi più deboli e un po' più radi), alla fine la si lascia andare."""
    hits = []
    t = t_start
    side = 0
    while t < t_stop:
        u = (t - t_start) / ramp
        v = (t_stop - t) / fall
        a = min(1.0, 0.35 + 0.65 * u) * min(1.0, 0.25 + 0.75 * v)
        hits.append((t, a * (1.0 if side == 0 else 0.82) * rng.uniform(0.9, 1.08), side))
        stretch = 1.0 + 0.25 * max(0.0, 1.0 - u)
        t += period / 2 * stretch * (1 + rng.normal(0, 0.025))
        side ^= 1
    return hits


@sound('bell_dawn', 9.0, channels=2, category='sfx', gain=0.8, rms=-19.0)
def bell_dawn(s, rng):
    """Le sei: il campanile suona a festa. Cinque campane a distesa (Do maggiore) che prendono slancio una
    dopo l'altra e si inseguono, la grande più lenta; ogni campana ha due "voci" (il battaglio colpisce
    un lato e poi l'altro); verso i 6,5 s le lasciano andare e resta la coda nella baia."""
    n = s.n
    out = np.zeros((2, n))
    bells = [  # prime (Hz), livello, posizione, periodo di oscillazione (s), attacco (s)
        (659.26, 0.38, -0.5, 0.92, 0.0),
        (523.25, 0.45, 0.3, 1.06, 0.35),
        (392.00, 0.55, -0.15, 1.28, 0.7),
        (329.63, 0.62, 0.55, 1.46, 1.0),
        (261.63, 0.8, -0.3, 1.78, 1.25),
    ]
    for prime, lvl, p, period, t0 in bells:
        T = 7.0 * (261.63 / prime) ** 0.5
        voices = [church_bell(rng, prime, dur=5.0, t60=T, bright=0.95, beat=1.1, strike=0.8),
                  church_bell(rng, prime * 1.0015, dur=5.0, t60=T, bright=0.8, beat=1.3, strike=0.6)]
        imp = [np.zeros(n), np.zeros(n)]
        for t, a, side in _swing_strikes(rng, period, t0 + rng.uniform(0, 0.15), 6.5 + rng.uniform(-0.2, 0.2)):
            imp[side][ns(t)] += a
        y = fftconvolve(imp[0], voices[0])[:n] + fftconvolve(imp[1], voices[1])[:n]
        out += pan(y, p) * lvl
    out = eq(lowpass(highpass(out, 100, 2), 4200, 2), 'highshelf', 1800, gain_db=-3.0)
    out = out * db_to_lin(1.2 * rand_curve(n, 0.5, rng))
    return out + 0.5 * convolve(out.mean(axis=0), bay_ir(rng, 2.6))


# ───────────────────────── sirena da nebbia ─────────────────────────

def _diaphone(rng, d, f, grunt=False, f_grunt=None):
    """Un fiato di diafono: la pressione che sale (il tono si alza e si pulisce), il tono pieno e ruvido
    del pistone a fessure, poi la fine; con grunt=True il "grugnito": il tono crolla e il pistone sbatacchia."""
    m = ns(d + (0.55 if grunt else 0.0))
    pts = [(0, f * 0.82), (0.16, f * 0.99), (0.3, f), (d - 0.05, f * 0.995)]
    if grunt:
        pts += [(d + 0.12, (f_grunt or f * 0.62) * 1.05), (d + 0.55, (f_grunt or f * 0.62) * 0.9)]
    else:
        pts += [(d, f * 0.97)]
    f0 = curve(m, pts, 'log') * cents(3 * rand_curve(m, 4.0, rng))
    # il pistone: onda ricca, quasi a dente di sega, con un po' di ruvidità
    src = additive(f0, lambda k: 1.0 / k ** 0.85, n_harm=36)
    src = src * (1 + 0.06 * rand_curve(m, 60.0, rng))
    if grunt:
        rat = 1 + 0.55 * np.sin(TWO_PI * phase_of(curve(m, [(0, 22.0), (m / SR, 16.0)]))) * \
            curve(m, [(0, 0), (d, 0), (d + 0.08, 1), (d + 0.55, 0.6)])
        src = src * rat
    # la tromba: risonanze larghe
    horn = resonate(src, 360, 2.2) + 0.85 * resonate(src, 720, 2.8) + 0.5 * resonate(src, 1180, 3.5) + 0.25 * src
    env = curve(m, [(0, 0.12), (0.05, 0.35), (0.22, 1.0), (d - 0.15, 0.97)] +
                ([(d + 0.1, 0.8), (d + 0.55, 0.0)] if grunt else [(d, 0.0)]))
    return normalize(horn) * env


@sound('foghorn', 7.0, channels=2, category='sfx', gain=0.6, rms=-22.0)
def foghorn(s, rng):
    """Una sirena da nebbia lontanissima, dal faro: diafono a due toni (alto, poi basso) che finisce col suo
    "grugnito", il tono che crolla mentre l'aria finisce. Arriva da lontano: niente acuti, il livello che
    ondeggia nell'aria umida, il riverbero della baia e due echi dalla costa."""
    n = s.n
    y = np.zeros(n)
    place(y, _diaphone(rng, 1.6, 172.0), 0.0)
    place(y, _diaphone(rng, 1.9, 129.0, grunt=True, f_grunt=84.0), 1.75)
    y = lowpass(y, 650, 2) * db_to_lin(2.5 * rand_curve(n, 1.0, rng))
    ir = reverb_ir(3.8, rng, lo=1.3, hi=0.35, attack=0.03, sparse=0.5, lp=2200,
                   early=[(0.6, 0.38, 0.6), (1.15, 0.24, -0.5), (1.8, 0.12, 0.2)])
    return 0.5 * pan(y, 0.35) + 0.9 * convolve(y, ir)


# ───────────────────────── scricchiolii ─────────────────────────

def boat_creak(rng, dur, rate_pts, env_pts, base=180.0, t60=0.1, bright=1.0, jitter=0.08, burst=0.5, wander=0.12,
               hull=0.35, rub=0.12):
    """Scricchiolio del legno della barca: l'attrito che si attacca e si stacca (stick-slip) con frequenza
    che vaga e a strappi (il legno 'prende' e 'molla' a raffiche), le tavole che risuonano, un po' di
    scafo sotto (modi gravi e lunghi) e il fruscio delle fibre che sfregano."""
    n = ns(dur)
    rate = curve(n, rate_pts, 'log') * (1.0 + wander * np.tanh(rand_curve(n, 2.5, rng))) * \
        (1.0 + 0.35 * wander * rand_curve(n, 11.0, rng))
    amp = curve(n, env_pts)
    if burst:
        amp = amp * (1.0 - burst + burst * np.abs(np.tanh(2.0 * rand_curve(n, 9.0, rng))))
    exc = stick_slip(n, rng, rate, amp, jitter)
    f, T, g = wood_modes(rng, base, 10, t60, bright)
    y = normalize(modal(exc, f, T, g))
    if hull:
        hf, hT, hg = HULL_MODES
        y += hull * normalize(modal(exc, np.array(hf) * rng.uniform(0.92, 1.08, len(hf)), np.array(hT) * 1.4, hg))
    if rub:
        y += rub * normalize(bandpass(rng.standard_normal(n), 900, 6000)) * amp
    return normalize(y)


def _creak(spec, rng):
    p = spec.params
    y = np.zeros(spec.n)
    for seg in p['segs']:
        c = boat_creak(rng, seg['dur'], seg['rate'], seg['env'], base=seg['base'], t60=seg.get('t60', 0.1),
                       bright=seg.get('bright', 1.0), jitter=seg.get('jitter', 0.08), burst=seg.get('burst', 0.5),
                       wander=seg.get('wander', 0.12), hull=seg.get('hull', 0.35), rub=seg.get('rub', 0.12))
        place(y, c * seg.get('gain', 1.0), seg.get('t0', 0.0))
    y = lowpass(y, 7000, 2)
    ir = reverb_ir(0.35, rng, lo=1.0, hi=0.5, attack=0.003, stereo_out=False, early=[(0.004, 0.4, 0.0), (0.009, 0.25, 0.0)])
    return y + 0.12 * convolve(y, ir)


CREAKS = {
    # breve e più acuto: una tavola del pagliolo sotto un piede
    'creak_1': (0.65, [dict(dur=0.62, rate=[(0, 60), (0.12, 150), (0.38, 230), (0.62, 110)],
                            env=[(0, 0.6), (0.03, 0.85), (0.3, 1), (0.5, 0.6), (0.62, 0)], base=210, t60=0.08,
                            bright=1.1, burst=0.4)]),
    # lungo gemito basso del fasciame, con un cigolio più acuto a metà
    'creak_2': (1.45, [dict(dur=1.42, rate=[(0, 14), (0.4, 30), (0.9, 44), (1.42, 18)],
                            env=[(0, 0.5), (0.1, 0.6), (0.7, 1), (1.2, 0.7), (1.42, 0)], base=112, t60=0.15,
                            bright=0.8, burst=0.55, hull=0.6),
                       dict(t0=0.45, dur=0.6, rate=[(0, 90), (0.3, 150), (0.6, 100)],
                            env=[(0, 0), (0.15, 1), (0.6, 0)], base=300, t60=0.07, bright=1.2, gain=0.35, hull=0.0)]),
    # in due tempi: "cre-eak"
    'creak_3': (1.0, [dict(dur=0.3, rate=[(0, 40), (0.3, 90)], env=[(0, 0.7), (0.05, 1), (0.25, 0.8), (0.3, 0)],
                           base=170, t60=0.1),
                      dict(t0=0.36, dur=0.6, rate=[(0, 70), (0.25, 150), (0.6, 55)],
                           env=[(0, 0), (0.06, 1), (0.4, 0.7), (0.6, 0)], base=165, t60=0.1)]),
    # lo scalmo e la cima: più tonale (meno strappi, meno jitter), più acuto, finale a scatti
    'creak_4': (1.15, [dict(dur=1.12, rate=[(0, 120), (0.3, 190), (0.8, 140), (1.12, 45)],
                            env=[(0, 0.5), (0.05, 0.7), (0.35, 1), (0.85, 0.6), (1.12, 0)], base=330, t60=0.06,
                            bright=1.4, jitter=0.035, burst=0.3, wander=0.06, hull=0.15, rub=0.06)]),
}
for _sid, (_dur, _segs) in CREAKS.items():
    register(_sid, _creak, _dur, category='sfx', gain=0.6, rms=-19.0, max_gr=6.0, params={'segs': _segs})


# ───────────────────────── acqua ─────────────────────────

def _splash_small(spec, rng):
    return splash(rng, size=spec.params['size'], dur=spec.dur)


for _sid, _dur, _size in [('splash_s1', 0.5, 0.12), ('splash_s2', 0.65, 0.2), ('splash_s3', 0.85, 0.3)]:
    register(_sid, _splash_small, _dur, category='sfx', gain=0.6, rms=-19.0, max_gr=6.0, release=0.03, params={'size': _size})


@sound('splash_big', 1.6, category='sfx', gain=0.85, rms=-16.0, max_gr=6.0, release=0.04)
def splash_big(s, rng):
    """Qualcosa di pesante che rientra in acqua: il tonfo (la cavità che collassa), il getto d'acqua che
    ricade in un secondo schizzo, la pioggia di gocce, una nuvola di bolle grosse che risale."""
    n = s.n
    y = splash(rng, size=1.0, dur=s.dur)
    nw = ns(0.55)
    whump = lowpass(rng.standard_normal(nw), 210, 2) * exp_env(nw, 0.24, attack=0.004)
    y[:nw] += 0.6 * normalize(whump)
    f = curve(nw, [(0, 86), (0.2, 46), (0.55, 40)], 'log')
    y[:nw] += 0.42 * osc(f) * exp_env(nw, 0.22, attack=0.003)
    place(y, 0.42 * splash(rng, size=0.45, dur=0.8), rng.uniform(0.3, 0.38))
    bubble_burst(y, rng, 0.06, 70, 0.18, 180, 1400, 0.05, xi=(0.0, 0.15), decay_mult=1.2)
    for t in (0.14, 0.33, 0.6):
        place(y, bubble(float(loguniform(rng, 105, 210)), xi=rng.uniform(0.04, 0.14), amp=rng.uniform(0.14, 0.24),
                        decay_mult=0.6), t + rng.uniform(-0.03, 0.03))
    return y


@sound('hull_thump', 0.75, category='sfx', gain=0.9, rms=-17.0)
def hull_thump(s, rng):
    """Qualcosa di grosso che urta lo scafo da sotto: la barca risuona come un tamburo sordo, la roba a
    bordo sobbalza, l'acqua sciaborda lungo i fianchi."""
    n = s.n
    y = knock(rng, force=0.016, base=68, t60=0.22, count=6, bright=0.6, dur=s.dur, rough=0.04,
              cavity=(92, 0.32, 0.7))
    y = lowpass(y, 600, 2)
    nt = ns(0.4)
    sub = osc(curve(nt, [(0, 62), (0.2, 44)], 'log')) * exp_env(nt, 0.26, attack=0.006)
    place(y, 0.5 * sub, 0.0)
    sl = bandpass(rng.standard_normal(n), 90, 500) * curve(n, [(0, 0), (0.05, 1), (s.dur, 0)])
    y += 0.12 * normalize(sl)
    # a bordo qualcosa sobbalza: il manico del secchio, un remo
    place(y, 0.05 * knock(rng, force=0.0005, base=900, t60=0.03, dur=0.1), 0.02)
    place(y, 0.035 * knock(rng, force=0.0008, base=420, t60=0.05, dur=0.15), 0.045)
    # l'acqua spinta via lungo i fianchi
    place(y, 0.2 * lap(rng, 0.7, dur=0.6, hull=0.2, clop_prob=0.6), 0.08)
    return y
