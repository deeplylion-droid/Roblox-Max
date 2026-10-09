"""
Modelli per i versi e i rumori del corpo delle creature di SPLASHLAND IS CLOSED!, costruiti su dsp.py
e instruments.py (solo numpy + scipy, nessun campione esterno):
  - voce: sorgente glottale irregolare (jitter e shimmer che cambiano nel tempo, diplofonia, fry),
    ruvidità da urlo (modulazione a 30–150 Hz), gole enormi (formanti basse) o da bambina (formanti alte),
    raddoppi "sbagliati" sotto la voce, respiri attraverso il tratto vocale;
  - gola bagnata: gargarismi, bolle, deglutizioni;
  - ossa, denti e mascelle: schiocchi, morsi, masticazione;
  - superfici: nocche sul fasciame, passi bagnati sul pagliolo, unghie che grattano, gomma che cigola;
  - naso: annusate umide.
Ogni funzione riceve un np.random.Generator: a parità di seme il risultato è identico.
"""
from __future__ import annotations

import numpy as np
from scipy import signal

from instruments import *  # noqa: F401,F403
from dsp import SR, NYQ, TWO_PI


# ═════════════════════════ VOCE ═════════════════════════

def glottal_tv(f0, rng, oq=0.6, sq=2.5, jitter=0.01, shimmer=0.05, sub=0.0, os_: int = 4):
    """Sorgente glottale di Rosenberg come dsp.glottal, ma jitter, shimmer, oq e sub possono essere curve
    per campione: la voce può "rompersi" (tratti caotici dell'urlo, crepe del pianto, fry).
    Restituisce (eccitazione = derivata del flusso, flusso)."""
    f0 = np.asarray(f0, dtype=float)
    n = len(f0)
    m = n * os_
    tt = (np.arange(m) + 0.5) / os_ - 0.5
    src_t = np.arange(n)
    fo = np.interp(tt, src_t, f0)
    ph0 = np.cumsum(fo) / (SR * os_)
    ncyc = int(ph0[-1]) + 3
    # campione d'inizio di ogni ciclo nominale: lì si leggono le curve di jitter
    starts = np.clip((np.searchsorted(ph0, np.arange(ncyc)) / os_).astype(np.int64), 0, n - 1)
    jit_c = np.broadcast_to(np.asarray(jitter, dtype=float), (n,))[starts]
    jit = 1.0 + jit_c * np.clip(rng.standard_normal(ncyc), -2.5, 2.5)
    fo = fo * jit[np.minimum(ph0.astype(np.int64), ncyc - 1)]
    ph = np.cumsum(fo) / (SR * os_)
    cyc = ph.astype(np.int64)
    fr = ph - cyc
    nc = int(cyc[-1]) + 2
    oq_a = np.interp(tt, src_t, np.broadcast_to(np.asarray(oq, dtype=float), (n,)))
    tp = oq_a * sq / (1.0 + sq)
    tn = oq_a / (1.0 + sq)
    g = np.where(fr < tp, 0.5 * (1.0 - np.cos(np.pi * fr / tp)),
                 np.where(fr < tp + tn, np.cos(np.pi * (fr - tp) / (2.0 * tn)), 0.0))
    cstart = np.clip((np.searchsorted(ph, np.arange(nc)) / os_).astype(np.int64), 0, n - 1)
    shi_c = np.broadcast_to(np.asarray(shimmer, dtype=float), (n,))[cstart]
    amp = np.maximum(1.0 + shi_c * np.clip(rng.standard_normal(nc), -2.5, 2.5), 0.03)
    g = g * amp[cyc]
    if np.any(np.asarray(sub) != 0):
        sub_a = np.interp(tt, src_t, np.broadcast_to(np.asarray(sub, dtype=float), (n,)))
        g = g * (1.0 - sub_a * (cyc % 2))
    d = np.diff(g, prepend=0.0) * (SR * os_) / np.maximum(fo, 1.0)
    exc = signal.resample_poly(d, 1, os_)[:n]
    flow = signal.resample_poly(g, 1, os_)[:n]
    return exc, flow


