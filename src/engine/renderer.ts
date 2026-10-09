/**
 * Renderer della scena dalla barca: strati del panorama (mondo, sprite nel mondo, barca, sprite sulla barca),
 * atmosfera (faro, luci), schermo del sonar, lenza, bloom e composizione finale.
 */
import { FULLSCREEN_VS, FullscreenTri, Program, Target, createGL, hdrSupported, textureFromCanvas, type GL } from './gl.ts';
import { ATMOS_FS, BRIGHT_FS, DOWN_FS, FINAL_FS, LAYER_FS, LINE_FS, LINE_VS, OVERLAY_FS, SCREEN_FS, UP_FS } from './shaders.ts';
import type { LoadedLayer, Manifest, Vec3 } from './assets.ts';
import type { View } from './view.ts';

const D2R = Math.PI / 180;

export interface LightGlow {
  dir: Vec3; // direzione dall'occhio (spazio mondo)
  color: Vec3; // già moltiplicato per l'intensità del momento
  radius: number; // radianti
}

/** Uno strato da disegnare, con la sua dissolvenza e l'eventuale spostamento (pixel del panorama). */
export interface LayerDraw {
  key: string;
  opacity?: number;
  shift?: [number, number];
  /** riga del panorama sotto cui lo strato non si vede (il pelo dell'acqua mentre emerge) */
  clipY?: number;
}

/** Immagine a tutto schermo dentro la scena (vista dal telone, jumpscare). */
export interface Overlay {
  base: WebGLTexture;
  baseScale: number;
  glow?: WebGLTexture | null;
  glowScale?: number;
  /** intensità dei due passi */
  wBase: number;
  wGlow?: number;
  /** bagliore mobile sul passo glow: centro (uv, y in su), raggio (uv dell'altezza), fondo */
  blob?: [number, number, number, number];
  /** larghezza/altezza dell'immagine */
  aspect: number;
  alpha: number;
  zoom?: number;
  offset?: [number, number];
  /** rollio della camera (radianti) */
  roll?: number;
  /** specchiata in orizzontale */
  flipX?: boolean;
}

export interface FrameParams {
  time: number;
  /** intensità dei passi di luce */
  ambient: number;
  lamp: number;
  lantern: number;
  exposure: number;
  fade: number;
  flash: number;
  flashColor: Vec3;
  /** nastro VHS rovinato, 0..1 (jumpscare) */
  glitch?: number;
  beamAngle: number;
  /** bagliori lontani (spazio mondo), coperti dalla barca */
  glows: LightGlow[];
  /** bagliori sulla barca (spazio barca), disegnati sopra lo scafo */
  boatGlows?: LightGlow[];
  /** strati da disegnare in ordine (chiavi del manifest, o con dissolvenza/spostamento) */
  layers: (string | LayerDraw)[];
  /** immagine a tutto schermo sopra la scena */
  overlay?: Overlay | null;
  sonar: HTMLCanvasElement | null;
  sonarGain: number;
  line: { points: Vec3[]; alpha: number } | null;
}

export class Renderer {
  readonly gl: GL;
  private tri: FullscreenTri;
  private pLayer: Program;
  private pAtmos: Program;
  private pScreen: Program;
  private pLine: Program;
  private pBright: Program;
  private pDown: Program;
  private pUp: Program;
  private pFinal: Program;
  private pOverlay: Program;
  private hdr!: Target;
  private bloom: Target[] = [];
  private w = 0;
  private h = 0;
  private hdrOk: boolean;
  private sonarTex: WebGLTexture | null = null;
  private lineVao: WebGLVertexArrayObject;
  private lineBuf: WebGLBuffer;
  readonly layers = new Map<string, LoadedLayer>();
  renderScale = 1;

