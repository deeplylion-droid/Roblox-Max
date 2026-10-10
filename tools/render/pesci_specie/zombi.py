"""
Zombi: marci, occhi lattiginosi, pinne strappate, punti di sutura (src/game/catalog.ts, docs/CATALOGO.md).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast

La famiglia (pesci.py: zombie) mette il marcio, la cucitura sul fianco sinistro, gli occhi lattiginosi e strappa
le pinne a raggi. Qui sotto, prima delle specie, gli aiuti propri della famiglia: occhi lattiginosi fatti a mano
(più o meno torbidi, con la pupilla a fessura), croste sulla pelle (fango, terra, sabbia, malta), una cucitura dove
la famiglia non arriva (sul ventre), gli strappi nelle pinne di carne degli squali, la carne marcia dei tagli.
"""
from __future__ import annotations

import math

import numpy as np

from .base import (DORSALE_SQUALO, PELVICA, PETTORALE, PETTORALE_ALA, PETTORALE_TONDA, RITRATTO_PROTOTIPI, Disco,
                   Disegno, Filamento, Fin, Look, Ritratto, Shape, Specie, Spine, coda_appuntita, coda_eterocerca,
                   coda_forcuta, coda_tonda, coda_tronca)

F32 = np.float32
SPECIE = {}

# ── Orrata (orata, Sparus aurata) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['orrata'] = Specie(
    forma=Shape(
        top=[(0, -0.03), (0.02, 0.004), (0.06, 0.06), (0.12, 0.118), (0.2, 0.158), (0.35, 0.182), (0.5, 0.176), (0.7, 0.118), (0.85, 0.064), (0.95, 0.042), (1, 0.04)],
        bot=[(0, -0.05), (0.025, -0.08), (0.1, -0.118), (0.25, -0.155), (0.45, -0.168), (0.6, -0.148), (0.75, -0.1), (0.9, -0.05), (1, -0.04)],
        w=[(0, 0.008), (0.06, 0.034), (0.2, 0.058), (0.4, 0.064), (0.65, 0.05), (0.85, 0.025), (1, 0.015)],
        eye_t=0.155, eye_z=0.058, eye_r=0.031, mouth_t=0.07, mouth_z0=-0.038, mouth_z1=-0.05, gill_t=0.29,
        fins=[Fin('dorsal', 0.33, 0.84, [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.82), (0.8, 0.75), (0.95, 0.55), (1, 0.05)], 0.12, 22, spiny=True),
              Fin('anal', 0.62, 0.84, [(0, 0), (0.12, 0.9), (0.6, 0.62), (0.95, 0.5), (1, 0.05)], 0.09, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.34), 0.26, 20),
              Fin('pectoral', 0.32, 0.34, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.2, 12),
              Fin('pelvic', 0.37, 0.39, [(0, 0), (0.6, 0.28), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.1, 7, spiny=True)]),
    aspetto=Look(back=(0.16, 0.18, 0.19), flank=(0.42, 0.44, 0.44), belly=(0.62, 0.62, 0.58), fin=(0.16, 0.16, 0.18),
                 iris=(0.72, 0.6, 0.36), pattern='bream'),
    famiglia='zombie', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ═════════════════════════ aiuti della famiglia ═════════════════════════

def _gia(c, nome):
    """Il materiale con quel nome, se c'è già (ogni pesce parte da una scena vuota: vale dentro un pesce)."""
    return c.P.bpy.data.materials.get(nome)


def _sezione(c, t):
    """(quota del centro, mezza altezza, mezza larghezza) del corpo in t, come numeri."""
    zc, h, w = c.body.section(np.array([t], F32))
    return float(zc[0]), float(h[0]), float(w[0])


def _res(c, fine, veloce):
    """La griglia di un oggetto in più: più grossa nelle anteprime veloci."""
    return veloce if c.fast else fine


def _mat_occhio(c, nome, sclera=(0.70, 0.70, 0.64), sclera2=(0.80, 0.78, 0.72), iride=(0.62, 0.64, 0.60),
                pupilla=(0.50, 0.52, 0.50), iride_r=0.75, pupilla_r=0.40, fessura=None, velo=0.35,
                velo_col=(0.75, 0.77, 0.75), capillari=0.55):
    """Occhio lattiginoso fatto a mano (come cloudy_eye di skin.py, con più manopole): la sclera torbida (fra
    sclera e sclera2), i capillari verso il bordo, l'iride sbiadita con l'anello scuro, la pupilla velata (tonda o
    a fessura: 'slit_h' / 'slit_v') e sopra il velo della cataratta (velo: quanto, velo_col: di che colore)."""
    m = _gia(c, nome)
    if m:
        return m
    m, g = c.P.material(nome)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(x, z, 0.0))
    if fessura == 'slit_h':
        rp = g.vmath('LENGTH', g.comb(g.mul(x, 0.5), g.mul(z, 2.4), 0.0))
    elif fessura == 'slit_v':
        rp = g.vmath('LENGTH', g.comb(g.mul(x, 2.4), g.mul(z, 0.5), 0.0))
    else:
        rp = r
    davanti = g.smoothstep(0.1, -0.45, y)
    nube = g.noise(co, scale=7.0, detail=6.0, rough=0.6)
    col = g.mix(g.mul(g.smoothstep(0.35, 0.75, nube.fac), 0.35), sclera, sclera2)
    vv = g.voronoi(co, scale=8.0, feature='DISTANCE_TO_EDGE')
    cap = g.mul(g.smoothstep(0.010, 0.0, vv), g.smoothstep(0.62, 0.97, r))
    col = g.mix(g.mul(cap, capillari), col, (0.48, 0.09, 0.08))
    ang = g.math('ARCTAN2', z, x)
    fib = g.noise(g.comb(g.mul(ang, 6.0), g.mul(r, 8.0), 0.0), scale=2.5, detail=5.0, rough=0.65)
    ir = g.mix(g.smoothstep(0.3, 0.75, fib.fac), tuple(a * 0.7 for a in iride), iride)
    ir = g.mix(g.smoothstep(iride_r - 0.12, iride_r, r), ir, tuple(a * 0.3 for a in iride))
    col = g.mix(g.mul(g.smoothstep(iride_r + 0.02, iride_r - 0.02, r), davanti), col, ir)
    col = g.mix(g.mul(g.smoothstep(pupilla_r + 0.03, pupilla_r - 0.02, rp), davanti), col, pupilla)
    col = g.mix(g.mul(g.mul(davanti, g.smoothstep(0.3, 0.8, nube.fac)), velo), col, velo_col)
    g.output_material(g.principled(color=col, rough=0.35, coat=1.0, coat_rough=0.03, spec=0.5, sss=0.15,
                                   sss_radius=(1, 0.6, 0.5), sss_scale=0.004))
    return m


def _occhi(c, mat, nome='OcchioMorto', guarda=None):
    """Gli occhi della forma con un materiale proprio (con opzioni occhi=None la famiglia non li mette, ma le
    orbite restano). guarda: dove guarda l'occhio sinistro (None: di lato, come sempre)."""
    for k, (cen, r, look) in enumerate(c.body.occhi_lista()):
        if guarda is not None and look[1] < 0:
            look = guarda
        ob = c.P.eyeball(f'{nome}{k}', tuple(map(float, cen)), r, mat, look=look, col=c.P.COL)
        if c.forma.eye_allungato != 1.0:
            ob.scale.x *= c.forma.eye_allungato
        c.obs.append(ob)


def _mat_grumi(c, nome, chiaro, scuro, scala=60.0, rough=0.85, coat=0.0, rilievo=0.5, chiazze=None):
    """Materiale grumoso (terra, sabbia, malta, pietra): due toni mescolati dal rumore, la grana fine; chiazze =
    (colore, quanto): un terzo tono a macchiette (i sassolini nella terra, le venature della pietra)."""
    m = _gia(c, nome)
    if m:
        return m
    m, g = c.P.material(nome)
    co = g.texcoord('Object')
    n = g.noise(co, scale=scala, detail=6.0, rough=0.62)
    grana = g.noise(co, scale=scala * 6.0, detail=2.0)
    col = g.mix(g.smoothstep(0.35, 0.68, n.fac), scuro, chiaro)
    if chiazze is not None:
        cc, q = chiazze
        vv = g.voronoi(co, scale=scala * 2.5, feature='F1', randomness=1.0)
        col = g.mix(g.mul(g.smoothstep(0.22, 0.12, vv), q), col, cc)
    col = g.mix(g.mul(grana.fac, 0.3), col, scuro)
    h = g.add(n.fac, g.mul(grana.fac, 0.6))
    nrm = g.bump(h, strength=rilievo, distance=0.002)
    kw = dict(coat=coat, coat_rough=0.08, coat_normal=nrm) if coat else {}
    g.output_material(g.principled(color=col, rough=rough, normal=nrm, spec=0.35, **kw))
    return m


def _mat_carne_marcia(c, nome='CarneMarcia'):
    """La carne dei tagli, marcia: rosa spento e bruno, venata di grasso giallastro, bagnata (come il marcio
    profondo della famiglia, appena più viva)."""
    m = _gia(c, nome)
    if m:
        return m
    m, g = c.P.material(nome)
    co = g.texcoord('Object')
    n = g.noise(co, scale=45.0, detail=5.0, rough=0.6)
    n2 = g.noise(co, scale=140.0, detail=3.0)
    col = g.mix(g.smoothstep(0.35, 0.7, n.fac), (0.4, 0.15, 0.12), (0.21, 0.08, 0.065))
    col = g.mix(g.mul(g.smoothstep(0.6, 0.72, n2.fac), 0.75), col, (0.5, 0.45, 0.3))
    h = g.add(n.fac, g.mul(n2.fac, 0.5))
    nrm = g.bump(h, strength=0.4, distance=0.002)
    g.output_material(g.principled(color=col, rough=0.35, coat=0.6, coat_rough=0.1, sss=0.25,
                                   sss_radius=(1.0, 0.3, 0.2), sss_scale=0.006, normal=nrm, coat_normal=nrm))
    return m


def _crosta(c, nome, mat, spessore, maschera, res=None, attrs=None):
    """Una crosta sulla pelle (fango, terra, sabbia, malta): il corpo gonfiato di spessore·maschera(p) meno il
    corpo; comincia appena sotto la pelle, così non resta una fessura. maschera(p) 0..1 dice dove sta e quanto è
    spessa (dove è 0 non c'è niente). Un oggetto solo, sul corpo senza le pinne."""
    base = c.body.base()
    res = res or _res(c, 0.0008, 0.0016)

    def f(q):
        d = base(q)
        m = maschera(q)
        return np.maximum(d - spessore * m, -d - 0.0008 * np.minimum(m * 4.0, 1.0)).astype(F32)
    lo, hi = c.body.bounds(pad=spessore + 0.006, solo_corpo=True)
    return c.P.oggetto_sdf(nome, f, lo, hi, mat, res=res, attrs=attrs)


def _solco(f, punti, profondita=0.0035, larghezza=0.0025):
    """Il solco di una cucitura lungo la spezzata fitta dei punti (sulla pelle), dentro un campo(c, f)."""
    from scipy.spatial import cKDTree
    albero = cKDTree(np.asarray(punti, F32))

    def g(p):
        d = f(p)
        dist, _ = albero.query(p, k=1, workers=-1)
        return (d + profondita * np.exp(-(dist / larghezza) ** 2)).astype(F32)
    return g


def _punti_cucitura(c, punti, quanti=12, seme=0, larghezza=0.009):
    """I punti di una cucitura lungo la spezzata fitta dei punti (sulla pelle): fili scuri che attraversano il
    solco, come in zombie() di pesci.py, ma su qualunque lato (la normale è quella della pelle)."""
    P, sdf = c.P, c.P.sdf
    rng = np.random.default_rng(seme)
    S = np.asarray(punti, F32)
    N = c.body.normale(S)
    filo = P.thread_material()
    for k in range(quanti):
        i = int(4 + k * (len(S) - 8) / max(quanti - 1, 1))
        p0, nrm = S[i], N[i]
        tg = S[min(i + 1, len(S) - 1)] - S[max(i - 1, 0)]
        tg /= np.linalg.norm(tg)
        lato = np.cross(tg, nrm)
        lato /= np.linalg.norm(lato)
        a = p0 + lato * larghezza + tg * rng.uniform(-0.002, 0.002)
        b = p0 - lato * larghezza + tg * rng.uniform(-0.002, 0.002)
        mid = p0 + nrm * 0.0035
        fb = sdf.union(sdf.round_cone(a, mid, 0.0011, 0.0013), sdf.round_cone(mid, b, 0.0013, 0.0011), k=0.001)
        c.obs.append(P.oggetto_sdf(f'PuntoCucitura{k}', fb, np.minimum(a, b) - 0.006, np.maximum(a, b) + 0.006, filo,
                                   res=0.0005))


def _strappi(c, f, seme=0, morsi=2, buchi=2, grandezza=0.16):
    """Le pinne di carne (squali) strappate come quelle a raggi della famiglia: morsi a mezzaluna sul bordo libero
    e qualche buco dentro. Si chiama dentro un campo(c, f): restituisce il campo nuovo."""
    P = c.P
    rng = np.random.default_rng(seme)
    vb, a_mondo, _ = c.body.telaio_pinne()
    n3 = P.sdf.Noise3(seme + 100)
    C, R = [], []
    for fin in c.forma.fins:
        if not fin.carnosa:
            continue
        for s in ((-1, 1) if fin.kind in ('pectoral', 'pelvic') else (-1,)):
            radici, punte, _ = P.fin_points(vb, fin, s)
            Rt, T = np.array(radici, F32), np.array(punte, F32)
            if a_mondo is not None:
                Rt, T = a_mondo(Rt), a_mondo(T)
            # solo i raggi lunghi: lontano dal corpo (non si morde il corpo)
            lunghi = [i for i in range(1, len(T) - 1) if np.linalg.norm(T[i] - Rt[i]) > fin.size * 0.45]
            if not lunghi:
                continue
            for _ in range(morsi):
                i = lunghi[int(rng.integers(0, len(lunghi)))]
                C.append(T[i] + (T[i] - Rt[i]) * 0.04)
                R.append(min(fin.size * grandezza, 0.022) * rng.uniform(0.6, 1.25))
            for _ in range(buchi):
                i = lunghi[int(rng.integers(0, len(lunghi)))]
                C.append(Rt[i] + (T[i] - Rt[i]) * rng.uniform(0.5, 0.75))
                R.append(min(fin.size * 0.06, 0.008) * rng.uniform(0.7, 1.3))
    if not C:
        return f
    C, R = np.array(C, F32), np.array(R, F32)
    lo, hi = C.min(0) - R.max() - 0.01, C.max(0) + R.max() + 0.01

    def g(p):
        d = f(p)
        m = np.all((p >= lo) & (p <= hi), axis=1)
        if m.any():
            q = p[m]
            nz = n3(q, scale=0.006, octaves=2)
            dd = d[m]
            for cc, rr in zip(C, R):
                dd = np.maximum(dd, rr * (1.0 + 0.35 * nz) - np.linalg.norm(q - cc, axis=1))
            d = d.copy()
            d[m] = dd
        return d
    return g


def _campo_dischi(C, N, R, th):
    """Tanti dischetti (scaglie): centri C, normali N, raggi R, mezzo spessore th; per ogni punto i 4 più vicini
    (KD-tree). Restituisce (campo, lo, hi)."""
    from scipy.spatial import cKDTree
    C, N, R = np.asarray(C, F32), np.asarray(N, F32), np.asarray(R, F32)
    N = N / np.linalg.norm(N, axis=1, keepdims=True)
    albero = cKDTree(C)
    k = min(4, len(C))
    lo, hi = C.min(0) - R.max() - 0.004, C.max(0) + R.max() + 0.004

    def f(P):
        out = np.full(len(P), 10.0, F32)
        m = np.all((P >= lo) & (P <= hi), axis=1)
        if m.any():
            Q = P[m]
            _, idx = albero.query(Q, k=k, workers=-1)
            idx = np.asarray(idx).reshape(len(Q), k)
            best = np.full(len(Q), 10.0, F32)
            for j in range(k):
                i = idx[:, j]
                q = Q - C[i]
                h = np.einsum('ij,ij->i', q, N[i])
                rr = np.linalg.norm(q - h[:, None] * N[i], axis=1)
                best = np.minimum(best, np.sqrt(np.maximum(rr - R[i], 0) ** 2 + h * h) - th)
            out[m] = best
        return out
    return f, lo, hi


# ═════════════════════════ le specie ═════════════════════════

# ── Cefamorto (cefalo, Mugil cephalus) ──
# Robusto e quasi cilindrico, la testa larga e piatta sopra, il muso corto e la bocca piccola; le due dorsali ben
# separate (la prima di 4 spine), le pettorali alte sul fianco, la coda forcuta; grigio con le righe scure lungo
# le file di squame e la macchia scura all'ascella della pettorale. «Mangia il fango… adesso il fango mangia lui»:
# croste di fango sul ventre e sulla bocca, a chiazze sui fianchi, e il fango che cola.

