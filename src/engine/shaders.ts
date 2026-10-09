/**
 * Shader del motore. Convenzione degli assi (come i render di Blender): x destra, y avanti, z alto.
 * Il panorama è equirettangolare: lon = atan(x, y) (0 avanti, + a destra), lat = atan(z, |xy|).
 */

const RAY = /* glsl */ `
uniform mat3 uRot;      // raggio camera → spazio dello strato
uniform vec2 uTan;      // tan(hfov/2), tan(vfov/2)
const float PI = 3.14159265359;
vec3 viewRay(vec2 uv) {
  vec2 ndc = uv * 2.0 - 1.0;
  return normalize(uRot * normalize(vec3(ndc.x * uTan.x, 1.0, ndc.y * uTan.y)));
}
`;

const NOISE = /* glsl */ `
float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
float vnoise(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash12(i), hash12(i + vec2(1, 0)), u.x), mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
  float a = 0.5, s = 0.0;
  for (int i = 0; i < 4; i++) { s += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; }
  return s;
}
`;

/** Uno strato del panorama (mondo, barca o sprite): ricompone i passi di luce e scrive colore premoltiplicato. */
export const LAYER_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
${RAY}
${NOISE}
uniform vec4 uRect;      // x0, y0, x1, y1 (pixel del panorama dello strato)
uniform vec2 uPano;      // larghezza, altezza del panorama
uniform vec2 uLat;       // latMin, latMax (radianti)
uniform float uYaw;      // centro dello strato (radianti)
uniform sampler2D uAmb, uLamp, uLant, uData;
uniform vec3 uScale;     // scale di decodifica dei passi
uniform vec3 uW;         // intensità: ambiente, lampara, lanterna
uniform vec3 uHas;       // 1 se il passo esiste
uniform float uAlpha;    // 1 = lo strato ha l'alpha (sprite / barca)
uniform float uHasData;  // dati del mondo (nebbia, acqua, cielo)
uniform float uTime;
uniform vec3 uFogColor;
uniform float uFogDensity;
uniform float uShimmer;
uniform float uOpacity;  // dissolvenza dello strato (le creature che compaiono e spariscono)
uniform vec2 uShift;     // spostamento dello strato (pixel del panorama): la creatura che emerge
uniform float uClipY;    // > 0: sotto questa riga del panorama non si disegna (il pelo dell'acqua)

vec3 dec(vec4 t, float s) { vec3 c = t.rgb * t.rgb; return c * c * s; }   // gamma 4

