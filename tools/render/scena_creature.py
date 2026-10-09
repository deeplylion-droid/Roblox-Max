"""
Le creature approvate dentro la scena della barca, nelle pose degli stati di gioco.

Ogni posa è uno strato del panorama (come la canna e i pesci nel secchio): visto dall'occhio del
pescatore, con le stesse luci (ambiente, lampara, lanterna); la barca fa da maschera davanti e il
mare nasconde la parte sott'acqua.

    gulpy_sale       Gulpy che sale, lontano davanti alla prua, immerso fino al petto
    gulpy_pretende   Gulpy che si sporge sulla prua, le mani sul bordo, la mascella aperta
    molly_destra     Molly aggrappata al bordo destro, accanto al pescatore
    molly_sinistra   Molly aggrappata al bordo sinistro
    hatch_conta      Hatch in acqua dietro la poppa, col pesciolino luminoso

Uso: tools/.venv/bin/python tools/render/jobs.py creature --quality preview
"""
from __future__ import annotations

import math

import bpy
import numpy as np

import boat
from common import EYE

F = np.float32


def M_of(origin, yaw=0.0, pitch=0.0):
    """Da coordinate locali della creatura a coordinate della barca: traslazione, poi yaw (Z), poi pitch (X)."""
    from mathutils import Matrix
    return (Matrix.Translation(tuple(map(float, origin))) @ Matrix.Rotation(math.radians(yaw), 4, 'Z')
            @ Matrix.Rotation(math.radians(pitch), 4, 'X'))


def to_local(M, p):
    from mathutils import Vector
    v = M.inverted() @ Vector(tuple(map(float, p)))
    return np.array((v.x, v.y, v.z), F)


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

def gulpy_sale():
    import gulpy
    M = M_of((0.35, 7.6, -1.0))
    obs = gulpy.build(viewer=to_local(M, EYE))
    return place(obs, M)


def gulpy_pretende():
    import gulpy
    M = M_of((0.40, 4.05, -0.30), pitch=12.0)
    grip = [to_local(M, (-0.29, 2.45, 0.99)), to_local(M, (0.29, 2.45, 0.99))]
    obs = gulpy.build(grip=grip, viewer=to_local(M, EYE), lo=np.array((-1.0, -1.9, -0.02), F), hi=np.array((0.62, 0.48, 2.72), F))
    return place(obs, M)


def molly(side):
    import molly as mo
    y = -0.26 if side > 0 else 0.15
    xc, ztop = gunwale_at(y, side)
    M = M_of((xc, y, ztop - mo.GUN_TOP), yaw=-90.0 if side > 0 else 90.0)
    v = to_local(M, EYE)
    d = v - mo.C
    turn = max(-35.0, min(35.0, math.degrees(math.atan2(float(d[0]), float(-d[1])))))
    obs = mo.build(viewer=v, head_turn=turn)
    return place(obs, M)


def hatch_conta():
    import hatch
    M = M_of((0.35, -8.0, -1.65), yaw=180.0)
    obs = hatch.build(viewer=to_local(M, EYE))
    lights = [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith('ToyLight')]
    return place(obs + lights, M)


POSES = {
    'gulpy_sale': (gulpy_sale, 'world', False),
    'gulpy_pretende': (gulpy_pretende, 'boat', True),
    'molly_destra': (lambda: molly(+1), 'boat', False),
    'molly_sinistra': (lambda: molly(-1), 'boat', False),
    'hatch_conta': (hatch_conta, 'world', False),
}
