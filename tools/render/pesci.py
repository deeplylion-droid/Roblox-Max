"""
I pesci del Catalogo (src/game/catalog.ts, docs/CATALOGO.md): un generatore parametrico e le cinque
famiglie di trasformazione (scheletrici, zombi, glitchati, corrotti, sanguinanti).

Il corpo è un campo di distanza costruito da tre profili lungo l'asse (dorso, ventre, mezza larghezza):
il muso sta in x = 0 e guarda verso −X, l'attacco della coda in x = 1, il dorso verso +Z, il fianco
sinistro verso −Y (la camera). Le pinne sono mesh sottili a raggi; occhi, denti e melma come le creature.
Si rende il "ritratto" di cattura su sfondo trasparente, con la lampara davanti e la luna dietro.

Uso: tools/.venv/bin/python tools/render/pesci.py [id ...] [--fast]
Uscite: public/assets/img/fish/<id>.webp (RGBA) e fish.json; anteprime in tools/render/cache/pesci/
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sdf  # noqa: E402
from common import CACHE, OUT_IMG, collection, log, mesh_from_arrays, reset_scene, set_lightgroup  # noqa: E402
from creature import eye_material, eyeball, flesh_material, sdf_object, tooth  # noqa: E402
from dettagli import area_light  # noqa: E402
from nodes import material  # noqa: E402
from skin import cloudy_eye, drip, slime_material  # noqa: E402

F = np.float32
FAST = '--fast' in sys.argv
FISH_DIR = os.path.join(OUT_IMG, 'fish')
COL = 'fish'


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


@dataclass
class Fin:
    """Pinna: radice da a a b (in t lungo il corpo, sul dorso/ventre o sul fianco) e sagoma.
    kind: 'dorsal' | 'anal' | 'caudal' | 'pectoral' | 'pelvic'; outline: punti (lungo, fuori) normalizzati
    rispetto alla radice, dalla radice a alla radice b. spiny: raggi rigidi e membrana incisa."""
    kind: str
    a: float
    b: float
    outline: list
    size: float = 0.1
    rays: int = 12
    spiny: bool = False
    tilt: float = 0.0


@dataclass
class Shape:
    top: list
    bot: list
    w: list
    eye_t: float
    eye_z: float
    eye_r: float
    mouth_t: float = 0.06          # dove finisce la bocca (angolo)
    mouth_z0: float = 0.0          # quota della bocca alla punta del muso
    mouth_z1: float = 0.0          # quota all'angolo
    gill_t: float = 0.2            # bordo dell'opercolo
    fins: list = field(default_factory=list)
    barbels: bool = False


@dataclass
class Look:
    back: tuple
    flank: tuple
    belly: tuple
    fin: tuple
    iris: tuple = (0.75, 0.66, 0.40)
    iris_dark: tuple = (0.20, 0.17, 0.10)
    metal: float = 0.45
    pattern: str = ''
    pattern_col: tuple = (0.02, 0.03, 0.04)
    irid: float = 0.35


# ───────────────────────── le specie dei prototipi ─────────────────────────

def _forked(spread=1.45, fork=0.32, length=1.0):
    """Coda forcuta: (fuori, verticale) con il verticale da +1 (radice in alto) a −1 (radice in basso);
    le punte dei lobi arrivano a ±spread."""
    return [(0.0, 1.0), (0.55 * length, 1.12), (1.0 * length, spread), (fork * length, 0.0), (1.0 * length, -spread), (0.55 * length, -1.12), (0.0, -1.0)]


SHAPES = {
    'mackerel': Shape(
        top=[(0, -0.006), (0.03, 0.022), (0.09, 0.055), (0.2, 0.082), (0.36, 0.092), (0.55, 0.082), (0.75, 0.05), (0.9, 0.026), (1, 0.018)],
        bot=[(0, -0.012), (0.04, -0.035), (0.12, -0.062), (0.3, -0.088), (0.5, -0.085), (0.72, -0.055), (0.9, -0.026), (1, -0.018)],
        w=[(0, 0.004), (0.05, 0.026), (0.15, 0.05), (0.35, 0.058), (0.6, 0.046), (0.85, 0.02), (1, 0.011)],
        eye_t=0.075, eye_z=0.016, eye_r=0.021, mouth_t=0.075, mouth_z0=-0.008, mouth_z1=-0.016, gill_t=0.2,
        fins=[Fin('dorsal', 0.30, 0.42, [(0, 0), (0.15, 0.9), (0.4, 1.0), (0.75, 0.55), (1, 0.08)], 0.11, 10, spiny=True),
              Fin('dorsal', 0.56, 0.64, [(0, 0), (0.25, 0.8), (0.6, 0.55), (1, 0.05)], 0.06, 8),
              Fin('anal', 0.58, 0.66, [(0, 0), (0.25, 0.75), (0.6, 0.5), (1, 0.05)], 0.055, 8),
              Fin('caudal', 1.0, 1.0, _forked(1.55, 0.26), 0.24, 18),
              Fin('pectoral', 0.20, 0.215, [(0, 0), (0.45, 0.35), (1.0, 0.18), (0.8, -0.05), (0, -0.1)], 0.11, 9),
              Fin('pelvic', 0.27, 0.285, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.06, 6)]),
    'bream': Shape(
        top=[(0, -0.03), (0.02, 0.004), (0.06, 0.06), (0.12, 0.118), (0.2, 0.158), (0.35, 0.182), (0.5, 0.176), (0.7, 0.118), (0.85, 0.064), (0.95, 0.042), (1, 0.04)],
        bot=[(0, -0.05), (0.025, -0.08), (0.1, -0.118), (0.25, -0.155), (0.45, -0.168), (0.6, -0.148), (0.75, -0.1), (0.9, -0.05), (1, -0.04)],
        w=[(0, 0.008), (0.06, 0.034), (0.2, 0.058), (0.4, 0.064), (0.65, 0.05), (0.85, 0.025), (1, 0.015)],
        eye_t=0.155, eye_z=0.058, eye_r=0.031, mouth_t=0.07, mouth_z0=-0.038, mouth_z1=-0.05, gill_t=0.29,
        fins=[Fin('dorsal', 0.33, 0.84, [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.82), (0.8, 0.75), (0.95, 0.55), (1, 0.05)], 0.12, 22, spiny=True),
              Fin('anal', 0.62, 0.84, [(0, 0), (0.12, 0.9), (0.6, 0.62), (0.95, 0.5), (1, 0.05)], 0.09, 12),
              Fin('caudal', 1.0, 1.0, _forked(1.5, 0.34), 0.26, 20),
              Fin('pectoral', 0.32, 0.34, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.2, 12),
              Fin('pelvic', 0.37, 0.39, [(0, 0), (0.6, 0.28), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.1, 7, spiny=True)]),
    'salema': Shape(
        top=[(0, -0.012), (0.05, 0.035), (0.15, 0.092), (0.35, 0.128), (0.55, 0.124), (0.75, 0.082), (0.9, 0.046), (1, 0.04)],
        bot=[(0, -0.026), (0.07, -0.058), (0.2, -0.096), (0.4, -0.12), (0.6, -0.106), (0.8, -0.068), (0.95, -0.042), (1, -0.04)],
        w=[(0, 0.008), (0.08, 0.034), (0.25, 0.053), (0.45, 0.056), (0.7, 0.04), (0.9, 0.02), (1, 0.014)],
        eye_t=0.12, eye_z=0.034, eye_r=0.026, mouth_t=0.045, mouth_z0=-0.02, mouth_z1=-0.026, gill_t=0.25,
        fins=[Fin('dorsal', 0.3, 0.82, [(0, 0), (0.06, 0.95), (0.25, 0.9), (0.55, 0.62), (0.85, 0.66), (1, 0.05)], 0.09, 22, spiny=True),
              Fin('anal', 0.6, 0.82, [(0, 0), (0.12, 0.85), (0.6, 0.6), (1, 0.05)], 0.07, 12),
              Fin('caudal', 1.0, 1.0, _forked(1.45, 0.3), 0.24, 20),
              Fin('pectoral', 0.28, 0.3, [(0, 0), (0.5, 0.3), (1.0, 0.15), (0.8, 0.0), (0, -0.06)], 0.15, 11),
              Fin('pelvic', 0.33, 0.35, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.08, 6)]),
    'redmullet': Shape(
        top=[(0, -0.045), (0.02, -0.018), (0.05, 0.03), (0.1, 0.07), (0.18, 0.096), (0.3, 0.108), (0.5, 0.1), (0.72, 0.068), (0.9, 0.04), (1, 0.034)],
        bot=[(0, -0.052), (0.03, -0.075), (0.15, -0.09), (0.38, -0.094), (0.6, -0.078), (0.8, -0.052), (1, -0.034)],
        w=[(0, 0.012), (0.08, 0.04), (0.25, 0.054), (0.5, 0.05), (0.8, 0.028), (1, 0.014)],
        eye_t=0.125, eye_z=0.046, eye_r=0.024, mouth_t=0.05, mouth_z0=-0.046, mouth_z1=-0.054, gill_t=0.24, barbels=True,
        fins=[Fin('dorsal', 0.28, 0.42, [(0, 0), (0.15, 1.0), (0.45, 0.95), (0.8, 0.55), (1, 0.05)], 0.12, 8, spiny=True),
              Fin('dorsal', 0.56, 0.68, [(0, 0), (0.2, 0.8), (0.6, 0.6), (1, 0.05)], 0.07, 9),
              Fin('anal', 0.58, 0.7, [(0, 0), (0.2, 0.75), (0.6, 0.55), (1, 0.05)], 0.065, 8),
              Fin('caudal', 1.0, 1.0, _forked(1.4, 0.3), 0.23, 18),
              Fin('pectoral', 0.25, 0.27, [(0, 0), (0.5, 0.3), (1.0, 0.15), (0.8, 0.0), (0, -0.06)], 0.14, 10),
              Fin('pelvic', 0.3, 0.32, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.08, 6)]),
    'barracuda': Shape(
        top=[(0, -0.018), (0.06, 0.006), (0.15, 0.04), (0.3, 0.06), (0.5, 0.066), (0.7, 0.055), (0.88, 0.031), (1, 0.026)],
        bot=[(0, -0.024), (0.04, -0.034), (0.15, -0.05), (0.3, -0.062), (0.5, -0.064), (0.7, -0.052), (0.88, -0.03), (1, -0.026)],
        w=[(0, 0.007), (0.08, 0.023), (0.25, 0.04), (0.5, 0.043), (0.75, 0.032), (1, 0.013)],
        eye_t=0.105, eye_z=0.016, eye_r=0.018, mouth_t=0.13, mouth_z0=-0.012, mouth_z1=-0.008, gill_t=0.19,
        fins=[Fin('dorsal', 0.38, 0.45, [(0, 0), (0.2, 0.95), (0.55, 0.85), (1, 0.05)], 0.06, 6, spiny=True),
              Fin('dorsal', 0.66, 0.73, [(0, 0), (0.25, 0.85), (0.7, 0.55), (1, 0.05)], 0.05, 8),
              Fin('anal', 0.67, 0.74, [(0, 0), (0.25, 0.8), (0.7, 0.5), (1, 0.05)], 0.045, 8),
              Fin('caudal', 1.0, 1.0, _forked(1.5, 0.32), 0.15, 18),
              Fin('pectoral', 0.2, 0.215, [(0, 0), (0.5, 0.3), (1.0, 0.12), (0.8, 0.0), (0, -0.05)], 0.08, 9),
              Fin('pelvic', 0.38, 0.395, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.06, 6)]),
}

LOOKS = {
    'mackerel': Look(back=(0.08, 0.24, 0.26), flank=(0.32, 0.36, 0.36), belly=(0.62, 0.62, 0.58), fin=(0.10, 0.12, 0.12),
                     iris=(0.55, 0.55, 0.50), iris_dark=(0.10, 0.10, 0.10), pattern='mackerel', irid=0.55),
    'bream': Look(back=(0.16, 0.18, 0.19), flank=(0.42, 0.44, 0.44), belly=(0.62, 0.62, 0.58), fin=(0.16, 0.16, 0.18),
                  iris=(0.72, 0.6, 0.36), pattern='bream'),
    'salema': Look(back=(0.12, 0.16, 0.20), flank=(0.36, 0.40, 0.44), belly=(0.62, 0.62, 0.6), fin=(0.16, 0.17, 0.2),
                   iris=(0.95, 0.62, 0.10), iris_dark=(0.45, 0.22, 0.02), pattern='salema'),
    'redmullet': Look(back=(0.52, 0.12, 0.08), flank=(0.72, 0.30, 0.22), belly=(0.78, 0.62, 0.55), fin=(0.62, 0.38, 0.28),
                      iris=(0.85, 0.55, 0.2), iris_dark=(0.4, 0.12, 0.04), metal=0.25, pattern='redmullet', irid=0.2),
    'barracuda': Look(back=(0.10, 0.13, 0.17), flank=(0.46, 0.49, 0.52), belly=(0.68, 0.68, 0.66), fin=(0.26, 0.27, 0.24),
                      iris=(0.7, 0.68, 0.55), iris_dark=(0.12, 0.12, 0.1), pattern='barracuda'),
}

# i cinque prototipi: id del catalogo → (forma, famiglia)
PROTOTYPES = {
    'sgombrato': ('mackerel', 'skeletal'),
    'orrata': ('bream', 'zombie'),
    'salpa_sfasata': ('salema', 'glitch'),
    'trigliocchi': ('redmullet', 'corrupt'),
    'barracruda': ('barracuda', 'bleeding'),
}


# ───────────────────────── campo del corpo ─────────────────────────

class Body:
    def __init__(self, sh: Shape):
        self.sh = sh
        self.top, self.bot, self.wid = prof(sh.top), prof(sh.bot), prof(sh.w)

    def section(self, t):
        zt, zb = self.top(t), self.bot(t)
        return (zt + zb) * 0.5, np.maximum((zt - zb) * 0.5, 1e-3), np.maximum(self.wid(t), 1e-3)

    def surface_y(self, t, z):
        """Mezza larghezza del corpo alla quota z (per appoggiare cose sul fianco)."""
        zc, h, w = self.section(np.asarray(t, F))
        q = np.clip((np.asarray(z, F) - zc) / h, -0.999, 0.999)
        return w * np.sqrt(1 - q * q)

    def norm_v(self, p):
        t = np.clip(p[:, 0], 0, 1)
        zc, h, _ = self.section(t)
        return (p[:, 2] - zc) / h

    def raw(self):
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

    def mouth_line(self, x):
        sh = self.sh
        u = np.clip(x / max(sh.mouth_t, 1e-3), 0, 1)
        return (sh.mouth_z0 + (sh.mouth_z1 - sh.mouth_z0) * u).astype(F)

    def field(self, mouth_open=0.0, socket=True):
        """Il corpo con la bocca (taglio sottile, o aperta di mouth_open gradi), l'opercolo e le orbite."""
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

        def f(p):
            x, z = p[:, 0], p[:, 2]
            if mouth_open:
                d = np.minimum(upper(p), lower(p)[0])
            else:
                # il taglio della bocca: una fessura sottile dal muso all'angolo
                d = base(p)
                slit = np.maximum(np.abs(z - self.mouth_line(x)) - 0.0012, x - sh.mouth_t)
                d = sdf.smax(d, -slit, 0.002)
            # bordo dell'opercolo: un solco ad arco sul fianco
            zc, h, _ = self.section(np.clip(x, 0, 1))
            v = (z - zc) / h
            arc_x = sh.gill_t - 0.035 * (v * v)
            groove = np.exp(-((x - arc_x) / 0.004) ** 2) * np.clip(1 - np.abs(v) / 0.95, 0, 1)
            d = d + 0.0025 * groove
            if socket:
                for s_ in (-1, 1):
                    ec = self.eye_center(s_)
                    d = sdf.smax(d, -(np.linalg.norm(p - ec, axis=1) - sh.eye_r * 1.05), 0.004)
            return d.astype(F)
        return f

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

    def bounds(self, pad=0.03):
        t = np.linspace(0, 1, 200, dtype=F)
        zt, zb, w = self.top(t), self.bot(t), self.wid(t)
        return np.array((-pad, -float(w.max()) - pad, float(zb.min()) - pad), F), np.array((1.0 + pad, float(w.max()) + pad, float(zt.max()) + pad), F)


