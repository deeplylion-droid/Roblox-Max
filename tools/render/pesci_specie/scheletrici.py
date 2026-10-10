"""
Scheletrici: carne mancante, lisca e cranio in vista (src/game/catalog.ts, docs/CATALOGO.md).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast

Lo scheletro lo fa la famiglia (pesci.skeletal): il cranio, la lisca, la striscia di pelle del dorso, il
peduncolo carnoso, le pinne d'osso. Prima delle voci ci sono gli aiuti comuni agli extra di questo file:
la lisca con lo spessore delle ossa regolabile (_lisca: su corpi alti o sottili quella della famiglia ha
spine e costole troppo fini, che nelle anteprime spariscono), i denti in più file (_denti), la bocca aperta
del cranio (_apri_bocca, un campo: il cranio della famiglia ha sempre la bocca chiusa), la pelle rimasta fatta
a mano (_involucro, _lembo), la mappa della piega (_mappa_piega) e i materiali.
"""
import math
from dataclasses import replace

import numpy as np

from .base import (DORSALE_SQUALO, PELVICA, PETTORALE, PETTORALE_TONDA, RITRATTO_PROTOTIPI, Disco, Disegno,
                   Filamento, Fin, Fotofori, Look, Rostro, Shape, Specie, coda_appuntita, coda_eterocerca,
                   coda_falcata, coda_forcuta, coda_tonda, coda_tronca)

F = np.float32
SPECIE = {}


# ───────────────────────── aiuti per gli extra degli scheletri ─────────────────────────

def _sez(body, t):
    """(quota del centro, mezza altezza, mezza larghezza) del corpo in t, come numeri."""
    zc, h, w = body.section(np.array([t], F))
    return float(zc[0]), float(h[0]), float(w[0])


def _x_cranio(c):
    """Dove finisce il cranio: come pesci.skeletal (l'opzione cranio_t, o subito dietro l'opercolo)."""
    t = c.specie.opzioni.get('cranio_t')
    return c.forma.gill_t + 0.01 if t is None else t


def _osso(c):
    """Il materiale delle ossa della famiglia per questa specie (con la tinta dell'opzione osso): lo stesso
    del cranio, così le ossa degli extra non si distinguono."""
    tinta = c.specie.opzioni.get('osso')
    return c.P.bone_material() if tinta is None else c.P.bone_material('BoneTinto', tinta=tinta)


def _trova(c, nome):
    """Gli oggetti di c.obs con questo nome (senza il suffisso .001 di Blender)."""
    return [o for o in c.obs if o.name.split('.')[0] == nome]


def _togli(c, *nomi):
    """Toglie dalla scena e da c.obs gli oggetti della famiglia con questi nomi ('Spine', 'SkinStrip',
    'Peduncle', ...), quando un extra li rifà a modo suo."""
    import bpy
    via = [o for o in c.obs if o.name.split('.')[0] in nomi]
    c.obs[:] = [o for o in c.obs if o.name.split('.')[0] not in nomi]
    for o in via:
        bpy.data.objects.remove(o, do_unlink=True)


def _rivesti(c, nome, mat):
    """Cambia il materiale degli oggetti con questo nome (il cranio, la lisca, la striscia di pelle...)."""
    for o in _trova(c, nome):
        o.data.materials.clear()
        o.data.materials.append(mat)


def _spezzata_2d(P, V):
    """Distanza dai punti P (N, 2) alla spezzata aperta V (M, 2) (come quella di pesci, che è privata)."""
    d2 = np.full(len(P), np.inf, F)
    for a, b in zip(V[:-1], V[1:]):
        e = b - a
        w = P - a
        t = np.clip((w @ e) / max(float(e @ e), 1e-12), 0, 1)
        dd = w - t[:, None] * e
        d2 = np.minimum(d2, np.einsum('ij,ij->i', dd, dd))
    return np.sqrt(d2).astype(F)


def _curva(c, punti, n=40):
    """Una curva liscia (pesci.prof su ogni coordinata) per i punti di controllo: n punti."""
    P = np.asarray(punti, F)
    s = np.arange(len(P), dtype=F)
    u = np.linspace(0, len(P) - 1, n).astype(F)
    return np.stack([c.P.prof(list(zip(s, P[:, k])))(u) for k in range(3)], axis=1)


class _Ossa:
    """Tante ossa (coni arrotondati) da fare in un oggetto solo con pesci.campo_coni. Le ossa lunghe si
    spezzano in segmenti corti, perché il campo guarda solo i pezzi più vicini a ogni punto; i segmenti che
    cadono in un morso (x, z, raggio: un cerchio sul fianco, nel piano del ritratto) si buttano."""

    def __init__(self, morsi=()):
        self.A, self.B, self.R1, self.R2 = [], [], [], []
        self.morsi = [tuple(map(float, m)) for m in morsi]

    def cono(self, a, b, r1, r2, passo=0.008):
        """Un osso dritto da a (raggio r1) a b (raggio r2)."""
        a, b = np.asarray(a, F), np.asarray(b, F)
        n = max(1, int(math.ceil(float(np.linalg.norm(b - a)) / passo)))
        for i in range(n):
            u0, u1 = i / n, (i + 1) / n
            p0, p1 = a + (b - a) * u0, a + (b - a) * u1
            m = (p0 + p1) * 0.5
            if any((m[0] - x) ** 2 + (m[2] - z) ** 2 < r * r for x, z, r in self.morsi):
                continue
            self.A.append(p0)
            self.B.append(p1)
            self.R1.append(r1 + (r2 - r1) * u0)
            self.R2.append(r1 + (r2 - r1) * u1)

    def spezzata(self, punti, r1, r2, passo=0.008):
        """Un osso curvo lungo la spezzata, che si assottiglia da r1 a r2."""
        P = [np.asarray(p, F) for p in punti]
        L = np.concatenate([[0.0], np.cumsum([np.linalg.norm(b - a) for a, b in zip(P[:-1], P[1:])])])
        L = L / max(float(L[-1]), 1e-9)
        for i in range(len(P) - 1):
            self.cono(P[i], P[i + 1], r1 + (r2 - r1) * L[i], r1 + (r2 - r1) * L[i + 1], passo)

    def nodo(self, p, r):
        """Una testa d'osso tonda (l'epifisi delle ossa lunghe, una nocca)."""
        p = np.asarray(p, F)
        d = np.array((r * 0.3, 0.0, 0.0), F)
        self.cono(p - d, p + d, r, r)

    def oggetto(self, c, nome, mat, res, attrs=None):
        f, lo, hi = c.P.campo_coni(self.A, self.B, self.R1, self.R2, k=6)
        return c.P.oggetto_sdf(nome, f, lo, hi, mat, res=res, attrs=attrs)


