"""
I suoni delle cinematiche dei finali della notte 6 (stereo, 17–18 s ciascuno: ogni finale è una cinematica breve nel
motore del gioco, vedi «I finali» in docs/NOTTI_E_MOSTRI.md):
  - madre_dawn_breve: il finale A «La quota», la versione corta di madre_dawn (17 s invece di 24);
  - finale_nessuno: il finale segreto «Nessuno» (non hai mai lasciato un pesce ai suoi piccoli: ora sei uno di loro);
  - finale_tuoi: il finale segreto «I tuoi» (i figli non seguono la Madre: restano con te e ti seguono a terra).
Nessuno parla: la Madre al massimo canticchia la sua ninna nanna senza parole. La voce, l'acqua e la ninna nanna sono
quelle di madre.py.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register
from sounds.ambience import sea_texture
from sounds.fishing import _hit, _shell_modes
from sounds.madre import DOWN, _at, _blow, _dive, _hum, _underwater, _whale
from sounds.world import boat_creak

P = -0.65           # la Madre sale sempre a sinistra della barca


# ───────────────────────── i pezzi comuni ─────────────────────────

def _dawn_sea(n, rng, pts, gain=1.6):
    """Il mare dell'alba, calmo; pts: quanto è smosso nel tempo."""
    sea = sea_texture(n, rng, swell_cycles=max(2, round(n / SR / 4.5)), lap_rate=0.25, bed=1.0, hull=0.3,
                      lap_gain=0.45, babble=1.0)
    return gain * sea * curve(n, pts)


def _rise(rng, out, t0, size=1.0, creaks=(0.8, 1.8)):
    """Lei che sale accanto alla barca: il mare che si gonfia, si rompe e le scroscia giù dal corpo, la barca che
    dondola e geme."""
    n = out.shape[-1]
    sw = lowpass(highpass(brown(ns(4.0), rng), 18, 2), 110, 2) * curve(ns(4.0), [(0, 0), (0.5, 0.4), (1.6, 1.0), (4.0, 0)])
    place(out, pan(0.8 * size * normalize(sw), P * 0.6), t0)
    m = ns(3.6)
    inten = curve(m, [(0, 0), (0.3, 0.5), (0.7, 1.0), (2.0, 0.6), (3.6, 0)])
    pour = gush(m, rng, inten, bubble_rate=120, f_lo=110, f_hi=900)
    pour = lowpass(pour, 4000, 2) + 0.12 * bandpass(rng.standard_normal(m), 600, 5000, 2) * inten
    place(out, pan(0.9 * size * normalize(pour), P), t0 + 0.3)
    place(out, pan(0.9 * size * splash(rng, size=1.0, dur=1.8), P), t0 + 0.4)
    for tc in creaks:
        cr = boat_creak(rng, 1.4, [(0, 12), (0.7, 26), (1.4, 10)], [(0, 0), (0.4, 1), (1.4, 0)], base=110, t60=0.15,
                        bright=0.8, hull=0.6)
        place(out, pan(0.18 * lowpass(cr, 4000, 2), rng.uniform(-0.5, 0.5)), t0 + tc)
    del n


def _kids_up(rng, out, times_pans, gain=0.5, breath_amt=0.12):
    """I figli che affiorano uno dopo l'altro: l'acqua che si apre, un fiato bagnato, le gocce."""
    for tk, p in times_pans:
        place(out, pan(gain * _dive(rng, rng.uniform(0.4, 0.8), up=True), p), tk)
        if breath_amt:
            place(out, pan(breath(rng, rng.uniform(0.35, 0.55), inhale=True) * breath_amt, p), tk + rng.uniform(0.25, 0.45))
        for _ in range(4):
            place(out, pan(droplet(rng, amp=rng.uniform(0.03, 0.08), tonal=0.4), p), tk + rng.uniform(0.2, 1.0))


