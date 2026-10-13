/** Testi del gioco in italiano e inglese. */

export type Lang = 'it' | 'en';

/** «a» o «ad» davanti a un nome: la d eufonica davanti alla stessa vocale (accanto ad Archie). */
const ad = (who: string): string => (/^a/i.test(who) ? 'ad' : 'a');

const IT = {
  title: 'SPLASHLAND IS CLOSED!',
  newGame: 'Nuova partita',
  continue: 'Continua',
  // la conferma di «Nuova partita» con una partita in corso (approvata dall'utente il 13 ottobre, anche l'inglese)
  newGameConfirm: {
    title: 'Nuova partita?',
    text: 'La partita in corso finisce qui: si riparte dalla prima notte, senza le albe e i pesci lasciati nelle tane. Le notti sbloccate, il Diario e il Catalogo restano.',
    yes: 'Ricomincia da capo',
  },
  extras: 'Extra',
  options: 'Opzioni',
  quit: 'Esci',
  back: 'Indietro',
  warningTitle: 'Attenzione',
  warning: 'Questo gioco contiene jumpscare, suoni improvvisi e luci lampeggianti. Si gioca meglio al buio, con le cuffie.',
  pressAny: 'Premi un tasto o fai clic',
  night: 'Notte',
  quota: 'Quota',
  fish: 'pesci',
  am: '',
  lampNames: ['spenta', 'bassa', 'alta'],
  lamp: 'Luce',
  hints: {
    cast: 'Clic sulla canna o Spazio per lanciare',
    hook: 'Ha abboccato! Clic o Spazio',
    reel: 'Tieni premuto per recuperare, molla quando strattona',
    throw: 'F o clic sul secchio: lancia un pesce',
    hide: 'C o clic sul telone: nasconditi',
    unhide: 'C per uscire dal telone',
    turn: 'S per voltarti',
    // notte 2: approvato il 10 ottobre
    robin: 'Robin: luce al massimo (E)',
    // notte 3 (approvati l'11 ottobre)
    archie: 'Archie prende fiato: spegni la luce (Q)',
    archieWait: 'Resta al buio finché non va giù',
    // notte 4 (approvato l'11 ottobre)
    lampy: 'Tre colpi uguali: è Lampy, non ferrare',
    // notte 5 (approvato l'11 ottobre)
    fangy: 'Fangy ascolta: niente rumori',
    // notte 6 (approvato l'11 ottobre: «immobilità totale»)
    mother: 'Non muoverti',
    // il Foxy (11 ottobre sera, DA APPROVARE)
    foxy: 'Col binocolo (B): non perderlo di vista',
    foxyGone: 'Il posto è vuoto',
  },
  denied: {
    noFish: 'Il secchio è vuoto.',
    noTarget: 'Non c’è nessuno da sfamare.',
    busy: 'Non adesso.',
    notFacing: 'Devi guardare da quella parte.',
    // notte 2: approvato il 10 ottobre
    dark: 'Batteria morta.',
    // notte 3 (approvato l'11 ottobre): il vetro della luce è esploso
    broken: 'Il vetro è rotto.',
  },
  caught: 'Hai preso',
  newEntry: 'Nuova voce nel Catalogo',
  loreFound: 'Hai ripescato qualcosa',
  lineSnap: 'Il filo si è spezzato.',
  escaped: 'Il pesce è scappato.',
  baitStolen: 'Ti hanno mangiato l’esca.',
  sixAm: '6:00',
  survived: 'Notte superata',
  quotaMet: 'Quota raggiunta',
  // il finale A della notte 6 (approvato l'11 ottobre): la scritta sotto i risultati
  finaleA: 'Ce l’hai fatta. Per quest’anno.',
  // i finali segreti della notte 6 (le frasi sono quelle approvate l'11 ottobre in docs/NOTTI_E_MOSTRI.md, «I finali»;
  // l'inglese è DA APPROVARE): la scritta alla fine della cinematica e sotto i risultati
  finaleTuoi: 'Non sei tornato da solo.',
  finaleNessuno: 'Non hai mai dato niente ai suoi piccoli. Adesso sei uno di loro.',
  // i titoli di coda dopo i finali della notte 6: una riga sola (scelta dell'utente del 12 ottobre sera)
  creditsTitle: 'SPLASHLAND IS CLOSED!',
  credits: [['Un gioco di', 'Ettore']] as [string, string][],
  creditsEnd: 'Grazie per aver giocato.',
  creditsSkip: 'Esc per saltare',
  quotaMissed: 'Quota mancata',
  deathTitle: 'Game over',
  deaths: {
    gulpy: 'Gulpy aveva fame. Il secchio era vuoto.',
    molly: 'Molly voleva solo che la guardassi.',
    hatch: '«Chi c’è c’è, chi non c’è non c’è.» Ti ha trovato.',
    // notte 2: approvati il 10 ottobre (accorciati e più criptici, come chiesto)
    robin: 'Robin ha svuotato il secchio. Poi te.',
    // notte 3 (approvata l'11 ottobre): da bambino spegneva le candeline degli altri alle feste
    archie: 'Archie ha spento la tua candelina.',
    // notte 4 (approvata l'11 ottobre): da bambina in piscina tirava giù gli altri per le gambe, per scherzo
    lampy: 'Lampy ti ha tirato giù, per scherzo.',
    // notte 5 (approvata l'11 ottobre): giocava a Marco Polo a occhi chiusi e vinceva sempre
    fangy: '«Marco.» Hai risposto.',
    // il Foxy (11 ottobre sera, DA APPROVARE): faceva lo spettacolo di Mama Marina, che finiva con un abbraccio
    foxy: 'Lo spettacolo finiva sempre con un abbraccio.',
    mother: 'Alle sei il secchio non era pieno. Stanotte la Madre si prenderà un altro bambino.',
    // notte 2 (approvato il 10 ottobre): la batteria è morta e la ninna nanna è finita prima delle sei
    lullaby: 'La canzone è finita prima dell’alba.',
    // notte 6 (la frase proposta e approvata l'11 ottobre): ti sei mosso mentre la Madre passava sotto la barca
    moved: 'Mama Marina ama i suoi piccoli. Adesso anche te.',
  },
  // notte 7, la notte extra coi livelli (DA APPROVARE: tutti i testi qui sotto)
  extraNight: 'Notte extra',
  extraHelp: 'Scegli chi viene stanotte. 0: non viene. 20: feroce.',
  extraStart: 'Salpa',
  extraLocked: 'Finisci tutte le notti per sbloccarla.',
  extraPresets: { all0: 'Tutti a 0', all5: 'Tutti a 5', all10: 'Tutti a 10', all20: 'Tutti a 20', first3: 'I primi tre' },
  /** la regola di ogni mostro in due parole, sotto il nome */
  // la regola di Soggy (il Foxy) nella notte extra: DA APPROVARE (12 ottobre)
  extraRules: { gulpy: 'sfamalo', molly: 'guardala', hatch: 'nasconditi', robin: 'luce in faccia', archie: 'spegni la luce', lampy: 'non ferrare', fangy: 'stai zitto', mother: 'non muoverti', foxy: 'non perderlo di vista' },
  extraMother: 'La Madre',
  extraLevelNames: ['non viene', 'calmo', 'come la sua notte', 'svelto', 'feroce'],
  retry: 'Riprova',
  nextNight: 'Notte successiva',
  quality: 'Qualità grafica',
  wishlist: 'Aggiungi alla lista dei desideri',
  qualityLevels: ['Alta', 'Media', 'Bassa'],
  textSize: 'Dimensione dei testi',
  textSizes: ['Normale', 'Grande', 'Molto grande'],
  menu: 'Menu principale',
  demoEnd: 'Fine della demo. Le altre notti arrivano presto.',
  // dopo la sesta notte, finché non ci sono i titoli di coda (DA APPROVARE)
  extraOpened: 'Si è aperta la notte extra.',
  optionsTitle: 'Opzioni',
  volMaster: 'Volume generale',
  volMusic: 'Musica',
  volSfx: 'Effetti',
  language: 'Lingua',
  brightness: 'Luminosità',
  fullscreen: 'Schermo intero',
  subtitles: 'Sottotitoli',
  captionsOption: 'Didascalie',
  reduceFlash: 'Riduci lampi e scosse',
  fogOption: 'Nebbia',
  // prova dell'utente del 12 ottobre: i suggerimenti della pesca solo nella prima notte, se no con questa opzione
  tutorialOption: 'Tutorial sempre attivo',
  sensitivity: 'Sensibilità della rotazione',
  paused: 'Pausa',
  resume: 'Riprendi',
  restartNight: 'Ricomincia la notte',
  radioName: 'Radio · canale 16',
  labels: { rod: 'Canna', bucket: 'Secchio', tarp: 'Telone', lamp: 'Luce', sonar: 'Sonar' },
  look: 'Bordi dello schermo per guardarti intorno, W A S D per voltarti di scatto',
  sonarHint: 'Tab: sonar',
  lampHint: 'Q/E o rotella: luce',
  turnBar: 'VOLTATI',
  intro: { quota: 'Quota', fishUnit: 'pesci', time: '00:00' },
  results: { caught: 'Pesci pescati', fed: 'Dati a Gulpy', lore: 'Oggetti ripescati', time: 'Ora', spare: 'Oltre la quota' },
  // Le immersioni all'alba (docs/IMMERSIONI.md): approvati l'11 ottobre sera
  dive: {
    descend: 'Scendi con le bombole',
    loading: 'Ti infili le bombole…',
    ascend: 'Risali',
    hint: 'Guardati attorno. Clicca un passaggio per nuotarci.',
    // find: DA APPROVARE (12 ottobre), il punto della cosa da trovare nelle tane
    links: { cave: 'La grotta', back: 'Indietro', toCave: 'Torna alla grotta', ascend: 'Risali lungo la cima', find: 'Guarda' } as Record<string, string>,
    notes: { mother: 'Dal fondo, nel buio, respira qualcosa di enorme.' } as Record<string, string>,
    emptyDen: 'La tana è vuota. Chi ci dorme è già in giro.',
    blocked: 'Di là non si passa. Torni indietro.',
    airOut: 'Aria finita: risali.',
    offer: (who: string) => `Lasci il pesce accanto ${ad(who)} ${who}?`,
    offerYes: 'Lascia il pesce',
    offerNo: 'No',
    offered: (who: string) => `Il pesce resta accanto ${ad(who)} ${who}. Stanotte dormirà.`,
    noFish: 'Non hai pesci da lasciare: alle sei non ne avanzava nessuno.',
    alreadyFed: 'Il pesce l’hai già lasciato.',
    // DA APPROVARE (12 ottobre): la didascalia quando prendi la cosa da trovare
    found: (what: string) => `Nel Diario: ${what}.`,
  },
  journalTitle: 'Diario',
  journalEmpty: 'Non hai ancora ripescato niente. Il mare restituisce le cose solo a chi pesca.',
  journalLocked: '???',
  // i disegni a pastelli dell'alba (approvati il 12 ottobre)
  /** le virgolette della lingua (attorno al nome di un disegno) */
  quotes: ['«', '»'] as [string, string],
  drawings: {
    found: 'Sul banco, bagnato, c’è un disegno.',
    title: 'Disegni',
    locked: 'Non l’hai ancora trovato.',
    names: { piscina: 'La piscina', tesoro: 'Il mio tesoro', compleanno: 'Tanti auguri', sottacqua: 'Sott’acqua', marcopolo: 'Marco Polo' } as Record<string, string>,
  },
  catalogTitle: 'Catalogo',
  catalogHint: 'Le specie che non hai ancora preso restano sagome.',
  bookIndex: 'Indice',
  bookFound: 'Specie trovate',
  bookOf: 'su',
  bookPick: 'Scegli un pesce sulla pagina accanto.',
  bookNone: 'Di questa famiglia non hai ancora preso niente.',
  bookClose: 'Chiudi il libro',
  bookTurn: 'frecce o angoli per sfogliare',
  pageAbbr: 'pag.',
  bookWeight: 'Peso',
  bookPull: 'Al recupero',
  bookWhen: 'Abbocca',
  pull: {
    darts: 'strattoni brevi e leggeri',
    dead: 'fa il morto, poi strappa di colpo',
    leaps: 'salta e scuote la testa',
    glitch: 'la tensione salta a caso',
    heavy: 'tira giù, pesante e costante',
    bottom: 'si pianta sul fondo',
    frenzy: 'strattoni continui e violenti',
  },
  when: {
    always: 'sempre',
    night: 'dalla notte {n}',
    dark: 'a luce spenta',
    bright: 'a luce al massimo',
    from: 'dalle {h}',
    near: 'con {who} nei paraggi',
    nearAny: 'con una creatura nei paraggi',
  },
  familyPlural: { skeletal: 'Scheletrici', zombie: 'Zombi', glitch: 'Glitchati', corrupt: 'Corrotti', bleeding: 'Sanguinanti' },
  familyText: {
    skeletal: 'Carne mancante, lisca e cranio in vista.',
    zombie: 'Marci, occhi lattiginosi, pinne strappate, punti di sutura.',
    glitch: 'Fette del corpo sfalsate, colori separati, pixel.',
    corrupt: 'Occhi in più, bocche sbagliate, escrescenze, melma nera.',
    bleeding: 'Ferite, denti sporchi, colature.',
  },
  families: { skeletal: 'Scheletrico', zombie: 'Zombi', glitch: 'Glitchato', corrupt: 'Corrotto', bleeding: 'Sanguinante' },
  rarities: { common: 'comune', uncommon: 'non comune', rare: 'raro', legendary: 'leggendario' },
  newSpecies: 'Nuova specie',
  record: 'Record',
  timesCaught: 'Presi',
  inspiredBy: 'Dalla specie',
  unknownFish: '???',
  sonarClose: 'Tab o clic per chiudere',
  tapToClose: 'clic per chiudere',
  on: 'Sì',
  off: 'No',
  captions: {
    bowGurgle: 'gorgoglio a prua',
    bowClimb: 'qualcosa sale a prua',
    bowDemand: 'Gulpy ha fame',
    bowEat: 'Gulpy mastica',
    bowLeave: 'tonfo in acqua a prua',
    knock: 'toc toc sullo scafo',
    // il falso allarme (più paura, 12 ottobre): DA APPROVARE
    falseSplash: 'un tonfo in acqua, dietro di te',
    peek: 'Molly si affaccia',
    giggle: 'risatina',
    whine: 'Molly piagnucola',
    tantrum: 'Molly fa i capricci',
    calm: 'Molly si calma',
    mollyLeave: 'Molly scivola in acqua',
    hatchBoard: 'qualcosa sale a poppa',
    hatchStep: 'passi bagnati',
    hatchSniff: 'annusa',
    hatchLeave: 'tonfo in acqua a poppa',
    bell: 'la campana del paese',
    left: 'sinistra',
    right: 'destra',
    // notte 2: approvati il 10 ottobre (accorciati e più criptici, come chiesto)
    robinClimb: 'zampette sul bordo',
    robinRattle: 'il secchio tintinna',
    robinSteal: 'un pesce in meno',
    robinScared: 'fuga in acqua',
    lampSick: 'la luce sfrigola',
    lampDead: 'buio',
    lullaby: 'un carillon, dal fondo',
    // notte 3 (approvate l'11 ottobre)
    archieRise: 'qualcosa sale dall’acqua, a prua',
    archieInhale: 'un risucchio lungo',
    archieWait: 'aspetta al buio',
    archieDive: 'si rituffa',
    archieBlow: 'la luce esplode',
    // notte 4 (approvate l'11 ottobre)
    lampyBeat: 'il campanellino, a tempo',
    lampyGiggle: 'una risatina sott’acqua',
    lampySurface: 'qualcosa affiora sulla lenza',
    lampyLet: 'molla la lenza',
    lampyClimb: 'risale la lenza',
    // notte 5 (approvate l'11 ottobre)
    fangyApproach: 'lucine sott’acqua, si avvicinano',
    fangyRise: 'qualcosa sale accanto alla barca, dietro di te',
    fangySnap: 'si volta di scatto',
    fangyLeave: 'torna giù',
    // notte 6 (DA APPROVARE)
    motherCall: 'un richiamo enorme, dal fondo',
    motherApproach: 'tornano giù tutti; il mare si ferma',
    motherLullaby: 'una ninna nanna, sotto la barca',
    motherPass: 'qualcosa di enorme passa sotto la barca',
    motherLeave: 'si allontana',
    // il Foxy (11 ottobre sera, DA APPROVARE)
    foxyLean: 'laggiù, qualcosa si sporge',
    foxyLeave: 'qualcosa corre sull’acqua',
  },
  hatchCount: ['Uno…', 'Due…', 'Tre…', 'Quattro…', 'Cinque…', 'Sei…', 'Sette…', 'Otto…', 'Nove…', 'Dieci!'],
  hatchReady: 'Chi c’è c’è, chi non c’è non c’è!',
  hatchName: 'Hatch',
  kg: 'kg',
  // i comandi col controller (12 ottobre, DA APPROVARE: tutti i testi qui sotto). {A}, {RT}… diventano i tasti del
  // controller in uso (A o ✕, RT o R2…: src/app/pad.ts)
  pad: {
    pressAny: 'Premi un tasto',
    hints: {
      cast: '{RT} per lanciare',
      hook: 'Ha abboccato! {RT}',
      reel: 'Tieni premuto {RT} per recuperare, molla quando strattona',
      throw: '{X}: lancia un pesce',
      hide: '{A}: nasconditi sotto il telone',
      unhide: '{A} per uscire dal telone',
      robin: 'Robin: luce al massimo ({RB})',
      archie: 'Archie prende fiato: spegni la luce ({LB})',
      foxy: 'Col binocolo ({LT}): non perderlo di vista',
    } as Partial<Record<string, string>>,
    look: 'Stick destro per guardarti intorno, croce per voltarti di scatto',
    sonarClose: '{Y} o {B} per chiudere',
    bookTurn: '{LB} {RB} per sfogliare',
    diveHint: 'Guardati attorno con lo stick. {A} su un passaggio per nuotarci.',
    select: 'Scegli',
  },
};

