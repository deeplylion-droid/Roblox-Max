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

from .base import (DORSALE_BASSA, DORSALE_LUNGA, PELVICA, PETTORALE, PETTORALE_ALA, PETTORALE_TONDA, RITRATTO_PROTOTIPI,
                   Disco, Disegno, Filamento, Fin, Look, Ritratto, Shape, Specie, Spine, coda_appuntita, coda_forcuta,
                   coda_tonda, coda_tronca)

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


def _neve(img, rng, k, chiara=0.0):
    """Neve televisiva in bianco e nero dentro la sagoma (aiuto dei ritocchi): granelli larghi il doppio che alti,
    righe che sfrigolano; k = quanta (0..1), chiara = quanto la neve prende la luce del pesce sotto."""
    H, W = img.shape[:2]
    g = max(1, int(round(W / 800)))
    n = rng.random(((H + g - 1) // g, (W + 2 * g - 1) // (2 * g))).astype(np.float32)
    n = np.repeat(np.repeat(n, g, axis=0), 2 * g, axis=1)[:H, :W]
    riga = np.repeat(rng.normal(0, 0.12, (H + g - 1) // g), g)[:H].astype(np.float32)
    riga += np.repeat((rng.random((H + g - 1) // g) < 0.04) * 0.35, g)[:H].astype(np.float32)
    n = np.clip(n * 1.1 - 0.05 + riga[:, None], 0, 1)
    luce = img[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32)
    neve = np.clip((n - 0.5) * 0.9 + luce * 1.1 * chiara + (1 - chiara) * 0.5, 0, 1)
    a = k * img[..., 3]
    out = img.copy()
    out[..., :3] = img[..., :3] * (1 - a[..., None]) + neve[..., None] * a[..., None]
    return out


def _proietta(c, punti):
    """Punti nelle coordinate del pesce dritto (N, 3) → pixel dell'immagine finita (x da sinistra, y dall'alto),
    con la posa e l'inquadratura del ritratto (quelle del corpo, c.obs[0]). Non vale per i pesci con la piega."""
    sc = c.P.bpy.context.scene
    W, H = sc.render.resolution_x, sc.render.resolution_y
    M = np.array(c.obs[0].matrix_world, np.float32)
    Q = np.asarray(punti, np.float32).reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    x, y, _ = c.P.proietta(Q, sc.camera, W, H)
    return x * W, y * H


def _occhio_img(c):
    """L'occhio verso la camera sull'immagine: centro (x, y) e raggio, in pixel."""
    centro, r, _ = c.body.occhi_lista()[0]
    xs, ys = _proietta(c, [centro, centro + np.array((0.0, 0.0, r), np.float32)])
    return float(xs[0]), float(ys[0]), float(np.hypot(xs[1] - xs[0], ys[1] - ys[0]))


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
    aspetto=Look(back=(0.68, 0.13, 0.1), flank=(0.84, 0.32, 0.26), belly=(0.88, 0.66, 0.6), fin=(0.78, 0.46, 0.36),
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
    # i fotogrammi di prima: due copie spostate a destra (davanti alla testa), ognuna in tre o quattro lastre
    # orizzontali che scattano di lato ciascuna per conto suo, sempre più tenui
    scie = np.zeros_like(img)
    for k, op in ((2, 0.2), (1, 0.42)):
        copia = _sposta(img, W * 0.075 * k, 0)
        tagli = np.sort(rng.uniform(y0, y1, 3).astype(int))
        for ya, yb in zip([0, *tagli], [*tagli, H]):
            copia[ya:yb] = _sposta(copia[ya:yb], rng.normal(0, W * 0.012), 0)
        scie = _sopra(_velato(copia, op), scie)
    out = _sopra(img, scie)
    # le righe stirate in avanti: il colore dell'ultimo pixel del pesce verso la testa corre a destra e sfuma
    for _ in range(5):
        h = max(1, int(H * rng.uniform(0.003, 0.008)))
        y = int(rng.uniform(y0 + 0.2 * (y1 - y0), y1 - 0.2 * (y1 - y0)))
        lung = int(W * rng.uniform(0.08, 0.2))
        for yy in range(y, min(H, y + h)):
            dentro = np.nonzero(img[yy, :, 3] > 0.5)[0]
            if len(dentro) == 0:
                continue
            x = int(dentro.max())
            n = min(lung, W - 1 - x)
            if n < 2:
                continue
            f = (np.linspace(1, 0, n) ** 1.6 * 0.75)[:, None]
            seg = out[yy, x + 1:x + 1 + n]
            col = img[yy, x - 1, :3] * 1.1
            seg[:, :3] = seg[:, :3] * (1 - f) + col * f
            seg[:, 3:4] = np.maximum(seg[:, 3:4], f)
    # le barre di disturbo del riavvolgimento, a metà del corpo: la fascia scorre di lato ed è mezza neve
    for q in (0.42, 0.68):
        h = max(2, int(H * 0.012))
        y = int(y0 + q * (y1 - y0))
        fascia = _sposta(out[y:y + h], -W * rng.uniform(0.02, 0.04), 0)
        neve = rng.random(fascia.shape[:2]).astype(np.float32)[..., None]
        fascia[..., :3] = fascia[..., :3] * 0.55 + neve * 0.45
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
    aspetto=Look(back=(0.05, 0.24, 0.24), flank=(0.36, 0.39, 0.33), belly=(0.66, 0.66, 0.62), fin=(0.12, 0.14, 0.12),
                 iris=(0.6, 0.6, 0.52), iris_dark=(0.1, 0.1, 0.1), metal=0.45, irid=0.5,
                 disegni=[Disegno('barre', colore=(0.008, 0.025, 0.03), forza=0.97, n=7, v0=0.05, onda=1.2),
                          Disegno('macchie', colore=(0.2, 0.22, 0.24), forza=0.8, scala=55, r=0.22, u0=0.12, u1=0.85,
                                  v0=-0.85, v1=-0.12, seme=2)]),
    ritocco=_riavvolto,
    famiglia='glitch', piano='fusiforme',
    ritratto=Ritratto(yaw=168.0, pitch=-4.0, riquadro=(0.7, 0.62), centro=(0.4, 0.47)),
    opzioni=dict(seed=34))


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
    L = max(4, int(W * 0.07))
    pesi = np.exp(-np.arange(L + 1) / (L * 0.45)).astype(np.float32)
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
        acc_arc += _gira_tinta(iq * 2.4 + np.array((0.12, 0.0), np.float32), 300.0 * i / L) * sa[..., None]
    tot = np.maximum(acc_a, 1e-5)
    a_s = acc_a / pesi.sum()
    iq_s = acc_iq / tot[..., None]
    arc = acc_arc / tot[..., None]
    y_s = acc_y / tot
    out = img.copy()
    # dentro: la luce di prima, la crominanza sbavata (e un velo d'arcobaleno)
    dentro = np.concatenate([yiq[..., :1], iq_s * 0.75 + yiq[..., 1:] * 0.35 + arc * 0.12], axis=2) @ _RGB.T
    out[..., :3] = img[..., :3] * (1 - a[..., None]) + dentro * a[..., None]
    # fuori (dove la sbavatura supera la sagoma): l'arcobaleno, quasi pieno vicino al pesce
    fuori = np.clip((a_s - a) * 1.5, 0, 0.92)
    scia = np.concatenate([y_s[..., None] * 0.8 + 0.12, arc], axis=2) @ _RGB.T
    nuovo_a = a + fuori * (1 - a)
    somma = out[..., :3] * a[..., None] + scia * fuori[..., None] * (1 - a[..., None])
    out[..., :3] = somma / np.maximum(nuovo_a, 1e-5)[..., None]
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
                          Disegno('macchia', colore=(0.01, 0.015, 0.03), forza=0.95, u=0.255, v=0.0, r=0.016,
                                  allungamento=0.75)]),
    ritocco=_sbavata,
    famiglia='glitch', piano='fusiforme',
    ritratto=Ritratto(riquadro=(0.74, 0.66), centro=(0.46, 0.46)),
    opzioni=dict(seed=44, saturazione=2.1))


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
    rada = np.clip(rn / 0.8, 0, 1) ** 1.4
    raggio = cel * 0.5 * np.sqrt(np.clip(0.6 + lum * 2.0, 0, 1.2)) * np.clip(cop * 2.5, 0, 1) ** 0.5 * (0.4 + 0.6 * rada)
    raggio *= rng.random((nh, nw)) < 0.35 + 0.75 * rada           # al centro ne mancano
    # i puntini, con il bordo morbido di mezzo pixel
    yy, xx = np.mgrid[0:nh * cel, 0:nw * cel].astype(np.float32)
    dist = np.hypot(yy % cel - cel / 2 + 0.5, xx % cel - cel / 2 + 0.5)
    r_pix = np.repeat(np.repeat(raggio, cel, axis=0), cel, axis=1)
    alfa = np.clip(r_pix - dist + 0.5, 0, 1)
    # i puntini coprono meno della cella: più chiari, perché il pesce non si spenga
    col_pix = np.repeat(np.repeat(np.clip(col * 1.9 + 0.02, 0, 1), cel, axis=0), cel, axis=1)
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
    """ritocco: quadretti di ~1/76 della larghezza, ciascuno del colore medio (azzurro dove c'era un puntino
    azzurro); pieni o vuoti (gli spigoli); qualcuno sparisce (più spesso sul bordo), qualcuno scivola di una o
    due caselle; l'occhio da videogioco, nero col riflesso; la griglia appena scura e le righe sopra."""
    rng = np.random.default_rng(62)
    H, W = img.shape[:2]
    q = max(5, int(round(W / 76)))
    nh, nw = (H + q - 1) // q, (W + q - 1) // q
    pad = np.zeros((nh * q, nw * q, 4), np.float32)
    pad[:H, :W] = img
    b = pad.reshape(nh, q, nw, q, 4)
    cop = b[..., 3].mean(axis=(1, 3))
    col = (b[..., :3] * b[..., 3:4]).sum(axis=(1, 3)) / np.maximum(b[..., 3].sum(axis=(1, 3)), 1e-5)[..., None]
    # i puntini azzurri non si perdono nella media: il quadretto che ne contiene uno diventa azzurro
    blu = b[..., 2] - b[..., 0]
    i_blu = blu.reshape(nh, nw, q * q).argmax(axis=2)
    piu_blu = b.transpose(0, 2, 1, 3, 4).reshape(nh, nw, q * q, 4)[np.arange(nh)[:, None], np.arange(nw)[None, :], i_blu]
    from scipy.ndimage import binary_erosion
    azzurro = (blu.max(axis=(1, 3)) > 0.12) & binary_erosion(cop > 0.9, iterations=1)    # non sul bordo (le frange)
    col[azzurro] = np.clip(piu_blu[azzurro, :3] * 1.25, 0, 1)
    pieno = cop > 0.42
    # i quadratini in meno: più spesso vicino al bordo della sagoma, qualcuno anche in mezzo
    bordo = pieno & ~binary_erosion(pieno, iterations=2)
    via = pieno & (rng.random((nh, nw)) < np.where(bordo, 0.12, 0.03))
    pieno &= ~via
    alfa = pieno.astype(np.float32)
    # i colori del rosa fragola, appena più accesi (la media dei quadretti li spegne)
    g = (col @ np.array((0.299, 0.587, 0.114), np.float32))[..., None]
    col = np.clip(g + (col - g) * 1.6, 0, 1)
    # qualcuno fuori posto: un quadretto copiato una casella più in là
    ys, xs = np.nonzero(pieno)
    for i in rng.choice(len(ys), size=min(6, len(ys)), replace=False):
        y, x = ys[i], min(nw - 1, xs[i] + int(rng.choice((-2, -1, 1, 2))))
        col[y, x], alfa[y, x] = col[ys[i], xs[i]], 1.0
    # l'occhio da videogioco: i quadretti dell'occhio neri, uno chiaro per il riflesso (sempre pieni)
    ex, ey, r_occhio = _occhio_img(c)
    for y in range(int((ey - r_occhio) // q), int((ey + r_occhio) // q) + 1):
        for x in range(int((ex - r_occhio) // q), int((ex + r_occhio) // q) + 1):
            if 0 <= y < nh and 0 <= x < nw:
                col[y, x], alfa[y, x] = (0.04, 0.03, 0.03), 1.0
    yo, xo = int((ey - q * 0.4) // q), int((ex - q * 0.4) // q)
    if 0 <= yo < nh and 0 <= xo < nw:
        col[yo, xo] = (0.92, 0.88, 0.8)
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
                 disegni=[Disegno('macchie', colore=(0.3, 0.62, 1.0), forza=0.95, scala=48, r=0.2, u0=0.12, u1=0.85, v0=0.1,
                                  seme=3)]),
    ritocco=_pixelato,
    famiglia='glitch', piano='fusiforme',
    opzioni=dict(seed=63, doppio=0.02, bande=5, blocchi=0, righe=0.94))


# ── Menola Neve (menola, Spicara maena) ──
# Come lo zerro ma più alta: muso appuntito con la bocca protrattile, occhio grande, la dorsale lunga
# continua, coda forcuta; grigio-azzurro argentato, e la macchia scura rettangolare sul fianco.
# Il glitch: «coperta di neve bianca e nera che sfrigola. Se avvicini l'orecchio, sotto la neve senti un canale
# lontano» → neve televisiva dentro la sagoma (ritocco), a granelli appena allungati come quelli del
# televisore, con le righe più chiare e più scure; sotto, il pesce si vede ancora, come il canale lontano.
def _neve_tv(img, c):
    """ritocco: neve in bianco e nero a metà dentro la sagoma, che prende tutta la luce del pesce sotto (il canale
    lontano): si vedono ancora la sagoma, l'occhio e la macchia."""
    return _neve(img, np.random.default_rng(72), 0.5, chiara=1.0)


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
# i fotogrammi di prima restano dietro e sotto, a passi uguali in diagonale, sempre più tenui e con le righe
# mancanti; uno manca (il salto, ritocco). Il pesce vero è l'ultimo, il più vicino al bordo di sopra (il
# bordo del secchio), e l'inquadratura lo mette in alto a sinistra.
def _a_scatti(img, c):
    """ritocco: due fotogrammi di prima (quello appena prima e il terzo: il secondo è saltato), spostati a
    destra e in giù a passi uguali, con fasce di righe che mancano, di più nel vecchio; sopra il pesce vero."""
    rng = np.random.default_rng(82)
    H, W = img.shape[:2]
    dietro = np.zeros_like(img)
    passi = [(1, 0.5), (3, 0.24)]                     # (quanti fotogrammi fa, opacità): il secondo è saltato
    for k, op in reversed(passi):
        copia = _sposta(img, W * 0.075 * k, H * 0.11 * k)
        # le righe che mancano: fasce sottili vuote, sempre di più nei fotogrammi vecchi
        y = 0
        while y < H:
            h = max(1, int(H * rng.uniform(0.006, 0.02)))
            if rng.random() < 0.15 * k:
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
    aspetto=Look(back=(0.62, 0.26, 0.2), flank=(0.88, 0.5, 0.38), belly=(0.9, 0.7, 0.6), fin=(0.8, 0.46, 0.38),
                 iris=(0.85, 0.55, 0.3), iris_dark=(0.35, 0.12, 0.06), metal=0.3, irid=0.65, squame=0.7,
                 disegni=[Disegno('bande', colore=(0.28, 0.45, 0.85), forza=0.85, n=5, u0=0.0, u1=0.13, larghezza=0.22,
                                  inclinazione=0.02, v0=-0.85, v1=0.95)]),
    ritocco=_a_scatti,
    famiglia='glitch', piano='alto',
    ritratto=Ritratto(riquadro=(0.54, 0.4), centro=(0.36, 0.3)),
    opzioni=dict(seed=87, doppio=0.0))


# ── Re di Triglie a Righe (re di triglie, Apogon imberbis) ──
# Piccolo e robusto, la testa e gli occhi grandissimi, la bocca larga e obliqua; due dorsali separate, l'anale
# sotto la seconda, la coda appena forcuta; rosso-arancio, con il punto scuro sul peduncolo.
# Il glitch: «fatto di righe orizzontali, una sì e una no. Nelle righe che mancano c'è un altro pesce, che non
# riesci mai a vedere bene» → interlacciato (ritocco): nelle righe pari il re di triglie, nelle dispari un altro
# pesce, pallido e sfocato, più lungo e girato dall'altra parte, con un occhio che riflette.
def _altro_pesce(img, c):
    """ritocco: righe alte mezzo centesimo dell'immagine, una sì e una no; nelle dispari l'altro pesce, fatto
    dalla sagoma di questo girata, allungata, schiacciata, grigio-azzurra e sfocata, con l'occhio che riflette."""
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # l'altro pesce: il punto (sx, sy) di questo finisce in (cx + D − (sx − cx)·S, cy − E + (sy − cy)·K): girato a
    # specchio, S volte più lungo, K volte più basso, appena spostato; per ogni pixel si prende il punto da cui viene
    S, K, D, E = 1.14, 0.74, W * 0.02, H * 0.075
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sx = np.clip(cx - (xx - cx - D) / S, 0, W - 1).astype(int)
    sy = np.clip(cy + (yy - cy + E) / K, 0, H - 1).astype(int)
    altro = img[sy, sx].copy()
    luce = altro[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32)
    altro[..., :3] = luce[..., None] * np.array((0.6, 0.78, 0.8), np.float32) + 0.05
    altro = _sfoca(altro, W * 0.0035)
    altro[..., 3] *= 0.95
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
# sbiadisce e ingiallisce), la coda si sbriciola in polvere che vola via; una riga dell'avanti veloce.
def _avanti_veloce(img, c):
    """ritocco: lungo la sagoma (u = 0 al muso, 1 in punta alla coda) i colori invecchiano da u 0.25 a 0.7; da
    u 0.7 la sagoma si sbriciola a zolle e granelli, e i granelli tolti volano via a destra e in su, sempre più
    tenui; una riga dell'avanti veloce."""
    rng = np.random.default_rng(102)
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    u = np.clip((np.arange(W, dtype=np.float32) - x0) / max(x1 - x0, 1), 0, 1)[None, :]
    out = img.copy()
    # vecchio: sbiadito, ingiallito, un po' più scuro, con le macchie dell'età
    eta = np.clip((u - 0.25) / 0.45, 0, 1) ** 0.8
    luce = img[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32)
    seppia = luce[..., None] * np.array((1.0, 0.8, 0.52), np.float32) * 0.8
    out[..., :3] = img[..., :3] * (1 - eta[..., None]) + seppia * eta[..., None]
    g = max(1, int(round(W / 400)))
    grana = np.repeat(np.repeat(rng.random(((H + g - 1) // g, (W + g - 1) // g)), g, axis=0), g, axis=1)[:H, :W]
    out[..., :3] *= (1 - 0.35 * eta * (grana > 0.9))[..., None]          # le macchie dell'età
    # polvere: la sagoma si sbriciola sempre di più verso la coda, a zolle (rumore grosso) e a granelli
    from scipy.ndimage import zoom
    zb = max(4, int(round(W / 66)))
    zolle = zoom(rng.random((H // zb + 2, W // zb + 2)).astype(np.float32), zb, order=1)[:H, :W]
    sbriciola = np.clip((u - 0.7) / 0.3, 0, 1)
    via = (zolle * 0.65 + grana * 0.35 < sbriciola ** 1.1 * 1.05) & (img[..., 3] > 0.05)
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
    # l'avanti veloce: una riga chiara e sfrangiata che attraversa il pesce
    y = int(y0 + 0.62 * (y1 - y0))
    h = max(1, int(H * 0.007))
    riga = out[y:y + h]
    riga[..., :3] = riga[..., :3] * 0.6 + rng.random(riga.shape[:2])[..., None] * 0.45
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


# ── Balestra Sfocata (pesce balestra, Balistes capriscus) ──
# Il corpo alto a rombo, compresso; il muso lungo con la boccuccia in punta (labbra grosse, i denti a scalpello),
# gli occhi alti e arretrati; la prima dorsale con la spina grossa a grilletto (extra), la seconda dorsale e
# l'anale lunghe e opposte, alte davanti; la coda a lira con le punte lunghe; grigio-oliva, pelle a placche.
# Il glitch: «sfocato… si mette a fuoco un attimo solo: quando morde» → tutto sfocato tranne la bocca che morde
# (aperta, con i denti), con gli angoli della messa a fuoco della videocamera attorno (ritocco).
def _denti_balestra(c):
    """I denti a scalpello nella boccuccia socchiusa (aiuto comune: denti_mascelle, corti, bianchi) e la spina a
    grilletto: un cono grosso e dritto, del colore delle pinne, sul primo raggio della prima dorsale."""
    P, sh = c.P, c.forma
    bianchi = P.materiale('DentiBalestra', (0.9, 0.86, 0.74), rough=0.3, coat=0.6, sss=0.2)
    c.obs += P.denti_mascelle(c.body, n=4, lunghezza=0.0075, apertura=sh.bocca_aperta, mat=bianchi, nome='DenteBalestra')
    t = 0.293
    base = np.array((t, 0.0, float(c.body.top(np.array([t], np.float32))[0]) - 0.006), np.float32)
    punta = base + np.array((0.045, 0.0, 0.13), np.float32)
    f, lo, hi = P.campo_coni([base], [punta], [0.0085], [0.0022])
    mat = P.materiale('SpinaBalestra', tuple(x * 0.8 for x in c.aspetto.fin), rough=0.45, coat=0.4)
    c.obs.append(P.oggetto_sdf('SpinaGrilletto', f, lo, hi, mat, res=0.0007))


def _a_fuoco_quando_morde(img, c):
    """ritocco: la sfocatura su tutto, tranne un tondo attorno alla bocca (proiettata dalla scena), e i quattro
    angoli bianchi della messa a fuoco attorno al morso."""
    H, W = img.shape[:2]
    sh = c.forma
    (bx,), (by,) = _proietta(c, [(0.018, 0.0, sh.mouth_z1)])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = W * 0.05
    nitido = np.clip(1.3 - np.hypot(xx - bx, yy - by) / r, 0, 1)[..., None] ** 1.5
    sf = _sfoca(img, W * 0.0068)
    out = sf * (1 - nitido) + img * nitido
    # gli angoli della messa a fuoco: quattro «L» sottili attorno alla bocca
    lato, gamba, sp = W * 0.05, W * 0.016, max(1, int(round(W / 500)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = int(bx + sx * lato), int(by + sy * lato * 0.8)
            xa, xb = sorted((cx, int(cx - sx * gamba)))
            ya, yb = sorted((cy, int(cy - sy * gamba)))
            for (y_a, y_b, x_a, x_b) in ((cy - sp // 2, cy + sp - sp // 2, xa, xb), (ya, yb, cx - sp // 2, cx + sp - sp // 2)):
                y_a, y_b, x_a, x_b = max(0, y_a), min(H, y_b), max(0, x_a), min(W, x_b)
                out[y_a:y_b, x_a:x_b, :3] = (0.92, 0.94, 0.9)
                out[y_a:y_b, x_a:x_b, 3] = 0.85
    return out


SPECIE['balestra_sfocata'] = Specie(
    forma=Shape(
        top=[(0, -0.026), (0.03, -0.002), (0.08, 0.042), (0.14, 0.088), (0.2, 0.128), (0.27, 0.163), (0.33, 0.18), (0.42, 0.184),
             (0.52, 0.168), (0.62, 0.138), (0.72, 0.104), (0.82, 0.07), (0.92, 0.046), (1, 0.04)],
        bot=[(0, -0.04), (0.03, -0.06), (0.08, -0.09), (0.15, -0.13), (0.24, -0.172), (0.33, -0.2), (0.4, -0.205), (0.5, -0.186),
             (0.6, -0.15), (0.7, -0.11), (0.8, -0.075), (0.9, -0.05), (1, -0.04)],
        w=[(0, 0.009), (0.05, 0.026), (0.15, 0.045), (0.3, 0.055), (0.5, 0.05), (0.7, 0.035), (0.9, 0.02), (1, 0.016)],
        eye_t=0.235, eye_z=0.112, eye_r=0.025, mouth_t=0.045, mouth_z0=-0.03, mouth_z1=-0.035, bocca_aperta=24.0,
        branchie='nessuna',
        fins=[Fin('dorsal', 0.29, 0.4, [(0, 0), (0.06, 1.0), (0.25, 0.62), (0.5, 0.4), (0.75, 0.22), (1, 0.05)], 0.13, 10,
                  spiny=True),
              Fin('dorsal', 0.5, 0.82, [(0, 0), (0.06, 1.0), (0.18, 0.85), (0.45, 0.5), (0.8, 0.38), (1, 0.1)], 0.12, 30),
              Fin('anal', 0.5, 0.82, [(0, 0), (0.06, 1.0), (0.18, 0.85), (0.45, 0.5), (0.8, 0.38), (1, 0.1)], 0.11, 28),
              Fin('caudal', 1.0, 1.0, [(0.0, 1.0), (0.45, 1.4), (1.15, 2.6), (0.7, 1.3), (0.55, 0.0), (0.7, -1.3), (1.15, -2.6),
                                       (0.45, -1.4), (0.0, -1.0)], 0.16, 22),
              Fin('pectoral', 0.31, 0.32, PETTORALE_TONDA, 0.06, 9, z=0.05),
              Fin('pelvic', 0.38, 0.39, [(0, 0), (0.6, 0.12), (1, 0.0), (0.5, -0.05), (0, -0.05)], 0.04, 4, spiny=True)]),
    aspetto=Look(back=(0.17, 0.18, 0.14), flank=(0.32, 0.33, 0.27), belly=(0.46, 0.46, 0.4), fin=(0.24, 0.25, 0.2),
                 iris=(0.55, 0.6, 0.45), iris_dark=(0.1, 0.12, 0.08), metal=0.08, irid=0.15, squame=0.5,
                 disegni=[Disegno('reticolo', colore=(0.12, 0.12, 0.1), forza=0.45, scala=60, larghezza=0.05),
                          Disegno('bande', colore=(0.12, 0.12, 0.09), forza=0.35, n=3, u0=0.25, u1=0.85, larghezza=0.4,
                                  inclinazione=0.1, v0=0.1),
                          Disegno('punti', colore=(0.3, 0.45, 0.6), forza=0.5, scala=170, r=0.12, v0=0.2)]),
    extra=_denti_balestra, ritocco=_a_fuoco_quando_morde,
    famiglia='glitch', piano='alto',
    opzioni=dict(seed=111, bande=5, blocchi=2))


# ── Torpedine Statica (torpedine marmorata, Torpedo marmorata) ──
# Come la razza (costruita con il dorso verso la camera): il disco quasi tondo e spesso, gli occhietti con gli
# spiracoli dietro, la coda corta e carnosa con due dorsali e la caudale grande a paletta; bruna marmorizzata.
# Le dorsali e la caudale della coda sono verticali (di taglio, viste dall'alto): il ritratto inclinato le fa
# vedere, ma piastra() le taglia all'altezza del tronco; il campo le rifà intere (_lastra_razza).
# Il glitch: «fa la neve come un televisore acceso su un canale vuoto. Se la tocchi… la radio si accende» →
# neve sul disco e scintille azzurre (è una torpedine: la scarica) che scappano dal bordo (ritocco).
def _lastra_razza(c, fin):
    """Il campo di una pinna carnosa sulla coda di una razza, come piastra() di pesci.py ma con il controllo del
    riquadro nelle coordinate del telaio delle pinne: in piastra() la funzione del campo vede il riquadro già
    riportato nel mondo (lo, hi riassegnati dopo) e sulle razze taglia la pinna all'altezza del tronco."""
    P = c.P
    vb, _, da_mondo = c.body.telaio_pinne()
    roots, tips, _ = P.fin_points(vb, fin, -1)
    R, T = np.array(roots, np.float32), np.array(tips, np.float32)

    def piano(Q):
        return np.stack([Q[:, 0], Q[:, 2]], axis=1).astype(np.float32), Q[:, 1].astype(np.float32)
    radice = piano(R)[0]
    poly = np.concatenate([radice, piano(T)[0][::-1]])
    th1 = 0.0024 if c.fast else 0.0015
    th0 = max(fin.spessore, th1 * 1.5)
    tutti = np.concatenate([R, T])
    lo, hi = tutti.min(0) - th0 - 0.01, tutti.max(0) + th0 + 0.01

    def g(Pm):
        out = np.full(len(Pm), P.LONTANO, np.float32)
        Q = da_mondo(Pm)
        m = np.all((Q >= lo) & (Q <= hi), axis=1)
        if m.any():
            q2, qn = piano(Q[m])
            d2 = P._poligono_2d(q2, poly)
            th = th1 + (th0 - th1) * np.clip(1 - P._polilinea(q2, radice) / (fin.size * 0.9), 0, 1) ** 1.5
            wy = np.abs(qn) - th
            out[m] = np.minimum(np.maximum(d2, wy), 0) + np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(wy, 0) ** 2)
        return out
    return g


def _pinne_della_coda(c, f):
    """campo: le dorsali e la caudale carnose della coda, intere (vedi _lastra_razza), fuse nel corpo come le altre."""
    lastre = [_lastra_razza(c, fin) for fin in c.forma.fins if fin.carnosa and fin.kind in ('dorsal', 'caudal')]

    def g(p):
        d = f(p)
        for lastra in lastre:
            d = c.P.sdf.smin(d, lastra(p), 0.005)
        return d.astype(np.float32)
    return g


def _scintille(img, c):
    """ritocco: neve sul disco e una decina di scintille azzurre a zig-zag che partono dal bordo della sagoma e
    scappano fuori, ramificate, con l'alone (disegnate con PIL e sfocate per la luce)."""
    from PIL import Image, ImageDraw
    from scipy.ndimage import binary_erosion, gaussian_filter
    rng = np.random.default_rng(122)
    H, W = img.shape[:2]
    out = _neve(img, rng, 0.34, chiara=0.75)
    pieno = img[..., 3] > 0.5
    bordo = np.argwhere(pieno & ~binary_erosion(pieno, iterations=2))
    ys, xs = np.nonzero(pieno)
    cy, cx = ys.mean(), xs.mean()
    S = 2                                   # disegnate al doppio e rimpicciolite: bordi morbidi
    nucleo = Image.new('L', (W * S, H * S), 0)
    d = ImageDraw.Draw(nucleo)

    def scarica(x, y, ang, passi, spessore):
        punti = [(x * S, y * S)]
        for _ in range(passi):
            ang += rng.uniform(-0.75, 0.75)
            lung = W * rng.uniform(0.009, 0.017)
            nx, ny = x + np.cos(ang) * lung, y + np.sin(ang) * lung
            if not (W * 0.03 < nx < W * 0.97 and H * 0.05 < ny < H * 0.95):
                break                               # la scintilla non esce dal fotogramma
            x, y = nx, ny
            punti.append((x * S, y * S))
            if rng.random() < 0.12 and passi > 2:
                scarica(x, y, ang + rng.choice((-1, 1)) * rng.uniform(0.5, 1.1), passi // 2, max(1, spessore - 1))
        if len(punti) > 1:
            d.line(punti, fill=255, width=spessore, joint='curve')
    for i in rng.choice(len(bordo), size=14, replace=False):
        y, x = bordo[i]
        fuori = np.arctan2(y - cy, x - cx)
        scarica(float(x), float(y), fuori + rng.uniform(-0.5, 0.5), int(rng.integers(5, 9)), max(1, int(W / 380)) * S)
    core = np.asarray(nucleo.resize((W, H), Image.LANCZOS), np.float32) / 255.0
    alone = np.clip(gaussian_filter(core, W * 0.005) * 3.5, 0, 1)
    luce = core[..., None] * np.array((0.85, 0.95, 1.0), np.float32) + alone[..., None] * np.array((0.25, 0.55, 1.0), np.float32)
    a = np.clip(np.maximum(core, alone * 0.75), 0, 1)
    nuova = a + out[..., 3] * (1 - a)
    somma = np.clip(luce, 0, 1) * a[..., None] + out[..., :3] * out[..., 3:4] * (1 - a[..., None])
    out[..., :3] = somma / np.maximum(nuova, 1e-5)[..., None]
    out[..., 3] = nuova
    return out


SPECIE['torpedine_statica'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.04, 0.05), (0.12, 0.075), (0.24, 0.085), (0.36, 0.08), (0.46, 0.072), (0.55, 0.068), (0.62, 0.065),
             (0.72, 0.058), (0.82, 0.05), (0.92, 0.043), (1, 0.038)],
        bot=[(0, 0.0), (0.04, -0.05), (0.12, -0.075), (0.24, -0.085), (0.36, -0.08), (0.46, -0.072), (0.55, -0.068),
             (0.62, -0.065), (0.72, -0.058), (0.82, -0.05), (0.92, -0.043), (1, -0.038)],
        w=[(0, 0.006), (0.06, 0.026), (0.18, 0.042), (0.3, 0.044), (0.42, 0.038), (0.52, 0.032), (0.62, 0.029), (0.75, 0.025),
           (0.88, 0.02), (1, 0.016)],
        eye_t=0.1, eye_z=0.0, eye_r=0.0075,
        occhi=[(0.1, 0.035, 0.0075, -1), (0.1, -0.035, 0.0075, -1)], spiracoli=0.0065,
        bocca='nessuna', branchie='nessuna',
        # il disco quasi tondo fino a t 0.5, poi i due lobi delle pelviche; la coda tozza da 0.62 in poi
        disco=Disco(contorno=[(0, 0.0), (0.007, 0.06), (0.022, 0.12), (0.045, 0.17), (0.08, 0.215), (0.125, 0.252), (0.18, 0.275),
                              (0.245, 0.286), (0.31, 0.28), (0.37, 0.258), (0.425, 0.222), (0.47, 0.17), (0.5, 0.12), (0.53, 0.105),
                              (0.565, 0.1), (0.595, 0.075), (0.615, 0.035), (0.63, 0.0), (1.0, 0.0)],
                    spessore=[(0, 0.006), (0.05, 0.016), (0.14, 0.026), (0.27, 0.03), (0.4, 0.024), (0.5, 0.014), (0.57, 0.007),
                              (0.63, 0.002), (1.0, 0.001)]),
        fins=[Fin('dorsal', 0.64, 0.72, [(0, 0), (0.25, 0.9), (0.55, 1.0), (0.8, 0.5), (1, 0.05)], 0.055, 16, carnosa=True,
                  spessore=0.0045),
              Fin('dorsal', 0.76, 0.82, [(0, 0), (0.25, 0.9), (0.55, 1.0), (0.8, 0.5), (1, 0.05)], 0.045, 16, carnosa=True,
                  spessore=0.004),
              Fin('caudal', 1.0, 1.0, [(0, 0.6), (0.45, 1.3), (0.9, 1.7), (1.05, 0.6), (1.08, -0.6), (0.9, -1.7), (0.45, -1.3),
                                       (0, -0.6)], 0.11, 30, carnosa=True, spessore=0.0045)]),
    aspetto=Look(back=(0.085, 0.06, 0.04), flank=(0.1, 0.075, 0.05), belly=(0.8, 0.74, 0.66), fin=(0.08, 0.06, 0.04),
                 iris=(0.55, 0.5, 0.3), iris_dark=(0.1, 0.09, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.2, ruvido=0.5, tinta_pinne=0.0,
                 disegni=[Disegno('marmo', colore=(0.025, 0.018, 0.012), forza=0.8, scala=60, r=0.45),
                          Disegno('marmo', colore=(0.2, 0.15, 0.1), forza=0.55, scala=110, r=0.35),
                          Disegno('macchie', colore=(0.24, 0.18, 0.12), forza=0.6, scala=45, r=0.2, seme=4)]),
    campo=_pinne_della_coda, ritocco=_scintille,
    famiglia='glitch', piano='razza',
    ritratto=Ritratto(yaw=4.0, pitch=0.0, roll=-38.0, riquadro=(0.68, 0.56), centro=(0.5, 0.47)),
    opzioni=dict(seed=121, bande=4))


# ── Anguilla Smagnetizzata (anguilla, Anguilla anguilla) ──
# Cilindrica e lunghissima (dalla murena): la testa piccola e conica con la mascella di sotto appena più lunga,
# gli occhietti, le pettorali piccole e tonde subito dietro la testa, la dorsale che parte a un terzo, unita
# all'anale e alla coda; pelle liscia e viscida, bruno-verde sopra, giallastra sotto.
# Il glitch: «l'ha perso tutto, come un nastro lasciato al sole» → il nastro ondulato e stirato (le righe
# scorrono di lato a onde, alcune si allungano), i colori sbiaditi e ingialliti dal sole (ritocco).
def _nastro_al_sole(img, c):
    """ritocco: ogni riga scorre di lato (due onde e un tremolio) e si allunga un poco attorno al centro, come
    il nastro deformato dal caldo; poi i colori si sbiadiscono, si alzano i neri e tutto ingiallisce."""
    rng = np.random.default_rng(132)
    H, W = img.shape[:2]
    x0, x1, _, _ = _sagoma(img)
    cx = (x0 + x1) / 2
    y = np.arange(H, dtype=np.float32)
    dx = W * (0.024 * np.sin(2 * np.pi * y / (H * 0.31) + rng.uniform(0, 6.3))
              + 0.009 * np.sin(2 * np.pi * y / (H * 0.083) + rng.uniform(0, 6.3)))
    dx += np.repeat(rng.normal(0, W * 0.0025, H // 4 + 1), 4)[:H]
    stira = 1.0 + 0.09 * np.clip(np.sin(2 * np.pi * y / (H * 0.45) + 1.0), 0, 1)
    xx = np.arange(W, dtype=np.float32)[None, :]
    sx = (cx + (xx - cx - dx[:, None]) / stira[:, None]).round().astype(int)
    dentro = (sx >= 0) & (sx < W)
    out = img[np.arange(H)[:, None], np.clip(sx, 0, W - 1)].copy()
    out[~dentro] = 0
    # sbiadito dal sole: meno colore, neri più chiari, una velatura gialla
    luce = out[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32)
    rgb = luce[..., None] + (out[..., :3] - luce[..., None]) * 0.45
    out[..., :3] = (rgb * 0.82 + 0.1) * np.array((1.06, 1.0, 0.8), np.float32)
    return np.clip(out, 0, 1)


SPECIE['anguilla_smagnetizzata'] = Specie(
    forma=Shape(
        top=[(0, -0.003), (0.01, 0.006), (0.03, 0.015), (0.06, 0.022), (0.1, 0.027), (0.2, 0.031), (0.4, 0.032), (0.6, 0.03),
             (0.8, 0.024), (0.92, 0.015), (1, 0.004)],
        bot=[(0, -0.01), (0.02, -0.016), (0.05, -0.021), (0.1, -0.026), (0.25, -0.03), (0.45, -0.031), (0.65, -0.028),
             (0.82, -0.021), (0.93, -0.012), (1, -0.004)],
        w=[(0, 0.004), (0.03, 0.013), (0.08, 0.021), (0.25, 0.025), (0.5, 0.023), (0.75, 0.015), (0.9, 0.009), (1, 0.003)],
        eye_t=0.038, eye_z=0.008, eye_r=0.0062, mouth_t=0.042, mouth_z0=-0.004, mouth_z1=-0.007,
        branchie='pori', n_branchie=1, gill_t=0.105,
        fins=[Fin('dorsal', 0.33, 1.0, DORSALE_BASSA, 0.022, 120, carnosa=True, spessore=0.003),
              Fin('anal', 0.43, 1.0, DORSALE_BASSA, 0.02, 100, carnosa=True, spessore=0.003),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.9, 1.0), 0.03, 20, carnosa=True, spessore=0.0025),
              Fin('pectoral', 0.115, 0.125, PETTORALE_TONDA, 0.034, 10, z=-0.1)],
        piega=[(0, -12), (0.25, 14), (0.5, -12), (0.75, 14), (1.0, -6)]),
    aspetto=Look(back=(0.045, 0.055, 0.025), flank=(0.14, 0.14, 0.06), belly=(0.62, 0.52, 0.18), fin=(0.08, 0.08, 0.04),
                 iris=(0.7, 0.62, 0.35), iris_dark=(0.12, 0.1, 0.05), metal=0.05, irid=0.1, squame=0.0, linea_laterale=0.0,
                 lucido=0.45, ruvido=0.4, tinta_pinne=0.0),
    ritocco=_nastro_al_sole,
    famiglia='glitch', piano='anguilliforme',
    opzioni=dict(seed=131, bande=4, blocchi=1))


# ── Pappagallo in Loop (pesce pappagallo, Sparisoma cretense) ──
# Ovale robusto, la testa tonda e il becco dei denti fusi (extra, come il becco del pesce palla), le squame
# grandi (il reticolo); la femmina: grigio sul dorso, rosso vivo sui fianchi e sulla testa, la macchia scura
# all'attacco della pettorale e la macchia gialla in alto sul peduncolo.
# Il glitch: «ripete sempre gli stessi tre secondi… apre la bocca, la chiude» → due pose sovrapposte: il
# ritocco rende una seconda volta il pesce con la bocca aperta (e il becco che si apre); la testa a bocca aperta
# spunta sotto quella chiusa, e attorno alla bocca le due pose si alternano a strisce (il nastro inceppato).
def _becco_pappagallo(c):
    """Il becco: due placche di dente bianco-verdino sopra e sotto il taglio della bocca; quella di sotto si chiama
    BeccoPappagallo1 (il ritocco la gira con la mascella)."""
    P, sh = c.P, c.forma
    mat = P.materiale('BeccoPappagallo', (0.8, 0.86, 0.74), rough=0.25, coat=0.7, sss=0.3)
    for k, dz in enumerate((0.0075, -0.0075)):
        z = sh.mouth_z0 + dz
        f = P.sdf.ellipsoid((0.009, 0.0, z), (0.019, 0.025, 0.0105))
        c.obs.append(P.oggetto_sdf(f'BeccoPappagallo{k}', f, (-0.014, -0.032, z - 0.015), (0.032, 0.032, z + 0.015), mat,
                                   res=0.0006))


def _in_loop(img, c):
    """ritocco: la seconda posa. Si costruisce un altro corpo con la mascella abbassata (stessa posa e stessa
    inquadratura del primo, che si nasconde), la placca di sotto del becco gira con lei attorno alla cerniera, si
    rende di nuovo (il render del pappagallo costa il doppio) e si glitcha come la prima; la sua testa va sotto la
    prima, un poco in basso e indietro, e attorno alla bocca le due pose si alternano a strisce."""
    import os

    from mathutils import Matrix, Vector
    from PIL import Image
    P = c.P
    sc = P.bpy.context.scene
    H, W = img.shape[:2]
    corpo = c.obs[0]
    M = corpo.matrix_world.copy()
    aperto = P.build_normal(c.body, c.aspetto, 'glitch', mouth_open=40.0)
    aperto.matrix_world = M
    corpo.hide_render = True
    h, R = Vector(tuple(map(float, c.body.hinge))), Matrix([list(map(float, r)) for r in c.body.jaw_R]).to_4x4()
    placca = next(o for o in c.obs if o.name.startswith('BeccoPappagallo1'))
    prima = placca.matrix_world.copy()
    placca.matrix_world = M @ Matrix.Translation(h) @ R @ Matrix.Translation(-h)
    vecchio = sc.render.filepath
    percorso = os.path.join(P.CACHE, 'pesci', f'{c.fid}_bocca_aperta.png')
    sc.render.filepath = percorso
    P.bpy.ops.render.render(write_still=True)
    sc.render.filepath = vecchio
    corpo.hide_render, aperto.hide_render = False, True
    placca.matrix_world = prima
    seconda = np.asarray(Image.open(percorso).convert('RGBA'), np.float32) / 255.0
    os.remove(percorso)
    seconda = P.glitch_post(seconda, **{k: v for k, v in c.specie.opzioni.items() if k != 'elementi'})
    (bx,), (by,) = _proietta(c, [(0.02, 0.0, c.forma.mouth_z1)])
    ex, ey, _ = _occhio_img(c)
    # la testa della seconda posa (a bocca aperta), staccata un poco in basso e indietro, velata e più fredda: si
    # vedono due teste, una a bocca chiusa e una aperta; sfuma dietro l'occhio
    testa = np.clip((ex + W * 0.1 - np.arange(W, dtype=np.float32)) / (W * 0.05), 0, 1)[None, :]
    fredda = seconda.copy()
    fredda[..., 3] *= testa
    fredda = _sposta(fredda, -W * 0.02, H * 0.035)
    fredda[..., :3] *= np.array((0.82, 1.0, 1.15), np.float32)
    out = _sopra(img, _velato(fredda, 0.75))
    # attorno alla bocca, strisce alternate delle due pose (il nastro inceppato fra i due fotogrammi)
    h = max(2, int(H * 0.011))
    xa = int(min(W, bx + W * 0.08))
    for k, y in enumerate(range(int(by - H * 0.05), int(by + H * 0.1), h)):
        if k % 2 == 0 and 0 <= y < H:
            out[y:y + h, :xa] = seconda[y:y + h, :xa]
    return out


SPECIE['pappagallo_in_loop'] = Specie(
    forma=Shape(
        top=[(0, -0.03), (0.02, 0.0), (0.05, 0.045), (0.1, 0.09), (0.18, 0.124), (0.3, 0.143), (0.45, 0.143), (0.6, 0.124),
             (0.75, 0.09), (0.88, 0.066), (1, 0.06)],
        bot=[(0, -0.044), (0.03, -0.074), (0.1, -0.108), (0.22, -0.133), (0.38, -0.138), (0.55, -0.123), (0.7, -0.09),
             (0.85, -0.068), (1, -0.06)],
        w=[(0, 0.012), (0.06, 0.04), (0.2, 0.06), (0.4, 0.062), (0.65, 0.045), (0.85, 0.03), (1, 0.022)],
        eye_t=0.125, eye_z=0.05, eye_r=0.022, mouth_t=0.058, mouth_z0=-0.034, mouth_z1=-0.042, gill_t=0.26,
        fins=[Fin('dorsal', 0.3, 0.85, [(0, 0), (0.05, 0.8), (0.5, 0.75), (0.9, 0.8), (1, 0.1)], 0.07, 24, spiny=True),
              Fin('anal', 0.62, 0.85, [(0, 0), (0.1, 0.8), (0.6, 0.7), (1, 0.1)], 0.06, 12),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.6, 0.0, 0.85), 0.17, 16),
              Fin('pectoral', 0.27, 0.28, PETTORALE, 0.1, 10),
              Fin('pelvic', 0.32, 0.33, PELVICA, 0.07, 6)]),
    aspetto=Look(back=(0.26, 0.27, 0.29), flank=(0.75, 0.15, 0.1), belly=(0.82, 0.3, 0.22), fin=(0.62, 0.2, 0.15),
                 iris=(0.9, 0.7, 0.2), iris_dark=(0.4, 0.2, 0.05), metal=0.15, irid=0.2,
                 disegni=[Disegno('reticolo', colore=(0.3, 0.05, 0.04), forza=0.35, scala=44, larghezza=0.04),
                          Disegno('macchia', colore=(0.04, 0.03, 0.03), forza=0.9, u=0.27, v=0.05, r=0.018),
                          Disegno('macchia', colore=(0.98, 0.78, 0.08), forza=0.95, u=0.86, v=0.55, r=0.03, allungamento=1.4)]),
    extra=_becco_pappagallo, ritocco=_in_loop,
    famiglia='glitch', piano='fusiforme',
    opzioni=dict(seed=141, bande=5, blocchi=2))


# ── Leccia Senza Segnale (leccia, Lichia amia) ──
# Grande, compressa e ovale-allungata, il muso appuntito con la bocca larga; la linea laterale ondulata ben
# visibile; la prima dorsale di spine corte staccate, la seconda dorsale e l'anale falcate e opposte, coda
# forcuta profonda; dorso grigio-oliva scuro, fianchi e ventre d'argento, le punte delle pinne scure.
# Il glitch: «compare e scompare come un canale che non prende» → fasce orizzontali sparite, una di neve, altre
# che scorrono di lato (ritocco); l'occhio, la linea laterale e le punte delle pinne restano.
def _senza_segnale(img, c):
    """ritocco: fasce disegnate in frazioni dell'altezza della sagoma (pinne comprese): sparite, di neve, scorse
    di lato; lasciano intere la testa con l'occhio, la linea laterale e le punte delle pinne falcate, che dicono
    che pesce è; la fascia che passa per l'occhio resta comunque intera."""
    rng = np.random.default_rng(152)
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    _, ey, er = _occhio_img(c)
    alt = y1 - y0
    out = img.copy()
    neve = _neve(img, rng, 0.9)
    fasce = [(0.08, 0.14, 'scorre'), (0.3, 0.335, 'via'), (0.5, 0.545, 'via'), (0.575, 0.62, 'neve'), (0.65, 0.71, 'via'),
             (0.75, 0.8, 'scorre'), (0.88, 0.97, 'via')]
    for a, b, cosa in fasce:
        ya, yb = int(y0 + a * alt), int(y0 + b * alt)
        if ya - er < ey < yb + er:
            continue
        if cosa == 'via':
            out[ya:yb, :, 3] = 0
        elif cosa == 'neve':
            out[ya:yb] = neve[ya:yb]
        else:
            out[ya:yb] = _sposta(out[ya:yb], W * rng.choice((-1, 1)) * rng.uniform(0.03, 0.06), 0)
    return out


SPECIE['leccia_senza_segnale'] = Specie(
    forma=Shape(
        top=[(0, -0.015), (0.03, 0.018), (0.08, 0.056), (0.16, 0.094), (0.28, 0.124), (0.42, 0.132), (0.56, 0.12), (0.72, 0.082),
             (0.86, 0.044), (0.95, 0.028), (1, 0.025)],
        bot=[(0, -0.03), (0.04, -0.054), (0.12, -0.088), (0.26, -0.118), (0.42, -0.126), (0.58, -0.112), (0.74, -0.074),
             (0.88, -0.038), (1, -0.025)],
        w=[(0, 0.006), (0.07, 0.027), (0.22, 0.04), (0.45, 0.042), (0.7, 0.029), (0.9, 0.013), (1, 0.01)],
        eye_t=0.08, eye_z=0.024, eye_r=0.02, mouth_t=0.1, mouth_z0=-0.016, mouth_z1=-0.03, gill_t=0.22,
        fins=[Fin('dorsal', 0.28, 0.4, [(0, 0), (0.05, 0.9), (0.1, 0.12), (0.2, 0.95), (0.25, 0.12), (0.35, 1.0), (0.4, 0.12),
                                       (0.5, 0.95), (0.55, 0.12), (0.65, 0.9), (0.7, 0.12), (0.8, 0.8), (0.85, 0.1), (1, 0.05)],
                  0.032, 40, spiny=True),
              Fin('dorsal', 0.45, 0.86, [(0, 0), (0.06, 1.0), (0.14, 0.75), (0.25, 0.35), (0.6, 0.25), (1, 0.1)], 0.13, 30,
                  bordo=(0.05, 0.05, 0.05)),
              Fin('anal', 0.5, 0.86, [(0, 0), (0.06, 1.0), (0.14, 0.75), (0.25, 0.35), (0.6, 0.25), (1, 0.1)], 0.11, 26,
                  bordo=(0.05, 0.05, 0.05)),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.75, 0.2), 0.26, 20, bordo=(0.05, 0.05, 0.05)),
              Fin('pectoral', 0.22, 0.23, PETTORALE, 0.1, 10),
              Fin('pelvic', 0.27, 0.28, PELVICA, 0.06, 6)]),
    aspetto=Look(back=(0.1, 0.11, 0.1), flank=(0.5, 0.53, 0.54), belly=(0.72, 0.73, 0.72), fin=(0.14, 0.14, 0.13),
                 iris=(0.75, 0.7, 0.55), iris_dark=(0.12, 0.1, 0.08), metal=0.75, irid=0.3, linea_laterale=0.0,
                 disegni=[Disegno('linea', colore=(0.06, 0.06, 0.06), forza=0.9, v=0.25, inclinazione=-0.25, onda=0.14,
                                  larghezza=0.035, u0=0.2),
                          Disegno('ventre', colore=(0.8, 0.82, 0.84), forza=0.5, v1=-0.35)]),
    ritocco=_senza_segnale,
    famiglia='glitch', piano='fusiforme',
    opzioni=dict(seed=151, bande=4, blocchi=2))


# ── Civetta Fuori Quadro (pesce civetta, Dactylopterus volitans) ──
# Dalla gallinella (gallincubo): la testa corazzata e squadrata con la spina lunga che corre indietro sul
# fianco (filamento), il primo raggio della dorsale libero sulla nuca; le pettorali enormi a ventaglio, scure
# con i puntini e il bordo azzurri, aperte di lato; corpo bruno-rossiccio puntinato, coda appena forcuta.
# Il glitch: «non sta mai tutta nell'inquadratura: un pezzo esce sempre dal bordo. Il pezzo che manca, nel
# secchio, si muove» → l'inquadratura più grande del fotogramma lo fa uscire a destra e in alto (Ritratto), e
# vicino al bordo destro, dove esce la coda, l'immagine si strappa a fette come se il pezzo di fuori si
# muovesse (ritocco).
def _fuori_quadro(img, c):
    """ritocco: nell'ultimo quinto a destra (dove esce la coda) una fascia su due scorre di lato. Prima si toglie
    quello che il glitch di sempre (np.roll) ha fatto rientrare dal bordo sinistro: i pezzi usciti a destra (la
    testa comincia a un decimo della larghezza, lì non c'è altro)."""
    rng = np.random.default_rng(162)
    H, W = img.shape[:2]
    out = img.copy()
    out[:, :int(W * 0.06), 3] = 0
    y = 0
    while y < H:
        h = max(2, int(H * rng.uniform(0.015, 0.05)))
        if rng.random() < 0.55:
            x = int(W * 0.8)
            out[y:y + h, x:] = _sposta(out[y:y + h, x:], W * rng.uniform(-0.03, 0.05), 0)
        y += h
    return out


SPECIE['civetta_fuori_quadro'] = Specie(
    forma=Shape(
        top=[(0, -0.03), (0.012, -0.012), (0.035, 0.012), (0.07, 0.04), (0.12, 0.06), (0.2, 0.07), (0.3, 0.072), (0.45, 0.064),
             (0.6, 0.052), (0.75, 0.04), (0.9, 0.03), (1, 0.026)],
        bot=[(0, -0.045), (0.03, -0.062), (0.08, -0.072), (0.16, -0.075), (0.3, -0.07), (0.45, -0.06), (0.6, -0.048), (0.8, -0.034),
             (1, -0.026)],
        w=[(0, 0.02), (0.04, 0.042), (0.12, 0.058), (0.25, 0.055), (0.5, 0.04), (0.75, 0.025), (1, 0.014)],
        eye_t=0.09, eye_z=0.03, eye_r=0.022, mouth_t=0.05, mouth_z0=-0.046, mouth_z1=-0.052, gill_t=0.2,
        filamenti=[Filamento(t=0.17, v=0.55, lunghezza=0.17, raggio=0.0042, dir=(1.0, 0.12, -0.05), curva=(0, 0, -0.4),
                             punta=0.12),
                   Filamento(t=0.125, v=1.0, lunghezza=0.075, raggio=0.003, dir=(0.45, 0.0, 1.0), curva=(2.0, 0, 0),
                             lati='centro', punta=0.2)],
        spine=[Spine(0.03, 0.18, 0.25, 0.95, 16, lunghezza=0.006, raggio=0.003, inclinazione=0.6, seme=4)],
        fins=[Fin('pectoral', 0.2, 0.24, [(0, 0.05), (0.3, 0.5), (0.7, 0.62), (1.0, 0.4), (1.08, 0.0), (0.95, -0.35), (0.6, -0.45),
                                         (0.25, -0.3), (0, -0.08)], 0.5, 26, z=-0.05, dir=(0.55, 0.8, -0.1), su=(1.0, 0.0, 0.25),
                  colore=(0.025, 0.03, 0.045), bordo=(0.015, 0.05, 0.16), macchie=0.5, colore_macchie=(0.1, 0.4, 0.95)),
              Fin('dorsal', 0.22, 0.36, [(0, 0), (0.1, 0.9), (0.4, 0.7), (1, 0.1)], 0.06, 9, spiny=True),
              Fin('dorsal', 0.5, 0.7, [(0, 0), (0.1, 0.85), (0.6, 0.6), (1, 0.05)], 0.05, 14),
              Fin('anal', 0.55, 0.72, [(0, 0), (0.1, 0.8), (0.6, 0.55), (1, 0.05)], 0.04, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.35, 0.55), 0.17, 16),
              Fin('pelvic', 0.24, 0.25, PELVICA, 0.06, 6)]),
    aspetto=Look(back=(0.32, 0.2, 0.14), flank=(0.46, 0.32, 0.24), belly=(0.76, 0.62, 0.55), fin=(0.35, 0.25, 0.2),
                 iris=(0.8, 0.62, 0.3), iris_dark=(0.3, 0.15, 0.05), metal=0.15, irid=0.25, squame=0.8,
                 disegni=[Disegno('macchie', colore=(0.16, 0.08, 0.05), forza=0.6, scala=40, r=0.25, v0=-0.3),
                          Disegno('punti', colore=(0.85, 0.75, 0.6), forza=0.6, scala=170, r=0.12, v0=0.0),
                          Disegno('reticolo', colore=(0.18, 0.1, 0.06), forza=0.6, scala=55, larghezza=0.08, u1=0.2, v0=-0.4)]),
    ritocco=_fuori_quadro,
    famiglia='glitch', piano='pettorali',
    ritratto=Ritratto(yaw=10.0, pitch=-4.0, roll=28.0, riquadro=(1.1, 0.95), centro=(0.6, 0.42)),
    opzioni=dict(seed=161, bande=5))


# ── Pesce Volante in Pausa (pesce volante, Cheilopogon heterurus) ──
# La prova del piano 'pettorali': le pettorali enormi aperte come ali (dir: fuori e indietro; su: la corda lungo
# il corpo) e le pelviche grandi; la coda con il lobo di sotto più lungo. Il ritratto del piano gira il dorso
# verso la camera.
# Il glitch: «fermo a mezz'aria, tremolante come un fermo immagine» → il fermo immagine del videoregistratore
# (ritocco): i due semiquadri che non combaciano (le righe dispari spostate di lato: il tremolio), un quadro che
# salta appena in su, e la barra di disturbo orizzontale che attraversa il pesce.
def _fermo_immagine(img, c):
    """ritocco: righe dispari spostate di mezzo centesimo, una copia tenue un poco più in alto, e la barra di
    disturbo (righe che scorrono di lato, piene di neve) a due terzi del pesce, un poco più larga del pesce."""
    rng = np.random.default_rng(172)
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    hl = max(1, H // 200)
    dispari = (np.arange(H) // hl) % 2 == 1
    out = img.copy()
    out[dispari] = _sposta(img, W * 0.005, 0)[dispari]
    out = _sopra(_velato(_sposta(out, 0, -H * 0.012), 0.22), out)
    # la barra di disturbo del fermo immagine
    yb, hb = int(y0 + 0.62 * (y1 - y0)), max(3, int(H * 0.045))
    xa, xb = max(0, x0 - int(W * 0.05)), min(W, x1 + int(W * 0.05))
    for y in range(yb, min(H, yb + hb)):
        riga = _sposta(out[y:y + 1], rng.normal(0, W * 0.02), 0)[0]
        f = 1.0 - abs((y - yb) / hb - 0.5) * 2              # più forte in mezzo alla barra
        neve = rng.random(W).astype(np.float32)
        riga[:, :3] = riga[:, :3] * (1 - 0.6 * f) + neve[:, None] * 0.75 * f
        bianchi = (neve > 1 - 0.35 * f) & (np.arange(W) >= xa) & (np.arange(W) < xb)
        riga[bianchi, 3] = np.maximum(riga[bianchi, 3], 0.7 * neve[bianchi])
        out[y] = riga
    return out


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
    ritocco=_fermo_immagine,
    famiglia='glitch', piano='pettorali',
    opzioni=dict(seed=171, bande=4, blocchi=2))


# ── Alaccia Registrata Sopra (alaccia, Sardinella aurita) ──
# Il clupeide slanciato, quasi cilindrico: muso corto, una dorsale sola a metà, coda forcuta; dorso blu-verde,
# fianchi d'argento con la riga dorata lungo il fianco, la macchietta scura sul bordo alto dell'opercolo, il
# ventre appena carenato (gli scudetti in fila); niente linea laterale.
# Il glitch: «sotto il pesce, a tratti, si vede ancora la registrazione di prima: una festa di compleanno, le
# candeline, qualcuno che dice di guardare in camera» → la registrazione di prima (disegnata con PIL: la torta
# con le candeline accese, i coriandoli, una faccia che guarda in camera, la data della videocamera) si vede in
# alcune fasce, sotto il pesce e attraverso il pesce (ritocco).
def _festa_di_compleanno(img, c):
    """ritocco: la registrazione di prima, calda e sbiadita, in quattro fasce (le candele, la torta, la faccia, la
    data): lì il pesce si fa mezzo trasparente e sotto compare la festa, appena spostata di lato."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    rng = np.random.default_rng(182)
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    S = 2                                   # disegnata al doppio e rimpicciolita: bordi morbidi
    # la stanza: buio caldo, più chiaro attorno alla torta
    yy, xx = np.mgrid[0:H * S, 0:W * S].astype(np.float32)
    tx, ty = (cx - W * 0.04) * S, (cy + H * 0.06) * S
    luce = np.exp(-(((xx - tx) / (W * S * 0.28)) ** 2 + ((yy - ty) / (H * S * 0.45)) ** 2))
    stanza = (luce[..., None] * np.array((80, 44, 20)) + np.array((8, 6, 5))).astype(np.uint8)
    tela = Image.fromarray(stanza)
    d = ImageDraw.Draw(tela)
    # il bordo del tavolo e la torta: corpo, glassa, decorazioni
    d.rectangle([0, ty + H * S * 0.07, W * S, H * S], fill=(26, 16, 11))
    lt, ht = W * S * 0.1, H * S * 0.075
    d.rectangle([tx - lt, ty - ht * 0.2, tx + lt, ty + ht], fill=(205, 160, 150))
    d.ellipse([tx - lt, ty + ht * 0.7, tx + lt, ty + ht * 1.3], fill=(205, 160, 150))
    d.ellipse([tx - lt, ty - ht * 0.6, tx + lt, ty + ht * 0.2], fill=(245, 225, 215))
    for k in range(9):
        a = -lt * 0.9 + k * lt * 0.225
        d.ellipse([tx + a - 4 * S, ty + ht * 0.3 - 4 * S, tx + a + 4 * S, ty + ht * 0.3 + 4 * S], fill=(220, 70, 120))
    # le candeline e le fiammelle
    fiamme = []
    colori = [(240, 120, 170), (120, 170, 250), (250, 220, 90), (150, 230, 140), (240, 120, 170), (120, 170, 250)]
    for k in range(6):
        x = tx - lt * 0.7 + k * lt * 0.28
        y = ty - ht * 0.2 + (k % 2) * ht * 0.12
        d.rectangle([x - W * S * 0.0035, y - H * S * 0.075, x + W * S * 0.0035, y], fill=colori[k])
        fiamme.append((x, y - H * S * 0.075))
    tela = np.asarray(tela, np.float32) / 255.0
    for x, y in fiamme:
        r2 = ((xx - x) / (W * S * 0.004)) ** 2 + ((yy - y + H * S * 0.022) / (H * S * 0.022)) ** 2
        alone = np.exp(-(((xx - x) / (W * S * 0.022)) ** 2 + ((yy - y + H * S * 0.02) / (H * S * 0.05)) ** 2))
        tela += alone[..., None] * np.array((0.55, 0.3, 0.08), np.float32) + (r2 < 1)[..., None] * np.array((1.0, 0.92, 0.6))
    tela = Image.fromarray((np.clip(tela, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(tela)
    # i coriandoli
    for _ in range(90):
        x, y = rng.uniform(x0 - W * 0.03, x1 + W * 0.03) * S, rng.uniform(y0 - H * 0.12, y1 + H * 0.12) * S
        q = rng.uniform(2, 5) * S * W / 800
        d.rectangle([x, y, x + q, y + q * 0.6], fill=tuple(int(v) for v in rng.choice(
            [(250, 80, 120), (80, 200, 250), (250, 220, 60), (120, 240, 120), (240, 240, 240)])))
    # qualcuno che guarda in camera, a destra della torta
    fx, fy, fr = tx + W * S * 0.24, ty - H * S * 0.12, H * S * 0.11
    d.ellipse([fx - fr * 1.25, fy + fr * 0.8, fx + fr * 1.25, fy + fr * 3.2], fill=(40, 52, 80))
    d.ellipse([fx - fr * 0.78, fy - fr, fx + fr * 0.78, fy + fr], fill=(196, 140, 110))
    d.chord([fx - fr * 0.85, fy - fr * 1.15, fx + fr * 0.85, fy + fr * 0.4], 180, 360, fill=(50, 32, 20))
    for sx in (-1, 1):
        ox = fx + sx * fr * 0.32
        d.ellipse([ox - fr * 0.1, fy - fr * 0.05, ox + fr * 0.1, fy + fr * 0.15], fill=(25, 15, 12))
    d.ellipse([fx - fr * 0.22, fy + fr * 0.42, fx + fr * 0.22, fy + fr * 0.62], fill=(110, 40, 40))
    # la data della videocamera
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', int(H * S * 0.05))
    except OSError:
        font = ImageFont.load_default()
    d.text((x1 * S - W * S * 0.2, (y1 + H * 0.06) * S), '14.08.1997', fill=(255, 170, 40), font=font)
    tela = tela.filter(ImageFilter.GaussianBlur(S * W / 800 * 1.2)).resize((W, H), Image.LANCZOS)
    vecchia = np.asarray(tela, np.float32) / 255.0
    luce_v = vecchia @ np.array((0.299, 0.587, 0.114), np.float32)
    vecchia = luce_v[..., None] * 0.35 + vecchia * 0.65                 # sbiadita
    # le fasce dove si vede: le candele, la torta, la faccia, la data
    fasce = [(ty / S - H * 0.13, H * 0.075), (ty / S + H * 0.01, H * 0.06), (fy / S - H * 0.03, H * 0.07),
             (y1 + H * 0.05, H * 0.07)]
    # si vede solo dove è chiara (le fiamme, la torta, la faccia, la data): il buio della stanza resta trasparente;
    # ai lati sfuma poco oltre il pesce
    luce_v = vecchia @ np.array((0.299, 0.587, 0.114), np.float32)
    xs = np.arange(W, dtype=np.float32)
    lati = np.clip((xs - (x0 - W * 0.06)) / (W * 0.04), 0, 1) * np.clip(((x1 + W * 0.06) - xs) / (W * 0.04), 0, 1)
    alfa_v = np.clip((luce_v - 0.07) * 2.6, 0, 0.92) * lati[None, :]
    vecchia = np.concatenate([np.clip(vecchia * 1.15, 0, 1), alfa_v[..., None]], axis=2)
    out = img.copy()
    for ya, h in fasce:
        ya, yb = int(max(0, ya)), int(min(H, ya + h))
        if yb - ya < 2:
            continue
        rampa = np.clip(np.minimum(np.arange(yb - ya) + 1, yb - ya - np.arange(yb - ya)) / max(2.0, H * 0.008), 0, 1)
        sotto = _sposta(vecchia[ya:yb], W * rng.uniform(-0.015, 0.015), 0)
        sotto[..., 3] *= rampa[:, None]
        pesce = out[ya:yb].copy()
        pesce[..., 3] *= 1 - 0.45 * rampa[:, None]
        out[ya:yb] = _sopra(pesce, sotto)
    return out


SPECIE['alaccia_registrata_sopra'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.03, 0.02), (0.08, 0.044), (0.16, 0.062), (0.3, 0.072), (0.45, 0.073), (0.6, 0.064), (0.75, 0.047),
             (0.88, 0.03), (1, 0.024)],
        bot=[(0, -0.016), (0.04, -0.033), (0.1, -0.052), (0.22, -0.068), (0.4, -0.072), (0.58, -0.062), (0.72, -0.044),
             (0.86, -0.03), (1, -0.024)],
        w=[(0, 0.005), (0.06, 0.026), (0.2, 0.042), (0.45, 0.044), (0.7, 0.032), (0.9, 0.017), (1, 0.012)],
        eye_t=0.075, eye_z=0.012, eye_r=0.02, mouth_t=0.065, mouth_z0=0.0, mouth_z1=-0.015, gill_t=0.19,
        spine=[Spine(0.14, 0.62, -1.0, -1.0, 22, lunghezza=0.0045, raggio=0.003, lati='sinistro', inclinazione=0.85, fila=True)],
        fins=[Fin('dorsal', 0.42, 0.56, [(0, 0), (0.15, 0.95), (0.4, 1.0), (0.8, 0.5), (1, 0.05)], 0.08, 12),
              Fin('anal', 0.74, 0.88, [(0, 0), (0.2, 0.7), (0.7, 0.5), (1, 0.05)], 0.025, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.25), 0.22, 18),
              Fin('pectoral', 0.2, 0.21, PETTORALE, 0.08, 9, z=-0.5),
              Fin('pelvic', 0.47, 0.48, PELVICA, 0.04, 6)]),
    aspetto=Look(back=(0.04, 0.13, 0.16), flank=(0.45, 0.5, 0.52), belly=(0.75, 0.76, 0.76), fin=(0.2, 0.24, 0.26),
                 iris=(0.75, 0.72, 0.6), iris_dark=(0.1, 0.1, 0.08), metal=0.8, irid=0.5, linea_laterale=0.0,
                 disegni=[Disegno('strisce', colore=(0.95, 0.72, 0.2), forza=0.8, n=1, v0=-0.04, v1=0.22, larghezza=0.13,
                                  u0=0.18, u1=0.95),
                          Disegno('macchia', colore=(0.02, 0.03, 0.04), forza=0.9, u=0.18, v=0.45, r=0.011)]),
    ritocco=_festa_di_compleanno,
    famiglia='glitch', piano='fusiforme',
    opzioni=dict(seed=181, bande=5, blocchi=2))


# ── Cheppia Senza Audio (cheppia, Alosa fallax) ──
# Il clupeide alto e compresso: la bocca obliqua, il ventre a dente di sega (gli scudetti in fila, Spine), la
# fila di macchie scure dietro l'opercolo (la prima più grande), una dorsale a metà, coda forcuta; dorso
# blu-verde, fianchi d'argento e oro. Il corpo piegato (piega): si sta dibattendo.
# Il glitch: «si dibatte senza fare rumore: niente schizzi, niente colpi sul legno» → gli spruzzi ci sono ma
# sono fermi, muti: gocce sospese attorno alla coda e al muso (extra); il glitch di sempre è discreto.
def _gocce_ferme(c):
    """Gli spruzzi fermi: gocce d'acqua immobili sui due ventagli dello schizzo della coda (sopra e sotto) e
    qualcuna davanti al muso; ogni goccia è un cono arrotondato appena allungato lungo il suo volo, d'acqua
    trasparente e lucida (si vede dal riflesso e dal bordo chiaro)."""
    P = c.P
    rng = np.random.default_rng(9)
    A, B, R1, R2 = [], [], [], []
    for centro, n, ang0, ang1, d0, d1 in (((1.0, 0.0, 0.02), 9, 20, 80, 0.08, 0.24), ((1.0, 0.0, -0.02), 7, -75, -20, 0.07, 0.2),
                                         ((0.05, 0.0, 0.02), 5, 110, 160, 0.05, 0.13)):
        C = np.array(centro, np.float32)
        for _ in range(n):
            a = np.radians(rng.uniform(ang0, ang1))
            dist = rng.uniform(d0, d1)
            dirz = np.array((np.cos(a), 0.0, np.sin(a)), np.float32)
            p = C + dirz * dist + np.array((0.0, rng.uniform(-0.07, 0.03), 0.0), np.float32)
            r = rng.uniform(0.0055, 0.011)
            A.append(p)
            B.append(p - dirz * r * rng.uniform(0.6, 1.4))
            R1.append(r)
            R2.append(r * 0.45)
    f, lo, hi = P.campo_coni(A, B, R1, R2)
    m, g = P.material('AcquaFerma')
    g.output_material(g.principled(color=(0.88, 0.95, 1.0), rough=0.02, ior=1.33, transmission=0.92, coat=1.0, coat_rough=0.0,
                                   spec=0.9))
    c.obs.append(P.oggetto_sdf('GocceFerme', f, lo, hi, m, res=0.0009 if c.fast else 0.0006))


SPECIE['cheppia_senza_audio'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.03, 0.025), (0.08, 0.058), (0.16, 0.088), (0.3, 0.105), (0.45, 0.107), (0.6, 0.095), (0.75, 0.068),
             (0.88, 0.042), (1, 0.032)],
        bot=[(0, -0.022), (0.04, -0.05), (0.12, -0.085), (0.25, -0.114), (0.4, -0.121), (0.55, -0.108), (0.7, -0.078),
             (0.85, -0.045), (1, -0.032)],
        w=[(0, 0.005), (0.06, 0.025), (0.2, 0.038), (0.45, 0.04), (0.7, 0.028), (0.9, 0.015), (1, 0.011)],
        eye_t=0.075, eye_z=0.018, eye_r=0.02, mouth_t=0.08, mouth_z0=0.002, mouth_z1=-0.02, gill_t=0.21,
        spine=[Spine(0.1, 0.64, -1.0, -1.0, 28, lunghezza=0.0065, raggio=0.0042, lati='sinistro', inclinazione=0.8, fila=True)],
        fins=[Fin('dorsal', 0.4, 0.53, [(0, 0), (0.15, 0.95), (0.4, 1.0), (0.8, 0.5), (1, 0.05)], 0.09, 12),
              Fin('anal', 0.72, 0.88, [(0, 0), (0.2, 0.7), (0.7, 0.5), (1, 0.05)], 0.03, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.65, 0.24), 0.24, 18),
              Fin('pectoral', 0.21, 0.22, PETTORALE, 0.09, 9, z=-0.55),
              Fin('pelvic', 0.45, 0.46, PELVICA, 0.045, 6)],
        piega=[(0, 5), (0.4, -3), (0.75, 7), (1.0, 15)]),
    aspetto=Look(back=(0.05, 0.12, 0.14), flank=(0.5, 0.5, 0.44), belly=(0.76, 0.76, 0.72), fin=(0.22, 0.24, 0.24),
                 iris=(0.8, 0.72, 0.5), iris_dark=(0.15, 0.12, 0.06), metal=0.8, irid=0.45, linea_laterale=0.0,
                 disegni=[Disegno('macchia', colore=(0.03, 0.04, 0.05), forza=0.9, u=0.245, v=0.45, r=0.017),
                          Disegno('macchia', colore=(0.03, 0.04, 0.05), forza=0.85, u=0.3, v=0.5, r=0.012),
                          Disegno('macchia', colore=(0.03, 0.04, 0.05), forza=0.8, u=0.35, v=0.52, r=0.011),
                          Disegno('macchia', colore=(0.03, 0.04, 0.05), forza=0.75, u=0.4, v=0.53, r=0.01),
                          Disegno('macchia', colore=(0.03, 0.04, 0.05), forza=0.7, u=0.45, v=0.53, r=0.009),
                          Disegno('sfumatura', colore=(0.62, 0.55, 0.3), forza=0.35, v0=-0.3, v1=0.3, larghezza=0.2)]),
    extra=_gocce_ferme,
    famiglia='glitch', piano='fusiforme',
    opzioni=dict(seed=191, doppio=0.02, bande=3, separa=0.004, blocchi=1, righe=0.9))


# ── Lampuga Fuori Traccia (lampuga, Coryphaena hippurus) ──
# Il maschio: la fronte altissima e verticale, l'occhio basso vicino alla bocca, la dorsale da sopra l'occhio
# fino alla coda, l'anale lunga, la coda forcuta profonda; oro-verde con i puntini azzurri e scuri, il dorso
# blu-verde, il ventre giallo chiaro.
# Il glitch: «cambia colore in continuazione, a strisce, come una cassetta che si sta per rompere» → fasce
# orizzontali con la tinta girata, ognuna di un angolo diverso (ritocco), e in basso la fascia del tracking
# sbagliato, con le righe che tremano di lato.
def _fuori_traccia(img, c):
    """ritocco: dall'alto in basso del pesce fasce di altezza diversa; due su tre con la tinta girata (60–300°) e
    un po' più accese; vicino al ventre la fascia del tracking: righe spostate a caso e un velo di neve."""
    rng = np.random.default_rng(202)
    H, W = img.shape[:2]
    x0, x1, y0, y1 = _sagoma(img)
    out = img.copy()
    yiq = out[..., :3] @ _YIQ.T
    y = y0
    while y < y1:
        h = max(2, int(H * rng.uniform(0.025, 0.065)))
        if rng.random() < 0.55:
            yiq[y:y + h, :, 1:] = _gira_tinta(yiq[y:y + h, :, 1:] * 1.35, rng.uniform(80, 280))
            yiq[y:y + h, :, 0] *= rng.uniform(0.9, 1.15)
        y += h
    out[..., :3] = yiq @ _RGB.T
    # il tracking sbagliato: una fascia di righe che tremano e sfrigolano
    yt, ht = int(y0 + 0.78 * (y1 - y0)), max(3, int(H * 0.05))
    for yy in range(yt, min(H, yt + ht)):
        out[yy] = _sposta(out[yy:yy + 1], rng.normal(0, W * 0.012), 0)[0]
        neve = rng.random(W).astype(np.float32)
        out[yy, :, :3] = out[yy, :, :3] * 0.7 + neve[:, None] * 0.35
    return np.clip(out, 0, 1)


SPECIE['lampuga_fuori_traccia'] = Specie(
    forma=Shape(
        top=[(0, -0.03), (0.008, 0.0), (0.016, 0.05), (0.026, 0.09), (0.04, 0.114), (0.07, 0.128), (0.12, 0.132), (0.25, 0.125),
             (0.4, 0.112), (0.55, 0.093), (0.7, 0.068), (0.85, 0.044), (0.95, 0.03), (1, 0.026)],
        bot=[(0, -0.05), (0.02, -0.07), (0.08, -0.09), (0.2, -0.1), (0.35, -0.098), (0.5, -0.085), (0.65, -0.065), (0.8, -0.045),
             (0.92, -0.03), (1, -0.026)],
        w=[(0, 0.01), (0.04, 0.03), (0.15, 0.042), (0.4, 0.038), (0.7, 0.026), (0.9, 0.015), (1, 0.011)],
        eye_t=0.068, eye_z=-0.012, eye_r=0.018, mouth_t=0.07, mouth_z0=-0.04, mouth_z1=-0.05, gill_t=0.17,
        fins=[Fin('dorsal', 0.06, 0.96, [(0, 0), (0.02, 0.7), (0.06, 1.0), (0.15, 0.95), (0.4, 0.7), (0.7, 0.6), (0.9, 0.5), (1, 0.1)],
                  0.085, 60, colore=(0.06, 0.22, 0.3)),
              Fin('anal', 0.45, 0.95, [(0, 0), (0.05, 0.9), (0.2, 0.75), (0.6, 0.55), (1, 0.1)], 0.06, 30, colore=(0.35, 0.4, 0.2)),
              Fin('caudal', 1.0, 1.0, coda_forcuta(2.3, 0.1, 1.1), 0.26, 22, colore=(0.3, 0.38, 0.22)),
              Fin('pectoral', 0.16, 0.17, PETTORALE, 0.09, 9),
              Fin('pelvic', 0.17, 0.18, PELVICA, 0.07, 6)]),
    aspetto=Look(back=(0.03, 0.22, 0.2), flank=(0.55, 0.48, 0.12), belly=(0.78, 0.72, 0.4), fin=(0.1, 0.25, 0.25),
                 iris=(0.75, 0.65, 0.3), iris_dark=(0.15, 0.12, 0.05), metal=0.5, irid=0.6,
                 disegni=[Disegno('macchie', colore=(0.08, 0.3, 0.65), forza=0.8, scala=45, r=0.18, v0=-0.45, seme=6),
                          Disegno('punti', colore=(0.05, 0.08, 0.1), forza=0.6, scala=170, r=0.14, v0=-0.3)]),
    ritocco=_fuori_traccia,
    famiglia='glitch', piano='fusiforme',
    opzioni=dict(seed=201, bande=6))
