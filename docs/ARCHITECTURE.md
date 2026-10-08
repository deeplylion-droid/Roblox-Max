# Architettura

## Principi
- **Server autorevole**: ogni modifica a scintille, frammenti, creature, layout ed esiti dei raid avviene solo nei servizi server. Il client invia intenzioni (remoti) e riceve lo stato.
- **Un solo posto per i numeri**: `src/Shared/Config.luau`. Testi in `Strings.luau`, palette in `Theme.luau`.
- **Logica condivisa dove serve coerenza**: `LayoutValidator` è usato dal client per l'anteprima e dal server per la pubblicazione, così ciò che il giocatore vede valido lo è davvero.
- **Grafica procedurale su mesh di qualità**: `Shared/Models/*` costruisce creature, moduli, decorazioni e l'intero vivaio componendo MeshPart ad alta risoluzione (template in `ReplicatedStorage.MeshTemplates`, caricati da `Server/World/MeshLibrary`) con parti primitive per i dettagli (occhi, luci, zone). Ogni uso di mesh ha un fallback a primitive, così il place resta giocabile anche senza accesso agli asset. Gli stessi costruttori alimentano i ViewportFrame della UI.
- **Pipeline asset riproducibile**: `tools/meshgen/generate.py` genera le mesh (icosfere suddivise, superfici di rivoluzione, tori, rumore frattale, gaussiane direzionali per i cumuli) e le anteprime; `upload.py` le carica via Open Cloud e aggiorna il catalogo `MeshAssets.luau`.

## Server (`src/Server`)
`Main.server.luau` precarica le mesh (`World/MeshLibrary`, timeout 25 s), costruisce il mondo (`World/WorldBuilder`) e avvia i servizi nell'ordine: `Init` di tutti (collegano i remoti), poi `Start` (loop e listener). I servizi comunicano tramite `Registry` (niente require circolari) ed `EventBus` (eventi di dominio: `SparksCollected`, `RaidCompleted`, `CreatureUnlocked`, …).

| Servizio | Responsabilità |
|---|---|
| `DataService` | Profili su DataStore con lock di sessione, retry/backoff, autosave, riconciliazione col template, migrazioni, `BindToClose`. Fallback in memoria in Studio senza API. |
| `PlayerService` | Replica coalescente dello stato al client (`StateSync`), toast, suoni, tempo di gioco, impostazioni. |
| `EconomyService` | Produzione a tick, buffer per creatura, rendimento decrescente, riserva offline, ritiro/deposito/auto-deposito, potenziamenti, sblocco moduli, posizionamento creature e decorazioni, fascia di progressione. |
| `PlotService` | Assegna le 12 isole, costruisce il vivaio dal profilo, teletrasporti hub↔vivaio, prompt, caduta dal bordo. |
| `DefenseService` | Pubblicazione layout (validatore + sanificazione), ultimo layout valido, alternative tattiche, prova locale. |
| `RaidService` | Matchmaking, arena istanziata, simulazione ostacoli a 60 Hz, checkpoint, esiti, scudi, inbox per difensori offline, anti-exploit leggero. |
| `PoolStore` | Istantanee dei vivai per fascia (DataStore) condivise tra server: bersagli, galleria, codici; inbox degli esiti. |
| `GalleryService` | Pubblicazione istantanee, galleria, visite (plot live o copia istanziata), «mi piace», import codici. |
| `CommissionService` | 3 commissioni giornaliere deterministiche, sostituzione gratuita, riscossione idempotente. |
| `StatsService` | Contatori giornalieri/settimanali derivati dagli eventi. |
| `AlbumService` | Traguardi album, tre tracce di maestria, varianti cromatiche, deposito automatico. |
| `CocoonService` | Bozzoli deterministici con obiettivo di sblocco. |
| `ShopService` | Cosmetici con gettoni, Robux opzionali (`ProcessReceipt` idempotente), Pass, fondatore, emote. |
| `TutorialService` | 5 passi guidati dagli eventi reali, decorazione gratuita, replay/skip. |
| `ThemeService` | Tema settimanale e sfida facoltativa. |
| `AnalyticsService` | Metriche del GDD §8 via `AnalyticsService` di Roblox (pcall). |

### Flusso di un'incursione
1. `RequestRaidTargets`: candidati dai bucket di fascia ±1, filtrati (scudo, 2 perdite/30', protezione nuovi, già colpiti, esposte < 40), ordinati per difficoltà adatta al tasso di successo. Sempre almeno un Vivaio del Guardiano.
2. `StartRaid(key)`: ricontrollo fresco del bersaglio, arena da `ArenaPool`, `PlotBuilder` in modalità `raid`, teletrasporto, conto alla rovescia.
3. Loop `Heartbeat`: sentinelle (cono orientato da `ModuleModel.OrientSentinel`), piattaforme (CFrame + velocità per trasportare il personaggio), correnti pulsanti, campana, ponte, faro, cadute, anomalie di velocità, pozza raggiunta, uscita.
4. `finish`: bottino = min(25% esposte attuali, tetto di fascia); attaccante riceve scintille **esposte**; difensore online → applicazione diretta, offline → `PushInbox` + aggiornamento istantanea (scudo, finestra perdite). Riepilogo senza identità a entrambi.

### Persistenza e sicurezza
- Lock di sessione con timeout 120 s; un profilo bloccato altrove non viene mai sovrascritto.
- `Ledger` per ricompense (commissioni, tutorial, ricevute Robux) e `AppliedInbox` per gli esiti raid: idempotenza.
- `RateLimiter` a token bucket su ogni remoto sensibile; `Guard` valida tipi e intervalli.
- `Logger.Audit` registra spese, premi, pubblicazioni e esiti raid per rollback mirati.

## Client (`src/Client`)
- `Controllers/State`: cache dello stato replicato + `Observe(key)`.
- `UI/UI`: costruttore con tema (pulsanti grandi, pannelli modali, progress bar con testo, toggle "Attivo/Spento", viewport 3D rotanti, tab).
- `UI/HUD`: le quattro informazioni, valute, menu, azioni contestuali, scorciatoie.
- `Controllers/BuildController`: griglia, fantasma, rotazione, anteprima percorso, layout di lavoro, pubblicazione.
- `Controllers/RaidController`: spinta delle correnti e trampolini sul personaggio (di proprietà del client), nebbia locale.
- `Controllers/WorldAnimator`: animazioni cosmetiche con LOD e modalità effetti ridotti.
- `Controllers/Visuals`: scie, targhette, emote, cielo/tema, scintille che volano verso l'HUD.
- Pannelli: Build, Commission, Album, Cocoon, Gallery, Shop, Settings, Raid, Demo; `TutorialController` con banner e beacon.

## Griglia del vivaio
12×12 celle da 4 stud. Ingresso (riga 0), pozza (centro 2×2), uscita (riga 11) sono riservate. Cassaforte, pad di spawn e pad verso l'hub stanno sul margine. Le celle con moduli "a vuoto" (piattaforma, ponte) sono calpestabili a casa e non in arena.