def _mat_fango(c):
    """Il fango del fondo: bruno scuro e bagnato, con le croste più chiare dove si è seccato."""
    m = _gia(c, 'Fango')
    if m:
        return m
    m, g = c.P.material('Fango')
    co = g.texcoord('Object')
    n = g.noise(co, scale=38.0, detail=6.0, rough=0.65)
    grana = g.noise(co, scale=240.0, detail=2.0)
    col = g.mix(g.smoothstep(0.35, 0.7, n.fac), (0.042, 0.03, 0.019), (0.1, 0.078, 0.05))
    secco = g.smoothstep(0.6, 0.7, n.fac)
    col = g.mix(g.mul(secco, 0.85), col, (0.2, 0.165, 0.115))
    h = g.add(n.fac, g.mul(grana.fac, 0.4))
    nrm = g.bump(h, strength=0.5, distance=0.003)
    g.output_material(g.principled(color=col, rough=g.mixf(secco, 0.32, 0.9), coat=g.mixf(secco, 0.8, 0.0),
                                   coat_rough=0.05, normal=nrm, coat_normal=nrm, spec=0.4))
    return m


def _fango_cefalo(c):
    """Le croste di fango (più spesse sul ventre e attorno alla bocca, a chiazze sui fianchi, mai sull'occhio) e
    le colature dal ventre e dal mento."""
    P, b = c.P, c.body
    mat = _mat_fango(c)
    n3 = P.sdf.Noise3(121)
    ec, er, _ = b.occhi_lista()[0]

    def maschera(q):
        v = b.norm_v(q)
        x = q[:, 0]
        nz = n3(q, scale=0.03, octaves=3)
        basso = np.clip((-v - 0.25) / 0.45, 0, 1)                    # il ventre, che striscia sul fondo
        sopra = np.clip((v - 0.05) / 0.4, 0, 1)                      # il dorso resta quasi pulito
        bocca = np.clip(1.0 - np.hypot((x - 0.01) / 0.055, (v + 0.3) / 0.7), 0, 1)
        occhio = np.clip(np.linalg.norm(q - ec, axis=1) / er - 1.6, 0, 1)
        k = np.clip((nz + 0.32 * basso + 0.9 * bocca - 0.16 - 0.45 * sopra) / 0.1, 0, 1)
        return (k * np.maximum(np.maximum(basso, bocca), 0.3) * occhio * (0.75 + 0.25 * nz)).astype(F32)
    c.obs.append(_crosta(c, 'CrostaFango', mat, 0.0055, maschera))
    rng = np.random.default_rng(121)
    for k, (t, ln) in enumerate(((0.02, 0.04), (0.17, 0.035), (0.29, 0.055), (0.41, 0.03), (0.52, 0.048))):
        p, _ = b.superficie(t, -1.0, 0)
        a = p + np.array((0.0, -0.002, 0.003), F32)
        f = P.drip(a, ln * rng.uniform(0.85, 1.15), r0=0.003, r1=0.0055, dir=(0.05, -0.08, -1.0))
        c.obs.append(P.oggetto_sdf(f'ColaFango{k}', f, a - 0.07, a + 0.07, mat, res=0.0006))


SPECIE['cefamorto'] = Specie(
    forma=Shape(
        top=[(0, -0.009), (0.015, 0.016), (0.04, 0.038), (0.08, 0.058), (0.13, 0.073), (0.2, 0.088), (0.32, 0.102), (0.45, 0.104),
             (0.6, 0.089), (0.75, 0.064), (0.88, 0.046), (1, 0.04)],
        bot=[(0, -0.026), (0.02, -0.045), (0.06, -0.067), (0.12, -0.088), (0.22, -0.104), (0.35, -0.11), (0.5, -0.102),
             (0.62, -0.084), (0.75, -0.062), (0.88, -0.047), (1, -0.04)],
        w=[(0, 0.014), (0.03, 0.043), (0.08, 0.063), (0.15, 0.074), (0.3, 0.077), (0.5, 0.066), (0.7, 0.043), (0.85, 0.028),
           (1, 0.016)],
        eye_t=0.075, eye_z=0.02, eye_r=0.019, mouth_t=0.045, mouth_z0=-0.016, mouth_z1=-0.024, gill_t=0.23,
        fins=[Fin('dorsal', 0.42, 0.49, [(0, 0), (0.12, 0.95), (0.3, 1.0), (0.6, 0.6), (1, 0.08)], 0.1, 4, spiny=True),
              Fin('dorsal', 0.66, 0.75, [(0, 0), (0.15, 0.9), (0.35, 0.85), (0.7, 0.45), (1, 0.06)], 0.075, 9),
              Fin('anal', 0.62, 0.74, [(0, 0), (0.15, 0.85), (0.4, 0.75), (0.75, 0.4), (1, 0.05)], 0.065, 10),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.45, 0.3), 0.24, 18),
              Fin('pectoral', 0.24, 0.255, PETTORALE, 0.11, 12, z=0.15),
              Fin('pelvic', 0.38, 0.395, PELVICA, 0.07, 6, spiny=True)]),
    aspetto=Look(back=(0.1, 0.12, 0.12), flank=(0.4, 0.42, 0.4), belly=(0.66, 0.65, 0.6), fin=(0.18, 0.19, 0.18),
                 iris=(0.7, 0.62, 0.4), metal=0.45, irid=0.2, squame=1.0, linea_laterale=0.0,
                 disegni=[Disegno('strisce', colore=(0.12, 0.13, 0.13), forza=0.6, n=6, v0=-0.55, v1=0.85, larghezza=0.05),
                          Disegno('macchia', colore=(0.04, 0.05, 0.07), forza=0.8, u=0.245, v=0.18, r=0.009),
                          Disegno('marmo', colore=(0.07, 0.055, 0.035), forza=0.55, scala=70, r=0.35, v1=-0.2)]),
    extra=_fango_cefalo,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=21, cucitura=(0.3, 0.6, -0.25), punti=11, marcio=0.44))


# ── Sogliombra (sogliola, Solea solea) ──
# Un pesce di fianco, molto compresso, con TUTTI E DUE GLI OCCHI SUL LATO −Y (la camera): il ritratto lo corica
# sul fondo. Dorsale e anale fanno la frangia tutto attorno, la coda tonda le tocca. «Da morta ha deciso di
# guardare anche dall'altra»: un terzo occhio lattiginoso spunta sul bordo del ventre, sotto la testa, girato
# verso il lato cieco; la cucitura sul lato degli occhi.

def _terzo_occhio(c):
    """Il terzo occhio della sogliola: (centro, raggio, sguardo), sul bordo del ventre sotto la testa, appena
    verso il lato cieco; guarda fuori dal bordo e un poco dall'altra parte."""
    zc, h, _ = _sezione(c, 0.12)
    r = 0.016
    return np.array((0.12, 0.002, zc - h - r * 0.05), F32), r, (-0.25, 0.2, -1.0)


def _campo_sogliola(c, f):
    """Il gonfiore di carne sul bordo dove spunta il terzo occhio, con la sua orbita."""
    sdf = c.P.sdf
    cen, r, _ = _terzo_occhio(c)
    sc = np.array((1.0 / 1.4, 1.0 / 1.05, 1.0), F32)

    def g(p):
        d = sdf.smin(f(p), np.linalg.norm((p - cen) * sc, axis=1) - r * 1.35, 0.01)
        return sdf.smax(d, -(np.linalg.norm(p - cen, axis=1) - r * 1.05), 0.002).astype(F32)
    return g


def _occhio_in_piu(c):
    cen, r, sguardo = _terzo_occhio(c)
    mat = _mat_occhio(c, 'OcchioCieco', sclera=(0.74, 0.7, 0.62), iride=(0.62, 0.62, 0.56), pupilla=(0.42, 0.43, 0.4),
                      capillari=1.0, velo=0.25)
    c.obs.append(c.P.eyeball('TerzoOcchio', tuple(map(float, cen)), r, mat, look=sguardo, col=c.P.COL))


SPECIE['sogliombra'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.02, 0.03), (0.06, 0.068), (0.15, 0.112), (0.3, 0.14), (0.5, 0.145), (0.7, 0.12), (0.85, 0.078),
             (0.95, 0.042), (1, 0.03)],
        bot=[(0, -0.03), (0.03, -0.062), (0.1, -0.1), (0.25, -0.135), (0.45, -0.145), (0.65, -0.128), (0.82, -0.088),
             (0.95, -0.044), (1, -0.03)],
        w=[(0, 0.004), (0.08, 0.015), (0.25, 0.02), (0.5, 0.02), (0.75, 0.014), (0.95, 0.007), (1, 0.005)],
        eye_t=0.08, eye_z=0.04, eye_r=0.0115,
        occhi=[(0.072, 0.048, 0.0115, -1), (0.104, 0.022, 0.0115, -1)],
        mouth_t=0.05, mouth_z0=-0.02, mouth_z1=-0.042, gill_t=0.17,
        fins=[Fin('dorsal', 0.025, 0.985, [(0, 0), (0.03, 0.6), (0.15, 0.9), (0.5, 1.0), (0.85, 0.9), (0.97, 0.7), (1, 0.55)], 0.05, 90),
              Fin('anal', 0.19, 0.985, [(0, 0), (0.04, 0.7), (0.2, 0.95), (0.6, 1.0), (0.9, 0.85), (1, 0.6)], 0.048, 75),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.0, 0.95), 0.1, 22),
              Fin('pectoral', 0.175, 0.185, PETTORALE_TONDA, 0.05, 9, bordo=(0.03, 0.025, 0.02)),
              Fin('pelvic', 0.17, 0.18, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.03, 5)]),
    aspetto=Look(back=(0.22, 0.17, 0.115), flank=(0.27, 0.22, 0.15), belly=(0.86, 0.83, 0.76), fin=(0.2, 0.16, 0.11),
                 iris=(0.7, 0.6, 0.35), iris_dark=(0.15, 0.12, 0.06), metal=0.0, irid=0.0, squame=0.6,
                 linea_laterale=0.8, linea_v=(0.0, 0.0), lucido=0.4,
                 disegni=[Disegno('marmo', colore=(0.11, 0.08, 0.05), forza=0.65, scala=26, r=0.4),
                          Disegno('punti', colore=(0.07, 0.05, 0.035), forza=0.6, scala=170, r=0.12)]),
    campo=_campo_sogliola, extra=_occhio_in_piu,
    famiglia='zombie', piano='piatto',
    opzioni=dict(seed=22, cucitura=(0.34, 0.76, -0.25), punti=12, marcio=0.45))


# ── Suro Sfatto (suro, Trachurus trachurus) ──
# Affusolato, l'occhio grande, la bocca obliqua; la prima dorsale alta e spinosa, la seconda lunga e bassa come
# l'anale; la coda profondamente forcuta; la linea laterale coperta di scudetti per tutta la lunghezza (sale
# sull'opercolo, scende a metà corpo e poi va dritta), la macchia nera sull'opercolo. «Si sfalda come pane
# bagnato. Le scaglie che restano sul legno brillano tutta la notte»: lembi di pelle che si staccano e si
# arricciano, con la carne marcia sotto, e le scaglie luminose addosso e che cadono.

def _lembi_suro_dati(c):
    """I lembi di pelle che si staccano: (cerniera, normale, e1 lungo il lembo, e2 di traverso, lunghezza,
    larghezza, quanto si alza, quanto si arriccia). Quelli bassi pendono giù oltre il ventre (il corpo sotto la
    cerniera si allontana, il lembo no), quelli alti si arricciano in fuori sopra il dorso: escono dalla sagoma."""
    out = []
    for t, v, dz, L, W, alza, arriccia in ((0.33, -0.28, -1, 0.1, 0.042, 0.04, 3.5), (0.5, -0.32, -1, 0.11, 0.05, 0.05, 4.0),
                                           (0.66, -0.25, -1, 0.085, 0.036, 0.06, 4.5), (0.42, 0.3, 1, 0.07, 0.04, 0.12, 9.0),
                                           (0.6, 0.35, 1, 0.06, 0.034, 0.1, 10.0), (0.22, -0.4, -1, 0.07, 0.032, 0.05, 5.0)):
        p0, n0 = c.body.superficie(t, v, -1)
        e1 = np.array((0.2, 0.0, float(dz)), F32)
        e1 = e1 - n0 * float(e1 @ n0)
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(n0, e1).astype(F32)
        out.append((p0 - n0 * 0.0004, n0, e1, e2, L, W, alza, arriccia))
    return out


def _lembi_suro(c):
    """I lembi (pelle d'argento sopra, carne pallida sotto: attributo 'sotto'), la carne marcia dove si sono
    staccati, e le scaglie luminose."""
    P, b, sdf = c.P, c.body, c.P.sdf
    lembi = _lembi_suro_dati(c)
    n3 = sdf.Noise3(123)
    th = 0.0009

    def piastre(q):
        d = np.full(len(q), 10.0, F32)
        sotto = np.zeros(len(q), F32)
        for p0, n0, e1, e2, L, W, tg, kk in lembi:
            r = q - p0
            s, u, h = r @ e1, r @ e2, r @ n0
            sc = np.clip(s, 0, L)
            alt = sc * tg + kk * sc * sc
            pend = tg + 2 * kk * sc
            dh = (h - alt) / np.sqrt(1 + pend * pend)
            nz = n3(q, scale=0.006, octaves=2)
            ell = (np.hypot((s - L * 0.5) / (L * 0.5), u / (W * 0.5)) - 1.0 - 0.25 * nz) * min(L, W) * 0.5
            dk = np.maximum(np.abs(dh) - th, ell)
            vicino = dk < d
            sotto = np.where(vicino, (dh < 0).astype(F32), sotto)
            d = np.minimum(d, dk)
        return d, sotto
    A = np.array([l[0] for l in lembi], F32)
    lo, hi = A.min(0) - 0.09, A.max(0) + 0.09
    m, g = P.material('LemboSuro')
    co = g.texcoord('Object')
    n = g.noise(co, scale=60.0, detail=4.0)
    pelle = g.mix(g.smoothstep(0.3, 0.7, n.fac), (0.2, 0.23, 0.23), (0.34, 0.36, 0.35))
    carne = g.mix(g.smoothstep(0.3, 0.7, n.fac), (0.46, 0.3, 0.27), (0.34, 0.22, 0.2))
    sotto = g.attr('sotto')
    g.output_material(g.principled(color=g.mix(sotto, pelle, carne), metal=g.mixf(sotto, 0.35, 0.0), rough=g.mixf(sotto, 0.35, 0.5),
                                   coat=0.5, coat_rough=0.1, normal=g.bump(n.fac, strength=0.3, distance=0.001)))
    c.obs.append(P.oggetto_sdf('LembiSuro', lambda q: piastre(q)[0], lo, hi, m, res=_res(c, 0.0005, 0.0008),
                               attrs={'sotto': lambda q: piastre(q)[1]}))

    # la carne marcia dove la pelle se n'è andata (sotto i lembi)
    def maschera(q):
        out = np.zeros(len(q), F32)
        for p0, n0, e1, e2, L, W, _, _ in lembi:
            r = q - p0
            s, u = r @ e1, r @ e2
            out = np.maximum(out, np.clip((1.0 - np.hypot((s - L * 0.5) / (L * 0.5), u / (W * 0.5))) / 0.15, 0, 1))
        return out
    c.obs.append(_crosta(c, 'CarneSottoLembi', _mat_carne_marcia(c), 0.0009, maschera, res=_res(c, 0.0006, 0.001)))

    # le scaglie luminose: attaccate qua e là sulla pelle che resta (qualcuna di sbieco) e qualcuna che cade
    rng = np.random.default_rng(323)
    C, N, R = [], [], []
    for _ in range(26):
        t, v = rng.uniform(0.12, 0.92), rng.uniform(-0.8, 0.8)
        p, n = b.superficie(t, v, -1)
        nn = n + rng.normal(0, 0.35, 3)
        C.append(p + n * 0.0012)
        N.append(nn)
        R.append(rng.uniform(0.0035, 0.0058))
    for _ in range(8):
        t = rng.uniform(0.15, 0.85)
        zc, h, _ = _sezione(c, t)
        C.append(np.array((t, rng.uniform(-0.05, -0.01), zc - h - rng.uniform(0.01, 0.045)), F32))
        N.append(rng.normal(0, 1, 3))
        R.append(rng.uniform(0.0035, 0.0055))
    f, lo, hi = _campo_dischi(C, N, R, 0.0005)
    luce = P.materiale('ScaglieLuminose', (0.55, 0.8, 0.74), rough=0.2, coat=1.0, metal=0.2, emissione=(0.45, 1.0, 0.82),
                       forza=5.0)
    c.obs.append(P.oggetto_sdf('ScaglieLuminose', f, lo, hi, luce, res=0.0004))