def _bucket(rng):
    """Il secchio preso dalla Madre (mono): il secchio che si stacca dal pagliolo, i pesci che scivolano nella
    lamiera, il manico che sbatte, l'acqua che ne cola mentre si alza."""
    b = np.zeros(ns(2.4))
    wall = _shell_modes(rng, 520, 7200, 26, 0.16, bright=1.0)
    bottom = _shell_modes(rng, 240, 2400, 18, 0.22, bright=0.8)
    place(b, _hit(rng, ns(0.6), 0.004, bottom, 0.5), 0.0)
    for i, tb in enumerate([0.12, 0.3, 0.42, 0.6, 0.85]):
        place(b, 0.5 * 0.8 ** i * _hit(rng, ns(0.4), rng.uniform(0.002, 0.004), wall, 0.4), tb)
        place(b, 0.3 * wet_slap(rng, size=0.3, surface='flesh', dur=0.3, drops=0.3), tb + 0.01)
    for tb in (0.05, 0.4, 0.95):
        place(b, 0.18 * knock(rng, force=0.0004, base=1250, t60=0.05, dur=0.15), tb)
    m = ns(2.2)
    drip = bandpass(rng.standard_normal(m), 500, 4500, 2) * curve(m, [(0, 0), (0.1, 1), (0.8, 0.4), (2.2, 0)])
    place(b, 0.12 * normalize(drip), 0.1)
    for _ in range(22):
        place(b, droplet(rng, amp=rng.uniform(0.04, 0.12), tonal=0.4), rng.uniform(0.2, 2.2))
    return b


def _sink(rng, out, t0, gain=1.0, bubbles=(0.6, 4.0)):
    """Lei che torna giù, enorme e lenta: l'acqua che le si chiude sopra, un tonfo sordo, le bolle grosse."""
    m = ns(4.5)
    sink = gush(m, rng, curve(m, [(0, 0), (0.8, 1.0), (2.5, 0.5), (4.5, 0)]), bubble_rate=90, f_lo=90, f_hi=600)
    place(out, pan(0.25 * gain * normalize(lowpass(sink, 2500, 2)), P), t0)
    wh = lowpass(rng.standard_normal(ns(2.5)), 90, 2) * exp_env(ns(2.5), 1.4, attack=0.3)
    place(out, pan(0.3 * gain * normalize(wh), P * 0.6), t0 + 0.6)
    bb = np.zeros(ns(bubbles[1] + 1.0))
    for _ in range(16):
        place(bb, bubble(float(loguniform(rng, 70, 200)), xi=rng.uniform(0.0, 0.08), amp=rng.uniform(0.3, 1.0),
                         decay_mult=0.4, max_dur=0.7), rng.uniform(*bubbles))
    place(out, pan(0.14 * gain * lowpass(bb, 900, 2), P * 0.7), t0)


def _gull(rng, f=1180, p=0.6, kind='short'):
    """Un gabbiano lontano sulla baia (stereo)."""
    g = lowpass(gull_call(rng, kind, f), 4200, 2)
    return 0.5 * pan(g, p) + 0.4 * convolve(g, reverb_ir(2.4, rng, lo=1.1, hi=0.5, sparse=0.6))


def _lullaby_bit(rng, beat, bars=2, start=0.3, major_end=False, sag=40.0):
    """Un pezzo della ninna nanna canticchiato a bocca chiusa (mono): le prime battute (Mi–Do | La–Si …) a tempo
    `beat`; con major_end la fine che si risolve (La Si Do♯ | La)."""
    if major_end:
        seq = [(69, 1), (71, 1), (73, 1), (69, 2)]
    else:
        seq = [(76, 2), (72, 1), (69, 2), (71, 1), (72, 1), (74, 1), (76, 1), (71, 3)][:{1: 2, 2: 4, 4: 8}[bars]]
    notes = []
    t = start
    for m, d in seq:
        notes.append((t, d * beat * 0.93, m - DOWN))
        t += d * beat
    dur = t + 0.6
    y = _hum(rng, ns(dur), notes, [(start, t)], sag=sag, octave=0.5, song=0.1)
    return y


# ───────────────────────── finale A, corto ─────────────────────────

