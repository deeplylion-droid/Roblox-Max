# SPLASHLAND IS CLOSED! — Specifica audio

Tutto l'audio è **sintetizzato da script** in `tools/audio/` (Python + numpy/scipy, nessun campione esterno) e scritto in `public/assets/audio/<id>.ogg` (Vorbis, 48 kHz, qualità ~6). Il manifest `public/assets/audio/manifest.json` elenca per ogni id: `file`, `duration` (s), `loop` (bool), `channels`, `gain` consigliato (lineare, 0..1) e `category` (`amb`, `sfx`, `mon`, `mus`, `ui`, `voice`).

Rigenerazione: `tools/.venv/bin/python tools/audio/generate.py [id...] [--spectro] [--jobs N]` (deterministico: seed fissi per id; `--spectro` scrive gli spettrogrammi di controllo in `tools/audio/cache/`).

> **Stato (9 ottobre 2026): tutti i suoni sono stati rifatti e sono approvati (gli ultimi il 13 ottobre).** Nuovi: musica e stinger, interfaccia, tutti i versi delle creature (con i tre jumpscare), `sonar_warn`. Rifatti: mare, alba, telone, bordone, scricchiolii, schizzi, tonfi, lancio della lenza, plop, lenza in tensione, filo che si spezza, secchio, lancio del pesce, battito, sonar, statica. Nella notte fra il 9 e il 10 ottobre ho rifatto anche gli ultimi rimasti: vento, lampara, statica radio, campane, sirena, campanellino, mulinello, pesce fuori dall'acqua, interruttore e tremolio della lampara, telone e radio. La lampara ora è coerente con il GDD (elettrica, a batteria): sibilo della lampada e ronzio del reattore, niente più valvola del gas.

## Organizzazione degli script

- `dsp.py`: mattoni (filtri, rumori periodici, voce a formanti, riverberi, limitatore, misure).
- `instruments.py`: modelli di medio livello (acqua: bolle, gocce, schizzi, colpi d'onda; legno; corpi bagnati; campane e lamelle; respiri, gabbiani, balene).
- `creatures.py`: modelli dei versi (voce irregolare con jitter e shimmer variabili, diplofonia, fry, ruvidità da urlo; gola bagnata, saliva, deglutizioni; ossa, denti, masticazione; nocche, unghie, passi bagnati, gomma; compressione e saturazione per bande degli urli).
- `sounds/`: un modulo per tema (`ambience`, `world`, `fishing`, `gulpy`, `molly`, `hatch`, `robin`, `archie`, `lampy`, `fangy`, `foxy`, `immersioni`, `madre`, `finali`, `music`, `ui`); ogni id si registra con `@sound(...)` o `register(...)`.
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
| `amb_sea` | 32 s | Sciabordio contro uno scafo di legno, mare calmo: il mare respira con l'onda lunga (8 cicli nel loop). A ogni cresta l'acqua sbatte su un fianco e, poco dopo e più piano, sull'altro (l'onda passa sotto la barca); nel cavo quasi silenzio, gorgoglii fra le tavole, bollicine, raramente un piccolo schizzo. Letto d'acqua lontano basso, perché i colpi si stacchino. *Rifatto, approvato il 13 ottobre.* |
| `amb_wind` | 30 s | Vento notturno debole sul mare aperto: raffiche lente che arrivano da un lato e passano all'altro; con la raffica il soffio si schiarisce e l'acqua fruscia sotto; le cime e il palo della lampara cantano appena (toni eolici che salgono e scendono con l'aria). Nelle raffiche più forti, raro e sordo in fondo al vento, il bordo del telone e la cima che tocca il palo. Quasi impercettibile. *Approvato con una correzione (10 ottobre: «troppo forte la parte del telone, fastidiosissima»): il telone è 16 dB più basso, più sordo, la metà delle volte. Riascoltato e approvato.* |
| `amb_lamp` | 20 s | La lampara elettrica accesa sul buttafuori: un ronzio morbido e basso del reattore (100 Hz rotondo, poche armoniche) che respira appena con la tensione della batteria, un velo d'aria calda attorno alla campana, rari tic sordi del metallo caldo, due volte una falena contro il vetro. *Rifatta (10 ottobre: bocciata, «forte e sgranata»): niente più sibilo frigolante, circa 13 dB più bassa all'orecchio. Approvata.* |
| `amb_drone` | 24 s | Bordone sub-basso inquietante (quarte sovrapposte, 30–80 Hz) con battimenti lenti; lontanissimi, due richiami di balena e due gemiti di lamiera del relitto del peschereccio che si piega sott'acqua. *Corretto (10 ottobre: «rumore di fondo eccessivo»): il soffio di pressione era il fruscio che si sentiva, ora è scuro e 16 dB più basso; anche il rombo sotto è più leggero. Approvato.* |
| `amb_tarp` | 16 s | Sotto il telone: mare ovattato (passa-basso ~600 Hz) con i colpi d'onda nuovi, tela che si muove appena, respiro trattenuto molto basso. *Approvato il 13 ottobre.* |
| `amb_dawn` | 24 s | Alba: il mare si è calmato (colpetti radi e leggeri), la risacca sulla riva lontana, una brezza, i gabbiani che si chiamano dalla baia (ora si sentono). Livelli fissati sull'RMS di ogni strato. *Rifatto, approvato il 13 ottobre.* |
| `radio_static` | 10 s | Il baracchino VHF acceso col silenziatore quasi chiuso: il canale aperto respira appena (un soffio scuro e liscio nel piccolo altoparlante), il ronzio dell'alimentazione, rari crepitii morbidi di scariche lontane, debolissimo il fischio di una portante alla deriva. *Corretta (10 ottobre: «abbassalo e riduci il rumore al minimo»): 13 dB più bassa, il fruscio quasi tutto via. Approvata.* |

## Mondo e orologio (mono, tranne dove indicato)

| id | durata | descrizione |
|---|---|---|
| `bell_toll` | 8 s | Un rintocco del campanile del paese, dall'altra parte della baia: campana grave (Sol3), il colpo metallico del battaglio, le parziali che si spengono ognuna col suo tempo e l'hum che resta per ultimo; la distanza si mangia gli acuti, arrivano il riverbero del paese e l'eco dai faraglioni, l'aria fa ondeggiare appena il livello. **Stereo**. *Rifatto, approvato il 13 ottobre.* |
| `bell_dawn` | 9 s | Le sei: cinque campane a distesa (Do maggiore) che prendono slancio una dopo l'altra e si inseguono, la grande più lenta; il battaglio colpisce un lato e poi l'altro (due voci per campana); verso i 6,5 s le lasciano andare e resta la coda nella baia. **Stereo**. *Rifatto, approvato il 13 ottobre.* |
| `foghorn` | 7 s | Sirena da nebbia lontanissima, dal faro: diafono a due toni (alto, poi basso), la pressione che sale all'inizio di ogni fiato e alla fine il «grugnito» (il tono che crolla mentre l'aria finisce e il pistone sbatacchia); niente acuti, il livello che ondeggia nell'aria umida, riverbero della baia e due echi dalla costa. **Stereo**. *Rifatto, approvato il 13 ottobre.* |
| `creak_1`…`creak_4` | 0,65–1,45 s | Scricchiolii del legno della barca: attrito a strappi (il legno "prende" e "molla") con frequenza che vaga, tavole che risuonano, un po' di scafo sotto. 1 tavola del pagliolo, 2 gemito lungo del fasciame con un cigolio a metà, 3 "cre-eak" in due tempi, 4 scalmo e cima (più tonale). *Rifatti, approvati il 13 ottobre.* |
| `splash_s1`…`splash_s3` | 0,5–0,85 s | Piccoli schizzi: impatto a banda larga, spruzzo a strappi, la cavità che si richiude in un "plop" corto, bollicine, la pioggia di gocce (soprattutto ticchettii, poche "plink"). *Rifatti, approvati il 13 ottobre.* |
| `splash_big` | 1,6 s | Qualcosa di pesante che rientra: il tonfo grave della cavità che collassa, il getto che ricade in un secondo schizzo, la pioggia di gocce, una nuvola di bolle grosse che risale. *Rifatto, approvato il 13 ottobre.* |
| `hull_thump` | 0,75 s | Qualcosa di grosso urta lo scafo da sotto: la barca risuona come un tamburo sordo, la roba a bordo sobbalza, l'acqua sciaborda lungo i fianchi. *Rifatto, approvato il 13 ottobre.* |