SPECIE['suro_sfatto'] = Specie(
    forma=Shape(
        top=[(0, -0.008), (0.02, 0.012), (0.05, 0.032), (0.1, 0.058), (0.18, 0.08), (0.3, 0.094), (0.42, 0.095), (0.55, 0.085),
             (0.7, 0.06), (0.85, 0.035), (0.95, 0.024), (1, 0.022)],
        bot=[(0, -0.016), (0.03, -0.03), (0.08, -0.055), (0.16, -0.078), (0.28, -0.092), (0.4, -0.09), (0.52, -0.078),
             (0.68, -0.055), (0.84, -0.032), (0.95, -0.023), (1, -0.022)],
        w=[(0, 0.006), (0.05, 0.026), (0.15, 0.044), (0.35, 0.05), (0.6, 0.04), (0.85, 0.02), (1, 0.012)],
        eye_t=0.085, eye_z=0.022, eye_r=0.027, mouth_t=0.085, mouth_z0=-0.006, mouth_z1=-0.022, gill_t=0.22,
        spine=[Spine(0.22, 0.47, 0.43, 0.02, 14, lunghezza=0.0035, raggio=0.0042, inclinazione=0.85, fila=True, seme=1),
               Spine(0.49, 0.97, 0.0, 0.0, 26, lunghezza=0.005, raggio=0.0048, inclinazione=0.85, fila=True, seme=2)],
        fins=[Fin('dorsal', 0.3, 0.42, [(0, 0), (0.12, 0.9), (0.3, 1.0), (0.7, 0.5), (1, 0.08)], 0.11, 8, spiny=True),
              Fin('dorsal', 0.44, 0.92, [(0, 0), (0.03, 0.75), (0.12, 0.6), (0.6, 0.45), (0.95, 0.4), (1, 0.06)], 0.05, 30),
              Fin('anal', 0.55, 0.92, [(0, 0), (0.04, 0.7), (0.15, 0.55), (0.6, 0.42), (0.95, 0.38), (1, 0.05)], 0.045, 24),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.65, 0.2), 0.25, 18),
              Fin('pectoral', 0.24, 0.255, [(0, 0), (0.45, 0.24), (1.0, 0.08), (0.8, -0.03), (0, -0.08)], 0.15, 12),
              Fin('pelvic', 0.3, 0.315, PELVICA, 0.06, 6)]),
    aspetto=Look(back=(0.06, 0.13, 0.14), flank=(0.48, 0.5, 0.5), belly=(0.7, 0.7, 0.68), fin=(0.2, 0.22, 0.2),
                 iris=(0.78, 0.72, 0.5), iris_dark=(0.1, 0.1, 0.08), metal=0.65, irid=0.45, squame=0.8, linea_laterale=0.0,
                 disegni=[Disegno('linea', colore=(0.08, 0.09, 0.09), forza=0.85, v=0.75, inclinazione=-1.6, larghezza=0.07, n=40,
                                  u0=0.2, u1=0.48),
                          Disegno('linea', colore=(0.08, 0.09, 0.09), forza=0.85, v=0.0, larghezza=0.09, n=48, u0=0.47, u1=0.99),
                          Disegno('macchia', colore=(0.02, 0.02, 0.025), forza=0.9, u=0.205, v=0.42, r=0.011),
                          Disegno('ventre', colore=(0.8, 0.82, 0.82), forza=0.5, v1=-0.4)]),
    extra=_lembi_suro,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=23, cucitura=(0.3, 0.56, -0.62), punti=9, marcio=0.42))


# ── Nasello Senza Naso (nasello, Merluccius merluccius) ──
# Lungo e slanciato, la testa grande e piatta sopra, la bocca larga con la mandibola che sporge; due dorsali (la
# prima corta e triangolare, la seconda lunghissima con l'incavo a metà), l'anale lunga uguale, la coda tronca;
# grigio acciaio sopra, argento sotto. «Il naso gli è caduto da tempo»: manca la punta del muso sopra la bocca
# (campo: un taglio storto e frastagliato), resta un moncherino di carne marcia con i due buchi del naso, come in
# un teschio, e la mascella di sotto che sporge con i denti.

_NARICI = [np.array((0.072, s * 0.0055, 0.011), F32) for s in (-1, 1)]
_NASO_BUCO = (np.array((0.058, -0.004, 0.008), F32), np.array((0.016, 0.013, 0.012), F32))   # la cavità: centro, raggi


def _naso_via(c):
    """< 0 nel pezzo di muso che non c'è più: sopra la linea della bocca, davanti a un taglio quasi dritto e
    frastagliato (appena più indietro in alto), più la cavità scavata nel moncherino, aperta in avanti e verso la
    camera. Serve al campo e al moncherino."""
    b = c.body
    n3 = c.P.sdf.Noise3(124)
    cb, rb = _NASO_BUCO

    def s(p):
        x, z = p[:, 0], p[:, 2]
        nz = n3(p, scale=0.006, octaves=3)
        ml = b.mouth_line(x)
        taglio = x - (0.062 + 0.22 * (z - ml)) - 0.005 * nz
        sopra = (ml + 0.0016) - z
        k0 = np.linalg.norm((p - cb) / rb, axis=1)
        k1 = np.linalg.norm((p - cb) / (rb * rb), axis=1)
        buco = k0 * (k0 - 1.0) / np.maximum(k1, 1e-6) + 0.002 * nz
        return np.minimum(np.maximum(taglio, sopra), np.maximum(buco, sopra)).astype(F32)
    return s


def _narici(p):
    """Le due narici scure in fondo alla cavità (< 0 dentro), lunghe verso l'interno."""
    d = np.full(len(p), 10.0, F32)
    for n in _NARICI:
        d = np.minimum(d, np.linalg.norm((p - n) / np.array((2.2, 1.0, 1.5), F32), axis=1) - 0.0032)
    return d


def _campo_nasello(c, f):
    sdf = c.P.sdf
    via = _naso_via(c)

    def g(p):
        d = sdf.smax(f(p), -via(p), 0.0015)
        return sdf.smax(d, -_narici(p), 0.0015).astype(F32)
    return g


def _moncherino_nasello(c):
    """La carne marcia sul taglio (una lastra sottile che lo ricopre, dentro il contorno della pelle, bucata dalle
    narici) e i denti aguzzi rimasti sulla mascella di sotto, che non mordono più niente."""
    P, b = c.P, c.body
    via = _naso_via(c)
    base = b.base()

    def f(q):
        d = np.maximum(np.abs(via(q) - 0.00045) - 0.00105, base(q) + 0.0007)
        return np.maximum(d, -_narici(q)).astype(F32)
    lo, hi = np.array((-0.01, -0.045, -0.035), F32), np.array((0.11, 0.045, 0.055), F32)
    c.obs.append(P.oggetto_sdf('Moncherino', f, lo, hi, _mat_carne_marcia(c, 'CarneNaso'), res=_res(c, 0.0005, 0.0008)))
    denti = P.dirty_teeth_material()
    for k, x in enumerate((0.008, 0.018, 0.029, 0.04, 0.051)):
        zl = float(b.mouth_line(np.array([x], F32))[0])
        for s in (-1, 1):
            y = s * float(b.surface_y(x, zl - 0.002)) * 0.72
            punta = (x + 0.003, y * 0.88, zl + 0.008 + 0.004 * (k % 2))
            c.obs.append(P.tooth(f'DenteNasello{k}_{s}', (x, y, zl - 0.0015), punta, 0.0021, denti, col=P.COL))


SPECIE['nasello_senza_naso'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.02, 0.01), (0.06, 0.029), (0.12, 0.048), (0.2, 0.062), (0.3, 0.07), (0.45, 0.07), (0.6, 0.062),
             (0.75, 0.049), (0.9, 0.034), (1, 0.03)],
        bot=[(0, -0.02), (0.03, -0.032), (0.08, -0.048), (0.15, -0.061), (0.25, -0.071), (0.38, -0.075), (0.5, -0.071),
             (0.65, -0.058), (0.8, -0.042), (0.92, -0.032), (1, -0.03)],
        w=[(0, 0.006), (0.05, 0.03), (0.15, 0.047), (0.3, 0.05), (0.5, 0.042), (0.75, 0.028), (1, 0.014)],
        eye_t=0.108, eye_z=0.024, eye_r=0.02, mouth_t=0.14, mouth_z0=-0.006, mouth_z1=-0.012, gill_t=0.26,
        fins=[Fin('dorsal', 0.3, 0.38, [(0, 0), (0.12, 0.9), (0.3, 1.0), (0.65, 0.55), (1, 0.08)], 0.08, 10, spiny=True),
              Fin('dorsal', 0.41, 0.96, [(0, 0), (0.03, 0.6), (0.2, 0.52), (0.4, 0.4), (0.55, 0.5), (0.8, 0.72), (0.95, 0.66),
                                        (1, 0.1)], 0.06, 40),
              Fin('anal', 0.45, 0.96, [(0, 0), (0.03, 0.55), (0.2, 0.48), (0.4, 0.38), (0.55, 0.48), (0.8, 0.68), (0.95, 0.62),
                                      (1, 0.1)], 0.055, 38),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.45, 0.0, 0.9), 0.16, 16),
              Fin('pectoral', 0.27, 0.285, [(0, 0), (0.45, 0.25), (1.0, 0.1), (0.8, -0.03), (0, -0.08)], 0.13, 11),
              Fin('pelvic', 0.22, 0.235, PELVICA, 0.07, 6)]),
    aspetto=Look(back=(0.12, 0.14, 0.16), flank=(0.5, 0.52, 0.54), belly=(0.74, 0.74, 0.73), fin=(0.22, 0.23, 0.25),
                 iris=(0.75, 0.72, 0.55), metal=0.55, irid=0.35, squame=0.7, linea_laterale=0.7, linea_v=(0.38, -0.3),
                 disegni=[Disegno('ventre', colore=(0.82, 0.83, 0.84), forza=0.5, v1=-0.35)]),
    campo=_campo_nasello, extra=_moncherino_nasello,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=24, cucitura=(0.32, 0.64, -0.6), punti=12, marcio=0.44))


# ── Tordo Torbido (tordo marvizzo, Labrus bergylta) ──
# Robusto, il muso appuntito con le labbra grosse, la dorsale lunga (spinosa davanti, più alta e tonda dietro),
# la coda tonda, il peduncolo alto; bruno-verde macchiettato di chiaro, a rete. «Occhi torbidi come l'acqua di
# una pozzanghera. Nel secchio fa le bolle»: occhi fangosi e velati, le bolle che escono dalla bocca.

def _campo_tordo(c, f):
    """Le labbra grosse: due cordoni di carne lungo il taglio della bocca, sopra e sotto (il taglio, che si fa
    dopo, passa in mezzo)."""
    b, sh, sdf = c.body, c.forma, c.P.sdf
    pezzi = []
    for s in (-1, 1):
        for dz, r in ((0.0052, 0.0056), (-0.0056, 0.006)):
            pts = []
            for x in np.linspace(0.002, sh.mouth_t * 0.95, 5):
                zl = float(b.mouth_line(np.array([x], F32))[0])
                pts.append(np.array((x, s * float(b.surface_y(x, zl + dz)) * 0.82, zl + dz), F32))
            for i in range(len(pts) - 1):
                pezzi.append(sdf.round_cone(pts[i], pts[i + 1], r, r * 0.92))
    labbra = sdf.union(*pezzi, k=0.003)
    xmax = sh.mouth_t + 0.02

    def g(p):
        d = f(p)
        m = p[:, 0] < xmax
        if m.any():
            d = d.copy()
            d[m] = sdf.smin(d[m], labbra(p[m]), 0.004)
        return d
    return g


def _mat_bolle(c):
    """Le bolle: un velo lattiginoso e iridescente, come la schiuma dell'acqua sporca (trasparenti del tutto non
    si vedrebbero sul fondo scuro)."""
    m = _gia(c, 'Bolle')
    if m:
        return m
    m, g = c.P.material('Bolle')
    g.output_material(g.principled(color=(0.78, 0.8, 0.74), rough=0.06, transmission=0.4, ior=1.3, spec=0.9, coat=1.0,
                                   coat_rough=0.02, thin_film=380.0))
    return m


def _tordo_torbido(c):
    """Gli occhi torbidi come una pozzanghera, e le bolle che salgono dalla bocca (con la schiuma sul labbro)."""
    P = c.P
    _occhi(c, _mat_occhio(c, 'OcchioPozzanghera', sclera=(0.3, 0.28, 0.19), sclera2=(0.44, 0.4, 0.28), iride=(0.38, 0.36, 0.24),
                          pupilla=(0.26, 0.25, 0.18), iride_r=0.7, pupilla_r=0.42, velo=0.8, velo_col=(0.48, 0.45, 0.32),
                          capillari=0.3))
    z0 = c.forma.mouth_z0
    # una fila che sale davanti al muso, sempre più grosse, e la schiuma sul labbro
    bolle = [(-0.008, -0.012, z0 + 0.004, 0.0048), (-0.018, -0.016, z0 + 0.019, 0.0062), (-0.026, -0.018, z0 + 0.04, 0.0078),
             (-0.033, -0.016, z0 + 0.066, 0.0092), (-0.043, -0.014, z0 + 0.097, 0.011), (-0.051, -0.018, z0 + 0.13, 0.0085),
             (-0.062, -0.012, z0 + 0.162, 0.0125), (0.005, -0.017, z0 - 0.005, 0.003), (0.013, -0.018, z0 - 0.003, 0.0026),
             (0.008, -0.02, z0 + 0.001, 0.0022), (0.019, -0.016, z0 - 0.006, 0.002)]
    C = np.array([b[:3] for b in bolle], F32)
    R = np.array([b[3] for b in bolle], F32)

    def f(q):
        d = np.full(len(q), 10.0, F32)
        for cc, rr in zip(C, R):
            d = np.minimum(d, np.abs(np.linalg.norm(q - cc, axis=1) - rr) - 0.0005)
        return d
    c.obs.append(P.oggetto_sdf('Bolle', f, C.min(0) - 0.015, C.max(0) + 0.015, _mat_bolle(c), res=0.0003))


SPECIE['tordo_torbido'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.02, 0.0), (0.05, 0.03), (0.1, 0.07), (0.18, 0.108), (0.3, 0.132), (0.45, 0.138), (0.6, 0.126),
             (0.75, 0.095), (0.88, 0.066), (1, 0.058)],
        bot=[(0, -0.035), (0.03, -0.055), (0.08, -0.085), (0.16, -0.113), (0.3, -0.133), (0.45, -0.133), (0.6, -0.118),
             (0.75, -0.09), (0.88, -0.065), (1, -0.058)],
        w=[(0, 0.012), (0.05, 0.04), (0.15, 0.062), (0.35, 0.068), (0.6, 0.055), (0.85, 0.032), (1, 0.02)],
        eye_t=0.12, eye_z=0.045, eye_r=0.022, mouth_t=0.06, mouth_z0=-0.025, mouth_z1=-0.03, gill_t=0.28,
        fins=[Fin('dorsal', 0.3, 0.88, [(0, 0), (0.03, 0.6), (0.1, 0.75), (0.5, 0.72), (0.62, 0.78), (0.8, 1.0), (0.95, 0.85),
                                       (1, 0.1)], 0.085, 30, spiny=True),
              Fin('anal', 0.64, 0.88, [(0, 0), (0.1, 0.7), (0.5, 0.95), (0.85, 0.85), (1, 0.1)], 0.08, 12),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.45, 0.95), 0.2, 18),
              Fin('pectoral', 0.3, 0.315, PETTORALE_TONDA, 0.11, 12),
              Fin('pelvic', 0.34, 0.355, PELVICA, 0.08, 6, spiny=True)]),
    aspetto=Look(back=(0.1, 0.12, 0.05), flank=(0.26, 0.22, 0.1), belly=(0.52, 0.42, 0.26), fin=(0.16, 0.15, 0.08),
                 iris=(0.7, 0.5, 0.25), metal=0.1, irid=0.1, squame=0.9, linea_laterale=0.0,
                 disegni=[Disegno('reticolo', colore=(0.06, 0.07, 0.03), forza=0.55, scala=70, larghezza=0.1),
                          Disegno('punti', colore=(0.78, 0.72, 0.5), forza=0.75, scala=170, r=0.16),
                          Disegno('macchie', colore=(0.45, 0.2, 0.08), forza=0.35, scala=25, r=0.35, seme=4)]),
    campo=_campo_tordo, extra=_tordo_torbido,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=25, cucitura=(0.34, 0.64, -0.55), punti=11, occhi=None, marcio=0.45))


# ── Sarcofago (sarago maggiore, Diplodus sargus) ──
# Sparide ovale e compresso, il muso appena appuntito; le bande verticali scure (forti e deboli alternate), la
# macchia nera sul peduncolo; grigio argento. «Bande nere come le fasce di una mummia. Ogni tanto una si scioglie,
# e sotto non c'è più il pesce»: le bande forti sono bende nere in rilievo che girano attorno al corpo; una si è
# srotolata e pende, e dove stava il pesce non c'è più (campo: una finestra da parte a parte).

_BENDE = [(0.25, 0.021), (0.37, 0.02), (0.61, 0.019), (0.73, 0.017), (0.85, 0.014)]   # (t, mezza larghezza)
_BENDA_SCIOLTA = (0.49, 0.026)
_BENDA_INCL = -0.025        # in cima le bende pendono appena in avanti


def _campo_sarcofago(c, f):
    """La finestra dove si è sciolta la benda: il pesce non c'è più, da parte a parte (bordi frastagliati)."""
    b, sdf = c.body, c.P.sdf
    n3 = sdf.Noise3(127)
    x0, hw = _BENDA_SCIOLTA

    def g(p):
        d = f(p)
        x = p[:, 0]
        zc, h, _ = b.section(np.clip(x, 0, 1))
        v = (p[:, 2] - zc) / h
        nz = n3(p, scale=0.01, octaves=3)
        fin = np.maximum(np.abs(x - x0 - _BENDA_INCL * v) - (hw + 0.004 * nz), (np.abs(v) - (0.62 + 0.08 * nz)) * h)
        return sdf.smax(d, -fin, 0.003).astype(F32)
    return g


