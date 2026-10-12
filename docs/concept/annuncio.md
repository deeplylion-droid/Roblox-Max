# L'annuncio (dopo «Nuova partita») — due proposte, DA APPROVARE

Come in FNAF: dopo «Nuova partita», per 3-4 secondi, l'annuncio con cui il pescatore ha trovato il lavoro, con una lenta
zoomata; poi la notte 1. Due anteprime a 1920×1080, come apparirebbero nel gioco:

- **A · il ritaglio di giornale**: `annuncio_giornale.jpg`
- **B · il volantino del parco**: `annuncio_volantino.jpg`

Script: `tools/render/annuncio.py` (composizione 2D in Python, senza Blender: la stampa si compone su un foglio piatto,
poi il foglio si posa nella scena e si illumina coi suoi rilievi). Per avere margine nella zoomata:
`tools/.venv/bin/python tools/render/annuncio.py tutti --scala 1.5` dà 2880×1620. Font SIL OFL (Google Fonts) in
`tools/render/fonts/annuncio/`.

## A · Il ritaglio di giornale

Il ritaglio della pagina 15 della **Gazzetta del Golfo**, posato sul banco della barca alla luce della lanterna:
ingiallito, piegato in quattro, con le macchie d'acqua vecchie e un angolo ancora bagnato, dove la carta diventa
trasparente e ci si vede il legno sotto (e il retro della pagina in controluce). L'angolo in basso a destra è strappato.

> Il nome: per il giornale ho usato **Gazzetta del Golfo**, quello che c'è già nella lore (i ritagli pescati, LORE.md),
> invece di «Il Gazzettino della Baia». Se preferite l'altro si cambia in una riga.

Nessun anno sulla pagina (il gioco non ne ha uno): la testatina dice solo «Martedì».

**L'annuncio**, in un riquadro, cerchiato due volte a penna rossa a mano libera (tratto tremolante, il cerchio che non
chiude, l'inchiostro che sbava un poco sulla carta umida):

> **CERCASI PESCATORE** per il turno di notte. Barca, luce e attrezzatura fornite. Dalle 0 alle 6. Paga in contanti
> all'alba. Nessuna esperienza richiesta. Presentarsi al molo vecchio, al tramonto.

Per la zoomata: il centro dell'annuncio cerchiato è a **x = 0,55, y = 0,37** dell'immagine.

**L'articolo**, tagliato dal bordo sinistro del ritaglio (del titolo si vede uno spicchio della parola prima):

- occhiello: *Il parco acquatico sulla baia · Il Comune rinvia ancora la demolizione*
- titolo: *(Così)* **SPLASHLAND RESTA CHIUSO**
- sommario: *Dei bambini nessuna traccia. Al bando per abbattere il parco non risponde nessuno: i cancelli restano
  sbarrati, la grande vasca è ancora piena d'acqua.*
- foto in mezzatinta: l'ingresso del parco (dal render del binocolo), didascalia: *L'ingresso di Mama Marina's
  Splashland, com'è oggi. Lo striscione della «Night Splash» non è del 1997: nessuno sa chi l'abbia appeso.*
- il testo: il consiglio comunale e la demolizione che nessuno vuole fare; la Night Splash del 14 agosto 1997 e le
  ricerche nella Deep End; la mareggiata del 2001; le luci della Deep End che si accendono ancora con la corrente
  staccata; le barche che escono ogni notte dal molo vecchio («In paese nessuno chiede che cosa peschino, né per chi»);
  il custode che aveva chiuso i cancelli e li trovò aperti; la madre che porta i fiori all'edicola sullo scoglio; la
  ditta che se n'è andata lasciando le ruspe. (Il testo intero è in `ARTICOLO`, nello script.)

**Gli altri annunci** (piccoli annunci veri di un paese di mare; i dettagli inquietanti sono appena accennati, in corsivo
qui sotto):

