import { describe, expect, it } from 'vitest';
import { DISEGNI_ALBA, disegnoAlba, disegnoSrc, disegniTrovati } from '../src/app/disegni.ts';
import { decimal, localizedImage } from '../src/i18n.ts';

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

  it('in inglese, i disegni con le scritte tradotte; Marco Polo vale per tutte le lingue', () => {
    expect(disegnoSrc('piscina', 'en')).toBe('assets/img/disegni/pastelli_piscina_en.webp');
    expect(disegnoSrc('compleanno', 'en')).toBe('assets/img/disegni/pastelli_compleanno_en.webp');
    expect(disegnoSrc('marcopolo', 'en')).toBe('assets/img/disegni/pastelli_marcopolo.webp');
    expect(disegnoSrc('piscina', 'it')).toBe('assets/img/disegni/pastelli_piscina.webp');
  });
});

describe('Le immagini con scritte nelle lingue del gioco', () => {
  it('la versione della lingua; se manca, quella inglese; se manca anche quella, l’originale', () => {
    expect(localizedImage('a/b.webp', 'it', ['en', 'de'])).toBe('a/b.webp');
    expect(localizedImage('a/b.webp', 'de', ['en', 'de'])).toBe('a/b_de.webp');
    expect(localizedImage('a/b.webp', 'fr', ['en'])).toBe('a/b_en.webp');
    expect(localizedImage('a/b.webp', 'fr', [])).toBe('a/b.webp');
  });

  it('i decimali: la virgola in italiano e nelle lingue europee, il punto in inglese e nelle lingue asiatiche', () => {
    expect(decimal('2.4', 'it')).toBe('2,4');
    expect(decimal('0.07', 'de')).toBe('0,07');
    expect(decimal('2.4', 'en')).toBe('2.4');
    expect(decimal('2.4', 'ja')).toBe('2.4');
  });
});
