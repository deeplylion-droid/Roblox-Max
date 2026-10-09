"""
Ambiente della baia di Santa Brina: cielo notturno, luna, mare, costa, paese col campanile,
faro, faraglioni. Tutto procedurale e deterministico.

Direzioni: yaw ψ in gradi misurato da +Y (avanti) verso +X (destra).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from common import (IDX_WATER, collection, link, mesh_from_arrays, set_lightgroup, set_visibility)
from geo import tube
from nodes import Graph, material, world

MOON_YAW, MOON_ELEV = 28.0, 19.0
MOON_RADIUS_DEG = 1.15       # licenza artistica: ~4 volte la luna vera
VILLAGE_YAW, VILLAGE_DIST = -38.0, 690.0
LIGHTHOUSE_YAW = 78.0


def yaw_dir(yaw_deg, elev_deg=0.0):
    p, e = math.radians(yaw_deg), math.radians(elev_deg)
    return (math.sin(p) * math.cos(e), math.cos(p) * math.cos(e), math.sin(e))


def rng(seed):
    return np.random.default_rng(seed)


# ───────────────────────── rumore numpy ─────────────────────────

def value_noise_1d(x, seed, octaves=4):
    """Rumore 1D liscio (somma di ottave interpolate con coseno), periodico su 360 per gli angoli."""
    r = rng(seed)
    out = np.zeros_like(x, dtype=float)
    amp, freq = 1.0, 1.0
    for _ in range(octaves):
        n = 64 * int(freq)
        tab = r.uniform(-1, 1, n + 1)
        tab[-1] = tab[0]
        t = (x / 360.0 % 1.0) * n
        i = np.floor(t).astype(int)
        f = t - i
        f = (1 - np.cos(f * math.pi)) / 2
        out += amp * (tab[i] * (1 - f) + tab[i + 1] * f)
        amp *= 0.5
        freq *= 2
    return out


def value_noise_2d(x, y, seed, scale, octaves=5, gain=0.5):
    """FBM 2D a valori su griglia (numpy, vettorizzato)."""
    r = rng(seed)
    perm = r.permutation(256)
    vals = r.uniform(-1, 1, 256)

    def hash2(ix, iy):
        return vals[perm[(perm[ix & 255] + iy) & 255]]

    out = np.zeros_like(x, dtype=float)
    amp, freq = 1.0, 1.0 / scale
    norm = 0.0
    for o in range(octaves):
        xs, ys = x * freq + o * 17.3, y * freq + o * 9.1
        ix, iy = np.floor(xs).astype(np.int64), np.floor(ys).astype(np.int64)
        fx, fy = xs - ix, ys - iy
        fx = fx * fx * (3 - 2 * fx)
        fy = fy * fy * (3 - 2 * fy)
        a = hash2(ix, iy)
        b = hash2(ix + 1, iy)
        c = hash2(ix, iy + 1)
        d = hash2(ix + 1, iy + 1)
        out += amp * (a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy)
        norm += amp
        amp *= gain
        freq *= 2.0
    return out / norm


# ───────────────────────── cielo ─────────────────────────

def build_sky(strength=1.0):
    w, g = world('NightSky')
    w.lightgroup = 'ambient'
    d = g.texcoord('Generated')
    dx, dy, dz = g.sep(d)
    md = yaw_dir(MOON_YAW, MOON_ELEV)
    cosang = g.vmath('DOT_PRODUCT', d, md)

    up = g.clamp01(dz)
    grad = g.pow(up, 0.42)
    zenith = (0.0016, 0.0032, 0.0085)
    horizon = (0.0105, 0.0150, 0.0230)
    sky = g.mix(grad, horizon, zenith)
    # alone della luna (tre lobi)
    c0 = g.math('MAXIMUM', cosang, 0.0)
    halo = g.add(g.add(g.mul(g.pow(c0, 900.0), 0.55), g.mul(g.pow(c0, 60.0), 0.05)), g.mul(g.pow(c0, 8.0), 0.012))
    sky = g.mix(1.0, sky, g.comb(g.mul(halo, 0.55), g.mul(halo, 0.62), g.mul(halo, 0.75)), blend='ADD', clamp=False)
    # banda di foschia all'orizzonte, più chiara verso la luna
    band = g.mul(g.smoothstep(0.10, 0.0, dz), g.smoothstep(-0.03, 0.0, dz))
    toward_moon = g.add(0.35, g.mul(g.smoothstep(0.2, 1.0, cosang), 0.9))
    hb = g.mul(band, g.mul(toward_moon, 0.010))
    sky = g.mix(1.0, sky, g.comb(g.mul(hb, 0.85), g.mul(hb, 0.95), hb), blend='ADD', clamp=False)

    # stelle (voronoi 3D sulla direzione)
    vor = g.node('ShaderNodeTexVoronoi', feature='F1', voronoi_dimensions='3D')
    g.set(vor, 'Vector', d)
    g.set(vor, 'Scale', 260.0)
    g.set(vor, 'Randomness', 1.0)
    dist = g.out(vor, 'Distance')
    rnd = g.bw(g.out(vor, 'Color'))
    star = g.mul(g.smoothstep(0.075, 0.0, dist), g.smoothstep(0.82, 1.0, rnd))
    star = g.mul(star, g.add(0.6, g.mul(rnd, 6.0)))
    star = g.mul(star, g.smoothstep(0.04, 0.25, dz))
    # costellazione debole di stelle fini
    vor2 = g.node('ShaderNodeTexVoronoi', feature='F1', voronoi_dimensions='3D')
    g.set(vor2, 'Vector', d)
    g.set(vor2, 'Scale', 700.0)
    star2 = g.mul(g.smoothstep(0.06, 0.0, g.out(vor2, 'Distance')), g.smoothstep(0.7, 1.0, g.bw(g.out(vor2, 'Color'))))
    star = g.add(star, g.mul(star2, g.mul(g.smoothstep(0.05, 0.3, dz), 0.45)))

    # nuvole: proiezione su un piano alto
    inv = g.div(1.0, g.add(dz, 0.09))
    p = g.comb(g.mul(dx, inv), g.mul(dy, inv), 0.0)
    n1 = g.noise(p, scale=0.55, detail=7.0, rough=0.58, distortion=0.25)
    n2 = g.noise(p, scale=2.2, detail=4.0, rough=0.6)
    cl = g.add(n1.fac, g.mul(g.sub(n2.fac, 0.5), 0.35))
    dens = g.smoothstep(0.50, 0.68, cl)
    dens = g.mul(dens, g.smoothstep(0.015, 0.22, dz))
    dens = g.mul(dens, 0.92)
    # nuvole illuminate dalla luna (bordo argento) e un po' dal paese (arancio basso)
    lit = g.add(g.mul(g.pow(c0, 14.0), 1.0), g.mul(g.pow(c0, 3.0), 0.12))
    thin = g.sub(1.0, g.smoothstep(0.55, 0.75, cl))  # i bordi sottili si illuminano di più
    lit = g.mul(lit, g.add(0.25, thin))
    cloud_col = g.mix(1.0, g.comb(0.0042, 0.0050, 0.0068), g.comb(g.mul(lit, 0.050), g.mul(lit, 0.058), g.mul(lit, 0.068)), blend='ADD', clamp=False)

    # disco lunare
    moon_cos = math.cos(math.radians(MOON_RADIUS_DEG))
    disc = g.smoothstep(moon_cos - 0.00001, moon_cos + 0.00002, cosang)
    # mari lunari: rumore sulla direzione
    mar = g.noise(d, scale=95.0, detail=5.0, rough=0.6)
    mcol = g.ramp(mar.fac, [(0.35, (0.55, 0.56, 0.58)), (0.62, (1.0, 0.98, 0.93))])
    moon_strength = g.mul(disc, 22.0)

    base = g.mix(1.0, sky, g.comb(g.mul(star, 0.55), g.mul(star, 0.6), g.mul(star, 0.7)), blend='ADD', clamp=False)
    base = g.mix(dens, base, cloud_col, clamp=False)
    occl = g.sub(1.0, g.mul(dens, 0.82))
    ms = g.mul(moon_strength, occl)
    moon_rgb = g.mix(1.0, mcol, g.comb(ms, ms, ms), blend='MULTIPLY', clamp=False)
    final = g.mix(1.0, base, moon_rgb, blend='ADD', clamp=False)
    g.output_world(g.background(final, strength))
    # campionamento dell'ambiente: mappa abbastanza fine per la luna
    w.cycles.sampling_method = 'MANUAL'
    w.cycles.sample_map_resolution = 2048
    w.mist_settings.start = 0.0
    w.mist_settings.depth = 2500.0
    w.mist_settings.falloff = 'INVERSE_QUADRATIC'
    return w


def build_moonlight(strength=0.16):
    d = yaw_dir(MOON_YAW, MOON_ELEV)
    data = bpy.data.lights.new('Moon', 'SUN')
    data.energy = strength
    data.color = (0.70, 0.80, 1.0)
    data.angle = math.radians(MOON_RADIUS_DEG * 2)
    ob = bpy.data.objects.new('Moon', data)
    collection('env').objects.link(ob)
    # il sole punta lungo -Z locale: orientiamo -Z verso -d
    from mathutils import Vector
    ob.rotation_mode = 'QUATERNION'
    ob.rotation_quaternion = Vector((-d[0], -d[1], -d[2])).to_track_quat('-Z', 'Y')
    set_lightgroup(ob, 'ambient')
    return ob


# ───────────────────────── mare ─────────────────────────

WAVES = [  # (lunghezza d'onda m, ampiezza m, direzione gradi, fase)
    (9.0, 0.050, 12.0, 0.0),
    (6.3, 0.034, -18.0, 1.3),
    (4.1, 0.022, 35.0, 2.2),
    (3.0, 0.014, -42.0, 0.7),
    (2.2, 0.009, 70.0, 4.1),
    (14.0, 0.040, 5.0, 2.9),
]


def sea_height(x, y, t=0.0):
    z = np.zeros_like(x, dtype=float)
    for lam, amp, ang, ph in WAVES:
        k = 2 * math.pi / lam
        a = math.radians(ang)
        dirx, diry = math.sin(a), math.cos(a)
        w = math.sqrt(9.81 * k)
        z += amp * np.sin(k * (x * dirx + y * diry) - w * t + ph)
    return z


def build_sea(boat_calm_radius=3.2):
    """Mare a griglia polare centrata sulla barca (fitta vicino, rada lontano)."""
    nr, nt = 230, 900
    r0, r1 = 0.15, 26000.0
    rs = r0 * (r1 / r0) ** (np.arange(nr) / (nr - 1))
    th = np.linspace(0, 2 * math.pi, nt, endpoint=False)
    R, T = np.meshgrid(rs, th, indexing='ij')
    X = R * np.sin(T)
    Y = R * np.cos(T)
    Z = sea_height(X, Y)
    # attenuazione: calmo vicino alla barca (non deve entrare nello scafo), piatto lontano
    rb = np.hypot(X / 1.25, Y / 3.0)
    near = np.clip((rb - 1.0) / (boat_calm_radius - 1.0), 0.0, 1.0)
    near = 0.15 + 0.85 * near * near * (3 - 2 * near)
    far = np.clip(1.0 - (R - 120.0) / 380.0, 0.0, 1.0)
    Z = Z * near * far
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    # dentro lo scafo non c'è acqua: si tolgono le facce nell'impronta della barca alla linea di galleggiamento
    t = np.clip(verts[:, 1] / 2.8, -1, 1)
    hb = np.where(t > 0, (1 - np.abs(t) ** 2.0) ** 0.62, (1 - np.abs(t) ** 2.3) ** 0.55) * 0.70
    inside = (np.abs(verts[:, 0]) < hb - 0.02) & (np.abs(verts[:, 1]) < 2.7)
    faces = []
    idx = lambda i, j: i * nt + (j % nt)
    for i in range(nr - 1):
        for j in range(nt):
            f = (idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j))
            if inside[f[0]] and inside[f[1]] and inside[f[2]] and inside[f[3]]:
                continue
            faces.append(f)
    ob = mesh_from_arrays('Sea', verts, faces, smooth=True, col='env')
    ob.pass_index = IDX_WATER
    ob.data.materials.append(water_material())
    set_lightgroup(ob, 'ambient')
    return ob


def water_material():
    m, g = material('Water')
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    dist = g.vmath('LENGTH', g.comb(x, y, 0.0))
    # micro-onde: più fini vicino, più "lisce" lontano (filtraggio naturale)
    n1 = g.noise(co, scale=0.9, detail=6.0, rough=0.62, distortion=0.4)
    n2 = g.noise(co, scale=3.6, detail=3.0, rough=0.5)
    n3 = g.noise(g.mapping(co, scale=(1.0, 0.45, 1.0)), scale=0.25, detail=3.0, rough=0.5)
    n4 = g.noise(g.mapping(co, scale=(1.0, 0.6, 1.0)), scale=13.0, detail=3.0, rough=0.5)
    n5 = g.noise(co, scale=38.0, detail=2.0, rough=0.5)
    h = g.add(g.add(n1.fac, g.mul(n2.fac, 0.35)), g.mul(n3.fac, 0.8))
    h = g.add(h, g.add(g.mul(n4.fac, 0.16), g.mul(n5.fac, 0.05)))
    fade = g.map_range(dist, 8.0, 900.0, 1.0, 0.85)
    nrm = g.bump(h, strength=g.mul(fade, 0.55), distance=0.08)
    rough = g.map_range(dist, 5.0, 2500.0, 0.045, 0.10)
    base = (0.0035, 0.0085, 0.0105)
    bsdf = g.principled(color=base, rough=rough, ior=1.333, spec=0.55, normal=nrm, coat=0.0)
    g.output_material(bsdf)
    return m


def build_lamp_glow(center=(0.0, 3.85), radius=5.0):
    """Bagliore smeraldo sotto la superficie attorno alla lampara (light group 'lamp')."""
    n = 96
    ring = 30
    verts, faces = [], []
    for i in range(ring + 1):
        r = radius * (i / ring) ** 1.4
        for j in range(n):
            a = 2 * math.pi * j / n
            x, y = center[0] + r * math.sin(a), center[1] + r * math.cos(a)
            verts.append((x, y, 0.0))
    for i in range(ring):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            c, d = (i + 1) * n + (j + 1) % n, (i + 1) * n + j
            faces.append((a, b, c, d))
    V = np.array(verts)
    rb = np.hypot(V[:, 0] / 1.25, V[:, 1] / 3.0)
    near = np.clip((rb - 1.0) / (3.2 - 1.0), 0, 1)
    near = 0.15 + 0.85 * near * near * (3 - 2 * near)
    V[:, 2] = sea_height(V[:, 0], V[:, 1]) * near + 0.004
    # niente bagliore dentro lo scafo
    t = np.clip(V[:, 1] / 2.8, -1, 1)
    inside = (np.abs(V[:, 0]) < (1 - t ** 2) ** 0.6 * 1.05 + 0.04) & (np.abs(V[:, 1]) < 2.9)
    faces = [f for f in faces if not all(inside[list(f)])]
    ob = mesh_from_arrays('LampGlow', V, faces, smooth=True, col='env')
    m, g = material('LampGlow')
    co = g.texcoord('Object')
    x, y, _ = g.sep(co)
    dx, dy = g.sub(x, center[0]), g.sub(y, center[1])
    d2 = g.add(g.mul(dx, dx), g.mul(dy, dy))
    fall = g.math('EXPONENT', g.mul(d2, -1.0 / (1.7 ** 2)))
    # caustiche finte: voronoi a bordi
    vor = g.voronoi(g.mapping(co, scale=(1, 1, 1)), scale=1.6, feature='SMOOTH_F1', out='Distance')
    caus = g.add(0.55, g.mul(g.smoothstep(0.35, 0.0, vor), 0.9))
    s = g.mul(g.mul(fall, caus), 0.22)
    em = g.emission((0.12, 0.85, 0.55), 1.0)
    shader = g.mix_shader(g.clamp01(s), g.transparent(), g.add_shader(g.transparent(), em))
    # intensità: mix tra trasparente e (trasparente + emissione) pesato
    g.output_material(shader)
    ob.data.materials.append(m)
    set_lightgroup(ob, 'lamp')
    set_visibility(ob, camera=True, shadow=False, diffuse=False, glossy=False, transmission=False, scatter=False)
    ob.pass_index = IDX_WATER
    return ob


# ───────────────────────── costa ─────────────────────────

SHORE = [  # (yaw, distanza della riva): la baia è chiusa, l'imboccatura è dietro a sinistra
    (-180, 405), (-168, 412), (-158, 425), (-150, 470), (-143, 640), (-136, 1500), (-128, 4200),
    (-116, 4600), (-106, 1900), (-94, 1080), (-66, 780), (-46, 690), (-34, 660), (-16, 640), (0, 625),
    (18, 650), (40, 730), (58, 900), (70, 1060), (78, 1150), (86, 1110), (100, 1280), (114, 1040),
    (128, 760), (142, 540), (155, 450), (168, 412), (180, 405),
]
PARK_YAW = 180.0


def wrap(yaw):
    return (np.asarray(yaw, float) + 180.0) % 360.0 - 180.0


def park_factor(yaw):
    """1 sulla spiaggia di Splashland (alle spalle), 0 altrove."""
    d = np.abs(wrap(np.asarray(yaw, float) - PARK_YAW))
    return np.exp(-(d / 24.0) ** 2)


def shore_radius(yaw):
    yaw = wrap(yaw)
    ys = np.array([s[0] for s in SHORE], float)
    rs = np.array([s[1] for s in SHORE], float)
    r = np.interp(yaw, ys, np.log(rs))
    wig = 0.025 * value_noise_1d(yaw * 2.0, 11, 1) * (1 - 0.8 * park_factor(yaw))
    return np.exp(r) * (1 + wig)


def cliff_height(yaw):
    yaw = wrap(yaw)
    h = 36 + 16 * value_noise_1d(yaw * 1.0, 21, 3)
    # il paese sta su un pianoro più alto; il faro su una punta bassa
    h += 16 * np.exp(-((yaw - VILLAGE_YAW) / 10.0) ** 2)
    h -= 14 * np.exp(-((yaw - LIGHTHOUSE_YAW) / 6.0) ** 2)
    h = np.maximum(h, 8)
    # spiaggia bassa di Splashland
    pf = park_factor(yaw)
    return h * (1 - pf) + 1.6 * pf


def terrain_z(yaw, s):
    """Altezza del terreno a distanza s dalla riva (s<0 in mare)."""
    ch = cliff_height(yaw)
    sp = np.maximum(s, 0)
    cliff = ch * (1 - np.exp(-sp / 16.0)) + 0.8 * value_noise_1d(yaw * 9.0, 23, 2) * np.clip(sp / 20.0, 0, 1)
    hmax = 150 + 75 * value_noise_1d(yaw * 1.0, 31, 2)
    hills = hmax * (1 - np.exp(-np.maximum(s - 30, 0) / 650.0))
    r = shore_radius(yaw) + s
    x, y = r * np.sin(np.radians(yaw)), r * np.cos(np.radians(yaw))
    ridges = 48 * value_noise_2d(x, y, 41, 380.0, 4) + 9 * value_noise_2d(x, y, 43, 60.0, 3)
    fade = np.clip((s - 30) / 260.0, 0, 1)
    # pianoro del paese: colline più basse e dolci
    plateau = np.exp(-((yaw - VILLAGE_YAW) / 10.0) ** 2) * np.exp(-((s - 140) / 160.0) ** 2)
    z = cliff + (hills + fade * ridges) * (1 - 0.7 * plateau)
    # il parco: terreno piatto per i primi 250 m, poi colline basse
    pf = park_factor(yaw)
    flat = 1.6 + np.clip((s - 250) / 900.0, 0, 1) * 70 + np.clip((s - 250) / 900.0, 0, 1) * ridges * 0.6
    z = z * (1 - pf) + flat * pf
    z = np.where(s < 0, -2.0 + np.minimum(s, 0) * 0.8, z)
    return z


def build_coast():
    yaws = np.arange(-180.0, 180.0, 0.12)
    ss = np.concatenate([[-60.0, -20.0, -4.0, 0.0], np.cumsum(np.full(6, 2.0)), 12 + np.geomspace(1, 2200, 80)])
    YW, S = np.meshgrid(yaws, ss, indexing='ij')
    R = shore_radius(YW) + S
    X = R * np.sin(np.radians(YW))
    Y = R * np.cos(np.radians(YW))
    Z = terrain_z(YW, S)
    # rugosità della scogliera: rientranze sulla parete
    Z += np.where((S > -1) & (S < 30), 0.6 * value_noise_2d(X, Y, 51, 30.0, 2), 0.0)
    # niente terra nell'imboccatura della baia (la riva è oltre l'orizzonte)
    far = shore_radius(YW) > 3000
    Z = np.where(far, -30.0, Z)
    nY, nS = YW.shape
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    faces = []
    for i in range(nY):
        i2 = (i + 1) % nY
        for j in range(nS - 1):
            a, b = i * nS + j, i2 * nS + j
            faces.append((a, b, b + 1, a + 1))
    ob = mesh_from_arrays('Coast', verts, faces, smooth=True, col='env')
    ob.data.materials.append(coast_material())
    set_lightgroup(ob, 'ambient')
    return ob


def coast_material():
    m, g = material('Coast')
    co = g.texcoord('Object')
    nrm = g.geometry('Normal')
    _, _, nz = g.sep(nrm)
    _, _, z = g.sep(co)
    steep = g.smoothstep(0.75, 0.35, nz)              # pareti di scogliera
    n = g.noise(co, scale=0.02, detail=6.0, rough=0.6)
    veg = g.ramp(n.fac, [(0.3, (0.020, 0.026, 0.016)), (0.7, (0.045, 0.050, 0.030))])
    rock_n = g.noise(co, scale=0.15, detail=5.0, rough=0.65)
    strata, _ = g.wave(co, scale=0.035, kind='BANDS', axis='Z', distortion=6.0, detail=4.0)
    rock = g.ramp(g.add(g.mul(rock_n.fac, 0.6), g.mul(g.bw(strata), 0.4)), [(0.25, (0.06, 0.058, 0.055)), (0.75, (0.13, 0.12, 0.11))])
    col = g.mix(steep, veg, rock)
    wet = g.smoothstep(4.0, 0.0, z)                     # base scura e bagnata
    col = g.mix(wet, col, g.comb(0.03, 0.03, 0.03))
    bump = g.bump(g.noise(co, scale=0.6, detail=6.0, rough=0.7).fac, strength=0.5, distance=1.5)
    g.output_material(g.principled(color=col, rough=g.mixf(wet, 0.92, 0.35), normal=bump))
    return m


def surface_at(yaw, s):
    r = float(shore_radius(np.array([yaw]))[0]) + s
    z = float(terrain_z(np.array([yaw]), np.array([s]))[0])
    return r * math.sin(math.radians(yaw)), r * math.cos(math.radians(yaw)), z


# ───────────────────────── paese ─────────────────────────

def box(name, size, loc, rot_z=0.0, col='env'):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    ob.rotation_euler = (0, 0, rot_z)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return link(ob, col)


def house_material(name, wall, lit_ratio=0.24, tint=None):
    """Facciata 'dipinta': tinta piatta, lesene, finestre a celle; una parte accese di ambra (o di un colore)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m, g = material(name)
    co = g.texcoord('Object')
    x, y, z = g.sep(co)
    nrm = g.geometry('Normal')
    nx, ny, nz = g.sep(nrm)
    horiz = g.smoothstep(0.5, 0.2, g.math('ABSOLUTE', nz))
    u = g.add(x, y)
    cu = g.math('FRACT', g.div(u, 2.6))
    cz = g.math('FRACT', g.div(z, 3.1))
    win = g.mul(g.mul(g.smoothstep(0.30, 0.34, cu), g.smoothstep(0.66, 0.62, cu)),
                g.mul(g.smoothstep(0.30, 0.36, cz), g.smoothstep(0.88, 0.82, cz)))
    win = g.mul(win, horiz)
    cell = g.comb(g.math('FLOOR', g.div(u, 2.6)), g.math('FLOOR', g.div(z, 3.1)), 0.0)
    rnd = g.noise(cell, scale=7.31, detail=0.0).fac
    lit = g.smoothstep(0.5 + (1.0 - lit_ratio) * 0.25 - 0.01, 0.5 + (1.0 - lit_ratio) * 0.25 + 0.01, rnd)
    ao = g.ao(1.5, 6)
    wallc = g.mix(g.mul(g.sub(1.0, ao), 0.55), wall, (wall[0] * 0.2, wall[1] * 0.2, wall[2] * 0.25))
    # cornici scure in alto (fasce art déco)
    band = g.smoothstep(0.93, 0.96, g.math('FRACT', g.div(z, 6.2)))
    wallc = g.mix(g.mul(band, 0.6), wallc, (wall[0] * 0.45, wall[1] * 0.45, wall[2] * 0.5))
    glass = (0.008, 0.009, 0.012)
    col = g.mix(win, wallc, glass)
    warm = tint or (1.0, 0.58, 0.22)
    em_s = g.mul(g.mul(win, lit), 9.0)
    bsdf = g.principled(color=col, rough=0.8, emission=warm, emission_strength=em_s)
    g.output_material(bsdf)
    return m


