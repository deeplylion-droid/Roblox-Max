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

    def scuro(self, c, da=0.003, scala=0.008):
        """Il fondo delle ferite profonde, più scuro: per l'attributo 'mouth' (il colore dell'interno della bocca,
        Look.bocca_col, che il materiale stende sopra la carne). Quanto il vertice sta sotto la pelle di prima, solo
        sulla carne viva."""
        base = c.body.base()

        def fn(V):
            return (np.clip((-base(V) - da) / scala, 0, 1) * (self.carne(V) > 0.5)).astype(F)
        return fn


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


def _pelle_y(c, X, Z, lato=-1, fino=0.2):
    """La pelle lungo y alle posizioni (X, Z) (array), sul lato dato, cercata sul campo vero del corpo (con le pinne
    di carne: serve per la coda dello squalo volpe, che non è nei profili). Bisezione da fuori (y = lato · fino) a
    dentro (y = 0), per tutti i punti insieme. Restituisce (punti, normali, dove c'è corpo)."""
    f = _cache(c, 'campo_vero', lambda c: c.body.raw())
    X, Z = np.asarray(X, F), np.asarray(Z, F)
    n = len(X)
    a = np.stack([X, np.full(n, lato * fino, F), Z], axis=1).astype(F)
    b = np.stack([X, np.zeros(n, F), Z], axis=1).astype(F)
    ok = f(b) <= 0
    for _ in range(18):
        m = (a + b) * 0.5
        fuori = (f(m) > 0)[:, None]
        a = np.where(fuori, m, a)
        b = np.where(fuori, b, m)
    p = ((a + b) * 0.5).astype(F)
    g = np.stack([f(p + d) - f(p - d) for d in np.eye(3, dtype=F) * 0.0006], axis=1)
    return p, (g / (np.linalg.norm(g, axis=1, keepdims=True) + 1e-12)).astype(F), ok


def _cicatrici(c, segmenti, raggio, mat, nome='Cicatrici', passo=0.004):
    """Le cicatrici: cordoni chiari in rilievo sulla pelle, ciascuno lungo il segmento ((x0, z0), (x1, z1)) del
    fianco sinistro (anche sulle pinne di carne). Tutte in un oggetto (una catena di coni per cicatrice)."""
    A, B, R1, R2 = [], [], [], []
    for (x0, z0), (x1, z1) in segmenti:
        n = max(3, int(math.hypot(x1 - x0, z1 - z0) / passo))
        u = np.linspace(0, 1, n + 1)
        pts, nrm, ok = _pelle_y(c, x0 + (x1 - x0) * u, z0 + (z1 - z0) * u)
        r = raggio * (0.55 + 0.45 * np.sin(np.pi * u) ** 0.5)
        Q = pts + nrm * (r * 0.15)[:, None]
        for i in range(n):
            if ok[i] and ok[i + 1]:
                A.append(Q[i])
                B.append(Q[i + 1])
                R1.append(r[i])
                R2.append(r[i + 1])
    if not A:
        return None
    f, lo, hi = c.P.campo_coni(A, B, R1, R2)
    return c.P.oggetto_sdf(nome, f, lo, hi, mat, res=_res(c, max(raggio * 0.3, 0.0005)))


def _pinne_razza(c):
    """Le pinne di carne delle specie viste dall'alto (piano 'razza': dorsali e caudale sulla coda), rifatte qui.
    In pesci.piastra, sulle razze, il riquadro della maschera viene riportato nel mondo prima che il campo lo usi
    (le variabili lo, hi della chiusura cambiano dopo): il campo resta vuoto e le pinne non si vedono. Qui la
    stessa lastra, con il riquadro nel telaio delle pinne. Restituisce [(campo, lo, hi)] nel mondo."""
    P, body = c.P, c.body
    vb, a_mondo, da_mondo = body.telaio_pinne()
    out = []
    for fin in c.forma.fins:
        if not fin.carnosa or fin.kind in ('pectoral', 'pelvic'):
            continue
        roots, tips, fr = P.fin_points(vb, fin, -1)
        R, T = np.array(roots, F), np.array(tips, F)
        o = np.zeros(3, F)
        e1, e2, en = np.array((1, 0, 0), F), np.array((0, 0, 1), F), np.array((0, 1, 0), F)

        def piano(Q, o=o, e1=e1, e2=e2, en=en):
            Q = Q - o
            return np.stack([Q @ e1, Q @ e2], axis=1).astype(F), (Q @ en).astype(F)
        radice = piano(R)[0]
        poly = np.concatenate([radice, piano(T)[0][::-1]])
        H, th1 = fin.size, (0.0024 if c.fast else 0.0015)
        th0 = max(fin.spessore, th1 * 1.5)
        tutti = np.concatenate([R, T])
        lo_t, hi_t = tutti.min(0) - th0 - 0.01, tutti.max(0) + th0 + 0.01

        def f(Pm, piano=piano, radice=radice, poly=poly, H=H, th0=th0, th1=th1, lo_t=lo_t, hi_t=hi_t):
            out_ = np.full(len(Pm), LONTANO, F)
            Q = da_mondo(Pm)
            m = np.all((Q >= lo_t) & (Q <= hi_t), axis=1)
            if m.any():
                q2, qn = piano(Q[m])
                d2 = P._poligono_2d(q2, poly)
                th = th1 + (th0 - th1) * np.clip(1 - P._polilinea(q2, radice) / (H * 0.9), 0, 1) ** 1.5
                wy = np.abs(qn) - th
                out_[m] = np.minimum(np.maximum(d2, wy), 0) + np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(wy, 0) ** 2)
            return out_
        cc = a_mondo(np.array([[a, b, z] for a in (lo_t[0], hi_t[0]) for b in (lo_t[1], hi_t[1]) for z in (lo_t[2], hi_t[2])], F))
        out.append((f, cc.min(0), cc.max(0)))
    return out


def _con_pinne_razza(c, f):
    """Il campo f con le pinne di carne della razza rifatte (vedi _pinne_razza), fuse come quelle del generatore."""
    pinne = _cache(c, 'pinne_razza', _pinne_razza)
    smin = c.P.sdf.smin

    def g(p):
        d = f(p)
        for pf, lo, hi in pinne:
            m = np.all((p >= lo) & (p <= hi), axis=1)
            if m.any():
                d[m] = smin(d[m], pf(p[m]), 0.005)
        return d.astype(F)
    return g


def _chiodo(P, base, asse, fuori, r=0.0028, testa=0.0068, piega=None):
    """Un chiodo infilato: il gambo da `base` (dentro la carne) lungo `asse` fino alla testa piatta, fuori di
    `fuori` dalla pelle; piega = (dove, direzione) storce la parte di fuori (chiodo piegato). Campo e riquadro."""
    asse = np.asarray(asse, F) / np.linalg.norm(asse)
    base = np.asarray(base, F)
    entra = 0.012
    a = base - asse * entra
    if piega is None:
        cima = base + asse * fuori
        gambo = P.sdf.round_cone(a, cima, r, r * 0.9)
        dirt = asse
    else:
        dove, verso = piega
        gomito = base + asse * fuori * dove
        dirt = np.asarray(verso, F) / np.linalg.norm(verso)
        cima = gomito + dirt * fuori * (1 - dove)
        gambo = P.sdf.union(P.sdf.round_cone(a, gomito, r, r * 0.95), P.sdf.round_cone(gomito, cima, r * 0.95, r * 0.9), k=0.001)
    # la testa: un disco piatto perpendicolare all'ultimo tratto del gambo
    c0 = cima + dirt * 0.0009

    def testa_f(p, c0=c0, d=dirt):
        q = p - c0
        h = q @ d
        rad = np.linalg.norm(q - h[:, None] * d, axis=1)
        return (np.maximum(rad - testa, np.abs(h) - 0.0011) - 0.0004).astype(F)
    f = P.sdf.union(gambo, testa_f, k=0.0012)
    pts = np.array([a, cima], F)
    return f, pts.min(0) - testa - 0.004, pts.max(0) + testa + 0.004


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
    R = np.linspace(0.0052, 0.0013, len(Q))
    nera = P.materiale('SpinaTracina', (0.03, 0.026, 0.024), rough=0.25, coat=0.8)
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
        fins=[Fin('dorsal', 0.255, 0.335, [(0, 0), (0.08, 1.0), (0.3, 0.92), (0.6, 0.7), (0.85, 0.4), (1, 0.05)], 0.1, 6, spiny=True,
                  colore=(0.06, 0.055, 0.05), bordo=(0.012, 0.011, 0.012)),
              Fin('dorsal', 0.35, 0.96, [(0, 0), (0.02, 0.8), (0.1, 0.95), (0.5, 0.95), (0.9, 0.9), (1, 0.15)], 0.048, 32,
                  colore=(0.5, 0.42, 0.22)),
              Fin('anal', 0.3, 0.96, [(0, 0), (0.02, 0.75), (0.1, 0.9), (0.5, 0.9), (0.9, 0.85), (1, 0.15)], 0.04, 34),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.5, 0.06, 0.85), 0.14, 16),
              Fin('pectoral', 0.25, 0.265, [(0, 0), (0.45, 0.42), (0.95, 0.3), (1.0, 0.0), (0.75, -0.18), (0, -0.12)], 0.12, 12,
                  z=-0.35),
              Fin('pelvic', 0.19, 0.2, PELVICA, 0.055, 6)]),
    aspetto=Look(back=(0.17, 0.13, 0.07), flank=(0.4, 0.34, 0.2), belly=(0.72, 0.7, 0.6), fin=(0.42, 0.36, 0.2),
                 iris=(0.55, 0.62, 0.45), iris_dark=(0.08, 0.1, 0.06), metal=0.25, irid=0.25, squame=0.5,
                 disegni=[Disegno('strisce', colore=(0.1, 0.22, 0.48), forza=0.8, n=22, v0=-13.4, v1=-1.3, inclinazione=12.0,
                                  larghezza=0.075, u0=0.22),
                          Disegno('strisce', colore=(0.85, 0.66, 0.16), forza=0.7, n=22, v0=-13.12, v1=-1.02, inclinazione=12.0,
                                  larghezza=0.06, u0=0.22),
                          Disegno('sfumatura', colore=(0.72, 0.7, 0.6), v1=-0.55, larghezza=0.12),
                          Disegno('macchie', colore=(0.1, 0.075, 0.04), forza=0.6, scala=38, r=0.2, v0=0.55)]),
    extra=_trafittina,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[((0.336, 0.74), (0.356, 0.47))], denti=7))


# i morsi del pesce serra: (t, v, raggio, verso). Sul bordo del profilo (|v| = 1) il morso porta via un pezzo da
# parte a parte, a mezzaluna smerlata (solo dove non ci sono pinne); sul fianco è una mezzaluna scavata nella carne
# con i fori dei denti lungo l'arco di fuori (verso = dove guarda la gobba della mezzaluna, in gradi: 0 verso la
# coda, 90 verso il dorso).
_MORSI_SERRA = [(0.2, 1.0, 0.042, 0), (0.42, -1.0, 0.04, 0), (0.86, 1.0, 0.03, 0), (0.9, -1.0, 0.026, 0),
                (0.38, 0.3, 0.036, 210), (0.56, -0.25, 0.034, 150), (0.7, 0.4, 0.03, 250)]


def _geo_serrasangue(c):
    """I morsi: sul profilo una tacca tonda passante con il bordo smerlato dai denti (cilindri lungo y); sul fianco
    una mezzaluna (una sfera meno la stessa spostata) scavata nella carne, con i fori conici dei denti in fila
    lungo l'arco di fuori."""
    P, body = c.P, c.body
    s = _Scavi(P)
    rng = np.random.default_rng(31)
    A, B, R1, R2, fondo = [], [], [], [], []
    for k, (t, v, R, verso) in enumerate(_MORSI_SERRA):
        if abs(v) >= 1.0:
            zb = float((body.top if v > 0 else body.bot)(np.array([t], F))[0])
            cz = zb + np.sign(v) * R * 0.3
            cerchi = [(t, cz, R)]
            for j in range(9):
                a = math.radians(180 + 18 * j) if v > 0 else math.radians(18 * j)
                cerchi.append((t + R * math.cos(a), cz + R * math.sin(a), R * 0.2))
            C2 = np.array([(x, z) for x, z, _ in cerchi], F)
            Rc = np.array([r for _, _, r in cerchi], F)

            def g(p, C2=C2, Rc=Rc):
                q = p[:, (0, 2)]
                return np.min(np.linalg.norm(q[:, None, :] - C2[None], axis=2) - Rc[None], axis=1).astype(F)
            s.aggiungi(g, (t - R * 1.4, -0.2, cz - R * 1.4), (t + R * 1.4, 0.2, cz + R * 1.4))
            p_basso, _ = _pelle_tz(c, t, (cz - R * 0.95) if v > 0 else zb + 0.004, -1)
            fondo.append((p_basso, p_basso, R))
            continue
        p0, n0 = body.superficie(t, v, -1)
        e1, e2 = _telaio(n0)
        b = math.radians(verso)
        u1 = (math.cos(b) * e1 + math.sin(b) * e2).astype(F)        # verso la gobba della mezzaluna
        ra, prof = R * 0.8, 0.0095
        ca = p0 + n0 * (ra - prof)
        cb = ca - u1 * ra * 0.62 + n0 * 0.002

        def g(q, ca=ca, cb=cb, ra=ra):
            return np.maximum(np.linalg.norm(q - ca, axis=1) - ra, -(np.linalg.norm(q - cb, axis=1) - ra * 0.98)).astype(F)
        s.aggiungi(g, ca - ra - 0.004, ca + ra + 0.004)
        piu_basso = None
        u2 = np.cross(n0, u1).astype(F)
        for j in range(9):
            phi = math.radians(-80 + 160 * j / 8)
            q = p0 + R * 0.72 * (math.cos(phi) * u1 + math.sin(phi) * u2)
            p, n = _pelle_tz(c, float(q[0]), float(q[2]), -1)
            A.append(p + n * 0.002)
            B.append(p - n * rng.uniform(0.007, 0.01))
            r = rng.uniform(0.0034, 0.0044)
            R1.append(r)
            R2.append(r * 0.22)
            if piu_basso is None or p[2] < piu_basso[2]:
                piu_basso = p
        fondo.append((p0, piu_basso, R))
    s.coni(A, B, R1, R2)
    s.fondo = fondo
    return s


def _campo_serrasangue(c, f):
    return _cache(c, 'scavi', _geo_serrasangue).scava(f)


def _serrasangue(c):
    """La carne viva nei morsi e nei fori dei denti, il sangue che cola da ciascuno, le gocce."""
    s = _cache(c, 'scavi', _geo_serrasangue)
    _dipingi(c, 'wound', s.carne)
    _dipingi(c, 'mouth', s.scuro(c))
    _dipingi(c, 'blood', _colature([(lo, 0.0055, 0.06 + R, 0.95) for _, lo, R in s.fondo] +
                                   [(p0, R * 0.45, R * 0.8, 0.4) for p0, _, R in s.fondo[4:]]))
    for k in (0, 1, 4, 5):
        _, lo, R = s.fondo[k]
        c.obs.append(_goccia(c, f'GocciaMorso{k}', lo, 0.026 + 0.008 * (k % 3), r0=0.0016, r1=0.0038))


# ── Serrasangue (pesce serra, Pomatomus saltatrix) ──
# Robusto e affusolato, la testa grande con la bocca larga (la mascella di sotto appena più lunga) e i denti
# taglienti; prima dorsale bassa e spinosa, seconda dorsale e anale lunghe e opposte, coda forcuta; verde-blu
# sopra, argento sotto, la macchia scura alla base della pettorale. È pieno di morsi a mezzaluna con i fori dei
# denti, ognuno della forma della sua bocca (campo + extra).
SPECIE['serrasangue'] = Specie(
    forma=Shape(
        top=[(0, -0.008), (0.03, 0.022), (0.08, 0.055), (0.15, 0.088), (0.25, 0.114), (0.38, 0.126), (0.5, 0.121), (0.65, 0.097),
             (0.8, 0.063), (0.92, 0.04), (1, 0.034)],
        bot=[(0, -0.024), (0.03, -0.044), (0.1, -0.08), (0.2, -0.108), (0.35, -0.122), (0.5, -0.116), (0.65, -0.091),
             (0.8, -0.058), (0.92, -0.038), (1, -0.034)],
        w=[(0, 0.006), (0.05, 0.032), (0.15, 0.056), (0.35, 0.066), (0.6, 0.054), (0.85, 0.03), (1, 0.018)],
        eye_t=0.1, eye_z=0.03, eye_r=0.021, mouth_t=0.125, mouth_z0=-0.014, mouth_z1=-0.032, gill_t=0.27,
        fins=[Fin('dorsal', 0.33, 0.44, [(0, 0), (0.12, 0.8), (0.35, 1.0), (0.75, 0.7), (1, 0.1)], 0.06, 8, spiny=True),
              Fin('dorsal', 0.47, 0.79, [(0, 0), (0.08, 1.0), (0.25, 0.72), (0.6, 0.5), (0.95, 0.42), (1, 0.05)], 0.095, 24),
              Fin('anal', 0.5, 0.79, [(0, 0), (0.08, 0.95), (0.25, 0.68), (0.6, 0.48), (0.95, 0.4), (1, 0.05)], 0.085, 22),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.65, 0.28), 0.25, 20),
              Fin('pectoral', 0.27, 0.285, PETTORALE, 0.1, 10),
              Fin('pelvic', 0.33, 0.345, PELVICA, 0.06, 6)]),
    aspetto=Look(back=(0.06, 0.17, 0.2), flank=(0.38, 0.44, 0.46), belly=(0.72, 0.74, 0.73), fin=(0.26, 0.3, 0.26),
                 iris=(0.75, 0.68, 0.35), iris_dark=(0.15, 0.12, 0.05), metal=0.55, irid=0.35, squame=0.6,
                 disegni=[Disegno('ventre', colore=(0.78, 0.8, 0.8), forza=0.5, v1=-0.4),
                          Disegno('macchia', colore=(0.02, 0.03, 0.035), forza=0.95, u=0.28, v=-0.22, r=0.011, allungamento=1.3)]),
    campo=_campo_serrasangue, extra=_serrasangue,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[((0.6, 0.55), (0.64, 0.15))], denti=8))


