"""
Il montaggio del trailer A «Le regole» (scelto dall'utente il 14 ottobre; da approvare). Mette insieme le scene prese
dal motore (scripts/trailer.mjs) con le regole dei mostri a tutto schermo, la radio della prima notte coi sottotitoli,
il Catalogo, l'insegna al neon e «Wishlist now». Il suono è fatto coi suoni del gioco (public/assets/audio) e con la
voce della radio e la conta di Hatch come le fa il gioco (scripts/voci.mjs); le parole delle regole e della radio sono
quelle dei testi inglesi del gioco (src/i18n.ts: le regole della notte extra, la chiamata della prima notte). Esce un
MP4 1920×1080 a 30 fotogrammi al secondo, H.264 e AAC, come lo chiede Steam.

La grana della pellicola del gioco costa moltissimo al compressore (a qualità piena 70 secondi pesavano 226 MB): prima
di comprimere la si attenua appena (hqdn3d leggero; Steam comunque ricomprime i trailer). Così il file sta sotto i 50 MB.

Uso: tools/.venv/bin/python tools/trailer/montaggio.py <scene> <voci.json> <uscita.mp4> [--senza-demo] [--crf N]
     [--fermi <cartella>]
  <scene>       la cartella di scripts/trailer.mjs
  <voci.json>   quello di scripts/voci.mjs
  --senza-demo  senza la riga della demo gratuita in fondo (se la demo non è ancora su Steam)
  --crf N       la qualità dell'H.264 (21 di base, sotto i 50 MB; più basso, più pesante)
  --fermi       invece del video, un fotogramma ogni mezzo secondo come JPEG nella cartella (per guardare il montaggio)
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
IMG = os.path.join(RADICE, 'public', 'assets', 'img')
AUDIO = os.path.join(RADICE, 'public', 'assets', 'audio')
FONT = os.path.join(RADICE, 'public', 'fonts')
W, H, FPS, SR = 1920, 1080, 30, 48000

# i colori del gioco (src/styles.css)
INK = (233, 226, 208)
AMBER = (255, 179, 92)
NOTTE = (5, 8, 13)

# ── il montaggio: le scene una dopo l'altra (nome, secondi) ──
SEQUENZA = [
    ('nero', 1.5),
    ('apertura', 10.7),
    ('pesca', 5.6),
    ('catalogo', 1.6),
    ('gulpy', 4.0),
    ('molly', 3.8),
    ('hatch', 3.8),
    ('robin', 3.6),
    ('archie', 3.6),
    ('lampy', 3.3),
    ('fangy', 3.3),
    ('soggy', 3.1),
    ('madre', 9.6),
    ('jumpscare', 2.6),
    ('buio', 1.0),
    ('logo', 8.9),
]
INIZIO = {}
_t = 0.0
for _n, _d in SEQUENZA:
    INIZIO.setdefault(_n, _t)
    _t += _d
DURATA = _t
SECONDI = dict(SEQUENZA)

# le regole: chi, il nome che si legge, quando entra la scritta (secondi dall'inizio della sua scena: col gesto che la
# rispetta, dove c'è)
REGOLE = {
    'gulpy': ('Gulpy', 'gulpy', 1.7),
    'molly': ('Molly', 'molly', 1.5),
    'hatch': ('Hatch', 'hatch', 2.35),
    'robin': ('Robin', 'robin', 1.75),
    'archie': ('Archie', 'archie', 2.05),
    'lampy': ('Lampy', 'lampy', 1.3),
    'fangy': ('Fangy', 'fangy', 1.5),
    'soggy': ('Soggy', 'foxy', 1.25),
    'madre': ('The Mother', 'mother', 6.6),
}
# la radio della prima notte comincia qui (secondi del trailer), la musica si taglia qui (il cuore resta solo)
RADIO_DA = INIZIO['apertura'] + 2.1
TAGLIO = INIZIO['madre'] + 7.0


# ───────────────────────── i testi del gioco ─────────────────────────

def testi():
    """Le regole della notte extra, il nome della radio e la chiamata della prima notte, in inglese (src/i18n.ts)."""
    s = open(os.path.join(RADICE, 'src', 'i18n.ts'), encoding='utf-8').read()
    en = s[s.index('const EN: typeof IT = {'):]
    en = en[:en.index('\n};')]
    blocco = re.search(r'extraRules: \{([^}]*)\}', en).group(1)
    regole = {k: a or b for k, a, b in re.findall(r"(\w+): (?:'([^']*)'|\"([^\"]*)\")", blocco)}
    radio = re.search(r"radioName: '([^']*)'", en).group(1)
    r1 = s[s.index('export const RADIO_NIGHT1'):]
    r1 = r1[r1.index('  en: ['):]
    r1 = r1[:r1.index('],')]
    righe = [(float(a), t) for a, t in re.findall(r"\{ at: ([\d.]+), text: '([^']*)' \}", r1)]
    return regole, radio, righe


# ───────────────────────── le scritte ─────────────────────────

def carattere(nome, size, peso=None):
    f = ImageFont.truetype(nome, size)
    if peso is not None:
        f.set_variation_by_axes([peso, min(60, max(8, size))])
    return f


def serif_ttf(cartella):
    """Source Serif 4 del gioco (woff2) in TTF, per PIL."""
    from fontTools.ttLib import TTFont
    out = os.path.join(cartella, 'SourceSerif4.ttf')
    if not os.path.exists(out):
        f = TTFont(os.path.join(FONT, 'SourceSerif4-latin.woff2'))
        f.flavor = None
        f.save(out)
    return out


def riga(testo, font, colore, spazio=0.0, ombra=0.85, sfocata=16, alone=None):
    """Una riga di testo come immagine RGBA, con l'ombra morbida sotto (e un alone colorato, se c'è): spazio è la
    spaziatura fra le lettere in frazioni della dimensione del carattere."""
    size = font.size
    passo = spazio * size
    larghi = [font.getlength(c) for c in testo]
    largo = sum(larghi) + passo * (len(testo) - 1)
    asc, disc = font.getmetrics()
    m = sfocata * 3
    w, h = int(largo + 2 * m), int(asc + disc + 2 * m)
    maschera = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(maschera)
    x = m
    for c, l in zip(testo, larghi):
        d.text((x, m), c, font=font, fill=255)
        x += l + passo
    a = np.asarray(maschera).astype(np.float32) / 255
    s1 = np.asarray(maschera.filter(ImageFilter.GaussianBlur(sfocata))).astype(np.float32) / 255
    s2 = np.asarray(maschera.filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255
    ombre = np.clip(s1 * 1.6 * ombra + s2 * ombra, 0, 1)
    rgb = np.zeros((h, w, 3), np.float32)
    al = ombre.copy()
    if alone is not None:
        g = np.asarray(maschera.filter(ImageFilter.GaussianBlur(sfocata * 0.8))).astype(np.float32) / 255 * alone[1]
        rgb = rgb * (1 - g[..., None]) + np.array(alone[0], np.float32) / 255 * g[..., None]
        al = np.maximum(al, g)
    rgb = rgb * (1 - a[..., None]) + np.array(colore, np.float32) / 255 * a[..., None]
    al = np.maximum(al, a)
    return np.dstack([rgb, al])


def adatta(testo, nome, size, massimo, spazio=0.0):
    """La dimensione più grande (fino a size) con cui la riga sta in massimo pixel."""
    while size > 20:
        f = carattere(nome, size)
        if sum(f.getlength(c) for c in testo) + spazio * size * (len(testo) - 1) <= massimo:
            return f
        size -= 4
    return carattere(nome, size)


def sopra(fondo, img, cx, cy, alfa=1.0, scala=1.0):
    """Mette img (RGBA float) su fondo (RGB float) col centro in (cx, cy), alla scala e con l'alfa dati."""
    if alfa <= 0.002:
        return
    if abs(scala - 1) > 0.002:
        h, w = img.shape[:2]
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGBA')
        im = im.resize((max(1, round(w * scala)), max(1, round(h * scala))), Image.BICUBIC)
        img = np.asarray(im).astype(np.float32) / 255
    h, w = img.shape[:2]
    x0, y0 = round(cx - w / 2), round(cy - h / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    pezzo = img[ya - y0:yb - y0, xa - x0:xb - x0]
    k = pezzo[..., 3:] * alfa
    fondo[ya:yb, xa:xb] = fondo[ya:yb, xa:xb] * (1 - k) + pezzo[..., :3] * k


def liscio(a, b, x):
    k = min(1.0, max(0.0, (x - a) / (b - a)))
    return k * k * (3 - 2 * k)


# ───────────────────────── il suono ─────────────────────────

_suoni = {}


def suono(nome):
    """Un suono del gioco, stereo a 48 kHz."""
    if nome not in _suoni:
        b = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(AUDIO, nome + '.ogg'), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                           capture_output=True, check=True).stdout
        _suoni[nome] = np.frombuffer(b, np.float32).reshape(-1, 2).copy()
    return _suoni[nome]