# ───────────────────────── materiali ─────────────────────────

def fish_skin(name, lk: Look, rot=0.0, wounds=False, slime=False):
    """Pelle di pesce: dorso scuro, fianchi argentati, ventre chiaro, squame, linea laterale, disegno della
    specie. Attributi: 'u' (lungo il corpo), 'v' (quota normalizzata), 'rot', 'wound', 'blood', 'tar', 'mouth'."""
    m, g = material(name)
    co = g.texcoord('Object')
    u, v = g.attr('u'), g.attr('v')
    # colore base per quota
    col = g.mix(g.smoothstep(-0.55, 0.15, v), lk.belly, lk.flank)
    col = g.mix(g.smoothstep(0.25, 0.75, v), col, lk.back)
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
    # linea laterale
    lat = g.mul(g.smoothstep(0.018, 0.0, g.math('ABSOLUTE', g.sub(v, g.add(0.42, g.mul(u, -0.4))))), g.smoothstep(0.22, 0.3, u))
    col = g.mix(g.mul(lat, 0.45), col, (0.06, 0.06, 0.07))
    # squame: celle allungate lungo il corpo
    sc = g.voronoi(g.comb(g.mul(u, 150.0), g.mul(v, 34.0), 0.0), scale=1.0, feature='DISTANCE_TO_EDGE', dims='3D')
    scale_edge = g.smoothstep(0.0, 0.14, sc)
    col = g.mix(g.mul(g.sub(1.0, scale_edge), 0.09), col, (0.02, 0.02, 0.025))
    metal = g.mul(g.smoothstep(-0.9, 0.5, v), lk.metal)
    rough = g.mixf(scale_edge, 0.42, 0.2)
    fine = g.noise(co, scale=180.0, detail=2.0)
    h = g.add(g.mul(scale_edge, 0.35), g.mul(fine.fac, 0.2))
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
    col = g.mix(g.smoothstep(0.3, 0.8, mouth), col, (0.22, 0.05, 0.06))
    nrm = g.bump(h, strength=0.25, distance=0.002)
    bsdf = g.principled(color=col, metal=metal, rough=rough, coat=0.6, coat_rough=0.05, normal=nrm, coat_normal=nrm,
                        thin_film=g.mul(g.smoothstep(-0.2, 0.6, v), lk.irid * 380.0), spec=0.6)
    g.output_material(bsdf)
    return m


