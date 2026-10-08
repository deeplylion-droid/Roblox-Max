#!/usr/bin/env python3
"""
Genera tutte le mesh del gioco (glTF binario .glb) e le anteprime PNG.
Uso: python3 tools/meshgen/generate.py [--out assets/meshes] [--previews assets/previews]
Ogni voce di CATALOG: chiave → (funzione, colore anteprima). La chiave è quella usata dal gioco (MeshUtil).
"""
from __future__ import annotations
import argparse, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from mesh import Mesh, icosphere, lathe, torus, merge, fbm, displace_radial, displace_normal, gaussian_bumps, export_glb, render

MAX_TRIS = 9000

# ───────────────────────── helper ─────────────────────────

def smooth_profile(points, n=10):
    """Interpola un profilo (r,y) con Catmull-Rom per superfici di rivoluzione morbide."""
    P = np.array(points, dtype=float)
    out = []
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]
        p1, p2 = P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    out = np.array(out)
    out[:, 0] = np.maximum(out[:, 0], 0)
    return [tuple(p) for p in out]


def rng(seed):
    return np.random.default_rng(seed)


# ───────────────────────── nuvole, rocce, isole ─────────────────────────

def cloud(seed=1, lumps=12, squash=0.72):
    r = rng(seed)
    m = icosphere(4, 1.0)
    centers = r.normal(size=(lumps, 3))
    centers[:, 1] = np.abs(centers[:, 1]) * 0.9 + 0.15  # gobbe verso l'alto (cumulo)
    centers[:, 0] *= 1.4
    sig = r.uniform(0.22, 0.38, lumps)
    h = r.uniform(0.35, 0.75, lumps)
    displace_radial(m, lambda V: gaussian_bumps(V, centers, sig, h))
    m.V[:, 0] *= 1.25
    # fondo piatto e morbido
    y = m.V[:, 1]
    m.V[:, 1] = np.where(y < 0, y * squash * 0.55, y)
    m.V[:, 1] += fbm(m.V, seed, 2, 1.5) * 0.03
    m.fix_orientation()
    return m.center_bottom()


def rock(seed=2, flatten=0.75):
    m = icosphere(3, 1.0)
    n = fbm(m.V, seed, 4, 1.3) * 0.28 + fbm(m.V, seed + 5, 2, 4.0) * 0.06
    displace_radial(m, lambda V: 1 + n)
    m.V[:, 1] *= flatten
    m.fix_orientation()
    return m.center_bottom()


def crystal(seed=3):
    m = icosphere(0, 1.0)
    m.V[:, 1] *= 2.2
    m.V += rng(seed).normal(scale=0.06, size=m.V.shape)
    m.flat = True
    m.fix_orientation()
    return m.center_bottom()


def island(seed=4, squareness=0.0, rim_noise=0.12, depth=0.9):
    """Isola: disco superiore lievemente bombato con bordo irregolare + roccia sottostante a cono."""
    m = icosphere(4, 1.0)
    V = m.V
    # bordo frastagliato (dipende solo dall'angolo attorno a Y)
    ang = np.arctan2(V[:, 2], V[:, 0])
    P = np.stack([np.cos(ang), np.sin(ang), np.zeros_like(ang)], axis=1)
    rimf = 1 + fbm(P * 2.0, seed, 3, 1.0) * rim_noise
    # forma quadrata arrotondata (superellisse) se richiesto
    if squareness > 0:
        sq = (np.abs(np.cos(ang)) ** 4 + np.abs(np.sin(ang)) ** 4) ** (-0.25)
        rimf *= 1 + (sq - 1) * squareness
    horiz = np.sqrt(V[:, 0] ** 2 + V[:, 2] ** 2)
    up = V[:, 1] > 0
    # sopra: piattaforma quasi piatta con leggera cupola; sotto: cono roccioso
    newY = np.where(up, 0.04 + 0.05 * (1 - horiz ** 2), -depth * (1 - horiz) ** 1.4 - 0.05)
    newH = np.where(up, horiz * rimf, horiz * rimf * (0.98 - 0.02 * (-newY)))
    m.V = np.stack([V[:, 0] / np.maximum(horiz, 1e-9) * newH, newY, V[:, 2] / np.maximum(horiz, 1e-9) * newH], axis=1)
    # rumore roccioso solo sotto
    noise = fbm(m.V * 3.0, seed + 1, 3, 1.0) * 0.08
    m.V[:, 1] += np.where(up, 0, noise)
    m.V[:, 0] *= 1 + np.where(up, 0, noise * 0.5)
    m.V[:, 2] *= 1 + np.where(up, 0, noise * 0.5)
    m.fix_orientation()
    return m