def voce(c):
    """Una frase registrata da scripts/voci.mjs (i due canali in float32, in base64)."""
    l = np.frombuffer(base64.b64decode(c['l']), np.float32)
    r = np.frombuffer(base64.b64decode(c['r']), np.float32)
    x = np.stack([l, r], 1)
    if c.get('sr', SR) != SR:
        raise SystemExit(f"voce a {c['sr']} Hz: attesi {SR}")
    return x


def colpo():
    """Il colpo che accompagna ogni regola: un tonfo basso che scende, con un poco di rumore all'attacco."""
    n = int(2.4 * SR)
    t = np.arange(n) / SR
    f = 36 + 34 * np.exp(-t * 6)
    corpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.9)
    rng = np.random.default_rng(7)
    rumore = rng.standard_normal(n).astype(np.float32)
    # il rumore passa da un filtro passa basso (a un polo) e muore in fretta
    y = np.zeros(n, np.float32)
    acc = 0.0
    for i in range(int(0.25 * SR)):
        acc += 0.08 * (rumore[i] - acc)
        y[i] = acc
    attacco = y * np.exp(-t * 18)
    x = 0.95 * corpo + 1.6 * attacco
    x = x / np.abs(x).max()
    return np.stack([x, x], 1).astype(np.float32)


class Mix:
    def __init__(self, secondi):
        self.buf = np.zeros((int(secondi * SR) + SR, 2), np.float32)

    def metti(self, x, t, db=0.0, dur=None, entra=0.0, esce=0.0, da=0.0):
        """x a t secondi, col guadagno in dB, tagliato a dur secondi (da `da` secondi del suono), con le dissolvenze."""
        x = x[int(da * SR):]
        if dur is not None:
            x = x[:int(dur * SR)]
        x = x * (10 ** (db / 20))
        n = len(x)
        if n == 0:
            return
        env = np.ones(n, np.float32)
        if entra > 0:
            k = min(n, int(entra * SR))
            env[:k] *= np.linspace(0, 1, k, dtype=np.float32)
        if esce > 0:
            k = min(n, int(esce * SR))
            env[n - k:] *= np.linspace(1, 0, k, dtype=np.float32)
        i = int(round(t * SR))
        if i < 0:
            x, env, i = x[-i:], env[-i:], 0
        fine = min(len(self.buf), i + len(x))
        self.buf[i:fine] += x[:fine - i] * env[:fine - i, None]

    def ciclo(self, x, t0, t1, db=0.0, entra=0.0, esce=0.0, inviluppo=None):
        """x ripetuto da t0 a t1; inviluppo: [(secondo, guadagno lineare)] sul tempo del trailer."""
        n = int((t1 - t0) * SR)
        y = np.tile(x, (n // len(x) + 1, 1))[:n]
        if inviluppo:
            tt = t0 + np.arange(n) / SR
            y = y * np.interp(tt, [p[0] for p in inviluppo], [p[1] for p in inviluppo]).astype(np.float32)[:, None]
        self.metti(y, t0, db, entra=entra, esce=esce)


def colonna(voci, neve):
    """La colonna sonora del trailer. neve: quando comincia e quando finisce la neve dopo il jumpscare (secondi del
    trailer)."""
    m = Mix(DURATA)
    A, P, C = INIZIO['apertura'], INIZIO['pesca'], INIZIO['catalogo']
    G, Mo, Ha, R, Ar, L, F, So, Md, J, Lo = (INIZIO[k] for k in ['gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy', 'soggy', 'madre', 'jumpscare', 'logo'])
    boom = colpo()

    # il mare: entra dal nero, si ferma quando arriva la Madre (come nel gioco), sparisce al taglio
    m.ciclo(suono('amb_sea'), 0.0, J, -11, inviluppo=[(0, 0), (2.8, 1), (Md, 1), (Md + 3.2, 0.15), (TAGLIO, 0.0), (J, 0.0)])
    m.metti(suono('foghorn'), 0.3, -17, esce=1.5)
    # la luce che si accende
    m.metti(suono('lamp_switch'), A + 1.5, -1)
    m.metti(suono('lamp_flicker'), A + 1.52, -11)
    m.metti(suono('lamp_flicker'), A + 1.9, -15)
    # la radio della prima notte (la voce del gioco), col fruscio
    m.metti(suono('radio_on'), RADIO_DA - 0.08, -7)
    righe = [c for c in voci['radio_en'] if not c.get('end')]
    fine_radio = RADIO_DA + max(c['at'] for c in voci['radio_en'])
    m.ciclo(suono('radio_static'), RADIO_DA, min(fine_radio, P), -25, entra=0.2, esce=0.25)
    for c in righe:
        if RADIO_DA + c['at'] < P:
            m.metti(voce(c), RADIO_DA + c['at'], 1.5, dur=P - (RADIO_DA + c['at']), esce=0.05)
    m.metti(suono('radio_off'), min(fine_radio, P) - 0.05, -7)
    # la ninna nanna del titolo, sotto la radio e la pesca
    m.ciclo(suono('mus_title'), A + 1.1, G + 0.6, 0, inviluppo=[(A + 1.1, 0), (A + 3.5, 0.08), (P - 0.4, 0.08), (P + 0.6, 0.17), (G - 0.2, 0.17), (G + 0.6, 0)])
    # la pesca
    m.metti(suono('cast'), P + 0.25, -5)
    m.metti(suono('plop'), P + 1.25, -6)
    m.metti(suono('rod_bell_1'), P + 1.72, -5)
    m.ciclo(suono('reel_loop'), P + 2.45, P + 4.3, -10, esce=0.1)
    m.metti(suono('fish_out'), P + 4.25, -5)
    m.metti(suono('ui_page'), C, -7)

    # i mostri: la tensione del gioco sotto, il bordone; a ogni regola il colpo
    m.ciclo(suono('tensione_bassa'), G - 0.3, Ar, -4, entra=0.6, esce=0.4)
    m.ciclo(suono('tensione_alta'), Ar - 0.2, Md + 1.0, -3, entra=0.4, esce=1.2)
    m.ciclo(suono('amb_drone'), G - 0.3, TAGLIO, -8, entra=1.0, esce=0.05)
    for chi, (_, _, quando) in REGOLE.items():
        m.metti(boom, INIZIO[chi] + quando, -2 if chi != 'madre' else 0)
    # Gulpy si aggrappa (la luce sfarfalla), gorgoglia, gli arriva il pesce e mastica
    m.metti(suono('gulpy_grab'), G + 0.05, -3)
    m.metti(suono('lamp_flicker'), G + 0.05, -10)
    m.metti(suono('gulpy_gurgle_1'), G + 1.0, -6)
    m.metti(suono('fish_throw'), G + 2.5, -5)
    m.metti(suono('gulpy_eat_1'), G + 2.65, -4, dur=Mo - G - 2.65, esce=0.2)
    # Molly bussa, si affaccia, ridacchia
    m.metti(suono('molly_knock_1'), Mo - 0.1, -5)
    m.metti(suono('molly_peek'), Mo + 0.35, -5)
    m.metti(suono('molly_giggle_1'), Mo + 2.4, -7)
    # Hatch sale e conta (la conta del gioco), il telone
    m.metti(suono('hatch_rise'), Ha, -5)
    for k, quando in enumerate([0.25, 1.3, 2.35, 3.4]):
        if k < len(voci['conta_en']):
            m.metti(voce(voci['conta_en'][k]), Ha + quando, 2, dur=min(1.0, R - Ha - quando), esce=0.05)
    m.metti(suono('tarp_in'), Ha + 2.35, -3)
    # Robin sale, fruga nel secchio; la luce al massimo e scappa
    m.metti(suono('robin_climb'), R, -4)
    m.metti(suono('robin_rattle_1'), R + 1.3, -6)
    m.metti(suono('lamp_switch'), R + 1.75, -3)
    m.metti(suono('robin_scared'), R + 3.25, -4, dur=Ar - R - 3.25, esce=0.1)
    # Archie prende fiato; la luce si spegne
    m.metti(suono('archie_inhale'), Ar, -3, dur=2.1, esce=0.12)
    m.metti(suono('lamp_switch'), Ar + 2.05, -2)
    # Lampy: il campanellino a tempo, la risatina, affiora
    m.metti(suono('lampy_bell'), L + 0.02, -4)
    m.metti(suono('lampy_giggle'), L + 0.12, -7)
    m.metti(suono('lampy_bell'), L + 0.64, -4)
    m.metti(suono('lampy_surface'), L + 0.64, -5)
    # Fangy: le lucine arrivano, sale, lo scatto al rumore
    m.metti(suono('fangy_approach'), F, -5, dur=1.0, esce=0.2)
    m.metti(suono('fangy_rise'), F + 0.9, -4)
    m.metti(suono('fangy_snap'), F + 2.3, -2)
    # Soggy nel binocolo
    m.metti(suono('foxy_near'), So + 0.4, -5)
    # la Madre: il suono dell'avvicinamento, la luce che trema, la sua ninna nanna; al taglio resta solo il cuore
    m.metti(suono('madre_approach'), Md, -2, dur=TAGLIO - Md, esce=0.06)
    for k in (1.1, 3.0, 5.6):
        m.metti(suono('lamp_flicker'), Md + k, -10)
    m.metti(suono('madre_lullaby'), Md + 3.0, -8, dur=TAGLIO - Md - 3.0, entra=2.0, esce=0.06)
    m.metti(suono('madre_breath'), TAGLIO, -14, dur=J - TAGLIO, entra=0.3, esce=0.1)
    for k in (0.05, 0.85, 1.55, 2.15):
        m.metti(suono('heartbeat'), TAGLIO + k, -1)
    # il jumpscare, poi la neve, poi niente
    m.metti(suono('js_molly'), J + 0.04, 0)
    m.metti(suono('static_burst'), neve[0], -3, dur=neve[1] - neve[0], esce=0.03)
    # l'insegna al neon che si accende (un colpo quando resta accesa), la ninna nanna del titolo
    for k, db in ((0.08, -11), (0.3, -10), (0.42, -13), (3.6, -14)):
        m.metti(suono('lamp_flicker'), Lo + k, db)
    m.metti(boom, Lo + 0.62, -3)
    m.ciclo(suono('mus_title'), Lo + 0.6, DURATA, 0, inviluppo=[(Lo + 0.6, 0), (Lo + 1.6, 0.45), (DURATA - 1.6, 0.45), (DURATA, 0)])
    return m.buf[:int(DURATA * SR)]


def sonorita(x, cartella):
    """La sonorità integrata (LUFS) secondo ffmpeg (EBU R128)."""
    wav = os.path.join(cartella, 'misura.wav')
    scrivi_wav(wav, np.clip(x, -1, 1))
    err = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-i', wav, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', err)[-1])