PALETTE = [(0.55, 0.40, 0.24), (0.52, 0.26, 0.20), (0.22, 0.38, 0.36), (0.55, 0.36, 0.38), (0.60, 0.55, 0.42), (0.30, 0.30, 0.40)]


def build_village():
    """Paese alla Rubacava: case alte e strette accatastate sulla scogliera, storte, con tetti a gradoni,
    a punta o a cupola, un campanile con la guglia altissima e una gru sul molo."""
    import deco
    r = rng(7)
    mats = [house_material(f'House{i}', c) for i, c in enumerate(PALETTE)]
    neon_cols = [(1.0, 0.15, 0.20), (0.15, 0.95, 0.85), (1.0, 0.45, 0.10), (0.95, 0.25, 0.70)]
    roof_m = deco.deco_paint('RoofTerracotta', (0.30, 0.12, 0.08), grime=0.4)
    houses = []
    for i in range(95):
        yaw = VILLAGE_YAW + r.normal(0, 5.0)
        s = abs(r.normal(70, 85)) + 14
        x, y, z = surface_at(yaw, s)
        w, d = r.uniform(4.5, 8.0), r.uniform(5.5, 9.0)
        h = r.uniform(9, 20) * (1.0 + 0.4 * math.exp(-s / 120.0))
        face = math.atan2(-x, -y)
        lean = r.normal(0, 0.035)
        ob = box(f'House{i}', (w, d, h), (x, y, z + h / 2 - 2.0), rot_z=-face + r.normal(0, 0.12))
        ob.rotation_euler[1] = lean
        ob.data.materials.append(mats[i % len(mats)])
        set_lightgroup(ob, 'ambient')
        houses.append(ob)
        top = z + h - 2.0
        kind = r.random()
        if kind < 0.35:      # tetto a punta
            bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=max(w, d) * 0.72, depth=h * 0.35, location=(x, y, top + h * 0.17),
                                            rotation=(0, lean, -face + math.pi / 4))
            rf = link(bpy.context.object, 'env')
            rf.data.materials.append(roof_m)
            set_lightgroup(rf, 'ambient')
        elif kind < 0.65:    # gradone art déco
            b2 = box(f'HouseStep{i}', (w * 0.7, d * 0.7, h * 0.22), (x, y, top + h * 0.11), rot_z=-face)
            b2.rotation_euler[1] = lean
            b2.data.materials.append(mats[(i + 2) % len(mats)])
            set_lightgroup(b2, 'ambient')
        elif kind < 0.75:    # cupoletta
            bpy.ops.mesh.primitive_uv_sphere_add(radius=min(w, d) * 0.42, location=(x, y, top), segments=16, ring_count=8)
            dm = link(bpy.context.object, 'env')
            dm.scale = (1, 1, 1.3)
            dm.data.materials.append(roof_m)
            set_lightgroup(dm, 'ambient')
        # qualche insegna al neon verticale sulle case basse vicino al porto
        if s < 60 and r.random() < 0.3:
            nc = neon_cols[i % len(neon_cols)]
            rr_ = math.hypot(x, y)
            ux, uy = -x / rr_, -y / rr_
            sign = box(f'HouseNeon{i}', (0.5, 0.3, r.uniform(2.5, 4.5)), (x + ux * (d / 2 + 0.4), y + uy * (d / 2 + 0.4), z + r.uniform(3, 6)), rot_z=-face)
            sign.data.materials.append(deco.neon_material(f'VillageNeon{i % 4}', nc, 25.0))
            set_lightgroup(sign, 'ambient')
    # chiesa con il campanile dalla guglia altissima
    x, y, z = surface_at(VILLAGE_YAW - 2.5, 30)
    face = math.atan2(-x, -y)
    church = box('Church', (13, 24, 16), (x, y, z + 6), rot_z=-face)
    church.data.materials.append(house_material('ChurchWall', (0.62, 0.58, 0.48), lit_ratio=0.05))
    set_lightgroup(church, 'ambient')
    tx, ty, tz = surface_at(VILLAGE_YAW + 1.8, 26)
    tower_h = 34.0
    tw = house_material('TowerWall', (0.60, 0.55, 0.46), lit_ratio=0.0)
    obs, top = deco.stepped_tower('BellTower', (tx, ty, tz - 2), -face, (6.0, 6.0), tower_h, steps=3, shrink=0.82, mat=tw, fins=3)
    for o in obs:
        set_lightgroup(o, 'ambient')
    # cella campanaria illuminata e guglia ad ago
    lume = bpy.data.lights.new('BelfryLamp', 'POINT')
    lume.energy = 12000
    lume.color = (1.0, 0.55, 0.25)
    lume.shadow_soft_size = 0.4
    lob = bpy.data.objects.new('BelfryLamp', lume)
    collection('env').objects.link(lob)
    lob.location = (tx, ty, top - 3.0)
    set_lightgroup(lob, 'ambient')
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=2.6, depth=26.0, location=(tx, ty, top + 13.0), rotation=(0, 0, -face + math.pi / 4))
    spire = link(bpy.context.object, 'env')
    spire.data.materials.append(deco.deco_paint('SpireCopper', (0.10, 0.22, 0.20), grime=0.5))
    set_lightgroup(spire, 'ambient')
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1.1, radius2=0.5, depth=1.5, location=(tx, ty, top - 4.2))
    bell = link(bpy.context.object, 'env')
    m, g = material('BellBronze')
    g.output_material(g.principled(color=(0.45, 0.32, 0.12), metal=1.0, rough=0.35))
    bell.data.materials.append(m)
    set_lightgroup(bell, 'ambient')
    # cupola maiolicata
    cx, cy, cz = surface_at(VILLAGE_YAW - 2.5, 40)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=4.6, location=(cx, cy, cz + 15), segments=32, ring_count=16)
    dome = link(bpy.context.object, 'env')
    dome.scale = (1, 1, 1.25)
    bpy.ops.object.shade_smooth()
    m, g = material('Majolica')
    co = g.texcoord('Object')
    stripes, _ = g.wave(co, scale=1.2, kind='BANDS', axis='Z', profile='SIN')
    col = g.mix(g.smoothstep(0.4, 0.6, g.bw(stripes)), (0.70, 0.55, 0.10), (0.10, 0.38, 0.30))
    g.output_material(g.principled(color=col, rough=0.25, coat=0.6))
    dome.data.materials.append(m)
    set_lightgroup(dome, 'ambient')
    # lampioni lungo la strada a tornanti (solo emissivi)
    lamp_m = deco.neon_material('StreetLamp', (1.0, 0.55, 0.18), 45.0)
    for i in range(30):
        t = i / 29.0
        yaw = VILLAGE_YAW + 10 * math.sin(t * 9.0) + r.normal(0, 0.6)
        s = 8 + t * 280
        x, y, z = surface_at(yaw, s)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(x, y, z + 4.5), segments=8, ring_count=6)
        lo = link(bpy.context.object, 'env')
        lo.data.materials.append(lamp_m)
        set_lightgroup(lo, 'ambient')
    # molo con fanale rosso
    mx, my, _ = surface_at(VILLAGE_YAW + 6, -10)
    ang = math.atan2(mx, my)
    pier_m = deco.deco_paint('PierStone', (0.30, 0.28, 0.25), grime=0.4)
    for k in range(6):
        px, py = mx - math.sin(ang) * k * 9, my - math.cos(ang) * k * 9
        b = box('Pier', (8, 8, 3), (px, py, 0.6))
        b.data.materials.append(pier_m)
        set_lightgroup(b, 'ambient')
    px, py = mx - math.sin(ang) * 50, my - math.cos(ang) * 50
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, location=(px, py, 6.0), segments=8, ring_count=6)
    red = link(bpy.context.object, 'env')
    red.data.materials.append(deco.neon_material('HarbourRed', (1.0, 0.08, 0.05), 160.0))
    set_lightgroup(red, 'ambient')
    # gru del porto (Rubacava): torre a traliccio e braccio sull'acqua
    gx, gy, _ = surface_at(VILLAGE_YAW + 3.5, -6)
    steel = deco.deco_paint('CraneSteel', (0.42, 0.16, 0.08), grime=0.5, rough=0.5)
    H = 26.0
    for cx_, cy_ in ((-1.5, -1.5), (1.5, -1.5), (1.5, 1.5), (-1.5, 1.5)):
        t_ = tube('CraneLeg', [(gx + cx_, gy + cy_, 0.5), (gx + cx_ * 0.6, gy + cy_ * 0.6, H)], 0.18, n=6, col='env')
        t_.data.materials.append(steel)
        set_lightgroup(t_, 'ambient')
    for k in range(1, 7):
        zz = H * k / 7
        ring = [(gx - 1.4, gy - 1.4, zz), (gx + 1.4, gy - 1.4, zz), (gx + 1.4, gy + 1.4, zz), (gx - 1.4, gy + 1.4, zz), (gx - 1.4, gy - 1.4, zz)]
        t_ = tube('CraneRing', ring, 0.09, n=4, col='env', cap=False)
        t_.data.materials.append(steel)
        set_lightgroup(t_, 'ambient')
    dirx, diry = -math.sin(ang), -math.cos(ang)
    tip = (gx + dirx * 28, gy + diry * 28, H + 9)
    for off in (-0.7, 0.7):
        t_ = tube('CraneBoom', [(gx + off * diry, gy - off * dirx, H), tip], 0.22, n=6, col='env')
        t_.data.materials.append(steel)
        set_lightgroup(t_, 'ambient')
    t_ = tube('CraneCable', [tip, (tip[0], tip[1], 6.0)], 0.04, n=4, col='env')
    t_.data.materials.append(steel)
    set_lightgroup(t_, 'ambient')
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(tip[0], tip[1], tip[2] + 0.6), segments=8, ring_count=6)
    cl = link(bpy.context.object, 'env')
    cl.data.materials.append(deco.neon_material('CraneRed', (1.0, 0.05, 0.03), 120.0))
    set_lightgroup(cl, 'ambient')
    return houses


