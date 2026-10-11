# Revisione della notte 6 (la Madre)

Revisione del branch `claude/notte6` (bozza: `NIGHTS[6].bozza`), 11 ottobre. Le regole sono quelle di
`docs/NOTTI_E_MOSTRI.md`, sezione «Notte 6». Le correzioni sono sul branch `claude/notte6-revisione`.

## Cosa ho provato

- `npm ci`, `npx tsc --noEmit` (pulito), `npx vitest run` (54 test verdi prima, 56 dopo le correzioni).
- Nel browser headless (Chromium con swiftshader, `?step&bozze`, il bot esperto che gioca da solo):
  - **a.** Una notte 6 intera giocata dal bot esperto: tre passate (alle 140, 290 e 402,5 s di notte; sotto la barca
    per 10, 15 e 20 s) superate con lo sguardo fermo a 21° dal primo all'ultimo fotogramma, i suoni nell'ordine giusto
    (`madre_far_*` lontani, `madre_approach`, `madre_lullaby` a 8 s, `madre_pass_1`/`_2`/`_3` a 10 s), dodici pesci su
    dieci, l'alba. Nessun errore né avviso in console.
  - **b.** Una passata in cui giro lo sguardo di 20°: muoio dopo un fotogramma (`moved`), il jumpscare da sotto (la
    barca sbalzata, lo sguardo che cade verso l'acqua, il buio), `js_madre`, poi la neve, poi i risultati con «Mama
    Marina ama i suoi piccoli. Adesso anche te.» (in inglese nel browser di prova: «Mama Marina loves her little
    ones. Now you too.»). Nessun errore in console.
  - **c.** Il finale A: `bell_dawn` alle sei, `madre_dawn` a 1,5 s, la barca che dondola e s'inclina, `amb_dawn` a
    21,5 s, il sole dopo i 15 s, la radio a 23,8 s («Ce l'hai fatta.» / «Per quest'anno.», poi `radio_off` a 27,2 s) e i
    risultati a 28 s con «Ce l'hai fatta. Per quest'anno.».
  - **d.** Col binocolo alzato su un luogo (2° di lato dall'albergo, dove di solito lo sguardo ci scivola sopra da
    solo) per tutta la passata: lo sguardo resta fermo a 126,75° dal primo all'ultimo fotogramma e lei se ne va.
    Pausa con Esc durante la passata: lei si ferma con la notte (stateTime fermo a 3,05 s per 3 s di pausa), alla ripresa riparte da lì e non ti prende.
- Le schermate sono in `docs/concept/notte6_prova_*.jpg`.

## Corretto in questa revisione

1. **La batteria morta col sonar (o il binocolo) alzato: morte senza colpa.** `src/game/sim.ts` `setView`: aprire il
   sonar mentre lei passa è un gesto, e lo si riconosceva da `sonarOpen && !this.sonarOpen`; ma al buio `this.sonarOpen`
   resta sempre falso, quindi chi teneva il binocolo alzato (che per la simulazione è «sonar aperto») o aveva lasciato il
   sonar aperto prima che la batteria morisse veniva preso al primo fotogramma della passata, senza muovere niente.
   Adesso si ricorda come lo tiene il pescatore (`sonarAsked`). Test: «il sonar (o il binocolo) già aperto prima che
   passi non conta, nemmeno se la batteria muore».
2. **Il telone tirato appena prima che passi: morte senza colpa.** `src/game/sim.ts` `updateMother`: il telone che si
   muove (`goingIn`/`goingOut`, 0,7 e 0,6 s) contava come gesto anche se l'avevi tirato durante l'avvicinamento, quando
   ci si può ancora muovere. Premere C a 9,6 s dell'avvicinamento = morte a 10 s. Toccarlo mentre lei passa resta un
   gesto (lo prende già `toggleHide`); il movimento che finisce da solo no, come la vista che si ferma
   (`MOTHER_SETTLE`). Test: «il telone tirato appena prima che passi finisce di muoversi senza colpa».
3. **Il suono dell'avvicinamento non si poteva fermare.** `src/app/sfx.ts` `motherApproach` non restituiva la voce: i
   12 s di `madre_approach` continuavano sopra un jumpscare, la neve e i risultati, se morivi in quel momento (un
   figlio già all'attacco quando lei arriva, la ninna nanna della batteria finita). Adesso la voce si tiene
   (`motherApproachV`) e si tronca alla morte e in `destroy`. Insieme: la ninna nanna della Madre (`motherSong`) si
   tronca anche con le morti che non sono «ti sei mosso» (un figlio, la batteria, la quota mancata), invece di
   continuare fino ai risultati.

## Da guardare (in ordine di gravità)

1. **Alzare il binocolo mentre passa è la morte, ma le regole non lo dicono.** `src/app/night.ts:724`
   (`sim.setView(view.yaw, this.sonarOpen || this.bino > 0.5)`): per la simulazione il binocolo è il sonar, quindi
   alzarlo durante la passata (tasto destro) fa scattare il jumpscare anche se lo sguardo non gira. Le regole elencano
   «canna, lampara, telone, pesci o sonar» e lo sguardo; la radio dice «non guardarti intorno», che lo copre solo in
   parte. Riprodurre: durante la passata, tasto destro col mouse fermo al centro. Da decidere: se è giusto (è un
   gesto), aggiungerlo alla regola e forse al suggerimento; se no, passare alla simulazione il sonar e il binocolo
   separati e far contare solo il sonar. Tenerlo alzato da prima, invece, va bene (prova d).
2. **Il mouse sul bordo quando il pesce scappa.** `src/app/night.ts:677`: mentre recuperi lo sguardo non gira coi
   bordi (`!reeling`); se lei passa mentre hai un pesce in canna e il mouse è nella fascia del bordo (il 20% a destra o
   a sinistra), quando il pesce scappa (lenza molle: succede da solo, perché non puoi recuperare) la vista comincia a
   girare da sola e lei ti prende. La canna sullo schermo sta al centro (u ≈ 0,49–0,61 guardandola), quindi capita
   solo a chi tiene il mouse lontano; ma è una morte senza un gesto nuovo. Riprodurre: pesce in canna, mouse a x > 0,8,
   lasciare il mulinello prima della passata e aspettare che il pesce scappi. Proposta: durante la passata (o mentre
   `mother.near`) lo sguardo gira coi bordi solo se il mouse si è mosso dopo l'inizio della passata.
3. **I tempi del suono dell'avvicinamento.** `madre_approach` dura 12 s ed è pensato con la passata «verso 13 s»
   (docs/AUDIO.md, la proposta); nel gioco la passata comincia a 10 s, quindi il richiamo che «arriva sotto la barca»
   e la coda dell'avvicinamento si sovrappongono ai primi 2 s di `madre_pass_*`. Sentire insieme: o si accorcia il
   suono a 10 s, o si fa partire la passata del suono un po' prima. (Anche le passate sono 12/16/20 s contro 10/15/20 s
   di gioco: la coda continua mentre se ne va, ed è giusto così.)
4. **Il jumpscare della Madre non ha ancora i fotogrammi** (`jumpscares.mother` vuoto): c'è il ripiego (la barca
   sbalzata, lo sguardo che cade verso l'acqua, il buio in 0,9 s) con l'urlo `js_madre`. Va bene per la bozza; quando
   arriva il render, `endTimer` prende la durata dai fotogrammi.
5. **Dopo il finale A c'è «Fine della demo».** `src/app/app.ts:278`: la notte 6 è l'ultima giocabile (la 7 non c'è),
   quindi i risultati del finale dicono «Fine della demo. Altre notti in arrivo.» al posto dei titoli di coda (le regole:
   «I titoli di coda, e si sblocca la notte 7»). Va bene finché la notte 7 e i titoli non ci sono; da ricordare quando
   arrivano. Riprodurre: vincere la notte 6 con `?bozze`.
6. **Durante il finale resta il suggerimento della canna.** Nel finale (28 s, i comandi fermi) sotto resta scritto
   «Tieni premuto per recuperare…» se all'alba avevi un pesce in canna (`updateHud`, il suggerimento non guarda
   `finished`). Piccolo; si vede nella schermata della radio dell'alba.
7. **Nota sulle prove nel browser.** I suoni si decodificano tutti dopo il primo tasto; nel browser di prova (CPU
   lenta, quattro pagine insieme) i `madre_*` non erano ancora pronti nelle prime prove saltate avanti nel tempo, e
   sono partiti i ripieghi (`splash_big`, `mus_title`, `creak_2`). Su una macchina vera non dovrebbe succedere; se si
   vuole stare tranquilli, l'intro della notte 6 può aspettare `audio.start()`.

## Cose controllate che vanno bene

- Le ore delle passate (2, 4 e 5:30 meno 10 s), i 10 s di avvicinamento, le passate da 10/15/20 s, i 6 s per andarsene.
- La pausa ferma tutto (la simulazione, l'audio sospeso) e alla ripresa non c'è nessun gesto: Esc non è un gesto e
  `setPaused` lascia il mulinello.
- Un figlio che attacca proprio quando lei comincia ad avvicinarsi: `retreatAll` lo rimanda giù nello stesso fotogramma.
- La batteria che muore mentre passa: la lampara si spegne senza `setLamp` (niente gesto); col sonar o il binocolo
  alzati ora si sopravvive (correzione 1).
- Il binocolo non si centra da solo mentre lei è vicina, né quando lo alzi né quando smetti di girare.
- Le voci: la passata finisce da sola, la ninna nanna si spegne in 4,5 s quando se ne va e in 3 s all'alba; tutte si
  fermano in `destroy`.
