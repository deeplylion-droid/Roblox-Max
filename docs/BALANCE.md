# Bilanciamento (valori iniziali da testare)

Tutti i numeri sono in `src/Shared/Config.luau`. Risultati di `python3 scripts/run_tests.py`:

| Verifica (GDD §5) | Obiettivo | Risultato |
|---|---|---|
| Primo acquisto significativo (modulo 180 ✦) | 3–5 min | **4,0 min** (1 Lumino + traguardo album + 2 commissioni rapide) |
| Rendimento 12 creature vs 6 | ridotto | **1,74×** invece di 2,9× (−26 %) |
| Recupero dopo due raid, giocatore medio | ≤ 10 min | **1,6 min** (fascia 2); peggior caso fascia 4: 2,7 min |
| Riserva offline | piacevole ma non necessaria | tetto **240 ✦** ≈ 2,8 min di gioco attivo |

## Produzione
- Base: 10 / 13 / 16 / 20 ✦ ogni 30 s per rarità comune / insolita / rara / leggendaria.
- Buffer per creatura: 6 intervalli (3 min) → incentiva il ritiro, evita AFK infinito.
- Fattori oltre la 6ª creatura (ordinate per produzione): 0,5 · 0,5 · 0,35 · 0,35 · 0,25 · 0,25.

## Cassaforte e plot
| Livello | Capienza | Costo | Creature esponibili | Costo |
|---|---|---|---|---|
| 1 | 300 | — | 6 | — |
| 2 | 600 | 250 | 8 | 400 |
| 3 | 1 200 | 600 | 10 | 1 200 |
| 4 | 2 400 | 1 200 | 12 | 2 600 |
| 5 | 4 800 | 2 400 | | |
| 6 | 9 000 | 4 500 | | |

## Incursioni
- 90 s, 25 % delle esposte, tetto per fascia 90 / 180 / 320 / 520 / 800.
- Max 2 perdite effettive per finestra di 30 min; scudo 20 min dopo una perdita; protezione iniziale (2 h di gioco e cassaforte L1).
- Partecipazione 15 ✦ (solo se ≥ 20 s in arena o pozza raggiunta), bonus difesa 45 ✦, consolazione 20 % della perdita (min 5).
- Maestria Incursione: +6 vittoria, +2 sconfitta; Difesa: +5 per incursione respinta, +2 per layout pubblicato.
- Cooldown attaccante 20 s; stesso bersaglio non riproposto per 1 h.

## Difesa
Budget 100. Corrente 20 · Piattaforma 25 · Sentinella 30 · Muro 15 · Faro 15 · Nebbia 20 · Prato di rugiada 15 · Cupola 30 · Campana 25 · Ponte 35.
Sblocchi: corrente e muro di base; piattaforma 180 ✦, sentinella 320 ✦, faro 150 ✦, nebbia 220 ✦, prato 150 ✦; moduli firma e alternative dalla Maestria Difesa (tier a 10 / 30 / 60 / 100 / 160 punti).

## Valute secondarie
- Frammenti: 2–4 per commissione, 3–15 per traguardo album, 3–20 per tier di maestria. Bozzolo = 8 frammenti (≈ una creatura nuova al giorno per chi completa le commissioni).
- Gettoni stile: 5 per commissione, 10 per traguardo, 15 per tier, 25 per sfida settimanale. Cosmetici 30–120 gettoni.

## Regole di iterazione (GDD §8)
Se l'abbandono dopo una perdita cresce → ridurre `MaxTakeFraction`/`TierTakeCaps` o allungare `ShieldAfterLossSeconds` prima di alzare premi. Se la raccolta diventa passiva → nuovi moduli/alternative, non più grind. Se il successo dipende dal dispositivo → ridurre `Speed` delle sentinelle e `Push` delle correnti in `Catalog/Defenses`.
