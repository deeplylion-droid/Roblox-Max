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

from .base import (DORSALE_SQUALO, PELVICA, PETTORALE, PETTORALE_TONDA, RITRATTO_PROTOTIPI, Disco, Disegno, Filamento, Fin,
                   Fotofori, Look, Ritratto, Shape, Specie, Spine, coda_eterocerca, coda_falcata, coda_forcuta, coda_tonda,
                   coda_tronca)

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


def _pittura(c, nome, peso, colore, ruvido=None, liscio=False, luce=0.0, lucido=None):
    """Dipinge la pelle del corpo dove peso(p) va a 1 (0..1, calcolato sui vertici del pesce dritto).
    colore: rgb, oppure una funzione g → (colore, alfa) (per esempio un'immagine proiettata: alfa limita la
    pittura); ruvido: la rugosità lì; liscio: niente squame né grana (la normale vera: uno specchio); luce:
    quanto il colore brilla da sé; lucido: lo strato bagnato lì (Look.lucido vale per tutto il pesce). Lì
    toglie il metallo e l'iridescenza della pelle. Si chiama anche più volte: le pitture si sovrappongono
    nell'ordine. Restituisce la maschera (socket)."""
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
    if lucido is not None:
        g.set(bsdf, 'Coat Weight', g.mixf(m, _stacca(g, bsdf, 'Coat Weight'), lucido))
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


def _profilo(punti, t):
    """Il valore di un profilo (t, valore) in t, con la stessa curva di pesci.prof (Hermite alla Catmull-Rom):
    per mettere a mano cose nelle coordinate della forma prima di costruirla (una corona di occhi in più)."""
    pts = np.array(punti, np.float64)
    ts, vs = pts[:, 0], pts[:, 1]
    t = float(np.clip(t, ts[0], ts[-1]))
    i = int(np.clip(np.searchsorted(ts, t, side='right') - 1, 0, len(ts) - 2))
    t0, t1 = ts[i], ts[i + 1]
    dt = max(t1 - t0, 1e-6)
    u = (t - t0) / dt
    im, ip = max(i - 1, 0), min(i + 2, len(ts) - 1)
    m0 = (vs[i + 1] - vs[im]) / max(ts[i + 1] - ts[im], 1e-6) * dt
    m1 = (vs[ip] - vs[i]) / max(ts[ip] - ts[i], 1e-6) * dt
    u2, u3 = u * u, u * u * u
    return float((2 * u3 - 3 * u2 + 1) * vs[i] + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * vs[i + 1] + (u3 - u2) * m1)


def _cartella_tex(c):
    """La cartella delle immagini fatte al volo (tools/render/cache/pesci/tex/)."""
    import os
    d = os.path.join(c.P.CACHE, 'pesci', 'tex')
    os.makedirs(d, exist_ok=True)
    return d


def _proiezione(percorso, x0, x1, z0, z1):
    """Per _pittura: un'immagine proiettata di lato (lungo Y) sul riquadro x0..x1, z0..z1 del pesce; restituisce
    la funzione g → (colore, alfa dell'immagine)."""
    def colore(g):
        x, _, z = g.sep(g.texcoord('Object'))
        uv = g.comb(g.map_range(x, x0, x1, 0.0, 1.0), g.map_range(z, z0, z1, 0.0, 1.0), 0.0)
        return g.image(percorso, uv, extension='CLIP')
    return colore


def _occhio_umano(c, nome, centro, raggio, iride, look):
    """Un occhio umano messo a mano (per i lati dove la famiglia non arriva: il ventre della razza)."""
    mat = c.P.human_eye(f'Umano{nome}', iris=iride)
    c.obs.append(c.P.eyeball(nome, tuple(map(float, centro)), raggio, mat, look=tuple(map(float, look)), col=c.P.COL))


def _dente_umano(c, nome, centro, larghezza, altezza, spessore, lungo, su, mat, canino=False, res=None):
    """Un dente da persona: una scatola arrotondata con la faccia larga lungo `lungo` e l'altezza lungo `su`
    (incisivi, premolari, molari); canino=True: un cono dalla gengiva alla punta, che sta in centro − su·alt/2."""
    P = c.P
    c0 = np.asarray(centro, np.float32)
    R = _ruota(lungo, su)
    if canino:
        e2 = R[:, 1]
        f = P.sdf.round_cone(c0 + e2 * altezza * 0.5, c0 - e2 * altezza * 0.5, larghezza * 0.5, larghezza * 0.14)
    else:
        rr = min(larghezza, spessore) * 0.4
        f = P.sdf.rotate(P.sdf.box(c0, (larghezza / 2, altezza / 2, spessore / 2), rounding=rr), R, center=c0)
    m = max(larghezza, altezza, spessore) + 0.004
    if res is None:
        res = 0.0005 if c.fast else 0.00028
    c.obs.append(P.oggetto_sdf(nome, f, c0 - m, c0 + m, mat, res=res))


def _membrana_nera(c, nome='MembranaNera'):
    """Materiale di una pelle nera, tesa e lucida (sacche, bubboni): quasi nera, con le vene rosso cupo che si
    vedono appena e un poco di luce che passa (sss rossa)."""
    m, g = c.P.material(nome)
    co = g.texcoord('Object')
    vv = g.voronoi(co, scale=60.0, feature='DISTANCE_TO_EDGE')
    vene = g.smoothstep(0.035, 0.0, vv)
    n = g.noise(co, scale=90.0, detail=3.0)
    col = g.mix(g.mul(vene, 0.6), (0.008, 0.006, 0.007), (0.08, 0.01, 0.016))
    g.output_material(g.principled(color=col, rough=0.1, coat=1.0, coat_rough=0.02, spec=0.7, sss=0.1,
                                   sss_radius=(1.0, 0.15, 0.1), sss_scale=0.003,
                                   normal=g.bump(g.add(g.mul(n.fac, 0.5), vene), strength=0.18, distance=0.0008)))
    return m


def _dentro(c, profondo=0.0012, sfuma=0.002):
    """Peso per _pittura: le superfici scavate dentro il corpo (più in fondo di `profondo` sotto la pelle di
    prima): l'interno delle bocche e dei tagli fatti con il campo."""
    base = c.body.base()

    def f(p):
        return np.clip((-base(p) - profondo) / sfuma, 0, 1)
    return f


# ───────────────────────── le specie ─────────────────────────

# ── Sardonica (sardina, Sardina pilchardus) ──
# Il clupeide di sempre: fuso appena compresso, il ventre tondo carenato, la bocca piccola appena all'insù,
# l'occhio grande, una dorsale sola a metà sopra le pelviche, la coda molto forcuta; dorso blu-verde, fianchi
# d'argento, la fila di macchie scure sul fianco alto. «Il sorriso sardonico dei morti: le labbra tirate
# indietro, tutti i denti in vista. Le sardine non hanno denti»: le labbra tagliate a lente lungo la bocca
# fino alla guancia (campo), le gengive scoperte e una dentatura umana intera (extra).
_SORRISO = dict(x0=-0.014, x1=0.13, alto=0.0155, prof=0.008, sale=0.16)


def _sorriso_z(sh, x):
    """La linea di mezzo del sorriso: la bocca vera fino all'angolo, poi sale verso la guancia."""
    x = np.asarray(x, np.float32)
    zb = sh.mouth_z0 + (sh.mouth_z1 - sh.mouth_z0) * np.clip(x / sh.mouth_t, 0, 1)
    return zb + _SORRISO['sale'] * np.maximum(x - sh.mouth_t, 0)


def _sorriso_alto(x):
    """La mezza apertura del sorriso in x: una lente, larga in mezzo e chiusa agli angoli."""
    s = _SORRISO
    xm, hw = (s['x0'] + s['x1']) / 2, (s['x1'] - s['x0']) / 2
    return s['alto'] * np.clip(1 - ((np.asarray(x, np.float32) - xm) / hw) ** 2, 0, 1) ** 0.6


def _campo_sorriso(c, f):
    """Sardonica: il taglio a lente lungo la bocca che scopre le gengive (fino a prof sotto la pelle), con
    l'orlo delle labbra tirate appena rialzato."""
    sh, s = c.forma, _SORRISO

    def g(p):
        d = f(p)
        x, z = p[:, 0], p[:, 2]
        hh = _sorriso_alto(x)
        banda = np.abs(z - _sorriso_z(sh, x)) - hh
        out = c.P.sdf.smax(d, -np.maximum(banda, -(d + s['prof'])), 0.0015)
        vicino = np.clip(1 - np.abs(d) / 0.006, 0, 1) * np.clip(hh / 0.003, 0, 1)
        return out - 0.0013 * np.exp(-((banda - 0.0012) / 0.0016) ** 2) * vicino
    return g


def _denti_sardonica(c):
    """Sardonica: tutti i denti in vista, da persona: gli incisivi davanti, i canini, i premolari e i molari
    verso la guancia, sopra e sotto, sui due lati; le gengive scoperte (una pittura color carne)."""
    body, sh, s = c.body, c.forma, _SORRISO
    mat = c.P.materiale('DentiUmani', (0.84, 0.79, 0.66), rough=0.24, coat=0.7, sss=0.3)
    for i, x in enumerate(np.arange(0.0015, 0.122, 0.0079)):
        x = float(x)
        zm, hh = float(_sorriso_z(sh, x)), float(_sorriso_alto(x))
        if hh < 0.0045:
            continue
        if x < 0.017:
            lar, alt, canino = 0.0078, 0.0128, False        # incisivi
        elif x < 0.028:
            lar, alt, canino = 0.0074, 0.0134, True         # canini
        elif x < 0.06:
            lar, alt, canino = 0.0077, 0.011, False         # premolari
        else:
            lar, alt, canino = 0.0082, 0.0096, False        # molari
        alt = min(alt, hh * 0.92)
        ys = float(body.surface_y(x, zm))
        ys2 = float(body.surface_y(x + 0.002, float(_sorriso_z(sh, x + 0.002))))
        for lato in (-1, 1):
            # la faccia larga del dente segue l'arco della mascella nel piano xy
            lungo = np.array((0.002, lato * (ys2 - ys), 0.0), np.float32)
            y = lato * (ys - s['prof'] * 0.55)
            for su in (1, -1):                # 1: l'arcata di sopra (il dente scende), −1: quella di sotto
                centro = (x, y, zm + su * (alt / 2 + 0.0004))
                _dente_umano(c, f'DenteSardonica{i}_{lato}_{su}', centro, lar - 0.0004, alt, 0.0042, lungo,
                             (0.0, 0.0, float(su)), mat, canino=canino)
    # le gengive scoperte, dentro il taglio
    dentro = _dentro(c, 0.001, 0.002)

    def gengive(p):
        banda = np.abs(p[:, 2] - _sorriso_z(sh, p[:, 0])) - _sorriso_alto(p[:, 0])
        return dentro(p) * np.clip((0.003 - banda) / 0.002, 0, 1)
    _pittura(c, 'gengive', gengive, (0.42, 0.1, 0.11), ruvido=0.3)


SPECIE['sardonica'] = Specie(
    forma=Shape(
        top=[(0, -0.008), (0.02, 0.014), (0.06, 0.04), (0.12, 0.066), (0.2, 0.086), (0.32, 0.096), (0.45, 0.094), (0.6, 0.078),
             (0.75, 0.052), (0.88, 0.03), (1, 0.022)],
        bot=[(0, -0.02), (0.03, -0.04), (0.08, -0.062), (0.16, -0.085), (0.3, -0.1), (0.45, -0.1), (0.6, -0.082), (0.75, -0.054),
             (0.88, -0.03), (1, -0.022)],
        w=[(0, 0.006), (0.05, 0.026), (0.15, 0.042), (0.35, 0.046), (0.6, 0.036), (0.85, 0.018), (1, 0.011)],
        eye_t=0.095, eye_z=0.03, eye_r=0.026, mouth_t=0.065, mouth_z0=-0.016, mouth_z1=-0.03, gill_t=0.22,
        fins=[Fin('dorsal', 0.4, 0.52, [(0, 0), (0.12, 0.9), (0.35, 1.0), (0.75, 0.5), (1, 0.06)], 0.085, 14),
              Fin('anal', 0.8, 0.9, [(0, 0), (0.2, 0.6), (0.7, 0.4), (1, 0.06)], 0.035, 10),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.65, 0.24), 0.23, 20),
              Fin('pectoral', 0.22, 0.235, PETTORALE, 0.1, 10, z=-0.55),
              Fin('pelvic', 0.47, 0.485, PELVICA, 0.055, 6)]),
    aspetto=Look(back=(0.04, 0.14, 0.17), flank=(0.5, 0.56, 0.58), belly=(0.78, 0.79, 0.78), fin=(0.18, 0.2, 0.2),
                 iris=(0.75, 0.72, 0.6), iris_dark=(0.1, 0.1, 0.1), metal=0.75, irid=0.5, linea_laterale=0.0,
                 disegni=[Disegno('ventre', colore=(0.82, 0.84, 0.85), forza=0.6, v1=-0.25),
                          Disegno('sfumatura', colore=(0.42, 0.4, 0.2), forza=0.3, v0=0.15, v1=0.45, larghezza=0.1)]
                 + [Disegno('macchia', colore=(0.03, 0.05, 0.06), forza=0.85, u=u, v=0.42, r=0.0085) for u in (0.25, 0.31, 0.37, 0.43, 0.49)]),
    extra=_denti_sardonica, campo=_campo_sorriso,
    famiglia='corrupt', piano='fusiforme',
    opzioni=dict(occhi_extra=[(0.3, 0.08, 0.02), (0.56, -0.25, 0.024)], iridi=[IRIDE_CASTANA, IRIDE_AZZURRA],
                 escrescenza=None, colature=2))


# ── Ghiozzo Gozzuto (ghiozzo nero, Gobius niger) ──
# Testa grossa, larga e tonda, gli occhi alti e vicini che guardano in su (occhi sul dorso della testa), la
# bocca grande e obliqua; due dorsali (la prima di sei spine), l'anale lunga, le pelviche fuse a ventosa sotto
# il petto, le pettorali larghe e tonde, la coda tonda; bruno scuro a chiazze. «Sotto la gola una sacca nera e
# molle. Se la premi, dentro qualcosa si sposta»: la sacca che pende dalla gola, lucida, con le vene e una
# bozza sul fianco (extra), la gola annerita dove nasce.
def _sacca_ghiozzo(c):
    """Ghiozzo Gozzuto: la sacca nera e molle che pende dalla gola: il collo dentro la gola, il bulbo floscio
    che pende, una bozza sul fianco (qualcosa dentro che si sposta); la pelle della gola nera attorno."""
    P = c.P
    n3 = P.sdf.Noise3(41)
    zg = float(c.body.bot(np.array([0.15], np.float32))[0])
    a = np.array((0.125, 0.0, zg + 0.026), np.float32)            # il collo, dentro la gola
    b = np.array((0.15, -0.005, zg - 0.03), np.float32)
    bulbo = np.array((0.163, -0.008, zg - 0.066), np.float32)
    bozza = bulbo + np.array((0.016, -0.038, 0.008), np.float32)
    sacca = P.sdf.union(P.sdf.round_cone(a, b, 0.02, 0.03), P.sdf.ellipsoid(bulbo, (0.048, 0.042, 0.043)), k=0.02)
    bz = P.sdf.sphere(bozza, 0.012)

    def f(p):
        return P.sdf.smin(sacca(p), bz(p), 0.01) + 0.0028 * n3(p, scale=0.014, octaves=2)
    lo = np.array((0.05, -0.075, zg - 0.13), np.float32)
    hi = np.array((0.25, 0.075, zg + 0.05), np.float32)
    c.obs.append(P.oggetto_sdf('SaccaNera', f, lo, hi, _membrana_nera(c), res=0.0011 if c.fast else 0.0006))
    # la gola nera e lucida dove la sacca nasce
    _pittura(c, 'gola_nera', _vicino([(0.135, 0.0, zg)], 0.022, 0.02), (0.01, 0.008, 0.009), ruvido=0.08)