const EN: typeof IT = {
  title: 'SPLASHLAND IS CLOSED!',
  newGame: 'New game',
  continue: 'Continue',
  newGameConfirm: {
    title: 'New game?',
    text: 'The game in progress ends here: you start again from the first night, without your dawns and the fish left in the dens. Unlocked nights, the Journal and the Catalogue stay.',
    yes: 'Start over',
  },
  extras: 'Extras',
  options: 'Options',
  quit: 'Quit',
  back: 'Back',
  warningTitle: 'Warning',
  warning: 'This game contains jumpscares, sudden loud sounds and flashing lights. Best played in the dark, with headphones.',
  pressAny: 'Press any key or click',
  night: 'Night',
  quota: 'Quota',
  fish: 'fish',
  am: 'AM',
  lampNames: ['off', 'low', 'high'],
  lamp: 'Light',
  hints: {
    cast: 'Click the rod or press Space to cast',
    hook: 'Bite! Click or Space',
    reel: 'Hold to reel in, let go when it pulls',
    throw: 'F or click the bucket: throw a fish',
    hide: 'C or click the tarp: hide',
    unhide: 'C to come out from under the tarp',
    turn: 'S to turn around',
    robin: 'Robin: light on full (E)',
    archie: 'Archie is drawing breath: turn off the light (Q)',
    archieWait: 'Stay in the dark until he goes under',
    lampy: 'Three even rings: it’s Lampy, don’t strike',
    fangy: 'Fangy is listening: not a sound',
    mother: 'Don’t move',
    foxy: 'With the binoculars (B): don’t lose sight of him',
    foxyGone: 'The place is empty',
  },
  denied: {
    noFish: 'The bucket is empty.',
    noTarget: 'Nobody to feed.',
    busy: 'Not now.',
    notFacing: 'You have to look that way.',
    dark: 'Battery dead.',
    broken: 'The glass is broken.',
  },
  caught: 'You caught',
  newEntry: 'New Catalogue entry',
  loreFound: 'You fished something up',
  lineSnap: 'The line snapped.',
  escaped: 'The fish got away.',
  baitStolen: 'Something ate your bait.',
  sixAm: '6:00 AM',
  survived: 'Night survived',
  quotaMet: 'Quota met',
  finaleA: 'You made it. For this year.',
  finaleTuoi: "You didn't come back alone.",
  finaleNessuno: 'You never gave her little ones anything. Now you are one of them.',
  creditsTitle: 'SPLASHLAND IS CLOSED!',
  credits: [['A game by', 'Ettore']] as [string, string][],
  creditsEnd: 'Thank you for playing.',
  creditsSkip: 'Esc to skip',
  quotaMissed: 'Quota missed',
  deathTitle: 'Game over',
  deaths: {
    gulpy: 'Gulpy was hungry. The bucket was empty.',
    molly: 'Molly only wanted you to watch her.',
    hatch: '"Ready or not, here I come." He found you.',
    robin: 'Robin emptied the bucket. Then you.',
    archie: 'Archie blew out your candle.',
    lampy: 'Lampy pulled you under. Just for fun.',
    fangy: '"Marco." You answered.',
    foxy: 'The show always ended with a hug.',
    mother: 'At six the bucket wasn’t full. Tonight the Mother will take another child.',
    lullaby: 'The song ended before dawn.',
    moved: 'Mama Marina loves her little ones. Now you too.',
  },
  // night 7, the extra night with levels (TO BE APPROVED: all the texts below)
  extraNight: 'Extra night',
  extraHelp: 'Choose who comes tonight. 0: stays away. 20: ferocious.',
  extraStart: 'Cast off',
  extraLocked: 'Finish every night to unlock it.',
  extraPresets: { all0: 'All at 0', all5: 'All at 5', all10: 'All at 10', all20: 'All at 20', first3: 'The first three' },
  extraRules: { gulpy: 'feed him', molly: 'watch her', hatch: 'hide', robin: 'light in his face', archie: 'light off', lampy: "don't strike", fangy: 'stay quiet', mother: "don't move", foxy: "don't lose sight of him" },
  extraMother: 'The Mother',
  extraLevelNames: ['stays away', 'calm', 'like their first night', 'quick', 'ferocious'],
  retry: 'Try again',
  nextNight: 'Next night',
  quality: 'Graphics quality',
  wishlist: 'Add to your wishlist',
  qualityLevels: ['High', 'Medium', 'Low'],
  textSize: 'Text size',
  textSizes: ['Normal', 'Large', 'Extra large'],
  menu: 'Main menu',
  demoEnd: 'End of the demo. More nights are coming.',
  extraOpened: 'The extra night is now open.',
  optionsTitle: 'Options',
  volMaster: 'Master volume',
  volMusic: 'Music',
  volSfx: 'Effects',
  language: 'Language',
  brightness: 'Brightness',
  fullscreen: 'Fullscreen',
  subtitles: 'Subtitles',
  captionsOption: 'Captions',
  reduceFlash: 'Reduce flashes and shaking',
  fogOption: 'Fog',
  tutorialOption: 'Tutorial always on',
  sensitivity: 'Look sensitivity',
  paused: 'Paused',
  resume: 'Resume',
  restartNight: 'Restart night',
  radioName: 'Radio · channel 16',
  labels: { rod: 'Rod', bucket: 'Bucket', tarp: 'Tarp', lamp: 'Light', sonar: 'Sonar' },
  look: 'Screen edges to look around, W A S D to snap around',
  sonarHint: 'Tab: sonar',
  lampHint: 'Q/E or mouse wheel: light',
  turnBar: 'TURN AROUND',
  intro: { quota: 'Quota', fishUnit: 'fish', time: '12:00 AM' },
  results: { caught: 'Fish caught', fed: 'Fed to Gulpy', lore: 'Things fished up', time: 'Time', spare: 'Over the quota' },
  // dawn dives: approved on 11 October (evening)
  dive: {
    descend: 'Dive with the tanks',
    loading: 'Strapping on the tanks…',
    ascend: 'Surface',
    hint: 'Look around. Click a passage to swim through it.',
    // find: TO APPROVE (12 October), the spot of the thing to find in the dens
    links: { cave: 'The cave', back: 'Back', toCave: 'Back to the cave', ascend: 'Climb the anchor line', find: 'Look' } as Record<string, string>,
    notes: { mother: 'Down in the dark, something enormous is breathing.' } as Record<string, string>,
    emptyDen: 'The den is empty. Whoever sleeps here is already out.',
    blocked: 'You can’t get through there. You turn back.',
    airOut: 'Out of air: surfacing.',
    offer: (who: string) => `Leave the fish beside ${who}?`,
    offerYes: 'Leave the fish',
    offerNo: 'No',
    offered: (who: string) => `The fish stays beside ${who}. Tonight they’ll sleep.`,
    noFish: 'You have no fish to leave: none were left over at six.',
    alreadyFed: 'You already left the fish.',
    // TO APPROVE (12 October)
    found: (what: string) => `In the Journal: ${what}.`,
  },
  journalTitle: 'Journal',
  journalEmpty: 'You haven’t fished anything up yet. The sea only gives things back to those who fish.',
  journalLocked: '???',
  quotes: ['“', '”'] as [string, string],
  drawings: {
    found: 'On the bench, soaking wet, there’s a drawing.',
    title: 'Drawings',
    locked: 'You haven’t found it yet.',
    names: { piscina: 'The pool', tesoro: 'My treasure', compleanno: 'Happy birthday', sottacqua: 'Underwater', marcopolo: 'Marco Polo' } as Record<string, string>,
  },
  catalogTitle: 'Catalogue',
  catalogHint: 'Species you haven’t caught yet stay silhouettes.',
  bookIndex: 'Contents',
  bookFound: 'Species found',
  bookOf: 'of',
  bookPick: 'Pick a fish on the facing page.',
  bookNone: 'You haven’t caught anything from this family yet.',
  bookClose: 'Close the book',
  bookTurn: 'arrow keys or corners to turn the page',
  pageAbbr: 'p.',
  bookWeight: 'Weight',
  bookPull: 'On the line',
  bookWhen: 'Bites',
  pull: {
    darts: 'short, light tugs',
    dead: 'plays dead, then jerks hard',
    leaps: 'leaps and shakes its head',
    glitch: 'the tension jumps at random',
    heavy: 'pulls down, heavy and steady',
    bottom: 'digs into the bottom',
    frenzy: 'constant, violent tugs',
  },
  when: {
    always: 'any time',
    night: 'from night {n}',
    dark: 'with the light off',
    bright: 'with the light at full',
    from: 'from {h}',
    near: 'with {who} nearby',
    nearAny: 'with a creature nearby',
  },
  familyPlural: { skeletal: 'Skeletal', zombie: 'Zombie', glitch: 'Glitched', corrupt: 'Corrupted', bleeding: 'Bleeding' },
  familyText: {
    skeletal: 'Missing flesh, spine and skull showing.',
    zombie: 'Rotting, milky eyes, torn fins, stitches.',
    glitch: 'Slices of the body out of place, split colours, pixels.',
    corrupt: 'Extra eyes, wrong mouths, growths, black slime.',
    bleeding: 'Wounds, dirty teeth, dripping.',
  },
  families: { skeletal: 'Skeletal', zombie: 'Zombie', glitch: 'Glitched', corrupt: 'Corrupted', bleeding: 'Bleeding' },
  rarities: { common: 'common', uncommon: 'uncommon', rare: 'rare', legendary: 'legendary' },
  newSpecies: 'New species',
  record: 'Record',
  timesCaught: 'Caught',
  inspiredBy: 'From',
  unknownFish: '???',
  sonarClose: 'Tab or click to close',
  tapToClose: 'click to close',
  on: 'On',
  off: 'Off',
  captions: {
    bowGurgle: 'gurgling at the bow',
    bowClimb: 'something climbs up the bow',
    bowDemand: 'Gulpy is hungry',
    bowEat: 'Gulpy chews',
    bowLeave: 'splash at the bow',
    knock: 'knock knock on the hull',
    falseSplash: 'a splash in the water, behind you',
    peek: 'Molly peeks in',
    giggle: 'giggle',
    whine: 'Molly whimpers',
    tantrum: 'Molly throws a tantrum',
    calm: 'Molly calms down',
    mollyLeave: 'Molly slips into the water',
    hatchBoard: 'something climbs up the stern',
    hatchStep: 'wet footsteps',
    hatchSniff: 'sniffing',
    hatchLeave: 'splash at the stern',
    bell: 'the village bell',
    left: 'left',
    right: 'right',
    robinClimb: 'little legs on the gunwale',
    robinRattle: 'the bucket rattles',
    robinSteal: 'one fish fewer',
    robinScared: 'a scurry into the water',
    lampSick: 'the light sputters',
    lampDead: 'dark',
    lullaby: 'a music box, from the deep',
    archieRise: 'something rises from the water, at the bow',
    archieInhale: 'a long sucking breath',
    archieWait: 'it waits in the dark',
    archieDive: 'it slips back under',
    archieBlow: 'the light shatters',
    lampyBeat: 'the bell, in perfect time',
    lampyGiggle: 'a giggle under the water',
    lampySurface: 'something surfaces on the line',
    lampyLet: 'it lets go of the line',
    lampyClimb: 'it climbs up the line',
    fangyApproach: 'lights under the water, coming closer',
    fangySnap: 'its head snaps round',
    fangyRise: 'something rises beside the boat, behind you',
    fangyLeave: 'it sinks back down',
    motherCall: 'a huge call, from the deep',
    motherApproach: 'they all go under; the sea goes still',
    motherLullaby: 'a lullaby, under the boat',
    motherPass: 'something huge passes under the boat',
    motherLeave: 'it moves away',
    foxyLean: 'over there, something leans out',
    foxyLeave: 'something is running across the water',
  },
  hatchCount: ['One…', 'Two…', 'Three…', 'Four…', 'Five…', 'Six…', 'Seven…', 'Eight…', 'Nine…', 'Ten!'],
  hatchReady: 'Ready or not, here I come!',
  hatchName: 'Hatch',
  kg: 'kg',
  pad: {
    pressAny: 'Press any button',
    hints: {
      cast: '{RT} to cast',
      hook: 'Bite! {RT}',
      reel: 'Hold {RT} to reel in, let go when it jerks',
      throw: '{X}: throw a fish',
      hide: '{A}: hide under the tarp',
      unhide: '{A} to leave the tarp',
      robin: 'Robin: light on full ({RB})',
      archie: 'Archie is drawing breath: light off ({LB})',
      foxy: 'With the binoculars ({LT}): don’t lose sight of him',
    },
    look: 'Right stick to look around, D-pad to snap around',
    sonarClose: '{Y} or {B} to close',
    bookTurn: '{LB} {RB} to turn the page',
    diveHint: 'Look around with the stick. {A} on a passage to swim through it.',
    select: 'Select',
  },
};

