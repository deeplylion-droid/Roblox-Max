"""
Corrotti: occhi in più, bocche sbagliate, escrescenze, melma nera (src/game/catalog.ts, docs/CATALOGO.md).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast

La famiglia (pesci.corrupt) mette gli occhi umani in più sul fianco sinistro, con la pece attorno e che cola,
e un'escrescenza; il resto lo fanno gli extra delle specie, con gli aiuti qui sotto: _pittura (dipinge la
pelle del corpo dove vuole la specie: pece, macchie, scritte, uno specchio), le gocce e i fili di pece, i
campi di tante sfere (pustole, grumi) e di catene di coni (dita, filamenti, zanne).
"""
import math

import numpy as np

from .base import (PELVICA, PETTORALE_TONDA, RITRATTO_PROTOTIPI, Disegno, Filamento, Fin, Look, Shape, Specie, Spine,
                   coda_forcuta, coda_tonda, coda_tronca)

SPECIE = {}

# ── Trigliocchi (triglia di scoglio, Mullus surmuletus) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['trigliocchi'] = Specie(
    forma=Shape(
        top=[(0, -0.045), (0.02, -0.018), (0.05, 0.03), (0.1, 0.07), (0.18, 0.096), (0.3, 0.108), (0.5, 0.1), (0.72, 0.068), (0.9, 0.04), (1, 0.034)],
        bot=[(0, -0.052), (0.03, -0.075), (0.15, -0.09), (0.38, -0.094), (0.6, -0.078), (0.8, -0.052), (1, -0.034)],
        w=[(0, 0.012), (0.08, 0.04), (0.25, 0.054), (0.5, 0.05), (0.8, 0.028), (1, 0.014)],
        eye_t=0.125, eye_z=0.046, eye_r=0.024, mouth_t=0.05, mouth_z0=-0.046, mouth_z1=-0.054, gill_t=0.24, barbels=True,
        fins=[Fin('dorsal', 0.28, 0.42, [(0, 0), (0.15, 1.0), (0.45, 0.95), (0.8, 0.55), (1, 0.05)], 0.12, 8, spiny=True),
              Fin('dorsal', 0.56, 0.68, [(0, 0), (0.2, 0.8), (0.6, 0.6), (1, 0.05)], 0.07, 9),
              Fin('anal', 0.58, 0.7, [(0, 0), (0.2, 0.75), (0.6, 0.55), (1, 0.05)], 0.065, 8),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.4, 0.3), 0.23, 18),
              Fin('pectoral', 0.25, 0.27, [(0, 0), (0.5, 0.3), (1.0, 0.15), (0.8, 0.0), (0, -0.06)], 0.14, 10),
              Fin('pelvic', 0.3, 0.32, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.08, 6)]),
    aspetto=Look(back=(0.52, 0.12, 0.08), flank=(0.72, 0.30, 0.22), belly=(0.78, 0.62, 0.55), fin=(0.62, 0.38, 0.28),
                 iris=(0.85, 0.55, 0.2), iris_dark=(0.4, 0.12, 0.04), metal=0.25, pattern='redmullet', irid=0.2),
    famiglia='corrupt', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ───────────────────────── aiuti degli extra della famiglia ─────────────────────────
# Gli extra e i campi girano con il pesce ancora dritto (prima della piega e della posa): le coordinate sono
# quelle del corpo (muso in x = 0 verso −X, dorso +Z, fianco sinistro −Y verso la camera).

# le iridi degli occhi umani in più (si sceglie da qui, per non avere tutti gli occhi uguali)
IRIDE_VERDE, IRIDE_AZZURRA, IRIDE_CASTANA = (0.30, 0.42, 0.28), (0.22, 0.36, 0.55), (0.42, 0.26, 0.12)
IRIDE_GRIGIA, IRIDE_NOCCIOLA, IRIDE_NERA = (0.42, 0.45, 0.47), (0.5, 0.36, 0.16), (0.08, 0.06, 0.05)


def _corpo(c):
    """L'oggetto del corpo (la mesh con la pelle) fra quelli della famiglia."""
    return next(o for o in c.obs if o.name.startswith('Body'))


def _vertici(ob):
    """I vertici della mesh (N, 3), nelle coordinate del pesce."""
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    return co.reshape(-1, 3)


