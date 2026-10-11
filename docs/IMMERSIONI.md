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
- **L'aria** basta per **due tane**: il manometro delle bombole (un ago come quello del voltmetro) scende a ogni
  tana visitata e a metà del ritorno suona l'avviso. Quando l'aria finisce si risale da soli.
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

**Da approvare**: l'aspetto della sala (roccia, colori, quanta vita), la luce del pozzo e quanto è torbida l'acqua;
i pezzi del parco e il cartello; la disposizione delle bocche; le sette cose appese (soprattutto le ciocche di
Molly); la tana della Madre così (solo buio, senza niente che si veda dentro).

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

## Il pesce e i finali

Il pesce lasciato nelle tane decide anche **il finale della sesta notte** (approvato l'11 ottobre, vedi
`docs/NOTTI_E_MOSTRI.md`, «I finali»): un pesce **a ogni alba** porta al finale segreto **«I tuoi»**; scendere almeno
tre volte senza lasciarne **mai** uno porta al finale segreto **«Nessuno»**; tutto il resto al finale A. Il
salvataggio deve quindi ricordare, alba per alba, se sei sceso e se hai lasciato il pesce.

## Cosa serve

- **Motore**: la modalità immersione (panorami collegati, la torcia, l'acqua torbida con le particelle e i raggi di
  luce, le bolle dell'erogatore, il manometro), l'offerta del pesce (si clicca il mostro tenendo il pesce),
  la schermata dell'alba con la scelta, i salvataggi (chi hai sfamato, le tane viste).
- **Render**: il panorama a 360° della grotta grande (più la discesa sotto la barca), sette camerette come
  inquadrature fisse larghe abbastanza da girarle di 30° per parte, sette pose addormentate con le loro toppe.
- **Suoni**: l'ambiente sott'acqua, l'erogatore, il respiro nel sonno di ognuno, le conchiglie di Fangy.
- **Simulazione**: il mostro sfamato non parte; il bot sfama il più pericoloso; si ribilanciano le notti.

## In che ordine

1. Prima le sei notti (deciso l'11 ottobre).
2. Un prototipo con la sola tana di Gulpy: l'alba con le bombole, la discesa, la grotta grande, Gulpy che dorme, il
   pesce lasciato accanto al letto, la notte dopo senza di lui.
3. Se convince, le altre tane una alla volta, nell'ordine in cui arrivano i mostri.
