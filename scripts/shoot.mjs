// Screenshot della scena nel Chromium headless (SwiftShader).
// Uso: node scripts/shoot.mjs <url> <out.png> [waitMs] [w] [h]
import { chromium } from 'playwright-core';

const [url, out, waitMs = '4000', w = '1280', h = '720'] = process.argv.slice(2);
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage({ viewport: { width: Number(w), height: Number(h) } });
const logs = [];
page.on('console', (m) => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
await page.goto(url, { waitUntil: 'load' });
await page.waitForTimeout(Number(waitMs));
await page.screenshot({ path: out });
console.log(logs.slice(-15).join('\n'));
await browser.close();
