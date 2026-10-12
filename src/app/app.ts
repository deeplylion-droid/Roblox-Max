/**
 * Il gioco intero: avvertenza → titolo → intro della notte → notte → alba o game over. All'alba di una notte vinta
 * (dalla prima alla quinta) si può scendere con le bombole (l'immersione, src/app/dive.ts) prima della notte dopo.
 * Tiene il salvataggio, le opzioni e lo sfondo animato dei menu (la scena dalla barca).
 */
import { loadLayer } from '../engine/assets.ts';
import { DISEGNI_ALBA, disegnoAlba, disegniTrovati } from './disegni.ts';
import { useLangFonts } from './fonts_lingua.ts';
import type { AudioEngine, Voice } from '../engine/audio.ts';
import { EXTRA_NIGHT, NIGHTS, extraEndingEarned, extraNight, type MonsterId, type NightConfig } from '../game/config.ts';
import { STRINGS, localizedImage, type Lang } from '../i18n.ts';
import { Dive, loadDiveData, type DiveResult } from './dive.ts';
import { Night, type NightAssets, type NightEnd } from './night.ts';
import { swapFogAssets } from './overlays.ts';
import { badge, pad } from './pad.ts';
import { PadNav } from './padnav.ts';
import { afterDive, chooseEnding, fedFor, newGame, pendingDawn, skipDawn, wonNight, writeSave, type Ending, type Options, type SaveData } from './save.ts';
import { Screens, setUiSound } from './screens.ts';
import type { Sfx } from './sfx.ts';
import type { Stage } from './stage.ts';

type Mode = 'warning' | 'title' | 'annuncio' | 'intro' | 'night' | 'paused' | 'static' | 'end' | 'dive';

/**
 * L'annuncio dopo «Nuova partita», come l'«Help Wanted» di FNAF (richiesta dell'utente del 12 ottobre; scelto il
 * volantino del parco, da approvare): 3-4 s con una zoomata lenta, si salta col clic. Lo fa tools/render/annuncio.py.
 */
const ANNUNCIO = {
  src: 'assets/img/annuncio/volantino.webp',
  /** le lingue che hanno la loro versione (vedi localizedImage) */
  langs: ['en'],
  /** dove va la zoomata, in frazioni dell'immagine: il centro del volantino, un po' verso il fumetto (a fine zoomata
   *  si leggono ancora le condizioni in fondo; escono solo le linguette) */
  fx: 0.52,
  fy: 0.46,
  /** quanto dura, e l'ultimo pezzo, in cui si spegne nel buio */
  seconds: 3.8,
  fadeOut: 0.45,
};

/** Le immersioni all'alba si fanno dopo le notti dalla prima alla quinta (docs/IMMERSIONI.md). */
const LAST_DIVE_NIGHT = 5;

const isElectron = navigator.userAgent.includes('Electron');

/** La pagina del gioco su Steam (per il tasto «Aggiungi alla lista dei desideri» alla fine della demo): si
 *  mette quando la pagina esiste. In Electron i link si aprono nel browser (electron/main.cjs). */
const STEAM_URL: string | null = null;

/** Fino a che notte arriva questa build: VITE_ULTIMA_NOTTE=1 per la demo della sola prima notte. */
const NIGHT_LIMIT = Number(import.meta.env.VITE_ULTIMA_NOTTE) || Infinity;

/** ?finale=tuoi|nessuno|A nell'indirizzo: forza il finale della sesta notte; ?finale=B quello della notte extra (prove e
 *  registrazioni; mai nelle build). */
const FORCE_ENDING = ((): Ending | 'B' | null => {
  if (!import.meta.env.DEV) return null;
  const f = new URLSearchParams(location.search).get('finale');
  return f === 'tuoi' || f === 'nessuno' || f === 'A' || f === 'B' ? f : null;
})();

/** ?bozze nell'indirizzo: si possono giocare anche le notti in bozza (prove; mai nelle build). */
const DRAFTS = import.meta.env.DEV && new URLSearchParams(location.search).has('bozze');
/** Dopo la notte n si può scendere con le bombole? (dalla prima alla quinta, se la notte dopo si gioca) */
function canDive(n: number): boolean {
  return n >= 1 && n <= LAST_DIVE_NIGHT && n < lastNight();
}

/** L'ultima notte giocabile (che esiste nel gioco e che questa build lascia giocare). */
function lastNight(): number {
  let n = 1;
  while (NIGHTS[n + 1] && (DRAFTS || !NIGHTS[n + 1]!.bozza) && n + 1 <= NIGHT_LIMIT) n++;
  return n;
}

