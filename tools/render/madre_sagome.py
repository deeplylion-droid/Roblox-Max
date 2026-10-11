"""
Sagome di studio della Madre (notte 6, il finale): solo proporzioni, da discutere prima di modellare.

Come le tavole degli altri mostri (`silhouettes.py`): tre varianti di profilo, in nero su fondo chiaro.
La Madre però è enorme: la scala la danno la barca (5,6 m, in grigio) e il pescatore alto 1,80 m in piedi
dentro. Il mare è velato, così quello che resta sotto si vede in trasparenza: dalla barca se ne vede solo
la parte sopra l'acqua, il resto è l'ombra sul sonar.
Uso: tools/.venv/bin/python tools/render/madre_sagome.py
"""
from __future__ import annotations

import math
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import sdf  # noqa: E402
from common import ROOT, mesh_from_arrays, reset_scene  # noqa: E402
from nodes import material  # noqa: E402
from silhouettes import chain, fingers, human  # noqa: E402

OUT = os.path.join(ROOT, 'docs', 'concept')

# la barca di tutte e tre le tavole: prua verso sinistra (verso la Madre), centro a BOAT_Y
BOAT_Y, BOAT_L = 6.0, 5.6


def arc(p0, p1, bulge, n=8):
    """Punti su un arco da p0 a p1 (nel piano YZ), gonfio di `bulge` metri a sinistra del verso."""
    a, b = np.array(p0, float), np.array(p1, float)
    d = b - a
    perp = np.array((0.0, -d[2], d[1])) / max(np.linalg.norm(d), 1e-6)
    return [tuple(a + d * t + perp * bulge * math.sin(math.pi * t)) for t in np.linspace(0, 1, n)]


def boat():
    """La barca di profilo: lo scafo affusolato a prua, il capodibanda a 0,75 m sull'acqua."""
    hull = sdf.ellipsoid((0, BOAT_Y, 0.05), (0.9, BOAT_L / 2, 0.75))
    cut = sdf.box((0, BOAT_Y, 1.30), (2.0, BOAT_L, 0.55))          # taglia la parte sopra il capodibanda
    palo = chain([(0, BOAT_Y - 1.9, 0.6), (0, BOAT_Y - 1.9, 2.6)], [0.05, 0.04])     # il palo della lampara
    lampara = sdf.sphere((0, BOAT_Y - 1.9, 2.65), 0.18)
    return sdf.union(sdf.subtract(hull, cut), palo, lampara, k=0.02)


def piccolo(c, s=1.0, lean=0.0, legs_up=False):
    """Uno dei «piccoli»: un bambino magro e rannicchiato, alto un metro e poco (in scala s)."""
    c = np.array(c, float)
    up = np.array((0, math.sin(lean), math.cos(lean)))
    fw = np.array((0, -math.cos(lean), math.sin(lean)))
    head = sdf.sphere(tuple(c + up * 0.55 * s), 0.16 * s)
    body = chain([tuple(c + up * 0.38 * s), tuple(c - up * 0.10 * s)], [0.11 * s, 0.09 * s])
    arm = chain([tuple(c + up * 0.32 * s), tuple(c + fw * 0.30 * s + up * 0.05 * s), tuple(c + fw * 0.42 * s - up * 0.15 * s)],
                [0.04 * s, 0.035 * s, 0.03 * s])
    knee = c + fw * (0.30 if not legs_up else 0.05) * s - up * (0.15 if not legs_up else 0.0) * s
    leg = chain([tuple(c - up * 0.10 * s), tuple(knee), tuple(knee - up * 0.35 * s + fw * 0.05 * s)], [0.05 * s, 0.045 * s, 0.035 * s])
    return sdf.union(head, body, arm, leg, k=0.04 * s)