def _lisca(c, vertebre=34, costole_fino=0.55, emali_da=0.5, spessore=1.0, minimo=0.0, r_min=0.0035,
           costole_dietro=0.012, alte=0.92, basse=0.9, inclinate=0.45, spine=True, aghi=False,
           pterigiofori=False, ipurale=False, morsi=(), seme=3, mat=None, nome='Lisca'):
    """La colonna vertebrale con le spine e le costole, fatta come quella della famiglia (pesci.skeletal) ma
    con lo spessore delle ossa regolabile. La famiglia fa comunque la sua ('Spine'): l'extra la toglie
    (_togli) e mette questa; con l'opzione vertebre=1 la famiglia ne fa una sola e ci mette meno.

    vertebre, costole_fino, emali_da: come le opzioni della famiglia (costole fino in fondo: emali_da=1);
    spessore: moltiplica il raggio di spine e costole; minimo: il raggio minimo delle costole (le spine 1.2
    volte); r_min: il raggio minimo delle vertebre; costole_dietro: quanto pendono indietro le costole; alte,
    basse: fin dove arrivano le spine (frazioni della mezza altezza); inclinate: quanto pendono indietro (in
    mezze altezze); spine=False: solo le vertebre; aghi: le ossicine fini fra i muscoli (acciughe, sardine);
    pterigiofori: le ossa che reggono i raggi di dorsali e anali; ipurale: il ventaglio d'osso in fondo alla
    colonna che regge la coda (quando non c'è il peduncolo carnoso); morsi: [(x, z, raggio)] dove le ossa
    mancano. Restituisce (oggetto, ossa): ossa = {'vertebre', 'costole' (le spezzate del lato sinistro),
    'neurali', 'emali' (base, punta)}, per attaccarci altre cose (le lucine della lanterna)."""
    body, sh = c.body, c.forma
    rng = np.random.default_rng(seme)
    oss = _Ossa(morsi)
    xs = np.linspace(_x_cranio(c) - 0.01, 1.0, vertebre + 1)
    ossa = {'vertebre': [], 'costole': [], 'neurali': [], 'emali': []}
    rc_min = 1.0
    for i in range(vertebre):
        x0, x1 = xs[i] + 0.0015, xs[i + 1] - 0.0015
        xm = 0.5 * (x0 + x1)
        zc, h, w = _sez(body, xm)
        r = max(r_min, min(h, w) * 0.16)
        a, b, e = np.array((x0, 0, zc), F), np.array((xm, 0, zc), F), np.array((x1, 0, zc), F)
        # il corpo della vertebra a clessidra, come quelle della famiglia
        oss.cono(a, b, r, r * 0.72)
        oss.cono(b, e, r * 0.72, r)
        ossa['vertebre'].append(b)
        if not spine:
            continue
        rs = max(r * 0.32 * spessore, minimo * 1.2)
        rc = max(r * 0.26 * spessore, minimo)
        rc_min = min(rc_min, rc)
        # spina neurale (in su e indietro) e, dalla metà in poi, emale (in giù)
        punta = np.array((xm + h * inclinate, 0, zc + h * alte), F)
        oss.cono(b + np.array((0, 0, r * 0.6), F), punta, rs, rs * 0.38)
        ossa['neurali'].append((b, punta))
        if xm > emali_da:
            punta = np.array((xm + h * inclinate, 0, zc - h * basse), F)
            oss.cono(b - np.array((0, 0, r * 0.6), F), punta, rs * 0.94, rs * 0.32)
            ossa['emali'].append((b, punta))
        elif xm < costole_fino:
            # costole: archi che scendono lungo la sezione, a destra e a sinistra
            for s in (-1, 1):
                pts = [b]
                for k in range(1, 6):
                    ang = math.radians(-12 - 95 * k / 5)
                    rr = 0.86 + 0.04 * rng.uniform(-1, 1)
                    pts.append(np.array((xm + costole_dietro * k / 5, s * w * rr * math.cos(ang),
                                         zc + h * rr * math.sin(ang)), F))
                oss.spezzata(pts, rc, rc * 0.77)
                if s == -1:
                    ossa['costole'].append(pts)
        if aghi and xm < 0.9:
            # le ossicine fra i muscoli: due aghi per lato, in su e in giù, coricati all'indietro
            ra = rc * 0.6
            for s in (-1, 1):
                for sz in (1, -1):
                    q = np.array((xm + h * 0.55, s * w * 0.4, zc + sz * h * 0.5), F)
                    oss.cono(b + np.array((0, s * r * 0.4, sz * r * 0.3), F), q, ra, ra * 0.25)
    if pterigiofori:
        # sotto ogni due raggi di dorsali e anali, un'osso che scende verso la colonna
        rp = max(min(rc_min, 0.004) * 0.85, 0.0011)
        for fin in sh.fins:
            if fin.kind not in ('dorsal', 'anal') or fin.carnosa:
                continue
            for j in range(0, fin.rays + 1, max(1, fin.rays // 12)):
                t = fin.a + (fin.b - fin.a) * j / fin.rays
                zc, h, _ = _sez(body, t)
                if fin.kind == 'dorsal':
                    a = (t, 0.0, float(body.top(np.array([t], F))[0]) - 0.003)
                    b = (t - 0.008, 0.0, zc + h * 0.48)
                else:
                    a = (t, 0.0, float(body.bot(np.array([t], F))[0]) + 0.003)
                    b = (t - 0.008, 0.0, zc - h * 0.48)
                oss.cono(a, b, rp, rp * 0.55)
    if ipurale:
        # il ventaglio dell'ipurale: dall'ultima vertebra alle radici dei raggi della coda (in x = 0.99)
        zc, h, _ = _sez(body, 1.0)
        rv = max(r_min, h * 0.12)
        base = np.array((0.972, 0.0, zc), F)
        for f in np.linspace(-1.0, 1.0, 7):
            oss.cono(base, (0.993, 0.0, zc + h * 0.92 * f), rv * 0.75, rv * 0.5)
    res = float(np.clip(min(rc_min, r_min) * 0.7, 0.0005, 0.0014))
    return oss.oggetto(c, nome, mat or _osso(c), res), ossa


def _apri_bocca(gradi):
    """campo: apre la bocca del cranio di `gradi` (la mascella di sotto gira attorno all'angolo della bocca),
    come Body.field con mouth_open, che lo scheletro della famiglia non usa. Con _denti(apertura=gradi)."""
    def campo(c, f):
        sh = c.forma
        cerniera = np.array((sh.mouth_t, 0.0, sh.mouth_z1), F)
        R = c.P.sdf.rot_matrix('y', -gradi)
        linea = c.body.mouth_line

        def g(p):
            sopra = np.maximum(f(p), np.minimum(linea(p[:, 0]) - p[:, 2], sh.mouth_t - p[:, 0]))
            q = ((p - cerniera) @ R + cerniera).astype(F)
            sotto = np.maximum(f(q), np.maximum(q[:, 2] - linea(q[:, 0]), q[:, 0] - sh.mouth_t))
            return np.minimum(sopra, sotto).astype(F)
        return g
    return campo


def _denti(c, n=12, lunghezza=0.004, raggio=0.001, file=1, apertura=0.0, fino=None, zanne=(), dentro=0.85,
           mat=None, nome='Denti', seme=0):
    """I denti lungo le due mascelle, in `file` file (la prima sul bordo, le altre più dentro e più corte),
    aguzzi e appena piegati indietro: coni in un oggetto solo (campo_coni). apertura: i gradi della bocca
    aperta (_apri_bocca), così quelli di sotto seguono la mascella; zanne: gli indici dei denti lunghi il
    doppio; dentro: a che frazione della mezza larghezza stanno (1 sulla pelle)."""
    P, body, sh = c.P, c.body, c.forma
    rng = np.random.default_rng(seme)
    R = P.sdf.rot_matrix('y', -apertura)
    cerniera = np.array((sh.mouth_t, 0.0, sh.mouth_z1), F)
    fino = sh.mouth_t - 0.012 if fino is None else fino
    A, B, R1, R2 = [], [], [], []
    for fila in range(file):
        k = 1.0 - 0.28 * fila
        for mascella in (1, -1):        # 1: sopra (la punta in giù), −1: sotto
            for i in range(n):
                x = 0.006 + (fino - 0.006) * min((i + 0.5 * fila) / max(n - 1, 1), 1.0)
                zl = float(body.mouth_line(np.array([x], F))[0])
                for s in (-1, 1):
                    y = s * float(body.surface_y(x, zl)) * (dentro - 0.2 * fila)
                    ln = lunghezza * k * (2.0 if i in zanne else 1.0) * rng.uniform(0.8, 1.15)
                    base = np.array((x, y, zl + mascella * 0.0015), F)
                    punta = base + np.array((ln * 0.22, -s * ln * 0.1, -mascella * ln), F)
                    if mascella == -1 and apertura:
                        base = (base - cerniera) @ R.T + cerniera
                        punta = (punta - cerniera) @ R.T + cerniera
                    A.append(base)
                    B.append(punta)
                    R1.append(raggio * k)
                    R2.append(raggio * 0.12)
    f, lo, hi = P.campo_coni(A, B, R1, R2)
    return P.oggetto_sdf(nome, f, lo, hi, mat or P.dirty_teeth_material(), res=max(raggio * 0.4, 0.0003))


def _involucro(c, mat, da=None, fino=1.0, nome='Involucro'):
    """La pelle rimasta tutta, da t = da (di default appena dentro il cranio) a fino: il corpo pieno, con gli
    attributi u, v della pelle; con un materiale trasparente (_mat_vetro) si vede la lisca dentro."""
    P, body = c.P, c.body
    da = _x_cranio(c) - 0.006 if da is None else da
    raw = body.raw()

    def f(p):
        d = np.maximum(raw(p), da - p[:, 0])
        return np.maximum(d, p[:, 0] - fino).astype(F)
    lo, hi = body.bounds(tratto=(da, fino))
    lo[0], hi[0] = max(float(lo[0]), da - 0.01), min(float(hi[0]), fino + 0.01)
    return P.oggetto_sdf(nome, f, lo, hi, mat, res=0.0025 if c.fast else 0.0015, attrs=P.base_attrs(body, lk=c.aspetto))


def _lembo(c, x0, z0, raggio, mat, nome='Lembo', seme=0):
    """Un lembo di pelle rimasto sul fianco sinistro (verso la camera), tondo e strappato, attorno a (x0, z0):
    un guscio sottile appena sotto la pelle di prima, come la striscia della famiglia."""
    P, body = c.P, c.body
    raw = body.raw()
    n3 = P.sdf.Noise3(seme)

    def f(p):
        d = np.abs(raw(p) + 0.003) - 0.0025
        rr = np.sqrt((p[:, 0] - x0) ** 2 + (p[:, 2] - z0) ** 2)
        d = np.maximum(d, rr - raggio * (1.0 + 0.22 * n3(p, scale=0.012, octaves=2)))
        return np.maximum(d, p[:, 1]).astype(F)
    _, _, w = _sez(body, x0)
    lo = np.array((x0 - raggio * 1.4, -w - 0.03, z0 - raggio * 1.4), F)
    hi = np.array((x0 + raggio * 1.4, 0.005, z0 + raggio * 1.4), F)
    return P.oggetto_sdf(nome, f, lo, hi, mat, res=0.0012, attrs=P.base_attrs(body, lk=c.aspetto))


def _mappa_piega(c):
    """La stessa mappa di pesci.piega: il punto del pesce dritto → il punto del pesce piegato, e l'angolo
    dell'asse; serve per gli oggetti rigidi che la piega sposta interi (il palo della giostra)."""
    pts = [(float(t), math.radians(float(a))) for t, a in c.forma.piega]
    th = c.P.prof(pts)
    xs = np.linspace(-1.5, 3.0, 9001, dtype=np.float64)
    ang = th(np.clip(xs, pts[0][0], pts[-1][0])).astype(np.float64)
    dx = xs[1] - xs[0]
    cx = np.concatenate([[0.0], np.cumsum((np.cos(ang[1:]) + np.cos(ang[:-1])) * 0.5 * dx)])
    cz = np.concatenate([[0.0], np.cumsum((np.sin(ang[1:]) + np.sin(ang[:-1])) * 0.5 * dx)])
    i0 = int(np.searchsorted(xs, 0.0))
    cx -= cx[i0]
    cz -= cz[i0]

    def mappa(P):
        P = np.asarray(P, np.float64).reshape(-1, 3)
        a = np.interp(P[:, 0], xs, ang)
        X = np.interp(P[:, 0], xs, cx) - P[:, 2] * np.sin(a)
        Z = np.interp(P[:, 0], xs, cz) + P[:, 2] * np.cos(a)
        return np.stack([X, P[:, 1], Z], axis=1), a
    return mappa


# ── materiali ──

def _plastica(c, nome, colore):
    """Plastica lucida da bancarella (il braccialetto, la trombetta, la perlina)."""
    return c.P.materiale(nome, colore, rough=0.22, coat=1.0, sss=0.15)


def _mat_vetro(c, nome, tinta, alfa=0.08, bordo=0.45, fascia=None, argento=(0.86, 0.88, 0.9)):
    """Pelle trasparente come vetro (latterino, ceca): quasi invisibile di fronte, più piena di taglio (così il
    contorno si legge), lucida; fascia = (v0, v1): una fascia d'argento opaca lungo il fianco."""
    m, g = c.P.material(nome)
    v = g.attr('v')
    taglio = g.layer_weight(blend=0.3, which='Facing')
    a = g.add(alfa, g.mul(g.pow(taglio, 2.0), bordo))
    col, metal, rough, velo = tinta, 0.0, 0.12, 0.0
    if fascia is not None:
        # la fascia: chiara e poco metallica (il metallo puro riflette il buio e viene nera), un po' ruvida
        v0, v1 = fascia
        fa = g.mul(g.smoothstep(v0 - 0.05, v0 + 0.02, v), g.smoothstep(v1 + 0.05, v1 - 0.02, v))
        col = g.mix(fa, tinta, argento)
        a = g.mx(a, g.mul(fa, 0.95))
        metal = g.mul(fa, 0.4)
        rough = g.mixf(fa, 0.12, 0.28)
        velo = g.mul(fa, 300.0)              # il velo iridescente dell'argento dei pesci
    g.output_material(g.principled(color=col, metal=metal, rough=rough, coat=1.0, coat_rough=0.03, spec=0.7,
                                   alpha=g.clamp01(a), thin_film=velo))
    return m


def _mat_lama(c):
    """Osso lucidato come una lama (la lisca del pesce sciabola): chiaro, quasi d'argento, con i riflessi."""
    m, g = c.P.material('OssoLama')
    co = g.texcoord('Object')
    n = g.noise(co, scale=40.0, detail=3.0)
    col = g.mix(g.smoothstep(0.4, 0.7, n.fac), (0.9, 0.9, 0.88), (0.74, 0.74, 0.72))
    g.output_material(g.principled(color=col, metal=0.45, rough=0.16, coat=1.0, coat_rough=0.03, spec=0.8,
                                   normal=g.bump(n.fac, strength=0.08, distance=0.001)))
    return m


def _mat_impronta(c, x0, z0, rx, rz, creste=6.5):
    """La pelle del San Pietro con la macchia diventata un'impronta di pollice piccola, da bambino: un ovale
    scuro con le creste a vortice (cerchi deformati dal rumore, nere) e l'anello giallo attorno."""
    lk = c.aspetto
    m, g = c.P.material('PelleImpronta')
    co = g.texcoord('Object')
    x, _, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(g.div(g.sub(x, x0), rx), g.div(g.sub(z, z0), rz), 0.0))
    nz = g.noise(co, scale=110.0, detail=2.0)
    fase = g.mul(g.add(r, g.mul(g.sub(nz.fac, 0.5), 0.16)), creste * 2 * math.pi)
    cresta = g.smoothstep(0.0, 0.6, g.math('SINE', fase))
    dentro = g.smoothstep(1.0, 0.9, r)
    anello = g.mul(g.smoothstep(1.0, 1.08, r), g.smoothstep(1.42, 1.3, r))
    v = g.attr('v')
    col = g.mix(g.smoothstep(-0.55, 0.15, v), lk.belly, lk.flank)
    col = g.mix(g.smoothstep(0.25, 0.75, v), col, lk.back)
    _, vm = g.wave(co, scale=10.0, distortion=9.0, detail=4.0, kind='BANDS', axis='X')
    col = g.mix(g.mul(g.smoothstep(0.78, 0.92, vm), 0.4), col, (0.16, 0.13, 0.08))
    col = g.mix(dentro, col, (0.3, 0.23, 0.14))
    col = g.mix(g.mul(dentro, cresta), col, (0.01, 0.008, 0.006))
    col = g.mix(anello, col, (0.8, 0.62, 0.26))
    g.output_material(g.principled(color=col, rough=0.42, coat=0.5, coat_rough=0.1, metal=0.15, spec=0.5))
    return m


def _mat_vernice(c, n_anelli, nome='VerniceGiostra'):
    """Osso con la vernice da giostra scrostata: anelli rossi, oro, bianchi e azzurri a turno, lucidi di
    smalto, e dove la vernice è saltata l'osso sotto. Usa l'attributo u (che resta giusto anche dopo la
    piega, le coordinate dell'oggetto no)."""
    m, g = c.P.material(nome)
    co = g.texcoord('Object')
    k = g.math('FLOOR', g.add(g.mul(g.attr('u'), float(n_anelli)), 0.5))
    fase = g.add(g.div(g.math('MODULO', k, 4.0), 4.0), 0.1)
    vern = g.ramp(fase, [(0.0, (0.62, 0.025, 0.03)), (0.25, (0.85, 0.58, 0.16)), (0.5, (0.86, 0.83, 0.74)),
                         (0.75, (0.06, 0.28, 0.66))], interp='CONSTANT')
    oro = g.mul(g.smoothstep(0.3, 0.32, fase), g.smoothstep(0.42, 0.4, fase))
    n = g.noise(co, scale=60.0, detail=4.0, rough=0.62)
    scrostata = g.smoothstep(0.55, 0.59, n.fac)
    osso = g.mix(g.smoothstep(0.4, 0.75, n.fac), (0.76, 0.71, 0.58), (0.55, 0.47, 0.34))
    col = g.mix(scrostata, vern, osso)
    g.output_material(g.principled(color=col, metal=g.mul(oro, g.sub(1.0, scrostata)), rough=g.mixf(scrostata, 0.2, 0.42),
                                   coat=g.sub(1.0, scrostata), coat_rough=0.04, spec=0.6))
    return m


# ───────────────────────── le specie ─────────────────────────

# ── Ossiuga (acciuga, Engraulis encrasicolus) ──
# Piccola, affusolata, quasi cilindrica; il muso a punta sporge sopra la bocca enorme, che arriva ben dietro
# l'occhio; una dorsale sola a metà, l'anale dietro, la coda forcuta; dorso verde-blu e la fascia d'argento
# lungo il fianco, che resta come bordo basso della striscia di pelle (striscia_v bassa). Da scheletro:
# «banchi di mille… un rumore di ossicini, come dadi» → tante ossa fitte e sottili: 44 vertebre, costole
# fini e le ossicine fra i muscoli (aghi) delle acciughe vere.
def _lisca_ossiuga(c):
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=44, spessore=0.8, minimo=0.0013, aghi=True)[0])


SPECIE['ossiuga'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.02, 0.018), (0.06, 0.036), (0.12, 0.052), (0.22, 0.066), (0.38, 0.072), (0.55, 0.067),
             (0.72, 0.05), (0.88, 0.03), (1, 0.02)],
        bot=[(0, -0.006), (0.03, -0.022), (0.08, -0.038), (0.16, -0.053), (0.3, -0.064), (0.45, -0.065), (0.6, -0.056),
             (0.78, -0.038), (0.92, -0.024), (1, -0.019)],
        w=[(0, 0.004), (0.05, 0.022), (0.15, 0.04), (0.35, 0.046), (0.6, 0.038), (0.85, 0.02), (1, 0.011)],
        eye_t=0.085, eye_z=0.016, eye_r=0.022, mouth_t=0.16, mouth_z0=-0.005, mouth_z1=-0.03, gill_t=0.22,
        fins=[Fin('dorsal', 0.42, 0.52, [(0, 0), (0.12, 1.0), (0.35, 0.9), (0.7, 0.5), (1, 0.08)], 0.09, 12),
              Fin('anal', 0.64, 0.76, [(0, 0), (0.15, 0.8), (0.5, 0.5), (1, 0.06)], 0.05, 14),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.25), 0.22, 18),
              Fin('pectoral', 0.23, 0.24, PETTORALE, 0.08, 9, z=-0.6),
              Fin('pelvic', 0.44, 0.45, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.012, 0.06, 0.075), flank=(0.05, 0.15, 0.17), belly=(0.7, 0.7, 0.68), fin=(0.3, 0.32, 0.32),
                 iris=(0.7, 0.7, 0.66), iris_dark=(0.12, 0.12, 0.12), metal=0.35, irid=0.45,
                 disegni=[Disegno('strisce', colore=(0.9, 0.92, 0.94), forza=1.0, v0=0.12, v1=0.46, n=1, larghezza=0.3),
                          Disegno('linea', colore=(0.01, 0.04, 0.05), forza=0.7, v=0.45, larghezza=0.05)]),
    extra=_lisca_ossiuga,
    famiglia='skeletal', piano='fusiforme',
    opzioni=dict(vertebre=1, striscia_v=0.17))     # la lisca la fa l'extra (vertebre=1: la famiglia quasi niente)


# ── Spratteschio (spratto, Sprattus sprattus) ──
# Piccolo e compresso, il ventre carenato a scudetti, la bocca piccola all'insù (la mascella di sotto sporge),
# la dorsale a metà, sopra le pelviche. Da scheletro: «il teschio ti sta in punta di dito… batte i denti come
# chi ha freddo» → la testa grande in proporzione, la bocca socchiusa (_apri_bocca) con una fila fitta di
# dentini; e la carena di scudetti d'osso a V lungo il ventre, che negli spratti veri è d'osso e resta.
_BOCCA_SPRATTO = 11.0


def _scudetti(c, t0, t1, n, nome='Scudetti'):
    """La carena del ventre di spratti e sardine: una fila di scudetti d'osso a V che abbracciano il ventre
    (il vertice sulla linea di mezzo, i bracci che salgono sui fianchi e indietro)."""
    oss = _Ossa()
    for t in np.linspace(t0, t1, n):
        zc, h, w = _sez(c.body, t)
        zb = zc - h
        r = max(0.0016, h * 0.026)
        punta = np.array((t, 0.0, zb - 0.002), F)
        # la spina della carena, che punta indietro e in giù (il dente di sega del ventre)
        oss.cono(punta + np.array((-0.004, 0.0, 0.003), F), punta + np.array((0.009, 0.0, -0.005), F), r * 1.5, r * 0.3)
        for s in (-1, 1):
            oss.cono(punta, (t + 0.012, s * w * 0.7, zb + h * 0.42), r * 1.3, r * 0.55)
    return oss.oggetto(c, nome, _osso(c), res=0.0007)


def _extra_spratteschio(c):
    """La lisca, la carena di scudetti, i dentini fitti nella bocca socchiusa."""
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=40, spessore=0.9, minimo=0.0013)[0])
    c.obs.append(_scudetti(c, 0.27, 0.69, 22))
    c.obs.append(_denti(c, n=9, lunghezza=0.0045, raggio=0.0011, apertura=_BOCCA_SPRATTO, dentro=0.9,
                        mat=c.P.materiale('Dentini', (0.86, 0.83, 0.74), rough=0.25, coat=0.7, sss=0.2), nome='Dentini'))


SPECIE['spratteschio'] = Specie(
    forma=Shape(
        top=[(0, 0.006), (0.02, 0.02), (0.06, 0.04), (0.12, 0.062), (0.22, 0.078), (0.36, 0.087), (0.52, 0.082),
             (0.7, 0.057), (0.86, 0.033), (1, 0.021)],
        bot=[(0, -0.003), (0.025, -0.022), (0.07, -0.046), (0.14, -0.07), (0.26, -0.091), (0.4, -0.097), (0.55, -0.088),
             (0.7, -0.062), (0.86, -0.034), (1, -0.021)],
        w=[(0, 0.004), (0.05, 0.02), (0.15, 0.032), (0.35, 0.036), (0.6, 0.029), (0.85, 0.016), (1, 0.009)],
        eye_t=0.1, eye_z=0.022, eye_r=0.027, mouth_t=0.065, mouth_z0=0.008, mouth_z1=-0.012, gill_t=0.26,
        fins=[Fin('dorsal', 0.43, 0.54, [(0, 0), (0.12, 1.0), (0.35, 0.85), (0.7, 0.45), (1, 0.06)], 0.085, 13),
              Fin('anal', 0.7, 0.83, [(0, 0), (0.12, 0.7), (0.5, 0.45), (1, 0.05)], 0.04, 14),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.25), 0.21, 18),
              Fin('pectoral', 0.27, 0.28, PETTORALE, 0.07, 9, z=-0.65),
              Fin('pelvic', 0.41, 0.42, PELVICA, 0.045, 6)]),
    aspetto=Look(back=(0.03, 0.09, 0.12), flank=(0.48, 0.5, 0.48), belly=(0.72, 0.72, 0.68), fin=(0.3, 0.32, 0.3),
                 iris=(0.72, 0.7, 0.62), iris_dark=(0.12, 0.12, 0.1), metal=0.5, irid=0.4,
                 disegni=[Disegno('sfumatura', colore=(0.62, 0.52, 0.3), forza=0.35, v0=0.1, v1=0.5, larghezza=0.15)]),
    campo=_apri_bocca(_BOCCA_SPRATTO), extra=_extra_spratteschio,
    famiglia='skeletal', piano='fusiforme', opzioni=dict(vertebre=1))


