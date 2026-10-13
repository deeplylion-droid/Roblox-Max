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
| `logo/logo`, `logo/logo_tremolio` (il logo del menu principale) | SPLASHLAND, «is closed!»: è il titolo del gioco, che non si traduce |

### Le tane: l'italiano che si leggeva (revisione del 12 ottobre)

Le tane sono render lunghi: niente versioni per lingua, le scritte diventano neutre o inglesi (regola 3). Le fa la
sessione delle grotte (`tools/render/tane.py`, `tools/render/disegni_tane.py`).

| Tana | Si leggeva | Diventa |
|---|---|---|
| Archie | lo striscione «TANTI AU…» | HAPPY BIRTHDAY |
| Gulpy | il manifesto «GELATI / ESTATE 1997» | ICE CREAM / SUMMER 1997 (e a sinistra FRIES / MAXI) |
| Gulpy | il menu sul bancone (la cosa da trovare): PATATINE, GELATO, PANINO, «TUTTO!» | MENU, HOT DOG, poi solo i disegnini coi prezzi, e «!!!» |
| Robin | il manifesto «…TTI SMARRITI» | LOST & FOUND |
| Robin | il fumetto del disegno da trovare, «VOGLIO TUTTO» | «!!!» |
| Hatch | il foglio della conta (la cosa da trovare) «DIECI!» | 10! (sotto, piccolo e illeggibile, «CHI C'È C'È») |
| Lampy | «BENVENUTA! / LUGLIO 2003» | WELCOME! / JULY 2003; il cartoncino della culla «3100 g – 7 / 2003» |
| Molly | — | la foto sulla sabbia, «6 / 1997» |

Tutte rifatte la notte del 12-13 ottobre e guardate come il giocatore (scelte approvate il 13 ottobre: le scritte
inglesi o neutre e i «!!!»). Il Diario (`LORE_TEXT` in `src/i18n.ts`) descrive ogni cosa da trovare com'è disegnata,
in ogni lingua. Restano, ma non si leggono nel gioco: il manifesto di Archie dice ancora «FESTA / MAGGIO 1999» nelle
immagini (nel sorgente è già «PARTY / MAY 1999»); la tana di Fangy non è stata rifatta (nel sorgente «EYES CLOSED!» e
«AUGUST»); nei disegni già renderizzati l'«IO» di Fangy e le iniziali italiane dei mesi di Archie, piccoli.

### Numeri e date neutri (decisione dell'utente del 13 ottobre)

- **Niente decimali nelle scritte dentro le immagini**: si leggono diversi in italiano (2,5) e in inglese (2.5). Nella
  tana di Molly il cartello è diventato «3 M – DEEP END» (era «2,5 m»), sul cartoncino della culla di Lampy «3100 g» (era
  «3,1 KG»). Per i grammi la «g» minuscola, che è anche il simbolo giusto: in Limelight, alla grandezza del cartoncino nel
  render, la «G» maiuscola si leggeva «C» («3100 C» sembrava una temperatura).
- **Le date col giorno oltre il 12**, così giorno·mese·anno non si confonde con mese·giorno·anno: sul pesce
  `sciarrano_scrivano` «13·11·2004» (era «3·11·2004», che un americano legge 11 marzo). Le altre date erano già sicure
  (14-16·8·1997, 21·6·2013, 10·10).

## Le lingue del gioco (13 ottobre)

Nove lingue: l'**italiano** (l'originale), l'**inglese** (adattamento approvato) e, dal 13 ottobre, **spagnolo, francese,
tedesco, portoghese** (del Brasile), **cinese** (semplificato), **giapponese** e **coreano** (scelta dell'utente del 12
ottobre sera; via libera del 13: «procediamo con le traduzioni»). Le sette lingue nuove sono **traduzioni automatiche**
(un traduttore per lingua, dall'italiano con l'inglese a fianco): prima dell'uscita le deve rileggere un madrelingua.
Ogni file lo dice in testa, e nel suo `_immagini.json` la voce `note` elenca i dubbi del traduttore (i nomi dei pesci
meno riusciti, le specie vere senza un nome sicuro nella lingua, le scelte da confermare).

