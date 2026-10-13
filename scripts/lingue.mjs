// Le schermate in ogni lingua, come le vede il giocatore (docs/LOCALIZZAZIONE.md, passo 5): per ogni lingua, alla
// finestra più piccola che il gioco permette (960×540), allo Steam Deck (1280×800) e a 1920×1080, coi testi normali e
// molto grandi, apre ogni schermata (avvertenza, titolo, opzioni, extra, diario, catalogo pesce per pesce, notte extra,
// intro, pausa, risultati, alba col disegno, titoli di coda) e ogni riquadro dell'HUD della notte e dell'immersione
// con tutti i testi che ci finiscono dentro (suggerimenti, avvisi, didascalie, radio, schede dei pesci). Controlla che
// nessuna scritta esca dallo schermo o dal riquadro che la contiene (pulsanti, schede, pagine del libro), anche coi
// tasti del controller al posto di quelli della tastiera. Scatta le foto delle schermate a 1280×800, testi molto grandi.
// Uso: node scripts/lingue.mjs [url] [cartella] [lingue, es. es,fr]   (url di partenza: http://localhost:5173/, con `npm run dev`)
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const base = process.argv[2] ?? 'http://localhost:5173/';
const dir = process.argv[3] ?? 'shots/lingue';
const only = process.argv[4] ? process.argv[4].split(',') : null;
const SIZES = [
  [960, 540],
  [1280, 800],
  [1920, 1080],
];
const TEXT = [1, 1.4];
/** le foto: a questa misura e con questa dimensione dei testi */
const PHOTO = { w: 1280, h: 800, ts: 1.4 };