def lashes(eye, r, n=3, length=None, side=-1.0, spread=(55, 115)):
    """Le ciglia da cartone animato di Mama Marina: tre punte arcuate sopra l'occhio."""
    out = []
    length = length or r * 0.9
    e = np.array(eye, float)
    for k in range(n):
        a = math.radians(spread[0] + (spread[1] - spread[0]) * k / max(n - 1, 1))
        d = np.array((0, side * math.cos(a), math.sin(a)))
        p0 = e + d * r * 0.92
        p1 = p0 + d * length * 0.6 + np.array((0, side * length * 0.15, 0))
        p2 = p1 + np.array((0, side * length * 0.45, length * 0.25))
        out.append(chain([tuple(p0), tuple(p1), tuple(p2)], [r * 0.10, r * 0.07, r * 0.03], k=0.05))
    return out


# ───────────────────────── LA MADRE: notte 6, immobilità totale ─────────────────────────

def madre_a():
    """'Abbraccio': la testa sale dritta accanto alla barca con la bocca spalancata sopra di te; dall'altra
    parte della barca si alza la pinna, come nell'abbraccio della statua."""
    # mascella superiore (il rostro) quasi in verticale, un po' piegata all'indietro
    up_pts = arc((0, -2.6, -1.0), (0, -1.8, 20.0), 1.2, 9)
    up_r = [3.4, 3.3, 3.1, 2.9, 2.6, 2.2, 1.8, 1.3, 0.8]
    upper = chain(up_pts, up_r)
    # mascella inferiore spalancata in fuori: la punta arriva sopra la barca
    lower = chain(arc((0, 0.6, -1.2), (0, 7.2, 8.4), -0.8, 7), [2.4, 2.2, 1.9, 1.6, 1.3, 1.0, 0.7])
    # la gola a pieghe gonfia sott'acqua, poi il corpo che scende e si allontana verso il fondo
    throat = sdf.ellipsoid((0, 0.8, -5.0), (4.0, 4.8, 5.5))
    body = chain([(0, -1.5, -4.0), (0, -6.5, -10.5), (0, -12.0, -15.5), (0, -17.0, -18.0)], [6.0, 6.2, 5.0, 3.6])
    # i fanoni: una frangia di sbarre dritte che pende dal rostro, come le sbarre di un lettino
    slats = []
    for k in range(13):
        t = 0.18 + 0.62 * k / 12
        j = t * (len(up_pts) - 1)
        i0 = min(int(j), len(up_pts) - 2)
        f = j - i0
        p = np.array(up_pts[i0]) * (1 - f) + np.array(up_pts[i0 + 1]) * f
        r = up_r[i0] * (1 - f) + up_r[i0 + 1] * f
        top = p + np.array((0, r * 0.9, 0))
        slats.append(chain([tuple(top), tuple(top + np.array((0, 2.4, -1.1)))], [0.13, 0.09], k=0.0))
    # la pinna dall'altra parte della barca: sale dall'acqua e si piega sopra la poppa, col bordo a bitorzoli
    fin_pts = arc((0, 12.4, -1.5), (0, 8.6, 10.0), -1.8, 8)
    fin = chain(fin_pts, [1.3, 1.5, 1.5, 1.4, 1.2, 1.0, 0.7, 0.35])
    knobs = [sdf.sphere(tuple(np.array(q) + np.array((0, 0.9, 0.3))), 0.45) for q in fin_pts[1:6]]
    parts = [upper, lower, throat, body, fin, *knobs]
    return sdf.union(sdf.union(*parts, k=0.6), *slats, k=0.15), 'A'


def madre_a_dettagli():
    """In bianco sulla sagoma: l'occhio con le ciglia e il sorriso dipinto che sale dall'angolo della bocca."""
    eye = (-2.7, 6.2)
    return [('ring', eye, 1.1), ('dot', (-2.45, 6.1), 0.45),
            *[('line', [(eye[0] + 1.1 * math.cos(a), eye[1] + 1.1 * math.sin(a)),
                        (eye[0] + 1.9 * math.cos(a) - 0.3, eye[1] + 1.9 * math.sin(a) + 0.4)], 5)
              for a in (math.radians(100), math.radians(130), math.radians(160))],
            ('line', [(0.3, 0.6), (-0.6, 2.4), (-2.0, 3.6), (-3.4, 3.9), (-4.2, 3.4)], 7)]


