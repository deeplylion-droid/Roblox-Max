"""
Scheletrici: carne mancante, lisca e cranio in vista (src/game/catalog.ts, docs/CATALOGO.md).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast
"""
from .base import (DORSALE_SQUALO, PETTORALE, PETTORALE_TONDA, PELVICA, RITRATTO_PROTOTIPI, Disco,
                   Disegno, Filamento, Fin, Fotofori, Look, Rostro, Shape, Specie, coda_eterocerca, coda_falcata,
                   coda_forcuta, coda_tonda)

SPECIE = {}

# ── Sgombrato (sgombro, Scomber scombrus) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['sgombrato'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.03, 0.022), (0.09, 0.055), (0.2, 0.082), (0.36, 0.092), (0.55, 0.082), (0.75, 0.05), (0.9, 0.026), (1, 0.018)],
        bot=[(0, -0.012), (0.04, -0.035), (0.12, -0.062), (0.3, -0.088), (0.5, -0.085), (0.72, -0.055), (0.9, -0.026), (1, -0.018)],
        w=[(0, 0.004), (0.05, 0.026), (0.15, 0.05), (0.35, 0.058), (0.6, 0.046), (0.85, 0.02), (1, 0.011)],
        eye_t=0.075, eye_z=0.016, eye_r=0.021, mouth_t=0.075, mouth_z0=-0.008, mouth_z1=-0.016, gill_t=0.2,
        fins=[Fin('dorsal', 0.30, 0.42, [(0, 0), (0.15, 0.9), (0.4, 1.0), (0.75, 0.55), (1, 0.08)], 0.11, 10, spiny=True),
              Fin('dorsal', 0.56, 0.64, [(0, 0), (0.25, 0.8), (0.6, 0.55), (1, 0.05)], 0.06, 8),
              Fin('anal', 0.58, 0.66, [(0, 0), (0.25, 0.75), (0.6, 0.5), (1, 0.05)], 0.055, 8),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.55, 0.26), 0.24, 18),
              Fin('pectoral', 0.20, 0.215, [(0, 0), (0.45, 0.35), (1.0, 0.18), (0.8, -0.05), (0, -0.1)], 0.11, 9),
              Fin('pelvic', 0.27, 0.285, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.06, 6)]),
    aspetto=Look(back=(0.08, 0.24, 0.26), flank=(0.32, 0.36, 0.36), belly=(0.62, 0.62, 0.58), fin=(0.10, 0.12, 0.12),
                 iris=(0.55, 0.55, 0.50), iris_dark=(0.10, 0.10, 0.10), pattern='mackerel', irid=0.55),
    famiglia='skeletal', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ── San Pietrificato (pesce San Pietro, Zeus faber) — PROVA DEL PIANO 'alto': forma normale, ancora da