def _attributo(ob, nome, f):
    """Un attributo per vertice della mesh ob, calcolato da f(punti) → (N,), tenuto in 0..1."""
    val = np.clip(np.asarray(f(_vertici(ob)), np.float32), 0, 1)
    a = ob.data.attributes.new(nome, 'FLOAT', 'POINT')
    a.data.foreach_set('value', val)


def _stacca(g, nodo, nome):
    """Quello che entra nell'ingresso `nome` del nodo: il socket collegato (staccandolo) o il valore."""
    s = g.inp(nodo, nome)
    if s.is_linked:
        lk = s.links[0]
        src = lk.from_socket
        g.nt.links.remove(lk)
        return src
    try:
        return tuple(s.default_value)[:3]
    except TypeError:
        return float(s.default_value)


def _pittura(c, nome, peso, colore, ruvido=None, liscio=False, luce=0.0):
    """Dipinge la pelle del corpo dove peso(p) va a 1 (0..1, calcolato sui vertici del pesce dritto).
    colore: rgb, oppure una funzione g → (colore, alfa) (per esempio un'immagine proiettata: alfa limita la
    pittura); ruvido: la rugosità lì; liscio: niente squame né grana (la normale vera: uno specchio); luce:
    quanto il colore brilla da sé. Lì toglie il metallo e l'iridescenza della pelle. Si chiama anche più
    volte: le pitture si sovrappongono nell'ordine. Restituisce la maschera (socket)."""
    from nodes import Graph
    ob = _corpo(c)
    _attributo(ob, nome, peso)
    mat = ob.data.materials[0]
    g = Graph(mat.node_tree, clear=False)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    m = g.attr(nome)
    if callable(colore):
        col, alfa = colore(g)
        if alfa is not None:
            m = g.mul(m, alfa)
    else:
        col = colore
    g.set(bsdf, 'Base Color', g.mix(m, _stacca(g, bsdf, 'Base Color'), col))
    g.set(bsdf, 'Metallic', g.mixf(m, _stacca(g, bsdf, 'Metallic'), 0.0))
    g.set(bsdf, 'Thin Film Thickness', g.mixf(m, _stacca(g, bsdf, 'Thin Film Thickness'), 0.0))
    if ruvido is not None:
        g.set(bsdf, 'Roughness', g.mixf(m, _stacca(g, bsdf, 'Roughness'), ruvido))
    if liscio:
        vera = g.geometry('Normal')
        for ingresso in ('Normal', 'Coat Normal'):
            if g.inp(bsdf, ingresso).is_linked:
                n = g.node('ShaderNodeMix', data_type='VECTOR')
                g.set(n, 'Factor', m)
                g.set(n, 'A', _stacca(g, bsdf, ingresso))
                g.set(n, 'B', vera)
                g.set(bsdf, ingresso, g.out(n, 'Result'))
    if luce:
        g.set(bsdf, 'Emission Color', g.mix(m, _stacca(g, bsdf, 'Emission Color'), col))
        g.set(bsdf, 'Emission Strength', g.add(_stacca(g, bsdf, 'Emission Strength'), g.mul(m, luce)))
    return m


def _vicino(centri, raggi, sfuma):
    """Peso per _pittura: 1 entro i raggi dai centri, che sfuma a 0 in `sfuma` (macchie tonde, aloni)."""
    C = np.asarray(centri, np.float32).reshape(-1, 3)
    R = np.broadcast_to(np.asarray(raggi, np.float32), (len(C),))

    def f(p):
        out = np.zeros(len(p), np.float32)
        for cc, rr in zip(C, R):
            out = np.maximum(out, np.clip(1 - (np.linalg.norm(p - cc, axis=1) - rr) / sfuma, 0, 1))
        return out
    return f


def _goccia(c, nome, attacco, lunghezza, r0=0.0022, r1=0.005, dir=(0.0, -0.12, -1.0), mat=None):
    """Una goccia di pece che pende da `attacco` (aiuto comune: drip), con il suo oggetto."""
    a = np.asarray(attacco, np.float32)
    f = c.P.drip(a, lunghezza, r0=r0, r1=r1, dir=dir)
    m = lunghezza + r1 * 2 + 0.008
    c.obs.append(c.P.oggetto_sdf(nome, f, a - m, a + m, mat or c.P.tar_material(), res=0.0008 if c.fast else 0.0005))


