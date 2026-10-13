# Atmosfera: la baia più buia, con la nebbia (prove dell'11 ottobre)

Decisione dell'utente (11 ottobre sera): attorno alla barca un'atmosfera più buia e cupa, con foschia e nebbia
«ma ben fatte». Gli sbuffi disegnati dal motore (branch claude/foschia) sono stati bocciati: questa volta la
nebbia è un volume vero, reso in Cycles.

## Le prove

- `docs/concept/atmosfera_prua_alta.jpg`, `_bassa.jpg`, `_spenta.jpg`: dal posto del pescatore verso la prua,
  con Gulpy che sale a 7 m (la posa `gulpy_sale`), luce alta, bassa e spenta.
- `docs/concept/atmosfera_prima_dopo.jpg`: lo stesso, il look di oggi sopra (con la nebbia del motore) e il nuovo
  sotto, luce alta.
- `docs/concept/atmosfera_poppa_alta.jpg`, `atmosfera_poppa_prima_dopo.jpg`: verso Splashland (ingresso, statua,
  torre degli scivoli, ruota panoramica), i posti del binocolo.

Sono rese a 1280×720 con 128 campioni dalla stessa camera della vista di gioco (90°, 12° in basso) e composte come
il motore: ambient + peso·lamp + lantern (pesi 1,7 / 1 / 0), esposizione, bloom, AgX col look noir, vignetta, grana.
Rifarle: `tools/render/atmosfera.py render dopo|prima ...` e poi `atmosfera.py componi`.

## Com'è fatta (tools/render/atmosfera.py)

- **Nebbia**: una scatola di 3,4 km × 160 m attorno alla barca con un Principled Volume (anisotropia 0,55). La
  densità è la somma di:
  - la foschia bassa sull'acqua, che cala a 1/e in 1,2 m e si sfilaccia in banchi col rumore;
  - una sacca di nebbia attorno alla barca, raggio 26 m: è lì che la lampara fa l'alone, oltre c'è il buio;
  - una nebbia rada che sale fino a 40 m e dà la profondità.
- **L'alone nei passi della lampara**: i light group di Cycles dividono la luce per sorgente anche nei volumi,
  quindi quello che la nebbia diffonde dalla lampara finisce nel passo `lamp` e cresce e cala col livello e con
  lo sfarfallio, senza toccare il motore.
- **Più buio**:
  - il cielo è a 0,30;
  - la luna sulla scena a 0,20 e il suo disco a 0,35, perché il riflesso sull'acqua bucava la foschia;
  - il paese a 0,35, con un lampione su tre;
  - il faro a 0,45.
- **I posti del binocolo restano leggibili**:
  - le loro luci vanno a 1,3 e bucano la nebbia;
  - una seconda luna con il light linking illumina solo loro (la ruota e la torre, con la luna abbassata, si
    perdevano contro le colline);
  - un chiarore appena più chiaro sopra l'orizzonte stacca le sagome delle colline.
- **Smussatura**: la luce della lampara che la nebbia diffonde lontano (oltre una trentina di metri) è debole e
  Cycles la lascia a chiazze nel cielo. Là la si sostituisce con la sua media larga, una convoluzione normalizzata
  sui soli pixel lontani, che è fisicamente giusta perché quella luce è liscissima. Il passo mist di Cycles si
  accumula nei volumi, quindi le distanze vere vengono dal passo Depth.
- **In jobs.py**: `ATMOSFERA=1` applica tutto alla scena dei job. Il job `world` rende anche il Depth e ne ricava il
  mist del motore, sqrt(d / 2500 m) come prima, e la smussatura del passo `lamp`.

## Tempi di render (4 CPU di questa macchina)

