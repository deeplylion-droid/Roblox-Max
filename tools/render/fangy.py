"""
FANGY — modello definitivo (sagoma B «Mastino», testa A «Sciabola»), notte 5. In bozza: da approvare.

Curvo e basso nell'acqua come un mastino: la schiena sale dal mare fino alla gobba delle spalle, la testa sta avanti,
all'altezza delle spalle, le braccia lunghissime scendono fino all'acqua e ci appoggiano le nocche. Viene dal pesce
vipera e dal pesce dente di sciabola: il testone ossuto con le creste e l'opercolo, la bocca enorme che non si chiude
più, le sciabole di sopra che pendono davanti alla mandibola e le zanne del pesce vipera che salgono fuori dal muso;
le fossette della linea laterale in fila sulle guance, sulla mascella e sul cranio (sente le vibrazioni); le file di
lucine (i fotofori) lungo il ventre e sotto la mascella. Da bambino giocava a Marco Polo a occhi chiusi e vinceva
sempre: gli occhialini da piscina con le lenti dipinte di nero gli sono rimasti incastrati nella faccia, la carne ci è
cresciuta attorno. Ora è cieco e caccia a orecchio.

La testa è la A «Sciabola» della tavola (teste_fangy.fangy_a) e il corpo è quello della tavola, con le stesse misure,
gli stessi occhialini e le stesse zanne; qui la testa non è china ma punta la faccia sul pescatore e si gira sul collo,
le lucine sono una per oggetto e la pelle è tagliata in due mesh più fini. Colori approvati (10 ottobre), quelli della tavola: blu
notte quasi nero, più scuro sul dorso e più chiaro sul ventre, le lucine azzurro-ciano, la montatura gialla degli
occhialini con le lenti nere, le zanne pallide.

Coordinate come la tavola: il mare è z = 0, Fangy guarda −Y; le nocche stanno in acqua davanti a lui (y = −0,37), la
schiena scende in mare dietro (y > 0). Nel gioco la posa si ricalcola dalla barca (scena_creature.fangy_posa): il
pescatore arriva come parametro; senza parametri build() rifà la posa di gioco (POSA, numeri arrotondati).

Le parti che si muovono, per le toppe del gioco (come palpebre e aggrotta di robin.build): build(testa=…) gira la
testa sul collo di tanti gradi (positivi verso la sinistra di Fangy, che è +X), con le zanne, gli occhialini, la bava e
le lucine della testa: il gioco la fa scattare verso ogni rumore. Il corpo resta lo stesso, oggetto per oggetto
(cambiano solo 'FangyHead' e i pezzi della testa). Le lucine sono oggetti separati, una per oggetto, in fila:
'FangyLight00', 'FangyLight01', … prima le file del ventre, dalla gola verso l'acqua, poi quelle della testa; ogni
lucina porta la sua fila ('fila') e il suo centro ('centro', coordinate di Fangy) come proprietà dell'oggetto: il
gioco le farà pulsare e accendere in fila da solo, come le luci degli occhi.
build(luci=…) è quanto brillano nel render (1 accese come nella tavola, 0 spente).

Uso: tools/.venv/bin/python tools/render/fangy.py [--fast]          vetrina → docs/concept/fangy_vetrina.jpg
     tools/.venv/bin/python tools/render/fangy.py [--fast] --posa   la posa di gioco nella scena della barca, vista
                                                                    dall'occhio → docs/concept/pose_fangy*.jpg
     tools/.venv/bin/python tools/render/fangy.py --vetrina-tavola  rimonta la tavola della vetrina dai pannelli
     tools/.venv/bin/python tools/render/fangy.py --posa-tavole     rimonta le anteprime della posa dai pannelli
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import dettagli as D  # noqa: E402
import sdf  # noqa: E402
import teste_fangy as TF  # noqa: E402  (la bozza: pelle, corpo, occhialini, zanne, lucine, aiuti)
from common import CACHE, EYE, ROOT, reset_scene  # noqa: E402
from creature import sdf_object  # noqa: E402

V, F, unit = D.V, D.F, D.unit
FAST = '--fast' in sys.argv
# la pelle è un campo solo (corpo e testa) tagliato in due mesh a risoluzioni diverse, che combaciano. Nel gioco Fangy
# sta a due metri dall'occhio, come Robin
RES_BODY = 0.0045 if FAST else 0.0030     # il corpo
RES_HEAD = 0.0030 if FAST else 0.0017     # la testa con le fossette e gli occhialini

# ───────────────────────── la testa (A «Sciabola», dalla tavola) ─────────────────────────

HEAD = V(0.0, -0.19, 0.85)                # centro della testa, come nella tavola
K_TESTA = 1.14                            # la testa A della tavola è più grande del vero
PIEGA = 6.0                               # la testa piegata di lato (chi ascolta), come nella tavola
CHINA = 3.0                               # gradi: la faccia punta appena sotto il pescatore
COLLO = V(0.0, 0.12, -0.04)               # nel sistema della testa: dove entra il collo (e il perno su cui gira)
COLLO_R = 0.10
R_ZONA = 0.40                             # la sfera della testa: ci sta a ogni giro, con la carne che si raccorda

# la posa di gioco (scena_creature.fangy_posa) in coordinate locali, arrotondata: è quella che build() fa senza
# parametri. Nel gioco i numeri si ricalcolano dalla barca.
POSA = {
    'viewer': (0.0, -1.93, 1.12),
}


def testa_frame(viewer, testa=0.0):
    """Il sistema della testa (teste_fangy.Head) e il punto del collo. A riposo la testa punta la faccia sul
    pescatore, gli occhialini ciechi fissi su di lui: girata verso di lui (±35° al massimo), alzata quanto serve
    (CHINA gradi sotto i suoi occhi) e piegata di lato come nella tavola. Nella tavola la testa era china di 10° con la
    camera quasi alla sua altezza; il pescatore sta più in alto, e con la testa china la visiera ossea gli
    nasconderebbe le lenti nere. Il collo ci entra dove vuole il corpo; testa = gradi in più attorno all'asse
    verticale per il collo (il corpo non si muove)."""
    d = V(*viewer) - HEAD
    yaw = max(-35.0, min(35.0, math.degrees(math.atan2(float(d[0]), float(-d[1])))))
    su = math.degrees(math.atan2(float(d[2]), float(np.hypot(d[0], d[1]))))
    china = max(-15.0, min(20.0, CHINA - su))
    fr0 = TF.Head(HEAD, yaw=yaw, pitch=china, roll=PIEGA, scale=K_TESTA)
    neck = fr0.pt(COLLO)
    fr = TF.Head(HEAD, yaw=yaw, pitch=china, roll=PIEGA, scale=K_TESTA)
    Rz = sdf.rot_matrix('z', float(testa))
    fr.pos = (neck + Rz @ (fr0.pos - neck)).astype(F)
    fr.R = (Rz @ fr0.R).astype(F)
    return fr, neck


def testa_campo(fr):
    """La testa A in coordinate locali (teste_fangy.fangy_a): il cranio ossuto con la visiera sopra gli occhialini, il
    muso, le guance, la mandibola calata, la gola, le creste e l'opercolo; le fossette della linea laterale; gli
    occhialini affondati nella carne. Restituisce il campo, i tagli, gli oggetti degli occhialini e l'attributo
    della bocca."""
    cran = sdf.ellipsoid(V(0, 0.03, 0.03), (0.13, 0.165, 0.115))
    brow = sdf.ellipsoid(V(0, -0.088, 0.07), (0.118, 0.08, 0.06))
    visor = sdf.ellipsoid(V(0, -0.118, 0.085), (0.12, 0.05, 0.03))
    snout = sdf.ellipsoid(V(0, -0.158, -0.018), (0.102, 0.088, 0.058))
    cheeks = sdf.union(*[sdf.ellipsoid(V(s * 0.088, -0.06, -0.03), (0.05, 0.08, 0.065)) for s in (-1, 1)])
    jaw = sdf.union(*[D.chain([V(s * 0.10, 0.05, -0.075), V(s * 0.09, -0.08, -0.14), V(s * 0.052, -0.178, -0.158), V(0, -0.21, -0.158)],
                              [0.034, 0.039, 0.036, 0.034], k=0.02) for s in (-1, 1)], k=0.02)
    throat = sdf.ellipsoid(V(0, -0.03, -0.115), (0.09, 0.12, 0.06))
    ridges = sdf.union(*[D.chain([V(s * 0.045, -0.13, 0.09), V(s * 0.062, -0.02, 0.152), V(s * 0.05, 0.10, 0.145)], [0.012, 0.017, 0.012], k=0.01)
                         for s in (-1, 1)])
    opercles = sdf.union(*[TF.ellipsoid_axes(V(s * 0.112, 0.035, -0.05), (0.075, 0.03, 0.075), V(0, 1, 0.15), V(s, 0, 0), V(0, -0.15, 1))
                           for s in (-1, 1)])
    head = sdf.union(cran, brow, visor, snout, cheeks, jaw, throat, ridges, opercles, k=0.03)
    slits = sdf.union(*[TF.ellipsoid_axes(V(s * 0.118, 0.105, -0.055), (0.009, 0.03, 0.068), V(0, 1, 0), V(s, 0, 0), V(0, 0, 1)) for s in (-1, 1)])
    mouth = sdf.union(sdf.ellipsoid(V(0, -0.115, -0.10), (0.092, 0.125, 0.036)), sdf.ellipsoid(V(0, -0.045, -0.09), (0.07, 0.10, 0.04)), slits)
    want = []
    for s in (-1, 1):
        want += list(TF.arc((s * 0.10, -0.15, 0.005), (s * 0.13, -0.05, 0.0), (s * 0.13, 0.07, 0.02), 8))
        want += list(TF.arc((s * 0.07, -0.17, -0.15), (s * 0.105, -0.07, -0.15), (s * 0.11, 0.03, -0.12), 7))
        want += list(TF.arc((s * 0.03, -0.165, 0.115), (s * 0.05, -0.08, 0.16), (s * 0.06, 0.04, 0.17), 5))
    pq, pn = TF.snap(head, want)
    pits = TF.around(sdf.union(*[sdf.sphere(q - n * 0.002, 0.0068) for q, n in zip(pq, pn)]), pq, 0.04)
    add, gcut, gobs = TF.goggles(fr, head, [V(s * 0.060, -0.15, 0.048) for s in (-1, 1)], 0.030, 0.022, strap_up=0.04)
    for o in gobs:
        o.name = 'Fangy' + o.name
    head = sdf.union(head, *add, k=0.016)
    cut = sdf.union(mouth, pits, *gcut)

    def attr_mouth(p):
        q = fr.local(p)
        e = np.linalg.norm((q - V(0, -0.09, -0.10)) / V(0.095, 0.14, 0.045), axis=1)
        return np.clip((1.15 - e) / 0.2, 0, 1).astype(F)
    return head, cut, gobs, attr_mouth


# le lucine della testa (sistema della testa): sette per lato in fila lungo la mandibola, dal mento verso la gola, e
# quella grande sotto l'occhio
LUCI_TESTA = ([(V(s * 0.06 + s * 0.05 * t, -0.17 + 0.19 * t, -0.17 + 0.02 * t), 0.0068, f'mandibola{"_sx" if s > 0 else "_dx"}')
               for s in (-1, 1) for t in np.linspace(0, 1, 7)]
              + [(V(s * 0.112, -0.085, -0.02), 0.011, f'guancia{"_sx" if s > 0 else "_dx"}') for s in (-1, 1)])


def zanne(fr):
    """Le zanne della tavola: le sciabole di sopra che pendono davanti alla mandibola, quelle del pesce vipera che
    salgono fuori dal muso e si incrociano, gli aghi in fila; un'unica mesh di tubi affusolati."""
    fangs = []
    for s in (-1, 1):
        fangs.append(TF.fang((s * 0.046, -0.214, -0.055), (s * 0.06, -0.16, -1), 0.29, 0.0125, bend=(0, 0.04, 0)))
        fangs.append(TF.fang((s * 0.078, -0.19, -0.058), (s * 0.12, -0.10, -1), 0.15, 0.0085, bend=(0, 0.02, 0)))
        fangs.append(TF.fang((s * 0.094, -0.14, -0.066), (s * 0.15, -0.05, -1), 0.075, 0.0065))
        fangs.append(TF.fang((s * 0.026, -0.212, -0.132), (s * 0.05, -0.45, 1), 0.17, 0.0105))
        fangs.append(TF.fang((s * 0.072, -0.172, -0.13), (s * 0.40, -0.30, 1), 0.125, 0.0092, bend=(0, 0.025, 0)))
        fangs.append(TF.fang((s * 0.086, -0.12, -0.128), (s * 0.30, -0.20, 1), 0.07, 0.0062))
        for t in np.linspace(0.1, 0.9, 5):
            x = s * (0.02 + 0.06 * t)
            fangs.append(TF.fang((x, -0.205 + 0.07 * t * t, -0.068), (s * 0.1, -0.3, -1), 0.034 + 0.014 * (1 - t), 0.0036))
            fangs.append(TF.fang((x * 0.95, -0.19 + 0.07 * t * t, -0.132), (s * 0.1, -0.35, 1), 0.03 + 0.012 * (1 - t), 0.0034))
    return TF.tubes('FangyFangs', TF.local_curves(fr, fangs), D.needle_teeth())


