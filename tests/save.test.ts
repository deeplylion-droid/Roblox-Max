import { describe, expect, it, vi } from 'vitest';
import { afterDive, chooseEnding, defaultOptions, fedFor, loadSave, newGame, pendingDawn, skipDawn, wonNight, type SaveData } from '../src/app/save.ts';
import type { MonsterId } from '../src/game/config.ts';
import { extraLevels } from '../src/game/config.ts';

function save(): SaveData {
  return { version: 1, lang: 'it', night: 1, extra: extraLevels(5), lore: [], catalog: {}, options: defaultOptions(), dawn: null, fed: null, dens: [], dawns: {} };
}

describe('Salvataggio: le immersioni all’alba', () => {
  it('il mostro sfamato dorme solo nella notte dopo quell’alba', () => {
    const d = save();
    wonNight(d, 1, 3);
    expect(pendingDawn(d, 2)).toEqual({ night: 1, spare: 3 });
    afterDive(d, 2, { fed: 'gulpy', dens: ['gulpy', 'robin'] });
    expect(fedFor(d, 2)).toBe('gulpy');
    expect(fedFor(d, 3)).toBeNull();
    expect(pendingDawn(d, 2)).toBeNull();
    expect(d.dens).toEqual(['gulpy', 'robin']);
  });

  it('le cose trovate nelle tane vanno nel Diario, una volta sola', () => {
    const d = save();
    d.lore.push('wristband');
    wonNight(d, 1, 1);
    afterDive(d, 2, { fed: null, dens: ['gulpy'], lore: ['den_gulpy'] });
    afterDive(d, 3, { fed: null, dens: ['gulpy'], lore: ['den_gulpy', 'den_molly'] });
    expect(d.lore).toEqual(['wristband', 'den_gulpy', 'den_molly']);
  });

  it('«Nuova partita» azzera il mostro sfamato, l’alba e le tane viste', () => {
    const d = save();
    wonNight(d, 1, 2);
    afterDive(d, 2, { fed: 'gulpy', dens: ['gulpy'] });
    newGame(d);
    expect(d.fed).toBeNull();
    expect(d.dawn).toBeNull();
    expect(d.dens).toEqual([]);
    // rivinta la prima notte senza scendere, nella seconda Gulpy non dorme
    wonNight(d, 1, 0);
    skipDawn(d);
    expect(fedFor(d, 2)).toBeNull();
  });

  it('un’alba senza discesa non eredita il pesce di un’altra alba', () => {
    const d = save();
    wonNight(d, 1, 2);
    afterDive(d, 2, { fed: 'molly', dens: ['molly'] });
    // si torna a giocare la prima notte (Alt + numero, o «?notte=1») e la si vince: il pesce vecchio non vale più
    wonNight(d, 1, 0);
    expect(fedFor(d, 2)).toBeNull();
  });

  it('il mostro sfamato dorme anche se quella notte si perde e si rigioca', () => {
    const d = save();
    wonNight(d, 1, 1);
    afterDive(d, 2, { fed: 'hatch', dens: ['hatch'] });
    // persa la notte 2 non cambia niente: si rigioca con Hatch che dorme
    expect(fedFor(d, 2)).toBe('hatch');
    wonNight(d, 2, 0);
    expect(fedFor(d, 3)).toBeNull();
  });

  it('l’alba resta aperta finché non si scende o si passa alla notte dopo (si riprende da «Continua»)', () => {
    const d = save();
    wonNight(d, 2, 4);
    expect(pendingDawn(d, 3)?.spare).toBe(4);
    expect(pendingDawn(d, 4)).toBeNull();
    skipDawn(d);
    expect(pendingDawn(d, 3)).toBeNull();
  });
});

