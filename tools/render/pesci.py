"""
I pesci del Catalogo (src/game/catalog.ts, docs/CATALOGO.md): un generatore parametrico e le cinque
famiglie di trasformazione (scheletrici, zombi, glitchati, corrotti, sanguinanti).

Il corpo è un campo di distanza costruito da tre profili lungo l'asse (dorso, ventre, mezza larghezza):
il muso sta in x = 0 e guarda verso −X, l'attacco della coda in x = 1, il dorso verso +Z, il fianco
sinistro verso −Y (la camera). Le pinne sono mesh sottili a raggi (o lastre di carne fuse nel corpo, per
squali e razze); occhi, denti e melma come le creature. Si rende il "ritratto" di cattura su sfondo
trasparente, con la lampara davanti e la luna dietro.

Le specie sono DATI, nel pacchetto pesci_specie/: un file per famiglia (scheletrici, zombi, glitchati,
corrotti, sanguinanti), le classi e gli aiuti in pesci_specie/base.py, il brief per aggiungerle in
pesci_specie/PIANO.md. Ogni voce: forma (Shape), aspetto (Look), famiglia, piano corporeo (PIANI) ed
eventuali extra (una funzione che aggiunge i dettagli propri della specie).

Uso: tools/.venv/bin/python tools/render/pesci.py [id ...] [--fast] [--anteprima]
        senza id: i cinque prototipi; --tutti: tutte le specie registrate; --famiglia=zombie: una famiglia
     tools/.venv/bin/python tools/render/pesci.py --elenco                      cosa c'è e cosa manca
     tools/.venv/bin/python tools/render/pesci.py --foglio out.jpg id[:etichetta] ... [--colonne=4] [--larghezza=1600]
                                                                     foglio delle anteprime già fatte
Uscite: public/assets/img/fish/<id>.webp (RGBA) e fish.json; il png in tools/render/cache/pesci/.
Con --anteprima scrive SOLO in tools/render/cache/pesci/anteprime/: <id>.png (RGBA, come il finale) e
<id>.jpg (sul fondo scuro del Catalogo, da guardare). Niente public/, niente fish.json.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == '__main__':
    # gli extra delle specie possono fare «import pesci»: che trovino questo modulo, non una seconda copia
    sys.modules.setdefault('pesci', sys.modules[__name__])

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import pesci_specie as registro  # noqa: E402
import sdf  # noqa: E402
from common import CACHE, OUT_IMG, collection, log, mesh_from_arrays, reset_scene, set_lightgroup  # noqa: E402,F401
from creature import eye_material, eyeball, flesh_material, sdf_object, tooth  # noqa: E402,F401
from dettagli import area_light  # noqa: E402
from nodes import material  # noqa: E402
from pesci_specie.base import (PIANI, Disegno, Filamento, Fin, Look, Piano, Ritratto, Shape, Specie,  # noqa: E402,F401
                               coda_forcuta)
from skin import cloudy_eye, drip, slime_material, strand  # noqa: E402,F401

F = np.float32
FAST = '--fast' in sys.argv
ANTEPRIMA = '--anteprima' in sys.argv
FISH_DIR = os.path.join(OUT_IMG, 'fish')
COL = 'fish'
LONTANO = 10.0                     # il valore di un pezzo di campo lontano dal suo riquadro
FONDO_CATALOGO = (10, 12, 17)      # il fondo scuro delle pagine (per le anteprime .jpg e i fogli)
_forked = coda_forcuta             # il nome di prima (le specie ora usano coda_forcuta, in pesci_specie/base.py)


# ───────────────────────── profili ─────────────────────────

def prof(points):
    """Curva liscia (Hermite con tangenti alla Catmull-Rom) per punti (t, valore) con t crescente."""
    pts = np.array(points, F)
    ts, vs = pts[:, 0], pts[:, 1]

    def f(t):
        t = np.clip(np.asarray(t, F), ts[0], ts[-1])
        i = np.clip(np.searchsorted(ts, t, side='right') - 1, 0, len(ts) - 2)
        t0, t1 = ts[i], ts[i + 1]
        dt = np.maximum(t1 - t0, 1e-6)
        u = (t - t0) / dt
        im, ip = np.maximum(i - 1, 0), np.minimum(i + 2, len(ts) - 1)
        m0 = (vs[i + 1] - vs[im]) / np.maximum(ts[i + 1] - ts[im], 1e-6) * dt
        m1 = (vs[ip] - vs[i]) / np.maximum(ts[ip] - ts[i], 1e-6) * dt
        u2, u3 = u * u, u * u * u
        return ((2 * u3 - 3 * u2 + 1) * vs[i] + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * vs[i + 1] + (u3 - u2) * m1).astype(F)
    return f


# ───────────────────────── campo del corpo ─────────────────────────

class Body:
    """Il corpo di una forma. piano: il piano corporeo (PIANI): 'alto' = costruito con il dorso verso la
    camera (pesci piatti, razze); disco = le razze, con il disco delle pettorali nel piano XZ."""

    def __init__(self, sh: Shape, piano: Piano | None = None):
        self.sh = sh
        self.top, self.bot, self.wid = prof(sh.top), prof(sh.bot), prof(sh.w)
        self.piano = piano if piano is not None else PIANI['fusiforme']
        self.alto = self.piano.vista == 'alto'
        self.razza = bool(self.piano.disco)
        self.disco = None
        if sh.disco is not None:
            # il disco è un secondo corpo a sezioni ellittiche: largo in z, sottile in y
            self.disco = Body(Shape(top=list(sh.disco.contorno), bot=[(t, -y) for t, y in sh.disco.contorno],
                                    w=list(sh.disco.spessore), eye_t=0.0, eye_z=0.0, eye_r=0.0))
        self.campo_extra = None     # il campo(c, f) della specie, se c'è (lo mette build())
        self._parti = None          # i pezzi fusi nel corpo: (campo, raccordo, lo, hi)
        self._base = None
        self._telaio = None
        self._occhi = None

    def section(self, t):
        zt, zb = self.top(t), self.bot(t)
        return (zt + zb) * 0.5, np.maximum((zt - zb) * 0.5, 1e-3), np.maximum(self.wid(t), 1e-3)

    def surface_y(self, t, z):
        """Mezza larghezza del corpo alla quota z (per appoggiare cose sul fianco). Sulle razze conta anche il
        disco: è la pelle del dorso."""
        zc, h, w = self.section(np.asarray(t, F))
        q = np.clip((np.asarray(z, F) - zc) / h, -0.999, 0.999)
        y = w * np.sqrt(1 - q * q)
        if self.disco is not None:
            y = np.maximum(y, self.disco.surface_y(t, z))
        return y

    def norm_v(self, p):
        t = np.clip(p[:, 0], 0, 1)
        zc, h, _ = self.section(t)
        return (p[:, 2] - zc) / h

    @property
    def zmax(self):
        """La mezza apertura massima in z (le razze: il disco), per normalizzare v sulle razze."""
        t = np.linspace(0, 1, 200, dtype=F)
        z = np.maximum(np.abs(self.top(t)), np.abs(self.bot(t)))
        if self.disco is not None:
            z = np.maximum(z, np.abs(self.disco.top(t)))
        return float(z.max())

    def _corpo(self):
        """Il campo del corpo nudo, dai tre profili (quello di sempre)."""
        def f(p):
            x, y, z = p[:, 0], p[:, 1], p[:, 2]
            t = np.clip(x, 0.0, 1.0)
            zc, h, w = self.section(t)
            dz = z - zc
            k0 = np.sqrt((y / w) ** 2 + (dz / h) ** 2)
            k1 = np.sqrt((y / (w * w)) ** 2 + (dz / (h * h)) ** 2)
            d = k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)
            d = sdf.smax(d, -x - 0.002, 0.006)
            d = np.maximum(d, x - 1.0)
            return d.astype(F)
        return f

    def base(self):
        """Il corpo con il disco delle razze, senza gli altri pezzi: serve per le normali e per appoggiare
        sulla pelle spine, occhi, filamenti."""
        if self._base is None:
            f = self._corpo()
            if self.disco is None:
                self._base = f
            else:
                fd, k = self.disco.raw(), self.sh.disco.raccordo
                self._base = lambda p: sdf.smin(f(p), fd(p), k).astype(F)
        return self._base

    def parti(self):
        """I pezzi fusi nel corpo (disco, pinne carnose, rostro, disco orale, spine): [(campo, raccordo)]."""
        if self._parti is None:
            sh = self.sh
            P = []
            if self.disco is not None:
                lo, hi = self.disco.bounds(pad=0.0)
                P.append((self.disco.raw(), sh.disco.raccordo, lo, hi, 'disco'))
            for fin in sh.fins:
                if fin.carnosa:
                    for s in ((-1, 1) if fin.kind in ('pectoral', 'pelvic') else (-1,)):
                        f, lo, hi = piastra(self, fin, s)
                        P.append((f, 0.005, lo, hi, 'pinna'))
            if sh.rostro is not None:
                f, lo, hi = rostro_campo(self)
                P.append((f, 0.008, lo, hi, 'rostro'))
            if sh.disco_orale is not None:
                f, lo, hi = disco_orale_campo(self)
                P.append((f, 0.006, lo, hi, 'orale'))
            if sh.spine:
                f, lo, hi = spine_campo(self)
                P.append((f, 0.002, lo, hi, 'spine'))
            self._parti = P
        return [(f, k) for f, k, _, _, _ in self._parti]

    def attr_parti(self):
        """Attributi della pelle per i pezzi fusi che vanno colorati a parte: 'pinna' (le pinne carnose, del
        colore delle pinne) e 'rostro' (del colore del dorso): 1 sul pezzo, 0 sul corpo, sfumati nel raccordo.
        Con la ventosa della remora anche 'ventosa' (1 sul disco) e 'lamelle' (1 nei solchi fra le lamelle)."""
        self.parti()
        out = {}
        for tipo in ('pinna', 'rostro'):
            campi = [f for f, _, _, _, t in self._parti if t == tipo]
            if not campi:
                continue
            base = self.base()

            def a(p, campi=campi, base=base):
                d = campi[0](p)
                for f in campi[1:]:
                    d = np.minimum(d, f(p))
                return np.clip((base(p) - d) / 0.004, 0, 1).astype(F)
            out[tipo] = a
        if self.sh.ventosa is not None:
            def disco(p):
                _, rr, vicino, _ = self._ventosa_q(p)
                return (np.clip((0.97 - rr) / 0.08, 0, 1) * vicino).astype(F)

            def lamelle(p):
                _, rr, vicino, lam = self._ventosa_q(p)
                return (lam * np.clip((0.92 - rr) / 0.08, 0, 1) * vicino).astype(F)
            out['ventosa'], out['lamelle'] = disco, lamelle
        return out

    def raw(self):
        f = self._corpo()
        parti = self.parti()
        anelli = self.sh.anelli
        if not parti and not anelli and self.campo_extra is None:
            return f

        def g(p):
            d = f(p)
            if anelli:
                # anelli ossei in rilievo (pesce ago, cavalluccio)
                x = p[:, 0]
                a0, a1 = self.sh.anelli_tratto
                cr = np.clip(np.cos(2 * np.pi * anelli * x), 0, 1) ** 6 * ((x > a0) & (x < a1))
                d = d - 0.0016 * cr
            for pf, k in parti:
                d = sdf.smin(d, pf(p), k)
            return d.astype(F)
        return self.campo_extra(g) if self.campo_extra is not None else g

    def mouth_line(self, x):
        sh = self.sh
        u = np.clip(x / max(sh.mouth_t, 1e-3), 0, 1)
        return (sh.mouth_z0 + (sh.mouth_z1 - sh.mouth_z0) * u).astype(F)

    def field(self, mouth_open=0.0, socket=True):
        """Il corpo con la bocca (taglio sottile, o aperta di mouth_open gradi), l'opercolo e le orbite; e,
        se la forma li chiede, bocca ventrale, fessure o pori branchiali, spiracoli, ventosa, disco orale."""
        sh = self.sh
        base = self.raw()
        hinge = np.array((sh.mouth_t, 0.0, sh.mouth_z1), F)
        R = sdf.rot_matrix('y', -mouth_open) if mouth_open else None
        self.hinge, self.jaw_R = hinge, R

        def upper(p):
            # il corpo senza la mascella inferiore (la parte sotto la linea della bocca, davanti alla cerniera)
            return np.maximum(base(p), np.minimum(self.mouth_line(p[:, 0]) - p[:, 2], sh.mouth_t - p[:, 0]))

        def lower(p):
            q = (p - hinge) @ R + hinge
            return np.maximum(base(q), np.maximum(q[:, 2] - self.mouth_line(q[:, 0]), q[:, 0] - sh.mouth_t)), q
        self.upper, self.lower = upper, lower
        occhi = self.occhi_lista()
        ventrale = self._bocca_ventrale() if sh.bocca == 'ventrale' else None
        pori = self._pori() if sh.branchie == 'pori' else None
        spir = self._spiracoli() if sh.spiracoli else None
        orale = _disco_orale_telaio(self) if sh.disco_orale is not None else None

        def f(p):
            x, z = p[:, 0], p[:, 2]
            if mouth_open:
                d = np.minimum(upper(p), lower(p)[0])
            elif sh.bocca == 'terminale':
                # il taglio della bocca: una fessura sottile dal muso all'angolo
                d = base(p)
                if sh.rostro is not None and sh.rostro.tipo == 'becco':
                    # il becco è tagliato fino in punta, e il taglio si assottiglia con le mascelle (resta un
                    # terzo della loro altezza): così arrivano intere fino in fondo
                    _, wz, _ = sezione_rostro(sh.rostro, np.minimum(x, 0.0))
                    slit = np.maximum(np.abs(z - self.mouth_line(x)) - np.minimum(0.0012, wz * 0.3), x - sh.mouth_t)
                else:
                    slit = np.maximum(np.abs(z - self.mouth_line(x)) - 0.0012, x - sh.mouth_t)
                if sh.rostro is not None and sh.rostro.tipo != 'becco':
                    slit = np.maximum(slit, -x - 0.003)      # il rostro resta intero (solo il becco è tagliato)
                d = sdf.smax(d, -slit, 0.002)
            else:
                d = base(p)
            if ventrale is not None:
                # la mezzaluna sotto il muso degli squali
                dist, _ = ventrale.query(p, k=1, workers=-1)
                d = sdf.smax(d, -(dist.astype(F) - 0.0016), 0.002)
            if sh.branchie == 'opercolo':
                # bordo dell'opercolo: un solco ad arco sul fianco
                zc, h, _ = self.section(np.clip(x, 0, 1))
                v = (z - zc) / h
                arc_x = sh.gill_t - 0.035 * (v * v)
                groove = np.exp(-((x - arc_x) / 0.004) ** 2) * np.clip(1 - np.abs(v) / 0.95, 0, 1)
                d = d + 0.0025 * groove
            elif sh.branchie == 'fessure':
                # fessure branchiali verticali, appena inclinate, sul fianco
                zc, h, _ = self.section(np.clip(x, 0, 1))
                v = (z - zc) / h
                gr = np.zeros(len(p), F)
                for i in range(sh.n_branchie):
                    xi = sh.gill_t + i * sh.passo_branchie - 0.01 * v
                    alt = 0.62 - 0.03 * i
                    gr = np.maximum(gr, np.exp(-((x - xi) / 0.0026) ** 2) * np.clip((alt - np.abs(v + 0.08)) / 0.12, 0, 1))
                d = d + 0.0032 * gr
            elif pori is not None:
                for c in pori:
                    d = sdf.smax(d, -(np.linalg.norm(p - c, axis=1) - 0.0042), 0.0015)
            if socket:
                for ec, r, _ in occhi:
                    if sh.eye_allungato != 1.0:
                        q = (p - ec) / np.array((sh.eye_allungato, 1.0, 1.0), F)
                        d = sdf.smax(d, -(np.linalg.norm(q, axis=1) - r * 1.05), 0.004)
                    else:
                        d = sdf.smax(d, -(np.linalg.norm(p - ec, axis=1) - r * 1.05), 0.004)
            if spir is not None:
                for c, r in spir:
                    d = sdf.smax(d, -(np.linalg.norm(p - c, axis=1) - r), 0.002)
            if sh.ventosa is not None:
                d = self._ventosa(p, d)
            if orale is not None:
                # la conca della ventosa orale e la gola al centro
                C, n, _, _ = orale
                R0 = sh.disco_orale.raggio
                d = sdf.smax(d, -(np.linalg.norm(p - (C + n * R0 * 0.95), axis=1) - R0 * 1.02), 0.003)
                d = sdf.smax(d, -(np.linalg.norm(p - (C + n * R0 * 0.05), axis=1) - R0 * 0.2), 0.002)
            return d.astype(F)
        return f

    def _bocca_ventrale(self):
        """KD-tree dei punti della mezzaluna della bocca degli squali: dal centro sotto il muso (mouth_a) agli
        angoli (mouth_t), sulla pelle del ventre."""
        from scipy.spatial import cKDTree
        sh = self.sh
        s = np.linspace(-1, 1, 121, dtype=F)
        xs = sh.mouth_a + (sh.mouth_t - sh.mouth_a) * s * s
        zc, h, w = self.section(xs)
        ys = s * w * 0.82
        zs = zc - h * np.sqrt(np.clip(1 - (ys / w) ** 2, 0, 1)) + 0.0006
        # verso gli angoli la bocca sale fino a mouth_z1
        zs = np.where(np.abs(s) > 0.7, zs + (sh.mouth_z1 - zs) * ((np.abs(s) - 0.7) / 0.3) ** 2, zs)
        return cKDTree(np.stack([xs, ys, zs], axis=1))

    def _pori(self):
        """I pori branchiali tondi della lampreda, in fila dietro l'occhio, sui due lati."""
        sh = self.sh
        out = []
        for i in range(sh.n_branchie):
            t = sh.gill_t + i * sh.passo_branchie
            zc, h, _ = (float(a[0]) for a in self.section(np.array([t], F)))
            z = zc + h * 0.12
            y = float(self.surface_y(t, z))
            for s in (-1, 1):
                out.append(np.array((t, s * y, z), F))
        return out

    def _spiracoli(self):
        """Il foro dietro ogni occhio (razze, squali): sulla pelle, 1.9 raggi dell'occhio più indietro."""
        out = []
        for ec, r, _ in self.occhi_lista():
            t = float(ec[0]) + r * 1.9
            z = float(ec[2])
            y = float(self.surface_y(t, z))
            out.append((np.array((t, np.sign(ec[1]) * y, z), F), self.sh.spiracoli))
        return out

    def _ventosa_q(self, p):
        """La ventosa della remora nei punti p: (q lungo il disco 0..1, distanza dal centro in unità del disco,
        vicinanza alla pelle del dorso 0..1, lamelle: 1 nei solchi e 0 sulle creste)."""
        vs = self.sh.ventosa
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        q = (x - vs.t0) / (vs.t1 - vs.t0)
        rr = np.sqrt((2 * q - 1) ** 2 + (y / vs.larghezza) ** 2)
        ztop = self.top(np.clip(x, 0, 1))
        vicino = np.clip(1 - np.abs(z - ztop) / 0.012, 0, 1)
        lam = 0.5 + 0.5 * np.cos(2 * np.pi * q * vs.lamelle)
        return q, rr, vicino, lam

    def _ventosa(self, p, d):
        """Il disco adesivo della remora sul capo: lamelle di traverso scavate e il bordo rialzato."""
        _, rr, vicino, lam = self._ventosa_q(p)
        dentro = np.clip((0.92 - rr) / 0.08, 0, 1)
        d = d + 0.0022 * lam * dentro * vicino
        return d - 0.0018 * np.exp(-((rr - 1.0) / 0.07) ** 2) * vicino

    def mouth_attr(self, p):
        """1 sulle superfici tagliate della bocca aperta (dentro il corpo originale), 0 sulla pelle."""
        base = self.raw()
        du, (dl, q) = self.upper(p), self.lower(p)
        on_upper = np.abs(du) <= np.abs(dl)
        inside = np.where(on_upper, base(p), base(q))
        return np.clip(-inside / 0.003, 0, 1).astype(F)

    def eye_center(self, side=-1):
        sh = self.sh
        y = float(self.surface_y(sh.eye_t, sh.eye_z)) - sh.eye_r * 0.45
        return np.array((sh.eye_t, side * y, sh.eye_z), F)

    def occhi_lista(self):
        """Gli occhi: [(centro, raggio, sguardo)]. Di default la coppia simmetrica di sempre, che guarda di
        lato; con sh.occhi = [(t, z, r, lato)] quelli, affondati e girati lungo la normale della pelle."""
        if self._occhi is None:
            sh = self.sh
            if sh.occhi is None:
                self._occhi = [(self.eye_center(s), sh.eye_r, (0.0, float(s), 0.0)) for s in (-1, 1)]
            else:
                out = []
                for t, z, r, lato in sh.occhi:
                    ps = np.array((t, lato * float(self.surface_y(t, z)), z), F)
                    n = self.normale(ps[None])[0]
                    out.append(((ps - n * r * 0.45).astype(F), r, tuple(float(a) for a in n)))
                self._occhi = out
        return self._occhi

    def normale(self, P, eps=0.0008):
        """La normale della pelle (gradiente del corpo con il disco) nei punti P (N, 3)."""
        f = self.base()
        P = np.asarray(P, F)
        g = np.empty_like(P)
        for k in range(3):
            d = np.zeros(3, F)
            d[k] = eps
            g[:, k] = f(P + d) - f(P - d)
        return g / (np.linalg.norm(g, axis=1, keepdims=True) + 1e-12)

    def superficie(self, t, v, lato=-1):
        """Il punto della pelle in (t, v) sul lato dato (−1 verso la camera, 1 l'altro, 0 la linea di mezzo
        del dorso se v ≥ 0 o del ventre) e la sua normale. v oltre ±1 ha senso solo sul disco delle razze."""
        zc, h, _ = (float(a[0]) for a in self.section(np.array([t], F)))
        if self.disco is None:
            v = max(-1.0, min(1.0, v))
        if lato == 0:
            p = np.array((t, 0.0, zc + h * (1.0 if v >= 0 else -1.0)), F)
        else:
            z = zc + h * v
            p = np.array((t, lato * float(self.surface_y(t, z)), z), F)
        return p, self.normale(p[None])[0]

    def telaio_pinne(self):
        """Il corpo su cui si costruiscono le pinne e le due trasformazioni dei punti (None: il corpo stesso).
        Le razze sono costruite con il dorso verso −Y: le loro pinne (dorsali e caudale sulla coda) si fanno
        su un corpo 'di fianco' equivalente — dorso = mezzo spessore w, fianchi = mezza apertura in z — e poi
        si girano: (x, y', z') → (x, −z', zc(x) + y')."""
        if not self.razza:
            return self, None, None
        if self._telaio is None:
            ts = np.linspace(0, 1, 41, dtype=F)
            zc, h, w = self.section(ts)
            vsh = Shape(top=[(float(t), float(a)) for t, a in zip(ts, w)], bot=[(float(t), -float(a)) for t, a in zip(ts, w)],
                        w=[(float(t), float(a)) for t, a in zip(ts, h)], eye_t=0.0, eye_z=0.0, eye_r=0.0)
            zcf = prof([(float(t), float(a)) for t, a in zip(ts, zc)])

            def a_mondo(P):
                P = np.asarray(P, F)
                return np.stack([P[:, 0], -P[:, 2], zcf(np.clip(P[:, 0], 0, 1)) + P[:, 1]], axis=1).astype(F)

            def da_mondo(P):
                P = np.asarray(P, F)
                return np.stack([P[:, 0], P[:, 2] - zcf(np.clip(P[:, 0], 0, 1)), -P[:, 1]], axis=1).astype(F)
            self._telaio = (Body(vsh), a_mondo, da_mondo)
        return self._telaio

    def bounds(self, pad=0.03, tratto=None, solo_corpo=False):
        """Il riquadro del corpo e dei pezzi fusi. solo_corpo: senza i pezzi (la lisca degli scheletri);
        tratto = (x0, x1): solo i pezzi che cadono in quel tratto (il cranio non ha bisogno della coda)."""
        t = np.linspace(0, 1, 200, dtype=F)
        zt, zb, w = self.top(t), self.bot(t), self.wid(t)
        lo = np.array((-pad, -float(w.max()) - pad, float(zb.min()) - pad), F)
        hi = np.array((1.0 + pad, float(w.max()) + pad, float(zt.max()) + pad), F)
        self.parti()
        for _, _, plo, phi, _ in ([] if solo_corpo else self._parti):
            if tratto is not None and (float(phi[0]) < tratto[0] or float(plo[0]) > tratto[1]):
                continue
            lo = np.minimum(lo, np.asarray(plo, F) - pad)
            hi = np.maximum(hi, np.asarray(phi, F) + pad)
        return lo, hi


