#!/bin/bash
# Rebuilds every fighter animation from the character sources: moves for both fighters, then all four throws against
# both victims (mirror matches included). Output: $EH_WS/sourceart/anims/<char>/ (+ victim_<char>/), review sheets.
# Usage: Tools/Blender/anim/build_all.sh [--review]
set -euo pipefail
WS="/media/cinqic/Cinqic Storage/EbonyHearts-Slice-20261102"
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
REVIEW="${1:-}"
declare -A H=( [wren]=1.78 [ashka]=1.70 )
for c in wren ashka; do
  C="${c^}"
  "$WS/bin/blender.sh" anim "$HERE/build_anims.py" -- --blend "$WS/sourceart/characters/$c/$C.blend" --char "$c" \
    --data "$REPO/Content/Data/Fighters/$c.json" --out "$WS/sourceart/anims/$c" --height "${H[$c]}" $REVIEW
  for v in wren ashka; do
    V="${v^}"
    SKIP=""; [ "$v" = "ashka" ] && SKIP="--skip-attacker"
    TMPDIR="$WS/tmp" "$WS/bin/blender.sh" anim "$HERE/build_anims.py" -- --blend "$WS/sourceart/characters/$c/$C.blend" --char "$c" \
      --data "$REPO/Content/Data/Fighters/$c.json" --out "$WS/sourceart/anims/$c" --height "${H[$c]}" \
      --victim-blend "$WS/sourceart/characters/$v/$V.blend" --victim-char "$v" --victim-height "${H[$v]}" $SKIP $REVIEW
  done
done
if [ -n "$REVIEW" ]; then
  for c in wren ashka; do python3 "$HERE/contact_sheets.py" "$WS/sourceart/anims/$c/review"; done
fi
echo "build_all done"
