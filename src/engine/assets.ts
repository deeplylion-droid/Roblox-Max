/** Manifest dei render (public/assets/img/manifest.json) e caricamento delle texture. */
import { textureFromImage, type GL } from './gl.ts';

export type Vec3 = [number, number, number];

export interface PassInfo {
  file: string;
  scale: number;
  res?: number;
}

export interface LayerInfo {
  space: 'world' | 'boat';
  yaw: number; // gradi: centro del panorama ruotato dello strato
  rect: [number, number, number, number];
  passes: Partial<Record<'ambient' | 'lamp' | 'lantern', PassInfo>>;
  data?: string;
  tip?: Vec3;
  /** occhi delle creature (dall'occhio del pescatore): a lampara spenta brillano appena */
  eyes?: Vec3[];
  /** batteria: il quadrante del voltmetro (centro, semiasse destro, semiasse alto, dall'occhio) */
  gauge?: [Vec3, Vec3, Vec3];
  /** «toppa» di un'animazione (la sola testa con una variante): lo strato della posa su cui va, con lo stesso yaw */
  base?: string;
}

export interface Manifest {
  pano: { width: number; height: number; latMin: number; latMax: number };
  layers: Record<string, LayerInfo>;
  points: {
    eye: Vec3;
    lamp: Vec3;
    rodTip: Vec3;
    bucket: Vec3;
    tarp: Vec3;
    sonarScreen: [Vec3, Vec3, Vec3, Vec3];
    sonarRound?: boolean;
    lighthouseYaw: number;
    moonYaw: number;
    moonElev: number;
    /** il bordo della barca visto dall'occhio: altezza in gradi per yaw da −180° (passo 360°/lunghezza) */
    sheer?: number[];
  };
  lights?: Record<string, Vec3>;
}

export interface LoadedLayer {
  key: string;
  info: LayerInfo;
  amb: WebGLTexture | null;
  lamp: WebGLTexture | null;
  lantern: WebGLTexture | null;
  data: WebGLTexture | null;
}

export const ASSET_BASE = 'assets/';

export async function loadManifest(): Promise<Manifest> {
  const r = await fetch(ASSET_BASE + 'img/manifest.json');
  if (!r.ok) throw new Error('manifest dei render non trovato');
  return (await r.json()) as Manifest;
}

async function bitmap(url: string): Promise<ImageBitmap> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`asset mancante: ${url}`);
  const blob = await r.blob();
  return createImageBitmap(blob, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
}

export async function loadLayer(gl: GL, man: Manifest, key: string): Promise<LoadedLayer> {
  const info = man.layers[key];
  if (!info) throw new Error(`strato ${key} non presente nel manifest`);
  const fullPano = info.rect[0] === 0 && info.rect[2] === man.pano.width;
  const wrap = fullPano ? gl.REPEAT : gl.CLAMP_TO_EDGE;
  const load = async (p?: PassInfo) => {
    if (!p) return null;
    const bmp = await bitmap(ASSET_BASE + 'img/' + p.file);
    const t = textureFromImage(gl, bmp, { wrapS: wrap });
    bmp.close();
    return t;
  };
  const [amb, lamp, lantern, data] = await Promise.all([
    load(info.passes.ambient),
    load(info.passes.lamp),
    load(info.passes.lantern),
    info.data ? load({ file: info.data, scale: 1 }) : Promise.resolve(null),
  ]);
  return { key, info, amb, lamp, lantern, data };
}