| Cosa | Tempo |
| --- | --- |
| Prova 1280×720, 128 campioni, vista prua (la peggiore: guarda nell'alone) | 20 min (senza nebbia 10) |
| Prova 1280×720, 128 campioni, vista verso il parco | 12 min (senza nebbia 5) |
| Costruzione della scena (le creature e la statua sono SDF) | ~4 min |
| Panorama del mondo in bozza (2048×535, 24 campioni, con la nebbia) | 4 min |
| **Panorama del mondo finale (8192×2139, 128 campioni)** | **~5-6 h** |
| Strato della barca (la nebbia fra l'occhio e la barca, vedi sotto) | ~2-3 h |
| Mostri: ~15 strati fra pose e toppe, riquadri piccoli | ~3-4 h (13 ottobre: 30 strati e i pesci in 4 h 40) |
| Binocolo (9 luoghi) | ~1-2 h |
| Jumpscare (4) | ~1-2 h (13 ottobre: 80 min l'uno con la nebbia a 64 campioni, sfondo 15 min, fotogrammi 5-13 min) |

Il mondo e la barca stanno in una notte. Il resto in un'altra.

## Cosa va rifatto per coerenza

1. **Strato della barca**: oggi si rende con l'ambiente invisibile alla camera, quindi anche la nebbia, e
   l'alone che sta davanti alla barca andrebbe perso. Va reso con la nebbia visibile e il mare e la costa in
   holdout. L'interno della barca prende comunque meno ambiente: va rifatto.
2. **Mostri** (fatto in parte il 13 ottobre, vedi «Mostri e jumpscare con la nebbia») (tutte le pose e le toppe di scena_creature.py e pose_animate.py): più bui dalla luna e
   illuminati dalla lampara attraverso la nebbia. La nebbia davanti a un mostro a 3-7 m è poca, ma la luce
   cambia. Le facce restano visibili: Gulpy a 7 m si legge bene con la luce alta e bassa. Con la luce spenta
   restano gli occhi che accende il motore.
3. **Binocolo** (binocolo.py): con la nebbia vera lungo la linea di vista, e la stessa luna legata ai luoghi.
   È lì che va il mostro nuovo da sorvegliare: conviene dargli una luce sua o un posto con la luna sopra.
4. **Jumpscare** (vedi «Mostri e jumpscare con la nebbia»): per l'ambiente più buio. La nebbia a mezzo metro non conta, ma conviene lasciarla nella scena
   per l'alone della lampara dietro il mostro.
5. **Vista da sotto il telone** (job tarp): l'ambiente più buio.
6. Non vanno rifatti: catalogo, pesci, oggetti di scena senza mare.

## Nel motore (12 ottobre, ramo `claude/atmosfera-motore`)

- **La voce `atmosfera` del manifest** (`src/engine/assets.ts`, `src/app/stage.ts`): `fog` è la nebbia di distanza
  del motore sopra al panorama (quasi niente, densità 1/50000 e colore molto scuro, perché è già nel render), `glows`
  dice quanto sono forti (`gain`) e larghi (`radius`) i bagliori delle luci lontane, più un elenco `off` per quelle
  spente nel render (oggi vuoto: le luci dei posti del binocolo restano accese). Senza la voce il motore fa come prima.
  Le dive (immersioni) hanno la loro nebbia e non cambiano.
- **L'opzione «Nebbia»** (decisa dall'utente il 12 ottobre; nelle impostazioni, accesa di partenza): la nebbia è
  dentro le immagini, quindi il gioco tiene **due serie**. Le immagini con la nebbia hanno i nomi di sempre; quelle di
  prima diventano `<nome>_senza.webp` e stanno nelle voci `senza` (`layers.world.senza`, `layers.boat.senza` nel
  manifest; `binocular.places[].senza` e `tarp.senza` in `overlays.json`). Con l'opzione spenta il gioco carica la
  serie senza nebbia e non usa la voce `atmosfera`. Si cambia anche a notte in corso: si scambiano tutti gli strati
  che hanno la voce `senza` (il mondo, la barca, i mostri e le loro toppe), i posti del binocolo, il telone e i
  jumpscare che hanno `senza` (vedi «Mostri e jumpscare con la nebbia» più sotto). Uno strato o un jumpscare senza
  la voce `senza` è uguale nelle due serie. Un posto del Foxy (scivoli, relitto) cambia serie solo se ha anche le sue viste senza nebbia, se no
  si vedrebbe quando arriva lui: dal 12 ottobre le ha tutte e due (sessione del Foxy).
- **Mettere le immagini nuove nel gioco**: `tools/render/atmosfera_due_serie.py <cartella dei render> <repository>
  --mondo --barca --luoghi albergo,edicola,... --telone`. La prima volta sposta le immagini di adesso nella serie
  `senza`; le volte dopo sostituisce solo quelle con la nebbia.
- **Il binocolo con la nebbia** (`binocolo.py` con `ATMOSFERA=1`): 192 campioni nei finali (`CAMPIONI=n`) e il mist
  dell'alfa dal passo Depth, come il mondo.
- **Attenzione alle scale**: `jobs.py binocolo` scrive le scale in `overlays.json` solo alla fine di tutti i posti.
  Il 12 ottobre le prime viste sono entrate con le scale del render di prima, e la statua si vedeva 3,8 volte più
  chiara, col bordo del riquadro staccato dal mondo. Ora l'installatore si ferma se il manifest della cartella dei
  render è più vecchio dei file da installare.
- **Le luci attorno a Soggy** (`stage.ts`, da approvare): lampione, lanterna e le due lampadine che pendono dal tetto
  della torre hanno un bagliore del motore solo nel binocolo, con un loro sfarfallio (nel render sono fisse).
  Posizioni e colori vengono dalla scena del Foxy (`luci_posti.json`) e stanno nel codice (`GlowDef.pos`), perché il
  render del mondo riscrive le luci del manifest. Col binocolo alzato le luci lontane dall'inquadratura restano fuori
  dal conto dei 16 bagliori.

### Installato il 12 ottobre (ramo `claude/atmosfera-motore`)

| Cosa | Da dove | Note |
| --- | --- | --- |
| Mondo | sessione dell'atmosfera, `claude/atmosfera` 8a9eb7b | 8192×2139, 256 campioni, 16 strisce |
| Barca | catena di questa macchina | 256 campioni |
| Binocolo: ingresso, statua, ruota, albergo, edicola, faro, paese | catena di questa macchina | 192 campioni; ai bordi combaciano col mondo (0,93-1,03) |
| Soggy al binocolo (scivoli, relitto), tutte e due le serie | sessione del Foxy, `claude/foxy` 1079fdf e 737f944 | con lampione, festone e lanterna |
| Telone (vista da sotto) | catena di questa macchina | |

**L'alone della luce più leggero** (prova dell'utente del 12 ottobre sera: «la nebbia mescolandosi con la luce della
lampara crea un alone bianco davanti alla barca che è brutto»): era la luce della barca diffusa nella nebbia del
mondo, un velo chiaro su metà della scena. Il passo `lamp` del mondo con la nebbia vale un quinto (la sua scala nel
manifest, 0,25 → 0,05): resta un velo leggero attorno alla lampada, si rivedono la luna sull'acqua e il paese. La serie
senza nebbia non cambia. Se si reinstalla il mondo, va rifatto. Da allora la nebbia è anche **spenta di partenza**.

**Ripulitura dopo il render** (`tools/render/liscia_nebbia.py`, 12 ottobre sera, segnalazione dell'utente: «sul lato
sinistro della barca la nebbia sembra pixellare la luce»): la diffusione nella nebbia della lanterna (e in parte della
lampara) usciva da Cycles a chiazze, che sull'acqua scura sembravano pixel. I passi `lamp` e `lantern` del mondo
prendono la media del loro intorno (mezzo grado vicino, un grado oltre i 15-60 m), tranne i riflessi veri, molto più
chiari dell'intorno e più grandi di un pixel. Va rifatta su ogni mondo nuovo con la nebbia.

Controllato nel gioco: sei direzioni con la luce alta e spenta, tutti i posti del binocolo, Soggy fermo, più
vicino e via, l'opzione accesa e spenta a notte in corso. La grana che si vede sulla foschia chiara è quella della pellicola
di sempre (`uGrain`), non del render.

## Mostri e jumpscare con la nebbia (12-13 ottobre, ramo `claude/mostri-nebbia`, da approvare)

Decisione dell'utente del 12 ottobre sera («Mostri nella nebbia»): chi gioca con la nebbia accesa vede anche i mostri
e i jumpscare resi con l'atmosfera. Le immagini di prima restano la serie `senza`.

- **Render**: le stesse pose, toppe e inquadrature, con `ATMOSFERA=1` (la baia più buia e la nebbia nella scena):
  `ATMOSFERA=1 RENDER_OUT=<cartella> POSES=… jobs.py creature --quality final` (128 campioni). Con `POSES` le pose si
  rendono in quell'ordine, una creatura alla volta, base e toppe insieme (le toppe prendono lo yaw della loro base
  dallo stesso giro). La nebbia negli strati dei mostri è invisibile alla camera (come prima, `render_sprite` nasconde
  l'ambiente): cambia la luce, la luna sui mostri è circa 0,4 di prima e la lampara uguale (la nebbia davanti a un
  mostro a 3-7 m è poca, e quella lontana è già nel mondo).
