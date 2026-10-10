"""
Glitchati: fette sfalsate, colori separati, come un nastro rovinato (src/game/catalog.ts, docs/CATALOGO.md).
Il pesce si costruisce normale; il glitch è sull'immagine (pesci.py: glitch_post).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast

Il glitch di sempre (glitch_post: il doppio tenue, le bande strappate, i colori separati, i blocchi a pixel, le
righe) si regola con le opzioni di ogni voce; quello proprio della specie è il suo ritocco(img, c), scritto qui
sotto con pochi aiuti comuni (spostare, comporre, sfocare, proiettare un punto del pesce sull'immagine). Le
misure dei ritocchi sono in frazioni dell'immagine, così l'anteprima veloce (800 px) e il finale (1600 px)
vengono uguali.
"""
import numpy as np

from .base import (DORSALE_LUNGA, PELVICA, PETTORALE, PETTORALE_ALA, PETTORALE_TONDA, RITRATTO_PROTOTIPI, Disegno, Fin,
                   Look, Ritratto, Shape, Specie, coda_forcuta, coda_tonda, coda_tronca)

SPECIE = {}


# ───────────────────────── aiuti per i ritocchi (immagini RGBA 0..1, colori non premoltiplicati) ─────────────────────────

def _sposta(img, dx, dy=0):
    """L'immagine spostata di dx, dy pixel (verso destra e verso il basso) senza farla rientrare dall'altro
    bordo (np.roll la farebbe rientrare): quello che esce si perde, quello che entra è trasparente."""
    H, W = img.shape[:2]
    dx, dy = int(dx), int(dy)
    out = np.zeros_like(img)
    xs0, xs1 = max(0, -dx), min(W, W - dx)
    ys0, ys1 = max(0, -dy), min(H, H - dy)
    if xs1 > xs0 and ys1 > ys0:
        out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = img[ys0:ys1, xs0:xs1]
    return out


def _sopra(alto, basso):
    """Composizione «sopra»: l'immagine alto sopra l'immagine basso (RGBA, colori non premoltiplicati)."""
    aa, ab = alto[..., 3:4], basso[..., 3:4]
    a = aa + ab * (1 - aa)
    rgb = (alto[..., :3] * aa + basso[..., :3] * ab * (1 - aa)) / np.maximum(a, 1e-6)
    return np.concatenate([rgb, a], axis=2)


def _velato(img, k):
    """La stessa immagine con l'alfa moltiplicato per k (uno strato più trasparente)."""
    out = img.copy()
    out[..., 3] *= k
    return out


def _sagoma(img, soglia=0.5):
    """Il riquadro della sagoma (x0, x1, y0, y1, in pixel, estremi compresi): dove l'alfa supera la soglia."""
    ys, xs = np.nonzero(img[..., 3] > soglia)
    if len(xs) == 0:
        H, W = img.shape[:2]
        return 0, W - 1, 0, H - 1
    return int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())


def _sfoca(img, r):
    """Sfocatura gaussiana di raggio r pixel, con i colori pesati dall'alfa (i bordi non diventano neri)."""
    from scipy.ndimage import gaussian_filter
    pre = img[..., :3] * img[..., 3:4]
    a = gaussian_filter(img[..., 3], r)
    pre = np.stack([gaussian_filter(pre[..., i], r) for i in range(3)], axis=2)
    return np.concatenate([pre / np.maximum(a[..., None], 1e-4), a[..., None]], axis=2).astype(np.float32)


# luminanza e crominanza (YIQ, quella dei televisori a colori): per sbavare o girare i colori lasciando la luce
_YIQ = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], np.float32)
_RGB = np.linalg.inv(_YIQ).astype(np.float32)


def _gira_tinta(iq, gradi):
    """Gira la crominanza (canali I e Q, ultimo asse) di tanti gradi (uno solo o un array come i pixel)."""
    a = np.radians(gradi)
    ca, sa = np.cos(a), np.sin(a)
    return np.stack([iq[..., 0] * ca - iq[..., 1] * sa, iq[..., 0] * sa + iq[..., 1] * ca], axis=-1)


def _proietta(c, punti):
    """Punti nelle coordinate del pesce dritto (N, 3) → pixel dell'immagine finita (x da sinistra, y dall'alto),
    con la posa e l'inquadratura del ritratto (quelle del corpo, c.obs[0]). Non vale per i pesci con la piega."""
    sc = c.P.bpy.context.scene
    W, H = sc.render.resolution_x, sc.render.resolution_y
    M = np.array(c.obs[0].matrix_world, np.float32)
    Q = np.asarray(punti, np.float32).reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    x, y, _ = c.P.proietta(Q, sc.camera, W, H)
    return x * W, y * H


# ── Salpa Sfasata (salpa, Sarpa salpa) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['salpa_sfasata'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.05, 0.035), (0.15, 0.092), (0.35, 0.128), (0.55, 0.124), (0.75, 0.082), (0.9, 0.046), (1, 0.04)],
        bot=[(0, -0.026), (0.07, -0.058), (0.2, -0.096), (0.4, -0.12), (0.6, -0.106), (0.8, -0.068), (0.95, -0.042), (1, -0.04)],
        w=[(0, 0.008), (0.08, 0.034), (0.25, 0.053), (0.45, 0.056), (0.7, 0.04), (0.9, 0.02), (1, 0.014)],
        eye_t=0.12, eye_z=0.034, eye_r=0.026, mouth_t=0.045, mouth_z0=-0.02, mouth_z1=-0.026, gill_t=0.25,
        fins=[Fin('dorsal', 0.3, 0.82, [(0, 0), (0.06, 0.95), (0.25, 0.9), (0.55, 0.62), (0.85, 0.66), (1, 0.05)], 0.09, 22, spiny=True),
              Fin('anal', 0.6, 0.82, [(0, 0), (0.12, 0.85), (0.6, 0.6), (1, 0.05)], 0.07, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.45, 0.3), 0.24, 20),
              Fin('pectoral', 0.28, 0.3, [(0, 0), (0.5, 0.3), (1.0, 0.15), (0.8, 0.0), (0, -0.06)], 0.15, 11),
              Fin('pelvic', 0.33, 0.35, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.08, 6)]),
    aspetto=Look(back=(0.12, 0.16, 0.20), flank=(0.36, 0.40, 0.44), belly=(0.62, 0.62, 0.6), fin=(0.16, 0.17, 0.2),
                 iris=(0.95, 0.62, 0.10), iris_dark=(0.45, 0.22, 0.02), pattern='salema'),
    famiglia='glitch', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ── Triglia Doppia (triglia di fango, Mullus barbatus) ──
