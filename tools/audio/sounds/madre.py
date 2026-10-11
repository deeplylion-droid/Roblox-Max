"""
La Madre (notte 6, il finale): Mama Marina, la balena-mamma della mascotte di Splashland diventata mostro. È enorme,
molto più grande della barca, e non parla: al massimo canticchia la sua ninna nanna senza parole (la stessa del
carillon, mus_title). Per tutta la notte la sua ombra gira lontana attorno alla barca e ogni tanto la si sente
chiamare dal fondo; tre volte si avvicina e passa sotto lo scafo (bisogna restare immobili). Se ti muovi ti prende
dal basso. All'alba (finale A) sale accanto alla barca con tutti i suoi figli, prende il secchio e torna giù.

La sua voce è una gola più grande di tutte (formanti a ×0,38, come il lamento di mus_madre) con una seconda gola
sotto, a un intervallo appena più stretto di un'ottava (suona sbagliato, come le voci doppie dei figli); sott'acqua
arriva scura, con le eco del fondo e della superficie e una coda lunghissima. I richiami lontani sono mono (il gioco
li mette dove sta l'ombra sul sonar); tutto il resto la circonda ed è stereo.
"""
from __future__ import annotations

from creatures import *  # noqa: F401,F403
from sounds import register
from sounds.ambience import sea_texture
from sounds.fishing import _hit, _shell_modes
from sounds.music import MELODY
from sounds.world import boat_creak

WHALE = 0.38        # scala delle formanti: la gola più grande che ci sia
UNDER = 0.485       # la seconda gola: appena meno di un'ottava sotto (mai esatta)
DOWN = 36           # la ninna nanna canticchiata tre ottave sotto il carillon (Mi5 → Mi2, La4 → La1)
BOY = 1.36          # i figli: formanti da bambino
LULL_BEAT = 1.4     # la ninna nanna della Madre: 3/4 a circa 43 al minuto (il carillon va a 67,5)
LULL_A = MELODY[:16]   # la prima frase della ninna nanna (battute 1–8 di mus_title)


def _at(x, db):
    """Porta uno strato al suo livello (RMS "attivo", dBFS) prima di mescolarlo: gli strati si bilanciano fra loro,
    il livello finale lo fissa master.py."""
    return x * db_to_lin(db - active_rms_db(x))


# ───────────────────────── la voce ─────────────────────────

def _whale(rng, dur, f0_pts=None, vowels=((0.0, 'u'),), amp_pts=None, *, f0=None, rough=0.2, rough_rate=13.0,
           sub=0.3, breath=0.05, scale=WHALE, wander=8.0, under=0.35):
    """La voce della Madre: una gola enorme (formanti bassissime e larghe), sorgente quasi regolare ma con un
    battito lento e ruvido (le pulsazioni dei versi delle balene, 10–20 al secondo), le subarmoniche; sotto, la
    stessa voce da una seconda gola a poco meno di un'ottava. Un filo di saturazione fa uscire le armoniche, così
    la si sente anche dove i bassi non arrivano. Uscita normalizzata."""
    kw = dict(scale=scale, amp_pts=amp_pts, oq=0.72, sq=2.0, jitter=0.004, shimmer=0.04, sub=sub, breath=breath,
              bw=1.6, wander=wander, rough=rough, rough_rate=rough_rate, fjit=15.0)
    if f0 is not None:
        y = vox(rng, dur, None, list(vowels), f0=f0, **kw)
        lo = vox(rng, dur, None, list(vowels), f0=np.asarray(f0) * UNDER, **{**kw, 'scale': scale * 0.85, 'rough': 0.0})
    else:
        y = vox(rng, dur, f0_pts, list(vowels), **kw)
        lo = vox(rng, dur, [(t, f * UNDER) for t, f in f0_pts], list(vowels), **{**kw, 'scale': scale * 0.85, 'rough': 0.0})
    y = normalize(y) + under * normalize(lo)
    y = y + 0.25 * softclip(normalize(lowpass(y, 400, 2)), 2.5)
    return normalize(y)


def _underwater(x, rng, dist=1.0, rt60=3.6, tail=True):
    """Sott'acqua e lontano (mono): dist 0 = sotto la barca, 1 = lontano, 2 = lontanissimo. Gli acuti spariscono,
    arrivano le eco della superficie (rovesciata) e del fondo, poi la coda lunghissima dell'acqua. tail: allunga il
    segnale perché la coda non venga tagliata."""
    fc = 1500.0 / (1.0 + 1.6 * dist)
    if tail:
        x = np.concatenate([x, np.zeros(ns(rt60 * 1.1 + 0.4))])
    y = lowpass(x, fc, 2)
    out = y.copy()
    for delay, g in [(0.012 + 0.03 * dist, -0.45), (0.045 + 0.09 * dist, 0.32), (0.11 + 0.15 * dist, 0.2)]:
        place(out, g * lowpass(y, fc * 0.7, 2), delay)
    ir = reverb_ir(rt60, rng, lo=1.4, hi=0.2, attack=0.08 + 0.1 * dist, lp=fc * 0.8, stereo_out=False)
    return (0.75 - 0.2 * min(dist, 2.0)) * out + (0.35 + 0.3 * min(dist, 2.0)) * convolve(out, ir)


def _melody_f0(n, notes, glide=0.3, scoop=40.0, sag=50.0, drift=None):
    """Contorno d'intonazione di una melodia canticchiata: notes = [(t0, durata, midi)]. La voce scivola da una
    nota all'altra (portamento), entra un po' sotto la nota e la raggiunge, e alla fine di ogni nota cala.
    drift: curva in centesimi sommata a tutto (la voce che si abbassa piano). Restituisce f0 in Hz."""
    t = tvec(n)
    m = np.full(n, float(notes[0][2]))
    for i, (t0, d, mm) in enumerate(notes):
        i0, i1 = ns(t0), min(n, ns(t0 + d))
        m[i0:i1] = mm
        if i + 1 == len(notes):
            m[i1:] = mm
        else:
            m[i1:ns(notes[i + 1][0])] = mm
    c = np.zeros(n)
    for i, (t0, d, mm) in enumerate(notes):
        # il portamento dalla nota prima (se è attaccata)
        if i and notes[i - 1][0] + notes[i - 1][1] > t0 - 0.1:
            prev = notes[i - 1][2]
            sel = (t >= t0 - glide * 0.4) & (t < t0 + glide * 0.6)
            u = np.clip((t[sel] - (t0 - glide * 0.4)) / glide, 0, 1)
            m[sel] = prev + (mm - prev) * (0.5 - 0.5 * np.cos(np.pi * u))
        # entra sotto e sale, poi alla fine cala
        sel = (t >= t0) & (t < t0 + d)
        u = (t[sel] - t0) / d
        c[sel] += -scoop * np.exp(-(t[sel] - t0) / 0.18) - sag * np.clip((u - 0.55) / 0.45, 0, 1) ** 1.5
    if drift is not None:
        c = c + drift
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0) * cents(c)


