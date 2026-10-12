/**
 * Il controller (Gamepad API, mappatura standard: Xbox, PlayStation, Steam Deck tramite Steam Input). Si legge una volta
 * per fotogramma (App.frame chiama pad.poll): chi ne ha bisogno chiede quali tasti sono tenuti (down), quali sono stati
 * appena premuti (pressed) o lasciati (released), e gli stick. Tastiera e mouse restano come sono: il controller si
 * aggiunge.
 *
 * Tiene anche l'ultimo dispositivo usato (tastiera e mouse, oppure controller): gli aiuti a schermo mostrano i tasti di
 * quello. Gli elementi con data-kb e data-pad cambiano testo da soli; <html> prende la classe «pad».
 */

/** I tasti della mappatura standard, coi nomi di un controller Xbox. */
export type PadButton = 'A' | 'B' | 'X' | 'Y' | 'LB' | 'RB' | 'LT' | 'RT' | 'Back' | 'Start' | 'L3' | 'R3' | 'Up' | 'Down' | 'Left' | 'Right';

/** Indice di ogni tasto in Gamepad.buttons (https://w3c.github.io/gamepad/#remapping). */
export const BUTTON_INDEX: Record<PadButton, number> = {
  A: 0, B: 1, X: 2, Y: 3, LB: 4, RB: 5, LT: 6, RT: 7, Back: 8, Start: 9, L3: 10, R3: 11, Up: 12, Down: 13, Left: 14, Right: 15,
};
const BUTTONS = Object.keys(BUTTON_INDEX) as PadButton[];

/** Quel che serve di un Gamepad (le prove ne fanno di finti). */
export interface PadLike {
  id?: string;
  connected?: boolean;
  mapping?: string;
  buttons: readonly { pressed: boolean; value: number }[];
  axes: readonly number[];
}

/** Lo stato del controller in un fotogramma: i tasti tenuti e i due stick (x a destra, y in giù, già senza zona morta). */
export interface PadState {
  held: Set<PadButton>;
  lx: number;
  ly: number;
  rx: number;
  ry: number;
}

export function emptyState(): PadState {
  return { held: new Set(), lx: 0, ly: 0, rx: 0, ry: 0 };
}

/** Zona morta degli stick (gli stick a riposo non tornano mai a zero esatto). */
export const DEADZONE = 0.2;
/** I grilletti analogici contano come premuti da qui in su. */
export const TRIGGER_ON = 0.35;

/** Zona morta radiale: sotto `dz` è zero, sopra si riscala da 0 a 1 (niente scatto al bordo della zona morta). */
export function deadzone(x: number, y: number, dz = DEADZONE): [number, number] {
  const m = Math.hypot(x, y);
  if (m < dz || !Number.isFinite(m)) return [0, 0];
  const k = Math.min(1, (m - dz) / (1 - dz)) / m;
  return [x * k, y * k];
}

/** La curva dello sguardo: morbida al centro (per mirare piano), piena in fondo. */
export function lookCurve(v: number): number {
  return Math.sign(v) * Math.abs(v) ** 1.6;
}

/** Lo stato di un controller. I grilletti valgono per il loro valore analogico; un tasto che manca non è premuto. */
export function readPad(gp: PadLike): PadState {
  const s = emptyState();
  for (const b of BUTTONS) {
    const btn = gp.buttons[BUTTON_INDEX[b]];
    if (!btn) continue;
    const on = b === 'LT' || b === 'RT' ? btn.pressed || btn.value > TRIGGER_ON : btn.pressed;
    if (on) s.held.add(b);
  }
  const ax = (i: number) => {
    const v = gp.axes[i] ?? 0;
    return Number.isFinite(v) ? v : 0;
  };
  [s.lx, s.ly] = deadzone(ax(0), ax(1));
  [s.rx, s.ry] = deadzone(ax(2), ax(3));
  return s;
}

/** Più controller collegati (sullo Steam Deck capita, col controller virtuale di Steam): i tasti di tutti, lo stick più
 *  spostato. */
export function mergeStates(states: PadState[]): PadState {
  const s = emptyState();
  for (const p of states) {
    for (const b of p.held) s.held.add(b);
    if (Math.hypot(p.lx, p.ly) > Math.hypot(s.lx, s.ly)) [s.lx, s.ly] = [p.lx, p.ly];
    if (Math.hypot(p.rx, p.ry) > Math.hypot(s.rx, s.ry)) [s.rx, s.ry] = [p.rx, p.ry];
  }
  return s;
}

/** I tasti appena premuti fra due fotogrammi. */
export function pressedBetween(prev: PadState, now: PadState): Set<PadButton> {
  const out = new Set<PadButton>();
  for (const b of now.held) if (!prev.held.has(b)) out.add(b);
  return out;
}

export type Dir = 'up' | 'down' | 'left' | 'right';

