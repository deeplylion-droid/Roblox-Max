"""
Il telone visto da sotto: il pescatore rannicchiato sul pagliolo tra i due banchi, con la tela tirata
sopra la testa (appoggiata sul banco di prua e sulla schiena). Si vede la tela da vicino, le pieghe che
scendono ai lati fino al pagliolo e, in fondo, lo spiraglio sotto il banco di prua.

Due passi di luce:
  ambient  la luce di fuori che filtra dalla tela (lampara, luna, lanterna)
  lamp     la tela retroilluminata in modo uniforme (luce verdeazzurra del giocattolo di Hatch):
           il motore la moltiplica per un bagliore che si muove, cioè Hatch che fruga sopra il telone
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from common import link, mesh_from_arrays, set_lightgroup
from nodes import material

EYE_HIDDEN = (0.03, -0.16, 0.17)       # occhi del pescatore rannicchiato sul pagliolo (piano a z −0.09)
LOOK_AT = (0.0, 1.0, 0.33)
FLOOR_Z = -0.08


def _ridge(y):
    """Quota della tela lungo l'asse della barca (x = 0)."""
    if y < -0.40:                                   # dietro: scende oltre il banco dove sei seduto
        return 0.42 - (-0.40 - y) * 0.9
    if y < -0.02:                                   # appoggiata sulla testa e sulla schiena
        return 0.34 + 0.03 * math.sin((y + 0.40) / 0.38 * math.pi)
    if y < 0.86:                                    # campata fino al banco di prua, un po' insaccata
        s = (y + 0.02) / 0.88
        return 0.34 + (0.435 - 0.34) * s - 0.06 * 4 * s * (1 - s)
    if y < 1.10:                                    # sopra il banco di prua
        return 0.435
    return max(0.03, 0.435 - (y - 1.10) * 1.4)      # oltre il banco ricade e resta sollevata dal pagliolo


def _cross(u, y):
    """Quanto la tela resta alta allontanandosi dall'asse (1 sul colmo, 0 sul pagliolo)."""
    w0 = 0.26 + 0.05 * math.sin(y * 3.1)
    w1 = 0.72 + 0.04 * math.sin(y * 2.3 + 1.0)
    if u <= w0:
        return 1.0
    if u >= w1:
        return 0.0
    t = (u - w0) / (w1 - w0)
    return 1.0 - t * t * (3 - 2 * t)


def canvas_material():
    """Tela cerata sottile: opaca e grezza vista da sotto, lascia passare la luce dalla trama."""
    m = bpy.data.materials.get('TarpUnderside')
    if m:
        return m
    m, g = material('TarpUnderside')
    co = g.texcoord('Object')
    weave1, _ = g.wave(co, scale=260.0, kind='BANDS', axis='X', profile='SIN')
    weave2, _ = g.wave(co, scale=260.0, kind='BANDS', axis='Y', profile='SIN')
    wv = g.mul(g.bw(weave1), g.bw(weave2))
    n = g.noise(co, scale=3.0, detail=6.0, rough=0.6)
    col = g.ramp(n.fac, [(0.3, (0.075, 0.08, 0.05)), (0.75, (0.12, 0.12, 0.075))])
    # aloni d'acqua e muffa sulla faccia interna
    stains = g.smoothstep(0.58, 0.72, g.noise(co, scale=1.6, detail=5.0).fac)
    col = g.mix(g.mul(stains, 0.55), col, (0.04, 0.045, 0.03))
    nrm = g.bump(wv, strength=0.18, distance=0.0008)
    surf = g.principled(color=col, rough=0.85, sheen=0.3, sheen_tint=(0.4, 0.45, 0.3), normal=nrm)
    # quanta luce passa: di più dove la trama è rada, di meno sulle macchie
    thin = g.mul(g.add(g.mul(wv, 0.5), 0.5), g.sub(1.0, g.mul(stains, 0.6)))
    trans = g.translucent(g.mix(thin, (0.0, 0.0, 0.0), (0.55, 0.52, 0.36)), normal=nrm)
    g.output_material(g.mix_shader(0.2, surf, trans))
    return m


def build_drape(name='TarpDrape', res=0.012):
    """La tela tirata sopra il pescatore, come superficie a quota z(x, y) con le pieghe."""
    xs = np.arange(-0.95, 0.95 + 1e-6, res)
    ys = np.arange(-0.80, 1.45 + 1e-6, res)
    rr = np.random.default_rng(11)
    ph = rr.uniform(0, 2 * math.pi, 6)
    verts = []
    for y in ys:
        ridge = _ridge(float(y))
        for x in xs:
            u = abs(float(x))
            c = _cross(u, float(y))
            z = FLOOR_Z + (ridge - FLOOR_Z) * c
            # pieghe: grinze a spigolo che scendono dal colmo verso i lati (più marcate dove la tela pende)
            hang = c * (1 - c) * 4
            w1 = y * 26 + ph[0] + 1.2 * math.sin(x * 5 + ph[1])
            w2 = y * 61 + x * 7 + ph[2]
            crease = 0.014 * (1 - abs(math.sin(w1))) ** 3 - 0.006 + 0.004 * (1 - abs(math.sin(w2))) ** 4
            wave = 0.008 * math.sin(y * 9 + ph[3] + 2 * math.sin(x * 3))
            sag = 0.004 * math.sin(x * 31 + ph[4]) * math.sin(y * 17 + ph[5])
            z += (crease + wave) * (0.35 + hang) + sag
            # la tela si allarga un po' quando scende (non è un telo rigido)
            xx = float(x) * (1 + 0.06 * (1 - c))
            verts.append((xx, float(y), max(FLOOR_Z, z)))
    nx = len(xs)
    faces = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    ob = mesh_from_arrays(name, np.array(verts), faces, smooth=True, col='boat')
    ob.data.materials.append(canvas_material())
    set_lightgroup(ob, 'ambient')
    return ob


def toy_backlight():
    """Luce uniforme sopra il telone (gruppo 'lamp'): il motore la trasforma nel bagliore che fruga."""
    ld = bpy.data.lights.new('ToyBacklight', 'AREA')
    ld.shape = 'RECTANGLE'
    ld.size = 2.2
    ld.size_y = 2.6
    ld.energy = 60.0
    ld.color = (0.30, 1.0, 0.82)
    ob = bpy.data.objects.new('ToyBacklight', ld)
    ob.location = (0.0, 0.35, 1.05)
    link(ob, 'boat')
    ob.lightgroup = 'lamp'
    return ob
