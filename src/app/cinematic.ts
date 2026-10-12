/**
 * Il regista delle cinematiche dei finali (approvate l'11 ottobre: brevi, 15-20 s, fatte nel motore del gioco). Una
 * cinematica è una sequenza di chiavi nel tempo: lo sguardo (direzione, inclinazione, campo visivo), la luce dell'alba e
 * della lampara, quanto sono su le creature, la barca che s'inclina, i suoni, le scritte, il buio. Il presentatore della
 * notte (night.ts) la suona al posto dei comandi; Esc la salta.
 */
import type { Lang } from '../i18n.ts';

export type Ease = 'lin' | 'smooth' | 'in' | 'out';

/** Una chiave: dall'istante prima a questo si arriva con la curva `ease` (lineare se manca). */
export interface Key<T> {
  t: number;
  v: T;
  ease?: Ease;
}

/** Cose che succedono in un istante (oltre ai suoni e alle scritte). */
export type CineEvent = 'emptyBucket' | 'shake' | 'radio' | 'lampOff' | 'dip';

export interface CinematicScript {
  /** durata (s): finita, si passa ai risultati */
  length: number;
  /** lo sguardo: yaw e pitch (gradi), campo visivo orizzontale (gradi) */
  view: Key<[number, number, number]>[];
  /** l'alba, 0..1 */
  dawn?: Key<number>[];
  /** la luce della lampara (il livello: 0 spenta, 1 bassa, 2 alta, anche a metà) */
  lamp?: Key<number>[];
  /** quanto è su ognuna delle creature che salgono dall'acqua (0 sotto, 1 su): gulpy, archie, lampy, fangy, hatch e la
   *  Madre (madre, la posa madre_sale) */
  creatures?: Partial<Record<CineCreature, Key<number>[]>>;
  /** la barca inclinata: gradi di rollio e di beccheggio in più */
  tilt?: Key<[number, number]>[];
  /** il buio a tutto schermo, 0..1 (dissolvenze) */
  black?: Key<number>[];
  sounds?: { t: number; id: string; gain?: number; loop?: boolean; fadeIn?: number }[];
  /** le scritte, al centro in basso */
  text?: { t: number; dur: number; it: string; en: string }[];
  events?: { t: number; e: CineEvent }[];
}

export type CineCreature = 'gulpy' | 'archie' | 'lampy' | 'fangy' | 'hatch' | 'madre';

function curve(x: number, e: Ease = 'lin'): number {
  const k = Math.max(0, Math.min(1, x));
  if (e === 'smooth') return k * k * (3 - 2 * k);
  if (e === 'in') return k * k;
  if (e === 'out') return 1 - (1 - k) * (1 - k);
  return k;
}

/** Il valore delle chiavi all'istante t (prima della prima: la prima; dopo l'ultima: l'ultima). */
export function sample<T extends number | number[]>(keys: Key<T>[], t: number): T {
  if (!keys.length) throw new Error('chiavi vuote');
  if (t <= keys[0]!.t) return keys[0]!.v;
  for (let i = 1; i < keys.length; i++) {
    const b = keys[i]!;
    if (t <= b.t) {
      const a = keys[i - 1]!;
      const k = curve((t - a.t) / Math.max(1e-6, b.t - a.t), b.ease);
      if (typeof a.v === 'number') return (a.v + ((b.v as number) - a.v) * k) as T;
      return (a.v as number[]).map((x, j) => x + ((b.v as number[])[j]! - x) * k) as T;
    }
  }
  return keys[keys.length - 1]!.v;
}

/** Le cose da fare fra due istanti (estremo sinistro escluso, destro incluso). */
export function between<E extends { t: number }>(list: E[] | undefined, t0: number, t1: number): E[] {
  return (list ?? []).filter((x) => x.t > t0 && x.t <= t1);
}