def fin_material(name, color, spiny=False, tears=0.0, bone=False, membrane=1.0):
    """Membrana con i raggi (u = indice del raggio, v = dalla radice al bordo). tears: buchi e strappi."""
    m, g = material(name)
    uv = g.texcoord('UV')
    u, v, _ = g.sep(uv)
    co = g.texcoord('Object')
    ray = g.pow(g.math('ABSOLUTE', g.math('COSINE', g.mul(u, math.pi))), 18.0)   # 1 sui raggi, 0 in mezzo
    ray_col = (0.70, 0.66, 0.55) if bone else (color[0] * 0.55, color[1] * 0.55, color[2] * 0.55)
    col = g.mix(g.mul(ray, 0.85), color, ray_col)
    # il bordo più scuro e sporco
    col = g.mix(g.mul(g.smoothstep(0.55, 1.0, v), 0.45), col, (color[0] * 0.4, color[1] * 0.4, color[2] * 0.42))
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


def bone_material(name='Bone', dirt=0.4):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    n = g.noise(co, scale=30.0, detail=5.0, rough=0.6)
    n2 = g.noise(co, scale=160.0, detail=2.0)
    col = g.mix(g.smoothstep(0.4, 0.75, n.fac), (0.78, 0.74, 0.62), (0.58, 0.50, 0.36))
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