void main() {
  vec3 d = viewRay(vUv);
  float lon = atan(d.x, d.y) - uYaw;
  lon = mod(lon + PI, 2.0 * PI) - PI;
  float lat = atan(d.z, length(d.xy));
  vec2 p = vec2((0.5 + lon / (2.0 * PI)) * uPano.x, (uLat.y - lat) / (uLat.y - uLat.x) * uPano.y);
  if (uClipY > 0.0 && p.y > uClipY) discard;
  p -= uShift;
  if (p.x < uRect.x || p.x > uRect.z || p.y < uRect.y || p.y > uRect.w) discard;
  vec2 uv = (p - uRect.xy) / (uRect.zw - uRect.xy);
  float mist = 0.0, sky = 0.0;
  if (uHasData > 0.5) {
    vec4 dd = texture(uData, uv);
    mist = dd.r; sky = dd.b;
    // increspature: le riflessioni sull'acqua tremano, di più vicino alla barca
    float water = dd.g;
    if (water > 0.01) {
      float near = 1.0 - smoothstep(0.0, 0.55, mist);
      vec2 q = vec2(lon * 60.0, lat * 260.0 / max(0.05, abs(lat) * 6.0 + 0.2));
      float n1 = fbm(q * 0.6 + vec2(uTime * 0.25, uTime * 0.5));
      float n2 = fbm(q * 1.7 - vec2(uTime * 0.4, uTime * 0.2));
      vec2 off = vec2(n1 - 0.5, n2 - 0.5) * water * uShimmer * (0.35 + 1.6 * near);
      uv += off / uPano * 2.2;
    }
  }
  vec4 a = texture(uAmb, uv);
  vec3 c = uHas.x * dec(a, uScale.x) * uW.x;
  if (uHas.y > 0.5) c += dec(texture(uLamp, uv), uScale.y) * uW.y;
  if (uHas.z > 0.5) c += dec(texture(uLant, uv), uScale.z) * uW.z;
  float alpha = uAlpha > 0.5 ? a.a : 1.0;
  if (uHasData > 0.5) {
    // nebbia dalla distanza (mist = sqrt(d / 2500 m)); il cielo si schiarisce solo all'orizzonte
    float dist = mist * mist * 2500.0;
    float fog = 1.0 - exp(-dist * uFogDensity);
    float bank = fbm(vec2(lon * 3.0 + uTime * 0.02, lat * 18.0)) ;
    fog *= mix(0.6, 1.2, bank);
    float horizon = exp(-abs(lat) * 22.0);
    fog = mix(fog, horizon * 0.35, sky);
    c = mix(c, uFogColor, clamp(fog, 0.0, 0.92));
  }
  frag = vec4(c * alpha, alpha) * uOpacity;
}`;

/**
 * Binocolo: un luogo dell'orizzonte renderizzato a parte (camera prospettica dall'occhio) disegnato sopra
 * al panorama, con la stessa nebbia del mondo; i bordi sfumano nel panorama. Alfa della texture = nebbia.
 */
export const PERSP_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
${RAY}
uniform sampler2D uTex;
uniform float uScale;
uniform mat3 uCam;       // spazio del mondo → spazio della camera del luogo (x destra, y avanti, z su)
uniform vec2 uCamTan;    // tan dei mezzi campi della camera del luogo
uniform float uW;        // intensità dell'ambiente
uniform float uAmount;   // quanto è alzato il binocolo
uniform vec3 uFogColor;
uniform float uFogDensity;

vec3 dec(vec4 t, float s) { vec3 c = t.rgb * t.rgb; return c * c * s; }

void main() {
  vec3 d = viewRay(vUv);
  vec3 c = uCam * d;
  if (c.y <= 0.0) discard;
  vec2 q = vec2(c.x, c.z) / (c.y * uCamTan);
  float m = max(abs(q.x), abs(q.y));
  if (m >= 1.0) discard;
  vec2 uv = vec2(0.5 + q.x * 0.5, 0.5 - q.y * 0.5);
  vec4 t = texture(uTex, uv);
  vec3 col = dec(t, uScale) * uW;
  float mist = t.a;
  float sky = step(0.995, mist);
  float fog = 1.0 - exp(-mist * mist * 2500.0 * uFogDensity);
  float lat = atan(d.z, length(d.xy));
  fog = mix(fog, exp(-abs(lat) * 22.0) * 0.35, sky);
  col = mix(col, uFogColor, clamp(fog, 0.0, 0.92));
  float a = smoothstep(1.0, 0.82, m) * uAmount;
  frag = vec4(col * a, a);
}`;

/**
 * Immagine a tutto schermo dentro la scena (prima di bloom e grana): la vista da sotto il telone,
 * i fotogrammi dei jumpscare. Passo base + passo "bagliore" modulato da una luce che si muove.
 */
export const OVERLAY_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
uniform sampler2D uBase, uGlow;
uniform float uHasGlow;
uniform vec2 uScale;     // decodifica dei passi (gamma 4)
uniform vec2 uW;         // intensità: base, bagliore
uniform vec4 uBlob;      // centro (uv dell'immagine), raggio, fondo sempre acceso
uniform float uAspect;   // larghezza/altezza dell'immagine
uniform vec2 uFit;       // uv dello schermo → uv dell'immagine (copertura)
uniform vec2 uOffset;
uniform float uZoom;
uniform float uAlpha;
uniform float uFlip;     // 1 = specchiata (Molly dal lato sinistro)
uniform float uRoll;     // rollio della camera (radianti)

vec3 dec(vec4 t, float s) { vec3 c = t.rgb * t.rgb; return c * c * s; }

