/**
 * Il regista delle cinematiche dei finali (approvate l'11 ottobre: brevi, 15-20 s, fatte nel motore del gioco). Una
 * cinematica è una sequenza di chiavi nel tempo: lo sguardo (direzione, inclinazione, campo visivo), la luce dell'alba e
 * della lampara, quanto sono su le creature, la barca che s'inclina, i suoni, le scritte, il buio. Il presentatore della
 * notte (night.ts) la suona al posto dei comandi; Esc la salta.
 */
import { STRINGS, type Lang } from '../i18n.ts';

export type Ease = 'lin' | 'smooth' | 'in' | 'out';

/** Una chiave: dall'istante prima a questo si arriva con la curva `ease` (lineare se manca). */
export interface Key<T> {
  t: number;
  v: T;
  ease?: Ease;
}

/** Cose che succedono in un istante (oltre ai suoni e alle scritte). */
export type CineEvent = 'emptyBucket' | 'shake' | 'radio' | 'lampOff' | 'dip' | 'quiet';

/** Le ultime inquadrature dei finali segreti, renderizzate (tools/render/finali.py → overlays.json, endings). */
export type EndingStill = 'molo' | 'edicola';

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
  /** l'ultima inquadratura: un'immagine ferma a tutto schermo da `t`, con la dissolvenza `fade` (0 = taglio netto) e un
   *  lento movimento di camera: zoom e il punto dell'immagine al centro dello schermo (x, y da in alto a sinistra, 0..1) */
  still?: { t: number; key: EndingStill; fade: number; move: Key<[number, number, number]>[] };
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

