"""
Le immagini della pagina Steam e della libreria (scelta dell'utente del 13 ottobre fra tre proposte: la A, Molly che si
affaccia dal bordo della barca, col logo al neon; approvate il 13 ottobre). Escono in steam/, fuori dal gioco; cosa sono
e dove vanno lo dice steam/LEGGIMI.md.

Due passi:
  render <ritratti.blend>   i render di Molly, con la scena, la posa e le luci del ritratto del menu (ritratti.py; la
                            scena si fa con `ritratti.py scena <blend> molly`): quello del menu (1920×1080), uno verticale
                            (1200×1800, lei in basso e il buio sopra per il logo) in steam/sorgenti/, e l'immagine
                            larga della libreria (3840×1240, obiettivo 16 mm, lei a destra) in steam/libreria/
  componi                   le capsule e il logo della libreria, da steam/sorgenti/ e dal logo del gioco
                            (public/assets/img/logo/logo.webp, tools/render/logo.py)
  itch                      la copertina della pagina itch.io (630×500, itch/LEGGIMI.md): il render verticale, il logo
                            in alto nel buio e la faccia di Molly sotto

Il logo si posa in luce, con la fusione «schermo», come la luce di un'insegna vera; dove sta il logo l'immagine si
scurisce un po' (il buio del lago, come nel menu).

Uso: tools/.venv/bin/python tools/render/steam.py render <blend>
     tools/.venv/bin/python tools/render/steam.py componi
     tools/.venv/bin/python tools/render/steam.py itch
"""
import os
import subprocess
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.dirname(os.path.dirname(QUI))
STEAM = os.path.join(RADICE, 'steam')
SORGENTI = os.path.join(STEAM, 'sorgenti')
ITCH = os.path.join(RADICE, 'itch')
LOGO = os.path.join(RADICE, 'public', 'assets', 'img', 'logo', 'logo.webp')

# i render di Molly: uscita, misura, campioni, obiettivo (mm), dove sta la faccia (dx: frazione della larghezza a destra
# del centro) e quanto più in alto guarda la camera (ty, m: la faccia scende nel quadro)
RENDER = (
    (os.path.join(SORGENTI, 'molly_ritratto.png'), 1920, 1080, 40, 28.0, 0.17, 0.0),
    (os.path.join(SORGENTI, 'molly_verticale.png'), 1200, 1800, 48, 28.0, 0.0, 0.16),
    (os.path.join(STEAM, 'libreria', 'immagine_3840x1240.png'), 3840, 1240, 48, 16.0, 0.18, 0.0),
)


def render(blend):
    """Un processo per render (bpy apre la scena ogni volta)."""
    os.makedirs(SORGENTI, exist_ok=True)
    os.makedirs(os.path.join(STEAM, 'libreria'), exist_ok=True)
    for out, W, H, S, lens, dx, ty in RENDER:
        codice = (f'import sys; sys.path.insert(0, {QUI!r}); import ritratti; '
                  f"ritratti.CAMERE['molly'] = dict(ritratti.CAMERE['molly'], lens={lens}, dx={dx}, ty={ty}); "
                  f"ritratti.rendi({os.path.abspath(blend)!r}, 'molly', {out!r}, {W}, {H}, {S})")
        subprocess.run([sys.executable, '-c', codice], check=True)
        # il render lascia accanto l'EXR dei passi: non serve
        exr = os.path.splitext(out)[0] + '.exr'
        if os.path.exists(exr):
            os.remove(exr)
        print('render', out, flush=True)


