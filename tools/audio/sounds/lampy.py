"""
Lampy (notte 4, non va ferrata): la bambina che in piscina tirava giù gli altri per le gambe, per scherzo, ora una
lampreda viola con la cuffia da piscina a fiori: il cranio da neonato, gli occhi tondi senza palpebre, la bocca a
ventosa piena di anelli di denti da latte. Prende la lenza e fa suonare il campanellino come un'abboccata, ma a tempo
perfetto: tre colpi identici (lampy_bell, uno per colpo: il ritmo lo fa il gioco), e dopo il secondo una risatina
sott'acqua da neonata. Poi affiora sulla lenza, ti guarda, e molla con lo schiocco della ventosa. Se la ferri risale la
lenza a baci risucchiati. Non parla. Mono (si spazializza nel gioco), tranne il jumpscare.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register

BABY = 1.55       # scala delle formanti: una neonata (più corta ancora della bambina di Molly)


def _finish(y, rng, room=0.12, lp=11000.0):
    return roomify(lowpass(highpass(y, 40, 2), lp, 2), rng, room)


def _kiss(rng, size=1.0, dur=0.16):
    """Lo schiocco della ventosa (un bacio umido): le labbra che si staccano di colpo, l'aria che entra, la saliva."""
    n = ns(dur)
    y = np.zeros(n)
    m = ns(0.012)
    pop = bandpass(rng.standard_normal(m), 500, 4000, 2) * exp_env(m, 0.006, attack=0.0003)
    place(y, normalize(pop), 0.0)
    f0 = rng.uniform(380, 620) / max(size, 0.3) ** 0.5
    place(y, 0.7 * bubble(f0, xi=0.6, amp=1.0, decay_mult=1.4, max_dur=0.08), 0.002)
    place(y, 0.4 * squish(rng, dur * 0.7, 700, 3000, density=1500, sticky=0.7), 0.004)
    return normalize(y)


# ───────────────────────── il campanellino, a tempo ─────────────────────────

def _bell(s, rng):
    """Un colpo solo dei due campanellini d'ottone in punta alla canna (gli stessi delle abboccate vere, fishing.py):
    il battaglio colpisce una volta, netto, e il secondo campanellino gli risponde appena; la molletta ticchetta. Il
    gioco lo suona tre volte a intervalli identici: è il ritmo perfetto che tradisce Lampy (le abboccate vere sono
    strattoni irregolari)."""
    n = s.n
    sa = [(0.0, 1.0)]
    sb = [(0.017, 0.35)]
    y = small_bell(rng, 2380.0, n, sa, t60=1.0, beat=5.0) + 0.8 * small_bell(rng, 3020.0, n, sb, t60=0.9, beat=6.5)
    exc = np.zeros(ns(0.03))
    exc[0], exc[1] = 1.0, -0.8
    tick = normalize(modal(exc, 5200 * np.array([1, 1.53, 2.21]), [0.012, 0.008, 0.006], [1, 0.6, 0.35]))
    place(y, 0.12 * tick, 0.001)
    return highpass(normalize(y), 400, 2)


register('lampy_bell', _bell, 0.9, category='sfx', gain=0.8, rms=-19.0, max_gr=6.0)


# ───────────────────────── la risatina sott'acqua ─────────────────────────

def _giggle(s, rng):
    """La risatina da sotto l'acqua, dopo il secondo colpo: una neonata che ride a singhiozzi («ih-ih-ih»), ovattata
    dall'acqua, e a ogni sillaba le bolle che le escono dalla bocca e salgono a scoppiare in superficie."""
    n = s.n
    d = s.dur
    on = [0.04, 0.2, 0.34, 0.47, 0.6, 0.76]
    durs = [0.11, 0.1, 0.1, 0.09, 0.11, 0.2]
    env = pulses(n, on, durs, att=0.01, rel=0.04, levels=[0.8, 1.0, 0.95, 0.85, 0.8, 0.6])
    f0 = [(0, 560), (0.2, 640), (0.47, 600), (0.76, 520), (d, 430)]
    v = vox(rng, d, f0, [(0, 'i'), (0.3, 'ae'), (0.6, 'i'), (d, 'e')], scale=BABY, amp_pts=env, oq=0.6, jitter=0.03,
            shimmer=0.16, breath=0.6, breath_base=0.5, bw=1.6, wander=30.0, hnoise=env * 0.6)
    v = wet(normalize(v), rng, rate=26.0, depth=0.45, bubbles=0.4, flange=0.5, f_lo=500, f_hi=1600)
    y = normalize(lowpass(v, 1100, 2))            # sott'acqua: gli acuti non arrivano
    for t0 in on:
        bubble_burst(y, rng, t0 + 0.05, 4, 0.06, 350, 1400, 0.25, xi=(0.4, 1.2))
    # le bolle che arrivano in superficie: plop corti e acuti, un po' dopo
    for t0 in on[1::2]:
        for _ in range(2):
            place(y, 0.18 * droplet(rng, tonal=0.9), t0 + rng.uniform(0.15, 0.3))
    return _finish(y, rng, room=0.15, lp=7000.0)


