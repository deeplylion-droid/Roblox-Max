"""
Panorami SEGNAPOSTO delle immersioni all'alba (docs/IMMERSIONI.md, «Il motore»): servono solo a provare il motore
finché non arrivano i render veri delle grotte e delle camerette. Brutti di proposito: roccia procedurale, buchi
scuri per i passaggi, una stanza a scatola con un letto e qualche macchia di colore, un mostro-sagoma che dorme.

La grotta grande è un equirettangolare a sfera intera (360° × 180°); sotto la barca (BARCA) e la cameretta (CAM) sono
pezzi di equirettangolare: inquadrature fisse che si girano di 30° per parte (deciso l'11 ottobre). I passi:
  *_ambient.webp   la luce dell'acqua (quasi buio, un po' di chiarore dall'alto)
  *_lantern.webp   la stessa scena accesa dalla torcia del sub (il motore la mostra solo nel cono della torcia)
  *_data.webp      R = sqrt(distanza / 2500 m) (la nebbia dell'acqua torbida), G = quanto trema l'immagine
I valori sono codificati come gli altri render (gamma 4: v = (lineare / scala)^(1/4), scala 1).

Uscita: public/assets/img/immersioni/segnaposto/ (i posti e i passaggi stanno in public/assets/img/immersioni.json;
le posizioni dei buchi qui sotto devono coincidere con quelle).

Uso: tools/.venv/bin/python tools/immersioni_segnaposto.py
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'public', 'assets', 'img', 'immersioni', 'segnaposto')
W, H = 2048, 1024
rng = np.random.default_rng(1997)


def set_grid(w, h, lon0=-180, lon1=180, lat0=-90, lat1=90):
    """La griglia del panorama che si sta facendo: longitudine (0 avanti, + a destra) e latitudine di ogni pixel, e la
    direzione (x destra, y avanti, z su). Sfera intera, o un pezzo (le inquadrature fisse delle camerette)."""
    global W, H, LON, LAT, DX, DY, DZ
    W, H = w, h
    lon = np.radians(lon0 + (np.arange(W) + 0.5) / W * (lon1 - lon0))
    lat = np.radians(lat1 - (np.arange(H) + 0.5) / H * (lat1 - lat0))
    LON, LAT = np.meshgrid(lon, lat)
    DX, DY, DZ = np.cos(LAT) * np.sin(LON), np.cos(LAT) * np.cos(LON), np.sin(LAT)


set_grid(W, H)
# l'inquadratura fissa delle camerette (deciso l'11 ottobre: come le telecamere di FNAF, si gira di 30° per parte):
# 160° × 80° attorno al letto, a 11 pixel per grado
CAM = dict(lon0=-80, lon1=80, lat0=-55, lat1=25)
CAM_PX = 11


def noise(power, seed_shift=0):
    """Rumore 1/f^power periodico in orizzontale (il panorama si richiude senza cuciture), da −1 a 1 circa."""
    fy = np.fft.fftfreq(H)[:, None]
    fx = np.fft.fftfreq(W)[None, :]
    f = np.sqrt(fx ** 2 + (fy * 2) ** 2)
    f[0, 0] = 1.0
    spec = (rng.standard_normal((H, W)) + 1j * rng.standard_normal((H, W))) / f ** power
    spec[0, 0] = 0
    x = np.real(np.fft.ifft2(spec))
    return x / (np.abs(x).max() + 1e-9)


def ang_dist(yaw, pitch):
    """Angolo (radianti) fra ogni pixel e la direzione yaw/pitch (gradi)."""
    a, e = np.radians(yaw), np.radians(pitch)
    v = np.array([np.cos(e) * np.sin(a), np.cos(e) * np.cos(a), np.sin(e)])
    return np.arccos(np.clip(DX * v[0] + DY * v[1] + DZ * v[2], -1, 1))


def enc(lin, scale=1.0):
    return np.clip((np.clip(lin, 0, None) / scale) ** 0.25, 0, 1)


def save(name, rgb, alpha=None):
    os.makedirs(OUT, exist_ok=True)
    a = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    if alpha is not None:
        a = np.dstack([a, (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)])
    Image.fromarray(a).save(os.path.join(OUT, name + '.webp'), quality=82, method=6)


def write_place(name, albedo, dist, sky_light, wobble=0.12, torch=4.0, reach=3.2):
    """Scrive i tre file di un posto. albedo: colore delle superfici (lineare); dist: metri dall'occhio;
    sky_light: luce dall'alto già pronta (lineare), che si somma all'ambiente."""
    # ambiente: un chiarore verde-blu che viene dall'alto, quasi niente sui fondi
    from_above = np.clip(0.25 + 0.75 * DZ, 0, 1) ** 2
    amb = albedo * (0.010 + 0.035 * from_above)[..., None] * np.array([0.55, 0.9, 1.0]) + sky_light
    # torcia: come una lampada sull'occhio, cala col quadrato della distanza
    lant = albedo * (torch / (1 + (dist / reach) ** 2))[..., None] * np.array([1.0, 0.96, 0.85])
    data = np.zeros((H, W, 3))
    data[..., 0] = np.sqrt(np.clip(dist, 0, 2500) / 2500)
    data[..., 1] = wobble
    save(name + '_ambient', enc(amb))
    save(name + '_lantern', enc(lant))
    save(name + '_data', data)


def rock(tint, rough=1.0):
    """Roccia nera con macchie (anemoni, incrostazioni)."""
    n1, n2, n3 = noise(1.1), noise(1.6), noise(0.7)
    base = 0.06 + 0.05 * n1 + 0.03 * n3 * rough
    alb = np.repeat(base[..., None], 3, axis=2) * np.array(tint)
    # incrostazioni chiare e qualche anemone colorato
    crust = np.clip((n2 - 0.35) * 4, 0, 1)
    alb += crust[..., None] * np.array([0.12, 0.13, 0.10])
    anem = np.clip((noise(0.4) - 0.72) * 9, 0, 1)
    alb += anem[..., None] * np.array([0.35, 0.10, 0.16])
    return np.clip(alb, 0, 1)


def holes(alb, dist, spots):
    """Buchi nella roccia (i passaggi): dentro è lontano (la nebbia lo riempie) e scuro; il bordo un po' più chiaro."""
    for yaw, pitch, r, depth in spots:
        a = ang_dist(yaw, pitch)
        rr = np.radians(r)
        inside = np.clip((rr - a) / (rr * 0.25), 0, 1)
        rim = np.exp(-(((a - rr) / (rr * 0.12)) ** 2))
        alb = alb * (1 - 0.85 * inside[..., None]) + rim[..., None] * np.array([0.05, 0.06, 0.05])
        dist = dist * (1 - inside) + depth * inside
    return alb, dist