def _geo_squartotta(c):
    """La fessura da parte a parte: una lastra obliqua nel piano del corpo (in y passa tutto), più stretta alle
    due punte come un colpo di lama; sta sopra la pettorale lunga."""
    P = c.P
    s = _Scavi(P)
    a, b, mezza = np.array((0.47, 0.18), F), np.array((0.63, -0.055), F), 0.028
    ab = b - a

    def g(p):
        # la lastra è inclinata come lo sguardo della camera (yaw del ritratto): attraverso il taglio si vede il fondo
        q = np.stack([p[:, 0] + 0.12 * p[:, 1], p[:, 2]], axis=1)
        tt = np.clip(((q - a) @ ab) / float(ab @ ab), 0, 1)
        d = np.linalg.norm(q - (a + tt[:, None] * ab), axis=1)
        return (d - mezza * (0.3 + 0.7 * np.clip(np.sin(np.pi * tt), 0, 1) ** 0.5)).astype(F)
    s.aggiungi(g, (min(a[0], b[0]) - 0.03, -0.2, min(a[1], b[1]) - 0.03), (max(a[0], b[0]) + 0.03, 0.2, max(a[1], b[1]) + 0.03))
    s.estremi = (a, b)
    return s


def _campo_squartotta(c, f):
    return _cache(c, 'scavi', _geo_squartotta).scava(f, k=0.001)


def _squartotta(c):
    """La carne viva sulle due facce del taglio; il sangue esce dalla punta di sotto e cola sul fianco."""
    s = _cache(c, 'scavi', _geo_squartotta)
    _dipingi(c, 'wound', s.carne)
    a, b = s.estremi
    basso, n = _pelle_tz(c, float(b[0]) - 0.004, float(b[1]) + 0.004, -1)
    lungo = [_pelle_tz(c, float(a[0] + (b[0] - a[0]) * u) + 0.012, float(a[1] + (b[1] - a[1]) * u), -1)[0] for u in (0.35, 0.6, 0.85)]
    _dipingi(c, 'blood', _colature([(basso, 0.007, 0.16, 1.0)] + [(p, 0.004, 0.06, 0.8) for p in lungo]))
    c.obs.append(_goccia(c, 'GocciaTaglio', basso + n * 0.001, 0.035, r0=0.0018, r1=0.0042))
    fondo, _ = c.body.superficie(float(b[0]) + 0.01, -0.97, -1)
    c.obs.append(_goccia(c, 'GocciaVentre', fondo, 0.045, r0=0.0018, r1=0.0045))


# ── Squartotta (sparaglione, Diplodus annularis) ──
# Piccolo sparide ovale e alto, il muso appuntito con la boccuccia, l'occhio grande; la dorsale lunga spinosa,
# coda forcuta, la pettorale lunga e appuntita; argento appena giallo con le bande verticali sbiadite, il largo
# ANELLO NERO attorno al peduncolo della coda, le pinne ventrali gialle. Un taglio netto da parte a parte
# (campo: si vede attraverso), la carne viva sulle facce del taglio, il sangue che cola dalla punta di sotto.
SPECIE['squartotta'] = Specie(
    forma=Shape(
        top=[(0, -0.028), (0.02, 0.0), (0.06, 0.05), (0.12, 0.11), (0.2, 0.17), (0.3, 0.212), (0.42, 0.232), (0.55, 0.218),
             (0.7, 0.168), (0.82, 0.11), (0.92, 0.07), (1, 0.06)],
        bot=[(0, -0.05), (0.03, -0.075), (0.1, -0.13), (0.2, -0.178), (0.32, -0.212), (0.45, -0.222), (0.58, -0.202),
             (0.7, -0.158), (0.82, -0.1), (0.92, -0.068), (1, -0.06)],
        w=[(0, 0.008), (0.06, 0.03), (0.18, 0.05), (0.38, 0.056), (0.6, 0.048), (0.8, 0.03), (1, 0.017)],
        eye_t=0.16, eye_z=0.075, eye_r=0.037, mouth_t=0.055, mouth_z0=-0.04, mouth_z1=-0.05, gill_t=0.3,
        fins=[Fin('dorsal', 0.33, 0.85, [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.82), (0.8, 0.75), (0.95, 0.55), (1, 0.05)], 0.12, 22,
                  spiny=True),
              Fin('anal', 0.62, 0.85, [(0, 0), (0.12, 0.9), (0.6, 0.62), (0.95, 0.5), (1, 0.05)], 0.09, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.34), 0.27, 20),
              Fin('pectoral', 0.31, 0.33, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.21, 12),
              Fin('pelvic', 0.36, 0.38, PELVICA, 0.1, 7, spiny=True, colore=(0.78, 0.62, 0.1))]),
    aspetto=Look(back=(0.26, 0.27, 0.22), flank=(0.56, 0.56, 0.48), belly=(0.74, 0.73, 0.66), fin=(0.42, 0.4, 0.3),
                 iris=(0.75, 0.65, 0.4), iris_dark=(0.15, 0.12, 0.06), metal=0.55, irid=0.3,
                 disegni=[Disegno('bande', colore=(0.24, 0.24, 0.2), forza=0.3, n=5, u0=0.22, u1=0.82, larghezza=0.35, onda=0.05),
                          Disegno('sfumatura', colore=(0.02, 0.02, 0.022), forza=0.95, u0=0.86, u1=0.96, larghezza=0.012),
                          Disegno('sfumatura', colore=(0.7, 0.6, 0.3), forza=0.35, u1=0.3, v1=-0.3, larghezza=0.1)]),
    campo=_campo_squartotta, extra=_squartotta,
    famiglia='bleeding', piano='alto',
    opzioni=dict(ferite=[], denti=5))


def _geo_pagro(c):
    """La fessura dell'opercolo aperta (un solco lungo l'arco del bordo) con la cavità delle branchie sotto, sui
    due lati: le branchie si vedono rosse, e da lì esce il sangue."""
    P, body, sh = c.P, c.body, c.forma
    s = _Scavi(P)
    vs = np.linspace(-0.9, 0.72, 44)
    for lato in (-1, 1):
        Q1, Q2 = [], []
        for v in vs:
            x = sh.gill_t - 0.035 * v * v
            p, n = body.superficie(float(x), float(v), lato)
            Q1.append(p - n * 0.0024)
            Q2.append(p - n * 0.0095 + np.array((-0.006, 0.0, 0.0), F))
        prof = np.sin(np.linspace(0.15, np.pi - 0.15, len(vs))) ** 0.4
        s.solco(Q1, 0.0042 * prof + 0.0012)
        s.solco(Q2, 0.0075 * prof + 0.002)
    s.arco = [body.superficie(float(sh.gill_t - 0.035 * v * v + 0.004), float(v), -1) for v in np.linspace(-0.88, 0.45, 9)]
    return s


def _campo_pagro(c, f):
    return _cache(c, 'scavi', _geo_pagro).scava(f, k=0.001)


def _pagro(c):
    """Sangue dal bordo dell'opercolo, come se respirasse sangue: la cavità rossa, un velo di sangue appena dietro il
    bordo che sfuma verso la coda (il fiato lo porta indietro), le colature che scendono, quattro rivoli grossi fino
    al ventre e le gocce alla gola."""
    s = _cache(c, 'scavi', _geo_pagro)
    sh, body = c.forma, c.body
    _dipingi(c, 'wound', s.carne)
    _dipingi(c, 'mouth', s.scuro(c))
    n3 = c.P.sdf.Noise3(4)

    def velo(V):
        x = V[:, 0]
        zc, h, _ = body.section(np.clip(x, 0, 1))
        v = np.clip((V[:, 2] - zc) / h, -1, 1)
        dx = x - (sh.gill_t - 0.035 * v * v)
        lungo = 0.05 + 0.03 * (n3(V, scale=0.02, octaves=2) + 0.5)
        k = np.clip(1 - dx / lungo, 0, 1) ** 1.2 * (dx > -0.003) * np.clip((0.55 - v) / 0.3, 0, 1)
        return (k * (V[:, 1] < 0.004)).astype(F)
    _dipingi(c, 'blood', velo)
    arco = [p for p, _ in s.arco]
    _dipingi(c, 'blood', _colature([(p + np.array((0.008, 0.0, 0.0), F), 0.012, 0.26, 1.0) for p in arco[::2]]))
    for k, v0 in enumerate((0.25, -0.1, -0.4, -0.65)):
        x0 = sh.gill_t - 0.035 * v0 * v0 + 0.005
        zc, h, _ = _sezione(c, x0)
        z0 = zc + h * v0
        tz = []
        for i in range(12):
            t = x0 + 0.005 * i + 0.002 * k * i
            zc_t, h_t, _ = _sezione(c, t)
            tz.append((t, max(z0 - 0.024 * i, zc_t - h_t * 0.97)))
        c.obs.append(_rivolo(c, f'RivoloBranchie{k}', _sul_fianco(c, tz, 0.0045), 0.003, 0.005, goccia=0.03 + 0.01 * k))
    gola, _ = c.body.superficie(sh.gill_t - 0.03, -0.97, -1)
    c.obs.append(_goccia(c, 'GocciaGola', gola, 0.045, r0=0.0022, r1=0.005))


# ── Pagro Sanguigno (pagro, Pagrus pagrus) ──
# Sparide alto e ovale con la fronte ripida e convessa, l'occhio grande, la bocca bassa; rosa-rosso, più scuro sul
# dorso, con i puntini azzurri sul fianco alto; dorsale lunga spinosa, coda forcuta. Sanguina dalle branchie: la
# fessura dell'opercolo aperta e rossa (campo) e il sangue che ne esce (extra); nessun altro taglio.
SPECIE['pagro_sanguigno'] = Specie(
    forma=Shape(
        top=[(0, -0.035), (0.02, -0.005), (0.05, 0.04), (0.1, 0.095), (0.17, 0.145), (0.26, 0.183), (0.38, 0.198), (0.52, 0.184),
             (0.68, 0.14), (0.82, 0.09), (0.93, 0.06), (1, 0.052)],
        bot=[(0, -0.055), (0.03, -0.08), (0.1, -0.12), (0.2, -0.16), (0.33, -0.184), (0.46, -0.184), (0.6, -0.16), (0.74, -0.11),
             (0.87, -0.068), (1, -0.052)],
        w=[(0, 0.008), (0.06, 0.035), (0.2, 0.058), (0.4, 0.064), (0.62, 0.052), (0.85, 0.028), (1, 0.016)],
        eye_t=0.165, eye_z=0.075, eye_r=0.034, mouth_t=0.07, mouth_z0=-0.045, mouth_z1=-0.058, gill_t=0.3,
        fins=[Fin('dorsal', 0.32, 0.85, [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.8), (0.8, 0.72), (0.95, 0.5), (1, 0.05)], 0.11, 24,
                  spiny=True),
              Fin('anal', 0.63, 0.85, [(0, 0), (0.12, 0.9), (0.6, 0.6), (0.95, 0.5), (1, 0.05)], 0.085, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.3), 0.27, 20),
              Fin('pectoral', 0.31, 0.33, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.21, 12),
              Fin('pelvic', 0.35, 0.37, PELVICA, 0.1, 7, spiny=True)]),
    aspetto=Look(back=(0.5, 0.17, 0.15), flank=(0.74, 0.42, 0.38), belly=(0.82, 0.68, 0.62), fin=(0.68, 0.38, 0.33),
                 iris=(0.82, 0.62, 0.35), iris_dark=(0.3, 0.12, 0.05), metal=0.45, irid=0.3,
                 disegni=[Disegno('macchie', colore=(0.2, 0.48, 0.95), forza=1.0, scala=55, r=0.17, v0=0.0, u0=0.15, u1=0.85)]),
    campo=_campo_pagro, extra=_pagro,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[], denti=6))


# ── le spine della razza chiodata (le stesse della prova del piano): diventano chiodi ──
_SPINE_RAZZA = [Spine(0.1, 0.94, 0.0, 0.0, 28, lunghezza=0.011, raggio=0.0042, lati='sinistro', inclinazione=0.55, fila=True),
                Spine(0.14, 0.42, -3.4, 3.4, 16, lunghezza=0.009, raggio=0.005, lati='sinistro', inclinazione=0.45, seme=3)]
# gli strappi nelle ali, dove si è staccata da sola: (t, z dentro l'ala, t, z al bordo, mezza larghezza)
_STRAPPI_RAZZA = [((0.215, -0.2), (0.235, -0.33), 0.012), ((0.26, 0.17), (0.3, 0.3), 0.011), ((0.37, -0.13), (0.4, -0.19), 0.008)]


def _posti_chiodi(c):
    """Dove stavano le spine della prova: la fila sulla linea di mezzo (una sì e una no, fino all'attacco della
    coda) e quelle sparse sul disco (con lo stesso generatore della prova)."""
    fila, sparse = _SPINE_RAZZA
    tv = [(float(t), 0.0) for t in np.linspace(fila.t0, fila.t1, fila.n)[:14:2]]
    rng = np.random.default_rng(sparse.seme)
    ts, vs = rng.uniform(sparse.t0, sparse.t1, sparse.n), rng.uniform(sparse.v0, sparse.v1, sparse.n)
    tv += [(float(t), float(v)) for t, v in zip(ts, vs)][:12]
    return tv


def _geo_razza(c):
    """Gli strappi passanti nelle ali (fessure frastagliate da dentro l'ala fino al bordo) e i buchi dove entrano i
    chiodi."""
    P, body = c.P, c.body
    s = _Scavi(P)
    n3 = P.sdf.Noise3(17)
    for (t0, z0), (t1, z1), mezza in _STRAPPI_RAZZA:
        a, b = np.array((t0, z0), F), np.array((t1, z1), F)
        ab = b - a

        def g(p, a=a, ab=ab, mezza=mezza):
            q = p[:, (0, 2)]
            tt = np.clip(((q - a) @ ab) / float(ab @ ab), 0, 1)
            d = np.linalg.norm(q - (a + tt[:, None] * ab), axis=1)
            frast = 0.35 + 0.65 * np.clip(tt * 1.6, 0, 1) + 0.5 * n3(p, scale=0.006, octaves=2)
            return (d - mezza * frast).astype(F)
        lo = (min(t0, t1) - 0.03, -0.1, min(z0, z1) - 0.03)
        hi = (max(t0, t1) + 0.03, 0.1, max(z0, z1) + 0.03)
        s.aggiungi(g, lo, hi)
    return s


def _campo_razza(c, f):
    return _con_pinne_razza(c, _cache(c, 'scavi', _geo_razza).scava(f, k=0.001))


def _razza(c):
    """I chiodi arrugginiti al posto delle spine (qualcuno storto, qualcuno mezzo tirato fuori), il sangue attorno a
    ciascuno, la carne viva negli strappi delle ali e il sangue che ne esce."""
    P, body = c.P, c.body
    s = _cache(c, 'scavi', _geo_razza)
    _dipingi(c, 'wound', s.carne)
    rng = np.random.default_rng(23)
    ruggine = _ruggine(c)
    campi, los, his, macchie = [], [], [], []
    for k, (t, v) in enumerate(_posti_chiodi(c)):
        p, n = body.superficie(t, v, -1)
        centro = abs(v) < 0.1
        fuori = rng.uniform(0.02, 0.034) * (1.2 if centro else 1.0) * (1.0 - 0.4 * t)
        asse = n + np.array((rng.normal(0, 0.25), 0.0, rng.normal(0, 0.25)), F)
        piega = None
        if k in (3, 9, 15):
            piega = (0.45, n * 0.3 + np.array((rng.choice((-1, 1)) * 0.9, 0.0, rng.normal(0, 0.5)), F))
        f, lo, hi = _chiodo(P, p, asse, fuori, r=0.0036 * (1.15 if centro else 1.0), testa=0.0095 * (1.15 if centro else 1.0), piega=piega)
        campi.append(f)
        los.append(lo)
        his.append(hi)
        macchie.append((p, 0.009, 0.03, 0.9))
    lo, hi = np.min(los, axis=0), np.max(his, axis=0)
    c.obs.append(P.oggetto_sdf('Chiodi', P.sdf.union(*campi), lo, hi, ruggine, res=_res(c, 0.0006)))
    # il sangue: attorno ai chiodi e agli strappi (sulla razza sdraiata il sangue si allarga, non cola lontano)
    _dipingi(c, 'blood', _colature(macchie, lato=0))
    for (t0, z0), (t1, z1), mezza in _STRAPPI_RAZZA:
        scia = []
        for u in np.linspace(0, 1, 5):
            t, z = t0 + (t1 - t0) * u, z0 + (z1 - z0) * u
            zc, h, _ = _sezione(c, t)
            scia.append(body.superficie(t, (z - zc) / h, -1)[0])
        _dipingi(c, 'blood', _lungo(scia, mezza * 1.6, 0.95, lato=0))


