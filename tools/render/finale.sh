#!/bin/bash
# Render finali in alta qualità, preparati in una cartella a parte: la larghezza del panorama è unica per
# tutti gli strati, quindi la cartella pubblica non si tocca finché non sono pronti tutti.
#   tools/render/finale.sh [job...]     rende i job (predefiniti: world boat props creature tarp), a bassa priorità
#   tools/render/finale.sh --installa   copia il risultato in public/assets/img
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$ROOT/tools/render/cache/final_out
PUB=$ROOT/public/assets/img
if [ "${1:-}" = "--installa" ]; then
  cp -a "$OUT"/. "$PUB"/
  echo "installati in $PUB"
  exit 0
fi
jobs=("$@")
[ ${#jobs[@]} -eq 0 ] && jobs=(world boat props creature tarp)
# si parte dagli asset attuali (sovrapposizioni, jumpscare) e i job li sostituiscono uno per uno
if [ ! -d "$OUT" ]; then mkdir -p "$OUT" && cp -a "$PUB"/. "$OUT"/; fi
for j in "${jobs[@]}"; do
  echo "== $(date +%H:%M) $j"
  RENDER_OUT=$OUT nice -n 15 "$ROOT/tools/.venv/bin/python" "$ROOT/tools/render/jobs.py" "$j" --quality final
  echo "EXIT $j $?"
done
echo "== $(date +%H:%M) FINE"
