// Registra le voci sintetizzate al volo dal gioco (conta di Hatch, radio della prima notte) in file WAV,
// per riascoltarle fuori dal gioco. Serve il server di Vite attivo (npm run dev, porta 5173).
// Uso: node scripts/voci.mjs <cartella d'uscita>
import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';

const out = process.argv[2] ?? 'voci';
fs.mkdirSync(out, { recursive: true });
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage();
await page.goto('http://localhost:5173/', { waitUntil: 'domcontentloaded' });

const clips = await page.evaluate(async () => {
  const { speak, CHILD, RADIO_VOICE } = await import('/src/engine/voice.ts');
  const { STRINGS, RADIO_NIGHT1 } = await import('/src/i18n.ts');
  const SR = 48000;
  // una frase in un contesto offline: la stessa catena del gioco, senza posizione nello spazio
  async function render(text, profile, maxDuration) {
    const len = Math.ceil((maxDuration + 1.2) * SR);
    const ctx = new OfflineAudioContext(2, len, SR);
    const bus = ctx.createGain();
    bus.connect(ctx.destination);
    const audio = { ctx, bus: () => bus, panner: () => null };
    const u = speak(audio, text, profile, { maxDuration });
    if (!u) return null;
    const buf = await ctx.startRendering();
    const toB64 = (f) => {
      const b = new Uint8Array(f.buffer);
      let s = '';
      for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
      return btoa(s);
    };
    return { l: toB64(buf.getChannelData(0)), r: toB64(buf.getChannelData(1)), sr: SR };
  }
  const res = {};
  for (const lang of ['it', 'en']) {
    const S = STRINGS[lang];
    const words = S.hatchCount;
    const count = [];
    for (let n = 1; n <= words.length; n++) {
      const last = n === words.length;
      const text = last ? `${words[words.length - 1]} ${S.hatchReady}` : words[n - 1];
      count.push({ at: 0.4 + (n - 1) * 1.1, ...(await render(text, { ...CHILD, pitch: 250, gain: 0.55 }, last ? 2.6 : 0.9)) });
    }
    res[`conta_${lang}`] = count;
    const lines = RADIO_NIGHT1[lang];
    const radio = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line.text) {
        radio.push({ at: line.at, end: true });
        continue;
      }
      const after = lines[i + 1];
      radio.push({ at: line.at, ...(await render(line.text, RADIO_VOICE, after ? after.at - line.at : 2)) });
    }
    res[`radio_${lang}`] = radio;
  }
  return res;
});
fs.writeFileSync(path.join(out, 'voci.json'), JSON.stringify(clips));
await browser.close();
console.log('ok', Object.keys(clips).join(' '));
