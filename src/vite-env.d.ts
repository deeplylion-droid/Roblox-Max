/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** fino a che notte arriva questa build (1 = demo della sola prima notte); senza, tutte */
  readonly VITE_ULTIMA_NOTTE?: string;
}

/** la sigla della build (vite.config.ts): il commit e quando è stata fatta */
declare const __BUILD__: string;