## Pesca e oggetti (mono)

| id | durata | descrizione |
|---|---|---|
| `cast` | 1,1 s | Scatto dell'archetto, la frusta della canna (fruscio netto che segue la velocità della punta + fischio della vetta), poi il filo che corre via dalla bobina: sibilo fino che sfarfalla contro il primo anello e rallenta. *Rifatto, approvato il 13 ottobre.* |
| `plop` | 0,4 s | Il piombo con l'esca che entra in acqua: tic dell'impatto, un "plup" corto con poca salita di tono, due bollicine, qualche goccia. *Rifatto, approvato il 13 ottobre.* |
| `rod_bell_1`, `rod_bell_2` | 1,2 s | Due campanellini d'ottone su una molletta in punta alla canna. Ogni strattone fa oscillare la vetta (circa 5 volte al secondo, sempre meno): il battaglio colpisce agli estremi dell'oscillazione, ribattuto all'inizio e poi sempre più piano; la molletta ticchetta. 1 due strattoni; 2 tre beccate leggere e poi lo strattone. *Rifatti, approvati il 13 ottobre.* |
| `reel_loop` | 0,48 s | Un giro di manovella, loop esatto (la velocità la regola il gioco col playbackRate): la mano accelera e rallenta nel giro e tutto la segue; il cricchetto dell'antiritorno scatta 12 volte, gli ingranaggi girano col loro fischio di denti, il filo si avvolge sulla bobina, il rullino dell'archetto cigola appena. *Approvato. Nel gioco il loop è continuo (misurato sul file); il salto che si sentiva nella pagina lo faceva il lettore mp3, che aggiunge un attimo di silenzio a ogni giro. Gli scatti ora cadono a mezzo passo dalla giunzione.* |
| `line_tension` | 2 s | Lenza sotto sforzo, loop: la canna che si flette e scricchiola a strappi, la frizione del mulinello che slitta a scatti ("zzzt", raffiche di scatti metallici), il filo che taglia l'acqua (sibilo) e canta appena. *Approvato. Nel gioco il loop è continuo (misurato sul file); il salto della pagina era del lettore mp3.* |
| `line_snap` | 0,6 s | Il filo che cede: uno schiocco secco e brillante, il moncone che frusta l'aria e picchietta sugli anelli, la canna che torna su di scatto (fruscio grave e un colpetto nel mulinello); solo un'ombra di vibrazione smorzata (il nylon non "canta" come una corda). *Rifatto, approvato il 13 ottobre.* |
| `fish_out` | 1,2 s | Il pesce tirato fuori: la superficie che si rompe e il risucchio della cavità che si richiude, il pesce che si dibatte in aria, ogni colpo di coda lancia gocce che ricadono sul mare poco dopo, l'acqua che gli cola di dosso, il filo che sibila negli anelli. *Rifatto, approvato il 13 ottobre.* |
| `fish_bucket` | 0,95 s | Il pesce sul fondo di un secchio di lamiera zincata con un dito d'acqua: tonfo carnoso, la lamiera (modi fitti e inarmonici) smorzata dal corpo bagnato; poi i colpi di coda contro le pareti, più acuti e sempre più deboli; l'acqua che sciaguatta. *Rifatto, approvato il 13 ottobre.* |
| `fish_throw` | 0,7 s | Il lancio di un pesce a Gulpy: il pesce afferrato nel secchio (scivola bagnato, la coda tocca la lamiera), il braccio che lancia (fruscio), il pesce che vola perdendo gocce e sbattendo la coda. L'arrivo non c'è più (suonava nel punto del pescatore): lo fa il morso dentro `gulpy_eat`. *Rifatto, approvato il 13 ottobre.* |
| `lamp_switch` | 0,3 s | Il commutatore della lampara: la manopola di bachelite che gira sulla camma (un tic) e scatta sulla tacca (un clac secco con la scatola che risuona), il contatto che sfrigola un attimo, il reattore che cambia ronzio. *Rifatto, approvato il 13 ottobre.* |
| `lamp_flicker` | 0,7 s | La lampara che tremola: la scarica s'interrompe e riprende a scatti (sibilo e ronzio cadono e tornano), a ogni ripresa il contatto crepita, nei cali il reattore ronza ruvido. *Rifatto, approvato il 13 ottobre.* |
| `tarp_in` | 1,1 s | Ci si infila sotto il telone di tela cerata: la mano che afferra la tela, il telone tirato sopra la testa (fruscio pesante, aria spostata), le ginocchia sulle tavole e il corpo che scivola sul pagliolo, il telone che ricade con un tonfo morbido e si assesta, già ovattato. *Rifatto, approvato il 13 ottobre.* |
| `tarp_out` | 0,9 s | Si esce dal telone: la tela spinta su di colpo, buttata indietro con un colpo d'aria, che ricade dietro sul banco; torna l'aria aperta. *Rifatto, approvato il 13 ottobre.* |
| `heartbeat` | 1 s, **loop** | Il battito sentito da dentro: "lub" grave e pieno, "dub" più corto e un po' più alto, il sangue che pulsa nelle orecchie. Ora è un loop vero (60 al minuto; il gioco lo accelera col playbackRate). *Rifatto, approvato il 13 ottobre.* |
| `sonar_ping` | 2,2 s | Ping dell'ecoscandaglio: tono che cala appena con il tic del trasduttore, coda d'acqua densa che ondeggia, eco dal fondo più scura e più grave, sotto il crepitio dei gamberetti. **Stereo**. *Rifatto, approvato il 13 ottobre.* |
| `sonar_blip` | 0,15 s | Bip di un contatto: il cicalino piezoelettrico (onda quasi quadra, risonanza acuta). *Rifatto, approvato il 13 ottobre.* |
| `sonar_warn` | 0,9 s | **Nuovo.** L'avviso quando sale qualcosa di grosso: due bip più gravi e sporchi (il secondo più basso), ognuno con un colpo sordo sotto. Lo usa `Sfx.sonarWarn()`. *Approvato il 13 ottobre.* |
| `radio_on` / `radio_off` | 0,45 / 0,4 s | Il baracchino: lo scatto del pulsante e lo squelch che si apre ('kshh') finché la portante aggancia e il fruscio crolla; in chiusura la coda dello squelch ('kshhht') che si chiude secca e lo scatto. Tutto dal piccolo altoparlante. *Rifatti, approvati il 13 ottobre.* |
| `static_burst` | 1,5 s | Il segnale che salta (dopo il jumpscare): schiocco elettrico, neve televisiva a strappi, ronzio a 50 Hz di un televisore che perde il quadro, fischi che strisciano come le righe di un nastro rovinato, il tubo che si spegne. **Stereo**. *Rifatto, approvato il 13 ottobre.* |

