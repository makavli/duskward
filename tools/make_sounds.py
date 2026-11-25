"""Synthesises the game's sounds into duskward/sounds/ (16-bit mono WAV), with the standard library only.
    python tools/make_sounds.py

- Beds (wing, wing_tight, chatter, wind, night, rain, surf) and the chord loops (pad, choir per chord, bass per root)
  loop without a seam: every tone runs a whole number of cycles in the loop, filters run twice round, and scattered
  events (wingbeats, chirps, drops, waves) wrap round the end.
- Notes: a harp-like pluck, a soft bell, a marimba and a celesta on D4..D6 (D E F# G A B C); duskward/audio.py plays
  the score from them.
- Rates: dull beds, chord loops and dull cues (thunder, burner, snag, blade, foghorn, buoy, bridge) at 11025 Hz, notes,
  bright beds and bright cues at 22050, the 0.3.0 short cues at 44100. The browser build carries every file, so the
  whole set stays at or under 7.5 MB (tests/test_audio.py checks it).
- One seeded generator makes everything in a fixed order: 1.0's sounds come after 0.3.0's, so every older file stays
  the same byte for byte. New sounds go at the end.
"""
import array
import glob
import math
import os
import random
import sys
import wave

OUT = os.path.join(os.path.dirname(__file__), "..", "duskward", "sounds")
TAU = 2 * math.pi
LO, MID, HI = 11025, 22050, 44100
NOTES = (62, 64, 66, 67, 69, 71, 72, 74, 76, 78, 79, 81, 83, 84, 86)    # duskward/audio.py keeps the same list
CHORDS = {                                                               # pad voicings, MIDI notes
    "Dadd9": (38, 50, 57, 64, 66), "Bm7": (47, 54, 57, 62), "Gmaj9": (43, 50, 54, 57, 59),
    "Asus2": (45, 52, 59, 64), "Dsus2": (38, 50, 57, 64), "Em7": (40, 47, 50, 55), "Cmaj7": (48, 55, 59, 64),
    "Dm9": (38, 45, 53, 60, 64), "Bbmaj9": (46, 53, 57, 60, 62), "Fmaj7": (41, 48, 52, 57), "Am7": (45, 52, 55, 60),
}
NEW_CHORDS = {                                                           # 1.0's places; choir notes stay <= F#4
    "Cadd9": (36, 43, 52, 55, 62), "Gsus2": (43, 50, 55, 57, 62), "Esus4": (40, 47, 52, 57),
    "Em9": (40, 47, 55, 62, 66), "Am9": (45, 52, 55, 59, 60), "Cmaj9": (36, 43, 52, 55, 59, 62),
    "Dmaj7": (38, 45, 54, 57, 61),
}
rng = random.Random(11)
written = []


# ---- the toolkit
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def save(name, xs, rate, peak=0.7):
    """Normalise to peak (0.7 is about -3 dBFS) and write."""
    k = peak * 32767 / max(1e-9, max(map(abs, xs)))
    a = array.array("h", [int(x * k) for x in xs])
    if sys.byteorder == "big":
        a.byteswap()
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(a.tobytes())
    written.append((name, os.path.getsize(path)))


def noise(n):
    r = rng.random
    return [2 * r() - 1 for _ in range(n)]


def level(xs, target):
    """Scales xs to this RMS, so layers mix by design and not by accident."""
    r = math.sqrt(sum(x * x for x in xs) / max(1, len(xs)))
    k = target / (r + 1e-12)
    return [x * k for x in xs]


def lowpass(xs, cut, rate, loop=False):
    """One-pole low-pass. loop: run twice round, so a loop's ends still join."""
    a = 1 - math.exp(-TAU * cut / rate)
    y = 0.0
    if loop:
        for x in xs:
            y += a * (x - y)
    out = []
    ap = out.append
    for x in xs:
        y += a * (x - y)
        ap(y)
    return out


def svf(xs, cut, rate, q=0.8, band=True, loop=False):
    """Zero-delay state-variable filter, stable at any cutoff: band-pass (unity peak), or low-pass with band=False.
    cut is Hz, or one value per sample. loop: run twice round, so a loop's ends still join."""
    k = 1.0 / q

    def coef(c):
        g = math.tan(math.pi * min(c, rate * 0.45) / rate)
        a1 = 1 / (1 + g * (g + k))
        return a1, g * a1, g * g * a1

    cs = [coef(c) for c in cut] if isinstance(cut, list) else None
    a1, a2, a3 = coef(cut) if cs is None else (0.0, 0.0, 0.0)
    s1 = s2 = 0.0
    out = [0.0] * len(xs)
    for _ in range(2 if loop else 1):
        for i, x in enumerate(xs):
            if cs:
                a1, a2, a3 = cs[i]
            v3 = x - s2
            v1 = a1 * s1 + a2 * v3
            v2 = s2 + a2 * s1 + a3 * v3
            s1 = 2 * v1 - s1
            s2 = 2 * v2 - s2
            out[i] = v1 * k if band else v2
    return out


def partials(n, rate, parts):
    """A sum of decaying sines, each a rotating phasor: parts = [(Hz, amplitude, seconds to fall to 1/e)]."""
    out = [0.0] * n
    for f, a, tau in parts:
        if f >= rate * 0.45:
            continue
        w = TAU * f / rate
        d = math.exp(-1.0 / (tau * rate))
        cd, sd = math.cos(w) * d, math.sin(w) * d
        x, y = a, 0.0
        for i in range(n):
            x, y = x * cd - y * sd, x * sd + y * cd
            out[i] += y
    return out


def place(buf, ev, at, gain=1.0, wrap=True):
    """Adds ev into buf from index at; a loop's events wrap round its end, a cue's are cut there."""
    n = len(buf)
    for j, v in enumerate(ev):
        k = at + j
        if k >= n:
            if not wrap:
                return
            k %= n
        buf[k] += v * gain