def luce_material(luci):
    """Il fotoforo: una perla azzurra che brilla (luci = 1 come nella tavola, 0 spenta: resta la perla lucida)."""
    k = min(max(float(luci), 0.0), 1.0)
    if k >= 0.999:
        return TF.luce_material()
    return D.glow(f'FangyLightSpenta{int(round(k * 100)):03d}', tuple(c * k for c in TF.LUCE), 16.0 * k + 1e-4,
                  base=(0.45, 0.90, 1.0))


# ───────────────────────── costruzione ─────────────────────────

def build(viewer=None, testa=0.0, luci=1.0, solo_testa=False):
    """Fangy nell'acqua, in coordinate locali. viewer: dove guarda la testa a riposo (il pescatore); testa: gradi di
    giro della testa sul collo (positivi verso la sinistra di Fangy); luci: quanto brillano le lucine (0..1).
    La pelle è tagliata in due mesh che combaciano: 'FangyHead' (la testa, nella sfera R_ZONA) e 'FangySkin' (il
    corpo). Le lucine sono 'FangyLight00'…, in fila, con le proprietà 'fila' e 'centro'. solo_testa=True fa solo la testa
    con i suoi pezzi e le sue lucine (per le varianti della vetrina: il corpo non cambia)."""
    P = dict(POSA)
    if viewer is not None:
        P['viewer'] = viewer
    fr, neck = testa_frame(V(*P['viewer']), testa)
    head, cut, gobs, attr_mouth = testa_campo(fr)
    head_r = 0.30 * fr.S
    body = TF.Body(neck, COLLO_R)
    hw = TF.bounded(fr.field(head), fr.pos, head_r)
    f = sdf.union(body.field(), hw, k=0.05)
    f = sdf.subtract(f, TF.bounded(fr.field(cut), fr.pos, head_r), k=0.005)
    f = sdf.subtract(f, body.gills(), k=0.006)
    # le lucine: le file del ventre (dal basso in su, a coppie) e quelle della testa, posate sulla pelle, con le
    # coppette e l'orlo; quelle sott'acqua non si fanno
    want, rr = body.light_rows()
    nb = len(want)
    want += [fr.pt(p) for p, _, _ in LUCI_TESTA]
    rr += [r * fr.S for _, r, _ in LUCI_TESTA]
    pts, nrm = TF.snap(f, want)
    rr = np.asarray(rr, F)
    keep = pts[:, 2] > 0.01
    holes, rims = TF.cups(pts[keep], nrm[keep], rr[keep])
    f = sdf.subtract(sdf.union(f, rims, k=0.003), holes, k=0.002)
    attrs = {'ventre': body.ventre(fr, head_r), 'mouth': attr_mouth}
    zona = sdf.sphere(HEAD, R_ZONA)
    pelle = TF.pelle_fangy()
    obs = []
    ob = sdf_object('FangyHead', sdf.intersect(f, zona), HEAD - R_ZONA - 0.02, HEAD + R_ZONA + 0.02, res=RES_HEAD, attrs=attrs,
                    banded=True)
    ob.data.materials.append(pelle)
    obs.append(ob)
    if not solo_testa:
        lo = np.minimum(V(-0.43, -0.46, -0.035), HEAD - R_ZONA)
        hi = np.maximum(V(0.43, 0.84, 1.10), HEAD + R_ZONA)
        lo[2] = -0.035                    # sotto il mare non serve: nel gioco il mare fa da maschera
        ob = sdf_object('FangySkin', sdf.subtract(f, zona), lo, hi, res=RES_BODY, attrs=attrs, banded=True)
        ob.data.materials.append(pelle)
        obs.append(ob)
    # le lucine, una per oggetto, in fila: prima il ventre (la fila di dentro e quella di fuori, ogni fila dalla gola
    # verso l'acqua, i due lati alternati), poi la testa (la mandibola dal mento verso la gola, poi le guance)
    file_corpo = ['ventre_dentro'] * 22 + ['ventre_fuori'] * 16
    nomi = (file_corpo + ['?'] * nb)[:nb] + [n for _, _, n in LUCI_TESTA]
    ordine = []
    for fila in ('ventre_dentro', 'ventre_fuori'):
        idx = [i for i in range(nb) if nomi[i] == fila and keep[i]]
        ordine += sorted(idx, key=lambda i: (-round(float(pts[i, 2]), 3), float(pts[i, 0])))
    ordine += [i for i in range(nb, len(want)) if keep[i]]
    mat = luce_material(luci)
    for j, i in enumerate(ordine):
        if solo_testa and i < nb:
            continue
        c = pts[i] - nrm[i] * (rr[i] * 0.30)
        o = TF.balls(f'FangyLight{j:02d}', [c], [rr[i] * 0.95], mat)
        o['fila'] = nomi[i]                          # la fila e il centro (coordinate di Fangy) restano sull'oggetto
        o['centro'] = [float(x) for x in c]
        obs.append(o)
        if luci > 0 and j % 3 == 0:
            # un filo di luce vera sulla pelle bagnata attorno (luci della testa a parte: girano con lei)
            nome = 'FangyFotoforo' if i < nb else 'FangyFotoforoTesta'
            obs.append(D.point_light(f'{nome}{j:02d}', tuple(map(float, pts[i] + nrm[i] * 0.018)), 0.10 * float(luci),
                                     (0.25, 0.85, 1.0), radius=0.006))
    obs += gobs
    c0 = fr.pt((0, -0.06, -0.10))
    obs.append(D.mesh('FangyThroat', fr.field(sdf.ellipsoid(V(0, -0.06, -0.10), (0.065, 0.10, 0.03))), c0 - 0.16 * fr.S,
                      c0 + 0.16 * fr.S, D.dark_throat(), res=0.004))
    obs.append(zanne(fr))
    # la bava: fili fra le zanne, gocce dal mento e dalle punte
    obs.append(TF.tubes('FangyDrool', TF.strands(fr, [((-0.046, -0.235, -0.16), (-0.05, -0.20, -0.15), 0.02),
                                                       ((0.046, -0.235, -0.18), (0.074, -0.19, -0.125), 0.025),
                                                       ((-0.078, -0.205, -0.12), (-0.074, -0.17, -0.13), 0.012)]), TF.goo_material()))
    obs.append(TF.drips('FangySlime', f, [fr.pt((0.0, -0.21, -0.18)), fr.pt((-0.04, -0.19, -0.185)), fr.pt((0.06, -0.16, -0.185))],
                        np.random.default_rng(5)))
    if not solo_testa:
        rip = TF.ripples()
        rip.name = 'FangyRipples'
        obs.append(rip)
    return obs


