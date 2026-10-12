/** Schermate in DOM sopra la scena: avvertenza, titolo, intro, pausa, opzioni, diario, alba, game over. */
import { FISH, FISH_BY_ID, type FishFamily, type FishSpecies } from '../game/catalog.ts';
import { EXTRA_IDS, EXTRA_MAX, EXTRA_PRESETS, FOXY_NAME, LORE, clampLevel, type ExtraLevels } from '../game/config.ts';
import { LANGS, LANG_NAMES, LORE_TEXT, STRINGS, decimal, type Lang } from '../i18n.ts';
import { disegnoSrc } from './disegni.ts';
import { badge, dualText, type PadButton } from './pad.ts';
import type { CatalogEntry, Options } from './save.ts';

/** Sagoma generica per le specie senza figura. */
const FISH_SHAPE =
  '<svg viewBox="0 0 120 60" aria-hidden="true"><path d="M6 30 C 24 8, 64 6, 86 26 L 112 10 L 104 30 L 112 50 L 86 34 C 64 54, 24 52, 6 30 Z"/></svg>';

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Record<string, string> = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else e.setAttribute(k, v);
  }
  for (const k of kids) e.append(k);
  return e;
}

/** Un disegno a pastelli (disegni.ts): il foglio un po' storto con l'ombra, e la didascalia. */
function drawingFigure(id: string, caption: string, lang: Lang, cls = 'disegno'): HTMLElement {
  const img = h('img', { src: disegnoSrc(id, lang), alt: caption, draggable: 'false' });
  return h('figure', { class: cls }, img, h('figcaption', {}, caption));
}

/** Suoni dell'interfaccia: li imposta l'App quando l'audio è pronto. */
let uiSound: (id: string) => void = () => {};
export function setUiSound(fn: (id: string) => void): void {
  uiSound = fn;
}

function button(label: string, onClick: () => void, kind: 'click' | 'back' | 'start' = 'click'): HTMLButtonElement {
  const b = h('button', { type: 'button' }, label);
  b.addEventListener('mouseenter', () => uiSound('ui_hover'));
  b.addEventListener('click', (e) => {
    e.stopPropagation();
    uiSound(kind === 'back' ? 'ui_back' : kind === 'start' ? 'ui_start' : 'ui_click');
    onClick();
  });
  return b;
}

/** Le due bombole da sub, a linee nel colore del testo: davanti a «Scendi con le bombole» (prova dell'utente del 12
 *  ottobre: «il simbolo delle bombole affianco alla scritta»). */
function tanksIcon(): SVGSVGElement {
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('class', 'icona');
  svg.setAttribute('aria-hidden', 'true');
  svg.innerHTML =
    '<g fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">' +
    '<rect x="4.5" y="7" width="6" height="14.5" rx="3"/><rect x="13.5" y="7" width="6" height="14.5" rx="3"/>' +
    '<path d="M4.5 12.5h15"/><path d="M7.5 7V4.5M16.5 7V4.5M6.5 4.5h11"/>' +
    '<path d="M17.5 4.5c3 0 4.5 2 4.5 4.5s-1 4-2.5 5"/></g>';
  return svg;
}

/** Il pulsante della discesa, con le bombole davanti. */
function diveButton(label: string, onClick: () => void): HTMLButtonElement {
  const b = button(label, onClick, 'start');
  b.prepend(tanksIcon());
  return b;
}

/** B (col controller) preme questo pulsante: tornare indietro. Col controller in uso ci compare accanto il tasto. */
function backKey<T extends HTMLElement>(b: T): T {
  b.dataset.back = '';
  b.append(badge('B'));
  return b;
}

/** Un pulsante di pagina (LB, RB): col controller in uso ci compare accanto il tasto. */
function pageKey<T extends HTMLElement>(b: T, key: Extract<PadButton, 'LB' | 'RB'>): T {
  b.dataset[key === 'LB' ? 'padPrev' : 'padNext'] = '';
  if (key === 'LB') b.prepend(badge(key));
  else b.append(badge(key));
  return b;
}

export class Screens {
  private current: HTMLElement | null = null;
  /** da chiamare quando la schermata se ne va (gli ascoltatori messi fuori da lei, come i tasti dell'annuncio) */
  private offScreen: (() => void) | null = null;

  constructor(
    private root: HTMLElement,
    public lang: Lang,
  ) {}

  get S() {
    return STRINGS[this.lang];
  }