# Come la triglia di scoglio (trigliocchi) ma con il profilo della fronte quasi verticale (l'occhio alto, sotto
# il profilo), tutta rosa uniforme senza le righe gialle, la prima dorsale senza righe; i due barbigli.
# Il glitch: «si vede due volte, un poco spostata, come in un televisore con l'antenna storta» → un doppio
# forte e netto, spostato a destra come il fantasma dell'antenna, quasi pieno (ritocco); il doppio tenue di
# sempre è spento (doppio=0), e l'inquadratura lascia il posto a destra per il secondo pesce.
def _doppio_antenna(img, c):
    """ritocco: la seconda triglia, spostata a destra e appena in su, più fredda, mezza trasparente, sopra la prima."""
    H, W = img.shape[:2]
    fantasma = _sposta(img, W * 0.085, -H * 0.018)
    fantasma[..., :3] *= np.array((0.78, 0.96, 1.12), np.float32)
    return _sopra(_velato(fantasma, 0.52), img)


SPECIE['triglia_doppia'] = Specie(
    forma=Shape(
        top=[(0, -0.045), (0.012, -0.022), (0.028, 0.024), (0.05, 0.058), (0.085, 0.082), (0.14, 0.098), (0.3, 0.108),
             (0.5, 0.1), (0.72, 0.068), (0.9, 0.04), (1, 0.034)],
        bot=[(0, -0.05), (0.03, -0.075), (0.15, -0.09), (0.38, -0.094), (0.6, -0.078), (0.8, -0.052), (1, -0.034)],
        w=[(0, 0.012), (0.08, 0.04), (0.25, 0.054), (0.5, 0.05), (0.8, 0.028), (1, 0.014)],
        eye_t=0.105, eye_z=0.05, eye_r=0.024, mouth_t=0.048, mouth_z0=-0.046, mouth_z1=-0.054, gill_t=0.23, barbels=True,
        fins=[Fin('dorsal', 0.28, 0.42, [(0, 0), (0.15, 1.0), (0.45, 0.95), (0.8, 0.55), (1, 0.05)], 0.12, 8, spiny=True),
              Fin('dorsal', 0.56, 0.68, [(0, 0), (0.2, 0.8), (0.6, 0.6), (1, 0.05)], 0.07, 9),
              Fin('anal', 0.58, 0.7, [(0, 0), (0.2, 0.75), (0.6, 0.55), (1, 0.05)], 0.065, 8),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.4, 0.3), 0.23, 18),
              Fin('pectoral', 0.25, 0.27, [(0, 0), (0.5, 0.3), (1.0, 0.15), (0.8, 0.0), (0, -0.06)], 0.14, 10),
              Fin('pelvic', 0.3, 0.32, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.08, 6)]),
    aspetto=Look(back=(0.6, 0.17, 0.13), flank=(0.76, 0.36, 0.3), belly=(0.86, 0.7, 0.64), fin=(0.74, 0.48, 0.38),
                 iris=(0.85, 0.6, 0.25), iris_dark=(0.4, 0.14, 0.05), metal=0.3, irid=0.25),
    ritocco=_doppio_antenna,
    famiglia='glitch', piano='fusiforme',
    ritratto=Ritratto(riquadro=(0.72, 0.64), centro=(0.45, 0.47)),
    opzioni=dict(seed=25, doppio=0.0, bande=5, blocchi=2))


# ── Lanzardo Riavvolto (lanzardo, Scomber colias) ──
# Lo sgombro (sgombrato) con l'occhio più grande, le barre del dorso più spezzate, le pinnule dietro la seconda
# dorsale e l'anale, e le macchiette grigie sul ventre che lo distinguono dallo sgombro.
# Il glitch: «nuota all'indietro, a scatti, come un nastro riavvolto» → il ritratto lo gira verso destra e lui
# torna indietro (verso sinistra): davanti alla testa restano i fotogrammi di prima, a fette e a scatti; qualche
# riga si stira in avanti come il nastro che corre; due barre di disturbo del riavvolgimento lo attraversano.
def _riavvolto(img, c):
    """ritocco: le copie a fette davanti alla testa, le righe stirate, le barre del riavvolgimento."""
    rng = np.random.default_rng(32)
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    # i fotogrammi di prima: copie spostate a destra (davanti alla testa), a fette con un piccolo scatto
    # ciascuna, sempre più tenui; qualche fetta manca (il fotogramma saltato)
    scie = np.zeros_like(img)
    fetta = max(2, int(H * 0.016))
    for k in (3, 2, 1):
        copia = _sposta(img, W * 0.06 * k, 0)
        for y in range(0, H, fetta):
            if rng.random() < 0.25:
                copia[y:y + fetta] = 0
            else:
                copia[y:y + fetta] = _sposta(copia[y:y + fetta], rng.normal(0, W * 0.01), 0)
        scie = _sopra(_velato(copia, 0.55 / k), scie)
    out = _sopra(img, scie)
    # le righe stirate in avanti: il colore dell'ultimo pixel del pesce verso la testa corre a destra e sfuma
    for _ in range(7):
        h = max(1, int(H * rng.uniform(0.003, 0.01)))
        y = int(rng.uniform(y0 + 0.15 * (y1 - y0), y1 - 0.15 * (y1 - y0)))
        lung = int(W * rng.uniform(0.1, 0.24))
        for yy in range(y, min(H, y + h)):
            dentro = np.nonzero(img[yy, :, 3] > 0.5)[0]
            if len(dentro) == 0:
                continue
            x = int(dentro.max())
            n = min(lung, W - 1 - x)
            if n < 2:
                continue
            f = (np.linspace(1, 0, n) ** 1.6 * 0.9)[:, None]
            seg = out[yy, x + 1:x + 1 + n]
            col = img[yy, x - 1, :3] * 1.15
            seg[:, :3] = seg[:, :3] * (1 - f) + col * f
            seg[:, 3:4] = np.maximum(seg[:, 3:4], f)
    # le barre di disturbo del riavvolgimento: la fascia scorre di lato ed è piena di neve
    for _ in range(2):
        h = max(2, int(H * rng.uniform(0.018, 0.03)))
        y = int(rng.uniform(y0 + 0.1 * (y1 - y0), y1 - 0.2 * (y1 - y0)))
        fascia = _sposta(out[y:y + h], W * rng.uniform(-0.05, -0.02), 0)
        neve = rng.random(fascia.shape[:2]).astype(np.float32)[..., None]
        fascia[..., :3] = fascia[..., :3] * 0.4 + neve * 0.75
        out[y:y + h] = fascia
    return out


