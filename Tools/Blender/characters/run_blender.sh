#!/usr/bin/env bash
# Runs Blender headless for the character pipeline with an isolated user-resource folder.
#
#   run_blender.sh <script.py> [script args...]
#
# Every Blender/MPFB user path (extensions, MPFB user data, logs) is redirected into
# <slice>/userdata/blender-chars, so the user's global ~/.config/blender is never touched.
# A lock file serialises runs: only one Blender process of this pipeline runs at a time.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SLICE="$(cd "$HERE/../../../../.." && pwd)"
export BLENDER_USER_RESOURCES="$SLICE/userdata/blender-chars"
export PYTHONDONTWRITEBYTECODE=1
BLENDER="${BLENDER:-/home/cinqic/.local/opt/blender-5.2.2-linux-x64/blender}"
THREADS="${EH_THREADS:-6}"
mkdir -p "$BLENDER_USER_RESOURCES"
script="$1"; shift
exec 9>"$BLENDER_USER_RESOURCES/.run.lock"
flock 9
exec "$BLENDER" --background --factory-startup -t "$THREADS" --python-exit-code 1 \
     --python "$script" -- "$@"