def _mat_bende(c):
    """Le bende nere: tela vecchia a trama fitta, nera e grigia di polvere, opaca."""
    m = _gia(c, 'BendeNere')
    if m:
        return m
    m, g = c.P.material('BendeNere')
    co = g.texcoord('Object')
    _, w1 = g.wave(co, scale=260.0, kind='BANDS', axis='X', distortion=0.6)
    _, w2 = g.wave(co, scale=260.0, kind='BANDS', axis='Z', distortion=0.6)
    trama = g.mul(g.smoothstep(0.3, 0.7, w1), g.smoothstep(0.3, 0.7, w2))
    n = g.noise(co, scale=25.0, detail=5.0, rough=0.6)
    col = g.mix(g.smoothstep(0.4, 0.75, n.fac), (0.014, 0.013, 0.012), (0.04, 0.036, 0.031))
    col = g.mix(g.mul(trama, 0.45), col, (0.065, 0.06, 0.052))
    nrm = g.bump(g.add(trama, g.mul(n.fac, 0.5)), strength=0.35, distance=0.0012)
    g.output_material(g.principled(color=col, rough=0.9, normal=nrm, spec=0.25, sheen=0.25, sheen_tint=(0.35, 0.33, 0.3)))
    return m


def _bende_sarcofago(c):
    """Le bende che tengono (gusci sottili attorno al corpo, sfilacciati ai bordi) e quella sciolta che pende dal
    bordo di sotto della finestra, girandosi un poco."""
    P, b = c.P, c.body
    base = b.base()
    n3 = P.sdf.Noise3(227)
    mat = _mat_bende(c)

    def bende(q):
        x = q[:, 0]
        zc, h, _ = b.section(np.clip(x, 0, 1))
        v = (q[:, 2] - zc) / h
        nz = n3(q, scale=0.008, octaves=2)
        fin = np.full(len(q), 10.0, F32)
        for t, hw in _BENDE:
            fin = np.minimum(fin, np.abs(x - t - _BENDA_INCL * v) - (hw + 0.003 * nz))
        return np.maximum(np.abs(base(q) - 0.0022) - 0.0013, fin).astype(F32)
    lo, hi = b.bounds(pad=0.01, solo_corpo=True)
    c.obs.append(P.oggetto_sdf('Bende', bende, lo, hi, mat, res=_res(c, 0.0008, 0.0014)))
    # la benda sciolta: un nastro che pende dal bordo di sotto della finestra
    x0, hw = _BENDA_SCIOLTA
    zc0, h0, _ = _sezione(c, x0)
    z_su = zc0 - 0.6 * h0
    y_su = -float(b.surface_y(x0, z_su)) - 0.0015
    z_giu = zc0 - h0 - 0.15

    def nastro(q):
        x, y, z = q[:, 0], q[:, 1], q[:, 2]
        s = np.clip((z_su - z) / (z_su - z_giu), 0, 1)
        # cade ondeggiando, si scosta dal corpo verso la camera e si gira su sé stesso, come una stoffa
        xc = x0 + 0.012 * np.sin(s * 4.0) + 0.02 * s
        yc = y_su - 0.035 * s * s
        phi = 1.5 * s
        dx, dy = x - xc, y - yc
        a = dx * np.cos(phi) + dy * np.sin(phi)
        bb = -dx * np.sin(phi) + dy * np.cos(phi) - 0.003 * np.sin(s * 22.0) * np.cos(a * 90.0)
        larg = hw * (1 - 0.25 * s) + 0.002 * n3(q, scale=0.008, octaves=2)
        d = np.maximum(np.abs(a) - larg, np.abs(bb) - 0.0011)
        fondo = z_giu + 0.014 * n3(q * 1.7, scale=0.006, octaves=2)            # in fondo sfilacciata
        return np.maximum(d, np.maximum(z - z_su, fondo - z)).astype(F32)
    lo = np.array((x0 - 0.06, y_su - 0.07, z_giu - 0.025), F32)
    hi = np.array((x0 + 0.08, y_su + 0.03, z_su + 0.01), F32)
    c.obs.append(P.oggetto_sdf('BendaSciolta', nastro, lo, hi, mat, res=_res(c, 0.0006, 0.0009)))


SPECIE['sarcofago'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.02, 0.01), (0.05, 0.05), (0.1, 0.1), (0.18, 0.152), (0.3, 0.188), (0.42, 0.198), (0.55, 0.184),
             (0.7, 0.13), (0.85, 0.075), (0.95, 0.05), (1, 0.046)],
        bot=[(0, -0.035), (0.03, -0.06), (0.08, -0.09), (0.16, -0.128), (0.28, -0.163), (0.42, -0.173), (0.56, -0.158),
             (0.7, -0.114), (0.85, -0.068), (0.95, -0.048), (1, -0.046)],
        w=[(0, 0.008), (0.06, 0.032), (0.2, 0.056), (0.4, 0.062), (0.65, 0.048), (0.85, 0.024), (1, 0.014)],
        eye_t=0.15, eye_z=0.06, eye_r=0.029, mouth_t=0.06, mouth_z0=-0.03, mouth_z1=-0.04, gill_t=0.28,
        fins=[Fin('dorsal', 0.3, 0.86, [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.82), (0.8, 0.75), (0.95, 0.55), (1, 0.05)], 0.12, 24,
                  spiny=True),
              Fin('anal', 0.62, 0.86, [(0, 0), (0.12, 0.9), (0.6, 0.62), (0.95, 0.5), (1, 0.05)], 0.09, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.32), 0.26, 20, bordo=(0.04, 0.04, 0.045)),
              Fin('pectoral', 0.3, 0.32, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.18, 12),
              Fin('pelvic', 0.36, 0.38, PELVICA, 0.09, 7, spiny=True, colore=(0.06, 0.06, 0.065))]),
    aspetto=Look(back=(0.22, 0.24, 0.25), flank=(0.52, 0.54, 0.54), belly=(0.68, 0.68, 0.66), fin=(0.18, 0.18, 0.2),
                 iris=(0.72, 0.64, 0.42), metal=0.5, irid=0.3, squame=1.0,
                 disegni=[Disegno('bande', colore=(0.06, 0.06, 0.07), forza=0.45, n=5, u0=0.25, u1=0.85, larghezza=0.22,
                                  inclinazione=-0.03),
                          Disegno('macchia', colore=(0.02, 0.02, 0.025), forza=0.9, u=0.935, v=0.35, r=0.025, allungamento=1.3)]),
    campo=_campo_sarcofago, extra=_bende_sarcofago,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=27, cucitura=None, marcio=0.46))


# ── Gattomorto (gattuccio, Scyliorhinus canicula) ──
# Piccolo squalo slanciato, la testa corta e piatta, gli occhi da gatto (allungati, la pupilla a fessura), le
# due dorsali molto arretrate (la prima dietro le pelviche), la coda lunga e bassa, quasi orizzontale; sabbia con
# tante macchioline scure. «Fa il gatto morto»: a pancia all'aria, girato di sbieco (roll +150: si vedono il
# fianco destro con le macchie e un poco di dorso, la pancia chiara in alto), con la cucitura sul fianco destro
# vicino alla pancia (la famiglia la metterebbe sul sinistro, che resta nascosto) e gli occhi lattiginosi.

def _gatto_cucitura(c):
    """La cucitura sul fianco destro, bassa, vicino alla pancia: una spezzata fitta sulla pelle."""
    b = c.body
    pts = [b.superficie(float(t), float(-0.52 + 0.07 * math.sin(t * 23.0)), 1)[0] for t in np.linspace(0.23, 0.5, 160)]
    return np.array(pts, F32)


def _campo_gatto(c, f):
    return _solco(_strappi(c, f, seme=28, morsi=2, buchi=1), _gatto_cucitura(c))


def _gatto_morto(c):
    _occhi(c, _mat_occhio(c, 'OcchioGatto', sclera=(0.55, 0.55, 0.45), sclera2=(0.68, 0.66, 0.56), iride=(0.62, 0.62, 0.5),
                          pupilla=(0.3, 0.31, 0.28), iride_r=0.86, pupilla_r=0.3, fessura='slit_v', velo=0.45))
    _punti_cucitura(c, _gatto_cucitura(c), quanti=11, seme=28)


SPECIE['gattomorto'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.015, 0.011), (0.05, 0.025), (0.1, 0.037), (0.18, 0.047), (0.3, 0.054), (0.45, 0.053), (0.6, 0.046),
             (0.75, 0.034), (0.9, 0.022), (1, 0.016)],
        bot=[(0, -0.012), (0.03, -0.024), (0.08, -0.034), (0.16, -0.044), (0.3, -0.05), (0.45, -0.049), (0.6, -0.041),
             (0.75, -0.03), (0.9, -0.019), (1, -0.015)],
        w=[(0, 0.012), (0.04, 0.035), (0.1, 0.049), (0.2, 0.054), (0.35, 0.05), (0.55, 0.04), (0.75, 0.027), (0.9, 0.017),
           (1, 0.011)],
        eye_t=0.075, eye_z=0.013, eye_r=0.0115, eye_allungato=1.6,
        bocca='ventrale', mouth_a=0.06, mouth_t=0.1, mouth_z1=-0.022, mouth_z0=-0.022,
        branchie='fessure', gill_t=0.155, n_branchie=5, passo_branchie=0.014,
        fins=[Fin('dorsal', 0.6, 0.68, DORSALE_SQUALO, 0.055, 24, carnosa=True, spessore=0.005),
              Fin('dorsal', 0.77, 0.83, DORSALE_SQUALO, 0.045, 20, carnosa=True, spessore=0.004),
              Fin('anal', 0.66, 0.74, DORSALE_SQUALO, 0.035, 20, carnosa=True, spessore=0.004),
              # la coda lunga e bassa, appena alzata, con il lobo di sotto lungo e basso e la tacca in punta
              Fin('caudal', 1.0, 1.0, [(0, 0.15), (0.5, 0.32), (1.0, 0.5), (1.06, 0.34), (0.96, 0.12), (0.78, -0.1), (0.45, -0.36),
                                      (0.25, -0.33), (0.1, -0.12)], 0.3, 50, carnosa=True, spessore=0.005),
              Fin('pectoral', 0.18, 0.24, [(0, 0.08), (0.5, 0.12), (1.0, 0.0), (0.85, -0.12), (0.4, -0.16), (0, -0.12)], 0.12, 30,
                  carnosa=True, spessore=0.005, dir=(0.75, 0.3, -0.6)),
              Fin('pelvic', 0.42, 0.5, [(0, 0.05), (0.6, 0.07), (1.0, -0.02), (0.6, -0.14), (0, -0.12)], 0.07, 20, carnosa=True,
                  spessore=0.004)]),
    aspetto=Look(back=(0.2, 0.15, 0.1), flank=(0.32, 0.25, 0.17), belly=(0.74, 0.7, 0.62), fin=(0.2, 0.15, 0.1),
                 iris=(0.7, 0.65, 0.3), metal=0.0, irid=0.05, squame=0.0, linea_laterale=0.0, lucido=0.3, ruvido=0.5,
                 tinta_pinne=0.0,
                 disegni=[Disegno('punti', colore=(0.05, 0.035, 0.025), forza=0.9, scala=170, r=0.2, v0=-0.45),
                          Disegno('macchie', colore=(0.05, 0.035, 0.025), forza=0.85, scala=55, r=0.22, v0=-0.35, seme=2),
                          Disegno('punti', colore=(0.75, 0.7, 0.6), forza=0.4, scala=160, r=0.12, v0=-0.2, seme=5)]),
    campo=_campo_gatto, extra=_gatto_morto,
    ritratto=Ritratto(yaw=12.0, pitch=-4.0, roll=150.0),
    famiglia='zombie', piano='squalo',
    opzioni=dict(seed=28, cucitura=None, occhi=None, marcio=0.46))


# ── Corvina Becchina (corvina, Sciaena umbra) ──
# Il dorso arcuato a gobba e il ventre quasi dritto, il muso tondo e la bocca appena sotto; due dorsali unite (la
# prima alta e spinosa), l'anale corta, la coda tronca; bronzo scuro e lucido, le pelviche e l'anale nere. «Brontola
# come i becchini… la terra che cade sul legno»: terra di camposanto addosso, sul dorso, a zolle e briciole.

def _terra_corvina(c):
    P, b, sdf = c.P, c.body, c.P.sdf
    mat = _mat_grumi(c, 'TerraCamposanto', chiaro=(0.11, 0.08, 0.055), scuro=(0.03, 0.022, 0.015), scala=70.0, rough=0.95,
                     rilievo=0.7, chiazze=((0.2, 0.19, 0.17), 0.35))
    n3 = sdf.Noise3(129)
    ec, er, _ = b.occhi_lista()[0]

    def maschera(q):
        v = b.norm_v(q)
        nz = n3(q, scale=0.025, octaves=3)
        sopra = np.clip((v - 0.2) / 0.45, 0, 1)
        occhio = np.clip(np.linalg.norm(q - ec, axis=1) / er - 1.5, 0, 1)
        return (np.clip((nz + 0.25 * sopra - 0.12) / 0.08, 0, 1) * sopra * occhio).astype(F32)
    c.obs.append(_crosta(c, 'TerraCrosta', mat, 0.004, maschera))
    # le zolle: grumi grossi sul dorso e sulla testa, e le briciole che cadono di lato
    rng = np.random.default_rng(129)
    C, R = [], []
    for _ in range(16):
        t, v = rng.uniform(0.1, 0.8), rng.uniform(0.35, 0.98)
        p, n = b.superficie(t, v, -1)
        r = rng.uniform(0.007, 0.016)
        C.append(p + n * r * 0.35)
        R.append(r)
    for _ in range(10):
        t = rng.uniform(0.2, 0.7)
        zc, h, _ = _sezione(c, t)
        C.append(np.array((t, rng.uniform(-0.05, -0.01), zc - h - rng.uniform(0.01, 0.06)), F32))
        R.append(rng.uniform(0.0025, 0.0045))
    C, R = np.array(C, F32), np.array(R, F32)

    def zolle(q):
        d = np.full(len(q), 10.0, F32)
        for cc, rr in zip(C, R):
            d = sdf.smin(d, np.linalg.norm(q - cc, axis=1) - rr, 0.002)
        return d + 0.0035 * n3(q * 2.3, scale=0.006, octaves=3)
    c.obs.append(P.oggetto_sdf('Zolle', zolle, C.min(0) - 0.02, C.max(0) + 0.02, mat, res=_res(c, 0.0006, 0.0009)))


SPECIE['corvina_becchina'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.02, 0.008), (0.05, 0.04), (0.1, 0.08), (0.18, 0.12), (0.28, 0.145), (0.38, 0.15), (0.5, 0.138),
             (0.65, 0.105), (0.8, 0.07), (0.92, 0.05), (1, 0.046)],
        bot=[(0, -0.03), (0.03, -0.05), (0.08, -0.072), (0.16, -0.09), (0.3, -0.1), (0.45, -0.1), (0.6, -0.09), (0.75, -0.07),
             (0.88, -0.052), (1, -0.046)],
        w=[(0, 0.01), (0.05, 0.035), (0.15, 0.055), (0.35, 0.062), (0.6, 0.05), (0.85, 0.03), (1, 0.018)],
        eye_t=0.1, eye_z=0.028, eye_r=0.02, mouth_t=0.065, mouth_z0=-0.03, mouth_z1=-0.04, gill_t=0.26,
        fins=[Fin('dorsal', 0.3, 0.45, [(0, 0), (0.1, 0.9), (0.25, 1.0), (0.6, 0.65), (0.9, 0.25), (1, 0.18)], 0.12, 10, spiny=True),
              Fin('dorsal', 0.45, 0.86, [(0, 0.18), (0.05, 0.6), (0.3, 0.65), (0.8, 0.55), (1, 0.05)], 0.07, 26),
              Fin('anal', 0.66, 0.78, [(0, 0), (0.12, 0.9), (0.5, 0.85), (1, 0.06)], 0.07, 9, colore=(0.025, 0.022, 0.02)),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.5, 0.0, 0.9), 0.18, 18),
              Fin('pectoral', 0.27, 0.285, PETTORALE, 0.11, 12),
              Fin('pelvic', 0.3, 0.315, PELVICA, 0.08, 6, spiny=True, colore=(0.025, 0.022, 0.02))]),
    aspetto=Look(back=(0.06, 0.045, 0.028), flank=(0.15, 0.105, 0.055), belly=(0.3, 0.25, 0.17), fin=(0.06, 0.045, 0.035),
                 iris=(0.75, 0.6, 0.3), metal=0.6, irid=0.4, squame=1.0, linea_laterale=0.6, linea_v=(0.5, -0.45),
                 disegni=[Disegno('sfumatura', colore=(0.3, 0.2, 0.08), forza=0.45, v0=-0.3, v1=0.4, larghezza=0.3)]),
    extra=_terra_corvina,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=29, cucitura=(0.3, 0.62, -0.58), punti=12, marcio=0.45))


# ── Palombra (palombo, Mustelus mustelus) ──
# Squalo slanciato tutto grigio, il muso lungo e tondo, gli occhi grandi e ovali; due dorsali quasi uguali, la
# coda con il lobo di sotto piccolo, niente macchie. «Grigio come un cane vecchio… ti segue»: grigio spento e
# opaco, il muso ingrigito come quello dei cani vecchi, gli occhi velati di azzurro che guardano te.

def _campo_palombra(c, f):
    return _strappi(c, f, seme=30, morsi=2, buchi=1)


