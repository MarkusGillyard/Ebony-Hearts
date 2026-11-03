#!/usr/bin/env bash
# Rebuild The Drowned Chapel from scratch. Extra arguments go to build_chapel.py
# (e.g. --no-render, --skip-textures, --only centre,left_corner).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SLICE="$(cd "$HERE/../../../../.." && pwd)"
BLENDER="${BLENDER:-/home/cinqic/.local/opt/blender-5.2.2-linux-x64/blender}"
export BLENDER_USER_RESOURCES="$SLICE/userdata/blender-chapel"
export PYTHONDONTWRITEBYTECODE=1
export CHAPEL_SLICE_ROOT="$SLICE"
# keep Blender's temp files inside the stage output folder
export TMPDIR="$SLICE/sourceart/chapel/_tmp"
mkdir -p "$BLENDER_USER_RESOURCES" "$TMPDIR"
exec "$BLENDER" --background --factory-startup -t 6 --python "$HERE/build_chapel.py" -- "$@"
