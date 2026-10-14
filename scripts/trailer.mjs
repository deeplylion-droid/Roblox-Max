// Il trailer A «Le regole» (scelto dall'utente il 14 ottobre, da approvare): le scene prese dal motore, fotogramma per
// fotogramma, a 1920×1080 e 30 al secondo, in inglese con la nebbia accesa. Ogni scena è una notte nuova messa in scena a
// mano: i mostri negli stati veri della simulazione (si muovono come in gioco), i gesti del pescatore coi tasti veri, la
// vista guidata come una camera. Solo la tela del motore, senza l'interfaccia: le scritte, i suoni e il logo li mette il
// montaggio (tools/trailer/montaggio.py).
// Escono in <cartella>/<scena>/f0000.jpg…
// Uso: node scripts/trailer.mjs <cartella> [scena…]   (con `npm run dev` sulla porta 5173; senza scene, tutte)
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const FPS = 30;
/** TRAILER_ANTEPRIMA=k: un fotogramma ogni k (il tempo della scena corre uguale), per guardare la regia in fretta */
const PASSO = Math.max(1, Number(process.env.TRAILER_ANTEPRIMA ?? 1));
const [out = 'trailer', ...scelte] = process.argv.slice(2);
const base = (process.env.TRAILER_URL ?? 'http://127.0.0.1:5173/').replace(/\/?$/, '/');

/**
 * Le scene. notte: quale notte si gioca; secondi: quanto dura; prima: secondi giocati prima di cominciare a registrare
 * (non escono); pagina: [da, a] i secondi in cui si registra la pagina intera, con l'interfaccia del gioco sopra la tela
 * (il sonar a tutto schermo); camera: [secondo, yaw, pitch, campo] con un passaggio morbido fra l'uno e l'altro (yaw,
 * pitch o campo null: li decide il gioco); prepara(n, a, g): una volta, a notte appena cominciata (i mostri che non
 * servono sono già fermi); regia(t, n, a, g): prima di ogni fotogramma (t in secondi dall'inizio della registrazione,
 * negativo prima); dopo(t, n): dopo la grafica di ogni fotogramma, per toccare lo stato visivo (n.v) dove la
 * simulazione non arriva. Le funzioni girano nella pagina: niente variabili di qui dentro. Nella pagina ci sono:
 * tasto(k, giù) per i tasti, passa(x) vero nel fotogramma in cui t supera x, liscio(a, b, x) per le salite morbide.
 */