  clear(): void {
    this.offScreen?.();
    this.offScreen = null;
    this.current?.remove();
    this.current = null;
  }

  private show(el: HTMLElement): HTMLElement {
    this.clear();
    this.current = el;
    this.root.appendChild(el);
    return el;
  }

  loading(progress: number): void {
    const pct = Math.round(progress * 100);
    if (this.current?.classList.contains('loading')) {
      this.current.querySelector('.bar i')!.setAttribute('style', `width:${pct}%`);
      return;
    }
    this.show(h('div', { class: 'screen loading' }, h('div', { class: 'bar' }, h('i', { style: `width:${pct}%` }))));
  }

  warning(onDone: () => void): void {
    const S = this.S;
    const el = this.show(
      h('div', { class: 'screen warning fade-in' }, h('h2', {}, S.warningTitle), h('p', {}, S.warning), dualText(h('div', { class: 'muted blink' }), S.pressAny, S.pad.pressAny)),
    );
    const go = () => {
      removeEventListener('keydown', go);
      el.removeEventListener('pointerdown', go);
      onDone();
    };
    addEventListener('keydown', go);
    el.addEventListener('pointerdown', go);
  }

  title(o: { canContinue: boolean; onNew: () => void; onContinue: () => void; onExtraNight: (() => void) | null; onJournal: () => void; onOptions: () => void; onQuit: (() => void) | null }): void {
    const S = this.S;
    const menu = h('div', { class: 'menu' }, button(S.newGame, o.onNew, 'start'));
    if (o.canContinue) menu.append(button(S.continue, o.onContinue));
    if (o.onExtraNight) menu.append(button(S.extraNight, o.onExtraNight));
    menu.append(button(S.extras, o.onJournal), button(S.options, o.onOptions));
    if (o.onQuit) menu.append(button(S.quit, o.onQuit));
    this.show(h('div', { class: 'screen title fade-in' }, h('h1', {}, S.title), menu, h('div', { class: 'build' }, __BUILD__)));
  }

