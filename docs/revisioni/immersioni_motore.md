# Revisione: il motore delle immersioni (`claude/immersioni-motore`)

> Revisione dell'11 ottobre del branch `claude/immersioni-motore` (fino a `37d2f8a`) rispetto a `origin/claude/lampara`
> (`git diff origin/claude/lampara...HEAD`), confrontato con il disegno approvato in `docs/IMMERSIONI.md`.
> Non è stato corretto niente: qui ci sono solo i risultati, dal più grave al meno grave.

## Cosa è stato provato

- `npm ci`, `npx tsc --noEmit` (nessun errore), `npx vitest run` (59 test, tutti passano).
- **Simulazione delle notti, prima e dopo**: `npm run sim -- <notte> 60` per le notti 1-5, sulla base (in una
  worktree di `origin/claude/lampara`) e sul branch: le uscite sono **identiche byte per byte** (stessi seed, tre
  abilità). Con uno script a parte: Archie sfamato nella notte 4, Lampy e Archie nella 5 (20 seed ciascuno) non
  partono mai.
- **Grafica delle notti, prima e dopo**: Chromium headless (`--use-angle=swiftshader`, `?step`, `Math.random` e
  `Date.now` fissati), due server Vite (base e branch), stessa scena: il titolo e le notti 1, 3 e 5 dopo 1, 21 e 71
  secondi di gioco. Le schermate sono **identiche pixel per pixel** (il titolo, fotografato subito, una volta è uscito
  diverso anche fra due giri dello stesso branch, probabilmente per la dissolvenza CSS ancora in corso; aspettando
  5 secondi è identico in tutti i giri). Lo schermo dei risultati di una notte vinta
  cambia solo per quello che chiede il disegno: la riga «Oltre la quota» e il tasto «Scendi con le bombole» sopra
  «Notte successiva».
- **Flusso completo nel browser**, partendo da un salvataggio vecchio (senza `dawn`, `fed`, `dens`): notte 1 vinta con
  11 pesci, «Scendi con le bombole», sotto la barca, la grotta grande, la tana di Gulpy girata tutta a destra e
  tutta a sinistra, il pesce a Gulpy, la tana vuota di Robin, la terza tana rifiutata, l'aria che finisce, la
  risalita da soli, l'intro e la notte 2 con `asleep = gulpy`. Contando le texture WebGL vive (`createTexture` e
  `deleteTexture` intercettati), all'alba sono 185, sotto la barca 188, nella tana 192 e di nuovo **185** dopo la
  risalita: il giro normale libera tutto. I loop della notte sono fermati, la vista torna come prima
  (`swell` 1, `hfov` 90, `pitch` −12), il salvataggio diventa `fed: {night: 2, who: "gulpy"}`,
  `dens: ["gulpy", "robin"]`, `dawn: null`.

**Risultato per le notti 1-5: nessuna regressione trovata**, né nella grafica né nella simulazione né nel flusso dei
menu (a parte le aggiunte del disegno sullo schermo dei risultati).

---

## 1. Media: se il panorama di un posto non si carica, si resta al buio e le texture non si liberano più

**Dove**: `src/app/dive.ts:460` (`void this.load(to).then(() => this.arrive())`, senza `catch`) e
`src/app/dive.ts:210-228` (`Promise.all` delle texture in `load`).

**Cosa succede**: durante il passaggio da un posto all'altro, se un file del posto manca o non si scarica:
- la promessa di `load` viene rifiutata e nessuno la gestisce: un errore non gestito in console
  (`asset mancante: …`), la fase resta `loading` per sempre, lo schermo resta nero con le bolle e si può uscire
  solo con «Risali»;
- le texture già create dalle altre `texture()` dello stesso `Promise.all` (gli altri passi del panorama e degli
  strati del mostro) non arrivano mai nel renderer e non vengono mai cancellate: restano in memoria GPU fino alla
  chiusura del gioco;
- l'aria della tana è già stata spesa e la tana è già contata fra quelle viste (`this.run.enter(to)` alla riga 459
  viene prima del caricamento), quindi il mostro risulta «visto» e sfamabile solo a parole.

Lo stesso `Promise.all` perde le texture anche al primo posto (`start()`, riga 181): lì l'errore arriva a
`App.dive` (`fail`, che passa alla notte dopo), ma le texture create prima dell'errore restano in memoria.

