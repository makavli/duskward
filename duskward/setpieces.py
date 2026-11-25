"""What moves along an evening's route, each a little logic the Evening steps while the flock flies: squalls, a wild
flock that leads you along a trail of marks, bird-scarers, a balloon, hop gardens, fireworks and warm air, turbines,
fog banks, bridges and sea arches, gulls. Like the Evening, they never draw; render.py and scenery.py read them.

A piece may also offer: covers(ev, x, y), true where nothing can stoop on a bird; lane(ev, cx), the (height, gather)
the autopilot should fly when the flock's middle is at cx; wants_ripple(ev) for the autopilot's ripple.
"""

import math
import random
from dataclasses import dataclass

from .flock import Flock
from .settings import FLOOR_GAP

MARK_REACH = 100             # a mark counts when the flock's middle passes this close (plus a share of its spread)
MARK_SPACING = 220           # measured: tighter (150 apart, or a loop-the-loop) and a following flock misses half
MARK_PHASE = 0.6
MARK_PATIENCE = 4.0          # seconds a trail waits on one mark before it moves on without you
HOP_H = 168                  # the hop wires' height over the ground


@dataclass
class Group:
    """Starlings on a perch: strays from the start, or birds blown or knocked back."""
    x: float
    y: float
    birds: list                   # [(x, y, eight)]
    kind: str                     # wire, roof, tree, field, bine, girder, stack
    scattered: bool = False
    called: float = -1.0          # when they called to the passing flock


def blast(ev, x, y, reach, push=500, risk=0.6):
    """A bang at (x, y): birds inside reach are thrown outward and some are torn from the flock and land behind,
    fewer when it is gathered tight. Returns how many."""
    f, r, blown, i = ev.flock, ev.rng2, [], 0
    while i < len(f):
        ex, ey = f.x[i] - x, f.y[i] - y
        d = math.hypot(ex, ey) + 1e-6
        if d < reach:
            k = 1 - d / reach
            f.vx[i] += ex / d * push * k
            f.vy[i] += ey / d * push * k
            if r.random() < risk * k * (1 - 0.85 * f.g):
                blown.append(f.remove(i))
                continue
        i += 1
    ev.blow_back(blown)
    return len(blown)


class Squall:
    """A squall cloud across the route: slip under it. Birds up in it are tossed about and a loose flock loses some,
    blown back. In midwinter it is a snow squall, and silent."""

    def __init__(self, a, b, snow=False):
        self.a, self.b, self.snow = a, b, snow
        self.bolt, self.wait = (0.0, -9.0), 2.0          # (x, when) of its last lightning

    def bottom(self, x):
        """The cloud's underside over x, or -1 outside it."""
        if not self.a <= x <= self.b:
            return -1.0
        return 430 + 62 * math.sin(math.pi * (x - self.a) / (self.b - self.a))

    def near(self, x):
        return self.a - 200 < x < self.b + 200

    def step(self, ev, dt, cx, cy):
        flock, r = ev.flock, ev.rng
        if self.a - 50 < cx < self.b + 50:
            risk = dt * 0.7 * (1 - 0.85 * flock.g)
            blown, i = [], 0
            while i < len(flock):
                bottom = self.bottom(flock.x[i])
                if bottom > 0 and flock.y[i] < bottom + 6:
                    flock.vx[i] += r.uniform(-1, 1) * 900 * dt
                    flock.vy[i] += r.uniform(-0.4, 1) * 900 * dt
                    if r.random() < risk:
                        blown.append(flock.remove(i))
                        continue
                i += 1
            if blown:
                ev.cue("scatter")
            ev.blow_back(blown)
        if self.a - 1600 < cx:
            ev.hint("squall", "A squall ahead. Gather, and slip under it.")
        if not self.snow and self.a - 1400 < cx < self.b + 300:
            self.wait -= dt
            if self.wait <= 0:
                r = ev.rng2
                self.wait = r.uniform(2.5, 6.0)
                self.bolt = (min(max(cx + r.uniform(-400, 700), self.a + 120), self.b - 120), ev.time)
                ev.cue("thunder")

    def lane(self, ev, cx):
        if self.a - 1320 < cx < self.b + 80:
            x = min(max(cx + 160, self.a), self.b)
            return (self.bottom(x) + ev.ground(x) - FLOOR_GAP) / 2 + 6, cx > self.a - 350