def rough_mod(n: int, rng, rate=70.0, depth=0.5, wobble=0.25):
    """Modulazione 'ruvida' (la firma degli urli: modulazioni d'ampiezza fra 30 e 150 Hz).
    rate e depth possono essere curve; wobble = quanto vaga la frequenza (frazione)."""
    rate = np.broadcast_to(np.asarray(rate, dtype=float), (n,))
    depth = np.broadcast_to(np.asarray(depth, dtype=float), (n,))
    f = rate * (1.0 + wobble * np.tanh(rand_curve(n, 7.0, rng)))
    ph = phase_of(f) + rng.uniform(0, 1)
    m = (0.5 + 0.5 * np.cos(TWO_PI * ph)) ** 1.6
    return 1.0 - depth * m


def vox(rng, dur, f0_pts=None, vowels=((0.0, '@'),), scale=1.0, amp_pts=None, *, f0=None, oq=0.6, sq=2.5,
        jitter=0.012, shimmer=0.06, sub=0.0, breath=0.12, breath_base=0.35, vib=(0.0, 5.5), wander=0.0,
        rough=0.0, rough_rate=70.0, rough_fm=0.0, bw=1.0, nform=5, voicing=None, hnoise=None, fjit=35.0):
    """Voce a formanti con sorgente irregolare. f0_pts: contorno [(t, Hz)] (interpolato in scala log)
    oppure f0 già pronta per campione; vowels: [(t, vocale)] (vedi dsp.VOWELS); scale: scala delle
    formanti (> 1 tratto corto da bambina, < 1 gola enorme), anche curva; jitter, shimmer, sub, oq anche
    curve. rough: profondità della modulazione 'ruvida' (anche curva); rough_fm: la stessa modulazione
    sull'intonazione (centesimi, anche curva: le armoniche si sfrangiano come negli urli veri). voicing: quanto vibrano le corde
    (curva, 0 = solo fiato); hnoise: soffio non modulato (le 'h' delle risate e dei singhiozzi), curva;
    fjit: tremolio casuale delle formanti (centesimi): l'articolazione vera non sta mai ferma.
    Uscita normalizzata."""
    n = ns(dur)
    if f0 is None:
        f0 = curve(n, f0_pts, 'log')
    f0 = np.asarray(f0, dtype=float)[:n]
    t = tvec(n)
    if vib[0]:
        f0 = f0 * cents(vib[0] * np.sin(TWO_PI * vib[1] * t + rng.uniform(0, TWO_PI)))
    if wander:
        f0 = f0 * cents(wander * rand_curve(n, 3.0, rng))
    if np.any(np.asarray(rough_fm) != 0):
        fr = rough_rate * (1.0 + 0.3 * np.tanh(rand_curve(n, 5.0, rng)))
        f0 = f0 * cents(np.asarray(rough_fm) * np.sin(TWO_PI * phase_of(fr) + rng.uniform(0, TWO_PI))
                        * (0.6 + 0.4 * np.abs(rand_curve(n, 9.0, rng))))
    exc, flow = glottal_tv(f0, rng, oq=oq, sq=sq, jitter=jitter, shimmer=shimmer, sub=sub)
    exc = exc / (np.max(np.abs(exc)) + 1e-9)
    if voicing is not None:
        exc = exc * np.asarray(voicing)[:n]
    src = exc + np.asarray(breath) * aspiration(flow, rng, breath_base)
    if hnoise is not None:
        src = src + np.asarray(hnoise)[:n] * 0.5 * highpass(rng.standard_normal(n), 400.0)
    if amp_pts is not None:
        src = src * (curve(n, amp_pts) if isinstance(amp_pts, (list, tuple)) else amp_pts)
    F, B = formant_track(n, list(vowels), scale, bw)
    if fjit:
        F = F * cents(fjit * np.stack([rand_curve(n, 6.0 + 2.0 * k, rng) for k in range(F.shape[0])]))
    y = formant_cascade(src, F[:nform], B[:nform])
    if np.any(np.asarray(rough) != 0):
        y = y * rough_mod(n, rng, rough_rate, rough)
    return normalize(y)


