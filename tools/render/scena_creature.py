"""
Le creature approvate dentro la scena della barca, nelle pose degli stati di gioco.

Ogni posa è uno strato del panorama (come la canna e i pesci nel secchio): visto dall'occhio del
pescatore, con le stesse luci (ambiente, lampara, lanterna); la barca fa da maschera davanti e il
mare nasconde la parte sott'acqua.

    gulpy_sale       Gulpy che sale, lontano davanti alla prua, immerso fino al petto
    gulpy_pretende   Gulpy che si sporge sulla prua, le mani sul bordo, la mascella aperta
    molly_destra     Molly aggrappata al bordo destro, accanto al pescatore
    molly_sinistra   Molly aggrappata al bordo sinistro
    hatch_conta      Hatch in acqua dietro la poppa, alto fino alla vita, col pesciolino luminoso
    robin_secchio    Robin steso sul bordo sinistro verso prua, il braccio lunghissimo nel secchio (notte 2)

Uso: tools/.venv/bin/python tools/render/jobs.py creature --quality preview
"""
from __future__ import annotations

import math

import bpy
import numpy as np

import boat
from common import EYE

F = np.float32


def M_of(origin, yaw=0.0, pitch=0.0, scale=1.0):
    """Da coordinate locali della creatura a coordinate della barca: traslazione, poi yaw (Z), pitch (X), scala."""
    from mathutils import Matrix
    return (Matrix.Translation(tuple(map(float, origin))) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
            @ Matrix.Rotation(math.radians(pitch), 4, 'X') @ Matrix.Scale(scale, 4))


def facing_yaw(origin, target=EYE):
    """Yaw che volta la faccia della creatura (−y locale) verso target."""
    return math.degrees(math.atan2(target[0] - origin[0], origin[1] - target[1]))


def to_local(M, p):
    from mathutils import Vector
    v = M.inverted() @ Vector(tuple(map(float, p)))
    return np.array((v.x, v.y, v.z), F)


# l'ultima trasformazione usata per ogni posa (serve ai jumpscare, che partono dalla posa di gioco)
LAST_M = {}


def place(obs, M):
    bpy.context.view_layer.update()
    for o in obs:
        o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()
    return obs


def gunwale_at(y, side):
    """Centro e quota superiore del capodibanda alla coordinata y, sul lato 'side' (+1 destra, −1 sinistra)."""
    t = y / boat.HALF
    x, _, z = boat.hull_point(t, 1.0, side)
    return float(x) + side * 0.012, float(z) + 0.012 + 0.0225


# ───────────────────────── pose ─────────────────────────

# Gulpy è un gigante: più grande del modello della vetrina, e arriva dal lato sinistro della prua,
# così l'albero della lampara non lo copre (davanti alla prua c'è la lampara sul buttafuori).
GULPY_SCALE = 1.35


def gulpy_sale():
    import gulpy
    o = (-2.2, 7.0, -1.1)
    M = LAST_M['gulpy_sale'] = M_of(o, yaw=facing_yaw(o), pitch=6.0, scale=GULPY_SCALE)
    obs = gulpy.build(viewer=to_local(M, EYE))
    return place(obs, M)


def gulpy_pretende():
    import gulpy
    o = (-1.9, 3.4, -0.4)
    M = LAST_M['gulpy_pretende'] = M_of(o, yaw=facing_yaw(o), pitch=25.0, scale=GULPY_SCALE)
    # una mano sul capodibanda di sinistra, l'altra sulla punta di prua
    xg, zg = gunwale_at(1.2, -1)
    xb, zb = gunwale_at(2.45, -1)
    grip = [to_local(M, (xg + 0.02, 1.2, zg)), to_local(M, (xb + 0.04, 2.45, zb))]
    lo = np.minimum(np.array((-0.62, -1.0, -0.02), F), np.min(grip, axis=0) - 0.25)
    hi = np.maximum(np.array((0.62, 0.48, 2.72), F), np.max(grip, axis=0) + 0.25)
    obs = gulpy.build(grip=grip, viewer=to_local(M, EYE), lo=lo, hi=hi)
    return place(obs, M)


def molly(side):
    import molly as mo
    y = -0.26 if side > 0 else 0.15
    xc, ztop = gunwale_at(y, side)
    M = LAST_M['molly_destra' if side > 0 else 'molly_sinistra'] = M_of((xc, y, ztop - mo.GUN_TOP), yaw=-90.0 if side > 0 else 90.0)
    v = to_local(M, EYE)
    d = v - mo.C
    turn = max(-35.0, min(35.0, math.degrees(math.atan2(float(d[0]), float(-d[1])))))
    obs = mo.build(viewer=v, head_turn=turn)
    return place(obs, M)


def hatch_conta():
    import hatch
    # appena dietro la poppa, altissimo, piegato sulla barca: l'esca gli penzola sopra il ponte di poppa
    o = (0.10, -3.45, -1.05)
    M = LAST_M['hatch_conta'] = M_of(o, yaw=facing_yaw(o), pitch=14.0)
    obs = hatch.build(viewer=to_local(M, EYE))
    lights = [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith('ToyLight')]
    # di notte, a qualche metro, lo illumina solo la sua esca: più forte che in vetrina
    for li in lights:
        li.data.energy = 9.0
        li.data.shadow_soft_size = 0.035
    return place(obs + lights, M)