def _hum_shape(n, notes, phrases, dip=0.35):
    """Inviluppo e vocali di una melodia canticchiata a bocca chiusa: ogni frase sale e si spegne, a ogni nota
    nuova la bocca si richiude un attimo ('m') e il fiato cala appena."""
    t = tvec(n)
    amp = np.zeros(n)
    for a, b in phrases:
        amp = np.maximum(amp, curve(n, [(0, 0), (a, 0), (a + 0.45, 1.0), (b - 0.9, 0.85), (b, 0), (n / SR, 0)]))
    for t0, d, _m in notes:
        amp *= 1.0 - dip * np.exp(-((t - t0) / 0.1) ** 2)
        amp *= 1.0 + 0.12 * np.exp(-((t - t0 - 0.35 * d) / (0.3 * d)) ** 2)
    keys = []
    for t0, d, _m in notes:
        keys += [(t0 - 0.02, 'm'), (t0 + 0.18, 'u')]
        if d > 1.8:
            keys.append((t0 + 0.5 * d, 'o'))
        keys.append((t0 + d - 0.12, 'u'))
    keys = sorted({round(k[0], 4): k for k in keys if k[0] >= 0}.values())
    return amp, [(0.0, 'm')] + keys


def _hum(rng, n, notes, phrases, drift=None, sag=50.0, octave=0.45, song=0.12):
    """La Madre che canticchia una melodia (mono): la voce enorme tre ottave sotto il carillon, la stessa un'ottava
    sopra (più piccola, appena scordata) e, alta e lontana, il canto delle balene che la segue."""
    dur = n / SR
    f0 = _melody_f0(n, notes, sag=sag, drift=drift)
    amp, keys = _hum_shape(n, notes, phrases)
    y = _whale(rng, dur, None, keys, amp, f0=f0, rough=0.12, rough_rate=11.0, sub=0.1, breath=0.04, under=0.25)
    if octave:
        hi = vox(rng, dur, None, keys, f0=f0 * 2.0 * cents(7), scale=0.5, amp_pts=amp, oq=0.68, jitter=0.004,
                 shimmer=0.04, breath=0.08, bw=1.5, wander=6.0, fjit=15.0)
        y = y + octave * normalize(hi)
    if song:
        # il canto: quasi un fischio, che scivola sulla melodia due ottave sopra la voce e respira lento
        ph = phase_of(f0 * 4.0 * cents(-12 + 10 * rand_curve(n, 0.5, rng)))
        s = np.sin(TWO_PI * ph) + 0.3 * np.sin(2 * TWO_PI * ph + 0.4) + 0.12 * np.sin(3 * TWO_PI * ph + 1.3)
        s *= amp ** 1.5 * (0.6 + 0.4 * np.abs(rand_curve(n, 0.3, rng)))
        y = y + song * normalize(s)
    return y


def _lull_notes(notes, beat, t_offset=0.0, rit=0.0, breath_at=(), breath=0.6):
    """Le note della ninna nanna [(battuta, tempo, midi, durata)] → [(t0, durata, midi)] a tempo `beat`, con un
    rallentando (rit: quanto si allunga l'ultima battuta) e una pausa per il fiato prima delle battute breath_at."""
    out = []
    shift = 0.0
    last_bar = max(b for b, *_ in notes)
    for b, bt, m, d in notes:
        if m is None:
            continue
        if b in breath_at and bt == 1:
            shift += breath
        k = 1.0 + rit * (b - 1) / max(last_bar - 1, 1)
        t0 = t_offset + shift + ((b - 1) * 3 + (bt - 1)) * beat * k
        out.append((t0, d * beat * k, m - DOWN))
    # chi canta respira: la nota prima della pausa si chiude un po' prima
    res = []
    for i, (t0, d, m) in enumerate(out):
        if i + 1 < len(out) and out[i + 1][0] - (t0 + d) > 0.2:
            d = min(d, out[i + 1][0] - t0 - breath * 0.8)
        res.append((t0, d, m))
    return res


# ───────────────────────── l'ombra lontana ─────────────────────────

