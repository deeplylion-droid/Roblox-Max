// Registra una sequenza dal motore, fotogramma per fotogramma, nel Chromium headless (pagina con ?step).
// Uso: node scripts/record.mjs <url> <cartella> <secondi> <fps> [JS di preparazione] [JS del via] [secondi prima del via]
// I fotogrammi (solo il canvas, senza l'interfaccia HTML) escono come <cartella>/f0000.jpg…; con ffmpeg si
// montano in un video a <fps>.
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const [url, dir, secs, fpsArg, setup = '', trigger = '', pre = '0'] = process.argv.slice(2);
const fps = Number(fpsArg);
fs.mkdirSync(dir, { recursive: true });
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
const logs = [];
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
await page.goto(url, { waitUntil: 'load' });
await page.waitForFunction('window.__game && window.__game.step', null, { timeout: 180000, polling: 250 });
if (setup) await page.evaluate(setup);
let n = 0;
// i pixel si leggono dal canvas subito dopo il disegno, nello stesso giro (senza aspettare il compositore)
const frame = async () => {
  const url = await page.evaluate(`(window.__game.step(${1 / fps}), document.querySelector('canvas').toDataURL('image/jpeg', 0.92))`);
  fs.writeFileSync(`${dir}/f${String(n++).padStart(4, '0')}.jpg`, Buffer.from(url.split(',')[1], 'base64'));
};
for (let i = 0; i < Math.round(Number(pre) * fps); i++) await frame();
if (trigger) await page.evaluate(trigger);
for (let i = 0; i < Math.round(Number(secs) * fps); i++) await frame();
console.log(`${n} fotogrammi in ${dir}`);
console.log(logs.slice(-15).join('\n'));
await browser.close();