/** L'ultima inquadratura all'istante t: quanto si vede, lo zoom e il centro (null prima che cominci). */
export function stillFrame(s: CinematicScript, t: number): { key: EndingStill; alpha: number; zoom: number; cx: number; cy: number } | null {
  const st = s.still;
  if (!st || t < st.t) return null;
  const alpha = st.fade > 0 ? curve((t - st.t) / st.fade, 'smooth') : 1;
  const [zoom, cx, cy] = sample(st.move, t);
  return { key: st.key, alpha, zoom, cx, cy };
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

/**
 * Il finale segreto «I tuoi» (da approvare), sui tempi del suono `finale_tuoi` (18 s): all'alba la Madre sale a sinistra e
 * canta per richiamare i figli (0-3 s); loro affiorano attorno alla barca ma non la seguono, e lei richiama più forte
 * (4-6 s); torna giù da sola col suo lamento (6-10 s); i figli restano, poi scendono sotto la barca e la seguono mentre
 * sorge il sole e si rema verso il porto (10-14 s); la barca tocca il molo (14,6 s) e l'ultima inquadratura è il molo
 * all'alba con le sette file di impronte che vanno verso il paese, mentre si sentono i passetti (15-18 s).
 */
export const FINALE_TUOI: CinematicScript = {
  length: 21,
  view: [
    { t: 0, v: [0, -6, 80] },
    // lei, a sinistra, che chiama
    { t: 2.4, v: [-62, -7, 70], ease: 'smooth' },
    { t: 3.4, v: [-60, -6, 68] },
    // i figli attorno alla barca, che non la seguono: Gulpy e Archie davanti alla prua, poi Lampy a destra (panoramiche
    // lente, con una sosta su ognuno)
    { t: 4.9, v: [-4, -4, 72], ease: 'smooth' },
    { t: 5.6, v: [0, -4, 72] },
    { t: 6.8, v: [28, -5, 74], ease: 'smooth' },
    { t: 7.2, v: [30, -5, 74] },
    // stacco netto: lei che affonda da sola
    { t: 7.21, v: [-52, -6, 72] },
    { t: 10.0, v: [-48, -7, 72] },
    // l'alba: davanti alla prua, i figli scendono sotto la barca per seguirla
    { t: 11.6, v: [4, -3, 80], ease: 'smooth' },
    { t: 14.0, v: [6, 2, 76], ease: 'smooth' },
  ],
  dawn: [
    { t: 0, v: 0.12 },
    { t: 8.5, v: 0.3, ease: 'in' },
    { t: 13.2, v: 1, ease: 'smooth' },
  ],
  creatures: {
    // affonda piano dietro il pelo dell'acqua (lo strato scende e si taglia al galleggiamento, come le creature di notte)
    madre: [{ t: 0.2, v: 0 }, { t: 2.8, v: 1, ease: 'smooth' }, { t: 7.0, v: 1 }, { t: 10.2, v: 0, ease: 'smooth' }],
    gulpy: [{ t: 3.3, v: 0 }, { t: 4.3, v: 1, ease: 'out' }, { t: 10.8, v: 1 }, { t: 12.2, v: 0, ease: 'in' }],
    archie: [{ t: 3.8, v: 0 }, { t: 4.9, v: 1, ease: 'out' }, { t: 11.0, v: 1 }, { t: 12.4, v: 0, ease: 'in' }],
    lampy: [{ t: 4.4, v: 0 }, { t: 5.4, v: 1, ease: 'out' }, { t: 11.2, v: 1 }, { t: 12.5, v: 0, ease: 'in' }],
    fangy: [{ t: 4.9, v: 0 }, { t: 5.9, v: 1, ease: 'out' }, { t: 10.8, v: 1 }, { t: 12.0, v: 0, ease: 'in' }],
    hatch: [{ t: 5.3, v: 0 }, { t: 6.4, v: 1, ease: 'out' }, { t: 10.9, v: 1 }, { t: 12.1, v: 0, ease: 'in' }],
  },
  tilt: [
    { t: 0, v: [0, 0] },
    { t: 2.6, v: [-1.4, 0.5], ease: 'smooth' },
    { t: 6.4, v: [-1.0, 0.3] },
    { t: 9.6, v: [0.5, -0.2], ease: 'smooth' },
    { t: 11.4, v: [0, 0], ease: 'smooth' },
  ],
  // il viaggio verso il porto passa nel buio di un battito di ciglia: si riapre sul molo quando la barca lo tocca
  black: [
    { t: 0, v: 0 },
    { t: 13.4, v: 0 },
    { t: 14.3, v: 1, ease: 'in' },
    { t: 14.6, v: 1 },
    { t: 15.6, v: 0, ease: 'out' },
    { t: 20.2, v: 0 },
    { t: 21, v: 1, ease: 'in' },
  ],
  still: {
    t: 14.6,
    key: 'molo',
    fade: 0,
    // dal molo intero verso le impronte, piano
    move: [
      { t: 14.6, v: [1.0, 0.5, 0.5] },
      { t: 21, v: [1.14, 0.53, 0.6], ease: 'smooth' },
    ],
  },
  sounds: [
    { t: 0.01, id: 'finale_tuoi' },
    { t: 10.5, id: 'amb_dawn', loop: true, fadeIn: 3, gain: 0.7 },
  ],
  text: [{ t: 16.2, dur: 4.4, it: STRINGS.it.finaleTuoi, en: STRINGS.en.finaleTuoi }],
};

/**
 * Il finale segreto «Nessuno» (da approvare), sui tempi del suono `finale_nessuno` (18 s): all'alba la Madre sale
 * accanto alla barca e si ferma a guardarti, non il secchio (0-3 s); i figli affiorano attorno uno dopo l'altro e
 * restano fermi a fissarti (3-8 s); la vista scende verso l'acqua e la lampara muore (8-10 s); nel buio la ninna nanna
 * canticchiata (10-15 s); a 15 s, taglio netto: l'edicola dello scoglio con le foto dei bambini scomparsi e fra loro
 * la tua, una Polaroid nuova (16,7 s: lo scatto della Polaroid). Dopo il taglio non c'è più il mare.
 */
export const FINALE_NESSUNO: CinematicScript = {
  length: 21.6,
  view: [
    { t: 0, v: [0, -6, 80] },
    // lei sale e ti guarda: l'occhio, da vicino
    { t: 2.6, v: [-64, -8, 62], ease: 'smooth' },
    { t: 3.6, v: [-63, -8, 60] },
    // i figli che affiorano e restano fermi a fissarti: Gulpy e Archie davanti alla prua, poi Archie e Lampy (due
    // panoramiche lente, con una sosta)
    { t: 5.0, v: [-6, -5, 74], ease: 'smooth' },
    { t: 6.0, v: [-2, -5, 74] },
    { t: 7.4, v: [38, -6, 74], ease: 'smooth' },
    { t: 7.99, v: [40, -6, 74] },
    // stacco netto: di nuovo lei, che non ha smesso di guardarti
    { t: 8.0, v: [-60, -10, 62] },
    // la vista scende verso l'acqua accanto a lei, oltre il bordo (dal banco, più giù di così si vedrebbe solo
    // l'interno della fiancata)
    { t: 10.0, v: [-46, -13, 60], ease: 'smooth' },
    { t: 15.0, v: [-44, -15, 56] },
  ],
  dawn: [
    { t: 0, v: 0.1 },
    { t: 8, v: 0.22, ease: 'in' },
  ],
  lamp: [
    { t: 0, v: 1.6 },
    { t: 8.0, v: 1.6 },
    { t: 8.9, v: 0.7 },
    { t: 9.5, v: 0 },
  ],
  creatures: {
    madre: [{ t: 0.2, v: 0 }, { t: 2.6, v: 1, ease: 'smooth' }],
    gulpy: [{ t: 3.1, v: 0 }, { t: 3.8, v: 1, ease: 'out' }],
    archie: [{ t: 3.8, v: 0 }, { t: 4.5, v: 1, ease: 'out' }],
    lampy: [{ t: 4.5, v: 0 }, { t: 5.2, v: 1, ease: 'out' }],
    fangy: [{ t: 5.2, v: 0 }, { t: 5.9, v: 1, ease: 'out' }],
    hatch: [{ t: 5.9, v: 0 }, { t: 6.6, v: 1, ease: 'out' }],
  },
  tilt: [
    { t: 0, v: [0, 0] },
    { t: 2.6, v: [-1.2, 0.4], ease: 'smooth' },
    { t: 8.0, v: [-0.8, 0.3] },
  ],
  black: [
    { t: 0, v: 0 },
    { t: 9.5, v: 0 },
    { t: 10.6, v: 0.94, ease: 'in' },
    { t: 14.97, v: 0.98 },
    // il taglio netto sull'edicola
    { t: 15.0, v: 0 },
    { t: 20.8, v: 0 },
    { t: 21.6, v: 1, ease: 'in' },
  ],
  still: {
    t: 15.0,
    key: 'edicola',
    fade: 0,
    // verso la Polaroid appesa, piano
    move: [
      { t: 15.0, v: [1.0, 0.5, 0.5] },
      { t: 21.6, v: [1.32, 0.585, 0.5], ease: 'smooth' },
    ],
  },
  sounds: [{ t: 0.01, id: 'finale_nessuno' }],
  events: [
    { t: 8.25, e: 'dip' },
    { t: 8.7, e: 'dip' },
    { t: 9.5, e: 'lampOff' },
    { t: 15.0, e: 'quiet' },
  ],
  text: [
    { t: 17.2, dur: 4.0, it: STRINGS.it.finaleNessuno, en: STRINGS.en.finaleNessuno },
  ],
};