# ───────────────────────── pinne ─────────────────────────

def fin_mesh(name, body: Body, fin: Fin, mat, side=-1, tears_geo=0.0, seed=0):
    """Mesh a raggi: ogni raggio va dalla radice a un punto della sagoma (uv: u = indice del raggio,
    v = dalla radice al bordo), con la membrana appena ondulata fra un raggio e l'altro."""
    rng = np.random.default_rng(seed)
    outline = np.array(fin.outline, F)
    seg = np.linalg.norm(np.diff(outline, axis=0), axis=1)
    s_ = np.concatenate([[0], np.cumsum(seg)])
    s_ /= s_[-1]
    ss = np.linspace(0, 1, fin.rays + 1)
    edge = np.stack([np.interp(ss, s_, outline[:, 0]), np.interp(ss, s_, outline[:, 1])], axis=1)
    rows = 8
    k = fin.kind
    zc1, h1, _ = (float(a[0]) for a in body.section(np.array([1.0], F)))
    if k in ('pectoral', 'pelvic'):
        t0 = fin.a
        zc, h, _ = (float(a[0]) for a in body.section(np.array([t0], F)))
        z0 = zc - h * (0.3 if k == 'pectoral' else 0.86)
        back = np.array((1.0, side * (0.35 if k == 'pectoral' else 0.25), -0.05 if k == 'pectoral' else -0.4), F)
        back /= np.linalg.norm(back)
        perp = np.array((0.0, side * (0.25 if k == 'pectoral' else 0.45), 1.0), F)
        perp -= back * (perp @ back)
        perp /= np.linalg.norm(perp)
        nrm = np.cross(back, perp)

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
        jit = 1.0 - tears_geo * float(rng.uniform(0.0, 0.45))
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
        return r0 + (back * ea + perp * eo) * fin.size * jit

    verts, uvs = [], []
    for i in range(fin.rays + 1):
        a, b = root(i), tip(i)
        for r in range(rows + 1):
            f = r / rows
            p = a + (b - a) * f
            # pieghe della membrana: i raggi alterni appena fuori piano
            off = (0.0011 if k != 'caudal' else 0.0014) * (1 if i % 2 else -1) * f
            if k in ('dorsal', 'anal', 'caudal'):
                p = p + np.array((0.0, off, 0.0), F)
            else:
                p = p + nrm * off
                # le pinne pari si incurvano verso il corpo in punta
                p = p + np.array((0.0, -side * 0.006 * f * f, 0.0), F)
            verts.append(p)
            uvs.append((float(i), f))
    verts = np.array(verts, F)
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
    for i, fin in enumerate(body.sh.fins):
        if family == 'skeletal':
            mat = fin_material(f'FinBone{i}', (0.45, 0.42, 0.36), spiny=fin.spiny, tears=0.6, bone=True, membrane=0.35)
        else:
            mat = fin_material(f'Fin{i}', lk.fin, spiny=fin.spiny, tears=tears)
        sides = (-1, 1) if fin.kind in ('pectoral', 'pelvic') else (-1,)
        for s in sides:
            obs.append(fin_mesh(f'Fin_{fin.kind}_{i}_{s}', body, fin, mat, side=s, tears_geo=tears, seed=seed + i))
    return obs


