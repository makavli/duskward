"""One evening of the journey: a place's route and its strays, its weather and dangers, the falcon, the roost flock's
dance, the clock. places.py says what a place holds; this builds it and steps it.

Everything here is logic: the painter in render.py reads it, the app and the autopilot drive it with a Ctrl.
"""

import math
import random
from dataclasses import dataclass

from .falcon import Falcon
from .flock import Flock
from .places import NAMES, PLACES, SHAPES
from .setpieces import (Balloon, Course, Fireworks, Fog, Group, Gulls, HopGarden, Scarer, Slab, Squall,  # noqa: F401
                        Thermal, Turbine)
from .settings import (FEED, FLOOR_GAP, GATHER_DRAIN, JOIN_REACH, LOW_BAND, NIGHT_LOSS, REST, RIPPLE_COOL,
                       RIPPLE_COST)

CARRY_MAX = 72                       # of last night's flock, the nearest rise with the eight; the rest follow south
SETTLE_SECONDS = 4.0
FREE_SECONDS = 14.0                  # the last evening's dance of every flock together
CHECK_REACH = 85
DANCE_Y = 300
WIND_HALF, WIND_PUSH = 60, 170       # a stream's half depth, and how much faster it carries a bird through its middle
MIDGE_FOOD = 0.35                    # stamina a midge swarm gives back
CHAIN_GAP = 3.5                      # joins and feeds closer than this in time make a chain
CARD_SECONDS = 5.0                   # the evening's title card; hints wait for it
RAMP = 0.8                           # birds meet a wall as a slope this steep in front of it, and climb in time
APART = (0, -420, 420)               # where the last evening's three flocks wait, about the roost
CAP = {"fly": 1.0, "watch": 0.97, "echo": 0.97, "free": 0.97, "settle": 1.0}     # night never falls on a dance
HOLD = 0.5                           # how often one of the eight, torn from the flock, fights its way back in
BASICS = ("steer", "gather", "strays", "midges", "wind", "falcon", "squall", "scarer", "balloon", "course")
ROOST_FLOCK = {"reeds": "reed flock", "trees": "wood flock", "bridge": "bridge flock", "pier": "pier flock"}


@dataclass
class Ctrl:
    tx: float = 0.0               # where the flock should go, in world pixels
    ty: float = 300.0
    gather: bool = False
    ripple: bool = False          # pressed this step


def between(points, x):
    """The height at x on a line through (x, y) points."""
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * max(0.0, (x - x0) / (x1 - x0))
    return points[-1][1]


