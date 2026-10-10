"""
Le piccole animazioni dei mostri sulla barca (approvate dall'utente il 10 ottobre): le «toppe» di gulpy_pretende,
molly_destra / molly_sinistra e hatch_conta.

Il gioco le fa alternando lentamente delle toppe: la stessa posa di gioco resa con una variante del modello, con
visibile solo la testa (il resto della creatura fa da maschera, come la barca), lo strato ritagliato sulla testa e
dissolto sopra lo strato principale (vedi jobs.job_creature: le opzioni 'visibili', 'occhi', 'yaw_di').

    gulpy_mascella_chiusa    Gulpy con la mascella sganciata un po' più chiusa (gulpy.build(mascella=−10)) …
    gulpy_mascella_aperta    … e un po' più aperta (+10): alternate piano, la mascella che pende ondeggia.
                             Il pescatore vede la faccia da molto sopra il suo asse (la testa pende): la mascella
                             più chiusa gli viene incontro e mostra più bocca, la più aperta va indietro verso il
                             petto e la bocca sembra più stretta
    molly_destra_primo       Molly sul bordo destro col primo occhio chiuso: quello che ti fissa (molly.EYES[0])
    molly_destra_secondo     … col secondo chiuso: quello che scivola via (EYES[1]); il gioco lo chiude dopo il
                             primo, in ritardo, storto (molly.build(palpebre=(1, 0)) e (0, 1))
    molly_sinistra_primo     lo stesso sul bordo sinistro
    molly_sinistra_secondo
    hatch_bocca_mezza        Hatch con la bocca mezza chiusa (hatch.build(bocca=0,5)) …
    hatch_bocca_chiusa       … e chiusa, resta una fessura (bocca=0): da alternare a ogni numero della conta
    archie_trombetta_mezza   Archie (notte 3) che prende fiato nella trombetta: la carta si srotola a metà
                             (archie.build(srotolata=0,5)) …
    archie_trombetta_tutta   … e tutta, distesa sulla lampara con la piuma in punta (srotolata=1): sulla barca il gioco
                             la srotola a metà e la riavvolge (la posa, archie_soffia, la tiene arrotolata); quella tutta
                             distesa è il soffio

Ogni funzione costruisce la creatura nella STESSA posizione della posa di gioco e restituisce (tutti gli oggetti
della creatura, gli oggetti della testa da tenere visibili). La sistemazione è copiata da scena_creature
(gulpy_pretende, molly, hatch_conta), che non accettano i parametri nuovi: se la posa cambia là va cambiata anche
qui. Se la posa principale è già stata costruita nella stessa sessione (scena_creature.LAST_M), le funzioni
controllano che la trasformazione sia la stessa e si fermano se non lo è. Archie fa eccezione: la sua posa
(scena_creature.archie_soffia) accetta già i parametri delle varianti, e qui si usa quella.
Con i parametri a riposo i modelli sono identici a prima, e nelle varianti cambiano solo i pezzi della testa
(GULPY_TESTA, MOLLY_TESTA, HATCH_TESTA): il corpo resta lo stesso, quindi le maschere combaciano.

TOPPE ha le voci pronte per scena_creature.POSES (POSES.update(pose_animate.TOPPE)), con lo spazio e il mare della
posa principale.

Attenzione, le mascelle: la palpebra di Molly sta tutta dentro la sagoma della testa, ma la mascella di Hatch che sale
(il contorno di sotto della testa sale di 22-34 pixel del panorama finale a bocca mezza, di 48-73 a bocca chiusa) e
quella di Gulpy che va indietro (+10°: il mento sale di ~40 pixel) scoprono una striscia che nello strato principale
era mascella: una toppa con la sola testa, disegnata sopra lo strato principale, lì lascerebbe vedere la mascella
vecchia. Dietro quella striscia c'è quasi solo il corpo (collo, petto, spalle): basta rendere visibile nella toppa
anche il corpo (GULPY_CORPO, HATCH_CORPO) tenendo il riquadro sulla sola testa (jobs.render_sprite ha già rect_objs),
e nel gioco far sfumare lo strato principale dentro il riquadro mentre entra la toppa. La mascella di Gulpy più chiusa
(−10°) invece copre di più e non scopre niente. Lo stesso per la trombetta di Archie: srotolandosi lascia vuoto il
posto della spirale, quindi nelle sue toppe si vede anche il collo (ARCHIE_CORPO) col riquadro sulla testa.

Anteprime, dall'occhio del pescatore e strette sulla testa, la posa di base accanto alle varianti:
    nice -n 10 tools/.venv/bin/python tools/render/pose_animate.py [gulpy] [molly] [hatch] [archie] [--fast] [--tavole]
    → docs/concept/animazioni/gulpy_mascella.jpg, molly_occhi.jpg (i due lati), hatch_bocca.jpg, archie_trombetta.jpg
"""
from __future__ import annotations

