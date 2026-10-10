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
    robin_strizza    toppa di robin_secchio: la sola testa, che strizza gli occhi nella luce della lampara
    robin_chiusi     toppa di robin_secchio: la sola testa a occhi chiusi (il battito di ciglia)
    archie_soffia    Archie che sale dal mare a destra della lampara, il collo dritto, la testa piegata sul vetro
                     con la trombetta puntata (notte 3; la trombetta arrotolata)
    archie_fiato     toppa di archie_soffia: la testa con la gola gonfia, il risucchio prima di soffiare
    lampy_lenza      Lampy aggrappata alla lenza vicino al pelo dell'acqua, ad arco, con la bocca e la ventosa della coda
                     (notte 4; da approvare)
    fangy_ascolta    Fangy nell'acqua accanto alla barca, a destra dietro il pescatore: curvo, la testa spinta avanti
                     verso il rumore, le nocche in acqua (notte 5; da approvare)

Le «toppe» sono pose uguali a quella principale con la sola parte che cambia visibile (il resto della creatura
fa da maschera, come la barca): il gioco le dissolve sopra lo strato principale. Le opzioni (quarto elemento
delle voci di POSES) sono spiegate in jobs.job_creature.

Uso: tools/.venv/bin/python tools/render/jobs.py creature --quality preview
     POSES=robin_strizza,robin_chiusi tools/.venv/bin/python tools/render/jobs.py creature --quality final
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


# La testa di Robin nelle toppe: la pelle della testa (con le arcate), gli occhi, le palpebre, e quello che sta
# nella faccia e non cambia (gola, denti, la bava della bocca), così la toppa non ha buchi dentro la faccia. I baffi
# no: partono dagli angoli della bocca e non si muovono con le arcate. Il resto di Robin fa da maschera: le parti
# che passano davanti alla testa la coprono come nello strato principale.
ROBIN_TESTA = ('RobinHead', 'RobinEye*', 'RobinLid*', 'RobinThroat', 'RobinTeeth', 'RobinSlime')
ROBIN_TOPPA = {'visibili': ROBIN_TESTA, 'occhi': False, 'yaw_di': 'robin_secchio'}

# La testa di Archie nelle toppe: la pelle della testa, gli occhi, i denti, la bava e la trombetta (bocchino, carta e
# piuma). La trombetta che si srotola lascia vuoto il posto dove nello strato principale c'era la spirale: nella toppa
# si vede anche il collo ('ArchieSkin'), con il riquadro sulla sola testa, e il gioco sfuma lo strato principale dove
# la toppa è vuota (come le mascelle di Gulpy e Hatch, pose_animate.py).
ARCHIE_TESTA = ('ArchieHead', 'ArchieEye*', 'ArchieTeeth', 'ArchieSlime', 'ArchieMouthpiece', 'ArchieBlower', 'ArchieFeather')
ARCHIE_CORPO = ('ArchieSkin',)
ARCHIE_TOPPA = {'visibili': ARCHIE_TESTA + ARCHIE_CORPO, 'riquadro': ARCHIE_TESTA, 'occhi': False, 'yaw_di': 'archie_soffia'}

# chiave → (funzione, spazio, mare[, opzioni]): vedi jobs.job_creature
POSES = {
    'gulpy_sale': (gulpy_sale, 'world', False),
    'gulpy_pretende': (gulpy_pretende, 'boat', True),
    'molly_destra': (lambda: molly(+1), 'boat', False),
    'molly_sinistra': (lambda: molly(-1), 'boat', False),
    'hatch_conta': (hatch_conta, 'world', False),
    'robin_secchio': (lambda: robin_secchio(), 'boat', True),
    # nella luce piena strizza gli occhi (le palpebre a tre quarti, le arcate aggrottate); sulla barca ogni tanto
    # sbatte le palpebre
    'robin_strizza': (lambda: robin_secchio(palpebre=0.75, aggrotta=1.0), 'boat', True, ROBIN_TOPPA),
    'robin_chiusi': (lambda: robin_secchio(palpebre=1.0, aggrotta=0.0), 'boat', True, ROBIN_TOPPA),
    # notte 3: Archie accanto alla lampara; prima di soffiare prende fiato e la gola si gonfia (toppa)
    'archie_soffia': (lambda: archie_soffia(), 'boat', True),
    'archie_fiato': (lambda: archie_soffia(fiato=1.0), 'boat', True, ARCHIE_TOPPA),
    # notte 4: Lampy sulla lenza, a destra della prua (da approvare)
    'lampy_lenza': (lambda: lampy_lenza(), 'boat', True),
    # notte 5: Fangy nell'acqua a destra, dietro il pescatore (da approvare)
    'fangy_ascolta': (lambda: fangy_ascolta(), 'world', True),
}


