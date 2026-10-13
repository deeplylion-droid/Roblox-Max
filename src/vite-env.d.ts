/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** fino a che notte arriva questa build (1 = demo della sola prima notte); senza, tutte */
  readonly VITE_ULTIMA_NOTTE?: string;
  /** «1» nelle build di prova: le scorciatoie da tastiera per le notti, la vittoria e i jumpscare (src/app/prove.ts) */
  readonly VITE_SCORCIATOIE?: string;
}

/** la sigla della build (vite.config.ts): il commit e quando è stata fatta */
declare const __BUILD__: string;
/** le scorciatoie di prova (vite.config.ts, src/app/prove.ts): vero in sviluppo, nei test e nelle build di prova */
declare const __SCORCIATOIE__: boolean;
