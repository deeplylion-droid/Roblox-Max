"""
Sanguinanti: ferite, denti sporchi, colature (src/game/catalog.ts, docs/CATALOGO.md).

Una voce per specie: SPECIE['id'] = Specie(forma, aspetto, famiglia, piano, ...). Il brief per aggiungere le
altre è in PIANO.md (accanto a questo file); si prova con
    tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast
"""
from .base import (DORSALE_FALCE, DORSALE_SQUALO, DORSALE_TRIANGOLO, PELVICA, PETTORALE, RITRATTO_PROTOTIPI, Disco,
                   DiscoOrale, Disegno, Fin, Look, Ritratto, Shape, Specie, Spine, Ventosa, coda_appuntita,
                   coda_eterocerca, coda_falcata, coda_forcuta, coda_tronca)

SPECIE = {}

# ── Barracruda (luccio di mare, Sphyraena sphyraena) — PROTOTIPO APPROVATO: non cambiare ──
SPECIE['barracruda'] = Specie(
    forma=Shape(
        top=[(0, -0.018), (0.06, 0.006), (0.15, 0.04), (0.3, 0.06), (0.5, 0.066), (0.7, 0.055), (0.88, 0.031), (1, 0.026)],
        bot=[(0, -0.024), (0.04, -0.034), (0.15, -0.05), (0.3, -0.062), (0.5, -0.064), (0.7, -0.052), (0.88, -0.03), (1, -0.026)],
        w=[(0, 0.007), (0.08, 0.023), (0.25, 0.04), (0.5, 0.043), (0.75, 0.032), (1, 0.013)],
        eye_t=0.105, eye_z=0.016, eye_r=0.018, mouth_t=0.13, mouth_z0=-0.012, mouth_z1=-0.008, gill_t=0.19,
        fins=[Fin('dorsal', 0.38, 0.45, [(0, 0), (0.2, 0.95), (0.55, 0.85), (1, 0.05)], 0.06, 6, spiny=True),
              Fin('dorsal', 0.66, 0.73, [(0, 0), (0.25, 0.85), (0.7, 0.55), (1, 0.05)], 0.05, 8),
              Fin('anal', 0.67, 0.74, [(0, 0), (0.25, 0.8), (0.7, 0.5), (1, 0.05)], 0.045, 8),
              Fin('caudal', 1.0, 1.0, coda_forcuta(1.5, 0.32), 0.15, 18),
              Fin('pectoral', 0.2, 0.215, [(0, 0), (0.5, 0.3), (1.0, 0.12), (0.8, 0.0), (0, -0.05)], 0.08, 9),
              Fin('pelvic', 0.38, 0.395, [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)], 0.06, 6)]),
    aspetto=Look(back=(0.10, 0.13, 0.17), flank=(0.46, 0.49, 0.52), belly=(0.68, 0.68, 0.66), fin=(0.26, 0.27, 0.24),
                 iris=(0.7, 0.68, 0.55), iris_dark=(0.12, 0.12, 0.1), pattern='barracuda'),
    famiglia='bleeding', piano='fusiforme', ritratto=RITRATTO_PROTOTIPI)