#    trasformare nella famiglia (lo scheletro, e l'impronta del pollice piccola come quella di un bambino) ──
# Corpo alto quasi quanto lungo e sottilissimo; le spine della dorsale con i filamenti lunghi (la sagoma a
# punte, con tanti raggi perché la membrana le segua); la macchia nera cerchiata di giallo sul fianco.
SPECIE['san_pietrificato'] = Specie(
    forma=Shape(
        top=[(0, -0.02), (0.03, 0.03), (0.08, 0.1), (0.15, 0.18), (0.25, 0.255), (0.35, 0.29), (0.5, 0.275), (0.65, 0.215),
             (0.8, 0.13), (0.92, 0.055), (1, 0.03)],
        bot=[(0, -0.06), (0.04, -0.1), (0.1, -0.17), (0.2, -0.245), (0.32, -0.29), (0.45, -0.29), (0.6, -0.245), (0.75, -0.17),
             (0.9, -0.07), (1, -0.03)],
        w=[(0, 0.006), (0.08, 0.024), (0.25, 0.038), (0.5, 0.04), (0.75, 0.028), (0.92, 0.014), (1, 0.009)],
        eye_t=0.2, eye_z=0.055, eye_r=0.032, mouth_t=0.09, mouth_z0=-0.012, mouth_z1=-0.095, gill_t=0.33,
        fins=[Fin('dorsal', 0.3, 0.5, [(0, 0), (0.04, 1.8), (0.08, 0.5), (0.15, 2.2), (0.2, 0.55), (0.27, 2.4), (0.32, 0.55),
                                      (0.39, 2.45), (0.44, 0.55), (0.51, 2.4), (0.56, 0.55), (0.63, 2.2), (0.68, 0.5), (0.75, 1.9),
                                      (0.8, 0.45), (0.87, 1.5), (0.92, 0.4), (1, 0.3)], 0.14, 90, spiny=True),
              Fin('dorsal', 0.52, 0.86, [(0, 0.3), (0.1, 0.75), (0.4, 0.85), (0.8, 0.6), (1, 0.05)], 0.1, 24),
              Fin('anal', 0.47, 0.86, [(0, 0), (0.05, 0.9), (0.12, 0.45), (0.2, 0.7), (0.5, 0.8), (0.85, 0.55), (1, 0.05)], 0.09, 28),
              Fin('caudal', 1.0, 1.0, coda_tonda(1.7, 1.0), 0.15, 18),
              Fin('pectoral', 0.36, 0.37, PETTORALE_TONDA, 0.08, 10),
              Fin('pelvic', 0.3, 0.32, [(0, 0), (0.5, 0.18), (1.0, 0.05), (0.85, -0.05), (0, -0.06)], 0.16, 8, spiny=True)]),
    aspetto=Look(back=(0.26, 0.22, 0.14), flank=(0.40, 0.36, 0.24), belly=(0.52, 0.48, 0.36), fin=(0.22, 0.19, 0.14),
                 iris=(0.8, 0.65, 0.3), iris_dark=(0.25, 0.18, 0.06), metal=0.35, irid=0.25, squame=0.3,
                 disegni=[Disegno('vermi', colore=(0.16, 0.13, 0.08), forza=0.4, scala=40),
                          Disegno('ocello', colore=(0.02, 0.02, 0.02), colore2=(0.78, 0.62, 0.28), u=0.46, v=0.05, r=0.042)]),
    famiglia='normale', piano='alto')


def _denti_sciabola(c):
    """Le zanne davanti, nelle due mascelle (aiuto comune: denti_mascelle)."""
    c.obs += c.P.denti_mascelle(c.body, n=6, lunghezza=0.0045, zanne=(0, 1), nome='DenteSciabola')


# ── Sciabola Spolpata (pesce sciabola, Lepidopus caudatus) — PROVA DEL PIANO 'nastriforme': forma normale,
#    ancora da trasformare nella famiglia (spolpata: la lisca lunga come una lama) ──
# Un nastro d'argento senza squame: la dorsale bassa da dietro la testa quasi alla coda, la coda minuscola.
SPECIE['sciabola_spolpata'] = Specie(
    forma=Shape(
        top=[(0, -0.002), (0.02, 0.008), (0.06, 0.022), (0.12, 0.033), (0.25, 0.038), (0.6, 0.034), (0.85, 0.02), (0.95, 0.01),
             (1, 0.005)],
        bot=[(0, -0.009), (0.03, -0.017), (0.08, -0.027), (0.15, -0.033), (0.4, -0.036), (0.7, -0.03), (0.9, -0.014), (1, -0.005)],
        w=[(0, 0.003), (0.05, 0.01), (0.15, 0.013), (0.5, 0.011), (0.8, 0.006), (1, 0.002)],
        eye_t=0.068, eye_z=0.008, eye_r=0.012, mouth_t=0.07, mouth_z0=-0.006, mouth_z1=-0.004, gill_t=0.13,
        fins=[Fin('dorsal', 0.11, 0.97, [(0, 0), (0.01, 0.9), (0.5, 1.0), (0.95, 0.8), (1, 0.2)], 0.022, 130, spiny=True),
              Fin('anal', 0.78, 0.95, [(0, 0), (0.1, 0.6), (0.9, 0.5), (1, 0.1)], 0.006, 20),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.4, 0.3), 0.045, 12),
              Fin('pectoral', 0.135, 0.145, PETTORALE, 0.035, 8)],
        piega=[(0, 0), (0.35, 5), (0.7, -5), (1, 3)]),
    aspetto=Look(back=(0.42, 0.45, 0.5), flank=(0.66, 0.68, 0.7), belly=(0.72, 0.73, 0.74), fin=(0.55, 0.58, 0.6),
                 iris=(0.85, 0.82, 0.7), iris_dark=(0.15, 0.15, 0.12), metal=0.92, irid=0.3, squame=0.0,
                 linea_laterale=0.5, linea_v=(0.0, 0.0), lucido=0.8),
    extra=_denti_sciabola,
    famiglia='normale', piano='nastriforme')