def _occhi_cane(c):
    _occhi(c, _mat_occhio(c, 'OcchioCaneVecchio', sclera=(0.2, 0.22, 0.25), sclera2=(0.3, 0.32, 0.36), iride=(0.36, 0.4, 0.46),
                          pupilla=(0.52, 0.57, 0.62), iride_r=0.78, pupilla_r=0.42, velo=0.7, velo_col=(0.7, 0.76, 0.82),
                          capillari=0.35),
           guarda=(-0.3, -1.0, 0.05))


SPECIE['palombra'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.02, 0.01), (0.06, 0.025), (0.12, 0.039), (0.22, 0.051), (0.35, 0.057), (0.5, 0.053), (0.65, 0.043),
             (0.8, 0.03), (0.92, 0.02), (1, 0.016)],
        bot=[(0, -0.012), (0.03, -0.022), (0.08, -0.033), (0.18, -0.045), (0.32, -0.053), (0.46, -0.051), (0.6, -0.041),
             (0.75, -0.028), (0.9, -0.018), (1, -0.015)],
        w=[(0, 0.005), (0.04, 0.022), (0.12, 0.038), (0.3, 0.048), (0.5, 0.043), (0.7, 0.03), (0.9, 0.017), (1, 0.011)],
        eye_t=0.078, eye_z=0.01, eye_r=0.0135, eye_allungato=1.45,
        bocca='ventrale', mouth_a=0.065, mouth_t=0.105, mouth_z1=-0.024, mouth_z0=-0.024,
        branchie='fessure', gill_t=0.16, n_branchie=5, passo_branchie=0.015,
        fins=[Fin('dorsal', 0.33, 0.43, DORSALE_SQUALO, 0.075, 30, carnosa=True, spessore=0.006),
              Fin('dorsal', 0.62, 0.71, DORSALE_SQUALO, 0.062, 26, carnosa=True, spessore=0.005),
              Fin('anal', 0.68, 0.74, DORSALE_SQUALO, 0.035, 16, carnosa=True, spessore=0.003),
              Fin('caudal', 1.0, 1.0, coda_eterocerca(lobo=1.0, alzata=1.3, lobo_basso=0.35, basso=0.8), 0.25, 50, carnosa=True,
                  spessore=0.006),
              Fin('pectoral', 0.2, 0.25, [(0, 0.07), (0.5, 0.08), (1.0, -0.04), (0.85, -0.12), (0.4, -0.15), (0, -0.12)], 0.16, 30,
                  carnosa=True, spessore=0.005, dir=(0.75, 0.3, -0.6)),
              Fin('pelvic', 0.5, 0.56, [(0, 0.05), (0.6, 0.06), (1.0, -0.02), (0.6, -0.12), (0, -0.1)], 0.06, 20, carnosa=True,
                  spessore=0.004)]),
    aspetto=Look(back=(0.075, 0.075, 0.078), flank=(0.17, 0.17, 0.175), belly=(0.68, 0.67, 0.64), fin=(0.1, 0.1, 0.105),
                 iris=(0.3, 0.32, 0.3), metal=0.05, irid=0.05, squame=0.0, linea_laterale=0.0, lucido=0.2, ruvido=0.55,
                 disegni=[Disegno('sfumatura', colore=(0.5, 0.5, 0.48), forza=0.75, u1=0.085, v0=-0.2, larghezza=0.04),
                          Disegno('punti', colore=(0.4, 0.4, 0.38), forza=0.25, scala=200, r=0.1)]),
    campo=_campo_palombra, extra=_occhi_cane,
    famiglia='zombie', piano='squalo',
    opzioni=dict(seed=30, cucitura=(0.28, 0.55, -0.5), punti=12, occhi=None, marcio=0.5))


# ── Pastinaca Putrida (pastinaca, Dasyatis pastinaca) ──
# Come la razza, costruita con il dorso verso la camera: il disco a rombo arrotondato, largo quanto lungo, con
# le pelviche piccole dietro; niente dorsali né caudale: la coda è una frusta lunga una volta e mezza il disco.
# «La senti prima di vederla. Il pungiglione è l'unica cosa che funziona»: il disco marcio e cascante (campo: i
# bordi pendono, mollicci, e si sfrangiano in buchi), il pungiglione intatto, lucido e seghettato (un oggetto a
# parte con il suo materiale, al posto della Spine della prova).

def _campo_pastinaca(c, f):
    sdf = c.P.sdf
    n3 = sdf.Noise3(141)

    def g(p):
        z = np.abs(p[:, 2])
        x = p[:, 0]
        fuori = np.clip(z - 0.07, 0, None)
        # i bordi delle ali cascano verso il fondo (+Y, il lato del ventre), ondulati come uno straccio bagnato
        cade = 1.5 * fuori ** 2 + 0.006 * np.sin(x * 34.0 + z * 20.0) * np.clip(fuori / 0.06, 0, 1)
        q = p.copy()
        q[:, 1] -= cade
        d = f(q)
        # i buchi del marcio, fitti verso il bordo
        nz = n3(p, scale=0.014, octaves=3)
        soglia = 0.24 + 0.5 * (1 - np.clip((z - 0.1) / 0.08, 0, 1))
        return np.maximum(d, (nz - soglia) * 0.03).astype(F32)
    return g


def _pungiglione(c):
    """Il pungiglione: una lama piatta coricata all'indietro sulla coda, appena sollevata, con i dentini sui due
    bordi che puntano verso la radice; lucido."""
    P, b, sdf = c.P, c.body, c.P.sdf
    p0, n0 = b.superficie(0.57, 0.45, -1)
    e1 = np.array((1.0, 0.0, 0.06), F32) + n0 * 0.05
    e1 /= np.linalg.norm(e1)
    e3 = n0 - e1 * float(n0 @ e1)
    e3 /= np.linalg.norm(e3)
    e2 = np.cross(e3, e1).astype(F32)
    o = p0 + n0 * 0.0016
    L, W, T = 0.11, 0.0062, 0.0021

    def lama(q):
        r = q - o
        s, u, h = r @ e1, r @ e2, r @ e3
        k = np.clip(s / L, 0, 1)
        d = np.maximum(np.abs(u) - (W * (1 - k) ** 0.75 + 0.0003), np.abs(h) - (T * (1 - 0.6 * k) + 0.0002))
        return sdf.smax(d, np.maximum(-s, s - L), 0.0006)
    A, B, R1, R2 = [], [], [], []
    for i in range(18):
        s = L * (0.12 + 0.78 * i / 17)
        hw = W * (1 - s / L) ** 0.75
        for sg in (-1, 1):
            a = o + e1 * s + e2 * sg * hw * 0.8
            A.append(a)
            B.append(a + e2 * sg * 0.0032 - e1 * 0.0034)
            R1.append(0.0012)
            R2.append(0.0002)
    fd, _, _ = P.campo_coni(A, B, R1, R2)
    ends = np.array([o, o + e1 * L], F32)
    lo, hi = ends.min(0) - 0.014, ends.max(0) + 0.014
    mat = P.materiale('Pungiglione', (0.3, 0.26, 0.19), rough=0.1, coat=1.0, metal=0.25, sss=0.1)
    c.obs.append(P.oggetto_sdf('Pungiglione', lambda q: np.minimum(lama(q), fd(q)).astype(F32), lo, hi, mat,
                               res=_res(c, 0.0003, 0.0005)))


SPECIE['pastinaca_putrida'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.04, 0.025), (0.1, 0.042), (0.2, 0.05), (0.3, 0.043), (0.38, 0.026), (0.44, 0.012), (0.55, 0.0075),
             (0.75, 0.005), (0.9, 0.003), (1, 0.0012)],
        bot=[(0, 0.0), (0.04, -0.025), (0.1, -0.042), (0.2, -0.05), (0.3, -0.043), (0.38, -0.026), (0.44, -0.012),
             (0.55, -0.0075), (0.75, -0.005), (0.9, -0.003), (1, -0.0012)],
        w=[(0, 0.003), (0.05, 0.011), (0.15, 0.024), (0.25, 0.027), (0.35, 0.021), (0.42, 0.012), (0.5, 0.0075), (0.7, 0.005),
           (0.9, 0.0028), (1, 0.0012)],
        eye_t=0.105, eye_z=0.0, eye_r=0.0085,
        occhi=[(0.105, 0.026, 0.0085, -1), (0.105, -0.026, 0.0085, -1)], spiracoli=0.0055,
        bocca='nessuna', branchie='nessuna',
        disco=Disco(contorno=[(0, 0.0), (0.02, 0.035), (0.06, 0.1), (0.11, 0.17), (0.16, 0.215), (0.2, 0.228), (0.24, 0.215),
                              (0.3, 0.155), (0.35, 0.095), (0.38, 0.07), (0.41, 0.062), (0.44, 0.045), (0.46, 0.0), (1.0, 0.0)],
                    spessore=[(0, 0.003), (0.08, 0.01), (0.2, 0.014), (0.32, 0.01), (0.42, 0.004), (0.47, 0.001), (1.0, 0.001)]),
        spine=[Spine(0.17, 0.36, 0.0, 0.0, 6, lunghezza=0.004, raggio=0.0028, lati='sinistro', inclinazione=0.5, fila=True)]),
    aspetto=Look(back=(0.085, 0.075, 0.05), flank=(0.12, 0.1, 0.07), belly=(0.82, 0.8, 0.74), fin=(0.08, 0.07, 0.05),
                 iris=(0.55, 0.5, 0.3), iris_dark=(0.1, 0.09, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.25, ruvido=0.5,
                 disegni=[Disegno('marmo', colore=(0.035, 0.03, 0.02), forza=0.7, scala=60, r=0.45),
                          Disegno('marmo', colore=(0.03, 0.028, 0.02), forza=0.5, scala=150, r=0.3)]),
    campo=_campo_pastinaca, extra=_pungiglione,
    famiglia='zombie', piano='razza',
    opzioni=dict(seed=31, cucitura=(0.13, 0.4, -0.5), punti=11, marcio=0.4))


# ── Castagna Marcia (pesce castagna, Brama brama) ──
# Alto e compresso, il profilo della testa ripido, l'occhio grande e la bocca obliqua; dorsale e anale lunghe
# con il lobo davanti alto e falcato, le pettorali lunghe a falce, la coda profondamente forcuta; nero bruno e
# lucido. «Nera e lucida come una castagna… piena di piccoli vermi bianchi che ballano»: buchi molli sul fianco
# da cui escono i vermetti bianchi, piegati in tutte le direzioni.

_CASTAGNA_BUCHI = [(0.3, 0.25, 0.01), (0.42, -0.2, 0.012), (0.52, 0.42, 0.009), (0.6, -0.45, 0.011), (0.7, 0.1, 0.0095),
                   (0.38, -0.62, 0.0085), (0.24, -0.3, 0.008), (0.5, 0.05, 0.0085), (0.78, -0.25, 0.0075)]


def _buchi_castagna(c):
    """I buchi da cui escono i vermi: (punto sulla pelle, normale, raggio)."""
    return [(*c.body.superficie(t, v, -1), r) for t, v, r in _CASTAGNA_BUCHI]


def _campo_castagna(c, f):
    sdf = c.P.sdf
    buchi = _buchi_castagna(c)
    n3 = sdf.Noise3(132)

    def g(p):
        d = f(p)
        nz = n3(p, scale=0.004, octaves=2)
        for cen, n, r in buchi:
            # un cratere molle che affonda nella carne, con il bordo sbrecciato
            d = sdf.smax(d, -(np.linalg.norm(p - (cen + n * r * 0.25), axis=1) - r * (1 + 0.25 * nz)), 0.002)
        return d.astype(F32)
    return g


def _vermi_castagna(c):
    P = c.P
    rng = np.random.default_rng(232)
    m = _gia(c, 'Vermi')
    if not m:
        m, g = P.material('Vermi')
        co = g.texcoord('Object')
        n = g.noise(co, scale=400.0, detail=2.0)
        g.output_material(g.principled(color=g.mix(g.mul(n.fac, 0.3), (0.86, 0.82, 0.7), (0.7, 0.64, 0.5)), rough=0.3, coat=0.7,
                                       coat_rough=0.1, sss=0.5, sss_radius=(1.0, 0.8, 0.5), sss_scale=0.002))
    buchi = _buchi_castagna(c)
    # l'orlo di carne marcia attorno ai buchi (si vede sul nero)
    C0 = np.array([p for p, _, _ in buchi], F32)
    R0 = np.array([r for _, _, r in buchi], F32)

    def orlo(q):
        out = np.zeros(len(q), F32)
        for cc, rr in zip(C0, R0):
            dist = np.linalg.norm(q - cc, axis=1)
            # un anello: niente dentro il buco, pieno sul bordo, sfuma fuori
            out = np.maximum(out, np.clip((dist - rr * 1.02) / (rr * 0.15), 0, 1) * np.clip(1.0 - (dist - rr) / (rr * 0.9), 0, 1))
        return out
    c.obs.append(_crosta(c, 'OrloBuchi', _mat_carne_marcia(c), 0.0012, orlo, res=_res(c, 0.0006, 0.001)))
    A, B, R1, R2 = [], [], [], []
    for cen, n, r in buchi:
        for _ in range(int(rng.integers(3, 7))):
            # dal fondo del buco verso fuori, piegati a caso: chi esce dritto, chi si arriccia, chi ricade sulla pelle
            a = cen - n * r * 0.5 + rng.normal(0, r * 0.25, 3).astype(F32)
            d = n + rng.normal(0, 0.55, 3).astype(F32)
            d /= np.linalg.norm(d)
            curva = rng.normal(0, 60.0, 3).astype(F32)
            L, rr = rng.uniform(0.018, 0.04), rng.uniform(0.0024, 0.0033)
            pts = [a]
            for _k in range(10):
                pts.append(pts[-1] + d * L / 10)
                d = d + curva * L / 10
                d /= np.linalg.norm(d)
            for k in range(10):
                A.append(pts[k])
                B.append(pts[k + 1])
                R1.append(rr * (0.7 + 0.3 * math.sin(math.pi * k / 10)))
                R2.append(rr * (0.7 + 0.3 * math.sin(math.pi * (k + 1) / 10)))
    f, lo, hi = P.campo_coni(A, B, R1, R2)
    c.obs.append(P.oggetto_sdf('Vermi', f, lo, hi, m, res=_res(c, 0.0004, 0.0006)))


SPECIE['castagna_marcia'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.015, 0.02), (0.04, 0.07), (0.08, 0.125), (0.14, 0.17), (0.22, 0.2), (0.32, 0.21), (0.45, 0.2), (0.6, 0.16),
             (0.75, 0.105), (0.88, 0.058), (0.96, 0.04), (1, 0.036)],
        bot=[(0, -0.04), (0.03, -0.08), (0.08, -0.13), (0.16, -0.18), (0.28, -0.205), (0.4, -0.205), (0.55, -0.175), (0.7, -0.12),
             (0.85, -0.065), (0.95, -0.04), (1, -0.036)],
        w=[(0, 0.008), (0.06, 0.03), (0.2, 0.05), (0.4, 0.054), (0.65, 0.04), (0.85, 0.02), (1, 0.012)],
        eye_t=0.11, eye_z=0.045, eye_r=0.03, mouth_t=0.08, mouth_z0=-0.01, mouth_z1=-0.055, gill_t=0.26,
        fins=[Fin('dorsal', 0.32, 0.9, [(0, 0), (0.06, 0.95), (0.12, 1.0), (0.2, 0.55), (0.35, 0.4), (0.8, 0.35), (0.95, 0.3), (1, 0.05)],
                  0.2, 36),
              Fin('anal', 0.45, 0.9, [(0, 0), (0.07, 0.95), (0.14, 1.0), (0.24, 0.5), (0.4, 0.38), (0.8, 0.33), (0.95, 0.28),
                                     (1, 0.05)], 0.17, 30),
              Fin('caudal', 1.0, 1.0, coda_forcuta(2.3, 0.25, 1.1), 0.3, 22),
              Fin('pectoral', 0.26, 0.28, [(0, 0), (0.4, 0.22), (1.0, 0.06), (0.85, -0.02), (0, -0.06)], 0.28, 14),
              Fin('pelvic', 0.3, 0.315, PELVICA, 0.06, 6)]),
    aspetto=Look(back=(0.022, 0.016, 0.012), flank=(0.045, 0.034, 0.025), belly=(0.07, 0.055, 0.042), fin=(0.1, 0.08, 0.062),
                 iris=(0.6, 0.55, 0.4), metal=0.35, irid=0.25, squame=0.6, linea_laterale=0.0, lucido=0.95,
                 disegni=[Disegno('sfumatura', colore=(0.12, 0.07, 0.035), forza=0.5, v0=-0.4, v1=0.5, larghezza=0.3)]),
    campo=_campo_castagna, extra=_vermi_castagna,
    famiglia='zombie', piano='alto',
    opzioni=dict(seed=32, cucitura=(0.3, 0.62, -0.78), punti=11, marcio=0.55))


# ── Ombrina Smorta (ombrina, Umbrina cirrosa) ──
# Allungata, il dorso arcuato e il ventre quasi dritto, la bocca sotto il muso con il barbiglio corto sotto il
# mento; due dorsali unite (la prima triangolare e spinosa), l'anale corta, la coda tronca; argento dorato con le
# righe oblique ondulate dorate e azzurre. «La vescica non ce l'ha più, ma il tamburo continua»: la pancia aperta
# e vuota (campo: una finestra frastagliata sul fianco sinistro e dentro niente), le costole sulla parete di
# fronte, e le corde tese attraverso la finestra come quelle di un tamburo.