# ── Volpe Sfregiata (squalo volpe, Alopias vulpinus) — PROVA DEL PIANO 'squalo': forma normale, ancora da
#    trasformare nella famiglia (ferite, cicatrici sulla coda: «una cicatrice per ogni volta che ha mancato») ──
SPECIE['volpe_sfregiata'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.02, 0.018), (0.06, 0.044), (0.12, 0.068), (0.22, 0.09), (0.36, 0.1), (0.5, 0.09), (0.65, 0.064),
             (0.8, 0.04), (0.92, 0.024), (1, 0.018)],
        bot=[(0, -0.012), (0.03, -0.034), (0.08, -0.054), (0.18, -0.078), (0.32, -0.094), (0.48, -0.088), (0.62, -0.066),
             (0.78, -0.038), (0.92, -0.022), (1, -0.018)],
        w=[(0, 0.004), (0.04, 0.03), (0.12, 0.058), (0.3, 0.078), (0.5, 0.07), (0.7, 0.044), (0.9, 0.021), (1, 0.014)],
        eye_t=0.085, eye_z=0.018, eye_r=0.017,
        bocca='ventrale', mouth_a=0.07, mouth_t=0.118, mouth_z1=-0.03, mouth_z0=-0.03,
        branchie='fessure', gill_t=0.165, n_branchie=5, passo_branchie=0.017,
        fins=[Fin('dorsal', 0.37, 0.49, DORSALE_SQUALO, 0.135, 30, carnosa=True, spessore=0.007),
              Fin('dorsal', 0.86, 0.885, DORSALE_SQUALO, 0.02, 12, carnosa=True, spessore=0.003),
              Fin('anal', 0.875, 0.9, DORSALE_SQUALO, 0.018, 12, carnosa=True, spessore=0.003),
              # il lobo di sopra lungo quanto il corpo, stretto come una falce; quello di sotto piccolo
              Fin('caudal', 1.0, 1.0, [(0, 0.12), (0.6, 0.75), (1.2, 1.32), (1.8, 1.82), (2.3, 2.2), (2.18, 1.98), (1.6, 1.45),
                                      (1.0, 0.9), (0.52, 0.32), (0.4, -0.05), (0.33, -0.45), (0.26, -0.78), (0.1, -0.15)],
                  0.42, 60, carnosa=True, spessore=0.006),
              Fin('pectoral', 0.2, 0.25, [(0, 0.08), (0.45, 0.13), (1.0, 0.03), (0.82, -0.08), (0.35, -0.18), (0, -0.14)], 0.24, 30,
                  carnosa=True, spessore=0.006, dir=(0.75, 0.3, -0.6)),
              Fin('pelvic', 0.56, 0.6, [(0, 0.05), (0.6, 0.06), (1.0, -0.02), (0.6, -0.12), (0, -0.1)], 0.075, 20,
                  carnosa=True, spessore=0.004)]),
    aspetto=Look(back=(0.05, 0.05, 0.08), flank=(0.13, 0.13, 0.17), belly=(0.70, 0.70, 0.68), fin=(0.08, 0.08, 0.11),
                 iris=(0.12, 0.13, 0.14), iris_dark=(0.03, 0.03, 0.04), metal=0.12, irid=0.08, squame=0.0,
                 linea_laterale=0.0, lucido=0.35, ruvido=0.45),
    famiglia='normale', piano='squalo')


# ── Verdesca Ferita (verdesca, Prionace glauca) — PROVA DELLA CODA ETEROCERCA (piano 'squalo'): forma normale,
#    ancora da trasformare nella famiglia (le ferite profonde: «il sangue era il suo») ──
# Lo squalo di sempre: slanciatissimo, muso lungo e appuntito, occhio grande; le pettorali lunghissime a falce,
# la prima dorsale arretrata, la coda eterocerca dell'aiuto comune (coda_eterocerca); indaco sopra, bianco sotto.
SPECIE['verdesca_ferita'] = Specie(
    forma=Shape(
        top=[(0, -0.004), (0.02, 0.01), (0.06, 0.026), (0.12, 0.042), (0.22, 0.057), (0.36, 0.065), (0.5, 0.06), (0.65, 0.046),
             (0.8, 0.03), (0.92, 0.019), (1, 0.015)],
        bot=[(0, -0.01), (0.03, -0.02), (0.08, -0.032), (0.18, -0.048), (0.32, -0.059), (0.46, -0.056), (0.6, -0.044),
             (0.75, -0.028), (0.9, -0.017), (1, -0.015)],
        w=[(0, 0.004), (0.04, 0.02), (0.12, 0.038), (0.3, 0.05), (0.5, 0.045), (0.7, 0.031), (0.9, 0.017), (1, 0.011)],
        eye_t=0.072, eye_z=0.006, eye_r=0.0155,
        bocca='ventrale', mouth_a=0.075, mouth_t=0.118, mouth_z1=-0.026, mouth_z0=-0.026,
        branchie='fessure', gill_t=0.165, n_branchie=5, passo_branchie=0.016,
        fins=[Fin('dorsal', 0.42, 0.52, DORSALE_SQUALO, 0.085, 30, carnosa=True, spessore=0.006),
              Fin('dorsal', 0.83, 0.855, DORSALE_SQUALO, 0.022, 12, carnosa=True, spessore=0.003),
              Fin('anal', 0.82, 0.85, DORSALE_SQUALO, 0.02, 12, carnosa=True, spessore=0.003),
              Fin('caudal', 1.0, 1.0, coda_eterocerca(lobo=1.0, alzata=1.9, lobo_basso=0.45, basso=1.45), 0.27, 50,
                  carnosa=True, spessore=0.006),
              # le pettorali lunghe e strette, a falce, che scendono all'indietro dietro le fessure
              Fin('pectoral', 0.2, 0.24, [(0, 0.06), (0.5, 0.055), (1.0, -0.06), (0.9, -0.1), (0.4, -0.13), (0, -0.11)], 0.32, 30,
                  carnosa=True, spessore=0.005, dir=(0.8, 0.35, -0.5)),
              Fin('pelvic', 0.6, 0.64, [(0, 0.05), (0.6, 0.06), (1.0, -0.02), (0.6, -0.12), (0, -0.1)], 0.06, 20,
                  carnosa=True, spessore=0.004)]),
    aspetto=Look(back=(0.01, 0.03, 0.12), flank=(0.04, 0.12, 0.34), belly=(0.74, 0.75, 0.77), fin=(0.02, 0.06, 0.2),
                 iris=(0.12, 0.13, 0.15), iris_dark=(0.02, 0.02, 0.03), metal=0.1, irid=0.1, squame=0.0,
                 linea_laterale=0.0, lucido=0.35, ruvido=0.45),
    famiglia='normale', piano='squalo')


