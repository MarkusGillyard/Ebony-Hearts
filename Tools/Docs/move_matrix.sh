#!/bin/bash
# Builds the move interaction matrix tool against the combat core and writes its tables into Docs/MoveMatrix.md
# (between the move-matrix markers). Usage: Tools/Docs/move_matrix.sh [build dir]
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$REPO/../build-move-matrix}"
mkdir -p "$OUT"
CORE="$REPO/Source/EbonyHearts/Core"
g++ -std=c++20 -O2 -Wall -Wextra -Werror -fno-exceptions -fno-rtti -I"$CORE" "$CORE"/EHJson.cpp "$CORE"/EHCombatData.cpp "$CORE"/EHMatch.cpp \
  "$REPO/Tools/Docs/move_matrix.cpp" -o "$OUT/move_matrix"
"$OUT/move_matrix" "$REPO/Content/Data" > "$OUT/matrix.md"
python3 - "$REPO/Docs/MoveMatrix.md" "$OUT/matrix.md" <<'PY'
import sys
doc, gen = sys.argv[1], open(sys.argv[2]).read()
text = open(doc).read()
a, b = "<!-- move-matrix:begin -->", "<!-- move-matrix:end -->"
text = text[:text.index(a)] + gen.strip() + text[text.index(b) + len(b):]
open(doc, "w").write(text)
print("updated", doc)
PY