class Course:
    """A small wild flock waits at the trail's start. When you come, it flies the trail just ahead of you, mark by
    mark, never more than two marks ahead. The more marks you pass through, the more of it joins you at the end."""

    def __init__(self, x0, n, base, birds, wave, seed):
        r = random.Random(seed)
        self.x0, self.base = x0, base
        self.marks = [(x0 + 260 + k * MARK_SPACING, base + wave * math.sin(k * MARK_PHASE)) for k in range(n)]
        self.guide = Flock(seed)
        for _ in range(birds):
            self.guide.add(x0 + r.uniform(-60, 60), base - 60 + r.uniform(-30, 30), r.uniform(-60, 60), r.uniform(-40, 40))
        self.state, self.next, self.hits, self.t, self.since = "wait", 0, 0, 0.0, 0.0

    def step(self, ev, dt, cx, cy):
        g, marks = self.guide, self.marks
        if self.state == "wait":
            if cx > self.x0 - 1600:
                self.t += dt
                g.step(dt, self.x0 + 110 * math.sin(self.t * 0.8), self.base - 60 + 30 * math.sin(self.t * 1.3), False, ev.floor)
            if self.x0 - 450 < cx < self.x0 + 600:
                self.state, self.t = "lead", 0.0
                ev.cue("course")
                ev.hint("course", "A wild flock is leading the way: follow its trail through the marks.")
        elif self.state == "lead":
            self.t += dt
            self.since += dt
            lx, ly = marks[min(self.next + 2, len(marks) - 1)]
            g.step(dt, lx, ly, False, ev.floor)
            reach = MARK_REACH + 0.3 * ev.flock.spread()
            for skip in range(3):                           # passing a mark late still counts the next ones
                k = self.next + skip
                if k < len(marks) and math.hypot(marks[k][0] - cx, marks[k][1] - cy) < reach:
                    ev.cue("mark", self.hits)
                    ev.fx.append(["mark", marks[k][0], marks[k][1], ev.time, k])
                    self.hits += 1
                    self.next, self.since = k + 1, 0.0
                    break
            else:
                if self.next < len(marks) and (cx > marks[self.next][0] + 220 or self.since > MARK_PATIENCE):
                    self.next, self.since = self.next + 1, 0.0
            if self.next >= len(marks):
                self.finish(ev)
        elif len(g):                                        # the rest fly home the way they came
            self.t += dt
            gx, _ = g.centre()
            g.step(dt, gx - 1500, 140, False, ev.floor)
            if self.t > 8:
                self.guide = Flock()

    def finish(self, ev):
        g = self.guide
        joiners = round(len(g) * (0.3 + 0.7 * self.hits / len(self.marks)))
        gx, gy = g.centre()
        for _ in range(joiners):
            x, y, vx, vy, _e = g.remove(len(g) - 1)
            ev.flock.add(x, y, vx, vy)
        ev.stats["marks"] += self.hits
        ev.stats["mark_total"] += len(self.marks)
        ev.stats["guided"] += joiners
        ev.cue("merge")
        ev.fx.append(["join", gx, gy, ev.time, joiners])
        ev.say(f"You followed {self.hits} of {len(self.marks)} marks: {joiners} of them join you.", 4.0)
        self.state, self.t = "done", 0.0

    def lane(self, ev, cx):
        if self.state == "lead" and self.next < len(self.marks):
            return self.marks[self.next][1], False