- **Jumpscare** (`jobs.py jumpscare`, `JS_SAMPLES=64`; la quota con `quota.py --finale`): stessi percorsi, camere,
  fotogrammi e post-produzione del motore. La nebbia è nello sfondo e non nei fotogrammi della creatura (come già
  faceva jumpscare.py). Nuovo: nello sfondo, fuori dalla barca, la lampara vale un quinto (`LAMPARA_MONDO`), come il
  passo `lamp` del mondo nel gioco, se no tornava l'alone bianco. La copertura della barca viene da un render rapido
  senza nebbia (4 campioni). Poi lo sfondo si ripulisce (`_liscia_sfondo`, 13 ottobre, segnalazione sul jumpscare di
  Gulpy: il mare vicino sembrava una superficie granulosa arancio-grigia): fuori dalla barca i passi `lamp` e
  `lantern` prendono la media dell'intorno (mezzo grado, solo sui pixel fuori dalla barca), tranne i riflessi veri,
  come liscia_nebbia.py col mondo. Sulla barca la nebbia davanti allo scafo è la differenza con lo sfondo reso senza la
  nebbia (`<chi>_bg_chiaro.exr`, 10 minuti): si liscia quella e si rimette sopra lo scafo pulito, così le coste restano
  nitide. Con `JS_RIPRENDI=1` si rifà riusando sfondo, copertura e fotogrammi della cache (rende solo lo sfondo
  chiaro, se manca); `tools/render/rimetti_jumpscare.py` rimette nel gioco i fotogrammi ricomposti quando la serie
  senza c'è già. I fotogrammi nuovi sono 1920×1080; quelli della serie senza di Gulpy, Molly e Hatch erano 960×540.