/** La scritta da mostrare all'istante t (vuota se nessuna). */
export function textAt(s: CinematicScript, t: number, lang: Lang): string {
  const x = (s.text ?? []).find((x) => t >= x.t && t < x.t + x.dur);
  return x ? x[lang] : '';
}

/**
 * Il finale A «La quota» (approvato l'11 ottobre), sui tempi del suono `madre_dawn_breve` (17 s): alle sei lei sale a
 * sinistra e il mare si gonfia (la barca s'inclina); i figli affiorano davanti alla prua, uno dopo l'altro; la sua
 * pinna sul capodibanda e il secchio che si svuota; tornano giù tutti; sorge il sole e la radio. Finché non c'è la
 * Madre renderizzata (la posa madre_sale, notte del 12 ottobre), di lei si vedevano solo l'acqua, la barca che
 * s'inclina e il secchio: ora sale accanto alla barca.
 */
export const FINALE_A: CinematicScript = {
  length: 17.2,
  view: [
    { t: 0, v: [0, -6, 80] },
    { t: 2.6, v: [-55, -4, 70], ease: 'smooth' },
    { t: 4.0, v: [-32, -3, 62], ease: 'smooth' },
    { t: 7.0, v: [38, -3, 62], ease: 'smooth' },
    // il secchio, da vicino: la lampara cala di colpo e quando torna i pesci non ci sono più
    { t: 8.0, v: [17, -20, 44], ease: 'smooth' },
    { t: 10.0, v: [16, -21, 40] },
    { t: 12.6, v: [0, -2, 78], ease: 'smooth' },
    { t: 17.2, v: [4, 2, 74], ease: 'smooth' },
  ],
  dawn: [
    { t: 0, v: 0.1 },
    { t: 11, v: 0.3, ease: 'in' },
    { t: 16, v: 1, ease: 'smooth' },
  ],
  creatures: {
    // lei sale a sinistra piano, insieme al mare che si gonfia e alla barca che s'inclina, mentre lo sguardo si gira
    // (a 2,6 s è sul suo occhio); resta finché il secchio si svuota e torna giù per prima
    madre: [{ t: 0.3, v: 0 }, { t: 3.0, v: 1, ease: 'smooth' }, { t: 10.0, v: 1 }, { t: 12.2, v: 0, ease: 'in' }],
    gulpy: [{ t: 4.0, v: 0 }, { t: 5.2, v: 1, ease: 'out' }, { t: 10.2, v: 1 }, { t: 12.0, v: 0, ease: 'in' }],
    archie: [{ t: 4.8, v: 0 }, { t: 6.2, v: 1, ease: 'out' }, { t: 10.4, v: 1 }, { t: 12.2, v: 0, ease: 'in' }],
    lampy: [{ t: 5.6, v: 0 }, { t: 6.8, v: 1, ease: 'out' }, { t: 10.6, v: 1 }, { t: 12.3, v: 0, ease: 'in' }],
  },
  tilt: [
    { t: 0, v: [0, 0] },
    { t: 2.5, v: [-1.6, 0.6], ease: 'smooth' },
    { t: 7.2, v: [-1.2, 0.4] },
    { t: 7.8, v: [-4.2, 0.8], ease: 'out' },
    { t: 9.8, v: [-3.6, 0.6] },
    { t: 11.5, v: [0.8, -0.3], ease: 'smooth' },
    { t: 13.5, v: [0, 0], ease: 'smooth' },
  ],
  black: [{ t: 0, v: 0 }, { t: 16.4, v: 0 }, { t: 17.2, v: 1, ease: 'in' }],
  sounds: [
    { t: 0.01, id: 'madre_dawn_breve' },
    { t: 13, id: 'amb_dawn', loop: true, fadeIn: 3, gain: 0.8 },
  ],
  events: [
    { t: 7.8, e: 'shake' },
    { t: 8.35, e: 'dip' },
    { t: 8.6, e: 'emptyBucket' },
    { t: 12.6, e: 'radio' },
  ],
};
