"""
Musica e stinger (stereo): la ninna nanna della Madre al carillon (menu, loop), l'inizio della notte, le
sei del mattino, il game over e il risveglio della Madre.

La ninna nanna è in La minore, 3/4, 67,5 BPM: 24 battute = 64 s esatti (A A' con una frase centrale B).
È un po' sbagliata di proposito: due lamelle del carillon sono stonate, nella frase B c'è un Re diesis
(tritono) e un Si bemolle che stride contro il Sol diesis, e all'ultima battuta la tonica non arriva (la
lamella è rotta: si sente solo il perno che la sfiora), così il loop riparte senza essersi mai risolto.
"""
from __future__ import annotations

from instruments import *  # noqa: F401,F403
from sounds import sound

BPM = 67.5
BEAT = 60.0 / BPM
BAR = 3 * BEAT

# melodia: (battuta da 1, tempo da 1, nota MIDI, durata in tempi); None = la lamella rotta
_A = [(1, 1, 76, 2), (1, 3, 72, 1), (2, 1, 69, 2), (2, 3, 71, 1), (3, 1, 72, 1), (3, 2, 74, 1), (3, 3, 76, 1),
      (4, 1, 71, 3), (5, 1, 76, 2), (5, 3, 72, 1), (6, 1, 69, 2), (6, 3, 68, 1), (7, 1, 69, 1), (7, 2, 71, 1),
      (7, 3, 72, 1), (8, 1, 69, 3)]
_B = [(9, 1, 81, 2), (9, 3, 77, 1), (10, 1, 76, 2), (10, 3, 72, 1), (11, 1, 74, 2), (11, 3, 71, 1), (12, 1, 76, 3),
      (13, 1, 81, 2), (13, 3, 77, 1), (14, 1, 76, 2), (14, 3, 75, 1), (15, 1, 76, 1), (15, 2, 70, 1), (15, 3, 68, 1),
      (16, 1, 69, 3)]
_A2 = [(b + 16, beat, m, d) for (b, beat, m, d) in _A[:7]] + [(20, 1, 71, 2)] + \
      [(b + 16, beat, m, d) for (b, beat, m, d) in _A[8:15]] + [(24, 1, None, 3)]
MELODY = _A + _B + _A2

# accordi per battuta (fondamentale MIDI del basso, note dell'accordo)
_AM, _F, _E, _DM, _B7 = (45, (57, 60, 64)), (41, (57, 60, 65)), (40, (56, 59, 64)), (38, (57, 62, 65)), (35, (57, 63, 66))
CHORDS = [_AM, _F, _AM, _E, _AM, _E, _DM, _AM,
          _F, _AM, _DM, _E, _F, _B7, _E, _AM,
          _AM, _F, _AM, _E, _AM, _E, _DM, _AM]

# ogni lamella ha la sua accordatura (centesimi): due sono stonate davvero
_TUNE_RNG = np.random.default_rng(1997)
TUNING = {m: float(_TUNE_RNG.uniform(-9, 9)) for m in range(30, 100)}
TUNING[72] = -27.0          # il Do5, calante
TUNING[77] = +21.0          # il Fa5, crescente


def tine_note(rng, midi, vel=1.0, dur=3.2, bright=1.0, detune=None):
    """Lamella d'acciaio di un carillon pizzicata da un perno: trave a sbalzo (modi a 1 : 6,27 : 17,5,
    il secondo molto presente nell'attacco), un'ottava debole dalla non linearità del pettine, battimento
    lento fra due lamelle gemelle, lo scatto del perno."""
    n = ns(dur)
    t = tvec(n)
    f = float(midi_hz(midi)) * cents(TUNING.get(midi, 0.0) if detune is None else detune)
    T1 = float(np.clip(3.4 * (440.0 / f) ** 0.6, 0.9, 5.0))
    y = (0.75 * np.exp(-6.907755 * t / T1) + 0.25 * np.exp(-6.907755 * t / (0.15 * T1))) * \
        (np.sin(TWO_PI * f * t) + 0.35 * np.sin(TWO_PI * f * cents(rng.uniform(1.5, 3.5)) * t + 1.1)) / 1.35
    for r, a, tf in [(2.0, 0.06, 0.35), (6.267 * rng.uniform(0.985, 1.01), 0.42, 0.11), (17.55 * rng.uniform(0.98, 1.02), 0.12, 0.035),
                     (3.0, 0.015, 0.2)]:
        fr = f * r
        if fr < NYQ * 0.9:
            y += a * bright * np.sqrt(vel) * np.sin(TWO_PI * fr * t + rng.uniform(0, TWO_PI)) * \
                np.exp(-6.907755 * t / max(T1 * tf, 0.01))
    k = ns(0.0025)
    y[:k] += 0.1 * vel * bandpass(rng.standard_normal(k), 1500, 9000) * np.linspace(1, 0, k)
    y *= np.clip(t / 0.0006, 0, 1)
    return vel * y


