"""The journey and its save file. The file is read as untrusted input: whatever it holds, loading never raises
and what comes back holds the invariants."""

import json
import os
import random
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from duskward.evening import Evening  # noqa: E402
from duskward.journey import FATES, LIMIT, MOST, RESULTS, Journey  # noqa: E402
from duskward.places import PLACES  # noqa: E402


def fly(j, k, keep=(1, 2, 3, 4, 5, 6, 7, 8), commons=30, result="roost", how="falcon", seed=1):
    """Evening k as it would end: the flock holds `keep` of the eight and `commons` common birds. Returns the evening."""
    ev = Evening(seed + k, k, j.carry(k) if k else None)
    f = ev.flock
    for e in ev.eight_start:
        if e not in keep:
            f.remove(f.eight.index(e))
            ev.fates[e] = how
    while len(f) - sum(1 for e in f.eight if e) < commons:
        f.add(*f.centre(), 0, 0)
    while len(f) - sum(1 for e in f.eight if e) > commons:
        f.remove(next(i for i, e in enumerate(f.eight) if not e))
    ev.finish(result)
    return ev


class SaveCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.file = os.path.join(self.dir, "journey.json")
        self.old = os.environ.get("DUSKWARD_SAVE")
        os.environ["DUSKWARD_SAVE"] = self.file

    def tearDown(self):
        if self.old is None:
            os.environ.pop("DUSKWARD_SAVE", None)
        else:
            os.environ["DUSKWARD_SAVE"] = self.old
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, text):
        with open(self.file, "w", encoding="utf-8") as f:
            f.write(text)

    def two_nights(self):
        j = Journey.load()
        self.assertTrue(j.record(0, fly(j, 0, keep=(1, 2, 3, 4, 5, 6), commons=40)))
        self.assertTrue(j.record(1, fly(j, 1, keep=(1, 2, 3, 4, 5), commons=55, result="night")))
        return j


class FreshTest(SaveCase):
    def test_a_fresh_journey(self):
        j = Journey.load()
        self.assertEqual(j.next, 0)
        self.assertEqual(j.feathers(), 0)
        self.assertEqual(j.carry(0), (tuple(range(1, 9)), 0))
        self.assertFalse(j.over)
        self.assertEqual(j.great(0), 8)
        self.assertEqual(j.fates(), {})

    def test_keep_false_never_reads_or_writes(self):
        self.write("garbage")
        j = Journey.load(keep=False)
        self.assertEqual(j.next, 0)
        self.assertTrue(j.record(0, fly(j, 0)))
        self.assertEqual(open(self.file, encoding="utf-8").read(), "garbage")
        os.remove(self.file)
        j.record(0, fly(j, 0))
        self.assertFalse(os.path.exists(self.file))


