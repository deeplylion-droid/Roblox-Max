// Prova automatica del gioco nel Chromium headless: attraversa i menu, avvia la notte e scatta foto.
// Uso: node scripts/play.mjs <url> <cartella> [passi JSON]
// Ogni passo: { "wait": ms } | { "key": "Space" } | { "click": [x, y] } | { "shot": "nome" }
//            | { "eval": "codice JS" } (con window.__game a disposizione) | { "until": "condizione JS" }
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const [url, dir, stepsJson] = process.argv.slice(2);
fs.mkdirSync(dir, { recursive: true });
const steps = stepsJson ? JSON.parse(stepsJson) : [];
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
const logs = [];
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
await page.goto(url, { waitUntil: 'load' });
for (const s of steps) {
  if (s.wait) await page.waitForTimeout(s.wait);
  if (s.key) await page.keyboard.press(s.key);
  if (s.down) await page.keyboard.down(s.down);
  if (s.up) await page.keyboard.up(s.up);
  if (s.click) await page.mouse.click(s.click[0], s.click[1]);
  if (s.move) await page.mouse.move(s.move[0], s.move[1]);
  if (s.text) await page.getByText(s.text, { exact: true }).first().click();
  if (s.until) await page.waitForFunction(s.until, null, { timeout: s.timeout ?? 180000, polling: 250 });
  if (s.eval) logs.push('[eval] ' + JSON.stringify(await page.evaluate(s.eval)));
  if (s.shot) await page.screenshot({ path: `${dir}/${s.shot}.png` });
}
console.log(logs.slice(-30).join('\n'));
await browser.close();