def _far(s, rng):
    """L'ombra lontana: un richiamo profondo e distorto che arriva dal fondo, da lontano. Tre richiami diversi:
    1 un lamento lungo che sale, si apre e ricade, con un canto acuto che gli risponde; 2 due grugniti pulsati che
    scendono e un lamento basso che crolla; 3 l'inizio della ninna nanna (Mi–Do–La–Si), lentissimo e storto."""
    n, d = s.n, s.dur
    v = s.params['v']
    y = np.zeros(n)
    if v == 1:
        place(y, _whale(rng, 6.4, [(0, 31), (1.6, 42), (3.4, 54), (4.8, 47), (6.4, 26)],
                        [(0, 'u'), (1.4, 'o'), (3.4, 'a'), (5.0, 'o'), (6.4, 'u')],
                        [(0, 0), (1.2, 0.7), (3.4, 1.0), (5.2, 0.6), (6.4, 0)], rough=0.25), 0.0)
        song = whale_moan(rng, 2.6, [(0, 180), (0.9, 330), (1.8, 290), (2.6, 140)], [(0, 'u'), (1.0, 'o'), (2.6, 'u')],
                          scale=0.6, amp_pts=[(0, 0), (0.7, 1), (1.9, 0.6), (2.6, 0)], sub=0.1)
        place(y, 0.22 * song, 4.6)
    elif v == 2:
        for t0, f1, f2 in [(0.0, 48, 40), (1.5, 44, 34)]:
            g = _whale(rng, 1.15, [(0, f1 * 0.9), (0.25, f1), (1.15, f2)], [(0, 'o'), (0.4, 'O'), (1.15, 'u')],
                       [(0, 0), (0.12, 1), (0.8, 0.7), (1.15, 0)], rough=0.65, rough_rate=8.0, sub=0.5)
            place(y, 0.9 * g, t0)
        moan = _whale(rng, 5.2, [(0, 36), (1.6, 41), (3.6, 30), (5.2, 21)], [(0, 'o'), (1.8, 'O'), (3.8, 'o'), (5.2, 'u')],
                      [(0, 0), (1.0, 0.9), (2.6, 1.0), (4.4, 0.5), (5.2, 0)], rough=0.3, rough_rate=10.0)
        place(y, moan, 3.0)
    else:
        notes = [(0.3, 2.3, 76 - DOWN), (2.6, 1.2, 72 - DOWN), (3.8, 2.4, 69 - DOWN), (6.2, 2.4, 71 - DOWN)]
        drift = curve(n, [(0, 0), (d, -90)])
        y += _hum(rng, n, notes, [(0.3, 8.5)], drift=drift, sag=80.0, octave=0.3, song=0.08)
    # lontano, sott'acqua: le eco del fondo e la coda; il livello ondeggia con l'acqua che c'è in mezzo
    y = y * (1.0 + 0.18 * rand_curve(n, 0.6, rng))
    y = _underwater(y, rng, dist=1.4, rt60=4.0, tail=False) * curve(n, [(0, 1), (d - 2.0, 1), (d, 0)])
    # un filo di bollicine nella testa del richiamo, perché l'orecchio sappia da che parte arriva
    for tb in poisson_times(rng, 3.0, 0.5, d - 1.5):
        place(y, 0.012 * bubble(float(loguniform(rng, 500, 1400)), xi=0.05, amp=1.0), tb)
    return highpass(y, 22, 2)


for _sid, _d, _v in [('madre_far_1', 10.5, 1), ('madre_far_2', 11.5, 2), ('madre_far_3', 12.0, 3)]:
    register(_sid, _far, _d, category='mon', gain=0.7, rms=-24.0, max_gr=4.0, params={'v': _v})


# ───────────────────────── l'avvicinamento ─────────────────────────

def _dive(rng, size=0.5, up=False):
    """Un figlio che va sotto (o, con up, che affiora): non un tuffo da piscina ma un corpo che scivola nell'acqua,
    un risucchio scuro e corto, poche bolle gravi che quasi non salgono di tono, qualche goccia."""
    d = 0.9 + 0.5 * size
    n = ns(d)
    y = np.zeros(n)
    m = ns(0.35 + 0.3 * size)
    pts = [(0, 0), (0.12, 1), (m / SR, 0)] if up else [(0, 0), (0.05, 1), (0.15, 0.6), (m / SR, 0)]
    sw = bandpass(rng.standard_normal(m), 140, 2200, 2) * (0.6 + 0.4 * np.abs(np.tanh(rand_curve(m, 30.0, rng))))
    place(y, normalize(sw) * curve(m, pts), 0.0)
    for k in range(int(rng.integers(2, 5))):
        place(y, bubble(float(loguniform(rng, 110, 260)), xi=rng.uniform(0.0, 0.04), amp=rng.uniform(0.2, 0.45),
                        decay_mult=0.5, max_dur=0.3), rng.uniform(0.04, 0.3))
    for _ in range(int(4 + 8 * size)):
        place(y, droplet(rng, amp=rng.uniform(0.04, 0.12), tonal=0.2), rng.uniform(0.08, d - 0.1))
    return lowpass(y, 5000, 2)


def _child_noise(rng, dur, f, kind):
    """Un figlio che fa i suoi versi, lontano sul mare (un mugolio o un gorgoglio): li si sente zittirsi."""
    if kind == 'giggle':
        n = ns(dur)
        syl = np.zeros(n)
        tt = 0.0
        while tt < dur - 0.08:
            syl += gate_env(n, tt, tt + 0.07, 0.008, 0.02)
            tt += rng.uniform(0.11, 0.14)
        y = vox(rng, dur, [(0, f), (dur, f * 0.82)], [(0, 'i'), (dur, 'E')], scale=BOY + 0.1, amp_pts=syl, oq=0.5,
                jitter=0.03, shimmer=0.15, breath=0.4, hnoise=0.4 * syl, bw=1.3)
    else:
        y = vox(rng, dur, [(0, f * 0.9), (dur * 0.3, f), (dur, f * 0.7)], [(0, 'u'), (dur * 0.5, 'o'), (dur, 'u')],
                scale=BOY, amp_pts=[(0, 0), (0.08, 1), (dur * 0.7, 0.8), (dur, 0)], oq=0.55, jitter=0.03,
                shimmer=0.12, breath=0.35, bw=1.3, rough=0.3, rough_rate=30.0)
        y = wet_throat(y, rng, rate=18.0, depth=0.4, bubbles=0.3, flange=0.3)
    return normalize(y)


def _lamp_tremble(rng, dur, amt=1.0):
    """La lampara che trema (mono): la scarica che si abbassa e torna a scatti, il ronzio del reattore che si fa
    ruvido nei cali, qualche crepitio del contatto. Più morbida di lamp_flicker: non si spegne, ha paura."""
    n = ns(dur)
    t = tvec(n)
    gate = np.ones(n)
    tc = 0.02
    while tc < dur - 0.12:
        off = rng.uniform(0.02, 0.07)
        gate[ns(tc):ns(tc + off)] = rng.uniform(0.25, 0.6)
        tc += off + rng.uniform(0.04, 0.14)
    gate = lowpass(gate, 120, 2)
    hum = np.tanh(2 * (np.sin(TWO_PI * 100 * t) + 0.5 * np.sin(TWO_PI * 200 * t + 1) + 0.3 * np.sin(TWO_PI * 300 * t + 2)))
    hiss = bandpass(rng.standard_normal(n), 1800, 4500) * (0.7 + 0.3 * np.abs(np.sin(TWO_PI * 50 * t)))
    env = curve(n, [(0, 0), (0.02, 1), (dur - 0.1, 1), (dur, 0)])
    y = (0.25 * hum + 0.05 * normalize(hiss)) * gate * env
    y += 0.2 * bandpass(np.tanh(4 * np.sin(TWO_PI * 100 * t)), 100, 4000) * np.clip(1 - gate, 0, 1) * env
    for tp in poisson_times(rng, 9.0, 0.02, dur - 0.05):
        k = ns(rng.uniform(0.0003, 0.001))
        place(y, 0.12 * highpass(rng.standard_normal(k + 64), 1500) * np.exp(-np.arange(k + 64) / k), tp)
    return amt * lowpass(y, 6000, 2)


