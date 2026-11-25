"""Plays the evenings with random, human-like input (headless), drawing as it goes, and fails on any exception.
The autopilot flies a clean line; players point anywhere, at any frame rate. This is the check that finds what the
autopilot never reaches (it found the squall drawing crash at the storm's edge). The pointer wanders, and between
its wanderings it follows the bot off-line, so that every set piece along the route is met.

    python tools/fuzz.py [evenings] [width]       evening k is place k (1-8, then round again);
                                                  prints each evening's 95th-percentile and slowest draw in ms
"""
import os
import random
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame  # noqa: E402

pygame.init()
N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1280
pygame.display.set_mode((W, 720))

from duskward import screens  # noqa: E402
from duskward.app import camera_goal  # noqa: E402
from duskward.autopilot import drive  # noqa: E402
from duskward.evening import Ctrl, Evening  # noqa: E402
from duskward.places import PLACES  # noqa: E402
from duskward.render import Painter  # noqa: E402

painter, screen, every = Painter(W), pygame.Surface((W, 720)), []
for run in range(N):
    r, k = random.Random(run), run % len(PLACES)
    ev = Evening(1 + run, k, (tuple(range(1, 9)), 60) if k else None)
    cam, mx, my, held, wild, frame, done, times = 0.0, W * 0.6, 300.0, False, False, 0, 0.0, []
    while done < 3 and ev.time < 420:
        if r.random() < 0.004:
            wild = not wild
        if r.random() < 0.03:
            mx, my = (r.uniform(-200, W + 200), r.uniform(-100, 820)) if wild else (r.uniform(-160, 160), r.uniform(-240, 240))
        if r.random() < 0.012:
            held = not held
        dt = r.choice((1 / 30, 1 / 60, 1 / 144))
        bot = drive(ev)
        ev.step(dt, Ctrl(cam + mx, my, held, r.random() < 0.02) if wild
                else Ctrl(bot.tx + mx, bot.ty + my, bot.gather or held, bot.ripple or r.random() < 0.01))
        done += dt * (ev.state == "done")
        cam += (camera_goal(ev, W) - cam) * min(1.0, dt * 2.5)
        if frame % 2 == 0:
            t = time.perf_counter()
            painter.draw(screen, ev, cam, ev.time, hud=ev.state != "done")
            if ev.state == "done":
                screens.summary(painter, screen, ev)
            times.append(time.perf_counter() - t)
        frame += 1
    times.sort()
    every += times
    print(f"{k + 1} {ev.place.name}: {ev.result or ev.state} after {ev.time:.0f}s, {len(ev.flock)} starlings; "
          f"draw p95 {times[int(len(times) * 0.95)] * 1000:.1f} ms, slowest {times[-1] * 1000:.1f} ms")
every.sort()
print(f"draw at {W} wide: p95 {every[int(len(every) * 0.95)] * 1000:.1f} ms, slowest {every[-1] * 1000:.1f} ms, "
      f"{len(every)} frames")