def _dawn_breve(s, rng):
    """Il finale A «La quota», ristretto a 17 s per la cinematica: lei sale a sinistra (0–3 s), lo sbuffo (3 s), i
    sette figli che affiorano attorno (4–7 s), la pinna sul capodibanda e il secchio preso (7–10 s), giù tutti
    (10–13 s), dal fondo la fine della ninna nanna che si risolve (12–16 s), il mare calmo e il primo gabbiano."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    out += _dawn_sea(n, rng, [(0, 0.7), (1.0, 1.0), (3.0, 1.3), (7.0, 1.0), (10.5, 1.3), (13.5, 0.6), (d, 0.35)])
    _rise(rng, out, 0.0)
    place(out, pan(lowpass(_blow(rng, 1.6), 7000, 2), P), 3.0)
    _kids_up(rng, out, [(4.0, -0.95), (4.4, -0.3), (4.8, -0.75), (5.2, 0.1), (5.6, -0.55), (6.0, 0.35), (6.4, -0.85)])
    # la pinna sul bordo, la barca che s'inclina, il secchio preso
    place(out, pan(0.55 * wet_slap(rng, size=1.6, surface='wood', dur=0.6, wood_base=110.0, drops=1.0), P * 0.7), 7.0)
    cr = boat_creak(rng, 1.6, [(0, 14), (0.8, 30), (1.6, 12)], [(0, 0.3), (0.4, 1), (1.6, 0)], base=100, t60=0.16,
                    bright=0.8, hull=0.7)
    place(out, pan(0.3 * lowpass(cr, 4000, 2), P * 0.5), 7.1)
    place(out, pan(_at(_bucket(rng), -21.0), P * 0.4), 7.5)
    # giù tutti: i figli e poi lei
    for k, p in enumerate((-0.9, -0.2, 0.3, -0.7, 0.05, -0.45, -0.8)):
        place(out, pan(0.45 * _dive(rng, rng.uniform(0.3, 0.6)), p), 10.0 + 0.3 * k + rng.uniform(-0.06, 0.06))
    _sink(rng, out, 11.0)
    # dal fondo la fine della ninna nanna, che si risolve
    hum = _underwater(_lullaby_bit(rng, 0.85, major_end=True, sag=20.0), rng, dist=0.8, rt60=3.0)
    place(out, stereo(hum) * 0.09, 12.0)
    for tl, a in [(13.6, 0.4), (14.8, 0.28), (16.0, 0.2)]:
        place(out, pan(lap(rng, a, dur=1.0, hull=0.3), rng.uniform(-0.6, 0.6)) * 0.4, tl)
    place(out, 0.3 * _gull(rng), 15.2)
    return highpass(out, 18, 2) * curve(n, [(0, 1), (d - 0.5, 1), (d, 0)])


register('madre_dawn_breve', _dawn_breve, 17.0, channels=2, category='mon', gain=0.85, rms=-19.0, max_gr=4.0)


# ───────────────────────── finale «Nessuno» ─────────────────────────

def _lamp_dies(rng, dur=2.0):
    """La lampara che muore (mono): il ronzio del reattore che cala di tono e di forza a strappi, la luce che
    sfarfalla, l'ultimo crepitio e lo scatto del relè che stacca; poi niente."""
    n = ns(dur)
    t = tvec(n)
    cut = dur - 0.35
    f = 100.0 * curve(n, [(0, 1.0), (cut * 0.6, 0.97), (cut, 0.86), (dur, 0.86)])
    ph = phase_of(f)
    hum = np.tanh(2 * (np.sin(TWO_PI * ph) + 0.5 * np.sin(2 * TWO_PI * ph + 1) + 0.3 * np.sin(3 * TWO_PI * ph + 2)))
    gate = np.clip(0.75 + 0.35 * rand_curve(n, 14.0, rng), 0, 1) * curve(n, [(0, 1), (cut * 0.5, 0.8), (cut - 0.05, 0.35),
                                                                           (cut, 0), (dur, 0)])
    gate = lowpass(gate, 60, 2)
    y = 0.3 * lowpass(hum, 1500, 2) * gate
    y += 0.12 * bandpass(np.tanh(5 * np.sin(TWO_PI * ph)), 100, 3000) * np.clip(0.8 - gate, 0, 1) * (t < cut)
    for tp in poisson_times(rng, 6.0, 0.2, cut):
        k = ns(rng.uniform(0.0003, 0.001))
        place(y, 0.1 * highpass(rng.standard_normal(k + 64), 1500) * np.exp(-np.arange(k + 64) / k), tp)
    # lo scatto del relè che stacca
    exc = np.zeros(ns(0.12))
    exc[0], exc[1] = 1.0, -0.7
    clk = modal(exc, [2300.0, 3650.0, 5400.0, 800.0], [0.015, 0.01, 0.007, 0.03], [1.0, 0.6, 0.35, 0.5])
    place(y, 0.35 * normalize(clk), cut)
    return lowpass(y, 7000, 2)