- **Installazione**: `tools/render/mostri_due_serie.py <cartella dei render> <repository> --mostri gulpy,molly
  --strati fish2,… --jumpscare gulpy,…`. Come atmosfera_due_serie.py: la prima volta i file di adesso diventano
  `<nome>_senza.webp` (strati: `layers.<chiave>.senza.passes`; jumpscare: `jumpscares.<chi>.senza.frames`), poi
  arrivano i file nuovi coi nomi di sempre. Prima di toccare qualcosa controlla tutto: si ferma se un riquadro o uno
  yaw sono cambiati (una toppa spostata di un pixel non combacia più), se cambia il numero dei fotogrammi o se il
  manifest dei render è più vecchio dei file (le scale). `--prova` dice cosa farebbe.
- **Controllo**: `tools/render/confronta_jumpscare.py <cartella> <chi> <tavola.jpg>` (i fotogrammi delle due serie);
  `scripts/nebbia_jumpscare.mjs` (il jumpscare nel gioco a notte in corso, con la nebbia spenta e accesa);
  `scripts/decodifica.mjs` (Chromium decodifica tutte le immagini; dopo un'installazione va riavviato `npx vite`, che
  può rispondere con la pagina HTML per un file tolto e rimesso); `tools/render/confronta_serie.py <cartella> <chiavi>` (riquadro, alfa al pixel, rapporto della luce e
  una tavola con la lampara spenta, bassa e alta sul mondo di ciascuna serie); `scripts/nebbia_mostri.mjs` (il visore,
  che ora accetta `?senza`, e il cambio di serie a notte in corso).