/** La direzione dei menu: la croce, oppure lo stick sinistro spinto oltre metà (la direzione più forte). */
export function navDirection(s: PadState): Dir | null {
  if (s.held.has('Up')) return 'up';
  if (s.held.has('Down')) return 'down';
  if (s.held.has('Left')) return 'left';
  if (s.held.has('Right')) return 'right';
  const [x, y] = [s.lx, s.ly];
  if (Math.max(Math.abs(x), Math.abs(y)) < 0.5) return null;
  return Math.abs(x) > Math.abs(y) ? (x < 0 ? 'left' : 'right') : y < 0 ? 'up' : 'down';
}

/** La ripetizione della direzione tenuta nei menu: la prima subito, poi dopo una pausa, poi a raffica. */
export class NavRepeat {
  private dir: Dir | null = null;
  private wait = 0;
  constructor(
    private first = 0.38,
    private every = 0.11,
  ) {}

  /** La direzione da eseguire in questo fotogramma (o null). */
  step(dir: Dir | null, dt: number): Dir | null {
    if (dir !== this.dir) {
      this.dir = dir;
      this.wait = this.first;
      return dir;
    }
    if (!dir) return null;
    this.wait -= dt;
    if (this.wait > 0) return null;
    this.wait += this.every;
    return dir;
  }
}

/** Le famiglie di controller, per scrivere i tasti come sono stampati sopra. */
export type PadFamily = 'xbox' | 'playstation' | 'deck';

export function padFamily(id: string): PadFamily {
  // Microsoft (045e) prima: in Bluetooth i controller Xbox si chiamano «Xbox Wireless Controller»
  if (/045e|xbox|xinput/i.test(id)) return 'xbox';
  if (/054c|playstation|dualsense|dualshock|wireless controller/i.test(id)) return 'playstation';
  // il controller virtuale di Steam (Steam Input, il produttore 28de è Valve): sullo Steam Deck i dorsali sono L1 R1
  if (/28de|steam/i.test(id)) return 'deck';
  return 'xbox';
}

export const GLYPHS: Record<PadFamily, Record<PadButton, string>> = {
  xbox: { A: 'A', B: 'B', X: 'X', Y: 'Y', LB: 'LB', RB: 'RB', LT: 'LT', RT: 'RT', Back: 'View', Start: 'Menu', L3: 'L3', R3: 'R3', Up: '↑', Down: '↓', Left: '←', Right: '→' },
  playstation: { A: '✕', B: '○', X: '□', Y: '△', LB: 'L1', RB: 'R1', LT: 'L2', RT: 'R2', Back: 'Create', Start: 'Options', L3: 'L3', R3: 'R3', Up: '↑', Down: '↓', Left: '←', Right: '→' },
  deck: { A: 'A', B: 'B', X: 'X', Y: 'Y', LB: 'L1', RB: 'R1', LT: 'L2', RT: 'R2', Back: 'View', Start: 'Menu', L3: 'L3', R3: 'R3', Up: '↑', Down: '↓', Left: '←', Right: '→' },
};

/** Sostituisce {A}, {RT}… coi tasti di quel controller. */
export function glyphText(text: string, family: PadFamily): string {
  return text.replace(/\{(\w+)\}/g, (m, b: string) => (b in BUTTON_INDEX ? GLYPHS[family][b as PadButton] : m));
}

/** Le vibrazioni: breve all'abboccata, forte al jumpscare. */
export const RUMBLE = {
  bite: { duration: 140, strongMagnitude: 0.25, weakMagnitude: 0.6 },
  scare: { duration: 650, strongMagnitude: 1, weakMagnitude: 1 },
} as const;

export type Device = 'kb' | 'pad';

/** Il controller del gioco (uno solo per tutta la pagina: `pad`). */
export class Pad {
  private state = emptyState();
  private prev = emptyState();
  private just = new Set<PadButton>();
  private gone = new Set<PadButton>();
  private repeat = new NavRepeat();
  private pads: Gamepad[] = [];
  /** l'ultimo dispositivo usato */
  device: Device = 'kb';
  family: PadFamily = 'xbox';
  /** le vibrazioni (spente con «Riduci lampi e scosse») */
  rumbleOn = true;
  private listeners: ((d: Device) => void)[] = [];
  private bound = false;

  /** Legge i controller; va chiamato una volta per fotogramma, prima di chi li usa. */
  poll(): void {
    this.bind();
    let list: (Gamepad | null)[] = [];
    try {
      list = typeof navigator !== 'undefined' && navigator.getGamepads ? Array.from(navigator.getGamepads()) : [];
    } catch {
      list = [];
    }
    this.pads = list.filter((g): g is Gamepad => !!g && g.connected !== false);
    this.feed(this.pads.map(readPad), this.pads[0]?.id);
  }

