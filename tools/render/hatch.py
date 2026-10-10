"""
HATCH — modello definitivo (sagoma C «Spilungone», testa A «Pescatrice»), in lavorazione.

Altissimo e magrissimo, piegato in avanti. La testa è quella di una rana pescatrice: grande e tonda,
la bocca spalancata con i denti di vetro rivolti all'indietro, gli occhietti in cima e le frange di pelle
sotto la mascella. Dalla fronte gli pende l'esca: il pesciolino luminoso del negozio del parco.

Coordinate: faccia verso −Y, piedi a z = 0.

Uso (vetrina): tools/.venv/bin/python tools/render/hatch.py [--fast]
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sdf  # noqa: E402
import skin  # noqa: E402
from common import CACHE, reset_scene  # noqa: E402
from creature import eyeball, sdf_object  # noqa: E402
from dettagli import (Frame, V, above, area_light, chain, ellipsoid_rot, glow, hair_clump, mat_simple,  # noqa: E402
                      needle_teeth, point_light, torus_axis, unit)

FAST = '--fast' in sys.argv
F = np.float32

# Il colore della pelle (richiesta dell'utente del 10 ottobre: i mostri vanno distinti per colore, come gli
# animatronics; dei primi tre si comincia da Hatch). Scelto l'ARANCIO (10 ottobre); 'grigio' era quello della
# prima versione, 'verde' l'alternativa scartata. Per la vetrina: --colore arancio|verde|grigio.
PALETTES = {
    'grigio': dict(base=(0.165, 0.150, 0.135), dark=(0.05, 0.045, 0.04), light=(0.30, 0.28, 0.25), vein=(0.13, 0.10, 0.14),
                   slime_tint=(0.80, 0.92, 0.66)),
    # arancione zucca: contrasta con l'esca verde-acqua e non si confonde coi quattro nuovi (rosso, giallo,
    # viola, blu); più cupo e bagnato sul dorso
    'arancio': dict(base=(0.62, 0.15, 0.018), dark=(0.20, 0.040, 0.008), light=(0.88, 0.36, 0.08), vein=(0.30, 0.05, 0.02),
                    slime_tint=(0.98, 0.80, 0.58)),
    # verde annegato: alga e acqua ferma
    'verde': dict(base=(0.08, 0.33, 0.06), dark=(0.015, 0.09, 0.02), light=(0.26, 0.52, 0.12), vein=(0.04, 0.14, 0.06),
                  slime_tint=(0.80, 0.95, 0.66)),
}
COLORE = sys.argv[sys.argv.index('--colore') + 1] if '--colore' in sys.argv else 'arancio'

HEAD = Frame((0, -0.60, 2.56), pitch=12)
LURE = HEAD.pt((0, -0.345, 0.06))          # il pesciolino luminoso
VIEWER = V(-0.5, -2.6, 1.25)


# ───────────────────────── corpo ─────────────────────────

def body_field():
    torso = chain([V(0, 0.06, 1.48), V(0, 0.02, 2.02), V(0, -0.17, 2.40), V(0, -0.33, 2.55)], [0.10, 0.112, 0.112, 0.092], k=0.05)
    pelvis = sdf.ellipsoid(V(0, 0.06, 1.46), (0.13, 0.09, 0.08))
    sh = sdf.union(*[sdf.ellipsoid(V(s * 0.17, -0.21, 2.43), (0.072, 0.078, 0.062)) for s in (-1, 1)], k=0.08)
    neck = chain([V(0, -0.33, 2.55), V(0, -0.47, 2.56)], [0.064, 0.058], k=0.02)
    parts = [torso, pelvis, sh, neck]
    # gabbia toracica: archi in rilievo sul petto, sterno, clavicole
    for i in range(6):
        z = 1.86 + i * 0.075
        yc = 0.02 - 0.42 * (z - 1.86)
        w = 0.105 - 0.004 * i
        pts = [V(-w, yc + 0.05, z + 0.015), V(-w * 0.78, yc - 0.06, z), V(-0.03, yc - 0.105, z - 0.03), V(0.03, yc - 0.105, z - 0.03), V(w * 0.78, yc - 0.06, z), V(w, yc + 0.05, z + 0.015)]
        parts.append(hair_clump(pts, 0.009, 0.0085))
    parts.append(chain([V(0, -0.085, 1.92), V(0, -0.27, 2.33)], [0.012, 0.015], k=0.01))
    for s_ in (-1, 1):
        parts.append(sdf.capsule(V(s_ * 0.02, -0.28, 2.36), V(s_ * 0.17, -0.22, 2.44), 0.013))
    for s in (-1, 1):
        hip, knee, ankle = V(s * 0.085, 0.07, 1.42), V(s * 0.10, -0.02, 0.78), V(s * 0.09, 0.07, 0.08)
        parts.append(chain([hip, hip + (knee - hip) * 0.35, knee], [0.05, 0.052, 0.034], k=0.02))           # coscia
        parts.append(chain([knee, knee + (ankle - knee) * 0.3, ankle], [0.034, 0.036, 0.022], k=0.02))     # polpaccio
        parts.append(sdf.ellipsoid(knee + V(0, -0.012, 0), (0.042, 0.04, 0.045)))   # ginocchio nodoso
        for dx in (-0.025, 0.0, 0.025):
            toe = ankle + V(dx * 1.6, -0.17, -0.06)
            parts.append(hair_clump([ankle, (ankle + toe) / 2 + V(0, 0, 0.015), toe], 0.016, 0.006))
        sh_p, el, wr = V(s * 0.18, -0.22, 2.41), V(s * 0.23, -0.36, 1.92), V(s * 0.21, -0.47, 1.45)
        parts.append(chain([sh_p, el], [0.040, 0.027], k=0.015))
        parts.append(chain([el, wr], [0.027, 0.020], k=0.015))
        parts.append(sdf.sphere(el, 0.031))
        parts.append(sdf.sphere(wr + V(0, 0.005, 0.005), 0.019))
        for dx, L in ((-0.03, 0.85), (-0.01, 1.0), (0.01, 0.97), (0.03, 0.8)):
            k1 = wr + V(dx, -0.025, -0.10 * L)
            k2 = k1 + V(dx * 0.5, -0.02, -0.12 * L)
            k3 = k2 + V(dx * 0.2, 0.01, -0.08 * L)
            parts.append(hair_clump([wr, k1, k2, k3], 0.0145, 0.006))
            parts.append(sdf.sphere(k1, 0.0128))
            parts.append(sdf.sphere(k2, 0.0098))
    body = sdf.union(*parts, k=0.03)
    body = sdf.displace(body, skin.bumps(81, 0.04, 0.003), 1.0)
    body = sdf.displace(body, skin.bumps(82, 0.01, 0.0009), 1.0)
    return body


# ───────────────────────── testa (sistema locale) ─────────────────────────

def head_local():
    head = sdf.union(sdf.ellipsoid(V(0, 0, 0), (0.17, 0.165, 0.125)), sdf.ellipsoid(V(0, -0.055, -0.078), (0.162, 0.148, 0.072)), k=0.04)
    sockets = sdf.union(*[sdf.sphere(V(s * 0.075, -0.098, 0.080), 0.019) for s in (-1, 1)])
    head = sdf.union(head, sockets, k=0.015)
    # frange di pelle sotto la mascella e sui fianchi della testa
    fr = []
    rng = np.random.default_rng(31)
    for i in range(22):
        a = -1.25 + 2.5 * i / 21 + rng.uniform(-0.03, 0.03)
        base = V(0.152 * math.sin(a), -0.055 - 0.135 * math.cos(a), -0.128)
        L = rng.uniform(0.008, 0.02)
        fr.append(ellipsoid_rot(base + V(0, 0, -L * 0.7), (0.0055 + 0.003 * rng.random(), 0.0022, L), sdf.rot_matrix('z', -math.degrees(a))))
    head = sdf.union(head, *fr, k=0.008)
    mouth = sdf.ellipsoid(V(0, -0.15, -0.032), (0.14, 0.11, 0.05))
    gills = sdf.union(*[ellipsoid_rot(V(s * 0.155, 0.06, -0.05 + 0.02 * i), (0.006, 0.02, 0.008), np.eye(3, dtype=F)) for s in (-1, 1) for i in range(2)])
    head = sdf.subtract(head, sdf.union(mouth, gills, *[sdf.sphere(V(s * 0.075, -0.104, 0.085), 0.0128) for s in (-1, 1)]), k=0.005)
    # palpebre pesanti: gli occhietti restano a fessura
    for s in (-1, 1):
        e = V(s * 0.075, -0.104, 0.085)
        shell = sdf.subtract(sdf.sphere(e, 0.019), sdf.sphere(e, 0.0126))
        head = sdf.union(head, sdf.intersect(shell, above(e + V(0, 0, 0.002), (0, 0.25, 1)), k=0.002), k=0.003)
    head = sdf.displace(head, sdf.warts(3, (0, 0, 0), (0.18, 0.18, 0.14), 110, 0.022), 0.008)
    head = sdf.displace(head, skin.bumps(84, 0.008, 0.0009), 1.0)
    head = sdf.displace(head, skin.wrinkles(85, 0.012, 0.0013, center=V(0, -0.14, -0.03), radius=0.17, direction=(1, 0, 0)), 1.0)
    return head


def head_attrs():
    R, c = HEAD.R, HEAD.pos

    def mouth(p):
        q = (p - c) @ R
        inner = np.clip(1.0 - np.linalg.norm((q - V(0, -0.10, -0.032)) / V(0.14, 0.11, 0.05), axis=1), 0, 1)
        return np.clip(inner * 2.5, 0, 1)

    def slime(p):
        q = (p - c) @ R
        return np.clip(1.0 - np.linalg.norm((q - V(0, -0.15, -0.032)) / V(0.17, 0.10, 0.08), axis=1), 0, 1)

    def scar(p):
        return np.zeros(len(p), F)

    return {'mouth': mouth, 'slime': slime, 'scar': scar}


def teeth():
    """Due file di denti di vetro, lunghi e storti, piegati verso l'interno della bocca."""
    rng = np.random.default_rng(12)
    out = []
    for row, (zu, zl, Ls, rad) in enumerate(((0.012, -0.076, (0.04, 0.075), 0.0062), (0.0, -0.064, (0.022, 0.04), 0.0045))):
        for i in range(15 - 4 * row):
            t = (i / (14 - 4 * row)) - 0.5
            x = t * (0.25 - 0.05 * row)
            yu = -0.165 * math.sqrt(max(0.05, 1 - (x / 0.17) ** 2 - (zu / 0.125) ** 2)) + 0.012 + 0.02 * row
            L = rng.uniform(*Ls)
            b = V(x, yu, zu)
            out.append(hair_clump([HEAD.pt(b), HEAD.pt(b + V(x * 0.03, 0.004, -L * 0.55)), HEAD.pt(b + V(x * 0.06, 0.03, -L))], rad, 0.0007))
            yl = -0.055 - 0.148 * math.sqrt(max(0.05, 1 - (x / 0.162) ** 2 - ((zl + 0.078) / 0.072) ** 2)) + 0.012 + 0.02 * row
            L2 = rng.uniform(*Ls) * 1.15
            b = V(x, yl, zl)
            out.append(hair_clump([HEAD.pt(b), HEAD.pt(b + V(x * 0.03, -0.004, L2 * 0.55)), HEAD.pt(b + V(x * 0.06, 0.03, L2))], rad * 1.1, 0.0008))
    return sdf.union(*out)


