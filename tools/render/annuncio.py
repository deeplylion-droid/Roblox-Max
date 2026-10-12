"""
L'annuncio con cui il pescatore ha trovato il lavoro: la schermata di 3-4 secondi dopo «Nuova partita», prima della
notte 1, con una lenta zoomata (idea dell'utente del 12 ottobre, come in FNAF). Due proposte da approvare:

  giornale  (A) il ritaglio della pagina degli annunci della «Gazzetta del Golfo» (il giornale della lore), posato sul
            banco di legno della barca alla luce della lanterna: l'annuncio cerchiato due volte a penna rossa, accanto
            un pezzo di articolo tagliato dal bordo («…SPLASHLAND RESTA CHIUSO»), la foto in mezzatinta dell'ingresso,
            gli altri annunci di un paese di mare;
  volantino (B) il volantino allegro di Mama Marina's Splashland, sbiadito e fradicio, inchiodato a un palo del molo
            di notte, illuminato dalla torcia; un angolo strappato e le linguette da staccare quasi tutte già prese.

Composizione 2D in Python (numpy, scipy, Pillow), senza Blender: la stampa si compone su un foglio piatto (colore,
rilievo, bagnato, trasparenza), poi il foglio si posa nella scena e si illumina coi rilievi (pieghe, grinze, gocce).
Si lavora al doppio della risoluzione finale e si riduce alla fine.

Uso: tools/.venv/bin/python tools/render/annuncio.py <giornale|volantino|tutti> [--lingua it,en] [--uscita cartella]
     [--scala 1.0] [--webp]   (il volantino italiano è volantino.webp, le traduzioni volantino_<lingua>.webp)
     (--scala 1.5 dà 2880×1620, per avere margine nella zoomata)
I font (SIL Open Font License, da Google Fonts) sono in tools/render/fonts/annuncio/.
"""
from __future__ import annotations

import math
import os
import re
import sys
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter, map_coordinates, binary_dilation, distance_transform_edt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FONTS = os.path.join(ROOT, 'tools', 'render', 'fonts')
IMG = os.path.join(ROOT, 'public', 'assets', 'img')

SCALA = float(sys.argv[sys.argv.index('--scala') + 1]) if '--scala' in sys.argv else 1.0
FW, FH = int(1920 * SCALA), int(1080 * SCALA)     # l'immagine finale
SW, SH = FW * 2, FH * 2                             # la scena si calcola al doppio


@lru_cache(None)
def font(nome: str, px: int) -> ImageFont.FreeTypeFont:
    p = os.path.join(FONTS, 'annuncio', nome + '.ttf')
    if not os.path.exists(p):
        p = os.path.join(FONTS, nome + '.ttf')
    return ImageFont.truetype(p, int(px))