def _sign_creak(rng, dur):
    """Il cartello di lamiera appeso alla catenella che oscilla col vento: un cigolio metallico lento, avanti e
    indietro, e la catenella che tintinna appena."""
    y = np.zeros(ns(dur))
    t = 0.05
    while t < dur - 0.5:
        d = rng.uniform(0.45, 0.7)
        c = boat_creak(rng, d, [(0, 140), (d * 0.5, 260), (d, 120)], [(0, 0), (d * 0.3, 1), (d, 0)], base=520, t60=0.05,
                       bright=1.5, jitter=0.03, burst=0.25, wander=0.05, hull=0.0, rub=0.04)
        place(y, rng.uniform(0.6, 1.0) * c, t)
        for _ in range(2):
            place(y, 0.08 * knock(rng, force=0.0003, base=2600, t60=0.02, dur=0.05), t + rng.uniform(0.1, d))
        t += d + rng.uniform(0.2, 0.35)
    return lowpass(y, 6000, 2)


def _polaroid(rng):
    """Lo scatto di una Polaroid: il clac dell'otturatore (due scatti secchi di plastica e molla), il motorino che
    spinge fuori la foto (un ronzio di ingranaggi) e la foto che striscia fuori dalla fessura."""
    y = np.zeros(ns(1.5))
    for t0, a, base in [(0.0, 1.0, 1900.0), (0.035, 0.7, 2600.0)]:
        exc = np.zeros(ns(0.1))
        exc[0], exc[1] = 1.0, -0.8
        sh = modal(exc, base * np.array([1, 1.7, 2.6, 3.9]), [0.02, 0.014, 0.01, 0.006], [1, 0.6, 0.4, 0.25])
        body = modal(exc, [420, 880, 1500], [0.03, 0.02, 0.015], [1, 0.6, 0.4])
        place(y, 0.3 * a * (normalize(sh) + 0.6 * normalize(body)), t0)
    m = ns(0.95)
    tm = tvec(m)
    f = curve(m, [(0, 90), (0.1, 165), (0.8, 158), (0.95, 110)], 'log') * cents(15 * rand_curve(m, 6.0, rng))
    ph = phase_of(f)
    # il motorino: un ronzio di ingranaggi, cioè rumore battuto dai denti (non un tono pulito)
    teeth = (0.5 + 0.5 * np.sin(TWO_PI * ph)) ** 3 + 0.5 * (0.5 + 0.5 * np.sin(TWO_PI * ph * 3.0 + 0.7)) ** 4
    grind = bandpass(rng.standard_normal(m), 400, 3500, 2) * teeth
    hum_ = 0.3 * np.tanh(2.0 * np.sin(TWO_PI * ph)) * (1 + 0.3 * rand_curve(m, 20.0, rng))
    motor = (normalize(grind) + 0.5 * bandpass(hum_, 120, 1500, 2)) * curve(m, [(0, 0), (0.05, 1), (0.85, 0.9), (0.95, 0)])
    slide = bandpass(rng.standard_normal(m), 1500, 7000, 2) * curve(m, [(0, 0), (0.2, 0.5), (0.85, 0.7), (0.95, 0)])
    place(y, 0.3 * normalize(motor) + 0.06 * normalize(slide), 0.15)
    del tm
    return lowpass(y, 6000, 4)


