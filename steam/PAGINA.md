# I testi della pagina Steam

**Approvati dall'utente il 14 ottobre** (proposta del 13 ottobre). Sono i testi da incollare su Steamworks (**Store
page admin**): la descrizione breve e quella lunga in italiano e in inglese, le lingue, i requisiti di sistema e una
bozza del questionario sui contenuti. Le immagini sono in `LEGGIMI.md`. La storia viene da `docs/LORE.md` e il gioco
da `docs/GDD.md`. Non c'è niente oltre quello che si scopre nelle prime notti: niente finali, niente Madre vista da
vicino.

Su Steam l'inglese è la lingua di base. Le altre lingue della pagina si aggiungono quando i loro testi sono pronti; per
ora solo italiano e inglese.

## Descrizione breve

Si vede accanto alla capsula, in alto a destra; massimo 300 caratteri.

**English** (241 caratteri)

> In 1997, three children vanished at Mama Marina's Splashland. Now you fish the dark bay behind the abandoned water
> park, and you must fill the bucket for the Mother by 6 AM while her children climb aboard. Each one wants something
> different.

**Italiano** (248 caratteri)

> Nel 1997 a Mama Marina's Splashland sparirono tre bambini. Ora peschi nella baia buia dietro il parco acquatico
> abbandonato, e devi riempire il secchio per la Madre entro le sei mentre i suoi figli salgono a bordo. Ognuno vuole
> qualcosa di diverso.

## Descrizione lunga («About this game»)

Su Steam si scrive col suo formato: `[h2]` per i titoli, `[list][*]…[/list]` per gli elenchi. Qui sotto c'è il testo;
la versione col formato di Steam si fa quando si carica.

### English

**The night shift starts at midnight.**

You sit in a small wooden boat in the middle of the bay, with a lamp, a rod and an empty bucket. Behind you, the slides
of Mama Marina's Splashland twist in the fog. Nobody has swum there since the summer of 1997.

Catch the quota before 6 AM. The Mother is hungry, and when the fishermen don't feed her, she takes another child.

Her children come up from the water to meet you. They still wear what they had at the park: a duck float, armbands, a
glowing toy from the gift shop. Each of them kept a habit from when they were little, and now that habit is a rule:

- feed Gulpy, or he eats you;
- keep your eyes on Molly, or she drags the boat under;
- hide under the tarp while Hatch counts;
- and more, night after night.

Every second you spend defending yourself is a second you're not fishing.

**Features**

- Six nights, then an Extra Night where you set every monster from 0 to 20.
- Eight monsters, each with their own rule. And the Mother.
- 100 undead fish to catch and collect in the Catalogue: skeletal, zombie, glitched, corrupted, bleeding.
- At dawn, put on the diving tanks and swim down into the monsters' dens. What you leave there decides how it ends.
- Binoculars to search the abandoned park. Some secrets can only be seen from the boat.
- A brighter lamp brings more fish. And more of them.
- Spatial sound: play with headphones.
- Full controller support, Steam Deck included.
- Interface and subtitles in 9 languages.

*Contains jump scares and flashing lights. An option reduces flashes and screen shake.*

### Italiano

**Il turno di notte comincia a mezzanotte.**

Sei seduto in una barchetta di legno in mezzo alla baia, con una lampara, una canna e un secchio vuoto. Alle tue
spalle gli scivoli di Mama Marina's Splashland si attorcigliano nella nebbia. Lì non fa il bagno nessuno dall'estate
del 1997.

Pesca la quota prima delle sei. La Madre ha fame, e quando i pescatori non la sfamano si prende un altro bambino.

I suoi figli salgono dall'acqua a cercarti. Hanno ancora addosso quello che avevano al parco: un salvagente a
paperella, i braccioli, un giocattolo luminoso del negozio. Ognuno ha tenuto un'abitudine di quando era piccolo, e
ora quell'abitudine è una regola:

- sfama Gulpy, o mangia te;
- non togliere gli occhi da Molly, o trascina giù la barca;
- nasconditi sotto il telone mentre Hatch conta;
- e altre ancora, notte dopo notte.

