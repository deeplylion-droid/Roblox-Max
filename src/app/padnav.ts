/**
 * I menu col controller: la croce o lo stick sinistro spostano la selezione fra i pulsanti della schermata (verso il
 * più vicino in quella direzione), A conferma, B torna indietro (il pulsante segnato data-back), LB e RB girano le
 * pagine (data-pad-prev, data-pad-next), lo stick destro scorre le liste lunghe. Sui cursori delle opzioni sinistra e
 * destra cambiano il valore. La selezione si vede solo quando si usa il controller (html.pad).
 */
import { pad, type Dir } from './pad.ts';

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Il prossimo riquadro andando in `dir` da `from`: fra quelli che stanno da quella parte, il più vicino, contando il
 * doppio lo scarto di traverso (così da un pulsante si va a quello sotto, non a quello sotto e di lato), e solo
 * dentro un cono di 45°.
 * -1 se da quella parte non c'è niente.
 */
export function pickNext(from: Box, cands: Box[], dir: Dir): number {
  const cx = from.x + from.w / 2;
  const cy = from.y + from.h / 2;
  let best = -1;
  let bestScore = Infinity;
  cands.forEach((c, i) => {
    const x = c.x + c.w / 2;
    const y = c.y + c.h / 2;
    const dx = x - cx;
    const dy = y - cy;
    // davanti: oltre metà del riquadro di partenza in quella direzione (le righe accanto non contano)
    let along: number;
    let across: number;
    if (dir === 'down' || dir === 'up') {
      along = dir === 'down' ? dy : -dy;
      across = Math.abs(dx);
      if (along <= Math.min(from.h, c.h) / 2 - 1) return;
      // sovrapposti in orizzontale: lo scarto di traverso non conta
      if (c.x < from.x + from.w && c.x + c.w > from.x) across = 0;
    } else {
      along = dir === 'right' ? dx : -dx;
      across = Math.abs(dy);
      if (along <= Math.min(from.w, c.w) / 2 - 1) return;
      if (c.y < from.y + from.h && c.y + c.h > from.y) across = 0;
    }
    // fuori dal cono di 45° non conta (da una colonna di pulsanti, «sinistra» non scende alla riga di sotto)
    if (across > along) return;
    const score = along + 2 * across;
    if (score < bestScore) {
      bestScore = score;
      best = i;
    }
  });
  return best;
}

/** Il riquadro più vicino a `b` (centro con centro). */
export function nearest(b: Box, cands: Box[]): number {
  let best = 0;
  let bestD = Infinity;
  cands.forEach((c, i) => {
    const d = Math.hypot(c.x + c.w / 2 - (b.x + b.w / 2), c.y + c.h / 2 - (b.y + b.h / 2));
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  });
  return best;
}

const FOCUSABLE = 'button:not([disabled]), input[type=range], [data-pad-focus]';

function visible(el: HTMLElement): boolean {
  if (el.closest('[hidden]')) return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
}

function box(el: HTMLElement): Box {
  const r = el.getBoundingClientRect();
  return { x: r.left, y: r.top, w: r.width, h: r.height };
}

/** La lista da scorrere della schermata (il diario, la notte extra quando non ci sta). */
function scroller(scope: HTMLElement, from: HTMLElement | null): HTMLElement | null {
  const can = (e: HTMLElement) => e.scrollHeight > e.clientHeight + 4 && /auto|scroll/.test(getComputedStyle(e).overflowY);
  for (let e = from; e && e !== scope.parentElement; e = e.parentElement) if (can(e)) return e;
  if (can(scope)) return scope;
  for (const e of Array.from(scope.querySelectorAll<HTMLElement>('*'))) if (can(e)) return e;
  return null;
}

export class PadNav {
  /** la schermata dell'ultima selezione e dov'era (si ritrova quando la schermata si ridisegna uguale, o quando il
   *  pulsante scelto si spegne: il − della notte extra arrivato a 0) */
  private lastKind = '';
  private lastBox: Box | null = null;

  /**
   * Un fotogramma dei menu dentro `root` (#ui): la schermata in primo piano è il riquadro di conferma, se c'è, se no
   * l'ultima .screen. Torna false se non c'era niente da comandare.
   */
  update(root: HTMLElement, dt: number): boolean {
    const scope = root.querySelector<HTMLElement>('.dive-confirm') ?? Array.from(root.querySelectorAll<HTMLElement>('.screen')).pop() ?? null;
    if (!scope) {
      pad.nav(dt);
      return false;
    }
    // l'avvertenza: qualunque tasto va avanti
    if (scope.classList.contains('warning')) {
      pad.nav(dt);
      if (pad.anyPressed()) scope.dispatchEvent(new Event('pointerdown'));
      return true;
    }
    const items = Array.from(scope.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(visible);
    const active = document.activeElement as HTMLElement | null;
    let cur = active && items.includes(active) ? active : null;
    const dir = pad.nav(dt);
    const kind = scope.className + '|' + (scope.querySelector('h1, h2')?.textContent ?? '');

    // col controller c'è sempre qualcosa di selezionato (il tasto che l'ha fatto apparire non lo preme anche)
    let fresh = false;
    if (!cur && pad.active && items.length) {
      fresh = true;
      const again = kind === this.lastKind && this.lastBox ? items[nearest(this.lastBox, items.map(box))] : null;
      cur = again ?? scope.querySelector<HTMLElement>('[data-pad-default]') ?? items[0]!;
      this.focus(cur, false);
    }
    this.lastKind = kind;
    if (cur) this.lastBox = box(cur);

    if (dir && cur) {
      if (cur instanceof HTMLInputElement && cur.type === 'range' && (dir === 'left' || dir === 'right')) {
        if (dir === 'left') cur.stepDown();
        else cur.stepUp();
        cur.dispatchEvent(new Event('input', { bubbles: true }));
      } else {
        const i = pickNext(box(cur), items.map(box), dir);
        if (i >= 0 && items[i] !== cur) this.focus(items[i]!, true);
        else if (dir === 'up' || dir === 'down') scroller(scope, cur)?.scrollBy({ top: dir === 'down' ? 120 : -120 });
      }
    }
    // A conferma; B torna indietro; LB e RB girano le pagine
    // (il tasto usato qui non arriva anche a chi legge il controller dopo, nello stesso fotogramma)
    const hit = (el: HTMLElement | null | undefined) => {
      pad.consume();
      el?.click();
    };
    if (pad.pressed('A') && cur && !fresh) hit(cur);
    else if (pad.pressed('B')) hit(scope.querySelector<HTMLElement>('[data-back]'));
    else if (pad.pressed('LB')) hit(scope.querySelector<HTMLElement>('[data-pad-prev]:not([disabled])'));
    else if (pad.pressed('RB')) hit(scope.querySelector<HTMLElement>('[data-pad-next]:not([disabled])'));
    // lo stick destro scorre le liste
    const ry = pad.stick.ry;
    if (ry) scroller(scope, cur)?.scrollBy({ top: ry * 900 * dt });
    return true;
  }

  private focus(el: HTMLElement, sound: boolean): void {
    el.focus({ preventScroll: true });
    el.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    // lo stesso suono del mouse che ci passa sopra
    if (sound) el.dispatchEvent(new MouseEvent('mouseenter'));
  }
}