# ───────────────────────── notte 2 ─────────────────────────

# Robin (robin.py) sul capodibanda di sinistra verso prua. La faccia sta a ROBIN_YAW dall'occhio (YAW.robin nel
# gioco) ed è girata verso il pescatore; il busto, girato a metà tra lui e il secchio, si appoggia al bordo e la
# coda scende in acqua. Il braccio lunghissimo passa alto davanti al banco di prua (dall'occhio sopra il telone,
# la bambola e la borraccia, senza toccarli) e tira fuori un pesce dal secchio (boat.BUCKET_POS) dalla parte del
# pescatore, davanti al manico: la batteria resta a destra, il braccio non ci arriva. Le zampe dalla parte della
# prua stanno lontane dal punto dove si aggrappa Gulpy in gulpy_pretende (capodibanda di sinistra a y = 1,2):
# nella notte 2 possono esserci insieme.
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


def _tra_ordinate(y):
    """La y più vicina a metà tra due ordinate (boat.build_structure le mette ogni 0,27 m a partire da −2,25):
    lì le dita che scendono lungo la fiancata di dentro non toccano il legno."""
    k = round((y + 2.25) / 0.27 - 0.5)
    return -2.25 + 0.27 * (k + 0.5)


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
    # la mano ha appena tirato fuori il pesce: lo stringe per la coda sopra la bocca del secchio, dalla parte del
    # pescatore e davanti al manico, e il pesce pende fuori, con la testa che lascia ora il bordo
    fist = (bx - 0.075, by - 0.075, bz + 0.57)
    bench_x = -(boat.half_width_at(by, boat.BENCH_TOP) - 0.07)
    # le punte delle zampe: dal lato della poppa una sul capodibanda, tra la spalla e la mano, e due fuori sulla
    # fiancata; dal lato della prua una sul banco (tra la fiancata e il telone), una sul capodibanda prima di
    # y = 1 e una fuori. L'altra mano si tiene al capodibanda più verso poppa, a metà tra due ordinate
    feet = [_bordo(y0 - 0.27, 0.02), _fiancata_fuori(y0 - 0.40, 0.50), _fiancata_fuori(y0 - 0.10, 0.40),
            (bench_x, by - 0.07, boat.BENCH_TOP), _bordo(y0 + 0.30), _fiancata_fuori(y0 + 0.28, 0.46)]
    grip = _bordo(_tra_ordinate(y0 - 0.55))
    loc = lambda p: tuple(float(v) for v in to_local(M, p))
    return M, {'viewer': loc(EYE), 'bucket': loc(rim), 'reach': loc(fist), 'feet': [loc(p) for p in feet],
               'grip': loc(grip), 'lungo': tuple(float(v) for v in lungo)}


def robin_secchio(palpebre=0.0, aggrotta=0.0):
    """La posa robin_secchio; con palpebre e aggrotta (robin.build) le espressioni delle toppe, nella stessa posa."""
    import robin as ro
    M, kw = robin_posa()
    LAST_M['robin_secchio'] = M
    return place(ro.build(**kw, palpebre=palpebre, aggrotta=aggrotta), M)


# ───────────────────────── notte 3 ─────────────────────────

# Archie (archie.py) sale dal mare a destra della lampara e appena oltre (più lontano dal pescatore): il collo dritto
# esce da dietro la prua, in cima fa l'arco e la testa guarda giù sul vetro, con la trombetta puntata su di lui.
# Dall'occhio sta tra la lampara (0°) e la canna (31°), dove nelle altre notti non c'è nessuno: Gulpy e Robin sono a
# sinistra della prua, Molly sui fianchi, Hatch a poppa, e la lenza va verso il largo a destra della canna (40°).
# La testa sta più in alto del vetro di ARCHIE_SU gradi, così la trombetta distesa passa sotto il cappello della
# lampara; ARCHIE_LATO la porta un po' dietro la lampara: dal pescatore la faccia si vede di tre quarti (di fianco,
# a 0°, si vedrebbe di profilo; più dietro, la trombetta distesa verrebbe verso di lui e si accorcerebbe).
ARCHIE_LATO = 35.0     # gradi attorno alla lampara, da destra (0) verso il largo (90)
ARCHIE_SU = 26.0       # gradi sopra il vetro
ARCHIE_DIST = 1.40     # metri dal centro della testa al vetro (la trombetta distesa ci arriva a pochi centimetri)