# ── Razza Inchiodata (razza chiodata, Raja clavata) — la prova del piano 'razza', trasformata ──
# Costruita con il dorso verso la camera (−Y): z è l'apertura delle ali, y lo spessore. I profili top/bot/w
# sono il tronco (la gobba al centro e la coda), il disco delle pettorali è Shape.disco. Le spine della prova
# (_SPINE_RAZZA) sono diventate chiodi veri, arrugginiti (extra), e nelle ali ci sono gli strappi passanti di
# quando si è staccata da sola (campo); niente bocca (bocca='nessuna': la famiglia la lascia chiusa).
SPECIE['razza_inchiodata'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.05, 0.03), (0.15, 0.058), (0.3, 0.068), (0.45, 0.055), (0.55, 0.034), (0.65, 0.017), (0.8, 0.011),
             (0.95, 0.007), (1, 0.005)],
        bot=[(0, 0.0), (0.05, -0.03), (0.15, -0.058), (0.3, -0.068), (0.45, -0.055), (0.55, -0.034), (0.65, -0.017), (0.8, -0.011),
             (0.95, -0.007), (1, -0.005)],
        w=[(0, 0.003), (0.05, 0.011), (0.15, 0.024), (0.3, 0.03), (0.45, 0.025), (0.55, 0.017), (0.65, 0.011), (0.8, 0.008),
           (0.95, 0.006), (1, 0.005)],
        eye_t=0.13, eye_z=0.0, eye_r=0.011,
        occhi=[(0.125, 0.03, 0.0105, -1), (0.125, -0.03, 0.0105, -1)], spiracoli=0.0055,
        bocca='nessuna', branchie='nessuna',
        disco=Disco(contorno=[(0, 0.0), (0.03, 0.05), (0.1, 0.15), (0.18, 0.26), (0.245, 0.34), (0.275, 0.35), (0.32, 0.315),
                              (0.39, 0.21), (0.45, 0.115), (0.5, 0.08), (0.555, 0.088), (0.6, 0.064), (0.64, 0.025), (0.68, 0.0),
                              (1.0, 0.0)],
                    spessore=[(0, 0.003), (0.12, 0.012), (0.3, 0.015), (0.45, 0.013), (0.6, 0.008), (0.68, 0.002), (1.0, 0.001)]),
        spine=[Spine(0.6, 0.94, 0.0, 0.0, 10, lunghezza=0.009, raggio=0.0036, lati='sinistro', inclinazione=0.55, fila=True)],
        fins=[Fin('dorsal', 0.82, 0.86, [(0, 0), (0.25, 0.9), (0.55, 1.0), (0.8, 0.5), (1, 0.05)], 0.028, 16, carnosa=True, spessore=0.004),
              Fin('dorsal', 0.88, 0.92, [(0, 0), (0.25, 0.9), (0.55, 1.0), (0.8, 0.5), (1, 0.05)], 0.026, 16, carnosa=True, spessore=0.004),
              Fin('caudal', 1.0, 1.0, [(0, 0.5), (0.5, 0.7), (1.0, 0.0), (0.5, -0.5), (0, -0.4)], 0.03, 16, carnosa=True, spessore=0.003)]),
    aspetto=Look(back=(0.20, 0.155, 0.11), flank=(0.26, 0.21, 0.16), belly=(0.84, 0.82, 0.78), fin=(0.18, 0.14, 0.1),
                 iris=(0.55, 0.5, 0.3), iris_dark=(0.1, 0.09, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.35, ruvido=0.5,
                 disegni=[Disegno('marmo', colore=(0.11, 0.08, 0.055), forza=0.7, scala=30, r=0.45),
                          Disegno('macchie', colore=(0.05, 0.035, 0.025), forza=0.85, scala=45, r=0.2),
                          Disegno('macchie', colore=(0.62, 0.55, 0.42), forza=0.7, scala=70, r=0.13, seme=5)]),
    campo=_campo_razza, extra=_razza,
    famiglia='bleeding', piano='razza',
    opzioni=dict(ferite=[((0.2, 1.6), (0.24, 0.9)), ((0.33, -1.0), (0.3, -1.9))], bocca=0))


def _scorticano(c):
    """Senza pelle: la famiglia lo fa tutto di carne viva (opzione carne=1); qui si ridisegnano sulla carne i
    miosetti, le linee a «<» della carne dei pesci (pallide, il colore di Look sotto la carne), il setto lungo il
    fianco e le placche d'osso della testa; le spine della testa restano spine (pallide come osso). Le gocce
    pendono dal ventre."""
    P, body, sh = c.P, c.body, c.forma
    fs, _, _ = P.spine_campo(body)

    def carne(V, vecchio):
        x, z = V[:, 0], V[:, 2]
        zc, h, _ = body.section(np.clip(x, 0, 1))
        v = (z - zc) / h
        s = (x - 0.06 * np.abs(v - 0.05) ** 0.8 - 0.36) / 0.038
        fr = np.abs(s - np.round(s))
        linee = np.exp(-(fr / 0.1) ** 2) * (x > 0.35) * (x < 0.97) * (np.abs(v) < 0.92)
        setto = np.exp(-((v - 0.05) / 0.03) ** 2) * (x > 0.34) * (x < 0.97)
        # le placche d'osso della testa: l'opercolo e il preopercolo, pallidi, dove la pelle è stata tirata via
        n3 = P.sdf.Noise3(12)
        osso = np.clip((n3(V, scale=0.02, octaves=3) + 0.15) * 3.0, 0, 1)
        dist_op = np.abs(x - (sh.gill_t - 0.03 - 0.03 * v * v))
        placche = (x < sh.gill_t + 0.005) * (x > 0.16) * np.clip(1 - dist_op / 0.022, 0, 1) * osso
        ec = body.occhi_lista()[0][0]
        orbita = np.exp(-((np.linalg.norm(V - ec, axis=1) - sh.eye_r * 1.25) / 0.0035) ** 2)
        w = 1.0 - 0.58 * np.maximum(linee, 0.7 * setto) - 0.55 * placche - 0.7 * orbita
        w = np.where(fs(V) < 0.0018, 0.0, w)
        return np.minimum(vecchio, w)
    _dipingi(c, 'wound', carne, modo='nuovo')
    for k, t in enumerate((0.3, 0.42, 0.55, 0.68)):
        p, _ = body.superficie(t, -0.98, -1)
        c.obs.append(_goccia(c, f'GocciaVentre{k}', p, 0.025 + 0.012 * (k % 2), r0=0.0018, r1=0.0042))


_PELLE_SCORFANO = (0.6, 0.13, 0.06)     # i brandelli di pelle rossa che restano: i lembi sopra gli occhi e sulle guance

# ── Scorticano (scorfano rosso, Scorpaena scrofa) ──
# Testa enorme e larga con le creste e le spine, gli occhi in alto, la bocca grande e obliqua; i lembi di pelle
# sopra gli occhi e sulle guance; dorsale spinosa alta e robusta seguita da quella molle, pettorali larghe e
# tonde, coda tonda. Gli manca la pelle (carne=1): è rosso di carne viva con le linee pallide dei miosetti
# (extra); le pinne e le spine invece ci sono tutte, ancora rosse e maculate come quelle dello scorfano.
SPECIE['scorticano'] = Specie(
    forma=Shape(
        top=[(0, -0.022), (0.025, 0.015), (0.06, 0.055), (0.1, 0.09), (0.14, 0.106), (0.18, 0.11), (0.24, 0.126), (0.34, 0.146),
             (0.48, 0.14), (0.62, 0.11), (0.78, 0.074), (0.9, 0.054), (1, 0.048)],
        bot=[(0, -0.05), (0.03, -0.08), (0.1, -0.118), (0.2, -0.146), (0.32, -0.158), (0.45, -0.15), (0.6, -0.12), (0.75, -0.085),
             (0.9, -0.056), (1, -0.048)],
        w=[(0, 0.016), (0.05, 0.052), (0.14, 0.084), (0.26, 0.092), (0.4, 0.084), (0.6, 0.06), (0.8, 0.036), (1, 0.022)],
        eye_t=0.125, eye_z=0.072, eye_r=0.03, mouth_t=0.125, mouth_z0=-0.028, mouth_z1=-0.064, gill_t=0.32,
        spine=[Spine(0.08, 0.3, 0.45, 0.98, 16, lunghezza=0.014, raggio=0.0042, inclinazione=0.55, seme=2),
               Spine(0.2, 0.3, -0.55, 0.15, 7, lunghezza=0.018, raggio=0.0045, inclinazione=0.8, seme=5)],
        filamenti=[Filamento(t=0.112, v=0.98, lunghezza=0.034, raggio=0.0045, dir=(0.25, 0.35, 1.0), curva=(5, 0, 0), punta=0.35,
                             colore=_PELLE_SCORFANO),
                   Filamento(t=0.16, v=-0.45, lunghezza=0.02, raggio=0.004, dir=(0.4, 0.7, -0.6), punta=0.4, colore=_PELLE_SCORFANO),
                   Filamento(t=0.2, v=-0.6, lunghezza=0.018, raggio=0.0038, dir=(0.5, 0.7, -0.6), punta=0.4, colore=_PELLE_SCORFANO),
                   Filamento(t=0.24, v=-0.3, lunghezza=0.016, raggio=0.0035, dir=(0.6, 0.7, -0.3), punta=0.4, colore=_PELLE_SCORFANO)],
        fins=[Fin('dorsal', 0.3, 0.62, [(0, 0), (0.04, 0.8), (0.12, 1.0), (0.25, 0.98), (0.45, 0.85), (0.65, 0.7), (0.85, 0.5), (1, 0.38)],
                  0.14, 12, spiny=True, macchie=0.55, colore_macchie=(0.18, 0.05, 0.03)),
              Fin('dorsal', 0.63, 0.86, [(0, 0.3), (0.08, 0.85), (0.45, 0.9), (0.85, 0.65), (1, 0.06)], 0.11, 10, macchie=0.5,
                  colore_macchie=(0.18, 0.05, 0.03)),
              Fin('anal', 0.62, 0.8, [(0, 0), (0.1, 0.85), (0.35, 1.0), (0.7, 0.8), (1, 0.06)], 0.1, 8, spiny=True),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.45, 1.0), 0.18, 16, macchie=0.45, colore_macchie=(0.18, 0.05, 0.03)),
              Fin('pectoral', 0.32, 0.34, PETTORALE_TONDA, 0.2, 14, z=-0.2, macchie=0.5, colore_macchie=(0.18, 0.05, 0.03)),
              Fin('pelvic', 0.34, 0.355, PELVICA, 0.11, 6, spiny=True)]),
    aspetto=Look(back=(0.74, 0.6, 0.55), flank=(0.8, 0.67, 0.62), belly=(0.86, 0.76, 0.71), fin=(0.62, 0.2, 0.1),
                 iris=(0.8, 0.55, 0.25), iris_dark=(0.3, 0.1, 0.03), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.9, ruvido=0.25),
    extra=_scorticano,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(carne=1.0, ferite=[], denti=8))


def _rabbiglio(c):
    """I denti da coniglio (due incisivi piatti davanti di sopra, due più corti sotto che si aprono con la
    mascella) e la schiuma rosa alla bocca: bollicine attorno al taglio della bocca che colano giù dal mento."""
    P, body, sh = c.P, c.body, c.forma
    ang = float(c.specie.opzioni.get('bocca', 22.0))
    R = P.sdf.rot_matrix('y', -ang)
    cerniera = np.array((sh.mouth_t, 0.0, sh.mouth_z1), F)
    giallo = P.materiale('IncisiviConiglio', (0.93, 0.88, 0.72), rough=0.18, coat=0.8, sss=0.15)
    for k, (jaw, lungo) in enumerate((('su', 0.038), ('giu', 0.018))):
        for s in (-1, 1):
            zl = float(body.mouth_line(np.array([0.004], F))[0])
            c0 = np.array((-0.0005, s * 0.0046, zl - lungo * 0.38 if jaw == 'su' else zl + lungo * 0.3), F)
            f0 = P.sdf.box(c0, (0.0034, 0.0042, lungo * 0.5), rounding=0.0016)
            # gli incisivi di sopra sporgono in avanti, come quelli di un coniglio
            f0 = P.sdf.rotate(f0, P.sdf.rot_matrix('y', 24.0 if jaw == 'su' else -10.0), center=(0.004, 0.0, zl))
            if jaw == 'giu':
                f0 = P.sdf.rotate(f0, R, center=cerniera)
                c0 = (c0 - cerniera) @ R.T + cerniera
            c.obs.append(P.oggetto_sdf(f'Incisivo{jaw}{s}', f0, c0 - 0.02, c0 + 0.02, giallo, res=_res(c, 0.0004)))
    # la schiuma: tante bollicine piccole e qualcuna grande sulle labbra e agli angoli della bocca (non davanti
    # agli incisivi), e tre fili di bava schiumosa che pendono dal mento
    rng = np.random.default_rng(8)
    C, Rr = [], []
    for _ in range(150):
        x = rng.uniform(0.012, sh.mouth_t + 0.016)
        zl = float(body.mouth_line(np.array([min(x, sh.mouth_t)], F))[0])
        z = zl + rng.normal(0, 0.0065)
        y = -float(body.surface_y(min(max(x, 0.002), 1.0), z)) - rng.uniform(-0.0008, 0.0035)
        C.append((x, y, z))
        Rr.append(rng.uniform(0.0011, 0.0021) if rng.uniform() < 0.75 else rng.uniform(0.0026, 0.0042))
    for k in range(3):
        x0 = 0.012 + 0.014 * k
        for j in range(7):
            C.append((x0 + rng.normal(0, 0.0012), -0.011 - 0.002 * k + rng.normal(0, 0.001), sh.mouth_z1 - 0.022 - 0.0055 * j - 0.006 * k))
            Rr.append(max(0.0032 - 0.0003 * j, 0.0012))
    C, Rr = np.array(C, F), np.array(Rr, F)
    from scipy.spatial import cKDTree
    albero = cKDTree(C)

    def schiuma(p):
        d, i = albero.query(p, k=4, workers=-1)
        return np.min(d - Rr[i], axis=1).astype(F)
    m, g = P.material('SchiumaRosa')
    co = g.texcoord('Object')
    n = g.noise(co, scale=260.0, detail=2.0)
    col = g.mix(g.smoothstep(0.5, 0.64, n.fac), (0.97, 0.76, 0.78), (0.72, 0.16, 0.2))
    g.output_material(g.principled(color=col, rough=0.1, coat=1.0, coat_rough=0.02, sss=0.6, sss_radius=(1, 0.4, 0.4),
                                   sss_scale=0.002, transmission=0.15))
    c.obs.append(P.oggetto_sdf('Schiuma', schiuma, C.min(0) - 0.006, C.max(0) + 0.006, m, res=_res(c, 0.00035)))


# ── Rabbiglio (pesce coniglio, Siganus luridus) ──
# Ovale alto e compresso, il muso tondo con la boccuccia, l'occhio grande; dorsale lunghissima tutta di spine
# robuste e anale spinosa lunga, coda tronca; bruno-oliva scuro e uniforme. I denti da coniglio e la schiuma
# rosa alla bocca (extra), due morsi aperti sul fianco (la famiglia).
SPECIE['rabbiglio'] = Specie(
    forma=Shape(
        top=[(0, -0.018), (0.02, 0.008), (0.05, 0.045), (0.1, 0.09), (0.18, 0.14), (0.28, 0.18), (0.4, 0.2), (0.54, 0.192),
             (0.68, 0.155), (0.82, 0.1), (0.93, 0.062), (1, 0.052)],
        bot=[(0, -0.036), (0.03, -0.06), (0.1, -0.105), (0.2, -0.152), (0.32, -0.188), (0.45, -0.195), (0.6, -0.17), (0.74, -0.125),
             (0.87, -0.078), (1, -0.052)],
        w=[(0, 0.008), (0.05, 0.026), (0.15, 0.042), (0.35, 0.048), (0.6, 0.04), (0.85, 0.022), (1, 0.013)],
        eye_t=0.155, eye_z=0.05, eye_r=0.03, mouth_t=0.045, mouth_z0=-0.024, mouth_z1=-0.03, gill_t=0.28,
        fins=[Fin('dorsal', 0.26, 0.92, [(0, 0), (0.04, 0.75), (0.12, 0.95), (0.4, 0.9), (0.62, 0.8), (0.66, 0.6), (0.7, 0.85),
                                        (0.85, 0.85), (0.95, 0.6), (1, 0.08)], 0.1, 34, spiny=True),
              Fin('anal', 0.5, 0.92, [(0, 0), (0.05, 0.8), (0.2, 0.9), (0.45, 0.8), (0.5, 0.65), (0.55, 0.85), (0.85, 0.8), (0.95, 0.55),
                                     (1, 0.08)], 0.085, 24, spiny=True),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.55, 0.06, 0.8), 0.24, 18),
              Fin('pectoral', 0.29, 0.305, PETTORALE, 0.13, 10),
              Fin('pelvic', 0.32, 0.335, PELVICA, 0.075, 6, spiny=True)]),
    aspetto=Look(back=(0.09, 0.09, 0.055), flank=(0.24, 0.23, 0.14), belly=(0.48, 0.46, 0.34), fin=(0.2, 0.19, 0.12),
                 iris=(0.82, 0.72, 0.42), iris_dark=(0.2, 0.15, 0.05), metal=0.2, irid=0.2, squame=0.35, linea_laterale=0.5,
                 disegni=[Disegno('marmo', colore=(0.05, 0.05, 0.03), forza=0.5, scala=60, r=0.4)]),
    extra=_rabbiglio,
    famiglia='bleeding', piano='alto',
    opzioni=dict(ferite=[((0.48, 0.45), (0.53, 0.05)), ((0.66, -0.15), (0.7, -0.5))], denti=0, sangue_bocca=False, bocca=24.0))