def broken_tine(rng, vel=1.0):
    """Il perno che sfiora una lamella spezzata: un tic metallico smorzato, senza nota."""
    n = ns(0.25)
    exc = np.zeros(n)
    exc[:2] = [1.0, -0.6]
    y = modal(exc, [1180.0, 2350.0, 4100.0, 6900.0], [0.025, 0.015, 0.01, 0.006], [1.0, 0.6, 0.4, 0.25])
    return 0.12 * vel * normalize(y)


def box_body(x):
    """La cassetta di legno del carillon: risonanze larghe e morbide (calore, 'legno'), non picchi stretti
    che gonfierebbero una nota sì e una no."""
    y = eq(x, 'peak', 210.0, 1.2, 2.5)
    y = eq(y, 'peak', 480.0, 1.4, 2.0)
    y = eq(y, 'peak', 1100.0, 1.6, 1.5)
    return eq(y, 'highshelf', 3500.0, 0.7, -2.5)


def music_box_track(rng, n, notes, accents=True, wrap=False, vel_scale=1.0, bright=1.0):
    """Mette le note [(t, midi, vel)] su una traccia (mono). Il cilindro non è perfetto: ±4 ms."""
    y = np.zeros(n)
    for t0, m, v in notes:
        if m is None:
            place(y, broken_tine(rng, v), t0 + rng.uniform(-0.004, 0.004), wrap=wrap)
            continue
        dur = float(np.clip(3.6 * (440.0 / float(midi_hz(m))) ** 0.6 * 1.2, 1.2, 6.0))
        place(y, tine_note(rng, m, v * vel_scale, dur=dur, bright=bright), t0 + rng.uniform(-0.004, 0.004), wrap=wrap)
    return y


def lullaby_notes(rng, t_offset=0.0):
    """Le note della ninna nanna (melodia + accompagnamento a valzer) come [(t, midi, vel)]."""
    out = []
    for b, beat, m, d in MELODY:
        t = t_offset + (b - 1) * BAR + (beat - 1) * BEAT
        v = (0.95 if beat == 1 else 0.82) * rng.uniform(0.92, 1.05)
        out.append((t, m, v))
    for i, (root, ch) in enumerate(CHORDS):
        t = t_offset + i * BAR
        out.append((t, root + 12, 0.55 * rng.uniform(0.9, 1.05)))                 # il basso sul primo tempo
        out.append((t + BEAT, ch[1] if i % 2 else ch[0], 0.32 * rng.uniform(0.9, 1.1)))
        out.append((t + 2 * BEAT, ch[2] if i % 2 else ch[1], 0.3 * rng.uniform(0.9, 1.1)))
    return out


def tape(x, rng, wow=0.45, flutter=0.06, circular_=True):
    """Il nastro vecchio: velocità che ondeggia piano (wow, ±0,45%) e trema (flutter), stessa per i due canali."""
    n = x.shape[-1]
    t = tvec(n)
    dur = n / SR
    k1 = max(1, round(0.55 * dur))
    k2 = max(1, round(0.23 * dur))
    r = 1.0 + 0.01 * (wow * np.sin(TWO_PI * k1 * t / dur + 0.7) + 0.55 * wow * np.sin(TWO_PI * k2 * t / dur + 2.1)
                      + 0.35 * wow * rand_curve(n, 0.4, rng) + flutter * rand_curve(n, 7.0, rng))
    if x.ndim == 1:
        return time_warp(x, r, circular=circular_)
    return np.stack([time_warp(c, r, circular=circular_) for c in x])


