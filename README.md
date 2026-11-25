# Duskward

You are the whole flock. A one-button game about a murmuration of starlings flying south, one evening at a time,
racing the dark to the next roost.

The night of the first frost, a storm off the sea blows the saltmarsh flock apart. Eight young starlings wake on a
telegraph wire with no elders left to follow. Eight evenings later, at midwinter, every scattered flock meets at the
Long Reeds. How many of the eight are still with you is the ending.

Everything on screen is drawn by the game's code, and every sound is synthesised: there are no image or audio
recordings in this repository. [docs/GAME.md](docs/GAME.md) holds the full idea.

## The eight evenings

| Evening | Place | What it adds |
| --- | --- | --- |
| 1 | The Saltmarsh | Steering, strays, midges, a squall to slip under, the falcon, the first dance |
| 2 | Hop Gardens | Wirework to slip under, gathered tight; the falcon stoops twice |
| 3 | Market Town | Bonfire night: rockets scatter a loose flock, warm air over the roofs lifts a wide one |
| 4 | The Wind Farm | Turning blades, and a river of wind between them |
| 5 | Estuary Fog | Birds that drift apart in the fog are lost: stay gathered, follow the calls |
| 6 | City of Bridges | Bridges to fly under, where no falcon follows; gulls that a ripple turns away |
| 7 | Chalk Cliffs | Open water between sea arches; two falcons, out of the sun |
| 8 | The Long Reeds | Midwinter and snow: every flock dances together, and the eight are counted |

## Play

The [latest release](https://github.com/makavli/duskward/releases/latest) has `Duskward.exe` for Windows (one file,
nothing to install) and `Duskward-web.zip`, the browser version. The exe is not signed, so Windows may warn about an
unknown publisher; its SHA-256 is in the release notes.

From the source, with Python 3.13:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # .venv/bin/python on macOS and Linux
.venv/Scripts/python tools/make_sounds.py                   # writes the sounds, once
.venv/Scripts/python run.py
```

| Do | Mouse | Keys | Pad |
| --- | --- | --- | --- |
| Steer | point | arrows or WASD | left stick |
| Gather (tighter, faster, tiring) | hold left button | hold Space | hold A |
| Ripple (a wave through the flock that confuses a falcon or a gull) | tap left button, or right button | tap Space, or E | tap A, or X |
| Pause | Esc | Esc | Start |

F11 is full screen, M mutes. While paused, R begins the evening again and Q goes back to the journey.

Fly through the golden midge swarms low over the fields to get your breath back; ride the wind streams up high to fly
faster; fly close to calling starlings to bring them along. Follow a wild flock's trail through its marks and more of
it joins you. At each roost a flock dances a shape: dance it back, and the closer you follow, the more of them join.

## The journey

Between evenings the journey's map shows the road south. Choose an evening with the pointer or the left and right
keys, and click or press Space to fly it.

- **The eight** have names, and glint gold in the flock. One taken by a falcon, left behind in the fog or lost to the
  cold is gone for the rest of the journey. The flock you bring to a roost sets out with you the next evening.
- **Feathers**: three an evening, 24 in all. Reach the roost before dark; lose none of the eight; bring enough
  starlings home.
- **Flying an evening again**: the latest evening is flown again from the same dusk, and the new night replaces the
  old one. Earlier evenings can be flown again for their feathers.
- **A new journey**: press N twice on the map. The old one is forgotten.

The journey is saved after every evening: on Windows in `%APPDATA%\duskward\Duskward\journey.json`, on macOS and
Linux in your user's application-data folder, and in the browser in the page's local storage. Set `DUSKWARD_SAVE` to
a file path to keep it somewhere else.

## Check

```bash
bash tools/test_local.sh            # unit tests, the whole journey by the autopilot, random input, screenshots, a window
bash tools/test_local.sh --exe      # ...and the Windows exe
bash tools/test_local.sh --web      # ...and the browser version, played in headless Chrome
bash tools/web_build.sh --serve     # the browser version on http://localhost:8000
.venv/Scripts/python tools/sim.py 1 3    # one evening by the autopilot, headless: seed 1, evening 3
.venv/Scripts/python tools/sim.py all    # the whole journey by the autopilot
.venv/Scripts/python tools/shots.py 5    # evening 5 as a sheet of screenshots, in shots/
```

`DUSKWARD_AUTOPILOT=1 python run.py` lets the autopilot fly, from evening `DUSKWARD_PLACE` (1 to 8) on, without
touching your save; `DUSKWARD_SEED=<n>` picks another country. In the browser, `index.html#bot8` does the same.

## Licence

The source is public to read, to build and to play. It is not open source: all rights are reserved. See
[LICENSE](LICENSE).

## Credits

See [CREDITS.md](CREDITS.md).
