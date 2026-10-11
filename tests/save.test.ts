import { describe, expect, it } from 'vitest';
import { afterDive, defaultOptions, fedFor, newGame, pendingDawn, skipDawn, wonNight, type SaveData } from '../src/app/save.ts';

function save(): SaveData {
  return { version: 1, lang: 'it', night: 1, lore: [], catalog: {}, options: defaultOptions(), dawn: null, fed: null, dens: [] };
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