def _righe_oblique(n, u0, passo, pendenza, v_basso=0.32, v_alto=1.05, larghezza=0.12, colore=(0.01, 0.02, 0.05), forza=0.9):
    """Le righe oblique scure sul dorso (palamita): n linee che salgono verso la coda con la pendenza data (in v per
    unità di u), ognuna tagliata fra v_basso e il dorso con la sua finestra in u."""
    out = []
    for k in range(n):
        uc = u0 + passo * k                    # dove la riga passa a v = 0.6
        out.append(Disegno('linea', colore=colore, forza=forza, v=0.6 - pendenza * uc, inclinazione=pendenza,
                           larghezza=larghezza, u0=uc - (0.6 - v_basso) / pendenza, u1=uc + (v_alto - 0.6) / pendenza))
    return out


def _geo_palamita(c):
    """Lo squarcio dalla testa alla coda: un solco lungo la pelle (catena di coni) largo in mezzo e sottile alle
    punte, e le due file dei fori dei denti, sopra e sotto, tutti in fila."""
    P, body = c.P, c.body
    s = _Scavi(P)
    rng = np.random.default_rng(5)
    ts = np.linspace(0.2, 0.9, 50)
    Q, R, lab_su, lab_giu = [], [], [], []
    A, B, R1, R2 = [], [], [], []
    for i, t in enumerate(ts):
        u = (t - 0.2) / 0.7
        v = 0.06 - 0.3 * u + 0.07 * math.sin(u * 7.0)
        p, n = body.superficie(float(t), v, -1)
        r = (0.0035 + 0.012 * math.sin(math.pi * u) ** 0.6) * (1.0 + 0.3 * math.sin(u * 37.0) * math.sin(u * 13.0))
        Q.append(p - n * r * 0.3)
        R.append(r)
        e1, e2 = _telaio(n)
        lab_su.append(p + e2 * r * 0.9)
        lab_giu.append(p - e2 * r * 0.9)
        if i % 3 == 1 and 0.05 < u < 0.97:
            for verso in (1, -1):
                q = p + e2 * verso * (r + 0.013)
                pp, nn = _pelle_tz(c, float(q[0]), float(q[2]), -1)
                A.append(pp + nn * 0.002)
                B.append(pp - nn * rng.uniform(0.007, 0.01))
                rr = rng.uniform(0.0036, 0.0046)
                R1.append(rr)
                R2.append(rr * 0.22)
    s.solco(Q, R)
    s.coni(A, B, R1, R2)
    s.labbro_giu = lab_giu
    s.labbro_su = lab_su
    s.normali = [body.superficie(float(t), 0.06 - 0.3 * ((t - 0.2) / 0.7) + 0.07 * math.sin((t - 0.2) / 0.7 * 7.0), -1)[1] for t in ts]
    return s


def _campo_palamita(c, f):
    return _cache(c, 'scavi', _geo_palamita).scava(f)


def _palamita(c):
    """La carne viva nello squarcio e nei fori, il sangue che cola dal labbro di sotto, tre denti rotti di quello che
    l'ha morsa rimasti infilati nella carne, le gocce."""
    P = c.P
    s = _cache(c, 'scavi', _geo_palamita)
    _dipingi(c, 'wound', s.carne)
    _dipingi(c, 'mouth', s.scuro(c))
    giu = s.labbro_giu
    _dipingi(c, 'blood', _colature([(giu[i], 0.006, 0.07 + 0.03 * (i % 3), 0.95) for i in range(3, len(giu) - 2, 4)]))
    _dipingi(c, 'blood', _lungo(giu[2:-2], 0.006, 0.8))
    denti = P.dirty_teeth_material()
    for k, i in enumerate((15, 26, 36)):
        p, n = giu[i], s.normali[i]
        e1, e2 = _telaio(n)
        base = p - n * 0.006 + e2 * 0.003
        punta = base + (n * 0.75 + e2 * 0.55 + e1 * 0.2) * 0.022
        c.obs.append(P.tooth(f'DenteRotto{k}', tuple(map(float, base)), tuple(map(float, punta)), 0.0042, denti, col=P.COL))
    for k, i in enumerate((10, 22, 31, 42)):
        c.obs.append(_goccia(c, f'GocciaSquarcio{k}', giu[i] - s.normali[i] * 0.001, 0.026 + 0.01 * (k % 2), r0=0.0017, r1=0.004))


_PINNULA = [(0, 0), (0.25, 1.0), (1, 0.15)]

# ── Palamita Squarciata (palamita, Sarda sarda) ──
# Come il tonno (la prova tonno_di_sangue) ma più slanciata, la bocca più grande; prima dorsale lunga, bassa e
# spinosa, la seconda piccola e falcata, le pinnule scure, la coda a mezzaluna; blu acciaio sopra con le righe
# oblique scure sul dorso, argento sotto. Uno squarcio dalla testa alla coda con i fori dei denti in fila sopra e
# sotto, come un morso enorme, e tre denti rotti rimasti nella carne (campo + extra).
SPECIE['palamita_squarciata'] = Specie(
    forma=Shape(
        top=[(0, -0.008), (0.03, 0.022), (0.08, 0.055), (0.16, 0.088), (0.28, 0.11), (0.4, 0.115), (0.55, 0.102), (0.7, 0.072),
             (0.83, 0.04), (0.93, 0.02), (1, 0.014)],
        bot=[(0, -0.02), (0.04, -0.045), (0.12, -0.078), (0.25, -0.104), (0.4, -0.112), (0.55, -0.1), (0.7, -0.07), (0.83, -0.038),
             (0.93, -0.018), (1, -0.014)],
        w=[(0, 0.006), (0.06, 0.04), (0.2, 0.075), (0.4, 0.082), (0.6, 0.065), (0.8, 0.032), (0.92, 0.016), (1, 0.011)],
        eye_t=0.095, eye_z=0.022, eye_r=0.017, mouth_t=0.115, mouth_z0=-0.012, mouth_z1=-0.03, gill_t=0.22,
        fins=[Fin('dorsal', 0.27, 0.56, [(0, 0), (0.05, 1.0), (0.18, 0.78), (0.5, 0.42), (0.85, 0.22), (1, 0.1)], 0.075, 20, spiny=True),
              Fin('dorsal', 0.58, 0.65, DORSALE_FALCE, 0.075, 10),
              Fin('anal', 0.6, 0.67, DORSALE_FALCE, 0.065, 10)]
             + [Fin('dorsal', 0.68 + 0.036 * i, 0.698 + 0.036 * i, _PINNULA, 0.02, 4) for i in range(8)]
             + [Fin('anal', 0.7 + 0.038 * i, 0.718 + 0.038 * i, _PINNULA, 0.018, 4) for i in range(7)]
             + [Fin('caudal', 1.0, 1.0, coda_falcata(2.7, 0.85, radice=0.3), 0.26, 26),
                Fin('pectoral', 0.23, 0.245, PETTORALE, 0.09, 10),
                Fin('pelvic', 0.27, 0.28, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.02, 0.05, 0.12), flank=(0.38, 0.42, 0.48), belly=(0.74, 0.75, 0.76), fin=(0.09, 0.1, 0.13),
                 iris=(0.6, 0.6, 0.52), iris_dark=(0.08, 0.08, 0.08), metal=0.7, irid=0.4, squame=0.25,
                 disegni=[Disegno('ventre', colore=(0.8, 0.82, 0.84), forza=0.6, v1=-0.35)]
                 + _righe_oblique(9, 0.2, 0.085, 4.0, larghezza=0.16, forza=1.0)),
    campo=_campo_palamita, extra=_palamita,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[], denti=8))


# le morsicature della leccia: una griglia di mezzelune tutte uguali e girate dalla stessa parte (t, v)
_GRIGLIA_LECCIA = [(0.32 + 0.075 * i + (0.0375 if j % 2 else 0.0), v) for j, v in enumerate((0.56, 0.22, -0.12, -0.46))
                   for i in range(8) if 0.3 < 0.32 + 0.075 * i + (0.0375 if j % 2 else 0.0) < 0.88
                   and not (v < -0.1 and 0.32 + 0.075 * i + (0.0375 if j % 2 else 0.0) < 0.43)]


def _geo_leccia(c):
    """Le ferite piccole e regolari: tante mezzelune uguali (una sfera meno la stessa spostata verso la coda),
    poco profonde, in griglia sfalsata su tutto il fianco."""
    P, body = c.P, c.body
    s = _Scavi(P)
    rp, prof = 0.0112, 0.0056
    centri = []
    for t, v in _GRIGLIA_LECCIA:
        p, n = body.superficie(t, v, -1)
        e1, _ = _telaio(n)
        ca = p + n * (rp - prof)
        cb = ca + e1 * rp * 0.75 + n * 0.001

        def g(q, ca=ca, cb=cb):
            return np.maximum(np.linalg.norm(q - ca, axis=1) - rp, -(np.linalg.norm(q - cb, axis=1) - rp)).astype(F)
        s.aggiungi(g, ca - rp - 0.003, ca + rp + 0.003)
        centri.append(p)
    s.centri = centri
    return s


def _campo_leccia(c, f):
    return _cache(c, 'scavi', _geo_leccia).scava(f, k=0.0008)


def _leccia(c):
    """Carne viva nelle mezzelune, una colatura corta sotto ciascuna, le gocce dalla fila di sotto."""
    s = _cache(c, 'scavi', _geo_leccia)
    _dipingi(c, 'wound', s.carne)
    _dipingi(c, 'blood', _colature([(p - np.array((0.0, 0.0, 0.004), F), 0.0034, 0.035, 0.9) for p in s.centri]))
    bassi = [p for p, (t, v) in zip(s.centri, _GRIGLIA_LECCIA) if v < -0.4]
    for k, p in enumerate(bassi[::2]):
        c.obs.append(_goccia(c, f'GocciaMorsetto{k}', p - np.array((0.0, 0.0, 0.006), F), 0.02 + 0.008 * (k % 2), r0=0.0014, r1=0.0032))


# ── Leccia Lacerata (leccia stella, Trachinotus ovatus) ──
# Compressa e ovale-allungata, il muso tondo e corto con la boccuccia; la prima dorsale ridotta a spinette, la
# seconda dorsale e l'anale opposte con il lobo davanti alto, falcato e scuro, la coda profondamente forcuta a
# punte scure; argento con il dorso grigio-azzurro e le macchiette nere sulla linea laterale. Ferite piccole e
# regolari su tutto il corpo: una griglia di morsetti a mezzaluna tutti uguali (campo + extra).
SPECIE['leccia_lacerata'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.02, 0.012), (0.05, 0.048), (0.1, 0.09), (0.18, 0.13), (0.3, 0.165), (0.42, 0.178), (0.56, 0.165),
             (0.7, 0.125), (0.83, 0.075), (0.93, 0.04), (1, 0.032)],
        bot=[(0, -0.045), (0.03, -0.075), (0.1, -0.115), (0.2, -0.15), (0.32, -0.17), (0.45, -0.172), (0.6, -0.15), (0.74, -0.105),
             (0.86, -0.06), (1, -0.032)],
        w=[(0, 0.008), (0.05, 0.03), (0.18, 0.048), (0.4, 0.052), (0.62, 0.042), (0.85, 0.022), (1, 0.012)],
        eye_t=0.115, eye_z=0.035, eye_r=0.025, mouth_t=0.06, mouth_z0=-0.035, mouth_z1=-0.042, gill_t=0.26,
        fins=[Fin('dorsal', 0.36, 0.47, [(0, 0), (0.05, 1.0), (0.12, 0.2), (0.22, 1.0), (0.3, 0.2), (0.42, 1.0), (0.5, 0.2), (0.62, 1.0),
                                        (0.7, 0.2), (0.82, 1.0), (0.9, 0.2), (1, 0.6)], 0.028, 22, spiny=True),
              Fin('dorsal', 0.5, 0.87, [(0, 0), (0.04, 1.0), (0.1, 1.08), (0.2, 0.45), (0.4, 0.3), (0.8, 0.25), (1, 0.05)], 0.17, 26,
                  colore=(0.13, 0.14, 0.17), bordo=(0.02, 0.02, 0.025)),
              Fin('anal', 0.53, 0.87, [(0, 0), (0.04, 1.0), (0.1, 1.05), (0.2, 0.42), (0.4, 0.28), (0.8, 0.24), (1, 0.05)], 0.15, 24,
                  colore=(0.13, 0.14, 0.17), bordo=(0.02, 0.02, 0.025)),
              Fin('caudal', 1.0, 1.0, coda_forcuta(2.1, 0.22, 1.2), 0.25, 22, bordo=(0.03, 0.03, 0.035)),
              Fin('pectoral', 0.27, 0.285, PETTORALE, 0.13, 10),
              Fin('pelvic', 0.33, 0.345, PELVICA, 0.06, 6)]),
    aspetto=Look(back=(0.16, 0.22, 0.27), flank=(0.58, 0.6, 0.62), belly=(0.78, 0.78, 0.76), fin=(0.3, 0.32, 0.35),
                 iris=(0.75, 0.72, 0.6), iris_dark=(0.1, 0.1, 0.08), metal=0.65, irid=0.35,
                 disegni=[Disegno('macchia', colore=(0.015, 0.015, 0.02), forza=0.95, u=0.31, v=0.06, r=0.0115),
                          Disegno('macchia', colore=(0.015, 0.015, 0.02), forza=0.95, u=0.41, v=0.05, r=0.0115),
                          Disegno('macchia', colore=(0.015, 0.015, 0.02), forza=0.95, u=0.51, v=0.04, r=0.011),
                          Disegno('macchia', colore=(0.015, 0.015, 0.02), forza=0.9, u=0.61, v=0.03, r=0.01)]),
    campo=_campo_leccia, extra=_leccia,
    famiglia='bleeding', piano='alto',
    opzioni=dict(ferite=[], denti=6))


def _dente_umano(P, tipo, radice, verso, sc):
    """Un dente da persona: radice sulla gengiva, verso (+1 in su, −1 in giù) dove punta la corona, sc la misura.
    tipo: 'incisivo' (una paletta piatta), 'canino' (un cono), 'premolare' e 'molare' (blocchi con le cuspidi)."""
    r = np.asarray(radice, F)
    up = np.array((0.0, 0.0, float(verso)), F)
    if tipo == 'incisivo':
        h = 0.0062 * sc
        return P.sdf.box(r + up * h, (0.0034 * sc, 0.0016 * sc, h), rounding=0.0013 * sc)
    if tipo == 'canino':
        return P.sdf.round_cone(r, r + up * 0.0145 * sc, 0.0027 * sc, 0.0008 * sc)
    h = (0.0046 if tipo == 'premolare' else 0.0042) * sc
    lato = (0.0034 if tipo == 'premolare' else 0.0046) * sc
    blocco = P.sdf.box(r + up * h, (lato, 0.0034 * sc, h), rounding=0.0019 * sc)
    cuspidi = P.sdf.sphere(r + up * (2.0 * h + 0.0012 * sc), 0.0024 * sc)
    return P.sdf.subtract(blocco, cuspidi, k=0.0008)