import fnmatch
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import scena_creature as SC  # noqa: E402
from common import CACHE, EYE, ROOT  # noqa: E402

F = np.float32
FAST = '--fast' in sys.argv

# le varianti
GULPY_MASCELLA = {'chiusa': -10.0, 'aperta': 10.0}   # gradi attorno alla cerniera (+ apre)
MOLLY_PRIMO = 0                                      # l'occhio che si chiude per primo (molly.EYES): quello che ti fissa
HATCH_BOCCA = {'mezza': 0.5, 'chiusa': 0.0}          # apertura (1 com'è)
ARCHIE_TROMBETTA = {'mezza': 0.5, 'tutta': 1.0}      # quanto è srotolata la trombetta (0 com'è, arrotolata)

# gli oggetti della testa: quello che cambia e quello che sta dentro la faccia (così la toppa non ha buchi);
# il resto della creatura fa da maschera
GULPY_TESTA = ('GulpyHead', 'GulpyEye*', 'GulpyThroat', 'GulpyTeeth', 'GulpySlimeMouth')
MOLLY_TESTA = ('MollyHead', 'MollyEye*', 'MollyBeak', 'MollySlimeMouth')
HATCH_TESTA = ('HatchHead', 'HatchEye*', 'HatchTeeth', 'HatchSlime')
# il corpo dietro le mascelle (vedi sopra, «Attenzione, le mascelle»)
GULPY_CORPO = ('GulpyBody',)
HATCH_CORPO = ('HatchBody',)
# Archie: la testa con la trombetta, e il collo dietro (scena_creature.ARCHIE_TESTA e ARCHIE_CORPO)
ARCHIE_TESTA = SC.ARCHIE_TESTA
ARCHIE_CORPO = SC.ARCHIE_CORPO


def _base(name):
    """Il nome senza il .001 dei doppioni (una creatura costruita più volte nella stessa scena)."""
    head, dot, tail = name.rpartition('.')
    return head if dot and tail.isdigit() else name


def _testa(obs, nomi):
    return [o for o in obs if o.type == 'MESH' and any(fnmatch.fnmatchcase(_base(o.name), n) for n in nomi)]


def _stessa_posa(key, M):
    """Se la posa principale è già stata costruita in questa sessione, la sua trasformazione deve essere M."""
    M0 = SC.LAST_M.get(key)
    if M0 is not None and max(abs(M0[i][j] - M[i][j]) for i in range(4) for j in range(4)) > 1e-5:
        raise RuntimeError(f'la posa {key} in scena_creature.py non è più quella copiata in pose_animate.py: '
                           'aggiorna la sistemazione qui')


# ───────────────────────── le pose, con i parametri nuovi ─────────────────────────

def gulpy_pretende(mascella=0.0):
    """Come scena_creature.gulpy_pretende (Gulpy sporto sulla prua, le mani sul bordo), con la mascella ruotata."""
    import gulpy
    o = (-1.9, 3.4, -0.4)
    M = SC.M_of(o, yaw=SC.facing_yaw(o), pitch=25.0, scale=SC.GULPY_SCALE)
    _stessa_posa('gulpy_pretende', M)
    # una mano sul capodibanda di sinistra, l'altra sulla punta di prua
    xg, zg = SC.gunwale_at(1.2, -1)
    xb, zb = SC.gunwale_at(2.45, -1)
    grip = [SC.to_local(M, (xg + 0.02, 1.2, zg)), SC.to_local(M, (xb + 0.04, 2.45, zb))]
    lo = np.minimum(np.array((-0.62, -1.0, -0.02), F), np.min(grip, axis=0) - 0.25)
    hi = np.maximum(np.array((0.62, 0.48, 2.72), F), np.max(grip, axis=0) + 0.25)
    obs = gulpy.build(grip=grip, viewer=SC.to_local(M, EYE), lo=lo, hi=hi, mascella=mascella)
    SC.place(obs, M)
    return obs, _testa(obs, GULPY_TESTA)