describe('L’opzione «Nebbia»', () => {
  it('di partenza è spenta, come «Tutorial sempre attivo»', () => {
    expect(defaultOptions().fog).toBe(false);
    expect(defaultOptions().tutorial).toBe(false);
  });

  it('i salvataggi di quando era accesa di partenza la ritrovano spenta; dopo, resta come la si lascia', () => {
    const store = new Map<string, string>();
    vi.stubGlobal('localStorage', { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) });
    try {
      store.set('splashland.save.v1', JSON.stringify({ ...save(), options: { ...defaultOptions(), fog: true } }));
      expect(loadSave().options.fog).toBe(false);
      store.set('splashland.save.v1', JSON.stringify({ ...save(), rev: 1, options: { ...defaultOptions(), fog: true } }));
      expect(loadSave().options.fog).toBe(true);
      expect(loadSave().options.tutorial).toBe(false);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});

/** Gioca le notti 1..5 e a ogni alba scende (lasciando il pesce a `who`, o a nessuno) oppure no. */
function play(d: SaveData, dawns: ('fed' | 'dove' | 'skip')[]): void {
  const who: MonsterId[] = ['gulpy', 'molly', 'hatch', 'robin', 'archie'];
  dawns.forEach((a, i) => {
    const n = i + 1;
    wonNight(d, n, a === 'fed' ? 1 : 0);
    if (a === 'skip') skipDawn(d);
    else afterDive(d, n + 1, { fed: a === 'fed' ? who[i]! : null, dens: [who[i]!] });
  });
}

describe('Il finale della sesta notte', () => {
  it('«I tuoi»: un pesce lasciato a ogni alba, dalla prima alla quinta', () => {
    const d = save();
    play(d, ['fed', 'fed', 'fed', 'fed', 'fed']);
    expect(chooseEnding(d)).toBe('tuoi');
  });

  it('un’alba sola senza pesce (sceso o no) e «I tuoi» non c’è più', () => {
    const a = save();
    play(a, ['fed', 'fed', 'dove', 'fed', 'fed']);
    expect(chooseEnding(a)).toBe('A');
    const b = save();
    play(b, ['fed', 'fed', 'fed', 'fed', 'skip']);
    expect(chooseEnding(b)).toBe('A');
    // la quinta alba non giocata del tutto (manca nel salvataggio)
    const c = save();
    play(c, ['fed', 'fed', 'fed', 'fed']);
    expect(chooseEnding(c)).toBe('A');
  });

  it('«Nessuno»: sceso almeno tre volte, mai un pesce', () => {
    const d = save();
    play(d, ['dove', 'skip', 'dove', 'skip', 'dove']);
    expect(chooseEnding(d)).toBe('nessuno');
    const e = save();
    play(e, ['dove', 'dove', 'dove', 'dove', 'dove']);
    expect(chooseEnding(e)).toBe('nessuno');
  });

  it('sceso due volte sole, o un pesce lasciato anche una volta: il finale A', () => {
    const d = save();
    play(d, ['dove', 'skip', 'dove', 'skip', 'skip']);
    expect(chooseEnding(d)).toBe('A');
    const e = save();
    play(e, ['dove', 'dove', 'fed', 'dove', 'dove']);
    expect(chooseEnding(e)).toBe('A');
  });

  it('mai sceso: il finale A', () => {
    const d = save();
    play(d, ['skip', 'skip', 'skip', 'skip', 'skip']);
    expect(chooseEnding(d)).toBe('A');
    expect(chooseEnding(save())).toBe('A');
  });

  it('rigiocare una notte riscrive la sua alba', () => {
    const d = save();
    play(d, ['fed', 'fed', 'dove', 'fed', 'fed']);
    // si torna alla terza notte, la si rivince e stavolta il pesce lo si lascia
    wonNight(d, 3, 2);
    afterDive(d, 4, { fed: 'robin', dens: ['robin'] });
    expect(chooseEnding(d)).toBe('tuoi');
  });

  it('«Nuova partita» dimentica le albe', () => {
    const d = save();
    play(d, ['fed', 'fed', 'fed', 'fed', 'fed']);
    newGame(d);
    expect(d.dawns).toEqual({});
    expect(chooseEnding(d)).toBe('A');
  });
});
