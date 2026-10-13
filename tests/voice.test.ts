import { describe, expect, it } from 'vitest';
import { syllables } from '../src/engine/voice.ts';

describe('La voce borbottata (radio, conta di Hatch) nelle altre lingue', () => {
  it('in cinese, giapponese e coreano ogni carattere è una sillaba, la punteggiatura larga fa le pause', () => {
    const zh = syllables('你好吗？我饿了。');
    expect(zh.length).toBe(6);
    expect(zh[2]!.pause).toBeCloseTo(0.34);
    expect(syllables('みつけて').map((s) => s.vowel).join('')).toBe('iuee');
    expect(syllables('ガギグゲゴ').map((s) => s.vowel).join('')).toBe('aiueo');
    expect(syllables('배고파').map((s) => s.vowel).join('')).toBe('eoa');
  });

  it('l’italiano e le lingue con l’alfabeto latino come prima', () => {
    expect(syllables('Buona pesca.').length).toBe(4);
    expect(syllables('¡Feliz cumpleaños!').length).toBe(5);
  });

  it('la punteggiatura staccata (francese) non è una sillaba, e un nome latino attaccato all’hangul si dice', () => {
    const fr = syllables('Prêt,\u00a0pas prêt, j’arrive\u00a0!');
    expect(fr.length).toBe(syllables('Prêt, pas prêt, j’arrive!').length);
    expect(fr[fr.length - 1]!.pause).toBeCloseTo(0.34);
    // «Gulpy는»: due sillabe del nome e una della particella
    expect(syllables('Gulpy는').length).toBe(3);
    expect(syllables('Soggy가 와').length).toBe(4);
  });
});