## Voce radio (mono)

`voice_01` … `voice_24` (60–220 ms ciascuno): sillabe borbottate di un vecchio pescatore, voce roca e bassa (fondamentale ~95–120 Hz con jitter), vocali diverse (a, e, i, o, u con formanti realistiche) e consonanti accennate, già filtrate come una radio (passa-banda 300–3000 Hz, leggera saturazione). Il gioco le concatena a caso mentre scorrono i sottotitoli (stile "animalese" ma umano e malinconico). *Non ancora generati: oggi la radio usa la voce sintetica al volo di `src/engine/voice.ts` (profilo `RADIO_VOICE`).*

## Le creature (mono) — tutto approvato (Gulpy, Molly e Hatch il 13 ottobre)

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

**La conta di Hatch** (`src/engine/voice.ts`, profilo `CHILD`, stessa API di `speak()`): ogni sillaba è ora un'onda glottale (non più un dente di sega) con tre formanti che scivolano da una sillaba all'altra, soffio sulle vocali, vibrato irregolare; il profilo del bambino ha formanti più alte (×1,36), la coda che cala alla fine di ogni parola, la "gola sotto" (la stessa sillaba poco meno di un'ottava più giù, da un tratto vocale enorme), un tremolio d'acqua nel fiato e la distanza (passa-basso e un'eco corta e scura dello scafo e dell'acqua). *Approvata il 13 ottobre.*

### Robin — notte 2, ruba dal secchio (11 ottobre, approvati)
La voce è quella delle gallinelle vere, che gracidano col tamburo della vescica natatoria: raffiche di colpi bassi e sordi
(da 20 a 70 al secondo), un «grr-grr» da rana sott'acqua. Dentro, a tratti, una risatina soffocata dal naso, di bambino
che l'ha fatta franca. Cammina sui raggi duri delle pinne (tic secchi sul legno, sulla lamiera del secchio) e ha i
biglietti della sala giochi avvolti, fradici, sulle braccia. Sostituiscono i provvisori fatti coi file di scena.

| id | durata | descrizione |
|---|---|---|
| `robin_climb` | 1,75 s | Sale dal mare sul capodibanda: l'acqua che si apre e gli cola di dosso, la mano bagnata che sbatte sul bordo, il legno che cede appena, le zampette dure che ticchettano in fila, i biglietti che sfregano, un gracidio corto quando è su. |
| `robin_rattle_1`, `2` | 1,05 / 1,15 s | Fruga nel secchio: i raggi delle pinne che ticchettano sulla lamiera, i pesci bagnati che scivolano e sbattono contro le pareti, il secchio che si sposta sul pagliolo, un gracidio avido sotto. |
| `robin_steal` | 1,6 s | Un pesce strappato dal secchio: la presa bagnata, il pesce che si dibatte contro la lamiera, trascinato sopra il bordo (la pancia che striscia sul legno), il tonfo in mare; poi la risatina soffocata. |
| `robin_scared` | 1,75 s | Nella luce piena: un gracidio d'allarme velocissimo che sale, uno strillo strozzato dal naso, le zampette che raspano in fuga, il corpo che scivola giù per la fiancata, il tuffo. |
| `js_robin` | 1,4 s | Jumpscare (**stereo**): lo schiocco bagnato con cui molla il bordo, i biglietti che frustano l'aria, lo strillo di un bambino (tre voci appena scordate) ruvido e bagnato, con dentro il tamburo della gallinella a raffica furiosa. RMS ≈ −7,6 dBFS, bilanciato come quelli di Hatch e Molly (i bassi del tamburo non coprono lo strillo). |

### Archie — notte 3, spegne la luce (11 ottobre, approvati)
La sua voce è la trombetta da festa fusa nel bocchino: un'ancia di plastica che sbatte (il ronzio nasale da kazoo), il
tubo di carta a strisce che risuona, la carta che si arrotola e si srotola, la piuma in punta. Sostituiscono i provvisori
sintetizzati al volo; le durate seguono i tempi della notte 3 (`config.ts`).

| id | durata | descrizione |
|---|---|---|
| `archie_rise` | 2,8 s | Il mare che si apre accanto alla prua e il collo che sale dritto: l'acqua che si gonfia e si rompe, poi scorre giù per tutto il collo lunghissimo e gocciola dall'alto sul mare; la pelle che scivola mentre si piega in cima, la carta fradicia della trombetta, un soffio fra i denti. |
| `archie_inhale` | 4,85 s | Il risucchio (4,5 s nel gioco, poi soffia: il culmine sta alla fine): l'aria tirata al contrario nella trombetta, un soffio che sale; l'ancia che strilla strozzata e s'inceppa, sempre più acuta; la carta che si arrotola sempre più stretta; la gola che si gonfia come un pallone (la pelle che cigola, la sacca che rimbomba sempre più grave); la saliva fra i denti. `sfx.ts` lo ferma con una dissolvenza quando la lampara si spegne o quando soffia. |
| `archie_relight` | 2,5 s | Lo stesso risucchio quando riaccendi la lampara mentre aspetta: 2,2 s, più acuto e più rabbioso. |
| `archie_wait` | 1,7 s | La lampara si è spenta in tempo: la trombetta si sgonfia in un lamento che scende (l'ancia che perde fiato e s'inceppa), la carta che si riavvolge, la gola che si svuota in un sospiro, uno schiocco umido delle labbra sul bocchino. |
| `archie_blow` | 1,3 s | Il soffio a tutto fiato sulla lampara: la trombetta che si srotola di scatto, l'ancia che strepita forte e nasale (due voci appena scordate), la piuma che frulla, l'aria che si rovescia sul vetro. |
| `glass_break` | 1,7 s | Il vetro della lampara che esplode (suona dalla lampara 0,12 s dopo il soffio): lo schianto, la lampadina che scoppia, l'arco che sfrigola mentre il reattore si spegne con un colpo sordo, la pioggia di schegge sul pagliolo e qualcuna in mare. Categoria `sfx`. |
| `archie_dive` | 2,4 s | Si rituffa: la testa che si piega giù (la pelle che scivola, un soffio), il collo lunghissimo che rientra in mare tutto di seguito («shhhllup» lungo, l'acqua che gorgoglia), la testa che va sotto con un tonfo e le bolle che risalgono, le onde che arrivano allo scafo. |
| `js_archie` | 1,4 s | Jumpscare (**stereo**): la trombetta che si riavvolge di scatto e frusta l'aria, e il grido dentro il bocchino: lo strillo di un bambino che passa per l'ancia e ne esce ronzante e nasale come da un kazoo enorme, il soffio del serpente fra i denti, le zanne che scattano a vuoto. RMS ≈ −7,8 dBFS. |

### Lampy — notte 4, non va ferrata (11 ottobre, approvati)
Una neonata (formanti a ×1,55, più corte ancora di quelle di Molly) che sta sott'acqua: la sua risatina arriva ovattata e
piena di bolle. Il suo segnale è il campanellino a tempo perfetto: `lampy_bell` è un colpo solo, e il ritmo lo fa il
gioco (`sfx.lampyBell`, senza variazioni d'altezza né di volume: i tre colpi devono essere identici).

| id | durata | descrizione |
|---|---|---|
| `lampy_bell` | 0,9 s | Un colpo solo dei due campanellini d'ottone in punta alla canna (gli stessi delle abboccate vere): il battaglio colpisce una volta, netto, il secondo campanellino gli risponde appena, la molletta ticchetta. Il gioco lo suona tre volte a 0,62 s. |
| `lampy_giggle` | 1,3 s | La risatina da sotto l'acqua, dopo il secondo colpo: una neonata che ride a singhiozzi («ih-ih-ih»), ovattata, e a ogni sillaba le bolle che salgono a scoppiare in superficie. |
| `lampy_grab` | 0,5 s | Prende la lenza: il galleggiante tirato sotto di colpo, il filo che si tende. |
| `lampy_surface` | 1,4 s | Affiora sulla lenza: l'acqua che le scorre giù dalla cuffia e dal corpo ad arco, la ventosa che si riattacca al filo con un bacio umido, un soffio dalle due fessure del naso. |
| `lampy_let` | 1,3 s | Molla la lenza: lo schiocco pieno della ventosa della bocca, poi quello della coda, e giù di schiena, le bolle. |
| `lampy_climb` | 1,2 s | Agganciata, risale la lenza a baci risucchiati sempre più svelti, il filo e la canna che gemono, una risatina che si stringe in un gorgoglio. |
| `js_lampy` | 1,4 s | Jumpscare (**stereo**): il risucchio enorme della ventosa che si spalanca e si attacca, gli anelli di denti che girano come una macina (un ticchettio fitto che va e viene), lo strillo di una neonata (tre voci) con sotto la stessa voce da una gola più grande. RMS ≈ −7,3 dBFS. |

### Fangy — notte 5, stare zitti (11 ottobre, approvati)
Un mastino degli abissi, cieco, con una gola enorme (formanti a ×0,62): non parla, respira. Quasi tutto il suo suono
è acqua e fiato, vicinissimo e dietro le spalle (sta accanto alla barca, a destra dietro il pescatore). Mentre ascolta
il gioco tiene acceso il suo respiro in loop (`fangy_listen`, il volume segue quanto è su); a ogni rumore che sente
suona uno dei tre scatti (`fangy_snap`, varianti `_2` e `_3`, scelte a caso).

| id | durata | descrizione |
|---|---|---|
| `fangy_approach` | 3,6 s | Le lucine che arrivano sott'acqua dal largo: un pulsare grave e lento (il corpo grande che spinge l'acqua) che si avvicina e si fa più chiaro, il ronzio sottile e freddo delle lucine che respirano, le bolle che salgono dal fondo. Tutto ovattato. |
| `fangy_rise` | 2,4 s | Sale accanto alla barca, dietro di te: l'acqua che si apre e gli cola di dosso a lungo, le nocche che toccano la fiancata (un colpo sordo, vicinissimo), le zanne che gocciolano, un fiato lungo dentro il muso: annusa l'aria con le fossette. |
| `fangy_listen` | 9 s, loop | Mentre ascolta: tre respiri lenti e bagnati fra le zanne (dentro, fuori, poi una pausa trattenuta per sentire meglio), l'acqua che gli sciaborda contro il petto, le gocce che cadono dalle zanne, di rado le zanne che si toccano. Basso (RMS ≈ −27 dBFS). |
| `fangy_snap` ×3 | 0,65 s | Ti ha sentito: la testa che scatta sul collo (lo schiocco della cartilagine, il collo che si torce nell'acqua), le zanne che sbattono, un'annusata secca e forte. |
| `fangy_leave` | 2,2 s | Torna giù: un fiato lungo che esce gorgogliando mentre il muso va sotto, l'acqua che si richiude sopra la testa, le bolle, lo sciabordio contro la fiancata. |
| `js_fangy` | 1,6 s | Jumpscare (**stereo**): l'acqua che esplode sulla fiancata, la mascella che schiocca e le zanne che sbattono, e il ruggito di un mastino enorme in una gola d'acqua con sopra, alta e rotta, la voce di un bambino che strilla (tre voci). RMS ≈ −7,3 dBFS. |

### La Madre — notte 6 (11 ottobre, approvati)
Mama Marina, la balena-mamma della mascotte del parco diventata mostro: enorme, molto più grande della barca. Non parla:
al massimo canticchia la sua ninna nanna senza parole. La voce è una gola più grande di tutte (formanti a ×0,38, come il
lamento di `mus_madre`) con un battito lento e ruvido (le pulsazioni dei versi delle balene) e sotto una seconda gola a
poco meno di un'ottava, mai esatta (suona sbagliata, come le voci doppie dei figli). Sott'acqua arriva scura, con le eco
della superficie e del fondo e una coda lunghissima. Modulo `tools/audio/sounds/madre.py`. I richiami lontani sono
**mono** (il gioco li mette dove sta l'ombra sul sonar); tutto il resto la circonda ed è **stereo**.

| id | durata | descrizione |
|---|---|---|
| `madre_far_1`…`3` | 10,5 / 11,5 / 12 s | L'ombra lontana: un richiamo profondo e distorto che arriva dal fondo, da lontano (niente acuti, le eco del fondo, il livello che ondeggia con l'acqua in mezzo). 1 un lamento lungo che sale, si apre e ricade, e un canto più acuto che gli risponde; 2 due grugniti pulsati che scendono e un lamento basso che crolla; 3 l'inizio della ninna nanna (Mi–Do–La–Si) canticchiato lentissimo e sempre più calante. Mono, RMS ≈ −24 dBFS. |
| `madre_approach` | 12 s | Si avvicina: in lontananza i figli fanno i loro versi (un gorgoglio, una risatina, un mugolio) e d'un tratto si zittiscono, l'ultimo a metà, e vanno giù tutti insieme (corpi che scivolano in acqua attorno alla barca); a 3,5 s il mare si calma di colpo e resta un silenzio che pesa, con sotto una pressione gravissima che cresce; il richiamo della Madre arriva da lontano e si fa vicinissimo, sotto la barca; la lampara trema due volte (6 e 9 s: la luce che cala e torna a scatti, il reattore che ronza ruvido; non si spegne). |
| `madre_lullaby` | 40 s, **loop** | La ninna nanna della Madre canticchiata dal fondo, a bocca chiusa, da una voce di balena enorme: la prima frase della melodia del carillon (Mi–Do \| La–Si \| Do Re Mi \| Si…, poi Mi–Do \| La–Sol♯ \| La Si Do \| La…), tre ottave sotto, lentissima (43 al minuto contro i 67,5 del carillon, e rallenta ancora). Scivola da una nota all'altra, entra un po' sotto ogni nota e la fa calare sulla coda; la seconda frase è più bassa della prima e l'ultima nota non arriva: crolla di quasi due semitoni in un lamento. Sopra, la stessa voce un'ottava più su e, lontanissimo, il canto delle balene che segue la melodia. Poi la pausa con le bolle grosse che salgono, e ricomincia. RMS ≈ −22 dBFS. |
| `madre_pass_1`, `_2`, `_3` | 12 / 16 / 20 s | La passata sotto la barca (le tre della notte, alle 2, alle 4 e alle 5:30, sempre più lunghe): l'acqua che il corpo enorme sposta e spinge contro lo scafo, la pelle che scorre sotto la chiglia (un attrito lento e sordo che fa vibrare il fasciame, le incrostazioni che grattano il legno), la barca che si solleva piano sul suo dorso e scricchiola tutta (dal fasciame grave alle tavole del pagliolo), il manico del secchio e la campanella a poppa che si muovono appena, l'acqua che scivola giù dai fianchi; attraverso il legno, il suo cuore lentissimo (13 battiti al minuto) e, appena, un brontolio dentro di lei. Passa da sinistra a destra. Sale piano e piano se ne va: niente è mai forte di colpo (picco ≈ −6 dBFS, RMS ≈ −21). |
| `js_madre` | 2 s | Jumpscare (**stereo**): ti prende dal basso. Lo scafo che si spacca sotto i piedi e la barca sollevata di colpo (un colpo enorme e sordo, il legno che si schianta), l'acqua che esplode, e la bocca: il ruggito di una balena enorme (due gole, la voce rotta) e dentro, alte e bagnate, le voci dei bambini che ha preso (cinque, appena scordate) che urlano tutte insieme. RMS ≈ −7,8 dBFS. |
| `madre_dawn` | 24 s | Il finale all'alba (finale A), da suonare sopra l'alba: la Madre sale accanto alla barca, a sinistra (il mare che si gonfia e si rompe, l'acqua che le scroscia giù dal corpo, la barca che dondola e geme), lo sbuffo dallo sfiatatoio con la pioggia dello spruzzo (4,6 s), un mormorio senza parole; attorno a lei affiorano i sette figli uno dopo l'altro (7–10 s); la sua pinna bagnata sul capodibanda e la barca che s'inclina, il secchio preso (10,6–13 s: i pesci che scivolano nella lamiera, il manico che sbatte, l'acqua che ne cola); tornano giù tutti, i figli e poi lei, enorme e lenta (13–17 s); dal fondo canticchia la fine della ninna nanna, che **per la prima volta si risolve** (La Si Do♯ \| La, in maggiore: proposta); il mare si calma, le ultime onde arrivano allo scafo e a 21 s un primo gabbiano. |

**Come li dovrebbe usare il gioco** (proposta, il codice della notte 6 non c'è ancora): `madre_far_*` ogni tanto durante
tutta la notte, spazializzati dove sta l'ombra sul sonar, mai lo stesso due volte di fila. A ogni passata: `madre_approach`;
a 3,5 s il gioco abbassa `amb_sea` (in un secondo: il mare del file si ferma lì) e zittisce i mostri; verso 8 s parte
`madre_lullaby` (con una dissolvenza di 3 s) e verso 13 s la passata (`madre_pass_1`, `_2` o `_3`). Quando la passata
finisce, la ninna nanna si spegne in 4–5 s e il mare torna. Se ti muovi: `js_madre`. All'alba del finale A
`madre_dawn`, con `amb_dawn` che entra piano dai 20 s.

**Ascolti di prova** (mp3 in `docs/concept/suoni/`, montati con il mare e la lampara del gioco):
`madre_passa_sotto.mp3` (la scena intera: il mare, l'avvicinamento, la ninna nanna, la seconda passata, il ritorno del
mare), `madre_lontana.mp3` (i tre richiami lontani sul mare), `madre_ninna_nanna.mp3` (la ninna nanna da sola, un giro e
l'inizio del successivo), `madre_jumpscare.mp3` (due secondi di passata e il jumpscare), `madre_finale_alba.mp3` (il
finale, con l'alba del gioco che entra alla fine).

### I finali della notte 6 (11 ottobre, approvati)
I suoni delle cinematiche dei finali (vedi «I finali» in `NOTTI_E_MOSTRI.md`): ognuno copre tutta la cinematica, da
17 a 18 s, **stereo**, coi livelli degli altri suoni lunghi (RMS attivo ≈ −19/−20 dBFS). Nessuno parla: la Madre al
massimo canticchia la ninna nanna senza parole. Modulo `tools/audio/sounds/finali.py` (usa la voce, l'acqua e la ninna
nanna di `madre.py`). `madre_dawn` (24 s) resta per ora, ma per la cinematica c'è la versione corta.

| id | durata | descrizione |
|---|---|---|
| `madre_dawn_breve` | 17 s | Il finale A «La quota», ristretto: lei sale a sinistra col mare che si gonfia e l'acqua che le scroscia di dosso (0–3 s); lo sbuffo dallo sfiatatoio con la pioggia dello spruzzo (3 s); i sette figli che affiorano attorno (4–7 s); la pinna sul capodibanda, la barca che s'inclina e geme, il secchio preso (i pesci che scivolano nella lamiera, il manico che sbatte, l'acqua che cola; 7–10 s); giù tutti, i figli e poi lei, con le bolle grosse (10–13 s); dal fondo la fine della ninna nanna che si risolve (La Si Do♯ \| La; 12–16 s); il mare calmo e il primo gabbiano (15–17 s). Il suono dell'alba (`amb_dawn`) può entrare dai 13 s. |
| `finale_nessuno` | 18 s | Il finale «Nessuno»: lei sale accanto alla barca ma si ferma, un fiato lungo e basso (0–3 s); i figli affiorano uno alla volta attorno alla barca, sette piccoli tonfi distanziati (3–8 s), poi nessuno si muove più: solo gocce; la lampara che muore (il ronzio che cala e sfarfalla) e lo scatto del relè (8–10 s), una pressione bassa che cresce nel buio; la ninna nanna canticchiata senza parole (Mi–Do \| La–Si, lentissima), vicinissima, come dentro l'acqua (10–15 s); a 15 s **taglio netto** sull'edicola del parco: il vento, il cartello di lamiera che cigola sulla catenella, e alla fine (16,7 s) lo scatto di una Polaroid con il motorino che spinge fuori la foto. Dopo il taglio non c'è più il mare. |
| `finale_tuoi` | 18 s | Il finale «I tuoi»: lei sale e chiama con una frase della ninna nanna, fuori dall'acqua (0–3 s); silenzio, nessuno la segue, e lei richiama più insistente (Mi–Do, Mi–Do, più forte e rotta; 4–6 s); il suo lamento che scende mentre torna giù da sola, prima nell'aria e poi sott'acqua, con le bolle (6–10 s); l'alba: i remi del gozzo che cigolano a ritmo negli scalmi, le pale che tirano l'acqua, e dietro, piccoli tonfi che seguono la barca, un gabbiano (10–14 s); il porto: un gabbiano più vicino, le cime che scricchiolano, la barca che tocca il molo (14,6 s), e i passetti bagnati e scalzi di sette bambini diversi (passo, peso e asse diversi) che scendono sul molo e si allontanano verso il paese (15–18 s). |

**Ascolti di prova** (mp3 in `docs/concept/suoni/`): `finale_A_breve.mp3` (con l'alba del gioco che entra alla fine),
`finale_nessuno.mp3`, `finale_tuoi.mp3`.

## Immersioni (11 ottobre) — tutto approvato

Proposta per le immersioni all'alba (`docs/IMMERSIONI.md`), tutta **approvata** (l'11 ottobre sera; `dive_found`,
aggiunto dopo, il 13 ottobre): modulo `sounds/immersioni.py`. Sott'acqua l'orecchio sente ovattato: gli acuti calano
ma non spariscono (i versi tengono un filo di bollicine e di schiocchi, per l'HRTF). Le bolle sono profonde: quasi
nessuna salita di tono, niente «bloop» da cartone. Il mare sopra e il letto della grotta stanno sotto i 700 Hz: niente
fruscio a banda larga. I mostri dormono e **non parlano**: solo fiato, bolle e le loro cose (la paperella, i
braccioli, l'esca, il tamburo, la trombetta, la ventosa, le conchiglie). Ascolti di prova in `docs/concept/suoni/`:
`immersione_gulpy.mp3` (scendi, la grotta grande con la Madre in fondo, nuoti fino a Gulpy che russa, gli lasci il
pesce, si gira nel sonno, torni, l'avviso dell'aria, risali all'alba), `immersione_sette_tane.mp3` (le sette tane una
dopo l'altra, 14 s ciascuna, con il mostro che si muove a metà), `immersione_erogatore.mp3` (il respiro calmo,
accelerato col playbackRate, l'avviso, il respiro affannato, l'aria che finisce, la risalita). I livelli nelle
anteprime sono indicativi: il bilanciamento vero lo fa il motore.

**L'ambiente e l'erogatore** (stereo)

| id | durata | descrizione |
|---|---|---|
| `amb_dive` | 48 s, loop | La grotta sott'acqua: il silenzio pesante dell'acqua (un letto grave e scurissimo), il mare lontano sopra che respira con l'onda lunga (6 cicli da 8 s), la grotta che rimbomba piano quando la risacca entra dall'imboccatura (risonanze a 38 e 57 Hz, tre colpi sordi), sassolini che rotolano giù per la roccia, il crepitio rado dei gamberetti, due volte la roccia che geme lontano, una volta un rottame di scivolo che la corrente fa toccare sulla pietra. Categoria `amb`. |
| `dive_breath` | 5,2 s, loop | Il respiro calmo nell'erogatore (11–12 al minuto): dentro lo scatto della leva e il sibilo della valvola a domanda, fuori il borbottio della membrana di scarico e la colonna di bolle che sale accanto alle orecchie e si allontana. Il gioco lo accelera col `playbackRate` quando l'aria cala (fino a ~1,3 regge). |
| `dive_breath_fast` | 3 s, loop | Il respiro affannato ad aria bassa (20 al minuto): l'inspiro corto che tira duro (il sibilo stretto e balbettante), l'espiro di colpo con un'esplosione di bolle. Da incrociare con `dive_breath` dopo l'avviso. |

**Le dissolvenze** (stereo, categoria `sfx`)

| id | durata | descrizione |
|---|---|---|
| `dive_down` | 8 s | La discesa: ci si lascia cadere all'indietro dalla barca (il tonfo già ovattato), la nuvola di bolle che ti avvolge, il silenzio pesante che arriva, il primo respiro nell'erogatore (a 2,3 s), le orecchie che si compensano (due schiocchi sordi), il mare sopra sempre più lontano, la cima dell'ancora che sfrega sulla mano. |
| `dive_swim_1`, `_2` | 2,6 s | La nuotata fra un posto e l'altro: tre colpi di pinne lenti (l'acqua spinta via, la pala che flette), il corpo che fende l'acqua, un espiro con le bolle che scivolano lungo le orecchie (prima o dopo, nelle due varianti). |
| `dive_bubbles` | 1,4 s | Per i tagli secchi: un espiro forte e la nuvola di bolle che passa davanti alla maschera da sinistra a destra. |
| `dive_air_low` | 2,4 s | L'avviso dell'aria: due colpetti del dito sul vetro del manometro, l'ago che trema e si assesta (due tic), poi un respiro che tira duro (la valvola sibila stretta e balbetta, la membrana cigola). Non è un bip: il manometro è un ago come quello del voltmetro. |
| `dive_air_out` | 2,8 s | L'aria che finisce: un ultimo inspiro che dà poco e poi niente, la membrana che si incolla con uno schiocco di gomma (due tentativi a vuoto), lo scarico che borbotta l'ultima aria. Poi `dive_up`. |
| `dive_up` | 7,6 s | La risalita: due soffi del gav, i colpi di pinne verso la luce, l'espiro lungo con le bolle che salgono con te, il mare sopra che si avvicina e si schiarisce; a 5,2 s la testa rompe il pelo dell'acqua: il mondo che si riapre, le gocce, il boccaglio sputato, un respiro grande nell'aria dell'alba, le onde contro la barca. |

**Le tane** (mono, si spazializzano; i respiri sono loop da suonare in continuo, i movimenti ogni tanto sopra)

| id | durata | descrizione |
|---|---|---|
| `dive_found` | 1,8 s | La cosa trovata in una tana (un disegno, una foto, il cartoncino), che va nel Diario: non è un premio. La carta fradicia che si stacca dalla sabbia e si piega fra le dita, l'acqua spostata dalla mano; sotto, un gonfiore grave e sordo con un battito dentro, come se la stanza trattenesse il fiato; lontano, la roccia che geme un momento. Stereo, categoria `sfx`. |
| `offer_fish` | 1,9 s | Il pesce lasciato accanto al mostro: la mano che lo lascia andare, il tonfo morbido e grave nella sabbia, lo sbuffo di granelli che si alza e ricade, la coda molle che ricade una volta, una bollicina. Categoria `sfx`. |
| `sleep_gulpy` | 13 s, loop | Russa con la mascella che pende aperta: due russate enormi e bagnate (il fry della gola gigante, il palato molle che sbatte), e fuori dalla bocca spalancata bolle grosse e lente una dopo l'altra (75–190 Hz), le labbra molli che sbattono; una volta la paperella del collo che cigola quando il petto si gonfia. |
| `sleep_molly` | 11,4 s, loop | Tre respiri piccoli di bambina dal naso, due o tre bollicine a ogni espiro; al secondo un mugolio nel sonno con sotto, appena, l'altra gola; i braccioli che stridono una volta. |
| `sleep_hatch` | 12 s, loop | Due respiri lunghi dalle narici grandi (un'aspirata lenta e bagnata), le branchie che sbattono piano sotto la mascella con qualche bolla; l'esca che si accende e si spegne piano due volte (lo scatto del contatto, la bobina che fischia fioca), i denti di vetro che si toccano una volta, il legno dell'armadio che geme. |
| `sleep_robin` | 10,2 s, loop | Respira col tamburo della vescica natatoria, piano e lento (fusa d'acqua, un «rrr» sordo a ogni espiro), le branchie che soffiano bollicine; due volte le zampette che si muovono nel sonno e ticchettano sul bottino (gomma, latta) con i biglietti fradici; una volta, dal naso, l'ombra della risatina. |
| `sleep_archie` | 12,6 s, loop | Due respiri: dentro un soffio fra i denti e la carta della trombetta che si riavvolge; fuori la trombetta che si srotola un poco (un filo di fiato nell'ancia, un ronzio nasale debole che s'inceppa e cala), la carta fradicia che si stende, le bolle dalla punta; il corpo che stringe e scivola sul tavolo, il tavolo che scricchiola. |
| `sleep_lampy` | 9 s, loop | Tre respiri piccoli e veloci da neonata; a ogni respiro la ventosa che si riassesta sul soffitto (un risucchio umido) e una fila di sette bollicine dalle fessure delle branchie; la giostrina della culla che la corrente fa ticchettare piano. |
| `sleep_fangy` | 14 s, loop | Due respiri lentissimi del mastino (dentro un fiato lungo e grave dal muso, fuori un soffio fra le zanne che gorgoglia e lascia salire le bolle); l'acqua mossa dal respiro fa toccare le conchiglie appese, che tintinnano piano; le lucine del ventre quasi spente, un ronzio freddo appena percettibile che respira. |
| `stir_gulpy` | 3 s | Si gira sul materasso di salvagenti: la gomma che cigola sotto il peso, la mascella molle che sbatte (uno schiocco d'osso sordo), uno sbuffo russato che s'interrompe, una bollona. |
| `stir_molly` | 3 s | Stringe i braccioli: la plastica che stride, il corpo che si rannicchia, un piagnucolio piccolo a bocca chiusa (con l'altra gola) che si spegne in un sospiro con le bollicine. |
| `stir_hatch` | 3 s | Si muove nell'armadio: le ante che sbattono piano, il legno che geme, l'esca che si accende di colpo e il chip che prova una nota sola, calante; un'annusata lunga. |
| `stir_robin` | 2,8 s | Si sistema sul bottino: il mucchio che frana un poco (scarpe di gomma, un giocattolo di latta, i biglietti), un gracidio corto e assonnato. |
| `stir_archie` | 3 s | Stringe le spire attorno al tavolo: la pelle che scivola, il tavolo che scricchiola, un palloncino che strofina, la trombetta che si srotola di scatto con un «prrt» sfiatato e le bolle. |
| `stir_lampy` | 2,8 s | La ventosa che molla un attimo dal soffitto (lo schiocco), il corpo che ondeggia sopra la culla, il bacio risucchiato con cui si riattacca, un versetto da neonata ovattato, la giostrina che gira. |
| `stir_fangy` | 3,2 s | Alza il testone come se avesse sentito qualcosa: il collo che si torce nell'acqua, le conchiglie che tintinnano tutte insieme, un'annusata secca, le zanne che si toccano, un fiato lungo che gorgoglia e la testa che si riposa. |
| `madre_breath` | 24 s, loop | Dal fondo della grotta grande (proposta di `IMMERSIONI.md`): qualcosa di gigantesco respira, un respiro solo in 24 s. Dentro, l'acqua della grotta risucchiata verso il buio (una corrente grave, i sassolini e la sabbia che scorrono verso l'apertura); fuori, la spinta lenta che torna indietro, bolle enormi e gravissime dal buio, e quasi sotto la soglia il lamento della voce più grande che ci sia. |

Note per il motore: nei loop delle tane il respiro parte entro il primo mezzo secondo (in `sleep_archie` dopo 1,3 s: il
loop comincia nella pausa); `rms` attivi: respiri −26…−23 dBFS, movimenti −21 dBFS, ambiente −28 dBFS.

### L'animatore (il «Foxy») — notti 2-5, da tenere d'occhio col binocolo (12 ottobre, approvati)
L'animatore di Splashland annegato dentro il costume di Mama Marina (variante B «Fradicio»; il nome, scelto
dall'utente, è Soggy; gli id restano `foxy_*`). Non parla: solo fiato, gorgoglio e il costume. Il suo suono è
**il peluche fradicio**: la gommapiuma marcia che si strizza a ogni movimento e butta fuori acqua a fiotti, i tonfi
molli, e un segno acuto tutto suo, **l'occhio di plastica da cartone** (una cupola vuota con la pupilla libera dentro:
«toc» e sbatacchio). La voce è di un uomo (formanti a ×0,94) coi polmoni pieni d'acqua. Modulo
`tools/audio/sounds/foxy.py`.

| id | durata | descrizione |
|---|---|---|
| `foxy_near` | 2,2 s | Si sporge verso di te mentre non lo guardi (evento `lean`): laggiù il costume si piega in avanti e l'acqua ne esce tutta insieme (uno scroscio lungo che cade sul mare, l'unica cosa che da lassù arriva sull'acqua ferma), la gommapiuma che si strizza, l'occhio che batte due volte. Lontano (pochi acuti, la coda dell'acqua aperta) e basso (RMS ≈ −24 dBFS); il gioco lo suona dal suo posto a 9 m. |
| `foxy_leave` | 3,2 s | Lascia il posto (evento `leave`): un tonfo pesante laggiù (il costume gonfio d'acqua che si butta), poi la corsa verso la barca, mezzo a nuoto e mezzo coi piedi sul fondo: bracciate spugnose che accelerano (da una ogni 0,46 s a una ogni 0,22 s), sempre più vicine e chiare (la coda lunga sull'acqua lascia il posto al suono asciutto), l'acqua spinta via che ribolle, i fiati gorgoglianti, l'occhio di plastica. Gli ultimi 0,35 s sono lo slancio fuori dall'acqua con un inspiro a bocca piena: il jumpscare parte sulla fine. Il gioco lo suona dal suo posto a 6 m e ne adatta la velocità a `run` (3,5 s nella notte 2 → ×0,91; 3 s nelle notti 4-5 → ×1,07). |
| `js_foxy` | 2 s | Jumpscare (**stereo**): lo slancio e il costume zuppo che sbatte sul capodibanda (la barca sobbalza e geme), il peluche che ti si schiaccia addosso strizzando acqua (e stringe ancora a metà), l'urlo di un uomo annegato dentro la testa del costume (tre voci appena scordate, soffocato dalla gommapiuma che si mangia gli acuti e rimbomba, un filo che esce dalla bocca; gorgogliante, affoga in un rantolo), l'occhio di plastica che sbatte dal lato dove la testa è crollata, e, schiacciata dall'abbraccio, la scatoletta sonora nel pancione che suonava la sigla: l'ultimo «ta-daaa» dello spettacolo (Sol, poi l'accordo di Do) da un altoparlantino pieno d'acqua, che gracchia e crolla storto mentre la pila muore. RMS ≈ −7,2 dBFS. |

Ascolti di prova: `docs/concept/suoni/foxy_near.mp3`, `foxy_leave.mp3`, `js_foxy.mp3` e `foxy_sequenza.mp3` (il mare,
si sporge, lascia il posto, corre, jumpscare; livelli approssimati come nel gioco, corsa da 3,2 s come nella notte 3).

## Più paura (12 ottobre) — tutto approvato il 13 ottobre

`tools/audio/sounds/paura.py`. Il cuore e il respiro sono della categoria `body`: suonano dentro la testa, senza
posizione e senza l'ovattato del telone (`src/app/paura.ts` li ripete col suo ritmo). I colpi dei falsi allarmi sono
quelli di Molly (`molly_knock_*`): devono ingannare.

| id | durata | descrizione |
|---|---|---|
| `cuore_1..3` | 0,62 s | Un battito (lub-dub): un'onda bassa che cala subito di tono, un'armonica e il tonfo sordo dei tessuti, un filo di saturazione perché si senta anche dalle casse di un portatile. Dal 1 al 3 sempre più agitato: i due colpi più vicini e il secondo più forte. |
| `fiato_dentro_1..3`, `fiato_fuori_1..3` | 0,5-1,2 s | Inspiro ed espiro a parte (il gioco li alterna): dal calmo al corto, col tremito della paura (il fiato che trema attorno ai 9 Hz); nell'espiro più agitato un filo di voce, un gemito soffocato. |
| `tensione_bassa` | 24 s, loop | Il fondo basso: due note gravi a un soffio di distanza che battono lente, un grappolo scuro (la, si bemolle, mi bemolle) che respira, e lontano il fasciame della barca che geme. Ogni oscillatore fa un numero intero di giri nel loop: niente giunture. |
| `tensione_alta` | 16 s, loop | Il fondo alto, per quando è vicino: archi stonati in alto in un grappolo che non risolve, col vibrato lento e il tremolo, il fruscio del crine, e un metallo strofinato che fischia appena. |
| `vivo_scatto_1..3` | 0,45 s | Lo scatto della testa quando la guardi: la cartilagine che schiocca, la carne bagnata che segue, un fiato corto dal naso (tre grandezze). |
| `goccia_1..4` | 0,32 s | Una goccia che cade da chi è uscito dall'acqua: il «plic» di una bollicina che risuona e sale di tono, a volte una seconda più piccola. |

## Musica e stinger (stereo) — tutto approvato (gli stinger il 13 ottobre)

| id | durata | descrizione |
|---|---|---|
| `mus_title` | 64 s, loop | **Ninna nanna della Madre** al carillon (approvata; suona dall'avvertenza all'avvio fino al menu). La minore, 3/4, 67,5 BPM: 24 battute = 64 s esatti, forma A (8) – B (8) – A' (8). Tema A: Mi–Do | La–Si | Do Re Mi | Si…, poi Mi–Do | La–Sol♯ | La Si Do | La… (accordi La m, Fa, La m, Mi, La m, Mi, Re m, La m). Frase B più alta (La5–Fa5 | Mi–Do | Re–Si | Mi…) con le note sbagliate: un Re♯ (tritono, su un Si7) e un Si♭ che stride contro il Sol♯ (Mi–Si♭–Sol♯ → La). Nell'A' all'ultima battuta la tonica non arriva: la lamella è rotta e si sente solo il perno che la sfiora, mentre dal fondo, lontanissimo, sale per un attimo il lamento della Madre; poi il loop riparte senza essersi mai risolto. Carillon: lamelle d'acciaio a sbalzo (modi 1 : 6,27 : 17,5, il secondo forte nell'attacco), due lamelle gemelle per nota che battono piano, lo scatto del perno, il cilindro un po' impreciso (±4 ms), il valzer d'accompagnamento (basso sul primo tempo, due note dell'accordo sugli altri), la cassetta di legno, il ventolino del regolatore che frulla. Due lamelle stonate davvero (Do5 −27 centesimi, Fa5 +21), le altre entro ±9. Nastro vecchio: wow lento (±0,45%) e flutter, acuti consumati, un velo di soffio. Sotto, un pad sott'acqua molto basso (l'accordo di ogni battuta due ottave sotto, filtro che respira in 8 s), 17 dB sotto il carillon. |
| `mus_night_start` | 4 s | Inizio notte: un colpo basso e cupo con un rintocco grave di boa sotto, poi il carillon accenna l'inizio della ninna nanna (Mi–Do–La–Si), rallenta e si spegne nel riverbero, una lamella sempre più calante. |
| `mus_6am` | 7 s | Le sei: un accordo di La maggiore che si apre piano (archi morbidi, il filtro che sale), la ninna nanna finalmente in maggiore al carillon che sale fino alla tonica, celesta e campanelle, un respiro di sollievo. |
| `mus_gameover` | 8 s | Il carillon che si scarica: la ninna nanna rallenta, ogni lamella più calante (fino a quasi un semitono), l'ultima nota pizzicata appena; la molla si ferma con un tonfo del meccanismo. Sotto, un bordone grave che stride (La e Si♭) e cresce. |
| `mus_madre` | 10 s | La Madre si sveglia (quota mancata alle 6): un colpo enorme sott'acqua (una coda gigantesca che sposta l'acqua), poi un lamento lentissimo da balena abissale (la voce più grande che ci sia, formanti a ×0,4, con un canto più acuto che la accompagna) e dentro un coro grave in La minore (La1, Mi2, La2, Do3, Mi3; tre cantori scordati per voce) che sale e si ritira; bolle enormi che salgono dal fondo; tutto lontano, sotto l'acqua. |

## Interfaccia (stereo, brevi e discreti) — tutto approvato il 13 ottobre

Legno e ottone, come gli oggetti della barca.

| id | durata | descrizione |
|---|---|---|
| `ui_hover` | 40 ms | Un tic di legno appena accennato. |
| `ui_click` | 90 ms | Un nottolino di legno con il fermo d'ottone. |
| `ui_back` | 110 ms | Lo stesso gesto al contrario: lo scatto d'ottone e due colpetti di legno che scendono. |
| `ui_start` | 1,5 s | Un rintocco della campanella di bordo e il mare che risponde con un'onda lunga. |
| `ui_page` | 0,55 s | **Nuovo.** Si gira una pagina del Catalogo: la carta spessa che si stacca dalla pila, l'aria che la pagina sposta, qualche crepitio della carta vecchia, la pagina che si posa. *Approvato il 13 ottobre.* |

## Come li usa il gioco

`src/app/sfx.ts` (classe `Sfx`): `gurgle(pos, gain)` (fiato o gorgoglio di Gulpy, ogni tanto la gomma; con `gain ≥ 1,3`, il momento in cui pretende, prima si sgancia la mascella), `chew(pos)` (`gulpy_eat`), `knock(pos)`, `giggle(pos)`, `whine(pos)`, `tantrum(pos)` (Molly), `step(pos)`, `sniff(pos)` (Hatch), `sonarWarn()` (`sonar_warn`), `scream(gain, pitch)` (compatibilità: sceglie il jumpscare dall'intonazione), più i nuovi `jumpscare(who)`, `emerge(who, pos)`, `jaw(pos)`, `grab(pos)`, `peek(pos)`, `board(pos)`, `rock(amount)` (loop `molly_rock`, da chiamare a ogni fotogramma con la forza del dondolio), `toy(amount, pos)` (loop `hatch_toy`) e `stopLoops()`; per l'animatore `foxyNear(pos)` e `foxyLeave(pos, run)` (la corsa, troncata dal jumpscare; il jumpscare è `jumpscare('foxy')` → `js_foxy`). Musica, stinger e interfaccia si suonano con `AudioEngine.play(id)`; vanno sul bus `music` o `ui` in base alla categoria.
