"""
Sagome di studio delle creature (solo proporzioni, da discutere prima di modellare).

Per ogni creatura tre varianti, viste di profilo, in nero su fondo chiaro, con una persona
alta 1,80 m per la scala e la linea dell'acqua / del bordo della barca dove serve.
Uso: tools/.venv/bin/python tools/render/silhouettes.py [gulpy|molly|hatch|all]
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import sdf  # noqa: E402
from common import ROOT, mesh_from_arrays, reset_scene  # noqa: E402
from nodes import material  # noqa: E402

OUT = os.path.join(ROOT, 'docs', 'concept')


def chain(points, radii, k=0.03):
    parts = []
    for i in range(len(points) - 1):
        parts.append(sdf.round_cone(points[i], points[i + 1], radii[i], radii[i + 1]))
    return sdf.union(*parts, k=k) if k > 0 else sdf.union(*parts)


def fingers(wrist, direction, length, n=4, spread=0.35, r=0.012, curl=0.3):
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    side = np.cross(d, (0, 0, 1.0))
    if np.linalg.norm(side) < 1e-3:
        side = np.array((1.0, 0, 0))
    side /= np.linalg.norm(side)
    down = np.cross(side, d)
    out = []
    for i in range(n):
        a = (i / (n - 1) - 0.5) * spread * 2
        fd = d * math.cos(a) + side * math.sin(a)
        p0 = np.array(wrist, float)
        p1 = p0 + fd * length * 0.55
        p2 = p1 + (fd * math.cos(curl) - down * math.sin(curl)) * length * 0.5
        out.append(chain([p0, p1, p2], [r * 1.2, r, r * 0.6], k=0.005))
    return out


def human(x=0.0):
    """Persona di riferimento alta 1,80 m, di profilo, rivolta verso −Y."""
    return sdf.union(
        sdf.sphere((x, 0, 1.68), 0.11),
        chain([(x, 0, 1.52), (x, 0.0, 1.05)], [0.17, 0.15]),
        chain([(x, 0, 1.0), (x, 0.0, 0.52), (x, 0.02, 0.05)], [0.09, 0.07, 0.05]),
        chain([(x, 0, 1.45), (x, -0.03, 1.15), (x, -0.06, 0.82)], [0.05, 0.045, 0.04]),
        sdf.box((x, -0.06, 0.03), (0.05, 0.12, 0.03), 0.02),
        k=0.04,
    )


# ───────────────────────── GULPY: prua, va sfamato ─────────────────────────

def gulpy_a():
    """'Lampione': busto emaciato che sale dritto dall'acqua, collo lungo, mascella sganciata sul petto."""
    z = lambda v: v
    torso = chain([(0, 0.0, -0.4), (0, 0.0, 0.6), (0, -0.04, 1.3), (0, -0.06, 1.7)], [0.13, 0.15, 0.17, 0.13])
    neck = chain([(0, -0.06, 1.7), (0, -0.14, 2.05), (0, -0.28, 2.3)], [0.07, 0.06, 0.07])
    skull = sdf.ellipsoid((0, -0.36, 2.36), (0.10, 0.17, 0.10))
    upper = chain([(0, -0.40, 2.38), (0, -0.75, 2.30)], [0.09, 0.03])
    lower = chain([(0, -0.30, 2.28), (0, -0.52, 1.85), (0, -0.62, 1.55)], [0.08, 0.07, 0.03])   # mascella sganciata
    ring = sdf.torus((0, -0.12, 1.98), 0.16, 0.06, axis='z')
    arm = chain([(0, -0.02, 1.62), (0, 0.05, 1.0), (0, -0.35, 0.55)], [0.05, 0.04, 0.035])
    hand = sdf.union(*fingers((0, -0.35, 0.55), (0, -1, -0.2), 0.30))
    return sdf.union(torso, neck, skull, upper, lower, ring, arm, hand, k=0.04), 'acqua'


def gulpy_b():
    """'Serpente': corpo d'anguilla ad arco fuori dall'acqua, due braccia lunghe vicino alla testa."""
    pts = [(0, 0.9, -0.5), (0, 0.75, 0.4), (0, 0.45, 1.4), (0, 0.0, 2.2), (0, -0.45, 2.5), (0, -0.8, 2.25)]
    body = chain(pts, [0.22, 0.24, 0.22, 0.18, 0.14, 0.11])
    head = sdf.ellipsoid((0, -0.95, 2.05), (0.10, 0.22, 0.11))
    jaw = chain([(0, -0.82, 2.08), (0, -1.10, 1.70), (0, -1.15, 1.35)], [0.09, 0.06, 0.03])
    ring = sdf.torus((0, -0.62, 2.40), 0.17, 0.06, axis='y')
    arm1 = chain([(0, -0.30, 2.40), (0, -0.55, 1.65), (0, -1.0, 1.0)], [0.045, 0.04, 0.03])
    hand = sdf.union(*fingers((0, -1.0, 1.0), (0, -0.6, -0.8), 0.32))
    return sdf.union(body, head, jaw, ring, arm1, hand, k=0.04), 'acqua'


