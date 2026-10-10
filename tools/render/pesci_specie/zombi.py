"""
Zombi: marci, occhi lattiginosi, pinne strappate, punti di sutura (src/game/catalog.ts, docs/CATALOGO.md).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast
"""
from .base import (PELVICA, PETTORALE_ALA, PETTORALE_TONDA, RITRATTO_PROTOTIPI, Disegno, Filamento, Fin, Look, Shape,
                   Specie, coda_appuntita, coda_forcuta, coda_tonda)

SPECIE = {}

# ── Orrata (orata, Sparus aurata) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['orrata'] = Specie(
    forma=Shape(
        top=[(0, -0.03), (0.02, 0.004), (0.06, 0.06), (0.12, 0.118), (0.2, 0.158), (0.35, 0.182), (0.5, 0.176), (0.7, 0.118), (0.85, 0.064), (0.95, 0.042), (1, 0.04)],
        bot=[(0, -0.05), (0.025, -0.08), (0.1, -0.118), (0.25, -0.155), (0.45, -0.168), (0.6, -0.148), (0.75, -0.1), (0.9, -0.05), (1, -0.04)],
        w=[(0, 0.008), (0.06, 0.034), (0.2, 0.058), (0.4, 0.064), (0.65, 0.05), (0.85, 0.025), (1, 0.015)],
        eye_t=0.155, eye_z=0.058, eye_r=0.031, mouth_t=0.07, mouth_z0=-0.038, mouth_z1=-0.05, gill_t=0.29,
        fins=[Fin('dorsal', 0.33, 0.84, [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.82), (0.8, 0.75), (0.95, 0.55), (1, 0.05)], 0.12, 22, spiny=True),
              Fin('anal', 0.62, 0.84, [(0, 0), (0.12, 0.9), (0.6, 0.62), (0.95, 0.5), (1, 0.05)], 0.09, 12),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.34), 0.26, 20),
              Fin('pectoral', 0.32, 0.34, [(0, 0), (0.5, 0.3), (1.0, 0.16), (0.8, 0.02), (0, -0.06)], 0.2, 12),
              Fin('pelvic', 0.37, 0.39, [(0, 0), (0.6, 0.28), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.1, 7, spiny=True)]),
    aspetto=Look(back=(0.16, 0.18, 0.19), flank=(0.42, 0.44, 0.44), belly=(0.62, 0.62, 0.58), fin=(0.16, 0.16, 0.18),
                 iris=(0.72, 0.6, 0.36), pattern='bream'),
    famiglia='zombie', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ── Sogliombra (sogliola, Solea solea) — PROVA DEL PIANO 'piatto': forma normale, ancora da trasformare nella
#    famiglia (e «da morta ha deciso di guardare anche dall'altra»: un occhio in più sul lato cieco) ──
# Un pesce di fianco, molto compresso, con TUTTI E DUE GLI OCCHI SUL LATO −Y (la camera): il ritratto lo
# corica sul fondo. Dorsale e anale fanno la frangia tutto attorno, la coda tonda le tocca.
SPECIE['sogliombra'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.02, 0.03), (0.06, 0.068), (0.15, 0.112), (0.3, 0.14), (0.5, 0.145), (0.7, 0.12), (0.85, 0.078),
             (0.95, 0.042), (1, 0.03)],
        bot=[(0, -0.03), (0.03, -0.062), (0.1, -0.1), (0.25, -0.135), (0.45, -0.145), (0.65, -0.128), (0.82, -0.088),
             (0.95, -0.044), (1, -0.03)],
        w=[(0, 0.004), (0.08, 0.015), (0.25, 0.02), (0.5, 0.02), (0.75, 0.014), (0.95, 0.007), (1, 0.005)],
        eye_t=0.08, eye_z=0.04, eye_r=0.0115,
        occhi=[(0.072, 0.048, 0.0115, -1), (0.104, 0.022, 0.0115, -1)],
        mouth_t=0.05, mouth_z0=-0.02, mouth_z1=-0.042, gill_t=0.17,
        fins=[Fin('dorsal', 0.025, 0.985, [(0, 0), (0.03, 0.6), (0.15, 0.9), (0.5, 1.0), (0.85, 0.9), (0.97, 0.7), (1, 0.55)], 0.05, 90),
              Fin('anal', 0.19, 0.985, [(0, 0), (0.04, 0.7), (0.2, 0.95), (0.6, 1.0), (0.9, 0.85), (1, 0.6)], 0.048, 75),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.0, 0.95), 0.1, 22),
              Fin('pectoral', 0.175, 0.185, PETTORALE_TONDA, 0.05, 9, bordo=(0.03, 0.025, 0.02)),
              Fin('pelvic', 0.17, 0.18, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.03, 5)]),
    aspetto=Look(back=(0.22, 0.17, 0.115), flank=(0.27, 0.22, 0.15), belly=(0.86, 0.83, 0.76), fin=(0.2, 0.16, 0.11),
                 iris=(0.7, 0.6, 0.35), iris_dark=(0.15, 0.12, 0.06), metal=0.0, irid=0.0, squame=0.6,
                 linea_laterale=0.8, linea_v=(0.0, 0.0), lucido=0.4,
                 disegni=[Disegno('marmo', colore=(0.11, 0.08, 0.05), forza=0.65, scala=26, r=0.4),
                          Disegno('punti', colore=(0.07, 0.05, 0.035), forza=0.6, scala=170, r=0.12)]),
    famiglia='normale', piano='piatto')



