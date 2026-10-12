# Le notti e i mostri nuovi

> **Deciso il 10 ottobre**: sette mostri in tutto, uno nuovo per notte (Robin, Archie, Lampy, Fangy, in
> quest'ordine); la Madre è il finale della notte 6; nelle notti avanzate tornano tutti i mostri già visti
> e la regia decide quanti insieme; la batteria arriva con Robin nella notte 2.
> **Sagome scelte**: Robin **A «Granchio»**, Archie **C «Periscopio»**, Lampy **C «Sanguisuga»** (ma più
> grosso), Fangy **B «Mastino»** (`docs/concept/*_sagome.png`). La batteria è approvata così; il segnale di
> Lampy è **sia il ritmo perfetto sia la risatina**.
> **Teste scelte** (10 ottobre): Robin **B «Baffi»**, Archie **A «Serpente»** (rifatto come serpente di mare
> con la trombetta da festa, approvata), Lampy **B «Bacio»**, Fangy **A «Sciabola»**
> (`docs/concept/*_dettagli_bozza.png`). Colori approvati.

## Più paura (decisioni dell'11 ottobre sera)

Dall'utente: «rispetto a FNAF il nostro gioco risulta meno pauroso e ansiogeno». Le proposte dell'utente, con le scelte
del questionario:

- **Il sonar non avvisa più dei mostri.** Lo schermo resta acceso, col fascio che gira e i pesci, ma niente ombre né bip
  d'avviso: per sapere chi arriva ci sono solo i suoni. Servirà solo nella notte della Madre, perché suonerà per lei.
  **Nessun ribilanciamento** (il bot non ha mai usato il sonar). *Fatto l'11 ottobre sera.*
- **Il binocolo non consuma più la batteria.** Era un difetto: per Molly il binocolo vale come il sonar aperto (non
  guardi la barca), e lo stesso segnale faceva anche consumare il sonar, circa il 7,5% di batteria al minuto.
  *Corretto l'11 ottobre sera.*
- **La luce si regola anche da sotto il telone** (Q, E e rotella). *Fatto l'11 ottobre sera.*
- **«Lampara» diventa «luce»** in tutti i testi del gioco («light» in inglese). Nei documenti e nel codice il nome
  resta. *Fatto l'11 ottobre sera.*
- **Jumpscare della quota mancata**: alle sei senza la quota, la **Madre vista solo in parte**. Scelto **l'occhio**
  che sale da sotto la barca e ti guarda attraverso l'acqua (11 ottobre sera; l'altra proposta era la mano enorme che
  afferra la barca). La Madre intera resta per la notte 6. **Fotogrammi finali fatti** (12 ottobre): otto
  fotogrammi 1920×1080 a 10 al secondo, 96 campioni (`tools/render/quota.py`, voce `jumpscares.quota` in
  `overlays.json`, tavola `docs/concept/jumpscare/js_quota_finale_fotogrammi.jpg`). Il motore lo fa partire alle sei
  quando manca la quota, al posto delle campane e della Madre che si sveglia (che restano se i fotogrammi mancano).
  Il testo c'è già: «Alle sei il secchio non era pieno. Stanotte la Madre si prenderà un altro bambino.»
- **Atmosfera più buia, con foschia e nebbia «ma ben fatte»**: nebbia volumetrica renderizzata in Blender e
  illuminata dalla luce della barca (un alone attorno alla barca, oltre il buio), la scena più buia, la foschia
  bassa sull'acqua; devono restare leggibili le facce dei mostri e i posti del binocolo. Prima le immagini di prova.
- **Il nostro Foxy**: un mostro nuovo, **l'animatore di Splashland annegato dentro il costume marcito della
  mascotte di Mama Marina** (dalla bocca del costume si vede la sua faccia), «molto brutto e horror». Non è uno dei
  sette bambini. Arriva **dalla notte 2**. Sta in uno o due dei posti che si guardano col binocolo: ogni volta che
  lo guardi il suo tempo riparte; se lo trascuri, quando alzi il binocolo il posto è vuoto, poi salta sulla barca e
  c'è il jumpscare immediato. Il binocolo diventa uno strumento vero (finora era un easter egg). Prima la tavola
  con le varianti, i nomi e i posti, da approvare.

### Più paura nel gioco (12 ottobre, ramo `claude/paura`; le idee sono approvate, i dettagli da approvare)

Dal questionario del 12 ottobre l'utente ha scelto tutte e quattro le idee. Sono solo nel presentatore: la
simulazione, le regole e il bilanciamento non cambiano.

- **Le creature vive** (`src/app/vivi.ts`): mentre aspettano in posa **respirano** (lo strato si allunga e si accorcia
  attorno alla base, dallo 0,4 all'1,1% dell'altezza, da 0,18 a 0,36 respiri al secondo; la Madre più piano). Quando
  ne guardi una che è tutta fuori da almeno 1,2 s, ogni tanto **la testa scatta**: una rotazione di 3-4° sopra il
  collo in 70 ms, ferma un quarto di secondo con un tremito, poi torna piano; una ogni 6-13 s, con lo schiocco della
  cartilagine bagnata (`vivo_scatto_*`). Chi è appena uscito dall'acqua **gocciola** (`goccia_*`, una ogni 0,8-2,5 s).
  Robin e la Madre non scattano. Nel renderer gli strati hanno `uWarp` e `uNeck` (le toppe seguono la loro posa; il
  bordo del riquadro si sfuma di 14 px mentre si deforma).
- **Il cuore del pescatore** (`src/app/paura.ts`): un solo numero, **il pericolo** (0..1, dagli stati dei mostri in
  `dangerNow()` di `night.ts`; per esempio Gulpy che pretende 0,55-0,9, Molly nei capricci 0,8-0,92, Hatch che cerca
  0,95, Soggy che corre verso la barca 0,96, la Madre che passa sotto 1; a batteria morta fino a 0,9), che sale in
  fretta e scende piano. Dallo 0,15 in su il **battito**, da 66 a 132 al minuto e sempre più forte; il **respiro** si
  fa corto; quando devi stare immobile (la Madre che passa sotto, Hatch che cerca) **trattieni il fiato**, e quando
  finisce lo butti fuori. Sono suoni «dentro la testa» (bus `body`): sotto il telone non si ovattano, anzi il cuore si
  sente di più. Sostituisce il vecchio battito.
- **La tensione nella musica**: due fondi in loop (`tensione_bassa`, 24 s; `tensione_alta`, 16 s) che entrano col
  pericolo medio e con quello forte; **sopra 0,92, un attimo prima del peggio, la musica sparisce di colpo** e resta
  solo il cuore.
- **I falsi allarmi** (dalla notte 2): una o due volte per notte, solo se è tutto calmo da almeno 20 s e sei fuori
  dal telone, senza sonar né binocolo: **i colpi di Molly sullo scafo**, da un lato, senza nessuno (6 volte su 10), o
  **un tonfo in acqua dietro di te** (sottotitolo «un tonfo in acqua, dietro di te» / «a splash in the water, behind
  you»). Il cuore sussulta e torna giù piano. Il primo fra la prima ora e le due passate, il secondo almeno 1,2 ore
  dopo.
