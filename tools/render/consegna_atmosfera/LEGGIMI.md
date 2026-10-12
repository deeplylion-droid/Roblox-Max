# Consegna: lo strato del mondo con l'atmosfera (12 ottobre)

Il panorama del mondo con la nebbia volumetrica e la baia più buia (vedi docs/ATMOSFERA.md), in qualità finale:
8192×2139, 256 campioni al massimo con la soglia adattiva a 0,01, reso a 16 strisce con
`tools/render/finale_atmosfera.sh world` (ATMOSFERA=1).

- `world_ambient.webp`, `world_lamp.webp`, `world_lantern.webp`: i passi di luce (codifica di post.py, gamma 4 e
  scale nel manifest). Nel passo `lamp` c'è anche l'alone della nebbia, smussato dove è lontano.
- `world_data.webp`: R = mist come prima, sqrt(d / 2500 m), ma ricavato dal passo Depth (il Mist di Cycles si
  accumula nei volumi); G = maschera dell'acqua; B = cielo.
- `manifest.json`: solo le voci `pano` e `layers.world`, da fondere nel manifest del gioco. La barca e i globali
  (write_globals) vengono dal render della barca fatto a parte.

Installazione: copiare i quattro webp in public/assets/img e sostituire `layers.world` (e `pano`, invariato) nel
manifest di public/assets/img/manifest.json.