# ── Spadossa (pesce spada, Xiphias gladius) — PROVA DEL PIANO 'rostro': forma normale, ancora da trasformare
#    nella famiglia (solo la spada e lo scheletro, il braccialetto fucsia infilato sulla spada) ──
# La spada è un Rostro piatto (largo in y, sottile in z); le pinne rigide sono carnose; niente pelviche.
SPECIE['spadossa'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.03, 0.02), (0.08, 0.055), (0.15, 0.085), (0.25, 0.105), (0.4, 0.11), (0.55, 0.1), (0.7, 0.075),
             (0.85, 0.042), (0.95, 0.022), (1, 0.017)],
        bot=[(0, -0.022), (0.04, -0.04), (0.1, -0.065), (0.2, -0.09), (0.35, -0.1), (0.5, -0.095), (0.65, -0.075), (0.8, -0.045),
             (0.95, -0.02), (1, -0.017)],
        w=[(0, 0.006), (0.06, 0.035), (0.2, 0.07), (0.4, 0.075), (0.65, 0.055), (0.85, 0.03), (1, 0.016)],
        eye_t=0.085, eye_z=0.018, eye_r=0.02, mouth_t=0.085, mouth_z0=-0.02, mouth_z1=-0.032, gill_t=0.2,
        rostro=Rostro('spada', lunghezza=0.45, z=0.0, larghezza=0.024, altezza=0.0075, punta=0.12),
        fins=[Fin('dorsal', 0.19, 0.3, [(0, 0), (0.12, 0.8), (0.25, 1.0), (0.36, 0.45), (0.55, 0.15), (1, 0.06)], 0.2, 40,
                  carnosa=True, spessore=0.006),
              Fin('dorsal', 0.9, 0.92, [(0, 0), (0.3, 1.0), (1, 0.1)], 0.025, 10, carnosa=True, spessore=0.003),
              Fin('anal', 0.62, 0.7, [(0, 0), (0.15, 0.9), (0.3, 1.0), (0.45, 0.4), (1, 0.06)], 0.075, 24, carnosa=True, spessore=0.004),
              Fin('anal', 0.89, 0.91, [(0, 0), (0.3, 1.0), (1, 0.1)], 0.02, 10, carnosa=True, spessore=0.003),
              Fin('caudal', 1.0, 1.0, coda_falcata(3.2, 0.95, radice=0.25), 0.3, 60, carnosa=True, spessore=0.006),
              Fin('pectoral', 0.2, 0.24, [(0, 0.06), (0.4, 0.1), (1.0, 0.02), (0.75, -0.06), (0.3, -0.12), (0, -0.1)], 0.18, 30,
                  carnosa=True, spessore=0.004, dir=(0.7, 0.3, -0.55))]),
    aspetto=Look(back=(0.05, 0.04, 0.07), flank=(0.2, 0.18, 0.22), belly=(0.55, 0.53, 0.52), fin=(0.07, 0.06, 0.09),
                 iris=(0.3, 0.35, 0.4), iris_dark=(0.05, 0.06, 0.08), metal=0.35, irid=0.15, squame=0.0, linea_laterale=0.0,
                 lucido=0.5),
    famiglia='normale', piano='rostro')