def _filo(c, nome, a, b, cedimento, r=0.0014, mat=None):
    """Un filo di pece (o di bava) fra due punti, che si affloscia (aiuto comune: strand)."""
    a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
    f = c.P.strand(a, b, cedimento, r=r, n=10)
    lo = np.minimum(a, b) - r * 2 - 0.004
    hi = np.maximum(a, b) + r * 2 + 0.004
    lo[2] -= cedimento
    c.obs.append(c.P.oggetto_sdf(nome, f, lo, hi, mat or c.P.tar_material(), res=0.0008 if c.fast else 0.0005))


def _campo_sfere(C, R, k=6):
    """Campo di tante sfere di raggi diversi (pustole, grumi, bolle): KD-tree sui centri, le k più vicine.
    Restituisce (campo, lo, hi)."""
    from scipy.spatial import cKDTree
    C = np.asarray(C, np.float32).reshape(-1, 3)
    R = np.asarray(R, np.float32).ravel()
    tree = cKDTree(C)
    kk = min(k, len(C))

    def f(P):
        _, idx = tree.query(P, k=kk, workers=-1)
        idx = np.asarray(idx).reshape(len(P), kk)
        d = np.full(len(P), 10.0, np.float32)
        for j in range(kk):
            i = idx[:, j]
            d = np.minimum(d, np.linalg.norm(P - C[i], axis=1) - R[i])
        return d
    return f, C.min(0) - R.max() - 0.004, C.max(0) + R.max() + 0.004


def _percorso(a, d, lunghezza, n=12, curva=(0.0, 0.0, 0.0), onda=0.0, giri=1.5, fase=0.0, piano=(0.0, 0.0, 1.0)):
    """I punti di un filamento che parte da a nella direzione d: si piega con `curva` (sommata alla direzione
    a ogni passo, come Filamento.curva) e ondeggia di `onda` (radianti) attorno all'asse `piano`, con `giri`
    mezze onde lungo la lunghezza (filamenti che si muovono da soli, tentacoli)."""
    a = np.asarray(a, np.float32)
    d = np.asarray(d, np.float32)
    d = d / np.linalg.norm(d)
    cv = np.asarray(curva, np.float32)
    ax = np.asarray(piano, np.float32)
    ax = ax / np.linalg.norm(ax)
    passo = lunghezza / n
    pts = [a]
    for i in range(n):
        ang = onda * math.sin(math.pi * giri * i / n + fase)
        # la direzione del passo: d girata di ang attorno all'asse (formula di Rodrigues)
        dd = d * math.cos(ang) + np.cross(ax, d) * math.sin(ang) + ax * float(ax @ d) * (1 - math.cos(ang))
        pts.append(pts[-1] + dd * passo)
        d = d + cv * passo
        d = d / np.linalg.norm(d)
    return np.array(pts, np.float32)


def _catena(punti, raggi):
    """I segmenti di una catena di coni lungo i punti (un filamento, un dito, una zanna): (A, B, R1, R2) da
    sommare ad altri e passare a campo_coni."""
    P = np.asarray(punti, np.float32)
    r = np.asarray(raggi, np.float32)
    if r.ndim == 0 or len(r) != len(P):
        r = np.linspace(float(np.ravel(r)[0]), float(np.ravel(r)[-1]), len(P)).astype(np.float32)
    return list(P[:-1]), list(P[1:]), list(r[:-1]), list(r[1:])


def _coni(c, nome, segmenti, mat, res=None):
    """Un oggetto da tanti coni: segmenti = lista di (A, B, R1, R2) (vedi _catena)."""
    A, B, R1, R2 = [], [], [], []
    for a, b, r1, r2 in segmenti:
        A += list(a)
        B += list(b)
        R1 += list(r1)
        R2 += list(r2)
    f, lo, hi = c.P.campo_coni(A, B, R1, R2)
    if res is None:
        res = max(min(R2) * 0.8, 0.0004) if not c.fast else max(min(R2) * 0.8, 0.0007)
    c.obs.append(c.P.oggetto_sdf(nome, f, lo, hi, mat, res=res))


