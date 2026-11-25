"""What each evening's place holds, painted: its far country, water, buildings, hop gardens, turbines, bridges, chalk,
fog, fireworks, gulls and snow. Every function takes the Painter (p) and draws for it; none changes the Evening.
"""

import math
import random

import pygame

from .render import SUN_X, TAU, WHITE, mix
from .settings import AMBER, CREAM, H, LAND, SUN, WINDOW
from .setpieces import HOP_H, Fireworks

ADD = pygame.BLEND_RGB_ADD
HUES = ((255, 130, 90), (255, 214, 120), (130, 214, 255), (180, 255, 150), (255, 150, 226), (246, 246, 255))
COLD = (190, 214, 255)                       # an office window

# Each look's far country: its two ridges (base height, then two waves' height and length), what stands on the nearer
# one and how far apart, what stands in the middle distance (t tree, h farmhouse, b block, p poplar, . nothing),
# whether open water lies at the horizon, and whether thistledown drifts in the light.
LOOKS = {
    "marsh": dict(r1=(556, (10, 700, 6, 210)), r2=(548, (22, 520, 9, 140)), far=("mill", 3000), mid="ttttth", motes=True),
    "weald": dict(r1=(546, (24, 640, 10, 230)), r2=(540, (34, 480, 12, 150)), far=("oast", 1300), mid="tttttth", motes=True),
    "town": dict(r1=(554, (12, 700, 6, 210)), r2=(550, (14, 520, 6, 140)), far=("spire", 900), mid="hhhhtb"),
    "downs": dict(r1=(538, (36, 900, 10, 260)), r2=(532, (44, 640, 12, 190)), far=("turbine", 520), mid="t...", motes=True),
    "estuary": dict(r1=(552, (5, 900, 2, 300)), r2=None, far=("crane", 1700), mid="", sea=True),
    "city": dict(r1=(552, (8, 700, 4, 210)), r2=(552, (6, 520, 3, 140)), far=("tower", 250), mid="bbbbbt"),
    "cliffs": dict(r1=(558, (20, 1100, 8, 330)), r2=None, far=None, mid="", sea=True),   # headlands, far along the coast
    "reeds": dict(r1=(556, (8, 700, 4, 210)), r2=(550, (12, 520, 6, 140)), far=("poplar", 900), mid="tpp.h"),
}


def chalk(p, light):
    """Chalk against the light: in its own shadow, and still the palest thing on the coast."""
    top, _mid, hor = p.cols
    return mix(mix(mix(hor, CREAM, 0.6), top, 0.18), LAND, 0.2 + 0.56 * light)


