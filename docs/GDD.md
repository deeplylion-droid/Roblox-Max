# LAMPARA — Game Design Document

> *Raggiungi la quota prima delle sei. Dai da mangiare ai ragazzi. Non farti trovare.*

Versione 0.1 — obiettivo del primo traguardo: **Notte 1 completa e rifinita** (vertical slice).

## 1. Il gioco in una frase

Horror in prima persona a inquadratura fissa (alla *Five Nights at Freddy's*): sei il pescatore di turno sopra **il Pozzo**, la voragine al centro della baia di **Santa Brina**. Devi riempire il secchio con la **quota di pesci** entro le 6:00, mentre i figli della Madre, i bambini spariti nel 1997 a **Splashland**, il parco acquatico abbandonato alle tue spalle, salgono a bordo. Ognuno vuole qualcosa di diverso.

## 2. Pilastri

1. **Lavorare mentre si ha paura.** In FNAF sopravvivi e basta; qui devi anche *produrre*. Ogni secondo passato a difenderti è un secondo in cui non peschi.
2. **Il pesce è insieme obiettivo e moneta.** Lo stesso pesce che serve alla quota è quello che devi lanciare a Gulpy per non farti mangiare.
3. **La lampara è un'avidità regolabile.** Più luce = più pesci che abboccano, ma anche più creature che salgono.
4. **Tre minacce, tre direzioni, tre risposte.** Prua → *sfamare*. Fianchi → *guardare*. Poppa → *nascondersi*. Leggibile al primo sguardo, difficile quando si sovrappongono.
5. **Family friendly distorto.** Creature lunghe e sbagliate che portano ancora i colori allegri di un parco acquatico per bambini: salvagenti, braccioli, giocattoli luminosi, la mascotte sorridente.

## 3. Visuale e controlli

- Sei seduto al centro del gozzo. La visuale è un **panorama pre-renderizzato a 360°** proiettato in prospettiva: puoi ruotare liberamente lo sguardo (bordi dello schermo col mouse, `A`/`D`, frecce) e voltarti di scatto (`S` o pulsante in basso).
- La barca **dondola** davvero rispetto all'orizzonte: il mondo e lo scafo sono strati separati.
- Interazioni col mouse (clic sugli oggetti) o tasti:

| Azione | Mouse | Tastiera |
|---|---|---|
| Ruotare lo sguardo | bordi dello schermo | `A` `D` / `←` `→` |
| Voltarsi (prua ↔ poppa) | barra in basso | `S` / `↓` |
| Lanciare / ferrare / recuperare la lenza | clic (tenere premuto) sulla canna | `Spazio` |
| Lanciare un pesce a Gulpy | clic sul secchio | `F` |
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

| Livello | Abboccate | Attività delle creature | Visibilità |
|---|---|---|---|
| 0 Spenta | ×0,45 (lentissime) | ×0,6 | solo luna: delle creature vedi solo gli occhi |
| 1 Bassa | ×1 | ×1 | normale |
| 2 Alta | ×1,8 | ×1,6 | piena, si vedono i pesci attirati sotto la superficie |

## 7. Le creature (Notte 1)

Sono i bambini spariti a **Splashland** nel 1997, presi e trasformati dalla Madre (vedi `LORE.md`). Non sono cuccioli e non sono carini: sono **allungati, magri, sproporzionati** (riferimento: SCP-096 "Shy Guy"), pelle grigio-pallida e bagnata, occhi bianchi senza pigmento, collo e arti troppo lunghi, dita palmate lunghissime, branchie sul collo. Il tocco "family friendly" c'è ma è distorto fino all'orrore, come il bavaglino di Chica in FNAF: ognuno porta ancora addosso qualcosa del parco. I nomi vengono da nomi inglesi di pesci, accorciati come diminutivi da bambino.

> Il design visivo si definisce insieme: prima le sagome per confrontare le proporzioni, poi la modellazione.

### Gulpy — prua — *SFAMARE*
Ispirato al pesce pellicano (*gulper eel*): tutto bocca su un corpo lunghissimo. Ha un salvagente giallo a paperella incastrato sul collo, che ormai stringe la carne.
- **Sale** (si avvicina in superficie davanti alla prua, si sentono lo sciabordio e il suo verso affamato) → **si sporge** (le mani enormi sul bordo di prua, si piega sopra la barca) → **pretende** (la mascella si sgancia fino al petto, aspetta).
- Gli lanci un pesce dal secchio → lo inghiotte e torna giù. Puoi lanciarglielo anche prima, mentre sale.
- Se non riceve il pesce in tempo → **jumpscare**. Il telone non serve: Gulpy sente l'odore.
- Lezione: tieni sempre almeno un pesce nel secchio.

### Molly — fianchi — *FISSARE*
Ispirata al barreleye (testa trasparente, gli occhi dentro che ruotano e ti seguono) e alla *mola*, il pesce luna. Porta i braccioli gonfiabili su braccia lunghe due metri. Da bambina gridava "Guardami!" dal trampolino.
- **Bussa** sullo scafo a sinistra o a destra → **si alza** lungo la fiancata e piega il collo sopra il bordo, la faccia a mezzo metro dalla tua.
- Devi **guardarla** (tenerla al centro della visuale) finché non è soddisfatta: allora si lascia scivolare in acqua.
- Se la ignori si offende e **dondola la barca**, sempre più forte (la visuale si inclina, entra acqua). Se continui a ignorarla **trascina giù la barca**.

### Hatch — poppa — *NASCONDERSI*
Ispirato alla rana pescatrice e all'*hatchetfish*: si muove a quattro zampe con arti lunghissimi, quasi un ragno. La sua esca è il giocattolo luminoso del negozio del parco, che gli pende dalla fronte: lo usa per cercarti.
- Gioca a nascondino: **conta fino a dieci** ad alta voce, da dietro la barca ("…eight, nine, ten… ready or not, here I come!", localizzato).
- Finita la conta **sale a bordo**. Devi già essere **sotto il telone**.
- Sotto il telone vedi la luce del giocattolo che fruga attraverso la tela e senti i passi bagnati. Se esci prima che torni in acqua → jumpscare.

### Regia (director)
- Prime apparizioni a orario fisso per insegnare le regole: Gulpy verso l'01:00, Molly verso le 02:00, Hatch verso le 03:00.
- Dopo, la regia sceglie gli eventi in base al livello della lampara e a un budget di tensione. Nella Notte 1 Hatch non si sovrappone mai a Molly né a Gulpy.

## 8. Sonar

Il sonar (lo schermo sulla console di poppa, o `Tab` per vederlo a tutto schermo con effetto CRT) mostra un cerchio con la barca al centro. Il fascio gira e *pinga*: puntini piccoli = pesci, ombre grandi = creature che salgono dal fondo, con direzione e profondità. È la "telecamera" di LAMPARA: anticipa le minacce, ma mentre lo guardi non vedi la barca.

## 9. Morte e sconfitta

- Jumpscare (sequenza renderizzata + urlo), poi statica e **schermata di game over** dedicata a ogni creatura.
- Quota mancata alle 6:00: l'acqua si fa liscia come uno specchio e sotto la barca si apre **un occhio**.

## 10. Flusso dei menu

Avvertenza (jumpscare, luci, cuffie consigliate) → Titolo (render animato, ninna nanna al carillon) → Nuova partita / Continua / Extra (Il Diario: frammenti di lore trovati) / Opzioni / Esci → Intro notte ("Notte 1 · 00:00 · Quota 8") → Gioco → Alba / Game over.

## 11. Opzioni e accessibilità

Volume generale/musica/effetti, lingua (italiano, inglese), luminosità, schermo intero, sottotitoli, sensibilità della rotazione, **riduci flash e scosse**, indicatori visivi dei suoni (per chi gioca senza audio).

## 12. Direzione artistica

- **3D pre-renderizzato** (Blender/Cycles) con passi di luce separati, ricomposti in tempo reale: la lampara può tremolare, abbassarsi, spegnersi.
- Palette: blu-petrolio della notte, ambra della lampara; i colori "allegri" sbiaditi di Splashland (giallo paperella, fucsia, turchese piscina) come unica nota stonata.
- **Un orizzonte pieno di luoghi**, come l'ufficio di FNAF pieno di oggetti di scena:
  - *davanti*: il paese col campanile, il relitto di un peschereccio con la prua fuori dall'acqua, una boa con la campana e la luce verde che lampeggia, il faro col fascio che gira;
  - *a destra*: un albergo abbandonato sulla scogliera con una sola finestra accesa, un traliccio radio con la luce rossa;
  - *alle spalle*: **Splashland** con la statua di Mama Marina, gli scivoli, l'insegna al neon che sfarfalla, le luci accese della Deep End e la ruota panoramica ferma sul pontile;
  - *a sinistra*: i faraglioni all'imbocco della baia, un'edicola votiva su uno scoglio con un lume acceso, le gabbie di un allevamento ittico.
- **Una barca piena di oggetti**: lanterna arrugginita, borraccia ammaccata, una bambola di legno seduta sul banco che ti guarda, una paperella di gomma del parco, un barattolo con un occhio che galleggia, occhialini da piscina appesi a un chiodo, un rosario di conchiglie sul palo della lampara, tacche incise sul banco a contare le notti, una campanella legata a poppa, una scatola di latta con mozziconi di candela, una statuina di Mama Marina sulla console.
- Post-processing: bloom, grana della pellicola, vignettatura, leggera aberrazione cromatica.

## 13. Audio

- Ambiente: sciabordio sullo scafo, legno che scricchiola, vento, campana delle ore, sirena lontana, ronzio della lampara.
- Pesca: lancio, plop, campanellino, cricchetto del mulinello, tensione della lenza, schiocco, pesce nel secchio.
- Ogni creatura ha una firma sonora riconoscibile e **spazializzata** (HRTF): si capisce da che lato arriva, meglio in cuffia.
- Musica: ninna nanna della Madre al carillon (menu), rintocchi e gabbiani (alba).

## 14. Piattaforme e tecnologia

TypeScript + WebGL2 (renderer proprio), interfaccia in HTML/CSS, Web Audio. Desktop con Electron (Windows, Linux/Steam Deck, macOS), Steamworks in un secondo momento (achievement, salvataggi cloud). Tutti gli asset sono generati da script nel repository (`tools/`).

## 15. Oltre la Notte 1 (roadmap)

| Notte | Novità |
|---|---|
| 2 | Batteria: lampara e sonar consumano. |
| 3 | Nuova creatura (da definire insieme). |
| 4 | Nuova creatura che tira la lenza: abboccate finte (da definire insieme). |
| 5 | **La Madre**: il sonar mostra un'ombra enorme; immobilità totale. |
| 6 | Notte extra con livelli di aggressività personalizzabili. |