# ───────────────────────── pezzi da fondere nel corpo ─────────────────────────

def _poligono_2d(P, V):
    """Distanza con segno dai punti P (N, 2) al poligono chiuso V (M, 2): negativa dentro."""
    d2 = np.full(len(P), np.inf, F)
    dentro = np.zeros(len(P), bool)
    px, py = P[:, 0], P[:, 1]
    for i in range(len(V)):
        a, b = V[i], V[(i + 1) % len(V)]
        e = b - a
        wx, wy = px - a[0], py - a[1]
        tt = np.clip((wx * e[0] + wy * e[1]) / max(float(e @ e), 1e-12), 0, 1)
        dx, dy = wx - tt * e[0], wy - tt * e[1]
        d2 = np.minimum(d2, dx * dx + dy * dy)
        c = (a[1] > py) != (b[1] > py)
        den = b[1] - a[1] if abs(b[1] - a[1]) > 1e-12 else 1e-12
        dentro ^= c & (px < a[0] + (py - a[1]) * (b[0] - a[0]) / den)
    d = np.sqrt(d2)
    return np.where(dentro, -d, d).astype(F)


def _polilinea(P, V):
    """Distanza dai punti P (N, 2) alla spezzata aperta V (M, 2)."""
    d2 = np.full(len(P), np.inf, F)
    for i in range(len(V) - 1):
        a, b = V[i], V[i + 1]
        e = b - a
        w = P - a
        tt = np.clip((w @ e) / max(float(e @ e), 1e-12), 0, 1)
        dd = w - tt[:, None] * e
        d2 = np.minimum(d2, np.einsum('ij,ij->i', dd, dd))
    return np.sqrt(d2).astype(F)


def _cono_arr(p, a, b, r1, r2):
    """Coni arrotondati (Inigo Quilez) con parametri diversi riga per riga: p, a, b (N, 3), r1, r2 (N,)."""
    ba = b - a
    l2 = np.maximum(np.einsum('ij,ij->i', ba, ba), 1e-12)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = p - a
    y = np.einsum('ij,ij->i', pa, ba)
    z = y - l2
    xv = pa * l2[:, None] - y[:, None] * ba
    x2 = np.einsum('ij,ij->i', xv, xv)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    out = (np.sqrt(np.maximum(x2 * a2 * il2, 0)) + y * rr) * il2 - r1
    c1 = np.sign(z) * a2 * z2 > k
    c2 = (~c1) & (np.sign(y) * a2 * y2 < k)
    out = np.where(c1, np.sqrt(x2 + z2) * il2 - r2, out)
    out = np.where(c2, np.sqrt(x2 + y2) * il2 - r1, out)
    return out.astype(F)


def campo_coni(A, B, R1, R2, k=4):
    """Campo di tanti coni arrotondati (spine, chiodi, denti) da A (raggio R1) a B (raggio R2): per ogni punto
    solo i k più vicini (KD-tree sui punti di mezzo). Restituisce (campo, lo, hi)."""
    from scipy.spatial import cKDTree
    A, B = np.asarray(A, F).reshape(-1, 3), np.asarray(B, F).reshape(-1, 3)
    R1, R2 = np.asarray(R1, F).ravel(), np.asarray(R2, F).ravel()
    tree = cKDTree((A + B) * 0.5)
    kk = min(k, len(A))
    marg = float(R1.max()) + 0.003
    lo = np.minimum(A, B).min(0) - marg
    hi = np.maximum(A, B).max(0) + marg

    def f(P):
        out = np.full(len(P), LONTANO, F)
        m = np.all((P >= lo) & (P <= hi), axis=1)
        if m.any():
            Q = P[m]
            _, idx = tree.query(Q, k=kk, workers=-1)
            idx = np.asarray(idx).reshape(len(Q), kk)
            best = np.full(len(Q), LONTANO, F)
            for j in range(kk):
                i = idx[:, j]
                best = np.minimum(best, _cono_arr(Q, A[i], B[i], R1[i], R2[i]))
            out[m] = best
        return out
    return f, lo, hi


def campo_sfere(C, r):
    """Campo di tante sferette uguali (fotofori), con il KD-tree. (campo, lo, hi)"""
    from scipy.spatial import cKDTree
    C = np.asarray(C, F).reshape(-1, 3)
    tree = cKDTree(C)

    def f(P):
        d, _ = tree.query(P, k=1, workers=-1)
        return (d - r).astype(F)
    return f, C.min(0) - r - 0.004, C.max(0) + r + 0.004


def piastra(body: Body, fin: Fin, side=-1):
    """Pinna carnosa (squali, razze): una lastra con la sagoma della pinna, spessa alla radice e sottile al
    bordo, da fondere nel corpo con la sua pelle. Restituisce (campo, lo, hi)."""
    vb, a_mondo, da_mondo = body.telaio_pinne()
    roots, tips, fr = fin_points(vb, fin, side)
    R, T = np.array(roots, F), np.array(tips, F)
    if fr is None:
        o = np.zeros(3, F)
        e1, e2, en = np.array((1, 0, 0), F), np.array((0, 0, 1), F), np.array((0, 1, 0), F)
    else:
        o = R[0]
        e1, e2, en = fr

    def piano(Q):
        Q = Q - o
        return np.stack([Q @ e1, Q @ e2], axis=1).astype(F), (Q @ en).astype(F)
    radice = piano(R)[0]
    poly = np.concatenate([radice, piano(T)[0][::-1]])
    # il bordo libero resta spesso almeno un voxel della griglia (più grossa nelle anteprime veloci)
    H, th0, th1 = fin.size, fin.spessore, (0.0024 if FAST else 0.0015)
    th0 = max(th0, th1 * 1.5)
    tutti = np.concatenate([R, T])
    lo, hi = tutti.min(0) - th0 - 0.01, tutti.max(0) + th0 + 0.01

    def f(P):
        out = np.full(len(P), LONTANO, F)
        Q = da_mondo(P) if da_mondo is not None else P
        m = np.all((Q >= lo) & (Q <= hi), axis=1)
        if m.any():
            q2, qn = piano(Q[m])
            d2 = _poligono_2d(q2, poly)
            # spessa vicino alla radice, sottile verso il bordo libero
            th = th1 + (th0 - th1) * np.clip(1 - _polilinea(q2, radice) / (H * 0.9), 0, 1) ** 1.5
            wy = np.abs(qn) - th
            out[m] = np.minimum(np.maximum(d2, wy), 0) + np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(wy, 0) ** 2)
        return out
    if a_mondo is not None:
        cc = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])], F)
        cc = a_mondo(cc)
        lo, hi = cc.min(0), cc.max(0)
    return f, lo, hi


def sezione_rostro(r, x):
    """La sezione del rostro r alla x (x < 0, davanti al muso): (mezza larghezza, mezza altezza, quota del
    centro). Si assottiglia dritta fino a r.punta in punta; la curva alza (+) o abbassa (−) la punta."""
    s = np.clip(-x / float(r.lunghezza), 0.0, 1.0)
    k = 1.0 - (1.0 - r.punta) * s
    return r.larghezza * k, r.altezza * k, r.z + r.curva * s * s


def rostro_campo(body: Body):
    """Il rostro davanti al muso: una trave a sezione ellittica che si assottiglia verso la punta. 'tubo' ha
    la boccuccia in punta, 'sega' i denti sui due bordi larghi, 'becco' è tagliato in due mascelle dal taglio
    della bocca (in Body.field; i dentini sono un elemento a parte, denti_becco). Restituisce (campo, lo, hi)."""
    r = body.sh.rostro
    L = float(r.lunghezza)
    x_rad = 0.05            # la radice sta dentro la testa

    def sezione(x):
        return sezione_rostro(r, x)

    tip_z = r.z + r.curva
    tond = max(min(r.larghezza, r.altezza) * r.punta, 0.0015)

    def trave(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        wy, wz, zc = sezione(x)
        dz = z - zc
        k0 = np.sqrt((y / wy) ** 2 + (dz / wz) ** 2)
        k1 = np.sqrt((y / (wy * wy)) ** 2 + (dz / (wz * wz)) ** 2)
        d = k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)
        d = sdf.smax(d, -x - L, tond)
        d = np.maximum(d, x - x_rad)
        if r.tipo == 'tubo':
            bocca = np.linalg.norm(P - np.array((-L - 0.001, 0.0, tip_z), F), axis=1) - tond * 0.8
            d = sdf.smax(d, -bocca, 0.0012)
        return d.astype(F)
    f = trave
    if r.tipo == 'sega' and r.denti:
        # i denti della sega: coni corti sui due bordi larghi, un po' inclinati in avanti
        A, B, R1, R2 = [], [], [], []
        lungo_z = r.altezza >= r.larghezza
        for i in range(r.denti):
            x = -L * (0.05 + 0.92 * i / max(r.denti - 1, 1))
            wy, wz, zc = (float(np.asarray(a).ravel()[0]) for a in sezione(np.array([x], F)))
            spess = min(wy, wz)
            for sg in (-1, 1):
                if lungo_z:
                    a = np.array((x, 0.0, zc + sg * wz * 0.9), F)
                    b = a + np.array((-0.25, 0.0, sg * 1.0), F) * max(r.altezza, r.larghezza) * 0.55
                else:
                    a = np.array((x, sg * wy * 0.9, zc), F)
                    b = a + np.array((-0.25, sg * 1.0, 0.0), F) * max(r.altezza, r.larghezza) * 0.55
                A.append(a)
                B.append(b)
                R1.append(spess * 0.9)
                R2.append(spess * 0.2)
        fd, _, _ = campo_coni(A, B, R1, R2)

        def f(P):
            return np.minimum(trave(P), fd(P))
    big = max(r.larghezza, r.altezza)
    lo = np.array((-L - 0.01, -big * 1.8 - 0.01, min(r.z, tip_z) - big * 1.8 - 0.01), F)
    hi = np.array((x_rad + 0.01, big * 1.8 + 0.01, max(r.z, tip_z) + big * 1.8 + 0.01), F)
    return f, lo, hi