def finish(xs, rate, attack=0.002, tail=0.3):
    """A short fade in, and a cosine fade over the last tail of the sound."""
    n = len(xs)
    a, t0 = max(1, int(attack * rate)), int(n * (1 - tail))
    for i in range(a):
        xs[i] *= i / a
    for i in range(t0, n):
        xs[i] *= 0.5 + 0.5 * math.cos(math.pi * (i - t0) / (n - t0))
    return xs


def window(xs, power=2.0):
    n = len(xs)
    return [x * math.sin(math.pi * i / n) ** power for i, x in enumerate(xs)]


def arch(n, a, b, c, peak=0.5):
    """A per-sample cutoff that glides a -> b (at peak of the way) -> c."""
    out = []
    for i in range(n):
        u = i / n
        out.append(a + (b - a) * u / peak if u < peak else b + (c - b) * (u - peak) / (1 - peak))
    return out


def flap(rate, centre, ms):
    """One wingbeat: a breath of band-passed noise, rising and falling."""
    return window(svf(noise(max(8, int(rate * ms / 1000))), centre, rate, q=1.1))


def chirp(rate, f0, f1, dur, bend=0.0, vib=0.0, vrate=35.0, rasp=0.0):
    """One starling whistle: f0 to f1, arched by bend, with vibrato; rasp threads a wheeze through it."""
    n = int(dur * rate)
    ph, out, r = 0.0, [], rng.random
    for i in range(n):
        u = i / n
        f = f0 + (f1 - f0) * u + bend * math.sin(math.pi * u) + vib * math.sin(TAU * vrate * i / rate)
        ph += TAU * f / rate
        s = math.sin(ph) + 0.18 * math.sin(2 * ph)
        if rasp:
            s *= 1 - rasp + rasp * (2 * r() - 1)
        out.append(s * math.sin(math.pi * u) ** 0.8)
    return out


def clicks(rate, k, f):
    one = partials(int(0.004 * rate), rate, [(f, 1.0, 0.0012), (f * 1.5, 0.5, 0.0008)])
    out = [0.0] * int((0.014 * k + 0.01) * rate)
    for j in range(k):
        place(out, one, int(j * 0.014 * rate), 1 - 0.1 * j, wrap=False)
    return out


def starling(rate, p=1.0):
    """One of a starling's sounds: a rising whistle, a falling wheeze, a twitter or a run of clicks."""
    kind = rng.random()
    if kind < 0.35:
        return chirp(rate, 2300 * p, 3000 * p, rng.uniform(0.08, 0.18), bend=1200 * p, vib=40)
    if kind < 0.6:
        return chirp(rate, 4200 * p, 2500 * p, rng.uniform(0.12, 0.25), vib=90, vrate=40, rasp=0.3)
    if kind < 0.82:
        return chirp(rate, 3000 * p, 3300 * p, rng.uniform(0.06, 0.12), vib=450, vrate=28)
    return clicks(rate, rng.randint(3, 6), 3500 * p)


# ---- the instruments
def pluck(m):
    """A harp-like string: bright harmonics that die first, a slightly sharp twin, the finger's soft thump."""
    f, u = hz(m), (m - 62) / 24
    tau = 0.65 - 0.35 * u
    n = int((1.8 * tau + 0.12) * MID)
    parts = [(f * h * math.sqrt(1 + 0.0002 * h * h), abs(math.sin(math.pi * h * 0.17)) / h ** 1.1,
              tau / (1 + 0.6 * (h - 1))) for h in range(1, 9)]
    parts.append((f * 1.0035, 0.3, tau * 0.85))
    xs = partials(n, MID, parts)
    thump = svf(noise(int(0.012 * MID)), f * 2, MID, q=0.8)
    place(xs, [v * (1 - i / len(thump)) for i, v in enumerate(thump)], 0, 0.15, wrap=False)
    return finish(xs, MID, attack=0.002, tail=0.35)


def bell(m):
    """A soft celesta bell: a beating twin of the fundamental and a few inharmonic partials."""
    f, u = hz(m), (m - 62) / 24
    tau = 0.8 - 0.35 * u
    n = int((1.7 * tau + 0.1) * MID)
    parts = [(f, 1.0, tau), (f + 1.3, 0.45, tau * 0.9), (2.0 * f, 0.3, tau * 0.5), (2.76 * f, 0.22, tau * 0.33),
             (4.07 * f, 0.1, tau * 0.2), (5.4 * f, 0.06, tau * 0.13)]
    return finish(partials(n, MID, parts), MID, attack=0.0015, tail=0.3)


def marimba(m):
    """A wooden bar: the tuned partials at 1, 4 and about 10 times the note, dying fast, and the mallet's knock."""
    f, u = hz(m), (m - 62) / 24
    tau = 0.26 - 0.13 * u
    n = int((1.8 * tau + 0.05) * MID)
    xs = partials(n, MID, [(f, 1.0, tau), (f * 1.003, 0.2, tau), (4.0 * f, 0.25, tau * 0.3), (9.9 * f, 0.06, tau * 0.12)])
    knock = lowpass(noise(int(0.008 * MID)), 1800, MID)
    place(xs, [v * (1 - i / len(knock)) for i, v in enumerate(knock)], 0, 0.3, wrap=False)
    return finish(xs, MID, attack=0.001, tail=0.3)


def celesta(m):
    """A celesta: a steel bar over a wooden box, glassy and nearly pure, a slow shimmer (a twin 0.12% sharp), a ting
    of the bar's high partials that dies at once, and the felt hammer's tap."""
    f, u = hz(m), (m - 62) / 24
    tau = 0.5 - 0.22 * u
    n = int((1.6 * tau + 0.08) * MID)
    xs = partials(n, MID, [(f, 1.0, tau), (f * 1.0012, 0.3, tau * 1.2), (2 * f, 0.1, tau * 0.5),
                           (5.4 * f, 0.07, 0.012), (8.9 * f, 0.03, 0.006)])
    tap = lowpass(noise(int(0.006 * MID)), 3000, MID)
    place(xs, [v * (1 - i / len(tap)) for i, v in enumerate(tap)], 0, 0.05, wrap=False)
    return finish(xs, MID, attack=0.001, tail=0.35)


