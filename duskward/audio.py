"""Sound: beds that follow the flock and the evening, a generative score that grows with the flock, and short cues.

Every file comes from tools/make_sounds.py. The mixer's settings go in before pygame.init() opens it, and it is never
closed and reopened (the browser's mixer breaks on that). Sounds load from paths, the one way the browser's pygame
takes them. Without a sound device, or without a file, the game plays on, silent where it must.

Channels 0-6 hold the beds, looping from the start with their volume eased every frame. Channels 7-12 hold three
chord loops (pad, bass, choir), two channels each so one chord crossfades into the next. Notes and cues take the free
channels and never steal a busy one.

The score ticks in eighths (64 beats a minute on the Saltmarsh): a chord every two bars, from a palette that darkens
with the light and lifts near the roost. The lead plays two-bar questions and answers; the flock's size adds layers (a
bass from about 20 birds, a bell counter-melody from 60, a choir from 150). The eight have a motif: the title opens
with it, liftoff plays it, the lead weaves it in every half minute or so, the roost resolves it, and night breaks it.
Each of the eight evenings gives the score its flavour (PLACES, and the palettes and rhythms named after the place's
number); fog, festivity, shelter and the finale bend it on top.
"""

import os
import random
import sys
import time

import pygame

SOUNDS = os.path.join(os.path.dirname(__file__), "sounds")
BEDS = ("wing", "wing_tight", "chatter", "wind", "night", "rain", "surf")
LOOPS = (("pad", 0.3), ("bass", 0.3), ("choir", 0.2))     # chord loops after the beds, and their full volume
CHANNELS = 40
RESERVED = len(BEDS) + 2 * len(LOOPS)                    # beds, then two channels a loop; notes and cues share the rest
NOTES = (62, 64, 66, 67, 69, 71, 72, 74, 76, 78, 79, 81, 83, 84, 86)    # the note banks, as make_sounds writes them
EIGHTH = 60 / 64 / 2
PALETTES = {                    # chords (two bars each) and the melody's pitch classes (C=0, D=2 ... B=11)
    "title": (("Dadd9", "Gmaj9", "Bm7", "Asus2"), (2, 4, 6, 9, 11)),
    "gold": (("Dadd9", "Bm7", "Gmaj9", "Asus2"), (2, 4, 6, 9, 11)),
    "dusk": (("Dsus2", "Gmaj9", "Em7", "Cmaj7"), (2, 4, 7, 9, 11)),
    "night": (("Dm9", "Bbmaj9", "Fmaj7", "Am7"), (2, 4, 7, 9, 0)),
    "lift": (("Bbmaj9", "Cmaj7", "Dsus2", "Dadd9"), (2, 4, 7, 9, 0)),     # near the roost: bVI, bVII, I
    "roost": (("Dadd9", "Gmaj9"), (2, 4, 6, 9, 11)),
    "cold": (("Dm9", "Bbmaj9"), (2, 4, 7, 9, 0)),
    # the other evenings: gold1 is the Hop Gardens' gold, and so on; a place without one keeps the Saltmarsh's
    "gold1": (("Gmaj9", "Dadd9", "Em7", "Cadd9"), (2, 4, 7, 9, 11)),      # Hop Gardens: warm, G at the heart
    "dusk1": (("Em7", "Cadd9", "Gmaj9", "Dsus2"), (2, 4, 7, 9, 11)),
    "night1": (("Am7", "Fmaj7", "Cmaj7", "Em7"), (2, 4, 7, 9, 0)),
    "lift1": (("Cadd9", "Dsus2", "Gmaj9", "Dadd9"), (2, 4, 7, 9, 11)),
    "gold2": (("Dadd9", "Asus2", "Bm7", "Gmaj9"), (2, 4, 6, 9, 11)),       # Market Town: bright, I V vi IV
    "dusk2": (("Gmaj9", "Dadd9", "Asus2", "Bm7"), (2, 4, 6, 9, 11)),
    "night2": (("Em7", "Cmaj7", "Gmaj9", "Dsus2"), (2, 4, 7, 9, 11)),
    "lift2": (("Gmaj9", "Asus2", "Dadd9", "Dadd9"), (2, 4, 6, 9, 11)),
    "gold3": (("Dsus2", "Asus2", "Gsus2", "Esus4"), (2, 4, 7, 9, 11)),     # The Wind Farm: open fifths, suspended
    "dusk3": (("Em7", "Dsus2", "Cmaj7", "Asus2"), (2, 4, 7, 9, 11)),
    "night3": (("Am7", "Gsus2", "Dm9", "Cmaj7"), (2, 4, 7, 9, 0)),
    "lift3": (("Gsus2", "Asus2", "Dsus2", "Dadd9"), (2, 4, 7, 9, 11)),
    "gold4": (("Dsus2", "Em7", "Gsus2", "Asus2"), (2, 4, 7, 9, 11)),       # Estuary Fog: grey, slow to move
    "dusk4": (("Em7", "Cmaj7", "Am7", "Dsus2"), (2, 4, 7, 9, 11)),
    "night4": (("Am9", "Dm9", "Fmaj7", "Am7"), (2, 4, 7, 9, 0)),
    "lift4": (("Cmaj7", "Gsus2", "Dsus2", "Dadd9"), (2, 4, 7, 9, 0)),
    "gold5": (("Gmaj9", "Em9", "Cmaj9", "Dadd9"), (2, 4, 6, 9, 11)),       # City of Bridges: maj7 and m9, cool
    "dusk5": (("Cmaj9", "Am9", "Em9", "Gmaj9"), (2, 4, 7, 9, 11)),
    "night5": (("Am9", "Fmaj7", "Dm9", "Cmaj9"), (2, 4, 7, 9, 0)),
    "lift5": (("Bbmaj9", "Cmaj9", "Dsus2", "Dadd9"), (2, 4, 7, 9, 0)),
    "gold6": (("Em7", "Cmaj7", "Am7", "Dsus2"), (2, 4, 7, 9, 11)),         # Chalk Cliffs: minor, wide, tense
    "dusk6": (("Am7", "Fmaj7", "Dm9", "Esus4"), (2, 4, 7, 9, 0)),
    "night6": (("Dm9", "Bbmaj9", "Am7", "Esus4"), (2, 4, 7, 9, 0)),
    "lift6": (("Bbmaj9", "Cmaj7", "Dsus2", "Dsus2"), (2, 4, 7, 9, 0)),
    "gold7": (("Dmaj7", "Bm7", "Gmaj9", "Asus2"), (2, 4, 6, 9, 11)),       # The Long Reeds: midwinter, glassy
    "dusk7": (("Gmaj9", "Dmaj7", "Em7", "Asus2"), (2, 4, 6, 9, 11)),
    "night7": (("Bm7", "Em7", "Gmaj9", "Asus2"), (2, 4, 6, 9, 11)),
    "lift7": (("Gmaj9", "Asus2", "Bm7", "Dmaj7"), (2, 4, 6, 9, 11)),
    "finale": (("Gmaj9", "Asus2", "Bm7", "Gmaj9", "Cmaj7", "Dadd9"), (2, 4, 6, 9, 11)),   # every flock's dance
}
MOTIF = ((0, 3), (2, 5), (3, 6), (4, 7), (6, 6), (8, 5))   # the eight's phrase, eighth -> degree: A D E F# E D in gold
MINOR = (64, 69, 71, 72, 71)                              # its shape in A minor, broken off, for the cold endings
TITLE = {10: 3, 12: 2,                                    # the title's theme after the motif: eighth -> degree, 8 bars
         16: 4, 18: 5, 19: 6, 22: 7, 24: 6, 27: 5, 28: 4,
         32: 5, 34: 7, 36: 8, 38: 7, 40: 6, 42: 5, 45: 4,
         48: 6, 51: 4, 52: 3, 56: 1, 58: 3, 60: 4}