def _dentiera(c):
    """Denti da persona di misure diverse, troppi, in fila sulle due mascelle (quelli di sotto si aprono con la
    mascella): incisivi, canini, premolari, molari, qualcuno giallo, uno d'oro; sui denti davanti di sopra, dalla
    parte che si vede, l'apparecchio: le placchette d'acciaio e il filo. Il sangue sulle gengive."""
    P, body, sh = c.P, c.body, c.forma
    ang = float(c.specie.opzioni.get('bocca', 22.0))
    R = P.sdf.rot_matrix('y', -ang)
    cerniera = np.array((sh.mouth_t, 0.0, sh.mouth_z1), F)
    rng = np.random.default_rng(14)
    tipi = ['incisivo', 'incisivo', 'canino', 'premolare', 'premolare', 'molare', 'molare']
    gruppi = {'Smalto': [], 'SmaltoGiallo': [], 'Oro': []}
    staffe = []
    for jaw, verso in (('su', -1), ('giu', 1)):
        for s in (-1, 1):
            n = len(tipi)
            for k, tipo in enumerate(tipi):
                x = 0.01 + (sh.mouth_t - 0.026) * k / (n - 1) + rng.normal(0, 0.0015)
                zl = float(body.mouth_line(np.array([x], F))[0])
                y = s * float(body.surface_y(x, zl)) * 0.7
                radice = np.array((x, y, zl - verso * (0.004 if verso > 0 else 0.0015)), F)
                sc = rng.uniform(0.95, 1.7) * (1.1 if tipo == 'molare' else 1.0)
                f0 = _dente_umano(P, tipo, radice, verso, sc)
                # storti: ognuno girato un po' attorno alla sua radice
                Rs = P.sdf.rot_matrix('x', rng.normal(0, 9)) @ P.sdf.rot_matrix('y', rng.normal(0, 12))
                f0 = P.sdf.rotate(f0, Rs.astype(F), center=radice)
                if jaw == 'giu':
                    f0 = P.sdf.rotate(f0, R, center=cerniera)
                    radice = (radice - cerniera) @ R.T + cerniera
                quale = 'Oro' if (jaw, s, k) == ('giu', -1, 5) else ('SmaltoGiallo' if rng.uniform() < 0.3 else 'Smalto')
                gruppi[quale].append((f0, radice))
                if jaw == 'su' and s == -1 and k < 5:
                    staffe.append(np.array((x, y - 0.0016 * sc - 0.0012, zl - 0.004 - 0.0062 * sc), F))
    colori = {'Smalto': ((0.86, 0.83, 0.74), 0.22), 'SmaltoGiallo': ((0.78, 0.66, 0.4), 0.3), 'Oro': ((0.95, 0.68, 0.25), 0.15)}
    for nome, denti in gruppi.items():
        if not denti:
            continue
        col, rough = colori[nome]
        mat = P.materiale(f'Denti{nome}', col, rough=rough, coat=0.8, metal=1.0 if nome == 'Oro' else 0.0, sss=0.0 if nome == 'Oro' else 0.25)
        C = np.array([r for _, r in denti], F)
        c.obs.append(P.oggetto_sdf(f'DentiUmani{nome}', P.sdf.union(*[f for f, _ in denti]), C.min(0) - 0.03, C.max(0) + 0.03, mat,
                                   res=_res(c, 0.00045)))
    # l'apparecchio: le placchette sui denti davanti di sopra (lato camera) e il filo che le unisce
    acc = _acciaio(c)
    S = np.array(staffe, F)
    placche = P.sdf.union(*[P.sdf.box(p, (0.0028, 0.0012, 0.0028), rounding=0.0006) for p in S])
    filo = _curva(S[0] + np.array((-0.004, 0.0003, 0.0), F), S[1], S[-2], S[-1] + np.array((0.004, 0.0003, 0.0), F), n=24)
    tutto = P.sdf.union(placche, *[P.sdf.capsule(filo[i] - np.array((0, 0.0008, 0), F), filo[i + 1] - np.array((0, 0.0008, 0), F),
                                                 0.0009) for i in range(len(filo) - 1)])
    c.obs.append(P.oggetto_sdf('Apparecchio', tutto, S.min(0) - 0.01, S.max(0) + 0.01, acc, res=_res(c, 0.0003)))
    # il sangue sulle gengive: lungo le due mascelle
    gengive = [_pelle_tz(c, float(x), float(body.mouth_line(np.array([x], F))[0]) + 0.003, -1)[0] for x in np.linspace(0.02, sh.mouth_t, 6)]
    _dipingi(c, 'blood', _colature([(p, 0.005, 0.03, 0.8) for p in gengive]))

    def labbra(V):
        # le gengive dove sono stati piantati i denti: carne viva lungo il taglio della bocca, sulle due mascelle
        x = np.clip(V[:, 0], 0, sh.mouth_t)
        zl = body.mouth_line(x)
        Vg = (V - cerniera) @ R + cerniera                 # la mascella di sotto riportata chiusa
        zlg = body.mouth_line(np.clip(Vg[:, 0], 0, sh.mouth_t))
        su = np.clip(1 - np.abs(V[:, 2] - zl - 0.002) / 0.006, 0, 1) * (V[:, 0] < sh.mouth_t)
        giu = np.clip(1 - np.abs(Vg[:, 2] - zlg + 0.002) / 0.006, 0, 1) * (Vg[:, 0] < sh.mouth_t)
        return (np.maximum(su, giu) * 0.9).astype(F)
    _dipingi(c, 'wound', labbra)


# ── Dentiera (dentice, Dentex dentex) ──
# Sparide robusto e allungato, la testa grande dal profilo convesso, la bocca larga; dorsale lunga spinosa, coda
# forcuta, pettorali lunghe; grigio-rosato e bronzo con i puntini azzurri sul dorso. I denti non sono i suoi: in
# bocca (spalancata) ha denti da persona, troppi e di misure diverse, e su quelli davanti l'apparecchio (extra);
# due tagli della famiglia sul fianco.
SPECIE['dentiera'] = Specie(
    forma=Shape(
        top=[(0, -0.03), (0.02, 0.0), (0.05, 0.04), (0.1, 0.085), (0.17, 0.13), (0.26, 0.163), (0.36, 0.176), (0.5, 0.166),
             (0.65, 0.13), (0.8, 0.085), (0.92, 0.055), (1, 0.048)],
        bot=[(0, -0.05), (0.03, -0.075), (0.1, -0.11), (0.2, -0.145), (0.33, -0.164), (0.47, -0.16), (0.6, -0.14), (0.74, -0.1),
             (0.87, -0.062), (1, -0.048)],
        w=[(0, 0.01), (0.05, 0.04), (0.18, 0.064), (0.38, 0.068), (0.6, 0.055), (0.85, 0.028), (1, 0.016)],
        eye_t=0.16, eye_z=0.072, eye_r=0.026, mouth_t=0.12, mouth_z0=-0.035, mouth_z1=-0.052, gill_t=0.3,
        fins=[Fin('dorsal', 0.32, 0.84, [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.82), (0.8, 0.72), (0.95, 0.5), (1, 0.05)], 0.11, 24,
                  spiny=True),
              Fin('anal', 0.62, 0.84, [(0, 0), (0.12, 0.9), (0.6, 0.6), (0.95, 0.5), (1, 0.05)], 0.08, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.55, 0.3), 0.26, 20),
              Fin('pectoral', 0.3, 0.32, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.2, 12),
              Fin('pelvic', 0.35, 0.37, PELVICA, 0.1, 7, spiny=True)]),
    aspetto=Look(back=(0.26, 0.19, 0.18), flank=(0.6, 0.5, 0.46), belly=(0.8, 0.74, 0.7), fin=(0.55, 0.42, 0.38),
                 iris=(0.75, 0.6, 0.35), iris_dark=(0.2, 0.12, 0.05), metal=0.4, irid=0.3,
                 disegni=[Disegno('macchie', colore=(0.16, 0.38, 0.85), forza=1.0, scala=50, r=0.18, v0=0.15, u0=0.12, u1=0.85)]),
    extra=_dentiera,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[((0.5, 0.4), (0.56, -0.05)), ((0.68, 0.3), (0.71, -0.2))], denti=0, bocca=36.0))


def _grondongo(c):
    """Gronda sangue da tutto il corpo: tante colature dal dorso al ventre su tutto il fianco, il corpo bagnato di
    sangue sotto, e una fila di gocce che pendono dal ventre per tutta la lunghezza."""
    body = c.body
    rng = np.random.default_rng(21)
    sorgenti = []
    for t in np.arange(0.1, 0.96, 0.028):
        t = float(t + rng.normal(0, 0.006))
        p, _ = body.superficie(t, float(rng.uniform(0.2, 0.85)), -1)
        sorgenti.append((p, rng.uniform(0.003, 0.0055), rng.uniform(0.05, 0.09), rng.uniform(0.7, 1.0)))
    _dipingi(c, 'blood', _colature(sorgenti, seme=2.0))

    def bagnato(V):
        zc, h, _ = body.section(np.clip(V[:, 0], 0, 1))
        v = (V[:, 2] - zc) / h
        return (np.clip((-0.3 - v) / 0.5, 0, 1) * 0.8 * (V[:, 0] > 0.08)).astype(F)
    _dipingi(c, 'blood', bagnato)
    for k, t in enumerate(np.arange(0.12, 0.95, 0.055)):
        p, _ = body.superficie(float(t + rng.normal(0, 0.008)), -0.97, -1)
        c.obs.append(_goccia(c, f'Grondante{k}', p, float(rng.uniform(0.015, 0.05)), r0=0.0014, r1=float(rng.uniform(0.0028, 0.004))))


# ── Grondongo (grongo, Conger conger) ──
# Grosso e cilindrico, lunghissimo; la testa conica con la mascella di sopra più lunga, gli occhi grandi, le
# pettorali ben sviluppate; la dorsale comincia sopra la punta delle pettorali e corre fino alla coda insieme
# all'anale, le pinne chiare con l'orlo nero; grigio scuro sopra, più chiaro sotto, i pori bianchi della linea
# laterale. Esce dall'acqua grondando sangue (extra) e le ferite della famiglia lungo il corpo.
SPECIE['grondongo'] = Specie(
    forma=Shape(
        top=[(0, -0.002), (0.012, 0.01), (0.03, 0.02), (0.05, 0.027), (0.08, 0.032), (0.12, 0.036), (0.25, 0.038), (0.5, 0.036),
             (0.7, 0.03), (0.85, 0.022), (0.95, 0.011), (1, 0.003)],
        bot=[(0, -0.006), (0.015, -0.013), (0.04, -0.022), (0.08, -0.028), (0.15, -0.033), (0.3, -0.035), (0.55, -0.033),
             (0.75, -0.026), (0.9, -0.014), (1, -0.003)],
        w=[(0, 0.004), (0.03, 0.014), (0.08, 0.024), (0.2, 0.03), (0.45, 0.028), (0.7, 0.02), (0.88, 0.011), (1, 0.003)],
        eye_t=0.038, eye_z=0.012, eye_r=0.0085, mouth_t=0.055, mouth_z0=-0.0035, mouth_z1=-0.008,
        branchie='pori', n_branchie=1, gill_t=0.118,
        fins=[Fin('pectoral', 0.125, 0.135, [(0, 0), (0.4, 0.32), (0.85, 0.25), (1, 0.05), (0.8, -0.12), (0, -0.08)], 0.045, 12, z=0.0,
                  colore=(0.42, 0.42, 0.42), bordo=(0.03, 0.03, 0.035)),
              Fin('dorsal', 0.17, 1.0, [(0, 0), (0.03, 0.6), (0.1, 0.85), (0.5, 0.95), (0.9, 1.0), (1, 0.7)], 0.026, 150,
                  colore=(0.4, 0.4, 0.4), bordo=(0.02, 0.02, 0.025)),
              Fin('anal', 0.4, 1.0, [(0, 0), (0.04, 0.7), (0.2, 0.9), (0.9, 1.0), (1, 0.7)], 0.022, 120,
                  colore=(0.42, 0.42, 0.42), bordo=(0.02, 0.02, 0.025)),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.9, 1.0), 0.03, 20, colore=(0.4, 0.4, 0.4), bordo=(0.02, 0.02, 0.025))],
        piega=[(0, -8), (0.25, 10), (0.5, -10), (0.75, 12), (1.0, -4)]),
    aspetto=Look(back=(0.07, 0.07, 0.075), flank=(0.15, 0.15, 0.155), belly=(0.36, 0.35, 0.33), fin=(0.4, 0.4, 0.4),
                 iris=(0.55, 0.52, 0.42), iris_dark=(0.08, 0.08, 0.07), metal=0.1, irid=0.1, squame=0.0, linea_laterale=0.0,
                 lucido=0.75, ruvido=0.3,
                 disegni=[Disegno('linea', colore=(0.72, 0.72, 0.7), forza=0.85, v=0.05, larghezza=0.05, n=110, u0=0.13, u1=0.95)]),
    extra=_grondongo,
    famiglia='bleeding', piano='anguilliforme',
    opzioni=dict(ferite=[((0.22, 0.6), (0.27, -0.2)), ((0.42, 0.5), (0.47, -0.4)), ((0.63, 0.55), (0.67, -0.25)),
                         ((0.82, 0.4), (0.85, -0.3))], denti=7))


def _lampreda(c):
    """Il disco insanguinato: la conca di carne viva, il sangue sull'orlo e sul muso che scende lungo la gola, i
    denti gialli diventati sporchi, due fili di bava rossa attraverso il disco e le gocce dall'orlo di sotto."""
    P, body = c.P, c.body
    do = c.forma.disco_orale
    C, n, e1, e2 = P._disco_orale_telaio(body)
    R0 = do.raggio
    S = C + n * R0 * 0.95

    def conca(V):
        d = np.linalg.norm(V - S, axis=1)
        return (np.clip((R0 * 1.12 - d) / 0.004, 0, 1) * (((V - C) @ n) > -R0 * 0.25)).astype(F)

    def orlo(V):
        d = np.linalg.norm(V - C, axis=1)
        return np.clip(1.25 - d / (R0 * 1.25), 0, 1).astype(F) * 1.6
    _dipingi(c, 'wound', conca)
    _dipingi(c, 'blood', orlo)
    gola = [body.superficie(t, -0.75, -1)[0] for t in (0.03, 0.06, 0.1, 0.15, 0.2)]
    _dipingi(c, 'blood', _lungo(gola, 0.01, 0.9))
    _dipingi(c, 'blood', _colature([(p, 0.006, 0.05, 0.8) for p in gola[1:4]]))
    for o in c.obs:
        if o.name.startswith('DentiDiscoOrale'):
            o.data.materials[0] = P.dirty_teeth_material()
    giu = np.array((0.0, 0.0, -1.0), F)
    giu = giu - n * float(giu @ n)
    giu /= np.linalg.norm(giu)
    for k, a in enumerate((-0.45, 0.0, 0.4)):
        lato = np.cross(n, giu)
        p = C + (giu * math.cos(a) + lato * math.sin(a)) * R0 * 0.98 + n * R0 * 0.1
        c.obs.append(_goccia(c, f'GocciaDisco{k}', p, 0.03 + 0.012 * (k % 2), r0=0.0018, r1=0.0042))
    bava = P.blood_material()
    for k, (a0, a1) in enumerate(((2.3, -0.6), (1.2, -1.9))):
        pa = S - n * R0 * 0.5 + (e1 * math.cos(a0) + e2 * math.sin(a0)) * R0 * 0.62
        pb = S - n * R0 * 0.5 + (e1 * math.cos(a1) + e2 * math.sin(a1)) * R0 * 0.62
        f = P.strand(pa, pb, 0.008, r=0.0012)
        lo, hi = np.minimum(pa, pb) - 0.02, np.maximum(pa, pb) + 0.02
        c.obs.append(P.oggetto_sdf(f'BavaRossa{k}', f, lo, hi, bava, res=_res(c, 0.0004)))


# ── Lampreda Vampira (lampreda di mare, Petromyzon marinus) — la prova del disco orale, trasformata ──
# Al posto della bocca la ventosa rotonda con gli anelli di denti (Shape.disco_orale); sette pori branchiali
# tondi; due dorsali, la seconda unita alla coda. Il ritratto gira la testa verso la camera per far vedere il disco.
# Il disco è insanguinato e i denti sporchi (extra); la bocca della famiglia resta chiusa (non ce l'ha).
SPECIE['lampreda_vampira'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.03, 0.012), (0.08, 0.026), (0.2, 0.034), (0.5, 0.036), (0.75, 0.03), (0.9, 0.018), (1, 0.004)],
        bot=[(0, -0.03), (0.04, -0.034), (0.1, -0.034), (0.3, -0.036), (0.6, -0.034), (0.85, -0.022), (1, -0.004)],
        w=[(0, 0.02), (0.05, 0.027), (0.2, 0.031), (0.5, 0.029), (0.75, 0.02), (0.9, 0.01), (1, 0.003)],
        eye_t=0.075, eye_z=0.013, eye_r=0.009, bocca='nessuna',
        disco_orale=DiscoOrale(raggio=0.03, anelli=4, denti=14, inclinazione=40.0),
        branchie='pori', n_branchie=7, gill_t=0.11, passo_branchie=0.016,
        fins=[Fin('dorsal', 0.56, 0.67, [(0, 0), (0.2, 0.9), (0.6, 1.0), (1, 0.15)], 0.026, 16),
              Fin('dorsal', 0.71, 1.0, [(0, 0), (0.1, 0.8), (0.4, 1.0), (0.85, 0.8), (1, 0.6)], 0.032, 36),
              Fin('anal', 0.9, 1.0, [(0, 0), (0.3, 0.7), (1, 0.6)], 0.012, 10),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.9, 1.0), 0.045, 14)],
        piega=[(0, 14), (0.3, -10), (0.65, 12), (1.0, -8)]),
    aspetto=Look(back=(0.2, 0.18, 0.12), flank=(0.3, 0.27, 0.19), belly=(0.62, 0.57, 0.46), fin=(0.25, 0.22, 0.16),
                 iris=(0.7, 0.62, 0.35), iris_dark=(0.15, 0.12, 0.05), metal=0.0, irid=0.05, squame=0.0, linea_laterale=0.0,
                 lucido=0.65, ruvido=0.3,
                 disegni=[Disegno('marmo', colore=(0.06, 0.05, 0.035), forza=0.8, scala=22, r=0.55)]),
    ritratto=Ritratto(yaw=38.0, pitch=10.0),
    extra=_lampreda,
    famiglia='bleeding', piano='anguilliforme',
    opzioni=dict(ferite=[((0.4, 0.5), (0.44, -0.2))], bocca=0))


