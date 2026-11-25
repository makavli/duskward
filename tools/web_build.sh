#!/usr/bin/env bash
# Builds the browser version with pygbag into out/Duskward-web.zip (index.html at its root, as itch.io wants).
#   bash tools/web_build.sh           build only
#   bash tools/web_build.sh --serve   build, then serve it on http://localhost:8000 to play locally
set -euo pipefail
cd "$(dirname "$0")/.."
PY=python; [ -x .venv/Scripts/python ] && PY="$PWD/.venv/Scripts/python"; [ -x .venv/bin/python ] && PY="$PWD/.venv/bin/python"
[ -f duskward/sounds/wing.wav ] || "$PY" tools/make_sounds.py >/dev/null
src=build/web-src
rm -rf "$src" && mkdir -p "$src" out
cp web/main.py "$src/"
cp -r duskward "$src/"
find "$src" -name __pycache__ -prune -exec rm -rf {} +
"$PY" -m pygbag --build --ume_block 0 --disable-sound-format-error --title Duskward --app_name duskward "$src"
rm -f out/Duskward-web.zip
(cd "$src/build/web" && "$PY" -m zipfile -c "$OLDPWD/out/Duskward-web.zip" ./*)
ls -la "$src/build/web" out/Duskward-web.zip
if [ "${1:-}" = "--serve" ]; then
    echo "Open http://localhost:8000 (Ctrl+C stops)"
    "$PY" -m http.server 8000 -b 127.0.0.1 -d "$src/build/web"
fi
