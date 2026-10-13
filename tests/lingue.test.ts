import { describe, expect, it } from 'vitest';
import { FISH } from '../src/game/catalog.ts';
import { LANGS, LORE_TEXT, RADIO, RADIO_FINALE, STRINGS, testiPesce, type Lang } from '../src/i18n.ts';

// le lingue tradotte il 13 ottobre (docs/LOCALIZZAZIONE.md): ogni testo dell'italiano c'è, ai suoi tempi e al suo posto
const NUOVE = ['es', 'fr', 'de', 'pt', 'zh', 'ja', 'ko'] as const;

/** Le foglie di un oggetto di testi: [percorso, valore] (le funzioni si chiamano con un nome di prova). */
function foglie(v: unknown, path = ''): [string, string][] {
  if (typeof v === 'string') return [[path, v]];
  if (typeof v === 'function') return [[path, String((v as (a: string) => unknown)('Gulpy'))]];
  if (Array.isArray(v)) return v.flatMap((x, i) => foglie(x, `${path}[${i}]`));
  if (v && typeof v === 'object') return Object.entries(v).flatMap(([k, x]) => foglie(x, path ? `${path}.${k}` : k));
  return [[path, String(v)]];
}

describe('Le lingue del gioco', () => {
  it('ci sono tutte e nove, nell’ordine del pulsante delle opzioni', () => {
    expect(LANGS).toEqual(['it', 'en', ...NUOVE]);
  });

  it('l’interfaccia: ogni testo che l’italiano ha, ogni lingua ce l’ha (non vuoto), con lo stesso numero di voci', () => {
    const it = new Map(foglie(STRINGS.it));
    for (const l of NUOVE) {
      const t = new Map(foglie(STRINGS[l]));
      expect([...t.keys()].sort(), l).toEqual([...it.keys()].sort());
      // vuoti apposta: am (solo l'inglese ha le 12 ore), pageAbbr (in cinese il numero di pagina va da solo)
      for (const [k, v] of it) if (v.trim() && k !== 'am' && k !== 'pageAbbr') expect(t.get(k)!.trim(), `${l} ${k}`).not.toBe('');
    }
  });

  it('i segnaposto restano ({n}, {h}, {who} e i tasti del controller come {RT}), e così i nomi propri', () => {
    const segni = (s: string) => (s.match(/\{[A-Za-z]+\}/g) ?? []).sort();
    const NOMI = ['Gulpy', 'Molly', 'Hatch', 'Robin', 'Archie', 'Lampy', 'Fangy', 'Mama Marina', 'Splashland'];
    const it = new Map(foglie(STRINGS.it));
    for (const l of NUOVE) {
      const t = new Map(foglie(STRINGS[l]));
      for (const [k, v] of it) {
        const x = t.get(k) ?? '';
        expect(segni(x), `${l} ${k}`).toEqual(segni(v));
        for (const n of NOMI) if (v.includes(n)) expect(x, `${l} ${k}: ${n}`).toContain(n);
      }
    }
  });

  it('i nomi che non si traducono restano: il titolo e il nome nei titoli di coda', () => {
    for (const l of LANGS) {
      expect(STRINGS[l].title, l).toBe('SPLASHLAND IS CLOSED!');
      expect(STRINGS[l].credits.map((c) => c[1]), l).toEqual(['Ettore Canu']);
    }
  });

  it('il Diario: tutte le voci, con titolo e testo', () => {
    const keys = Object.keys(LORE_TEXT.it).sort();
    for (const l of LANGS) {
      expect(Object.keys(LORE_TEXT[l]).sort(), l).toEqual(keys);
      for (const k of keys) {
        expect(LORE_TEXT[l][k]!.title.trim(), `${l} ${k}`).not.toBe('');
        expect(LORE_TEXT[l][k]!.body.trim(), `${l} ${k}`).not.toBe('');
      }
    }
  });

  it('la radio: le stesse battute agli stessi tempi, parlate dove parla l’italiano', () => {
    const tutte = [...Object.values(RADIO), RADIO_FINALE];
    for (const notte of tutte) {
      for (const l of LANGS) {
        expect(notte[l].map((r) => r.at), l).toEqual(notte.it.map((r) => r.at));
        notte.it.forEach((r, i) => expect(notte[l][i]!.text.trim() === '', `${l} riga ${i}`).toBe(r.text.trim() === ''));
      }
    }
  });

  it('il Catalogo: nome, specie vera e descrizione di tutti i cento pesci in ogni lingua; i nomi non si ripetono', () => {
    for (const l of LANGS as readonly Lang[]) {
      const nomi = new Set<string>();
      for (const f of FISH) {
        const t = testiPesce(f, l);
        expect(t.name.trim() && t.real.trim() && t.desc.trim(), `${l} ${f.id}`).toBeTruthy();
        nomi.add(t.name.toLowerCase());
      }
      expect(nomi.size, l).toBe(FISH.length);
    }
  });

  it('nelle lingue nuove il Catalogo è il loro, non quello inglese', () => {
    for (const l of NUOVE) {
      const diversi = FISH.filter((f) => testiPesce(f, l).desc !== testiPesce(f, 'en').desc).length;
      expect(diversi, l).toBe(FISH.length);
    }
  });
});
