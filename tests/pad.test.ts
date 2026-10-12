import { describe, expect, it } from 'vitest';
import {
  BUTTON_INDEX,
  NavRepeat,
  Pad,
  deadzone,
  emptyState,
  glyphText,
  lookCurve,
  mergeStates,
  navDirection,
  padFamily,
  pressedBetween,
  readPad,
  type PadButton,
  type PadLike,
} from '../src/app/pad.ts';
import { nearest, pickNext, type Box } from '../src/app/padnav.ts';

/** Un controller finto con la mappatura standard: i tasti premuti, i grilletti (0..1) e gli assi. */
function fake(pressed: PadButton[] = [], axes: number[] = [0, 0, 0, 0], triggers: { LT?: number; RT?: number } = {}): PadLike {
  const buttons = Array.from({ length: 17 }, () => ({ pressed: false, value: 0 }));
  for (const b of pressed) buttons[BUTTON_INDEX[b]] = { pressed: true, value: 1 };
  if (triggers.LT !== undefined) buttons[6] = { pressed: false, value: triggers.LT };
  if (triggers.RT !== undefined) buttons[7] = { pressed: false, value: triggers.RT };
  return { id: 'Xbox 360 Controller (XInput STANDARD GAMEPAD)', mapping: 'standard', connected: true, buttons, axes };
}

describe('Controller: la mappatura standard', () => {
  it('ogni tasto al suo posto (A B X Y, dorsali, grilletti, Back e Start, gli stick premuti, la croce)', () => {
    for (const b of Object.keys(BUTTON_INDEX) as PadButton[]) {
      const s = readPad(fake([b]));
      expect([...s.held]).toEqual([b]);
    }
    expect(BUTTON_INDEX).toMatchObject({ A: 0, B: 1, X: 2, Y: 3, LB: 4, RB: 5, LT: 6, RT: 7, Back: 8, Start: 9, L3: 10, R3: 11, Up: 12, Down: 13, Left: 14, Right: 15 });
  });

  it('i grilletti analogici contano da un terzo in su', () => {
    expect(readPad(fake([], undefined, { RT: 0.2 })).held.has('RT')).toBe(false);
    expect(readPad(fake([], undefined, { RT: 0.5 })).held.has('RT')).toBe(true);
    expect(readPad(fake([], undefined, { LT: 0.9 })).held.has('LT')).toBe(true);
  });

  it('un controller con meno tasti o assi strani non rompe niente', () => {
    const s = readPad({ buttons: [{ pressed: true, value: 1 }], axes: [NaN] });
    expect([...s.held]).toEqual(['A']);
    expect(s.lx).toBe(0);
    expect(s.rx).toBe(0);
  });

  it('gli stick: zona morta (a riposo non girano) e poi su fino a 1', () => {
    expect(deadzone(0.1, -0.12)).toEqual([0, 0]);
    const [x] = deadzone(1, 0);
    expect(x).toBeCloseTo(1);
    // appena fuori dalla zona morta il valore parte da vicino a zero (niente scatto)
    expect(deadzone(0.21, 0)[0]).toBeLessThan(0.02);
    const s = readPad(fake([], [0, 0, 0.8, -1]));
    expect(s.rx).toBeGreaterThan(0.5);
    expect(s.ry).toBeLessThan(-0.5);
  });

  it('lo sguardo è morbido al centro e pieno in fondo, con il segno giusto', () => {
    expect(lookCurve(0)).toBe(0);
    expect(lookCurve(1)).toBe(1);
    expect(lookCurve(-1)).toBe(-1);
    expect(lookCurve(0.5)).toBeLessThan(0.5);
  });

  it('più controller insieme: i tasti di tutti, lo stick più spostato', () => {
    const a = readPad(fake(['A'], [0.9, 0, 0, 0]));
    const b = readPad(fake(['RT'], [0, 0, 0, 0.4]));
    const m = mergeStates([a, b]);
    expect([...m.held].sort()).toEqual(['A', 'RT']);
    expect(m.lx).toBeGreaterThan(0.8);
    expect(m.ry).toBeGreaterThan(0.1);
  });

  it('premuto e lasciato fra due fotogrammi', () => {
    const p1 = readPad(fake(['A', 'LT']));
    const p2 = readPad(fake(['LT', 'RT']));
    expect([...pressedBetween(p1, p2)]).toEqual(['RT']);
    expect([...pressedBetween(p2, p1)]).toEqual(['A']);
  });
});

