"""
Glitchati: fette sfalsate, colori separati, come un nastro rovinato (src/game/catalog.ts, docs/CATALOGO.md).
Il pesce si costruisce normale; il glitch è sull'immagine (pesci.py: glitch_post).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast
"""
from .base import PETTORALE_ALA, RITRATTO_PROTOTIPI, Fin, Look, Shape, Specie, coda_forcuta

SPECIE = {}

# ── Salpa Sfasata (salpa, Sarpa salpa) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['salpa_sfasata'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.05, 0.035), (0.15, 0.092), (0.35, 0.128), (0.55, 0.124), (0.75, 0.082), (0.9, 0.046), (1, 0.04)],
        bot=[(0, -0.026), (0.07, -0.058), (0.2, -0.096), (0.4, -0.12), (0.6, -0.106), (0.8, -0.068), (0.95, -0.042), (1, -0.04)],
        w=[(0, 0.008), (0.08, 0.034), (0.25, 0.053), (0.45, 0.056), (0.7, 0.04), (0.9, 0.02), (1, 0.014)],
        eye_t=0.12, eye_z=0.034, eye_r=0.026, mouth_t=0.045, mouth_z0=-0.02, mouth_z1=-0.026, gill_t=0.25,
        fins=[Fin('dorsal', 0.3, 0.82, [(0, 0), (0.06, 0.95), (0.25, 0.9), (0.55, 0.62), (0.85, 0.66), (1, 0.05)], 0.09, 22, spiny=True),
              Fin('anal', 0.6, 0.82, [(0, 0), (0.12, 0.85), (0.6, 0.6), (1, 0.05)], 0.07, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.45, 0.3), 0.24, 20),
              Fin('pectoral', 0.28, 0.3, [(0, 0), (0.5, 0.3), (1.0, 0.15), (0.8, 0.0), (0, -0.06)], 0.15, 11),
              Fin('pelvic', 0.33, 0.35, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.08, 6)]),
    aspetto=Look(back=(0.12, 0.16, 0.20), flank=(0.36, 0.40, 0.44), belly=(0.62, 0.62, 0.6), fin=(0.16, 0.17, 0.2),
                 iris=(0.95, 0.62, 0.10), iris_dark=(0.45, 0.22, 0.02), pattern='salema'),
    famiglia='glitch', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ── Pesce Volante in Pausa (pesce volante, Cheilopogon heterurus) — PROVA DEL PIANO 'pettorali': forma normale,
#    ancora da trasformare nella famiglia (il fermo immagine) ──
# Le pettorali enormi aperte come ali (dir: fuori e indietro; su: la corda lungo il corpo) e le pelviche
# grandi; la coda con il lobo di sotto più lungo. Il ritratto del piano gira il dorso verso la camera.
SPECIE['pesce_volante_in_pausa'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.025), (0.08, 0.05), (0.18, 0.068), (0.35, 0.074), (0.55, 0.066), (0.75, 0.045), (0.9, 0.027),
             (1, 0.022)],
        bot=[(0, -0.022), (0.04, -0.045), (0.12, -0.065), (0.3, -0.075), (0.5, -0.07), (0.7, -0.05), (0.9, -0.026), (1, -0.022)],
        w=[(0, 0.008), (0.06, 0.035), (0.2, 0.055), (0.5, 0.05), (0.8, 0.026), (1, 0.014)],
        eye_t=0.085, eye_z=0.016, eye_r=0.022, mouth_t=0.04, mouth_z0=-0.005, mouth_z1=-0.012, gill_t=0.19,
        fins=[Fin('pectoral', 0.2, 0.23, PETTORALE_ALA, 0.6, 16, z=0.35, dir=(0.5, 0.85, 0.12), su=(1.0, 0.0, 0.0)),
              Fin('pelvic', 0.48, 0.5, PETTORALE_ALA, 0.3, 10, z=-0.7, dir=(0.6, 0.75, -0.1), su=(1.0, 0.0, 0.0)),
              Fin('dorsal', 0.66, 0.8, [(0, 0), (0.15, 0.9), (0.5, 1.0), (0.9, 0.7), (1, 0.05)], 0.05, 12),
              Fin('anal', 0.7, 0.8, [(0, 0), (0.15, 0.9), (0.5, 0.9), (1, 0.05)], 0.04, 10),
              Fin('caudal', 1.0, 1.0, [(0.0, 1.0), (0.55, 1.12), (0.9, 1.45), (0.3, 0.0), (1.3, -2.0), (0.6, -1.12), (0.0, -1.0)],
                  0.24, 18)]),
    aspetto=Look(back=(0.04, 0.09, 0.2), flank=(0.48, 0.53, 0.58), belly=(0.7, 0.72, 0.74), fin=(0.3, 0.34, 0.4),
                 iris=(0.5, 0.52, 0.5), iris_dark=(0.06, 0.06, 0.07), metal=0.7, irid=0.5),
    famiglia='normale', piano='pettorali')