def _approach(s, rng):
    """Arriva: in lontananza i figli fanno i loro versi e d'un tratto si zittiscono (l'ultimo a metà) e vanno giù
    tutti insieme; il mare si calma di colpo; resta un silenzio che pesa, con sotto una pressione bassissima che
    cresce; il richiamo della Madre si fa vicino, sotto la barca; la lampara trema due volte."""
    n, d = s.n, s.dur
    out = np.zeros((2, n))
    # il mare, che si ferma di colpo verso i 3,6 s
    sea = sea_texture(n, rng, swell_cycles=3, lap_rate=0.3, bed=1.0, hull=0.35, lap_gain=0.5, babble=1.5)
    sea = lowpass(sea, 3500, 2)
    pk = 4.0 * rms(sea)
    sea = pk * np.tanh(sea / pk)                       # niente colpi d'onda che saltano fuori
    out += _at(sea, -27.0) * curve(n, [(0, 1), (3.4, 1), (4.4, 0.04), (d, 0.02)])
    # i figli lontani: un gorgoglio, una risatina, un mugolio interrotto a metà
    kids = np.zeros((2, n))
    for t0, dd, f, kind, p in [(0.15, 0.9, 120, 'moan', -0.7), (0.9, 0.85, 560, 'giggle', 0.55),
                               (2.15, 1.1, 300, 'moan', 0.1)]:
        v = _child_noise(rng, dd, f, kind)
        if t0 > 2.0:
            v *= curve(len(v), [(0, 1), (0.42, 1), (0.45, 0), (dd, 0)])        # si zittisce di colpo
        v = lowpass(v, 2600, 2)
        place(kids, pan(v, p), t0)
    kids = lowpass(kids, 3000, 2)
    kids = kids + 0.5 * convolve(kids.mean(axis=0), reverb_ir(1.8, rng, lo=1.0, hi=0.4, sparse=0.5))
    out += _at(kids, -29.0)
    # e vanno giù tutti insieme: piccoli tuffi attorno alla barca
    dives = np.zeros((2, n))
    for k, p in enumerate((-0.8, 0.6, -0.2, 0.9, -0.55)):
        place(dives, pan(_dive(rng, rng.uniform(0.3, 0.7)), p), 2.75 + 0.14 * k + rng.uniform(-0.04, 0.04))
    out += _at(dives, -27.0)
    # il silenzio che pesa: una pressione grave che cresce, quasi solo sentita
    nz = brown(n, rng)
    press = lowpass(highpass(nz, 18, 2), 70, 2)
    out += stereo(_at(press, -31.0) * curve(n, [(0, 0), (3.6, 0), (6.0, 0.4), (d - 1.0, 1.0), (d, 0.6)]))
    # il richiamo: da lontano a vicinissimo, sotto la barca (la voce si schiarisce e cresce)
    call = _whale(rng, 8.4, [(0, 27), (2.4, 36), (5.0, 49), (6.8, 41), (8.4, 30)],
                  [(0, 'u'), (2.0, 'o'), (5.0, 'a'), (6.6, 'o'), (8.4, 'u')],
                  [(0, 0), (2.0, 0.35), (5.0, 1.0), (7.0, 0.7), (8.4, 0)], rough=0.22, under=0.45)
    far = _underwater(call, rng, dist=1.4, rt60=4.0)
    near = _underwater(call, rng, dist=0.15, rt60=3.0)
    m = min(len(far), len(near))
    mix = curve(m, [(0, 0), (2.5, 0.15), (5.5, 0.85), (8.4, 1.0), (m / SR, 1.0)])
    cl = (1 - mix) * far[:m] + mix * near[:m]
    cl_st = stereo(cl) * np.sqrt(0.5) + 0.35 * convolve(cl, reverb_ir(3.2, rng, lo=1.4, hi=0.2, lp=900))
    place(out, _at(cl_st, -21.0), 3.2)
    # la lampara che trema (in alto, un po' a destra: è sul buttafuori)
    for t0, dd, a in [(5.9, 0.7, 0.55), (9.0, 1.1, 0.7)]:
        place(out, pan(_at(_lamp_tremble(rng, dd), -30.0 + 20 * np.log10(a)), 0.35), t0)
    return highpass(out, 18, 2)


register('madre_approach', _approach, 12.0, channels=2, category='mon', gain=0.85, rms=-21.0, max_gr=4.0)


# ───────────────────────── la ninna nanna dal fondo (loop) ─────────────────────────

LULL_DUR = 40.0