def underwater_pad(rng, n, chords, bar, wrap=True, level=1.0):
    """Pad sott'acqua molto basso: l'accordo di ogni battuta in due ottave gravi, onde morbide e un po'
    scordate, filtro passa-basso che respira; gli accordi si sciolgono l'uno nell'altro."""
    out = np.zeros((2, n))
    t_all = tvec(n)
    for i, (root, ch) in enumerate(chords):
        tones = [root - 12, root, ch[0] - 12, ch[1] - 12, ch[2] - 12]
        d = bar * 1.7
        m = ns(d)
        t = tvec(m)
        env = curve(m, [(0, 0), (bar * 0.45, 1), (bar * 1.05, 1), (d, 0)])
        for c in range(2):
            y = np.zeros(m)
            for j, mm in enumerate(tones):
                f = float(midi_hz(mm)) * cents(rng.normal(0, 4) + (6 if c else -6))
                ph = rng.uniform(0, TWO_PI)
                a = 1.0 if j < 2 else 0.6
                for k in range(1, 7):
                    y += a / k ** 1.3 * np.sin(TWO_PI * k * f * t + ph * k)
            place(out[c:c + 1], (y * env)[None], i * bar - bar * 0.35, wrap=wrap)
    # il filtro che respira (8 s: cicli interi su 64 s) e l'acqua che ondeggia
    lfo = 0.5 + 0.5 * np.sin(TWO_PI * t_all / 8.0)
    lp = 260.0 + 220.0 * lfo
    res = np.zeros_like(out)
    for c in range(2):
        res[c] = circular(lambda x: tv_lowpass(x, np.concatenate([lp[-ns(2.0):], lp, lp[:ns(2.0)]])[:len(x)], q=0.9), out[c])
    return level * res


@sound('mus_title', 64.0, loop=True, channels=2, category='mus', gain=0.7, rms=-21.0, params={'rotate_max': 0.03})
def mus_title(s, rng):
    n = s.n
    box = music_box_track(rng, n, lullaby_notes(rng), wrap=True)
    box = circular(box_body, box, pad=1.0)
    # il carillon è appoggiato un po' a sinistra, su un tavolo; la stanza è piccola e di legno
    ir = reverb_ir(1.9, rng, lo=1.1, hi=0.45, attack=0.01, lp=6500, early=[(0.011, 0.35, -0.5), (0.019, 0.25, 0.6)])
    dry = pan(box, -0.15)
    wet = convolve(box, ir, circular=True)
    mb = dry + 0.32 * wet
    # il meccanismo: il ventolino del regolatore che frulla e il cilindro che gira
    t = tvec(n)
    whir = spectral_noise(n, rng, lambda f: bw_bp(f, 300, 2500, 2)) * (0.6 + 0.4 * np.sin(TWO_PI * 22.0 * t) ** 2)
    mb += stereo(0.0022 * whir)
    # sotto, il pad sott'acqua (molto basso)
    pad = underwater_pad(rng, n, CHORDS, BAR)
    pad = pad * rms(mb) / (rms(pad) + 1e-12) * db_to_lin(-17.0)
    pad = pad + 0.6 * convolve(pad.mean(axis=0), reverb_ir(3.5, rng, lo=1.2, hi=0.3, lp=1500), circular=True) * db_to_lin(-3)
    # l'ultima battuta senza tonica: dal fondo, lontanissimo, il lamento della Madre
    moan = whale_moan(rng, 4.2, [(0, 62), (1.6, 88), (3.0, 74), (4.2, 50)], [(0, 'u'), (1.8, 'o'), (4.2, 'u')], scale=0.5,
                      amp_pts=[(0, 0), (1.2, 1), (3.0, 0.7), (4.2, 0)])
    mw = np.zeros(n)
    place(mw, moan, 23 * BAR - 0.4, wrap=True)
    mw = circular(lambda x: lowpass(x, 500, 2), mw)
    mw_rev = convolve(mw, reverb_ir(5.0, rng, lo=1.2, hi=0.3, attack=0.08, lp=900), circular=True)
    mw_all = 0.3 * stereo(mw) + mw_rev
    mw_all *= rms(mb) * db_to_lin(-22.0) / (db_to_lin(active_rms_db(mw_all)) + 1e-12)
    out = tape(mb + pad, rng) + mw_all
    # il nastro: un velo di soffio, gli acuti consumati, una saturazione appena
    hiss = np.stack([spectral_noise(n, rng, lambda f: bw_bp(f, 400, 9000, 1), exponent=0.6) for _ in range(2)])
    out = out + hiss * rms(out) * db_to_lin(-36.0)
    out = circular(lambda x: lowpass(highpass(x, 35, 2), 7200, 2), out)
    return circular(lambda x: softclip(x / (np.max(np.abs(x)) + 1e-9) * 0.9, 1.15), out, pad=0.2)