SPECIE['ghiozzo_gozzuto'] = Specie(
    forma=Shape(
        top=[(0, -0.014), (0.02, 0.01), (0.05, 0.038), (0.09, 0.058), (0.14, 0.07), (0.22, 0.074), (0.35, 0.07), (0.5, 0.062),
             (0.68, 0.05), (0.85, 0.04), (1, 0.034)],
        bot=[(0, -0.03), (0.03, -0.05), (0.08, -0.064), (0.16, -0.07), (0.3, -0.066), (0.5, -0.056), (0.7, -0.046), (0.88, -0.038),
             (1, -0.034)],
        w=[(0, 0.02), (0.04, 0.05), (0.1, 0.068), (0.17, 0.07), (0.3, 0.056), (0.5, 0.042), (0.75, 0.028), (1, 0.015)],
        eye_t=0.085, eye_z=0.044, eye_r=0.021, occhi=[(0.085, 0.044, 0.021, -1), (0.085, 0.044, 0.021, 1)],
        mouth_t=0.075, mouth_z0=-0.012, mouth_z1=-0.032, gill_t=0.22,
        fins=[Fin('dorsal', 0.3, 0.41, [(0, 0), (0.1, 0.85), (0.35, 1.0), (0.7, 0.85), (1, 0.1)], 0.075, 7, spiny=True),
              Fin('dorsal', 0.45, 0.8, [(0, 0), (0.05, 0.8), (0.5, 0.85), (0.9, 0.8), (1, 0.1)], 0.06, 16),
              Fin('anal', 0.52, 0.8, [(0, 0), (0.06, 0.8), (0.5, 0.8), (0.9, 0.75), (1, 0.1)], 0.05, 14),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.5, 1.0), 0.17, 16),
              Fin('pectoral', 0.23, 0.25, PETTORALE_TONDA, 0.12, 12, z=-0.2),
              # le pelviche fuse a ventosa, sotto il petto
              Fin('pelvic', 0.25, 0.26, [(0, 0.02), (0.4, 0.3), (0.85, 0.25), (1.0, 0.0), (0.85, -0.2), (0.4, -0.25), (0, -0.02)],
                  0.065, 10, z=-0.92, dir=(0.6, 0.15, -0.8), su=(1.0, 0.0, 0.3))]),
    aspetto=Look(back=(0.1, 0.075, 0.05), flank=(0.17, 0.13, 0.09), belly=(0.3, 0.25, 0.18), fin=(0.09, 0.07, 0.055),
                 iris=(0.75, 0.6, 0.3), iris_dark=(0.2, 0.12, 0.05), metal=0.08, irid=0.15, squame=0.8, linea_laterale=0.0,
                 disegni=[Disegno('macchie', colore=(0.03, 0.022, 0.016), forza=0.75, scala=24, r=0.35),
                          Disegno('punti', colore=(0.32, 0.26, 0.15), forza=0.4, scala=170, r=0.15)]),
    extra=_sacca_ghiozzo,
    famiglia='corrupt', piano='fusiforme',
    opzioni=dict(occhi_extra=[(0.42, 0.22, 0.019), (0.63, -0.05, 0.014)], iridi=[IRIDE_VERDE, IRIDE_CASTANA],
                 escrescenza=None, colature=1))


# ── Bavaccia (bavosa, Parablennius gattorugine) ──
# Allungata e senza squame, la testa tozza dal profilo ripido, i cirri ramificati sopra gli occhi
# (filamenti: un ciuffo per lato), le labbra grosse, la dorsale lunga continua (spinosa, poi molle e più
# alta), l'anale lunga, le pelviche piccole davanti alle pettorali, la coda tonda; bruno-arancio a bande.
# «Sbava melma nera senza fermarsi mai»: le labbra e il mento sporchi di pece lucida (pittura), le colate
# sulla gola e i bavoni che pendono dalla bocca (extra).
def _bava_bavaccia(c):
    """Bavaccia: le labbra e il mento sporchi di pece (una pittura lucida), tre colate che scendono sulla gola,
    i bavoni di pece che pendono dal labbro di sotto."""
    body, sh = c.body, c.forma

    def sporco(p):
        x, z = p[:, 0], p[:, 2]
        zl = body.mouth_line(x)
        labbra = np.clip(1 - (np.abs(z - zl) - 0.004) / 0.004, 0, 1) * np.clip((sh.mouth_t + 0.012 - x) / 0.008, 0, 1)
        col = np.zeros(len(p), np.float32)
        for xl, lung in ((0.012, 0.05), (0.03, 0.065), (0.05, 0.04)):
            col = np.maximum(col, np.exp(-((x - xl) / 0.0045) ** 2) * ((z < zl) & (z > zl - lung)))
        return np.maximum(labbra, col) * (p[:, 1] < 0.002)
    _pittura(c, 'bava', sporco, (0.006, 0.006, 0.008), ruvido=0.04)
    # il grumo di pece sul labbro di sotto e i bavoni grossi che ne pendono, tutti in un pezzo
    P = c.P
    parti = []
    for x, lung, r0, r1, dx in ((0.01, 0.115, 0.006, 0.01, -0.12), (0.028, 0.05, 0.0045, 0.0075, 0.08), (0.048, 0.078, 0.004, 0.0068, 0.22)):
        zl = float(body.mouth_line(np.array([x], np.float32))[0])
        a = np.array((x, -float(body.surface_y(x, zl - 0.006)) + 0.002, zl - 0.006), np.float32)
        parti.append(P.drip(a, lung, r0=r0, r1=r1, dir=(dx, -0.12, -1.0)))
        parti.append(P.sdf.ellipsoid(a + np.array((0.0, -0.002, 0.0), np.float32), (0.011, 0.0065, 0.0075)))
    zl0 = float(body.mouth_line(np.array([0.03], np.float32))[0])
    centro = np.array((0.03, 0.0, zl0 - 0.05), np.float32)
    c.obs.append(P.oggetto_sdf('BavaNera', P.sdf.union(*parti, k=0.006), centro - 0.08, centro + 0.08, P.tar_material(),
                               res=0.0009 if c.fast else 0.0005))


def _cirro(t, lung, dir, curva=(0.0, 0.0, 0.0), r=0.0026):
    """Un ramo del cirro sopra l'occhio della bavosa (Filamento sulla cresta dell'orbita)."""
    return Filamento(t=t, v=0.93, lunghezza=lung, raggio=r, dir=dir, curva=curva, punta=0.3)


SPECIE['bavaccia'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.015, 0.016), (0.04, 0.046), (0.08, 0.07), (0.13, 0.082), (0.22, 0.086), (0.4, 0.08), (0.6, 0.065),
             (0.8, 0.047), (0.95, 0.036), (1, 0.034)],
        bot=[(0, -0.03), (0.03, -0.052), (0.08, -0.066), (0.18, -0.074), (0.35, -0.07), (0.55, -0.06), (0.75, -0.046),
             (0.9, -0.037), (1, -0.034)],
        w=[(0, 0.016), (0.05, 0.038), (0.15, 0.046), (0.35, 0.042), (0.6, 0.032), (0.85, 0.02), (1, 0.013)],
        eye_t=0.072, eye_z=0.042, eye_r=0.02, mouth_t=0.055, mouth_z0=-0.018, mouth_z1=-0.024, gill_t=0.19,
        filamenti=[_cirro(0.07, 0.05, (0.1, 0.3, 1.0), (0, 0, -6), r=0.0045),
                   _cirro(0.066, 0.032, (-0.6, 0.3, 0.8), r=0.0032), _cirro(0.074, 0.034, (0.6, 0.35, 0.8), r=0.0032),
                   _cirro(0.07, 0.026, (0.0, 0.8, 0.6), r=0.003)],
        fins=[Fin('dorsal', 0.19, 0.55, [(0, 0), (0.03, 0.8), (0.2, 0.9), (0.5, 0.8), (0.85, 0.6), (1, 0.45)], 0.06, 24, spiny=True),
              Fin('dorsal', 0.55, 0.94, [(0, 0.45), (0.1, 0.95), (0.5, 1.0), (0.9, 0.85), (1, 0.1)], 0.064, 22),
              Fin('anal', 0.45, 0.92, [(0, 0), (0.05, 0.8), (0.5, 0.85), (0.9, 0.8), (1, 0.1)], 0.045, 24),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.4, 0.95), 0.15, 16),
              Fin('pectoral', 0.2, 0.22, PETTORALE_TONDA, 0.12, 12),
              Fin('pelvic', 0.15, 0.16, [(0, 0), (0.6, 0.12), (1.0, 0.05), (0.6, -0.05), (0, -0.04)], 0.05, 4)]),
    aspetto=Look(back=(0.2, 0.1, 0.05), flank=(0.34, 0.2, 0.1), belly=(0.55, 0.42, 0.28), fin=(0.26, 0.14, 0.07),
                 iris=(0.8, 0.5, 0.2), iris_dark=(0.3, 0.12, 0.03), metal=0.0, irid=0.08, squame=0.0, linea_laterale=0.0,
                 lucido=0.75,
                 disegni=[Disegno('bande', colore=(0.07, 0.035, 0.02), forza=0.7, n=7, u0=0.15, u1=0.98, larghezza=0.42, onda=0.08,
                                  inclinazione=-0.05),
                          Disegno('punti', colore=(0.08, 0.04, 0.02), forza=0.5, scala=170, r=0.15),
                          Disegno('macchie', colore=(0.6, 0.45, 0.25), forza=0.35, scala=50, r=0.15, seme=2)]),
    extra=_bava_bavaccia,
    famiglia='corrupt', piano='fusiforme',
    opzioni=dict(occhi_extra=[(0.3, 0.25, 0.019), (0.52, -0.1, 0.022), (0.72, 0.2, 0.014)],
                 iridi=[IRIDE_GRIGIA, IRIDE_VERDE, IRIDE_CASTANA], escrescenza=None, colature=2))


# ── Scorfano Pece (scorfano nero, Scorpaena porcus) ──
# Testa enorme coperta di spine e creste (Shape.spine), il lembo di pelle sopra l'occhio e qualche cirro
# (filamenti), la bocca grande e obliqua, la dorsale spinosa incisa fra una spina e l'altra, la molle più
# tonda, le pettorali larghe a ventaglio, la coda tonda; bruno marmorizzato. «Gli cola pece nera dalle spine»:
# ogni spina della dorsale ricoperta di pece lucida con la goccia in punta che cola; le spine della testa
# sporche e gocciolanti; le colate sul dorso (extra e pittura).
_MACCHIE_SCORFANO = (0.06, 0.035, 0.022)      # le pinne dello scorfano sono chiazzate di scuro
_DORSALE_SCORFANO = [(0, 0), (0.04, 0.9), (0.08, 0.5), (0.13, 1.0), (0.18, 0.55), (0.24, 1.0), (0.29, 0.55), (0.35, 0.95),
                     (0.4, 0.52), (0.46, 0.9), (0.51, 0.5), (0.57, 0.82), (0.62, 0.45), (0.68, 0.72), (0.73, 0.4), (0.8, 0.6),
                     (0.86, 0.35), (0.93, 0.45), (1, 0.25)]


def _pece_scorfano(c):
    """Scorfano Pece: la pece sulle spine della dorsale (un rivestimento lucido lungo ogni raggio che arriva a
    una punta), la goccia che cola da ogni punta, le gocce dalle spine della testa, le colate sul dorso."""
    P, body = c.P, c.body
    pinna = c.forma.fins[0]
    radici, punte, _ = P.fin_points(body, pinna, -1)
    radici, punte = np.array(radici), np.array(punte)
    out = pinna.outline
    picchi = [i for i in range(1, len(out) - 1) if out[i][1] > out[i - 1][1] and out[i][1] > out[i + 1][1]]
    segs, xs = [], []
    rng = np.random.default_rng(11)
    for k, i in enumerate(picchi):
        ea, eo = out[i]
        t = pinna.a + (pinna.b - pinna.a) * ea
        cima = np.array((t + eo * pinna.size * 0.35, 0.0, float(body.top(np.array([t], np.float32))[0]) + eo * pinna.size))
        j = int(np.argmin(np.linalg.norm(punte - cima, axis=1)))       # il raggio che arriva a quella punta
        segs.append(_catena([radici[j] - (0, 0, 0.003), punte[j]], (0.0032, 0.0021)))
        xs.append(float(radici[j][0]))
        _goccia(c, f'PeceSpina{k}', punte[j] + np.array((0.001, -0.0018, -0.002)), float(rng.uniform(0.024, 0.046)),
                r0=0.0024, r1=float(rng.uniform(0.0045, 0.0062)), dir=(0.12, -0.35, -1.0))
    _coni(c, 'PeceDorsale', segs, P.tar_material())
    # le spine della testa: le stesse di spine_campo (stessi semi), sul lato sinistro
    k = 0
    for sp in c.forma.spine:
        rng2 = np.random.default_rng(sp.seme)
        ts, vs = rng2.uniform(sp.t0, sp.t1, sp.n), rng2.uniform(sp.v0, sp.v1, sp.n)
        for t, v in list(zip(ts, vs))[::2]:
            p, nr = body.superficie(float(t), float(v), -1)
            av = np.array((1.0, 0.0, 0.0), np.float32) - nr * float(nr[0])
            av /= np.linalg.norm(av) + 1e-9
            d = nr * (1 - sp.inclinazione) + av * sp.inclinazione
            punta = p + d / np.linalg.norm(d) * sp.lunghezza
            _goccia(c, f'PeceTesta{k}', punta, float(rng.uniform(0.012, 0.028)), r0=0.002, r1=0.0042, dir=(0.1, -0.3, -1.0))
            k += 1
    # le colate sul dorso, sotto ogni spina, e la testa sporca attorno alle spine
    lungh = rng.uniform(0.25, 0.75, len(xs))

    def colate(p):
        v = body.norm_v(p)
        w = np.zeros(len(p), np.float32)
        for x0, fino in zip(xs, lungh):
            w = np.maximum(w, np.exp(-((p[:, 0] - x0 - 0.01 * (1 - v)) / 0.0035) ** 2) * np.clip((v - (1 - fino)) / 0.1, 0, 1))
        return w * (p[:, 1] < 0.001)
    _pittura(c, 'colate', colate, (0.006, 0.006, 0.008), ruvido=0.05)