def gulpy_c():
    """'Avvoltoio': gigante curvo in piedi nell'acqua alla vita, testa che pende davanti al petto."""
    torso = chain([(0, 0.15, -0.6), (0, 0.10, 0.5), (0, -0.05, 1.6), (0, -0.30, 2.35)], [0.16, 0.17, 0.20, 0.17])
    neck = chain([(0, -0.30, 2.35), (0, -0.65, 2.30), (0, -0.85, 1.95)], [0.09, 0.07, 0.07])
    head = sdf.ellipsoid((0, -0.92, 1.85), (0.11, 0.15, 0.13))
    jaw = chain([(0, -0.88, 1.75), (0, -0.95, 1.30), (0, -0.90, 0.95)], [0.09, 0.07, 0.03])
    ring = sdf.torus((0, -0.55, 2.22), 0.16, 0.06, axis='y')
    arm = chain([(0, -0.25, 2.2), (0, -0.35, 1.3), (0, -0.85, 0.75)], [0.06, 0.05, 0.04])
    hand = sdf.union(*fingers((0, -0.85, 0.75), (0, -0.8, -0.4), 0.38))
    return sdf.union(torso, neck, head, jaw, ring, arm, hand, k=0.05), 'acqua'


# ───────────────────────── MOLLY: fianchi, va fissata ─────────────────────────

def molly_head(c, tilt=0.0):
    """Testa a cupola trasparente (barreleye) con gli occhi tubolari dentro: in sagoma, la cupola."""
    dome = sdf.ellipsoid(c, (0.13, 0.18, 0.17))
    snout = sdf.round_cone((c[0], c[1] - 0.14, c[2] - 0.06), (c[0], c[1] - 0.27, c[2] - 0.10), 0.05, 0.025)
    return sdf.union(dome, snout, k=0.03)


def molly_a():
    """'Palo': corpo dritto lungo la fiancata, collo che si piega sopra il bordo."""
    body = chain([(0, 0.55, -0.8), (0, 0.55, 0.4), (0, 0.50, 1.6), (0, 0.45, 2.4)], [0.10, 0.11, 0.12, 0.09])
    neck = chain([(0, 0.45, 2.4), (0, 0.25, 2.75), (0, -0.15, 2.65), (0, -0.40, 2.25)], [0.06, 0.05, 0.05, 0.05])
    head = molly_head((0, -0.52, 2.12))
    arm = chain([(0, 0.48, 2.2), (0, 0.5, 1.2), (0, 0.40, 0.75)], [0.035, 0.03, 0.025])
    floaty = sdf.round_cone((0, 0.49, 1.95), (0, 0.495, 1.75), 0.09, 0.09)    # bracciolo
    hand = sdf.union(*fingers((0, 0.40, 0.75), (0, -0.6, -0.1), 0.30))
    return sdf.union(body, neck, head, arm, floaty, hand, k=0.035), 'bordo'


def molly_b():
    """'Davanzale': appoggiata al bordo con le braccia incrociate, collo teso verso di te."""
    body = chain([(0, 0.65, -0.6), (0, 0.60, 0.3), (0, 0.50, 0.85)], [0.11, 0.12, 0.12])
    shoulders = sdf.ellipsoid((0, 0.45, 0.95), (0.20, 0.10, 0.08))
    neck = chain([(0, 0.40, 1.0), (0, 0.10, 1.35), (0, -0.35, 1.45), (0, -0.70, 1.35)], [0.06, 0.05, 0.05, 0.05])
    head = molly_head((0, -0.85, 1.30))
    arm = chain([(0, 0.45, 0.92), (0, 0.05, 0.72), (0, -0.55, 0.78)], [0.035, 0.03, 0.025])
    floaty = sdf.round_cone((0, 0.32, 0.86), (0, 0.18, 0.79), 0.09, 0.09)
    hand = sdf.union(*fingers((0, -0.55, 0.78), (0, -1, 0.0), 0.32, curl=0.6))
    return sdf.union(body, shoulders, neck, head, arm, floaty, hand, k=0.035), 'bordo'