def _ruota(d, su):
    """La matrice (colonne = assi) di un oggetto con l'asse lungo d e il secondo asse verso su."""
    e1 = np.asarray(d, np.float32)
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.asarray(su, np.float32) - e1 * float(np.dot(su, e1))
    e2 = e2 / np.linalg.norm(e2)
    return np.stack([e1, e2, np.cross(e1, e2)], axis=1).astype(np.float32)


def _ellissoide(c, centro, raggi, R):
    """Campo di un ellissoide ruotato (R: colonne = i suoi assi; raggi lungo quegli assi)."""
    c0 = np.asarray(centro, np.float32)
    f = c.P.sdf.ellipsoid(c0, raggi)
    return c.P.sdf.rotate(f, R, center=c0)


# ───────────────────────── le specie ─────────────────────────

def _becco_pesce_palla(c):
    """Il becco del pesce palla: due placche di dente bianco, sopra e sotto il taglio della bocca."""
    P, sh = c.P, c.forma
    mat = P.materiale('BeccoPalla', (0.86, 0.82, 0.7), rough=0.25, coat=0.7, sss=0.3)
    for k, dz in enumerate((0.0055, -0.0055)):
        z = sh.mouth_z0 + dz
        f = P.sdf.ellipsoid((0.001, 0.0, z), (0.011, 0.02, 0.0065))
        c.obs.append(P.oggetto_sdf(f'BeccoPalla{k}', f, (-0.015, -0.028, z - 0.012), (0.02, 0.028, z + 0.012), mat, res=0.0006))


def _bubboni(c):
    """Pesce Bubbone: il becco, e al posto delle macchie le bolle nere gonfie, tese e lucide, in rilievo sulla
    pelle, con un livido attorno (una pittura)."""
    _becco_pesce_palla(c)
    body = c.body
    rng = np.random.default_rng(23)
    occhi = c.specie.opzioni.get('occhi_extra', [])
    C, R = [], []
    for s in (-1, 1):
        n = 0
        while n < (46 if s < 0 else 26):
            t, v = float(rng.uniform(0.07, 0.74)), float(rng.uniform(-0.25, 0.97))
            if t < 0.2 and v > 0.2:
                continue                      # non sull'occhio del pesce
            if s < 0 and any(abs(t - te) < re * 2.2 and abs(v - ve) < 0.32 for te, ve, re in occhi):
                continue                      # né sugli occhi in più
            r = float(rng.choice([0.006, 0.008, 0.01, 0.013, 0.017], p=[0.3, 0.27, 0.2, 0.15, 0.08]))
            p, nr = body.superficie(t, v, s)
            C.append(p - nr * r * 0.3)
            R.append(r)
            n += 1
    f, lo, hi = _campo_sfere(C, R)
    mat = c.P.materiale('Bubboni', (0.012, 0.007, 0.012), rough=0.07, coat=1.0, sss=0.12)
    c.obs.append(c.P.oggetto_sdf('Bubboni', f, lo, hi, mat, res=0.0011 if c.fast else 0.0006))
    # il livido violaceo attorno a ogni bolla
    _pittura(c, 'livido', _vicino(C, np.array(R) * 0.95, 0.008), (0.1, 0.055, 0.07), ruvido=0.3)