SPECIE['scorfano_pece'] = Specie(
    forma=Shape(
        top=[(0, -0.025), (0.02, 0.01), (0.06, 0.055), (0.12, 0.095), (0.2, 0.122), (0.3, 0.132), (0.45, 0.122), (0.6, 0.096),
             (0.78, 0.064), (0.92, 0.047), (1, 0.044)],
        bot=[(0, -0.048), (0.03, -0.08), (0.1, -0.108), (0.22, -0.12), (0.38, -0.114), (0.55, -0.095), (0.72, -0.068),
             (0.88, -0.05), (1, -0.044)],
        w=[(0, 0.024), (0.05, 0.056), (0.15, 0.085), (0.3, 0.08), (0.55, 0.056), (0.8, 0.032), (1, 0.019)],
        eye_t=0.13, eye_z=0.07, eye_r=0.028, mouth_t=0.12, mouth_z0=-0.012, mouth_z1=-0.055, gill_t=0.34,
        spine=[Spine(0.05, 0.3, 0.35, 0.95, 18, lunghezza=0.012, raggio=0.0034, inclinazione=0.5, seme=7),
               Spine(0.2, 0.32, -0.5, 0.2, 6, lunghezza=0.015, raggio=0.0036, inclinazione=0.65, seme=8)],
        filamenti=[Filamento(t=0.125, v=0.97, lunghezza=0.042, raggio=0.0075, dir=(0.3, 0.2, 1.0), curva=(4, 0, 0), punta=0.45),
                   Filamento(t=0.07, v=0.75, lunghezza=0.012, raggio=0.0025, dir=(0.2, 0.5, 1.0)),
                   Filamento(t=0.24, v=0.6, lunghezza=0.013, raggio=0.0028, dir=(0.4, 0.6, 0.8))],
        # la dorsale spinosa intrisa di pece (la membrana quasi nera)
        fins=[Fin('dorsal', 0.3, 0.6, _DORSALE_SCORFANO, 0.11, 72, spiny=True, colore=(0.045, 0.032, 0.026)),
              Fin('dorsal', 0.61, 0.82, [(0, 0.25), (0.15, 0.8), (0.5, 0.95), (0.85, 0.7), (1, 0.05)], 0.085, 14, macchie=0.6,
                  colore_macchie=_MACCHIE_SCORFANO),
              Fin('anal', 0.62, 0.8, [(0, 0), (0.1, 0.9), (0.5, 0.95), (0.85, 0.7), (1, 0.05)], 0.075, 10, spiny=True, macchie=0.6,
                  colore_macchie=_MACCHIE_SCORFANO),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.45, 0.95), 0.17, 16, macchie=0.6, colore_macchie=_MACCHIE_SCORFANO),
              Fin('pectoral', 0.31, 0.33, [(0, 0.05), (0.4, 0.42), (0.85, 0.45), (1.0, 0.15), (0.9, -0.2), (0.5, -0.32), (0, -0.12)],
                  0.17, 16, z=-0.25, macchie=0.6, colore_macchie=_MACCHIE_SCORFANO),
              Fin('pelvic', 0.34, 0.35, PELVICA, 0.075, 6, spiny=True)]),
    aspetto=Look(back=(0.2, 0.11, 0.065), flank=(0.3, 0.19, 0.12), belly=(0.55, 0.42, 0.32), fin=(0.26, 0.15, 0.09),
                 iris=(0.7, 0.45, 0.2), iris_dark=(0.25, 0.1, 0.03), metal=0.05, irid=0.1, squame=0.5, linea_laterale=0.6,
                 lucido=0.5,
                 disegni=[Disegno('marmo', colore=(0.07, 0.04, 0.025), forza=0.75, scala=50, r=0.5),
                          Disegno('macchie', colore=(0.05, 0.03, 0.02), forza=0.6, scala=35, r=0.25, seme=3),
                          Disegno('punti', colore=(0.5, 0.35, 0.25), forza=0.4, scala=160, r=0.12)]),
    extra=_pece_scorfano,
    famiglia='corrupt', piano='fusiforme',
    opzioni=dict(occhi_extra=[(0.44, 0.25, 0.023), (0.6, -0.25, 0.018), (0.22, -0.28, 0.015)],
                 iridi=[IRIDE_NOCCIOLA, IRIDE_GRIGIA, IRIDE_VERDE], escrescenza=None, colature=2))


# ── Sciarrano Scrivano (sciarrano, Serranus scriba) ──
# Il serranide slanciato: muso a punta, bocca grande, la dorsale lunga (spinosa e poi molle), la coda tronca;
# bruno-rossiccio con le bande verticali scure, la macchia blu-viola sul ventre, i ghirigori sulla testa.
# «Le scritte si leggono: sono date. L'ultima è di stanotte»: sulla testa le date scritte a mano, a onde come
# i ghirigori (un'immagine fatta con PIL e dipinta sul fianco della testa): le tre notti della Night Splash,
# le altre dopo, e l'ultima, ancora fresca, rosso scuro.
_DATE_SCRIVANO = (('14·8·1997', 0.05, 0.46, 8), ('15·8·1997', 0.52, 0.72, -3), ('16·8·1997', 0.53, 0.585, -1),
                  ('3·11·2004', 0.53, 0.45, 1), ('21·6·2013', 0.5, 0.315, -2), ('10·10·2026', 0.42, 0.18, 3))
_TESTA_SCRIVANO = (0.015, 0.26, -0.075, 0.09)       # il riquadro della testa dove si scrive: x0, x1, z0, z1


def _date_sciarrano(c):
    """Sciarrano Scrivano: le date sulla testa. Ogni riga è scritta in corsivo e fatta ondeggiare colonna per
    colonna (la grafia dei ghirigori), un poco storta; l'inchiostro blu, l'ultima data rosso scuro."""
    import os
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    x0, x1, z0, z1 = _TESTA_SCRIVANO
    W = 1200
    H = int(W * (z1 - z0) / (x1 - x0))
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    font = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf', 104)
    for k, (testo, u, v, gradi) in enumerate(_DATE_SCRIVANO):
        col = (150, 12, 10) if k == len(_DATE_SCRIVANO) - 1 else (22, 40, 130)
        riga = Image.new('L', (int(font.getlength(testo)) + 44, 156), 0)
        ImageDraw.Draw(riga).text((22, 12), testo, font=font, fill=255, stroke_width=2, stroke_fill=255)
        a = np.asarray(riga, np.float32)
        onde = np.zeros_like(a)
        for x in range(a.shape[1]):
            onde[:, x] = np.roll(a[:, x], int(round(7 * math.sin(x / a.shape[1] * math.pi * 2.3 + k))))
        riga = Image.fromarray(onde.astype(np.uint8)).rotate(gradi, expand=True, resample=Image.BICUBIC)
        im.paste(Image.new('RGBA', riga.size, col + (255,)), (int(u * W), int((1 - v) * H - riga.size[1] / 2)), riga)
    im = im.filter(ImageFilter.GaussianBlur(1.0))
    percorso = os.path.join(_cartella_tex(c), 'date_sciarrano.png')
    im.save(percorso)

    def testa(p):
        return np.clip(-p[:, 1] / 0.004, 0, 1) * np.clip((x1 - p[:, 0]) / 0.01, 0, 1)
    _pittura(c, 'date', testa, _proiezione(percorso, x0, x1, z0, z1), ruvido=0.3)


SPECIE['sciarrano_scrivano'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.02, 0.01), (0.06, 0.04), (0.12, 0.07), (0.2, 0.09), (0.32, 0.1), (0.5, 0.095), (0.7, 0.07),
             (0.88, 0.045), (1, 0.04)],
        bot=[(0, -0.035), (0.03, -0.055), (0.1, -0.075), (0.25, -0.09), (0.45, -0.09), (0.65, -0.07), (0.85, -0.046), (1, -0.04)],
        w=[(0, 0.012), (0.06, 0.035), (0.2, 0.05), (0.45, 0.048), (0.7, 0.035), (1, 0.016)],
        eye_t=0.1, eye_z=0.035, eye_r=0.021, mouth_t=0.1, mouth_z0=-0.025, mouth_z1=-0.03, gill_t=0.26,
        fins=[Fin('dorsal', 0.28, 0.6, [(0, 0), (0.05, 0.85), (0.12, 0.6), (0.2, 0.95), (0.3, 0.7), (0.45, 0.85), (0.6, 0.65),
                                       (0.75, 0.75), (0.9, 0.6), (1, 0.55)], 0.075, 30, spiny=True),
              Fin('dorsal', 0.6, 0.84, [(0, 0.55), (0.15, 0.95), (0.5, 1.0), (0.85, 0.8), (1, 0.05)], 0.085, 14),
              Fin('anal', 0.62, 0.8, [(0, 0), (0.12, 0.9), (0.5, 0.95), (0.85, 0.7), (1, 0.05)], 0.07, 10),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.5, 0.06, 0.85), 0.2, 18),
              Fin('pectoral', 0.27, 0.285, PETTORALE_TONDA, 0.12, 12),
              Fin('pelvic', 0.3, 0.315, PELVICA, 0.07, 6)]),
    aspetto=Look(back=(0.3, 0.16, 0.1), flank=(0.55, 0.36, 0.24), belly=(0.78, 0.68, 0.55), fin=(0.6, 0.35, 0.18),
                 iris=(0.8, 0.6, 0.25), iris_dark=(0.3, 0.15, 0.04), metal=0.15, irid=0.2, squame=0.8,
                 disegni=[Disegno('bande', colore=(0.1, 0.05, 0.04), forza=0.75, n=6, u0=0.26, u1=0.96, larghezza=0.4, onda=0.06),
                          Disegno('macchia', colore=(0.16, 0.12, 0.42), forza=0.85, u=0.42, v=-0.6, r=0.04, allungamento=0.6),
                          Disegno('vermi', colore=(0.14, 0.22, 0.5), forza=0.25, scala=60, u1=0.1)]),
    extra=_date_sciarrano,
    famiglia='corrupt', piano='fusiforme',
    opzioni=dict(occhi_extra=[(0.4, 0.2, 0.02), (0.62, -0.15, 0.016)], iridi=[IRIDE_AZZURRA, IRIDE_NOCCIOLA],
                 escrescenza=None, colature=2))


# ── Gallincubo (gallinella, Chelidonichthys lucerna) ──
# Testa grossa e corazzata: il profilo dal muso alla nuca è una rampa dritta e ripida, gli occhi alti sotto il
# bordo osseo, la bocca bassa; le placche della testa (disegno 'reticolo' solo sulla testa) e le spinette.
# Le pettorali enormi a ventaglio (verdi, puntinate di blu, il bordo blu). «Le pinne davanti sono diventate
# dita… di notte bussa»: al posto dei tre raggi liberi (Fin.liberi) tre dita umane per lato, che camminano
# sulla punta (extra); tre occhi umani sul fianco, sopra la pettorale.
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
    """Gallincubo: tre dita umane per lato sotto la pettorale, dove la gallinella ha i raggi liberi: tre
    falangi (giù e in fuori, poi avanti, poi giù sulla punta), le nocche gonfie e grinzose, l'unghia sporca
    sul dorso dell'ultima falange."""
    P, body = c.P, c.body
    pinna = next(f for f in c.forma.fins if f.kind == 'pectoral')
    pelle = _pelle_dita(c)
    unghia = P.materiale('Unghia', (0.7, 0.62, 0.5), rough=0.22, coat=0.8, sss=0.15)
    for s in (-1, 1):
        for i in range(3):
            base, nr = body.superficie(pinna.a - 0.012 - 0.03 * i, -0.74, s)
            k = 1.0 - 0.08 * i                         # le dita dietro un poco più corte
            ap = 0.39 - 0.42 * i                       # a ventaglio: quella dietro punta indietro, quella davanti avanti
            dirs = [(ap, 0.9, -1.0), (ap - 0.55, 0.35, -0.6), (ap * 0.3 - 0.12, 0.15, -1.0)]
            lung = [0.066 * k, 0.048 * k, 0.036 * k]
            rag = [0.0098, 0.009, 0.0082, 0.0067]
            pts = [base - nr * 0.007]
            for d, L in zip(dirs, lung):
                d = np.array((d[0], s * d[1], d[2]), np.float32)
                pts.append(pts[-1] + d / np.linalg.norm(d) * L)
            nocche = [(pts[j], pts[j + 1] - pts[j - 1]) for j in (1, 2)]
            parti = [P.sdf.round_cone(pts[j], pts[j + 1], rag[j], rag[j + 1]) for j in range(3)]
            parti += [P.sdf.sphere(q, rag[1] * 1.12) for q, _ in nocche]     # le nocche gonfie
            dito = P.sdf.union(*parti, k=0.005)

            def grinze(p, nocche=nocche):
                # le pieghe di traverso sulle nocche
                out = np.zeros(len(p), np.float32)
                for q, ax in nocche:
                    ax = ax / np.linalg.norm(ax)
                    h = (p - q) @ ax
                    vic = np.clip(1 - np.linalg.norm(p - q, axis=1) / 0.016, 0, 1)
                    out += vic * (np.exp(-((h - 0.003) / 0.001) ** 2) + np.exp(-((h + 0.0005) / 0.001) ** 2)
                                  + np.exp(-((h + 0.004) / 0.001) ** 2))
                return out

            def f(p, dito=dito, grinze=grinze):
                return dito(p) + 0.0007 * grinze(p)

            def nocca(p, grinze=grinze):
                return np.clip(grinze(p) * 0.6, 0, 1)
            Q = np.array(pts)
            c.obs.append(P.oggetto_sdf(f'Dito{s}_{i}', f, Q.min(0) - 0.016, Q.max(0) + 0.016, pelle,
                                       res=0.0008 if c.fast else 0.0004, attrs={'nocca': nocca}))
            # l'unghia sul dorso dell'ultima falange (il lato davanti e in fuori della curva)
            d3 = pts[3] - pts[2]
            d3 = d3 / np.linalg.norm(d3)
            fuori = np.array((-0.45, s * 1.0, 0.3), np.float32)
            fuori -= d3 * float(fuori @ d3)
            fuori /= np.linalg.norm(fuori)
            cu = pts[3] - d3 * 0.0095 + fuori * rag[3] * 0.75
            fu = _ellissoide(c, cu, (0.0085, 0.0018, 0.0066), _ruota(d3, fuori))
            c.obs.append(P.oggetto_sdf(f'Unghia{s}_{i}', fu, cu - 0.014, cu + 0.014, unghia, res=0.0005 if c.fast else 0.0003))


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


# ── Mostrella (mostella, Phycis phycis) ──
# Allungata, la testa media con la bocca grande e l'occhio grande, la prima dorsale corta e alta, la seconda
# e l'anale lunghissime fino alla coda tonda (scure, orlate di chiaro), le pelviche ridotte a due filamenti
# lunghi e biforcuti che arrivano a metà corpo (la «forkbeard»); bruno-rossiccia. «Al posto della barbetta
# un ciuffo di filamenti neri che si muovono da soli»: sotto il mento, invece del barbiglio, un ciuffo di
# filamenti di pece lucida, ognuno storto a modo suo (extra).
def _barba_mostrella(c):
    """Mostrella: il ciuffo di filamenti neri sotto il mento, ognuno con la sua onda (si muovono da soli)."""
    body = c.body
    rng = np.random.default_rng(13)
    segs = []
    for _ in range(36):
        p, _ = body.superficie(float(rng.uniform(0.025, 0.09)), -1.0, 0)
        a = p + np.array((0.0, float(rng.uniform(-0.009, 0.009)), 0.003), np.float32)
        d = np.array((rng.uniform(-0.7, 0.6), rng.uniform(-0.75, 0.75), -1.0), np.float32)
        asse = np.cross(d, rng.normal(size=3).astype(np.float32))
        if np.linalg.norm(asse) < 1e-3:
            asse = np.array((0.0, 1.0, 0.0), np.float32)
        pts = _percorso(a, d, float(rng.uniform(0.05, 0.13)), n=16, curva=(float(rng.uniform(-3, 3)), 0.0, float(rng.uniform(0, 4))),
                        onda=float(rng.uniform(0.35, 0.85)), giri=float(rng.uniform(1.5, 3.5)), fase=float(rng.uniform(0, 6.28)),
                        piano=asse)
        segs.append(_catena(pts, (0.0034, 0.0008)))
    _coni(c, 'BarbaNera', segs, c.P.tar_material())


