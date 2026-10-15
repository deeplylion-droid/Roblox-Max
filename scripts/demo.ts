/**
 * La demo leggera (14 ottobre, per la demo su itch.io e su Steam). La build con VITE_ULTIMA_NOTTE (la demo: 2) prima
 * portava con sé tutto il gioco, fermato solo dal codice: chi smontava il programma poteva giocarlo intero, o vedere i
 * mostri e i finali. Adesso, a build finita (vite.config.ts), dai manifest di dist/ si tolgono le voci delle notti dopo
 * l'ultima: i mostri che arrivano dopo (strati, jumpscare, tane, ritratti, suoni), la Madre della sesta notte, i finali,
 * i disegni delle albe dopo e le schede della notte extra. Poi se ne cancellano i file, se nessuna voce rimasta li usa.
 *
 * Della Madre restano il jumpscare `js_madre` e la musica `mus_madre`: servono già nelle prime notti (la quota
 * mancata, la canzone finita al buio). Le tane dei mostri che non sono ancora arrivati il gioco non le apre: si
 * possono togliere.
 */
import fs from 'node:fs';
import path from 'node:path';

/** La notte in cui arriva ogni mostro: come ARRIVAL in src/game/config.ts (un test controlla che siano uguali). */
export const ARRIVO: Record<string, number> = { gulpy: 1, molly: 1, hatch: 1, robin: 2, archie: 3, lampy: 4, fangy: 5 };
/** La notte della Madre e dei finali. */
export const NOTTE_MADRE = 6;
/** La notte extra (le schede coi livelli). */
export const NOTTE_EXTRA = 7;
/** Il disegno dell'alba di ogni notte: come DISEGNI_ALBA in src/app/disegni.ts (un test controlla). */
export const DISEGNI: Record<number, string> = { 1: 'piscina', 2: 'tesoro', 3: 'compleanno', 4: 'sottacqua', 5: 'marcopolo' };

type Obj = Record<string, unknown>;

/** I manifest che il gioco legge, come stanno in assets/. */
export interface Manifesti {
  /** img/manifest.json: gli strati della notte */
  img: Obj & { layers: Obj };
  /** img/overlays.json: binocolo, telone, jumpscare, finali */
  overlays: Obj & { jumpscares?: Obj; endings?: Obj };
  /** img/immersioni.json: i posti delle immersioni, con le tane */
  immersioni: Obj & { places: Record<string, Obj & { den?: string }> };
  /** audio/manifest.json: i suoni */
  audio: Obj;
}

export interface Piano {
  /** i manifest senza le voci delle notti dopo */
  manifesti: Manifesti;
  /** i file da cancellare, rispetto ad assets/ */
  via: string[];
}

/** I file nominati dentro un valore JSON (le stringhe con l'estensione di un'immagine, di un suono o di un JSON). */
export function fileIn(x: unknown, out = new Set<string>()): Set<string> {
  if (typeof x === 'string') {
    if (/\.(webp|png|jpe?g|ogg|opus|mp3|wav|json)$/i.test(x)) out.add(x);
  } else if (Array.isArray(x)) {
    for (const v of x) fileIn(v, out);
  } else if (x && typeof x === 'object') {
    for (const v of Object.values(x)) fileIn(v, out);
  }
  return out;
}

/** Toglie da `o` le chiavi per cui `via` è vero; i file che quelle voci nominano (con `dir` davanti) vanno in `tolti`. */
function togli(o: Obj | undefined, via: (k: string, v: unknown) => boolean, dir: string, tolti: Set<string>): Obj {
  const resta: Obj = {};
  for (const [k, v] of Object.entries(o ?? {})) {
    if (via(k, v)) for (const f of fileIn(v)) tolti.add(dir + f);
    else resta[k] = v;
  }
  return resta;
}

/**
 * Il piano della demo fino alla notte `ultima`: i manifest senza le voci delle notti dopo e i file da cancellare.
 * `file` sono tutti i file di assets/ (per i ritratti, le schede e i disegni, che non stanno nei manifest).
 */
