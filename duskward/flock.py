"""The flock: every bird steers by the birds around it, never by a leader.

Positions and velocities live in plain lists, which are fast in CPython and in the browser's Python. Each step bins
the birds into a grid once, sums every 3x3 block of cells once, and then each bird reads one block, so the cost grows
with the number of birds and not with its square.
"""

import math
import random

from .settings import (ALIGN, ATTRACT, ATTRACT_G, CELL, COHERE, COHERE_G, FLOOR_GAP, ORBIT, RIPPLE_BAND,
                       RIPPLE_PUSH, RIPPLE_REACH, RIPPLE_SPEED, SEP_CELL, SEPARATE, V_GATHER, V_MAX, V_MIN)

ROW = 4096                                       # a cell's key is column * ROW + row + ROW // 4
NINE = [dx * ROW + dy for dx in (-1, 0, 1) for dy in (-1, 0, 1)]


def key(x, y, cell):
    return int(x // cell) * ROW + int(y // cell) + ROW // 4


def blocks(cells, width):
    """{cell: per-cell sums} -> {cell: the sums over its 3x3 block}."""
    out = {}
    get = cells.get
    for k in cells:
        tot = [0.0] * width
        for o in NINE:
            c = get(k + o)
            if c:
                for j in range(width):
                    tot[j] += c[j]
        out[k] = tot
    return out


class Flock:
    FIELDS = ("x", "y", "vx", "vy", "ph", "z", "eight", "flash", "ids")

    def __init__(self, seed=0):
        for f in self.FIELDS:
            setattr(self, f, [])
        self.rng = random.Random(seed)
        self.next_id = 0
        self.g = 0.0                              # how gathered the flock is, 0..1, eased toward the button
        self.ripples = []                         # [x, y, radius]
        self.fear = None                          # (x, y) of a stooping falcon

    def __len__(self):
        return len(self.x)

    def add(self, x, y, vx=0.0, vy=-90.0, eight=0):
        """eight: 0 for a common starling, 1..8 for one of the eight (which one)."""
        r = self.rng.random
        self.x.append(x); self.y.append(y); self.vx.append(vx); self.vy.append(vy)
        self.ph.append(r() * 6.283); self.z.append(r()); self.eight.append(eight); self.flash.append(0.0)
        self.ids.append(self.next_id)
        self.next_id += 1
        return self.next_id - 1

    def remove(self, i):
        """Takes bird i out (the last bird takes its place). Returns its (x, y, vx, vy, eight)."""
        out = (self.x[i], self.y[i], self.vx[i], self.vy[i], self.eight[i])
        for f in self.FIELDS:
            a = getattr(self, f)
            a[i] = a[-1]
            a.pop()
        return out

    def index(self, bird_id):
        try:
            return self.ids.index(bird_id)
        except ValueError:
            return -1

    def centre(self):
        n = len(self.x)
        if not n:
            return 0.0, 0.0
        return sum(self.x) / n, sum(self.y) / n

    def spread(self):
        """Root mean square distance from the centre."""
        n = len(self.x)
        if not n:
            return 0.0
        cx, cy = self.centre()
        return math.sqrt(sum((x - cx) ** 2 + (y - cy) ** 2 for x, y in zip(self.x, self.y)) / n)

    def nearest(self, i):
        """Distance from bird i to its nearest neighbour (how exposed it is)."""
        x, y, best = self.x[i], self.y[i], 1e9
        for j in range(len(self.x)):
            if j != i:
                d = (self.x[j] - x) ** 2 + (self.y[j] - y) ** 2
                if d < best:
                    best = d
        return math.sqrt(best)

    def ripple(self, x, y):
        self.ripples.append([x, y, 0.0])

    def step(self, dt, tx, ty, gather, floor, slab=None):
        """One step toward the target (tx, ty). floor(x) is the ground's height under x; slab(x) is None or the
        (top, bottom) of something solid in the air over x (a bridge deck, a sea arch's roof)."""
        self.g += ((1.0 if gather else 0.0) - self.g) * min(1.0, dt * 3.0)
        for r in self.ripples:
            r[2] += RIPPLE_SPEED * dt
        self.ripples = [r for r in self.ripples if r[2] < RIPPLE_REACH]
        n = len(self.x)
        if not n:
            return
        X, Y, VX, VY, PH, Z, FL = self.x, self.y, self.vx, self.vy, self.ph, self.z, self.flash
        big, fine, kb, kf = {}, {}, [0] * n, [0] * n
        for i in range(n):
            x, y = X[i], Y[i]
            k = kb[i] = key(x, y, CELL)
            c = big.get(k)
            if c is None:
                big[k] = [1, x, y, VX[i], VY[i]]
            else:
                c[0] += 1; c[1] += x; c[2] += y; c[3] += VX[i]; c[4] += VY[i]
            k = kf[i] = key(x, y, SEP_CELL)
            c = fine.get(k)
            if c is None:
                fine[k] = [1, x, y]
            else:
                c[0] += 1; c[1] += x; c[2] += y
        bb, fb = blocks(big, 5), blocks(fine, 3)

        g = self.g
        coh = COHERE + (COHERE_G - COHERE) * g
        att = ATTRACT + (ATTRACT_G - ATTRACT) * g
        orb = ORBIT * (1 - 0.6 * g)
        sep = SEPARATE * (1 - 0.5 * g)
        vmax = V_MAX + (V_GATHER - V_MAX) * g
        flap = 15 + 6 * g
        fear, rips, hypot = self.fear, self.ripples, math.hypot
        for i in range(n):
            x, y, vx, vy = X[i], Y[i], VX[i], VY[i]
            ax = ay = 0.0
            s = bb[kb[i]]
            m = s[0] - 1
            if m > 0:                                   # match the neighbours' heading, drift to their middle
                ax += ((s[3] - vx) / m - vx) * ALIGN + ((s[1] - x) / m - x) * coh
                ay += ((s[4] - vy) / m - vy) * ALIGN + ((s[2] - y) / m - y) * coh
            f = fb[kf[i]]
            m = f[0] - 1
            if m > 0:                                   # keep out of the closest birds' way
                ex, ey = x - (f[1] - x) / m, y - (f[2] - y) / m
                d = hypot(ex, ey) + 0.5
                if d < 24:
                    push = sep * min(m, 8) / 8 * (1 - d / 24) / d
                    ax += ex * push; ay += ey * push
            dx, dy = tx - x, ty - y
            dl = hypot(dx, dy) + 1e-6
            near = dl / 180 if dl < 180 else 1.0
            o = orb * (1 - 0.8 * near)                  # mill around the target, fly straight at a far one
            ax += (dx * att * near - dy * o) / dl
            ay += (dy * att * near + dx * o) / dl
            for rx, ry, rr in rips:
                ex, ey = x - rx, y - ry
                d = hypot(ex, ey) + 1e-6
                if abs(d - rr) < RIPPLE_BAND:
                    ax += ex / d * RIPPLE_PUSH; ay += ey / d * RIPPLE_PUSH
                    FL[i] = 0.35
            if fear:
                ex, ey = x - fear[0], y - fear[1]
                d = hypot(ex, ey) + 1e-6
                if d < 120:
                    k = 950 * (1 - d / 120) / d
                    ax += ex * k; ay += ey * k
            fy = floor(x) - FLOOR_GAP
            if y > fy:
                ay -= (y - fy) * 30
            if y < 30:
                ay += (30 - y) * 30
            if slab:
                s = slab(x)
                if s:                                   # over it, it is a floor; under it, a ceiling
                    if y < (s[0] + s[1]) / 2:
                        if y > s[0] - 16:
                            ay -= (y - s[0] + 16) * 30
                    elif y < s[1] + 16:
                        ay += (s[1] + 16 - y) * 30
            vx += ax * dt; vy += ay * dt
            sp = hypot(vx, vy) + 1e-6
            if sp > vmax:
                vx *= vmax / sp; vy *= vmax / sp
            elif sp < V_MIN:
                vx *= V_MIN / sp; vy *= V_MIN / sp
            VX[i], VY[i] = vx, vy
            X[i], Y[i] = x + vx * dt, y + vy * dt
            PH[i] += dt * (flap + 7 * Z[i])
            if FL[i] > 0:
                FL[i] -= dt