def tract_noise(rng, dur, vowels=((0.0, 'a'),), scale=1.0, amp_pts=None, bw=1.6, hiss=0.15, nform=4):
    """Fiato che passa per il tratto vocale (respiri, sospiri, soffi): rumore filtrato dalle formanti
    della vocale (bocca aperta o chiusa), più un filo di sibilo alto."""
    n = ns(dur)
    nz = rng.standard_normal(n)
    F, B = formant_track(n, list(vowels), scale, bw)
    y = formant_parallel(nz, F[:nform], B[:nform], [1.0, 0.7, 0.4, 0.25][:nform])
    y = normalize(y) + hiss * normalize(highpass(nz, 3500))
    if amp_pts is not None:
        y = y * (curve(n, amp_pts) if isinstance(amp_pts, (list, tuple)) else amp_pts)
    return y


def saliva(rng, dur, rate=60.0, amp=1.0, f_lo=1200.0, f_hi=6000.0, env_pts=None):
    """Crepitio di saliva o di muco: micro-scoppi di bollicine e filamenti che si staccano."""
    n = ns(dur)
    y = np.zeros(n)
    env = curve(n, env_pts) if env_pts else np.ones(n)
    t_ = tvec(n)
    for tc in poisson_times(rng, lambda tt: rate * np.interp(tt, t_, env) + 1e-6, 0.0, dur):
        if rng.random() < 0.55:
            k = max(4, ns(rng.uniform(0.0002, 0.0012)))
            g = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 3.0))
        else:
            g = bubble(float(loguniform(rng, f_lo, f_hi)), rng.uniform(0.0, 0.25), 1.0, decay_mult=rng.uniform(0.8, 2.0),
                       max_dur=0.02)
        place(y, g * rng.lognormal(0, 0.6) * np.interp(tc, t_, env), tc)
    return amp * normalize(bandpass(y, f_lo * 0.7, min(f_hi * 1.4, NYQ * 0.9)))


def throat_bubbles(rng, dur, rate=40.0, f_lo=140.0, f_hi=700.0, env_pts=None, xi=(0.0, 0.18)):
    """Bolle in una gola piena d'acqua (gorgoglio): bolle grandi e basse, poca salita di tono."""
    n = ns(dur)
    y = np.zeros(n)
    env = curve(n, env_pts) if env_pts else np.ones(n)
    t_ = tvec(n)
    for tb in poisson_times(rng, lambda tt: rate * np.interp(tt, t_, env) + 1e-6, 0.0, dur):
        f = float(loguniform(rng, f_lo, f_hi))
        b = bubble(f, rng.uniform(*xi), rng.lognormal(0, 0.45) * (f_lo / f) ** 0.2, decay_mult=rng.uniform(0.45, 0.9),
                   max_dur=0.25)
        place(y, b * np.interp(tb, t_, env), tb)
    return normalize(y)


def lip_flutter(x, rng, rate=24.0, depth=0.75):
    """Labbra (o branchie) molli che sbattono nel fiato: modulazione a impulsi irregolari."""
    n = len(x)
    m = rough_mod(n, rng, rate, depth, wobble=0.35)
    return x * m


def ghost_double(x_fn, ratio=0.5, level=0.25):
    """Raddoppio 'sbagliato': la stessa frase detta da una gola più grande, sotto. x_fn(ratio) → segnale."""
    return level * x_fn(ratio)


def tape_bend(x, pts):
    """Cambio di velocità come un nastro (anche il tono): pts [(t, rapporto)] sul tempo d'uscita."""
    n = len(x)
    r = curve(n, pts, 'log')
    pos = np.concatenate([[0.0], np.cumsum(r)[:-1]])
    return frac_read(x, np.minimum(pos, n - 1.001))


# ═════════════════════════ OSSA, DENTI, MASCELLE ═════════════════════════

