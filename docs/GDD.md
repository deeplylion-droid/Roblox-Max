# LAMPARA — Game Design Document

> *Raggiungi la quota prima delle sei. Sfama i Piccoli. Non farti trovare.*

Versione 0.1 — obiettivo del primo traguardo: **Notte 1 completa e rifinita** (vertical slice).

## 1. Il gioco in una frase

Horror in prima persona a inquadratura fissa (alla *Five Nights at Freddy's*): sei il pescatore di turno sopra **il Pozzo**, la voragine al centro della baia di **Santa Brina**. Devi riempire il secchio con la **quota di pesci** entro le 6:00, mentre i **Piccoli del Fondo**, creature anfibie dall'aria tenera e dai denti sbagliati, salgono a bordo. Ognuno vuole qualcosa di diverso.

## 2. Pilastri

1. **Lavorare mentre si ha paura.** In FNAF sopravvivi e basta; qui devi anche *produrre*. Ogni secondo passato a difenderti è un secondo in cui non peschi.
2. **Il pesce è insieme obiettivo e moneta.** Lo stesso pesce che serve alla quota è quello che devi lanciare a Pappo per non farti mangiare.
3. **La lampara è un'avidità regolabile.** Più luce = più pesci che abboccano, ma anche più Piccoli che salgono.
4. **Tre minacce, tre direzioni, tre risposte.** Prua → *sfamare*. Fianchi → *guardare*. Poppa → *nascondersi*. Leggibile al primo sguardo, difficile quando si sovrappongono.
5. **Coccoloso finché non apre la bocca.** Proporzioni da neonato, accessori da cameretta, pelle lucida e bagnata, occhi che riflettono la luce come quelli dei gatti.

## 3. Visuale e controlli

- Sei seduto al centro del gozzo. La visuale è un **panorama pre-renderizzato a 360°** proiettato in prospettiva: puoi ruotare liberamente lo sguardo (bordi dello schermo col mouse, `A`/`D`, frecce) e voltarti di scatto (`S` o pulsante in basso).
- La barca **dondola** davvero rispetto all'orizzonte: il mondo e lo scafo sono strati separati.
- Interazioni col mouse (clic sugli oggetti) o tasti:

| Azione | Mouse | Tastiera |
|---|---|---|
| Ruotare lo sguardo | bordi dello schermo | `A` `D` / `←` `→` |
| Voltarsi (prua ↔ poppa) | barra in basso | `S` / `↓` |
| Lanciare / ferrare / recuperare la lenza | clic (tenere premuto) sulla canna | `Spazio` |
| Lanciare un pesce a Pappo | clic sul secchio | `F` |
| Nascondersi sotto il telone / uscire | clic sul telone | `C` / `Ctrl` |
| Lampara: abbassa / alza | rotella o clic sull'interruttore | `Q` / `E` |
| Sonar a tutto schermo | barra in alto | `Tab` |
| Pausa | | `Esc` |

## 4. Struttura della notte

- Dalle **00:00 alle 06:00**; un'ora di gioco dura **75 secondi**, quindi circa 7 minuti e mezzo per notte.
- Ogni ora la campana del campanile di Santa Brina batte i rintocchi: è l'orologio diegetico.
- All'inizio della notte chiama **Marzio** alla radio VHF (l'equivalente del Phone Guy): spiega le regole, scherza, e lascia scappare dettagli che non dovrebbe.
- Alle 06:00: se il secchio contiene almeno la quota la notte è superata (alba, campane, gabbiani). Se no, **la Madre si sveglia** (finale negativo della notte).

## 5. Pesca

1. **Lancio** (`Spazio` o clic sulla canna): la lenza entra in acqua.
2. **Attesa**: il tempo prima dell'abboccata dipende dalla lampara.
3. **Abboccata**: suona il **campanellino** in punta alla canna (come nella pesca notturna vera) e la punta si piega. Hai circa 2,5 s per ferrare, altrimenti il pesce si mangia l'esca.
4. **Recupero**: tieni premuto per riavvolgere. La tensione sale mentre recuperi e quando il pesce strattona; se supera il massimo **la lenza si spezza**, se scende a zero **il pesce si slama**. Mentre recuperi lo sguardo resta bloccato sulla canna.
5. **Cattura**: il pesce finisce nel secchio. Ogni tanto, al posto del pesce, sale **un oggetto**: sono i frammenti di lore (vedi `LORE.md`).

Specie (cosmetiche nella Notte 1): acciuga, sgombro, orata, spigola, triglia.

## 6. La lampara

| Livello | Abboccate | Attività dei Piccoli | Visibilità |
|---|---|---|---|
| 0 Spenta | ×0,45 (lentissime) | ×0,6 | solo luna: dei Piccoli vedi gli occhi |
| 1 Bassa | ×1 | ×1 | normale |
| 2 Alta | ×1,8 | ×1,6 | piena, si vedono i pesci attirati sotto la superficie |

## 7. I Piccoli del Fondo (Notte 1)

> **Bozza.** Nomi, specie, aspetto e carattere dei Piccoli sono ancora da decidere insieme. Restano fermi solo i tre ruoli di gioco: uno da sfamare, uno da fissare, uno da cui nascondersi.