# ── Sgombrato (sgombro, Scomber scombrus) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['sgombrato'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.03, 0.022), (0.09, 0.055), (0.2, 0.082), (0.36, 0.092), (0.55, 0.082), (0.75, 0.05), (0.9, 0.026), (1, 0.018)],
        bot=[(0, -0.012), (0.04, -0.035), (0.12, -0.062), (0.3, -0.088), (0.5, -0.085), (0.72, -0.055), (0.9, -0.026), (1, -0.018)],
        w=[(0, 0.004), (0.05, 0.026), (0.15, 0.05), (0.35, 0.058), (0.6, 0.046), (0.85, 0.02), (1, 0.011)],
        eye_t=0.075, eye_z=0.016, eye_r=0.021, mouth_t=0.075, mouth_z0=-0.008, mouth_z1=-0.016, gill_t=0.2,
        fins=[Fin('dorsal', 0.30, 0.42, [(0, 0), (0.15, 0.9), (0.4, 1.0), (0.75, 0.55), (1, 0.08)], 0.11, 10, spiny=True),
              Fin('dorsal', 0.56, 0.64, [(0, 0), (0.25, 0.8), (0.6, 0.55), (1, 0.05)], 0.06, 8),
              Fin('anal', 0.58, 0.66, [(0, 0), (0.25, 0.75), (0.6, 0.5), (1, 0.05)], 0.055, 8),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.55, 0.26), 0.24, 18),
              Fin('pectoral', 0.20, 0.215, [(0, 0), (0.45, 0.35), (1.0, 0.18), (0.8, -0.05), (0, -0.1)], 0.11, 9),
              Fin('pelvic', 0.27, 0.285, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.06, 6)]),
    aspetto=Look(back=(0.08, 0.24, 0.26), flank=(0.32, 0.36, 0.36), belly=(0.62, 0.62, 0.58), fin=(0.10, 0.12, 0.12),
                 iris=(0.55, 0.55, 0.50), iris_dark=(0.10, 0.10, 0.10), pattern='mackerel', irid=0.55),
    famiglia='skeletal', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ── Lattossino (latterino, Atherina boyeri) ──
# Piccolo e slanciato, l'occhio grande, due dorsali ben separate, l'anale sotto la seconda, la coda forcuta;
# la fascia d'argento lungo il fianco. Da scheletro: «trasparente da vivo, ancora di più adesso. Attraverso la
# lisca vedi il fondo» → la pelle resta tutta ma è di vetro (_involucro con _mat_vetro: quasi invisibile di
# fronte, il contorno di taglio), con la sola fascia d'argento opaca; dentro, la lisca sottilissima e chiara.
def _extra_lattossino(c):
    """La lisca sottilissima e chiara, e la pelle di vetro con la fascia d'argento."""
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=44, spessore=0.75, minimo=0.0011, r_min=0.0028)[0])
    c.obs.append(_involucro(c, _mat_vetro(c, 'PelleLatterino', (0.55, 0.66, 0.6), alfa=0.06, bordo=0.4,
                                          fascia=(-0.14, 0.2), argento=(0.92, 0.94, 0.96))))


SPECIE['lattossino'] = Specie(
    forma=Shape(
        top=[(0, -0.002), (0.02, 0.016), (0.06, 0.034), (0.12, 0.05), (0.22, 0.062), (0.38, 0.066), (0.55, 0.06),
             (0.72, 0.045), (0.88, 0.028), (1, 0.019)],
        bot=[(0, -0.01), (0.03, -0.026), (0.08, -0.042), (0.16, -0.056), (0.3, -0.064), (0.45, -0.063), (0.6, -0.052),
             (0.76, -0.036), (0.9, -0.024), (1, -0.019)],
        w=[(0, 0.004), (0.05, 0.02), (0.15, 0.034), (0.35, 0.038), (0.6, 0.03), (0.85, 0.016), (1, 0.01)],
        eye_t=0.088, eye_z=0.012, eye_r=0.028, mouth_t=0.06, mouth_z0=-0.002, mouth_z1=-0.016, gill_t=0.2,
        fins=[Fin('dorsal', 0.38, 0.45, [(0, 0), (0.15, 1.0), (0.5, 0.8), (1, 0.1)], 0.06, 7, spiny=True),
              Fin('dorsal', 0.58, 0.68, [(0, 0), (0.15, 0.9), (0.5, 0.65), (1, 0.08)], 0.06, 10),
              Fin('anal', 0.56, 0.7, [(0, 0), (0.12, 0.85), (0.5, 0.55), (1, 0.06)], 0.05, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.55, 0.28), 0.2, 18),
              Fin('pectoral', 0.21, 0.22, PETTORALE, 0.08, 9, z=0.1),
              Fin('pelvic', 0.4, 0.41, PELVICA, 0.04, 6)]),
    aspetto=Look(back=(0.3, 0.36, 0.3), flank=(0.6, 0.64, 0.58), belly=(0.72, 0.72, 0.68), fin=(0.4, 0.42, 0.4),
                 iris=(0.75, 0.75, 0.7), iris_dark=(0.12, 0.12, 0.12), metal=0.4, irid=0.3),
    extra=_extra_lattossino,
    famiglia='skeletal', piano='fusiforme',
    opzioni=dict(vertebre=1, striscia=False, peduncolo=None, osso=(1.12, 1.14, 1.2)))


# ── Bogossa (boga, Boops boops) ──
# Sparide slanciato con gli occhi enormi, la bocca piccola, la dorsale lunga (spine e raggi molli), la coda
# forcuta; da viva tre o quattro righe dorate e una macchietta scura all'ascella della pettorale. Da scheletro:
# «ha gli occhi enormi di quando era viva. Le sono rimasti solo quelli» → gli occhi grandissimi, intatti e
# lucidi nel cranio spolpato, e niente pelle: né striscia né peduncolo (la lisca con le ossa delle pinne e il
# ventaglio della coda).
def _extra_bogossa(c):
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=24, spessore=1.1, minimo=0.0015, pterigiofori=True, ipurale=True)[0])


SPECIE['bogossa'] = Specie(
    forma=Shape(
        top=[(0, -0.008), (0.02, 0.016), (0.06, 0.044), (0.12, 0.07), (0.22, 0.09), (0.36, 0.098), (0.52, 0.09),
             (0.7, 0.062), (0.86, 0.036), (1, 0.025)],
        bot=[(0, -0.02), (0.03, -0.04), (0.08, -0.058), (0.16, -0.078), (0.3, -0.092), (0.45, -0.09), (0.6, -0.075),
             (0.76, -0.05), (0.9, -0.031), (1, -0.025)],
        w=[(0, 0.005), (0.05, 0.024), (0.15, 0.038), (0.35, 0.042), (0.6, 0.034), (0.85, 0.018), (1, 0.011)],
        eye_t=0.105, eye_z=0.018, eye_r=0.038, mouth_t=0.06, mouth_z0=-0.012, mouth_z1=-0.022, gill_t=0.25,
        fins=[Fin('dorsal', 0.32, 0.78, [(0, 0), (0.05, 0.85), (0.2, 1.0), (0.45, 0.8), (0.6, 0.7), (0.8, 0.75), (0.95, 0.5),
                                         (1, 0.05)], 0.085, 26, spiny=True),
              Fin('anal', 0.6, 0.8, [(0, 0), (0.1, 0.8), (0.5, 0.6), (0.9, 0.55), (1, 0.05)], 0.055, 14),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.3), 0.22, 18),
              Fin('pectoral', 0.26, 0.27, PETTORALE, 0.1, 10),
              Fin('pelvic', 0.33, 0.34, PELVICA, 0.06, 6, spiny=True)]),
    aspetto=Look(back=(0.18, 0.2, 0.12), flank=(0.55, 0.56, 0.48), belly=(0.75, 0.74, 0.68), fin=(0.3, 0.3, 0.26),
                 iris=(0.85, 0.8, 0.6), iris_dark=(0.3, 0.26, 0.14), metal=0.5, irid=0.3,
                 disegni=[Disegno('strisce', colore=(0.85, 0.66, 0.22), forza=0.7, v0=-0.35, v1=0.45, n=4, larghezza=0.035)]),
    extra=_extra_bogossa,
    famiglia='skeletal', piano='fusiforme', opzioni=dict(vertebre=1, striscia=False, peduncolo=None))


# ── Zerossa (zerro, Spicara smaris) ──
# Piccolo e slanciato, il muso a punta con la bocca protrattile, la dorsale lunga, la coda forcuta; da vivo la
# macchia scura sul fianco sopra la pettorale. Da scheletro: «pulito come se l'avessero mangiato con calma, un
# boccone alla volta» → ossa pulitissime e chiare (niente pelle, niente peduncolo, le ossa senza sporco) e i
# segni regolari dei morsi: archi tondi tolti uno dopo l'altro al bordo del ventre e sopra la coda.
_MORSO = 0.046          # il raggio dei morsi dello zerro: tutti uguali, un boccone alla volta


def _morsi_zerossa(body):
    """I morsi dello zerro, (x, z, raggio) sul fianco: quattro in fila lungo il ventre, uno sopra la coda."""
    R = _MORSO
    m = [(x, float(body.bot(np.array([x], F))[0]) + R * 0.12, R) for x in (0.3, 0.375, 0.45, 0.525)]
    return m + [(0.86, float(body.top(np.array([0.86], F))[0]) + R * 0.2, R * 0.85)]


def _morso_nuca(c, f):
    """campo: un morso tondo e netto dalla nuca del cranio (un cilindro di traverso, come i morsi della lisca)."""
    x = _x_cranio(c) - 0.02
    z = float(c.body.top(np.array([x], F))[0]) + _MORSO * 0.25

    def g(p):
        return np.maximum(f(p), -(np.sqrt((p[:, 0] - x) ** 2 + (p[:, 2] - z) ** 2) - _MORSO * 0.8)).astype(F)
    return g


def _extra_zerossa(c):
    body = c.body
    morsi = _morsi_zerossa(body)
    pulite = c.P.bone_material('OssaPulite', dirt=0.05, tinta=(1.14, 1.12, 1.08))
    _rivesti(c, 'Skull', pulite)
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=24, spessore=1.1, minimo=0.0015, pterigiofori=True, ipurale=True, morsi=morsi,
                        mat=pulite)[0])


SPECIE['zerossa'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.02, 0.014), (0.06, 0.038), (0.12, 0.06), (0.22, 0.08), (0.36, 0.088), (0.52, 0.082),
             (0.7, 0.058), (0.86, 0.034), (1, 0.022)],
        bot=[(0, -0.014), (0.03, -0.032), (0.08, -0.05), (0.16, -0.068), (0.3, -0.082), (0.45, -0.08), (0.6, -0.066),
             (0.76, -0.046), (0.9, -0.029), (1, -0.022)],
        w=[(0, 0.004), (0.05, 0.02), (0.15, 0.033), (0.35, 0.037), (0.6, 0.03), (0.85, 0.016), (1, 0.01)],
        eye_t=0.09, eye_z=0.016, eye_r=0.024, mouth_t=0.07, mouth_z0=-0.01, mouth_z1=-0.024, gill_t=0.23,
        fins=[Fin('dorsal', 0.3, 0.76, [(0, 0), (0.06, 0.9), (0.22, 1.0), (0.45, 0.75), (0.55, 0.62), (0.7, 0.7), (0.9, 0.6),
                                        (1, 0.06)], 0.08, 26, spiny=True),
              Fin('anal', 0.58, 0.77, [(0, 0), (0.1, 0.8), (0.5, 0.6), (0.9, 0.5), (1, 0.05)], 0.05, 14),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.28), 0.22, 18),
              Fin('pectoral', 0.24, 0.25, PETTORALE, 0.09, 10),
              Fin('pelvic', 0.3, 0.31, PELVICA, 0.055, 6, spiny=True)]),
    aspetto=Look(back=(0.2, 0.18, 0.14), flank=(0.5, 0.5, 0.46), belly=(0.74, 0.73, 0.68), fin=(0.3, 0.28, 0.24),
                 iris=(0.7, 0.66, 0.5), iris_dark=(0.18, 0.15, 0.08), metal=0.45, irid=0.3,
                 disegni=[Disegno('macchia', colore=(0.04, 0.035, 0.03), forza=0.85, u=0.36, v=0.25, r=0.025, allungamento=1.3)]),
    campo=_morso_nuca, extra=_extra_zerossa,
    famiglia='skeletal', piano='fusiforme', opzioni=dict(vertebre=1, striscia=False, peduncolo=None))


# ── Occhiata Vuota (occhiata, Oblada melanura) ──
# Sparide ovale, l'occhio grande, la bocca piccola, la dorsale lunga, la coda forcuta; grigio argento con
# righe tenui e, sul peduncolo, la macchia nera cerchiata di bianco. Da scheletro: «al posto degli occhi ha due
# buchi… e ti guarda lo stesso» → le orbite vuote (occhi=False), e la macchia che resta sul peduncolo carnoso
# (peduncolo più lungo, da 0.86): nera, cerchiata di bianco, è lei che guarda.
SPECIE['occhiata_vuota'] = Specie(
    forma=Shape(
        top=[(0, -0.015), (0.02, 0.012), (0.06, 0.05), (0.12, 0.09), (0.22, 0.13), (0.36, 0.148), (0.52, 0.138),
             (0.7, 0.096), (0.85, 0.055), (0.95, 0.04), (1, 0.038)],
        bot=[(0, -0.03), (0.03, -0.055), (0.1, -0.09), (0.22, -0.125), (0.38, -0.14), (0.55, -0.128), (0.72, -0.09),
             (0.86, -0.052), (0.95, -0.04), (1, -0.038)],
        w=[(0, 0.006), (0.06, 0.03), (0.2, 0.05), (0.4, 0.055), (0.65, 0.043), (0.85, 0.022), (1, 0.014)],
        eye_t=0.125, eye_z=0.04, eye_r=0.032, mouth_t=0.055, mouth_z0=-0.02, mouth_z1=-0.03, gill_t=0.27,
        fins=[Fin('dorsal', 0.33, 0.8, [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.8), (0.8, 0.72), (0.95, 0.5), (1, 0.05)],
                  0.11, 24, spiny=True),
              Fin('anal', 0.6, 0.8, [(0, 0), (0.12, 0.9), (0.6, 0.62), (0.95, 0.5), (1, 0.05)], 0.08, 14),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.32), 0.25, 20),
              Fin('pectoral', 0.29, 0.3, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.17, 12),
              Fin('pelvic', 0.34, 0.35, PELVICA, 0.09, 7, spiny=True)]),
    aspetto=Look(back=(0.2, 0.23, 0.25), flank=(0.48, 0.51, 0.53), belly=(0.72, 0.72, 0.7), fin=(0.18, 0.2, 0.22),
                 iris=(0.7, 0.66, 0.5), metal=0.5, irid=0.3,
                 disegni=[Disegno('strisce', colore=(0.18, 0.2, 0.22), forza=0.35, v0=-0.5, v1=0.7, n=8, larghezza=0.025),
                          Disegno('ocello', colore=(0.008, 0.008, 0.01), colore2=(0.93, 0.92, 0.88), u=0.935, v=0.02,
                                  r=0.03, allungamento=1.25)]),
    famiglia='skeletal', piano='fusiforme', opzioni=dict(occhi=False, peduncolo=0.86))


# ── Ossaguglia (aguglia, Belone belone) — dalla prova del becco (piano 'rostro'; le altre famiglie copiano la
#    forma da qui: la forma è quella della prova) ──
# Lunghissima e sottile; le due mascelle a becco sono un Rostro('becco') alla quota della bocca (il taglio
# arriva in punta e lo divide in due); dorsale e anale arretrate e opposte, coda forcuta con il lobo di sotto
# più lungo; dorso verde-azzurro, fianchi d'argento. Da scheletro: «ha le ossa verdi… un becco pieno di
# dentini. Ti punge» → le ossa verdi (le ha davvero, da viva), la lisca lunghissima (50 vertebre) e al posto
# dei dentini della prova (elementi=False) quelli dell'extra, più grossi, aguzzi e sporchi.
def _extra_ossaguglia(c):
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=50, spessore=1.1, minimo=0.0014)[0])
    c.obs.append(c.P.denti_becco(c.body, n=34, lunghezza=0.0065, raggio=0.0015, mat=c.P.dirty_teeth_material(),
                                 nome='DentiAguzzi'))


