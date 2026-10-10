# Pesci del Catalogo: il piano per le 95 specie

Brief per gli agenti delle cinque famiglie. Il generatore è `tools/render/pesci.py` (Blender 5.2 come modulo
Python, Cycles); le specie sono **dati** in questo pacchetto, un file per famiglia:

| famiglia | file | prototipo approvato (non si tocca) |
|---|---|---|
| scheletrici (`skeletal`) | `scheletrici.py` | `sgombrato` |
| zombi (`zombie`) | `zombi.py` | `orrata` |
| glitchati (`glitch`) | `glitchati.py` | `salpa_sfasata` |
| corrotti (`corrupt`) | `corrotti.py` | `trigliocchi` |
| sanguinanti (`bleeding`) | `sanguinanti.py` | `barracruda` |

Le classi dei dati e gli aiuti per scriverli sono in `base.py`; `__init__.py` raccoglie le voci e le
controlla contro `src/game/catalog.ts` (che si legge e basta). Le immagini approvate dei prototipi sono in
`docs/concept/pesci/` (il foglio `prototipi.jpg` dà lo stile: Grim Fandango, ritratto di fianco, lampara calda
davanti, luna fredda dietro, sfondo trasparente).

## 0. Regole

- Ogni agente scrive **solo nel file della sua famiglia**. Non toccare `pesci.py`, `base.py`, gli altri file
  di famiglia, `src/`, `public/`, `docs/`. Se manca qualcosa di comune, fallo come `extra`/`campo`/`ritocco`
  nel tuo file; se ti sembra davvero di tutti, scrivilo nella relazione finale per chi coordina.