SPECIE['lanzardo_riavvolto'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.03, 0.022), (0.09, 0.055), (0.2, 0.082), (0.36, 0.092), (0.55, 0.082), (0.75, 0.05), (0.9, 0.026),
             (1, 0.018)],
        bot=[(0, -0.012), (0.04, -0.035), (0.12, -0.062), (0.3, -0.088), (0.5, -0.085), (0.72, -0.055), (0.9, -0.026),
             (1, -0.018)],
        w=[(0, 0.004), (0.05, 0.026), (0.15, 0.05), (0.35, 0.058), (0.6, 0.046), (0.85, 0.02), (1, 0.011)],
        eye_t=0.078, eye_z=0.017, eye_r=0.026, mouth_t=0.078, mouth_z0=-0.008, mouth_z1=-0.017, gill_t=0.2,
        fins=[Fin('dorsal', 0.28, 0.4, [(0, 0), (0.15, 0.9), (0.4, 1.0), (0.75, 0.55), (1, 0.08)], 0.1, 10, spiny=True),
              Fin('dorsal', 0.56, 0.64, [(0, 0), (0.25, 0.8), (0.6, 0.55), (1, 0.05)], 0.06, 8),
              Fin('anal', 0.58, 0.66, [(0, 0), (0.25, 0.75), (0.6, 0.5), (1, 0.05)], 0.055, 8),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.55, 0.26), 0.24, 18),
              Fin('pectoral', 0.20, 0.215, PETTORALE, 0.11, 9),
              Fin('pelvic', 0.27, 0.285, PELVICA, 0.06, 6)]
             # le pinnule: cinque dietro la seconda dorsale e cinque dietro l'anale
             + [Fin('dorsal', 0.68 + 0.05 * i, 0.7 + 0.05 * i, [(0, 0), (0.25, 1.0), (1, 0.15)], 0.018, 4) for i in range(5)]
             + [Fin('anal', 0.7 + 0.048 * i, 0.72 + 0.048 * i, [(0, 0), (0.25, 1.0), (1, 0.15)], 0.016, 4) for i in range(5)]),
    aspetto=Look(back=(0.06, 0.2, 0.2), flank=(0.36, 0.39, 0.33), belly=(0.66, 0.66, 0.62), fin=(0.12, 0.14, 0.12),
                 iris=(0.6, 0.6, 0.52), iris_dark=(0.1, 0.1, 0.1), metal=0.5, irid=0.5,
                 disegni=[Disegno('barre', colore=(0.02, 0.05, 0.06), forza=0.92, n=7, v0=0.12, onda=1.2),
                          Disegno('macchie', colore=(0.2, 0.22, 0.24), forza=0.8, scala=55, r=0.22, u0=0.12, u1=0.85,
                                  v0=-0.85, v1=-0.12, seme=2)]),
    ritocco=_riavvolto,
    famiglia='glitch', piano='fusiforme',
    ritratto=Ritratto(yaw=168.0, pitch=-4.0, riquadro=(0.66, 0.62), centro=(0.4, 0.47)),
    opzioni=dict(seed=31))


# ── Donzella Saturata (donzella, Coris julis) ──
# Il labride piccolo e slanciato del maschio: muso appuntito con la boccuccia, la dorsale lunga e bassa con le
# prime spine lunghe a bandierina, la coda tronca; dorso verde, la fascia arancione a zig-zag lungo il fianco
# (strisce con onda) e sotto la riga azzurra, la macchia nera dietro la pettorale, il ventre bianco.
# Il glitch: «colori troppo accesi, come le cassette dei cartoni animati consumate… ti lascia l'arcobaleno sulle
# mani» → saturazione esagerata (opzioni) e i colori che sbavano verso destra oltre la sagoma, girando in un
# arcobaleno (ritocco), come la crominanza di una cassetta consumata.
def _sbavata(img, c):
    """ritocco: la crominanza (I, Q) si allunga a destra e sfuma; fuori dalla sagoma la sbavatura gira la tinta
    a ogni passo e lascia la scia d'arcobaleno; dentro resta la luce di prima con i colori sbavati."""
    H, W = img.shape[:2]
    a = img[..., 3]
    yiq = img[..., :3] @ _YIQ.T
    L = max(4, int(W * 0.045))
    pesi = np.exp(-np.arange(L + 1) / (L * 0.35)).astype(np.float32)
    acc_a = np.zeros_like(a)
    acc_y = np.zeros_like(a)
    acc_iq = np.zeros(a.shape + (2,), np.float32)
    acc_arc = np.zeros(a.shape + (2,), np.float32)
    for i, p in enumerate(pesi):
        sa = _sposta(a[..., None], i, 0)[..., 0] * p
        acc_a += sa
        acc_y += _sposta(yiq[..., :1], i, 0)[..., 0] * sa
        iq = _sposta(yiq[..., 1:], i, 0)
        acc_iq += iq * sa[..., None]
        # la scia d'arcobaleno: la stessa crominanza, ma girata di più a ogni passo e più accesa
        acc_arc += _gira_tinta(iq * 1.6, 330.0 * i / L) * sa[..., None]
    tot = np.maximum(acc_a, 1e-5)
    a_s = acc_a / pesi.sum()
    iq_s = acc_iq / tot[..., None]
    arc = acc_arc / tot[..., None]
    y_s = acc_y / tot
    out = img.copy()
    # dentro: la luce di prima, la crominanza sbavata
    dentro = np.concatenate([yiq[..., :1], iq_s * 0.8 + yiq[..., 1:] * 0.35], axis=2) @ _RGB.T
    out[..., :3] = img[..., :3] * (1 - a[..., None]) + dentro * a[..., None]
    # fuori (dove la sbavatura supera la sagoma): l'arcobaleno, mezzo trasparente
    fuori = np.clip(a_s - a, 0, 1) * 0.75
    scia = np.concatenate([y_s[..., None] * 0.9 + 0.08, arc], axis=2) @ _RGB.T
    nuovo_a = a + fuori * (1 - a)
    out[..., :3] = (out[..., :3] * a[..., None] + scia * fuori[..., None] * (1 - a[..., None])) / np.maximum(nuovo_a, 1e-5)[..., None]
    out[..., 3] = nuovo_a
    return out


