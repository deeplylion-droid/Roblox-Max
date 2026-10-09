/**
 * Suoni delle creature sintetizzati al volo: sono PROVVISORI, servono a giocare la notte finché non
 * decidiamo insieme quelli veri (vedi docs/AUDIO.md). Dove c'è già un file registrato lo usano.
 */
import type { Vec3 } from '../engine/assets.ts';
import type { AudioEngine } from '../engine/audio.ts';
import { CHILD, speak, type VoiceProfile } from '../engine/voice.ts';

let noiseBuf: AudioBuffer | null = null;
function noise(ctx: AudioContext): AudioBuffer {
  if (noiseBuf && noiseBuf.sampleRate === ctx.sampleRate) return noiseBuf;
  const b = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
  const d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  noiseBuf = b;
  return b;
}

function distortion(ctx: AudioContext, amount: number): WaveShaperNode {
  const ws = ctx.createWaveShaper();
  const c = new Float32Array(2048);
  for (let i = 0; i < c.length; i++) {
    const x = (i / (c.length - 1)) * 2 - 1;
    c[i] = Math.tanh(x * amount) / Math.tanh(amount);
  }
  ws.curve = c;
  return ws;
}

export class Sfx {
  constructor(private audio: AudioEngine) {}

  /** Catena d'uscita usa e getta: guadagno → (panner) → bus. */
  private chain(pos: Vec3 | undefined, gain: number, life: number, bus: 'sfx' | 'voice' = 'sfx'): { ctx: AudioContext; input: GainNode; t: number } | null {
    const ctx = this.audio.ctx;
    const b = this.audio.bus(bus);
    if (!ctx || !b) return null;
    const g = ctx.createGain();
    g.gain.value = gain;
    let tail: AudioNode = g;
    const p = pos ? this.audio.panner(pos) : null;
    if (p) {
      g.connect(p);
      tail = p;
    }
    tail.connect(b);
    setTimeout(() => {
      g.disconnect();
      p?.disconnect();
    }, (life + 0.5) * 1000);
    return { ctx, input: g, t: ctx.currentTime + 0.01 };
  }

  private noiseBurst(ctx: AudioContext, dest: AudioNode, t: number, dur: number, type: BiquadFilterType, freq: number, q: number, peak: number, freqEnd?: number): void {
    const n = ctx.createBufferSource();
    n.buffer = noise(ctx);
    const f = ctx.createBiquadFilter();
    f.type = type;
    f.frequency.setValueAtTime(freq, t);
    if (freqEnd) f.frequency.exponentialRampToValueAtTime(freqEnd, t + dur);
    f.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(peak, t + Math.min(0.012, dur * 0.2));
    g.gain.exponentialRampToValueAtTime(0.0008, t + dur);
    n.connect(f).connect(g).connect(dest);
    n.start(t, Math.random() * 1.5);
    n.stop(t + dur + 0.05);
  }