TABLE = 4096
DARK = [sum(a * math.sin(TAU * (h + 1) * i / TABLE) for h, a in enumerate((1, 0.32, 0.1, 0.035))) for i in range(TABLE)]
BRIGHT = [sum(math.sin(TAU * h * i / TABLE) / h ** 1.3 for h in range(1, 9)) for i in range(TABLE)]
BOW = [sum(math.sin(TAU * h * i / TABLE) / h ** 1.15 for h in range(1, 25)) for i in range(TABLE)]    # bass: <= A2 only
VOX = [sum(math.sin(TAU * h * i / TABLE) / h for h in range(1, 9)) for i in range(TABLE)]           # choir: <= F#4 only
ROOTS = {"D": 38, "E": 40, "F": 41, "G": 43, "A": 45, "Bb": 34, "B": 35, "C": 36}


def bass(m, secs=2.0):
    """A bowed bass on the chord's root: a rich string, a slow vibrato and one bow swell a loop, over a pure sub drone.
    The note, the vibrato (5 Hz) and the swell all run whole cycles in the loop."""
    n = int(LO * secs)
    f = round(hz(m) * secs) / secs
    dv, o, ph0 = 0.004 * f / (TAU * 5), rng.random() * TAU, rng.random()
    sin, out = math.sin, []
    for i in range(n):
        t = i / LO
        ph = ph0 + f * t + dv * sin(TAU * 5 * t)
        out.append(BOW[int(ph * TABLE) & 4095] * (0.85 + 0.15 * sin(TAU * t / secs + o)) + 0.6 * sin(TAU * f * t))
    return svf(out, 520, LO, q=0.9, band=False, loop=True)


def choir(notes, secs=2.0):
    """A soft choir on the chord's upper notes: two detuned voices a note, each with its own vibrato, through the
    formants of "ah", swelling once a loop."""
    n = int(LO * secs)
    src = [0.0] * n
    sin = math.sin
    for m in [x for x in notes if x >= 47]:
        for cents in (-9, 9):
            f = round(hz(m) * 2 ** (cents / 1200) * secs) / secs
            vr = rng.choice((4, 5, 6))                                  # whole cycles in the 2 s loop
            ph0, dv, o = rng.random(), 0.005 * f / (TAU * vr), rng.random() * TAU
            for i in range(n):
                t = i / LO
                src[i] += VOX[int((ph0 + f * t + dv * sin(TAU * vr * t + o)) * TABLE) & 4095]
    a, b, c = (svf(src, fc, LO, q=q, loop=True) for fc, q in ((700, 4), (1150, 5), (2500, 6)))
    o = rng.random() * TAU
    return [(x + 0.6 * y + 0.25 * z) * (0.8 + 0.2 * sin(TAU * i / n + o)) for i, (x, y, z) in enumerate(zip(a, b, c))]


def pad(notes, secs=3.0):
    """A warm chord: three detuned voices a note, each breathing and brightening once a loop."""
    n = int(LO * secs)
    out = [0.0] * n
    sin = math.sin
    for m in notes:
        g = 0.65 if m < 48 else 1.0
        for cents, gv in ((-8, 0.7), (0, 1.0), (7, 0.7)):
            f = round(hz(m) * 2 ** (cents / 1200) * secs) / secs      # a whole number of cycles: the loop joins
            inc, ph = f * TABLE / LO, rng.random() * TABLE
            o1, o2, amp = rng.random() * TAU, rng.random() * TAU, g * gv
            for i in range(n):
                u = TAU * i / n
                w = 0.35 + 0.3 * sin(u + o1)
                j = int(ph) & 4095
                d = DARK[j]
                out[i] += amp * (1 + 0.12 * sin(2 * u + o2)) * (d + w * (BRIGHT[j] - d))
                ph += inc
    return out


# ---- the beds (loops)
def wing_bed(name, secs, centre, q, flaps, flap_ms, swells):
    """The murmuration: a soft rush that swells and ebbs, threaded with thousands of single wingbeats."""
    n = int(LO * secs)
    rush = level(svf(noise(n), centre, LO, q=q, loop=True), 0.2)
    body = level(svf(noise(n), centre * 0.45, LO, q=0.7, band=False, loop=True), 0.12)
    env = [0.55 + sum(a * math.sin(TAU * k * i / n + p) for k, a, p in swells) for i in range(n)]
    out = [(r + b) * e for r, b, e in zip(rush, body, env)]
    pool = [level(flap(LO, rng.uniform(centre * 0.6, centre * 1.5), rng.uniform(*flap_ms)), 0.25) for _ in range(32)]
    for _ in range(flaps):
        at = rng.randrange(n)
        place(out, rng.choice(pool), at, rng.uniform(0.2, 0.7) * env[at])
    save(name, lowpass(out, 2400, LO, loop=True), LO, 0.5)


def chatter():
    n = 4 * MID
    out = [0.0] * n
    for _ in range(70):
        place(out, starling(MID, rng.uniform(0.85, 1.2)), rng.randrange(n), rng.uniform(0.15, 1.0))
    save("chatter", lowpass(out, 4500, MID, loop=True), MID, 0.5)


def wind():
    """Marsh wind in gusts, reeds rustling with it, water lapping somewhere."""
    n = 5 * LO
    cut = [230 + 150 * (0.5 + 0.5 * math.sin(TAU * i / n)) + 70 * math.sin(TAU * 3 * i / n + 1) for i in range(n)]
    air = level(svf(noise(n), cut, LO, q=0.6, band=False, loop=True), 0.25)
    reeds = level(svf(noise(n), 1500, LO, q=0.7, loop=True), 0.05)
    gust = [0.6 + 0.25 * math.sin(TAU * 2 * i / n + 0.5) + 0.1 * math.sin(TAU * 5 * i / n) for i in range(n)]
    out = [a * g + r * g * g for a, r, g in zip(air, reeds, gust)]
    for _ in range(9):
        lap = level(window(svf(noise(int(rng.uniform(0.35, 0.8) * LO)), rng.uniform(260, 480), LO, q=1.5)), 0.1)
        place(out, lap, rng.randrange(n), rng.uniform(0.5, 1.0))
    save("wind", out, LO, 0.5)