# ── Ossaguglia (aguglia, Belone belone) — PROVA DEL BECCO (piano 'rostro'): forma normale, ancora da
#    trasformare nella famiglia (le ossa verdi, il becco pieno di dentini che punge) ──
# Lunghissima e sottile; le due mascelle a becco sono un Rostro('becco') alla quota della bocca (il taglio
# arriva in punta e lo divide in due), con i dentini sui bordi (denti); dorsale e anale arretrate e opposte,
# coda forcuta con il lobo di sotto più lungo; dorso verde-azzurro, fianchi d'argento.
SPECIE['ossaguglia'] = Specie(
    forma=Shape(
        top=[(0, 0.004), (0.02, 0.012), (0.06, 0.022), (0.12, 0.03), (0.25, 0.037), (0.45, 0.04), (0.62, 0.038), (0.75, 0.032),
             (0.88, 0.021), (0.96, 0.014), (1, 0.012)],
        bot=[(0, -0.006), (0.03, -0.014), (0.08, -0.023), (0.18, -0.032), (0.4, -0.038), (0.6, -0.037), (0.75, -0.031),
             (0.88, -0.021), (0.96, -0.013), (1, -0.012)],
        w=[(0, 0.007), (0.05, 0.016), (0.15, 0.024), (0.4, 0.028), (0.65, 0.025), (0.85, 0.015), (1, 0.008)],
        eye_t=0.055, eye_z=0.007, eye_r=0.0135, mouth_t=0.05, mouth_z0=-0.0015, mouth_z1=-0.004, gill_t=0.13,
        rostro=Rostro('becco', lunghezza=0.42, z=-0.0015, larghezza=0.0085, altezza=0.0095, punta=0.3, denti=28),
        fins=[Fin('dorsal', 0.68, 0.86, [(0, 0), (0.06, 0.95), (0.2, 0.7), (0.6, 0.55), (0.9, 0.75), (1, 0.35)], 0.04, 22),
              Fin('anal', 0.65, 0.84, [(0, 0), (0.06, 0.95), (0.2, 0.7), (0.6, 0.55), (0.9, 0.7), (1, 0.3)], 0.036, 22),
              Fin('caudal', 1.0, 1.0, [(0.0, 1.0), (0.5, 1.1), (0.95, 1.5), (0.32, 0.0), (1.1, -1.75), (0.55, -1.1), (0.0, -1.0)],
                  0.12, 18),
              Fin('pectoral', 0.12, 0.13, PETTORALE, 0.06, 9, z=0.25),
              Fin('pelvic', 0.5, 0.51, PELVICA, 0.04, 6)]),
    aspetto=Look(back=(0.02, 0.1, 0.11), flank=(0.38, 0.44, 0.45), belly=(0.72, 0.74, 0.72), fin=(0.1, 0.16, 0.17),
                 iris=(0.75, 0.72, 0.55), iris_dark=(0.1, 0.1, 0.08), metal=0.7, irid=0.45, squame=0.25,
                 linea_laterale=0.0,
                 disegni=[Disegno('ventre', colore=(0.8, 0.82, 0.84), forza=0.6, v1=-0.3)]),
    famiglia='normale', piano='rostro')