def _denti_murena(c):
    """I denti a zanna nella bocca aperta (aiuto comune: denti_mascelle, con la stessa apertura della forma)."""
    c.obs += c.P.denti_mascelle(c.body, n=7, lunghezza=0.0055, zanne=(1, 2), apertura=c.forma.bocca_aperta, nome='DenteMurena')


# ── Murena Murata (murena, Muraena helena) — PROVA DEL PIANO 'anguilliforme': forma normale, ancora da
#    trasformare nella famiglia (marcia, murata nella fessura) ──
# Lunghissima, senza pettorali; dorsale, coda e anale sono una pinna sola di pelle spessa (carnose, con i
# disegni del corpo: tinta_pinne=0); la bocca aperta con le zanne (extra); l'asse a S (piega).
SPECIE['murena_murata'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.015, 0.012), (0.04, 0.026), (0.07, 0.036), (0.1, 0.045), (0.14, 0.052), (0.25, 0.055), (0.5, 0.052),
             (0.7, 0.044), (0.85, 0.032), (0.95, 0.016), (1, 0.004)],
        bot=[(0, -0.012), (0.02, -0.02), (0.05, -0.028), (0.1, -0.036), (0.2, -0.045), (0.4, -0.05), (0.6, -0.046), (0.8, -0.032),
             (0.93, -0.016), (1, -0.004)],
        w=[(0, 0.004), (0.04, 0.018), (0.1, 0.028), (0.25, 0.03), (0.5, 0.025), (0.75, 0.016), (0.9, 0.009), (1, 0.003)],
        eye_t=0.045, eye_z=0.011, eye_r=0.0085, mouth_t=0.075, mouth_z0=-0.006, mouth_z1=-0.012, bocca_aperta=16.0,
        branchie='pori', n_branchie=1, gill_t=0.13,
        fins=[Fin('dorsal', 0.12, 1.0, [(0, 0), (0.03, 0.55), (0.12, 0.9), (0.5, 1.0), (0.9, 1.0), (1, 0.7)], 0.03, 150,
                  carnosa=True, spessore=0.004),
              Fin('anal', 0.45, 1.0, [(0, 0), (0.05, 0.6), (0.2, 0.9), (0.9, 1.0), (1, 0.7)], 0.024, 100, carnosa=True, spessore=0.004),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.9, 1.0), 0.035, 20, carnosa=True, spessore=0.003)],
        piega=[(0, -10), (0.25, 12), (0.5, -10), (0.75, 12), (1.0, -4)]),
    aspetto=Look(back=(0.06, 0.045, 0.03), flank=(0.085, 0.065, 0.04), belly=(0.11, 0.09, 0.06), fin=(0.07, 0.05, 0.035),
                 iris=(0.78, 0.74, 0.6), iris_dark=(0.2, 0.18, 0.1), metal=0.0, irid=0.05, squame=0.0, linea_laterale=0.0,
                 lucido=0.6, ruvido=0.3, tinta_pinne=0.0,
                 disegni=[Disegno('macchie', colore=(0.78, 0.62, 0.28), forza=0.9, scala=34, r=0.24, colore2=(0.02, 0.015, 0.01)),
                          Disegno('punti', colore=(0.7, 0.58, 0.3), forza=0.7, scala=120, r=0.16, seme=3)]),
    extra=_denti_murena,
    famiglia='normale', piano='anguilliforme')