def night():
    """Three crickets near, many far, in a still night. Each near cricket's period divides the 2 s loop."""
    n = 2 * MID
    out = [0.0] * n
    for f, period, gain, start in ((4400, 0.5, 1.0, 0.03), (4800, 2 / 3, 0.55, 0.29), (3900, 1.0, 0.4, 0.51)):
        pulse = window(partials(int(0.016 * MID), MID, [(f, 1.0, 1.0), (2 * f, 0.15, 1.0)]), 1.0)
        t = start
        while t < 2:
            for p in range(3):
                place(out, pulse, int((t + p * 0.026) * MID), gain * (1 - 0.15 * p))
            t += period
    for _ in range(70):
        f = rng.uniform(3500, 5200)
        place(out, window(partials(int(0.012 * MID), MID, [(f, 1.0, 1.0)]), 1.0), rng.randrange(n),
              rng.uniform(0.04, 0.14))
    air = level(svf(noise(n), 400, MID, q=0.7, band=False, loop=True), 0.02)
    save("night", lowpass([a + b for a, b in zip(out, air)], 6500, MID, loop=True), MID, 0.45)


def rain():
    """Soft rain: a hush and a patter of drops, nothing sharp."""
    n = 3 * MID
    out = level(svf(noise(n), 1100, MID, q=0.45, loop=True), 0.12)
    pool = [partials(int(0.03 * MID), MID, [(rng.uniform(1500, 4000), 1.0, rng.uniform(0.003, 0.008))])
            for _ in range(24)]
    for _ in range(900):
        place(out, rng.choice(pool), rng.randrange(n), rng.uniform(0.05, 0.35))
    save("rain", lowpass(out, 5000, MID, loop=True), MID, 0.5)


def surf():
    """The sea below: a wash that never stops, and waves breaking on the shingle, each drawing a hiss back after it."""
    n = 7 * LO
    swell = [0.7 + 0.2 * math.sin(TAU * i / n + 0.4) + 0.1 * math.sin(TAU * 3 * i / n) for i in range(n)]
    out = [w * e for w, e in zip(level(svf(noise(n), 320, LO, q=0.6, band=False, loop=True), 0.14), swell)]
    m = int(2.6 * LO)
    for at, g in ((0.2, 1.0), (2.7, 0.7), (4.9, 0.85)):
        crash = level(svf(noise(m), arch(m, 250, 1400, 300, 0.2), LO, q=0.6, band=False), 0.3)
        back = level(svf(noise(m), 2200, LO, q=0.7), 0.06)
        ev = []
        for j, (c, b) in enumerate(zip(crash, back)):
            t = j / LO
            e = min(1.0, t / 0.35) * math.exp(-max(0.0, t - 0.35) / 0.6) * min(1.0, (m - j) / (0.3 * LO))
            ev.append(c * e + b * math.sin(math.pi * min(1.0, max(0.0, (t - 0.6) / 1.7))) ** 2)
        place(out, ev, int(at * LO), g)
    save("surf", lowpass(out, 3000, LO, loop=True), LO, 0.5)


# ---- the cues
def calls():
    one = chirp(HI, 2300, 2600, 0.22, bend=1500, vib=40)
    one += [0.0] * int(0.04 * HI) + chirp(HI, 3800, 3300, 0.06)
    two = clicks(HI, 4, 3600) + chirp(HI, 4300, 2500, 0.25, vib=120, vrate=40, rasp=0.25)
    three = chirp(HI, 3000, 3400, 0.12, vib=500, vrate=28) + chirp(HI, 3600, 2800, 0.1, bend=300)
    for k, xs in enumerate((one, two, three), 1):
        save(f"call{k}", finish(lowpass(xs, 6000, HI), HI, 0.003, 0.1), HI)


def liftoff():
    """The eight leave the wire: a flurry of wings, slowing as they climb, and a few bright calls."""
    n = int(1.6 * MID)
    out = [0.0] * n
    pool = [level(flap(MID, rng.uniform(600, 1200), rng.uniform(25, 40)), 0.25) for _ in range(20)]
    for _ in range(8):
        t, beat, g = rng.uniform(0, 0.35), rng.uniform(11, 15), rng.uniform(0.6, 1.0)
        while t < 1.3:
            place(out, rng.choice(pool), int(t * MID), g, wrap=False)
            t += 1 / beat
            g *= 0.9
            beat *= 0.985
    for _ in range(4):
        place(out, level(starling(MID, rng.uniform(0.95, 1.15)), 0.12), int(rng.uniform(0.1, 1.0) * MID), 1.0,
              wrap=False)
    save("liftoff", finish(out, MID, 0.002, 0.25), MID)


def gust(name, rate, secs, a, b, c, flaps=0):
    n = int(secs * rate)
    air = level(svf(noise(n), arch(n, a, b, c, 0.6), rate, q=0.7), 0.2)
    body = level(svf(noise(n), a, rate, q=0.7, band=False), 0.1)
    out = window([x + y for x, y in zip(air, body)], 1.5)
    for k in range(flaps):
        place(out, level(flap(rate, rng.uniform(700, 1200), 30), 0.2), int((0.05 + 0.12 * k) * rate), 1.0, wrap=False)
    save(name, finish(out, rate, 0.01, 0.2), rate)


def ripple():
    """A wave running through the flock: a swell of wingbeats that rises and falls."""
    n = int(0.9 * HI)
    whoosh = svf(noise(n), arch(n, 500, 1300, 700, 0.3), HI, q=0.8)
    out = level([x * min(1, i / (0.08 * HI)) * (1 - i / n) ** 1.5 for i, x in enumerate(whoosh)], 0.08)
    pool = [level(flap(HI, rng.uniform(700, 1400), rng.uniform(18, 30)), 0.2) for _ in range(20)]
    for _ in range(80):
        t = min(0.7, abs(rng.gauss(0.18, 0.12)))
        place(out, rng.choice(pool), int(t * HI), rng.uniform(0.4, 1.0) * (1 - t), wrap=False)
    save("ripple", finish(out, HI, 0.005, 0.3), HI)


