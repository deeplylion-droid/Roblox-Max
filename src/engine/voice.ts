/**
 * Voci borbottate sintetizzate al volo (stile "animalese", ma umano): ogni sillaba è un'onda glottale (lo
 * spettro scende di 12 dB per ottava, come una gola vera, non il ronzio di un dente di sega) filtrata da tre
 * formanti scelte dalla vocale del testo, con un filo di soffio, un vibrato irregolare e le formanti che
 * scivolano da una sillaba all'altra. Serve per la voce alla radio e per la conta di Hatch.
 * Il profilo del bambino aggiunge la "gola sotto" (la stessa voce, più grave e scura, da una gola enorme),
 * un tremolio d'acqua nel fiato, la coda che cala alla fine di ogni parola e la distanza (ovattata, con l'eco
 * corta dello scafo e dell'acqua).
 */
import type { AudioEngine } from './audio.ts';
import type { Vec3 } from './assets.ts';

export interface VoiceProfile {
  /** fondamentale (Hz) */
  pitch: number;
  /** variazione casuale dell'intonazione (0..1) */
  jitter: number;
  /** sillabe al secondo (massimo) */
  rate: number;
  /** scala delle formanti (1 adulto, ~1.3 bambino) */
  formant: number;
  /** filtro da radio VHF */
  radio: boolean;
  gain: number;
  /** soffio sulle vocali (0..1) */
  breath?: number;
  /** profondità del vibrato (frazione dell'intonazione, es. 0.015) */
  vibrato?: number;
  /** quanto cala il tono alla fine di ogni sillaba (frazione, es. 0.06) */
  droop?: number;
  /** "gola sotto": livello della stessa voce più grave e scura (0 = niente) */
  ghost?: number;
  /** gola bagnata: tremolio irregolare del fiato (0..1) */
  wet?: number;
  /** distanza: 0 vicino, 1 lontano (passa-basso, eco corta dell'acqua e dello scafo) */
  distance?: number;
}

export const RADIO_VOICE: VoiceProfile = { pitch: 104, jitter: 0.18, rate: 7.2, formant: 1, radio: true, gain: 0.55, breath: 0.12, vibrato: 0.006 };
export const CHILD: VoiceProfile = {
  pitch: 285,
  jitter: 0.1,
  rate: 3.6,
  formant: 1.36,
  radio: false,
  gain: 0.5,
  breath: 0.32,
  vibrato: 0.016,
  droop: 0.07,
  ghost: 0.2,
  wet: 0.3,
  distance: 0.55,
};

/** Prime tre formanti (Hz, voce adulta) e loro peso relativo. */
const FORMANTS: Record<string, [number, number, number]> = {
  a: [730, 1090, 2440],
  e: [530, 1840, 2480],
  i: [290, 2250, 2890],
  o: [570, 840, 2410],
  u: [320, 870, 2240],
};
const NEUTRAL: [number, number, number] = [500, 1500, 2500];

interface Syl {
  vowel: string;
  /** consonante d'attacco (rumore) */
  hiss: number;
  /** pausa dopo la sillaba (s) */
  pause: number;
  stress: boolean;
}

function syllables(text: string): Syl[] {
  const out: Syl[] = [];
  const t = text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
  const words = t.split(/\s+/).filter(Boolean);
  for (const w of words) {
    const groups = w.match(/[aeiouy]+/g) ?? [];
    const cons = w.match(/[^aeiouy\W\d]+/g) ?? [];
    const n = Math.max(1, groups.length);
    for (let i = 0; i < n; i++) {
      const g = groups[i] ?? 'e';
      const v = g.replace('y', 'i')[0]!;
      const c = cons[i] ?? '';
      const sibilant = /[szcfx]/.test(c) ? 1 : /[tkpg]/.test(c) ? 0.55 : c ? 0.25 : 0;
      out.push({ vowel: v, hiss: sibilant, pause: 0, stress: i === Math.max(0, n - 2) });
    }
    const last = out[out.length - 1]!;
    if (/[.!?…]$/.test(w)) last.pause = 0.34;
    else if (/[,;:]$/.test(w)) last.pause = 0.17;
    else last.pause = 0.035;
  }
  return out;
}