def lure():
    """Il peduncolo che esce dalla fronte e il pesciolino di plastica col portachiavi."""
    pts = [HEAD.pt(q) for q in ((0, -0.07, 0.115), (0, -0.10, 0.25), (0, -0.20, 0.33), (0, -0.30, 0.30), (0, -0.345, 0.20), (0, -0.345, 0.135))]
    stalk = hair_clump(pts, 0.0085, 0.0028)
    p = LURE
    body = sdf.union(sdf.ellipsoid(p, (0.022, 0.015, 0.034)), sdf.round_cone(p + V(0, 0, 0.026), p + V(0, 0, 0.050), 0.010, 0.020), k=0.008)
    tail = sdf.intersect(sdf.ellipsoid(p + V(0, 0, 0.058), (0.004, 0.022, 0.016)), above(p + V(0, 0, 0.048), (0, 0, 1)))
    fins = sdf.union(*[ellipsoid_rot(p + V(s * 0.016, 0.002, 0.004), (0.003, 0.012, 0.009), sdf.rot_matrix('y', s * 25)) for s in (-1, 1)])
    seam = sdf.intersect(sdf.shell(sdf.ellipsoid(p, (0.0225, 0.0155, 0.0345)), 0.0007), above(p, (1, 0, 0)), k=0.0)
    toy = sdf.union(body, tail, fins, k=0.004)
    ring = torus_axis(p + V(0, 0, 0.064), (1, 0, 0), 0.008, 0.0017)
    eyes = sdf.union(*[sdf.sphere(p + V(s * 0.0165, -0.005, -0.012), 0.0045) for s in (-1, 1)])
    return stalk, toy, seam, ring, eyes