def _nessuno(s, rng):
    """Il finale «Nessuno»: lei sale accanto alla barca ma si ferma, un fiato lungo e basso (0–3 s); i figli
    affiorano uno alla volta attorno alla barca e restano fermi a fissarti (3–8 s), poi solo gocce; la lampara che
    muore, lo scatto, una pressione bassa che cresce (8–10 s); nel buio la ninna nanna canticchiata senza parole,
    vicinissima, come dentro l'acqua (10–15 s); taglio netto sull'edicola del parco: il vento, il cartello che
    cigola, e alla fine lo scatto di una Polaroid (15–18 s)."""
    n, d = s.n, s.dur
    CUT = 15.0
    out = np.zeros((2, n))
    out += _dawn_sea(n, rng, [(0, 0.8), (1.0, 1.1), (3.0, 0.9), (6.0, 0.5), (8.0, 0.35), (10.0, 0.08), (d, 0.08)])
    # sale, ma si ferma: niente secchio, guarda te
    _rise(rng, out, 0.0, size=0.8, creaks=(0.9,))
    m = ns(3.0)
    fiato = tract_noise(rng, 3.0, [(0, 'o'), (3.0, 'u')], scale=0.38, amp_pts=[(0, 0), (0.4, 1), (2.0, 0.7), (3.0, 0)],
                        hiss=0.05)
    fiato = normalize(fiato) + 0.6 * normalize(lowpass(rng.standard_normal(m), 90, 2)) * curve(m, [(0, 0), (0.5, 1), (3.0, 0)])
    fiato = wet_throat(normalize(lowpass(fiato, 2500, 2)), rng, rate=10.0, depth=0.25, bubbles=0.15, flange=0.2)
    place(out, pan(_at(fiato, -24.0), P), 1.4)
    # i figli, uno alla volta, ben distanziati; poi nessuno si muove più: solo gocce
    pts = [(3.1, -0.9), (3.8, 0.7), (4.5, -0.3), (5.2, 0.95), (5.9, 0.2), (6.6, -0.6), (7.3, 0.5)]
    kids = np.zeros((2, n))
    _kids_up(rng, kids, pts, gain=0.42, breath_amt=0.0)
    out += lowpass(kids, 3000, 4)
    for td in poisson_times(rng, 2.5, 7.8, 10.0):
        place(out, pan(droplet(rng, amp=rng.uniform(0.03, 0.08), tonal=0.5), rng.uniform(-0.9, 0.9)), td)
    # la lampara che muore, e la pressione che cresce nel buio
    place(out, pan(_at(_lamp_dies(rng, 1.9), -25.0), 0.35), 8.0)
    press = lowpass(highpass(brown(n, rng), 18, 2), 70, 2)
    out += stereo(_at(press, -30.0) * curve(n, [(0, 0), (9.2, 0), (11.0, 0.6), (CUT - 0.3, 1.0), (CUT, 0), (d, 0)]))
    # nel buio, vicinissima, come dentro l'acqua: Mi–Do | La–Si, lentissimo
    hum = _lullaby_bit(rng, 0.8, bars=2, sag=60.0)
    hum = _underwater(hum, rng, dist=0.1, rt60=2.5)
    hm = np.zeros((2, ns(5.0)))
    place(hm, stereo(hum) * np.sqrt(0.5) + 0.3 * convolve(hum, reverb_ir(2.0, rng, lo=1.3, hi=0.3, lp=1500))[..., :len(hum)], 0.0)
    hm *= curve(hm.shape[-1], [(0, 1), (4.9, 1), (5.0, 0)])
    place(out, _at(hm, -19.0), 10.1)
    # taglio netto (5 ms): tutto quello che c'era sparisce
    out *= curve(n, [(0, 1), (CUT - 0.005, 1), (CUT, 0), (d, 0)])
    # l'edicola del parco: il vento, il cartello che cigola, la Polaroid
    k = n - ns(CUT)
    wind = wind_layer(k, rng, gust_rate=0.5, low=0.4, mid=0.35, high=0.1, whistle=0.015, whistle_f=900.0)
    wind *= curve(k, [(0, 1), (k / SR, 1)])
    shrine = _at(wind, -26.0)
    place(shrine, pan(_at(_sign_creak(rng, 2.4), -27.0), 0.4), 0.15)
    place(shrine, pan(_at(_polaroid(rng), -19.0), -0.1), 1.75)
    place(out, shrine, CUT)
    return highpass(out, 18, 2) * curve(n, [(0, 1), (d - 0.15, 1), (d, 0)])