SPECIE['donzella_saturata'] = Specie(
    forma=Shape(
        top=[(0, -0.008), (0.02, 0.01), (0.05, 0.03), (0.1, 0.052), (0.18, 0.07), (0.3, 0.078), (0.45, 0.074), (0.6, 0.062),
             (0.75, 0.046), (0.88, 0.033), (1, 0.028)],
        bot=[(0, -0.014), (0.03, -0.027), (0.08, -0.045), (0.18, -0.062), (0.32, -0.07), (0.48, -0.066), (0.64, -0.052),
             (0.8, -0.037), (1, -0.028)],
        w=[(0, 0.005), (0.06, 0.021), (0.2, 0.034), (0.45, 0.032), (0.75, 0.02), (1, 0.011)],
        eye_t=0.072, eye_z=0.018, eye_r=0.0145, mouth_t=0.035, mouth_z0=-0.007, mouth_z1=-0.01, gill_t=0.18,
        fins=[Fin('dorsal', 0.19, 0.86, [(0, 0), (0.008, 2.2), (0.02, 1.9), (0.036, 0.75), (0.08, 0.6), (0.5, 0.62), (0.9, 0.72),
                                        (1, 0.1)], 0.042, 70, spiny=True, colore=(0.22, 0.45, 0.34), bordo=(0.9, 0.3, 0.05)),
              Fin('anal', 0.5, 0.86, [(0, 0), (0.05, 0.7), (0.5, 0.7), (0.9, 0.75), (1, 0.1)], 0.038, 36, colore=(0.2, 0.42, 0.42),
                  bordo=(0.15, 0.35, 0.85)),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.55, 0.04, 0.8), 0.14, 16),
              Fin('pectoral', 0.19, 0.2, PETTORALE_TONDA, 0.07, 9),
              Fin('pelvic', 0.24, 0.25, PELVICA, 0.04, 5)]),
    aspetto=Look(back=(0.06, 0.2, 0.12), flank=(0.22, 0.42, 0.5), belly=(0.82, 0.84, 0.86), fin=(0.25, 0.42, 0.42),
                 iris=(0.9, 0.5, 0.15), iris_dark=(0.35, 0.1, 0.04), metal=0.2, irid=0.5, squame=0.5,
                 disegni=[Disegno('strisce', colore=(0.95, 0.32, 0.04), forza=0.95, n=1, v0=-0.16, v1=0.34, larghezza=0.3,
                                  onda=0.085, u0=0.13, u1=0.97),
                          Disegno('strisce', colore=(0.15, 0.4, 0.9), forza=0.8, n=1, v0=-0.42, v1=-0.24, larghezza=0.07,
                                  onda=0.06, u0=0.13, u1=0.95),
                          Disegno('macchia', colore=(0.01, 0.015, 0.03), forza=0.95, u=0.255, v=0.02, r=0.013,
                                  allungamento=0.75)]),
    ritocco=_sbavata,
    famiglia='glitch', piano='fusiforme',
    ritratto=Ritratto(riquadro=(0.74, 0.66), centro=(0.46, 0.46)),
    opzioni=dict(seed=41, saturazione=2.1))


# ── Castagnola Sgranata (castagnola, Chromis chromis) ──
# Piccola, ovale e alta; la coda forcuta profonda con i lobi lunghi; dorsale lunga (spinosa e poi molle, più
# alta dietro), anale corta e alta, le pelviche col filamento; bruno-blu scuro con le squame orlate.
# Il glitch: «da vicino è tutta puntini, come una foto ingrandita troppo. Più ti avvicini, meno pesce c'è» →
# retinatura a puntini (ritocco), fitta sul bordo e sempre più rada verso il centro del pesce, dove i puntini
# rimpiccioliscono e mancano.
def _retinata(img, c):
    """ritocco: una cella ogni ~1/95 della larghezza; in ogni cella un puntino del colore medio, grande quanto la
    luce e la copertura della cella; verso il centro della sagoma (ellisse del riquadro) i puntini calano e mancano."""
    rng = np.random.default_rng(52)
    H, W = img.shape[:2]
    cel = max(4, int(round(W / 95)))
    x0, x1, y0, y1 = _sagoma(img)
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    nh, nw = (H + cel - 1) // cel, (W + cel - 1) // cel
    pad = np.zeros((nh * cel, nw * cel, 4), np.float32)
    pad[:H, :W] = img
    blocchi = pad.reshape(nh, cel, nw, cel, 4)
    cop = blocchi[..., 3].mean(axis=(1, 3))
    col = (blocchi[..., :3] * blocchi[..., 3:4]).sum(axis=(1, 3)) / np.maximum(blocchi[..., 3].sum(axis=(1, 3)), 1e-5)[..., None]
    lum = col @ np.array((0.299, 0.587, 0.114), np.float32)
    # quanto è lontana dal centro ogni cella (0 al centro, 1 sul bordo dell'ellisse)
    gy, gx = np.mgrid[0:nh, 0:nw].astype(np.float32)
    rn = np.hypot((gx * cel + cel / 2 - cx) / max(rx, 1), (gy * cel + cel / 2 - cy) / max(ry, 1))
    rada = np.clip(rn / 0.85, 0, 1) ** 1.3
    raggio = cel * 0.5 * np.sqrt(np.clip(0.35 + lum * 2.2, 0, 1.15)) * np.clip(cop * 1.4, 0, 1) * (0.3 + 0.7 * rada)
    raggio *= rng.random((nh, nw)) < 0.25 + 0.8 * rada           # al centro ne mancano
    # i puntini, con il bordo morbido di mezzo pixel
    yy, xx = np.mgrid[0:nh * cel, 0:nw * cel].astype(np.float32)
    dist = np.hypot(yy % cel - cel / 2 + 0.5, xx % cel - cel / 2 + 0.5)
    r_pix = np.repeat(np.repeat(raggio, cel, axis=0), cel, axis=1)
    alfa = np.clip(r_pix - dist + 0.5, 0, 1)
    col_pix = np.repeat(np.repeat(np.clip(col * 1.35, 0, 1), cel, axis=0), cel, axis=1)
    out = np.concatenate([col_pix, alfa[..., None]], axis=2)[:H, :W]
    return out.astype(np.float32)


SPECIE['castagnola_sgranata'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.03, 0.028), (0.08, 0.08), (0.15, 0.13), (0.25, 0.168), (0.38, 0.185), (0.5, 0.176), (0.65, 0.13),
             (0.8, 0.082), (0.92, 0.06), (1, 0.055)],
        bot=[(0, -0.036), (0.04, -0.07), (0.12, -0.115), (0.25, -0.155), (0.4, -0.168), (0.55, -0.15), (0.7, -0.105),
             (0.85, -0.068), (1, -0.055)],
        w=[(0, 0.008), (0.06, 0.03), (0.2, 0.048), (0.45, 0.05), (0.7, 0.034), (0.9, 0.02), (1, 0.015)],
        eye_t=0.11, eye_z=0.045, eye_r=0.032, mouth_t=0.045, mouth_z0=-0.012, mouth_z1=-0.022, gill_t=0.26,
        fins=[Fin('dorsal', 0.26, 0.86, [(0, 0), (0.04, 0.6), (0.45, 0.65), (0.6, 1.0), (0.8, 1.05), (0.95, 0.6), (1, 0.05)], 0.1, 30,
                  spiny=True),
              Fin('anal', 0.58, 0.86, [(0, 0), (0.1, 0.55), (0.45, 1.0), (0.8, 0.9), (1, 0.05)], 0.1, 16),
              Fin('caudal', 1.0, 1.0, coda_forcuta(2.1, 0.12, 1.1), 0.21, 22),
              Fin('pectoral', 0.29, 0.3, PETTORALE, 0.11, 10),
              Fin('pelvic', 0.3, 0.31, [(0, 0), (0.6, 0.2), (1.25, 0.04), (0.5, -0.05), (0, -0.05)], 0.1, 6)]),
    aspetto=Look(back=(0.06, 0.05, 0.05), flank=(0.15, 0.11, 0.085), belly=(0.24, 0.2, 0.17), fin=(0.08, 0.07, 0.08),
                 iris=(0.4, 0.5, 0.7), iris_dark=(0.05, 0.06, 0.1), metal=0.25, irid=0.7,
                 disegni=[Disegno('reticolo', colore=(0.03, 0.025, 0.025), forza=0.55, scala=26, larghezza=0.05),
                          Disegno('sfumatura', colore=(0.07, 0.12, 0.26), forza=0.55, v0=0.3, larghezza=0.25)]),
    ritocco=_retinata,
    famiglia='glitch', piano='alto',
    opzioni=dict(seed=51))