# ───────────────────────── attributi della pelle ─────────────────────────

def base_attrs(body: Body, extra=None):
    def u(p):
        return np.clip(p[:, 0], 0, 1).astype(F)

    def v(p):
        return np.clip(body.norm_v(p), -1.2, 1.2).astype(F)

    def mouth(p):
        return np.zeros(len(p), F)
    a = {'u': u, 'v': v, 'mouth': mouth}
    if extra:
        a.update(extra)
    return a


def eyes(body: Body, lk: Look, cloudy=False, name='Eye'):
    if cloudy:
        mat = cloudy_eye('FishCloudyEye', sclera=(0.70, 0.70, 0.64), iris=(0.62, 0.64, 0.6), pupil_col=(0.5, 0.52, 0.5), iris_r=0.75, pupil=0.4)
    else:
        mat = eye_material(name + 'Mat', iris=lk.iris, iris_dark=lk.iris_dark, pupil='round', pupil_size=0.5,
                           shine=(0.6, 0.7, 0.5), shine_strength=0.25, sclera=lk.iris_dark)
    obs = []
    for s in (-1, 1):
        c = body.eye_center(s)
        obs.append(eyeball(f'{name}{s}', tuple(map(float, c)), body.sh.eye_r, mat, look=(0.0, float(s), 0.0), col=COL))
    return obs


# ───────────────────────── le famiglie ─────────────────────────