- **I cinque prototipi non si cambiano** (né la forma, né l'aspetto, né le opzioni).
- La macchina ha 4 core: **un render alla volta**. Le prove sono sempre `--anteprima --fast`; i render finali
  (senza `--anteprima`, scrivono in `public/assets/img/fish/` e in `fish.json`) li lancia chi coordina.
- Nel codice tutto in italiano (commenti, docstring, nomi), con la densità di commenti che trovi.
- Le specie già registrate con `famiglia='normale'` sono **le prove dei piani corporei** (21, elencate nel §4):
  forma e aspetto della specie vera, già controllati. Sono il punto di partenza: trasformale nella tua
  famiglia (metti la famiglia giusta, aggiungi opzioni ed extra). Una voce `normale` non si può rendere senza
  `--anteprima`, e `--elenco` le conta a parte finché restano `normale`.

## 1. Comandi

```
tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast     # prova veloce (10–30 s)
tools/.venv/bin/python tools/render/pesci.py <id> <id> ... --anteprima --fast
tools/.venv/bin/python tools/render/pesci.py --famiglia=zombie --anteprima --fast   # tutte quelle di una famiglia
tools/.venv/bin/python tools/render/pesci.py --elenco                    # registrate, mancanti, errori di famiglia
tools/.venv/bin/python tools/render/pesci.py --foglio tools/render/cache/pesci/zombi.jpg orrata sogliombra:piatto ...
```

Se più agenti lavorano nello stesso momento, ogni render passa dal lucchetto, così ne parte uno alla volta:
`flock tools/render/cache/pesci/.lock tools/.venv/bin/python tools/render/pesci.py <id> --anteprima --fast`.

Le anteprime finiscono in `tools/render/cache/pesci/anteprime/`: `<id>.jpg` (sul fondo scuro delle pagine
del Catalogo: **è quella da guardare**, con lo strumento Read) e `<id>.png` (RGBA, come il finale). Con
`--foglio` si fa una tavola delle anteprime già fatte; `id:etichetta` cambia il titolo sotto l'immagine.
I fogli già fatti, da guardare prima di cominciare (in `tools/render/cache/pesci/`):

| foglio | cosa fa vedere |
|---|---|
| `piani_corporei.jpg` | le 21 prove dei piani corporei, con il piano sotto ciascuna |
| `famiglie_sui_piani.jpg` | le famiglie applicate ai piani nuovi con le opzioni di default o quasi (scheletro di murena, aguglia, pastinaca e pesce sega; zombi sulla razza; corrotti sulla sogliola; sanguinanti su verdesca e aguglia) |
| `disegni_della_pelle.jpg` | i disegni generici della pelle (§3.3) provati su un tonno |
| `ganci_per_specie.jpg` | trasparenza, occhio allungato con la pupilla a fessura, pancia all'aria, `campo`, `ritocco`, pesce che esce dal bordo |
| `effetti_glitch.jpg` | gli effetti in più dei glitchati (§5) sulla salpa |
| `confronto_prototipi/prima_dopo.jpg` | i cinque prototipi prima e dopo il generatore nuovo: identici |

Il modo di lavorare: scrivi la voce → anteprima → guarda il jpg → correggi → avanti. La specie vera deve
riconoscersi al primo sguardo, e i dettagli della descrizione si devono vedere. Alla fine fai il foglio
della famiglia e confrontalo con `docs/concept/pesci/prototipi.jpg`.

## 2. Coordinate

Il corpo è lungo 1: il muso in x = 0 guarda verso −X, l'attacco della coda è in x = 1 (la caudale va oltre),
il dorso verso +Z, il fianco sinistro verso −Y, cioè verso la camera. `t` è la posizione lungo il corpo
(0 muso … 1 coda); `v` è la quota normalizzata sulla sezione (−1 ventre, 0 asse, +1 dorso). Tutte le misure
sono frazioni della lunghezza del corpo (un'altezza di 0.1 è un decimo della lunghezza).

Il ritratto poi gira il pesce (`Ritratto`: yaw 12°, pitch −4°) e, per le specie nuove, lo **inquadra da
solo** come i prototipi (largo al massimo l'80% del fotogramma, alto al massimo il 70%): un pesce alto o con
una coda lunga viene rimpicciolito, non tagliato. Non serve preoccuparsi della scala.

**Pesci visti dall'alto** (piani `piatto` e `razza`): si costruiscono con il **dorso verso la camera (−Y)**.
La sogliola è un pesce di fianco molto compresso con tutti e due gli occhi sul lato −Y; la razza ha il disco
delle pettorali nel piano XZ (z è l'apertura delle ali, y lo spessore). Così tutto quello che le famiglie
mettono "sul fianco sinistro" (ferite, cuciture, occhi in più) finisce sul dorso, che è quello che si vede.
Il ritratto dei due piani corica il pesce come se fosse sul fondo (roll −38°).

## 3. Il formato di una voce: un esempio completo

La murena (prova del piano `anguilliforme`, in `zombi.py`), con un extra:

```python
from .base import Disegno, Fin, Look, Shape, Specie, coda_appuntita


def _denti_murena(c):
    """I denti a zanna nella bocca aperta (aiuto comune: denti_mascelle, con la stessa apertura della forma)."""
    c.obs += c.P.denti_mascelle(c.body, n=7, lunghezza=0.0055, zanne=(1, 2), apertura=c.forma.bocca_aperta,
                                nome='DenteMurena')


# ── Murena Murata (murena, Muraena helena) ──
SPECIE['murena_murata'] = Specie(
    forma=Shape(
        # i tre profili lungo l'asse: (t, quota del dorso), (t, quota del ventre), (t, mezza larghezza)
        top=[(0, -0.004), (0.015, 0.012), (0.04, 0.026), (0.07, 0.036), (0.1, 0.045), (0.14, 0.052), (0.25, 0.055),
             (0.5, 0.052), (0.7, 0.044), (0.85, 0.032), (0.95, 0.016), (1, 0.004)],
        bot=[(0, -0.012), (0.02, -0.02), (0.05, -0.028), (0.1, -0.036), (0.2, -0.045), (0.4, -0.05), (0.6, -0.046),
             (0.8, -0.032), (0.93, -0.016), (1, -0.004)],
        w=[(0, 0.004), (0.04, 0.018), (0.1, 0.028), (0.25, 0.03), (0.5, 0.025), (0.75, 0.016), (0.9, 0.009), (1, 0.003)],
        eye_t=0.045, eye_z=0.011, eye_r=0.0085,                       # occhio: t, quota, raggio
        mouth_t=0.075, mouth_z0=-0.006, mouth_z1=-0.012,              # bocca: angolo in t, quota al muso e all'angolo
        bocca_aperta=16.0,                                            # gradi
        branchie='pori', n_branchie=1, gill_t=0.13,                   # il forellino branchiale della murena
        fins=[Fin('dorsal', 0.12, 1.0, [(0, 0), (0.03, 0.55), (0.12, 0.9), (0.5, 1.0), (0.9, 1.0), (1, 0.7)], 0.03, 150,
                  carnosa=True, spessore=0.004),                      # pinna di pelle spessa, fusa nel corpo
              Fin('anal', 0.45, 1.0, [(0, 0), (0.05, 0.6), (0.2, 0.9), (0.9, 1.0), (1, 0.7)], 0.024, 100, carnosa=True,
                  spessore=0.004),
              Fin('caudal', 1.0, 1.0, coda_appuntita(0.9, 1.0), 0.035, 20, carnosa=True, spessore=0.003)],
        piega=[(0, -10), (0.25, 12), (0.5, -10), (0.75, 12), (1.0, -4)]),   # l'asse a S, gradi lungo t
    aspetto=Look(back=(0.06, 0.045, 0.03), flank=(0.085, 0.065, 0.04), belly=(0.11, 0.09, 0.06), fin=(0.07, 0.05, 0.035),
                 iris=(0.78, 0.74, 0.6), iris_dark=(0.2, 0.18, 0.1), metal=0.0, irid=0.05, squame=0.0,
                 linea_laterale=0.0, lucido=0.6, ruvido=0.3, tinta_pinne=0.0,
                 disegni=[Disegno('macchie', colore=(0.78, 0.62, 0.28), forza=0.9, scala=34, r=0.24,
                                  colore2=(0.02, 0.015, 0.01)),
                          Disegno('punti', colore=(0.7, 0.58, 0.3), forza=0.7, scala=120, r=0.16, seme=3)]),
    extra=_denti_murena,
    famiglia='zombie',                       # (la prova è registrata come 'normale')
    piano='anguilliforme',
    opzioni=dict(cucitura=(0.3, 0.6, -0.4), marcio=0.4))   # parametri della funzione zombie()
```

Per una specie si parte quasi sempre **copiando la prova del suo piano** (o un prototipo) e cambiando i
numeri. I colori sono lineari (0..1, come in Blender): un dorso "scuro" sta sotto 0.1.

### 3.1 Shape (la forma)

| campo | cosa fa |
|---|---|
| `top`, `bot`, `w` | profili (t, valore): quota del dorso, del ventre, mezza larghezza. Curva liscia fra i punti: mettine 8–12, più fitti dove la sagoma cambia in fretta (muso, coda). Il corpo finisce in x = 1 (il peduncolo, che regge la caudale) |
| `eye_t`, `eye_z`, `eye_r` | la coppia di occhi simmetrica (guardano di lato) |
| `occhi` | `[(t, z, r, lato)]` al posto della coppia: pesci piatti e razze (`lato −1` tutti e due), pesce prete (in cima), `[]` = niente occhi (missina) |
| `eye_allungato` | occhio allungato lungo il corpo (gattuccio 1.5–1.7) |
| `mouth_t`, `mouth_z0`, `mouth_z1` | la bocca: taglio dal muso (quota z0) all'angolo (t = mouth_t, quota z1). Bocca all'insù: z0 > z1 |
| `bocca` | `'terminale'` (il taglio), `'ventrale'` (squali: mezzaluna sotto il muso da `mouth_a` agli angoli in `mouth_t`), `'nessuna'` |
| `bocca_aperta` | gradi della mascella abbassata (i sanguinanti la aprono comunque, opzione `bocca`) |
| `branchie` | `'opercolo'` (il solco ad arco in `gill_t`), `'fessure'` (squali: `n_branchie`, `passo_branchie`), `'pori'` (lampreda: fori tondi in fila), `'nessuna'` |
| `fins` | le pinne (`Fin`, sotto) |
| `barbels` | i due baffi delle triglie come il prototipo (`True`); per tutto il resto `filamenti` |
| `spiracoli` | raggio del foro dietro ogni occhio (razze, squali) |
| `rostro` | `Rostro(tipo, lunghezza, z, larghezza, altezza, punta, curva, denti)`: `'spada'` (piatta, sopra la bocca), `'becco'` (le due mascelle: z = mouth_z0, il taglio della bocca arriva in punta e si assottiglia con loro; `denti` = i dentini per mascella e per lato, vedi `ossaguglia`), `'tubo'` (muso a tubo con la boccuccia in punta), `'sega'` (con i denti sui bordi larghi). Con la bocca aperta (sanguinanti, `bocca_aperta`) la metà di sotto del becco si apre con i suoi dentini |
| `disco` | razze: `Disco(contorno=[(t, mezza apertura)], spessore=[(t, mezzo spessore)])`; le pelviche delle razze sono un secondo lobo nel contorno |
| `disco_orale` | lampreda: `DiscoOrale(raggio, anelli, denti, inclinazione)` (la ventosa con gli anelli di denti) |
| `ventosa` | remora: `Ventosa(t0, t1, larghezza, lamelle)` sul capo piatto |
| `filamenti` | `[Filamento(t, v, lunghezza, raggio, dir, curva, lati, punta, colore, xyz)]`: barbigli, cirri, filamenti delle pinne, il filo in coda della chimera. `dir` = (x, fuori, z): 'fuori' è verso la camera sul lato sinistro e si specchia; `lati` `'due'`/`'sinistro'`/`'centro'` (sotto il mento) |
| `spine` | `[Spine(t0, t1, v0, v1, n, lunghezza, raggio, lati, inclinazione, fila, seme)]`: spine, chiodi e tubercoli fusi nella pelle (pesce palla, razza chiodata, scorfano, rombo). `fila=True` le mette in fila regolare |
| `fotofori` | `Fotofori(righe=[(t0, t1, v, n)], sparsi, raggio, colore, forza)`: lucine (pesce lanterna, pesce vipera) |
| `piega` | `[(t, gradi)]`: curva l'asse nel piano del ritratto. Anguille a S (±10–20°), cavalluccio (testa 0°, collo −90°, coda arrotolata fino a −400°). Tutto (pinne, occhi, extra) si piega insieme |
| `anelli`, `anelli_tratto` | anelli ossei in rilievo: quanti, e su che tratto del corpo (t0, t1) (pesce ago, cavalluccio) |

### 3.2 Fin (le pinne)

`Fin(kind, a, b, outline, size, rays, spiny=False, ...)`

- `kind`: `'dorsal'`, `'anal'` (sul dorso / ventre, da t = a a t = b), `'caudal'` (in coda, a e b = 1),
  `'pectoral'`, `'pelvic'` (pari, sui due lati, attaccate in t = a).
- `outline`: la sagoma. Dorsali e anali: punti (lungo 0..1 sulla radice, altezza in unità di `size`); le
  punte pendono indietro di 0.35 dell'altezza. Caudale: (fuori in unità di `size`, verticale in unità di
  0.42·size, da +radice a −radice). Pari: (lungo l'asse della pinna, di lato) in unità di `size`.
- `rays`: quanti raggi (per le carnose è solo la risoluzione della sagoma: 30–60).
- `spiny`: raggi rigidi, membrana più incisa. `colore`, `bordo`, `macchie`, `colore_macchie`: la membrana.
- `carnosa=True` (+ `spessore`): pinna di carne fusa nel corpo, con la pelle del corpo e niente raggi
  (squali, razze, la murena, l'adiposa, le pinne rigide del pesce spada). Il colore lo dà `Look.fin`
  (`tinta_pinne` = quanto; 0 lascia i disegni del corpo).
- Pinne pari: `z` (quota dell'attacco, −1 ventre … +1 dorso), `dir` (asse lungo: (indietro, fuori, su)),
  `su` (secondo asse). Ali del pesce volante: `z=0.35, dir=(0.5, 0.85, 0.12), su=(1, 0, 0)`.
  `liberi=3`: i raggi liberi a zampetta della gallinella.

Sagome pronte in `base.py`: `coda_forcuta`, `coda_falcata` (mezzaluna), `coda_tonda`, `coda_tronca`,
`coda_appuntita` (unita a dorsale e anale), `coda_eterocerca` (squali; lo squalo volpe ha la sua falce);
`DORSALE_TRIANGOLO`, `DORSALE_MOLLE`, `DORSALE_LUNGA`, `DORSALE_BASSA`, `DORSALE_FALCE`, `DORSALE_SQUALO`,
`PETTORALE`, `PETTORALE_TONDA`, `PETTORALE_ALA`, `PELVICA`. Per le code di carne usa `radice≈0.15–0.3`
(il primo tratto della sagoma, dalla radice a (0, ±radice), è dritto in verticale).

### 3.3 Look (l'aspetto)

| campo | cosa fa |
|---|---|
| `back`, `flank`, `belly`, `fin` | colori di dorso, fianchi, ventre, pinne |
| `iris`, `iris_dark`, `pupilla` | occhio (`'round'`, `'slit_h'`, `'slit_v'`) |
| `metal`, `irid` | argento (0..1) e iridescenza |
| `squame` | quanto si vedono le squame (0: pelle liscia di squali, razze, anguille, pesce palla) |
| `linea_laterale`, `linea_v` | la linea laterale scura (0: niente) e la sua quota `v = a + b·u` |
| `lucido`, `ruvido` | strato bagnato (coat); rugosità fissa (squali ~0.5) |
| `alfa` | < 1: trasparente (latterino, ceca) |
| `tinta_pinne`, `tinta_rostro` | quanto pinne carnose e rostro prendono `fin` e `back` |
| `pattern` | solo i disegni dei prototipi: per le specie nuove si usa `disegni` |
| `disegni` | lista di `Disegno` (sotto), uno sopra l'altro |

`Disegno(tipo, colore, forza, u0, u1, v0, v1, n, larghezza, scala, u, v, r, allungamento, colore2, onda,
inclinazione, seme)`; u va lungo il corpo (0..1), v è la quota (sulle razze v è z diviso la mezza apertura del
disco). La fascia u0..u1 / v0..v1 limita il disegno (i lati aperti 0, 1, ±1 non sfumano).

| tipo | cosa | campi che contano |
|---|---|---|
| `strisce` | n righe lungo il corpo | v0, v1, n, larghezza (in v), onda, inclinazione (righe oblique: palamita, ricciola) |
| `bande` | n bande verticali | u0, u1, n, larghezza (frazione del passo), inclinazione, onda (bordi irregolari) |
| `barre` | barre ondulate sul dorso come lo sgombro | n, v0 |
| `macchie` | macchie tonde sparse | scala (fittezza), r (grandezza 0..0.5), colore2 (alone), seme |
| `punti` | puntini fitti | scala (≥ 160), r |
| `macchia` | una macchia in (u, v) | u, v, r (in lunghezze del corpo), allungamento |
| `ocello` | macchia con l'anello di colore2 | u, v, r, colore2 |
| `marmo` | marmorizzato | scala, r (copertura 0..1), onda |
| `reticolo` | rete di linee | scala, larghezza |
| `vermi` | ghirigori, linee vermiformi | scala, u0..u1 (es. solo la testa) |
| `linea` | linea evidente (laterale o altra) | v, inclinazione, larghezza, onda, n (scudetti del suro) |
| `ventre` | ventre argentato metallico | v1, colore, forza (= metallo) |
| `sfumatura` | tinta di una zona | u0, u1, v0, v1, larghezza (morbidezza) |

Le scale sono in unità della lunghezza del pesce: `marmo` con `scala` sotto 30 fa chiazze grandi quanto il
pesce, che quindi non si vedono (sulla pastinaca: 60 e 150); `macchie` 30–50, `punti` ≥ 160. I pesci visti
dall'alto (piatti e razze) prendono la luce in pieno sul dorso: lì i colori vanno tenuti più scuri del
solito (dorso ≤ 0.1) e il disegno più contrastato, se no il disco viene chiaro e piatto.

### 3.4 Specie, Ritratto, i ganci per specie

`Specie(forma, aspetto, famiglia, piano, extra=None, campo=None, opzioni={}, ritratto=None, ritocco=None, note='')`

- `famiglia`: `'skeletal' | 'zombie' | 'glitch' | 'corrupt' | 'bleeding'` (`'normale'` solo per le prove).
- `piano`: una chiave di `PIANI` (vedi §4); dà il ritratto di default.
- `opzioni`: i parametri della funzione della famiglia (§5). `opzioni['elementi'] = False` toglie gli elementi
  in più della forma (filamenti, fotofori…), per esempio da uno scheletro.
- `ritratto`: `Ritratto(yaw, pitch, roll, adatta, riquadro, centro)`; `roll` + mostra il dorso, − il
  ventre, 180 a pancia all'aria; `riquadro`/`centro` spostano l'inquadratura (oltre 1 il pesce esce dal bordo).
- `extra(c)`: aggiunge oggetti propri della specie, **costruiti nelle coordinate del pesce dritto** (poi
  vengono piegati, girati e inquadrati con tutto il resto). Si appendono a `c.obs`.
- `campo(c, f)`: restituisce un nuovo campo del corpo (escrescenze, buchi, tagli) prima che si estraggano
  le superfici: vale per tutte le famiglie (anche il cranio degli scheletri).
- `ritocco(img, c)`: ritocca l'immagine finita (array RGBA 0..1, dopo il glitch): i glitch propri della specie.

Cosa c'è in `c`: `c.fid`, `c.specie`, `c.body` (il corpo: `section(t)` → (zc, h, w), `surface_y(t, z)`,
`superficie(t, v, lato)` → (punto, normale), `occhi_lista()`, `mouth_line(x)`, `bounds()`), `c.forma`,
`c.aspetto`, `c.famiglia`, `c.obs`, `c.fast`, e `c.P`, il modulo `pesci` con tutti gli aiuti:

- `c.P.sdf`: primitive e operazioni (`sphere`, `ellipsoid`, `capsule`, `round_cone`, `torus`, `box`, `smin`,
  `smax`, `union`, `subtract`, `rot_matrix`, `Noise3`); i campi prendono punti (N, 3) e danno (N,).
- `c.P.oggetto_sdf(nome, campo, lo, hi, materiale, res)`: un oggetto da un campo (res 0.0005–0.0015).
- `c.P.campo_coni(A, B, R1, R2)`, `c.P.campo_sfere(C, r)`: tanti coni/sferette in un campo solo (chiodi,
  denti, bolle, verruche) → `(campo, lo, hi)`.
- `c.P.denti_mascelle(body, n, lunghezza, zanne, apertura, mat, nome, seme)`: denti lungo le due mascelle.
- `c.P.filamento(body, aspetto, Filamento(...), k, mat)`: un filamento in più (per esempio con un altro materiale).
- `c.P.denti_becco(body, n, lunghezza, raggio, mat, nome)`: i dentini lungo il becco (li mette già la forma se
  `Rostro.denti` > 0; l'aiuto serve per farne altri, più grossi o di un altro materiale).
- `c.P.raggi_cartilagine(body, mat, n, seme)`: il ventaglio di raggi di cartilagine nelle ali delle razze (lo
  mette già la famiglia skeletal, opzione `raggi_disco`).
- `c.P.sezione_rostro(r, x)` → (mezza larghezza, mezza altezza, quota del centro) del rostro alla x (x < 0):
  per attaccare cose alla spada, al becco o alla sega (il braccialetto della Spadossa, la cosa infilata
  sull'aguglia imperiale).
- Materiali: `c.P.materiale(nome, colore, rough, coat, metal, sss, emissione, forza)`, `fish_skin`,
  `bone_material`, `blood_material`, `tar_material`, `dirty_teeth_material`, `thread_material`,
  `flesh_material`, `human_eye(nome, iris)`, `slime_material`; `c.P.eyeball(nome, centro, raggio, mat,
  look, col=c.P.COL)`, `c.P.tooth(nome, base, punta, raggio, mat, col=c.P.COL)`, `c.P.drip(punto, lunghezza, r0, r1, dir)` (goccia
  che pende), `c.P.strand(a, b, cedimento, r)` (filo di bava fra due punti): sono campi, da passare a `oggetto_sdf`.
- Materiali fatti a mano: `m, g = c.P.material('Nome')` dà il materiale e il costruttore dei nodi di
  `tools/render/nodes.py` (`g.texcoord('Object')`, `g.attr('u')`, `g.noise`, `g.voronoi`, `g.wave`, `g.mix`,
  `g.smoothstep`, `g.image(percorso, vec)`, `g.principled(color=…, rough=…, emission=…, alpha=…)`,
  `g.output_material(…)`); poi `oggetto.data.materials.append(m)`. Le immagini che servono (scritte, la barca
  dentro lo specchio, una foto) si fanno al volo con PIL in `tools/render/cache/pesci/tex/` e si leggono con
  `g.image`, proiettate con le coordinate `Object`.
- `c.P.sdf.smin(a, b, k)` / `smax` lavorano sui **valori** (array), `sdf.union(*campi, k)` / `subtract` /
  `intersect` sui **campi** (funzioni).

Esempi già scritti: `_denti_murena` (zombi.py), `_becco_pesce_palla` (corrotti.py), `_denti_sciabola`
(scheletrici.py). Esempi di `campo` e `ritocco`: il foglio `ganci_per_specie.jpg` è fatto con (serve
`import numpy as np` in cima al file di famiglia)

```python
def buco(c, f):
    """campo: un buco tondo che passa il corpo da parte a parte (a metà, all'altezza dell'asse)."""
    centro = np.array((0.5, 0.0, 0.0), np.float32)

    def g(p):
        q = p - centro
        return np.maximum(f(p), -(np.sqrt(q[:, 0] ** 2 + q[:, 2] ** 2) - 0.035))
    return g


def verde(img, c):
    """ritocco: tutto più verde dentro la sagoma (img è RGBA 0..1, il canale 3 è la sagoma)."""
    out = img.copy()
    out[..., 1] = np.clip(out[..., 1] * 1.6, 0, 1)
    return out
```

## 4. I piani corporei

Il foglio con le prove è `tools/render/cache/pesci/piani_corporei.jpg`. Il piano decide come si costruisce
il pesce e la posa del ritratto; tutto il resto è nei dati della forma.

| piano | come | prova da copiare | ritratto |
|---|---|---|---|
| `fusiforme` | il corpo standard di fianco | `tonno_di_sangue` (pinnule, coda a mezzaluna); i prototipi; `remora_strappata` (ventosa); `lanternossa` (fotofori) | yaw 12, pitch −4 |
| `alto` | corpo alto e compresso, quasi un disco di fianco | `san_pietrificato` | come sopra (si rimpicciolisce da solo) |
| `anguilliforme` | lunghissimo (alto 1/12–1/30), dorsale e anale continue unite alla coda, `piega` a S | `murena_murata` (pinne carnose, bocca aperta); `lampreda_vampira` (disco orale, pori); `missina_della_melma` (barbigli, niente occhi) | yaw 12 |
| `nastriforme` | nastro compresso, dorsale bassa da cima a fondo, coda minuscola | `sciabola_spolpata` | yaw 12 |
| `squalo` | pinne carnose, coda eterocerca, fessure, bocca ventrale, pelle liscia e opaca | `verdesca_ferita` (lo squalo di sempre: `coda_eterocerca`, pettorali a falce); `volpe_sfregiata` (la coda a falce lunga quanto il corpo) | yaw 12 |
| `rostro` | spada, becco o muso a tubo davanti al muso | `spadossa` (spada, pinne rigide carnose); `ossaguglia` (becco con i dentini) | yaw 12 |
| `pettorali` | pettorali enormi aperte (pesce volante, civetta, gallinella) | `pesce_volante_in_pausa` (ali), `gallincubo` (ventaglio e zampette) | roll +28: si vede il dorso |
| `palla` | pesce palla gonfio | `pesce_bubbone` (spine, becco) | yaw 12 |
| `cavalluccio` | asse curvo: testa ad angolo, coda arrotolata | `cavalluccio_dosso` | yaw 14, pitch 0 |
| `coda_di_topo` | testa grossa, coda che si assottiglia in un filo (chimera, granatiere) | `chimera_bianca` | yaw 12 |
| `piatto` | pesce di fianco compresso, occhi tutti e due sul lato −Y, frangia di pinne | `sogliombra` | roll −38: coricato sul fondo |
| `razza` | disco delle pettorali visto dall'alto, tronco con la coda | `razza_inchiodata` (disco a rombo, spine, coda con due dorsali); `pastinaca_putrida` (coda a frusta con il pungiglione); `sega_dossa` (corpo da squalo, sega) | roll −38 |

Le 21 prove, piano per piano (sono le voci `normale` dei file di famiglia): `tonno_di_sangue` (fusiforme),
`san_pietrificato` (alto), `murena_murata`, `lampreda_vampira`, `missina_della_melma` (anguilliforme),
`sciabola_spolpata` (nastriforme), `chimera_bianca` (coda di topo), `sogliombra` (piatto), `razza_inchiodata`,
`pastinaca_putrida`, `sega_dossa` (razza), `verdesca_ferita`, `volpe_sfregiata` (squalo), `spadossa`,
`ossaguglia` (rostro), `cavalluccio_dosso` (cavalluccio), `pesce_volante_in_pausa`, `gallincubo` (pettorali),
`pesce_bubbone` (palla), `remora_strappata`, `lanternossa` (fusiforme con ventosa e fotofori).

Consigli per piano:

- **fusiforme / alto**: la sagoma si fa con i profili; la gobba della fronte (lampuga, pettine), la testa
  grossa (cernia, scorfano) e il muso appuntito sono tutti in `top`/`bot`. Pinnule = tante dorsali piccole.
- **anguilliforme / nastriforme**: dorsale e anale fino a b = 1.0, caudale piccola (`coda_appuntita` o
  `coda_tonda`); la `piega` dà vita e riempie meglio il riquadro. Le anguille con le pettorali (anguilla,
  grongo) hanno una `pectoral` piccola e tonda.
- **squalo**: tutte le pinne `carnosa=True`; la pettorale con `dir=(0.75, 0.3, -0.6)` scende dietro le
  fessure; `bocca='ventrale'` (mezzaluna sotto il muso), `branchie='fessure'` (`n_branchie` 5 o 6),
  `squame=0`, `ruvido≈0.45`, `linea_laterale=0`, colori scuri sul dorso (≤ 0.08) perché la pelle opaca
  sotto la lampara schiarisce. La coda: `coda_eterocerca(lobo, alzata, lobo_basso, basso)` con `size`
  0.22–0.3 (verdesca: 1.0, 1.9, 0.45, 1.45); gattuccio e palombo hanno la coda bassa e lunga, quasi
  orizzontale (alzata ~0.8–1.0, lobo_basso piccolo). Partire da `verdesca_ferita`.
- **piatto**: compresso (w ≤ 0.02), `occhi=[(t, z, r, -1), (t, z, r, -1)]` vicini al bordo dorsale della
  testa, dorsale dal muso alla coda e anale lunga (90 raggi), `dv`: il lato degli occhi prende il colore
  `back`, il lato cieco `belly`. Il rombo è quasi tondo (alto ~0.8 della lunghezza).
- **razza**: `top`/`bot`/`w` sono il tronco (la gobba centrale e la coda: top = −bot = mezza larghezza in z,
  w = mezzo spessore), `disco` le ali; `occhi` sul lato −1 a z = ±, `spiracoli`, `bocca='nessuna'`,
  `branchie='nessuna'`; le pinne dorsali e la caudale della coda si scrivono come per un pesce di fianco
  (il generatore le gira verso la camera). Pastinaca (`pastinaca_putrida`): coda a frusta lunga una volta e
  mezza il disco (il tronco che si assottiglia fino a 0.001), pungiglione = una `Spine` sola coricata
  all'indietro, appena di lato (v = 0.55) perché dall'alto si veda.
  Aquila di mare: ali appuntite larghe, la testa che sporge (tronco largo davanti). Torpedine: disco tondo,
  coda grossa con la caudale. Pesce violino e squadro: disco a cuneo / ali staccate dalla testa con una
  tacca, coda da squalo con due dorsali (vedi `sega_dossa`).
- **rostro**: la spada è piatta (larghezza ≫ altezza); il becco dell'aguglia è `'becco'` a z = mouth_z0;
  l'aguglia imperiale ha un rostro corto e tondo (`'spada'` con larghezza ≈ altezza); muso a tubo (`'tubo'`)
  per pesce ago, pesce flauto, trombetta, cavalluccio, con `bocca='nessuna'`.
- **pettorali**: pinne pari grandi con `dir` e `su`; il ritratto le fa vedere girando il dorso verso la camera.

## 5. Le famiglie e le loro opzioni

Le funzioni sono in `pesci.py`; le opzioni si passano con `Specie.opzioni` (default = i prototipi).

- **skeletal** `skeletal(seed=3, vertebre=34, costole_fino=0.55, emali_da=0.5, cranio_t=None, striscia=None,
  striscia_v=0.6, striscia_fino=0.9, peduncolo=0.9, occhi=True, osso=None, raggi_disco=None)`: il cranio è il corpo tagliato
  dietro l'opercolo (`cranio_t`), eroso, con le orbite e gli archi branchiali; vertebre con le spine e le
  costole fino a `costole_fino`; la striscia di pelle del dorso (sopra `striscia_v`) con il disegno; il
  peduncolo carnoso che regge la coda (`None` per toglierlo); pinne d'osso con brandelli di membrana.
  `occhi=False`: orbite vuote. `osso=(r, g, b)` tinge le ossa (le ossa verdi dell'aguglia). Le pinne carnose,
  il rostro e il disco delle razze sono nel campo del corpo: finiscono nel cranio se stanno davanti a
  `cranio_t`, nella striscia o nel peduncolo se ci cadono dentro. **Sulle razze** (piano `razza`) lo scheletro
  è un altro: il cranio è solo il tronco (con il rostro: la sega resta), le vertebre non hanno spine né
  costole, niente striscia di pelle (di default), e le ali diventano un ventaglio di raggi di cartilagine a
  segmenti, attaccati a una cartilagine lungo il fianco del tronco, con le due cinture di traverso
  (`raggi_disco` = quanti per ala, default 30; 0 = niente, per fare altre ossa con un extra: l'Aquila d'Osso).
  `cranio_t` ~0.15 sulle razze (il default, dietro `gill_t`, è lungo). Vedi `famiglie_sui_piani.jpg`.
- **zombie** `zombie(seed=5, cucitura=(0.26, 0.64, -0.52), punti=13, occhi='lattiginosi', marcio=0.45)`:
  chiazze di marcio e muffa, carne esposta dove è profondo, squame cadute, la cucitura (t0, t1, v) sul
  fianco sinistro con i punti, occhi lattiginosi, pinne strappate. `marcio` più basso = più marcio.
- **corrupt** `corrupt(seed=7, occhi_extra=[(t, v, raggio)], iridi=[(r, g, b)], escrescenza=(t, v, raggio),
  colature=2)`: occhi umani in più con la palpebra carnosa che guardano la camera, pece nera attorno e che
  cola dai primi `colature` occhi, un'escrescenza (`None`: niente), i baffi se `barbels`. Gli occhi in più e
  l'escrescenza stanno sul fianco sinistro (sulle razze e sui pesci piatti: sul dorso).
- **bleeding** `bleeding(seed=9, ferite=[((t0, v0), (t1, v1))], bocca=None, denti=9, sangue_bocca=None,
  carne=0.0)`: tagli aperti con la carne viva sul fianco sinistro, sangue che cola, bocca aperta con i denti
  sporchi. `bocca` = gradi di apertura; il default (None) è 22 con la bocca di sempre (`bocca='terminale'`) e
  0 (chiusa, niente denti né goccia dal labbro) per le bocche ventrali degli squali e per chi non ha bocca
  (razze, lampreda): i denti degli squali, se servono, si fanno con un extra. Sul becco delle aguglie la
  bocca aperta apre il becco (bastano 10–14 gradi: è lungo). `carne` (0..1) la pelle che manca dappertutto.
- **glitch**: il pesce si costruisce normale; il glitch è sull'immagine:
  `glitch_post(seed=11, doppio=0.035, bande=9, separa=0.006, blocchi=4, righe=0.86, **effetti)` (opzioni:
  spostamento del doppio, bande strappate, colori separati, blocchi a pixel, righe), più gli effetti in più,
  tutti spenti di default (`effetti_glitch`): `saturazione` (> 1 colori troppo accesi), `sfocatura` (raggio,
  frazione della larghezza, ~0.006), `onda` (righe che ondeggiano, ~0.01–0.03), `copie` (copie a scatti dietro
  il pesce), `pixel` (lato del quadretto in px), `puntini` (retinatura, lato della cella in px), `interlacciato`
  (0..1: righe alterne che spariscono), `neve` (0..1), `tinta_bande` (0..1: bande con la tinta girata),
  `buchi` (0..1: bande sparite). Si mettono tutti in `opzioni`, per esempio
  `opzioni=dict(doppio=0.06, neve=0.5)`. Il foglio con gli effetti provati sulla salpa è
  `tools/render/cache/pesci/effetti_glitch.jpg`. Quello che non c'è (la festa di compleanno sotto l'alaccia,
  la bocca aperta e chiusa del pappagallo, la messa a fuoco solo sui denti) si fa con `ritocco(img, c)`
  (numpy sull'immagine RGBA 0..1; il canale alfa è la sagoma; `c.P.effetti_glitch` si può richiamare anche lì,
  per esempio su una maschera).

## 6. Le specie, famiglia per famiglia

Per ogni specie: il piano, la **forma** della specie vera da modellare (quello che la fa riconoscere), e i
**dettagli** che la descrizione del catalogo chiede di vedere. "Prova" = la voce già registrata da cui partire.

### Scheletrici (`scheletrici.py`) — carne mancante, lisca e cranio in vista

1. **`ossiuga`** — Ossiuga, acciuga (*Engraulis encrasicolus*) — `fusiforme`. Forma: piccola, affusolata,
   quasi cilindrica; il muso a punta sporge sopra una bocca enorme che arriva dietro l'occhio (mouth_t ~0.16);
   una dorsale sola a metà, coda forcuta; dorso verde-blu, fascia d'argento lungo il fianco (`strisce`).
   Dettagli: "banchi di mille… un rumore di ossicini, come dadi" → tante ossa fitte e sottili (vertebre ~44),
   uno scheletro minuto e pulito; la striscia di pelle con la fascia d'argento. Partenza: `sgombrato`.
2. **`spratteschio`** — Spratteschio, spratto (*Sprattus sprattus*) — `fusiforme`. Forma: piccolo, compresso,
   ventre carenato a scudetti (`linea` con scudi sul ventre), bocca piccola all'insù, dorsale a metà.
   Dettagli: "il teschio ti sta in punta di dito… batte i denti come chi ha freddo" → il cranio grande in
   proporzione e una fila di dentini che battono (extra: `denti_mascelle` piccoli fitti, bocca socchiusa).
3. **`sgombrato`** — PROTOTIPO.
4. **`lattossino`** — Lattossino, latterino (*Atherina boyeri*) — `fusiforme`. Forma: piccolo e slanciato,
   occhio grande, due dorsali ben separate, la fascia d'argento lungo il fianco. Dettagli: "trasparente da
   vivo, ancora di più adesso. Attraverso la lisca vedi il fondo" → quel che resta della pelle trasparente
   (`alfa` 0.3–0.5) con la sola fascia d'argento, ossa sottilissime e chiare.
5. **`bogossa`** — Bogossa, boga (*Boops boops*) — `fusiforme`. Forma: sparide slanciato, occhi enormi,
   bocca piccola, 3–4 righe dorate sottili sul fianco, macchietta scura all'ascella della pettorale.
   Dettagli: "ha gli occhi enormi di quando era viva. Le sono rimasti solo quelli" → occhi grandissimi
   (eye_r ~0.04) intatti e lucidi nel cranio spolpato; poca o niente pelle.
6. **`zerossa`** — Zerossa, zerro (*Spicara smaris*) — `fusiforme`. Forma: piccolo, slanciato, bocca
   protrattile, dorsale lunga, macchia scura sul fianco sopra la pettorale. Dettagli: "pulito come se
   l'avessero mangiato con calma, un boccone alla volta" → ossa pulitissime (`striscia=False`,
   `peduncolo=None`), forse i segni regolari dei morsi sulle ossa.
7. **`occhiata_vuota`** — Occhiata Vuota, occhiata (*Oblada melanura*) — `fusiforme`. Forma: sparide ovale,
   occhio grande, la macchia nera cerchiata di bianco sul peduncolo (`ocello`). Dettagli: "al posto degli
   occhi ha due buchi… e ti guarda lo stesso" → orbite vuote (`occhi=False`), la macchia del peduncolo che
   resta sulla coda carnosa.
8. **`ossaguglia`** — Ossaguglia, aguglia (*Belone belone*) — `rostro` (becco). Prova (il becco con i
   dentini, `Rostro('becco', denti=28)`). Dettagli: "ha le ossa verdi… un becco pieno di dentini. Ti punge"
   → `osso` verde (vedi `famiglie_sui_piani.jpg`), dentini più grossi e numerosi, magari aguzzi e sporchi
   (`denti_becco` con `lunghezza`/`raggio` maggiori e un altro materiale), lo scheletro lunghissimo
   (vertebre ~50).
9. **`ago_dosso`** — Ago d'Osso, pesce ago (*Syngnathus acus*) — `rostro` (tubo). Forma: lunghissimo e
   sottilissimo (alto ~1/30), rigido, muso a tubo lungo, `anelli` ~50, una dorsale piccola a metà, coda
   minuscola, niente pelviche. Dettagli: "un ago da cucito fatto d'osso. Qualcuno lo usa ancora per
   ricucire" → la cruna in coda con un filo infilato che pende (extra: `thread_material`).
10. **`san_pietrificato`** — San Pietrificato, pesce San Pietro (*Zeus faber*) — `alto`. Prova. Dettagli:
   "l'impronta di un pollice… piccolo, come quello di un bambino" → la macchia del fianco con le righe di
   un'impronta digitale, piccola; lo scheletro del corpo alto (spine lunghe fino ai bordi), i filamenti della
   dorsale come raggi d'osso.
11. **`ceca_ossuta`** — Ceca Ossuta, ceca (anguilla giovane, *Anguilla anguilla*) — `anguilliforme`. Forma: anguillina minuscola
    e trasparente, dorsale-anale-coda continue, occhi neri, testa piccola. Dettagli: "non ha mai avuto niente
    da nascondere… adesso si vede anche quello che ha mangiato" → corpo trasparente (`alfa`), la lisca
    dentro, e nella pancia qualcosa che ha mangiato (extra: un oggettino, una perlina, un dentino).
12. **`lucertossa`** — Lucertossa, pesce lucertola (*Synodus saurus*) — `fusiforme` (cilindrico). Forma: testa
    da lucertola piatta, bocca enormemente lunga, pinna adiposa, dorsale alta a metà, coda forcuta; righe blu
    e gialle. Dettagli: "più denti che ossa… sorride anche da morto" → tantissimi denti (`denti_mascelle` con
    n alto, anche più file), il ghigno.
13. **`sciabola_spolpata`** — Sciabola Spolpata, pesce sciabola (*Lepidopus caudatus*) — `nastriforme`.
    Prova. Dettagli: "lungo come un braccio, sottile come una lama… rumore di posate" → la lisca lunghissima
    e lucida come una lama (vertebre ~70, costole fino in fondo), le zanne.
14. **`lanternossa`** — Lanternossa, pesce lanterna (*Myctophum punctatum*) — `fusiforme` + fotofori. Prova.
    Dettagli: "le lucine… rimaste accese sulle ossa. Al buio sembra un piccolo parco giochi visto da
    lontano" → i fotofori accesi attaccati alle ossa (con un extra, o lasciati dove stava la pelle, come un
    contorno di lucine), magari di colori diversi come un luna park.
15. **`cavalluccio_dosso`** — Cavalluccio d'Osso, cavalluccio marino (*Hippocampus guttulatus*) —
    `cavalluccio`. Prova. Dettagli: "un cavallino da giostra, senza la giostra" → lo scheletro ad anelli,
    tracce di vernice da giostra, o il palo dorato che lo attraversa.
16. **`flauto_dossa`** — Flauto d'Ossa, pesce flauto (*Fistularia commersonii*) — `rostro` (tubo). Forma:
    lunghissimo e sottile, muso a tubo lungo un quarto del corpo, dorsale e anale piccole opposte vicino alla
    coda, coda forcuta con il filo centrale lunghissimo (`Filamento` in punta, come la chimera); macchie
    azzurre. Dettagli: "se ci soffi dentro suona… la nota del carillon" → i buchi del flauto lungo il tubo
    (`campo`: fori).
17. **`trombetta_dosso`** — Trombetta d'Osso, pesce trombetta (*Macroramphosus scolopax*) — `alto` + tubo.
    Forma: corpo piccolo, alto e compresso, muso a tubo lungo, una spina dorsale lunghissima e seghettata,
    coda piccola; rosa-argento. Dettagli: "il muso a trombetta… le trombette che suonavano i bambini" → il
    tubo finisce in una campana di trombetta di plastica (extra).
18. **`aquila_dosso`** — Aquila d'Osso, aquila di mare (*Myliobatis aquila*) — `razza`. Forma: ali appuntite
    larghissime, la testa tonda che sporge davanti al disco, occhi ai lati della testa, coda a frusta
    lunghissima con il pungiglione e una dorsale piccola alla base. Dettagli: "le razze non hanno ossa…
    questa ne ha trovate, e non sono di pesce" → ossa da mammifero, quasi umane: falangi nelle ali come dita,
    una gabbia toracica, clavicole (extra, con `raggi_disco=0`: il ventaglio di cartilagine qui non c'è).
    Partenza: `pastinaca_putrida` (la coda a frusta, il pungiglione) con il disco da rifare (ali appuntite).
19. **`spadossa`** — Spadossa, pesce spada (*Xiphias gladius*) — `rostro` (spada). Prova. Dettagli: "solo la
    spada e lo scheletro, in posa da combattimento. Sulla spada è infilato un braccialetto di plastica
    fucsia" → spada intatta, scheletro completo, il braccialetto fucsia infilato a metà spada (extra: un
    toro di plastica lucida).
20. **`sega_dossa`** — Sega d'Ossa, pesce sega (*Pristis pectinata*) — `razza` + sega. Prova. Dettagli: "nel
    Mediterraneo non se ne vedono da cent'anni. Questo non lo sa" → ossa vecchie e ingiallite (`osso`),
    incrostazioni, qualche dente della sega mancante. Lo scheletro delle razze c'è già (il ventaglio di
    cartilagine, `famiglie_sui_piani.jpg`): `cranio_t` ~0.15.

### Zombi (`zombi.py`) — marci, occhi lattiginosi, pinne strappate, punti di sutura

1. **`cefamorto`** — Cefamorto, cefalo (*Mugil cephalus*) — `fusiforme`. Forma: robusto, quasi cilindrico,
   testa larga e piatta sopra, bocca piccola, palpebra adiposa sugli occhi, due dorsali ben separate (la
   prima di 4 spine), coda forcuta; grigio con righe scure lungo il corpo. Dettagli: "mangia il fango…
   adesso il fango mangia lui" → croste e colature di fango scuro (`marmo` fangoso, gocce), la bocca sporca.
2. **`sogliombra`** — Sogliombra, sogliola (*Solea solea*) — `piatto`. Prova. Dettagli: "tutti e due gli
   occhi dalla stessa parte. Da morta ha deciso di guardare anche dall'altra" → un occhio lattiginoso in
   più che spunta sul bordo verso il lato cieco (extra), la cucitura sul lato degli occhi.
3. **`suro_sfatto`** — Suro Sfatto, suro (*Trachurus trachurus*) — `fusiforme`. Forma: affusolato, occhio
   grande, la linea laterale coperta di scudetti ossei per tutta la lunghezza (`linea` con `n`, o `Spine` in
   fila), macchia nera sull'opercolo, due dorsali. Dettagli: "si sfalda come pane bagnato. Le scaglie che
   restano sul legno brillano tutta la notte" → pelle che si sfalda a lembi, scagliette luminose
   (emissive) sparse addosso e attorno.
4. **`nasello_senza_naso`** — Nasello Senza Naso, nasello (*Merluccius merluccius*) — `fusiforme`. Forma:
   lungo, testa grande, bocca larga con la mandibola sporgente, due dorsali (la seconda lunghissima), anale
   lunga, coda tronca; grigio argento. Dettagli: "il naso gli è caduto da tempo" → la punta del muso
   mancante, un moncherino marcio (`campo`: taglio frastagliato).
5. **`tordo_torbido`** — Tordo Torbido, tordo marvizzo (*Labrus bergylta*) — `fusiforme`. Forma: robusto,
   labbra grosse, dorsale lunga spinosa, coda tonda, pelle macchiettata. Dettagli: "occhi torbidi come
   l'acqua di una pozzanghera. Fa le bolle" → occhi lattiginosi molto torbidi, bolle che escono dalla
   bocca (extra: sferette trasparenti).
6. **`orrata`** — PROTOTIPO.
7. **`sarcofago`** — Sarcofago, sarago maggiore (*Diplodus sargus*) — `fusiforme` (alto). Forma: sparide
   ovale, bande verticali scure, macchia nera sul peduncolo, muso a punta. Dettagli: "bande nere come le
   fasce di una mummia. Ogni tanto una si scioglie, e sotto non c'è più il pesce" → le bande come bende in
   rilievo (extra), una che si srotola e pende, sotto il vuoto (`campo`).
8. **`gattomorto`** — Gattomorto, gattuccio (*Scyliorhinus canicula*) — `squalo`. Forma: piccolo squalo
   slanciato, testa corta e piatta, occhi da gatto (`eye_allungato` ~1.6, pupilla a fessura), due dorsali
   molto arretrate, coda bassa quasi orizzontale, pelle con tante macchioline scure. Partenza:
   `verdesca_ferita` (coda più bassa, dorsali arretrate). Dettagli: "fa il gatto morto" → a pancia all'aria
   (`Ritratto(roll=180)` o di sbieco), occhi lattiginosi.
9. **`corvina_becchina`** — Corvina Becchina, corvina (*Sciaena umbra*) — `fusiforme`. Forma: dorso arcuato,
   muso tondo, due dorsali unite, coda tronca; bronzo scuro, pelviche e anale nere orlate di bianco.
   Dettagli: "brontola come i becchini… la terra che cade sul legno" → terra di camposanto addosso (grumi).
10. **`palombra`** — Palombra, palombo (*Mustelus mustelus*) — `squalo`. Forma: squalo slanciato grigio,
    muso tondo, due dorsali simili, coda con il lobo basso piccolo, niente macchie. Partenza:
    `verdesca_ferita`. Dettagli: "grigio come un
    cane vecchio… ti segue" → grigio spento, occhi da cane vecchio lattiginosi.
11. **`pastinaca_putrida`** — Pastinaca Putrida, pastinaca (*Dasyatis pastinaca*) — `razza`. Prova (la coda
    a frusta). Dettagli: "la senti prima di vederla. Il pungiglione è l'unica cosa che funziona" → disco
    marcio e cascante (bordi che pendono: `campo`), il pungiglione intatto, lucido e seghettato (un oggetto a
    parte con il suo materiale, al posto della `Spine`).
12. **`castagna_marcia`** — Castagna Marcia, pesce castagna (*Brama brama*) — `alto`. Forma: alto e compresso,
    profilo ripido, dorsale e anale lunghe e falcate, coda profondamente forcuta; nero lucido. Dettagli:
    "nera e lucida come una castagna… piena di piccoli vermi bianchi che ballano" → buchi da cui escono
    vermetti bianchi (extra: filamenti corti piegati).
13. **`ombrina_smorta`** — Ombrina Smorta, ombrina (*Umbrina cirrosa*) — `fusiforme`. Forma: allungata, dorso
    arcuato, un barbiglio corto sotto il mento (`Filamento` `lati='centro'`), righe oblique ondulate dorate,
    coda tronca. Dettagli: "la vescica non ce l'ha più, ma il tamburo continua" → la pancia aperta e vuota
    (`campo`), magari una pelle tesa come un tamburo.
14. **`branzombi`** — Branzombi, spigola (*Dicentrarchus labrax*) — `fusiforme`. Forma: slanciata, due dorsali
    separate, opercolo spinoso, bocca grande; argento. Dettagli: "il pesce più bello del secchio, se non
    fosse per gli occhi bianchi come il latte. Continua a boccheggiare" → poco marcio (`marcio` 0.6),
    occhi bianchissimi, bocca aperta (`bocca_aperta`).
15. **`murena_murata`** — Murena Murata, murena (*Muraena helena*) — `anguilliforme`. Prova. Dettagli:
    "sempre nella stessa fessura, con la bocca aperta… hanno chiuso la fessura, una pietra alla volta" →
    pietre e malta attaccate al corpo (extra), la bocca aperta con le zanne.
16. **`raccapricciola`** — Raccapricciola, ricciola (*Seriola dumerili*) — `fusiforme`. Forma: robusta,
    affusolata, la fascia ambra obliqua dall'occhio alla dorsale, coda forcuta. Dettagli: "metà del corpo
    se n'è andata da un pezzo" → la metà posteriore marcita fino alla lisca (`campo` che toglie la carne e
    un extra con le vertebre, o le ossa della funzione skeletal).
17. **`cernia_gemente`** — Cernia Gemente, cernia bruna (*Epinephelus marginatus*) — `fusiforme`. Forma:
    massiccia, testa grande, bocca enorme con la mandibola sporgente, coda tonda; bruna con chiazze chiare.
    Dettagli: "geme piano come un vecchio… sessant'anni, e da quaranta è morta" → pelle vecchia a pieghe
    cadenti (`campo`: grinze), bocca socchiusa.
18. **`rombo_sepolto`** — Rombo Sepolto, rombo chiodato (*Scophthalmus maximus*) — `piatto`. Forma: quasi
    tondo, occhi sul lato −1, tubercoli ossei sparsi (`Spine` corte e larghe), dorsale che parte davanti
    agli occhi; marmorizzato. Partenza: `sogliombra`. Dettagli: "si è seppellito tanto tempo fa, e non è più
    riuscito a uscire" → coperto di sabbia (puntini chiari, croste), mezzo sepolto.
19. **`chimera_bianca`** — Chimera Bianca, chimera (*Chimaera monstrosa*) — `coda_di_topo`. Prova. Dettagli:
    "la lampara le fa male: chiude gli occhi enormi e piange una cosa grigia" → palpebre chiuse o socchiuse
    (extra) e lacrime grigie che colano.
20. **`squalo_capomorto`** — Squalo Capomorto, squalo capopiatto (*Hexanchus griseus*) — `squalo`. Forma:
    testa larga e piatta, **sei** fessure branchiali, una sola dorsale molto arretrata, coda lunga; occhi
    verdi; grigio-bruno. Partenza: `verdesca_ferita`. Dettagli: "sei branchie, e respira con tutte e sei" →
    le sei fessure aperte e marce, rosse dentro.

### Glitchati (`glitchati.py`) — fette sfalsate, colori separati, nastro rovinato

Il pesce si costruisce normale (forma e aspetto della specie vera, curati come per le altre famiglie); il
glitch è sull'immagine: `opzioni` per `glitch_post`, e `ritocco(img, c)` per il glitch proprio della specie.

1. **`triglia_doppia`** — Triglia Doppia, triglia di fango (*Mullus barbatus*) — `fusiforme`. Forma: come
   `trigliocchi` ma con la fronte più ripida, rosa uniforme senza fasce gialle, i due barbigli. Dettagli:
   "si vede due volte, un poco spostata… solo una è nel secchio" → un doppio forte e netto.
2. **`lanzardo_riavvolto`** — Lanzardo Riavvolto, lanzardo (*Scomber colias*) — `fusiforme`. Forma: come lo
   sgombro (`sgombrato`), occhio più grande, macchiette scure sul ventre. Dettagli: "nuota all'indietro, a
   scatti, come un nastro riavvolto" → righe stirate all'indietro, scie, magari girato verso destra.
3. **`donzella_saturata`** — Donzella Saturata, donzella (*Coris julis*) — `fusiforme`. Forma: labride
   piccolo e slanciato, muso appuntito; la fascia arancione a zig-zag lungo il fianco (`strisce` con onda),
   la macchia nera dietro la pettorale. Dettagli: "colori troppo accesi, come le cassette consumate" →
   saturazione esagerata, colori che sbavano.
4. **`castagnola_sgranata`** — Castagnola Sgranata, castagnola (*Chromis chromis*) — `alto` (piccolo). Forma:
   piccola e alta, coda profondamente forcuta, bruno-blu. Dettagli: "tutta puntini, come una foto
   ingrandita troppo. Più ti avvicini, meno pesce c'è" → retinatura a punti, più rada al centro.
5. **`pagello_pixelato`** — Pagello Pixelato, pagello fragolino (*Pagellus erythrinus*) — `fusiforme`.
   Forma: sparide rosa con puntini azzurri sul dorso. Dettagli: "ha gli spigoli… e qualche quadratino in
   meno" → pixel grossi, qualche blocco trasparente.
6. **`menola_neve`** — Menola Neve, menola (*Spicara maena*) — `fusiforme`. Forma: come lo zerro ma più alta,
   macchia scura rettangolare sul fianco. Dettagli: "coperta di neve bianca e nera che sfrigola" → neve
   televisiva dentro la sagoma.
7. **`salpa_sfasata`** — PROTOTIPO.
8. **`pettine_a_scatti`** — Pettine a Scatti, pesce pettine (*Xyrichtys novacula*) — `alto`. Forma: compresso,
   la fronte verticale a picco, dorsale lunga, coda tronca; rosato con righe azzurre sul muso. Dettagli:
   "si muove a scatti, saltando dei fotogrammi" → copie spostate a scatti, fotogrammi mancanti.
9. **`re_di_triglie_a_righe`** — Re di Triglie a Righe, re di triglie (*Apogon imberbis*) — `fusiforme`.
   Forma: piccolo, testa e occhi grandi, due dorsali separate, rosso-arancio, punto scuro sul peduncolo.
   Dettagli: "righe orizzontali, una sì e una no. Nelle righe che mancano c'è un altro pesce" →
   interlacciato, con un altro pesce (un'altra immagine) nelle righe vuote.
10. **`occhialone_veloce`** — Occhialone Veloce, occhialone (*Pagellus bogaraveo*) — `fusiforme`. Forma:
    sparide con l'occhio grandissimo e la macchia nera all'inizio della linea laterale. Dettagli: "giovane
    quando lo tiri su, vecchio nel secchio, domattina polvere" → la coda che si sbriciola in polvere.
11. **`balestra_sfocata`** — Balestra Sfocata, pesce balestra (*Balistes capriscus*) — `alto`. Forma: corpo
    alto romboidale, occhi alti e arretrati, bocca piccolissima con i denti, la prima dorsale con la spina
    grossa a grilletto, seconda dorsale e anale lunghe opposte, coda a lira; grigio-oliva. Dettagli:
    "sfocato… si mette a fuoco solo quando morde" → tutto sfocato tranne la bocca con i denti.
12. **`torpedine_statica`** — Torpedine Statica, torpedine marmorata (*Torpedo marmorata*) — `razza`. Forma:
    disco quasi rotondo, coda corta e carnosa con due dorsali e la caudale grande, marmorizzata. Partenza:
    `razza_inchiodata` (contorno tondo, niente spine). Dettagli: "fa la neve come un televisore acceso su un
    canale vuoto" → neve sul disco, scintille azzurre.
13. **`anguilla_smagnetizzata`** — Anguilla Smagnetizzata, anguilla (*Anguilla anguilla*) — `anguilliforme`.
    Forma: cilindrica lunghissima, testa piccola con la mandibola un po' più lunga, pettorali piccole e tonde,
    dorsale che parte a un terzo, unita ad anale e coda; bruno-verde sopra, giallastra sotto. Partenza:
    `murena_murata`. Dettagli: "come un nastro lasciato al sole" → nastro ondulato e stirato, colori sbiaditi.
14. **`pappagallo_in_loop`** — Pappagallo in Loop, pesce pappagallo (*Sparisoma cretense*) — `fusiforme`.
    Forma: ovale robusto, il becco dei denti fusi (come `_becco_pesce_palla`), squame grandi, rosso e grigio
    con la macchia gialla. Dettagli: "apre la bocca, la chiude, apre la bocca" → due pose sovrapposte.
15. **`leccia_senza_segnale`** — Leccia Senza Segnale, leccia (*Lichia amia*) — `fusiforme`. Forma: compressa,
    la linea laterale ondulata ben visibile (`linea` con `onda`), dorsale e anale falcate, coda forcuta.
    Dettagli: "compare e scompare come un canale che non prende" → pezzi mancanti a bande.
16. **`civetta_fuori_quadro`** — Civetta Fuori Quadro, pesce civetta (*Dactylopterus volitans*) —
    `pettorali`. Forma: testa corazzata squadrata con una spina lunga, pettorali enormi a ventaglio blu
    puntinate aperte di lato, coda forcuta. Partenza: `gallincubo`. Dettagli: "non sta mai tutta
    nell'inquadratura" → `Ritratto(centro=..., riquadro=...)` che lo fa uscire dal bordo.
17. **`pesce_volante_in_pausa`** — Pesce Volante in Pausa, pesce volante (*Cheilopogon heterurus*) —
    `pettorali`. Prova. Dettagli: "fermo a mezz'aria, tremolante come un fermo immagine" → le righe di
    disturbo del fermo immagine VHS, un leggero tremolio.
18. **`alaccia_registrata_sopra`** — Alaccia Registrata Sopra, alaccia (*Sardinella aurita*) — `fusiforme`.
    Forma: clupeide slanciato con la riga dorata, ventre carenato, macchia scura sull'opercolo. Dettagli: "si
    vede la registrazione di prima: una festa di compleanno, le candeline" → immagine fantasma di candeline
    e coriandoli sotto il pesce.
19. **`cheppia_senza_audio`** — Cheppia Senza Audio, cheppia (*Alosa fallax*) — `fusiforme`. Forma: clupeide
    alto e compresso, ventre a dente di sega, una fila di macchie scure dietro l'opercolo. Dettagli: "si
    dibatte senza fare rumore" → spruzzi fermi, muti (gocce sospese), un glitch discreto.
20. **`lampuga_fuori_traccia`** — Lampuga Fuori Traccia, lampuga (*Coryphaena hippurus*) — `fusiforme`. Forma:
    la fronte altissima e verticale, dorsale da sopra l'occhio fino alla coda, coda profondamente forcuta;
    oro-verde con puntini azzurri. Dettagli: "cambia colore a strisce, come una cassetta che si sta per
    rompere" → fasce di colore con la tinta ruotata.

### Corrotti (`corrotti.py`) — occhi in più, bocche sbagliate, escrescenze, melma nera

1. **`trigliocchi`** — PROTOTIPO.
2. **`sardonica`** — Sardonica, sardina (*Sardina pilchardus*) — `fusiforme`. Forma: clupeide, macchie scure
   sul fianco, ventre carenato. Dettagli: "il sorriso sardonico dei morti: labbra tirate, tutti i denti in
   vista. Le sardine non hanno denti" → una dentatura umana in vista (extra).
3. **`ghiozzo_gozzuto`** — Ghiozzo Gozzuto, ghiozzo nero (*Gobius niger*) — `fusiforme`. Forma: testa grossa
   e larga, occhi alti e vicini, due dorsali, pelviche fuse a ventosa, coda tonda; bruno scuro. Dettagli:
   "sotto la gola una sacca nera e molle" → `escrescenza` sotto la gola, nera e lucida.
4. **`bavaccia`** — Bavaccia, bavosa (*Parablennius gattorugine*) — `fusiforme`. Forma: testa tozza dal
   profilo ripido, cirri ramificati sopra gli occhi (`filamenti`), dorsale lunga continua, labbra grosse,
   coda tonda; bruna a bande. Dettagli: "sbava melma nera senza fermarsi" → pece che cola dalla bocca.
5. **`scorfano_pece`** — Scorfano Pece, scorfano nero (*Scorpaena porcus*) — `fusiforme`. Forma: testa grossa
   con le spine (`Spine`) e i lembi di pelle sopra gli occhi (`filamenti`), bocca grande, dorsale spinosa,
   pettorali larghe, coda tonda; bruno marmorizzato. Dettagli: "gli cola pece nera dalle spine" → pece che
   cola dalle punte della dorsale e della testa.
6. **`sciarrano_scrivano`** — Sciarrano Scrivano, sciarrano (*Serranus scriba*) — `fusiforme`. Forma: bande
   verticali scure, macchia blu-viola sul ventre, ghirigori sulla testa (`vermi` sulla testa). Dettagli:
   "le scritte si leggono: sono date. L'ultima è di stanotte" → date leggibili sulla testa (extra: una
   texture con il testo, per esempio fatta con PIL).
7. **`gallincubo`** — Gallincubo, gallinella (*Chelidonichthys lucerna*) — `pettorali`. Prova. Dettagli: "le
   pinne davanti sono diventate dita… di notte bussa" → i raggi liberi diventano dita umane con nocche e
   unghie (extra al posto di `liberi`).
8. **`mostrella`** — Mostrella, mostella (*Phycis phycis*) — `fusiforme`. Forma: allungata, barbiglio sotto il
   mento, prima dorsale corta, seconda e anale lunghissime, pelviche ridotte a due filamenti lunghi, coda
   tonda. Dettagli: "al posto della barbetta un ciuffo di filamenti neri che si muovono da soli" → tanti
   filamenti neri lucidi sotto il mento.
9. **`mormoria`** — Mormorìa, mormora (*Lithognathus mormyrus*) — `fusiforme`. Forma: sparide allungato,
   muso appuntito, 12–14 bande verticali scure sottili, argento. Dettagli: "dalle branchie un brusio, come
   un parco pieno di gente lontano" → l'opercolo socchiuso con dentro tante boccucce o occhietti.
10. **`luciferna`** — Luciferna, pesce prete (*Uranoscopus scaber*) — `fusiforme`. Forma: testa grande e
   squadrata, occhi in cima che guardano in su (`occhi` sul dorso), bocca verticale all'insù con le frange,
   pettorali larghe. Dettagli: "gli occhi rivolti in su… una fila intera, verso la barca" → una fila di
   occhi in più sul dorso (`occhi_extra` a v ~0.9).
11. **`bocchenere`** — Bocchenere, squalo boccanera (*Galeus melastomus*) — `squalo`. Forma: piccolo squalo
    slanciato, muso lungo, occhi grandi da gatto, l'interno della bocca nero, macchie a sella sul dorso.
    Partenza: `verdesca_ferita`. Dettagli: "una bocca nera, poi un'altra sul fianco, poi un'altra" → bocche
    nere in più sul fianco (`campo`: tagli a mezzaluna; extra: denti).
12. **`pesce_bubbone`** — Pesce Bubbone, pesce palla argenteo (*Lagocephalus sceleratus*) — `palla`. Prova.
    Dettagli: "si gonfiano anche le bolle nere che ha sulla pelle" → pustole nere in rilievo al posto delle
    macchie.
13. **`missina_della_melma`** — Missina della Melma, missina (*Myxine glutinosa*) — `anguilliforme`. Prova.
    Dettagli: "tanta melma da riempire il secchio. È nera, ed è tiepida" → fili e colate di melma nera.
14. **`specchio_nero`** — Specchio Nero, pesce specchio (*Hoplostethus mediterraneus*) — `alto`. Forma: alto e
    compresso, testa enorme con le cavità mucose, occhi grandi, scudetti sul ventre, coda forcuta; rosato.
    Dettagli: "una macchia nera lucida come uno specchio… dentro c'è la barca, e qualcuno in più" → la
    macchia-specchio con dentro la barca e una figura in più (extra con un materiale immagine).
15. **`sciabola_di_carbone`** — Sciabola di Carbone, pesce sciabola nero (*Aphanopus carbo*) — `nastriforme`.
    Partenza: `sciabola_spolpata` (nera, occhi enormi). Dettagli: "occhi grandi come monete, e dentro una
    lampara accesa" → occhi enormi con un puntino di luce calda.
16. **`granatiere_nero`** — Granatiere Nero, granatiere (*Coelorinchus caelorhincus*) — `coda_di_topo`.
    Forma: testa grossa, muso appuntito che sporge sopra la bocca, occhi grandi, barbiglio sotto il mento,
    corpo che finisce in una coda da topo. Partenza: `chimera_bianca`. Dettagli: "una coda come quella di un
    topo… cento sotto la barca" → coda nuda da topo, baffi.
17. **`vipera_degli_abissi`** — Vipera degli Abissi, pesce vipera (*Chauliodus sloani*) — `fusiforme`
    (allungato) + fotofori. Forma: corpo allungato, bocca enorme con zanne lunghissime che restano fuori, il
    primo raggio della dorsale lunghissimo, fotofori lungo il ventre. Dettagli: "i denti così lunghi che non
    riesce a chiudere la bocca" → le zanne fuori dalla bocca.
18. **`razza_due_facce`** — Razza dalle Due Facce, razza bianca (*Rostroraja alba*) — `razza`. Forma: disco a
    rombo con il muso lungo e appuntito, bianca sotto. Partenza: `razza_inchiodata`. Dettagli: "sotto, le
    razze hanno una faccia che sembra sorridere. Questa ne ha due, e non sorridono" → si mostra il ventre
    (`Ritratto(roll=142)`) con due facce di narici e bocca (`campo`, extra).
19. **`pesce_angelo_caduto`** — Pesce Angelo Caduto, squadro (*Squatina squatina*) — `razza`. Forma: squalo
    piatto, testa larga con la bocca davanti, pettorali come ali staccate dalla testa, pelviche larghe, due
    dorsali sulla coda, caudale. Partenza: `sega_dossa`. Dettagli: "le ali nere e bagnate, e attorno alla
    testa un'aureola di occhi" → ali nere lucide, un anello di occhi attorno alla testa.
20. **`re_nero`** — Re Nero, pesce re (*Lampris guttatus*) — `alto`. Forma: ovale altissimo, dorsale falcata
    alta davanti, pettorali lunghe, coda a mezzaluna; qui nero come la pece. Dettagli: "al posto della
    corona ha una bocca" → una bocca dentata sulla nuca al posto della corona.

### Sanguinanti (`sanguinanti.py`) — ferite, denti sporchi, colature

1. **`trafittina`** — Trafittina, tracina drago (*Trachinus draco*) — `fusiforme`. Forma: allungata e
   compressa, occhi alti, bocca obliqua all'insù, prima dorsale corta nera con le spine, seconda dorsale e
   anale lunghe, spina sull'opercolo; righe oblique gialle e azzurre. Dettagli: "piange sangue dagli occhi…
   la spina della schiena le è entrata dentro" → lacrime di sangue, una spina piegata e conficcata nel dorso.
2. **`serrasangue`** — Serrasangue, pesce serra (*Pomatomus saltatrix*) — `fusiforme`. Forma: robusto, testa
   grande con la bocca larga e i denti taglienti, coda forcuta; verde-blu sopra. Dettagli: "pieno di morsi,
   ognuno della forma della sua bocca" → morsi a mezzaluna con i segni dei denti (ferite corte ad arco).
3. **`squartotta`** — Squartotta, sparaglione (*Diplodus annularis*) — `alto`. Forma: piccolo sparide ovale,
   l'anello nero sul peduncolo, pelviche gialle. Dettagli: "un taglio netto da parte a parte" → una fetta
   tolta che attraversa il corpo (`campo`), la carne viva sulle due facce.
4. **`pagro_sanguigno`** — Pagro Sanguigno, pagro (*Pagrus pagrus*) — `fusiforme`. Forma: sparide rosa con
   puntini azzurri, fronte ripida. Dettagli: "sanguina dalle branchie, come se respirasse sangue" → sangue
   dal bordo dell'opercolo.
5. **`barracruda`** — PROTOTIPO.
6. **`razza_inchiodata`** — Razza Inchiodata, razza chiodata (*Raja clavata*) — `razza`. Prova. Dettagli: "le
   spine sono diventate chiodi veri, arrugginiti… si è staccata da sola" → chiodi arrugginiti al posto delle
   spine (extra), fori strappati sulle ali; `bocca=0`.
7. **`scorticano`** — Scorticano, scorfano rosso (*Scorpaena scrofa*) — `fusiforme`. Forma: come lo scorfano
   nero ma più grande e rosso, lembi di pelle sul mento. Dettagli: "gli manca la pelle. Le spine invece ci
   sono tutte" → `carne=1` (carne viva dappertutto), spine intatte.
8. **`rabbiglio`** — Rabbiglio, pesce coniglio (*Siganus luridus*) — `alto`. Forma: compresso ovale, bocca
   piccola, dorsale e anale spinose lunghe, coda tronca; bruno-oliva. Dettagli: "i denti da coniglio e la
   schiuma rosa alla bocca" → incisivi da coniglio, schiuma rosa (sferette).
9. **`palamita_squarciata`** — Palamita Squarciata, palamita (*Sarda sarda*) — `fusiforme`. Forma: come il
   tonno ma più slanciata, righe oblique scure sul dorso, pinnule. Partenza: `tonno_di_sangue`. Dettagli:
   "uno squarcio dalla testa alla coda… tanti denti, tutti in fila" → una ferita lunghissima con i segni dei
   denti in fila.
10. **`leccia_lacerata`** — Leccia Lacerata, leccia stella (*Trachinotus ovatus*) — `alto`. Forma: compressa,
    lobi scuri e falcati di dorsale e anale, coda forcuta, 3–5 macchie nere sulla linea laterale. Dettagli:
    "ferite piccole e regolari su tutto il corpo" → tante ferite corte in griglia.
11. **`dentiera`** — Dentiera, dentice (*Dentex dentex*) — `fusiforme`. Forma: sparide robusto, testa
    grande, canini lunghi, puntini blu sul dorso. Dettagli: "i denti non sono i suoi… di misure diverse, e
    qualcuno ha ancora l'apparecchio" → denti umani di misure diverse e un apparecchio di filo d'acciaio.
12. **`grondongo`** — Grondongo, grongo (*Conger conger*) — `anguilliforme`. Forma: grosso, cilindrico, la
    mascella di sopra più lunga, occhi grandi, pettorali, dorsale che parte sopra le pettorali, grigio scuro
    con il bordo delle pinne nero. Partenza: `murena_murata`. Dettagli: "esce dall'acqua grondando, e non è
    acqua" → colature di sangue da tutto il corpo.
13. **`lampreda_vampira`** — Lampreda Vampira, lampreda di mare (*Petromyzon marinus*) — `anguilliforme`.
    Prova. Dettagli: "al posto della bocca un cerchio di denti… succhia piano" → il disco insanguinato, denti
    sporchi; `bocca=0`.
14. **`pesce_violento`** — Pesce Violento, pesce violino (*Rhinobatos rhinobatos*) — `razza`. Forma: disco a
    cuneo (muso appuntito), coda spessa da squalo con due dorsali grandi e la caudale. Partenza: `sega_dossa`
    (senza sega). Dettagli: "le corde sono i suoi nervi, tesi da una ferita all'altra" → fili tesi fra due
    tagli sul dorso, come le corde di un violino.
15. **`pilota_sanguinante`** — Pilota Sanguinante, pesce pilota (*Naucrates ductor*) — `fusiforme`. Forma:
    affusolato, 5–7 bande verticali scure larghe, coda con le punte bianche. Dettagli: "ogni tanto quel
    qualcuno lo morde" → un grosso morso che porta via un pezzo (`campo`).
16. **`remora_strappata`** — Remora Strappata, remora (*Remora remora*) — `fusiforme`. Prova. Dettagli:
    "strappata via… ha ancora un pezzo di pelle grigia sulla ventosa" → un lembo di pelle grigia (di Gulpy)
    attaccato alla ventosa.
17. **`verdesca_ferita`** — Verdesca Ferita, verdesca (*Prionace glauca*) — `squalo`. Prova (la coda
    eterocerca). Dettagli: "il sangue era il suo" → ferite profonde che sanguinano (la bocca resta chiusa di
    default, vedi §5; i denti sporchi, se servono, con un extra).
18. **`aguglia_imperiale`** — Aguglia Imperiale Trafitta, aguglia imperiale (*Tetrapturus belone*) —
    `rostro`. Forma: slanciata, rostro corto e tondo, dorsale lunga e alta davanti, coda a mezzaluna; blu
    scuro. Partenza: `spadossa`. Dettagli: "ha trafitto qualcosa con il rostro… ancora lì, infilata, e si
    muove" → la cosa infilata sul rostro (extra).
19. **`volpe_sfregiata`** — Volpe Sfregiata, squalo volpe (*Alopias vulpinus*) — `squalo`. Prova. Dettagli:
    "una cicatrice per ogni volta che ha mancato il colpo" → cicatrici chiare sulla coda e sul corpo.
20. **`tonno_di_sangue`** — Tonno di Sangue, tonno rosso (*Thunnus thynnus*) — `fusiforme`. Prova. Dettagli:
    "si ricorda tutte le mattanze" → ferite da arpione e raffio, uncini infilati, tanto sangue.

## 7. Controllo finale di ogni famiglia

- `--elenco`: nessun errore, nessuna specie mancante della tua famiglia, nessuna `normale` rimasta.
- Il foglio della famiglia: ogni pesce si riconosce, i dettagli della descrizione si vedono, nessuno è
  tagliato dal bordo (salvo la Civetta), lo stile è quello dei prototipi.
- Le anteprime `--fast` hanno la griglia più grossa: dettagli sotto i 4–5 mm (un centesimo della lunghezza
  di un pesce) si vedono solo nel render finale; prima di consegnare rendi le specie più delicate con
  `--anteprima` senza `--fast`, una alla volta.
