// Rigenera docs/CATALOGO.md da src/game/catalog.ts (la lista dei pesci da approvare).
// Uso: npm run catalog
import fs from 'node:fs';
import { FISH, FISH_PROTOTYPES, type FishFamily, type FishSpecies, type PullStyle, type Rarity } from '../src/game/catalog.ts';

const FAMILY: Record<FishFamily, [string, string]> = {
  skeletal: ['Scheletrici', 'carne mancante, lisca e cranio in vista. Nomi: il nome vero fuso con *osso*, *lisca*, *teschio*.'],
  zombie: ['Zombi', 'marci, occhi lattiginosi, pinne strappate, punti di sutura. Nomi: giochi di parole con la morte e la sepoltura.'],
  glitch: ['Glitchati', 'fette sfalsate, colori separati, come un nastro VHS rovinato. Nomi: il nome vero più un difetto del video (*sfasata*, *riavvolto*, *senza segnale*…).'],
  corrupt: ['Corrotti', 'occhi in più, bocche sbagliate, escrescenze, melma nera. Nomi: il nome vero storpiato verso *mostro*, *incubo*, *pece*.'],
  bleeding: ['Sanguinanti', 'ferite, denti sporchi, colature. Nomi: tagli, morsi e sangue.'],
};
const RARITY: Record<Rarity, string> = { common: 'comune', uncommon: 'non comune', rare: 'raro', legendary: 'leggendario' };
const PULL: Record<PullStyle, string> = {
  darts: 'strattoni brevi', dead: 'fa il morto, poi strattona', leaps: 'salta e scuote la testa', glitch: 'tensione che salta e sparisce',
  heavy: 'tira giù, pesante', bottom: 'si pianta sul fondo', frenzy: 'strattoni violenti e continui',
};
const kg = (n: number) => (n < 1 ? n.toFixed(n < 0.01 ? 3 : 2) : String(n)).replace('.', ',');
function when(s: FishSpecies): string {
  const w = s.when ?? {};
  const out: string[] = [];
  out.push(w.night && w.night > 1 ? `dalla notte ${w.night}` : 'dalla notte 1');
  if (w.lamp === 'dark') out.push('solo a lampara spenta');
  if (w.lamp === 'bright') out.push('solo a lampara al massimo');
  if (w.from) out.push(`dopo le ${w.from}:00`);
  if (w.near === 'any') out.push('solo con una creatura vicina');
  else if (w.near) out.push(`solo con ${w.near[0]!.toUpperCase() + w.near.slice(1)} vicino`);
  return out.join(', ');
}

const lines: string[] = [];
lines.push('# SPLASHLAND IS CLOSED! — Il Catalogo dei pesci');
lines.push('');
lines.push('> ⚠️ **PROPOSTA DA APPROVARE.** Nomi, descrizioni, rarità e condizioni sono una bozza scritta di notte: si cambia tutto quello che non convince. Il file si rigenera da `src/game/catalog.ts` con `npm run catalog`.');
lines.push('');
lines.push('Cento specie, tutte ispirate a pesci veri del Mediterraneo e degli abissi, venti per famiglia. Ogni voce ha il nome italiano e quello inglese (un gioco di parole diverso per ogni lingua), la specie vera, la rarità, quando abbocca, come combatte al recupero, il peso e una riga inquietante. Le descrizioni inglesi si scrivono dopo l\'approvazione (per ora ci sono solo per i 5 prototipi).');
lines.push('');
const counts = { common: 0, uncommon: 0, rare: 0, legendary: 0 } as Record<Rarity, number>;
for (const s of FISH) counts[s.rarity]++;
const night1 = FISH.filter((s) => !s.when?.night || s.when.night <= 1).length;
lines.push(`Rarità: ${counts.common} comuni, ${counts.uncommon} non comuni, ${counts.rare} rari, ${counts.legendary} leggendari. Nella Notte 1 possono abboccare ${night1} specie; le altre arrivano nelle notti successive.`);
lines.push('');
lines.push(`**Prototipi renderizzati** (uno per famiglia): ${FISH_PROTOTYPES.map((id) => FISH.find((s) => s.id === id)!.name.it).join(', ')} — immagini in \`docs/concept/pesci/\`.`);
lines.push('');
let n = 0;
for (const fam of Object.keys(FAMILY) as FishFamily[]) {
  const [title, about] = FAMILY[fam];
  lines.push(`## ${title}`);
  lines.push('');
  lines.push(`*${about}*`);
  lines.push('');
  for (const s of FISH.filter((x) => x.family === fam)) {
    n++;
    const proto = FISH_PROTOTYPES.includes(s.id) ? ' · 🎨 prototipo' : '';
    lines.push(`### ${n}. ${s.name.it} · *${s.name.en}*${proto}`);
    lines.push(`${s.real.it} / ${s.real.en} (*${s.real.sci}*) · **${RARITY[s.rarity]}** · ${kg(s.kg[0])}–${kg(s.kg[1])} kg · ${PULL[s.pull]} · ${when(s)}`);
    lines.push('');
    lines.push(`> ${s.desc.it}`);
    if (s.desc.en) lines.push(`>\n> *${s.desc.en}*`);
    lines.push('');
  }
}
fs.writeFileSync(new URL('../docs/CATALOGO.md', import.meta.url), lines.join('\n'));
console.log(`docs/CATALOGO.md: ${FISH.length} pesci`);
