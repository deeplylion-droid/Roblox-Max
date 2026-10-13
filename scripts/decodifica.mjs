// Controlla che Chromium decodifichi tutte le immagini di manifest.json e overlays.json (strati, serie senza,
// jumpscare). Dopo un'installazione va riavviato npx vite: un file tolto e rimesso col suo nome (la serie senza) può
// restare fuori dai file pubblici di Vite, che risponde con la pagina HTML (13 ottobre, archie_trombetta_tutta).
// Uso (con npx vite su localhost:5173): node scripts/decodifica.mjs
import { chromium } from 'playwright-core';

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const p = await b.newPage();
await p.goto('http://localhost:5173/assets/img/manifest.json');
const r = await p.evaluate(async () => {
  const m = await (await fetch('manifest.json')).json();
  const o = await (await fetch('overlays.json')).json();
  const files = new Set();
  for (const e of Object.values(m.layers)) {
    for (const s of [e.passes, e.senza?.passes]) if (s) for (const q of Object.values(s)) files.add(q.file);
    if (e.data) files.add(e.data);
    if (e.senza?.data) files.add(e.senza.data);
  }
  for (const js of Object.values(o.jumpscares ?? {})) for (const f of [...js.frames, ...(js.senza?.frames ?? [])]) files.add(f.file);
  const bad = [];
  for (const f of files) {
    try {
      const bm = await createImageBitmap(await (await fetch(f)).blob(), { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
      bm.close();
    } catch (e) {
      bad.push(`${f}: ${e.message}`);
    }
  }
  return { n: files.size, bad };
});
console.log(`${r.n} immagini, ${r.bad.length} non si decodificano`);
for (const x of r.bad) console.log('  ' + x);
await b.close();
process.exit(r.bad.length ? 1 : 0);
