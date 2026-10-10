/**
 * Audio di SPLASHLAND IS CLOSED!: Web Audio con suoni spazializzati (HRTF) attorno al pescatore.
 * Coordinate come i render (x destra, y avanti, z alto, metri dall'occhio); il motore le converte
 * nel sistema di Web Audio (x destra, y alto, −z avanti).
 */
import { ASSET_BASE, type Vec3 } from './assets.ts';

export interface SoundInfo {
  file: string;
  duration: number;
  loop: boolean;
  channels: number;
  gain: number;
  category: 'amb' | 'sfx' | 'mon' | 'mus' | 'ui' | 'voice';
}

export interface PlayOpts {
  gain?: number;
  rate?: number;
  pos?: Vec3;
  loop?: boolean;
  /** secondi di dissolvenza in ingresso */
  fadeIn?: number;
  /** filtro passa-basso (Hz), per suoni ovattati (sotto il telone) */
  lowpass?: number;
  bus?: 'music' | 'sfx' | 'amb' | 'ui' | 'voice';
}

export interface Voice {
  stop(fade?: number): void;
  setGain(g: number, ramp?: number): void;
  setRate(r: number): void;
  setPos(p: Vec3): void;
  /** sposta il passa-basso (solo se la voce è partita con lowpass) */
  setLowpass(hz: number, ramp?: number): void;
  readonly ended: boolean;
}

export class AudioEngine {
  ctx: AudioContext | null = null;
  private buffers = new Map<string, AudioBuffer>();
  manifest: Record<string, SoundInfo> = {};
  private master!: GainNode;
  private buses: Record<string, GainNode> = {};
  private muffle!: BiquadFilterNode;
  volumes = { master: 0.9, music: 0.7, sfx: 0.9, amb: 0.8, voice: 0.9, ui: 0.6 };

  async load(): Promise<void> {
    const r = await fetch(ASSET_BASE + 'audio/manifest.json');
    this.manifest = r.ok ? ((await r.json()) as Record<string, SoundInfo>) : {};
  }

  private loading: Promise<void> | null = null;

  /** Carica tutti i suoni. Va chiamato dopo un gesto dell'utente (policy dei browser): riattiva il contesto
   *  se il browser l'aveva creato sospeso. */
  async start(): Promise<void> {
    const ctx = this.open();
    if (ctx.state === 'suspended') void ctx.resume().catch(() => {});
    this.loading ??= Promise.all(Object.keys(this.manifest).map((id) => this.decode(id))).then(() => {});
    await this.loading;
  }

  /** Carica subito un suono solo, anche prima di un gesto dell'utente (la ninna nanna dell'avvio). Dove il
   *  browser non lascia partire l'audio da solo il contesto resta sospeso: quello che si suona parte, dal
   *  principio, al primo tasto. In Electron parte subito. */
  async preload(id: string): Promise<void> {
    const ctx = this.open();
    if (ctx.state === 'suspended') void ctx.resume().catch(() => {});
    await this.decode(id);
  }

  private open(): AudioContext {
    if (this.ctx) return this.ctx;
    const ctx = (this.ctx = new AudioContext({ latencyHint: 'interactive' }));
    this.master = ctx.createGain();
    // un leggero compressore evita che i jumpscare saturino
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -10;
    comp.ratio.value = 6;
    comp.attack.value = 0.003;
    comp.release.value = 0.2;
    this.muffle = ctx.createBiquadFilter();
    this.muffle.type = 'lowpass';
    this.muffle.frequency.value = 20000;
    this.master.connect(this.muffle).connect(comp).connect(ctx.destination);
    for (const b of ['music', 'sfx', 'amb', 'ui', 'voice']) {
      const g = ctx.createGain();
      g.connect(this.master);
      this.buses[b] = g;
    }
    this.applyVolumes();
    const l = ctx.listener;
    if (l.positionX) {
      l.positionX.value = 0;
      l.positionY.value = 0;
      l.positionZ.value = 0;
    }
    return ctx;
  }

  applyVolumes(): void {
    if (!this.ctx) return;
    this.master.gain.value = this.volumes.master;
    for (const [k, g] of Object.entries(this.buses)) g.gain.value = (this.volumes as Record<string, number>)[k] ?? 1;
  }

  private decoding = new Map<string, Promise<AudioBuffer | null>>();

  /** Scarica e decodifica un suono (una volta sola, anche se lo chiedono in due insieme). */
  private decode(id: string): Promise<AudioBuffer | null> {
    let p = this.decoding.get(id);
    if (!p) {
      p = this.fetchDecode(id);
      this.decoding.set(id, p);
    }
    return p;
  }

  private async fetchDecode(id: string): Promise<AudioBuffer | null> {
    const info = this.manifest[id];
    if (!info || !this.ctx) return null;
    try {
      const r = await fetch(ASSET_BASE + 'audio/' + info.file);
      const buf = await this.ctx.decodeAudioData(await r.arrayBuffer());
      this.buffers.set(id, buf);
      return buf;
    } catch {
      return null;
    }
  }

  has(id: string): boolean {
    return this.buffers.has(id);
  }