# ── Chimera Bianca (chimera, Chimaera monstrosa) — PROVA DEL PIANO 'coda_di_topo': forma normale, ancora da
#    trasformare nella famiglia (gli occhi enormi che piangono una cosa grigia) ──
# Testa grossa e occhi enormi, la prima dorsale alta con la spina, la seconda lunga e bassa fino alla coda
# che finisce in un filo (Filamento in punta); pettorali larghe come ali.
SPECIE['chimera_bianca'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.02, 0.03), (0.06, 0.06), (0.12, 0.075), (0.2, 0.08), (0.3, 0.075), (0.45, 0.055), (0.6, 0.035),
             (0.75, 0.02), (0.9, 0.009), (1, 0.003)],
        bot=[(0, -0.032), (0.04, -0.056), (0.1, -0.07), (0.2, -0.075), (0.32, -0.07), (0.45, -0.05), (0.6, -0.03), (0.75, -0.016),
             (0.9, -0.007), (1, -0.002)],
        w=[(0, 0.01), (0.05, 0.04), (0.15, 0.054), (0.3, 0.045), (0.5, 0.03), (0.75, 0.014), (1, 0.002)],
        eye_t=0.088, eye_z=0.022, eye_r=0.031, mouth_t=0.04, mouth_z0=-0.032, mouth_z1=-0.042, gill_t=0.17,
        filamenti=[Filamento(xyz=(0.995, 0.0, 0.0), dir=(1.0, 0.0, 0.05), curva=(0, 0, -0.6), lunghezza=0.28, raggio=0.0026,
                             lati='centro', punta=0.3, segmenti=12)],
        fins=[Fin('dorsal', 0.2, 0.27, [(0, 0), (0.05, 1.0), (0.2, 0.92), (0.6, 0.5), (1, 0.05)], 0.11, 12, spiny=True),
              Fin('dorsal', 0.31, 0.97, [(0, 0), (0.02, 0.5), (0.1, 0.8), (0.5, 0.75), (0.9, 0.6), (1, 0.3)], 0.025, 80),
              Fin('anal', 0.78, 0.97, [(0, 0), (0.1, 0.7), (0.8, 0.6), (1, 0.2)], 0.018, 20),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.5, 1.0), 0.03, 12),
              Fin('pectoral', 0.17, 0.2, PETTORALE_ALA, 0.21, 18, dir=(0.8, 0.45, -0.3)),
              Fin('pelvic', 0.42, 0.44, PELVICA, 0.06, 7)]),
    aspetto=Look(back=(0.3, 0.26, 0.22), flank=(0.5, 0.46, 0.42), belly=(0.64, 0.62, 0.58), fin=(0.32, 0.28, 0.25),
                 iris=(0.35, 0.75, 0.45), iris_dark=(0.05, 0.18, 0.1), metal=0.45, irid=0.45, squame=0.0, linea_laterale=0.0,
                 disegni=[Disegno('marmo', colore=(0.2, 0.16, 0.12), forza=0.5, scala=24, r=0.5),
                          Disegno('linea', colore=(0.12, 0.1, 0.08), forza=0.7, v=0.15, inclinazione=-0.1, larghezza=0.025, u0=0.15),
                          Disegno('vermi', colore=(0.15, 0.12, 0.1), forza=0.6, scala=60, u1=0.16)]),
    famiglia='normale', piano='coda_di_topo')