def far_thing(p, screen, kind, color, sx, y, t, u, light):
    """One thing standing on the far ridge, its foot at (sx, y)."""
    poly, line = pygame.draw.polygon, pygame.draw.line
    if kind == "mill":
        poly(screen, color, [(sx - 7, y), (sx - 4, y - 46), (sx + 4, y - 46), (sx + 7, y)])
        poly(screen, color, [(sx - 6, y - 45), (sx, y - 53), (sx + 6, y - 45)])
        for k in range(4):
            a = t * 0.9 + k * TAU / 4 + u
            line(screen, color, (sx, y - 48), (sx + 30 * math.cos(a), y - 48 + 30 * math.sin(a)), 3)
    elif kind == "oast":                                       # two kilns, their cowls turned from the wind
        for dx in (-9, 9):
            pygame.draw.rect(screen, color, (sx + dx - 7, y - 16, 14, 18))
            poly(screen, color, [(sx + dx - 8, y - 16), (sx + dx, y - 38), (sx + dx + 8, y - 16)])
            line(screen, color, (sx + dx, y - 38), (sx + dx + 6, y - 43), 3)
        pygame.draw.rect(screen, color, (sx + 14, y - 12, 26, 14))
    elif kind == "spire":
        for k in range(5):
            hx = sx - 60 + k * 22 + (int(u) * 7 + k * 13) % 9
            poly(screen, color, [(hx - 9, y + 2), (hx - 9, y - 10), (hx, y - 18), (hx + 9, y - 10), (hx + 9, y + 2)])
        pygame.draw.rect(screen, color, (sx + 52, y - 22, 12, 24))
        poly(screen, color, [(sx + 51, y - 22), (sx + 58, y - 58), (sx + 65, y - 22)])
    elif kind == "turbine":
        line(screen, color, (sx, y), (sx, y - 44), 2)
        for k in range(3):
            a = t * 1.3 + k * TAU / 3 + u
            line(screen, color, (sx, y - 44), (sx + 20 * math.cos(a), y - 44 + 20 * math.sin(a)), 2)
    elif kind == "crane":
        line(screen, color, (sx, y), (sx, y - 44), 3)
        line(screen, color, (sx - 10, y - 40), (sx + 38, y - 54), 2)
        line(screen, color, (sx, y - 52), (sx + 38, y - 54), 1)
        line(screen, color, (sx + 30, y - 52), (sx + 30, y - 30), 1)
        for dx in (-70, -52, 84):                               # masts at their moorings
            line(screen, color, (sx + dx, y + 2), (sx + dx, y - 22 - dx % 9), 1)
    elif kind == "tower":
        r = random.Random(int(u))
        for k in range(6):
            bw, bh = r.randint(12, 26), r.randint(14, 74)
            bx = sx - 60 + k * 21
            pygame.draw.rect(screen, color, (bx, y - bh, bw, bh + 4))
            if light > 0.3 and bh > 30:
                for j in range(r.randint(1, 4)):
                    screen.fill(mix(color, WINDOW, min(1.0, light * 1.3)), (bx + 3 + r.randint(0, bw - 7), y - bh + 5 + j * 9, 2, 2))
        if int(u) % 3 == 0:                                     # a dome and its lantern
            pygame.draw.circle(screen, color, (sx + 80, y - 18), 16)
            pygame.draw.rect(screen, color, (sx + 64, y - 18, 32, 20))
            line(screen, color, (sx + 80, y - 34), (sx + 80, y - 46), 2)
    elif kind == "poplar":
        for k in range(4):
            px = sx + k * 13
            line(screen, color, (px, y + 2), (px, y - 38 - k % 2 * 6), 1)
            pygame.draw.ellipse(screen, color, (px - 3, y - 40 - k % 2 * 6, 7, 30), 1)


def sea(p, screen, cam, t, light):
    """Open water to the horizon, and the sun's road across it."""
    top, mid, hor = p.cols
    water, y0 = mix(mix(hor, mid, 0.55), LAND, 0.3), 548
    pygame.draw.rect(screen, water, (0, y0, p.w, H - y0))
    pygame.draw.line(screen, mix(water, hor, 0.5), (0, y0), (p.w, y0))
    shine = mix(hor, SUN, 0.3)
    for k in range(8):
        y = y0 + 3 + k * 5
        off = (t * (8 + k * 3) + k * 97 + cam * 0.05 * (1 + k)) % 140
        for x in range(int(-off), p.w, 140):
            pygame.draw.line(screen, shine, (x, y), (x + 30 + 10 * math.sin(t + k + x), y))
    road = max(0.0, 1 - light / 0.66)
    if road:
        sx, bright = p.w * SUN_X, mix(water, SUN, 0.75 * road)
        for k in range(14):
            half = 6 + k * 2.2 + 5 * math.sin(t * 2.6 + k * 1.9)
            pygame.draw.line(screen, mix(bright, water, k / 18), (sx - half, y0 + 2 + k * 5), (sx + half, y0 + 2 + k * 5), 2)


