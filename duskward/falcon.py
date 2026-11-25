"""The Pale Falcon. It takes the bird furthest from the flock's middle, the way peregrines take stragglers.

A ripple that reaches its chosen bird while it stoops makes it miss. Otherwise the flock's density decides: a bird with
neighbours close around it is hard to pick out. Ripple too soon and it learns to feint: the next stoops pull up short,
wait, and come again. Further south it feints from the first stoop, shows itself for less time, comes out of the sun,
and hunts with its mate.
"""

import math

CONFUSE_RANGE = 240           # a ripple on its bird inside this range makes it miss
EARLY_RANGE = 320             # a ripple while it is further than this is "too soon"
TOP_SPEED = 680


class Falcon:
    def __init__(self, rng, circle=1.8, feint=False, from_sun=False, mate=None):
        self.rng = rng
        self.circle = circle          # seconds it shows itself, high over the flock, before it stoops
        self.always_feints, self.from_sun = feint, from_sun
        self.mate = mate              # the falcon it follows: it comes as that one stoops
        self.state = "away"
        self.x = self.y = self.vx = self.vy = self.t = self.tx = self.ty = 0.0
        self.wait = 5.0
        self.target = -1
        self.early = 0                # ripples sent too soon: the falcon's lesson
        self.feint = self.feinted = False
        self.caught = self.missed = 0
        self.news = []                # ("cry" | "stoop" | "miss" | "catch" | "feint" | "lost", eight) for the evening

    def on_ripple(self):
        if self.state == "stoop" and self.distance() > EARLY_RANGE:
            self.early += 1

    def distance(self):
        return math.hypot(self.tx - self.x, self.ty - self.y) if self.state in ("stoop", "feint") else 1e9

    def pick(self, flock):
        cx, cy = flock.centre()
        far, best = -1, -1.0
        for i in range(len(flock)):
            d = (flock.x[i] - cx) ** 2 + (flock.y[i] - cy) ** 2
            if d > best:
                far, best = i, d
        return flock.ids[far]

    def step(self, dt, flock, hunting, sun=None, hidden=False):
        """hunting: it may come now. sun: where the sun stands in the world, for a falcon that comes out of it.
        hidden: the flock is under cover, and a falcon already on it gives up."""
        self.t += dt
        if self.state == "away":
            if hunting and len(flock):
                if self.mate:
                    self.wait = 0.0 if self.mate.state in ("stoop", "feint") and self.mate.t < 0.3 else 1.0
                else:
                    self.wait -= dt
                if self.wait <= 0:
                    self.target = self.pick(flock)
                    cx, _ = flock.centre()
                    self.state, self.t = "circle", 0.0
                    if self.from_sun and sun:
                        self.x, self.y = sun
                    else:
                        self.x, self.y = cx + self.rng.choice((-1, 1)) * 260, -40.0
                    self.feint = (self.early > 0 or self.always_feints) and self.rng.random() < 0.8
                    self.feinted = False
                    self.news.append(("cry", 0))
            flock.fear = None
            return
        if hidden and self.state in ("circle", "stoop", "feint"):
            self.news.append(("lost", 0))
            self.leave()
        i = flock.index(self.target)
        if i >= 0:
            self.tx, self.ty = flock.x[i], flock.y[i]
        if self.state == "circle":
            cx, cy = flock.centre()
            side = -90 if self.mate else 0
            gx, gy = cx + side + 150 * math.cos(self.t * 2.2), max(60.0, cy - 220) + 20 * math.sin(self.t * 4.4)
            self.vx, self.vy = (gx - self.x) * 3, (gy - self.y) * 3
            if self.t > self.circle:
                if i < 0:
                    self.target = self.pick(flock) if len(flock) else -1
                self.state, self.t = "stoop", 0.0
                self.news.append(("stoop", 0))
        elif self.state in ("stoop", "feint"):
            if i < 0:
                self.leave()
            elif self.state == "feint":
                self.vx *= 1 - dt * 2
                self.vy = -240.0
                if self.t > 0.5:
                    self.state, self.t = "stoop", 0.3
            else:
                dx, dy = self.tx - self.x, self.ty - self.y
                d = math.hypot(dx, dy) + 1e-6
                sp = min(TOP_SPEED, 220 + 620 * self.t)
                turn = min(1.0, dt * 6)
                self.vx += (dx / d * sp - self.vx) * turn
                self.vy += (dy / d * sp - self.vy) * turn
                if self.feint and not self.feinted and d < 260:
                    self.state, self.t, self.feinted = "feint", 0.0, True
                    self.news.append(("feint", 0))
                elif flock.flash[i] > 0 and d < CONFUSE_RANGE:
                    self.missed += 1
                    self.news.append(("miss", flock.eight[i]))
                    self.leave()
                elif d < 12:
                    exposed = flock.nearest(i)
                    chance = min(0.92, max(0.12, (exposed - 4) / 16)) * (0.6 + 0.4 * min(1.0, 60 / len(flock)))
                    if self.rng.random() < chance:
                        eight = flock.remove(i)[4]
                        self.caught += 1
                        self.news.append(("catch", eight))
                    else:
                        self.missed += 1
                        self.news.append(("miss", flock.eight[i]))
                    self.leave()
                elif self.t > 5:
                    self.leave()
        else:                                                  # climbing away
            self.vy -= 420 * dt
            self.vx *= 1 + dt
            if self.y < -80:
                self.state, self.wait = "away", self.rng.uniform(9, 14)
        self.x += self.vx * dt
        self.y += self.vy * dt
        flock.fear = (self.x, self.y) if self.state in ("stoop", "feint") else None

    def leave(self):
        self.state, self.t = "climb", 0.0
        self.vy = -320.0
        self.vx *= 0.5