def molly_c():
    """'Dita': quasi tutta sott'acqua; si vedono la testa e dita lunghissime aggrappate al bordo."""
    neck = chain([(0, 0.40, -0.3), (0, 0.32, 0.55), (0, 0.15, 0.95)], [0.07, 0.06, 0.055])
    head = molly_head((0, 0.02, 1.02))
    parts = [neck, head]
    for dy in (0.25, -0.15):
        arm = chain([(0, 0.45, -0.2), (0, 0.42, 0.5), (0, dy, 0.80)], [0.035, 0.03, 0.025])
        parts.append(arm)
        parts += fingers((0, dy, 0.80), (0, -0.7, -0.7), 0.42, curl=0.9)
    floaty = sdf.round_cone((0, 0.44, 0.15), (0, 0.43, 0.32), 0.085, 0.085)
    return sdf.union(*parts, floaty, k=0.03), 'bordo'


# ───────────────────────── HATCH: poppa, ci si nasconde ─────────────────────────

def hatch_head(c, scale=1.0):
    s = scale
    skull = sdf.ellipsoid(c, (0.17 * s, 0.22 * s, 0.15 * s))
    jaw = sdf.ellipsoid((c[0], c[1] - 0.10 * s, c[2] - 0.08 * s), (0.16 * s, 0.17 * s, 0.07 * s))
    rod = chain([(c[0], c[1] - 0.05 * s, c[2] + 0.12 * s), (c[0], c[1] - 0.25 * s, c[2] + 0.32 * s), (c[0], c[1] - 0.48 * s, c[2] + 0.22 * s)], [0.015, 0.012, 0.01], k=0.01)
    lure = sdf.sphere((c[0], c[1] - 0.50 * s, c[2] + 0.12 * s), 0.05 * s)
    return sdf.union(skull, jaw, k=0.04), sdf.union(rod, lure, k=0.01)


def hatch_a():
    """'Ragno': corpo basso, gomiti e ginocchia più alti della schiena."""
    body = sdf.ellipsoid((0, 0.1, 0.55), (0.18, 0.45, 0.17))
    head, lure = hatch_head((0, -0.45, 0.62))
    parts = [body, head, lure]
    for dy, side in ((-0.22, 1), (0.42, -1)):
        knee = (0, dy - 0.05 * side, 1.25)
        foot = (0, dy - 0.35 * side, 0.0)
        parts.append(chain([(0, dy, 0.6), knee, foot], [0.05, 0.035, 0.025]))
        parts += fingers(foot, (0, -0.8 * side, -0.1), 0.18)
    return sdf.union(*parts, k=0.04), 'ponte'


def hatch_b():
    """'Strisciante': torso lungo a quattro zampe, braccia più lunghe delle gambe, testa in su."""
    body = chain([(0, 0.75, 0.75), (0, 0.2, 0.95), (0, -0.25, 1.15)], [0.13, 0.15, 0.14])
    head, lure = hatch_head((0, -0.48, 1.30), 1.05)
    arm = chain([(0, -0.22, 1.1), (0, -0.55, 0.55), (0, -0.70, 0.0)], [0.05, 0.04, 0.03])
    leg = chain([(0, 0.75, 0.75), (0, 1.15, 0.45), (0, 0.95, 0.0)], [0.06, 0.05, 0.035])
    hand = sdf.union(*fingers((0, -0.70, 0.0), (0, -1, 0.05), 0.22))
    return sdf.union(body, head, lure, arm, leg, hand, k=0.04), 'ponte'


def hatch_c():
    """'Spilungone': bipede altissimo e piegato in avanti, l'esca che penzola davanti alla faccia."""
    legs = chain([(0, 0.1, 0.0), (0, -0.05, 0.95), (0, 0.05, 1.45)], [0.04, 0.05, 0.10])
    torso = chain([(0, 0.05, 1.45), (0, 0.0, 2.1), (0, -0.30, 2.55)], [0.12, 0.13, 0.12])
    head, lure = hatch_head((0, -0.55, 2.55), 1.1)
    arm = chain([(0, -0.20, 2.4), (0, -0.40, 1.65), (0, -0.45, 0.95)], [0.045, 0.04, 0.03])
    hand = sdf.union(*fingers((0, -0.45, 0.95), (0, -0.2, -1), 0.36))
    return sdf.union(legs, torso, head, lure, arm, hand, k=0.04), 'ponte'



# ───────────────────────── i mostri delle notti 2-5 (10 ottobre) ─────────────────────────
# Stesse regole della prima notte: allungati, magri, sproporzionati, con addosso una cosa del parco.

def whiskers(mouth, n=3, length=0.32, droop=0.9):
    """Barbigli da pesce gatto che pendono dalla bocca."""
    out = []
    for i in range(n):
        a = (i / max(n - 1, 1) - 0.5) * 0.9
        p0 = np.array(mouth, float)
        p1 = p0 + np.array((0, -0.10 + 0.08 * a, -0.12))
        p2 = p0 + np.array((0, -0.16 + 0.22 * a, -length * droop))
        out.append(chain([p0, p1, p2], [0.022, 0.016, 0.010], k=0.005))
    return out