def bone_crack(rng, size=1.0, dur=0.3, bright=1.0):
    """Schiocco d'osso o di cartilagine: grappolo di micro-fratture in pochi ms (risonanze medio-acute)
    e il colpo sordo del pezzo che si sposta. size 0..1."""
    n = ns(dur)
    y = np.zeros(n)
    k_hits = int(rng.integers(2, 5 + int(4 * size)))
    t = 0.0
    for i in range(k_hits):
        g = max(3, ns(rng.uniform(0.0002, 0.0009)))
        imp = rng.standard_normal(g) * np.exp(-np.arange(g) / (g / 3.0))
        f = rng.uniform(900, 2600) * bright
        body = modal(np.pad(imp, (0, ns(0.03))), [f, f * rng.uniform(1.6, 2.3), f * rng.uniform(2.9, 3.8)],
                     [0.008, 0.005, 0.003], [1.0, 0.6, 0.35])
        place(y, (normalize(body) * 0.7 + 0.5 * normalize(np.pad(imp, (0, ns(0.03))))) * rng.uniform(0.4, 1.0) * (1.0 if i == 0 else 0.7),
              t)
        t += rng.exponential(0.004 + 0.006 * size)
    # il pezzo che si sposta: tonfo basso e corto
    nt = ns(0.12)
    th = lowpass(rng.standard_normal(nt), 260 + 200 * (1 - size), 2) * exp_env(nt, 0.05 + 0.05 * size, attack=0.001)
    place(y, (0.25 + 0.6 * size) * normalize(th), 0.0005)
    return normalize(y)


def teeth_clack(rng, count=12, spread=0.008, glass=0.0, dur=0.3):
    """Denti che sbattono (tanti aghi che si incontrano quasi insieme). glass > 0: denti di vetro che
    tintinnano (modi alti e lunghi)."""
    n = ns(dur)
    y = np.zeros(n)
    for _ in range(count):
        t = abs(rng.normal(0, spread))
        g = max(3, ns(rng.uniform(0.00015, 0.0005)))
        imp = np.zeros(ns(0.06))
        imp[:g] = rng.standard_normal(g) * np.exp(-np.arange(g) / (g / 3.0))
        f = float(loguniform(rng, 2200, 6500))
        T = 0.004 + glass * rng.uniform(0.03, 0.12)
        ring = modal(imp, [f, f * rng.uniform(1.4, 1.9), f * rng.uniform(2.3, 2.9)], [T, T * 0.7, T * 0.5],
                     [1.0, 0.5 + 0.4 * glass, 0.3])
        place(y, (normalize(ring) * (0.5 + 0.5 * glass) + 0.6 * normalize(imp)) * rng.lognormal(0, 0.4), t)
    return normalize(highpass(y, 900, 2))


def squish(rng, dur=0.18, f_lo=250.0, f_hi=1600.0, density=900.0, sticky=0.5):
    """Carne bagnata che si comprime (masticazione, ventose, passi): risucchio basso e appiccicoso."""
    y = squelch(rng, dur, f_lo, f_hi, rate=45.0, density=density)
    if sticky:
        # filamenti di saliva che si staccano alla fine
        place(y, sticky * 0.5 * saliva(rng, dur * 0.6, rate=90, f_lo=1500, f_hi=5000), dur * 0.35)
    return y


def crunch(rng, dur=0.08, density=500.0, f_lo=1500.0, f_hi=7000.0):
    """Lische e cartilagini che si spezzano: nuvola fitta di micro-schiocchi secchi."""
    n = ns(dur)
    y = np.zeros(n)
    for tc in poisson_times(rng, density, 0.0, dur):
        k = max(3, ns(rng.uniform(0.0001, 0.0006)))
        g = rng.standard_normal(k) * np.exp(-np.arange(k) / (k / 2.5))
        place(y, g * rng.lognormal(0, 0.8), tc)
    y = bandpass(y, f_lo, f_hi, 2) + 0.4 * resonate(y, rng.uniform(1800, 3200), 2.5)
    env = curve(n, [(0, 0), (0.003, 1), (dur * 0.5, 0.7), (dur, 0)])
    return normalize(y * env)