def _disco_orale_telaio(body: Body):
    """Centro, normale (dove guarda) e assi del disco orale della lampreda: in fondo al muso, avanti e giù."""
    do = body.sh.disco_orale
    R0 = do.raggio
    a = math.radians(do.inclinazione)
    n = np.array((-math.cos(a), 0.0, -math.sin(a)), F)
    zc, h, _ = (float(v[0]) for v in body.section(np.array([0.03], F)))
    C = np.array((0.012, 0.0, zc - h * 0.3), F) + n * R0 * 0.25
    e1 = np.array((0.0, 1.0, 0.0), F)
    e2 = np.cross(n, e1).astype(F)
    return C, n, e1, e2


def disco_orale_campo(body: Body):
    """La ventosa della lampreda: un disco carnoso rotondo davanti al muso (la conca si scava in field)."""
    R0 = body.sh.disco_orale.raggio
    C, n, _, _ = _disco_orale_telaio(body)

    def f(P):
        q = P - C
        hn = q @ n
        rad = np.linalg.norm(q - hn[:, None] * n, axis=1)
        a = rad - R0 * 0.82
        b = np.abs(hn + R0 * 0.1) - R0 * 0.22
        return (np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(b, 0) ** 2) + np.minimum(np.maximum(a, b), 0) - R0 * 0.18).astype(F)
    return f, C - R0 * 1.3, C + R0 * 1.3


def spine_campo(body: Body):
    """Le spine della pelle (Shape.spine): coni sulla pelle lungo la normale, coricati all'indietro."""
    A, B, R1, R2 = [], [], [], []
    lati_di = {'due': (-1, 1), 'sinistro': (-1,), 'destro': (1,), 'centro': (0,)}
    for sp in body.sh.spine:
        rng = np.random.default_rng(sp.seme)
        if sp.fila:
            ts, vs = np.linspace(sp.t0, sp.t1, sp.n), np.linspace(sp.v0, sp.v1, sp.n)
        else:
            ts, vs = rng.uniform(sp.t0, sp.t1, sp.n), rng.uniform(sp.v0, sp.v1, sp.n)
        for s in lati_di[sp.lati]:
            for t, v in zip(ts, vs):
                p, nrm = body.superficie(float(t), float(v), s)
                av = np.array((1.0, 0.0, 0.0), F) - nrm * float(nrm[0])
                av /= np.linalg.norm(av) + 1e-9
                d = nrm * (1 - sp.inclinazione) + av * sp.inclinazione
                d /= np.linalg.norm(d)
                A.append(p - nrm * sp.raggio * 0.6)
                B.append(p + d * sp.lunghezza)
                R1.append(sp.raggio)
                R2.append(sp.raggio * 0.15)
    return campo_coni(A, B, R1, R2)


# ───────────────────────── materiali ─────────────────────────

def _finestra(g, d: Disegno, u, v, sfuma=0.03):
    """La fascia del disegno (u0..u1, v0..v1) con i bordi morbidi; i lati aperti (0, 1, ±1) non sfumano."""
    m = None
    parti = []
    if d.u0 > 0.0:
        parti.append(g.smoothstep(d.u0 - sfuma, d.u0 + sfuma, u))
    if d.u1 < 1.0:
        parti.append(g.smoothstep(d.u1 + sfuma, d.u1 - sfuma, u))
    if d.v0 > -1.0:
        parti.append(g.smoothstep(d.v0 - sfuma * 2, d.v0 + sfuma * 2, v))
    if d.v1 < 1.0:
        parti.append(g.smoothstep(d.v1 + sfuma * 2, d.v1 - sfuma * 2, v))
    for q in parti:
        m = q if m is None else g.mul(m, q)
    return m


def disegno(g, d: Disegno, k, u, v, co, col):
    """Un disegno generico della pelle (Disegno, in pesci_specie/base.py) sopra il colore col. Restituisce
    (colore, maschera del metallo o None)."""
    t = d.tipo
    m = None
    metallo = None
    if t == 'strisce':
        passo = (d.v1 - d.v0) / max(d.n, 1)
        vv = v
        if d.inclinazione:
            vv = g.sub(vv, g.mul(u, d.inclinazione))
        if d.onda:
            vv = g.add(vv, g.mul(g.math('SINE', g.mul(u, 38.0)), d.onda))
        fase = g.math('FRACT', g.div(g.sub(vv, d.v0), passo))
        dist = g.mul(g.math('ABSOLUTE', g.sub(fase, 0.5)), passo)
        mezza = d.larghezza * 0.5
        m = g.smoothstep(mezza + 0.012, max(mezza - 0.012, 0.0), dist)
        fin = _finestra(g, Disegno('x', u0=d.u0, u1=d.u1, v0=d.v0, v1=d.v1), u, vv)
        m = m if fin is None else g.mul(m, fin)
    elif t == 'bande':
        passo = (d.u1 - d.u0) / max(d.n, 1)
        uu = u
        if d.inclinazione:
            uu = g.add(uu, g.mul(v, d.inclinazione))
        if d.onda:
            nz = g.noise(co, scale=30.0, detail=3.0)
            uu = g.add(uu, g.mul(g.sub(nz.fac, 0.5), d.onda))
        fase = g.math('FRACT', g.div(g.sub(uu, d.u0), passo))
        dist = g.math('ABSOLUTE', g.sub(fase, 0.5))
        mezza = d.larghezza * 0.5
        m = g.smoothstep(mezza + 0.04, max(mezza - 0.04, 0.0), dist)
        fin = _finestra(g, d, u, v)
        m = m if fin is None else g.mul(m, fin)
    elif t == 'barre':
        _, wv = g.wave(g.comb(u, g.mul(v, 0.35), 0.0), scale=d.n * 2.7, distortion=2.2 + d.onda, detail=2.0, kind='BANDS', axis='X')
        m = g.smoothstep(0.6, 0.75, wv)
        fin = _finestra(g, d, u, v)
        m = m if fin is None else g.mul(m, fin)
    elif t in ('macchie', 'punti'):
        scala = d.scala if t == 'macchie' else max(d.scala, 160.0)
        r = d.r if t == 'macchie' else min(d.r, 0.2)
        dist = g.voronoi(g.vmath('ADD', co, (d.seme * 3.1, d.seme * 1.7, 0.0)), scale=scala, feature='F1', randomness=1.0)
        rc = g.voronoi(g.vmath('ADD', co, (d.seme * 3.1, d.seme * 1.7, 0.0)), scale=scala, feature='F1', randomness=1.0, out='Color')
        rx, _, _ = g.sep(rc)
        rr = g.mul(g.add(0.6, g.mul(rx, 0.8)), r)          # le macchie non sono tutte uguali
        m = g.smoothstep(g.add(rr, 0.05), g.sub(rr, 0.05), dist)
        if d.colore2 is not None:
            alone = g.mul(g.smoothstep(g.add(rr, 0.16), g.add(rr, 0.04), dist), g.sub(1.0, m))
            fin = _finestra(g, d, u, v)
            alone = alone if fin is None else g.mul(alone, fin)
            col = g.mix(g.mul(alone, d.forza), col, d.colore2)
        fin = _finestra(g, d, u, v)
        m = m if fin is None else g.mul(m, fin)
    elif t in ('macchia', 'ocello'):
        # vicinanza al centro (attributo macchia<k>, da base_attrs): 1 al centro, 2/3 sul bordo, 0 lontano
        a = g.attr(f'macchia{k}')
        m = g.smoothstep(0.62, 0.72, a)
        if t == 'ocello':
            anello = g.mul(g.smoothstep(0.5, 0.56, a), g.sub(1.0, m))
            col = g.mix(g.mul(anello, d.forza), col, d.colore2 if d.colore2 is not None else (0.85, 0.72, 0.35))
    elif t == 'marmo':
        nz = g.noise(co, scale=d.scala * 0.25, detail=6.0, rough=0.62, distortion=0.5 + d.onda)
        c = max(0.0, min(1.0, d.r))
        m = g.smoothstep(0.62 - 0.3 * c, 0.68 - 0.3 * c, nz.fac)
        fin = _finestra(g, d, u, v)
        m = m if fin is None else g.mul(m, fin)
    elif t == 'reticolo':
        e = g.voronoi(co, scale=d.scala, feature='DISTANCE_TO_EDGE')
        m = g.smoothstep(d.larghezza, d.larghezza * 0.3, e)
        fin = _finestra(g, d, u, v)
        m = m if fin is None else g.mul(m, fin)
    elif t == 'vermi':
        _, wv = g.wave(co, scale=d.scala * 0.25, distortion=9.0, detail=4.0, kind='BANDS', axis='X')
        m = g.smoothstep(0.78, 0.92, wv)
        fin = _finestra(g, d, u, v)
        m = m if fin is None else g.mul(m, fin)
    elif t == 'linea':
        vl = g.add(d.v, g.mul(u, d.inclinazione))
        if d.onda:
            vl = g.add(vl, g.mul(g.math('SINE', g.mul(u, 2 * math.pi * 3.0)), d.onda))
        dist = g.math('ABSOLUTE', g.sub(v, vl))
        mezza = d.larghezza * 0.5
        m = g.smoothstep(mezza + 0.01, mezza, dist)
        if d.n:
            # gli scudetti del suro: più chiari in mezzo, scuri fra uno e l'altro
            sc = g.math('ABSOLUTE', g.sub(g.math('FRACT', g.mul(u, d.n)), 0.5))
            m = g.mul(m, g.add(0.35, g.mul(g.smoothstep(0.3, 0.46, sc), 0.65)))
        fin = _finestra(g, Disegno('x', u0=d.u0, u1=d.u1), u, v)
        m = m if fin is None else g.mul(m, fin)
    elif t == 'ventre':
        m = g.smoothstep(d.v1 + 0.15, d.v1 - 0.15, v)
        fin = _finestra(g, Disegno('x', u0=d.u0, u1=d.u1), u, v)
        m = m if fin is None else g.mul(m, fin)
        metallo = g.mul(m, d.forza)
    elif t == 'sfumatura':
        m = _finestra(g, d, u, v, sfuma=max(d.larghezza, 0.01))
        if m is None:
            m = 1.0
    else:
        raise ValueError(f'disegno sconosciuto: {t!r}')
    col = g.mix(g.mul(m, d.forza) if t != 'ventre' else m, col, d.colore)
    return col, metallo


def fish_skin(name, lk: Look, rot=0.0, wounds=False, slime=False, alto=False, parti=()):
    """Pelle di pesce: dorso scuro, fianchi argentati, ventre chiaro, squame, linea laterale, disegno della
    specie. Attributi: 'u' (lungo il corpo), 'v' (quota normalizzata), 'rot', 'wound', 'blood', 'tar', 'mouth';
    alto: sui pesci visti dall'alto il dorso è il lato verso la camera (attributo 'dv'); parti: i pezzi fusi
    da colorare a parte ('pinna': le pinne carnose; 'rostro'), vedi Body.attr_parti."""
    m, g = material(name)
    co = g.texcoord('Object')
    u, v = g.attr('u'), g.attr('v')
    dv = g.attr('dv') if alto else v
    # colore base per quota
    col = g.mix(g.smoothstep(-0.55, 0.15, dv), lk.belly, lk.flank)
    col = g.mix(g.smoothstep(0.25, 0.75, dv), col, lk.back)
    pat = lk.pattern
    if pat == 'mackerel':
        # barre scure ondulate sul dorso
        _, wv = g.wave(g.comb(g.mul(u, 1.0), g.mul(v, 0.35), 0.0), scale=16.0, distortion=2.2, detail=2.0, kind='BANDS', axis='X')
        bars = g.mul(g.smoothstep(0.6, 0.75, wv), g.smoothstep(0.15, 0.4, v))
        col = g.mix(g.mul(bars, 0.92), col, lk.pattern_col)
    elif pat == 'bream':
        # righe sottili lungo il corpo, macchia scura sull'opercolo, la riga d'oro tra gli occhi
        lines = g.smoothstep(0.75, 0.95, g.math('SINE', g.mul(v, 26.0)))
        col = g.mix(g.mul(lines, 0.25), col, (0.10, 0.11, 0.12))
        gold = g.mul(g.smoothstep(0.32, 0.55, v), g.mul(g.smoothstep(0.11, 0.13, u), g.smoothstep(0.17, 0.15, u)))
        col = g.mix(gold, col, (0.95, 0.66, 0.16))
        spot = g.mul(g.smoothstep(0.30, 0.42, v), g.mul(g.smoothstep(0.255, 0.27, u), g.smoothstep(0.31, 0.29, u)))
        col = g.mix(g.mul(spot, 0.9), col, (0.03, 0.025, 0.03))
    elif pat == 'salema':
        st = g.smoothstep(0.55, 0.85, g.math('SINE', g.add(g.mul(v, 22.0), g.mul(u, 1.5))))
        col = g.mix(g.mul(g.mul(st, g.smoothstep(-0.8, -0.5, v)), 0.85), col, (0.92, 0.70, 0.12))
    elif pat == 'redmullet':
        stripe = g.mul(g.smoothstep(0.06, 0.0, g.math('ABSOLUTE', g.sub(v, 0.05))), g.smoothstep(0.12, 0.25, u))
        col = g.mix(g.mul(stripe, 0.85), col, (0.92, 0.70, 0.16))
        stripe2 = g.mul(g.smoothstep(0.05, 0.0, g.math('ABSOLUTE', g.sub(v, -0.25))), g.smoothstep(0.2, 0.3, u))
        col = g.mix(g.mul(stripe2, 0.55), col, (0.9, 0.62, 0.2))
    elif pat == 'barracuda':
        _, wv = g.wave(g.comb(g.add(u, g.mul(v, -0.06)), 0.0, 0.0), scale=26.0, kind='BANDS', axis='X', distortion=0.6)
        bars = g.mul(g.smoothstep(0.62, 0.8, wv), g.mul(g.smoothstep(-0.05, 0.3, v), g.smoothstep(0.15, 0.25, u)))
        col = g.mix(g.mul(bars, 0.7), col, (0.05, 0.06, 0.08))
    # i disegni generici della specie, in ordine
    metalli = []
    for k, d in enumerate(lk.disegni):
        col, mm = disegno(g, d, k, u, v, co, col)
        if mm is not None:
            metalli.append(mm)
    # le pinne carnose del colore delle pinne, il rostro (spada, becco) del colore del dorso
    if 'pinna' in parti and lk.tinta_pinne:
        col = g.mix(g.mul(g.attr('pinna'), lk.tinta_pinne), col, lk.fin)
    if 'rostro' in parti and lk.tinta_rostro:
        col = g.mix(g.mul(g.attr('rostro'), lk.tinta_rostro), col, lk.back)
    if 'ventosa' in parti:
        # la ventosa della remora: il disco più chiaro del dorso, i solchi fra le lamelle scuri
        chiaro = tuple(min(1.0, c * 2.0 + 0.06) for c in lk.flank)
        col = g.mix(g.mul(g.attr('ventosa'), 0.8), col, chiaro)
        col = g.mix(g.mul(g.attr('lamelle'), 0.85), col, tuple(c * 0.3 for c in lk.back))
    # linea laterale
    if lk.linea_laterale > 0:
        la, lb = lk.linea_v
        lat = g.mul(g.smoothstep(0.018, 0.0, g.math('ABSOLUTE', g.sub(v, g.add(la, g.mul(u, lb))))), g.smoothstep(0.22, 0.3, u))
        col = g.mix(g.mul(lat, 0.45 * lk.linea_laterale), col, (0.06, 0.06, 0.07))
    fine = None
    if lk.squame > 0:
        # squame: celle allungate lungo il corpo
        sc = g.voronoi(g.comb(g.mul(u, 150.0), g.mul(v, 34.0), 0.0), scale=1.0, feature='DISTANCE_TO_EDGE', dims='3D')
        scale_edge = g.smoothstep(0.0, 0.14, sc)
        col = g.mix(g.mul(g.sub(1.0, scale_edge), 0.09 * lk.squame), col, (0.02, 0.02, 0.025))
        metal = g.mul(g.smoothstep(-0.9, 0.5, dv), lk.metal)
        rough = g.mixf(scale_edge, 0.42, 0.2)
        fine = g.noise(co, scale=180.0, detail=2.0)
        h = g.add(g.mul(scale_edge, 0.35 * lk.squame), g.mul(fine.fac, 0.2))
    else:
        # pelle liscia (squali, razze, anguille): niente squame, solo la grana
        metal = g.mul(g.smoothstep(-0.9, 0.5, dv), lk.metal)
        rough = 0.32
        fine = g.noise(co, scale=180.0, detail=2.0)
        h = g.mul(fine.fac, 0.2)
    if lk.ruvido is not None:
        rough = lk.ruvido
    for mm in metalli:
        metal = g.mx(metal, mm)
    if rot:
        # marciume: chiazze grigio-verdi, squame cadute, muffa
        rotw = g.attr('rot')
        mold = g.noise(co, scale=40.0, detail=5.0, rough=0.65)
        rc = g.mix(g.smoothstep(0.45, 0.7, mold.fac), (0.20, 0.22, 0.17), (0.34, 0.36, 0.26))
        col = g.mix(g.mul(g.smoothstep(0.2, 0.6, rotw), 0.95), col, rc)
        metal = g.mul(metal, g.sub(1.0, rotw))
        rough = g.mixf(rotw, rough, 0.7)
        # carne esposta dove il marciume è profondo
        deep = g.smoothstep(0.75, 0.9, rotw)
        col = g.mix(deep, col, (0.42, 0.30, 0.28))
        h = g.add(h, g.mul(mold.fac, g.mul(rotw, 1.2)))
        # desaturato tutto, un velo giallastro
        bwv = g.bw(col)
        col = g.mix(0.45, col, g.comb(g.mul(bwv, 0.92), g.mul(bwv, 0.95), g.mul(bwv, 0.82)))
    if wounds:
        ww = g.attr('wound')
        bl = g.attr('blood')
        fl = g.noise(co, scale=90.0, detail=3.0)
        flesh = g.mix(g.smoothstep(0.4, 0.7, fl.fac), (0.40, 0.03, 0.035), (0.62, 0.10, 0.10))
        col = g.mix(g.mul(bl, 0.85), col, (0.18, 0.012, 0.015))
        col = g.mix(g.smoothstep(0.3, 0.7, ww), col, flesh)
        metal = g.mul(metal, g.sub(1.0, g.mx(ww, bl)))
        rough = g.mixf(g.mx(ww, bl), rough, 0.12)
        h = g.add(h, g.mul(fl.fac, g.mul(ww, 1.5)))
    if slime:
        lw = g.attr('lump')
        vv = g.voronoi(co, scale=90.0, feature='DISTANCE_TO_EDGE')
        lumpc = g.mix(g.smoothstep(0.02, 0.0, vv), (0.12, 0.05, 0.07), (0.45, 0.06, 0.08))
        col = g.mix(g.smoothstep(0.1, 0.6, lw), col, lumpc)
        h = g.add(h, g.mul(lw, g.mul(g.smoothstep(0.02, 0.0, vv), 1.5)))
        tar = g.attr('tar')
        col = g.mix(g.smoothstep(0.2, 0.6, tar), col, (0.008, 0.008, 0.009))
        rough = g.mixf(g.smoothstep(0.2, 0.6, tar), rough, 0.05)
        metal = g.mul(metal, g.sub(1.0, tar))
    if pat == 'bream':
        # la riga d'oro tra gli occhi resta, anche nel marcio
        gold2 = g.mul(g.smoothstep(0.2, 0.45, v), g.mul(g.smoothstep(0.105, 0.125, u), g.smoothstep(0.185, 0.165, u)))
        col = g.mix(gold2, col, (0.85, 0.58, 0.12))
        metal = g.mixf(gold2, metal, 0.85)
    mouth = g.attr('mouth')
    col = g.mix(g.smoothstep(0.3, 0.8, mouth), col, lk.bocca_col)
    nrm = g.bump(h, strength=0.25, distance=0.002)
    kw = {}
    if lk.alfa < 1.0:
        kw['alpha'] = lk.alfa
    bsdf = g.principled(color=col, metal=metal, rough=rough, coat=lk.lucido, coat_rough=0.05, normal=nrm, coat_normal=nrm,
                        thin_film=g.mul(g.smoothstep(-0.2, 0.6, dv), lk.irid * 380.0), spec=0.6, **kw)
    g.output_material(bsdf)
    return m


