import { execSync } from 'node:child_process';
import path from 'node:path';
import { defineConfig, loadEnv, type Plugin } from 'vite';
import { alleggerisci } from './scripts/demo.ts';

/** La sigla della build, piccola sul titolo (per sapere quale build si sta provando): il commit e l'ora italiana. */
function buildId(): string {
  let sha = process.env.GITHUB_SHA ?? '';
  if (!sha) {
    try {
      sha = execSync('git rev-parse HEAD', { encoding: 'utf8' }).trim();
    } catch {
      sha = 'dev';
    }
  }
  const when = new Date().toLocaleString('it-IT', { timeZone: 'Europe/Rome', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  return `build ${sha.slice(0, 7)} · ${when}`;
}

/** La demo leggera: con VITE_ULTIMA_NOTTE (la demo: 2), a build finita i file delle notti dopo escono da dist/
 *  (scripts/demo.ts). */
function demoLeggera(ultima: number): Plugin {
  let dist = 'dist';
  return {
    name: 'demo-leggera',
    apply: 'build',
    configResolved(c) {
      dist = path.resolve(c.root, c.build.outDir);
    },
    closeBundle() {
      if (!ultima) return;
      const r = alleggerisci(dist, ultima);
      console.log(`demo fino alla notte ${ultima}: tolti ${r.file} file delle notti dopo (${(r.byte / 1e6).toFixed(1)} MB)`);
    },
  };
}

// base relativa: la stessa build funziona nel browser, in Electron (file://) e come demo statica.
export default defineConfig(({ command, mode }) => ({
  base: './',
  plugins: [demoLeggera(Number(loadEnv(mode, process.cwd(), 'VITE_').VITE_ULTIMA_NOTTE) || 0)],
  define: {
    __BUILD__: JSON.stringify(buildId()),
    // le scorciatoie di prova (src/app/prove.ts): sempre in sviluppo e nei test, nelle build solo con
    // VITE_SCORCIATOIE=1; altrimenti è «false» già nel codice e il minificatore toglie tutto quello che la usa
    __SCORCIATOIE__: JSON.stringify(command === 'serve' || process.env.VITE_SCORCIATOIE === '1'),
  },
  build: {
    outDir: 'dist',
    assetsInlineLimit: 0,
    target: 'es2022',
    chunkSizeWarningLimit: 2000,
  },
  server: { host: true },
}));