void main() {
  vec2 p = (vUv - 0.5) * uFit;
  // il rollio gira l'inquadratura attorno al centro (in unità isotrope dell'immagine)
  p.x *= uAspect;
  float cr = cos(uRoll), sr = sin(uRoll);
  p = vec2(cr * p.x - sr * p.y, sr * p.x + cr * p.y);
  p.x /= uAspect;
  vec2 uv = p / uZoom + 0.5 + uOffset;
  if (uFlip > 0.5) uv.x = 1.0 - uv.x;
  uv = clamp(uv, vec2(0.0), vec2(1.0));
  vec2 tuv = vec2(uv.x, 1.0 - uv.y);
  vec3 c = dec(texture(uBase, tuv), uScale.x) * uW.x;
  if (uHasGlow > 0.5) {
    vec2 q = (uv - uBlob.xy) * vec2(uAspect, 1.0) / uBlob.z;
    float k = uBlob.w + exp(-dot(q, q)) + 0.35 * exp(-dot(q, q) * 0.12);
    c += dec(texture(uGlow, tuv), uScale.y) * uW.y * k;
  }
  frag = vec4(c * uAlpha, uAlpha);
}`;

/** Atmosfera nello spazio del mondo: fascio del faro e bagliori delle luci lontane (additivo). */
export const ATMOS_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
${RAY}
uniform vec3 uBeamPos;      // posizione del faro (m, dall'occhio)
uniform float uBeamAngle;   // direzione del fascio (radianti, attorno all'asse verticale)
uniform vec3 uBeamColor;
#define MAXL 16
uniform int uLightCount;
uniform vec3 uLightDir[MAXL];
uniform vec4 uLightCol[MAXL];   // rgb, raggio angolare (radianti)
void main() {
  vec3 d = viewRay(vUv);
  vec3 c = vec3(0.0);
  // fascio del faro: distanza tra il raggio di vista e l'asse del fascio (cono che si allarga)
  vec3 b = vec3(sin(uBeamAngle), cos(uBeamAngle), 0.02);
  b = normalize(b);
  vec3 w0 = uBeamPos;
  float bb = dot(b, b), bd = dot(b, d), dd = dot(d, d);
  float wb = dot(w0, b), wd = dot(w0, d);
  float den = bb * dd - bd * bd;
  if (den > 1e-5) {
    float t = (bd * wd - dd * wb) / den;   // lungo il fascio
    float s = (bb * wd - bd * wb) / den;   // lungo il raggio di vista
    if (t > 0.0 && s > 0.0) {
      vec3 pa = uBeamPos + b * t;
      vec3 pb = d * s;
      float dist = length(pa - pb);
      float r = 2.0 + t * 0.07;
      float beam = exp(-pow(dist / r, 2.0)) * exp(-t / 2600.0);
      c += uBeamColor * beam * 0.06;
    }
  }
  // lampo quando il fascio punta verso di noi
  vec3 toEye = normalize(-uBeamPos);
  float facing = pow(max(dot(b, toEye), 0.0), 60.0);
  float ang = acos(clamp(dot(d, normalize(uBeamPos)), -1.0, 1.0));
  c += uBeamColor * facing * (exp(-pow(ang / 0.012, 2.0)) * 6.0 + exp(-pow(ang / 0.06, 2.0)) * 0.6);
  // bagliori delle luci (lampeggi e sfarfallii decisi in TS)
  for (int i = 0; i < MAXL; i++) {
    if (i >= uLightCount) break;
    float a = acos(clamp(dot(d, uLightDir[i]), -1.0, 1.0));
    float rad = uLightCol[i].a;
    c += uLightCol[i].rgb * (exp(-pow(a / rad, 2.0)) + 0.25 * exp(-a / (rad * 6.0)));
  }
  frag = vec4(c, 0.0);
}`;

