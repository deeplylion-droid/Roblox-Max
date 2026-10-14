# Le immagini per Steam

Le immagini e il trailer della pagina del negozio e della libreria di Steam. Stanno qui, fuori dal gioco (`public/`),
perché non vanno nella build: si caricano a mano su Steamworks, nella pagina del gioco (**Store page admin → Graphical
assets** per le capsule e gli screenshot, **Trailers** per il trailer, **Library assets** per la libreria). Il piano di
tutti i passi è nella pagina «Splashland su Steam».

**Approvate dall'utente il 13 ottobre.** La scelta fra tre proposte per la capsula è stata la A: Molly che si affaccia dal bordo della
barca, col logo al neon. Le altre due erano Gulpy che sale alla prua (B) e Hatch con l'esca (C). Per il Catalogo
l'utente ha chiesto la pagina di un pesce invece dell'indice.

## Le capsule (`capsule/`)

| File | Su Steam | Cosa c'è |
|---|---|---|
| `principale_1232x706.png` | Main capsule (1232×706) | il ritratto di Molly del menu, il buio a sinistra col logo |
| `intestazione_920x430.png` | Header capsule (920×430) | lo stesso, più stretto |
| `piccola_462x174.png` | Small capsule (462×174) | il logo grande, Molly che sbircia dal bordo destro: si legge anche a metà grandezza |
| `verticale_748x896.png` | Vertical capsule (748×896) | il render verticale di Molly, il logo in alto nel buio |

Le capsule hanno solo l'immagine e il logo, come vuole Steam. Niente frasi, voti o scritte tipo «demo» o «sconto».

## La libreria (`libreria/`)

| File | Su Steam | Cosa c'è |
|---|---|---|
| `capsula_600x900.png` | Library capsule (600×900) | come la capsula verticale |
| `intestazione_920x430.png` | Library header (920×430) | la stessa dell'intestazione del negozio |
| `immagine_3840x1240.png` | Library hero (3840×1240) | un render largo, senza scritte: Molly a destra, dentro la zona centrale di 3000×740 che Steam non taglia; a sinistra il lago e la barca, dove Steam mette il logo |
| `logo_1280x612.png` | Library logo (largo 1280, PNG trasparente) | il logo al neon col suo bagliore |

Il logo della libreria va messo **in alto a sinistra** sull'immagine larga. In basso a sinistra c'è l'interno della
barca, chiaro, e il neon si vedrebbe poco.

## Gli screenshot (`screenshot/`)

Sono 8, a 1920×1080, presi dal gioco con la nebbia accesa e messi nell'ordine della pagina. I primi quattro sono
quelli che Steam mostra di più:

1. `01_molly`: Molly che si affaccia accanto alla barca;
2. `02_hatch`: Hatch con l'esca accesa a poppa, l'insegna di Splashland nella nebbia;
3. `03_binocolo_ingresso`: l'ingresso del parco nel binocolo;
4. `04_tana_di_molly`: la tana di Molly durante l'immersione all'alba;
5. `05_archie`: Archie alla prua sotto la luna;
6. `06_binocolo_soggy_al_relitto`: Soggy al relitto, nel binocolo;
7. `07_catalogo`: il Catalogo aperto su un pesce scheletrico (Bonchovy), in inglese;
8. `08_grotta_sotto_la_barca`: la grotta sotto la barca.

Le scene della notte e dell'immersione sono la tela del motore, senza HUD. I mostri sono messi in posa a mano.

## Il trailer (`trailer/`)

**Approvato dall'utente il 14 ottobre**, con una modifica: la Madre non si vede («Sì, ma senza l'occhio della
Madre»). È la proposta A «Le regole», scelta il 14 ottobre fra tre storyboard: 70 secondi, 1920×1080 a 30 fotogrammi
al secondo, H.264 e AAC, in inglese. Le versioni sono due, uguali fino all'ultima scritta:

- `trailer_le_regole.mp4` (40 MB): finisce con «Wishlist now». È quella della pagina «Prossimamente», finché
  la demo non è su Steam;
- `trailer_le_regole_con_demo.mp4` (40 MB): sotto «Wishlist now» c'è anche «Free demo: the first two nights»,
  per quando la demo è su Steam. Allora si carica questa e si toglie l'altra.