def limita(x, tetto):
    """Un limitatore semplice: guarda 5 ms avanti, rilascia in 150 ms; nessun campione sopra il tetto."""
    B = 64
    n = len(x)
    nb = (n + B - 1) // B
    p = np.zeros(nb * B, np.float32)
    p[:n] = np.abs(x).max(axis=1)
    picco = p.reshape(nb, B).max(axis=1)
    g = np.minimum(1.0, tetto / np.maximum(picco, 1e-9))
    av = max(1, int(0.005 * SR / B))
    g = np.array([g[i:i + av + 1].min() for i in range(nb)], np.float32)
    rel = np.exp(-B / (0.15 * SR))
    out = np.empty(nb, np.float32)
    cur = 1.0
    for i in range(nb):
        cur = g[i] if g[i] < cur else g[i] + (cur - g[i]) * rel
        out[i] = cur
    gs = np.interp(np.arange(n) / B, np.arange(nb), out).astype(np.float32)
    return np.clip(x * gs[:, None], -tetto, tetto)


def volume(x, cartella, obiettivo=-16.0):
    """Il volume da trailer: la sonorità a obiettivo LUFS, i picchi (il jumpscare) sotto -1,5 dB."""
    x = x / np.abs(x).max()
    x = x * 10 ** ((obiettivo - sonorita(x, cartella)) / 20)
    return limita(x, 10 ** (-1.5 / 20))


