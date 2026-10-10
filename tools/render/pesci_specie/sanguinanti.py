"""
Sanguinanti: ferite, denti sporchi, colature (src/game/catalog.ts, docs/CATALOGO.md).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast

La funzione della famiglia (pesci.bleeding) fa i tagli dritti a lente sul fianco, la bocca aperta con i denti
sporchi e le gocce. Quello che serve in più (morsi, fori dei denti, fessure da parte a parte, il sangue che
cola dalle branchie o dagli occhi) è qui sotto negli aiuti della famiglia: lo stesso elenco di pezzi tolti
scava il campo del corpo (Specie.campo) e dipinge la carne viva sui vertici della pelle (Specie.extra, che
riscrive gli attributi 'wound' e 'blood' del corpo), così il taglio e il colore coincidono.
"""
import math

import numpy as np

from .base import (DORSALE_FALCE, DORSALE_SQUALO, DORSALE_TRIANGOLO, PELVICA, PETTORALE, PETTORALE_TONDA, PIANI,
                   RITRATTO_PROTOTIPI, Disco, DiscoOrale, Disegno, Filamento, Fin, Look, Ritratto, Rostro, Shape, Specie,
                   Spine, Ventosa, coda_appuntita, coda_eterocerca, coda_falcata, coda_forcuta, coda_tonda, coda_tronca)

F = np.float32
LONTANO = 10.0          # il valore dei campi lontano dai loro pezzi (come in pesci.py)

SPECIE = {}

# ── Barracruda (luccio di mare, Sphyraena sphyraena) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['barracruda'] = Specie(
    forma=Shape(
        top=[(0, -0.018), (0.06, 0.006), (0.15, 0.04), (0.3, 0.06), (0.5, 0.066), (0.7, 0.055), (0.88, 0.031), (1, 0.026)],
        bot=[(0, -0.024), (0.04, -0.034), (0.15, -0.05), (0.3, -0.062), (0.5, -0.064), (0.7, -0.052), (0.88, -0.03), (1, -0.026)],
        w=[(0, 0.007), (0.08, 0.023), (0.25, 0.04), (0.5, 0.043), (0.75, 0.032), (1, 0.013)],
        eye_t=0.105, eye_z=0.016, eye_r=0.018, mouth_t=0.13, mouth_z0=-0.012, mouth_z1=-0.008, gill_t=0.19,
        fins=[Fin('dorsal', 0.38, 0.45, [(0, 0), (0.2, 0.95), (0.55, 0.85), (1, 0.05)], 0.06, 6, spiny=True),
              Fin('dorsal', 0.66, 0.73, [(0, 0), (0.25, 0.85), (0.7, 0.55), (1, 0.05)], 0.05, 8),
              Fin('anal', 0.67, 0.74, [(0, 0), (0.25, 0.8), (0.7, 0.5), (1, 0.05)], 0.045, 8),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.32), 0.15, 18),
              Fin('pectoral', 0.2, 0.215, [(0, 0), (0.5, 0.3), (1.0, 0.12), (0.8, 0.0), (0, -0.05)], 0.08, 9),
              Fin('pelvic', 0.38, 0.395, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.06, 6)]),
    aspetto=Look(back=(0.10, 0.13, 0.17), flank=(0.46, 0.49, 0.52), belly=(0.68, 0.68, 0.66), fin=(0.26, 0.27, 0.24),
                 iris=(0.7, 0.68, 0.55), iris_dark=(0.12, 0.12, 0.1), pattern='barracuda'),
    famiglia='bleeding', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ───────────────────────── aiuti della famiglia ─────────────────────────
# Tutto nelle coordinate del pesce dritto (gli extra girano prima della piega e della posa): il muso in x = 0,
# la coda in x = 1, il fianco sinistro (quello che si vede) verso −Y.

def _sezione(c, t):
    """(quota del centro, mezza altezza, mezza larghezza) del corpo alla posizione t."""
    zc, h, w = c.body.section(np.array([t], F))
    return float(zc[0]), float(h[0]), float(w[0])