# ── Pagello Pixelato (pagello fragolino, Pagellus erythrinus) ──
# Lo sparide rosa fragola: ovale allungato, muso un poco appuntito, occhio grande, dorsale lunga, coda forcuta;
# il dorso più rosso con i puntini azzurri, il ventre argento-rosa.
# Il glitch: «ha gli spigoli… e qualche quadratino in meno» → pixel grossi con la sagoma a scalini, netta
# (ogni quadretto o c'è o non c'è), qualche quadretto sparito e qualcuno fuori posto (ritocco); poi le righe.
def _pixelato(img, c):
    """ritocco: quadretti di ~1/70 della larghezza, ciascuno del colore medio; pieni o vuoti (gli spigoli);
    uno su quindici dentro il pesce sparisce, qualcuno scivola di un quadretto; le righe di sempre sopra."""
    rng = np.random.default_rng(62)
    H, W = img.shape[:2]
    q = max(5, int(round(W / 70)))
    nh, nw = (H + q - 1) // q, (W + q - 1) // q
    pad = np.zeros((nh * q, nw * q, 4), np.float32)
    pad[:H, :W] = img
    b = pad.reshape(nh, q, nw, q, 4)
    cop = b[..., 3].mean(axis=(1, 3))
    col = (b[..., :3] * b[..., 3:4]).sum(axis=(1, 3)) / np.maximum(b[..., 3].sum(axis=(1, 3)), 1e-5)[..., None]
    pieno = cop > 0.42
    # i quadratini in meno: più spesso vicino al bordo della sagoma, qualcuno anche in mezzo
    from scipy.ndimage import binary_erosion
    bordo = pieno & ~binary_erosion(pieno, iterations=2)
    via = pieno & (rng.random((nh, nw)) < np.where(bordo, 0.14, 0.05))
    pieno &= ~via
    alfa = pieno.astype(np.float32)
    # qualcuno fuori posto: un quadretto copiato una casella più in là
    ys, xs = np.nonzero(pieno)
    for i in rng.choice(len(ys), size=min(6, len(ys)), replace=False):
        y, x = ys[i], min(nw - 1, xs[i] + int(rng.choice((-2, -1, 1, 2))))
        col[y, x], alfa[y, x] = col[ys[i], xs[i]], 1.0
    out = np.concatenate([np.repeat(np.repeat(col, q, axis=0), q, axis=1),
                          np.repeat(np.repeat(alfa, q, axis=0), q, axis=1)[..., None]], axis=2)[:H, :W].copy()
    # il bordo di ogni quadretto appena più scuro (si vedono gli spigoli anche dentro) e le righe
    yy, xx = np.mgrid[0:H, 0:W]
    griglia = ((yy % q) == q - 1) | ((xx % q) == q - 1)
    out[griglia, :3] *= 0.86
    out[::3, :, :3] *= 0.9
    return out.astype(np.float32)


SPECIE['pagello_pixelato'] = Specie(
    forma=Shape(
        top=[(0, -0.015), (0.03, 0.02), (0.08, 0.06), (0.15, 0.1), (0.25, 0.13), (0.38, 0.142), (0.52, 0.135), (0.7, 0.095),
             (0.85, 0.058), (0.95, 0.042), (1, 0.04)],
        bot=[(0, -0.03), (0.04, -0.06), (0.12, -0.095), (0.25, -0.125), (0.4, -0.135), (0.55, -0.122), (0.72, -0.085),
             (0.88, -0.052), (1, -0.04)],
        w=[(0, 0.007), (0.07, 0.032), (0.22, 0.05), (0.42, 0.054), (0.68, 0.04), (0.88, 0.02), (1, 0.014)],
        eye_t=0.12, eye_z=0.045, eye_r=0.028, mouth_t=0.06, mouth_z0=-0.026, mouth_z1=-0.035, gill_t=0.27,
        fins=[Fin('dorsal', 0.3, 0.84, DORSALE_LUNGA, 0.1, 22, spiny=True),
              Fin('anal', 0.62, 0.84, [(0, 0), (0.12, 0.9), (0.6, 0.62), (0.95, 0.5), (1, 0.05)], 0.08, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.3), 0.25, 20),
              Fin('pectoral', 0.3, 0.32, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.18, 12),
              Fin('pelvic', 0.35, 0.37, PELVICA, 0.09, 7, spiny=True)]),
    aspetto=Look(back=(0.62, 0.18, 0.2), flank=(0.82, 0.45, 0.44), belly=(0.88, 0.76, 0.74), fin=(0.78, 0.42, 0.42),
                 iris=(0.85, 0.65, 0.4), iris_dark=(0.35, 0.12, 0.08), metal=0.5, irid=0.4,
                 disegni=[Disegno('macchie', colore=(0.3, 0.62, 1.0), forza=0.95, scala=55, r=0.16, u0=0.12, u1=0.85, v0=0.1,
                                  seme=3)]),
    ritocco=_pixelato,
    famiglia='glitch', piano='fusiforme',
    opzioni=dict(seed=61))