class RecordTest(SaveCase):
    def test_a_lost_flock_records_nothing(self):
        j = Journey.load()
        ev = fly(j, 0, result="lost")
        self.assertFalse(j.record(0, ev))
        self.assertEqual(j.nights, [])
        self.assertFalse(os.path.exists(self.file))

    def test_an_empty_flock_records_nothing(self):
        j = Journey.load()
        ev = fly(j, 0)
        while len(ev.flock):
            ev.flock.remove(0)
        self.assertFalse(j.record(0, ev))
        self.assertEqual(j.nights, [])

    def test_an_evening_out_of_turn_records_nothing(self):
        j = Journey.load()
        self.assertFalse(j.record(1, fly(Journey(keep=False), 0)))
        self.assertEqual(j.nights, [])
        j.record(0, fly(j, 0))
        self.assertFalse(j.record(2, fly(Journey(keep=False), 0)))
        self.assertEqual(j.next, 1)

    def test_what_a_night_leaves_is_what_the_next_one_sets_out_with(self):
        j = self.two_nights()
        self.assertEqual(j.next, 2)
        self.assertEqual(j.carry(1), ((1, 2, 3, 4, 5, 6), 40))
        self.assertEqual(j.carry(2), ((1, 2, 3, 4, 5), 55))
        self.assertEqual(j.fates(), {7: (0, "falcon"), 8: (0, "falcon"), 6: (1, "falcon")})
        self.assertEqual(j.nights[1]["result"], "night")

    def test_flying_an_older_evening_again_only_adds_feathers(self):
        j = self.two_nights()
        before = json.loads(json.dumps(j.nights))
        # a better night 0: nobody lost, a great flock; it must not rewrite the night the next evening set out from
        better = fly(Journey(keep=False), 0, keep=tuple(range(1, 9)), commons=70)
        self.assertTrue(j.record(0, better))
        after = j.nights
        for key in ("result", "eight", "commons", "great", "fates"):
            self.assertEqual(after[0][key], before[0][key], key)
        self.assertEqual(after[1], before[1])
        self.assertEqual(j.next, 2)
        for was, now in zip(before[0]["feathers"], after[0]["feathers"]):
            self.assertTrue(now or not was)                    # a feather is never taken back
        self.assertGreaterEqual(sum(after[0]["feathers"]), sum(before[0]["feathers"]))
        self.assertTrue(after[0]["feathers"][0])               # it reached the roost

    def test_a_worse_replay_of_an_older_evening_keeps_every_feather(self):
        j = Journey.load()
        j.record(0, fly(j, 0, commons=80))
        j.record(1, fly(j, 1))
        won = list(j.nights[0]["feathers"])
        self.assertTrue(won[0])
        j.record(0, fly(Journey(keep=False), 0, keep=(1, 2), commons=1, result="night"))
        self.assertEqual(j.nights[0]["feathers"], [a or b for a, b in zip(won, [False, False, False])])
        self.assertEqual(j.nights[0]["eight"], list(range(1, 9)))

    def test_flying_the_latest_evening_again_rewrites_it(self):
        j = self.two_nights()
        self.assertTrue(j.record(1, fly(j, 1, keep=(1, 2), commons=10)))
        self.assertEqual(j.next, 2)
        self.assertEqual(j.nights[1]["eight"], [1, 2])
        self.assertEqual(j.nights[1]["commons"], 10)
        self.assertEqual(j.nights[1]["result"], "roost")
        self.assertEqual(j.nights[0]["eight"], [1, 2, 3, 4, 5, 6])    # nothing before it moved

    def test_replaying_the_first_night_of_one_rewrites_it(self):
        j = Journey.load()
        j.record(0, fly(j, 0, keep=(1, 2, 3), commons=5))
        j.record(0, fly(j, 0, keep=(1, 2, 3, 4), commons=7))
        self.assertEqual(j.next, 1)
        self.assertEqual(j.carry(1), ((1, 2, 3, 4), 7))

    def test_recording_an_evening_drops_what_came_after_it_only(self):
        j = self.two_nights()
        j.record(1, fly(j, 1))
        self.assertEqual(j.next, 2)
        self.assertEqual(j.nights[0]["eight"], [1, 2, 3, 4, 5, 6])

    def test_an_evening_past_the_last_records_nothing(self):
        j = Journey([{"result": "roost", "eight": [1], "commons": 9, "great": 9, "feathers": [True] * 3,
                      "fates": {}}] * len(PLACES))
        self.assertFalse(j.record(len(PLACES), fly(j, len(PLACES) - 1)))
        self.assertEqual(len(j.nights), len(PLACES))

    def test_the_journey_ends_after_the_last_place(self):
        j = Journey.load()
        for k in range(len(PLACES)):
            self.assertFalse(j.over)
            self.assertTrue(j.record(k, fly(j, k)), k)
        self.assertTrue(j.over)
        self.assertEqual(j.next, len(PLACES))
        self.assertEqual(Journey.load().nights, j.nights)

    def test_the_great_flock_follows_the_birds_that_joined(self):
        j = Journey.load()
        ev = fly(j, 0, commons=40)
        j.record(0, ev)
        n = j.nights[0]
        self.assertEqual(n["commons"], 40)
        self.assertGreaterEqual(n["great"], len(ev.flock))
        self.assertLessEqual(n["great"], MOST)

    def test_the_feathers_of_a_night_are_the_evenings(self):
        j = Journey.load()
        ev = fly(j, 0, keep=(1, 2, 3), commons=10)
        j.record(0, ev)
        self.assertEqual(j.nights[0]["feathers"], list(ev.feathers()))
        self.assertEqual(j.feathers(), sum(ev.feathers()))


class RoundTripTest(SaveCase):
    def test_two_nights_load_back_the_same(self):
        j = self.two_nights()
        back = Journey.load()
        self.assertEqual(back.nights, j.nights)
        self.assertEqual(back.next, 2)
        self.assertEqual(back.feathers(), j.feathers())
        self.assertEqual(back.fates(), j.fates())
        self.assertFalse(os.path.exists(self.file + ".tmp"))

    def test_the_save_is_small(self):
        j = Journey.load()
        for k in range(len(PLACES)):
            j.record(k, fly(j, k, keep=tuple(range(1, 9 - k % 8)) or (1,), commons=72))
        self.assertLess(os.path.getsize(self.file), LIMIT)


