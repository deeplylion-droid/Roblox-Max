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
| `disegni/pastelli_sottacqua` | alba della notte 4, Diario | AIUTO! → HELP!, AH AH AH → HA HA HA (in inglese «AH AH AH» sembra un grido) | `pastelli.py` |
| `annuncio/volantino` | dopo «Nuova partita» | tutto il volantino (vedi `docs/concept/annuncio.md`) | `annuncio.py` |

`pastelli.py --lingua xx --larghezza 1600 --uscita public/assets/img/disegni <nomi>` rifà i disegni con scritte da
tradurre (tabella `SCRITTE`); il resto del disegno resta identico a quello italiano, tratto per tratto (la scritta
italiana si «disegna a secco» per consumare gli stessi numeri a caso). Una scritta tradotta più lunga si rimpicciolisce
fino a stare nello spazio dell'italiana; una più corta si mette nel mezzo (in cinese, giapponese e coreano può anche
crescere un po', che i tratti fitti si leggano). Nelle nuvolette, una traduzione molto più lunga (AIUTO! → AU SECOURS!)
allarga la nuvoletta dalla parte opposta a chi parla, fino a una volta e mezza (meno dove accanto c'è poco posto:
`allarga` nella chiamata), invece di diventare minuscola. Le lettere del bambino (`LETTERE`): tutte le maiuscole,
quelle accentate dell'Europa occidentale (gli accenti grandi e staccati, che nelle scritte piccole non si impastino
con la lettera), `! ? ¡ ¿ ' - . , :` e le cifre (il trattino fra due lettere, TROUVE-MOI, è largo come una lettera;
quello delle date resta stretto); il resto dallo scheletro di un font (vedi sotto).

### Uguali in tutte le lingue