_ORLO_MOSTELLA = (0.72, 0.7, 0.66)
SPECIE['mostrella'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.02, 0.01), (0.06, 0.038), (0.12, 0.062), (0.2, 0.078), (0.32, 0.084), (0.5, 0.078), (0.7, 0.058),
             (0.88, 0.035), (1, 0.026)],
        bot=[(0, -0.03), (0.03, -0.048), (0.1, -0.066), (0.25, -0.078), (0.45, -0.074), (0.65, -0.058), (0.85, -0.036), (1, -0.026)],
        w=[(0, 0.012), (0.06, 0.036), (0.2, 0.048), (0.45, 0.042), (0.7, 0.028), (1, 0.011)],
        eye_t=0.095, eye_z=0.024, eye_r=0.022, mouth_t=0.09, mouth_z0=-0.016, mouth_z1=-0.026, gill_t=0.23,
        # le pelviche: due filamenti lunghi per lato, che si biforcano
        filamenti=[Filamento(t=0.19, v=-0.9, lunghezza=0.2, raggio=0.0026, dir=(0.8, 0.25, -0.55), curva=(0, 0, 1.6), punta=0.35),
                   Filamento(t=0.192, v=-0.92, lunghezza=0.16, raggio=0.0022, dir=(0.85, 0.15, -0.5), curva=(0, 0, 2.2), punta=0.35)],
        fins=[Fin('dorsal', 0.24, 0.32, [(0, 0), (0.1, 0.85), (0.3, 1.0), (0.7, 0.7), (1, 0.08)], 0.075, 9),
              Fin('dorsal', 0.34, 0.97, [(0, 0), (0.02, 0.6), (0.1, 0.75), (0.5, 0.8), (0.9, 0.75), (1, 0.2)], 0.05, 50,
                  bordo=_ORLO_MOSTELLA),
              Fin('anal', 0.42, 0.96, [(0, 0), (0.03, 0.6), (0.1, 0.75), (0.5, 0.8), (0.9, 0.7), (1, 0.2)], 0.045, 44,
                  bordo=_ORLO_MOSTELLA),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.3, 0.95), 0.14, 16, bordo=_ORLO_MOSTELLA),
              Fin('pectoral', 0.24, 0.255, PETTORALE_TONDA, 0.1, 11)]),
    aspetto=Look(back=(0.22, 0.11, 0.07), flank=(0.34, 0.2, 0.13), belly=(0.58, 0.48, 0.4), fin=(0.12, 0.07, 0.05),
                 iris=(0.75, 0.6, 0.35), iris_dark=(0.2, 0.12, 0.05), metal=0.15, irid=0.2, squame=0.9, linea_laterale=0.7),
    extra=_barba_mostrella,
    famiglia='corrupt', piano='fusiforme',
    opzioni=dict(occhi_extra=[(0.37, 0.3, 0.02), (0.58, -0.1, 0.017)], iridi=[IRIDE_CASTANA, IRIDE_GRIGIA],
                 escrescenza=None, colature=2))


# ── Mormorìa (mormora, Lithognathus mormyrus) ──
# Lo sparide allungato con il muso lungo e appuntito, le labbra grosse e la bocca bassa, la dorsale lunga, la
# coda forcuta; argento con 14 bande verticali scure e sottili. «Dalle branchie un brusio, come un parco
# pieno di gente lontano»: l'opercolo socchiuso, la fessura che si apre a mezzaluna (campo), e dentro tante
# boccucce di carne, una sopra l'altra, che mormorano (extra), il fondo rosso cupo (pittura).
def _bordo_opercolo(sh, v):
    """La x del bordo dell'opercolo alla quota v (lo stesso arco del solco di Body.field)."""
    return sh.gill_t - 0.035 * v * v


def _campo_mormora(c, f):
    """Mormorìa: dietro il bordo dell'opercolo, sul fianco sinistro, la fessura aperta a mezzaluna (fino a
    0.016 sotto la pelle) e il lembo dell'opercolo appena sollevato."""
    sh, body = c.forma, c.body

    def g(p):
        d = f(p)
        x = p[:, 0]
        zc, h, _ = body.section(np.clip(x, 0, 1))
        v = (p[:, 2] - zc) / h
        xa = _bordo_opercolo(sh, v)
        fessura = np.maximum(np.maximum(x - (xa + 0.006), (xa - 0.036) - x), (np.abs(v) - 0.74) * h)
        out = c.P.sdf.smax(d, -np.maximum(np.maximum(fessura, -(d + 0.018)), p[:, 1]), 0.002)
        # il lembo dell'opercolo, davanti alla fessura, che si alza
        lembo = (np.clip(1 - np.abs(x - (xa - 0.056)) / 0.022, 0, 1) * np.clip((0.8 - np.abs(v)) / 0.08, 0, 1)
                 * np.clip(1 - np.abs(d) / 0.008, 0, 1) * (p[:, 1] < 0))
        return out - 0.003 * lembo
    return g


def _boccucce_mormora(c):
    """Mormorìa: le boccucce nella fessura dell'opercolo: due labbra di carne per bocca, socchiuse, una sopra
    l'altra lungo la mezzaluna; il fondo della fessura rosso cupo."""
    P, body, sh = c.P, c.body, c.forma
    labbra = P.flesh_material('LabbraMormora', (0.66, 0.3, 0.3))
    for k, v in enumerate(np.linspace(-0.54, 0.54, 5)):
        v = float(v)
        xa = float(_bordo_opercolo(sh, v)) - 0.015
        zc, h, _ = (float(a[0]) for a in body.section(np.array([xa], np.float32)))
        z = zc + h * v
        q = np.array((xa, -float(body.surface_y(xa, z)) + 0.0135, z), np.float32)
        L, ap = 0.0098 - 0.0015 * abs(v), 0.0025 + 0.0013 * (k % 2)
        parti = []
        for su, r in ((1, 0.0029), (-1, 0.0035)):
            a = q + np.array((-L, 0.0, su * ap), np.float32)
            b = q + np.array((L, 0.0, su * ap), np.float32)
            mezzo = q + np.array((0.0, -0.0012, su * (ap + 0.0008)), np.float32)
            parti += [P.sdf.round_cone(a, mezzo, r * 0.7, r), P.sdf.round_cone(mezzo, b, r, r * 0.7)]
        bocca = P.sdf.union(*parti, k=0.002)
        c.obs.append(P.oggetto_sdf(f'Boccuccia{k}', bocca, q - 0.018, q + 0.018, labbra, res=0.0005 if c.fast else 0.0003))
    # il fondo della fessura, rosso cupo
    dentro = _dentro(c, 0.003, 0.003)

    def fondo(p):
        zc, h, _ = body.section(np.clip(p[:, 0], 0, 1))
        v = (p[:, 2] - zc) / h
        xa = _bordo_opercolo(sh, v)
        return dentro(p) * (p[:, 0] > xa - 0.045) * (p[:, 0] < xa + 0.01) * (p[:, 1] < 0)
    _pittura(c, 'fessura', fondo, (0.045, 0.006, 0.01), ruvido=0.3)


SPECIE['mormoria'] = Specie(
    forma=Shape(
        top=[(0, -0.03), (0.02, -0.012), (0.06, 0.02), (0.12, 0.055), (0.2, 0.082), (0.32, 0.095), (0.5, 0.09), (0.7, 0.065),
             (0.88, 0.04), (1, 0.034)],
        bot=[(0, -0.04), (0.03, -0.055), (0.1, -0.07), (0.25, -0.085), (0.45, -0.085), (0.65, -0.066), (0.85, -0.042), (1, -0.034)],
        w=[(0, 0.01), (0.06, 0.03), (0.2, 0.046), (0.45, 0.045), (0.7, 0.03), (1, 0.014)],
        eye_t=0.14, eye_z=0.035, eye_r=0.02, mouth_t=0.06, mouth_z0=-0.035, mouth_z1=-0.043, gill_t=0.27,
        fins=[Fin('dorsal', 0.3, 0.58, [(0, 0), (0.06, 0.9), (0.25, 1.0), (0.6, 0.8), (1, 0.6)], 0.075, 24, spiny=True),
              Fin('dorsal', 0.58, 0.82, [(0, 0.6), (0.2, 0.8), (0.6, 0.7), (1, 0.05)], 0.07, 14),
              Fin('anal', 0.62, 0.82, [(0, 0), (0.12, 0.9), (0.6, 0.62), (1, 0.05)], 0.06, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.3), 0.24, 20),
              Fin('pectoral', 0.29, 0.305, PETTORALE, 0.15, 11),
              Fin('pelvic', 0.33, 0.345, PELVICA, 0.07, 6, spiny=True)]),
    aspetto=Look(back=(0.3, 0.32, 0.33), flank=(0.58, 0.6, 0.6), belly=(0.75, 0.75, 0.73), fin=(0.3, 0.3, 0.28),
                 iris=(0.7, 0.68, 0.55), iris_dark=(0.12, 0.12, 0.1), metal=0.6, irid=0.3, squame=0.8,
                 disegni=[Disegno('bande', colore=(0.07, 0.07, 0.08), forza=0.75, n=14, u0=0.14, u1=0.95, larghezza=0.28)]),
    extra=_boccucce_mormora, campo=_campo_mormora,
    famiglia='corrupt', piano='fusiforme',
    opzioni=dict(occhi_extra=[(0.48, 0.3, 0.02), (0.66, -0.2, 0.016)], iridi=[IRIDE_VERDE, IRIDE_CASTANA],
                 escrescenza=None, colature=2))


# ── Luciferna (pesce prete, Uranoscopus scaber) ──
# La testa grande e squadrata, piatta sopra e larga, coperta di placche; gli occhi in cima, che guardano in
# su; la bocca quasi verticale, all'insù, con le frange sulle labbra; la spina dietro l'opercolo, la prima
# dorsale piccola e nera, la seconda e l'anale lunghe, le pettorali larghe a ventaglio; grigio-bruno con i
# puntini chiari. «Gli occhi rivolti in su… questo ne ha una fila intera, tutti rivolti verso la barca»: una
# fila di occhi umani lungo il dorso, che guardano la camera (la famiglia); il ritratto gira il dorso verso
# la camera.
def _frange_luciferna(c):
    """Luciferna: le frange sulle labbra della bocca verticale (cirri corti, sopra e sotto il taglio)."""
    body, sh = c.body, c.forma
    segs = []
    for x in np.linspace(0.004, sh.mouth_t - 0.003, 6):
        zl = float(body.mouth_line(np.array([x], np.float32))[0])
        for s in (-1, 1):
            for dz, su in ((0.003, 1), (-0.003, -1)):
                a = np.array((x, s * float(body.surface_y(x, zl + dz)), zl + dz), np.float32)
                segs.append(_catena(_percorso(a, (-0.7, s * 0.6, su * 0.4), 0.009, n=4), (0.0014, 0.0005)))
    _coni(c, 'FrangeLabbra', segs, c.P.fish_skin('PelleFrange', c.aspetto))


SPECIE['luciferna'] = Specie(
    forma=Shape(
        top=[(0, 0.038), (0.015, 0.058), (0.04, 0.072), (0.1, 0.08), (0.18, 0.082), (0.26, 0.078), (0.38, 0.066), (0.55, 0.05),
             (0.75, 0.035), (1, 0.026)],
        bot=[(0, -0.024), (0.02, -0.058), (0.06, -0.085), (0.14, -0.098), (0.24, -0.096), (0.36, -0.082), (0.55, -0.06),
             (0.75, -0.04), (1, -0.026)],
        w=[(0, 0.034), (0.03, 0.065), (0.1, 0.085), (0.2, 0.085), (0.32, 0.068), (0.5, 0.048), (0.75, 0.028), (1, 0.014)],
        eye_t=0.1, eye_z=0.075, eye_r=0.018, occhi=[(0.1, 0.075, 0.018, -1), (0.1, 0.075, 0.018, 1)],
        mouth_t=0.04, mouth_z0=0.036, mouth_z1=-0.014, gill_t=0.28,
        spine=[Spine(0.25, 0.25, 0.1, 0.1, 1, lunghezza=0.035, raggio=0.0045, inclinazione=0.85, fila=True, seme=1)],
        fins=[Fin('dorsal', 0.33, 0.4, [(0, 0), (0.15, 0.9), (0.5, 1.0), (0.85, 0.6), (1, 0.05)], 0.045, 6, spiny=True,
                  colore=(0.02, 0.02, 0.02)),
              Fin('dorsal', 0.43, 0.84, [(0, 0), (0.04, 0.8), (0.4, 0.9), (0.85, 0.85), (1, 0.1)], 0.055, 22),
              Fin('anal', 0.45, 0.84, [(0, 0), (0.04, 0.75), (0.4, 0.85), (0.85, 0.8), (1, 0.1)], 0.05, 22),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.55, 0.06, 0.85), 0.17, 16),
              Fin('pectoral', 0.27, 0.3, [(0, 0.05), (0.45, 0.42), (0.9, 0.38), (1.0, 0.1), (0.85, -0.2), (0.4, -0.28), (0, -0.1)],
                  0.16, 16, z=-0.25, dir=(0.6, 0.65, -0.25)),
              Fin('pelvic', 0.12, 0.13, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.17, 0.14, 0.1), flank=(0.3, 0.26, 0.2), belly=(0.72, 0.7, 0.66), fin=(0.2, 0.17, 0.13),
                 iris=(0.7, 0.62, 0.4), iris_dark=(0.15, 0.12, 0.06), metal=0.1, irid=0.1, squame=0.4, linea_laterale=0.0,
                 disegni=[Disegno('marmo', colore=(0.08, 0.065, 0.045), forza=0.5, scala=40, r=0.4),
                          Disegno('punti', colore=(0.62, 0.6, 0.55), forza=0.6, scala=110, r=0.18, v0=0.0),
                          Disegno('reticolo', colore=(0.07, 0.06, 0.045), forza=0.6, scala=45, larghezza=0.1, u1=0.26, v0=-0.3)]),
    extra=_frange_luciferna,
    famiglia='corrupt', piano='fusiforme', ritratto=Ritratto(yaw=12.0, pitch=-4.0, roll=24.0),
    opzioni=dict(occhi_extra=[(0.2, 0.84, 0.014), (0.29, 0.86, 0.016), (0.38, 0.87, 0.017), (0.47, 0.87, 0.016),
                              (0.56, 0.86, 0.015), (0.65, 0.84, 0.013), (0.74, 0.82, 0.011)],
                 iridi=[IRIDE_CASTANA, IRIDE_AZZURRA, IRIDE_VERDE, IRIDE_GRIGIA, IRIDE_NOCCIOLA, IRIDE_AZZURRA, IRIDE_CASTANA],
                 escrescenza=None, colature=0))


