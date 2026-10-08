# Copertura del GDD (v1.0)

| Sezione | Requisito | Dove |
|---|---|---|
| 1 | Le creature non si perdono mai; solo le scintille esposte sono contendibili | `EconomyService.RemoveExposed` tocca solo pool esposto e buffer; `Vault` e `Creatures` mai |
| 1 | Promessa 60 s / 5 min / 12 min | Creatura iniziale in inventario → tutorial passo 1–2; `docs/BALANCE.md` |
| 2 | Hub: vivaio dimostrativo, bacheca, portale, galleria | `WorldBuilder` (stazioni con ProximityPrompt) |
| 2 | 4 informazioni sempre visibili | `UI/HUD.luau` (Exposed, Vault, Protection, Goal) |
| 2 | Pulsanti grandi, testo oltre al colore, audio off, effetti ridotti | `Theme.ButtonHeight`, pillole/toggle con testo, `SettingsPanel` |
| 2 | Comando contestuale unico | ProximityPrompt (E / tocco / controller) + pulsanti HUD |
| 3 | Ciclo breve | ritira → deposita → compra → prova/incursione → ricompensa (Economy/Defense/Raid) |
| 4.1 | 16 creature, 4 famiglie, 4 varianti | `Catalog/Creatures.luau` |
| 4.1 | Rendimento marginale decrescente oltre la 6ª | `Config.Production.DiminishingFactors` |
| 4.1 | Riserva offline con tetto | `Config.Production.Offline*`, `applyOfflineReserve` |
| 4.1 | Stati esposta/depositata; deposito manuale e automatico sbloccabile | `EconomyService`, `AlbumService` (Maestria Collezione II) |
| 4.2 | Bersagli proposti, stima difficoltà, copia istanziata, 60–90 s | `RaidService`, `ArenaPool`, `PlotBuilder(mode="raid")` |
| 4.2 | Ostacoli telegrafati (corrente, piattaforma, sentinella) | `Catalog/Defenses`, `ModuleModel` (particelle, fasci) |
| 4.2 | Errore → checkpoint, nessun combattimento | `teleportToCheckpoint` |
| 4.2 | Nessuna attesa che il proprietario sia online | `PoolStore` istantanee + inbox |
| 4.2 | Bonus difesa dal sistema, consolazione, riepilogo | `ApplyDefend`, `ApplyLoss`, `History` |
| 4.2 | ≤ 25%, 2 perdite/30', scudo, protezione iniziale, no bersagli ripetuti, nessuna identità | `Config.Raid`, `RequestTargets`, `ApplyLoss`, nomi "Vivaio rivale · fascia N" |
| 4.3 | 6 slot (3/2/1), budget energia, griglia, percorso completabile | `LayoutValidator` |
| 4.3 | Prova gratuita, anteprima percorso, copia layout precedente | `StartTest`, `BuildController.refreshPath`, `RestoreLastValid` |
| 4.3 | Alternative tattiche, ultimo layout valido resta attivo | `Defenses.Alternatives`, `DefenseService.SaveLayout` |
| 4.4 | 3 commissioni, categorie diverse, una sostituzione gratis, nessuna richiede furto | `CommissionService`, `Catalog/Commissions` |
| 4.4 | Album con traguardi e decorazioni permanenti | `Catalog/Album`, `AlbumService` |
| 4.4 | Galleria con moderazione testo (solo DisplayName), profilo nascondibile, like senza effetti | `GalleryService`, `Settings.HideProfile/ShowName` |
| 5 | Tre valute; frammenti non acquistabili; bozzoli deterministici | `CocoonService.Preview/Begin` |
| 5 | Esempio numerico (10/30 s, 300, 180, 1.200) | `Config` + `scripts/simulate_economy.luau` |
| 6 | Solo cosmetici, prezzi chiari, pass trasparente, fondatore senza vantaggi | `Catalog/Cosmetics`, `ShopService`, `ShopPanel` (nota etica) |
| 7 | Tutorial 5 passi, saltabile dopo la prima volta, 2 decorazioni gratuite | `TutorialService`, `TutorialController` |
| 7 | Tema settimanale con sfida facoltativa | `Catalog/Themes`, `ThemeService` |
| 7 | Codici layout, visite con tetto, nessun obbligo di invito | `GalleryService.ImportCode`, `Config.Gallery` |
| 8 | Validità layout, salvataggi resilienti, anti-exploit, rate limit, anti-dup, interruzioni | `LayoutValidator`, `DataService`, `RateLimiter`, `Ledger`, `BindToClose`, `Abort` |
| 8 | Metriche | `AnalyticsService` (tutorial, prima azione, raid, abbandono dopo perdita) |
| 9 | Performance mobile | LOD in `WorldAnimator`, `Decorations.MaxPlaced`, effetti ridotti |
| 9 | Nessuna schermata commerciale dopo una sconfitta | il riepilogo raid non contiene offerte |

## Scelte progettuali dove il GDD lasciava margine
- **Bottino dell'attaccante nelle scintille esposte**: il raid riuscito produce a sua volta rischio (va depositato), coerente con il ritmo "esponi e proteggi".
- **Vivai del Guardiano**: cinque layout fissi per tutorial, commissioni e fallback quando non ci sono bersagli idonei. Ricompensa al 60%.
- **Protezione iniziale**: fino a 2 ore di gioco *e* cassaforte di livello 1; termina al primo potenziamento della cassaforte, così un giocatore che progredisce entra nel pool con coscienza.
- **Identità**: nelle incursioni il bersaglio è sempre "Vivaio rivale · fascia N"; in galleria il nome appare solo se il proprietario lo consente.