class Evening:
    def __init__(self, seed=1, place=0, carry=None):
        """carry: (which of the eight still fly, the common starlings that roosted with them last night)."""
        self.seed, self.index = seed, place
        self.place = p = PLACES[place]
        self.roost_x, self.length, self.dance_x = p.roost, p.length, p.roost + p.dance_at
        self.water_y = p.base + 20
        self.walls = bool(p.blocks or p.heights or p.stacks)       # something a bird can fly into
        eight, commons = carry or (tuple(range(1, 9)), 0)
        self.eight_start = tuple(eight)
        self.fates = {}                     # which of the eight was lost tonight, and how: falcon, behind, cold
        self.rng = random.Random(seed)
        self.time = 0.0
        self.light = p.light0               # 0 golden hour .. 1 dark
        self.state = "fly"                  # fly, watch, echo, free, settle, done
        self.state_t = 0.0
        self.result = None                  # roost, night, lost
        self.stamina, self.tired, self.cool = 1.0, False, 0.0
        self.gathering = False
        self.messages = []                  # [text, seconds left]
        self.pending = []                   # hints wait here and show one at a time
        self.sounds = []                    # (name, n) to play this step
        self.fx = []                        # [kind, x, y, born, n] for the painter: join, feed, feathers, burst...
        self.hints = set(BASICS) if place else set()      # what the first evening taught is not said again
        self.stats = {"start": 0, "strays": 0, "regathered": 0, "scattered": 0, "caught": 0, "merged": 0,
                      "dance": 0.0, "cold": 0, "midges": 0, "marks": 0, "mark_total": 0, "guided": 0, "balloon": 0,
                      "snagged": 0, "fogged": 0, "gulls": 0, "flown": 0.0}
        self.chain, self.chain_at = 0, -9.0
        self.in_wind = self.shelter = False
        self.fog = 0.0                      # how thick the fog is about the flock, 0..1
        self.rng2 = random.Random(seed + 7)               # the newer things draw here, so the old marsh stays the same
        self.rng3 = random.Random(seed + 13)              # and the lands south of the marsh here
        self.build()
        self.flock = Flock(seed)
        self.falcon = Falcon(random.Random(seed + 1), p.circle, p.feint, p.from_sun)
        self.falcons = [self.falcon]
        if p.pair:
            self.falcons.append(Falcon(random.Random(seed + 3), p.circle, p.feint, p.from_sun, mate=self.falcon))
        r, r2 = self.rng, self.rng2
        for k, e in enumerate(self.eight_start):                # the eight, on the first wire
            x = 420 + k * 9 + r.uniform(-2, 2)
            self.flock.add(x, self.wire_y(x, 0) - 3, r.uniform(20, 70), r.uniform(-150, -90), eight=e)
        for k in range(min(CARRY_MAX, commons)):                # and those who roosted beside them, either side
            x = 210 + k * 8 + r2.uniform(-2, 2)
            self.flock.add(x, self.wire_y(x, k % 2) - 3, r2.uniform(20, 70), r2.uniform(-150, -90))
        self.stats["start"] = len(self.flock)
        self.remnants = []                                      # the flocks dancing over the roost
        for j in range(3 if p.finale else 1):
            rem = Flock(seed + 2 + 20 * j)
            for _ in range(p.remnant):
                rem.add(self.dance_x + APART[j] + r.uniform(-220, 220), DANCE_Y + r.uniform(-70, 70),
                        r.uniform(-90, 90), r.uniform(-60, 60))
            self.remnants.append(rem)
        self.share = p.remnant / (1 if p.finale else len(p.dance))   # how many a perfect round wins
        self.set_round(0)

    # ---- the land
    def build(self):
        p, r, r3 = self.place, self.rng, self.rng3
        ph = [r.uniform(0, 6.283) for _ in range(3)]
        hp = r3.uniform(0, 6.283)
        flats = [(a, b, p.base + 18, 0.8) for a, b in p.pools + (p.reeds,)]       # the marsh lies low and flat
        flats += [(b[0], b[1], p.base, 0.9) for b in p.blocks] + [(a, b, self.water_y, 1.0) for a, b in p.waters]
        n = p.length // 8 + 2
        self.gt = gt = []                                     # the ground, every 8 px
        for i in range(n):
            x = i * 8
            if p.heights:                                     # cliffs and sea: the heights say it all
                y = between(p.heights, x)
                if y < 600:
                    y += 4 * math.sin(x / 170 + ph[1]) + 2.5 * math.sin(x / 61 + ph[2])
            else:
                y = (p.base + p.roll * 14 * math.sin(x / 530 + ph[0]) + p.roll * 9 * math.sin(x / 170 + ph[1])
                     + p.roll * 5 * math.sin(x / 61 + ph[2]) + p.hill * math.sin(x / 1150 + hp))
                for a, b, level, weight in flats:
                    if a - 300 < x < b + 300:
                        w = min(1.0, (x - a + 300) / 300, (b + 300 - x) / 300)
                        y += (level - y) * w * weight
            gt.append(y)

        self.houses, self.trees, self.pools, self.perches, self.buildings = [], [], [], [], []
        self.ft = ft = gt[:]                                  # the floor: the ground, or what stands on it
        for a, b, lo, hi in p.blocks:
            x = a
            while x < b - 60:
                w, h = r3.randint(80, 190), r3.randint(lo, hi)
                roof = self.ground(x + w / 2) - h
                self.buildings.append((x, w, h, r3.randrange(1000)))
                for i in range(x >> 3, min(n, ((x + w) >> 3) + 1)):
                    ft[i] = min(ft[i], roof)
                x += w + r3.choice((0, 0, 8, 30, 60))
        for x, h in p.stacks:                                 # sea stacks
            for i in range((x - 36) >> 3, ((x + 36) >> 3) + 1):
                ft[i] = min(ft[i], self.water_y - h)
            self.perches.append(("stack", x, self.water_y - h - 3))
        self.rt = ft[:]                                       # the roofs and the ground as they stand
        for i in range(1, n):                                 # a wall is a slope to a bird: it climbs before it
            ft[i] = min(ft[i], ft[i - 1] + 8 * RAMP)
        for i in range(n - 2, -1, -1):
            ft[i] = min(ft[i], ft[i + 1] + 8 * RAMP)

        self.poles, self.wires = [], []
        for a, b in p.wires:
            xs = list(range(a, b + 1, 420))
            self.poles += xs
            for k in range(2):
                for x0, x1 in zip(xs, xs[1:]):
                    self.wires.append((x0, x1, k))
        for a, b in p.farms:
            x = a
            while x < b:
                w, h = r.randint(70, 120), r.randint(40, 62)
                self.houses.append((x, w, h, r.randint(24, 38), r.random() < 0.5))
                self.perches.append(("roof", x + w / 2, self.ground(x + w / 2) - h - 30))
                x += w + r.randint(40, 160)
        bare = [(a - 100, b + 100) for a, b in p.farms]
        bare += [(z[0] - 60, z[1] + 60) for z in p.blocks + p.waters + p.hops]
        x = 300
        while p.tree_gap and x < p.reeds[0] - 200:
            x += r.randint(*p.tree_gap)
            if any(a < x < b for a, b in bare):
                continue
            h, rad = r.randint(50, 112), r.randint(18, 36)
            self.trees.append((x, h, rad))
            self.perches.append(("tree", x, self.ground(x) - h - rad * 0.6))
        if p.kind == "trees":                                # the roost wood
            x = p.roost - 520
            while x < p.roost + 760:
                self.trees.append((x, r3.randint(70, 132), r3.randint(22, 40)))
                x += r3.randint(46, 110)
        for a, b in p.pools:
            x = a + r.randint(60, 300)
            while x < b:
                w = r.randint(120, 420)
                self.pools.append((x, w, r.randint(5, 12)))
                x += w + r.randint(160, 520)
        if not p.heights:
            for a, b in p.waters:                             # mooring posts: somewhere to stand, out on the water
                x = a + r3.randint(150, 400)
                while x < b - 100:
                    self.perches.append(("post", x, self.water_y - 26))
                    x += r3.randint(420, 620)
        r2 = random.Random(self.seed + 5)
        self.herons = [[x + w * r2.uniform(0.3, 0.7), self.ground(x + w / 2) + 4, 0.0, 0.0, -1.0]  # x, y, vx, vy, flushed at
                       for x, w, _h in self.pools if w > 180 and r2.random() < 0.8]
        self.midges = []                                      # [x, y, eaten at]
        skip = [(a - 400, b + 300, b + 400) for a, b in p.squalls]
        skip += [(z[0] - 100, z[1] + 100, z[1] + 150) for z in p.blocks + p.hops]
        x = 1250
        while x < p.reeds[0] - 600:
            for a, b, on in skip:
                if a < x < b:
                    x = on
            self.midges.append([x, self.floor(x) - r2.uniform(50, 100), -1.0])
            x += r2.randint(*p.midge_gap[0]) if x < 7000 else r2.randint(*p.midge_gap[1])

        self.groups = []
        self.squalls = [Squall(a, b, p.snow) for a, b in p.squalls]
        self.courses = [Course(*c, self.seed + 11 + k) for k, c in enumerate(p.courses)]
        self.scarers = [Scarer(a + (b - a) * 0.6, self.ground(a + (b - a) * 0.6) - 4) for a, b in p.farms] if p.scarers else []
        self.balloon = Balloon(*p.balloon) if p.balloon else None
        self.hops = [HopGarden(self, a, b) for a, b in p.hops]
        self.fireworks = [Fireworks(a, b) for a, b in p.fireworks]
        self.thermals = [Thermal(x, half) for x, half in p.thermals]
        self.turbines = [Turbine(self, *t) for t in p.turbines]
        self.fogs = [Fog(a, b) for a, b in p.fogs]
        self.slabs = [Slab(self, a, b, self.water_y - h - 22, self.water_y - h + 6, "girder") for a, b, h in p.bridges]
        self.slabs += [Slab(self, a, b, top, roof, "arch", rise=40) for a, b, top, roof in p.arches]
        self.gulls = [Gulls(a, b) for a, b in p.gulls]
        self.pieces = (self.courses + self.scarers + ([self.balloon] if self.balloon else []) + self.squalls
                       + self.hops + self.thermals + self.turbines + self.fogs + self.slabs + self.gulls
                       + self.fireworks)
        self.covers = self.hops + self.slabs                  # where nothing can stoop on the flock
        self.st = [None] * n if self.slabs else []            # what is solid in the air: (top, bottom) every 8 px
        for s in self.slabs:
            half = (s.low - s.top) / 2
            lead = min(110.0, half * 1.5)                     # a bird is turned over or under before the face
            for i in range(max(0, int(s.a - lead) >> 3), min(n, (int(s.b + lead) >> 3) + 1)):
                x = i * 8
                if s.a <= x <= s.b:
                    self.st[i] = (s.top, s.bottom(x))
                else:
                    u = 1 - (s.a - x if x < s.a else x - s.b) / lead
                    if u > 0:
                        self.st[i] = (s.top + half * (1 - u), s.top + half * (1 + u))
        for x, _h in p.stacks:
            k = r3.choice(p.strays)
            y = self.floor(x) - 3
            self.groups.append(Group(x, y, [(x + (j - k / 2) * 7, y + r3.uniform(-2, 2), 0) for j in range(k)], "stack"))

        skip = [(a - 300, b + 200, b + 260) for a, b in p.squalls] + [(a - 150, b + 100, b + 160) for a, b in p.hops]
        x = 900
        while x < p.reeds[0] - 500:
            for a, b, on in skip:
                if a < x < b:
                    x = on
            k = r.choice(p.strays)
            self.groups.append(self.perch_group(x, k, low=r.random() < 0.3))
            x += r.randint(*p.stray_gap)

    def ground(self, x):
        i = int(x) >> 3
        return self.gt[0 if i < 0 else (i if i < len(self.gt) else -1)]

    def floor(self, x):
        """What a bird cannot fly below at x: the ground, a roof, the slope before a wall."""
        i = int(x) >> 3
        return self.ft[0 if i < 0 else (i if i < len(self.ft) else -1)]

    def slab(self, x):
        """None, or the (top, bottom) of the bridge or arch over x."""
        i = int(x) >> 3
        return self.st[i] if 0 <= i < len(self.st) else None

    def over_water(self, x):
        return any(a < x < b for a, b in self.place.waters)

    def wire_y(self, x, k):
        for x0, x1, kk in self.wires:
            if kk == k and x0 <= x <= x1:
                u = (x - x0) / (x1 - x0)
                return self.pole_top(x0) + (self.pole_top(x1) - self.pole_top(x0)) * u + 26 * math.sin(math.pi * u) + k * 12
        return self.ground(x) - 4

    def pole_top(self, x):
        return self.ground(x) - 118

    def on_wire(self, x):
        return any(a <= x <= b for a, b in self.place.wires)

    def perch_group(self, x, n, low=False, birds=None, scattered=False):
        """n birds near x: on a wire, a roof or a tree if one is close, otherwise in the field. Over water, on the
        nearest thing that stands in it."""
        r = self.rng
        while self.walls and x < self.length and self.rt[int(x) >> 3] - self.floor(x) > 4:
            x += 8                                            # never on the air before a wall: on the roof past it
        wet = self.over_water(x)
        if not low and not wet and self.on_wire(x):
            k = r.randint(0, 1)
            pts = [(x + j * 8, self.wire_y(x + j * 8, k) - 3) for j in range(n)]
            kind = "wire"
        else:
            near = [q for q in self.perches if abs(q[1] - x) < (900 if wet else 160)] if wet or not low else []
            if near:
                kind, px, py = min(near, key=lambda q: abs(q[1] - x))
                pts = [(px + (j - n / 2) * 7 + r.uniform(-2, 2), py + r.uniform(-4, 3)) for j in range(n)]
            else:
                if wet:                                       # nothing stands in it: the bank they came from
                    x = max(a for a, b in self.place.waters if a < x < b) - 40 - 9 * n
                kind = "field"
                pts = [(x + j * 9 + r.uniform(-3, 3), self.floor(x + j * 9) - 3) for j in range(n)]
        eights = birds or [0] * n
        return Group(pts[0][0], pts[0][1], [(px, py, e) for (px, py), e in zip(pts, eights)], kind, scattered)

    def squall_bottom(self, x):
        """The underside of the squall cloud over x, or -1 under open sky."""
        return max((s.bottom(x) for s in self.squalls), default=-1.0)

    def roost_point(self):
        return self.roost_x, self.ground(self.roost_x) - self.place.perch

    def sun(self, cx):
        """Where the sun stands, seen from the flock: a falcon can come out of it."""
        return cx + 430, min(520.0, 250 + 420 * self.light / 0.62)

    def set_round(self, k):
        """The roost flock's k-th figure."""
        self.round = k
        self.shape = SHAPES[self.place.dance[k]]
        n = self.shape[5]
        self.checks = [self.dance_point(2 * math.pi * j / n) for j in range(1, n + 1)]
        self.next_check, self.trail, self.score = 0, [], 0.0

    def dance_point(self, s):
        a, b, phase, ax, ay = self.shape[:5]
        return self.dance_x + ax * math.sin(a * s + phase), DANCE_Y + ay * math.sin(b * s)

    # ---- one step
    def say(self, text, seconds=4.0):
        self.messages.append([text, seconds])

    def hint(self, name, text):
        if name not in self.hints:
            self.hints.add(name)
            self.pending.append(text)

    def cue(self, name, n=0):
        self.sounds.append((name, n))

    def link(self):
        """The next step of a chain of joins and feeds: 0, 1, 2... while they come quickly."""
        self.chain = self.chain + 1 if self.time - self.chain_at < CHAIN_GAP else 0
        self.chain_at = self.time
        return self.chain

    def step(self, dt, ctrl):
        self.time += dt
        self.state_t += dt
        self.sounds = [("liftoff", 0)] if self.time == dt else []
        for m in self.messages:
            m[1] -= dt
        self.messages = [m for m in self.messages if m[1] > 0]
        if not self.messages and self.pending and self.time > CARD_SECONDS:
            self.say(self.pending.pop(0), 5.0)
        self.fx = [f for f in self.fx if self.time - f[3] < 3.0]
        p, flock = self.place, self.flock
        slab = self.slab if self.slabs else None
        if self.state == "done":                       # the flock rests: at the roost, or milling where night found it
            cx, cy = flock.centre()
            gx, gy = self.roost_point() if self.result == "roost" else (cx + 40, cy)
            flock.step(dt, gx, gy, False, self.floor, slab)
            for rem in self.remnants:
                rem.step(dt, *self.roost_point(), False, self.floor, slab)
            return
        self.light = min(CAP[self.state], self.light + dt / p.seconds)
        cx, cy = flock.centre()
        self.shelter = any(c.covers(self, cx, cy) for c in self.covers)
        self.fog = max((f.thick(cx) for f in self.fogs), default=0.0)

        low = self.shelter or (cy > self.ground(cx) - LOW_BAND and not self.over_water(cx))
        want = ctrl.gather and not self.tired and self.state in ("fly", "echo", "free")
        if want:
            self.stamina -= GATHER_DRAIN * dt
            if self.stamina <= 0:
                self.stamina, self.tired = 0.0, True
        else:
            self.stamina = min(1.0, self.stamina + (FEED if low else REST) * dt)
            if self.tired and self.stamina >= 0.3:
                self.tired = False
        if self.state == "free":                       # nobody tires tonight
            self.stamina, self.tired = 1.0, False
        self.gathering = want and not self.tired
        self.cool -= dt
        if ctrl.ripple and self.cool <= 0 and self.stamina >= RIPPLE_COST and len(flock):
            self.stamina -= RIPPLE_COST
            self.cool = RIPPLE_COOL
            flock.ripple(cx, cy)
            self.falcon.on_ripple()
            self.cue("ripple")
            if self.state == "free":                   # and every flock answers
                for rem in self.remnants:
                    rem.ripple(*rem.centre())

        tx, ty = ctrl.tx, min(max(ctrl.ty, 40.0), self.floor(ctrl.tx) - FLOOR_GAP - 8)
        if self.state == "watch":
            tx = self.dance_x - 520
            ty = min(440, self.floor(tx) - 60)
        elif self.state == "settle":
            tx, ty = self.roost_point()
        flock.step(dt, tx, ty, self.gathering, self.floor, slab)

        hunting = (self.state == "fly" and (self.light > p.falcon_from or cx > p.falcon_x * p.roost)
                   and not any(s.near(cx) for s in self.squalls))
        hidden = self.shelter or self.fog > 0.5
        if self.state == "free":                       # it comes to look, and thinks better of it
            hunting, hidden = False, self.state_t > 2.5
        fear = None
        for f in self.falcons:
            f.step(dt, flock, hunting and not hidden, self.sun(cx), hidden)
            fear = flock.fear or fear
        flock.fear = fear
        self.falcon_news()
        self.join_strays(cx, cy)
        self.feed(cx, cy)
        self.wind(dt, cx)
        self.wildlife(dt, cx, cy)
        if self.state == "fly":
            for piece in self.pieces:
                piece.step(self, dt, cx, cy)
        self.dance(dt)
        self.tutorial(cx)
        self.end_checks()

    def falcon_news(self):
        for f in self.falcons:
            for what, eight in f.news:
                if what == "cry":
                    self.cue("cry")
                    self.hint("falcon", "The falcon! Tap to ripple as it stoops.")
                elif what == "stoop":
                    self.cue("stoop")
                elif what == "feint":
                    self.hint("feint", "It pulled up short. It has learned your timing.")
                elif what == "miss":
                    self.say("Missed.", 2.0)
                    self.cue("miss")
                elif what == "lost":
                    self.say("Too many to choose from. The falcon turns away." if self.state == "free"
                             else "The falcon has lost you.", 2.5)
                elif what == "catch":
                    self.stats["caught"] += 1
                    if eight:
                        self.fates[eight] = "falcon"
                    self.say(f"The falcon took {NAMES[eight - 1]}." if eight else "The falcon took one.", 3.0)
                    self.cue("catch", eight)
                    self.fx.append(["feathers", f.x, f.y, self.time, eight])
            f.news = []

    def join_strays(self, cx, cy):
        reach = JOIN_REACH + self.flock.spread()
        keep = []
        for grp in self.groups:
            if abs(grp.x - cx) < reach and abs(grp.y - cy) < reach + 60 and math.hypot(grp.x - cx, grp.y - cy) < reach:
                for x, y, eight in grp.birds:
                    self.flock.add(x, y, self.rng.uniform(40, 120), self.rng.uniform(-140, -80), eight)
                self.stats["regathered" if grp.scattered else "strays"] += len(grp.birds)
                self.cue("join", self.link())
                self.fx.append(["join", grp.x, grp.y, self.time, len(grp.birds)])
            else:
                keep.append(grp)
                if abs(grp.x - cx) < 650 and (grp.called < 0 or (self.fog > 0.3 and self.time - grp.called > 4)):
                    grp.called = self.time             # in fog they keep calling: the calls are the way
                    self.cue("call")
                    if not grp.scattered:
                        self.hint("strays", "Starlings calling! Fly close to them to bring them along.")
        self.groups = keep

    def feed(self, cx, cy):
        reach = 70 + 0.6 * self.flock.spread()
        for m in self.midges:
            if m[2] < 0:
                if abs(m[0] - cx) < reach and abs(m[1] - cy) < reach:
                    m[2] = self.time
                    self.stamina = min(1.0, self.stamina + MIDGE_FOOD)
                    self.tired = self.tired and self.stamina < 0.3
                    self.stats["midges"] += 1
                    n = self.link()
                    self.cue("feed", n)
                    self.fx.append(["feed", m[0], m[1], self.time, n])
                elif 0 < m[0] - cx < 800:
                    self.hint("midges", "Golden midges over the fields: fly through them to feed and get your breath back.")

    def wind(self, dt, cx):
        f, inside = self.flock, 0
        for x0, x1, y in self.place.winds:
            if x0 - 300 < cx < x1 + 300:
                X, Y = f.x, f.y
                for i in range(len(X)):
                    d = abs(Y[i] - y)
                    if x0 < X[i] < x1 and d < WIND_HALF:
                        X[i] += WIND_PUSH * dt * (1 - d / WIND_HALF)
                        inside += 1
            elif 0 < x0 - cx < 900:
                self.hint("wind", "A wind stream ahead, up high: ride it to fly faster.")
        now = inside > 0.4 * len(f)
        if now and not self.in_wind:
            self.cue("gust")
        self.in_wind = now

    def wildlife(self, dt, cx, cy):
        """The herons on the pools: they stand until the flock passes close, then lumber off ahead of it."""
        for h in self.herons:
            if h[4] < 0:
                if abs(h[0] - cx) < 330 and cy > h[1] - 320:
                    h[4] = self.time
                    h[2], h[3] = self.rng2.uniform(70, 100), -80.0
                    self.cue("heron")
            elif h[1] > -100:
                h[3] = -70.0 if h[1] > 380 else h[3] * (1 - dt)
                h[0] += h[2] * dt
                h[1] += h[3] * dt

    def blow_back(self, blown, near=False):
        """Birds torn from the flock: scattered, never dead. They land behind (a squall or a bang throws them far,
        a wire or the fog drops them near) and call until you come back for them."""
        r = self.rng
        for x, y, vx, vy, eight in blown:
            if eight and self.rng3.random() < HOLD:   # the eight are the strongest fliers
                self.flock.add(x, y, vx, vy, eight)
                continue
            self.stats["scattered"] += 1
            if eight:
                self.say(f"{NAMES[eight - 1]} is down, and calling." if near else f"{NAMES[eight - 1]} was blown back.", 3.0)
            back = max(200.0, x - (self.rng2.uniform(60, 200) if near else r.uniform(250, 520)))
            for grp in self.groups:
                if grp.scattered and abs(grp.x - back) < 60:
                    k = len(grp.birds)
                    grp.birds.append((grp.x + k * 7, self.floor(grp.x + k * 7) - 3 if grp.kind == "field" else grp.y, eight))
                    break
            else:
                self.groups.append(self.perch_group(back, 1, low=True, birds=[eight], scattered=True))

    def dance(self, dt):
        p, st, dx, rems = self.place, self.state, self.dance_x, self.remnants
        slab = self.slab if self.slabs else None
        lead = rems[min(self.round, len(rems) - 1)]
        name = ROOST_FLOCK[p.kind]
        if st == "fly":
            cx = self.flock.centre()[0]
            if cx < dx - 3200:
                return
            t = self.time
            for j, rem in enumerate(rems):
                rem.step(dt, dx + APART[j] + 200 * math.sin(t * 0.3 + j), 330 + 60 * math.sin(t * 0.5 + 2 * j), False,
                         self.floor, slab)
            if cx > dx - 700:
                self.stats["flown"] = self.time
                self.go("watch")
                self.cue("watch")
                self.say(f"The {name} is dancing. Watch the shape.", self.shape[6])
        elif st == "watch":
            s = min(1.0, self.state_t / self.shape[6]) * 2 * math.pi
            px, py = self.dance_point(s)
            if not self.trail or math.hypot(px - self.trail[-1][0], py - self.trail[-1][1]) > 14:
                self.trail.append((px, py))
            for j, rem in enumerate(rems):
                if rem is lead:
                    rem.step(dt, px, py, False, self.floor, slab)
                else:
                    rem.step(dt, dx + APART[j], self.floor(dx + APART[j]) - 130, False, self.floor, slab)
            if self.state_t > self.shape[6] + 0.6:
                self.go("echo")
                self.say("Now dance it back.", 3.0)
        elif st == "echo":
            for j, rem in enumerate(rems):
                rem.step(dt, dx + APART[j], self.floor(dx + APART[j]) - 130, False, self.floor, slab)
            cx, cy = self.flock.centre()
            n = len(self.checks)
            for skip in range(3):                      # passing one or two marks late still counts the rest
                k = self.next_check + skip
                if k < n and math.hypot(self.checks[k][0] - cx, self.checks[k][1] - cy) < CHECK_REACH:
                    self.score += 1 / n
                    self.stats["dance"] += 1 / (n * len(p.dance))
                    self.next_check = k + 1
                    self.cue("chime", k)
                    break
            if self.next_check >= n or self.state_t > self.shape[7]:
                joiners = min(len(lead), round(self.share * (0.25 + 0.75 * self.score)))
                for _ in range(joiners):
                    x, y, vx, vy, _e = lead.remove(len(lead) - 1)
                    self.flock.add(x, y, vx, vy)
                self.stats["merged"] += joiners
                if joiners:
                    self.cue("merge")
                self.say(f"{joiners} of the {name} join you." if joiners else f"The {name} stays apart.", 4.0)
                if self.round + 1 < len(p.dance):
                    self.set_round(self.round + 1)
                    self.go("watch")
                    self.cue("watch")
                elif p.finale:
                    self.go("free")
                    self.cue("finale")
                    self.say("Every flock the storm scattered is in the air. Dance.", 5.0)
                    f = self.falcon                    # the falcon comes to look
                    f.state, f.t, f.circle, f.target = "circle", 0.0, 99.0, -1
                    f.x, f.y, f.vx, f.vy = cx + 320, -40.0, 0.0, 0.0
                    self.cue("cry")
                else:
                    self.go("settle")
        elif st == "free":
            cx, cy = self.flock.centre()
            for j, rem in enumerate(rems):
                rem.step(dt, cx + APART[j] * 0.45, cy + 50 * math.sin(self.time * 0.9 + 2 * j), self.gathering,
                         self.floor, slab)
            if self.state_t > FREE_SECONDS:
                self.go("settle")
        elif st == "settle":
            for rem in rems:
                rem.step(dt, *self.roost_point(), False, self.floor, slab)
            if self.state_t > SETTLE_SECONDS:
                self.finish("roost")

    def tutorial(self, cx):
        self.hint("steer", "Point where the flock should fly.")
        if cx > 4000:
            self.hint("gather", "Hold to gather: fast and narrow, but tiring. Rest low over the fields.")

    def go(self, state):
        self.state, self.state_t = state, 0.0

    def end_checks(self):
        if self.state == "fly" and not len(self.flock):
            self.finish("lost")
        elif self.state == "fly" and self.light >= 1.0:
            cold = int(len(self.flock) * NIGHT_LOSS)
            for _ in range(cold):                     # the cold takes the weakest first; the eight hold on longest
                plain = [i for i, e in enumerate(self.flock.eight) if not e]
                eight = self.flock.remove(plain[-1] if plain else len(self.flock) - 1)[4]
                if eight:
                    self.fates[eight] = "cold"
            self.stats["cold"] = cold
            self.finish("night")

    def finish(self, result):
        self.result = result
        if result != "lost":                          # whoever is not with the flock now is left behind
            for e in self.eight_start:
                if e not in self.flock.eight:
                    self.fates.setdefault(e, "behind")
        self.cue("home" if result == "roost" and self.place.finale else result)
        self.go("done")

    # ---- for the painter, the summary and the journey
    @property
    def eight_in_flock(self):
        return sum(1 for e in self.flock.eight if e)

    @property
    def eight_behind(self):
        return sum(1 for g in self.groups for _x, _y, e in g.birds if e)

    @property
    def progress(self):
        return min(1.0, max(0.0, self.flock.centre()[0] / self.roost_x))

    def feathers(self):
        """The evening's three feathers: reached the roost; lost none of the eight; brought a great flock home."""
        home = self.result == "roost"
        return (home, self.result in ("roost", "night") and not self.fates,
                home and len(self.flock) >= self.place.home)