  constructor(
    readonly canvas: HTMLCanvasElement,
    readonly man: Manifest,
  ) {
    const gl = (this.gl = createGL(canvas));
    this.hdrOk = hdrSupported(gl);
    this.tri = new FullscreenTri(gl);
    this.pLayer = new Program(gl, FULLSCREEN_VS, LAYER_FS, 'layer');
    this.pAtmos = new Program(gl, FULLSCREEN_VS, ATMOS_FS, 'atmos');
    this.pScreen = new Program(gl, FULLSCREEN_VS, SCREEN_FS, 'screen');
    this.pLine = new Program(gl, LINE_VS, LINE_FS, 'line');
    this.pBright = new Program(gl, FULLSCREEN_VS, BRIGHT_FS, 'bright');
    this.pDown = new Program(gl, FULLSCREEN_VS, DOWN_FS, 'down');
    this.pUp = new Program(gl, FULLSCREEN_VS, UP_FS, 'up');
    this.pFinal = new Program(gl, FULLSCREEN_VS, FINAL_FS, 'final');
    this.pOverlay = new Program(gl, FULLSCREEN_VS, OVERLAY_FS, 'overlay');
    this.lineVao = gl.createVertexArray()!;
    this.lineBuf = gl.createBuffer()!;
    gl.bindVertexArray(this.lineVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.lineBuf);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 12, 0);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 12, 8);
    gl.bindVertexArray(null);
  }

  addLayer(l: LoadedLayer): void {
    this.layers.set(l.key, l);
  }

  resize(): void {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cw = Math.round(this.canvas.clientWidth * dpr);
    const ch = Math.round(this.canvas.clientHeight * dpr);
    if (cw !== this.canvas.width || ch !== this.canvas.height) {
      this.canvas.width = cw;
      this.canvas.height = ch;
    }
    const w = Math.max(16, Math.round(cw * this.renderScale));
    const h = Math.max(16, Math.round(ch * this.renderScale));
    if (w === this.w && h === this.h) return;
    this.w = w;
    this.h = h;
    this.hdr?.dispose();
    this.bloom.forEach((b) => b.dispose());
    this.hdr = new Target(this.gl, w, h, this.hdrOk);
    this.bloom = [];
    let bw = w >> 1, bh = h >> 1;
    for (let i = 0; i < 6 && bw > 8 && bh > 8; i++) {
      this.bloom.push(new Target(this.gl, bw, bh, this.hdrOk));
      bw >>= 1;
      bh >>= 1;
    }
  }

  get aspect(): number {
    return this.canvas.clientWidth / Math.max(1, this.canvas.clientHeight);
  }

  render(view: View, f: FrameParams): void {
    const gl = this.gl;
    this.resize();
    this.hdr.bind();
    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    const pano = this.man.pano;
    const p = this.pLayer.use();
    p.f2('uTan', view.tanX, view.tanY)
      .f2('uPano', pano.width, pano.height)
      .f2('uLat', pano.latMin * D2R, pano.latMax * D2R)
      .f1('uTime', f.time)
      .f3('uFogColor', 0.006, 0.010, 0.017)
      .f1('uFogDensity', 1 / 3200)
      .f1('uShimmer', 1.0);
    let atmosDone = false;
    for (const item of f.layers) {
      const d: LayerDraw = typeof item === 'string' ? { key: item } : item;
      const key = d.key;
      const l = this.layers.get(key);
      if (!l || (d.opacity ?? 1) <= 0.001) continue;
      // l'atmosfera va disegnata dopo il mondo e prima della barca
      if (!atmosDone && l.info.space === 'boat') {
        this.drawAtmos(view, f);
        this.pLayer.use();
        atmosDone = true;
      }
      const world = l.info.space === 'world';
      const ps = l.info.passes;
      p.m3('uRot', new Float32Array(world ? view.worldRot : view.boatRot))
        .f4('uRect', ...l.info.rect)
        .f1('uYaw', l.info.yaw * D2R)
        .f3('uScale', ps.ambient?.scale ?? 1, ps.lamp?.scale ?? 1, ps.lantern?.scale ?? 1)
        .f3('uW', f.ambient, f.lamp, f.lantern)
        .f3('uHas', l.amb ? 1 : 0, l.lamp ? 1 : 0, l.lantern ? 1 : 0)
        .f1('uAlpha', key === 'world' ? 0 : 1)
        .f1('uOpacity', d.opacity ?? 1)
        .f2('uShift', d.shift?.[0] ?? 0, d.shift?.[1] ?? 0)
        .f1('uClipY', d.clipY ?? 0)
        .f1('uHasData', l.data ? 1 : 0)
        .tex('uAmb', 0, l.amb)
        .tex('uLamp', 1, l.lamp)
        .tex('uLant', 2, l.lantern)
        .tex('uData', 3, l.data);
      this.tri.draw();
    }
    if (!atmosDone) this.drawAtmos(view, f);
    if (f.boatGlows?.length) this.drawGlows(view, f.boatGlows);
    if (f.sonar) this.drawScreen(view, f);
    if (f.line) this.drawLine(view, f.line);
    if (f.overlay && f.overlay.alpha > 0.001) this.drawOverlay(f.overlay);
    gl.disable(gl.BLEND);
    this.drawBloom();
    this.drawFinal(f);
  }

  private drawAtmos(view: View, f: FrameParams): void {
    const gl = this.gl;
    gl.blendFunc(gl.ONE, gl.ONE);
    const a = this.pAtmos.use();
    const lights = this.man.lights ?? {};
    const lh = lights['lighthouse'] ?? [0, 1000, 40];
    const n = Math.min(16, f.glows.length);
    const dirs = new Float32Array(48);
    const cols = new Float32Array(64);
    for (let i = 0; i < n; i++) {
      const g = f.glows[i]!;
      dirs.set(g.dir, i * 3);
      cols.set([g.color[0], g.color[1], g.color[2], g.radius], i * 4);
    }
    a.m3('uRot', new Float32Array(view.worldRot))
      .f2('uTan', view.tanX, view.tanY)
      .f3('uBeamPos', lh[0], lh[1], lh[2])
      .f1('uBeamAngle', f.beamAngle)
      .f3('uBeamColor', 1.0 * f.ambient, 0.86 * f.ambient, 0.62 * f.ambient)
      .i1('uLightCount', n)
      .v3('uLightDir', dirs)
      .v4('uLightCol', cols);
    this.tri.draw();
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  }

  /** Solo bagliori, nello spazio della barca (occhi a bordo, il giocattolo di Hatch). */
  private drawGlows(view: View, glows: LightGlow[]): void {
    const gl = this.gl;
    gl.blendFunc(gl.ONE, gl.ONE);
    const n = Math.min(16, glows.length);
    const dirs = new Float32Array(48);
    const cols = new Float32Array(64);
    for (let i = 0; i < n; i++) {
      const g = glows[i]!;
      dirs.set(g.dir, i * 3);
      cols.set([g.color[0], g.color[1], g.color[2], g.radius], i * 4);
    }
    this.pAtmos
      .use()
      .m3('uRot', new Float32Array(view.boatRot))
      .f2('uTan', view.tanX, view.tanY)
      .f3('uBeamPos', 0, 1000, 40)
      .f1('uBeamAngle', 0)
      .f3('uBeamColor', 0, 0, 0)
      .i1('uLightCount', n)
      .v3('uLightDir', dirs)
      .v4('uLightCol', cols);
    this.tri.draw();
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  }

  private drawScreen(view: View, f: FrameParams): void {
    const gl = this.gl;
    const pts = this.man.points.sonarScreen;
    if (!pts || !f.sonar) return;
    this.sonarTex = textureFromCanvas(gl, f.sonar, this.sonarTex ?? undefined);
    const [tl, tr, br, bl] = pts;
    const c: Vec3 = [(tl[0] + br[0]) / 2, (tl[1] + br[1]) / 2, (tl[2] + br[2]) / 2];
    const right: Vec3 = [(tr[0] - tl[0]) / 2, (tr[1] - tl[1]) / 2, (tr[2] - tl[2]) / 2];
    const up: Vec3 = [(tl[0] - bl[0]) / 2, (tl[1] - bl[1]) / 2, (tl[2] - bl[2]) / 2];
    gl.blendFunc(gl.ONE, gl.ONE);
    this.pScreen
      .use()
      .m3('uRot', new Float32Array(view.boatRot))
      .f2('uTan', view.tanX, view.tanY)
      .f3('uC', ...c)
      .f3('uRight', ...right)
      .f3('uUp', ...up)
      .f1('uRound', this.man.points.sonarRound ? 1 : 0)
      .f1('uGain', f.sonarGain)
      .tex('uTex', 0, this.sonarTex);
    this.tri.draw();
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
  }

  private drawOverlay(o: Overlay): void {
    const gl = this.gl;
    const sa = this.w / this.h;
    // copre lo schermo mantenendo le proporzioni (come object-fit: cover)
    const fit: [number, number] = sa > o.aspect ? [1, o.aspect / sa] : [sa / o.aspect, 1];
    gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    this.pOverlay
      .use()
      .tex('uBase', 0, o.base)
      .tex('uGlow', 1, o.glow ?? o.base)
      .f1('uHasGlow', o.glow ? 1 : 0)
      .f2('uScale', o.baseScale, o.glowScale ?? 1)
      .f2('uW', o.wBase, o.wGlow ?? 0)
      .f4('uBlob', ...(o.blob ?? [0.5, 0.5, 0.2, 0]))
      .f1('uAspect', o.aspect)
      .f2('uFit', fit[0], fit[1])
      .f2('uOffset', o.offset?.[0] ?? 0, o.offset?.[1] ?? 0)
      .f1('uZoom', o.zoom ?? 1)
      .f1('uFlip', o.flipX ? 1 : 0)
      .f1('uRoll', o.roll ?? 0)
      .f1('uAlpha', o.alpha);
    this.tri.draw();
  }

  /** Lenza: polilinea 3D (spazio barca) proiettata e disegnata come nastro sottile. */
  private drawLine(view: View, line: { points: Vec3[]; alpha: number }): void {
    const gl = this.gl;
    const pts2: [number, number][] = [];
    for (const p of line.points) {
      const s = view.project(p);
      if (s) pts2.push([s[0] * 2 - 1, s[1] * 2 - 1]);
    }
    if (pts2.length < 2) return;
    const px = 1.4 / this.w; // mezzo spessore in clip (~1.4 px)
    const py = 1.4 / this.h;
    const data: number[] = [];
    for (let i = 0; i < pts2.length; i++) {
      const a = pts2[Math.max(0, i - 1)]!, b = pts2[Math.min(pts2.length - 1, i + 1)]!;
      let dx = b[0] - a[0], dy = b[1] - a[1];
      const l = Math.hypot(dx * this.w, dy * this.h) || 1;
      dx /= l;
      dy /= l;
      const nx = -dy * this.h * px, ny = dx * this.w * py;
      const fade = line.alpha * (0.35 + 0.65 * (1 - i / (pts2.length - 1)));
      const p = pts2[i]!;
      data.push(p[0] + nx, p[1] + ny, fade, p[0] - nx, p[1] - ny, fade);
    }
    gl.bindVertexArray(this.lineVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.lineBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.DYNAMIC_DRAW);
    this.pLine.use().f3('uColor', 0.55, 0.52, 0.45);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, data.length / 3);
    gl.bindVertexArray(null);
  }

  private drawBloom(): void {
    const gl = this.gl;
    if (this.bloom.length === 0) return;
    // soglia nel primo livello
    const b0 = this.bloom[0]!;
    b0.bind();
    this.pBright.use().f1('uThreshold', 0.9).tex('uSrc', 0, this.hdr.tex);
    this.tri.draw();
    for (let i = 1; i < this.bloom.length; i++) {
      const src = this.bloom[i - 1]!, dst = this.bloom[i]!;
      dst.bind();
      this.pDown.use().f2('uTexel', 1 / src.w, 1 / src.h).tex('uSrc', 0, src.tex);
      this.tri.draw();
    }
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.ONE, gl.ONE);
    for (let i = this.bloom.length - 1; i > 0; i--) {
      const src = this.bloom[i]!, dst = this.bloom[i - 1]!;
      dst.bind();
      this.pUp.use().f2('uTexel', 1 / src.w, 1 / src.h).f1('uWeight', 1.0).tex('uSrc', 0, src.tex);
      this.tri.draw();
    }
    gl.disable(gl.BLEND);
  }

  private drawFinal(f: FrameParams): void {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    this.pFinal
      .use()
      .tex('uHdr', 0, this.hdr.tex)
      .tex('uBloom', 1, this.bloom[0]?.tex ?? this.hdr.tex)
      .f1('uExposure', f.exposure)
      .f1('uBloomAmt', this.bloom.length ? 0.16 : 0)
      .f1('uTime', f.time)
      .f1('uGrain', 0.035)
      .f1('uVignette', 0.55)
      .f1('uAberration', 0.010)
      .f1('uFade', f.fade)
      .f1('uFlash', f.flash)
      .f1('uGlitch', f.glitch ?? 0)
      .f3('uFlashColor', ...f.flashColor)
      .f2('uRes', this.canvas.width, this.canvas.height);
    this.tri.draw();
  }
}
