# Il Vivaio delle Nuvole · Roblox

Implementazione completa del GDD **«Il Vivaio delle Nuvole» v1.0**: social collection, base defense leggera e incursioni asincrone istanziate. Tutto il gioco è costruito via codice (Luau). La grafica usa **35 mesh ad alta risoluzione** (fino a 7.000 triangoli ciascuna, normali smooth) generate dalla pipeline in `tools/meshgen/` e caricate su Roblox via Open Cloud; se una mesh non è disponibile il gioco ripiega automaticamente su primitive, quindi il place funziona sempre.

## Avvio rapido

**Opzione A – place già costruito**
1. Apri `build/IlVivaioDelleNuvole.rbxlx` in Roblox Studio.
2. In *Game Settings → Security* attiva **Enable Studio Access to API Services** (serve a DataStore: senza, il gioco funziona ma avvisa che i progressi non vengono salvati).
3. Premi **Play**. Il tutorial parte da solo.

**Opzione B – sviluppo con Rojo** (consigliata per modificare il codice)
```bash
rokit install          # installa rojo e luau-lsp (vedi rokit.toml)
rojo serve             # poi "Connect" dal plugin Rojo in Studio
# oppure
rojo build -o build/IlVivaioDelleNuvole.rbxlx
```

**Opzione C – pubblicazione via Open Cloud** (l'esperienza di test è "Cloud Garden", universe `10769836705`, place `103319589301496`)
```bash
python3 tools/publish.py --universe 10769836705 --place 103319589301496   # build + publish
```

**Test e simulazione economica** (richiede il CLI `luau`):
```bash
python3 scripts/run_tests.py            # 85 test sui moduli condivisi + simulazione del bilanciamento
```

## Cosa c'è dentro

| Area GDD | Implementazione |
|---|---|
| §2 Hub e interfaccia | Isola hub con Albero delle Nuvole, portale incursioni, bacheca, galleria, bottega, vivaio dimostrativo. HUD con **le 4 informazioni fisse** (scintille da depositare, cassaforte, protezione, prossimo obiettivo), pulsanti grandi, testo oltre al colore, audio disattivabile, effetti riducibili, mobile-first. |
| §4.1 Creature | **16 Nimbini** (4 famiglie × 4) con silhouette procedurali, comportamenti (bob/hop/orbit/drift), 4 varianti cromatiche per creatura; produzione a intervalli, buffer per creatura, rendimento marginale decrescente oltre la 6ª, riserva offline con tetto, deposito manuale e automatico (sbloccabile). |
| §4.2 Incursioni | Matchmaking asincrono per fascia/difficoltà/tasso di successo, copia istanziata del layout in arena, 90 s, ostacoli simulati dal server (sentinelle, piattaforme, campana, ponte, faro), checkpoint, bottino ≤ 25% e ≤ tetto di fascia, 2 perdite max / 30 min, scudo automatico 20 min, protezione nuovi giocatori, no raid ripetuti, nessuna identità mostrata, bonus difesa finanziato dal sistema e consolazione, **inbox per proprietari offline**, 5 Vivai del Guardiano simulati. |
| §4.3 Difesa | 6 slot (3 ostacoli, 2 distrazioni, 1 firma), budget energia 100, griglia 12×12, **validatore condiviso client/server** con BFS ingresso→pozza→uscita, anteprima percorso, prova locale gratuita, ripristino ultimo valido, 10 moduli con **alternative tattiche** sbloccate dalla maestria. |
| §4.4 Commissioni, album, social | 3 commissioni giornaliere da categorie diverse (deterministiche), 1 sostituzione gratis, nessuna richiede di colpire giocatori reali; album con 20 traguardi e decorazioni permanenti; galleria con «mi piace» (senza effetti sulla produzione), visite con ricompensa a tetto basso, profilo nascondibile, **codici layout** condivisibili. |
| §5 Economia | Scintille / frammenti di cielo / gettoni stile; bozzoli **deterministici** con anteprima del percorso; 3 tracce di maestria con tier e premi laterali. Numeri in `src/Shared/Config.luau`. |
| §6 Monetizzazione etica | Solo cosmetici (skin, cieli, scie, emote, targhette), Pass delle Nuvole trasparente senza scadenza, bundle fondatore. ID Robux opzionali in `Config.Monetization` (0 = nascosto). Nulla influisce sul gameplay. |
| §7 Onboarding | Tutorial in 5 passi guidato da eventi reali, saltabile solo dalla seconda volta, scelta tra due decorazioni gratuite; tema settimanale con sfida facoltativa. |
| §8 MVP e sicurezza | Salvataggi con lock di sessione, retry e riconciliazione; tutte le risorse e gli esiti dei raid validati dal server; rate limit sui remoti; ledger idempotente; log di audit; analytics delle metriche del GDD. |

Dettagli: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/GDD_COVERAGE.md`](docs/GDD_COVERAGE.md), [`docs/BALANCE.md`](docs/BALANCE.md).

## Mesh 3D ad alta qualità

| | |
|---|---|
| Generazione | `python3 tools/meshgen/generate.py` → `assets/meshes/*.glb` + anteprime in `assets/previews/` (contact sheet `_contact_sheet.png`) |
| Upload | `python3 tools/meshgen/upload.py --creator <userId>` → crea asset *Model* via Open Cloud Assets API e scrive `src/Shared/Catalog/MeshAssets.luau` |
| Runtime | `Server/World/MeshLibrary` carica gli asset con `InsertService:LoadAsset` e li espone in `ReplicatedStorage.MeshTemplates`; `Shared/Models/MeshUtil` li clona e dimensiona; i costruttori (`CreatureModel`, `ModuleModel`, `DecorationModel`, `PlotBuilder`, `WorldBuilder`) li preferiscono alle primitive |

Gli asset attuali appartengono all'utente Roblox **118377242** (la chiave Open Cloud di questo ambiente). `InsertService` carica un asset solo nei place dello stesso proprietario: se pubblichi il gioco da un altro account o da un gruppo, ri-esegui `upload.py` con il tuo `--creator` (serve una chiave con scope `asset:read` e `asset:write`) e committa il nuovo `MeshAssets.luau`. In Studio senza accesso agli asset vedrai nell'Output quante mesh sono state caricate; le mancanti usano le primitive.

Catalogo: 4 corpi di creatura (sfera solare, goccia, soffio inclinato, ovale d'aurora) + raggi, cappello di nuvola, codina, nastri di vento, archi d'aurora; 3 cumuli, 3 rocce, 2 isole (hub e vivaio), cristallo sfaccettato; colonna, lampada, campana, vasca, cassaforte, anello del portale, arco, lanterna esagonale, palo, cespuglio, tronco, pedana, piedistallo, trampolino, bocchetta, pietra a fungo, aiuola fiorita.

## Controlli

Movimento standard Roblox · **E** interagisci (ProximityPrompt) · **F** raccogli tutto · **G** deposita · **B** costruisci · **R** ruota · **X** modalità modifica · **N** incursione · **C** commissioni · **V** album · **K** bozzoli · **L** galleria · **P** negozio · **O** opzioni · **T** emote. Su mobile tutto è raggiungibile dai pulsanti dell'HUD e dai prompt a schermo.

## Struttura

```
default.project.json      progetto Rojo (Lighting, Workspace, StarterPlayer, ...)
src/Shared/               Config, Strings (it), Theme, cataloghi, LayoutValidator, modelli procedurali
src/Server/               Main + 16 servizi (Data, Player, Economy, Plot, Defense, Raid, Gallery, ...)
src/Client/               Main + controller (Build, Raid, WorldAnimator, Visuals, Tutorial) + UI
src/ReplicatedFirst/      schermata di caricamento
scripts/                  test harness e simulazione economica
tools/meshgen/            generatore di mesh (numpy), esportatore glTF/FBX, upload Open Cloud
assets/meshes, previews/  mesh .glb caricate e anteprime PNG
build/                    place costruito (.rbxlx)
```