def waters(p, screen, ev, cam, t):
    """The rivers, creeks and sea the route crosses."""
    w, y0 = p.w, int(ev.water_y) + 2
    top, mid, hor = p.cols
    water = mix(mix(mid, hor, 0.6), mix(LAND, top, 0.25), 0.34)
    lip = mix(water, hor, 0.55)
    glint = mix(hor, SUN, 0.5 * max(0.0, 1 - ev.light / 0.62))
    sun_x = w * SUN_X
    for a, b in ev.place.waters:
        x0, x1 = max(a - cam, 0), min(b - cam, w)
        if x1 <= x0:
            continue
        pygame.draw.polygon(screen, water, [(a - cam, y0), (b - cam, y0), (b - cam - 46, H), (a - cam + 46, H)])
        pygame.draw.line(screen, lip, (x0, y0), (x1, y0))
        for k in range(6):                                      # the swell catching the sky
            y = y0 + 6 + k * 9
            off = (t * (10 + k * 4) + k * 97 + cam) % 150
            c = mix(water, hor, 0.42 - k * 0.05)
            bank = 46 * (y - y0) / (H - y0)                     # the banks shelve in under the water
            lo, hi = max(a - cam + bank, 0), min(b - cam - bank, w)
            for x in range(int(-off), int(hi), 150):
                xa, xb = max(x, lo), min(x + 34 + 10 * math.sin(t + k + x), hi)
                if xb > xa:
                    pygame.draw.line(screen, c, (xa, y), (xb, y))
        if x0 < sun_x < x1:
            for k in range(6):
                half = (16 - k * 2) + 4 * math.sin(t * 3 + k * 1.7)
                pygame.draw.line(screen, mix(glint, water, k / 7), (sun_x - half, y0 + 4 + k * 7), (sun_x + half, y0 + 4 + k * 7))
    post = mix(LAND, hor, 0.12)
    for kind, x, y in ev.perches:
        if kind == "post" and -10 < x - cam < w + 10:
            pygame.draw.line(screen, post, (x - cam, y0 + 6), (x - cam, y + 3), 5)
            pygame.draw.line(screen, post, (x - cam - 5, y + 3), (x - cam + 5, y + 3), 2)


def windows(style, bw, h, town):
    """Where a building's windows are, and which are lit first: [(dx, dy, when it lights 0..1, cold light?)]."""
    r, out = random.Random(style), []
    for wy in range(16, h - 14, 24 if town else 20):
        for wx in range(9, bw - 12, 22 if town else 16):
            if r.random() < 0.72:
                out.append((wx, wy, r.random(), not town and r.random() < 0.35))
    return out


def buildings(p, screen, ev, cam, t):
    """The town's roofs and the city's blocks: dark against the sky, their windows coming on as the light goes."""
    w, town = p.w, ev.place.look == "town"
    lit = min(1.0, max(0.0, (ev.light - 0.18) * 2.6))
    edge = mix(LAND, p.rim, p.rim_a / 300)
    for x, bw, h, style in ev.buildings:
        sx = x - cam
        if sx + bw < -30 or sx > w + 30:
            continue
        g = ev.ground(x + bw / 2)
        top = g - h
        pygame.draw.rect(screen, LAND, (sx, top, bw + 1, h + 10))
        if town or style % 4 == 0:                              # a pitched roof, under the birds' clearance
            rise = min(18, bw * 0.2)
            pygame.draw.polygon(screen, LAND, [(sx - 4, top + 1), (sx + bw / 2, top - rise), (sx + bw + 4, top + 1)])
            pygame.draw.aaline(screen, edge, (sx + bw / 2, top - rise), (sx + bw + 4, top + 1))
            if style % 3:
                pygame.draw.rect(screen, LAND, (sx + bw * 0.68, top - rise - 4, 9, rise + 4))
        else:
            pygame.draw.line(screen, edge, (sx + bw, top), (sx + bw, top + min(h, 60)))
            if style % 5 == 1:                                  # a mast
                pygame.draw.line(screen, LAND, (sx + bw * 0.4, top), (sx + bw * 0.4, top - 20), 2)
            elif style % 5 == 2:                                # a water tank
                pygame.draw.rect(screen, LAND, (sx + bw * 0.55, top - 12, 18, 12))
        if not lit:
            continue
        panes = p.panes.get(style)
        if panes is None:
            panes = p.panes[style] = windows(style, bw, h, town)
        for k, (wx, wy, when, cold) in enumerate(panes):
            if when < lit:
                screen.fill(COLD if cold else WINDOW, (sx + wx, top + wy, 5, 8 if town else 6))
                if k % 5 == 0:
                    screen.blit(p.window_glow, (sx + wx - 11, top + wy - 10), special_flags=ADD)