# ── Cavalluccio d'Osso (cavalluccio marino, Hippocampus guttulatus) — PROVA DEL PIANO 'cavalluccio': forma
#    normale, ancora da trasformare nella famiglia (le ossa del cavallino da giostra) ──
# Si costruisce dritto (muso a tubo in −X, coda in +X) e piega curva l'asse: la testa resta orizzontale, il
# collo scende ad angolo retto, la coda si arrotola in avanti. Gli anelli ossei sono Shape.anelli.
SPECIE['cavalluccio_dosso'] = Specie(
    forma=Shape(
        top=[(0, 0.004), (0.03, 0.03), (0.08, 0.044), (0.12, 0.038), (0.16, 0.034), (0.25, 0.048), (0.35, 0.054), (0.45, 0.042),
             (0.6, 0.028), (0.8, 0.016), (1.0, 0.006)],
        bot=[(0, -0.008), (0.03, -0.028), (0.08, -0.034), (0.12, -0.03), (0.16, -0.036), (0.25, -0.066), (0.35, -0.07),
             (0.45, -0.046), (0.6, -0.028), (0.8, -0.016), (1, -0.006)],
        w=[(0, 0.007), (0.05, 0.02), (0.12, 0.022), (0.2, 0.034), (0.35, 0.037), (0.5, 0.025), (0.8, 0.013), (1, 0.005)],
        eye_t=0.06, eye_z=0.012, eye_r=0.011, bocca='nessuna', gill_t=0.12, anelli=38, anelli_tratto=(0.15, 0.99),
        rostro=Rostro('tubo', lunghezza=0.08, z=-0.004, larghezza=0.0085, altezza=0.0095, punta=0.8),
        filamenti=[Filamento(t=0.085, v=1.0, lunghezza=0.028, raggio=0.004, dir=(0.15, 0.0, 1.0), lati='centro', punta=0.5),
                   Filamento(t=0.24, v=0.95, lunghezza=0.022, raggio=0.002, dir=(0.4, 0.5, 1.0), curva=(4, 0, 0)),
                   Filamento(t=0.33, v=0.95, lunghezza=0.018, raggio=0.002, dir=(0.4, 0.5, 1.0), curva=(4, 0, 0)),
                   Filamento(t=0.05, v=0.6, lunghezza=0.016, raggio=0.0018, dir=(0.2, 0.6, 1.0))],
        fins=[Fin('dorsal', 0.37, 0.5, [(0, 0), (0.1, 0.9), (0.5, 1.0), (0.9, 0.9), (1, 0.1)], 0.035, 20),
              Fin('pectoral', 0.13, 0.14, PETTORALE_TONDA, 0.03, 9, z=0.1)],
        piega=[(0, 0), (0.1, 0), (0.15, -40), (0.2, -92), (0.45, -100), (0.55, -95), (0.7, -150), (0.82, -240), (0.92, -330),
               (1.0, -400)]),
    aspetto=Look(back=(0.24, 0.17, 0.09), flank=(0.3, 0.21, 0.12), belly=(0.36, 0.27, 0.15), fin=(0.4, 0.33, 0.24),
                 iris=(0.75, 0.6, 0.3), iris_dark=(0.2, 0.12, 0.04), metal=0.05, irid=0.1, squame=0.0, linea_laterale=0.0,
                 disegni=[Disegno('punti', colore=(0.82, 0.8, 0.72), forza=0.85, scala=150, r=0.17)]),
    famiglia='normale', piano='cavalluccio')


# ── Lanternossa (pesce lanterna, Myctophum punctatum) — PROVA DEI FOTOFORI (piano 'fusiforme'): forma normale,
#    ancora da trasformare nella famiglia (le lucine restano accese sulle ossa) ──
# Le file di lucine sul fianco basso sono Shape.fotofori (sferette luminose appena affondate nella pelle).
SPECIE['lanternossa'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.03), (0.08, 0.065), (0.18, 0.09), (0.35, 0.1), (0.55, 0.09), (0.75, 0.06), (0.9, 0.035),
             (1, 0.03)],
        bot=[(0, -0.03), (0.04, -0.06), (0.12, -0.085), (0.3, -0.1), (0.5, -0.095), (0.7, -0.068), (0.9, -0.035), (1, -0.03)],
        w=[(0, 0.01), (0.06, 0.035), (0.2, 0.045), (0.5, 0.04), (0.8, 0.022), (1, 0.012)],
        eye_t=0.1, eye_z=0.016, eye_r=0.038, mouth_t=0.14, mouth_z0=-0.004, mouth_z1=-0.042, gill_t=0.23,
        fotofori=Fotofori(righe=[(0.16, 0.4, -0.86, 6), (0.44, 0.72, -0.8, 6), (0.76, 0.95, -0.66, 5), (0.22, 0.5, -0.52, 4),
                                 (0.56, 0.8, -0.42, 4), (0.05, 0.1, -0.55, 2)],
                          sparsi=3, raggio=0.0058, colore=(0.35, 0.8, 1.0), forza=4.0),
        fins=[Fin('dorsal', 0.4, 0.55, [(0, 0), (0.15, 0.9), (0.45, 1.0), (0.8, 0.6), (1, 0.05)], 0.08, 12),
              Fin('dorsal', 0.79, 0.85, [(0, 0), (0.3, 0.9), (0.7, 0.8), (1, 0.05)], 0.02, 8, carnosa=True, spessore=0.003),
              Fin('anal', 0.55, 0.75, [(0, 0), (0.1, 0.85), (0.6, 0.6), (1, 0.05)], 0.06, 14),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.6, 0.3), 0.21, 18),
              Fin('pectoral', 0.23, 0.24, PETTORALE, 0.08, 9),
              Fin('pelvic', 0.38, 0.39, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.03, 0.04, 0.06), flank=(0.3, 0.33, 0.38), belly=(0.42, 0.44, 0.47), fin=(0.18, 0.2, 0.22),
                 iris=(0.4, 0.45, 0.5), iris_dark=(0.04, 0.05, 0.06), metal=0.7, irid=0.3, squame=1.0),
    famiglia='normale', piano='fusiforme')


