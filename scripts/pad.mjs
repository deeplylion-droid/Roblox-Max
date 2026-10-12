// Prova del controller nel Chromium headless, alla misura dello Steam Deck (1280×800): un controller finto al posto di
// navigator.getGamepads, il tempo che avanza solo con __game.step (?step). Senza mai toccare mouse o tastiera:
// avvertenza, titolo, opzioni (anche un cursore), extra, diario, catalogo, la notte (sguardo, luce, lancio, telone,
// sonar, binocolo, pausa), la vibrazione, i risultati, la notte extra, l'immersione. Scatta le foto a testo normale e
// grande e controlla che niente esca dallo schermo.
// Uso: node scripts/pad.mjs [url] [cartella]   (url di partenza: http://localhost:5173/, con `npm run dev`)
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const base = process.argv[2] ?? 'http://localhost:5173/';
const dir = process.argv[3] ?? 'shots/pad';
fs.mkdirSync(dir, { recursive: true });
const W = 1280, H = 800;
const browser = await chromium.launch({
  executablePath: process.env.CHROME ?? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});

const failures = [];
const check = (ok, what) => {
  console.log(`${ok ? 'ok  ' : 'NO  '} ${what}`);
  if (!ok) failures.push(what);
};

/** Il controller finto: i tasti della mappatura standard, gli assi, le vibrazioni chieste. */
const PAD_INIT = `
  window.__pad = { buttons: Array.from({ length: 17 }, () => ({ pressed: false, value: 0, touched: false })), axes: [0, 0, 0, 0], rumbles: [] };
  const gp = () => ({
    id: window.__padId || 'Xbox 360 Controller (XInput STANDARD GAMEPAD)', index: 0, connected: true, mapping: 'standard', timestamp: performance.now(),
    buttons: window.__pad.buttons.map((b) => ({ ...b })), axes: [...window.__pad.axes],
    vibrationActuator: { type: 'dual-rumble', playEffect: (t, p) => { window.__pad.rumbles.push({ t, ...p }); return Promise.resolve('complete'); } },
  });
  Object.defineProperty(Navigator.prototype, 'getGamepads', { value: () => [gp(), null, null, null], configurable: true });
`;
const IDX = { A: 0, B: 1, X: 2, Y: 3, LB: 4, RB: 5, LT: 6, RT: 7, Back: 8, Start: 9, L3: 10, R3: 11, Up: 12, Down: 13, Left: 14, Right: 15 };

async function session(query, textSize) {
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  const logs = [];
  page.on('pageerror', (e) => logs.push(`[pageerror] ${e.message}`));
  page.on('console', (m) => m.type() === 'error' && logs.push(`[error] ${m.text()}`));
  await page.addInitScript(PAD_INIT);
  // la dimensione dei testi dalle opzioni salvate (e la qualità bassa: senza GPU si disegna piano)
  await page.addInitScript((ts) => {
    try {
      const k = 'splashland.save.v1';
      const s = JSON.parse(localStorage.getItem(k) || 'null');
      if (!s) localStorage.setItem(k, JSON.stringify({ version: 1, lang: 'it', night: 7, options: { textSize: ts, quality: 0.5 } }));
    } catch {}
  }, textSize);
  await page.goto(base + query, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__game?.step, null, { timeout: 180000 });
  const step = (n = 1, dt = 1 / 60) => page.evaluate(([n, dt]) => window.__game.step(dt, n), [n, dt]);
  const set = (b, on) => page.evaluate(([i, on]) => { window.__pad.buttons[i] = { pressed: on, value: on ? 1 : 0, touched: on }; }, [IDX[b], on]);
  const press = async (b, hold = 1) => {
    await set(b, true);
    await step(hold);
    await set(b, false);
    await step(1);
  };
  const axes = (a) => page.evaluate((a) => { window.__pad.axes = a; }, a);
  const focused = () => page.evaluate(() => document.activeElement?.textContent?.trim() ?? '');
  const mode = () => page.evaluate(() => window.__game.app.mode);
  // (senza GPU i fotogrammi si disegnano davvero solo allo scatto: può volerci molto)
  const shot = (name) => page.screenshot({ path: `${dir}/${name}.png`, timeout: 600000 });
  /** niente esce dallo schermo (testi e pulsanti delle schermate) */
  const fits = (what) =>
    page.evaluate(([W, H]) => {
      const out = [];
      for (const e of document.querySelectorAll('#ui .screen *, #ui .hud-hint, #ui .pad-legend')) {
        const r = e.getBoundingClientRect();
        if (!r.width || !r.height || getComputedStyle(e).visibility === 'hidden') continue;
        // le liste che scorrono (il diario) possono andare oltre: conta il loro riquadro
        if (e.closest('.journal') && !e.classList.contains('journal')) continue;
        if (r.left < -1 || r.top < -1 || r.right > W + 1 || r.bottom > H + 1) out.push(`${e.tagName}.${e.className} ${Math.round(r.left)},${Math.round(r.top)}–${Math.round(r.right)},${Math.round(r.bottom)}`);
      }
      return out.slice(0, 5);
    }, [W, H]).then((out) => check(out.length === 0, `${what}: tutto dentro lo schermo ${out.join(' | ')}`));
  return { page, logs, step, press, set, axes, focused, mode, shot, fits };
}

