"""The autopilot flies an evening, headless, and prints how it went.
    python tools/sim.py [seed] [place 1-8]      one evening (the first by default), setting out as on a new journey
    python tools/sim.py all [seed]              the whole journey, each evening carrying the last one's flock;
                                                exits 1 unless every evening ends at its roost
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from duskward.autopilot import drive  # noqa: E402
from duskward.evening import Evening  # noqa: E402
from duskward.journey import Journey  # noqa: E402
from duskward.places import PLACES  # noqa: E402
from duskward.settings import STEP  # noqa: E402


def run(seed=1, limit=400.0, place=0, carry=None):
    ev = Evening(seed, place, carry)
    worst = 0.0
    while ev.state != "done" and ev.time < limit:
        t = time.perf_counter()
        ev.step(STEP, drive(ev))
        worst = max(worst, time.perf_counter() - t)
    return ev, worst


def line(ev, worst):
    s = ev.stats
    return (f"{ev.index + 1} {ev.place.name}, seed {ev.seed}: {ev.result} after {ev.time:.0f}s (light {ev.light:.2f}, "
            f"at the roost after {s['flown']:.0f}s), "
            f"{len(ev.flock)} starlings from {s['start']}, eight {ev.eight_in_flock}/{len(ev.eight_start)} "
            f"(+{ev.eight_behind} behind); strays {s['strays']}, regathered {s['regathered']}, "
            f"scattered {s['scattered']}, snagged {s['snagged']}, fogged {s['fogged']}, caught {s['caught']}, "
            f"falcon missed {sum(f.missed for f in ev.falcons)}, marks {s['marks']}/{s['mark_total']}, "
            f"dance {s['dance']:.0%}, merged {s['merged']}, cold {s['cold']}; feathers {sum(ev.feathers())}/3; "
            f"slowest step {worst * 1000:.1f} ms")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["all"]:
        seed, journey, ok = int(args[1]) if len(args) > 1 else 1, Journey(keep=False), True
        for k in range(len(PLACES)):
            ev, worst = run(seed + k, place=k, carry=journey.carry(k))
            print(line(ev, worst))
            ok = ok and ev.result == "roost"
            if not journey.record(k, ev):
                break
        print(f"journey: {len(journey.nights)}/8 evenings, great flock {journey.great(len(journey.nights))}, "
              f"feathers {journey.feathers()}/24, the eight home: {len(journey.carry(len(journey.nights))[0])}")
        sys.exit(0 if ok and journey.over else 1)
    seed = int(args[0]) if args else 1
    ev, worst = run(seed, place=int(args[1]) - 1 if len(args) > 1 else 0)
    print(line(ev, worst))
