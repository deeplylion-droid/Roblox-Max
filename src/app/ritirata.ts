/**
 * La ritirata di Robin (scelta dell'utente del 13 ottobre): scacciato dalla luce se ne va oltre il bordo con
 * un'animazione renderizzata (tools/render/scena_creature.py, robin_ritirata_1..N) invece di svanire. Robin ha mezzo
 * corpo dentro la barca: le mani che mollano la presa di Gulpy e Molly (Night.aboard, `release`) con lui lo
 * spezzerebbero in pezzi. Prima la fuga, fotogramma per fotogramma, poi la discesa di sempre dietro lo scafo
 * dall'ultimo fotogramma (dove niente sta più davanti alla barca). Quando torna è il contrario: sale dietro lo scafo
 * nell'ultimo fotogramma, poi la fuga all'indietro lo riporta col braccio nel secchio.
 */

/** i fotogrammi della ritirata nel manifest */
export const ROBIN_FUGA_KEY = (i: number) => `robin_ritirata_${i}`;
/** secondi della fuga (la posa e i fotogrammi, tagli netti a ~16 al secondo: rapida ma continua) */
export const ROBIN_FUGA_S = 0.42;
/** secondi del ritorno, all'indietro (più piano: si riavvicina al secchio) */
export const ROBIN_TORNA_S = 0.6;
/** la discesa dietro lo scafo, come prima: una corsa intera in UP secondi a salire, DOWN a scendere */
export const ROBIN_SALE_S = 1.2;
export const ROBIN_SCENDE_S = 0.7;

/** Quanti fotogrammi della ritirata ci sono (di fila da 1). */
export function robinFugaFrames(has: (key: string) => boolean): number {
  let n = 0;
  while (has(ROBIN_FUGA_KEY(n + 1))) n++;
  return n;
}

/**
 * Un passo di Robin sulla barca. p: quanto è su (1 in posa sopra il bordo, 0 sparito dietro lo scafo); go: quanto è
 * andata avanti la fuga (0 in posa, 1 all'ultimo fotogramma). target 1: arriva (o resta), 0: se ne va. n: i
 * fotogrammi della fuga (0: senza, la discesa di prima).
 */
export function robinStep(p: number, go: number, target: 0 | 1, dt: number, n: number): { p: number; go: number } {
  const toward = (cur: number, t: number, up: number, down: number) =>
    t > cur ? Math.min(t, cur + dt / up) : Math.max(t, cur - dt / down);
  if (n <= 0) return { p: toward(p, target, ROBIN_SALE_S, ROBIN_SCENDE_S), go: 0 };
  if (target === 0) {
    if (p <= 0) return { p: 0, go: 1 };
    // prima la fuga oltre il bordo, poi giù dietro lo scafo
    if (go < 1) return { p, go: Math.min(1, go + dt / ROBIN_FUGA_S) };
    return { p: toward(p, 0, ROBIN_SALE_S, ROBIN_SCENDE_S), go: 1 };
  }
  // sale dietro lo scafo nell'ultimo fotogramma, poi la fuga all'indietro
  if (p < 1) return { p: toward(p, 1, ROBIN_SALE_S, ROBIN_SCENDE_S), go };
  return { p: 1, go: Math.max(0, go - dt / ROBIN_TORNA_S) };
}

/** Il fotogramma della fuga da mostrare: 0 la posa (con le toppe della testa), 1..n i fotogrammi; ognuno per lo
 *  stesso tempo. */
export function robinFrame(go: number, n: number): number {
  if (n <= 0 || go <= 0) return 0;
  return Math.min(n, Math.floor(go * (n + 1)));
}