# l'inquadratura fissa di sotto la barca (deciso l'11 ottobre sera: come le camerette): 160° × 95° verso la parete
BARCA = dict(lon0=-80, lon1=80, lat0=-45, lat1=50)
BARCA_PX = 11


def sotto_barca():
    """Sotto la barca, un'inquadratura fissa (BARCA): davanti la parete di roccia con l'imboccatura della grotta (yaw 0),
    sopra la parete l'acqua aperta che si schiarisce verso la superficie, a sinistra la cima dell'ancora che scende
    dalla barca (yaw −28), sotto il fondo."""
    set_grid((BARCA['lon1'] - BARCA['lon0']) * BARCA_PX, (BARCA['lat1'] - BARCA['lat0']) * BARCA_PX, **BARCA)
    alb = rock([0.9, 1.0, 0.95])
    # la parete davanti a 6 m (alta 4 m sopra l'occhio), il fondo sotto a 5 m; sopra la parete l'acqua aperta
    wall_t = 6.0 / np.maximum(DY, 0.05)
    wall = np.where((DY > 0.05) & (DZ * wall_t < 4.0 + 0.8 * noise(1.1)), wall_t, 80.0)
    floor = np.where(DZ < -0.05, 5.0 / np.maximum(-DZ, 0.05), 80.0)
    dist = np.minimum(np.minimum(wall, floor), 60.0) * (1 + 0.15 * noise(1.3))
    open_water = dist > 30
    alb[open_water] *= 0.1
    alb, dist = holes(alb, dist, [(0, -6, 13, 45)])
    # l'acqua aperta si schiarisce salendo verso la superficie, e tremola
    surf = np.clip((DZ - 0.25) / 0.55, 0, 1) ** 2 * (0.6 + 0.4 * noise(0.9)) * 0.5 * open_water
    sky = surf[..., None] * np.array([0.35, 0.75, 0.8])
    # la cima dell'ancora: una riga chiara che scende dalla barca fino al fondo, a 2,5 m
    rope = np.exp(-(((LON - np.radians(-28)) / 0.008) ** 2))
    alb = alb * (1 - rope[..., None]) + rope[..., None] * np.array([0.45, 0.40, 0.30])
    dist = np.where(rope > 0.5, 2.5, dist)
    write_place('sotto_barca', alb, dist, sky)