class Scarer:
    """A farm's gas gun. It ticks twice, then bangs; birds close to it scatter back down the route unless the flock
    is gathered tight. Then it re-arms."""

    PERIOD, REACH = 7.0, 260

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.left, self.fired = 4.0, -9.0

    def step(self, ev, dt, cx, cy):
        if abs(self.x - cx) > 1100:
            return
        ev.hint("scarer", "A bird-scarer! When it ticks, gather tight or keep clear.")
        before = self.left
        self.left -= dt
        if before > 2.0 >= self.left or before > 1.0 >= self.left:
            ev.cue("tick")
        if self.left > 0:
            return
        self.left, self.fired = self.PERIOD + ev.rng2.uniform(0, 3), ev.time
        ev.cue("bang")
        ev.fx.append(["bang", self.x, self.y - 14, ev.time, 0])
        blast(ev, self.x, self.y, self.REACH)


class Balloon:
    """A hot-air balloon drifting on the evening air, its burner roaring now and then, starlings riding its basket.
    Swing past the basket and they come with you."""

    def __init__(self, x, y, riders):
        self.x0, self.y0 = x, y
        self.x, self.y = x, y
        self.riders = [0] * riders
        self.burn, self.next_burn = -9.0, 2.0

    def basket(self):
        return self.x, self.y + 76

    def step(self, ev, dt, cx, cy):
        self.x = self.x0 + 24 * ev.time
        self.y = self.y0 + 22 * math.sin(ev.time * 0.23) + 10 * math.sin(ev.time * 0.61)
        self.next_burn -= dt
        if self.next_burn <= 0:
            self.burn, self.next_burn = ev.time, ev.rng2.uniform(5, 9)
            if abs(self.x - cx) < 1300:
                ev.cue("burner")
        if not self.riders:
            return
        bx, by = self.basket()
        if math.hypot(bx - cx, by - cy) < 100 + 0.5 * ev.flock.spread():
            for j, eight in enumerate(self.riders):
                ev.flock.add(bx - 8 + j * 3, by - 6, ev.rng2.uniform(40, 120), ev.rng2.uniform(-120, -60), eight)
            ev.stats["strays"] += len(self.riders)
            ev.stats["balloon"] = len(self.riders)
            ev.cue("balloon")
            ev.fx.append(["join", bx, by, ev.time, len(self.riders)])
            self.riders = []
        elif 0 < bx - cx < 900:
            ev.hint("balloon", "Starlings riding the balloon! Swing past its basket.")


def knock(ev, birds, stat="snagged"):
    """Birds something solid knocked out of the air: they drop behind and call, like any scattered bird."""
    if birds:
        ev.cue("snag", len(birds))
        ev.stats[stat] += len(birds)
        ev.blow_back(birds, near=True)


class HopGarden:
    """Rows of hop poles under a lattice of wire, the bines hanging from it. Under the wires nothing can stoop on the
    flock and strays shelter in the bines; a bird that crosses the wires is snagged and left behind."""

    def __init__(self, ev, a, b):
        self.a, self.b = a, b
        r, x = ev.rng3, a + 230
        while x < b - 180:                               # strays in the bines, midges between the rows
            n = r.choice((2, 3, 3, 4, 5, 6))
            y = ev.ground(x) - r.uniform(52, 108)
            ev.groups.append(Group(x, y, [(x + (j - n / 2) * 7, y + r.uniform(-3, 3), 0) for j in range(n)], "bine"))
            ev.midges.append([x + 200, ev.ground(x + 200) - 74, -1.0])
            x += r.randint(390, 520)

    def wire(self, ev, x):
        return ev.ground(x) - HOP_H

    def covers(self, ev, x, y):
        return self.a < x < self.b and y > self.wire(ev, x)

    def step(self, ev, dt, cx, cy):
        if not self.a - 1000 < cx < self.b + 300:
            return
        ev.hint("hops", "Hop gardens. Gather and fly in under the wires: strays shelter in the bines.")
        f, r, snagged, i, risk = ev.flock, ev.rng2, [], 0, dt * 5
        while i < len(f):
            x = f.x[i]
            if self.a < x < self.b and abs(f.y[i] - self.wire(ev, x)) < 5 and r.random() < risk:
                snagged.append(f.remove(i))
                continue
            i += 1
        knock(ev, snagged)

    def lane(self, ev, cx):
        if self.a - 700 < cx < self.b + 40:
            x = min(max(cx + 160, self.a), self.b)
            return ev.ground(x) - HOP_H * 0.46, self.a - 260 < cx < self.b - 40