def gulp(rng, size=1.0, dur=0.7):
    """Deglutizione: il bolo spinto dalla lingua (schiocco umido), la sacca d'aria che si chiude in gola
    ('glunk' grave con il tono che SCENDE) e un secondo 'gloop' più giù. size 1 = gigante."""
    n = ns(dur)
    y = np.zeros(n)
    # la lingua che spinge: schiocco umido
    place(y, 0.35 * squish(rng, 0.07, 600, 2500, density=1500, sticky=0.3), 0.0)
    # 'glunk': risonanza grave con caduta di tono (sacca d'aria schiacciata nella gola)
    for t0, f_a, f_b, d, a in [(0.035, 210.0, 105.0, 0.16, 1.0), (0.2 + 0.05 * size, 150.0, 82.0, 0.22, 0.7)]:
        m = ns(d)
        f_a /= (0.6 + 0.6 * size)
        f_b /= (0.6 + 0.6 * size)
        f = curve(m, [(0, f_a), (d * 0.35, f_b), (d, f_b * 0.95)], 'log')
        tone = osc(f) * exp_env(m, d * 0.55, attack=0.003)
        tone += 0.4 * osc(f * 2.02) * exp_env(m, d * 0.3, attack=0.002)
        nz = lowpass(rng.standard_normal(m), 500, 2) * exp_env(m, d * 0.4, attack=0.002)
        place(y, a * (normalize(tone) + 0.35 * normalize(nz)), t0)
    # bolle che risalgono dopo il passaggio
    place(y, 0.25 * throat_bubbles(rng, 0.35, rate=25, f_lo=110 / size ** 0.3, f_hi=420), 0.25)
    return normalize(lowpass(y, 4000, 2))


# ═════════════════════════ SUPERFICI ═════════════════════════

HULL_PLANK = 205.0      # modo più basso del fasciame visto dall'esterno (Hz)


def knuckle_knock(rng, force=0.001, base=HULL_PLANK, dur=0.5, wet_amt=0.3, hard=1.0):
    """Nocche lunghe sul fasciame dello scafo: contatto duro e breve (le ossa), le tavole che risuonano,
    l'aria della barca che rimbomba appena, un velo d'acqua (le nocche sono bagnate)."""
    n = ns(dur)
    y = knock(rng, force=force, base=base * rng.uniform(0.96, 1.04), t60=0.085, count=9, bright=1.15, dur=dur,
              rough=0.12, cavity=(rng.uniform(108, 122), 0.2, 0.55))
    # il 'tic' osseo del contatto
    k = ns(0.004)
    tick = bandpass(rng.standard_normal(k), 1800, 9000) * np.exp(-np.arange(k) / (k / 4.0))
    y[:k] += 0.45 * hard * normalize(tick)
    if wet_amt:
        place(y, wet_amt * 0.25 * squish(rng, 0.05, 900, 3500, density=1200, sticky=0.0), 0.002)
    return normalize(y)


def nail_scrape(rng, dur=0.6, pts=None, env_pts=None, base=420.0):
    """Unghie che grattano sulle tavole: attrito a scatti veloci (stick-slip acuto e irregolare) che
    eccita le tavole, più il fruscio del legno ruvido."""
    n = ns(dur)
    rate = curve(n, pts or [(0, 260), (dur * 0.3, 520), (dur, 380)], 'log') * cents(80 * rand_curve(n, 14.0, rng))
    amp = curve(n, env_pts or [(0, 0), (0.03, 1), (dur * 0.7, 0.8), (dur, 0)])
    amp = amp * (0.6 + 0.4 * np.abs(np.tanh(2 * rand_curve(n, 25.0, rng))))
    exc = stick_slip(n, rng, rate, amp, jitter=0.18, grain=0.0002)
    f, T, g = wood_modes(rng, base, 9, 0.03, 1.4)
    y = normalize(modal(exc, f, T, g)) + 0.35 * normalize(highpass(exc, 2500))
    hiss = bandpass(rng.standard_normal(n), 1500, 8000) * amp
    return normalize(y + 0.2 * normalize(hiss))