let noiseBuf: AudioBuffer | null = null;
function noise(ctx: BaseAudioContext): AudioBuffer {
  if (noiseBuf && noiseBuf.sampleRate === ctx.sampleRate) return noiseBuf;
  const b = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
  const d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  noiseBuf = b;
  return b;
}

/** Onda glottale: armoniche che calano di 12 dB per ottava, con un'increspatura (apertura delle corde). */
const waves = new WeakMap<BaseAudioContext, PeriodicWave>();
function glottalWave(ctx: BaseAudioContext): PeriodicWave {
  let w = waves.get(ctx);
  if (w) return w;
  const N = 48;
  const re = new Float32Array(N + 1);
  const im = new Float32Array(N + 1);
  for (let k = 1; k <= N; k++) {
    im[k] = (1 / (k * k)) * (1 + 0.35 * Math.cos(k * 1.9));
  }
  w = ctx.createPeriodicWave(re, im, { disableNormalization: false });
  waves.set(ctx, w);
  return w;
}

function shaper(ctx: BaseAudioContext): WaveShaperNode {
  const ws = ctx.createWaveShaper();
  const c = new Float32Array(1024);
  for (let i = 0; i < c.length; i++) {
    const x = (i / (c.length - 1)) * 2 - 1;
    c[i] = Math.tanh(x * 2.2) / Math.tanh(2.2);
  }
  ws.curve = c;
  return ws;
}

export interface Utterance {
  /** durata effettiva (s) */
  duration: number;
  stop(): void;
}

/**
 * Pronuncia 'text' a partire da adesso, stando nei 'maxDuration' secondi.
 * pos: posizione nello spazio (coordinate dei render); senza, la voce è centrata.
 */
