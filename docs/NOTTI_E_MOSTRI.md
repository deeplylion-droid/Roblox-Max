# Le notti e i mostri nuovi

> **Deciso il 10 ottobre**: sette mostri in tutto, uno nuovo per notte (Robin, Archie, Lampy, Fangy, in
> quest'ordine); la Madre è il finale della notte 6; nelle notti avanzate tornano tutti i mostri già visti
> e la regia decide quanti insieme; la batteria arriva con Robin nella notte 2.
> **Sagome scelte**: Robin **A «Granchio»**, Archie **C «Periscopio»**, Lampy **C «Sanguisuga»** (ma più
> grosso), Fangy **B «Mastino»** (`docs/concept/*_sagome.png`). La batteria è approvata così; il segnale di
> Lampy è **sia il ritmo perfetto sia la risatina**.
> **Ancora da scegliere**: le teste dei quattro mostri. Niente di questo è ancora nel gioco.

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
la sua regola. Sono allungati, magri e sproporzionati come Gulpy, Molly e Hatch, con la stessa pelle
grigia e bagnata e la stessa melma. **Non parlano** (l'unica eccezione resta la conta di Hatch).

## Notte 2 — La batteria

- Una **batteria d'auto** con un voltmetro ad ago. Per la nota dell'utente (niente oggetti nuovi dove si
  vedono i jumpscare già renderizzati) non sta più sul pagliolo ma **sul banco di prua, a destra del
  secchio** (circa 26° a destra), con i cavi che corrono lungo lo scafo fino al palo della lampara e il
  voltmetro su una staffa girato verso il pescatore: la vedi guardando il secchio. Niente barre sullo
  schermo. *Da approvare*: `docs/concept/batteria_anteprima.jpg` e `batteria_vicino.jpg`.
- **Nel gioco** l'ago lo disegna il motore sopra il quadrante renderizzato: nel rosso esattamente quando la
  carica scende sotto la soglia bassa (15%), cala un poco con la lampara alta (la batteria sotto sforzo),
  trema appena; a batteria morta batte sul fermo.
- La **lampara** consuma secondo il livello (spenta niente, bassa poco, alta molto); il **sonar** aperto
  consuma un po'. La carica basta per tenere la lampara bassa tutta la notte, non alta.
- Quando l'ago scende nel rosso la lampara comincia a tremolare.
- **Quando la batteria muore** si spengono lampara e sonar. Dal fondo, piano, sale la ninna nanna della
  Madre (quella del menu, al carillon). Se suonano le sei prima che la canzone finisca, sei salvo; se
  finisce prima, la Madre sale. È il momento di Freddy quando salta la corrente in FNAF, con la nostra
  canzone. Nel gioco la canzone è proprio `mus_title` (64 secondi, quanto il tempo che ti resta): parte
  ovattata e si apre salendo; se finisce, un tonfo enorme sotto la barca, la barca che sobbalza, il tema
  della Madre e il buio.
- **La scelta di ogni minuto**: la luce attira i pesci (serve per la quota) e scaccia Robin, ma costa. Al
  buio si pesca poco e le creature arrivano più vicine prima che te ne accorga.
- **Quota 10 pesci** (prima notte 8). Gulpy, Molly e Hatch tornano più spesso; Hatch può arrivare mentre
  c'è Molly.
- La radio spiega la batteria e Robin in poche frasi; due o tre oggetti di lore nuovi da pescare.

### Stato nel gioco (10 ottobre)

La notte 2 si gioca: dal menu con **Continua** dopo aver vinto la prima, con **Notte successiva** alla fine
della prima, o con `?notte=2` nell'indirizzo (prove). C'è tutto tranne **Robin visibile**: finché non è
scelta la testa e fatto il modello, Robin si sente soltanto (suoni provvisori fatti con i file di scena:
zampette, secchio che tintinna, pesce strappato, fuga in acqua) e si vede sul sonar; il jumpscare è un urlo
sintetizzato. *Da approvare*: la chiamata alla radio della notte 2, i sottotitoli dei suoni nuovi, il
suggerimento per Robin, il messaggio «La batteria è morta.» (`src/i18n.ts`, segnati ⚠️).

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

### Notte 3 · Archie — *SPEGNERE LA LUCE*

- **Sagoma** (scelta): C «Periscopio», un collo sottilissimo che sale dritto dall'acqua, la testa in cima
  piegata verso la luce.

- **Da dove viene**: il pesce arciere, che sputa getti d'acqua per far cadere gli insetti dalle foglie.
- **Dal parco**: la pistola ad acqua arancione del negozio, fusa nel braccio.
- **Da bambino**: sfidava tutti a duello con la pistola ad acqua. Ora **mira alla lampara**.
- **Come si gioca**: un ticchettio sull'acqua, poi un sibilo che si carica: vuole spegnere la tua luce.
  Devi **spegnere la lampara** prima che spari e restare al buio finché non si rituffa. Se spara con la
  lampara accesa il vetro della lampara esplode e nel buio Archie ti è addosso: **jumpscare** (nota
  dell'utente: non deve limitarsi a spegnerti la luce).
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