SPECIE['ossaguglia'] = Specie(
    forma=Shape(
        top=[(0, 0.004), (0.02, 0.012), (0.06, 0.022), (0.12, 0.03), (0.25, 0.037), (0.45, 0.04), (0.62, 0.038), (0.75, 0.032),
             (0.88, 0.021), (0.96, 0.014), (1, 0.012)],
        bot=[(0, -0.006), (0.03, -0.014), (0.08, -0.023), (0.18, -0.032), (0.4, -0.038), (0.6, -0.037), (0.75, -0.031),
             (0.88, -0.021), (0.96, -0.013), (1, -0.012)],
        w=[(0, 0.007), (0.05, 0.016), (0.15, 0.024), (0.4, 0.028), (0.65, 0.025), (0.85, 0.015), (1, 0.008)],
        eye_t=0.055, eye_z=0.007, eye_r=0.0135, mouth_t=0.05, mouth_z0=-0.0015, mouth_z1=-0.004, gill_t=0.13,
        rostro=Rostro('becco', lunghezza=0.42, z=-0.0015, larghezza=0.0085, altezza=0.0095, punta=0.3, denti=28),
        fins=[Fin('dorsal', 0.68, 0.86, [(0, 0), (0.06, 0.95), (0.2, 0.7), (0.6, 0.55), (0.9, 0.75), (1, 0.35)], 0.04, 22),
              Fin('anal', 0.65, 0.84, [(0, 0), (0.06, 0.95), (0.2, 0.7), (0.6, 0.55), (0.9, 0.7), (1, 0.3)], 0.036, 22),
              Fin('caudal', 1.0, 1.0, [(0.0, 1.0), (0.5, 1.1), (0.95, 1.5), (0.32, 0.0), (1.1, -1.75), (0.55, -1.1), (0.0, -1.0)],
                  0.12, 18),
              Fin('pectoral', 0.12, 0.13, PETTORALE, 0.06, 9, z=0.25),
              Fin('pelvic', 0.5, 0.51, PELVICA, 0.04, 6)]),
    aspetto=Look(back=(0.02, 0.1, 0.11), flank=(0.38, 0.44, 0.45), belly=(0.72, 0.74, 0.72), fin=(0.1, 0.16, 0.17),
                 iris=(0.75, 0.72, 0.55), iris_dark=(0.1, 0.1, 0.08), metal=0.7, irid=0.45, squame=0.25,
                 linea_laterale=0.0,
                 disegni=[Disegno('ventre', colore=(0.8, 0.82, 0.84), forza=0.6, v1=-0.3)]),
    extra=_extra_ossaguglia,
    famiglia='skeletal', piano='rostro', opzioni=dict(vertebre=1, osso=(0.38, 0.95, 0.6), elementi=False))


# ── Ago d'Osso (pesce ago, Syngnathus acus) ──
# Lunghissimo e sottilissimo (alto un trentesimo), rigido, il muso a tubo lungo, il corpo fatto di anelli
# ossei (Shape.anelli), una dorsale piccola a metà, niente pelviche. Da scheletro: «un ago da cucito fatto
# d'osso. Qualcuno lo usa ancora per ricucire» → il pesce ago è già tutto corazza: qui è tutto osso (il
# cranio arriva fino in coda, cranio_t oltre 1, con gli anelli in rilievo), e la coda finisce nella cruna di
# un ago con un filo rosso infilato che pende. Il corpo d'osso lo fa l'extra (il cranio della famiglia sul corpo
# così sottile apre il buco dell'opercolo da parte a parte e si mangia la coda): liscio, lucido, con le orbite.
def _extra_ago(c):
    """L'ago d'osso (il corpo intero con gli anelli), la cruna in fondo alla coda e il filo rosso infilato, con
    il nodo in fondo."""
    P = c.P
    _togli(c, 'Spine', 'Skull')
    corpo = c.body.field(socket=True)
    lo, hi = c.body.bounds()
    c.obs.append(P.oggetto_sdf('Ago', corpo, lo, hi, P.bone_material('OssoLucido', dirt=0.15), res=0.0008))
    zc, h, _ = _sez(c.body, 1.0)
    a, b, rt = 0.015, 0.0085, 0.0032          # la cruna: mezza lunghezza del tratto dritto, raggio, spessore
    xc = 0.993 + a + b
    collo = P.sdf.round_cone((0.975, 0.0, zc), (xc - a - b + 0.001, 0.0, zc), h * 1.05, rt * 1.1)

    def cruna(p):
        # un anello a stadio nel piano del ritratto (XZ), attaccato in fondo alla coda
        sx = np.clip(p[:, 0], xc - a, xc + a)
        d2 = np.sqrt((p[:, 0] - sx) ** 2 + (p[:, 2] - zc) ** 2) - b
        anello = np.sqrt(d2 * d2 + p[:, 1] ** 2) - rt
        return P.sdf.smin(anello, collo(p), 0.003).astype(F)
    lo = np.array((0.965, -0.015, zc - 0.02), F)
    hi = np.array((xc + a + b + 0.01, 0.015, zc + 0.02), F)
    c.obs.append(P.oggetto_sdf('Cruna', cruna, lo, hi, P.bone_material('OssoLucido', dirt=0.15), res=0.0005))
    # il filo: passa nella cruna (lungo y), un capo corto dietro e uno lungo che pende davanti, col nodo
    xf = xc + 0.004
    corto = [(xf + 0.012, 0.005, zc - 0.042), (xf + 0.01, 0.006, zc - 0.022), (xf + 0.005, 0.006, zc - 0.006),
             (xf, 0.0035, zc)]
    lungo = [(xf, -0.0035, zc), (xf - 0.002, -0.007, zc - 0.006), (xf - 0.008, -0.008, zc - 0.03),
             (xf - 0.013, -0.006, zc - 0.065), (xf - 0.004, -0.004, zc - 0.1), (xf + 0.014, -0.003, zc - 0.118)]
    filo = _Ossa()
    pts = _curva(c, corto + lungo, 60)
    filo.spezzata(pts, 0.0016, 0.0016, passo=0.004)
    filo.nodo(pts[-1], 0.0027)
    rosso = c.P.materiale('FiloRosso', (0.5, 0.02, 0.025), rough=0.55, coat=0.2, sss=0.1)
    c.obs.append(filo.oggetto(c, 'Filo', rosso, res=0.0005))


SPECIE['ago_dosso'] = Specie(
    forma=Shape(
        top=[(0, 0.004), (0.02, 0.012), (0.05, 0.017), (0.08, 0.016), (0.12, 0.016), (0.2, 0.018), (0.35, 0.019),
             (0.5, 0.017), (0.7, 0.013), (0.85, 0.0095), (1, 0.007)],
        bot=[(0, -0.006), (0.02, -0.012), (0.05, -0.016), (0.1, -0.016), (0.2, -0.019), (0.33, -0.021), (0.45, -0.018),
             (0.6, -0.013), (0.8, -0.0095), (1, -0.007)],
        w=[(0, 0.005), (0.04, 0.012), (0.1, 0.012), (0.25, 0.015), (0.45, 0.013), (0.7, 0.0095), (1, 0.006)],
        eye_t=0.045, eye_z=0.005, eye_r=0.0065, bocca='nessuna', gill_t=0.085, anelli=50, anelli_tratto=(0.09, 0.99),
        rostro=Rostro('tubo', lunghezza=0.075, z=-0.002, larghezza=0.005, altezza=0.0055, punta=0.85),
        fins=[Fin('dorsal', 0.4, 0.5, [(0, 0), (0.1, 0.9), (0.5, 1.0), (0.9, 0.9), (1, 0.1)], 0.02, 24),
              Fin('pectoral', 0.09, 0.1, PETTORALE_TONDA, 0.016, 8, z=0.0)]),
    aspetto=Look(back=(0.2, 0.17, 0.1), flank=(0.28, 0.24, 0.15), belly=(0.4, 0.34, 0.22), fin=(0.3, 0.26, 0.18),
                 iris=(0.7, 0.6, 0.3), iris_dark=(0.15, 0.1, 0.04), metal=0.05, irid=0.1, squame=0.0, linea_laterale=0.0),
    extra=_extra_ago,
    famiglia='skeletal', piano='rostro',
    opzioni=dict(cranio_t=1.02, striscia=False, peduncolo=None, vertebre=1))   # il cranio è tutto il pesce


# ── San Pietrificato (pesce San Pietro, Zeus faber) — dalla prova del piano 'alto' (la forma è quella della
#    prova: le altre famiglie la copiano da qui) ──
# Corpo alto quasi quanto lungo e sottilissimo; le spine della dorsale con i filamenti lunghi (la sagoma a
# punte, con tanti raggi perché la membrana le segua); la macchia nera cerchiata di giallo sul fianco. Da
# scheletro: «l'impronta di un pollice… piccolo, come quello di un bambino» → lo scheletro del corpo alto
# (_lisca più spessa: spine lunghe fino ai bordi, le ossa sotto le pinne alte), i filamenti della dorsale come
# raggi d'osso (le pinne della famiglia), e sul fianco un lembo di pelle rimasto sulle ossa con la macchia
# diventata un'impronta di pollice piccola, con le creste.
def _extra_san_pietrificato(c):
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=30, spessore=1.8, minimo=0.0028, costole_dietro=0.04, pterigiofori=True)[0])
    x0 = 0.46
    zc, h, _ = _sez(c.body, x0)
    z0 = zc + h * 0.05
    c.obs.append(_lembo(c, x0, z0, 0.064, _mat_impronta(c, x0, z0, 0.03, 0.039, creste=5.0), nome='LemboImpronta', seme=4))


SPECIE['san_pietrificato'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.03, 0.03), (0.08, 0.1), (0.15, 0.18), (0.25, 0.255), (0.35, 0.29), (0.5, 0.275), (0.65, 0.215),
             (0.8, 0.13), (0.92, 0.055), (1, 0.03)],
        bot=[(0, -0.06), (0.04, -0.1), (0.1, -0.17), (0.2, -0.245), (0.32, -0.29), (0.45, -0.29), (0.6, -0.245), (0.75, -0.17),
             (0.9, -0.07), (1, -0.03)],
        w=[(0, 0.006), (0.08, 0.024), (0.25, 0.038), (0.5, 0.04), (0.75, 0.028), (0.92, 0.014), (1, 0.009)],
        eye_t=0.2, eye_z=0.055, eye_r=0.032, mouth_t=0.09, mouth_z0=-0.012, mouth_z1=-0.095, gill_t=0.33,
        fins=[Fin('dorsal', 0.3, 0.5, [(0, 0), (0.04, 1.8), (0.08, 0.5), (0.15, 2.2), (0.2, 0.55), (0.27, 2.4), (0.32, 0.55),
                                      (0.39, 2.45), (0.44, 0.55), (0.51, 2.4), (0.56, 0.55), (0.63, 2.2), (0.68, 0.5), (0.75, 1.9),
                                      (0.8, 0.45), (0.87, 1.5), (0.92, 0.4), (1, 0.3)], 0.14, 90, spiny=True),
              Fin('dorsal', 0.52, 0.86, [(0, 0.3), (0.1, 0.75), (0.4, 0.85), (0.8, 0.6), (1, 0.05)], 0.1, 24),
              Fin('anal', 0.47, 0.86, [(0, 0), (0.05, 0.9), (0.12, 0.45), (0.2, 0.7), (0.5, 0.8), (0.85, 0.55), (1, 0.05)], 0.09, 28),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.7, 1.0), 0.15, 18),
              Fin('pectoral', 0.36, 0.37, PETTORALE_TONDA, 0.08, 10),
              Fin('pelvic', 0.3, 0.32, [(0, 0), (0.5, 0.18), (1.0, 0.05), (0.85, -0.05), (0, -0.06)], 0.16, 8, spiny=True)]),
    aspetto=Look(back=(0.26, 0.22, 0.14), flank=(0.40, 0.36, 0.24), belly=(0.52, 0.48, 0.36), fin=(0.22, 0.19, 0.14),
                 iris=(0.8, 0.65, 0.3), iris_dark=(0.25, 0.18, 0.06), metal=0.35, irid=0.25, squame=0.3,
                 disegni=[Disegno('vermi', colore=(0.16, 0.13, 0.08), forza=0.4, scala=40),
                          Disegno('ocello', colore=(0.02, 0.02, 0.02), colore2=(0.78, 0.62, 0.28), u=0.46, v=0.05, r=0.042)]),
    extra=_extra_san_pietrificato,
    famiglia='skeletal', piano='alto', opzioni=dict(vertebre=1))


# ── Ceca Ossuta (ceca, l'anguilla giovane, Anguilla anguilla) ──
# Un'anguillina minuscola e trasparente: dorsale, anale e coda continue (la dorsale parte a un terzo), la testa
# piccola, gli occhi neri, l'asse a S. Da scheletro: «non ha mai avuto niente da nascondere… adesso si vede
# anche quello che ha mangiato» → il corpo resta tutto ma di vetro (_involucro), dentro la lisca sottile, e
# nella pancia quello che ha mangiato: una perlina di plastica rosa di un braccialetto e un dentino da latte.
def _extra_ceca(c):
    """La lisca sottile, il corpo di vetro, e nella pancia la perlina e il dentino."""
    P, body = c.P, c.body
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=70, spessore=0.8, minimo=0.0009, r_min=0.0024, costole_fino=0.42, emali_da=0.42)[0])
    c.obs.append(_involucro(c, _mat_vetro(c, 'PelleCeca', (0.62, 0.66, 0.66), alfa=0.05, bordo=0.5)))
    # la perlina, con il buco lungo il corpo
    zc, h, w = _sez(body, 0.27)
    cp = np.array((0.27, -w * 0.3, zc - h * 0.18), F)
    rp = min(h * 0.45, 0.0115)

    def perlina(p):
        buco = np.sqrt(p[:, 1] ** 2 + (p[:, 2] - cp[2]) ** 2) - rp * 0.36
        return np.maximum(np.linalg.norm(p - cp, axis=1) - rp, -buco).astype(F)
    c.obs.append(P.oggetto_sdf('Perlina', perlina, cp - rp - 0.004, cp + rp + 0.004, _plastica(c, 'PlasticaRosa', (0.95, 0.12, 0.4)),
                               res=0.0005))
    # il dentino da latte: la corona schiacciata e la radice corta, storto
    zc, h, w = _sez(body, 0.36)
    cd = np.array((0.36, -w * 0.45, zc - h * 0.15), F)
    Rz = P.sdf.rot_matrix('y', 28.0)
    corona = P.sdf.ellipsoid((0.0, 0.0, 0.003), (0.0062, 0.0036, 0.0075))
    radice = P.sdf.round_cone((0.0, 0.0, -0.0015), (0.0015, 0.0, -0.0125), 0.0038, 0.001)

    def dente(p):
        q = ((p - cd) @ Rz).astype(F)
        return P.sdf.smin(corona(q), radice(q), 0.0015).astype(F)
    c.obs.append(P.oggetto_sdf('DentinoDaLatte', dente, cd - 0.018, cd + 0.018,
                               P.materiale('Smalto', (0.88, 0.86, 0.8), rough=0.2, coat=0.9, sss=0.25), res=0.00035))


