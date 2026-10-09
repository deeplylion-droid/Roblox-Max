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

@sound('bell_toll', 7.0, channels=2, category='sfx', gain=0.8, rms=-20.0)
def bell_toll(s, rng):
    b = church_bell(rng, prime=262.0, dur=s.dur, t60=9.0, bright=0.85, beat=1.0, strike=0.6)
    # la distanza: aria e tetti si mangiano gli acuti, il riverbero della baia prevale sul diretto
    b = eq(lowpass(highpass(b, 90, 2), 2600, 2), 'highshelf', 1500, gain_db=-4.0)
    return 0.75 * pan(b, -0.12) + 0.6 * convolve(b, bay_ir(rng))


@sound('bell_dawn', 9.0, channels=2, category='sfx', gain=0.8, rms=-19.0)
def bell_dawn(s, rng):
    n = s.n
    out = np.zeros((2, n))
    # quattro campane in Do maggiore suonate "a distesa": ognuna oscilla col suo periodo e il
    # battaglio colpisce un lato e poi l'altro (poliritmo festoso); si fermano verso i 6,5 s
    bells = [(523.25, 0.45, -0.45, 1.02), (392.0, 0.6, 0.35, 1.24), (329.63, 0.75, -0.1, 1.46),
             (261.63, 0.9, 0.55, 1.72)]
    for i, (prime, lvl, p, period) in enumerate(bells):
        ring = church_bell(rng, prime, dur=5.5, t60=7.5 * (261.63 / prime) ** 0.5, bright=0.95, beat=1.2,
                           strike=0.7)
        imp = np.zeros(n)
        t = 0.0 if i == 0 else rng.uniform(0.15, 0.6)
        side = 0
        while t < 6.4:
            imp[ns(t)] += (1.0 if side == 0 else 0.78) * rng.uniform(0.9, 1.1)
            t += period / 2 * (1 + rng.normal(0, 0.03))
            side ^= 1
        out += pan(fftconvolve(imp, ring)[:n], p) * lvl
    out = lowpass(highpass(out, 110, 2), 4500, 2)
    return out + 0.45 * convolve(out.mean(axis=0), bay_ir(rng, 2.4))


# ───────────────────────── sirena da nebbia ─────────────────────────

@sound('foghorn', 6.0, channels=2, category='sfx', gain=0.6, rms=-22.0)
def foghorn(s, rng):
    n = s.n
    y = np.zeros(n)
    # diafono a due toni (alto, poi basso) con il "grugnito" finale: il tono cala quando l'aria finisce
    for t0, d, f, fend in [(0.0, 1.75, 168.0, 148.0), (1.9, 2.1, 126.0, 104.0)]:
        m = ns(d)
        f0 = curve(m, [(0, f * 0.96), (0.1, f), (d - 0.32, f), (d, fend)], 'log') * cents(4 * rand_curve(m, 5.0, rng))
        src = additive(f0, lambda k: 1.0 / k ** 0.75, n_harm=30)
        horn = resonate(src, 390, 2.5) + 0.8 * resonate(src, 780, 3.0) + 0.5 * resonate(src, 1250, 4.0) + 0.3 * src
        env = curve(m, [(0, 0.15), (0.06, 1.0), (d - 0.35, 0.95), (d, 0)])
        place(y, normalize(horn) * env, t0)
    # lontanissima: passa-basso forte, l'aria turbolenta fa ondeggiare il livello
    y = lowpass(y, 720, 2) * (1 + 0.22 * rand_curve(n, 1.2, rng))
    ir = reverb_ir(3.6, rng, lo=1.3, hi=0.35, attack=0.03, sparse=0.5, lp=2500,
                   early=[(0.55, 0.4, 0.6), (1.1, 0.25, -0.5), (1.7, 0.12, 0.2)])
    return 0.55 * pan(y, 0.35) + 0.85 * convolve(y, ir)


# ───────────────────────── scricchiolii ─────────────────────────

def _creak(spec, rng):
    p = spec.params
    y = np.zeros(spec.n)
    for seg in p['segs']:
        t0 = seg.get('t0', 0.0)
        c = creak(rng, seg['dur'], seg['rate'], seg['env'], base=seg['base'], t60=seg.get('t60', 0.1),
                  bright=seg.get('bright', 1.0), jitter=seg.get('jitter', 0.06))
        place(y, c * seg.get('gain', 1.0), t0)
    return lowpass(y, 7000, 2)


