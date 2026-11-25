"""One small contrast per mechanic of the later places: the thing happens here, and does not happen there."""

import math
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from duskward.autopilot import drive  # noqa: E402
from duskward.evening import CARRY_MAX, Ctrl, Evening  # noqa: E402
from duskward.falcon import Falcon  # noqa: E402
from duskward.flock import Flock  # noqa: E402
from duskward.settings import STEP  # noqa: E402
from tests.helpers import move, run  # noqa: E402

EIGHT = tuple(range(1, 9))


def hover(gather=False):
    return lambda ev: Ctrl(*ev.flock.centre(), gather, False)


class HopGardenTest(unittest.TestCase):
    def snagged(self, through):
        ev = Evening(1, 1)
        h = ev.hops[0]
        x = h.a + 300
        wire = h.wire(ev, x)
        move(ev, x, wire + 70 if through else wire - 230, extra=40)
        ty = wire - 100 if through else wire - 230
        run(ev, lambda ev: Ctrl(ev.flock.centre()[0] + 100, ty, False, False), 3)
        return ev.stats["snagged"]

    def test_flying_through_the_wires_snags_birds_and_flying_over_them_snags_none(self):
        self.assertGreater(self.snagged(True), 0)
        self.assertEqual(self.snagged(False), 0)


class FireworksTest(unittest.TestCase):
    def burst(self, near, gather):
        ev = Evening(1, 2)
        fw = ev.fireworks[0]
        fw.wait = 1e9                                       # only the rocket put here goes up
        x = fw.a + 800
        y = max(120.0, ev.floor(x) - 260)
        move(ev, x - 100 if near else x - 900, y, extra=60)
        fw.rockets.append([x, ev.floor(x), y, ev.time + 1.0, 0])
        run(ev, hover(gather), 3.0)
        self.assertEqual(fw.rockets, [], "the rocket should have burst")
        return ev.stats["scattered"]

    def test_a_burst_scatters_a_loose_flock_more_than_a_gathered_one(self):
        loose, gathered = self.burst(True, False), self.burst(True, True)
        self.assertGreater(loose, 0)
        self.assertLess(gathered, loose)

    def test_a_flock_outside_the_reach_loses_none(self):
        self.assertEqual(self.burst(False, False), 0)


class ThermalTest(unittest.TestCase):
    def lifted(self, dx, gathering):
        ev = Evening(1, 2)
        th = ev.thermals[0]
        move(ev, th.x + dx, 300, extra=30)
        f, ev.stamina, ev.gathering = ev.flock, 0.5, gathering
        before = list(f.vy)
        th.step(ev, STEP, *f.centre())
        return [b - a for a, b in zip(f.vy, before)], ev.stamina, th

    def test_a_flock_in_the_warm_air_rises_and_gets_its_breath_back(self):
        lift, stamina, th = self.lifted(0, False)
        self.assertTrue(all(d > 0 for d in lift))
        self.assertGreater(sum(lift) / len(lift), 0.5 * th.LIFT * STEP)
        self.assertAlmostEqual(stamina, 0.5 + th.FOOD * STEP)

    def test_a_gathering_flock_is_lifted_but_not_rested(self):
        lift, stamina, _ = self.lifted(0, True)
        self.assertTrue(all(d > 0 for d in lift))
        self.assertAlmostEqual(stamina, 0.5)

    def test_a_flock_beside_the_warm_air_gets_nothing(self):
        ev = Evening(1, 2)
        th = ev.thermals[0]
        lift, stamina, _ = self.lifted(th.half + 300, False)
        self.assertEqual(lift, [0.0] * len(lift))
        self.assertAlmostEqual(stamina, 0.5)