def fin_material(name, color, spiny=False, tears=0.0, bone=False, membrane=1.0, bordo=None, macchie=0.0,
                 colore_macchie=(0.10, 0.25, 0.55)):
    """Membrana con i raggi (u = indice del raggio, v = dalla radice al bordo). tears: buchi e strappi;
    bordo: colore del bordo libero; macchie: puntini sulla membrana."""
    m, g = material(name)
    uv = g.texcoord('UV')
    u, v, _ = g.sep(uv)
    co = g.texcoord('Object')
    ray = g.pow(g.math('ABSOLUTE', g.math('COSINE', g.mul(u, math.pi))), 18.0)   # 1 sui raggi, 0 in mezzo
    ray_col = (0.70, 0.66, 0.55) if bone else (color[0] * 0.55, color[1] * 0.55, color[2] * 0.55)
    col = g.mix(g.mul(ray, 0.85), color, ray_col)
    if macchie:
        sp = g.voronoi(co, scale=70.0, feature='F1', randomness=1.0)
        col = g.mix(g.mul(g.smoothstep(0.3, 0.18, sp), macchie), col, colore_macchie)
    # il bordo più scuro e sporco
    if bordo is None:
        col = g.mix(g.mul(g.smoothstep(0.55, 1.0, v), 0.45), col, (color[0] * 0.4, color[1] * 0.4, color[2] * 0.42))
    else:
        col = g.mix(g.mul(g.smoothstep(0.7, 0.9, v), 0.9), col, bordo)
    alpha = g.mixf(ray, membrane * (0.82 if not spiny else 0.7), 1.0)
    alpha = g.mul(alpha, g.smoothstep(1.02, 0.94, v))
    if tears:
        n = g.noise(co, scale=55.0, detail=4.0, rough=0.6)
        holes = g.smoothstep(0.62 - tears * 0.18, 0.66 - tears * 0.18, n.fac)
        ragged = g.smoothstep(1.0 - tears * 0.55, 1.0 - tears * 0.35, g.add(v, g.mul(n.fac, 0.5)))
        keep = g.mx(g.mul(ray, 0.9), g.sub(1.0, g.mx(holes, ragged)))
        alpha = g.mul(alpha, keep)
    bsdf = g.principled(color=col, rough=0.5, coat=0.1, coat_rough=0.2, spec=0.3,
                        alpha=alpha, normal=g.bump(ray, strength=0.35, distance=0.001))
    trans = g.translucent(g.vmath('SCALE', col, scale=0.35))
    g.output_material(g.mix_shader(0.05, bsdf, trans))
    return m