def tickets(top, length=0.55, side=1.0):
    """La striscia di biglietti della sala giochi che pende a zig-zag."""
    p = np.array(top, float)
    pts = [p]
    for i in range(1, 7):
        pts.append(p + np.array((0, side * (0.05 if i % 2 else -0.04), -length * i / 6)))
    return chain(pts, [0.022] * len(pts), k=0.01)


def robin_a():
    """'Granchio': steso sul bordo come un ragno di mare, le zampe-raggi ad arco; la coda resta in acqua."""
    body = sdf.ellipsoid((0, 0.05, 0.98), (0.15, 0.36, 0.13))
    head = sdf.ellipsoid((0, -0.42, 0.88), (0.14, 0.19, 0.09))
    tail = chain([(0, 0.36, 0.95), (0, 0.62, 0.60), (0, 0.78, 0.0), (0, 0.85, -0.5)], [0.11, 0.09, 0.07, 0.05])
    parts = [body, head, tail, *whiskers((0, -0.58, 0.84), length=0.3)]
    for yb, yk, zk, yf, zf in ((-0.18, -0.44, 1.32, -0.70, 0.50), (-0.04, -0.22, 1.40, -0.36, 0.40),
                               (0.20, 0.42, 1.34, 0.50, 0.48), (0.32, 0.64, 1.20, 0.68, 0.22)):
        parts.append(chain([(0, yb, 1.02), (0, yk, zk), (0, yf, zf)], [0.035, 0.026, 0.016], k=0.01))
    parts += [*fingers((0, -0.70, 0.50), (0, -0.2, -1), 0.2), tickets((0, 0.0, 0.88), 0.5)]
    return sdf.union(*parts, k=0.035), 'bordo_secchio'


def robin_b():
    """'Scimmia': mezzo corpo in acqua, la testa che spunta dal bordo, braccia lunghissime dentro la barca."""
    torso = chain([(0, 0.62, -0.6), (0, 0.50, 0.3), (0, 0.36, 0.95)], [0.12, 0.13, 0.13])
    head = sdf.ellipsoid((0, 0.14, 1.12), (0.13, 0.18, 0.11))
    arm1 = chain([(0, 0.32, 0.98), (0, 0.02, 1.30), (0, -0.45, 1.10), (0, -0.70, 0.56)], [0.045, 0.04, 0.035, 0.03])
    arm2 = chain([(0, 0.34, 0.94), (0, 0.06, 1.02), (0, -0.25, 0.86), (0, -0.32, 0.45)], [0.045, 0.04, 0.035, 0.03])
    parts = [torso, head, arm1, arm2, *whiskers((0, -0.02, 1.07), length=0.36),
             *fingers((0, -0.70, 0.56), (0, -0.3, -1), 0.28), *fingers((0, -0.32, 0.45), (0, -0.6, -0.8), 0.24),
             tickets((0, -0.40, 1.12), 0.6, -1.0)]
    return sdf.union(*parts, k=0.035), 'bordo_secchio'


def robin_c():
    """'Trampoliere': in piedi nell'acqua su zampe-raggi altissime, il collo che scende fino al secchio."""
    body = sdf.ellipsoid((0, 0.55, 1.78), (0.13, 0.32, 0.14))
    parts = [body]
    for i in range(3):
        yb = 0.42 + 0.14 * i
        parts.append(chain([(0, yb, 1.70), (0, 0.12 + 0.36 * i, 2.08), (0, -0.02 + 0.46 * i, -0.4)], [0.04, 0.03, 0.02], k=0.01))
    neck = chain([(0, 0.32, 1.86), (0, 0.0, 2.02), (0, -0.32, 1.62), (0, -0.46, 1.22)], [0.07, 0.06, 0.055, 0.05])
    head = sdf.ellipsoid((0, -0.52, 1.12), (0.10, 0.15, 0.09))
    arm = chain([(0, 0.30, 1.66), (0, -0.18, 1.12), (0, -0.66, 0.62)], [0.04, 0.035, 0.03])
    parts += [neck, head, arm, *whiskers((0, -0.62, 1.06), length=0.26), *fingers((0, -0.66, 0.62), (0, -0.3, -1), 0.24),
              tickets((0, 0.10, 2.02), 0.5)]
    return sdf.union(*parts, k=0.035), 'bordo_secchio'


def pistol(hand, aim):
    """La pistola ad acqua fusa nella mano: impugnatura, serbatoio tondo sopra, canna verso aim."""
    h = np.array(hand, float)
    d = np.array(aim, float)
    d /= np.linalg.norm(d)
    up = np.array((0, -d[2], d[1]))
    grip = sdf.ellipsoid(tuple(h), (0.05, 0.08, 0.08))
    tank = sdf.sphere(tuple(h + up * 0.11 - d * 0.02), 0.08)
    barrel = sdf.round_cone(tuple(h + d * 0.05 + up * 0.04), tuple(h + d * 0.26 + up * 0.05), 0.035, 0.025)
    return sdf.union(grip, tank, barrel, k=0.02)