GROTTA_BUCHI = [
    # (yaw, pitch, raggio, profondità): l'uscita verso la barca, il fondo della Madre, le sette tane
    (180, 0, 12, 50),     # verso sotto la barca
    (0, -4, 22, 400),     # il fondo della grotta grande (la Madre: non ci si entra)
    (-40, -8, 8, 40),     # tana di Gulpy
    (40, -8, 8, 40),      # Molly
    (-80, -5, 8, 40),     # Hatch
    (80, -5, 8, 40),      # Robin
    (-120, -6, 8, 40),    # Archie
    (120, -6, 8, 40),     # Lampy
    (-152, -4, 7, 40),    # Fangy
]


def grotta_grande():
    """La grotta grande: una sala chiusa con un buco per ogni tana, l'uscita alle spalle e il fondo enorme davanti."""
    set_grid(2048, 1024)
    alb = rock([0.85, 0.95, 1.0], rough=1.4)
    # una sala schiacciata di circa 7 m di raggio, il soffitto più basso, la roccia irregolare
    r = 7.0 * (1 + 0.25 * noise(1.2))
    dist = r / np.sqrt(DX ** 2 + DY ** 2 + (DZ * 1.8) ** 2)
    alb, dist = holes(alb, dist, GROTTA_BUCHI)
    # una fessura nel soffitto da cui scende un po' di luce
    crack = np.exp(-(ang_dist(30, 80) / 0.07) ** 2)
    sky = crack[..., None] * np.array([0.25, 0.55, 0.6]) * 0.6
    write_place('grotta_grande', alb, dist, sky)


def cameretta():
    """Una «cameretta» qualsiasi a scatola, sommersa: carta da parati a righe sbiadite, il pavimento di melma, un letto
    davanti in basso (yaw 0), qualche giocattolo colorato. Il motore la tinge per ogni tana. È un'inquadratura fissa
    (CAM), non un panorama intero."""
    set_grid((CAM['lon1'] - CAM['lon0']) * CAM_PX, (CAM['lat1'] - CAM['lat0']) * CAM_PX, **CAM)
    hx, hy, up, dn = 2.6, 2.6, 1.5, 1.2
    tx = hx / np.maximum(np.abs(DX), 1e-4)
    ty = hy / np.maximum(np.abs(DY), 1e-4)
    tz = np.where(DZ > 0, up / np.maximum(DZ, 1e-4), dn / np.maximum(-DZ, 1e-4))
    dist = np.minimum(np.minimum(tx, ty), tz)
    px, py, pz = DX * dist, DY * dist, DZ * dist
    n = noise(1.2)
    # pareti: righe verticali (lungo la coordinata orizzontale della parete)
    u = np.where(tx < ty, py, px)
    stripes = 0.5 + 0.5 * np.sign(np.sin(u * 9))
    wall = np.stack([0.16 + 0.06 * stripes, 0.12 + 0.03 * stripes, 0.14 + 0.07 * stripes], -1)
    alb = wall * (0.8 + 0.3 * n[..., None])
    floor = (tz < np.minimum(tx, ty)) & (DZ < 0)
    alb[floor] = np.array([0.06, 0.08, 0.05]) * (0.8 + 0.4 * n[floor][..., None])
    ceil = (tz < np.minimum(tx, ty)) & (DZ > 0)
    alb[ceil] = np.array([0.08, 0.09, 0.09])
    # il letto: una scatola bassa davanti (y da 1,0 a 2,4 m, x ±0,8, alto 0,5 dal pavimento)
    bed = (py > 1.0) & (py < 2.5) & (np.abs(px) < 0.9) & (pz < -dn + 0.55)
    t_bed = np.where(DZ < 0, (dn - 0.55) / np.maximum(-DZ, 1e-4), 99)
    bx, by = DX * t_bed, DY * t_bed
    top = (bx > -0.9) & (bx < 0.9) & (by > 1.0) & (by < 2.5) & (t_bed < dist)
    alb[top] = np.array([0.30, 0.28, 0.22])
    dist = np.where(top, t_bed, dist)
    del bed
    # macchie di colore: i giocattoli e le cose del bambino (gialle, fucsia, turchesi) sparse sul pavimento e sulle pareti
    for i in range(14):
        yaw, pitch = rng.uniform(-180, 180), rng.uniform(-45, 10)
        col = [np.array([0.6, 0.45, 0.05]), np.array([0.55, 0.08, 0.3]), np.array([0.05, 0.45, 0.45])][i % 3]
        m = np.exp(-(ang_dist(yaw, pitch) / np.radians(rng.uniform(1.5, 4))) ** 2)
        alb = alb * (1 - m[..., None]) + m[..., None] * col
    # alghe e melma a chiazze su tutto
    slime = np.clip((noise(0.9) - 0.2) * 2, 0, 1)
    alb = alb * (1 - 0.5 * slime[..., None]) + slime[..., None] * np.array([0.03, 0.06, 0.03])
    sky = np.zeros_like(alb)
    write_place('cameretta', alb, dist, sky, wobble=0.1, torch=1.6, reach=2.2)


