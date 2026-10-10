/** Schermate in DOM sopra la scena: avvertenza, titolo, intro, pausa, opzioni, diario, alba, game over. */
import { FISH, FISH_BY_ID, type FishFamily, type FishSpecies } from '../game/catalog.ts';
import { LORE } from '../game/config.ts';
import { LORE_TEXT, STRINGS, type Lang } from '../i18n.ts';
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

export class Screens {
  private current: HTMLElement | null = null;

  constructor(
    private root: HTMLElement,
    public lang: Lang,
  ) {}

  get S() {
    return STRINGS[this.lang];
  }

  clear(): void {
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
      h('div', { class: 'screen warning fade-in' }, h('h2', {}, S.warningTitle), h('p', {}, S.warning), h('div', { class: 'muted blink' }, S.pressAny)),
    );
    const go = () => {
      removeEventListener('keydown', go);
      el.removeEventListener('pointerdown', go);
      onDone();
    };
    addEventListener('keydown', go);
    el.addEventListener('pointerdown', go);
  }

  title(o: { canContinue: boolean; onNew: () => void; onContinue: () => void; onJournal: () => void; onOptions: () => void; onQuit: (() => void) | null }): void {
    const S = this.S;
    const menu = h('div', { class: 'menu' }, button(S.newGame, o.onNew, 'start'));
    if (o.canContinue) menu.append(button(S.continue, o.onContinue));
    menu.append(button(S.extras, o.onJournal), button(S.options, o.onOptions));
    if (o.onQuit) menu.append(button(S.quit, o.onQuit));
    this.show(h('div', { class: 'screen title fade-in' }, h('h1', {}, S.title), menu));
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

  pause(o: { onResume: () => void; onOptions: () => void; onMenu: () => void }): void {
    const S = this.S;
    this.show(h('div', { class: 'screen pause' }, h('h2', {}, S.paused), h('div', { class: 'menu' }, button(S.resume, o.onResume), button(S.options, o.onOptions), button(S.menu, o.onMenu, 'back'))));
  }

  options(opts: Options, o: { onChange: (k: keyof Options | 'lang', v: number | boolean | string) => void; onBack: () => void; fullscreen: (() => void) | null }): void {
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
    toggle(S.reduceFlash, 'reduceFlash');
    const lang = button(this.lang === 'it' ? 'Italiano' : 'English', () => o.onChange('lang', this.lang === 'it' ? 'en' : 'it'));
    rows.append(h('label', {}, h('span', {}, S.language), lang));
    if (o.fullscreen) {
      const fs = o.fullscreen;
      rows.append(h('label', {}, h('span', {}, S.fullscreen), button('⛶', fs)));
    }
    this.show(h('div', { class: 'screen opts fade-in' }, h('h2', {}, S.optionsTitle), rows, h('div', { class: 'menu' }, button(S.back, o.onBack, 'back'))));
  }

  journal(found: string[], onBack: () => void): void {
    const S = this.S;
    const list = h('div', { class: 'journal' });
    const items = LORE.filter((l) => found.includes(l.id));
    if (items.length === 0) list.append(h('p', { class: 'empty' }, S.journalEmpty));
    for (const l of LORE) {
      const t = LORE_TEXT[this.lang][l.id];
      if (!t) continue;
      if (found.includes(l.id)) list.append(h('div', { class: 'entry' }, h('h3', {}, t.title), h('p', {}, t.body)));
      else list.append(h('div', { class: 'entry locked' }, h('h3', {}, S.journalLocked)));
    }
    this.show(h('div', { class: 'screen journal-screen fade-in' }, h('h2', {}, S.journalTitle), list, h('div', { class: 'menu' }, button(S.back, onBack, 'back'))));
  }

  /** Extra: il Diario degli oggetti ripescati e il Catalogo dei pesci. */
  extras(o: { onJournal: () => void; onCatalog: () => void; onBack: () => void }): void {
    const S = this.S;
    this.show(
      h('div', { class: 'screen title fade-in' }, h('h2', {}, S.extras), h('div', { class: 'menu' }, button(S.journalTitle, o.onJournal), button(S.catalogTitle, o.onCatalog), button(S.back, o.onBack, 'back'))),
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
    const kgText = (x: number) => (x < 1 ? x.toFixed(2) : x.toFixed(1)).replace('.', L === 'it' ? ',' : '.');
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
    const prevBtn = button('‹', () => turn(spread - 1));
    const nextBtn = button('›', () => turn(spread + 1));
    prevBtn.classList.add('turnbtn');
    nextBtn.classList.add('turnbtn');
    const nav = h('div', { class: 'book-nav' }, prevBtn, h('span', { class: 'hint' }, S.bookTurn), nextBtn, button(S.bookClose, o.onBack, 'back'));

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

  /** Statica tra il jumpscare e il game over. */
  static(): void {
    this.show(h('div', { class: 'screen static' }));
  }

  results(o: { won: boolean; text: string; caught: number; fed: number; lore: number; demoEnd: boolean; onRetry: () => void; onMenu: () => void }): void {
    const S = this.S;
    const stats = h(
      'div',
      { class: 'stats' },
      h('div', {}, h('span', {}, S.results.caught), h('b', {}, String(o.caught))),
      h('div', {}, h('span', {}, S.results.fed), h('b', {}, String(o.fed))),
      h('div', {}, h('span', {}, S.results.lore), h('b', {}, String(o.lore))),
    );
    const menu = h('div', { class: 'menu' });
    if (!o.won) menu.append(button(S.retry, o.onRetry, 'start'));
    menu.append(button(S.menu, o.onMenu, 'back'));
    const el = h('div', { class: `screen ${o.won ? 'dawn' : 'death'} fade-in` }, h('h2', {}, o.won ? `${S.sixAm} · ${S.survived}` : S.deathTitle), h('p', {}, o.text), stats);
    if (o.demoEnd) el.append(h('p', { class: 'muted' }, S.demoEnd));
    el.append(menu);
    this.show(el);
  }
}