def archie_posa():
    """La trasformazione della posa archie_soffia e i parametri di archie.build() in coordinate locali (servono
    anche alla vetrina di archie.py e al jumpscare). Il collo sta in verticale: la creatura gira solo attorno a Z,
    con la faccia (−y locale) verso la lampara."""
    import archie as ar
    L = np.array(boat.LAMP_POS, F)
    b, e = math.radians(ARCHIE_LATO), math.radians(ARCHIE_SU)
    H = L + ARCHIE_DIST * np.array((math.cos(e) * math.cos(b), math.cos(e) * math.sin(b), math.sin(e)), F)
    yaw = ARCHIE_LATO - 90.0
    t = math.radians(yaw)
    hx, hy, hz = (float(v) for v in ar.HEAD)
    o = (float(H[0]) - (hx * math.cos(t) - hy * math.sin(t)), float(H[1]) - (hx * math.sin(t) + hy * math.cos(t)), float(H[2]) - hz)
    M = M_of(o, yaw=yaw)
    loc = lambda p: tuple(round(float(v), 4) for v in to_local(M, p))
    return M, {'lampara': loc(L), 'viewer': loc(EYE)}


def archie_soffia(srotolata=0.0, fiato=0.0):
    """La posa archie_soffia; con srotolata e fiato (archie.build) le varianti delle toppe, nella stessa posa."""
    import archie as ar
    M, kw = archie_posa()
    LAST_M['archie_soffia'] = M
    return place(ar.build(**kw, srotolata=srotolata, fiato=fiato), M)


# ───────────────────────── notte 4 ─────────────────────────

# Lampy (lampy.py) aggrappata alla lenza vicino al pelo dell'acqua, ad arco: la lenza le entra in bocca, passa sotto
# l'arco e la ventosa della coda la tiene a un palmo dall'acqua; da lì il filo scende in mare (il galleggiante, tirato
# sotto, non si vede). Sta a destra della prua, oltre la punta della canna (30°), più lontana e più bassa della punta;
# ha tirato la lenza un po' a destra di dove va di solito (il galleggiante sta a 40°). L'arco si vede quasi di profilo
# (girato di LAMPY_GIRO, la coda verso il largo) e la faccia guarda il pescatore. A 43° la canna, che all'altezza della testa sta tra 31° e 34°, le passa a sinistra della
# faccia senza coprirla, e la boa verde (37,7°, 2° sopra l'orizzonte) col suo riflesso sull'acqua resta a sinistra
# della testa: più vicina, la boa lampeggiava tra la faccia e l'arco e il riflesso le scendeva dalla bocca come bava
# luminosa. Lì nelle altre notti non c'è nessuno: Archie sta tra la lampara e la canna e molto più in alto, Molly sul
# bordo di destra da 59°. Nel gioco la lenza va disegnata per i punti di lampy_lenza_punti: dalla punta della canna
# alla bocca, sotto l'arco fino alla ventosa della coda, poi in mare.
LAMPY_YAW = 43.0       # gradi: dove la lenza le entra in bocca, dall'occhio
LAMPY_DIST = 6.0       # metri, in orizzontale, dall'occhio alla bocca
LAMPY_GIRO = 15.0      # gradi: l'arco girato con la coda verso il largo (0: esattamente di profilo dall'occhio)
LAMPY_SCALA = 1.15     # più grande del modello: a sei metri deve leggersi accanto alla canna
CANNA_PUNTA = (2.02, 2.95, 1.80)   # la punta della canna a riposo (boat.build_rod, lo strato rod0 del gioco)


