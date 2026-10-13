/**
 * La tastiera (13 ottobre: la tastiera francese, docs/LOCALIZZAZIONE.md). I tasti che contano per dove stanno, sotto
 * la mano sinistra (W A S D per voltarsi, Q ed E per la luce), si leggono per posizione (`KeyboardEvent.code`): su una
 * tastiera francese (AZERTY) sono Z Q S D e A/E. Gli altri (F il pesce, C il telone, B il binocolo, Spazio, Tab, le
 * frecce) si leggono per la lettera, come prima. Nei suggerimenti {KeyW}, {KeyQ}… diventano le lettere della tastiera di
 * chi gioca: le dice il browser (`navigator.keyboard`, che in Electron c'è) e le conferma ogni tasto premuto.
 */

/** I tasti a posizione fissa: il codice del tasto e il nome che gli dà il gioco (la lettera della tastiera americana). */
const POSTO: Record<string, string> = { KeyW: 'w', KeyA: 'a', KeyS: 's', KeyD: 'd', KeyQ: 'q', KeyE: 'e' };
const LETTERE_DEI_POSTI = new Set(Object.values(POSTO));

/** Le lettere della tastiera di chi gioca, per codice del tasto (solo i tasti a posizione fissa). */
const lettere = new Map<string, string>();

/**
 * Il tasto premuto, col nome che usa il gioco: quelli a posizione fissa per dove stanno ('w', 'a', 's', 'd', 'q', 'e'),
 * gli altri per la lettera in minuscolo ('f', ' ', 'tab', 'arrowleft', 'escape'…); '' per un tasto che non conta.
 */
export function tasto(e: KeyboardEvent): string {
  const posto = POSTO[e.code];
  if (posto) {
    impara(e);
    return posto;
  }
  const k = e.key.toLowerCase();
  // una tastiera che non scrive in latino (russa, greca…) o un tasto che si tiene il metodo di scrittura (IME): vale la
  // lettera stampata sul tasto, che quelle tastiere hanno accanto alla loro
  if (/^Key[A-Z]$/.test(e.code) && (k === 'process' || k === 'unidentified' || (/^\p{L}$/u.test(k) && !/^[a-z]$/.test(k)))) {
    return e.code.slice(3).toLowerCase();
  }
  // le lettere dei tasti a posizione fissa valgono solo lì (in Francia la W sta dove qui c'è la Z)
  if (LETTERE_DEI_POSTI.has(k) && e.code && e.code !== 'Unidentified') return '';
  return k;
}

/** Un tasto a posizione fissa premuto da solo dice che lettera ha sopra (se la mappa del browser non c'era). */
function impara(e: KeyboardEvent): void {
  if (e.ctrlKey || e.altKey || e.metaKey || e.key.length !== 1) return;
  lettere.set(e.code, e.key.toLowerCase());
}

/** La lettera sul tasto in quel posto, maiuscola; senza notizie, o se non è una lettera latina, quella americana. */
export function etichetta(code: string): string {
  const l = lettere.get(code);
  return (l && /^\p{Script=Latin}$/u.test(l) ? l : code.slice(3)).toUpperCase();
}

/** Un testo con {KeyW}, {KeyQ}… con le lettere della tastiera di chi gioca. */
export function tastiText(text: string): string {
  return text.replace(/\{(Key[A-Z])\}/g, (_, code: string) => etichetta(code));
}

type MappaTastiera = { get(code: string): string | undefined };

/** Chiede al browser le lettere dei tasti; di nuovo quando la finestra torna in primo piano (si può cambiare tastiera). */
export function ascoltaTastiera(): void {
  const k = (navigator as Navigator & { keyboard?: { getLayoutMap?: () => Promise<MappaTastiera> } }).keyboard;
  if (!k?.getLayoutMap) return;
  const leggi = () =>
    k.getLayoutMap!()
      .then((m) => {
        for (const code of Object.keys(POSTO)) {
          const l = m.get(code);
          if (l) lettere.set(code, l.toLowerCase());
        }
      })
      // fuori da un contesto sicuro o in una cornice il browser non la dà: restano le lettere imparate
      .catch(() => {});
  leggi();
  addEventListener('focus', leggi);
}