# ── Pesce Bubbone (pesce palla argenteo, Lagocephalus sceleratus) ──
# Gonfio: la testa e la pancia sono una palla, la coda resta stretta. Le spinette sulla pancia sono
# Shape.spine (coni fusi nella pelle); il becco a quattro denti e le bolle nere sono l'extra («si gonfiano
# anche le bolle nere che ha sulla pelle»): al posto delle macchie, pustole nere in rilievo con il livido
# attorno; due occhi umani in mezzo alle bolle.
SPECIE['pesce_bubbone'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.03, 0.06), (0.1, 0.15), (0.22, 0.21), (0.38, 0.23), (0.55, 0.2), (0.7, 0.12), (0.82, 0.055),
             (0.92, 0.035), (1, 0.03)],
        bot=[(0, -0.05), (0.04, -0.12), (0.12, -0.21), (0.28, -0.27), (0.45, -0.27), (0.6, -0.2), (0.74, -0.1), (0.85, -0.045),
             (1, -0.03)],
        w=[(0, 0.02), (0.05, 0.1), (0.15, 0.18), (0.32, 0.22), (0.5, 0.2), (0.68, 0.12), (0.82, 0.05), (1, 0.018)],
        eye_t=0.13, eye_z=0.085, eye_r=0.034, mouth_t=0.03, mouth_z0=-0.03, mouth_z1=-0.034, gill_t=0.3, branchie='nessuna',
        spine=[Spine(0.06, 0.72, -1.0, -0.12, 170, lunghezza=0.016, raggio=0.0034, inclinazione=0.35, seme=1),
               Spine(0.1, 0.62, 0.15, 0.9, 50, lunghezza=0.01, raggio=0.0026, inclinazione=0.4, seme=2)],
        fins=[Fin('dorsal', 0.72, 0.79, [(0, 0), (0.2, 0.9), (0.6, 1.0), (1, 0.1)], 0.07, 10),
              Fin('anal', 0.73, 0.8, [(0, 0), (0.2, 0.9), (0.6, 1.0), (1, 0.1)], 0.065, 10),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.7, 0.15, 0.85), 0.17, 16),
              Fin('pectoral', 0.3, 0.31, PETTORALE_TONDA, 0.08, 10, z=0.1)]),
    aspetto=Look(back=(0.16, 0.18, 0.15), flank=(0.55, 0.58, 0.58), belly=(0.86, 0.86, 0.83), fin=(0.3, 0.32, 0.3),
                 iris=(0.85, 0.75, 0.4), iris_dark=(0.2, 0.15, 0.05), metal=0.35, irid=0.2, squame=0.0, linea_laterale=0.0,
                 disegni=[Disegno('macchie', colore=(0.04, 0.045, 0.04), forza=0.8, scala=70, r=0.12, v0=0.25),
                          Disegno('strisce', colore=(0.78, 0.8, 0.82), forza=0.6, n=1, v0=-0.3, v1=0.1, larghezza=0.3)]),
    extra=_bubboni,
    famiglia='corrupt', piano='palla',
    opzioni=dict(occhi_extra=[(0.47, 0.3, 0.032), (0.3, -0.42, 0.02)], iridi=[IRIDE_AZZURRA, IRIDE_CASTANA],
                 escrescenza=None, colature=2))


def _melma_missina(c):
    """Missina della Melma: la melma nera, lucida, che la copre a chiazze (più sotto che sopra: cola), le
    gocce che pendono dalla pancia e i fili che si afflosciano fra un punto e l'altro della pancia."""
    P, body = c.P, c.body
    base = body.base()
    n3 = P.sdf.Noise3(31)

    def spessore(p):
        nz = n3(p, scale=0.03, octaves=3)
        v = np.clip(body.norm_v(p), -1.2, 1.2)
        sotto = np.clip(0.5 - v, 0, 1.5)              # la melma scende: più sotto che sopra
        m = np.clip((nz + 0.22 * sotto - 0.02) * 4.0, 0, 1)
        return m * (0.0025 + 0.0025 * sotto)

    def f(p):
        return base(p) - spessore(p) + 0.0015
    lo, hi = body.bounds(pad=0.012)
    c.obs.append(P.oggetto_sdf('MelmaNera', f, lo, hi, P.tar_material(), res=0.0013 if c.fast else 0.0008))
    # gocce dalla pancia e fili fra un punto e l'altro
    rng = np.random.default_rng(5)
    for k, t in enumerate((0.11, 0.2, 0.27, 0.36, 0.47, 0.55, 0.63, 0.74, 0.86)):
        p, _ = body.superficie(t, -0.97, -1)
        _goccia(c, f'GocciaMelma{k}', p + np.array((0, 0.002, 0.001), np.float32), float(rng.uniform(0.018, 0.05)),
                r0=0.0025, r1=float(rng.uniform(0.004, 0.0065)), dir=(float(rng.uniform(-0.1, 0.1)), -0.05, -1.0))
    for k, (t0, t1, cad) in enumerate(((0.14, 0.24, 0.03), (0.4, 0.52, 0.045), (0.58, 0.7, 0.025), (0.78, 0.9, 0.035))):
        a, _ = body.superficie(t0, -0.9, -1)
        b, _ = body.superficie(t1, -0.85, -1)
        _filo(c, f'FiloMelma{k}', a, b, cad, r=0.0016)
    # e dalla bocca, fra i barbigli
    a, _ = body.superficie(0.02, -0.5, -1)
    _goccia(c, 'BavaMelma', a, 0.045, r0=0.002, r1=0.005, dir=(-0.15, -0.1, -1.0))