def _geo_violino(c):
    """I due tagli di traverso sul dorso, da cui escono le corde: uno dietro gli occhi (il capotasto), uno all'attacco
    della coda (la cordiera)."""
    P, body = c.P, c.body
    s = _Scavi(P)
    s.tagli = []
    for t, mezza in ((0.085, 0.018), (0.56, 0.026)):
        zc, h, _ = _sezione(c, t)
        Q, R = [], []
        for z in np.linspace(-mezza, mezza, 13):
            p, n = body.superficie(t, (z - zc) / h, -1)
            u = (z + mezza) / (2 * mezza)
            r = 0.002 + 0.0048 * math.sin(math.pi * u) ** 0.5
            Q.append(p - n * r * 0.35)
            R.append(r)
        s.solco(Q, R)
        s.tagli.append(Q)
    return s


def _campo_violino(c, f):
    return _con_pinne_razza(c, _cache(c, 'scavi', _geo_violino).scava(f, k=0.001))


def _violino(c):
    """Le corde: quattro nervi tesi da un taglio all'altro, sollevati da un ponticello d'osso piantato sul dorso;
    la carne viva nei tagli e il sangue attorno."""
    P, body = c.P, c.body
    s = _cache(c, 'scavi', _geo_violino)
    _dipingi(c, 'wound', s.carne)
    t1, t2, tp = 0.085, 0.56, 0.36
    ponte_h = 0.011
    nervi = P.materiale('Nervi', (0.86, 0.8, 0.6), rough=0.22, coat=0.9, sss=0.35)
    osso = P.bone_material()
    A, B, R1, R2 = [], [], [], []
    for z in (-0.0096, -0.0032, 0.0032, 0.0096):
        pa, na = _pelle_tz(c, t1, z, -1)
        pb, nb = _pelle_tz(c, t2, z, -1)
        pp, npn = _pelle_tz(c, tp, z, -1)
        a = pa - na * 0.003
        top = pp + npn * (ponte_h + 0.0012)
        b = pb - nb * 0.003
        for u, v in ((a, top), (top, b)):
            A.append(u)
            B.append(v)
            R1.append(0.0017)
            R2.append(0.0017)
    f, lo, hi = P.campo_coni(A, B, R1, R2)
    c.obs.append(P.oggetto_sdf('Corde', f, lo, hi, nervi, res=_res(c, 0.0004)))
    # gocce di sangue lungo le corde, come perline
    rng = np.random.default_rng(2)
    perle = []
    for a, b in zip(A, B):
        for u in rng.uniform(0.15, 0.85, 2):
            perle.append(a + (b - a) * u + np.array((0.0, 0.0, -0.0012), F))
    fp, lo, hi = P.campo_sfere(perle, 0.0026)
    c.obs.append(P.oggetto_sdf('PerleDiSangue', fp, lo, hi, P.blood_material(), res=_res(c, 0.0004)))
    # il ponticello: una lastrina d'osso ritta sul dorso, con l'arco sotto (due piedi) e le tacche in cima
    pc, nc = _pelle_tz(c, tp, 0.0, -1)
    centro = pc + nc * ponte_h * 0.5
    ex = np.array((1.0, 0.0, 0.0), F)

    def ponte(p):
        q = p - centro
        qx, qn = q @ ex, q @ nc
        qz = q[:, 2]
        lastra = np.maximum(np.maximum(np.abs(qx) - 0.0014, np.abs(qn) - ponte_h * 0.5), np.abs(qz) - 0.017)
        arco = np.sqrt((qz / 0.011) ** 2 + ((qn + ponte_h * 0.5) / (ponte_h * 0.62)) ** 2) - 1.0
        return np.maximum(lastra, -arco * 0.006).astype(F)
    c.obs.append(P.oggetto_sdf('Ponticello', ponte, centro - 0.025, centro + 0.025, osso, res=_res(c, 0.0004)))
    macchie = [(q, 0.009, 0.03, 1.0) for Q in s.tagli for q in Q[1:-1:2]]
    _dipingi(c, 'blood', _colature(macchie, lato=0))
    for Q in s.tagli:
        _dipingi(c, 'blood', _lungo(Q, 0.016, 0.9, lato=0))


# ── Pesce Violento (pesce violino, Rhinobatos rhinobatos) ──
# Visto dall'alto come le razze (dorso verso −Y). Il disco a cuneo con il muso appuntito (testa e pettorali fuse
# fino a un terzo del corpo), le pinne ventrali piccole dietro, il tronco e la coda grossi da squalo con due
# dorsali grandi e la caudale; bruno sabbia sopra, bianco sotto. Ha la forma di un violino: sul dorso quattro
# corde (i suoi nervi) tese da un taglio all'altro sopra un ponticello d'osso (campo + extra).
SPECIE['pesce_violento'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.03, 0.012), (0.08, 0.025), (0.15, 0.04), (0.25, 0.052), (0.38, 0.058), (0.5, 0.056), (0.62, 0.05),
             (0.75, 0.042), (0.88, 0.032), (1, 0.024)],
        bot=[(0, 0.0), (0.03, -0.012), (0.08, -0.025), (0.15, -0.04), (0.25, -0.052), (0.38, -0.058), (0.5, -0.056), (0.62, -0.05),
             (0.75, -0.042), (0.88, -0.032), (1, -0.024)],
        w=[(0, 0.003), (0.06, 0.01), (0.15, 0.02), (0.3, 0.03), (0.45, 0.034), (0.6, 0.032), (0.8, 0.025), (1, 0.017)],
        eye_t=0.13, eye_z=0.0, eye_r=0.009,
        occhi=[(0.13, 0.022, 0.0088, -1), (0.13, -0.022, 0.0088, -1)], spiracoli=0.0055,
        bocca='nessuna', branchie='nessuna',
        disco=Disco(contorno=[(0, 0.0), (0.04, 0.034), (0.1, 0.074), (0.16, 0.108), (0.22, 0.136), (0.27, 0.15), (0.31, 0.145),
                              (0.35, 0.112), (0.38, 0.078), (0.41, 0.072), (0.45, 0.082), (0.49, 0.078), (0.52, 0.05), (0.55, 0.0),
                              (1.0, 0.0)],
                    spessore=[(0, 0.003), (0.1, 0.008), (0.25, 0.012), (0.4, 0.01), (0.52, 0.004), (1.0, 0.001)]),
        fins=[Fin('dorsal', 0.6, 0.69, DORSALE_SQUALO, 0.14, 24, carnosa=True, spessore=0.006),
              Fin('dorsal', 0.79, 0.88, DORSALE_SQUALO, 0.125, 24, carnosa=True, spessore=0.005),
              Fin('caudal', 1.0, 1.0, coda_eterocerca(lobo=1.0, alzata=1.2, lobo_basso=0.5, basso=0.9), 0.25, 40,
                  carnosa=True, spessore=0.006)]),
    aspetto=Look(back=(0.15, 0.11, 0.065), flank=(0.19, 0.145, 0.09), belly=(0.82, 0.8, 0.74), fin=(0.065, 0.045, 0.028),
                 iris=(0.6, 0.55, 0.35), iris_dark=(0.12, 0.1, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.35, ruvido=0.5,
                 disegni=[Disegno('marmo', colore=(0.08, 0.06, 0.035), forza=0.55, scala=60, r=0.35),
                          Disegno('macchie', colore=(0.5, 0.42, 0.3), forza=0.45, scala=70, r=0.12, seme=4)]),
    campo=_campo_violino, extra=_violino,
    ritratto=Ritratto(yaw=4.0, pitch=0.0, roll=-42.0),
    famiglia='bleeding', piano='razza',
    opzioni=dict(ferite=[], bocca=0))


def _geo_pilota(c):
    """Il morso grande: una sfera che porta via un pezzo del dorso e del fianco (spostata verso la camera, così la
    carne si vede), con il bordo smerlato dai denti triangolari di chi l'ha morso."""
    P, body = c.P, c.body
    s = _Scavi(P)
    t0, R = 0.36, 0.1
    ztop = float(body.top(np.array([t0], F))[0])
    centro = np.array((t0, -0.042, ztop + 0.018), F)
    s.sfera(centro, R)
    # le tacche dei denti lungo l'orlo (dove la sfera taglia la pelle): coni corti che entrano nella carne
    rng = np.random.default_rng(3)
    A, B, R1, R2 = [], [], [], []
    orlo = []
    for a in np.linspace(0.0, 2 * math.pi, 64, endpoint=False):
        q = centro + R * np.array((math.cos(a), 0.0, math.sin(a)), F) * 0.98
        if q[2] > ztop + 0.002:
            continue
        p, n = _pelle_tz(c, float(q[0]), float(q[2]), -1)
        if np.linalg.norm(p - centro) > R * 1.05:
            continue
        orlo.append(p)
    for k, p in enumerate(orlo[::3]):
        d = (centro - p) / (np.linalg.norm(centro - p) + 1e-9)
        A.append(p - d * 0.006)
        B.append(p + d * 0.01)
        R1.append(rng.uniform(0.0045, 0.006))
        R2.append(0.0008)
    if A:
        s.coni(B, A, R2, R1)
    s.orlo = orlo
    s.centro = centro
    return s


def _campo_pilota(c, f):
    return _cache(c, 'scavi', _geo_pilota).scava(f, k=0.0015)


def _pilota(c):
    """La carne viva nel morso, il sangue che cola dall'orlo di sotto lungo il fianco, le gocce."""
    s = _cache(c, 'scavi', _geo_pilota)
    _dipingi(c, 'wound', s.carne)
    _dipingi(c, 'mouth', s.scuro(c))
    bassi = sorted(s.orlo, key=lambda p: p[2])[:8]
    _dipingi(c, 'blood', _colature([(p, 0.007, 0.11, 1.0) for p in bassi[::2]]))
    for k, p in enumerate(bassi[::3]):
        c.obs.append(_goccia(c, f'GocciaMorso{k}', p, 0.028 + 0.012 * k, r0=0.0018, r1=0.0042))


# ── Pilota Sanguinante (pesce pilota, Naucrates ductor) ──
# Affusolato, il muso corto e tondo con la boccuccia; la prima dorsale ridotta a spinette (qui le ha portate
# via il morso), la seconda dorsale e l'anale con il lobo davanti, la coda forcuta con le punte bianche;
# argento azzurrato con 6 larghe bande verticali blu-nere. Un morso enorme gli ha portato via un pezzo del
# dorso (campo + extra), e quello che lo accompagna lo morde ancora.
SPECIE['pilota_sanguinante'] = Specie(
    forma=Shape(
        top=[(0, -0.015), (0.02, 0.012), (0.05, 0.04), (0.1, 0.068), (0.18, 0.096), (0.3, 0.115), (0.42, 0.118), (0.55, 0.108),
             (0.7, 0.08), (0.84, 0.045), (0.94, 0.024), (1, 0.02)],
        bot=[(0, -0.035), (0.03, -0.06), (0.1, -0.088), (0.2, -0.108), (0.33, -0.118), (0.48, -0.112), (0.62, -0.09), (0.76, -0.06),
             (0.88, -0.032), (1, -0.02)],
        w=[(0, 0.01), (0.05, 0.035), (0.18, 0.055), (0.4, 0.058), (0.65, 0.045), (0.85, 0.024), (1, 0.012)],
        eye_t=0.085, eye_z=0.018, eye_r=0.019, mouth_t=0.06, mouth_z0=-0.025, mouth_z1=-0.035, gill_t=0.22,
        fins=[Fin('dorsal', 0.47, 0.82, [(0, 0), (0.06, 0.9), (0.15, 1.0), (0.3, 0.6), (0.7, 0.45), (1, 0.08)], 0.09, 24),
              Fin('anal', 0.58, 0.82, [(0, 0), (0.08, 0.9), (0.2, 0.95), (0.35, 0.55), (0.7, 0.42), (1, 0.08)], 0.075, 18),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.75, 0.28), 0.25, 20, bordo=(0.8, 0.8, 0.78)),
              Fin('pectoral', 0.23, 0.245, PETTORALE, 0.1, 10),
              Fin('pelvic', 0.3, 0.315, PELVICA, 0.07, 6, colore=(0.05, 0.06, 0.09))]),
    aspetto=Look(back=(0.12, 0.15, 0.22), flank=(0.44, 0.48, 0.54), belly=(0.7, 0.72, 0.74), fin=(0.12, 0.13, 0.18),
                 iris=(0.65, 0.65, 0.6), iris_dark=(0.08, 0.08, 0.1), metal=0.5, irid=0.3,
                 disegni=[Disegno('bande', colore=(0.03, 0.04, 0.08), forza=0.92, n=6, u0=0.2, u1=0.97, larghezza=0.5, onda=0.04)]),
    campo=_campo_pilota, extra=_pilota,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[((0.62, 0.2), (0.66, -0.3))], denti=5))


def _remora(c):
    """Il lembo di pelle grigia di Gulpy rimasto attaccato alla ventosa: un foglio sottile che segue il capo, scende
    sul fianco verso la camera e dietro si stacca e si arriccia, con l'orlo strappato. Sangue attorno all'orlo."""
    P, body = c.P, c.body
    base = body.base()
    n3 = P.sdf.Noise3(41)

    def lembo(p):
        x = p[:, 0]
        alza = 0.02 * np.clip((x - 0.215) / 0.06, 0, 1) ** 2
        guscio = np.abs(base(p) - 0.0022 - alza) - 0.0013
        zc, h, _ = body.section(np.clip(x, 0, 1))
        ang = np.arctan2(-p[:, 1], p[:, 2] - zc)              # 0 in cima, + verso il fianco sinistro
        frast = n3(p, scale=0.012, octaves=3)
        dentro = np.maximum(np.abs(x - 0.2) - 0.066 - 0.016 * frast, (np.abs(ang - 0.3) - 0.85 - 0.3 * frast) * 0.045)
        return np.maximum(guscio, dentro).astype(F)
    m, g = P.material('PelleDiGulpy')
    co = g.texcoord('Object')
    big = g.noise(co, scale=40.0, detail=6.0, rough=0.6, distortion=0.4)
    col = g.mix(g.smoothstep(0.42, 0.68, big.fac), (0.1, 0.11, 0.1), (0.03, 0.036, 0.032))
    mid = g.noise(co, scale=160.0, detail=4.0)
    col = g.mix(g.mul(g.smoothstep(0.55, 0.72, mid.fac), 0.55), col, (0.2, 0.21, 0.19))
    pori = g.noise(co, scale=900.0, detail=2.0)
    g.output_material(g.principled(color=col, rough=0.62, coat=0.35, coat_rough=0.1, sss=0.1, sss_radius=(1, 0.38, 0.22),
                                   sss_scale=0.002, normal=g.bump(g.add(pori.fac, g.mul(mid.fac, 0.5)), strength=0.35, distance=0.0008)))
    lo = np.array((0.02, -0.08, -0.02), F)
    hi = np.array((0.3, 0.06, 0.1), F)
    c.obs.append(P.oggetto_sdf('LemboGulpy', lembo, lo, hi, m, res=_res(c, 0.0005)))
    # il sangue sotto l'orlo strappato e sul capo
    orlo = [body.superficie(t, v, -1)[0] for t, v in ((0.135, 0.45), (0.16, 0.25), (0.2, 0.15), (0.24, 0.3), (0.27, 0.6))]
    _dipingi(c, 'blood', _colature([(p, 0.007, 0.06, 1.0) for p in orlo]))


# ── Remora Strappata (remora, Remora remora) — la prova della ventosa, trasformata ──
# Il disco adesivo con le lamelle sta sul capo piatto (Shape.ventosa); il ritratto mostra un po' il dorso.
# Strappata via da Gulpy: sulla ventosa le è rimasto un lembo della sua pelle grigia (extra); i tagli e la bocca
# aperta della famiglia.
SPECIE['remora_strappata'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.02, 0.01), (0.06, 0.03), (0.12, 0.042), (0.2, 0.047), (0.28, 0.049), (0.4, 0.052), (0.6, 0.048),
             (0.8, 0.032), (0.95, 0.02), (1, 0.017)],
        bot=[(0, -0.02), (0.03, -0.033), (0.1, -0.048), (0.3, -0.06), (0.5, -0.058), (0.7, -0.045), (0.9, -0.024), (1, -0.017)],
        w=[(0, 0.008), (0.05, 0.03), (0.15, 0.045), (0.35, 0.048), (0.6, 0.04), (0.85, 0.022), (1, 0.012)],
        eye_t=0.1, eye_z=0.01, eye_r=0.012, mouth_t=0.06, mouth_z0=-0.013, mouth_z1=-0.015, gill_t=0.21,
        ventosa=Ventosa(t0=0.035, t1=0.27, larghezza=0.034, lamelle=18),
        fins=[Fin('dorsal', 0.55, 0.8, [(0, 0), (0.08, 1.0), (0.25, 0.7), (0.9, 0.5), (1, 0.05)], 0.05, 22),
              Fin('anal', 0.56, 0.8, [(0, 0), (0.08, 1.0), (0.25, 0.7), (0.9, 0.5), (1, 0.05)], 0.05, 22),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.6, 0.25, 0.85), 0.16, 16),
              Fin('pectoral', 0.22, 0.23, PETTORALE, 0.08, 10, z=0.25),
              Fin('pelvic', 0.25, 0.26, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.16, 0.15, 0.14), flank=(0.2, 0.19, 0.18), belly=(0.24, 0.23, 0.21), fin=(0.15, 0.14, 0.13),
                 iris=(0.6, 0.55, 0.4), iris_dark=(0.12, 0.1, 0.06), metal=0.15, irid=0.1, squame=0.4),
    ritratto=Ritratto(yaw=12.0, pitch=-2.0, roll=40.0),
    extra=_remora,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[((0.4, 0.3), (0.46, -0.35)), ((0.62, 0.4), (0.66, -0.2))], denti=6))


