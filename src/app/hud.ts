/** HUD in DOM: orologio, secchio/quota, lampara, suggerimenti, sottotitoli della radio, avvisi. */
import type { Lang } from '../i18n.ts';
import { STRINGS } from '../i18n.ts';

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, parent: HTMLElement, html = ''): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  e.className = cls;
  if (html) e.innerHTML = html;
  parent.appendChild(e);
  return e;
}

export class Hud {
  readonly root: HTMLDivElement;
  private nightEl: HTMLDivElement;
  private timeEl: HTMLDivElement;
  private quotaEl: HTMLDivElement;
  private lampEl: HTMLDivElement;
  private hintEl: HTMLDivElement;
  private subEl: HTMLDivElement;
  private toastEl: HTMLDivElement;
  private capEl: HTMLDivElement;
  private capTimer = 0;
  private hoverEl: HTMLDivElement;
  readonly turnEl: HTMLDivElement;
  private reelEl: HTMLDivElement;
  private reelBar: HTMLDivElement;
  private toastTimer = 0;
  private cardEl: HTMLDivElement;
  private cardTimer = 0;
  private lastHint = '';

  constructor(
    parent: HTMLElement,
    private lang: Lang,
  ) {
    const S = STRINGS[lang];
    this.root = el('div', 'hud', parent);
    const clock = el('div', 'hud-clock', this.root);
    this.nightEl = el('div', 'night', clock);
    this.timeEl = el('div', 'time', clock);
    const q = el('div', 'hud-quota', this.root);
    el('div', 'label', q, S.quota);
    this.quotaEl = el('div', 'count', q);
    this.lampEl = el('div', 'hud-lamp', this.root);
    this.hintEl = el('div', 'hud-hint', this.root);
    this.subEl = el('div', 'hud-sub', this.root);
    this.toastEl = el('div', 'hud-toast', this.root);
    this.cardEl = el('div', 'hud-card', this.root);
    this.capEl = el('div', 'hud-cap', this.root);
    this.hoverEl = el('div', 'hud-hover', this.root);
    this.turnEl = el('div', 'hud-turn', this.root, S.turnBar);
    this.reelEl = el('div', 'hud-reel', this.root);
    this.reelBar = el('div', 'bar', this.reelEl);
    el('div', 'zone', this.reelEl);
  }

  setClock(night: number, hour: number, minutes: number): void {
    const S = STRINGS[this.lang];
    this.nightEl.textContent = `${S.night} ${night}`;
    const h = hour === 0 ? 12 : hour;
    const mm = String(Math.floor(minutes / 10) * 10).padStart(2, '0');
    this.timeEl.textContent = this.lang === 'en' ? `${h}:${mm} ${S.am}` : `${String(hour).padStart(2, '0')}:${mm}`;
  }

  setQuota(fish: number, quota: number): void {
    this.quotaEl.textContent = `${fish} / ${quota}`;
    this.quotaEl.classList.toggle('ok', fish >= quota);
  }

  setLamp(level: number): void {
    const S = STRINGS[this.lang];
    this.lampEl.innerHTML = `${S.lamp} ` + [0, 1].map((i) => `<i class="${level > i ? 'on' : ''}"></i>`).join('');
  }

  hint(text: string): void {
    if (text === this.lastHint) return;
    this.lastHint = text;
    if (text) this.hintEl.textContent = text;
    this.hintEl.classList.toggle('show', !!text);
  }

  subtitle(who: string, text: string): void {
    if (text) this.subEl.innerHTML = `<span class="who">${who}</span>${text}`;
    this.subEl.classList.toggle('show', !!text);
  }

  toast(big: string, small: string, seconds = 2.6): void {
    this.toastEl.innerHTML = `<div class="small">${small}</div><div class="big">${big}</div>`;
    this.toastEl.classList.add('show');
    this.toastTimer = seconds;
  }

  /** La scheda del pesce appena preso: figura, nome, famiglia e rarità, peso, la riga del Catalogo. */
  catchCard(o: { img: string | null; name: string; meta: string; kg: string; desc: string; family: string; isNew: string | null }, seconds = 5): void {
    const c = this.cardEl;
    c.replaceChildren();
    c.className = `hud-card fam-${o.family}`;
    if (o.isNew) el('div', 'new', c, '').textContent = o.isNew;
    if (o.img) {
      const im = el('img', 'fish', c);
      im.src = o.img;
      im.alt = '';
    }
    el('div', 'name', c).textContent = o.name;
    el('div', 'meta', c).textContent = `${o.meta} · ${o.kg}`;
    el('div', 'desc', c).textContent = o.desc;
    void c.offsetWidth;
    c.classList.add('show');
    this.cardTimer = seconds;
  }

  /** Didascalia di un suono (per chi gioca senza audio): sparisce da sola. */
  caption(text: string, seconds = 2.4): void {
    this.capEl.textContent = text;
    this.capEl.classList.add('show');
    this.capTimer = seconds;
  }

  hover(text: string, x: number, y: number): void {
    this.hoverEl.textContent = text;
    this.hoverEl.style.left = `${x}px`;
    this.hoverEl.style.top = `${y}px`;
    this.hoverEl.classList.toggle('show', !!text);
  }

  showTurn(show: boolean): void {
    this.turnEl.classList.toggle('show', show);
  }

  /** strain 0..1: la tensione è piena e il filo sta per spezzarsi (la barra trema di rosso). */
  reel(show: boolean, tension: number, progress: number, strain = 0): void {
    this.reelEl.classList.toggle('show', show);
    if (show) {
      this.reelBar.style.width = `${Math.round(Math.min(1, tension) * 100)}%`;
      this.reelBar.style.background = tension > 0.8 ? 'var(--blood)' : tension < 0.12 ? 'var(--dim)' : 'var(--amber)';
      this.reelEl.style.borderColor = strain > 0 ? 'var(--blood)' : `rgba(233,226,208,${0.3 + 0.5 * progress})`;
      // a tensione piena la barra trema, sempre più forte finché il filo non si spezza
      const a = strain > 0 ? 1.5 + 3.5 * strain : 0;
      this.reelEl.style.transform = a ? `translate(calc(-50% + ${((Math.random() * 2 - 1) * a).toFixed(1)}px), ${((Math.random() * 2 - 1) * a * 0.6).toFixed(1)}px)` : '';
      this.reelEl.style.boxShadow = strain > 0 ? `0 0 ${Math.round(6 + 12 * strain)}px rgba(200,30,20,${(0.4 + 0.5 * strain).toFixed(2)})` : '';
    }
  }

  update(dt: number): void {
    if (this.toastTimer > 0) {
      this.toastTimer -= dt;
      if (this.toastTimer <= 0) this.toastEl.classList.remove('show');
    }
    if (this.capTimer > 0) {
      this.capTimer -= dt;
      if (this.capTimer <= 0) this.capEl.classList.remove('show');
    }
    if (this.cardTimer > 0) {
      this.cardTimer -= dt;
      if (this.cardTimer <= 0) this.cardEl.classList.remove('show');
    }
  }

  setVisible(v: boolean): void {
    this.root.style.display = v ? '' : 'none';
  }

  destroy(): void {
    this.root.remove();
  }
}
