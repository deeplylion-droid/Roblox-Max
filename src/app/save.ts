/** Salvataggio locale: progressi, diario, catalogo, immersioni e opzioni. */
import { ARRIVAL, EXTRA_IDS, clampLevel, extraLevels, type ExtraLevels, type MonsterId } from '../game/config.ts';
import type { Lang } from '../i18n.ts';

export interface Options {
  master: number;
  music: number;
  sfx: number;
  brightness: number;
  subtitles: boolean;
  /** didascalie degli eventi e dei suoni («Molly si affaccia», «toc toc sullo scafo»): spente di default */
  captions: boolean;
  reduceFlash: boolean;
  /** velocità di rotazione dello sguardo */
  sensitivity: number;
  /** qualità grafica: frazione della risoluzione a cui si disegna la scena (1 alta, 0,75 media, 0,5 bassa) */
  quality: number;
  /** dimensione dei testi dell'interfaccia: 1 normale, 1,2 grande, 1,4 molto grande (la variabile CSS --ts) */
  textSize: number;
}

export interface CatalogEntry {
  count: number;
  bestKg: number;
}

export interface SaveData {
  version: 1;
  lang: Lang | null;
  /** ultima notte sbloccata */
  night: number;
  /** gli ultimi livelli scelti per la notte extra (la notte 7) */
  extra: ExtraLevels;
  lore: string[];
  catalog: Record<string, CatalogEntry>;
  options: Options;
  /** l'alba dell'ultima notte vinta (immersioni): quanti pesci avanzavano alle sei oltre la quota. Giù se ne porta
   *  uno solo; gli altri restano alla Madre */
  dawn: { night: number; spare: number } | null;
  /** il mostro sfamato all'alba e la notte in cui dorme (anche se quella notte si rigioca, finché non la vinci) */
  fed: { night: number; who: MonsterId } | null;
  /** le tane viste nelle immersioni (anche quelle vuote) */
  dens: MonsterId[];
  /** alba per alba (la chiave è la notte appena vinta, 1..5): se sei sceso e se hai lasciato il pesce a qualcuno.
   *  Decide il finale della sesta notte (chooseEnding). Rigiocando una notte, la sua alba si riscrive */
  dawns: Record<string, DawnRecord>;
}

export interface DawnRecord {
  dove: boolean;
  fed: boolean;
}

/** I finali della sesta notte (docs/NOTTI_E_MOSTRI.md, «I finali»). */
export type Ending = 'tuoi' | 'nessuno' | 'A';

/** Le albe che contano per il finale: dalla prima alla quinta. */
export const ENDING_DAWNS = [1, 2, 3, 4, 5] as const;
/** «Nessuno»: almeno tante discese senza lasciare mai un pesce. */
export const NESSUNO_DIVES = 3;

const isMonster = (x: unknown): x is MonsterId => typeof x === 'string' && Object.hasOwn(ARRIVAL, x);

const KEY = 'splashland.save.v1';

export function defaultOptions(): Options {
  return { master: 0.9, music: 0.7, sfx: 0.9, brightness: 1, subtitles: true, captions: false, reduceFlash: false, sensitivity: 1, quality: 1, textSize: 1 };
}

function fresh(): SaveData {
  return { version: 1, lang: null, night: 1, extra: extraLevels(5), lore: [], catalog: {}, options: defaultOptions(), dawn: null, fed: null, dens: [], dawns: {} };
}

export function loadSave(): SaveData {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return fresh();
    const d = JSON.parse(raw) as Partial<SaveData>;
    const f = fresh();
    return {
      version: 1,
      lang: d.lang === 'it' || d.lang === 'en' ? d.lang : null,
      night: typeof d.night === 'number' ? d.night : 1,
      extra: Object.fromEntries(EXTRA_IDS.map((m) => [m, clampLevel(Number((d.extra as Partial<ExtraLevels> | undefined)?.[m] ?? f.extra[m]))])) as ExtraLevels,
      lore: Array.isArray(d.lore) ? d.lore.filter((x) => typeof x === 'string') : [],
      catalog: d.catalog && typeof d.catalog === 'object' ? d.catalog : {},
      options: { ...f.options, ...(d.options ?? {}) },
      dawn: d.dawn && typeof d.dawn.night === 'number' && typeof d.dawn.spare === 'number' ? { night: d.dawn.night, spare: d.dawn.spare } : null,
      fed: d.fed && typeof d.fed.night === 'number' && isMonster(d.fed.who) ? { night: d.fed.night, who: d.fed.who } : null,
      dens: Array.isArray(d.dens) ? d.dens.filter(isMonster) : [],
      dawns: cleanDawns(d.dawns),
    };
  } catch {
    return fresh();
  }
}