# ── Razza Inchiodata (razza chiodata, Raja clavata) — PROVA DEL PIANO 'razza': forma normale, ancora da
#    trasformare nella famiglia (le spine diventano chiodi arrugginiti) ──
# Costruita con il dorso verso la camera (−Y): z è l'apertura delle ali, y lo spessore. I profili top/bot/w
# sono il tronco (la gobba al centro e la coda), il disco delle pettorali è Shape.disco.
SPECIE['razza_inchiodata'] = Specie(
    forma=Shape(
        top=[(0, 0.0), (0.05, 0.03), (0.15, 0.058), (0.3, 0.068), (0.45, 0.055), (0.55, 0.034), (0.65, 0.017), (0.8, 0.011),
             (0.95, 0.007), (1, 0.005)],
        bot=[(0, 0.0), (0.05, -0.03), (0.15, -0.058), (0.3, -0.068), (0.45, -0.055), (0.55, -0.034), (0.65, -0.017), (0.8, -0.011),
             (0.95, -0.007), (1, -0.005)],
        w=[(0, 0.003), (0.05, 0.011), (0.15, 0.024), (0.3, 0.03), (0.45, 0.025), (0.55, 0.017), (0.65, 0.011), (0.8, 0.008),
           (0.95, 0.006), (1, 0.005)],
        eye_t=0.13, eye_z=0.0, eye_r=0.011,
        occhi=[(0.125, 0.03, 0.0105, -1), (0.125, -0.03, 0.0105, -1)], spiracoli=0.0055,
        bocca='nessuna', branchie='nessuna',
        disco=Disco(contorno=[(0, 0.0), (0.03, 0.05), (0.1, 0.15), (0.18, 0.26), (0.245, 0.34), (0.275, 0.35), (0.32, 0.315),
                              (0.39, 0.21), (0.45, 0.115), (0.5, 0.08), (0.555, 0.088), (0.6, 0.064), (0.64, 0.025), (0.68, 0.0),
                              (1.0, 0.0)],
                    spessore=[(0, 0.003), (0.12, 0.012), (0.3, 0.015), (0.45, 0.013), (0.6, 0.008), (0.68, 0.002), (1.0, 0.001)]),
        spine=[Spine(0.1, 0.94, 0.0, 0.0, 28, lunghezza=0.011, raggio=0.0042, lati='sinistro', inclinazione=0.55, fila=True),
               Spine(0.14, 0.42, -3.4, 3.4, 16, lunghezza=0.009, raggio=0.005, lati='sinistro', inclinazione=0.45, seme=3)],
        fins=[Fin('dorsal', 0.82, 0.86, [(0, 0), (0.25, 0.9), (0.55, 1.0), (0.8, 0.5), (1, 0.05)], 0.028, 16, carnosa=True, spessore=0.004),
              Fin('dorsal', 0.88, 0.92, [(0, 0), (0.25, 0.9), (0.55, 1.0), (0.8, 0.5), (1, 0.05)], 0.026, 16, carnosa=True, spessore=0.004),
              Fin('caudal', 1.0, 1.0, [(0, 0.5), (0.5, 0.7), (1.0, 0.0), (0.5, -0.5), (0, -0.4)], 0.03, 16, carnosa=True, spessore=0.003)]),
    aspetto=Look(back=(0.20, 0.155, 0.11), flank=(0.26, 0.21, 0.16), belly=(0.84, 0.82, 0.78), fin=(0.18, 0.14, 0.1),
                 iris=(0.55, 0.5, 0.3), iris_dark=(0.1, 0.09, 0.05), metal=0.0, irid=0.0, squame=0.0, linea_laterale=0.0,
                 lucido=0.35, ruvido=0.5,
                 disegni=[Disegno('marmo', colore=(0.11, 0.08, 0.055), forza=0.7, scala=30, r=0.45),
                          Disegno('macchie', colore=(0.05, 0.035, 0.025), forza=0.85, scala=45, r=0.2),
                          Disegno('macchie', colore=(0.62, 0.55, 0.42), forza=0.7, scala=70, r=0.13, seme=5)]),
    famiglia='normale', piano='razza')