def tube_mouth(base, aim, length=0.28):
    d = np.array(aim, float)
    d /= np.linalg.norm(d)
    b = np.array(base, float)
    return sdf.round_cone(tuple(b), tuple(b + d * length), 0.055, 0.03)


def archie_a():
    """'Cecchino': steso a pelo d'acqua come un coccodrillo, solo la testa fuori, il muso a tubo puntato in alto."""
    aim = (0, -0.75, 0.66)
    body = chain([(0, 1.15, -0.18), (0, 0.65, -0.08), (0, 0.15, -0.02)], [0.10, 0.16, 0.14])
    head = sdf.ellipsoid((0, -0.10, 0.06), (0.12, 0.22, 0.10))
    eyes = sdf.union(sdf.sphere((0, -0.08, 0.17), 0.06), sdf.sphere((0, -0.16, 0.15), 0.05))
    mouth = tube_mouth((0, -0.28, 0.10), aim, 0.34)
    arm = chain([(0, 0.08, -0.02), (0, -0.25, 0.10), (0, -0.48, 0.22)], [0.04, 0.035, 0.03])
    return sdf.union(body, head, eyes, mouth, arm, pistol((0, -0.52, 0.25), aim), k=0.03), 'acqua_lampara'


def archie_b():
    """'Pistolero': mezzo fuori dall'acqua, dritto, il braccio-pistola teso verso la luce."""
    aim = (0, -0.8, 0.6)
    torso = chain([(0, 0.40, -0.7), (0, 0.36, 0.2), (0, 0.28, 1.12)], [0.12, 0.13, 0.12])
    neck = chain([(0, 0.28, 1.12), (0, 0.18, 1.36)], [0.06, 0.06])
    head = sdf.ellipsoid((0, 0.06, 1.46), (0.12, 0.17, 0.12))
    eyes = sdf.sphere((0, 0.04, 1.58), 0.06)
    mouth = tube_mouth((0, -0.08, 1.50), aim, 0.26)
    arm = chain([(0, 0.22, 1.06), (0, -0.18, 1.28), (0, -0.58, 1.52)], [0.045, 0.04, 0.035])
    arm2 = chain([(0, 0.34, 1.02), (0, 0.52, 0.42), (0, 0.46, -0.1)], [0.04, 0.035, 0.03])
    return sdf.union(torso, neck, head, eyes, mouth, arm, arm2, pistol((0, -0.62, 1.55), aim), k=0.035), 'acqua_lampara'


def archie_c():
    """'Periscopio': un collo sottilissimo che sale dritto dall'acqua, la testa in cima piegata verso la luce."""
    aim = (0, -0.9, 0.42)
    neck = chain([(0, 0.48, -0.6), (0, 0.45, 0.6), (0, 0.40, 1.6), (0, 0.32, 2.28)], [0.13, 0.10, 0.08, 0.07])
    head = sdf.ellipsoid((0, 0.20, 2.38), (0.10, 0.16, 0.10))
    eyes = sdf.sphere((0, 0.18, 2.48), 0.05)
    mouth = tube_mouth((0, 0.06, 2.42), aim, 0.30)
    arm = chain([(0, 0.44, 0.45), (0, 0.24, 0.95), (0, 0.02, 1.38)], [0.04, 0.035, 0.03])
    return sdf.union(neck, head, eyes, mouth, arm, pistol((0, -0.02, 1.42), aim), k=0.035), 'acqua_lampara'


# la lenza disegnata nelle tavole di Lampy: dalla punta della canna (in alto a sinistra) all'acqua
LINE0, LINE1 = np.array((0.0, -1.15, 2.25)), np.array((0.0, 0.55, 0.0))


def on_line(s):
    return tuple(LINE0 + (LINE1 - LINE0) * s)


def sucker_head(c, r=0.13, aim=(0, -0.6, 0.8)):
    """Testa tonda a ventosa con la cuffia da piscina: in sagoma, un disco con la calotta sopra."""
    d = np.array(aim, float)
    d /= np.linalg.norm(d)
    cc = np.array(c, float)
    head = sdf.sphere(tuple(cc), r)
    disc = sdf.round_cone(tuple(cc + d * r * 0.6), tuple(cc + d * r * 1.05), r * 0.95, r * 0.9)
    cap = sdf.ellipsoid(tuple(cc - d * r * 0.35 + np.array((0, 0, 0.02))), (r * 1.05, r * 1.0, r * 0.85))
    return sdf.union(head, disc, cap, k=0.03)