def slime_bits():
    """Melma vera: bava tra i denti di sopra e di sotto, gocce dalle frange della mascella e dal pesciolino."""
    rng = np.random.default_rng(29)
    parts = []
    for x, sag in ((-0.09, 0.012), (-0.045, 0.02), (0.0, 0.03), (0.05, 0.018), (0.095, 0.01)):
        yu = -0.165 * math.sqrt(max(0.05, 1 - (x / 0.17) ** 2)) + 0.02
        parts.append(skin.strand(HEAD.pt((x, yu, 0.0)), HEAD.pt((x * 0.95, yu - 0.01, -0.07)), sag, 0.0015))
    for i in range(6):
        a = -1.0 + 2.0 * i / 5
        base = V(0.152 * math.sin(a), -0.055 - 0.135 * math.cos(a), -0.15)
        parts.append(skin.drip(HEAD.pt(base), rng.uniform(0.015, 0.05), 0.0022, 0.0042))
    parts.append(skin.drip(LURE + V(0, 0, -0.034), 0.018, 0.0016, 0.003))
    pts = np.array([HEAD.pt(q) for q in ((-0.2, -0.25, -0.25), (0.2, 0.05, 0.05))] + [LURE], F)
    return [('HatchSlime', sdf.union(*parts), pts.min(0) - 0.07, pts.max(0) + 0.05)]


