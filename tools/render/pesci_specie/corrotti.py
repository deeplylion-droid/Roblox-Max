"""
Corrotti: occhi in più, bocche sbagliate, escrescenze, melma nera (src/game/catalog.ts, docs/CATALOGO.md).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast
"""
from .base import (PELVICA, PETTORALE_TONDA, RITRATTO_PROTOTIPI, Disegno, Filamento, Fin, Look, Shape, Specie, Spine,
                   coda_forcuta, coda_tonda, coda_tronca)

SPECIE = {}

# ── Trigliocchi (triglia di scoglio, Mullus surmuletus) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['trigliocchi'] = Specie(
    forma=Shape(
        top=[(0, -0.045), (0.02, -0.018), (0.05, 0.03), (0.1, 0.07), (0.18, 0.096), (0.3, 0.108), (0.5, 0.1), (0.72, 0.068), (0.9, 0.04), (1, 0.034)],
        bot=[(0, -0.052), (0.03, -0.075), (0.15, -0.09), (0.38, -0.094), (0.6, -0.078), (0.8, -0.052), (1, -0.034)],
        w=[(0, 0.012), (0.08, 0.04), (0.25, 0.054), (0.5, 0.05), (0.8, 0.028), (1, 0.014)],
        eye_t=0.125, eye_z=0.046, eye_r=0.024, mouth_t=0.05, mouth_z0=-0.046, mouth_z1=-0.054, gill_t=0.24, barbels=True,
        fins=[Fin('dorsal', 0.28, 0.42, [(0, 0), (0.15, 1.0), (0.45, 0.95), (0.8, 0.55), (1, 0.05)], 0.12, 8, spiny=True),
              Fin('dorsal', 0.56, 0.68, [(0, 0), (0.2, 0.8), (0.6, 0.6), (1, 0.05)], 0.07, 9),
              Fin('anal', 0.58, 0.7, [(0, 0), (0.2, 0.75), (0.6, 0.55), (1, 0.05)], 0.065, 8),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.4, 0.3), 0.23, 18),
              Fin('pectoral', 0.25, 0.27, [(0, 0), (0.5, 0.3), (1.0, 0.15), (0.8, 0.0), (0, -0.06)], 0.14, 10),
              Fin('pelvic', 0.3, 0.32, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.08, 6)]),
    aspetto=Look(back=(0.52, 0.12, 0.08), flank=(0.72, 0.30, 0.22), belly=(0.78, 0.62, 0.55), fin=(0.62, 0.38, 0.28),
                 iris=(0.85, 0.55, 0.2), iris_dark=(0.4, 0.12, 0.04), metal=0.25, pattern='redmullet', irid=0.2),
    famiglia='corrupt', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)



def _becco_pesce_palla(c):
    """Il becco del pesce palla: due placche di dente bianco, sopra e sotto il taglio della bocca."""
    P, sh = c.P, c.forma
    mat = P.materiale('BeccoPalla', (0.86, 0.82, 0.7), rough=0.25, coat=0.7, sss=0.3)
    for k, dz in enumerate((0.0055, -0.0055)):
        z = sh.mouth_z0 + dz
        f = P.sdf.ellipsoid((0.001, 0.0, z), (0.011, 0.02, 0.0065))
        c.obs.append(P.oggetto_sdf(f'BeccoPalla{k}', f, (-0.015, -0.028, z - 0.012), (0.02, 0.028, z + 0.012), mat, res=0.0006))