register('lampy_giggle', _giggle, 1.3, category='mon', gain=0.85, rms=-18.0, max_gr=6.0)


# ───────────────────────── prende la lenza ─────────────────────────

def _grab(s, rng):
    """Prende la lenza: il galleggiante tirato sott'acqua di colpo (un risucchio corto), il filo che si tende."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.6 * bubble(330, xi=0.5, amp=1.0, decay_mult=0.8), 0.0)
    place(y, 0.4 * splash(rng, size=0.12, dur=0.35), 0.0)
    m = ns(0.2)
    zing = bandpass(rng.standard_normal(m), 2500, 7000, 2) * curve(m, [(0, 0), (0.02, 1), (0.2, 0)])
    place(y, 0.1 * normalize(zing), 0.02)
    return _finish(y, rng, room=0.1)


register('lampy_grab', _grab, 0.5, category='mon', gain=0.6, rms=-21.0, max_gr=6.0)


# ───────────────────────── affiora sulla lenza ─────────────────────────

def _surface(s, rng):
    """Affiora sulla lenza: l'acqua che si apre e le scorre giù dalla cuffia e dal corpo ad arco, gocce, la ventosa
    che si riattacca al filo con un bacio umido, un soffio dalle due fessure del naso."""
    n = s.n
    d = s.dur
    y = np.zeros(n)
    place(y, 0.6 * splash(rng, size=0.3, dur=0.8), 0.0)
    m = ns(1.0)
    place(y, 0.32 * gush(m, rng, curve(m, [(0, 0.3), (0.15, 1.0), (0.6, 0.35), (1.0, 0)]), bubble_rate=130, f_lo=500,
                         f_hi=3500), 0.05)
    for t in poisson_times(rng, lambda tt: 22 * np.exp(-np.maximum(tt - 0.3, 0) / 0.6) + 2, 0.25, d - 0.05):
        place(y, droplet(rng, amp=rng.uniform(0.03, 0.1), tonal=0.5), t)
    place(y, 0.45 * _kiss(rng, 1.0), 0.62)
    br = tract_noise(rng, 0.35, [(0, 'n'), (0.35, 'm')], scale=BABY, amp_pts=[(0, 0), (0.12, 1), (0.35, 0)], hiss=0.5)
    place(y, 0.18 * normalize(highpass(br, 500, 2)), 0.9)
    return _finish(y, rng)


register('lampy_surface', _surface, 1.4, category='mon', gain=0.85, rms=-17.5, max_gr=6.0)


# ───────────────────────── molla la lenza ─────────────────────────

def _let(s, rng):
    """Molla la lenza: la ventosa della bocca che si stacca con uno schiocco pieno, poi quella della coda, e va giù
    di schiena (un tonfo morbido, le bolle che risalgono); il filo libero che sbatte appena sull'acqua."""
    n = s.n
    y = np.zeros(n)
    place(y, 0.7 * _kiss(rng, 1.3, dur=0.2), 0.0)
    place(y, 0.45 * _kiss(rng, 0.8, dur=0.16), 0.16)
    place(y, 0.55 * splash(rng, size=0.28, dur=0.7), 0.3)
    bubble_burst(y, rng, 0.42, 14, 0.18, 220, 1100, 0.16, xi=(0.2, 0.7))
    place(y, 0.1 * squelch(rng, 0.06, 1500, 4500, rate=60.0, density=900.0), 0.5)
    return _finish(y, rng)


register('lampy_let', _let, 1.3, category='mon', gain=0.85, rms=-17.5, max_gr=6.0)


# ───────────────────────── agganciata, risale la lenza ─────────────────────────