def build_normal(body: Body, lk: Look, family: str, extra_field=None, extra_attrs=None, mouth_open=0.0, res=0.0022):
    f = body.field(mouth_open=mouth_open)
    if extra_field:
        f = extra_field(f)
    lo, hi = body.bounds()
    if mouth_open:
        lo[2] -= 0.06
    attrs = base_attrs(body, extra_attrs)
    if mouth_open:
        attrs['mouth'] = body.mouth_attr
    ob = sdf_object('Body', f, lo, hi, res=res if not FAST else res * 2, attrs=attrs, col=COL, banded=not FAST)
    ob.data.materials.append(fish_skin('Skin', lk, rot=1.0 if family == 'zombie' else 0.0,
                                       wounds=family == 'bleeding', slime=family == 'corrupt'))
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


def skeletal(body: Body, lk: Look, seed=3):
    """Lisca, cranio, costole; resta la striscia di pelle del dorso con le righe, e gli occhi."""
    rng = np.random.default_rng(seed)
    sh = body.sh
    obs = []
    bone = bone_material()
    raw = body.field(socket=True)
    x_skull = sh.gill_t + 0.01
    # cranio: la testa erosa, con l'orbita grande e il buco dell'opercolo
    n3 = sdf.Noise3(seed)

    gill_c = [np.array((sh.gill_t - 0.035, s_ * 0.0, float(body.section(np.array([sh.gill_t - 0.035], F))[0][0])), F) for s_ in (-1, 1)]

    def skull(p):
        d = raw(p) + 0.0025
        # il bordo posteriore del cranio, frastagliato
        d = np.maximum(d, p[:, 0] - x_skull - 0.012 * n3(p, scale=0.015, octaves=2))
        for s_ in (-1, 1):
            # orbite vuote e larghe
            d = sdf.smax(d, -(np.linalg.norm(p - body.eye_center(s_), axis=1) - sh.eye_r * 1.45), 0.004)
            # niente opercolo: si vedono gli archi delle branchie
            c = gill_c[0] + np.array((0, s_ * 0.0, 0), F)
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

    lo, hi = body.bounds()
    hi[0] = x_skull + 0.02
    o = sdf_object('Skull', lambda p: sdf.smin(skull(p), arch_f(p), 0.002), lo, hi, res=0.0016 if not FAST else 0.004, col=COL, banded=not FAST)
    o.data.materials.append(bone)
    obs.append(o)
    # colonna vertebrale e spine
    nv = 34
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
        # spina neurale (in su e indietro) e, dalla metà in poi, emale (in giù)
        top = zc + h * 0.92
        parts.append(sdf.round_cone(b + (0, 0, r * 0.6), np.array((xm + h * 0.45, 0, top), F), r * 0.32, r * 0.12))
        if xm > 0.5:
            parts.append(sdf.round_cone(b - (0, 0, r * 0.6), np.array((xm + h * 0.45, 0, zc - h * 0.9), F), r * 0.3, r * 0.1))
        elif xm < 0.55:
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
    lo, hi = body.bounds()
    lo[0] = x_skull - 0.03
    o = sdf_object('Spine', spine, lo, hi, res=0.0014 if not FAST else 0.0035, col=COL, banded=not FAST)
    o.data.materials.append(bone)
    obs.append(o)
    # la striscia di pelle del dorso, strappata ai bordi, che pende sopra la lisca
    rawb = body.raw()

    def strip(p):
        d = np.abs(rawb(p) + 0.003) - 0.0025
        v = body.norm_v(p)
        edge = 0.6 + 0.2 * n3(p, scale=0.03, octaves=3)
        d = np.maximum(d, (edge - v) * 0.05)
        holes = n3(p + 7.0, scale=0.018, octaves=2)
        d = np.maximum(d, (holes - 0.28) * 0.02)
        d = np.maximum(d, x_skull + 0.02 - p[:, 0])
        d = np.maximum(d, p[:, 0] - 0.9)
        return d
    lo, hi = body.bounds()
    o = sdf_object('SkinStrip', strip, lo, hi, res=0.0016 if not FAST else 0.0035, col=COL,
                   attrs=base_attrs(body), banded=not FAST)
    o.data.materials.append(fish_skin('StripSkin', lk))
    obs.append(o)
    # il peduncolo della coda resta carnoso (tiene la pinna)
    def ped(p):
        cut = 0.9 + 0.025 * n3(p, scale=0.012, octaves=2) - 0.02 * np.clip(body.norm_v(p), -1, 1)
        return np.maximum(rawb(p), cut - p[:, 0])
    o = sdf_object('Peduncle', ped, lo, hi, res=0.0016 if not FAST else 0.0035, col=COL, attrs=base_attrs(body), banded=not FAST)
    o.data.materials.append(fish_skin('PedSkin', lk))
    obs.append(o)
    obs += eyes(body, lk)
    return obs


