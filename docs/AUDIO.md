# SPLASHLAND IS CLOSED! — Specifica audio

Tutto l'audio è **sintetizzato da script** in `tools/audio/` (Python + numpy/scipy, nessun campione esterno) e scritto in `public/assets/audio/<id>.ogg` (Vorbis, 48 kHz, qualità ~6). Il manifest `public/assets/audio/manifest.json` elenca per ogni id: `file`, `duration` (s), `loop` (bool), `channels`, `gain` consigliato (lineare, 0..1) e `category` (`amb`, `sfx`, `mon`, `mus`, `ui`, `voice`).

Rigenerazione: `tools/.venv/bin/python tools/audio/generate.py` (deterministico: seed fissi).

## Regole tecniche

- **Mono** per tutto ciò che viene spazializzato nel mondo (mostri, campanellino, mulinello, secchio, scafo). **Stereo** per ambienti, musica, UI e stinger.
- Loop **senza cuciture**: incrocio (crossfade) testa/coda e lunghezza esatta in campioni; niente click al punto di loop.
- Picco ≤ −1 dBFS; nessun clipping digitale. Livelli indicativi (RMS): ambienti −30…−24 dBFS, effetti −20…−14, jumpscare −8…−6 (forti ma non saturati).
- Code di riverbero incluse nel file (non c'è riverbero in tempo reale), salvo diversa indicazione.
- Niente silenzio inutile in testa: l'attacco parte entro 5 ms (tranne dove indicato).

## Ambienti (loop, stereo)

| id | durata | descrizione |
|---|---|---|
| `amb_sea` | 32 s | Sciabordio dell'acqua contro uno scafo di legno di notte, mare calmo: colpetti morbidi e irregolari, gorgoglii, qualche piccolo schizzo. Bassi presenti ma non rimbombanti. |
| `amb_wind` | 30 s | Vento notturno debole sul mare aperto, raffiche lente, quasi impercettibile. |
| `amb_lamp` | 8 s | Sibilo di una lampada a pressione (petromax) + leggerissimo ronzio elettrico a 50 Hz con armoniche. |
| `amb_drone` | 24 s | Bordone sub-basso inquietante (30–60 Hz) con battimenti lenti e un velo di "canto di balena" filtrato in lontananza. Usato quando la tensione sale. |
| `amb_tarp` | 16 s | Sotto il telone: mare ovattato (passa-basso ~600 Hz), tela che si muove appena, respiro trattenuto molto basso. |
| `amb_dawn` | 24 s | Alba: onde calme, gabbiani lontani, una brezza. |
| `radio_static` | 6 s | Fruscio radio VHF con lievi crepitii. |

## Mondo e orologio (mono, tranne dove indicato)

| id | durata | descrizione |
|---|---|---|
| `bell_toll` | 7 s | Un rintocco della campana di un campanile lontano (bronzo, parziali inarmoniche: hum, prime, tierce minore, quinta, nominale), coda lunga, filtrato dalla distanza. **Stereo**. |
| `bell_dawn` | 9 s | Scampanio festoso di più campane (alba delle 6). **Stereo**. |
| `foghorn` | 6 s | Sirena da nebbia lontanissima, due toni, riverbero di baia. **Stereo**. |
| `creak_1`…`creak_4` | 0,5–1,5 s | Scricchiolii del legno della barca (variati). |
| `splash_s1`…`splash_s3` | 0,4–0,8 s | Piccoli schizzi d'acqua. |
| `splash_big` | 1,5 s | Grosso tonfo in acqua (qualcosa di pesante che rientra). |
| `hull_thump` | 0,6 s | Colpo sordo sotto lo scafo. |

## Pesca e oggetti (mono)

| id | durata | descrizione |
|---|---|---|
| `cast` | 1,1 s | Frusta della canna + filo che corre (zip del mulinello libero). |
| `plop` | 0,4 s | Esca/piombo che entra in acqua. |
| `rod_bell_1`, `rod_bell_2` | 1,2 s | Campanellino d'ottone in punta alla canna che trilla per l'abboccata (scosse irregolari, 2–3 rintocchi ravvicinati). |
| `reel_loop` | 0,48 s | Cricchetto del mulinello mentre si recupera, loop esatto (la velocità si regola col playbackRate). |
| `line_tension` | 2 s | Filo sotto tensione: cigolio acuto e teso, loop. |
| `line_snap` | 0,6 s | Filo che si spezza (twang secco). |
| `fish_out` | 1,2 s | Pesce che esce dall'acqua: schizzo + guizzi. |
| `fish_bucket` | 0,9 s | Pesce che cade in un secchio di metallo zincato e sbatte la coda. |
| `fish_throw` | 0,8 s | Lancio di un pesce (fruscio) e schiaffo bagnato all'arrivo. |
| `lamp_switch` | 0,25 s | Interruttore/valvola della lampara. |
| `lamp_flicker` | 0,6 s | Crepitio della lampara che tremola. |
| `tarp_in` | 0,9 s | Ci si infila sotto un telone di tela cerata (fruscio pesante). |
| `tarp_out` | 0,8 s | Si esce dal telone. |
| `heartbeat` | 1 s | Un battito cardiaco ovattato (lub-dub), da ripetere. |
| `sonar_ping` | 2,2 s | Ping del sonar con eco. **Stereo**. |
| `sonar_blip` | 0,15 s | Bip di un contatto. |
| `radio_on` / `radio_off` | 0,4 s | Squelch VHF in apertura / chiusura. |
| `static_burst` | 1,5 s | Esplosione di statica (dopo il jumpscare). **Stereo**. |

## Voce radio (mono)

`voice_01` … `voice_24` (60–220 ms ciascuno): sillabe borbottate di un vecchio pescatore, voce roca e bassa (fondamentale ~95–120 Hz con jitter), vocali diverse (a, e, i, o, u con formanti realistiche) e consonanti accennate, già filtrate come una radio (passa-banda 300–3000 Hz, leggera saturazione). Il gioco le concatena a caso mentre scorrono i sottotitoli (stile "animalese" ma umano e malinconico).

## Le creature (mono) — da definire

**I mostri non parlano: solo versi.** L'unica eccezione è la conta di Hatch fino a dieci (testo approvato, vedi `LORE.md`).

Per ora nel gioco ci sono versi **provvisori**, sintetizzati al volo (`src/app/sfx.ts`): si sostituiranno quando li definiamo insieme. Intenzioni di massima:
- **Gulpy**: respiro umido e affamato, deglutizioni enormi, la mascella che si sgancia (schiocco osseo), il salvagente di gomma che cigola.
- **Molly**: nocche lunghe che bussano sullo scafo, versi di bambina distorti (risatina, piagnucolio, capriccio), il legno che geme mentre dondola la barca.
- **Hatch**: la voce di bambino che conta fino a dieci (localizzata), passi bagnati, il ronzio del giocattolo luminoso.

## Musica e stinger (stereo)

| id | durata | descrizione |
|---|---|---|
| `mus_title` | ~64 s, loop | **Ninna nanna della Madre** al carillon: melodia semplice in La minore, 3/4, ~66 BPM; timbro di carillon (parziali metalliche, attacco secco, decadimento), leggermente stonato e con "wow" come un nastro vecchio; sotto, un pad sott'acqua molto basso. Loop perfetto. |
| `mus_night_start` | 4 s | Stinger cupo d'inizio notte: colpo basso + tintinnio di carillon che si spegne. |
| `mus_6am` | 7 s | Le 6 del mattino: accordo maggiore che si apre, campanelle, sollievo. |
| `mus_gameover` | 8 s | Carillon che rallenta e si scarica, stonandosi; bordone basso. |
| `mus_madre` | 10 s | La Madre si sveglia: un lamento enorme e lentissimo (canto di balena abissale), coro grave. |

## Interfaccia (stereo, brevi e discreti)

`ui_hover` (40 ms, tick legnoso), `ui_click` (90 ms), `ui_back` (110 ms), `ui_start` (1,5 s: rintocco di campanella + fruscio di mare).