def wet_footstep(rng, weight=1.0, dur=0.7, claws=0.0, creak_amt=0.5):
    """Passo pesante di un piede palmato e bagnato sul pagliolo: tallone e pianta che schiaffeggiano il legno
    (due contatti), la tavola che flette e geme, lo scafo che rimbomba, gocce, il risucchio quando si stacca."""
    n = ns(dur)
    y = np.zeros(n)
    # tallone e pianta (pelle bagnata su legno)
    t_ball = rng.uniform(0.035, 0.07)
    place(y, wet_slap(rng, size=0.8 * weight, surface='wood', dur=0.4, wood_base=125.0, drops=0.5), 0.0)
    place(y, 0.7 * wet_slap(rng, size=0.55 * weight, surface='wood', dur=0.35, wood_base=150.0, drops=0.4), t_ball)
    # il peso: tonfo grave dello scafo
    nt = ns(0.35)
    th = lowpass(rng.standard_normal(nt), 160, 2) * exp_env(nt, 0.16, attack=0.004)
    th = th + 0.8 * osc(curve(nt, [(0, 95), (0.15, 72)], 'log')) * exp_env(nt, 0.2, attack=0.003) * rng.uniform(0.6, 1.0)
    place(y, 0.55 * weight * normalize(th), 0.004)
    # la tavola che flette sotto il peso
    if creak_amt:
        d = rng.uniform(0.18, 0.32)
        c = creak(rng, d, [(0, rng.uniform(25, 40)), (d * 0.5, rng.uniform(45, 80)), (d, rng.uniform(25, 45))],
                  [(0, 0), (0.03, 1), (d * 0.6, 0.7), (d, 0)], base=rng.uniform(140, 190), t60=0.09, bright=0.8,
                  jitter=0.12)
        place(y, creak_amt * 0.3 * c, t_ball + rng.uniform(0.0, 0.05))
    # artigli che toccano le tavole
    if claws:
        for _ in range(int(rng.integers(2, 4))):
            k = knock(rng, force=0.0004, base=rng.uniform(600, 900), t60=0.03, count=6, bright=1.5, dur=0.06)
            place(y, claws * 0.18 * k, t_ball + rng.uniform(0.005, 0.03))
    # il piede che si stacca: risucchio appiccicoso
    place(y, 0.22 * squish(rng, rng.uniform(0.09, 0.15), 350, 2200, density=900, sticky=0.6),
          rng.uniform(0.3, 0.42))
    # acqua che cola dal corpo
    for _ in range(int(rng.integers(3, 7))):
        place(y, droplet(rng, amp=rng.uniform(0.02, 0.07)), rng.uniform(0.05, dur - 0.1))
    return normalize(y)


def rubber_squeal(rng, dur=0.8, rate_pts=None, env_pts=None, bright=1.0):
    """Gomma bagnata tesa che sfrega sulla pelle (il salvagente a paperella che stringe il collo):
    stick-slip acuto e instabile filtrato da risonanze morbide della gomma."""
    n = ns(dur)
    rate = curve(n, rate_pts or [(0, 380), (dur * 0.4, 620), (dur, 430)], 'log')
    rate = rate * cents(120 * rand_curve(n, 9.0, rng))
    amp = curve(n, env_pts or [(0, 0), (0.05, 1), (dur * 0.6, 0.8), (dur, 0)])
    amp = amp * np.clip(0.5 + 0.6 * rand_curve(n, 16.0, rng), 0.05, 1.3)
    exc = stick_slip(n, rng, rate, amp, jitter=0.07, grain=0.0006)
    y = (resonate(exc, 950 * bright, 2.2) + 0.7 * resonate(exc, 1900 * bright, 3.0) + 0.35 * resonate(exc, 3100 * bright, 3.5)
         + 0.25 * lowpass(exc, 600))
    return normalize(lowpass(y, 6000, 2))