# ───────────────────────── costruzione ─────────────────────────

def build(viewer=None):
    """viewer: dove guardano gli occhi (coordinate locali)."""
    vw = VIEWER if viewer is None else V(*viewer)
    rb = 0.008 if FAST else 0.004
    rh = 0.0028 if FAST else 0.0013
    obs = []
    pal = PALETTES[COLORE]
    sk = skin.creature_skin(f'HatchSkin_{COLORE}', base=pal['base'], dark=pal['dark'], light=pal['light'], vein=pal['vein'],
                            rough=0.66, sss=0.08, scale=1.1, slime_tint=pal['slime_tint'])
    head_w = HEAD.field(head_local())
    full = sdf.union(body_field(), head_w, k=0.03)
    # cucitura nel collo, dietro la testa
    cut_c = V(0, -0.47, 2.56)
    plane_body = above(cut_c, (0, 1, 0))
    plane_head = above(cut_c + V(0, 0.01, 0), (0, -1, 0))
    body = sdf_object('HatchBody', sdf.intersect(full, plane_body), V(-0.42, -0.55, -0.02), V(0.42, 0.25, 2.72), res=rb, banded=True)
    body.data.materials.append(sk)
    head = sdf_object('HatchHead', sdf.intersect(full, plane_head), V(-0.24, -0.86, 2.30), V(0.24, -0.45, 2.80), res=rh,
                      attrs=head_attrs(), banded=True)
    head.data.materials.append(sk)
    obs += [body, head]
    for s in (-1, 1):
        e = HEAD.pt((s * 0.075, -0.104, 0.085))
        obs.append(eyeball(f'HatchEye{s}', tuple(map(float, e)), 0.012, skin.cloudy_eye(), look=tuple(map(float, unit(vw - e)))))
    te = sdf_object('HatchTeeth', teeth(), HEAD.pos - 0.3, HEAD.pos + 0.3, res=0.0009, banded=True)
    te.data.materials.append(needle_teeth())
    obs.append(te)
    stalk, toy, seam, ring, eyes = lure()
    st = sdf_object('HatchStalk', stalk, HEAD.pos - 0.5, HEAD.pos + 0.5, res=0.0022 if FAST else 0.0012, banded=True)
    st.data.materials.append(sk)
    obs.append(st)
    p = LURE
    t = sdf_object('ToyFish', toy, p - 0.08, p + 0.1, res=0.0012)
    t.data.materials.append(glow('ToyGlow', (0.20, 0.95, 0.75), 1.4, base=(0.15, 0.75, 0.6)))
    obs.append(t)
    sm = sdf_object('ToySeam', seam, p - 0.05, p + 0.05, res=0.0006)
    sm.data.materials.append(mat_simple('ToySeamPlastic', (0.12, 0.6, 0.5), rough=0.3))
    obs.append(sm)
    rg = sdf_object('ToyRing', ring, p - 0.03 + V(0, 0, 0.06), p + 0.03 + V(0, 0, 0.06), res=0.0006)
    rg.data.materials.append(mat_simple('ToyRingMetal', (0.7, 0.7, 0.7), rough=0.25, metal=1.0))
    obs.append(rg)
    ey = sdf_object('ToyEyes', eyes, p - 0.03, p + 0.03, res=0.0006)
    ey.data.materials.append(mat_simple('ToyEyePaint', (0.02, 0.02, 0.03), rough=0.2))
    obs.append(ey)
    point_light('ToyLight', tuple(map(float, p)), 1.2, (0.30, 1.0, 0.82), radius=0.02)
    for name, fld, lo, hi in slime_bits():
        sl = sdf_object(name, fld, lo, hi, res=0.0016 if FAST else 0.0009, banded=True)
        sl.data.materials.append(skin.slime_material())
        obs.append(sl)
    return obs