def molly(side, palpebre=(0.0, 0.0)):
    """Come scena_creature.molly(side) (+1 bordo destro, −1 sinistro), con gli occhi chiusi per 'palpebre'."""
    import molly as mo
    y = -0.26 if side > 0 else 0.15
    xc, ztop = SC.gunwale_at(y, side)
    M = SC.M_of((xc, y, ztop - mo.GUN_TOP), yaw=-90.0 if side > 0 else 90.0)
    _stessa_posa('molly_destra' if side > 0 else 'molly_sinistra', M)
    v = SC.to_local(M, EYE)
    d = v - mo.C
    turn = max(-35.0, min(35.0, math.degrees(math.atan2(float(d[0]), float(-d[1])))))
    obs = mo.build(viewer=v, head_turn=turn, palpebre=palpebre)
    SC.place(obs, M)
    return obs, _testa(obs, MOLLY_TESTA)


def hatch_conta(bocca=1.0):
    """Come scena_creature.hatch_conta (dietro la poppa, piegato sulla barca), con la bocca aperta per 'bocca'."""
    import hatch
    # appena dietro la poppa, altissimo, piegato sulla barca: l'esca gli penzola sopra il ponte di poppa
    o = (0.10, -3.45, -1.05)
    M = SC.M_of(o, yaw=SC.facing_yaw(o), pitch=14.0)
    _stessa_posa('hatch_conta', M)
    before = set(bpy.data.objects.keys())
    obs = hatch.build(viewer=SC.to_local(M, EYE), bocca=bocca)
    # la luce dell'esca di questa costruzione (non quella di un Hatch costruito prima nella stessa scena)
    lights = [bpy.data.objects[n] for n in bpy.data.objects.keys()
              if n not in before and bpy.data.objects[n].type == 'LIGHT' and n.startswith('ToyLight')]
    # di notte, a qualche metro, lo illumina solo la sua esca: più forte che in vetrina
    for li in lights:
        li.data.energy = 9.0
        li.data.shadow_soft_size = 0.035
    SC.place(obs + lights, M)
    return obs + lights, _testa(obs, HATCH_TESTA)


# ───────────────────────── le varianti (le toppe) ─────────────────────────

def gulpy_mascella_chiusa():
    return gulpy_pretende(mascella=GULPY_MASCELLA['chiusa'])


def gulpy_mascella_aperta():
    return gulpy_pretende(mascella=GULPY_MASCELLA['aperta'])


def _occhio(i):
    return tuple(1.0 if k == i else 0.0 for k in range(2))


def molly_destra_primo():
    return molly(+1, _occhio(MOLLY_PRIMO))


def molly_destra_secondo():
    return molly(+1, _occhio(1 - MOLLY_PRIMO))


def molly_sinistra_primo():
    return molly(-1, _occhio(MOLLY_PRIMO))


def molly_sinistra_secondo():
    return molly(-1, _occhio(1 - MOLLY_PRIMO))


def hatch_bocca_mezza():
    return hatch_conta(bocca=HATCH_BOCCA['mezza'])


def hatch_bocca_chiusa():
    return hatch_conta(bocca=HATCH_BOCCA['chiusa'])


def archie_soffia(srotolata=0.0):
    """Come scena_creature.archie_soffia (accanto alla lampara), con la trombetta srotolata per 'srotolata': la posa
    accetta già il parametro, quindi qui non c'è niente da copiare."""
    obs = SC.archie_soffia(srotolata=srotolata)
    return obs, _testa(obs, ARCHIE_TESTA)


def archie_trombetta_mezza():
    return archie_soffia(srotolata=ARCHIE_TROMBETTA['mezza'])