- Le anteprime (la scena col suono e Gulpy vivo) le ho mandate in chat il 12 ottobre. **Da fare**: la sagoma nella
  nebbia (serve un render, dopo l'atmosfera).

### Il Foxy nel gioco (logica, notte fra l'11 e il 12 ottobre; branch `claude/foxy-gioco`)

> **I render sono arrivati** (12 ottobre: il modello, le viste del binocolo di scivoli e relitto, il jumpscare, sotto);
> dove manca una vista col Foxy restano i **due occhi rossi** nel suo posto. **I suoni** (12 ottobre, da
> approvare; `docs/AUDIO.md`, «L'animatore») sono i file `foxy_near` (si sporge), `foxy_leave` (lascia il posto e corre
> verso la barca, finisce sul salto) e `js_foxy` (l'abbraccio); senza i file restano i ripieghi. **Da approvare**: i testi (sotto) e i numeri.
>
> **La variante** (notte fra l'11 e il 12 ottobre, scelta da me col via libera dell'utente; tavola
> `docs/concept/foxy_varianti.jpg` sul ramo `claude/foxy`): la **B «Fradicio»**, il costume gonfio d'acqua che cede,
> curvo, la testa crollata di lato, dalle pinne sfondate le sue mani, la faccia gonfia spinta fuori dalla bocca e un
> occhio da cartone che penzola. Le altre erano la A «Pupazzo» (il costume intero, lui in fondo al sorriso) e la C
> «Sventrato» (la testa spaccata, lui scheletrico che esce fino al petto). **Il nome è Soggy** («fradicio»), scelto
> dall'utente il 12 ottobre fra le tre proposte (le altre erano Grinny, il sorriso del costume, e Marty, il nome sul
> cartellino dell'animatore). Nel codice e nei file resta `foxy`.
>
> **Approvato dall'utente il 12 ottobre** (questionario del mattino): la variante B, le regole e i numeri, i testi, i
> suoni e l'anteprima del jumpscare; **c'è anche nella notte extra**. **Da cambiare**: nel binocolo lo vuole **più
> grande ed evidente, a discapito del realismo della distanza** (le viste si rifanno con l'animatore ingrandito).
>
> **Le viste del binocolo** col Foxy: per ogni posto due immagini con la stessa inquadratura di quella vuota (lui fermo,
> lui più vicino), in `overlays.json` → `binocular.places[].foxy` (`bino_<posto>_foxy0.webp`, `_foxy1.webp`). Il motore
> le mostra al posto della vista vuota secondo lo stadio; finché non ci sono restano gli occhi rossi.
>
> **Le viste definitive** (notte fra l'11 e il 12 ottobre, sessione del Foxy, ramo `claude/foxy`): scivoli e relitto,
> vuoto, fermo e più vicino, rese con la nebbia nuova (ATMOSFERA=1). Agli scivoli lui sta in cima alla torre sotto il
> tetto rosso, poi ai piedi della torre davanti agli scivoli; al relitto sulla tuga, poi in acqua fino alla vita davanti
> al relitto. Le tre immagini di un posto combaciano fuori dalla sua sagoma; le ho ricodificate con perdita (qualità 90,
> da 2,2 MB a mezzo MB l'una): lui cambia stadio solo quando non lo guardi, quindi le minime differenze della
> compressione non si vedono. Siccome la nebbia nuova è già nel render, in `overlays.json` questi due posti hanno
> `fog: 0`: il motore non ci aggiunge la sua (le altre viste la prendono ancora, finché non si rifanno con l'atmosfera).
>
> **Il jumpscare definitivo** (12 ottobre, sessione del Foxy, ramo `claude/foxy`, commit 9549a04; tavola
> `docs/concept/jumpscare/js_foxy_finale_fotogrammi.jpg`): otto fotogrammi a 1920×1080 (`js_foxy_00..07.webp`,
> `overlays.json` → `jumpscares.foxy`), con le correzioni chieste sull'anteprima: la camera guarda il bordo a prua sulla
> dritta e lui sale da sotto il capodibanda contro la foschia (fotogrammi 0-3), poi ti viene addosso con la faccia al
> centro, luce calda solo sulla faccia, l'occhio da cartone che dondola di lato e le mani ossute che salgono dagli angoli
> in basso (4-7). La faccia da annegato: pelle macerata, chiazze grigio-viola, labbra gonfie e livide.
> **Più vicino** (richiesta dell'utente del 12 ottobre, «così che ti arriva proprio in faccia, alla FNAF»): nel gioco i
> fotogrammi si ingrandiscono del 20% attorno al centro, senza rifare il render (`JS_ZOOM` in `src/app/night.ts`).

- **Dove sta**: in uno di due posti del binocolo, la **torre degli scivoli** alle spalle (−167°, 460 m) e il
  **relitto** davanti alla prua (14°, 170 m), da dove salta in acqua e arriva alla barca. Li ha proposti la sessione
  del Foxy con la tavola e li ho scelti io stanotte (l'utente mi ha dato il via): l'albergo Miramare, a 885 m, lo
  avrebbe fatto di pochi pixel. Uno davanti e uno dietro: il relitto si controlla senza voltarsi, per gli scivoli
  bisogna girarsi.
- **Come si muove**: ogni volta che lo guardi col binocolo il suo tempo riparte da zero. Trascurato, dopo `lean`
  secondi **si sporge** verso di te; dopo `leave` secondi **lascia il posto** (il posto è vuoto: sta arrivando) e dopo
  `run` secondi **salta sulla barca**: jumpscare immediato. Si muove solo quando non lo guardi: guardato mentre è
  sporto resta sporto, e torna fermo al suo posto appena abbassi il binocolo; a volte (`swap`) torna **nell'altro
  posto**, e allora va cercato. **La prima volta**, finché non lo trovi, aspetta 1,6 volte di più (si impara dov'è).
- **Numeri** (secondi; una notte dura 450 s):

  | Notte | compare | si sporge | lascia il posto | salta | cambia posto |
  |---|---|---|---|---|---|
  | 2 | 01:00 circa | 46 | 85 | 3,5 | 15% |
  | 3 | 00:40 circa | 44 | 82 | 3,2 | 20% |
  | 4 | 00:35 circa | 40 | 72 | 3 | 30% |
  | 5 | 00:30 circa | 36 | 66 | 3 | 35% |

- **Il bot** lo controlla quando tocca e non c'è niente di più urgente (non mentre recupera un pesce o ferra): si volta
  (di scatto se il posto è alle spalle), alza il binocolo sul posto dove l'ha visto l'ultima volta, e se lì non c'è
  guarda nell'altro. Ogni quanto
  dipende dall'abilità, in frazioni di `leave` (esperto 0,45-0,6; medio 0,5-0,75; maldestro 0,55-0,9); visto sporto,
  il controllo dopo arriva prima. Ogni controllo costa tempo di pesca: per questo cresce anche la quota mancata.
- **Bilanciamento: il recupero più veloce** (indicazione dell'utente, 11 ottobre sera: «se devi bilanciare, riduci il
  tempo necessario per tirare su i pesci»). Il tempo passato col binocolo si ripaga tirando su i pesci più in fretta:
  `reelMul` per notte (2: ×1,10; 3: ×1,06; 4: ×1,15; 5: ×1,08). Le regole del Foxy e le quote non cambiano.
- **Simulazioni** (esperto / medio / maldestro; 200 partite le prime due colonne, 400 le ultime due):

  | Notte | prima del Foxy | col Foxy | col Foxy e il recupero più veloce | idem, col relitto al posto dell'albergo |
  |---|---|---|---|---|
  | 2 | 100 / 91 / 64,5% | 99 / 78,5 / 45% | 100 / 94 / 64% | 99,8 / 94 / 66,5% |
  | 3 | 100 / 76 / 46,5% | 99,5 / 69,5 / 31% | 100 / 79 / 44% | 100 / 80 / 45% |
  | 4 | 96,5 / 74 / 51% | 94 / 63,5 / 31% | 99 / 74,5 / 51% | 98,5 / 78 / 51% |
  | 5 | 95 / 76,5 / 53% | 93 / 73 / 38% | 97,5 / 79 / 50% | 98 / 80,5 / 52,5% |

  Le percentuali tornano quelle di prima: il Foxy aggiunge tensione, non sconfitte. Chi si dimentica di lui muore
  per lui (il maldestro: dal 5,5% delle partite nella notte 2 al 12% nella 5) invece che per la quota. Col relitto
  davanti i numeri restano quelli: il costo vero di un controllo è il tempo col binocolo alzato, non il voltarsi.
- **Testi** (da approvare): suggerimento «Col binocolo (B): non perderlo di vista» finché non lo trovi la prima volta,
  «Il posto è vuoto» se lo guardi quando se n'è andato; didascalie «laggiù, qualcosa si sporge», «qualcosa corre
  sull'acqua»; game over **«Lo spettacolo finiva sempre con un abbraccio.»** (faceva lo spettacolo di Mama Marina).
- **Il binocolo** smette di essere un easter egg: dalla notte 2 serve per sopravvivere (non si alza sotto il telone,
  col sonar aperto o con un pesce in canna; mentre lo guardi non vedi la barca, e Molly non si sente guardata).

## Il piano delle notti

| Notte | Novità |
|---|---|
| 1 | **Gulpy**, **Molly**, **Hatch**: sfamare, guardare, nascondersi. |
| 2 | **Robin**: scacciarlo con la luce. Arriva **la batteria**: lampara e sonar consumano. |
| 3 | **Archie**: spegnere la luce in tempo. |
| 4 | **Lampy**: non ferrare le abboccate finte. |
| 5 | **Fangy**: stare zitti. Va contro tutto il resto, per questo arriva per ultimo. |
| 6 | **La Madre**, il finale: tutti e sette i mostri, il sonar mostra un'ombra enorme, immobilità totale. |
| 7 | Notte extra con i livelli di aggressività da scegliere. |

Come per la prima notte, i mostri sono bambini presi dalla Madre: le loro foto stanno sull'edicola. Ognuno
ha un pesce vero da cui viene, una cosa del parco addosso e un'abitudine di quando era bambino diventata
la sua regola. Sono allungati, magri e sproporzionati come Gulpy, Molly e Hatch, bagnati e coperti della
stessa melma. **Non parlano** (l'unica eccezione resta la conta di Hatch).

**Colori** (richiesta dell'utente, 10 ottobre: «i mostri tutti dello stesso colore non piacciono, dobbiamo
differenziarli come su FNAF dove ognuno ha un colore»): Gulpy e Molly restano grigi come sono; **Hatch diventa
arancione** (scelto il 10 ottobre, tra arancio e verde: `docs/concept/hatch_colori.jpg`); i quattro nuovi hanno
ognuno un colore netto. Confermato poco dopo: «un colore diverso ciascuno: rosso, giallo
eccetera, un po' come gli animatronics», quindi tinte sature e iconiche, riconoscibili anche al buio.
**Approvati** sulle tavole delle teste (anche la montatura gialla degli occhialini di Fangy):

| Mostro | Colore | Perché |
|---|---|---|
| Robin | **rosso corallo**, pinne a ventaglio azzurro-turchese | la gallinella vera è rossa con le «ali» azzurre |
| Archie | **giallo limone a fasce nere**, la pistola arancione | le bande nere del pesce arciere |
| Lampy | **viola-magenta**, la cuffia a fiori rosa e bianca | pelle da sanguisuga; stacca dal mare blu-verde |
| Fangy | **blu notte quasi nero**, lucine azzurre lungo il ventre | i pesci degli abissi; in acqua si vedono solo le luci |

## Notte 2 — La batteria

- Una **batteria d'auto** con un voltmetro ad ago. Per la nota dell'utente (niente oggetti nuovi dove si
  vedono i jumpscare già renderizzati) non sta più sul pagliolo ma **sul banco di prua, a destra del
  secchio** (circa 26° a destra), con i cavi che corrono lungo lo scafo fino al palo della lampara e il
  voltmetro su una staffa girato verso il pescatore: la vedi guardando il secchio. Niente barre sullo
  schermo. **Approvata** il 10 ottobre (`docs/concept/batteria_anteprima.jpg` e `batteria_vicino.jpg`).
- **Nel gioco** l'ago lo disegna il motore sopra il quadrante renderizzato: nel rosso esattamente quando la
  carica scende sotto la soglia bassa (15%), cala un poco con la lampara alta (la batteria sotto sforzo),
  trema appena; a batteria morta batte sul fermo.
- **Il quadrante è retroilluminato** (richiesta dell'utente: «fallo illuminato così è più importante»): una
  lucina ambra dietro la carta, come i cruscotti di una volta. Si legge anche a lampara spenta; quando la
  batteria è quasi scarica cala e trema insieme alla lampara; quando muore si spegne con lei.
- La **lampara** consuma secondo il livello (spenta niente, bassa poco, alta molto); il **sonar** aperto
  consuma un po'. La carica basta per tenere la lampara bassa tutta la notte, non alta. **Più rapida dall'11
  ottobre** (dopo la prova dell'utente: «si consuma troppo lentamente»): bassa tutta la notte, all'alba resta circa un
  quinto della carica; alta dura circa metà notte (`drain: [0, 1/560, 1/240]`, sonar `1/800`); l'ago corre su gran
  parte del quadrante prima del rosso (da 14,6 V a 11,2 V), così si vede calare. Il tasto **E** alza la lampara e dal
  massimo la spegne (gira in tondo); **Q** la abbassa.
- Quando l'ago scende nel rosso la lampara comincia a tremolare.
- **Quando la batteria muore** si spengono lampara e sonar. Dal fondo, piano, sale la ninna nanna della
  Madre (quella del menu, al carillon). Se suonano le sei prima che la canzone finisca, sei salvo; se
  finisce prima, la Madre sale. È il momento di Freddy quando salta la corrente in FNAF, con la nostra
  canzone. Nel gioco la canzone è proprio `mus_title` (64 secondi, quanto il tempo che ti resta): parte
  ovattata e si apre salendo; se finisce, un tonfo enorme sotto la barca, la barca che sobbalza, il tema
  della Madre e il buio. **Approvato**: mentre canta la Madre gli altri mostri scappano e non tornano
  finché la canzone non finisce (come in FNAF quando salta la corrente: resta solo Freddy).
- **Difficoltà approvata** (200 partite simulate per tipo): esperti 100%, medi 81%, maldestri 57%.
- **La scelta di ogni minuto**: la luce attira i pesci (serve per la quota) e scaccia Robin, ma costa. Al
  buio si pesca poco e le creature arrivano più vicine prima che te ne accorga.
- **Quota 10 pesci** (prima notte 8). Gulpy, Molly e Hatch tornano più spesso; Hatch può arrivare mentre
  c'è Molly. **Sotto il telone Molly non ti vede** (11 ottobre, dopo la prova dell'utente: ti uccideva mentre ti
  nascondevi da Hatch): aspetta senza offendersi, e quando esci vuole di nuovo che la guardi.
- La radio spiega la batteria e Robin in poche frasi; due o tre oggetti di lore nuovi da pescare.

### Stato nel gioco (10 ottobre)

La notte 2 si gioca: dal menu con **Continua** dopo aver vinto la prima, con **Notte successiva** alla fine
della prima, o con `?notte=2` nell'indirizzo (prove). Robin ora si vede (strato `robin_secchio`, 10 ottobre): sale dal
mare sul bordo, nella luce trema e si accende di rosso, scacciato scivola giù; prima si sentiva soltanto (suoni provvisori fatti con i file di scena:
zampette, secchio che tintinna, pesce strappato, fuga in acqua) e si vede sul sonar. Il jumpscare (11 ottobre, render
finale messo nel gioco come chiesto, «se ti convince mettilo»; **approvato l'11 ottobre**): a secchio vuoto molla il bordo e ti salta in faccia a
mani vuote, le arcate aggrottate, la mano lunga con le dita aperte; una luce calda dalla parte della lanterna, solo su
di lui, gli prende la faccia mentre arriva (la lampara gli sta alle spalle). L'urlo è ancora quello sintetizzato. I testi della notte 2 (radio, le due morti, sottotitoli, suggerimento, «Batteria morta.»),
accorciati e resi più criptici come chiesto, sono **approvati** (`src/i18n.ts`).

## I quattro mostri nuovi

> **Animazioni sulla barca** (10 ottobre, decise dall'utente): come Gulpy (la mascella lenta), Molly (sbatte gli
> occhi), Hatch (la bocca che conta) e Robin (sbatte gli occhi), **ognuno dei prossimi mostri avrà una piccola
> animazione** quando è in scena: da progettare insieme al modello. Proposte legate a come si gioca ognuno
> (**approvate l'11 ottobre** con i modelli): **Archie** prende fiato nella trombetta, che si srotola a metà e si riavvolge (il
> risucchio che si sente); **Lampy** apre e chiude piano la ventosa, con gli anelli di denti che girano;
> **Fangy** gira la testa di scatto verso ogni rumore e le lucine del ventre si accendono in fila, come un
> respiro (queste si fanno nel motore, senza render).

### Notte 2 · Robin — *SCACCIARLO CON LA LUCE*

- **Sagoma** (scelta): A «Granchio», steso sul bordo come un ragno di mare, le zampe-raggi ad arco, la coda
  in acqua.

- **Da dove viene**: la gallinella (*sea robin*), che cammina sul fondo con le pinne a zampette, e il
  pesce gatto.
- **Dal parco**: una striscia lunghissima di biglietti della sala giochi, avvolta attorno alle braccia.
- **Da bambino**: prendeva le cose degli altri bambini e le nascondeva sotto gli scivoli. Ora **ruba i
  pesci dal secchio**.
- **Come si gioca**: senti il secchio che tintinna e vedi le zampette sul bordo. Devi girarti e
  **puntargli in faccia la lampara al massimo** finché non scappa. Se non lo fai ti porta via pesci (e la
  quota si allontana); se il secchio è vuoto, prende te.
- **Perché funziona**: con la batteria la luce costa; con Robin in giro non puoi risparmiare sempre.
- **Basta la luce** (**deciso dall'utente l'11 ottobre**, dopo la sua prova: «non deve servire guardare Robin per
  mandarlo via, basta avere la luce al massimo»): Robin scappa dopo 2,5 s di **lampara al massimo**, da qualunque parte
  tu guardi (prima serviva anche guardarlo in faccia, entro 20° da lui). Il suggerimento e la radio dicono «lampara al
  massimo».
- **Modello e posa approvati** (10 ottobre; `tools/render/robin.py`, posa `robin_secchio` in
  `scena_creature.py`, anteprime `docs/concept/pose_robin.jpg`, `pose_robin_vicino.jpg`, `robin_vetrina.jpg`):
  steso di traverso sul capodibanda di sinistra verso prua, la faccia (a −38° dall'occhio) girata verso il
  pescatore; il braccio lungo (circa 1,5 m, a tre segmenti) passa sopra il banco e tiene per la coda un pesce
  sopra il secchio; l'altra mano è aggrappata al bordo come Molly; biglietti di Splashland avvolti sulle braccia
  («SPLASHLAND / 1 TICKET / Nº 040217»), la coda in acqua.
- **Nel gioco** (approvato): sale dal mare sul bordo e, scacciato, scivola giù e in fuori. Mentre lo scacci
  trema e si ritrae, la faccia si accende di luce calda e **strizza gli occhi** (la lampara gli sta dietro, da
  sola gli illuminerebbe solo la schiena).

### Notte 3 · Archie — *SPEGNERE LA LUCE*

- **Sagoma** (scelta): C «Periscopio», un collo sottilissimo che sale dritto dall'acqua, la testa in cima
  piegata verso la luce.
- **Rifatto il 10 ottobre** (nota dell'utente sulle teste: «Non mi piace, rifacciamo, la pistola non è bella,
  troviamo un altro sistema: che sia un serpente marino e ti soffia per spegnere»). Prima era il pesce
  arciere con la pistola ad acqua fusa nel braccio.

- **Da dove viene**: il serpente di mare del Mediterraneo (*Ophisurus serpens*), un'anguilla lunghissima e
  sottile col muso appuntito. Giallo a bande nere (colore approvato), come i serpenti di mare veri.
- **Dal parco** (approvato): una trombetta da festa a strisce rosse e bianche, con la piuma in punta, che si
  srotola soffiando; il bocchino è fuso nelle labbra.
- **Da bambino** (approvato): alle feste di compleanno al parco spegneva lui le candeline degli altri bambini.
  Ora **soffia sulla lampara**.
- **Testa** (scelta): A «Serpente», la testa lunga e appuntita del serpente di mare coi denti aguzzi fuori
  dalle labbra, che stringe il bocchino.
- **Come si gioca**: un risucchio lungo, mentre prende fiato: vuole spegnere la tua luce. Devi **spegnere la
  lampara** prima che soffi e restare al buio finché non si rituffa. Se soffia con la lampara accesa il
  vetro della lampara esplode e nel buio Archie ti è addosso: **jumpscare** (nota dell'utente: non deve
  limitarsi a spegnerti la luce).
- **Perché funziona**: è l'opposto di Robin, che con la luce scappa: la lampara diventa una scelta
  continua.
- **Modello e posa** (**approvati l'11 ottobre**; `tools/render/archie.py`, posa `archie_soffia` in
  `scena_creature.py`, anteprime `docs/concept/pose_archie.jpg`, `pose_archie_vicino.jpg`, `archie_vetrina.jpg`):
  sale dal mare a destra della lampara e un po' oltre, a 12° dall'occhio, tra la lampara e la canna: lì nelle altre
  notti non c'è nessuno (Gulpy e Robin stanno a sinistra della prua, Molly sui fianchi, Hatch a poppa, la lenza va
  verso il largo a destra della canna). Il collo, sottilissimo e a bande nere un po' storte (a passo fisso sembrava
  un palo da barbiere), esce dritto da dietro la prua e in cima si piega in avanti; la testa, a 2,4 m sul mare e a
  5 m dal pescatore, guarda giù sul vetro dall'alto, con la trombetta arrotolata sotto il muso e puntata sulla
  lampara. La faccia si vede di tre quarti, l'occhio sinistro ti guarda. La testa è la A rifinita: gli occhi più
  piccoli e affondati sotto un'arcata aggrottata (nella tavola sporgevano, da rana), le labbra col bordo, le zanne
  davanti più lunghe e storte all'indietro, le pieghe sulla gola. È più grande del vero (una volta e mezza) e la
  trombetta è lunga 85 cm, una volta e mezza la testa come quelle vere: così dall'alto arriva al vetro passando sotto
  il cappello, e da dove sei la vedi srotolarsi per quasi dieci gradi. Nel gioco sta nello spazio della barca (si
  muove con lei, così la trombetta resta puntata sulla lampara); lo strato finisce al pelo dell'acqua.
- **Sulla barca** (l'animazione scelta: prende fiato nella trombetta, che si srotola a metà e si riavvolge): le toppe
  `archie_trombetta_mezza` e `archie_trombetta_tutta` (`pose_animate.py`; tavola
  `docs/concept/animazioni/archie_trombetta.jpg`). Tutta distesa è il soffio: la piuma arriva a una decina di
  centimetri dal vetro. Per il risucchio una toppa in più (approvata l'11 ottobre), `archie_fiato`: la gola si gonfia come un
  pallone mentre prende fiato (nel gioco può seguire il risucchio, da 0 a 1). Nelle toppe si vede anche il collo
  dietro la testa e il riquadro sta sulla testa: la spirale che si srotola lascia vuoto il suo posto, e il gioco
  sfuma lo strato principale dove la toppa è vuota, come per le mascelle di Gulpy e Hatch.
- **Jumpscare** (**approvato l'11 ottobre** così com'è, senza la mascella che si apre; `jumpscare.py`, `ATTACKS['archie']`; anteprima
  `docs/concept/jumpscare/js_archie_fotogrammi.jpg`): il vetro è esploso e la lampara è spenta (nella scena non c'è
  più il vetro, la reticella e la lampadina di servizio non fanno luce). Nel buio si vedono solo i suoi occhi che
  brillano, come nel gioco a lampara spenta; la trombetta si è riavvolta di scatto, si stacca dalla lampara e ti
  arriva in faccia di tre quarti, il muso che ti passa accanto a sinistra con le zanne. Lo illuminano la luna alle
  spalle, la lanterna e una luce calda dalla parte della lanterna che tocca solo lui (come per Robin), così la faccia
  esce dal buio man mano che arriva.
- **Render finali** (10 ottobre, approvati l'11): `archie_soffia` con gli occhi nel
  manifest (al buio brillano come quelli degli altri), e le toppe `archie_fiato`, `archie_trombetta_mezza`,
  `archie_trombetta_tutta`, in `public/assets/img` con le chiavi che il gioco già aspetta. Il jumpscare finale è nel
  gioco (11 ottobre, 64 campioni: con la scossa e la grana del nastro non si vede la differenza).
- **Nel gioco** (10 ottobre, notte del lavoro; **approvato l'11 ottobre**: tempi, regole, testi): la notte 3 si gioca (`?notte=3`, o Alt + 3 sul
  titolo nelle build di prova). Archie sale dall'acqua in 3 s (il sonar lo annuncia davanti alla prua), poi il
  risucchio dura 4,5 s: la gola si gonfia, la trombetta resta arrotolata, si sente il fiato al contrario. Se alla
  fine la lampara è accesa (anche bassa) soffia: la trombetta si distende sul vetro, il vetro esplode (la lampara
  non si riaccende più: «Il vetro è rotto.») e un attimo dopo il jumpscare. Se l'hai spenta, la gola si sgonfia in
  un sospiro e aspetta al buio 7 s, l'occhio acceso, prendendo fiato a metà nella trombetta; poi si rituffa. Se la
  riaccendi prima riprende fiato più in fretta (2,2 s). Quando canta la Madre si rituffa anche lui. Robin e Archie
  non vengono mai insieme (vogliono il contrario dalla luce). Quota 11 pesci. Giocatori simulati
  (`npm run sim -- 3 300`): esperto 100%, medio 71%, maldestro 50% (la seconda notte 100/81/58). Suoni provvisori
  sintetizzati (l'acqua che si apre, il risucchio, la trombetta che si sgonfia, il soffio e il vetro, il tuffo):
  la direzione è approvata (11 ottobre), si rifanno come gli altri suoni del gioco.
  La chiamata alla radio: «Terza notte. Undici pesci. / Archie viene per la lampara. / Se lo senti prendere fiato,
  spegni. / E resta al buio finché non va giù. / Buona pesca.» La frase della morte: «Archie ha spento la tua
  candelina.» (da bambino spegneva le candeline degli altri).

### Notte 4 · Lampy — *NON FERRARE*

- **Da dove viene**: la lampreda (la bocca a ventosa piena di anelli di denti).
- **Dal parco**: una cuffia da piscina di gomma a fiori, tirata sulla testa tonda.
- **Da bambino**: in piscina ti tirava giù per le gambe, per scherzo. Ora **tira la lenza**.
- **Come si gioca**: fa suonare il campanellino come un'abboccata. Le abboccate vere sono irregolari; le
  sue hanno un ritmo **perfetto**, tre colpi uguali, e sotto, nell'acqua, una risatina. Se ferri, hai
  agganciato lei: risale la lenza fino alla canna, jumpscare. Se aspetti, lascia la lenza e sparisce.
- **Il segnale** (scelto): tutti e due, il ritmo perfetto e la risatina.
- **Sagoma** (scelta): C «Sanguisuga», un arco di carne attaccato alla lenza per i due capi, ma più grosso.
- **Testa** (scelta): B «Bacio», il cranio da neonato sotto la cuffia, gli occhi tondi senza palpebre; la ventosa
  è una bocca enorme a bacio con gli anelli di denti da latte.
- **Modello e posa** (**approvati l'11 ottobre**; `tools/render/lampy.py`, posa `lampy_lenza` in
  `scena_creature.py`, anteprime `docs/concept/pose_lampy.jpg`, `pose_lampy_vicino.jpg`, `lampy_vetrina.jpg`):
  sta sulla lenza a destra della prua, oltre la punta della canna. La bocca, dove le entra la lenza, è a 43°
  dall'occhio, a 6 m e a 1,2 m sopra l'acqua; la ventosa della coda tiene la lenza a un palmo dall'acqua, a 55°.
  L'arco si vede quasi di profilo e la faccia guarda il pescatore. A 43° la canna le passa a sinistra della faccia
  senza coprirla, e la boa verde (38°) resta staccata a sinistra della testa: più vicina, la boa lampeggiava tra la
  faccia e l'arco e il suo riflesso le scendeva dalla bocca come bava luminosa. Lì nelle altre notti non c'è
  nessuno: Archie sta tra la lampara e la canna e molto più in alto, Molly sul bordo di destra da 59°. La testa è
  la B rifinita e un po' più grande, perché la faccia resti la prima cosa che si legge; il corpo è quello della
  tavola, un poco più grosso, e tutta Lampy è più grande del modello (1,15). L'orlo della cuffia passa sopra la nuca
  e il collo esce da sotto, come da una cuffia vera; i fiori sono più fitti sulla fronte. Nel gioco sta nello spazio
  della barca: la lenza parte dalla canna.
- **La lenza nel gioco** (approvata l'11 ottobre con la posa): la disegna il motore come sempre, ma per i punti della posa: dalla punta
  della canna alla bocca, sotto l'arco fino alla ventosa della coda, poi giù in mare (`scena_creature.lampy_lenza_punti`;
  dall'occhio in `tools/render/cache/lampy_posa.json`). Lampy ha tirato la lenza: il galleggiante è sott'acqua.
- **Sulla barca** (l'animazione proposta: apre e chiude piano la ventosa, con gli anelli di denti che girano): nel
  modello ci sono le due parti, `bocca` (da 0, chiusa a bacio stretto sulla lenza, a 1, spalancata a disco come
  quella della lampreda; nella posa 0,5, la bocca della tavola) e `denti_giro` (gradi: gli anelli vicini girano in
  versi opposti, come una macina). Cambia solo la testa, il corpo resta lo stesso: le toppe si fanno come per Robin.
  La vetrina mostra la ventosa chiusa, a riposo e spalancata.
- **Quando si vede** (scelto l'11 ottobre): **dopo i tre colpi**. I colpi li senti e basta; dopo il terzo affiora sulla
  lenza, ti guarda, poi molla e va giù. Chi aspetta la vede (la paura anche quando giochi bene), chi ferra subito se la
  trova addosso.
- **Render finali** (11 ottobre): la posa `lampy_lenza` e le toppe `lampy_bocca_chiusa` e `lampy_bocca_aperta` (coi denti
  girati di 10°; `pose_animate.py`, tavola `docs/concept/animazioni/lampy_ventosa.jpg`, **approvata l'11 ottobre**), in
  `public/assets/img`.
- **Nel gioco** (11 ottobre; **approvato l'11 ottobre**, la difficoltà la prova l'utente: «devo testare io la difficoltà»): la notte 4 si gioca (`?notte=4`, o Alt + 4 sul titolo nelle build di
  prova). Quando tocca a lei aspetta che la lenza sia in acqua e la prende: la canna si piega e il galleggiante va sotto
  come per un pesce, ma il campanellino lo suona lei, **tre colpi identici a 0,62 s l'uno dall'altro** (la canna dà lo
  stesso strattone a ogni colpo), e dopo il secondo **una risatina sott'acqua**. Dopo il terzo affiora sulla lenza
  (tagliata al pelo dell'acqua), la lenza le entra in bocca e passa sotto l'arco fino alla ventosa della coda; ti
  guarda per 2,4 s aprendo e chiudendo piano la ventosa (le toppe), poi molla e va giù: **l'esca resta lì** e il
  galleggiante torna su (chi aspetta perde solo il tempo della sua visita). **Se ferri** mentre ti tiene la lenza (anche
  quando è già affiorata) l'hai agganciata: la canna si piega tutta, lei spalanca la ventosa e risale la lenza (1,1 s),
  poi il jumpscare. Le abboccate vere restano irregolari (gli strattoni di `rod_bell_*`). Se ti nascondi o lanci un
  pesce a Gulpy mentre suona, la lenza non è più sua e se ne va. Quando canta la Madre molla anche lei. Il sonar la
  mostra sotto la lenza. Non viene con Hatch né con Archie. Quota 12; Gulpy passa più di rado (prima mangiava metà
  della quota), gli altri un po' più spesso della terza notte, e i pesci abboccano più in fretta. Giocatori simulati
  (`npm run sim -- 4 300`): **esperto 97%, medio 74%, maldestro 51%** (la terza 100/71/50); il bot riconosce il ritmo al
  secondo colpo (l'esperto quasi sempre, il maldestro nove volte su dieci) e non ferra mai se la vede affiorata.
- **Testi** (**approvati l'11 ottobre**): la radio «Quarta notte. Dodici pesci. / Lampy tira la lenza. / Tre colpi uguali e una
  risatina: non ferrare. / Lasciala andare. / Buona pesca.»; la frase della morte «Lampy ti ha tirato giù, per
  scherzo.» (in piscina tirava giù gli altri per le gambe); il suggerimento «Tre colpi uguali: è Lampy, non ferrare»,
  che nella quarta notte compare solo dal secondo colpo (prima nessun suggerimento, nemmeno «Abbocca!»: direbbe di
  ferrare anche lei); le didascalie «il campanellino, a tempo», «una risatina sott'acqua», «qualcosa affiora sulla
  lenza», «molla la lenza», «risale la lenza». I suoni sono in `docs/AUDIO.md` (approvati l'11 ottobre).
- **Jumpscare** (**approvato l'11 ottobre** sull'anteprima, `docs/concept/jumpscare/js_lampy_fotogrammi.jpg`
  e `js_lampy.gif`; `jumpscare.py`, `ATTACKS['lampy']`): agganciata, ti salta in
  faccia dalla lenza con la ventosa spalancata a disco (a 60 cm dall'occhio riempie mezzo quadro), e da un fotogramma
  all'altro gli anelli di denti da latte girano come una macina, quelli vicini in versi opposti; una luce calda dalla
  parte della lanterna le prende la faccia, come per Robin. Il **render finale** (64 campioni, otto fotogrammi
  `public/assets/img/js_lampy_00…07.webp`, 11 ottobre) è nel gioco.

### Notte 5 · Fangy — *STARE ZITTI*

- **Sagoma** (scelta): B «Mastino», curvo e basso, la testa spinta avanti, le zanne che pendono, le nocche
  in acqua.

- **Da dove viene**: il pesce vipera e il pesce dente di sciabola (denti troppo lunghi per chiudere la
  bocca, file di lucine lungo il ventre).
- **Dal parco**: gli occhialini da piscina con le lenti dipinte di nero, ormai incastrati nella faccia.
- **Da bambino**: giocava a Marco Polo a occhi chiusi e vinceva sempre. Ora è cieco e **caccia a
  orecchio**.
- **Come si gioca**: lo annuncia una fila di lucine che si accende sott'acqua e si avvicina. Mentre è
  vicino devi **fare silenzio**: non riavvolgere, non lanciare, non cambiare la lampara, non buttare pesci.
  Se resti fermo abbastanza se ne va. Ogni rumore lo fa venire più vicino; al terzo, jumpscare.
- **Perché funziona**: va contro tutto il resto. Se in quel momento abbocca un pesce lo devi lasciar
  andare; se arriva Gulpy, tirargli un pesce fa rumore.
- **Testa** (scelta): A «Sciabola», il testone del pesce dente di sciabola con le zanne del pesce vipera fuori dalla
  bocca, le fossette per sentire, gli occhialini affondati nella carne.
- **Modello e posa** (**approvati l'11 ottobre**; `tools/render/fangy.py`, posa `fangy_ascolta` in
  `scena_creature.py`, anteprime `docs/concept/pose_fangy.jpg`, `pose_fangy_vicino.jpg`, `fangy_vetrina.jpg`):
  sta nell'acqua a destra, un po' dietro il pescatore. La testa è a 112° dall'occhio e a 2 m, all'altezza del
  capodibanda e quasi un metro fuori dalla fiancata; le nocche sono in acqua a mezzo metro dallo scafo. Dall'occhio
  si vedono la testa e la gobba sopra il bordo, le braccia scendono dietro la fiancata. Lì nelle altre notti non c'è
  nessuno: Molly arriva fino a 94°, Hatch e il sonar stanno a poppa, la canna e la lenza (con Lampy) davanti a
  destra. La testa e il corpo sono quelli della tavola, un po' più grandi (1,12); la testa però non è china:
  punta la faccia sul pescatore, gli occhialini ciechi fissi su di lui (china come nella tavola, vista dall'alto la
  visiera ossea gli nascondeva le lenti nere). Nel gioco sta nel mondo, come Hatch: la barca non la tocca.
- **Sulla barca** (l'animazione proposta: gira la testa di scatto verso ogni rumore e le lucine si accendono in fila):
  nel modello la testa gira sul collo (`testa`, gradi; cambia solo la testa, il corpo resta lo stesso, quindi le
  toppe si fanno come per Robin) e le lucine sono una per oggetto, 54 in fila: il ventre dalla gola verso l'acqua,
  poi la mandibola e le guance. Ognuna porta la sua fila e il suo centro, e la posa le elenca dall'occhio
  (`tools/render/cache/fangy_posa.json`): il motore le può accendere una dopo l'altra e farle pulsare come gli
  occhi. **Deciso l'11 ottobre**: nello strato le lucine sono spente (`luci` 0) e tutta la luce la fa il motore, perché
  si accendano in fila come nella proposta approvata; le loro posizioni vanno nel manifest con lo strato. La vetrina
  mostra la testa girata dalle due parti e le lucine spente.
- **Render finali** (11 ottobre): la posa `fangy_ascolta` e le toppe `fangy_testa_prua` e `fangy_testa_poppa` (la testa
  girata di 35° dalle due parti; sono la creatura intera, perché girando la testa scopre e copre il corpo), con le 54
  lucine nel manifest. Tavola `docs/concept/animazioni/fangy_testa.jpg` (**approvata l'11 ottobre**).
- **Nel gioco** (**approvato l'11 ottobre**: «Tutto approvato procedi»; il gioco la propone dopo la quarta): lo annuncia
  una **fila di nove lucine azzurre sott'acqua** che arriva dal largo girando verso la barca, a destra dietro di te (5 s,
  con un suono sordo che pulsa); le lucine spariscono sotto la fiancata e lui **sale dall'acqua** accanto alla barca
  (1,4 s). Poi **ascolta** (5,5 s): ogni rumore che fai (lanciare o ferrare, il mulinello tenuto per più di 1,2 s,
  buttare un pesce, coprirti col telone, cambiare la lampara) lo fa **voltare di scatto verso prua**, dove hai fatto
  rumore, e accende tutte le sue lucine insieme; resta ad ascoltare almeno un altro po'. Al terzo rumore è addosso.
  Mentre ascolta in silenzio, ogni tanto volta la testa verso poppa come per sentire meglio (è cieco: non conta dove
  guarda). Le lucine del ventre e della testa **respirano**: si accendono in fila dalla gola verso l'acqua e calano
  insieme, sempre più in fretta a ogni rumore che ha sentito (al buio si vedono solo loro). Se resti zitto torna giù
  (2 s). Il suo respiro bagnato si sente dietro le spalle finché è su, e il cuore batte più forte a ogni rumore. Il
  suggerimento dice «Fangy ascolta: niente rumori»; il sonar lo mostra mentre arriva e accanto alla fiancata. Quando
  canta la Madre torna giù anche lui. Non viene con Hatch, Archie né Robin. Viene ogni 85-125 s e ascolta 7 s: ogni
  visita ferma la pesca per una decina di secondi, quindi la quota scende a 11 e i pesci abboccano più in fretta.
  Giocatori simulati (`npm run sim -- 5 400`, da rifinire): **esperto 96%, medio 81%, maldestro 53%**; Fangy prende
  soprattutto chi continua a recuperare quando sale.
- **Testi** (**approvati l'11 ottobre**): la radio «Quinta notte. Undici pesci. / Fangy non vede. Sente. / Quando le luci salgono,
  zitto. / Niente mulinello, niente lampara. / Buona pesca.»; la frase della morte «"Marco." Hai risposto.» (giocava a
  Marco Polo a occhi chiusi: chi sente la voce trova chi risponde); il suggerimento «Fangy ascolta: niente rumori»; le
  didascalie «lucine sott'acqua, si avvicinano», «qualcosa sale accanto alla barca, dietro di te», «si volta di scatto»,
  «torna giù». I suoni sono in `docs/AUDIO.md` (approvati l'11 ottobre).
- **Jumpscare** (**approvato l'11 ottobre** sull'anteprima, `docs/concept/jumpscare/js_fangy_fotogrammi.jpg` e
  `js_fangy.gif`; `jumpscare.py`, `ATTACKS['fangy']`): si lancia dalla fiancata con la
  testa avanti e le zanne puntate su di te, tutte le lucine accese; arriva a 55 cm dall'occhio chinandosi un poco, con
  una luce calda dalla parte della lanterna sulla faccia. Il **render finale** (64 campioni, otto fotogrammi
  `public/assets/img/js_fangy_00…07.webp`, 11 ottobre) è nel gioco.

### Notte 6 · La Madre — *IL FINALE*

> **Approvato l'11 ottobre** (come si gioca e il finale A). **Questionario della sera (11 ottobre)**: la sagoma è la
> **B «Occhio»**, col jumpscare fatto con la bocca coi fanoni a sbarre di lettino della A; il colore **bianco latte**
> (sotto la vernice blu della mascotte che si stacca a croste); i suoi suoni (`madre_*`, `docs/AUDIO.md`) **approvati**;
> la quota **10 pesci**; alzare il binocolo mentre passa è un movimento (si muore).

- **Il suo aspetto** (approvato l'11 ottobre, la tavola `docs/concept/madre_sagome.png`): resta quasi tutta sott'acqua,
  lunga una trentina di metri, e passa proprio sotto la barca; fuori sale solo la fronte e **un occhio grande quanto
  la barca**, con le ciglia da cartone animato. Sotto, la pinna ripiegata sul ventre stringe i suoi piccoli, come la
  statua coi pesciolini in grembo. Il **jumpscare** viene da sotto con la **bocca** spalancata e i **fanoni come le
  sbarre di un lettino** (dalla sagoma A).

- **Il modello** (**da approvare**, fatto l'11 ottobre sera; `tools/render/madre.py`, ramo `claude/madre-modello`):
  una balena di una trentina di metri (dal muso alla coda 33 m), la testa grande come quella della mascotte, con la
  fronte tonda come i beluga e la gola a pieghe come le balenottere. La pelle è **bianco latte**, liscia e bagnata, con
  la stessa melma degli altri mostri (chiazze lucide, colature, ristagni nelle pieghe, gocce che colano dalle palpebre
  e dal mento). Sopra c'è ancora la **vernice della mascotte** (i colori di `mascot.py`): il blu sul dorso e sulla
  testa, la pancia crema sulla mandibola e sotto il corpo, le guance rosa, il sorriso rosso scuro. La vernice è
  screpolata e **si stacca a grandi croste** di un paio di metri, con l'orlo frastagliato, alzato e sporco d'alga, e
  sotto si vede il bianco. Il **sorriso dipinto** continua la linea della bocca e sale fino **sotto l'occhio**.
  L'**occhio** è grande quanto la barca (4,4 m, ne resta fuori una calotta larga quasi 4 m), azzurro come quello della
  mascotte ma vero: il bianco lattiginoso con le venuzze, la pupilla nera grande, bagnato; sta nell'orbita sotto una
  palpebra pesante e gira verso il pescatore. Sopra, **tre ciglia da cartone animato** nere e lucide. Sullo sfiatatoio il
  **ciuffo d'acqua** a ombrello come quello della statua. In bocca i **fanoni sono le sbarre di un lettino**: tonde,
  dritte e in fila lungo i due lati del palato, verniciate di bianco e scheggiate (sotto, il corno scuro), unite in fondo
  da un corrimano; a bocca chiusa stanno piegate dentro la mandibola. Sotto, le **due pinne ripiegate sul ventre**
  stringono **i suoi piccoli** (quattro bambini rannicchiati), come la statua coi pesciolini in grembo.
  `build(bocca=…)` apre la mandibola (fino a 62°), `build(viewer=…)` gira gli occhi.
  - **La tavola della testa** (anteprima a pochi campioni, `docs/concept/madre_testa.jpg`, **da approvare**): tutta fuori
    dall'acqua, la fronte e l'occhio dalla barca, l'occhio con le ciglia, il sorriso e la guancia, le croste sulla
    fronte, la bocca spalancata coi fanoni.
  - **La posa di gioco** `madre_sale` (anteprima a pochi campioni, `docs/concept/madre_posa.jpg`, **da approvare**;
    `scena_creature.madre_posa`): sale accanto alla barca a sinistra; il centro dell'occhio sta a 55° dalla prua, a
    6,8 m dall'occhio del pescatore e 1 m sopra il mare (la calotta a circa 3,4 m dal bordo), e guarda il pescatore;
    il muso va verso prua, sott'acqua, e il corpo scende verso poppa. Fuori escono la fronte (fino a 5,7 m sul mare) e
    l'occhio. Vista dall'occhio come le altre pose, di notte con la lampara e all'alba (l'alba dell'anteprima è
    provvisoria: cielo caldo dietro a sinistra, il sole basso). **Render finale fatto** (notte fra l'11 e il 12
    ottobre: l'utente ha dato a me il via per scegliere): è fra le pose del gioco (`POSES`), con la cima della sagoma
    nel manifest (`tools/render/cima.py`) perché le luci lontane che ha dietro, come la candela dell'edicola, non si
    vedano attraverso di lei.
  - **Il jumpscare dal basso** (anteprima, otto fotogrammi a pochi campioni,
    `docs/concept/jumpscare/js_madre_fotogrammi.jpg`, **da approvare**; `jumpscare.py`, `ATTACKS['madre']`): la barca
    è sbalzata (sollevata di 90 cm, inclinata a sinistra, la prua su) e la vista si inclina con lei; da sinistra,
    bassa e mezza sott'acqua, sale la bocca spalancata con l'apertura verso di te e ti viene addosso: negli ultimi
    fotogrammi sei dentro, col palato rosso sopra, la lingua sotto, la gola nera in fondo e ai due lati i fanoni in fila
    come le sbarre di un lettino, col corrimano. (Venendo dritta da sotto, il palato passava davanti agli occhi: per
    questo arriva da un lato.) Gli altri jumpscare non cambiano: in `jumpscare.py` si aggiungono solo la voce `madre` e
    la sua camera, che si inclina con la barca.
  - **Render finali** (notte fra l'11 e il 12 ottobre, scelti da me col via libera dell'utente): la posa e il
    jumpscare (otto fotogrammi a 10 al secondo). L'utente li vede domattina e può ancora cambiarli.
- **Giocabile** dalla notte del 12 ottobre (prima era in bozza, finché non c'era il suo aspetto): il gioco la propone
  dopo la quinta.
- **Come si gioca**: tornano tutti e sette i mostri e la regia ne manda di più insieme (è la notte più dura). Quota 10
  (proposta 12; con 12 l'esperto simulato vinceva 5 notti su 100; **approvato 10** l'11 ottobre),
  la batteria come sempre. In più c'è lei: sul sonar un'**ombra enorme** gira attorno alla barca, lontana, per tutta
  la notte. Tre volte (verso le 2, le 4 e le 5:30) si avvicina e **passa sotto la barca**.
- **Gli avvisi**: l'ombra sul sonar si stringe verso il centro; i mostri si zittiscono e tornano giù tutti insieme
  (anche loro hanno paura della mamma); il mare si calma di colpo; dal fondo sale la ninna nanna della Madre
  canticchiata da una voce di balena (la stessa ninna nanna di quando la batteria muore); la lampara trema.
- **Mentre passa sotto** (da 10 a 20 s, sempre più a lungo): **immobilità totale**. Niente canna, lampara, telone,
  pesci, sonar o binocolo (alzarlo è un movimento: approvato l'11 ottobre), e non girare lo sguardo (un tremito
  piccolo si perdona). La barca si solleva piano sul suo dorso e
  scricchiola. Se abbocca un pesce, lo lasci andare.
- **Se ti muovi** ti prende: il jumpscare viene dal basso, con la barca sollevata. La frase della morte (proposta):
  «Mama Marina ama i suoi piccoli. Adesso anche te.» Quando è passata, tornano i figli.
- **La radio**: «Sesta notte. Dieci pesci. / Stanotte viene anche lei. / Quando passa sotto la barca, non
  muoverti. / Non toccare niente, non guardarti intorno. / Buona pesca.»
- **Il finale A «La quota»** (scelto l'11 ottobre): all'alba la Madre sale accanto alla barca (l'unica volta che la
  vedi davvero) e attorno a lei emergono tutti i suoi figli; prende il secchio e torna giù con loro. Sorge il sole;
  la radio: «Ce l'hai fatta. Per quest'anno.» I titoli di coda, e si sblocca la notte 7. La **cinematica di 17 s**
  (`src/app/cinematic.ts`, `FINALE_A`, sul suono `madre_dawn_breve`) è **approvata** (11 ottobre). Da stanotte c'è
  anche lei: la posa `madre_sale` sale piano a sinistra da 0,3 a 3 s, insieme al mare che si gonfia, mentre lo sguardo
  si gira sul suo occhio; resta finché il secchio si svuota e torna giù per prima (10-12,2 s).

### Notte 7 · La notte extra

> **Deciso l'11 ottobre**: la notte coi livelli da scegliere (come la notte personalizzata di FNAF), con anche **la
> Madre come ottavo livello** (quanto spesso passa sotto la barca). Ha un suo finale, il **finale B «Il ricordo»**:
> come il finale A, ma prima di andarsene la Madre ti lascia sul banco un disegno a pastelli bagnato, da bambino: voi
> quattro a Splashland nel 1997, e il quarto sei tu (c'eri anche tu, e sei l'unico che è tornato a casa; prima era una
> foto dell'edicola, il disegno è un'idea dell'utente approvata il 12 ottobre). Si vede **solo vincendo la notte 7 con
> impostazioni difficili** (tutti, Madre compresa, almeno a 10); con impostazioni più facili un'alba normale.
> **Tutti a 20** (questionario dell'11 ottobre): **difficilissima ma possibile**, il traguardo da raccontare (come il
> 20/20/20/20 di FNAF): un giocatore bravissimo deve poterla vincere.

> ⚠️ **PROPOSTA DA APPROVARE** (11 ottobre, tutto quello che segue: regole, numeri, testi e schermata). La notte
> extra si sblocca finendo l'ultima notte giocabile: oggi la quinta, quando la sesta uscirà dalla bozza la sesta.

Come la *custom night* di FNAF: per ognuno dei sette mostri, per **la Madre** (ottava, confermato dall'utente
l'11 ottobre) e per **Soggy**, il Foxy (nono, deciso dall'utente il 12 ottobre), si sceglie un **livello da 0 a 20**. A 0 non viene, a
20 è feroce. Le regole che il giocatore ha imparato non cambiano mai (i dieci della conta di Hatch, i tre colpi di
Lampy, il terzo rumore di Fangy): cambiano solo **quando arriva, quanto spesso torna e quanta pazienza ha**.

- **Da dove vengono i numeri** (`extraNight()` in `src/game/config.ts`): ogni mostro ha tre punti di riferimento e
  fra l'uno e l'altro i numeri si sfumano.
  - **1, calmo**: arriva tardi, le pause fra una visita e l'altra sono 1,6 volte quelle della sua notte, un filo più
    di pazienza.
  - **5, come la sua notte**: esattamente i numeri della notte in cui arriva per la prima volta (Gulpy, Molly e
    Hatch la prima, Robin la seconda, Archie la terza, Lampy la quarta, Fangy la quinta). Un test lo controlla.
  - **20, feroce**: arriva nel primo quarto d'ora, torna quasi il doppio più spesso che nella sua notte e ha meno
    pazienza che nella quinta (Gulpy sale e pretende prima, Molly si offende prima, Hatch conta più svelto e cerca
    più a lungo, Robin ruba più spesso, Archie prende fiato in meno tempo e resta più a lungo al buio, Lampy prende la
    lenza prima, Fangy arriva più svelto e ascolta di più).
  - Fra 5 e 10 la curva sale piano verso il punto feroce (se no a 10 era già quasi impossibile).
  - **Dal 10 al 20, difficilissima ma possibile** (decisione dell'utente dell'11 ottobre): un tratto a sé, in cui
    **le pause fra una visita e l'altra restano quelle del 10**, mentre pazienza, avvisi, velocità e primo arrivo vanno
    fino al punto feroce. Dal 10 al 20 i mostri non tornano più spesso, ma ogni visita è più cattiva; e la Madre al
    20 passa cinque volte invece di tre, con meno avviso.

    **Perché le pause e non la quota.** Con le pause del punto feroce, tutti a 20 l'esperto non vinceva quasi mai
    (una notte su 150): moriva quasi sempre alle sei con la quota mancata, 5,5 pesci nel secchio su 10, perché le
    visite si mangiavano tutto il tempo per pescare. Le strade erano due: allungare le pause al 20, o abbassare la
    quota ai livelli alti. Ho scelto le pause: la quota resta una sola per tutta la notte extra (la radio dice «Dieci
    pesci», e una quota che cambia coi livelli sarebbe una regola nuova da spiegare), e il giocatore vede comunque
    salire la ferocia dal 10 al 20. Fermare le pause al 10 è anche il limite naturale: allungarle oltre (provato fino
    a 1,4 volte quelle feroci) faceva tornare i mostri **meno** spesso al 20 che al 10, cioè un 20 meno feroce del 10.
    Con le pause ferme al 10 ho accorciato un po' anche le passate della Madre al 20 (da 12 a 20 s invece che da 14 a
    26): con quelle più lunghe l'esperto vinceva il 5,7%, al limite basso. Risultato: **l'esperto vince il 6,7% delle
    notti tutti a 20** (su 300; su 600 seed il 7,3%), il medio il 2%, il maldestro mai. I livelli fino al 10 non sono
    cambiati (un test lo controlla). Dopo le novità dell'11 ottobre sera (il sonar che mostra solo la
    Madre, i frammenti nuovi con il tetto di due per notte) i numeri sono gli stessi: 6,7% su 300, 7,3% su 600 seed.
- **La Madre** (**confermato l'11 ottobre** che c'è, come ottavo livello): è la stessa della notte 6 (l'ombra enorme
  sul sonar, i figli che si zittiscono e tornano giù, l'immobilità totale mentre passa sotto la barca). Il suo livello
  dice **quante volte passa, quanto dura ogni passata e quanto avvisa prima** (`extraMother()`, numeri da approvare):
  - **1**: una passata sola, verso le 3, di 8 s, con 12 s di avviso e un tremito di 5° perdonato;
  - **10**: **esattamente come nella notte 6** (tre passate, verso le 2, le 4 e le 5:30, di 10, 15 e 20 s, 10 s di
    avviso, 4° di tremito; un test lo controlla);
  - **20**: cinque passate (verso l'1, le 2, le 3, le 4:15 e le 5:30) da 12 a 20 s, con 8 s di avviso e 3° di tremito.

  Le passate sono 1 + livello/5 (arrotondato: 2 dal 3, 3 dall'8, 4 dal 13, 5 dal 18); durate, avviso e tremito si
  sfumano. A 0 non viene. Il finale A della notte 6 (lei che si prende il secchio) nella notte extra non c'è.
- **Soggy, il Foxy** (**deciso il 12 ottobre** che c'è, come nono livello; numeri da approvare): sta in uno dei due
  posti del binocolo tutta la notte, quindi non ha pause fra una visita e l'altra. Il livello cambia quando compare,
  quanto aspetta prima di sporgersi e di lasciare il posto (la sua pazienza), la corsa fino alla barca e quanto spesso
  cambia posto:
  - **1, calmo**: compare verso le 2:20 (1,8 ore), si sporge dopo 60 s senza guardarlo, lascia il posto dopo 110 s,
    corre per 4 s, cambia posto una volta su dieci;
  - **5, come la sua notte**: i numeri della notte 2 (un test lo controlla);
  - **20, feroce**: compare nel primo quarto d'ora, si sporge dopo 30 s, lascia il posto dopo 54 s, corre per 2,6 s,
    cambia posto quasi una volta su due. Lui non ha pause, quindi dal 10 al 20 va dritto al punto feroce.

  Come nelle notti 2-5, il tempo passato col binocolo si ripaga tirando su i pesci più in fretta: quando c'è lui il
  recupero è più svelto di un decimo (`FOXY_REEL`, decisione dell'utente: «se devi bilanciare, riduci il tempo
  necessario per tirare su i pesci»). Con lui anche il finale speciale chiede di vincere con tutti e nove almeno a 10.
- **Il finale speciale** (**confermato l'11 ottobre**): si vede solo **vincendo con tutti, Madre compresa, almeno a
  10** (`extraEndingEarned()`; dal 12 ottobre anche Soggy); con impostazioni più facili all'alba c'è l'alba normale. Il finale vero è da fare:
  per ora dopo l'alba compare una **schermata segnaposto** (`Screens.extraEnding`, il titolo «Il finale della notte
  extra» e una riga che dice che è un segnaposto), poi i risultati. È diverso da quello della notte 6.
- **Il resto della notte**: quota **10**; i pesci abboccano in fretta come nella quinta notte; la batteria è quella
  dalla notte 2 in poi (con la ninna nanna della Madre a batteria morta); le ore fanno salire l'attività come nella
  quinta. La regia tiene le **esclusioni della quinta notte**: chi chiede il contrario dell'altro non viene insieme a
  lui (Robin con Molly, Hatch o Archie; Hatch con Gulpy, Lampy o Fangy; Lampy con Archie; Fangy con Archie o Robin).
  Gulpy, Molly e Hatch, che il gioco disegna in tutte le notti, a 0 restano semplicemente a casa.
- **La schermata** (`docs/concept/notte7_livelli.jpg`): dal titolo, «Notte extra» (compare solo quando è sbloccata).
  Nove schede in fila, una per mostro più la Madre e Soggy (nelle finestre più strette 5 + 4 centrate): il nome, la sua regola in due parole, il livello grande con − e + (anche la
  rotella sulla scheda), e sotto una parola: *non viene* (0), *calmo* (1-4), *come la sua notte* (5), *svelto* (6-14),
  *feroce* (15-20). Più è alto, più la scheda si tinge di rosso e il numero passa dall'ambra al rosso sangue; a 0 la
  scheda si spegne e il nome è barrato. Sotto, le preimpostazioni **Tutti a 0, Tutti a 5, Tutti a 10, Tutti a 20,
  I primi tre** (Gulpy, Molly e Hatch a 15, gli altri e la Madre a 0; le altre valgono anche per la Madre). Poi **Salpa** e Indietro. I livelli scelti restano nel
  salvataggio per la volta dopo (all'inizio tutti a 5). Per ora ci sono i nomi: i **ritratti** dei mostri (per esempio le
  foto sbiadite dell'edicola) sono da fare.
- **La notte**: l'intro dice «Notte 7» con la quota; vincerla non sblocca niente e non cambia «Continua»; alla fine
  «Riprova» la rigioca con gli stessi livelli. Per le prove: `?notte=7` (Nuova partita apre la schermata dei livelli,
  e il pulsante compare anche se non è sbloccata) e **Alt+7** sul titolo.
- **Testi** (italiano e inglese, in `src/i18n.ts`, segnati da approvare): il pulsante «Notte extra» / «Extra night»;
  «Scegli chi viene stanotte. 0: non viene. 20: feroce.» / «Choose who comes tonight. 0: stays away. 20: ferocious.»;
  le regole sotto i nomi «sfamalo, guardala, nasconditi, luce in faccia, spegni la luce, non ferrare, stai zitto» /
  «feed him, watch her, hide, light in his face, light off, don't strike, stay quiet»; per la Madre «La Madre, non
  muoverti» / «The Mother, don't move»; per Soggy «non perderlo di vista» / «don't lose sight of him» (12 ottobre, da
  approvare); «Salpa» / «Cast off». Il finale B «Il ricordo»: sotto, «I finali
  segreti nel gioco» (il segnaposto di prima non c'è più).
  La radio, corta: «Notte extra. Dieci pesci. / Stanotte vengono quelli che hai chiamato tu. / Buona pesca.» /
  «Extra night. Ten fish. / Tonight the ones you called are coming. / Good fishing.»
- **Giocatori simulati, con la Madre** (`npm run sim -- 7 300 <livelli>`, dopo l'unione dei rami claude/lampara e claude/notte6:
  batteria più rapida, Molly che aspetta sotto il telone, Robin che si scaccia con la sola luce; un numero vale per tutti
  e otto, se no gli otto livelli in ordine Gulpy, Molly, Hatch, Robin, Archie, Lampy, Fangy, Madre). Vittorie di
  esperto / medio / maldestro; fra le morti, «la quota» è la quota mancata alle sei e «la Madre» è lei che ti prende
  perché ti sei mosso:

  | Livelli | Esperto | Medio | Maldestro | Chi uccide |
  |---|---|---|---|---|
  | tutti a 0 | 100% | 100% | 100% | nessuno: si pesca e basta |
  | tutti a 1 | 99% | 85% | 63% | Lampy (i bot sbagliano a sentire i tre colpi), la Madre |
  | tutti a 3 | 98% | 79% | 52% | Lampy, la Madre |
  | tutti a 5 | 98% | 76% | 39% | Lampy, la Madre, Fangy, Archie |
  | **tutti a 10** (il minimo per il finale B) | 89% | 65% | 27% | la Madre, Lampy, la quota; il maldestro anche Archie |
  | tutti a 15 | 34% | 22% | 5% | la quota (non resta tempo per pescare), la Madre |
  | **tutti a 20** | **6,7%** | 2% | 0% | quasi sempre la quota; poi la Madre |

  **Con Soggy** (12 ottobre, 200 partite per abilità, Soggy allo stesso livello degli altri, contro gli otto senza di
  lui nella stessa prova): il recupero più svelto compensa il tempo al binocolo.

  | Livelli | Esperto | Medio | Maldestro | Senza Soggy (stessa prova) |
  |---|---|---|---|---|
  | tutti a 5 | 98,5% | 76,5% | 43% | 98,5% · 77% · 39,5% |
  | **tutti a 10** | 97% | 64,5% | 22,5% | 90% · 67,5% · 26% |
  | **tutti a 20** | **12%** | 2% | 0% | 5,5% · 2,5% · 0% |

  Soggy uccide il maldestro in poche partite (dal 4% a tutti a 5 al 10% a tutti a 20) e il medio a tutti a 20 (17%).
  Tutti a 20 resta difficilissima ma possibile.
  | i sette a 20, la Madre a 0 | 10% | 7% | 3% | la quota, Lampy |
  | solo la Madre a 10 | 98% | 78% | 65% | la Madre |
  | solo la Madre a 20 | 97% | 69% | 45% | la Madre |
  | tutti a 5, Lampy e Fangy a 15, Madre a 5 | 94% | 71% | 36% | Lampy, la Madre |
  | i primi tre a 15, il resto a 0 | 100% | 100% | 100% | nessuno |
  | i primi quattro a 20, il resto a 0 | 94% | 85% | 65% | la quota (Gulpy e Robin svuotano il secchio) |
  | Robin, Archie, Lampy e Fangy a 20, il resto a 0 | 99% | 80% | 6% | Archie, Lampy |

  A 10 con la Madre l'esperto vince di più che senza (tutti a 10: 89%; i sette a 10 e lei a 0: 82%), perché quando
  passa i figli tornano giù e per un po' non salgono; a 20 invece le sue cinque passate tolgono tempo alla pesca
  (con lei 6,7%, senza 10%); lei uccide soprattutto chi si muove (il maldestro e il medio). Ogni
  mostro da solo a 20 si batte; insieme rubano il tempo per pescare, e a 20 il nemico vero è l'orologio. L'esperto
  tiene la luce alta e attira tutti, quindi da 15 in su vince poco più del medio: un giocatore che dosa la luce
  dovrebbe fare meglio dei bot. Il finale B (tutti almeno a 10) per l'esperto è alla portata, per il medio due volte su
  tre; tutti a 20 è il traguardo da raccontare. Un test controlla che a 20 l'esperto vinca qualche volta (4 notti su 60
  seed fissi).

## I finali

> **Approvati l'11 ottobre** (i due segreti: proposta dell'utente, storie e regole proposte e approvate).
> **Ogni finale è una cinematica breve, 15–20 secondi, fatta nel motore del gioco** (la vista che si muove da sola, le
> pose delle creature, la luce, i suoni e i sottotitoli; saltabile con Esc), poi i titoli di coda. Le immagini della
> Madre arrivano quando è scelta la sua sagoma.

All'alba della **sesta notte** il finale dipende dal pesce che hai lasciato ai mostri che dormono nelle tane, nelle
immersioni all'alba (`docs/IMMERSIONI.md`; durante le notti Gulpy va sfamato per forza, quindi non conta):

| Finale | Quando | La cinematica |
|---|---|---|
| **«I tuoi»** (segreto) | hai lasciato un pesce a qualcuno **a ogni alba**, dalla prima alla quinta | All'alba la Madre sale e canta per richiamare i figli, ma loro non la seguono: restano attorno alla tua barca. Lei torna giù da sola, col suo lamento. Sorge il sole, la barca rientra verso il porto e sul sonar, dietro di te, sette ombre la seguono. Ultima inquadratura: il molo all'alba, la barca ormeggiata, e sulle assi bagnate sette file di piccole impronte che vanno verso il paese. «Non sei tornato da solo.» |
| **«Nessuno»** (segreto) | sei sceso nelle tane **almeno tre volte** e **non hai mai lasciato un pesce**, nemmeno quando ti avanzava | All'alba la Madre sale accanto alla barca, ma non guarda il secchio: guarda te. I figli affiorano attorno, uno dopo l'altro, e restano fermi a fissarti. La vista scende verso l'acqua, la lampara si spegne, nel buio la ninna nanna canticchiata. Ultima inquadratura: l'edicola del parco con le foto dei bambini scomparsi; fra le foto, una nuova: la tua. «Non hai mai dato niente ai suoi piccoli. Adesso sei uno di loro.» |
| **A «La quota»** | in tutti gli altri casi: hai sfamato qualcuno una o due volte (o fino a quattro), oppure non sei mai sceso | La Madre sale accanto alla barca, attorno a lei emergono i figli, prende il secchio e torna giù con loro; sorge il sole; la radio: «Ce l'hai fatta. Per quest'anno.» |

**L'ultima inquadratura di «I tuoi»** (il molo all'alba con le sette file di impronte, `docs/concept/finali_molo_anteprima.jpg`)
è **approvata** (11 ottobre), con le impronte più scure e bagnate perché si leggano anche fuori dal riflesso del sole.

La **notte 7** ha il suo finale, **B «Il ricordo»** (con impostazioni difficili; sopra), anche lui come cinematica
breve. Fatti: il «regista» delle cinematiche, i render del molo e dell'edicola, i suoni dei due finali segreti e il
taglio più corto del finale all'alba (`madre_dawn_breve`), le due cinematiche segrete, i titoli di coda e il finale B
col disegno a pastelli (sotto; i tre finali approvati il 12 ottobre).

### I finali segreti nel gioco

> **Approvati il 12 ottobre** i tre finali, «I tuoi», «Nessuno» e «Il ricordo» (ramo `claude/finali-gioco`), per la
> build di quella sera. La frase del finale B è stata tolta per scelta dell'utente. I titoli di coda restano coi nomi
> segnaposto.
> Le clip col suono per l'approvazione stanno in `docs/concept/clip/`.

- **Quale finale** (`chooseEnding` in `src/app/save.ts`, provato in `tests/save.test.ts`): il salvataggio ricorda,
  alba per alba (`dawns`, la chiave è la notte appena vinta, 1-5), se sei sceso e se hai lasciato il pesce a
  qualcuno. «I tuoi» se un pesce l'hai lasciato **a ogni alba dalla prima alla quinta**; «Nessuno» se sei sceso
  **almeno tre volte** e **non hai mai lasciato un pesce**; il finale A in tutti gli altri casi (anche mai sceso).
  Rigiocando una notte la sua alba si riscrive; «Nuova partita» le azzera; un'immersione che non parte (dati mancanti)
  conta come un'alba senza discesa. In sviluppo `?finale=tuoi|nessuno|A` lo forza (prove e registrazioni).
- **Le cinematiche** (`src/app/cinematic.ts`, `FINALE_TUOI` e `FINALE_NESSUNO`, provate in `tests/cinematic.test.ts`),
  sui tempi dei loro suoni (`docs/AUDIO.md`):
  - **«I tuoi»** (21 s): la Madre sale a sinistra e chiama (0-3 s); i figli affiorano attorno alla barca e non la
    seguono, mentre lei richiama più forte (3-6 s); lei torna giù da sola (6-10 s); i figli restano, poi scendono
    sotto la barca mentre sorge il sole (10-13 s); un attimo di buio e, quando la barca tocca il molo (14,6 s),
    l'ultima inquadratura del molo con le impronte, che si avvicina piano alle impronte mentre si sentono i passetti;
    «Non sei tornato da solo.»
  - **«Nessuno»** (21,6 s): la Madre sale e ti guarda (0-3 s); i figli affiorano uno dopo l'altro e restano fermi a
    fissarti (3-8 s); di nuovo lei, poi la vista scende verso l'acqua e la lampara muore (8-10 s); il buio con la ninna
    nanna (10-15 s); a 15 s il taglio netto sull'edicola, dove il mare e i rumori della barca si spengono, e la vista
    si avvicina piano alla Polaroid; «Non hai mai dato niente ai suoi piccoli. Adesso sei uno di loro.»
- **Il regista** ha due cose nuove: l'**ultima inquadratura** (`still`: l'immagine renderizzata a tutto schermo, la
  dissolvenza, lo zoom e il punto al centro nel tempo; si disegna con l'esposizione del suo render al posto di quella
  della notte, più la sola luminosità delle opzioni) e l'evento **`quiet`** (il taglio su un altro posto spegne il
  mare, il vento e gli scricchiolii).
- **I titoli di coda** (`Screens.credits`, DA APPROVARE, i nomi sono un segnaposto in `src/i18n.ts`: «(nome da
  decidere)» / «(name to be decided)»): dopo ognuno dei
  tre finali della notte 6, su un fondo nero salgono il titolo, i ruoli coi nomi e «Grazie per aver giocato.», con la
  ninna nanna del titolo; Esc, Invio o un clic li saltano. Poi i risultati, con l'avviso della notte extra.
- **Il finale B «Il ricordo»** (la notte 7; approvato il 12 ottobre, senza frase): al posto della foto del 1997 (provata
  coi bambini renderizzati, `tools/render/bambini.py` e `finali.foto_1997`, restano nel ramo ma non si usano) un
  **disegno a pastelli: idea dell'utente e approvato il 12 ottobre** (`docs/concept/ricordo_disegno.webp`, disegnato
  da `tools/render/pastelli.py`): i quattro bambini davanti all'ingresso di Splashland la sera della Night
  Splash (14-8-97, la data del braccialetto), tre con la faccia scarabocchiata di nero e una cosa a testa (i braccioli
  di Molly, il salvagente a paperella di Gulpy, il giocattolo luminoso di Hatch), il quarto col berretto e la canna
  col pesce.
  - **La scena** (`finali.scena_ricordo`, `public/assets/img/fin_ricordo.webp`; anteprima
    `docs/concept/finali_ricordo_anteprima.jpg`): il foglio sul banco di prua all'alba, bagnato e ondulato (le pieghe,
    gli orli che si alzano), la carta scurita dove ha bevuto l'acqua e la cera che la respinge in goccioline tonde
    (la maschera della cera si ricava dal disegno), qualche goccia sul banco, accanto il secchio vuoto; la borraccia
    spostata fuori dal quadro.
  - **La cinematica** (`FINALE_B`, 22 s, sul suono del finale A `madre_dawn_breve`): uguale al finale A fino al
    secchio che si svuota e ai figli che tornano giù (0-12 s); niente radio: la vista scende sul banco di prua mentre
    sorge il sole e lì (14,6 s) si dissolve nel disegno, poi va piano verso i quattro bambini e infine il nero.
    **Niente frase** (c'era «Il quarto eri tu. L'unico che è tornato a casa.», tolta per scelta dell'utente il 12
    ottobre): solo il disegno che si avvicina. Poi i risultati («Quota raggiunta»), senza titoli di coda. Il segnaposto `Screens.extraEnding` non c'è più. In sviluppo `?finale=B` lo
    forza alla notte extra. La clip: `docs/concept/clip/finale_ricordo.mp4` (solo il canvas: le scritte non ci sono).

### Le ultime inquadrature dei due finali segreti

> **Da approvare** (11 ottobre): solo le anteprime, a pochi campioni (1600×900, 24 campioni); i render finali si
> fanno dopo l'approvazione. Script: `tools/render/finali.py` (`tools/.venv/bin/python tools/render/finali.py
> [molo|edicola] [--fast]`).

Due immagini fisse, 16:9, che il motore mostra alla fine della cinematica con un lento movimento di camera. Nel
finale saranno 2560×1440, codificate come i jumpscare (`post.encode_light_pass` con la sua scala, webp) in
`public/assets/img/fin_molo.webp` e `fin_edicola.webp`, con la voce `endings.<scena>` in `overlays.json` (file,
scala, proporzioni ed esposizione); il comando è lo stesso con `--finale`.

- **«I tuoi» — il molo all'alba** (`docs/concept/finali_molo_anteprima.jpg`). **Approvato l'11 ottobre** (seconda
  anteprima); **render finale fatto**: `public/assets/img/fin_molo.webp` (2560×1440, 256 campioni), voce
  `endings.molo` in `overlays.json` (scala 6, esposizione +0,2 EV da dare al tonemap del motore). Un molo di legno nuovo sotto il
  paese, a sinistra del campanile: la costa, il paese, il faro, i faraglioni e il parco sono quelli della baia
  (`env.py`, `landmarks.py`), spostati e girati in modo che il gozzo del gioco (`boat.py`, senza il pescatore,
  lampara spenta, secchio vuoto) sia ormeggiato al molo con due cime e i parabordi. La camera sta in cima al molo,
  dalla parte della riva, e guarda verso il largo: il sole appena sorto sopra le colline del parco, il mare rosa,
  la ruota panoramica lontana. Sulle assi umide di rugiada, le **sette file di impronte bagnate** salgono dalla
  scaletta in fondo al molo e vengono verso la camera, cioè verso il paese che sta alle sue spalle: col sole
  davanti, quelle nella sua scia brillano, le altre sono scure sul legno chiaro. Le impronte, come proposte:
  - **Gulpy**: palmate, tre dita lunghe a ventaglio con la membrana a festoni;
  - **Molly**: piedini nudi da bambina, cinque ditini;
  - **Hatch**: scarpette da bambino col battistrada, piccole ma col passo lunghissimo (lui è altissimo);
  - **Robin**: tante zampette a puntini, a ventaglio, e la coda che striscia in mezzo;
  - **Lampy**: gli anelli della ventosa coi denti da latte dentro, distanziati, come una sanguisuga che cammina;
  - **Fangy**: graffi sottili e lunghi degli artigli, con le nocche;
  - **Archie**: una scia che serpeggia, continua.

  Attorno a dove sono saliti, gocce. Le impronte sono una maschera dipinta (4 mm per pixel) sotto il materiale delle
  assi, un po' più grandi del vero (×1,3) per leggersi da in piedi: dove è bagnato il legno è quasi nero e lucido, e
  riflette come l'acqua. Così si leggono tutte e sette, anche fuori dalla scia del sole (seconda anteprima, 11
  ottobre).
- **«Nessuno» — l'edicola da vicino** (`docs/concept/finali_edicola_anteprima.jpg`). **Approvata l'11 ottobre**;
  **render finale fatto**: `public/assets/img/fin_edicola.webp` (2560×1440, 256 campioni; la foto nella Polaroid
  rifatta a 900 px), voce `endings.edicola` in `overlays.json` (scala 0,43, esposizione 0); decodificata:
  `docs/concept/finali_edicola_finale_decodificata.jpg`. L'edicola votiva dello scoglio
  (la stessa del binocolo: `landmarks.build_chapel` e `binocolo.lore_photos`) nella luce grigia di un mattino coperto.
  **La tua foto** (proposta): una **Polaroid nuova**, l'unica non sbiadita, appesa con una molletta di legno a uno
  spago teso fra le due pareti, sul davanti dell'edicola. L'inquadratura è stretta su di lei (un medio tele a un metro
  e un quarto, f/1,4): la Polaroid è a fuoco e occupa circa un quarto dell'altezza del quadro; dietro, più di un metro
  più in là, le foto dei bambini del 1997 e i teschi sono macchie di colore sbiadito nelle cornici (le foto pensate per
  il binocolo, da vicino, sembravano grezze; così non si rifanno). I lumini restano fuori dall'inquadratura. Dentro la
  Polaroid, la barca di notte con la lampara accesa e la sagoma del pescatore col berretto, vista da sotto, dal pelo
  dell'acqua, a sinistra di poppa, come da qualcuno che nuotava lì accanto: è un render vero della scena del gioco
  (il pescatore, che nel gioco proietta solo l'ombra, qui si vede), passato in colori da Polaroid (neri slavati,
  grana, vignetta). La Polaroid è grande come una vera (8,8×10,7 cm).

**Da decidere**: le impronte una per mostro come sopra; la Polaroid (cosa c'è nella foto, e lo spago con la molletta
davanti all'edicola). Nell'anteprima del molo il paese non si vede (è alle spalle della camera): le impronte vanno
verso di lui.