RHYTHMS = {                     # two-bar shapes in eighths: golden hour lilts, dusk breathes, night leaves room
    "gold": ((0, 2, 3, 6, 8, 9, 12), (0, 3, 4, 6, 9, 10), (0, 1, 3, 6, 8, 11), (0, 3, 6, 7, 8)),
    "dusk": ((0, 4, 6, 10), (0, 3, 8, 11), (0, 6, 8), (2, 4, 8, 12)),
    "night": ((0, 8), (0, 6), (4, 10), (0,)),
    "gold1": ((0, 2, 3, 5, 6, 9, 12), (0, 3, 5, 6, 8, 11, 12), (0, 2, 3, 6, 9, 11, 12, 14), (0, 3, 6, 8, 9, 12)),
    "dusk1": ((0, 3, 6, 9, 12), (0, 2, 3, 6, 12), (0, 3, 5, 6, 12), (2, 3, 6, 9)),     # in threes: a dance
    "night1": ((0, 3, 6), (0, 6, 9), (3, 6, 12), (0, 9)),
    "gold2": ((0, 1, 2, 4, 6, 7, 8, 10, 12), (0, 2, 3, 4, 6, 8, 10, 11, 12), (0, 1, 2, 3, 4, 6, 8, 12),
              (0, 2, 4, 5, 6, 8, 9, 10, 12, 14)),                                        # quick, busy figures
    "dusk2": ((0, 2, 4, 6, 8, 12), (0, 1, 2, 4, 8, 10), (0, 2, 3, 4, 8, 12), (0, 4, 5, 6, 8, 12)),
    "night2": ((0, 2, 4, 8), (0, 1, 2, 8, 12), (0, 4, 6, 8), (0, 2, 8, 10)),
    "gold3": ((0, 2, 4, 6, 8, 10, 12), (0, 2, 3, 4, 6, 8, 10, 11), (0, 1, 2, 4, 6, 8, 12), (0, 2, 4, 6, 7, 8, 12, 14)),
    "dusk3": ((0, 2, 4, 6, 8, 12), (0, 2, 4, 8, 10), (0, 3, 4, 6, 8), (0, 2, 6, 8, 10, 12)),   # driving eighths
    "night3": ((0, 2, 4, 8), (0, 4, 6), (0, 2, 8, 10), (4, 6, 8)),
    "gold4": ((0, 6), (0, 4, 10), (0,), (2, 8)),                                         # a note, then fog
    "dusk4": ((0, 8), (0,), (4,), (0, 10)),
    "night4": ((0,), (8,), (0,), (4,)),
    "gold5": ((0, 2, 4, 6, 8, 12), (0, 4, 6, 8, 12), (0, 2, 4, 8, 10, 12), (0, 4, 8, 10, 12)),  # steady on the beat
    "dusk5": ((0, 4, 8, 12), (0, 4, 6, 8), (0, 2, 4, 8), (0, 4, 8)),
    "night5": ((0, 4, 8), (0, 8, 12), (0, 4), (4, 8, 12)),
    "gold6": ((0, 3, 4, 8, 11), (0, 4, 7, 8, 12), (0, 1, 4, 8), (0, 3, 8, 12)),          # long notes, sudden pairs
    "dusk6": ((0, 4, 8), (0, 3, 8, 11), (0, 8, 12), (0, 1, 8)),
    "night6": ((0, 8), (0,), (0, 3), (8,)),
    "gold7": ((0, 4, 6, 8, 12), (0, 2, 4, 8), (0, 4, 8, 10, 12), (0, 6, 8)),             # slow and even, a hymn
    "dusk7": ((0, 4, 8, 12), (0, 6, 8), (0, 8), (0, 4, 8)),
    "night7": ((0, 8), (0, 4, 8), (0,), (4, 12)),
}
PLACES = (      # each evening: beats a minute, lead, the lead's voice at night, counter-melody, the lead's register (in
                # degrees), how often an answer rests, the danger pulse's weight, an ostinato (instrument, notes,
                # every n eighths, volume)
    (64, "pluck", "bell", "bell", 0, 0.25, 1.0, None),                          # 0 The Saltmarsh, as in 0.3.0
    (70, "pluck", "bell", "mari", 0, 0.2, 1.0, None),                           # 1 Hop Gardens: a lilting dance
    (84, "mari", "bell", "pluck", 1, 0.1, 1.0, None),                           # 2 Market Town: the marimba leads
    (76, "pluck", "bell", "bell", 0, 0.25, 1.0, ("pluck", (62, 69), 2, 0.07)),  # 3 The Wind Farm: fifths drive it
    (54, "bell", "bell", "pluck", -1, 0.5, 1.0, None),                          # 4 Estuary Fog: bells and room
    (68, "pluck", "bell", "bell", -1, 0.25, 1.0, None),                         # 5 City of Bridges: steady, cool
    (62, "pluck", "bell", "bell", 2, 0.3, 1.4, None),                           # 6 Chalk Cliffs: high, the pulse first
    (58, "cel", "cel", "bell", 1, 0.25, 1.0, None),                             # 7 The Long Reeds: the celesta
)
CARDS = (       # each evening's title card: (seconds in, sound, volume); the Saltmarsh's stays soft, liftoff follows
    ((0.0, "bell_74", 0.11), (0.07, "bell_81", 0.08)),
    ((0.0, "pluck_67", 0.26), (0.36, "pluck_71", 0.2), (0.54, "pluck_74", 0.24), (0.9, "mari_79", 0.2)),
    ((0.0, "mari_74", 0.3), (0.08, "mari_78", 0.3), (0.16, "mari_81", 0.32), (0.24, "mari_86", 0.36),
     (0.24, "bell_86", 0.12)),
    ((0.0, "pluck_62", 0.2), (0.0, "pluck_69", 0.2), (0.32, "pluck_76", 0.24), (0.64, "bell_81", 0.16)),
    ((0.0, "bell_69", 0.2), (1.4, "bell_76", 0.14)),
    ((0.0, "pluck_64", 0.2), (0.07, "pluck_67", 0.18), (0.14, "pluck_71", 0.18), (0.21, "bell_78", 0.14)),
    ((0.0, "pulse", 0.3), (0.0, "bell_64", 0.18), (0.0, "pluck_81", 0.2), (0.75, "pulse", 0.2),
     (0.8, "bell_72", 0.16)),
    ((0.0, "bell_62", 0.1), (0.0, "cel_74", 0.22), (0.4, "cel_81", 0.2), (0.8, "cel_78", 0.2), (1.4, "cel_86", 0.2)),
)
SIMPLE = {"liftoff": 0.55, "gust": 0.45, "ripple": 0.5, "cry": 0.5, "stoop": 0.45, "scatter": 0.35, "thunder": 0.7,
          "heron": 0.4, "tick": 0.2, "bang": 0.85, "burner": 0.22, "rocket": 0.3, "thermal": 0.3, "foghorn": 0.3,
          "bridge": 0.4}