def human_eye(name, iris=(0.35, 0.45, 0.30), iris_r=0.42, pupil=0.16):
    """Occhio da persona (sclera bianca venata, iride piccola): sui pesci corrotti è la cosa peggiore."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(x, z, 0.0))
    front = g.smoothstep(0.1, -0.45, y)
    n = g.noise(co, scale=6.0, detail=5.0, rough=0.6)
    col = g.mix(g.mul(g.smoothstep(0.4, 0.8, n.fac), 0.3), (0.80, 0.77, 0.70), (0.86, 0.78, 0.66))
    vv = g.voronoi(co, scale=7.0, feature='DISTANCE_TO_EDGE')
    veins = g.mul(g.smoothstep(0.012, 0.0, vv), g.smoothstep(0.35, 0.9, r))
    col = g.mix(g.mul(veins, 0.75), col, (0.55, 0.06, 0.05))
    ang = g.math('ARCTAN2', z, x)
    fib = g.noise(g.comb(g.mul(ang, 6.0), g.mul(r, 9.0), 0.0), scale=2.5, detail=5.0, rough=0.65)
    ir = g.mix(g.smoothstep(0.3, 0.75, fib.fac), (iris[0] * 0.55, iris[1] * 0.55, iris[2] * 0.55), iris)
    ir = g.mix(g.smoothstep(iris_r - 0.07, iris_r, r), ir, (0.05, 0.05, 0.05))
    col = g.mix(g.mul(g.smoothstep(iris_r + 0.015, iris_r - 0.015, r), front), col, ir)
    col = g.mix(g.mul(g.smoothstep(pupil + 0.02, pupil - 0.02, r), front), col, (0.005, 0.005, 0.006))
    g.output_material(g.principled(color=col, rough=0.3, coat=1.0, coat_rough=0.02, spec=0.6, sss=0.12,
                                   sss_radius=(1, 0.6, 0.5), sss_scale=0.004))
    return m


def bone_material(name='Bone', dirt=0.4, tinta=None):
    """Osso sporco; tinta: moltiplica i colori (le ossa verdi dell'aguglia)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    n = g.noise(co, scale=30.0, detail=5.0, rough=0.6)
    n2 = g.noise(co, scale=160.0, detail=2.0)
    c1, c2 = (0.78, 0.74, 0.62), (0.58, 0.50, 0.36)
    if tinta is not None:
        c1, c2 = tuple(a * b for a, b in zip(c1, tinta)), tuple(a * b for a, b in zip(c2, tinta))
    col = g.mix(g.smoothstep(0.4, 0.75, n.fac), c1, c2)
    col = g.mix(g.mul(g.smoothstep(0.62, 0.8, n.fac), dirt), col, (0.22, 0.14, 0.09))
    ao = g.ao(distance=0.012, samples=8)
    col = g.mix(g.mul(g.sub(1.0, ao), 0.85), col, (0.12, 0.08, 0.05))
    g.output_material(g.principled(color=col, rough=0.32, sss=0.25, sss_radius=(1, 0.8, 0.6), sss_scale=0.004,
                                   coat=0.45, coat_rough=0.08, normal=g.bump(g.add(n.fac, g.mul(n2.fac, 0.4)), strength=0.25, distance=0.0015)))
    return m


def thread_material():
    m = bpy.data.materials.get('Thread')
    if m:
        return m
    m, g = material('Thread')
    co = g.texcoord('Object')
    _, tw = g.wave(co, scale=420.0, kind='BANDS', axis='X', distortion=1.0)
    col = g.mix(g.mul(tw, 0.5), (0.05, 0.04, 0.03), (0.15, 0.11, 0.07))
    g.output_material(g.principled(color=col, rough=0.55, coat=0.3, normal=g.bump(tw, strength=0.3, distance=0.0005)))
    return m


def blood_material():
    m = bpy.data.materials.get('Blood')
    if m:
        return m
    m, g = material('Blood')
    g.output_material(g.principled(color=(0.22, 0.004, 0.006), rough=0.04, coat=1.0, coat_rough=0.02, transmission=0.25,
                                   sss=0.6, sss_radius=(1.0, 0.1, 0.05), sss_scale=0.01, ior=1.4))
    return m


def tar_material():
    m = bpy.data.materials.get('Tar')
    if m:
        return m
    m, g = material('Tar')
    co = g.texcoord('Object')
    n = g.noise(co, scale=70.0, detail=2.0)
    g.output_material(g.principled(color=(0.006, 0.006, 0.008), rough=0.03, coat=1.0, coat_rough=0.01, spec=0.8,
                                   normal=g.bump(n.fac, strength=0.1, distance=0.001)))
    return m


def dirty_teeth_material():
    m = bpy.data.materials.get('DirtyTeeth')
    if m:
        return m
    m, g = material('DirtyTeeth')
    co = g.texcoord('Object')
    n = g.noise(co, scale=120.0, detail=3.0)
    col = g.mix(g.smoothstep(0.45, 0.7, n.fac), (0.78, 0.72, 0.56), (0.45, 0.36, 0.22))
    col = g.mix(g.mul(g.smoothstep(0.62, 0.75, n.fac), 0.8), col, (0.30, 0.02, 0.02))
    g.output_material(g.principled(color=col, rough=0.25, sss=0.3, sss_radius=(1, 0.8, 0.6), sss_scale=0.002, coat=0.6))
    return m


def materiale(name, colore, rough=0.4, coat=0.5, metal=0.0, sss=0.0, emissione=None, forza=0.0):
    """Un materiale semplice a tinta unita (per gli extra delle specie e per i pezzi in più)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    kw = {}
    if emissione is not None:
        kw.update(emission=emissione, emission_strength=forza)
    g.output_material(g.principled(color=colore, rough=rough, coat=coat, metal=metal, sss=sss, sss_radius=(1, 0.5, 0.3),
                                   sss_scale=0.004, **kw))
    return m


# ───────────────────────── pinne ─────────────────────────

def fin_points(body: Body, fin: Fin, side=-1, rng=None, tears_geo=0.0):
    """Le radici e le punte dei raggi di una pinna (fin.rays + 1 ciascuna) sul corpo dato, e il telaio delle
    pinne pari (asse lungo, secondo asse, normale; None per dorsali, anali e caudali, che stanno in y = 0)."""
    outline = np.array(fin.outline, F)
    seg = np.linalg.norm(np.diff(outline, axis=0), axis=1)
    s_ = np.concatenate([[0], np.cumsum(seg)])
    s_ /= s_[-1]
    ss = np.linspace(0, 1, fin.rays + 1)
    edge = np.stack([np.interp(ss, s_, outline[:, 0]), np.interp(ss, s_, outline[:, 1])], axis=1)
    k = fin.kind
    zc1, h1, _ = (float(a[0]) for a in body.section(np.array([1.0], F)))
    frame = None
    if k in ('pectoral', 'pelvic'):
        t0 = fin.a
        zc, h, _ = (float(a[0]) for a in body.section(np.array([t0], F)))
        if fin.z is None:
            z0 = zc - h * (0.3 if k == 'pectoral' else 0.86)
        else:
            z0 = zc + h * fin.z
        if fin.dir is None:
            back = np.array((1.0, side * (0.35 if k == 'pectoral' else 0.25), -0.05 if k == 'pectoral' else -0.4), F)
        else:
            back = np.array((fin.dir[0], side * fin.dir[1], fin.dir[2]), F)
        back /= np.linalg.norm(back)
        if fin.su is None:
            perp = np.array((0.0, side * (0.25 if k == 'pectoral' else 0.45), 1.0), F)
        else:
            perp = np.array((fin.su[0], side * fin.su[1], fin.su[2]), F)
        perp -= back * (perp @ back)
        perp /= np.linalg.norm(perp)
        nrm = np.cross(back, perp)
        frame = (back, perp, nrm)

    def root(i):
        f = ss[i]
        if k == 'dorsal':
            t = fin.a + (fin.b - fin.a) * f
            return np.array((t, 0.0, float(body.top(np.array([t], F))[0]) - 0.003), F)
        if k == 'anal':
            t = fin.a + (fin.b - fin.a) * f
            return np.array((t, 0.0, float(body.bot(np.array([t], F))[0]) + 0.003), F)
        if k == 'caudal':
            return np.array((0.99, 0.0, zc1 + h1 * 0.9 * (1 - 2 * f)), F)
        t = fin.a + (fin.b - fin.a) * f
        z = z0 + (fin.b - fin.a) * 0.4 * (f - 0.5)
        return np.array((t, side * (float(body.surface_y(t, z)) + 0.0015), z), F)

    def tip(i):
        ea, eo = float(edge[i, 0]), float(edge[i, 1])
        jit = 1.0 - tears_geo * float(rng.uniform(0.0, 0.45)) if rng is not None else 1.0
        if k in ('dorsal', 'anal'):
            t = fin.a + (fin.b - fin.a) * ea
            sgn = 1.0 if k == 'dorsal' else -1.0
            zb = float((body.top if k == 'dorsal' else body.bot)(np.array([min(t, 1.0)], F))[0])
            r = root(i)
            return r + (np.array((t + eo * fin.size * 0.35, 0.0, zb + sgn * eo * fin.size), F) - r) * jit
        if k == 'caudal':
            r = root(i)
            return r + (np.array((0.99 + ea * fin.size, 0.0, zc1 + eo * fin.size * 0.42), F) - r) * jit
        r0 = root(0)
        return r0 + (frame[0] * ea + frame[1] * eo) * fin.size * jit

    roots, tips = [], []
    for i in range(fin.rays + 1):
        roots.append(root(i))
        tips.append(tip(i))
    return roots, tips, frame


def fin_mesh(name, body: Body, fin: Fin, mat, side=-1, tears_geo=0.0, seed=0, a_mondo=None):
    """Mesh a raggi: ogni raggio va dalla radice a un punto della sagoma (uv: u = indice del raggio,
    v = dalla radice al bordo), con la membrana appena ondulata fra un raggio e l'altro."""
    rng = np.random.default_rng(seed)
    roots, tips, frame = fin_points(body, fin, side, rng, tears_geo)
    rows = 8
    k = fin.kind
    verts, uvs = [], []
    for i in range(fin.rays + 1):
        a, b = roots[i], tips[i]
        for r in range(rows + 1):
            f = r / rows
            p = a + (b - a) * f
            # pieghe della membrana: i raggi alterni appena fuori piano
            off = (0.0011 if k != 'caudal' else 0.0014) * (1 if i % 2 else -1) * f
            if k in ('dorsal', 'anal', 'caudal'):
                p = p + np.array((0.0, off, 0.0), F)
            else:
                p = p + frame[2] * off
                # le pinne pari si incurvano verso il corpo in punta
                p = p + np.array((0.0, -side * 0.006 * f * f, 0.0), F)
            verts.append(p)
            uvs.append((float(i), f))
    verts = np.array(verts, F)
    if a_mondo is not None:
        verts = a_mondo(verts)
    n = rows + 1
    faces = []
    for i in range(fin.rays):
        for r in range(rows):
            a = i * n + r
            faces.append((a, a + 1, a + n + 1, a + n))
    ob = mesh_from_arrays(name, verts, faces, smooth=True, col=COL)
    uvl = ob.data.uv_layers.new(name='UVMap')
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            vi = ob.data.loops[li].vertex_index
            uvl.data[li].uv = uvs[vi]
    so = ob.modifiers.new('S', 'SOLIDIFY')
    so.thickness = 0.0016
    so.offset = 0.0
    sub = ob.modifiers.new('Sub', 'SUBSURF')
    sub.levels = sub.render_levels = 1
    ob.data.materials.append(mat)
    set_lightgroup(ob, 'ambient')
    return ob


def build_fins(body: Body, lk: Look, family: str, seed=0):
    obs = []
    tears = {'zombie': 0.75, 'skeletal': 0.0, 'bleeding': 0.12}.get(family, 0.0)
    vb, a_mondo, _ = body.telaio_pinne()
    for i, fin in enumerate(body.sh.fins):
        if fin.carnosa:
            continue            # è già nel corpo (piastra)
        if family == 'skeletal':
            mat = fin_material(f'FinBone{i}', (0.45, 0.42, 0.36), spiny=fin.spiny, tears=0.6, bone=True, membrane=0.35)
        else:
            mat = fin_material(f'Fin{i}', fin.colore if fin.colore is not None else lk.fin, spiny=fin.spiny, tears=tears,
                               bordo=fin.bordo, macchie=fin.macchie, colore_macchie=fin.colore_macchie)
        sides = (-1, 1) if fin.kind in ('pectoral', 'pelvic') else (-1,)
        for s in sides:
            obs.append(fin_mesh(f'Fin_{fin.kind}_{i}_{s}', vb, fin, mat, side=s, tears_geo=tears, seed=seed + i, a_mondo=a_mondo))
    return obs


def a_fascia(lo, hi, res):
    """Griglia fine solo vicino alla superficie: sempre nei render finali; nelle anteprime veloci solo se la
    griglia piena sarebbe enorme (corpi grandi con code e spade lunghe), così restano veloci."""
    return (not FAST) or float(np.prod((np.asarray(hi) - np.asarray(lo)) / res)) > 3e6


# ───────────────────────── attributi della pelle ─────────────────────────

def _vicinanza_macchia(body: Body, d: Disegno):
    """Attributo di una macchia o di un ocello: 1 al centro, 2/3 sul bordo (raggio d.r), 0 a tre raggi; la
    macchia è in (u, v) sul fianco sinistro, con la sua gemella sul destro."""
    v = d.v
    if body.razza:
        zc, h, _ = (float(a[0]) for a in body.section(np.array([d.u], F)))
        v = (d.v * body.zmax - zc) / h
    p0, _ = body.superficie(d.u, v, -1)
    p1 = p0 * np.array((1, -1, 1), F)
    sc = np.array((1.0 / max(d.allungamento, 1e-3), 1.0, 1.0), F)

    def f(p):
        dist = np.minimum(np.linalg.norm((p - p0) * sc, axis=1), np.linalg.norm((p - p1) * sc, axis=1))
        return np.clip(1.0 - dist / (3.0 * d.r), 0, 1).astype(F)
    return f


def base_attrs(body: Body, extra=None, lk: Look | None = None):
    def u(p):
        return np.clip(p[:, 0], 0, 1).astype(F)

    def v(p):
        return np.clip(body.norm_v(p), -1.2, 1.2).astype(F)
    if body.razza:
        zm = body.zmax

        def v(p):       # noqa: F811 — sulle razze v è la posizione sull'apertura del disco
            return np.clip(p[:, 2] / zm, -1.2, 1.2).astype(F)

    def mouth(p):
        return np.zeros(len(p), F)
    a = {'u': u, 'v': v, 'mouth': mouth}
    if body.alto:
        # dorso (+1, il lato verso la camera) e ventre (−1) dei pesci visti dall'alto
        a['dv'] = lambda p: np.tanh(-p[:, 1] / 0.003).astype(F)
    a.update(body.attr_parti())
    if lk is not None:
        for k, d in enumerate(lk.disegni):
            if d.tipo in ('macchia', 'ocello'):
                a[f'macchia{k}'] = _vicinanza_macchia(body, d)
    if extra:
        a.update(extra)
    return a


def eyes(body: Body, lk: Look, cloudy=False, name='Eye'):
    if cloudy:
        mat = cloudy_eye('FishCloudyEye', sclera=(0.70, 0.70, 0.64), iris=(0.62, 0.64, 0.6), pupil_col=(0.5, 0.52, 0.5), iris_r=0.75, pupil=0.4)
    else:
        mat = eye_material(name + 'Mat', iris=lk.iris, iris_dark=lk.iris_dark, pupil=lk.pupilla, pupil_size=0.5,
                           shine=(0.6, 0.7, 0.5), shine_strength=0.25, sclera=lk.iris_dark)
    obs = []
    for k, (c, r, look) in enumerate(body.occhi_lista()):
        ob = eyeball(f'{name}{(-1, 1)[k] if k < 2 else k}', tuple(map(float, c)), r, mat, look=look, col=COL)
        if body.sh.eye_allungato != 1.0:
            ob.scale.x *= body.sh.eye_allungato
        obs.append(ob)
    return obs


# ───────────────────────── le famiglie ─────────────────────────

def build_normal(body: Body, lk: Look, family: str, extra_field=None, extra_attrs=None, mouth_open=0.0, res=0.0022):
    if not mouth_open:
        mouth_open = body.sh.bocca_aperta
    f = body.field(mouth_open=mouth_open)
    if extra_field:
        f = extra_field(f)
    lo, hi = body.bounds()
    if mouth_open:
        lo[2] -= 0.06
    attrs = base_attrs(body, extra_attrs, lk)
    if mouth_open:
        attrs['mouth'] = body.mouth_attr
    res = res if not FAST else res * 2
    ob = sdf_object('Body', f, lo, hi, res=res, attrs=attrs, col=COL, banded=a_fascia(lo, hi, res))
    ob.data.materials.append(fish_skin('Skin', lk, rot=1.0 if family == 'zombie' else 0.0,
                                       wounds=family == 'bleeding', slime=family == 'corrupt', alto=body.alto,
                                       parti=tuple(body.attr_parti())))
    return ob


def barbels(body: Body, mat):
    obs = []
    for s in (-1, 1):
        a = np.array((0.035, s * 0.012, body.sh.mouth_z1 - 0.012), F)
        pts = [a + np.array((0.012 * k, s * 0.004 * k, -0.018 * k + 0.0015 * k * k), F) for k in range(7)]
        parts = [sdf.round_cone(pts[k], pts[k + 1], 0.0026 * (1 - k / 8), 0.0026 * (1 - (k + 1) / 8)) for k in range(6)]
        fb = sdf.union(*parts)
        lo = np.minimum(pts[0], pts[-1]) - 0.01
        hi = np.maximum(pts[0], pts[-1]) + 0.01
        o = sdf_object(f'Barbel{s}', fb, lo, hi, res=0.0008, col=COL)
        o.data.materials.append(mat)
        obs.append(o)
    return obs


def skeletal(body: Body, lk: Look, seed=3, vertebre=34, costole_fino=0.55, emali_da=0.5, cranio_t=None,
             striscia=None, striscia_v=0.6, striscia_fino=0.9, peduncolo=0.9, occhi=True, osso=None, raggi_disco=None):
    """Lisca, cranio, costole; resta la striscia di pelle del dorso con le righe, e gli occhi.
    Opzioni: vertebre (quante), costole_fino (fin dove arrivano le costole), emali_da (da dove le spine di
    sotto), cranio_t (dove finisce il cranio; None: dietro l'opercolo), striscia (la pelle del dorso; None:
    sì, tranne sulle razze) con striscia_v (da che quota) e striscia_fino (fin dove), peduncolo (da dove resta
    carnosa la coda; None: niente), occhi (False: le orbite vuote), osso (tinta delle ossa, per esempio verde).
    Le razze (piano 'razza'): il cranio è solo il tronco, le vertebre non hanno spine né costole (starebbero
    nel piano delle ali) e le ali diventano raggi di cartilagine a ventaglio: raggi_disco = quanti per ala
    (None: 30; 0: niente)."""
    rng = np.random.default_rng(seed)
    sh = body.sh
    obs = []
    bone = bone_material() if osso is None else bone_material('BoneTinto', tinta=osso)
    raw = body.field(socket=True)
    x_skull = sh.gill_t + 0.01 if cranio_t is None else cranio_t
    if striscia is None:
        striscia = not body.razza
    # cranio: la testa erosa, con l'orbita grande e il buco dell'opercolo
    n3 = sdf.Noise3(seed)
    occhi_l = body.occhi_lista()

    gill_c = [np.array((sh.gill_t - 0.035, s_ * 0.0, float(body.section(np.array([sh.gill_t - 0.035], F))[0][0])), F) for s_ in (-1, 1)]

    def skull(p):
        d = raw(p) + 0.0025
        if body.razza:
            # sulle razze il cranio è solo il tronco (il rostro davanti resta): le ali sono i raggi di cartilagine
            zc_, h_, _ = body.section(np.clip(p[:, 0], 0, 1))
            d = np.maximum(d, np.where(p[:, 0] > 0.0, np.abs(p[:, 2] - zc_) - h_ * 1.1, -1.0))
        # il bordo posteriore del cranio, frastagliato
        d = np.maximum(d, p[:, 0] - x_skull - 0.012 * n3(p, scale=0.015, octaves=2))
        for ec, r, _ in occhi_l:
            # orbite vuote e larghe
            d = sdf.smax(d, -(np.linalg.norm(p - ec, axis=1) - r * 1.45), 0.004)
        for s_ in (-1, 1):
            # niente opercolo: si vedono gli archi delle branchie
            c = gill_c[0] + np.array((0, s_ * 0.0, 0), F)  # noqa: F841
            zc, h, w = body.section(np.array([sh.gill_t - 0.035], F))
            q = (p - np.array((sh.gill_t - 0.03, s_ * float(w[0]), float(zc[0])), F)) / np.array((0.05, 0.035, float(h[0]) * 0.75), F)
            d = sdf.smax(d, -(np.linalg.norm(q, axis=1) - 1.0) * 0.03, 0.003)
        # buchi e vaiolature dell'osso
        d = d + 0.0022 * np.maximum(n3(p, scale=0.012, octaves=2), 0)
        return d

    # gli archi delle branchie, dentro il buco dell'opercolo
    arches = []
    zc, h, w = (float(a[0]) for a in body.section(np.array([sh.gill_t - 0.04], F)))
    for k in range(4):
        xk = sh.gill_t - 0.065 + k * 0.012
        for s_ in (-1, 1):
            pts = []
            for j in range(7):
                a = math.radians(-70 + 140 * j / 6)
                pts.append(np.array((xk - 0.012 * math.cos(a), s_ * w * (0.55 - 0.05 * k) * math.cos(a) * 0.6, zc + h * 0.62 * math.sin(a)), F))
            for j in range(6):
                arches.append(sdf.round_cone(pts[j], pts[j + 1], 0.0018, 0.0016))
    arch_f = sdf.union(*arches)

    lo, hi = body.bounds(tratto=(-10.0, x_skull + 0.02))
    hi[0] = x_skull + 0.02
    res = 0.0016 if not FAST else 0.004
    o = sdf_object('Skull', lambda p: sdf.smin(skull(p), arch_f(p), 0.002), lo, hi, res=res, col=COL, banded=a_fascia(lo, hi, res))
    o.data.materials.append(bone)
    obs.append(o)
    # colonna vertebrale e spine
    nv = vertebre
    xs = np.linspace(x_skull - 0.01, 1.0, nv + 1)
    parts = []
    for i in range(nv):
        x0, x1 = xs[i] + 0.0015, xs[i + 1] - 0.0015
        xm = (x0 + x1) / 2
        zc, h, w = body.section(np.array([xm], F))
        zc, h, w = float(zc[0]), float(h[0]), float(w[0])
        r = max(0.0035, min(h, w) * 0.16)
        a, b, c = np.array((x0, 0, zc), F), np.array((xm, 0, zc), F), np.array((x1, 0, zc), F)
        parts.append(sdf.round_cone(a, b, r, r * 0.72))
        parts.append(sdf.round_cone(b, c, r * 0.72, r))
        if body.razza:
            continue        # le razze: solo le vertebre (spine e costole starebbero nel piano delle ali)
        # spina neurale (in su e indietro) e, dalla metà in poi, emale (in giù)
        top = zc + h * 0.92
        parts.append(sdf.round_cone(b + (0, 0, r * 0.6), np.array((xm + h * 0.45, 0, top), F), r * 0.32, r * 0.12))
        if xm > emali_da:
            parts.append(sdf.round_cone(b - (0, 0, r * 0.6), np.array((xm + h * 0.45, 0, zc - h * 0.9), F), r * 0.3, r * 0.1))
        elif xm < costole_fino:
            # costole: archi che scendono lungo la sezione, a destra e a sinistra
            for s in (-1, 1):
                pts = []
                for k in range(6):
                    ang = math.radians(-12 - 95 * k / 5)
                    rr = 0.86 + 0.04 * rng.uniform(-1, 1)
                    pts.append(np.array((xm + 0.012 * k / 5, s * w * rr * math.cos(ang), zc + h * rr * math.sin(ang)), F))
                pts[0] = b.copy()
                for k in range(5):
                    parts.append(sdf.round_cone(pts[k], pts[k + 1], r * 0.26, r * 0.2))
    spine = sdf.union(*parts, k=0.0015)
    lo, hi = body.bounds(solo_corpo=True)
    lo[0] = x_skull - 0.03
    res = 0.0014 if not FAST else 0.0035
    o = sdf_object('Spine', spine, lo, hi, res=res, col=COL, banded=a_fascia(lo, hi, res))
    o.data.materials.append(bone)
    obs.append(o)
    if body.razza and body.disco is not None and raggi_disco != 0:
        obs += raggi_cartilagine(body, bone, 30 if raggi_disco is None else raggi_disco, seme=seed)
    # la striscia di pelle del dorso, strappata ai bordi, che pende sopra la lisca
    rawb = body.raw()

    def strip(p):
        d = np.abs(rawb(p) + 0.003) - 0.0025
        v = body.norm_v(p)
        edge = striscia_v + 0.2 * n3(p, scale=0.03, octaves=3)
        d = np.maximum(d, (edge - v) * 0.05)
        holes = n3(p + 7.0, scale=0.018, octaves=2)
        d = np.maximum(d, (holes - 0.28) * 0.02)
        d = np.maximum(d, x_skull + 0.02 - p[:, 0])
        d = np.maximum(d, p[:, 0] - striscia_fino)
        return d
    res = 0.0016 if not FAST else 0.0035
    if striscia:
        lo, hi = body.bounds(tratto=(x_skull, striscia_fino + 0.03))
        o = sdf_object('SkinStrip', strip, lo, hi, res=res, col=COL, attrs=base_attrs(body, lk=lk), banded=a_fascia(lo, hi, res))
        o.data.materials.append(fish_skin('StripSkin', lk, alto=body.alto, parti=tuple(body.attr_parti())))
        obs.append(o)
    # il peduncolo della coda resta carnoso (tiene la pinna)

    def ped(p):
        cut = peduncolo + 0.025 * n3(p, scale=0.012, octaves=2) - 0.02 * np.clip(body.norm_v(p), -1, 1)
        return np.maximum(rawb(p), cut - p[:, 0])
    if peduncolo is not None:
        lo, hi = body.bounds(tratto=(peduncolo - 0.06, 10.0))
        o = sdf_object('Peduncle', ped, lo, hi, res=res, col=COL, attrs=base_attrs(body, lk=lk), banded=a_fascia(lo, hi, res))
        o.data.materials.append(fish_skin('PedSkin', lk, alto=body.alto, parti=tuple(body.attr_parti())))
        obs.append(o)
    if occhi:
        obs += eyes(body, lk)
    return obs


def raggi_cartilagine(body: Body, mat, n=30, seme=0):
    """Lo scheletro delle ali delle razze (famiglia skeletal, piano 'razza'): n raggi di cartilagine per ala, a
    ventaglio dal fianco del tronco al bordo del disco (i primi in avanti verso il muso, gli ultimi indietro
    verso l'angolo dell'ala), appena piegati e a segmenti come le ossicine vere. Stanno nel piano del disco;
    un oggetto solo (campo_coni). Restituisce [oggetto] (o [] se il disco non sporge dal tronco)."""
    rng = np.random.default_rng(seme)
    ts = np.linspace(0.0, 1.0, 801, dtype=F)
    ala = body.disco.top(ts)
    tronco = body.section(ts)[1]                     # la mezza larghezza del tronco, in z
    fuori = np.nonzero(ala > tronco * 1.15 + 0.004)[0]
    if len(fuori) == 0:
        return []
    t0, t1 = float(ts[fuori[0]]), float(ts[fuori[-1]])
    A, B, R1, R2 = [], [], [], []

    def osso(a, b, r1, r2):
        A.append(a)
        B.append(b)
        R1.append(r1)
        R2.append(r2)

    def radice(f, sz):
        """Il punto della radice sul fianco del tronco (f = 0 il primo raggio, 1 l'ultimo)."""
        tr = t0 + (t1 - t0) * (0.18 + 0.72 * f)
        return np.array((tr, 0.0, sz * float(body.section(np.array([tr], F))[1][0]) * 0.92), F)
    segmenti = 7
    for sz in (-1.0, 1.0):
        radici = []
        for i in range(n):
            f = i / max(n - 1, 1)
            tt = t0 + (t1 - t0) * f                  # la punta, lungo il bordo dell'ala
            a = radice(f, sz)
            b = np.array((tt, 0.0, sz * float(body.disco.top(np.array([tt], F))[0]) * 0.96), F)
            radici.append(a)
            # una curva dolce (Bézier): a metà il raggio si piega appena all'indietro
            m = (a + b) * 0.5 + np.array((0.012 + 0.004 * rng.uniform(-1, 1), 0.0, 0.0), F)
            pts = [(1 - u) ** 2 * a + 2 * u * (1 - u) * m + u * u * b for u in np.linspace(0, 1, segmenti + 1)]
            for k in range(segmenti):
                rr = 0.0019 * (1 - 0.5 * k / segmenti)
                osso(pts[k], pts[k + 1], rr, rr * 0.72)     # ogni pezzo si stringe in fondo: cartilagine a segmenti
        # la cartilagine lunga lungo il fianco del tronco, che regge tutti i raggi
        for a, b in zip(radici[:-1], radici[1:]):
            osso(a, b, 0.0028, 0.0028)
    # le due cinture di traverso, dalla cartilagine di un lato a quella dell'altro passando per la colonna:
    # quella delle pettorali (davanti) e quella delle pelviche (in fondo)
    for f in (0.3, 0.97):
        osso(radice(f, -1.0), radice(f, 1.0), 0.0032, 0.0032)
    f, lo, hi = campo_coni(A, B, R1, R2)
    return [oggetto_sdf('RaggiDisco', f, lo, hi, mat, res=0.0008 if FAST else 0.0005)]


def zombie(body: Body, lk: Look, seed=5, cucitura=(0.26, 0.64, -0.52), punti=13, occhi='lattiginosi', marcio=0.45):
    """Marcio: chiazze, squame cadute, occhi lattiginosi, pinne strappate, una cucitura lungo la pancia.
    Opzioni: cucitura = (t0, t1, v) il solco sul fianco sinistro (None: niente), punti (quanti), occhi
    ('lattiginosi' | 'normali' | None = niente occhi), marcio (soglia del rumore: più bassa, più marcio)."""
    sh = body.sh  # noqa: F841
    n3 = sdf.Noise3(seed)
    rng = np.random.default_rng(seed)
    seam_pts = None
    if cucitura is not None:
        # la cucitura: un solco lungo il ventre, sul fianco sinistro
        seam_x = np.linspace(cucitura[0], cucitura[1], 60, dtype=F)
        seam_v = cucitura[2] + 0.06 * np.sin(seam_x * 23.0)
        zc, h, _ = body.section(seam_x)
        seam_z = zc + h * seam_v
        seam_y = -body.surface_y(seam_x, seam_z)
        seam_pts = np.stack([seam_x, seam_y, seam_z], axis=1)

    def rot(p):
        r = n3(p, scale=0.06, octaves=4) * 0.5 + 0.5
        return np.clip((r - marcio) * 2.6, 0, 1).astype(F)

    def ex_field(f):
        from scipy.spatial import cKDTree
        tree = cKDTree(seam_pts) if seam_pts is not None else None

        def g(p):
            d = f(p)
            # incavi dove il marciume è profondo
            r = rot(p)
            d = d + 0.003 * np.clip((r - 0.7) * 3, 0, 1)
            if tree is not None:
                dist, _ = tree.query(p, k=1, workers=-1)
                d = d + 0.0035 * np.exp(-(dist / 0.0025) ** 2)
            return d
        return g
    ob = build_normal(body, lk, 'zombie', extra_field=ex_field, extra_attrs={'rot': rot})
    obs = [ob]
    # i punti: fili scuri che attraversano il solco
    thread = thread_material()
    for k in range(punti if seam_pts is not None else 0):
        i = int(4 + k * (len(seam_pts) - 8) / max(punti - 1, 1))
        p0 = seam_pts[i]
        tangent = seam_pts[min(i + 1, len(seam_pts) - 1)] - seam_pts[max(i - 1, 0)]
        tangent /= np.linalg.norm(tangent)
        nrm = np.array((0, -1, 0), F)
        side = np.cross(tangent, nrm)
        side /= np.linalg.norm(side)
        a = p0 + side * 0.009 + tangent * rng.uniform(-0.002, 0.002)
        b = p0 - side * 0.009 + tangent * rng.uniform(-0.002, 0.002)
        mid = p0 + nrm * 0.0035
        fb = sdf.union(sdf.round_cone(a, mid, 0.0011, 0.0013), sdf.round_cone(mid, b, 0.0013, 0.0011), k=0.001)
        o = sdf_object(f'Stitch{k}', fb, np.minimum(a, b) - 0.006, np.maximum(a, b) + 0.006, res=0.0005, col=COL)
        o.data.materials.append(thread)
        obs.append(o)
    if occhi:
        obs += eyes(body, lk, cloudy=occhi == 'lattiginosi')
    return obs


OCCHI_CORROTTI = [(0.215, 0.28, 0.022), (0.44, 0.08, 0.033), (0.31, -0.42, 0.015)]   # (t, v, raggio)
IRIDI_CORROTTE = [(0.30, 0.42, 0.28), (0.22, 0.36, 0.55), (0.42, 0.26, 0.12)]


def corrupt(body: Body, lk: Look, seed=7, occhi_extra=None, iridi=None, escrescenza=(0.58, -0.5, 0.024), colature=2):
    """Tre occhi in più (da persona) che guardano la camera, melma nera che cola, un'escrescenza; i baffi.
    Opzioni: occhi_extra = [(t, v, raggio)] sul fianco sinistro, iridi = un colore per occhio, escrescenza =
    (t, v, raggio) o None, colature (dai primi quanti occhi cola la pece)."""
    sh = body.sh
    rng = np.random.default_rng(seed)
    extra_eyes = OCCHI_CORROTTI if occhi_extra is None else occhi_extra
    centers = []
    for t, v, r in extra_eyes:
        zc, h, _ = body.section(np.array([t], F))
        z = float(zc[0] + h[0] * v)
        y = -float(body.surface_y(t, z)) + r * 0.42
        centers.append((np.array((t, y, z), F), r))
    lump_c = None
    if escrescenza is not None:
        lt, lv, lr = escrescenza
        zc, h, _ = body.section(np.array([lt], F))
        lz = float(zc[0] + h[0] * lv)
        lump_c = np.array((lt, -float(body.surface_y(lt, lz)) + 0.006, lz), F)
    n3 = sdf.Noise3(seed)

    def tar(p):
        v = np.zeros(len(p), F)
        n = n3(p, scale=0.012, octaves=2)
        for c, r in centers:
            d = np.linalg.norm(p - c, axis=1)
            v = np.maximum(v, np.clip(1 - (d - r * 1.25) / 0.006, 0, 1))
            # colature corte e irregolari sotto l'occhio
            dx = (p[:, 0] - c[0] - 0.004 * n) / (r * 0.55)
            below = np.clip((c[2] - p[:, 2]) / (0.022 + 0.012 * n), 0, 1)
            lane = np.exp(-dx * dx * 3) * (below < 1) * (p[:, 2] < c[2])
            v = np.maximum(v, lane * 0.95)
        return v.astype(F)

    def lump(p):
        if lump_c is None:
            return np.zeros(len(p), F)
        return np.clip(1 - (np.linalg.norm(p - lump_c, axis=1) - lr) / 0.01, 0, 1).astype(F)

    def ex_field(f):
        def g(p):
            d = f(p)
            for c, r in centers:
                d = sdf.smax(d, -(np.linalg.norm(p - c, axis=1) - r * 1.02), 0.003)
                # palpebra carnosa: un anello sottile attorno all'occhio, un po' indietro
                q = p - c
                ring = np.sqrt((np.sqrt(q[:, 0] ** 2 + q[:, 2] ** 2) - r * 1.02) ** 2 + (q[:, 1] - r * 0.12) ** 2) - r * 0.17
                d = sdf.smin(d, ring, 0.002)
            if lump_c is not None:
                lumpd = np.linalg.norm(p - lump_c, axis=1) - (lr + 0.002) - 0.007 * n3(p, scale=0.01, octaves=2)
                d = sdf.smin(d, lumpd, 0.01)
            return d
        return g
    ob = build_normal(body, lk, 'corrupt', extra_field=ex_field, extra_attrs={'tar': tar, 'lump': lump})
    obs = [ob]
    obs += eyes(body, lk)
    irises = IRIDI_CORROTTE if iridi is None else iridi
    for k, ((c, r), ir) in enumerate(zip(centers, irises)):
        mat = human_eye(f'HumanEye{k}', iris=ir)
        look = (float(rng.uniform(-0.12, 0.05)), -1.0, float(rng.uniform(-0.05, 0.1)))
        obs.append(eyeball(f'ExtraEye{k}', tuple(map(float, c)), r, mat, look=look, col=COL))
    tm = tar_material()
    for k, (c, r) in enumerate(centers[:colature]):
        a = c + np.array((0.002, -r * 0.35, -r * 1.05), F)
        fb = drip(a, 0.03 + 0.012 * k, r0=0.0022, r1=0.005, dir=(0.08, -0.2, -1))
        o = sdf_object(f'TarDrip{k}', fb, a - 0.06, a + 0.06, res=0.0007, col=COL)
        o.data.materials.append(tm)
        obs.append(o)
    if sh.barbels:
        obs += barbels(body, fish_skin('BarbelSkin', lk))
    return obs


FERITE_SANGUINANTI = [((0.30, 0.25), (0.42, -0.35)), ((0.52, 0.45), (0.60, -0.15)), ((0.70, 0.30), (0.74, -0.30))]


def bleeding(body: Body, lk: Look, seed=9, ferite=None, bocca=None, denti=9, sangue_bocca=None, carne=0.0):
    """Ferite aperte con la carne viva, sangue che cola, bocca aperta con i denti sporchi.
    Opzioni: ferite = [((t0, v0), (t1, v1))] tagli sul fianco sinistro, bocca (gradi di apertura; 0:
    chiusa, senza denti; None: 22 se la bocca è il taglio di sempre, 0 per le bocche ventrali degli squali e
    per chi non ha bocca), denti (per mascella e per lato), sangue_bocca (la goccia dal labbro; None: solo
    con la bocca di sempre), carne (0..1: la pelle che manca dappertutto, carne viva su tutto il corpo: lo
    Scorticano)."""
    sh = body.sh
    if bocca is None:
        bocca = 22.0 if sh.bocca == 'terminale' else 0.0
    if sangue_bocca is None:
        sangue_bocca = sh.bocca == 'terminale'
    rng = np.random.default_rng(seed)
    gashes = FERITE_SANGUINANTI if ferite is None else ferite
    segs = []
    for (t0, v0), (t1, v1) in gashes:
        pts = []
        for (t, v) in ((t0, v0), (t1, v1)):
            zc, h, _ = body.section(np.array([t], F))
            z = float(zc[0] + h[0] * v)
            pts.append(np.array((t, -float(body.surface_y(t, z)), z), F))
        segs.append(pts)

    def seg_dist(p, a, b):
        ab = b - a
        tt = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
        return np.linalg.norm(p - (a + tt[:, None] * ab), axis=1), tt

    def wound(p):
        v = np.zeros(len(p), F)
        for a, b in segs:
            d, tt = seg_dist(p, a, b)
            wdt = 0.009 * np.sin(np.pi * np.clip(tt, 0.02, 0.98)) + 0.0015
            v = np.maximum(v, np.clip(1 - (d - wdt) / 0.003, 0, 1))
        if carne:
            v = np.maximum(v, carne)
        return v.astype(F)

    def blood(p):
        v = np.zeros(len(p), F)
        for a, b in segs:
            d, tt = seg_dist(p, a, b)
            lowest = np.minimum(a[2], b[2])
            below = np.clip((lowest + 0.004 - p[:, 2]) / 0.04, 0, 1)
            streak = np.exp(-(d / 0.012) ** 2) + below * np.exp(-((p[:, 0] - (a[0] + b[0]) / 2) / 0.03) ** 2) * 0.6
            v = np.maximum(v, np.clip(streak, 0, 1))
        return v.astype(F)

    def ex_field(f):
        def g(p):
            d = f(p)
            for a, b in segs:
                dist, tt = seg_dist(p, a, b)
                wdt = 0.009 * np.sin(np.pi * np.clip(tt, 0.02, 0.98)) + 0.002
                d = sdf.smax(d, -(dist - wdt), 0.002)
            return d
        return g
    ob = build_normal(body, lk, 'bleeding', extra_field=ex_field, extra_attrs={'wound': wound, 'blood': blood}, mouth_open=bocca)
    obs = [ob]
    obs += eyes(body, lk)
    # denti: zanne lungo le due mascelle, verso l'interno della bocca
    tm = dirty_teeth_material()
    R = sdf.rot_matrix('y', -bocca)
    hinge = np.array((sh.mouth_t, 0.0, sh.mouth_z1), F)
    for jaw in (('upper', 'lower') if bocca else ()):
        n = denti
        for k in range(n):
            x = 0.008 + (sh.mouth_t - 0.02) * k / (n - 1)
            for s in (-1, 1):
                zl = float(body.mouth_line(np.array([x], F))[0])
                y = s * float(body.surface_y(x, zl)) * 0.8
                ln = (0.010 if k in (1, 5) else 0.006) * (1.3 if jaw == 'lower' else 1.0) * rng.uniform(0.8, 1.2)
                base = np.array((x, y, zl + (0.002 if jaw == 'upper' else -0.002)), F)
                tip = base + np.array((rng.uniform(-0.002, 0.003), -s * 0.001, -ln if jaw == 'upper' else ln), F)
                if jaw == 'lower':
                    base = (base - hinge) @ R.T + hinge
                    tip = (tip - hinge) @ R.T + hinge
                obs.append(tooth(f'Tooth_{jaw}_{k}_{s}', tuple(map(float, base)), tuple(map(float, tip)), 0.0016 + ln * 0.08, tm, col=COL))
    # gocce di sangue sotto le ferite e dalla bocca
    bm = blood_material()
    for k, (a, b) in enumerate(segs):
        low = a if a[2] < b[2] else b
        anchor = low + np.array((0.0, -0.001, -0.002), F)
        fb = drip(anchor, rng.uniform(0.025, 0.05), r0=0.0022, r1=0.0048, dir=(0.0, -0.1, -1))
        o = sdf_object(f'BloodDrip{k}', fb, anchor - 0.06, anchor + 0.06, res=0.0006, col=COL)
        o.data.materials.append(bm)
        obs.append(o)
    if sangue_bocca:
        lip = (np.array((0.02, -0.006, sh.mouth_z1 - 0.004), F) - hinge) @ R.T + hinge
        fb = drip(lip, 0.04, r0=0.0018, r1=0.0042, dir=(0.0, -0.05, -1))
        o = sdf_object('BloodMouth', fb, lip - 0.06, lip + 0.06, res=0.0006, col=COL)
        o.data.materials.append(bm)
        obs.append(o)
    return obs


def glitch_post(img, seed=11, doppio=0.035, bande=9, separa=0.006, blocchi=4, righe=0.86, **effetti):
    """Il nastro sfasato sull'immagine RGBA (0..1): bande che scorrono di lato, colori separati, un doppio
    spostato, righe, blocchi a pixel. Opzioni (Specie.opzioni dei glitchati): doppio (spostamento del
    doppio, frazione della larghezza), bande (quante strappate), separa (colori separati), blocchi (a
    pixel), righe (quanto scuriscono le righe: 1 = niente); poi gli effetti in più (effetti_glitch), tutti
    spenti di default."""
    rng = np.random.default_rng(seed)
    H, W = img.shape[:2]
    out = img.copy()
    # doppio sfasato, tenue
    ghost = np.roll(img, int(W * doppio), axis=1)
    a = ghost[..., 3:4] * 0.28
    out[..., :3] = out[..., :3] * (1 - a) + ghost[..., :3] * a * np.array((0.6, 1.0, 1.2))
    out[..., 3:4] = np.maximum(out[..., 3:4], a)
    # bande strappate
    for _ in range(bande):
        h = int(H * rng.uniform(0.01, 0.06))
        y = int(rng.uniform(0.05, 0.9) * H)
        dx = int(W * rng.uniform(-0.05, 0.05))
        out[y:y + h] = np.roll(out[y:y + h], dx, axis=1)
    # colori separati
    rgb = out.copy()
    out[..., 0] = np.roll(rgb[..., 0], -int(W * separa), axis=1)
    out[..., 2] = np.roll(rgb[..., 2], int(W * separa), axis=1)
    out[..., 3] = np.maximum.reduce([rgb[..., 3], np.roll(rgb[..., 3], -int(W * separa), axis=1), np.roll(rgb[..., 3], int(W * separa), axis=1)])
    # blocchi a pixel
    for _ in range(blocchi):
        bw, bh = int(W * rng.uniform(0.04, 0.12)), int(H * rng.uniform(0.04, 0.1))
        x0, y0 = int(rng.uniform(0.15, 0.8) * W), int(rng.uniform(0.2, 0.75) * H)
        blk = out[y0:y0 + bh, x0:x0 + bw]
        s = max(4, int(W * 0.008))
        small = blk[::s, ::s]
        out[y0:y0 + bh, x0:x0 + bw] = np.repeat(np.repeat(small, s, axis=0), s, axis=1)[:blk.shape[0], :blk.shape[1]]
    # righe
    out[::3, :, :3] *= righe
    if effetti:
        out = effetti_glitch(np.clip(out, 0, 1), seed=seed + 1, **effetti)
    return np.clip(out, 0, 1)


def _tinta(rgb, gradi):
    """Ruota la tinta dei colori (nello spazio YIQ) di tanti gradi."""
    a = math.radians(gradi)
    T = np.array([[0.299, 0.587, 0.114], [0.596, -0.274, -0.322], [0.211, -0.523, 0.312]], np.float32)
    R = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]], np.float32)
    M = np.linalg.inv(T) @ R @ T
    return rgb @ M.T.astype(np.float32)