def componi(solo_itch=False):
    import numpy as np
    from PIL import Image

    logo_im = Image.open(LOGO).convert('RGBA')

    def apri(nome):
        return Image.open(os.path.join(SORGENTI, nome)).convert('RGB')

    def copri(im, W, H, fx=0.5, fy=0.5):
        """Ridimensiona a coprire W×H e ritaglia attorno a (fx, fy) (frazioni dell'immagine)."""
        k = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        x0 = min(max(0, round(im.width * fx - W / 2)), im.width - W)
        y0 = min(max(0, round(im.height * fy - H / 2)), im.height - H)
        return np.asarray(im.crop((x0, y0, x0 + W, y0 + H))).astype(np.float32) / 255

    def buio_sinistra(a, fino, forza):
        x = np.linspace(0, 1, a.shape[1])[None, :, None]
        return a * (1 - np.clip(1 - x / fino, 0, 1) ** 1.5 * forza)

    def buio_alto(a, fino, forza):
        y = np.linspace(0, 1, a.shape[0])[:, None, None]
        return a * (1 - np.clip(1 - y / fino, 0, 1) ** 1.5 * forza)

    def logo(a, x, y, larg, luce=1.0):
        """Il logo con l'angolo in alto a sinistra in (x, y) e largo `larg` (frazioni), in luce; il bagliore che esce
        dall'immagine si taglia."""
        H, W, _ = a.shape
        lw = round(W * larg)
        lh = round(logo_im.height * lw / logo_im.width)
        l = np.asarray(logo_im.resize((lw, lh), Image.LANCZOS)).astype(np.float32) / 255
        L = l[..., :3] * l[..., 3:4] * luce
        x0, y0 = round(W * x), round(H * y)
        L = L[max(0, -y0):, max(0, -x0):]
        x0, y0 = max(0, x0), max(0, y0)
        reg = a[y0:y0 + L.shape[0], x0:x0 + L.shape[1]]
        L = L[:reg.shape[0], :reg.shape[1]]
        a[y0:y0 + L.shape[0], x0:x0 + L.shape[1]] = 1 - (1 - reg) * (1 - L)
        return a

    def salva(a, *percorso, dove=STEAM):
        p = os.path.join(dove, *percorso)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(p, optimize=True)
        print('immagine', os.path.relpath(p, RADICE), flush=True)

    ritratto = apri('molly_ritratto.png')
    verticale = apri('molly_verticale.png')
    # la copertina di itch.io (630×500, quasi quadrata): il logo in alto nel buio, sotto la faccia di Molly intera
    salva(logo(buio_alto(copri(verticale, 630, 500, 0.5, 0.5), 0.45, 0.85), 0.19, 0.0, 0.62), 'copertina_630x500.png', dove=ITCH)
    if solo_itch:
        return
    # la capsula principale e l'intestazione (anche nella libreria): lei a destra, il logo a sinistra
    salva(logo(buio_sinistra(copri(ritratto, 1232, 706, 0.55, 0.5), 0.55, 0.8), 0.015, 0.03, 0.58), 'capsule', 'principale_1232x706.png')
    testata = logo(buio_sinistra(copri(ritratto, 920, 430, 0.55, 0.40), 0.55, 0.8), 0.012, 0.03, 0.56)
    salva(testata, 'capsule', 'intestazione_920x430.png')
    salva(testata, 'libreria', 'intestazione_920x430.png')
    # la piccola: il logo grande, e lei che sbircia dal bordo destro (il ritratto senza l'ultimo quinto a destra)
    w = round(ritratto.width * 0.8)
    h = round(w * 174 / 462)
    y0 = round(ritratto.height * 0.42 - h * 0.5)
    piccola = np.asarray(ritratto.crop((0, y0, w, y0 + h)).resize((462, 174), Image.LANCZOS)).astype(np.float32) / 255
    salva(logo(buio_sinistra(piccola, 0.62, 0.85), 0.0, -0.04, 0.66, 1.15), 'capsule', 'piccola_462x174.png')
    # le verticali: il logo in alto nel buio, lei sotto
    salva(logo(buio_alto(copri(verticale, 748, 896, 0.5, 0.55), 0.45, 0.8), 0.02, 0.0, 0.96), 'capsule', 'verticale_748x896.png')
    salva(logo(buio_alto(copri(verticale, 600, 900, 0.5, 0.55), 0.45, 0.8), 0.02, 0.0, 0.96), 'libreria', 'capsula_600x900.png')
    # il logo della libreria: trasparente, largo 1280 (Steam lo mette sopra l'immagine larga)
    lw = 1280
    p = os.path.join(STEAM, 'libreria', 'logo_1280x612.png')
    logo_im.resize((lw, round(logo_im.height * lw / logo_im.width)), Image.LANCZOS).save(p, optimize=True)
    print('immagine', os.path.relpath(p, RADICE), flush=True)


if __name__ == '__main__':
    cmd, *a = sys.argv[1:] or ['']
    if cmd == 'render' and a:
        render(a[0])
    elif cmd == 'componi':
        componi()
    elif cmd == 'itch':
        componi(solo_itch=True)
    else:
        sys.exit(__doc__)
