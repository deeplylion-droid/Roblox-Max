/**
 * Il menu principale col ritratto (scelta dell'utente del 13 ottobre, la proposta A «Il ritratto», come il titolo di
 * FNAF; da approvare il risultato): a destra, da vicino, uno dei bambini-mostro alla luce della barca, che respira e
 * ogni tanto ha uno scatto col segnale disturbato. Si vedono solo i mostri già incontrati; al primo avvio Molly. A ogni
 * avvio uno diverso. I ritratti li fa tools/render/ritratti.py.
 */
import { MONSTERS, type MonsterId, type NightConfig } from '../game/config.ts';

/** I mostri che hanno il loro ritratto (renderizzato), nell'ordine in cui si incontrano. */
export const RITRATTI: readonly MonsterId[] = ['gulpy', 'molly', 'hatch', 'robin'];
/** Al primo avvio, quando non hai ancora incontrato nessuno (scelta dell'utente). */
export const PRIMO_RITRATTO: MonsterId = 'molly';

/** Le immagini di un ritratto: quella ferma e i due fotogrammi dello scatto. */
export function ritrattoSrc(who: MonsterId): { calmo: string; scatti: [string, string] } {
  const b = `assets/img/ritratti/${who}`;
  return { calmo: `${b}.webp`, scatti: [`${b}_scatto1.webp`, `${b}_scatto2.webp`] };
}

/** Il ritratto di questo avvio: uno dei mostri incontrati che ha il ritratto, diverso da quello dell'ultima volta
 *  (se ce n'è più d'uno); nessuno incontrato, Molly. */
export function scegliRitratto(seen: readonly MonsterId[], last: MonsterId | null, rnd: () => number = Math.random): MonsterId {
  const pool = RITRATTI.filter((m) => seen.includes(m));
  if (!pool.length) return PRIMO_RITRATTO;
  const altri = pool.length > 1 ? pool.filter((m) => m !== last) : pool;
  return altri[Math.min(altri.length - 1, Math.floor(rnd() * altri.length))]!;
}

/** I mostri che vengono in una notte (quelli che la notte ha e che arrivano: nella notte extra quelli a livello 0 no). */
export function mostriDellaNotte(cfg: NightConfig): MonsterId[] {
  return MONSTERS.filter((m) => {
    const c = (cfg as unknown as Record<string, { firstAt?: number } | undefined>)[m];
    return !!c && (c.firstAt ?? 0) < 1e8;
  });
}
