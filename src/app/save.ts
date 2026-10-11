/** Salvataggio locale: progressi, diario, catalogo, immersioni e opzioni. */
import { ARRIVAL, type MonsterId } from '../game/config.ts';
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
}

const isMonster = (x: unknown): x is MonsterId => typeof x === 'string' && x in ARRIVAL;

const KEY = 'splashland.save.v1';

export function defaultOptions(): Options {
  return { master: 0.9, music: 0.7, sfx: 0.9, brightness: 1, subtitles: true, captions: false, reduceFlash: false, sensitivity: 1, quality: 1 };
}

function fresh(): SaveData {
  return { version: 1, lang: null, night: 1, lore: [], catalog: {}, options: defaultOptions(), dawn: null, fed: null, dens: [] };
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
      lore: Array.isArray(d.lore) ? d.lore.filter((x) => typeof x === 'string') : [],
      catalog: d.catalog && typeof d.catalog === 'object' ? d.catalog : {},
      options: { ...f.options, ...(d.options ?? {}) },
      dawn: d.dawn && typeof d.dawn.night === 'number' && typeof d.dawn.spare === 'number' ? { night: d.dawn.night, spare: d.dawn.spare } : null,
      fed: d.fed && typeof d.fed.night === 'number' && isMonster(d.fed.who) ? { night: d.fed.night, who: d.fed.who } : null,
      dens: Array.isArray(d.dens) ? d.dens.filter(isMonster) : [],
    };
  } catch {
    return fresh();
  }
}

export function writeSave(d: SaveData): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(d));
  } catch {
    // archiviazione non disponibile (finestra privata): si gioca senza salvare
  }
}