# ── Bocchenere (squalo boccanera, Galeus melastomus) ──
# Il piccolo squalo slanciato: il muso lungo e appuntito, gli occhi grandi e allungati da gatto, le due
# dorsali arretrate, l'anale con la base lunghissima, la coda bassa e lunga; grigio-bruno con le selle scure
# orlate di chiaro sul dorso; dentro la bocca è nero. «Una bocca nera, poi un'altra sul fianco, poi
# un'altra ancora»: due bocche in più sul fianco, tagli a mezzaluna nel corpo (campo) con il dentro nero e
# lucido (pittura), le file di denti piccoli e la bava di pece che cola dal labbro (extra).
_BOCCHE_NERE = ((0.33, 0.12, 0.045, 0.012), (0.58, 0.02, 0.038, 0.0105))   # (t, v, mezza larghezza, mezza apertura)


def _bocche_geometria(c):
    """Le bocche del fianco nelle coordinate del pesce: (x, z del centro, mezza larghezza, mezza apertura)."""
    out = []
    for t, v, W, H in _BOCCHE_NERE:
        zc, h, _ = (float(a[0]) for a in c.body.section(np.array([t], np.float32)))
        out.append((t, zc + h * v, W, H))
    return out


def _bocca_lente(p, xc, zc, W, H):
    """Distanza (in z) dalla lente della bocca: negativa dentro; la linea di mezzo scende agli angoli."""
    dx = (p[:, 0] - xc) / W
    zm = zc - 0.45 * H * dx * dx
    hh = H * np.clip(1 - dx * dx, 0, 1) ** 0.7
    return np.abs(p[:, 2] - zm) - hh, hh


def _campo_bocchenere(c, f):
    """Bocchenere: le bocche sul fianco sinistro, scavate a lente fino a 0.014 sotto la pelle, con le labbra."""
    bocche = _bocche_geometria(c)

    def g(p):
        d = f(p)
        out = d
        vicino = np.clip(1 - np.abs(d) / 0.006, 0, 1) * (p[:, 1] < 0)
        for xc, zc, W, H in bocche:
            lente, hh = _bocca_lente(p, xc, zc, W, H)
            out = c.P.sdf.smax(out, -np.maximum(np.maximum(lente, -(d + 0.014)), p[:, 1]), 0.002)
            out = out - 0.0016 * np.exp(-((lente - 0.0012) / 0.0018) ** 2) * np.clip(hh / 0.003, 0, 1) * vicino
        return out
    return g


def _denti_bocchenere(c):
    """Bocchenere: le file di denti piccoli e aguzzi sulle due labbra di ogni bocca del fianco, il dentro nero
    e lucido, la bava di pece che pende dal labbro di sotto."""
    P, body = c.P, c.body
    bocche = _bocche_geometria(c)
    A, B, R1, R2 = [], [], [], []
    for xc, zc, W, H in bocche:
        for k in range(13):
            dx = -0.84 + 1.68 * k / 12
            x = xc + dx * W
            zm, hh = zc - 0.45 * H * dx * dx, H * (1 - dx * dx) ** 0.7
            for su in (1, -1):
                z = zm + su * (hh + 0.0004)
                base = np.array((x, -float(body.surface_y(x, z)) + 0.0028, z), np.float32)
                A.append(base)
                B.append(base + np.array((0.0004 * dx, -0.0016, -su * min(0.0072, hh * 1.1)), np.float32))
                R1.append(0.002)
                R2.append(0.0003)
    f, lo, hi = P.campo_coni(A, B, R1, R2)
    c.obs.append(P.oggetto_sdf('DentiBocchenere', f, lo, hi, P.dirty_teeth_material(), res=0.0006 if c.fast else 0.00035))
    dentro = _dentro(c, 0.0012, 0.002)

    def nero(p):
        w = np.zeros(len(p), np.float32)
        for xc, zc, W, H in bocche:
            lente, _ = _bocca_lente(p, xc, zc, W, H)
            w = np.maximum(w, np.clip((0.004 - lente) / 0.003, 0, 1))
        return w * dentro(p) * (p[:, 1] < 0)
    _pittura(c, 'bocche_nere', nero, (0.005, 0.005, 0.006), ruvido=0.12)
    for k, (xc, zc, W, H) in enumerate(bocche):
        z = zc - H - 0.002
        _goccia(c, f'BavaBocca{k}', (xc + 0.004, -float(body.surface_y(xc, z)) + 0.001, z), 0.028 + 0.01 * k,
                r0=0.002, r1=0.0042, dir=(0.05, -0.15, -1.0))


SPECIE['bocchenere'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.02, 0.008), (0.06, 0.02), (0.12, 0.032), (0.22, 0.044), (0.36, 0.05), (0.5, 0.046), (0.65, 0.036),
             (0.8, 0.026), (0.92, 0.018), (1, 0.014)],
        bot=[(0, -0.008), (0.03, -0.016), (0.08, -0.026), (0.18, -0.038), (0.32, -0.046), (0.46, -0.044), (0.6, -0.036),
             (0.75, -0.026), (0.9, -0.017), (1, -0.014)],
        w=[(0, 0.004), (0.04, 0.016), (0.12, 0.03), (0.3, 0.04), (0.5, 0.035), (0.7, 0.025), (0.9, 0.014), (1, 0.01)],
        eye_t=0.075, eye_z=0.008, eye_r=0.012, eye_allungato=1.6,
        bocca='ventrale', mouth_a=0.07, mouth_t=0.11, mouth_z1=-0.022, mouth_z0=-0.022,
        branchie='fessure', gill_t=0.15, n_branchie=5, passo_branchie=0.013,
        fins=[Fin('dorsal', 0.5, 0.57, DORSALE_SQUALO, 0.045, 24, carnosa=True, spessore=0.004),
              Fin('dorsal', 0.7, 0.76, DORSALE_SQUALO, 0.04, 20, carnosa=True, spessore=0.0035),
              Fin('anal', 0.52, 0.72, [(0, 0), (0.15, 0.7), (0.4, 1.0), (0.8, 0.8), (1, 0.1)], 0.03, 30, carnosa=True,
                  spessore=0.0035),
              Fin('caudal', 1.0, 1.0, coda_eterocerca(lobo=1.0, alzata=0.8, lobo_basso=0.5, basso=0.9), 0.28, 50,
                  carnosa=True, spessore=0.005),
              Fin('pectoral', 0.17, 0.21, [(0, 0.06), (0.5, 0.06), (1.0, -0.05), (0.85, -0.12), (0.4, -0.15), (0, -0.11)], 0.13, 24,
                  carnosa=True, spessore=0.004, dir=(0.75, 0.3, -0.6)),
              Fin('pelvic', 0.4, 0.46, [(0, 0.05), (0.6, 0.06), (1.0, -0.02), (0.6, -0.12), (0, -0.1)], 0.05, 20,
                  carnosa=True, spessore=0.0035)]),
    aspetto=Look(back=(0.1, 0.085, 0.07), flank=(0.16, 0.14, 0.12), belly=(0.55, 0.52, 0.5), fin=(0.1, 0.09, 0.075),
                 iris=(0.55, 0.62, 0.45), iris_dark=(0.06, 0.08, 0.05), pupilla='slit_v', metal=0.1, irid=0.15, squame=0.0,
                 linea_laterale=0.0, lucido=0.35, ruvido=0.45, tinta_pinne=0.6,
                 disegni=[Disegno('macchie', colore=(0.012, 0.01, 0.009), colore2=(0.26, 0.24, 0.21), forza=0.9, scala=16, r=0.42,
                                  v0=0.12)]),
    extra=_denti_bocchenere, campo=_campo_bocchenere,
    famiglia='corrupt', piano='squalo',
    opzioni=dict(occhi_extra=[(0.45, 0.5, 0.011)], iridi=[IRIDE_GRIGIA], escrescenza=None, colature=1))


# ── Pesce Bubbone (pesce palla argenteo, Lagocephalus sceleratus) ──
# Gonfio: la testa e la pancia sono una palla, la coda resta stretta. Le spinette sulla pancia sono
# Shape.spine (coni fusi nella pelle); il becco a quattro denti è un extra. «Si gonfiano anche le bolle nere
# che ha sulla pelle»: al posto delle macchie, pustole nere in rilievo, tese e lucide, con il livido attorno
# (extra e pittura); due occhi umani in mezzo alle bolle.
def _becco_pesce_palla(c):
    """Il becco del pesce palla: due placche di dente bianco, sopra e sotto il taglio della bocca."""
    P, sh = c.P, c.forma
    mat = P.materiale('BeccoPalla', (0.86, 0.82, 0.7), rough=0.25, coat=0.7, sss=0.3)
    for k, dz in enumerate((0.0055, -0.0055)):
        z = sh.mouth_z0 + dz
        f = P.sdf.ellipsoid((0.001, 0.0, z), (0.011, 0.02, 0.0065))
        c.obs.append(P.oggetto_sdf(f'BeccoPalla{k}', f, (-0.015, -0.028, z - 0.012), (0.02, 0.028, z + 0.012), mat, res=0.0006))


def _bubboni(c):
    """Pesce Bubbone: il becco, e le bolle nere gonfie (cupole affondate a metà nella pelle, di tante misure),
    con il livido violaceo attorno a ciascuna."""
    _becco_pesce_palla(c)
    body = c.body
    rng = np.random.default_rng(23)
    occhi = c.specie.opzioni.get('occhi_extra', [])
    C, R = [], []
    for s in (-1, 1):
        n = 0
        while n < (40 if s < 0 else 24):
            t, v = float(rng.uniform(0.07, 0.74)), float(rng.uniform(-0.3, 0.97))
            if t < 0.2 and v > 0.2:
                continue                      # non sull'occhio del pesce
            if s < 0 and any(abs(t - te) < re * 2.4 and abs(v - ve) < 0.36 for te, ve, re in occhi):
                continue                      # né sugli occhi in più
            r = float(rng.choice([0.007, 0.01, 0.013, 0.017, 0.022, 0.027], p=[0.2, 0.24, 0.2, 0.16, 0.12, 0.08]))
            p, nr = body.superficie(t, v, s)
            C.append(p - nr * r * 0.45)
            R.append(r)
            n += 1
    f, lo, hi = _campo_sfere(C, R)
    c.obs.append(c.P.oggetto_sdf('Bubboni', f, lo, hi, _membrana_nera(c, 'Bubboni'), res=0.0011 if c.fast else 0.0006))
    _pittura(c, 'livido', _vicino(C, np.array(R) * 0.9, 0.012), (0.09, 0.05, 0.065), ruvido=0.3)


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


# ── Missina della Melma (missina, Myxine glutinosa) ──
# Niente occhi veri (occhi=[]), tre paia di barbigli attorno alla bocca (Shape.filamenti), la fila dei pori
# del muco sul fianco (disegno 'linea' a puntini), la piega della coda. «Tanta melma da riempire il secchio.
# È nera, ed è tiepida»: la melma nera e lucida a chiazze, più sotto che sopra perché cola (un guscio dal
# campo del corpo), le gocce grosse che pendono dalla pancia e i fili che si afflosciano (extra); tre occhi
# umani piccoli dove la missina non ne ha.
def _melma_missina(c):
    """Missina della Melma: la melma nera a chiazze (il corpo gonfiato dove il rumore lo dice, più sotto che
    sopra), le gocce dalla pancia, i fili fra un punto e l'altro della pancia, la bava dalla bocca."""
    P, body = c.P, c.body
    base = body.base()
    n3 = P.sdf.Noise3(31)

    def spessore(p):
        nz = n3(p, scale=0.03, octaves=3)
        sotto = np.clip(0.5 - np.clip(body.norm_v(p), -1.2, 1.2), 0, 1.5)    # la melma scende: più sotto che sopra
        return np.clip((nz + 0.3 * sotto + 0.06) * 4.0, 0, 1) * (0.003 + 0.003 * sotto)

    def f(p):
        return base(p) - spessore(p) + 0.0015
    lo, hi = body.bounds(pad=0.012)
    c.obs.append(P.oggetto_sdf('MelmaNera', f, lo, hi, P.tar_material(), res=0.0013 if c.fast else 0.0008))
    rng = np.random.default_rng(5)
    for k, t in enumerate((0.1, 0.19, 0.27, 0.36, 0.45, 0.53, 0.62, 0.71, 0.8, 0.89)):
        p, _ = body.superficie(t, -0.97, -1)
        _goccia(c, f'GocciaMelma{k}', p + np.array((0, 0.002, 0.001), np.float32), float(rng.uniform(0.025, 0.08)),
                r0=0.0036, r1=float(rng.uniform(0.0055, 0.009)), dir=(float(rng.uniform(-0.1, 0.1)), -0.05, -1.0))
    for k, (t0, t1, cad) in enumerate(((0.14, 0.23, 0.035), (0.31, 0.4, 0.05), (0.48, 0.57, 0.04), (0.66, 0.75, 0.045))):
        a, _ = body.superficie(t0, -0.9, -1)
        b, _ = body.superficie(t1, -0.85, -1)
        _filo(c, f'FiloMelma{k}', a, b, cad, r=0.0026)
    a, _ = body.superficie(0.02, -0.5, -1)
    _goccia(c, 'BavaMelma', a, 0.05, r0=0.0028, r1=0.0065, dir=(-0.15, -0.1, -1.0))


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


# ── Specchio Nero (pesce specchio, Hoplostethus mediterraneus) ──
# Alto e compresso, la testa enorme con le creste e le cavità del muco (un reticolo largo sulla testa), gli
# occhi grandi, la bocca grande e obliqua, la carena di scudetti sul ventre (Spine in fila sulla linea di
# mezzo), la coda forcuta; rosato e argento. «Una macchia nera lucida come uno specchio. Dentro c'è la barca,
# e sulla barca c'è qualcuno in più»: lo specchio ovale sul fianco (una pittura liscia e lucida con
# un'immagine fatta con PIL): la notte, la barca con la lampara accesa, il pescatore e dietro di lui una
# figura in più, alta, magra e pallida.
_SPECCHIO = (0.5, -0.02, 0.102, 0.084)        # t, v del centro; mezza larghezza (x), mezza altezza (z)


