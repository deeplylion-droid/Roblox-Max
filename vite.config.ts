import { execSync } from 'node:child_process';
import { defineConfig } from 'vite';

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

// base relativa: la stessa build funziona nel browser, in Electron (file://) e come demo statica.
export default defineConfig({
  base: './',
  define: { __BUILD__: JSON.stringify(buildId()) },
  build: {
    outDir: 'dist',
    assetsInlineLimit: 0,
    target: 'es2022',
    chunkSizeWarningLimit: 2000,
  },
  server: { host: true },
});