SPECIE['ceca_ossuta'] = Specie(
    forma=Shape(
        top=[(0, -0.002), (0.015, 0.008), (0.04, 0.016), (0.08, 0.022), (0.14, 0.026), (0.3, 0.028), (0.5, 0.027),
             (0.7, 0.022), (0.85, 0.016), (0.95, 0.008), (1, 0.003)],
        bot=[(0, -0.008), (0.02, -0.013), (0.05, -0.019), (0.1, -0.024), (0.2, -0.028), (0.4, -0.029), (0.6, -0.025),
             (0.8, -0.017), (0.93, -0.009), (1, -0.003)],
        w=[(0, 0.003), (0.04, 0.012), (0.1, 0.018), (0.3, 0.02), (0.6, 0.015), (0.85, 0.009), (1, 0.002)],
        eye_t=0.04, eye_z=0.006, eye_r=0.0085, mouth_t=0.04, mouth_z0=-0.005, mouth_z1=-0.009, gill_t=0.11,
        fins=[Fin('dorsal', 0.33, 1.0, [(0, 0), (0.04, 0.7), (0.15, 0.95), (0.5, 1.0), (0.9, 1.0), (1, 0.6)], 0.022, 110),
              Fin('anal', 0.42, 1.0, [(0, 0), (0.05, 0.7), (0.2, 0.95), (0.9, 1.0), (1, 0.6)], 0.02, 100),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.9, 1.0), 0.03, 16),
              Fin('pectoral', 0.12, 0.13, PETTORALE_TONDA, 0.03, 8, z=0.0)],
        piega=[(0, -8), (0.25, 10), (0.5, -10), (0.75, 10), (1.0, -4)]),
    aspetto=Look(back=(0.45, 0.5, 0.5), flank=(0.55, 0.6, 0.6), belly=(0.62, 0.66, 0.66), fin=(0.5, 0.55, 0.55),
                 iris=(0.02, 0.02, 0.025), iris_dark=(0.006, 0.006, 0.008), metal=0.1, irid=0.2, squame=0.0, linea_laterale=0.0),
    extra=_extra_ceca,
    famiglia='skeletal', piano='anguilliforme',
    opzioni=dict(vertebre=1, striscia=False, peduncolo=None, osso=(1.1, 1.12, 1.15)))


# ── Lucertossa (pesce lucertola, Synodus saurus) ──
# Cilindrico, la testa piatta da lucertola col muso a punta, la bocca lunghissima (arriva ben dietro l'occhio),
# l'occhio alto, una dorsale alta a metà, la pinna adiposa, le pelviche grandi, la coda forcuta; righe blu e
# gialle. Da scheletro: «più denti che ossa… sorride anche da morto» → la bocca aperta nel ghigno (_apri_bocca)
# con tre file di denti ad ago lungo tutte e due le mascelle.
_BOCCA_LUCERTOLA = 15.0


def _extra_lucertossa(c):
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=50, spessore=1.0, minimo=0.0014)[0])
    c.obs.append(_denti(c, n=24, lunghezza=0.0068, raggio=0.0013, file=3, apertura=_BOCCA_LUCERTOLA, seme=2,
                        nome='DentiLucertola'))


SPECIE['lucertossa'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.02, 0.008), (0.06, 0.02), (0.12, 0.033), (0.2, 0.048), (0.32, 0.061), (0.48, 0.064),
             (0.65, 0.055), (0.82, 0.04), (0.92, 0.03), (1, 0.025)],
        bot=[(0, -0.012), (0.03, -0.026), (0.08, -0.04), (0.15, -0.052), (0.28, -0.062), (0.45, -0.063), (0.62, -0.055),
             (0.8, -0.04), (0.92, -0.03), (1, -0.025)],
        w=[(0, 0.005), (0.04, 0.022), (0.12, 0.038), (0.3, 0.052), (0.55, 0.048), (0.8, 0.032), (1, 0.014)],
        eye_t=0.1, eye_z=0.022, eye_r=0.017, mouth_t=0.18, mouth_z0=-0.008, mouth_z1=-0.022, gill_t=0.23,
        fins=[Fin('dorsal', 0.38, 0.47, [(0, 0), (0.08, 1.0), (0.3, 0.95), (0.7, 0.55), (1, 0.12)], 0.11, 12),
              Fin('dorsal', 0.79, 0.83, [(0, 0), (0.3, 0.9), (0.7, 0.85), (1, 0.05)], 0.022, 10, carnosa=True, spessore=0.003),
              Fin('anal', 0.72, 0.8, [(0, 0), (0.15, 0.8), (0.5, 0.6), (1, 0.06)], 0.05, 10),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.28), 0.2, 18),
              Fin('pectoral', 0.22, 0.23, PETTORALE, 0.08, 10, z=0.05),
              Fin('pelvic', 0.33, 0.34, [(0, 0), (0.5, 0.3), (1.0, 0.15), (0.8, -0.05), (0, -0.08)], 0.11, 9)]),
    aspetto=Look(back=(0.1, 0.075, 0.05), flank=(0.3, 0.25, 0.17), belly=(0.75, 0.72, 0.62), fin=(0.35, 0.3, 0.22),
                 iris=(0.8, 0.7, 0.35), iris_dark=(0.2, 0.15, 0.05), metal=0.15, irid=0.2,
                 disegni=[Disegno('bande', colore=(0.04, 0.03, 0.02), forza=0.6, u0=0.25, u1=0.95, n=7, larghezza=0.4, v0=0.55),
                          Disegno('strisce', colore=(0.06, 0.22, 0.65), forza=0.9, v0=0.3, v1=0.9, n=3, larghezza=0.07),
                          Disegno('strisce', colore=(0.85, 0.66, 0.1), forza=0.9, v0=0.4, v1=1.0, n=3, larghezza=0.06)]),
    campo=_apri_bocca(_BOCCA_LUCERTOLA), extra=_extra_lucertossa,
    famiglia='skeletal', piano='fusiforme', opzioni=dict(vertebre=1, striscia_v=0.3))


# ── Sciabola Spolpata (pesce sciabola, Lepidopus caudatus) — dalla prova del piano 'nastriforme' (la forma è
#    quella della prova: le altre famiglie la copiano da qui) ──
# Un nastro d'argento senza squame: la dorsale bassa da dietro la testa quasi alla coda, la coda minuscola. Da
# scheletro: «lungo come un braccio, sottile come una lama… rumore di posate» → spolpata: niente striscia di
# pelle, la lisca lunghissima (70 vertebre, le costole fino in fondo) d'osso lucido come una lama (_mat_lama),
# le zanne della prova.
def _denti_sciabola(c):
    """Le zanne davanti, nelle due mascelle (aiuto comune: denti_mascelle)."""
    c.obs += c.P.denti_mascelle(c.body, n=6, lunghezza=0.0045, zanne=(0, 1), nome='DenteSciabola')


def _extra_sciabola(c):
    _denti_sciabola(c)
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=70, costole_fino=1.0, emali_da=1.0, spessore=1.0, minimo=0.0015, costole_dietro=0.02,
                        mat=_mat_lama(c))[0])


SPECIE['sciabola_spolpata'] = Specie(
    forma=Shape(
        top=[(0, -0.002), (0.02, 0.008), (0.06, 0.022), (0.12, 0.033), (0.25, 0.038), (0.6, 0.034), (0.85, 0.02), (0.95, 0.01),
             (1, 0.005)],
        bot=[(0, -0.009), (0.03, -0.017), (0.08, -0.027), (0.15, -0.033), (0.4, -0.036), (0.7, -0.03), (0.9, -0.014), (1, -0.005)],
        w=[(0, 0.003), (0.05, 0.01), (0.15, 0.013), (0.5, 0.011), (0.8, 0.006), (1, 0.002)],
        eye_t=0.068, eye_z=0.008, eye_r=0.012, mouth_t=0.07, mouth_z0=-0.006, mouth_z1=-0.004, gill_t=0.13,
        fins=[Fin('dorsal', 0.11, 0.97, [(0, 0), (0.01, 0.9), (0.5, 1.0), (0.95, 0.8), (1, 0.2)], 0.022, 130, spiny=True),
              Fin('anal', 0.78, 0.95, [(0, 0), (0.1, 0.6), (0.9, 0.5), (1, 0.1)], 0.006, 20),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.4, 0.3), 0.045, 12),
              Fin('pectoral', 0.135, 0.145, PETTORALE, 0.035, 8)],
        piega=[(0, 0), (0.35, 5), (0.7, -5), (1, 3)]),
    aspetto=Look(back=(0.42, 0.45, 0.5), flank=(0.66, 0.68, 0.7), belly=(0.72, 0.73, 0.74), fin=(0.55, 0.58, 0.6),
                 iris=(0.85, 0.82, 0.7), iris_dark=(0.15, 0.15, 0.12), metal=0.92, irid=0.3, squame=0.0,
                 linea_laterale=0.5, linea_v=(0.0, 0.0), lucido=0.8),
    extra=_extra_sciabola,
    famiglia='skeletal', piano='nastriforme', opzioni=dict(vertebre=1, striscia=False))


# ── Lanternossa (pesce lanterna, Myctophum punctatum) — dalla prova dei fotofori (piano 'fusiforme'; la forma
#    è quella della prova: le altre famiglie la copiano da qui) ──
# Le file di lucine sul fianco basso sono Shape.fotofori (sferette luminose appena affondate nella pelle). Da
# scheletro: «le lucine… rimaste accese sulle ossa. Al buio sembra un piccolo parco giochi visto da lontano» →
# le lucine della pelle no (elementi=False): ne fa altre l'extra, attaccate alle ossa (in fondo e a metà di
# ogni costola, in punta e a metà di ogni spina di sotto, due sul cranio), di tanti colori come le lampadine
# di un luna park.
_COLORI_LUNAPARK = [(1.0, 0.62, 0.2), (1.0, 0.03, 0.02), (1.0, 0.55, 0.0), (0.02, 1.0, 0.12), (0.03, 0.25, 1.0),
                    (1.0, 0.04, 0.5)]


def _extra_lanternossa(c):
    P = c.P
    _togli(c, 'Spine')
    lisca, ossa = _lisca(c, vertebre=34, spessore=1.3, minimo=0.0022)
    c.obs.append(lisca)
    punti = []
    for pts in ossa['costole']:
        punti += [pts[4], pts[3], pts[2]]
    for base, punta in ossa['emali']:
        punti += [punta, base + (punta - base) * 0.6]
    for t in (0.05, 0.1):                   # sul cranio: dove la prova ha le due lucine della testa
        p, n = c.body.superficie(t, -0.55, -1)
        punti.append(p - n * 0.002)
    r = 0.0064
    gruppi = {}
    for i, p in enumerate(punti):
        gruppi.setdefault(i % len(_COLORI_LUNAPARK), []).append(np.asarray(p, F) + np.array((0.0, -r * 0.8, 0.0), F))
    for k, C in gruppi.items():
        f, lo, hi = P.campo_sfere(C, r)
        col = _COLORI_LUNAPARK[k]
        mat = P.materiale(f'Lampadina{k}', col, rough=0.15, coat=1.0, emissione=col, forza=1.6)
        c.obs.append(P.oggetto_sdf(f'Lampadine{k}', f, lo, hi, mat, res=0.0011))


SPECIE['lanternossa'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.03), (0.08, 0.065), (0.18, 0.09), (0.35, 0.1), (0.55, 0.09), (0.75, 0.06), (0.9, 0.035),
             (1, 0.03)],
        bot=[(0, -0.03), (0.04, -0.06), (0.12, -0.085), (0.3, -0.1), (0.5, -0.095), (0.7, -0.068), (0.9, -0.035), (1, -0.03)],
        w=[(0, 0.01), (0.06, 0.035), (0.2, 0.045), (0.5, 0.04), (0.8, 0.022), (1, 0.012)],
        eye_t=0.1, eye_z=0.016, eye_r=0.038, mouth_t=0.14, mouth_z0=-0.004, mouth_z1=-0.042, gill_t=0.23,
        fotofori=Fotofori(righe=[(0.16, 0.4, -0.86, 6), (0.44, 0.72, -0.8, 6), (0.76, 0.95, -0.66, 5), (0.22, 0.5, -0.52, 4),
                                 (0.56, 0.8, -0.42, 4), (0.05, 0.1, -0.55, 2)],
                          sparsi=3, raggio=0.0058, colore=(0.35, 0.8, 1.0), forza=4.0),
        fins=[Fin('dorsal', 0.4, 0.55, [(0, 0), (0.15, 0.9), (0.45, 1.0), (0.8, 0.6), (1, 0.05)], 0.08, 12),
              Fin('dorsal', 0.79, 0.85, [(0, 0), (0.3, 0.9), (0.7, 0.8), (1, 0.05)], 0.02, 8, carnosa=True, spessore=0.003),
              Fin('anal', 0.55, 0.75, [(0, 0), (0.1, 0.85), (0.6, 0.6), (1, 0.05)], 0.06, 14),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.3), 0.21, 18),
              Fin('pectoral', 0.23, 0.24, PETTORALE, 0.08, 9),
              Fin('pelvic', 0.38, 0.39, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.03, 0.04, 0.06), flank=(0.3, 0.33, 0.38), belly=(0.42, 0.44, 0.47), fin=(0.18, 0.2, 0.22),
                 iris=(0.4, 0.45, 0.5), iris_dark=(0.04, 0.05, 0.06), metal=0.7, irid=0.3, squame=1.0),
    extra=_extra_lanternossa,
    famiglia='skeletal', piano='fusiforme', opzioni=dict(vertebre=1, elementi=False))


# ── Cavalluccio d'Osso (cavalluccio marino, Hippocampus guttulatus) — dalla prova del piano 'cavalluccio' (la
#    forma è quella della prova: le altre famiglie la copiano da qui) ──
# Si costruisce dritto (muso a tubo in −X, coda in +X) e piega curva l'asse: la testa resta orizzontale, il
# collo scende ad angolo retto, la coda si arrotola in avanti. Da scheletro: «un cavallino da giostra, senza la
# giostra» → della corazza restano gli anelli d'osso (_anelli_ossei), vuoti fra uno e l'altro, con la vernice
# da giostra scrostata (rossi, oro, bianchi, azzurri); la colonna dentro; la corona e le spine d'osso; e il
# palo d'ottone a tortiglione della giostra che lo attraversa, dritto, dalla testa a sotto la coda.
def _anelli_ossei(c, mat, raggio=0.0034, nome='Anelli'):
    """Gli anelli della corazza: un cerchio d'osso attorno al corpo per ogni anello di Shape.anelli, sulla
    sezione, con un bitorzolo in cima, e tre creste lunghe (sul dorso e sui fianchi) che li tengono insieme."""
    P, body, sh = c.P, c.body, c.forma
    n = sh.anelli
    a0, a1 = sh.anelli_tratto
    ks = np.arange(int(math.ceil(a0 * n)), int(math.floor(a1 * n)) + 1)
    xs = (ks / n).astype(F)
    zc, h, w = (np.asarray(a, F) for a in body.section(xs))
    top = body.top

    def f(p):
        k = (np.clip(np.rint(p[:, 0] * n), ks[0], ks[-1]) - ks[0]).astype(int)
        y, dz = p[:, 1], p[:, 2] - zc[k]
        # distanza dall'ellisse della sezione (come il corpo), poi un tubo attorno
        k0 = np.sqrt((y / w[k]) ** 2 + (dz / h[k]) ** 2)
        k1 = np.sqrt((y / (w[k] * w[k])) ** 2 + (dz / (h[k] * h[k])) ** 2)
        de = k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)
        d = np.sqrt(de * de + (p[:, 0] - xs[k]) ** 2) - raggio
        d = np.minimum(d, np.sqrt((p[:, 0] - xs[k]) ** 2 + y ** 2 + (dz - h[k]) ** 2) - raggio * 1.7)
        # le creste lunghe: sul dorso e sui due fianchi, dentro il tratto degli anelli
        xx = np.clip(p[:, 0], xs[0], xs[-1])
        zt = top(xx)
        zcx, hx, wx = body.section(xx)
        cresta = np.sqrt(y ** 2 + (p[:, 2] - zt) ** 2)
        for s in (-1, 1):
            cresta = np.minimum(cresta, np.sqrt((y - s * wx * 0.92) ** 2 + (p[:, 2] - zcx) ** 2))
        cresta = np.maximum(cresta - raggio * 0.6, np.maximum(xs[0] - p[:, 0], p[:, 0] - xs[-1]))
        return np.minimum(d, cresta).astype(F)
    lo, hi = body.bounds(solo_corpo=True)
    lo[0], hi[0] = float(xs[0]) - 0.01, float(xs[-1]) + 0.01
    return P.oggetto_sdf(nome, f, lo, hi, mat, res=0.0008, attrs={'u': lambda p: p[:, 0].astype(F)})