class TurbineTest(unittest.TestCase):
    def knocked(self, turn, radii):
        ev = Evening(1, 3)
        t, f = ev.turbines[0], ev.flock
        while len(f):
            f.remove(0)
        f.add(t.x, t.y)                                     # at the hub, which no blade reaches
        a = t.angle(ev.time) + turn
        for rad in radii:
            f.add(t.x + rad * math.cos(a), t.y + rad * math.sin(a), 0, 0)
        ev.state = "fly"
        t.step(ev, 1.0, *f.centre())                        # a whole second: a bird on a blade is certain to be hit
        return ev.stats["snagged"], len(radii), t

    def test_the_blades_knock_the_birds_they_sweep(self):
        hit, n, _ = self.knocked(0.0, (60, 80, 100, 120, 140))
        self.assertEqual(hit, n)

    def test_birds_between_the_blades_or_past_the_tips_are_left_alone(self):
        ev = Evening(1, 3)
        gap = math.tau / 6
        self.assertEqual(self.knocked(gap, (60, 80, 100, 120, 140))[0], 0)
        t = ev.turbines[0]
        self.assertEqual(self.knocked(0.0, (t.r + 30, t.r + 60, t.r + 90))[0], 0)


class FogTest(unittest.TestCase):
    def fogged(self, gather, inside=True):
        ev = Evening(1, 4)
        fg = ev.fogs[0]
        x = (fg.a + fg.b) / 2 if inside else fg.a - 900
        move(ev, x, max(120.0, ev.floor(x) - 250), extra=60)
        run(ev, hover(gather), 5)
        return ev.stats["fogged"]

    def test_a_loose_flock_loses_birds_in_the_fog_and_a_gathered_one_fewer(self):
        loose = self.fogged(False)
        self.assertGreater(loose, 0)
        self.assertLess(self.fogged(True), loose)

    def test_no_bird_is_lost_outside_the_fog(self):
        self.assertEqual(self.fogged(False, inside=False), 0)


class BridgeTest(unittest.TestCase):
    def flock_at(self, seed, under):
        ev = Evening(seed, 5)
        s = ev.slabs[0]
        x = (s.a + s.b) / 2
        move(ev, x, s.bottom(x) + 40 if under else s.top - 80)
        return ev

    def test_under_a_bridge_there_is_shelter_and_above_it_none(self):
        for under in (True, False):
            ev = self.flock_at(1, under)
            ev.step(STEP, hover()(ev))
            self.assertEqual(ev.shelter, under)

    def stoop(self, seed, under):
        ev = self.flock_at(seed, under)
        f, fa = ev.flock, ev.falcons[0]
        f.x[0] += 300                                       # the bird it takes is alone, and easy to catch
        fa.state, fa.t, fa.target = "stoop", 0.0, f.ids[0]
        fa.x, fa.y = f.x[0], f.y[0]
        ev.step(STEP, hover()(ev))
        return ev.stats["caught"], fa

    def test_a_falcon_on_the_flock_gives_up_under_a_bridge_and_takes_a_bird_above_it(self):
        under = [self.stoop(seed, True) for seed in range(1, 13)]
        above = [self.stoop(seed, False) for seed in range(1, 13)]
        self.assertEqual(sum(c for c, _ in under), 0)
        self.assertTrue(all(fa.state == "climb" for _, fa in under))
        self.assertGreater(sum(c for c, _ in above), 6)

    def falcon_on(self, seed, hidden):
        f = Flock(seed)
        for k in range(3):
            f.add(100 + k * 200, 300, 0, 0, eight=k + 1)
        fa = Falcon(random.Random(seed), circle=0.0)
        fa.state, fa.t, fa.target = "stoop", 0.0, f.ids[0]
        fa.x, fa.y = f.x[0], f.y[0]
        fa.step(STEP, f, True, None, hidden)
        return fa

    def test_a_hidden_falcon_never_catches_and_says_it_lost_the_flock(self):
        seen = [self.falcon_on(s, False) for s in range(20)]
        hid = [self.falcon_on(s, True) for s in range(20)]
        self.assertGreater(sum(fa.caught for fa in seen), 10)
        self.assertEqual(sum(fa.caught for fa in hid), 0)
        self.assertTrue(all(("lost", 0) in fa.news for fa in hid))