class HostileSaveTest(SaveCase):
    def night(self, **kw):
        n = {"result": "roost", "eight": [1, 2, 3, 4, 5, 6, 7, 8], "commons": 10, "great": 20,
             "feathers": [True, False, True], "fates": {}}
        n.update(kw)
        return n

    def save(self, *nights, v=1):
        return json.dumps({"v": v, "nights": list(nights)})

    def fresh(self, text, binary=False):
        if binary:
            with open(self.file, "wb") as f:
                f.write(text)
        else:
            self.write(text)
        j = Journey.load()
        self.assertEqual(j.nights, [], text if not binary else "bytes")
        self.assertEqual(j.next, 0)
        self.assertEqual(j.carry(0), (tuple(range(1, 9)), 0))

    def test_the_control_save_is_accepted(self):
        self.write(self.save(self.night()))
        self.assertEqual(Journey.load().next, 1)

    def test_not_json(self):
        for text in ("", "garbage", "{", "{'v': 1}", "\x00\x00", "nan", '{"v":1,"nights":[}',
                     "[" * 2000 + "]" * 2000, '{"v":1,"nights":' + "[" * 41 + "]" * 41 + "}"):   # nested past any save
            self.fresh(text)

    def test_the_wrong_shape(self):
        for text in ("[]", "[1,2]", "7", '"nights"', "null", "true", '{"v":1}', '{"nights":[]}',
                     '{"v":2,"nights":[]}', '{"v":"1","nights":[]}', '{"v":1,"nights":{}}',
                     '{"v":1,"nights":"x"}', '{"v":1,"nights":7}', '{"v":1,"nights":[1]}',
                     '{"v":1,"nights":[[]]}', '{"v":1,"nights":[null]}', '{"v":1,"nights":["roost"]}',
                     '{"v":{"v":1},"nights":{"nights":[]}}'):
            self.fresh(text)

    def test_a_file_longer_than_the_limit(self):
        n = self.night()
        pad = " " * (LIMIT + 1)
        self.fresh(self.save(n) + pad)
        self.fresh(self.save(n)[:-1] + "," + '"x":"' + "a" * LIMIT + '"}')

    def test_nine_nights(self):
        nights = [self.night() for _ in range(len(PLACES) + 1)]
        self.fresh(self.save(*nights))
        self.write(self.save(*nights[:len(PLACES)]))
        self.assertTrue(Journey.load().over)

    def test_ids_outside_one_to_eight(self):
        for bad in ([0, 1], [9], [-1], [1, 2, 3, 4, 5, 6, 7, 8, 9], [10**9], [1, 2, 3, 4, 5, 6, 7, 8, 0]):
            self.fresh(self.save(self.night(eight=bad, fates={str(e): "cold" for e in range(1, 9) if e not in bad})))

    def test_duplicate_ids(self):
        self.fresh(self.save(self.night(eight=[1, 1, 2, 3, 4, 5, 6, 7], fates={"8": "cold"})))
        self.fresh(self.save(self.night(eight=[1, 1, 1, 1, 1, 1, 1, 1], fates={})))

    def test_booleans_floats_and_strings_where_integers_belong(self):
        for bad in ([True, 2, 3, 4, 5, 6, 7, 8], [1.0, 2, 3, 4, 5, 6, 7, 8], ["1", 2, 3, 4, 5, 6, 7, 8],
                    [None, 2, 3, 4, 5, 6, 7, 8], [[1], 2, 3, 4, 5, 6, 7, 8]):
            self.fresh(self.save(self.night(eight=bad, fates={})))
        for field in ("commons", "great"):
            for bad in (True, False, 1.0, 1.5, "10", None, [10], {"a": 1}):
                self.fresh(self.save(self.night(**{field: bad})))

    def test_negative_and_huge_numbers(self):
        for field in ("commons", "great"):
            for bad in (-1, MOST + 1, 10**12, -(10**12), 10**40):
                self.fresh(self.save(self.night(**{field: bad})))
        self.write(self.save(self.night(commons=MOST, great=MOST)))
        self.assertEqual(Journey.load().nights[0]["great"], MOST)

    def test_an_unknown_fate_or_result(self):
        gone = dict(eight=[1, 2, 3, 4, 5, 6, 7])
        for how in ("dead", "", None, 3, ["falcon"], "Falcon"):
            self.fresh(self.save(self.night(fates={"8": how}, **gone)))
        for how in FATES:
            self.write(self.save(self.night(fates={"8": how}, **gone)))
            self.assertEqual(Journey.load().next, 1, how)
        for result in ("lost", "", None, 1, True, "ROOST", ["roost"]):
            self.fresh(self.save(self.night(result=result)))

    def test_fates_that_do_not_match_who_is_gone(self):
        gone = dict(eight=[1, 2, 3, 4, 5, 6, 7])
        for fates in ({}, {"7": "cold"}, {"8": "cold", "7": "cold"}, {"8": "cold", "9": "cold"}, [], "8", None, {"x": "cold"}):
            self.fresh(self.save(self.night(fates=fates, **gone)))
        self.fresh(self.save(self.night(fates={"1": "cold"})))

    def test_feathers_of_the_wrong_length_or_kind(self):
        for bad in ([], [True], [True, True], [True] * 4, [1, 0, 1], [1.0, 0.0, 1.0], ["a", "b", "c"], None, "tft",
                    {"a": True}, [True, False, None]):
            self.fresh(self.save(self.night(feathers=bad)))

    def test_one_of_the_eight_alive_after_being_lost(self):
        first = self.night(eight=[1, 2, 3, 4, 5, 6, 7], fates={"8": "falcon"})
        back = self.night(eight=[1, 2, 3, 4, 5, 6, 7, 8], fates={})
        self.fresh(self.save(first, back))
        wrong = self.night(eight=[1, 2, 3, 4, 5, 6, 7, 8], fates={"8": "cold"})
        self.fresh(self.save(first, wrong))
        self.write(self.save(first, self.night(eight=[1, 2, 3, 4, 5, 6], fates={"7": "cold"})))
        self.assertEqual(Journey.load().next, 2)

    def test_a_bad_later_night_gives_a_fresh_journey_not_half_of_it(self):
        self.fresh(self.save(self.night(), self.night(result="x")))

    def test_invalid_utf8(self):
        good = self.save(self.night()).encode("utf-8")
        self.fresh(b"\xff\xfe\x00{" + good, binary=True)
        self.fresh(good[:20] + b"\xc3\x28" + good[20:], binary=True)
        self.fresh(b"\x80" * 100, binary=True)

    def test_a_missing_file_and_a_directory_in_its_place(self):
        self.assertEqual(Journey.load().nights, [])
        os.mkdir(self.file)
        self.assertEqual(Journey.load().nights, [])

    def test_a_tmp_file_left_by_a_crash_is_ignored(self):
        with open(self.file + ".tmp", "w", encoding="utf-8") as f:
            f.write(self.save(self.night()))
        self.assertEqual(Journey.load().nights, [])


