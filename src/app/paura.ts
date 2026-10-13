/**
 * Il cuore del pescatore e la tensione nella musica («più paura», idee approvate dall'utente il 12 ottobre; i numeri
 * il 13 ottobre). Un solo numero, il pericolo (0..1, lo calcola la notte dagli stati dei mostri), guida:
 * - il battito (cuore_*): dal pericolo 0,15 in su, da 66 a 132 battiti al minuto, sempre più forte; sotto il telone
 *   si sente di più (fuori è tutto ovattato, lui no: è dentro la testa);
 * - il respiro (fiato_*): sempre più corto; quando devi stare immobile (la Madre che passa sotto, Hatch che cerca)
 *   lo trattieni, e quando finisce lo butti fuori;
 * - la tensione (tensione_bassa, tensione_alta): il fondo basso col pericolo medio, quello alto col pericolo forte; al
 *   massimo (un attimo prima del peggio) la musica sparisce di colpo e resta solo il cuore.
 * Solo il presentatore: la simulazione e le regole non cambiano.
 */
import type { AudioEngine, Voice } from '../engine/audio.ts';

const smooth = (a: number, b: number, x: number) => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/** sopra questo pericolo la musica tace (resta il cuore) */
export const PEAK = 0.92;

export class Paura {
  /** il pericolo che si sente (sale in fretta, scende piano) */
  level = 0;
  private beatIn = 0;
  private breathIn = 1.5;
  private inhale = true;
  private held = false;
  private low: Voice | null = null;
  private high: Voice | null = null;
  private on = false;

  constructor(private audio: AudioEngine) {}

  /**
   * Un fotogramma. target: il pericolo di adesso; hold: trattieni il fiato; hidden: sotto il telone; quiet: niente
   * (jumpscare, cinematiche, fine della notte).
   */
  update(dt: number, target: number, o: { hold: boolean; hidden: boolean; quiet: boolean }): void {
    if (o.quiet) {
      this.stop(0.08);
      return;
    }
    this.level += (target - this.level) * (1 - Math.exp(-dt * (target > this.level ? 3.0 : 0.35)));
    const l = this.level;
    this.music(l);
    // il cuore
    if (l > 0.15) {
      this.beatIn -= dt;
      if (this.beatIn <= 0) {
        const bpm = 66 + 66 * l;
        this.beatIn = 60 / bpm;
        const id = l < 0.45 ? 'cuore_1' : l < 0.8 ? 'cuore_2' : 'cuore_3';
        const gain = (0.25 + 0.75 * smooth(0.15, 1, l)) * (o.hidden ? 1.3 : 1);
        this.audio.play(id, { gain, bus: 'body' });
      }
    } else this.beatIn = Math.min(this.beatIn, 0.5);
    // il respiro: trattenuto finché devi stare fermo, poi buttato fuori
    if (o.hold) {
      if (!this.held && l > 0.3) this.audio.play('fiato_dentro_3', { gain: 0.5, bus: 'body' });
      this.held = true;
      return;
    }
    if (this.held) {
      this.held = false;
      this.audio.play('fiato_fuori_2', { gain: 0.55, bus: 'body' });
      this.breathIn = 1.4;
      this.inhale = true;
      return;
    }
    if (l < 0.2) {
      this.breathIn = Math.max(this.breathIn, 1.0);
      return;
    }
    this.breathIn -= dt;
    if (this.breathIn <= 0) {
      const period = 4.2 - 2.7 * l;
      const k = l < 0.45 ? 1 : l < 0.8 ? 2 : 3;
      const gain = 0.15 + 0.4 * smooth(0.2, 1, l);
      this.audio.play(`fiato_${this.inhale ? 'dentro' : 'fuori'}_${k}`, { gain, bus: 'body' });
      this.breathIn = period * (this.inhale ? 0.42 : 0.58) * (0.9 + 0.2 * Math.random());
      this.inhale = !this.inhale;
    }
  }

  /** I due fondi: entrano col pericolo e, al massimo, spariscono di colpo. */
  private music(l: number): void {
    const peak = l > PEAK;
    const lowG = peak ? 0 : 0.55 * smooth(0.15, 0.6, l);
    const highG = peak ? 0 : 0.5 * smooth(0.55, 0.9, l);
    if (!this.on && lowG > 0.001) {
      this.on = true;
      this.low = this.audio.play('tensione_bassa', { loop: true, gain: 0.0001 });
      this.high = this.audio.play('tensione_alta', { loop: true, gain: 0.0001 });
    }
    if (!this.on) return;
    const ramp = peak ? 0.12 : 1.2;
    this.low?.setGain(Math.max(0.0001, lowG), ramp);
    this.high?.setGain(Math.max(0.0001, highG), ramp);
  }

  stop(fade = 0.5): void {
    this.low?.stop(fade);
    this.high?.stop(fade);
    this.low = this.high = null;
    this.on = false;
    this.held = false;
    this.level = 0;
  }
}