- **Dove stanno**: `src/lingue/<lingua>.ts` ha tutti i testi della lingua (interfaccia, Diario, radio, Catalogo:
  nome, specie vera e descrizione dei cento pesci); `src/lingue/<lingua>_immagini.json` le scritte dentro le immagini
  (disegni a pastello, volantino), il glossario e le note. `src/i18n.ts` li raccoglie (`NUOVE`), `testiPesce` dà i
  testi di un pesce nella lingua; TypeScript controlla che ogni lingua abbia tutte le voci dell'italiano
  (`src/lingue/tipo.ts`), `tests/lingue.test.ts` il resto (le battute della radio agli stessi tempi, i segnaposto
  come `{RT}` e `{who}`, i nomi propri, i cento pesci coi nomi tutti diversi).
- **Il glossario** (le parole che tornano dappertutto):

| | la Madre | il Diario | il Catalogo | la quota | il telone | il secchio | le tane |
|---|---|---|---|---|---|---|---|
| es | la Madre | el Diario | el Catálogo | la cuota | la lona | el cubo | las guaridas |
| fr | la Mère | le Journal | le Catalogue | le quota | la bâche | le seau | les tanières |
| de | die Mutter | das Tagebuch | der Katalog | die Quote | die Plane | der Eimer | die Höhlen |
| pt | a Mãe | o Diário | o Catálogo | a cota | a lona | o balde | as tocas |
| zh | 母亲 | 日志 | 图鉴 | 配额 | 篷布 | 鱼桶 | 巢穴 |
| ja | 母さま | 日誌 | 図鑑 | ノルマ | シート | バケツ | 巣穴 |
| ko | 어머니 | 일지 | 도감 | 할당량 | 방수포 | 양동이 | 굴 |

- **La conta di Hatch** è quella del nascondino di ogni paese: «¡Quien no se haya escondido, tiempo ha tenido!»,
  «Prêt, pas prêt, j'arrive !», «Eckstein, alles muss versteckt sein!», «Lá vou eu!», «藏好了没？我来啦！», «もういいかい？»,
  «꼭꼭 숨어라, 머리카락 보일라!» (nella conta, nella sua morte e nel foglio della sua tana nel Diario).
- **Altre scelte**: in francese la notte extra è «Nuit bonus» («nuit extra» suonerebbe come «notte fantastica») e gli
  Extra «Bonus»; in tedesco «Buona pesca» è «Petri Heil», il saluto dei pescatori; in cinese il numero di pagina del
  Catalogo va da solo (`pageAbbr` vuoto). I nomi propri (Mama Marina, Splashland, i mostri, Soggy) restano come sono.
- **La voce della radio** (`src/engine/voice.ts`, 13 ottobre): la punteggiatura staccata con lo spazio, come in
  francese («Prêt ?»), non è più una sillaba; un nome latino attaccato a una particella coreana o giapponese
  («Gulpy는») si dice invece di restare muto.
