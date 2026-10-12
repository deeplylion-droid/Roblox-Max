/**
 * I disegni a pastelli dell'alba (richiesta dell'utente del 12 ottobre, «4/5 in giro per il gioco»; da approvare): all'alba
 * di ogni notte vinta, dalla prima alla quinta, sul banco c'è un disegno bagnato dei bambini di quella notte, com'erano
 * prima della Madre. Si vede nella schermata delle sei e poi resta nel Diario. Li genera tools/render/pastelli.py (la
 * stessa mano del disegno di «Il ricordo», il finale B).
 */

/** Il disegno dell'alba di ogni notte. */
export const DISEGNI_ALBA: Record<number, string> = {
  1: 'piscina',
  2: 'tesoro',
  3: 'compleanno',
  4: 'sottacqua',
  5: 'marcopolo',
};

export const disegnoSrc = (id: string): string => `assets/img/disegni/pastelli_${id}.webp`;

/** Il disegno trovato all'alba della notte `night` (null: quella notte non ne lascia). */
export function disegnoAlba(night: number): string | null {
  return DISEGNI_ALBA[night] ?? null;
}

/** I disegni già trovati, in ordine: quelli delle notti vinte (`unlocked` è la prima notte non ancora vinta). */
export function disegniTrovati(unlocked: number): string[] {
  return Object.keys(DISEGNI_ALBA)
    .map(Number)
    .sort((a, b) => a - b)
    .filter((n) => n < unlocked)
    .map((n) => DISEGNI_ALBA[n]!);
}