def zombie(body: Body, lk: Look, seed=5):
    """Marcio: chiazze, squame cadute, occhi lattiginosi, pinne strappate, una cucitura lungo la pancia."""
    sh = body.sh
    n3 = sdf.Noise3(seed)
    rng = np.random.default_rng(seed)
    # la cucitura: un solco lungo il ventre, sul fianco sinistro
    seam_x = np.linspace(0.26, 0.64, 60, dtype=F)
    seam_v = -0.52 + 0.06 * np.sin(seam_x * 23.0)
    zc, h, _ = body.section(seam_x)
    seam_z = zc + h * seam_v
    seam_y = -body.surface_y(seam_x, seam_z)
    seam_pts = np.stack([seam_x, seam_y, seam_z], axis=1)

    def rot(p):
        r = n3(p, scale=0.06, octaves=4) * 0.5 + 0.5
        return np.clip((r - 0.45) * 2.6, 0, 1).astype(F)

    def ex_field(f):
        from scipy.spatial import cKDTree
        tree = cKDTree(seam_pts)

        def g(p):
            d = f(p)
            # incavi dove il marciume è profondo
            r = rot(p)
            d = d + 0.003 * np.clip((r - 0.7) * 3, 0, 1)
            dist, _ = tree.query(p, k=1, workers=-1)
            d = d + 0.0035 * np.exp(-(dist / 0.0025) ** 2)
            return d
        return g
    ob = build_normal(body, lk, 'zombie', extra_field=ex_field, extra_attrs={'rot': rot})
    obs = [ob]
    # i punti: fili scuri che attraversano il solco
    thread = thread_material()
    for k in range(13):
        i = int(4 + k * (len(seam_pts) - 8) / 12)
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
    obs += eyes(body, lk, cloudy=True)
    return obs


def corrupt(body: Body, lk: Look, seed=7):
    """Tre occhi in più (da persona) che guardano la camera, melma nera che cola, un'escrescenza; i baffi."""
    sh = body.sh
    rng = np.random.default_rng(seed)
    extra_eyes = [(0.215, 0.28, 0.022), (0.44, 0.08, 0.033), (0.31, -0.42, 0.015)]   # (t, v, raggio)
    centers = []
    for t, v, r in extra_eyes:
        zc, h, _ = body.section(np.array([t], F))
        z = float(zc[0] + h[0] * v)
        y = -float(body.surface_y(t, z)) + r * 0.42
        centers.append((np.array((t, y, z), F), r))
    zc, h, _ = body.section(np.array([0.58], F))
    lz = float(zc[0] - h[0] * 0.5)
    lump_c = np.array((0.58, -float(body.surface_y(0.58, lz)) + 0.006, lz), F)
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
        return np.clip(1 - (np.linalg.norm(p - lump_c, axis=1) - 0.024) / 0.01, 0, 1).astype(F)

    def ex_field(f):
        def g(p):
            d = f(p)
            for c, r in centers:
                d = sdf.smax(d, -(np.linalg.norm(p - c, axis=1) - r * 1.02), 0.003)
                # palpebra carnosa: un anello sottile attorno all'occhio, un po' indietro
                q = p - c
                ring = np.sqrt((np.sqrt(q[:, 0] ** 2 + q[:, 2] ** 2) - r * 1.02) ** 2 + (q[:, 1] - r * 0.12) ** 2) - r * 0.17
                d = sdf.smin(d, ring, 0.002)
            lumpd = np.linalg.norm(p - lump_c, axis=1) - 0.026 - 0.007 * n3(p, scale=0.01, octaves=2)
            d = sdf.smin(d, lumpd, 0.01)
            return d
        return g
    ob = build_normal(body, lk, 'corrupt', extra_field=ex_field, extra_attrs={'tar': tar, 'lump': lump})
    obs = [ob]
    obs += eyes(body, lk)
    irises = [(0.30, 0.42, 0.28), (0.22, 0.36, 0.55), (0.42, 0.26, 0.12)]
    for k, ((c, r), ir) in enumerate(zip(centers, irises)):
        mat = human_eye(f'HumanEye{k}', iris=ir)
        look = (float(rng.uniform(-0.12, 0.05)), -1.0, float(rng.uniform(-0.05, 0.1)))
        obs.append(eyeball(f'ExtraEye{k}', tuple(map(float, c)), r, mat, look=look, col=COL))
    tm = tar_material()
    for k, (c, r) in enumerate(centers[:2]):
        a = c + np.array((0.002, -r * 0.35, -r * 1.05), F)
        fb = drip(a, 0.03 + 0.012 * k, r0=0.0022, r1=0.005, dir=(0.08, -0.2, -1))
        o = sdf_object(f'TarDrip{k}', fb, a - 0.06, a + 0.06, res=0.0007, col=COL)
        o.data.materials.append(tm)
        obs.append(o)
    if sh.barbels:
        obs += barbels(body, fish_skin('BarbelSkin', lk))
    return obs