- **La tastiera francese (AZERTY)** (13 ottobre, fra le rifiniture scelte dall'utente): i tasti che contano per dove
  stanno, sotto la mano sinistra (W A S D per voltarsi, Q ed E per la luce), si leggono per posizione
  (`src/app/tastiera.ts`): su una tastiera francese sono Z Q S D e A/E, come in tutti i giochi. Gli altri (F, C, B,
  Spazio, Tab) restano per la lettera, che su ogni tastiera latina sta lì. Nei testi quei tasti sono segnaposto
  (`{KeyW}`, `{KeyQ}`…: vanno lasciati come sono, come quelli del controller) e i suggerimenti dicono le lettere della
  tastiera di chi gioca: le chiede al browser (`navigator.keyboard`, che in Electron c'è) e le conferma ogni tasto
  premuto; senza notizie dicono quelle americane. Con una tastiera che non scrive in latino (russa, greca) valgono le
  lettere latine stampate sui tasti.

**Come funziona** (preparato la notte del 12-13 ottobre)
- **La lingua**: il pulsante della lingua nelle opzioni passa da una lingua all'altra (`LANGS`, ognuna col suo nome
  in `LANG_NAMES`: Español, Français, Deutsch, Português, 中文, 日本語, 한국어); al primo avvio è quella del sistema, se il
  gioco ce l'ha (pt-BR e pt-PT → pt, zh-CN → zh), se no l'inglese. La pagina dice la sua lingua (`<html lang>`).
- **I font**: Limelight e Source Serif 4 hanno tutti gli accenti di spagnolo, francese, tedesco e portoghese (manca
  solo la Ÿ, che il francese usa in qualche nome). Per cinese, giapponese e coreano `src/app/fonts_lingua.ts` aggiunge
  alle stesse famiglie, solo per i caratteri quadrati, il sottoinsieme di Noto Serif della lingua (il fratello di
  Source Serif 4). Gli a capo: il coreano fra le parole, cinese e giapponese con le regole strette (`styles.css`).
- **La voce della radio e la conta di Hatch**: in cinese, giapponese e coreano ogni carattere è una sillaba, con la
  vocale presa dall'hangul o dal sillabario; la punteggiatura larga fa le pause.
- **I disegni a pastello**: la mano del bambino scrive le lettere accentate (Á É Í Ó Ú Ñ Ü Ç À È Ê Ô Ã Õ Ä Ö…, ¡ ¿,
  la ß come SS) e J, Q, X; cinese, giapponese e coreano li prende dallo scheletro di Noto Sans e li ripassa a pastello
  con lo stesso tremolio.
- **Il volantino**: Luckiest Guy, Baloo 2 e Lilita One per le lingue latine; per cinese, giapponese e coreano altri
  font per lingua, salvati come sottoinsiemi coi soli caratteri dei testi (`docs/concept/annuncio.md`).

**Le immagini.** I quattro disegni con scritte da tradurre (piscina, tesoro, compleanno, sott'acqua) e il volantino
hanno la loro versione in ogni lingua (`TRADOTTI` in `src/app/disegni.ts`, `ANNUNCIO.langs` in `src/app/app.ts`); i
font dell'interfaccia per cinese, giapponese e coreano sono in `public/fonts/cjk-<lingua>.woff2` (Noto Serif SC, JP,
KR ridotti ai caratteri dei testi, 250-450 KB; licenza OFL in `public/fonts/OFL-NotoSerifCJK.txt`).

**I controlli** (13 ottobre): `scripts/lingue.mjs` apre in ogni lingua ogni schermata, il Catalogo pesce per pesce e
ogni riquadro dell'HUD della notte e dell'immersione con tutti i testi che ci finiscono dentro, alla finestra più
piccola che il gioco permette (960×540), allo Steam Deck (1280×800) e a 1920×1080, coi testi normali e «Molto
grande», con la tastiera e col controller: nessuna scritta esce dallo schermo o dal suo riquadro. Le immagini nuove
sono state guardate a piena risoluzione in ogni lingua.

## Per una lingua nuova

1. I testi: `src/lingue/<lingua>.ts` (il tipo `Traduzione` di `src/lingue/tipo.ts`: TypeScript dice cosa manca) e
   `src/lingue/<lingua>_immagini.json`; il codice in `Lang` e in `NUOVE` di `src/i18n.ts`, il nome in `LANG_NAMES`.
2. I disegni dell'alba: `pastelli.py --lingua <lingua> --larghezza 1600 --uscita public/assets/img/disegni piscina
   tesoro compleanno sottacqua` (le scritte le prende dal `_immagini.json`) e la lingua in `TRADOTTI` di
   `src/app/disegni.ts`.
3. Il volantino: `annuncio.py --controlla` (nessun carattere mancante; per cinese, giapponese e coreano, se i testi
   cambiano, prima `annuncio.py --sottoinsiemi <cartella coi font interi>`), poi
   `annuncio.py volantino --lingua <lingua> --scala 1.5 --webp --uscita public/assets/img/annuncio` (una lingua per
   volta: servono circa 6 GB) e la lingua in `ANNUNCIO.langs` di `src/app/app.ts`.
4. Solo per cinese, giapponese e coreano: `tools/.venv/bin/python tools/fonts/sottoinsieme_cjk.py <lingua>` (da rifare
   quando cambiano i testi) e il file in `CJK_FONTS` di `src/app/fonts_lingua.ts`.
5. `node scripts/lingue.mjs` (con `npm run dev`) e uno sguardo alle foto delle schermate e alle immagini nuove.
   Per altre scritture (cirillico, greco) servirebbero altri font per il volantino.

## Come è stato controllato

Il 12 ottobre sera tutte le immagini del gioco (notte, binocolo, barca, jumpscare, finali, catalogo e pesci, disegni,
volantino, tane e grotte, con le varianti senza nebbia, le pose e le toppe) sono state guardate una per una, schiarite
come nel motore e ritagliate a piena risoluzione dove c'era una scritta; quelle in italiano ricontrollate a 1920×1080
come le vede il giocatore. Quello che non è nelle tabelle sopra non ha scritte.