def madre_b():
    """'Occhio': resta quasi tutta sott'acqua, lunga una trentina di metri, sotto la barca; fuori sale solo
    l'occhio, grande quanto la barca, con le ciglia da cartone animato. Sotto la pinna tiene i suoi piccoli."""
    head = sdf.ellipsoid((0, -1.0, -4.0), (6.5, 7.5, 5.6))
    body = chain([(0, -4.0, -6.0), (0, -12.0, -8.5), (0, -20.0, -10.0)], [6.6, 5.8, 4.2])
    # la fronte che affiora appena, e l'occhio a pelo d'acqua: 4,4 m, quanto la barca
    brow = sdf.ellipsoid((0, -0.6, -0.2), (3.0, 3.6, 1.4))
    eye = sdf.sphere((0, 0.3, 0.6), 2.2)
    # la pinna ripiegata sul ventre, come la statua coi pesciolini in grembo; dentro, rannicchiati, i piccoli
    fin = chain(arc((0, -5.0, -9.0), (0, 5.4, -14.5), -2.6, 8), [1.3, 1.4, 1.4, 1.3, 1.2, 1.0, 0.8, 0.5])
    kids = [piccolo((0, -3.6 + 2.2 * i, -12.4 + 0.3 * (i % 2)), 2.0, lean=0.2 * (i - 1.5)) for i in range(4)]
    tail = chain([(0, -20.0, -10.0), (0, -24.0, -10.5)], [4.2, 2.2])
    parts = [head, body, brow, eye, fin, tail, *lashes((0, 0.3, 0.6), 2.2, length=3.4, side=-1.0, spread=(50, 115))]
    return sdf.union(sdf.union(*parts, k=0.8), *kids, k=0.15), 'B'


def madre_b_dettagli():
    """In bianco: l'iride e la pupilla dell'occhio grande quanto la barca, girato verso di te."""
    return [('ring', (0.9, 0.7), 1.35), ('dot', (1.3, 0.7), 0.6), ('dot', (0.9, 1.3), 0.22)]


def madre_c():
    """'Culla': non ha più niente della balena, se non la testa tonda della mascotte con la pelle dipinta;
    una figura altissima e magrissima immersa fino ai fianchi, china sulla barca come su una culla, le
    braccia che scendono ai due lati; i piccoli le stanno aggrappati alla schiena."""
    hips = (0, -6.5, -3.0)
    legs = [chain([hips, (0, -6.0 + dy, -11.0), (0, -6.8 + dy, -19.0)], [1.4, 1.0, 0.7]) for dy in (-1.0, 1.0)]
    spine = chain([hips, (0, -7.6, 4.0), (0, -7.0, 11.0), (0, -4.6, 16.5)], [1.5, 1.25, 1.4, 1.6])
    neck = chain([(0, -4.6, 16.5), (0, -1.6, 17.6), (0, 1.0, 16.0)], [0.9, 0.75, 0.7])
    # la testa della mascotte, tonda e liscia, girata in giù sulla barca; il ciuffo dello sfiatatoio in cima
    head = sdf.ellipsoid((0, 2.9, 14.8), (2.4, 2.8, 2.3))
    spout = [chain([(0, 2.0, 16.9), (0, 1.0 + 0.9 * k, 18.6 - 0.25 * abs(k - 1))], [0.22, 0.12], k=0.0) for k in range(3)]
    # braccia lunghissime: una oltre la barca, una di qua, le dita in acqua
    far = chain([(0, -4.4, 15.8), (0, 3.8, 18.4), (0, 10.4, 9.5), (0, 11.4, 0.6)], [0.75, 0.6, 0.5, 0.4])
    near = chain([(0, -5.0, 15.2), (0, -1.6, 11.0), (0, 1.3, 4.4), (0, 1.7, 0.5)], [0.75, 0.6, 0.5, 0.4])
    hands = [*fingers((0, 11.4, 0.6), (0, 0.2, -1), 2.2, r=0.15, curl=0.6),
             *fingers((0, 1.7, 0.5), (0, 0.3, -1), 2.0, r=0.15, curl=0.6)]
    # i piccoli aggrappati alla schiena, come i ragnetti sul dorso della mamma
    kids = [piccolo((0, -9.6 + 0.3 * i, 1.0 + 3.4 * i), 2.3, lean=-1.35 + 0.12 * i) for i in range(4)]
    parts = [*legs, spine, neck, head, far, near, *spout, *hands]
    return sdf.union(sdf.union(*parts, k=0.5), *kids, k=0.12), 'C'