def lampy_a():
    """'Anguilla': corpo d'anguilla che risale la lenza a esse, la testa a ventosa attaccata al filo."""
    L = LINE1 - LINE0
    perp = np.array((0, -L[2], L[1])) / np.linalg.norm(L)
    pts, rad = [], []
    for i, s in enumerate(np.linspace(1.18, 0.56, 9)):
        off = 0.13 * math.sin(i * 1.3) if s < 1.0 else 0.0
        pts.append(tuple(np.array(on_line(min(s, 1.0))) + perp * off + (np.array((0, 0.25, -0.45)) * max(s - 1.0, 0) / 0.18)))
        rad.append(0.05 + 0.04 * min(i, 6) / 6)
    body = chain(pts, rad)
    head = sucker_head(on_line(0.5), 0.13, tuple(LINE0 - LINE1))
    return sdf.union(body, head, k=0.04), 'acqua_lenza'


def lampy_b():
    """'Bambino': un corpo da bambino magrissimo appeso alla lenza, braccia lunghissime che tirano giù."""
    sh = (0, -0.16, 0.86)
    torso = chain([sh, (0, -0.10, 0.45), (0, -0.04, 0.08)], [0.10, 0.085, 0.08])
    head = sucker_head((0, -0.24, 1.14), 0.16, (0, -0.55, 0.85))
    arm1 = chain([sh, (0, -0.44, 0.98), on_line(0.47)], [0.042, 0.036, 0.03])
    arm2 = chain([sh, (0, -0.58, 1.20), on_line(0.33)], [0.042, 0.036, 0.03])
    leg1 = chain([(0, -0.04, 0.08), (0, -0.14, -0.35), (0, -0.06, -0.75)], [0.06, 0.05, 0.04])
    leg2 = chain([(0, -0.04, 0.08), (0, 0.10, -0.32), (0, 0.22, -0.68)], [0.06, 0.05, 0.04])
    hands = [*fingers(on_line(0.47), (0, -0.4, 0.6), 0.14, curl=1.2), *fingers(on_line(0.33), (0, -0.4, 0.6), 0.14, curl=1.2)]
    return sdf.union(torso, head, arm1, arm2, leg1, leg2, *hands, k=0.03), 'acqua_lenza'


def lampy_c():
    """'Sanguisuga': un arco di carne attaccato alla lenza per i due capi, come una sanguisuga che cammina."""
    a, b = np.array(on_line(0.40)), np.array(on_line(0.80))
    L = b - a
    perp = np.array((0, -L[2], L[1])) / np.linalg.norm(L)
    if perp[2] < 0:
        perp = -perp
    pts = [tuple(a + L * t + perp * 0.46 * math.sin(math.pi * t)) for t in np.linspace(0.08, 1, 9)]
    body = chain(pts, [0.09, 0.12, 0.14, 0.15, 0.15, 0.14, 0.12, 0.1, 0.08])
    head = sucker_head(tuple(a + perp * 0.08), 0.17, tuple(LINE0 - LINE1))
    tail = sdf.sphere(tuple(b + perp * 0.04), 0.09)
    return sdf.union(body, head, tail, k=0.05), 'acqua_lenza'


def fangs(jaw, down=0.28, n=3, spread=0.12, lean=-0.05):
    out = []
    j = np.array(jaw, float)
    for i in range(n):
        y = (i / max(n - 1, 1) - 0.5) * spread
        p0 = j + np.array((0, y, 0))
        out.append(sdf.round_cone(tuple(p0), tuple(p0 + np.array((0, lean, -down * (1.0 - 0.25 * abs(y) / spread)))), 0.022, 0.006))
    return out


def goggles(c, r):
    cc = np.array(c, float)
    strap = sdf.torus(tuple(cc), r * 1.02, 0.018, axis='z')
    lens = sdf.ellipsoid(tuple(cc + np.array((0, -r * 0.9, 0.02))), (0.06, 0.04, 0.045))
    return sdf.union(strap, lens, k=0.01)


def fangy_a():
    """'Lanterna': lungo e sottile appena sotto il pelo dell'acqua, solo la testa fuori, in ascolto."""
    body = chain([(0, 1.25, -0.38), (0, 0.75, -0.28), (0, 0.28, -0.12), (0, -0.02, 0.10)], [0.07, 0.11, 0.12, 0.10])
    head = sdf.ellipsoid((0, -0.20, 0.30), (0.11, 0.17, 0.13))
    return sdf.union(body, head, goggles((0, -0.20, 0.34), 0.13), *fangs((0, -0.32, 0.22), 0.30), k=0.03), 'acqua_vista'