/** Schermo del sonar: intersezione col disco/quadro della console (spazio della barca). */
export const SCREEN_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
${RAY}
uniform vec3 uC;       // centro dello schermo (m, dall'occhio)
uniform vec3 uRight;   // semiasse destro
uniform vec3 uUp;      // semiasse alto
uniform float uRound;
uniform sampler2D uTex;
uniform float uGain;
void main() {
  vec3 d = viewRay(vUv);
  vec3 n = normalize(cross(uRight, uUp));
  float den = dot(d, n);
  if (abs(den) < 1e-4) discard;
  float t = dot(uC, n) / den;
  if (t <= 0.0) discard;
  vec3 p = d * t - uC;
  float x = dot(p, uRight) / dot(uRight, uRight);
  float y = dot(p, uUp) / dot(uUp, uUp);
  if (abs(x) > 1.0 || abs(y) > 1.0) discard;
  bool isRound = uRound > 0.5;
  float r = isRound ? length(vec2(x, y)) : max(abs(x), abs(y));
  if (isRound && r > 0.97) discard;
  // schermo rettangolare: il quadrato del sonar sta al centro, ai lati resta il fondo scuro
  float aspect = length(uRight) / length(uUp);
  vec2 q = isRound ? vec2(x, y) : vec2(x * aspect, y);
  vec3 c = vec3(0.0, 0.02, 0.01);
  if (abs(q.x) <= 1.0) c = texture(uTex, vec2(q.x, -q.y) * 0.5 + 0.5).rgb;
  // bombatura del vetro: bordo più scuro
  c *= 1.0 - smoothstep(0.78, 1.0, r) * 0.6;
  frag = vec4(c * uGain, 0.0);
}`;

/** Lenza: striscia di triangoli già in coordinate clip. */
export const LINE_VS = /* glsl */ `#version 300 es
layout(location = 0) in vec2 aPos;
layout(location = 1) in float aAlpha;
out float vA;
void main() { vA = aAlpha; gl_Position = vec4(aPos, 0.0, 1.0); }`;

export const LINE_FS = /* glsl */ `#version 300 es
precision highp float;
in float vA;
out vec4 frag;
uniform vec3 uColor;
void main() { frag = vec4(uColor * vA, vA); }`;

/** Bloom: soglia, sottocampionamento con filtro a 13 campioni, sovracampionamento a tenda. */
export const BRIGHT_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
uniform sampler2D uSrc;
uniform float uThreshold;
void main() {
  vec3 c = texture(uSrc, vUv).rgb;
  float l = max(c.r, max(c.g, c.b));
  float k = smoothstep(uThreshold, uThreshold * 2.5, l);
  frag = vec4(c * k, 1.0);
}`;

export const DOWN_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
uniform sampler2D uSrc;
uniform vec2 uTexel;
void main() {
  vec2 t = uTexel;
  vec3 a = texture(uSrc, vUv + t * vec2(-2, 2)).rgb, b = texture(uSrc, vUv + t * vec2(0, 2)).rgb, c = texture(uSrc, vUv + t * vec2(2, 2)).rgb;
  vec3 d = texture(uSrc, vUv + t * vec2(-2, 0)).rgb, e = texture(uSrc, vUv).rgb, f = texture(uSrc, vUv + t * vec2(2, 0)).rgb;
  vec3 g = texture(uSrc, vUv + t * vec2(-2, -2)).rgb, h = texture(uSrc, vUv + t * vec2(0, -2)).rgb, i = texture(uSrc, vUv + t * vec2(2, -2)).rgb;
  vec3 j = texture(uSrc, vUv + t * vec2(-1, 1)).rgb, k = texture(uSrc, vUv + t * vec2(1, 1)).rgb;
  vec3 l = texture(uSrc, vUv + t * vec2(-1, -1)).rgb, m = texture(uSrc, vUv + t * vec2(1, -1)).rgb;
  vec3 o = e * 0.125 + (a + c + g + i) * 0.03125 + (b + d + f + h) * 0.0625 + (j + k + l + m) * 0.125;
  frag = vec4(o, 1.0);
}`;

export const UP_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
uniform sampler2D uSrc;
uniform vec2 uTexel;
uniform float uWeight;
void main() {
  vec2 t = uTexel;
  vec3 s = texture(uSrc, vUv).rgb * 4.0;
  s += (texture(uSrc, vUv + t * vec2(-1, 0)).rgb + texture(uSrc, vUv + t * vec2(1, 0)).rgb +
        texture(uSrc, vUv + t * vec2(0, -1)).rgb + texture(uSrc, vUv + t * vec2(0, 1)).rgb) * 2.0;
  s += texture(uSrc, vUv + t * vec2(-1, -1)).rgb + texture(uSrc, vUv + t * vec2(1, -1)).rgb +
       texture(uSrc, vUv + t * vec2(-1, 1)).rgb + texture(uSrc, vUv + t * vec2(1, 1)).rgb;
  frag = vec4(s / 16.0 * uWeight, 1.0);
}`;