const SCENE = {
  // la barca nella nebbia a luce spenta; poi la luce si accende, sfarfallando (la radio la mette il montaggio)
  apertura: {
    notte: 1,
    secondi: 10.7,
    camera: [[0, 14, -13, 92], [10.7, 22, -10, 80]],
    prepara: (n, a, g) => {
      n.setLamp(0);
      g.stage.lampShown = 0;
    },
    regia: (t, n, a, g) => {
      const st = g.stage;
      if (passa(1.5)) {
        n.setLamp(1);
        st.lampDip = 1;
      }
      if (passa(1.66)) st.lampDip = 0.85;
      if (passa(1.9)) st.lampDip = 0.6;
      if (passa(2.3)) st.lampDip = 0.35;
    },
  },
  // il lancio, l'abboccata, la ferrata e il recupero, il pesce che esce dall'acqua
  pesca: {
    notte: 1,
    secondi: 5.6,
    camera: [[0, 33, -6, 72], [5.6, 31, -8, 64]],
    prepara: (n) => {
      n.sim.fishing.reelMul = 2.4;
    },
    regia: (t, n) => {
      const f = n.sim.fishing;
      if (passa(0.25)) tasto(' ', true);
      if (passa(0.35)) tasto(' ', false);
      // il pesce abbocca presto
      if (f.phase === 'waiting' && t > 1.7) f.timer = 0;
      if (passa(2.45)) tasto(' ', true);
      // il recupero: si tiene e si molla quando strattona, come un pescatore bravo
      if (f.phase === 'reeling' && t > 2.6) {
        if (f.tension > 0.72) tasto(' ', false);
        else if (f.tension < 0.3) tasto(' ', true);
      }
      if (f.phase === 'landing') tasto(' ', false);
    },
  },
  // Gulpy si aggrappa alla prua (la luce sfarfalla), pretende; gli si lancia un pesce e mastica
  gulpy: {
    notte: 5,
    secondi: 4.0,
    camera: [[0, -22, 9, 78], [4.0, -24, 11, 68]],
    prepara: (n) => {
      n.sim.fish = 3;
    },
    regia: (t, n) => {
      const g = n.sim.gulpy;
      if (passa(0)) {
        // il punto dell'arrampicata in cui le mani arrivano sul bordo
        g.state = 'climbing';
        g.stateTime = 1.0;
        g.timer = 0.5;
        n.gulpyDive = 1;
      }
      if (g.state === 'demanding') g.timer = Math.max(g.timer, 5);
      if (passa(2.5)) n.sim.throwFish();
    },
  },
  // Molly sale sul fianco destro e ti fissa, sbattendo gli occhi
  molly: {
    notte: 5,
    secondi: 3.8,
    camera: [[0, 71, -9, 68], [3.8, 73, -10, 58]],
    regia: (t, n) => {
      const m = n.sim.molly;
      if (passa(0)) {
        m.side = 'right';
        m.state = 'peeking';
        m.update = () => {};
      }
    },
  },
  // Hatch emerge dietro la poppa e conta; il telone scende sulla testa
  hatch: {
    notte: 5,
    secondi: 3.8,
    camera: [[0, 178, -2, 64], [3.8, 178, -1, 56]],
    regia: (t, n) => {
      const h = n.sim.hatch;
      if (passa(0)) {
        h.state = 'counting';
        h.count = 0;
        h.timer = 0.25;
      }
      if (passa(2.35)) n.hideToggle();
    },
  },
  // Robin sale sul bordo con le mani nel secchio; la luce al massimo: si ritrae e scappa
  robin: {
    notte: 5,
    secondi: 3.6,
    camera: [[0, -27, -13, 80], [3.6, -29, -14, 72]],
    prepara: (n) => {
      n.sim.fish = 3;
    },
    regia: (t, n) => {
      const r = n.sim.robin;
      if (passa(0)) {
        r.state = 'climbing';
        r.timer = 1.25;
        r.lit = 0;
        r.stolen = 0;
      }
      if (passa(1.75)) {
        n.setLamp(2);
        // già un po' di luce addosso: scappa prima della fine della scena
        r.lit = 1.0;
      }
    },
  },
  // Archie fuori dall'acqua davanti alla prua prende fiato; la luce si spegne: al buio restano i suoi occhi
  archie: {
    notte: 5,
    secondi: 3.6,
    camera: [[0, 7, 5, 54], [3.6, 8, 7, 46]],
    regia: (t, n) => {
      const r = n.sim.archie;
      if (passa(0)) {
        r.state = 'inhaling';
        r.timer = 4.5;
        r.inhaleTime = 4.5;
        n.v.aRise = 0.5;
      }
      if (passa(2.05)) n.setLamp(0);
    },
  },
  // la lenza in acqua; il campanellino suona tre colpi uguali e Lampy affiora sulla lenza
  lampy: {
    notte: 5,
    secondi: 3.3,
    prima: 3.4,
    camera: [[-3.4, 42, -5, 56], [0, 45, -4, 54], [3.3, 46, -3, 48]],
    regia: (t, n) => {
      const f = n.sim.fishing;
      const l = n.sim.lampy;
      if (passa(-3.3)) tasto(' ', true);
      if (passa(-3.2)) tasto(' ', false);
      // niente pesci veri: la lenza aspetta Lampy
      if (f.phase === 'waiting') f.timer = 99;
      if (passa(-0.9)) {
        l.state = 'lurking';
        l.timer = 0;
        l.stateTime = 0;
      }
    },
  },
  // le lucine di Fangy arrivano sott'acqua, lui sale accanto alla barca; un rumore e si volta di scatto
  fangy: {
    notte: 5,
    secondi: 3.3,
    camera: [[0, 115, -13, 60], [3.3, 112, -15, 50]],
    prepara: (n, a, g) => {
      // dietro al pescatore la luce arriva poca: la luce al massimo e la luminosità del gioco più alta, come nelle opzioni
      n.setLamp(2);
      g.stage.lampShown = 2;
      g.stage.brightness = 1.4;
    },
    regia: (t, n) => {
      const f = n.sim.fangy;
      if (passa(0)) {
        f.state = 'approaching';
        f.timer = 0.9;
        f.stateTime = 0;
        f.heard = 0;
      }
      if (f.state === 'listening') f.timer = Math.max(f.timer, 5);
      if (passa(2.3)) f.hear(n.sim.world);
    },
  },
  // col binocolo: Soggy al relitto, sporto verso di te
  soggy: {
    notte: 5,
    secondi: 3.1,
    camera: [[0, 14.8, 0.2, 70], [0.34, 14.8, null, null]],
    regia: (t, n) => {
      const x = n.sim.foxy;
      if (passa(0)) {
        x.update = () => {};
        x.place = x.places.findIndex((q) => q.id === 'relitto');
        x.state = 'leaning';
        n.binoFov = 5;
      }
      if (passa(0.35)) n.raiseBino(true);
      // il binocolo si mette sul posto (il relitto): un poco più giù, dove sta lui
      if (passa(0.36)) n.binoPitch = 0.15;
    },
  },
  // notte 6: la Madre non si vede (scelta dell'utente del 14 ottobre). Col sonar aperto la sua eco enorme arriva e le
  // passa sotto la barca; poi la prua: il mare fermo, la luce che trema, la barca che si solleva e s'inclina sul suo
  // dorso. Il sonar a tutto schermo è interfaccia del gioco (HTML), non la tela: quei fotogrammi sono la pagina intera
  madre: {
    notte: 6,
    secondi: 9.6,
    pagina: [0, 4.0],
    camera: [[0, -10, -6, 80], [4.0, -10, -6, 80], [9.6, -13, -4, 68]],
    prepara: (n) => {
      n.sim.mother.update = () => {};
      // l'interfaccia della notte via; del sonar resta lo schermo (senza la scritta per chiuderlo)
      n.hud.root.style.visibility = 'hidden';
      const chiudi = n.sonarEl.querySelector('.sonar-close');
      if (chiudi) chiudi.style.visibility = 'hidden';
    },
    regia: (t, n, a, g) => {
      const mo = n.sim.mother;
      const st = g.stage;
      // l'ombra si mette appena davanti al fascio, che passandoci sopra la accende
      const davanti = () => (mo.angle = (n.sonar.sweep + 40) % 360);
      if (passa(0)) {
        mo.state = 'approaching';
        mo.stateTime = 0;
        mo.dist = 0.5;
        davanti();
        n.toggleSonar(true);
      }
      if (passa(1.0)) {
        mo.dist = 0.22;
        davanti();
      }
      if (passa(1.8)) mo.state = 'passing';
      // la passata: a metà (sotto la barca) al taglio sulla prua, poi oltre, piano
      if (mo.state === 'passing') {
        const p = t < 4.0 ? (0.5 * (t - 1.8)) / 2.2 : 0.5 + (0.5 * (t - 4.0)) / 5.6;
        mo.stateTime = Math.max(0, p) * mo.passTime;
      }
      if (passa(4.0)) n.toggleSonar(false);
      if (passa(4.5)) st.lampDip = 0.75;
      if (passa(5.8)) st.lampDip = 0.6;
    },
    dopo: (t, n) => {
      n.v.mCalm = Math.max(liscio(0, 3.0, t), t >= 4 ? 1 : 0);
      n.v.mLift = t < 4 ? 0 : 0.6 + 0.9 * liscio(4.0, 7.0, t);
    },
  },
  // il jumpscare di Molly, poi il segnale perso (la neve)
  jumpscare: {
    notte: 5,
    secondi: 2.6,
    camera: [[0, 70, -9, 66], [0.1, null, null, null]],
    regia: (t, n) => {
      if (passa(0)) {
        n.sim.molly.side = 'right';
        n.sim.provaMorte('molly');
      }
    },
  },
};

