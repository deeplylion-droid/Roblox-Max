/**
 * Bilanciamento: fa giocare la notte a bot di diversa abilità e riassume i risultati.
 * Uso: node scripts/balance.ts [notte] [partite]
 * Notte extra: node scripts/balance.ts 7 [partite] [livelli], coi livelli nell'ordine di EXTRA_IDS
 * (gulpy,molly,hatch,robin,archie,lampy,fangy e, ottava, la Madre, che la simulazione non usa ancora), per esempio 5,5,5,5,5,5,5; un numero solo vale per tutti.
 */
import { EXTRA_IDS, EXTRA_NIGHT, NIGHTS, extraLevels, extraNight, type ExtraLevels } from '../src/game/config.ts';
import { NightSim } from '../src/game/sim.ts';
import { SKILLS, playNight } from '../src/game/bot.ts';

const night = Number(process.argv[2] ?? 1);
const games = Number(process.argv[3] ?? 300);
let levels: ExtraLevels | null = null;
if (night === EXTRA_NIGHT) {
  const v = (process.argv[4] ?? '5').split(',').map(Number);
  levels = v.length === 1 ? extraLevels(v[0]!) : (Object.fromEntries(EXTRA_IDS.map((m, i) => [m, v[i] ?? 0])) as ExtraLevels);
}
const cfg = levels ? extraNight(levels) : NIGHTS[night];
if (!cfg) throw new Error(`notte ${night} non configurata`);

const extra = levels ? ` · livelli ${EXTRA_IDS.map((m) => `${m} ${levels![m]}`).join(', ')}` : '';
console.log(`Notte ${night} · quota ${cfg.quota}${extra} · ${games} partite per abilità\n`);
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
      ` · pescati ${(caughtSum / games).toFixed(1)} · dati a Gulpy ${(fedSum / games).toFixed(1)} · nel secchio ${(fishSum / games).toFixed(1)} · lore ${(loreSum / games).toFixed(2)}`,
  );
}
