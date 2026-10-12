# Localizzazione: le scritte dentro le immagini

Prova dell'utente del 12 ottobre: «stai attento alle immagini e ai testi nelle immagini», e «prima del lancio potremmo
doverlo localizzare anche in altre lingue». I testi dell'interfaccia stanno in `src/i18n.ts`; questo documento è per
le scritte disegnate o renderizzate **dentro le immagini**, che non passano da lì.

## Le regole

1. **Un'immagine con scritte che il giocatore deve capire ha una versione per lingua.** L'originale è in italiano,
   `nome.webp`; ogni lingua tradotta ha accanto `nome_<lingua>.webp` (per esempio `pastelli_piscina_en.webp`). Il gioco
   la sceglie con `localizedImage(path, lang, langs)` in `src/i18n.ts`: la versione della lingua, se c'è; se no quella
   inglese; se no l'originale.
2. **Le scritte stanno in una tabella per lingua nello script che fa l'immagine**, mai sparse nel codice: per una
   lingua nuova si aggiungono le sue righe e si rilancia lo script con `--lingua xx`.
3. **Nelle scene 3D (render lunghi: il panorama, il binocolo, le tane) si usano scritte che valgono in tutte le lingue**:
   nomi propri (SPLASHLAND, MAMA MARINA'S, MIRAMARE), numeri e date in cifre, e l'inglese delle insegne di un parco
   acquatico (NIGHT SPLASH, TICKETS, SNACK SHACK, HAPPY BIRTHDAY). Così non si rifà un render per ogni lingua.
4. **Prima di dare per finita un'immagine con scritte, si guarda davvero in ogni lingua** (ritagli a piena
   risoluzione): che la scritta ci stia, che non copra il resto, che si legga.

## Le immagini con scritte

### Tradotte (una versione per lingua)

| Immagine | Dove si vede | Scritte (it → en) | Script |
|---|---|---|---|
| `disegni/pastelli_piscina` | alba della notte 1, Diario | TROVAMI! → FIND ME!, GUARDAMI! → LOOK AT ME!, HO FAME! → I'M HUNGRY!, AGOSTO 97 → AUGUST 97 (SNACK resta) | `pastelli.py` |
| `disegni/pastelli_tesoro` | alba della notte 2, Diario | IL MIO TESORO → MY TREASURE | `pastelli.py` |
| `disegni/pastelli_compleanno` | alba della notte 3, Diario | TANTI AUGURI → HAPPY BIRTHDAY | `pastelli.py` |
| `disegni/pastelli_sottacqua` | alba della notte 4, Diario | AIUTO! → HELP! (AH AH AH resta) | `pastelli.py` |
| `annuncio/volantino` | dopo «Nuova partita» | tutto il volantino (vedi `docs/concept/annuncio.md`) | `annuncio.py` |

`pastelli.py --lingua xx --larghezza 1600 --uscita public/assets/img/disegni <nomi>` rifà i disegni con scritte da
tradurre (tabella `SCRITTE`); il resto del disegno resta identico a quello italiano, tratto per tratto (la scritta
italiana si «disegna a secco» per consumare gli stessi numeri a caso). Una scritta tradotta più lunga si rimpicciolisce
fino a stare nello spazio dell'italiana; una più corta si mette nel mezzo. Le lettere del bambino (`LETTERE`) sono le
maiuscole senza accenti, meno J, Q e X, più `! ? ' -` e le cifre: per altre lingue vanno aggiunte le lettere che
mancano (À È É Ì Ò Ù, Ä Ö Ü ß, Ñ, Ç…).

### Uguali in tutte le lingue

| Immagine | Scritte |
|---|---|
| `disegni/pastelli_marcopolo` | MARCO!, POLO! (il gioco si chiama così anche in inglese) |
| `fin_ricordo` («Il ricordo», finale B) | SPLASHLAND, NIGHT SPLASH, 14-8-97 |
| panorama e binocolo | SPLASHLAND, MAMA MARINA'S, MIRAMARE, NIGHT SPLASH ★ TONIGHT ★ |
| barca | adesivi SPLASHLAND; la batteria: VOLT e i numeri |
| biglietti di Robin | SPLASHLAND, 1 TICKET, Nº 040217 |
| foto del finale | la data della macchinetta, '97 7 26 |
| tana di Archie | HAPPY BIRTHDAY (era TANTI AUGURI: cambiato il 12 ottobre, scelta dell'utente) |