/** Una pagina del gioco in inglese, con la nebbia accesa, pronta per essere comandata (?step). */
async function pagina(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', (e) => console.log(`[errore nella pagina] ${e.message}`));
  await page.addInitScript(() => {
    localStorage.setItem('splashland.save.v1', JSON.stringify({ version: 1, rev: 2, lang: 'en', night: 6, current: 6, options: { quality: 1, fog: true, tutorial: false, subtitles: false } }));
    // gli aiuti per le scene
    window.__t = 0;
    window.__tPrima = -1e9;
    window.passa = (x) => window.__tPrima < x && window.__t >= x;
    window.liscio = (a, b, x) => {
      const k = Math.max(0, Math.min(1, (x - a) / (b - a)));
      return k * k * (3 - 2 * k);
    };
    const codici = { ' ': 'Space', b: 'KeyB', c: 'KeyC', e: 'KeyE', f: 'KeyF', q: 'KeyQ' };
    window.tasto = (k, giu) => window.dispatchEvent(new KeyboardEvent(giu ? 'keydown' : 'keyup', { key: k, code: codici[k] ?? '' }));
  });
  await page.goto(`${base}?step`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__game?.step, null, { timeout: 300000, polling: 250 });
  // l'avvertenza dell'avvio aspetta un tasto qualsiasi: se no il primo tasto di una scena la chiude e torna al titolo
  await page.evaluate(() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Shift', code: 'ShiftLeft' })));
  return page;
}

/** Registra una scena in <out>/<nome>. */
async function registra(page, nome, s) {
  const dir = `${out}/${nome}`;
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  await page.evaluate(
    ({ notte, camera, prepara, regia, dopo }) => {
      const g = window.__game;
      const a = g.app;
      // il tempo della scena riparte: passa(x) scatta anche per gli x del primo fotogramma
      window.__t = window.__tPrima = -1e9;
      a.title();
      a.intro(notte);
      a.startNight();
      const n = a.night;
      const sim = n.sim;
      // tutti fermi: i mostri arrivano solo quando li chiama la scena
      for (const k of ['gulpy', 'molly', 'hatch', 'robin', 'archie', 'lampy', 'fangy', 'foxy']) if (sim[k]) sim[k].timer = 1e9;
      if (sim.mother) sim.mother.update = () => {};
      // niente falsi allarmi (il tonfo, la sagoma nella nebbia)
      n.falso = { next: 1e9, left: 0, boost: 0 };
      n.updateSagoma = () => {};
      // le luci lontane del paesaggio: gli aloni sono pensati per la vista larga del gioco (90°); con le inquadrature
      // strette del trailer si stringono, come fa il gioco col binocolo. La boa verde, che lampeggia forte proprio dove
      // si pesca, e le luci rosse dell'antenna, che stanno dietro a Molly e a Fangy, più piano
      // (gli originali si tengono da parte: la pagina gira più scene, una dopo l'altra)
      const st = g.stage;
      st.__glows ??= st.landscapeGlows.bind(st);
      st.__update ??= st.update.bind(st);
      const lg = st.__glows;
      st.landscapeGlows = (extra, bino) => {
        const k = bino > 0 ? 1 : Math.min(1, st.view.hfov / 90) ** 1.5;
        return lg(extra, bino).map((l) => {
          const c = l.color;
          const boa = Math.abs(c[1] / Math.max(1e-6, c[0]) - 5) < 0.01 && c[1] > 0.5;
          const antenna = c[0] > 0.5 && c[0] > 10 * c[1];
          const m = boa ? 0.4 : antenna ? 0.6 : 1;
          return { ...l, radius: l.radius * k * (boa || antenna ? 0.6 : 1), color: [c[0] * m, c[1] * m, c[2] * m] };
        });
      };
      g.step(0.1, 20);
      // la camera: i punti della scena, con un passaggio morbido fra l'uno e l'altro
      const su = st.__update;
      const lungo = (k, t) => {
        let i = 0;
        while (i < camera.length - 1 && camera[i + 1][0] <= t) i++;
        const p = camera[i];
        const q = camera[Math.min(i + 1, camera.length - 1)];
        if (p[k] === null || q[k] === null || q === p || t <= p[0]) return p[k];
        if (t >= q[0]) return q[k];
        return p[k] + (q[k] - p[k]) * window.liscio(p[0], q[0], t);
      };
      st.update = (dt) => {
        const t = window.__t;
        const yaw = lungo(1, t), pitch = lungo(2, t), hfov = lungo(3, t);
        if (yaw !== null) st.view.yaw = st.view.targetYaw = yaw;
        if (pitch !== null) st.view.pitch = pitch;
        if (hfov !== null) st.view.hfov = hfov;
        su(dt);
      };
      const fDopo = dopo ? eval(`(${dopo})`) : null;
      if (fDopo) {
        const uv = n.updateVisuals.bind(n);
        n.updateVisuals = (dt) => {
          uv(dt);
          fDopo(window.__t, n);
        };
      }
      st.brightness = 1;
      if (prepara) eval(`(${prepara})`)(n, a, g);
      window.__regia = regia ? eval(`(${regia})`) : () => {};
      window.__night = n;
    },
    {
      notte: s.notte,
      camera: s.camera,
      prepara: s.prepara?.toString(),
      regia: s.regia?.toString(),
      dopo: s.dopo?.toString(),
    },
  );
  const prima = Math.round((s.prima ?? 0) * FPS);
  const tot = Math.round(s.secondi * FPS);
  let k = 0;
  for (let i = -prima; i < tot; i += PASSO) {
    const t = i / FPS;
    // la pagina intera (l'interfaccia del gioco sopra la tela) o la sola tela
    const tutta = !!s.pagina && t >= s.pagina[0] && t < s.pagina[1];
    const url = await page.evaluate(
      ({ t, dt, salva }) => {
        const g = window.__game;
        window.__tPrima = window.__t;
        window.__t = t;
        const n = g.app.night ?? window.__night;
        window.__regia(t, n, g.app, g);
        g.step(dt);
        return salva ? document.querySelector('canvas').toDataURL('image/jpeg', 0.95) : null;
      },
      { t, dt: PASSO / FPS, salva: i >= 0 && !tutta },
    );
    const nome = `${dir}/f${String(k).padStart(4, '0')}.jpg`;
    if (url) fs.writeFileSync(nome, Buffer.from(url.split(',')[1], 'base64'));
    else if (i >= 0) await page.screenshot({ path: nome, type: 'jpeg', quality: 95, timeout: 600000 });
    if (i >= 0) k++;
  }
  console.log(`${nome}: ${k} fotogrammi`);
}

const nomi = scelte.length ? scelte : Object.keys(SCENE);
for (const n of nomi) if (!SCENE[n]) throw new Error(`scena sconosciuta: ${n}`);
fs.mkdirSync(out, { recursive: true });
// TRAILER_PAGINE browser insieme, una scena alla volta ciascuno. Di base uno: senza scheda video la grafica (swiftshader)
// usa già tutti i processori, e due o tre browser insieme fanno meno fotogrammi di uno solo (prova del 14 ottobre: 1,6 s
// a fotogramma con uno, 2,5 con due)
const coda = [...nomi];
const quante = Math.max(1, Math.min(coda.length, Number(process.env.TRAILER_PAGINE ?? 1)));
await Promise.all(
  Array.from({ length: quante }, async () => {
    const browser = await chromium.launch({
      executablePath: process.env.CHROME ?? '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
      args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
    });
    const page = await pagina(browser);
    while (coda.length) {
      const nome = coda.shift();
      await registra(page, nome, SCENE[nome]);
    }
    await browser.close();
  }),
);
