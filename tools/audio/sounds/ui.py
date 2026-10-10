"""
Interfaccia (stereo, brevi e discreti): legno e ottone, come gli oggetti della barca. Il passaggio del
puntatore è un tic di legno appena accennato, il clic un nottolino di legno con il fermo d'ottone,
il "indietro" lo stesso gesto al contrario, l'avvio della partita una campanella di bordo sul mare.
"""
from __future__ import annotations

from instruments import *  # noqa: F401,F403
from sounds import sound


def _tick(rng, base, t60, force=0.0003, count=6, bright=1.3, dur=0.06):
    return knock(rng, force=force, base=base, t60=t60, count=count, bright=bright, dur=dur, rough=0.05)


def _brass_click(rng, f=2900.0, dur=0.05):
    n = ns(dur)
    exc = np.zeros(n)
    exc[:2] = [1.0, -0.5]
    return normalize(modal(exc, f * np.array([1.0, 1.58, 2.31, 3.4]), [0.012, 0.009, 0.006, 0.004], [1.0, 0.6, 0.4, 0.25]))


@sound('ui_hover', 0.04, channels=2, category='ui', gain=0.5, rms=-26.0, max_gr=6.0, release=0.01)
def ui_hover(s, rng):
    y = _tick(rng, 1350.0, 0.012, force=0.00022, dur=s.dur)
    y = highpass(y, 500, 2)
    return pan(y, 0.05)


@sound('ui_click', 0.09, channels=2, category='ui', gain=0.6, rms=-21.0, max_gr=6.0, release=0.01)
def ui_click(s, rng):
    n = s.n
    y = np.zeros(n)
    place(y, _tick(rng, 520.0, 0.035, force=0.0006, count=8, bright=1.1, dur=0.09), 0.0)
    place(y, 0.35 * _brass_click(rng, 3100.0, 0.05), 0.011)
    return pan(highpass(y, 150, 2), 0.0)


@sound('ui_back', 0.11, channels=2, category='ui', gain=0.6, rms=-22.0, max_gr=6.0, release=0.01)
def ui_back(s, rng):
    n = s.n
    y = np.zeros(n)
    place(y, 0.3 * _brass_click(rng, 2500.0, 0.04), 0.0)
    place(y, _tick(rng, 410.0, 0.03, force=0.0007, count=8, bright=1.0, dur=0.08), 0.014)
    place(y, 0.55 * _tick(rng, 330.0, 0.03, force=0.0008, count=8, bright=0.9, dur=0.06), 0.052)
    return pan(highpass(y, 120, 2), -0.05)


@sound('ui_start', 1.5, channels=2, category='ui', gain=0.7, rms=-20.0)
def ui_start(s, rng):
    """Un rintocco della campanella di bordo e il mare che risponde con un'onda lunga."""
    n = s.n
    out = np.zeros((2, n))
    bell = small_bell(rng, 1046.0, n, [(0.0, 1.0), (0.012, 0.25)], t60=1.6, beat=3.0, click=0.2)
    bell = lowpass(bell, 7000, 2)
    ir = reverb_ir(1.4, rng, lo=1.0, hi=0.5, attack=0.01, sparse=0.5, lp=6000,
                   early=[(0.09, 0.3, 0.5), (0.17, 0.2, -0.5)])
    out += 0.7 * pan(bell, 0.1) + 0.35 * convolve(bell, ir)
    # l'onda: un fruscio che sale e si ritira da sinistra a destra
    for c, sh in enumerate((0.0, 0.08)):
        m = n
        w = spectral_noise(m, rng, lambda f: bw_bp(f, 150, 3500, 2), exponent=0.8)
        env = curve(m, [(0, 0), (0.15 + sh, 0.0), (0.7 + sh, 1.0), (1.5, 0.0)])
        out[c] += 0.16 * w * env / (np.max(np.abs(w)) + 1e-9) * 2.5
    nb = ns(1.2)
    place(out, stereo(0.18 * lowpass(rng.standard_normal(nb), 120, 2) * curve(nb, [(0, 0), (0.5, 1), (1.2, 0)])), 0.15)
    return highpass(out, 40, 2)


@sound('ui_page', 0.55, channels=2, category='ui', gain=0.6, rms=-22.0, max_gr=6.0)
def ui_page(s, rng):
    """Si gira una pagina del Catalogo: la carta spessa che si stacca dalla pila (un fruscio che sale), l'aria
    che la pagina sposta mentre passa sopra, qualche crepitio della carta vecchia, poi la pagina che si posa."""
    n = s.n
    out = np.zeros((2, n))
    # fruscio della carta: rumore in banda che segue la velocità della pagina (sale e scende), da destra a sinistra
    v = curve(n, [(0, 0.0), (0.05, 0.35), (0.22, 1.0), (0.4, 0.45), (0.55, 0.0)])
    for c, (p0, p1) in enumerate(((0.35, -0.25), (0.55, -0.05))):
        sw = tv_bandpass(rng.standard_normal(n), 900 + 3200 * v, (900 + 3200 * v) * 0.9) * v ** 1.4
        out[c] += 0.55 * normalize(sw) * (1.0 - 0.3 * c)
    # crepitii della carta (micro-scatti fitti all'inizio)
    cr = crinkle(rng, 0.3, [(0, 0.6), (0.06, 1.0), (0.18, 0.3), (0.3, 0.0)], density=900, f_lo=1500, f_hi=7000, res=3200, swish=0.1)
    place(out, stereo(0.28 * cr), 0.02)
    # la pagina che si posa: un colpetto morbido e sordo
    nb = ns(0.12)
    thud = lowpass(rng.standard_normal(nb), 380, 2) * exp_env(nb, 0.06, attack=0.004)
    place(out, stereo(0.35 * normalize(thud)), 0.4)
    return highpass(out, 90, 2)
