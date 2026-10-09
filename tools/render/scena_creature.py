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
    # vicino alla poppa e alto fuori dall'acqua: quando ti volti spunta da dietro lo specchio di poppa
    o = (0.25, -5.6, -0.9)
    M = LAST_M['hatch_conta'] = M_of(o, yaw=facing_yaw(o), pitch=8.0)
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
}