register('finale_nessuno', _nessuno, 18.0, channels=2, category='mon', gain=0.85, rms=-20.0, max_gr=4.0)


# ───────────────────────── finale «I tuoi» ─────────────────────────

def _oar_stroke(rng):
    """Un colpo di remi del gozzo (stereo, i due remi): gli scalmi che cigolano sotto lo sforzo, le pale che
    entrano in acqua e tirano, l'acqua che gocciola dalle pale quando escono."""
    y = np.zeros((2, ns(1.6)))
    for side in (-0.75, 0.75):
        d = rng.uniform(0.5, 0.65)
        c = boat_creak(rng, d, [(0, 60), (d * 0.4, 140), (d, 70)], [(0, 0), (0.08, 1), (d, 0)], base=330, t60=0.06,
                       bright=1.3, jitter=0.04, burst=0.3, wander=0.06, hull=0.15, rub=0.05)
        place(y, pan(0.5 * c, side), rng.uniform(0.0, 0.03))
        m = ns(0.75)
        pull = lowpass(bandpass(rng.standard_normal(m), 180, 2000, 2), 2500, 2) * curve(m, [(0, 0), (0.05, 1), (0.5, 0.6), (0.75, 0)])
        pull *= 0.6 + 0.4 * np.abs(np.tanh(rand_curve(m, 20.0, rng)))
        place(y, pan(0.3 * normalize(pull), side * 1.2), 0.02)
        for _ in range(6):
            place(y, pan(droplet(rng, amp=rng.uniform(0.03, 0.08), tonal=0.4), side), rng.uniform(0.8, 1.5))
    return y


def _patter(rng, weight=0.3, base=240.0):
    """Un passetto bagnato e scalzo sulle assi del molo: la pianta piccola che schiaffeggia il legno, l'asse che
    risuona, il piede che si stacca appiccicoso."""
    y = np.zeros(ns(0.3))
    place(y, wet_slap(rng, size=weight, surface='wood', dur=0.25, wood_base=base, drops=0.3), 0.0)
    place(y, 0.25 * squish(rng, 0.06, 500, 2600, density=800, sticky=0.6), rng.uniform(0.08, 0.14))
    return y


