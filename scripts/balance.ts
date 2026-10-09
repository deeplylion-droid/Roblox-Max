/**
 * Bilanciamento: fa giocare la notte a bot di diversa abilità e riassume i risultati.
 * Uso: node scripts/balance.ts [notte] [partite]
 */
import { NIGHTS } from '../src/game/config.ts';
import { NightSim } from '../src/game/sim.ts';
import { SKILLS, playNight } from '../src/game/bot.ts';

const night = Number(process.argv[2] ?? 1);
const games = Number(process.argv[3] ?? 300);
const cfg = NIGHTS[night];
if (!cfg) throw new Error(`notte ${night} non configurata`);

console.log(`Notte ${night} · quota ${cfg.quota} · ${games} partite per abilità\n`);
for (const skill of Object.values(SKILLS)) {
  let wins = 0;
  const deaths: Record<string, number> = {};
  const deathHour: number[] = [];
  let fishSum = 0;
  let fedSum = 0;
  let caughtSum = 0;
  let loreSum = 0;
  for (let seed = 1; seed <= games; seed++) {
    const sim = playNight(new NightSim(cfg, seed * 7919), skill, seed);
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
    `${skill.name.padEnd(8)} vittorie ${pct(wins).padStart(6)} · morti ${JSON.stringify(deaths)} (ora media ${avgHour})` +
      ` · pescati ${(caughtSum / games).toFixed(1)} · dati a Pappo ${(fedSum / games).toFixed(1)} · nel secchio ${(fishSum / games).toFixed(1)} · lore ${(loreSum / games).toFixed(2)}`,
  );
}
