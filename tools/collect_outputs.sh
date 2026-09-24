#!/usr/bin/env bash
# Move the three Colab downloads into the repo root.
# Run after the notebook finishes:  bash tools/collect_outputs.sh
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-$HOME/Downloads}"
found=0
for f in evaluation_results.json test_predictions.csv confusion_matrix.png; do
  # Colab re-downloads land as "name (1).ext"; take the newest match.
  newest=$(ls -t "$SRC/$f" "$SRC/${f%.*} ("*")".${f##*.} 2>/dev/null | head -1)
  if [ -n "$newest" ] && [ -f "$newest" ]; then
    mv "$newest" "$REPO/$f" && echo "  ok   $f" && found=$((found+1))
  else
    echo "  MISS $f  (not in $SRC)"
  fi
done
echo
echo "$found/3 collected into $REPO"
[ "$found" -eq 3 ] || echo "Re-download the missing ones from the Colab Files panel."