def _lullaby(s, rng):
    """La ninna nanna della Madre canticchiata dal fondo (loop da 40 s): la prima frase della melodia del carillon
    (Mi–Do | La–Si | Do Re Mi | Si…, poi Mi–Do | La–Sol♯ | La Si Do | La…) tre ottave sotto, a bocca chiusa, da una
    voce di balena enorme, lentissima (43 al minuto, e rallenta ancora); scivola da una nota all'altra, ogni nota
    cala sulla coda, la seconda frase è più bassa della prima e l'ultima nota non arriva: crolla in un lamento. Poi
    il silenzio, le bolle che salgono, e ricomincia. Tutto sott'acqua, attorno e sotto la barca."""
    n, d = s.n, s.dur
    notes = _lull_notes(LULL_A, LULL_BEAT, t_offset=0.8, rit=0.12, breath_at=(5,), breath=0.9)
    # l'ultima nota (il La) crolla: si allunga e scende di quasi due semitoni
    t_last, d_last, m_last = notes[-1]
    notes[-1] = (t_last, d_last + 1.6, m_last)
    p1_end = notes[7][0] + notes[7][1]
    p2_start = notes[8][0]
    end = t_last + d_last + 1.6
    drift = curve(n, [(0, 0), (p1_end, -15), (p2_start, -30), (t_last, -60), (t_last + 1.0, -70), (end, -230),
                      (d, -230)])
    y = _hum(rng, n, notes, [(0.8, p1_end + 0.3), (p2_start - 0.1, end)], drift=drift, sag=45.0, octave=0.5,
             song=0.14)
    # l'acqua fra lei e la barca fa ondeggiare piano la voce (come un nastro): cicli interi nel loop
    t = tvec(n)
    r = 1.0 + 0.0025 * np.sin(TWO_PI * 5 * t / d + 0.3) + 0.0012 * np.sin(TWO_PI * 13 * t / d + 1.7)
    y = time_warp(y, r, circular=True)
    # le bolle che salgono nella pausa e qua e là (grosse e lente: niente "bloop")
    bb = np.zeros(n)
    for tb in list(rng.uniform(end - 0.5, d + 0.6, 9)) + list(poisson_times(rng, 0.25, 0.0, d)):
        place(bb, bubble(float(loguniform(rng, 70, 220)), xi=rng.uniform(0.0, 0.06), amp=rng.uniform(0.3, 1.0),
                         decay_mult=0.4, max_dur=0.7), tb, wrap=True)
    y = circular(lambda x: lowpass(x, 1300, 2), y + 0.12 * lowpass(bb, 800, 2))
    # sott'acqua, dal fondo: eco del fondo e della superficie, coda lunghissima, attorno a tutta la barca
    dry = y.copy()
    for delay, g in [(0.021, -0.4), (0.07, 0.3), (0.16, 0.18)]:
        place(dry, g * circular(lambda x: lowpass(x, 900, 2), y), delay, wrap=True)
    ir = reverb_ir(5.5, rng, lo=1.4, hi=0.2, attack=0.15, lp=1200, early=[(0.09, 0.3, -0.6), (0.23, 0.22, 0.6)])
    out = 0.55 * stereo(dry) + 0.85 * convolve(dry, ir, circular=True)
    return circular(lambda x: highpass(x, 22, 2), out)


register('madre_lullaby', _lullaby, LULL_DUR, loop=True, channels=2, category='mon', gain=0.8, rms=-22.0,
         max_gr=3.0, params={'rotate_max': 3.0})


# ───────────────────────── la passata sotto la barca ─────────────────────────

def _heart(rng, dur=1.6):
    """Un battito del cuore della balena sentito attraverso il legno: due colpi gravissimi e lenti (lub… dub) che
    fanno risuonare lo scafo come un tamburo sordo, senza attacco."""
    n = ns(dur)
    y = np.zeros(n)
    for t0, f1, f2, T, a in [(0.0, 34.0, 25.0, 0.55, 1.0), (0.55, 40.0, 30.0, 0.4, 0.6)]:
        m = ns(1.0)
        f = curve(m, [(0, f1), (0.12, f2), (1.0, f2 * 0.97)], 'log')
        th = osc(f) * exp_env(m, T, attack=0.045)
        nz = lowpass(rng.standard_normal(m), 90, 2) * exp_env(m, 0.3, attack=0.04)
        place(y, a * (th + 0.4 * normalize(nz)), t0)
    hf, hT, hg = HULL_MODES
    wood = modal(lowpass(y, 160, 2), np.array(hf) * rng.uniform(0.95, 1.05, len(hf)), np.array(hT) * 1.6, hg)
    return normalize(y) + 0.35 * normalize(lowpass(wood, 500, 2))