# ── Pesce Bubbone (pesce palla argenteo, Lagocephalus sceleratus) — PROVA DEL PIANO 'palla': forma normale,
#    ancora da trasformare nella famiglia (le bolle nere sulla pelle) ──
# Gonfio: la testa e la pancia sono una palla, la coda resta stretta. Le spinette sulla pancia sono
# Shape.spine (coni fusi nella pelle); il becco a quattro denti è l'extra.
SPECIE['pesce_bubbone'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.03, 0.06), (0.1, 0.15), (0.22, 0.21), (0.38, 0.23), (0.55, 0.2), (0.7, 0.12), (0.82, 0.055),
             (0.92, 0.035), (1, 0.03)],
        bot=[(0, -0.05), (0.04, -0.12), (0.12, -0.21), (0.28, -0.27), (0.45, -0.27), (0.6, -0.2), (0.74, -0.1), (0.85, -0.045),
             (1, -0.03)],
        w=[(0, 0.02), (0.05, 0.1), (0.15, 0.18), (0.32, 0.22), (0.5, 0.2), (0.68, 0.12), (0.82, 0.05), (1, 0.018)],
        eye_t=0.13, eye_z=0.085, eye_r=0.034, mouth_t=0.03, mouth_z0=-0.03, mouth_z1=-0.034, gill_t=0.3, branchie='nessuna',
        spine=[Spine(0.06, 0.72, -1.0, -0.12, 170, lunghezza=0.016, raggio=0.0034, inclinazione=0.35, seme=1),
               Spine(0.1, 0.62, 0.15, 0.9, 50, lunghezza=0.01, raggio=0.0026, inclinazione=0.4, seme=2)],
        fins=[Fin('dorsal', 0.72, 0.79, [(0, 0), (0.2, 0.9), (0.6, 1.0), (1, 0.1)], 0.07, 10),
              Fin('anal', 0.73, 0.8, [(0, 0), (0.2, 0.9), (0.6, 1.0), (1, 0.1)], 0.065, 10),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.7, 0.15, 0.85), 0.17, 16),
              Fin('pectoral', 0.3, 0.31, PETTORALE_TONDA, 0.08, 10, z=0.1)]),
    aspetto=Look(back=(0.16, 0.18, 0.15), flank=(0.55, 0.58, 0.58), belly=(0.86, 0.86, 0.83), fin=(0.3, 0.32, 0.3),
                 iris=(0.85, 0.75, 0.4), iris_dark=(0.2, 0.15, 0.05), metal=0.35, irid=0.2, squame=0.0, linea_laterale=0.0,
                 disegni=[Disegno('macchie', colore=(0.04, 0.045, 0.04), forza=0.9, scala=40, r=0.22, v0=0.25),
                          Disegno('strisce', colore=(0.78, 0.8, 0.82), forza=0.6, n=1, v0=-0.3, v1=0.1, larghezza=0.3)]),
    extra=_becco_pesce_palla,
    famiglia='normale', piano='palla')


# ── Missina della Melma (missina, Myxine glutinosa) — PROVA DEI BARBIGLI (piano 'anguilliforme'): forma
#    normale, ancora da trasformare nella famiglia (la melma nera e tiepida) ──
# Niente occhi veri (occhi=[]: due macchie chiare sotto la pelle), tre paia di barbigli attorno alla bocca
# (Shape.filamenti), la fila dei pori del muco sul fianco (disegno 'linea' a puntini), la piega della coda.
SPECIE['missina_della_melma'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.03, 0.012), (0.1, 0.021), (0.4, 0.027), (0.7, 0.027), (0.9, 0.023), (1, 0.009)],
        bot=[(0, -0.012), (0.04, -0.021), (0.15, -0.026), (0.5, -0.029), (0.8, -0.025), (0.95, -0.015), (1, -0.006)],
        w=[(0, 0.008), (0.05, 0.017), (0.3, 0.023), (0.7, 0.019), (0.9, 0.011), (1, 0.004)],
        eye_t=0.05, eye_z=0.01, eye_r=0.006, occhi=[], mouth_t=0.022, mouth_z0=-0.005, mouth_z1=-0.008,
        branchie='pori', n_branchie=1, gill_t=0.3,
        filamenti=[Filamento(t=0.004, v=0.45, lunghezza=0.024, raggio=0.0021, dir=(-0.7, 0.35, 0.25), curva=(0, 0, -3)),
                   Filamento(t=0.006, v=-0.2, lunghezza=0.02, raggio=0.002, dir=(-0.6, 0.5, -0.3), curva=(0, 0, -3)),
                   Filamento(t=0.018, v=-0.75, lunghezza=0.018, raggio=0.0019, dir=(-0.35, 0.55, -0.75), curva=(3, 0, 0))],
        fins=[Fin('dorsal', 0.68, 1.0, [(0, 0), (0.1, 0.7), (0.5, 1.0), (0.9, 1.0), (1, 0.7)], 0.012, 40),
              Fin('anal', 0.86, 1.0, [(0, 0), (0.2, 0.8), (0.9, 1.0), (1, 0.7)], 0.011, 16),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.0, 0.9), 0.035, 14)],
        piega=[(0, 12), (0.3, -22), (0.6, 18), (1.0, -26)]),
    aspetto=Look(back=(0.42, 0.29, 0.27), flank=(0.5, 0.37, 0.34), belly=(0.6, 0.47, 0.43), fin=(0.45, 0.33, 0.3),
                 metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0, lucido=0.9, ruvido=0.2,
                 disegni=[Disegno('linea', colore=(0.85, 0.78, 0.72), forza=0.85, v=-0.6, larghezza=0.06, n=70, u0=0.12, u1=0.95),
                          Disegno('macchia', colore=(0.62, 0.5, 0.45), forza=0.7, u=0.05, v=0.25, r=0.006)]),
    famiglia='normale', piano='anguilliforme')



