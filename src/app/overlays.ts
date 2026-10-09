/**
 * Immagini a tutto schermo della notte: la vista da sotto il telone e i fotogrammi dei jumpscare.
 * Vengono dai render (assets/img/overlays.json); finché il render del telone non c'è, una tela
 * procedurale ne fa le veci.
 */
import { ASSET_BASE } from '../engine/assets.ts';
import { textureFromCanvas, textureFromImage, type GL } from '../engine/gl.ts';
import type { MonsterId } from '../game/config.ts';
import type { NightAssets, OverlayTex } from './night.ts';

interface PassFile {
  file: string;
  scale: number;
}

interface OverlayManifest {
  tarp?: { base: PassFile; glow: PassFile; aspect: number };
  jumpscares?: Partial<Record<MonsterId, { frames: PassFile[]; fps: number; aspect: number }>>;
}

async function tex(gl: GL, p: PassFile): Promise<OverlayTex> {
  const r = await fetch(ASSET_BASE + 'img/' + p.file);
  if (!r.ok) throw new Error(`asset mancante: ${p.file}`);
  const bmp = await createImageBitmap(await r.blob(), { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
  const t = textureFromImage(gl, bmp, { wrapS: gl.CLAMP_TO_EDGE });
  bmp.close();
  return { tex: t, scale: p.scale };
}

/** Tela del telone vista da sotto, generata al volo (segnaposto del render). */
function proceduralTarp(gl: GL): NightAssets['tarp'] {
  const W = 640, H = 360;
  const base = document.createElement('canvas');
  const glow = document.createElement('canvas');
  base.width = glow.width = W;
  base.height = glow.height = H;
  const cb = base.getContext('2d')!, cg = glow.getContext('2d')!;
  const ib = cb.createImageData(W, H), ig = cg.createImageData(W, H);
  const hash = (x: number, y: number) => {
    const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
    return s - Math.floor(s);
  };
  // codifica come i render: valore lineare → radice quarta
  const enc = (v: number) => Math.round(Math.min(1, Math.pow(Math.max(0, v), 0.25)) * 255);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const u = x / W, v = y / H;
      // pieghe della tela che pende sopra la testa, più fitte ai lati
      const fold = 0.5 + 0.5 * Math.sin(u * 23 + Math.sin(v * 5 + u * 3) * 1.8) * Math.cos(v * 7 - u * 4);
      const weave = 0.85 + 0.15 * ((x + y) % 3 === 0 ? 1 : 0) + 0.1 * (hash(x, y) - 0.5);
      const edge = Math.min(1, Math.min(u, 1 - u) * 6) * Math.min(1, (1 - v) * 3 + 0.2);
      // in basso uno spiraglio sul pagliolo: lì la tela finisce
      const gap = v > 0.88 ? (v - 0.88) / 0.12 : 0;
      const shade = (0.35 + 0.65 * fold) * weave * edge * (1 - gap);
      const i = (y * W + x) * 4;
      // passo base: tela scura, appena scaldata dalla lampara attraverso la trama
      ib.data[i] = enc(0.012 * shade + 0.002 * gap);
      ib.data[i + 1] = enc(0.010 * shade + 0.002 * gap);
      ib.data[i + 2] = enc(0.006 * shade + 0.003 * gap);
      ib.data[i + 3] = 255;
      // passo retroilluminato: la luce verdeazzurra del giocattolo passa dove la tela è più sottile
      const thin = (0.55 + 0.45 * (1 - fold)) * weave * (1 - gap * 0.8);
      ig.data[i] = enc(0.05 * thin);
      ig.data[i + 1] = enc(0.17 * thin);
      ig.data[i + 2] = enc(0.14 * thin);
      ig.data[i + 3] = 255;
    }
  }
  cb.putImageData(ib, 0, 0);
  cg.putImageData(ig, 0, 0);
  return {
    base: { tex: textureFromCanvas(gl, base), scale: 1 },
    glow: { tex: textureFromCanvas(gl, glow), scale: 1 },
    aspect: W / H,
  };
}

export async function loadNightAssets(gl: GL): Promise<NightAssets> {
  let man: OverlayManifest = {};
  try {
    const r = await fetch(ASSET_BASE + 'img/overlays.json');
    if (r.ok) man = (await r.json()) as OverlayManifest;
  } catch {
    // niente overlay renderizzati: si usano i segnaposto
  }
  const out: NightAssets = { tarp: null, jumpscares: {}, fish: {} };
  try {
    const r = await fetch(ASSET_BASE + 'img/fish/fish.json');
    if (r.ok) {
      const fm = (await r.json()) as Record<string, { file: string }>;
      for (const [id, e] of Object.entries(fm)) out.fish[id] = ASSET_BASE + 'img/fish/' + e.file;
    }
  } catch {
    // nessun pesce renderizzato: le schede restano senza figura
  }
  try {
    if (man.tarp) out.tarp = { base: await tex(gl, man.tarp.base), glow: await tex(gl, man.tarp.glow), aspect: man.tarp.aspect };
  } catch (e) {
    console.warn(e);
  }
  out.tarp ??= proceduralTarp(gl);
  for (const [k, js] of Object.entries(man.jumpscares ?? {})) {
    if (!js) continue;
    try {
      const frames = await Promise.all(js.frames.map((f) => tex(gl, f)));
      out.jumpscares[k as MonsterId] = { frames, fps: js.fps, aspect: js.aspect };
    } catch (e) {
      console.warn(e);
    }
  }
  return out;
}