def cry():
    """The falcon, a little way off: kek-kek-kek with an echo, over a low, uneasy swell."""
    n = int(1.2 * HI)
    out = [0.0] * n
    for k in range(3):
        m, ph, note = int(0.1 * HI), 0.0, []
        for i in range(m):
            u = i / m
            f = (2250 - k * 90) * (1 - 0.12 * u) + 40 * math.sin(TAU * 36 * i / HI)
            ph += TAU * f / HI
            note.append((math.sin(ph) + 0.3 * math.sin(2 * ph) + 0.08 * math.sin(3 * ph)) * min(1, i / 300)
                        * (1 - u) ** 0.8)
        place(out, note, int(k * 0.17 * HI), 1 - 0.15 * k, wrap=False)
    dry = lowpass(out, 3500, HI)
    out = dry[:]
    for d, g in ((0.11, 0.3), (0.23, 0.15)):
        place(out, dry, int(d * HI), g, wrap=False)
    out = level(out, 0.12)
    sting = []
    for i in range(n):
        t = i / HI
        s = math.sin(TAU * 73.4 * t) + 0.8 * math.sin(TAU * 77.8 * t) + 0.3 * math.sin(TAU * 146.8 * t)
        sting.append(s * min(1, t / 0.35) * math.exp(-max(0.0, t - 0.35) / 0.45))
    sting = level(sting, 0.1)
    save("cry", finish([a + b for a, b in zip(out, sting)], HI, 0.002, 0.2), HI)


def stoop():
    """The dive: wind whistling higher and higher past the falcon's wings."""
    n = int(1.3 * MID)
    rise = 1.15 * MID
    cut = [350 * (2600 / 350) ** min(1.0, i / rise) for i in range(n)]
    air = level(svf(noise(n), cut, MID, q=3.0), 0.2)
    ph, out = 0.0, []
    for i in range(n):
        ph += TAU * cut[i] / MID
        env = (i / rise) ** 1.6 if i < rise else max(0.0, 1 - (i - rise) / (n - rise))
        out.append((air[i] + 0.06 * math.sin(ph)) * env)
    save("stoop", finish(out, MID, 0.01, 0.05), MID)


def miss():
    """Relief: a quick swoosh up and away."""
    n = int(0.6 * HI)
    cut = [500 * (3200 / 500) ** min(1.0, i / (0.35 * HI)) for i in range(n)]
    xs = svf(noise(n), cut, HI, q=1.2)
    save("miss", finish([x * min(1, i / (0.03 * HI)) * (1 - i / n) ** 2 for i, x in enumerate(xs)], HI, 0.002, 0.1), HI)


def catch():
    """A muted thump and a few loose feathers."""
    n = int(0.5 * HI)
    ph, thump = 0.0, []
    for i in range(n):
        t = i / HI
        ph += TAU * (60 + 70 * math.exp(-t / 0.04)) / HI
        thump.append(math.sin(ph) * math.exp(-t / 0.07))
    out = level(thump, 0.15)
    for k in range(6):
        place(out, level(flap(HI, rng.uniform(900, 1500), rng.uniform(20, 30)), 0.12), int((0.01 + 0.035 * k) * HI),
              1 - 0.14 * k, wrap=False)
    save("catch", finish(lowpass(out, 2500, HI), HI, 0.002, 0.3), HI)


def sparkle():
    """Midges caught in the low sun: a scatter of tiny, high pings."""
    n = int(0.7 * HI)
    out = [0.0] * n
    for _ in range(12):
        f, tau = rng.uniform(3000, 6500), rng.uniform(0.04, 0.12)
        place(out, partials(int(0.25 * HI), HI, [(f, 1.0, tau), (f * 2.76, 0.3, tau * 0.4)]),
              int(rng.uniform(0, 0.35) * HI), rng.uniform(0.3, 1.0), wrap=False)
    save("sparkle", finish(out, HI, 0.001, 0.3), HI)


def thunder():
    """Far thunder: a dull crack, then rumbles rolling away."""
    n = 3 * LO
    cut = [80 + 900 * math.exp(-i / (0.25 * LO)) for i in range(n)]
    xs = svf(noise(n), cut, LO, q=0.6, band=False)
    bumps = [(0.0, 1.0, 0.05), (rng.uniform(0.3, 0.6), 0.7, 0.25), (rng.uniform(0.8, 1.3), 0.5, 0.4),
             (rng.uniform(1.5, 2.0), 0.3, 0.5)]
    out = []
    for i, x in enumerate(xs):
        t = i / LO
        e = sum(a * min(1.0, (t - t0) / 0.03) * math.exp(-(t - t0) / d) for t0, a, d in bumps if t >= t0)
        out.append(x * e * math.exp(-t / 1.0))
    save("thunder", finish(out, LO, 0.01, 0.4), LO)


def pulse():
    """The danger beat: a soft, low heartbeat on D."""
    n = int(0.5 * LO)
    ph, out = 0.0, []
    for i in range(n):
        t = i / LO
        ph += TAU * (73.4 + 50 * math.exp(-t / 0.03)) / LO
        out.append((math.sin(ph) + 0.4 * math.sin(2 * ph)) * math.exp(-t / 0.11))
    save("pulse", finish(out, LO, 0.004, 0.2), LO)


def shaker():
    """One soft shake of seeds: two close grains of high noise."""
    n = int(0.12 * MID)
    out = [0.0] * n
    for at, g in ((0, 1.0), (int(0.018 * MID), 0.6)):
        m = int(0.07 * MID)
        grain = svf(noise(m), 6500, MID, q=0.9)
        place(out, [v * min(1, i / (0.006 * MID)) * math.exp(-i / (0.018 * MID)) for i, v in enumerate(grain)], at, g,
              wrap=False)
    save("shaker", finish(out, MID, 0.001, 0.2), MID, 0.6)


