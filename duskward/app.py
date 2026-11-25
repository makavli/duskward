"""The window, the input and the loop: the title, the journey's map, an evening, its summary, the ending.

The game draws into one surface, 720 px tall and as wide as the screen's shape (16:9 to 21:9), chosen once at start.
On a desktop the GPU scales it smoothly to the window; in a browser (pygbag) the page's canvas is that surface.
The world moves by the real time between frames (capped), so it is smooth at any refresh rate.
"""

import math
import os
import sys
import time

import pygame

from . import __version__, audio, screens
from .autopilot import drive
from .evening import Ctrl, Evening, Group
from .flock import Flock
from .journey import Journey
from .places import PLACES
from .render import Painter
from .settings import H, LAND, MAX_DT, TAP, V_GATHER, W_MAX, W_MIN

WEB = sys.platform == "emscripten"
LAST = len(PLACES) - 1
SURF = {"cliffs": 1.0, "estuary": 0.5}       # how much of the sea each country hears


def view_width(desktop):
    """The surface's width for a screen of this shape: 16:9 is 1280, 21:9 about 1680."""
    w = round(H * desktop[0] / max(1, desktop[1]) / 2) * 2
    return max(W_MIN, min(W_MAX, w))


def fit(window, view):
    s = min(window[0] / view[0], window[1] / view[1])
    w, h = max(1, round(view[0] * s)), max(1, round(view[1] * s))
    return pygame.Rect((window[0] - w) // 2, (window[1] - h) // 2, w, h)


class Controls:
    """Mouse, keys and pad into one Ctrl. One button does two things: tap to ripple, hold to gather."""

    KEYS = {pygame.K_LEFT: (-1, 0), pygame.K_a: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_d: (1, 0),
            pygame.K_UP: (0, -1), pygame.K_w: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_s: (0, 1)}

    def __init__(self, w):
        self.w = w
        self.mode = "mouse"
        self.mouse = (w * 0.62, H * 0.42)
        self.held = {}                      # which button -> when it went down
        self.tap = False
        self.keys = set()
        self.stick = (0.0, 0.0)
        self.pads = {}

    def reset(self):
        self.held.clear()
        self.tap = False

    def press(self, name, now):
        self.held[name] = now

    def release(self, name, now):
        t = self.held.pop(name, None)
        if t is not None and now - t < TAP:
            self.tap = True

    def handle(self, e, now, to_view):
        if e.type == pygame.MOUSEMOTION:
            self.mode, self.mouse = "mouse", to_view(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            self.mode, self.mouse = "mouse", to_view(e.pos)
            if e.button == 1:
                self.press("mouse", now)
            elif e.button == 3:
                self.tap = True
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.release("mouse", now)
        elif e.type == pygame.KEYDOWN:
            if e.key in self.KEYS:
                self.mode = "keys"
                self.keys.add(e.key)
            elif e.key == pygame.K_SPACE:
                self.press("space", now)
            elif e.key in (pygame.K_e, pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.tap = True
        elif e.type == pygame.KEYUP:
            self.keys.discard(e.key)
            if e.key == pygame.K_SPACE:
                self.release("space", now)
        elif e.type == pygame.JOYDEVICEADDED:
            pad = pygame.joystick.Joystick(e.device_index)
            self.pads[pad.get_instance_id()] = pad
        elif e.type == pygame.JOYDEVICEREMOVED:
            self.pads.pop(e.instance_id, None)
            self.stick = (0.0, 0.0)
            self.held.pop("pad", None)
        elif e.type == pygame.JOYBUTTONDOWN:
            if e.button == 0:
                self.press("pad", now)
            elif e.button in (1, 2):
                self.tap = True
        elif e.type == pygame.JOYBUTTONUP and e.button == 0:
            self.release("pad", now)
        elif e.type == pygame.JOYAXISMOTION and e.axis in (0, 1):
            pad = self.pads.get(e.instance_id)
            if pad:
                self.stick = (pad.get_axis(0), pad.get_axis(1))
                if math.hypot(*self.stick) > 0.3:
                    self.mode = "pad"

    def started(self):
        """Any press that should start an evening or move on."""
        return bool(self.held) or self.tap

    def ctrl(self, ev, cam, now):
        c = Ctrl()
        c.ripple, self.tap = self.tap, False
        c.gather = any(now - t >= TAP for t in self.held.values())
        cx, cy = ev.flock.centre()
        if self.mode == "mouse":
            c.tx, c.ty = cam + self.mouse[0], self.mouse[1]
        else:
            if self.mode == "keys":
                dx = sum(self.KEYS[k][0] for k in self.keys)
                dy = sum(self.KEYS[k][1] for k in self.keys)
            else:
                dx, dy = self.stick
                if math.hypot(dx, dy) < 0.25:
                    dx = dy = 0.0
            c.tx, c.ty = (cx + dx * 300, cy + dy * 300) if (dx or dy) else (cx + 90, cy)
        return c


def title_evening(seed, w, place=0):
    """A place before the flock wakes: the eight still sit on their wire. And, for the title, a big flock to turn in
    the sky behind the name."""
    ev = Evening(seed + place, place)
    fl = ev.flock
    ev.groups.insert(0, Group(fl.x[0], fl.y[0], [(x, y, True) for x, y in zip(fl.x, fl.y)], "wire"))
    ev.flock = Flock()
    ev.light = max(ev.light, 0.06)
    deco = Flock(5)
    for k in range(260):
        a = k * 2.399
        deco.add(w * 0.7 + 120 * math.cos(a), 300 + 70 * math.sin(a), 120 * math.sin(a), -120 * math.cos(a))
    return ev, deco


def title_step(deco, ev, w, t, dt):
    deco.step(dt, w * (0.7 + 0.12 * math.sin(t * 0.3)), 330 + 60 * math.sin(t * 0.47), False, ev.floor)


def camera_goal(ev, w):
    """Where the view's left edge wants to be: with the flock, then on the dance, then on the roost."""
    if ev.state == "settle" or ev.result == "roost":
        x = ev.roost_x - w / 2
    elif ev.state in ("watch", "echo", "free"):
        x = ev.dance_x - w / 2
    else:
        x = ev.flock.centre()[0] - w * 0.36
    return max(0.0, min(ev.length - w, x))


def note(text):
    """A line in the page's console, where the browser check reads it."""
    if WEB:
        import platform
        platform.window.console.log("Duskward: " + text)


class App:
    def __init__(self):
        os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")            # smooth scaling
        os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
        audio.pre_init()
        pygame.init()
        audio.init()
        pygame.joystick.init()
        if WEB:
            self.w = W_MIN
            self.canvas = pygame.display.set_mode((self.w, H))
        else:
            from pygame._sdl2.video import Renderer, Texture
            desk = pygame.display.get_desktop_sizes()[0]
            self.w = view_width(desk)
            s = min((desk[0] - 80) / self.w, (desk[1] - 120) / H)
            self.window = pygame.Window("Duskward " + __version__, (int(self.w * s), int(H * s)), resizable=True)
            self.window.minimum_size = (self.w // 3, H // 3)
            self.renderer = Renderer(self.window, vsync=True)
            self.renderer.draw_color = (*LAND, 255)
            self.Texture = Texture
        self.screen = pygame.Surface((self.w, H))
        self.tex = None if WEB else self.Texture.from_surface(self.renderer, self.screen)
        try:
            pygame.mouse.set_system_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
        except (pygame.error, AttributeError):
            pass
        self.painter = Painter(self.w)
        self.controls = Controls(self.w)
        self.seed = int(os.environ.get("DUSKWARD_SEED", "1"))
        self.auto = os.environ.get("DUSKWARD_AUTOPILOT") == "1"         # the bot flies, from DUSKWARD_PLACE (1-8) on
        first = os.environ.get("DUSKWARD_PLACE", "1")
        if WEB:                                                           # in a page: index.html#bot8
            import platform
            tag = str(platform.window.location.hash)
            self.auto, first = tag.startswith("#bot"), tag[4:5]
        self.limit = int(os.environ.get("DUSKWARD_FRAMES", "0"))
        self.journey = Journey.load(keep=not (self.auto or self.limit))   # a test never touches the player's save
        self.full, self.t, self.pick = False, 0.0, -1
        self.wait(min(self.journey.next, LAST), "title")
        if self.auto:
            self.play(int(first) - 1 if first in tuple("12345678") else 0)

    # ---- scenes
    def wait(self, k, scene="journey"):
        """The title or the journey's map, over evening k's place before the flock wakes."""
        if k != self.pick or self.ev.time or self.scene == "play":
            self.pick = k
            self.ev, self.deco = title_evening(self.seed, self.w, k)
        self.scene, self.paused, self.sure, self.cam = scene, False, -9.0, 0.0
        self.controls.reset()

    def play(self, k):
        jn = self.journey
        self.scene, self.paused, self.kept = "play", False, False
        self.ev = Evening(self.seed + k, k, jn.carry(k) if k <= jn.next else None)
        self.cam, self.end_t = 0.0, 0.0
        self.controls.reset()
        audio.cue("card", k)
        note(f"evening {k + 1}")

    def after(self):
        """The summary is read: fly on."""
        ev = self.ev
        if self.auto:
            self.play((ev.index + (ev.result != "lost")) % len(PLACES))
        elif ev.result == "lost":
            self.play(ev.index)
        elif ev.index == LAST and ev.result == "roost" and self.journey.over:
            self.scene, self.end_t = "ending", 0.0
            self.controls.reset()
        else:
            self.wait(min(self.journey.next, LAST))

    # ---- one frame
    def to_view(self, pos):
        if WEB:
            return pos
        r = fit(self.window.size, (self.w, H))
        return (pos[0] - r.x) * self.w / r.w, (pos[1] - r.y) * H / r.h

    def handle(self, e, now):
        if e.type == pygame.QUIT:
            return False
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT):
                self.toggle_full()
                return True
            if e.key == pygame.K_m:
                audio.toggle_mute()
            if e.key == pygame.K_ESCAPE:
                return self.escape()
            if self.scene == "play":
                if e.key == pygame.K_q and self.paused:
                    self.wait(min(self.journey.next, LAST))
                    return True
                if e.key == pygame.K_r and (self.paused or self.ev.state == "done"):
                    self.play(self.ev.index)
                    return True
            elif self.scene == "journey":
                if e.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                    step = -1 if e.key in (pygame.K_LEFT, pygame.K_a) else 1
                    self.wait(max(0, min(self.journey.next, LAST, self.pick + step)))
                elif e.key == pygame.K_n:
                    if now < self.sure:                       # asked twice: the journey begins again
                        self.journey = Journey(keep=self.journey.keep)
                        self.journey.save()
                        self.wait(0)
                    else:
                        self.sure = now + 4.0
        if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and self.scene == "journey":
            x, y = self.to_view(e.pos)
            for k, (sx, sy) in enumerate(screens.stops(self.w)):
                if k <= self.journey.next and abs(x - sx) < 60 and abs(y - sy) < 80 and k != self.pick:
                    self.wait(k)
        if e.type == pygame.JOYBUTTONDOWN and e.button == 7 and self.scene == "play" and self.ev.state != "done":
            self.paused = not self.paused
            self.controls.reset()
        self.controls.handle(e, now, self.to_view)
        return True

    def escape(self):
        """Esc steps back: out of the pause, to the journey, to the title, out of the game."""
        if self.scene == "play" and self.ev.state != "done":
            self.paused = not self.paused
            self.controls.reset()
        elif self.scene == "play" and self.ev.index == LAST and self.ev.result == "roost" and self.journey.over:
            self.after()                                      # the last roost: nothing skips the ending
        elif self.scene in ("play", "ending"):
            self.wait(min(self.journey.next, LAST))
        elif self.scene == "journey":
            self.wait(self.pick, "title")
        else:
            return WEB                                        # a browser tab has nowhere to quit to
        return True

    def mood(self):
        """What the music and the beds follow this frame."""
        ev, scene = self.ev, self.scene
        if scene in ("title", "journey"):
            return {"scene": scene, "place": ev.index, "light": ev.light, "flock": len(self.deco) if scene == "title" else 0,
                    "gather": 0.0, "speed": 0.5, "danger": 0.0, "squall": 0.0, "paused": False, "result": None}
        f, n, p = ev.flock, len(ev.flock), ev.place
        cx = f.centre()[0]
        every = n + sum(len(r) for r in ev.remnants) if ev.state == "free" else n
        return {"scene": "ending" if scene == "ending" else ("summary" if ev.state == "done" else "play"),
                "place": ev.index, "light": ev.light, "flock": every, "gather": f.g,
                "speed": min(1.0, math.hypot(sum(f.vx), sum(f.vy)) / max(1, n) / V_GATHER),
                "danger": 1.0 if any(fa.state in ("circle", "stoop", "feint") for fa in ev.falcons) else 0.0,
                "squall": 1.0 if any(s.a - 150 < cx < s.b + 150 and not s.snow for s in ev.squalls) else 0.0,
                "wind": 1.0 if ev.in_wind or any(s.snow and s.near(cx) for s in ev.squalls) else 0.0,
                "fog": ev.fog, "sea": SURF.get(p.look, 0.0), "shelter": 1.0 if ev.shelter else 0.0,
                "festive": 1.0 if any(fw.a - 300 < cx < fw.b + 300 for fw in ev.fireworks) else 0.0,
                "finale": 1.0 if p.finale and (ev.state == "free" or ev.result == "roost") else 0.0,
                "paused": self.paused, "result": ev.result, "progress": ev.progress,
                "course": 1.0 if any(c.state == "lead" for c in ev.courses) else 0.0}

    def frame(self, dt):
        now = time.perf_counter()
        for e in pygame.event.get():
            if not self.handle(e, now):
                return False
        self.t += dt
        ev = self.ev
        if self.scene == "title":
            title_step(self.deco, ev, self.w, self.t, dt)
            screens.title(self.painter, self.screen, ev, self.deco, self.t)
            if self.controls.started():
                self.wait(self.pick)
        elif self.scene == "journey":
            screens.journey(self.painter, self.screen, ev, self.journey, self.pick, self.t, now < self.sure)
            if self.controls.started():
                self.play(self.pick)
        elif self.scene == "ending":
            self.end_t += dt
            ev.step(dt, Ctrl())
            screens.ending(self.painter, self.screen, ev, self.journey, self.cam, self.t)
            if self.end_t > 2.0 and self.controls.started():
                self.wait(LAST)
            elif self.end_t <= 2.0:
                self.controls.reset()
        else:
            if not self.paused:
                ctrl = drive(ev) if self.auto else self.controls.ctrl(ev, self.cam, now)
                ev.step(dt, ctrl)
                for name, n in ev.sounds:
                    audio.cue(name, n)
                self.cam += (camera_goal(ev, self.w) - self.cam) * min(1.0, dt * 2.5)
            self.painter.draw(self.screen, ev, self.cam, self.t, hud=ev.state != "done")
            if self.paused:
                screens.paused(self.painter, self.screen)
            if ev.state == "done":
                if not self.kept:                             # the night is written once, as it falls
                    self.kept = True
                    self.journey.record(ev.index, ev)
                    note(f"evening {ev.index + 1} ended: {ev.result}")
                self.end_t += dt
                if self.end_t > 2.0:
                    screens.summary(self.painter, self.screen, ev, self.journey)
                    if self.controls.started() or (self.auto and self.end_t > 6):
                        self.after()
                else:
                    self.controls.reset()
        audio.update(dt, self.mood())
        self.present()
        return True

    def present(self):
        if WEB:
            self.canvas.blit(self.screen, (0, 0))
            pygame.display.flip()
            return
        self.tex.update(self.screen)
        self.renderer.clear()
        self.tex.draw(dstrect=fit(self.window.size, (self.w, H)))
        self.renderer.present()

    def toggle_full(self):
        if WEB:
            return
        self.full = not self.full
        if self.full:
            self.window.set_fullscreen(desktop=True)
        else:
            self.window.set_windowed()

    def run(self):
        clock, last, shown = pygame.time.Clock(), time.perf_counter(), 0
        while True:
            clock.tick(400)                                 # a brake, for a driver that ignores vsync
            now = time.perf_counter()
            dt, last = min(MAX_DT, now - last), now
            if not self.frame(dt):
                break
            shown += 1
            if self.limit and shown >= self.limit:
                break
        self.tex = self.renderer = self.window = None        # textures, renderer, window, before SDL goes
        pygame.quit()

    async def run_web(self):
        import asyncio
        last = time.perf_counter()
        while True:
            now = time.perf_counter()
            dt, last = min(MAX_DT, now - last), now
            if not self.frame(dt):
                break
            await asyncio.sleep(0)                          # the browser paints and runs its events here


def main():
    App().run()
    sys.exit(0)