### Pappo — prua — *SFAMARE*
Rospo-neonato grosso e paffuto, bavaglino ricamato con un pesciolino, due dentini davanti e molti altri dietro.
- **Sale** (occhi gialli e bolle davanti alla prua, gorgoglio affamato) → **si arrampica** (manine sul bordo di prua, *flop* bagnato) → **pretende** (seduto sulla prua a bocca aperta).
- Gli lanci un pesce dal secchio → lo mangia felice, applaude e torna in acqua. Puoi anche lanciarglielo prima, mentre sale.
- Se non riceve il pesce in tempo → **jumpscare**. Il telone non serve: Pappo sente l'odore.
- Lezione: tieni sempre almeno un pesce nel secchio.

### Lulù — fianchi — *GUARDARE*
Axolotl-bambina rosa pallido, branchie a ventaglio, occhi neri enormi, un ciuccio appeso al collo con un nastrino.
- **Bussa** sullo scafo (*toc toc*) a sinistra o a destra → **spunta** dal bordo con le manine aggrappate.
- Devi **guardarla** (tenerla al centro della visuale) finché non si sente vista abbastanza: ride, fa una bolla e si lascia scivolare in acqua.
- Se la ignori si offende: piange e **dondola la barca**, sempre più forte (la visuale si inclina, entra acqua). Se continui a ignorarla **affonda la barca**.

### Cucù — poppa — *NASCONDERSI*
Pesce-rana neonato che cammina sulle pinne, una lucina da esca in fronte (la usa per cercarti) e un berrettino rosso di lana col pon-pon.
- Gioca a nascondino: **conta** con il verso di un orologio a cucù (*cu-cù… cu-cù…*), da dietro la barca.
- Al quinto cucù **sale a bordo**. Devi già essere **sotto il telone**.
- Sotto il telone vedi la sua lucina che fruga attraverso la tela e senti i passi bagnati. Se esci prima che se ne vada (cucù triste e tonfo in acqua) → **"Cucù! Trovato!"** → jumpscare.

### Regia (director)
- Prime apparizioni a orario fisso per insegnare le regole: Pappo verso l'01:00, Lulù verso le 02:00, Cucù verso le 03:00.
- Dopo, la regia sceglie gli eventi in base al livello della lampara e a un budget di tensione. Nella Notte 1 non sovrappone mai la perquisizione di Cucù a Lulù sul bordo.

## 8. Sonar

Il sonar (lo schermo sulla console di poppa, o `Tab` per vederlo a tutto schermo con effetto CRT) mostra un cerchio con la barca al centro. Il fascio gira e *pinga*: puntini piccoli = pesci, ombre grandi = Piccoli che salgono dal fondo, con direzione e profondità. È la "telecamera" di LAMPARA: anticipa le minacce, ma mentre lo guardi non vedi la barca.

## 9. Morte e sconfitta

- Jumpscare (sequenza renderizzata + urlo), poi statica e **schermata di game over** dedicata a ogni Piccolo (es. il tuo berretto che galleggia mentre Lulù ci gioca).
- Quota mancata alle 6:00: l'acqua si fa liscia come uno specchio e sotto la barca si apre **un occhio**.

## 10. Flusso dei menu

Avvertenza (jumpscare, luci, cuffie consigliate) → Titolo (render animato, ninna nanna al carillon) → Nuova partita / Continua / Extra (Il Diario: frammenti di lore trovati) / Opzioni / Esci → Intro notte ("Notte 1 · 00:00 · Quota 8") → Gioco → Alba / Game over.

## 11. Opzioni e accessibilità

Volume generale/musica/effetti, lingua (italiano, inglese), luminosità, schermo intero, sottotitoli, sensibilità della rotazione, **riduci flash e scosse**, indicatori visivi dei suoni (per chi gioca senza audio).

## 12. Direzione artistica

- **3D pre-renderizzato** (Blender/Cycles) con passi di luce separati, ricomposti in tempo reale: la lampara può tremolare, abbassarsi, spegnersi.
- Palette: blu-petrolio della notte, ambra della lampara, verde-giallo e rosa degli occhi dei Piccoli.
- Ambientazione mediterranea: gozzo di legno dipinto con l'occhio apotropaico a prua, faraglioni, paese arroccato con il campanile, faro con il fascio che gira, luna tra le nuvole, bonaccia e banchi di nebbia.
- Post-processing: bloom, grana della pellicola, vignettatura, leggera aberrazione cromatica.

## 13. Audio

- Ambiente: sciabordio sullo scafo, legno che scricchiola, vento, campana delle ore, sirena lontana, ronzio della lampara.
- Pesca: lancio, plop, campanellino, cricchetto del mulinello, tensione della lenza, schiocco, pesce nel secchio.
- Ogni Piccolo ha una firma sonora riconoscibile e **spazializzata** (HRTF): si capisce da che lato arriva, meglio in cuffia.
- Musica: ninna nanna della Madre al carillon (menu), rintocchi e gabbiani (alba).

## 14. Piattaforme e tecnologia

TypeScript + WebGL2 (renderer proprio), interfaccia in HTML/CSS, Web Audio. Desktop con Electron (Windows, Linux/Steam Deck, macOS), Steamworks in un secondo momento (achievement, salvataggi cloud). Tutti gli asset sono generati da script nel repository (`tools/`).

## 15. Oltre la Notte 1 (roadmap)

| Notte | Novità |
|---|---|
| 2 | Batteria: lampara e sonar consumano. |
| 3 | **Bolla** (pesce palla): si gonfia se cambi luce mentre è vicino. |
| 4 | **I Gemelli**: girini che tirano la lenza; abboccate finte. |
| 5 | **La Madre**: il sonar mostra un'ombra enorme; immobilità totale. |
| 6 | Notte extra con livelli di aggressività personalizzabili. |