# ── Menola Neve (menola, Spicara maena) ──
# Come lo zerro ma più alta: muso appuntito con la bocca protrattile, occhio grande, la dorsale lunga
# continua, coda forcuta; grigio-azzurro argentato, e la macchia scura rettangolare sul fianco.
# Il glitch: «coperta di neve bianca e nera che sfrigola. Se avvicini l'orecchio, sotto la neve senti un canale
# lontano» → neve televisiva dentro la sagoma (ritocco), a granelli appena allungati come quelli del
# televisore, con le righe più chiare e più scure; sotto, il pesce si vede ancora, come il canale lontano.
def _neve_tv(img, c):
    """ritocco: neve in bianco e nero dentro la sagoma, a granelli larghi il doppio che alti (un pixel ogni 800
    di larghezza), righe che sfrigolano più forte; il pesce sotto resta a metà."""
    rng = np.random.default_rng(72)
    H, W = img.shape[:2]
    g = max(1, int(round(W / 800)))
    n = rng.random(((H + g - 1) // g, (W + 2 * g - 1) // (2 * g))).astype(np.float32)
    n = np.repeat(np.repeat(n, g, axis=0), 2 * g, axis=1)[:H, :W]
    # righe che sfrigolano: ogni riga di granelli un poco più chiara o più scura, qualcuna bianca
    riga = np.repeat(rng.normal(0, 0.12, (H + g - 1) // g), g)[:H].astype(np.float32)
    riga += np.repeat((rng.random((H + g - 1) // g) < 0.04) * 0.35, g)[:H].astype(np.float32)
    n = np.clip(n * 1.1 - 0.05 + riga[:, None], 0, 1)
    out = img.copy()
    luce = img[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32)
    k = 0.62 * img[..., 3]
    # la neve si somma alla luce del pesce (il canale lontano sotto la neve), in bianco e nero
    neve = np.clip(n * 0.85 + luce * 0.35, 0, 1)
    out[..., :3] = img[..., :3] * (1 - k[..., None]) + neve[..., None] * k[..., None]
    return out


SPECIE['menola_neve'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.02), (0.08, 0.056), (0.15, 0.092), (0.25, 0.118), (0.38, 0.128), (0.52, 0.12), (0.7, 0.084),
             (0.85, 0.052), (0.95, 0.038), (1, 0.035)],
        bot=[(0, -0.024), (0.04, -0.05), (0.12, -0.082), (0.25, -0.108), (0.42, -0.116), (0.58, -0.102), (0.74, -0.07),
             (0.88, -0.044), (1, -0.035)],
        w=[(0, 0.006), (0.07, 0.027), (0.22, 0.04), (0.42, 0.042), (0.68, 0.031), (0.88, 0.016), (1, 0.012)],
        eye_t=0.105, eye_z=0.032, eye_r=0.028, mouth_t=0.055, mouth_z0=-0.01, mouth_z1=-0.022, gill_t=0.25,
        fins=[Fin('dorsal', 0.28, 0.84, [(0, 0), (0.08, 0.9), (0.2, 0.95), (0.5, 0.62), (0.62, 0.68), (0.9, 0.6), (1, 0.05)], 0.085,
                  24, spiny=True),
              Fin('anal', 0.6, 0.84, [(0, 0), (0.12, 0.8), (0.6, 0.55), (1, 0.05)], 0.065, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.25), 0.23, 18),
              Fin('pectoral', 0.27, 0.28, PETTORALE, 0.13, 10),
              Fin('pelvic', 0.3, 0.31, PELVICA, 0.07, 6)]),
    aspetto=Look(back=(0.1, 0.12, 0.16), flank=(0.42, 0.46, 0.5), belly=(0.7, 0.72, 0.72), fin=(0.2, 0.22, 0.26),
                 iris=(0.7, 0.68, 0.6), iris_dark=(0.12, 0.12, 0.12), metal=0.6, irid=0.4,
                 # la macchia rettangolare: una fascia limitata in u e in v, con i bordi appena morbidi
                 disegni=[Disegno('sfumatura', colore=(0.025, 0.025, 0.03), forza=0.95, u0=0.38, u1=0.47, v0=-0.12, v1=0.36,
                                  larghezza=0.012),
                          Disegno('strisce', colore=(0.3, 0.45, 0.7), forza=0.35, n=3, v0=0.1, v1=0.75, larghezza=0.05,
                                  u0=0.25, u1=0.85)]),
    ritocco=_neve_tv,
    famiglia='glitch', piano='fusiforme',
    opzioni=dict(seed=71))


# ── Pettine a Scatti (pesce pettine, Xyrichtys novacula) ──
# Compresso e alto, con la fronte a picco come una lama e la boccuccia in basso, gli occhi alti; la dorsale
# lunga da sopra l'occhio alla coda (le prime due spine appena staccate), l'anale lunga, la coda tronca;
# rosato madreperla, con le righe azzurre verticali sul muso.
# Il glitch: «si muove a scatti, saltando dei fotogrammi. Ogni volta che salta è un po' più vicino al bordo» →
# dietro il pesce (a destra) i fotogrammi di prima, a scatti in su e in giù, sempre più tenui e con le righe
# mancanti, e un buco dove manca un fotogramma (ritocco); il pesce vero è il più avanti, verso il bordo.
def _a_scatti(img, c):
    """ritocco: quattro fotogrammi di prima (il terzo saltato), spostati a destra a passi uguali e a scatti in
    verticale, con qualche fascia di righe che manca; sotto il pesce vero."""
    rng = np.random.default_rng(82)
    H, W = img.shape[:2]
    dietro = np.zeros_like(img)
    passi = [(1, -0.035, 0.5), (2, 0.03, 0.34), (4, -0.02, 0.18)]       # (fotogramma, scatto in su/giù, opacità)
    for k, dy, op in reversed(passi):
        copia = _sposta(img, W * 0.085 * k, H * dy)
        # le righe che mancano: fasce sottili vuote, sempre di più nei fotogrammi vecchi
        y = 0
        while y < H:
            h = max(1, int(H * rng.uniform(0.006, 0.02)))
            if rng.random() < 0.18 * k:
                copia[y:y + h] = 0
            y += h
        dietro = _sopra(_velato(copia, op), dietro)
    return _sopra(img, dietro)


SPECIE['pettine_a_scatti'] = Specie(
    forma=Shape(
        top=[(0, -0.05), (0.008, -0.012), (0.02, 0.04), (0.04, 0.088), (0.07, 0.122), (0.13, 0.146), (0.28, 0.156), (0.45, 0.148),
             (0.62, 0.12), (0.78, 0.084), (0.9, 0.058), (1, 0.05)],
        bot=[(0, -0.062), (0.03, -0.088), (0.1, -0.112), (0.25, -0.13), (0.42, -0.13), (0.6, -0.112), (0.78, -0.08),
             (0.9, -0.058), (1, -0.05)],
        w=[(0, 0.006), (0.05, 0.022), (0.2, 0.033), (0.45, 0.031), (0.7, 0.022), (0.9, 0.013), (1, 0.01)],
        eye_t=0.085, eye_z=0.074, eye_r=0.021, mouth_t=0.035, mouth_z0=-0.055, mouth_z1=-0.063, gill_t=0.24,
        fins=[Fin('dorsal', 0.1, 0.93, [(0, 0), (0.015, 0.95), (0.035, 0.85), (0.06, 0.35), (0.1, 0.72), (0.5, 0.78), (0.9, 0.85),
                                       (1, 0.1)], 0.06, 60, spiny=True),
              Fin('anal', 0.47, 0.93, [(0, 0), (0.05, 0.7), (0.5, 0.78), (0.9, 0.85), (1, 0.1)], 0.052, 34),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.6, 0.02, 0.85), 0.15, 16),
              Fin('pectoral', 0.23, 0.24, PETTORALE_TONDA, 0.08, 10),
              Fin('pelvic', 0.25, 0.26, PELVICA, 0.05, 5)]),
    aspetto=Look(back=(0.55, 0.3, 0.27), flank=(0.82, 0.56, 0.48), belly=(0.86, 0.72, 0.66), fin=(0.72, 0.5, 0.45),
                 iris=(0.85, 0.55, 0.3), iris_dark=(0.35, 0.12, 0.06), metal=0.3, irid=0.65, squame=0.7,
                 disegni=[Disegno('bande', colore=(0.28, 0.45, 0.85), forza=0.85, n=5, u0=0.0, u1=0.13, larghezza=0.22,
                                  inclinazione=0.02, v0=-0.85, v1=0.95)]),
    ritocco=_a_scatti,
    famiglia='glitch', piano='alto',
    ritratto=Ritratto(riquadro=(0.58, 0.58), centro=(0.34, 0.48)),
    opzioni=dict(seed=81))


# ── Re di Triglie a Righe (re di triglie, Apogon imberbis) ──
# Piccolo e robusto, la testa e gli occhi grandissimi, la bocca larga e obliqua; due dorsali separate, l'anale
# sotto la seconda, la coda appena forcuta; rosso-arancio, con il punto scuro sul peduncolo.
# Il glitch: «fatto di righe orizzontali, una sì e una no. Nelle righe che mancano c'è un altro pesce, che non
# riesci mai a vedere bene» → interlacciato (ritocco): nelle righe pari il re di triglie, nelle dispari un altro
# pesce, scuro e sfocato, più lungo e girato dall'altra parte, con un occhio chiaro.
def _altro_pesce(img, c):
    """ritocco: righe alte mezzo centesimo dell'immagine, una sì e una no; nelle dispari l'altro pesce, fatto
    dalla sagoma di questo girata, allungata, schiacciata, scura e sfocata, con l'occhio che riflette."""
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # l'altro pesce: il punto (sx, sy) di questo finisce in (cx + D − (sx − cx)·S, cy − E + (sy − cy)·K): girato a
    # specchio, S volte più lungo, K volte più basso, appena spostato; per ogni pixel si prende il punto da cui viene
    S, K, D, E = 1.12, 0.72, W * 0.03, H * 0.035
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sx = np.clip(cx - (xx - cx - D) / S, 0, W - 1).astype(int)
    sy = np.clip(cy + (yy - cy + E) / K, 0, H - 1).astype(int)
    altro = img[sy, sx].copy()
    luce = altro[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32)
    altro[..., :3] = luce[..., None] * np.array((0.35, 0.45, 0.48), np.float32) + 0.02
    altro = _sfoca(altro, W * 0.004)
    altro[..., 3] *= 0.85
    # l'occhio dell'altro: dove finisce l'occhio di questo, un punto chiaro che riflette
    ex, ey = _proietta(c, c.body.occhi_lista()[0][0])
    ox, oy = cx + D - (float(ex[0]) - cx) * S, cy - E + (float(ey[0]) - cy) * K
    occhio = np.exp(-((xx - ox) ** 2 + (yy - oy) ** 2) / (2 * (W * 0.005) ** 2))
    altro[..., :3] += occhio[..., None] * np.array((0.75, 0.8, 0.7), np.float32)
    altro[..., 3] = np.maximum(altro[..., 3], occhio * 0.9)
    hl = max(1, H // 200)
    dispari = ((np.arange(H) // hl) % 2 == 1)
    out = img.copy()
    out[dispari] = altro[dispari]
    return np.clip(out, 0, 1)


SPECIE['re_di_triglie_a_righe'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.03, 0.024), (0.07, 0.062), (0.13, 0.096), (0.22, 0.118), (0.35, 0.124), (0.5, 0.112), (0.65, 0.084),
             (0.78, 0.064), (0.9, 0.057), (1, 0.055)],
        bot=[(0, -0.042), (0.04, -0.072), (0.1, -0.1), (0.22, -0.118), (0.38, -0.12), (0.55, -0.1), (0.7, -0.075), (0.85, -0.062),
             (1, -0.055)],
        w=[(0, 0.01), (0.06, 0.036), (0.2, 0.054), (0.4, 0.05), (0.65, 0.035), (0.85, 0.025), (1, 0.018)],
        eye_t=0.11, eye_z=0.036, eye_r=0.04, mouth_t=0.1, mouth_z0=-0.016, mouth_z1=-0.05, gill_t=0.27,
        fins=[Fin('dorsal', 0.3, 0.42, [(0, 0), (0.2, 0.95), (0.45, 1.0), (0.8, 0.6), (1, 0.05)], 0.11, 8, spiny=True),
              Fin('dorsal', 0.52, 0.66, [(0, 0), (0.2, 1.0), (0.5, 0.85), (0.85, 0.5), (1, 0.05)], 0.11, 10),
              Fin('anal', 0.55, 0.68, [(0, 0), (0.2, 0.95), (0.5, 0.8), (0.85, 0.45), (1, 0.05)], 0.09, 10),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.35, 0.5), 0.2, 18),
              Fin('pectoral', 0.28, 0.29, PETTORALE, 0.1, 10),
              Fin('pelvic', 0.3, 0.31, PELVICA, 0.08, 6, spiny=True)]),
    aspetto=Look(back=(0.6, 0.12, 0.06), flank=(0.86, 0.32, 0.12), belly=(0.9, 0.56, 0.4), fin=(0.85, 0.36, 0.16),
                 iris=(0.9, 0.75, 0.4), iris_dark=(0.4, 0.15, 0.05), metal=0.2, irid=0.3,
                 disegni=[Disegno('macchia', colore=(0.08, 0.02, 0.02), forza=0.9, u=0.9, v=0.05, r=0.02)]),
    ritocco=_altro_pesce,
    famiglia='glitch', piano='fusiforme',
    ritratto=Ritratto(riquadro=(0.68, 0.6), centro=(0.48, 0.47)),
    opzioni=dict(seed=91))


