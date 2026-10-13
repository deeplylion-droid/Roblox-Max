import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

// la sagoma nella nebbia (un falso allarme, 13 ottobre): lo strato reso da tools/render/scena_creature.py
const man = JSON.parse(readFileSync('public/assets/img/manifest.json', 'utf8'));
const main = readFileSync('src/main.ts', 'utf8');

describe('La sagoma nella nebbia', () => {
  it('è uno strato del mondo, coi suoi file, senza occhi che brillano', () => {
    const l = man.layers.sagoma_nebbia;
    expect(l.space).toBe('world');
    expect(l.eyes).toBeUndefined();
    for (const p of Object.values(l.passes) as { file: string }[]) expect(existsSync(`public/assets/img/${p.file}`), p.file).toBe(true);
  });

  it('il gioco la carica', () => {
    expect(main).toContain("'sagoma_nebbia'");
  });
});
