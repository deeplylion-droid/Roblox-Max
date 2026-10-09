/**
 * Il gioco intero: avvertenza → titolo → intro della notte → notte → alba o game over.
 * Tiene il salvataggio, le opzioni e lo sfondo animato dei menu (la scena dalla barca).
 */
import type { AudioEngine, Voice } from '../engine/audio.ts';
import { NIGHTS, type MonsterId } from '../game/config.ts';
import { STRINGS, type Lang } from '../i18n.ts';
import { Night, type NightAssets, type NightEnd } from './night.ts';
import { writeSave, type Options, type SaveData } from './save.ts';
import { Screens, setUiSound } from './screens.ts';
import type { Sfx } from './sfx.ts';
import type { Stage } from './stage.ts';

type Mode = 'warning' | 'title' | 'intro' | 'night' | 'paused' | 'static' | 'end';

const isElectron = navigator.userAgent.includes('Electron');

export class App {
  private mode: Mode = 'warning';
  private night: Night | null = null;
  readonly screens: Screens;
  private timer = 0;
  private lang: Lang;

  constructor(
    private stage: Stage,
    private audio: AudioEngine,
    private sfx: Sfx,
    private canvas: HTMLCanvasElement,
    private ui: HTMLElement,
    private assets: NightAssets,
    private save: SaveData,
    lang: Lang,
  ) {
    this.lang = lang;
    this.screens = new Screens(ui, lang);
    this.applyOptions();
    addEventListener('blur', () => {
      if (this.mode === 'night') this.pause();
    });
  }

  get S() {
    return STRINGS[this.lang];
  }

  begin(): void {
    this.mode = 'warning';
    this.screens.warning(() => {
      void this.audio.start().then(() => {
        this.applyOptions();
        setUiSound((id) => this.audio.play(id));
        if (this.mode === 'title') this.titleMusic(true);
      });
      this.title();
    });
  }

  // ───────────────────────── schermate ─────────────────────────

  /** La ninna nanna della Madre al carillon, nel menu (si avvia solo se non suona già). */
  private titleMusic(on: boolean): void {
    if (on && !this.music) this.music = this.audio.play('mus_title', { loop: true, fadeIn: 2.5 });
    if (!on && this.music) {
      this.music.stop(1.5);
      this.music = null;
    }
  }

  private title(): void {
    this.mode = 'title';
    this.titleMusic(true);
    this.stage.lampTarget = 1;
    this.stage.view.hfov = 90;
    this.screens.title({
      canContinue: false,
      onNew: () => this.intro(),
      onContinue: () => this.intro(),
      onJournal: () => this.extras(),
      onOptions: () => this.options(() => this.title()),
      onQuit: isElectron ? () => window.close() : null,
    });
  }

  private extras(): void {
    this.screens.extras({
      onJournal: () => this.screens.journal(this.save.lore, () => this.extras()),
      onCatalog: () =>
        this.screens.catalog({
          caught: this.save.catalog,
          images: this.assets.fish,
          revealAll: new URLSearchParams(location.search).get('catalogo') === 'tutto',
          onBack: () => this.extras(),
        }),
      onBack: () => this.title(),
    });
  }

  private options(back: () => void): void {
    this.screens.options(this.save.options, {
      onChange: (k, v) => {
        if (k === 'lang') {
          this.lang = v as Lang;
          this.save.lang = this.lang;
          this.screens.lang = this.lang;
          writeSave(this.save);
          this.options(back);
          return;
        }
        (this.save.options as unknown as Record<string, number | boolean>)[k] = v as number | boolean;
        this.applyOptions();
        writeSave(this.save);
      },
      onBack: back,
      fullscreen: document.fullscreenEnabled
        ? () => {
            if (document.fullscreenElement) void document.exitFullscreen();
            else void document.documentElement.requestFullscreen();
          }
        : null,
    });
  }

  private applyOptions(): void {
    const o: Options = this.save.options;
    const v = this.audio.volumes;
    v.master = o.master;
    v.music = o.music;
    v.sfx = v.amb = v.voice = v.ui = o.sfx;
    this.audio.applyVolumes();
    this.stage.brightness = o.brightness;
  }