/** Specie dei pesci (nomi provvisori finché non c'è il Catalogo completo). */
export const LORE_TEXT: Record<Lang, Record<string, { title: string; body: string }>> = {
  it: {
    wristband: { title: 'Braccialetto d’ingresso', body: 'Plastica fucsia scolorita: «MAMA MARINA’S SPLASHLAND · NIGHT SPLASH · 14·08·1997 · CHILD».' },
    clipping: {
      title: 'Ritaglio di giornale',
      body: 'Gazzetta del Golfo, 17 agosto 1997. «SPLASHLAND, SPARITO UN TERZO BAMBINO. Il parco chiude a tempo indeterminato. Le ricerche dei sommozzatori nella piscina "Deep End" non hanno dato esito. Il proprietario: "Mama Marina ama i suoi piccoli, non…"» Il resto è illeggibile.',
    },
    // approvati l'11 ottobre sera
    clipping_snack: {
      title: 'Ritaglio di giornale',
      body: 'Gazzetta del Golfo, 15 agosto 1997. «NIGHT SPLASH, UN BAMBINO NON TORNA DALLA PISCINA. Alle undici era in fila allo Snack Shack, dice la madre. Alle undici e mezza il suo braccialetto galleggiava nella Deep End.»',
    },
    tickets: { title: 'Biglietti della sala giochi', body: 'Un rotolo di biglietti della sala giochi, ancora attaccati. Sono più di mille: nessuno vince così tanto giocando.' },
    flyer: {
      title: 'Volantino di Splashland',
      body: 'Plastificato. Mama Marina abbraccia tre pesciolini: «Mama Marina loves her little ones! Bring yours!» Qualcuno ha disegnato a penna altri pesciolini, piccoli, sul fondo.',
    },
    clipping_birthday: {
      title: 'Ritaglio di giornale',
      body: 'Gazzetta del Golfo, 3 maggio 1999. «Festa di compleanno sulla spiaggia: il bambino che spegneva le candeline al posto del festeggiato corre in acqua e non torna. Sulla torta resta una candelina accesa.»',
    },
    swim_cap: { title: 'Cuffia da piscina', body: 'Di gomma, a fiori rosa e bianchi, piena di sabbia. Dentro, il nome è stato grattato via.' },
    clipping_lido: {
      title: 'Ritaglio di giornale',
      body: 'Gazzetta del Golfo, 22 luglio 2003. «Lido Sirena: bambina scomparsa durante il bagno. I bagnini: "Giocava a tirare giù gli altri per le gambe. Stavolta qualcuno ha tirato giù lei."»',
    },
    goggles: { title: 'Occhialini da nuoto', body: 'Le lenti sono dipinte di nero, dall’interno. Chi li ha dipinti non voleva vedere niente.' },
    clipping_seventh: {
      title: 'Ritaglio di giornale',
      body: 'Gazzetta del Golfo, 9 agosto 2008. «Ancora un bambino scomparso nella baia, il settimo dal 1997. Il sindaco: "Nessun legame con Splashland." Da quell’estate i pescatori escono anche di notte.»',
    },
    clipping_storm: {
      title: 'Ritaglio di giornale',
      body: 'Gazzetta del Golfo, 12 novembre 2001. «Mareggiata: metà di Splashland sott’acqua. I sommozzatori dei vigili del fuoco si rifiutano di scendere nella Deep End.»',
    },
    notebook: {
      title: 'Pagina di un quaderno',
      body: 'Strappata dal quaderno di un pescatore. «La quota è dieci. Se non la porti, se ne prende un altro. Mio padre la portava, suo padre la portava. Stanotte tocca a me.»',
    },
    // le cose da trovare nelle tane delle immersioni (12 ottobre): DA APPROVARE
    den_gulpy: {
      title: 'Il menù dello Snack Shack',
      body: 'Disegnato a pastelli su un foglio a quadretti: «HOT DOG» 3000, poi solo i disegnini coi prezzi: le patatine 2000, il gelato 1500, il panino 4000. Poi un cerchio rosso attorno a tutto, ripassato due volte, la freccia e tre punti esclamativi, calcati. Estate 1997.',
    },
    den_molly: {
      title: 'Foto del trampolino',
      body: 'Una bambina in cima al trampolino, i braccioli arancioni, le braccia alzate verso chi la fotografa. Dietro, a penna: «GUARDAMI! – giugno 1997».',
    },
    den_hatch: {
      title: 'Il foglio della conta',
      body: 'I numeri da uno a dieci, scritti e riscritti a pastello finché non c’è più posto. In mezzo, calcato in rosso, grande: «10!», e sotto, più piccolo: «CHI C’È C’È».',
    },
    den_robin: {
      title: 'I premi della sala giochi',
      body: 'Gli scaffali dei premi disegnati a pastelli: l’orso enorme (5000 biglietti), la palla, la macchinina, la scatola rosa. Davanti, piccolo, un bambino con le strisce dei biglietti attorno alle braccia. Nella nuvoletta, tre punti esclamativi.',
    },
    den_archie: {
      title: 'Tutti i compleanni',
      body: 'In alto «1999». Dodici torte in fila, una per mese, ognuna con le sue candeline. Tutte le fiammelle sono cancellate col pastello nero, calcato.',
    },
    den_lampy: {
      title: 'Braccialetto dell’ospedale',
      body: 'Rosa, da neonata: «KG 3,1 – luglio 2003». Sul cartoncino, a penna, qualcuno ha aggiunto: «non lasciarla mai andare».',
    },
    den_fangy: {
      title: 'Io',
      body: 'Un bambino in mezzo al foglio, e sotto «IO». Gli occhialini da piscina sono ripassati col nero tante volte che la cera luccica. Agosto 2008.',
    },
  },
  en: {
    wristband: { title: 'Entry wristband', body: 'Faded fuchsia plastic: "MAMA MARINA’S SPLASHLAND · NIGHT SPLASH · 14·08·1997 · CHILD".' },
    clipping: {
      title: 'Newspaper clipping',
      body: 'Gulf Gazette, 17 August 1997. "SPLASHLAND: A THIRD CHILD MISSING. The park closes indefinitely. Divers searching the ‘Deep End’ pool found nothing. The owner: ‘Mama Marina loves her little ones, she would never…’" The rest is unreadable.',
    },
    clipping_snack: {
      title: 'Newspaper clipping',
      body: 'Gulf Gazette, 15 August 1997. "NIGHT SPLASH: A CHILD DOES NOT COME BACK FROM THE POOL. At eleven he was queueing at the Snack Shack, his mother says. At half past eleven his wristband was floating in the Deep End."',
    },
    tickets: { title: 'Arcade tickets', body: 'A roll of arcade tickets, still joined together. There are more than a thousand: nobody wins that many by playing.' },
    flyer: {
      title: 'Splashland flyer',
      body: 'Laminated. Mama Marina hugs three little fish: "Mama Marina loves her little ones! Bring yours!" Someone has drawn more little fish in pen, small, along the bottom.',
    },
    clipping_birthday: {
      title: 'Newspaper clipping',
      body: 'Gulf Gazette, 3 May 1999. "Birthday party on the beach: the boy who always blew out the candles instead of the birthday child runs into the water and does not come back. One candle is still lit on the cake."',
    },
    swim_cap: { title: 'Swimming cap', body: 'Rubber, with pink and white flowers, full of sand. Inside, the name has been scratched off.' },
    clipping_lido: {
      title: 'Newspaper clipping',
      body: 'Gulf Gazette, 22 July 2003. "Lido Sirena: girl missing while swimming. The lifeguards: ‘She liked to pull the others under by the legs. This time someone pulled her under.’"',
    },
    goggles: { title: 'Swimming goggles', body: 'The lenses are painted black, from the inside. Whoever painted them didn’t want to see anything.' },
    clipping_seventh: {
      title: 'Newspaper clipping',
      body: 'Gulf Gazette, 9 August 2008. "Another child missing in the bay, the seventh since 1997. The mayor: ‘No connection with Splashland.’ Since that summer, the fishermen go out at night too."',
    },
    clipping_storm: {
      title: 'Newspaper clipping',
      body: 'Gulf Gazette, 12 November 2001. "Storm surge: half of Splashland under water. The fire brigade divers refuse to go down into the Deep End."',
    },
    notebook: {
      title: 'Notebook page',
      body: 'Torn from a fisherman’s notebook. "The quota is ten. If you don’t bring it, she takes another. My father brought it, his father brought it. Tonight it’s my turn."',
    },
    // the things to find in the dens of the dives (12 October): TO APPROVE
    den_gulpy: {
      title: 'The Snack Shack menu',
      body: 'Drawn in crayon on squared paper: "HOT DOG" 3000, then just little drawings with prices: fries 2000, ice cream 1500, a sandwich 4000. Then a red circle around everything, gone over twice, the arrow and three exclamation marks, pressed hard. Summer 1997.',
    },
    den_molly: {
      title: 'Diving board photo',
      body: 'A girl at the top of the diving board, orange armbands, arms raised at whoever is taking the picture. On the back, in pen: "WATCH ME! – June 1997".',
    },
    den_hatch: {
      title: 'The counting sheet',
      body: 'The numbers one to ten, written over and over in crayon until there’s no room left. In the middle, big and pressed hard in red: "10!", and underneath, smaller: "READY OR NOT".',
    },
    den_robin: {
      title: 'The arcade prizes',
      body: 'The prize shelves drawn in crayon: the giant bear (5000 tickets), the ball, the toy car, the pink box. In front, small, a boy with strips of tickets wrapped round his arms. In the speech bubble, three exclamation marks.',
    },
    den_archie: {
      title: 'All the birthdays',
      body: '"1999" across the top. Twelve cakes in a row, one for each month, each with its candles. Every flame has been scribbled out in black crayon, pressed hard.',
    },
    den_lampy: {
      title: 'Hospital bracelet',
      body: 'Pink, a newborn’s: "3.1 KG – July 2003". On the card, in pen, someone added: "never let her go".',
    },
    den_fangy: {
      title: 'Me',
      body: 'A boy in the middle of the page, and underneath "ME". The swimming goggles have been gone over in black so many times the wax shines. August 2008.',
    },
  },
};

