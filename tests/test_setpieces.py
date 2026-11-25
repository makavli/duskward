import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from duskward.evening import Ctrl, Evening  # noqa: E402
from tests.helpers import move, run  # noqa: E402


class SetPieceTest(unittest.TestCase):
    def test_a_bang_scatters_a_loose_flock_more_than_a_gathered_one(self):
        lost = {}
        for gather in (False, True):
            ev = Evening(4)
            sc = ev.scarers[0]
            move(ev, sc.x - 60, sc.y - 90, extra=60)
            sc.left = 2.5                                   # two ticks, then the bang, while the flock is close
            run(ev, lambda ev: Ctrl(sc.x, sc.y - 90, gather, False), 2.7)
            lost[gather] = ev.stats["scattered"]
        self.assertGreater(lost[False], 0)
        self.assertLess(lost[True], lost[False])

    def fly_trail(self, follow):
        ev = Evening(4)
        c = ev.courses[0]
        move(ev, c.x0 - 500, 250)

        def steer(ev):
            if follow and c.state == "lead":
                x, y = c.marks[min(c.next, len(c.marks) - 1)]
                return Ctrl(x + 60, y, True, False)
            return Ctrl(ev.flock.centre()[0] + 300, 40, False, False)
        run(ev, steer, 40)
        self.assertEqual(c.state, "done")
        return c, ev.stats["guided"]

    def test_following_the_trail_brings_more_of_the_guide_flock(self):
        c, followed = self.fly_trail(True)
        self.assertGreaterEqual(c.hits, len(c.marks) - 2)
        _, ignored = self.fly_trail(False)
        self.assertGreaterEqual(ignored, round(14 * 0.3))  # some always come
        self.assertGreater(followed, ignored + 4)

    def test_every_mark_hit_brings_the_whole_guide_flock(self):
        ev = Evening(4)
        c = ev.courses[0]
        n, start = len(c.guide), len(ev.flock)
        c.state, c.hits = "lead", len(c.marks)
        c.finish(ev)
        self.assertEqual(ev.stats["guided"], n)
        self.assertEqual(len(ev.flock), start + n)

    def test_balloon_riders_join_when_the_flock_passes_the_basket(self):
        ev = Evening(4)
        b = ev.balloon
        riders = len(b.riders)
        move(ev, 5400, 300)
        run(ev, lambda ev: Ctrl(*ev.balloon.basket(), True, False), 12)
        self.assertEqual(ev.stats["balloon"], riders)
        self.assertEqual(b.riders, [])


if __name__ == "__main__":
    unittest.main()