- LAVORO: azienda ittica cerca addetti, turno del mattino · *baby sitter per due bambini, solo di giorno* · signora
  referenziata offresi per pulizie.
- IMMOBILI: affittasi bilocale vista baia, *libero tutto l'anno* · vendesi villetta, *i proprietari si trasferiscono al
  più presto* · affittasi posto barca al molo vecchio, *il precedente affittuario non l'ha più ritirata*.
- BARCHE E MOTORI: vendesi gozzo in legno 6 m, Lombardini, *usato poco: solo di giorno* · cedesi negozio di articoli
  da pesca, causa trasferimento · vendesi fuoribordo 15 cv.
- COMPRAVENDITA: *vendo lettino, seggiolone, braccioli e un salvagente a paperella, praticamente nuovi; regalo a chi
  viene a prenderli* · compro vecchie cartoline e souvenir della baia.
- SMARRITI E TROVATI: *smarrito cane Bricco, visto l'ultima volta sul molo vecchio, di sera: abbaiava verso l'acqua* ·
  *trovato braccialetto di gomma azzurro con la scritta «NIGHT SPLASH»*.
- VARIE: *si ringrazia chi ha riportato in porto la barca «Santa Rita», trovata alla deriva all'alba; del proprietario
  si chiedono ancora notizie* · lezioni di nuoto in piscina, *al mare, no* · cerco compagno per pesca la domenica ·
  *messa in ricordo dei bambini della baia* · vendo bicicletta da bambina con le rotelle · riparazione reti.
- Riquadri: **Pescheria da Nino**, pesce fresco ogni mattina, molo nuovo, *la notte siamo chiusi* · Farmacia di turno.

## B · Il volantino del parco

Un volantino A4 di Mama Marina's Splashland, stampato allegro e oggi sbiadito dal sole e fradicio, inchiodato con
quattro chiodi a un palo del molo, sotto una cima legata. Di notte, alla luce della torcia. L'angolo in alto a destra è
strappato via (sotto il chiodo resta un pezzetto); le gocce, i rigoli, i colori colati, la ruggine dei chiodi. Dietro,
fuori fuoco, la baia: le luci del paese e il faro a sinistra; a destra la ruota panoramica, l'insegna rosa e azzurra, le
luci verdi della Deep End sott'acqua e, in controluce, la sagoma della statua di Mama Marina.

Mama Marina fedele al modello della statua (`tools/render/mascot.py`): la balena blu a pinne aperte, la pancia crema, le
guance rosa, gli occhioni con tre ciglia, il sorriso, lo zampillo dello sfiatatoio, i tre pesciolini in grembo
(arancione, giallo, verde). Le scritte del parco in Limelight, come l'insegna dell'ingresso.

I testi:

- MAMA MARINA'S **SPLASHLAND**
- **CERCHIAMO TE!**
- nel fumetto di Mama Marina: «**I nostri piccoli hanno fame!**»
- sul nastro: **TURNO DI NOTTE · SI PESCA DALLA BARCA**
- ★ Barca, luce ed esca fornite ★ Dalle 0 alle 6 ★ Paga in contanti all'alba ★ Nessuna esperienza!
- *Ti aspettiamo al molo vecchio, al tramonto!*
- sulle onde in fondo: *Mama Marina loves her little ones!*
- le linguette da strappare: **MOLO VECCHIO · AL TRAMONTO**. Sono nove: **sei sono già state strappate** (altri hanno
  risposto prima di te), ne restano tre.

## Cosa resta da fare

- La scelta tra A e B (e i ritocchi richiesti).
- La versione inglese della proposta scelta (testi tradotti, stessa impaginazione: lo script ha i testi in costanti).
- Nel motore: la schermata di 3-4 s con la zoomata lenta verso l'annuncio (per A, verso x 0,55 · y 0,37); conviene
  usare la versione a `--scala 1.5` perché la zoomata non sgrani.