export interface RadioLine {
  at: number; // secondi dall'inizio della chiamata
  text: string;
}

/** La chiamata alla radio della Notte 1: breve, al massimo 20 secondi (testo approvato). */
export const RADIO_NIGHT1: Record<Lang, RadioLine[]> = {
  it: [
    { at: 0.0, text: 'Pronto? Prima notte.' },
    { at: 1.8, text: 'Entro le sei, otto pesci nel secchio: sono per la Madre.' },
    { at: 5.6, text: 'Se non arrivano, si prende un altro bambino.' },
    { at: 8.6, text: 'Gulpy sale a prua: tiragli un pesce.' },
    { at: 11.2, text: 'Molly bussa sul fianco: guardala finché non se ne va.' },
    { at: 14.6, text: 'Hatch conta dietro di te: nasconditi sotto il telone.' },
    { at: 17.8, text: 'Buona pesca.' },
    { at: 19.2, text: '' },
  ],
  en: [
    { at: 0.0, text: 'Hello? First night.' },
    { at: 1.8, text: 'By six, eight fish in the bucket: they’re for the Mother.' },
    { at: 5.6, text: 'If they don’t come, she takes another child.' },
    { at: 8.6, text: 'Gulpy comes up at the bow: toss him a fish.' },
    { at: 11.2, text: 'Molly knocks on the side: watch her until she leaves.' },
    { at: 14.6, text: 'Hatch counts behind you: hide under the tarp.' },
    { at: 17.8, text: 'Good fishing.' },
    { at: 19.2, text: '' },
  ],
};

