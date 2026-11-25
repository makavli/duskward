"""The journey south: eight evenings, what each one left of the flock and of the eight, and the save that keeps it.

A save is a small JSON text: a file on a desktop, the browser's local storage on the web. It is read as untrusted
input: anything out of shape is a fresh journey, never a crash.
"""

import json
import os
import sys

from .places import PLACES

WEB = sys.platform == "emscripten"
KEY = "duskward-journey"
RESULTS = ("roost", "night")         # a lost flock records nothing: that evening is flown again
FATES = ("falcon", "behind", "cold")
LIMIT = 4096                         # a whole journey is about 1 KB
MOST = 100000                        # no flock is larger
OPENS = 40                           # a whole journey opens 34 brackets: more is no save, and none nests deep


def whole(v, most):
    return type(v) is int and 0 <= v <= most


def clean(data):
    """The nights in a decoded save, each checked against the one before it, or None."""
    nights = data.get("nights") if isinstance(data, dict) and data.get("v") == 1 else None
    if not isinstance(nights, list) or len(nights) > len(PLACES):
        return None
    out, alive = [], set(range(1, 9))
    for n in nights:
        if not isinstance(n, dict) or n.get("result") not in RESULTS:
            return None
        eight, fates, feathers = n.get("eight"), n.get("fates"), n.get("feathers")
        if not (isinstance(eight, list) and all(type(e) is int for e in eight) and len(set(eight)) == len(eight)
                and set(eight) <= alive):
            return None
        gone = {str(e) for e in alive - set(eight)}
        if not (isinstance(fates, dict) and set(fates) == gone and all(f in FATES for f in fates.values())):
            return None
        if not (isinstance(feathers, list) and len(feathers) == 3 and all(type(f) is bool for f in feathers)):
            return None
        if not (whole(n.get("commons"), MOST) and whole(n.get("great"), MOST)):
            return None
        alive = set(eight)
        out.append({"result": n["result"], "eight": sorted(eight), "commons": n["commons"], "great": n["great"],
                    "feathers": feathers, "fates": dict(fates)})
    return out


def path():
    """The save file. DUSKWARD_SAVE names another."""
    if os.environ.get("DUSKWARD_SAVE"):
        return os.environ["DUSKWARD_SAVE"]
    import pygame
    return os.path.join(pygame.system.get_pref_path("duskward", "Duskward"), "journey.json")


class Journey:
    def __init__(self, nights=(), keep=True):
        self.nights = list(nights)   # one per evening flown: result, eight, commons, great, feathers, fates
        self.keep = keep             # False: never written (the tests and the bot leave the player's save alone)

    @classmethod
    def load(cls, keep=True):
        if not keep:
            return cls(keep=False)
        try:
            if WEB:
                import platform
                text = platform.window.localStorage.getItem(KEY)
            else:
                with open(path(), encoding="utf-8") as f:
                    text = f.read(LIMIT + 1)
            text = str(text or "")
            if text and len(text) <= LIMIT and text.count("[") + text.count("{") <= OPENS:
                return cls(clean(json.loads(text)) or ())
        except Exception:            # no save, a broken one, a browser that refuses storage: a fresh journey
            pass
        return cls()

    def save(self):
        if not self.keep:
            return
        text = json.dumps({"v": 1, "nights": self.nights}, separators=(",", ":"))
        try:
            if WEB:
                import platform
                platform.window.localStorage.setItem(KEY, text)
            else:
                tmp = path() + ".tmp"            # written whole, then swapped in: a crash never leaves half a save
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(text)
                os.replace(tmp, path())
        except Exception:            # a full disk or a private window: play on, unsaved
            pass

    @property
    def next(self):
        """The evening to fly next; len(PLACES) when the journey is over."""
        return len(self.nights)

    @property
    def over(self):
        return len(self.nights) == len(PLACES)

    def carry(self, k):
        """Who sets out on evening k: (which of the eight, the common starlings beside them)."""
        if k == 0:
            return tuple(range(1, 9)), 0
        return tuple(self.nights[k - 1]["eight"]), self.nights[k - 1]["commons"]

    def great(self, k):
        """The great flock before evening k: everyone who has come south with the eight, wherever they roost."""
        return self.nights[k - 1]["great"] if k else 8

    def record(self, k, ev):
        """Evening k is over. The last evening flown may be flown again, and its night is written anew; an older one
        only adds to its feathers, since the evenings after it set out from the night it left. A lost flock, or an
        evening flown out of turn, records nothing."""
        home = len(ev.flock)
        if ev.result not in RESULTS or not home or k > len(self.nights) or k >= len(PLACES):
            return False
        won = self.nights[k]["feathers"] if k < len(self.nights) else [False] * 3
        feathers = [bool(a or b) for a, b in zip(won, ev.feathers())]
        if k < len(self.nights) - 1:
            self.nights[k]["feathers"] = feathers
        else:
            eight = sorted(e for e in ev.flock.eight if e)
            self.nights[k:] = [{
                "result": ev.result, "eight": eight, "commons": home - len(eight),
                "great": min(MOST, max(home, self.great(k) + home - ev.stats["start"])),
                "feathers": feathers, "fates": {str(e): how for e, how in sorted(ev.fates.items())}}]
        self.save()
        return True

    def feathers(self):
        return sum(sum(n["feathers"]) for n in self.nights)

    def fates(self):
        """{which of the eight: (the evening it was lost, how)} over the whole journey."""
        return {int(e): (k, how) for k, n in enumerate(self.nights) for e, how in n["fates"].items()}