POSES = {
    'gulpy_sale': (gulpy_sale, 'world', False),
    'gulpy_pretende': (gulpy_pretende, 'boat', True),
    'molly_destra': (lambda: molly(+1), 'boat', False),
    'molly_sinistra': (lambda: molly(-1), 'boat', False),
    'hatch_conta': (hatch_conta, 'world', False),
    'robin_secchio': (lambda: robin_secchio(), 'boat', True),
}


# ───────────────────────── notte 2 ─────────────────────────

# Robin (robin.py) sul capodibanda di sinistra verso prua. La faccia sta a ROBIN_YAW dall'occhio (YAW.robin nel
# gioco) ed è girata verso il pescatore; il busto, girato a metà tra lui e il secchio, si appoggia al bordo e la
# coda scende in acqua. Il braccio lunghissimo passa davanti al banco di prua, sopra il telone, la bambola e la
# borraccia, e tira fuori un pesce dal secchio (boat.BUCKET_POS) dalla parte del pescatore, davanti al manico:
# la batteria resta a destra, il braccio non ci arriva. Le zampe dalla parte della prua stanno lontane dal punto
# dove si aggrappa Gulpy in gulpy_pretende (capodibanda di sinistra a y = 1,2): nella notte 2 ci sono insieme.
ROBIN_YAW = -38.0
ROBIN_BODY = 50.0      # yaw del busto: 38° guarderebbe il pescatore, 83° dritto dentro la barca, 100° il secchio


def _robin_M(y):
    """La trasformazione di Robin col busto appoggiato al capodibanda di sinistra alla coordinata y."""
    import robin as ro
    xc, ztop = gunwale_at(y, -1)
    return M_of((xc, y, ztop - ro.GUN), yaw=ROBIN_BODY)


def _bordo(y, dentro=0.0):
    """Un punto sopra il capodibanda di sinistra alla coordinata y (dentro > 0: verso l'interno della barca)."""
    x, z = gunwale_at(y, -1)
    return (x + dentro, y, z)


def _fiancata_fuori(y, z):
    """Un punto sulla fiancata di sinistra, dalla parte del mare, alla quota z."""
    t = y / boat.HALF
    K, S = float(boat.keel(t)), float(boat.sheer(t))
    x, _, _ = boat.hull_point(t, min((z - K) / (S - K), 1.0), -1)
    return (float(x) - 0.012, y, z)


def robin_posa():
    """La trasformazione della posa robin_secchio e i parametri di robin.build() in coordinate locali (servono
    anche alla vetrina di robin.py)."""
    import robin as ro
    from mathutils import Vector

    def face_yaw(y):
        h = _robin_M(y) @ Vector(tuple(map(float, ro.HEAD)))
        return math.degrees(math.atan2(h.x - EYE[0], h.y - EYE[1]))
    # dove si appoggia il busto perché la faccia stia a ROBIN_YAW (andando verso prua lo yaw cresce)
    a, b = -0.4, 1.4
    for _ in range(36):
        m = (a + b) / 2
        a, b = (m, b) if face_yaw(m) < ROBIN_YAW else (a, m)
    y0 = (a + b) / 2
    M = _robin_M(y0)
    R = np.array(M.to_3x3(), F)
    x0, _ = gunwale_at(y0 - 0.01, -1)
    x1, _ = gunwale_at(y0 + 0.01, -1)
    lungo = R.T @ np.array((x1 - x0, 0.02, 0.0), F)
    bx, by, bz = boat.BUCKET_POS
    rim = (bx, by, bz + 0.285)
    # la mano stringe il pesce sopra la bocca del secchio, dalla parte del pescatore e davanti al manico
    fist = (bx - 0.075, by - 0.075, bz + 0.40)
    bench_x = -(boat.half_width_at(by, boat.BENCH_TOP) - 0.07)
    # le punte delle zampe: dal lato della poppa due sul capodibanda e una fuori, sulla fiancata; dal lato della
    # prua una sul banco (tra la fiancata e il telone), una sul capodibanda prima di y = 1 e una fuori
    feet = [_bordo(y0 - 0.62, 0.02), _bordo(y0 - 0.40, -0.03), _fiancata_fuori(y0 - 0.12, 0.42),
            (bench_x, by - 0.07, boat.BENCH_TOP), _bordo(y0 + 0.30), _fiancata_fuori(y0 + 0.28, 0.46)]
    grip = _bordo(y0 - 0.22)
    loc = lambda p: tuple(float(v) for v in to_local(M, p))
    return M, {'viewer': loc(EYE), 'bucket': loc(rim), 'reach': loc(fist), 'feet': [loc(p) for p in feet],
               'grip': loc(grip), 'lungo': tuple(float(v) for v in lungo)}


def robin_secchio():
    import robin as ro
    M, kw = robin_posa()
    LAST_M['robin_secchio'] = M
    return place(ro.build(**kw), M)