def _tuoi(s, rng):
    """Il finale «I tuoi»: lei sale e chiama con una frase della ninna nanna (0–3 s); dove ti aspetteresti i figli
    che la seguono c'è silenzio, e lei richiama, più insistente (3–6 s); il suo lamento mentre torna giù da sola,
    profondo e triste, con le bolle (6–10 s); l'alba, i remi del gozzo che cigolano a ritmo e dietro, piccoli tonfi
    che seguono la barca (10–14 s); il porto: i gabbiani, le cime che scricchiolano, la barca che tocca il molo, e i
    passetti bagnati di sette bambini diversi che si allontanano sulle assi (14–18 s)."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    out += _dawn_sea(n, rng, [(0, 0.8), (1.0, 1.1), (3.0, 0.8), (6.0, 0.6), (7.0, 1.1), (10.0, 0.8), (14.0, 0.5), (d, 0.3)])
    # sale e chiama: la frase della ninna nanna, fuori dall'acqua (vicina e piena)
    _rise(rng, out, 0.0, size=0.7, creaks=(0.9,))
    call = _lullaby_bit(rng, 0.62, bars=2, start=0.1, sag=30.0)
    call = lowpass(call, 1800, 2)
    call = call + 0.3 * convolve(call, reverb_ir(2.2, rng, lo=1.2, hi=0.4, sparse=0.5, stereo_out=False))
    place(out, pan(_at(call, -19.0), P), 1.3)
    # silenzio: nessuno la segue. Richiama, più insistente: Mi–Do, Mi–Do, più forte e più rotta
    seq = [(0.1, 0.55, 76), (0.7, 0.4, 72), (1.2, 0.55, 76), (1.8, 0.75, 72)]
    notes = [(t0, dd, m - DOWN + 0) for t0, dd, m in seq]
    again = _hum(rng, ns(3.0), notes, [(0.1, 2.6)], sag=60.0, octave=0.6, song=0.08)
    again = lowpass(again + 0.3 * softclip(normalize(again), 3.0), 2000, 2)
    again = again + 0.3 * convolve(again, reverb_ir(2.2, rng, lo=1.2, hi=0.4, sparse=0.5, stereo_out=False))
    place(out, pan(_at(again, -19.0), P), 4.2)
    # il lamento mentre torna giù da sola
    lam = _whale(rng, 4.0, [(0, 52), (0.8, 58), (2.4, 41), (4.0, 27)], [(0, 'o'), (1.0, 'O'), (2.6, 'o'), (4.0, 'u')],
                 [(0, 0), (0.6, 1.0), (2.2, 0.8), (4.0, 0)], rough=0.2, rough_rate=10.0, under=0.4)
    lam_air = lowpass(lam, 1500, 2)
    lam_w = _underwater(lam, rng, dist=0.6, rt60=3.5)
    m = len(lam)
    mix = curve(m, [(0, 0), (1.2, 0), (2.6, 1.0), (4.0, 1.0)])
    lam_mix = np.concatenate([(1 - mix) * lam_air + mix * lam_w[:m], lam_w[m:]])
    place(out, pan(_at(lam_mix, -21.0), P), 6.0)
    _sink(rng, out, 6.8, gain=0.9, bubbles=(1.0, 4.0))
    # l'alba: i remi a ritmo e, dietro, i piccoli tonfi che seguono la barca
    oars = np.zeros((2, ns(4.4)))
    for k in range(3):
        place(oars, _oar_stroke(rng), 0.15 + 1.45 * k)
    place(out, _at(oars, -24.0), 10.0)
    for tk in [10.6, 11.0, 11.9, 12.1, 12.5, 13.3, 13.6]:
        place(out, pan(0.22 * _dive(rng, rng.uniform(0.15, 0.3), up=rng.random() < 0.5), rng.uniform(-0.25, 0.25)), tk)
    place(out, 0.25 * _gull(rng, 1220, -0.5), 11.4)
    # il porto: le cime che scricchiolano, la barca che tocca il molo, i gabbiani, e i passetti che si allontanano
    place(out, 0.6 * _gull(rng, 1150, 0.55, 'long'), 14.0)
    for tc, p in [(14.2, -0.4), (15.4, 0.3)]:
        c = boat_creak(rng, 0.9, [(0, 70), (0.4, 150), (0.9, 60)], [(0, 0), (0.3, 1), (0.9, 0)], base=360, t60=0.06,
                       bright=1.3, jitter=0.035, burst=0.3, wander=0.06, hull=0.15, rub=0.06)
        place(out, pan(0.2 * c, p), tc)
    bump = knock(rng, force=0.012, base=85, t60=0.2, count=6, bright=0.6, dur=0.8, rough=0.04, cavity=(95, 0.3, 0.6))
    place(out, pan(_at(lowpass(bump, 900, 2), -18.0), 0.5), 14.6)
    place(out, pan(0.2 * lap(rng, 0.5, dur=1.0, hull=0.3), 0.5), 14.7)
    # sette bambini diversi (passo, peso, asse), che scendono sul molo e vanno verso il paese
    for k in range(7):
        w = rng.uniform(0.18, 0.4)
        base = rng.uniform(200, 300)
        rate = rng.uniform(4.2, 5.6)
        t0 = 15.2 + 0.18 * k + rng.uniform(-0.05, 0.05)
        p0 = rng.uniform(-0.2, 0.4)
        tt = t0
        while tt < d - 0.35:
            u = (tt - t0) / (d - t0)
            a = 0.4 * (1 - 0.75 * u)
            stp = lowpass(_patter(rng, w, base), 9000 - 6000 * u, 2)
            place(out, pan(a * stp, p0 * (1 - u) + 0.3 * u), tt)
            tt += 1.0 / rate * rng.uniform(0.92, 1.08)
    return highpass(out, 18, 2) * curve(n, [(0, 1), (d - 0.4, 1), (d, 0)])


register('finale_tuoi', _tuoi, 18.0, channels=2, category='mon', gain=0.85, rms=-20.0, max_gr=4.0)