def build_lighthouse():
    """Faro art déco: torre altissima e affusolata a gradoni, scanalata, con la lanterna sfaccettata."""
    import deco
    x, y, z = surface_at(LIGHTHOUSE_YAW, 22)
    white = deco.deco_paint('LighthouseWhite', (0.70, 0.68, 0.62), grime=0.45)
    red = deco.deco_paint('LighthouseRed', (0.45, 0.06, 0.05), grime=0.4)
    obs = []
    # basamento a tre gradoni
    for k, (r_, h_) in enumerate(((6.5, 3.0), (5.0, 2.5), (3.8, 2.0))):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=r_, depth=h_, location=(x, y, z + sum(hh for _, hh in ((6.5, 3.0), (5.0, 2.5), (3.8, 2.0))[:k]) + h_ / 2))
        o = link(bpy.context.object, 'env')
        o.data.materials.append(white if k % 2 == 0 else red)
        obs.append(o)
    base_top = z + 7.5
    # fusto scanalato (lathe con 16 scanalature), alto e sottile
    H = 34.0
    prof = [(2.9, 0.0), (2.4, H * 0.5), (2.0, H)]
    n = 64
    verts, faces = [], []
    for i, (r_, hz) in enumerate(prof):
        for k in range(n):
            a = 2 * math.pi * k / n
            flute = 1.0 - 0.07 * (0.5 + 0.5 * math.cos(a * 16))
            verts.append((x + r_ * flute * math.cos(a), y + r_ * flute * math.sin(a), base_top + hz))
    for i in range(len(prof) - 1):
        for k in range(n):
            a_, b_ = i * n + k, i * n + (k + 1) % n
            faces.append((a_, b_, b_ + n, a_ + n))
    shaft = mesh_from_arrays('LighthouseShaft', np.array(verts), faces, smooth=True, col='env')
    m, g = material('LighthouseShaftPaint')
    co = g.texcoord('Object')
    _, _, zz = g.sep(co)
    band = g.smoothstep(0.48, 0.52, g.math('FRACT', g.div(g.sub(zz, base_top), 8.5)))
    g.output_material(g.principled(color=g.mix(band, (0.70, 0.68, 0.62), (0.45, 0.06, 0.05)), rough=0.6))
    shaft.data.materials.append(m)
    obs.append(shaft)
    top = base_top + H
    # ballatoio e lanterna sfaccettata con cupola a punta
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=3.0, depth=0.6, location=(x, y, top + 0.3))
    o = link(bpy.context.object, 'env')
    o.data.materials.append(red)
    obs.append(o)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=1.7, depth=3.2, location=(x, y, top + 2.2))
    lamp = link(bpy.context.object, 'env')
    lamp.data.materials.append(deco.neon_material('LighthouseLamp', (1.0, 0.90, 0.70), 70.0))
    obs.append(lamp)
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=2.2, depth=3.5, location=(x, y, top + 5.5))
    o = link(bpy.context.object, 'env')
    o.data.materials.append(red)
    obs.append(o)
    for o in obs:
        set_lightgroup(o, 'ambient')
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        sd = bpy.data.lights.new(f'LighthouseFlood{k}', 'SPOT')
        sd.energy = 60000
        sd.color = (1.0, 0.82, 0.62)
        sd.spot_size = math.radians(28)
        sd.spot_blend = 0.4
        so = bpy.data.objects.new(f'LighthouseFlood{k}', sd)
        collection('env').objects.link(so)
        so.location = (x + 9 * math.cos(a), y + 9 * math.sin(a), z + 1.0)
        from mathutils import Vector
        so.rotation_mode = 'QUATERNION'
        so.rotation_quaternion = (Vector((x, y, z + 26)) - Vector(so.location)).to_track_quat('-Z', 'Y')
        set_lightgroup(so, 'ambient')
    house = box('KeeperHouse', (9, 6, 5), (x + 7, y + 3, z + 2), rot_z=0.3)
    house.data.materials.append(house_material('KeeperWall', (0.55, 0.50, 0.42), lit_ratio=0.3))
    set_lightgroup(house, 'ambient')
    return (x, y, top + 2.2)