_OMBRINA_FINESTRA = (0.44, 0.115, -0.42, 0.38)      # centro in t, mezza lunghezza, centro in v, mezza altezza in v


def _ombrina_finestra(c):
    """< 0 dentro la finestra della pancia (un'ellisse frastagliata in t, v) sulla metà sinistra del corpo."""
    b = c.body
    n3 = c.P.sdf.Noise3(133)
    tc, a, vc, bv = _OMBRINA_FINESTRA

    def s(p):
        x = p[:, 0]
        zc, h, w = b.section(np.clip(x, 0, 1))
        v = (p[:, 2] - zc) / h
        e = np.hypot((x - tc) / a, (v - vc) / bv) - 1.0 - 0.12 * n3(p, scale=0.012, octaves=3)
        return np.maximum(e * 0.04, p[:, 1] + 0.3 * w).astype(F32)
    return s


_OMBRINA_PARETE = 0.008    # lo spessore della parete della pancia (più della griglia delle anteprime, se no si buca)


def _ombrina_cavita(c):
    """< 0 nella pancia vuota: la carne più in fondo della parete, fra t 0.29 e 0.6, sotto v 0.2."""
    b = c.body
    base = b.base()

    def s(p):
        x = p[:, 0]
        zc, h, _ = b.section(np.clip(x, 0, 1))
        v = (p[:, 2] - zc) / h
        return np.maximum(np.maximum(base(p) + _OMBRINA_PARETE, np.maximum(0.29 - x, x - 0.6)), (v - 0.2) * h).astype(F32)
    return s


def _campo_ombrina(c, f):
    sdf = c.P.sdf
    cav, fin = _ombrina_cavita(c), _ombrina_finestra(c)

    def g(p):
        d = sdf.smax(f(p), -cav(p), 0.002)
        return sdf.smax(d, -fin(p), 0.0015).astype(F32)
    return g


def _tamburo_ombrina(c):
    """Dentro: la parete della pancia di carne scura (una pellicola sulla parete della cavità, tranne dove c'è la
    finestra) e le costole sulla parete di fronte; fuori: le corde tese a zig-zag attraverso la finestra."""
    P, b = c.P, c.body
    cav, fin = _ombrina_cavita(c), _ombrina_finestra(c)

    def parete(q):
        return np.maximum(np.abs(cav(q) - 0.0005) - 0.0008, -fin(q)).astype(F32)
    lo, hi = b.bounds(pad=0.005, solo_corpo=True)
    lo[0], hi[0] = 0.27, 0.62
    c.obs.append(P.oggetto_sdf('PareteVuota', parete, lo, hi, _mat_carne_marcia(c, 'CarneScura'), res=_res(c, 0.0008, 0.0014)))
    # le costole, sulla parete di destra (quella che si vede dalla finestra)
    A, B, R1, R2 = [], [], [], []
    for x in np.arange(0.31, 0.59, 0.035):
        zc, h, w = _sezione(c, float(x))
        wi, hi_ = w - _OMBRINA_PARETE - 0.0008, h - _OMBRINA_PARETE - 0.0008
        pts = [np.array((x + 0.01 * k / 8, wi * math.cos(math.radians(70 - 155 * k / 8)),
                         zc + hi_ * math.sin(math.radians(70 - 155 * k / 8))), F32) for k in range(9)]
        for k in range(8):
            A.append(pts[k])
            B.append(pts[k + 1])
            R1.append(0.0017)
            R2.append(0.0015)
    fc, lo2, hi2 = P.campo_coni(A, B, R1, R2)
    c.obs.append(P.oggetto_sdf('CostoleOmbrina', fc, lo2, hi2, P.bone_material('OssoOmbrina', dirt=0.5), res=_res(c, 0.0005, 0.0008)))
    # le corde del tamburo: a zig-zag dal bordo di sopra a quello di sotto della finestra
    tc, a, vc, bv = _OMBRINA_FINESTRA
    corda = P.materiale('CordaTamburo', (0.36, 0.3, 0.2), rough=0.6, coat=0.2)
    estremi = []
    for j in range(9):
        x = tc - 0.8 * a + 1.6 * a * j / 8
        u = (x - tc) / a
        alto = j % 2 == 0
        v = vc + (1 if alto else -1) * bv * 1.08 * math.sqrt(max(1 - u * u, 0.05))
        p, n = b.superficie(float(x), float(v), -1)
        estremi.append(p + n * 0.0012)
    for k in range(len(estremi) - 1):
        f = P.strand(estremi[k], estremi[k + 1], 0.003, r=0.0014)
        lo3 = np.minimum(estremi[k], estremi[k + 1]) - 0.01
        hi3 = np.maximum(estremi[k], estremi[k + 1]) + 0.01
        c.obs.append(P.oggetto_sdf(f'Corda{k}', f, lo3, hi3, corda, res=0.0005))


SPECIE['ombrina_smorta'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.02, 0.006), (0.05, 0.035), (0.1, 0.07), (0.18, 0.1), (0.28, 0.12), (0.4, 0.126), (0.55, 0.115),
             (0.7, 0.085), (0.85, 0.055), (0.95, 0.04), (1, 0.037)],
        bot=[(0, -0.03), (0.03, -0.05), (0.08, -0.068), (0.16, -0.082), (0.3, -0.09), (0.45, -0.088), (0.6, -0.078), (0.75, -0.06),
             (0.88, -0.045), (1, -0.037)],
        w=[(0, 0.01), (0.05, 0.035), (0.15, 0.054), (0.35, 0.06), (0.6, 0.048), (0.85, 0.026), (1, 0.016)],
        eye_t=0.1, eye_z=0.03, eye_r=0.02, mouth_t=0.06, mouth_z0=-0.03, mouth_z1=-0.04, gill_t=0.25,
        filamenti=[Filamento(t=0.014, v=-0.95, lunghezza=0.024, raggio=0.0036, dir=(0.3, 0.0, -1.0), curva=(3.0, 0.0, 0.0),
                             lati='centro', punta=0.55)],
        fins=[Fin('dorsal', 0.29, 0.42, [(0, 0), (0.1, 0.95), (0.3, 1.0), (0.7, 0.55), (1, 0.15)], 0.11, 10, spiny=True),
              Fin('dorsal', 0.43, 0.86, [(0, 0.15), (0.05, 0.6), (0.3, 0.65), (0.8, 0.55), (1, 0.05)], 0.07, 28),
              Fin('anal', 0.67, 0.78, [(0, 0), (0.12, 0.9), (0.5, 0.8), (1, 0.06)], 0.065, 8),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.45, 0.06, 0.85), 0.18, 18),
              Fin('pectoral', 0.25, 0.265, PETTORALE, 0.12, 12),
              Fin('pelvic', 0.29, 0.305, PELVICA, 0.08, 6, spiny=True)]),
    aspetto=Look(back=(0.16, 0.15, 0.1), flank=(0.44, 0.4, 0.28), belly=(0.64, 0.62, 0.55), fin=(0.18, 0.16, 0.12),
                 iris=(0.8, 0.68, 0.38), metal=0.55, irid=0.35, squame=0.9, linea_laterale=0.5,
                 disegni=[Disegno('strisce', colore=(0.5, 0.36, 0.1), forza=0.65, n=11, v0=-0.75, v1=0.95, larghezza=0.045, onda=0.03,
                                  inclinazione=0.85),
                          Disegno('strisce', colore=(0.6, 0.64, 0.7), forza=0.35, n=11, v0=-0.72, v1=0.98, larghezza=0.025, onda=0.03,
                                  inclinazione=0.85)]),
    campo=_campo_ombrina, extra=_tamburo_ombrina,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=33, cucitura=None, marcio=0.45))


# ── Branzombi (spigola, Dicentrarchus labrax) ──
# Slanciata, la testa lunga con la bocca grande, l'opercolo con le due spine piatte; due dorsali ben separate,
# la coda appena incavata; argento con il dorso grigio-azzurro, la macchia scura sull'opercolo. «Il pesce più
# bello del secchio, se non fosse per gli occhi bianchi come il latte. Continua a boccheggiare»: poco marcio (una
# cucitura corta e pulita), gli occhi bianchissimi, la bocca aperta.

def _occhi_latte(c):
    _occhi(c, _mat_occhio(c, 'OcchioLatte', sclera=(0.86, 0.85, 0.8), sclera2=(0.93, 0.92, 0.88), iride=(0.84, 0.84, 0.8),
                          pupilla=(0.76, 0.77, 0.74), iride_r=0.7, pupilla_r=0.32, velo=0.9, velo_col=(0.95, 0.95, 0.93),
                          capillari=0.25))


SPECIE['branzombi'] = Specie(
    forma=Shape(
        top=[(0, -0.008), (0.02, 0.012), (0.05, 0.03), (0.1, 0.055), (0.18, 0.078), (0.3, 0.092), (0.42, 0.094), (0.55, 0.085),
             (0.7, 0.062), (0.85, 0.04), (0.95, 0.03), (1, 0.028)],
        bot=[(0, -0.018), (0.03, -0.032), (0.08, -0.05), (0.16, -0.07), (0.28, -0.085), (0.42, -0.086), (0.56, -0.076),
             (0.7, -0.058), (0.85, -0.038), (0.95, -0.03), (1, -0.028)],
        w=[(0, 0.006), (0.05, 0.028), (0.15, 0.046), (0.35, 0.052), (0.6, 0.042), (0.85, 0.022), (1, 0.013)],
        eye_t=0.095, eye_z=0.022, eye_r=0.02, mouth_t=0.1, mouth_z0=-0.01, mouth_z1=-0.022, bocca_aperta=18.0, gill_t=0.25,
        spine=[Spine(0.255, 0.262, 0.06, 0.32, 2, lunghezza=0.012, raggio=0.0032, inclinazione=0.92, fila=True, seme=3)],
        fins=[Fin('dorsal', 0.3, 0.42, [(0, 0), (0.12, 0.9), (0.3, 1.0), (0.7, 0.55), (1, 0.1)], 0.1, 9, spiny=True),
              Fin('dorsal', 0.5, 0.68, [(0, 0), (0.1, 0.9), (0.35, 0.8), (0.8, 0.55), (1, 0.06)], 0.07, 13),
              Fin('anal', 0.56, 0.7, [(0, 0), (0.12, 0.85), (0.4, 0.78), (0.8, 0.5), (1, 0.06)], 0.065, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.45, 0.45), 0.22, 18),
              Fin('pectoral', 0.26, 0.275, PETTORALE, 0.12, 12),
              Fin('pelvic', 0.3, 0.315, PELVICA, 0.07, 6, spiny=True)]),
    aspetto=Look(back=(0.12, 0.15, 0.18), flank=(0.58, 0.6, 0.62), belly=(0.8, 0.8, 0.79), fin=(0.22, 0.24, 0.26),
                 iris=(0.8, 0.8, 0.78), metal=0.75, irid=0.45, squame=1.0, linea_laterale=0.8, linea_v=(0.42, -0.4),
                 bocca_col=(0.34, 0.2, 0.2),
                 disegni=[Disegno('ventre', colore=(0.86, 0.87, 0.88), forza=0.6, v1=-0.35),
                          Disegno('macchia', colore=(0.05, 0.06, 0.07), forza=0.7, u=0.235, v=0.3, r=0.009)]),
    extra=_occhi_latte,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=34, cucitura=(0.4, 0.58, -0.62), punti=7, occhi=None, marcio=0.62))


# ── Murena Murata (murena, Muraena helena) ──
# Lunghissima, senza pettorali; dorsale, coda e anale sono una pinna sola di pelle spessa (carnose, con i
# disegni del corpo: tinta_pinne=0); la bocca aperta con le zanne (extra); l'asse a S (piega). «Sempre nella
# stessa fessura, con la bocca aperta… hanno chiuso la fessura, una pietra alla volta»: le pietre e la malta del
# muretto che l'ha murata, rimaste attaccate attorno alla metà di dietro.

def _denti_murena(c):
    """I denti a zanna nella bocca aperta (aiuto comune: denti_mascelle, con la stessa apertura della forma)."""
    c.obs += c.P.denti_mascelle(c.body, n=7, lunghezza=0.0055, zanne=(1, 2), apertura=c.forma.bocca_aperta, nome='DenteMurena')


_MURO = (0.575, 0.765)      # il tratto murato


def _murena_murata(c):
    """Le zanne, e il muretto: conci di pietra squadrati e smussati in tre file sfalsate attorno al corpo, murati
    con la malta più chiara (si leggono le fughe)."""
    _denti_murena(c)
    P, sdf = c.P, c.P.sdf
    rng = np.random.default_rng(135)
    n3 = sdf.Noise3(135)
    conci = []
    for fila, t in enumerate((0.605, 0.67, 0.735)):
        zc, h, w = _sezione(c, t)
        for a_deg in (np.arange(-160, 200, 40) + (20 if fila % 2 else 0) + rng.uniform(-6, 6, 9)):
            a = math.radians(float(a_deg))
            s = np.array((t + rng.uniform(-0.004, 0.004), -w * math.cos(a), zc + h * math.sin(a)), F32)
            en = np.array((0.0, -math.cos(a) / w, math.sin(a) / h), F32)
            en /= np.linalg.norm(en)
            ex = np.array((1.0, 0.0, 0.0), F32)
            ea = np.cross(en, ex).astype(F32)
            mezzi = np.array((0.029 * rng.uniform(0.85, 1.05), 0.0065, 0.017 * rng.uniform(0.8, 1.1)), F32)
            conci.append((s + en * (mezzi[1] - 0.0015), np.stack([ex, en, ea]), mezzi))
    C = np.array([k[0] for k in conci], F32)

    def pietre(q):
        d = np.full(len(q), 10.0, F32)
        for cc, Rk, mezzi in conci:
            loc = np.abs((q - cc) @ Rk.T) - (mezzi - 0.003)
            d = np.minimum(d, np.linalg.norm(np.maximum(loc, 0), axis=1) + np.minimum(loc.max(1), 0) - 0.003)
        return (d + 0.0012 * n3(q, scale=0.005, octaves=3)).astype(F32)
    pietra = _mat_grumi(c, 'Pietra', chiaro=(0.36, 0.34, 0.3), scuro=(0.17, 0.16, 0.14), scala=45.0, rough=0.8, rilievo=0.45,
                        chiazze=((0.09, 0.085, 0.075), 0.5))
    c.obs.append(P.oggetto_sdf('Conci', pietre, C.min(0) - 0.04, C.max(0) + 0.04, pietra, res=_res(c, 0.0008, 0.0012)))
    malta = _mat_grumi(c, 'Malta', chiaro=(0.6, 0.57, 0.5), scuro=(0.42, 0.4, 0.35), scala=120.0, rough=0.95, rilievo=0.6)

    def maschera(q):
        x = q[:, 0]
        nz = n3(q * 1.3, scale=0.02, octaves=2)
        return (np.clip((x - _MURO[0] - 0.008 * nz) / 0.008, 0, 1) * np.clip((_MURO[1] + 0.008 * nz - x) / 0.008, 0, 1)
                * (0.8 + 0.2 * nz)).astype(F32)
    c.obs.append(_crosta(c, 'Malta', malta, 0.0085, maschera))


SPECIE['murena_murata'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.015, 0.012), (0.04, 0.026), (0.07, 0.036), (0.1, 0.045), (0.14, 0.052), (0.25, 0.055), (0.5, 0.052),
             (0.7, 0.044), (0.85, 0.032), (0.95, 0.016), (1, 0.004)],
        bot=[(0, -0.012), (0.02, -0.02), (0.05, -0.028), (0.1, -0.036), (0.2, -0.045), (0.4, -0.05), (0.6, -0.046), (0.8, -0.032),
             (0.93, -0.016), (1, -0.004)],
        w=[(0, 0.004), (0.04, 0.018), (0.1, 0.028), (0.25, 0.03), (0.5, 0.025), (0.75, 0.016), (0.9, 0.009), (1, 0.003)],
        eye_t=0.045, eye_z=0.011, eye_r=0.0085, mouth_t=0.075, mouth_z0=-0.006, mouth_z1=-0.012, bocca_aperta=16.0,
        branchie='pori', n_branchie=1, gill_t=0.13,
        fins=[Fin('dorsal', 0.12, 1.0, [(0, 0), (0.03, 0.55), (0.12, 0.9), (0.5, 1.0), (0.9, 1.0), (1, 0.7)], 0.03, 150,
                  carnosa=True, spessore=0.004),
              Fin('anal', 0.45, 1.0, [(0, 0), (0.05, 0.6), (0.2, 0.9), (0.9, 1.0), (1, 0.7)], 0.024, 100, carnosa=True, spessore=0.004),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.9, 1.0), 0.035, 20, carnosa=True, spessore=0.003)],
        piega=[(0, -10), (0.25, 12), (0.5, -10), (0.75, 12), (1.0, -4)]),
    aspetto=Look(back=(0.06, 0.045, 0.03), flank=(0.085, 0.065, 0.04), belly=(0.11, 0.09, 0.06), fin=(0.07, 0.05, 0.035),
                 iris=(0.78, 0.74, 0.6), iris_dark=(0.2, 0.18, 0.1), metal=0.0, irid=0.05, squame=0.0, linea_laterale=0.0,
                 lucido=0.6, ruvido=0.3, tinta_pinne=0.0,
                 disegni=[Disegno('macchie', colore=(0.78, 0.62, 0.28), forza=0.9, scala=34, r=0.24, colore2=(0.02, 0.015, 0.01)),
                          Disegno('punti', colore=(0.7, 0.58, 0.3), forza=0.7, scala=120, r=0.16, seme=3)]),
    extra=_murena_murata,
    famiglia='zombie', piano='anguilliforme',
    opzioni=dict(seed=35, cucitura=(0.22, 0.46, -0.4), punti=12, marcio=0.42))