def lampy_posa():
    """La trasformazione della posa lampy_lenza e i parametri di lampy.build() in coordinate locali (servono anche
    alla vetrina di lampy.py). Lampy gira solo attorno a Z, il mare resta a z = 0; la bocca (lampy.BOCCA) va a
    LAMPY_DIST metri dall'occhio, a LAMPY_YAW gradi."""
    import lampy as la
    from mathutils import Vector
    a = math.radians(LAMPY_YAW)
    b = (EYE[0] + LAMPY_DIST * math.sin(a), EYE[1] + LAMPY_DIST * math.cos(a), float(la.BOCCA[2]) * LAMPY_SCALA)
    yaw = facing_yaw(b) + LAMPY_GIRO
    off = M_of((0.0, 0.0, 0.0), yaw=yaw, scale=LAMPY_SCALA) @ Vector(tuple(map(float, la.BOCCA)))
    M = M_of((b[0] - off.x, b[1] - off.y, b[2] - off.z), yaw=yaw, scale=LAMPY_SCALA)
    loc = lambda p: tuple(round(float(v), 4) for v in to_local(M, p))
    return M, {'viewer': loc(EYE)}


def lampy_lenza_punti(M=None):
    """I punti della lenza con Lampy attaccata (mondo): la punta della canna, la bocca, la ventosa della coda, dove
    il filo entra in mare."""
    import lampy as la
    from mathutils import Vector
    if M is None:
        M, _ = lampy_posa()
    w = lambda p: tuple(float(x) for x in M @ Vector(tuple(map(float, p))))
    return [CANNA_PUNTA, w(la.BOCCA), w(la.CODA), w(la.ACQUA)]


def lampy_lenza(bocca=None, denti_giro=0.0):
    """La posa lampy_lenza; con bocca e denti_giro (lampy.build) le varianti delle toppe, nella stessa posa."""
    import lampy as la
    M, kw = lampy_posa()
    LAST_M['lampy_lenza'] = M
    return place(la.build(**kw, bocca=la.BOCCA_RIPOSO if bocca is None else bocca, denti_giro=denti_giro), M)


# ───────────────────────── notte 5 ─────────────────────────

# Fangy (fangy.py) nell'acqua accanto alla barca, a destra e un po' dietro il pescatore: curvo e basso, le nocche in
# acqua a mezzo metro dallo scafo, la testa spinta avanti verso di lui (verso il rumore). Dall'occhio si vedono la
# testa con le zanne e gli occhialini e la gobba sopra il bordo; le braccia scendono dietro la fiancata. Sta dove nelle
# altre notti non c'è nessuno: tra Molly (sul bordo di destra, fino a 94°) e la poppa (Hatch e il sonar, oltre 165°);
# la canna e la lenza stanno davanti a destra (30-45°), Lampy con loro. Sta nel mondo, non sulla barca (come Hatch):
# non la tocca.
FANGY_YAW = 112.0      # gradi: dove sta la testa, dall'occhio
FANGY_DIST = 1.95      # metri, in orizzontale, dall'occhio alla testa
FANGY_SCALA = 1.12     # più grande del modello della tavola: un mastino grosso, la testa all'altezza del bordo


def fangy_posa():
    """La trasformazione della posa fangy_ascolta e i parametri di fangy.build() in coordinate locali (servono anche
    alla vetrina di fangy.py). Fangy gira solo attorno a Z, col corpo verso il pescatore; il mare resta a z = 0."""
    import fangy as fa
    from mathutils import Vector
    a = math.radians(FANGY_YAW)
    h = (EYE[0] + FANGY_DIST * math.sin(a), EYE[1] + FANGY_DIST * math.cos(a), 0.0)
    yaw = facing_yaw(h)
    off = M_of((0.0, 0.0, 0.0), yaw=yaw, scale=FANGY_SCALA) @ Vector(tuple(map(float, fa.HEAD)))
    M = M_of((h[0] - off.x, h[1] - off.y, 0.0), yaw=yaw, scale=FANGY_SCALA)
    loc = lambda p: tuple(round(float(v), 4) for v in to_local(M, p))
    return M, {'viewer': loc(EYE)}


def fangy_ascolta(testa=0.0, luci=1.0):
    """La posa fangy_ascolta; con testa e luci (fangy.build) le varianti delle toppe, nella stessa posa."""
    import fangy as fa
    M, kw = fangy_posa()
    LAST_M['fangy_ascolta'] = M
    return place(fa.build(**kw, testa=testa, luci=luci), M)