  /**
   * L'annuncio con cui il pescatore ha trovato il lavoro (dopo «Nuova partita»): esce dal buio e si avvicina piano,
   * portando il punto (fx, fy), in frazioni dell'immagine, verso il centro. Un clic, un tasto o un tasto del controller
   * lo saltano (`onSkip`); annuncioOut lo spegne.
   */
  annuncio(a: { src: string; fx: number; fy: number; seconds: number; onSkip: () => void }): void {
    const img = h('img', { src: a.src, alt: '', draggable: 'false' });
    const foglio = h('div', { class: 'foglio' }, img);
    const el = this.show(h('div', { class: 'screen annuncio' }, foglio));
    // da tutta l'immagine a 1,25 volte; il punto fa sei decimi della strada verso il centro, senza mai scoprire i bordi
    const s = 1.25;
    const lim = ((s - 1) / 2) * 100;
    const t = (f: number) => Math.max(-lim, Math.min(lim, (f - 0.5) * (0.4 - s) * 100));
    img.animate([{ transform: 'none' }, { transform: `translate(${t(a.fx)}%, ${t(a.fy)}%) scale(${s})` }], {
      duration: a.seconds * 1000,
      easing: 'cubic-bezier(.3, 0, .7, 1)',
      fill: 'forwards',
    });
    foglio.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 900, easing: 'ease-out', fill: 'both' });
    const skip = (e: Event) => {
      e.preventDefault();
      a.onSkip();
    };
    addEventListener('keydown', skip);
    el.addEventListener('pointerdown', skip);
    this.offScreen = () => removeEventListener('keydown', skip);
  }

  /** L'annuncio si spegne nel buio in `seconds` (da quanto era acceso, se lo si salta mentre compare). */
  annuncioOut(seconds: number): void {
    const f = this.current?.querySelector<HTMLElement>('.foglio');
    if (!f || f.dataset.via) return;
    f.dataset.via = '1';
    const o = Number(getComputedStyle(f).opacity);
    for (const x of f.getAnimations()) x.cancel();
    f.animate([{ opacity: o }, { opacity: 0 }], { duration: seconds * 1000 * Math.max(0.3, o), easing: 'ease-in', fill: 'forwards' });
  }

  intro(night: number, quota: number): void {
    const S = this.S;
    this.show(
      h(
        'div',
        { class: 'screen intro fade-in' },
        h('h2', {}, `${S.night} ${night}`),
        h('div', { class: 'intro-time' }, S.intro.time),
        h('div', { class: 'muted' }, `${S.intro.quota}: ${quota} ${S.intro.fishUnit}`),
      ),
    );
  }

  pause(o: { onResume: () => void; onRestart: () => void; onOptions: () => void; onMenu: () => void }): void {
    const S = this.S;
    this.show(
      h(
        'div',
        { class: 'screen pause' },
        h('h2', {}, S.paused),
        h('div', { class: 'menu' }, backKey(button(S.resume, o.onResume)), button(S.restartNight, o.onRestart), button(S.options, o.onOptions), button(S.menu, o.onMenu, 'back')),
      ),
    );
  }

  /** `lang: false`: senza la lingua (dalla pausa: la notte in corso resterebbe nella lingua di prima). */
  options(opts: Options, o: { onChange: (k: keyof Options | 'lang', v: number | boolean | string) => void; onBack: () => void; fullscreen: (() => void) | null; lang?: boolean }): void {
    const S = this.S;
    const rows = h('div', { class: 'options' });
    const slider = (label: string, key: keyof Options, min: number, max: number, step: number) => {
      const input = h('input', { type: 'range', min: String(min), max: String(max), step: String(step), value: String(opts[key]) });
      input.addEventListener('input', () => o.onChange(key, Number(input.value)));
      rows.append(h('label', {}, h('span', {}, label), input));
    };
    const toggle = (label: string, key: keyof Options) => {
      const b = button(opts[key] ? S.on : S.off, () => {
        const v = !opts[key];
        o.onChange(key, v);
        b.textContent = v ? S.on : S.off;
      });
      rows.append(h('label', {}, h('span', {}, label), b));
    };
    slider(S.volMaster, 'master', 0, 1, 0.05);
    slider(S.volMusic, 'music', 0, 1, 0.05);
    slider(S.volSfx, 'sfx', 0, 1, 0.05);
    slider(S.brightness, 'brightness', 0.5, 1.6, 0.05);
    slider(S.sensitivity, 'sensitivity', 0.4, 2, 0.05);
    toggle(S.subtitles, 'subtitles');
    toggle(S.captionsOption, 'captions');
    toggle(S.reduceFlash, 'reduceFlash');
    toggle(S.fogOption, 'fog');
    toggle(S.tutorialOption, 'tutorial');
    // qualità grafica: sui PC più deboli la scena si disegna a risoluzione ridotta (l'interfaccia resta nitida)
    const steps = [1, 0.75, 0.5];
    const qLabel = (v: number) => S.qualityLevels[Math.max(0, steps.indexOf(v))]!;
    const qb = button(qLabel(opts.quality), () => {
      const v = steps[(Math.max(0, steps.indexOf(opts.quality)) + 1) % steps.length]!;
      o.onChange('quality', v);
      qb.textContent = qLabel(v);
    });
    rows.append(h('label', {}, h('span', {}, S.quality), qb));
    // dimensione dei testi: normale, grande, molto grande
    const sizes = [1, 1.2, 1.4];
    const tLabel = (v: number) => S.textSizes[Math.max(0, sizes.indexOf(v))]!;
    const tb = button(tLabel(opts.textSize), () => {
      const v = sizes[(Math.max(0, sizes.indexOf(opts.textSize)) + 1) % sizes.length]!;
      o.onChange('textSize', v);
      tb.textContent = tLabel(v);
    });
    rows.append(h('label', {}, h('span', {}, S.textSize), tb));
    if (o.lang !== false) {
      // il pulsante passa alla lingua dopo (con due lingue, all'altra)
      const lang = button(LANG_NAMES[this.lang] ?? this.lang, () => o.onChange('lang', LANGS[(LANGS.indexOf(this.lang) + 1) % LANGS.length]!));
      rows.append(h('label', {}, h('span', {}, S.language), lang));
    }
    if (o.fullscreen) {
      const fs = o.fullscreen;
      rows.append(h('label', {}, h('span', {}, S.fullscreen), button('⛶', fs)));
    }
    this.show(h('div', { class: 'screen opts fade-in' }, h('h2', {}, S.optionsTitle), rows, h('div', { class: 'menu' }, backKey(button(S.back, o.onBack, 'back')))));
  }

  /**
   * La notte extra (notte 7): per ognuno dei sette mostri, la Madre e Soggy il livello da 0 (non viene) a 20 (feroce), con − e +,
   * e qualche preimpostazione. onChange a ogni modifica (l'App la salva), onStart per salpare.
   */
  extraNight(levels: ExtraLevels, o: { onChange: (l: ExtraLevels) => void; onStart: (l: ExtraLevels) => void; onBack: () => void }): void {
    const S = this.S;
    const lv: ExtraLevels = { ...levels };
    const grid = h('div', { class: 'extra-grid' });
    const paint: (() => void)[] = [];
    /** la parola sotto il numero: non viene, calmo, come la sua notte, svelto, feroce */
    const word = (n: number) => S.extraLevelNames[n === 0 ? 0 : n < 5 ? 1 : n === 5 ? 2 : n < 15 ? 3 : 4]!;
    const set = (who: keyof ExtraLevels, n: number) => {
      lv[who] = clampLevel(n);
      for (const p of paint) p();
      o.onChange({ ...lv });
    };
    for (const who of EXTRA_IDS) {
      const num = h('b', { class: 'lv' });
      const what = h('div', { class: 'lv-word' });
      const minus = button('−', () => set(who, lv[who] - 1));
      const plus = button('+', () => set(who, lv[who] + 1));
      minus.classList.add('step');
      plus.classList.add('step');
      minus.setAttribute('aria-label', `${who} −`);
      plus.setAttribute('aria-label', `${who} +`);
      const card = h(
        'div',
        { class: 'extra-card', 'data-who': who },
        h('div', { class: 'who' }, who === 'mother' ? S.extraMother : who === 'foxy' ? FOXY_NAME : who[0]!.toUpperCase() + who.slice(1)),
        h('div', { class: 'rule' }, S.extraRules[who]),
        h('div', { class: 'ctl' }, minus, num, plus),
        what,
      );
      // la rotella sulla scheda alza e abbassa il livello
      card.addEventListener('wheel', (e) => {
        e.preventDefault();
        set(who, lv[who] + (e.deltaY < 0 ? 1 : -1));
      });
      paint.push(() => {
        num.textContent = String(lv[who]);
        what.textContent = word(lv[who]);
        card.classList.toggle('off', lv[who] === 0);
        card.style.setProperty('--fury', String(lv[who] / EXTRA_MAX));
        minus.disabled = lv[who] === 0;
        plus.disabled = lv[who] === EXTRA_MAX;
      });
      grid.append(card);
    }
    const presets = h('div', { class: 'extra-presets' });
    for (const p of EXTRA_PRESETS) {
      presets.append(
        button(S.extraPresets[p.id as keyof typeof S.extraPresets] ?? p.id, () => {
          Object.assign(lv, p.levels);
          for (const f of paint) f();
          o.onChange({ ...lv });
        }),
      );
    }
    for (const p of paint) p();
    this.show(
      h(
        'div',
        { class: 'screen extra-screen fade-in' },
        h('h2', {}, S.extraNight),
        h('p', {}, S.extraHelp),
        grid,
        presets,
        h('div', { class: 'menu' }, button(S.extraStart, () => o.onStart({ ...lv }), 'start'), backKey(button(S.back, o.onBack, 'back'))),
      ),
    );
  }

  /**
   * I titoli di coda, dopo i finali della notte 6: su un fondo nero salgono piano il titolo, «Un gioco di Ettore» e il
   * ringraziamento (una riga sola, scelta dell'utente del 12 ottobre sera); poi `onDone`. Esc, Invio, Spazio o un
   * clic li saltano.
   * La durata segue la lunghezza (circa 2,6 s a riga), così coi nomi veri resta lo stesso passo.
   */
  credits(onDone: () => void): void {
    const S = this.S;
    const roll = h('div', { class: 'credits-roll' }, h('h1', {}, S.creditsTitle));
    for (const [role, name] of S.credits) roll.append(h('div', { class: 'credit' }, h('span', {}, role), h('b', {}, name)));
    roll.append(h('p', { class: 'credits-end' }, S.creditsEnd));
    const rows = S.credits.length + 3;
    const secs = Math.max(18, rows * 2.6);
    roll.style.animationDuration = `${secs}s`;
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      removeEventListener('keydown', onKey);
      onDone();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        finish();
      }
    };
    addEventListener('keydown', onKey);
    roll.addEventListener('animationend', finish);
    const el = h('div', { class: 'screen credits after-ending' }, roll, h('p', { class: 'credits-skip muted' }, S.creditsSkip));
    el.addEventListener('click', finish);
    this.show(el);
  }

  journal(found: string[], onBack: () => void, drawings: { all: string[]; found: string[] } = { all: [], found: [] }): void {
    const S = this.S;
    const list = h('div', { class: 'journal' });
    if (drawings.all.length) {
      const grid = h('div', { class: 'disegni' });
      for (const id of drawings.all) {
        const name = S.drawings.names[id] ?? id;
        if (drawings.found.includes(id)) grid.append(drawingFigure(id, name, this.lang, 'disegno piccolo'));
        else grid.append(h('figure', { class: 'disegno piccolo locked' }, h('div', { class: 'vuoto' }, '?'), h('figcaption', {}, S.drawings.locked)));
      }
      list.append(h('h3', { class: 'sezione' }, S.drawings.title), grid);
    }
    const items = LORE.filter((l) => found.includes(l.id));
    if (items.length === 0) list.append(h('p', { class: 'empty' }, S.journalEmpty));
    for (const l of LORE) {
      const t = LORE_TEXT[this.lang][l.id];
      if (!t) continue;
      if (found.includes(l.id)) list.append(h('div', { class: 'entry' }, h('h3', {}, t.title), h('p', {}, t.body)));
      else list.append(h('div', { class: 'entry locked' }, h('h3', {}, S.journalLocked)));
    }
    this.show(h('div', { class: 'screen journal-screen fade-in' }, h('h2', {}, S.journalTitle), list, h('div', { class: 'menu' }, backKey(button(S.back, onBack, 'back')))));
  }

  /** Extra: il Diario degli oggetti ripescati e il Catalogo dei pesci. */
  extras(o: { onJournal: () => void; onCatalog: () => void; onBack: () => void }): void {
    const S = this.S;
    this.show(
      h('div', { class: 'screen title fade-in' }, h('h2', {}, S.extras), h('div', { class: 'menu' }, button(S.journalTitle, o.onJournal), button(S.catalogTitle, o.onCatalog), backKey(button(S.back, o.onBack, 'back')))),
    );
  }

  /**
   * Il Catalogo è un libro aperto sul banco della barca. Prima doppia pagina: il frontespizio e l'indice; poi
   * una doppia pagina per famiglia: a sinistra le foto delle specie attaccate col nastro (le specie non ancora
   * prese sono sagome a matita), a destra la scheda della specie scelta. Le pagine si girano davvero
   * (frecce, angoli, segnalibri). revealAll mostra tutte le voci (per le prove).
   */
  catalog(o: { caught: Record<string, CatalogEntry>; images: Record<string, string>; revealAll: boolean; onBack: () => void }): void {
    const S = this.S;
    const L = this.lang;
    const families: FishFamily[] = ['skeletal', 'zombie', 'glitch', 'corrupt', 'bleeding'];
    const known = (f: FishSpecies) => !!o.caught[f.id] || o.revealAll;
    const got = FISH.filter((f) => o.caught[f.id]).length;
    const ofFam = (fam: FishFamily) => FISH.filter((f) => f.family === fam);
    const last = families.length;
    const A = 'assets/img/catalogo/';
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

    const screen = h('div', { class: 'screen book-screen fade-in' });
    // indirizzi assoluti: un url() relativo dentro una variabile CSS si risolverebbe rispetto al foglio di stile
    const abs = (f: string) => `url("${new URL(A + f, document.baseURI).href}")`;
    screen.style.setProperty('--sfondo', abs('sfondo.webp'));
    screen.style.setProperty('--carta', abs('carta.webp'));
    screen.style.setProperty('--cuoio', abs('cuoio.webp'));
    const book = h('div', { class: 'book' });
    const pages = h('div', { class: 'book-pages' });
    const left = h('div', { class: 'page left' });
    const right = h('div', { class: 'page right' });
    const prevCorner = h('div', { class: 'corner prev' });
    const nextCorner = h('div', { class: 'corner next' });
    pages.append(left, right, prevCorner, nextCorner, h('div', { class: 'book-light' }));
    const tabs = h('div', { class: 'book-tabs' });
    book.append(h('div', { class: 'book-cover' }), tabs, pages);

    let spread = 0;
    let busy = false;
    const sel: Partial<Record<FishFamily, string>> = {};

    // rotazione delle foto: sempre la stessa per la stessa specie
    const tilt = (id: string, max: number) => {
      let x = 0;
      for (const ch of id) x = (x * 31 + ch.charCodeAt(0)) % 997;
      return ((x / 996) * 2 - 1) * max;
    };
    const pageNo = (n: number) => h('div', { class: 'page-no' }, `${S.pageAbbr} ${n}`);
    const snap = (f: FishSpecies, big = false) => {
      const k = known(f);
      const img = o.images[f.id];
      const el = h('figure', { class: `snap${k ? '' : ' unknown'}${big ? ' big' : ''}` });
      el.style.setProperty('--r', `${tilt(f.id, big ? 1.6 : 3.5).toFixed(2)}deg`);
      const ph = h('div', { class: 'ph' });
      if (k && img) ph.append(h('img', { src: img, alt: '' }));
      else {
        const sh = h('span', { class: 'shape' });
        sh.innerHTML = FISH_SHAPE;
        ph.append(sh);
      }
      el.append(ph);
      if (!big) el.append(h('figcaption', {}, k ? f.name[L] : S.unknownFish));
      return el;
    };
    const kgText = (x: number) => decimal(x < 1 ? x.toFixed(2) : x.toFixed(1), L);
    const whenText = (f: FishSpecies) => {
      const w = f.when;
      if (!w) return S.when.always;
      const parts: string[] = [];
      if (w.night) parts.push(S.when.night.replace('{n}', String(w.night)));
      if (w.lamp === 'dark') parts.push(S.when.dark);
      if (w.lamp === 'bright') parts.push(S.when.bright);
      if (w.from != null) parts.push(S.when.from.replace('{h}', `${w.from}:00`));
      if (w.near === 'any') parts.push(S.when.nearAny);
      else if (w.near) parts.push(S.when.near.replace('{who}', w.near[0]!.toUpperCase() + w.near.slice(1)));
      return parts.join(', ');
    };

    const renderLeft = (k: number): HTMLElement[] => {
      if (k === 0) {
        return [
          h('div', { class: 'title-page' },
            h('h2', {}, S.catalogTitle),
            h('div', { class: 'rule' }),
            h('p', { class: 'progress' }, `${S.bookFound}: ${got} ${S.bookOf} ${FISH.length}`),
            h('p', { class: 'hint' }, S.catalogHint)),
          pageNo(1),
        ];
      }
      const fam = families[k - 1]!;
      const list = ofFam(fam);
      const grid = h('div', { class: 'snaps' });
      for (const f of list) {
        const el = snap(f);
        if (known(f)) {
          el.classList.add('can');
          // col controller le foto si scelgono come i pulsanti
          el.tabIndex = -1;
          el.dataset.padFocus = '';
          if (sel[fam] === f.id) el.classList.add('on');
          el.addEventListener('click', () => {
            sel[fam] = f.id;
            for (const x of Array.from(left.querySelectorAll('.snap.on'))) x.classList.remove('on');
            el.classList.add('on');
            right.replaceChildren(...renderRight(spread));
            uiSound('ui_click');
          });
        }
        grid.append(el);
      }
      return [
        h('header', { class: `fam-head fam-${fam}` },
          h('h3', {}, S.familyPlural[fam]),
          h('p', {}, S.familyText[fam]),
          h('div', { class: 'count' }, `${list.filter((f) => o.caught[f.id]).length} / ${list.length}`)),
        grid,
        pageNo(2 * k + 1),
      ];
    };

    const renderRight = (k: number): HTMLElement[] => {
      if (k === 0) {
        const idx = h('div', { class: 'index' }, h('h3', {}, S.bookIndex));
        families.forEach((fam, i) => {
          const list = ofFam(fam);
          const row = h('button', { type: 'button', class: `row fam-${fam}` },
            h('span', { class: 'name' }, S.familyPlural[fam]),
            h('span', { class: 'dots' }),
            h('span', { class: 'num' }, `${list.filter((f) => o.caught[f.id]).length} / ${list.length}`),
            h('span', { class: 'pg' }, String(2 * (i + 1) + 1)));
          row.addEventListener('click', () => turn(i + 1));
          idx.append(row, h('p', { class: 'fam-text' }, S.familyText[fam]));
        });
        return [idx, pageNo(2)];
      }
      const fam = families[k - 1]!;
      const list = ofFam(fam);
      const id = sel[fam] ?? list.find(known)?.id;
      if (!id) return [h('p', { class: 'note' }, S.bookNone), pageNo(2 * k + 2)];
      const f = FISH_BY_ID[id]!;
      const c = o.caught[f.id];
      return [
        snap(f, true),
        h('h3', { class: 'fish-name' }, f.name[L]),
        h('div', { class: 'real' }, `${S.inspiredBy}: ${f.real[L]} · `, h('i', {}, f.real.sci)),
        h('div', { class: 'stamps' },
          h('span', { class: `stamp fam-${f.family}` }, S.families[f.family]),
          h('span', { class: `stamp rar-${f.rarity}` }, S.rarities[f.rarity])),
        h('p', { class: 'desc' }, f.desc[L] ?? f.desc.it),
        h('dl', { class: 'facts' },
          h('dt', {}, S.bookWeight), h('dd', {}, `${kgText(f.kg[0])}–${kgText(f.kg[1])} ${S.kg}`),
          h('dt', {}, S.bookPull), h('dd', {}, S.pull[f.pull]),
          h('dt', {}, S.bookWhen), h('dd', {}, whenText(f))),
        h('div', { class: 'log' }, c ? `${S.timesCaught}: ${c.count}    ${S.record}: ${kgText(c.bestKg)} ${S.kg}` : '—'),
        pageNo(2 * k + 2),
      ];
    };

    const paintChrome = () => {
      for (const t of Array.from(tabs.children)) t.classList.toggle('on', Number((t as HTMLElement).dataset.k) === spread);
      prevCorner.hidden = spread === 0;
      nextCorner.hidden = spread === last;
      prevBtn.disabled = spread === 0;
      nextBtn.disabled = spread === last;
    };

    const turn = (to: number) => {
      if (busy || to === spread || to < 0 || to > last) return;
      uiSound('ui_page');
      const fwd = to > spread;
      const nl = renderLeft(to);
      const nr = renderRight(to);
      spread = to;
      paintChrome();
      if (reduce) {
        left.replaceChildren(...nl);
        right.replaceChildren(...nr);
        return;
      }
      busy = true;
      // la pagina che gira: davanti la pagina di adesso, dietro quella che arriva
      const leaf = h('div', { class: `leaf ${fwd ? 'fwd' : 'bwd'}` });
      const front = h('div', { class: `page face ${fwd ? 'right' : 'left'}` });
      const back = h('div', { class: `page face back ${fwd ? 'left' : 'right'}` });
      front.append(...Array.from((fwd ? right : left).childNodes).map((n) => n.cloneNode(true)));
      back.append(...(fwd ? nl : nr));
      leaf.append(front, back);
      (fwd ? right : left).replaceChildren(...(fwd ? nr : nl));
      pages.append(leaf);
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        (fwd ? left : right).replaceChildren(...Array.from(back.childNodes));
        leaf.remove();
        busy = false;
      };
      void leaf.offsetWidth; // lo stato di partenza va calcolato prima, se no la transizione non parte
      leaf.classList.add('go');
      leaf.addEventListener('transitionend', finish, { once: true });
      setTimeout(finish, 1100);
    };

    // segnalibri: indice e famiglie
    const tabLabels = [S.bookIndex, ...families.map((f) => S.familyPlural[f])];
    tabLabels.forEach((label, k) => {
      const t = h('button', { type: 'button', class: `tab${k ? ` fam-${families[k - 1]}` : ' idx'}` }, label);
      t.dataset.k = String(k);
      t.addEventListener('click', () => turn(k));
      tabs.append(t);
    });
    prevCorner.addEventListener('click', () => turn(spread - 1));
    nextCorner.addEventListener('click', () => turn(spread + 1));
    const prevBtn = pageKey(button('‹', () => turn(spread - 1)), 'LB');
    const nextBtn = pageKey(button('›', () => turn(spread + 1)), 'RB');
    prevBtn.classList.add('turnbtn');
    nextBtn.classList.add('turnbtn');
    const nav = h('div', { class: 'book-nav' }, prevBtn, dualText(h('span', { class: 'hint' }), S.bookTurn, S.pad.bookTurn), nextBtn, backKey(button(S.bookClose, o.onBack, 'back')));

    left.append(...renderLeft(0));
    right.append(...renderRight(0));
    screen.append(book, nav);
    this.show(screen);
    paintChrome();

    const onKey = (e: KeyboardEvent) => {
      if (!screen.isConnected) {
        document.removeEventListener('keydown', onKey);
        return;
      }
      if (e.key === 'ArrowRight' || e.key === 'PageDown') turn(spread + 1);
      else if (e.key === 'ArrowLeft' || e.key === 'PageUp') turn(spread - 1);
      else if (e.key === 'Escape') {
        document.removeEventListener('keydown', onKey);
        uiSound('ui_back');
        o.onBack();
      }
    };
    document.addEventListener('keydown', onKey);
  }

  /** L'alba ripresa da «Continua» (immersioni): le sei passate, i pesci avanzati, scendere o andare alla notte dopo. */
  dawn(o: { spare: number; drawing?: string | null; onDive: () => void; onNext: () => void; onMenu: () => void }): void {
    const S = this.S;
    const stats = h('div', { class: 'stats' }, h('div', {}, h('span', {}, S.results.spare), h('b', {}, String(o.spare))));
    const menu = h('div', { class: 'menu' }, diveButton(S.dive.descend, o.onDive), button(S.nextNight, o.onNext, 'start'), button(S.menu, o.onMenu, 'back'));
    const parts: Node[] = [h('h2', {}, `${S.sixAm} · ${S.survived}`), stats, menu];
    this.show(this.withDrawing('screen dawn fade-in', parts, o.drawing));
  }

  /** La schermata con accanto il disegno dell'alba (se c'è): a sinistra il foglio, a destra il resto. */
  private withDrawing(cls: string, parts: Node[], drawing?: string | null): HTMLElement {
    if (!drawing) return h('div', { class: cls }, ...parts);
    const S = this.S;
    const name = S.drawings.names[drawing] ?? drawing;
    return h('div', { class: `${cls} alba-disegno` }, drawingFigure(drawing, `${S.drawings.found} «${name}»`, this.lang), h('div', { class: 'colonna' }, ...parts));
  }

  /** Statica tra il jumpscare e il game over. */
  /** Segnale perso dopo il jumpscare: la neve la disegna la scena (WebGL), sopra non c'è niente. */
  static(): void {
    this.clear();
  }

  results(o: { won: boolean; text: string; caught: number; fed: number; lore: number; demoEnd: boolean; onNext?: (() => void) | null; onWishlist?: (() => void) | null; onRetry: () => void; onMenu: () => void;
    /** finita l'ultima notte, si è aperta la notte extra: al posto della fine della demo, il pulsante per giocarla */
    onExtra?: (() => void) | null;
    /** dopo un finale (la cinematica o i titoli di coda, che finiscono nel buio): il fondo nero da subito, se no nella
     *  dissolvenza si rivedrebbe la barca di notte */
    afterEnding?: boolean;
    /** pesci avanzati oltre la quota (immersioni) */
    spare?: number;
    /** scendere con le bombole prima della notte dopo (l'immersione è facoltativa) */
    onDive?: (() => void) | null;
    /** il disegno a pastelli trovato all'alba (disegni.ts) */
    drawing?: string | null }): void {
    const S = this.S;
    const stats = h(
      'div',
      { class: 'stats' },
      h('div', {}, h('span', {}, S.results.caught), h('b', {}, String(o.caught))),
      h('div', {}, h('span', {}, S.results.fed), h('b', {}, String(o.fed))),
      h('div', {}, h('span', {}, S.results.lore), h('b', {}, String(o.lore))),
    );
    if (o.won && o.spare !== undefined) stats.append(h('div', {}, h('span', {}, S.results.spare), h('b', {}, String(o.spare))));
    const menu = h('div', { class: 'menu' });
    if (!o.won) menu.append(button(S.retry, o.onRetry, 'start'));
    if (o.won && o.onDive) menu.append(diveButton(S.dive.descend, o.onDive));
    if (o.won && o.onNext) menu.append(button(S.nextNight, o.onNext, 'start'));
    if (o.won && o.onExtra) menu.append(button(S.extraNight, o.onExtra, 'start'));
    if (o.demoEnd && !o.onExtra && o.onWishlist) menu.append(button(S.wishlist, o.onWishlist, 'start'));
    menu.append(button(S.menu, o.onMenu, 'back'));
    const parts: Node[] = [h('h2', {}, o.won ? `${S.sixAm} · ${S.survived}` : S.deathTitle), h('p', {}, o.text), stats];
    if (o.demoEnd) parts.push(h('p', { class: 'muted' }, o.onExtra ? S.extraOpened : S.demoEnd));
    parts.push(menu);
    this.show(this.withDrawing(`screen ${o.won ? 'dawn' : 'death'} ${o.afterEnding ? 'after-ending' : 'fade-in'}`, parts, o.won ? o.drawing : null));
  }
}