def _pelle_tz(c, t, z, lato=-1):
    """Il punto della pelle (e la sua normale) alla posizione t e alla quota z, sul lato dato."""
    zc, h, _ = _sezione(c, t)
    return c.body.superficie(t, (z - zc) / h, lato)


def _telaio(n):
    """Due direzioni sulla pelle nel punto di normale n: e1 lungo il corpo (verso la coda), e2 = n × e1 (sul
    fianco sinistro è verso il dorso)."""
    e1 = np.array((1.0, 0.0, 0.0), F) - n * float(n[0])
    e1 = e1 / (np.linalg.norm(e1) + 1e-9)
    e2 = np.cross(n, e1).astype(F)
    return e1.astype(F), e2 / (np.linalg.norm(e2) + 1e-9)


def _cache(c, nome, fn):
    """La geometria delle ferite di una specie si calcola una volta sola: la usano sia il campo che l'extra."""
    if not hasattr(c, nome):
        setattr(c, nome, fn(c))
    return getattr(c, nome)


def _giu(c, verso_camera=0.1):
    """Il basso del ritratto nelle coordinate del pesce dritto: le gocce pendono giù anche quando il ritratto
    gira il pesce sul suo asse (la remora mostra il dorso). La posa è Rz(yaw)·Ry(pitch)·Rx(roll): il basso
    del mondo riportato nel pesce è (sin pitch, −sin roll·cos pitch, −cos roll·cos pitch); come nel prototipo
    pende appena verso la camera."""
    rit = c.specie.ritratto if c.specie.ritratto is not None else PIANI[c.specie.piano].ritratto
    ro, pi = math.radians(rit.roll), math.radians(rit.pitch)
    d = np.array((math.sin(pi), -verso_camera - math.sin(ro) * math.cos(pi), -math.cos(ro) * math.cos(pi)), F)
    return d / np.linalg.norm(d)


def _pelle(c):
    """Il corpo con la pelle e i suoi attributi: è il primo oggetto che fa la famiglia."""
    return c.obs[0]


def _vertici(ob):
    """I vertici di una mesh (N, 3), nelle coordinate del pesce dritto."""
    me = ob.data
    V = np.empty(len(me.vertices) * 3, F)
    me.vertices.foreach_get('co', V)
    return V.reshape(-1, 3)


def _dipingi(c, nome, fn, modo='max'):
    """Ridipinge un attributo della pelle del corpo: 'wound' (carne viva), 'blood' (sangue), 'mouth' (il colore
    Look.bocca_col). modo 'max': il più forte fra quello che c'è e fn(V); 'nuovo': fn(V, vecchio)."""
    ob = _pelle(c)
    V = _vertici(ob)
    a = ob.data.attributes[nome]
    vecchio = np.empty(len(V), F)
    a.data.foreach_get('value', vecchio)
    nuovo = np.maximum(vecchio, fn(V)) if modo == 'max' else fn(V, vecchio)
    a.data.foreach_set('value', np.clip(np.asarray(nuovo, F), 0.0, 1.0))