def _palo_giostra(c, x_p, sopra=0.07, sotto=0.04, raggio=0.0072, nome='PaloGiostra'):
    """Il palo d'ottone a tortiglione della giostra, verticale, che attraversa il cavalluccio. La piega
    (pesci.piega) sposta interi gli oggetti che non hanno la matrice identità e li gira dell'angolo dell'asse:
    il palo si fa attorno a un'origine sua nel punto x_p del pesce dritto, con l'asse già girato al contrario
    di quell'angolo, così dopo la piega è verticale e passa dove è finito quel punto."""
    from mathutils import Matrix, Vector
    P, body = c.P, c.body
    mappa = _mappa_piega(c)
    zc, h, _ = _sez(body, x_p)
    loc = np.array((x_p, 0.0, zc - h * 0.35), F)
    q, a = mappa(loc)
    a = float(a[0])
    # quanto è alto il cavalluccio dopo la piega: il palo va da sotto la coda a sopra la testa
    ts = np.linspace(-0.08, 1.0, 300)
    bordo = np.concatenate([np.stack([ts, 0 * ts, body.top(np.clip(ts, 0, 1)) + 0.03], 1),
                            np.stack([ts, 0 * ts, body.bot(np.clip(ts, 0, 1))], 1)])
    zz = mappa(bordo)[0][:, 2]
    s_top, s_bot = float(zz.max()) + sopra - q[0, 2], float(zz.min()) - sotto - q[0, 2]
    asse = np.array((math.sin(a), 0.0, math.cos(a)), F)
    e1 = np.array((math.cos(a), 0.0, -math.sin(a)), F)
    passo = 0.045

    def f(p):
        s = p @ asse
        u1, u2 = p @ e1, p[:, 1]
        rho = np.sqrt(u1 * u1 + u2 * u2)
        th = np.arctan2(u2, u1)
        # il tortiglione: quattro creste che girano attorno all'asse
        rr = raggio * (1.0 + 0.14 * np.cos(4 * th - s * 2 * np.pi / passo))
        d = np.maximum((rho - rr) * 0.8, np.maximum(s_bot - s, s - s_top))
        for se in (s_bot, s_top):          # i pomi alle due estremità
            d = np.minimum(d, np.linalg.norm(p - asse * se, axis=1) - raggio * 1.8)
        return d.astype(F)
    ends = np.stack([asse * s_bot, asse * s_top])
    lo, hi = ends.min(0) - raggio * 2.5, ends.max(0) + raggio * 2.5
    o = P.oggetto_sdf(nome, f, lo, hi, P.materiale('Ottone', (0.98, 0.74, 0.32), rough=0.34, coat=0.6, metal=1.0), res=0.0009)
    o.matrix_world = Matrix.Translation(Vector(tuple(map(float, loc))))
    return o


def _extra_cavalluccio(c):
    P, body, sh = c.P, c.body, c.forma
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=40, spine=False)[0])
    c.obs.append(_anelli_ossei(c, _mat_vernice(c, sh.anelli)))
    osso = _osso(c)
    for k, fl in enumerate(sh.filamenti):
        c.obs += P.filamento(body, c.aspetto, fl, k, mat=osso)
    c.obs.append(_palo_giostra(c, 0.3))


SPECIE['cavalluccio_dosso'] = Specie(
    forma=Shape(
        top=[(0, 0.004), (0.03, 0.03), (0.08, 0.044), (0.12, 0.038), (0.16, 0.034), (0.25, 0.048), (0.35, 0.054), (0.45, 0.042),
             (0.6, 0.028), (0.8, 0.016), (1.0, 0.006)],
        bot=[(0, -0.008), (0.03, -0.028), (0.08, -0.034), (0.12, -0.03), (0.16, -0.036), (0.25, -0.066), (0.35, -0.07),
             (0.45, -0.046), (0.6, -0.028), (0.8, -0.016), (1, -0.006)],
        w=[(0, 0.007), (0.05, 0.02), (0.12, 0.022), (0.2, 0.034), (0.35, 0.037), (0.5, 0.025), (0.8, 0.013), (1, 0.005)],
        eye_t=0.06, eye_z=0.012, eye_r=0.011, bocca='nessuna', gill_t=0.12, anelli=38, anelli_tratto=(0.15, 0.99),
        rostro=Rostro('tubo', lunghezza=0.08, z=-0.004, larghezza=0.0085, altezza=0.0095, punta=0.8),
        filamenti=[Filamento(t=0.085, v=1.0, lunghezza=0.028, raggio=0.004, dir=(0.15, 0.0, 1.0), lati='centro', punta=0.5),
                   Filamento(t=0.24, v=0.95, lunghezza=0.022, raggio=0.002, dir=(0.4, 0.5, 1.0), curva=(4, 0, 0)),
                   Filamento(t=0.33, v=0.95, lunghezza=0.018, raggio=0.002, dir=(0.4, 0.5, 1.0), curva=(4, 0, 0)),
                   Filamento(t=0.05, v=0.6, lunghezza=0.016, raggio=0.0018, dir=(0.2, 0.6, 1.0))],
        fins=[Fin('dorsal', 0.37, 0.5, [(0, 0), (0.1, 0.9), (0.5, 1.0), (0.9, 0.9), (1, 0.1)], 0.035, 20),
              Fin('pectoral', 0.13, 0.14, PETTORALE_TONDA, 0.03, 9, z=0.1)],
        piega=[(0, 0), (0.1, 0), (0.15, -40), (0.2, -92), (0.45, -100), (0.55, -95), (0.7, -150), (0.82, -240), (0.92, -330),
               (1.0, -400)]),
    aspetto=Look(back=(0.24, 0.17, 0.09), flank=(0.3, 0.21, 0.12), belly=(0.36, 0.27, 0.15), fin=(0.4, 0.33, 0.24),
                 iris=(0.75, 0.6, 0.3), iris_dark=(0.2, 0.12, 0.04), metal=0.05, irid=0.1, squame=0.0, linea_laterale=0.0,
                 disegni=[Disegno('punti', colore=(0.82, 0.8, 0.72), forza=0.85, scala=150, r=0.17)]),
    extra=_extra_cavalluccio,
    famiglia='skeletal', piano='cavalluccio',
    opzioni=dict(vertebre=1, striscia=False, peduncolo=None, elementi=False))


# ── Flauto d'Ossa (pesce flauto, Fistularia commersonii) ──
# Lunghissimo e sottile, il muso a tubo lungo un quarto del corpo, dorsale e anale piccole e opposte vicino
# alla coda, la coda forcuta con il filo di mezzo lunghissimo; macchie e righe azzurre sul dorso. Da scheletro:
# «se ci soffi dentro suona… la nota del carillon» → il muso a tubo è un flauto d'osso: vuoto dentro, con sei
# fori in fila (_canna_flauto, al posto del muso del cranio); il filo della coda è d'osso (elementi=False: lo
# rifà l'extra).
def _senza_muso(c, f):
    """campo: toglie dal cranio il muso a tubo (lo rifà _canna_flauto, con la griglia fine: le pareti del tubo
    vuoto sono più sottili della griglia del cranio nelle anteprime)."""
    def g(p):
        return np.maximum(f(p), -(p[:, 0] + 0.003)).astype(F)
    return g


def _canna_flauto(c, nfori=6, nome='Flauto'):
    """Il muso a tubo fatto flauto d'osso: la sezione del Rostro('tubo'), vuota dentro (aperta in punta), con
    i fori in fila sul lato di sopra verso la camera (si vedono scuri: dentro è vuoto)."""
    P = c.P
    r = c.forma.rostro
    L = float(r.lunghezza)
    a = math.radians(35.0)
    nf = np.array((0.0, -math.sin(a), math.cos(a)), F)      # la direzione dei fori: in su e verso la camera
    fori = []
    for j in range(nfori):
        x = -0.05 - 0.04 * j
        wy, wz, zc = (float(np.asarray(v).ravel()[0]) for v in P.sezione_rostro(r, np.array([x], F)))
        fori.append((np.array((x, 0.0, zc), F), min(wy, wz) * 0.62))

    def f(p):
        x = p[:, 0]
        wy, wz, zc = P.sezione_rostro(r, np.minimum(x, 0.0))
        k0 = np.sqrt((p[:, 1] / wy) ** 2 + ((p[:, 2] - zc) / wz) ** 2)
        m = np.minimum(wy, wz)
        d = np.maximum((k0 - 1.0) * m, -(k0 - 0.52) * m)          # la parete del tubo
        d = np.maximum(d, np.maximum(-L - x, x - 0.012))
        for cf, rf in fori:
            q = p - cf
            lungo = q @ nf
            fuori = np.linalg.norm(q - lungo[:, None] * nf, axis=1)
            d = np.maximum(d, -np.maximum(fuori - rf, -lungo))
        return d.astype(F)
    big = max(r.larghezza, r.altezza) * 1.3
    lo = np.array((-L - 0.006, -big, r.z - big), F)
    hi = np.array((0.016, big, r.z + abs(r.curva) + big), F)
    return P.oggetto_sdf(nome, f, lo, hi, _osso(c), res=0.0006)


def _extra_flauto(c):
    """Il flauto, la lisca e il filo della coda d'osso."""
    c.obs.append(_canna_flauto(c))
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=44, spessore=1.0, minimo=0.0013)[0])
    for k, fl in enumerate(c.forma.filamenti):
        c.obs += c.P.filamento(c.body, c.aspetto, fl, k, mat=_osso(c))


SPECIE['flauto_dossa'] = Specie(
    forma=Shape(
        top=[(0, 0.007), (0.03, 0.012), (0.08, 0.016), (0.12, 0.018), (0.2, 0.021), (0.35, 0.023), (0.5, 0.022), (0.65, 0.018),
             (0.8, 0.013), (0.92, 0.009), (1, 0.007)],
        bot=[(0, -0.008), (0.03, -0.012), (0.08, -0.016), (0.15, -0.019), (0.3, -0.023), (0.5, -0.022), (0.65, -0.019),
             (0.8, -0.013), (0.92, -0.009), (1, -0.007)],
        w=[(0, 0.008), (0.05, 0.013), (0.12, 0.018), (0.3, 0.023), (0.55, 0.02), (0.8, 0.012), (1, 0.006)],
        eye_t=0.085, eye_z=0.007, eye_r=0.012, bocca='nessuna', gill_t=0.14,
        rostro=Rostro('tubo', lunghezza=0.3, z=-0.0005, larghezza=0.0105, altezza=0.011, punta=0.72),
        filamenti=[Filamento(xyz=(0.995, 0.0, 0.0), dir=(1.0, 0.0, 0.0), curva=(0.0, 0.0, -0.5), lunghezza=0.3, raggio=0.0022,
                             lati='centro', punta=0.3, segmenti=14)],
        fins=[Fin('dorsal', 0.74, 0.8, [(0, 0), (0.15, 1.0), (0.5, 0.8), (1, 0.1)], 0.045, 12),
              Fin('anal', 0.74, 0.8, [(0, 0), (0.15, 1.0), (0.5, 0.8), (1, 0.1)], 0.04, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.35, 0.45), 0.08, 14),
              Fin('pectoral', 0.16, 0.17, PETTORALE_TONDA, 0.03, 9),
              Fin('pelvic', 0.42, 0.43, PELVICA, 0.025, 5)]),
    aspetto=Look(back=(0.22, 0.2, 0.15), flank=(0.45, 0.42, 0.35), belly=(0.7, 0.68, 0.62), fin=(0.35, 0.33, 0.28),
                 iris=(0.75, 0.65, 0.4), iris_dark=(0.15, 0.12, 0.06), metal=0.3, irid=0.3, squame=0.0, linea_laterale=0.0,
                 disegni=[Disegno('strisce', colore=(0.2, 0.5, 0.88), forza=0.8, v0=0.45, v1=0.95, n=2, larghezza=0.07),
                          Disegno('macchie', colore=(0.25, 0.55, 0.92), forza=0.85, scala=45, r=0.2, v0=0.2)]),
    campo=_senza_muso, extra=_extra_flauto,
    famiglia='skeletal', piano='rostro', opzioni=dict(vertebre=1, elementi=False))


# ── Trombetta d'Osso (pesce trombetta, Macroramphosus scolopax) ──
# Il corpo piccolo, alto e compresso, il muso a tubo lunghissimo, la seconda spina della dorsale lunghissima e
# seghettata, la seconda dorsale e l'anale piccole vicino alla coda, la coda piccola; rosa-argento. Da
# scheletro: «il muso a trombetta… le trombette che suonavano i bambini» → il tubo d'osso finisce nella
# campana gialla di una trombetta di plastica; la spina seghettata d'osso è un extra (_spina_seghettata).
def _spina_seghettata(c, t, angolo, lunghezza, raggio=0.0055, denti=14, nome='SpinaSeghettata'):
    """La spina lunghissima della dorsale del pesce trombetta: un osso dritto che parte dal dorso in t,
    coricato all'indietro di `angolo` gradi sull'orizzontale, con i dentini lungo il bordo di dietro."""
    z0 = float(c.body.top(np.array([t], F))[0]) - 0.004
    a = np.array((t, 0.0, z0), F)
    d = np.array((math.cos(math.radians(angolo)), 0.0, math.sin(math.radians(angolo))), F)
    dietro = np.array((math.sin(math.radians(angolo)), 0.0, -math.cos(math.radians(angolo))), F)
    oss = _Ossa()
    oss.cono(a, a + d * lunghezza, raggio, raggio * 0.15)
    for i in range(denti):
        u = 0.18 + 0.74 * i / max(denti - 1, 1)
        rr = raggio * (1 - 0.85 * u)
        p = a + d * lunghezza * u + dietro * rr * 0.5
        oss.cono(p, p + dietro * (0.0045 + rr * 0.8) - d * 0.004, rr * 0.55 + 0.0009, 0.0003)
    return oss.oggetto(c, nome, _osso(c), res=0.0006)


def _campana(c, lunga=0.075, bocca=0.04, spessore=0.0015, nome='Trombetta'):
    """La campana della trombetta di plastica in punta al muso a tubo: un corno che si apre in avanti (−X),
    con il bordo arrotolato; dentro abbraccia la punta del tubo."""
    r = c.forma.rostro
    L = float(r.lunghezza)
    wy, wz, zc = (float(np.asarray(v).ravel()[0]) for v in c.P.sezione_rostro(r, np.array([-L], F)))
    r0 = max(wy, wz) * 1.05
    x0 = -L + 0.006
    us = np.linspace(0, 1, 48)
    profilo = np.stack([us * lunga, r0 + (bocca - r0) * us ** 2.6], axis=1).astype(F)

    def f(p):
        q = np.stack([x0 - p[:, 0], np.sqrt(p[:, 1] ** 2 + (p[:, 2] - zc) ** 2)], axis=1).astype(F)
        d = _spezzata_2d(q, profilo) - spessore
        bordo = np.sqrt((q[:, 0] - lunga) ** 2 + (q[:, 1] - bocca) ** 2) - spessore * 1.9
        return np.minimum(d, bordo).astype(F)
    lo = np.array((x0 - lunga - 0.01, -bocca - 0.01, zc - bocca - 0.01), F)
    hi = np.array((x0 + 0.01, bocca + 0.01, zc + bocca + 0.01), F)
    return c.P.oggetto_sdf(nome, f, lo, hi, _plastica(c, 'PlasticaTrombetta', (0.95, 0.6, 0.02)), res=0.0006)


def _extra_trombetta(c):
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=24, spessore=1.6, minimo=0.0024, costole_dietro=0.025)[0])
    c.obs.append(_spina_seghettata(c, t=0.43, angolo=48.0, lunghezza=0.3))
    c.obs.append(_campana(c))