// ───────── le immersioni all'alba nel salvataggio (funzioni pure: l'App le chiama, i test le provano) ─────────

function cleanDawns(x: unknown): Record<string, DawnRecord> {
  const out: Record<string, DawnRecord> = {};
  if (!x || typeof x !== 'object') return out;
  for (const [k, v] of Object.entries(x as Record<string, unknown>)) {
    const r = v as Partial<DawnRecord> | null;
    if (/^\d+$/.test(k) && r && typeof r.dove === 'boolean' && typeof r.fed === 'boolean') out[k] = { dove: r.dove, fed: r.fed && r.dove };
  }
  return out;
}

/** Nuova partita: si riparte senza pesci da portare giù, senza mostri sfamati, senza tane viste e senza albe. */
export function newGame(d: SaveData): void {
  d.dawn = null;
  d.fed = null;
  d.dens = [];
  d.dawns = {};
}

/** Notte vinta: il mostro sfamato ha dormito (o era di un'altra partita): non vale più. Si apre l'alba, con i pesci
 *  avanzati oltre la quota. */
export function wonNight(d: SaveData, night: number, spare: number): void {
  d.night = Math.max(d.night, night + 1);
  d.fed = null;
  d.dawn = { night, spare };
}

/** Il mostro che dorme nella notte `night` (sfamato all'alba prima), se c'è. */
export function fedFor(d: SaveData, night: number): MonsterId | null {
  return d.fed?.night === night ? d.fed.who : null;
}

/** L'alba ancora aperta prima della notte `next` (il gioco chiuso sullo schermo dei risultati): i pesci avanzati. */
export function pendingDawn(d: SaveData, next: number): { night: number; spare: number } | null {
  return d.dawn && d.dawn.night + 1 === next ? d.dawn : null;
}

/** Si passa alla notte dopo senza scendere: il pesce resta alla Madre, l'alba è chiusa (e conta come un'alba senza
 *  discesa). */
export function skipDawn(d: SaveData): void {
  if (d.dawn) d.dawns[String(d.dawn.night)] = { dove: false, fed: false };
  d.dawn = null;
}

/** Risaliti: chi è stato sfamato dorme la notte `next`; le tane viste restano; l'alba è chiusa. */
export function afterDive(d: SaveData, next: number, r: { fed: MonsterId | null; dens: MonsterId[] }): void {
  d.dawns[String(next - 1)] = { dove: true, fed: !!r.fed };
  d.fed = r.fed ? { night: next, who: r.fed } : null;
  for (const m of r.dens) if (!d.dens.includes(m)) d.dens.push(m);
  d.dawn = null;
}

/**
 * Il finale della sesta notte (approvato l'11 ottobre): «I tuoi» se hai lasciato un pesce a qualcuno a ogni alba, dalla
 * prima alla quinta; «Nessuno» se sei sceso almeno tre volte e non hai mai lasciato un pesce; il finale A negli altri
 * casi (anche se non sei mai sceso).
 */
export function chooseEnding(d: Pick<SaveData, 'dawns'>): Ending {
  const ds = ENDING_DAWNS.map((n) => d.dawns[String(n)]);
  if (ds.every((x) => x?.dove && x.fed)) return 'tuoi';
  const dives = ds.filter((x) => x?.dove).length;
  if (dives >= NESSUNO_DIVES && !ds.some((x) => x?.fed)) return 'nessuno';
  return 'A';
}

export function writeSave(d: SaveData): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(d));
  } catch {
    // archiviazione non disponibile (finestra privata): si gioca senza salvare
  }
}
