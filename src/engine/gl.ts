/** Piccoli aiuti WebGL2: programmi, texture, framebuffer HDR, quad a schermo intero. */

export type GL = WebGL2RenderingContext;

export function createGL(canvas: HTMLCanvasElement): GL {
  const gl = canvas.getContext('webgl2', {
    antialias: false,
    alpha: false,
    depth: false,
    stencil: false,
    premultipliedAlpha: false,
    preserveDrawingBuffer: false,
    powerPreference: 'high-performance',
  });
  if (!gl) throw new Error('WebGL2 non disponibile');
  if (!gl.getExtension('EXT_color_buffer_float')) {
    // senza float render target usiamo RGBA8 (meno margine HDR ma funziona)
    console.warn('EXT_color_buffer_float non disponibile: HDR ridotto');
  }
  gl.getExtension('OES_texture_float_linear');
  return gl;
}

export const hdrSupported = (gl: GL) => !!gl.getExtension('EXT_color_buffer_float');

export class Program {
  readonly prog: WebGLProgram;
  private locs = new Map<string, WebGLUniformLocation | null>();

  constructor(
    private gl: GL,
    vs: string,
    fs: string,
    readonly name = 'program',
  ) {
    const p = gl.createProgram()!;
    gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, vs, name));
    gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fs, name));
    gl.bindAttribLocation(p, 0, 'aPos');
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      throw new Error(`link ${name}: ${gl.getProgramInfoLog(p)}`);
    }
    this.prog = p;
  }

  use(): this {
    this.gl.useProgram(this.prog);
    return this;
  }

  loc(name: string): WebGLUniformLocation | null {
    if (!this.locs.has(name)) this.locs.set(name, this.gl.getUniformLocation(this.prog, name));
    return this.locs.get(name)!;
  }

  f1(n: string, v: number): this {
    this.gl.uniform1f(this.loc(n), v);
    return this;
  }
  f2(n: string, a: number, b: number): this {
    this.gl.uniform2f(this.loc(n), a, b);
    return this;
  }
  f3(n: string, a: number, b: number, c: number): this {
    this.gl.uniform3f(this.loc(n), a, b, c);
    return this;
  }
  f4(n: string, a: number, b: number, c: number, d: number): this {
    this.gl.uniform4f(this.loc(n), a, b, c, d);
    return this;
  }
  i1(n: string, v: number): this {
    this.gl.uniform1i(this.loc(n), v);
    return this;
  }
  m3(n: string, m: Float32Array): this {
    this.gl.uniformMatrix3fv(this.loc(n), false, m);
    return this;
  }
  fv(n: string, v: Float32Array): this {
    this.gl.uniform1fv(this.loc(n), v);
    return this;
  }
  v3(n: string, v: Float32Array): this {
    this.gl.uniform3fv(this.loc(n), v);
    return this;
  }
  v4(n: string, v: Float32Array): this {
    this.gl.uniform4fv(this.loc(n), v);
    return this;
  }
  tex(n: string, unit: number, t: WebGLTexture | null): this {
    const gl = this.gl;
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.uniform1i(this.loc(n), unit);
    return this;
  }
}

function compile(gl: GL, type: number, src: string, name: string): WebGLShader {
  const s = gl.createShader(type)!;
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(s);
    const numbered = src
      .split('\n')
      .map((l, i) => `${String(i + 1).padStart(4)} ${l}`)
      .join('\n');
    throw new Error(`compile ${name}: ${log}\n${numbered}`);
  }
  return s;
}

export function textureFromImage(gl: GL, img: TexImageSource, opts: { wrapS?: number; mipmap?: boolean } = {}): WebGLTexture {
  const t = gl.createTexture()!;
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, img);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, opts.wrapS ?? gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  if (opts.mipmap) {
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
  } else {
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  }
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  return t;
}

export function textureFromCanvas(gl: GL, canvas: HTMLCanvasElement | OffscreenCanvas, existing?: WebGLTexture): WebGLTexture {
  const t = existing ?? gl.createTexture()!;
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, canvas as TexImageSource);
  if (!existing) {
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  }
  return t;
}

export class Target {
  fb: WebGLFramebuffer;
  tex: WebGLTexture;
  constructor(
    private gl: GL,
    public w: number,
    public h: number,
    hdr: boolean,
  ) {
    this.tex = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    if (hdr) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, w, h, 0, gl.RGBA, gl.HALF_FLOAT, null);
    else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    this.fb = gl.createFramebuffer()!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.tex, 0);
    const st = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    if (st !== gl.FRAMEBUFFER_COMPLETE) throw new Error('framebuffer incompleto: ' + st);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  bind(): void {
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fb);
    gl.viewport(0, 0, this.w, this.h);
  }

  dispose(): void {
    this.gl.deleteFramebuffer(this.fb);
    this.gl.deleteTexture(this.tex);
  }
}

/** Triangolo che copre lo schermo (attributo 0). */
export class FullscreenTri {
  private vao: WebGLVertexArrayObject;
  constructor(private gl: GL) {
    this.vao = gl.createVertexArray()!;
    gl.bindVertexArray(this.vao);
    const buf = gl.createBuffer()!;
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
  }
  draw(): void {
    this.gl.bindVertexArray(this.vao);
    this.gl.drawArrays(this.gl.TRIANGLES, 0, 3);
  }
}

export const FULLSCREEN_VS = `#version 300 es
layout(location = 0) in vec2 aPos;
out vec2 vUv;
void main() {
  vUv = aPos * 0.5 + 0.5;
  gl_Position = vec4(aPos, 0.0, 1.0);
}`;