VARIANTS = {"call": 3, "burst": 3, "blade": 3, "buoy": 2, "gull": 2}    # call1..call3 and so on
CAPS = {"thunder": (2, 0.3), "cry": (2, 0.3), "stoop": (2, 0.3), "heron": (2, 0.3), "bang": (2, 0.3),
        "snag": (2, 0.3), "blade": (1, 0.6), "burst": (2, 0.5)}     # at most so many in so many seconds; else 3 in 0.3


def pitches(palette):
    return [m for m in NOTES if m % 12 in PALETTES[palette][1]]


def root(chord):
    return chord[:2] if chord[1] == "b" else chord[0]


def _ramp(x, a, b):
    return min(1.0, max(0.0, (x - a) / (b - a)))


sounds = {}
state = {"muted": False, "last": None}
scale = pitches("gold")         # the current palette's notes, D4..D6; changed in place
_rng = random.Random(5)
_beds = []                      # [name, channel, level]
_loops = []                     # pad, bass, choir
_free = []                      # the channels notes and cues may take
_seq = {"t": 0.0, "next": 0.0, "tick": 0, "palette": None, "scene": None, "master": 1.0, "deg": 5, "queue": [],
        "recent": {}, "check": 0.0, "lay": [0.0, 0.0, 0.0, 0.0], "ask": False, "rhythm": (0,), "lead": {},
        "counter": {}, "hold": 0.0, "motif_at": 0.0, "eighth": EIGHTH, "place": 0, "fog": 0.0, "finale": 0.0,
        "full": 0.0}


