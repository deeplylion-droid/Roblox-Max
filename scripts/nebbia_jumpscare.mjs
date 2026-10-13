// Il jumpscare nel gioco con le due serie: a notte in corso parte il jumpscare di `chi`, cattura un fotogramma con la
// nebbia spenta e accesa (la serie cambia con l'opzione, anche a notte in corso).
// Uso (con npx vite su localhost:5173): node scripts/nebbia_jumpscare.mjs <cartella> <chi> [<tempo in s>]
import { chromium } from 'playwright-core';

const [out, chi, t = '0.65'] = process.argv.slice(2);
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
const errori = [];
page.on('pageerror', (e) => errori.push(e.message));
await page.goto('http://localhost:5173/?notte=1&step', { waitUntil: 'load' });
await page.waitForFunction(() => window.__game?.app, null, { timeout: 120000 });
await page.evaluate(() => {
  const a = window.__game.app;
  a.nightNo = 1;
  a.startNight();
  window.__game.step(1 / 30, 30);
});
for (const on of [false, true]) {
  await page.evaluate(async ({ on, chi, t }) => {
    const a = window.__game.app;
    a.save.options.fog = on;
    a.applyOptions();
    a.swapFog(on);
    await a.fogSwap;
    const n = a.night;
    n.startJumpscare(chi);
    window.__game.step(1 / 60, Math.round(t * 60));
  }, { on, chi, t: Number(t) });
  await page.screenshot({ path: `${out}/js_${chi}_${on ? 'nebbia' : 'senza'}.png` });
}
console.log('errori', errori.slice(0, 5).join(' | ') || 'nessuno');
await browser.close();