class Fireworks:
    """Bonfire night over the town: rockets climb from the streets to where the flock will be, and burst. The climb is
    the warning: steer clear of the burst, or gather tight."""

    REACH, CLIMB = 185, 1.25

    def __init__(self, a, b):
        self.a, self.b = a, b
        self.rockets = []                                # [x, y0, y1, born, hue]
        self.wait = 2.0

    def at(self, rk, now):
        u = min(1.0, (now - rk[3]) / self.CLIMB)
        return rk[0], rk[1] + (rk[2] - rk[1]) * (1 - (1 - u) ** 2)

    def step(self, ev, dt, cx, cy):
        if self.a - 500 < cx < self.b:
            ev.hint("rockets", "Fireworks! A rocket's climb is your warning: steer clear of its burst, or gather tight.")
            self.wait -= dt
            if self.wait <= 0:
                r, f = ev.rng2, ev.flock
                self.wait = r.uniform(1.7, 3.5)
                x = cx + sum(f.vx) / max(1, len(f)) * self.CLIMB + r.uniform(-70, 240)
                if self.a < x < self.b:
                    y1 = min(max(cy + r.uniform(-150, 150), 110.0), ev.floor(x) - 110)
                    self.rockets.append([x, ev.floor(x), y1, ev.time, r.randrange(6)])
                    ev.cue("rocket")
        keep = []
        for rk in self.rockets:
            if ev.time - rk[3] < self.CLIMB:
                keep.append(rk)
                continue
            ev.cue("burst", rk[4])
            ev.fx.append(["burst", rk[0], rk[2], ev.time, rk[4]])
            if blast(ev, rk[0], rk[2], self.REACH, 420, 0.5):
                ev.cue("scatter")
        self.rockets = keep

    def lane(self, ev, cx):
        cy = ev.flock.centre()[1]
        for rk in self.rockets:
            if abs(rk[0] - cx) < 420 and abs(rk[2] - cy) < 270:
                away = cy + (190 if rk[2] < cy else -190)
                return min(max(away, 90.0), ev.floor(cx + 200) - 70), True


class Thermal:
    """Warm air rising over chimneys and the bonfire. It lifts the birds in it, and a flock spread wide on it gets its
    breath back without a wingbeat."""

    LIFT, FOOD = 230, 0.3

    def __init__(self, x, half):
        self.x, self.half, self.inside = x, half, False

    def step(self, ev, dt, cx, cy):
        if abs(cx - self.x) > self.half + 600:
            self.inside = False
            return
        ev.hint("thermal", "Warm air rising: spread wide on it, and the flock rests as it flies.")
        f, n = ev.flock, 0
        for i in range(len(f)):
            d = abs(f.x[i] - self.x)
            if d < self.half:
                f.vy[i] -= self.LIFT * dt * (1 - d / self.half)
                n += 1
        now = n > 0.5 * len(f)
        if now and not self.inside:
            ev.cue("thermal")
        self.inside = now
        if now and not ev.gathering:
            ev.stamina = min(1.0, ev.stamina + self.FOOD * dt)


