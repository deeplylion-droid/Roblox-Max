/**
 * Le scorciatoie da tastiera per provare il gioco (richiesta dell'utente del 13 ottobre):
 * - sul titolo, Alt + numero: comincia da quella notte (Alt+7: la schermata della notte extra);
 * - durante la notte, Alt+V: la notte vinta adesso, come alle sei con la quota piena (alla sesta parte il finale);
 * - durante la notte, Alt+Maiusc + numero: il jumpscare (e la morte) di 1 Gulpy, 2 Molly, 3 Hatch, 4 Robin, 5 Archie,
 *   6 Lampy, 7 Fangy, 8 il Foxy, 9 la Madre, 0 la quota mancata.
 *
 * Ci sono in sviluppo (npx vite) e nelle build di prova (VITE_SCORCIATOIE=1: l'opzione «scorciatoie» del workflow
 * build, accesa di base quando la build si lancia a mano). Nelle build per il pubblico (i tag v*, o l'opzione spenta)
 * __SCORCIATOIE__ (vite.config.ts) è «false» già nel codice: il minificatore toglie il blocco del titolo che registra i
 * tasti (App.title) e con lui questo modulo, e i metodi di prova della simulazione restano vuoti.
 */
import type { MonsterId } from '../game/config.ts';
import type { MotherCause } from '../game/sim.ts';

/** Alt+Maiusc + numero: di chi è il jumpscare. Il codice del tasto (Digit1…) è uguale su ogni tastiera, anche dove i
 *  numeri vogliono il Maiusc. La Madre è quella che ti prende da sotto perché ti sei mosso; la quota mancata è la
 *  Madre senza causa, come alle sei col secchio troppo vuoto. */
export const JUMPSCARE_TASTI: Readonly<Record<string, { killer: MonsterId | 'mother'; cause?: MotherCause }>> = {
  Digit1: { killer: 'gulpy' },
  Digit2: { killer: 'molly' },
  Digit3: { killer: 'hatch' },
  Digit4: { killer: 'robin' },
  Digit5: { killer: 'archie' },
  Digit6: { killer: 'lampy' },
  Digit7: { killer: 'fangy' },
  Digit8: { killer: 'foxy' },
  Digit9: { killer: 'mother', cause: 'moved' },
  Digit0: { killer: 'mother' },
};

/** Alt + numero sul titolo: la notte da cui cominciare (0 se il tasto non è un numero). */
export function notteDelTasto(code: string): number {
  const m = /^Digit(\d)$/.exec(code);
  return m ? Number(m[1]) : 0;
}
