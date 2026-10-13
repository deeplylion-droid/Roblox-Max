/**
 * Una lingua del gioco oltre all'italiano e all'inglese (docs/LOCALIZZAZIONE.md, «Per una lingua nuova»): tutti i
 * testi in un file solo, `src/lingue/<codice>.ts`, che src/i18n.ts mette insieme agli altri. Tradotti dall'italiano
 * (l'originale), con l'inglese approvato come riferimento per il senso e per i giochi di parole.
 */
import type { RadioLine, Testi } from '../i18n.ts';

export interface Traduzione {
  /** l'interfaccia: la stessa forma dei testi italiani (TypeScript dice se manca qualcosa) */
  strings: Testi;
  /** il Diario: titolo e testo di ogni voce, con le stesse chiavi di LORE_TEXT.it */
  lore: Record<string, { title: string; body: string }>;
  /** la chiamata alla radio di ogni notte (1-7), con gli stessi tempi (`at`) dell'italiano */
  radio: Record<1 | 2 | 3 | 4 | 5 | 6 | 7, RadioLine[]>;
  /** la radio del finale (RADIO_FINALE), con gli stessi tempi */
  radioFinale: RadioLine[];
  /** il Catalogo: per ogni pesce (id di src/game/catalog.ts) il nome inventato, il nome comune della specie vera e la
   *  descrizione */
  catalogo: Record<string, { name: string; real: string; desc: string }>;
}
