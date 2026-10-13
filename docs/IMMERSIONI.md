# Le immersioni all'alba

> **Proposta scritta dell'11 ottobre** (idea dell'utente), **approvata l'11 ottobre** con una modifica: solo la
> grotta grande si esplora a 360°; le camerette delle tane sono **inquadrature fisse**, che si girano di 30° a destra
> e a sinistra, come le telecamere di FNAF. Il motore e le grotte si preparano già in parallelo; le notti restano la
> priorità (prima si finiscono le sei).
>
> **Già deciso dall'utente (11 ottobre)**: un pesce per notte; la tana del mostro nuovo della notte dopo è vuota
> (è già in giro); due tane per immersione; niente pericoli, ma atmosfera inquietante; i tunnel sono **grotte
> naturali**, il resto l'ha fatto la Madre; le bombole compaiono perché all'alba il pescatore le tira fuori dalla
> **cambusa**.

## Perché

In FNAF la varietà viene dalle telecamere: tante stanze diverse. Qui la notte resta sulla barca (è il nostro
ufficio), e la varietà arriva fra una notte e l'altra: sott'acqua ci sono le tane dei mostri, ognuna una cameretta
sommersa piena della vita di quel bambino. Le tane raccontano la storia meglio di qualsiasi testo, e danno un senso
ai pesci in più (oggi a fine notte non servono a niente).

## Come si gioca

- **All'alba** (dopo ogni notte vinta, dalla prima alla quinta): sulla barca, accanto al banco, ci sono le bombole
  che il pescatore ha tirato fuori dalla cambusa. Si può **scendere** o passare subito alla notte dopo
  (l'immersione è facoltativa).
- **L'aria** basta per **due tane** (la tana vuota del mostro nuovo non conta). **Niente indicatore** (deciso l'11
  ottobre sera): quando lasci la seconda tana compare «Aria finita: risali.» e si risale da soli.
- **Niente pericoli**: i mostri dormono. Si muovono nel sonno, respirano, fanno bolle, qualche volta sembrano
  svegliarsi, ma non succede niente. Solo atmosfera.
- **Il pesce**: se alle sei avevi più pesci della quota, **uno** te lo porti giù e lo puoi lasciare accanto a **uno**
  dei mostri addormentati. Quel mostro la notte dopo **non viene** (ha mangiato, resta a dormire). Un solo pesce per
  alba, a un solo mostro; gli altri pesci in più restano alla Madre.
- **Il mostro nuovo** della notte dopo non si può sfamare: la sua tana è **vuota**, è già in giro. La vedi prima di
  incontrarlo, con gli indizi su chi è (la cuffia a fiori di Lampy, gli occhialini di Fangy, la trombetta di Archie).
- Quello che trovi nelle tane (disegni, foto, oggetti) va nel diario, come le altre scoperte.

## Le grotte

Grotte naturali scavate dal mare sotto lo scoglio dell'edicola: roccia nera, anemoni, banchi di pesciolini che
scappano dalla torcia, alghe che ondeggiano. Dentro, i pezzi del parco che la Madre ha trascinato giù (boe, pezzi di
scivoli, cartelli di Splashland).

- **Sotto la barca**: la cima dell'ancora che scende nel buio; nella parete di roccia, l'imboccatura della grotta.
- **La grotta grande**: una sala con un'apertura per ogni tana (proposta: a ogni apertura una cosa del bambino
  appesa alla roccia, così le riconosci). Notte dopo notte se ne aggiungono, man mano che arrivano i mostri nuovi.
- **Il fondo della grotta grande** (proposta): un'apertura enorme e buia da cui si sente respirare qualcosa di
  gigantesco. Non ci si entra: è la Madre, e prepara la notte 6.