/** La chiamata della seconda notte (la batteria e Robin), accorciata e più criptica: approvata il 10 ottobre. Le due
 *  battute su Soggy (prova dell'utente del 12 ottobre: «all'inizio della notte 2 una linea di dialogo che ti avverte»)
 *  sono DA APPROVARE. */
export const RADIO_NIGHT2: Record<Lang, RadioLine[]> = {
  it: [
    { at: 0.0, text: 'Seconda notte. Dieci pesci.' },
    { at: 2.4, text: 'La luce va a batteria. Guarda l’ago.' },
    { at: 5.4, text: 'A zero, buio. Al buio, lei canta.' },
    { at: 8.4, text: 'Robin ruba dal secchio. Luce al massimo.' },
    { at: 11.8, text: 'La luce piena costa.' },
    { at: 13.6, text: 'Al parco c’è Soggy.' },
    { at: 15.6, text: 'Col binocolo. Non perderlo di vista.' },
    { at: 18.8, text: 'Buona pesca.' },
    { at: 20.2, text: '' },
  ],
  en: [
    { at: 0.0, text: 'Second night. Ten fish.' },
    { at: 2.4, text: 'The light runs on a battery. Watch the needle.' },
    { at: 5.4, text: 'At zero, dark. In the dark, she sings.' },
    { at: 8.4, text: 'Robin steals from the bucket. Light on full.' },
    { at: 11.8, text: 'Full light costs.' },
    { at: 13.6, text: 'Soggy is in the park.' },
    { at: 15.6, text: 'Binoculars. Don’t lose sight of him.' },
    { at: 18.8, text: 'Good fishing.' },
    { at: 20.2, text: '' },
  ],
};