# ───────────────────────── stinger ─────────────────────────

def _choir_voice(rng, d, midi, vowels, amp_pts, scale=0.92, vib=(22.0, 5.2)):
    """Una voce grave del coro (tre cantori leggermente scordati: il coro non è mai perfetto)."""
    out = np.zeros(ns(d))
    f = float(midi_hz(midi))
    for det in (-9.0, 0.0, 11.0):
        fp = [(0, f * cents(det - 20)), (0.6, f * cents(det)), (d, f * cents(det - 8))]
        out += creature(rng, d, fp, vowels, scale=scale * rng.uniform(0.97, 1.03), amp_pts=amp_pts, oq=0.65,
                        jitter=0.006, shimmer=0.04, breath=0.18, vib=vib, bw_scale=1.2, wander=6.0)
    return normalize(out)


@sound('mus_night_start', 4.0, channels=2, category='mus', gain=0.8, rms=-18.0)
def mus_night_start(s, rng):
    """Un colpo basso e cupo, poi il carillon che accenna l'inizio della ninna nanna, rallenta e si spegne
    nel riverbero, una lamella sempre più calante."""
    n = s.n
    out = np.zeros((2, n))
    b = boom(rng, dur=3.9, f_start=60.0, f_end=29.0, t60=2.4, thump=0.7)
    place(out, stereo(0.85 * b), 0.0)
    # un rintocco grave e metallico sotto il colpo (una boa in lontananza)
    bell = church_bell(rng, 98.0, dur=3.9, t60=4.5, bright=0.55, beat=0.7, strike=0.3)
    place(out, stereo(0.18 * lowpass(bell, 1800, 2)), 0.0)
    notes = [(0.18, 76, 0.85, 0), (0.66, 72, 0.72, -8), (1.24, 69, 0.62, -18), (2.02, 71, 0.5, -34)]
    mb = np.zeros(n)
    for t0, m, v, det in notes:
        place(mb, tine_note(rng, m, v, dur=3.0, detune=TUNING[m] + det), t0)
    ir = reverb_ir(3.4, rng, lo=1.2, hi=0.4, attack=0.02, lp=5000)
    out += 0.55 * pan(mb, -0.12) + 0.6 * convolve(mb, ir)
    return lowpass(highpass(out, 25, 2), 9000, 2)


