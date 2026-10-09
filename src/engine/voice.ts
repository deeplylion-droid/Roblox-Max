/**
 * Voci borbottate sintetizzate al volo (stile "animalese", ma umano): ogni sillaba è un'onda a dente di sega
 * filtrata da due formanti scelte dalla vocale del testo. Serve per la voce alla radio e per la conta di Hatch,
 * finché non ci saranno voci registrate.
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
  /** scala delle formanti (1 adulto, ~1.25 bambino) */
  formant: number;
  /** filtro da radio VHF */
  radio: boolean;
  gain: number;
}

export const RADIO_VOICE: VoiceProfile = { pitch: 104, jitter: 0.18, rate: 7.2, formant: 1, radio: true, gain: 0.55 };
export const CHILD: VoiceProfile = { pitch: 285, jitter: 0.1, rate: 3.6, formant: 1.28, radio: false, gain: 0.5 };

const FORMANTS: Record<string, [number, number]> = {
  a: [730, 1090],
  e: [530, 1840],
  i: [290, 2250],
  o: [570, 840],
  u: [320, 870],
};

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
function noise(ctx: AudioContext): AudioBuffer {
  if (noiseBuf && noiseBuf.sampleRate === ctx.sampleRate) return noiseBuf;
  const b = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
  const d = b.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  noiseBuf = b;
  return b;
}

function shaper(ctx: AudioContext): WaveShaperNode {
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
  // catena d'uscita
  const out = ctx.createGain();
  out.gain.value = p.gain;
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
    tail = lp;
  }
  const pan = opts.pos ? audio.panner(opts.pos) : null;
  if (pan) {
    tail.connect(pan);
    tail = pan;
  }
  tail.connect(bus);

  const nodes: AudioScheduledSourceNode[] = [];
  let t = ctx.currentTime + 0.05;
  const t0 = t;
  const nb = noise(ctx);
  syl.forEach((s, i) => {
    const len = dur * (s.stress ? 1.15 : 0.92) * (0.85 + Math.random() * 0.3);
    // intonazione: leggera discesa lungo la frase, accento sulle toniche, domanda che sale alla fine
    const prog = i / syl.length;
    const question = text.trim().endsWith('?') && prog > 0.8 ? 1.18 : 1;
    const f0 = p.pitch * (1 + (Math.random() * 2 - 1) * p.jitter * 0.5) * (1.06 - 0.12 * prog) * (s.stress ? 1.08 : 1) * question;
    const osc = ctx.createOscillator();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(f0, t);
    osc.frequency.linearRampToValueAtTime(f0 * (0.94 + Math.random() * 0.08), t + len);
    const [F1, F2] = FORMANTS[s.vowel] ?? FORMANTS['e']!;
    const env = ctx.createGain();
    env.gain.setValueAtTime(0, t);
    env.gain.linearRampToValueAtTime(s.stress ? 1 : 0.75, t + Math.min(0.025, len * 0.3));
    env.gain.setTargetAtTime(0, t + len * 0.62, len * 0.18);
    for (const [f, q, g] of [
      [F1 * p.formant, 7, 1.0],
      [F2 * p.formant, 11, 0.55],
    ] as const) {
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = f;
      bp.Q.value = q;
      const gg = ctx.createGain();
      gg.gain.value = g;
      osc.connect(bp).connect(gg).connect(env);
    }
    env.connect(out);
    osc.start(t);
    osc.stop(t + len + 0.2);
    nodes.push(osc);
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
      n.connect(bp).connect(ng).connect(out);
      n.start(t, Math.random() * 0.8);
      n.stop(t + 0.12);
      nodes.push(n);
    }
    t += len + s.pause * (0.8 + Math.random() * 0.4);
  });
  const end = t;
  let stopped = false;
  nodes[nodes.length - 1]!.onended = () => {
    if (!stopped) setTimeout(() => out.disconnect(), 300);
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
      for (const n of nodes) {
        try {
          n.stop(now + 0.08);
        } catch {
          // già fermato
        }
      }
      setTimeout(() => out.disconnect(), 200);
    },
  };
}