class Turbine:
    """A wind turbine. Its three blades sweep a disc, and a bird a blade catches is knocked down. Slip under the
    tips, go over the top, or pass between two blades."""

    THIRD = 2 * math.pi / 3

    def __init__(self, ev, x, hub, radius, period):
        self.x, self.r, self.period = x, radius, period
        self.y = ev.ground(x) - hub                      # the hub
        self.phase, self.last = ev.rng3.uniform(0, 6.283), 0

    def angle(self, t):
        return self.phase + t * 2 * math.pi / self.period

    def step(self, ev, dt, cx, cy):
        if abs(cx - self.x) > self.r + 800:
            return
        ev.hint("turbine", "Turbines. Slip under the blade tips, low on the wind, or climb right over the top.")
        a = self.angle(ev.time)
        k = int(a / self.THIRD)
        if k != self.last:                               # a blade swings through the bottom of its turn
            self.last = k
            if abs(cx - self.x) < self.r + 240:
                ev.cue("blade")
        f = ev.flock
        if abs(cx - self.x) > self.r + 3 * f.spread() + 60:
            return
        r, hit, i, r2, risk = ev.rng2, [], 0, self.r * self.r, dt * 3
        while i < len(f):
            ex, ey = f.x[i] - self.x, f.y[i] - self.y
            d2 = ex * ex + ey * ey
            if 150 < d2 < r2:
                m = (math.atan2(ey, ex) - a) % self.THIRD          # the angle to the nearest of the three blades
                if math.sqrt(d2) * math.sin(min(m, self.THIRD - m)) < 5 and r.random() < risk:
                    hit.append(f.remove(i))
                    continue
            i += 1
        knock(ev, hit)

    def lane(self, ev, cx):
        if self.x - self.r - 560 < cx < self.x + self.r + 60:
            return (self.y + self.r + ev.ground(self.x) - FLOOR_GAP) / 2 + 8, abs(cx - self.x) < self.r + 220


class Fog:
    """A bank of fog on the estuary. In it a bird on the flock's edge loses the others and drops to the mud, calling,
    unless the flock is gathered: then each bird has a neighbour in sight. The falcon cannot find you in it either."""

    KEEP = 100                                           # further than this from the middle, a bird is on its own

    def __init__(self, a, b):
        self.a, self.b, self.horn = a, b, 2.5

    def thick(self, x):
        return max(0.0, min(1.0, (x - self.a) / 240, (self.b - x) / 240))

    def step(self, ev, dt, cx, cy):
        k = self.thick(cx)
        if not k:
            if 0 < self.a - cx < 1300:
                ev.hint("fog", "Fog ahead. Gather before you go in: a bird that drifts apart is lost.")
            return
        self.horn -= dt
        if self.horn <= 0:
            self.horn = ev.rng2.uniform(14, 20)
            ev.cue("foghorn")
        beat = int(ev.time / 6.5)
        if beat != int((ev.time - dt) / 6.5):            # a bell buoy, somewhere out in it
            ev.cue("buoy", beat)
        f, r, lost, i, risk, keep2 = ev.flock, ev.rng2, [], 0, dt * 0.6 * k * (1 - 0.9 * ev.flock.g), self.KEEP ** 2
        while i < len(f):
            if (f.x[i] - cx) ** 2 + (f.y[i] - cy) ** 2 > keep2 and r.random() < risk:
                lost.append(f.remove(i))
                continue
            i += 1
        if lost:
            ev.cue("scatter")
            ev.stats["fogged"] += len(lost)
            ev.blow_back(lost, near=True)

    def lane(self, ev, cx):
        if self.a - 60 < cx < self.b - 60:
            return None, True
        if self.a - 1300 < cx < self.a - 60 and ev.stamina < 0.97 and not ev.over_water(cx + 200):
            return ev.ground(cx + 200) - 90, False       # feed low before it