def squeaker(rng, dur=0.45, f_pts=None, breath_amt=0.6, env_pts=None):
    """Il fischietto di gomma di una paperella schiacciata male (ancia che fischia con poca aria):
    tono instabile, molto soffio."""
    n = ns(dur)
    f = curve(n, f_pts or [(0, 1250), (dur * 0.25, 1750), (dur, 1350)], 'log') * cents(45 * rand_curve(n, 11.0, rng))
    ph = phase_of(f)
    reed = np.sin(TWO_PI * ph) + 0.35 * np.sin(2 * TWO_PI * ph + 0.4) + 0.12 * np.sin(3 * TWO_PI * ph)
    reed = np.tanh(1.8 * reed)
    air = tv_bandpass(rng.standard_normal(n), f, f / 4.0)
    env = curve(n, env_pts or [(0, 0), (0.04, 1), (dur * 0.55, 0.75), (dur, 0)])
    stall = np.clip(0.55 + 0.7 * rand_curve(n, 20.0, rng), 0.0, 1.0)     # l'ancia che si inceppa
    y = (0.6 * reed * stall + breath_amt * normalize(air) + 0.25 * normalize(highpass(rng.standard_normal(n), 2500))) * env
    return normalize(bandpass(y, 500, 7000, 2))


def big_sniff(rng, dur=0.28, f=1.0, wet_amt=0.5):
    """Un'annusata forte e breve da narici grandi e bagnate: soffio aspirato con risonanze nasali,
    crepitio di muco, finale secco."""
    n = ns(dur)
    nz = rng.standard_normal(n)
    y = (0.6 * resonate(nz, 1250 * f, 2.5) + 0.55 * resonate(nz, 2300 * f, 3.0) + 0.35 * resonate(nz, 3900 * f, 3.0)
         + 0.2 * highpass(nz, 1800))
    env = curve(n, [(0, 0), (0.02, 0.5), (dur * 0.7, 1.0), (dur - 0.012, 0.95), (dur, 0)])
    y = normalize(y) * env
    if wet_amt:
        y += wet_amt * 0.35 * saliva(rng, dur, rate=180, f_lo=900, f_hi=4500, env_pts=[(0, 0.2), (dur, 1)])
    return y


# ═════════════════════════ AMBIENTE RAVVICINATO ═════════════════════════

def near_room(rng, rt60=0.35, stereo_out=False):
    """Spazio aperto sul mare a un passo dalla barca: poche prime riflessioni (scafo, acqua) e una coda
    cortissima. Le creature non sono in una stanza: serve solo a togliere la secchezza da studio."""
    return reverb_ir(rt60, rng, lo=0.9, hi=0.45, attack=0.004, sparse=0.3, lp=6000, stereo_out=stereo_out,
                     early=[(0.006, 0.5, -0.3), (0.013, 0.35, 0.4), (0.021, 0.2, 0.1)])


def roomify(x, rng, wet=0.18, rt60=0.35):
    """Aggiunge lo spazio ravvicinato a un suono mono (resta mono, lunghezza invariata)."""
    ir = near_room(rng, rt60, stereo_out=False)
    return x + wet * convolve(x, ir)


def wet_throat(x, rng, rate=22.0, depth=0.55, bubbles=0.4, flange=0.45, f_lo=130.0, f_hi=650.0, width=0.01):
    """Gola piena d'acqua: il flusso interrotto dalle bolle (gargarismo), un pettine acquoso che vaga e
    bolle basse che scoppiano dove il fiato è forte (poca salita di tono: niente 'bloop' da cartone)."""
    n = len(x)
    g, times = gargle(n, rng, rate, depth, width)
    y = x * g
    if flange:
        y = flanger(y, rng, base_ms=1.8, depth_ms=0.9, rate=1.0, mix=flange)
    if bubbles:
        env = lowpass(np.abs(x), 20.0)
        env /= np.max(env) + 1e-9
        pk = np.max(np.abs(x))
        for t in times:
            if rng.random() < 0.7:
                i = min(int(t * SR), n - 1)
                f = float(loguniform(rng, f_lo, f_hi))
                b = bubble(f, xi=rng.uniform(0.0, 0.15), amp=bubbles * env[i] * pk * rng.uniform(0.4, 1.0),
                           decay_mult=rng.uniform(0.5, 0.9), max_dur=0.2)
                place(y, b, t)
    return y


# ═════════════════════════ DINAMICA ═════════════════════════