class _Loop:
    """One chord loop (pad, bass or choir) on two channels: a new chord fades in on one as the old fades out."""

    def __init__(self, kind, full, first):
        self.kind, self.full = kind, full
        self.ch = [pygame.mixer.Channel(first), pygame.mixer.Channel(first + 1)]
        self.lv, self.side, self.name = [0.0, 0.0], 0, None

    def switch(self, name):
        if name == self.name:
            return
        self.side ^= 1
        self.name = name
        ch = self.ch[self.side]
        ch.stop()
        self.lv[self.side] = 0.0
        snd = sounds.get(name)
        if snd:
            ch.set_volume(0)
            ch.play(snd, loops=-1)

    def ease(self, dt, gain):
        on, off = self.side, self.side ^ 1
        self.lv[on] += (1.0 - self.lv[on]) * min(1.0, dt / 1.2)
        self.lv[off] -= self.lv[off] * min(1.0, dt / 1.4)
        if self.lv[off] < 0.01 and self.ch[off].get_busy():
            self.ch[off].stop()
        for k in (0, 1):
            self.ch[k].set_volume(self.lv[k] * gain * self.full)


def pre_init():
    # a browser fills the sound between frames, so its buffer must outlast a slow frame (4096 = 93 ms) or it ticks
    pygame.mixer.pre_init(44100, -16, 2, 4096 if sys.platform == "emscripten" else 512, allowedchanges=0)


def init():
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.set_num_channels(CHANNELS)
        pygame.mixer.set_reserved(RESERVED)
        for f in sorted(os.listdir(SOUNDS)):
            if f.endswith(".wav"):
                sounds[f[:-4]] = pygame.mixer.Sound(os.path.join(SOUNDS, f))
        for k, name in enumerate(BEDS):
            ch = pygame.mixer.Channel(k)
            ch.set_volume(0)
            if name in sounds:
                ch.play(sounds[name], loops=-1)
                _beds.append([name, ch, 0.0])
        _loops[:] = [_Loop(kind, full, len(BEDS) + 2 * k) for k, (kind, full) in enumerate(LOOPS)]
        _free[:] = [pygame.mixer.Channel(i) for i in range(RESERVED, CHANNELS)]
    except (pygame.error, OSError) as err:          # no audio device: the game plays silent
        print("audio:", err)
        sounds.clear()
        _beds.clear()


# ---- playing
def _play(name, vol):
    snd = sounds.get(name)
    v = vol * _seq["master"]
    if snd is None or state["muted"] or v < 0.004:
        return
    for ch in _free:                                # not find_channel(): it hands out the reserved loop channels too
        if not ch.get_busy():
            ch.set_volume(min(1.0, v))
            ch.play(snd)
            return