def _pass(s, rng):
    """La Madre passa sotto la barca (12, 16 o 20 s: le tre passate della notte, sempre più lunghe). L'acqua che
    il suo corpo sposta e spinge contro lo scafo, la pelle enorme che scorre sotto la chiglia (un attrito lento e
    sordo, i denti di balena e le incrostazioni che grattano il legno), la barca che si solleva piano sul suo
    dorso e scricchiola tutta (dal fasciame grave alle tavole del pagliolo), e attraverso il legno il suo cuore,
    lentissimo. Passa da un lato all'altro. Cresce piano e piano se ne va: niente è mai forte di colpo."""
    n, d = s.n, s.dur
    t = tvec(n)
    out = np.zeros((2, n))
    # quanto è sotto: sale, resta e scende (il dorso è lungo); dove sta: da sinistra a destra
    under = curve(n, [(0, 0), (0.3 * d, 0.75), (0.5 * d, 1.0), (0.72 * d, 0.85), (d, 0)])
    lift = curve(n, [(0, 0), (0.25 * d, 0.2), (0.5 * d, 1.0), (0.8 * d, 0.5), (d, 0)])
    where = lambda tt: float(np.clip(-0.75 + 1.5 * tt / d, -0.8, 0.8))   # noqa: E731
    # 1) l'acqua che sposta: una spinta grave e lunga, e la pressione che si sente nello stomaco
    nz = brown(n, rng)
    push = lowpass(highpass(nz, 16, 2), 90, 2) * under ** 1.3
    out += stereo(0.8 * normalize(push))
    flow = np.zeros((2, n))
    for c in range(2):
        f = spectral_noise(n, rng, lambda f: bw_bp(f, 60, 600, 2), exponent=1.0)
        flow[c] = f * (0.6 + 0.4 * np.abs(rand_curve(n, 0.8, rng)))
    out += 0.12 * flow / np.max(np.abs(flow)) * under * np.stack([curve(n, [(0, 1.0), (d, 0.4)]), curve(n, [(0, 0.4), (d, 1.0)])])
    # 2) la pelle che scorre sotto la chiglia: attrito lento che fa vibrare lo scafo
    m = n
    rate = 7.0 + 9.0 * under * (1 + 0.3 * np.tanh(rand_curve(m, 1.5, rng)))
    exc = stick_slip(m, rng, rate, under * (0.6 + 0.4 * np.abs(np.tanh(2 * rand_curve(m, 3.0, rng)))), 0.12)
    hf, hT, hg = HULL_MODES
    keel = modal(exc, np.array(hf) * 0.7, np.array(hT) * 1.8, hg)
    rub = lowpass(highpass(rng.standard_normal(m), 60, 2), 380, 2) * under * (0.5 + 0.5 * np.abs(rand_curve(m, 4.0, rng)))
    skin = normalize(keel) + 0.5 * normalize(rub)
    th = (np.clip(-0.75 + 1.5 * t / d, -0.8, 0.8) + 1.0) * np.pi / 4.0
    out += 0.35 * np.stack([skin * np.cos(th), skin * np.sin(th)])
    # le incrostazioni che grattano il legno: brevi grattate sorde, rade, nel mezzo della passata
    for tg in poisson_times(rng, lambda tt: 0.7 * np.interp(tt, t, under) ** 2 + 1e-3, 0.2 * d, 0.85 * d):
        sc = nail_scrape(rng, dur=rng.uniform(0.35, 0.8), base=rng.uniform(180, 300))
        place(out, pan(lowpass(sc, 2500, 2), where(tg) + rng.uniform(-0.2, 0.2)) * 0.08, tg)
    # 3) la barca che si solleva e scricchiola tutta
    for tc in poisson_times(rng, lambda tt: 0.3 + 1.6 * np.interp(tt, t, lift), 0.4, d - 1.4):
        lv = float(np.interp(tc, t, lift))
        grave = rng.random() < 0.6
        dur = rng.uniform(0.9, 2.0) if grave else rng.uniform(0.5, 1.1)
        base = rng.uniform(85, 140) if grave else rng.uniform(190, 300)
        r0 = rng.uniform(8, 18) if grave else rng.uniform(30, 70)
        cr = boat_creak(rng, dur, [(0, r0), (dur * 0.5, r0 * rng.uniform(1.4, 2.2)), (dur, r0 * 0.7)],
                        [(0, 0), (dur * 0.3, 1), (dur * 0.75, 0.7), (dur, 0)], base=base, t60=0.14 if grave else 0.08,
                        bright=0.8 if grave else 1.0, burst=0.45, hull=0.6 if grave else 0.15)
        cr = lowpass(cr, 5000, 2)
        place(out, pan(cr, rng.uniform(-0.8, 0.8)) * (0.12 + 0.2 * lv) * (1.0 if grave else 0.7), tc)
    # la roba a bordo che si sposta mentre la barca s'inclina: il manico del secchio, la campanella a poppa
    for tk in sorted(rng.uniform(0.35 * d, 0.7 * d, 3)):
        place(out, pan(0.035 * knock(rng, force=0.0005, base=900, t60=0.03, dur=0.12), rng.uniform(-0.4, 0.4)), tk)
    tb = 0.52 * d + rng.uniform(-0.5, 0.5)
    bell = small_bell(rng, 2100.0, ns(1.4), [(0.0, 0.5), (0.24, 0.25)], t60=0.8)
    place(out, pan(0.04 * bell, -0.2), tb)
    # l'acqua che scivola giù dai fianchi quando la barca si alza e torna giù
    for tl in poisson_times(rng, lambda tt: 0.5 + 1.2 * np.interp(tt, t, lift), 0.0, d - 1.0):
        lp_ = lap(rng, rng.uniform(0.25, 0.6), dur=1.0, hull=0.3, clop_prob=0.5, bright=0.7)
        a = 0.22 * (0.25 + 0.75 * float(np.interp(tl, t, lift)))
        place(out, pan(lp_, float(rng.choice([-1, 1])) * rng.uniform(0.4, 0.8)) * a, tl)
    # 4) il cuore: lentissimo (13 al minuto), più forte quando è proprio sotto
    th = 0.12 * d
    while th < d - 1.6:
        a = float(np.interp(th + 0.2, t, under))
        place(out, stereo(_heart(rng)) * 0.55 * a ** 1.2, th)
        th += 4.6 + rng.uniform(-0.15, 0.15)
    # 5) dentro di lei, appena, la voce: un brontolio senza note che passa attraverso il legno
    g = _whale(rng, d * 0.6, [(0, 24), (d * 0.3, 29), (d * 0.6, 22)], [(0, 'u'), (d * 0.3, 'o'), (d * 0.6, 'u')],
               [(0, 0), (d * 0.3, 1), (d * 0.6, 0)], rough=0.3, rough_rate=9.0)
    place(out, stereo(lowpass(g, 300, 2)) * 0.18, d * 0.22)
    return lowpass(highpass(out, 16, 2), 9000, 2)


for _sid, _d in [('madre_pass_1', 12.0), ('madre_pass_2', 16.0), ('madre_pass_3', 20.0)]:
    register(_sid, _pass, _d, channels=2, category='mon', gain=0.9, rms=-21.0, max_gr=3.0, release=0.2)


# ───────────────────────── jumpscare ─────────────────────────

def _js_madre(s, rng):
    """Ti prende dal basso: lo scafo che si spacca sotto i piedi e la barca sollevata di colpo (un colpo enorme e
    sordo, il legno che si schianta), l'acqua che esplode tutta attorno, e la bocca: il ruggito di una balena enorme
    (due gole, la voce rotta) e dentro, alte e bagnate, le voci dei bambini che ha preso che urlano tutte insieme."""
    n, d = s.n, s.dur
    amp = [(0, 0.5), (0.06, 1), (1.4, 0.9), (d, 0.3)]
    roar = _whale(rng, d, [(0, 40), (0.1, 72), (0.6, 64), (1.1, 76), (1.5, 58), (d, 38)],
                  [(0, 'o'), (0.12, 'a'), (0.9, 'O'), (1.4, 'a'), (d, 'o')], amp, rough=0.75, rough_rate=34.0,
                  sub=0.6, breath=0.3, scale=0.42, under=0.5, wander=40.0)
    roar = wet_throat(roar, rng, rate=20.0, depth=0.5, bubbles=0.45, flange=0.35)
    kids = np.zeros(n)
    for k, (f, sc, det) in enumerate([(880, 1.4, 0.0), (1040, 1.5, 12.0), (720, 1.32, -14.0), (960, 1.55, 25.0),
                                      (640, 1.36, -30.0)]):
        t0 = 0.05 + 0.04 * k
        pts = [(0, f * 0.7), (0.08, f), (0.5, f * 0.94), (1.0, f * 1.06), (1.4, f * 0.95), (d, f * 0.7)]
        v = vox(rng, d, [(tt, ff * cents(det)) for tt, ff in pts], [(0, 'ae'), (0.15, 'a'), (1.2, 'a'), (d, '@')],
                scale=sc, amp_pts=[(0, 0), (0.07, 1), (1.4, 0.85), (d, 0.25)], oq=0.42, jitter=0.05, shimmer=0.2,
                sub=0.2, breath=0.5, bw=1.4, rough=0.55, rough_rate=55.0 + 6 * k, rough_fm=50.0, wander=40.0)
        place(kids, (1.0 if k == 0 else 0.6) * v, t0)
    # le voci stanno dentro la bocca: un po' rimbombanti e bagnate
    kids = wet_throat(bandpass(kids, 280, 7000, 2), rng, rate=24.0, depth=0.35, bubbles=0.2, flange=0.4)
    y = 0.9 * normalize(roar) + 0.75 * normalize(kids)
    # lo scafo che si spacca e la barca sollevata
    place(y, 0.9 * boom(rng, dur=1.4, f_start=60.0, f_end=34.0, t60=0.9, thump=0.6), 0.0)
    place(y, 0.7 * knock(rng, force=0.02, base=70, t60=0.25, count=6, bright=0.6, dur=0.8, rough=0.05,
                         cavity=(90, 0.3, 0.7)), 0.0)
    for tc, a in [(0.0, 0.8), (0.07, 0.5), (0.2, 0.35)]:
        place(y, a * bone_crack(rng, size=1.4, dur=0.3, bright=0.6), tc)
    cr = boat_creak(rng, 0.9, [(0, 120), (0.3, 260), (0.9, 70)], [(0, 1), (0.5, 0.7), (0.9, 0)], base=150, t60=0.1,
                    burst=0.7, hull=0.6)
    place(y, 0.45 * cr, 0.03)
    # l'acqua che esplode
    place(y, 0.8 * splash(rng, size=1.0, dur=1.6), 0.0)
    place(y, 0.45 * splash(rng, size=0.7, dur=1.2), 0.32)
    ir = near_room(rng, 0.6, stereo_out=True)
    out = stereo(y) * np.sqrt(0.5) + 0.25 * convolve(y, ir)
    out = lowpass(highpass(out, 50, 2), 12000, 2)
    return scream_master(out, drive=2.0)