# ── Raccapricciola (ricciola, Seriola dumerili) ──
# Robusta e affusolata, il muso tondo; la prima dorsale bassa e corta, la seconda lunga con il lobo davanti alto
# e falcato, l'anale uguale più corta, la coda profondamente forcuta; grigio-azzurro, argento, la fascia ambra
# scura obliqua dall'occhio alla dorsale e la riga ambra a metà fianco. «Metà del corpo se n'è andata da un
# pezzo»: da metà corpo al peduncolo la carne non c'è più (campo), resta la lisca (extra: vertebre, spine e tre
# costole spezzate) con la carne marcia sui tagli e qualche filo di carne che pende; la coda tiene ancora.

_RICCIOLA = (0.5, 0.9)      # dove comincia il vuoto e dove ricomincia il peduncolo


def _ricciola_vuoto(c):
    """< 0 nel tratto del corpo che se n'è andato (i due tagli frastagliati e storti)."""
    b = c.body
    n3 = c.P.sdf.Noise3(136)

    def s(p):
        x = p[:, 0]
        v = np.clip(b.norm_v(p), -1.2, 1.2)
        nz = n3(p, scale=0.012, octaves=3)
        x0 = _RICCIOLA[0] + 0.045 * nz - 0.035 * v
        x1 = _RICCIOLA[1] + 0.014 * nz + 0.012 * v
        return np.maximum(x0 - x, x - x1).astype(F32)
    return s


def _campo_ricciola(c, f):
    sdf = c.P.sdf
    vuoto = _ricciola_vuoto(c)

    def g(p):
        return sdf.smax(f(p), -vuoto(p), 0.003).astype(F32)
    return g


def _lisca_ricciola(c):
    P, b = c.P, c.body
    osso = P.bone_material('OssoRicciola', dirt=0.6, tinta=(1.0, 0.95, 0.82))
    A, B, R1, R2 = [], [], [], []

    def pezzo(a, bb, r1, r2):
        A.append(np.array(a, F32))
        B.append(np.array(bb, F32))
        R1.append(r1)
        R2.append(r2)
    xs = np.linspace(0.44, 0.97, 25)
    for i in range(len(xs) - 1):
        x0, x1 = float(xs[i]) + 0.0012, float(xs[i + 1]) - 0.0012
        xm = 0.5 * (x0 + x1)
        zc, h, w = _sezione(c, xm)
        r = max(0.0036, min(h, w) * 0.17)
        pezzo((x0, 0, zc), (xm, 0, zc), r, r * 0.72)
        pezzo((xm, 0, zc), (x1, 0, zc), r * 0.72, r)
        top = float(b.top(np.array([xm], F32))[0])
        bot = float(b.bot(np.array([xm], F32))[0])
        pezzo((xm, 0, zc + r * 0.6), (xm + h * 0.45, 0, top - 0.003), r * 0.34, r * 0.1)     # spina neurale
        pezzo((xm, 0, zc - r * 0.6), (xm + h * 0.45, 0, bot + 0.003), r * 0.32, r * 0.1)     # spina emale
    # tre costole spezzate, appese dove comincia il vuoto
    for x, fino in ((0.5, 0.8), (0.535, 0.55), (0.57, 0.35)):
        zc, h, w = _sezione(c, x)
        for s in (-1, 1):
            pts = [(x, 0.0, zc)] + [(x + 0.014 * k / 5, s * w * 0.86 * math.cos(math.radians(-10 - 100 * fino * k / 5)),
                                     zc + h * 0.86 * math.sin(math.radians(-10 - 100 * fino * k / 5))) for k in range(1, 6)]
            for k in range(5):
                pezzo(pts[k], pts[k + 1], 0.0017, 0.0013)
    f, lo, hi = P.campo_coni(A, B, R1, R2)
    c.obs.append(P.oggetto_sdf('LiscaRicciola', f, lo, hi, osso, res=_res(c, 0.0008, 0.0014)))
    # la carne marcia sui due tagli (una lastra sottile dentro il contorno della pelle)
    vuoto = _ricciola_vuoto(c)
    base = b.base()
    carne = _mat_carne_marcia(c)

    def tagli(q):
        return np.maximum(np.abs(vuoto(q) - 0.00045) - 0.00105, base(q) + 0.0008).astype(F32)
    lo2, hi2 = b.bounds(pad=0.01, solo_corpo=True)
    lo2[0], hi2[0] = 0.4, 0.97
    c.obs.append(P.oggetto_sdf('TagliRicciola', tagli, lo2, hi2, carne, res=_res(c, 0.0008, 0.0014)))
    # i fili di carne che pendono dal taglio verso la lisca
    for k, (v, xb, cede) in enumerate(((0.55, 0.6, 0.012), (-0.35, 0.58, 0.018), (0.1, 0.66, 0.02), (-0.7, 0.55, 0.01))):
        p, _ = b.superficie(_RICCIOLA[0] - 0.03 * v - 0.006, v * 0.85, -1)
        zc, h, _ = _sezione(c, xb)
        q = np.array((xb, -0.004, zc + 0.3 * h * v), F32)
        fs = P.strand(p, q, cede, r=0.0018)
        c.obs.append(P.oggetto_sdf(f'FiloCarne{k}', fs, np.minimum(p, q) - 0.03, np.maximum(p, q) + 0.03, carne, res=0.0006))


SPECIE['raccapricciola'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.02, 0.012), (0.05, 0.038), (0.1, 0.07), (0.18, 0.1), (0.3, 0.12), (0.42, 0.124), (0.55, 0.11),
             (0.7, 0.08), (0.85, 0.045), (0.95, 0.028), (1, 0.024)],
        bot=[(0, -0.025), (0.03, -0.045), (0.08, -0.07), (0.16, -0.095), (0.28, -0.113), (0.42, -0.116), (0.56, -0.102),
             (0.7, -0.074), (0.85, -0.043), (0.95, -0.027), (1, -0.024)],
        w=[(0, 0.008), (0.05, 0.035), (0.15, 0.058), (0.35, 0.066), (0.6, 0.05), (0.85, 0.025), (1, 0.014)],
        eye_t=0.1, eye_z=0.03, eye_r=0.018, mouth_t=0.09, mouth_z0=-0.015, mouth_z1=-0.03, gill_t=0.24,
        fins=[Fin('dorsal', 0.28, 0.36, [(0, 0), (0.15, 0.8), (0.4, 0.9), (0.8, 0.5), (1, 0.1)], 0.045, 7, spiny=True),
              Fin('dorsal', 0.38, 0.85, [(0, 0), (0.06, 0.9), (0.12, 1.0), (0.22, 0.55), (0.5, 0.4), (0.9, 0.35), (1, 0.05)], 0.12, 30),
              Fin('anal', 0.56, 0.85, [(0, 0), (0.08, 0.9), (0.15, 1.0), (0.3, 0.5), (0.6, 0.4), (0.9, 0.35), (1, 0.05)], 0.1, 18),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.95, 0.24), 0.28, 20),
              Fin('pectoral', 0.25, 0.265, PETTORALE, 0.1, 11),
              Fin('pelvic', 0.3, 0.315, PELVICA, 0.08, 6)]),
    aspetto=Look(back=(0.1, 0.12, 0.13), flank=(0.48, 0.47, 0.44), belly=(0.72, 0.71, 0.68), fin=(0.2, 0.2, 0.2),
                 iris=(0.75, 0.68, 0.45), metal=0.55, irid=0.35, squame=0.8,
                 disegni=[Disegno('linea', colore=(0.17, 0.075, 0.018), forza=1.0, v=0.04, inclinazione=3.4, larghezza=0.26,
                                  u0=0.06, u1=0.27),
                          Disegno('strisce', colore=(0.6, 0.4, 0.08), forza=0.65, n=1, v0=-0.14, v1=0.14, larghezza=0.16, u0=0.1),
                          Disegno('ventre', colore=(0.8, 0.8, 0.8), forza=0.5, v1=-0.35)]),
    campo=_campo_ricciola, extra=_lisca_ricciola,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=36, cucitura=(0.2, 0.42, -0.55), punti=9, marcio=0.44))


# ── Cernia Gemente (cernia bruna, Epinephelus marginatus) ──
# Massiccia, la testa grande con la bocca enorme e la mandibola che sporge; la dorsale lunga (spinosa davanti,
# tonda dietro), la coda tonda, le pettorali grandi; bruna scura con le chiazze chiare, le pinne orlate di
# chiaro. «Geme piano come un vecchio… sessant'anni, e da quaranta è morta»: la pelle vecchia a pieghe cadenti
# (campo: solchi che scendono dalla testa, le borse sotto gli occhi, la gola che pende), la bocca socchiusa.

def _campo_cernia(c, f):
    b, sdf = c.body, c.P.sdf
    n3 = sdf.Noise3(137)
    ec, er, _ = b.occhi_lista()[0]
    zg, hg, wg = _sezione(c, 0.2)
    gola = sdf.ellipsoid((0.2, 0.0, zg - hg * 0.72), (0.11, wg * 0.85, hg * 0.42))

    def g(p):
        d = f(p)
        x, z = p[:, 0], p[:, 2]
        nz = n3(p, scale=0.025, octaves=2)
        # i solchi: righe che scendono verso la coda, più storte andando indietro
        q = z + 0.5 * (x - 0.06) + 0.9 * (x - 0.06) ** 2 + 0.012 * nz
        solco = np.clip(1.0 - np.abs(np.sin(np.pi * q / 0.034)) / 0.45, 0, 1) ** 1.5
        zona = np.clip((0.75 - x) / 0.3, 0, 1) * np.clip((x - 0.03) / 0.05, 0, 1)
        d = d + 0.0042 * solco * zona * (0.7 + 0.3 * nz)
        # le borse sotto gli occhi: due cordoni ad arco
        rr = np.hypot(x - ec[0], z - ec[2])
        sotto = np.clip((ec[2] - z) / er, 0, 1)
        for k in (1.55, 2.15):
            d = d - 0.0022 * np.exp(-((rr - er * k) / 0.0035) ** 2) * sotto
        # la gola che pende
        return sdf.smin(d, gola(p), 0.02).astype(F32)
    return g


SPECIE['cernia_gemente'] = Specie(
    forma=Shape(
        top=[(0, -0.018), (0.02, 0.012), (0.05, 0.045), (0.1, 0.085), (0.18, 0.12), (0.3, 0.142), (0.45, 0.148), (0.6, 0.135),
             (0.75, 0.1), (0.88, 0.068), (1, 0.058)],
        bot=[(0, -0.045), (0.03, -0.07), (0.08, -0.1), (0.15, -0.125), (0.28, -0.145), (0.45, -0.148), (0.6, -0.132), (0.75, -0.098),
             (0.88, -0.068), (1, -0.058)],
        w=[(0, 0.012), (0.05, 0.05), (0.15, 0.075), (0.35, 0.082), (0.6, 0.065), (0.85, 0.038), (1, 0.024)],
        eye_t=0.12, eye_z=0.055, eye_r=0.019, mouth_t=0.14, mouth_z0=-0.022, mouth_z1=-0.025, bocca_aperta=9.0, gill_t=0.33,
        fins=[Fin('dorsal', 0.3, 0.86, [(0, 0), (0.04, 0.55), (0.12, 0.7), (0.5, 0.62), (0.62, 0.7), (0.8, 0.95), (0.93, 0.85),
                                       (1, 0.1)], 0.1, 32, spiny=True, bordo=(0.62, 0.56, 0.42)),
              Fin('anal', 0.64, 0.84, [(0, 0), (0.1, 0.6), (0.5, 1.0), (0.85, 0.85), (1, 0.1)], 0.09, 12, bordo=(0.62, 0.56, 0.42)),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.5, 0.9), 0.2, 18, bordo=(0.62, 0.56, 0.42)),
              Fin('pectoral', 0.3, 0.315, PETTORALE_TONDA, 0.15, 14, bordo=(0.55, 0.48, 0.36)),
              Fin('pelvic', 0.32, 0.335, PELVICA, 0.1, 6, spiny=True)]),
    aspetto=Look(back=(0.11, 0.065, 0.035), flank=(0.2, 0.12, 0.065), belly=(0.42, 0.34, 0.2), fin=(0.13, 0.08, 0.045),
                 iris=(0.75, 0.55, 0.25), metal=0.05, irid=0.08, squame=0.7, linea_laterale=0.0, lucido=0.45,
                 disegni=[Disegno('marmo', colore=(0.46, 0.38, 0.22), forza=0.55, scala=36, r=0.3, v0=-0.7, onda=0.5),
                          Disegno('macchie', colore=(0.5, 0.42, 0.26), forza=0.35, scala=22, r=0.22, v0=-0.4, seme=2),
                          Disegno('marmo', colore=(0.05, 0.03, 0.017), forza=0.5, scala=50, r=0.4)]),
    campo=_campo_cernia,
    famiglia='zombie', piano='fusiforme',
    opzioni=dict(seed=37, cucitura=(0.42, 0.72, -0.5), punti=12, marcio=0.45))


# ── Rombo Sepolto (rombo chiodato, Scophthalmus maximus) ──
# Pesce piatto quasi tondo, gli occhi tutti e due sul lato −Y vicini, la dorsale che parte sul muso davanti agli
# occhi, l'anale lunga, la coda tonda; la pelle senza squame coperta di tubercoli ossei (Spine corte e larghe),
# marmorizzata. «Si è seppellito tanto tempo fa, e non è più riuscito a uscire»: la sabbia addosso a croste (più
# spessa verso i bordi e la coda, mai sugli occhi) e i mucchietti che gli coprono i bordi e la frangia.

def _mat_sabbia(c):
    """La sabbia del fondo: grigio-beige a granelli, opaca."""
    m = _gia(c, 'Sabbia')
    if m:
        return m
    m, g = c.P.material('Sabbia')
    co = g.texcoord('Object')
    gr = g.voronoi(co, scale=420.0, feature='F1', randomness=1.0)
    n = g.noise(co, scale=30.0, detail=4.0)
    col = g.mix(g.smoothstep(0.3, 0.7, n.fac), (0.22, 0.2, 0.15), (0.34, 0.3, 0.22))
    col = g.mix(g.mul(g.smoothstep(0.25, 0.1, gr), 0.45), col, (0.1, 0.09, 0.07))
    nrm = g.bump(g.add(g.smoothstep(0.0, 0.4, gr), g.mul(n.fac, 0.3)), strength=0.45, distance=0.0008)
    g.output_material(g.principled(color=col, rough=0.9, normal=nrm, spec=0.3))
    return m


def _sabbia_rombo(c):
    P, b, sdf = c.P, c.body, c.P.sdf
    mat = _mat_sabbia(c)
    n3 = sdf.Noise3(138)
    occhi = [e for e, _, _ in b.occhi_lista()]

    def maschera(q):
        v = np.abs(b.norm_v(q))
        x = q[:, 0]
        nz = n3(q, scale=0.035, octaves=3)
        bordo = np.clip((v - 0.55) / 0.35, 0, 1)
        coda = np.clip((x - 0.55) / 0.35, 0, 1)
        k = np.clip((nz + 0.4 * bordo + 0.3 * coda - 0.3) / 0.06, 0, 1)
        lontano = np.ones(len(q), F32)
        for e in occhi:
            lontano = np.minimum(lontano, np.clip(np.linalg.norm(q - e, axis=1) / 0.03 - 1.0, 0, 1))
        return (k * lontano * (0.5 + 0.5 * np.maximum(bordo, coda))).astype(F32)
    c.obs.append(_crosta(c, 'CrostaSabbia', mat, 0.0045, maschera))
    # i mucchietti sui bordi: la sabbia che copre la frangia, bassi e piatti
    C, R = [], []
    for t, su, r in ((0.5, 1, 0.032), (0.78, 1, 0.026), (0.62, -1, 0.034), (0.88, -1, 0.024), (0.96, 1, 0.02)):
        z = float((b.top if su > 0 else b.bot)(np.array([t], F32))[0])
        C.append(np.array((t, -0.003, z + su * r * 0.2), F32))
        R.append(r)
    sc = np.array((1.0 / 1.3, 1 / 0.22, 1 / 0.7), F32)

    def mucchi(q):
        d = np.full(len(q), 10.0, F32)
        for cc, rr in zip(C, R):
            d = sdf.smin(d, (np.linalg.norm((q - cc) * sc, axis=1) - rr) * 0.22, 0.004)
        return (d + 0.002 * n3(q, scale=0.006, octaves=2)).astype(F32)
    Cn = np.array(C, F32)
    lo, hi = Cn.min(0) - 0.06, Cn.max(0) + 0.06
    c.obs.append(P.oggetto_sdf('MucchiSabbia', mucchi, lo, hi, mat, res=_res(c, 0.0007, 0.0012)))


