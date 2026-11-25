"""The painter: sky, land, birds, weather and the few words on screen. It reads an Evening and never changes it.

What costs the most to draw (clouds, trees, the squall, the grass, the glows) is drawn once into surfaces. Whatever
takes the sky's colours is re-tinted only when the light has moved on a little (retint), not every frame.
"""

import math
import os
import random

import pygame

from . import evening as E
from .places import WORDS
from .settings import AMBER, CLOUD, CREAM, FALCON, GLINT, H, INK, LAND, SILVER, SUN, WINDOW

FONTS = os.path.join(os.path.dirname(__file__), "fonts")
HEADINGS, FLAPS = 24, 4
TAU = 2 * math.pi
MID_Y, HORIZON_Y = 0.55 * H, 0.84 * H
SUN_X = 0.7                                  # the sun's place across the view
WHITE = (255, 255, 255)
FORE = (9, 8, 16)                            # the grass right in front of the eye
ISLE = 430                                   # the lighthouse's rock, in the far ridge's units
SCARER_REACH = 260


def mix(a, b, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def sky_at(sky, light):
    """(top, middle, horizon) colours of this place's sky with this much of the evening gone."""
    for (t0, *c0), (t1, *c1) in zip(sky, sky[1:]):
        if light <= t1:
            u = (light - t0) / (t1 - t0)
            return [mix(a, b, u) for a, b in zip(c0, c1)]
    return list(sky[-1][1:])


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def bird_sprites(color, span, alpha=255, size=14):
    """[heading][flap] -> a small antialiased starling: two pointed wings swept back from the body."""
    k = 4                                                   # drawn at 4x, then smoothed down
    out = []
    for h in range(HEADINGS):
        a = h * TAU / HEADINGS
        fx, fy = math.cos(a), math.sin(a)
        row = []
        for f in range(FLAPS):
            big = pygame.Surface((size * k, size * k), pygame.SRCALPHA)
            c = size * k / 2
            sp = span * (0.72 + 0.28 * math.cos(f * TAU / FLAPS))
            back = span * (0.3 + 0.3 * (1 + math.sin(f * TAU / FLAPS)))
            pts = [(c + (-fy * sp - fx * back) * k, c + (fx * sp - fy * back) * k),
                   (c + fx * 1.4 * k, c + fy * 1.4 * k),
                   (c + (fy * sp - fx * back) * k, c + (-fx * sp - fy * back) * k)]
            pygame.draw.lines(big, color, False, pts, int(1.6 * k))
            pygame.draw.circle(big, color, (c + fx * 0.6 * k, c + fy * 0.6 * k), 1.1 * k)
            s = pygame.transform.smoothscale(big, (size, size))
            if alpha < 255:
                s.set_alpha(alpha)
            row.append(s)
        out.append(row)
    return out


def perch_sprite(color):
    s = pygame.Surface((24, 28), pygame.SRCALPHA)
    pygame.draw.ellipse(s, color, (4, 6, 14, 12))
    pygame.draw.circle(s, color, (16, 7), 4)
    pygame.draw.polygon(s, color, [(5, 14), (0, 24), (8, 16)])
    return pygame.transform.smoothscale(s, (6, 7))


def glow(radius, color, strength=1.0, power=2.2):
    """A soft light for additive blits: the falloff is baked into the colour, since an additive blit ignores alpha."""
    s = pygame.Surface((radius * 2, radius * 2))
    for r in range(radius, 0, -1 if radius < 40 else -2):
        k = strength * (1 - r / radius) ** power
        pygame.draw.circle(s, [int(c * k) for c in color], (radius, radius), r)
    return s


def dim(surface, k):
    """A copy of a glow at k (0..255) of its strength."""
    d = surface.copy()
    d.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
    return d


def tint(mask, color, alpha=255):
    """A white alpha mask in this colour, its alpha scaled by alpha/255."""
    s = mask.copy()
    s.fill((*color, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def soften(small, size):
    """A shape drawn small, scaled up."""
    return pygame.transform.smoothscale(small, size)


def blur(s, r):
    """A soft copy: pygame-ce's gaussian blur, or a scale down and up where a build lacks it."""
    try:
        return pygame.transform.gaussian_blur(s, r, False)
    except (AttributeError, ValueError, pygame.error):
        w, h = s.get_size()
        return soften(soften(s, (max(1, w // r), max(1, h // r))), (w, h))


def whiten(s):
    """A mask's colour back to white after a blur has greyed its edges; its alpha stays."""
    s.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    return s


def rim_of(body, dx, dy):
    """The edge of a white mask that faces away from (dx, dy): what a low sun lights."""
    rim = body.copy()
    rim.blit(body, (dx, dy), special_flags=pygame.BLEND_RGBA_SUB)
    rim.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
    return rim


def cloud_masks(rng, w, h, streak):
    """A cloud as a white body mask, and the belly that the low sun lights from beneath.
    streak: a long thin band of high cloud; otherwise a heaped cumulus."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    if streak:
        for _ in range(rng.randint(4, 7)):
            ew, eh = w * rng.uniform(0.3, 0.62), h * rng.uniform(0.22, 0.45)
            pygame.draw.ellipse(s, WHITE, (rng.uniform(0.05 * w, 0.95 * w - ew), h / 2 - eh / 2 + rng.uniform(-0.12, 0.12) * h, ew, eh))
        body = whiten(blur(s, 5))
        return body, whiten(blur(rim_of(body, 0, -6), 3))
    n = rng.randint(6, 10)
    for i in range(n):
        u = (i + 0.5) / n
        r = h * (0.15 + 0.22 * math.sin(math.pi * u)) * rng.uniform(0.85, 1.15)
        pygame.draw.circle(s, WHITE, (w * (0.14 + 0.72 * u) + rng.uniform(-6, 6), h * 0.68 - r * 0.6), r)
    pygame.draw.ellipse(s, WHITE, (w * 0.12, h * 0.52, w * 0.76, h * 0.24))
    body = whiten(blur(s, 3))
    return body, whiten(blur(rim_of(body, 0, -14), 5))


def tree_masks(rng, h, rad):
    """A hedgerow tree as a white mask and its sun-side rim; the foot of its trunk is at the bottom middle."""
    k = 2
    w2, h2 = int(rad * 3.4) + 10, int(h + rad * 1.5) + 6
    big = pygame.Surface((w2 * k, h2 * k), pygame.SRCALPHA)
    wood = big.copy()                                          # trunk and limbs: too thin to catch a rim
    fx, fy, top = w2 / 2, h2 - 1, h2 - 1 - h
    pygame.draw.line(wood, WHITE, (fx * k, fy * k), (fx * k, (top + rad * 0.5) * k), int(3.5 * k))
    if rad < 24 and h > 85:                                    # a poplar: tall and narrow
        pygame.draw.ellipse(big, WHITE, ((fx - rad * 0.8) * k, (top - rad * 1.2) * k, rad * 1.6 * k, (h * 0.8 + rad) * k))
    else:
        for side in (-1, 1):                                   # two limbs into the crown
            pygame.draw.line(wood, WHITE, (fx * k, (top + rad * 0.9) * k),
                             ((fx + side * rad * 0.7) * k, (top + rad * 0.1) * k), int(2 * k))
        pygame.draw.circle(big, WHITE, (fx * k, top * k), rad * 0.85 * k)
        for _ in range(8):
            a, d = rng.uniform(0, TAU), rng.uniform(0.35, 0.8) * rad
            pygame.draw.circle(big, WHITE, ((fx + math.cos(a) * d * 1.25) * k, (top + math.sin(a) * d * 0.75) * k),
                               rad * rng.uniform(0.42, 0.62) * k)
    rim = rim_of(soften(big, (w2, h2)), -3, 2)
    big.blit(wood, (0, 0))
    return soften(big, (w2, h2)), rim, (w2 // 2, h2 - 1)


def puff(r):
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for k in range(r, 0, -1):
        pygame.draw.circle(s, (255, 255, 255, int(90 * (1 - k / r) ** 0.8)), (r, r), k)
    return s


class Painter:
    def __init__(self, w):
        self.w = w
        f = lambda name, size: pygame.font.Font(os.path.join(FONTS, name), size)  # noqa: E731
        self.fonts = {"title": f("Marcellus-Regular.ttf", 132), "head": f("Marcellus-Regular.ttf", 58),
                      "count": f("AlegreyaSans-Medium.ttf", 44), "big": f("AlegreyaSans-Medium.ttf", 30),
                      "text": f("AlegreyaSans-Regular.ttf", 26), "small": f("AlegreyaSans-Regular.ttf", 21),
                      "card": f("Marcellus-Regular.ttf", 76)}
        self.sets = {}
        for name, col in (("ink", INK), ("silver", SILVER), ("glint", GLINT)):
            self.sets[name] = (bird_sprites(col, 2.5, 150), bird_sprites(col, 3.4), bird_sprites(col, 4.8))
        self.perched = {"ink": perch_sprite(INK), "silver": perch_sprite(SILVER), "glint": perch_sprite(GLINT)}
        self.sun_glow = glow(320, SUN, 0.6)
        self.rays = self.make_rays()
        self.moon_glow = glow(90, (150, 160, 200), 0.5)
        self.dot = glow(16, CREAM, 0.9)
        self.dot_big = glow(30, AMBER, 0.9)
        self.halo = glow(11, GLINT, 0.75, 1.6)
        self.midge_glow = glow(46, AMBER, 0.55)
        self.window_glow = glow(14, WINDOW, 0.7)
        self.flash = glow(60, (255, 196, 120), 0.9, 3.0)
        self.streak = self.make_streak()
        self.dims = {}                                    # (name, level) -> a dimmed glow
        self.cache = {}
        self.sky_light, self.sky = -1.0, None
        self.dark_rows = [False] * H
        r = random.Random(7)
        self.stars = [(r.uniform(0, w), r.uniform(0, H * 0.55), r.uniform(0.3, 1), r.uniform(0.6, 2.4),
                       r.uniform(0, TAU)) for _ in range(140)]
        self.clouds = []                                  # (u, y, parallax, drift, body mask, rim mask, nearness)
        for k in range(10):
            near = k % 3 == 0
            cw, ch = (r.randint(320, 480), r.randint(100, 140)) if near else (r.randint(380, 700), r.randint(36, 60))
            body, rim = cloud_masks(r, cw, ch, not near)
            self.clouds.append((r.uniform(0, w + 700), r.uniform(40, 120) if near else r.uniform(110, 300),
                                0.12 if near else 0.05, r.uniform(4, 10), body, rim, 0.92 if near else 0.6))
        self.tinted = []
        self.grass = self.make_grass(r)
        self.fog = self.make_fog()
        self.bank = self.make_bank()
        self.vignette = self.make_vignette()
        self.puffs = [puff(6), puff(10), puff(15)]
        self.beams = self.make_beams()
        self.motes = [(r.uniform(0, w + 100), r.uniform(200, 600), r.uniform(-14, 22), r.uniform(0, TAU), r.uniform(0.3, 1))
                      for _ in range(70)]
        self.flakes = [(r.uniform(0, w + 40), r.uniform(0, H + 20), r.uniform(0, TAU), r.random()) for _ in range(150)]
        self.beacon = glow(14, (255, 70, 60), 0.9)
        self.fire_glow = glow(110, (255, 150, 70), 0.5)
        self.rise = glow(10, (150, 120, 80), 0.7)
        self.sparks = [glow(9, c, 1.0, 1.4) for c in S.HUES]
        self.shade = pygame.Surface((w, H), pygame.SRCALPHA)
        self.title_glow = None
        self.ev = None                                    # the evening the place's own surfaces were built for

    def enter(self, ev):
        """A new evening: what is built for its place (its far country, its reeds, its squalls)."""
        self.ev, p = ev, ev.place
        self.look = look = S.LOOKS[p.look]
        self.sky_light, self.panes, self.storm_tints = -1.0, {}, {}
        self.trees = {}                                   # (x, h, rad) -> [body, rim mask, foot, tinted rim, tint key]
        r = random.Random(7 + ev.index)
        self.mid, u = [], 0.0
        while look["mid"] and u < ev.length * 0.45 + self.w + 400:
            u += r.uniform(40, 150)
            self.mid.append((u, r.choice(look["mid"]), r.uniform(10, 26), r.uniform(18, 46)))
        self.far, u = [], r.uniform(200, 600)
        while look["far"] and u < ev.length * 0.15 + self.w + 200:
            self.far.append(u)
            u += look["far"][1] * r.uniform(0.7, 1.3)
        self.reeds = [(x, r.uniform(26, 64), r.uniform(0, TAU), r.random() < 0.6)
                      for x in range(p.reeds[0] - 200, p.reeds[1], 5)] if p.kind == "reeds" else []
        self.storms = [self.make_storm(s) for s in ev.squalls]

    # ---- built once
    def make_rays(self):
        """The sun's long rays: soft wedges, blurred, fading with distance, for an additive blit. Made at half size."""
        rw, rh = 550, 380
        s = pygame.Surface((rw, rh))
        cx, cy = rw / 2, rh / 2
        r = random.Random(3)
        for i in range(16):
            a = i * TAU / 16 + r.uniform(-0.12, 0.12)
            spread, reach = r.uniform(0.03, 0.07), r.uniform(0.7, 1.0) * rw / 2
            c = r.uniform(26, 48)
            pygame.draw.polygon(s, (int(c), int(c * 0.78), int(c * 0.5)), [
                (cx, cy), (cx + math.cos(a - spread) * reach, cy + math.sin(a - spread) * reach),
                (cx + math.cos(a + spread) * reach, cy + math.sin(a + spread) * reach)])
        s = blur(s, 7)
        s.blit(glow(rw // 2, WHITE, 1.0, 1.3), (0, rh / 2 - rw / 2), special_flags=pygame.BLEND_RGB_MULT)
        return soften(s, (rw * 2, rh * 2))

    def make_streak(self):
        s = pygame.Surface((150, 5))
        for x in range(150):
            k = math.sin(math.pi * x / 150) ** 1.5
            for y, v in ((1, 0.45), (2, 1.0), (3, 0.45)):
                s.set_at((x, y), (int(120 * k * v), int(108 * k * v), int(84 * k * v)))
        return s

    def make_beams(self):
        """The lighthouse's beam seen from the side as it turns: ten lengths, each facing right and left."""
        length, h = 460, 70
        s = pygame.Surface((length, h))
        for x in range(length):
            u = x / length
            half, k = 2 + 28 * u, (1 - u) ** 1.4
            pygame.draw.line(s, (int(120 * k), int(112 * k), int(88 * k)), (x, h / 2 - half), (x, h / 2 + half))
            pygame.draw.line(s, (int(170 * k), int(160 * k), int(126 * k)), (x, h / 2 - half / 3), (x, h / 2 + half / 3))
        s = blur(s, 3)
        out = []
        for k in range(1, 11):
            b = soften(s, (max(4, length * k // 10), h))
            out.append((b, pygame.transform.flip(b, True, False)))
        return out

    def make_grass(self, r):
        """A tileable band of grass right in front of the eye, 256 wide, repeated across the view."""
        t, h = 256, 64
        tile = pygame.Surface((t * 2, h * 2), pygame.SRCALPHA)
        for _ in range(170):
            x, bh = r.uniform(0, t * 2), r.uniform(14, 58) * 2
            lean = r.uniform(-14, 14)
            for dx in (-t * 2, 0, t * 2):                 # drawn three times: the tile wraps cleanly
                pygame.draw.polygon(tile, FORE, [(x + dx - 3, h * 2), (x + dx + lean, h * 2 - bh), (x + dx + 3, h * 2)])
        pygame.draw.rect(tile, FORE, (0, h * 2 - 14, t * 2, 14))
        tile = soften(tile, (t, h))
        out = pygame.Surface((self.w + t, h), pygame.SRCALPHA)
        for x in range(0, self.w + t, t):
            out.blit(tile, (x, 0))
        return out

    def make_fog(self):
        """A white band, clear at the top and thicker toward the bottom: mist lying in the low ground."""
        s = pygame.Surface((self.w, 150), pygame.SRCALPHA)
        for y in range(150):
            s.fill((255, 255, 255, int(150 * (y / 150) ** 1.8)), (0, y, self.w, 1))
        return s

    def make_bank(self):
        """A fog bank as white masks: the 240 px over which it rises off the water, the same falling, and its body."""
        small = pygame.Surface((24, 72), pygame.SRCALPHA)
        for x in range(24):
            s = (x / 23) ** 2 * (3 - 2 * x / 23)
            top = 15 + 33 * (1 - s)                               # it lies on the water: the sky shows over it
            for y in range(72):
                u = min(1.0, max(0.0, (y - top) / 26))
                small.set_at((x, y), (255, 255, 255, int(240 * s ** 0.6 * u * u * (3 - 2 * u))))
        edge = soften(small, (240, H))
        return edge, pygame.transform.flip(edge, True, False), pygame.transform.scale(edge.subsurface((239, 0, 1, H)), (256, H))

    def make_vignette(self):
        sw, sh = self.w // 8, H // 8
        small = pygame.Surface((sw, sh))
        for y in range(sh):
            for x in range(sw):
                d = math.hypot((x - sw / 2) / (sw / 2), (y - sh * 0.45) / (sh * 0.62))
                k = int(255 - 95 * max(0.0, d - 0.55) ** 1.4)
                small.set_at((x, y), (k, k, max(0, min(255, k + 6))))
        return soften(small, (self.w, H))

    def make_storm(self, sq):
        """A squall, from a little before it starts to a little after it ends, as half-size white masks: its body,
        the billows inside it that catch what light is left, and a shade that darkens it toward its belly."""
        a, b = sq.a, sq.b
        x0, k = a - 220, 2
        w, h = (b - a + 440) // k, 560 // k
        body, bill = pygame.Surface((w, h), pygame.SRCALPHA), pygame.Surface((w, h), pygame.SRCALPHA)
        r = random.Random(9)
        edge = []
        for x in range(0, w * k, 30):
            wx = x0 + x
            ramp = max(0.0, min(1.0, (wx - (a - 220)) / 260, ((b + 220) - wx) / 260))
            y = (sq.bottom(min(max(wx, a), b)) + 20) * ramp
            rad = r.uniform(36, 78) * (0.4 + 0.6 * ramp)
            cy = y - rad * 0.4
            pygame.draw.circle(body, WHITE, (x / k, cy / k), rad / k)
            pygame.draw.rect(body, WHITE, (x / k - 8, 0, 16, max(4, cy / k)))
            edge.append((x, cy))
        for _ in range(150):
            x, cy = r.choice(edge)
            rad = r.uniform(24, 60)
            y = r.uniform(0, max(0.0, cy - rad - 10))
            pygame.draw.circle(bill, WHITE, (x / k + r.uniform(-8, 8), y / k), rad / k)
        shade = pygame.Surface((1, h))
        for y in range(h):
            v = int(255 - 105 * min(1.0, (y * k / 470) ** 1.6))
            shade.set_at((0, y), (v, v, v))
        return x0, whiten(blur(body, 3)), whiten(blur(bill, 6)), pygame.transform.scale(shade, (w, h))

    def storm_surface(self, storm, top):
        x0, body, bill, shade = storm
        cloud = mix(mix(CLOUD, top, 0.35), (120, 110, 140), 0.12)
        s = tint(body, cloud)
        s.blit(tint(bill, mix(cloud, CREAM, 0.12), 120), (0, 0))
        s.blit(shade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        return soften(s, (s.get_width() * 2, s.get_height() * 2))

    def faded(self, name, surface, level):
        """A glow at one of 32 strengths. Small glows keep every strength made; a big one keeps only its last."""
        level = max(0, min(31, int(level * 31 + 0.5)))
        small = surface.get_width() * surface.get_height() < 20000
        key = (name, level) if small else name
        d = self.dims.get(key)
        if d is None or (not small and d[0] != level):
            d = self.dims[key] = (level, dim(surface, level * 255 // 31))
        return d[1]

    # ---- helpers
    def text(self, s, font, color, alpha=255):
        key = (s, font, color)
        surf = self.cache.get(key)
        if surf is None:
            if len(self.cache) > 300:
                self.cache.clear()
            surf = self.cache[key] = self.fonts[font].render(s, True, color)
        if alpha < 255:
            surf = surf.copy()
            surf.set_alpha(alpha)
        return surf

    def write(self, screen, s, font, pos, color=CREAM, alpha=255, centre=False, shadow=True):
        surf = self.text(s, font, color, alpha)
        x, y = pos
        if centre:
            x -= surf.get_width() // 2
        if shadow:
            screen.blit(self.text(s, font, LAND, alpha * 2 // 3), (x + 2, y + 2))
        screen.blit(surf, (x, y))
        return surf.get_size()

    def retint(self, light):
        """Everything that takes the sky's colours, again, when the light has moved on."""
        if abs(light - self.sky_light) < 0.003 and self.sky:
            return
        self.sky_light = light
        top, mid, hor = self.cols = sky_at(self.ev.place.sky, light)
        strip = pygame.Surface((1, H))
        for y in range(H):
            c = mix(top, mid, y / MID_Y) if y < MID_Y else mix(mid, hor, (y - MID_Y) / (HORIZON_Y - MID_Y))
            strip.set_at((0, y), c)
            self.dark_rows[y] = lum(c) < 70 or y > HORIZON_Y - 30
        self.sky = pygame.transform.scale(strip, (self.w, H))
        self.sky.blit(self.vignette, (0, 0), special_flags=pygame.BLEND_RGB_MULT)   # baked here, not every frame
        warm =max(0.0, 1 - light / 0.7)                   # how much the low sun still lights the edges
        self.rim = mix(mix(LAND, hor, 0.55), mix(hor, SUN, 0.5), warm)
        self.rim_a = int(70 + 170 * warm)
        body = mix(mix(top, mid, 0.5), LAND, 0.25 + 0.25 * light)
        self.tinted = [(tint(b, mix(body, hor, 0.25 * (1 - near)), int(255 * near)),
                        tint(rm, mix(hor, SUN, 0.35 + 0.4 * warm) if warm else mix(mid, CREAM, 0.15), int(220 * warm + 30)))
                       for *_, b, rm, near in self.clouds]
        haze = self.ev.place.haze                         # the estuary's air is never clear
        self.fog_far = tint(self.fog, mix(hor, CREAM, 0.15), int(200 + 55 * haze))
        self.fog_near = tint(self.fog, mix(hor, mid, 0.4), int(120 + 300 * haze))
        if self.ev.fogs:
            pearl = mix(mix(hor, mid, 0.3), CREAM, 0.3)
            self.fog_edges, self.fog_core = (tint(self.bank[0], pearl), tint(self.bank[1], pearl)), tint(self.bank[2], pearl)
        smoke = mix(mix(hor, mid, 0.5), LAND, 0.35)
        self.smoke = [tint(p, smoke) for p in self.puffs]

    # ---- the scene
    def draw(self, screen, ev, cam, t, hud=True):
        if ev is not self.ev:
            self.enter(ev)
        self.retint(ev.light)
        top, mid, hor = self.cols
        screen.blit(self.sky, (0, 0))
        light, w, p, look = ev.light, self.w, ev.place, self.look
        if light > 0.55:
            a = min(1.0, (light - 0.55) / 0.3)
            for x, y, b, rate, ph in self.stars:
                tw = 0.65 + 0.35 * math.sin(t * rate + ph)
                screen.fill(mix(top, CREAM, a * b * tw * 0.85), ((x - cam * 0.02) % w, y, 2, 2))
        self.sun(screen, light)
        self.moon(screen, light)
        for (u, y, par, drift, *_), (body, rim) in zip(self.clouds, self.tinted):
            span = w + 700
            sx = (u - cam * par - t * drift) % span - 500
            screen.blit(body, (sx, y))
            screen.blit(rim, (sx, y))
        if p.sea:
            self.coast(screen, cam, t, light)
        ridges = [r for r in ((0.06, 0.16, look["r1"]), (0.15, 0.3, look["r2"])) if r[2]]
        for k, (par, dark, (base, waves)) in enumerate(ridges):          # what stands far off stands on the nearer one
            self.ridge(screen, cam * par, mix(hor, LAND, dark), base, waves, look["far"] if k == len(ridges) - 1 else None,
                       t, p.sea[k] if p.sea else 0)
        if look.get("sea"):
            S.sea(self, screen, cam, t, light)
        screen.blit(self.fog_far, (0, 548 - 112))
        if self.mid:
            self.middle(screen, cam * 0.45, mix(hor, LAND, 0.6))
        screen.blit(self.fog_near, (0, 590 - 125))
        self.near(screen, ev, cam, t, top, mid, hor)
        self.groups(screen, ev, cam, t)
        self.midges(screen, ev, cam, t)
        if ev.fogs:
            S.fog(self, screen, ev, cam)
        self.calls(screen, ev, cam)
        self.winds(screen, ev, cam, t)
        if look.get("motes"):
            self.motes_(screen, cam, t, light)
        self.scarers(screen, ev, cam)
        if ev.balloon:
            self.balloon(screen, ev, cam)
        S.thermals(self, screen, ev, cam, t)
        S.fireworks(self, screen, ev, cam)
        self.courses(screen, ev, cam, t)
        for rem in ev.remnants:
            self.birds(screen, rem, cam)
        self.birds(screen, ev.flock, cam)
        for f in ev.falcons:
            self.falcon(screen, ev, cam, f)
        S.gulls(self, screen, ev, cam, t)
        for k in range(len(ev.squalls)):
            self.squall(screen, ev, cam, t, top, hor, k)
        if p.snow:
            S.snow(self, screen, ev, cam, t)
        self.effects(screen, ev, cam)
        self.dance(screen, ev, cam, t)
        screen.blit(self.grass, (-((cam * 1.35) % 256), H - 64))
        if hud:
            self.hud(screen, ev, t)
            self.card(screen, ev)

    def sun(self, screen, light):
        sun_y = 250 + 420 * light / 0.62
        if sun_y > H:
            return
        w, hor = self.w, self.cols[2]
        fade = max(0.0, min(1.0, (HORIZON_Y + 40 - sun_y) / 120))
        sx = w * SUN_X
        rays = self.faded("rays", self.rays, fade * (1 - 0.6 * light))
        screen.blit(rays, (sx - 550, sun_y - 380), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(self.faded("sun", self.sun_glow, fade), (sx - 320, sun_y - 320), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(screen, mix(hor, SUN, 0.35 + 0.65 * fade), (int(sx), int(sun_y)), 30)
        pygame.draw.circle(screen, mix(SUN, (255, 255, 240), fade), (int(sx), int(sun_y)), 24)

    def coast(self, screen, cam, t, light):
        """The sea the marsh begins at, far off on the left, and its lighthouse turning as the light goes."""
        u0 = cam * 0.06
        edge = self.ev.place.sea[0] - u0
        if edge < -40:
            return
        top, mid, hor = self.cols
        sea, y0 = mix(mix(hor, mid, 0.55), LAND, 0.3), 546
        pygame.draw.rect(screen, sea, (0, y0, min(self.w, edge + 40), 74))
        shine = mix(hor, SUN, 0.3)
        for k in range(7):                                      # the swell catching the sky
            y = y0 + 3 + k * 4
            off = (t * (8 + k * 3) + k * 97) % 140
            for x in range(int(-off), int(min(self.w, edge)), 140):
                pygame.draw.line(screen, shine, (x, y), (x + 30 + 10 * math.sin(t + k + x), y))
        sx = ISLE - u0
        if not -60 < sx < self.w + 60:
            return
        rock = mix(hor, LAND, 0.5)
        pygame.draw.polygon(screen, rock, [(sx - 30, y0 + 7), (sx - 16, y0 - 4), (sx + 9, y0 - 7), (sx + 30, y0 + 7)])
        pygame.draw.polygon(screen, rock, [(sx - 6, y0 - 4), (sx - 4, y0 - 46), (sx + 4, y0 - 46), (sx + 6, y0 - 4)])
        band = mix(rock, hor, 0.35)
        for yy in (y0 - 16, y0 - 32):
            pygame.draw.line(screen, band, (sx - 5, yy), (sx + 5, yy), 3)
        pygame.draw.rect(screen, rock, (sx - 5, y0 - 54, 10, 8), 1)
        pygame.draw.polygon(screen, rock, [(sx - 6, y0 - 54), (sx, y0 - 61), (sx + 6, y0 - 54)])
        a = t * 0.9
        c = math.cos(a)
        on = 0.35 + 0.65 * min(1.0, max(0.0, (light - 0.15) / 0.4))
        k, side = min(9, int(abs(c) * 10)), 0 if c > 0 else 1
        b = self.beams[k][side]
        bx = sx if c > 0 else sx - b.get_width()
        screen.blit(self.faded(f"beam{k}{side}", b, on * 0.8), (bx, y0 - 50 - 35), special_flags=pygame.BLEND_RGB_ADD)
        lamp = on * (0.45 + 0.55 * max(0.0, math.sin(a)) ** 4)
        screen.blit(self.faded("lamp", self.dot_big, lamp), (sx - 30, y0 - 80), special_flags=pygame.BLEND_RGB_ADD)

    def motes_(self, screen, cam, t, light):
        """Thistledown and dust adrift in the low sun: they glint while the light is golden."""
        warm = max(0.0, 1 - light / 0.55)
        if not warm:
            return
        span, add = self.w + 100, pygame.BLEND_RGB_ADD
        for x, y, vx, ph, b in self.motes:
            sx = (x + t * vx - cam * 0.5) % span - 50
            k = int(150 * warm * b * (0.55 + 0.45 * math.sin(t * 2.3 + ph)))
            screen.fill((k, int(k * 0.85), int(k * 0.55)), (sx, y + 14 * math.sin(t * 0.7 + ph), 2, 2), special_flags=add)

    def scarers(self, screen, ev, cam):
        for sc in ev.scarers:
            sx = sc.x - cam
            if not -40 < sx < self.w + 40:
                continue
            y = sc.y
            for dx in (-9, 2, 9):
                pygame.draw.line(screen, LAND, (sx, y - 12), (sx + dx, y + 4), 2)
            pygame.draw.line(screen, LAND, (sx - 4, y - 12), (sx + 18, y - 24), 5)
            pygame.draw.circle(screen, LAND, (sx + 18, y - 24), 4)
            pygame.draw.rect(screen, LAND, (sx - 17, y - 10, 7, 14), border_radius=3)
            if 0 < sc.left < 2.05 and int(sc.left * 6) % 2 == 0:          # armed: its pilot light blinks
                screen.blit(self.faded("pilot", self.window_glow, 1.0), (sx - 27, y - 28), special_flags=pygame.BLEND_RGB_ADD)
                screen.fill(AMBER, (sx - 14, y - 15, 3, 3))

    def balloon(self, screen, ev, cam):
        b = ev.balloon
        sx, y = b.x - cam, b.y
        if not -80 < sx < self.w + 80:
            return
        shade = 0.2 + 0.65 * ev.light
        red, cream = mix((176, 62, 54), LAND, shade), mix((232, 206, 162), LAND, shade)

        def hw(v):                                              # the envelope's half width at height v
            d = v - y
            return math.sqrt(max(0.0, 46 * 46 - d * d)) if d <= 10 else 44 - 30 * (d - 10) / 48

        ys = [y - 46 + k * 6.5 for k in range(17)]
        right = [(sx + hw(v), v) for v in reversed(ys)]
        pygame.draw.polygon(screen, cream, [(sx - hw(v), v) for v in ys] + right)
        for f1, f2 in ((-0.82, -0.5), (-0.16, 0.16), (0.5, 0.82)):
            pygame.draw.polygon(screen, red, [(sx + f1 * hw(v), v) for v in ys] + [(sx + f2 * hw(v), v) for v in reversed(ys)])
        pygame.draw.aalines(screen, mix(cream, self.rim, self.rim_a / 255), False, right)
        for dx in (-12, 12):
            pygame.draw.line(screen, LAND, (sx + dx, y + 58), (sx + dx * 0.6, y + 70))
        age = ev.time - b.burn
        if 0 <= age < 1.1:                                      # the burner
            k = math.sin(math.pi * age / 1.1)
            screen.blit(self.faded("flame", self.window_glow, k), (sx - 14, y + 48), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.polygon(screen, mix(AMBER, CREAM, 0.5), [(sx - 3, y + 64), (sx, y + 62 - 14 * k), (sx + 3, y + 64)])
        pygame.draw.rect(screen, mix(LAND, (96, 64, 42), 0.5 * (1 - ev.light)), (sx - 8, y + 70, 16, 12))
        for j, eight in enumerate(b.riders):
            screen.blit(self.perched["glint" if eight else "silver"], (sx - 11 + j * 3, y + 64))

    def courses(self, screen, ev, cam, t):
        add = pygame.BLEND_RGB_ADD
        for c in ev.courses:
            if c.state == "lead":
                pts = c.marks[c.next:c.next + 6]
                if len(pts) > 1:
                    pygame.draw.aalines(screen, mix(CREAM, self.cols[1], 0.72), False, [(x - cam, y) for x, y in pts])
                for j, (x, y) in enumerate(pts):
                    sx = x - cam
                    if j == 0:
                        screen.blit(self.faded("mark", self.dot_big, 0.8 + 0.2 * math.sin(t * 8)), (sx - 30, y - 30), special_flags=add)
                        pygame.draw.circle(screen, mix(AMBER, CREAM, 0.4), (sx, y), 16 + 3 * math.sin(t * 6), 2)
                    else:
                        screen.blit(self.faded("dot", self.dot, 1 - j * 0.15), (sx - 16, y - 16), special_flags=add)
            if len(c.guide):
                self.birds(screen, c.guide, cam)

    def moon(self, screen, light):
        if light < 0.62:
            return
        u = min(1.0, (light - 0.62) / 0.38)
        x, y = self.w * 0.24, H * 0.72 - u * 470
        screen.blit(self.faded("moon", self.moon_glow, u), (x - 90, y - 90), special_flags=pygame.BLEND_RGB_ADD)
        c = mix(self.cols[1], (226, 228, 240), u)
        pygame.draw.circle(screen, c, (int(x), int(y)), 17)
        pygame.draw.circle(screen, mix(c, self.cols[0], 0.18), (int(x) - 5, int(y) + 3), 5)
        pygame.draw.circle(screen, mix(c, self.cols[0], 0.12), (int(x) + 6, int(y) - 5), 3)

    def ridge(self, screen, u0, color, base, waves, far=None, t=0.0, coast=0):
        """A far line of hills; before coast (in its own units) it sinks below the sea. far: what stands on it."""
        a1, l1, a2, l2 = waves

        def y_at(u):
            sink = 0.0 if u >= coast else 75 * min(1.0, (coast - u) / 420) ** 1.5
            return base + a1 * math.sin(u / l1) + a2 * math.sin(u / l2 + 1.3) + sink
        pts = [(0, H)] + [(sx, y_at(u0 + sx)) for sx in range(-8, self.w + 16, 16)] + [(self.w, H)]
        pygame.draw.polygon(screen, color, pts)
        if far:
            for u in self.far:
                sx = u - u0
                if -130 < sx < self.w + 130:
                    S.far_thing(self, screen, far[0], color, sx, y_at(u) + 4, t, u, self.sky_light)

    def middle(self, screen, u0, color):
        base = lambda u: 584 + 12 * math.sin(u / 380 + 2) + 6 * math.sin(u / 97)  # noqa: E731
        pts = [(0, H)] + [(sx, base(u0 + sx)) for sx in range(-8, self.w + 16, 16)] + [(self.w, H)]
        pygame.draw.polygon(screen, color, pts)
        for u, kind, r, h in self.mid:
            sx = u - u0
            if -60 < sx < self.w + 60:
                y = base(u)
                if kind == "t":
                    pygame.draw.circle(screen, color, (sx, y - h * 0.6), r)
                    pygame.draw.circle(screen, color, (sx + r * 0.6, y - h * 0.4), r * 0.8)
                    pygame.draw.circle(screen, color, (sx - r * 0.5, y - h * 0.35), r * 0.7)
                elif kind == "h":                                      # a far farmhouse
                    pygame.draw.polygon(screen, color, [(sx - 16, y + 2), (sx - 16, y - 14), (sx, y - 26), (sx + 16, y - 14), (sx + 16, y + 2)])
                elif kind == "b":                                      # a block of the town
                    pygame.draw.rect(screen, color, (sx - r, y - h * 1.5, r * 2, h * 1.5 + 4))
                elif kind == "p":                                      # a poplar
                    pygame.draw.ellipse(screen, color, (sx - r * 0.3, y - h * 1.7, r * 0.6, h * 1.8))

    def tree(self, x, h, rad):
        key = (x, h, rad)
        tr = self.trees.get(key)
        if tr is None:
            body, rim, foot = tree_masks(random.Random(int(x)), h, rad)
            tr = self.trees[key] = [tint(body, LAND), rim, foot, None, None]
        if tr[4] != self.sky_light:
            tr[3], tr[4] = tint(tr[1], self.rim, self.rim_a), self.sky_light
        return tr

    def near(self, screen, ev, cam, t, top, mid, hor):
        w, p = self.w, ev.place
        ground = [(sx, ev.ground(cam + sx)) for sx in range(-8, w + 16, 8)]
        if p.heights:
            S.cliffs(self, screen, ev, cam, ground)
        else:
            pygame.draw.polygon(screen, LAND, [(0, H)] + ground + [(w, H)])
            pygame.draw.aalines(screen, mix(LAND, self.rim, self.rim_a / 400), False, ground)
        wet = [(a - cam, b - cam) for a, b in p.waters]
        off = int(cam) % 7
        for sx in range(-off, w, 7):                            # tufts along the ground's edge
            if any(a < sx < b for a, b in wet):
                continue
            wx = int(cam) + sx
            hgt = (wx * 7919 % 13) * 0.6 + 2
            g = ev.ground(wx)
            pygame.draw.line(screen, LAND, (sx, g + 1), (sx + (wx % 5 - 2), g - hgt), 2)
        self.pools(screen, ev, cam, t, mid, hor)
        if p.waters:
            S.waters(self, screen, ev, cam, t)
        lit = ev.light > 0.42
        on = min(1.0, (ev.light - 0.42) * 4)
        for i, (x, hw, hh, roof, chimney) in enumerate(ev.houses):
            if x + hw > cam - 40 and x < cam + w + 40:
                g = ev.ground(x + hw / 2) + 2
                sx = x - cam
                pygame.draw.rect(screen, LAND, (sx, g - hh, hw, hh + 4))
                ridge = [(sx - 6, g - hh), (sx + hw / 2, g - hh - roof), (sx + hw + 6, g - hh)]
                pygame.draw.polygon(screen, LAND, ridge)
                pygame.draw.aaline(screen, mix(LAND, self.rim, self.rim_a / 300), ridge[1], ridge[2])
                if chimney:
                    cx, ct = sx + hw * 0.7, g - hh - roof * 0.8
                    pygame.draw.rect(screen, LAND, (cx, ct, 8, roof * 0.6))
                    for k in range(5):                          # smoke, drifting with the evening air
                        age = (t * 0.22 + k / 5 + i * 0.37) % 1
                        sm = self.smoke[min(2, int(age * 3))]
                        sm.set_alpha(int(255 * math.sin(math.pi * age)))
                        r = sm.get_width() / 2
                        screen.blit(sm, (cx + 4 + age * 38 + 5 * math.sin(t + k) - r, ct - age * 80 - r))
                if lit:
                    r = random.Random(i)
                    for k in range(r.randint(1, 3)):
                        if r.random() < on:
                            wx, wy = sx + 10 + k * (hw - 26) / 2.5, g - hh * 0.62
                            screen.fill(WINDOW, (wx, wy, 7, 9))
                            screen.blit(self.window_glow, (wx - 10, wy - 9), special_flags=pygame.BLEND_RGB_ADD)
        if ev.buildings:
            S.buildings(self, screen, ev, cam, t)
        for x, th, rad in ev.trees:
            if -90 < x - cam < w + 90:
                body, _m, (fx, fy), rimmed, _k = self.tree(x, th, rad)
                pos = (x - cam - fx, ev.ground(x) - fy + 2)
                screen.blit(body, pos)
                screen.blit(rimmed, pos)
        if ev.hops:
            S.hops(self, screen, ev, cam, t)
        if ev.turbines:
            S.turbines(self, screen, ev, cam, t)
        wire = mix(LAND, hor, 0.16)
        for x in ev.poles:
            if -20 < x - cam < w + 20:
                top_y = ev.pole_top(x)
                pygame.draw.line(screen, LAND, (x - cam, ev.ground(x) + 4), (x - cam, top_y - 6), 3)
                pygame.draw.line(screen, LAND, (x - cam - 14, top_y), (x - cam + 14, top_y), 3)
        for x0, x1, k in ev.wires:
            if x1 > cam and x0 < cam + w:
                pts = [(x - cam, ev.wire_y(x, k)) for x in range(int(x0), int(x1) + 1, 12)]
                pygame.draw.aalines(screen, wire, False, pts)
        self.herons(screen, ev, cam, t, hor)
        if p.stacks:
            S.stacks(self, screen, ev, cam)
        if ev.slabs:
            S.slabs(self, screen, ev, cam, t)
        if p.kind == "pier":
            S.pier(self, screen, ev, cam, t)
        if self.reeds and p.reeds[0] - 200 - w < cam < p.reeds[1]:
            reed, plume = mix(LAND, hor, 0.1), mix(LAND, hor, 0.22)
            for x, rh, ph, head in self.reeds:
                sx = x - cam
                if -4 < sx < w + 4:
                    g = ev.ground(x) + 4
                    lean = 4 * math.sin(t * 1.3 + ph) + 2 * math.sin(t * 3.1 + ph * 2)
                    pygame.draw.line(screen, reed, (sx, g), (sx + lean, g - rh), 2)
                    if head:
                        pygame.draw.ellipse(screen, plume, (sx + lean * 1.1 - 2, g - rh - 10, 5, 12))

    def pools(self, screen, ev, cam, t, mid, hor):
        w = self.w
        water = mix(mix(mid, hor, 0.6), LAND, 0.25)
        shine = mix(hor, SUN, 0.5 * max(0.0, 1 - ev.light / 0.62))
        sx_sun = w * SUN_X
        for x, pw, ph in ev.pools:
            if x + pw > cam and x < cam + w:
                y = ev.ground(x + pw / 2) + 6
                sx = x - cam
                pygame.draw.ellipse(screen, water, (sx, y, pw, ph * 2))
                pygame.draw.ellipse(screen, mix(water, LAND, 0.35), (sx + pw * 0.08, y + ph * 0.9, pw * 0.84, ph * 1.05))
                pygame.draw.line(screen, mix(water, hor, 0.6), (sx + pw * 0.15, y + 2), (sx + pw * 0.8, y + 2))
                if sx < sx_sun < sx + pw:                       # the sun's path across the water
                    for k in range(5):
                        half = (12 - k * 2) + 4 * math.sin(t * 3 + k * 1.7)
                        yy = y + 3 + k * ph * 0.35
                        pygame.draw.line(screen, mix(shine, water, k / 6), (sx_sun - half, yy), (sx_sun + half, yy))

    def herons(self, screen, ev, cam, t, hor):
        c = mix(LAND, hor, 0.14)
        for x, y, vx, _vy, flushed in ev.herons:
            sx = x - cam
            if not -40 < sx < self.w + 40:
                continue
            if flushed < 0:                                     # standing in the shallows, neck folded
                pygame.draw.line(screen, c, (sx - 2, y), (sx - 1, y - 15), 2)
                pygame.draw.line(screen, c, (sx + 2, y), (sx + 1, y - 15), 2)
                pygame.draw.polygon(screen, c, [(sx - 11, y - 18), (sx + 7, y - 26), (sx + 10, y - 21), (sx - 1, y - 14)])
                pygame.draw.lines(screen, c, False, [(sx + 7, y - 24), (sx + 4, y - 32), (sx + 8, y - 38)], 3)
                pygame.draw.circle(screen, c, (sx + 9, y - 38), 3)
                pygame.draw.line(screen, c, (sx + 9, y - 38), (sx + 19, y - 36), 2)
            else:                                               # lumbering off: slow deep beats, legs trailing
                flap = math.sin((t - flushed) * 4.2)
                pygame.draw.ellipse(screen, c, (sx - 10, y - 4, 22, 8))
                pygame.draw.circle(screen, c, (sx + 12, y - 3), 4)
                pygame.draw.line(screen, c, (sx + 14, y - 3), (sx + 23, y - 1), 2)
                pygame.draw.line(screen, c, (sx - 10, y), (sx - 26, y + 3), 2)
                pygame.draw.polygon(screen, c, [(sx - 7, y - 1), (sx + 6, y - 1), (sx - 4, y - 1 - 30 * flap)])

    def groups(self, screen, ev, cam, t):
        w, dark = self.w, self.dark_rows
        for grp in ev.groups:
            if -20 < grp.x - cam < w + 20:
                bare = grp.kind in ("wire", "stack", "post")           # seen against the sky
                for x, y, eight in grp.birds:
                    hop = max(0.0, math.sin(t * 2.3 + x * 0.7)) ** 8 * 4      # now and then one hops
                    kind = "glint" if eight else ("ink" if bare and not dark[int(y) % H] else "silver")
                    screen.blit(self.perched[kind], (x - cam - 3, y - 6 - hop))

    def calls(self, screen, ev, cam):
        """The strays' calls, as rings you can see: through fog too."""
        for grp in ev.groups:
            age = ev.time - grp.called
            if grp.called >= 0 and age < 1.8 and -60 < grp.x - cam < self.w + 60:
                for k in range(2):
                    a = age - k * 0.3
                    if 0 < a < 1.2:
                        pygame.draw.circle(screen, mix(CREAM, self.cols[2], a / 1.2), (grp.x - cam, grp.y - 4), 8 + 40 * a, 1)

    def midges(self, screen, ev, cam, t):
        w = self.w
        add = pygame.BLEND_RGB_ADD
        for k, (x, y, eaten) in enumerate(ev.midges):
            sx = x - cam
            if eaten >= 0 or not -60 < sx < w + 60:
                continue
            pulse = 0.55 + 0.2 * math.sin(t * 2.5 + k)
            screen.blit(self.faded("midge", self.midge_glow, pulse), (sx - 46, y - 46), special_flags=add)
            for j in range(18):
                a = t * (1.6 + j % 5 * 0.4) + j * 2.4
                px = sx + 26 * math.sin(a) * math.cos(j * 1.3 + t * 0.4)
                py = y + 14 * math.sin(a * 1.7 + j)
                screen.fill((120, 96, 40), (px, py, 2, 2), special_flags=add)

    def winds(self, screen, ev, cam, t):
        w = self.w
        for i, (x0, x1, y) in enumerate(ev.place.winds):
            if x1 < cam or x0 > cam + w:
                continue
            long = x1 - x0                                      # streaks run at one speed, however long the stream
            for k in range(round(22 * long / 1600)):
                u = (t * 352 / long + k * 0.137 + i * 0.3) % 1
                wx = x0 + u * long
                sx = wx - cam
                if not -150 < sx < w:
                    continue
                edge = min(1.0, u * 6, (1 - u) * 6) * (0.55 + 0.45 * math.sin(t * 2 + k))
                yy = y + (k % 5 - 2) * 21 + 6 * math.sin(t * 1.5 + k + wx / 160)
                screen.blit(self.faded("streak", self.streak, edge), (sx, yy), special_flags=pygame.BLEND_RGB_ADD)
            leaf = mix(mix(AMBER, LAND, 0.55), self.cols[2], 0.2)
            for j in range(round(8 * long / 1600)):             # leaves tumbling along it
                u = (t * 480 / long + j * 0.125 + i * 0.21) % 1
                sx = x0 + u * long - cam
                if -10 < sx < w + 10:
                    yy = y + 40 * math.sin(u * 9 + j)
                    a = t * 5 + j
                    dx, dy = 4 * math.cos(a), 2.5 * math.sin(a)
                    pygame.draw.line(screen, leaf, (sx - dx, yy - dy), (sx + dx, yy + dy), 3)

    def birds(self, screen, flock, cam):
        if not len(flock):
            return
        X, Y, VX, VY, PH, Z, EI, FL = flock.x, flock.y, flock.vx, flock.vy, flock.ph, flock.z, flock.eight, flock.flash
        sets, dark, w, atan2 = self.sets, self.dark_rows, self.w, math.atan2
        k = HEADINGS / TAU
        batch, halos = [], []
        for i in range(len(X)):
            sx = X[i] - cam
            if sx < -10 or sx > w + 10:
                continue
            y = Y[i]
            if EI[i]:
                halos.append((self.halo, (sx - 11, y - 11)))
            s = sets["glint" if EI[i] else ("silver" if dark[int(y) % H] else "ink")]
            size = 2 if FL[i] > 0 else (1 if Z[i] > 0.45 or EI[i] else 0)
            head = int(atan2(VY[i], VX[i]) * k + 0.5) % HEADINGS
            batch.append((s[size][head][int(PH[i] * 0.6366) % FLAPS], (sx - 7, y - 7)))
        if halos:
            screen.fblits(halos, pygame.BLEND_RGB_ADD)
        screen.fblits(batch)

    def falcon(self, screen, ev, cam, f):
        if f.state == "away":
            return
        i = ev.flock.index(f.target)
        if i >= 0 and f.state in ("circle", "stoop", "feint"):
            pygame.draw.circle(screen, AMBER, (ev.flock.x[i] - cam, ev.flock.y[i]), 9, 1)
        s = math.hypot(f.vx, f.vy) + 1e-6
        fx, fy = f.vx / s, f.vy / s
        if f.state == "circle":
            fx, fy = (1.0, 0.0) if f.vx >= 0 else (-1.0, 0.0)
        span = 8 if f.state == "stoop" and f.t > 0.5 else 20
        x, y = f.x - cam, f.y
        if f.state == "stoop" and f.t > 0.3:                    # the dive's slipstream
            for k in range(1, 5):
                pygame.draw.aaline(screen, mix(self.cols[1], CREAM, 0.3 / k), (x - fx * 16 + fy * 4, y - fy * 16 - fx * 4),
                                   (x - fx * (40 + 22 * k) + fy * 4, y - fy * (40 + 22 * k) - fx * 4))
        P = lambda a, b: (x + a, y + b)  # noqa: E731
        pts = [P(fx * 13, fy * 13), P(-fy * span - fx * 8, fx * span - fy * 8), P(-fx * 5, -fy * 5),
               P(-fx * 15 - fy * 3, -fy * 15 + fx * 3), P(-fx * 15 + fy * 3, -fy * 15 - fx * 3), P(-fx * 5, -fy * 5),
               P(fy * span - fx * 8, -fx * span - fy * 8)]
        pygame.draw.polygon(screen, FALCON, pts)
        pygame.draw.aalines(screen, FALCON, True, pts)

    def squall(self, screen, ev, cam, t, top, hor, k):
        sq, storm = ev.squalls[k], self.storms[k]
        a, b = sq.a, sq.b
        x0, mask = storm[:2]
        if x0 + mask.get_width() * 2 < cam or x0 > cam + self.w:
            return
        key = round(ev.light * 40)                              # re-tinted every 1/40 of the evening, not every frame
        if self.storm_tints.get(k, (None,))[0] != key:
            self.storm_tints[k] = key, self.storm_surface(storm, top)
        screen.blit(self.storm_tints[k][1], (x0 - cam, -20))
        cloud = mix(CLOUD, top, 0.25)
        belly = mix(cloud, LAND, 0.3)
        lo, hi = max(a, cam - 40), min(b, cam + self.w + 40)
        for x in range(int(lo) - int(lo) % 30 + 30, int(hi), 30):    # the belly churns
            r = 22 + 8 * math.sin(x * 0.13 + t * 0.9)
            pygame.draw.circle(screen, belly, (x - cam + 6 * math.sin(t * 0.7 + x), sq.bottom(x) - r * 0.55), r)
        if hi > lo and not sq.snow:
            r = random.Random(int(t * 30))
            rain, rain2 = mix(cloud, hor, 0.4), mix(cloud, hor, 0.22)
            for j in range(150):
                x = r.uniform(lo, hi)
                y = r.uniform(sq.bottom(x) - 10, ev.ground(x))
                pygame.draw.line(screen, rain if j % 3 else rain2, (x - cam, y), (x - cam - 6, y + 18))
        bx, when = sq.bolt
        age = ev.time - when
        if 0 <= age < 0.35:
            v = int(90 * (1 - age / 0.35))
            screen.fill((v, v, v + 12), special_flags=pygame.BLEND_RGB_ADD)
            if age < 0.22:
                r = random.Random(int(when * 1000))
                y, x, pts = sq.bottom(bx), bx - cam, []
                while y < ev.ground(bx):
                    pts.append((x, y))
                    x += r.uniform(-14, 14)
                    y += r.uniform(12, 30)
                pts.append((x, ev.ground(bx)))
                pygame.draw.lines(screen, (236, 236, 255), False, pts, 2)

    def effects(self, screen, ev, cam):
        add = pygame.BLEND_RGB_ADD
        for kind, x, y, born, n in ev.fx:
            age = ev.time - born
            sx = x - cam
            if not -200 < sx < self.w + 200:
                continue
            if kind == "burst":
                S.burst(self, screen, sx, y, age, n)
            elif kind == "join":
                if age < 0.8:
                    pygame.draw.circle(screen, mix(CREAM, self.cols[1], age / 0.8), (sx, y), 10 + 70 * age, 2)
                if age < 1.6:
                    self.write(screen, f"+{n}", "big", (sx, y - 30 - 40 * age), GLINT, int(255 * min(1.0, (1.6 - age) * 2)),
                               centre=True)
            elif kind == "feed":
                if age < 1.0:
                    for j in range(14):
                        a = j * TAU / 14 + n
                        d = 20 + 90 * age
                        c = int(200 * (1 - age))
                        screen.fill((c, int(c * 0.8), int(c * 0.4)), (sx + math.cos(a) * d, y + math.sin(a) * d * 0.7, 3, 3),
                                    special_flags=add)
            elif kind == "mark" and age < 0.9:
                pygame.draw.circle(screen, mix(CREAM, self.cols[1], age / 0.9), (sx, y), 14 + 50 * age, 2)
                for j in range(10):
                    a = j * TAU / 10 + n
                    c = int(220 * (1 - age / 0.9))
                    screen.fill((c, c, int(c * 0.8)), (sx + math.cos(a) * 70 * age, y + math.sin(a) * 70 * age, 3, 3),
                                special_flags=add)
            elif kind == "bang":
                if age < 0.2:
                    screen.blit(self.faded("muzzle", self.flash, 1 - age / 0.2), (sx + 18 - 60, y - 10 - 60),
                                special_flags=add)
                if age < 0.7:
                    pygame.draw.circle(screen, mix(CREAM, self.cols[1], age / 0.7), (sx + 18, y - 10),
                                       20 + SCARER_REACH * age / 0.7, 2)
                if age < 2.5:
                    for j in range(5):
                        p = self.smoke[min(2, int(age * 1.5))]
                        p.set_alpha(int(220 * (1 - age / 2.5)))
                        r = p.get_width() / 2
                        screen.blit(p, (sx + 18 + j * 7 + age * 26 - r, y - 10 - age * 34 - j * 5 - r))
            elif kind == "feathers" and age < 2.5:
                col = GLINT if n else SILVER
                for j in range(9):
                    fx = sx + (j - 4) * 9 * age + 10 * math.sin(age * 3 + j)
                    fy = y + 36 * age + 6 * math.cos(age * 4 + j * 2)
                    tilt = math.sin(age * 5 + j)
                    pygame.draw.line(screen, mix(col, self.cols[1], age / 2.5), (fx - 3, fy - 2 * tilt), (fx + 3, fy + 2 * tilt), 2)

    def dance(self, screen, ev, cam, t):
        if ev.state == "watch":
            n = len(ev.trail)
            for k, (x, y) in enumerate(ev.trail):
                d = dim(self.dot, int(80 + 175 * k / max(1, n)))
                screen.blit(d, (x - cam - 16, y - 16), special_flags=pygame.BLEND_RGB_ADD)
        elif ev.state == "echo":
            for k, (x, y) in enumerate(ev.checks):
                if k < ev.next_check:
                    screen.blit(self.dot, (x - cam - 16, y - 16), special_flags=pygame.BLEND_RGB_ADD)
                elif k == ev.next_check:
                    d = dim(self.dot_big, int(170 + 85 * math.sin(t * 8)))
                    screen.blit(d, (x - cam - 30, y - 30), special_flags=pygame.BLEND_RGB_ADD)
                else:
                    pygame.draw.circle(screen, mix(CREAM, self.cols[0], 0.55), (x - cam, y), 3)

    def hud(self, screen, ev, t):
        n = len(ev.flock)
        tw, _ = self.write(screen, str(n), "count", (30, 18))
        self.write(screen, "starling" if n == 1 else "starlings", "small", (38 + tw, 36), alpha=210)
        if ev.chain and ev.time - ev.chain_at < E.CHAIN_GAP:
            a = int(255 * min(1.0, (E.CHAIN_GAP - (ev.time - ev.chain_at)) * 1.5))
            self.write(screen, f"chain x{ev.chain + 1}", "text", (48 + tw + 90, 30), AMBER, a)
        behind, alive = ev.eight_behind, ev.eight_in_flock
        faint = mix(CREAM, self.cols[0], 0.6)
        for k in range(8):
            c = (40 + k * 17, 82)
            if k < alive:
                screen.blit(self.halo, (c[0] - 11, c[1] - 11), special_flags=pygame.BLEND_RGB_ADD)
                pygame.draw.circle(screen, GLINT, c, 5)
            elif k < alive + behind:
                pygame.draw.circle(screen, GLINT, c, 5, 1)
            else:
                pygame.draw.line(screen, faint, (c[0] - 4, c[1]), (c[0] + 4, c[1]), 2)
        bar = pygame.Rect(34, 100, 140, 5)
        pygame.draw.rect(screen, mix(CREAM, self.cols[0], 0.72), bar, border_radius=3)
        fill = bar.copy()
        fill.w = int(bar.w * ev.stamina)
        if fill.w:
            pygame.draw.rect(screen, AMBER if ev.tired else CREAM, fill, border_radius=3)
        self.clock(screen, ev)
        if ev.state == "fly":
            y = H - 24
            line = mix(CREAM, self.cols[2], 0.5)
            pygame.draw.line(screen, line, (34, y), (self.w - 34, y), 1)
            px = 34 + (self.w - 68) * ev.progress
            pygame.draw.circle(screen, CREAM, (px, y), 4)
            for k in range(3):
                pygame.draw.line(screen, line, (self.w - 40 + k * 4, y - 2), (self.w - 42 + k * 4, y - 12), 1)
        if ev.messages:
            msg, left = ev.messages[-1]
            self.write(screen, msg, "text", (self.w // 2, 64), alpha=int(255 * min(1.0, left / 0.6)), centre=True)

    def clock(self, screen, ev):
        """The sun is the clock: a small arc, and the sun sinking along it to the horizon."""
        cx, cy, r = self.w - 74, 70, 36
        line = mix(CREAM, self.cols[0], 0.5)
        pygame.draw.arc(screen, line, (cx - r, cy - r, 2 * r, 2 * r), 0, math.pi, 1)
        pygame.draw.line(screen, line, (cx - r - 8, cy), (cx + r + 8, cy), 1)
        a = math.pi * (0.5 - 0.5 * min(1.0, ev.light / 0.8))
        sx, sy = cx + r * math.cos(a), cy - r * math.sin(a)
        screen.blit(self.faded("sun-dot", self.dot_big, 1 - ev.light), (sx - 30, sy - 30), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(screen, mix(GLINT, SILVER, ev.light), (sx, sy), 5)

    def card(self, screen, ev):
        """The evening's name as it begins."""
        tc = ev.time
        if ev.state != "fly" or tc > E.CARD_SECONDS:
            return
        a = int(255 * min(1.0, (tc - 0.3) / 1.0, (E.CARD_SECONDS - tc) / 1.2))
        if a <= 0:
            return
        x = int(self.w * 0.38)                                 # left of the sun
        self.write(screen, "Evening " + WORDS[ev.index], "text", (x, 168), AMBER, a, centre=True)
        self.write(screen, ev.place.name, "card", (x, 196), CREAM, a, centre=True)
        self.write(screen, ev.place.goal, "small", (x, 290), CREAM, a * 3 // 4, centre=True)


from . import scenery as S  # noqa: E402  (it paints for the Painter, with the helpers above)