| Immagine | Scritte |
|---|---|
| `disegni/pastelli_marcopolo` | MARCO!, POLO! (il gioco si chiama così anche in inglese) |
| `fin_ricordo` («Il ricordo», finale B) | SPLASHLAND (con la S girata), NIGHT SPLASH, 14-8-97 |
| `bino_ingresso`, panorama | MAMA MARINA'S, SPLASHLAND (lettere spente), lo striscione NIGHT SPLASH ★ TONIGHT ★ |
| `bino_albergo`, panorama | MIRAMARE (con lettere spente) |
| `bino_relitto`, barca, `catalogo/sfondo` | tacche contate a cinque (58, 23, 15) |
| barca | l'adesivo SPLASHLAND a prua; la batteria: VOLT e i numeri |
| biglietti di Robin (jumpscare, toppe) | SPLASHLAND, 1 TICKET, Nº 040217 |
| foto del finale | la data della macchinetta, '97 7 26 |
| pesci del catalogo | `alaccia_registrata_sopra`: 14.08.1997; `sciarrano_scrivano`: le date giorno·mese·anno (vedi sotto) |
| `annuncio/volantino` | lo slogan «Mama Marina loves her little ones!» resta in inglese anche nella versione italiana, come il nome del parco |
| tane | SNACK SHACK, DEEP END, SPLASHLAND, i numeri di Hatch, POLO!, 2008; Archie: HAPPY BIRTHDAY (era TANTI AUGURI, scelta dell'utente del 12 ottobre) |
| `favicon.png` | la S al neon |

### Le tane: l'italiano che si leggeva (revisione del 12 ottobre)

Le tane sono render lunghi: niente versioni per lingua, le scritte diventano neutre o inglesi (regola 3). Le fa la
sessione delle grotte (`tools/render/tane.py`, `tools/render/disegni_tane.py`).

| Tana | Si leggeva | Diventa |
|---|---|---|
| Archie | lo striscione «TANTI AU…» | HAPPY BIRTHDAY |
| Gulpy | il manifesto «GELATI / ESTATE 1997» | ICE CREAM / SUMMER 1997 |
| Robin | il manifesto «…TTI SMARRITI» | LOST & FOUND |
| Hatch | il foglio della conta (la cosa da trovare) «DIECI!» | 10! (il Diario cita la stessa scritta, in ogni lingua) |

Nel gioco non si leggono, ma nel sorgente diventano neutre per i render futuri: il menu di Gulpy (PATATINE, GELATO,
PANINO, TUTTO!), «si gioca a occhi chiusi» di Fangy, «FESTA / MAGGIO 1999» di Archie, «BENVENUTA! / LUGLIO 2003» di
Lampy, «CHI C'È C'È» di Hatch. Le cose da trovare hanno il loro testo nel Diario (`LORE_TEXT` in `src/i18n.ts`), in
ogni lingua.

### Da decidere più avanti

- **Le date giorno·mese·anno**: sul pesce `sciarrano_scrivano` c'è «3·11·2004», che un americano legge 11 marzo. Per
  le scritte neutre meglio date che non si confondono (giorno oltre il 12) o l'anno da solo.
- **I numeri coi decimali**: nella tana di Molly «2,5 m» e sul cartoncino della culla di Lampy «3,1 KG» hanno la
  virgola italiana (in inglese 2.5 m, 3.1 kg). Si leggono, ma un inglese ci inciampa: o numeri senza decimali, o va bene
  così. Piccolo.

## Per una lingua nuova

Le lingue a cui il gioco potrebbe arrivare (scelta dell'utente del 12 ottobre sera): **spagnolo, francese, tedesco,
portoghese, cinese, giapponese, coreano**. La notte del 12-13 ottobre il gioco è stato preparato per tutte; mancano solo i
testi tradotti, che si fanno con l'ok dell'utente (e un madrelingua che li controlli).

**Già pronto**
- **Interfaccia**: il pulsante della lingua nelle opzioni passa da una lingua all'altra di quelle che hanno i testi
  (`LANGS` e `LANG_NAMES` in `src/i18n.ts`, ognuna col suo nome: Español, Français, Deutsch, Português, 中文, 日本語, 한국어);
  al primo avvio la lingua è quella del sistema, se il gioco ce l'ha (pt-BR → pt, zh-CN → zh), se no l'inglese; una
  lingua salvata che il gioco non ha più torna a quella del sistema. La pagina dice la sua lingua (`<html lang>`).
- **Font dell'interfaccia**: Limelight e Source Serif 4 hanno già tutti gli accenti di spagnolo, francese, tedesco e
  portoghese (manca solo la Ÿ, che il francese usa in qualche nome). Per cinese, giapponese e coreano
  `src/app/fonts_lingua.ts` aggiunge alle stesse famiglie, solo per i caratteri quadrati, il sottoinsieme di Noto Serif
  della lingua (il fratello di Source Serif 4) fatto da `tools/fonts/sottoinsieme_cjk.py`: qualche centinaio di KB
  invece di 10-25 MB. Gli a capo: il coreano fra le parole, cinese e giapponese con le regole strette (`styles.css`).
- **La voce della radio e la conta di Hatch** (`src/engine/voice.ts`): in cinese, giapponese e coreano ogni carattere è
  una sillaba, con la vocale presa dall'hangul o dal sillabario (i caratteri cinesi ne prendono una sempre uguale); la
  punteggiatura larga fa le pause.
- **I disegni a pastello**: la mano del bambino scrive le lettere accentate (Á É Í Ó Ú Ñ Ü Ç À È Ê Ô Ã Õ Ä Ö…, ¡ ¿, la ß
  come SS) e J, Q, X; cinese, giapponese e coreano li prende dallo scheletro di Noto Sans e li ripassa a pastello con lo
  stesso tremolio. Le prove in tutte le sette lingue sono in `docs/concept/lingue/pastelli_<lingua>_prova.jpg`, coi testi
  di `tools/render/pastelli_prova_lingue.py` (PROVE, da far controllare: non vanno nel gioco).
- **Il volantino**: testi di prova per tutte e sette (`prova=True` in `TESTI_V`: i render lo scrivono in rosso), coi
  render in `docs/concept/lingue/annuncio_volantino_<lingua>.jpg`. I font: Luckiest Guy, Baloo 2 e Lilita One per le
  lingue latine; per cinese, giapponese e coreano altri font per lingua (chiave `font`), salvati come sottoinsiemi coi
  soli caratteri dei testi (`docs/concept/annuncio.md`). Gocce e colature stanno fuori dalle scritte, in ogni lingua.
  Per altre scritture (cirillico, greco) servirebbero altri font.
- **Il portoghese** è quello del Brasile (i testi di prova lo sono, e `detectLang` porta pt-BR e pt-PT a `pt`).

**I passi per una lingua (per esempio lo spagnolo, `es`)**
1. I testi: `es` nel tipo `Lang` e i suoi testi in `STRINGS`, `LORE_TEXT` e nelle `RADIO_NIGHT…` di `src/i18n.ts`
   (TypeScript dice cosa manca), poi il suo nome è già in `LANG_NAMES`.
2. I disegni dell'alba: le sue righe in `SCRITTE` di `tools/render/pastelli.py`, poi
   `pastelli.py --lingua es --larghezza 1600 --uscita public/assets/img/disegni piscina tesoro compleanno sottacqua`
   e `es` in `TRADOTTI` di `src/app/disegni.ts`.
3. Il volantino: le sue righe in `TESTI_V` di `tools/render/annuncio.py` (togliendo `prova=True` quando un madrelingua
   le ha controllate), `annuncio.py --controlla` (nessun carattere mancante; per cinese, giapponese e coreano, se i
   testi cambiano, prima `annuncio.py --sottoinsiemi <cartella coi font interi>`), poi
   `annuncio.py volantino --lingua es --scala 1.5 --webp --uscita public/assets/img/annuncio` (una lingua per volta:
   servono circa 6 GB) e `es` in `ANNUNCIO.langs` di `src/app/app.ts`.
4. Solo per cinese, giapponese e coreano: `tools/.venv/bin/python tools/fonts/sottoinsieme_cjk.py zh` (da rifare quando
   cambiano i testi) e `zh: 'fonts/cjk-zh.woff2'` in `CJK_FONTS` di `src/app/fonts_lingua.ts`.
5. Poi si guardano le immagini nuove e le schermate come le vede il giocatore (regola 4): che i testi stiano nei loro
   spazi anche con la dimensione dei testi al massimo.

## Come è stato controllato

Il 12 ottobre sera tutte le immagini del gioco (notte, binocolo, barca, jumpscare, finali, catalogo e pesci, disegni,
volantino, tane e grotte, con le varianti senza nebbia, le pose e le toppe) sono state guardate una per una, schiarite
come nel motore e ritagliate a piena risoluzione dove c'era una scritta; quelle in italiano ricontrollate a 1920×1080
come le vede il giocatore. Quello che non è nelle tabelle sopra non ha scritte.