SPECIE['trombetta_dosso'] = Specie(
    forma=Shape(
        top=[(0, 0.012), (0.04, 0.032), (0.1, 0.07), (0.2, 0.13), (0.32, 0.168), (0.45, 0.174), (0.58, 0.15), (0.72, 0.1),
             (0.85, 0.055), (0.95, 0.032), (1, 0.026)],
        bot=[(0, -0.01), (0.05, -0.04), (0.12, -0.08), (0.25, -0.13), (0.4, -0.15), (0.55, -0.135), (0.7, -0.095), (0.85, -0.052),
             (0.95, -0.03), (1, -0.026)],
        w=[(0, 0.009), (0.08, 0.03), (0.25, 0.045), (0.45, 0.045), (0.7, 0.03), (0.9, 0.016), (1, 0.011)],
        eye_t=0.1, eye_z=0.03, eye_r=0.036, bocca='nessuna', gill_t=0.24,
        rostro=Rostro('tubo', lunghezza=0.42, z=0.004, larghezza=0.011, altezza=0.012, punta=0.6),
        fins=[Fin('dorsal', 0.74, 0.84, [(0, 0), (0.2, 0.9), (0.6, 0.7), (1, 0.05)], 0.05, 10),
              Fin('anal', 0.68, 0.82, [(0, 0), (0.2, 0.8), (0.6, 0.6), (1, 0.05)], 0.045, 12),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.4, 0.12, 0.85), 0.11, 14),
              Fin('pectoral', 0.28, 0.29, PETTORALE, 0.07, 9),
              Fin('pelvic', 0.45, 0.46, PELVICA, 0.05, 5, spiny=True)]),
    aspetto=Look(back=(0.5, 0.26, 0.26), flank=(0.75, 0.58, 0.56), belly=(0.82, 0.78, 0.74), fin=(0.6, 0.45, 0.42),
                 iris=(0.82, 0.72, 0.5), iris_dark=(0.25, 0.15, 0.1), metal=0.6, irid=0.4),
    extra=_extra_trombetta,
    famiglia='skeletal', piano='alto', opzioni=dict(vertebre=1))


# ── Aquila d'Osso (aquila di mare, Myliobatis aquila) ──
# Una razza dalle ali appuntite larghissime, la testa tonda che sporge davanti al disco con gli occhi ai lati,
# la coda a frusta lunghissima con il pungiglione e una dorsale piccola alla base. Come le razze, costruita con
# il dorso verso la camera (z è l'apertura delle ali). Da scheletro: «le razze non hanno ossa… questa ne ha
# trovate, e non sono di pesce» → niente ventaglio di cartilagine (raggi_disco=0): nelle ali ci sono braccia e
# mani d'uomo, come le ali dei pipistrelli (omero, radio e ulna, le dita aperte fino al bordo dell'ala), con
# quel che resta della pelle tesa fra le dita a festoni (così la sagoma ad ali appuntite si legge); sul tronco
# le scapole, le clavicole e una gabbia toracica, dietro un bacino; il pungiglione d'osso seghettato.
def _ossa_umane(c, y0=-0.006, nome='OssaUmane'):
    """Le ossa da mammifero dell'Aquila d'Osso, nel piano delle ali (y = y0, appena sopra la colonna verso la
    camera): clavicole, scapole, costole, braccia, mani con le dita fino al bordo delle ali, bacino e femori."""
    P, body = c.P, c.body
    oss = _Ossa()

    def pt(x, z, dy=0.0):
        return np.array((x, y0 + dy, z), F)

    def osso_lungo(a, b, r, testa=1.4):
        """Un osso lungo: il fusto più sottile in mezzo, le teste tonde alle estremità."""
        m = (a + b) * 0.5
        oss.cono(a, m, r, r * 0.78)
        oss.cono(m, b, r * 0.78, r)
        oss.nodo(a, r * testa)
        oss.nodo(b, r * testa)

    lastre = []          # le ossa piatte (scapole, bacino): poligoni nel piano XZ, con lo spessore
    fori = []            # i buchi nelle ossa piatte (x, z, raggio): i fori otturatori del bacino
    contorno = body.disco.top
    for s in (1.0, -1.0):
        # clavicola a S, dallo sterno alla spalla
        oss.spezzata(_curva(c, [pt(0.086, s * 0.006), pt(0.093, s * 0.02), pt(0.104, s * 0.033), pt(0.118, s * 0.05)], 12),
                     0.0032, 0.0028)
        # scapola: un triangolo piatto, con la cresta
        lastre.append([(0.117, s * 0.053), (0.128, s * 0.015), (0.198, s * 0.024)])
        oss.cono(pt(0.12, s * 0.049, -0.002), pt(0.133, s * 0.017, -0.002), 0.0022, 0.0016)
        # costole: archi che dalla colonna vanno in fuori e girano indietro
        for i in range(8):
            x = 0.112 + 0.021 * i
            ll = 1.0 - 0.07 * max(i - 4, 0)
            oss.spezzata(_curva(c, [pt(x, s * 0.004), pt(x - 0.002, s * 0.02 * ll), pt(x + 0.008, s * 0.035 * ll),
                                    pt(x + 0.024 * ll, s * 0.044 * ll), pt(x + 0.04 * ll, s * 0.042 * ll)], 14),
                         0.0024, 0.0017)
        # il braccio: omero, radio e ulna, il polso
        spalla, gomito, polso = pt(0.121, s * 0.056), pt(0.142, s * 0.135), pt(0.166, s * 0.206)
        osso_lungo(spalla, gomito, 0.0042, 1.5)
        dperp = np.array((0.0042, 0.0, -0.0016 * s), F)
        osso_lungo(gomito + dperp * 0.3, polso + dperp, 0.0026)
        osso_lungo(gomito - dperp * 0.6, polso - dperp * 0.4, 0.0025)
        rng = np.random.default_rng(int(7 + s))
        for _ in range(6):
            oss.nodo(polso + np.array((rng.uniform(-0.006, 0.008), 0.0, s * rng.uniform(0.002, 0.012)), F), 0.0027)
        # le dita: dal polso al bordo dell'ala, come quelle di un pipistrello (metacarpo e tre falangi)
        for k, t in enumerate(_DITA_AQUILA):
            punta = pt(t, s * float(contorno(np.array([t], F))[0]) * (0.95 if k else 0.82))
            base = polso + np.array((0.004 * k - 0.004, 0.0, s * 0.008), F)
            giunti = [base + (punta - base) * u for u in ((0.0, 0.4, 0.66, 0.85, 1.0) if k else (0.0, 0.45, 0.78, 1.0))]
            for j in range(len(giunti) - 1):
                rr = 0.0031 - 0.0004 * j
                oss.cono(giunti[j], giunti[j + 1], rr, rr * 0.8)
                oss.nodo(giunti[j + 1], rr * 1.15)
        # il bacino visto da dietro (la testa dell'uomo sarebbe verso −X): l'ala dell'ileo che si apre verso la
        # testa, sotto l'ischio e il pube attorno al foro otturatore; il femore che entra nella pinna pelvica
        lastre.append([(0.33, s * 0.008), (0.316, s * 0.03), (0.318, s * 0.046), (0.332, s * 0.053), (0.35, s * 0.047),
                       (0.36, s * 0.037), (0.376, s * 0.032), (0.382, s * 0.018), (0.378, s * 0.004), (0.364, s * 0.004),
                       (0.35, s * 0.01)])
        fori.append((0.369, s * 0.021, 0.0055))
        osso_lungo(pt(0.36, s * 0.038), pt(0.402, s * 0.052), 0.0034, 1.6)
    # l'osso sacro, il cuneo fra le due ali del bacino
    lastre.append([(0.322, -0.009), (0.322, 0.009), (0.352, 0.0035), (0.352, -0.0035)])
    fo, lo_o, hi_o = P.campo_coni(oss.A, oss.B, oss.R1, oss.R2, k=6)
    polig = [np.array(v, F) for v in lastre]

    def f(p):
        d = fo(p)
        q2 = np.stack([p[:, 0], p[:, 2]], axis=1)
        for V in polig:
            d2 = P._poligono_2d(q2, V) - 0.0012
            dy = np.abs(p[:, 1] - y0) - 0.0016
            lastra = np.minimum(np.maximum(d2, dy), 0) + np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dy, 0) ** 2) - 0.0008
            d = np.minimum(d, lastra)
        for x, z, r in fori:
            d = np.maximum(d, -(np.sqrt((p[:, 0] - x) ** 2 + (p[:, 2] - z) ** 2) - r))
        return d.astype(F)
    tutti = np.concatenate([np.stack([np.array((v[0], y0, v[1]), F) for v in V]) for V in lastre])
    lo = np.minimum(lo_o, tutti.min(0) - 0.006)
    hi = np.maximum(hi_o, tutti.max(0) + 0.006)
    return P.oggetto_sdf(nome, f, lo, hi, P.bone_material('OssaUmane', dirt=0.25, tinta=(1.06, 1.04, 1.0)), res=0.0009)


_DITA_AQUILA = (0.148, 0.186, 0.214, 0.248, 0.288)     # dove le dita dell'Aquila toccano il bordo dell'ala (t)


def _membrana_ali(c, y0=0.004, nome='Membrana'):
    """Quel che resta della pelle delle ali dell'Aquila d'Osso: una membrana sottile tesa sulle dita, come
    un'ala di pipistrello, con la sagoma del disco (le ali appuntite) e il bordo di dietro a festoni fra la
    punta di un dito e l'altra; bucata e strappata. Sta appena dietro le ossa (y0 > 0, lontano dalla camera)."""
    P, body = c.P, c.body
    contorno = body.disco.top
    n3 = P.sdf.Noise3(11)
    # i festoni: fra le punte delle dita (e dall'ultima alla pelvica) il bordo si incurva verso dentro
    punte = [(t, float(contorno(np.array([t], F))[0]) * 0.95) for t in _DITA_AQUILA[1:]] + [(0.36, 0.05)]
    archi = []
    for (x1, z1), (x2, z2) in zip(punte[:-1], punte[1:]):
        corda = math.hypot(x2 - x1, z2 - z1)
        freccia = corda * 0.22
        R = (corda * corda / 4 + freccia * freccia) / (2 * freccia)
        nx, nz = -(z2 - z1) / corda, (x2 - x1) / corda          # la normale verso fuori (indietro e in fuori)
        archi.append(((x1 + x2) / 2 + nx * (R - freccia), (z1 + z2) / 2 + nz * (R - freccia), R))

    def f(p):
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        az = np.abs(z)
        d = az - contorno(np.clip(x, 0, 1)) * 0.97
        for cx, cz, R in archi:
            d = np.maximum(d, -(np.sqrt((x - cx) ** 2 + (az - cz) ** 2) - R))
        d = np.maximum(d, 0.045 - az)                                  # non sul tronco: lì ci sono le costole
        d = np.maximum(d, (n3(p, scale=0.03, octaves=3) - 0.32) * 0.02)  # i buchi e gli strappi
        dy = np.abs(y - y0) - 0.0011
        return (np.minimum(np.maximum(d, dy), 0) + np.sqrt(np.maximum(d, 0) ** 2 + np.maximum(dy, 0) ** 2)).astype(F)
    zm = body.zmax
    lo = np.array((0.04, y0 - 0.006, -zm - 0.01), F)
    hi = np.array((0.42, y0 + 0.006, zm + 0.01), F)
    m, g = P.material('MembranaAli')
    co = g.texcoord('Object')
    n = g.noise(co, scale=50.0, detail=4.0, rough=0.6)
    col = g.mix(g.smoothstep(0.35, 0.7, n.fac), (0.16, 0.12, 0.09), (0.07, 0.055, 0.04))
    taglio = g.layer_weight(blend=0.4, which='Facing')
    g.output_material(g.principled(color=col, rough=0.55, coat=0.3, sheen=0.4, alpha=g.add(0.72, g.mul(taglio, 0.25)),
                                   normal=g.bump(n.fac, strength=0.2, distance=0.002)))
    return P.oggetto_sdf(nome, f, lo, hi, m, res=0.0011)


def _pungiglione(c, t=0.5, lunghezza=0.09, raggio=0.0034, nome='Pungiglione'):
    """Il pungiglione d'osso sulla coda, coricato all'indietro e appena di lato (perché dall'alto si veda),
    seghettato sui due bordi."""
    zc, h, _ = _sez(c.body, t)
    a = np.array((t, -0.002, zc + h * 0.5), F)
    d = np.array((1.0, 0.0, 0.07), F)
    d /= np.linalg.norm(d)
    oss = _Ossa()
    oss.cono(a, a + d * lunghezza, raggio, raggio * 0.12)
    for i in range(12):
        u = 0.25 + 0.7 * i / 11
        rr = raggio * (1 - 0.88 * u)
        p = a + d * lunghezza * u
        for s in (1, -1):
            oss.cono(p + np.array((0, 0, s * rr * 0.5), F), p + np.array((-0.0028, 0.0, s * (rr + 0.0022)), F),
                     rr * 0.45 + 0.0004, 0.00025)
    return oss.oggetto(c, nome, _osso(c), res=0.0005)


def _extra_aquila(c):
    c.obs.append(_ossa_umane(c))
    c.obs.append(_membrana_ali(c))
    c.obs.append(_pungiglione(c))


SPECIE['aquila_dosso'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.012, 0.016), (0.03, 0.026), (0.055, 0.031), (0.08, 0.03), (0.12, 0.036), (0.2, 0.044), (0.28, 0.038),
             (0.34, 0.026), (0.38, 0.014), (0.42, 0.0075), (0.55, 0.005), (0.75, 0.0035), (0.9, 0.0022), (1, 0.001)],
        bot=[(0, 0.0), (0.012, -0.016), (0.03, -0.026), (0.055, -0.031), (0.08, -0.03), (0.12, -0.036), (0.2, -0.044),
             (0.28, -0.038), (0.34, -0.026), (0.38, -0.014), (0.42, -0.0075), (0.55, -0.005), (0.75, -0.0035), (0.9, -0.0022),
             (1, -0.001)],
        w=[(0, 0.004), (0.02, 0.012), (0.06, 0.018), (0.15, 0.024), (0.25, 0.022), (0.35, 0.013), (0.42, 0.006), (0.6, 0.004),
           (0.8, 0.0028), (1, 0.001)],
        eye_t=0.045, eye_z=0.0, eye_r=0.008, occhi=[(0.045, 0.027, 0.008, -1), (0.045, -0.027, 0.008, -1)], spiracoli=0.005,
        bocca='nessuna', branchie='nessuna',
        disco=Disco(contorno=[(0, 0.0), (0.05, 0.0), (0.065, 0.035), (0.09, 0.1), (0.12, 0.18), (0.15, 0.26), (0.175, 0.318),
                              (0.19, 0.338), (0.2, 0.333), (0.215, 0.29), (0.24, 0.21), (0.27, 0.14), (0.3, 0.085),
                              (0.325, 0.056), (0.345, 0.05), (0.37, 0.047), (0.385, 0.03), (0.395, 0.0), (1.0, 0.0)],
                    spessore=[(0, 0.003), (0.08, 0.008), (0.18, 0.011), (0.28, 0.008), (0.36, 0.004), (0.4, 0.001), (1.0, 0.001)]),
        fins=[Fin('dorsal', 0.415, 0.445, [(0, 0), (0.25, 1.0), (0.6, 0.85), (1, 0.1)], 0.03, 8)]),
    aspetto=Look(back=(0.08, 0.065, 0.05), flank=(0.1, 0.085, 0.065), belly=(0.82, 0.8, 0.76), fin=(0.08, 0.065, 0.05),
                 iris=(0.55, 0.5, 0.3), iris_dark=(0.1, 0.09, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.3, ruvido=0.5),
    extra=_extra_aquila,
    famiglia='skeletal', piano='razza', opzioni=dict(raggi_disco=0, cranio_t=0.11))


