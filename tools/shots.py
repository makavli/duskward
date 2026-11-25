"""Renders the game to contact sheets, headless: the bot flies an evening and the painter is caught at its moments.
    python tools/shots.py [what] [width]
what: a place 1-8 (shots/place3.png), "screens" (title, journey, pause, ending: shots/screens.png), or "all" (default).
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame  # noqa: E402

pygame.init()
WHAT = sys.argv[1] if len(sys.argv) > 1 else "all"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1280
pygame.display.set_mode((W, 720))

from duskward import screens  # noqa: E402
from duskward.app import camera_goal, title_evening, title_step  # noqa: E402
from duskward.autopilot import drive  # noqa: E402
from duskward.evening import Evening  # noqa: E402
from duskward.journey import Journey  # noqa: E402
from duskward.places import PLACES  # noqa: E402
from duskward.render import Painter  # noqa: E402
from duskward.settings import H, STEP  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "shots")
os.makedirs(OUT, exist_ok=True)
p, s = Painter(W), pygame.Surface((W, H))
EVERY = 14.0                                   # a frame this often, between the moments

MOMENTS = {                                    # name -> is this the frame? (ev, cam)
    "burst": lambda ev, cam: any(f[0] == "burst" and 0.15 < ev.time - f[3] < 0.5 and 150 < f[1] - cam < W - 150 for f in ev.fx),
    "stoop": lambda ev, cam: any(f.state == "stoop" and f.distance() < 260 for f in ev.falcons),
    "fog": lambda ev, cam: ev.fog > 0.95,
    "gull": lambda ev, cam: any(g.gull and 200 < g.gull[0] - cam < W - 200 for g in ev.gulls),
    "shelter": lambda ev, cam: ev.shelter,
    "blades": lambda ev, cam: any(abs(tb.x - cam - W * 0.5) < 30 for tb in ev.turbines),
    "thermal": lambda ev, cam: any(th.inside for th in ev.thermals),
    "squall": lambda ev, cam: any(sq.a + 400 < ev.flock.centre()[0] < sq.b for sq in ev.squalls),
    "trail": lambda ev, cam: any(c.state == "lead" and c.next >= 2 for c in ev.courses),
    "balloon": lambda ev, cam: bool(ev.balloon and ev.balloon.riders and abs(ev.balloon.x - cam - W * 0.6) < 40),
    "bang": lambda ev, cam: any(0.05 < ev.time - sc.fired < 0.2 and 0 < sc.x - cam < W for sc in ev.scarers),
    "watch": lambda ev, cam: ev.state == "watch" and ev.state_t > 4,
    "echo": lambda ev, cam: ev.state == "echo" and ev.state_t > 5,
    "free": lambda ev, cam: ev.state == "free" and ev.state_t > 7,
    "settle": lambda ev, cam: ev.state == "settle" and ev.state_t > 3,
}


def sheet(name, pics, cols=4):
    """pics: [(label, surface)] -> shots/name.png"""
    sw, sh = 480, 480 * H // W
    out = pygame.Surface((cols * sw, ((len(pics) + cols - 1) // cols) * sh))
    for i, (label, pic) in enumerate(pics):
        tile = pygame.transform.smoothscale(pic, (sw, sh))
        p.write(tile, label, "small", (8, sh - 30))
        out.blit(tile, ((i % cols) * sw, (i // cols) * sh))
    pygame.image.save(out, os.path.join(OUT, name + ".png"))
    print(name, len(pics), "shots:", " ".join(label for label, _ in pics))


def fly(k):
    """Evening k by the bot -> ([(label, picture)], the evening as it ended)."""
    ev = Evening(1 + k, k, (tuple(range(1, 9)), 60) if k else None)
    cam, pics, taken, next_at, done_at = 0.0, [], set(), 3.0, None
    while ev.time < 400:
        ev.step(STEP, drive(ev))
        cam += (camera_goal(ev, W) - cam) * min(1.0, STEP * 2.5)
        due = [n for n, hit in MOMENTS.items() if n not in taken and hit(ev, cam)][:1]
        if ev.state == "fly" and ev.time >= next_at:
            due, next_at = due or [f"{ev.time:.0f}s"], next_at + EVERY
        for name in due:
            taken.add(name)
            p.draw(s, ev, cam, ev.time)
            pics.append((name, s.copy()))
        if ev.state == "done":
            done_at = done_at or ev.time
            if ev.time > done_at + 3:
                p.draw(s, ev, cam, ev.time, hud=False)
                pics.append(("roost", s.copy()))
                screens.summary(p, s, ev)
                pics.append(("summary", s.copy()))
                break
    return pics, ev, cam


def the_screens():
    pics = []
    ev, deco = title_evening(1, W)
    for f in range(150):
        title_step(deco, ev, W, f * STEP, STEP)
    screens.title(p, s, ev, deco, 2.5)
    pics.append(("title", s.copy()))
    night = lambda eight, fates, feathers, great: {  # noqa: E731
        "result": "roost", "eight": eight, "commons": 150, "great": great, "feathers": feathers, "fates": fates}
    jn = Journey([night([1, 2, 3, 4, 5, 6, 7, 8], {}, [True, True, True], 230),
                  night([1, 2, 4, 5, 6, 7, 8], {"3": "falcon"}, [True, False, True], 480),
                  night([1, 2, 4, 5, 7, 8], {"6": "behind"}, [True, False, False], 690)], keep=False)
    for pick, sure in ((3, False), (1, True)):
        screens.journey(p, s, title_evening(1, W, pick)[0], jn, pick, 0.5, sure)
        pics.append((f"journey, evening {pick + 1}", s.copy()))
    screens.journey(p, s, title_evening(1, W)[0], Journey(keep=False), 0, 0.5)
    pics.append(("a new journey", s.copy()))
    ev = Evening(8, 7, jn.carry(3))
    for _ in range(600):
        ev.step(STEP, drive(ev))
    p.draw(s, ev, camera_goal(ev, W), ev.time)
    screens.paused(p, s)
    pics.append(("paused", s.copy()))
    ev.light, ev.fates = 0.97, {8: "cold"}
    ev.finish("roost")
    jn.nights += [night([1, 2, 4, 5, 7, 8], {}, [True, True, False], 900 + 200 * k) for k in range(4)]
    jn.nights.append(night([1, 2, 4, 5, 7], {"8": "cold"}, [True, False, True], 1900))
    cam = camera_goal(ev, W)
    p.draw(s, ev, cam, 1.0, hud=False)
    screens.summary(p, s, ev, jn)
    pics.append(("summary, the last evening", s.copy()))
    screens.ending(p, s, ev, jn, cam, 0.5)
    pics.append(("ending", s.copy()))
    sheet("screens", pics, 3)


for k in range(len(PLACES)):
    if WHAT in ("all", str(k + 1)):
        sheet(f"place{k + 1}", fly(k)[0])
if WHAT in ("all", "screens"):
    the_screens()