SPECIE['rombo_sepolto'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.02, 0.06), (0.06, 0.15), (0.12, 0.24), (0.2, 0.31), (0.3, 0.37), (0.42, 0.39), (0.55, 0.37), (0.68, 0.3),
             (0.8, 0.2), (0.9, 0.1), (0.97, 0.05), (1, 0.04)],
        bot=[(0, -0.02), (0.02, -0.08), (0.06, -0.16), (0.12, -0.24), (0.2, -0.31), (0.32, -0.37), (0.45, -0.39), (0.58, -0.37),
             (0.7, -0.3), (0.82, -0.2), (0.92, -0.1), (0.97, -0.05), (1, -0.04)],
        w=[(0, 0.004), (0.08, 0.016), (0.25, 0.024), (0.5, 0.025), (0.75, 0.018), (0.95, 0.008), (1, 0.006)],
        eye_t=0.1, eye_z=0.12, eye_r=0.018,
        occhi=[(0.1, 0.15, 0.018, -1), (0.11, 0.098, 0.019, -1)],
        mouth_t=0.075, mouth_z0=0.0, mouth_z1=-0.035, gill_t=0.22,
        spine=[Spine(0.14, 0.95, -0.85, 0.85, 70, lunghezza=0.006, raggio=0.0055, lati='sinistro', inclinazione=0.2, seme=8)],
        fins=[Fin('dorsal', 0.02, 0.98, [(0, 0), (0.03, 0.5), (0.12, 0.85), (0.45, 1.0), (0.8, 0.85), (0.95, 0.6), (1, 0.4)], 0.09, 90),
              Fin('anal', 0.2, 0.98, [(0, 0), (0.04, 0.6), (0.3, 1.0), (0.75, 0.9), (1, 0.4)], 0.085, 70),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.3, 0.9), 0.14, 22),
              Fin('pectoral', 0.21, 0.22, PETTORALE_TONDA, 0.06, 9),
              Fin('pelvic', 0.19, 0.2, PELVICA, 0.04, 5)]),
    aspetto=Look(back=(0.1, 0.085, 0.06), flank=(0.13, 0.11, 0.08), belly=(0.84, 0.82, 0.76), fin=(0.1, 0.085, 0.06),
                 iris=(0.7, 0.6, 0.35), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.6, linea_v=(0.0, 0.0), lucido=0.35,
                 disegni=[Disegno('marmo', colore=(0.04, 0.032, 0.022), forza=0.7, scala=34, r=0.45),
                          Disegno('macchie', colore=(0.3, 0.26, 0.18), forza=0.5, scala=45, r=0.2, seme=3),
                          Disegno('punti', colore=(0.6, 0.53, 0.38), forza=0.7, scala=200, r=0.15, seme=6)]),
    extra=_sabbia_rombo,
    famiglia='zombie', piano='piatto',
    opzioni=dict(seed=38, cucitura=(0.32, 0.66, -0.3), punti=11, marcio=0.45))


# ── Chimera Bianca (chimera, Chimaera monstrosa) ──
# Testa grossa e occhi enormi, la prima dorsale alta con la spina, la seconda lunga e bassa fino alla coda che
# finisce in un filo (Filamento in punta); pettorali larghe come ali. «La lampara le fa male: chiude gli occhi
# enormi e piange una cosa grigia»: gli occhi socchiusi (palpebre di pelle sopra e sotto, resta una fessura di
# occhio lattiginoso) e le lacrime grigie che colano lungo la guancia fin sotto il mento.

def _mat_palpebra(c):
    m = _gia(c, 'Palpebra')
    if m:
        return m
    m, g = c.P.material('Palpebra')
    co = g.texcoord('Object')
    n = g.noise(co, scale=120.0, detail=3.0)
    col = g.mix(g.smoothstep(0.3, 0.7, n.fac), (0.4, 0.37, 0.34), (0.5, 0.45, 0.41))
    g.output_material(g.principled(color=col, rough=0.45, coat=0.5, coat_rough=0.1, sss=0.3, sss_radius=(1, 0.5, 0.4),
                                   sss_scale=0.004, normal=g.bump(n.fac, strength=0.3, distance=0.001)))
    return m


def _chimera_piange(c):
    P, b, sdf = c.P, c.body, c.P.sdf
    _occhi(c, _mat_occhio(c, 'OcchioChimera', sclera=(0.5, 0.6, 0.52), sclera2=(0.62, 0.7, 0.62), iride=(0.42, 0.6, 0.48),
                          pupilla=(0.3, 0.38, 0.33), iride_r=0.72, pupilla_r=0.38, velo=0.55))
    pelle = _mat_palpebra(c)
    n3 = sdf.Noise3(139)
    for k, (ec, r, look) in enumerate(b.occhi_lista()):
        ln = np.array(look, F32)

        def palpebre(q, ec=ec, r=r, ln=ln):
            rel = q - ec
            guscio = np.abs(np.linalg.norm(rel, axis=1) - r * 1.1) - r * 0.07
            zz, xx = rel[:, 2] / r, rel[:, 0] / r
            nz = n3(q, scale=0.006, octaves=2)
            sopra = (-0.08 + 0.12 * xx * xx) - zz + 0.05 * nz       # < 0 sopra il bordo della palpebra di sopra
            sotto = zz - (-0.58 + 0.1 * xx * xx)                     # < 0 sotto il bordo di quella di sotto
            fuori = -(rel @ ln) - r * 0.1                            # solo la metà che sporge
            d = sdf.smax(guscio, np.minimum(sopra, sotto) * r, r * 0.06)
            return np.maximum(d, fuori).astype(F32)
        c.obs.append(P.oggetto_sdf(f'Palpebre{k}', palpebre, ec - r * 1.4, ec + r * 1.4, pelle, res=_res(c, 0.0004, 0.0006)))
    # le lacrime grigie, dall'occhio sinistro (quello verso la camera) fin sotto il mento
    grigio = P.materiale('LacrimeGrigie', (0.11, 0.11, 0.105), rough=0.08, coat=1.0, sss=0.2)
    ec, r, _ = b.occhi_lista()[0]
    for k, (dt, fino) in enumerate(((-0.008, 1.0), (0.012, 0.75))):
        t0 = float(ec[0]) + dt
        zc, h, _ = _sezione(c, t0)
        v0 = (float(ec[2]) - 0.62 * r - zc) / h
        A, B, R1, R2 = [], [], [], []
        pts = []
        for j in range(12):
            u = j / 11
            t = t0 + 0.014 * u
            v = v0 + (-0.97 * fino - v0) * u
            p, n = b.superficie(t, v, -1)
            pts.append(p + n * 0.0016)
        for j in range(11):
            A.append(pts[j])
            B.append(pts[j + 1])
            R1.append(0.0028 + 0.0012 * (j % 4 == 2))
            R2.append(0.0028 + 0.0012 * ((j + 1) % 4 == 2))
        fs, lo, hi = P.campo_coni(A, B, R1, R2)
        goccia = P.drip(pts[-1], 0.006 + 0.004 * k, r0=0.0026, r1=0.0042, dir=(0.1, -0.15, -1.0))
        c.obs.append(P.oggetto_sdf(f'Lacrima{k}', lambda q, fs=fs, goccia=goccia: np.minimum(fs(q), goccia(q)).astype(F32),
                                   lo - 0.03, hi + 0.03, grigio, res=0.0005))


SPECIE['chimera_bianca'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.02, 0.03), (0.06, 0.06), (0.12, 0.075), (0.2, 0.08), (0.3, 0.075), (0.45, 0.055), (0.6, 0.035),
             (0.75, 0.02), (0.9, 0.009), (1, 0.003)],
        bot=[(0, -0.032), (0.04, -0.056), (0.1, -0.07), (0.2, -0.075), (0.32, -0.07), (0.45, -0.05), (0.6, -0.03), (0.75, -0.016),
             (0.9, -0.007), (1, -0.002)],
        w=[(0, 0.01), (0.05, 0.04), (0.15, 0.054), (0.3, 0.045), (0.5, 0.03), (0.75, 0.014), (1, 0.002)],
        eye_t=0.088, eye_z=0.022, eye_r=0.031, mouth_t=0.04, mouth_z0=-0.032, mouth_z1=-0.042, gill_t=0.17,
        filamenti=[Filamento(xyz=(0.995, 0.0, 0.0), dir=(1.0, 0.0, 0.05), curva=(0, 0, -0.6), lunghezza=0.28, raggio=0.0026,
                             lati='centro', punta=0.3, segmenti=12)],
        fins=[Fin('dorsal', 0.2, 0.27, [(0, 0), (0.05, 1.0), (0.2, 0.92), (0.6, 0.5), (1, 0.05)], 0.11, 12, spiny=True),
              Fin('dorsal', 0.31, 0.97, [(0, 0), (0.02, 0.5), (0.1, 0.8), (0.5, 0.75), (0.9, 0.6), (1, 0.3)], 0.025, 80),
              Fin('anal', 0.78, 0.97, [(0, 0), (0.1, 0.7), (0.8, 0.6), (1, 0.2)], 0.018, 20),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.5, 1.0), 0.03, 12),
              Fin('pectoral', 0.17, 0.2, PETTORALE_ALA, 0.21, 18, dir=(0.8, 0.45, -0.3)),
              Fin('pelvic', 0.42, 0.44, PELVICA, 0.06, 7)]),
    aspetto=Look(back=(0.3, 0.26, 0.22), flank=(0.5, 0.46, 0.42), belly=(0.64, 0.62, 0.58), fin=(0.32, 0.28, 0.25),
                 iris=(0.35, 0.75, 0.45), iris_dark=(0.05, 0.18, 0.1), metal=0.45, irid=0.45, squame=0.0, linea_laterale=0.0,
                 disegni=[Disegno('marmo', colore=(0.2, 0.16, 0.12), forza=0.5, scala=24, r=0.5),
                          Disegno('linea', colore=(0.12, 0.1, 0.08), forza=0.7, v=0.15, inclinazione=-0.1, larghezza=0.025, u0=0.15),
                          Disegno('vermi', colore=(0.15, 0.12, 0.1), forza=0.6, scala=60, u1=0.16)]),
    extra=_chimera_piange,
    famiglia='zombie', piano='coda_di_topo',
    opzioni=dict(seed=39, cucitura=(0.26, 0.5, -0.5), punti=10, occhi=None, marcio=0.45))


# ── Squalo Capomorto (squalo capopiatto, Hexanchus griseus) ──
# Squalo pesante, la testa larga e piatta con il muso tondo, SEI fessure branchiali lunghe, una sola dorsale molto
# arretrata, la coda lunga con il lobo di sotto debole; gli occhi piccoli e verdi; grigio-bruno, la linea laterale
# chiara. «Ha sei branchie, e respira con tutte e sei»: le sei fessure aperte (campo: spaccature larghe e
# profonde dai bordi marci) e rosse dentro (extra: le lamelle di carne viva in fondo).

_CAPOMORTO_PROF = 0.009     # quanto sono profonde le fessure aperte


_CAPOMORTO_APERTE = (1.0, 0.7, 1.15, 0.85, 1.05, 0.65)     # quanto è spalancata ogni fessura (marce, non in fila)


def _fessure_capomorto(c):
    """Le sei fessure come in Body.field: (t, mezza altezza in v, quanto è aperta); x = t − 0.01·v, centrate su
    v = −0.08."""
    sh = c.forma
    return [(sh.gill_t + i * sh.passo_branchie, 0.62 - 0.03 * i, _CAPOMORTO_APERTE[i]) for i in range(sh.n_branchie)]


def _campo_capomorto(c, f):
    b, sdf = c.body, c.P.sdf
    fes = _fessure_capomorto(c)
    n3 = sdf.Noise3(140)
    f2 = _strappi(c, f, seme=40, morsi=2, buchi=1)
    x_lo, x_hi = fes[0][0] - 0.03, fes[-1][0] + 0.03

    def g(p):
        d = f2(p)
        m = (p[:, 0] > x_lo) & (p[:, 0] < x_hi)
        if not m.any():
            return d
        q = p[m]
        zc, h, _ = b.section(np.clip(q[:, 0], 0, 1))
        v = (q[:, 2] - zc) / h
        sy = b.surface_y(q[:, 0], q[:, 2])
        nz = n3(q, scale=0.005, octaves=2)
        dd = d[m]
        for xi, alt, aperta in fes:
            u = (v + 0.08) / alt
            larg = 0.0042 * aperta * np.sqrt(np.clip(1 - u * u, 0, 1)) + 0.0012 * nz
            slot = np.maximum(np.abs(q[:, 0] - (xi - 0.01 * v)) - larg, (np.abs(v + 0.08) - alt) * h)
            slot = np.maximum(slot, (sy - _CAPOMORTO_PROF) - np.abs(q[:, 1]))
            dd = sdf.smax(dd, -slot, 0.0012)
        d = d.copy()
        d[m] = dd
        return d
    return g


def _capomorto(c):
    """Gli occhi verdi e velati, e la carne rossa in fondo alle fessure (le lamelle)."""
    P, b = c.P, c.body
    _occhi(c, _mat_occhio(c, 'OcchioVerdeMorto', sclera=(0.2, 0.32, 0.22), sclera2=(0.3, 0.44, 0.3), iride=(0.3, 0.6, 0.36),
                          pupilla=(0.35, 0.5, 0.4), iride_r=0.8, pupilla_r=0.4, velo=0.5, velo_col=(0.62, 0.72, 0.62)))
    fes = _fessure_capomorto(c)

    def lamelle(q):
        x = q[:, 0]
        zc, h, _ = b.section(np.clip(x, 0, 1))
        v = (q[:, 2] - zc) / h
        sy = b.surface_y(x, q[:, 2])
        d = np.full(len(q), 10.0, F32)
        for xi, alt, aperta in fes:
            s = np.maximum(np.abs(x - (xi - 0.01 * v)) - 0.0062 * aperta, (np.abs(v + 0.08) - alt * 0.96) * h)
            s = np.maximum(s, np.abs(np.abs(q[:, 1]) - (sy - _CAPOMORTO_PROF * 0.8)) - 0.0016 - 0.0007 * np.sin(q[:, 2] * 900.0))
            d = np.minimum(d, s)
        return d.astype(F32)
    lo, hi = b.bounds(pad=0.004, solo_corpo=True)
    lo[0], hi[0] = fes[0][0] - 0.03, fes[-1][0] + 0.03
    c.obs.append(P.oggetto_sdf('Lamelle', lamelle, lo, hi, P.flesh_material('BranchieRosse', color=(0.27, 0.035, 0.035)),
                               res=_res(c, 0.0006, 0.001)))


SPECIE['squalo_capomorto'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.02, 0.012), (0.06, 0.028), (0.12, 0.042), (0.22, 0.056), (0.35, 0.066), (0.5, 0.066), (0.65, 0.056),
             (0.8, 0.04), (0.92, 0.026), (1, 0.02)],
        bot=[(0, -0.014), (0.03, -0.03), (0.08, -0.045), (0.18, -0.06), (0.32, -0.07), (0.48, -0.07), (0.62, -0.058), (0.76, -0.04),
             (0.9, -0.025), (1, -0.02)],
        w=[(0, 0.008), (0.04, 0.036), (0.1, 0.058), (0.2, 0.066), (0.35, 0.066), (0.55, 0.056), (0.75, 0.038), (0.9, 0.024),
           (1, 0.016)],
        eye_t=0.07, eye_z=0.008, eye_r=0.011,
        bocca='ventrale', mouth_a=0.06, mouth_t=0.12, mouth_z1=-0.03, mouth_z0=-0.03,
        branchie='fessure', gill_t=0.14, n_branchie=6, passo_branchie=0.017,
        fins=[Fin('dorsal', 0.66, 0.74, DORSALE_SQUALO, 0.06, 26, carnosa=True, spessore=0.005),
              Fin('anal', 0.74, 0.8, DORSALE_SQUALO, 0.04, 18, carnosa=True, spessore=0.004),
              Fin('caudal', 1.0, 1.0, coda_eterocerca(lobo=1.0, alzata=1.1, lobo_basso=0.45, basso=0.9), 0.36, 60, carnosa=True,
                  spessore=0.006),
              Fin('pectoral', 0.19, 0.25, [(0, 0.08), (0.5, 0.12), (1.0, 0.0), (0.85, -0.12), (0.4, -0.16), (0, -0.12)], 0.2, 30,
                  carnosa=True, spessore=0.006, dir=(0.75, 0.3, -0.6)),
              Fin('pelvic', 0.55, 0.62, [(0, 0.05), (0.6, 0.06), (1.0, -0.02), (0.6, -0.12), (0, -0.1)], 0.07, 20, carnosa=True,
                  spessore=0.004)]),
    aspetto=Look(back=(0.05, 0.045, 0.04), flank=(0.12, 0.11, 0.095), belly=(0.42, 0.4, 0.36), fin=(0.06, 0.055, 0.048),
                 iris=(0.3, 0.6, 0.35), metal=0.05, irid=0.05, squame=0.0, linea_laterale=0.0, lucido=0.3, ruvido=0.5,
                 disegni=[Disegno('linea', colore=(0.4, 0.38, 0.34), forza=0.45, v=0.12, larghezza=0.025, u0=0.2, u1=0.98)]),
    campo=_campo_capomorto, extra=_capomorto,
    famiglia='zombie', piano='squalo',
    opzioni=dict(seed=40, cucitura=(0.3, 0.6, -0.55), punti=13, occhi=None, marcio=0.45))
