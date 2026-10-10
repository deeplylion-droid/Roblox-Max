"""
Pelle e dettagli fini delle creature (modelli definitivi).

- creature_skin(): pelle OPACA a strati (chiazze, maculatura, puntini, vene sotto pelle, cavità scure
  dall'occlusione, creste più chiare, pori e grinze in rilievo). Il bagnato è solo dove lo dice
  l'attributo 'slime' (bocca, occhi), non su tutto il corpo.
- campi di dettaglio da sommare agli SDF: grinze, pieghe ad anello, bitorzoli fitti.
"""
from __future__ import annotations

import math

import numpy as np

import sdf
from nodes import material

F = np.float32


def creature_skin(name, base, dark, light, vein=(0.10, 0.12, 0.17), mouth=(0.07, 0.012, 0.015),
                  rough=0.62, sss=0.10, scale=1.0, pores=1.0, blotch=1.0, spec=0.32, slime_amount=0.75,
                  slime_tint=(0.80, 0.92, 0.66)):
    """scale: dimensione delle macchie (1 = taglia umana). Attributi letti: mouth, blush, slime, scar.

    Sopra la pelle opaca c'è uno strato di MELMA: chiazze lucide, colature verso il basso, ristagni nelle
    pieghe e attorno a bocca e occhi (attributo 'slime'); dappertutto un velo bagnato appena accennato."""
    import bpy
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    k = 1.0 / scale
    # chiazze grandi e maculatura
    big = g.noise(co, scale=2.6 * k, detail=7.0, rough=0.58, distortion=0.35)
    col = g.mix(g.mul(g.smoothstep(0.40, 0.70, big.fac), 0.85 * blotch), base, dark)
    mid = g.noise(co, scale=15.0 * k, detail=5.0, rough=0.6, distortion=0.2)
    col = g.mix(g.mul(g.smoothstep(0.56, 0.74, mid.fac), 0.55 * blotch), col, light)
    # puntini scuri sparsi
    dots_d = g.voronoi(co, scale=70.0 * k, feature='F1', randomness=1.0)
    dots = g.mul(g.smoothstep(0.16, 0.04, dots_d), g.smoothstep(0.45, 0.6, mid.fac))
    col = g.mix(g.mul(dots, 0.6), col, dark)
    # vene sotto la pelle
    warp = g.vmath('ADD', co, g.vmath('SCALE', big.color, scale=0.06 * scale))
    vv = g.voronoi(warp, scale=6.5 * k, feature='DISTANCE_TO_EDGE')
    veins = g.mul(g.smoothstep(0.03, 0.0, vv), 0.16)
    col = g.mix(veins, col, vein)
    # cicatrici (attributo) e chiazze rosate sulle guance
    col = g.mix(g.mul(g.attr('scar'), 0.7), col, light)
    col = g.mix(g.mul(g.attr('blush'), 0.45), col, (0.42, 0.20, 0.20))
    # cavità più scure, creste più chiare
    ao = g.ao(distance=0.03 * scale, samples=8)
    col = g.mix(g.sub(1.0, ao), col, (0.28, 0.26, 0.26), blend='MULTIPLY')
    ridge = g.smoothstep(0.53, 0.66, g.geometry('Pointiness'))
    col = g.mix(g.mul(ridge, 0.35), col, light)
    # interno della bocca
    col = g.mix(g.smoothstep(0.3, 0.7, g.attr('mouth')), col, mouth)
    # ── melma: chiazze, colature verticali, ristagni nelle cavità, bava (attributo) ──
    patch = g.noise(co, scale=4.2 * k, detail=4.0, rough=0.55, distortion=0.7)
    pm = g.smoothstep(0.50, 0.60, patch.fac)
    streak = g.noise(g.mapping(co, scale=(28.0 * k, 28.0 * k, 2.6 * k)), scale=1.0, detail=3.0, rough=0.5, distortion=0.3)
    dm = g.mul(g.smoothstep(0.56, 0.68, streak.fac), 0.9)
    cm = g.mul(g.smoothstep(0.25, 0.55, g.sub(1.0, ao)), 0.8)
    sl = g.mx(g.mx(pm, dm), g.mx(cm, g.smoothstep(0.15, 0.7, g.attr('slime'))))
    sl = g.clamp01(g.mul(sl, slime_amount * 1.15))
    # sotto la melma il colore è più cupo e saturo, con un velo verdastro
    col = g.mix(g.mul(sl, 0.7), col, (slime_tint[0] * 0.75, slime_tint[1] * 0.75, slime_tint[2] * 0.7), blend='MULTIPLY')
    # rugosità: pelle opaca, bagnata appena; lucidissima dove c'è melma
    r = g.add(rough, g.mul(g.sub(mid.fac, 0.5), 0.22))
    r = g.mixf(sl, r, 0.22)
    # rilievo della pelle: pori + grana media + vene
    pore = g.noise(co, scale=380.0 * k, detail=2.0, rough=0.5)
    grain = g.noise(co, scale=55.0 * k, detail=4.0, rough=0.6)
    h = g.add(g.mul(pore.fac, 0.45 * pores), g.mul(grain.fac, 0.55))
    h = g.add(h, g.mul(veins, 0.6))
    nrm = g.bump(h, strength=0.42, distance=0.0012 * scale)
    # superficie della melma: bordi delle chiazze, bollicine, increspature
    bub = g.voronoi(co, scale=160.0 * k, feature='F1')
    bubbles = g.mul(g.smoothstep(0.22, 0.05, bub), g.smoothstep(0.55, 0.8, pm))
    ripple = g.noise(co, scale=90.0 * k, detail=2.0)
    hs = g.add(g.mul(sl, 0.8), g.add(g.mul(bubbles, 0.25), g.mul(ripple.fac, 0.08)))
    coat_n = g.bump(hs, strength=0.35, distance=0.002 * scale)
    coat = g.add(0.14, g.mul(sl, 0.86))
    bsdf = g.principled(color=col, rough=r, spec=spec, sss=sss, sss_radius=(1.0, 0.38, 0.22), sss_scale=0.012 * scale,
                        normal=nrm, coat=coat, coat_rough=g.mixf(sl, 0.16, 0.025), coat_normal=coat_n,
                        coat_tint=slime_tint)
    g.output_material(bsdf)
    return m