def archie_trombetta_tutta():
    return archie_soffia(srotolata=ARCHIE_TROMBETTA['tutta'])


def _toppa(fn, base, testa, corpo=()):
    """La voce di una toppa. Con corpo (le mascelle): nella toppa si vede anche il corpo dietro la testa, perché la
    mascella che si sposta scopre una striscia che nello strato principale era mascella; il riquadro resta sulla
    sola testa, e il gioco sfuma lo strato principale dove la toppa è vuota (lo sfondo)."""
    space, sea = SC.POSES[base][1:3]
    opts = {'visibili': tuple(testa) + tuple(corpo), 'occhi': False, 'yaw_di': base}
    if corpo:
        opts['riquadro'] = testa
    return (fn, space, sea, opts)


# chiave → (funzione, spazio, mare, opzioni), come le voci di scena_creature.POSES (vedi jobs.job_creature)
TOPPE = {
    'gulpy_mascella_chiusa': _toppa(gulpy_mascella_chiusa, 'gulpy_pretende', GULPY_TESTA, GULPY_CORPO),
    'gulpy_mascella_aperta': _toppa(gulpy_mascella_aperta, 'gulpy_pretende', GULPY_TESTA, GULPY_CORPO),
    'molly_destra_primo': _toppa(molly_destra_primo, 'molly_destra', MOLLY_TESTA),
    'molly_destra_secondo': _toppa(molly_destra_secondo, 'molly_destra', MOLLY_TESTA),
    'molly_sinistra_primo': _toppa(molly_sinistra_primo, 'molly_sinistra', MOLLY_TESTA),
    'molly_sinistra_secondo': _toppa(molly_sinistra_secondo, 'molly_sinistra', MOLLY_TESTA),
    'hatch_bocca_mezza': _toppa(hatch_bocca_mezza, 'hatch_conta', HATCH_TESTA, HATCH_CORPO),
    'hatch_bocca_chiusa': _toppa(hatch_bocca_chiusa, 'hatch_conta', HATCH_TESTA, HATCH_CORPO),
    'archie_trombetta_mezza': _toppa(archie_trombetta_mezza, 'archie_soffia', ARCHIE_TESTA, ARCHIE_CORPO),
    'archie_trombetta_tutta': _toppa(archie_trombetta_tutta, 'archie_soffia', ARCHIE_TESTA, ARCHIE_CORPO),
}


# ───────────────────────── anteprime ─────────────────────────

def _num(x):
    return f'{x:g}'.replace('.', ',').replace('-', '−')


def _posa_di_gioco(fn, testa):
    """La posa principale vera (scena_creature), con gli oggetti della testa: è la base delle anteprime e, costruita
    prima delle varianti, fa controllare a queste di stare nella stessa trasformazione."""
    def f():
        obs = fn()
        return obs, _testa(obs, testa)
    return f


# su che cosa si stringe la camera, se non su tutta la testa (la pelle della testa di Gulpy arriva fino al salvagente)
INQUADRA = {'gulpy': ('GulpyEye*', 'GulpyTeeth', 'GulpyThroat', 'GulpySlimeMouth'),
            # Archie: la testa e la trombetta, che nella prima variante costruita (tutta distesa) arriva alla lampara
            'archie': ('ArchieHead', 'ArchieMouthpiece', 'ArchieBlower', 'ArchieFeather')}

