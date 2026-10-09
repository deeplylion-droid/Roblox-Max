/** Salvataggio locale: progressi, diario, catalogo e opzioni. */
import type { Lang } from '../i18n.ts';

export interface Options {
  master: number;
  music: number;
  sfx: number;
  brightness: number;
  subtitles: boolean;
  reduceFlash: boolean;
  /** velocità di rotazione dello sguardo */
  sensitivity: number;
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
}

const KEY = 'splashland.save.v1';

export function defaultOptions(): Options {
  return { master: 0.9, music: 0.7, sfx: 0.9, brightness: 1, subtitles: true, reduceFlash: false, sensitivity: 1 };
}

function fresh(): SaveData {
  return { version: 1, lang: null, night: 1, lore: [], catalog: {}, options: defaultOptions() };
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