# ── Spadossa (pesce spada, Xiphias gladius) — dalla prova del piano 'rostro' (_FORMA_SPADA è la forma della
#    prova, che le altre famiglie copiano: resta com'era) ──
# La spada è un Rostro piatto (largo in y, sottile in z); le pinne rigide sono carnose; niente pelviche. Da
# scheletro: «solo la spada e lo scheletro, in posa da combattimento. Sulla spada è infilato un braccialetto di
# plastica fucsia» → niente pelle (né striscia né peduncolo): la spada intera, lo scheletro completo con le ossa
# delle pinne e il ventaglio della coda; le pinne di carne della prova diventano pinne d'osso a raggi (la
# famiglia fa a raggi solo quelle non carnose); la posa: il corpo ad arco, la spada alzata e la coda su; il
# braccialetto fucsia infilato a metà spada, fermo dove la spada diventa larga quanto lui.
_FORMA_SPADA = Shape(
    top=[(0, -0.004), (0.03, 0.02), (0.08, 0.055), (0.15, 0.085), (0.25, 0.105), (0.4, 0.11), (0.55, 0.1), (0.7, 0.075),
         (0.85, 0.042), (0.95, 0.022), (1, 0.017)],
    bot=[(0, -0.022), (0.04, -0.04), (0.1, -0.065), (0.2, -0.09), (0.35, -0.1), (0.5, -0.095), (0.65, -0.075), (0.8, -0.045),
         (0.95, -0.02), (1, -0.017)],
    w=[(0, 0.006), (0.06, 0.035), (0.2, 0.07), (0.4, 0.075), (0.65, 0.055), (0.85, 0.03), (1, 0.016)],
    eye_t=0.085, eye_z=0.018, eye_r=0.02, mouth_t=0.085, mouth_z0=-0.02, mouth_z1=-0.032, gill_t=0.2,
    rostro=Rostro('spada', lunghezza=0.45, z=0.0, larghezza=0.024, altezza=0.0075, punta=0.12),
    fins=[Fin('dorsal', 0.19, 0.3, [(0, 0), (0.12, 0.8), (0.25, 1.0), (0.36, 0.45), (0.55, 0.15), (1, 0.06)], 0.2, 40,
              carnosa=True, spessore=0.006),
          Fin('dorsal', 0.9, 0.92, [(0, 0), (0.3, 1.0), (1, 0.1)], 0.025, 10, carnosa=True, spessore=0.003),
          Fin('anal', 0.62, 0.7, [(0, 0), (0.15, 0.9), (0.3, 1.0), (0.45, 0.4), (1, 0.06)], 0.075, 24, carnosa=True, spessore=0.004),
          Fin('anal', 0.89, 0.91, [(0, 0), (0.3, 1.0), (1, 0.1)], 0.02, 10, carnosa=True, spessore=0.003),
          Fin('caudal', 1.0, 1.0, coda_falcata(3.2, 0.95, radice=0.25), 0.3, 60, carnosa=True, spessore=0.006),
          Fin('pectoral', 0.2, 0.24, [(0, 0.06), (0.4, 0.1), (1.0, 0.02), (0.75, -0.06), (0.3, -0.12), (0, -0.1)], 0.18, 30,
              carnosa=True, spessore=0.004, dir=(0.7, 0.3, -0.55))])

# le stesse pinne fatte di raggi d'osso (non carnose), per lo scheletro
_PINNE_SPADA_OSSO = [
    Fin('dorsal', 0.19, 0.3, [(0, 0), (0.12, 0.8), (0.25, 1.0), (0.36, 0.45), (0.55, 0.15), (1, 0.06)], 0.2, 22, spiny=True),
    Fin('dorsal', 0.9, 0.92, [(0, 0), (0.3, 1.0), (1, 0.1)], 0.025, 6),
    Fin('anal', 0.62, 0.7, [(0, 0), (0.15, 0.9), (0.3, 1.0), (0.45, 0.4), (1, 0.06)], 0.075, 12),
    Fin('anal', 0.89, 0.91, [(0, 0), (0.3, 1.0), (1, 0.1)], 0.02, 6),
    Fin('caudal', 1.0, 1.0, coda_falcata(3.2, 0.95), 0.3, 36),
    Fin('pectoral', 0.2, 0.24, [(0, 0.06), (0.4, 0.1), (1.0, 0.02), (0.75, -0.06), (0.3, -0.12), (0, -0.1)], 0.18, 14,
        dir=(0.7, 0.3, -0.55))]


def _braccialetto(c, x=-0.215, raggio=0.0042, inclinato=32.0, nome='Braccialetto'):
    """Il braccialetto di plastica fucsia infilato sulla spada in x (< 0): un anello che abbraccia la spada,
    appeso (la parte di sopra appoggiata sul filo della lama) e storto di `inclinato` gradi."""
    P = c.P
    r = c.forma.rostro
    wy, wz, zc = (float(np.asarray(v).ravel()[0]) for v in P.sezione_rostro(r, np.array([x], F)))
    R = wy + raggio * 1.15 + 0.003                # il raggio dell'anello: largo quanto la spada lì
    centro = np.array((x, 0.0, zc + wz - (R - raggio)), F)
    Rm = P.sdf.rot_matrix('z', inclinato)
    anello = P.sdf.torus((0.0, 0.0, 0.0), R, raggio, axis='x')

    def f(p):
        return anello(((p - centro) @ Rm).astype(F)).astype(F)
    m = R + raggio + 0.006
    return P.oggetto_sdf(nome, f, centro - m, centro + m, _plastica(c, 'PlasticaFucsia', (1.0, 0.02, 0.32)), res=0.0006)


def _senza_rostro(c, f):
    """campo: toglie dal cranio quello che sta davanti al muso (il rostro): lo rifà un extra a parte, intero."""
    def g(p):
        return np.maximum(f(p), -(p[:, 0] + 0.003)).astype(F)
    return g


def _rostro_intero(c, nome='Rostro'):
    """Il rostro della forma (la spada) come osso a parte, liscio e con la griglia fine: il cranio della famiglia
    lo erode e la punta, sottile un paio di millimetri, sparisce («la spada intatta»)."""
    f, lo, hi = c.P.rostro_campo(c.body)
    return c.P.oggetto_sdf(nome, f, lo, hi, _osso(c), res=0.0006)


def _extra_spadossa(c):
    c.obs.append(_rostro_intero(c, 'Spada'))
    _togli(c, 'Spine')
    c.obs.append(_lisca(c, vertebre=26, spessore=1.2, minimo=0.0024, pterigiofori=True, ipurale=True)[0])
    c.obs.append(_braccialetto(c))


SPECIE['spadossa'] = Specie(
    forma=replace(_FORMA_SPADA, fins=_PINNE_SPADA_OSSO, piega=[(0, -9), (0.3, -3), (0.65, 3), (1.0, 12)]),
    aspetto=Look(back=(0.05, 0.04, 0.07), flank=(0.2, 0.18, 0.22), belly=(0.55, 0.53, 0.52), fin=(0.07, 0.06, 0.09),
                 iris=(0.3, 0.35, 0.4), iris_dark=(0.05, 0.06, 0.08), metal=0.35, irid=0.15, squame=0.0, linea_laterale=0.0,
                 lucido=0.5),
    campo=_senza_rostro, extra=_extra_spadossa,
    famiglia='skeletal', piano='rostro', opzioni=dict(vertebre=1, striscia=False, peduncolo=None))


# ── Sega d'Ossa (pesce sega, Pristis pectinata) — dalla prova del rostro a sega su una razza (piano 'razza'; la
#    forma è quella della prova: le altre famiglie la copiano da qui) ──
# Come le razze, costruito con il dorso verso la camera: z è la larghezza, y lo spessore. Il corpo è quasi da
# squalo (disco stretto: pettorali e pelviche come lobi), la sega è un Rostro largo in z con i denti sui bordi.
# Da scheletro: «nel Mediterraneo non se ne vedono da cent'anni. Questo non lo sa» → lo scheletro delle razze
# della famiglia (il cranio è il tronco davanti, cranio_t 0.15, e il ventaglio di cartilagine nelle ali), con
# le ossa vecchie, ingiallite e macchiate (rivestite in un osso più sporco), i balani incrostati sulla sega,
# sul cranio e sulla colonna (extra), e qualche dente della sega che manca, con l'alveolo vuoto (campo).
_DENTI_PERSI = {1: (3, 8, 9, 14, 18), -1: (5, 11, 12, 17)}   # per lato della sega: gli indici dei denti che mancano


def _denti_persi_sega(c, f):
    """campo: toglie dalla sega i denti di _DENTI_PERSI (gli stessi punti di pesci.rostro_campo), lasciando nel
    bordo la tacca tonda dell'alveolo."""
    r = c.forma.rostro
    L = float(r.lunghezza)
    via = []
    for sg, quali in _DENTI_PERSI.items():
        for i in quali:
            x = -L * (0.05 + 0.92 * i / max(r.denti - 1, 1))
            wy, wz, zc = (float(np.asarray(v).ravel()[0]) for v in c.P.sezione_rostro(r, np.array([x], F)))
            a = np.array((x, 0.0, zc + sg * wz * 0.9), F)
            b = a + np.array((-0.25, 0.0, sg * 1.0), F) * max(r.altezza, r.larghezza) * 0.55
            via.append((a, b, min(wy, wz), zc, wz, sg))

    def g(p):
        d = f(p)
        for a, b, sp, zc, wz, sg in via:
            ab = b - a
            t = np.clip(((p - a) @ ab) / float(ab @ ab), 0.0, 1.0)
            dist = np.linalg.norm(p - (a + t[:, None] * ab), axis=1)
            fuori = sg * (p[:, 2] - zc) - wz * 0.93            # > 0: fuori dal bordo della lama
            d = np.maximum(d, -np.maximum(dist - sp * 1.7, -fuori))
            alveolo = np.linalg.norm(p - (a + np.array((0.0, 0.0, sg * wz * 0.1), F)), axis=1) - sp * 0.6
            d = np.maximum(d, -alveolo)
        return d.astype(F)
    return g


def _balani(c, seme=5, nome='Balani'):
    """I balani (i denti di cane degli scogli) incrostati sulle ossa: coni bassi col buco in cima, a gruppi,
    sulla faccia della sega, sul cranio e sulla colonna, dal lato della camera."""
    P, body = c.P, c.body
    rng = np.random.default_rng(seme)
    r = c.forma.rostro
    L = float(r.lunghezza)
    posti = []                                  # (punto sulla pelle, normale)
    for _ in range(7):                          # a gruppi sulla sega
        xg, zg = rng.uniform(-L * 0.9, -0.03), rng.uniform(-0.5, 0.5)
        for _ in range(rng.integers(3, 6)):
            x = float(np.clip(xg + rng.normal(0, 0.012), -L * 0.95, -0.01))
            wy, wz, zc = (float(np.asarray(v).ravel()[0]) for v in P.sezione_rostro(r, np.array([x], F)))
            dz = float(np.clip(zg + rng.normal(0, 0.15), -0.6, 0.6)) * wz
            posti.append((np.array((x, -wy * math.sqrt(1 - (dz / wz) ** 2), zc + dz), F), np.array((0.0, -1.0, 0.0), F)))
    for _ in range(10):                         # sul cranio
        p, n = body.superficie(float(rng.uniform(0.02, 0.13)), float(rng.uniform(-0.6, 0.6)), -1)
        posti.append((p, n))
    for _ in range(12):                         # sulla colonna
        x = float(rng.uniform(0.2, 0.85))
        zc, h, w = _sez(body, x)
        rv = max(0.0035, min(h, w) * 0.16)
        posti.append((np.array((x, -rv * 0.9, zc + rng.uniform(-0.4, 0.4) * rv), F), np.array((0.0, -1.0, 0.0), F)))
    A, B, R1, R2, buchi, rb = [], [], [], [], [], []
    for p, n in posti:
        rr, hh = rng.uniform(0.0026, 0.0045), rng.uniform(0.0022, 0.0038)
        A.append(p - n * 0.0012)
        B.append(p + n * hh)
        R1.append(rr)
        R2.append(rr * 0.55)
        buchi.append(p + n * (hh + 0.0004))
        rb.append(rr * 0.4)
    fc, lo, hi = P.campo_coni(A, B, R1, R2)
    buchi, rb = np.array(buchi, F), np.array(rb, F)

    def f(q):
        d = fc(q)
        for cb, r_ in zip(buchi, rb):
            d = np.maximum(d, -(np.linalg.norm(q - cb, axis=1) - r_))
        return d.astype(F)
    mat = P.materiale('Balano', (0.58, 0.56, 0.5), rough=0.85, coat=0.1)
    return P.oggetto_sdf(nome, f, lo, hi, mat, res=0.0005)


def _mat_ossa_vecchie(c):
    """Ossa di cent'anni: ingiallite e brune, opache, con le macchie scure e le chiazze verdastre delle alghe."""
    m, g = c.P.material('OssaVecchie')
    co = g.texcoord('Object')
    n = g.noise(co, scale=28.0, detail=5.0, rough=0.62)
    n2 = g.noise(co, scale=9.0, detail=3.0, rough=0.5)
    fine = g.noise(co, scale=150.0, detail=2.0)
    col = g.mix(g.smoothstep(0.35, 0.75, n.fac), (0.66, 0.53, 0.31), (0.42, 0.31, 0.16))
    col = g.mix(g.mul(g.smoothstep(0.58, 0.72, n2.fac), 0.75), col, (0.26, 0.3, 0.14))
    col = g.mix(g.mul(g.smoothstep(0.6, 0.7, n.fac), 0.85), col, (0.11, 0.075, 0.04))
    ao = g.ao(distance=0.012, samples=8)
    col = g.mix(g.mul(g.sub(1.0, ao), 0.85), col, (0.08, 0.05, 0.03))
    g.output_material(g.principled(color=col, rough=0.62, coat=0.15, coat_rough=0.3, sss=0.1, sss_radius=(1, 0.7, 0.4),
                                   sss_scale=0.003, normal=g.bump(g.add(n.fac, g.mul(fine.fac, 0.5)), strength=0.35,
                                                                  distance=0.0015)))
    return m


def _extra_sega(c):
    vecchie = _mat_ossa_vecchie(c)
    for nome in ('Skull', 'Spine', 'RaggiDisco'):
        _rivesti(c, nome, vecchie)
    c.obs.append(_balani(c))


SPECIE['sega_dossa'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.03, 0.035), (0.1, 0.055), (0.25, 0.07), (0.4, 0.068), (0.55, 0.055), (0.7, 0.04), (0.85, 0.025), (1, 0.015)],
        bot=[(0, 0.0), (0.03, -0.035), (0.1, -0.055), (0.25, -0.07), (0.4, -0.068), (0.55, -0.055), (0.7, -0.04), (0.85, -0.025),
             (1, -0.015)],
        w=[(0, 0.004), (0.05, 0.015), (0.15, 0.028), (0.35, 0.04), (0.55, 0.038), (0.75, 0.028), (0.9, 0.018), (1, 0.012)],
        eye_t=0.08, eye_z=0.0, eye_r=0.009, occhi=[(0.08, 0.034, 0.009, -1), (0.08, -0.034, 0.009, -1)], spiracoli=0.006,
        bocca='nessuna', branchie='nessuna',
        rostro=Rostro('sega', lunghezza=0.34, z=0.0, larghezza=0.008, altezza=0.03, punta=0.62, denti=22),
        disco=Disco(contorno=[(0, 0.0), (0.05, 0.04), (0.14, 0.062), (0.2, 0.1), (0.26, 0.15), (0.31, 0.155), (0.35, 0.08),
                              (0.4, 0.062), (0.47, 0.072), (0.52, 0.1), (0.56, 0.098), (0.6, 0.05), (0.65, 0.0), (1, 0.0)],
                    spessore=[(0, 0.003), (0.15, 0.01), (0.3, 0.012), (0.5, 0.01), (0.62, 0.004), (1, 0.001)]),
        fins=[Fin('dorsal', 0.44, 0.52, DORSALE_SQUALO, 0.07, 24, carnosa=True, spessore=0.005),
              Fin('dorsal', 0.7, 0.77, DORSALE_SQUALO, 0.06, 24, carnosa=True, spessore=0.004),
              Fin('caudal', 1.0, 1.0, coda_eterocerca(lobo=1.0, alzata=1.2, lobo_basso=0.4, basso=0.8), 0.16, 40,
                  carnosa=True, spessore=0.005)]),
    aspetto=Look(back=(0.26, 0.25, 0.2), flank=(0.32, 0.31, 0.26), belly=(0.82, 0.8, 0.76), fin=(0.24, 0.23, 0.19),
                 iris=(0.6, 0.55, 0.35), iris_dark=(0.12, 0.1, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.35, ruvido=0.5, tinta_rostro=0.4),
    campo=_denti_persi_sega, extra=_extra_sega,
    famiglia='skeletal', piano='razza', opzioni=dict(cranio_t=0.15, osso=(0.94, 0.75, 0.45)))