def fangy_b():
    """'Mastino': curvo e basso, la testa spinta avanti, le zanne che pendono, le nocche in acqua."""
    torso = chain([(0, 0.62, -0.45), (0, 0.46, 0.42), (0, 0.18, 0.88)], [0.14, 0.17, 0.15])
    head = sdf.ellipsoid((0, -0.16, 0.86), (0.13, 0.20, 0.14))
    parts = [torso, head, goggles((0, -0.16, 0.92), 0.15), *fangs((0, -0.30, 0.76), 0.38, 4, 0.16)]
    for dy in (0.0, 0.12):
        parts.append(chain([(0, 0.24 + dy, 0.80), (0, -0.10 + dy, 0.45), (0, -0.36 + dy, 0.0)], [0.05, 0.045, 0.04]))
        parts += fingers((0, -0.36 + dy, 0.0), (0, -0.7, -0.6), 0.22)
    return sdf.union(*parts, k=0.035), 'acqua_vista'


def fangy_c():
    """'In ascolto': altissimo in piedi nell'acqua fino al petto, la testa piegata, una mano all'orecchio."""
    torso = chain([(0, 0.26, -0.6), (0, 0.22, 0.6), (0, 0.15, 1.7)], [0.10, 0.11, 0.12])
    neck = chain([(0, 0.15, 1.7), (0, 0.06, 1.98)], [0.06, 0.055])
    head = sdf.ellipsoid((0, -0.04, 2.08), (0.11, 0.16, 0.13))
    ear_arm = chain([(0, 0.18, 1.62), (0, 0.36, 1.92), (0, 0.14, 2.16)], [0.04, 0.035, 0.03])
    arm = chain([(0, 0.16, 1.60), (0, 0.02, 0.95), (0, -0.10, 0.35)], [0.04, 0.035, 0.03])
    parts = [torso, neck, head, ear_arm, arm, goggles((0, -0.04, 2.13), 0.13), *fangs((0, -0.16, 1.98), 0.30),
             *fingers((0, 0.14, 2.16), (0, -0.4, 0.3), 0.16, curl=0.9), *fingers((0, -0.10, 0.35), (0, -0.2, -1), 0.3)]
    return sdf.union(*parts, k=0.035), 'acqua_vista'

SHEETS = {
    'gulpy': ('GULPY — prua, va sfamato', [('A · Lampione', gulpy_a), ('B · Serpente', gulpy_b), ('C · Avvoltoio', gulpy_c)]),
    'molly': ('MOLLY — fianchi, va fissata', [('A · Palo', molly_a), ('B · Davanzale', molly_b), ('C · Dita', molly_c)]),
    'hatch': ('HATCH — poppa, ci si nasconde', [('A · Ragno', hatch_a), ('B · Strisciante', hatch_b), ('C · Spilungone', hatch_c)]),
    'robin': ('ROBIN — notte 2, ruba dal secchio: si scaccia con la luce', [('A · Granchio', robin_a), ('B · Scimmia', robin_b), ('C · Trampoliere', robin_c)]),
    'archie': ('ARCHIE — notte 3, mira alla lampara: si spegne la luce', [('A · Cecchino', archie_a), ('B · Pistolero', archie_b), ('C · Periscopio', archie_c)]),
    'lampy': ('LAMPY — notte 4, tira la lenza: non si ferra', [('A · Anguilla', lampy_a), ('B · Bambino', lampy_b), ('C · Sanguisuga', lampy_c)]),
    'fangy': ('FANGY — notte 5, caccia a orecchio: si sta zitti', [('A · Lanterna', fangy_a), ('B · Mastino', fangy_b), ('C · In ascolto', fangy_c)]),
}


