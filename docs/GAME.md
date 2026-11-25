# Duskward: the game

You steer a whole murmuration of starlings south, one evening at a time, racing the dark to the next roost.

## The story

The night of the first frost, a storm off the sea blows the saltmarsh flock apart. Eight young starlings wake on a
telegraph wire with no elders to follow. A starling in flight tracks about seven neighbours; these eight have exactly
seven each. Every evening they fly to the next roost before the light goes, gathering every stray they pass, with the
Pale Falcon close behind. At midwinter every scattered flock meets at the Long Reeds.

## What makes it a game

1. **The eight.** The first eight birds glint gold in the flock, however large it grows, and each has a name. Strays
   and whole flocks join, but the eight are the ones the story is about: the ending counts how many of them reach the
   Long Reeds. Losing a common bird costs a number. Losing one of the eight costs a name.
2. **Size cuts both ways.** A big flock confuses the falcon (each bird is safer), but it is slow to turn, wide in a
   gap and hungry. A small flock is nimble and exposed.
3. **One button, two meanings.** Hold to gather: the flock pulls into a dark ball, fast and narrow, and it tires.
   Tap to ripple: a wave runs through the birds and a diving falcon loses the one it chose. Point to steer.
4. **Feed low, fly high.** Stamina comes back slowly in the air and fast in the midge swarms low over the fields,
   where the strays are and where the hedges, wires and roofs are too.
5. **Scattered, not dead.** A squall, a rocket, a blade or the fog scatters birds; they land behind you and call. Go
   back for them and lose light, or leave them. Only the falcon and the cold kill.
6. **The falcon learns.** It takes the bird furthest from the flock. A tight flock makes it miss; a ripple at the
   right moment always does. From the Hop Gardens on it feints: it pulls up, waits, and stoops again. On the cliffs
   it comes out of the sun, with its mate. Nothing stoops on a bird under a bridge or a sea arch.
7. **Flocks join by dancing.** Each roost holds a flock of its own. It dances a shape over the roost; you dance it
   back with your whole flock. The closer you follow, the more of them join you: the biggest growth of each evening.
8. **The sun is the clock.** Each evening runs from golden hour to dark, about three minutes. Reach the roost before
   night or sleep in the open and lose birds to the cold.
9. **The flock carries over.** The eight who reach a roost, and the nearest of the flock around them, set out
   together the next evening. The rest follow south as the great flock, and are waiting at the Long Reeds.

## Eight evenings south

| Evening | Place | What it adds |
| --- | --- | --- |
| 1 | The Saltmarsh | First frost. Steering, strays, midges, wind streams, a squall to slip under, the falcon once, the first dance |
| 2 | Hop Gardens | Hop poles and wirework to slip under, gathered tight; strays in the bines; the falcon feints |
| 3 | Market Town | Bonfire night: a rocket's climb is the warning, its burst scatters a loose flock; warm air over the roofs lifts a flock that spreads |
| 4 | The Wind Farm | Turning blades; a river of wind runs between them, under the tips |
| 5 | Estuary Fog | In a fog bank a bird that drifts from the flock is lost: stay gathered, and follow the calls of the lost |
| 6 | City of Bridges | Bridges to fly under, where the falcon cannot follow; gulls over the open water, turned away by a ripple |
| 7 | Chalk Cliffs | The falcon's own country: open water between sea arches, and two falcons out of the sun |
| 8 | The Long Reeds | Midwinter, snow on the wind: every flock you passed dances one last shape together, and the eight are counted |

Three feathers an evening: reach the roost before dark, lose none of the eight, bring enough starlings home.

## How it is made

Python and pygame-ce: a window for Windows, macOS and Linux, and the same code in the browser (pygbag). Every bird,
sky and field is drawn by code; the only files are two OFL fonts and sounds synthesised by `tools/make_sounds.py`.
The flock costs the same per bird for 8 or 800: each step sums the birds per grid cell once and every bird reads the
3x3 cells around it.

| File | What it holds |
| --- | --- |
| `duskward/places.py` | The eight places as data: route, weather, dangers, light, words |
| `duskward/evening.py`, `setpieces.py`, `falcon.py`, `flock.py` | The rules. They never draw |
| `duskward/journey.py` | The journey and its save, checked field by field when it is read |
| `duskward/render.py`, `scenery.py`, `screens.py` | The painter: the scene, what each place holds, and the words around the flying |
| `duskward/audio.py` | The score, which follows the light, the place and the flock |
| `duskward/autopilot.py` | A bot that flies every evening: the tests and `tools/sim.py` use it |
| `tools/` | The checks: `test_local.sh` runs them all |
