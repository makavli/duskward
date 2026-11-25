"""Shared by the evening tests: fly an Evening for a while, or put its flock somewhere."""

from duskward.settings import STEP


def run(ev, steer, seconds):
    end = ev.time + seconds
    while ev.state != "done" and ev.time < end:
        ev.step(STEP, steer(ev))


def move(ev, x, y, extra=0):
    """Puts the flock (plus extra birds) at (x, y) in the air, as if it had flown there."""
    f = ev.flock
    for _ in range(extra):
        f.add(f.x[0], f.y[0], 120, 0)
    cx, cy = f.centre()
    for i in range(len(f)):
        f.x[i] += x - cx
        f.y[i] += y - cy
    ev.state = "fly"


def play(ev, steer, until=lambda ev: False, limit=400.0):
    while ev.state != "done" and ev.time < limit and not until(ev):
        ev.step(STEP, steer(ev))
    return ev