register('js_madre', _js_madre, 2.0, channels=2, category='mon', gain=1.0, rms=-6.6, max_gr=6.5, release=0.03)


# ───────────────────────── il finale all'alba ─────────────────────────

def _blow(rng, dur=1.8):
    """Lo sbuffo di una balena enorme: l'aria che esce di colpo dallo sfiatatoio (un soffio pieno e profondo con
    l'acqua dentro), poi la pioggia dello spruzzo che ricade sul mare."""
    n = ns(dur)
    y = tract_noise(rng, dur, [(0, 'O'), (dur, 'o')], scale=WHALE, amp_pts=[(0, 0), (0.06, 1), (0.5, 0.7), (dur, 0)],
                    hiss=0.25)
    y = normalize(y) + 0.5 * normalize(lowpass(rng.standard_normal(n), 120, 2)) * curve(n, [(0, 0), (0.05, 1), (0.6, 0.4), (dur, 0)])
    y = wet_throat(normalize(y), rng, rate=14.0, depth=0.3, bubbles=0.2, flange=0.2)
    out = np.zeros(ns(dur + 2.2))
    place(out, y, 0.0)
    for _ in range(140):
        tr = 0.5 + rng.gamma(2.0, 0.35)
        if tr < dur + 2.1:
            place(out, droplet(rng, amp=rng.uniform(0.04, 0.14) * np.exp(-(tr - 0.5) / 1.2), tonal=0.25), tr)
    return out