# ── Missina della Melma (missina, Myxine glutinosa) ──
# Niente occhi veri (occhi=[]: due macchie chiare sotto la pelle), tre paia di barbigli attorno alla bocca
# (Shape.filamenti), la fila dei pori del muco sul fianco (disegno 'linea' a puntini), la piega della coda.
# La famiglia: «tanta melma da riempire il secchio. È nera»: la melma nera a chiazze, gocce e fili (extra);
# tre occhi umani piccoli dove la missina non ne ha.
SPECIE['missina_della_melma'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.03, 0.012), (0.1, 0.021), (0.4, 0.027), (0.7, 0.027), (0.9, 0.023), (1, 0.009)],
        bot=[(0, -0.012), (0.04, -0.021), (0.15, -0.026), (0.5, -0.029), (0.8, -0.025), (0.95, -0.015), (1, -0.006)],
        w=[(0, 0.008), (0.05, 0.017), (0.3, 0.023), (0.7, 0.019), (0.9, 0.011), (1, 0.004)],
        eye_t=0.05, eye_z=0.01, eye_r=0.006, occhi=[], mouth_t=0.022, mouth_z0=-0.005, mouth_z1=-0.008,
        branchie='pori', n_branchie=1, gill_t=0.3,
        filamenti=[Filamento(t=0.004, v=0.45, lunghezza=0.024, raggio=0.0021, dir=(-0.7, 0.35, 0.25), curva=(0, 0, -3)),
                   Filamento(t=0.006, v=-0.2, lunghezza=0.02, raggio=0.002, dir=(-0.6, 0.5, -0.3), curva=(0, 0, -3)),
                   Filamento(t=0.018, v=-0.75, lunghezza=0.018, raggio=0.0019, dir=(-0.35, 0.55, -0.75), curva=(3, 0, 0))],
        fins=[Fin('dorsal', 0.68, 1.0, [(0, 0), (0.1, 0.7), (0.5, 1.0), (0.9, 1.0), (1, 0.7)], 0.012, 40),
              Fin('anal', 0.86, 1.0, [(0, 0), (0.2, 0.8), (0.9, 1.0), (1, 0.7)], 0.011, 16),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.0, 0.9), 0.035, 14)],
        piega=[(0, 12), (0.3, -22), (0.6, 18), (1.0, -26)]),
    aspetto=Look(back=(0.42, 0.29, 0.27), flank=(0.5, 0.37, 0.34), belly=(0.6, 0.47, 0.43), fin=(0.45, 0.33, 0.3),
                 metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0, lucido=0.9, ruvido=0.2,
                 disegni=[Disegno('linea', colore=(0.85, 0.78, 0.72), forza=0.85, v=-0.6, larghezza=0.06, n=70, u0=0.12, u1=0.95),
                          Disegno('macchia', colore=(0.62, 0.5, 0.45), forza=0.7, u=0.05, v=0.25, r=0.006)]),
    extra=_melma_missina,
    famiglia='corrupt', piano='anguilliforme',
    opzioni=dict(occhi_extra=[(0.075, 0.3, 0.0085), (0.3, 0.2, 0.011), (0.55, 0.15, 0.0095)],
                 iridi=[IRIDE_GRIGIA, IRIDE_AZZURRA, IRIDE_CASTANA], escrescenza=None, colature=3))


def _pelle_dita(c):
    """La pelle delle dita: carne grigio-rosata da morto, più scura e grinzosa sulle nocche (attributo
    'nocca' dell'oggetto)."""
    m, g = c.P.material('PelleDita')
    co = g.texcoord('Object')
    n = g.noise(co, scale=320.0, detail=3.0)
    n2 = g.noise(co, scale=60.0, detail=2.0)
    nocca = g.attr('nocca')
    col = g.mix(g.smoothstep(0.35, 0.7, n2.fac), (0.6, 0.46, 0.43), (0.5, 0.38, 0.37))
    col = g.mix(g.mul(nocca, 0.85), col, (0.33, 0.22, 0.21))
    g.output_material(g.principled(color=col, rough=0.48, coat=0.3, coat_rough=0.15, sss=0.3, sss_radius=(1, 0.4, 0.3),
                                   sss_scale=0.003, normal=g.bump(g.add(n.fac, g.mul(nocca, 0.8)), strength=0.3, distance=0.0008)))
    return m