const browser = await chromium.launch({
  executablePath: process.env.CHROME ?? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
const errors = [];
page.on('pageerror', (e) => errors.push(e.message));
// le pagine del catalogo si girano subito (niente transizione)
await page.emulateMedia({ reducedMotion: 'reduce' });
await page.addInitScript(() => {
  try {
    localStorage.setItem('splashland.save.v1', JSON.stringify({ version: 1, lang: 'it', night: 7, options: { textSize: 1, quality: 0.5 } }));
  } catch {}
});
await page.goto(base + '?step', { waitUntil: 'load' });
await page.waitForFunction(() => window.__game?.step, null, { timeout: 300000 });

// nella pagina: i moduli del gioco (gli stessi che usa lui) e il controllo delle scritte
await page.evaluate(async () => {
  const [I, C, G, D, H, P, T] = await Promise.all([
    import('/src/i18n.ts'),
    import('/src/game/catalog.ts'),
    import('/src/game/config.ts'),
    import('/src/app/disegni.ts'),
    import('/src/app/hud.ts'),
    import('/src/app/pad.ts'),
    import('/src/app/tastiera.ts'),
  ]);
  const app = window.__game.app;
  // la scena non serve (si guardano le scritte) e senza GPU disegnarla rallenta le foto
  document.querySelector('canvas').style.visibility = 'hidden';
  const noop = () => {};

  /** I rettangoli delle scritte vere (i nodi di testo) dentro `root`, con l'elemento che le contiene. */
  const texts = (root) => {
    const out = [];
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      if (!n.textContent.trim()) continue;
      const e = n.parentElement;
      const cs = getComputedStyle(e);
      if (cs.visibility === 'hidden' || e.closest('[hidden]')) continue;
      const r = document.createRange();
      r.selectNodeContents(n);
      const rects = [...r.getClientRects()].filter((x) => x.width > 0 && x.height > 0);
      if (!rects.length) continue;
      const box = {
        l: Math.min(...rects.map((x) => x.left)),
        t: Math.min(...rects.map((x) => x.top)),
        r: Math.max(...rects.map((x) => x.right)),
        b: Math.max(...rects.map((x) => x.bottom)),
      };
      out.push({ e, box, text: n.textContent.trim() });
    }
    return out;
  };
  /** Un riquadro che si vede: un bordo, uno sfondo, o che taglia quello che esce (overflow). */
  const isBox = (e) => {
    const cs = getComputedStyle(e);
    if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible') return true;
    if (e.tagName === 'BUTTON') return true;
    if (parseFloat(cs.borderTopWidth) > 0 && parseFloat(cs.borderBottomWidth) > 0 && cs.borderTopStyle !== 'none') return true;
    const bg = cs.backgroundColor;
    if (bg && bg !== 'transparent' && !/rgba\(.*,\s*0\)$/.test(bg)) return true;
    return cs.backgroundImage !== 'none' && !cs.backgroundImage.includes('gradient');
  };
  const name = (e) => `${e.tagName.toLowerCase()}${e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\s+/).join('.') : ''}`;
  /** Le scritte di `root` che escono dallo schermo o dal riquadro più vicino che le contiene (la riga del difetto e la
   *  scritta). Una riga è alta quanto il suo font: in verticale può superare il riquadro di poco (0,3 em) senza che
   *  l'inchiostro esca. Dentro una schermata o una lista che scorre, in verticale si può andare oltre lo schermo. */
  window.__fuori = (root, stop = root) => {
    const W = innerWidth, H = innerHeight;
    const bad = [];
    for (const { e, box, text } of texts(root)) {
      const t = text.length > 40 ? text.slice(0, 40) + '…' : text;
      const tv = Math.max(2, parseFloat(getComputedStyle(e).fontSize) * 0.3);
      const where = (r) => `(${Math.round(box.l - r.left)},${Math.round(box.t - r.top)}–${Math.round(box.r - r.right)},${Math.round(box.b - r.bottom)})`;
      let scroller = false;
      for (let a = e; a && a !== document.body; a = a.parentElement) if (/auto|scroll/.test(getComputedStyle(a).overflowY)) scroller = true;
      if (box.l < -2 || box.r > W + 2 || (!scroller && (box.t < -tv || box.b > H + tv))) {
        bad.push(`${name(e)} fuori dallo schermo ${where({ left: 0, top: 0, right: W, bottom: H })}: «${t}»`);
        continue;
      }
      for (let a = e; a && a !== stop.parentElement; a = a.parentElement) {
        if (!isBox(a)) continue;
        const r = a.getBoundingClientRect();
        const scroll = /auto|scroll/.test(getComputedStyle(a).overflowY);
        if (box.l < r.left - 2 || box.r > r.right + 2 || (!scroll && (box.t < r.top - tv || box.b > r.bottom + tv))) bad.push(`${name(e)} esce da ${a === e ? 'sé' : name(a)} ${where(r)}: «${t}»`);
        break;
      }
    }
    return bad;
  };
  /** Il logo del titolo è un'immagine (__fuori non lo vede): i tubi accesi (le frazioni le stampa tools/render/logo.py;
   *  sotto, fino in fondo all'immagine, c'è solo il bagliore) stanno nello schermo e non arrivano alle voci del menu. */
  window.__logo = () => {
    const img = document.querySelector('.title h1.logo .insegna');
    const menu = document.querySelector('.title .menu');
    if (!img || !menu) return ['h1.logo: manca il logo o il menu'];
    const r = img.getBoundingClientRect();
    const m = menu.getBoundingClientRect();
    const bad = [];
    const fondo = r.top + r.height * 0.86;
    if (fondo > m.top) bad.push(`h1.logo arriva sulle voci del menu (${Math.round(fondo - m.top)} px)`);
    if (r.left + r.width * 0.07 < -2 || r.left + r.width * 0.93 > innerWidth + 2 || r.top + r.height * 0.09 < -2) bad.push('h1.logo esce dallo schermo');
    return bad;
  };
  /** Le animazioni a metà (dissolvenze, il rullo dei titoli) portate alla fine, o ferme all'inizio se non finiscono. */
  window.__ferma = () => {
    for (const a of document.getAnimations()) {
      try {
        a.finish();
      } catch {
        a.pause();
        a.currentTime = 0;
      }
    }
  };

  /** Ogni schermata: una funzione che la apre (e restituisce l'elemento da controllare). */
  const ui = document.getElementById('ui');
  const scr = () => ui.querySelector(':scope > .screen');
  const S = () => I.STRINGS[app.lang];
  const LORE_IDS = G.LORE.map((l) => l.id);
  const DIS = Object.values(D.DISEGNI_ALBA);
  const caught = Object.fromEntries(C.FISH.map((f) => [f.id, { count: 12, bestKg: f.kg[1] }]));
  window.__schermate = {
    avvertenza: () => (app.screens.warning(noop), scr()),
    titolo: () => (app.screens.title({ canContinue: true, onNew: noop, onContinue: noop, onExtraNight: noop, onJournal: noop, onOptions: noop, onQuit: noop }), scr()),
    'nuova-partita': () => (app.screens.newGameConfirm({ onYes: noop, onNo: noop }), scr()),
    opzioni: () => (app.screens.options(app.save.options, { onChange: noop, onBack: noop, fullscreen: noop, lang: true }), scr()),
    extra: () => (app.screens.extras({ onJournal: noop, onCatalog: noop, onBack: noop }), scr()),
    diario: () => (app.screens.journal(LORE_IDS, noop, { all: DIS, found: DIS }), scr()),
    'diario-vuoto': () => (app.screens.journal([], noop, { all: DIS, found: [] }), scr()),
    catalogo: () => (app.screens.catalog({ caught, images: app.assets.fish, revealAll: true, onBack: noop }), scr()),
    // la pagina del pesce con la descrizione più lunga della lingua
    'catalogo-pesce': () => {
      app.screens.catalog({ caught, images: app.assets.fish, revealAll: true, onBack: noop });
      const desc = (f) => (I.testiPesce ? I.testiPesce(f, app.lang).desc : (f.desc[app.lang] ?? f.desc.it));
      const f = [...C.FISH].sort((a, b) => desc(b).length - desc(a).length)[0];
      const fams = ['skeletal', 'zombie', 'glitch', 'corrupt', 'bleeding'];
      ui.querySelector(`.book-tabs .tab[data-k="${fams.indexOf(f.family) + 1}"]`).click();
      const i = C.FISH.filter((x) => x.family === f.family).indexOf(f);
      ui.querySelectorAll('.page.left .snap')[i].click();
      return scr();
    },
    'notte-extra': () => (app.screens.extraNight(app.save.extra, { onChange: noop, onStart: noop, onBack: noop }), scr()),
    intro: () => (app.screens.intro(G.EXTRA_NIGHT, 12), scr()),
    'intro-1': () => (app.screens.intro(1, 4), scr()),
    pausa: () => (app.screens.pause({ onResume: noop, onRestart: noop, onOptions: noop, onMenu: noop }), scr()),
    morte: () => {
      // la frase di morte più lunga della lingua
      const d = Object.values(S().deaths).sort((a, b) => b.length - a.length)[0];
      app.screens.results({ won: false, text: d, caught: 12, fed: 3, lore: 2, demoEnd: false, onRetry: noop, onMenu: noop });
      return scr();
    },
    alba: () => {
      app.screens.results({ won: true, text: '', caught: 12, fed: 3, lore: 2, demoEnd: false, spare: 4, onDive: noop, onNext: noop, onRetry: noop, onMenu: noop, drawing: 'piscina' });
      return scr();
    },
    'alba-ripresa': () => (app.screens.dawn({ spare: 4, drawing: 'compleanno', onDive: noop, onNext: noop, onMenu: noop }), scr()),
    'fine-demo': () => {
      app.screens.results({ won: true, text: S().finaleA, caught: 12, fed: 3, lore: 2, demoEnd: true, onWishlist: noop, onRetry: noop, onMenu: noop });
      return scr();
    },
    'notte-extra-aperta': () => {
      app.screens.results({ won: true, text: S().finaleNessuno, caught: 12, fed: 3, lore: 2, demoEnd: true, onExtra: noop, onRetry: noop, onMenu: noop });
      return scr();
    },
    titoli: () => {
      app.screens.credits(noop);
      // il rullo fermo, dall'alto dello schermo
      const roll = ui.querySelector('.credits-roll');
      roll.style.animation = 'none';
      roll.style.paddingTop = '8vh';
      return scr();
    },
  };

  /** Il catalogo pesce per pesce: le pagine di ogni famiglia, con ogni pesce scelto. */
  window.__catalogo = () => {
    const bad = [];
    const book = ui.querySelector('.book-screen');
    const tabs = [...book.querySelectorAll('.book-tabs .tab')];
    for (const tab of tabs) {
      tab.click();
      window.__ferma();
      bad.push(...window.__fuori(book).map((x) => `pagina ${tab.dataset.k}: ${x}`));
      for (const snap of [...book.querySelectorAll('.page.left .snap.can')]) {
        snap.click();
        window.__ferma();
        const nome = book.querySelector('.page.right .fish-name')?.textContent;
        bad.push(...window.__fuori(book.querySelector('.page.right'), book).map((x) => `«${nome}»: ${x}`));
      }
    }
    return bad;
  };

  /** L'HUD della notte e quello dell'immersione, riempiti a turno con tutti i loro testi. */
  window.__hud = async () => {
    const s = S();
    const bad = [];
    const hud = new H.Hud(ui, app.lang);
    const prova = async (what, fill, el) => {
      fill();
      // la foto del pesce nella scheda: la sua altezza conta
      for (const im of (el ?? hud.root).querySelectorAll('img')) if (!im.complete) await im.decode().catch(() => {});
      window.__ferma();
      bad.push(...window.__fuori(el ?? hud.root, ui).map((x) => `${what}: ${x}`));
    };
    hud.setClock(G.EXTRA_NIGHT, 5, 50);
    hud.setQuota(12, 12);
    hud.setLamp(2);
    await prova('orologio e quota', () => {});
    const hintEl = hud.root.querySelector('.hud-hint');
    const pads = new Set(Object.keys(s.pad.hints));
    for (const [k, v] of Object.entries(s.hints)) {
      await prova(`suggerimento ${k}`, () => hud.hint(T.tastiText(v)), hintEl);
      hud.hint('');
      if (pads.has(k)) {
        await prova(`suggerimento ${k} (controller)`, () => hud.hint(P.pad.glyphs(s.pad.hints[k])), hintEl);
        hud.hint('');
      }
    }
    for (const [k, v] of [['look', T.tastiText(s.look)], ['look (controller)', P.pad.glyphs(s.pad.look)], ['sonar', s.sonarHint], ['luce', T.tastiText(s.lampHint)]]) {
      await prova(`suggerimento ${k}`, () => hud.hint(v), hintEl);
      hud.hint('');
    }
    const toastEl = hud.root.querySelector('.hud-toast');
    const toasts = [
      ...Object.values(s.denied).map((d) => [d, '']),
      [s.lineSnap, ''],
      [s.escaped, ''],
      [s.baitStolen, ''],
      [s.sixAm, s.quotaMissed],
      [s.sixAm, `${s.survived} · ${s.quotaMet}`],
      ...Object.values(I.LORE_TEXT[app.lang]).map((t) => [t.title, s.loreFound]),
    ];
    for (const [big, small] of toasts) await prova(`avviso «${big}»`, () => hud.toast(big, small), toastEl);
    // i pesci: l'avviso col nome e la scheda del Catalogo
    for (const f of C.FISH) {
      const t = I.testiPesce ? I.testiPesce(f, app.lang) : { name: f.name[app.lang], desc: f.desc[app.lang] ?? f.desc.it };
      await prova(`avviso «${t.name}»`, () => hud.toast(t.name, `${s.caught} · ${I.decimal('12.40', app.lang)} ${s.kg}`), toastEl);
      await prova(`scheda «${t.name}»`, () => hud.catchCard({ img: app.assets.fish[f.id] ?? null, name: t.name, meta: `${s.families[f.family]} · ${s.rarities[f.rarity]}`, kg: `${I.decimal('12.40', app.lang)} ${s.kg}`, desc: t.desc, family: f.family, isNew: s.newSpecies }), hud.root.querySelector('.hud-card'));
    }
    const capEl = hud.root.querySelector('.hud-cap');
    for (const [k, v] of Object.entries(s.captions)) await prova(`didascalia ${k}`, () => hud.caption(v), capEl);
    const subEl = hud.root.querySelector('.hud-sub');
    const radio = [...Object.values(I.RADIO).flatMap((n) => n[app.lang]), ...I.RADIO_FINALE[app.lang]];
    for (const l of radio) if (l.text) await prova(`radio «${l.text.slice(0, 30)}»`, () => hud.subtitle(s.radioName, l.text), subEl);
    for (const c of [...s.hatchCount, s.hatchReady]) await prova(`Hatch «${c}»`, () => hud.subtitle(s.hatchName, c), subEl);
    for (const k of ['finaleTuoi', 'finaleNessuno']) await prova(`finale ${k}`, () => hud.cineText(s[k]), hud.root.querySelector('.hud-cine'));
    for (const [k, v] of Object.entries(s.labels)) await prova(`etichetta ${k}`, () => hud.hover(v, innerWidth * 0.85, innerHeight * 0.5), hud.root.querySelector('.hud-hover'));
    hud.hover('', 0, 0);
    await prova('voltati', () => hud.showTurn(true), hud.turnEl);
    hud.destroy();

    // l'immersione: gli stessi elementi di src/app/dive.ts
    const root = document.createElement('div');
    root.className = 'hud dive-hud';
    const cap = document.createElement('div');
    cap.className = 'dive-cap show';
    const hint = document.createElement('div');
    hint.className = 'hud-hint show';
    const up = document.createElement('button');
    up.className = 'dive-up';
    up.textContent = s.dive.ascend;
    up.append(P.badge('Y'));
    const spots = document.createElement('div');
    spots.className = 'dive-spots';
    const buttons = document.createElement('div');
    buttons.className = 'dive-buttons';
    const back = document.createElement('button');
    back.className = 'dive-back';
    back.textContent = s.dive.links.toCave;
    back.append(P.badge('B'));
    buttons.append(back);
    root.append(spots, buttons, cap, hint, up);
    ui.append(root);
    await prova('immersione: suggerimento', () => (hint.textContent = s.dive.hint), root);
    await prova('immersione: suggerimento (controller)', () => (hint.textContent = P.pad.glyphs(s.pad.diveHint)), root);
    const caps = [s.dive.loading, s.dive.emptyDen, s.dive.blocked, s.dive.airOut, s.dive.noFish, s.dive.alreadyFed, ...Object.values(s.dive.notes),
      ...['Gulpy', 'Molly', 'Hatch', 'Robin', 'Archie', 'Lampy', 'Fangy'].map((w) => s.dive.offered(w)),
      ...Object.values(I.LORE_TEXT[app.lang]).map((t) => s.dive.found(t.title))];
    for (const c of caps) await prova(`immersione: didascalia «${c.slice(0, 30)}»`, () => (cap.textContent = c), root);
    // le etichette dei passaggi, al centro dello schermo
    for (const [k, v] of Object.entries(s.dive.links)) {
      const e = document.createElement('div');
      e.className = 'dive-spot';
      e.style.left = '50%';
      e.style.top = '50%';
      const span = document.createElement('span');
      span.textContent = v;
      e.append(span);
      spots.replaceChildren(e);
      await prova(`immersione: passaggio ${k}`, () => {}, root);
    }
    spots.replaceChildren();
    // la domanda accanto al letto, con la parola più lunga dei nomi
    for (const w of ['Gulpy', 'Molly', 'Hatch', 'Robin', 'Archie', 'Lampy', 'Fangy']) {
      const box = document.createElement('div');
      box.className = 'dive-confirm';
      const p = document.createElement('p');
      p.textContent = s.dive.offer(w);
      const yes = document.createElement('button');
      yes.textContent = s.dive.offerYes;
      const no = document.createElement('button');
      no.textContent = s.dive.offerNo;
      const row = document.createElement('div');
      row.className = 'row';
      row.append(yes, no);
      box.append(p, row);
      root.append(box);
      await prova(`immersione: lasciare il pesce a ${w}`, () => {}, root);
      box.remove();
    }
    root.remove();
    return bad;
  };

  /** La lingua del gioco, cambiata come dalle opzioni (il pulsante passa alla lingua dopo). */
  window.__lingua = (lang) => {
    for (let i = 0; i < 12 && app.lang !== lang; i++) {
      app.screens.lang = app.lang;
      app.options(noop);
      const label = [...ui.querySelectorAll('.screen.opts label')].find((l) => l.querySelector('span')?.textContent === S().language);
      label.querySelector('button').click();
    }
    return app.lang === lang;
  };
  window.__testo = (ts) => {
    app.save.options.textSize = ts;
    document.documentElement.style.setProperty('--ts', String(ts));
  };
  window.__lingue = I.LANGS;
});

const langs = (await page.evaluate(() => window.__lingue)).filter((l) => !only || only.includes(l));
const report = {};
let total = 0;
for (const lang of langs) {
  check(await page.evaluate((l) => window.__lingua(l), lang), `${lang}: la lingua si sceglie dalle opzioni`);
  // i font della lingua (cinese, giapponese e coreano) caricati prima di misurare
  await page.evaluate(() => document.fonts.ready);
  fs.mkdirSync(`${dir}/${lang}`, { recursive: true });
  const bad = (report[lang] = []);
  for (const [w, h] of SIZES) {
    await page.setViewportSize({ width: w, height: h });
    for (const ts of TEXT) {
      const tag = `${w}×${h} testi ${ts === 1 ? 'normali' : 'molto grandi'}`;
      await page.evaluate((ts) => window.__testo(ts), ts);
      for (const padOn of [false, true]) {
        await page.evaluate((on) => document.documentElement.classList.toggle('pad', on), padOn);
        const names = await page.evaluate(() => Object.keys(window.__schermate));
        for (const n of names) {
          const out = await page.evaluate(async (n) => {
            const el = window.__schermate[n]();
            await document.fonts.ready;
            window.__ferma();
            const extra = n === 'catalogo' ? window.__catalogo() : n === 'titolo' ? window.__logo() : [];
            // il catalogo torna alla prima pagina per la foto
            if (n === 'catalogo') document.querySelector('.book-tabs .tab')?.click();
            return [...window.__fuori(el.parentElement ?? el), ...extra];
          }, n);
          for (const x of out) bad.push(`${tag}${padOn ? ' controller' : ''} · ${n} · ${x}`);
          if (!padOn && w === PHOTO.w && ts === PHOTO.ts) await page.screenshot({ path: `${dir}/${lang}/${n}.png`, timeout: 600000 });
        }
        const hud = await page.evaluate(() => window.__hud());
        for (const x of hud) bad.push(`${tag}${padOn ? ' controller' : ''} · hud · ${x}`);
      }
    }
  }
  // le stesse righe a più misure contano una volta (con le misure dove capitano: G = testi molto grandi, c = controller)
  const uniq = new Map();
  for (const b of bad) {
    const [where, ...rest] = b.split(' · ');
    const k = rest.join(' · ').replace(/\(-?\d+,-?\d+–-?\d+,-?\d+\)/, '');
    if (!uniq.has(k)) uniq.set(k, { k: rest.join(' · '), where: new Set() });
    uniq.get(k).where.add(where.replace(' testi normali', '').replace(' testi molto grandi', ' G').replace(' controller', ' c'));
  }
  report[lang] = [...uniq.values()].map((u) => `${u.k}   [${u.where.size === SIZES.length * TEXT.length * 2 ? 'ovunque' : [...u.where].join(', ')}]`);
  total += report[lang].length;
  console.log(`\n— ${lang}: ${report[lang].length} scritte fuori posto —`);
  for (const r of report[lang].slice(0, 60)) console.log(`  ${r}`);
  if (report[lang].length > 60) console.log(`  … e altre ${report[lang].length - 60} (tutte in ${dir}/rapporto.json)`);
}
fs.writeFileSync(`${dir}/rapporto.json`, JSON.stringify(report, null, 1));
if (errors.length) console.log(`\nerrori nella pagina:\n${errors.slice(0, 10).join('\n')}`);
await browser.close();
console.log(total ? `\n${total} scritte fuori posto (${dir}/rapporto.json)` : '\ntutte le scritte stanno al loro posto');
process.exit(total || errors.length ? 1 : 0);

function check(ok, what) {
  console.log(`${ok ? 'ok  ' : 'NO  '} ${what}`);
  if (!ok) errors.push(what);
}