def _immagine_specchio(c, W=736, H=600):
    """La barca riflessa nello specchio: cielo e mare di notte, la barca nera con la lampara che brilla sulla
    prua e il suo riflesso sull'acqua, il pescatore illuminato di lato, e dietro di lui la figura in più."""
    import os
    from PIL import Image, ImageDraw, ImageFilter
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, yy / H
    oriz = 0.6
    cielo = np.array((6, 9, 20), np.float32)[None, None] * (1 - v[..., None] / oriz) + np.array((22, 30, 50), np.float32) * (v[..., None] / oriz)
    mare = np.array((4, 6, 12), np.float32)[None, None] * np.ones_like(v)[..., None]
    img = np.where((v < oriz)[..., None], cielo, mare)
    # la lampara: alone caldo e riflesso spezzato sull'acqua
    lx, ly = 0.25, 0.37
    dist = np.sqrt(((u - lx) * W / H) ** 2 + (v - ly) ** 2)
    img += np.array((255, 190, 110), np.float32) * (np.exp(-(dist / 0.07) ** 2) * 0.85 + np.exp(-(dist / 0.2) ** 2) * 0.18)[..., None]
    riflesso = (v > oriz + 0.02) * np.exp(-((u - lx) / 0.025) ** 2) * (np.sin(v * 160) > 0.2) * np.exp(-(v - oriz) / 0.25)
    img += np.array((200, 140, 70), np.float32) * riflesso[..., None] * 0.7
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)

    def P(a, b):
        return (a * W, b * H)
    # la barca (scafo, cabina a poppa, il palo della lampara a prua)
    d.polygon([P(0.1, 0.53), P(0.88, 0.56), P(0.82, 0.68), P(0.22, 0.68)], fill=(3, 3, 4))
    d.rectangle([P(0.7, 0.44), P(0.84, 0.56)], fill=(4, 4, 5))
    d.line([P(0.2, 0.55), P(0.2, 0.33), P(0.24, 0.33)], fill=(12, 10, 8), width=6)
    d.ellipse([P(0.225, 0.315), P(0.265, 0.365)], fill=(255, 236, 190))
    # il pescatore: nero, con il bordo caldo verso la lampara
    d.ellipse([P(0.365, 0.35), P(0.435, 0.435)], fill=(120, 76, 38))
    d.ellipse([P(0.372, 0.355), P(0.44, 0.44)], fill=(5, 5, 6))
    d.polygon([P(0.33, 0.57), P(0.338, 0.47), P(0.4, 0.43), P(0.465, 0.47), P(0.475, 0.57)], fill=(5, 5, 6))
    d.line([P(0.332, 0.565), P(0.34, 0.475), P(0.395, 0.437)], fill=(140, 88, 40), width=5)
    # la figura in più: alta, magra, pallida, la testa piegata, le braccia lunghe oltre il bordo
    pal = (150, 156, 162)
    d.ellipse([P(0.57, 0.17), P(0.625, 0.245)], fill=pal)
    d.line([P(0.6, 0.24), P(0.59, 0.29)], fill=pal, width=9)
    d.polygon([P(0.555, 0.57), P(0.56, 0.31), P(0.59, 0.28), P(0.625, 0.31), P(0.632, 0.57)], fill=pal)
    d.line([P(0.56, 0.32), P(0.535, 0.47), P(0.54, 0.66)], fill=pal, width=7)
    d.line([P(0.628, 0.32), P(0.652, 0.48), P(0.645, 0.67)], fill=pal, width=7)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    # lo specchio è scuro ai bordi: sfuma al nero verso l'ovale
    a = np.asarray(im, np.float32)
    e = ((u - 0.5) / 0.5) ** 2 + ((v - 0.5) / 0.5) ** 2
    a *= np.clip((1.0 - e) / 0.35, 0, 1)[..., None] ** 0.8
    percorso = os.path.join(_cartella_tex(c), 'specchio_nero.png')
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(percorso)
    return percorso


def _specchio_nero(c):
    """Specchio Nero: lo specchio ovale sul fianco sinistro, nero e lucidissimo (liscio, senza squame), con la
    barca dentro che si vede anche al buio (l'immagine brilla appena da sé)."""
    t, v, rx, rz = _SPECCHIO
    zc, h, _ = (float(a[0]) for a in c.body.section(np.array([t], np.float32)))
    zc = zc + h * v
    percorso = _immagine_specchio(c)

    def ovale(p):
        e = ((p[:, 0] - t) / rx) ** 2 + ((p[:, 2] - zc) / rz) ** 2
        return np.clip((1 - e) / 0.05, 0, 1) * np.clip(-p[:, 1] / 0.004, 0, 1)
    colore = _proiezione(percorso, t - rx, t + rx, zc - rz, zc + rz)
    _pittura(c, 'specchio', ovale, lambda g: (colore(g)[0], None), ruvido=0.02, liscio=True, luce=1.6)


SPECIE['specchio_nero'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.04), (0.08, 0.1), (0.15, 0.15), (0.25, 0.185), (0.38, 0.195), (0.52, 0.18), (0.68, 0.13),
             (0.82, 0.075), (0.93, 0.045), (1, 0.038)],
        bot=[(0, -0.05), (0.04, -0.1), (0.1, -0.15), (0.2, -0.19), (0.32, -0.205), (0.45, -0.2), (0.6, -0.16), (0.75, -0.1),
             (0.88, -0.055), (1, -0.038)],
        w=[(0, 0.012), (0.06, 0.04), (0.2, 0.06), (0.4, 0.058), (0.65, 0.04), (0.85, 0.022), (1, 0.014)],
        eye_t=0.125, eye_z=0.065, eye_r=0.046, mouth_t=0.15, mouth_z0=0.012, mouth_z1=-0.09, gill_t=0.36,
        spine=[Spine(0.42, 0.78, -1.0, -1.0, 12, lunghezza=0.012, raggio=0.0045, lati='centro', inclinazione=0.7, fila=True)],
        fins=[Fin('dorsal', 0.42, 0.72, [(0, 0), (0.08, 0.7), (0.2, 0.95), (0.4, 1.0), (0.75, 0.85), (1, 0.08)], 0.13, 22,
                  spiny=True),
              Fin('anal', 0.68, 0.82, [(0, 0), (0.15, 0.9), (0.6, 0.7), (1, 0.05)], 0.09, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.3), 0.25, 20),
              Fin('pectoral', 0.32, 0.335, PETTORALE, 0.14, 11),
              Fin('pelvic', 0.36, 0.375, PELVICA, 0.08, 7, spiny=True)]),
    aspetto=Look(back=(0.42, 0.14, 0.1), flank=(0.66, 0.42, 0.37), belly=(0.74, 0.6, 0.54), fin=(0.55, 0.2, 0.15),
                 iris=(0.72, 0.62, 0.42), iris_dark=(0.12, 0.08, 0.05), metal=0.55, irid=0.3, squame=0.9, bocca_col=(0.02, 0.015, 0.02),
                 disegni=[Disegno('reticolo', colore=(0.2, 0.05, 0.04), forza=0.6, scala=22, larghezza=0.12, u1=0.3)]),
    extra=_specchio_nero,
    famiglia='corrupt', piano='alto',
    opzioni=dict(occhi_extra=[(0.27, -0.38, 0.022), (0.72, 0.3, 0.018)], iridi=[IRIDE_CASTANA, IRIDE_VERDE],
                 escrescenza=None, colature=1))


# ── Sciabola di Carbone (pesce sciabola nero, Aphanopus carbo) ──
# Il nastro lungo e compresso del pesce sciabola (dalla prova della sciabola), ma nero carbone con i
# riflessi di rame, la dorsale spinosa e poi molle con la tacca, la bocca con le zanne. «Occhi grandi come
# monete, e dentro una lampara accesa»: gli occhi enormi, la pupilla nera e un punto di luce calda dentro,
# con l'alone (il materiale degli occhi cambiato dall'extra).
def _occhi_lampara(c):
    """Sciabola di Carbone: gli occhi con la lampara dentro: iride sottile dorata, pupilla enorme e nera e, un
    poco in alto, il punto di luce calda che brilla con il suo alone; e le zanne davanti."""
    m, g = c.P.material('OcchioLampara')
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(x, z, 0.0))
    davanti = g.smoothstep(0.1, -0.45, y)
    col = g.mix(g.mul(g.smoothstep(0.99, 0.92, r), davanti), (0.03, 0.025, 0.02), (0.6, 0.45, 0.18))
    col = g.mix(g.mul(g.smoothstep(0.84, 0.78, r), davanti), col, (0.004, 0.004, 0.005))
    dl = g.vmath('LENGTH', g.comb(g.sub(x, 0.12), g.sub(z, 0.18), 0.0))
    lamp = g.mul(g.smoothstep(0.15, 0.06, dl), davanti)
    alone = g.mul(g.smoothstep(0.5, 0.0, dl), davanti)
    col = g.mix(lamp, col, (1.0, 0.85, 0.6))
    em = g.add(g.mul(lamp, 45.0), g.mul(alone, 3.0))
    g.output_material(g.principled(color=col, rough=0.25, coat=1.0, coat_rough=0.02, spec=0.6, emission=(1.0, 0.68, 0.32),
                                   emission_strength=em))
    for o in c.obs:
        if o.name.startswith('Eye'):
            o.data.materials.clear()
            o.data.materials.append(m)
    c.obs += c.P.denti_mascelle(c.body, n=6, lunghezza=0.0045, zanne=(0, 1), nome='DenteCarbone')


SPECIE['sciabola_di_carbone'] = Specie(
    forma=Shape(
        top=[(0, -0.002), (0.02, 0.011), (0.06, 0.028), (0.12, 0.036), (0.25, 0.038), (0.6, 0.034), (0.85, 0.02), (0.95, 0.01),
             (1, 0.005)],
        bot=[(0, -0.009), (0.03, -0.019), (0.08, -0.03), (0.15, -0.034), (0.4, -0.036), (0.7, -0.03), (0.9, -0.014), (1, -0.005)],
        w=[(0, 0.003), (0.05, 0.011), (0.15, 0.013), (0.5, 0.011), (0.8, 0.006), (1, 0.002)],
        eye_t=0.068, eye_z=0.011, eye_r=0.021, mouth_t=0.07, mouth_z0=-0.008, mouth_z1=-0.006, gill_t=0.14,
        fins=[Fin('dorsal', 0.11, 0.56, [(0, 0), (0.01, 0.8), (0.5, 0.9), (0.95, 0.6), (1, 0.15)], 0.018, 80, spiny=True),
              Fin('dorsal', 0.58, 0.97, [(0, 0.2), (0.05, 0.9), (0.5, 1.0), (0.95, 0.8), (1, 0.2)], 0.024, 50),
              Fin('anal', 0.62, 0.95, [(0, 0), (0.1, 0.6), (0.9, 0.5), (1, 0.1)], 0.01, 30),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.4, 0.3), 0.045, 12),
              Fin('pectoral', 0.135, 0.145, PETTORALE, 0.035, 8)],
        piega=[(0, 0), (0.35, 5), (0.7, -5), (1, 3)]),
    aspetto=Look(back=(0.02, 0.016, 0.014), flank=(0.05, 0.038, 0.032), belly=(0.06, 0.05, 0.045), fin=(0.035, 0.026, 0.022),
                 iris=(0.6, 0.45, 0.18), iris_dark=(0.1, 0.07, 0.03), metal=0.65, irid=0.6, squame=0.0, linea_laterale=0.0,
                 lucido=0.8),
    extra=_occhi_lampara,
    famiglia='corrupt', piano='nastriforme',
    opzioni=dict(occhi_extra=[(0.3, 0.1, 0.012), (0.55, 0.0, 0.011)], iridi=[IRIDE_GRIGIA, IRIDE_NOCCIOLA],
                 escrescenza=None, colature=1))


# ── Granatiere Nero (granatiere, Coelorinchus caelorhincus) ──
# La testa grossa, il muso appuntito che sporge sopra la bocca (la bocca sotto, a mezzaluna), gli occhi
# grandi, il barbiglio corto sotto il mento, la prima dorsale alta e corta, la seconda e l'anale basse fino in
# fondo, il corpo che si assottiglia in una coda da topo; grigio-bruno, la macchia nera sul ventre. «Una coda
# come quella di un topo… cento sotto la barca»: la coda nuda, rosa, ad anelli (Shape.anelli e una pittura
# liscia) che finisce in un filo, e i baffi da topo sul muso (extra).
def _baffi_granatiere(c):
    """Granatiere Nero: i baffi da topo sul muso (lunghi, sottili, chiari, a ventaglio) e la coda nuda e rosa
    (una pittura liscia, senza squame, dal tronco in giù)."""
    body = c.body
    rng = np.random.default_rng(3)
    segs = []
    for s in (-1, 1):
        for k in range(6):
            a, _ = body.superficie(0.036 + 0.005 * k, -0.15 + 0.09 * k, s)
            d = (-0.25 + 0.17 * k, s * 0.9, 0.45 - 0.17 * k)
            pts = _percorso(a, d, 0.1 + 0.03 * float(rng.random()), n=10, curva=(2.5, 0.0, -0.8), onda=0.12, giri=1.0)
            segs.append(_catena(pts, (0.0018, 0.0004)))
    _coni(c, 'Baffi', segs, c.P.materiale('Baffi', (0.8, 0.77, 0.72), rough=0.35, coat=0.5))

    def coda(p):
        return np.clip((p[:, 0] - 0.5) / 0.08, 0, 1)
    _pittura(c, 'coda_nuda', coda, (0.5, 0.33, 0.31), ruvido=0.42, liscio=True)


SPECIE['granatiere_nero'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.006), (0.07, 0.025), (0.12, 0.05), (0.18, 0.068), (0.25, 0.075), (0.33, 0.07), (0.45, 0.05),
             (0.6, 0.03), (0.75, 0.016), (0.9, 0.007), (1, 0.002)],
        bot=[(0, -0.016), (0.04, -0.03), (0.1, -0.05), (0.18, -0.065), (0.28, -0.068), (0.38, -0.055), (0.5, -0.036), (0.65, -0.02),
             (0.8, -0.01), (1, -0.002)],
        w=[(0, 0.006), (0.05, 0.022), (0.15, 0.042), (0.28, 0.045), (0.45, 0.03), (0.65, 0.016), (0.85, 0.007), (1, 0.002)],
        eye_t=0.14, eye_z=0.025, eye_r=0.027,
        bocca='ventrale', mouth_a=0.1, mouth_t=0.14, mouth_z1=-0.045, mouth_z0=-0.045, gill_t=0.24,
        anelli=120, anelli_tratto=(0.5, 1.0),
        filamenti=[Filamento(t=0.13, v=-1.0, lunghezza=0.016, raggio=0.0018, dir=(0.2, 0.0, -1.0), lati='centro'),
                   Filamento(xyz=(0.995, 0.0, 0.0), dir=(1.0, 0.0, 0.02), curva=(0, 0, -0.8), lunghezza=0.12, raggio=0.0022,
                             lati='centro', punta=0.25, segmenti=12, colore=(0.5, 0.33, 0.31))],
        fins=[Fin('dorsal', 0.24, 0.3, [(0, 0), (0.08, 1.0), (0.3, 0.9), (0.7, 0.5), (1, 0.05)], 0.08, 10, spiny=True),
              Fin('dorsal', 0.36, 0.62, [(0, 0), (0.05, 0.6), (0.5, 0.7), (0.9, 0.5), (1, 0.05)], 0.014, 30),
              Fin('anal', 0.3, 0.62, [(0, 0), (0.05, 0.7), (0.5, 0.8), (0.9, 0.5), (1, 0.05)], 0.018, 34),
              Fin('pectoral', 0.23, 0.245, PETTORALE, 0.09, 10),
              Fin('pelvic', 0.27, 0.285, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.24, 0.22, 0.19), flank=(0.4, 0.37, 0.33), belly=(0.48, 0.43, 0.39), fin=(0.26, 0.24, 0.21),
                 iris=(0.6, 0.62, 0.55), iris_dark=(0.08, 0.08, 0.07), metal=0.3, irid=0.1, squame=0.8, linea_laterale=0.0,
                 disegni=[Disegno('macchia', colore=(0.02, 0.02, 0.025), forza=0.9, u=0.3, v=-0.85, r=0.012, allungamento=0.6)]),
    extra=_baffi_granatiere,
    famiglia='corrupt', piano='coda_di_topo',
    opzioni=dict(occhi_extra=[(0.2, -0.3, 0.017), (0.36, 0.25, 0.015)], iridi=[IRIDE_NOCCIOLA, IRIDE_AZZURRA],
                 escrescenza=None, colature=2))