/** La chiamata della terza notte (Archie), corta e criptica come la seconda: approvata l'11 ottobre. */
export const RADIO_NIGHT3: Record<Lang, RadioLine[]> = {
  it: [
    { at: 0.0, text: 'Terza notte. Undici pesci.' },
    { at: 2.4, text: 'Archie viene per la luce.' },
    { at: 5.0, text: 'Se lo senti prendere fiato, spegni.' },
    { at: 8.0, text: 'E resta al buio finché non va giù.' },
    { at: 11.2, text: 'Buona pesca.' },
    { at: 12.6, text: '' },
  ],
  en: [
    { at: 0.0, text: 'Third night. Eleven fish.' },
    { at: 2.4, text: 'Archie comes for the light.' },
    { at: 5.0, text: 'If you hear him draw breath, turn it off.' },
    { at: 8.0, text: 'And stay in the dark until he goes under.' },
    { at: 11.2, text: 'Good fishing.' },
    { at: 12.6, text: '' },
  ],
};

/** La chiamata della quarta notte (Lampy), corta come le altre: approvata l'11 ottobre. */
export const RADIO_NIGHT4: Record<Lang, RadioLine[]> = {
  it: [
    { at: 0.0, text: 'Quarta notte. Dodici pesci.' },
    { at: 2.4, text: 'Lampy tira la lenza.' },
    { at: 4.6, text: 'Tre colpi uguali e una risatina: non ferrare.' },
    { at: 8.4, text: 'Lasciala andare.' },
    { at: 10.4, text: 'Buona pesca.' },
    { at: 11.8, text: '' },
  ],
  en: [
    { at: 0.0, text: 'Fourth night. Twelve fish.' },
    { at: 2.4, text: 'Lampy pulls the line.' },
    { at: 4.6, text: 'Three even rings and a giggle: don’t strike.' },
    { at: 8.4, text: 'Let her go.' },
    { at: 10.4, text: 'Good fishing.' },
    { at: 11.8, text: '' },
  ],
};