Si caricano su Steamworks in **Store page admin → Trailers**: il primo della lista è quello che Steam fa partire in
cima alla pagina.

1. 0:00-0:12 · Nero, il mare. La luce si accende sulla barca nella nebbia; la radio della prima notte coi sottotitoli:
   «Hello? First night. By six, eight fish in the bucket: they're for the Mother. If they don't come, she takes
   another child.»
2. 0:12-0:19 · Si pesca: il lancio, l'abboccata, il recupero; la pagina di un pesce del Catalogo.
3. 0:19-0:48 · Gli otto, uno alla volta, ognuno con la sua regola a tutto schermo nel momento in cui il pescatore la
   rispetta: Gulpy «Feed him», Molly «Watch her», Hatch «Hide» (scende il telone), Robin «Light in his face» (la luce
   al massimo, scappa), Archie «Light off» (la luce si spegne), Lampy «Don't strike», Fangy «Stay quiet», Soggy nel
   binocolo «Don't lose sight of him». Le parole sono quelle delle schede della notte extra.
4. 0:48-0:57 · La Madre, senza vederla: il sonar a tutto schermo, la sua eco enorme che arriva e passa sotto la
   barca; poi la prua, il mare che si ferma, la luce che trema e la barca che si alza e si inclina sulla sua schiena.
   «Don't move». La musica si taglia, resta il cuore.
5. 0:57-1:01 · Il jumpscare di Molly, il segnale perso, il silenzio.
6. 1:01-1:10 · L'insegna al neon che si accende a scatti, «Wishlist now» (nella seconda versione anche «Free demo:
   the first two nights»).

Le scritte si leggono anche senza audio: su Steam il trailer parte muto. Le scene sono il motore del gioco, fotogramma
per fotogramma, con la nebbia accesa; i mostri si muovono con le loro animazioni vere (gli stati della simulazione, i
gesti del pescatore coi tasti). Il suono è fatto coi suoni del gioco, con la voce della radio e la conta di Hatch come le
fa il gioco.

## Come si rifanno

- **Capsule e logo della libreria**: `tools/.venv/bin/python tools/render/steam.py componi`. Parte dalle immagini
  di partenza in `sorgenti/` e dal logo del gioco (`public/assets/img/logo/logo.webp`).
- **Le immagini di partenza e l'immagine larga della libreria**: `tools/.venv/bin/python tools/render/steam.py
  render <ritratti.blend>`, con la scena dei ritratti (`tools/render/ritratti.py scena <blend> molly`). Sono il
  ritratto del menu (1920×1080), quello verticale (1200×1800) e quello largo (3840×1240, obiettivo 16 mm). Ci
  vogliono circa 45 minuti.
- **Gli screenshot**: `node scripts/steam_screenshot.mjs`, col gioco aperto con `npm run dev`. Ci vogliono circa
  25 minuti. Vengono le stesse scene, con piccole differenze da quelli approvati (la grana, le luci e l'acqua che si
  muovono).

- **Il trailer**, in tre passi, col gioco aperto con `npm run dev`:
  1. `node scripts/trailer.mjs <scene>`: le scene dal motore, una cartella di fotogrammi per scena (circa un'ora;
     `TRAILER_ANTEPRIMA=6` ne fa una prova veloce, un fotogramma ogni sei);
  2. `node scripts/voci.mjs <voci>`: la voce della radio e la conta di Hatch;
  3. `tools/.venv/bin/python tools/trailer/montaggio.py <scene> <voci>/voci.json steam/trailer/trailer_le_regole.mp4`:
     il montaggio, le scritte e il suono (pochi minuti). Con `--demo` la versione con la riga della demo gratuita in
     fondo (`trailer_le_regole_con_demo.mp4`); con `--crf 18` una copia più pesante e più fedele (circa 70 MB: Steam
     la ricomprime comunque); con `--fermi <cartella>` un fotogramma ogni mezzo secondo invece del video, per guardare
     il montaggio.

Se cambia il logo, si rifà `componi`. Se cambiano Molly o la scena, si rifanno `render` e poi `componi`. Se cambia
l'aspetto del gioco (nebbia, luci, mostri), si rifanno gli screenshot e il trailer.