CREAKS = {
    # breve e più acuto
    'creak_1': (0.6, [dict(dur=0.6, rate=[(0, 70), (0.15, 160), (0.4, 220), (0.6, 120)],
                           env=[(0, 0.5), (0.03, 0.8), (0.3, 1), (0.5, 0.6), (0.6, 0)], base=210, t60=0.08, bright=1.1)]),
    # lungo gemito basso del fasciame, con un cigolio più acuto a metà
    'creak_2': (1.4, [dict(dur=1.4, rate=[(0, 16), (0.4, 32), (0.9, 45), (1.4, 22)],
                           env=[(0, 0.4), (0.1, 0.6), (0.7, 1), (1.2, 0.7), (1.4, 0)], base=118, t60=0.14, bright=0.8),
                      dict(t0=0.45, dur=0.6, rate=[(0, 90), (0.3, 140), (0.6, 100)],
                           env=[(0, 0), (0.15, 1), (0.6, 0)], base=300, t60=0.07, bright=1.2, gain=0.35)]),
    # in due tempi: "cre-eak"
    'creak_3': (0.95, [dict(dur=0.3, rate=[(0, 40), (0.3, 90)], env=[(0, 0.5), (0.05, 1), (0.25, 0.8), (0.3, 0)],
                            base=170, t60=0.1),
                       dict(t0=0.36, dur=0.55, rate=[(0, 70), (0.25, 150), (0.55, 60)],
                            env=[(0, 0), (0.06, 1), (0.4, 0.7), (0.55, 0)], base=165, t60=0.1)]),
    # cima/albero: più tonale (meno jitter), più acuto, finale a scatti
    'creak_4': (1.1, [dict(dur=1.1, rate=[(0, 110), (0.3, 170), (0.8, 130), (1.1, 45)],
                           env=[(0, 0.4), (0.05, 0.7), (0.35, 1), (0.85, 0.6), (1.1, 0)], base=330, t60=0.06,
                           bright=1.4, jitter=0.03)]),
}
for _sid, (_dur, _segs) in CREAKS.items():
    register(_sid, _creak, _dur, category='sfx', gain=0.6, rms=-19.0, params={'segs': _segs})


# ───────────────────────── acqua ─────────────────────────

def _splash_small(spec, rng):
    return splash(rng, size=spec.params['size'], dur=spec.dur)


for _sid, _dur, _size in [('splash_s1', 0.45, 0.12), ('splash_s2', 0.6, 0.2), ('splash_s3', 0.8, 0.3)]:
    register(_sid, _splash_small, _dur, category='sfx', gain=0.6, rms=-19.0, params={'size': _size})


@sound('splash_big', 1.5, category='sfx', gain=0.85, rms=-16.0)
def splash_big(s, rng):
    n = s.n
    y = splash(rng, size=1.0, dur=s.dur)
    # il corpo pesante che sfonda la superficie: tonfo basso (cavità d'aria che collassa)
    nw = ns(0.6)
    whump = lowpass(rng.standard_normal(nw), 220, 2) * exp_env(nw, 0.3, attack=0.003)
    y[:nw] += 0.7 * normalize(whump)
    f = curve(nw, [(0, 78), (0.25, 42), (0.6, 38)], 'log')
    y[:nw] += 0.6 * osc(f) * exp_env(nw, 0.3, attack=0.002)
    # bolloni che risalgono
    for t in (0.09, 0.16, 0.27, 0.45, 0.62, 0.85):
        place(y, bubble(float(loguniform(rng, 110, 260)), rng.uniform(0.2, 0.5), rng.uniform(0.25, 0.5),
                        decay_mult=0.5), t + rng.uniform(-0.02, 0.02))
    return y


@sound('hull_thump', 0.6, category='sfx', gain=0.9, rms=-17.0)
def hull_thump(s, rng):
    n = s.n
    # qualcosa urta da sotto: forza lunga e morbida sui modi bassi dello scafo + l'aria della barca
    y = knock(rng, force=0.012, base=72, t60=0.18, count=6, bright=0.7, dur=s.dur, rough=0.05,
              cavity=(95, 0.3, 0.6))
    y = lowpass(y, 650, 2)
    sl = bandpass(rng.standard_normal(n), 90, 500) * curve(n, [(0, 0), (0.05, 1), (0.6, 0)])
    y += 0.18 * normalize(sl)
    place(y, 0.05 * knock(rng, force=0.0005, base=900, t60=0.03, dur=0.1), 0.018)   # qualcosa che sobbalza a bordo
    return y