  /** Ingresso di un bus (per i suoni sintetizzati al volo, come le voci). */
  bus(name: 'music' | 'sfx' | 'amb' | 'ui' | 'voice'): AudioNode | null {
    return this.ctx ? this.buses[name]! : null;
  }

  /** Panner HRTF già posizionato (coordinate dei render). */
  panner(pos: Vec3): PannerNode | null {
    if (!this.ctx) return null;
    const p = this.ctx.createPanner();
    p.panningModel = 'HRTF';
    p.distanceModel = 'inverse';
    p.refDistance = 1.2;
    p.rolloffFactor = 0.6;
    setPannerPos(p, pos);
    return p;
  }

  suspend(): void {
    void this.ctx?.suspend();
  }

  resume(): void {
    void this.ctx?.resume();
  }

  /** Orientamento dell'ascoltatore dallo yaw dello sguardo (gradi). */
  setListenerYaw(yawDeg: number): void {
    if (!this.ctx) return;
    const a = (yawDeg * Math.PI) / 180;
    const l = this.ctx.listener;
    const fx = Math.sin(a), fz = -Math.cos(a);
    if (l.forwardX) {
      const t = this.ctx.currentTime;
      l.forwardX.setTargetAtTime(fx, t, 0.02);
      l.forwardY.setTargetAtTime(0, t, 0.02);
      l.forwardZ.setTargetAtTime(fz, t, 0.02);
      l.upX.value = 0;
      l.upY.value = 1;
      l.upZ.value = 0;
    } else {
      (l as unknown as { setOrientation: (...a: number[]) => void }).setOrientation(fx, 0, fz, 0, 1, 0);
    }
  }

  /** Sotto il telone tutto diventa ovattato. */
  setMuffled(amount: number): void {
    if (!this.ctx) return;
    const f = 20000 * Math.pow(600 / 20000, Math.max(0, Math.min(1, amount)));
    this.muffle.frequency.setTargetAtTime(f, this.ctx.currentTime, 0.08);
  }

  play(id: string, o: PlayOpts = {}): Voice | null {
    const ctx = this.ctx;
    const buf = this.buffers.get(id);
    const info = this.manifest[id];
    if (!ctx || !buf || !info) return null;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = o.loop ?? info.loop;
    src.playbackRate.value = o.rate ?? 1;
    const g = ctx.createGain();
    const target = (o.gain ?? 1) * info.gain;
    const now = ctx.currentTime;
    if (o.fadeIn) {
      g.gain.setValueAtTime(0, now);
      g.gain.linearRampToValueAtTime(target, now + o.fadeIn);
    } else g.gain.value = target;
    let node: AudioNode = src;
    let lp: BiquadFilterNode | null = null;
    if (o.lowpass) {
      lp = ctx.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = o.lowpass;
      node.connect(lp);
      node = lp;
    }
    let panner: PannerNode | null = null;
    if (o.pos) {
      panner = ctx.createPanner();
      panner.panningModel = 'HRTF';
      panner.distanceModel = 'inverse';
      panner.refDistance = 1.2;
      panner.rolloffFactor = 0.6;
      setPannerPos(panner, o.pos);
      node.connect(panner);
      node = panner;
    }
    node.connect(g);
    const bus = o.bus ?? (info.category === 'mus' ? 'music' : info.category === 'amb' ? 'amb' : info.category === 'ui' ? 'ui' : info.category === 'voice' ? 'voice' : 'sfx');
    g.connect(this.buses[bus]!);
    src.start();
    let ended = false;
    src.onended = () => {
      ended = true;
      g.disconnect();
    };
    return {
      stop(fade = 0.05) {
        if (ended) return;
        const t = ctx.currentTime;
        g.gain.cancelScheduledValues(t);
        g.gain.setValueAtTime(g.gain.value, t);
        g.gain.linearRampToValueAtTime(0, t + fade);
        src.stop(t + fade + 0.02);
      },
      setGain(v: number, ramp = 0.05) {
        g.gain.setTargetAtTime(v * info.gain, ctx.currentTime, ramp);
      },
      setRate(r: number) {
        src.playbackRate.setTargetAtTime(r, ctx.currentTime, 0.03);
      },
      setPos(p: Vec3) {
        if (panner) setPannerPos(panner, p);
      },
      setLowpass(hz: number, ramp = 0.3) {
        lp?.frequency.setTargetAtTime(hz, ctx.currentTime, ramp);
      },
      get ended() {
        return ended;
      },
    };
  }
}

function setPannerPos(p: PannerNode, v: Vec3): void {
  // render (x destra, y avanti, z alto) → Web Audio (x destra, y alto, z indietro)
  if (p.positionX) {
    p.positionX.value = v[0];
    p.positionY.value = v[2];
    p.positionZ.value = -v[1];
  } else {
    (p as unknown as { setPosition: (x: number, y: number, z: number) => void }).setPosition(v[0], v[2], -v[1]);
  }
}

/** Posizione a distanza 'dist' nella direzione yaw/elevazione (gradi). */
export function dirPos(yawDeg: number, dist = 3, elevDeg = -10): Vec3 {
  const a = (yawDeg * Math.PI) / 180, e = (elevDeg * Math.PI) / 180;
  return [Math.sin(a) * Math.cos(e) * dist, Math.cos(a) * Math.cos(e) * dist, Math.sin(e) * dist];
}