def _dita_gallincubo(c):
    """Gallincubo: al posto dei tre raggi liberi sotto ogni pettorale, tre dita umane che camminano sulla punta
    (e di notte bussano): tre falangi con le nocche grinzose, l'unghia sporca sull'ultima."""
    P, body = c.P, c.body
    pinna = next(f for f in c.forma.fins if f.kind == 'pectoral')
    pelle = _pelle_dita(c)
    unghia = P.materiale('Unghia', (0.7, 0.62, 0.5), rough=0.22, coat=0.8, sss=0.15)
    for s in (-1, 1):
        for i in range(3):
            base, nr = body.superficie(pinna.a - 0.014 - 0.012 * i, -0.62 - 0.09 * i, s)
            k = 1.0 - 0.09 * i                         # le dita dietro un poco più corte
            dirs = [(-0.2 + 0.15 * i, 0.55, -1.0), (-0.85 + 0.1 * i, 0.32, -0.55), (-0.18, 0.1, -1.0)]
            lung = [0.05 * k, 0.034 * k, 0.025 * k]
            rag = [0.0086, 0.0079, 0.0071, 0.0057]
            pts = [base - nr * 0.006]
            for d, L in zip(dirs, lung):
                d = np.array((d[0], s * d[1], d[2]), np.float32)
                pts.append(pts[-1] + d / np.linalg.norm(d) * L)
            nocche = [(pts[j], pts[j + 1] - pts[j - 1]) for j in (1, 2)]
            parti = []
            for j in range(3):
                parti.append(P.sdf.round_cone(pts[j], pts[j + 1], rag[j], rag[j + 1]))
            for q, _ in nocche:
                parti.append(P.sdf.sphere(q, rag[1] * 1.12))     # la nocca gonfia
            dito = P.sdf.union(*parti, k=0.004)

            def grinze(p, nocche=nocche):
                # le pieghe di traverso sulle nocche
                out = np.zeros(len(p), np.float32)
                for q, ax in nocche:
                    ax = ax / np.linalg.norm(ax)
                    h = (p - q) @ ax
                    vic = np.clip(1 - np.linalg.norm(p - q, axis=1) / 0.013, 0, 1)
                    out += vic * (np.exp(-((h - 0.0025) / 0.0008) ** 2) + np.exp(-((h + 0.0005) / 0.0008) ** 2)
                                  + np.exp(-((h + 0.0035) / 0.0008) ** 2))
                return out

            def f(p, dito=dito, grinze=grinze):
                return dito(p) + 0.0006 * grinze(p)

            def nocca(p, grinze=grinze):
                return np.clip(grinze(p) * 0.6, 0, 1)
            P_ = np.array(pts)
            lo, hi = P_.min(0) - 0.014, P_.max(0) + 0.014
            c.obs.append(P.oggetto_sdf(f'Dito{s}_{i}', f, lo, hi, pelle, res=0.0008 if c.fast else 0.0004,
                                       attrs={'nocca': nocca}))
            # l'unghia sul dorso dell'ultima falange (il lato davanti e in alto della curva)
            d3 = pts[3] - pts[2]
            d3 /= np.linalg.norm(d3)
            fuori = np.array((-1.0, s * 0.35, 0.25), np.float32)
            fuori -= d3 * float(fuori @ d3)
            fuori /= np.linalg.norm(fuori)
            cu = pts[3] - d3 * 0.0085 + fuori * rag[3] * 0.72
            R = _ruota(d3, fuori)
            fu = _ellissoide(c, cu, (0.0072, 0.0016, 0.0058), R)
            c.obs.append(P.oggetto_sdf(f'Unghia{s}_{i}', fu, cu - 0.012, cu + 0.012, unghia, res=0.0005 if c.fast else 0.0003))