# ───────────────────────── vetrina ─────────────────────────

SHOTS = {
    # (camera, bersaglio, lente), in coordinate locali di Fangy (guarda −Y, verso la barca)
    'insieme': ((-0.95, -1.85, 1.25), (0.0, -0.05, 0.55), 32),
    'testa': ((-0.30, -1.05, 1.05), (0.0, -0.22, 0.80), 50),
    'fuori': ((2.30, 0.55, 0.62), (0.0, 0.0, 0.55), 30),
}
# le varianti da vicino: (titolo, giro della testa, luci)
VARIANTI = (('la testa girata alla sua destra (testa −35°)', -35.0, 1.0),
            ('la testa girata alla sua sinistra (testa +35°)', 35.0, 1.0), ('le lucine spente (luci 0)', 0.0, 0.0))
SHOT_VARIANTI = ((-0.15, -1.55, 1.20), (0.0, -0.10, 0.70), 40)


def mare():
    """Il mare della vetrina, quello della tavola (teste_fangy.water): nero, con le onde che rompono i riflessi."""
    w = TF.water()
    return w


def _luci_studio(M, h):
    """Le luci di studio delle altre vetrine, attorno alla testa h (mondo): la lanterna calda dalla barca, la luna
    fredda da dietro, poco riempimento."""
    from mathutils import Vector
    R = M.to_3x3()
    rel = lambda v: tuple(h + np.array(R @ Vector(v)))
    D.area_light('Key', rel((-0.9, -1.6, 0.35)), tuple(h), 30, (1.0, 0.74, 0.46), 0.5)
    D.area_light('Rim', rel((1.0, 1.5, 1.1)), tuple(h + (0.0, 0.0, -0.2)), 120, (0.55, 0.72, 1.0), 0.6)
    D.area_light('Fill', rel((1.3, -1.6, 0.3)), tuple(h), 6, (0.55, 0.65, 0.85), 1.6)