def _name(inst, degree, notes=None):
    notes = notes or scale
    return f"{inst}_{notes[max(0, min(len(notes) - 1, degree))]}"


def _note(inst, degree, vol, notes=None):
    _play(_name(inst, degree, notes), vol)


def _later(delay, inst, degree, vol, notes=None):
    """Queues a note; update() plays it when its time comes."""
    _seq["queue"].append((_seq["t"] + delay, _name(inst, degree, notes), vol))


def _chord(chord):
    for lp in _loops:
        lp.switch(f"{lp.kind}_{root(chord) if lp.kind == 'bass' else chord}")


def _force(palette, chord=0):
    """Starts a palette's chord now; the next change comes two bars later."""
    s = _seq
    s["palette"] = palette
    scale[:] = pitches(palette)
    _chord(PALETTES[palette][0][chord])
    s["tick"], s["next"] = 1, s["t"] + s["eighth"]


def _palette(scene, light, result, progress):
    if scene == "title":
        return "title"
    if result == "roost" or scene == "ending":
        return "roost"
    if result in ("night", "lost"):
        return "cold"
    p = _seq["place"]
    if scene == "journey" and not p:
        return "title"
    if scene == "play" and _seq["finale"] > 0.5:
        return "finale"
    if scene == "play" and progress >= 0.85:
        name = "lift"
    else:
        name = "gold" if scene == "journey" or light < 0.4 else ("dusk" if light < 0.72 else "night")
    return f"{name}{p}" if f"{name}{p}" in PALETTES else name


def _capped(name, limit, window=0.3):
    t = _seq["t"]
    recent = [x for x in _seq["recent"].get(name, ()) if t - x < window]
    full = len(recent) >= limit
    if not full:
        recent.append(t)
    _seq["recent"][name] = recent
    return full


def _motif(kind, vol=0.3):
    """The eight's phrase. open: in the current scale on the place's lead, ending on E (a question); whole: resolved
    on D, crowned an octave up; fast: liftoff's quick version; broken: in A minor, slow, cut off; lost: three notes,
    then a low D."""
    s = _seq
    eighth = s["eighth"]
    if kind in ("broken", "lost"):
        steps = tuple(zip((0, 3, 5, 6, 10), MINOR))[:3 if kind == "lost" else 5]
        for k, (e, m) in enumerate(steps):
            _later(e * eighth * 1.3, "bell", 0, vol * (1 - 0.12 * k), [m])
        if kind == "lost":
            _later(10 * eighth * 1.3, "pluck", 0, vol * 0.8, [62])
        hold = 14 * eighth
    else:
        notes = scale if kind == "open" else pitches("gold")
        steps = MOTIF[:5] if kind == "open" else MOTIF
        speed = {"fast": 0.6, "whole": 1.15}.get(kind, 1.0)
        inst = ("bell" if s["fog"] > 0.5 else PLACES[s["place"]][1]) if kind == "open" else "pluck"
        for k, (e, d) in enumerate(steps):
            _later(e * eighth * speed, inst, d, vol + (0.05 if k == 0 else 0.0), notes)
            if kind == "fast":
                _later(e * eighth * speed, "bell", d, vol * 0.35, notes)
        e, d = steps[-1]
        _later(e * eighth * speed, "bell", d if kind == "open" else d + 5, vol * 0.5, notes)
        hold = (e + 2) * eighth * speed
    s["hold"] = max(s["hold"], s["t"] + hold)


