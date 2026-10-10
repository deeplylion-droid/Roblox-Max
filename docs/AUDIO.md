# SPLASHLAND IS CLOSED! — Specifica audio

Tutto l'audio è **sintetizzato da script** in `tools/audio/` (Python + numpy/scipy, nessun campione esterno) e scritto in `public/assets/audio/<id>.ogg` (Vorbis, 48 kHz, qualità ~6). Il manifest `public/assets/audio/manifest.json` elenca per ogni id: `file`, `duration` (s), `loop` (bool), `channels`, `gain` consigliato (lineare, 0..1) e `category` (`amb`, `sfx`, `mon`, `mus`, `ui`, `voice`).

Rigenerazione: `tools/.venv/bin/python tools/audio/generate.py [id...] [--spectro] [--jobs N]` (deterministico: seed fissi per id; `--spectro` scrive gli spettrogrammi di controllo in `tools/audio/cache/`).

> **Stato (9 ottobre 2026): tutti i suoni sono stati rifatti e sono DA APPROVARE.** Nuovi: musica e stinger, interfaccia, tutti i versi delle creature (con i tre jumpscare), `sonar_warn`. Rifatti: mare, alba, telone, bordone, scricchiolii, schizzi, tonfi, lancio della lenza, plop, lenza in tensione, filo che si spezza, secchio, lancio del pesce, battito, sonar, statica. Nella notte fra il 9 e il 10 ottobre ho rifatto anche gli ultimi rimasti: vento, lampara, statica radio, campane, sirena, campanellino, mulinello, pesce fuori dall'acqua, interruttore e tremolio della lampara, telone e radio. La lampara ora è coerente con il GDD (elettrica, a batteria): sibilo della lampada e ronzio del reattore, niente più valvola del gas.

## Organizzazione degli script

