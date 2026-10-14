# Su Steamworks: l'account e la pagina, passo per passo

Il 14 ottobre l'utente ha scelto di anticipare l'account Steamworks: il materiale della pagina è già pronto, e prima
esce la pagina «Prossimamente», più a lungo raccoglie liste dei desideri prima del Next Fest di febbraio. Lo stesso
giorno l'utente ha aperto l'account e pagato la quota; Valve sta verificando i dati. Qui ci sono
i passi e, per ogni voce della pagina, il file da usare. Steamworks è in inglese: i nomi delle voci sono i suoi. Le
date sono nella pagina «Splashland su Steam».

## 1. L'account (lo apre l'utente)

Da [partner.steamgames.com](https://partner.steamgames.com/), voce **Steam Direct**. Serve:

- **un account Steam** (va bene quello di sempre) con **Steam Guard** sul telefono e un numero di telefono collegato:
  Steamworks lo usa per confermare le operazioni importanti;
- **i dati legali** come sul documento d'identità, e l'indirizzo. Si firma il contratto di distribuzione (Steam
  Distribution Agreement): lo firma una persona maggiorenne (o una ditta), a cui vanno i soldi del gioco;
- **un conto in banca** (IBAN e BIC) intestato alla stessa persona del documento;
- **il questionario fiscale** (tax interview): per chi vive in Italia è quello del modulo americano W-8BEN, col
  codice fiscale come numero fiscale straniero;
- **la quota**: 100 dollari per il gioco, che Steam restituisce quando il gioco incassa 1.000 dollari. La demo si
  aggiunge dopo, senza un'altra quota.

La verifica di banca e dati fiscali richiede qualche giorno (le guide dicono da 2 a 7 giorni lavorativi). Dal
pagamento all'uscita del gioco c'è un'attesa obbligatoria di qualche settimana, che a noi non tocca: il gioco esce
dopo il festival. In Italia i soldi che arriveranno vanno dichiarati: quando arrivano i primi, conviene sentire un
commercialista.

## 2. La pagina («Store page admin»)

| Su Steamworks | Cosa ci va | Da dove |
|---|---|---|
| Nome del gioco | SPLASHLAND IS CLOSED! | il titolo del gioco |
| Sviluppatore ed editore | Ettore Canu | scelta dell'utente del 14 ottobre |
| Data di uscita | «Coming soon»: non impegna a una data | scelta dell'utente del 14 ottobre |
| Descrizione breve e lunga, per lingua | il file della lingua, già col formato di Steam | `testi/en.txt`, `testi/it.txt`… |
| Capsule | le quattro immagini | `capsule/` (tabella in `LEGGIMI.md`) |
| Screenshot | gli 8, nell'ordine dei numeri dei file | `screenshot/` |
| Trailer | quello senza la riga della demo | `trailer/trailer_le_regole.mp4` |
| Libreria | capsula, intestazione, immagine larga, logo | `libreria/` |
| Lingue | interfaccia e sottotitoli in 9 lingue, niente audio completo | `PAGINA.md`, «Le lingue» |
| Requisiti di sistema | minimi e consigliati | `PAGINA.md` |
| Questionario sui contenuti | le risposte proposte | `PAGINA.md` |
| Tag | i 20, in ordine | `PAGINA.md` |

Sulla pagina vanno subito **tutte e nove le lingue** (scelta dell'utente del 14 ottobre, «Subito, così come sono»):
le sette nuove (`testi/es.txt`…`testi/ko.txt`) sono traduzioni automatiche, messe così come sono. Se un madrelingua
trova un errore, si corregge in `PAGINA_lingue.md` e si rifanno i file con
`tools/.venv/bin/python tools/steam_testi.py`.

Poi la pagina va **in revisione** (Valve la guarda in qualche giorno lavorativo) e, quando è approvata, si pubblica
come **«Prossimamente»** (Coming Soon). Da lì la gente può aggiungere il gioco alla lista dei desideri, e ci si può
iscrivere al Next Fest di febbraio (entro il 10 gennaio).

## 3. Dopo

- **La demo**: le prime due notti, la build con «ultima_notte» 2 e senza scorciatoie, come demo collegata al gioco.
- **Il trailer con la riga della demo** (`trailer/trailer_le_regole_con_demo.mp4`) prende il posto dell'altro quando
  la demo è su Steam.