def slime_material(name='Slime', tint=(0.72, 0.84, 0.55)):
    """Melma vera e propria (gocce, fili, pozze): trasparente, verdognola, lucidissima."""
    import bpy
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    n = g.noise(co, scale=60.0, detail=2.0)
    g.output_material(g.principled(color=tint, rough=0.03, transmission=0.85, ior=1.36, coat=1.0, coat_rough=0.01,
                                   sss=0.25, sss_radius=(0.6, 0.8, 0.4), sss_scale=0.004,
                                   normal=g.bump(n.fac, strength=0.08, distance=0.001)))
    return m


def drip(anchor, length, r0=0.0035, r1=0.006, dir=(0, 0, -1)):
    """Goccia che pende: sottile in alto, gonfia in fondo."""
    a = np.asarray(anchor, F)
    d = np.asarray(dir, F)
    d = d / np.linalg.norm(d)
    b = a + d * length
    return sdf.union(sdf.round_cone(a, b - d * r1 * 0.6, r0, r1 * 0.8), sdf.sphere(b, r1), k=r1 * 0.6)


def strand(a, b, sag, r=0.0016, n=6):
    """Filo di bava tra due punti, che si affloscia al centro."""
    a = np.asarray(a, F)
    b = np.asarray(b, F)
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(a * (1 - t) + b * t + np.array((0, 0, -sag * 4 * t * (1 - t)), F))
    parts = []
    for i in range(n):
        t = i / n
        rr = r * (0.55 + 0.45 * abs(2 * t - 1))       # più sottile al centro
        parts.append(sdf.round_cone(pts[i], pts[i + 1], rr, r * (0.55 + 0.45 * abs(2 * (i + 1) / n - 1))))
    return sdf.union(*parts)


def strand_follow(a, b0, b1, sag, r=0.0016):
    """Un filo di bava tra a e b0 il cui capo b0 si sposta in b1 (una mascella che si muove). La bava è elastica:
    se la bocca si apre il filo si tende (la pancia cala col cubo dell'allungamento) e si assottiglia, se si chiude
    si affloscia (al massimo del 30%, e mai più di metà della distanza tra i capi, così non fa il cappio).
    Restituisce (pancia, raggio) per strand(a, b1, ...)."""
    d0 = float(np.linalg.norm(np.asarray(b0, F) - np.asarray(a, F)))
    d1 = float(np.linalg.norm(np.asarray(b1, F) - np.asarray(a, F)))
    k = d0 / max(d1, 1e-4)
    s1 = min(sag * k ** 3, sag * 1.3, max(sag, 0.5 * d1 + 0.003) if k > 1 else sag)
    return s1, r * min(1.0, math.sqrt(k))