def compress(x, thr_db=-18.0, ratio=4.0, attack=0.004, release=0.08, knee=6.0, block: int = 32):
    """Compressore a rilevatore RMS (a blocchi): abbassa le punte di un urlo e alza il corpo, così il
    jumpscare arriva forte senza che il limitatore debba schiacciarlo. thr_db è relativo al picco RMS."""
    m = x if x.ndim == 1 else np.sqrt(np.mean(x ** 2, axis=0))
    n = len(m)
    nb = (n + block - 1) // block
    p = np.concatenate([m ** 2, np.zeros(nb * block - n)]).reshape(nb, block).mean(axis=1)
    ra = np.exp(-block / (attack * SR))
    rr = np.exp(-block / (release * SR))
    env = np.empty(nb)
    e = p[0]
    for i in range(nb):
        r = ra if p[i] > e else rr
        e = r * e + (1 - r) * p[i]
        env[i] = e
    ed = 10 * np.log10(env + 1e-20)
    thr = ed.max() + thr_db
    over = ed - thr
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 - 1 / ratio),
                           (1 - 1 / ratio) * (over + knee / 2) ** 2 / (2 * knee)))
    g = db_to_lin(-gr)
    centers = np.arange(nb) * block + (block - 1) / 2.0
    gs = np.interp(np.arange(n), centers, g)
    return x * gs


def pulses(n: int, onsets, durs, att=0.012, rel=0.03, levels=None) -> np.ndarray:
    """Inviluppo a impulsi (sillabe di una risata, singhiozzi): somma di trapezi raccordati."""
    out = np.zeros(n)
    for i, (t0, d) in enumerate(zip(onsets, durs)):
        a = 1.0 if levels is None else levels[i]
        out = np.maximum(out, a * gate_env(n, t0, t0 + max(d - rel, att), att, rel))
    return out


def phase_rotate(x, freqs=(70.0, 150.0, 330.0, 700.0, 1500.0, 3100.0), q=0.5):
    """Rotatore di fase (cascata di passa-tutto del secondo ordine): lo spettro resta identico, ma gli
    impulsi glottali si 'spalmano' nel tempo e il fattore di cresta scende di qualche dB (il trucco delle
    radio per avere voci forti senza distorcerle)."""
    y = x
    for f in freqs:
        w = TWO_PI * f / SR
        al = np.sin(w) / (2 * q)
        b = np.array([1 - al, -2 * np.cos(w), 1 + al])
        a = np.array([1 + al, -2 * np.cos(w), 1 - al])
        y = signal.lfilter(b / a[0], a / a[0], y, axis=-1)
    return y


def _bands(x, edges=(300.0, 2400.0)):
    """Divide un segnale in bande complementari (filtri a fase zero: la somma ridà il segnale)."""
    out = []
    prev = None
    for fc in edges:
        lo = fft_filter(x, lambda f, fc=fc: 1.0 / np.sqrt(1.0 + (f / fc) ** 8))
        out.append(lo if prev is None else lo - prev)
        prev = lo
    out.append(x - prev)
    return out


def scream_master(x, thr_db=-24.0, ratio=6.0, drive=1.6, rotate=2, multiband=True):
    """Catena finale degli urli dei jumpscare: rotazione di fase (cresta più bassa senza toccare il timbro),
    compressione forte ma non schiacciata, poi una saturazione morbida che smussa le ultime punte: arrivano
    a −7 dBFS RMS senza clipping digitale."""
    y = x
    for _ in range(rotate):
        y = phase_rotate(y)
    y = compress(normalize(y), thr_db=thr_db, ratio=ratio, attack=0.002, release=0.05)
    if multiband:
        # saturazione per bande (come i processori delle radio): i bassi non sporcano gli acuti
        parts = []
        for b in _bands(normalize(y)):
            b = compress(b, thr_db=-12.0, ratio=4.0, attack=0.002, release=0.04)
            parts.append(softclip(normalize(b), 1.8, asym=0.03))
        y = parts[0] * 0.8 + parts[1] + parts[2] * 0.7
    y = compress(normalize(y), thr_db=-10.0, ratio=4.0, attack=0.001, release=0.02)
    return softclip(normalize(y) * 1.2, drive, asym=0.04)
