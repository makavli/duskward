import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from duskward.app import Controls  # noqa: E402
from duskward.autopilot import drive  # noqa: E402
from duskward.evening import Ctrl, Evening  # noqa: E402
from duskward.settings import RIPPLE_COST, STEP, TAP  # noqa: E402
from tests.helpers import play  # noqa: E402


class EveningTest(unittest.TestCase):
    def test_the_autopilot_reaches_the_reeds(self):
        for seed in (1,):                  # the other places are flown whole by tools/sim.py all
            ev = play(Evening(seed), drive)
            self.assertEqual(ev.result, "roost", f"seed {seed}")
            self.assertGreater(len(ev.flock), ev.stats["start"], f"seed {seed}: the flock should grow")
            self.assertGreater(ev.stats["dance"], 0.3, f"seed {seed}")

    def test_no_falcon_in_the_golden_hour(self):
        ev = Evening(1)
        play(ev, drive, until=lambda ev: ev.light >= ev.place.falcon_from * 0.95)
        self.assertEqual(ev.falcons[0].state, "away")
        self.assertEqual(ev.stats["caught"], 0)

    def put_in_the_squall(self, ev):
        f = ev.flock
        for i in range(len(f)):
            f.x[i] += (ev.squalls[0].a + ev.squalls[0].b) / 2 - 400
            f.y[i] = 320 + (i % 5) * 6
        ev.state = "fly"

    def test_the_squall_scatters_a_loose_flock_more_than_a_gathered_one(self):
        lost = {}
        for gather in (False, True):
            ev = Evening(4)
            for k in range(60):                                    # a flock big enough to measure
                ev.flock.add(ev.flock.x[0] + k % 10 * 8, 300 + k // 10 * 8, 120, 0)
            self.put_in_the_squall(ev)
            start = len(ev.flock)
            play(ev, lambda ev: Ctrl(ev.flock.centre()[0] + 300, 320, gather, False), limit=ev.time + 4)
            lost[gather] = ev.stats["scattered"]
            self.assertEqual(lost[gather] + len(ev.flock),
                             start + ev.stats["strays"] + ev.stats["regathered"] + ev.stats["guided"])
        self.assertGreater(lost[False], 0)
        self.assertLess(lost[True], lost[False])

    def test_a_ripple_costs_stamina_once_per_cooldown(self):
        ev = Evening(1)
        ev.step(STEP, Ctrl(600, 300))
        s = ev.stamina
        ev.step(STEP, Ctrl(600, 300, False, True))
        ev.step(STEP, Ctrl(600, 300, False, True))                  # inside the cooldown: no second ripple
        self.assertAlmostEqual(ev.stamina, s - RIPPLE_COST, delta=0.01)

    def test_hovering_until_dark_ends_the_evening_in_the_open(self):
        ev = play(Evening(2), lambda ev: Ctrl(ev.flock.centre()[0], 250, False, False))
        self.assertIn(ev.result, ("night", "lost"))
        if ev.result == "night":
            self.assertGreater(ev.stats["cold"], 0)


class ControlsTest(unittest.TestCase):
    def test_tap_ripples_and_hold_gathers(self):
        c, ev = Controls(1280), Evening(1)
        down = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0)
        up = pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE, mod=0)
        c.handle(down, 10.0, None)
        c.handle(up, 10.0 + TAP / 2, None)
        tap = c.ctrl(ev, 0, 10.1)
        self.assertTrue(tap.ripple)
        self.assertFalse(tap.gather)
        c.handle(down, 20.0, None)
        hold = c.ctrl(ev, 0, 20.0 + TAP * 2)
        self.assertTrue(hold.gather)
        self.assertFalse(hold.ripple)
        c.handle(up, 21.0, None)
        self.assertFalse(c.ctrl(ev, 0, 21.0).ripple)              # a long hold is not also a tap


if __name__ == "__main__":
    unittest.main()