  /** Gorgoglio: bolle che salgono in una gola piena d'acqua. */
  gurgle(pos: Vec3, gain = 1): void {
    const c = this.chain(pos, gain, 2);
    if (!c) return;
    const { ctx, input } = c;
    let t = c.t;
    const n = 9 + Math.floor(Math.random() * 6);
    for (let i = 0; i < n; i++) {
      const f = 180 + Math.random() * 420;
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.setValueAtTime(f, t);
      o.frequency.exponentialRampToValueAtTime(f * (1.6 + Math.random()), t + 0.06);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.35, t + 0.008);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.09);
      o.connect(g).connect(input);
      o.start(t);
      o.stop(t + 0.12);
      t += 0.04 + Math.random() * 0.1;
    }
    // il verso affamato sotto le bolle
    const o = ctx.createOscillator();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(62, c.t);
    o.frequency.linearRampToValueAtTime(48, c.t + 1.1);
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 260;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, c.t);
    g.gain.linearRampToValueAtTime(0.28, c.t + 0.2);
    g.gain.linearRampToValueAtTime(0, c.t + 1.2);
    o.connect(lp).connect(g).connect(input);
    o.start(c.t);
    o.stop(c.t + 1.3);
  }

  /** Toc toc sullo scafo. */
  knock(pos: Vec3): void {
    if (this.audio.has('hull_thump')) {
      // il file registrato, due colpi dal punto giusto
      this.audio.play('hull_thump', { pos, rate: 1.25 + Math.random() * 0.15, gain: 0.8 });
      setTimeout(() => this.audio.play('hull_thump', { pos, rate: 1.3 + Math.random() * 0.15, gain: 0.7 }), 260);
      return;
    }
    const c = this.chain(pos, 1, 1.2);
    if (!c) return;
    for (let i = 0; i < 2; i++) {
      const t = c.t + i * 0.26;
      const o = c.ctx.createOscillator();
      o.type = 'sine';
      o.frequency.setValueAtTime(150, t);
      o.frequency.exponentialRampToValueAtTime(70, t + 0.12);
      const g = c.ctx.createGain();
      g.gain.setValueAtTime(0.9, t);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
      o.connect(g).connect(c.input);
      o.start(t);
      o.stop(t + 0.2);
      this.noiseBurst(c.ctx, c.input, t, 0.05, 'bandpass', 900, 1.5, 0.5);
    }
  }

  /** Voce da bambina deformata. */
  private child(text: string, pos: Vec3, p: Partial<VoiceProfile> = {}, max?: number): void {
    speak(this.audio, text, { ...CHILD, ...p }, { pos, bus: 'sfx', maxDuration: max });
  }

  giggle(pos: Vec3): void {
    this.child('hi hi hi hi', pos, { pitch: 360, rate: 8, jitter: 0.25 }, 0.9);
  }

  whine(pos: Vec3): void {
    this.child('uuuh… uuuuh…', pos, { pitch: 300, rate: 2.2, jitter: 0.3 }, 1.8);
  }

  tantrum(pos: Vec3): void {
    this.child('aaah! aaah!', pos, { pitch: 380, rate: 4, jitter: 0.35, gain: 0.6 }, 1.2);
    this.knock(pos);
  }

  /** Passo bagnato sul pagliolo. */
  step(pos: Vec3): void {
    const c = this.chain(pos, 1, 0.6);
    if (!c) return;
    this.noiseBurst(c.ctx, c.input, c.t, 0.16, 'lowpass', 700, 0.7, 0.9);
    this.noiseBurst(c.ctx, c.input, c.t + 0.03, 0.12, 'bandpass', 1900, 3, 0.35, 900);
  }

  /** Annusa: tre inspirazioni rapide. */
  sniff(pos: Vec3): void {
    const c = this.chain(pos, 1, 1);
    if (!c) return;
    for (let i = 0; i < 3; i++) this.noiseBurst(c.ctx, c.input, c.t + i * 0.13, 0.1, 'bandpass', 2600 + i * 300, 2.2, 0.32, 3600);
  }

  /** Urlo del jumpscare: seghe stonate che scendono, rumore e saturazione. */
  scream(gain = 1, pitch = 1): void {
    const c = this.chain(undefined, 0.75 * gain, 2.2);
    if (!c) return;
    const { ctx, input, t } = c;
    const ws = distortion(ctx, 3.5);
    const hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 160;
    const env = ctx.createGain();
    env.gain.setValueAtTime(0, t);
    env.gain.linearRampToValueAtTime(1, t + 0.02);
    env.gain.setValueAtTime(1, t + 0.9);
    env.gain.exponentialRampToValueAtTime(0.001, t + 1.8);
    ws.connect(hp).connect(env).connect(input);
    for (const det of [0.97, 1.0, 1.035, 1.51]) {
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      const f = 760 * pitch * det;
      o.frequency.setValueAtTime(f * 0.6, t);
      o.frequency.exponentialRampToValueAtTime(f, t + 0.08);
      o.frequency.exponentialRampToValueAtTime(f * 0.55, t + 1.7);
      const lfo = ctx.createOscillator();
      lfo.frequency.value = 11 + Math.random() * 6;
      const lg = ctx.createGain();
      lg.gain.value = f * 0.04;
      lfo.connect(lg).connect(o.frequency);
      const g = ctx.createGain();
      g.gain.value = 0.22;
      o.connect(g).connect(ws);
      o.start(t);
      lfo.start(t);
      o.stop(t + 1.9);
      lfo.stop(t + 1.9);
    }
    this.noiseBurst(ctx, ws, t, 1.6, 'bandpass', 2400, 0.8, 0.5, 900);
  }

  /** Bip dell'ecoscandaglio quando arriva qualcosa di grosso: più basso e doppio. */
  sonarWarn(): void {
    const c = this.chain(undefined, 0.4, 1, 'sfx');
    if (!c) return;
    for (const [dt, f] of [
      [0, 520],
      [0.2, 390],
    ] as const) {
      const o = c.ctx.createOscillator();
      o.type = 'triangle';
      o.frequency.value = f;
      const g = c.ctx.createGain();
      g.gain.setValueAtTime(0, c.t + dt);
      g.gain.linearRampToValueAtTime(0.8, c.t + dt + 0.01);
      g.gain.exponentialRampToValueAtTime(0.001, c.t + dt + 0.32);
      o.connect(g).connect(c.input);
      o.start(c.t + dt);
      o.stop(c.t + dt + 0.35);
    }
  }

  /** Mastica (Gulpy che inghiotte il pesce). */
  chew(pos: Vec3): void {
    const c = this.chain(pos, 1, 2.5);
    if (!c) return;
    for (let i = 0; i < 5; i++) this.noiseBurst(c.ctx, c.input, c.t + i * 0.34 + Math.random() * 0.06, 0.2, 'lowpass', 500, 1.2, 0.8, 200);
  }
}