- **Come ci si muove** (deciso l'11 ottobre): la **grotta grande** è un panorama a 360° in cui ti guardi attorno con
  la torcia e clicchi l'apertura della tana dove vuoi andare (dissolvenza con le bolle e il respiro
  dell'erogatore). **Ogni cameretta è un'inquadratura fissa**, come una telecamera di FNAF: la guardi da un punto
  solo e la puoi girare di 30° a destra e a sinistra; da lì si torna alla grotta grande.

### Sotto la barca (inquadratura fissa, anteprima **approvata** l'11 ottobre sera)

Deciso l'11 ottobre sera: non è più a 360°, è un'inquadratura fissa come le camerette (si gira di 30° a destra e a
sinistra e di pochi gradi in su e in giù). Scena in `tools/render/sotto_barca.py`, la stessa roccia, luce e acqua
della grotta. Il sub galleggia 3,4 m sotto la superficie, 8 m dietro la poppa, e guarda avanti un po' in su:

- in alto, la **chiglia della nostra barca** (quella vera di `boat.py`, con l'opera viva scura e la lampara spenta)
  contro la superficie chiara e mossa dell'alba, con i raggi che scendono;
- dalla prua, la **cima dell'ancora** che scende obliqua davanti al sub, con qualche filo d'alga impigliato, e si
  perde nel buio in basso;
- davanti, la **parete sommersa dello scoglio** con l'**imboccatura della grotta**, un buco nero di 6 m (si clicca
  per andare alla grotta grande).

Anteprime: `docs/concept/sotto_barca_anteprima.jpg` (come la vede il gioco, 90° in orizzontale) e
`sotto_barca_anteprima_larga.jpg` (124°: tutto il campo in cui si gira).

**Il render finale** (job `sotto`): un panorama parziale come le camerette, coi numeri del segnaposto del motore:
160° × 95° (`lonMin`/`lonMax` ±80°, `latMin` −45°, `latMax` +50°), 3640 × 2162 (la stessa densità della grotta
grande), centrato sulla direzione in cui guarda il sub; `frame` con `yawRange` 30 e `pitchRange` 6. Stessa codifica
della grotta grande (acqua cotta, passo dati come il mondo, B = la superficie). File in
`public/assets/img/immersioni/sotto_barca_*.webp` e la voce del posto in `sotto_barca_posto.json`, con le direzioni
vere: l'imboccatura (`cave`: yaw 12,1°, pitch −14,5°, raggio 9,3°) e la cima dell'ancora vicino alla prua (`ascend`:
yaw −6,6°, pitch 12,2°), che nella scena sta appena a sinistra del centro, non a −28° come nel segnaposto; il
`frame` ha pitch 6,4° (lo sguardo del sub). Nel finale la parete gira attorno al sub come un'insenatura,
così ai lati dell'inquadratura non ci sono più spigoli squadrati.

### La grotta grande (anteprime **approvate** l'11 ottobre sera; render finale del panorama)

Scena in `tools/render/grotte.py`, job in `tools/render/jobs.py`:

| Job | Cosa fa |
|---|---|
| `grotte_anteprime` | tre viste prospettiche: `docs/concept/grotte_anteprima_insieme.jpg` (la sala da sotto il pozzo, verso la Madre), `grotte_anteprima_madre.jpg` (la tana della Madre dall'occhio, con la torcia), `grotte_anteprima_torcia.jpg` (la torcia sulla bocca di Gulpy) |
| `grotte_tane` | la tavola delle sette bocche da vicino, con la torcia: `docs/concept/grotte_anteprima_tane.jpg` |
| `grotte` | il panorama a 360° della sala nel formato del motore delle immersioni (sfera intera): `public/assets/img/immersioni/grotta_grande_{ambient,lantern,data}.webp` e la voce del posto `grotta_grande_posto.json` (da copiare in `immersioni.json`). Il primo giro, in qualità preview e nel formato del mio strato, è quello di `docs/concept/grotte_panorama.jpg` |
| `sotto_anteprima` | l'anteprima veloce di «sotto la barca» (vedi sotto) |
| `grotte_ricomponi` | rifà le anteprime dagli EXR in cache senza rendere (per provare l'acqua o l'esposizione) |

**Com'è fatta.** Una sala naturale di circa 14 × 20 m e 9 m d'altezza, scavata dal mare: un'unica roccia scolpita
come campo SDF (unione di ellissoidi, rumore per le bozze e le cengie orizzontali), quasi nera e lucida d'acqua,
con la patina d'alghe sulle facce in su e qualche chiazza rosata di alghe calcaree. Il fondo è sabbia grigia
increspata con i ciottoli e qualche masso caduto, e in fondo scivola giù nella tana della Madre. Dietro, in alto,
c'è il **pozzo** da cui si è scesi: da lì entra l'alba (un faretto con le caustiche e i raggi nell'acqua), e in
cima si vede la superficie chiara. Sulle pareti, a gruppi, anemoni pallidi e spugne a tubo spente; ciuffi di alghe a
nastro sul fondo e sulle cenge; due banchi di pesciolini argentati (uno gira in tondo a mezz'acqua, uno fila lungo la
parete destra); la neve marina sospesa (solo nelle anteprime: nel gioco la fa il motore).

**I pezzi del parco** (proposta): tre boe bianche e rosse (una sul fondo, una che galleggia trattenuta dalla sua
cima, una incastrata sotto il soffitto); tre pezzi di scivolo a tubo coi colori di quelli del parco (giallo sul
fondo, blu che sale contro la parete, rosso spezzato sull'orlo della tana della Madre); il **cartello
SPLASHLAND** (insegna verde acqua con le lettere fucsia, il carattere dell'insegna del parco) inclinato e mezzo
sepolto nella sabbia.

**Le bocche delle tane** (proposta: posizioni e oggetti). L'occhio del sub galleggia in mezzo alla sala; attorno,
da sinistra a destra nell'ordine in cui arrivano i mostri, sette bocche di tunnel che entrano dritti nella roccia e
poi piegano nel buio. A ognuna è appesa all'architrave la cosa del bambino, girata verso chi guarda (le cose piccole
sono più grandi del vero, da 1,2 a 1,7 volte, come la trombetta di Archie sul mostro, perché si leggano da lontano):

| Tana | Dove (yaw dall'occhio) | La cosa appesa |
|---|---|---|
| Gulpy | −128°, a mezza parete | il **salvagente a paperella** giallo, appeso per la testa della papera |
| Molly | −88° | due **ciocche bagnate coi codini**, legate dagli **elastici rosa** con le palline (la ciocca è un'aggiunta mia: gli elastici da soli sono troppo piccoli per leggersi; si possono togliere) |
| Hatch | −48°, bassa e stretta, quasi sul fondo (un nascondiglio) | il **pesciolino luminoso** del negozio, **acceso**: l'unica luce che non viene dal pozzo |
| Robin | +46° | la **striscia dei biglietti** della sala giochi, arancio, che pende attorcigliata |
| Archie | +88° | la **trombetta da festa** bianca e rossa, arrotolata |
| Lampy | +128°, alta, vicino al soffitto (dorme attaccata in alto) | la **cuffia di gomma bianca coi fiori** fucsia e rosa in rilievo |
| Fangy | −160°, dietro, vicino al pozzo | gli **occhialini con le lenti dipinte di nero**, appesi per l'elastico |
| **La Madre** | 0°, in fondo | nessun oggetto: un'apertura enorme (circa 7 m) sotto la parete di fondo, dove la sabbia scivola giù nel nero. La torcia non ci arriva. |

Le bocche delle tane che non ci sono ancora (i mostri che arrivano più avanti) per ora sono tutte aperte; il motore
potrà nasconderle con una toppa di roccia, o si fa un panorama per alba (da decidere).

**Le luci.** Due light group come la baia: `ambient` (l'alba dal pozzo, la luce diffusa dall'acqua, i raggi, il
pesciolino di Hatch) e `lantern` (la **torcia del sub**). Nel panorama la torcia è una luce puntiforme sull'occhio
che illumina tutto attorno: il motore la ritaglia con un cono attorno allo sguardo e la accende o spegne. Nelle
anteprime è un faretto sulla camera.

**L'acqua torbida.** Niente volume (su CPU costa troppo): il passo dati porta la distanza (mist lineare, 0
sull'occhio e 1 a 40 m) e dopo il render `grotte.acqua()` la cuoce nei passi di luce: l'assorbimento (il rosso
sparisce per primo, poi il verde) e la luce rimandata dall'acqua (una sfocatura larga della luce ambiente: vicino
al pozzo l'acqua brilla, in fondo alla tana della Madre resta nero). La torcia fa andata e ritorno e lascia una
scia chiara davanti al sub. I raggi sono coni emissivi trasparenti resi in un secondo passaggio leggero (se no
rovinerebbero il passo della distanza) e sommati dopo.

**Il panorama finale per il motore** (il formato di «Come si aggiungono i posti veri», sul branch del motore):
equirettangolare a sfera intera (`latMin` −90, `latMax` 90), 8192 × 4096; passi `ambient` e `lantern` (la torcia
sull'occhio, a metà risoluzione) codificati come gli altri render (gamma 4 con la loro `scale`); il passo dati come
quello del mondo: R = √(distanza / 2500 m), G = 0,1 (quanto trema), B = la superficie vista dal pozzo. **L'acqua
torbida approvata è già cotta nei passi** (`acquaCotta: true` nella voce del posto): perché resti com'è nelle
anteprime, la nebbia del motore in questo posto va tenuta bassa (con `GROTTE_ACQUA=0` il job dà i passi crudi, se
si preferisce farla fare tutta al motore). I passaggi (`links`) della voce del posto hanno le direzioni vere: le
sette bocche, la tana della Madre (`note: mother`) e il ritorno a «sotto la barca» dal pozzo, in alto dietro.
Si rende a strisce che restano in cache, così un riavvio del container non fa perdere il lavoro.

**Problemi aperti**: gli occhialini di Fangy sono ancora piccoli rispetto al loro elastico; la luce della torcia
nelle anteprime si nota poco (l'acqua chiara del pozzo la copre); l'arco della Madre potrebbe essere più nero (la
luce rimandata dall'acqua lo schiarisce); i raggi nel panorama sono tenui; le bocche dei mostri non ancora arrivati
sono tutte aperte (vedi sopra); il panorama non ha ancora le toppe animate (alghe che ondeggiano, pesci che si
muovono: si possono fare come strati a parte o nel motore).

**Approvati l'11 ottobre sera**, con le anteprime: l'aspetto della sala (roccia, colori, quanta vita), la luce del
pozzo e quanto è torbida l'acqua; i pezzi del parco e il cartello; la disposizione delle bocche; le sette cose appese
(soprattutto le ciocche di Molly); la tana della Madre così (solo buio, senza niente che si veda dentro).

## Le tane

Ogni tana è una cameretta rifatta dalla Madre con le cose del bambino, in una grotta laterale: il letto, i
giocattoli, le cose del parco, tutto sommerso, coperto di melma e di alghe. Ogni mostro ha la sua posa
addormentata, con una piccola animazione (il respiro, le bolle).

| Mostro | La cameretta | Come dorme |
|---|---|---|
| **Gulpy** | Il chiosco degli snack del parco smontato e rimontato: carte di merendine, cestini del pranzo, una pila di salvagenti a paperella. | Raggomitolato su un materasso di salvagenti, la mascella che pende aperta, fa bolle grosse a ogni respiro. |
| **Molly** | Il trampolino della piscina dentro la stanza, specchi dappertutto, le medaglie di nuoto, gli elastici rosa. | Su un fianco, abbracciata ai braccioli; l'occhio che scivola via resta socchiuso. |
| **Hatch** | Piena di nascondigli: armadi, una tenda fatta di asciugamani; i numeri della conta scritti sulle pareti. | Rannicchiato dentro un armadio aperto, l'esca del giocattolo che si accende e si spegne piano. |
| **Robin** | Un mucchio di cose rubate agli altri bambini (scarpe, giocattoli, oggetti smarriti del parco) e i biglietti della sala giochi. | Disteso sul mucchio come un granchio sul bottino, le zampe che si muovono nel sonno. |
| **Archie** | Una festa di compleanno sommersa: torte con le candeline spente, cappellini, palloncini che galleggiano, lo striscione degli auguri. | Avvolto come un serpente attorno al tavolo della festa; a ogni respiro la trombetta si srotola un poco. |
| **Lampy** | Una culla con la giostrina di pesciolini, una vaschetta da bagno, cuffie a fiori appese. | Attaccata con la ventosa al soffitto sopra la culla; non ha palpebre e dorme a occhi aperti. |
| **Fangy** | Bende per gli occhi, occhialini dipinti di nero, il gioco del Marco Polo; attorno al letto conchiglie appese che tintinnano quando ti avvicini (le sente anche nel sonno, ma dorme). | Raggomitolato, gli occhialini neri, le lucine del ventre quasi spente che respirano lentissime. |

### Le tane disegnate (12 ottobre, **approvate** il 13 ottobre)

Scena in `tools/render/tane.py`, anteprime col job `tane_anteprime`: `docs/concept/tane_camerette.jpg` (le sette
camerette vuote come le vede il sub entrando, con la torcia) e `docs/concept/tane_pose.jpg` (i sette mostri
addormentati da vicino). Sono bozze: mostri a risoluzione ridotta, pochi campioni.

Ogni tana è una grotta laterale di circa 9 × 8 m, alta 4-5 m, con la stessa roccia, sabbia, ciottoli, alghe e acqua
della grotta grande; il sub entra dal tunnel e guarda la stanza da un punto solo (inquadratura fissa, ±30°). La
cameretta senza il mostro è anche **la tana vuota** del mostro nuovo della notte dopo; il mostro addormentato è uno
strato sopra, con la toppa del respiro che si dissolve.

| Tana | Cosa c'è (proposta) | Come dorme (proposta) | La cosa da trovare (diario) |
|---|---|---|---|
| **Gulpy** | Lo Snack Shack rimontato a sinistra (bancone rosso, tenda a strisce, l'insegna, lo scaffale delle merendine), carte di merendine dappertutto, i cestini del pranzo, una pila di salvagenti a paperella. | Accasciato sulla pila di salvagenti, la schiena all'indietro, la mascella che pende aperta. | **Il menù dello Snack Shack** a pastelli, coi disegnini e i prezzi (resta scritto solo «HOT DOG»), tutto cerchiato in rosso con «!!!» (prima «TUTTO!»; approvato il 13 ottobre). |
| **Molly** | Il trampolino con la scaletta, gli specchi ossidati appoggiati alle pareti, le medaglie appese, la corsia galleggiante della piscina tirata da parete a parete, braccioli ed elastici rosa sulla sabbia. | Su un fianco sulla sabbia, abbracciata ai braccioli; un occhio chiuso, quello che scivola via socchiuso. | Una **foto**: lei in cima al trampolino con i braccioli, le braccia alzate («GUARDAMI! – giugno 1997»). |
| **Hatch** | Tre armadi con le ante spalancate, una capanna di asciugamani tra due sedie, i numeri della conta scritti col gesso sulle pareti. | In piedi, curvo, chiuso dentro l'armadio grande in fondo, la bocca chiusa, il pesciolino luminoso acceso. | **Il foglio della conta**: i numeri da 1 a 10 scritti e riscritti, e in mezzo «10!» (che si legge nel gioco ed è uguale in tutte le lingue) e sotto, piccolo, «CHI C'È C'È». |
| **Robin** | Un mucchio di cose rubate (scarpe, palline, giocattoli, secchielli) avvolto nelle strisce dei biglietti. | Disteso sul mucchio come un granchio sul bottino, gli occhi chiusi. | **I premi della sala giochi** a pastelli: l'orso da 5000 biglietti, la palla, la macchinina; lui davanti, nel fumetto «!!!» (prima «VOGLIO TUTTO»; approvato il 13 ottobre). |
| **Archie** | La festa: il tavolo tondo con la tovaglia, tre torte con le candeline spente, i cappellini sparsi, i palloncini che galleggiano legati al tavolo, lo striscione «HAPPY BIRTHDAY» (uguale in italiano e in inglese, deciso il 12 ottobre sera). | Avvolto in spire attorno al tavolo, la testa appoggiata sul bordo; a ogni respiro la trombetta si srotola un poco. | **Tutti i compleanni** del 1999: dodici torte, una per mese, con le fiammelle cancellate col nero. |
| **Lampy** | La culla con la copertina, la giostrina di pesciolini appesa alla volta, la vaschetta da bagno, le cuffie a fiori appese alla parete. | Attaccata con la ventosa al soffitto sopra la culla, a testa in giù; dorme a occhi aperti. | **Il braccialetto dell'ospedale** da neonata («KG 3,1»), con scritto «non lasciarla mai andare». |
| **Fangy** | Il letto con il lenzuolo, decine di conchiglie appese ai fili tutt'attorno, le bende per terra, gli occhialini dipinti di nero sullo sgabello, il cartello «MARCO? POLO!» e i tubi galleggianti. | Raggomitolato sul fianco sul letto, gli occhialini neri, le lucine del ventre quasi spente. | **«IO»**: lui disegnato con gli occhialini ripassati col nero finché la cera luccica. |

**Deciso dall'utente (12 ottobre)**, guardate le due tavole: l'idea va avanti. Le camerette dei mostri arrivati
dopo il 1997 sono **del loro anno**, come nei ritagli: Archie 1999, Lampy 2003, Fangy 2008 (Molly, Gulpy e Hatch
1997, la Night Splash; Robin senza data). **Hatch** non sta in piedi rigido nell'armadio (sembrava appeso): è
**rannicchiato in fondo all'armadio, le ginocchia al petto**, come un bambino nascosto a nascondino.

Correzioni per i finali (dalla sessione che coordina, 12 ottobre): Gulpy addormentato davvero, disteso sulla pila di
paperelle, occhi chiusi, mascella rilassata; Molly (il modello ha solo testa e mani) sotto una coperta di
asciugamani e braccioli, con fuori solo la testa e le mani; niente più scatole negli arredi (armadi con le ante, le
maniglie e il legno gonfio, lo sgabello, il letto col materasso e le lenzuola, il trampolino vero); ogni cameretta si
riconosce dall'ingresso anche dalle pareti (le piastrelle della piscina di Molly, la carta da parati a fiori strappata
di Lampy, le lucine della festa di Archie...); la macchia della torcia sulla sabbia più morbida; i disegni a pastelli
delle cose da trovare fatti con la stessa mano del disegno di «Il ricordo» e dei disegni dell'alba
(`tools/render/pastelli.py`), su soggetti diversi da quelli dell'alba.

**Approvati il 13 ottobre**: le sette cose da trovare e i loro testi (in italiano e inglese, nel gioco).

**Fatto per i finali (12 ottobre).** Arredi veri: gli armadi con le ante sui cardini, i riquadri, i pomelli e il
legno gonfio e imbarcato; le sedie e la capanna di asciugamani di Hatch; il letto di Fangy con la testiera a
colonnine, il materasso, il lenzuolo e il cuscino; lo sgabello; il trampolino vero di Molly (la tavola blu che si
piega, il fulcro, la scaletta coi corrimano). Le pareti di ognuna: le piastrelle della piscina e il cartello «3 M –
DEEP END» di Molly, i manifesti dello Snack Shack («ESTATE 1997») di Gulpy, i numeri e le tacche della conta col gesso
di Hatch, il cartello «OGGETTI SMARRITI» e il cabinato dei biglietti rovesciato di Robin, le lucine della festa e il
manifesto «MAGGIO 1999» di Archie, la carta da parati a fiori strappata e «BENVENUTA! – LUGLIO 2003» di Lampy, il
cartello «MARCO? POLO!», il calendario «AGOSTO 2008» e il salvagente di Fangy. La macchia della torcia sulla sabbia è
sfumata. Le pose: Gulpy disteso sul fianco sulla pila di paperelle, gli occhi chiusi (le palpebre abbassate sul
bulbo) e la mascella appena aperta, un salvagente grande dove finisce il modello; Molly sotto una coperta di
asciugamani a strisce tirata fino al mento, le mani che ne stringono l'orlo; Hatch rannicchiato in fondo
all'armadio, le ginocchia al petto e le braccia attorno alle gambe (`tane.corpo_rannicchiato`). I disegni a pastelli
(Gulpy, Hatch, Robin, Archie, Fangy) li fa `tools/render/disegni_tane.py` con `pastelli.py`; i soggetti non ripetono
quelli dei cinque disegni dell'alba (la piscina, il tesoro, la festa, sott'acqua, Marco Polo).

**Nel motore.** Ogni tana è un posto di `public/assets/img/immersioni.json` (il job `tane` lo aggiorna):

- `pano`: la cameretta **vuota** (panorama parziale, 3640 × 1820 a qualità finale: 160° × 80°, da −55° a +25°;
  per Lampy da −45° a +35°, perché dorme al soffitto), con l'acqua cotta (`acquaCotta`); vale anche come tana vuota
  del mostro nuovo;
- `frame`: lo sguardo a −15° (Lampy −5°), ±30° di lato, ±4° in su e in giù;
- `sleeper.layers`: la posa del mostro (strato ritagliato con l'alfa, la stanza gli fa da maschera) e la toppa del
  respiro (la stessa posa col fiato preso: la gola o il corpo appena gonfi, la mascella o la trombetta che si muovono,
  le lucine di Fangy più accese), con `breath`, il periodo in secondi (Fangy 6,5, lentissimo); `sleeper.yaw/pitch/r`
  dove si clicca per lasciare il pesce, `sleeper.bubbles` da dove salgono le bolle (sopra la testa);
- `find`: la cosa da trovare (`lore`: la voce del Diario `den_<mostro>`, `yaw`, `pitch`, `r`). Nel gioco compare il
  punto «Guarda»; cliccato, la cosa va nel **Diario** («Nel Diario: …») e non si offre più. Le sette voci stanno in
  `LORE` (`src/game/config.ts`, con `den`): **non si pescano** di notte. I testi, in italiano e inglese, sono in
  `src/i18n.ts` (`LORE_TEXT.den_*`, `dive.links.find`, `dive.found`), **approvati il 13 ottobre**.

Regole e salvataggio: `DiveRun.findHere()` e `take()` (le voci già nel Diario non si offrono), `DiveResult.lore`,
`afterDive` le aggiunge al Diario. Test in `tests/dive.test.ts`, `tests/save.test.ts`, `tests/sim.test.ts`. Il suono
della cosa trovata è `dive_found` (vedi sotto; approvato il 13 ottobre).

**Rifatte il 12 ottobre notte.** Hatch (le ante dell'armadio aperte verso fuori) e Archie (la tovaglia tonda che
ricade dal tavolo; lo striscione «HAPPY BIRTHDAY», uguale in tutte le lingue, orientato come il telo e con le lucine
sopra). Poi, una tana alla volta:

- **Le scritte** (docs/LOCALIZZAZIONE.md: niente italiano leggibile nelle scene, scritte inglesi come le insegne del
  parco o neutre, così non si rifà un render per lingua): Gulpy «ICE CREAM / SUMMER 1997» e «FRIES»; Hatch «10!» nel
  foglio della conta (e «CHI C'È C'È» con l'accento: la È è in `pastelli.py`), il Diario cita «10!»; Robin «LOST &
  FOUND»; nel sorgente, per i render futuri, Archie «PARTY / MAY 1999», Lampy «WELCOME! / JULY 2003», Fangy «EYES
  CLOSED!» e «AUGUST». Anche i disegni a pastelli delle tane ancora da rifare
  perdono le parole italiane (scelta approvata il 13 ottobre): il menu di Gulpy tiene «MENU» e «HOT DOG», il resto
  sono disegnini e prezzi, e al posto di «TUTTO!» c'è «!!!»; il fumetto di Robin dice «!!!» invece di «VOGLIO TUTTO».
  Il Diario descrive i disegni come sono. Restano, nelle tane già fatte e illeggibili nel gioco, «IO» di Fangy e le
  iniziali dei mesi di Archie.
- **Molly**: la foto è caduta sulla sabbia davanti al trampolino (sopra la tavola, all'altezza degli occhi, si vedeva
  di taglio), con «6 / 1997»; la coperta ha le strisce. Le strisce non comparivano in nessun telo
  (`strisce_material`: la soglia era fissa a 0,5 e il passo più corto): ora sì anche negli asciugamani di Hatch, e nella
  tenda di Gulpy e nella tovaglia di Archie al prossimo render.
- **Lampy**: il cartoncino del braccialetto rosa acceso (bianco spariva sotto la torcia), legato al corrimano davanti
  della culla, verso chi entra: «3100 g – 7 / 2003» (numeri neutri, 13 ottobre); le parole («non lasciarla mai andare») stanno nel Diario.
- **Robin**: il braccio lungo raccolto nel sonno (il gomito alto ripiegato, il pugno sotto il mento); il cabinato dei
  biglietti caduto sul fianco ma con la faccia verso chi entra: il cartellone «TICKETS» acceso, lo schermo verde, la
  plancia con la leva e i pulsanti, lo sportello delle monete, la striscia di biglietti che esce e si arrotola sulla
  sabbia (`tane.cabinato`). Il disegno da trovare è dall'altra parte del mucchio.
- **La cosa trovata** ha un suo suono, `dive_found` (docs/AUDIO.md): la carta fradicia fra le dita, un gonfiore grave
  e sordo, la roccia lontana; non un premio.

**Lampy resta con la sua inquadratura** (da −45° a +35°, sguardo a −5°): dorme attaccata al soffitto sopra la culla,
a 3,5 m (la posa approvata), e con l'inquadratura delle altre (fino a +18° in alto) il soffitto e lei sarebbero fuori
campo. Per portarla come le altre bisognerebbe abbassarla di un metro abbondante, attaccata a qualcos'altro (la
corda della giostrina, una trave). **Decisione dell'utente del 13 ottobre: resta così**, appesa al soffitto con la sua
inquadratura.

### Il pesce lasciato nella tana (13 ottobre, **approvato**)

Dopo «Lascia il pesce» il pesce compare sulla sabbia davanti al letto (in poco più di un secondo) e resta lì se torni
nella tana durante la stessa immersione. È uno strato sopra il mostro che dorme, `sleeper.fish` del posto in
`immersioni.json` (`tana_<mostro>_pesce_ambient.webp` e `_lantern.webp`), fatto col job `tane_pesce`
(`tools/render/jobs.py`, `tana_pesce`; `TANE=molly,lampy` per rifarne solo alcune):

- **Il pesce** è il pagello del Catalogo (`pesci.costruisci('pagello_pixelato')`: in 3D è un pagello come gli altri, il
  glitch a quadretti è solo nell'immagine del Catalogo), lungo mezzo metro con la coda (più piccolo, a quattro metri
  dall'occhio, quasi non si vedeva), coricato sul fianco con il muso verso il letto, il dorso rosa verso chi entra
  (dall'altra parte si vedeva il ventre bianco) e il fianco di sopra girato di 12° verso di lui, come sulla sabbia non
  piana.
- **Il posto si sceglie da solo**: sabbia libera e piana davanti al letto, verso l'ingresso e un po' di lato (niente
  sassi, coriandoli o arredi sotto: la sabbia si tasta ogni 4-5 cm, se no un sassolino bucava il pesce), visibile
  dall'occhio con la sabbia davanti (se no sembra in bilico sul sasso che lo copre), dentro l'inquadratura, fuori dal
  mostro e lontano dalla cosa da trovare.
- **Tre render del riquadro** con la camera della cameretta: il pesce da solo (stanza e mostro fanno da maschera:
  il colore e la copertura), poi la stanza intera con il pesce e senza. Dal confronto viene **l'ombra** che il pesce fa
  sulla sabbia: nello strato è nera con l'alfa dell'ombra e scurisce la cameretta sotto. La luce viene dall'ingresso,
  alle spalle del sub, e l'ombra vera resta quasi tutta nascosta dietro il pesce: c'è anche un'ombra morbida di
  contatto sotto il pesce, così sta appoggiato e non incollato sopra l'immagine. L'acqua si cuoce come per il mostro
  (la luce sfocata della stanza viene da un render piccolo della cameretta intera).

## Il pesce e i finali

Il pesce lasciato nelle tane decide anche **il finale della sesta notte** (approvato l'11 ottobre, vedi
`docs/NOTTI_E_MOSTRI.md`, «I finali»): un pesce **a ogni alba** porta al finale segreto **«I tuoi»**; scendere almeno
tre volte senza lasciarne **mai** uno porta al finale segreto **«Nessuno»**; tutto il resto al finale A. Il
salvataggio deve quindi ricordare, alba per alba, se sei sceso e se hai lasciato il pesce.

## Cosa serve

- **Motore**: la modalità immersione (panorami collegati, la torcia, l'acqua torbida con le particelle e i raggi di
  luce, le bolle dell'erogatore), l'offerta del pesce (si clicca il mostro tenendo il pesce),
  la schermata dell'alba con la scelta, i salvataggi (chi hai sfamato, le tane viste).
- **Render**: il panorama a 360° della grotta grande, l'inquadratura fissa sotto la barca (11 ottobre sera), sette camerette come
  inquadrature fisse larghe abbastanza da girarle di 30° per parte, sette pose addormentate con le loro toppe.
- **Suoni**: l'ambiente sott'acqua, l'erogatore, il respiro nel sonno di ognuno, le conchiglie di Fangy.
- **Simulazione**: il mostro sfamato non arriva, ma la regia conta i suoi tempi (il fantasma, 13 ottobre); il bot
  sfama il più pericoloso.

## In che ordine

1. Prima le sei notti (deciso l'11 ottobre).
2. Un prototipo con la sola tana di Gulpy: l'alba con le bombole, la discesa, la grotta grande, Gulpy che dorme, il
   pesce lasciato accanto al letto, la notte dopo senza di lui.
3. Se convince, le altre tane una alla volta, nell'ordine in cui arrivano i mostri.

## Il motore

> **Fatto l'11 ottobre, con contenuti segnaposto.** Il motore, il flusso, la simulazione e il salvataggio ci sono;
> i panorami sono **finti** (grotte procedurali e una «cameretta» qualsiasi, brutti di proposito) finché non
> arrivano i render veri delle grotte e le camerette approvate.
>
> **Decisioni dell'utente, 11 ottobre sera**: approvati le anteprime della grotta grande, i 26 suoni delle
> immersioni e i testi; **niente indicatore dell'aria** (via il manometro, l'avviso e la riserva: uscendo dalla
> seconda tana compare «Aria finita: risali.» e si risale da soli; nella seconda tana il respiro dell'erogatore
> diventa affannoso, approvato poco dopo); la **tana vuota** del mostro nuovo **non costa
> aria**; **sotto la barca** è un'inquadratura fissa come le camerette. **Da rivedere nel prototipo con la tana di
> Gulpy**: l'aspetto dell'acqua e i cerchietti cliccabili.

### Come si gioca, oggi

- **All'alba** di una notte vinta, dalla prima alla quinta (se la notte dopo è giocabile in questa build), la
  schermata dei risultati mostra anche **«Oltre la quota»** (i pesci avanzati alle sei) e il tasto **«Scendi con le
  bombole»** sopra «Notte successiva». L'immersione è facoltativa.
- **Giù**: si parte **sotto la barca**, un'inquadratura fissa (11 ottobre sera): la parete di roccia con
  l'imboccatura della grotta davanti, la cima dell'ancora a sinistra; lo sguardo si gira di 30° per parte (bordi dello
  schermo, `A`/`D`) e di pochi gradi in su e in giù (`W`/`S`). I passaggi sono cerchietti tenui che si accendono
  passandoci sopra, col nome; si clicca e si passa con una dissolvenza al nero con le bolle davanti alla maschera.
  In basso a destra c'è sempre **«Risali»**; si risale anche cliccando la cima dell'ancora.
- **La torcia** segue lo sguardo con un piccolo ritardo e trema appena: fuori dal cono resta quasi buio.
  **L'acqua**: la nebbia verde-blu (dalla distanza del passo dati), le particelle sospese che vanno alla deriva e si
  accendono nella torcia, i raggi che scendono dall'alto, l'immagine che trema appena, si galleggia ondeggiando.
- **La grotta grande**, l'unico posto a 360° (ci si guarda attorno anche in su e in giù): un'apertura per ogni tana dei mostri **già arrivati** (dopo la prima notte: Gulpy, Molly,
  Hatch e Robin); le altre non si vedono ancora. Il fondo enorme davanti si guarda soltanto («Dal fondo, nel buio,
  respira qualcosa di enorme»): non ci si entra. Da lì si sente sempre il respiro della Madre (`madre_breath`).
- **Le tane** (deciso l'11 ottobre): ogni cameretta è un'**inquadratura fissa**, come una telecamera di FNAF: lo
  sguardo si gira di 30° a destra e a sinistra (e di pochi gradi in su e in giù) e basta; in basso c'è il tasto
  **«Torna alla grotta»**. Il mostro dorme sul letto e respira (la toppa del respiro si dissolve sopra la posa) e fa salire le
  bolle. Cliccandolo, se hai un pesce, compare la conferma **«Lasci il pesce accanto a Gulpy?»**; sì, il pesce compare
  sulla sabbia davanti al letto (vedi «Il pesce lasciato nella tana») e quel mostro **la notte dopo non viene**. La tana del **mostro nuovo** della notte dopo è **vuota** («La tana è vuota.
  Chi ci dorme è già in giro.»).
- **L'aria** (decisa l'11 ottobre sera; `immersioni.json` → `air`): basta per **due tane**; il tempo dentro le tane è
  libero e nuotare non costa. **Non c'è un indicatore**: l'unico segnale è il respiro nell'erogatore, che entrando
  nella seconda tana (l'ultima che costa aria) diventa **affannoso** (`dive_breath_fast`, approvato l'11 ottobre
  sera); quando lasci la seconda tana («Torna alla grotta») invece di
  tornare nella grotta compare **«Aria finita: risali.»**, l'erogatore smette di dare aria (`dive_air_out`) e si
  risale da soli (`dive_up`). A una terza tana quindi non si arriva mai. La **tana vuota** del mostro nuovo **non
  conta** (`emptyDenFree: true`): dopo la prima notte si può vedere la tana vuota di Robin e poi due mostri che
  dormono. **«Risali»** resta sempre disponibile.
- **I suoni** (approvati, `docs/AUDIO.md`): l'ambiente della grotta (`amb_dive`) e l'erogatore (`dive_breath`) per
  tutta l'immersione, la discesa (`dive_down`), le nuotate fra un posto e l'altro (`dive_swim_1`, `_2`, alternate),
  le bolle quando un passaggio è bloccato (`dive_bubbles`), l'aria finita e la risalita, il pesce nella sabbia
  (`offer_fish`), nelle tane il respiro nel sonno in loop (`sleep_<mostro>`, dal letto) e ogni 14-28 secondi un
  movimento (`stir_<mostro>`), dalla grotta grande il respiro della Madre; nella seconda tana il respiro affannato
  (`dive_breath_fast`). Resta fuori solo `dive_air_low` (l'avviso del manometro, che non c'è più).
- **Risaliti**, si va all'intro della notte dopo.

### La simulazione

- `NightSim` ha un'opzione `fed` (il quarto argomento, `NightOptions`): il mostro sfamato **non arriva mai** in tutta
  la notte (non si vede, non si sente, il sonar non lo annuncia, non fa niente al pescatore); gli altri vengono come
  sempre.
- **La regia lo conta lo stesso** (deciso dall'utente il 13 ottobre: «il mostro rimosso viene comunque conteggiato
  nei tempi di spawn, ma durante il suo tempo non arriva»). Una sua copia invisibile, il **fantasma**
  (`NightSim.fantasma`), segue i suoi tempi: parte quando partirebbe lui, dopo di lei gli altri aspettano la solita
  pausa (`minGapBetweenStarts`), chi non viene insieme a lui (`exclusive`) aspetta che finisca la sua visita, e
  quando arriverebbe a prenderti se ne va e basta. Così la notte ha lo stesso ritmo di quella con lui, con i suoi
  arrivi vuoti; prima gli altri si prendevano i suoi turni. Le notti senza nessuno sfamato non cambiano.
- `canFeed(notte, mostro)` in `src/game/config.ts`: si sfama chi gira nella notte, **tranne il mostro nuovo** di
  quella notte (la sua tana è vuota); se gli si passa il nuovo, l'opzione non conta. `ARRIVAL` dice in che notte
  arriva ognuno.
- `npm run sim -- <notte> <partite> --sfama`: per ogni abilità il bot gioca la notte senza aiuti, poi la rigioca
  sfamando il mostro che lo uccide più spesso (se lo uccide solo la quota mancata, Gulpy, che si mangia i pesci).
  Con il fantasma (13 ottobre, 300 partite per abilità, prima → dopo):

  | Notte | Chi | Senza pesce | Sfamato, prima | Sfamato, col fantasma |
  |---|---|---|---|---|
  | 2 | medio, Gulpy | 93,7% | 98,3% | 99,0% |
  | 2 | maldestro, Gulpy | 65,0% | 94,7% | 94,7% |
  | 3 | maldestro, Gulpy | 44,3% | 81,0% | 81,7% |
  | 4 | medio, Gulpy | 77,0% | 76,7% | 78,7% |
  | 4 | maldestro, Archie | 51,7% | **48,3%** | 50,3% |
  | 5 | medio, Lampy | 81,0% | 90,0% | 93,3% |
  | 5 | maldestro, Lampy | 53,7% | 70,7% | 63,0% |
  | 6 | medio, Lampy | 74,0% | 79,7% | 78,0% |
  | 6 | maldestro, Lampy | 37,7% | 49,3% | 46,3% |

  Sfamare non fa più andare **peggio** (nella quarta notte il maldestro che sfamava Archie perdeva di più: Lampy
  veniva al suo posto). Nella quinta il maldestro che sfama Lampy vince un po' meno di prima (63% invece di 71%, ma
  sempre più del 54% senza pesce): ora gli arrivi si accalcano come nella notte vera quando Lampy se ne va, e il
  Foxy, che il maldestro guarda poco, lo prende più spesso. Gulpy resta il pesce che conta di più: si mangia i pesci
  della quota.

### Il salvataggio

In `src/app/save.ts`, oltre a quello che c'era: `dawn` (l'alba aperta: la notte vinta e quanti pesci avanzavano oltre
la quota; giù se ne porta uno solo, gli altri restano alla Madre), `fed` (il mostro sfamato e la notte in cui dorme)
e `dens` (le tane viste, anche quelle vuote). I vecchi salvataggi si leggono lo stesso. Le regole stanno in funzioni
piccole (`wonNight`, `afterDive`, `skipDawn`, `newGame`, `fedFor`, `pendingDawn`), provate in `tests/save.test.ts`:

- l'alba resta aperta finché non scendi o passi alla notte dopo: se chiudi il gioco sullo schermo dei risultati (o
  torni al menu), **«Continua» riprende l'alba** e si può ancora scendere; l'immersione prende i pesci da lì;
- il mostro sfamato dorme nella notte dopo quell'alba, anche se la perdi e la rigiochi; **vincere una notte qualsiasi**
  lo cancella (ha dormito, o era di un'altra alba): un'alba senza discesa non eredita mai un pesce vecchio;
- **«Nuova partita»** azzera l'alba, il mostro sfamato e le tane viste (il diario e il Catalogo restano).

### I file

| File | Cosa c'è |
|---|---|
| `src/app/dive_run.ts` | Le regole di un'immersione senza grafica (`DiveRun`): passaggi visibili, tane chiuse/vuote/col mostro, l'aria (due tane, `outOfAirOnLeave`), il pesce. E i tipi del file di dati. Test in `tests/dive.test.ts`. |
| `src/app/dive.ts` | La modalità immersione: carica i posti, lo sguardo, la torcia, l'acqua, i punti cliccabili, la conferma del pesce, i suoni. |
| `src/app/app.ts` | Il flusso: alba → «Scendi con le bombole» → immersione → notte dopo (col mostro sfamato). |
| `src/engine/renderer.ts`, `shaders.ts` | Nuovo nel motore: la nebbia degli strati configurabile (`fog`), la torcia sul passo lanterna (`torch`), la tinta di uno strato, il passo dell'acqua `WATER_FS` (raggi, particelle, alone della torcia, colonne di bolle, le bolle dell'erogatore) al posto dell'atmosfera della notte, `removeLayer` per liberare le texture. Le notti non cambiano. |
| `public/assets/img/immersioni.json` | I posti, i passaggi, le tane, i suoni dei posti, l'aria e l'aspetto dell'acqua. |
| `tools/immersioni_segnaposto.py` | Genera i panorami segnaposto in `public/assets/img/immersioni/segnaposto/`. |

### I render veri delle grotte

Dall'11 ottobre notte **sotto la barca** e la **grotta grande** sono i render finali (`tools/render/sotto_barca.py`,
`tools/render/grotte.py`, branch `claude/immersioni-grotte`): le loro voci in `immersioni.json` vengono da
`public/assets/img/immersioni/*_posto.json`, con le direzioni vere dei passaggi e delle tane (per esempio la tana di
Gulpy a −128°, la cima per risalire a −6,6° / 12,2°). L'acqua torbida è già cotta nei loro passi (`acquaCotta: true`):
lì la nebbia del motore scende a `water.fogDensityCooked` (0,012 invece di 0,09), se no si raddoppia. Le camerette e
il mostro che dorme restano segnaposto. Schermate: `docs/concept/immersioni_prova_15…18_*.jpg`.

### Come si aggiungono i posti veri

Tutto sta in `public/assets/img/immersioni.json`; il codice non cambia.

1. **Il panorama** di un posto: per la grotta grande un equirettangolare a sfera intera (`latMin` −90 e `latMax` 90,
   così si guarda in su e in giù), con i passi `ambient` (la luce dell'acqua, quasi buio), `lantern` (la scena
   accesa da una luce sull'occhio: il motore la mostra solo nel cono della torcia) e `data` (R = sqrt(distanza /
   2500 m), come il passo dati del mondo, per la nebbia; G = quanto trema l'immagine, 0,1 circa). Si codificano
   come gli altri render (gamma 4, con la loro `scale`). `size` è la larghezza e l'altezza in pixel, `yaw` la
   rotazione, `look` dove guardi arrivando, `rays` quanta luce scende dall'alto.
   **Sotto la barca e le camerette** sono inquadrature fisse: un panorama **parziale** (`lonMin`/`lonMax` e
   `latMin`/`latMax`, i bordi in gradi; i segnaposto sono 160° × 95° sotto la barca e 160° × 80° le camerette) con `frame`: `yaw` e `pitch` del centro, `yawRange` (30) e
   `pitchRange` (4 nelle camerette, 6 sotto la barca), i gradi di cui si gira. Il panorama deve coprire il campo visivo (90° in orizzontale, fino a
   68° in verticale) più quanto si gira: almeno 150° × 76°. Lo zoom non cambia.
2. **I passaggi** (`links`): `to` (il posto), `yaw` e `pitch` (gradi, nel panorama del posto: dove sta l'apertura),
   `r` (il raggio cliccabile in gradi), `label` (il nome che compare: chiave di `STRINGS.dive.links`). Con
   `button: true` il passaggio è un tasto sullo schermo invece di un punto del panorama (nelle camerette, «Torna alla
   grotta»: in un'inquadratura fissa l'uscita alle spalle non si vede). Un passaggio
   con `ascend: true` fa risalire; uno con `note` mostra una didascalia (`STRINGS.dive.notes`).
3. **Le tane**: un posto con `den: "<mostro>"`. Il passaggio verso una tana si vede solo quando quel mostro è già
   arrivato; per il mostro nuovo della notte dopo la tana è vuota. Il mostro che dorme sta in `sleeper`: `yaw`,
   `pitch`, `r` (dove si clicca per lasciargli il pesce), `layers` (gli strati ritagliati sopra il panorama: la posa,
   poi le toppe con `breath`, il periodo in secondi con cui si dissolvono sopra la posa; `rect` in pixel del
   panorama del posto) e `bubbles` (da dove salgono le bolle). Se la posa è dipinta nel panorama, `panoEmpty` dà il
   panorama della tana vuota.
4. **La memoria**: un panorama a sfera intera con tre passi pesa molto in GPU (8192 × 4096 RGBA sono 128 MB a
   passo). Il motore tiene in memoria **un posto solo**: lo carica quando ci arrivi (durante la dissolvenza al nero)
   e lo libera quando te ne vai. Il passo `lantern` può stare a mezza risoluzione, come quello del mondo.
5. **I suoni** di un posto: `sounds` (id, `yaw`, `pitch`, `dist` in metri, `gain`) suonano in loop finché ci sei
   (la Madre dalla grotta grande). Il mostro che dorme usa da solo `sleep_<mostro>` e `stir_<mostro>` dal punto
   `sleeper`.

### La prova nel browser

Provato l'11 ottobre nel Chromium headless con `?step` (nessun errore in console): la prima notte vinta con tre
pesci oltre la quota, «Scendi con le bombole», sotto la barca, la grotta grande, la tana di Gulpy col pesce lasciato,
la tana vuota di Robin, la terza tana rifiutata per l'aria, l'aria che finisce e la risalita da soli (prima delle
decisioni della sera: allora c'erano ancora il manometro e la riserva), l'intro della
seconda notte e la notte con Gulpy che dorme. Le schermate sono in `docs/concept/immersioni_prova_*.jpg` (i panorami
sono i segnaposto). Dopo la decisione delle inquadrature fisse: `immersioni_prova_11_cameretta_inquadratura.jpg`
(la cameretta girata tutta a sinistra, al centro, tutta a destra). Dopo le decisioni della sera:
`immersioni_prova_12_sotto_barca_fissa.jpg` e `immersioni_prova_13_aria_finita.jpg`.

### Se qualcosa va storto

- Se un file di un posto manca o non si scarica, le texture già create si liberano, non si spende aria e la tana
  non si conta; si torna nel posto di prima con la didascalia «Di là non si passa. Torni indietro.» Se non si carica nemmeno quello, si risale. Se manca il primo posto, si passa alla notte dopo.
- Se si risale (il tasto o l'aria finita) mentre si carica un posto, la risalita vince.

### Cosa manca

(Aggiornato il 13 ottobre: i render delle grotte e delle tane sono quelli finali, le cose trovate nelle tane vanno
nel Diario, il mostro sfamato conta nella regia senza arrivare; le camerette, le pose addormentate e il pesce lasciato
nella tana sono approvati, con la pagina «Approvazioni di Splashland».)

- Le bombole sulla barca all'alba: oggi c'è il tasto «Scendi con le bombole» con la loro icona, non l'oggetto sulla
  barca.
