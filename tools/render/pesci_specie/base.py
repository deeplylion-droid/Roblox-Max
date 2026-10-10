"""
I dati delle specie del Catalogo, che tools/render/pesci.py costruisce e rende.

Qui non c'è Blender: solo le classi dei dati (forma, aspetto, pinne, disegni della pelle, elementi in più,
ritratto, la voce del registro) e pochi aiuti per scriverli (sagome di code e pinne, i piani corporei).

Coordinate del generatore: il corpo è lungo 1, il muso in x = 0 guarda verso −X, l'attacco della coda è in
x = 1, il dorso verso +Z, il fianco sinistro verso −Y (la camera). t è la posizione lungo il corpo (0 muso …
1 coda), v la quota normalizzata sulla sezione (−1 ventre … 0 asse … +1 dorso). Le misure sono frazioni
della lunghezza del corpo.

I pesci che si guardano dall'alto (piani 'piatto' e 'razza') si costruiscono con il DORSO VERSO LA CAMERA
(−Y): la sogliola è un pesce di fianco con tutti e due gli occhi sul lato −Y; la razza ha il disco delle
pettorali nel piano XZ (z è la direzione dell'apertura delle ali). Così i dettagli delle famiglie, che
stanno sul fianco −Y, finiscono sul dorso; il ritratto poi li inclina come se fossero sul fondo.

Ogni campo nuovo è facoltativo: con i valori di default una forma è quella dei cinque prototipi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# le cinque famiglie del gioco, più 'normale' (il pesce vero, senza trasformazione: per le prove)
FAMIGLIE = ('skeletal', 'zombie', 'glitch', 'corrupt', 'bleeding', 'normale')


# ───────────────────────── pinne ─────────────────────────

@dataclass
class Fin:
    """Pinna: radice da a a b (in t lungo il corpo, sul dorso/ventre o sul fianco) e sagoma.
    kind: 'dorsal' | 'anal' | 'caudal' | 'pectoral' | 'pelvic'; outline: punti (lungo, fuori) normalizzati
    rispetto alla radice, dalla radice a alla radice b. spiny: raggi rigidi e membrana incisa.

    Dorsali e anali: 'lungo' va da a (0) a b (1), 'fuori' è l'altezza in unità di size (le punte pendono
    indietro di 0.35 dell'altezza). Caudale: (fuori, verticale) con il verticale da +1 (radice in alto) a −1
    (radice in basso); fuori è in unità di size, il verticale in unità di 0.42·size. Pari (pettorali,
    pelviche): (lungo l'asse della pinna, di lato) in unità di size, attaccate in t = a.

    Campi nuovi, tutti facoltativi:
    colore    colore della membrana (None: Look.fin)
    bordo     colore del bordo libero (None: il colore scurito, come sempre)
    macchie   puntini sulla membrana (0..1), del colore colore_macchie (gallinella, pesce civetta)
    carnosa   pinna di carne (squali, razze, la dorsale della murena): una lastra spessa fusa nel corpo, con
              la pelle del corpo e senza raggi; spessore = mezzo spessore alla radice
    z         pinne pari: quota dell'attacco sul fianco (−1 ventre … +1 dorso); None: −0.3 le pettorali,
              −0.86 le pelviche
    dir       pinne pari: direzione dell'asse lungo (x indietro, fuori, su); None: indietro e appena fuori.
              Per le ali del pesce volante, per esempio, (0.45, 1.0, 0.25)
    su        pinne pari: direzione del secondo asse della sagoma; None: verso l'alto
    liberi    pettorali: raggi liberi sotto la pinna, grossi e piegati come zampette (gallinella)
    """
    kind: str
    a: float
    b: float
    outline: list
    size: float = 0.1
    rays: int = 12
    spiny: bool = False
    tilt: float = 0.0
    colore: tuple | None = None
    bordo: tuple | None = None
    macchie: float = 0.0
    colore_macchie: tuple = (0.10, 0.25, 0.55)
    carnosa: bool = False
    spessore: float = 0.006
    z: float | None = None
    dir: tuple | None = None
    su: tuple | None = None
    liberi: int = 0


# ───────────────────────── elementi della forma ─────────────────────────

@dataclass
class Rostro:
    """Quello che sporge davanti al muso (x < 0).
    tipo: 'spada' (pesce spada: lama piatta dalla mascella di sopra; la bocca resta sotto),
          'becco' (aguglie: le due mascelle lunghe e sottili, il taglio della bocca arriva in punta: z va
                   messo sulla linea della bocca, mouth_z0; il taglio si assottiglia con le mascelle; con
                   denti > 0 i dentini sui bordi, pesci.denti_becco),
          'tubo' (pesce ago, cavalluccio, pesce flauto, trombetta: muso a tubo con la boccuccia in punta),
          'sega' (pesce sega: lama piatta con i denti sui due bordi; per una razza vista dall'alto la lama
                  è larga in z, quindi altezza > larghezza)
    larghezza / altezza: mezze misure della sezione alla radice (y / z); punta: quanto ne resta in punta
    (frazione); curva: quanto sale (+) o scende (−) la punta; denti: 'sega' e 'becco', per lato (e, nel
    becco, per mascella)."""
    tipo: str = 'spada'
    lunghezza: float = 0.3
    z: float = 0.0
    larghezza: float = 0.02
    altezza: float = 0.01
    punta: float = 0.15
    curva: float = 0.0
    denti: int = 0


@dataclass
class Disco:
    """Il disco delle pettorali delle razze (piano 'razza', costruito con il dorso verso −Y): contorno è la
    mezza apertura del disco (in z) lungo t, spessore il mezzo spessore (in y). Le sezioni sono ellissi:
    spesse vicino al corpo, sottili al bordo. Le pinne pelviche delle razze si disegnano nel contorno
    (un secondo lobo dopo il disco)."""
    contorno: list
    spessore: list
    raccordo: float = 0.012


@dataclass
class DiscoOrale:
    """Bocca a ventosa della lampreda: un disco rotondo in fondo al muso, rivolto avanti e in giù, con gli
    anelli di denti gialli che puntano verso il centro."""
    raggio: float = 0.032
    anelli: int = 4
    denti: int = 14
    inclinazione: float = 35.0


@dataclass
class Ventosa:
    """Il disco adesivo della remora sulla testa: un ovale piatto con le lamelle di traverso e il bordo."""
    t0: float = 0.02
    t1: float = 0.24
    larghezza: float = 0.035
    lamelle: int = 18


@dataclass
class Filamento:
    """Barbiglio, cirro o filamento: un tubicino che si assottiglia, attaccato alla pelle.
    t, v: dove nasce (v = quota normalizzata; v > 1 o < −1 va bene sulle razze); oppure xyz esplicito.
    dir: direzione iniziale (x, fuori, z): 'fuori' è verso la camera sul lato sinistro e si specchia sul
    destro; curva: come piega lungo il percorso (si somma alla direzione a ogni passo).
    lati: 'due' (coppia), 'sinistro' (solo quello verso la camera), 'centro' (y = 0: il barbiglio sotto il
    mento del granatiere o dell'ombrina). colore: None è la pelle del pesce."""
    t: float = 0.04
    v: float = -0.6
    lunghezza: float = 0.06
    raggio: float = 0.0025
    dir: tuple = (0.3, 0.25, -1.0)
    curva: tuple = (0.0, 0.0, 0.0)
    lati: str = 'due'
    punta: float = 0.25
    colore: tuple | None = None
    xyz: tuple | None = None
    segmenti: int = 8


@dataclass
class Spine:
    """Spine, chiodi e tubercoli sulla pelle (pesce palla, razza chiodata, scorfano, rombo chiodato):
    coni fusi nel corpo, con la stessa pelle. Si spargono a caso nella fascia t0..t1, v0..v1 (o in fila
    regolare con fila=True); inclinazione 0 = dritte sulla normale, 1 = coricate all'indietro."""
    t0: float
    t1: float
    v0: float = -1.0
    v1: float = 1.0
    n: int = 20
    lunghezza: float = 0.012
    raggio: float = 0.003
    lati: str = 'due'
    inclinazione: float = 0.3
    fila: bool = False
    seme: int = 0


@dataclass
class Fotofori:
    """Lucine (pesce lanterna, pesce vipera): righe = [(t0, t1, v, n)] file di fotofori sul fianco, più
    'sparsi' a caso nella fascia sparsi_v. Sono sferette luminose appena affondate nella pelle."""
    righe: list = field(default_factory=list)
    sparsi: int = 0
    sparsi_v: tuple = (-0.9, 0.2)
    raggio: float = 0.004
    colore: tuple = (0.45, 0.85, 1.0)
    forza: float = 8.0
    lati: str = 'due'
    seme: int = 0


# ───────────────────────── la forma ─────────────────────────

@dataclass
class Shape:
    """La forma del corpo: tre profili (t, valore) lungo l'asse — dorso (top), ventre (bot), mezza larghezza
    (w) — più occhi, bocca, opercolo e pinne. I campi dopo 'barbels' sono nuovi e facoltativi."""
    top: list
    bot: list
    w: list
    eye_t: float
    eye_z: float
    eye_r: float
    mouth_t: float = 0.06          # dove finisce la bocca (angolo)
    mouth_z0: float = 0.0          # quota della bocca alla punta del muso
    mouth_z1: float = 0.0          # quota all'angolo
    gill_t: float = 0.2            # bordo dell'opercolo
    fins: list = field(default_factory=list)
    barbels: bool = False          # i due baffi delle triglie (come il prototipo); per gli altri: filamenti
    # ── bocca e branchie ──
    bocca: str = 'terminale'       # 'terminale' (il taglio dal muso) | 'ventrale' (squali: mezzaluna sotto il muso) | 'nessuna'
    mouth_a: float = 0.03          # bocca ventrale: t del centro della mezzaluna (gli angoli sono in mouth_t, a quota mouth_z1)
    bocca_aperta: float = 0.0      # gradi: mascella abbassata (la famiglia sanguinante la apre comunque)
    branchie: str = 'opercolo'     # 'opercolo' (solco ad arco) | 'fessure' (squali) | 'pori' (lampreda: fori tondi) | 'nessuna'
    n_branchie: int = 5
    passo_branchie: float = 0.022  # distanza fra le fessure / i pori, a partire da gill_t
    # ── occhi ──
    occhi: list | None = None      # [(t, z, r, lato)] al posto della coppia simmetrica: pesci piatti e razze (lato −1)
    eye_allungato: float = 1.0     # occhio allungato lungo il corpo (gattuccio: 1.5)
    spiracoli: float = 0.0         # razze, squali: raggio del foro dietro ogni occhio (0: niente)
    # ── elementi in più ──
    rostro: Rostro | None = None
    disco: Disco | None = None
    disco_orale: DiscoOrale | None = None
    ventosa: Ventosa | None = None
    filamenti: list = field(default_factory=list)
    spine: list = field(default_factory=list)
    fotofori: Fotofori | None = None
    piega: list | None = None      # [(t, gradi)]: l'asse curvo nel piano del ritratto (anguille a S, cavalluccio)
    anelli: int = 0                # pesce ago, cavalluccio: anelli ossei in rilievo lungo il corpo (quanti)
    anelli_tratto: tuple = (0.05, 0.97)   # il tratto del corpo con gli anelli (t0, t1)


# ───────────────────────── l'aspetto ─────────────────────────

@dataclass
class Disegno:
    """Un disegno generico della pelle, sopra il colore di base. Coordinate: u lungo il corpo (0..1), v la
    quota normalizzata (razze: v è z diviso la mezza apertura del disco). Tipi:

    'strisce'    n righe lungo il corpo fra v0 e v1 (larghezza in v); onda: ondulazione; inclinazione:
                 quanto salgono andando verso la coda (strisce oblique della palamita)
    'bande'      n bande verticali fra u0 e u1 (larghezza: frazione del passo); inclinazione: quanto si
                 piegano in avanti verso il dorso; onda: bordi irregolari
    'barre'      barre scure ondulate sul dorso (come lo sgombro), n = quante
    'macchie'    macchie tonde sparse (scala: quante per unità di lunghezza; r: grandezza 0..1), nella
                 fascia u0..u1 / v0..v1
    'punti'      puntini fitti (come 'macchie' ma piccoli e tanti)
    'macchia'    una macchia sola in (u, v) di raggio r (in unità di u; allungamento: rapporto v/u)
    'ocello'     macchia con l'anello di colore2 attorno (pesce San Pietro, occhialone)
    'marmo'      marmorizzato: chiazze irregolari di rumore (torpedine, murena, cernia, lampreda)
    'reticolo'   rete di linee scure (celle di voronoi)
    'vermi'      ghirigori e linee vermiformi (sciarrano, ombrina)
    'linea'      linea laterale evidente (suro: con gli scudetti se n > 0; leccia: onda > 0)
    'ventre'     ventre argentato e metallico sotto v1 (forza = quanto metallo)
    'sfumatura'  il colore che sale dal ventre (v0..v1) o dalla coda (u0..u1) sfumando

    forza: opacità del disegno; colore2: secondo colore (anello dell'ocello, bordo delle macchie)."""
    tipo: str
    colore: tuple = (0.03, 0.03, 0.035)
    forza: float = 0.9
    u0: float = 0.0
    u1: float = 1.0
    v0: float = -1.0
    v1: float = 1.0
    n: float = 6.0
    larghezza: float = 0.08
    scala: float = 40.0
    u: float = 0.5
    v: float = 0.0
    r: float = 0.05
    allungamento: float = 1.0
    colore2: tuple | None = None
    onda: float = 0.0
    inclinazione: float = 0.0
    seme: float = 0.0


@dataclass
class Look:
    """Colori e pelle. pattern: uno dei disegni dei prototipi ('mackerel', 'bream', 'salema', 'redmullet',
    'barracuda'); per le specie nuove si usano i disegni generici in 'disegni'."""
    back: tuple
    flank: tuple
    belly: tuple
    fin: tuple
    iris: tuple = (0.75, 0.66, 0.40)
    iris_dark: tuple = (0.20, 0.17, 0.10)
    metal: float = 0.45
    pattern: str = ''
    pattern_col: tuple = (0.02, 0.03, 0.04)
    irid: float = 0.35
    # ── nuovi ──
    disegni: list = field(default_factory=list)
    squame: float = 1.0            # quanto si vedono le squame (0: pelle liscia: squali, razze, anguille)
    linea_laterale: float = 1.0    # quanto è scura la linea laterale di sempre (0: niente)
    linea_v: tuple = (0.42, -0.4)  # la linea laterale: v = a + b·u
    lucido: float = 0.6            # strato lucido (coat)
    ruvido: float | None = None    # rugosità fissa (None: come sempre, lucida sulle squame)
    alfa: float = 1.0              # < 1: trasparente (latterino, ceca)
    pupilla: str = 'round'         # 'round' | 'slit_h' | 'slit_v'
    bocca_col: tuple = (0.22, 0.05, 0.06)   # dentro la bocca aperta
    tinta_pinne: float = 1.0       # quanto le pinne carnose prendono il colore 'fin' (0: la pelle e i disegni del corpo)
    tinta_rostro: float = 0.85     # quanto il rostro (spada, becco) prende il colore del dorso


# ───────────────────────── ritratto e piani corporei ─────────────────────────

@dataclass
class Ritratto:
    """La posa del ritratto: yaw gira la testa verso la camera, pitch alza il muso (negativo: lo abbassa),
    roll gira il pesce sul suo asse (+ mostra il dorso alla camera, − il ventre; 180: a pancia all'aria).
    adatta: centra il pesce e lo scala perché stia nel riquadro come i prototipi: riquadro = (larghezza,
    altezza) massime in frazioni del fotogramma, centro = (x, y dall'alto). Con un riquadro più grande del
    fotogramma o il centro spostato il pesce esce dal bordo (Civetta Fuori Quadro)."""
    yaw: float = 12.0
    pitch: float = -4.0
    roll: float = 0.0
    adatta: bool = True
    riquadro: tuple = (0.80, 0.70)
    centro: tuple = (0.49, 0.46)


# i cinque prototipi approvati: la posa e l'inquadratura di prima, senza adattare
RITRATTO_PROTOTIPI = Ritratto(adatta=False)


@dataclass
class Piano:
    """Un piano corporeo: come si costruisce (vista 'fianco' o 'alto'; disco: le razze) e come si ritrae."""
    vista: str
    descrizione: str
    ritratto: Ritratto = field(default_factory=Ritratto)
    disco: bool = False


PIANI = {
    'fusiforme': Piano('fianco', 'il corpo affusolato o compresso visto di fianco (sgombro, orata, spigola, tonno)'),
    'alto': Piano('fianco', 'corpo alto e compresso, quasi un disco di fianco (pesce San Pietro, pesce re, castagna)'),
    'anguilliforme': Piano('fianco', 'lunghissimo, dorsale e anale continue unite alla coda (anguilla, murena, grongo, missina, lampreda)'),
    'nastriforme': Piano('fianco', 'nastro d\'argento lunghissimo e compresso, dorsale da cima a fondo (pesce sciabola)'),
    'squalo': Piano('fianco', 'pinne di carne, coda eterocerca, fessure branchiali, bocca sotto il muso'),
    'rostro': Piano('fianco', 'spada, becco o muso a tubo davanti al muso (pesce spada, aguglia, pesce flauto)'),
    'pettorali': Piano('fianco', 'pettorali enormi aperte come ali (pesce volante, pesce civetta, gallinella)',
                       Ritratto(yaw=10.0, pitch=-4.0, roll=28.0)),
    'palla': Piano('fianco', 'pesce palla gonfio, con le spine sulla pancia'),
    'cavalluccio': Piano('fianco', 'la testa ad angolo, il corpo dritto e la coda arrotolata (asse curvo)',
                         Ritratto(yaw=14.0, pitch=0.0)),
    'coda_di_topo': Piano('fianco', 'testa grossa e corpo che finisce in una coda sottile (chimera, granatiere)'),
    'piatto': Piano('alto', 'pesce piatto sdraiato su un fianco, gli occhi dalla stessa parte (sogliola, rombo)',
                    Ritratto(yaw=4.0, pitch=0.0, roll=-38.0)),
    'razza': Piano('alto', 'disco delle pettorali visto dall\'alto, coda a frusta o carnosa (razze, torpedine, pastinaca, squadro)',
                   Ritratto(yaw=4.0, pitch=0.0, roll=-38.0), disco=True),
}


# ───────────────────────── la voce del registro ─────────────────────────

@dataclass
class Specie:
    """Una specie del Catalogo (id come in src/game/catalog.ts).
    famiglia: 'skeletal' | 'zombie' | 'glitch' | 'corrupt' | 'bleeding' (o 'normale' per le prove);
    piano: una chiave di PIANI; opzioni: parametri della funzione della famiglia (vedi pesci.py: skeletal,
    zombie, corrupt, bleeding, glitch_post); extra(c): aggiunge oggetti propri della specie dopo la famiglia
    (c.obs, c.body, c.forma, c.aspetto, c.famiglia, c.P = il modulo pesci con tutti gli aiuti);
    campo(c, f) -> f: cambia il campo del corpo (escrescenze, buchi) prima di estrarre le superfici;
    ritratto: None = quello del piano; ritocco(img, c) -> img: ritocca l'immagine finita (RGBA float 0..1,
    dopo il glitch dei glitchati): i glitch propri della specie (neve, puntini, righe, doppio…)."""
    forma: Shape
    aspetto: Look
    famiglia: str
    piano: str = 'fusiforme'
    extra: Callable | None = None
    campo: Callable | None = None
    opzioni: dict = field(default_factory=dict)
    ritratto: Ritratto | None = None
    ritocco: Callable | None = None
    note: str = ''


# ───────────────────────── sagome pronte (aiuti) ─────────────────────────

def coda_forcuta(apertura=1.45, forca=0.32, lunghezza=1.0):
    """Coda forcuta: (fuori, verticale) con il verticale da +1 (radice in alto) a −1 (radice in basso);
    le punte dei lobi arrivano a ±apertura. (È la _forked dei prototipi.)"""
    return [(0.0, 1.0), (0.55 * lunghezza, 1.12), (1.0 * lunghezza, apertura), (forca * lunghezza, 0.0),
            (1.0 * lunghezza, -apertura), (0.55 * lunghezza, -1.12), (0.0, -1.0)]


def coda_falcata(apertura=2.6, lunghezza=0.85, radice=1.0):
    """Coda a mezzaluna (tonno, pesce spada, lampuga, palamita): lobi lunghi e stretti, bordo concavo.
    radice: dove parte il primo raggio (1 come i prototipi; per le pinne carnose meglio ~0.2, attaccata al
    peduncolo, perché il primo tratto dalla radice a (0, ±radice) è dritto in verticale)."""
    L, r = lunghezza, radice
    return [(0.0, r), (0.45 * L, 1.55), (1.0 * L, apertura), (0.55 * L, 1.25), (0.38 * L, 0.0),
            (0.55 * L, -1.25), (1.0 * L, -apertura), (0.45 * L, -1.55), (0.0, -r)]


def coda_tonda(alta=1.5, lunghezza=1.0):
    """Coda tonda (cernia, scorfano, ghiozzo, bavosa, sogliola)."""
    L = lunghezza
    return [(0.0, 1.0), (0.45 * L, alta), (0.85 * L, alta * 0.75), (1.0 * L, 0.0), (0.85 * L, -alta * 0.75),
            (0.45 * L, -alta), (0.0, -1.0)]


def coda_tronca(alta=1.55, incavo=0.08, lunghezza=0.85):
    """Coda tronca o appena incavata (spigola, ombrina, corvina)."""
    L = lunghezza
    return [(0.0, 1.0), (1.0 * L, alta), (1.0 * L - incavo, 0.0), (1.0 * L, -alta), (0.0, -1.0)]


def coda_appuntita(alta=1.0, lunghezza=1.0):
    """Coda a punta, unita alla dorsale e all'anale (anguille, granatiere, bavosa lunga)."""
    L = lunghezza
    return [(0.0, 1.0), (0.45 * L, alta), (1.0 * L, 0.0), (0.45 * L, -alta), (0.0, -1.0)]


def coda_eterocerca(lobo=1.0, alzata=1.8, lobo_basso=0.5, basso=1.9, radice=0.15):
    """Coda degli squali (pinna carnosa): il lobo di sopra lungo e alzato, con la tacca vicino alla punta,
    quello di sotto corto. lobo = lunghezza del lobo alto (in size); alzata: quanto sale (in 0.42·size);
    lobo_basso, basso: lunghezza e discesa del lobo di sotto. Lo squalo volpe ha una falce sua (vedi
    sanguinanti.py, volpe_sfregiata)."""
    L, B, r = lobo, lobo_basso, radice
    return [(0.0, r), (0.55 * L, r + alzata * 0.55), (1.0 * L, r + alzata), (0.93 * L, alzata * 0.82),
            (0.8 * L, alzata * 0.62), (0.45 * L, alzata * 0.3), (0.32 * L, -0.05),
            (0.5 * B + 0.1, -basso), (0.12, -r)]


# sagome di dorsali, anali e pinne pari (lungo, fuori)
DORSALE_TRIANGOLO = [(0, 0), (0.15, 0.9), (0.4, 1.0), (0.75, 0.55), (1, 0.08)]           # spinosa dello sgombro
DORSALE_MOLLE = [(0, 0), (0.25, 0.8), (0.6, 0.55), (1, 0.05)]                            # seconda dorsale
DORSALE_LUNGA = [(0, 0), (0.06, 0.9), (0.2, 1.0), (0.5, 0.82), (0.8, 0.75), (0.95, 0.55), (1, 0.05)]  # orata
DORSALE_BASSA = [(0, 0), (0.04, 0.7), (0.15, 0.95), (0.5, 1.0), (0.9, 1.0), (1, 0.6)]      # nastro continuo (anguille)
DORSALE_FALCE = [(0, 0), (0.08, 0.85), (0.2, 1.0), (0.3, 0.55), (0.55, 0.2), (1, 0.06)]  # falcata (tonno, pesce spada)
DORSALE_SQUALO = [(0, 0), (0.3, 0.7), (0.55, 1.0), (0.62, 0.62), (0.8, 0.22), (1.0, 0.04)]  # squalo: punta e coda libera
PETTORALE = [(0, 0), (0.45, 0.35), (1.0, 0.18), (0.8, -0.05), (0, -0.1)]
PETTORALE_TONDA = [(0, 0), (0.5, 0.42), (0.95, 0.25), (1.0, 0.0), (0.7, -0.2), (0, -0.12)]
PETTORALE_ALA = [(0, 0), (0.35, 0.26), (0.75, 0.24), (1.0, 0.08), (0.9, -0.06), (0.4, -0.1), (0, -0.06)]
PELVICA = [(0, 0), (0.6, 0.25), (1.0, 0.1), (0.5, -0.05), (0, -0.05)]


def pinna(kind, a, b, outline, size, rays=None, **k):
    """Abbreviazione per scrivere le pinne: i raggi, se non detti, vanno con la lunghezza della radice."""
    if rays is None:
        rays = max(5, int(round((b - a) * 60))) if kind in ('dorsal', 'anal') else 10
    return Fin(kind, a, b, outline, size, rays, **k)
