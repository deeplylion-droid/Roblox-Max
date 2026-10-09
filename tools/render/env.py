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
    faces = []
    idx = lambda i, j: i * nt + (j % nt)
    for i in range(nr - 1):
        for j in range(nt):
            faces.append((idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)))
    # tappo centrale
    center = len(verts)
    verts = np.vstack([verts, [[0, 0, 0]]])
    for j in range(nt):
        faces.append((center, idx(0, j + 1), idx(0, j)))
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
    wig = 0.035 * value_noise_1d(yaw * 6.0, 11, 4) * (1 - 0.8 * park_factor(yaw))
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
    cliff = ch * (1 - np.exp(-sp / 16.0)) + 3.0 * value_noise_1d(yaw * 9.0, 23, 2) * np.clip(sp / 20.0, 0, 1)
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
    Z += np.where((S > -1) & (S < 30), 2.5 * value_noise_2d(X, Y, 51, 7.0, 3), 0.0)
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
    steep = g.smoothstep(0.82, 0.55, nz)              # pareti di scogliera
    n = g.noise(co, scale=0.02, detail=6.0, rough=0.6)
    veg = g.ramp(n.fac, [(0.3, (0.020, 0.026, 0.016)), (0.7, (0.045, 0.050, 0.030))])
    rock_n = g.noise(co, scale=0.15, detail=5.0, rough=0.65)
    strata, _ = g.wave(co, scale=0.035, kind='BANDS', axis='Z', distortion=6.0, detail=4.0)
    rock = g.ramp(g.add(g.mul(rock_n.fac, 0.6), g.mul(g.bw(strata), 0.4)), [(0.25, (0.07, 0.068, 0.06)), (0.75, (0.20, 0.185, 0.16))])
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


def house_material(name, wall):
    m, g = material(name)
    co = g.texcoord('Object')
    # finestre: celle regolari su pareti verticali
    x, y, z = g.sep(co)
    nrm = g.geometry('Normal')
    nx, ny, nz = g.sep(nrm)
    horiz = g.smoothstep(0.5, 0.2, g.math('ABSOLUTE', nz))
    u = g.add(x, y)
    cu = g.math('FRACT', g.div(u, 3.1))
    cz = g.math('FRACT', g.div(z, 3.3))
    win = g.mul(g.mul(g.smoothstep(0.30, 0.34, cu), g.smoothstep(0.70, 0.66, cu)),
                g.mul(g.smoothstep(0.35, 0.40, cz), g.smoothstep(0.85, 0.80, cz)))
    win = g.mul(win, horiz)
    cell = g.comb(g.math('FLOOR', g.div(u, 3.1)), g.math('FLOOR', g.div(z, 3.3)), 0.0)
    rnd = g.noise(cell, scale=7.31, detail=0.0).fac
    lit = g.smoothstep(0.70, 0.72, rnd)
    walln = g.noise(co, scale=0.5, detail=3.0).fac
    wallc = g.mix(g.mul(walln, 0.35), wall, g.comb(wall[0] * 0.6, wall[1] * 0.6, wall[2] * 0.6))
    glass = (0.01, 0.012, 0.015)
    col = g.mix(win, wallc, glass)
    em_s = g.mul(g.mul(win, lit), 7.0)
    warm = g.mix(g.noise(cell, scale=3.1, detail=0.0).fac, (1.0, 0.62, 0.28), (1.0, 0.80, 0.50))
    bsdf = g.principled(color=col, rough=0.85, emission=warm, emission_strength=em_s)
    g.output_material(bsdf)
    return m