def _geo_verdesca(c):
    """Tre squarci paralleli e profondi sul fianco, come quelli di un'elica: solchi lungo la pelle, larghi in mezzo."""
    P, body = c.P, c.body
    s = _Scavi(P)
    s.squarci = []
    n3 = P.sdf.Noise3(9)
    for k, t0 in enumerate((0.4, 0.475, 0.55)):
        Q, R, bordo = [], [], []
        for u in np.linspace(0, 1, 22):
            t = t0 + 0.07 * u
            v = 0.62 - 1.2 * u
            p, n = body.superficie(float(t), float(v), -1)
            r = 0.0035 + 0.0095 * math.sin(math.pi * u) ** 0.6 * (1 + 0.25 * float(n3(p[None], scale=0.01)[0]))
            Q.append(p - n * r * 0.25)
            R.append(r)
            bordo.append(p)
        s.solco(Q, R)
        s.squarci.append(bordo)
    return s


def _campo_verdesca(c, f):
    return _cache(c, 'scavi', _geo_verdesca).scava(f)


def _verdesca(c):
    """La carne viva negli squarci e il sangue che ne esce e scende sul ventre bianco fino a gocciolare; i denti a
    triangolo, sporchi, lungo la bocca sotto il muso, e il sangue sul mento."""
    P, body, sh = c.P, c.body, c.forma
    s = _cache(c, 'scavi', _geo_verdesca)
    _dipingi(c, 'wound', s.carne)
    _dipingi(c, 'mouth', s.scuro(c))
    sorgenti = []
    for bordo in s.squarci:
        for p in bordo[4:-1:3]:
            sorgenti.append((p, 0.0075, 0.13, 1.0))
    _dipingi(c, 'blood', _colature(sorgenti))
    for k, bordo in enumerate(s.squarci):
        c.obs.append(_goccia(c, f'GocciaSquarcio{k}', bordo[-2], 0.03 + 0.012 * k, r0=0.0019, r1=0.0045))
    ventre = [body.superficie(t, -0.98, -1)[0] for t in (0.47, 0.53, 0.6, 0.66)]
    for k, p in enumerate(ventre):
        c.obs.append(_goccia(c, f'GocciaVentre{k}', p, 0.02 + 0.015 * (k % 2), r0=0.0016, r1=0.0038))
    # i denti: lungo la mezzaluna della bocca sotto il muso, triangoli che pendono
    denti = P.dirty_teeth_material()
    A, B, R1, R2 = [], [], [], []
    for s_ in np.linspace(-0.9, 0.9, 15):
        x = sh.mouth_a + (sh.mouth_t - sh.mouth_a) * s_ * s_
        zc, h, w = _sezione(c, x)
        y = s_ * w * 0.82
        z = zc - h * math.sqrt(max(1 - (y / w) ** 2, 0.0)) + 0.0006
        if abs(s_) > 0.7:
            z = z + (sh.mouth_z1 - z) * ((abs(s_) - 0.7) / 0.3) ** 2
        base = np.array((x, y, z + 0.0015), F)
        ln = 0.0075 * (1.0 - 0.35 * abs(s_))
        A.append(base)
        B.append(base + np.array((-0.0015, 0.0, -ln), F))
        R1.append(0.0024 * (1.0 - 0.3 * abs(s_)))
        R2.append(0.0004)
    f, lo, hi = P.campo_coni(A, B, R1, R2)
    c.obs.append(P.oggetto_sdf('DentiVerdesca', f, lo, hi, denti, res=_res(c, 0.0004)))
    mento, _ = body.superficie(sh.mouth_a + 0.01, -0.95, -1)
    _dipingi(c, 'blood', _colature([(mento, 0.008, 0.03, 0.9)]))
    c.obs.append(_goccia(c, 'GocciaBocca', mento, 0.035, r0=0.0018, r1=0.0042))


# ── Verdesca Ferita (verdesca, Prionace glauca) — la prova della coda eterocerca (piano 'squalo'), trasformata ──
# Lo squalo di sempre: slanciatissimo, muso lungo e appuntito, occhio grande; le pettorali lunghissime a falce,
# la prima dorsale arretrata, la coda eterocerca dell'aiuto comune (coda_eterocerca); indaco sopra, bianco sotto.
# Il sangue era il suo: tre squarci profondi e paralleli sul fianco (campo + extra), i denti sporchi sotto il muso
# (la bocca ventrale resta chiusa: i denti sono un extra).
SPECIE['verdesca_ferita'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.02, 0.01), (0.06, 0.026), (0.12, 0.042), (0.22, 0.057), (0.36, 0.065), (0.5, 0.06), (0.65, 0.046),
             (0.8, 0.03), (0.92, 0.019), (1, 0.015)],
        bot=[(0, -0.01), (0.03, -0.02), (0.08, -0.032), (0.18, -0.048), (0.32, -0.059), (0.46, -0.056), (0.6, -0.044),
             (0.75, -0.028), (0.9, -0.017), (1, -0.015)],
        w=[(0, 0.004), (0.04, 0.02), (0.12, 0.038), (0.3, 0.05), (0.5, 0.045), (0.7, 0.031), (0.9, 0.017), (1, 0.011)],
        eye_t=0.072, eye_z=0.006, eye_r=0.0155,
        bocca='ventrale', mouth_a=0.075, mouth_t=0.118, mouth_z1=-0.026, mouth_z0=-0.026,
        branchie='fessure', gill_t=0.165, n_branchie=5, passo_branchie=0.016,
        fins=[Fin('dorsal', 0.42, 0.52, DORSALE_SQUALO, 0.085, 30, carnosa=True, spessore=0.006),
              Fin('dorsal', 0.83, 0.855, DORSALE_SQUALO, 0.022, 12, carnosa=True, spessore=0.003),
              Fin('anal', 0.82, 0.85, DORSALE_SQUALO, 0.02, 12, carnosa=True, spessore=0.003),
              Fin('caudal', 1.0, 1.0, coda_eterocerca(lobo=1.0, alzata=1.9, lobo_basso=0.45, basso=1.45), 0.27, 50,
                  carnosa=True, spessore=0.006),
              # le pettorali lunghe e strette, a falce, che scendono all'indietro dietro le fessure
              Fin('pectoral', 0.2, 0.24, [(0, 0.06), (0.5, 0.055), (1.0, -0.06), (0.9, -0.1), (0.4, -0.13), (0, -0.11)], 0.32, 30,
                  carnosa=True, spessore=0.005, dir=(0.8, 0.35, -0.5)),
              Fin('pelvic', 0.6, 0.64, [(0, 0.05), (0.6, 0.06), (1.0, -0.02), (0.6, -0.12), (0, -0.1)], 0.06, 20,
                  carnosa=True, spessore=0.004)]),
    aspetto=Look(back=(0.01, 0.03, 0.12), flank=(0.04, 0.12, 0.34), belly=(0.74, 0.75, 0.77), fin=(0.02, 0.06, 0.2),
                 iris=(0.12, 0.13, 0.15), iris_dark=(0.02, 0.02, 0.03), metal=0.1, irid=0.1, squame=0.0,
                 linea_laterale=0.0, lucido=0.35, ruvido=0.45),
    campo=_campo_verdesca, extra=_verdesca,
    famiglia='bleeding', piano='squalo',
    opzioni=dict(ferite=[]))


def _polpo_mat(c):
    """La pelle del polpo: bruno rossiccio a chiazze più scure e più chiare, le ventose pallide a puntini, bagnata."""
    import bpy
    m = bpy.data.materials.get('PelleDiPolpo')
    if m:
        return m
    m, g = c.P.material('PelleDiPolpo')
    co = g.texcoord('Object')
    n = g.noise(co, scale=70.0, detail=6.0, rough=0.6, distortion=0.5)
    col = g.mix(g.smoothstep(0.38, 0.66, n.fac), (0.42, 0.12, 0.11), (0.14, 0.035, 0.05))
    n2 = g.noise(co, scale=260.0, detail=3.0)
    col = g.mix(g.mul(g.smoothstep(0.6, 0.75, n2.fac), 0.6), col, (0.7, 0.45, 0.38))
    ventose = g.voronoi(co, scale=520.0, feature='F1', randomness=0.6)
    col = g.mix(g.mul(g.smoothstep(0.22, 0.1, ventose), 0.55), col, (0.82, 0.62, 0.55))
    g.output_material(g.principled(color=col, rough=0.35, coat=0.85, coat_rough=0.06, sss=0.3, sss_radius=(1, 0.3, 0.25),
                                   sss_scale=0.003, normal=g.bump(g.add(n2.fac, g.mul(ventose, -1.0)), strength=0.3, distance=0.0008)))
    return m


def _aguglia(c):
    """La cosa infilata sul rostro: un polpo trafitto attraverso la testa, ancora vivo. Due braccia si attorcigliano
    strette sul rostro verso la punta, due tornano indietro e si avvolgono sul muso dell'aguglia (una le passa
    sull'occhio), le altre pendono e si arricciano; gli occhi a fessura guardano la camera; il sangue sul rostro e le
    gocce dal polpo."""
    P, body = c.P, c.body
    r = c.forma.rostro
    xo = -0.105
    asse_z = float(r.z)
    H = np.array((xo, 0.0, asse_z + 0.003), F)
    cm = np.array((xo - 0.014, 0.003, asse_z + 0.047), F)
    mantello = P.sdf.rotate(P.sdf.ellipsoid(cm, (0.034, 0.029, 0.044)), P.sdf.rot_matrix('y', 25.0), center=cm)
    testa = P.sdf.ellipsoid(H, (0.025, 0.024, 0.022))
    rng = np.random.default_rng(6)
    braccia = []
    # due braccia a spirale strette attorno al rostro, verso la punta
    for k, fase in enumerate((0.3, 3.4)):
        s_ = np.linspace(0, 1, 26)
        x = xo - 0.016 - 0.07 * s_
        wy, wz, zc = P.sezione_rostro(r, x)
        ang = fase + 2 * math.pi * 1.4 * s_
        ra = 0.0072 - 0.0052 * s_
        rr = (wy + wz) * 0.5 + ra * 0.85
        braccia.append((np.stack([x, rr * np.cos(ang), zc + rr * np.sin(ang)], axis=1).astype(F), ra))
    # due braccia che tornano indietro sul muso: una si avvolge sopra l'occhio, una sotto la mascella
    e = body.occhi_lista()[0][0]
    for Q in (_curva(H + np.array((0.012, -0.016, 0.01), F), H + np.array((0.045, -0.04, 0.035), F),
                     e + np.array((-0.01, -0.035, 0.03), F), e + np.array((0.016, -0.014, 0.012), F), n=22),
              _curva(H + np.array((0.014, -0.014, -0.014), F), H + np.array((0.05, -0.04, -0.04), F),
                     np.array((0.035, -0.04, -0.05), F), np.array((0.06, -0.03, -0.035), F), n=22)):
        braccia.append((Q, np.linspace(0.0072, 0.0018, len(Q))))
    # quattro braccia che pendono e si arricciano in fondo
    for k in range(4):
        dy = (-0.02, -0.007, 0.007, 0.02)[k]
        dx = (-0.015, 0.005, -0.005, 0.015)[k]
        fondo = np.array((xo + dx * 2.5 + rng.normal(0, 0.008), dy * 2.2, asse_z - 0.095 - rng.uniform(0, 0.025)), F)
        ricciolo = fondo + np.array((rng.choice((-1, 1)) * 0.018, -0.008, 0.018), F)
        Q = _curva(H + np.array((dx, dy, -0.016), F), H + np.array((dx * 2, dy * 1.8, -0.055), F),
                   fondo + np.array((0.0, 0.0, -0.016), F), ricciolo, n=22)
        braccia.append((Q, np.linspace(0.0075, 0.0014, len(Q))))
    A, B, R1, R2 = [], [], [], []
    for Q, R in braccia:
        R = np.broadcast_to(np.asarray(R, F), (len(Q),))
        A += list(Q[:-1])
        B += list(Q[1:])
        R1 += list(R[:-1])
        R2 += list(R[1:])
    fb, lo_b, hi_b = P.campo_coni(A, B, R1, R2)
    corpo = P.sdf.union(mantello, testa, k=0.01)

    def polpo(p):
        return P.sdf.smin(corpo(p), fb(p), 0.005).astype(F)
    lo = np.minimum(lo_b, H - 0.07)
    hi = np.maximum(hi_b, H + np.array((0.05, 0.05, 0.11), F))
    c.obs.append(P.oggetto_sdf('Polpo', polpo, lo, hi, _polpo_mat(c), res=_res(c, 0.0006)))
    # gli occhi del polpo, a fessura, che guardano la camera
    occhio = P.eye_material('OcchioPolpo', iris=(0.85, 0.66, 0.22), iris_dark=(0.35, 0.22, 0.05), pupil='slit_h', pupil_size=0.42,
                            shine=(0.6, 0.6, 0.4), shine_strength=0.2, sclera=(0.3, 0.2, 0.06))
    for k, sy in enumerate((-1, 1)):
        ce = H + np.array((0.005, sy * 0.0225, 0.012), F)
        c.obs.append(P.eyeball(f'OcchioPolpo{k}', tuple(map(float, ce)), 0.0075, occhio, look=(0.25, -1.0, 0.15), col=P.COL))
    # il sangue: sul rostro attorno al polpo (fino al muso) e le gocce dalla testa trafitta
    rostro = [np.array((x, -0.007, asse_z), F) for x in np.linspace(-0.16, 0.0, 9)]
    _dipingi(c, 'blood', _lungo(rostro, 0.009, 0.85, lato=0))
    for k, dx in enumerate((-0.014, 0.008)):
        c.obs.append(_goccia(c, f'GocciaPolpo{k}', H + np.array((dx, -0.01, -0.02), F), 0.032 + 0.015 * k, r0=0.0022, r1=0.005))


# ── Aguglia Imperiale Trafitta (aguglia imperiale, Tetrapturus belone) ──
# Un pesce spada piccolo e slanciato (partenza: la prova spadossa): il rostro corto e tondo, la prima dorsale lunga
# dalla nuca quasi alla coda, alta davanti e poi bassa, la seconda dorsale e la seconda anale piccole vicino alla
# coda, le ventrali lunghe e sottili, la coda a mezzaluna rigida; blu scuro sopra, argento sotto. Anni fa ha
# trafitto qualcosa con il rostro: è ancora lì, infilato, e si muove (un polpo vivo, extra); i tagli della famiglia.
SPECIE['aguglia_imperiale'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.03, 0.016), (0.08, 0.036), (0.15, 0.055), (0.25, 0.069), (0.4, 0.072), (0.55, 0.066), (0.7, 0.05),
             (0.85, 0.029), (0.95, 0.016), (1, 0.012)],
        bot=[(0, -0.016), (0.04, -0.03), (0.1, -0.046), (0.2, -0.06), (0.35, -0.066), (0.5, -0.062), (0.65, -0.048), (0.8, -0.031),
             (0.95, -0.015), (1, -0.012)],
        w=[(0, 0.006), (0.06, 0.026), (0.2, 0.04), (0.4, 0.043), (0.65, 0.033), (0.85, 0.019), (1, 0.01)],
        eye_t=0.07, eye_z=0.01, eye_r=0.015, mouth_t=0.078, mouth_z0=-0.012, mouth_z1=-0.022, gill_t=0.17,
        rostro=Rostro('spada', lunghezza=0.2, z=-0.004, larghezza=0.0085, altezza=0.0078, punta=0.18),
        fins=[Fin('dorsal', 0.17, 0.74, [(0, 0), (0.03, 0.9), (0.07, 1.0), (0.12, 0.72), (0.2, 0.4), (0.35, 0.33), (0.6, 0.3),
                                        (0.85, 0.28), (0.97, 0.22), (1, 0.05)], 0.13, 60, colore=(0.04, 0.06, 0.16)),
              Fin('dorsal', 0.86, 0.89, [(0, 0), (0.3, 1.0), (1, 0.1)], 0.026, 10, carnosa=True, spessore=0.003),
              Fin('anal', 0.6, 0.67, [(0, 0), (0.15, 0.9), (0.3, 1.0), (0.5, 0.45), (1, 0.06)], 0.07, 20, carnosa=True, spessore=0.004),
              Fin('anal', 0.85, 0.88, [(0, 0), (0.3, 1.0), (1, 0.1)], 0.022, 10, carnosa=True, spessore=0.003),
              Fin('caudal', 1.0, 1.0, coda_falcata(3.0, 0.95, radice=0.25), 0.27, 60, carnosa=True, spessore=0.006),
              Fin('pectoral', 0.18, 0.2, [(0, 0.05), (0.45, 0.08), (1.0, 0.02), (0.75, -0.05), (0.3, -0.09), (0, -0.08)], 0.11, 20,
                  carnosa=True, spessore=0.003, dir=(0.75, 0.3, -0.5)),
              Fin('pelvic', 0.21, 0.215, [(0, 0), (0.5, 0.05), (1, 0.015), (0.5, -0.025), (0, -0.025)], 0.13, 5,
                  colore=(0.04, 0.06, 0.16))]),
    aspetto=Look(back=(0.015, 0.03, 0.09), flank=(0.2, 0.25, 0.36), belly=(0.72, 0.74, 0.76), fin=(0.03, 0.05, 0.13),
                 iris=(0.3, 0.35, 0.4), iris_dark=(0.05, 0.06, 0.08), metal=0.5, irid=0.35, squame=0.1, linea_laterale=0.0,
                 lucido=0.5,
                 disegni=[Disegno('ventre', colore=(0.8, 0.82, 0.84), forza=0.55, v1=-0.3)]),
    extra=_aguglia,
    famiglia='bleeding', piano='rostro',
    opzioni=dict(ferite=[((0.36, 0.45), (0.41, -0.15)), ((0.55, 0.35), (0.58, -0.25))], denti=6))