# ── Vipera degli Abissi (pesce vipera, Chauliodus sloani) ──
# Allungato e compresso, la testa corta e la bocca enorme, la prima dorsale molto avanti con il primo raggio
# lunghissimo (un filamento con la lucina in punta), l'adiposa, la coda piccola; nero-verde iridescente con il
# reticolo delle squame, le file di fotofori lungo il ventre. «I denti così lunghi che non riesce a chiudere
# la bocca»: la bocca aperta, e le zanne di vetro che restano fuori: quelle di sotto salgono davanti al muso
# fin sopra l'occhio, quelle di sopra scendono fuori dalla mandibola (extra).
def _vetro_zanne(c):
    """Il materiale delle zanne: vetro bianco, appena trasparente."""
    m, g = c.P.material('ZanneVetro')
    g.output_material(g.principled(color=(0.86, 0.86, 0.82), rough=0.12, coat=1.0, coat_rough=0.02, transmission=0.35, ior=1.5,
                                   sss=0.2, sss_radius=(1, 1, 1), sss_scale=0.002))
    return m


def _zanne_vipera(c):
    """Vipera degli Abissi: le zanne fuori dalla bocca (catene di coni che si piegano), i dentini lungo le due
    mascelle aperte, e la lucina in punta al raggio lungo della dorsale."""
    P, body, sh = c.P, c.body, c.forma
    vetro = _vetro_zanne(c)
    R = P.sdf.rot_matrix('y', -sh.bocca_aperta)
    cern = np.array((sh.mouth_t, 0.0, sh.mouth_z1), np.float32)
    segs = []
    for s in (-1, 1):
        # di sotto: dalla punta della mandibola su (nel riferimento della mandibola), poi indietro sopra il muso
        for x, L, rr in ((0.012, 0.13, 0.0046), (0.03, 0.09, 0.0036)):
            zl = float(body.mouth_line(np.array([x], np.float32))[0])
            a = np.array((x, s * float(body.surface_y(x, zl - 0.004)) * 0.85, zl - 0.005), np.float32)
            a = (a - cern) @ R.T + cern
            d = np.array((-0.25, s * 0.22, 1.0), np.float32) @ R.T
            segs.append(_catena(_percorso(a, d, L, n=14, curva=(9.0, 0.0, -2.0)), (rr, rr * 0.12)))
        # di sopra: giù, fuori dalla mandibola, piegate indietro
        for x, L, rr in ((0.016, 0.06, 0.0035), (0.042, 0.045, 0.003)):
            zl = float(body.mouth_line(np.array([x], np.float32))[0])
            a = np.array((x, s * float(body.surface_y(x, zl + 0.004)) * 0.85, zl + 0.004), np.float32)
            segs.append(_catena(_percorso(a, (-0.3, s * 0.25, -1.0), L, n=12, curva=(8.0, 0.0, 0.0)), (rr, rr * 0.12)))
    _coni(c, 'ZanneVipera', segs, vetro)
    c.obs += P.denti_mascelle(body, n=8, lunghezza=0.006, apertura=sh.bocca_aperta, mat=vetro, nome='DenteVipera')
    # la lucina in punta al raggio lungo della dorsale (lo stesso percorso del Filamento)
    fl = sh.filamenti[0]
    a, _ = body.superficie(fl.t, fl.v, 0)
    punta = _percorso(a, fl.dir, fl.lunghezza, n=fl.segmenti, curva=fl.curva)[-1]
    luce = P.materiale('EscaVipera', (0.6, 0.8, 1.0), rough=0.2, coat=1.0, emissione=(0.4, 0.75, 1.0), forza=12.0)
    c.obs.append(P.oggetto_sdf('EscaVipera', P.sdf.sphere(punta, 0.004), punta - 0.008, punta + 0.008, luce, res=0.0005))


SPECIE['vipera_degli_abissi'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.02, 0.012), (0.05, 0.03), (0.1, 0.045), (0.2, 0.054), (0.4, 0.056), (0.6, 0.05), (0.8, 0.035),
             (0.93, 0.02), (1, 0.016)],
        bot=[(0, -0.02), (0.03, -0.035), (0.08, -0.048), (0.18, -0.056), (0.4, -0.058), (0.6, -0.052), (0.8, -0.036), (0.93, -0.02),
             (1, -0.016)],
        w=[(0, 0.008), (0.05, 0.022), (0.15, 0.03), (0.4, 0.028), (0.7, 0.02), (1, 0.008)],
        eye_t=0.062, eye_z=0.016, eye_r=0.016, mouth_t=0.13, mouth_z0=0.0, mouth_z1=-0.004, bocca_aperta=30.0, gill_t=0.17,
        filamenti=[Filamento(t=0.17, v=1.0, lunghezza=0.3, raggio=0.0017, dir=(0.25, 0.0, 1.0), curva=(3.5, 0, -2.5), lati='centro',
                             punta=0.35, segmenti=16)],
        fotofori=Fotofori(righe=[(0.08, 0.95, -0.82, 30), (0.1, 0.62, -0.55, 18), (0.03, 0.06, 0.1, 2)], sparsi=10, raggio=0.0036,
                          colore=(0.35, 0.65, 1.0), forza=5.0),
        fins=[Fin('dorsal', 0.17, 0.24, [(0, 0), (0.15, 0.9), (0.5, 0.8), (1, 0.05)], 0.05, 8),
              Fin('dorsal', 0.84, 0.88, [(0, 0), (0.3, 0.9), (1, 0.1)], 0.02, 8, carnosa=True, spessore=0.003),
              Fin('anal', 0.8, 0.9, [(0, 0), (0.15, 0.9), (0.6, 0.7), (1, 0.05)], 0.045, 10),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.3), 0.13, 16),
              Fin('pectoral', 0.14, 0.15, PETTORALE, 0.06, 8, z=-0.6),
              Fin('pelvic', 0.45, 0.46, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.015, 0.025, 0.03), flank=(0.04, 0.07, 0.08), belly=(0.025, 0.03, 0.035), fin=(0.04, 0.05, 0.05),
                 iris=(0.5, 0.55, 0.5), iris_dark=(0.05, 0.06, 0.05), metal=0.5, irid=0.6, squame=0.6, linea_laterale=0.0,
                 bocca_col=(0.02, 0.01, 0.012),
                 disegni=[Disegno('reticolo', colore=(0.01, 0.015, 0.02), forza=0.6, scala=60, larghezza=0.12)]),
    extra=_zanne_vipera,
    famiglia='corrupt', piano='fusiforme',
    opzioni=dict(occhi_extra=[(0.34, 0.25, 0.016), (0.55, -0.2, 0.014)], iridi=[IRIDE_AZZURRA, IRIDE_CASTANA],
                 escrescenza=None, colature=2))


# ── Razza dalle Due Facce (razza bianca, Rostroraja alba) ──
# Il disco a rombo con il muso lunghissimo e appuntito (i margini davanti concavi), la coda con le due
# dorsali vicino alla punta; grigio-bruna sopra, bianca sotto con il bordo scuro. «Sotto, le razze hanno una
# faccia che sembra sorridere. Questa ne ha due, e non sorridono tutte e due»: il ritratto mostra il ventre
# (roll 142). La faccia vera: le narici, la bocca a sorriso, le fessure delle branchie (campo); più indietro,
# sulla pancia, la seconda faccia: due occhi umani e una bocca storta all'ingiù con i denti da persona
# (campo ed extra), la pece che le cola dagli occhi. Gli occhi in più della famiglia starebbero sul dorso,
# che qui non si vede: li mette l'extra, sul ventre.
_DUE_FACCE = dict(narici=(0.17, 0.058, 0.0095, 0.016),          # t, |z| del centro, mezze misure dell'ovale in x e z
                  sorriso=(0.232, 0.08, 0.036, 0.006),          # t del centro, mezza larghezza, quanto curva, mezza apertura
                  branchie=(0.29, 0.018, 0.102),                # t della prima, passo, |z|
                  occhi=(0.39, 0.06, 0.025),                    # t, |z|, raggio
                  smorfia=(0.468, 0.078, 0.032, 0.0115))        # come il sorriso, ma storta all'ingiù
_CONTORNO_RAZZA_BIANCA = [(0, 0.0), (0.04, 0.02), (0.08, 0.045), (0.12, 0.085), (0.17, 0.15), (0.22, 0.24), (0.27, 0.33),
                          (0.3, 0.36), (0.34, 0.33), (0.4, 0.23), (0.46, 0.12), (0.5, 0.08), (0.55, 0.09), (0.6, 0.06),
                          (0.64, 0.02), (0.67, 0.0), (1.0, 0.0)]
_SPESSORE_RAZZA_BIANCA = [(0, 0.002), (0.1, 0.008), (0.3, 0.015), (0.45, 0.013), (0.6, 0.008), (0.68, 0.002), (1.0, 0.001)]


def _occhio_ventre(c, t, z, r):
    """Il centro di un occhio sul ventre della razza (lato +Y), affondato come quelli della famiglia."""
    return np.array((t, float(c.body.surface_y(t, z)) - r * 0.42, z), np.float32)


def _arco(z, t0, mz, cu, ap, su):
    """Una bocca ad arco sul ventre della razza, nel piano x-z: (x della linea di mezzo, mezza apertura) in z.
    su = 1: gli angoli verso il muso (sorride), −1: verso la coda (storta all'ingiù)."""
    zz = np.clip(np.asarray(z, np.float32) / mz, -1.2, 1.2)
    return t0 - su * cu * zz * zz, ap * np.sqrt(np.clip(1 - zz * zz, 0, 1)) + ap * 0.12


def _campo_due_facce(c, f):
    """Razza dalle Due Facce: sul ventre (y > 0) le narici, la bocca a sorriso e le fessure delle branchie
    della faccia vera; più indietro le orbite con le palpebre e la bocca storta all'ingiù della seconda."""
    F = _DUE_FACCE
    to, zo, ro = F['occhi']
    occhi = [_occhio_ventre(c, to, s * zo, ro) for s in (-1, 1)]
    smax, smin = c.P.sdf.smax, c.P.sdf.smin

    def g(p):
        d = f(p)
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        prof = -(d + 0.011)
        out = d
        # le narici: due ovali scavati
        tn, zn, ax, az = F['narici']
        for s in (-1, 1):
            nar = (np.sqrt(((x - tn) / ax) ** 2 + ((z - s * zn) / az) ** 2) - 1.0) * ax
            out = smax(out, -np.maximum(np.maximum(nar, prof), -y), 0.0015)
        # le due bocche: il sorriso della faccia vera e la smorfia della seconda
        for chiave, su in (('sorriso', 1), ('smorfia', -1)):
            t0, mz, cu, ap = F[chiave]
            xm, hw = _arco(z, t0, mz, cu, ap, su)
            bocca = np.maximum(np.abs(x - xm) - hw, np.abs(z) - mz)
            out = smax(out, -np.maximum(np.maximum(bocca, prof), -y), 0.0015)
        # le cinque fessure delle branchie per lato
        tb, passo, zb = F['branchie']
        for k in range(5):
            for s in (-1, 1):
                fess = np.maximum(np.abs(x - (tb + passo * k)) - 0.0018, np.abs(z - s * (zb + 0.005 * k)) - 0.015)
                out = smax(out, -np.maximum(np.maximum(fess, -(d + 0.005)), -y), 0.001)
        # le orbite della seconda faccia, con la palpebra carnosa (come gli occhi della famiglia, girati verso +Y)
        for ce in occhi:
            q = p - ce
            out = smax(out, -(np.linalg.norm(q, axis=1) - ro * 1.02), 0.003)
            anello = np.sqrt((np.sqrt(q[:, 0] ** 2 + q[:, 2] ** 2) - ro * 1.02) ** 2 + (-q[:, 1] - ro * 0.12) ** 2) - ro * 0.17
            out = smin(out, anello, 0.002)
        return out
    return g


def _due_facce(c):
    """Razza dalle Due Facce: gli occhi umani e i denti da persona della seconda faccia, il dentro scuro delle
    bocche e delle narici, il bordo scuro del ventre, la pece che cola dagli occhi della seconda faccia."""
    P, body = c.P, c.body
    F = _DUE_FACCE
    to, zo, ro = F['occhi']
    for s, iride in ((-1, IRIDE_AZZURRA), (1, IRIDE_CASTANA)):
        _occhio_umano(c, f'OcchioVentre{s}', _occhio_ventre(c, to, s * zo, ro), ro, iride, (0.05 * s, 1.0, 0.08))
    # i denti nella smorfia: la fila verso il muso e quella verso la coda, che si toccano in mezzo
    denti = P.materiale('DentiUmani', (0.84, 0.79, 0.66), rough=0.24, coat=0.7, sss=0.3)
    t1, mz1, cu1, ap1 = F['smorfia']
    for k, zz in enumerate(np.linspace(-0.84, 0.84, 11)):
        z = float(zz) * mz1
        xm, hw = (float(a) for a in _arco(z, t1, mz1, cu1, ap1, -1))
        tang = np.array((2 * cu1 * float(zz) / mz1, 0.0, 1.0), np.float32)       # la tangente dell'arco della bocca
        alt = min(0.0092, hw * 0.96)
        for su in (-1, 1):                 # −1: la fila verso il muso (il dente punta a +x), 1: quella verso la coda
            x = xm + su * (hw - alt / 2 + 0.0002)
            y = float(body.surface_y(x, z)) - 0.0042
            _dente_umano(c, f'DenteFaccia{k}_{su}', (x, y, z), 0.0108, alt, 0.005, tang, (float(-su), 0.0, 0.0), denti)
    # il dentro scuro di bocche e narici, sul ventre
    dentro = _dentro(c, 0.0012, 0.002)

    def scuro(p):
        return dentro(p) * (p[:, 1] > 0) * (p[:, 0] < 0.52)
    _pittura(c, 'facce', scuro, (0.04, 0.01, 0.015), ruvido=0.3)
    # il bordo scuro del ventre (dove il disco si assottiglia)
    disco = body.disco

    def bordo(p):
        t = np.clip(p[:, 0], 0, 1)
        sp = disco.surface_y(t, p[:, 2])
        return np.clip(1 - (sp - 0.003) / 0.005, 0, 1) * (p[:, 1] > 0) * (np.abs(p[:, 2]) > body.section(t)[1])
    _pittura(c, 'bordo_ventre', bordo, (0.12, 0.11, 0.12), ruvido=0.45)

    # la pece attorno agli occhi della seconda faccia e che ne cola: sul ventre, verso +z (in giù nel ritratto)
    occhi = [_occhio_ventre(c, to, s * zo, ro) for s in (-1, 1)]

    def lacrime(p):
        w = np.zeros(len(p), np.float32)
        for s, ce in zip((-1, 1), occhi):
            w = np.maximum(w, np.clip(1 - (np.linalg.norm(p - ce, axis=1) - ro * 1.25) / 0.005, 0, 1))
            z0 = s * zo + ro * 0.9
            corsia = np.exp(-((p[:, 0] - to - 0.0025 * np.sin(p[:, 2] * 260)) / 0.0052) ** 2)
            w = np.maximum(w, corsia * (p[:, 2] > z0) * (p[:, 2] < z0 + 0.085 - 0.03 * (s > 0)))
        return w * (p[:, 1] > 0)
    _pittura(c, 'lacrime', lacrime, (0.006, 0.006, 0.008), ruvido=0.05)


