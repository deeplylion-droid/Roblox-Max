#!/bin/bash
# I render finali del mondo e della barca con l'atmosfera (vedi docs/ATMOSFERA.md), in una cartella a parte che
# parte dagli asset attuali: public/ non si tocca. Il mare nella nebbia vuole più campioni (la grana sull'acqua):
# 256 al massimo con una soglia adattiva più bassa, così il cielo e la costa si fermano prima.
#   tools/render/finale_atmosfera.sh [job...]   (predefiniti: world boat)
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$ROOT/tools/render/cache/atmosfera_out
PUB=$ROOT/public/assets/img
jobs=("$@")
[ ${#jobs[@]} -eq 0 ] && jobs=(world boat)
if [ ! -d "$OUT" ]; then mkdir -p "$OUT" && cp -a "$PUB"/. "$OUT"/; fi
for j in "${jobs[@]}"; do
  echo "== $(date +%H:%M) $j"
  ATMOSFERA=1 CAMPIONI=${CAMPIONI:-256} SOGLIA=${SOGLIA:-0.01} RENDER_OUT=$OUT nice -n 15 \
    "$ROOT/tools/.venv/bin/python" "$ROOT/tools/render/jobs.py" "$j" --quality final
  echo "EXIT $j $?"
done
echo "== $(date +%H:%M) FINE"