class _Scavi:
    """I pezzi di carne tolti a mano da una specie: morsi, solchi lungo la pelle, fori dei denti, fessure da parte
    a parte. Ogni pezzo è un campo g(p) (negativo dentro la carne tolta) con il suo riquadro; lo stesso elenco
    scava il campo del corpo (scava, per Specie.campo) e dà la carne viva sui vertici (carne, per l'attributo
    'wound' nell'extra)."""

    def __init__(self, P):
        self.P = P
        self.pezzi = []

    def aggiungi(self, f, lo, hi):
        self.pezzi.append((f, np.asarray(lo, F), np.asarray(hi, F)))

    def coni(self, A, B, R1, R2):
        """Coni arrotondati da A (raggio R1) a B (raggio R2): fori dei denti, chiodi, solchi in fila."""
        f, lo, hi = self.P.campo_coni(A, B, R1, R2)
        self.aggiungi(f, lo, hi)

    def solco(self, Q, R):
        """Un solco lungo la spezzata Q (M, 3) con i raggi R (M,): una catena di coni arrotondati."""
        Q, R = np.asarray(Q, F), np.asarray(R, F)
        self.coni(Q[:-1], Q[1:], R[:-1], R[1:])

    def sfera(self, centro, r):
        c0 = np.asarray(centro, F)
        self.aggiungi(lambda p: (np.linalg.norm(p - c0, axis=1) - r).astype(F), c0 - r - 0.002, c0 + r + 0.002)

    def g(self, p):
        out = np.full(len(p), LONTANO, F)
        for f, lo, hi in self.pezzi:
            m = np.all((p >= lo) & (p <= hi), axis=1)
            if m.any():
                out[m] = np.minimum(out[m], f(p[m]))
        return out

    def scava(self, f, k=0.0012):
        """Il campo del corpo f senza i pezzi tolti."""
        smax = self.P.sdf.smax

        def h(p):
            return smax(f(p), -self.g(p), k).astype(F)
        return h

    def carne(self, V, bordo=0.0025):
        """La carne viva sui vertici: 1 sulle pareti dei pezzi tolti, che sfuma in `bordo` sulla pelle attorno."""
        return np.clip(1.0 - self.g(V) / bordo, 0.0, 1.0)


def _colature(sorgenti, lato=-1, seme=0.0):
    """Il sangue che cola sulla pelle (per l'attributo 'blood'): da ogni sorgente (punto, larghezza, lunghezza,
    forza) una striscia un po' storta che scende verso il ventre e si assottiglia, più la macchia attorno alla
    sorgente. Solo sul lato dato (−1: quello verso la camera; 0: tutti e due)."""
    S = [(np.asarray(p, F), float(w), float(L), float(k)) for p, w, L, k in sorgenti]

    def fn(V):
        out = np.zeros(len(V), F)
        dalla = (V[:, 1] * lato) > -0.004 if lato else np.ones(len(V), bool)
        for i, (p, w, L, k) in enumerate(S):
            m = dalla & (np.abs(V[:, 0] - p[0]) < 4 * w + 0.012) & (V[:, 2] < p[2] + 3 * w) & (V[:, 2] > p[2] - L - 0.012)
            if not m.any():
                continue
            Q = V[m]
            dz = p[2] - Q[:, 2]
            s = np.clip(dz / L, 0.0, 1.0)
            storto = w * 0.9 * np.sin(Q[:, 2] * 150.0 + i * 1.7 + seme) * s
            larga = w * (1.0 - 0.5 * s)
            stri = np.exp(-((Q[:, 0] - p[0] - storto) / larga) ** 2) * (1.0 - s) ** 0.5 * (dz > -0.6 * w)
            alone = np.exp(-(np.linalg.norm(Q - p, axis=1) / (1.5 * w)) ** 2)
            out[m] = np.maximum(out[m], k * np.maximum(stri, alone))
        return np.clip(out, 0.0, 1.0)
    return fn


