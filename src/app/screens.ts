/** Schermate in DOM sopra la scena: avvertenza, titolo, intro, pausa, opzioni, diario, alba, game over. */
import { LORE } from '../game/config.ts';
import { LORE_TEXT, STRINGS, type Lang } from '../i18n.ts';
import type { Options } from './save.ts';

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Record<string, string> = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else e.setAttribute(k, v);
  }
  for (const k of kids) e.append(k);
  return e;
}

function button(label: string, onClick: () => void): HTMLButtonElement {
  const b = h('button', { type: 'button' }, label);
  b.addEventListener('click', (e) => {
    e.stopPropagation();
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
    const menu = h('div', { class: 'menu' }, button(S.newGame, o.onNew));
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
    this.show(h('div', { class: 'screen pause' }, h('h2', {}, S.paused), h('div', { class: 'menu' }, button(S.resume, o.onResume), button(S.options, o.onOptions), button(S.menu, o.onMenu))));
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
    this.show(h('div', { class: 'screen opts fade-in' }, h('h2', {}, S.optionsTitle), rows, h('div', { class: 'menu' }, button(S.back, o.onBack))));
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
    this.show(h('div', { class: 'screen journal-screen fade-in' }, h('h2', {}, S.journalTitle), list, h('div', { class: 'menu' }, button(S.back, onBack))));
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
    if (!o.won) menu.append(button(S.retry, o.onRetry));
    menu.append(button(S.menu, o.onMenu));
    const el = h('div', { class: `screen ${o.won ? 'dawn' : 'death'} fade-in` }, h('h2', {}, o.won ? `${S.sixAm} · ${S.survived}` : S.deathTitle), h('p', {}, o.text), stats);
    if (o.demoEnd) el.append(h('p', { class: 'muted' }, S.demoEnd));
    el.append(menu);
    this.show(el);
  }
}