def scena_vetrina():
    """La scena della vetrina: Fangy nella posa di gioco (scena_creature.fangy_posa), solo nell'acqua come nella
    tavola (lo scafo col mare a z = 0 si allagherebbe), con le luci di studio; resa AgX. Restituisce la
    trasformazione della posa e i parametri di build()."""
    import scena_creature as SC
    from mathutils import Vector
    sc = reset_scene()
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'None'
    sc.cycles.use_denoising = True
    w = bpy.data.worlds.new('Night')
    sc.world = w
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.010, 0.014, 0.022, 1)
    w.lightgroup = 'ambient'
    mare()
    M, kw = SC.fangy_posa()
    SC.place(build(**kw), M)
    h = np.array(M @ Vector(tuple(map(float, HEAD))))
    _luci_studio(M, h)
    return M, kw


def _camera(M, cl, ct, lens):
    from mathutils import Vector
    sc = bpy.context.scene
    cam = sc.camera
    if cam is None:
        cam_d = bpy.data.cameras.new('Cam')
        cam_d.sensor_width = 36.0
        cam_d.clip_start = 0.02
        cam = bpy.data.objects.new('Cam', cam_d)
        sc.collection.objects.link(cam)
        sc.camera = cam
    cam.data.lens = lens
    a, b = M @ Vector(cl), M @ Vector(ct)
    cam.location = a
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = (b - a).to_track_quat('-Z', 'Y')
    return cam