  /** Il passo di poll senza il browser (le prove): gli stati letti, l'id del primo controller. */
  feed(states: PadState[], id?: string): void {
    this.prev = this.state;
    this.state = mergeStates(states);
    this.just = pressedBetween(this.prev, this.state);
    this.gone = pressedBetween(this.state, this.prev);
    if (id && padFamily(id) !== this.family) {
      this.family = padFamily(id);
      if (this.active && typeof document !== 'undefined') refreshDual();
    }
    const moved = Math.max(Math.abs(this.state.lx), Math.abs(this.state.ly), Math.abs(this.state.rx), Math.abs(this.state.ry)) > 0.3;
    if (this.just.size || moved) this.setDevice('pad');
  }

  /** Il tasto è tenuto. */
  down(b: PadButton): boolean {
    return this.state.held.has(b);
  }

  /** Il tasto è stato premuto in questo fotogramma. */
  pressed(b: PadButton): boolean {
    return this.just.has(b);
  }

  /** Il tasto è stato lasciato in questo fotogramma. */
  released(b: PadButton): boolean {
    return this.gone.has(b);
  }

  /** I tasti premuti in questo fotogramma sono già stati usati (da un menu): per gli altri non contano più. */
  consume(): void {
    this.just.clear();
  }

  /** Qualunque tasto premuto in questo fotogramma. */
  anyPressed(): boolean {
    return this.just.size > 0;
  }

  /** Gli stick (senza zona morta): l = sinistro, r = destro. */
  get stick() {
    const s = this.state;
    return { lx: s.lx, ly: s.ly, rx: s.rx, ry: s.ry };
  }

  /** Lo sguardo: lo stick destro, oppure il sinistro se il destro è fermo; con la curva morbida. */
  look(): [number, number] {
    const s = this.state;
    const [x, y] = Math.hypot(s.rx, s.ry) > 0 ? [s.rx, s.ry] : [s.lx, s.ly];
    return [lookCurve(x), lookCurve(y)];
  }

  /** La direzione dei menu in questo fotogramma (con la ripetizione se la si tiene). */
  nav(dt: number): Dir | null {
    return this.repeat.step(navDirection(this.state), dt);
  }

  get active(): boolean {
    return this.device === 'pad';
  }

  /** Un testo con {A}, {RT}… coi tasti del controller in uso. */
  glyphs(text: string): string {
    return glyphText(text, this.family);
  }

  /** Fa vibrare i controller (dove si può). */
  rumble(kind: keyof typeof RUMBLE): void {
    if (!this.rumbleOn) return;
    for (const p of this.pads) {
      try {
        // (vibrationActuator manca su alcuni browser e controller anche se il tipo dice di no)
        const act = p.vibrationActuator as GamepadHapticActuator | null | undefined;
        void act?.playEffect?.('dual-rumble', { startDelay: 0, ...RUMBLE[kind] })?.catch(() => {});
      } catch {
        // il controller non vibra: pazienza
      }
    }
  }

  onDevice(fn: (d: Device) => void): () => void {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter((f) => f !== fn);
    };
  }

  setDevice(d: Device): void {
    if (d === this.device) return;
    this.device = d;
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('pad', d === 'pad');
      refreshDual();
    }
    for (const f of this.listeners) f(d);
  }

  /** Tastiera e mouse riportano gli aiuti ai loro tasti. */
  private bind(): void {
    if (this.bound || typeof addEventListener === 'undefined') return;
    this.bound = true;
    const kb = () => this.setDevice('kb');
    addEventListener('keydown', kb, true);
    addEventListener('mousedown', kb, true);
    addEventListener('wheel', kb, true);
    let last: [number, number] | null = null;
    addEventListener(
      'mousemove',
      (e) => {
        // un mouse fermo che manda un evento a caso non conta: deve spostarsi davvero
        if (last && Math.hypot(e.clientX - last[0], e.clientY - last[1]) > 8) kb();
        last = [e.clientX, e.clientY];
      },
      true,
    );
  }
}

export const pad = new Pad();

/** Un testo che cambia col dispositivo: `kb` per tastiera e mouse, `padText` (con {A}, {RT}…) per il controller. */
export function dualText(el: HTMLElement, kb: string, padText: string): HTMLElement {
  el.dataset.kb = kb;
  el.dataset.pad = padText;
  el.textContent = pad.active ? pad.glyphs(padText) : kb;
  return el;
}

/** Un tastino col simbolo del controller (si vede solo col controller in uso). */
export function badge(b: PadButton): HTMLSpanElement {
  const s = document.createElement('span');
  s.className = 'pad-badge';
  s.dataset.glyph = b;
  s.textContent = GLYPHS[pad.family][b];
  return s;
}

function refreshDual(): void {
  for (const el of Array.from(document.querySelectorAll<HTMLElement>('[data-pad]'))) {
    el.textContent = pad.active ? pad.glyphs(el.dataset.pad!) : (el.dataset.kb ?? '');
  }
  for (const el of Array.from(document.querySelectorAll<HTMLElement>('[data-glyph]'))) el.textContent = GLYPHS[pad.family][el.dataset.glyph as PadButton] ?? '';
}
