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

/** Fino a che notte arriva questa build: VITE_ULTIMA_NOTTE=1 per la demo della sola prima notte. */
const NIGHT_LIMIT = Number(import.meta.env.VITE_ULTIMA_NOTTE) || Infinity;

/** L'ultima notte giocabile (che esiste nel gioco e che questa build lascia giocare). */
function lastNight(): number {
  let n = 1;
  while (NIGHTS[n + 1] && n + 1 <= NIGHT_LIMIT) n++;
  return n;
}

export class App {
  private mode: Mode = 'warning';
  private night: Night | null = null;
  readonly screens: Screens;
  private timer = 0;
  private lang: Lang;
  /** la notte in corso (o l'ultima giocata) */
  private nightNo = 1;

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
    // la ninna nanna parte già sull'avvertenza e continua nel menu (dove il browser la blocca, al primo tasto)
    void this.audio.preload('mus_title').then(() => {
      if (this.mode === 'warning' || this.mode === 'title') this.titleMusic(true);
    });
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

  /** La ninna nanna della Madre al carillon, dall'avvertenza al menu (si avvia solo se non suona già). */
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
    // ?notte=N: la nuova partita parte da quella notte (prove)
    const forced = Number(new URLSearchParams(location.search).get('notte'));
    const reached = Math.min(this.save.night, lastNight());
    this.screens.title({
      canContinue: reached >= 2,
      onNew: () => this.intro(forced >= 1 && forced <= lastNight() ? forced : 1),
      onContinue: () => this.intro(reached),
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

  private intro(n = this.nightNo): void {
    this.mode = 'intro';
    this.timer = 3.6;
    this.nightNo = NIGHTS[n] ? n : 1;
    this.screens.intro(this.nightNo, NIGHTS[this.nightNo]!.quota);
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
      night: this.nightNo,
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
    if (r.kind === 'won') this.save.night = Math.max(this.save.night, this.nightNo + 1);
    writeSave(this.save);
    const S = this.S;
    const show = () => {
      this.mode = 'end';
      this.night?.destroy();
      this.night = null;
      if (r.kind === 'dead' && r.killer !== 'mother') this.audio.play('mus_gameover', { gain: 0.9 });
      this.screens.results({
        won: r.kind === 'won',
        text: r.kind === 'won' ? S.quotaMet : r.cause === 'lullaby' ? S.deaths.lullaby : S.deaths[r.killer as MonsterId | 'mother'],
        caught: r.stats.caught,
        fed: r.stats.fed,
        lore: r.stats.lore.length,
        demoEnd: r.kind === 'won' && this.nightNo >= lastNight(),
        onNext: r.kind === 'won' && this.nightNo < lastNight() ? () => this.intro(this.nightNo + 1) : null,
        onRetry: () => this.intro(),
        onMenu: () => this.title(),
      });
    };
    if (r.kind === 'dead' && r.killer !== 'mother') {
      // il segnale salta: la notte si spegne di colpo, resta la neve del televisore, poi i risultati
      this.mode = 'static';
      this.night?.destroy();
      this.night = null;
      this.screens.static();
      this.audio.play('static_burst', { gain: 0.85 });
      this.timer = 1.2;
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
        // la notte può finire dentro l'aggiornamento (alba, la Madre, il segnale che salta): allora
        // si disegna subito quello che viene dopo
        if (this.mode === 'night' && this.night) this.night.render();
        else this.frame(0);
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
          break;
        }
        // segnale perso: solo neve (più scura se l'utente ha chiesto meno lampi)
        st.update(dt);
        st.frame({ layers: ['world'], snow: 1, fade: this.save.options.reduceFlash ? 0.55 : 1 });
        return;
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