export function pianoDemo(m: Manifesti, ultima: number, file: readonly string[]): Piano {
  const dopo = Object.keys(ARRIVO).filter((k) => ARRIVO[k]! > ultima);
  const senzaMadre = ultima < NOTTE_MADRE;
  const senzaExtra = ultima < NOTTE_EXTRA;
  const deiDopo = (k: string) => dopo.some((who) => k.startsWith(who + '_')) || (senzaMadre && k.startsWith('madre_'));
  const tolti = new Set<string>();

  const img = { ...m.img, layers: togli(m.img.layers, deiDopo, 'img/', tolti) };
  const overlays = {
    ...m.overlays,
    // il jumpscare della quota mancata resta: c'è dalla prima notte
    jumpscares: togli(m.overlays.jumpscares, (k) => dopo.includes(k) || (senzaMadre && k === 'madre'), 'img/', tolti),
    endings: togli(m.overlays.endings, () => senzaMadre, 'img/', tolti),
  };
  const places = togli(m.immersioni.places, (_k, v) => dopo.includes(String((v as { den?: string }).den)), 'img/', tolti);
  const immersioni = { ...m.immersioni, places: places as Manifesti['immersioni']['places'] };
  // i suoni dei mostri che arrivano dopo (le loro voci, il jumpscare, il sonno e il risveglio nella tana), della Madre
  // (tranne js_madre e mus_madre, che non cominciano con «madre_») e dei finali
  const suonoDopo = (k: string) =>
    deiDopo(k) || dopo.some((who) => k === `js_${who}` || k === `sleep_${who}` || k === `stir_${who}`) || (senzaMadre && k.startsWith('finale_'));
  const audio = togli(m.audio, suonoDopo, 'audio/', tolti);
  const manifesti: Manifesti = { img, overlays, immersioni, audio };

  // i file che le voci rimaste usano ancora non si toccano
  const usati = new Set<string>();
  for (const f of fileIn(img)) usati.add('img/' + f);
  for (const f of fileIn(overlays)) usati.add('img/' + f);
  for (const f of fileIn(immersioni)) usati.add('img/' + f);
  for (const f of fileIn(audio)) usati.add('audio/' + f);
  const via = new Set([...tolti].filter((f) => !usati.has(f)));

  // fuori dai manifest: i ritratti del menu dei mostri che arrivano dopo, le schede della notte extra, i disegni
  // delle albe dopo l'ultima (con le versioni per lingua)
  const disegniDopo = Object.entries(DISEGNI)
    .filter(([n]) => Number(n) > ultima)
    .map(([, id]) => id);
  for (const f of file) {
    const nome = f.split('/').pop()!;
    if (f.startsWith('img/ritratti/') && dopo.some((who) => nome === `${who}.webp` || nome.startsWith(`${who}_`))) via.add(f);
    if (f.startsWith('img/schede/') && senzaExtra) via.add(f);
    if (f.startsWith('img/disegni/') && disegniDopo.some((id) => nome === `pastelli_${id}.webp` || nome.startsWith(`pastelli_${id}_`))) via.add(f);
  }
  return { manifesti, via: [...via].filter((f) => file.includes(f)).sort() };
}

/** Tutti i file sotto `dir`, rispetto a `dir`, con le barre «/». */
export function elenco(dir: string, sotto = ''): string[] {
  const out: string[] = [];
  for (const e of fs.readdirSync(path.join(dir, sotto), { withFileTypes: true })) {
    const rel = sotto ? `${sotto}/${e.name}` : e.name;
    if (e.isDirectory()) out.push(...elenco(dir, rel));
    else out.push(rel);
  }
  return out;
}

/** Alleggerisce la build in `dist` per la demo fino alla notte `ultima`: riscrive i manifest e cancella i file. */
export function alleggerisci(dist: string, ultima: number): { file: number; byte: number } {
  const A = path.join(dist, 'assets');
  const leggi = (f: string) => JSON.parse(fs.readFileSync(path.join(A, f), 'utf8'));
  const p = pianoDemo(
    { img: leggi('img/manifest.json'), overlays: leggi('img/overlays.json'), immersioni: leggi('img/immersioni.json'), audio: leggi('audio/manifest.json') },
    ultima,
    elenco(A),
  );
  const scrivi = (f: string, x: unknown) => fs.writeFileSync(path.join(A, f), JSON.stringify(x));
  scrivi('img/manifest.json', p.manifesti.img);
  scrivi('img/overlays.json', p.manifesti.overlays);
  scrivi('img/immersioni.json', p.manifesti.immersioni);
  scrivi('audio/manifest.json', p.manifesti.audio);
  let byte = 0;
  for (const f of p.via) {
    byte += fs.statSync(path.join(A, f)).size;
    fs.unlinkSync(path.join(A, f));
  }
  return { file: p.via.length, byte };
}
