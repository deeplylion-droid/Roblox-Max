/**
 * Il Catalogo dei pesci: circa cento specie, tutte ispirate a pesci veri del Mediterraneo e degli abissi,
 * trasformate in cinque famiglie (vedi docs/GDD.md, «Il Catalogo dei pesci»).
 *
 * ⚠️ PROPOSTA DA APPROVARE (notte del 9 ottobre): nomi, descrizioni, rarità e condizioni sono una bozza.
 * docs/CATALOGO.md si rigenera da qui: `npm run catalog`. Le descrizioni inglesi mancanti si scrivono dopo
 * l'approvazione; finché mancano il gioco mostra quella italiana.
 */

export type FishFamily = 'skeletal' | 'zombie' | 'glitch' | 'corrupt' | 'bleeding';
export type Rarity = 'common' | 'uncommon' | 'rare' | 'legendary';
/**
 * Come combatte al recupero:
 * darts  strattoni brevi e leggeri          dead   fa il morto, poi uno strattone di colpo
 * leaps  salta e scuote la testa             glitch la tensione salta a caso, sparisce e torna
 * heavy  tira giù costante, pesante          bottom si pianta sul fondo
 * frenzy strattoni continui e violenti
 */
export type PullStyle = 'darts' | 'dead' | 'leaps' | 'glitch' | 'heavy' | 'bottom' | 'frenzy';

export interface FishWhen {
  /** abbocca dalla notte N in poi (assente: dalla prima) */
  night?: number;
  /** solo a lampara spenta / solo a lampara al massimo */
  lamp?: 'dark' | 'bright';
  /** solo da quest'ora in poi (0 = mezzanotte … 5) */
  from?: number;
  /** solo quando quella creatura è nei paraggi */
  near?: 'gulpy' | 'molly' | 'hatch' | 'any';
}

export interface FishSpecies {
  id: string;
  name: { it: string; en: string };
  /** la specie vera a cui si ispira */
  real: { it: string; en: string; sci: string };
  family: FishFamily;
  rarity: Rarity;
  kg: [number, number];
  pull: PullStyle;
  /** 0..1: quanto spesso e quanto forte strattona */
  strength: number;
  when?: FishWhen;
  desc: { it: string; en?: string };
}

const f = (
  id: string,
  it: string,
  en: string,
  real: [string, string, string],
  family: FishFamily,
  rarity: Rarity,
  kg: [number, number],
  pull: PullStyle,
  strength: number,
  descIt: string,
  when?: FishWhen,
  descEn?: string,
): FishSpecies => ({
  id,
  name: { it, en },
  real: { it: real[0], en: real[1], sci: real[2] },
  family,
  rarity,
  kg,
  pull,
  strength,
  when,
  desc: descEn ? { it: descIt, en: descEn } : { it: descIt },
});

