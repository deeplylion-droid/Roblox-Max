// Tutti i testi del gioco in una lingua (interfaccia, Diario, radio, finali), su stdout: per sapere quali caratteri
// servono nei font (tools/fonts/sottoinsieme_cjk.py). Uso: node --experimental-strip-types --no-warnings tools/fonts/testi_lingua.mjs <lingua>
// Le tabelle dei testi sono quelle che hanno per chiavi esattamente le lingue del gioco (LANGS); RADIO ne ha una per notte.
const lang = process.argv[2];
const m = await import('../../src/i18n.ts');
const lingue = [...m.LANGS].sort().join();
const tabella = (v) => v && typeof v === 'object' && !Array.isArray(v) && Object.keys(v).sort().join() === lingue;
const out = [];
const raccogli = (v) => {
  if (typeof v === 'string') out.push(v);
  // le frasi con un nome dentro (offer(who) …): il testo sta nel sorgente della funzione
  else if (typeof v === 'function') out.push(v.toString());
  else if (Array.isArray(v)) v.forEach(raccogli);
  else if (v && typeof v === 'object') Object.values(v).forEach(raccogli);
};
for (const v of Object.values(m)) {
  if (tabella(v)) raccogli(v[lang]);
  else if (v && typeof v === 'object' && !Array.isArray(v)) for (const w of Object.values(v)) if (tabella(w)) raccogli(w[lang]);
}
// le lingue nuove hanno tutti i loro testi (anche il Catalogo) in src/lingue/<lingua>.ts
try {
  const t = (await import(`../../src/lingue/${lang}.ts`)).default;
  raccogli(t);
} catch {
  // italiano e inglese: stanno solo in src/i18n.ts e nel Catalogo
}
if (!out.length) {
  console.error(`nessun testo per la lingua ${lang}`);
  process.exit(1);
}
process.stdout.write(out.join('\n'));