def effetti_glitch(img, seed=12, saturazione=1.0, sfocatura=0.0, onda=0.0, copie=0, pixel=0, puntini=0,
                   interlacciato=0.0, neve=0.0, tinta_bande=0.0, buchi=0.0):
    """Gli effetti di nastro rovinato per i glitchati, da mettere nelle opzioni della specie (si sommano al
    glitch di sempre). Tutti spenti di default:
    saturazione  colori troppo accesi (> 1) o sbiaditi (< 1)                 (Donzella Saturata)
    sfocatura    raggio della sfocatura, in frazioni della larghezza          (Balestra Sfocata)
    onda         righe che ondeggiano di lato, ampiezza in frazioni della larghezza (Anguilla Smagnetizzata)
    copie        copie a scatti dietro il pesce, sempre più tenui            (Pettine a Scatti)
    pixel        pixel grossi su tutto, lato del quadretto in pixel          (Pagello Pixelato)
    puntini      retinatura a puntini, lato della cella in pixel             (Castagnola Sgranata)
    interlacciato 0..1: le righe dispari spariscono                          (Re di Triglie a Righe)
    neve         0..1: neve televisiva dentro la sagoma                      (Menola Neve, Torpedine Statica)
    tinta_bande  0..1: bande orizzontali con la tinta girata                 (Lampuga Fuori Traccia)
    buchi        0..1: bande orizzontali sparite, come un canale che non prende (Leccia Senza Segnale)"""
    rng = np.random.default_rng(seed)
    H, W = img.shape[:2]
    out = img.copy()
    if copie:
        # copie dietro il pesce, spostate a scatti verso la coda, ognuna più tenue
        base = out.copy()
        for k in range(copie, 0, -1):
            sh = np.roll(base, int(W * 0.055 * k), axis=1)
            a = sh[..., 3:4] * (0.5 / k) * (1 - out[..., 3:4])
            out[..., :3] = out[..., :3] + sh[..., :3] * a
            out[..., 3:4] = out[..., 3:4] + a
    if onda:
        y = np.arange(H)
        dx = (onda * W * np.sin(2 * np.pi * y / (H * 0.23) + rng.uniform(0, 6.28))).astype(int)
        cols = (np.arange(W)[None, :] - dx[:, None]) % W
        out = out[y[:, None], cols]
    if sfocatura:
        from scipy.ndimage import gaussian_filter
        r = sfocatura * W
        pre = out[..., :3] * out[..., 3:4]
        a = gaussian_filter(out[..., 3], r)
        pre = np.stack([gaussian_filter(pre[..., i], r) for i in range(3)], axis=2)
        out = np.concatenate([pre / np.maximum(a[..., None], 1e-4), a[..., None]], axis=2)
    if saturazione != 1.0:
        g = (out[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32))[..., None]
        out[..., :3] = g + (out[..., :3] - g) * saturazione
    if tinta_bande:
        y = 0
        while y < H:
            h = int(H * rng.uniform(0.03, 0.09))
            if rng.random() < tinta_bande:
                out[y:y + h, :, :3] = _tinta(out[y:y + h, :, :3], rng.uniform(60, 300))
            y += h
    if pixel:
        p = int(pixel)
        small = out[::p, ::p]
        out = np.repeat(np.repeat(small, p, axis=0), p, axis=1)[:H, :W]
    if puntini:
        c = int(puntini)
        yy, xx = np.mgrid[0:H, 0:W]
        cy, cx = (yy // c) * c + c / 2, (xx // c) * c + c / 2
        small = out[::c, ::c]
        cel = np.repeat(np.repeat(small, c, axis=0), c, axis=1)[:H, :W]
        lum = (cel[..., :3] @ np.array((0.299, 0.587, 0.114), np.float32)) * cel[..., 3]
        rad = c * 0.5 * np.sqrt(np.clip(lum * 1.6 + 0.15 * cel[..., 3], 0, 1.2))
        dentro = np.hypot(yy - cy + 0.5, xx - cx + 0.5) < rad
        out = np.concatenate([cel[..., :3], (cel[..., 3] * dentro)[..., None]], axis=2)
    if interlacciato:
        # righe alte mezzo centesimo dell'immagine (2 px nelle anteprime, 4 nei finali), una sì e una no
        hl = max(1, H // 200)
        dispari = (np.arange(H) // hl) % 2 == 1
        out[dispari, :, 3] *= 1 - interlacciato
        out[dispari, :, :3] *= 1 - interlacciato * 0.5
    if neve:
        n = rng.random((H, W)).astype(np.float32)
        a = out[..., 3] * neve
        out[..., :3] = out[..., :3] * (1 - a[..., None]) + n[..., None] * a[..., None]
    if buchi:
        y = int(H * 0.05)
        while y < H:
            h = int(H * rng.uniform(0.02, 0.07))
            if rng.random() < buchi:
                out[y:y + h, :, 3] *= 0.0
            y += h + int(H * rng.uniform(0.02, 0.1))
    return np.clip(out, 0, 1)


# ───────────────────────── elementi in più (oggetti) ─────────────────────────

def oggetto_sdf(name, campo, lo, hi, mat, res=0.0008, attrs=None):
    """Un oggetto da un campo (per gli elementi e per gli extra delle specie): nella collezione dei pesci,
    con la griglia fine solo vicino alla superficie se il riquadro è grande."""
    lo, hi = np.asarray(lo, F), np.asarray(hi, F)
    grande = float(np.prod((hi - lo) / res)) > 4e6
    o = sdf_object(name, campo, lo, hi, res=res, attrs=attrs, col=COL, banded=grande)
    o.data.materials.append(mat)
    return o


def filamento(body: Body, lk: Look, fl: Filamento, k=0, mat=None):
    """Un barbiglio, un cirro o un filamento (Filamento): una catena di coni che si assottiglia."""
    if mat is None:
        mat = materiale(f'Filamento{k}', fl.colore, rough=0.45, coat=0.4) if fl.colore is not None else fish_skin('BarbelSkin', lk, alto=body.alto)
    obs = []
    lati = {'due': (-1, 1), 'sinistro': (-1,), 'destro': (1,), 'centro': (0,)}[fl.lati]
    for s in lati:
        if fl.xyz is not None:
            a = np.array((fl.xyz[0], (s or 1) * fl.xyz[1], fl.xyz[2]), F)
        else:
            a, _ = body.superficie(fl.t, fl.v, s)
        m = 1.0 if s == 0 else -s       # 'fuori' è −y sul lato sinistro
        d = np.array((fl.dir[0], -m * fl.dir[1] if s else 0.0, fl.dir[2]), F)
        d /= np.linalg.norm(d)
        cv = np.array((fl.curva[0], -m * fl.curva[1] if s else 0.0, fl.curva[2]), F)
        n = max(2, fl.segmenti)
        step = fl.lunghezza / n
        pts = [a - d * fl.raggio * 0.5]
        for _ in range(n):
            pts.append(pts[-1] + d * step)
            d = d + cv * step
            d /= np.linalg.norm(d)
        rad = [fl.raggio * (1 - (1 - fl.punta) * i / n) for i in range(n + 1)]
        parti = [sdf.round_cone(pts[i], pts[i + 1], rad[i], rad[i + 1]) for i in range(n)]
        P = np.array(pts)
        o = oggetto_sdf(f'Filamento{k}_{s}', sdf.union(*parti), P.min(0) - fl.raggio - 0.004, P.max(0) + fl.raggio + 0.004, mat,
                        res=max(min(fl.raggio * 0.4, 0.0008), 0.0004))
        obs.append(o)
    return obs


def raggi_liberi(body: Body, lk: Look, fin: Fin, k=0):
    """I raggi liberi sotto la pettorale (gallinella): grossi (in proporzione alla pinna), piegati verso il basso
    come zampette, color carne chiara (fra il ventre e il fianco), appena più sottili in punta."""
    obs = []
    col = tuple(a * 0.6 + b * 0.4 for a, b in zip(lk.belly, lk.flank))
    mat = materiale(f'RaggiLiberi{k}', col, rough=0.45, coat=0.5, sss=0.25)
    for i in range(fin.liberi):
        fl = Filamento(t=fin.a - 0.012 - 0.011 * i, v=-0.62 - 0.08 * i, lunghezza=fin.size * (0.62 - 0.06 * i),
                       raggio=max(0.0042, fin.size * 0.02), dir=(-0.3 + 0.15 * i, 0.4, -1.0), curva=(4.0, 0.0, 1.0),
                       lati='due', punta=0.7)
        obs += filamento(body, lk, fl, k=f'{k}l{i}', mat=mat)
    return obs


def fotofori(body: Body, fo):
    """Le lucine del pesce lanterna: sferette luminose appena affondate nella pelle."""
    rng = np.random.default_rng(fo.seme)
    tv = []
    for t0, t1, v, n in fo.righe:
        for t in np.linspace(t0, t1, int(n)):
            tv.append((float(t), float(v)))
    for _ in range(fo.sparsi):
        tv.append((float(rng.uniform(0.08, 0.92)), float(rng.uniform(*fo.sparsi_v))))
    C = []
    for s in ((-1, 1) if fo.lati == 'due' else (-1,)):
        for t, v in tv:
            p, n = body.superficie(t, v, s)
            C.append(p - n * fo.raggio * 0.3)
    f, lo, hi = campo_sfere(C, fo.raggio)
    mat = materiale('Fotofori', (0.55, 0.62, 0.66), rough=0.15, coat=1.0, emissione=fo.colore, forza=fo.forza)
    return oggetto_sdf('Fotofori', f, lo, hi, mat, res=max(fo.raggio / 3.5, 0.0005))


def denti_disco_orale(body: Body):
    """Gli anelli di denti gialli nella conca della ventosa della lampreda, che puntano verso il centro."""
    do = body.sh.disco_orale
    R0 = do.raggio
    C, n, e1, e2 = _disco_orale_telaio(body)
    S = C + n * R0 * 0.95
    Rb = R0 * 1.02
    A, B, R1, R2 = [], [], [], []
    for j in range(do.anelli):
        q = j / max(do.anelli - 1, 1)
        rho = R0 * (0.3 + 0.48 * q)
        cnt = max(5, int(round(do.denti * (0.55 + 0.6 * q))))
        for i in range(cnt):
            ph = 2 * math.pi * i / cnt + j * 0.37
            er = e1 * math.cos(ph) + e2 * math.sin(ph)
            base = S - n * math.sqrt(max(Rb * Rb - rho * rho, 0.0)) + er * rho
            d = n * 0.8 - er * 0.55
            d /= np.linalg.norm(d)
            ln = R0 * (0.2 - 0.07 * q)
            A.append(base - d * R0 * 0.03)
            B.append(base + d * ln)
            R1.append(R0 * (0.075 - 0.02 * q))
            R2.append(R0 * 0.012)
    f, lo, hi = campo_coni(A, B, R1, R2)
    mat = materiale('DentiLampreda', (0.80, 0.66, 0.30), rough=0.25, coat=0.8, sss=0.3)
    return oggetto_sdf('DentiDiscoOrale', f, lo, hi, mat, res=max(R0 * 0.012, 0.00035))


def denti_becco(body: Body, n=None, lunghezza=None, raggio=None, mat=None, nome='DentiBecco'):
    """I dentini delle aguglie lungo le due mascelle del becco (Rostro('becco')): aghi corti sul bordo del
    taglio, sui due lati, piegati in fuori e verso l'altra mascella. n: quanti per mascella e per lato (None:
    Rostro.denti); lunghezza, raggio: None = in proporzione al becco, che in punta si assottiglia. Seguono la
    mascella di sotto se la bocca è aperta (sanguinanti). Un oggetto solo (campo_coni)."""
    r = body.sh.rostro
    n = r.denti if n is None else n
    L = float(r.lunghezza)
    R, hinge = getattr(body, 'jaw_R', None), getattr(body, 'hinge', None)
    A, B, R1, R2 = [], [], [], []
    for i in range(n):
        x = -L * (0.02 + 0.92 * i / max(n - 1, 1))      # dalla radice quasi alla punta
        wy, wz, _ = (float(np.asarray(a).ravel()[0]) for a in sezione_rostro(r, np.array([x], F)))
        zl = float(body.mouth_line(np.array([x], F))[0])
        ln = lunghezza if lunghezza is not None else max(wz * 0.55, 0.0012)
        rr = raggio if raggio is not None else max(min(wy, wz) * 0.22, 0.0004)
        for jaw in (1, -1):         # 1: la mascella di sopra (il dente punta in giù), −1: quella di sotto
            for s in (-1, 1):
                a = np.array((x, s * wy * 0.6, zl + jaw * wz * 0.35), F)
                d = np.array((-0.2, s * 0.6, -jaw * 0.75), F)
                d /= np.linalg.norm(d)
                b = a + d * (ln + wz * 0.35)
                if jaw == -1 and R is not None:
                    a = (a - hinge) @ R.T + hinge
                    b = (b - hinge) @ R.T + hinge
                A.append(a)
                B.append(b)
                R1.append(rr)
                R2.append(rr * 0.15)
    f, lo, hi = campo_coni(A, B, R1, R2)
    mat = mat or materiale('DentiBecco', (0.84, 0.82, 0.72), rough=0.3, coat=0.6, sss=0.2)
    return oggetto_sdf(nome, f, lo, hi, mat, res=max(min(R1) * 0.6, 0.0004))


def elementi(body: Body, lk: Look):
    """Gli oggetti in più chiesti dalla forma: filamenti (barbigli, cirri), raggi liberi delle pettorali,
    fotofori, i denti del disco orale e quelli del becco."""
    sh = body.sh
    obs = []
    for k, fl in enumerate(sh.filamenti):
        obs += filamento(body, lk, fl, k)
    for k, fin in enumerate(sh.fins):
        if fin.liberi and fin.kind == 'pectoral':
            obs += raggi_liberi(body, lk, fin, k)
    if sh.fotofori is not None:
        obs.append(fotofori(body, sh.fotofori))
    if sh.disco_orale is not None:
        obs.append(denti_disco_orale(body))
    if sh.rostro is not None and sh.rostro.tipo == 'becco' and sh.rostro.denti:
        obs.append(denti_becco(body))
    return obs


def denti_mascelle(body: Body, n=8, lunghezza=0.008, zanne=(), apertura=0.0, mat=None, nome='Dente', seme=0):
    """Aiuto per gli extra: denti lungo le due mascelle (come quelli dei sanguinanti). zanne: indici dei
    denti lunghi il doppio; apertura: i gradi della bocca aperta (come Shape.bocca_aperta)."""
    sh = body.sh
    rng = np.random.default_rng(seme)
    mat = mat or dirty_teeth_material()
    R = sdf.rot_matrix('y', -apertura)
    hinge = np.array((sh.mouth_t, 0.0, sh.mouth_z1), F)
    obs = []
    for jaw in ('upper', 'lower'):
        for k in range(n):
            x = 0.008 + (sh.mouth_t - 0.02) * k / max(n - 1, 1)
            for s in (-1, 1):
                zl = float(body.mouth_line(np.array([x], F))[0])
                y = s * float(body.surface_y(x, zl)) * 0.8
                ln = lunghezza * (2.0 if k in zanne else 1.0) * rng.uniform(0.8, 1.2)
                base = np.array((x, y, zl + (0.002 if jaw == 'upper' else -0.002)), F)
                tip = base + np.array((rng.uniform(-0.002, 0.003), -s * 0.001, -ln if jaw == 'upper' else ln), F)
                if jaw == 'lower' and apertura:
                    base = (base - hinge) @ R.T + hinge
                    tip = (tip - hinge) @ R.T + hinge
                obs.append(tooth(f'{nome}_{jaw}_{k}_{s}', tuple(map(float, base)), tuple(map(float, tip)), 0.0014 + ln * 0.08, mat, col=COL))
    return obs


# ───────────────────────── asse curvo, posa, inquadratura ─────────────────────────

def piega(obs, body: Body):
    """Curva l'asse del pesce nel piano del ritratto (XZ) secondo sh.piega = [(t, gradi)]: il punto (x, y, z)
    del pesce dritto va in C(x) + z·N(x) + y, con C la curva dell'asse (lunga quanto il pesce) e N la sua
    normale. Gli oggetti con le coordinate già nel mondo si deformano vertice per vertice (e le normali
    girano con loro); gli altri (gli occhi) si spostano e si girano interi."""
    from mathutils import Matrix, Vector
    pts = [(float(t), math.radians(float(a))) for t, a in body.sh.piega]
    th = prof(pts)
    xs = np.linspace(-1.5, 3.0, 9001, dtype=np.float64)
    ang = th(np.clip(xs, pts[0][0], pts[-1][0])).astype(np.float64)
    dx = xs[1] - xs[0]
    cx = np.concatenate([[0.0], np.cumsum((np.cos(ang[1:]) + np.cos(ang[:-1])) * 0.5 * dx)])
    cz = np.concatenate([[0.0], np.cumsum((np.sin(ang[1:]) + np.sin(ang[:-1])) * 0.5 * dx)])
    i0 = int(np.searchsorted(xs, 0.0))
    cx -= cx[i0]
    cz -= cz[i0]

    def angolo(x):
        return np.interp(x, xs, ang)

    def mappa(P):
        x, y, z = P[:, 0].astype(np.float64), P[:, 1], P[:, 2].astype(np.float64)
        a = angolo(x)
        X = np.interp(x, xs, cx) - z * np.sin(a)
        Z = np.interp(x, xs, cz) + z * np.cos(a)
        return np.stack([X, y, Z], axis=1).astype(F), a

    bpy.context.view_layer.update()
    for o in obs:
        if o.type != 'MESH':
            continue
        M = o.matrix_world
        if M == Matrix.Identity(4):
            me = o.data
            nv = len(me.vertices)
            co = np.empty(nv * 3, F)
            me.vertices.foreach_get('co', co)
            P = co.reshape(-1, 3)
            Q, a = mappa(P)
            custom = me.has_custom_normals
            if custom:
                nl = len(me.loops)
                cn = np.empty(nl * 3, F)
                me.corner_normals.foreach_get('vector', cn)
                cn = cn.reshape(-1, 3)
                vi = np.empty(nl, np.int32)
                me.loops.foreach_get('vertex_index', vi)
                al = a[vi]
                ca, sa = np.cos(al), np.sin(al)
                nx = cn[:, 0] * ca - cn[:, 2] * sa
                nz = cn[:, 0] * sa + cn[:, 2] * ca
                cn = np.stack([nx, cn[:, 1], nz], axis=1).astype(F)
            me.vertices.foreach_set('co', Q.ravel())
            me.update()
            if custom:
                me.normals_split_custom_set([tuple(map(float, n)) for n in cn])
        else:
            loc = np.array(M.translation, F)[None]
            q, a = mappa(loc)
            R = Matrix.Rotation(-float(a[0]), 4, 'Y')
            o.matrix_world = Matrix.Translation(Vector(q[0])) @ R @ Matrix.Translation(-Vector(loc[0])) @ M


def _vertici_mondo(obs, quanti=60000):
    """Un campione dei vertici di tutti gli oggetti, nel mondo (per l'inquadratura)."""
    out = []
    tot = sum(len(o.data.vertices) for o in obs if o.type == 'MESH')
    passo = max(1, tot // quanti)
    for o in obs:
        if o.type != 'MESH':
            continue
        nv = len(o.data.vertices)
        co = np.empty(nv * 3, F)
        o.data.vertices.foreach_get('co', co)
        P = co.reshape(-1, 3)[::passo] if nv > passo * 4 else co.reshape(-1, 3)
        M = np.array(o.matrix_world, F)
        out.append(P @ M[:3, :3].T + M[:3, 3])
    return np.concatenate(out)


def proietta(P, cam, W, H):
    """Punti del mondo → coordinate nel fotogramma (x da sinistra, y dall'alto, 0..1)."""
    Mi = np.array(cam.matrix_world.inverted(), F)
    Pc = P @ Mi[:3, :3].T + Mi[:3, 3]
    k = cam.data.lens / cam.data.sensor_width
    zc = -Pc[:, 2]
    return 0.5 + Pc[:, 0] / zc * k, 0.5 - Pc[:, 1] / zc * k * (W / H), zc


def adatta(obs, sc, W, H, larg=0.80, alt=0.70, cx=0.49, cy=0.46):
    """Inquadra il pesce come i prototipi: lo scala perché il suo riquadro sia largo al massimo `larg` e alto
    al massimo `alt` del fotogramma, e lo centra in (cx, cy) (frazioni; y dall'alto)."""
    from mathutils import Matrix, Vector
    cam = sc.camera
    k = cam.data.lens / cam.data.sensor_width
    cm = np.array(cam.matrix_world, F)
    right, up, back, loc = cm[:3, 0], cm[:3, 1], cm[:3, 2], cm[:3, 3]
    for _ in range(3):
        bpy.context.view_layer.update()
        P = _vertici_mondo(obs)
        xs, ys, zc = proietta(P, cam, W, H)
        x0, x1, y0, y1 = float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max())
        s = min(larg / max(x1 - x0, 1e-6), alt / max(y1 - y0, 1e-6))
        D = float(np.median(zc))
        fw = D / k
        fh = fw * H / W
        G = loc - back * D + right * ((x0 + x1) / 2 - 0.5) * fw + up * (0.5 - (y0 + y1) / 2) * fh
        T = loc - back * D + right * (cx - 0.5) * fw + up * (0.5 - cy) * fh
        M = Matrix.Translation(Vector(T)) @ Matrix.Scale(s, 4) @ Matrix.Translation(-Vector(G))
        for o in obs:
            o.matrix_world = M @ o.matrix_world


# ───────────────────────── scena e render ─────────────────────────

def studio():
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    w = bpy.data.worlds.new('Studio')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.012, 0.016, 0.024, 1)
    s = (0.58, 0.0, 0.0)
    # la lampara (calda, davanti e in alto), la luna dietro (fredda), un riflesso dell'acqua da sotto
    area_light('Key', (-0.2, -1.4, 1.5), s, 42, (1.0, 0.76, 0.50), 0.7)
    area_light('Rim', (1.5, 1.3, 1.0), s, 90, (0.55, 0.72, 1.0), 0.5)
    area_light('Fill', (1.4, -1.9, -0.5), s, 3.5, (0.45, 0.6, 0.75), 1.4)
    area_light('Top', (0.6, 0.3, 1.5), s, 10, (0.8, 0.85, 1.0), 1.0)
    cam_d = bpy.data.cameras.new('Cam')
    cam_d.lens = 85.0
    cam_d.sensor_width = 36.0
    cam = bpy.data.objects.new('Cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    from mathutils import Vector
    cam.location = (0.6, -3.45, 0.05)
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = (Vector((0.6, 0.0, 0.0)) - Vector(cam.location)).to_track_quat('-Z', 'Y')
    return sc


def pose(obs, yaw=12.0, pitch=-4.0, roll=0.0):
    """Il pesce un po' girato verso la camera (testa più vicina) e appena inclinato; roll lo gira sul suo
    asse (+ mostra il dorso: le ali del pesce volante; − sui pesci visti dall'alto li corica sul fondo)."""
    from mathutils import Euler, Matrix
    bpy.context.view_layer.update()
    c = Matrix.Translation((0.55, 0, 0))
    M = c @ Euler((math.radians(roll), math.radians(pitch), math.radians(yaw)), 'XYZ').to_matrix().to_4x4() @ c.inverted()
    for o in obs:
        o.matrix_world = M @ o.matrix_world


class Contesto:
    """Quello che ricevono gli extra (e i campi) delle specie: c.fid, c.specie, c.body (Body), c.forma
    (Shape), c.aspetto (Look), c.famiglia, c.obs (la lista degli oggetti: gli extra ci aggiungono i loro),
    c.P (questo modulo, con tutti gli aiuti: sdf, oggetto_sdf, materiale, fish_skin, eyeball, filamento,
    denti_mascelle, campo_coni, Body.superficie…), c.fast (anteprima veloce)."""

    def __init__(self, **k):
        self.__dict__.update(k)


def build(fid):
    """Gli oggetti del pesce e la sua famiglia (vedi costruisci)."""
    c = costruisci(fid)
    return c.obs, c.famiglia


def costruisci(fid):
    """Costruisce la specie registrata fid (forma, famiglia, pinne, elementi, extra, asse curvo) e restituisce
    il Contesto, con gli oggetti in c.obs."""
    sp = registro.SPECIE[fid]
    sh, lk, family = sp.forma, sp.aspetto, sp.famiglia
    body = Body(sh, PIANI[sp.piano])
    c = Contesto(fid=fid, specie=sp, body=body, forma=sh, aspetto=lk, famiglia=family, P=sys.modules[__name__], obs=[], fast=FAST)
    if sp.campo is not None:
        body.campo_extra = lambda f: sp.campo(c, f)
    opz = dict(sp.opzioni)
    con_elementi = opz.pop('elementi', True)
    if family == 'skeletal':
        obs = skeletal(body, lk, **opz)
    elif family == 'zombie':
        obs = zombie(body, lk, **opz)
    elif family == 'corrupt':
        obs = corrupt(body, lk, **opz)
    elif family == 'bleeding':
        obs = bleeding(body, lk, **opz)
    else:
        # 'glitch' (il glitch è sull'immagine) e 'normale' (le prove dei piani)
        ob = build_normal(body, lk, family)
        obs = [ob] + eyes(body, lk)
        if body.sh.barbels:
            obs += barbels(body, fish_skin('BarbelSkin', lk))
    obs += build_fins(body, lk, family, seed=len(fid))
    if con_elementi:
        obs += elementi(body, lk)
    c.obs = obs
    if sp.extra is not None:
        sp.extra(c)
    if sh.piega:
        piega(c.obs, body)
    return c


def render_fish(fid):
    t0 = time.time()
    if fid not in registro.SPECIE:
        raise SystemExit(f'specie {fid!r} non registrata (pesci_specie/): vedi --elenco')
    sp = registro.SPECIE[fid]
    if sp.famiglia == 'normale' and not ANTEPRIMA:
        raise SystemExit(f'{fid} è registrata come prova (famiglia normale): si rende solo con --anteprima')
    sc = studio()
    c = costruisci(fid)
    obs, family = c.obs, c.famiglia
    rit = sp.ritratto if sp.ritratto is not None else PIANI[sp.piano].ritratto
    pose(obs, rit.yaw, rit.pitch, rit.roll)
    W, H = (800, 400) if FAST else (1600, 800)
    if rit.adatta:
        adatta(obs, sc, W, H, larg=rit.riquadro[0], alt=rit.riquadro[1], cx=rit.centro[0], cy=rit.centro[1])
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 24 if FAST else 96
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    out_dir = os.path.join(CACHE, 'pesci', 'anteprime') if ANTEPRIMA else os.path.join(CACHE, 'pesci')
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, f'{fid}.png')
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    im = np.asarray(Image.open(png).convert('RGBA'), np.float32) / 255.0
    if family == 'glitch':
        Image.fromarray((im * 255).astype(np.uint8)).save(png.replace('.png', '_pulito.png'))
        im = glitch_post(im, **{k: v for k, v in sp.opzioni.items() if k != 'elementi'})
    if sp.ritocco is not None:
        im = np.clip(sp.ritocco(im, c), 0, 1)
    if family == 'glitch' or sp.ritocco is not None:
        Image.fromarray((im * 255).astype(np.uint8)).save(png)
    if ANTEPRIMA:
        # da guardare: sul fondo scuro delle pagine del Catalogo
        fondo = np.array(FONDO_CATALOGO, np.float32) / 255.0
        rgb = im[..., :3] * im[..., 3:4] + fondo * (1 - im[..., 3:4])
        Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(png.replace('.png', '.jpg'), quality=90)
        log(f'anteprima {fid} ({family}, piano {sp.piano})', round(time.time() - t0), 's →', png.replace('.png', '.jpg'))
        return png
    os.makedirs(FISH_DIR, exist_ok=True)
    img = Image.fromarray((im * 255).astype(np.uint8))
    img.save(os.path.join(FISH_DIR, f'{fid}.webp'), quality=88, method=6)
    man_path = os.path.join(FISH_DIR, 'fish.json')
    man = json.load(open(man_path)) if os.path.exists(man_path) else {}
    man[fid] = {'file': f'{fid}.webp', 'w': W, 'h': H, 'family': family}
    with open(man_path, 'w') as f:
        json.dump(dict(sorted(man.items())), f, indent=1)
    log(f'pesce {fid} ({family})', round(time.time() - t0), 's →', png)
    return png


# ───────────────────────── fogli delle anteprime ─────────────────────────

def foglio(voci, out, colonne=4, larghezza=1600):
    """Un foglio con le immagini e il testo sotto ciascuna: voci = [(percorso, titolo, sotto)]. Il titolo e la
    riga sotto vanno a capo se non stanno nella colonna (al massimo due righe ciascuno)."""
    from PIL import Image, ImageDraw, ImageFont
    cw = larghezza // colonne
    ih = cw // 2

    def font(nome, px):
        for p in (f'/usr/share/fonts/truetype/dejavu/{nome}.ttf',):
            if os.path.exists(p):
                return ImageFont.truetype(p, px)
        return ImageFont.load_default()
    f1, f2 = font('DejaVuSans-Bold', 19), font('DejaVuSans', 13)
    misura = ImageDraw.Draw(Image.new('RGB', (8, 8)))

    def a_capo(testo, f, largo, righe_max=2):
        """Le righe del testo spezzato alle parole perché stia largo al massimo `largo` pixel."""
        righe, riga = [], ''
        for parola in testo.split(' '):
            prova = (riga + ' ' + parola).strip()
            if riga and misura.textlength(prova, font=f) > largo:
                righe.append(riga)
                riga = parola
            else:
                riga = prova
        righe.append(riga)
        if len(righe) > righe_max:
            righe = righe[:righe_max - 1] + [' '.join(righe[righe_max - 1:])]
        return righe
    testi = [(a_capo(titolo, f1, cw - 20), a_capo(sotto, f2, cw - 20)) for _, titolo, sotto in voci]
    th = max(len(a) * 25 + len(b) * 17 for a, b in testi) + 12
    righe = (len(voci) + colonne - 1) // colonne
    sheet = Image.new('RGB', (larghezza, righe * (ih + th) + 16), FONDO_CATALOGO)
    dr = ImageDraw.Draw(sheet)
    for i, ((path, _, _), (r1, r2)) in enumerate(zip(voci, testi)):
        x, y = (i % colonne) * cw, (i // colonne) * (ih + th) + 8
        if os.path.exists(path):
            im = Image.open(path).convert('RGBA')
            fondo = Image.new('RGBA', im.size, FONDO_CATALOGO + (255,))
            im = Image.alpha_composite(fondo, im).convert('RGB').resize((cw - 8, ih - 4), Image.LANCZOS)
            sheet.paste(im, (x + 4, y))
        else:
            dr.text((x + 20, y + ih // 2), f'manca {os.path.basename(path)}', fill=(200, 80, 80), font=f2)
        ty = y + ih + 4
        for r in r1:
            dr.text((x + 12, ty), r, fill=(236, 226, 205), font=f1)
            ty += 25
        ty += 2
        for r in r2:
            dr.text((x + 12, ty), r, fill=(214, 160, 90), font=f2)
            ty += 17
    sheet.save(out, quality=90)
    log('foglio', out)
    return out


def foglio_anteprime(out, voci_cli, colonne=4, larghezza=1600):
    """--foglio out.jpg id[:etichetta] ...: le anteprime già fatte, con il piano (o l'etichetta) e la specie."""
    cat = registro.catalogo()
    voci = []
    for v in voci_cli:
        fid, _, etichetta = v.partition(':')
        sp = registro.SPECIE.get(fid)
        titolo = etichetta or (sp.piano if sp else fid)
        info = cat.get(fid)
        sotto = f"{info['vero']} ({info['sci']}) · {fid}" if info else fid
        voci.append((os.path.join(CACHE, 'pesci', 'anteprime', f'{fid}.png'), titolo, sotto))
    return foglio(voci, out, colonne=colonne, larghezza=larghezza)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--elenco' in sys.argv:
        for fid, sp in registro.SPECIE.items():
            print(f'{fid:28s} {sp.famiglia:9s} {sp.piano:14s} ({registro.ORIGINE[fid]}.py)')
        registro.controlla()
        sys.exit(0)
    if '--foglio' in sys.argv:
        # --colonne=N --larghezza=PX (default 4 colonne, 1600 px)
        num = {a.split('=', 1)[0]: int(a.split('=', 1)[1]) for a in sys.argv if a.startswith(('--colonne=', '--larghezza='))}
        foglio_anteprime(args[0], args[1:], colonne=num.get('--colonne', 4), larghezza=num.get('--larghezza', 1600))
        sys.exit(0)
    fam = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--famiglia=')]
    if '--tutti' in sys.argv:
        ids = list(registro.SPECIE)
    elif fam:
        ids = [k for k, v in registro.SPECIE.items() if v.famiglia == fam[0]]
    else:
        ids = args or list(registro.PROTOTIPI)
    if not ANTEPRIMA:
        # le prove dei piani (famiglia 'normale') non finiscono nel gioco: si rendono solo come anteprima
        prove = [k for k in ids if k in registro.SPECIE and registro.SPECIE[k].famiglia == 'normale']
        if prove:
            log('salto le prove dei piani (famiglia normale, solo --anteprima):', ', '.join(prove))
        ids = [k for k in ids if k not in prove]
    for fid in ids:
        render_fish(fid)