def _testa_di(obs):
    """Gli oggetti della testa (quelli che le varianti rifanno): la pelle della testa, gli occhialini, le zanne, la
    gola, la bava e le lucine della testa."""
    testa = ('FangyHead', 'FangyGoggle', 'FangyFangs', 'FangyThroat', 'FangyDrool', 'FangySlime', 'FangyFotoforoTesta')
    return [o for o in obs if o.name.startswith(testa) or (o.get('fila') and not o['fila'].startswith('ventre'))]


def showcase(shots=('insieme', 'testa', 'fuori'), varianti=True):
    """La vetrina: tools/render/cache/vetrina/fangy_<inquadratura>.png, le varianti da vicino (la testa girata dalle
    due parti, le lucine spente: fangy_variante_<i>.png) e la tavola docs/concept/fangy_vetrina.jpg."""
    out = []
    os.makedirs(os.path.join(CACHE, 'vetrina'), exist_ok=True)
    W, H = (720, 540) if FAST else (960, 720)          # la tavola li riduce a 480 × 360
    M, kw = scena_vetrina()
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 32 if FAST else 64
    sc.render.image_settings.file_format = 'PNG'
    for name in shots:
        _camera(M, *SHOTS[name])
        path = os.path.join(CACHE, 'vetrina', f'fangy_{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('ok', path, flush=True)
    if varianti:
        import scena_creature as SC
        riposo = _testa_di([o for o in bpy.data.objects if o.name.startswith('Fangy')])
        _camera(M, *SHOT_VARIANTI)
        nuove = []
        for i, (_, giro, luci) in enumerate(VARIANTI):
            for o in riposo + nuove:
                o.hide_render = True
            if giro:
                nuove = SC.place(build(**kw, testa=giro, solo_testa=True), M)
            else:
                # la testa a riposo; le lucine spente sono le stesse perle col materiale spento, senza luce
                for o in riposo:
                    o.hide_render = False
                m = luce_material(luci)
                for o in bpy.data.objects:
                    if o.name.startswith('FangyLight') and o.type == 'MESH' and not o.hide_render:
                        o.data.materials[0] = m
                    if o.name.startswith('FangyFotoforo') and luci <= 0:
                        o.hide_render = True
            path = os.path.join(CACHE, 'vetrina', f'fangy_variante_{i}.png')
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            out.append(path)
            print('ok', path, flush=True)
    if len(shots) == 3 and varianti:
        tavola_vetrina()
    return out


def _font(size, bold=False):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''), size)
    except OSError:
        return ImageFont.load_default()