def madre_c_dettagli():
    """In bianco: il sorriso della mascotte e l'occhio, sulla testa girata in giù."""
    return [('line', [(1.4, 14.6), (2.4, 13.4), (3.8, 13.2), (4.8, 14.0)], 6), ('ring', (3.6, 15.6), 0.6)]


VARIANTS = [
    ('A · «Abbraccio»', madre_a, madre_a_dettagli,
     'La testa sale dritta accanto alla barca e la bocca si apre sopra di te; dentro, i fanoni come le sbarre '
     'di un lettino. Dall\'altra parte della barca si alza la pinna: è l\'abbraccio della statua. Dalla barca: '
     'guardi in su e vedi il sorriso dipinto, l\'occhio con le ciglia e la gola.'),
    ('B · «Occhio»', madre_b, madre_b_dettagli,
     'Quasi tutta sott\'acqua, lunga una trentina di metri: passa sotto la barca. Fuori sale solo l\'occhio, '
     'grande quanto la barca, con le ciglia da cartone animato. Dalla barca: un occhio azzurro dipinto a un '
     'metro dal bordo che ti guarda; sotto, nel buio, la pinna stringe i suoi piccoli.'),
    ('C · «Culla»', madre_c, madre_c_dettagli,
     'Non è più una balena: è altissima e magra, immersa fino ai fianchi, china sulla barca come su una culla, '
     'le braccia ai due lati. Le resta la testa tonda della mascotte; i piccoli le stanno aggrappati alla '
     'schiena. Dalla barca: due braccia che salgono nel buio e, in alto, il sorriso.'),
]

PANEL = 32.0           # larghezza di ogni pannello, in metri
ZC = 5.5               # quota del centro dell'inquadratura
W, H = 2400, 1500


