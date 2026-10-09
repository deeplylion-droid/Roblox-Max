"""
Gulpy (prua, va sfamato): il gigante-pesce pellicano con la mascella che si sgancia fino al petto e il
salvagente a paperella incastrato nella carne del collo. Voce enorme e bagnata (gola lunghissima:
formanti a poco più di metà di quelle di un uomo), fiato affamato, gorgoglii, deglutizioni,
masticazione, la gomma che cigola. Tutto mono (si spazializza nel gioco), tranne il jumpscare.
Ogni verso ha un filo di contenuto acuto (saliva, fiato): senza, in cuffia non si capirebbe da dove arriva.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

GIANT = 0.56     # scala delle formanti: un tratto vocale lungo quasi il doppio di quello di un uomo


def _finish(y, rng, lp=6500.0, room=0.12):
    return roomify(lowpass(y, lp, 2), rng, room)


def _moan(rng, d, f0_pts, vowels, amp_pts, *, scale=GIANT, oq=0.6, jitter=0.035, shimmer=0.15, sub=0.45,
          breath=0.5, rough=0.0, rough_rate=28.0, wander=25.0, vib=(0.0, 4.0), layers=2, spread=4.0):
    """Lamento della gola enorme: due o tre strati leggermente diversi (gole che non vanno all'unisono:
    battimenti e ruvidità organici invece di un'onda sola)."""
    out = np.zeros(ns(d))
    for k in range(layers):
        det = cents(spread * (k - (layers - 1) / 2) * 2)
        pts = [(t, f * det) for t, f in f0_pts]
        v = vox(rng, d, pts, vowels, scale=scale * (1 + 0.03 * (k - 0.5)), amp_pts=amp_pts, oq=oq, jitter=jitter,
                shimmer=shimmer, sub=sub, breath=breath, rough=rough, rough_rate=rough_rate * (1 + 0.1 * k),
                wander=wander, vib=vib)
        out += v * (1.0 if k == 0 else 0.6)
    return normalize(out)


# ───────────────────────── fiato affamato ─────────────────────────

def _breath_1(s, rng):
    """Inspiro umido dalla bocca enorme, poi un espiro lungo con il lamento sotto."""
    y = np.zeros(s.n)
    d_in = 0.9
    inh = tract_noise(rng, d_in, [(0, 'o'), (d_in, 'a')], scale=0.62,
                      amp_pts=[(0, 0.25), (d_in * 0.75, 1), (d_in, 0)], bw=1.3, hiss=0.3)
    inh = wet_throat(inh, rng, rate=30, depth=0.5, bubbles=0.0, flange=0.35)
    inh = inh + 0.35 * saliva(rng, d_in, rate=80, env_pts=[(0, 0.2), (d_in * 0.7, 1), (d_in, 0.2)])
    place(y, 0.75 * inh, 0.0)
    d_ex = 1.4
    v = _moan(rng, d_ex, [(0, 60), (0.35, 55), (d_ex, 43)], [(0, 'o'), (0.6, 'u'), (d_ex, 'u')],
              [(0, 0), (0.12, 1), (0.8, 0.7), (d_ex, 0)], oq=0.8, breath=0.9, sub=0.45)
    nz = tract_noise(rng, d_ex, [(0, 'o'), (d_ex, 'u')], scale=GIANT, amp_pts=[(0, 0), (0.1, 1), (d_ex, 0)], hiss=0.12)
    ex = wet_throat(0.75 * v + 0.5 * nz, rng, rate=20, depth=0.6, bubbles=0.5, flange=0.5, f_lo=110, f_hi=520)
    ex = ex + 0.12 * saliva(rng, d_ex, rate=45, env_pts=[(0, 0.5), (0.4, 1), (d_ex, 0)])
    place(y, ex, 1.0)
    return _finish(y, rng)


def _breath_2(s, rng):
    """Espiro lungo dalle labbra molli (sbattono nel fiato), un mugolio che sale e ricade, labbra che si chiudono."""
    y = np.zeros(s.n)
    d = 1.7
    nz = tract_noise(rng, d, [(0, 'u'), (0.8, 'o'), (d, 'u')], scale=GIANT, amp_pts=[(0, 0.3), (0.15, 1), (1.1, 0.8), (d, 0)],
                     hiss=0.18)
    nz = lip_flutter(nz, rng, rate=21.0, depth=0.7)
    v = _moan(rng, d, [(0, 52), (0.6, 66), (1.2, 58), (d, 47)], [(0, 'u'), (0.7, 'o'), (d, 'u')],
              [(0, 0), (0.25, 0.9), (1.2, 0.7), (d, 0)], oq=0.75, breath=0.7, sub=0.35)
    ex = wet_throat(0.6 * nz + 0.55 * v, rng, rate=17, depth=0.45, bubbles=0.45, flange=0.4)
    place(y, ex, 0.0)
    # le labbra che si richiudono: schiocco umido e appiccicoso
    place(y, 0.45 * squish(rng, 0.16, 300, 1800, density=1000, sticky=0.8), d - 0.03)
    return _finish(y, rng)


def _breath_3(s, rng):
    """Due inspiri corti e avidi (fiuta il pesce), poi un espiro roco con il fry sotto."""
    y = np.zeros(s.n)
    for t0, d0, a in [(0.0, 0.32, 0.8), (0.42, 0.38, 1.0)]:
        inh = tract_noise(rng, d0, [(0, 'a'), (d0, 'O')], scale=0.6, amp_pts=[(0, 0.3), (d0 * 0.8, 1), (d0, 0)], hiss=0.35)
        inh = wet_throat(inh, rng, rate=35, depth=0.45, bubbles=0.0, flange=0.3)
        inh += 0.4 * saliva(rng, d0, rate=110, env_pts=[(0, 0.4), (d0, 1)])
        place(y, a * inh, t0)
    d = 1.25
    v = _moan(rng, d, [(0, 38), (0.4, 42), (d, 31)], [(0, 'a'), (0.5, 'o'), (d, 'o')],
              [(0, 0), (0.08, 1), (0.8, 0.6), (d, 0)], oq=0.4, jitter=0.11, shimmer=0.3, sub=0.6, breath=0.6,
              rough=0.3, rough_rate=19.0)
    nz = tract_noise(rng, d, [(0, 'a'), (d, 'o')], scale=GIANT, amp_pts=[(0, 0), (0.06, 1), (d, 0)], hiss=0.15)
    ex = wet_throat(0.8 * v + 0.45 * nz, rng, rate=22, depth=0.55, bubbles=0.45)
    place(y, ex, 0.9)
    return _finish(y, rng)


for _i, (_fn, _d) in enumerate([(_breath_1, 2.45), (_breath_2, 1.95), (_breath_3, 2.2)], 1):
    register(f'gulpy_breath_{_i}', _fn, _d, category='mon', gain=0.85, rms=-18.0)


# ───────────────────────── gorgoglio affamato ─────────────────────────

def _gurgle_1(s, rng):
    """'Ghhuurrll': ringhio basso e gorgogliante, la gola piena d'acqua."""
    d = s.dur
    v = _moan(rng, d, [(0, 62), (0.4, 70), (1.2, 58), (d, 50)], [(0, 'u'), (0.5, 'o'), (1.2, 'u'), (d, 'u')],
              [(0, 0.3), (0.08, 1), (1.15, 0.8), (d, 0)], oq=0.55, jitter=0.04, shimmer=0.18, sub=0.55,
              breath=0.45, rough=0.35, rough_rate=28.0, wander=30)
    y = wet_throat(v, rng, rate=24, depth=0.7, bubbles=0.6, f_lo=140, f_hi=600)
    y = y + 0.3 * throat_bubbles(rng, d, rate=35, env_pts=[(0, 0), (0.1, 1), (d * 0.8, 0.7), (d, 0)])
    # il fiato che esce fra i denti ad ago, la bava che crepita
    air = tract_noise(rng, d, [(0, 'u'), (0.5, 'o'), (d, 'u')], scale=GIANT, amp_pts=[(0, 0.3), (0.1, 1), (d * 0.8, 0.7), (d, 0)],
                      hiss=0.6)
    y = y + 0.22 * wet_throat(air, rng, rate=24, depth=0.6, bubbles=0.0, flange=0.0)
    y = y + 0.18 * saliva(rng, d, rate=70, env_pts=[(0, 1), (d, 0.3)])
    return _finish(y, rng, lp=8000)


def _gurgle_2(s, rng):
    """Il richiamo della fame: un lamento che sale aprendo la bocca e ricade, poi un piccolo 'glk'."""
    d = 1.55
    y = np.zeros(s.n)
    v = _moan(rng, d, [(0, 50), (0.55, 80), (1.0, 72), (d, 60)], [(0, 'u'), (0.4, 'o'), (0.8, 'a'), (d, 'o')],
              [(0, 0.25), (0.3, 1), (1.1, 0.85), (d, 0)], oq=0.5, jitter=0.03, shimmer=0.12, sub=0.3, breath=0.3,
              rough=0.15, rough_rate=33.0, vib=(9.0, 4.2), layers=3)
    v = wet_throat(v, rng, rate=18, depth=0.45, bubbles=0.4)
    air = tract_noise(rng, d, [(0, 'u'), (0.4, 'o'), (0.8, 'a'), (d, 'o')], scale=GIANT,
                      amp_pts=[(0, 0.25), (0.3, 1), (1.1, 0.85), (d, 0)], hiss=0.6)
    v = v + 0.2 * air + 0.16 * saliva(rng, d, rate=70, env_pts=[(0, 0.3), (0.8, 1), (d, 0.5)])
    place(y, v, 0.0)
    place(y, 0.5 * gulp(rng, size=0.5, dur=0.4), d - 0.05)
    return _finish(y, rng)


def _gurgle_3(s, rng):
    """Solo acqua in gola: il fiato che ribolle, un paio di 'glonk', bava che crepita."""
    d = s.dur
    y = np.zeros(s.n)
    nz = tract_noise(rng, d, [(0, 'o'), (0.7, 'u'), (d, 'o')], scale=GIANT, amp_pts=[(0, 0.3), (0.1, 1), (d * 0.75, 0.8), (d, 0)],
                     hiss=0.15)
    y += 0.55 * wet_throat(nz, rng, rate=30, depth=0.85, bubbles=0.8, f_lo=120, f_hi=500, width=0.014)
    y += 0.7 * throat_bubbles(rng, d, rate=70, f_lo=110, f_hi=520, env_pts=[(0, 0.3), (0.1, 1), (d * 0.8, 0.8), (d, 0)])
    for t0 in (0.32, 0.86):
        place(y, 0.45 * gulp(rng, size=0.8, dur=0.35), t0 + rng.uniform(-0.04, 0.04))
    y += 0.15 * saliva(rng, d, rate=70)
    return _finish(y, rng, lp=5000)


def _gurgle_4(s, rng):
    """Ringhio col fry (la voce che gratta sul fondo della gola), uno schiocco di labbra all'inizio."""
    d = 1.4
    y = np.zeros(s.n)
    place(y, 0.4 * squish(rng, 0.12, 300, 2000, density=1100, sticky=0.6), 0.0)
    v = _moan(rng, d, [(0, 33), (0.5, 41), (d, 29)], [(0, 'a'), (0.7, 'O'), (d, 'o')],
              [(0, 0), (0.1, 1), (0.9, 0.8), (d, 0)], oq=0.35, jitter=0.12, shimmer=0.3, sub=0.6, breath=0.5,
              rough=0.4, rough_rate=22.0)
    nz = tract_noise(rng, d, [(0, 'a'), (d, 'o')], scale=GIANT, amp_pts=[(0, 0), (0.1, 1), (d, 0)], hiss=0.12)
    v = wet_throat(0.85 * v + 0.35 * nz, rng, rate=26, depth=0.55, bubbles=0.5)
    place(y, v, 0.05)
    y += 0.08 * saliva(rng, s.dur, rate=40)
    return _finish(y, rng)


for _i, (_fn, _d) in enumerate([(_gurgle_1, 1.7), (_gurgle_2, 1.85), (_gurgle_3, 1.4), (_gurgle_4, 1.5)], 1):
    register(f'gulpy_gurgle_{_i}', _fn, _d, category='mon', gain=0.85, rms=-17.0)


# ───────────────────────── il salvagente che stringe ─────────────────────────

def _rubber_1(s, rng):
    """La gomma tesa che sfrega sulla carne bagnata del collo."""
    y = np.zeros(s.n)
    place(y, 0.3 * squish(rng, 0.1, 400, 2200, density=900, sticky=0.4), 0.0)
    r = rubber_squeal(rng, 0.85, [(0, 360), (0.3, 650), (0.55, 520), (0.85, 410)],
                      [(0, 0.3), (0.06, 1), (0.5, 0.75), (0.85, 0)])
    place(y, r, 0.03)
    return _finish(y, rng, lp=7000, room=0.1)


def _rubber_2(s, rng):
    """Il fischietto della paperella, schiacciato dal collo che si gonfia: un guaito di gomma sfiatato."""
    y = np.zeros(s.n)
    place(y, squeaker(rng, 0.42, [(0, 1180), (0.12, 1720), (0.42, 1300)]), 0.0)
    place(y, 0.45 * rubber_squeal(rng, 0.38, [(0, 520), (0.2, 410), (0.38, 330)], [(0, 0), (0.05, 1), (0.38, 0)]), 0.4)
    return _finish(y, rng, lp=8000, room=0.1)


register('gulpy_rubber_1', _rubber_1, 0.95, category='mon', gain=0.6, rms=-19.0)
register('gulpy_rubber_2', _rubber_2, 0.85, category='mon', gain=0.6, rms=-19.0)


# ───────────────────────── la mascella che si sgancia ─────────────────────────

def _jaw(s, rng):
    """Legamenti che si tendono (scricchiolio basso), due schiocchi piccoli e uno enorme (la mascella si
    sgancia), la carne bagnata che si stira, i fili di bava che si spezzano, poi il fiato dalla bocca spalancata."""
    n = s.n
    y = np.zeros(n)
    # i legamenti che cedono piano
    d_c = 0.62
    c = creak(rng, d_c, [(0, 22), (0.3, 34), (d_c, 48)], [(0, 0.2), (0.1, 0.6), (d_c, 1)], base=95, t60=0.12,
              bright=0.6, jitter=0.15, hiss=0.05)
    place(y, 0.35 * lowpass(c, 1500, 2), 0.0)
    place(y, 0.25 * bone_crack(rng, size=0.15, dur=0.1, bright=0.7), 0.0)      # il primo scricchiolio
    # schiocchi: piccoli, poi quello grande
    for t0, sz, a in [(0.17, 0.3, 0.35), (0.36, 0.45, 0.5), (0.6, 1.0, 1.0)]:
        place(y, a * bone_crack(rng, size=sz, dur=0.3, bright=0.8), t0)
    nt = ns(0.3)
    thud = osc(curve(nt, [(0, 75), (0.2, 48)], 'log')) * exp_env(nt, 0.18, attack=0.002)
    place(y, 0.55 * thud, 0.6)
    # la carne che si stira e la bava che fila
    place(y, 0.5 * squish(rng, 0.35, 220, 1400, density=700, sticky=0.9), 0.63)
    place(y, 0.25 * saliva(rng, 0.7, rate=90, f_lo=1500, f_hi=6000, env_pts=[(0, 1), (0.7, 0.1)]), 0.66)
    for _ in range(4):
        place(y, droplet(rng, amp=rng.uniform(0.04, 0.1)), rng.uniform(0.8, 1.5))
    # il fiato che esce dalla bocca spalancata (vocale aperta, gola enorme)
    d = 0.95
    v = _moan(rng, d, [(0, 47), (d, 40)], [(0, 'a'), (d, 'a')], [(0, 0), (0.15, 1), (d, 0)], scale=0.5, oq=0.85,
              breath=1.0, sub=0.5, jitter=0.05, layers=2)
    nz = tract_noise(rng, d, [(0, 'a'), (d, 'O')], scale=0.5, amp_pts=[(0, 0), (0.12, 1), (d, 0)], hiss=0.1)
    place(y, 0.55 * wet_throat(0.6 * v + 0.6 * nz, rng, rate=16, depth=0.5, bubbles=0.4), 0.78)
    return _finish(y, rng, lp=7500)


register('gulpy_jaw', _jaw, 1.75, category='mon', gain=0.9, rms=-17.0, max_gr=7.0, release=0.03)


# ───────────────────────── mangia ─────────────────────────

def _chew_cycle(rng, strength=1.0, bones=1.0):
    """Un morso di masticazione: la carne schiacciata, le lische che si spezzano, la mascella che sbatte,
    la bocca che si riapre appiccicosa."""
    y = np.zeros(ns(0.45))
    place(y, 0.6 * strength * squish(rng, rng.uniform(0.12, 0.2), 200, 1300, density=900, sticky=0.3), 0.0)
    if bones:
        place(y, 0.55 * bones * crunch(rng, rng.uniform(0.04, 0.09), density=rng.uniform(300, 700)), rng.uniform(0.02, 0.06))
    nt = ns(0.12)
    th = lowpass(rng.standard_normal(nt), 220, 2) * exp_env(nt, 0.05, attack=0.002)
    place(y, 0.35 * strength * normalize(th), 0.03)
    place(y, 0.25 * squish(rng, 0.08, 700, 3200, density=1300, sticky=0.8), rng.uniform(0.2, 0.28))
    return y


EAT_BITE = 0.42      # il morso arriva quando arriva il pesce (night.ts suona chew() appena lo lanci)


def _eat(s, rng):
    """Un inspiro avido a bocca spalancata mentre il pesce vola, il morso secco quando arriva, la
    masticazione con i denti ad ago, la deglutizione enorme, un rutto d'acqua soddisfatto."""
    y = np.zeros(s.n)
    p = s.params
    d0 = EAT_BITE + 0.02
    gasp = tract_noise(rng, d0, [(0, 'a'), (d0, 'O')], scale=0.55, amp_pts=[(0, 0.35), (d0 * 0.85, 1), (d0, 0.2)], hiss=0.3)
    gasp = wet_throat(gasp, rng, rate=30, depth=0.5, bubbles=0.0, flange=0.3)
    place(y, 0.45 * gasp + 0.12 * saliva(rng, d0, rate=90, env_pts=[(0, 0.4), (d0, 1)]), 0.0)
    # il morso: denti ad ago che si chiudono + lo schiaffo bagnato del pesce in bocca
    tb = EAT_BITE
    place(y, 0.9 * teeth_clack(rng, count=16, spread=0.006, dur=0.25), tb)
    place(y, 0.6 * wet_slap(rng, size=0.6, surface='flesh', dur=0.35, drops=0.4), tb + 0.004)
    place(y, 0.4 * crunch(rng, 0.07, 800), tb + 0.01)
    t = tb + 0.3
    for i in range(p['chews']):
        place(y, _chew_cycle(rng, 1.0 - 0.1 * i, bones=1.0 if i < p['chews'] - 1 else 0.4), t)
        t += rng.uniform(0.3, 0.42)
    # deglutizione enorme
    place(y, 1.0 * gulp(rng, size=1.0, dur=0.75), t + 0.05)
    t += 0.7
    # un rutto d'acqua: gorgoglio basso e breve, soddisfatto
    d = s.dur - t - 0.05
    if d > 0.3:
        v = _moan(rng, d, [(0, 58), (d, 46)], [(0, 'o'), (d, 'u')], [(0, 0), (0.08, 1), (d, 0)], oq=0.5, breath=0.4,
                  sub=0.5, rough=0.3, rough_rate=24.0, layers=2)
        place(y, 0.6 * wet_throat(v, rng, rate=26, depth=0.7, bubbles=0.6), t)
    return _finish(y, rng, lp=8000)


register('gulpy_eat_1', _eat, 3.6, category='mon', gain=0.85, rms=-17.0, max_gr=6.0, params={'chews': 4})
register('gulpy_eat_2', _eat, 3.3, category='mon', gain=0.85, rms=-17.0, max_gr=6.0, params={'chews': 3})


# ───────────────────────── jumpscare ─────────────────────────

def _js_gulpy(s, rng):
    """Si lancia sul pescatore con la mascella spalancata: acqua che esplode, un ruggito enorme e bagnato
    (la gola gigante) con sopra uno strillo da maiale (la stessa gola, più in alto), e alla fine i denti
    ad ago che si chiudono davanti alla faccia."""
    n = s.n
    d = s.dur
    t = tvec(n)
    # ruggito: tre gole, f0 che sale e ricade, voce compressa e piena di subarmoniche
    roar = _moan(rng, d, [(0, 72), (0.18, 118), (0.6, 104), (1.0, 86), (d, 60)], [(0, 'O'), (0.12, 'a'), (0.9, 'a'), (d, 'O')],
                 [(0, 0.7), (0.05, 1), (1.05, 0.95), (d, 0.45)], scale=0.6, oq=0.42, jitter=0.06, shimmer=0.22,
                 sub=0.6, breath=0.5, rough=0.6, rough_rate=46.0, wander=40, layers=3, spread=7.0)
    shriek = _moan(rng, d, [(0, 420), (0.15, 690), (0.7, 610), (d, 380)], [(0, 'a'), (0.5, 'ae'), (d, 'a')],
                   [(0, 0.2), (0.08, 1), (1.0, 0.8), (d, 0.1)], scale=0.82, oq=0.45, jitter=0.06, shimmer=0.2,
                   sub=0.4, breath=0.4, rough=0.7, rough_rate=74.0, wander=60, layers=2, spread=12.0)
    v = roar + 0.5 * shriek
    v = wet_throat(v, rng, rate=26, depth=0.4, bubbles=0.35, flange=0.35)
    # acqua che esplode e spruzzi di bava
    spray = highpass(rng.standard_normal(n), 1500) * curve(n, [(0, 1), (0.25, 0.35), (d, 0.15)]) * (0.6 + 0.4 * np.abs(rand_curve(n, 30, rng)))
    y = v + 0.18 * normalize(spray)
    place(y, 0.6 * splash(rng, size=0.7, dur=0.9), 0.0)
    # colpo grave del corpo che si lancia
    nb = ns(0.5)
    place(y, 0.45 * osc(curve(nb, [(0, 80), (0.3, 48)], 'log')) * exp_env(nb, 0.3, attack=0.002), 0.0)
    # i denti che si chiudono davanti alla faccia
    place(y, 0.9 * teeth_clack(rng, count=22, spread=0.007, dur=0.25), 1.12)
    place(y, 0.5 * wet_slap(rng, size=0.9, surface='flesh', dur=0.25, drops=0.3), 1.125)
    ir = near_room(rng, 0.5, stereo_out=True)
    out = stereo(y) * np.sqrt(0.5) + 0.22 * convolve(y, ir)
    out = lowpass(highpass(out, 60, 2), 9000, 2)
    return scream_master(out, drive=1.9)


register('js_gulpy', _js_gulpy, 1.4, channels=2, category='mon', gain=1.0, rms=-6.6, max_gr=6.0, release=0.03)


# ───────────────────────── si aggrappa alla prua ─────────────────────────

def _grab(s, rng):
    """Riemerge aggrappato alla prua: due mani enormi e bagnate che sbattono sul capodibanda, la prua che
    affonda sotto il suo peso e geme, l'acqua che gli cola dalle braccia, un fiato enorme."""
    n = s.n
    y = np.zeros(n)
    for t0, sz, base in [(0.0, 1.0, 96.0), (0.27, 0.9, 112.0)]:
        place(y, wet_slap(rng, size=sz, surface='wood', dur=0.6, wood_base=base, drops=1.5), t0)
        nt = ns(0.45)
        place(y, 0.7 * lowpass(rng.standard_normal(nt), 150, 2) * exp_env(nt, 0.25, attack=0.004), t0 + 0.003)
    g = creak(rng, 1.3, [(0, 12), (0.5, 26), (1.3, 15)], [(0, 0), (0.2, 1), (0.9, 0.8), (1.3, 0)], base=92, t60=0.2,
              bright=0.6, jitter=0.15, hiss=0.08)
    place(y, 0.55 * g, 0.3)
    m = ns(1.4)
    place(y, 0.3 * gush(m, rng, curve(m, [(0, 0.3), (0.2, 1.0), (1.4, 0)]), bubble_rate=150, f_lo=300, f_hi=2200), 0.15)
    for t0 in (0.35, 0.8):
        place(y, 0.45 * lap(rng, 1.0, dur=1.0, hull=0.6), t0)
    d = 0.9
    v = _moan(rng, d, [(0, 50), (d, 42)], [(0, 'o'), (d, 'u')], [(0, 0), (0.15, 1), (d, 0)], oq=0.8, breath=0.9, sub=0.5)
    nz = tract_noise(rng, d, [(0, 'o'), (d, 'u')], scale=GIANT, amp_pts=[(0, 0), (0.12, 1), (d, 0)], hiss=0.3)
    place(y, 0.5 * wet_throat(0.6 * v + 0.6 * nz, rng, rate=18, depth=0.5, bubbles=0.4), 1.05)
    return _finish(y, rng, lp=9000)


register('gulpy_grab', _grab, 2.1, category='mon', gain=0.9, rms=-16.0, max_gr=6.0)


# ───────────────────────── emerge ─────────────────────────

def _rise(s, rng):
    """Emerge lontano davanti alla prua: l'acqua che si gonfia e si rompe, l'acqua che gli cade di dosso a
    scrosci dalle spalle enormi, uno sbuffo da balena (fiato e spruzzi da una gola gigante), un gemito
    affamato."""
    n = s.n
    y = np.zeros(n)
    nb = ns(0.6)
    bloom = lowpass(rng.standard_normal(nb), 260, 2) * curve(nb, [(0, 0.2), (0.12, 1), (0.6, 0)])
    place(y, 0.5 * normalize(bloom), 0.0)
    place(y, 0.6 * splash(rng, size=0.6, dur=1.1), 0.02)
    m = ns(2.0)
    place(y, 0.55 * gush(m, rng, curve(m, [(0, 0.2), (0.25, 1.0), (1.0, 0.55), (2.0, 0)]), bubble_rate=200, f_lo=250, f_hi=2000),
          0.08)
    for _ in range(6):
        place(y, 0.25 * splash(rng, size=rng.uniform(0.12, 0.25), dur=0.6), rng.uniform(0.3, 1.6))
    d = 1.2
    blow = tract_noise(rng, d, [(0, 'O'), (d, 'u')], scale=0.5, amp_pts=[(0, 0), (0.06, 1), (0.5, 0.7), (d, 0)], hiss=0.5)
    spray = highpass(rng.standard_normal(ns(d)), 1800) * curve(ns(d), [(0, 0), (0.05, 1), (0.4, 0.3), (d, 0)])
    place(y, 0.5 * wet_throat(blow, rng, rate=22, depth=0.5, bubbles=0.5) + 0.12 * normalize(spray), 0.55)
    dm = 0.9
    v = _moan(rng, dm, [(0, 48), (0.4, 62), (dm, 50)], [(0, 'u'), (0.4, 'o'), (dm, 'u')], [(0, 0), (0.2, 1), (dm, 0)],
              oq=0.6, breath=0.5, sub=0.5, rough=0.3, rough_rate=26.0)
    place(y, 0.45 * wet_throat(v, rng, rate=22, depth=0.6, bubbles=0.5), 1.65)
    return _finish(y, rng, lp=9000)


register('gulpy_rise', _rise, 2.7, category='mon', gain=0.9, rms=-16.0, max_gr=6.0)
