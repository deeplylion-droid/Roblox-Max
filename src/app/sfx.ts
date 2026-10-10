/**
 * Versi delle creature (e qualche suono di gioco che ha bisogno di un po' di regia). Suonano i file
 * sintetizzati da tools/audio (categoria `mon`, con più varianti: gulpy_gurgle_1…4, molly_knock_1…3…):
 * ogni volta una variante a caso, mai la stessa due volte di fila, con piccole variazioni di intonazione e
 * di volume. Se un file manca (manifest vecchio, decodifica non ancora finita) resta il ripiego
 * sintetizzato al volo di prima. I versi sono DA APPROVARE (vedi docs/AUDIO.md).
 */
import type { Vec3 } from '../engine/assets.ts';
import type { AudioEngine, PlayOpts, Voice } from '../engine/audio.ts';
import { CHILD, speak, type VoiceProfile } from '../engine/voice.ts';

export type Creature = 'gulpy' | 'molly' | 'hatch';

/** Opzioni di playAny: quelle di AudioEngine.play più la variazione casuale. */
interface AnyOpts extends PlayOpts {
  /** variazione casuale della velocità (±, frazione: 0.04 ≈ ±0,7 semitoni) */
  spread?: number;
  /** variazione casuale del volume (± dB) */
  spreadDb?: number;
}

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
  /** ultima variante suonata per ogni gruppo (niente ripetizioni immediate) */
  private last = new Map<string, string>();
  private variants = new Map<string, string[]>();
  private rockLoop: Voice | null = null;
  private toyLoop: Voice | null = null;

  constructor(private audio: AudioEngine) {}

  // ───────────────────────── file e varianti ─────────────────────────

  /** Le varianti caricate di un suono: `base` stesso oppure `base_1`, `base_2`… */
  private pool(base: string): string[] {
    let ids = this.variants.get(base);
    if (!ids) {
      const re = new RegExp(`^${base}(_\\d+)?$`);
      ids = Object.keys(this.audio.manifest)
        .filter((k) => re.test(k))
        .sort();
      if (ids.length) this.variants.set(base, ids);
    }
    return ids.filter((id) => this.audio.has(id));
  }

  /** Suona una variante a caso del gruppo `base`; null se non ce n'è nessuna caricata. */
  private playAny(base: string, o: AnyOpts = {}): Voice | null {
    const ids = this.pool(base);
    if (!ids.length) return null;
    const prev = this.last.get(base);
    const choices = ids.length > 1 ? ids.filter((id) => id !== prev) : ids;
    const id = choices[Math.floor(Math.random() * choices.length)]!;
    this.last.set(base, id);
    const { spread = 0.035, spreadDb = 1.5, ...po } = o;
    const rate = (po.rate ?? 1) * (1 + (Math.random() * 2 - 1) * spread);
    const gain = (po.gain ?? 1) * Math.pow(10, ((Math.random() * 2 - 1) * spreadDb) / 20);
    return this.audio.play(id, { ...po, rate, gain });
  }

  private later(ms: number, fn: () => void): void {
    setTimeout(fn, ms);
  }

  // ───────────────────────── Gulpy ─────────────────────────

  /**
   * Gulpy: fiato affamato o gorgoglio (a caso), ogni tanto il salvagente di gomma che cigola sul collo.
   * Con gain ≥ 1,3 (il momento in cui pretende, vedi night.ts) prima si sgancia la mascella.
   */
  gurgle(pos: Vec3, gain = 1): void {
    if (gain >= 1.3 && this.pool('gulpy_jaw').length) {
      this.jaw(pos, Math.min(gain, 1.2));
      this.later(1100, () => this.playAny('gulpy_gurgle', { pos, gain }));
      return;
    }
    const v = (Math.random() < 0.35 ? this.playAny('gulpy_breath', { pos, gain }) : null) ?? this.playAny('gulpy_gurgle', { pos, gain });
    if (v) {
      if (Math.random() < 0.3) this.later(250 + Math.random() * 700, () => this.playAny('gulpy_rubber', { pos, gain: gain * 0.75, spread: 0.06 }));
      return;
    }
    this.synthGurgle(pos, gain);
  }

  /** La mascella di Gulpy che si sgancia fino al petto (schiocchi d'osso, carne che si stira, fiato). */
  jaw(pos: Vec3, gain = 1): void {
    if (this.playAny('gulpy_jaw', { pos, gain, spread: 0.02 })) return;
    this.synthGurgle(pos, gain);
  }

  /**
   * Una creatura che emerge dall'acqua: Gulpy lontano davanti alla prua (scrosci, sbuffo da balena,
   * gemito), Hatch dietro la poppa (l'acqua che gli scorre di dosso, il giocattolo che si accende), Molly
   * accanto al bordo (come peek).
   */
  emerge(who: Creature, pos: Vec3): void {
    if (who === 'molly') return this.peek(pos);
    if (this.playAny(`${who}_rise`, { pos, spread: 0.02 })) return;
    this.audio.play('splash_s3', { pos, gain: 0.8 });
  }

  /** Gulpy riemerge aggrappato alla prua: le mani enormi sul capodibanda, la prua che affonda e geme. */
  grab(pos: Vec3): void {
    if (this.playAny('gulpy_grab', { pos, spread: 0.02 })) return;
    this.audio.play('hull_thump', { pos, gain: 1 });
    this.audio.play('creak_3', { pos, gain: 0.9 });
  }

  /** Mastica e inghiotte (Gulpy ha preso il pesce): morso, lische, deglutizione enorme. */
  chew(pos: Vec3): void {
    if (this.playAny('gulpy_eat', { pos, spread: 0.03 })) return;
    const c = this.chain(pos, 1, 2.5);
    if (!c) return;
    for (let i = 0; i < 5; i++) this.noiseBurst(c.ctx, c.input, c.t + i * 0.34 + Math.random() * 0.06, 0.2, 'lowpass', 500, 1.2, 0.8, 200);
  }

  // ───────────────────────── Molly ─────────────────────────

  /** Le nocche lunghe di Molly sullo scafo. */
  knock(pos: Vec3): void {
    if (this.playAny('molly_knock', { pos, spread: 0.03 })) return;
    if (this.audio.has('hull_thump')) {
      // ripiego: il colpo sotto lo scafo, due volte dal punto giusto
      this.audio.play('hull_thump', { pos, rate: 1.25 + Math.random() * 0.15, gain: 0.8 });
      this.later(260, () => this.audio.play('hull_thump', { pos, rate: 1.3 + Math.random() * 0.15, gain: 0.7 }));
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

  /** Molly si affaccia sul bordo: la testa che esce dall'acqua, le dita bagnate sul capodibanda, un fiato. */
  peek(pos: Vec3): void {
    if (this.playAny('molly_peek', { pos, spread: 0.03 })) return;
    this.audio.play('splash_s1', { pos, gain: 0.5 });
  }

  giggle(pos: Vec3): void {
    if (this.playAny('molly_giggle', { pos })) return;
    this.child('hi hi hi hi', pos, { pitch: 360, rate: 8, jitter: 0.25 }, 0.9);
  }

  whine(pos: Vec3): void {
    if (this.playAny('molly_whine', { pos })) return;
    this.child('uuuh… uuuuh…', pos, { pitch: 300, rate: 2.2, jitter: 0.3 }, 1.8);
  }

  /** Il capriccio: strilli, pugni sullo scafo, la barca che comincia a dondolare (tutto nel file). */
  tantrum(pos: Vec3): void {
    if (this.playAny('molly_tantrum', { pos, spread: 0.025 })) return;
    this.child('aaah! aaah!', pos, { pitch: 380, rate: 4, jitter: 0.35, gain: 0.6 }, 1.2);
    this.knock(pos);
  }

  /**
   * Il dondolio della barca quando Molly si arrabbia (fasciame che geme, acqua che sbatte, roba che si
   * sposta): da chiamare a ogni fotogramma con la forza del dondolio (0..1, es. `v.rock`). Parte e si
   * ferma da solo.
   */
  rock(amount: number): void {
    const a = Math.max(0, Math.min(1, amount));
    if (a > 0.02 && !this.rockLoop && this.audio.has('molly_rock')) this.rockLoop = this.audio.play('molly_rock', { loop: true, gain: 0 });
    if (!this.rockLoop) return;
    this.rockLoop.setGain(Math.pow(a, 0.8), 0.15);
    this.rockLoop.setRate(0.92 + 0.16 * a);
    if (a <= 0.02) {
      this.rockLoop.stop(0.6);
      this.rockLoop = null;
    }
  }

  // ───────────────────────── Hatch ─────────────────────────

  /** Passo bagnato sul pagliolo. */
  step(pos: Vec3): void {
    if (this.playAny('hatch_step', { pos, spread: 0.05 })) return;
    const c = this.chain(pos, 1, 0.6);
    if (!c) return;
    this.noiseBurst(c.ctx, c.input, c.t, 0.16, 'lowpass', 700, 0.7, 0.9);
    this.noiseBurst(c.ctx, c.input, c.t + 0.03, 0.12, 'bandpass', 1900, 3, 0.35, 900);
  }

  /** Annusa. */
  sniff(pos: Vec3): void {
    if (this.playAny('hatch_sniff', { pos, spread: 0.04 })) return;
    const c = this.chain(pos, 1, 1);
    if (!c) return;
    for (let i = 0; i < 3; i++) this.noiseBurst(c.ctx, c.input, c.t + i * 0.13, 0.1, 'bandpass', 2600 + i * 300, 2.2, 0.32, 3600);
  }

  /** Hatch sale a bordo dalla poppa (mano sul capodibanda, acqua che cola, la poppa che affonda e geme). */
  board(pos: Vec3): void {
    if (this.playAny('hatch_board', { pos, spread: 0.02 })) return;
    this.audio.play('hull_thump', { pos, gain: 1 });
    this.audio.play('creak_2', { pos, gain: 1 });
  }

  /**
   * Il ronzio del giocattolo luminoso di Hatch (con il chip che prova a suonare la ninna nanna): da
   * chiamare a ogni fotogramma con la sua intensità (0..1, es. `v.toy`) e la posizione della lucina.
   */
  toy(amount: number, pos?: Vec3): void {
    const a = Math.max(0, Math.min(1, amount));
    if (a > 0.02 && !this.toyLoop && this.audio.has('hatch_toy')) this.toyLoop = this.audio.play('hatch_toy', { loop: true, gain: 0, pos: pos ?? [0, -1.5, -0.4] });
    if (!this.toyLoop) return;
    this.toyLoop.setGain(a, 0.1);
    if (pos) this.toyLoop.setPos(pos);
    if (a <= 0.02) {
      this.toyLoop.stop(0.3);
      this.toyLoop = null;
    }
  }

  /** Ferma i loop di regia (dondolio, giocattolo): da chiamare quando la notte finisce. */
  stopLoops(): void {
    this.rockLoop?.stop(0.4);
    this.toyLoop?.stop(0.4);
    this.rockLoop = this.toyLoop = null;
  }

  // ───────────────────────── jumpscare ─────────────────────────

  /** L'urlo del jumpscare di ciascuna creatura (in faccia, non spazializzato); la voce serve a troncarlo
   *  quando il segnale salta. */
  jumpscare(who: Creature): Voice | null {
    this.stopLoops();
    const v = this.audio.play(`js_${who}`);
    if (!v) this.synthScream(1, who === 'molly' ? 1.35 : who === 'hatch' ? 0.85 : 0.7);
    return v;
  }

  /**
   * Compatibilità con la chiamata di prima (scream(gain, pitch) in night.ts): se ci sono i file sceglie
   * l'urlo dall'intonazione che night.ts usava per ogni creatura (Molly 1,35, Hatch 0,85, Gulpy 0,7).
   * Meglio chiamare jumpscare(who).
   */
  scream(gain = 1, pitch = 1): void {
    const who: Creature = pitch >= 1.15 ? 'molly' : pitch >= 0.78 ? 'hatch' : 'gulpy';
    if (this.audio.has(`js_${who}`)) {
      this.stopLoops();
      this.audio.play(`js_${who}`, { gain });
      return;
    }
    this.synthScream(gain, pitch);
  }

  // ───────────────────────── sonar ─────────────────────────

  /** Bip dell'ecoscandaglio quando arriva qualcosa di grosso: più basso e doppio. */
  sonarWarn(): void {
    if (this.audio.has('sonar_warn')) {
      this.audio.play('sonar_warn', { gain: 0.8 });
      return;
    }
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

  // ───────────────────────── ripieghi sintetizzati al volo ─────────────────────────

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

  /** Voce da bambina deformata (ripiego per Molly). */
  private child(text: string, pos: Vec3, p: Partial<VoiceProfile> = {}, max?: number): void {
    speak(this.audio, text, { ...CHILD, distance: 0, ...p }, { pos, bus: 'sfx', maxDuration: max });
  }

  /** Gorgoglio sintetizzato: bolle che salgono in una gola piena d'acqua e il verso sotto. */
  private synthGurgle(pos: Vec3, gain: number): void {
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

  /** Urlo sintetizzato: seghe stonate che scendono, rumore e saturazione. */
  private synthScream(gain = 1, pitch = 1): void {
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
}