def build_village():
    r = rng(7)
    pastel = [(0.62, 0.55, 0.42), (0.58, 0.44, 0.36), (0.66, 0.62, 0.55), (0.55, 0.50, 0.40), (0.60, 0.40, 0.33), (0.50, 0.52, 0.48)]
    mats = [house_material(f'House{i}', c) for i, c in enumerate(pastel)]
    houses = []
    for i in range(78):
        yaw = VILLAGE_YAW + r.normal(0, 4.2)
        s = abs(r.normal(85, 70)) + 18
        x, y, z = surface_at(yaw, s)
        w, d, h = r.uniform(6, 12), r.uniform(6, 11), r.uniform(6, 15)
        face = math.atan2(-x, -y)     # guarda verso la baia
        ob = box(f'House{i}', (w, d, h), (x, y, z + h / 2 - 1.5), rot_z=-face + r.normal(0, 0.15))
        ob.data.materials.append(mats[i % len(mats)])
        set_lightgroup(ob, 'ambient')
        houses.append(ob)
    # chiesa con campanile e cupola maiolicata
    x, y, z = surface_at(VILLAGE_YAW - 2.0, 34)
    face = math.atan2(-x, -y)
    church = box('Church', (13, 24, 15), (x, y, z + 6), rot_z=-face)
    church.data.materials.append(house_material('ChurchWall', (0.70, 0.66, 0.58)))
    set_lightgroup(church, 'ambient')
    tx, ty, tz = surface_at(VILLAGE_YAW + 1.6, 30)
    tower_h = 34.0
    tower = box('BellTower', (5.2, 5.2, tower_h - 7), (tx, ty, tz + (tower_h - 7) / 2 - 1), rot_z=-face)
    tower.data.materials.append(house_material('TowerWall', (0.68, 0.64, 0.56)))
    set_lightgroup(tower, 'ambient')
    # cella campanaria: 4 pilastri + tetto
    pillar_mat = tower.data.materials[0]
    for sx in (-1, 1):
        for sy in (-1, 1):
            off = np.array([sx * 2.2, sy * 2.2])
            c, s_ = math.cos(-face), math.sin(-face)
            ox, oy = off[0] * c - off[1] * s_, off[0] * s_ + off[1] * c
            p = box('Belfry', (0.8, 0.8, 5.0), (tx + ox, ty + oy, tz + tower_h - 8 + 2.5 + 1), rot_z=-face)
            p.data.materials.append(pillar_mat)
            set_lightgroup(p, 'ambient')
    cap = box('BelfryCap', (5.6, 5.6, 0.9), (tx, ty, tz + tower_h - 2.5), rot_z=-face)
    cap.data.materials.append(pillar_mat)
    set_lightgroup(cap, 'ambient')
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=4.0, depth=4.5, location=(tx, ty, tz + tower_h + 0.2), rotation=(0, 0, -face + math.pi / 4))
    roof = link(bpy.context.object, 'env')
    roof.data.materials.append(house_material('TowerRoof', (0.35, 0.22, 0.18)))
    set_lightgroup(roof, 'ambient')
    # campana appesa (emissiva debole: c'è un lume nella cella)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1.0, radius2=0.45, depth=1.4, location=(tx, ty, tz + tower_h - 4.6))
    bell = link(bpy.context.object, 'env')
    m, g = material('BellBronze')
    g.output_material(g.principled(color=(0.45, 0.32, 0.12), metal=1.0, rough=0.35))
    bell.data.materials.append(m)
    set_lightgroup(bell, 'ambient')
    lume = bpy.data.lights.new('BelfryLamp', 'POINT')
    lume.energy = 9000
    lume.color = (1.0, 0.62, 0.30)
    lume.shadow_soft_size = 0.3
    lob = bpy.data.objects.new('BelfryLamp', lume)
    collection('env').objects.link(lob)
    lob.location = (tx, ty, tz + tower_h - 3.0)
    set_lightgroup(lob, 'ambient')
    # cupola
    cx, cy, cz = surface_at(VILLAGE_YAW - 2.0, 44)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=4.2, location=(cx, cy, cz + 14), segments=32, ring_count=16)
    dome = link(bpy.context.object, 'env')
    bpy.ops.object.shade_smooth()
    m, g = material('Majolica')
    co = g.texcoord('Object')
    stripes, _ = g.wave(co, scale=1.2, kind='BANDS', axis='Z', profile='SIN')
    col = g.mix(g.smoothstep(0.4, 0.6, g.bw(stripes)), (0.70, 0.55, 0.10), (0.10, 0.38, 0.30))
    g.output_material(g.principled(color=col, rough=0.25, coat=0.6))
    dome.data.materials.append(m)
    set_lightgroup(dome, 'ambient')
    # lampioni lungo la strada a tornanti (solo emissivi)
    lamp_m, g = material('StreetLamp')
    g.output_material(g.emission((1.0, 0.55, 0.18), 40.0))
    for i in range(26):
        t = i / 25.0
        yaw = VILLAGE_YAW + 9 * math.sin(t * 9.0) + r.normal(0, 0.6)
        s = 8 + t * 260
        x, y, z = surface_at(yaw, s)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, location=(x, y, z + 4.5), segments=8, ring_count=6)
        lo = link(bpy.context.object, 'env')
        lo.data.materials.append(lamp_m)
        set_lightgroup(lo, 'ambient')
    # molo con fanale rosso
    mx, my, _ = surface_at(VILLAGE_YAW + 6, -10)
    ang = math.atan2(mx, my)
    for k in range(6):
        px, py = mx - math.sin(ang) * k * 9, my - math.cos(ang) * k * 9
        b = box('Pier', (8, 8, 3), (px, py, 0.6))
        b.data.materials.append(coast_material())
        set_lightgroup(b, 'ambient')
    px, py = mx - math.sin(ang) * 50, my - math.cos(ang) * 50
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7, location=(px, py, 6.0), segments=8, ring_count=6)
    red = link(bpy.context.object, 'env')
    rm, g = material('HarbourRed')
    g.output_material(g.emission((1.0, 0.08, 0.05), 160.0))
    red.data.materials.append(rm)
    set_lightgroup(red, 'ambient')
    return houses


def build_lighthouse():
    x, y, z = surface_at(LIGHTHOUSE_YAW, 22)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=2.4, depth=18, location=(x, y, z + 9))
    tower = link(bpy.context.object, 'env')
    m, g = material('LighthouseWall')
    co = g.texcoord('Object')
    _, _, zz = g.sep(co)
    band = g.smoothstep(0.45, 0.55, g.math('FRACT', g.div(zz, 6.0)))
    g.output_material(g.principled(color=g.mix(band, (0.72, 0.72, 0.70), (0.45, 0.06, 0.05)), rough=0.6))
    tower.data.materials.append(m)
    set_lightgroup(tower, 'ambient')
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.7, depth=2.6, location=(x, y, z + 19.4))
    lamp = link(bpy.context.object, 'env')
    lm, g = material('LighthouseLamp')
    g.output_material(g.emission((1.0, 0.92, 0.75), 60.0))
    lamp.data.materials.append(lm)
    set_lightgroup(lamp, 'ambient')
    house = box('KeeperHouse', (9, 6, 5), (x + 6, y + 3, z + 2), rot_z=0.3)
    house.data.materials.append(house_material('KeeperWall', (0.6, 0.58, 0.52)))
    set_lightgroup(house, 'ambient')
    return (x, y, z + 19.4)


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