# ── Lampreda Vampira (lampreda di mare, Petromyzon marinus) — PROVA DEL DISCO ORALE (piano 'anguilliforme'):
#    forma normale, ancora da trasformare nella famiglia ──
# Al posto della bocca la ventosa rotonda con gli anelli di denti (Shape.disco_orale); sette pori branchiali
# tondi; due dorsali, la seconda unita alla coda. Il ritratto gira la testa verso la camera per far vedere il disco.
SPECIE['lampreda_vampira'] = Specie(
    forma=Shape(
        top=[(0, -0.012), (0.03, 0.012), (0.08, 0.026), (0.2, 0.034), (0.5, 0.036), (0.75, 0.03), (0.9, 0.018), (1, 0.004)],
        bot=[(0, -0.03), (0.04, -0.034), (0.1, -0.034), (0.3, -0.036), (0.6, -0.034), (0.85, -0.022), (1, -0.004)],
        w=[(0, 0.02), (0.05, 0.027), (0.2, 0.031), (0.5, 0.029), (0.75, 0.02), (0.9, 0.01), (1, 0.003)],
        eye_t=0.075, eye_z=0.013, eye_r=0.009, bocca='nessuna',
        disco_orale=DiscoOrale(raggio=0.03, anelli=4, denti=14, inclinazione=40.0),
        branchie='pori', n_branchie=7, gill_t=0.11, passo_branchie=0.016,
        fins=[Fin('dorsal', 0.56, 0.67, [(0, 0), (0.2, 0.9), (0.6, 1.0), (1, 0.15)], 0.026, 16),
              Fin('dorsal', 0.71, 1.0, [(0, 0), (0.1, 0.8), (0.4, 1.0), (0.85, 0.8), (1, 0.6)], 0.032, 36),
              Fin('anal', 0.9, 1.0, [(0, 0), (0.3, 0.7), (1, 0.6)], 0.012, 10),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.9, 1.0), 0.045, 14)],
        piega=[(0, 14), (0.3, -10), (0.65, 12), (1.0, -8)]),
    aspetto=Look(back=(0.2, 0.18, 0.12), flank=(0.3, 0.27, 0.19), belly=(0.62, 0.57, 0.46), fin=(0.25, 0.22, 0.16),
                 iris=(0.7, 0.62, 0.35), iris_dark=(0.15, 0.12, 0.05), metal=0.0, irid=0.05, squame=0.0, linea_laterale=0.0,
                 lucido=0.65, ruvido=0.3,
                 disegni=[Disegno('marmo', colore=(0.06, 0.05, 0.035), forza=0.8, scala=22, r=0.55)]),
    ritratto=Ritratto(yaw=38.0, pitch=10.0),
    famiglia='normale', piano='anguilliforme')


