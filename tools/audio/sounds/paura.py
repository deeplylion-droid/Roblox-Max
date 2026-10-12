"""
«Più paura» (approvato dall'utente il 12 ottobre come idea; i suoni sono da approvare):
  - il cuore del pescatore: il battito (lub-dub) che il gioco ripete sempre più svelto quando c'è pericolo, e il
    respiro che si fa corto (inspiro ed espiro a parte, il gioco li alterna col suo ritmo); categoria 'body', dentro
    la testa: niente spazio e niente ovattato sotto il telone;
  - la tensione nella musica: due fondi in loop che il gioco alza con le minacce (il basso, poi l'alto) e toglie del
    tutto un attimo prima del peggio;
  - le creature vive: lo scatto della testa quando le guardi (cartilagine e carne bagnata) e le gocce che cadono
    da chi è appena uscito dall'acqua.
I colpi sullo scafo dei falsi allarmi sono quelli di Molly (molly_knock_*): devono ingannare.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

# ───────────────────────── il cuore ─────────────────────────


def _thump(rng, f0, dur, amp):
    """Un colpo del cuore: un'onda bassa che cala subito di tono, un'armonica e il tonfo sordo dei tessuti (perché si
    senta anche dalle casse di un portatile, che il 50 Hz non lo fanno)."""
    n = ns(dur)
    t = tvec(n)
    f = f0 * (1.0 + 0.55 * np.exp(-t / 0.028))
    ph = TWO_PI * np.cumsum(f) / SR
    env = (1.0 - np.exp(-t / 0.0035)) * np.exp(-t / 0.075)
    y = np.sin(ph) * env + 0.32 * np.sin(2.0 * ph + 0.4) * env + 0.12 * np.sin(3.0 * ph) * env
    nz = lowpass(rng.standard_normal(n), 170.0, 2) * exp_env(n, 0.055, attack=0.003)
    y = y + 0.45 * normalize(nz)
    return amp * y


def _heart(s, rng):
    p = s.params
    y = np.zeros(s.n)
    t0 = 0.012
    place(y, _thump(rng, p['f0'] * rng.uniform(0.97, 1.03), 0.4, 1.0), t0)
    place(y, _thump(rng, p['f0'] * 1.27 * rng.uniform(0.97, 1.03), 0.32, p['dub']), t0 + p['gap'] * rng.uniform(0.96, 1.04))
    # un filo di saturazione: le armoniche portano il colpo dove le casse piccole arrivano
    y = np.tanh(1.7 * normalize(y)) / np.tanh(1.7)
    return highpass(lowpass(y, 320.0, 2), 28.0, 2)


for _sid, _p in [
    ('cuore_1', {'f0': 50.0, 'gap': 0.30, 'dub': 0.62}),
    ('cuore_2', {'f0': 53.0, 'gap': 0.26, 'dub': 0.68}),
    # quando corre: i due colpi più vicini e il secondo più forte
    ('cuore_3', {'f0': 56.0, 'gap': 0.20, 'dub': 0.8}),
]:
    register(_sid, _heart, 0.62, category='body', gain=0.85, rms=-21.0, max_gr=3.0, release=0.03, params=_p)


# ───────────────────────── il respiro ─────────────────────────


def _shake(n, rng, rate, depth):
    """Il tremito della paura: il fiato che trema (un'oscillazione irregolare attorno ai 9 Hz)."""
    w = rand_curve(n, 3.0, rng)
    ph = TWO_PI * np.cumsum(rate * (1.0 + 0.25 * w)) / SR
    return 1.0 - depth * (0.5 + 0.5 * np.sin(ph))


def _breath_in(s, rng):
    p = s.params
    d = s.dur
    n = s.n
    a = curve(n, [(0, 0), (0.05, 0.25), (d * 0.55, 1.0), (d * 0.86, 0.85), (d, 0)])
    y = tract_noise(rng, d, ((0.0, 'O'), (d * 0.5, 'o'), (d, 'u')), scale=1.0, amp_pts=a, hiss=0.22)
    y = y * _shake(n, rng, p['shake'], p['depth'])
    # il naso, un attimo: un sibilo stretto in alto
    y += 0.08 * bandpass(rng.standard_normal(n), 2600, 5200, 2) * a
    return lowpass(highpass(y, 180.0, 2), 7500.0, 2)


def _breath_out(s, rng):
    p = s.params
    d = s.dur
    n = s.n
    a = curve(n, [(0, 0), (0.06, 1.0), (d * 0.35, 0.8), (d * 0.75, 0.35), (d, 0)])
    y = tract_noise(rng, d, ((0.0, 'a'), (d * 0.6, '@'), (d, 'E')), scale=1.0, amp_pts=a, hiss=0.12)
    y = y * _shake(n, rng, p['shake'], p['depth'])
    if p.get('voice'):
        # nell'espiro che trema c'è un filo di voce: un gemito soffocato
        v = vox(rng, d, [(0, 150), (d, 120)], ((0.0, '@'), (d, 'u')), amp_pts=[(0, 0), (0.1, 0.35), (d * 0.6, 0.2), (d, 0)], oq=0.75, sq=1.5)
        y = y + p['voice'] * normalize(v) * a
    return lowpass(highpass(y, 140.0, 2), 6500.0, 2)


for _sid, _fn, _d, _p in [
    ('fiato_dentro_1', _breath_in, 0.9, {'shake': 8.5, 'depth': 0.18}),
    ('fiato_dentro_2', _breath_in, 0.7, {'shake': 10.0, 'depth': 0.3}),
    ('fiato_dentro_3', _breath_in, 0.5, {'shake': 11.5, 'depth': 0.42}),
    ('fiato_fuori_1', _breath_out, 1.2, {'shake': 7.5, 'depth': 0.15}),
    ('fiato_fuori_2', _breath_out, 0.95, {'shake': 9.5, 'depth': 0.3, 'voice': 0.12}),
    ('fiato_fuori_3', _breath_out, 0.7, {'shake': 11.0, 'depth': 0.45, 'voice': 0.2}),
]:
    register(_sid, _fn, _d, category='body', gain=0.55, rms=-25.0, max_gr=3.0, params=_p)


# ───────────────────────── la tensione ─────────────────────────


def _periodic_lfo(n, cycles, phase=0.0):
    """Un'oscillazione che fa un numero intero di giri nel loop (così il loop non ha giunture)."""
    return np.sin(TWO_PI * cycles * np.arange(n) / n + phase)


def _tension_low(s, rng):
    """Il fondo basso: due note gravi a un soffio di distanza che battono lente, un grappolo scuro di seghe filtrate
    che respira, e ogni tanto il fasciame della barca che geme sotto, lontano."""
    n = s.n
    t = np.arange(n) / SR
    y = np.zeros((2, n))
    # ogni oscillatore fa un numero intero di giri nel loop, se no la giuntura si sente
    q = lambda f: round(f * s.dur) / s.dur  # noqa: E731
    # le due note che battono (un numero intero di battiti nel loop)
    for ch, (fa, fb) in enumerate([(q(41.2), q(41.2) + 7 / s.dur), (q(41.2) + 3 / s.dur, q(41.2) + 11 / s.dur)]):
        y[ch] += 0.6 * np.sin(TWO_PI * fa * t) + 0.6 * np.sin(TWO_PI * fb * t)
        y[ch] += 0.18 * np.sin(TWO_PI * 2 * fa * t + 0.7)
    # il grappolo: la, si bemolle e mi bemolle gravi, seghe arrotondate che respirano
    for k, f in enumerate([55.0, 58.27, 77.78]):
        for ch in range(2):
            det = q(f * (1.0 + (0.0025 if ch else -0.0025) * (k + 1)))
            ph = TWO_PI * det * t + rng.uniform(0, TWO_PI)
            saw = sum(np.sin(m * ph) / m for m in range(1, 9))
            sw = 0.55 + 0.45 * _periodic_lfo(n, 2 + k, rng.uniform(0, TWO_PI))
            y[ch] += 0.11 * saw * sw
    y = circular(lambda x: lowpass(x, 260.0, 2), y)
    # il fasciame che geme: legno che si torce, lento e basso, due o tre volte nel loop (composto in circolo)
    for t0 in rng.uniform(0, s.dur, 3):
        d = rng.uniform(1.6, 2.6)
        m = ns(d)
        exc = rng.standard_normal(m) * curve(m, [(0, 0), (d * 0.3, 1), (d * 0.7, 0.6), (d, 0)])
        f0 = rng.uniform(70, 110)
        bend = curve(m, [(0, 1.0), (d, rng.uniform(0.82, 0.94))])
        g = tv_bandpass(exc, f0 * bend, 6.0) + 0.5 * tv_bandpass(exc, 2.3 * f0 * bend, 9.0)
        g = normalize(g) * 0.22
        pan = rng.uniform(0.3, 0.7)
        place(y, np.stack([g * (1 - pan), g * pan]) * 1.4, t0, wrap=True)
    return y


def _tension_high(s, rng):
    """Il fondo alto, per quando è vicino: archi stonati in alto (un grappolo che non risolve, col vibrato lento e
    il tremolo) e il metallo strofinato che fischia, appena."""
    n = s.n
    y = np.zeros((2, n))
    q = lambda f: round(f * s.dur) / s.dur  # noqa: E731
    for k, f in enumerate([1108.7, 1174.7, 1244.5, 1661.2]):
        for ch in range(2):
            vib = 1.0 + 0.004 * _periodic_lfo(n, 5 + k, rng.uniform(0, TWO_PI))
            ph = TWO_PI * np.cumsum(q(f * (1.0 + (0.001 if ch else -0.001))) * vib) / SR
            bow = np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
            trem = 0.6 + 0.4 * _periodic_lfo(n, int(s.dur * (5.5 + k)), rng.uniform(0, TWO_PI))
            sw = 0.5 + 0.5 * _periodic_lfo(n, 1 + (k % 2), rng.uniform(0, TWO_PI))
            y[ch] += 0.09 * bow * trem * sw
    # l'arco: un fruscio di crine dentro gli archi
    hair = circular(lambda x: bandpass(x, 1800, 6000, 2), rng.standard_normal((2, n)))
    y += 0.025 * normalize(hair) * (0.5 + 0.5 * _periodic_lfo(n, 3))
    # il metallo strofinato: un fischio sottile che sale e scende, una volta nel loop
    for t0 in rng.uniform(0, s.dur, 2):
        d = rng.uniform(2.5, 4.0)
        m = ns(d)
        f = curve(m, [(0, 2900), (d * 0.5, 3300), (d, 3050)])  # (dentro il loop: si compone in circolo)
        w = np.sin(TWO_PI * np.cumsum(f) / SR) * curve(m, [(0, 0), (d * 0.4, 1), (d, 0)])
        place(y, 0.05 * np.stack([w, w * 0.6]), t0, wrap=True)
    return circular(lambda x: highpass(lowpass(x, 7000.0, 2), 300.0, 2), y)


register('tensione_bassa', _tension_low, 24.0, loop=True, channels=2, category='mus', gain=0.7, rms=-24.0)
register('tensione_alta', _tension_high, 16.0, loop=True, channels=2, category='mus', gain=0.6, rms=-28.0)


# ───────────────────────── le creature vive ─────────────────────────


def _twitch(s, rng):
    """Lo scatto della testa quando la guardi: la cartilagine che schiocca, la carne bagnata che segue, e un fiato
    corto dal naso."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.9 * bone_crack(rng, size=s.params['size'], dur=0.25, bright=0.85), 0.01)
    place(y, 0.45 * squish(rng, 0.16, 260, 1400, density=1100, sticky=0.7), 0.03)
    place(y, 0.18 * big_sniff(rng, 0.2, f=0.8, wet_amt=0.6), 0.12)
    return roomify(lowpass(highpass(y, 80.0, 2), 9000.0, 2), rng, 0.1)


for _sid, _size in [('vivo_scatto_1', 0.55), ('vivo_scatto_2', 0.75), ('vivo_scatto_3', 0.95)]:
    register(_sid, _twitch, 0.45, category='mon', gain=0.75, rms=-19.0, max_gr=6.0, release=0.02, params={'size': _size})


def _drip(s, rng):
    """Una goccia che cade da chi è uscito dall'acqua: il «plic» (una bollicina che risuona e sale di tono) e, a volte,
    una seconda più piccola."""
    n = s.n
    y = np.zeros(n)
    for k in range(1 if rng.uniform() < 0.5 else 2):
        m = ns(0.12)
        t = tvec(m)
        f0 = rng.uniform(900, 1500) * (1.0 if k == 0 else 1.4)
        f = f0 * (1.0 + 0.9 * (1.0 - np.exp(-t / 0.012)))
        w = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / rng.uniform(0.025, 0.045))
        click = highpass(rng.standard_normal(m), 3000) * exp_env(m, 0.0015)
        place(y, (1.0 if k == 0 else 0.4) * (w + 0.15 * click), 0.005 + k * rng.uniform(0.09, 0.16))
    return roomify(y, rng, 0.08)


for _i in range(1, 5):
    register(f'goccia_{_i}', _drip, 0.32, category='sfx', gain=0.5, rms=-24.0, max_gr=6.0, release=0.02)
