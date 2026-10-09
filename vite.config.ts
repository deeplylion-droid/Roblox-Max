import { defineConfig } from 'vite';

// base relativa: la stessa build funziona nel browser, in Electron (file://) e come demo statica.
export default defineConfig({
  base: './',
  build: {
    outDir: 'dist',
    assetsInlineLimit: 0,
    target: 'es2022',
    chunkSizeWarningLimit: 2000,
  },
  server: { host: true },
});
