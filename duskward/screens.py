"""The words around the flying: the title, the journey south, an evening's summary, the pause and the ending.
Every function takes the Painter (p) and draws with it.
"""

import math

import pygame

from .evening import CARRY_MAX, ROOST_FLOCK
from .places import NAMES, PLACES, WORDS
from .render import dim, mix, soften
from .settings import AMBER, CREAM, GLINT, H, LAND

ADD = pygame.BLEND_RGB_ADD
ROOSTED = {"reeds": "You roosted in the reeds.", "trees": "You roosted in the wood.",
           "bridge": "You roosted on the girders, under the bridge.", "pier": "You roosted under the pier."}
FATE = {"falcon": "taken by the falcon over {}", "behind": "stayed behind at {}", "cold": "lost to the cold at {}"}
SHORT = {"falcon": "the falcon", "behind": "left behind", "cold": "the cold"}


def at(k):
    """A place's name inside a sentence."""
    name = PLACES[k].name
    return "the" + name[3:] if name.startswith("The ") else name


def shade(p, screen, alpha):
    p.shade.fill((*LAND, alpha))
    screen.blit(p.shade, (0, 0))


def feather(p, screen, x, y, filled, k=1.0):
    """A feather for the rating: earned ones gold, the rest an outline. k scales it."""
    ca, sa = math.cos(-0.45), math.sin(-0.45)
    side = [(u / 12, math.sin(math.pi * u / 12) ** 0.8 * 8) for u in range(13)]
    pts = [(-wd, 22 - 44 * u) for u, wd in side] + [(wd, 22 - 44 * u) for u, wd in reversed(side)]
    poly = [(x + (px * ca - py * sa) * k, y + (px * sa + py * ca) * k) for px, py in pts]
    faint = mix(CREAM, p.cols[0], 0.5)
    if filled:
        pygame.draw.polygon(screen, GLINT, poly)
    else:
        pygame.draw.polygon(screen, faint, poly, 2 if k == 1 else 1)
    pygame.draw.line(screen, mix(GLINT, LAND, 0.3) if filled else faint,
                     (x - 30 * sa * k, y + 30 * ca * k), (x + 22 * sa * k, y - 22 * ca * k), 2 if k == 1 else 1)