describe('Controller: i menu', () => {
  it('la croce o lo stick sinistro spinto oltre metà danno la direzione', () => {
    expect(navDirection(readPad(fake(['Down'])))).toBe('down');
    expect(navDirection(readPad(fake([], [-0.9, 0.2, 0, 0])))).toBe('left');
    expect(navDirection(readPad(fake([], [0.1, -0.95, 0, 0])))).toBe('up');
    expect(navDirection(readPad(fake([], [0.3, 0.3, 0, 0])))).toBe(null);
    expect(navDirection(emptyState())).toBe(null);
  });

  it('tenendo la direzione: una volta subito, poi una pausa, poi a raffica', () => {
    const r = new NavRepeat(0.4, 0.1);
    const dt = 1 / 60;
    const fired: number[] = [];
    for (let f = 0; f < 60; f++) if (r.step('down', dt)) fired.push(f);
    expect(fired[0]).toBe(0);
    // la seconda dopo circa 0,4 s, poi ogni 0,1 s
    expect(fired[1]).toBeGreaterThanOrEqual(23);
    expect(fired[1]).toBeLessThanOrEqual(25);
    expect(fired[2]! - fired[1]!).toBeGreaterThanOrEqual(5);
    expect(fired[2]! - fired[1]!).toBeLessThanOrEqual(7);
    // lasciata e ripresa: di nuovo subito
    expect(r.step(null, dt)).toBe(null);
    expect(r.step('down', dt)).toBe('down');
  });

  // una colonna di tre pulsanti e una riga di due sotto
  const boxes: Box[] = [
    { x: 100, y: 0, w: 200, h: 40 },
    { x: 100, y: 50, w: 200, h: 40 },
    { x: 100, y: 100, w: 200, h: 40 },
    { x: 0, y: 200, w: 120, h: 40 },
    { x: 280, y: 200, w: 120, h: 40 },
  ];

  it('la selezione va al pulsante più vicino in quella direzione', () => {
    expect(pickNext(boxes[0]!, boxes, 'down')).toBe(1);
    expect(pickNext(boxes[1]!, boxes, 'up')).toBe(0);
    expect(pickNext(boxes[0]!, boxes, 'up')).toBe(-1);
    expect(pickNext(boxes[3]!, boxes, 'right')).toBe(4);
    expect(pickNext(boxes[4]!, boxes, 'left')).toBe(3);
    expect(pickNext(boxes[3]!, boxes, 'up')).toBe(2);
    // dalla colonna in alto, «sinistra» non scende alla riga di sotto
    expect(pickNext(boxes[0]!, boxes, 'left')).toBe(-1);
  });

  it('se il pulsante scelto sparisce, si riparte dal più vicino', () => {
    expect(nearest({ x: 110, y: 52, w: 10, h: 10 }, boxes)).toBe(1);
  });
});

describe('Controller: i nomi dei tasti e il dispositivo in uso', () => {
  it('riconosce PlayStation, Steam Deck (Steam Input) e il resto come Xbox', () => {
    expect(padFamily('DualSense Wireless Controller (STANDARD GAMEPAD Vendor: 054c Product: 0ce6)')).toBe('playstation');
    expect(padFamily('Steam Virtual Gamepad (Vendor: 28de Product: 11ff)')).toBe('deck');
    expect(padFamily('Xbox 360 Controller (XInput STANDARD GAMEPAD)')).toBe('xbox');
    // in Bluetooth anche l'Xbox è un «Wireless Controller», come il DualShock
    expect(padFamily('Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 0b13)')).toBe('xbox');
    expect(padFamily('Wireless Controller (STANDARD GAMEPAD Vendor: 054c Product: 09cc)')).toBe('playstation');
  });

  it('scrive i tasti come sono stampati sul controller', () => {
    expect(glyphText('{RT} per lanciare', 'xbox')).toBe('RT per lanciare');
    expect(glyphText('{RT} per lanciare', 'playstation')).toBe('R2 per lanciare');
    expect(glyphText('{A}: nasconditi', 'playstation')).toBe('✕: nasconditi');
    expect(glyphText('{LB} {RB}', 'deck')).toBe('L1 R1');
    // le parole fra graffe che non sono tasti restano
    expect(glyphText('{who}', 'xbox')).toBe('{who}');
  });

  it('il dispositivo passa al controller al primo tasto o stick, e i tasti premuti valgono un fotogramma solo', () => {
    const p = new Pad();
    expect(p.active).toBe(false);
    p.feed([readPad(fake())]);
    expect(p.active).toBe(false);
    p.feed([readPad(fake(['RT']))], 'Xbox 360 Controller');
    expect(p.active).toBe(true);
    expect(p.pressed('RT')).toBe(true);
    expect(p.down('RT')).toBe(true);
    p.feed([readPad(fake(['RT']))]);
    expect(p.pressed('RT')).toBe(false);
    expect(p.down('RT')).toBe(true);
    p.feed([readPad(fake())]);
    expect(p.released('RT')).toBe(true);
    p.setDevice('kb');
    // uno stick spinto riporta al controller
    p.feed([readPad(fake([], [0, 0, 0.9, 0]))]);
    expect(p.active).toBe(true);
    const [x] = p.look();
    expect(x).toBeGreaterThan(0.5);
  });

  it('un tasto usato da un menu non arriva anche alla notte', () => {
    const p = new Pad();
    p.feed([readPad(fake())]);
    p.feed([readPad(fake(['A']))]);
    expect(p.pressed('A')).toBe(true);
    p.consume();
    expect(p.pressed('A')).toBe(false);
    expect(p.down('A')).toBe(true);
  });
});