def scrivi_wav(percorso, x):
    import wave
    with wave.open(percorso, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


# ───────────────────────── le immagini ─────────────────────────

class Scene:
    def __init__(self, cartella):
        self.cartella = cartella
        self.file = {}
        for n in SECONDI:
            d = os.path.join(cartella, n)
            if os.path.isdir(d):
                self.file[n] = sorted(f for f in os.listdir(d) if f.endswith('.jpg'))

    def indice(self, nome, t):
        """Quale fotogramma della scena va a t secondi dal suo inizio (anche da un'anteprima con meno fotogrammi)."""
        fs = self.file.get(nome)
        if not fs:
            raise SystemExit(f'manca la scena «{nome}» in {self.cartella} (scripts/trailer.mjs)')
        return min(len(fs) - 1, int(t / SECONDI[nome] * len(fs)))

    def secondi(self, nome, i):
        """A che secondo del trailer comincia il fotogramma i della scena."""
        return INIZIO[nome] + i / len(self.file[nome]) * SECONDI[nome]

    def fotogramma(self, nome, t):
        i = self.indice(nome, t)
        return np.asarray(Image.open(os.path.join(self.cartella, nome, self.file[nome][i])).convert('RGB')).astype(np.float32) / 255


def neve_in(scene):
    """La neve dopo il jumpscare (il segnale perso): i fotogrammi tutti granelli, il primo e l'ultimo (indici della
    scena). Dopo la neve il gioco torna a disegnare la barca dietro i risultati: nel trailer lì c'è il nero."""
    fs = scene.file['jumpscare']
    neve = []
    for i, f in enumerate(fs):
        a = np.asarray(Image.open(os.path.join(scene.cartella, 'jumpscare', f)).convert('L').resize((480, 270))).astype(np.float32)
        if np.abs(np.diff(a, axis=1)).mean() > 12:
            neve.append(i)
    if not neve:
        raise SystemExit('nella scena del jumpscare non c’è la neve del segnale perso')
    return neve[0], neve[-1]


class Montaggio:
    def __init__(self, scene, voci_testi, demo, tmp):
        self.scene = scene
        self.neve = neve_in(scene)
        regole, radio, righe = voci_testi
        lime = os.path.join(FONT, 'Limelight-Regular.ttf')
        serif = serif_ttf(tmp)
        # le regole: il nome in ambra spaziato, la regola grande
        self.regole = {}
        for chi, (nome, chiave, _) in REGOLE.items():
            testo = regole[chiave].upper().replace("'", '’') + '.'
            fr = adatta(testo, lime, 132, W * 0.84, 0.02)
            self.regole[chi] = (
                riga(nome.upper(), carattere(lime, 46), AMBER, spazio=0.3, ombra=0.9, sfocata=12),
                riga(testo, fr, INK, spazio=0.02, ombra=0.95, sfocata=20),
            )
        # la radio: come i sottotitoli del gioco (.hud-sub), più grandi
        fs = carattere(serif, 48, peso=500)
        fw = carattere(serif, 28, peso=600)
        self.radio = []
        for k, (at, testo) in enumerate(righe):
            if not testo:
                continue
            fine = righe[k + 1][0] if k + 1 < len(righe) else at + 2
            self.radio.append((RADIO_DA + at, RADIO_DA + fine, self.sottotitolo(radio, testo, fs, fw)))
        # il logo e le scritte della fine
        logo = Image.open(os.path.join(IMG, 'logo', 'logo.webp')).convert('RGBA')
        tre = Image.open(os.path.join(IMG, 'logo', 'logo_tremolio.webp')).convert('RGBA')
        lw = 1240
        lh = round(logo.height * lw / logo.width)
        self.logo = np.asarray(logo.resize((lw, lh), Image.LANCZOS)).astype(np.float32) / 255
        self.tremolio = np.asarray(tre.resize((lw, lh), Image.LANCZOS)).astype(np.float32) / 255
        self.wishlist = riga('WISHLIST NOW', carattere(lime, 78), AMBER, spazio=0.12, ombra=0.6, sfocata=18, alone=((255, 140, 40), 0.55))
        self.demo = riga('Free demo: the first two nights', carattere(serif, 46, peso=500), INK, ombra=0.8, sfocata=10) if demo else None
        self.catalogo = np.asarray(Image.open(os.path.join(RADICE, 'steam', 'screenshot', '07_catalogo.jpg')).convert('RGB')).astype(np.float32) / 255

    @staticmethod
    def sottotitolo(chi, testo, fs, fw):
        """Il riquadro del sottotitolo del gioco: fondo nero al 60%, il filo ambra a sinistra, chi parla in alto."""
        pad_x, pad_y, filo = 34, 20, 4
        tw = fs.getlength(testo)
        cw = sum(fw.getlength(c) for c in chi.upper()) + 0.25 * fw.size * (len(chi) - 1)
        w = int(max(tw, cw) + 2 * pad_x)
        h = int(pad_y * 2 + fw.size + 10 + fs.size * 1.3)
        im = Image.new('RGBA', (w, h), (0, 0, 0, 153))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, filo - 1, h), fill=AMBER + (255,))
        x = pad_x
        for c in chi.upper():
            d.text((x, pad_y - 4), c, font=fw, fill=AMBER + (255,))
            x += fw.getlength(c) + 0.25 * fw.size
        d.text((pad_x, pad_y + fw.size + 6), testo, font=fs, fill=INK + (255,))
        return np.asarray(im).astype(np.float32) / 255

    def fotogramma(self, t):
        nome, t0 = None, 0.0
        for n, d in SEQUENZA:
            if t < t0 + d or n == SEQUENZA[-1][0]:
                nome = n
                break
            t0 += d
        u = t - t0
        if nome in ('nero', 'buio'):
            f = np.zeros((H, W, 3), np.float32)
        elif nome == 'catalogo':
            f = self.zoom(self.catalogo, 1.0 + 0.05 * u / SECONDI['catalogo'])
        elif nome == 'logo':
            f = self.fine(u)
        elif nome == 'jumpscare' and self.scene.indice(nome, u) > self.neve[1]:
            f = np.zeros((H, W, 3), np.float32)
        else:
            f = self.scene.fotogramma(nome, u)
        if nome == 'apertura':
            # dal nero
            f = f * liscio(0, 1.2, u)
            for da, a, img in self.radio:
                k = liscio(da, da + 0.2, t) * (1 - liscio(a - 0.2, a, t))
                sopra(f, img, W / 2, H * 0.86, k)
        if nome in REGOLE:
            self.regola(f, nome, u)
        return f

    @staticmethod
    def zoom(img, z):
        h, w = img.shape[:2]
        cw, ch = w / z, h / z
        x0, y0 = (w - cw) / 2, (h - ch) / 2
        im = Image.fromarray((img * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        return np.asarray(im).astype(np.float32) / 255

    def regola(self, f, chi, u):
        """La regola a tutto schermo: lo schermo si scurisce, la scritta entra con un colpo (un poco più grande, poi
        al suo posto) e resta fino al taglio."""
        da = REGOLE[chi][2]
        if u < da:
            return
        k = liscio(da, da + 0.16, u)
        # lo scuro: tutto un poco, il basso di più (dove sta la scritta)
        y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        scuro = 0.2 + 0.55 * np.clip((y - 0.5) / 0.4, 0, 1)
        f *= 1 - k * scuro
        nome, testo = self.regole[chi]
        s = 1.0 + 0.1 * (1 - liscio(da, da + 0.22, u))
        sopra(f, testo, W / 2, H * 0.80, liscio(da, da + 0.08, u), s)
        sopra(f, nome, W / 2, H * 0.685, liscio(da + 0.08, da + 0.24, u))

    def fine(self, u):
        """L'insegna al neon che si accende a scatti; la S spenta prova una volta a riaccendersi; «Wishlist now»."""
        f = np.zeros((H, W, 3), np.float32) + np.array(NOTTE, np.float32) / 255
        # gli scatti dell'accensione (acceso/spento), poi accesa
        scatti = [(0.0, 0.0), (0.08, 1.0), (0.13, 0.0), (0.3, 1.0), (0.36, 0.25), (0.42, 1.0), (0.5, 0.0), (0.62, 1.0)]
        luce = 0.0
        for da, v in scatti:
            if u >= da:
                luce = v
        # la S: tre colpi corti (acceso 70 ms, spento 60, acceso 120), come nel menu
        s = 3.6
        img = self.tremolio if (s <= u < s + 0.07) or (s + 0.13 <= u < s + 0.25) else self.logo
        sopra(f, img, W / 2, H * 0.40, luce)
        sopra(f, self.wishlist, W / 2, H * 0.73, liscio(1.9, 2.4, u))
        if self.demo is not None:
            sopra(f, self.demo, W / 2, H * 0.81, liscio(2.5, 3.0, u))
        # in fondo, al nero
        return f * (1 - liscio(SECONDI['logo'] - 1.0, SECONDI['logo'], u))


def main():
    args = sys.argv[1:]
    demo = '--senza-demo' not in args
    fermi = args[args.index('--fermi') + 1] if '--fermi' in args else None
    crf = args[args.index('--crf') + 1] if '--crf' in args else '21'
    pos = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--fermi', '--crf'))]
    if len(pos) < 3:
        raise SystemExit(__doc__)
    cartella, voci_json, uscita = pos[:3]
    with open(voci_json, encoding='utf-8') as fh:
        voci = json.load(fh)
    scene = Scene(cartella)
    with tempfile.TemporaryDirectory() as tmp:
        mont = Montaggio(scene, testi(), demo, tmp)
        n = int(round(DURATA * FPS))
        if fermi:
            os.makedirs(fermi, exist_ok=True)
            for i in range(0, n, FPS // 2):
                f = mont.fotogramma(i / FPS)
                Image.fromarray((np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(fermi, f'm{i:04d}.jpg'), quality=88)
            print('fermi in', fermi)
            return
        a, b = mont.neve
        neve = (scene.secondi('jumpscare', a), scene.secondi('jumpscare', b + 1))
        audio = volume(colonna(voci, neve), tmp)
        wav = os.path.join(tmp, 'colonna.wav')
        scrivi_wav(wav, audio)
        ff = subprocess.Popen([
            'ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
            '-i', wav, '-vf', 'hqdn3d=1.5:1.5:4:4', '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-pix_fmt', 'yuv420p', '-profile:v', 'high',
            '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', uscita,
        ], stdin=subprocess.PIPE)
        for i in range(n):
            f = mont.fotogramma(i / FPS)
            ff.stdin.write((np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
            if i % 300 == 0:
                print(f'{i / FPS:5.1f} s', flush=True)
        ff.stdin.close()
        if ff.wait() != 0:
            raise SystemExit('ffmpeg non ce l’ha fatta')
    print(uscita)


if __name__ == '__main__':
    main()