SPECIE['razza_due_facce'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.04, 0.012), (0.1, 0.03), (0.18, 0.056), (0.3, 0.068), (0.45, 0.055), (0.55, 0.034), (0.65, 0.017),
             (0.8, 0.011), (0.95, 0.007), (1, 0.005)],
        bot=[(0, 0.0), (0.04, -0.012), (0.1, -0.03), (0.18, -0.056), (0.3, -0.068), (0.45, -0.055), (0.55, -0.034), (0.65, -0.017),
             (0.8, -0.011), (0.95, -0.007), (1, -0.005)],
        w=[(0, 0.002), (0.04, 0.006), (0.1, 0.012), (0.2, 0.026), (0.3, 0.03), (0.45, 0.025), (0.55, 0.017), (0.65, 0.011),
           (0.8, 0.008), (0.95, 0.006), (1, 0.005)],
        eye_t=0.17, eye_z=0.0, eye_r=0.01, occhi=[(0.165, 0.03, 0.0105, -1), (0.165, -0.03, 0.0105, -1)], spiracoli=0.0055,
        bocca='nessuna', branchie='nessuna',
        disco=Disco(contorno=_CONTORNO_RAZZA_BIANCA, spessore=_SPESSORE_RAZZA_BIANCA),
        fins=[Fin('dorsal', 0.84, 0.88, [(0, 0), (0.25, 0.9), (0.55, 1.0), (0.8, 0.5), (1, 0.05)], 0.026, 16, carnosa=True,
                  spessore=0.004),
              Fin('dorsal', 0.9, 0.94, [(0, 0), (0.25, 0.9), (0.55, 1.0), (0.8, 0.5), (1, 0.05)], 0.024, 16, carnosa=True,
                  spessore=0.004),
              Fin('caudal', 1.0, 1.0, [(0, 0.5), (0.5, 0.7), (1.0, 0.0), (0.5, -0.5), (0, -0.4)], 0.03, 16, carnosa=True,
                  spessore=0.003)]),
    aspetto=Look(back=(0.16, 0.14, 0.12), flank=(0.2, 0.18, 0.15), belly=(0.86, 0.85, 0.82), fin=(0.15, 0.13, 0.11),
                 iris=(0.55, 0.5, 0.3), iris_dark=(0.1, 0.09, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.45, ruvido=0.45,
                 disegni=[Disegno('macchie', colore=(0.5, 0.48, 0.44), forza=0.5, scala=40, r=0.18)]),
    extra=_due_facce, campo=_campo_due_facce,
    famiglia='corrupt', piano='razza', ritratto=Ritratto(yaw=4.0, pitch=0.0, roll=142.0),
    opzioni=dict(occhi_extra=[], iridi=[], escrescenza=None, colature=0))


# ── Pesce Angelo Caduto (squadro, Squatina squatina) ──
# Lo squalo piatto: la testa larga e tonda con la bocca davanti, gli occhi in cima con gli spiracoli dietro,
# le pettorali larghe come ali staccate dalla testa da una tacca, le pelviche larghe dietro, il tronco che
# porta due dorsali e la caudale (il lobo di sotto più grande); sabbia con i puntini. «Le ali ci sono ancora,
# nere e bagnate, e intorno alla testa un'aureola di occhi»: le ali dipinte di nero lucido (pittura), una
# corona di occhi umani attorno alla testa (gli occhi della famiglia, messi in cerchio).
_TRONCO_SQUADRO = [(0, 0.0), (0.015, 0.05), (0.04, 0.072), (0.08, 0.084), (0.12, 0.086), (0.16, 0.078), (0.22, 0.07), (0.32, 0.066),
                   (0.45, 0.058), (0.55, 0.048), (0.65, 0.04), (0.8, 0.032), (0.92, 0.026), (1, 0.022)]


def _aureola(n=12, centro=(0.085, 0.0), raggi=(0.066, 0.074), r=0.0105):
    """Gli occhi in più in cerchio attorno alla testa dello squadro: (t, v, raggio), con v = z / la mezza
    larghezza del tronco in t (come li vuole la famiglia sulle razze)."""
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        t = centro[0] + raggi[0] * math.cos(a)
        z = centro[1] + raggi[1] * math.sin(a)
        out.append((round(t, 4), round(z / _profilo(_TRONCO_SQUADRO, t), 3), r * (1.0 if k % 2 else 0.85)))
    return out


def _ali_nere(c):
    """Pesce Angelo Caduto: le ali nere e bagnate: il disco fuori dal tronco dipinto di nero lucidissimo, che
    sfuma sul tronco."""
    body = c.body

    def ali(p):
        zc, h, _ = body.section(np.clip(p[:, 0], 0, 1))
        return np.clip((np.abs(p[:, 2] - zc) - h - 0.002) / 0.014, 0, 1) * (p[:, 0] > 0.1)
    _pittura(c, 'ali_nere', ali, (0.006, 0.006, 0.008), ruvido=0.03, lucido=1.0)


SPECIE['pesce_angelo_caduto'] = Specie(
    forma=Shape(
        top=_TRONCO_SQUADRO,
        bot=[(t, -z) for t, z in _TRONCO_SQUADRO],
        w=[(0, 0.004), (0.05, 0.016), (0.15, 0.024), (0.3, 0.026), (0.5, 0.024), (0.7, 0.021), (0.9, 0.017), (1, 0.014)],
        eye_t=0.07, eye_z=0.0, eye_r=0.008, occhi=[(0.07, 0.04, 0.008, -1), (0.07, -0.04, 0.008, -1)], spiracoli=0.006,
        bocca='nessuna', branchie='nessuna',
        disco=Disco(contorno=[(0, 0.0), (0.1, 0.0), (0.13, 0.06), (0.16, 0.13), (0.2, 0.2), (0.25, 0.26), (0.3, 0.3), (0.34, 0.29),
                              (0.38, 0.21), (0.42, 0.12), (0.45, 0.085), (0.5, 0.11), (0.55, 0.15), (0.6, 0.155), (0.64, 0.1),
                              (0.68, 0.05), (0.7, 0.0), (1.0, 0.0)],
                    spessore=[(0, 0.001), (0.1, 0.002), (0.2, 0.012), (0.35, 0.014), (0.5, 0.01), (0.65, 0.006), (0.72, 0.001),
                              (1.0, 0.001)]),
        fins=[Fin('dorsal', 0.62, 0.68, DORSALE_SQUALO, 0.06, 20, carnosa=True, spessore=0.005),
              Fin('dorsal', 0.76, 0.82, DORSALE_SQUALO, 0.055, 20, carnosa=True, spessore=0.005),
              Fin('caudal', 1.0, 1.0, [(0, 0.15), (0.5, 0.7), (0.85, 0.95), (0.75, 0.4), (0.5, 0.0), (0.8, -0.6), (1.0, -1.3),
                                      (0.6, -0.9), (0.12, -0.15)], 0.16, 40, carnosa=True, spessore=0.005)]),
    aspetto=Look(back=(0.07, 0.06, 0.045), flank=(0.09, 0.075, 0.055), belly=(0.8, 0.78, 0.72), fin=(0.02, 0.02, 0.025),
                 iris=(0.6, 0.55, 0.35), iris_dark=(0.12, 0.1, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.12, ruvido=0.55, tinta_pinne=0.0,
                 disegni=[Disegno('punti', colore=(0.025, 0.02, 0.015), forza=0.7, scala=170, r=0.15),
                          Disegno('macchie', colore=(0.2, 0.17, 0.12), forza=0.5, scala=45, r=0.16, seme=4)]),
    extra=_ali_nere,
    famiglia='corrupt', piano='razza',
    opzioni=dict(occhi_extra=_aureola(),
                 iridi=[IRIDE_AZZURRA, IRIDE_CASTANA, IRIDE_VERDE, IRIDE_GRIGIA, IRIDE_NOCCIOLA, IRIDE_AZZURRA,
                        IRIDE_CASTANA, IRIDE_VERDE, IRIDE_GRIGIA, IRIDE_NOCCIOLA, IRIDE_AZZURRA, IRIDE_CASTANA],
                 escrescenza=None, colature=0))


# ── Re Nero (pesce re, Lampris guttatus) ──
# Ovale altissimo e compresso, la bocca piccola, l'occhio grande, la dorsale con il lobo davanti alto e
# falcato e poi bassa fino alla coda, le pettorali e le pelviche lunghe a falce, la coda a mezzaluna larga;
# qui nero come la pece (con le macchie chiare appena visibili e le pinne rosso cupo). «Al posto della corona
# ha una bocca»: sulla nuca, davanti alla dorsale, una bocca aperta verso l'alto (campo) con le labbra e una
# corona di denti dritti attorno, lunghi e corti alternati (extra), la gola rosso scuro.
_CORONA = (0.2, 0.9, 0.085, 0.032)        # t, v del centro della bocca sulla nuca, mezza lunghezza, mezza larghezza


def _corona_geometria(c):
    """Il telaio della bocca sulla nuca: il punto della pelle, la normale e i due assi del piano tangente."""
    t, v, _, _ = _CORONA
    p0, n = c.body.superficie(t, v, -1)
    e1 = np.array((1.0, 0.0, 0.0), np.float32) - n * float(n[0])
    e1 /= np.linalg.norm(e1)
    return p0, n, e1, np.cross(n, e1)


def _campo_corona(c, f):
    """Re Nero: la bocca sulla nuca: un buco ovale profondo nel piano della pelle, con il labbro tondo attorno."""
    p0, n, e1, e2 = _corona_geometria(c)
    _, _, L, Wd = _CORONA
    smax, smin = c.P.sdf.smax, c.P.sdf.smin

    def g(p):
        d = f(p)
        q = p - p0
        a, b, h = q @ e1, q @ e2, q @ n
        ell = (np.sqrt((a / L) ** 2 + (b / Wd) ** 2) - 1.0) * Wd
        # il buco: dentro l'ovale, fino a 0.032 sotto la pelle e solo vicino alla nuca (non dall'altra parte)
        out = smax(d, -np.maximum(np.maximum(ell, -(d + 0.04)), -(h + 0.06)), 0.003)
        labbro = np.sqrt(ell ** 2 + (h - 0.0015) ** 2) - 0.0065
        return smin(out, labbro, 0.004)
    return g


def _corona_re(c):
    """Re Nero: la corona di denti attorno alla bocca della nuca (dritti verso l'alto e un poco in fuori,
    lunghi e corti alternati) e la gola rosso scuro."""
    P = c.P
    p0, n, e1, e2 = _corona_geometria(c)
    _, _, L, Wd = _CORONA
    A, B, R1, R2 = [], [], [], []
    for k in range(16):
        a = 2 * math.pi * k / 16
        radiale = e1 * math.cos(a) * L + e2 * math.sin(a) * Wd
        rad = radiale / np.linalg.norm(radiale)
        base = p0 + radiale * 0.95 + n * 0.002
        lungo = k % 2 == 0
        d = n * 0.9 + rad * 0.3
        A.append(base)
        B.append(base + d / np.linalg.norm(d) * (0.058 if lungo else 0.03))
        R1.append(0.0088 if lungo else 0.0062)
        R2.append(0.0006)
    f, lo, hi = P.campo_coni(A, B, R1, R2)
    c.obs.append(P.oggetto_sdf('CoronaDenti', f, lo, hi, P.dirty_teeth_material(), res=0.0007 if c.fast else 0.0004))
    dentro = _dentro(c, 0.003, 0.004)

    def gola(p):
        return dentro(p) * np.clip(1 - np.linalg.norm(p - p0, axis=1) / (L * 1.6), 0, 1)
    _pittura(c, 'gola_corona', gola, (0.16, 0.015, 0.025), ruvido=0.25)


SPECIE['re_nero'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.03, 0.04), (0.08, 0.12), (0.15, 0.2), (0.25, 0.26), (0.38, 0.28), (0.52, 0.26), (0.66, 0.2), (0.8, 0.12),
             (0.92, 0.055), (1, 0.035)],
        bot=[(0, -0.06), (0.04, -0.12), (0.1, -0.19), (0.2, -0.25), (0.33, -0.28), (0.47, -0.27), (0.6, -0.22), (0.74, -0.14),
             (0.88, -0.065), (1, -0.035)],
        w=[(0, 0.012), (0.06, 0.04), (0.2, 0.065), (0.4, 0.068), (0.65, 0.05), (0.85, 0.025), (1, 0.014)],
        eye_t=0.12, eye_z=0.02, eye_r=0.035, mouth_t=0.06, mouth_z0=-0.03, mouth_z1=-0.045, gill_t=0.26,
        fins=[Fin('dorsal', 0.28, 0.86, [(0, 0), (0.04, 1.0), (0.1, 0.92), (0.16, 0.35), (0.3, 0.12), (0.9, 0.1), (1, 0.02)], 0.26, 60),
              Fin('anal', 0.6, 0.86, [(0, 0), (0.1, 0.5), (0.5, 0.4), (1, 0.05)], 0.05, 20),
              Fin('caudal', 1.0, 1.0, coda_falcata(2.4, 0.8, radice=1.0), 0.22, 24),
              Fin('pectoral', 0.3, 0.32, [(0, 0.06), (0.35, 0.12), (0.7, 0.1), (1.0, 0.04), (0.6, -0.02), (0, -0.06)], 0.25, 14,
                  z=0.0, dir=(1.0, 0.25, 0.1)),
              Fin('pelvic', 0.38, 0.4, [(0, 0.06), (0.35, 0.12), (0.7, 0.1), (1.0, 0.04), (0.6, -0.02), (0, -0.06)], 0.2, 12,
                  dir=(0.6, 0.3, -0.8))]),
    aspetto=Look(back=(0.012, 0.012, 0.016), flank=(0.025, 0.024, 0.03), belly=(0.04, 0.035, 0.04), fin=(0.2, 0.025, 0.02),
                 iris=(0.75, 0.55, 0.15), iris_dark=(0.25, 0.15, 0.03), metal=0.5, irid=0.4, squame=0.0, linea_laterale=0.0,
                 lucido=0.85,
                 disegni=[Disegno('macchie', colore=(0.3, 0.31, 0.33), forza=0.55, scala=40, r=0.18)]),
    extra=_corona_re, campo=_campo_corona,
    famiglia='corrupt', piano='alto',
    opzioni=dict(occhi_extra=[(0.45, 0.2, 0.03), (0.62, -0.3, 0.025), (0.33, -0.48, 0.02)],
                 iridi=[IRIDE_AZZURRA, IRIDE_CASTANA, IRIDE_VERDE], escrescenza=None, colature=3))
