#!/usr/bin/env bash
# One-time setup: installs the MPFB 2.0.18 extension and the MakeHuman CC0 system-asset pack into
# <slice>/userdata/blender-chars (never into the user's global Blender config). Idempotent.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SLICE="$(cd "$HERE/../../../../.." && pwd)"
export BLENDER_USER_RESOURCES="$SLICE/userdata/blender-chars"
BLENDER="${BLENDER:-/home/cinqic/.local/opt/blender-5.2.2-linux-x64/blender}"
MH="$SLICE/downloads/thirdparty/MakeHuman/downloads"
ZIP="$MH/mpfb2_addon/add-on-mpfb-v2.0.18.zip"
PACK="$MH/makehuman_system_assets/makehuman_system_assets_cc0.zip"
mkdir -p "$BLENDER_USER_RESOURCES"
if [ ! -f "$BLENDER_USER_RESOURCES/extensions/user_default/mpfb/blender_manifest.toml" ]; then
  "$BLENDER" --factory-startup --command extension install-file -r user_default "$ZIP"
fi
"$HERE/run_blender.sh" "$HERE/setup_mpfb_assets.py" "$PACK"