def hops(p, screen, ev, cam, t):
    """Hop gardens: poles in rows, the wirework over them, the bines hanging to the ground."""
    w, hor = p.w, p.cols[2]
    pole, wire = mix(LAND, hor, 0.08), mix(LAND, hor, 0.34)
    bine = mix(mix(LAND, (64, 92, 40), 0.4 * (1 - ev.light)), hor, 0.1)
    for hg in ev.hops:
        lo, hi = max(hg.a, cam - 40), min(hg.b, cam + w + 40)
        if hi <= lo:
            continue
        first = hg.a + ((int(lo) - hg.a) // 35) * 35
        for x in range(first, int(hi) + 1, 35):
            g, sx = ev.ground(x), x - cam
            if (x - hg.a) % 140 == 0:
                pygame.draw.line(screen, pole, (sx, g + 4), (sx, g - HOP_H - 5), 3)
                continue
            sway = 3 * math.sin(t * 1.1 + x * 0.05)
            pts = [(sx, g - HOP_H), (sx + sway * 0.5 + 2, g - HOP_H * 0.62), (sx + sway - 2, g - HOP_H * 0.3), (sx + sway * 0.4, g)]
            pygame.draw.lines(screen, bine, False, pts)
            for k in range(6):                                  # leaves and cones along the bine
                u = (k + 0.5) / 6
                lx = sx + sway * math.sin(u * 3.1) + (4 if (k + x // 35) % 2 else -7)
                pygame.draw.ellipse(screen, bine, (lx, g - HOP_H * (1 - u) - 3, 6, 9))
        pts = [(x - cam, ev.ground(x) - HOP_H) for x in range(int(lo), int(hi) + 1, 20)]
        if len(pts) > 1:
            pygame.draw.lines(screen, wire, False, pts, 2)


def turbines(p, screen, ev, cam, t):
    w, hor = p.w, p.cols[2]
    body = mix(mix(hor, CREAM, 0.45), LAND, 0.16 + 0.6 * ev.light)
    ring = mix(p.cols[1], CREAM, 0.16)
    for tb in ev.turbines:
        sx = tb.x - cam
        if not -tb.r - 20 < sx < w + tb.r + 20:
            continue
        g = ev.ground(tb.x) + 3
        pygame.draw.circle(screen, ring, (sx, tb.y), tb.r, 1)   # what the blades sweep
        pygame.draw.polygon(screen, body, [(sx - 7, g), (sx - 3, tb.y), (sx + 3, tb.y), (sx + 7, g)])
        a = tb.angle(ev.time)
        for k in range(3):
            c, s = math.cos(a + k * TAU / 3), math.sin(a + k * TAU / 3)
            pts = [(sx - s * 5 + c * 8, tb.y + c * 5 + s * 8), (sx + c * tb.r, tb.y + s * tb.r), (sx + s * 4, tb.y - c * 4)]
            pygame.draw.polygon(screen, body, pts)
            pygame.draw.aalines(screen, body, True, pts)
        pygame.draw.circle(screen, body, (sx, tb.y), 6)
        if ev.light > 0.45 and int(t * 0.8 + tb.x) % 2:         # its warning light
            screen.blit(p.faded("beacon", p.beacon, min(1.0, (ev.light - 0.45) * 4)), (sx - 14, tb.y - 22), special_flags=ADD)


def slabs(p, screen, ev, cam, t):
    """Bridges and sea arches: solid above, air beneath."""
    w, hor = p.w, p.cols[2]
    pier = mix(LAND, hor, 0.2)
    rock = chalk(p, ev.light)
    lamp = min(1.0, max(0.0, (ev.light - 0.2) * 3))
    for s in ev.slabs:
        lo, hi = max(s.a, int(cam) - 120), min(s.b, int(cam) + w + 120)   # 120: an arch's shoulders reach past its ends
        if hi <= lo:
            continue
        xs = list(range(int(lo), int(hi), 16)) + [int(hi)]
        under = [(x - cam, s.bottom(x)) for x in xs]
        spans = max(2, round((s.b - s.a) / 420)) if s.kind == "girder" else 1
        feet = [s.a + (s.b - s.a) * k / spans for k in range(spans + 1)]
        if s.kind == "girder":
            for fx in feet:                                     # piers, and the ribs that spring from them
                pygame.draw.rect(screen, pier, (fx - cam - 8, s.low, 16, ev.water_y - s.low + 4))
            span = (s.b - s.a) / spans
            for x in range(int(lo) - int(lo) % 40, int(hi), 40):
                u = ((x - s.a) % span) / span
                y = s.low + 6 + 46 * (1 - math.sin(math.pi * u))
                pygame.draw.line(screen, pier, (x - cam, s.low), (x - cam, y))
            for k in range(spans):
                rib = [(s.a + span * (k + j / 16) - cam, s.low + 6 + 46 * (1 - math.sin(math.pi * j / 16))) for j in range(17)]
                pygame.draw.lines(screen, pier, False, rib, 3)
            pygame.draw.polygon(screen, LAND, [(x - cam, s.top) for x in xs] + under[::-1])
            pygame.draw.line(screen, LAND, (lo - cam, s.top - 7), (hi - cam, s.top - 7), 2)
            for x in range(int(lo) - int(lo) % 220, int(hi), 220):
                if x > s.a:
                    pygame.draw.line(screen, LAND, (x - cam, s.top), (x - cam, s.top - 30), 2)
                    if lamp:
                        screen.blit(p.faded("lamp", p.window_glow, lamp), (x - cam - 14, s.top - 46), special_flags=ADD)
                        screen.fill(WINDOW, (x - cam - 2, s.top - 34, 4, 4))
        else:
            side = [(36 + 60 * (1 - j / 8) ** 2.4, s.low - 40 + (ev.water_y + 44 - s.low) * j / 8) for j in range(9)]
            for fx in feet:                                     # the legs it stands on, springing out into the arch
                sx = fx - cam
                pygame.draw.polygon(screen, mix(rock, LAND, 0.14),
                                    [(sx - wd, y) for wd, y in side] + [(sx + wd, y) for wd, y in reversed(side)])
            crown = [(x - cam, s.top + 5 * math.sin(x / 130) + 3 * math.sin(x / 37)) for x in xs]
            if lo == s.a:                                       # its ends: a weathered shoulder, not a cut
                crown = [(s.a - cam - 96, s.low - 40), (s.a - cam - 56, s.top + 44), (s.a - cam - 20, s.top + 10)] + crown
            if hi == s.b:
                crown += [(s.b - cam + 20, s.top + 10), (s.b - cam + 56, s.top + 44), (s.b - cam + 96, s.low - 40)]
            pygame.draw.polygon(screen, rock, crown + under[::-1])
            pygame.draw.lines(screen, LAND, False, crown, 6)   # turf
            for k in range(3):                                  # the chalk's beds
                y = s.top + 34 + k * 30
                bed = [(x - cam, y + 4 * math.sin(x / 210 + k)) for x in xs if y + 6 < s.bottom(x)]
                if len(bed) > 1:
                    pygame.draw.lines(screen, mix(rock, LAND, 0.14), False, bed)


def cliffs(p, screen, ev, cam, ground):
    """The chalk coast: the white face, its beds, and the turf along the top."""
    rock, w = chalk(p, ev.light), p.w
    pygame.draw.polygon(screen, rock, [(0, H)] + ground + [(w, H)])
    for k in range(1, 7):                                       # its beds: the same ground, cut off lower and darker
        y = 372 + k * 40 + 11 * math.sin(k * 2.3)
        bed = [(sx, max(g, y + 5 * math.sin((cam + sx) / 130 + k * 2))) for sx, g in ground]
        pygame.draw.polygon(screen, mix(rock, LAND, 0.065 * k), [(0, H)] + bed + [(w, H)])
    top = ev.water_y - 30
    for (x0, g0), (x1, g1) in zip(ground, ground[1:]):          # turf where it is level enough to grow
        if g0 < top and g1 < top and abs(g1 - g0) < 6:
            pygame.draw.line(screen, LAND, (x0, g0), (x1, g1), 7)


def stacks(p, screen, ev, cam):
    rock, y0 = chalk(p, ev.light), ev.water_y + 4
    for x, h in ev.place.stacks:
        sx = x - cam
        if -70 < sx < p.w + 70:
            ty = ev.water_y - h
            pygame.draw.polygon(screen, rock, [(sx - 44, y0), (sx - 34, ty + 16), (sx - 22, ty), (sx + 24, ty), (sx + 36, ty + 22), (sx + 44, y0)])
            pygame.draw.line(screen, LAND, (sx - 22, ty), (sx + 24, ty), 5)
            pygame.draw.line(screen, mix(rock, LAND, 0.14), (sx - 36, ty + h * 0.45), (sx + 38, ty + h * 0.5))


def pier(p, screen, ev, cam, t):
    """The pier the last flocks of the coast sleep under."""
    x0, x1, deck = ev.roost_x - 460, ev.roost_x + 950, ev.water_y - 104
    if x1 < cam or x0 > cam + p.w:
        return
    wood = mix(LAND, p.cols[2], 0.14)
    lamp = min(1.0, max(0.0, (ev.light - 0.2) * 3))
    for x in range(x0, x1, 70):
        sx = x - cam
        pygame.draw.line(screen, wood, (sx, deck), (sx, ev.water_y + 4), 3)
        if (x - x0) % 140 == 0 and x + 70 < x1:
            pygame.draw.line(screen, wood, (sx, deck + 22), (sx + 70, ev.water_y - 6))
            pygame.draw.line(screen, wood, (sx + 70, deck + 22), (sx, ev.water_y - 6))
    pygame.draw.rect(screen, LAND, (x0 - cam, deck - 6, x1 - x0, 8))
    pygame.draw.line(screen, LAND, (x0 - cam, deck - 20), (x1 - cam, deck - 20))
    for x in range(x0, x1, 35):
        pygame.draw.line(screen, LAND, (x - cam, deck - 20), (x - cam, deck - 6))
    hx = ev.roost_x + 420 - cam                                # the pavilion at its end
    pygame.draw.rect(screen, LAND, (hx, deck - 52, 150, 48))
    pygame.draw.polygon(screen, LAND, [(hx - 8, deck - 52), (hx + 30, deck - 78), (hx + 120, deck - 78), (hx + 158, deck - 52)])
    pygame.draw.line(screen, LAND, (hx + 75, deck - 78), (hx + 75, deck - 104), 2)
    for k in range(5):
        if lamp:
            screen.fill(WINDOW, (hx + 14 + k * 27, deck - 40, 12, 18))
            screen.blit(p.faded("lamp", p.window_glow, lamp), (hx + 6 + k * 27, deck - 46), special_flags=ADD)
    for x in range(x0 + 105, x1, 210):
        pygame.draw.line(screen, LAND, (x - cam, deck - 6), (x - cam, deck - 44), 2)
        if lamp:
            screen.blit(p.faded("lamp", p.window_glow, lamp), (x - cam - 14, deck - 60), special_flags=ADD)
            screen.fill(WINDOW, (x - cam - 2, deck - 48, 4, 4))


def thermals(p, screen, ev, cam, t):
    """Warm air rising: a shimmer over the chimneys, and the bonfire it climbs from."""
    for k, th in enumerate(ev.thermals):
        sx = th.x - cam
        if not -th.half - 80 < sx < p.w + th.half + 80:
            continue
        g = ev.floor(th.x)
        if th.half > 200:                                       # the bonfire
            flick = 0.7 + 0.3 * math.sin(t * 13) * math.sin(t * 7.3)
            screen.blit(p.faded("fire", p.fire_glow, flick), (sx - 110, g - 120), special_flags=ADD)
            pygame.draw.polygon(screen, LAND, [(sx - 34, g + 2), (sx - 8, g - 26), (sx + 10, g - 30), (sx + 36, g + 2)])
            for j in range(5):
                fh = 26 + 22 * abs(math.sin(t * (5 + j) + j * 2))
                fx = sx - 22 + j * 11
                pygame.draw.polygon(screen, mix(AMBER, (255, 110, 50), j % 2 * 0.6), [(fx - 6, g - 18), (fx + 3 * math.sin(t * 9 + j), g - 18 - fh), (fx + 6, g - 18)])
        for j in range(9):
            u = (t * 0.26 + j * 0.111 + k * 0.37) % 1
            x = sx + th.half * 0.75 * math.sin(j * 2.4 + k) + 10 * math.sin(t * 2 + j)
            screen.blit(p.faded("rise", p.rise, math.sin(math.pi * u) * 0.9), (x, g - 30 - u * 400), special_flags=ADD)


def fog(p, screen, ev, cam):
    """The fog banks: the land goes, the flock and the calls stay."""
    edge, core = p.fog_edges, p.fog_core
    for f in ev.fogs:
        if f.b < cam or f.a > cam + p.w:
            continue
        screen.blit(edge[0], (f.a - cam, 0))
        screen.blit(edge[1], (f.b - 240 - cam, 0))
        x = f.a + 240
        while x < f.b - 240:
            wide = min(256, f.b - 240 - x)
            screen.blit(core, (x - cam, 0), (0, 0, wide, H))
            x += wide


def fireworks(p, screen, ev, cam):
    """Rockets on their way up, and the ring that shows where each will burst."""
    warn = mix(p.cols[1], CREAM, 0.3)
    for fw in ev.fireworks:
        for rk in fw.rockets:
            x, y = fw.at(rk, ev.time)
            sx = x - cam
            pygame.draw.line(screen, mix(AMBER, CREAM, 0.4), (sx, y + 30), (sx, y), 2)
            screen.blit(p.dot, (sx - 16, y - 16), special_flags=ADD)
            u = (ev.time - rk[3]) / Fireworks.CLIMB
            pygame.draw.circle(screen, warn, (sx, rk[2]), Fireworks.REACH * (0.25 + 0.75 * u), 1)


def burst(p, screen, sx, y, age, hue):
    """A firework's burst at this age: a flash, then sparks that hang and fall."""
    if age > 1.9:
        return
    col = HUES[hue % len(HUES)]
    if age < 0.25:
        screen.blit(p.faded("burst", p.flash, 1 - age / 0.25), (sx - 60, y - 60), special_flags=ADD)
    k = max(0.0, 1 - age / 1.9) ** 0.7
    c = (int(col[0] * k), int(col[1] * k), int(col[2] * k))
    star = p.faded(f"spark{hue % len(HUES)}", p.sparks[hue % len(HUES)], k)
    r = Fireworks.REACH * (1 - math.exp(-age * 7))
    drop = 46 * age * age
    for j in range(44):
        a = j * TAU / 44 + hue
        ca, sa = math.cos(a), math.sin(a)
        d = r * (0.72 + 0.28 * ((j * 7) % 5) / 4)
        screen.blit(star, (sx + ca * d - 9, y + sa * d + drop - 9), special_flags=ADD)
        for back in (0.86, 0.72, 0.58):                         # the trail each star leaves
            screen.fill(c, (sx + ca * d * back, y + sa * d * back + drop * back, 2, 2), special_flags=ADD)
        if j % 2:
            screen.blit(star, (sx + ca * d * 0.45 - 9, y + sa * d * 0.45 + drop * 0.5 - 9), special_flags=ADD)


def gulls(p, screen, ev, cam, t):
    col = mix(CREAM, p.cols[1], 0.25 + 0.4 * ev.light)
    for gs in ev.gulls:
        g = gs.gull
        if g and -40 < g[0] - cam < p.w + 40:
            x, y = g[0] - cam, g[1]
            flap = math.sin(t * 9)
            way = -1 if g[2] < 0 else 1
            pygame.draw.ellipse(screen, col, (x - 9, y - 3, 18, 6))
            pygame.draw.line(screen, col, (x + way * 8, y), (x + way * 14, y + 1), 2)
            for side in (-1, 1):
                pygame.draw.lines(screen, col, False, [(x, y), (x + side * 13, y - 4 - 9 * flap), (x + side * 25, y - 2 * flap)], 3)


def snow(p, screen, ev, cam, t):
    """Midwinter: snow in the air all evening, thick in the squall."""
    col = mix(p.cols[2], WHITE, 0.72)
    span, heavy = p.w + 40, [(s.a - cam, s.b - cam) for s in ev.squalls]
    for k, (x, y, ph, b) in enumerate(p.flakes):
        sx = (x - cam * (0.5 + 0.4 * b) + 22 * math.sin(t * 0.7 + ph)) % span - 20
        if k % 3 and not any(a < sx < z for a, z in heavy):     # two flakes in three fall only in the squall
            continue
        size = 3 if b > 0.75 else 2
        screen.fill(col, (sx, (y + t * (38 + 50 * b)) % (H + 20) - 10, size, size))