# ── Sega d'Ossa (pesce sega, Pristis pectinata) — PROVA DEL ROSTRO A SEGA SU UNA RAZZA (piano 'razza'): forma
#    normale, ancora da trasformare nella famiglia (le ossa di un pesce che non c'è più da cent'anni) ──
# Come le razze, costruito con il dorso verso la camera: z è la larghezza, y lo spessore. Il corpo è quasi da
# squalo (disco stretto: pettorali e pelviche come lobi), la sega è un Rostro largo in z con i denti sui bordi.
SPECIE['sega_dossa'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.03, 0.035), (0.1, 0.055), (0.25, 0.07), (0.4, 0.068), (0.55, 0.055), (0.7, 0.04), (0.85, 0.025), (1, 0.015)],
        bot=[(0, 0.0), (0.03, -0.035), (0.1, -0.055), (0.25, -0.07), (0.4, -0.068), (0.55, -0.055), (0.7, -0.04), (0.85, -0.025),
             (1, -0.015)],
        w=[(0, 0.004), (0.05, 0.015), (0.15, 0.028), (0.35, 0.04), (0.55, 0.038), (0.75, 0.028), (0.9, 0.018), (1, 0.012)],
        eye_t=0.08, eye_z=0.0, eye_r=0.009, occhi=[(0.08, 0.034, 0.009, -1), (0.08, -0.034, 0.009, -1)], spiracoli=0.006,
        bocca='nessuna', branchie='nessuna',
        rostro=Rostro('sega', lunghezza=0.34, z=0.0, larghezza=0.008, altezza=0.03, punta=0.62, denti=22),
        disco=Disco(contorno=[(0, 0.0), (0.05, 0.04), (0.14, 0.062), (0.2, 0.1), (0.26, 0.15), (0.31, 0.155), (0.35, 0.08),
                              (0.4, 0.062), (0.47, 0.072), (0.52, 0.1), (0.56, 0.098), (0.6, 0.05), (0.65, 0.0), (1, 0.0)],
                    spessore=[(0, 0.003), (0.15, 0.01), (0.3, 0.012), (0.5, 0.01), (0.62, 0.004), (1, 0.001)]),
        fins=[Fin('dorsal', 0.44, 0.52, DORSALE_SQUALO, 0.07, 24, carnosa=True, spessore=0.005),
              Fin('dorsal', 0.7, 0.77, DORSALE_SQUALO, 0.06, 24, carnosa=True, spessore=0.004),
              Fin('caudal', 1.0, 1.0, coda_eterocerca(lobo=1.0, alzata=1.2, lobo_basso=0.4, basso=0.8), 0.16, 40,
                  carnosa=True, spessore=0.005)]),
    aspetto=Look(back=(0.26, 0.25, 0.2), flank=(0.32, 0.31, 0.26), belly=(0.82, 0.8, 0.76), fin=(0.24, 0.23, 0.19),
                 iris=(0.6, 0.55, 0.35), iris_dark=(0.12, 0.1, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.35, ruvido=0.5, tinta_rostro=0.4),
    famiglia='normale', piano='razza')
