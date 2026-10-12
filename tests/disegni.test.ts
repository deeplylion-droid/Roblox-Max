import { describe, expect, it } from 'vitest';
import { DISEGNI_ALBA, disegnoAlba, disegnoSrc, disegniTrovati } from '../src/app/disegni.ts';

describe('I disegni a pastelli dell’alba', () => {
  it('uno per notte, dalla prima alla quinta; la sesta e la notte extra non ne lasciano', () => {
    expect(Object.keys(DISEGNI_ALBA).map(Number)).toEqual([1, 2, 3, 4, 5]);
    expect(disegnoAlba(1)).toBe('piscina');
    expect(disegnoAlba(5)).toBe('marcopolo');
    expect(disegnoAlba(6)).toBeNull();
    expect(disegnoAlba(7)).toBeNull();
  });

  it('nel Diario ci sono quelli delle notti vinte, in ordine', () => {
    expect(disegniTrovati(1)).toEqual([]);
    expect(disegniTrovati(3)).toEqual(['piscina', 'tesoro']);
    expect(disegniTrovati(7)).toEqual(['piscina', 'tesoro', 'compleanno', 'sottacqua', 'marcopolo']);
  });

  it('i file stanno in assets/img/disegni', () => {
    expect(disegnoSrc('piscina')).toBe('assets/img/disegni/pastelli_piscina.webp');
  });
});