/** La chiamata della quinta notte (Fangy), corta come le altre (approvata l'11 ottobre). */
export const RADIO_NIGHT5: Record<Lang, RadioLine[]> = {
  it: [
    { at: 0.0, text: 'Quinta notte. Undici pesci.' },
    { at: 2.4, text: 'Fangy non vede. Sente.' },
    { at: 4.6, text: 'Quando le luci salgono, zitto.' },
    { at: 7.0, text: 'Niente mulinello, niente luce.' },
    { at: 9.6, text: 'Buona pesca.' },
    { at: 11.0, text: '' },
  ],
  en: [
    { at: 0.0, text: 'Fifth night. Eleven fish.' },
    { at: 2.4, text: 'Fangy can’t see. He hears.' },
    { at: 4.6, text: 'When the lights come up, not a sound.' },
    { at: 7.0, text: 'No reel, no light.' },
    { at: 9.6, text: 'Good fishing.' },
    { at: 11.0, text: '' },
  ],
};

/** La chiamata della notte extra (DA APPROVARE): non spiega niente, le regole le sai già. */
export const RADIO_NIGHT7: Record<Lang, RadioLine[]> = {
  it: [
    { at: 0.0, text: 'Notte extra. Dieci pesci.' },
    { at: 2.4, text: 'Stanotte vengono quelli che hai chiamato tu.' },
    { at: 5.6, text: 'Buona pesca.' },
    { at: 7.0, text: '' },
  ],
  en: [
    { at: 0.0, text: 'Extra night. Ten fish.' },
    { at: 2.4, text: 'Tonight the ones you called are coming.' },
    { at: 5.6, text: 'Good fishing.' },
    { at: 7.0, text: '' },
  ],
};