# ── Gallincubo (gallinella, Chelidonichthys lucerna) — PROVA DEI RAGGI LIBERI (piano 'pettorali'): forma
#    normale, ancora da trasformare nella famiglia (le dita che bussano) ──
# Testa ossuta e larga, le pettorali enormi a ventaglio (verdi, puntinate di blu, il bordo blu) e sotto i tre
# raggi liberi a zampetta (Fin.liberi = 3).
SPECIE['gallincubo'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.02, 0.012), (0.06, 0.046), (0.12, 0.074), (0.22, 0.088), (0.35, 0.086), (0.55, 0.068), (0.75, 0.044),
             (0.9, 0.028), (1, 0.022)],
        bot=[(0, -0.036), (0.03, -0.06), (0.1, -0.074), (0.25, -0.076), (0.45, -0.066), (0.65, -0.048), (0.85, -0.03), (1, -0.022)],
        w=[(0, 0.016), (0.05, 0.045), (0.15, 0.058), (0.3, 0.054), (0.6, 0.037), (0.85, 0.02), (1, 0.012)],
        eye_t=0.09, eye_z=0.045, eye_r=0.02, mouth_t=0.06, mouth_z0=-0.03, mouth_z1=-0.04, gill_t=0.2,
        spine=[Spine(0.03, 0.17, 0.35, 0.9, 10, lunghezza=0.006, raggio=0.003, inclinazione=0.6, seme=4)],
        fins=[Fin('pectoral', 0.2, 0.23, [(0, 0.05), (0.35, 0.45), (0.8, 0.5), (1.0, 0.2), (0.95, -0.15), (0.6, -0.3), (0, -0.1)],
                  0.3, 16, z=-0.1, dir=(0.55, 0.75, -0.2), su=(1.0, 0.0, 0.3),
                  colore=(0.12, 0.3, 0.32), bordo=(0.12, 0.3, 0.8), macchie=0.7, colore_macchie=(0.15, 0.35, 0.9), liberi=3),
              Fin('dorsal', 0.24, 0.38, [(0, 0), (0.1, 0.9), (0.35, 1.0), (0.8, 0.5), (1, 0.05)], 0.08, 9, spiny=True),
              Fin('dorsal', 0.4, 0.75, [(0, 0), (0.05, 0.8), (0.5, 0.7), (1, 0.05)], 0.05, 18),
              Fin('anal', 0.42, 0.75, [(0, 0), (0.05, 0.8), (0.5, 0.7), (1, 0.05)], 0.045, 16),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.6, 0.2, 0.85), 0.18, 16),
              Fin('pelvic', 0.24, 0.25, PELVICA, 0.06, 6)]),
    aspetto=Look(back=(0.45, 0.2, 0.13), flank=(0.6, 0.36, 0.28), belly=(0.85, 0.78, 0.72), fin=(0.5, 0.3, 0.25),
                 iris=(0.8, 0.6, 0.3), iris_dark=(0.3, 0.15, 0.05), metal=0.2, irid=0.2, squame=0.7),
    famiglia='normale', piano='pettorali')
