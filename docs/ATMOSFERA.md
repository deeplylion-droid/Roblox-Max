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
| Mostri: ~15 strati fra pose e toppe, riquadri piccoli | ~3-4 h |
| Binocolo (9 luoghi) | ~1-2 h |
| Jumpscare (4) | ~1-2 h |

Il mondo e la barca stanno in una notte. Il resto in un'altra.

## Cosa va rifatto per coerenza

1. **Strato della barca**: oggi si rende con l'ambiente invisibile alla camera, quindi anche la nebbia, e
   l'alone che sta davanti alla barca andrebbe perso. Va reso con la nebbia visibile e il mare e la costa in
   holdout. L'interno della barca prende comunque meno ambiente: va rifatto.
2. **Mostri** (tutte le pose e le toppe di scena_creature.py e pose_animate.py): più bui dalla luna e
   illuminati dalla lampara attraverso la nebbia. La nebbia davanti a un mostro a 3-7 m è poca, ma la luce
   cambia. Le facce restano visibili: Gulpy a 7 m si legge bene con la luce alta e bassa. Con la luce spenta
   restano gli occhi che accende il motore.
3. **Binocolo** (binocolo.py): con la nebbia vera lungo la linea di vista, e la stessa luna legata ai luoghi.
   È lì che va il mostro nuovo da sorvegliare: conviene dargli una luce sua o un posto con la luna sopra.
4. **Jumpscare**: per l'ambiente più buio. La nebbia a mezzo metro non conta, ma conviene lasciarla nella scena
   per l'alone della lampara dietro il mostro.
5. **Vista da sotto il telone** (job tarp): l'ambiente più buio.
6. Non vanno rifatti: catalogo, pesci, oggetti di scena senza mare.

## Cosa cambiare nel motore (src/, non toccato)

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