/** Composizione finale: bloom, esposizione, AgX + "look noir" (come tools/render/post.py), vignetta, grana. */
export const FINAL_FS = /* glsl */ `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 frag;
${NOISE}
uniform sampler2D uHdr, uBloom;
uniform float uExposure, uBloomAmt, uTime, uGrain, uVignette, uAberration, uFade, uFlash;
uniform float uGlitch;   // 0..1: nastro VHS rovinato (jumpscare)
uniform float uBino;     // 0..1: binocolo alzato (i due cerchi)
uniform vec3 uFlashColor;
uniform vec2 uRes;

float luma(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

/** VHS rovinata: di quanto scorre di lato ogni riga (onda del nastro, strappi, cambio testine).
 *  tear = 1 dentro una banda strappata. fr cambia 15 volte al secondo. */
float vhsShift(float y, float fr, float t, out float tear) {
  float s = (sin(y * 31.0 + t * 19.0) * 0.6 + sin(y * 87.0 - t * 43.0) * 0.4) * 0.0012;
  tear = 0.0;
  for (int i = 0; i < 3; i++) {
    float fi = float(i) * 13.0;
    float y0 = hash12(vec2(fr, fi + 1.0));
    float h = 0.006 + 0.045 * hash12(vec2(fr, fi + 2.0));
    float on = step(0.5, hash12(vec2(fr, fi + 3.0))) * step(y0, y) * step(y, y0 + h);
    s += on * (hash12(vec2(fr, fi + 4.0)) - 0.3) * 0.06;
    tear = max(tear, on);
  }
  float hsw = 1.0 - smoothstep(0.0, 0.035, y);
  s += hsw * (0.015 + 0.035 * hash12(vec2(floor(y * 240.0), fr)));
  return s;
}

const mat3 AGX = mat3(0.842479062253094, 0.0423282422610123, 0.0423756549057051,
                      0.0784335999999992, 0.878468636469772, 0.0784336,
                      0.0792237451477643, 0.0791661274605434, 0.879142973793104);
const mat3 AGX_INV = mat3(1.19687900512017, -0.0528968517574562, -0.0529716355144438,
                          -0.0980208811401368, 1.15190312990417, -0.0980434501171241,
                          -0.0990297440797205, -0.0989611768448433, 1.15107367264116);

vec3 agx(vec3 x) {
  x = AGX * max(x, vec3(1e-10));
  x = clamp(log2(x), -12.47393, 4.026069);
  x = (x + 12.47393) / 16.499999;
  vec3 x2 = x * x, x4 = x2 * x2;
  x = 15.5 * x4 * x2 - 40.14 * x4 * x + 31.96 * x4 - 6.868 * x2 * x + 0.4298 * x2 + 0.1191 * x - 0.00232;
  float l = dot(x, vec3(0.2126, 0.7152, 0.0722));
  x = l + (x - l) * 1.12;
  x = 0.5 + (x - 0.5) * 1.16;
  x = clamp(AGX_INV * x, 0.0, 1.0);
  l = dot(x, vec3(0.2126, 0.7152, 0.0722));
  x += vec3(-0.010, 0.022, 0.032) * pow(1.0 - l, 3.0);
  x *= 1.0 + vec3(0.05, 0.0, -0.06) * l * l;
  return clamp(x, 0.0, 1.0);
}

void main() {
  vec2 uv = vUv;
  vec2 cc = uv - 0.5;
  float r2 = dot(cc, cc);
  // aberrazione cromatica ai bordi
  vec2 ab = cc * r2 * uAberration;
  float k = uGlitch;
  float fr = floor(uTime * 15.0);
  float tear = 0.0;
  vec2 suv = uv;
  vec3 hdr;
  if (k > 0.0) {
    // righe che scorrono di lato e un piccolo sobbalzo verticale; fuori dal quadro, nero
    suv = vec2(uv.x + vhsShift(uv.y, fr, uTime, tear) * k, uv.y + (hash12(vec2(fr, 7.7)) - 0.5) * 0.004 * k);
    vec3 sharp = vec3(texture(uHdr, suv + ab).r, texture(uHdr, suv).g, texture(uHdr, suv - ab).b);
    // la crominanza della VHS è sbavata e spostata a destra; la luminanza resta nitida
    vec3 smear = vec3(0.0);
    for (int i = 0; i < 6; i++) smear += texture(uHdr, suv + vec2((float(i) - 1.5) * 0.0024 - 0.002, 0.0) * k).rgb;
    smear /= 6.0;
    vec3 vhs = max(vec3(0.0), luma(sharp) + (smear - luma(smear)) * 1.15);
    hdr = mix(sharp, vhs, min(1.0, k * 1.5)) * step(0.0, suv.x) * step(suv.x, 1.0);
  } else {
    hdr = vec3(texture(uHdr, uv + ab).r, texture(uHdr, uv).g, texture(uHdr, uv - ab).b);
  }
  hdr += texture(uBloom, suv).rgb * uBloomAmt;
  hdr *= exp2(uExposure);
  vec3 col = agx(hdr);
  col *= 1.0 - uVignette * smoothstep(0.08, 0.6, r2);
  float g = hash12(uv * uRes + fract(uTime * 37.0) * 400.0) - 0.5;
  col += g * uGrain * (0.6 + 0.4 * (1.0 - dot(col, vec3(0.333))));
  if (k > 0.0) {
    // nastro consumato: colori smorti, neri lattiginosi, righe, neve, tratti bianchi, rumore in fondo
    col = mix(col, vec3(luma(col)), 0.25 * k);
    col = col * (1.0 - 0.05 * k) + vec3(0.016, 0.018, 0.022) * k;
    col *= 1.0 - 0.09 * k * (0.5 + 0.5 * sin(uv.y * uRes.y * 1.5708));
    float row = floor(uv.y * uRes.y * 0.5);
    float x0 = hash12(vec2(row, fr + 3.0));
    float len = 0.02 + 0.16 * hash12(vec2(row, fr + 5.0));
    float dash = step(0.995, hash12(vec2(row, fr))) * step(x0, uv.x) * step(uv.x, x0 + len) * (1.0 - (uv.x - x0) / len);
    col += dash * 0.55 * k;
    float snow = hash12(uv * uRes + fract(uTime * 61.0) * 911.0) - 0.5;
    col += snow * (0.09 + 0.25 * tear) * k;
    float hsw = 1.0 - smoothstep(0.0, 0.035, uv.y);
    col = mix(col, vec3(hash12(vec2(floor(uv.x * uRes.x * 0.25), row + fr)) * 0.6), hsw * 0.6 * k);
    // banda di disturbo che scorre verso l'alto
    float band = fract(uv.y * 0.6 - uTime * 0.45);
    col += vec3(0.045) * k * smoothstep(0.86, 1.0, band) * (0.5 + 0.5 * hash12(vec2(row, fr + 9.0)));
  }
  if (uBino > 0.0) {
    // i due cerchi del binocolo, con il bordo morbido e un filo di aberrazione
    vec2 bp = (uv - 0.5) * vec2(uRes.x / uRes.y, 1.0);
    float dc = min(length(bp - vec2(-0.21, 0.0)), length(bp + vec2(-0.21, 0.0)));
    float lens = 1.0 - smoothstep(0.405, 0.43, dc);
    col *= mix(1.0, lens * (1.0 - 0.35 * smoothstep(0.25, 0.42, dc)), uBino);
  }
  col = mix(col, uFlashColor, uFlash);
  col *= uFade;
  col += (hash12(uv * uRes * 1.3 + 7.0) - 0.5) / 255.0;   // dithering
  frag = vec4(col, 1.0);
}`;
