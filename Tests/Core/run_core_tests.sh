#!/bin/bash
# Builds and runs the engine-independent combat core tests with strict warnings.
# Usage: Tests/Core/run_core_tests.sh [output-dir]   (defaults to a build folder beside the repository)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$REPO/../build-core-tests}"
mkdir -p "$OUT"
CORE="$REPO/Source/EbonyHearts/Core"
g++ -std=c++20 -O2 -g -Wall -Wextra -Wshadow -Wconversion -Wno-sign-conversion -Werror -fno-exceptions -fno-rtti \
  -I"$CORE" "$CORE"/EHJson.cpp "$CORE"/EHCombatData.cpp "$CORE"/EHMatch.cpp "$CORE"/EHAI.cpp \
  "$REPO/Tests/Core/CoreTests.cpp" -o "$OUT/core_tests"
"$OUT/core_tests" "$REPO/Content/Data"