for (const ts of [1, 1.4]) {
  const tag = ts === 1 ? 'normale' : 'grande';
  console.log(`\n— testo ${tag} —`);
  const s = await session('?step&notte=1', ts);
  const { page, step, press, set, axes, focused, mode, shot, fits } = s;
  await step(5);
  await shot(`${tag}-01-avvertenza`);
  await press('A');
  await step(3);
  check((await mode()) === 'title', 'A sull’avvertenza: il titolo');
  check(await page.evaluate(() => document.documentElement.classList.contains('pad')), 'il controller è il dispositivo in uso (html.pad)');
  check((await focused()).startsWith('Nuova partita'), `selezionato «Nuova partita» (${await focused()})`);
  await press('Down');
  check(!(await focused()).startsWith('Nuova partita'), `giù sposta la selezione (${await focused()})`);
  await step(10, 0.1);
  await shot(`${tag}-02-titolo`);
  await fits('titolo');

  // opzioni: il cursore del volume con destra e sinistra
  for (let i = 0; i < 8 && !(await focused()).startsWith('Opzioni'); i++) await press('Down');
  await press('A');
  await step(2);
  check(!!(await page.$('.screen.opts')), 'A su «Opzioni»: le opzioni');
  const vol0 = await page.evaluate(() => window.__game.app.save.options.master);
  await press('Right');
  await press('Right');
  const vol1 = await page.evaluate(() => window.__game.app.save.options.master);
  check(vol1 > vol0 || vol0 >= 1, `destra sul cursore alza il volume (${vol0} → ${vol1})`);
  await press('Left');
  await press('Left');
  check((await page.evaluate(() => window.__game.app.save.options.master)) === vol0, 'sinistra lo riabbassa');
  await press('Down');
  await step(5, 0.1);
  await shot(`${tag}-03-opzioni`);
  await fits('opzioni');
  // «Riduci lampi e scosse» spegne le vibrazioni
  for (let i = 0; i < 12 && !(await page.evaluate(() => document.activeElement?.closest('label')?.textContent?.includes('Riduci lampi'))); i++) await press('Down');
  await press('A');
  check((await page.evaluate(() => window.__game.app.save.options.reduceFlash)) === true, 'A su «Riduci lampi e scosse»: acceso');
  await press('A');
  check((await page.evaluate(() => window.__game.app.save.options.reduceFlash)) === false, 'di nuovo A: spento');
  await press('B');
  await step(2);
  check(!!(await page.$('.screen.title h1')), 'B dalle opzioni: di nuovo il titolo');

  // extra: il diario e il catalogo a libro
  for (let i = 0; i < 8 && !(await focused()).startsWith('Extra'); i++) await press('Down');
  await press('A');
  await press('A');
  await step(5, 0.1);
  check(!!(await page.$('.journal-screen')), 'il diario');
  await shot(`${tag}-04-diario`);
  await fits('diario');
  await press('B');
  await press('Down');
  await press('A');
  await step(10, 0.1);
  check(!!(await page.$('.book-screen')), 'il catalogo a libro');
  await press('RB');
  // (la pagina gira col tempo vero: una transizione CSS)
  await page.waitForTimeout(1300);
  check((await page.evaluate(() => document.querySelector('.book-tabs .tab.on')?.dataset.k)) === '1', 'RB gira la pagina');
  await shot(`${tag}-05-catalogo`);
  await fits('catalogo');
  await press('LB');
  // (la pagina gira col tempo vero: una transizione CSS)
  await page.waitForTimeout(1300);
  check((await page.evaluate(() => document.querySelector('.book-tabs .tab.on')?.dataset.k)) === '0', 'LB la rigira indietro');
  await press('B');
  await step(2);
  await press('B');
  await step(2);
  check(!!(await page.$('.screen.title h1')), 'B, B: di nuovo il titolo');

  // la notte extra (sbloccata nel salvataggio di prova): i livelli col controller
  for (let i = 0; i < 8 && !(await focused()).startsWith('Notte extra'); i++) await press('Down');
  await press('A');
  await step(5, 0.1);
  check(!!(await page.$('.extra-screen')), 'la schermata dei livelli della notte extra');
  const lv0 = await page.evaluate(() => window.__game.app.save.extra.gulpy);
  // dal primo pulsante (il − di Gulpy) a destra c'è il +
  await press('Right');
  await press('A');
  const lv1 = await page.evaluate(() => window.__game.app.save.extra.gulpy);
  check(lv1 === lv0 + 1, `+ di Gulpy col controller (${lv0} → ${lv1})`);
  await press('Left');
  await press('A');
  check((await page.evaluate(() => window.__game.app.save.extra.gulpy)) === lv0, '− di Gulpy');
  await shot(`${tag}-06-notte-extra`);
  await fits('notte extra');
  await press('B');
  await step(2);

  // la notte: Nuova partita
  for (let i = 0; i < 8 && !(await focused()).startsWith('Nuova partita'); i++) await press('Up');
  await press('A');
  check((await mode()) === 'intro', 'A su «Nuova partita»: l’intro');
  await step(40, 0.1);
  check((await mode()) === 'night', 'la notte comincia');
  await step(5, 0.1);
  const sim = (expr) => page.evaluate(`(() => { const n = window.__game.app.night; const sim = n.sim; return ${expr}; })()`);
  // lo sguardo con lo stick destro
  const yaw0 = await sim('window.__game.stage.view.targetYaw');
  await axes([0, 0, 1, 0]);
  await step(5, 0.1);
  await axes([0, 0, 0, 0]);
  const yaw1 = await sim('window.__game.stage.view.targetYaw');
  check(yaw1 - yaw0 > 20, `stick destro: lo sguardo gira (${yaw0.toFixed(1)} → ${yaw1.toFixed(1)})`);
  await step(10);
  await shot(`${tag}-07-notte-hud`);
  // la croce: voltarsi verso la canna e il suggerimento coi tasti del controller
  await press('Right');
  await step(10, 0.1);
  const hint = await page.evaluate(() => document.querySelector('.hud-hint.show')?.textContent ?? '');
  console.log(`     suggerimento: «${hint}»`);
  check(!/Spazio|Clic|clic|Tab\b/.test(hint), 'il suggerimento non parla di tastiera o mouse');
  // la luce
  const l0 = await sim('sim.lamp');
  await press('LB');
  check((await sim('sim.lamp')) === Math.max(0, l0 - 1), 'LB abbassa la luce');
  await press('RB');
  check((await sim('sim.lamp')) === l0, 'RB la rialza');
  // il lancio col grilletto destro
  await press('RT', 2);
  check((await sim('sim.fishing.phase')) !== 'idle', `RT lancia (${await sim('sim.fishing.phase')})`);
  // l'abboccata vibra poco, il jumpscare forte
  await page.evaluate(() => window.__game.app.night.handle({ t: 'bite' }));
  const r1 = await page.evaluate(() => window.__pad.rumbles.at(-1));
  check(!!r1 && r1.duration < 300, `l’abboccata vibra, breve (${JSON.stringify(r1)})`);
  // il sonar e il telone
  await press('Y');
  check(await sim('n.sonarOpen'), 'Y apre il sonar');
  const close = await page.evaluate(() => document.querySelector('.sonar-close')?.textContent);
  check(/Y|B/.test(close) && !/Tab/.test(close), `sotto il sonar i tasti del controller («${close}»)`);
  await step(3, 0.1);
  await shot(`${tag}-08-sonar`);
  await press('B');
  check(!(await sim('n.sonarOpen')), 'B chiude il sonar');
  await press('A');
  await step(15, 0.1);
  check((await sim('sim.hide')) !== 'out', `A: sotto il telone (${await sim('sim.hide')})`);
  await press('A');
  await step(15, 0.1);
  check((await sim('sim.hide')) !== 'in', `A di nuovo: fuori (${await sim('sim.hide')})`);
  // il binocolo (LT tenuto), lo zoom con RB, giù quando lo lasci
  await press('Left');
  await step(10, 0.1);
  await set('LT', true);
  await step(7, 0.1);
  check((await sim('n.bino')) > 0.5, `LT tenuto: il binocolo (${(await sim('n.bino')).toFixed(2)})`);
  await set('RB', true);
  await step(1);
  await set('RB', false);
  await step(5, 0.1);
  check((await sim('n.binoFov')) === 4.5, 'RB col binocolo: lo zoom');
  await shot(`${tag}-09-binocolo`);
  await set('LT', false);
  await step(7, 0.1);
  check((await sim('n.bino')) < 0.5, 'LT lasciato: il binocolo giù');
  // la pausa: Start, poi B riprende; Start, Start riprende
  await press('Start');
  check((await mode()) === 'paused', 'Start: la pausa');
  await step(5, 0.1);
  await shot(`${tag}-10-pausa`);
  await fits('pausa');
  await press('B');
  check((await mode()) === 'night', 'B riprende');
  await press('Start');
  await press('Start');
  check((await mode()) === 'night', 'Start, Start: riprende');
  // un jumpscare: la vibrazione forte
  await page.evaluate(() => window.__game.app.night.startJumpscare('molly'));
  const r2 = await page.evaluate(() => window.__pad.rumbles.at(-1));
  check(!!r2 && r2.strongMagnitude === 1, `il jumpscare vibra forte (${JSON.stringify(r2)})`);
  // i risultati della morte, poi Riprova col controller
  await page.evaluate(() => window.__game.app.endNight({ kind: 'dead', killer: 'molly', stats: { caught: 2, fed: 1, lore: [], time: 300, bucket: 0 }, js: false }));
  await step(5, 0.1);
  check(!!(await page.$('.screen.death')), 'la morte: i risultati');
  await shot(`${tag}-11-morte`);
  await fits('morte');
  check((await focused()).startsWith('Riprova'), `selezionato «Riprova» (${await focused()})`);
  await page.evaluate(() => window.__game.app.endNight({ kind: 'won', stats: { caught: 9, fed: 1, lore: [], time: 600, bucket: 8 } }));
  await step(5, 0.1);
  await shot(`${tag}-12-alba`);
  await fits('alba');
  // l'immersione: lo sguardo, il mirino, Y per risalire
  const hasDive = await page.evaluate(() => !!document.querySelector('.screen.dawn button'));
  if (hasDive && (await focused()).startsWith('Scendi')) {
    await press('A');
    await page.waitForFunction(() => window.__game.app.diving && window.__game.app.diving.phase !== 'loading', null, { timeout: 120000 }).catch(() => {});
    await step(15, 0.1);
    check((await mode()) === 'dive', 'A su «Scendi con le bombole»: l’immersione');
    const p0 = await page.evaluate(() => window.__game.stage.view.targetYaw);
    await axes([0, 0, 1, 0]);
    await step(3, 0.1);
    await axes([0, 0, 0, 0]);
    check((await page.evaluate(() => window.__game.stage.view.targetYaw)) !== p0, 'stick destro sott’acqua: lo sguardo gira');
    const dh = await page.evaluate(() => document.querySelector('.dive-hud .hud-hint')?.textContent ?? '');
    check(!/[Cc]licca/.test(dh), `il suggerimento sott’acqua coi tasti del controller («${dh}»)`);
    await shot(`${tag}-13-immersione`);
    await press('Y');
    await step(25, 0.1);
    check((await mode()) !== 'dive', `Y: si risale (${await mode()})`);
  } else check(false, 'all’alba c’è «Scendi con le bombole» selezionato');
  // tornando alla tastiera gli aiuti tornano ai tasti
  await page.keyboard.press('Shift');
  check(!(await page.evaluate(() => document.documentElement.classList.contains('pad'))), 'un tasto della tastiera: gli aiuti tornano alla tastiera');
  if (s.logs.length) console.log(s.logs.slice(-10).join('\n'));
  check(!s.logs.some((l) => l.startsWith('[pageerror]')), 'nessun errore nella pagina');
  await page.close();
}

// la cinematica del finale si salta col controller (A)
{
  console.log('\n— cinematica —');
  const s = await session('?step&notte=6', 1);
  await s.press('A');
  await s.step(3);
  await s.page.evaluate(() => window.__game.app.intro(6));
  await s.step(40, 0.1);
  // la notte 6 vinta: parte la cinematica del finale A
  const started = await s.page.evaluate(() => {
    const n = window.__game.app.night;
    n.handle({ t: 'won' });
    return !!n.cine;
  });
  check(started, 'notte 6 vinta: la cinematica del finale');
  await s.step(10, 0.1);
  await s.press('A');
  check(await s.page.evaluate(() => { const c = window.__game.app.night?.cine; return !c || c.t >= c.s.length; }), 'A salta la cinematica');
  await s.step(10, 0.1);
  check((await s.mode()) === 'end', `poi i risultati (${await s.mode()})`);
  await s.page.close();
}

await browser.close();
console.log(failures.length ? `\n${failures.length} prove fallite` : '\ntutte le prove passate');
process.exit(failures.length ? 1 : 0);