# ── Remora Strappata (remora, Remora remora) — PROVA DELLA VENTOSA (piano 'fusiforme'): forma normale, ancora
#    da trasformare nella famiglia (il pezzo di pelle grigia di Gulpy sulla ventosa) ──
# Il disco adesivo con le lamelle sta sul capo piatto (Shape.ventosa); il ritratto mostra un po' il dorso.
SPECIE['remora_strappata'] = Specie(
    forma=Shape(
        top=[(0, -0.006), (0.02, 0.01), (0.06, 0.03), (0.12, 0.042), (0.2, 0.047), (0.28, 0.049), (0.4, 0.052), (0.6, 0.048),
             (0.8, 0.032), (0.95, 0.02), (1, 0.017)],
        bot=[(0, -0.02), (0.03, -0.033), (0.1, -0.048), (0.3, -0.06), (0.5, -0.058), (0.7, -0.045), (0.9, -0.024), (1, -0.017)],
        w=[(0, 0.008), (0.05, 0.03), (0.15, 0.045), (0.35, 0.048), (0.6, 0.04), (0.85, 0.022), (1, 0.012)],
        eye_t=0.1, eye_z=0.01, eye_r=0.012, mouth_t=0.06, mouth_z0=-0.013, mouth_z1=-0.015, gill_t=0.21,
        ventosa=Ventosa(t0=0.035, t1=0.27, larghezza=0.034, lamelle=18),
        fins=[Fin('dorsal', 0.55, 0.8, [(0, 0), (0.08, 1.0), (0.25, 0.7), (0.9, 0.5), (1, 0.05)], 0.05, 22),
              Fin('anal', 0.56, 0.8, [(0, 0), (0.08, 1.0), (0.25, 0.7), (0.9, 0.5), (1, 0.05)], 0.05, 22),
              Fin('caudal', 1.0, 1.0, coda_tronca(1.6, 0.25, 0.85), 0.16, 16),
              Fin('pectoral', 0.22, 0.23, PETTORALE, 0.08, 10, z=0.25),
              Fin('pelvic', 0.25, 0.26, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.16, 0.15, 0.14), flank=(0.2, 0.19, 0.18), belly=(0.24, 0.23, 0.21), fin=(0.15, 0.14, 0.13),
                 iris=(0.6, 0.55, 0.4), iris_dark=(0.12, 0.1, 0.06), metal=0.15, irid=0.1, squame=0.4),
    ritratto=Ritratto(yaw=12.0, pitch=-2.0, roll=40.0),
    famiglia='normale', piano='fusiforme')


# ── Tonno di Sangue (tonno rosso, Thunnus thynnus) — PROVA DEL PIANO 'fusiforme': forma normale, ancora da
#    trasformare nella famiglia (le mattanze) ──
# Il fuso di sempre, con le pinnule gialle (tante dorsali e anali piccole) e la coda a mezzaluna.
_PINNULA = [(0, 0), (0.25, 1.0), (1, 0.15)]
SPECIE['tonno_di_sangue'] = Specie(
    forma=Shape(
        top=[(0, -0.01), (0.03, 0.03), (0.08, 0.075), (0.16, 0.115), (0.3, 0.14), (0.42, 0.142), (0.55, 0.125), (0.7, 0.085),
             (0.82, 0.045), (0.92, 0.022), (1, 0.016)],
        bot=[(0, -0.025), (0.04, -0.055), (0.12, -0.095), (0.25, -0.13), (0.4, -0.138), (0.55, -0.12), (0.7, -0.08), (0.82, -0.042),
             (0.92, -0.02), (1, -0.016)],
        w=[(0, 0.008), (0.06, 0.05), (0.2, 0.1), (0.4, 0.11), (0.6, 0.085), (0.8, 0.04), (0.92, 0.02), (1, 0.014)],
        eye_t=0.1, eye_z=0.025, eye_r=0.02, mouth_t=0.075, mouth_z0=-0.015, mouth_z1=-0.03, gill_t=0.21,
        fins=[Fin('dorsal', 0.3, 0.42, DORSALE_TRIANGOLO, 0.1, 13, spiny=True),
              Fin('dorsal', 0.45, 0.52, DORSALE_FALCE, 0.13, 12),
              Fin('anal', 0.5, 0.57, DORSALE_FALCE, 0.11, 12)]
             + [Fin('dorsal', 0.6 + 0.04 * i, 0.62 + 0.04 * i, _PINNULA, 0.022, 4, colore=(0.75, 0.6, 0.15)) for i in range(8)]
             + [Fin('anal', 0.62 + 0.04 * i, 0.64 + 0.04 * i, _PINNULA, 0.02, 4, colore=(0.75, 0.6, 0.15)) for i in range(7)]
             + [Fin('caudal', 1.0, 1.0, coda_falcata(2.9, 0.85, radice=0.3), 0.3, 26),
                Fin('pectoral', 0.24, 0.255, PETTORALE, 0.12, 12),
                Fin('pelvic', 0.3, 0.31, PELVICA, 0.05, 6)]),
    aspetto=Look(back=(0.02, 0.04, 0.09), flank=(0.36, 0.4, 0.46), belly=(0.72, 0.73, 0.74), fin=(0.12, 0.13, 0.16),
                 iris=(0.55, 0.55, 0.5), iris_dark=(0.08, 0.08, 0.08), metal=0.75, irid=0.4, squame=0.3,
                 disegni=[Disegno('ventre', colore=(0.78, 0.8, 0.82), forza=0.6, v1=-0.35),
                          Disegno('bande', colore=(0.82, 0.84, 0.86), forza=0.35, n=14, u0=0.3, u1=0.85, v0=-0.75, v1=-0.15,
                                  larghezza=0.25, onda=0.05)]),
    famiglia='normale', piano='fusiforme')