- **Nel motore**: `fogLayerKeys` e `layerSeries` (`assets.ts`) e `swapFog` (`app.ts`) scambiano ogni strato caricato
  che ha `senza`; i jumpscare si caricano all'avvio nella serie dell'opzione e `swapFogAssets` (`overlays.ts`) li
  scambia (la notte li legge a ogni fotogramma). Test in `tests/nebbia.test.ts`.

### Rifatti con la nebbia (da approvare)

| Cosa | Strati / fotogrammi | Note |
| --- | --- | --- |
| Gulpy | gulpy_sale, gulpy_pretende, gulpy_mascella_chiusa, gulpy_mascella_aperta | sagome uguali (2-9 pixel di bordo); luna 0,35-0,4 |
| Molly | molly_destra, molly_sinistra e le quattro toppe degli occhi | sagome uguali (1-10 pixel di bordo); luna 0,36-0,4 |
| Hatch | hatch_conta, hatch_bocca_mezza, hatch_bocca_chiusa | sagome uguali (3-6 pixel); cambia poco (0,95): lo illumina la sua lucina |
| Robin | robin_secchio, robin_strizza, robin_chiusi | sagome uguali (1-15 pixel); luna 0,4-0,5 |
| Robin, la ritirata (13 ottobre) | robin_ritirata_1..6, nuovi: tutte e due le serie rese insieme (la `_senza` da un'altra sessione, `claude/robin-ritirata-senza`) e installate con mostri_due_serie.py | sagome uguali (IoU 0,9997-0,9999, 11-22 pixel); luna 0,31-0,38; stesso yaw di robin_secchio |
| Archie | archie_soffia, archie_fiato, archie_trombetta_mezza, archie_trombetta_tutta | sagome uguali (0-2 pixel); luna 0,55-0,6 |
| Lampy | lampy_lenza, lampy_bocca_chiusa, lampy_bocca_aperta | sagome uguali (2-4 pixel); luna 0,5-0,55 |
| Fangy | fangy_ascolta, fangy_testa_prua, fangy_testa_poppa | sagome uguali (3 pixel); luna 0,25-0,4, lanterna 1,2-1,35; a luce spenta lo mostrano le lucine del motore (posizioni invariate) |
| La Madre | madre_sale | sagoma uguale (4 pixel); luna 0,4 |
| Pesci nel secchio | fish2, fish5, fish9 (`PROPS=fish jobs.py props`) | sagome uguali (0-4 pixel); luna 0,3, lampara 1,04-1,18 |
| Jumpscare di Gulpy | js_gulpy_00..07 (1920×1080, 64 campioni) | stesse inquadrature e movimento; luce media 1,0-1,1 di prima; sfondo velato, alone della lampara leggero; il mare vicino ripulito dalla grana a chiazze del denoiser e lo scafo dalla grana fine (13 ottobre: `_liscia_sfondo` in jumpscare.py, con ATMOSFERA=1: fuori dalla barca la media dell'intorno sui passi lamp e lantern; sulla barca si liscia solo la nebbia davanti allo scafo, la differenza con lo sfondo reso senza nebbia; ricomposto con JS_RIPRENDI=1, `rimetti_jumpscare.py`) |
| Jumpscare di Molly | js_molly_00..07 | stesse inquadrature; luce media 0,76-1,0 di prima (la luna più bassa sul fianco della barca); sfondo ripulito dalla grana del denoiser, mare e scafo (13 ottobre, come Gulpy) |
| Jumpscare di Hatch | js_hatch_00..07 | stesse inquadrature; luce media 0,76-0,94 di prima; sfondo ripulito dalla grana del denoiser, mare e scafo (13 ottobre, come Gulpy); nel cielo resta una grana fine leggera |
| Jumpscare di Robin | js_robin_00..07 | stesse inquadrature e movimento; luce media 1,02-1,04 di prima; sfondo più velato e scuro, niente alone; un filo di grana nella nebbia sopra lo scafo (la copre la grana del nastro del motore) |
| Jumpscare di Archie | js_archie_00..07 | stesse inquadrature e movimento; luce media 0,28-0,57 di prima (lampara spenta: resta la luna, come nel mondo con la nebbia, 0,36); sfondo velato, montagne quasi nella nebbia, niente alone; Archie da vicino 0,55-0,57 |
| Jumpscare di Lampy | js_lampy_00..07 | stesse inquadrature e movimento; luce media 0,60-0,65 di prima nei primi fotogrammi (quasi tutta lago e cielo velati), 0,90-1,01 da vicino; luna e riflessi più morbidi, niente alone |
| Jumpscare di Fangy | js_fangy_00..07 (1920×1080, 64 campioni) | stesse inquadrature e movimento; luce media 0,76-0,79 di prima (la luna più bassa); sfondo velato, alone della lampara leggero, lucine e zanne leggibili |
| Jumpscare del Foxy | js_foxy_00..07 | stesse inquadrature e movimento; luce media 0,86-0,95 di prima; sfondo velato e più azzurro; niente alone bianco (la serie di prima ce l'aveva in alto a sinistra) |
| Jumpscare della Madre | js_madre_00..07 | stesse inquadrature e stessa inclinazione della barca; luce media 0,79-0,95 di prima; monti, paese e lume lontano velati; il mare vicino è nebbia liscia (la grana a chiazze del denoiser tolta dallo sfondo con `liscia_sfondo_jumpscare.py`, solo sui passi lamp e lantern fuori dalla barca); niente alone |
| Jumpscare della quota | js_quota_00..07 (1920×1080, 96 campioni; 0-3 dalla sessione della quota, 4-7 da quattro sessioni in parallelo con `QUOTA_FOTOGRAMMI`, scale da `post.pick_scale`) | stesse inquadrature e movimento; luce media 1,17-1,35 di prima, dal 3 al 4 senza salti (1,22 → 1,24); velo leggero e uniforme sull'acqua, la schiuma un po' più spenta; nessun alone (quota.py non cambia: LAMPARA_MONDO spegnerebbe la luce sott'acqua sull'occhio) |

## Cosa cambiare nel motore (scritto prima del lavoro sul motore: vedi sopra)

- **Nebbia di distanza** (`WORLD_FS` e il binocolo in `shaders.ts`, `uFogDensity` in `renderer.ts`): ora è dentro
  il panorama, quindi va tolta o ridotta a quasi niente, se no la baia si schiarisce due volte. `uFogColor`,
  se resta, va molto più scuro.
- **Bagliori delle luci lontane** (`landscapeGlows` in `stage.ts`): più deboli e più larghi, perché nella nebbia le
  luci fanno un alone morbido. Vanno tolti quelli delle luci spente o abbassate, come i lampioni del paese.
- Il **mist** del `world_data` resta con la stessa formula (ora corretto dal Depth): le increspature sull'acqua e
  il resto funzionano come prima.
- Facoltativo: un leggerissimo scorrere della nebbia già resa, una distorsione lenta degli UV solo dove c'è
  nebbia vicina, per non averla immobile. Va provato con cautela, dopo la bocciatura degli sbuffi.
- Nient'altro: l'alone segue già la luce, perché sta nel passo `lamp`.
