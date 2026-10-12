/**
 * Immagini a tutto schermo della notte: la vista da sotto il telone e i fotogrammi dei jumpscare.
 * Vengono dai render (assets/img/overlays.json); finché il render del telone non c'è, una tela
 * procedurale ne fa le veci.
 */
import { ASSET_BASE } from '../engine/assets.ts';
import { textureFromCanvas, textureFromImage, type GL } from '../engine/gl.ts';
import { mul, rotX, rotZ, transpose } from '../engine/view.ts';
import type { MonsterId } from '../game/config.ts';
import type { EndingStill } from './cinematic.ts';
import type { NightAssets, OverlayTex } from './night.ts';

interface PassFile {
  file: string;
  scale: number;
}

/** le immagini senza la nebbia resa, per l'opzione «Nebbia» spenta (le stesse inquadrature, altri file) */
interface Senza extends PassFile {
  /** la nebbia del motore su questa vista (di solito 1: queste immagini non ce l'hanno) */
  fog?: number;
  foxy?: PassFile[];
}

interface PlaceFile extends PassFile {
  key: string;
  yaw: number;
  pitch: number;
  hfov: number;
  aspect: number;
  foxy?: PassFile[];
  fog?: number;
  senza?: Senza;
}

interface OverlayManifest {
  tarp?: { base: PassFile; glow: PassFile; aspect: number; senza?: { base: PassFile; glow: PassFile } };
  /** i jumpscare: dei mostri, della Madre (notte 6) e della quota mancata (l'occhio della Madre, notti 1-5) */
  jumpscares?: Partial<Record<MonsterId | 'mother' | 'quota', { frames: PassFile[]; fps: number; aspect: number }>>;
  /** i posti del binocolo; dove sta il Foxy anche le sue due viste (fermo, più vicino), con la stessa inquadratura */
  binocular?: { places: PlaceFile[]; rec?: [number, number, number] };
  /** le ultime inquadrature dei finali segreti (tools/render/finali.py): l'esposizione in EV da dare al tono */
  endings?: Partial<Record<EndingStill, PassFile & { aspect: number; exposure?: number }>>;
}

type Place = NightAssets['binocular']['places'][number];

/** Un posto del binocolo nella serie scelta. Senza nebbia vale solo se c'è tutta: dove sta il Foxy servono anche le
 *  sue viste senza nebbia, se no il posto cambierebbe aspetto quando arriva lui (e resta quello con la nebbia). */
async function loadPlace(gl: GL, pl: PlaceFile, senza: boolean): Promise<Place> {
  const s = senza && pl.senza && (!pl.foxy?.length || pl.senza.foxy?.length) ? pl.senza : null;
  const t = await tex(gl, s ?? pl);
  // camera del luogo: yaw (a destra) poi pitch (in su), come lo sguardo; la trasposta porta il mondo nella camera
  const R = mul(rotZ(pl.yaw), rotX(pl.pitch));
  const tx = Math.tan((pl.hfov / 2) * (Math.PI / 180));
  const place = { tex: t.tex, scale: t.scale, cam: transpose(R), tan: [tx, tx / pl.aspect] as [number, number], fog: s ? s.fog : pl.fog };
  // le viste col Foxy: servono tutte e due, se no resta il segnaposto (gli occhi rossi)
  let foxy: (typeof place)[] | undefined;
  const fx = s ? s.foxy : pl.foxy;
  if (fx?.length) {
    try {
      foxy = await Promise.all(fx.map(async (f) => ({ ...place, ...(await tex(gl, f)) })));
    } catch (e) {
      console.warn(e);
    }
  }
  return { key: pl.key, yaw: pl.yaw, pitch: pl.pitch, hfov: pl.hfov, place, foxy };
}

async function loadTarp(gl: GL, t: NonNullable<OverlayManifest['tarp']>, senza: boolean): Promise<NonNullable<NightAssets['tarp']>> {
  const s = senza && t.senza ? t.senza : t;
  return { base: await tex(gl, s.base), glow: await tex(gl, s.glow), aspect: t.aspect };
}

/** il manifest degli overlay letto all'avvio (per cambiare serie con l'opzione «Nebbia» senza rileggerlo) */
let overlayMan: OverlayManifest = {};

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

/** Gli overlay della notte; con senza (l'opzione «Nebbia» spenta) il binocolo e il telone senza la nebbia resa. */
export async function loadNightAssets(gl: GL, senza = false): Promise<NightAssets> {
  let man: OverlayManifest = {};
  try {
    const r = await fetch(ASSET_BASE + 'img/overlays.json');
    if (r.ok) man = (await r.json()) as OverlayManifest;
  } catch {
    // niente overlay renderizzati: si usano i segnaposto
  }
  overlayMan = man;
  const out: NightAssets = { tarp: null, jumpscares: {}, fish: {}, binocular: { places: [], rec: null }, endings: {} };
  for (const pl of man.binocular?.places ?? []) {
    try {
      out.binocular.places.push(await loadPlace(gl, pl, senza));
    } catch (e) {
      console.warn(e);
    }
  }
  if (man.binocular?.rec) out.binocular.rec = man.binocular.rec;
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
    if (man.tarp) out.tarp = await loadTarp(gl, man.tarp, senza);
  } catch (e) {
    console.warn(e);
  }
  out.tarp ??= proceduralTarp(gl);
  for (const [k, js] of Object.entries(man.jumpscares ?? {})) {
    if (!js) continue;
    try {
      const frames = await Promise.all(js.frames.map((f) => tex(gl, f)));
      // jumpscare.py scrive la Madre come 'madre' (il nome dei render): nel gioco è 'mother'
      out.jumpscares[(k === 'madre' ? 'mother' : k) as MonsterId | 'mother' | 'quota'] = { frames, fps: js.fps, aspect: js.aspect };
    } catch (e) {
      console.warn(e);
    }
  }
  for (const [k, e] of Object.entries(man.endings ?? {})) {
    if (!e) continue;
    try {
      out.endings[k as EndingStill] = { ...(await tex(gl, e)), aspect: e.aspect, exposure: e.exposure ?? 0 };
    } catch (err) {
      console.warn(err);
    }
  }
  return out;
}

/**
 * L'opzione «Nebbia» cambiata: rimette i posti del binocolo e il telone della serie scelta, al posto di quelli caricati
 * (anche a notte in corso: la notte li legge da qui a ogni fotogramma). Solo dove le due serie sono diverse.
 */
export async function swapFogAssets(gl: GL, assets: NightAssets, senza: boolean): Promise<void> {
  const drop = (t: WebGLTexture | null) => t && gl.deleteTexture(t);
  const places = assets.binocular.places;
  for (const pl of overlayMan.binocular?.places ?? []) {
    if (!pl.senza) continue;
    const i = places.findIndex((p) => p.key === pl.key);
    if (i < 0) continue;
    try {
      const fresh = await loadPlace(gl, pl, senza);
      const old = places[i]!;
      places[i] = fresh;
      drop(old.place.tex);
      for (const f of old.foxy ?? []) drop(f.tex);
    } catch (e) {
      console.warn(e);
    }
  }
  if (overlayMan.tarp?.senza && assets.tarp) {
    try {
      const fresh = await loadTarp(gl, overlayMan.tarp, senza);
      const old = assets.tarp;
      assets.tarp = fresh;
      drop(old.base.tex);
      drop(old.glow.tex);
    } catch (e) {
      console.warn(e);
    }
  }
}