def title(p, screen, ev, deco, t):
    p.draw(screen, ev, 0.0, t, hud=False)
    p.birds(screen, deco, 0.0)
    if p.title_glow is None:
        s = p.fonts["title"].render("Duskward", True, AMBER)
        sw, sh = s.get_size()
        pad = pygame.Surface((sw + 120, sh + 120))
        pad.blit(s, (60, 60))
        p.title_glow = dim(soften(soften(pad, ((sw + 120) // 10, (sh + 120) // 10)), (sw + 120, sh + 120)), 150)
    screen.blit(p.title_glow, (72 - 60, 70 - 60), special_flags=ADD)
    p.write(screen, "Duskward", "title", (72, 70))
    p.write(screen, "You are the whole flock.", "big", (78, 228))
    if int(t * 1.6) % 2 == 0 or t < 1:
        p.write(screen, "Click or press Space to fly", "text", (78, 290), AMBER)
    p.write(screen, "Point to steer.  Hold to gather.  Tap to ripple.", "small", (78, H - 76), alpha=220)
    p.write(screen, "Keys: arrows to steer, Space to gather or ripple.  F11 full screen.  M sound.  Esc pause.",
            "small", (78, H - 46), alpha=170)


def stops(w):
    """Where the eight evenings stand on the journey's line."""
    return [(150 + k * (w - 300) / 7, 214 + 22 * math.sin(k * 0.9) + k * 5) for k in range(8)]


def journey(p, screen, ev, jn, pick, t, sure=False):
    """The journey south: the evenings flown and the one ahead, the place picked, and the eight."""
    p.draw(screen, ev, 0.0, t, hud=False)
    shade(p, screen, 175)
    w, done = p.w, jn.next
    faint = mix(CREAM, p.cols[0], 0.55)
    p.write(screen, "The journey south", "head", (96, 44))
    info = f"feathers  {jn.feathers()} of 24        the great flock  {jn.great(done)}"
    p.write(screen, info, "text", (w - 96 - p.text(info, "text", CREAM).get_width(), 70), alpha=220)
    pts = stops(w)
    pygame.draw.aalines(screen, faint, False, pts)
    if done:
        pygame.draw.lines(screen, CREAM, False, pts[:min(8, done + 1)], 2)
    for k, (x, y) in enumerate(pts):
        up = k % 2 == 0
        if k == pick:
            screen.blit(p.faded("pick", p.dot_big, 0.8 + 0.2 * math.sin(t * 5)), (x - 30, y - 30), special_flags=ADD)
        if k < done:
            pygame.draw.circle(screen, CREAM, (x, y), 7)
            for j, got in enumerate(jn.nights[k]["feathers"]):
                feather(p, screen, x - 14 + j * 14, y - 64 if up else y + 64, got, 0.4)
        else:
            pygame.draw.circle(screen, AMBER if k == done else faint, (x, y), 8 if k == done else 6, 2 if k == done else 1)
        p.write(screen, PLACES[k].name, "small", (x, y - 44 if up else y + 20), CREAM if k <= done else faint, centre=True)
    pl, y = PLACES[pick], 356
    p.write(screen, "Evening " + WORDS[pick], "text", (96, y), AMBER)
    p.write(screen, pl.name, "head", (96, y + 26))
    for j, line in enumerate(pl.story):
        p.write(screen, line, "text", (96, y + 102 + j * 32))
    eight, commons = jn.carry(pick)
    who = "all eight" if len(eight) == 8 else (f"{WORDS[len(eight) - 1]} of the eight" if eight else "none of the eight")
    with_them = f", and {min(CARRY_MAX, commons)} of last night's flock" if commons else ""
    p.write(screen, f"Setting out: {who}{with_them}.", "text", (96, y + 176), alpha=200)
    if int(t * 1.6) % 2 == 0 or t < 1:
        again = ("" if pick == done else "  It is flown again from the same dusk." if pick == done - 1
                 else "  Flown again, only its feathers can change.")
        p.write(screen, "Click or press Space to fly." + again, "text", (96, y + 216), AMBER)
    fates = jn.fates()
    for e in range(1, 9):                                       # the eight, and who is still flying
        x, yy = 96 + (e - 1) * (w - 192) / 8, H - 104
        if e in fates:
            pygame.draw.circle(screen, faint, (x + 6, yy + 14), 5, 1)
            p.write(screen, NAMES[e - 1], "text", (x + 22, yy), faint)
            p.write(screen, SHORT[fates[e][1]], "small", (x + 22, yy + 28), faint)
        else:
            screen.blit(p.halo, (x + 6 - 11, yy + 14 - 11), special_flags=ADD)
            pygame.draw.circle(screen, GLINT, (x + 6, yy + 14), 5)
            p.write(screen, NAMES[e - 1], "text", (x + 22, yy), GLINT)
    if sure:
        p.write(screen, "Press N again to begin a new journey: this one will be forgotten.", "small", (96, H - 40), AMBER)
    else:
        p.write(screen, "Left, right or the pointer: choose an evening.     N: a new journey.     Esc: the title.",
                "small", (96, H - 40), alpha=170)


def summary(p, screen, ev, jn=None):
    """How the evening went. jn: the journey, once the night is written in it."""
    shade(p, screen, 160)
    s, x, pl = ev.stats, 96, ev.place
    how = {"roost": ROOSTED[pl.kind], "night": "Night caught the flock in the open.", "lost": "The flock is gone."}[ev.result]
    hw, _ = p.write(screen, pl.name, "head", (x, 90))
    for k, got in enumerate(ev.feathers()):
        feather(p, screen, x + hw + 60 + k * 44, 122, got)
    p.write(screen, f"roost  ·  none of the eight lost  ·  {pl.home} home", "small", (x + hw + 196, 110), alpha=170)
    p.write(screen, how, "big", (x, 168))
    p.write(screen, f"{s['start']}  to  {len(ev.flock)} starlings", "count", (x, 228), GLINT)
    gone = ", ".join(f"{NAMES[e - 1]} ({SHORT[f]})" for e, f in sorted(ev.fates.items()))
    lines = [f"The eight: {ev.eight_in_flock} of {len(ev.eight_start)} with you" + (f".  {gone}" if gone else ""),
             f"Strays who joined you: {s['strays']}"]
    if s["midges"]:
        lines.append(f"Midge swarms eaten: {s['midges']}")
    if s["mark_total"]:
        lines.append(f"Trails followed: {s['marks']} of {s['mark_total']} marks, and {s['guided']} came with you")
    if s["scattered"]:
        why = [f"{n} by {what}" for what, n in (("the blades" if ev.turbines else "the wirework", s["snagged"]),
                                                 ("the fog", s["fogged"])) if n]
        lines.append(f"Scattered: {s['scattered']}" + (f" ({', '.join(why)})" if why else "")
                     + (f", {s['regathered']} found again" if s["regathered"] else ""))
    if s["gulls"]:
        lines.append(f"Gulls turned away: {s['gulls']}")
    lines.append(f"Taken by the falcon: {s['caught']}")
    lines.append(f"The {ROOST_FLOCK[pl.kind]}'s dance: {s['dance']:.0%}, and {s['merged']} joined you")
    if s["cold"]:
        lines.append(f"Lost to the cold: {s['cold']}")
    if jn and ev.index < jn.next:
        lines.append(f"The great flock, wherever it sleeps tonight: {jn.great(ev.index + 1)}")
    gap = 38 if len(lines) < 9 else 33
    for k, line in enumerate(lines):
        p.write(screen, line, "text", (x, 306 + k * gap))
    last = ev.index == len(PLACES) - 1
    foot = ("Click or press Space to fly the evening again.     Esc: the journey." if ev.result == "lost"
            else "Click or press Space" + ("." if last else " to fly on.") + "     R: fly this evening again.     Esc: the journey.")
    p.write(screen, foot, "small", (x, 306 + len(lines) * gap + 24), AMBER)


def paused(p, screen):
    shade(p, screen, 140)
    p.write(screen, "Paused", "head", (p.w // 2, H // 2 - 70), centre=True)
    p.write(screen, "Esc to fly on.     R to begin the evening again.     Q for the journey.", "text",
            (p.w // 2, H // 2 + 10), centre=True)


def ending(p, screen, ev, jn, cam, t):
    """The Long Reeds, and the count of the eight."""
    p.draw(screen, ev, cam, t, hud=False)
    shade(p, screen, 150)
    fates, x = jn.fates(), 96
    faint = mix(CREAM, p.cols[0], 0.5)
    home = 8 - len(fates)
    head = {8: "All eight came home.", 0: "None of the eight came home."}.get(
        home, f"{WORDS[home - 1].capitalize()} of the eight came home.")
    p.write(screen, "The Long Reeds, midwinter", "text", (x, 62), AMBER)
    p.write(screen, head, "head", (x, 90))
    for e in range(1, 9):
        y = 186 + (e - 1) * 36
        if e in fates:
            night, how = fates[e]
            pygame.draw.circle(screen, faint, (x + 8, y + 15), 5, 1)
            p.write(screen, NAMES[e - 1], "text", (x + 28, y), faint)
            p.write(screen, FATE[how].format(at(night)), "text", (x + 150, y), faint)
        else:
            screen.blit(p.halo, (x + 8 - 11, y + 15 - 11), special_flags=ADD)
            pygame.draw.circle(screen, GLINT, (x + 8, y + 15), 5)
            p.write(screen, NAMES[e - 1], "text", (x + 28, y), GLINT)
            p.write(screen, "home, in the Long Reeds", "text", (x + 150, y))
    p.write(screen, f"{jn.great(len(jn.nights))} starlings came south with them.", "big", (x, 494))
    for k in range(jn.feathers()):
        feather(p, screen, x + 10 + k * 15, 560, True, 0.4)
    p.write(screen, f"{jn.feathers()} of 24 feathers", "small", (x + 10 + max(1, jn.feathers()) * 15 + 6, 548), alpha=200)
    if t % 1.25 < 0.8:
        p.write(screen, "Click or press Space: the journey. Any evening can be flown again.", "small", (x, H - 60), AMBER)