def _lungo(Q, larghezza, forza=1.0, lato=-1):
    """Una macchia di sangue lungo la spezzata Q (per l'attributo 'blood'): la scia di un rivolo."""
    Q = np.asarray(Q, F)

    def fn(V):
        d = np.full(len(V), LONTANO, F)
        for a, b in zip(Q[:-1], Q[1:]):
            ab = b - a
            tt = np.clip(((V - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
            d = np.minimum(d, np.linalg.norm(V - (a + tt[:, None] * ab), axis=1))
        out = forza * np.exp(-(d / larghezza) ** 2)
        if lato:
            out = out * ((V[:, 1] * lato) > -0.004)
        return out.astype(F)
    return fn


def _res(c, fine=0.0005):
    """La griglia dei pezzi piccoli: fine nei render finali, un po' più grossa nelle anteprime veloci."""
    return fine * 1.4 if c.fast else fine


def _goccia(c, nome, punto, lunghezza, r0=0.0018, r1=0.0042, giu=None, mat=None):
    """Una goccia di sangue che pende dal punto, verso il basso del ritratto (o giu)."""
    P = c.P
    d = _giu(c) if giu is None else np.asarray(giu, F) / np.linalg.norm(giu)
    a = np.asarray(punto, F)
    b = a + d * lunghezza
    f = P.drip(a, lunghezza, r0=r0, r1=r1, dir=tuple(map(float, d)))
    lo, hi = np.minimum(a, b) - r1 * 2 - 0.002, np.maximum(a, b) + r1 * 2 + 0.002
    return P.oggetto_sdf(nome, f, lo, hi, mat or P.blood_material(), res=_res(c))


def _rivolo(c, nome, punti, r0, r1, goccia=0.0, mat=None):
    """Un rivolo di sangue appoggiato sulla pelle lungo i punti (già sulla pelle, appena fuori): una catena di
    coni che si allarga verso il fondo e, se goccia > 0, la goccia che pende in fondo."""
    P = c.P
    Q = [np.asarray(p, F) for p in punti]
    n = len(Q)
    R = [r0 + (r1 - r0) * i / max(n - 1, 1) for i in range(n)]
    parti = [P.sdf.round_cone(Q[i], Q[i + 1], R[i], R[i + 1]) for i in range(n - 1)]
    if goccia:
        d = _giu(c)
        parti.append(P.drip(Q[-1], goccia, r0=R[-1] * 0.8, r1=R[-1] * 1.45, dir=tuple(map(float, d))))
        Q.append(Q[-1] + d * goccia)
    A = np.array(Q)
    lo, hi = A.min(0) - max(R) * 2.5 - 0.003, A.max(0) + max(R) * 2.5 + 0.003
    return P.oggetto_sdf(nome, P.sdf.union(*parti), lo, hi, mat or P.blood_material(), res=_res(c))


def _sul_fianco(c, tz, r, lato=-1, fuori=0.25):
    """I punti (t, z) portati sulla pelle del lato dato, appena fuori (fuori · r lungo la normale): il percorso
    di un rivolo."""
    out = []
    for t, z in tz:
        p, n = _pelle_tz(c, t, z, lato)
        out.append(p + n * r * fuori)
    return out


def _curva(P0, P1, P2, P3, n=16):
    """I punti di una curva di Bézier cubica (spine piegate, uncini, fili)."""
    P0, P1, P2, P3 = (np.asarray(p, F) for p in (P0, P1, P2, P3))
    s = np.linspace(0, 1, n, dtype=F)[:, None]
    return ((1 - s) ** 3 * P0 + 3 * (1 - s) ** 2 * s * P1 + 3 * (1 - s) * s * s * P2 + s ** 3 * P3).astype(F)


def _tubo(c, nome, Q, R, mat, res=None):
    """Un oggetto a tubo lungo la spezzata Q con i raggi R (una catena di coni arrotondati)."""
    Q, R = np.asarray(Q, F), np.asarray(R, F)
    f, lo, hi = c.P.campo_coni(Q[:-1], Q[1:], R[:-1], R[1:])
    return c.P.oggetto_sdf(nome, f, lo, hi, mat, res=res or _res(c, max(float(R.min()) * 0.35, 0.0004)))


# ── materiali in più ──

def _ruggine(c, nome='Ruggine'):
    """Ferro arrugginito (chiodi, uncini, arpioni): bruno arancio a chiazze, croste scure, qualche punto di
    ferro ancora nudo; ruvido."""
    import bpy
    m = bpy.data.materials.get(nome)
    if m:
        return m
    m, g = c.P.material(nome)
    co = g.texcoord('Object')
    n = g.noise(co, scale=220.0, detail=6.0, rough=0.65)
    n2 = g.noise(co, scale=45.0, detail=4.0, rough=0.6)
    col = g.mix(g.smoothstep(0.35, 0.65, n.fac), (0.13, 0.045, 0.018), (0.44, 0.17, 0.045))
    col = g.mix(g.mul(g.smoothstep(0.58, 0.72, n2.fac), 0.85), col, (0.035, 0.025, 0.022))
    nudo = g.smoothstep(0.72, 0.8, n2.fac)
    col = g.mix(g.mul(nudo, 0.7), col, (0.3, 0.29, 0.28))
    g.output_material(g.principled(color=col, rough=g.mixf(nudo, 0.82, 0.35), metal=g.mul(nudo, 0.8), coat=0.15,
                                   normal=g.bump(g.add(n.fac, g.mul(n2.fac, 0.5)), strength=0.45, distance=0.0012)))
    return m


def _acciaio(c, nome='Acciaio'):
    """Acciaio lucido (l'apparecchio dei denti)."""
    return c.P.materiale(nome, (0.62, 0.63, 0.66), rough=0.18, coat=0.3, metal=1.0)


def _carne_mat(c, nome='CarneViva'):
    """La carne viva rossa e bagnata (lembi, brandelli)."""
    return c.P.flesh_material(nome, (0.5, 0.06, 0.06))


# ───────────────────────── le specie ─────────────────────────

def _trafittina(c):
    """Piange sangue da tutti e due gli occhi (un rivolo dal bordo di sotto di ciascun occhio, giù per la guancia
    dietro l'angolo della bocca fino alla gola, dove pende la goccia) e la prima spina della dorsale, nera e
    velenosa, si è piegata all'indietro e le è entrata nella schiena (dove entra c'è la ferita della famiglia)."""
    P, body = c.P, c.body
    sh = c.forma
    occhi = body.occhi_lista()
    scie = []
    for k, lato in enumerate((-1, 1)):
        ec, r, _ = occhi[k]
        tz = [(sh.eye_t + 0.002, sh.eye_z - r * 0.98), (sh.eye_t + 0.009, sh.eye_z - r * 1.8),
              (sh.eye_t + 0.018, sh.eye_z - r * 2.6), (sh.eye_t + 0.028, sh.eye_z - r * 3.4),
              (sh.eye_t + 0.037, sh.eye_z - r * 4.2), (sh.eye_t + 0.044, sh.eye_z - r * 4.9)]
        Q = _sul_fianco(c, tz, 0.0028, lato)
        c.obs.append(_rivolo(c, f'Lacrima{lato}', Q, 0.0021, 0.0032, goccia=0.03))
        scie.append(Q)
    _dipingi(c, 'blood', _lungo(scie[0], 0.006, 0.9))
    # la spina: dalla radice della prima dorsale sale, si piega indietro e scende a infilarsi nel fianco
    t0 = 0.265
    base = np.array((t0, 0.0, float(body.top(np.array([t0], F))[0]) - 0.004), F)
    E, nE = body.superficie(0.345, 0.62, -1)
    Q = _curva(base, base + np.array((0.012, -0.004, 0.065), F), E + nE * 0.05 + np.array((-0.018, 0.0, 0.012), F),
               E - nE * 0.016, n=18)
    R = np.linspace(0.0036, 0.0011, len(Q))
    nera = P.materiale('SpinaTracina', (0.018, 0.016, 0.015), rough=0.28, coat=0.7)
    c.obs.append(_tubo(c, 'SpinaPiegata', Q, R, nera))
    _dipingi(c, 'blood', _colature([(E, 0.006, 0.06, 1.0)]))


# ── Trafittina (tracina drago, Trachinus draco) ──
# Allungata e compressa, la testa piccola con gli occhi in cima che guardano in su, la bocca obliqua all'insù
# (la mascella di sotto davanti); la prima dorsale corta e nera con le spine velenose, la seconda dorsale e
# l'anale lunghissime e basse, la spina dell'opercolo all'indietro e due spinette sopra gli occhi; le righe
# oblique gialle e azzurre sul fianco, il dorso bruno a chiazze. Le lacrime di sangue e la spina piegata nella
# schiena sono l'extra; la ferita della famiglia è dove entra la spina.
SPECIE['trafittina'] = Specie(
    forma=Shape(
        top=[(0, 0.014), (0.02, 0.026), (0.05, 0.04), (0.09, 0.052), (0.14, 0.064), (0.22, 0.078), (0.32, 0.088), (0.45, 0.087),
             (0.6, 0.075), (0.75, 0.058), (0.88, 0.04), (1, 0.03)],
        bot=[(0, -0.002), (0.02, -0.016), (0.05, -0.034), (0.1, -0.055), (0.18, -0.074), (0.3, -0.087), (0.45, -0.087),
             (0.6, -0.075), (0.75, -0.058), (0.88, -0.04), (1, -0.03)],
        w=[(0, 0.008), (0.04, 0.028), (0.12, 0.048), (0.25, 0.054), (0.45, 0.047), (0.7, 0.033), (0.9, 0.02), (1, 0.014)],
        eye_t=0.085, eye_z=0.036, eye_r=0.018, mouth_t=0.085, mouth_z0=0.008, mouth_z1=-0.024, gill_t=0.24,
        spine=[Spine(0.232, 0.232, 0.22, 0.22, 1, lunghezza=0.036, raggio=0.0036, inclinazione=0.9, fila=True),
               Spine(0.072, 0.094, 0.96, 0.96, 2, lunghezza=0.008, raggio=0.0022, inclinazione=0.45, fila=True)],
        fins=[Fin('dorsal', 0.26, 0.33, [(0, 0), (0.08, 1.0), (0.3, 0.92), (0.6, 0.7), (0.85, 0.4), (1, 0.05)], 0.075, 6, spiny=True,
                  colore=(0.016, 0.015, 0.016), bordo=(0.01, 0.01, 0.012)),
              Fin('dorsal', 0.35, 0.96, [(0, 0), (0.02, 0.8), (0.1, 0.95), (0.5, 0.95), (0.9, 0.9), (1, 0.15)], 0.048, 32,
                  colore=(0.5, 0.42, 0.22)),
              Fin('anal', 0.3, 0.96, [(0, 0), (0.02, 0.75), (0.1, 0.9), (0.5, 0.9), (0.9, 0.85), (1, 0.15)], 0.04, 34),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.5, 0.06, 0.85), 0.14, 16),
              Fin('pectoral', 0.25, 0.265, [(0, 0), (0.45, 0.42), (0.95, 0.3), (1.0, 0.0), (0.75, -0.18), (0, -0.12)], 0.12, 12,
                  z=-0.35),
              Fin('pelvic', 0.19, 0.2, PELVICA, 0.055, 6)]),
    aspetto=Look(back=(0.24, 0.19, 0.1), flank=(0.52, 0.45, 0.28), belly=(0.74, 0.72, 0.62), fin=(0.42, 0.36, 0.2),
                 iris=(0.55, 0.62, 0.45), iris_dark=(0.08, 0.1, 0.06), metal=0.25, irid=0.25, squame=0.5,
                 disegni=[Disegno('strisce', colore=(0.14, 0.3, 0.56), forza=0.8, n=22, v0=-13.4, v1=-1.3, inclinazione=12.0,
                                  larghezza=0.13, u0=0.22),
                          Disegno('strisce', colore=(0.88, 0.72, 0.2), forza=0.75, n=22, v0=-13.12, v1=-1.02, inclinazione=12.0,
                                  larghezza=0.11, u0=0.22),
                          Disegno('sfumatura', colore=(0.74, 0.72, 0.62), v1=-0.55, larghezza=0.12),
                          Disegno('macchie', colore=(0.1, 0.075, 0.04), forza=0.6, scala=38, r=0.2, v0=0.55)]),
    extra=_trafittina,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[((0.336, 0.74), (0.356, 0.47))], denti=7))