# ───────────────────────── creature ─────────────────────────

def body_sole():
    m = icosphere(4, 1.0)
    m.V[:, 1] *= 0.95
    # leggero "pancino"
    m.V[:, 2] -= 0.08 * np.clip(-m.V[:, 1], 0, 1)
    return m.center()


def body_pioggia():
    prof = smooth_profile([(0, -1.0), (0.45, -0.85), (0.85, -0.45), (1.0, 0.05), (0.85, 0.55), (0.5, 0.95), (0.18, 1.3), (0.0, 1.55)], 8)
    m = lathe(prof, 64)
    return m.center()


def body_vento():
    prof = smooth_profile([(0, -1.0), (0.6, -0.8), (0.95, -0.2), (1.0, 0.25), (0.8, 0.7), (0.45, 1.0), (0.12, 1.25), (0.0, 1.35)], 8)
    m = lathe(prof, 64)
    m.rotate_x(-55)  # inclinata in avanti come soffiata dal vento
    m.V[:, 0] *= 0.9
    return m.center()


def body_aurora():
    prof = smooth_profile([(0, -1.25), (0.55, -0.9), (0.95, -0.2), (1.0, 0.15), (0.9, 0.5), (0.55, 0.95), (0.0, 1.25)], 8)
    m = lathe(prof, 64)
    m.V[:, 0] *= 0.85
    return m.center()


def sun_petals(count=8):
    petals = []
    for i in range(count):
        p = icosphere(2, 1.0)
        p.V[:, 0] *= 0.34
        p.V[:, 1] *= 0.75
        p.V[:, 2] *= 0.14
        p.V[:, 0] *= 1 - 0.55 * np.clip(p.V[:, 1] / 0.75, 0, 1)  # a punta verso l'esterno
        p.translate(0, 1.45, 0).rotate_z(360 * i / count)
        petals.append(p)
    return merge(*petals).center()


def cloud_hat():
    return cloud(seed=11, lumps=7, squash=0.5).scale(1, 0.75, 1).center_bottom()


def drop_tail():
    prof = smooth_profile([(0, 0), (0.55, 0.3), (0.7, 0.8), (0.4, 1.35), (0.0, 1.7)], 8)
    return lathe(prof, 40).center()


def swirl_ribbon(turns=1.1, length=2.4):
    """Nastro di vento: striscia che si avvolge a spirale e si assottiglia verso la coda."""
    n = 60
    V, F = [], []
    for i in range(n):
        t = i / (n - 1)
        a = t * turns * 2 * math.pi
        r = 0.9 - 0.4 * t
        w = 0.28 * (1 - t) + 0.03
        cx, cz = math.cos(a) * r, math.sin(a) * r
        y = (t - 0.5) * length
        # direzione radiale per la larghezza (nastro verticale che ruota)
        nx, nz = math.cos(a), math.sin(a)
        V.append([cx - nx * w * 0.2, y - w, cz - nz * w * 0.2])
        V.append([cx + nx * w * 0.2, y + w, cz + nz * w * 0.2])
    for i in range(n - 1):
        a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        F += [[a, c, b], [b, c, d], [a, b, c], [b, d, c]]  # doppia faccia
    return Mesh(np.array(V), np.array(F)).center()


def aurora_arc():
    return torus(1.0, 0.16, 48, 16, arc=210).rotate_z(-15).center()


# ───────────────────────── architettura e arredi ─────────────────────────

def pillar():
    prof = smooth_profile([(0, 0), (0.95, 0), (1.0, 0.15), (0.72, 0.4), (0.62, 1.0), (0.58, 3.5), (0.62, 6.0), (0.75, 6.4), (0.95, 6.7), (0.9, 7.0), (0, 7.0)], 4)
    return lathe(prof, 40).center_bottom()


def lamp_head():
    m = icosphere(3, 1.0)
    m.V[:, 1] *= 1.15
    return m.center()