# ── Occhialone Veloce (occhialone, Pagellus bogaraveo) ──
# Lo sparide ovale con l'occhio grandissimo (un terzo della testa) e il muso corto e tondo; la macchia nera
# all'inizio della linea laterale, sopra l'opercolo; grigio-rosato argento, le pinne rossicce, coda forcuta.
# Il glitch: «vive tutto più in fretta. Quando lo tiri su è giovane, quando lo metti nel secchio è vecchio, e
# domattina sarà polvere» → l'avanti veloce lungo il corpo (ritocco): la testa fresca, a metà invecchia (si
# sbiadisce e ingiallisce), la coda si sbriciola in polvere che vola via; due righe dell'avanti veloce.
def _avanti_veloce(img, c):
    """ritocco: lungo la sagoma (u = 0 al muso, 1 in punta alla coda) i colori invecchiano da u 0.3 a 0.75; da
    u 0.66 la sagoma si sbriciola a granelli, e i granelli tolti volano via a destra e in su, sempre più tenui."""
    rng = np.random.default_rng(102)
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    u = np.clip((np.arange(W, dtype=np.float32) - x0) / max(x1 - x0, 1), 0, 1)[None, :]
    out = img.copy()
    # vecchio: sbiadito, ingiallito, un po' più scuro, con le macchie dell'età
    eta = np.clip((u - 0.3) / 0.45, 0, 1)
    luce = img[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32)
    seppia = luce[..., None] * np.array((1.0, 0.86, 0.66), np.float32) * 0.85
    out[..., :3] = img[..., :3] * (1 - eta[..., None]) + seppia * eta[..., None]
    g = max(1, int(round(W / 400)))
    grana = np.repeat(np.repeat(rng.random(((H + g - 1) // g, (W + g - 1) // g)), g, axis=0), g, axis=1)[:H, :W]
    out[..., :3] *= (1 - 0.25 * eta * (grana > 0.93))[..., None]
    # polvere: la sagoma si sbriciola (a granelli) sempre di più verso la coda
    sbriciola = np.clip((u - 0.66) / 0.3, 0, 1)
    via = (grana < sbriciola ** 0.8 * 1.05) & (img[..., 3] > 0.05)
    out[..., 3] *= ~via
    # i granelli tolti volano via: a destra e un poco in su, piccoli, color polvere, sempre più tenui
    ys, xs = np.nonzero(via)
    if len(xs):
        scelti = rng.choice(len(xs), size=min(len(xs), 2600), replace=False)
        ys, xs = ys[scelti], xs[scelti]
        dist = rng.exponential(W * 0.05, len(xs))
        nx = (xs + dist + rng.normal(0, W * 0.006, len(xs))).astype(int)
        ny = (ys - dist * rng.uniform(0.05, 0.35, len(xs)) + rng.normal(0, H * 0.012, len(xs))).astype(int)
        ok = (nx >= 0) & (nx < W - g) & (ny >= 0) & (ny < H - g)
        tono = rng.uniform(0.45, 0.8, len(xs))[:, None] * np.array((0.78, 0.72, 0.62), np.float32)
        op = np.clip(1.0 - dist / (W * 0.16), 0.0, 1.0) * 0.85
        for i in np.nonzero(ok)[0]:
            blk = out[ny[i]:ny[i] + g, nx[i]:nx[i] + g]
            blk[..., :3] = blk[..., :3] * (1 - op[i]) * blk[..., 3:4] + tono[i] * op[i]
            blk[..., :3] /= np.maximum(blk[..., 3:4] * (1 - op[i]) + op[i], 1e-5)
            blk[..., 3] = blk[..., 3] + op[i] * (1 - blk[..., 3])
    # l'avanti veloce: due righe chiare e sfrangiate che attraversano il pesce
    for _ in range(2):
        y = int(rng.uniform(y0 + 0.2 * (y1 - y0), y1 - 0.2 * (y1 - y0)))
        h = max(1, int(H * 0.008))
        riga = out[y:y + h]
        riga[..., :3] = riga[..., :3] * 0.5 + rng.random(riga.shape[:2])[..., None] * 0.6
    return np.clip(out, 0, 1)


SPECIE['occhialone_veloce'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.03, 0.025), (0.07, 0.068), (0.13, 0.108), (0.22, 0.136), (0.36, 0.146), (0.5, 0.138), (0.68, 0.098),
             (0.84, 0.058), (0.95, 0.042), (1, 0.04)],
        bot=[(0, -0.036), (0.04, -0.07), (0.12, -0.104), (0.25, -0.128), (0.4, -0.133), (0.56, -0.118), (0.72, -0.084),
             (0.88, -0.05), (1, -0.04)],
        w=[(0, 0.008), (0.07, 0.034), (0.22, 0.052), (0.42, 0.055), (0.68, 0.04), (0.88, 0.02), (1, 0.014)],
        eye_t=0.115, eye_z=0.038, eye_r=0.042, mouth_t=0.055, mouth_z0=-0.03, mouth_z1=-0.04, gill_t=0.27,
        fins=[Fin('dorsal', 0.3, 0.84, DORSALE_LUNGA, 0.1, 22, spiny=True),
              Fin('anal', 0.62, 0.84, [(0, 0), (0.12, 0.9), (0.6, 0.62), (0.95, 0.5), (1, 0.05)], 0.08, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.3), 0.25, 20),
              Fin('pectoral', 0.3, 0.32, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.18, 12),
              Fin('pelvic', 0.35, 0.37, PELVICA, 0.09, 7, spiny=True)]),
    aspetto=Look(back=(0.42, 0.24, 0.24), flank=(0.68, 0.55, 0.53), belly=(0.82, 0.75, 0.72), fin=(0.7, 0.38, 0.33),
                 iris=(0.75, 0.68, 0.55), iris_dark=(0.15, 0.1, 0.08), metal=0.55, irid=0.35, linea_v=(0.62, -0.42),
                 disegni=[Disegno('macchia', colore=(0.02, 0.015, 0.015), forza=0.95, u=0.275, v=0.52, r=0.022)]),
    ritocco=_avanti_veloce,
    famiglia='glitch', piano='fusiforme',
    ritratto=Ritratto(riquadro=(0.7, 0.64), centro=(0.44, 0.47)),
    opzioni=dict(seed=101))