def _volpe(c):
    """Una cicatrice per ogni colpo mancato: cordoni chiari in rilievo sparsi sul fianco e di traverso su tutto il lobo
    lunghissimo della coda (cercati sul campo vero, perché la coda è una pinna di carne)."""
    P = c.P
    rng = np.random.default_rng(13)
    seg = []
    for _ in range(15):
        t, v = rng.uniform(0.12, 0.95), rng.uniform(-0.55, 0.75)
        zc, h, _ = _sezione(c, t)
        z = zc + h * v
        L, a = rng.uniform(0.025, 0.09), rng.uniform(0.25, math.pi - 0.25)
        seg.append(((t - L / 2 * math.cos(a), z - L / 2 * math.sin(a)), (t + L / 2 * math.cos(a), z + L / 2 * math.sin(a))))
    coda = next(f for f in c.forma.fins if f.kind == 'caudal')
    zc1, _, _ = _sezione(c, 1.0)
    sopra = np.array(coda.outline[:5], F)
    sotto = np.array(coda.outline[5:9][::-1], F)
    for ea in np.sort(rng.uniform(0.4, 2.15, 15)):
        eo_s = float(np.interp(ea, sopra[:, 0], sopra[:, 1]))
        eo_g = float(np.interp(ea, sotto[:, 0], sotto[:, 1]))
        storto = rng.normal(0, 0.16)
        quanto = rng.uniform(0.45, 1.25)                    # alcune attraversano il lobo, altre no
        da_sopra = rng.uniform() < 0.5
        a_, b_ = (eo_s + 0.12, eo_s + 0.12 - (eo_s - eo_g + 0.24) * quanto) if da_sopra else \
            (eo_g - 0.12, eo_g - 0.12 + (eo_s - eo_g + 0.24) * quanto)
        x0, x1 = 0.99 + (ea + storto) * coda.size, 0.99 + (ea - storto) * coda.size
        seg.append(((x0, zc1 + a_ * coda.size * 0.42), (x1, zc1 + b_ * coda.size * 0.42)))
    mat = P.materiale('Cicatrice', (0.6, 0.53, 0.53), rough=0.45, coat=0.35, sss=0.2)
    ob = _cicatrici(c, seg, 0.0034, mat)
    if ob is not None:
        c.obs.append(ob)


# ── Volpe Sfregiata (squalo volpe, Alopias vulpinus) — la prova del piano 'squalo', trasformata ──
# La coda a falce lunga quanto il corpo, gli occhi grandi, la prima dorsale alta, le pettorali lunghe; grigio
# scuro sopra, bianco sotto. Ha una cicatrice chiara per ogni colpo mancato, sul corpo e di traverso su tutta la
# coda (extra), più due tagli freschi della famiglia.
SPECIE['volpe_sfregiata'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.02, 0.018), (0.06, 0.044), (0.12, 0.068), (0.22, 0.09), (0.36, 0.1), (0.5, 0.09), (0.65, 0.064),
             (0.8, 0.04), (0.92, 0.024), (1, 0.018)],
        bot=[(0, -0.012), (0.03, -0.034), (0.08, -0.054), (0.18, -0.078), (0.32, -0.094), (0.48, -0.088), (0.62, -0.066),
             (0.78, -0.038), (0.92, -0.022), (1, -0.018)],
        w=[(0, 0.004), (0.04, 0.03), (0.12, 0.058), (0.3, 0.078), (0.5, 0.07), (0.7, 0.044), (0.9, 0.021), (1, 0.014)],
        eye_t=0.085, eye_z=0.018, eye_r=0.017,
        bocca='ventrale', mouth_a=0.07, mouth_t=0.118, mouth_z1=-0.03, mouth_z0=-0.03,
        branchie='fessure', gill_t=0.165, n_branchie=5, passo_branchie=0.017,
        fins=[Fin('dorsal', 0.37, 0.49, DORSALE_SQUALO, 0.135, 30, carnosa=True, spessore=0.007),
              Fin('dorsal', 0.86, 0.885, DORSALE_SQUALO, 0.02, 12, carnosa=True, spessore=0.003),
              Fin('anal', 0.875, 0.9, DORSALE_SQUALO, 0.018, 12, carnosa=True, spessore=0.003),
              # il lobo di sopra lungo quanto il corpo, stretto come una falce; quello di sotto piccolo
              Fin('caudal', 1.0, 1.0, [(0, 0.12), (0.6, 0.75), (1.2, 1.32), (1.8, 1.82), (2.3, 2.2), (2.18, 1.98), (1.6, 1.45),
                                      (1.0, 0.9), (0.52, 0.32), (0.4, -0.05), (0.33, -0.45), (0.26, -0.78), (0.1, -0.15)],
                  0.42, 60, carnosa=True, spessore=0.006),
              Fin('pectoral', 0.2, 0.25, [(0, 0.08), (0.45, 0.13), (1.0, 0.03), (0.82, -0.08), (0.35, -0.18), (0, -0.14)], 0.24, 30,
                  carnosa=True, spessore=0.006, dir=(0.75, 0.3, -0.6)),
              Fin('pelvic', 0.56, 0.6, [(0, 0.05), (0.6, 0.06), (1.0, -0.02), (0.6, -0.12), (0, -0.1)], 0.075, 20,
                  carnosa=True, spessore=0.004)]),
    aspetto=Look(back=(0.05, 0.05, 0.08), flank=(0.13, 0.13, 0.17), belly=(0.70, 0.70, 0.68), fin=(0.08, 0.08, 0.11),
                 iris=(0.12, 0.13, 0.14), iris_dark=(0.03, 0.03, 0.04), metal=0.12, irid=0.08, squame=0.0,
                 linea_laterale=0.0, lucido=0.35, ruvido=0.45),
    extra=_volpe,
    famiglia='bleeding', piano='squalo',
    opzioni=dict(ferite=[((0.33, 0.45), (0.38, -0.2)), ((0.58, 0.4), (0.61, -0.3))]))


# i buchi degli arpioni delle mattanze passate: (t, v, raggio)
_BUCHI_TONNO = [(0.27, -0.25, 0.012), (0.56, 0.5, 0.011), (0.74, -0.15, 0.009)]


def _geo_tonno(c):
    """I buchi tondi e profondi degli arpioni."""
    P, body = c.P, c.body
    s = _Scavi(P)
    s.buchi = []
    for t, v, r in _BUCHI_TONNO:
        p, n = body.superficie(t, v, -1)
        s.coni([p + n * 0.004], [p - n * 0.03], [r], [r * 0.5])
        s.buchi.append((p, n, r))
    return s


def _campo_tonno(c, f):
    return _cache(c, 'scavi', _geo_tonno).scava(f)


def _uncino(P, E, n, d, mat_ferro, mat_legno, nome):
    """Un raffio della mattanza piantato nella carne: la punta dentro, la curva del gancio che esce dalla pelle in E
    (normale n), il gambo dritto lungo d e il manico di legno spezzato. Due oggetti (ferro e legno)."""
    n = np.asarray(n, F) / np.linalg.norm(n)
    d = np.asarray(d, F) / np.linalg.norm(d)
    punta = E - n * 0.026 - d * 0.018
    curva = _curva(punta, E - n * 0.012 - d * 0.03, E + n * 0.03 - d * 0.02, E + n * 0.04 + d * 0.012, n=18)
    gambo_fine = E + n * 0.04 + d * 0.11
    Q = np.concatenate([curva, [gambo_fine]])
    R = np.concatenate([np.linspace(0.0012, 0.0055, len(curva)), [0.0055]])
    f, lo, hi = P.campo_coni(Q[:-1], Q[1:], R[:-1], R[1:])
    ferro = P.oggetto_sdf(f'{nome}Ferro', f, lo, hi, mat_ferro, res=0.0007)
    # il manico: un bastone di legno con la punta spezzata a scheggia
    a, b = gambo_fine - d * 0.012, gambo_fine + d * 0.1
    bastone = P.sdf.round_cone(a, b, 0.0085, 0.0078)
    scheggia = P.sdf.round_cone(b - d * 0.004, b + d * 0.03 + n * 0.004, 0.006, 0.0008)
    legno = P.oggetto_sdf(f'{nome}Legno', P.sdf.union(bastone, scheggia, k=0.003), np.minimum(a, b) - 0.04,
                          np.maximum(a, b) + 0.04, mat_legno, res=0.0008)
    return [ferro, legno]


def _tonno(c):
    """Le mattanze, tutte: due raffi piantati nella carne con il manico spezzato, un arpione infilato, i buchi tondi
    degli arpioni vecchi, le cicatrici chiare, e tanto sangue che cola dappertutto fino a gocciolare dal ventre."""
    P, body = c.P, c.body
    s = _cache(c, 'scavi', _geo_tonno)
    _dipingi(c, 'wound', s.carne)
    _dipingi(c, 'mouth', s.scuro(c))
    ferro = _ruggine(c)
    legno = P.materiale('LegnoRaffio', (0.2, 0.12, 0.06), rough=0.75, coat=0.1)
    E1, n1 = body.superficie(0.36, 0.55, -1)
    c.obs += _uncino(P, E1, n1, n1 * 0.35 + np.array((0.75, 0.0, 0.55), F), ferro, legno, 'Raffio1')
    E2, n2 = body.superficie(0.6, -0.45, -1)
    c.obs += _uncino(P, E2, n2, n2 * 0.3 + np.array((0.8, 0.0, -0.5), F), ferro, legno, 'Raffio2')
    # l'arpione: un'asta di ferro infilata di sbieco, con l'anello in cima e le alette vicino alla pelle
    E3, n3 = body.superficie(0.47, 0.15, -1)
    d3 = n3 * 0.55 + np.array((0.6, 0.0, 0.35), F)
    d3 /= np.linalg.norm(d3)
    a, b = E3 - d3 * 0.05, E3 + d3 * 0.13
    asta = P.sdf.round_cone(a, b, 0.0034, 0.0032)

    def anello_f(p, b=b, d=d3):
        q = p - (b + d * 0.008)
        h = q @ d
        rad = np.linalg.norm(q - h[:, None] * d, axis=1)
        return (np.sqrt((rad - 0.0085) ** 2 + h ** 2) - 0.0022).astype(F)
    c.obs.append(P.oggetto_sdf('Arpione', P.sdf.union(asta, anello_f, k=0.001), np.minimum(a, b) - 0.02, np.maximum(a, b) + 0.02,
                               ferro, res=0.0007))
    # le cicatrici delle mattanze vecchie
    rng = np.random.default_rng(19)
    seg = []
    for _ in range(7):
        t, v = rng.uniform(0.2, 0.85), rng.uniform(-0.6, 0.6)
        zc, h, _ = _sezione(c, t)
        z = zc + h * v
        L, ang = rng.uniform(0.04, 0.09), rng.uniform(0.2, math.pi - 0.2)
        seg.append(((t - L / 2 * math.cos(ang), z - L / 2 * math.sin(ang)), (t + L / 2 * math.cos(ang), z + L / 2 * math.sin(ang))))
    ob = _cicatrici(c, seg, 0.0034, P.materiale('CicatriceTonno', (0.62, 0.55, 0.55), rough=0.45, coat=0.35, sss=0.2))
    if ob is not None:
        c.obs.append(ob)
    # tanto sangue: dai raffi, dall'arpione, dai buchi; il ventre bagnato; le gocce
    sorgenti = [(E1, 0.009, 0.2, 1.0), (E2, 0.009, 0.14, 1.0), (E3, 0.008, 0.2, 1.0)]
    sorgenti += [(p - n * 0.0, r * 0.8, 0.16, 1.0) for p, n, r in s.buchi]
    _dipingi(c, 'blood', _colature(sorgenti, seme=1.0))

    def ventre(V):
        zc, h, _ = body.section(np.clip(V[:, 0], 0, 1))
        v = (V[:, 2] - zc) / h
        return (np.clip((-0.55 - v) / 0.35, 0, 1) * 0.75 * (V[:, 0] > 0.15) * (V[:, 0] < 0.85)).astype(F)
    _dipingi(c, 'blood', ventre)
    for k, t in enumerate((0.28, 0.37, 0.47, 0.56, 0.66)):
        p, _ = body.superficie(t, -0.97, -1)
        c.obs.append(_goccia(c, f'GocciaVentre{k}', p, 0.025 + 0.015 * (k % 3), r0=0.0022, r1=0.005))


# ── Tonno di Sangue (tonno rosso, Thunnus thynnus) — la prova del piano 'fusiforme', trasformata ──
# Il fuso di sempre, con le pinnule gialle (tante dorsali e anali piccole) e la coda a mezzaluna. Si ricorda tutte
# le mattanze: due raffi piantati con il manico spezzato, un arpione, i buchi tondi degli arpioni e le cicatrici
# delle mattanze vecchie, i tagli freschi della famiglia, tanto sangue (campo + extra).
SPECIE['tonno_di_sangue'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.03), (0.08, 0.075), (0.16, 0.115), (0.3, 0.14), (0.42, 0.142), (0.55, 0.125), (0.7, 0.085),
             (0.82, 0.045), (0.92, 0.022), (1, 0.016)],
        bot=[(0, -0.025), (0.04, -0.055), (0.12, -0.095), (0.25, -0.13), (0.4, -0.138), (0.55, -0.12), (0.7, -0.08), (0.82, -0.042),
             (0.92, -0.02), (1, -0.016)],
        w=[(0, 0.008), (0.06, 0.05), (0.2, 0.1), (0.4, 0.11), (0.6, 0.085), (0.8, 0.04), (0.92, 0.02), (1, 0.014)],
        eye_t=0.1, eye_z=0.025, eye_r=0.02, mouth_t=0.075, mouth_z0=-0.015, mouth_z1=-0.03, gill_t=0.21,
        fins=[Fin('dorsal', 0.3, 0.42, DORSALE_TRIANGOLO, 0.1, 13, spiny=True),
              Fin('dorsal', 0.45, 0.52, DORSALE_FALCE, 0.13, 12),
              Fin('anal', 0.5, 0.57, DORSALE_FALCE, 0.11, 12)]
             + [Fin('dorsal', 0.6 + 0.04 * i, 0.62 + 0.04 * i, _PINNULA, 0.022, 4, colore=(0.75, 0.6, 0.15)) for i in range(8)]
             + [Fin('anal', 0.62 + 0.04 * i, 0.64 + 0.04 * i, _PINNULA, 0.02, 4, colore=(0.75, 0.6, 0.15)) for i in range(7)]
             + [Fin('caudal', 1.0, 1.0, coda_falcata(2.9, 0.85, radice=0.3), 0.3, 26),
                Fin('pectoral', 0.24, 0.255, PETTORALE, 0.12, 12),
                Fin('pelvic', 0.3, 0.31, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.02, 0.04, 0.09), flank=(0.36, 0.4, 0.46), belly=(0.72, 0.73, 0.74), fin=(0.12, 0.13, 0.16),
                 iris=(0.55, 0.55, 0.5), iris_dark=(0.08, 0.08, 0.08), metal=0.75, irid=0.4, squame=0.3,
                 disegni=[Disegno('ventre', colore=(0.78, 0.8, 0.82), forza=0.6, v1=-0.35),
                          Disegno('bande', colore=(0.82, 0.84, 0.86), forza=0.35, n=14, u0=0.3, u1=0.85, v0=-0.75, v1=-0.15,
                                  larghezza=0.25, onda=0.05)]),
    campo=_campo_tonno, extra=_tonno,
    famiglia='bleeding', piano='fusiforme',
    opzioni=dict(ferite=[((0.25, 0.35), (0.32, -0.3)), ((0.66, 0.4), (0.7, -0.1)), ((0.42, -0.35), (0.5, -0.75))], denti=8))