**Come riprodurlo**: nel browser headless con `?step`, intercettare
`**/dormiente_respiro_lantern.webp` con una risposta 404, scendere, andare nella grotta grande e poi nella tana di
Gulpy. Risultato misurato: `[pageerror] asset mancante: immersioni/segnaposto/dormiente_respiro_lantern.webp`,
fase `loading`, `fade` 0 per sempre; texture vive 185 all'alba, 191 dopo il tentativo, **ancora 191** dopo
«Risali» e la fine dell'immersione (6 texture perse).

## 2. Media: un mostro sfamato in una partita vecchia dorme anche nella nuova, senza aver lasciato nessun pesce

**Dove**: `src/app/app.ts:120` («Nuova partita» chiama solo `intro(1)`), `src/app/app.ts:265` (il mostro sfamato si
toglie solo quando si vince *la sua* notte), `src/app/app.ts:203`.

**Cosa succede**: `save.fed` sopravvive a «Nuova partita» e a ogni alba successiva in cui non si scende. Vincendo di
nuovo la notte prima e passando subito alla notte dopo (senza immersione), il mostro sfamato in un'altra alba
continua a dormire. Il disegno dice «un pesce per alba»: qui un'alba senza pesce (e senza immersione) ne
eredita uno vecchio. Se invece in quella nuova alba si scende e non si sfama nessuno, `endDive` lo cancella
(`app.ts:339`): lo stesso giocatore, nella stessa situazione, ottiene due risultati diversi a seconda che scenda o no.

**Come riprodurlo**: vincere la notte 1, scendere, lasciare il pesce a Gulpy, risalire (`fed: {night: 2, who:
"gulpy"}`); tornare al menu; «Nuova partita»; vincere la notte 1 **con zero pesci oltre la quota**; «Notte
successiva»: nella notte 2 `__game.app.night.sim.asleep` vale `"gulpy"`. (Verificato leggendo il codice, non
nel browser: `endNight` toglie `fed` solo se `fed.night === nightNo`, cioè 2 ≠ 1, e `startNight` della notte 2
lo passa alla simulazione.)

## 3. Bassa: «Risali» (o l'aria che finisce) durante il caricamento di un posto può essere annullato

**Dove**: `src/app/dive.ts:276-287` (`arrive()` mette `phase = 'in'` senza guardare se nel frattempo è partita la
risalita) e `src/app/dive.ts:305-310`.

**Cosa succede**: se la risalita parte mentre la fase è `loading` (dal tasto «Risali», sempre cliccabile, oppure
dall'evento `airOut`) e il caricamento del posto finisce prima del fotogramma successivo, `arrive()` rimette la
fase a `in` e la risalita è persa: si arriva nel posto nuovo. Se è stato l'`airOut`, `DiveRun` è già `out` e non
manda più eventi: si resta giù con l'aria a zero finché non si clicca «Risali». La finestra è di un fotogramma,
quindi nel gioco vero capita di rado, ma capita.

**Come riprodurlo** (`?step`): nella grotta grande `diving.go('tana_gulpy')`, avanzare un fotogramma alla volta
finché la fase è `loading`, chiamare `diving.ascend()` (fase `ascend`), aspettare 3 secondi senza fotogrammi:
la fase diventa `in`; dopo altri 4 secondi di gioco il modo è ancora `dive`, fase `look`, posto `tana_gulpy`.

## 4. Bassa: `save.dawn` si scrive ma non si legge mai

**Dove**: `src/app/save.ts:35` e `:67`, `src/app/app.ts:264` e `:342`.

**Cosa succede**: `dawn` (la notte vinta e i pesci avanzati) viene salvato a ogni notte vinta e azzerato a fine
immersione, ma nessuno lo legge: l'immersione si apre solo dallo schermo dei risultati, con lo `spare` passato a
mano. Se si chiude il gioco sullo schermo dei risultati, l'immersione di quell'alba è persa comunque. O serve a
riprendere l'alba (e allora manca quella parte), o è codice morto (e anche la frase in `docs/IMMERSIONI.md`, «Il
salvataggio», va rivista).