def tick():
    """A bird scarer arming: a dry mechanical click, a tinny ring, a short hiss of gas."""
    n = int(0.3 * MID)
    out = [0.0] * n
    place(out, svf(noise(int(0.003 * MID)), 3000, MID, q=0.7), 0, 1.0, wrap=False)
    place(out, partials(int(0.08 * MID), MID, [(1800, 0.25, 0.015), (4100, 0.15, 0.01)]), 0, 1.0, wrap=False)
    m = int(0.22 * MID)
    hiss = level(svf(noise(m), 4000, MID, q=0.8), 0.06)
    place(out, [v * min(1, i / (0.02 * MID)) * (1 - i / m) ** 2 for i, v in enumerate(hiss)], int(0.04 * MID), 1.0,
          wrap=False)
    save("tick", finish(out, MID, 0.0005, 0.15), MID)


def bang():
    """The gas gun: a deep boom, its tail rolling off over the fields, then every bird nearby taking off at once."""
    n = int(1.6 * MID)
    ph, boom = 0.0, []
    for i in range(n):
        t = i / MID
        ph += TAU * (38 + 90 * math.exp(-t / 0.05)) / MID
        boom.append(math.sin(ph) * math.exp(-t / 0.22))
    out = level(boom, 0.25)
    cut = [180 + 2800 * math.exp(-i / (0.03 * MID)) for i in range(n)]
    crack = svf(noise(n), cut, MID, q=0.6, band=False)
    tail = [v * min(1, i / (0.004 * MID)) * (0.55 * math.exp(-i / (0.05 * MID)) + 0.45 * math.exp(-i / (0.5 * MID)))
            for i, v in enumerate(crack)]
    out = [a + b for a, b in zip(out, level(tail, 0.12))]
    pool = [level(flap(MID, rng.uniform(700, 1300), rng.uniform(20, 34)), 0.12) for _ in range(16)]
    for _ in range(60):
        t = 0.12 + rng.expovariate(1 / 0.25)
        if t < 1.4:
            place(out, rng.choice(pool), int(t * MID), rng.uniform(0.5, 1.0) * (1.4 - t), wrap=False)
    save("bang", finish(out, MID, 0.0005, 0.2), MID, 0.8)


def burner():
    """A hot-air balloon's propane burner, some way off: a soft, fluttering roar."""
    n = int(1.3 * LO)
    flutter = level(lowpass(noise(n), 30, LO), 0.25)
    roar = level(svf(noise(n), 260, LO, q=0.7, band=False), 0.2)
    hiss = level(svf(noise(n), 900, LO, q=0.7), 0.08)
    out = [(a + b) * (1 + f) * min(1, i / (0.12 * LO)) for i, (a, b, f) in enumerate(zip(roar, hiss, flutter))]
    save("burner", finish(lowpass(out, 2500, LO), LO, 0.01, 0.3), LO)


def heron():
    """A grey heron flushed from a pool: one hoarse croak, then three slow, heavy wingbeats."""
    n = int(1.8 * MID)
    out = [0.0] * n
    m = int(0.55 * MID)
    rough = level(lowpass(noise(m), 60, MID), 0.3)
    ph, croak = 0.0, []
    for i in range(m):
        ph += TAU * (250 - 70 * i / m + 25 * rough[i]) / MID
        s = sum(math.sin(h * ph) / h for h in range(1, 13))
        croak.append(s * (1 + 0.5 * rough[i]) * min(1, i / (0.04 * MID)) * min(1, (m - i) / (0.15 * MID)))
    voice = level([a + 0.8 * b for a, b in zip(svf(croak, 850, MID, q=2.5), svf(croak, 1500, MID, q=3))], 0.2)
    place(out, voice, int(0.02 * MID), 1.0, wrap=False)
    for k in range(3):
        beat = level(window(lowpass(noise(int(0.14 * MID)), 420, MID)), 0.15)
        place(out, beat, int((0.72 + 0.34 * k) * MID), 1 - 0.2 * k, wrap=False)
    save("heron", finish(out, MID, 0.002, 0.15), MID)


# ---- 1.0's cues: the places south
def knock(rate, f0, f1, secs, tau):
    """A dull, pitched thump gliding from f0 down to f1."""
    ph, out = 0.0, []
    for i in range(int(secs * rate)):
        t = i / rate
        ph += TAU * (f1 + (f0 - f1) * math.exp(-t / (tau * 0.35))) / rate
        out.append(math.sin(ph) * math.exp(-t / tau))
    return out


def snag():
    """A starling knocked down by something solid: a dull knock, then a few broken wingbeats as it rights itself."""
    n = int(0.45 * LO)
    out = [0.0] * n
    place(out, level(knock(LO, 290, 150, 0.1, 0.022), 0.2), 0, 1.0, wrap=False)
    hit = lowpass(noise(int(0.012 * LO)), 1500, LO)
    place(out, level([v * (1 - i / len(hit)) for i, v in enumerate(hit)], 0.15), 0, 1.0, wrap=False)
    t = 0.05
    for k in range(5):
        place(out, level(flap(LO, rng.uniform(600, 1100), rng.uniform(14, 24)), 0.14), int(t * LO), 1 - 0.15 * k,
              wrap=False)
        t += rng.uniform(0.04, 0.08)
    save("snag", finish(lowpass(out, 2200, LO), LO, 0.001, 0.3), LO)


def rocket():
    """A firework climbing: a whistle rising over about a second, a hiss of sparks under it."""
    n, rise = int(1.15 * MID), int(1.05 * MID)
    hiss = level(svf(noise(n), 3200, MID, q=0.8), 0.05)
    ph, out = 0.0, []
    for i in range(n):
        u = min(1.0, i / rise)
        ph += TAU * 850 * (2900 / 850) ** (u ** 0.8) * (1 + 0.012 * math.sin(TAU * 11 * i / MID)) / MID
        env = min(1.0, i / (0.06 * MID)) * (1.0 if i < rise else 1 - (i - rise) / (n - rise))
        out.append((0.16 * (math.sin(ph) + 0.15 * math.sin(2 * ph)) + hiss[i] * (0.4 + 0.6 * u)) * env)
    save("rocket", finish(out, MID, 0.005, 0.08), MID)