def render():
    reset_scene()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 8
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('w')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (1, 1, 1, 1)
    ink, g = material('Ink')
    g.output_material(g.emission((0.0, 0.0, 0.0), 1.0))
    grey, g = material('BoatInk')
    g.output_material(g.emission((0.62, 0.62, 0.62), 1.0))
    for i, (label, fn, _, _) in enumerate(VARIANTS):
        field, _ = fn()
        y0 = (i - 1) * PANEL
        V, F, _ = sdf.mesh(field, (-7.0, -PANEL / 2, -26.0), (7.0, PANEL / 2, 26.0), res=0.11)
        ob = mesh_from_arrays(f'Madre{i}', V + np.array((0, y0, 0), np.float32), F.tolist(), smooth=False, col='sil')
        ob.data.materials.append(ink)
        # la barca e il pescatore in piedi, davanti alla Madre (più vicini alla camera)
        bV, bF, _ = sdf.mesh(boat(), (-1.0, BOAT_Y - 3.0, -0.8), (1.0, BOAT_Y + 3.0, 2.9), res=0.03)
        b = mesh_from_arrays(f'Barca{i}', bV + np.array((8.0, y0, 0), np.float32), bF.tolist(), smooth=False, col='sil')
        b.data.materials.append(grey)
        hV, hF, _ = sdf.mesh(human(), (-0.3, -0.4, -0.05), (0.3, 0.4, 1.85), res=0.02)
        h = mesh_from_arrays(f'Pescatore{i}', hV + np.array((8.0, y0 + BOAT_Y + 1.2, 0.25), np.float32), hF.tolist(), smooth=False, col='sil')
        h.data.materials.append(grey)
    cam_d = bpy.data.cameras.new('Ortho')
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = PANEL * 3.0
    cam_d.clip_end = 200.0
    cam = bpy.data.objects.new('Ortho', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (60.0, 0.0, ZC)
    cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.film_transparent = False
    raw = os.path.join(OUT, '_madre_raw.png')
    os.makedirs(OUT, exist_ok=True)
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = raw
    bpy.ops.render.render(write_still=True)
    annotate(raw, os.path.join(OUT, 'madre_sagome.png'))
    os.remove(raw)


def annotate(src, dst):
    im = Image.open(src).convert('RGBA')
    ppm = W / (PANEL * 3.0)

    def zpx(z):
        return int(H / 2 - (z - ZC) * ppm)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
        small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 26)
        note = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 23)
    except OSError:
        font = small = note = ImageFont.load_default()
    pw = int(PANEL * ppm)
    # il mare velato: quello che resta sotto si vede in trasparenza
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for i in range(3):
        x0 = i * pw
        od.rectangle([x0 + 10, zpx(0.0), x0 + pw - 10, H], fill=(150, 185, 205, 175))
    im = Image.alpha_composite(im, ov).convert('RGB')
    d = ImageDraw.Draw(im)
    for i in range(4):
        d.rectangle([i * pw - 12, 0, i * pw + 12, H], fill=(255, 255, 255))
    for i, (label, _, dettagli, caption) in enumerate(VARIANTS):
        x0 = i * pw

        def px(y, z, x0=x0):
            return (x0 + (y + PANEL / 2) * ppm, zpx(z))
        # i dettagli dipinti, in bianco sulla sagoma
        for kind, *a in dettagli():
            if kind == 'line':
                d.line([px(*q) for q in a[0]], fill=(255, 255, 255), width=a[1], joint='curve')
            else:
                (cy, cz), r = a
                x, y = px(cy, cz)
                rr = r * ppm
                if kind == 'ring':
                    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 255, 255), width=6)
                else:
                    d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 255, 255))
        d.text((x0 + 30, zpx(0.0) + 10), 'superficie del mare', fill=(40, 70, 90), font=small)
        d.text((x0 + int((PANEL / 2 + BOAT_Y - 2.0) * ppm), zpx(0.0) + 46), 'la barca', fill=(70, 70, 70), font=small)
        d.text((x0 + 30, 80), label, fill=(20, 20, 20), font=font)
        # la riga che dice com'è e come si vede dalla barca, sotto il nome
        lines = textwrap.wrap(caption, 52)
        y = 138
        for ln in lines:
            d.text((x0 + 30, y), ln, fill=(20, 40, 55), font=note)
            y += 30
    d.text((40, 15), 'LA MADRE — notte 6, il finale: immobilità totale', fill=(10, 10, 10), font=font)
    d.text((W - 360, 26), 'proposta da approvare', fill=(150, 60, 40), font=small)
    d.text((W - 640, H - 76), 'in grigio: la barca (5,6 m) e un uomo di 1,80 m', fill=(60, 60, 60), font=small)
    d.text((W - 640, H - 42), 'in bianco: i dettagli dipinti', fill=(60, 60, 60), font=small)
    im.save(dst)


if __name__ == '__main__':
    render()
    print('ok madre', flush=True)