def bleeding(body: Body, lk: Look, seed=9):
    """Ferite aperte con la carne viva, sangue che cola, bocca aperta con i denti sporchi."""
    sh = body.sh
    rng = np.random.default_rng(seed)
    gashes = [((0.30, 0.25), (0.42, -0.35)), ((0.52, 0.45), (0.60, -0.15)), ((0.70, 0.30), (0.74, -0.30))]
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
    ob = build_normal(body, lk, 'bleeding', extra_field=ex_field, extra_attrs={'wound': wound, 'blood': blood}, mouth_open=22.0)
    obs = [ob]
    obs += eyes(body, lk)
    # denti: zanne lungo le due mascelle, verso l'interno della bocca
    tm = dirty_teeth_material()
    R = sdf.rot_matrix('y', -22.0)
    hinge = np.array((sh.mouth_t, 0.0, sh.mouth_z1), F)
    for jaw in ('upper', 'lower'):
        n = 9
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
    lip = (np.array((0.02, -0.006, sh.mouth_z1 - 0.004), F) - hinge) @ R.T + hinge
    fb = drip(lip, 0.04, r0=0.0018, r1=0.0042, dir=(0.0, -0.05, -1))
    o = sdf_object('BloodMouth', fb, lip - 0.06, lip + 0.06, res=0.0006, col=COL)
    o.data.materials.append(bm)
    obs.append(o)
    return obs


def glitch_post(img, seed=11):
    """Il nastro sfasato sull'immagine RGBA (0..1): bande che scorrono di lato, colori separati, un doppio
    spostato, righe, blocchi a pixel."""
    rng = np.random.default_rng(seed)
    H, W = img.shape[:2]
    out = img.copy()
    # doppio sfasato, tenue
    ghost = np.roll(img, int(W * 0.035), axis=1)
    a = ghost[..., 3:4] * 0.28
    out[..., :3] = out[..., :3] * (1 - a) + ghost[..., :3] * a * np.array((0.6, 1.0, 1.2))
    out[..., 3:4] = np.maximum(out[..., 3:4], a)
    # bande strappate
    for _ in range(9):
        h = int(H * rng.uniform(0.01, 0.06))
        y = int(rng.uniform(0.05, 0.9) * H)
        dx = int(W * rng.uniform(-0.05, 0.05))
        out[y:y + h] = np.roll(out[y:y + h], dx, axis=1)
    # colori separati
    rgb = out.copy()
    out[..., 0] = np.roll(rgb[..., 0], -int(W * 0.006), axis=1)
    out[..., 2] = np.roll(rgb[..., 2], int(W * 0.006), axis=1)
    out[..., 3] = np.maximum.reduce([rgb[..., 3], np.roll(rgb[..., 3], -int(W * 0.006), axis=1), np.roll(rgb[..., 3], int(W * 0.006), axis=1)])
    # blocchi a pixel
    for _ in range(4):
        bw, bh = int(W * rng.uniform(0.04, 0.12)), int(H * rng.uniform(0.04, 0.1))
        x0, y0 = int(rng.uniform(0.15, 0.8) * W), int(rng.uniform(0.2, 0.75) * H)
        blk = out[y0:y0 + bh, x0:x0 + bw]
        s = max(4, int(W * 0.008))
        small = blk[::s, ::s]
        out[y0:y0 + bh, x0:x0 + bw] = np.repeat(np.repeat(small, s, axis=0), s, axis=1)[:blk.shape[0], :blk.shape[1]]
    # righe
    out[::3, :, :3] *= 0.86
    return np.clip(out, 0, 1)


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


def pose(obs, yaw=12.0, pitch=-4.0):
    """Il pesce un po' girato verso la camera (testa più vicina) e appena inclinato."""
    from mathutils import Euler, Matrix
    bpy.context.view_layer.update()
    c = Matrix.Translation((0.55, 0, 0))
    M = c @ Euler((0, math.radians(pitch), math.radians(yaw)), 'XYZ').to_matrix().to_4x4() @ c.inverted()
    for o in obs:
        o.matrix_world = M @ o.matrix_world


def build(fid):
    shape, family = PROTOTYPES[fid]
    body = Body(SHAPES[shape])
    lk = LOOKS[shape]
    if family == 'skeletal':
        obs = skeletal(body, lk)
    elif family == 'zombie':
        obs = zombie(body, lk)
    elif family == 'corrupt':
        obs = corrupt(body, lk)
    elif family == 'bleeding':
        obs = bleeding(body, lk)
    else:
        ob = build_normal(body, lk, family)
        obs = [ob] + eyes(body, lk)
        if body.sh.barbels:
            obs += barbels(body, fish_skin('BarbelSkin', lk))
    obs += build_fins(body, lk, family, seed=len(fid))
    return obs, family


def render_fish(fid):
    t0 = time.time()
    sc = studio()
    obs, family = build(fid)
    pose(obs)
    W, H = (800, 400) if FAST else (1600, 800)
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 24 if FAST else 96
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    out_dir = os.path.join(CACHE, 'pesci')
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, f'{fid}.png')
    sc.render.filepath = png
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    im = np.asarray(Image.open(png).convert('RGBA'), np.float32) / 255.0
    if family == 'glitch':
        Image.fromarray((im * 255).astype(np.uint8)).save(png.replace('.png', '_pulito.png'))
        im = glitch_post(im)
        Image.fromarray((im * 255).astype(np.uint8)).save(png)
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


if __name__ == '__main__':
    ids = [a for a in sys.argv[1:] if not a.startswith('--')] or list(PROTOTYPES)
    for fid in ids:
        render_fish(fid)