@sound('mus_6am', 7.0, channels=2, category='mus', gain=0.8, rms=-19.0)
def mus_6am(s, rng):
    """Le sei: un accordo di La maggiore che si apre (la ninna nanna finalmente in maggiore, risolta),
    campanelle e celesta che salgono, un respiro di sollievo."""
    n = s.n
    t = tvec(n)
    out = np.zeros((2, n))
    # pad caldo che si apre: corde morbide, il filtro che sale piano
    chord = [45, 52, 57, 61, 64, 69]
    env = curve(n, [(0, 0), (0.9, 0.7), (2.5, 1.0), (5.0, 0.8), (7.0, 0)])
    for c in range(2):
        y = np.zeros(n)
        for m in chord:
            f = float(midi_hz(m)) * cents(rng.normal(0, 3) + (5 if c else -5))
            vib = cents(9 * np.sin(TWO_PI * 5.0 * t + rng.uniform(0, TWO_PI)))
            y += additive(f * vib, lambda k: 1.0 / k ** 1.1, n_harm=14) * (0.8 if m < 50 else 1.0)
        y = tv_lowpass(y, curve(n, [(0, 300), (2.2, 2600), (7.0, 1800)], 'log'), q=0.8)
        out[c] = y * env
    # la ninna nanna in maggiore, al carillon, che sale fino alla tonica
    mb = np.zeros(n)
    tt = 0.55
    for m in [76, 73, 69, 71, 73, 74, 76, 81]:
        place(mb, tine_note(rng, m, 0.7, dur=3.0, detune=TUNING[m] * 0.4), tt)
        tt += 0.29
    place(mb, tine_note(rng, 69, 0.6, dur=3.5, detune=0.0), tt - 0.29)
    # celesta e campanelle: arpeggio luminoso, due rintocchi chiari
    gl = np.zeros(n)
    for i, m in enumerate([81, 85, 88, 93]):
        place(gl, glock(rng, float(midi_hz(m)), 0.5, dur=3.0), 2.9 + 0.22 * i)
    hb = small_bell(rng, float(midi_hz(93)), n, [(0.0, 0.45), (2.85, 0.35)], t60=2.5, beat=2.0, click=0.05)
    ir = reverb_ir(2.8, rng, lo=1.1, hi=0.5, attack=0.02, lp=8000)
    bells = pan(mb, -0.2) * 0.6 + pan(gl, 0.25) * 0.45 + pan(hb, 0.1) * 0.12
    out = out / (np.max(np.abs(out)) + 1e-9) * 0.35 + bells
    out = out + 0.45 * convolve(out.mean(axis=0), ir)
    return lowpass(highpass(out, 35, 2), 11000, 2)


@sound('mus_gameover', 8.0, channels=2, category='mus', gain=0.8, rms=-19.0)
def mus_gameover(s, rng):
    """Il carillon che si scarica: la ninna nanna rallenta, ogni lamella più calante, l'ultima nota pizzicata
    appena; la molla si ferma con un tonfo. Sotto, un bordone grave che stride (La e Si bemolle)."""
    n = s.n
    t = tvec(n)
    out = np.zeros((2, n))
    mb = np.zeros(n)
    tt = 0.0
    gaps = [0.44, 0.5, 0.58, 0.69, 0.83, 1.02, 1.28]
    for i, m in enumerate([76, 72, 69, 71, 72, 74, 76, 71]):
        det = TUNING[m] - 14.0 * i ** 1.3
        v = 0.9 * 0.88 ** i
        place(mb, tine_note(rng, m, v, dur=3.2, detune=det), tt)
        if i < len(gaps):
            tt += gaps[i]
    # la molla scarica: il cilindro si ferma, il regolatore sbatte
    stop_t = tt + 0.9
    nk = ns(0.4)
    exc = np.zeros(nk)
    exc[:3] = [1.0, -0.5, 0.2]
    clunk = modal(exc, [180.0, 410.0, 1230.0, 2650.0], [0.12, 0.08, 0.04, 0.02], [1.0, 0.7, 0.4, 0.25])
    place(mb, 0.18 * normalize(clunk), stop_t)
    whir = bandpass(rng.standard_normal(n), 300, 2500) * curve(n, [(0, 0.6), (stop_t - 0.6, 0.35), (stop_t, 0.0), (8, 0)])
    whir *= 0.6 + 0.4 * np.sin(TWO_PI * phase_of(curve(n, [(0, 24), (stop_t, 6), (8, 6)]))) ** 2
    mb += 0.012 * whir
    ir = reverb_ir(2.6, rng, lo=1.2, hi=0.4, attack=0.015, lp=6000)
    out += 0.6 * pan(mb, -0.1) + 0.45 * convolve(mb, ir)
    # bordone grave che stride e cresce
    dr = np.zeros(n)
    for m, a in [(33, 1.0), (34, 0.7), (45, 0.4)]:
        f = float(midi_hz(m))
        dr += a * additive(np.full(n, f) * cents(6 * rand_curve(n, 0.3, rng)), lambda k: 1.0 / k ** 1.6, n_harm=8)
    dr = lowpass(dr, 320, 2) * curve(n, [(0, 0), (2.5, 0.8), (5.5, 1.0), (8, 0)])
    out += 0.22 * np.stack([dr, np.roll(dr, ns(0.011))]) / (np.max(np.abs(dr)) + 1e-9)
    return lowpass(highpass(out, 25, 2), 8000, 2)


