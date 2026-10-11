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
della prima, o con `?notte=2` nell'indirizzo (prove). Robin ora si vede (strato `robin_secchio`, 10 ottobre): sale dal
mare sul bordo, nella luce trema e si accende di rosso, scacciato scivola giù; prima si sentiva soltanto (suoni provvisori fatti con i file di scena:
zampette, secchio che tintinna, pesce strappato, fuga in acqua) e si vede sul sonar. Il jumpscare (11 ottobre, render
finale messo nel gioco come chiesto, «se ti convince mettilo»): a secchio vuoto molla il bordo e ti salta in faccia a
mani vuote, le arcate aggrottate, la mano lunga con le dita aperte; una luce calda dalla parte della lanterna, solo su
di lui, gli prende la faccia mentre arriva (la lampara gli sta alle spalle). L'urlo è ancora quello sintetizzato. I testi della notte 2 (radio, le due morti, sottotitoli, suggerimento, «Batteria morta.»),
accorciati e resi più criptici come chiesto, sono **approvati** (`src/i18n.ts`).

## I quattro mostri nuovi

> **Animazioni sulla barca** (10 ottobre, decise dall'utente): come Gulpy (la mascella lenta), Molly (sbatte gli
> occhi), Hatch (la bocca che conta) e Robin (sbatte gli occhi), **ognuno dei prossimi mostri avrà una piccola
> animazione** quando è in scena: da progettare insieme al modello. Proposte legate a come si gioca ognuno
> (*da approvare*): **Archie** prende fiato nella trombetta, che si srotola a metà e si riavvolge (il
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
- **Modello e posa** (*da approvare*, 10 ottobre; `tools/render/archie.py`, posa `archie_soffia` in
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
  centimetri dal vetro. Per il risucchio una toppa in più (*da approvare*), `archie_fiato`: la gola si gonfia come un
  pallone mentre prende fiato (nel gioco può seguire il risucchio, da 0 a 1). Nelle toppe si vede anche il collo
  dietro la testa e il riquadro sta sulla testa: la spirale che si srotola lascia vuoto il suo posto, e il gioco
  sfuma lo strato principale dove la toppa è vuota, come per le mascelle di Gulpy e Hatch.
- **Jumpscare** (*da approvare*; `jumpscare.py`, `ATTACKS['archie']`; anteprima
  `docs/concept/jumpscare/js_archie_fotogrammi.jpg`): il vetro è esploso e la lampara è spenta (nella scena non c'è
  più il vetro, la reticella e la lampadina di servizio non fanno luce). Nel buio si vedono solo i suoi occhi che
  brillano, come nel gioco a lampara spenta; la trombetta si è riavvolta di scatto, si stacca dalla lampara e ti
  arriva in faccia di tre quarti, il muso che ti passa accanto a sinistra con le zanne. Lo illuminano la luna alle
  spalle, la lanterna e una luce calda dalla parte della lanterna che tocca solo lui (come per Robin), così la faccia
  esce dal buio man mano che arriva.
- **Render finali** (10 ottobre, in attesa dell'approvazione ma già usabili): `archie_soffia` con gli occhi nel
  manifest (al buio brillano come quelli degli altri), e le toppe `archie_fiato`, `archie_trombetta_mezza`,
  `archie_trombetta_tutta`, in `public/assets/img` con le chiavi che il gioco già aspetta. Il jumpscare finale è nel
  gioco (11 ottobre, 64 campioni: con la scossa e la grana del nastro non si vede la differenza).
- **Nel gioco** (10 ottobre, notte del lavoro; tutto *da approvare*): la notte 3 si gioca (`?notte=3`, o Alt + 3 sul
  titolo nelle build di prova). Archie sale dall'acqua in 3 s (il sonar lo annuncia davanti alla prua), poi il
  risucchio dura 4,5 s: la gola si gonfia, la trombetta resta arrotolata, si sente il fiato al contrario. Se alla
  fine la lampara è accesa (anche bassa) soffia: la trombetta si distende sul vetro, il vetro esplode (la lampara
  non si riaccende più: «Il vetro è rotto.») e un attimo dopo il jumpscare. Se l'hai spenta, la gola si sgonfia in
  un sospiro e aspetta al buio 7 s, l'occhio acceso, prendendo fiato a metà nella trombetta; poi si rituffa. Se la
  riaccendi prima riprende fiato più in fretta (2,2 s). Quando canta la Madre si rituffa anche lui. Robin e Archie
  non vengono mai insieme (vogliono il contrario dalla luce). Quota 11 pesci. Giocatori simulati
  (`npm run sim -- 3 300`): esperto 100%, medio 71%, maldestro 50% (la seconda notte 100/81/58). Suoni provvisori
  sintetizzati (l'acqua che si apre, il risucchio, la trombetta che si sgonfia, il soffio e il vetro, il tuffo).
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
- **Modello e posa** (*da approvare*, 10 ottobre; `tools/render/lampy.py`, posa `lampy_lenza` in
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
- **La lenza nel gioco** (*da approvare*): la disegna il motore come sempre, ma per i punti della posa: dalla punta
  della canna alla bocca, sotto l'arco fino alla ventosa della coda, poi giù in mare (`scena_creature.lampy_lenza_punti`;
  dall'occhio in `tools/render/cache/lampy_posa.json`). Lampy ha tirato la lenza: il galleggiante è sott'acqua.
- **Sulla barca** (l'animazione proposta: apre e chiude piano la ventosa, con gli anelli di denti che girano): nel
  modello ci sono le due parti, `bocca` (da 0, chiusa a bacio stretto sulla lenza, a 1, spalancata a disco come
  quella della lampreda; nella posa 0,5, la bocca della tavola) e `denti_giro` (gradi: gli anelli vicini girano in
  versi opposti, come una macina). Cambia solo la testa, il corpo resta lo stesso: le toppe si fanno come per Robin.
  La vetrina mostra la ventosa chiusa, a riposo e spalancata.

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
- **Modello e posa** (*da approvare*, 10 ottobre; `tools/render/fangy.py`, posa `fangy_ascolta` in
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
  occhi. Da decidere: nello strato le lucine accese, come adesso, o spente (`luci`), lasciando tutta la luce al
  motore. La vetrina mostra la testa girata dalle due parti e le lucine spente.