def burst(k, low, pops, colour, sizzle):
    """A firework bursting close by: a boom, the shell's crack rolling off the roofs, then the stars crackling as they
    fall; sizzle adds a willow's long falling hiss."""
    n = int(1.5 * MID)
    out = [0.0] * n
    place(out, level(knock(MID, low + 110, low, 0.9, 0.2), 0.25), 0, 1.0, wrap=False)
    crack = svf(noise(n), [200 + 3500 * math.exp(-i / (0.02 * MID)) for i in range(n)], MID, q=0.6, band=False)
    roll = [v * min(1, i / (0.002 * MID)) * (0.6 * math.exp(-i / (0.03 * MID)) + 0.4 * math.exp(-i / (0.4 * MID)))
            for i, v in enumerate(crack)]
    place(out, level(roll, 0.1), 0, 1.0, wrap=False)
    for _ in range(pops):
        t = 0.22 + rng.expovariate(1 / 0.35)
        if t < 1.4:
            m = int(rng.uniform(0.002, 0.005) * MID)
            pop = svf(noise(m), colour * rng.uniform(0.7, 1.3), MID, q=1.2)
            place(out, [v * (1 - j / m) for j, v in enumerate(pop)], int(t * MID), rng.uniform(0.5, 1.4) * (1.5 - t),
                  wrap=False)
    if sizzle:
        hiss = svf(noise(n), arch(n, 6000, 4000, 1500, 0.3), MID, q=0.7)
        place(out, level([v * min(1, max(0.0, i / MID - 0.15) / 0.2) * math.exp(-i / (0.6 * MID))
                          for i, v in enumerate(hiss)], sizzle), 0, 1.0, wrap=False)
    save(f"burst{k}", finish(out, MID, 0.0005, 0.25), MID, 0.8)


def thermal():
    """Warm air rising off the roofs or a bonfire: a soft whoosh climbing, and a shimmer like heat haze above it."""
    n = int(1.6 * MID)
    air = level(svf(noise(n), arch(n, 250, 1300, 1700, 0.75), MID, q=0.8), 0.15)
    body = level(svf(noise(n), 300, MID, q=0.7, band=False), 0.06)
    haze = [0.0] * n
    for _ in range(5):
        f, vr, o, ph = rng.uniform(2400, 4800), rng.uniform(6, 11), rng.random() * TAU, 0.0
        for i in range(n):
            ph += TAU * f * (1 + 0.06 * i / n) / MID
            haze[i] += math.sin(ph) * (0.5 + 0.5 * math.sin(TAU * vr * i / MID + o))
    haze = level(haze, 0.03)
    out = []
    for i, (a, b, h) in enumerate(zip(air, body, haze)):
        u = i / n
        out.append((a + b + h) * min(1.0, u / 0.55) ** 1.5 * (1 - max(0.0, u - 0.55) / 0.45) ** 1.2)
    save("thermal", finish(out, MID, 0.01, 0.25), MID)


def blade(k, f):
    """A turbine blade sweeping past close: a low, soft whoomp of pushed air, nothing sharp to tire the ear."""
    n = int(0.8 * LO)
    env = [math.exp(-((i / LO - 0.3) / (0.09 if i / LO < 0.3 else 0.14)) ** 2) for i in range(n)]
    air = level(svf(noise(n), arch(n, f * 0.8, f * 1.25, f * 0.7, 0.38), LO, q=1.4), 0.2)
    body = level(svf(noise(n), f * 0.6, LO, q=0.7, band=False), 0.12)
    ph, out = 0.0, []
    for i in range(n):
        ph += TAU * f * 0.5 * (1.05 - 0.1 * i / n) / LO
        out.append((air[i] + body[i] + 0.08 * math.sin(ph)) * env[i])
    save(f"blade{k}", finish(lowpass(out, 800, LO), LO, 0.01, 0.2), LO)


def foghorn():
    """A far foghorn in the estuary: a low reed tone on D, falling to A, and the fog throwing it back."""
    n = int(5.2 * LO)
    out = [0.0] * n
    for start, dur, f, g in ((0.0, 1.5, hz(50), 0.8), (1.65, 2.2, hz(45), 1.0)):
        ph, ph2, tone = 0.0, 0.0, []
        for i in range(int(dur * LO)):
            t = i / LO
            w = TAU * f * (1 - 0.03 * math.exp(-t / 0.08)) / LO      # the reed scoops up to pitch
            ph, ph2 = ph + w, ph2 + w * 1.003
            s = sum((math.sin(h * ph) + 0.6 * math.sin(h * ph2)) / h for h in range(1, 12))
            tone.append(s * min(1.0, t / 0.12) * min(1.0, (dur - t) / 0.25))
        place(out, tone, int(start * LO), g, wrap=False)
    dry = svf(out, 700, LO, q=0.7, band=False)
    far, out = lowpass(dry, 400, LO), dry[:]
    for d, g in ((0.55, 0.25), (1.2, 0.12)):
        place(out, far, int(d * LO), g, wrap=False)
    save("foghorn", finish(out, LO, 0.02, 0.25), LO)


def buoy(k, strikes):
    """A bell buoy rolling in the swell: the clapper strikes when it leans, never twice alike. The bell's hum, prime,
    minor third and fifth are A, A, C and E, so it sits in the score's minor colours."""
    n = int(2.4 * LO)
    out = [0.0] * n
    for at, g in strikes:
        a = int(at * LO)
        ring = partials(n - a, LO, [(220, 0.35, 1.8), (440, 1.0, 1.3), (523.6, 0.45, 0.9), (659.3, 0.25, 0.7),
                                    (880, 0.4, 0.5), (1100, 0.15, 0.3), (1320, 0.1, 0.22)])
        place(ring, lowpass(noise(int(0.004 * LO)), 3000, LO), 0, 1.0, wrap=False)      # the clapper's clank
        place(out, ring, a, g, wrap=False)
    save(f"buoy{k}", finish(lowpass(out, 2200, LO), LO, 0.001, 0.3), LO)