class Slab:
    """Something solid across the route with air under it: a bridge's deck, or the rock over a sea arch. The flock
    passes under or over it. Under it nothing can stoop on a bird, and strays roost in its shadow."""

    def __init__(self, ev, a, b, top, bottom, kind, rise=0.0):
        """top and bottom are heights in the world at the ends; the underside rises by `rise` toward the middle."""
        self.a, self.b, self.top, self.low, self.kind, self.rise = a, b, top, bottom, kind, rise
        self.inside = False
        r, x = ev.rng3, a + 150
        while x < b - 120:                               # strays roosting under it, and perches for the blown-back
            y = self.bottom(x) + 9
            ev.perches.append((kind, x, y))
            if r.random() < 0.6:
                n = r.choice((2, 3, 3, 4, 5, 6))
                ev.groups.append(Group(x, y, [(x + (j - n / 2) * 7, y + r.uniform(-1, 2), 0) for j in range(n)], kind))
            x += r.randint(230, 330)

    def bottom(self, x):
        u = (x - self.a) / (self.b - self.a)
        return self.low - self.rise * math.sin(math.pi * min(1.0, max(0.0, u)))

    def covers(self, ev, x, y):
        return self.a < x < self.b and y > self.bottom(x)

    def step(self, ev, dt, cx, cy):
        now = self.covers(ev, cx, cy)
        if now and not self.inside:
            ev.cue("bridge")
        self.inside = now
        if 0 < self.a - cx < 1100:
            ev.hint(self.kind, "A bridge: starlings roost on the girders under its deck, and nothing hunts there."
                    if self.kind == "girder" else "A sea arch: fly in under the rock. The falcons cannot follow.")

    def lane(self, ev, cx):
        if self.a - 620 < cx < self.b + 40:
            x = min(max(cx + 160, self.a), self.b)
            return (self.bottom(x) + 16 + ev.floor(x) - FLOOR_GAP) / 2, False


class Gulls:
    """Herring gulls over the open water. One at a time they come down the river at the flock and barge through it:
    the birds they hit drop out. A ripple as one closes makes it sheer off, and a gathered flock gives it less to hit."""

    SPEED = 250

    def __init__(self, a, b):
        self.a, self.b, self.wait = a, b, 2.0
        self.gull = None                                 # [x, y, vx, vy, coming?]

    def step(self, ev, dt, cx, cy):
        g = self.gull
        if g is None:
            if self.a < cx < self.b and not ev.shelter:
                self.wait -= dt
                if self.wait <= 0:
                    self.gull = [cx + 920, max(70.0, cy - 130), -self.SPEED, 0.0, True]
                    ev.cue("gull")
                    ev.hint("gull", "Gulls! Ripple as one closes and it sheers off. Or keep under the bridge.")
            return
        if g[4]:
            dx, dy = cx - g[0], cy - g[1]
            d = math.hypot(dx, dy) + 1e-6
            turn = min(1.0, dt * 2.5)
            g[2] += (dx / d * self.SPEED - g[2]) * turn
            g[3] += (dy / d * self.SPEED - g[3]) * turn
            if any(abs(math.hypot(g[0] - rx, g[1] - ry) - rr) < 30 for rx, ry, rr in ev.flock.ripples):
                g[4] = False
                ev.stats["gulls"] += 1
                ev.say("The gull sheers off.", 2.0)
                ev.cue("miss")
            elif ev.shelter or not self.a - 300 < cx < self.b + 300:
                g[4] = False
            elif d < 34 + 0.4 * ev.flock.spread():
                g[4] = False
                if blast(ev, g[0], g[1], 80, 320, 0.8):
                    ev.cue("scatter")
        else:                                            # away, up and over
            g[3] -= 320 * dt
            if g[1] < -60 or abs(g[0] - cx) > 1500:
                self.gull, self.wait = None, ev.rng2.uniform(3.5, 6.5)
                return
        g[0] += g[2] * dt
        g[1] += g[3] * dt

    def wants_ripple(self, ev):
        g = self.gull
        if g and g[4]:
            cx, cy = ev.flock.centre()
            return math.hypot(g[0] - cx, g[1] - cy) < 190 + ev.flock.spread()
        return False
