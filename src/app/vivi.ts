/**
 * Le creature vive («più paura», idea approvata dall'utente il 12 ottobre; i numeri sono da approvare): mentre
 * aspettano respirano (lo strato si allunga e si accorcia piano attorno alla base) e, quando le guardi, ogni tanto la
 * testa scatta (un colpo di rotazione, un attimo fermo, e torna). Chi è appena uscito dall'acqua gocciola. Solo il
 * presentatore: la simulazione e le regole non cambiano.
 */
import type { LayerInfo } from '../engine/assets.ts';

export interface Vivo {
  /** quanto si allunga col respiro (frazione dell'altezza) e quanti respiri al secondo */
  amp: number;
  hz: number;
  /** l'angolo dello scatto della testa (radianti); 0: non scatta */
  twitch: number;
  /** dov'è il collo, in frazione dell'altezza della posa dal basso: sopra ruota la testa */
  neck: number;
  /** gocciola (appena uscito dall'acqua) */
  wet: boolean;
}

/** I numeri di ognuno (da approvare). La Madre respira piano e non scatta. */
export const VIVI: Record<string, Vivo> = {
  gulpy: { amp: 0.011, hz: 0.24, twitch: 0.07, neck: 0.62, wet: true },
  mollyR: { amp: 0.008, hz: 0.31, twitch: 0.06, neck: 0.5, wet: true },
  mollyL: { amp: 0.008, hz: 0.29, twitch: 0.06, neck: 0.5, wet: true },
  hatch: { amp: 0.006, hz: 0.2, twitch: 0.05, neck: 0.74, wet: true },
  robin: { amp: 0.006, hz: 0.36, twitch: 0, neck: 0.5, wet: true },
  archie: { amp: 0.008, hz: 0.18, twitch: 0.05, neck: 0.7, wet: true },
  lampy: { amp: 0.009, hz: 0.27, twitch: 0.07, neck: 0.55, wet: true },
  fangy: { amp: 0.006, hz: 0.22, twitch: 0.05, neck: 0.7, wet: true },
  madre: { amp: 0.004, hz: 0.09, twitch: 0, neck: 0.5, wet: false },
};

/** Di chi è uno strato: le pose e le loro toppe prendono lo stesso respiro e lo stesso scatto. */
export const VIVO_DI: Record<string, string> = {
  gulpy_sale: 'gulpy',
  gulpy_pretende: 'gulpy',
  gulpy_mascella_aperta: 'gulpy',
  gulpy_mascella_chiusa: 'gulpy',
  molly_destra: 'mollyR',
  molly_destra_primo: 'mollyR',
  molly_destra_secondo: 'mollyR',
  molly_sinistra: 'mollyL',
  molly_sinistra_primo: 'mollyL',
  molly_sinistra_secondo: 'mollyL',
  hatch_conta: 'hatch',
  hatch_bocca_mezza: 'hatch',
  hatch_bocca_chiusa: 'hatch',
  robin_secchio: 'robin',
  robin_strizza: 'robin',
  robin_chiusi: 'robin',
  archie_soffia: 'archie',
  archie_trombetta_mezza: 'archie',
  archie_trombetta_tutta: 'archie',
  archie_fiato: 'archie',
  lampy_lenza: 'lampy',
  lampy_bocca_chiusa: 'lampy',
  lampy_bocca_aperta: 'lampy',
  fangy_ascolta: 'fangy',
  fangy_testa_prua: 'fangy',
  fangy_testa_poppa: 'fangy',
  madre_sale: 'madre',
};

/** Lo scatto nel tempo: arriva in 70 ms, resta un attimo tremando, torna piano. */
export function twitchEnvelope(t: number): number {
  if (t < 0) return 0;
  if (t < 0.07) {
    const x = t / 0.07;
    return 1 - (1 - x) * (1 - x);
  }
  if (t < 0.34) return 1;
  if (t < 0.85) {
    const x = (t - 0.34) / 0.51;
    return 1 - x * x * (3 - 2 * x);
  }
  return 0;
}

interface State {
  presence: number;
  /** da quanto è tutta fuori (s) */
  shown: number;
  /** lo scatto in corso: da quanto (s), verso dove (±1); prossimo scatto possibile fra (s) */
  tw: number;
  dir: number;
  next: number;
  drip: number;
  phase: number;
}

export class Vivi {
  private s = new Map<string, State>();
  /** il generatore dei numeri a caso (sostituibile nei test) */
  constructor(private rnd: () => number = Math.random) {}

  private state(id: string): State {
    let st = this.s.get(id);
    if (!st) {
      st = { presence: 0, shown: 0, tw: -1, dir: 1, next: 4 + 6 * this.rnd(), drip: 0.5 + this.rnd(), phase: this.rnd() * Math.PI * 2 };
      this.s.set(id, st);
    }
    return st;
  }

  /**
   * Un fotogramma. presence: quanto è fuori ognuno (0..1); looked: lo stai guardando; quiet: niente scatti né gocce
   * (jumpscare, cinematiche). onTwitch e onDrip suonano lo scatto e la goccia.
   */
  update(dt: number, presence: Record<string, number>, looked: (id: string) => boolean, quiet: boolean, onTwitch: (id: string) => void, onDrip: (id: string) => void): void {
    for (const [id, cfg] of Object.entries(VIVI)) {
      const st = this.state(id);
      st.presence = presence[id] ?? 0;
      st.shown = st.presence > 0.98 ? st.shown + dt : 0;
      st.phase += dt * cfg.hz * Math.PI * 2;
      if (st.tw >= 0) {
        st.tw += dt;
        if (st.tw > 0.9) st.tw = -1;
      }
      st.next -= dt;
      if (!quiet && cfg.twitch > 0 && st.tw < 0 && st.next <= 0 && st.shown > 1.2 && looked(id)) {
        st.tw = 0;
        st.dir = this.rnd() < 0.5 ? -1 : 1;
        st.next = 6 + 7 * this.rnd();
        onTwitch(id);
      }
      if (!quiet && cfg.wet && st.presence > 0.5) {
        st.drip -= dt;
        if (st.drip <= 0) {
          st.drip = 0.8 + 1.7 * this.rnd();
          onDrip(id);
        }
      }
    }
  }

  /** Il warp di uno strato di questa creatura: il respiro attorno alla base della posa, e lo scatto. */
  warp(id: string, base: LayerInfo): { anchor: [number, number]; scale: number; rot: number; neck: number; band: number } | undefined {
    const cfg = VIVI[id];
    const st = this.s.get(id);
    if (!cfg || !st || st.presence < 0.002) return undefined;
    const r = base.rect;
    // il respiro: un po' più lungo a inspirare che a espirare (il seno storto)
    const b = Math.sin(st.phase + 0.35 * Math.sin(st.phase));
    const scale = 1 + cfg.amp * b * st.presence;
    const rot = st.tw >= 0 ? st.dir * cfg.twitch * twitchEnvelope(st.tw) * (1 + 0.08 * Math.sin(st.tw * 90)) : 0;
    const hgt = r[3] - r[1];
    return { anchor: [(r[0] + r[2]) / 2, r[3]], scale, rot, neck: r[3] - cfg.neck * hgt, band: 0.06 * hgt };
  }
}