def bell():
    prof = smooth_profile([(0, 0), (1.0, 0), (1.05, 0.12), (0.9, 0.35), (0.72, 0.9), (0.62, 1.4), (0.5, 1.75), (0.22, 2.0), (0.0, 2.1)], 8)
    return lathe(prof, 48).center_bottom()


def basin():
    """Ciotola con bordo arrotondato (pozza, fontana, faro)."""
    prof = smooth_profile([(0, 0), (0.75, 0), (0.95, 0.1), (1.0, 0.4), (0.97, 0.55), (0.85, 0.6), (0.8, 0.5), (0.72, 0.18), (0.0, 0.14)], 6)
    return lathe(prof, 56).center_bottom()


def vault():
    prof = smooth_profile([(0, 0), (0.9, 0), (1.0, 0.1), (1.0, 1.7), (0.95, 1.85), (0.8, 1.95), (0.0, 2.0)], 5)
    return lathe(prof, 48).center_bottom()


def portal_ring():
    return torus(1.0, 0.12, 72, 20).rotate_x(90).center()


def arch():
    return torus(1.0, 0.1, 48, 14, arc=180).rotate_x(0).center()


def lantern():
    prof = [(0, 0), (0.5, 0), (0.6, 0.1), (0.6, 0.9), (0.5, 1.0), (0.25, 1.05), (0.2, 1.3), (0, 1.3)]
    return lathe(prof, 6).center_bottom()  # 6 lati = lanterna esagonale


def post():
    prof = smooth_profile([(0, 0), (0.22, 0), (0.17, 0.5), (0.14, 4.0), (0.16, 4.3), (0, 4.4)], 4)
    return lathe(prof, 16).center_bottom()


def bush(seed=21):
    m = icosphere(3, 1.0)
    n = fbm(m.V * 1.2, seed, 3, 1.0) * 0.18
    bumps = gaussian_bumps(m.V, rng(seed).normal(size=(6, 3)), [0.5] * 6, [0.2] * 6) - 1
    displace_radial(m, lambda V: 1 + n + bumps)
    m.V[:, 1] *= 0.85
    m.fix_orientation()
    return m.center_bottom()


def trunk(seed=31):
    prof = smooth_profile([(0, 0), (1.5, 0), (1.15, 0.5), (0.85, 1.5), (0.7, 6.0), (0.62, 12.0), (0.5, 17.0), (0.0, 17.6)], 5)
    m = lathe(prof, 36)
    n = fbm(m.V * np.array([1.5, 0.35, 1.5]), seed, 3, 1.0) * 0.12
    m.V[:, 0] *= 1 + n
    m.V[:, 2] *= 1 + n
    return m.center_bottom()


def platform_pad():
    prof = smooth_profile([(0, 0), (0.9, 0), (1.0, 0.15), (0.98, 0.3), (0.0, 0.32)], 4)
    return lathe(prof, 48).center_bottom()


def pedestal():
    prof = smooth_profile([(0, 0), (1.0, 0), (1.0, 0.2), (0.85, 0.45), (0.82, 6.4), (0.95, 6.75), (1.0, 7.0), (0, 7.0)], 4)
    return lathe(prof, 48).center_bottom()


def bounce_pad():
    prof = smooth_profile([(0, 0), (0.8, 0), (1.0, 0.12), (0.9, 0.3), (0.0, 0.42)], 4)
    return lathe(prof, 40).center_bottom()


def vent():
    prof = smooth_profile([(0, 0), (1.0, 0), (1.0, 0.25), (0.75, 0.4), (0.6, 0.55), (0.0, 0.5)], 3)
    return lathe(prof, 32).center_bottom()


def mushroom_stone():
    prof = smooth_profile([(0, 0), (0.6, 0), (0.5, 0.6), (1.0, 0.9), (0.9, 1.15), (0.0, 1.25)], 5)
    return lathe(prof, 28).center_bottom()


def flower_bed(seed=41):
    r = rng(seed)
    parts = [bush(seed).scale(1.2, 0.5, 1.2)]
    for i in range(9):
        f = icosphere(1, 0.16)
        a = r.uniform(0, 2 * math.pi)
        d = r.uniform(0.2, 0.9)
        f.translate(math.cos(a) * d, 0.55 + r.uniform(0, 0.15), math.sin(a) * d)
        parts.append(f)
    return merge(*parts).center_bottom()


