import math
import unittest

from duskward.flock import Flock


def disc(n=120, r=260.0, seed=3):
    f = Flock(seed)
    for k in range(n):
        a, d = k * 2.399, r * math.sqrt((k + 0.5) / n)
        f.add(1000 + d * math.cos(a), 300 + d * math.sin(a), 120, 0)
    return f


def ground(x):
    return 680.0


class FlockTest(unittest.TestCase):
    def fly(self, f, seconds, gather):
        for _ in range(int(seconds * 60)):
            cx, cy = f.centre()
            f.step(1 / 60, cx + 200, 300, gather, ground)

    def test_gathering_tightens_the_flock(self):
        loose, tight = disc(), disc()
        self.fly(loose, 3, False)
        self.fly(tight, 3, True)
        self.assertLess(tight.spread(), loose.spread() * 0.8)

    def test_birds_stay_above_the_ground(self):
        f = disc()
        for _ in range(240):
            f.step(1 / 60, f.centre()[0], 900, True, ground)          # steered into the earth
        self.assertTrue(all(y < ground(0) for y in f.y))

    def test_a_ripple_pushes_birds_outward_and_lights_them(self):
        f = disc()
        cx, cy = f.centre()
        before = sum(math.hypot(x - cx, y - cy) for x, y in zip(f.x, f.y))
        f.ripple(cx, cy)
        for _ in range(20):
            f.step(1 / 60, cx, cy, False, ground)
        after = sum(math.hypot(x - cx, y - cy) for x, y in zip(f.x, f.y))
        self.assertGreater(after, before)
        self.assertTrue(any(v > 0 for v in f.flash))

    def test_remove_keeps_every_field_aligned(self):
        f = Flock()
        for k in range(5):
            f.add(k, 10 * k, eight=k == 3)
        gone = f.remove(1)
        self.assertEqual(gone[:2], (1, 10))
        self.assertEqual(len(f), 4)
        for name in Flock.FIELDS:
            self.assertEqual(len(getattr(f, name)), 4, name)
        i = f.x.index(3)
        self.assertTrue(f.eight[i])
        self.assertEqual(f.y[i], 30)


if __name__ == "__main__":
    unittest.main()