def dormiente():
    """Il mostro addormentato sul letto (yaw 0, pitch circa −28): una sagoma lunga e grigia raggomitolata, con due
    occhi chiusi più chiari; e la «toppa» del respiro (la stessa sagoma un poco gonfiata) che il motore dissolve sopra.
    Ritaglio del panorama della cameretta: il riquadro va scritto in immersioni.json (rect)."""
    set_grid((CAM['lon1'] - CAM['lon0']) * CAM_PX, (CAM['lat1'] - CAM['lat0']) * CAM_PX, **CAM)
    # il riquadro: da −30° a 30° di longitudine, da −10° a −45° di latitudine
    x0, x1 = (-30 - CAM['lon0']) * CAM_PX, (30 - CAM['lon0']) * CAM_PX
    y0, y1 = (CAM['lat1'] + 10) * CAM_PX, (CAM['lat1'] + 45) * CAM_PX
    sl = (slice(y0, y1), slice(x0, x1))
    L, A = np.degrees(LON[sl]), np.degrees(LAT[sl])
    out = {}
    for name, k in (('dormiente', 1.0), ('dormiente_respiro', 1.06)):
        # un corpo a fagiolo e una testa
        body = ((L / (17 * k)) ** 2 + ((A + 29 + 0.012 * L ** 2) / (6.5 * k)) ** 2) < 1
        head = (((L + 15) / (6 * k)) ** 2 + ((A + 24) / (5 * k)) ** 2) < 1
        m = (body | head).astype(float)
        shade = 0.10 + 0.05 * noise(1.0)[sl]
        col = np.stack([shade * 0.9, shade, shade * 0.95], -1)
        eyes = np.zeros_like(L)
        for ex in (-17.5, -12.5):
            eyes += np.exp(-(((L - ex) / 1.1) ** 2 + ((A + 23.5) / 0.35) ** 2))
        col += eyes[..., None] * np.array([0.25, 0.25, 0.22])
        dd = 2.2
        amb = col * 0.03
        lant = col * (1.6 / (1 + (dd / 2.2) ** 2))
        save(name + '_ambient', enc(amb), m)
        save(name + '_lantern', enc(lant), m)
        out[name] = (x0, y0, x1, y1)
    print('riquadro della dormiente nel panorama (rect per immersioni.json):', out['dormiente'])


if __name__ == '__main__':
    sotto_barca()
    grotta_grande()
    cameretta()
    dormiente()
    print('fatto:', OUT)