# ── Gallincubo (gallinella, Chelidonichthys lucerna) ──
# Testa grossa e corazzata: il profilo dal muso alla nuca è una rampa dritta e ripida, gli occhi alti sotto il
# bordo osseo, la bocca bassa; le placche della testa (disegno 'reticolo' solo sulla testa) e le spinette.
# Le pettorali enormi a ventaglio (verdi, puntinate di blu, il bordo blu). «Le pinne davanti sono diventate
# dita… di notte bussa»: al posto dei tre raggi liberi (Fin.liberi) tre dita umane per lato (extra); tre
# occhi umani sul fianco, sopra la pettorale.
SPECIE['gallincubo'] = Specie(
    forma=Shape(
        top=[(0, -0.028), (0.015, -0.0157), (0.04, 0.0047), (0.08, 0.0374), (0.12, 0.066), (0.17, 0.08), (0.25, 0.086), (0.38, 0.08),
             (0.55, 0.066), (0.75, 0.044), (0.9, 0.028), (1, 0.022)],
        bot=[(0, -0.04), (0.03, -0.058), (0.08, -0.07), (0.16, -0.074), (0.3, -0.071), (0.45, -0.063), (0.65, -0.047),
             (0.85, -0.03), (1, -0.022)],
        w=[(0, 0.02), (0.04, 0.042), (0.12, 0.06), (0.25, 0.056), (0.5, 0.041), (0.75, 0.025), (1, 0.012)],
        eye_t=0.115, eye_z=0.036, eye_r=0.02, mouth_t=0.065, mouth_z0=-0.036, mouth_z1=-0.046, gill_t=0.22,
        spine=[Spine(0.03, 0.2, 0.3, 0.95, 14, lunghezza=0.007, raggio=0.0032, inclinazione=0.6, seme=4),
               Spine(0.19, 0.21, -0.2, 0.4, 3, lunghezza=0.012, raggio=0.003, inclinazione=0.85, seme=6)],
        fins=[Fin('pectoral', 0.2, 0.23, [(0, 0.05), (0.35, 0.45), (0.8, 0.5), (1.0, 0.2), (0.95, -0.15), (0.6, -0.3), (0, -0.1)],
                  0.3, 16, z=-0.1, dir=(0.55, 0.75, -0.2), su=(1.0, 0.0, 0.3),
                  colore=(0.12, 0.3, 0.32), bordo=(0.12, 0.3, 0.8), macchie=0.7, colore_macchie=(0.15, 0.35, 0.9)),
              Fin('dorsal', 0.24, 0.38, [(0, 0), (0.1, 0.9), (0.35, 1.0), (0.8, 0.5), (1, 0.05)], 0.08, 9, spiny=True),
              Fin('dorsal', 0.4, 0.75, [(0, 0), (0.05, 0.8), (0.5, 0.7), (1, 0.05)], 0.05, 18),
              Fin('anal', 0.42, 0.75, [(0, 0), (0.05, 0.8), (0.5, 0.7), (1, 0.05)], 0.045, 16),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.6, 0.2, 0.85), 0.18, 16),
              Fin('pelvic', 0.24, 0.25, PELVICA, 0.06, 6)]),
    aspetto=Look(back=(0.45, 0.2, 0.13), flank=(0.6, 0.36, 0.28), belly=(0.85, 0.78, 0.72), fin=(0.5, 0.3, 0.25),
                 iris=(0.8, 0.6, 0.3), iris_dark=(0.3, 0.15, 0.05), metal=0.2, irid=0.2, squame=0.7,
                 disegni=[Disegno('reticolo', colore=(0.2, 0.06, 0.04), forza=0.75, scala=55, larghezza=0.09, u1=0.21, v0=-0.4),
                          Disegno('macchie', colore=(0.3, 0.1, 0.06), forza=0.5, scala=30, r=0.3, u0=0.2, v0=0.1)]),
    extra=_dita_gallincubo,
    famiglia='corrupt', piano='pettorali',
    opzioni=dict(occhi_extra=[(0.31, 0.5, 0.017), (0.5, 0.38, 0.022), (0.68, 0.25, 0.014)],
                 iridi=[IRIDE_VERDE, IRIDE_NOCCIOLA, IRIDE_AZZURRA], escrescenza=None, colature=2))