def cloudy_eye(name='CloudyEye', sclera=(0.66, 0.64, 0.57), iris=(0.40, 0.47, 0.47), pupil_col=(0.22, 0.24, 0.25),
               iris_r=0.56, pupil=0.17):
    """Occhio lattiginoso: sclera giallastra con capillari ai bordi, iride grigio-verde torbida con le fibre,
    pupila velata dalla cataratta, cornea bagnata."""
    import bpy
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    r = g.vmath('LENGTH', g.comb(x, z, 0.0))
    front = g.smoothstep(0.1, -0.45, y)
    cloud = g.noise(co, scale=7.0, detail=6.0, rough=0.6)
    col = g.mix(g.mul(g.smoothstep(0.35, 0.75, cloud.fac), 0.35), sclera, (0.80, 0.78, 0.72))
    # capillari solo verso i bordi
    vv = g.voronoi(co, scale=8.0, feature='DISTANCE_TO_EDGE')
    caps = g.mul(g.smoothstep(0.010, 0.0, vv), g.smoothstep(0.62, 0.97, r))
    col = g.mix(g.mul(caps, 0.55), col, (0.48, 0.09, 0.08))
    # iride: fibre radiali, anello scuro al bordo
    ang = g.math('ARCTAN2', z, x)
    fib = g.noise(g.comb(g.mul(ang, 6.0), g.mul(r, 8.0), 0.0), scale=2.5, detail=5.0, rough=0.65)
    ir = g.mix(g.smoothstep(0.3, 0.75, fib.fac), (iris[0] * 0.7, iris[1] * 0.7, iris[2] * 0.7), iris)
    ir = g.mix(g.smoothstep(iris_r - 0.12, iris_r, r), ir, (0.16, 0.18, 0.18))
    iris_m = g.mul(g.smoothstep(iris_r + 0.02, iris_r - 0.02, r), front)
    col = g.mix(iris_m, col, ir)
    pupil_m = g.mul(g.smoothstep(pupil + 0.03, pupil - 0.02, r), front)
    col = g.mix(pupil_m, col, pupil_col)
    # velo della cataratta sopra a tutto
    col = g.mix(g.mul(g.mul(front, g.smoothstep(0.3, 0.8, cloud.fac)), 0.35), col, (0.75, 0.77, 0.75))
    g.output_material(g.principled(color=col, rough=0.35, coat=1.0, coat_rough=0.03, spec=0.5, sss=0.15,
                                   sss_radius=(1, 0.6, 0.5), sss_scale=0.004))
    return m


# ───────────────────────── dettagli geometrici (da sommare agli SDF) ─────────────────────────

def ring_folds(center, axis, radius, width, freq=3, amp=0.002):
    """Pieghe ad anello attorno a un asse (nocche, collo stretto dal salvagente)."""
    c = np.asarray(center, F)
    n = np.asarray(axis, F)
    n = n / np.linalg.norm(n)

    def f(p):
        q = p - c
        h = q @ n
        rad = np.linalg.norm(q - h[:, None] * n, axis=1)
        mask = np.clip(1 - np.abs(h) / width, 0, 1) * np.clip(1 - np.abs(rad - radius) / (radius * 0.8), 0, 1)
        return (amp * np.sin(h / width * np.pi * freq) * mask).astype(F)
    return f


def wrinkles(seed, scale, amp, center=None, radius=None, direction=(0, 0, 1)):
    """Grinze irregolari: creste sottili da rumore 'ridged', allungate lungo 'direction'."""
    n3 = sdf.Noise3(seed)
    d = np.asarray(direction, F)
    d = d / np.linalg.norm(d)
    c = None if center is None else np.asarray(center, F)

    def f(p):
        q = p - (d[None, :] * (p @ d)[:, None]) * 0.65     # schiaccia lungo la direzione: grinze allungate
        v = 1.0 - np.abs(n3(q, scale=scale, octaves=2))
        v = v ** 6
        if c is not None:
            v = v * np.clip(1.0 - np.linalg.norm(p - c, axis=1) / radius, 0.0, 1.0)
        return (amp * v).astype(F)
    return f


def bumps(seed, scale, amp, octaves=2):
    n3 = sdf.Noise3(seed)
    return lambda p: (amp * n3(p, scale=scale, octaves=octaves)).astype(F)