def yelp(path, dur, rasp):
    """One gull note: a nasal voice whose pitch follows path(u) over the note, made harsh by rasp."""
    n = int(dur * MID)
    ph, out, r = 0.0, [], rng.random
    for i in range(n):
        u = i / n
        ph += TAU * path(u) / MID
        s = sum(a * math.sin(h * ph) for h, a in ((1, 1.0), (2, 0.8), (3, 0.6), (4, 0.35), (5, 0.2)))
        out.append(s * (1 - rasp + rasp * (2 * r() - 1)) * min(1.0, u / 0.08) * min(1.0, (1 - u) / 0.2))
    return out


def gull(k, notes):
    """A herring gull coming for the flock: notes = [(start, path, seconds, rasp)], through the beak's formant."""
    out = [0.0] * int((max(s + d for s, _, d, _ in notes) + 0.05) * MID)
    for start, path, dur, rasp in notes:
        place(out, yelp(path, dur, rasp), int(start * MID), 1.0, wrap=False)
    voice = [a + 0.4 * b for a, b in zip(svf(out, 1900, MID, q=1.2), out)]
    save(f"gull{k}", finish(lowpass(voice, 6000, MID), MID, 0.002, 0.1), MID)


def bridge():
    """Under a bridge or a sea arch: the air closing in, the vault ringing hollow, the walls throwing it back."""
    n = int(1.8 * LO)
    rush = svf(noise(n), arch(n, 300, 900, 450, 0.3), LO, q=0.9)
    hollow = [x * min(1.0, i / LO / 0.35) ** 1.5 * math.exp(-max(0.0, i / LO - 0.35) / 0.35)
              for i, x in enumerate(rush)]
    d = int(LO / hz(50))                             # a comb tuned to D3: the vault's ring
    for i in range(d, n):
        hollow[i] += 0.7 * hollow[i - d]
    out, back = hollow[:], lowpass(hollow, 1200, LO)
    for t, g in ((0.09, 0.4), (0.19, 0.25), (0.31, 0.14)):
        place(out, back, int(t * LO), g, wrap=False)
    save("bridge", finish(out, LO, 0.005, 0.3), LO)


def swell():
    """Everything opening up: air drawn in like a long breath, a shimmer on D, F# and A rising with it, then release."""
    n, pk = int(3.0 * MID), int(2.2 * MID)
    air = level(svf(noise(n), arch(n, 300, 5000, 2500, 0.73), MID, q=0.7), 0.15)
    glow = [0.0] * n
    for m in (74, 78, 81, 86):
        w, vr, o = TAU * hz(m) / MID, rng.uniform(5, 7), rng.random() * TAU
        for i in range(n):
            glow[i] += math.sin(w * i) * (0.75 + 0.25 * math.sin(TAU * vr * i / MID + o))
    glow = level(glow, 0.06)
    out = [(a + g) * ((i / pk) ** 2 if i < pk else math.exp(-(i - pk) / (0.25 * MID)))
           for i, (a, g) in enumerate(zip(air, glow))]
    save("swell", finish(out, MID, 0.01, 0.15), MID)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for old in glob.glob(os.path.join(OUT, "*.wav")):        # names change between versions: no stale files ship
        os.remove(old)
    wing_bed("wing", 4, 650, 0.6, 1300, (22, 40), ((1, 0.2, 0.3), (2, 0.12, 1.9), (5, 0.06, 0.7)))
    wing_bed("wing_tight", 3, 1100, 0.9, 2200, (14, 26), ((2, 0.2, 0.0), (3, 0.12, 1.0), (7, 0.08, 2.0)))
    chatter()
    wind()
    night()
    rain()
    for name, notes in CHORDS.items():
        save("pad_" + name, pad(notes), LO, 0.5)
        save("choir_" + name, choir(notes), LO, 0.5)
    for name, m in ROOTS.items():
        save("bass_" + name, bass(m), LO, 0.5)
    for m in NOTES:
        save(f"pluck_{m}", pluck(m), MID)
        save(f"bell_{m}", bell(m), MID)
        save(f"mari_{m}", marimba(m), MID)
    calls()
    liftoff()
    gust("gust", MID, 1.2, 300, 1500, 900)
    gust("scatter", HI, 0.5, 600, 1500, 800, flaps=2)
    ripple()
    cry()
    stoop()
    miss()
    catch()
    sparkle()
    thunder()
    pulse()
    heron()
    shaker()
    tick()
    bang()
    burner()
    # 1.0: everything below comes after 0.3.0's sounds, so the shared seed leaves those unchanged
    surf()
    for name, notes in NEW_CHORDS.items():
        save("pad_" + name, pad(notes), LO, 0.5)
        save("choir_" + name, choir(notes), LO, 0.5)
    for m in NOTES:
        save(f"cel_{m}", celesta(m), MID)
    snag()
    rocket()
    burst(1, 42, 160, 3200, 0)                      # deep, a long crackle
    burst(2, 62, 70, 5200, 0)                       # higher and brighter, shorter
    burst(3, 50, 25, 2600, 0.05)                    # a willow: soft crackle, a long falling hiss
    thermal()
    for k, f in enumerate((130, 155, 180), 1):
        blade(k, f)
    foghorn()
    buoy(1, ((0.0, 1.0), (0.55, 0.6)))
    buoy(2, ((0.0, 0.7), (0.3, 1.0), (1.05, 0.45)))
    gull(1, ((0.0, lambda u: 750 + 3300 * u if u < 0.15 else 1250 - 550 * ((u - 0.15) / 0.85) ** 1.6, 0.5, 0.15),
             (0.62, lambda u: 900 + 250 * math.sin(math.pi * u) - 150 * u, 0.28, 0.2)))      # kee-ow, kyow
    gull(2, [(0.16 * j, lambda u: 950 + 150 * math.sin(math.pi * u) - 100 * u, 0.1, 0.35) for j in range(4)])  # ha-ha
    bridge()
    swell()
    total = sum(s for _, s in written)
    print(f"wrote {len(written)} sounds, {total / 1e6:.2f} MB")