def srgb_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_srgb(c):
    c = np.clip(c, 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def rumore(rng, shape, sigma, ottave=1, decad=0.5):
    """Rumore liscio a media 0 e deviazione 1 (somma di ottave)."""
    out = np.zeros(shape, np.float32)
    amp, tot = 1.0, 0.0
    for o in range(ottave):
        s = sigma / (2 ** o)
        if s > 6:
            # a bassa risoluzione e poi ingrandito: molto più veloce
            k = int(s / 3)
            small = gaussian_filter(rng.standard_normal((shape[0] // k + 2, shape[1] // k + 2)).astype(np.float32), s / k)
            n = np.array(Image.fromarray(small).resize((small.shape[1] * k, small.shape[0] * k), Image.BICUBIC))[:shape[0], :shape[1]]
        else:
            n = gaussian_filter(rng.standard_normal(shape).astype(np.float32), s)
        out += amp * n / (n.std() + 1e-6)
        tot += amp
        amp *= decad
    return out / tot


# ───────────────────────── tipografia ─────────────────────────

VOCALI = set('aeiouàèéìíòóùúAEIOUÀÈÉÌÒÙ')
INSEPARABILI = {'bl', 'br', 'cl', 'cr', 'dr', 'fl', 'fr', 'gl', 'gr', 'pl', 'pr', 'tr', 'vr', 'ch', 'gh', 'gn', 'sc'}


def sillabe(parola: str) -> list[int]:
    """Dove si può andare a capo in una parola italiana (regole semplici: V-CV, doppie, s impura, nessi con l e r)."""
    m = re.match(r"^([«(\"']*)(.*?)([»).,;:!?\"']*)$", parola)
    pre, w, _ = m.groups()
    if not w.isalpha() or len(w) < 5:
        return []
    lw = w.lower()
    pos = []
    i = 1
    n = len(lw)
    while i < n:
        if lw[i - 1] in VOCALI and lw[i] not in VOCALI:
            j = i
            while j < n and lw[j] not in VOCALI:
                j += 1
            if j >= n:
                break
            run = lw[i:j]
            if len(run) == 1:
                b = i
            elif run[0] == 's' or run[:2] in INSEPARABILI or (len(run) == 2 and run[1] in 'lr' and run[0] not in 'lmnr'):
                b = i
            else:
                b = i + 1
            if 2 <= b <= n - 2:
                pos.append(b + len(pre))
            i = j
        else:
            i += 1
    return pos


class Tipo:
    """Compone colonne giustificate (con la sillabazione) su un livello d'inchiostro in scala di grigi."""

    def __init__(self, img: Image.Image):
        self.img = img
        self.d = ImageDraw.Draw(img)

    def righe(self, gettoni, larg, sp):
        righe, cur, curw = [], [], 0.0
        gettoni = list(gettoni)
        i = 0
        while i < len(gettoni):
            w, f = gettoni[i]
            ww = f.getlength(w)
            need = ww if not cur else curw + sp + ww
            if need <= larg:
                cur.append((w, f)); curw = need; i += 1
                continue
            avail = larg - (curw + sp if cur else 0)
            spezzata = False
            if curw / larg < 0.93 or not cur:
                for b in reversed(sillabe(w)):
                    pezzo = w[:b] + '-'
                    if f.getlength(pezzo) <= avail:
                        cur.append((pezzo, f)); gettoni[i] = (w[b:], f)
                        spezzata = True
                        break
            if not spezzata and not cur:
                cur.append((w, f)); i += 1
            righe.append(cur); cur, curw = [], 0.0
        if cur:
            righe.append(cur + [None])     # l'ultima riga del paragrafo non si giustifica
        return righe

    def paragrafo(self, x, y, larg, testo, f, interl, grassetto=None, fg=None, rientro=0, giustifica=True,
                  colore=255, centra=False, limite=None, disegna=True):
        """Scrive un paragrafo; 'grassetto' è l'attacco in neretto (come negli annunci). Restituisce la nuova y."""
        gettoni = []
        if grassetto:
            gettoni += [(w, fg) for w in grassetto.split()]
        gettoni += [(w, f) for w in testo.split()]
        sp = f.getlength(' ')
        prima = True
        for riga in self.righe(gettoni, larg - rientro, sp) if rientro else self.righe(gettoni, larg, sp):
            if limite is not None and y > limite:
                break
            ultima = riga[-1] is None
            riga = [r for r in riga if r is not None]
            x0 = x + (rientro if prima else 0)
            lw = larg - (rientro if prima else 0)
            tot = sum(g.getlength(w) for w, g in riga)
            if centra:
                cx = x0 + (lw - tot - sp * (len(riga) - 1)) / 2
                gap = sp
            elif giustifica and not ultima and len(riga) > 1:
                cx, gap = x0, (lw - tot) / (len(riga) - 1)
            else:
                cx, gap = x0, sp
            for w, g in riga:
                if disegna:
                    self.d.text((cx, y), w, font=g, fill=colore)
                cx += g.getlength(w) + gap
            y += interl
            prima = False
        return y

    def testo(self, x, y, s, f, colore=255, anchor='la'):
        self.d.text((x, y), s, font=f, fill=colore, anchor=anchor)

    def riga(self, x0, y0, x1, y1, w=2, colore=255):
        self.d.line((x0, y0, x1, y1), fill=colore, width=w)


def mezzatinta(gray: np.ndarray, cella: float, angolo=45.0, guadagno=1.0):
    """Retino a punti tondi (mezzatinta da giornale) da un'immagine in [0,1] (0 = nero): restituisce la copertura."""
    h, w = gray.shape
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    a = math.radians(angolo)
    u = (xx * math.cos(a) + yy * math.sin(a)) / cella
    v = (-xx * math.sin(a) + yy * math.cos(a)) / cella
    fu, fv = u - np.floor(u) - 0.5, v - np.floor(v) - 0.5
    dist = np.sqrt(fu ** 2 + fv ** 2)            # 0 al centro della cella, ~0.707 agli angoli
    scuro = np.clip((1 - gray) * guadagno, 0, 1)
    r = np.sqrt(scuro / math.pi)                 # raggio del punto per coprire la frazione 'scuro'
    # nelle zone molto scure i punti si fondono: il retino diventa negativo (buchi bianchi)
    r = np.where(scuro > 0.78, 0.707 - np.sqrt((1 - scuro) / math.pi) * 0.9, r)
    return np.clip((r - dist) * cella * 0.9 + 0.5, 0, 1)


# ───────────────────────── carta, rilievo e luce ─────────────────────────

def normali(h, forza=1.0):
    gy, gx = np.gradient(h)
    n = np.dstack([-gx * forza, -gy * forza, np.ones_like(h)])
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def fibre(rng, shape):
    fine = rumore(rng, shape, 0.8)
    medio = rumore(rng, shape, 3.0)
    fib = gaussian_filter(rng.standard_normal(shape).astype(np.float32), (0.7, 4.0))
    fib /= fib.std()
    return (0.5 * fine + 0.35 * medio + 0.25 * fib)


def macchia(rng, shape, cx, cy, rx, ry, lobi=5):
    """Una macchia d'acqua irregolare: (dentro in [0,1], alone sul bordo)."""
    h, w = shape
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    ang = np.arctan2(yy - cy, xx - cx)
    f1, f2, f3 = rng.uniform(0, 6.28, 3)
    rr = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    rr = rr * (1 + 0.13 * np.sin(ang * lobi + f1) + 0.07 * np.sin(ang * (lobi * 2 + 3) + f2) + 0.04 * np.sin(ang * 23 + f3))
    rr = rr + 0.05 * rumore(rng, shape, 30)
    dentro = np.clip((1 - rr) / 0.08, 0, 1)
    alone = np.exp(-((rr - 1.0) / 0.018) ** 2) + 0.4 * np.exp(-((rr - 0.93) / 0.012) ** 2)
    return dentro, alone


def tonemap(x):
    """Curva filmica morbida (Hable) sul lineare."""
    A, B, C, D, E, F = 0.22, 0.30, 0.10, 0.20, 0.01, 0.30
    f = lambda v: ((v * (A * v + C * B) + D * E) / (v * (A * v + B) + D * F)) - E / F
    return f(x * 2.2) / f(np.float32(5.0))


def finitura(lin, rng, vignetta=0.55, grana=0.018, aberr=1.2):
    """Dal lineare all'immagine finale: tonemap, vignettatura, aberrazione cromatica, grana, riduzione a FW×FH."""
    h, w, _ = lin.shape
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    r2 = ((xx - w / 2) / (w / 2)) ** 2 * 0.8 + ((yy - h / 2) / (h / 2)) ** 2
    lin = lin * (1 - vignetta * np.clip(r2 / 1.8, 0, 1) ** 1.3)[..., None]
    out = lin_srgb(tonemap(lin))
    if aberr:
        # aberrazione cromatica radiale leggerissima (rosso fuori, blu dentro)
        for c, k in ((0, 1.0), (2, -1.0)):
            s = 1 + k * aberr / (w / 2)
            cy, cx = h / 2, w / 2
            out[..., c] = map_coordinates(out[..., c], [(yy - cy) / s + cy, (xx - cx) / s + cx], order=1, mode='nearest')
    im = Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((FW, FH), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    g = rng.standard_normal((FH, FW)).astype(np.float32)
    g = 0.7 * g + 0.3 * gaussian_filter(g, 0.8) / 0.45
    lum = a.mean(-1, keepdims=True)
    a = a + grana * g[..., None] * (0.35 + 0.65 * np.sqrt(np.clip(1 - lum, 0, 1)))
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def warp(arr, M, shape, order=1, cval=0.0):
    """Porta una mappa dal foglio alla scena: M è l'affine scena→foglio (2×3)."""
    h, w = shape
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    u = M[0, 0] * xx + M[0, 1] * yy + M[0, 2]
    v = M[1, 0] * xx + M[1, 1] * yy + M[1, 2]
    if arr.ndim == 2:
        return map_coordinates(arr, [v, u], order=order, mode='constant', cval=cval)
    return np.dstack([map_coordinates(arr[..., c], [v, u], order=order, mode='constant', cval=cval)
                      for c in range(arr.shape[2])])


def affine(cx_s, cy_s, cx_f, cy_f, scala, gradi):
    """Affine scena→foglio: il punto (cx_f, cy_f) del foglio va in (cx_s, cy_s), scalato e ruotato."""
    a = math.radians(gradi)
    ca, sa = math.cos(a) / scala, math.sin(a) / scala
    # foglio = R^-1 (scena - c_s) / scala + c_f
    return np.array([[ca, sa, cx_f - ca * cx_s - sa * cy_s],
                     [-sa, ca, cy_f + sa * cx_s - ca * cy_s]], np.float32)


def legno_assi(rng, shape, dir_x=True, larg_asse=520, base=(0.30, 0.22, 0.15), giunti=True):
    """Assi di legno vecchio e bagnato: colore (sRGB), rilievo, bagnato. Le venature corrono lungo x."""
    h, w = shape
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    if not dir_x:
        xx, yy = yy, xx
    off = yy + 18 * rumore(rng, shape, 300)
    asse = np.floor(off / larg_asse)
    fr = off / larg_asse - asse
    # ogni asse ha il suo tono e la sua venatura
    ids = asse.astype(int) % 64
    toni = rng.uniform(0.75, 1.15, 64).astype(np.float32)
    caldo = rng.uniform(-0.06, 0.06, 64).astype(np.float32)
    fase = rng.uniform(0, 1000, 64).astype(np.float32)
    tono = toni[ids]
    # venature: rumore stirato lungo x, deformato
    stir = gaussian_filter(rng.standard_normal((h // 4 + 2, w // 24 + 2)).astype(np.float32), (1.2, 2.0))
    stir = np.array(Image.fromarray(stir).resize((stir.shape[1] * 24, stir.shape[0] * 4), Image.BICUBIC))
    if not dir_x:
        stir = np.array(Image.fromarray(stir.T.copy()).resize((h + 50, w + 50)[::-1], Image.BICUBIC)).T
    stir = stir[:h, :w] if dir_x else np.array(Image.fromarray(stir).resize((w, h)))
    stir = stir / (stir.std() + 1e-6)
    vena = np.sin((off * 0.9 + fase[ids] + 22 * stir + 6 * rumore(rng, shape, 60)) * 0.11)
    vena = 0.5 + 0.5 * vena
    vena_fine = rumore(rng, shape, 1.2) if dir_x else rumore(rng, shape, 1.2)
    graffi = gaussian_filter(rng.standard_normal(shape).astype(np.float32), (0.6, 14.0) if dir_x else (14.0, 0.6))
    graffi /= graffi.std()
    righe_ = gaussian_filter(rng.standard_normal(shape).astype(np.float32), (0.7, 36.0) if dir_x else (36.0, 0.7))
    righe_ /= righe_.std()
    nodi = np.clip(rumore(rng, shape, 50) - 1.6, 0, None)
    lum = tono * (0.70 + 0.30 * vena ** 2) * (1 + 0.16 * righe_) * (1 + 0.05 * vena_fine) * (1 + 0.05 * graffi) * (1 - 0.5 * nodi)
    # la fessura tra le assi
    fessura = np.zeros_like(fr)
    if giunti:
        d = np.minimum(fr, 1 - fr) * larg_asse
        fessura = np.clip(1 - d / 7.0, 0, 1) ** 1.5
    lum = lum * (1 - 0.92 * fessura)
    col = np.array(base, np.float32)[None, None] * lum[..., None]
    col[..., 0] *= 1 + caldo[ids]
    col[..., 2] *= 1 - caldo[ids]
    # sale e muffa lungo le fessure
    muffa = np.clip(rumore(rng, shape, 25, 2) * 0.6 - 0.2, 0, 1) * np.clip(1 - np.minimum(fr, 1 - fr) * 14, 0, 1)
    col = col * (1 - 0.25 * muffa[..., None]) + np.array([0.12, 0.13, 0.09]) * 0.25 * muffa[..., None]
    alt = 1.2 * vena + 0.6 * graffi + 0.8 * righe_ + 0.4 * vena_fine - 14 * fessura
    # bombatura delle assi
    alt += 8 * np.sin(np.clip(fr, 0, 1) * math.pi)
    bagnato = np.clip(rumore(rng, shape, 120, 2) * 0.9 + 0.2, 0, 1)
    return np.clip(col, 0, 1), alt, bagnato


# ───────────────────────── A · il ritaglio di giornale ─────────────────────────

# la pagina intera (in pixel del foglio): sei colonne, di cui si vede il ritaglio
PG_W, PG_H = 3720, 2240
COL_X0, COL_W, GUT = 60, 560, 40


def col(i):
    return COL_X0 + i * (COL_W + GUT)


ARTICOLO = [
    "Il cancello resta sbarrato, e la catena è nuova. Dopo l'ennesima seduta del consiglio comunale, ieri sera, il "
    "destino del parco acquatico della baia resta sospeso: al bando per la demolizione non ha risposto nessuna ditta. "
    "«Nessuno vuole lavorarci, nemmeno di giorno», ammette l'assessore ai lavori pubblici.",
    "Mama Marina's Splashland chiuse dopo la Night Splash del 14 agosto 1997, le tre notti di apertura straordinaria "
    "in cui sparirono tre bambini. Le ricerche dei sommozzatori nella piscina più profonda, la «Deep End», non "
    "diedero esito.",
    "Dei bambini nessuna traccia, né quell'estate né dopo. Nel 2001 la mareggiata allagò metà del parco; da allora "
    "gli scivoli, la ruota panoramica e la grande statua della balena sono rimasti dove sono, a guardare il mare.",
    "Chi abita sul lungomare racconta che di notte, d'estate, le luci della Deep End si accendono ancora sott'acqua. "
    "«È l'impianto, sarà un guasto», taglia corto il sindaco. Ma la corrente al parco è staccata da anni.",
    "Intanto, come ogni notte, le barche dei pescatori escono dal molo vecchio al tramonto e rientrano all'alba. "
    "In paese nessuno chiede che cosa peschino, né per chi.",
    "Il vecchio custode, che ha lavorato al parco dall'apertura fino all'ultima sera, non vuole parlarne. Dice solo "
    "che la statua di Mama Marina «andrebbe lasciata in pace» e che i cancelli, quella notte, li aveva chiusi lui. "
    "Alle sette del mattino li trovò aperti.",
    "Negli anni la Procura ha riaperto il fascicolo due volte, senza nuovi elementi. Le famiglie dei tre bambini "
    "chiedono ancora che la vasca venga svuotata. «Basterebbe una pompa», ripete la madre di uno di loro, che ogni "
    "anno, a metà agosto, porta dei fiori all'edicola sullo scoglio. «Nessuno la vuole accendere.»",
    "Al Comune la manutenzione costa ogni anno qualche migliaio di euro: catene, lucchetti, cartelli di pericolo. "
    "I cartelli spariscono in pochi giorni, i lucchetti vengono trovati aperti senza segni di scasso. L'ultima "
    "volta, a maggio, qualcuno ha riacceso l'insegna dell'ingresso per una notte intera.",
    "Una ditta di fuori, l'anno scorso, aveva accettato il lavoro. Gli operai sono venuti un lunedì con le ruspe; "
    "il martedì mattina se n'erano già andati, lasciando i mezzi davanti al cancello. Sono ancora lì, arrugginiti.",
    "In paese il parco non lo nomina quasi nessuno. I bambini lo chiamano «la balena» e ci vanno a guardare dalla "
    "spiaggia, di giorno, come si guarda una casa disabitata. I genitori li richiamano prima che faccia buio, e "
    "d'estate, la sera, sul lungomare non si fa più il bagno.",
    "Il prossimo consiglio è fissato per la fine del mese. All'ordine del giorno, di nuovo, il parco. (segue a pag. 17)",
]

ANNUNCI = [
    ('LAVORO', [
        ("AZIENDA ittica cerca", "addetti alla lavorazione del pesce, turno del mattino. Presentarsi in via del Porto 11."),
        ('CERCASI', '__PESCATORE__'),
        ("BABY SITTER cercasi", "per due bambini, 6 e 8 anni, solo di giorno. Referenze. Tel. 0544 31 27 09."),
        ("SIGNORA referenziata", "offresi per pulizie e stiro, zona porto e lungomare. Ore pasti 0544 30 18 66."),
    ]),
    ('IMMOBILI', [
        ("AFFITTASI", "bilocale sul lungomare, 4 posti letto, vista baia, terrazzo. Libero tutto l'anno. Prezzo da concordare."),
        ("VENDESI", "villetta con giardino in via delle Conchiglie, ristrutturata. Affare: i proprietari si trasferiscono al più presto."),
        ("AFFITTASI", "posto barca al molo vecchio, libero da subito. Il precedente affittuario non l'ha più ritirata."),
    ]),
    ('BARCHE E MOTORI', [
        ("VENDESI gozzo", "in legno, 6 metri, motore Lombardini revisionato, reti e nasse. Usato poco: solo di giorno. Tel. 0544 32 05 51."),
        ("CEDESI", "attività di articoli da pesca, esche vive e lenze, causa trasferimento. Svendita di tutta la merce."),
        ("VENDESI", "motore fuoribordo 15 cv, ottimo stato, con serbatoio. Tel. ore serali."),
    ]),
    ('COMPRAVENDITA', [
        ("VENDO", "lettino, seggiolone, braccioli e un salvagente a paperella, praticamente nuovi. Regalo a chi viene a prenderli."),
        ("COMPRO", "vecchie cartoline e souvenir della baia, anche rovinati. Massima serietà."),
    ]),
    ('SMARRITI E TROVATI', [
        ("SMARRITO", "cane meticcio, pelo fulvo, risponde al nome di Bricco. Visto l'ultima volta sul molo vecchio, di sera: "
                     "abbaiava verso l'acqua. Ricompensa."),
        ("TROVATO", "braccialetto di gomma azzurro con la scritta «NIGHT SPLASH», sulla spiaggia davanti al parco. "
                    "Rivolgersi all'edicola del porto."),
    ]),
    ('VARIE', [
        ("SI RINGRAZIA", "chi ha riportato in porto la barca «Santa Rita», trovata alla deriva all'alba. Del proprietario "
                         "si chiedono ancora notizie."),
        ("LEZIONI", "di nuoto per bambini, piscina coperta comunale. Iscrizioni aperte tutto l'anno. Al mare, no."),
        ("CERCO", "compagno per pesca sportiva la domenica mattina, con barca propria. Tel. 0544 33 41 20."),
        ("SABATO", "alle 18, nella chiesa di Sant'Andrea al porto, messa in ricordo dei bambini della baia. "
                   "Sono invitati tutti."),
        ("VENDO", "bicicletta da bambina, rosa, con le rotelle e il cestino. Tenuta in garage. Prezzo simbolico."),
        ("RIPARAZIONE", "reti e nasse, rammendo vele. Chiedere di Gino al molo nuovo."),
    ]),
]

PESCATORE = ("CERCASI PESCATORE", "per il turno di notte. Barca, luce e attrezzatura fornite. Dalle 0 alle 6. "
             "Paga in contanti all'alba. Nessuna esperienza richiesta. Presentarsi al molo vecchio, al tramonto.")


def impagina_giornale():
    """La pagina 15 della Gazzetta del Golfo: restituisce l'inchiostro (0..1), il riquadro dell'annuncio e la foto."""
    ink = Image.new('L', (PG_W, PG_H), 0)
    T = Tipo(ink)
    corpo = font('PTSerif-Regular', 34)
    corpo_b = font('PTSerif-Bold', 34)
    # testatina di pagina
    y = 38
    T.testo(col(1), y, 'Martedì', font('PTSerif-Italic', 34))
    T.testo((col(1) + col(5) + COL_W) / 2, y - 4, 'CRONACA DELLA BAIA', font('Oswald-SemiBold', 40), anchor='ma')
    gaz = font('UnifrakturMaguntia', 46)
    T.testo(col(5) + COL_W - 70, y - 8, 'Gazzetta del Golfo', gaz, anchor='ra')
    T.testo(col(5) + COL_W, y - 2, '15', font('Oswald-SemiBold', 44), anchor='ra')
    T.riga(0, 100, PG_W, 100, 5)
    T.riga(0, 110, PG_W, 110, 2)

    # ── l'articolo (colonne 0-2) ──
    y0 = 140
    T.testo(col(0) + 10, y0, 'IL PARCO ACQUATICO SULLA BAIA · IL COMUNE RINVIA ANCORA LA DEMOLIZIONE', font('Oswald-SemiBold', 34))
    tit = font('PlayfairDisplay-Black', 112)
    s = 'Così SPLASHLAND RESTA CHIUSO'
    # il titolo si allinea a destra sulla colonna 2: il bordo del ritaglio taglia il «Così»
    T.testo(col(2) + COL_W, y0 + 58, s, tit, anchor='ra')
    titolo_x0 = col(2) + COL_W - tit.getlength(s)
    sp_x = titolo_x0 + tit.getlength('Così ')       # dove comincia SPLASHLAND
    y = y0 + 230
    T.riga(col(0), y - 18, col(2) + COL_W, y - 18, 2)
    # sommario in corsivo sulle colonne 1-2
    y = T.paragrafo(col(1), y, 2 * COL_W + GUT, "Dei bambini nessuna traccia. Al bando per abbattere il parco non risponde "
                    "nessuno: i cancelli restano sbarrati, la grande vasca è ancora piena d'acqua.",
                    font('PTSerif-Italic', 50), 60, giustifica=False)
    y += 24
    # la foto (colonne 1-2) con la didascalia
    fx0, fy0, fx1 = col(1), y, col(2) + COL_W
    fy1 = fy0 + 760
    foto = (fx0, fy0, fx1, fy1)
    yc = fy1 + 16
    yc = T.paragrafo(fx0, yc, fx1 - fx0, "L'ingresso di Mama Marina's Splashland, com'è oggi. Lo striscione della «Night Splash» "
                     "non è del 1997: nessuno sa chi l'abbia appeso.", font('PTSerif-Italic', 30), 36, giustifica=False)
    yc += 14
    T.riga(fx0, yc - 4, fx1, yc - 4, 1)
    # il corpo dell'articolo: colonna 0 (tagliata dal bordo) dall'alto, poi 1 e 2 sotto la foto
    def scorri(paragrafi, colonne):
        k, (cx, cy, lim) = 0, colonne[0]
        for p in paragrafi:
            gett = p
            while gett:
                # componi riga per riga per poter cambiare colonna
                righe = T.righe([(w, corpo) for w in gett.split()], COL_W, corpo.getlength(' '))
                fatte = 0
                for r in righe:
                    if cy > lim:
                        k += 1
                        if k >= len(colonne):
                            return
                        cx, cy, lim = colonne[k]
                    ultima = r[-1] is None
                    r = [g for g in r if g is not None]
                    tot = sum(f.getlength(w) for w, f in r)
                    gap = (COL_W - tot) / (len(r) - 1) if (not ultima and len(r) > 1) else corpo.getlength(' ')
                    xx = cx + (36 if fatte == 0 and gett is p else 0) * 0
                    for w, f in r:
                        T.d.text((xx, cy), w, font=f, fill=255)
                        xx += f.getlength(w) + gap
                    cy += 43
                    fatte += 1
                gett = None
            cy += 8
    scorri(ARTICOLO, [(col(0), 400, PG_H - 80), (col(1), yc + 10, PG_H - 80), (col(2), yc + 10, PG_H - 80)])
    # filetti verticali tra le colonne dell'articolo
    T.riga(col(1) - GUT / 2, 380, col(1) - GUT / 2, PG_H - 60, 1)
    T.riga(col(2) - GUT / 2, yc + 10, col(2) - GUT / 2, PG_H - 60, 1)

    # ── i piccoli annunci (colonne 3-5) ──
    ax0, ax1 = col(3), col(5) + COL_W
    T.riga(col(3) - GUT / 2, 130, col(3) - GUT / 2, PG_H - 60, 3)
    y = 150
    T.testo((ax0 + ax1) / 2, y, 'PICCOLI ANNUNCI', font('PlayfairDisplay-Black', 104), anchor='ma')
    y += 128
    T.riga(ax0, y, ax1, y, 4)
    T.paragrafo(ax0, y + 12, ax1 - ax0, "Si ricevono in redazione, via del Porto 3, entro le ore 18 del giorno precedente. "
                "Tariffa: 0,50 euro a parola. Gli annunci anonimi non si pubblicano.", font('PTSerif-Italic', 30), 36,
                centra=True, giustifica=False)
    y += 104
    T.riga(ax0, y, ax1, y, 2)
    y += 26
    cat_f = font('Oswald-SemiBold', 34)
    lead_f = font('PTSerif-Bold', 33)
    ann_f = font('PTSerif-Regular', 33)
    colonne = [[col(3), y], [col(4), y], [col(5), y]]
    lim = PG_H - 470
    k = 0
    riquadro = None
    for cat, lista in ANNUNCI:
        # la testatina di categoria in negativo
        cx, cy = colonne[k]
        if cy > lim - 200:
            k += 1; cx, cy = colonne[k]
        T.d.rectangle((cx, cy, cx + COL_W, cy + 50), fill=255)
        T.testo(cx + COL_W / 2, cy + 4, cat, cat_f, colore=0, anchor='ma')
        cy += 66
        for lead, txt in lista:
            if txt == '__PESCATORE__':
                # l'annuncio del pescatore, in un riquadro (lo si è pagato di più)
                if cy > lim - 420:
                    colonne[k][1] = cy; k += 1; cx, cy = colonne[k]
                cy += 10
                bx0, by0 = cx, cy
                tit_f = font('PlayfairDisplay-Black', 50)
                T.testo(cx + COL_W / 2, cy + 24, PESCATORE[0], tit_f, anchor='ma')
                yy = T.paragrafo(cx + 26, cy + 98, COL_W - 52, PESCATORE[1], font('PTSerif-Regular', 39), 48,
                                 giustifica=True)
                by1 = yy + 18
                T.d.rectangle((bx0, by0, bx0 + COL_W, by1), outline=255, width=5)
                T.d.rectangle((bx0 + 10, by0 + 10, bx0 + COL_W - 10, by1 - 10), outline=255, width=2)
                riquadro = (bx0, by0, bx0 + COL_W, by1)
                cy = by1 + 26
                continue
            alto = T.paragrafo(cx, cy, COL_W, txt, ann_f, 40, grassetto=lead, fg=lead_f, disegna=False) - cy
            if cy + alto > lim:
                colonne[k][1] = cy; k += 1; cx, cy = colonne[k]
            cy = T.paragrafo(cx, cy, COL_W, txt, ann_f, 40, grassetto=lead, fg=lead_f) + 14
        colonne[k] = [cx, cy + 8]
    # in fondo alle colonne, i riquadri pubblicitari
    by = PG_H - 440
    def box(x0, x1, righe):
        yy = by + 34
        for s, f in righe:
            T.testo((x0 + x1) / 2, yy, s, f, anchor='ma')
            yy += f.size * 1.25
        T.d.rectangle((x0, by, x1, yy + 30), outline=255, width=4)
    box(col(3), col(4) + COL_W, [('PESCHERIA DA NINO', font('PlayfairDisplay-Black', 70)),
                                 ('pesce fresco ogni mattina, direttamente dalle barche', font('PTSerif-Italic', 38)),
                                 ('MOLO NUOVO · aperto dalle 7 alle 13', font('Oswald-SemiBold', 44)),
                                 ('La notte siamo chiusi.', font('PTSerif-Italic', 38))])
    box(col(5), col(5) + COL_W, [('FARMACIA', font('Oswald-SemiBold', 50)), ('DI TURNO', font('Oswald-SemiBold', 50)),
                                 ('Farmacia del Porto', font('PTSerif-Bold', 36)), ('via Marinai d\'Italia 2', font('PTSerif-Regular', 32)),
                                 ('tel. 0544 30 11 12', font('PTSerif-Regular', 32))])
    return np.asarray(ink, np.float32) / 255, riquadro, foto, sp_x


def foto_mezzatinta(box, shape):
    """La foto dell'ingresso del parco, in bianco e nero e a retino, dentro 'box' della pagina."""
    x0, y0, x1, y1 = [int(v) for v in box]
    im = Image.open(os.path.join(IMG, 'bino_ingresso_senza.webp')).convert('RGB')
    w, h = x1 - x0, y1 - y0
    # ritaglio sull'insegna e lo striscione
    W0, H0 = im.size
    cw = W0 * 0.92
    ch = cw * h / w
    cx, cy = W0 * 0.5, H0 * 0.43
    im = im.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((w, h), Image.LANCZOS)
    g = np.asarray(im.convert('L'), np.float32) / 255
    # stampa da giornale: contrasto forte, neri chiusi, bianchi sporchi
    g = np.clip((g - 0.04) / 0.50, 0, 1) ** 0.75
    g = gaussian_filter(g, 1.0)
    g = 0.22 + 0.74 * g
    cov = mezzatinta(g, 9.0, 45.0)
    out = np.zeros(shape, np.float32)
    out[y0:y1, x0:x1] = cov
    # il filetto attorno alla foto
    out[y0:y0 + 3, x0:x1] = 1; out[y1 - 3:y1, x0:x1] = 1; out[y0:y1, x0:x0 + 3] = 1; out[y0:y1, x1 - 3:x1] = 1
    return out


def cerchio_penna(rng, shape, box):
    """Il cerchio a penna rossa, a mano libera: tremolante, ripassato due volte, che non chiude bene."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2 + 6, (y0 + y1) / 2 - 4
    rx, ry = (x1 - x0) / 2 + 70, (y1 - y0) / 2 + 62
    layer = np.zeros(shape, np.float32)
    for passata in range(2):
        img = Image.new('L', (shape[1], shape[0]), 0)
        d = ImageDraw.Draw(img)
        start = rng.uniform(-2.4, -1.9) + passata * 0.5
        giri = 1.12 + 0.08 * passata
        n = 1600
        t = np.linspace(0, 1, n)
        a = start - t * giri * 2 * math.pi          # in senso antiorario, come chi è destro
        # deriva lenta (la mano che non chiude) + tremolio
        k = rng.uniform(0, 6.28, 6)
        trem = gaussian_filter(rng.standard_normal(n), 6) * 0.05 + gaussian_filter(rng.standard_normal(n), 2) * 0.012
        dr = (0.045 * np.sin(a * 1 + k[0]) + 0.03 * np.sin(a * 2 + k[1]) + 0.015 * np.sin(a * 3 + k[2])
              + 0.06 * t * (1 if passata else -1) + trem)
        rot = math.radians(rng.uniform(-4, -1))
        ex, ey = rx * (1 + dr) * np.cos(a), ry * (1 + dr * 1.3) * np.sin(a)
        px = cx + ex * math.cos(rot) - ey * math.sin(rot) + passata * rng.uniform(-6, 6)
        py = cy + ex * math.sin(rot) + ey * math.cos(rot) + passata * rng.uniform(-6, 6)
        press = 0.75 + 0.25 * np.sin(t * 23 + k[5]) * np.sin(t * 7)
        press *= np.clip(t / 0.04, 0.2, 1) * np.clip((1 - t) / 0.06, 0.15, 1)     # attacco e coda leggeri
        larg = 6.0 + 4.0 * press
        for i in range(n):
            r = larg[i]
            d.ellipse((px[i] - r, py[i] - r, px[i] + r, py[i] + r), fill=int(255 * (0.55 + 0.45 * press[i])))
        a_ = np.asarray(img, np.float32) / 255
        # la biro salta un po' sulla carta ruvida
        a_ *= np.clip(0.75 + 0.5 * rumore(rng, shape, 1.2), 0, 1) if passata == 0 else 1.0
        layer = 1 - (1 - layer) * (1 - a_ * 0.85)
    return layer


def giornale(uscita):
    rng = np.random.default_rng(1408)
    shape = (PG_H, PG_W)
    ink, riquadro, foto, sp_x = impagina_giornale()
    ink = np.maximum(ink, foto_mezzatinta(foto, shape))
    yy, xx = np.mgrid[:PG_H, :PG_W].astype(np.float32)

    # ── la sagoma del ritaglio: tagliato a forbice (tratti dritti, scalini) con l'angolo in basso a destra strappato ──
    L = sp_x - 30          # il taglio a sinistra passa appena prima di SPLASHLAND
    pts = [(L + 8, 26), (1500, 16), (2600, 30), (PG_W - 64, 22), (PG_W - 50, 900), (PG_W - 62, 1620),
           (PG_W - 330, PG_H - 70), (1900, PG_H - 52), (900, PG_H - 66), (L - 6, PG_H - 58), (L + 4, 1200)]
    sag = Image.new('L', (PG_W, PG_H), 0)
    dd = ImageDraw.Draw(sag)
    poly = []
    for i in range(len(pts)):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % len(pts)]
        seg = max(2, int(math.hypot(bx - ax, by - ay) / 6))
        strappo = i == 5      # il tratto strappato a mano
        for j in range(seg):
            t = j / seg
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            nx, ny = -(by - ay), bx - ax
            nl = math.hypot(nx, ny)
            if strappo:
                o = 22 * math.sin(t * 9.0) + rng.normal(0, 4.5)
            else:
                o = rng.normal(0, 0.6) + 3 * math.sin(t * 6.3 + i)     # la forbice va un po' a onde
            poly.append((x + nx / nl * o, y + ny / nl * o))
    dd.polygon(poly, fill=255)
    alfa = np.asarray(sag, np.float32) / 255
    alfa = gaussian_filter(alfa, 0.8)
    bordo_d = distance_transform_edt(alfa > 0.5)

    # ── la carta ──
    fib = fibre(rng, shape)
    carta = np.array([0.86, 0.80, 0.665], np.float32)[None, None] * (1 + 0.035 * fib[..., None])
    # ingiallita di più verso i bordi tagliati (ossidazione) e a chiazze
    ox = np.clip(1 - bordo_d / 90, 0, 1) ** 1.6 + 0.25 * np.clip(rumore(rng, shape, 260, 2), 0, 1)
    carta = carta * (1 - 0.18 * ox[..., None]) * np.array([1.0, 0.95, 0.80])[None, None] ** ox[..., None]
    # puntini di muffa (foxing)
    for _ in range(70):
        fx, fy, r = rng.uniform(0, PG_W), rng.uniform(0, PG_H), rng.uniform(1.5, 7)
        m = np.exp(-(((xx - fx) ** 2 + (yy - fy) ** 2) / (2 * r * r)))
        carta = carta * (1 - 0.25 * m[..., None] * np.array([0.25, 0.5, 0.9]))
    # le pieghe: una verticale e una orizzontale (il ritaglio è stato piegato in quattro per tenerlo nel portafoglio)
    fold_v = PG_W * 0.53 + 10 * rumore(rng, (1, PG_H), 80)[0][None, :].T * 0 + 0.012 * (yy - PG_H / 2)
    dv = xx - (PG_W * 0.535 + 0.012 * (yy - PG_H / 2))
    dh = yy - (PG_H * 0.47 - 0.006 * (xx - PG_W / 2))
    linea = np.exp(-(dv / 2.5) ** 2) + np.exp(-(dh / 2.5) ** 2)
    carta = carta * (1 - 0.16 * np.clip(linea, 0, 1)[..., None])
    # macchie d'acqua vecchie (asciutte, con l'alone)
    asciutte = np.zeros(shape, np.float32)
    aloni = np.zeros(shape, np.float32)
    for cx, cy, rx, ry in ((1300, 520, 330, 260), (2900, 260, 220, 150), (900, 1900, 280, 210)):
        a, b = macchia(rng, shape, cx, cy, rx, ry)
        asciutte = np.maximum(asciutte, a); aloni = np.maximum(aloni, b)
    carta = carta * (1 - 0.045 * asciutte[..., None]) * (1 - 0.30 * aloni[..., None] * np.array([0.25, 0.48, 0.85]))
    # bagnato adesso: in basso a destra e una pozza sul bordo sinistro
    w1, _ = macchia(rng, shape, PG_W - 250, PG_H - 180, 900, 620, lobi=4)
    w2, a2 = macchia(rng, shape, L + 60, 1500, 260, 420, lobi=3)
    bagnato = np.clip(gaussian_filter(np.maximum(w1, w2 * 0.9), 16), 0, 1)

    # ── l'inchiostro: grana della carta, inchiostrazione irregolare, consumato sulle pieghe, sbavato dove è bagnato ──
    ink = gaussian_filter(ink, 0.55)
    ink = ink * np.clip(0.86 + 0.14 * fib + 0.06 * rumore(rng, shape, 180), 0, 1)
    ink = ink * (1 - 0.55 * np.clip(linea, 0, 1))
    ink = ink * (1 - bagnato) + gaussian_filter(ink, 1.6) * bagnato
    # il retro della pagina che traspare (un'altra pagina, rovesciata), molto di più dove è bagnato
    retro = np.roll(ink[:, ::-1], (37, 310), (0, 1))
    retro = gaussian_filter(retro, 2.2)
    trasp = 0.07 + 0.33 * bagnato
    nero = np.array([0.10, 0.09, 0.09], np.float32)
    col_ = carta * (1 - (retro * trasp)[..., None] * 0.6)
    col_ = col_ * (1 - ink[..., None]) + nero * ink[..., None] * (col_ / 0.8)
    # la penna rossa (fresca: sopra tutto, sbava un poco dove la carta è bagnata)
    pen = cerchio_penna(rng, shape, riquadro)
    pen = pen * (1 - bagnato * 0.5) + gaussian_filter(pen, 3.0) * bagnato * 0.9
    rosso = np.array([0.62, 0.03, 0.06], np.float32)
    col_ = col_ * (1 - pen[..., None] * 0.95) + (col_ * rosso / 0.85) * pen[..., None] * 0.95
    # la carta bagnata è più scura e più satura
    gr = col_.mean(-1, keepdims=True)
    col_ = col_ * (1 - 0.30 * bagnato[..., None])
    col_ = gr + (col_ - gr) * (1 + 0.25 * bagnato[..., None])
    # l'orlo bianchiccio dove è strappato (le fibre)
    alb = np.clip(col_, 0, 1)

    # ── il rilievo del foglio ──
    alt = np.zeros(shape, np.float32)
    alt += 16.0 * np.exp(-(np.abs(dv) / 90)) - 3.0 * np.exp(-(np.abs(dv) / 5))      # piega a monte
    alt += -12.0 * np.exp(-(np.abs(dh) / 80)) - 3.0 * np.exp(-(np.abs(dh) / 4))     # piega a valle
    alt += 2.2 * rumore(rng, shape, 90, 3) + 0.25 * fib
    alt += 4.0 * bagnato * rumore(rng, shape, 55, 2)                                # la carta bagnata si gonfia
    alt += 0.5 * ink                                                                 # l'inchiostro è un velo
    alt += 0.6 * pen
    # l'angolo strappato si alza un po'
    alt += 30 * np.clip((xx - PG_W * 0.80) / (PG_W * 0.2), 0, 1) ** 2 * np.clip((PG_H * 0.15 - yy) / (PG_H * 0.15), 0, 1) ** 2 * 0

    # ── la scena: il banco della barca, la lanterna ──
    scala = 0.86 * SCALA
    M = affine(SW * 0.5, SH * 0.5, (L + PG_W - 50) / 2, PG_H / 2 + 10, scala, -2.2)
    sw = (SH, SW)
    A = warp(alfa, M, sw)
    C = warp(alb, M, sw)
    Hh = warp(alt, M, sw) * scala
    B = warp(bagnato, M, sw)
    wcol, walt, wbag = legno_assi(rng, sw, dir_x=True, larg_asse=int(560 * SCALA), base=(0.27, 0.21, 0.155))
    # ombra del foglio sul legno (la luce viene dall'alto a sinistra)
    om = gaussian_filter(np.roll(A, (int(14 * SCALA), int(18 * SCALA)), (0, 1)), 10 * SCALA)
    alb_lin = srgb_lin(C) * A[..., None] + srgb_lin(wcol) * (1 - A[..., None])
    # la carta bagnata si fa trasparente: ci si vede il legno sotto
    wl = srgb_lin(wcol)
    tr = (0.5 * B * A)[..., None]
    alb_lin = alb_lin * (1 - tr) + alb_lin * np.clip(wl / (wl.mean() + 1e-4), 0.3, 1.6) * 0.75 * tr
    altezza = Hh * A + walt * 0.6 * (1 - A) + 3 * A
    n = normali(gaussian_filter(altezza, 0.8), 0.9)
    yy2, xx2 = np.mgrid[:SH, :SW].astype(np.float32)
    # la lanterna: in alto a sinistra fuori campo, calda
    lx, ly, lz = -0.10 * SW, -0.35 * SH, 0.95 * SW
    Lv = np.dstack([lx - xx2, ly - yy2, np.full_like(xx2, lz)])
    dist = np.linalg.norm(Lv, axis=-1)
    Lv /= dist[..., None]
    diff = np.clip((n * Lv).sum(-1), 0, 1)
    att = (lz / dist) ** 2.2
    # il cono della lanterna (più luce sull'annuncio, il resto cala)
    cono = np.exp(-(((xx2 - SW * 0.56) / (SW * 0.55)) ** 2 + ((yy2 - SH * 0.45) / (SH * 0.75)) ** 2))
    luce = np.array([1.0, 0.70, 0.40], np.float32) * 3.4
    amb = np.array([0.20, 0.28, 0.45], np.float32) * 0.10
    sha = 1 - 0.75 * om * (1 - A)
    Hv = Lv + np.array([0, 0, 1], np.float32)
    Hv /= np.linalg.norm(Hv, axis=-1, keepdims=True)
    ndh = np.clip((n * Hv).sum(-1), 0, 1)
    lucido = B * A * 0.9 + wbag * (1 - A) * 0.6
    spec = lucido * (ndh ** 120) * 0.7 + lucido * (ndh ** 16) * 0.03
    lin = alb_lin * (amb + luce * (diff * att * (0.25 + 0.75 * cono) * sha)[..., None])
    lin += luce * (spec * att * cono)[..., None]
    # un poco di sfocatura di campo sui bordi alti e bassi (la foto è fatta da vicino)
    sf = np.clip((np.abs(yy2 - SH * 0.5) / (SH * 0.5) - 0.55) / 0.45, 0, 1)
    blur = np.dstack([gaussian_filter(lin[..., c], 5 * SCALA) for c in range(3)])
    lin = lin * (1 - sf[..., None]) + blur * sf[..., None]
    out = finitura(lin, rng, vignetta=0.62)
    p = os.path.join(uscita, 'annuncio_giornale.jpg')
    out.save(p, quality=93, subsampling=0)
    # dove guardare per la zoomata: il riquadro cerchiato, in coordinate dell'immagine finale (0..1)
    Mi = np.vstack([M, [0, 0, 1]])
    inv = np.linalg.inv(Mi)
    bx0, by0, bx1, by1 = riquadro
    cxs, cys, _ = inv @ np.array([(bx0 + bx1) / 2, (by0 + by1) / 2, 1])
    print(f'giornale → {p}  (centro dell\'annuncio: x={cxs / SW:.3f}, y={cys / SH:.3f})', flush=True)


# ───────────────────────── B · il volantino del parco ─────────────────────────

VW, VH = 2480, 3508          # A4 a 300 dpi
NAVY = (22, 34, 92)
ROSA = (242, 104, 168)
CIANO = (96, 214, 226)
GIALLO = (255, 212, 52)

# Mama Marina, come la statua (tools/render/mascot.py), in coordinate del modello: x a destra, z in alto, alta ~1,2
MM_BLU = (66, 128, 214)
MM_BLU_OMBRA = (40, 86, 170)
MM_PANCIA = (250, 236, 200)
MM_GUANCE = (246, 128, 140)
MM_ZAMPILLO = (226, 246, 255)
MM_ZAMPILLO_SCURO = (140, 205, 240)
MM_PESCI = [(250, 128, 40), (252, 208, 40), (70, 180, 90)]


def sd_ellisse(x, y, cx, cy, rx, ry, gradi=0.0):
    a = math.radians(gradi)
    dx, dy = x - cx, y - cy
    u = dx * math.cos(a) + dy * math.sin(a)
    v = -dx * math.sin(a) + dy * math.cos(a)
    k = np.sqrt((u / rx) ** 2 + (v / ry) ** 2)
    return (k - 1) * min(rx, ry)


def sd_unione(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def sd_capsula(x, y, ax, ay, bx, by, r):
    px, py = x - ax, y - ay
    vx, vy = bx - ax, by - ay
    h = np.clip((px * vx + py * vy) / (vx * vx + vy * vy), 0, 1)
    return np.sqrt((px - vx * h) ** 2 + (py - vy * h) ** 2) - r


class Tela:
    """Un livello RGB in float su cui si dipinge con le maschere (antialias dalle distanze)."""

    def __init__(self, w, h, colore):
        self.a = np.ones((h, w, 3), np.float32) * np.array(colore, np.float32) / 255

    def dipingi(self, mask, colore, box=(0, 0)):
        x0, y0 = box
        h, w = mask.shape
        sub = self.a[y0:y0 + h, x0:x0 + w]
        sub[:] = sub * (1 - mask[..., None]) + np.array(colore, np.float32) / 255 * mask[..., None]

    def incolla(self, im: Image.Image, x, y):
        """Incolla un'immagine RGBA (testi, forme disegnate con Pillow)."""
        a = np.asarray(im, np.float32) / 255
        h, w = a.shape[:2]
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.a.shape[1], x + w), min(self.a.shape[0], y + h)
        if x1 <= x0 or y1 <= y0:
            return
        sa = a[y0 - y:y1 - y, x0 - x:x1 - x]
        sub = self.a[y0:y1, x0:x1]
        sub[:] = sub * (1 - sa[..., 3:4]) + sa[..., :3] * sa[..., 3:4]


def cop(sd, px=1.0):
    """Copertura antialias da una distanza in pixel."""
    return np.clip(0.5 - sd / px, 0, 1)


def mama_marina(tela: Tela, cx, base, alt):
    """Disegna Mama Marina a cartone: cx, base = punto in basso al centro (pixel), alt = altezza del corpo (pixel)."""
    S = alt / 1.0                      # pixel per unità del modello
    x0, x1 = int(cx - 0.95 * S), int(cx + 0.95 * S)
    y0, y1 = int(base - 1.36 * S), int(base + 0.04 * S)
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    X = (xx - cx) / S
    Z = (base - yy) / S
    px = 1.0 / S                       # un pixel in unità del modello
    o = 0.022                          # spessore del contorno

    corpo = sd_ellisse(X, Z, 0, 0.36, 0.36, 0.38)
    testa = sd_ellisse(X, Z, 0, 0.80, 0.36, 0.27)
    f = sd_unione(corpo, testa, 0.12)
    pinne = [sd_ellisse(X, Z, s * 0.52, 0.66, 0.24, 0.095, -s * 30) for s in (1, -1)]
    for p_ in pinne:
        f = sd_unione(f, p_, 0.06)
    # la coda dietro, con le pinne caudali a cuore che spuntano da dietro la testa
    coda = np.minimum(sd_ellisse(X, Z, 0.17, 1.0, 0.15, 0.06, -25), sd_ellisse(X, Z, -0.17, 1.0, 0.15, 0.06, 25))
    coda = np.minimum(coda, sd_capsula(X, Z, 0, 0.8, 0, 0.98, 0.05))
    # lo zampillo dello sfiatatoio: un getto che sale dritto, si apre in cima e ricade in gocce ai due lati
    def cono(z0, z1, r0, r1):
        t = np.clip((Z - z0) / (z1 - z0), 0, 1)
        return np.maximum(np.abs(X) - (r0 + (r1 - r0) * t), np.maximum(z0 - Z, Z - z1))
    getto = sd_unione(cono(1.0, 1.24, 0.026, 0.040), sd_ellisse(X, Z, 0, 1.265, 0.075, 0.042), 0.03)
    for s_ in (1, -1):
        getto = sd_unione(getto, sd_ellisse(X, Z, s_ * 0.075, 1.25, 0.05, 0.026, -s_ * 25), 0.02)
    venatura = np.maximum(cono(1.03, 1.22, 0.007, 0.012), getto + 0.012)
    gocce = []
    for s_ in (1, -1):
        # ricadono lungo una parabola, sempre più piccole, a goccia con la punta in su (cadono)
        for (gx_, gz_, r_) in ((0.15, 1.22, 0.024), (0.215, 1.135, 0.020), (0.255, 1.045, 0.016)):
            gx_ *= s_
            gocce.append(sd_unione(np.sqrt((X - gx_) ** 2 + (Z - gz_) ** 2) - r_,
                                   sd_capsula(X, Z, gx_ - s_ * r_ * 0.5, gz_ + r_ * 1.6, gx_ - s_ * r_ * 0.5, gz_ + r_ * 1.7, 0.002), r_ * 0.9))
        for (gx_, gz_, r_) in ((0.11, 1.31, 0.010), (0.19, 1.27, 0.008), (0.29, 1.12, 0.007)):
            gocce.append(np.sqrt((X - s_ * gx_) ** 2 + (Z - gz_) ** 2) - r_)

    def strato(sd, colore, contorno=True):
        if contorno:
            tela.dipingi(cop(sd - o, px), NAVY, (x0, y0))
        tela.dipingi(cop(sd, px), colore, (x0, y0))

    strato(coda, MM_BLU)
    o_acqua = o * 0.7
    tela.dipingi(cop(getto - o_acqua, px), NAVY, (x0, y0))
    tela.dipingi(cop(getto, px), MM_ZAMPILLO, (x0, y0))
    tela.dipingi(cop(venatura, px) * 0.8, MM_ZAMPILLO_SCURO, (x0, y0))
    for g in gocce:
        tela.dipingi(cop(g - o_acqua, px), NAVY, (x0, y0))
        tela.dipingi(cop(g, px), MM_ZAMPILLO, (x0, y0))
    strato(f, MM_BLU)
    # ombra a cartone (in basso a destra) e lucido (in alto a sinistra)
    ombra = np.maximum(f, -sd_unione(sd_ellisse(X + 0.06, Z - 0.05, 0, 0.36, 0.36, 0.38),
                                         sd_ellisse(X + 0.06, Z - 0.05, 0, 0.80, 0.36, 0.27), 0.12))
    tela.dipingi(cop(ombra, px) * 0.85, MM_BLU_OMBRA, (x0, y0))
    for p_ in pinne:
        pass
    # la pancia color crema
    pancia = np.maximum(sd_ellisse(X, Z, 0, 0.33, 0.27, 0.30), f + 0.01)
    tela.dipingi(cop(pancia - o * 0.6, px), NAVY, (x0, y0))
    tela.dipingi(cop(pancia, px), MM_PANCIA, (x0, y0))
    # righe della pancia (come le balenottere dei cartoni)
    for k in range(4):
        zz = 0.18 + k * 0.075
        r = sd_capsula(X, Z, -0.20 + 0.03 * abs(k - 1.5), zz, 0.20 - 0.03 * abs(k - 1.5), zz, 0.006)
        tela.dipingi(cop(np.maximum(r, pancia + 0.02), px) * 0.35, (200, 170, 130), (x0, y0))
    lucido = sd_ellisse(X, Z, -0.17, 0.93, 0.07, 0.035, 30)
    tela.dipingi(cop(lucido, px) * 0.8, (190, 225, 255), (x0, y0))
    # le guance
    for s in (1, -1):
        g = sd_ellisse(X, Z, s * 0.22, 0.72, 0.07, 0.045)
        tela.dipingi(np.clip(0.5 - g / (px * 6), 0, 1) * 0.8, MM_GUANCE, (x0, y0))
    # gli occhi, grandi, con tre ciglia ciascuno
    for s in (1, -1):
        ex, ez = s * 0.13, 0.875
        bianco = sd_ellisse(X, Z, ex, ez, 0.085, 0.10)
        tela.dipingi(cop(bianco - o * 0.7, px), NAVY, (x0, y0))
        tela.dipingi(cop(bianco, px), (255, 255, 255), (x0, y0))
        pup = sd_ellisse(X, Z, ex + s * 0.012, ez - 0.012, 0.050, 0.062)
        tela.dipingi(cop(pup, px), (16, 18, 40), (x0, y0))
        hl = sd_ellisse(X, Z, ex - 0.012 + s * 0.012, ez + 0.012, 0.017, 0.02)
        tela.dipingi(cop(hl, px), (255, 255, 255), (x0, y0))
        for c in (-1, 0, 1):
            a = math.radians(90 + s * 18 + c * 26)
            bx, bz = ex + 0.085 * math.cos(a) * 0.95, ez + 0.10 * math.sin(a) * 0.95
            tx, tz = ex + 0.155 * math.cos(a), ez + 0.165 * math.sin(a)
            tela.dipingi(cop(sd_capsula(X, Z, bx, bz, tx, tz, 0.011), px), NAVY, (x0, y0))
    # il sorriso: grande, aperto, con la lingua
    bocca = np.maximum(sd_ellisse(X, Z, 0, 0.705, 0.17, 0.085), Z - (0.69 + 0.9 * X ** 2))
    tela.dipingi(cop(bocca - o * 0.6, px), NAVY, (x0, y0))
    tela.dipingi(cop(bocca, px), (150, 20, 50), (x0, y0))
    lingua = np.maximum(sd_ellisse(X, Z, 0.0, 0.615, 0.09, 0.05), bocca)
    tela.dipingi(cop(lingua, px), (246, 120, 140), (x0, y0))
    # i tre pesciolini in grembo, abbracciati
    for k, (fx, fz) in enumerate(((-0.13, 0.36), (0.0, 0.28), (0.13, 0.36))):
        d = -1 if k == 0 else 1
        pesce = sd_ellisse(X, Z, fx, fz, 0.075, 0.048)
        coda_p = sd_ellisse(X, Z, fx - d * 0.085, fz, 0.025, 0.045)
        pp = np.minimum(pesce, coda_p)
        tela.dipingi(cop(pp - o * 0.6, px), NAVY, (x0, y0))
        tela.dipingi(cop(pp, px), MM_PESCI[k], (x0, y0))
        occhio = np.sqrt((X - fx - d * 0.035) ** 2 + (Z - fz - 0.01) ** 2) - 0.012
        tela.dipingi(cop(occhio, px), NAVY, (x0, y0))
        sorr = np.abs(np.sqrt((X - fx - d * 0.035) ** 2 + (Z - fz + 0.005) ** 2) - 0.02) - 0.004
        sorr = np.maximum(sorr, Z - fz + 0.008)
        tela.dipingi(cop(sorr, px), NAVY, (x0, y0))
    # le pinne che abbracciano i pesciolini (la punta davanti)


def stella(d: ImageDraw.ImageDraw, cx, cy, r, colore, contorno=None, w=0):
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = r if k % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=colore, outline=contorno, width=w)


def testo_img(s, f, colore, contorno=None, w=0, ombra=None, off=(0, 0), gradi=0.0, pad=60):
    bb = f.getbbox(s, stroke_width=w)
    tw, th = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    im = Image.new('RGBA', (int(tw + abs(off[0])), int(th + abs(off[1]))), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, y = pad - bb[0], pad - bb[1]
    if ombra:
        d.text((x + off[0], y + off[1]), s, font=f, fill=ombra, stroke_width=w, stroke_fill=ombra)
    d.text((x, y), s, font=f, fill=colore, stroke_width=w, stroke_fill=contorno)
    if gradi:
        im = im.rotate(gradi, resample=Image.BICUBIC, expand=True)
    return im


def incolla_centro(tela, im, cx, cy):
    tela.incolla(im, int(cx - im.width / 2), int(cy - im.height / 2))


# tutti i testi del volantino, per lingua: per una lingua nuova bastano le sue righe (e 'font' se servono altri font)
TESTI_V = {
    'it': dict(titolo='CERCHIAMO TE!', fumetto=('I nostri', 'piccoli hanno', 'fame!'),
               nastro='TURNO DI NOTTE · SI PESCA DALLA BARCA',
               righe=[('Barca, luce ed esca fornite', 'Dalle 0 alle 6'), ("Paga in contanti all'alba", 'Nessuna esperienza!')],
               invito='Ti aspettiamo al molo vecchio, al tramonto!', linguetta=('MOLO VECCHIO', 'AL TRAMONTO')),
    'en': dict(titolo='WE WANT YOU!', fumetto=('Our little', 'ones are', 'hungry!'),
               nastro='NIGHT SHIFT · FISHING FROM THE BOAT',
               righe=[('Boat, light and bait provided', 'Midnight to 6 AM'), ('Cash paid at dawn', 'No experience needed!')],
               invito='Meet us at the old pier at sunset!', linguetta=('OLD PIER', 'AT SUNSET')),
    # ── PROVA, DA FAR CONTROLLARE A UN MADRELINGUA: queste righe non vanno nel gioco così come sono ──
    'es': dict(prova=True, titolo='¡TE BUSCAMOS!', fumetto=('¡Nuestros', 'pequeños tienen', 'hambre!'),
               nastro='TURNO DE NOCHE · PESCA DESDE EL BARCO',
               righe=[('Barco, luz y cebo incluidos', 'De 0 a 6 h'), ('Pago en efectivo al alba', '¡Sin experiencia!')],
               invito='¡Te esperamos en el muelle viejo, al atardecer!', linguetta=('MUELLE VIEJO', 'AL ATARDECER')),
    'fr': dict(prova=True, titolo='ON TE CHERCHE\u00a0!', fumetto=('Nos petits', 'ont', 'faim\u00a0!'),
               nastro='TRAVAIL DE NUIT · PÊCHE EN BATEAU',
               righe=[('Bateau, lampe et appâts fournis', 'De minuit à 6 h'), ("Payé en liquide à l'aube", 'Sans expérience\u00a0!')],
               invito='On t\u2019attend à la vieille jetée, au coucher du soleil\u00a0!',
               linguetta=('VIEILLE JETÉE', 'AU CRÉPUSCULE')),
    'de': dict(prova=True, titolo='WIR SUCHEN DICH!', fumetto=('Unsere', 'Kleinen haben', 'Hunger!'),
               nastro='NACHTSCHICHT · ANGELN VOM BOOT',
               righe=[('Boot, Licht und Köder gestellt', '0 bis 6 Uhr'), ('Bar bezahlt im Morgengrauen', 'Keine Erfahrung nötig!')],
               invito='Wir warten am alten Steg, bei Sonnenuntergang!', linguetta=('ALTER STEG', 'BEI DÄMMERUNG')),
    # portoghese del Brasile: nel gioco la lingua è 'pt' (detectLang porta pt-BR → pt)
    'pt': dict(prova=True, titolo='PROCURAMOS VOCÊ!', fumetto=('Nossos', 'pequenos estão', 'com fome!'),
                  nastro='TURNO DA NOITE · PESCA NO BARCO',
                  righe=[('Barco, luz e isca inclusos', 'Da meia-noite às 6h'), ('Pagamento em dinheiro', 'Sem experiência!')],
                  invito='Te esperamos no píer velho, ao pôr do sol!', linguetta=('PÍER VELHO', 'AO PÔR DO SOL')),
    'zh': dict(prova=True, titolo='我们需要你！', fumetto=('我们的', '小宝贝们', '饿了！'),
               nastro='夜班 • 乘船钓鱼',
               righe=[('提供船、灯和鱼饵', '午夜0点到早上6点'), ('天亮时现金结算', '无需经验！')],
               invito='日落时分，我们在旧码头等你！', linguetta=('旧码头', '日落时分'), verticale=True,
               font={'titolo': 'cjk/ZCOOLKuaiLe-volantino', 'testo': 'cjk/NotoSansSC-ExtraBold-volantino',
                     'nastro': 'cjk/ZCOOLQingKeHuangYou-volantino'}),
    'ja': dict(prova=True, titolo='キミを募集中！', fumetto=('うちの子たち、', 'おなかが', 'ペコペコ！'),
               nastro='夜のシフト・ボートで釣り',
               righe=[('ボート・ライト・エサ支給', '0時〜6時'), ('夜明けに現金払い', '未経験OK！')],
               invito='日没に、古い桟橋で待ってるよ！', linguetta=('古い桟橋', '日没に'), verticale=True,
               font={'titolo': 'cjk/MochiyPopOne-volantino', 'testo': 'cjk/MPLUSRounded1c-ExtraBold-volantino',
                     'nastro': 'cjk/DelaGothicOne-volantino'}),
    'ko': dict(prova=True, titolo='당신을 찾습니다!', fumetto=('우리 아이들이', '배가', '고파요!'),
               nastro='야간 근무 ★ 배에서 낚시',
               righe=[('배, 조명, 미끼 제공', '자정부터 새벽 6시'), ('새벽에 현금 지급', '경험 무관!')],
               invito='해 질 녘, 낡은 부두에서 기다릴게요!', linguetta=('낡은 부두', '해 질 녘'), verticale=True,
               font={'titolo': 'cjk/BlackHanSans-volantino', 'testo': 'cjk/Jua-volantino',
                     'nastro': 'cjk/DoHyeon-volantino'}),
}


# i font del volantino; una lingua può sostituirli con la chiave 'font' (p. es. per il cirillico, che questi non hanno).
# Copertura: Luckiest Guy e Baloo 2 hanno il latino esteso (accenti, ß, ñ, polacco, ceco, turco), niente cirillico né
# greco; Lilita One ha l'Europa occidentale (accenti, ß, ñ) ma non tutto il polacco e il turco; Pacifico ha anche il
# cirillico. La testata (Limelight) e lo slogan non si traducono. Le stelle si disegnano, non sono un carattere.
FONT_V = {'titolo': 'LuckiestGuy-Regular', 'testo': 'Baloo2-ExtraBold', 'nastro': 'LilitaOne-Regular'}


# i font interi per cinese, giapponese e coreano (Google Fonts, OFL) da cui si ricavano i sottoinsiemi in
# tools/render/fonts/annuncio/cjk/ coi soli caratteri dei testi: se cambiano i testi, si rifanno con
# `annuncio.py --sottoinsiemi <cartella coi font interi>` (i font interi pesano 1-10 MB l'uno e non stanno nel repo)
FONT_CJK = {
    'cjk/ZCOOLKuaiLe-volantino': 'ZCOOLKuaiLe-Regular.ttf',
    'cjk/NotoSansSC-ExtraBold-volantino': 'NotoSansSC-ExtraBold.ttf',
    'cjk/ZCOOLQingKeHuangYou-volantino': 'ZCOOLQingKeHuangYou-Regular.ttf',
    'cjk/MochiyPopOne-volantino': 'MochiyPopOne-Regular.ttf',
    'cjk/MPLUSRounded1c-ExtraBold-volantino': 'MPLUSRounded1c-ExtraBold.ttf',
    'cjk/DelaGothicOne-volantino': 'DelaGothicOne-Regular.ttf',
    'cjk/BlackHanSans-volantino': 'BlackHanSans-Regular.ttf',
    'cjk/Jua-volantino': 'Jua-Regular.ttf',
    'cjk/DoHyeon-volantino': 'DoHyeon-Regular.ttf',
}

# quale testo usa quale font del volantino
USO_FONT = {'titolo': ('titolo',), 'testo': ('fumetto', 'righe', 'invito'), 'nastro': ('nastro', 'linguetta')}


def caratteri_per_font():
    """{nome del font: insieme dei caratteri che deve avere}, da tutte le lingue di TESTI_V."""
    out = {}
    for lingua, TX in TESTI_V.items():
        FV = {**FONT_V, **TX.get('font', {})}
        for ruolo, campi in USO_FONT.items():
            car = out.setdefault(FV[ruolo], set())
            for c in campi:
                v = TX[c]
                testi = [v] if isinstance(v, str) else [x for t in v for x in ((t,) if isinstance(t, str) else t)]
                car.update(ch for t in testi for ch in t if not ch.isspace())
    return out


def controlla_font():
    """Per ogni font, i caratteri dei testi che non ha (finirebbero come quadratini). Restituisce {font: mancanti}."""
    from fontTools.ttLib import TTFont
    mancano = {}
    for nome, car in caratteri_per_font().items():
        p = os.path.join(FONTS, 'annuncio', nome + '.ttf')
        if not os.path.exists(p):
            p = os.path.join(FONTS, nome + '.ttf')
        cmap = TTFont(p).getBestCmap()
        m = sorted(ch for ch in car if ord(ch) not in cmap)
        if m:
            mancano[nome] = m
    return mancano


def sottoinsiemi(cartella):
    """Ricava i sottoinsiemi CJK dai font interi in 'cartella': i caratteri dei testi più l'ASCII stampabile."""
    from fontTools import subset
    usati = caratteri_per_font()
    os.makedirs(os.path.join(FONTS, 'annuncio', 'cjk'), exist_ok=True)
    for nome, file in FONT_CJK.items():
        car = usati.get(nome, set()) | {chr(c) for c in range(0x20, 0x7f)} | {'\u00a0', '·', '・', '！', '，', '、', '〜'}
        opt = subset.Options()
        opt.layout_features = ['*']
        opt.name_IDs = ['*']
        opt.notdef_outline = True
        f = subset.load_font(os.path.join(cartella, file), opt)
        sub = subset.Subsetter(opt)
        sub.populate(text=''.join(sorted(car)))
        sub.subset(f)
        out = os.path.join(FONTS, 'annuncio', nome + '.ttf')
        f.save(out)
        print(f'{nome}: {len(car)} caratteri, {os.path.getsize(out) // 1024} KB', flush=True)

def font_adatto(nome, px, testi, larg):
    """Il corpo più grande (fino a px) con cui tutti i testi stanno in larg."""
    while px > 20 and max(font(nome, px).getlength(t) for t in testi) > larg:
        px -= 2
    return font(nome, px)


def impagina_volantino(lingua='it'):
    """Il volantino nuovo, appena stampato: restituisce il colore (0..1)."""
    TX = TESTI_V[lingua]
    FV = {**FONT_V, **TX.get('font', {})}
    T = Tela(VW, VH, (176, 230, 244))
    yy, xx = np.mgrid[:VH, :VW].astype(np.float32)
    # cielo: dal celeste al bianco, i raggi del sole dietro Mama Marina (come l'insegna dell'ingresso)
    t = yy / VH
    T.a[:] = (np.array([0.50, 0.82, 0.94]) * (1 - t[..., None]) + np.array([0.86, 0.96, 0.99]) * t[..., None])
    cx, cy = VW * 0.42, 1720
    ang = np.arctan2(yy - cy, xx - cx)
    raggi = (np.sin(ang * 16) > 0).astype(np.float32)
    rr = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    raggi = gaussian_filter(raggi, 1.0) * np.clip(1 - rr / 2300, 0, 1) * (rr > 180)
    T.a[:] = T.a * (1 - 0.55 * raggi[..., None]) + np.array([1.0, 0.93, 0.70]) * 0.55 * raggi[..., None]
    # bollicine
    rng = np.random.default_rng(7)
    lay = Image.new('RGBA', (VW, VH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(70):
        bx, by, r = rng.uniform(0, VW), rng.uniform(900, 2900), rng.uniform(10, 46)
        if in_zona_testo(bx, by, r + 10):
            continue
        d.ellipse((bx - r, by - r, bx + r, by + r), outline=(255, 255, 255, 200), width=max(3, int(r / 6)))
        d.ellipse((bx - r * 0.5, by - r * 0.6, bx - r * 0.1, by - r * 0.2), fill=(255, 255, 255, 220))
    T.incolla(lay, 0, 0)

    # la testata del parco
    incolla_centro(T, testo_img("MAMA MARINA'S", font('Limelight-Regular', 170), CIANO, NAVY, 9, NAVY, (8, 10)), VW / 2, 200)
    incolla_centro(T, testo_img('SPLASHLAND', font('Limelight-Regular', 360), ROSA, NAVY, 14, NAVY, (16, 20)), VW / 2, 470)
    # CERCHIAMO TE!
    incolla_centro(T, testo_img(TX['titolo'], font_adatto(FV['titolo'], 300, [TX['titolo']], 1900), GIALLO, NAVY, 18, (232, 70, 120), (14, 16),
                                gradi=4), VW / 2, 805)
    lay = Image.new('RGBA', (VW, VH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for (sx, sy, r) in ((180, 800, 60), (2310, 760, 70), (2240, 1010, 38), (260, 1020, 34)):
        stella(d, sx, sy, r, GIALLO + (255,), NAVY + (255,), 7)
    T.incolla(lay, 0, 0)

    # Mama Marina
    mama_marina(T, VW * 0.40, 2150, 900)

    # il fumetto
    lay = Image.new('RGBA', (VW, VH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    bx0, by0, bx1, by1 = 1500, 1080, 2400, 1640
    d.polygon([(1640, 1520), (1560, 1720), (1800, 1580)], fill=NAVY + (255,))
    d.ellipse((bx0 - 12, by0 - 12, bx1 + 12, by1 + 12), fill=NAVY + (255,))
    d.ellipse((bx0, by0, bx1, by1), fill=(255, 255, 255, 255))
    d.polygon([(1652, 1500), (1580, 1680), (1790, 1560)], fill=(255, 255, 255, 255))
    fb = font_adatto(FV['testo'], 116, TX['fumetto'], 720)
    nf = len(TX['fumetto'])
    for k, riga in enumerate(TX['fumetto']):
        d.text(((bx0 + bx1) / 2, by0 + 238 + (k - (nf - 1) / 2) * fb.size * 1.02), riga, font=fb, fill=NAVY + (255,),
               anchor='mm')
    T.incolla(lay, 0, 0)

    # il nastro: turno di notte, si pesca dalla barca
    lay = Image.new('RGBA', (VW, VH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ry0, ry1 = 2190, 2370
    d.polygon([(40, ry0 + 50), (230, ry0 + 50), (230, ry1 + 50), (40, ry1 + 50), (120, (ry0 + ry1) / 2 + 50)], fill=(196, 60, 120, 255))
    d.polygon([(VW - 40, ry0 + 50), (VW - 230, ry0 + 50), (VW - 230, ry1 + 50), (VW - 40, ry1 + 50), (VW - 120, (ry0 + ry1) / 2 + 50)], fill=(196, 60, 120, 255))
    d.polygon([(150, ry1), (230, ry1 + 50), (230, ry1)], fill=(120, 30, 70, 255))
    d.polygon([(VW - 150, ry1), (VW - 230, ry1 + 50), (VW - 230, ry1)], fill=(120, 30, 70, 255))
    d.rectangle((150, ry0, VW - 150, ry1), fill=ROSA + (255,), outline=NAVY + (255,), width=8)
    d.text((VW / 2, (ry0 + ry1) / 2 + 6), TX['nastro'], font=font_adatto(FV['nastro'], 122, [TX['nastro']], VW - 400),
           fill=(255, 255, 255, 255), anchor='mm', stroke_width=6, stroke_fill=NAVY + (255,))
    # le condizioni, su un cartiglio bianco
    px0, py0, px1, py1 = 170, 2450, VW - 170, 2840
    d.rounded_rectangle((px0, py0, px1, py1), 50, fill=(255, 255, 255, 235), outline=NAVY + (255,), width=8)
    righe = TX['righe']
    xa, xb, fine = px0 + 145, VW / 2 + 250, px1 - 40
    la = max(font(FV['testo'], 92).getlength(a) for a, _ in righe)
    lb = max(font(FV['testo'], 92).getlength(b) for _, b in righe)
    if la > xb - 60 - xa or lb > fine - (xb + 55):
        # non ci sta con la colonna a metà: si sposta la colonna destra e si rimpicciolisce tutto quanto basta
        k = min(1.0, (fine - xa - 115) / (la + lb))
        xb = xa + la * k + 60
    fi = font_adatto(FV['testo'], 92, [a for a, _ in righe], xb - 60 - xa)
    fi = font_adatto(FV['testo'], fi.size, [b for _, b in righe], fine - (xb + 55))
    for r_, (a_, b_) in enumerate(righe):
        y = py0 + 85 + r_ * 115
        stella(d, px0 + 90, y, 34, GIALLO + (255,), NAVY + (255,), 5)
        d.text((px0 + 145, y), a_, font=fi, fill=NAVY + (255,), anchor='lm')
        stella(d, xb, y, 34, GIALLO + (255,), NAVY + (255,), 5)
        d.text((xb + 55, y), b_, font=fi, fill=NAVY + (255,), anchor='lm')
    d.text((VW / 2, py0 + 315), TX['invito'], font=font_adatto(FV['testo'], 104, [TX['invito']], px1 - px0 - 80),
           fill=(214, 60, 130, 255), anchor='mm')
    T.incolla(lay, 0, 0)

    # le onde in fondo, con lo slogan
    wy = 2880
    onda = wy + 28 * np.sin(xx / 95.0) + 10 * np.sin(xx / 37.0 + 1)
    acqua = np.clip(yy - onda, 0, 1)
    T.a[:] = T.a * (1 - acqua[..., None]) + np.array([0.20, 0.47, 0.82]) * acqua[..., None]
    cresta = np.clip(1 - np.abs(yy - onda - 4) / 10, 0, 1)
    T.a[:] = T.a * (1 - cresta[..., None]) + np.array([0.95, 0.98, 1.0]) * cresta[..., None]
    incolla_centro(T, testo_img('Mama Marina loves her little ones!', font('Pacifico-Regular', 112), (255, 255, 255),
                                NAVY, 5), VW / 2, 2975)
    # le linguette da strappare col posto dell'appuntamento
    ly0 = 3080
    T.a[ly0:] = np.array([1.0, 1.0, 1.0]) * 0.97
    lay = Image.new('RGBA', (VW, VH), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    n = 9
    for k in range(n):
        x0 = k * VW / n
        if k:
            for yd in range(ly0, VH, 26):
                d.line((x0, yd, x0, yd + 13), fill=NAVY + (255,), width=3)
        if TX.get('verticale'):
            # cinese, giapponese, coreano: scrittura verticale, due colonne da destra a sinistra, caratteri dritti
            sub = Image.new('RGBA', (200, 420), (0, 0, 0, 0))
            ds = ImageDraw.Draw(sub)
            nmax = max(len(r) for r in TX['linguetta'])
            fl = font(FV['nastro'], int(min(64, 400 / nmax * 0.92)))
            for c_, (riga, colr) in enumerate(zip(TX['linguetta'], (NAVY + (255,), (214, 60, 130, 255)))):
                cxs = 140 - c_ * 80
                y0s = 210 - (len(riga) - 1) / 2 * fl.size * 1.05
                for q, ch in enumerate(riga):
                    if ch.strip():
                        ds.text((cxs, y0s + q * fl.size * 1.05), ch, font=fl, fill=colr, anchor='mm')
        else:
            sub = Image.new('RGBA', (440, 200), (0, 0, 0, 0))
            ds = ImageDraw.Draw(sub)
            fl = font_adatto(FV['nastro'], 54, TX['linguetta'], 400)
            ds.text((220, 62), TX['linguetta'][0], font=fl, fill=NAVY + (255,), anchor='mm')
            ds.text((220, 138), TX['linguetta'][1], font=fl, fill=(214, 60, 130, 255), anchor='mm')
            sub = sub.rotate(90, expand=True)
        lay.alpha_composite(sub, (int(x0 + VW / n / 2 - sub.width / 2), int(ly0 + (VH - ly0) / 2 - sub.height / 2)))
    for xd in range(0, VW, 26):
        d.line((xd, ly0, xd + 13, ly0), fill=NAVY + (255,), width=3)
    T.incolla(lay, 0, 0)
    return np.clip(T.a, 0, 1)

# le zone del foglio con le scritte che il giocatore deve leggere (fumetto, nastro, condizioni e invito, slogan, linguette):
# lì non vanno gocce, bolle, colature, ruggine né muffa (richiesta della sessione principale: «all'alba» si leggeva
# «all'a ba» sotto una goccia). Il bagnato resta, più leggero; la striscia di luce resta.
ZONE_TESTO = ((1480, 1060, 2420, 1660), (140, 2180, 2340, 2380), (160, 2440, 2320, 2850), (0, 2880, 2480, 3508))


def maschera_testo(h, w, margine=30):
    """1 nelle zone con le scritte (più un margine che sfuma), 0 altrove; in pixel del foglio intero."""
    m = np.zeros((h, w), np.float32)
    sx, sy = w / VW, h / VH
    for (x0, y0, x1, y1) in ZONE_TESTO:
        m[int(max(0, (y0 - margine) * sy)):int((y1 + margine) * sy), int(max(0, (x0 - margine) * sx)):int((x1 + margine) * sx)] = 1
    return gaussian_filter(m, margine * 0.4 * sx)


def in_zona_testo(x, y, r=0.0):
    return any(x0 - r <= x <= x1 + r and y0 - r <= y <= y1 + r for (x0, y0, x1, y1) in ZONE_TESTO)


LINGUETTE_STRAPPATE = (0, 1, 3, 4, 6, 7)       # le linguette già prese: ne restano tre
CHIODI_V = ((120, 130), (VW - 118, 120), (130, 2990), (VW - 140, 3000))


def invecchia_volantino(rng, col):
    """Sbiadito dal sole, poi fradicio: i colori colati, la ruggine dei chiodi, l'angolo strappato, le linguette prese.
    Restituisce colore, alfa, rilievo, bagnato (tutti sul foglio)."""
    h, w = col.shape[:2]
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    carta = np.array([0.93, 0.91, 0.84], np.float32)
    # il sole: meno saturo, più chiaro, il magenta se ne va per primo
    sole = np.clip(0.55 + 0.45 * rumore(rng, (h, w), 260, 2), 0, 1)
    gr = col.mean(-1, keepdims=True)
    col = gr + (col - gr) * (0.74 - 0.12 * sole[..., None])
    col[..., 1] = col[..., 1] + (1 - col[..., 1]) * 0.10 * sole       # il magenta sbiadisce: il verde risale
    col = col * (0.85 - 0.06 * sole[..., None]) + carta * (0.15 + 0.06 * sole[..., None])
    col = col * np.array([1.0, 0.97, 0.88])          # e ingiallisce
    # il bagnato: l'acqua è entrata dal basso e cola dall'alto, a strisce
    strisce = gaussian_filter(rng.standard_normal((h // 4, w // 4)).astype(np.float32), (40, 2.5))
    strisce = np.array(Image.fromarray(strisce / strisce.std()).resize((w, h), Image.BICUBIC))
    bag = np.clip((yy / h - 0.55) * 2.2 + 0.35 * rumore(rng, (h, w), 120, 2), 0, 1)
    bag = np.maximum(bag, np.clip(strisce - 0.6, 0, 1) * np.clip(1.2 - yy / h, 0, 1))
    bag = np.maximum(bag, np.clip(1 - yy / 260 + 0.3 * rumore(rng, (h, w), 40), 0, 1) * 0.8)   # il bordo in alto
    bag = gaussian_filter(bag, 4)
    # i colori colano verso il basso dove c'è acqua che scende
    zt = maschera_testo(h, w)
    cola = np.clip(strisce - 0.25, 0, 1) * 0.85 * (1 - zt)
    e = col.copy()
    for y in range(1, h):
        e[y] = 0.988 * e[y - 1] + 0.012 * col[y]
    scuro = np.minimum(col, e)
    col = col * (1 - cola[..., None]) + scuro * cola[..., None]
    # l'alone della linea dove l'acqua si è fermata
    bordo_b = np.exp(-((bag - 0.5) / 0.06) ** 2) * (gaussian_filter(bag, 12) > 0.2)
    col = col * (1 - 0.10 * bordo_b[..., None] * np.array([0.3, 0.6, 1.0]))
    bag_c = bag * (1 - 0.5 * zt)          # sulle scritte il bagnato scurisce meno
    gr = col.mean(-1, keepdims=True)
    col = gr + (col - gr) * (1 + 0.25 * bag_c[..., None])
    col = col * (1 - 0.22 * bag_c[..., None])
    # sporco della pioggia e muffa
    sporco = gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), (30, 1.5))
    sporco = np.clip(sporco / sporco.std() - 0.8, 0, 2) * np.clip(1.1 - yy / h, 0, 1)
    col = col * (1 - 0.10 * (sporco * (1 - zt))[..., None])
    for _ in range(120):
        fx, fy = rng.uniform(0, w), rng.uniform(0, h)
        if rng.uniform() < 0.6:
            fx = rng.choice([rng.uniform(0, 200), rng.uniform(w - 200, w)])
        r = rng.uniform(2, 9)
        if in_zona_testo(fx, fy, 4 * r):
            continue
        x0, x1, y0, y1 = int(max(0, fx - 4 * r)), int(min(w, fx + 4 * r)), int(max(0, fy - 4 * r)), int(min(h, fy + 4 * r))
        m = np.exp(-(((xx[y0:y1, x0:x1] - fx) ** 2 + (yy[y0:y1, x0:x1] - fy) ** 2) / (2 * r * r)))
        col[y0:y1, x0:x1] *= 1 - 0.35 * m[..., None] * np.array([0.55, 0.5, 0.6])
    # la ruggine che cola dai chiodi
    for (nx, ny) in CHIODI_V:
        lung = rng.uniform(380, 900)
        larg = rng.uniform(14, 26)
        t = np.clip((yy - ny) / lung, 0, 1)
        off = 10 * np.sin((yy - ny) / 70 + nx)
        m = np.exp(-((xx - nx - off) / (larg * (1 - 0.7 * t) + 1)) ** 2) * (yy > ny - 10) * (1 - t) ** 1.5
        m += np.exp(-(((xx - nx) ** 2 + (yy - ny) ** 2) / (2 * 34 ** 2))) * 1.2
        m = np.clip(m * (0.7 + 0.5 * rumore(rng, (h, w), 3)), 0, 1) * (1 - zt)
        rug = np.array([0.42, 0.20, 0.07], np.float32)
        col = col * (1 - 0.75 * m[..., None]) + rug * col * 1.3 * 0.75 * m[..., None]

    # ── la sagoma: l'angolo in alto a destra strappato (resta solo il pezzetto sotto il chiodo), le linguette prese ──
    alfa = np.ones((h, w), np.float32)
    lt = 680
    bordo = (w - xx) + yy - lt + 30 * rumore(rng, (h, w), 14) + 12 * rumore(rng, (h, w), 3)
    via = bordo < 0
    nx, ny = CHIODI_V[1]
    pezzetto = (np.sqrt((xx - nx) ** 2 + (yy - ny) ** 2) + 26 * rumore(rng, (h, w), 10) + 8 * rumore(rng, (h, w), 2.5)) < 95
    alfa[via & ~pezzetto] = 0
    ly0 = 3080
    nl = 9
    for k in LINGUETTE_STRAPPATE:
        x0, x1 = k * w / nl, (k + 1) * w / nl
        moncone = ly0 + 18 + 22 * np.abs(rumore(rng, (1, w), 8))[0] + 8 * rumore(rng, (1, w), 1.5)[0]
        m = (xx >= x0 - 2) & (xx <= x1 + 2) & (yy > moncone[None, :])
        alfa[m] = 0
    # bordi sfrangiati: fibre bianche lungo gli strappi
    alfa = gaussian_filter(alfa, 1.0)
    fibra = np.clip(1 - distance_transform_edt(alfa > 0.5) / 6, 0, 1) * (alfa > 0.1)
    strappato = ((np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) > 12) * 0.8)[..., None]
    col = col * (1 - fibra[..., None] * strappato) + carta * fibra[..., None] * strappato

    # ── il rilievo: grinze della carta bagnata, una piega, il gonfiore tra i chiodi ──
    alt = 3.0 * rumore(rng, (h, w), 120, 3) + 9.0 * bag * rumore(rng, (h, w), 45, 2)
    alt += 0.5 * fibre(rng, (h, w))
    d = (xx - w * 0.15) * 0.25 + (yy - h * 0.62)
    alt += -6 * np.exp(-np.abs(d) / 70) - 2 * np.exp(-np.abs(d) / 4)
    alt += 22 * np.sin(np.clip(xx / w, 0, 1) * math.pi) * np.sin(np.clip((yy - 120) / 2880, 0, 1) * math.pi)
    # le linguette rimaste si incurvano in fuori
    alt += np.clip((yy - ly0) / (h - ly0), 0, 1) ** 2 * 40
    return np.clip(col, 0, 1), alfa, alt, bag


def sfondo_notte(rng, shape):
    """La baia di notte dietro il palo, fuori fuoco: il cielo, la riva con Splashland e le luci."""
    h, w = shape
    q = max(1, round(4 * SCALA))     # la mezza scena si fa sempre a ~960 px di larghezza
    K = SCALA
    hq, wq = h // q, w // q
    yy, xx = np.mgrid[:hq, :wq].astype(np.float32)
    oriz = 0.60 * hq
    t = np.clip(yy / oriz, 0, 1)
    cielo = np.array([0.0015, 0.002, 0.006]) * (1 - t[..., None]) + np.array([0.009, 0.010, 0.018]) * t[..., None]
    nuvole = np.clip(rumore(rng, (hq, wq), 40, 3), -1, 2) * 0.0015
    img = cielo + nuvole[..., None] * np.array([0.8, 0.9, 1.2])
    # la riva: colline basse, il paese a sinistra, Splashland a destra
    riva = oriz - 18 - 10 * rumore(rng, (1, wq), 30)[0]
    sil = Image.new('L', (wq, hq), 0)
    d = ImageDraw.Draw(sil)
    for x in range(wq):
        d.line((x, riva[x], x, oriz), fill=255)
    # la ruota panoramica, gli scivoli e la statua di Mama Marina (in controluce)
    rx, ry, rr = wq * 0.89, oriz - 70, 58
    d.ellipse((rx - rr, ry - rr, rx + rr, ry + rr), outline=255, width=3)
    for k in range(12):
        a = k * math.pi / 6
        d.line((rx, ry, rx + rr * math.cos(a), ry + rr * math.sin(a)), fill=255, width=1)
    d.polygon([(rx - 20, oriz), (rx, ry), (rx + 20, oriz)], outline=255)
    d.line((rx - 22, oriz, rx, ry), fill=255, width=3)
    d.line((rx + 22, oriz, rx, ry), fill=255, width=3)
    mx, my = wq * 0.77, oriz - 8
    d.ellipse((mx - 26, my - 60, mx + 26, my), fill=255)
    d.ellipse((mx - 24, my - 92, mx + 24, my - 46), fill=255)
    d.polygon([(mx - 20, my - 70), (mx - 52, my - 88), (mx - 50, my - 78)], fill=255)
    d.polygon([(mx + 20, my - 70), (mx + 52, my - 88), (mx + 50, my - 78)], fill=255)
    d.line((mx, my - 92, mx, my - 104), fill=255, width=3)
    for k in range(3):
        x0 = wq * (0.95 + 0.02 * k)
        d.line((x0, oriz - 40 - 10 * k, x0 - 30, oriz - 5), fill=255, width=3)
    s_ = np.asarray(sil, np.float32) / 255
    bagliore = np.exp(-(((xx - wq * 0.86) / (wq * 0.12)) ** 2 + ((yy - oriz + 40) / 70) ** 2))
    img = img + bagliore[..., None] * np.array([0.030, 0.012, 0.028])
    img = img * (1 - s_[..., None]) + np.array([0.002, 0.002, 0.004]) * s_[..., None]
    # il mare: più scuro, con le increspature
    mare = yy > oriz
    inc = rumore(rng, (hq, wq), 1.5) * 0.5 + 0.5
    acqua = np.array([0.003, 0.004, 0.007]) * (0.7 + 0.6 * inc[..., None])
    img = np.where(mare[..., None], acqua, img)
    img = np.dstack([gaussian_filter(img[..., c], 2.0) for c in range(3)])
    img = np.array(Image.fromarray(img.astype(np.float32)[..., 0]).resize((w, h), Image.BICUBIC))[..., None] * 0 + \
        np.dstack([np.array(Image.fromarray(img[..., c].astype(np.float32)).resize((w, h), Image.BICUBIC)) for c in range(3)])
    # le luci fuori fuoco (bokeh): l'insegna rosa e azzurra, le luci della Deep End sott'acqua, il paese
    luci = np.zeros((h, w, 3), np.float32)
    lay = [Image.new('F', (w, h), 0) for _ in range(3)]
    dl = [ImageDraw.Draw(l) for l in lay]
    oy = oriz * q

    def bokeh(x, y, r, c, i=1.0):
        for k in range(3):
            dl[k].ellipse((x - r, y - r, x + r, y + r), fill=float(c[k] * i))
    for k in range(9):
        bokeh(w * (0.82 + 0.017 * k) + rng.normal(0, 6) * K, oy - (170 + 25 * math.sin(k * 0.7)) * K, rng.uniform(26, 40) * K,
              (1.0, 0.32, 0.70) if k % 3 else (0.35, 0.90, 1.0), 0.35)
    for k in range(14):
        a = k * math.pi / 7
        bokeh(rx * q + rr * q * math.cos(a), ry * q + rr * q * math.sin(a), rng.uniform(14, 22) * K, (1.0, 0.75, 0.45), 0.10)
    for k in range(22):
        bokeh(rng.uniform(0, w * 0.26), oy - rng.uniform(20, 90) * K, rng.uniform(10, 26) * K, (1.0, 0.66, 0.32), rng.uniform(0.08, 0.3))
    bokeh(w * 0.05, oy - 210 * K, 30 * K, (1.0, 0.92, 0.75), 0.5)        # il faro
    # le luci della Deep End, verdi-azzurre sotto la superficie, e i riflessi delle luci sull'acqua
    for k in range(5):
        bokeh(w * (0.80 + 0.03 * k), oy + (70 + rng.uniform(0, 30)) * K, rng.uniform(50, 80) * K, (0.15, 0.85, 0.75), 0.06)
    luci = np.dstack([np.asarray(l, np.float32) for l in lay])
    luci = np.dstack([gaussian_filter(luci[..., c], 2.5 * K) for c in range(3)])
    rifl = np.dstack([gaussian_filter(np.flipud(luci[..., c]), (30 * K, 4 * K)) for c in range(3)])
    sh = int(2 * oy - h)
    rifl = np.roll(rifl, sh, 0) * (np.mgrid[:h, :w][0] > oy)[..., None] * 0.45
    alone = np.dstack([gaussian_filter(luci[..., c], 60 * K) for c in range(3)]) * 1.2
    return img + luci + rifl + alone


def volantino(uscita, lingua='it'):
    rng = np.random.default_rng(1997)
    K = SCALA
    col, alfa, alt, bag = invecchia_volantino(rng, impagina_volantino(lingua))
    # il foglio a metà risoluzione (si campiona circa 1:1 nella scena)
    rf = 2 if SCALA < 1.4 else 1      # il foglio si campiona circa 1:1 nella scena
    h2, w2 = VH // rf, VW // rf
    col = np.asarray(Image.fromarray((col * 255).astype(np.uint8)).resize((w2, h2), Image.LANCZOS), np.float32) / 255
    rid = lambda a: np.array(Image.fromarray(a.astype(np.float32)).resize((w2, h2), Image.BILINEAR))
    alfa, alt, bag = rid(alfa), rid(alt) * (0.82 * SH / VH), rid(bag)
    zt = maschera_testo(h2, w2, margine=10)

    sw = (SH, SW)
    yy, xx = np.mgrid[:SH, :SW].astype(np.float32)
    # il palo: un cilindro verticale
    cxp, R = SW * 0.5, SH * 0.43
    xn = (xx - cxp) / R
    dentro = np.abs(xn) < 1
    xn_c = np.clip(xn, -0.9999, 0.9999)
    sarc = R * np.arcsin(xn_c)                      # ascissa curvilinea sulla superficie
    nz0 = np.sqrt(1 - xn_c ** 2)
    # il volantino sulla superficie del palo
    Hs = 0.82 * SH
    sc = Hs / h2                                     # pixel di scena per pixel del foglio
    top = 0.085 * SH
    rot = math.radians(-1.6)
    s0 = -0.01 * SH
    ds, dy = sarc - s0, yy - (top + Hs / 2)
    u = (ds * math.cos(rot) + dy * math.sin(rot)) / sc + w2 / 2
    v = (-ds * math.sin(rot) + dy * math.cos(rot)) / sc + h2 / 2
    samp = lambda a, cval=0.0: map_coordinates(a, [v, u], order=1, mode='constant', cval=cval)
    A = samp(alfa) * dentro
    C = np.dstack([samp(col[..., c]) for c in range(3)])
    Hp = samp(alt)
    Bg = samp(bag)
    Zs = samp(zt)

    def foglio_a_scena(uf, vf):
        uf, vf = uf / rf - w2 / 2, vf / rf - h2 / 2
        s_ = (uf * math.cos(rot) - vf * math.sin(rot)) * sc + s0
        y_ = (uf * math.sin(rot) + vf * math.cos(rot)) * sc + top + Hs / 2
        return cxp + R * math.sin(s_ / R), y_

    # il legno del palo: venature verticali, crepe, grigio di salsedine, più scuro e verde in basso
    pw = int(math.pi * R) + 4
    g = rumore(rng, (SH, pw), 1.0)
    ven = gaussian_filter(rng.standard_normal((SH, pw)).astype(np.float32), (40 * K, 1.0 * K))
    ven /= ven.std()
    ven2 = gaussian_filter(rng.standard_normal((SH, pw)).astype(np.float32), (120 * K, 6 * K))
    ven2 /= ven2.std()
    crepe = np.zeros((SH, pw), np.float32)
    for _ in range(9):
        cx0 = rng.uniform(0, pw)
        y0, y1 = sorted(rng.uniform(0, SH, 2))
        if y1 - y0 < 300:
            y1 = min(SH, y0 + 600)
        ys = np.arange(SH)
        cxs = cx0 + (12 * np.sin(ys / (90 * K) + cx0) + 5 * gaussian_filter(rng.standard_normal(SH), 8 * K) * 6) * K
        larg = rng.uniform(2, 7) * K * np.sin(np.clip((ys - y0) / (y1 - y0), 0, 1) * math.pi)
        X_ = np.arange(pw)[None, :]
        crepe = np.maximum(crepe, np.clip(1 - np.abs(X_ - cxs[:, None]) / (larg[:, None] + 0.5), 0, 1) * (larg[:, None] > 0.3))
    ven3 = gaussian_filter(rng.standard_normal((SH, pw)).astype(np.float32), (90 * K, 3.0 * K))
    ven3 /= ven3.std()
    lumw = (0.80 + 0.025 * ven + 0.09 * ven3 + 0.10 * ven2 + 0.03 * g) * (1 - 0.85 * crepe)
    base = np.array([0.33, 0.29, 0.24], np.float32)
    wtex = base[None, None] * lumw[..., None]
    basso = np.clip((np.arange(SH)[:, None] / SH - 0.7) / 0.3, 0, 1)
    wtex = wtex * (1 - 0.4 * basso[..., None]) + np.array([0.06, 0.08, 0.05]) * 0.4 * basso[..., None]
    walt = 0.08 * ven + 0.9 * ven3 + 0.8 * ven2 - 10 * crepe + 0.05 * g
    # la cima legata attorno al palo, in alto
    yr = np.arange(SH)[:, None].astype(np.float32)
    Xr = np.arange(pw)[None, :].astype(np.float32)
    corda = np.zeros((SH, pw), np.float32)
    calt = np.zeros((SH, pw), np.float32)
    for k, yc in enumerate((60.0 * K, 150.0 * K)):
        yc_ = yc + 0.025 * (Xr - pw / 2) * (1 if k else -1)
        d_ = np.abs(yr - yc_) / (46 * K)
        m = np.clip(1 - d_, 0, 1)
        fili = 0.5 + 0.5 * np.sin((Xr * 0.9 + yr * 2.2) / (14 * K))
        corda = np.maximum(corda, (m > 0) * 1.0)
        calt = np.maximum(calt, ((np.sqrt(np.clip(1 - d_ ** 2, 0, 1)) * 30 + fili * 6) * K) * (m > 0))
    ctex = np.array([0.30, 0.25, 0.17], np.float32)[None, None] * (0.45 + 0.7 * (calt[..., None] / (36 * K)))
    wtex = wtex * (1 - corda[..., None]) + ctex * corda[..., None]
    walt = walt * (1 - corda) + calt
    si = np.clip(sarc + pw / 2, 0, pw - 1)
    W_ = np.dstack([map_coordinates(wtex[..., c], [yy, si], order=1) for c in range(3)])
    Wa = map_coordinates(walt, [yy, si], order=1)
    Wc = map_coordinates(corda, [yy, si], order=1)
    # l'ombra della corda e del foglio sul palo
    om_c = np.roll(gaussian_filter(Wc, 6 * K), int(22 * K), 0) * (1 - Wc)
    om_f = gaussian_filter(np.roll(A, (int(10 * K), int(8 * K)), (0, 1)), 7 * K) * (1 - A)
    A = A * (1 - Wc)              # la corda passa sopra il foglio? no: il foglio è sotto la corda solo se la tocca

    # le gocce d'acqua, sul foglio e sul legno, con qualche rigolo
    gh = np.zeros(sw, np.float32)
    rig = np.zeros(sw, np.float32)
    n_g = 420
    gx = rng.uniform(cxp - R * 0.72, cxp + R * 0.72, n_g)
    gy = top + (SH - top) * rng.uniform(0, 1, n_g) ** 0.6
    gr_ = (rng.gamma(2.0, 3.2, n_g) + 2.0) * K
    for x_, y_, r_ in zip(gx, gy, gr_):
        r_ = min(r_, 22 * K)
        x0, x1, y0, y1 = int(x_ - r_ - 2), int(x_ + r_ + 3), int(y_ - r_ * 1.3 - 2), int(y_ + r_ * 1.3 + 3)
        if x0 < 0 or y0 < 0 or x1 >= SW or y1 >= SH:
            continue
        if Zs[y0:y1, x0:x1].max() > 0.02:
            continue                   # niente gocce sulle scritte
        ly, lx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dd = ((lx - x_) / r_) ** 2 + ((ly - y_) / (r_ * 1.15)) ** 2
        hgt = np.sqrt(np.clip(1 - dd, 0, 1)) * r_ * 0.7
        gh[y0:y1, x0:x1] = np.maximum(gh[y0:y1, x0:x1], hgt)
        if r_ > 9 * K and rng.uniform() < 0.45:
            # il rigolo che la goccia lascia salendo verso l'alto (da dove è scesa)
            lung = int(rng.uniform(60, 420) * K)
            ys = np.arange(max(0, int(y_) - lung), int(y_))
            xs = x_ + np.cumsum(rng.normal(0, 0.6, len(ys)))[::-1] * 0.6
            if len(ys) and Zs[ys, np.clip(xs.astype(int), 0, SW - 1)].max() > 0.02:
                continue                   # nemmeno i rigoli
            for yk, xk in zip(ys, xs):
                rw = r_ * 0.35
                rig[yk, int(xk - rw):int(xk + rw) + 1] = 1
    rig = gaussian_filter(rig, 1.2 * K)
    gh = gaussian_filter(gh, 0.7 * K)
    gm = np.clip(gh / (2.0 * K), 0, 1)

    # i chiodi
    ch_h = np.zeros(sw, np.float32)
    ch_m = np.zeros(sw, np.float32)
    for (uf, vf) in CHIODI_V:
        x_, y_ = foglio_a_scena(uf, vf)
        r_, W2 = 21 * K, int(30 * K)
        ly, lx = np.mgrid[int(y_) - W2:int(y_) + W2, int(x_) - W2:int(x_) + W2].astype(np.float32)
        dd = np.sqrt((lx - x_) ** 2 + (ly - y_) ** 2) / r_
        ch_h[int(y_) - W2:int(y_) + W2, int(x_) - W2:int(x_) + W2] = (np.sqrt(np.clip(1 - dd ** 2, 0, 1)) * 12 + 4 * (dd < 1)) * K
        ch_m[int(y_) - W2:int(y_) + W2, int(x_) - W2:int(x_) + W2] = np.clip((1 - dd) * r_, 0, 1)
    om_ch = gaussian_filter(np.roll(ch_m, (int(9 * K), int(7 * K)), (0, 1)), 4 * K) * (1 - ch_m)
    ruggine = np.clip(rumore(rng, sw, 3) * 0.8 + 0.2, 0, 1)
    ch_col = np.array([0.10, 0.09, 0.085]) * (1 - ruggine[..., None]) + np.array([0.30, 0.13, 0.05]) * ruggine[..., None]

    # ── composizione dei materiali ──
    alb = srgb_lin(W_) * (1 - A[..., None]) + srgb_lin(C) * A[..., None]
    alb *= (0.25 + 0.75 * nz0 ** 0.8)[..., None]          # il palo gira: i fianchi al buio
    alb *= (1 - 0.65 * om_f - 0.6 * om_c - 0.7 * om_ch)[..., None]
    alb = alb * (1 - 0.18 * gm[..., None])
    alb = alb * (1 - 0.10 * rig[..., None])
    alb = alb * (1 - ch_m[..., None]) + srgb_lin(ch_col) * ch_m[..., None]
    altezza = Wa * (1 - A) + (Hp + 2) * A + gh * 1.0 + ch_h
    gy_, gx_ = np.gradient(gaussian_filter(altezza, 0.8 * K))
    n = np.dstack([xn_c - gx_ * 0.7 * nz0, -gy_ * 0.7, nz0 + 0 * xn_c])
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    zs = R * nz0
    # la torcia del pescatore, quasi dalla camera, un po' a sinistra e in alto
    lp = np.array([0.40 * SW, 0.18 * SH, 2.6 * SH], np.float32)
    Lv = np.dstack([lp[0] - xx, lp[1] - yy, lp[2] - zs])
    dist = np.linalg.norm(Lv, axis=-1)
    Lv /= dist[..., None]
    asse = np.array([0.5 * SW, 0.47 * SH, 0.0]) - lp
    asse /= np.linalg.norm(asse)
    cosang = -(Lv * asse[None, None]).sum(-1)
    ang = np.arccos(np.clip(cosang, -1, 1))
    cono = np.clip(1 - (ang - 0.10) / 0.10, 0, 1) ** 1.6 * 0.95 + 0.05 * np.exp(-(ang / 0.30) ** 2)
    cono *= 1 + 0.06 * np.sin(ang * 90)          # gli anelli del riflettore della torcia
    diff = np.clip((n * Lv).sum(-1), 0, 1) ** 1.4 * nz0 ** 0.5
    luce = np.array([1.0, 0.93, 0.80], np.float32) * 2.0
    Hv = Lv + np.array([0, 0, 1], np.float32)
    Hv /= np.linalg.norm(Hv, axis=-1, keepdims=True)
    ndh = np.clip((n * Hv).sum(-1), 0, 1)
    lucido_f = A * (0.10 + 0.5 * Bg)
    spec = (lucido_f * ndh ** 40 * 0.6 + gm * ndh ** 400 * 6.0 + gm * ndh ** 30 * 0.15 + rig * ndh ** 120 * 1.2
            + ch_m * ndh ** 60 * 0.8 + (1 - A) * dentro * ndh ** 20 * 0.04)
    # la luna da destra e dietro: un filo freddo sul bordo del palo
    Lm = np.array([0.85, -0.35, 0.25]); Lm /= np.linalg.norm(Lm)
    rim = np.clip((n * Lm[None, None]).sum(-1), 0, 1) ** 2
    amb = np.array([0.020, 0.026, 0.045], np.float32)
    lin = alb * (amb + luce * (diff * cono)[..., None] + np.array([0.25, 0.35, 0.60]) * 0.35 * rim[..., None])
    lin += luce * (spec * cono)[..., None]
    # bordi del palo morbidi e fuori il fondo notturno
    bordo_p = np.clip((1 - np.abs(xn)) * R / (2.0 * K), 0, 1)
    fondo = sfondo_notte(rng, sw)
    lin = lin * bordo_p[..., None] + fondo * (1 - bordo_p[..., None])
    # nebbiolina
    lin += np.array([0.010, 0.013, 0.022]) * np.clip(0.5 + 0.5 * rumore(rng, sw, 200)[..., None], 0, 1) * 0.12
    out = finitura(lin, rng, vignetta=0.60, grana=0.014)
    if TESTI_V[lingua].get('prova'):
        # i testi di prova non sono controllati: l'immagine lo dice da sola, perché non finisca nel gioco per sbaglio
        d = ImageDraw.Draw(out)
        d.text((24 * SCALA, 20 * SCALA), f'PROVA [{lingua}] · TESTI DA FAR CONTROLLARE A UN MADRELINGUA',
               font=font('Oswald-SemiBold', int(30 * SCALA)), fill=(255, 70, 70))
    if '--webp' in sys.argv:
        p = os.path.join(uscita, 'volantino.webp' if lingua == 'it' else f'volantino_{lingua}.webp')
        out.save(p, quality=90, method=6)
    else:
        p = os.path.join(uscita, 'annuncio_volantino.jpg' if lingua == 'it' else f'annuncio_volantino_{lingua}.jpg')
        out.save(p, quality=93, subsampling=0)
    print(f'volantino → {p}', flush=True)



# ───────────────────────── main ─────────────────────────

def main():
    nomi = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] not in ('--uscita', '--scala', '--lingua', '--sottoinsiemi')]
    uscita = sys.argv[sys.argv.index('--uscita') + 1] if '--uscita' in sys.argv else os.path.join(ROOT, 'docs', 'concept')
    if '--sottoinsiemi' in sys.argv:
        sottoinsiemi(sys.argv[sys.argv.index('--sottoinsiemi') + 1])
    if '--controlla' in sys.argv or '--sottoinsiemi' in sys.argv:
        m = controlla_font()
        print('caratteri mancanti:', m if m else 'nessuno')
        return
    os.makedirs(uscita, exist_ok=True)
    if not nomi or nomi == ['tutti']:
        nomi = ['giornale', 'volantino', 'volantino_en']
    for n in nomi:
        if n == 'volantino':
            lingue = sys.argv[sys.argv.index('--lingua') + 1].split(',') if '--lingua' in sys.argv else ['it']
            for l in lingue:
                volantino(uscita, l)
        elif n.startswith('volantino_'):
            volantino(uscita, n.split('_', 1)[1])
        else:
            giornale(uscita)


if __name__ == '__main__':
    main()