def tavola_vetrina(size=(480, 360)):
    """La tavola della vetrina: sopra le tre inquadrature (insieme, testa, di fianco dal mare), sotto le varianti (la
    testa girata dalle due parti, le lucine spente), con le didascalie → docs/concept/fangy_vetrina.jpg."""
    W, H = size
    cap = 30
    sheet = Image.new('RGB', (3 * W, 2 * (H + cap)), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    font = _font(15)
    titoli = ['insieme, dalla parte della barca', 'la testa: occhialini, zanne, fossette', 'di fianco, dal mare']
    righe = [[os.path.join(CACHE, 'vetrina', f'fangy_{n}.png') for n in ('insieme', 'testa', 'fuori')],
             [os.path.join(CACHE, 'vetrina', f'fangy_variante_{i}.png') for i in range(len(VARIANTI))]]
    for r, (paths, tt) in enumerate(zip(righe, (titoli, [t for t, _, _ in VARIANTI]))):
        for i, (p, t) in enumerate(zip(paths, tt)):
            im = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)
            y = r * (H + cap)
            sheet.paste(im, (i * W, y))
            d.text((i * W + 8, y + H + 6), t, fill=(225, 225, 220), font=font)
    dst = os.path.join(ROOT, 'docs', 'concept', 'fangy_vetrina.jpg')
    sheet.save(dst, quality=90)
    print('tavola', dst, flush=True)
    return dst