@sound('mus_madre', 10.0, channels=2, category='mus', gain=0.9, rms=-18.0)
def mus_madre(s, rng):
    """La Madre si sveglia: un colpo enorme sott'acqua, poi un lamento lentissimo da balena abissale e,
    dentro, un coro grave in minore che sale e si ritira. Tutto lontano, sotto l'acqua."""
    n = s.n
    out = np.zeros((2, n))
    # il colpo: una coda gigantesca che sposta l'acqua
    nw = ns(2.5)
    whump = lowpass(rng.standard_normal(nw), 120, 2) * exp_env(nw, 1.2, attack=0.006)
    whump = 0.7 * normalize(whump) + 0.8 * boom(rng, dur=2.5, f_start=46.0, f_end=24.0, t60=1.8, thump=0.3)
    place(out, stereo(whump), 0.0)
    # il lamento: la voce più grande che ci sia (formanti bassissime), e il canto più acuto che la accompagna
    deep = whale_moan(rng, 7.6, [(0, 30), (2.2, 44), (4.2, 57), (6.0, 43), (7.6, 27)],
                      [(0, 'u'), (1.8, 'o'), (4.2, 'a'), (6.2, 'o'), (7.6, 'u')], scale=0.4,
                      amp_pts=[(0, 0), (1.3, 0.8), (4.2, 1.0), (6.0, 0.5), (7.6, 0)], sub=0.3, breath_amt=0.08)
    song = whale_moan(rng, 6.8, [(0, 150), (2.2, 236), (4.0, 318), (5.4, 205), (6.8, 118)],
                      [(0, 'u'), (2.2, 'o'), (4.0, 'a'), (6.8, 'u')], scale=0.62,
                      amp_pts=[(0, 0), (1.8, 0.7), (4.0, 1.0), (5.6, 0.45), (6.8, 0)], sub=0.1)
    wl = np.zeros(n)
    place(wl, deep, 0.25)
    place(wl, 0.45 * song, 1.3)
    # il coro grave: La minore (La1, Mi2, La2, Do3, Mi3), cresce con il lamento e si ritira
    ch = np.zeros(n)
    for m, a, t0 in [(33, 1.0, 1.2), (40, 0.8, 1.6), (45, 0.75, 2.0), (48, 0.6, 2.5), (52, 0.45, 3.0)]:
        d = 7.5 - t0
        v = _choir_voice(rng, d, m, [(0, 'u'), (d * 0.4, 'o'), (d * 0.7, 'O'), (d, 'u')],
                         [(0, 0), (d * 0.4, 0.8), (d * 0.62, 1.0), (d - 1.5, 0.5), (d, 0)])
        place(ch, a * v, t0)
    voices = normalize(wl) + 0.6 * normalize(ch)
    voices = lowpass(voices, 1300, 2)
    # bolle enormi che salgono dal fondo
    bb = np.zeros(n)
    for _ in range(14):
        place(bb, bubble(float(loguniform(rng, 60, 180)), rng.uniform(0.0, 0.12), rng.uniform(0.3, 1.0), decay_mult=0.4,
                         max_dur=0.8), rng.uniform(1.0, 7.0))
    ir = reverb_ir(4.2, rng, lo=1.3, hi=0.25, attack=0.1, lp=1800)
    wet = convolve(voices + 0.25 * lowpass(bb, 700, 2), ir)
    out += 0.6 * stereo(voices) + 0.6 * wet
    return lowpass(highpass(out, 20, 2), 6000, 2)