  private intro(): void {
    this.mode = 'intro';
    this.timer = 3.6;
    this.screens.intro(1, NIGHTS[1]!.quota);
    this.titleMusic(false);
    this.audio.play('mus_night_start', { gain: 0.9 });
    setTimeout(() => this.audio.play('foghorn', { gain: 0.5, lowpass: 1800 }), 1500);
  }

  private startNight(): void {
    this.screens.clear();
    this.night?.destroy();
    this.night = new Night({
      stage: this.stage,
      audio: this.audio,
      sfx: this.sfx,
      ui: this.ui,
      canvas: this.canvas,
      lang: this.lang,
      options: this.save.options,
      foundLore: this.save.lore,
      assets: this.assets,
      seed: (Date.now() & 0x7fffffff) >>> 0,
      onEnd: (r) => this.endNight(r),
      onPause: () => this.pause(),
      knownSpecies: new Set(Object.keys(this.save.catalog)),
      onCatch: (species, kg) => {
        const c = (this.save.catalog[species] ??= { count: 0, bestKg: 0 });
        c.count++;
        c.bestKg = Math.max(c.bestKg, kg);
      },
    });
    this.mode = 'night';
    this.night.start();
  }

  private pause(): void {
    if (!this.night || this.mode !== 'night') return;
    this.mode = 'paused';
    this.night.setPaused(true);
    this.audio.suspend();
    const show = () =>
      this.screens.pause({
        onResume: () => this.resume(),
        onOptions: () => this.options(show),
        onMenu: () => {
          removeEventListener('keydown', this.escResume);
          this.audio.resume();
          this.night?.destroy();
          this.night = null;
          this.title();
        },
      });
    show();
    // Esc di nuovo riprende (registrato dopo questo evento, e tolto comunque alla ripresa)
    setTimeout(() => addEventListener('keydown', this.escResume), 0);
  }

  private escResume = (e: KeyboardEvent): void => {
    if (e.key === 'Escape' && this.mode === 'paused') {
      e.stopImmediatePropagation();
      this.resume();
    }
  };

  private resume(): void {
    removeEventListener('keydown', this.escResume);
    if (!this.night) return;
    this.screens.clear();
    this.audio.resume();
    this.night.setPaused(false);
    this.mode = 'night';
  }

  private endNight(r: NightEnd): void {
    // i ritrovamenti restano anche se la notte va male
    for (const l of r.stats.lore) if (!this.save.lore.includes(l)) this.save.lore.push(l);
    if (r.kind === 'won') this.save.night = Math.max(this.save.night, 2);
    writeSave(this.save);
    const S = this.S;
    const show = () => {
      this.mode = 'end';
      this.night?.destroy();
      this.night = null;
      if (r.kind === 'dead' && r.killer !== 'mother') this.audio.play('mus_gameover', { gain: 0.9 });
      this.screens.results({
        won: r.kind === 'won',
        text: r.kind === 'won' ? S.quotaMet : S.deaths[r.killer as MonsterId | 'mother'],
        caught: r.stats.caught,
        fed: r.stats.fed,
        lore: r.stats.lore.length,
        demoEnd: r.kind === 'won',
        onRetry: () => this.intro(),
        onMenu: () => this.title(),
      });
    };
    if (r.kind === 'dead' && r.killer !== 'mother') {
      this.mode = 'static';
      this.screens.static();
      this.audio.play('static_burst', { gain: 0.6 });
      this.timer = 1.1;
      this.afterStatic = show;
    } else show();
  }

  private afterStatic: (() => void) | null = null;
  private music: Voice | null = null;

  // ───────────────────────── ciclo ─────────────────────────

  frame(dt: number): void {
    const st = this.stage;
    switch (this.mode) {
      case 'night':
        this.night!.update(dt);
        this.night!.render();
        return;
      case 'paused':
        this.night!.render();
        return;
      case 'intro':
        this.timer -= dt;
        if (this.timer <= 0) {
          this.startNight();
          return;
        }
        break;
      case 'static':
        this.timer -= dt;
        if (this.timer <= 0 && this.afterStatic) {
          const f = this.afterStatic;
          this.afterStatic = null;
          f();
        }
        break;
      default:
        break;
    }
    // sfondo dei menu: la barca alla deriva, lo sguardo che vaga piano
    st.view.rockBoost = 0;
    st.view.swell = 1;
    st.view.targetYaw += dt * 2.5;
    st.update(dt);
    st.frame({ layers: ['world', 'boat', 'rod0'] });
  }
}