# ───────────────────────── la posa nella scena del gioco ─────────────────────────

def _angoli(pts):
    """Yaw e pitch (gradi) dei punti visti dall'occhio: yaw positivo a destra, come nel gioco."""
    d = np.atleast_2d(np.asarray(pts, float)) - np.array(EYE)
    return np.degrees(np.arctan2(d[:, 0], d[:, 1])), np.degrees(np.arctan2(d[:, 2], np.hypot(d[:, 0], d[:, 1])))


def _span(pts):
    y, p = _angoli(pts)
    return {'yaw': [round(float(y.min()), 1), round(float(y.max()), 1)], 'pitch': [round(float(p.min()), 1), round(float(p.max()), 1)]}


def _dir(p):
    y, pt = _angoli([tuple(p)])
    return [round(float(y[0]), 1), round(float(pt[0]), 1)]


def _rel(p):
    return [round(float(p[i] - EYE[i]), 4) for i in range(3)]


def ingombro(obs, M):
    """Dove sta la posa vista dall'occhio del pescatore (per la regia del gioco): yaw e pitch minimi e massimi di
    tutti i pezzi e della parte che si vede davvero (senza quello che coprono la barca e il mare), della testa e del
    corpo; dove sta la testa (gradi, metri dall'occhio, quota); e le lucine, in fila, dall'occhio (il motore le fa
    pulsare: [nome, fila, metri dall'occhio])."""
    import jobs
    from mathutils import Vector
    meshes = [o for o in obs if o.type == 'MESH']
    pts = np.array(jobs.dense_points(meshes, n=2500))
    dg = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    nomi = {o.name for o in meshes}
    eye = np.array(EYE)
    vis = []
    for p in pts:
        d = p - eye
        L = float(np.linalg.norm(d))
        d /= L
        hit, _, _, _, ob, _ = sc.ray_cast(dg, Vector(tuple(eye + d * 0.15)), Vector(tuple(d)), distance=L - 0.15 - 0.003)
        vis.append((not hit) or (ob is not None and ob.name in nomi))
    vis = np.array(vis) & (pts[:, 2] > 0.0)
    head = M @ Vector(tuple(map(float, HEAD)))
    out = {
        'tutto': _span(pts),
        'visibile': _span(pts[vis]),
        'testa': _dir(head),
        'testa_m': _rel(head),
        'distanza_testa': round(float(math.dist(tuple(head), EYE)), 2),
        'quota_testa': round(float(head[2]), 2),
        'luci': [[o.name, o['fila'], _rel(o.matrix_world @ Vector(o['centro']))]
                 for o in sorted((o for o in meshes if o.get('fila')), key=lambda o: o.name)],
    }
    for k, n in (('testa_mesh', 'FangyHead'), ('corpo', 'FangySkin'), ('zanne', 'FangyFangs')):
        o = bpy.data.objects.get(n)
        if o:
            out[k] = _span(jobs.dense_points([o], n=2500))
    return out


