"""
Robin (notte 2, ruba dal secchio): il bambino che prendeva le cose degli altri e le nascondeva sotto gli scivoli,
ora la gallinella di mare col muso baffuto da pesce gatto: cammina sui raggi duri delle pinne come su zampette e
ha i biglietti della sala giochi avvolti, fradici, sulle braccia. Sale sul bordo, fruga nel secchio, strappa un
pesce e lo porta in acqua; nella luce piena scappa. La sua voce è quella delle gallinelle vere, che gracidano col
tamburo della vescica natatoria: raffiche di colpi bassi e sordi (un «grr-grr» da rana sott'acqua). Dentro, a tratti,
una risatina soffocata dal naso, di bambino che l'ha fatta franca. Non parla. Mono (si spazializza nel gioco),
tranne il jumpscare.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

DRUM_F = 165.0     # il tamburo della vescica natatoria: il modo più basso (Hz)


def _finish(y, rng, room=0.12, lp=11000.0):
    return roomify(lowpass(highpass(y, 45, 2), lp, 2), rng, room)


def _drum(rng, dur, rate_pts, env_pts, f=DRUM_F, jitter=0.12, bright=1.0):
    """Il gracidio: un treno di colpi sordi del muscolo sulla vescica natatoria (ogni colpo un'onda smorzata a
    pochi modi, come un tamburello bagnato), con la frequenza dei colpi che cambia (rate_pts, colpi al secondo)
    e un filo di rumore di carne. Le gallinelle vere fanno raffiche da 20 a 60 colpi al secondo."""
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
            k = max(2, ns(rng.uniform(0.0015, 0.003)))
            exc[:k] = np.sin(np.pi * (np.arange(k) + 0.5) / k)
            ff = f * rng.uniform(0.94, 1.06)
            body = modal(exc, [ff, ff * 1.93 * bright, ff * 3.05 * bright, ff * 4.4 * bright],
                         [0.018, 0.011, 0.007, 0.004], [1.0, 0.55, 0.3, 0.15])
            place(y, a * rng.lognormal(0, 0.18) * normalize(body), t)
        r = float(np.interp(t, t_, rate))
        t += (1.0 / r) * (1.0 + jitter * rng.standard_normal())
    # la carne attorno che vibra: un velo di rumore grave che segue i colpi
    fl = lowpass(rng.standard_normal(n), 700, 2) * lowpass(np.abs(y), 40.0)
    return normalize(y + 0.6 * normalize(fl) * np.max(np.abs(y)))


def _snicker(rng, dur, f0=430.0, n_puffs=4):
    """La risatina soffocata dal naso, a bocca chiusa («hm-hm-hm»), di bambino che l'ha fatta franca: sbuffi
    nasali che scendono, bagnati, con il gracidio sotto."""
    on = [dur * 0.05 + i * (dur * 0.78 / n_puffs) + rng.uniform(-0.02, 0.02) for i in range(n_puffs)]
    durs = [rng.uniform(0.07, 0.11) for _ in on]
    n = ns(dur)
    env = pulses(n, on, durs, att=0.01, rel=0.04, levels=[1.0 - 0.15 * i for i in range(n_puffs)])
    pts = [(0, f0 * 1.08), (dur, f0 * 0.82)]
    v = vox(rng, dur, pts, [(0, 'm'), (dur * 0.5, 'n'), (dur, 'm')], scale=1.35, amp_pts=env, oq=0.62, jitter=0.03,
            shimmer=0.15, breath=0.8, breath_base=0.6, bw=1.7, wander=25.0, hnoise=env * 0.8)
    nose = big_sniff(rng, dur, f=1.25, wet_amt=0.6) * env
    y = normalize(v) + 0.45 * normalize(nose)
    return normalize(wet(y, rng, rate=18.0, depth=0.35, bubbles=0.25, flange=0.3, f_lo=500, f_hi=1500))


def _tick_wood(rng, a=1.0):
    """Un raggio duro della pinna che batte sul legno del capodibanda (un'unghia corta e bagnata)."""
    k = knock(rng, force=rng.uniform(0.00025, 0.0005), base=rng.uniform(650, 1100), t60=0.025, count=6, bright=1.6,
              dur=0.06)
    place(k, 0.25 * squelch(rng, 0.02, 1500, 4500, rate=80.0, density=900.0), 0.0)
    return a * k


def _shell_modes(rng, lo, hi, count, t60, bright=1.0):
    """Modi fitti e inarmonici della lamiera zincata del secchio (come in fishing.py)."""
    f = np.exp(np.linspace(np.log(lo), np.log(hi), count)) * rng.uniform(0.95, 1.05, count)
    T = t60 * (lo / f) ** 0.45 * rng.uniform(0.7, 1.3, count)
    g = (1.0 / np.arange(1, count + 1) ** (0.5 / bright)) * rng.uniform(0.5, 1.2, count)
    return f, T, g


def _tick_metal(rng, modes, a=1.0, force=None):
    """Un raggio della pinna (o un'unghia) sulla lamiera del secchio: tic metallico corto."""
    m = ns(0.25)
    exc = np.zeros(m)
    k = max(2, ns(force or rng.uniform(0.0003, 0.0008)))
    exc[:k] = np.sin(np.pi * (np.arange(k) + 0.5) / k)
    f, T, g = modes
    return a * normalize(modal(exc, f, T, g * rng.uniform(0.6, 1.3, len(g))))


def _tickets(rng, dur, env_pts, a=1.0):
    """I biglietti della sala giochi avvolti sulle braccia, fradici: carta molle che sfrega e si stacca a strappi
    (meno croccante della tela, più fruscio)."""
    y = crinkle(rng, dur, env_pts, density=260.0, f_lo=900.0, f_hi=5000.0, res=2300.0, swish=0.5)
    return a * normalize(lowpass(y, 6500, 2))


def _drips(y, rng, t0, t1, count, lo=0.03, hi=0.1):
    for _ in range(count):
        place(y, droplet(rng, amp=rng.uniform(lo, hi), tonal=0.35), rng.uniform(t0, t1))


# ───────────────────────── sale sul bordo ─────────────────────────

def _climb(s, rng):
    """Sale dal mare sul capodibanda: l'acqua che si apre e gli cola di dosso, la mano bagnata che sbatte sul
    bordo, il legno che cede appena sotto il peso, le zampette dure che ticchettano in fila sul legno, i biglietti
    fradici che sfregano, e un gracidio corto quando è su."""
    n = s.n
    d = s.dur
    y = np.zeros(n)
    place(y, 0.55 * splash(rng, size=0.25, dur=0.8), 0.0)
    m = ns(1.1)
    place(y, 0.35 * gush(m, rng, curve(m, [(0, 0.2), (0.15, 1.0), (0.6, 0.35), (1.1, 0)]), bubble_rate=120,
                         f_lo=500, f_hi=3500), 0.08)
    place(y, 0.7 * wet_slap(rng, size=0.45, surface='wood', dur=0.45, wood_base=170.0, drops=0.8), 0.22)
    c = creak(rng, 0.42, [(0, 30), (0.2, 70), (0.42, 40)], [(0, 0), (0.05, 1), (0.3, 0.6), (0.42, 0)], base=175.0,
              t60=0.09, bright=0.8, jitter=0.12)
    place(y, 0.22 * c, 0.3)
    t = 0.42
    for i in range(10):
        place(y, _tick_wood(rng, 0.5 * rng.uniform(0.6, 1.0)), t)
        t += rng.uniform(0.055, 0.11)
    place(y, 0.3 * _tickets(rng, 0.9, [(0, 0), (0.2, 1), (0.6, 0.6), (0.9, 0)]), 0.35)
    place(y, 0.55 * _drum(rng, 0.32, [(0, 26), (0.32, 22)], [(0, 0), (0.03, 1), (0.25, 0.8), (0.32, 0)]), d - 0.5)
    _drips(y, rng, 0.25, d - 0.05, 16)
    return _finish(y, rng)


register('robin_climb', _climb, 1.75, category='mon', gain=0.85, rms=-17.0, max_gr=6.0)


# ───────────────────────── fruga nel secchio ─────────────────────────

def _rattle(s, rng):
    """Le zampe nel secchio: i raggi delle pinne che ticchettano sulla lamiera, i pesci bagnati che scivolano e
    sbattono contro le pareti, il secchio che si sposta sul pagliolo; un gracidio avido sotto."""
    p = s.params
    n = s.n
    d = s.dur
    y = np.zeros(n)
    wall = _shell_modes(rng, 520, 7200, 24, 0.14, bright=1.2)
    bottom = _shell_modes(rng, 240, 2400, 16, 0.2, bright=0.8)
    t = 0.0
    for i in range(p['ticks']):
        place(y, _tick_metal(rng, wall, 0.35 * rng.uniform(0.5, 1.0)), t)
        t += rng.uniform(0.04, 0.1)
        if t > d - 0.3:
            break
    for t0 in p['fish']:
        place(y, 0.4 * squish(rng, 0.12, 300, 2200, density=900, sticky=0.5), t0)
        place(y, 0.22 * _tick_metal(rng, wall, 1.0, force=0.003), t0 + 0.03)
    # il secchio che si sposta: la lamiera del fondo sul legno
    place(y, 0.3 * _tick_metal(rng, bottom, 1.0, force=0.006), p['shift'])
    place(y, 0.15 * knock(rng, 0.003, base=150, t60=0.06, dur=0.25), p['shift'])
    sl = bandpass(rng.standard_normal(n), 300, 2500) * curve(n, [(0, 0), (0.1, 1), (d * 0.6, 0.5), (d, 0)])
    y += 0.05 * normalize(sl * (0.6 + 0.4 * np.abs(rand_curve(n, 12.0, rng))))
    place(y, 0.35 * _drum(rng, 0.4, [(0, 30), (0.4, 38)], [(0, 0), (0.05, 0.8), (0.3, 1), (0.4, 0)], f=180.0), p['croak'])
    return _finish(y, rng, room=0.1)


register('robin_rattle_1', _rattle, 1.05, category='mon', gain=0.8, rms=-18.0, max_gr=8.0, release=0.02,
         params={'ticks': 9, 'fish': [0.18, 0.55], 'shift': 0.4, 'croak': 0.6})
register('robin_rattle_2', _rattle, 1.15, category='mon', gain=0.8, rms=-18.0, max_gr=8.0, release=0.02,
         params={'ticks': 12, 'fish': [0.32], 'shift': 0.12, 'croak': 0.7})


# ───────────────────────── strappa un pesce ─────────────────────────

def _steal(s, rng):
    """Un pesce strappato dal secchio: la presa bagnata, il pesce che si dibatte contro la lamiera, trascinato
    sopra il bordo (la pancia che striscia sul legno), giù in mare; poi la risatina soffocata."""
    n = s.n
    y = np.zeros(n)
    wall = _shell_modes(rng, 520, 7200, 24, 0.15, bright=1.2)
    place(y, 0.5 * squish(rng, 0.14, 350, 2600, density=1100, sticky=0.6), 0.0)
    for i, t in enumerate([0.08, 0.17, 0.25]):
        place(y, 0.35 * 0.8 ** i * _tick_metal(rng, wall, 1.0, force=0.003), t + rng.uniform(-0.01, 0.01))
        place(y, 0.4 * 0.8 ** i * wet_slap(rng, size=0.25, surface='none', dur=0.2, drops=0.5), t)
    # trascinato sul capodibanda: carne bagnata che striscia sul legno
    m = ns(0.32)
    drag = squelch(rng, 0.32, 300, 1800, rate=30.0, density=1400.0) * curve(m, [(0, 0), (0.05, 1), (0.25, 0.7), (0.32, 0)])
    place(y, 0.35 * drag, 0.3)
    place(y, 0.18 * creak(rng, 0.25, [(0, 40), (0.25, 60)], [(0, 0), (0.04, 1), (0.25, 0)], base=190.0, t60=0.08), 0.32)
    place(y, 0.25 * _tickets(rng, 0.4, [(0, 0), (0.1, 1), (0.4, 0)]), 0.28)
    place(y, 0.6 * splash(rng, size=0.32, dur=0.7), 0.68)
    place(y, 0.42 * _snicker(rng, 0.55, f0=440.0, n_puffs=4), 0.92)
    _drips(y, rng, 0.05, 0.6, 8)
    return _finish(y, rng)


register('robin_steal', _steal, 1.6, category='mon', gain=0.85, rms=-17.0, max_gr=6.0)


# ───────────────────────── scappa dalla luce ─────────────────────────

def _scared(s, rng):
    """Nella luce piena scappa: un gracidio d'allarme velocissimo che sale (la raffica dei pesci spaventati), uno
    strillo strozzato dal naso, le zampette che raspano sul legno in fuga, il corpo che scivola giù per la
    fiancata, il tuffo."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.8 * _drum(rng, 0.45, [(0, 45), (0.2, 62), (0.45, 50)], [(0, 0), (0.02, 1), (0.35, 0.8), (0.45, 0)],
                         f=205.0, jitter=0.08, bright=1.1), 0.0)
    yelp = vox(rng, 0.32, [(0, 620), (0.08, 880), (0.32, 520)], [(0, 'n'), (0.1, 'i'), (0.32, 'n')], scale=1.38,
               amp_pts=[(0, 0), (0.03, 1), (0.22, 0.7), (0.32, 0)], oq=0.45, jitter=0.05, shimmer=0.2, breath=0.7,
               bw=1.6, rough=0.5, rough_rate=60.0, rough_fm=40.0, wander=30.0)
    place(y, 0.38 * normalize(wet(yelp, rng, rate=24.0, depth=0.4, bubbles=0.2, flange=0.35)), 0.06)
    t = 0.22
    for i in range(14):
        place(y, _tick_wood(rng, 0.45 * rng.uniform(0.5, 1.0)), t)
        t += rng.uniform(0.03, 0.06)
    place(y, 0.3 * _tickets(rng, 0.5, [(0, 0), (0.1, 1), (0.5, 0)]), 0.25)
    m = ns(0.35)
    slide = squelch(rng, 0.35, 250, 1500, rate=25.0, density=1500.0) * curve(m, [(0, 0), (0.05, 1), (0.35, 0.3)])
    place(y, 0.3 * slide, 0.68)
    place(y, 0.7 * splash(rng, size=0.42, dur=0.75), 0.95)
    _drips(y, rng, 0.1, 0.9, 6)
    return _finish(y, rng)


register('robin_scared', _scared, 1.75, category='mon', gain=0.9, rms=-16.5, max_gr=6.0)


# ───────────────────────── jumpscare ─────────────────────────

def _js_robin(s, rng):
    """A secchio vuoto ti salta in faccia: lo schiocco bagnato con cui molla il bordo, i biglietti che frustano
    l'aria, e il grido: il tamburo della gallinella a raffica furiosa con dentro lo strillo di un bambino (tre voci
    appena scordate), ruvido e bagnato; i baffi da pesce gatto che sbattono, un risucchio di bocca enorme."""
    n = s.n
    d = s.dur
    f0_pts = [(0, 520), (0.06, 820), (0.4, 760), (0.85, 860), (1.15, 720), (d, 480)]
    amp = [(0, 0.6), (0.04, 1), (1.12, 0.95), (d, 0.4)]
    kid = np.zeros(n)
    for k, det in enumerate((-14.0, 0.0, 11.0)):
        pts = [(t, f * cents(det)) for t, f in f0_pts]
        kid += (1.0 if k == 1 else 0.6) * vox(rng, d, pts, [(0, 'ae'), (0.12, 'a'), (0.9, 'ae'), (d, 'a')], scale=1.35,
                                             amp_pts=amp, oq=0.4, jitter=0.06, shimmer=0.22, sub=0.35, breath=0.6, bw=1.5,
                                             rough=0.7, rough_rate=48.0, rough_fm=65.0, wander=40.0)
    throat = vox(rng, d, [(t, f * 0.36) for t, f in f0_pts], [(0, 'a'), (d, 'O')], scale=0.85, amp_pts=amp, oq=0.4,
                 jitter=0.07, shimmer=0.25, sub=0.6, breath=0.8, bw=1.4, rough=0.8, rough_rate=36.0, rough_fm=60.0)
    y = normalize(kid) + 0.32 * normalize(highpass(wet_throat(throat, rng, rate=20.0, depth=0.45, bubbles=0.3), 160, 2))
    # il tamburo della vescica: raffica furiosa dentro il grido (come negli altri jumpscare, i bassi non devono
    # coprire lo strillo)
    drum = _drum(rng, d, [(0, 40), (0.1, 72), (1.0, 66), (d, 50)], [(0, 0.5), (0.03, 1), (1.15, 0.9), (d, 0.3)],
                 f=240.0, jitter=0.06, bright=1.15)
    y += 0.3 * normalize(highpass(drum, 150, 2))
    place(y, 0.6 * wet_slap(rng, size=0.7, surface='wood', dur=0.4, drops=1.0), 0.0)
    place(y, 0.3 * _tickets(rng, 0.7, [(0, 0), (0.05, 1), (0.5, 0.7), (0.7, 0)]), 0.02)
    sw = bandpass(rng.standard_normal(ns(0.35)), 400, 3000) * curve(ns(0.35), [(0, 0), (0.12, 1), (0.35, 0)])
    place(y, 0.25 * normalize(sw), 0.0)
    ir = near_room(rng, 0.45, stereo_out=True)
    out = stereo(y) * np.sqrt(0.5) + 0.22 * convolve(y, ir)
    out = lowpass(highpass(out, 50, 2), 12000, 2)
    return scream_master(out, drive=2.0)


register('js_robin', _js_robin, 1.4, channels=2, category='mon', gain=1.0, rms=-6.6, max_gr=6.5, release=0.03)