export class App {
  private mode: Mode = 'warning';
  private night: Night | null = null;
  /** l'immersione all'alba in corso */
  private diving: Dive | null = null;
  readonly screens: Screens;
  private timer = 0;
  private lang: Lang;
  /** Alt + numero sul titolo (vedi title) */
  private nightKeys: ((e: KeyboardEvent) => void) | null = null;
  /** la notte in corso (o l'ultima giocata) */
  private nightNo = 1;
  /** i menu col controller */
  private nav = new PadNav();
  /** in basso a destra nei menu, col controller in uso: «A Scegli · B Indietro» */
  private legendEl: HTMLDivElement;

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
    // la lingua della pagina: i font e gli a capo del cinese, del giapponese e del coreano dipendono da questa (styles.css)
    document.documentElement.lang = lang;
    useLangFonts(lang);
    this.screens = new Screens(ui, lang);
    this.legendEl = document.createElement('div');
    this.legendEl.className = 'pad-legend';
    ui.appendChild(this.legendEl);
    this.legend();
    this.applyOptions();
    addEventListener('blur', () => {
      if (this.mode === 'night') this.pause();
    });
  }

  get S() {
    return STRINGS[this.lang];
  }

  private legend(): void {
    const S = this.S;
    const item = (b: 'A' | 'B', text: string) => {
      const s = document.createElement('span');
      s.append(badge(b), text);
      return s;
    };
    this.legendEl.replaceChildren(item('A', S.pad.select), item('B', S.back));
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
    // ?notte=N: la nuova partita parte da quella notte (prove); ?notte=7 apre la notte extra
    const forced = Number(new URLSearchParams(location.search).get('notte'));
    // «Continua» riprende la partita in corso, non l'ultima notte mai sbloccata (dopo una «Nuova partita» sono diverse)
    const reached = Math.min(this.save.current, lastNight());
    // la notte extra si sblocca finendo l'ultima notte giocabile (sarà la sesta, la Madre)
    const extraOpen = this.save.night > lastNight() || forced === EXTRA_NIGHT;
    // Alt + numero sul titolo: comincia da quella notte (per provare le notti dopo la prima nelle build di prova;
    // la demo arriva solo alla prima)
    if (!this.nightKeys) {
      this.nightKeys = (e: KeyboardEvent) => {
        const n = Number(e.key);
        if (this.mode !== 'title' || !e.altKey || !((n >= 1 && n <= lastNight()) || n === EXTRA_NIGHT)) return;
        e.preventDefault();
        // Alt+7: la schermata dei livelli della notte extra
        if (n === EXTRA_NIGHT) this.extraNight();
        else this.intro(n);
      };
      addEventListener('keydown', this.nightKeys);
    }
    // l'annuncio di «Nuova partita» pronto in memoria, che compaia subito
    new Image().src = localizedImage(ANNUNCIO.src, this.lang, ANNUNCIO.langs);
    this.screens.title({
      canContinue: reached >= 2,
      onNew: () => {
        if (forced === EXTRA_NIGHT) return this.extraNight();
        // nuova partita: niente pesci, mostri sfamati e tane della partita di prima
        newGame(this.save);
        writeSave(this.save);
        const n = forced >= 1 && forced <= lastNight() ? forced : 1;
        // dalla prima notte, prima l'annuncio con cui il pescatore ha trovato il lavoro
        if (n === 1) this.annuncio(() => this.intro(1));
        else this.intro(n);
      },
      // se il gioco era stato chiuso sullo schermo dell'alba, si riprende da lì (si può ancora scendere)
      onContinue: () => (canDive(reached - 1) && pendingDawn(this.save, reached) ? this.dawnAgain(reached) : this.intro(reached)),
      onExtraNight: extraOpen ? () => this.extraNight() : null,
      onJournal: () => this.extras(),
      onOptions: () => this.options(() => this.title()),
      onQuit: isElectron ? () => window.close() : null,
    });
  }

  /** La notte extra: si scelgono i livelli dei sette mostri, poi si salpa (restano salvati per la prossima volta). */
  private extraNight(): void {
    this.mode = 'title';
    this.screens.extraNight(this.save.extra, {
      onChange: (l) => {
        this.save.extra = l;
        writeSave(this.save);
      },
      onStart: (l) => {
        this.save.extra = l;
        writeSave(this.save);
        this.intro(EXTRA_NIGHT);
      },
      onBack: () => this.title(),
    });
  }

  /** la config della notte n: la notte extra si costruisce dai livelli scelti */
  private config(n: number): NightConfig {
    return n === EXTRA_NIGHT ? extraNight(this.save.extra) : NIGHTS[n]!;
  }

  private extras(): void {
    this.screens.extras({
      onJournal: () =>
        this.screens.journal(this.save.lore, () => this.extras(), { all: Object.values(DISEGNI_ALBA), found: disegniTrovati(this.save.night) }),
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
          document.documentElement.lang = this.lang;
          useLangFonts(this.lang);
          this.legend();
          writeSave(this.save);
          this.options(back);
          return;
        }
        (this.save.options as unknown as Record<string, number | boolean>)[k] = v as number | boolean;
        this.applyOptions();
        if (k === 'fog') this.swapFog(v as boolean);
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

  /** i cambi di serie dell'opzione «Nebbia», uno dopo l'altro (se si preme due volte di fila il secondo aspetta) */
  private fogSwap: Promise<void> = Promise.resolve();

  /** L'opzione «Nebbia» cambiata: il mondo, la barca, il binocolo e il telone passano all'altra serie di immagini
   *  (pochi megabyte, un attimo; anche a notte in corso). Mostri e jumpscare sono gli stessi nelle due serie. */
  private swapFog(on: boolean): void {
    this.fogSwap = this.fogSwap
      .then(async () => {
        const r = this.stage.renderer;
        for (const k of ['world', 'boat']) {
          if (!this.stage.man.layers[k]?.senza) continue;
          const l = await loadLayer(r.gl, this.stage.man, k, !on);
          r.removeLayer(k);
          r.addLayer(l);
        }
        await swapFogAssets(r.gl, this.assets, !on);
      })
      .catch((e) => console.warn(e));
  }

  private applyOptions(): void {
    const o: Options = this.save.options;
    this.stage.fog = o.fog;
    const v = this.audio.volumes;
    v.master = o.master;
    v.music = o.music;
    v.sfx = v.amb = v.voice = v.ui = v.body = o.sfx;
    this.audio.applyVolumes();
    this.stage.brightness = o.brightness;
    this.stage.renderer.renderScale = o.quality;
    // «Riduci lampi e scosse» spegne anche le vibrazioni del controller
    pad.rumbleOn = !o.reduceFlash;
    document.documentElement.style.setProperty('--ts', String(o.textSize || 1));
  }

  /** L'annuncio (vedi ANNUNCIO), poi `next`. Sotto continua la ninna nanna del titolo. */
  private annuncio(next: () => void): void {
    this.mode = 'annuncio';
    // il conto va col tempo vero, come la zoomata (Web Animations): finiscono insieme anche coi fotogrammi lenti
    this.annuncioEnd = performance.now() + ANNUNCIO.seconds * 1000;
    this.afterAnnuncio = next;
    this.screens.annuncio({
      src: localizedImage(ANNUNCIO.src, this.lang, ANNUNCIO.langs),
      fx: ANNUNCIO.fx,
      fy: ANNUNCIO.fy,
      seconds: ANNUNCIO.seconds,
      onSkip: () => {
        if (this.mode === 'annuncio') this.annuncioEnd = Math.min(this.annuncioEnd, performance.now() + ANNUNCIO.fadeOut * 1000);
      },
    });
  }

  private intro(n = this.nightNo): void {
    this.mode = 'intro';
    this.timer = 3.6;
    this.nightNo = NIGHTS[n] || n === EXTRA_NIGHT ? n : 1;
    this.screens.intro(this.nightNo, this.config(this.nightNo).quota);
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
      config: this.nightNo === EXTRA_NIGHT ? this.config(EXTRA_NIGHT) : undefined,
      // il mostro sfamato all'alba dorme stanotte
      fed: fedFor(this.save, this.nightNo),
      // il finale della sesta notte: dai pesci lasciati nelle tane, alba per alba
      ending:
        this.nightNo === 6
          ? FORCE_ENDING && FORCE_ENDING !== 'B'
            ? FORCE_ENDING
            : chooseEnding(this.save)
          : this.nightNo === EXTRA_NIGHT && (FORCE_ENDING === 'B' || extraEndingEarned(this.save.extra))
            ? 'B'
            : undefined,
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
    // a notte finita (l'alba, la cinematica del finale) niente pausa: perdendo il fuoco della finestra, «Menu
    // principale» o «Ricomincia la notte» butterebbero via la notte vinta (Esc la pausa già non l'apre)
    if (!this.night || this.mode !== 'night' || this.night.over) return;
    this.mode = 'paused';
    this.night.setPaused(true);
    this.audio.suspend();
    const show = () =>
      this.screens.pause({
        onResume: () => this.resume(),
        // ricomincia la notte in corso da capo (dall'intro, come «Riprova» dopo una morte)
        onRestart: () => {
          removeEventListener('keydown', this.escResume);
          this.audio.resume();
          this.night?.destroy();
          this.night = null;
          this.intro(this.nightNo);
        },
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
    // la notte extra non sblocca niente (è fuori dal conto delle notti) e non ha un'alba con l'immersione
    const extra = this.nightNo === EXTRA_NIGHT;
    // all'alba: i pesci oltre la quota (uno lo puoi portare giù nell'immersione); il mostro sfamato ha dormito
    const spare = r.kind === 'won' && !extra ? Math.max(0, r.stats.bucket - NIGHTS[this.nightNo]!.quota) : 0;
    if (r.kind === 'won' && !extra) wonNight(this.save, this.nightNo, spare);
    writeSave(this.save);
    const next = this.nightNo + 1;
    const diveOk = r.kind === 'won' && canDive(this.nightNo);
    const S = this.S;
    // un jumpscare (i figli, o la Madre che ti prende da sotto perché ti sei mosso): il segnale salta
    const jumpscare = r.kind === 'dead' && (r.js === true || r.killer !== 'mother' || r.cause === 'moved');
    const show = () => {
      this.mode = 'end';
      this.night?.destroy();
      this.night = null;
      if (jumpscare) this.audio.play('mus_gameover', { gain: 0.9 });
      this.screens.results({
        won: r.kind === 'won',
        text:
          r.kind === 'won'
            ? this.nightNo === 6
              ? r.ending === 'tuoi'
                ? S.finaleTuoi
                : r.ending === 'nessuno'
                  ? S.finaleNessuno
                  : S.finaleA
              : S.quotaMet
            : r.cause === 'lullaby'
              ? S.deaths.lullaby
              : r.cause === 'moved'
                ? S.deaths.moved
                : S.deaths[r.killer as MonsterId | 'mother'],
        caught: r.stats.caught,
        fed: r.stats.fed,
        lore: r.stats.lore.length,
        demoEnd: r.kind === 'won' && !extra && this.nightNo >= lastNight(),
        onNext: r.kind === 'won' && !extra && this.nightNo < lastNight() ? () => this.skipToNight(next) : null,
        // i pesci avanzati servono solo se all'alba si può scendere
        spare: diveOk ? spare : undefined,
        onDive: diveOk ? () => this.dive(next) : null,
        // il disegno a pastelli sul banco, all'alba delle notti 1-5
        drawing: r.kind === 'won' && !extra ? disegnoAlba(this.nightNo) : null,
        // finita l'ultima notte (la sesta), si apre la notte extra
        onExtra: r.kind === 'won' && !extra && this.nightNo >= lastNight() && NIGHT_LIMIT === Infinity ? () => this.extraNight() : null,
        afterEnding: r.kind === 'won' && !!r.ending,
        onWishlist: STEAM_URL ? () => window.open(STEAM_URL, '_blank') : null,
        onRetry: () => this.intro(),
        onMenu: () => this.title(),
      });
    };
    if (jumpscare) {
      // il segnale salta: la notte si spegne di colpo, resta la neve del televisore, poi i risultati
      this.mode = 'static';
      this.night?.destroy();
      this.night = null;
      this.screens.static();
      this.audio.play('static_burst', { gain: 0.85 });
      this.timer = 1.2;
      this.afterStatic = show;
    } else if (!extra && r.kind === 'won' && this.nightNo === 6) {
      // dopo il finale della notte 6 (A, «I tuoi» o «Nessuno»): i titoli di coda, con la ninna nanna del titolo; poi i
      // risultati, con l'avviso della notte extra
      this.mode = 'end';
      this.night?.destroy();
      this.night = null;
      this.titleMusic(true);
      this.screens.credits(() => {
        this.titleMusic(false);
        show();
      });
    } else show();
  }

  // ───────────────────────── immersione all'alba ─────────────────────────

  /** L'alba ripresa da «Continua» (il gioco era stato chiuso sullo schermo dei risultati): scendere o no. */
  private dawnAgain(next: number): void {
    this.mode = 'end';
    this.screens.dawn({
      spare: pendingDawn(this.save, next)?.spare ?? 0,
      drawing: disegnoAlba(next - 1),
      onDive: () => this.dive(next),
      onNext: () => this.skipToNight(next),
      onMenu: () => this.title(),
    });
  }

  /** Alla notte dopo senza scendere: l'alba si chiude. */
  private skipToNight(next: number): void {
    skipDawn(this.save);
    writeSave(this.save);
    this.intro(next);
  }

  /** Scendi con le bombole prima della notte `next`, con i pesci avanzati alle sei (dal salvataggio dell'alba). */
  private dive(next: number): void {
    const spare = pendingDawn(this.save, next)?.spare ?? 0;
    this.mode = 'dive';
    this.screens.clear();
    this.titleMusic(false);
    const fail = (e: unknown) => {
      // senza dati o panorami l'immersione non si fa: si va alla notte dopo (come un'alba senza discesa)
      console.error(e);
      this.diving?.destroy();
      this.diving = null;
      this.skipToNight(next);
    };
    loadDiveData()
      .then((data) => {
        if (this.mode !== 'dive') return;
        this.diving = new Dive({
          stage: this.stage,
          audio: this.audio,
          ui: this.ui,
          canvas: this.canvas,
          lang: this.lang,
          options: this.save.options,
          data,
          nextNight: next,
          spare,
          known: this.save.lore,
          onEnd: (r) => this.endDive(next, r),
        });
        this.diving.start().catch(fail);
      })
      .catch(fail);
  }

  /** Risaliti: chi è stato sfamato dorme la notte dopo, le tane viste restano; poi la notte dopo. */
  private endDive(next: number, r: DiveResult): void {
    this.diving?.destroy();
    this.diving = null;
    // il pesce portato giù è rimasto lì o è tornato alla Madre: l'alba è finita
    afterDive(this.save, next, r);
    writeSave(this.save);
    this.intro(next);
  }

  private afterStatic: (() => void) | null = null;
  private afterAnnuncio: (() => void) | null = null;
  /** quando finisce l'annuncio (performance.now) */
  private annuncioEnd = 0;
  private music: Voice | null = null;

  // ───────────────────────── ciclo ─────────────────────────

  /** Un fotogramma: si legge il controller, poi si va avanti. */
  frame(dt: number): void {
    pad.poll();
    this.tick(dt);
  }

  private tick(dt: number): void {
    const st = this.stage;
    switch (this.mode) {
      case 'night':
        this.night!.update(dt);
        // la notte può finire dentro l'aggiornamento (alba, la Madre, il segnale che salta): allora
        // si disegna subito quello che viene dopo
        if (this.mode === 'night' && this.night) this.night.render();
        else this.tick(0);
        return;
      case 'paused':
        // col controller: Start riprende, il resto lo fanno i menu (B riprende anche lui)
        if (pad.pressed('Start')) this.resume();
        else this.nav.update(this.ui, dt);
        this.night?.render();
        return;
      case 'dive':
        // prima i menu (la conferma del pesce), poi l'immersione: un tasto usato da uno non arriva all'altra
        this.nav.update(this.ui, dt);
        this.diving?.update(dt);
        // l'immersione può finire dentro l'aggiornamento (la risalita): allora si disegna quello che viene dopo
        if (this.mode === 'dive' && this.diving) this.diving.render();
        else if (this.mode === 'dive') st.frame({ layers: [], fade: 0 });
        else this.tick(0);
        return;
      case 'annuncio': {
        const left = (this.annuncioEnd - performance.now()) / 1000;
        // l'ultimo pezzo: il volantino si spegne nel buio
        if (left <= ANNUNCIO.fadeOut) this.screens.annuncioOut(ANNUNCIO.fadeOut);
        if (left <= 0) {
          const next = this.afterAnnuncio;
          this.afterAnnuncio = null;
          next?.();
          return;
        }
        // il controller lo salta (padnav); la scena dietro non si vede, non serve disegnarla
        this.nav.update(this.ui, dt);
        return;
      }
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
    // i menu col controller (l'avvertenza, il titolo, le opzioni, i risultati…)
    this.nav.update(this.ui, dt);
    // sfondo dei menu: la barca alla deriva, lo sguardo che vaga piano
    st.view.rockBoost = 0;
    st.view.swell = 1;
    st.view.targetYaw += dt * 2.5;
    st.update(dt);
    st.frame({ layers: ['world', 'boat', 'rod0'] });
  }
}