# ───────────────────────── vetrina ─────────────────────────

SHOTS = {
    'insieme': ((-0.55, -2.75, 1.25), (0.0, -0.35, 1.85), 32),
    'testa': ((-0.38, -1.48, 2.22), (0.0, -0.64, 2.52), 50),
}


def showcase(shots=('insieme', 'testa')):
    from mathutils import Vector
    out = []
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Night')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.010, 0.014, 0.022, 1)
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0.0))
    deck = bpy.context.object
    deck.data.materials.append(mat_simple('DeckWood', (0.09, 0.05, 0.03), rough=0.6))
    build()
    s = np.array((0, -0.5, 2.2))
    area_light('Rim', (0.8, 1.2, 3.6), tuple(s), 160, (0.55, 0.72, 1.0), 0.5)
    area_light('Key', (-0.9, -2.8, 1.5), tuple(s), 22, (1.0, 0.74, 0.46), 0.6)
    area_light('Fill', (1.3, -2.2, 2.4), tuple(s), 4, (0.55, 0.65, 0.85), 1.6)
    cam_d = bpy.data.cameras.new('Cam')
    cam_d.sensor_width = 36.0
    cam = bpy.data.objects.new('Cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    W, H = (540, 720) if FAST else (1080, 1440)
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.cycles.samples = 32 if FAST else 160
    sc.render.image_settings.file_format = 'PNG'
    os.makedirs(os.path.join(CACHE, 'vetrina'), exist_ok=True)
    for name in shots:
        cl, ct, lens = SHOTS[name]
        cam_d.lens = lens
        cam.location = cl
        cam.rotation_mode = 'QUATERNION'
        cam.rotation_quaternion = (Vector(ct) - Vector(cl)).to_track_quat('-Z', 'Y')
        path = os.path.join(CACHE, 'vetrina', f'hatch_{name}.png' if COLORE == 'grigio' else f'hatch_{name}_{COLORE}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('ok', path, flush=True)
    return out


if __name__ == '__main__':
    showcase()
