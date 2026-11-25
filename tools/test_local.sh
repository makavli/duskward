#!/usr/bin/env bash
# Every check, on this machine, before every push.
#   bash tools/test_local.sh          unit tests, the whole journey by the autopilot, random input, screenshots, a window
#   bash tools/test_local.sh --quick  unit tests only
#   bash tools/test_local.sh --exe    ...and build the Windows exe and start it for a few seconds
#   bash tools/test_local.sh --web    ...and build the browser version and play it in headless Chrome
#   bash tools/test_local.sh --exe --web   both, as before a release
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .venv/Scripts/python.exe ]]; then PY=.venv/Scripts/python; else PY=.venv/bin/python; fi
step() { echo; echo "==> $*"; }
fail() { echo "FAILED: $*"; exit 1; }
log=$(mktemp)
trap 'rm -f "$log" "$log".*' EXIT
quiet() { "$@" >"$log" 2>&1 || { tail -n 25 "$log"; return 1; }; }      # the tail of the output, only when it fails

[[ -f duskward/sounds/wing.wav ]] || "$PY" tools/make_sounds.py >/dev/null

step "1. Version, and unit tests (headless)"
"$PY" tools/version_check.py || fail "version"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy quiet "$PY" -m unittest -q || fail "unit tests"
tail -n 3 "$log"
[[ "${1:-}" == "--quick" ]] && { echo "Quick tests passed."; exit 0; }

step "2. The autopilot flies the whole journey, twice (every evening must end at its roost)"
pids=()
for seed in 1 11; do "$PY" tools/sim.py all "$seed" >"$log.$seed" 2>&1 & pids+=($!); done
for pid in "${pids[@]}"; do wait "$pid" || { tail -n 12 "$log".1 "$log".11; fail "a journey"; }; done
cut -c1-150 "$log".1 "$log".11

step "3. Random human-like input over all eight evenings, drawn as it goes (must not raise)"
quiet "$PY" tools/fuzz.py 8 || fail "fuzz"
cut -c1-150 "$log"

step "4. Screenshots -> shots/place1.png ... place8.png, shots/screens.png"
pids=()
for what in 1 2 3 4 5 6 7 8 screens; do "$PY" tools/shots.py "$what" >"$log.$what" 2>&1 & pids+=($!); done
for pid in "${pids[@]}"; do wait "$pid" || { tail -n 12 "$log".[1-8] "$log".screens; fail "screenshots"; }; done

step "5. A real window: the title for 180 frames, then the autopilot flies the last evening for 900"
SDL_AUDIODRIVER=dummy DUSKWARD_FRAMES=180 quiet "$PY" run.py || fail "real window, title"
SDL_AUDIODRIVER=dummy DUSKWARD_AUTOPILOT=1 DUSKWARD_PLACE=8 DUSKWARD_FRAMES=900 quiet "$PY" run.py || fail "real window, play"

if [[ " $* " == *" --exe "* ]]; then
    step "6. Windows exe (PyInstaller, one file, as released)"
    "$PY" -m pip install --quiet pyinstaller==6.22.3
    quiet "$PY" -m PyInstaller --noconfirm --clean --windowed --onefile --name Duskward --distpath dist --workpath build/pyi \
        --add-data duskward/sounds:duskward/sounds --add-data duskward/fonts:duskward/fonts run.py || fail "exe build"
    SDL_AUDIODRIVER=dummy DUSKWARD_FRAMES=120 ./dist/Duskward.exe || fail "exe run"
fi
if [[ " $* " == *" --web "* ]]; then
    step "7. Browser build (pygbag), played in headless Chrome: the title, the map, an evening, and the last one by the bot"
    "$PY" -m pip install --quiet pygbag==0.9.3 websocket-client==1.8.0
    quiet bash tools/web_build.sh || fail "web build"
    quiet "$PY" tools/web_check.py 40 || fail "web check"
    tail -n 6 "$log"
fi
echo; echo "All local checks passed."