# ── Pesce Volante in Pausa (pesce volante, Cheilopogon heterurus) — PROVA DEL PIANO 'pettorali': forma normale,
#    ancora da trasformare nella famiglia (il fermo immagine) ──
# Le pettorali enormi aperte come ali (dir: fuori e indietro; su: la corda lungo il corpo) e le pelviche
# grandi; la coda con il lobo di sotto più lungo. Il ritratto del piano gira il dorso verso la camera.
SPECIE['pesce_volante_in_pausa'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.025), (0.08, 0.05), (0.18, 0.068), (0.35, 0.074), (0.55, 0.066), (0.75, 0.045), (0.9, 0.027),
             (1, 0.022)],
        bot=[(0, -0.022), (0.04, -0.045), (0.12, -0.065), (0.3, -0.075), (0.5, -0.07), (0.7, -0.05), (0.9, -0.026), (1, -0.022)],
        w=[(0, 0.008), (0.06, 0.035), (0.2, 0.055), (0.5, 0.05), (0.8, 0.026), (1, 0.014)],
        eye_t=0.085, eye_z=0.016, eye_r=0.022, mouth_t=0.04, mouth_z0=-0.005, mouth_z1=-0.012, gill_t=0.19,
        fins=[Fin('pectoral', 0.2, 0.23, PETTORALE_ALA, 0.6, 16, z=0.35, dir=(0.5, 0.85, 0.12), su=(1.0, 0.0, 0.0)),
              Fin('pelvic', 0.48, 0.5, PETTORALE_ALA, 0.3, 10, z=-0.7, dir=(0.6, 0.75, -0.1), su=(1.0, 0.0, 0.0)),
              Fin('dorsal', 0.66, 0.8, [(0, 0), (0.15, 0.9), (0.5, 1.0), (0.9, 0.7), (1, 0.05)], 0.05, 12),
              Fin('anal', 0.7, 0.8, [(0, 0), (0.15, 0.9), (0.5, 0.9), (1, 0.05)], 0.04, 10),
              Fin('caudal', 1.0, 1.0, [(0.0, 1.0), (0.55, 1.12), (0.9, 1.45), (0.3, 0.0), (1.3, -2.0), (0.6, -1.12), (0.0, -1.0)],
                  0.24, 18)]),
    aspetto=Look(back=(0.04, 0.09, 0.2), flank=(0.48, 0.53, 0.58), belly=(0.7, 0.72, 0.74), fin=(0.3, 0.34, 0.4),
                 iris=(0.5, 0.52, 0.5), iris_dark=(0.06, 0.06, 0.07), metal=0.7, irid=0.5),
    famiglia='normale', piano='pettorali')
