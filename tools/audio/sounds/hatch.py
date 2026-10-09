"""
Hatch (poppa, ci si nasconde): il bambino che vinceva sempre a nascondino, ora un bipede altissimo con la
testa da rana pescatrice, i denti di vetro e il giocattolo luminoso del negozio del parco che gli penzola
davanti alla faccia come un'esca. La sua conta fino a dieci è la voce sintetica di src/engine/voice.ts;
qui ci sono i passi bagnati, le annusate, il ronzio del giocattolo, la salita a bordo e il jumpscare.
Mono (si spazializza nel gioco), tranne il jumpscare.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

# il motivo della ninna nanna della Madre (lo stesso di mus_title), che il chip del giocattolo prova a suonare
LULLABY_MOTIF = [76, 72, 69, 71, 72, 74, 76, 71]


def _finish(y, rng, room=0.12, lp=10000.0):
    return roomify(lowpass(highpass(y, 40, 2), lp, 2), rng, room)


# ───────────────────────── passi bagnati sul pagliolo ─────────────────────────

def _step(s, rng):
    p = s.params
    y = np.zeros(s.n)
    place(y, wet_footstep(rng, weight=p['w'], dur=s.dur - 0.02, claws=p['claws'], creak_amt=p['creak']), 0.0)
    return _finish(y, rng)


for _i, (_w, _cl, _cr, _d) in enumerate([(1.0, 0.4, 0.6, 0.7), (0.9, 0.0, 0.8, 0.72), (1.1, 0.6, 0.3, 0.66),
                                          (0.95, 0.3, 0.9, 0.75)], 1):
    register(f'hatch_step_{_i}', _step, _d, category='mon', gain=0.9, rms=-16.0, max_gr=6.0,
             params={'w': _w, 'claws': _cl, 'creak': _cr})


# ───────────────────────── annusate ─────────────────────────

def _snort(rng, d=0.32, flutter=0.6):
    """Lo sbuffo dopo le annusate: fiato che esce dalle fessure del naso e dalle branchie, che sbattono."""
    nz = tract_noise(rng, d, [(0, 'u'), (d, '@')], scale=0.8, amp_pts=[(0, 0.4), (0.03, 1), (d, 0)], hiss=0.4)
    nz = lip_flutter(nz, rng, rate=27.0, depth=flutter)
    return nz + 0.4 * saliva(rng, d, rate=120, f_lo=1000, f_hi=5000, env_pts=[(0, 1), (d, 0.2)])


def _sniff(s, rng):
    p = s.params
    y = np.zeros(s.n)
    for t0, d0, a in p['sniffs']:
        place(y, a * big_sniff(rng, d0, f=rng.uniform(0.85, 1.05), wet_amt=0.6), t0)
    t0, d0 = p['snort']
    place(y, 0.75 * _snort(rng, d0), t0)
    if p.get('glass'):
        # il fiato che sibila fra i denti di vetro, che tintinnano appena
        place(y, 0.25 * teeth_clack(rng, count=5, spread=0.05, glass=1.0, dur=0.35), t0 + 0.05)
    return _finish(y, rng)


register('hatch_sniff_1', _sniff, 1.05, category='mon', gain=0.85, rms=-17.0,
         params={'sniffs': [(0.0, 0.14, 0.85), (0.19, 0.13, 0.9), (0.37, 0.16, 1.0)], 'snort': (0.62, 0.36)})
register('hatch_sniff_2', _sniff, 1.15, category='mon', gain=0.85, rms=-17.0,
         params={'sniffs': [(0.0, 0.24, 0.9), (0.33, 0.27, 1.0)], 'snort': (0.72, 0.4), 'glass': True})
register('hatch_sniff_3', _sniff, 1.2, category='mon', gain=0.85, rms=-17.0,
         params={'sniffs': [(0.0, 0.1, 0.7), (0.13, 0.1, 0.8), (0.25, 0.1, 0.9), (0.36, 0.13, 1.0)], 'snort': (0.75, 0.42),
                 'glass': True})


# ───────────────────────── il giocattolo luminoso (loop) ─────────────────────────

def _chip_note(rng, f, d, sag=0.0):
    """Una nota del chip musicale del giocattolo: onda quadra sottile, con la pila scarica che la fa
    calare e balbettare."""
    n = ns(d)
    fr = f * curve(n, [(0, 1.0), (d, 1.0 - sag)], 'log') * cents(8 * rand_curve(n, 7.0, rng))
    ph = phase_of(fr)
    sq = np.sign(np.sin(TWO_PI * ph)) * 0.8 + 0.2 * np.sin(TWO_PI * ph)
    sq = lowpass(sq, 6000, 2)
    env = curve(n, [(0, 0), (0.004, 1), (d * 0.8, 0.85), (d, 0)])
    return sq * env


def _toy(s, rng):
    """Il giocattolo che penzola: il fischio sottile del circuito che accende la luce, un ronzio a scatti
    dei contatti della pila che ballano, l'acqua che sfrigola dentro, e due volte il chip musicale che prova
    a suonare la ninna nanna della Madre, rallentata e calante, e si inceppa."""
    n, dur = s.n, s.dur
    t = tvec(n)
    y = np.zeros(n)
    # il circuito: fischio acuto con la luce che sfarfalla (PWM), i contatti che vanno e vengono
    flick = np.clip(0.6 + 0.5 * rand_curve(n, 3.5, rng) + 0.25 * rand_curve(n, 23.0, rng), 0.05, 1.2)
    drop = 0.2 + 0.8 * (rand_curve(n, 1.3, rng) > -1.25).astype(float)       # cali brevi della pila
    drop = circular(lambda x: lowpass(x, 14.0, 1), drop, pad=0.5)
    # il fischio della bobina: rumore a banda stretta attorno ai 3,9 kHz (mai un tono pulito), un filo d'armonica
    fw = periodic_freq(np.full(n, 3870.0) * cents(25 * rand_curve(n, 0.7, rng)))
    coil = spectral_noise(n, rng, lambda f: peak_shape(f, 3870.0, 40.0, 30.0) - 1.0)
    whine = coil / (np.max(np.abs(coil)) + 1e-9) * 1.6 + 0.35 * np.sin(TWO_PI * phase_of(fw)) \
        + 0.12 * np.sin(2 * TWO_PI * phase_of(fw))
    buzz_f = periodic_freq(np.full(n, 118.0) * cents(15 * rand_curve(n, 0.5, rng)))
    bph = phase_of(buzz_f)
    buzz = np.tanh(3.0 * np.sin(TWO_PI * bph)) + 0.4 * np.sign(np.sin(2 * TWO_PI * bph))
    buzz = circular(lambda x: bandpass(x, 150, 2600, 2), buzz)
    y += 0.06 * whine * flick * drop + 0.065 * buzz * flick ** 2 * drop
    # scricchiolii dei contatti (a grappoli, quando il giocattolo dondola)
    crack = np.zeros(n)
    for tc in poisson_times(rng, lambda tt: 5.0 + 25.0 * (np.sin(TWO_PI * 3 * tt / dur) > 0.6), 0.0, dur):
        k = max(4, ns(rng.uniform(0.0003, 0.002)))
        crack_ = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 3.0))
        place(crack, crack_ * rng.lognormal(-0.5, 0.7), tc, wrap=True)
    y += 0.25 * circular(lambda x: bandpass(x, 800, 9000, 2), crack)
    # acqua che sfrigola nel vano della pila
    fz = spectral_noise(n, rng, lambda f: bw_bp(f, 2500, 11000, 2)) * np.clip(rand_curve(n, 0.4, rng) - 0.3, 0, None) ** 2
    y += 0.05 * fz
    # gocce che cadono dal giocattolo
    for td in poisson_times(rng, 1.3, 0.0, dur):
        place(y, droplet(rng, amp=rng.uniform(0.04, 0.12)), td, wrap=True)
    # il chip musicale: il motivo della ninna nanna, lento, calante, che si inceppa
    chip = np.zeros(n)
    for start, notes, step, sag in [(1.6, LULLABY_MOTIF[:5], 0.36, 0.0), (7.2, LULLABY_MOTIF, 0.42, 0.25)]:
        tt = start
        for i, m in enumerate(notes):
            f = float(midi_hz(m)) * cents(-35 - 60 * sag * i / len(notes))
            d = step * (0.85 + 0.3 * rng.random())
            if sag and i == 5:
                # si inceppa: la stessa nota ripetuta a scatti
                for r in range(3):
                    place(chip, 0.8 * _chip_note(rng, f, 0.06), tt + r * 0.08, wrap=True)
                tt += 0.3
                continue
            place(chip, _chip_note(rng, f, d * 0.8, sag=0.04 + 0.12 * sag * i / len(notes)), tt, wrap=True)
            tt += d * (1 + sag * i / len(notes) * 0.6)
    # altoparlantino: banda stretta, saturo, bagnato
    chip = circular(lambda x: bandpass(softclip(bandpass(x, 500, 4500, 2), 2.5), 600, 5000, 2), chip)
    y += 0.3 * chip
    return circular(lambda x: highpass(x, 60, 2), y)


register('hatch_toy', _toy, 12.0, loop=True, category='mon', gain=0.55, rms=-22.0)


# ───────────────────────── sale a bordo ─────────────────────────

def _board(s, rng):
    """La mano enorme che sbatte sul capodibanda di poppa, l'acqua che gli cola di dosso a fiotti mentre
    esce dal mare, la poppa che affonda e geme, il piede sul pagliolo, poi un fiato lungo fra i denti di vetro."""
    n = s.n
    y = np.zeros(n)
    place(y, wet_slap(rng, size=1.0, surface='wood', dur=0.5, wood_base=118.0, drops=1.2), 0.0)
    nb = ns(0.5)
    place(y, 0.7 * lowpass(rng.standard_normal(nb), 180, 2) * exp_env(nb, 0.25, attack=0.003), 0.004)
    # l'acqua che cola dal corpo che esce dal mare
    m = ns(1.5)
    inten = curve(m, [(0, 0.2), (0.25, 1.0), (0.8, 0.6), (1.5, 0)])
    place(y, 0.35 * gush(m, rng, inten, bubble_rate=160, f_lo=300, f_hi=2400), 0.1)
    for _ in range(25):
        place(y, droplet(rng, amp=rng.uniform(0.04, 0.12)), rng.uniform(0.3, 1.9))
    # la poppa che affonda sotto il peso
    g = creak(rng, 1.1, [(0, 15), (0.4, 30), (1.1, 19)], [(0, 0), (0.2, 1), (0.8, 0.8), (1.1, 0)], base=105, t60=0.16,
              bright=0.7, jitter=0.12, hiss=0.1)
    place(y, 0.45 * g, 0.2)
    place(y, 0.7 * wet_slap(rng, size=0.9, surface='wood', dur=0.4, wood_base=130.0, drops=0.8), 0.48)
    place(y, 0.9 * wet_footstep(rng, weight=1.2, dur=0.7, claws=0.5, creak_amt=0.9), 0.95)
    for t0 in (0.3, 0.9):
        place(y, 0.4 * lap(rng, 1.0, dur=1.0, hull=0.6), t0)
    # il fiato fra i denti di vetro
    d = 0.7
    br = tract_noise(rng, d, [(0, 'a'), (d, '@')], scale=0.7, amp_pts=[(0, 0), (0.1, 1), (d, 0)], hiss=0.5)
    place(y, 0.35 * br, 1.45)
    place(y, 0.18 * teeth_clack(rng, count=4, spread=0.08, glass=1.0, dur=0.5), 1.5)
    return _finish(y, rng)


register('hatch_board', _board, 2.3, category='mon', gain=0.9, rms=-16.0)


# ───────────────────────── jumpscare ─────────────────────────

def _js_hatch(s, rng):
    """Ti trova: i denti di vetro che scattano, il chip del giocattolo che impazzisce, e l'urlo: un ragazzino
    che strilla dentro una gola roca e vuota, con il raspo sotto. Tre morsi a vuoto mentre si avventa."""
    n = s.n
    d = s.dur
    f0_pts = [(0, 250), (0.07, 410), (0.45, 375), (0.8, 440), (1.15, 400), (d, 300)]
    vowels = [(0, 'ae'), (0.1, 'a'), (0.9, 'a'), (d, 'O')]
    amp = [(0, 0.7), (0.04, 1), (1.15, 0.95), (d, 0.45)]
    rasp = np.zeros(n)
    for k, det in enumerate((-10.0, 0.0, 12.0)):
        pts = [(t, f * cents(det)) for t, f in f0_pts]
        rasp += (1.0 if k == 1 else 0.6) * vox(rng, d, pts, vowels, scale=0.9, amp_pts=amp, oq=0.36, jitter=0.08,
                                               shimmer=0.26, sub=0.55, breath=0.9, breath_base=0.6, bw=1.4, rough=0.75,
                                               rough_rate=57.0, rough_fm=70.0, wander=45)
    kid = vox(rng, d, [(t, f * 2.24) for t, f in f0_pts], [(0, 'a'), (d, 'ae')], scale=1.32, amp_pts=amp, oq=0.4,
              jitter=0.05, shimmer=0.18, sub=0.3, breath=0.5, bw=1.5, rough=0.6, rough_rate=81.0, rough_fm=60.0, wander=40)
    y = normalize(rasp) + 0.45 * normalize(kid)
    # il chip impazzito: arpeggio quadro velocissimo che sale e si strozza
    chip = np.zeros(n)
    tt = 0.0
    i = 0
    while tt < d - 0.05:
        m = LULLABY_MOTIF[i % len(LULLABY_MOTIF)] + 12 * ((i // 4) % 2)
        f = float(midi_hz(m)) * cents(40 * i)
        place(chip, _chip_note(rng, f, 0.05, sag=0.1), tt)
        tt += 0.055
        i += 1
    chip = bandpass(softclip(bandpass(chip, 600, 5000, 2), 3.0), 700, 6000, 2)
    y += 0.2 * normalize(chip)
    # denti di vetro: lo scatto iniziale e tre morsi
    for t0, a in [(0.0, 1.0), (0.36, 0.7), (0.71, 0.8), (1.06, 0.9)]:
        place(y, a * 0.8 * teeth_clack(rng, count=18, spread=0.006, glass=1.0, dur=0.3), t0)
    place(y, 0.4 * wet_slap(rng, size=0.8, surface='wood', dur=0.4, drops=0.8), 0.0)
    ir = near_room(rng, 0.45, stereo_out=True)
    out = stereo(y) * np.sqrt(0.5) + 0.22 * convolve(y, ir)
    out = lowpass(highpass(out, 50, 2), 12000, 2)
    return scream_master(out, drive=2.0)


register('js_hatch', _js_hatch, 1.4, channels=2, category='mon', gain=1.0, rms=-6.6, max_gr=6.5, release=0.03)


# ───────────────────────── emerge dietro la poppa ─────────────────────────

def _rise(s, rng):
    """Emerge dietro la poppa, altissimo: l'acqua che si apre, l'acqua che gli scorre giù dal corpo lungo
    e sottile, il giocattolo che si accende con uno scatto e comincia a ronzare, un fiato prima di contare."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.6 * splash(rng, size=0.35, dur=0.9), 0.0)
    m = ns(1.7)
    place(y, 0.4 * gush(m, rng, curve(m, [(0, 0.3), (0.2, 1.0), (0.9, 0.4), (1.7, 0)]), bubble_rate=160, f_lo=400, f_hi=3000),
          0.05)
    for _ in range(18):
        place(y, droplet(rng, amp=rng.uniform(0.04, 0.12), tonal=0.35), rng.uniform(0.4, 1.9))
    # il giocattolo: lo scatto del contatto, poi il ronzio che parte balbettando
    exc = np.zeros(ns(0.05))
    exc[:2] = [1.0, -0.5]
    place(y, 0.12 * normalize(modal(exc, [3100.0, 5200.0, 7900.0], [0.01, 0.007, 0.004])), 0.42)
    d = 1.4
    t = tvec(ns(d))
    buzz = np.tanh(3.0 * np.sin(TWO_PI * 118.0 * t)) * (0.4 + 0.6 * (np.sin(TWO_PI * 9.0 * t) > -0.3))
    buzz = bandpass(buzz, 150, 2600, 2) * curve(ns(d), [(0, 0), (0.25, 0.6), (0.4, 0.2), (0.6, 1.0), (d - 0.35, 0.8), (d, 0)])
    coil = bandpass(rng.standard_normal(ns(d)), 3700, 4050, 2) * curve(ns(d), [(0, 0), (0.6, 1), (d - 0.35, 0.8), (d, 0)])
    place(y, 0.05 * buzz + 0.04 * normalize(coil), 0.44)
    br = tract_noise(rng, 0.45, [(0, 'a'), (0.45, '@')], scale=0.8, amp_pts=[(0, 0), (0.3, 1), (0.45, 0)], hiss=0.5)
    place(y, 0.2 * br, 1.35)
    return _finish(y, rng)


register('hatch_rise', _rise, 2.1, category='mon', gain=0.85, rms=-17.0, max_gr=6.0)