# per ogni anteprima: (nome del file, righe, nota); ogni riga è (titolo della riga, [(titolo, funzione che costruisce
# la posa, colonna)]); la base si costruisce per prima (la camera si punta su di lei)
ANTEPRIME = {
    'gulpy': ('gulpy_mascella', [
        ('', [('posa di base · gulpy_pretende', _posa_di_gioco(SC.gulpy_pretende, GULPY_TESTA), 1),
              (f'mascella più chiusa ({_num(GULPY_MASCELLA["chiusa"])}°) · gulpy_mascella_chiusa', gulpy_mascella_chiusa, 0),
              (f'mascella più aperta (+{_num(GULPY_MASCELLA["aperta"])}°) · gulpy_mascella_aperta', gulpy_mascella_aperta, 2)]),
    ], 'Da qui la faccia si vede molto dall\'alto: la mascella più chiusa viene in avanti, verso di te, e mostra più bocca; '
       'la più aperta va indietro verso il petto e la bocca sembra più stretta.'),
    'molly': ('molly_occhi', [
        ('bordo destro', [('posa di base · molly_destra', _posa_di_gioco(lambda: SC.molly(+1), MOLLY_TESTA), 0),
                          ('primo occhio chiuso · molly_destra_primo', molly_destra_primo, 1),
                          ('secondo occhio chiuso · molly_destra_secondo', molly_destra_secondo, 2)]),
        ('bordo sinistro', [('posa di base · molly_sinistra', _posa_di_gioco(lambda: SC.molly(-1), MOLLY_TESTA), 0),
                            ('primo occhio chiuso · molly_sinistra_primo', molly_sinistra_primo, 1),
                            ('secondo occhio chiuso · molly_sinistra_secondo', molly_sinistra_secondo, 2)]),
    ], 'Il primo occhio è quello che ti fissa (a sinistra), il secondo quello che scivola via.'),
    'hatch': ('hatch_bocca', [
        ('', [('posa di base · hatch_conta', _posa_di_gioco(SC.hatch_conta, HATCH_TESTA), 0),
              (f'bocca mezza chiusa ({_num(HATCH_BOCCA["mezza"])}) · hatch_bocca_mezza', hatch_bocca_mezza, 1),
              (f'bocca chiusa ({_num(HATCH_BOCCA["chiusa"])}) · hatch_bocca_chiusa', hatch_bocca_chiusa, 2)]),
    ], 'La mascella sale ruotando dietro la testa; i denti di vetro di sotto si ripiegano dentro la bocca.'),
    # la variante tutta distesa si costruisce per prima: la camera deve tenere dentro la trombetta fino alla lampara
    'archie': ('archie_trombetta', [
        ('', [(f'tutta srotolata ({_num(ARCHIE_TROMBETTA["tutta"])}) · archie_trombetta_tutta', archie_trombetta_tutta, 2),
              ('posa di base, arrotolata · archie_soffia', _posa_di_gioco(SC.archie_soffia, ARCHIE_TESTA), 0),
              (f'srotolata a metà ({_num(ARCHIE_TROMBETTA["mezza"])}) · archie_trombetta_mezza', archie_trombetta_mezza, 1),
              ('prende fiato, la gola gonfia · archie_fiato', _posa_di_gioco(lambda: SC.archie_soffia(fiato=1.0), ARCHIE_TESTA), 3)]),
    ], 'Sulla barca prende fiato nella trombetta: la carta si srotola a metà e si riavvolge, piano. Tutta distesa sulla '
       'lampara è il soffio; la gola gonfia (archie_fiato, in scena_creature) è il risucchio lungo prima di soffiare.'),
}


def _inquadra(objs, size, margin=1.22, name='AnimCam'):
    """Camera nell'occhio del pescatore puntata sul centro della testa, con l'obiettivo che la fa stare nel quadro."""
    import jobs
    from common import perspective_camera
    from mathutils import Vector
    pts = np.array(jobs.dense_points(objs, n=800))
    c = (pts.min(0) + pts.max(0)) / 2
    cam = perspective_camera(EYE, tuple(map(float, c)), lens=50.0, name=name)
    bpy.context.view_layer.update()
    R = cam.matrix_world.to_3x3()
    right, up, fwd = R.col[0], R.col[1], -R.col[2]
    t = 0.0
    W, H = size
    for p in pts:
        d = Vector(tuple(map(float, p))) - Vector(EYE)
        z = d.dot(fwd)
        t = max(t, abs(d.dot(right)) / z, abs(d.dot(up)) / z * W / H)
    cam.data.lens = 18.0 / (t * margin)
    return cam


TMP = os.path.join(CACHE, 'animazioni')
OUT_DIR = os.path.join(ROOT, 'docs', 'concept', 'animazioni')


def _pannello(nome, r, k):
    return os.path.join(TMP, f'{nome}_{r}_{k}.png')


