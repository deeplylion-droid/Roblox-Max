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

from .base import PETTORALE_ALA, RITRATTO_PROTOTIPI, Fin, Look, Ritratto, Shape, Specie, coda_forcuta

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
    opzioni=dict(seed=21, doppio=0.0))


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