class GullTest(unittest.TestCase):
    def gull(self, ripple):
        ev = Evening(1, 5)
        g = ev.gulls[0]
        x = g.a + 600
        move(ev, x, max(150.0, ev.floor(x) - 250), extra=40)
        cx, cy = ev.flock.centre()
        g.gull = [cx + 320, cy, -g.SPEED, 0.0, True]
        fired = []

        def steer(ev):
            fired.append(1)
            return Ctrl(*ev.flock.centre(), False, bool(ripple and len(fired) == 1))
        run(ev, steer, 3)
        return ev.stats["gulls"], ev.stats["scattered"]

    def test_a_ripple_turns_the_gull_away_and_without_one_it_costs_birds(self):
        turned, lost = self.gull(True)
        self.assertEqual((turned, lost), (1, 0))
        turned, lost = self.gull(False)
        self.assertEqual(turned, 0)
        self.assertGreater(lost, 0)


class PlacesTest(unittest.TestCase):
    def test_the_cliffs_have_two_falcons_and_the_marsh_one(self):
        self.assertEqual(len(Evening(1, 6).falcons), 2)
        self.assertEqual(len(Evening(1, 0).falcons), 1)

    def test_the_last_evening_has_three_waiting_roost_flocks(self):
        ev = Evening(1, 7)
        self.assertTrue(ev.place.finale)
        self.assertEqual(len(ev.remnants), 3)
        self.assertTrue(all(len(r) == ev.place.remnant for r in ev.remnants))
        other = Evening(1, 6)
        self.assertFalse(other.place.finale)
        self.assertEqual(len(other.remnants), 1)

    def test_every_place_builds_steps_and_has_a_finite_floor(self):
        for k in range(8):
            with self.subTest(place=k):
                ev = Evening(1 + k, k, (EIGHT, 40) if k else None)
                for _ in range(600):
                    ev.step(STEP, drive(ev))
                for x in range(-200, int(ev.place.length) + 200, 50):
                    self.assertTrue(math.isfinite(ev.floor(x)), x)


class CarryTest(unittest.TestCase):
    def test_a_carry_sets_out_exactly_who_it_names(self):
        ev = Evening(1, 1, ((1, 2, 4), 60))
        self.assertEqual(ev.eight_start, (1, 2, 4))
        self.assertEqual(sorted(e for e in ev.flock.eight if e), [1, 2, 4])
        self.assertEqual(len(ev.flock), 3 + 60)
        self.assertEqual(ev.stats["start"], 63)

    def test_a_carry_above_the_most_is_capped(self):
        ev = Evening(1, 1, ((1, 2, 3), 500))
        self.assertEqual(len(ev.flock), 3 + CARRY_MAX)

    def test_the_first_evening_starts_with_the_eight_alone(self):
        ev = Evening(1, 0, None)
        self.assertEqual(ev.eight_start, EIGHT)
        self.assertEqual(sorted(ev.flock.eight), list(EIGHT))
        self.assertEqual(len(ev.flock), 8)


class FeatherTest(unittest.TestCase):
    def evening(self, result, size=None, fates=None):
        ev = Evening(1)
        size = ev.place.home if size is None else size
        while len(ev.flock) < size:
            ev.flock.add(*ev.flock.centre(), 0, 0)
        while len(ev.flock) > size:
            ev.flock.remove(len(ev.flock) - 1)
        ev.result, ev.fates = result, dict(fates or {})
        return ev

    def test_the_three_feathers_turn_on_and_off(self):
        home = Evening(1).place.home
        cases = [
            (("roost", home, None), (True, True, True)),
            (("roost", home - 1, None), (True, True, False)),            # no great flock
            (("roost", home, {3: "falcon"}), (True, False, True)),        # one of the eight lost
            (("night", home, None), (False, True, False)),                # caught out in the open
            (("night", home, {3: "cold"}), (False, False, False)),
            (("lost", home, None), (False, False, False)),
        ]
        for args, want in cases:
            with self.subTest(args=args):
                got = self.evening(*args).feathers()
                self.assertEqual(tuple(got), want)
                self.assertTrue(all(type(f) is bool for f in got))
                self.assertEqual(len(got), 3)


if __name__ == "__main__":
    unittest.main()
