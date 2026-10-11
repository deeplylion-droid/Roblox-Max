/**
 * Bilanciamento: fa giocare la notte a bot di diversa abilità e riassume i risultati.
 * Uso: node scripts/balance.ts [notte] [partite] [--sfama]
 *
 * Con --sfama si vede l'effetto delle immersioni all'alba (docs/IMMERSIONI.md): per ogni abilità il bot gioca la
 * notte una volta senza aiuti, trova il mostro che lo uccide più spesso fra quelli che si possono sfamare (il nuovo
 * della notte no: la sua tana è vuota; se non lo uccide nessun mostro, Gulpy, che si mangia i pesci) e la rigioca con quel mostro sfamato, che dorme tutta la notte.
 */
import { NIGHTS, canFeed, type MonsterId } from '../src/game/config.ts';
import { NightSim } from '../src/game/sim.ts';
import { SKILLS, playNight } from '../src/game/bot.ts';

const args = process.argv.slice(2).filter((a) => !a.startsWith('--'));
const sfama = process.argv.includes('--sfama');
const night = Number(args[0] ?? 1);
const games = Number(args[1] ?? 300);
const cfg = NIGHTS[night];
if (!cfg) throw new Error(`notte ${night} non configurata`);

console.log(`Notte ${night} · quota ${cfg.quota} · ${games} partite per abilità${sfama ? ' · con il mostro più letale sfamato all’alba' : ''}\n`);

/** Gioca le partite di un'abilità e ne stampa il riassunto; restituisce i morti per mostro. */
function play(skill: (typeof SKILLS)[string], fed: MonsterId | null, label: string): Record<string, number> {
  let wins = 0;
  const deaths: Record<string, number> = {};
  const deathHour: number[] = [];
  let fishSum = 0;
  let fedSum = 0;
  let caughtSum = 0;
  let loreSum = 0;
  for (let seed = 1; seed <= games; seed++) {
    const sim = playNight(new NightSim(cfg!, seed * 7919, [], { fed }), skill, seed);
    fishSum += sim.fish;
    fedSum += sim.fed;
    caughtSum += sim.caught;
    loreSum += sim.loreThisNight.length;
    if (sim.outcome.kind === 'won') wins++;
    else if (sim.outcome.kind === 'dead') {
      deaths[sim.outcome.killer] = (deaths[sim.outcome.killer] ?? 0) + 1;
      deathHour.push(sim.hour);
    }
  }
  const pct = (n: number) => `${((100 * n) / games).toFixed(1)}%`;
  const avgHour = deathHour.length ? (deathHour.reduce((a, b) => a + b, 0) / deathHour.length).toFixed(1) : '-';
  console.log(
    `${label.padEnd(8)} vittorie ${pct(wins).padStart(6)} · morti ${JSON.stringify(deaths)} (ora media ${avgHour})` +
      ` · pescati ${(caughtSum / games).toFixed(1)} · dati a Gulpy ${(fedSum / games).toFixed(1)} · nel secchio ${(fishSum / games).toFixed(1)} · lore ${(loreSum / games).toFixed(2)}`,
  );
  return deaths;
}

for (const skill of Object.values(SKILLS)) {
  const deaths = play(skill, null, skill.name);
  if (!sfama) continue;
  // il mostro che uccide più spesso fra quelli che si possono sfamare stanotte
  const best = (Object.entries(deaths) as [string, number][])
    .filter(([m]) => m !== 'mother' && canFeed(night, m as MonsterId))
    .sort((a, b) => b[1] - a[1])[0];
  // se non lo uccide nessun mostro (solo la quota mancata, o niente), sfama Gulpy: è lui che si mangia i pesci
  const fed = (best?.[0] as MonsterId | undefined) ?? (canFeed(night, 'gulpy') ? 'gulpy' : null);
  if (!fed) console.log(`  (nessun mostro da sfamare nella notte ${night})`);
  else play(skill, fed, `  +${fed}`);
}