- `dsp.py`: mattoni (filtri, rumori periodici, voce a formanti, riverberi, limitatore, misure).
- `instruments.py`: modelli di medio livello (acqua: bolle, gocce, schizzi, colpi d'onda; legno; corpi bagnati; campane e lamelle; respiri, gabbiani, balene).
- `creatures.py`: modelli dei versi (voce irregolare con jitter e shimmer variabili, diplofonia, fry, ruvidità da urlo; gola bagnata, saliva, deglutizioni; ossa, denti, masticazione; nocche, unghie, passi bagnati, gomma; compressione e saturazione per bande degli urli).
- `sounds/`: un modulo per tema (`ambience`, `world`, `fishing`, `gulpy`, `molly`, `hatch`, `music`, `ui`); ogni id si registra con `@sound(...)` o `register(...)`.
- `master.py`: pulizia, livello (RMS "attivo"), limitatore, codifica Vorbis e verifica sul file decodificato (lunghezza, picco, giunzione del loop).

## Regole tecniche

- **Mono** per tutto ciò che viene spazializzato nel mondo (mostri, campanellino, mulinello, secchio, scafo). **Stereo** per ambienti, musica, UI e stinger. Fanno eccezione, stereo, il dondolio della barca (`molly_rock`, intorno a te) e i jumpscare (in faccia, non spazializzati).
- Loop **senza cuciture**: costruiti in modo circolare (eventi, filtri e riverberi che escono dalla fine rientrano dall'inizio) e con lunghezza esatta in campioni; il generatore misura la giunzione sul file decodificato.
- Picco ≤ −1 dBFS; nessun clipping digitale. Livelli indicativi (RMS "attivo"): ambienti −30…−24 dBFS, effetti −20…−14, versi delle creature −19…−15, jumpscare −8…−6 (forti ma non saturati: compressione e saturazione morbida per bande, rotazione di fase).
- Code di riverbero incluse nel file (non c'è riverbero in tempo reale), salvo diversa indicazione.
- Niente silenzio inutile in testa: l'attacco parte entro 5 ms (tranne dove indicato).
- I versi hanno sempre un filo di contenuto acuto (fiato, saliva, gocce): senza, in cuffia l'HRTF non riesce a dire da dove arrivano.

## Ambienti (loop, stereo)

| id | durata | descrizione |
|---|---|---|
| `amb_sea` | 32 s | Sciabordio contro uno scafo di legno, mare calmo: il mare respira con l'onda lunga (8 cicli nel loop). A ogni cresta l'acqua sbatte su un fianco e, poco dopo e più piano, sull'altro (l'onda passa sotto la barca); nel cavo quasi silenzio, gorgoglii fra le tavole, bollicine, raramente un piccolo schizzo. Letto d'acqua lontano basso, perché i colpi si stacchino. *Rifatto, da approvare.* |
| `amb_wind` | 30 s | Vento notturno debole sul mare aperto: raffiche lente che arrivano da un lato e passano all'altro; con la raffica il soffio si schiarisce e l'acqua fruscia sotto; le cime e il palo della lampara cantano appena (toni eolici che salgono e scendono con l'aria). Nelle raffiche più forti, raro e sordo in fondo al vento, il bordo del telone e la cima che tocca il palo. Quasi impercettibile. *Approvato con una correzione (10 ottobre: «troppo forte la parte del telone, fastidiosissima»): il telone è 16 dB più basso, più sordo, la metà delle volte. Riascoltato e approvato.* |
| `amb_lamp` | 20 s | La lampara elettrica accesa sul buttafuori: un ronzio morbido e basso del reattore (100 Hz rotondo, poche armoniche) che respira appena con la tensione della batteria, un velo d'aria calda attorno alla campana, rari tic sordi del metallo caldo, due volte una falena contro il vetro. *Rifatta (10 ottobre: bocciata, «forte e sgranata»): niente più sibilo frigolante, circa 13 dB più bassa all'orecchio. Approvata.* |
| `amb_drone` | 24 s | Bordone sub-basso inquietante (quarte sovrapposte, 30–80 Hz) con battimenti lenti; lontanissimi, due richiami di balena e due gemiti di lamiera del relitto del peschereccio che si piega sott'acqua. *Corretto (10 ottobre: «rumore di fondo eccessivo»): il soffio di pressione era il fruscio che si sentiva, ora è scuro e 16 dB più basso; anche il rombo sotto è più leggero. Approvato.* |
| `amb_tarp` | 16 s | Sotto il telone: mare ovattato (passa-basso ~600 Hz) con i colpi d'onda nuovi, tela che si muove appena, respiro trattenuto molto basso. *Da approvare.* |
| `amb_dawn` | 24 s | Alba: il mare si è calmato (colpetti radi e leggeri), la risacca sulla riva lontana, una brezza, i gabbiani che si chiamano dalla baia (ora si sentono). Livelli fissati sull'RMS di ogni strato. *Rifatto, da approvare.* |
| `radio_static` | 10 s | Il baracchino VHF acceso col silenziatore quasi chiuso: il canale aperto respira appena (un soffio scuro e liscio nel piccolo altoparlante), il ronzio dell'alimentazione, rari crepitii morbidi di scariche lontane, debolissimo il fischio di una portante alla deriva. *Corretta (10 ottobre: «abbassalo e riduci il rumore al minimo»): 13 dB più bassa, il fruscio quasi tutto via. Approvata.* |

## Mondo e orologio (mono, tranne dove indicato)

| id | durata | descrizione |
|---|---|---|
| `bell_toll` | 8 s | Un rintocco del campanile del paese, dall'altra parte della baia: campana grave (Sol3), il colpo metallico del battaglio, le parziali che si spengono ognuna col suo tempo e l'hum che resta per ultimo; la distanza si mangia gli acuti, arrivano il riverbero del paese e l'eco dai faraglioni, l'aria fa ondeggiare appena il livello. **Stereo**. *Rifatto, da approvare.* |
| `bell_dawn` | 9 s | Le sei: cinque campane a distesa (Do maggiore) che prendono slancio una dopo l'altra e si inseguono, la grande più lenta; il battaglio colpisce un lato e poi l'altro (due voci per campana); verso i 6,5 s le lasciano andare e resta la coda nella baia. **Stereo**. *Rifatto, da approvare.* |
| `foghorn` | 7 s | Sirena da nebbia lontanissima, dal faro: diafono a due toni (alto, poi basso), la pressione che sale all'inizio di ogni fiato e alla fine il «grugnito» (il tono che crolla mentre l'aria finisce e il pistone sbatacchia); niente acuti, il livello che ondeggia nell'aria umida, riverbero della baia e due echi dalla costa. **Stereo**. *Rifatto, da approvare.* |
| `creak_1`…`creak_4` | 0,65–1,45 s | Scricchiolii del legno della barca: attrito a strappi (il legno "prende" e "molla") con frequenza che vaga, tavole che risuonano, un po' di scafo sotto. 1 tavola del pagliolo, 2 gemito lungo del fasciame con un cigolio a metà, 3 "cre-eak" in due tempi, 4 scalmo e cima (più tonale). *Rifatti, da approvare.* |
| `splash_s1`…`splash_s3` | 0,5–0,85 s | Piccoli schizzi: impatto a banda larga, spruzzo a strappi, la cavità che si richiude in un "plop" corto, bollicine, la pioggia di gocce (soprattutto ticchettii, poche "plink"). *Rifatti, da approvare.* |
| `splash_big` | 1,6 s | Qualcosa di pesante che rientra: il tonfo grave della cavità che collassa, il getto che ricade in un secondo schizzo, la pioggia di gocce, una nuvola di bolle grosse che risale. *Rifatto, da approvare.* |
| `hull_thump` | 0,75 s | Qualcosa di grosso urta lo scafo da sotto: la barca risuona come un tamburo sordo, la roba a bordo sobbalza, l'acqua sciaborda lungo i fianchi. *Rifatto, da approvare.* |

## Pesca e oggetti (mono)

| id | durata | descrizione |
|---|---|---|
| `cast` | 1,1 s | Scatto dell'archetto, la frusta della canna (fruscio netto che segue la velocità della punta + fischio della vetta), poi il filo che corre via dalla bobina: sibilo fino che sfarfalla contro il primo anello e rallenta. *Rifatto, da approvare.* |
| `plop` | 0,4 s | Il piombo con l'esca che entra in acqua: tic dell'impatto, un "plup" corto con poca salita di tono, due bollicine, qualche goccia. *Rifatto, da approvare.* |
| `rod_bell_1`, `rod_bell_2` | 1,2 s | Due campanellini d'ottone su una molletta in punta alla canna. Ogni strattone fa oscillare la vetta (circa 5 volte al secondo, sempre meno): il battaglio colpisce agli estremi dell'oscillazione, ribattuto all'inizio e poi sempre più piano; la molletta ticchetta. 1 due strattoni; 2 tre beccate leggere e poi lo strattone. *Rifatti, da approvare.* |
| `reel_loop` | 0,48 s | Un giro di manovella, loop esatto (la velocità la regola il gioco col playbackRate): la mano accelera e rallenta nel giro e tutto la segue; il cricchetto dell'antiritorno scatta 12 volte, gli ingranaggi girano col loro fischio di denti, il filo si avvolge sulla bobina, il rullino dell'archetto cigola appena. *Approvato. Nel gioco il loop è continuo (misurato sul file); il salto che si sentiva nella pagina lo faceva il lettore mp3, che aggiunge un attimo di silenzio a ogni giro. Gli scatti ora cadono a mezzo passo dalla giunzione.* |
| `line_tension` | 2 s | Lenza sotto sforzo, loop: la canna che si flette e scricchiola a strappi, la frizione del mulinello che slitta a scatti ("zzzt", raffiche di scatti metallici), il filo che taglia l'acqua (sibilo) e canta appena. *Approvato. Nel gioco il loop è continuo (misurato sul file); il salto della pagina era del lettore mp3.* |
| `line_snap` | 0,6 s | Il filo che cede: uno schiocco secco e brillante, il moncone che frusta l'aria e picchietta sugli anelli, la canna che torna su di scatto (fruscio grave e un colpetto nel mulinello); solo un'ombra di vibrazione smorzata (il nylon non "canta" come una corda). *Rifatto, da approvare.* |
| `fish_out` | 1,2 s | Il pesce tirato fuori: la superficie che si rompe e il risucchio della cavità che si richiude, il pesce che si dibatte in aria, ogni colpo di coda lancia gocce che ricadono sul mare poco dopo, l'acqua che gli cola di dosso, il filo che sibila negli anelli. *Rifatto, da approvare.* |
| `fish_bucket` | 0,95 s | Il pesce sul fondo di un secchio di lamiera zincata con un dito d'acqua: tonfo carnoso, la lamiera (modi fitti e inarmonici) smorzata dal corpo bagnato; poi i colpi di coda contro le pareti, più acuti e sempre più deboli; l'acqua che sciaguatta. *Rifatto, da approvare.* |
| `fish_throw` | 0,7 s | Il lancio di un pesce a Gulpy: il pesce afferrato nel secchio (scivola bagnato, la coda tocca la lamiera), il braccio che lancia (fruscio), il pesce che vola perdendo gocce e sbattendo la coda. L'arrivo non c'è più (suonava nel punto del pescatore): lo fa il morso dentro `gulpy_eat`. *Rifatto, da approvare.* |
| `lamp_switch` | 0,3 s | Il commutatore della lampara: la manopola di bachelite che gira sulla camma (un tic) e scatta sulla tacca (un clac secco con la scatola che risuona), il contatto che sfrigola un attimo, il reattore che cambia ronzio. *Rifatto, da approvare.* |
| `lamp_flicker` | 0,7 s | La lampara che tremola: la scarica s'interrompe e riprende a scatti (sibilo e ronzio cadono e tornano), a ogni ripresa il contatto crepita, nei cali il reattore ronza ruvido. *Rifatto, da approvare.* |
| `tarp_in` | 1,1 s | Ci si infila sotto il telone di tela cerata: la mano che afferra la tela, il telone tirato sopra la testa (fruscio pesante, aria spostata), le ginocchia sulle tavole e il corpo che scivola sul pagliolo, il telone che ricade con un tonfo morbido e si assesta, già ovattato. *Rifatto, da approvare.* |
| `tarp_out` | 0,9 s | Si esce dal telone: la tela spinta su di colpo, buttata indietro con un colpo d'aria, che ricade dietro sul banco; torna l'aria aperta. *Rifatto, da approvare.* |
| `heartbeat` | 1 s, **loop** | Il battito sentito da dentro: "lub" grave e pieno, "dub" più corto e un po' più alto, il sangue che pulsa nelle orecchie. Ora è un loop vero (60 al minuto; il gioco lo accelera col playbackRate). *Rifatto, da approvare.* |
| `sonar_ping` | 2,2 s | Ping dell'ecoscandaglio: tono che cala appena con il tic del trasduttore, coda d'acqua densa che ondeggia, eco dal fondo più scura e più grave, sotto il crepitio dei gamberetti. **Stereo**. *Rifatto, da approvare.* |
| `sonar_blip` | 0,15 s | Bip di un contatto: il cicalino piezoelettrico (onda quasi quadra, risonanza acuta). *Rifatto, da approvare.* |
| `sonar_warn` | 0,9 s | **Nuovo.** L'avviso quando sale qualcosa di grosso: due bip più gravi e sporchi (il secondo più basso), ognuno con un colpo sordo sotto. Lo usa `Sfx.sonarWarn()`. *Da approvare.* |
| `radio_on` / `radio_off` | 0,45 / 0,4 s | Il baracchino: lo scatto del pulsante e lo squelch che si apre ('kshh') finché la portante aggancia e il fruscio crolla; in chiusura la coda dello squelch ('kshhht') che si chiude secca e lo scatto. Tutto dal piccolo altoparlante. *Rifatti, da approvare.* |
| `static_burst` | 1,5 s | Il segnale che salta (dopo il jumpscare): schiocco elettrico, neve televisiva a strappi, ronzio a 50 Hz di un televisore che perde il quadro, fischi che strisciano come le righe di un nastro rovinato, il tubo che si spegne. **Stereo**. *Rifatto, da approvare.* |

## Voce radio (mono)

`voice_01` … `voice_24` (60–220 ms ciascuno): sillabe borbottate di un vecchio pescatore, voce roca e bassa (fondamentale ~95–120 Hz con jitter), vocali diverse (a, e, i, o, u con formanti realistiche) e consonanti accennate, già filtrate come una radio (passa-banda 300–3000 Hz, leggera saturazione). Il gioco le concatena a caso mentre scorrono i sottotitoli (stile "animalese" ma umano e malinconico). *Non ancora generati: oggi la radio usa la voce sintetica al volo di `src/engine/voice.ts` (profilo `RADIO_VOICE`).*

## Le creature (mono) — DA APPROVARE

**I mostri non parlano: solo versi.** L'unica eccezione è la conta di Hatch fino a dieci (testo approvato, vedi `LORE.md`), che resta la voce sintetica di `src/engine/voice.ts`.

I versi sono file (categoria `mon`, mono, spazializzati dal gioco) con più varianti: `src/app/sfx.ts` ne sceglie una a caso, mai la stessa due volte di fila, con piccole variazioni d'intonazione (±3–5%) e di volume (±1,5 dB). Se un file manca resta il ripiego sintetizzato al volo. Tecnica comune: voce a formanti con sorgente glottale irregolare (jitter, shimmer, diplofonia e fry che cambiano nel tempo), più gole leggermente diverse sovrapposte, fiato filtrato dal tratto vocale, gola bagnata (gargarismo, bolle basse, pettine acquoso), un'ombra di spazio ravvicinato.

### Gulpy — prua, va sfamato
Un gigante: tratto vocale lungo quasi il doppio di quello di un uomo (formanti a ×0,56), voce a 30–80 Hz piena di subarmoniche, sempre bagnata.

| id | durata | descrizione |
|---|---|---|
| `gulpy_breath_1`…`3` | 1,95–2,45 s | Fiato affamato: 1 inspiro umido dalla bocca enorme e un espiro lungo con il lamento sotto; 2 espiro dalle labbra molli che sbattono, un mugolio che sale e ricade, le labbra che si richiudono appiccicose; 3 due inspiri corti e avidi (fiuta il pesce) e un espiro roco con il fry. |
| `gulpy_gurgle_1`…`4` | 1,4–1,85 s | Gorgoglio affamato: 1 "ghhuurrll" basso con la gola piena d'acqua; 2 il richiamo della fame, un lamento che sale aprendo la bocca e ricade, poi un piccolo "glk"; 3 solo acqua in gola che ribolle, due "glonk", bava; 4 ringhio col fry che gratta sul fondo della gola. |
| `gulpy_rubber_1`, `2` | 0,85–0,95 s | Il salvagente a paperella: 1 la gomma tesa che sfrega sulla carne bagnata del collo; 2 il fischietto della paperella schiacciato dal collo che si gonfia, un guaito di gomma sfiatato. |
| `gulpy_jaw` | 1,75 s | La mascella che si sgancia fino al petto: legamenti che scricchiolano, due schiocchi d'osso piccoli e uno enorme, la carne che si stira, i fili di bava che si spezzano, poi il fiato dalla bocca spalancata. |
| `gulpy_eat_1`, `2` | 3,6 / 3,3 s | Mangia: un inspiro avido a bocca spalancata mentre il pesce vola, il morso secco dei denti ad ago **a 0,42 s** (quando il pesce arriva: `night.ts` chiama `chew()` nell'istante del lancio), la masticazione (carne schiacciata, lische che si spezzano), la deglutizione enorme ("glunk" grave col tono che scende), un rutto d'acqua soddisfatto. |
| `gulpy_rise` | 2,7 s | Emerge lontano davanti alla prua: l'acqua che si gonfia e si rompe, l'acqua che gli cade di dosso a scrosci dalle spalle enormi, uno sbuffo da balena (fiato e spruzzi da una gola gigante), un gemito affamato. Per `Sfx.emerge('gulpy', pos)` (oggi al suo posto suona `splash_s3`). |
| `gulpy_grab` | 2,1 s | Riemerge aggrappato alla prua: due mani enormi e bagnate che sbattono sul capodibanda, la prua che affonda sotto il suo peso e geme, l'acqua che gli cola dalle braccia, un fiato enorme. Per `Sfx.grab(pos)` (oggi al suo posto suonano `hull_thump` + `creak_3`). |
| `js_gulpy` | 1,4 s | Jumpscare (**stereo**): l'acqua che esplode, un ruggito enorme e bagnato (tre gole) con sopra uno strillo da maiale dalla stessa gola, i denti ad ago che si chiudono davanti alla faccia. RMS ≈ −7,2 dBFS. |

### Molly — fianchi, va fissata
Una bambina di sette anni (formanti a ×1,4, tanto soffio) ma bagnata e "doppia": sotto, a tratti, la stessa voce da una gola molto più grande, a un intervallo mai d'ottava esatta (suona sbagliato).

| id | durata | descrizione |
|---|---|---|
| `molly_knock_1`…`3` | 1,1–1,65 s | Le nocche lunghe sul fasciame (contatto osseo, tavole che risuonano, un velo d'acqua): 1 tre colpi lenti e regolari, 2 "toc-toc… toc", 3 quattro colpi che accelerano e poi le unghie che grattano giù per le tavole. |
| `molly_peek` | 1,35 s | Si affaccia sul bordo: la testa che rompe il pelo dell'acqua e l'acqua che le cola di dosso, le dita lunghe che si posano bagnate sul capodibanda una dopo l'altra, i braccioli che stridono appena, un fiato piccolo e umido. Per `Sfx.peek(pos)` (oggi al suo posto suona `splash_s1`). |
| `molly_giggle_1`, `2` | 1,3 / 1,5 s | Risatine: 1 "hi-hi-hi-hi-hiii" che scende, l'ultima sillaba crolla di un'ottava come un nastro che rallenta e finisce in un gorgoglio, l'altra gola sempre più presente; 2 risata trattenuta e inspirata, stridula, poi due "he-he" più in basso e un sospiro con le bolle. |
| `molly_whine_1`, `2` | 2,05 / 1,95 s | Piagnucolio: 1 due singhiozzi con il tremito del pianto, in mezzo i singulti, il secondo con la voce che si spezza; 2 lamento a bocca chiusa (nasale) che trema, poi si apre. |
| `molly_tantrum_1`, `2` | 2,95 / 2,9 s | Capriccio: strilli di bambina ruvidi (con un tratto caotico e la voce che si spezza), schiaffi e pugni sullo scafo con l'acqua che schizza, il fasciame che geme mentre la barca comincia a dondolare, un singhiozzo; nel secondo calci nell'acqua e un ultimo pugno. |
| `molly_rock` | 9,6 s, loop | Il dondolio della barca quando si arrabbia (**stereo**, intorno a te): quattro inclinazioni da 2,4 s, il fasciame che geme verso il lato che scende, l'acqua che sbatte su quel fianco, quella di sentina che corre sotto il pagliolo, il manico del secchio e uno scalmo che sbattono; sotto, il mare smosso senza pause. Il volume lo dà la forza del dondolio. |
| `js_molly` | 1,35 s | Jumpscare (**stereo**): l'acqua che esplode, i braccioli di plastica che stridono, uno strillo altissimo di bambina (tre voci appena scordate) con sotto la gola enorme, ruvido e bagnato. RMS ≈ −7,3 dBFS. |

### Hatch — poppa, ci si nasconde
| id | durata | descrizione |
|---|---|---|
| `hatch_step_1`…`4` | 0,66–0,75 s | Passi pesanti di un piede palmato e bagnato sul pagliolo: tallone e pianta che schiaffeggiano il legno, la tavola che flette e geme, lo scafo che rimbomba, a volte gli artigli che toccano le tavole, il risucchio quando il piede si stacca, l'acqua che cola. |
| `hatch_sniff_1`…`3` | 1,05–1,2 s | Annusate forti da narici grandi e bagnate (risonanze nasali, crepitio di muco), poi lo sbuffo dalle fessure del naso e dalle branchie che sbattono; in due varianti il fiato sibila fra i denti di vetro che tintinnano. |
| `hatch_toy` | 12 s, loop | Il giocattolo luminoso che gli penzola davanti alla faccia: il fischio sottile della bobina che accende la luce (rumore a banda stretta, mai un tono pulito), un ronzio a scatti dei contatti della pila, l'acqua che sfrigola dentro, gocce, e due volte il chip musicale che prova a suonare la ninna nanna della Madre, rallentata e calante, e si inceppa. |
| `hatch_rise` | 2,1 s | Emerge dietro la poppa, altissimo: l'acqua che si apre e gli scorre giù dal corpo lungo e sottile, il giocattolo che si accende con uno scatto e comincia a ronzare balbettando, un fiato prima di contare. Per `Sfx.emerge('hatch', pos)` alla prima parola della conta (oggi al suo posto suona `splash_s3`). |
| `hatch_board` | 2,3 s | Sale a bordo dalla poppa: la mano enorme sul capodibanda, l'acqua che gli cola di dosso a fiotti, la poppa che affonda e geme, il piede sul pagliolo, un fiato lungo fra i denti di vetro. |
| `js_hatch` | 1,4 s | Jumpscare (**stereo**): i denti di vetro che scattano, il chip del giocattolo che impazzisce (arpeggio quadro della ninna nanna che sale e si strozza), l'urlo di un ragazzino dentro una gola roca e vuota con il raspo sotto, tre morsi a vuoto. RMS ≈ −7,6 dBFS. |

**La conta di Hatch** (`src/engine/voice.ts`, profilo `CHILD`, stessa API di `speak()`): ogni sillaba è ora un'onda glottale (non più un dente di sega) con tre formanti che scivolano da una sillaba all'altra, soffio sulle vocali, vibrato irregolare; il profilo del bambino ha formanti più alte (×1,36), la coda che cala alla fine di ogni parola, la "gola sotto" (la stessa sillaba poco meno di un'ottava più giù, da un tratto vocale enorme), un tremolio d'acqua nel fiato e la distanza (passa-basso e un'eco corta e scura dello scafo e dell'acqua). *Da approvare.*

## Musica e stinger (stereo) — DA APPROVARE

| id | durata | descrizione |
|---|---|---|
| `mus_title` | 64 s, loop | **Ninna nanna della Madre** al carillon (approvata; suona dall'avvertenza all'avvio fino al menu). La minore, 3/4, 67,5 BPM: 24 battute = 64 s esatti, forma A (8) – B (8) – A' (8). Tema A: Mi–Do | La–Si | Do Re Mi | Si…, poi Mi–Do | La–Sol♯ | La Si Do | La… (accordi La m, Fa, La m, Mi, La m, Mi, Re m, La m). Frase B più alta (La5–Fa5 | Mi–Do | Re–Si | Mi…) con le note sbagliate: un Re♯ (tritono, su un Si7) e un Si♭ che stride contro il Sol♯ (Mi–Si♭–Sol♯ → La). Nell'A' all'ultima battuta la tonica non arriva: la lamella è rotta e si sente solo il perno che la sfiora, mentre dal fondo, lontanissimo, sale per un attimo il lamento della Madre; poi il loop riparte senza essersi mai risolto. Carillon: lamelle d'acciaio a sbalzo (modi 1 : 6,27 : 17,5, il secondo forte nell'attacco), due lamelle gemelle per nota che battono piano, lo scatto del perno, il cilindro un po' impreciso (±4 ms), il valzer d'accompagnamento (basso sul primo tempo, due note dell'accordo sugli altri), la cassetta di legno, il ventolino del regolatore che frulla. Due lamelle stonate davvero (Do5 −27 centesimi, Fa5 +21), le altre entro ±9. Nastro vecchio: wow lento (±0,45%) e flutter, acuti consumati, un velo di soffio. Sotto, un pad sott'acqua molto basso (l'accordo di ogni battuta due ottave sotto, filtro che respira in 8 s), 17 dB sotto il carillon. |
| `mus_night_start` | 4 s | Inizio notte: un colpo basso e cupo con un rintocco grave di boa sotto, poi il carillon accenna l'inizio della ninna nanna (Mi–Do–La–Si), rallenta e si spegne nel riverbero, una lamella sempre più calante. |
| `mus_6am` | 7 s | Le sei: un accordo di La maggiore che si apre piano (archi morbidi, il filtro che sale), la ninna nanna finalmente in maggiore al carillon che sale fino alla tonica, celesta e campanelle, un respiro di sollievo. |
| `mus_gameover` | 8 s | Il carillon che si scarica: la ninna nanna rallenta, ogni lamella più calante (fino a quasi un semitono), l'ultima nota pizzicata appena; la molla si ferma con un tonfo del meccanismo. Sotto, un bordone grave che stride (La e Si♭) e cresce. |
| `mus_madre` | 10 s | La Madre si sveglia (quota mancata alle 6): un colpo enorme sott'acqua (una coda gigantesca che sposta l'acqua), poi un lamento lentissimo da balena abissale (la voce più grande che ci sia, formanti a ×0,4, con un canto più acuto che la accompagna) e dentro un coro grave in La minore (La1, Mi2, La2, Do3, Mi3; tre cantori scordati per voce) che sale e si ritira; bolle enormi che salgono dal fondo; tutto lontano, sotto l'acqua. |

## Interfaccia (stereo, brevi e discreti) — DA APPROVARE

Legno e ottone, come gli oggetti della barca.

| id | durata | descrizione |
|---|---|---|
| `ui_hover` | 40 ms | Un tic di legno appena accennato. |
| `ui_click` | 90 ms | Un nottolino di legno con il fermo d'ottone. |
| `ui_back` | 110 ms | Lo stesso gesto al contrario: lo scatto d'ottone e due colpetti di legno che scendono. |
| `ui_start` | 1,5 s | Un rintocco della campanella di bordo e il mare che risponde con un'onda lunga. |
| `ui_page` | 0,55 s | **Nuovo.** Si gira una pagina del Catalogo: la carta spessa che si stacca dalla pila, l'aria che la pagina sposta, qualche crepitio della carta vecchia, la pagina che si posa. *Da approvare.* |

## Come li usa il gioco

`src/app/sfx.ts` (classe `Sfx`): `gurgle(pos, gain)` (fiato o gorgoglio di Gulpy, ogni tanto la gomma; con `gain ≥ 1,3`, il momento in cui pretende, prima si sgancia la mascella), `chew(pos)` (`gulpy_eat`), `knock(pos)`, `giggle(pos)`, `whine(pos)`, `tantrum(pos)` (Molly), `step(pos)`, `sniff(pos)` (Hatch), `sonarWarn()` (`sonar_warn`), `scream(gain, pitch)` (compatibilità: sceglie il jumpscare dall'intonazione), più i nuovi `jumpscare(who)`, `emerge(who, pos)`, `jaw(pos)`, `grab(pos)`, `peek(pos)`, `board(pos)`, `rock(amount)` (loop `molly_rock`, da chiamare a ogni fotogramma con la forza del dondolio), `toy(amount, pos)` (loop `hatch_toy`) e `stopLoops()`. Musica, stinger e interfaccia si suonano con `AudioEngine.play(id)`; vanno sul bus `music` o `ui` in base alla categoria.