# ---- the interface
def cue(name, n=0):
    """A one-shot sound for something that just happened; n is a step in a chain, a mark, which bird, how many, which
    burst or which place."""
    if not sounds or state["muted"] or _capped(name, *CAPS.get(name, (3, 0.3))):
        return
    s = _seq
    top = len(scale) - 1
    if name in SIMPLE:
        _play(name, SIMPLE[name])
    if name == "call":
        _play(f"call{_rng.randint(1, VARIANTS['call'])}", 0.22)
    elif name == "liftoff":
        _motif("fast", 0.26)
    elif name == "join":
        _note("pluck", (2 + n) % len(scale), 0.38)
        _play(f"call{_rng.randint(1, VARIANTS['call'])}", 0.1)
    elif name == "feed":
        _play("sparkle", 0.25)
        _note("bell", 5 + n % (top - 4), 0.2)
    elif name == "miss":
        _play("miss", 0.45)
        _later(0.15, "bell", 7, 0.28)
    elif name == "catch":
        _play("catch", 0.55)
        if n:                                       # one of the eight: a low minor bell
            for k in range(3):
                _later(0.25 + 0.35 * k, "bell", k, 0.3, [64, 67, 71])
            _later(0.25, "pluck", 0, 0.25, [62])
    elif name == "chime":                           # the dance's marks climb the scale in thirds
        d = n * (top - 2) // 23 + (2 if n % 2 else 0)
        _note("bell", d, 0.42)
        if d >= 5:
            _note("pluck", d - 5, 0.16)
    elif name == "mark":                            # the guide's trail climbs the scale on the marimba
        _note("mari", max(0, n) * top // 15, 0.42)
    elif name == "course":                          # follow me: a quick rising call
        for t, d in ((0.0, 5), (0.1, 7), (0.2, 8), (0.42, 10)):
            _later(t, "mari", d, 0.34)
            _later(t, "pluck", d, 0.12)
    elif name == "balloon":
        d = _rng.choice((5, 6, 7))
        _note("mari", d, 0.34)
        _later(0.13, "mari", d + 2, 0.38)
        _play(f"call{_rng.randint(1, VARIANTS['call'])}", 0.1)
    elif name == "watch":
        for k, d in enumerate((0, 2, 4, 5, 7, 9)):
            _later(0.3 * k, "bell", d, 0.16 + 0.03 * k)
    elif name == "merge":
        _force(s["palette"] or "gold")
        for k, d in enumerate((0, 2, 4, 5, 7)):
            _later(0.07 * k, "pluck", d, 0.3)
        _later(0.4, "bell", top, 0.25)
        for t in (0.3, 0.5, 0.8):
            s["queue"].append((s["t"] + t, f"call{_rng.randint(1, VARIANTS['call'])}", 0.15))
    elif name == "roost":                           # the motif, home at last
        _force("roost")
        _motif("whole", 0.32)
    elif name == "night":
        _force("cold")
        _motif("broken", 0.3)
    elif name == "lost":
        _force("cold")
        _motif("lost", 0.3)
    elif name == "snag":                            # n birds knocked down this step: more of them, a second knock
        _play("snag", 0.3 + 0.06 * min(4, max(1, n)))
        if n > 2:
            s["queue"].append((s["t"] + 0.06, "snag", 0.22))
    elif name == "burst":
        _play(f"burst{n % VARIANTS['burst'] + 1}", 0.55)
    elif name == "blade":                           # sent every second or so: a few takes, never quite the same
        _play(f"blade{_rng.randint(1, VARIANTS['blade'])}", _rng.uniform(0.2, 0.28))
    elif name == "buoy":
        _play(f"buoy{_rng.randint(1, VARIANTS['buoy'])}", 0.3)
    elif name == "gull":
        _play(f"gull{_rng.randint(1, VARIANTS['gull'])}", 0.38)
    elif name == "card":                            # the evening's signature, in its own voice
        for when, snd, vol in CARDS[max(0, min(7, n))]:
            s["queue"].append((s["t"] + when, snd, vol))
    elif name == "finale":                          # every flock's dance: a swell, the scale rising, every layer open
        _force("finale")
        _play("swell", 0.45)
        for k in range(len(scale)):
            _later(0.6 + 0.11 * k, "cel" if k % 2 else "bell", k, 0.1 + 0.012 * k)
        s["full"] = s["t"] + 10
    elif name == "home":                            # the journey's end: the motif whole on harp and celesta, full
        _force("roost")
        _motif("whole", 0.34)
        crown = MOTIF[-1][0] * s["eighth"] * 1.15
        for e, d in MOTIF:
            _later(e * s["eighth"] * 1.15, "cel", d, 0.16, pitches("gold"))
        for m in (74, 78, 81):
            _later(crown, "bell", 0, 0.14, [m])
        _later(0.0, "pluck", 0, 0.3, [62])
        s["queue"].append((s["t"] + crown - 2.2, "swell", 0.35))      # the swell peaks on the crowning D
        s["full"] = s["t"] + 16


def update(dt, mood):
    """Every frame: eases the beds and loops toward the mood, plays what is due, and ticks the score."""
    if not sounds:
        return
    s = _seq
    s["t"] += dt
    t = s["t"]
    get = mood.get
    scene, light, paused, result = get("scene", "play"), get("light", 0.0), get("paused", False), get("result")
    n, speed, gather = get("flock", 0), get("speed", 0.6), get("gather", 0.0)
    squall, danger = get("squall", 0.0), get("danger", 0.0)
    course, progress = get("course", 0.0), get("progress", 0.0)
    fog, sea, wind, festive = get("fog", 0.0), get("sea", 0.0), get("wind", 0.0), get("festive", 0.0)
    shelter, finale = get("shelter", 0.0), get("finale", 0.0)
    place = 0 if scene == "title" else max(0, min(7, int(get("place", 0) or 0)))
    s["place"], s["fog"], s["finale"] = place, fog, finale
    s["eighth"] = 60 / PLACES[place][0] / 2 * (1 - 0.15 * festive)
    target = 0.0 if state["muted"] else (0.3 if paused else 1.0)
    s["master"] += (target - s["master"]) * min(1.0, dt * 4)
    m = s["master"]

    size = min(1.0, n / 260) ** 0.6 if n > 0 else 0.0
    dark = min(1.0, max(0.0, (light - 0.68) / 0.25))
    hush, still = 1 - 0.5 * fog, 1 - 0.35 * shelter     # fog lowers every bed, the bright ones most; shelter the air
    want = {"wing": size * (0.25 + 0.45 * speed) * (1 - 0.7 * gather) * still * hush,
            "wing_tight": size * (0.2 + 0.5 * speed) * gather * still * hush,
            "chatter": 0.3 * min(1.0, n / 300) ** 0.7 * ((1.4 if scene == "summary" else 1.0) - 0.5 * light)
            * (1 - 0.8 * fog),
            "wind": (0.28 * (1 - 0.45 * light) + 0.3 * squall + 0.35 * wind) * still * hush,
            "night": 0.35 * dark * (1 - 0.8 * fog),
            "rain": 0.55 * squall * hush,
            "surf": 0.45 * sea * hush}
    ease = min(1.0, dt * 2.5)
    for bed in _beds:
        bed[2] += (want[bed[0]] - bed[2]) * ease
        bed[1].set_volume(max(0.0, bed[2] * m))

    if scene == "title":                            # pad, bass, counter-melody, choir: the flock's layers
        layers = (1.0, 0.55, 0.0, 0.0)
    elif scene == "journey":
        layers = (0.8, 0.4, 0.0, 0.0)
    elif scene == "ending":
        layers = (1.0, 0.6, 0.3, 0.9)
    elif scene == "summary":
        layers = (1.0, 0.5, 0.0, 0.6 if result == "roost" else 0.0)
    else:
        layers = (0.55 + 0.45 * _ramp(n, 0, 60), _ramp(n, 20, 50), _ramp(n, 60, 100), _ramp(n, 150, 200))
    full = 1.0 if t < s["full"] else finale         # the finale and the journey's end: every layer, whatever the size
    lay, k = s["lay"], min(1.0, dt / 3.0)
    for j in range(4):
        lay[j] += (max(layers[j], full) - lay[j]) * k
    boost = (1 + 0.4 * shelter - 0.25 * fog, 1 - 0.6 * fog, 1 + 0.6 * full - 0.7 * fog)     # pad, bass, choir
    for lp, j, b in zip(_loops, (0, 1, 3), boost):
        lp.ease(dt, lay[j] * m * b)

    s["check"] -= dt
    if s["check"] <= 0:                             # a bed that stopped (a device change, a stray stop) starts again
        s["check"] = 2.0
        for name, ch, _lv in _beds:
            if not ch.get_busy():
                ch.play(sounds[name], loops=-1)

    if s["queue"]:
        due = [q for q in s["queue"] if q[0] <= t]
        if due:
            s["queue"] = [q for q in s["queue"] if q[0] > t]
            for _when, name, vol in due:
                _play(name, vol)

    if scene != s["scene"]:
        s["scene"], s["tick"], s["next"] = scene, 0, t
        s["motif_at"] = t + _rng.uniform(30, 40)
    while t >= s["next"]:
        if t - s["next"] > 1.0:                     # a long hitch: skip ahead, never a burst of notes
            s["next"] = t
        s["next"] += s["eighth"]
        _tick(scene, light - 0.35 * festive, paused, danger, result, course, progress)    # festive: a lighter hour


def _phrase(zone):
    """Two bars of lead, a question (ending up, away from home) or its answer (ending on D or A), and the bell
    counter-melody's reply in the lead's rests."""
    s = _seq
    p = s["place"]
    s["ask"] = ask = not s["ask"]
    lead, counter = {}, {}
    shape = "night" if s["fog"] > 0.5 else zone     # in fog, the sparsest shapes
    if ask or _rng.random() < 0.3:                  # an answer usually keeps the question's rhythm
        s["rhythm"] = _rng.choice(RHYTHMS.get(f"{shape}{p}", RHYTHMS[shape]))
    if not ask and zone != "gold" and _rng.random() < PLACES[p][5]:
        return lead, counter                        # the answer is a rest
    rhythm = s["rhythm"]
    centre = {"gold": 6, "dusk": 5, "night": 4}[zone] + PLACES[p][4]
    first = max(1, min(9, (centre if ask else s["deg"]) + _rng.choice((-1, 0, 1))))
    end = _rng.choice((4, 6, 7) if ask else (3, 5, 5, 8))
    last = len(rhythm) - 1
    for j, e in enumerate(rhythm):
        d = end if j == last else first if j == 0 else round(first + (end - first) * j / last) + _rng.choice((-1, 0, 0, 1))
        lead[e] = max(0, min(10, d))
    s["deg"] = end
    if ask:
        for off, up in ((2, 2), (3, 1)):
            if rhythm[-1] + off < 16:
                counter[rhythm[-1] + off] = min(10, end + up)
    else:
        counter[0] = min(10, first + 2)
    return lead, counter


def _tick(scene, light, paused, danger, result, course, progress):
    s = _seq
    i = s["tick"]
    s["tick"] += 1
    _bpm, voice, night_voice, counter_voice, _shift, _rest, beat, ostinato = PLACES[s["place"]]
    fog, finale = s["fog"], s["finale"] > 0.5
    if i % 16 == 0:                                 # a new chord every two bars
        name = _palette(scene, light, result, progress)
        if name != s["palette"]:
            s["palette"], i, s["tick"] = name, 0, 1
            scale[:] = pitches(name)
        chords = PALETTES[name][0]
        _chord(chords[(i // 16) % len(chords)])
    zone = "gold" if light < 0.4 or finale else ("dusk" if light < 0.75 else "night")
    calm = 0.4 if paused else 1.0
    if scene == "title":
        if i % 64 == 0:
            _motif("whole", 0.3)
        d = TITLE.get(i % 64)
        if d is not None:
            _note("pluck", d, 0.3 + (0.06 if i % 16 == 0 else 0.0))
            if i % 16 == 0:
                _note("bell", d, 0.1)
    elif scene in ("summary", "journey", "ending"):
        every = {"journey": 96, "ending": 32}.get(scene)    # the map: the motif now and then; the end: every 4 bars
        if every and i % every == 0:
            _motif("whole" if scene == "ending" or i % (2 * every) == 0 else "open", 0.26)
        elif s["t"] >= s["hold"] and _rng.random() < (0.06 if scene == "journey" else 0.12) * calm * (
                1.8 if i % 8 == 0 else 0.6):
            s["deg"] = max(2, min(8, s["deg"] + _rng.choice((-2, -1, 1, 2))))
            _note("bell" if _rng.random() < 0.5 else "pluck", s["deg"], 0.2)
    else:
        if i % 16 == 0:
            s["lead"], s["counter"] = {}, {}
            if s["t"] >= s["motif_at"] and course < 0.3 and danger < 0.3 and not paused:
                _motif("open", 0.28)                # the eight's phrase as the question; the next phrase answers
                s["motif_at"] = s["t"] + _rng.uniform(30, 40)
                s["ask"] = True
            else:
                s["lead"], s["counter"] = _phrase(zone)
        thin = (1 - 0.7 * course) * calm
        d = s["lead"].get(i % 16)
        if d is not None and s["t"] >= s["hold"] and _rng.random() < 1 - 0.5 * danger - 0.4 * fog:
            inst = night_voice if zone == "night" and _rng.random() < 0.5 else voice
            inst = "bell" if fog > 0.5 else inst
            base = {"gold": 0.27, "dusk": 0.24, "night": 0.2}[zone]
            vol = (base + (0.05 if i % 16 == min(s["lead"]) else 0.0)) * thin
            _note(inst, d, vol)
            if finale:                              # the great dance: the lead doubled, harp and celesta
                _note("pluck" if inst == "cel" else "cel", d, vol * 0.6)
        c = s["counter"].get(i % 16)
        if c is not None and s["lay"][2] > 0.03:
            _note(counter_voice, c, 0.17 * s["lay"][2] * thin * (1 - fog))
        if ostinato and i % ostinato[2] == 0:
            inst, notes, every, vol = ostinato
            _note(inst, 0, vol * thin * (1 - fog), [notes[(i // every) % len(notes)]])
        if course > 0.05:                           # following a guide: a soft shaker and a plucked ostinato
            _play("shaker", course * (0.2 if i % 2 == 0 else 0.11))
            if i % 2 == 0:
                _note("pluck", (0, 3)[(i // 2) % 2], 0.09 * course)
    if danger > 0.05 and i % 2 == 0:
        _play("pulse", 0.55 * danger * beat)
    elif danger > 0.6:
        _play("pulse", 0.3 * danger * beat)


def toggle_mute():
    state["muted"] = not state["muted"]
    if state["muted"] and sounds:                   # silent now, not after the next frame's easing
        _seq["master"] = 0.0
        _seq["queue"].clear()
        for i in range(pygame.mixer.get_num_channels()):
            ch = pygame.mixer.Channel(i)
            ch.set_volume(0)
            if i >= RESERVED:
                ch.stop()


# ---- the old interface, until the app passes a mood
def play(name, volume=1.0):
    cue(name)


def wings(level):
    now = time.perf_counter()
    dt = min(0.1, now - state["last"]) if state["last"] else 1 / 60
    state["last"] = now
    update(dt, {"scene": "play", "flock": int(260 * max(0.0, min(1.0, level))), "speed": 0.7})
