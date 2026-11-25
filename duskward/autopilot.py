"""A bot that flies every evening: for the tests, the screenshots and the browser check, never for players.

It cruises, goes to the strays it sees ahead, and lets each set piece on the route say how to pass it (its lane).
"""

import math

from .evening import Ctrl

TRAILS = True                 # follow a wild flock's marks (off to fly as the first bot did)


def drive(ev):
    c = Ctrl()
    cx, cy = ev.flock.centre()
    if ev.state == "echo":                       # aim a little past the next mark, along the shape
        last = len(ev.checks) - 1
        (ax, ay), (bx, by) = ev.checks[min(ev.next_check, last)], ev.checks[min(ev.next_check + 1, last)]
        c.tx, c.ty = ax + (bx - ax) * 1.5, ay + (by - ay) * 1.5
        c.gather = ev.stamina > 0.2 and not ev.tired
        n = max(1, len(ev.flock))
        if (ax - cx) * sum(ev.flock.vx) / n + (ay - cy) * sum(ev.flock.vy) / n < 0:
            c.tx, c.ty, c.gather = ax + (ax - cx) * 0.7, ay + (ay - cy) * 0.7, False     # flown past it: turn back, slowly
        return c
    if ev.state == "free":                       # a slow wheel over the roost, a ripple now and then
        t = ev.state_t
        c.tx, c.ty = ev.dance_x + 280 * math.sin(t * 0.8), 300 + 120 * math.sin(t * 1.6)
        c.ripple = int(t * 60) % 180 == 90
        return c
    ahead = cx + 420
    ty = 340.0
    groups = [g for g in ev.groups if cx + 60 < g.x < cx + 900]
    if groups:
        ty = max(200.0, min(groups, key=lambda g: g.x).y - 20)
    if ev.stamina < 0.35 and not ev.over_water(ahead):
        ty = max(ty, ev.ground(ahead) - 100)
    for piece in ev.pieces:
        lane = getattr(piece, "lane", None)
        way = lane(ev, cx) if lane and (TRAILS or piece not in ev.courses) else None
        if way:
            if way[0] is not None:
                ty = way[0]
            c.gather = c.gather or (way[1] and not ev.tired)
    if ev.walls:                                 # never aim into a roof or a cliff
        ty = min(ty, min(ev.floor(cx + d) for d in (0, 140, 280, 420)) - 34)
    c.ripple = (any(f.state == "stoop" and f.distance() < 200 for f in ev.falcons)
                or any(g.wants_ripple(ev) for g in ev.gulls))
    c.tx, c.ty = ahead, ty
    return c
