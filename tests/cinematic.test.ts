import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { FINALE_A, FINALE_B, FINALE_NESSUNO, FINALE_TUOI, stillFrame, textAt, type CinematicScript } from '../src/app/cinematic.ts';
import { LANGS, STRINGS } from '../src/i18n.ts';

const audio = JSON.parse(readFileSync('public/assets/audio/manifest.json', 'utf8')) as Record<string, { duration: number }>;
const overlays = JSON.parse(readFileSync('public/assets/img/overlays.json', 'utf8')) as { endings?: Record<string, unknown> };
const SCRIPTS: Record<string, CinematicScript> = { A: FINALE_A, tuoi: FINALE_TUOI, nessuno: FINALE_NESSUNO, B: FINALE_B };

describe('Le cinematiche dei finali', () => {
  for (const [name, s] of Object.entries(SCRIPTS)) {
    it(`${name}: chiavi in ordine, dentro la durata, suoni che esistono`, () => {
      const tracks = [s.view, s.dawn, s.lamp, s.tilt, s.black, s.still?.move, ...Object.values(s.creatures ?? {})].filter((x) => !!x);
      for (const keys of tracks) {
        for (let i = 1; i < keys!.length; i++) expect(keys![i]!.t).toBeGreaterThanOrEqual(keys![i - 1]!.t);
        expect(keys![keys!.length - 1]!.t).toBeLessThanOrEqual(s.length);
      }
      for (const x of s.sounds ?? []) expect(audio[x.id], x.id).toBeDefined();
      // brevi, come deciso l'11 ottobre (15-20 s, poco di più con l'ultima inquadratura)
      expect(s.length).toBeGreaterThanOrEqual(15);
      expect(s.length).toBeLessThanOrEqual(22);
    });
  }

  it('i finali segreti e il finale B finiscono sull’ultima inquadratura renderizzata (i segreti con la frase)', () => {
    for (const [s, key] of [[FINALE_TUOI, 'molo'], [FINALE_NESSUNO, 'edicola'], [FINALE_B, 'ricordo']] as const) {
      expect(overlays.endings?.[key], key).toBeDefined();
      expect(stillFrame(s, s.still!.t - 0.01)).toBeNull();
      const end = stillFrame(s, s.length)!;
      expect(end.key).toBe(key);
      expect(end.alpha).toBe(1);
      // il movimento di camera è lento: al più un terzo di zoom in tutta l'inquadratura (il disegno del finale B
      // un po' di più, fino ai quattro bambini)
      expect(end.zoom).toBeGreaterThan(1);
      expect(end.zoom).toBeLessThanOrEqual(key === 'ricordo' ? 1.6 : 1.35);
      // il finale B non ha frase (scelta dell'utente, 12 ottobre): solo il disegno e il nero
      if (key === 'ricordo') {
        expect(s.text ?? []).toHaveLength(0);
        continue;
      }
      const line = s.text![0]!;
      expect(line.t).toBeGreaterThan(s.still!.t);
      for (const lang of LANGS) expect(textAt(s, line.t + 0.1, lang)).toBe(STRINGS[lang][line.key]);
    }
  });

  it('«Nessuno»: il taglio sull’edicola arriva quando lo vuole il suono (15 s), nel buio', () => {
    const s = FINALE_NESSUNO;
    expect(s.still!.t).toBe(15);
    expect(s.still!.fade).toBe(0);
    expect(s.events?.some((e) => e.e === 'quiet' && e.t === 15)).toBe(true);
  });

  it('il finale B: come il finale A fino al secchio vuoto, senza la radio, e il disegno arriva in dissolvenza', () => {
    const s = FINALE_B;
    expect(s.view.slice(0, 6)).toEqual(FINALE_A.view.slice(0, 6));
    expect(s.events?.some((e) => e.e === 'emptyBucket')).toBe(true);
    expect(s.events?.some((e) => e.e === 'radio')).toBe(false);
    expect(s.still!.fade).toBeGreaterThan(0);
    expect(stillFrame(s, s.still!.t + s.still!.fade / 2)!.alpha).toBeLessThan(1);
  });
});