def _tavola(who, size=(440, 440)):
    """Compone la tavola di un'anteprima dai pannelli già resi (in cache/animazioni)."""
    from PIL import Image, ImageDraw, ImageFont
    nome, righe, nota = ANTEPRIME[who]
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
        font_b = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
    except OSError:
        font = font_b = ImageFont.load_default()
    tavola = [(titolo_riga, sorted((col, _pannello(nome, r, k), titolo) for k, (titolo, _, col) in enumerate(pannelli)))
              for r, (titolo_riga, pannelli) in enumerate(righe)]
    W, H = size
    pad, cap, head, line = 8, 30, 26, 20
    cols = max(len(r) for _, r in tavola)
    width = cols * W + (cols + 1) * pad
    # la nota va a capo se non ci sta
    righe_nota, cur = [], ''
    for parola in (nota or '').split():
        prova = (cur + ' ' + parola).strip()
        if cur and font.getlength(prova) > width - 2 * pad - 8:
            righe_nota.append(cur)
            cur = parola
        else:
            cur = prova
    if cur:
        righe_nota.append(cur)
    has_head = any(t for t, _ in tavola)
    rh = H + cap + (head if has_head else 0)
    foot = line * len(righe_nota) + (6 if righe_nota else 0)
    sheet = Image.new('RGB', (width, len(tavola) * rh + (len(tavola) + 1) * pad + foot), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    for r, (titolo_riga, riga) in enumerate(tavola):
        y = pad + r * (rh + pad)
        if has_head:
            d.text((pad + 4, y + 3), titolo_riga, fill=(240, 190, 110), font=font_b)
            y += head
        for i, (_, path, titolo) in enumerate(riga):
            x = pad + i * (W + pad)
            sheet.paste(Image.open(path).convert('RGB'), (x, y))
            d.text((x + 4, y + H + 7), titolo, fill=(225, 225, 220), font=font)
    for i, t in enumerate(righe_nota):
        d.text((pad + 4, sheet.height - foot + i * line), t, fill=(170, 170, 165), font=font)
    os.makedirs(OUT_DIR, exist_ok=True)
    dst = os.path.join(OUT_DIR, f'{nome}.jpg')
    sheet.save(dst, quality=90)
    print('anteprima', dst, flush=True)
    return dst


def anteprime(chi=('gulpy', 'molly', 'hatch'), size=(440, 440)):
    """Le anteprime delle toppe nella scena del gioco: per ogni riga la posa di base e le varianti, viste
    dall'occhio del pescatore con la stessa camera stretta sulla testa. → docs/concept/animazioni/<nome>.jpg
    (i pannelli in cache/animazioni; con --tavole si ricompongono soltanto le tavole da lì)."""
    import jobs
    os.makedirs(TMP, exist_ok=True)
    done = []
    for who in chi:
        nome, righe, _ = ANTEPRIME[who]
        jobs.build_scene(fish=0, rod=False)
        sc = bpy.context.scene
        sc.cycles.use_denoising = True
        sc.render.use_compositing = False
        sc.render.image_settings.file_format = 'PNG'
        sc.render.resolution_percentage = 100
        sc.render.resolution_x, sc.render.resolution_y = size
        sc.cycles.samples = 32 if FAST else 96
        for r, (_, pannelli) in enumerate(righe):
            cam = None
            for k, (titolo, fn, col) in enumerate(pannelli):
                before = set(bpy.data.objects.keys())
                obs, testa = fn()
                bpy.context.view_layer.update()
                new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
                if cam is None:
                    # la stessa camera per tutta la riga (le varianti stanno nello stesso posto)
                    fuoco = _testa(testa, INQUADRA[who]) if who in INQUADRA else testa
                    cam = _inquadra(fuoco, size, margin=1.4 if who in INQUADRA else 1.22, name=f'AnimCam_{nome}_{r}')
                sc.camera = cam
                path = _pannello(nome, r, k)
                sc.render.filepath = path
                bpy.ops.render.render(write_still=True)
                print('pannello', path, flush=True)
                for o in new:
                    o.hide_render = True
        done.append(_tavola(who, size))
    return done


if __name__ == '__main__':
    scelte = tuple(a for a in sys.argv[1:] if a in ANTEPRIME) or ('gulpy', 'molly', 'hatch')
    if '--tavole' in sys.argv:
        for w in scelte:
            _tavola(w)
    else:
        anteprime(scelte)
