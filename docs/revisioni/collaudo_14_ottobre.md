# Collaudo completo (notte del 13-14 ottobre)

Il passo «Collaudo completo» scelto dall'utente il 13 ottobre: il bot su tutte le notti, i percorsi interi e i pezzi
del gioco uno per uno, sul codice di `ac82cd1` (ramo `claude/prova-12-ottobre`). Prove in una copia a parte del
repository (staccata, nessun commit), con tre server: lo sviluppo (`npx vite`), la build di produzione (`vite build`,
`vite preview`) e la build della demo (`VITE_ULTIMA_NOTTE=2`). Chromium senza finestra e senza scheda video
(swiftshader); Electron dentro uno schermo virtuale (Xvfb). Gli script sono quelli del collaudo del 12-13 ottobre,
aggiornati dove il gioco nel frattempo è cambiato, più quattro nuovi: la demo, Electron, le novità del 13 ottobre e
il logo.

## In breve

- **Nessun difetto nuovo nel gioco.**
- I difetti del collaudo di prima, corretti il 13 ottobre, sono verificati: D18 (col sonar aperto Spazio e clic
  ferrano), D19 (grafica persa: la notte va in pausa; ritrovata: il gioco riparte), D20 («Nuova partita» con una
  partita in corso chiede conferma, anche col controller). D7 (le scritte italiane nelle tane) era già chiuso: tane
  rifatte con le scritte inglesi o neutre il 12-13 ottobre.
- Sei script si fermavano solo perché il gioco è cambiato (la conferma, «Continua» primo, le nove lingue, il
  volantino più lungo, la ricarica dopo la grafica persa, la nebbia accesa di partenza): aggiornati e ripassati,
  tutto a posto (sotto, «Gli script aggiornati»).

## I risultati

| Prova | Esito |
|---|---|
| Controllo dei tipi, 197 test (17 file), build di produzione, build della demo | a posto |
| Notti 1-7 col bot bravo (seme 8, italiano e inglese alternati), più una notte 1 (seme 7) | 8 vinte su 8; nessun errore, nessun suono mancante |
| Notti 1-7 col bot medio (seme 21) | 5 vinte su 7: la 3 persa per Soggy, la 6 per la Madre (si è mosso durante la passata). In simulazione il bot medio vince la notte 3 l'80% delle volte e la 6 il 74% (il bravo 100% e 97%): un limite del bot |
| Percorsi interi, dalla nuova partita: sei notti, cinque immersioni (in ogni tana la cosa trovata e il pesce lasciato), finale «I tuoi», titoli di coda, risultati, notte extra, Indietro | italiano e inglese: a posto, nessun errore della pagina |
| Finali dalla notte 5: «Nessuno» (inglese), A senza immersioni (italiano), B con la Madre a 10 (a 9 no) | a posto |
| Salvataggi e «Continua»: dall'alba, a metà notte, dopo «Nuova partita», salvataggi vecchi, la lingua dopo il ricaricamento; la vittoria salvata alle sei; il blur a notte finita | a posto |
| Tastiera e mouse in notte (italiano e inglese) | 0 controlli falliti |
| Le undici morti (i sette mostri, Soggy, la Madre in due modi, la quota mancata), in italiano e in inglese, e «Riprova» | 22 su 22: testi giusti, nessun suono rimasto acceso |
| Opzioni (nebbia, tutorial, luminosità, qualità, testi, lampi, lingua) | a posto; il pulsante della lingua gira tutte e nove |
| Controller: le opzioni; le immersioni fino in fondo (Xbox in italiano, PlayStation in inglese) | 9 su 9; 41 su 41 e 41 su 41 |
| Falsi allarmi: il tonfo; la sagoma nella nebbia | suonano / compare e sparisce |
| Vibrazioni del controller e «Riduci lampi e scosse» | ci sono, e l'opzione le spegne |
| Immersione interrotta e gioco riaperto | si rifà dall'alba, niente a metà |
| L'alba coi testi grandi (cinque misure, due dimensioni) | nessuna riga tagliata |
| La nebbia: avvio, cambi a notte in corso, durante il jumpscare, al titolo | 9 su 9 |
| Le tane (Archie a 1920×1080), il Diario a 1920×1080 | a posto |
| Build di produzione | i font, 178 suoni su 178, nessun errore; `?finale` ignorato |
| La demo delle prime due notti | 16 su 16: la notte 1 porta all'alba e all'immersione, la 2 dice «Fine della demo»; la notte extra non si apre (nemmeno con un salvataggio del gioco intero, `?notte=7` o Alt+7) |
| Electron (la cartella del gioco, come l'eseguibile) | 7 su 7: parte da file, WebGL2, le lettere della tastiera, il logo, la notte, il salvataggio dopo la chiusura, nessun errore |
| Le novità del 13 ottobre | il volantino dura 8,8 s e si salta col clic; la nebbia accesa al primo avvio; il binocolo sale in 0,3 s e scende in 0,22 s; il logo; la sagoma; le facce delle schede |
| Le scritte in nove lingue (tre misure, due dimensioni dei testi; `scripts/lingue.mjs` su `e7c4c69`) | nessuna fuori posto |

## Gli script aggiornati (non erano difetti)

- `continua.mjs`, `padtest2.mjs`, `nuova_partita*.mjs`: «Nuova partita» con una partita in corso chiede conferma, e
  «Continua» è il primo pulsante (D20).
- `percorso.mjs`, `continua.mjs`: il volantino dura 8,8 s (prima 3,6).
- `opzioni.mjs`: le lingue sono nove; dall'inglese il pulsante va allo spagnolo.
- `robustezza.mjs`: a grafica ritrovata il gioco si ricarica (D19).
- `nebbia_gulpy.mjs`: partiva da un salvataggio della versione di prima (`rev` 1) con la nebbia spenta, che il gioco
  riaccende una volta (`OPTIONS_REV` 2): da lì le sue etichette erano al contrario. Con un salvataggio nuovo, 9 su 9.
- Il controllo dei loop audio dopo la notte 6 guarda mentre scorrono i titoli di coda: la musica che trova è la loro.

## Limiti

- Il bot legge lo stato della simulazione: non vede e non sente. Le notti vinte dicono che regole e gioco reggono,
  non che i segnali si capiscano.
- Senza scheda video: il gioco va a passi senza disegnare e disegna solo per le catture; in Electron 0,5 fotogrammi
  al secondo. Le prestazioni vanno provate su PC veri.
- Il controller è finto (`navigator.getGamepads`). Lo Steam Deck vero, i controller veri e l'ascolto dei suoni non
  sono provati qui.