**Come riprodurlo**: `grep -rn "dawn" src/app` (a parte la grafica dell'alba in `night.ts`): solo scritture.

## 5. Bassa: differenze dal disegno approvato

- **Solo la grotta grande a 360°**: anche **«sotto la barca»** è un panorama a sfera intera in cui si guarda attorno
  liberamente (`public/assets/img/immersioni.json`, `sotto_barca`: `latMin` −90, `latMax` 90, senza `lonMin`,
  `lonMax` e `frame`). L'approvazione dell'11 ottobre dice «solo la grotta grande si esplora a 360°»; la sezione
  «Il motore» invece dice «Solo le grotte (sotto la barca e la grotta grande)». È da far confermare all'utente: o
  sotto la barca diventa un'inquadratura fissa, o va corretto il riassunto della decisione in cima al documento.
  Anche il commento in cima a `src/app/dive.ts:3-4` («Ogni posto è un panorama a 360°») non vale più per le
  camerette.
- **Due tane per immersione**: rispettato (`air.maxDens` 2, verificato nel browser: la terza tana viene
  rifiutata). Però anche la **tana vuota** del mostro nuovo conta come una delle due (`src/app/dive_run.ts:170` e
  `:180`): dopo la notte 1, chi guarda la tana vuota di Robin può vedere un solo mostro che dorme. Il disegno non lo
  dice: da confermare.
- **Un pesce per alba, a un solo mostro**: rispettato (`dive_run.ts:143`, `:195`; nel browser il secondo tentativo dà
  «Il pesce l'hai già lasciato»), a parte il caso del punto 2.
- **La tana del mostro nuovo della notte dopo è vuota**: rispettato (`canFeed`, `denState`; nel browser la tana di
  Robin dopo la notte 1 mostra «La tana è vuota. Chi ci dorme è già in giro.» e non ha il mostro cliccabile; in
  simulazione l'opzione `fed` del mostro nuovo non conta).
- **Camerette come inquadrature fisse, ±30°**: rispettato. Nel browser lo sguardo si ferma a yaw +30,0 e −30,0
  e a pitch −15 ± 4; il panorama parziale (160° × 80°) copre il campo visivo anche con l'ondeggiare (±0,85°) e con
  lo schermo stretto (il campo verticale è limitato a 68° da `View`).

## 6. Bassa: codice morto e testi non usati

- `monstersOfNight` (`src/game/config.ts:383`) si usa solo in `tests/sim.test.ts`, mai nel gioco.
- `STRINGS.dive.loading` («Ti infili le bombole…», `src/i18n.ts`, in italiano e in inglese) non si usa: mentre si
  caricano i dati e il primo panorama lo schermo resta nero senza scritte.
- `save.dawn` (vedi il punto 4).
- `isMonster` (`src/app/save.ts:43`) usa `x in ARRIVAL`, che accetta anche `"toString"`, `"constructor"` e le altre
  chiavi del prototipo: un salvataggio rovinato con `fed.who: "toString"` passa il controllo. Non fa danni
  (`canFeed` poi dà `false`), ma il controllo non fa quello che dice; `Object.hasOwn` lo farebbe.

## 7. Bassa: prestazioni nel ciclo dei fotogrammi

Niente di grave; le misure sono nel ciclo dei fotogrammi, quindi le segnalo:
- **Nelle notti** (`src/engine/renderer.ts:341-342`): per ogni strato e ogni fotogramma si creano due o tre array
  nuovi (`[0, 1, 0, 0]`, `[1, 1, 1]`, e lo spread di `torch`) per `uTorch` e `uTint`, e si mandano due uniform in
  più. Sono pochi byte, ma il ciclo della notte prima non li aveva; basterebbero due costanti.
- **Nelle immersioni**: `drawGauge` (`src/app/dive.ts:539-586`) ridisegna tutto il manometro (tacche, testo
  compreso) su un canvas 2D a ogni fotogramma anche quando l'ago non si muove; `render()` (`dive.ts:593-600`)
  fa `map` e `split(':')` delle chiavi a ogni fotogramma; `updateSpots` scrive `canvas.style.cursor` e i
  `transform` di tutti i punti a ogni fotogramma (`dive.ts:527`, `:534`); `drawWater` crea un `Float32Array(16)`
  a ogni fotogramma (`renderer.ts:391`).

## 8. Note (non sono difetti)

- I test di `tests/sim.test.ts` sul mostro sfamato provano solo Gulpy, Molly, Hatch e Robin: Archie, Lampy e Fangy
  non sono coperti (provati a mano in questa revisione: non partono mai).
- L'effetto del pesce sul bilanciamento è molto forte, come dice già il documento: `npm run sim -- 2 200 --sfama`
  porta il medio dall'81,5% al 100% e il maldestro dal 58,5% al 100% sfamando Molly (che uccide direttamente solo
  1 e 8 volte su 200: il resto lo fanno la quota e la batteria). Con questi numeri, nella seconda notte
  l'immersione decide la partita.