def _climb(s, rng):
    """L'hai agganciata: risale la lenza verso la canna a baci risucchiati, sempre più svelti (la ventosa che si
    stacca e si riattacca al filo), il filo che geme sotto il peso e la canna che scricchiola, l'acqua che le cola
    di dosso, e sotto una risatina che si stringe in un gorgoglio."""
    n = s.n
    d = s.dur
    y = np.zeros(n)
    t = 0.0
    gap = 0.2
    while t < d - 0.15:
        place(y, 0.55 * _kiss(rng, rng.uniform(0.8, 1.2)), t)
        t += gap
        gap = max(0.07, gap * 0.85)
    c = creak(rng, d, [(0, 25), (d * 0.5, 60), (d, 90)], [(0, 0), (0.1, 0.6), (d * 0.8, 1.0), (d, 0)], base=230.0,
              t60=0.07, bright=1.1, jitter=0.15)
    y += 0.25 * c
    for _ in range(10):
        place(y, droplet(rng, amp=rng.uniform(0.03, 0.08), tonal=0.4), rng.uniform(0.05, d - 0.05))
    g = vox(rng, 0.7, [(0, 520), (0.7, 380)], [(0, 'i'), (0.7, 'u')], scale=BABY, amp_pts=[(0, 0), (0.1, 1), (0.7, 0)],
            oq=0.5, jitter=0.05, shimmer=0.2, breath=0.6, bw=1.6, wander=30.0)
    place(y, 0.25 * normalize(wet_throat(g, rng, rate=24.0, depth=0.5, bubbles=0.5)), d - 0.75)
    return _finish(y, rng)


register('lampy_climb', _climb, 1.2, category='mon', gain=0.9, rms=-16.5, max_gr=6.0)


# ───────────────────────── jumpscare ─────────────────────────

def _js_lampy(s, rng):
    """Ti arriva in faccia con la ventosa spalancata: un risucchio enorme e bagnato (la bocca a disco che si attacca),
    gli anelli di denti da latte che girano come una macina (ticchettio fitto che va e viene), e il grido: una
    neonata che strilla dentro una gola bagnata, con sotto la stessa voce da una gola più grande, e la risatina che si
    rompe nello strillo."""
    n = s.n
    d = s.dur
    f0_pts = [(0, 700), (0.06, 1020), (0.45, 940), (0.85, 1060), (1.15, 900), (d, 620)]
    amp = [(0, 0.6), (0.04, 1), (1.12, 0.95), (d, 0.4)]
    baby = np.zeros(n)
    for k, det in enumerate((-13.0, 0.0, 12.0)):
        pts = [(t, f * cents(det)) for t, f in f0_pts]
        baby += (1.0 if k == 1 else 0.6) * vox(rng, d, pts, [(0, 'i'), (0.1, 'ae'), (0.9, 'a'), (d, 'ae')], scale=BABY,
                                              amp_pts=amp, oq=0.42, jitter=0.05, shimmer=0.2, sub=0.3, breath=0.55,
                                              bw=1.5, rough=0.65, rough_rate=55.0, rough_fm=60.0, wander=40.0)
    under = vox(rng, d, [(t, f * 0.43) for t, f in f0_pts], [(0, 'a'), (d, 'O')], scale=0.9, amp_pts=amp, oq=0.45,
                jitter=0.06, shimmer=0.22, sub=0.5, breath=0.6, bw=1.4, rough=0.7, rough_rate=40.0, rough_fm=55.0)
    y = normalize(baby) + 0.35 * normalize(highpass(wet_throat(under, rng, rate=20.0, depth=0.45, bubbles=0.35), 150, 2))
    # il risucchio della ventosa che si spalanca e si attacca: un vortice d'acqua e d'aria che sale
    m = ns(0.5)
    fc = curve(m, [(0, 300), (0.5, 1800)], 'log')
    suck = tv_bandpass(rng.standard_normal(m), fc, fc * 0.5) * curve(m, [(0, 0), (0.08, 1), (0.5, 0.2)])
    place(y, 0.4 * normalize(suck), 0.0)
    place(y, 0.5 * _kiss(rng, 1.6, dur=0.25), 0.02)
    # gli anelli di denti che girano: un ticchettio fitto che va e viene (due anelli in versi opposti)
    for ring, (t0, t1, rate) in enumerate([(0.1, 1.3, 70.0), (0.25, 1.2, 55.0)]):
        t = t0
        while t < t1:
            place(y, 0.12 * teeth_clack(rng, count=3, spread=0.002, glass=0.0, dur=0.05), t)
            t += 1.0 / (rate * (1 + 0.3 * np.sin(TWO_PI * 1.7 * t + ring)))
    ir = near_room(rng, 0.45, stereo_out=True)
    out = stereo(y) * np.sqrt(0.5) + 0.22 * convolve(y, ir)
    out = lowpass(highpass(out, 60, 2), 12500, 2)
    return scream_master(out, drive=2.0)


register('js_lampy', _js_lampy, 1.4, channels=2, category='mon', gain=1.0, rms=-6.6, max_gr=6.5, release=0.03)