Ogni secondo passato a difenderti è un secondo in cui non peschi.

**Caratteristiche**

- Sei notti, poi una Notte extra in cui scegli ogni mostro da 0 a 20.
- Otto mostri, ognuno con la sua regola. E la Madre.
- 100 pesci non morti da prendere e raccogliere nel Catalogo: scheletrici, zombi, glitchati, corrotti, sanguinanti.
- All'alba indossi le bombole e scendi nelle tane dei mostri. Quello che ci lasci decide come finisce.
- Il binocolo per frugare nel parco abbandonato: certi segreti si vedono solo dalla barca.
- Una lampara più forte porta più pesci. E più di loro.
- Suono nello spazio: gioca con le cuffie.
- Si gioca tutto col controller, anche sullo Steam Deck.
- Interfaccia e sottotitoli in 9 lingue.

*Contiene jumpscare e luci lampeggianti. Un'opzione riduce lampi e scosse dello schermo.*

## Le lingue

Su Steam, per ogni lingua: interfaccia, audio completo, sottotitoli.

| Lingua su Steam | Interfaccia | Audio completo | Sottotitoli |
|---|---|---|---|
| English | sì | — | sì |
| Italian | sì | — | sì |
| Spanish - Spain | sì | — | sì |
| French | sì | — | sì |
| German | sì | — | sì |
| Portuguese - Brazil | sì | — | sì |
| Simplified Chinese | sì | — | sì |
| Japanese | sì | — | sì |
| Korean | sì | — | sì |

«Audio completo» no in nessuna lingua: i mostri non parlano e la radio ha i sottotitoli. Le sette lingue nuove sono
traduzioni automatiche e prima di metterle sulla pagina le deve rileggere un madrelingua (`docs/LOCALIZZAZIONE.md`).
Per lo spagnolo la traduzione non è di un paese preciso: «Spain» è il più vicino.

## Requisiti di sistema

**Sono stime da verificare** su qualche PC vero, soprattutto quello minimo. Il gioco è un'app Electron con WebGL 2;
la cartella del gioco per Windows occupa circa mezzo gigabyte.

| | Minimi | Consigliati |
|---|---|---|
| Sistema | Windows 10 a 64 bit | Windows 10 o 11 a 64 bit |
| Processore | dual core a 2 GHz | quad core a 3 GHz |
| Memoria | 4 GB di RAM | 8 GB di RAM |
| Scheda video | con WebGL 2 (Intel UHD 620 o simile) | NVIDIA GTX 1050 / AMD RX 560 o meglio |
| Spazio | 1 GB | 1 GB |
| Note | cuffie consigliate | cuffie consigliate |

Linux / SteamOS: Ubuntu 22.04 o più nuovo (AppImage), stessi numeri. Lo Steam Deck va provato su un Deck vero prima
di chiedere la verifica di Valve: finora è stato provato solo a 1280×800 nel browser.

## Il questionario sui contenuti (bozza)

Steam lo chiede prima di pubblicare la pagina (**Content Survey**). Le mie risposte:

- **Nudità o contenuti sessuali**: no.
- **Violenza o sangue frequenti**: no. I jumpscare mostrano i mostri che ti prendono, ma non c'è sangue né corpi.
  Il sangue c'è solo sui pesci «sanguinanti» del Catalogo, stilizzati.
- **Contenuti per adulti in generale**: sì. Testo proposto: «Horror with jump scares and disturbing themes: children
  who went missing at a water park have become the monsters that hunt the player. No gore.»

Più avanti, all'uscita, Steam chiede anche la classificazione IARC (un altro questionario), che dà i bollini PEGI/ESRB.

## I tag (proposta)

Steam lascia sceglierne fino a 20, nell'ordine di importanza: Horror, Psychological Horror, Survival Horror, Jump
Scare, Fishing, First-Person, Atmospheric, Dark, Creepy, Singleplayer, Indie, Strategy, Point & Click, Short,
Controller, Collectathon, Multiple Endings, Underwater, Mystery, Cute.