# ───────────────────────── catalogo ─────────────────────────

CATALOG = {
    # nuvole e scenario
    "cloud_a": (lambda: cloud(1, 12), (250, 252, 255)),
    "cloud_b": (lambda: cloud(2, 9), (250, 252, 255)),
    "cloud_c": (lambda: cloud(3, 14, 0.6), (250, 252, 255)),
    "rock_a": (lambda: rock(2), (150, 160, 190)),
    "rock_b": (lambda: rock(7, 0.6), (150, 160, 190)),
    "rock_c": (lambda: rock(13, 0.9), (150, 160, 190)),
    "crystal": (lambda: crystal(3), (220, 180, 255)),
    "island_hub": (lambda: island(4, 0.0, 0.10, 0.9), (128, 200, 120)),
    "island_plot": (lambda: island(9, 0.85, 0.05, 0.8), (128, 200, 120)),
    # creature
    "body_sole": (body_sole, (255, 214, 102)),
    "body_pioggia": (body_pioggia, (110, 170, 250)),
    "body_vento": (body_vento, (170, 240, 210)),
    "body_aurora": (body_aurora, (200, 150, 255)),
    "sun_petals": (sun_petals, (255, 240, 180)),
    "cloud_hat": (cloud_hat, (245, 248, 255)),
    "drop_tail": (drop_tail, (110, 170, 250)),
    "swirl_ribbon": (swirl_ribbon, (240, 255, 250)),
    "aurora_arc": (aurora_arc, (150, 255, 220)),
    # architettura
    "pillar": (pillar, (205, 210, 230)),
    "lamp_head": (lamp_head, (255, 250, 200)),
    "bell": (bell, (240, 200, 110)),
    "basin": (basin, (236, 232, 220)),
    "vault": (vault, (120, 150, 210)),
    "portal_ring": (portal_ring, (250, 250, 255)),
    "arch": (arch, (196, 130, 255)),
    "lantern": (lantern, (255, 220, 150)),
    "post": (post, (120, 90, 60)),
    "bush": (lambda: bush(21), (110, 190, 150)),
    "trunk": (lambda: trunk(31), (130, 100, 80)),
    "platform_pad": (platform_pad, (255, 220, 150)),
    "pedestal": (pedestal, (220, 200, 255)),
    "bounce_pad": (bounce_pad, (255, 200, 255)),
    "vent": (vent, (120, 190, 170)),
    "mushroom_stone": (mushroom_stone, (200, 190, 230)),
    "flower_bed": (lambda: flower_bed(41), (120, 200, 140)),
}


def contact_sheet(previews, path, cols=6, cell=210):
    from PIL import Image, ImageDraw
    rows = math.ceil(len(previews) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 22)), (236, 243, 252))
    d = ImageDraw.Draw(sheet)
    for i, (name, p) in enumerate(previews):
        im = Image.open(p).resize((cell, cell))
        x, y = (i % cols) * cell, (i // cols) * (cell + 22)
        sheet.paste(im, (x, y))
        d.text((x + 6, y + cell + 4), name, fill=(40, 50, 80))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets/meshes")
    ap.add_argument("--previews", default="assets/previews")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.previews, exist_ok=True)
    previews = []
    for name, (fn, color) in CATALOG.items():
        if args.only and name not in args.only:
            continue
        m = fn()
        assert m.tris <= MAX_TRIS, f"{name}: {m.tris} triangoli (max {MAX_TRIS})"
        lo, hi = m.bounds()
        export_glb(m, os.path.join(args.out, f"{name}.glb"), name)
        p = render(m, os.path.join(args.previews, f"{name}.png"), color=color)
        previews.append((name, p))
        print(f"{name:16s} {m.tris:5d} tri  size=({hi[0]-lo[0]:.2f}, {hi[1]-lo[1]:.2f}, {hi[2]-lo[2]:.2f})")
    if not args.only:
        contact_sheet(previews, os.path.join(args.previews, "_contact_sheet.png"))
        print("contact sheet:", os.path.join(args.previews, "_contact_sheet.png"))


if __name__ == "__main__":
    main()
