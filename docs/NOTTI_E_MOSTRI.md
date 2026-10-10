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
  consuma un po'. La carica basta per tenere la lampara bassa tutta la notte, non alta.
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
  c'è Molly.
- La radio spiega la batteria e Robin in poche frasi; due o tre oggetti di lore nuovi da pescare.

### Stato nel gioco (10 ottobre)

La notte 2 si gioca: dal menu con **Continua** dopo aver vinto la prima, con **Notte successiva** alla fine
della prima, o con `?notte=2` nell'indirizzo (prove). Robin visibile è in arrivo (modello approvato, strato in
render); finché lo strato non c'è, Robin si sente soltanto (suoni provvisori fatti con i file di scena:
zampette, secchio che tintinna, pesce strappato, fuga in acqua) e si vede sul sonar; il jumpscare è un urlo
sintetizzato. I testi della notte 2 (radio, le due morti, sottotitoli, suggerimento, «Batteria morta.»),
accorciati e resi più criptici come chiesto, sono **approvati** (`src/i18n.ts`).

## I quattro mostri nuovi

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

### Notte 4 · Lampy — *NON FERRARE*

- **Da dove viene**: la lampreda (la bocca a ventosa piena di anelli di denti).
- **Dal parco**: una cuffia da piscina di gomma a fiori, tirata sulla testa tonda.
- **Da bambino**: in piscina ti tirava giù per le gambe, per scherzo. Ora **tira la lenza**.
- **Come si gioca**: fa suonare il campanellino come un'abboccata. Le abboccate vere sono irregolari; le
  sue hanno un ritmo **perfetto**, tre colpi uguali, e sotto, nell'acqua, una risatina. Se ferri, hai
  agganciato lei: risale la lenza fino alla canna, jumpscare. Se aspetti, lascia la lenza e sparisce.
- **Il segnale** (scelto): tutti e due, il ritmo perfetto e la risatina.
- **Sagoma** (scelta): C «Sanguisuga», un arco di carne attaccato alla lenza per i due capi, ma più grosso.

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