/**
 * La chiamata della sesta notte (la Madre): il testo proposto e approvato l'11 ottobre, con la quota portata a dieci
 * pesci per il bilanciamento (DA APPROVARE: la proposta diceva dodici).
 */
export const RADIO_NIGHT6: Record<Lang, RadioLine[]> = {
  it: [
    { at: 0.0, text: 'Sesta notte. Dieci pesci.' },
    { at: 2.4, text: 'Stanotte viene anche lei.' },
    { at: 4.6, text: 'Quando passa sotto la barca, non muoverti.' },
    { at: 7.4, text: 'Non toccare niente, non guardarti intorno.' },
    { at: 10.2, text: 'Buona pesca.' },
    { at: 11.6, text: '' },
  ],
  en: [
    { at: 0.0, text: 'Sixth night. Ten fish.' },
    { at: 2.4, text: 'Tonight she comes too.' },
    { at: 4.6, text: 'When she passes under the boat, don’t move.' },
    { at: 7.4, text: 'Don’t touch anything, don’t look around.' },
    { at: 10.2, text: 'Good fishing.' },
    { at: 11.6, text: '' },
  ],
};

/** La radio all'alba del finale A (approvato l'11 ottobre), dopo che la Madre se n'è andata col secchio. */
export const RADIO_FINALE: Record<Lang, RadioLine[]> = {
  it: [
    { at: 0.0, text: 'Ce l’hai fatta.' },
    { at: 1.6, text: 'Per quest’anno.' },
    { at: 3.4, text: '' },
  ],
  en: [
    { at: 0.0, text: 'You made it.' },
    { at: 1.6, text: 'For this year.' },
    { at: 3.4, text: '' },
  ],
};

/** La chiamata alla radio di ogni notte. */
export const RADIO: Record<number, Record<Lang, RadioLine[]>> = { 1: RADIO_NIGHT1, 2: RADIO_NIGHT2, 3: RADIO_NIGHT3, 4: RADIO_NIGHT4, 5: RADIO_NIGHT5, 6: RADIO_NIGHT6, 7: RADIO_NIGHT7 };

export const STRINGS: Record<Lang, typeof IT> = { it: IT, en: EN };

/** Le lingue del gioco, nell'ordine in cui le propone il pulsante delle opzioni. Una lingua nuova: il suo codice in
 *  `Lang`, i suoi testi in STRINGS, LORE_TEXT e RADIO (TypeScript dice cosa manca), il suo nome qui sotto
 *  (docs/LOCALIZZAZIONE.md). */
export const LANGS = Object.keys(STRINGS) as Lang[];

/** Il nome di ogni lingua nella lingua stessa (anche quelle a cui il gioco potrebbe arrivare). */
export const LANG_NAMES: Record<string, string> = {
  it: 'Italiano',
  en: 'English',
  es: 'Español',
  fr: 'Français',
  de: 'Deutsch',
  pt: 'Português',
  zh: '中文',
  ja: '日本語',
  ko: '한국어',
};

/** Un numero coi decimali come lo scrive la lingua: con la virgola in italiano e nelle altre lingue europee del gioco
 *  (2,4 kg), col punto in inglese, cinese, giapponese e coreano (2.4 kg). */
export function decimal(n: string, lang: string): string {
  return ['it', 'es', 'fr', 'de', 'pt'].includes(lang) ? n.replace('.', ',') : n;
}

/** La lingua del sistema, se il gioco ce l'ha (pt-BR → pt, zh-CN → zh); se no l'inglese. */
export function detectLang(prefs: readonly string[] = typeof navigator === 'undefined' ? [] : navigator.languages?.length ? navigator.languages : [navigator.language]): Lang {
  for (const p of prefs) {
    const l = (p || '').slice(0, 2).toLowerCase() as Lang;
    if (LANGS.includes(l)) return l;
  }
  return 'en';
}

/**
 * Le immagini con scritte (prova dell'utente del 12 ottobre: «stai attento alle immagini e ai testi nelle immagini»;
 * e prima del lancio il gioco potrebbe uscire in altre lingue). L'originale è in italiano (`nome.webp`); ogni lingua
 * tradotta ha accanto `nome_<lingua>.webp`. `langs` sono le lingue che hanno la loro versione: una lingua che non ce
 * l'ha prende quella inglese, se c'è, se no l'originale. L'elenco di tutte le immagini con scritte, e come rifarle in
 * un'altra lingua, è in docs/LOCALIZZAZIONE.md.
 */
export function localizedImage(path: string, lang: string, langs: readonly string[]): string {
  if (lang === 'it') return path;
  const pick = langs.includes(lang) ? lang : langs.includes('en') ? 'en' : null;
  return pick ? path.replace(/\.(\w+)$/, `_${pick}.$1`) : path;
}
