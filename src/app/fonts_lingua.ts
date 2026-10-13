/**
 * I font del cinese, del giapponese e del coreano (lingue a cui il gioco potrebbe arrivare: scelta dell'utente del 12
 * ottobre sera). Si aggiungono alle famiglie del gioco, Source Serif 4 e Limelight, solo per i loro caratteri
 * (unicode-range) e solo quando la lingua è quella: le regole dei fogli di stile restano come sono. I file sono i
 * sottoinsiemi coi soli caratteri dei testi (tools/fonts/sottoinsieme_cjk.py). Finché una lingua non ha il suo file,
 * il browser usa i font del sistema.
 */

/** i caratteri quadrati: hangul, segni e punteggiatura CJK, kana, ideogrammi, forme larghe */
const CJK_RANGE = 'U+1100-11FF, U+2E80-2FDF, U+3000-303F, U+3040-30FF, U+3130-318F, U+31F0-31FF, U+3400-4DBF, U+4E00-9FFF, U+AC00-D7AF, U+FF00-FFEF';

/** lingua → file del suo sottoinsieme (in public/fonts): si aggiunge quando la lingua ha i suoi testi */
export const CJK_FONTS: Record<string, string> = { zh: 'fonts/cjk-zh.woff2', ja: 'fonts/cjk-ja.woff2', ko: 'fonts/cjk-ko.woff2' };

let active: FontFace[] = [];

/** I font della lingua `lang`: toglie quelli di prima, aggiunge i suoi (se ne ha). */
export function useLangFonts(lang: string, fonts: Record<string, string> = CJK_FONTS): FontFace[] {
  if (typeof document === 'undefined' || typeof FontFace === 'undefined') return [];
  for (const f of active) document.fonts.delete(f);
  active = [];
  const file = fonts[lang];
  if (!file) return active;
  for (const [family, weight] of [
    ['Source Serif 4', '200 900'],
    ['Limelight', '400'],
  ] as const) {
    const f = new FontFace(family, `url(${file})`, { unicodeRange: CJK_RANGE, weight, display: 'block' });
    document.fonts.add(f);
    void f.load().catch(() => {});
    active.push(f);
  }
  return active;
}