def render_sheet(key):
    title, variants = SHEETS[key]
    reset_scene()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 8
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
    m, g = material('Ink')
    g.output_material(g.emission((0.0, 0.0, 0.0), 1.0))
    spacing = 2.6
    for i, (label, fn) in enumerate(variants):
        field, ref = fn()
        x0 = i * spacing
        V, F, N = sdf.mesh(lambda p, f=field, x0=x0: f(p - np.array((0, 0, 0), np.float32)), (-0.6, -1.5, -0.9), (0.6, 1.4, 3.1), res=0.012)
        ob = mesh_from_arrays(f'Sil{i}', V + np.array((0, x0, 0), np.float32), F.tolist(), smooth=False, col='sil')
        ob.data.materials.append(m)
        hV, hF, _ = sdf.mesh(human(), (-0.3, -0.4, -0.05), (0.3, 0.4, 1.85), res=0.015)
        h = mesh_from_arrays(f'Human{i}', hV + np.array((0, x0 + 1.05, 0), np.float32), hF.tolist(), smooth=False, col='sil')
        hm, hg = material(f'HumanInk{i}')
        hg.output_material(hg.emission((0.62, 0.62, 0.62), 1.0))
        h.data.materials.append(hm)
    cam_d = bpy.data.cameras.new('Ortho')
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = spacing * 3.0
    cam = bpy.data.objects.new('Ortho', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (20.0, spacing, 1.1)
    cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    W, H = 1800, 1050
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.film_transparent = False
    path = os.path.join(OUT, f'_{key}_raw.png')
    os.makedirs(OUT, exist_ok=True)
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    annotate(path, os.path.join(OUT, f'{key}_sagome.png'), title, variants, W, H, spacing, cam_d.ortho_scale)
    os.remove(path)


def annotate(src, dst, title, variants, W, H, spacing, ortho):
    im = Image.open(src).convert('RGB')
    d = ImageDraw.Draw(im)
    px_per_m = W / ortho
    zc = 1.1

    def zpx(z):
        return int(H / 2 - (z - zc) * px_per_m)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
        small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
    except OSError:
        font = small = ImageFont.load_default()
    for i, (label, fn) in enumerate(variants):
        _, ref = fn()
        cx = int(W / 2 + (i * spacing - spacing) * px_per_m)
        ypx = lambda yy, cx=cx: int(cx + yy * px_per_m)
        if ref in ('acqua_vista', 'acqua_lampara', 'acqua_lenza', 'bordo_secchio'):
            # acqua velata: quello che resta sotto si vede in trasparenza
            ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.rectangle([cx - int(1.25 * px_per_m), zpx(0.0), cx + int(1.25 * px_per_m), H], fill=(150, 185, 205, 175))
            im = Image.alpha_composite(im.convert('RGBA'), ov).convert('RGB')
            d = ImageDraw.Draw(im)
            d.text((cx - int(1.2 * px_per_m), zpx(0.0) + 8), 'superficie del mare', fill=(40, 70, 90), font=small)
            if ref == 'bordo_secchio':
                y = zpx(0.75)
                d.line([cx - int(1.25 * px_per_m), y, ypx(0.0), y], fill=(180, 120, 60), width=6)
                d.text((cx - int(1.2 * px_per_m), y - 32), 'bordo della barca', fill=(140, 90, 40), font=small)
                # il secchio sul banco, dentro la barca
                d.polygon([(ypx(-0.86), zpx(0.52)), (ypx(-0.56), zpx(0.52)), (ypx(-0.60), zpx(0.22)), (ypx(-0.82), zpx(0.22))], outline=(120, 120, 120), width=4)
                d.text((ypx(-1.2), zpx(0.18)), 'secchio', fill=(100, 100, 100), font=small)
            elif ref == 'acqua_lampara':
                lx, lz = -1.15, 2.75
                d.ellipse([ypx(lx) - 16, zpx(lz) - 16, ypx(lx) + 16, zpx(lz) + 16], outline=(200, 150, 40), width=5)
                d.text((ypx(lx) + 24, zpx(lz) - 14), 'lampara', fill=(160, 110, 20), font=small)
            elif ref == 'acqua_lenza':
                d.line([ypx(LINE0[1]), zpx(LINE0[2]), ypx(LINE1[1]), zpx(LINE1[2])], fill=(120, 120, 120), width=2)
                d.text((ypx(LINE0[1]) + 10, zpx(LINE0[2]) - 30), 'lenza', fill=(100, 100, 100), font=small)
        elif ref == 'acqua':
            y = zpx(0.0)
            d.rectangle([cx - int(1.25 * px_per_m), y, cx + int(1.25 * px_per_m), H], fill=(150, 185, 205))
            d.text((cx - int(1.2 * px_per_m), y + 8), 'superficie del mare', fill=(40, 70, 90), font=small)
        elif ref == 'bordo':
            y = zpx(0.75)
            d.line([cx - int(1.25 * px_per_m), y, cx + int(0.0 * px_per_m), y], fill=(180, 120, 60), width=6)
            d.text((cx - int(1.2 * px_per_m), y - 32), 'bordo della barca', fill=(140, 90, 40), font=small)
            yw = zpx(0.0)
            d.rectangle([cx - int(1.25 * px_per_m), yw, cx + int(1.25 * px_per_m), H], fill=(150, 185, 205))
        else:
            y = zpx(0.0)
            d.line([cx - int(1.25 * px_per_m), y, cx + int(1.25 * px_per_m), y], fill=(180, 120, 60), width=6)
            d.text((cx - int(1.2 * px_per_m), y + 8), 'ponte della barca', fill=(140, 90, 40), font=small)
        d.text((cx - int(1.1 * px_per_m), 70), label, fill=(20, 20, 20), font=font)
    d.text((40, 15), title, fill=(10, 10, 10), font=font)
    d.text((W - 430, H - 40), 'in grigio: persona alta 1,80 m', fill=(90, 90, 90), font=small)
    im.save(dst)


if __name__ == '__main__':
    which = sys.argv[-1] if len(sys.argv) > 1 and sys.argv[-1] in (*SHEETS, 'all') else 'all'
    for k in (SHEETS if which == 'all' else [which]):
        render_sheet(k)
        print('ok', k, flush=True)