export function speak(audio: AudioEngine, text: string, p: VoiceProfile, opts: { maxDuration?: number; pos?: Vec3; bus?: 'voice' | 'sfx' } = {}): Utterance | null {
  const ctx = audio.ctx;
  const bus = audio.bus(opts.bus ?? 'voice');
  if (!ctx || !bus || !text.trim()) return null;
  const syl = syllables(text);
  if (syl.length === 0) return null;
  // ritmo: non più veloce di p.rate, ma abbastanza da stare nel tempo disponibile
  const pauses = syl.reduce((s, x) => s + x.pause, 0);
  let dur = 1 / p.rate;
  if (opts.maxDuration) {
    const need = (opts.maxDuration * 0.92 - pauses) / syl.length;
    dur = Math.min(Math.max(need, 1 / (p.rate * 1.35)), 1 / (p.rate * 0.55));
  }
  const breath = p.breath ?? 0;
  const vib = p.vibrato ?? 0;
  const droop = p.droop ?? 0;
  const ghost = p.ghost ?? 0;
  const wet = p.wet ?? 0;
  const dist = p.distance ?? 0;

  // catena d'uscita: sillabe → tremolio (gola bagnata) → volume → [radio] → [distanza] → [posizione] → bus
  const chain: AudioNode[] = [];
  const trem = ctx.createGain();
  const out = ctx.createGain();
  out.gain.value = p.gain;
  trem.connect(out);
  chain.push(trem, out);
  let tail: AudioNode = out;
  if (p.radio) {
    const hp = ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 320;
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 2900;
    const ws = shaper(ctx);
    out.connect(hp).connect(ws).connect(lp);
    chain.push(hp, ws, lp);
    tail = lp;
  }
  if (dist > 0) {
    // lontano: gli acuti se ne vanno, e torna un'eco corta e scura (lo scafo, il pelo dell'acqua)
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 9000 * Math.pow(0.28, dist);
    lp.Q.value = 0.5;
    const sum = ctx.createGain();
    const dl = ctx.createDelay(0.5);
    dl.delayTime.value = 0.075 + 0.03 * dist;
    const fb = ctx.createGain();
    fb.gain.value = 0.22;
    const dlp = ctx.createBiquadFilter();
    dlp.type = 'lowpass';
    dlp.frequency.value = 1600;
    const wetG = ctx.createGain();
    wetG.gain.value = 0.35 * dist;
    tail.connect(lp);
    lp.connect(sum);
    lp.connect(dl);
    dl.connect(dlp).connect(fb).connect(dl);
    dlp.connect(wetG).connect(sum);
    chain.push(lp, sum, dl, fb, dlp, wetG);
    tail = sum;
  }
  const pan = opts.pos ? audio.panner(opts.pos) : null;
  if (pan) {
    tail.connect(pan);
    chain.push(pan);
    tail = pan;
  }
  tail.connect(bus);

  const nodes: AudioScheduledSourceNode[] = [];
  let t = ctx.currentTime + 0.05;
  const t0 = t;
  const nb = noise(ctx);
  const wave = glottalWave(ctx);

  // vibrato irregolare (due oscillatori lenti) condiviso da tutte le sillabe
  const mods: AudioScheduledSourceNode[] = [];
  const vibG = ctx.createGain();
  vibG.gain.value = p.pitch * vib;
  if (vib > 0) {
    for (const [f, a] of [
      [5.1 + Math.random() * 0.8, 1],
      [0.7 + Math.random() * 0.4, 0.8],
    ] as const) {
      const lfo = ctx.createOscillator();
      lfo.frequency.value = f;
      const g = ctx.createGain();
      g.gain.value = a;
      lfo.connect(g).connect(vibG);
      mods.push(lfo);
      chain.push(g);
    }
  }
  chain.push(vibG);
  // gola bagnata: il fiato che trema in modo irregolare
  if (wet > 0) {
    const tg = ctx.createGain();
    tg.gain.value = 0.3 * wet;
    for (const f of [16 + Math.random() * 4, 6.3 + Math.random()]) {
      const lfo = ctx.createOscillator();
      lfo.frequency.value = f;
      lfo.connect(tg);
      mods.push(lfo);
    }
    tg.connect(trem.gain);
    trem.gain.value = 1 - 0.3 * wet;
    chain.push(tg);
  }

  let prevF = NEUTRAL;
  let lastOsc: OscillatorNode | null = null;
  syl.forEach((s, i) => {
    const len = dur * (s.stress ? 1.15 : 0.92) * (0.85 + Math.random() * 0.3);
    // intonazione: leggera discesa lungo la frase, accento sulle toniche, domanda che sale alla fine
    const prog = i / syl.length;
    const question = text.trim().endsWith('?') && prog > 0.8 ? 1.18 : 1;
    const f0 = p.pitch * (1 + (Math.random() * 2 - 1) * p.jitter * 0.5) * (1.06 - 0.12 * prog) * (s.stress ? 1.08 : 1) * question;
    const fEnd = f0 * (0.94 + Math.random() * 0.08) * (1 - droop * (s.pause > 0.1 ? 1.6 : 1));
    const F = FORMANTS[s.vowel] ?? FORMANTS['e']!;
    const env = ctx.createGain();
    env.gain.setValueAtTime(0, t);
    env.gain.linearRampToValueAtTime(s.stress ? 1 : 0.75, t + Math.min(0.025, len * 0.3));
    env.gain.setTargetAtTime(0, t + len * 0.62, len * 0.18);
    env.connect(trem);
    chain.push(env);
    // tre formanti in parallelo, che arrivano dalla vocale di prima (coarticolazione)
    const bps: BiquadFilterNode[] = [];
    const weights = s.vowel === 'i' ? [1.0, 0.55, 0.4] : [1.0, 0.6, 0.28];
    for (let k = 0; k < 3; k++) {
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.setValueAtTime(prevF[k]! * p.formant, t);
      bp.frequency.setTargetAtTime(F[k]! * p.formant, t, 0.028);
      bp.Q.value = [6, 10, 14][k]! / Math.sqrt(p.formant);
      const gg = ctx.createGain();
      gg.gain.value = weights[k]!;
      bp.connect(gg).connect(env);
      bps.push(bp);
      chain.push(bp, gg);
    }
    prevF = F;
    const osc = ctx.createOscillator();
    osc.setPeriodicWave(wave);
    osc.frequency.setValueAtTime(f0, t);
    osc.frequency.linearRampToValueAtTime(fEnd, t + len);
    vibG.connect(osc.frequency);
    for (const bp of bps) osc.connect(bp);
    osc.start(t);
    osc.stop(t + len + 0.2);
    nodes.push(osc);
    lastOsc = osc;
    // soffio sulle vocali, filtrato dalle stesse formanti
    if (breath > 0) {
      const n = ctx.createBufferSource();
      n.buffer = nb;
      const ng = ctx.createGain();
      ng.gain.value = 0.9 * breath;
      n.connect(ng);
      for (const bp of bps) ng.connect(bp);
      n.start(t, Math.random() * 0.8);
      n.stop(t + len + 0.2);
      nodes.push(n);
      chain.push(ng);
    }
    // la gola sotto: la stessa sillaba, poco meno di un'ottava più giù, da un tratto vocale enorme
    if (ghost > 0) {
      const go = ctx.createOscillator();
      go.setPeriodicWave(wave);
      go.frequency.setValueAtTime(f0 * 0.48, t);
      go.frequency.linearRampToValueAtTime(fEnd * 0.46, t + len);
      const gEnv = ctx.createGain();
      gEnv.gain.value = ghost;
      for (let k = 0; k < 2; k++) {
        const bp = ctx.createBiquadFilter();
        bp.type = 'bandpass';
        bp.frequency.value = F[k]! * 0.72;
        bp.Q.value = 5;
        go.connect(bp).connect(gEnv);
        chain.push(bp);
      }
      gEnv.connect(env);
      chain.push(gEnv);
      go.start(t);
      go.stop(t + len + 0.2);
      nodes.push(go);
    }
    if (s.hiss > 0) {
      const n = ctx.createBufferSource();
      n.buffer = nb;
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = s.hiss > 0.8 ? 5200 * p.formant : 2400 * p.formant;
      bp.Q.value = 1.2;
      const ng = ctx.createGain();
      ng.gain.setValueAtTime(0, t);
      ng.gain.linearRampToValueAtTime(0.18 * s.hiss, t + 0.008);
      ng.gain.exponentialRampToValueAtTime(0.001, t + 0.05 + 0.03 * s.hiss);
      n.connect(bp).connect(ng).connect(trem);
      n.start(t, Math.random() * 0.8);
      n.stop(t + 0.12);
      nodes.push(n);
      chain.push(bp, ng);
    }
    t += len + s.pause * (0.8 + Math.random() * 0.4);
  });
  const end = t;
  for (const m of mods) {
    m.start(t0);
    m.stop(end + 0.4);
  }
  let stopped = false;
  let released = false;
  const release = () => {
    if (released) return;
    released = true;
    for (const n of chain) n.disconnect();
  };
  // l'eco della distanza ha bisogno di un attimo per spegnersi
  const tailTime = 300 + dist * 900;
  (lastOsc ?? nodes[nodes.length - 1]!).onended = () => {
    if (!stopped) setTimeout(release, tailTime);
  };
  return {
    duration: end - t0,
    stop() {
      if (stopped) return;
      stopped = true;
      const now = ctx.currentTime;
      out.gain.cancelScheduledValues(now);
      out.gain.setValueAtTime(out.gain.value, now);
      out.gain.linearRampToValueAtTime(0, now + 0.06);
      for (const n of [...nodes, ...mods]) {
        try {
          n.stop(now + 0.08);
        } catch {
          // già fermato
        }
      }
      setTimeout(release, 200);
    },
  };
}