JUNK = (None, -1, 10**12, 1.5, "x", [], {}, True, "y" * 5000)


def deep(n=60):
    v = 1
    for _ in range(n):
        v = [v]
    return v


class FuzzTest(SaveCase):
    def places(self, node, out):
        """Every (container, key) in the decoded JSON."""
        for k in (range(len(node)) if isinstance(node, list) else node):
            out.append((node, k))
            if isinstance(node[k], (list, dict)):
                self.places(node[k], out)
        return out

    def check(self, j, context):
        self.assertLessEqual(len(j.nights), len(PLACES), context)
        alive = set(range(1, 9))
        for n in j.nights:
            eight = n["eight"]
            self.assertIsInstance(eight, list, context)
            self.assertTrue(all(type(e) is int and 1 <= e <= 8 for e in eight), context)
            self.assertEqual(len(set(eight)), len(eight), context)
            self.assertTrue(set(eight) <= alive, context)
            for key in ("commons", "great"):
                self.assertIs(type(n[key]), int, context)
                self.assertTrue(0 <= n[key] <= MOST, context)
            self.assertEqual(len(n["feathers"]), 3, context)
            self.assertTrue(all(type(f) is bool for f in n["feathers"]), context)
            self.assertIn(n["result"], RESULTS, context)
            self.assertTrue(all(v in FATES for v in n["fates"].values()), context)
            self.assertEqual(set(n["fates"]), {str(e) for e in alive - set(eight)}, context)
            alive = set(eight)
        self.assertEqual(j.next, len(j.nights))

    def test_four_hundred_mutations_of_a_valid_save(self):
        self.two_nights()
        base = open(self.file, encoding="utf-8").read()
        rng = random.Random(7)
        kept = 0
        for i in range(400):
            data = json.loads(base)
            spots = self.places(data, [])
            box, key = rng.choice(spots)
            junk = deep() if rng.random() < 0.1 else rng.choice(JUNK)
            box[key] = junk
            if rng.random() < 0.3:                                   # sometimes two at once
                box2, key2 = rng.choice(self.places(data, []))
                box2[key2] = rng.choice(JUNK)
            text = json.dumps(data)
            self.write(text)
            j = Journey.load()
            self.check(j, f"mutation {i}: {text[:300]}")
            kept += bool(j.nights)
        self.assertGreater(kept, 0)                                  # some mutations are harmless: the fuzz is not all-reject

    def test_a_mutated_save_loaded_and_recorded_again_stays_valid(self):
        self.two_nights()
        base = open(self.file, encoding="utf-8").read()
        rng = random.Random(11)
        for i in range(60):
            data = json.loads(base)
            box, key = rng.choice(self.places(data, []))
            box[key] = rng.choice(JUNK)
            self.write(json.dumps(data))
            j = Journey.load()
            j.record(j.next if j.next < len(PLACES) else 0, fly(j, min(j.next, len(PLACES) - 1)))
            self.check(Journey.load(), f"mutation {i}")


if __name__ == "__main__":
    unittest.main()