POSE_ANTEPRIME = {
    # (yaw, pitch, lente): la vista del gioco (90° di campo) girata a destra verso Fangy, e una più stretta su di lui
    'pose_fangy': (88.0, -12.0, 18.0),
    'pose_fangy_vicino': (None, -10.0, 34.0),
}


def anteprima_posa():
    """Anteprima della posa fangy_ascolta senza toccare il gioco (come robin.anteprima_posa): la scena del gioco con
    la batteria, la canna, la posa da scena_creature, e la camera prospettica dall'occhio del pescatore come la vista
    del gioco (90° di campo) e una più stretta su Fangy. Scrive i pannelli in cache e l'ingombro in
    cache/fangy_posa.json."""
    import batteria
    import jobs
    import scena_creature as SC
    from common import perspective_camera
    jobs.build_scene(fish=5, rod=True)
    batteria.build_battery(needle=0.72)
    before = set(bpy.data.objects.keys())
    SC.POSES['fangy_ascolta'][0]()
    bpy.context.view_layer.update()
    new = [bpy.data.objects[n] for n in set(bpy.data.objects.keys()) - before]
    info = ingombro(new, SC.LAST_M['fangy_ascolta'])
    print('ingombro', json.dumps(info), flush=True)
    with open(os.path.join(CACHE, 'fangy_posa.json'), 'w') as fh:
        json.dump(info, fh, indent=1)
    sc = bpy.context.scene
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.resolution_percentage = 100
    sc.render.resolution_x, sc.render.resolution_y = (960, 540) if FAST else (1600, 900)
    sc.cycles.samples = 24 if FAST else 64
    out = []
    for name, (yaw, pitch, lens) in POSE_ANTEPRIME.items():
        if yaw is None:
            yaw = info['testa'][0] - 4.0
        t = (EYE[0] + math.sin(math.radians(yaw)) * math.cos(math.radians(pitch)),
             EYE[1] + math.cos(math.radians(yaw)) * math.cos(math.radians(pitch)), EYE[2] + math.sin(math.radians(pitch)))
        perspective_camera(EYE, t, lens=lens, name='FangyCam_' + name)
        path = os.path.join(CACHE, f'{name}.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
        print('pannello', path, flush=True)
    return out, info


def anteprima_tavole(paths=None):
    """Le anteprime della posa con la scritta «da approvare» → docs/concept/pose_fangy.jpg e pose_fangy_vicino.jpg
    (dai pannelli in cache, senza rifarli)."""
    paths = paths or [os.path.join(CACHE, f'{n}.png') for n in POSE_ANTEPRIME]
    font = _font(22, bold=True)
    out = []
    for p in paths:
        im = Image.open(p).convert('RGB')
        d = ImageDraw.Draw(im)
        txt = 'FANGY · posa fangy_ascolta · da approvare'
        d.rectangle((0, 0, int(d.textlength(txt, font=font)) + 24, 38), fill=(14, 14, 16))
        d.text((12, 7), txt, fill=(240, 190, 110), font=font)
        dst = os.path.join(ROOT, 'docs', 'concept', os.path.basename(p).replace('.png', '.jpg'))
        im.save(dst, quality=90)
        out.append(dst)
        print('anteprima', dst, flush=True)
    return out


if __name__ == '__main__':
    if '--posa' in sys.argv:
        anteprima_posa()
        anteprima_tavole()
    elif '--posa-tavole' in sys.argv:
        anteprima_tavole()
    elif '--vetrina-tavola' in sys.argv:
        tavola_vetrina()
    elif '--solo' in sys.argv:
        solo = sys.argv[sys.argv.index('--solo') + 1].split(',')
        showcase(tuple(s for s in solo if s in SHOTS), varianti='varianti' in solo)
    else:
        showcase()