export const FISH: FishSpecies[] = [
  // ───────────── scheletrici: carne mancante, lisca e cranio in vista ─────────────
  f('ossiuga', 'Ossiuga', 'Bonchovy', ['Acciuga', 'European anchovy', 'Engraulis encrasicolus'], 'skeletal', 'common', [0.02, 0.06], 'darts', 0.15,
    'Nuota in banchi di mille. Quando il banco gira tutto insieme, sott\'acqua si sente un rumore di ossicini, come dadi in un bicchiere.'),
  f('spratteschio', 'Spratteschio', 'Skullsprat', ['Spratto', 'European sprat', 'Sprattus sprattus'], 'skeletal', 'common', [0.01, 0.03], 'darts', 0.1,
    'Così piccolo che il teschio ti sta in punta di dito. Se lo avvicini all\'orecchio, batte i denti come chi ha freddo.'),
  f('sgombrato', 'Sgombrato', 'Macabrel', ['Sgombro', 'Atlantic mackerel', 'Scomber scombrus'], 'skeletal', 'common', [0.25, 0.6], 'darts', 0.4,
    'Qualcuno l\'ha svuotato con cura, come si sgombera una stanza. Ha lasciato la lisca, gli occhi e le righe sulla schiena.', undefined,
    'Someone emptied it out with care, the way you clear out a room. They left the spine, the eyes and the stripes on its back.'),
  f('lattossino', 'Lattossino', 'Bonesmelt', ['Latterino', 'Big-scale sand smelt', 'Atherina boyeri'], 'skeletal', 'common', [0.005, 0.02], 'darts', 0.1,
    'Trasparente da vivo, ancora di più adesso. Attraverso la lisca vedi il fondo del secchio.'),
  f('bogossa', 'Bogossa', 'Bonebogue', ['Boga', 'Bogue', 'Boops boops'], 'skeletal', 'common', [0.1, 0.3], 'darts', 0.25,
    'Ha gli occhi enormi di quando era viva. Le sono rimasti solo quelli, e la voglia di guardare.'),
  f('zerossa', 'Zerossa', 'Picked Picarel', ['Zerro', 'Picarel', 'Spicara smaris'], 'skeletal', 'common', [0.03, 0.1], 'darts', 0.2,
    'Pulito come se qualcuno l\'avesse mangiato con calma, un boccone alla volta, senza nessuna fretta.'),
  f('occhiata_vuota', 'Occhiata Vuota', 'Hollow Bream', ['Occhiata', 'Saddled seabream', 'Oblada melanura'], 'skeletal', 'common', [0.1, 0.4], 'darts', 0.3,
    'Al posto degli occhi ha due buchi. Il nome però è rimasto, e ti guarda lo stesso.'),
  f('ossaguglia', 'Ossaguglia', 'Garbone', ['Aguglia', 'Garfish', 'Belone belone'], 'skeletal', 'uncommon', [0.3, 1.0], 'leaps', 0.45,
    'Ha le ossa verdi, come quando era viva, e un becco pieno di dentini. Se la prendi in mano ti punge, per abitudine.'),
  f('ago_dosso', 'Ago d\'Osso', 'Pipebone', ['Pesce ago', 'Greater pipefish', 'Syngnathus acus'], 'skeletal', 'uncommon', [0.01, 0.04], 'darts', 0.1,
    'Sembra un ago da cucito fatto d\'osso. Qualcuno, laggiù, lo usa ancora per ricucire.'),
  f('san_pietrificato', 'San Pietrificato', 'Johnny Bones', ['Pesce San Pietro', 'John Dory', 'Zeus faber'], 'skeletal', 'uncommon', [0.5, 2.0], 'heavy', 0.5,
    'Sul fianco ha l\'impronta di un pollice, come dice la leggenda. Ma non è il pollice di un santo: è piccolo, come quello di un bambino.'),
  f('ceca_ossuta', 'Ceca Ossuta', 'Glassbone Eel', ['Ceca (anguilla giovane)', 'Glass eel', 'Anguilla anguilla'], 'skeletal', 'uncommon', [0.001, 0.005], 'darts', 0.05,
    'Non ha mai avuto niente da nascondere: si vedeva tutto anche prima. Adesso si vede anche quello che ha mangiato.'),
  f('lucertossa', 'Lucertossa', 'Lizardbone', ['Pesce lucertola', 'Atlantic lizardfish', 'Synodus saurus'], 'skeletal', 'uncommon', [0.2, 0.8], 'darts', 0.5,
    'Ha più denti che ossa, e di ossa ne ha tante. Sorride anche da morto, come le lucertole al sole.'),
  f('sciabola_spolpata', 'Sciabola Spolpata', 'Stripped Scabbard', ['Pesce sciabola', 'Silver scabbardfish', 'Lepidopus caudatus'], 'skeletal', 'uncommon', [1.0, 4.0], 'leaps', 0.55,
    'Lungo come un braccio, sottile come una lama. Quando lo tiri su sbatte sul bordo con un rumore di posate.', { from: 3 }),
  f('lanternossa', 'Lanternossa', 'Bonelantern', ['Pesce lanterna', 'Spotted lanternfish', 'Myctophum punctatum'], 'skeletal', 'rare', [0.01, 0.03], 'darts', 0.15,
    'Le lucine che aveva sui fianchi sono rimaste accese sulle ossa. Al buio sembra un piccolo parco giochi visto da lontano.', { lamp: 'dark', from: 2 }),
  f('cavalluccio_dosso', 'Cavalluccio d\'Osso', 'Bone Seahorse', ['Cavalluccio marino', 'Long-snouted seahorse', 'Hippocampus guttulatus'], 'skeletal', 'rare', [0.01, 0.02], 'dead', 0.05,
    'Un cavallino da giostra, senza la giostra. Nel secchio gira in tondo, piano, finché lo guardi.', { lamp: 'dark' }),
  f('flauto_dossa', 'Flauto d\'Ossa', 'Bone Cornet', ['Pesce flauto', 'Bluespotted cornetfish', 'Fistularia commersonii'], 'skeletal', 'rare', [0.5, 2.5], 'darts', 0.35,
    'Se ci soffi dentro suona. Una nota sola, sempre la stessa: quella del carillon.', { night: 2 }),
  f('trombetta_dosso', 'Trombetta d\'Osso', 'Snipebone', ['Pesce trombetta', 'Longspine snipefish', 'Macroramphosus scolopax'], 'skeletal', 'rare', [0.02, 0.08], 'darts', 0.15,
    'Ha il muso a trombetta. All\'ingresso di Splashland vendevano trombette così, e i bambini le suonavano fino a sera.', { night: 2 }),
  f('aquila_dosso', 'Aquila d\'Osso', 'Bone Eagle Ray', ['Aquila di mare', 'Common eagle ray', 'Myliobatis aquila'], 'skeletal', 'rare', [3, 15], 'heavy', 0.7,
    'Le razze non hanno ossa, dicono i libri. Questa ne ha trovate da qualche parte, e non sono di pesce.', { night: 2, lamp: 'dark' }),
  f('spadossa', 'Spadossa', 'Bonesword', ['Pesce spada', 'Swordfish', 'Xiphias gladius'], 'skeletal', 'legendary', [40, 200], 'leaps', 0.9,
    'Solo la spada e lo scheletro, ancora in posa da combattimento. Sulla spada è infilato un braccialetto di plastica fucsia.', { night: 3 }),
  f('sega_dossa', 'Sega d\'Ossa', 'Bonesaw', ['Pesce sega', 'Smalltooth sawfish', 'Pristis pectinata'], 'skeletal', 'legendary', [60, 250], 'bottom', 0.95,
    'Nel Mediterraneo non se ne vedono da cent\'anni. Questo non lo sa.', { night: 4, lamp: 'dark' }),

  // ───────────── zombi: marci, occhi lattiginosi, pinne strappate, punti di sutura ─────────────
  f('cefamorto', 'Cefamorto', 'Ghoullet', ['Cefalo', 'Flathead grey mullet', 'Mugil cephalus'], 'zombie', 'common', [0.4, 2.5], 'dead', 0.35,
    'Mangia il fango del fondo da quando è nato. Adesso il fango mangia lui, e vanno d\'accordo.'),
  f('sogliombra', 'Sogliombra', 'Lost Sole', ['Sogliola', 'Common sole', 'Solea solea'], 'zombie', 'common', [0.2, 1.0], 'bottom', 0.3,
    'Vive schiacciata sul fondo, con tutti e due gli occhi dalla stessa parte. Da morta ha deciso di guardare anche dall\'altra.'),
  f('suro_sfatto', 'Suro Sfatto', 'Horse Mackerot', ['Suro', 'Atlantic horse mackerel', 'Trachurus trachurus'], 'zombie', 'common', [0.1, 0.5], 'dead', 0.3,
    'Si sfalda come pane bagnato. Le scaglie che restano sul legno brillano tutta la notte.'),
  f('nasello_senza_naso', 'Nasello Senza Naso', 'Noseless Hake', ['Nasello', 'European hake', 'Merluccius merluccius'], 'zombie', 'common', [0.3, 2.0], 'dead', 0.3,
    'Il naso gli è caduto da tempo. Gli piaceva molto, dicono quelli che lo conoscevano.'),
  f('tordo_torbido', 'Tordo Torbido', 'Murky Wrasse', ['Tordo marvizzo', 'Ballan wrasse', 'Labrus bergylta'], 'zombie', 'common', [0.2, 1.0], 'dead', 0.35,
    'Ha gli occhi torbidi come l\'acqua di una pozzanghera. Nel secchio fa le bolle, anche se non respira più.'),
  f('orrata', 'Orrata', 'Guilt-head Bream', ['Orata', 'Gilt-head bream', 'Sparus aurata'], 'zombie', 'uncommon', [0.5, 3.0], 'dead', 0.5,
    'Ha ancora la riga d\'oro tra gli occhi e una cucitura grossolana lungo la pancia. Qualcuno l\'ha aperta, ci ha messo dentro qualcosa e l\'ha richiusa.', undefined,
    'It still has the gold band between its eyes, and a crude seam along its belly. Someone opened it, put something inside, and sewed it shut.'),
  f('sarcofago', 'Sarcofago', 'Sarcophagus', ['Sarago maggiore', 'White seabream', 'Diplodus sargus'], 'zombie', 'uncommon', [0.3, 1.5], 'dead', 0.45,
    'Ha le bande nere sui fianchi come le fasce di una mummia. Ogni tanto una si scioglie, e sotto non c\'è più il pesce.'),
  f('gattomorto', 'Gattomorto', 'Deadcat Shark', ['Gattuccio', 'Small-spotted catshark', 'Scyliorhinus canicula'], 'zombie', 'uncommon', [0.5, 2.0], 'dead', 0.6,
    'Fa il gatto morto, come si dice. Lo tiri su senza fatica, lo metti nel secchio, e allora smette di farlo.'),
  f('corvina_becchina', 'Corvina Becchina', 'Meagrave', ['Corvina', 'Brown meagre', 'Sciaena umbra'], 'zombie', 'uncommon', [0.5, 2.5], 'dead', 0.45,
    'Brontola come i becchini a fine giornata. Se l\'avvicini all\'orecchio, senti la terra che cade sul legno.'),
  f('palombra', 'Palombra', 'Smooth Hellhound', ['Palombo', 'Common smooth-hound', 'Mustelus mustelus'], 'zombie', 'uncommon', [2, 10], 'heavy', 0.6,
    'Grigio come un cane vecchio, e come un cane vecchio ti segue. Rimesso in acqua torna sotto la barca, e aspetta.', { from: 2 }),
  f('pastinaca_putrida', 'Pastinaca Putrida', 'Stinkray', ['Pastinaca', 'Common stingray', 'Dasyatis pastinaca'], 'zombie', 'uncommon', [2, 10], 'bottom', 0.6,
    'La senti prima di vederla. Il pungiglione è ancora velenoso: è l\'unica cosa di lei che funziona.'),
  f('castagna_marcia', 'Castagna Marcia', 'Rotten Pomfret', ['Pesce castagna', 'Atlantic pomfret', 'Brama brama'], 'zombie', 'uncommon', [0.5, 3.0], 'dead', 0.5,
    'Nera e lucida come una castagna d\'autunno. E come una castagna marcia, dentro è piena di piccoli vermi bianchi che ballano.', { from: 2 }),
  f('ombrina_smorta', 'Ombrina Smorta', 'Ghost Drum', ['Ombrina', 'Shi drum', 'Umbrina cirrosa'], 'zombie', 'uncommon', [1, 8], 'dead', 0.55,
    'Le ombrine fanno il tamburo con la vescica natatoria. Questa la vescica non ce l\'ha più, ma il tamburo continua.', { lamp: 'dark' }),
  f('branzombi', 'Branzombi', 'Grave Bass', ['Spigola (branzino)', 'European seabass', 'Dicentrarchus labrax'], 'zombie', 'rare', [1, 6], 'dead', 0.65,
    'Il pesce più bello del secchio, se non fosse per gli occhi bianchi come il latte. Continua a boccheggiare anche se non ne ha più bisogno.'),
  f('murena_murata', 'Murena Murata', 'Morgueray', ['Murena', 'Mediterranean moray', 'Muraena helena'], 'zombie', 'rare', [1, 6], 'dead', 0.7,
    'È sempre stata nella stessa fessura, con la bocca aperta. Un giorno qualcuno ha chiuso la fessura da fuori, una pietra alla volta.', { lamp: 'dark' }),
  f('raccapricciola', 'Raccapricciola', 'Shamberjack', ['Ricciola', 'Greater amberjack', 'Seriola dumerili'], 'zombie', 'rare', [5, 30], 'heavy', 0.85,
    'Tira come un toro anche se metà del corpo se n\'è andata da un pezzo. È la metà che resta che ti preoccupa.', { night: 2 }),
  f('cernia_gemente', 'Cernia Gemente', 'Groaner', ['Cernia bruna', 'Dusky grouper', 'Epinephelus marginatus'], 'zombie', 'rare', [5, 40], 'bottom', 0.9,
    'Dal fondo della barca la senti gemere piano, come un vecchio che si gira nel letto. Ha sessant\'anni, e da quaranta è morta.', { night: 2, from: 3 }),
  f('rombo_sepolto', 'Rombo Sepolto', 'Tomb Turbot', ['Rombo chiodato', 'Turbot', 'Scophthalmus maximus'], 'zombie', 'rare', [2, 12], 'bottom', 0.75,
    'Si seppellisce nella sabbia per aspettare le prede. Questo si è seppellito tanto tempo fa, e non è più riuscito a uscire.', { night: 2 }),
  f('chimera_bianca', 'Chimera Bianca', 'Pale Ghost Shark', ['Chimera', 'Rabbit fish (ghost shark)', 'Chimaera monstrosa'], 'zombie', 'rare', [0.5, 2.5], 'dead', 0.5,
    'Vive così in fondo che la luce non sa cosa sia. La lampara le fa male: chiude gli occhi enormi e piange una cosa grigia.', { night: 3, lamp: 'dark' }),
  f('squalo_capomorto', 'Squalo Capomorto', 'Sickgill Shark', ['Squalo capopiatto', 'Bluntnose sixgill shark', 'Hexanchus griseus'], 'zombie', 'legendary', [50, 300], 'bottom', 1.0,
    'Sale dagli abissi una volta all\'anno, come chi va a trovare i morti. Ha sei branchie, e respira con tutte e sei, piano, anche fuori dall\'acqua.', { night: 5, from: 4 }),

  // ───────────── glitchati: fette sfalsate, colori separati, come un nastro rovinato ─────────────
  f('triglia_doppia', 'Triglia Doppia', 'Double Mullet', ['Triglia di fango', 'Red mullet', 'Mullus barbatus'], 'glitch', 'common', [0.1, 0.4], 'glitch', 0.3,
    'Si vede due volte, un poco spostata, come in un televisore con l\'antenna storta. Delle due, solo una è nel secchio.'),
  f('lanzardo_riavvolto', 'Lanzardo Riavvolto', 'Rewound Chub Mackerel', ['Lanzardo', 'Atlantic chub mackerel', 'Scomber colias'], 'glitch', 'common', [0.2, 0.8], 'glitch', 0.4,
    'Nuota all\'indietro, a scatti, come un nastro riavvolto. Se lo guardi abbastanza a lungo, torna in acqua da solo.'),
  f('donzella_saturata', 'Donzella Saturata', 'Oversaturated Wrasse', ['Donzella', 'Mediterranean rainbow wrasse', 'Coris julis'], 'glitch', 'common', [0.03, 0.15], 'glitch', 0.25,
    'Colori troppo accesi, come le cassette dei cartoni animati consumate a forza di guardarle. Ti lascia l\'arcobaleno sulle mani.'),
  f('castagnola_sgranata', 'Castagnola Sgranata', 'Grainy Damselfish', ['Castagnola', 'Damselfish', 'Chromis chromis'], 'glitch', 'common', [0.02, 0.08], 'glitch', 0.2,
    'Da vicino è tutta puntini, come una foto ingrandita troppo. Più ti avvicini, meno pesce c\'è.'),
  f('pagello_pixelato', 'Pagello Pixelato', 'Pixelated Pandora', ['Pagello fragolino', 'Common pandora', 'Pagellus erythrinus'], 'glitch', 'common', [0.1, 0.6], 'glitch', 0.3,
    'Ha gli spigoli. Non dovrebbe averli, i pesci sono rotondi, ma lui ha gli spigoli e qualche quadratino in meno.'),
  f('menola_neve', 'Menola Neve', 'Snow Picarel', ['Menola', 'Blotched picarel', 'Spicara maena'], 'glitch', 'common', [0.05, 0.15], 'glitch', 0.2,
    'Coperta di neve bianca e nera che sfrigola. Se avvicini l\'orecchio, sotto la neve senti un canale lontano.'),
  f('salpa_sfasata', 'Salpa Sfasata', 'Out-of-Sync Salema', ['Salpa', 'Salema porgy (dreamfish)', 'Sarpa salpa'], 'glitch', 'uncommon', [0.3, 1.5], 'glitch', 0.45,
    'Chi la mangia fa brutti sogni, dicono i vecchi. Questa li fa fare anche a chi la guarda: righe gialle che scorrono, e una musica che non c\'è.', undefined,
    'Eat one and you get bad dreams, the old men say. This one gives them to whoever looks at it: yellow stripes sliding past, and music that isn\'t there.'),
  f('pettine_a_scatti', 'Pettine a Scatti', 'Stuttering Razorfish', ['Pesce pettine', 'Pearly razorfish', 'Xyrichtys novacula'], 'glitch', 'uncommon', [0.05, 0.3], 'glitch', 0.3,
    'Si muove a scatti, saltando dei fotogrammi. Ogni volta che salta è un po\' più vicino al bordo del secchio.'),
  f('re_di_triglie_a_righe', 'Re di Triglie a Righe', 'Interlaced Cardinal', ['Re di triglie', 'Mediterranean cardinalfish', 'Apogon imberbis'], 'glitch', 'uncommon', [0.02, 0.08], 'glitch', 0.25,
    'Fatto di righe orizzontali, una sì e una no. Nelle righe che mancano c\'è un altro pesce, che non riesci mai a vedere bene.', { lamp: 'dark' }),
  f('occhialone_veloce', 'Occhialone Veloce', 'Fast-Forward Seabream', ['Occhialone', 'Blackspot seabream', 'Pagellus bogaraveo'], 'glitch', 'uncommon', [0.3, 1.5], 'glitch', 0.45,
    'Vive tutto più in fretta. Quando lo tiri su è giovane, quando lo metti nel secchio è vecchio, e domattina sarà polvere.', { from: 3 }),
  f('balestra_sfocata', 'Balestra Sfocata', 'Blurred Triggerfish', ['Pesce balestra', 'Grey triggerfish', 'Balistes capriscus'], 'glitch', 'uncommon', [0.5, 2.0], 'glitch', 0.5,
    'Sfocato, anche se ti avvicini, anche se ti strofini gli occhi. Si mette a fuoco un attimo solo: quando morde.'),
  f('torpedine_statica', 'Torpedine Statica', 'Static Ray', ['Torpedine marmorata', 'Marbled electric ray', 'Torpedo marmorata'], 'glitch', 'rare', [2, 10], 'glitch', 0.7,
    'Fa la neve come un televisore acceso su un canale vuoto. Se la tocchi, per un attimo la radio di bordo si accende da sola.', { lamp: 'dark' }),
  f('anguilla_smagnetizzata', 'Anguilla Smagnetizzata', 'Demagnetized Eel', ['Anguilla', 'European eel', 'Anguilla anguilla'], 'glitch', 'rare', [0.5, 3.0], 'glitch', 0.6,
    'Le anguille trovano la strada col magnetismo. Questa l\'ha perso tutto, come un nastro lasciato al sole, e si ricorda solo un pezzo di canzone.', { night: 2 }),
  f('pappagallo_in_loop', 'Pappagallo in Loop', 'Looping Parrotfish', ['Pesce pappagallo', 'Mediterranean parrotfish', 'Sparisoma cretense'], 'glitch', 'rare', [0.5, 2.0], 'glitch', 0.5,
    'Ripete sempre gli stessi tre secondi, come un nastro inceppato: apre la bocca, la chiude, apre la bocca, la chiude.', { night: 2 }),
  f('leccia_senza_segnale', 'Leccia Senza Segnale', 'No-Signal Leerfish', ['Leccia', 'Leerfish', 'Lichia amia'], 'glitch', 'rare', [3, 20], 'glitch', 0.75,
    'Per un momento tira fortissimo, poi la lenza è vuota, poi di nuovo. Sul sonar compare e scompare come un canale che non prende.', { night: 2 }),
  f('civetta_fuori_quadro', 'Civetta Fuori Quadro', 'Off-Frame Gurnard', ['Pesce civetta', 'Flying gurnard', 'Dactylopterus volitans'], 'glitch', 'rare', [0.5, 1.8], 'glitch', 0.5,
    'Non sta mai tutta nell\'inquadratura: un pezzo esce sempre dal bordo. Il pezzo che manca, nel secchio, si muove.', { night: 2 }),
  f('pesce_volante_in_pausa', 'Pesce Volante in Pausa', 'Freeze-Frame Flyingfish', ['Pesce volante', 'Mediterranean flyingfish', 'Cheilopogon heterurus'], 'glitch', 'rare', [0.1, 0.4], 'glitch', 0.6,
    'Salta fuori dall\'acqua e resta lì, fermo a mezz\'aria, tremolante come un fermo immagine. Poi qualcuno preme play.', { night: 3 }),
  f('alaccia_registrata_sopra', 'Alaccia Registrata Sopra', 'Taped-Over Sardinella', ['Alaccia', 'Round sardinella', 'Sardinella aurita'], 'glitch', 'rare', [0.05, 0.2], 'glitch', 0.35,
    'Sotto il pesce, a tratti, si vede ancora la registrazione di prima: una festa di compleanno, le candeline, qualcuno che dice di guardare in camera.', { night: 3 }),
  f('cheppia_senza_audio', 'Cheppia Senza Audio', 'Muted Shad', ['Cheppia', 'Twaite shad', 'Alosa fallax'], 'glitch', 'rare', [0.5, 1.5], 'glitch', 0.5,
    'Si dibatte senza fare rumore: niente schizzi, niente colpi sul legno. Come se qualcuno avesse tolto l\'audio solo a lei.', { night: 4 }),
  f('lampuga_fuori_traccia', 'Lampuga Fuori Traccia', 'Bad-Tracking Mahi', ['Lampuga', 'Common dolphinfish', 'Coryphaena hippurus'], 'glitch', 'legendary', [3, 15], 'glitch', 0.8,
    'Le lampughe cambiano colore quando muoiono. Questa cambia colore in continuazione, a strisce, come una cassetta che si sta per rompere.', { night: 3, lamp: 'bright' }),

  // ───────────── corrotti: occhi in più, bocche sbagliate, escrescenze, melma nera ─────────────
  f('trigliocchi', 'Trigliocchi', 'Dread Mullet', ['Triglia di scoglio', 'Striped red mullet', 'Mullus surmuletus'], 'corrupt', 'common', [0.1, 0.5], 'heavy', 0.35,
    'Ha i baffi per frugare nella sabbia, e tre occhi in più per cercare te.', undefined,
    'It has whiskers for rooting through the sand, and three extra eyes for looking for you.'),
  f('sardonica', 'Sardonica', 'Sardonic Sardine', ['Sardina', 'European pilchard', 'Sardina pilchardus'], 'corrupt', 'common', [0.05, 0.12], 'heavy', 0.15,
    'Ha il sorriso sardonico dei morti: le labbra tirate indietro, tutti i denti in vista. Le sardine non hanno denti.'),
  f('ghiozzo_gozzuto', 'Ghiozzo Gozzuto', 'Gooby', ['Ghiozzo nero', 'Black goby', 'Gobius niger'], 'corrupt', 'common', [0.02, 0.1], 'heavy', 0.2,
    'Sotto la gola gli è cresciuta una sacca nera e molle. Se la premi, dentro qualcosa si sposta.'),
  f('bavaccia', 'Bavaccia', 'Slime Blenny', ['Bavosa', 'Tompot blenny', 'Parablennius gattorugine'], 'corrupt', 'common', [0.02, 0.1], 'heavy', 0.2,
    'Sbava melma nera senza fermarsi mai. La melma resta sul secchio, sulle mani, e la mattina dopo è ancora lì.'),
  f('scorfano_pece', 'Scorfano Pece', 'Tar Scorpionfish', ['Scorfano nero', 'Black scorpionfish', 'Scorpaena porcus'], 'corrupt', 'common', [0.1, 0.5], 'heavy', 0.4,
    'Brutto di suo, come tutti gli scorfani. Adesso gli cola pece nera dalle spine, e dove cola il legno della barca diventa scuro.'),
  f('sciarrano_scrivano', 'Sciarrano Scrivano', 'Scribbled Comber', ['Sciarrano', 'Painted comber', 'Serranus scriba'], 'corrupt', 'common', [0.05, 0.3], 'heavy', 0.25,
    'Sulla testa ha dei ghirigori che sembrano scritte. Da quando è cambiato, le scritte si leggono: sono date. L\'ultima è di stanotte.'),
  f('gallincubo', 'Gallincubo', 'Gurner', ['Gallinella', 'Tub gurnard', 'Chelidonichthys lucerna'], 'corrupt', 'uncommon', [0.3, 2.0], 'heavy', 0.5,
    'Le pinne davanti sono diventate dita, e con le dita cammina sul fondo del secchio. Di notte bussa.'),
  f('mostrella', 'Mostrella', 'Forkbeast', ['Mostella', 'Forkbeard', 'Phycis phycis'], 'corrupt', 'uncommon', [0.5, 3.0], 'heavy', 0.55,
    'Al posto della barbetta ha un ciuffo di filamenti neri che si muovono da soli, anche quando lei sta ferma.', { from: 2 }),
  f('mormoria', 'Mormorìa', 'Murmuring Steenbras', ['Mormora', 'Sand steenbras', 'Lithognathus mormyrus'], 'corrupt', 'uncommon', [0.2, 1.0], 'heavy', 0.35,
    'Dalle branchie viene un brusio continuo, come quello di un parco pieno di gente, molto lontano.'),
  f('luciferna', 'Luciferna', 'Starglazer', ['Pesce prete (lucerna)', 'Atlantic stargazer', 'Uranoscopus scaber'], 'corrupt', 'rare', [0.2, 1.0], 'heavy', 0.5,
    'Sta sepolto nella sabbia con gli occhi rivolti in su, ad aspettare. Questo ne ha una fila intera, tutti rivolti verso la barca.', { lamp: 'dark' }),
  f('bocchenere', 'Bocchenere', 'Blackmouths', ['Squalo boccanera', 'Blackmouth catshark', 'Galeus melastomus'], 'corrupt', 'rare', [0.5, 2.0], 'heavy', 0.6,
    'Una bocca nera, come dice il nome. Poi un\'altra sul fianco, poi un\'altra ancora. Si aprono e si chiudono tutte insieme.', { night: 2, lamp: 'dark' }),
  f('pesce_bubbone', 'Pesce Bubbone', 'Pustule Puffer', ['Pesce palla argenteo', 'Silver-cheeked toadfish', 'Lagocephalus sceleratus'], 'corrupt', 'rare', [1, 4], 'heavy', 0.5,
    'Quando si spaventa si gonfia, e si gonfiano anche le bolle nere che ha sulla pelle. Non spaventarlo.', { night: 2 }),
  f('missina_della_melma', 'Missina della Melma', 'Slimehag', ['Missina', 'Atlantic hagfish', 'Myxine glutinosa'], 'corrupt', 'rare', [0.1, 0.6], 'heavy', 0.6,
    'Quando la tocchi fa tanta di quella melma da riempire il secchio. La melma è nera, ed è tiepida.', { night: 2, lamp: 'dark' }),
  f('specchio_nero', 'Specchio Nero', 'Grimehead', ['Pesce specchio', 'Mediterranean slimehead', 'Hoplostethus mediterraneus'], 'corrupt', 'rare', [0.2, 0.6], 'heavy', 0.5,
    'Sul fianco ha una macchia nera lucida come uno specchio. Dentro lo specchio c\'è la barca, e sulla barca c\'è qualcuno in più.', { night: 3, from: 3 }),
  f('sciabola_di_carbone', 'Sciabola di Carbone', 'Coalscabbard', ['Pesce sciabola nero', 'Black scabbardfish', 'Aphanopus carbo'], 'corrupt', 'rare', [1, 3], 'heavy', 0.6,
    'Viene da mille metri sotto, dove non arriva niente. Ha gli occhi grandi come monete, e dentro, a guardarli bene, una lampara accesa.', { night: 3, from: 4 }),
  f('granatiere_nero', 'Granatiere Nero', 'Grimadier', ['Granatiere', 'Hollowsnout grenadier', 'Coelorinchus caelorhincus'], 'corrupt', 'rare', [0.1, 0.5], 'heavy', 0.4,
    'Ha la coda lunga e sottile come quella di un topo, e come i topi non arriva mai da solo. Uno nel secchio, cento sotto la barca.', { night: 3 }),
  f('vipera_degli_abissi', 'Vipera degli Abissi', 'Vipermaw', ['Pesce vipera', 'Sloane\'s viperfish', 'Chauliodus sloani'], 'corrupt', 'rare', [0.02, 0.05], 'heavy', 0.3,
    'Così piccolo, e i denti così lunghi che non riesce a chiudere la bocca. Non ha mai potuto. Non ha mai voluto.', { night: 4, lamp: 'dark' }),
  f('razza_due_facce', 'Razza dalle Due Facce', 'Two-Faced Skate', ['Razza bianca', 'White skate', 'Rostroraja alba'], 'corrupt', 'rare', [5, 40], 'heavy', 0.8,
    'Sotto, le razze hanno una faccia che sembra sorridere. Questa ne ha due, e non sorridono tutte e due.', { night: 3 }),
  f('pesce_angelo_caduto', 'Pesce Angelo Caduto', 'Fallen Angelshark', ['Squadro (pesce angelo)', 'Angelshark', 'Squatina squatina'], 'corrupt', 'legendary', [10, 60], 'heavy', 0.9,
    'Lo chiamavano pesce angelo per le pinne larghe come ali. Le ali ci sono ancora, nere e bagnate, e intorno alla testa un\'aureola di occhi.', { night: 4, lamp: 'dark' }),
  f('re_nero', 'Re Nero', 'Black Opah', ['Pesce re', 'Opah', 'Lampris guttatus'], 'corrupt', 'legendary', [20, 70], 'heavy', 0.95,
    'Il pesce re è rotondo e rosso come la luna al tramonto. Questo è nero come la pece, e al posto della corona ha una bocca.', { night: 5 }),

  // ───────────── sanguinanti: ferite, denti sporchi, colature ─────────────
  f('trafittina', 'Trafittina', 'Weeper', ['Tracina drago', 'Greater weever', 'Trachinus draco'], 'bleeding', 'common', [0.1, 0.4], 'frenzy', 0.45,
    'Piange sangue da tutti e due gli occhi. Non è triste: la spina che ha sulla schiena le è entrata dentro.'),
  f('serrasangue', 'Serrasangue', 'Bleedfish', ['Pesce serra', 'Bluefish', 'Pomatomus saltatrix'], 'bleeding', 'common', [0.5, 3.0], 'frenzy', 0.65,
    'Morde tutto quello che si muove, anche se stesso. È pieno di morsi, e ognuno ha la forma della sua bocca.'),
  f('squartotta', 'Squartotta', 'Slashed Seabream', ['Sparaglione', 'Annular seabream', 'Diplodus annularis'], 'bleeding', 'common', [0.05, 0.2], 'frenzy', 0.35,
    'Piccola, piatta, con un taglio netto da parte a parte. Il taglio sanguina solo quando la guardi.'),
  f('pagro_sanguigno', 'Pagro Sanguigno', 'Bled Porgy', ['Pagro', 'Red porgy', 'Pagrus pagrus'], 'bleeding', 'common', [0.3, 2.0], 'frenzy', 0.5,
    'Sanguina dalle branchie, come se respirasse sangue. Per lui, adesso, è la stessa cosa.'),
  f('barracruda', 'Barracruda', 'Barracutter', ['Luccio di mare', 'European barracuda', 'Sphyraena sphyraena'], 'bleeding', 'uncommon', [0.5, 3.0], 'frenzy', 0.7,
    'Morde anche fuori dall\'acqua, anche nel secchio, anche con lo sguardo. Ha la carne viva in vista, rossa come appena tagliata.', undefined,
    'It bites out of the water too, in the bucket too, even with its eyes. Its flesh is showing, raw and red, as if it had just been cut.'),
  f('razza_inchiodata', 'Razza Inchiodata', 'Nailback Ray', ['Razza chiodata', 'Thornback ray', 'Raja clavata'], 'bleeding', 'uncommon', [1, 6], 'frenzy', 0.55,
    'Le spine sulla schiena sono diventate chiodi veri, arrugginiti. Qualcuno l\'aveva inchiodata a qualcosa, e lei si è staccata da sola.'),
  f('scorticano', 'Scorticano', 'Skinned Scorpionfish', ['Scorfano rosso', 'Red scorpionfish', 'Scorpaena scrofa'], 'bleeding', 'uncommon', [0.5, 3.0], 'frenzy', 0.5,
    'Rosso non perché sia rosso: gli manca la pelle. Le spine invece ci sono tutte, e sono ancora velenose.'),
  f('rabbiglio', 'Rabbiglio', 'Rabidfish', ['Pesce coniglio', 'Dusky spinefoot', 'Siganus luridus'], 'bleeding', 'uncommon', [0.1, 0.5], 'frenzy', 0.6,
    'Ha i denti da coniglio e la schiuma rosa alla bocca. Morde la lenza, il secchio, il bordo della barca, e non si stanca.', { night: 2 }),
  f('palamita_squarciata', 'Palamita Squarciata', 'Gashed Bonito', ['Palamita', 'Atlantic bonito', 'Sarda sarda'], 'bleeding', 'uncommon', [1, 5], 'frenzy', 0.7,
    'Uno squarcio dalla testa alla coda, come se qualcosa di molto grande avesse provato ad aprirla. Qualcosa con tanti denti, tutti in fila.'),
  f('leccia_lacerata', 'Leccia Lacerata', 'Lacerated Pompano', ['Leccia stella', 'Pompano', 'Trachinotus ovatus'], 'bleeding', 'uncommon', [0.3, 1.5], 'frenzy', 0.55,
    'Ferite piccole e regolari su tutto il corpo, come se l\'avesse rosicchiata un banco di qualcosa di piccolo e ordinato.'),
  f('dentiera', 'Dentiera', 'Dentures', ['Dentice', 'Common dentex', 'Dentex dentex'], 'bleeding', 'rare', [1, 8], 'frenzy', 0.8,
    'I denti non sono i suoi. Sono troppi, di misure diverse, e qualcuno ha ancora l\'apparecchio.', { night: 2 }),
  f('grondongo', 'Grondongo', 'Congore', ['Grongo', 'European conger', 'Conger conger'], 'bleeding', 'rare', [3, 25], 'frenzy', 0.85,
    'Esce dall\'acqua grondando, e non è acqua. Nel secchio continua a grondare, e il secchio si riempie.', { lamp: 'dark' }),
  f('lampreda_vampira', 'Lampreda Vampira', 'Vampire Lamprey', ['Lampreda di mare', 'Sea lamprey', 'Petromyzon marinus'], 'bleeding', 'rare', [0.5, 2.0], 'frenzy', 0.7,
    'Al posto della bocca, un cerchio di denti. Si attacca al secchio, al remo, alla tua mano, e succhia piano, senza fare male. All\'inizio.', { night: 2, lamp: 'dark' }),
  f('pesce_violento', 'Pesce Violento', 'Gutarfish', ['Pesce violino', 'Common guitarfish', 'Rhinobatos rhinobatos'], 'bleeding', 'rare', [3, 15], 'frenzy', 0.75,
    'Ha la forma di un violino e le corde sono i suoi nervi, tesi da una ferita all\'altra. Se lo tiri su troppo in fretta, suonano.', { night: 3 }),
  f('pilota_sanguinante', 'Pilota Sanguinante', 'Bleeding Pilotfish', ['Pesce pilota', 'Pilot fish', 'Naucrates ductor'], 'bleeding', 'rare', [0.2, 1.0], 'frenzy', 0.45,
    'Accompagna sempre qualcuno più grande di lui. Stanotte accompagna qualcuno di molto più grande, e ogni tanto quel qualcuno lo morde.', { near: 'any' }),
  f('remora_strappata', 'Remora Strappata', 'Torn Remora', ['Remora', 'Common remora', 'Remora remora'], 'bleeding', 'rare', [0.2, 1.0], 'frenzy', 0.4,
    'Le remore si attaccano ai grandi animali e viaggiano con loro. Questa è stata strappata via da qualcosa che di notte sale dalla prua, e ha ancora un pezzo di pelle grigia sulla ventosa.', { near: 'gulpy' }),
  f('verdesca_ferita', 'Verdesca Ferita', 'Bruise Shark', ['Verdesca', 'Blue shark', 'Prionace glauca'], 'bleeding', 'legendary', [20, 80], 'frenzy', 0.9,
    'Segue l\'odore del sangue per chilometri. Stanotte l\'ha seguito fino alla barca, e il sangue era il suo.', { night: 4 }),
  f('aguglia_imperiale', 'Aguglia Imperiale Trafitta', 'Impaled Spearfish', ['Aguglia imperiale', 'Mediterranean spearfish', 'Tetrapturus belone'], 'bleeding', 'legendary', [10, 70], 'frenzy', 0.95,
    'Anni fa ha trafitto qualcosa con il rostro, e se l\'è portato dietro. Quella cosa è ancora lì, infilata, e si muove.', { night: 4, lamp: 'bright' }),
  f('volpe_sfregiata', 'Volpe Sfregiata', 'Scarred Thresher', ['Squalo volpe', 'Common thresher', 'Alopias vulpinus'], 'bleeding', 'legendary', [50, 250], 'frenzy', 0.95,
    'Usa la coda lunghissima come una frusta. Ha frustato tante volte, e ha una cicatrice per ogni volta che ha mancato il colpo.', { night: 5 }),
  f('tonno_di_sangue', 'Tonno di Sangue', 'Bloodfin Tuna', ['Tonno rosso', 'Atlantic bluefin tuna', 'Thunnus thynnus'], 'bleeding', 'legendary', [80, 400], 'frenzy', 1.0,
    'Si ricorda tutte le mattanze, una per una. Viene a galla solo quando il mare è rosso, e stanotte, intorno alla barca, lo è.', { night: 5, lamp: 'bright' }),
];

/** I primi cinque renderizzati, uno per famiglia (da approvare). */
export const FISH_PROTOTYPES = ['sgombrato', 'orrata', 'salpa_sfasata', 'trigliocchi', 'barracruda'];

export const FISH_BY_ID: Record<string, FishSpecies> = Object.fromEntries(FISH.map((s) => [s.id, s]));

/** Peso relativo di ogni rarità quando il pesce abbocca. */
export const RARITY_WEIGHT: Record<Rarity, number> = { common: 30, uncommon: 11, rare: 3.5, legendary: 0.6 };