def build_stacks():
    """Faraglioni dietro a sinistra."""
    specs = [(-124.0, 390.0, 58.0, 17.0, 3), (-133.0, 470.0, 40.0, 13.0, 5), (-116.0, 520.0, 26.0, 10.0, 7)]
    m, g = material('Limestone')
    co = g.texcoord('Object')
    _, _, z = g.sep(co)
    n = g.noise(co, scale=0.12, detail=6.0, rough=0.65, distortion=0.3)
    bands, _ = g.wave(co, scale=0.06, kind='BANDS', axis='Z', distortion=4.0, detail=3.0)
    col = g.ramp(g.add(g.mul(n.fac, 0.7), g.mul(g.bw(bands), 0.3)), [(0.25, (0.13, 0.12, 0.10)), (0.8, (0.36, 0.33, 0.28))])
    wet = g.smoothstep(3.5, 0.0, z)
    col = g.mix(wet, col, (0.025, 0.028, 0.03))
    bump = g.bump(g.noise(co, scale=0.4, detail=6.0, rough=0.7).fac, strength=0.6, distance=1.2)
    g.output_material(g.principled(color=col, rough=g.mixf(wet, 0.9, 0.3), normal=bump))
    obs = []
    for k, (yaw, dist, h, rad, seed) in enumerate(specs):
        cx, cy = dist * math.sin(math.radians(yaw)), dist * math.cos(math.radians(yaw))
        nz, na = 60, 96
        zs = np.linspace(-6, h, nz)
        an = np.linspace(0, 2 * math.pi, na, endpoint=False)
        Zs, A = np.meshgrid(zs, an, indexing='ij')
        prof = rad * (1.0 - 0.35 * (np.clip(Zs, 0, h) / h) ** 1.6) * (1 + 0.18 * np.exp(-((Zs - h * 0.3) / (h * 0.25)) ** 2))
        noise = value_noise_2d(A * 40.0, Zs * 1.0, seed, 9.0, 4) * 0.32 + value_noise_2d(A * 90.0, Zs * 3.0, seed + 1, 6.0, 3) * 0.10
        Rr = prof * (1 + noise)
        X = cx + Rr * np.cos(A) * 1.25
        Y = cy + Rr * np.sin(A)
        top = Zs >= h - 1e-6
        Zz = Zs + np.where(top, value_noise_2d(A * 30, Zs, seed + 2, 4.0, 3) * 4.0, 0)
        verts = np.stack([X.ravel(), Y.ravel(), Zz.ravel()], axis=1)
        faces = []
        for i in range(nz - 1):
            for j in range(na):
                a = i * na + j
                b = i * na + (j + 1) % na
                faces.append((a, b, b + na, a + na))
        ctr = len(verts)
        verts = np.vstack([verts, [[cx, cy, h + 3.0]]])
        for j in range(na):
            a = (nz - 1) * na + j
            b = (nz - 1) * na + (j + 1) % na
            faces.append((a, b, ctr))
        ob = mesh_from_arrays(f'Stack{k}', verts, faces, smooth=True, col='env')
        ob.data.materials.append(m)
        set_lightgroup(ob, 'ambient')
        obs.append(ob)
    return obs


def build_environment(with_glow=True):
    build_sky()
    build_moonlight()
    sea = build_sea()
    build_coast()
    build_village()
    lh = build_lighthouse()
    build_stacks()
    glow = build_lamp_glow() if with_glow else None
    return {'sea': sea, 'lighthouse': lh, 'glow': glow}
