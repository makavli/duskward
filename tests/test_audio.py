import os
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from duskward import audio  # noqa: E402

CUES = ("liftoff", "call", "join", "feed", "gust", "ripple", "cry", "stoop", "miss", "catch", "scatter", "thunder",
        "chime", "watch", "merge", "roost", "night", "lost", "heron", "mark", "course", "balloon", "tick", "bang",
        "burner", "snag", "rocket", "burst", "thermal", "blade", "foghorn", "buoy", "gull", "bridge", "card", "finale",
        "home", "no-such-sound")
SCENES = ("title", "journey", "play", "play", "summary", "ending")


def mood(place, k, f, frames):
    """One frame's mood in scene k: every key the game may send, swept over its range."""
    u = f / frames
    return {"scene": SCENES[k], "light": u, "flock": f % 400, "gather": (f % 90) / 90, "speed": 0.5,
            "danger": float(f % 200 > 150), "squall": float(k == 2), "paused": f % 300 > 270,
            "result": "roost" if SCENES[k] == "summary" else None, "course": float(k == 3 and f % 100 > 60),
            "progress": u, "place": place, "fog": u if k == 2 else 0.0, "sea": 1 - u, "wind": u,
            "festive": float(k == 3), "shelter": float(f % 120 > 80), "finale": float(k == 3 and u > 0.5)}


class AudioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        audio.pre_init()
        pygame.init()
        audio.init()

    def test_every_cue_and_mood_plays_without_error_and_cheaply(self):
        cost = []
        for place in range(8):
            for k in range(len(SCENES)):
                for f in range(300):
                    if f % 12 == 0:
                        audio.cue(CUES[(f // 12 + 7 * k + place) % len(CUES)], f // 12)
                    if k == 4 and f in (150, 200):
                        audio.toggle_mute()
                    m = mood(place, k, f, 300)
                    t = time.perf_counter()
                    audio.update(1 / 60, m)
                    cost.append(time.perf_counter() - t)
        self.assertLess(sorted(cost)[len(cost) * 99 // 100], 0.005)       # not the worst: a busy machine stalls one call

    def test_every_sound_audio_asks_for_was_made_and_fits_the_browser(self):
        files = [f for f in os.listdir(audio.SOUNDS) if f.endswith(".wav")]
        have = {f[:-4] for f in files}
        want = set(audio.BEDS)
        for chords, _ in audio.PALETTES.values():
            for c in chords:
                want |= {"pad_" + c, "choir_" + c, "bass_" + audio.root(c)}
        banks = {"pluck", "bell", "mari"} | {v for p in audio.PLACES for v in p[1:4]}
        want |= {f"{b}_{m}" for b in banks for m in audio.NOTES}
        want |= set(audio.SIMPLE) | {f"{k}{j}" for k, v in audio.VARIANTS.items() for j in range(1, v + 1)}
        want |= {snd for card in audio.CARDS for _, snd, _ in card}
        asked, real = set(), audio._play
        audio._play = lambda name, vol: (asked.add(name), real(name, vol))     # every name the score and cues play
        try:
            if audio.state["muted"]:
                audio.toggle_mute()
            for place in range(8):
                for name in CUES[:-1]:
                    for n in range(8):
                        audio.cue(name, n)
                        odd = n % 2                 # odd steps: the danger pulse and the guide's shaker
                        audio.update(0.35, mood(place, 2 + odd, 37 * n, 300) | {"danger": odd, "course": 0.5 * odd})
        finally:
            audio._play = real
        self.assertTrue(asked)
        self.assertEqual(sorted((want | asked) - have), [])
        self.assertLessEqual(sum(os.path.getsize(os.path.join(audio.SOUNDS, f)) for f in files), 7.5e6)


if __name__ == "__main__":
    unittest.main()