def _dawn(s, rng):
    """Il finale all'alba (finale A): la Madre sale accanto alla barca, a sinistra (il mare che si gonfia, l'acqua
    che le scroscia giù dal corpo enorme, lo sbuffo, la barca che dondola); attorno a lei emergono i figli uno dopo
    l'altro; la sua pinna bagnata sul capodibanda, il secchio preso (i pesci che scivolano nella lamiera, l'acqua che
    ne cola mentre si alza); poi tornano giù tutti, lei per ultima, canticchiando la fine della ninna nanna, che per
    la prima volta si risolve (in La maggiore); il mare si calma, arriva un primo gabbiano."""
    n, d = s.n, s.dur
    t = tvec(n)
    out = np.zeros((2, n))
    P = -0.65                                           # lei è a sinistra della barca
    # il mare dell'alba: calmo, smosso quando lei sale e quando va giù, poi quieto
    sea = sea_texture(n, rng, swell_cycles=5, lap_rate=0.25, bed=1.0, hull=0.3, lap_gain=0.45, babble=1.0)
    out += 1.6 * sea * curve(n, [(0, 0.6), (2.0, 1.0), (6.0, 1.3), (11.0, 1.0), (15.0, 1.3), (18.5, 0.6), (d, 0.35)])
    # 1) sale: il mare che si gonfia, si rompe e le scroscia giù dal corpo
    swell = lowpass(highpass(brown(n, rng), 18, 2), 110, 2) * curve(n, [(0, 0), (0.6, 0.3), (2.0, 1.0), (4.0, 0.4), (6.0, 0)])
    out += pan(0.8 * normalize(swell), P * 0.6)
    m = ns(5.0)
    inten = curve(m, [(0, 0), (0.4, 0.5), (0.9, 1.0), (2.8, 0.6), (5.0, 0)])
    pour = gush(m, rng, inten, bubble_rate=120, f_lo=110, f_hi=900)
    pour = lowpass(pour, 4000, 2) + 0.4 * bandpass(rng.standard_normal(m), 600, 5000, 2) * inten * 0.3
    place(out, pan(0.9 * normalize(pour), P), 1.2)
    place(out, pan(0.9 * splash(rng, size=1.0, dur=1.8), P), 1.3)
    for tc in (2.0, 3.1, 4.4):
        cr = boat_creak(rng, 1.4, [(0, 12), (0.7, 26), (1.4, 10)], [(0, 0), (0.4, 1), (1.4, 0)], base=110, t60=0.15,
                        bright=0.8, hull=0.6)
        place(out, pan(0.18 * lowpass(cr, 4000, 2), rng.uniform(-0.5, 0.5)), tc)
    blow = _blow(rng, 1.8)
    place(out, pan(lowpass(blow, 7000, 2), P), 4.6)
    # un mormorio di lei, vicino: non una parola, un suono di mamma che chiama
    call = _whale(rng, 2.6, [(0, 44), (0.9, 55), (2.6, 41)], [(0, 'm'), (0.4, 'u'), (1.2, 'o'), (2.6, 'u')],
                  [(0, 0), (0.6, 1), (1.8, 0.7), (2.6, 0)], rough=0.15, under=0.3)
    call = lowpass(call, 1500, 2)
    place(out, pan(0.45 * call, P), 6.3)
    # 2) i figli che emergono attorno a lei, uno dopo l'altro: l'acqua che si apre, un fiato bagnato
    for k, (tk, p) in enumerate([(7.0, -0.95), (7.45, -0.3), (7.8, -0.75), (8.3, 0.1), (8.7, -0.55), (9.15, 0.35),
                                 (9.6, -0.85)]):
        place(out, pan(0.5 * _dive(rng, rng.uniform(0.4, 0.8), up=True), p), tk)
        br = breath(rng, rng.uniform(0.35, 0.55), inhale=True) * 0.12
        place(out, pan(br, p), tk + rng.uniform(0.25, 0.45))
        for _ in range(4):
            place(out, pan(droplet(rng, amp=rng.uniform(0.03, 0.08), tonal=0.4), p), tk + rng.uniform(0.2, 1.0))
    # 3) il secchio: la sua pinna bagnata sul bordo (la barca s'inclina verso di lei), il secchio preso
    place(out, pan(0.55 * wet_slap(rng, size=1.6, surface='wood', dur=0.6, wood_base=110.0, drops=1.0), P * 0.7), 10.6)
    cr = boat_creak(rng, 1.6, [(0, 14), (0.8, 30), (1.6, 12)], [(0, 0.3), (0.4, 1), (1.6, 0)], base=100, t60=0.16,
                    bright=0.8, hull=0.7)
    place(out, pan(0.3 * lowpass(cr, 4000, 2), P * 0.5), 10.7)
    bucket = np.zeros(ns(2.4))
    wall = _shell_modes(rng, 520, 7200, 26, 0.16, bright=1.0)
    bottom = _shell_modes(rng, 240, 2400, 18, 0.22, bright=0.8)
    place(bucket, _hit(rng, ns(0.6), 0.004, bottom, 0.5), 0.0)                        # il secchio che si stacca
    for i, tb in enumerate([0.12, 0.3, 0.42, 0.6, 0.85]):                              # i pesci che scivolano
        place(bucket, 0.5 * 0.8 ** i * _hit(rng, ns(0.4), rng.uniform(0.002, 0.004), wall, 0.4), tb)
        place(bucket, 0.3 * wet_slap(rng, size=0.3, surface='flesh', dur=0.3, drops=0.3), tb + 0.01)
    for tb in (0.05, 0.4, 0.95):                                                      # il manico che sbatte
        place(bucket, 0.18 * knock(rng, force=0.0004, base=1250, t60=0.05, dur=0.15), tb)
    m = ns(2.2)
    drip = bandpass(rng.standard_normal(m), 500, 4500, 2) * curve(m, [(0, 0), (0.1, 1), (0.8, 0.4), (2.2, 0)])
    place(bucket, 0.12 * normalize(drip), 0.1)
    for _ in range(22):
        place(bucket, droplet(rng, amp=rng.uniform(0.04, 0.12), tonal=0.4), rng.uniform(0.2, 2.2))
    place(out, pan(_at(bucket, -21.0), P * 0.4), 11.1)
    # 4) tornano giù tutti: i figli prima (piccoli tuffi), lei per ultima, enorme e lenta
    for k, p in enumerate((-0.9, -0.2, 0.3, -0.7, 0.05, -0.45, -0.8)):
        place(out, pan(0.45 * _dive(rng, rng.uniform(0.3, 0.6)), p), 13.0 + 0.32 * k + rng.uniform(-0.08, 0.08))
    m = ns(4.5)
    sink = gush(m, rng, curve(m, [(0, 0), (0.8, 1.0), (2.5, 0.5), (4.5, 0)]), bubble_rate=90, f_lo=90, f_hi=600)
    place(out, pan(0.25 * normalize(lowpass(sink, 2500, 2)), P), 14.6)
    whump = lowpass(rng.standard_normal(ns(2.5)), 90, 2) * exp_env(ns(2.5), 1.4, attack=0.3)
    place(out, pan(0.3 * normalize(whump), P * 0.6), 15.2)
    bb = np.zeros(n)
    for _ in range(18):
        place(bb, bubble(float(loguniform(rng, 70, 200)), xi=rng.uniform(0.0, 0.08), amp=rng.uniform(0.3, 1.0),
                         decay_mult=0.4, max_dur=0.7), rng.uniform(15.5, 19.5))
    out += pan(0.14 * lowpass(bb, 900, 2), P * 0.7)
    # la fine della ninna nanna, dal fondo, in maggiore: La Si Do♯ | La (si risolve)
    hn = ns(7.4)
    b = 1.4
    notes = [(0.4, 1.3, 69 - DOWN), (0.4 + b, 1.3, 71 - DOWN), (0.4 + 2 * b, 1.3, 73 - DOWN), (0.4 + 3 * b, 2.6, 69 - DOWN)]
    hum = _hum(rng, hn, notes, [(0.4, 0.4 + 3 * b + 2.6)], sag=20.0, octave=0.5, song=0.1)
    hum = _underwater(hum, rng, dist=0.8, rt60=3.5)
    place(out, stereo(hum) * 0.09, 14.6)
    # 5) il mare che si calma, le ultime onde che arrivano allo scafo, e il primo gabbiano
    for tl, a in [(18.6, 0.5), (19.9, 0.35), (21.4, 0.22)]:
        place(out, pan(lap(rng, a, dur=1.0, hull=0.3), rng.uniform(-0.6, 0.6)) * 0.4, tl)
    gull = gull_call(rng, 'short', 1180)
    gull = lowpass(gull, 4200, 2)
    gull = 0.5 * pan(gull, 0.6) + 0.4 * convolve(gull, reverb_ir(2.4, rng, lo=1.1, hi=0.5, sparse=0.6))
    place(out, 0.3 * gull, 21.0)
    return highpass(out, 18, 2) * curve(n, [(0, 1), (d - 0.5, 1), (d, 0)])


register('madre_dawn', _dawn, 24.0, channels=2, category='mon', gain=0.85, rms=-19.0, max_gr=4.0)
