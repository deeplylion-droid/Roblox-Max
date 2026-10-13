import { describe, expect, it } from 'vitest';
import { STRINGS } from '../src/i18n.ts';
import { etichetta, tastiText, tasto } from '../src/app/tastiera.ts';

/** Un tasto premuto: dove sta (`code`) e cosa scrive (`key`). */
const ev = (code: string, key: string, mod: Partial<KeyboardEvent> = {}) =>
  ({ code, key, ctrlKey: false, altKey: false, metaKey: false, ...mod }) as unknown as KeyboardEvent;

// l'ordine conta: le lettere dei tasti si imparano premendoli
describe('La tastiera (tastiera.ts)', () => {
  it('senza notizie sulla tastiera, i suggerimenti dicono le lettere americane', () => {
    expect(tastiText(STRINGS.it.look)).toContain(' W A S D ');
    expect(tastiText(STRINGS.it.lampHint)).toBe('Q/E o rotella: luce');
    expect(tastiText(STRINGS.it.hints.archie)).toBe('Archie prende fiato: spegni la luce (Q)');
  });

  it('americana: tutto come prima', () => {
    expect(tasto(ev('KeyW', 'w'))).toBe('w');
    expect(tasto(ev('KeyQ', 'Q', { shiftKey: true }))).toBe('q');
    expect(tasto(ev('KeyF', 'f'))).toBe('f');
    expect(tasto(ev('Space', ' '))).toBe(' ');
    expect(tasto(ev('Tab', 'Tab'))).toBe('tab');
    expect(tasto(ev('ArrowLeft', 'ArrowLeft'))).toBe('arrowleft');
    expect(tasto(ev('ControlLeft', 'Control'))).toBe('control');
  });

  it('francese (AZERTY): W A S D e Q E per dove stanno, gli altri per la lettera', () => {
    expect(tasto(ev('KeyW', 'z'))).toBe('w');
    expect(tasto(ev('KeyA', 'q'))).toBe('a');
    expect(tasto(ev('KeyQ', 'a'))).toBe('q');
    expect(tasto(ev('KeyE', 'e'))).toBe('e');
    expect(tasto(ev('KeyS', 's'))).toBe('s');
    expect(tasto(ev('KeyD', 'd'))).toBe('d');
    // la W sta dove l'americana ha la Z: non volta verso prua
    expect(tasto(ev('KeyZ', 'w'))).toBe('');
    expect(tasto(ev('KeyC', 'c'))).toBe('c');
    expect(tasto(ev('KeyB', 'b'))).toBe('b');
    expect(tasto(ev('KeyM', ','))).toBe(',');
  });

  it('i suggerimenti dicono le lettere della tastiera di chi gioca', () => {
    expect(tastiText(STRINGS.fr.look)).toContain(' Z Q S D ');
    expect(tastiText(STRINGS.fr.lampHint)).toBe('A/E ou molette : lampe');
    expect(tastiText(STRINGS.fr.hints.archie)).toBe('Archie inspire : éteins la lampe (A)');
    expect(tastiText(STRINGS.fr.hints.robin)).toBe('Robin : lampe à fond (E)');
    // con un modificatore (AltGr, Ctrl…) il tasto non insegna niente
    tasto(ev('KeyE', '€', { ctrlKey: true, altKey: true }));
    expect(etichetta('KeyE')).toBe('E');
  });

  it('una tastiera che non scrive in latino o il metodo di scrittura: vale la lettera stampata sul tasto', () => {
    expect(tasto(ev('KeyF', 'а'))).toBe('f');
    expect(tasto(ev('KeyW', 'ц'))).toBe('w');
    expect(etichetta('KeyW')).toBe('W');
    expect(tasto(ev('KeyB', 'Process'))).toBe('b');
    // un tasto finto senza posto (le prove automatiche): la lettera
    expect(tasto(ev('', 'w'))).toBe('w');
  });

  it('ogni lingua mette i tasti a posizione fissa coi segnaposto, non con le lettere', () => {
    for (const s of Object.values(STRINGS)) {
      for (const t of [s.look, s.lampHint, s.hints.robin, s.hints.archie, s.hints.turn]) expect(t).toMatch(/\{Key[WASDQE]\}/);
    }
  });
});
