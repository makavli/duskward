"""The eight evenings south: each place's route, weather, dangers, light and words. Data only: evening.py builds the
world from it, setpieces.py runs what moves, render.py and scenery.py paint it.

Distances are world pixels along the route; heights are pixels above the ground unless a comment says otherwise.
"""

from types import SimpleNamespace

NAMES = ("Ash", "Bramble", "Cinder", "Dew", "Ember", "Flint", "Gorse", "Hazel")       # the eight
WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight")

# Skies: progress through the evening, then the sky's top, middle and horizon.
SALT = [(0.00, (70, 92, 138), (222, 150, 118), (250, 212, 150)), (0.30, (54, 66, 116), (204, 112, 104), (244, 170, 108)),
        (0.55, (40, 46, 92), (142, 84, 110), (222, 128, 94)), (0.78, (22, 26, 58), (66, 56, 92), (140, 86, 90)),
        (1.00, (10, 12, 28), (20, 22, 46), (38, 36, 62))]
HOPS = [(0.00, (86, 104, 120), (226, 168, 96), (252, 214, 130)), (0.30, (70, 80, 104), (214, 130, 80), (246, 176, 96)),
        (0.55, (50, 52, 84), (158, 88, 84), (226, 124, 80)), (0.78, (26, 28, 54), (74, 52, 76), (140, 80, 76)),
        (1.00, (10, 12, 26), (20, 20, 40), (40, 34, 54))]
TOWN = [(0.00, (60, 70, 128), (170, 110, 140), (240, 160, 120)), (0.30, (44, 48, 104), (128, 78, 126), (226, 128, 100)),
        (0.55, (30, 32, 80), (84, 56, 104), (190, 100, 84)), (0.78, (18, 20, 52), (44, 36, 76), (120, 70, 70)),
        (1.00, (8, 10, 26), (18, 18, 42), (46, 34, 52))]
DOWNS = [(0.00, (72, 96, 112), (150, 160, 150), (246, 214, 140)), (0.30, (56, 74, 94), (130, 128, 124), (240, 180, 104)),
         (0.55, (40, 52, 74), (96, 88, 100), (214, 136, 84)), (0.78, (22, 30, 48), (52, 50, 70), (128, 88, 76)),
         (1.00, (8, 12, 22), (18, 22, 36), (34, 36, 50))]
PEARL = [(0.00, (150, 160, 178), (214, 196, 190), (244, 224, 200)), (0.30, (120, 128, 154), (196, 168, 170), (236, 200, 178)),
         (0.55, (84, 90, 122), (150, 124, 140), (206, 160, 150)), (0.78, (44, 48, 78), (84, 74, 100), (130, 104, 112)),
         (1.00, (14, 16, 32), (26, 28, 48), (46, 44, 62))]
CITY = [(0.00, (58, 62, 124), (190, 104, 130), (252, 170, 110)), (0.30, (46, 44, 104), (160, 76, 120), (244, 136, 90)),
        (0.55, (32, 30, 82), (104, 54, 104), (214, 110, 80)), (0.78, (20, 20, 56), (56, 38, 80), (150, 84, 70)),
        (1.00, (10, 10, 30), (24, 20, 48), (70, 46, 52))]
CHALK = [(0.00, (58, 120, 150), (164, 196, 180), (252, 220, 160)), (0.30, (44, 92, 134), (190, 150, 140), (250, 184, 124)),
         (0.55, (34, 60, 108), (150, 96, 120), (232, 134, 98)), (0.78, (20, 32, 66), (70, 58, 98), (150, 90, 92)),
         (1.00, (8, 12, 30), (18, 24, 50), (38, 40, 66))]
FROST = [(0.00, (74, 92, 132), (176, 140, 150), (250, 170, 130)), (0.30, (54, 66, 112), (150, 96, 124), (240, 124, 100)),
         (0.55, (36, 44, 88), (100, 66, 108), (204, 96, 90)), (0.78, (20, 26, 58), (52, 46, 86), (120, 74, 90)),
         (1.00, (8, 12, 30), (18, 22, 48), (40, 40, 66))]

# The figures a roost flock dances: x = ax sin(a s + phase), y = ay sin(b s) about the roost, then how many marks
# the echo has, the seconds the flock takes to draw it, and the seconds you have to dance it back.
SHAPES = {
    "eight": (1, 2, 0.0, 300, 130, 24, 7.5, 16.0),          # a lying eight
    "ring": (1, 1, -1.571, 220, 190, 18, 6.0, 12.5),
    "tall": (2, 1, 0.0, 85, 225, 24, 7.5, 16.0),            # a standing eight
    "fish": (1, 2, -0.785, 300, 130, 24, 7.5, 16.0),         # the eight, leaning
}

DEFAULTS = dict(
    wires=((200, 2200),),        # telegraph wires (x0, x1); the flock always wakes on the first
    farms=(), pools=(), squalls=(), winds=(), courses=(), balloon=None, scarers=True,
    hops=(), blocks=(), fireworks=(), thermals=(), turbines=(), fogs=(), haze=0.0, bridges=(), gulls=(), waters=(),
    heights=(), arches=(), stacks=(),
    base=604, roll=1.0, hill=0.0,                  # the ground: its level, how much it rolls, and long hills on top
    tree_gap=(180, 620), stray_gap=(520, 860), strays=(1, 2, 2, 3, 3, 4, 5, 6), midge_gap=((600, 950), (1000, 1700)),
    falcon_from=0.5, falcon_x=0.77, feint=False, pair=False, from_sun=False, circle=1.8,
    light0=0.0, seconds=180,                       # the light the evening starts in, and seconds from golden hour to dark
    remnant=160, dance=("eight",), dance_at=0,     # the roost flock, its figures, and where it dances from the roost
    kind="reeds", perch=0, home=200, snow=False, finale=False, sea=None,
)


def place(**kw):
    p = SimpleNamespace(**{**DEFAULTS, **kw})
    p.reeds = (p.roost - 900, p.roost + 1100)      # the roost's own ground, flat
    p.length = p.roost + 1200
    return p


PLACES = (
    place(name="The Saltmarsh", look="marsh", sky=SALT, roost=22800,
          goal="Reach the reeds before dark.",
          story=("The night of the first frost, a storm off the sea blew the saltmarsh flock apart.",
                 "Eight young starlings wake on a wire, with no elders left to follow."),
          wires=((200, 2600), (6500, 8200), (15500, 17200)), farms=((5200, 5900), (14000, 15200)),
          pools=((0, 3200), (17600, 21800)), squalls=((9000, 11500),),
          winds=((1700, 3300, 250), (4700, 6300, 190), (12300, 13900, 230), (18100, 19700, 205)),
          courses=((3700, 9, 250, 14, 60), (15700, 12, 230, 26, 120)), balloon=(6000, 240, 7), sea=(760, 520),
          falcon_x=17600 / 22800),

    place(name="Hop Gardens", look="weald", sky=HOPS, roost=21800,
          goal="Slip under the wirework, gathered tight.",
          story=("South of the marsh the last hops hang on their wires, and strays shelter in the bines.",
                 "The falcon has followed. It has learned your trick, and stoops twice."),
          wires=((200, 2200), (12000, 13400)), farms=((4800, 5700), (13800, 14700)), pools=((19700, 20800),),
          hops=((2700, 4400), (6500, 8500), (9900, 11300), (15300, 17500)),
          winds=((4600, 6200, 230), (8700, 9800, 200), (17700, 19300, 215)),
          courses=((11500, 10, 250, 18, 80),), roll=1.3, falcon_from=0.3, falcon_x=0.4, feint=True,
          dance=("ring",), home=250),

    place(name="Market Town", look="town", sky=TOWN, roost=20800,
          goal="Spread on the warm air. Gather when the rockets climb.",
          story=("Bonfire night. The town throws fire at the sky until the last child is called indoors.",
                 "The warm air over its roofs will carry a flock that dares to spread."),
          wires=((200, 1900),), blocks=((3200, 9000, 70, 170), (11400, 17600, 80, 200)),
          fireworks=((4000, 8800), (12000, 17200)),
          thermals=((4700, 150), (6500, 150), (8200, 150), (10200, 260), (12600, 150), (14500, 150), (16400, 150)),
          winds=((1400, 2900, 240), (9300, 10900, 170)), courses=((18000, 9, 250, 20, 70),),
          falcon_from=0.62, falcon_x=0.86, light0=0.3, seconds=230, roll=0.6,
          dance=("tall",), kind="trees", perch=64, home=200),

    place(name="The Wind Farm", look="downs", sky=DOWNS, roost=23800,
          goal="Ride the wind under the blades.",
          story=("On the high downs the great blades turn in a rising gale.",
                 "The wind runs between them like a river: ride it, and mind the tips."),
          wires=((200, 2200),), farms=((7000, 7700),), squalls=((13300, 15300),),
          turbines=((3400, 290, 150, 5.0), (4700, 270, 140, 4.4), (6000, 300, 150, 5.4),
                    (9000, 280, 150, 4.6), (10200, 300, 160, 5.2), (11400, 270, 140, 4.2), (12500, 290, 150, 5.0),
                    (16300, 300, 160, 4.4), (17500, 280, 150, 5.0), (18700, 300, 150, 4.0), (19900, 290, 160, 4.6)),
          winds=((3000, 6500, 520), (8700, 13000, 525), (16000, 20300, 520), (20600, 22400, 230)),
          courses=((20700, 9, 240, 22, 90),), base=596, roll=0.8, hill=26, tree_gap=(500, 1300),
          falcon_from=0.45, dance=("ring", "eight"), kind="trees", perch=64, home=250),

    place(name="Estuary Fog", look="estuary", sky=PEARL, roost=21300,
          goal="Stay gathered in the fog. Follow the calls.",
          story=("The river meets the sea in fog. A bird that drifts from the flock is alone at once.",
                 "The lost call from the mud. Listen, and bring them in."),
          wires=((200, 2000),), waters=((2700, 4700), (8200, 11400), (14600, 17600)),
          fogs=((3100, 3900), (5600, 6400), (8000, 8900), (10100, 10900), (12700, 13500), (15600, 16500),
                (18200, 18900)), haze=0.3,
          winds=((1300, 2600, 240), (19200, 20300, 215)), courses=((13750, 7, 260, 20, 60),),
          roll=0.35, base=612, tree_gap=None, falcon_from=0.4, strays=(2, 3, 3, 4, 5, 6, 7),
          dance=("fish",), home=210),

    place(name="City of Bridges", look="city", sky=CITY, roost=23300,
          goal="Under the arches, past the gulls.",
          story=("The river runs through the city under its bridges, and starlings sleep on the girders.",
                 "Gulls own the open water. The falcon keeps a ledge on the cathedral."),
          wires=((200, 2000),),
          blocks=((2400, 5300, 110, 250), (7500, 10500, 150, 360), (13100, 16100, 120, 300), (18300, 21000, 150, 380)),
          waters=((5500, 7300), (10700, 12900), (16300, 18100), (21500, 24500)),
          bridges=((5600, 7200, 215), (10800, 12800, 225), (16400, 18000, 215), (22500, 24100, 230)),
          gulls=((5400, 7400), (10600, 13000), (16200, 18200)),
          thermals=((8300, 170), (9700, 170), (14600, 170), (19900, 170)), winds=((1100, 2300, 220),),
          roll=0.3, base=612, tree_gap=None, falcon_from=0.35, falcon_x=0.3, feint=True,
          dance=("tall", "ring"), dance_at=-1250, kind="bridge", perch=190, home=250, strays=(2, 2, 3, 3, 4, 5)),

    place(name="Chalk Cliffs", look="cliffs", sky=CHALK, roost=22800,
          goal="From arch to arch. Two falcons: two ripples.",
          story=("The falcon's own country. Here it hunts with its mate, out of the sun.",
                 "Only the sea arches give shelter. Cross the open water fast."),
          wires=((200, 2100),),
          heights=((0, 372), (2590, 356), (2640, 632), (4300, 632), (6490, 632), (6540, 330), (8290, 352), (8340, 632),
                   (10200, 632), (12300, 632), (14190, 632), (14240, 344), (15990, 360), (16040, 632), (17800, 632),
                   (19700, 632), (25000, 632)),
          arches=((4300, 5900, 318, 470), (10200, 12300, 300, 462), (17800, 19700, 324, 476)),
          stacks=((3300, 150), (9100, 190), (9500, 120), (13100, 170), (16900, 150), (20600, 130)),
          waters=((2640, 6540), (8340, 14240), (16040, 25000)),
          winds=((600, 2300, 250), (6700, 8100, 230), (14400, 15800, 240)), base=612,
          tree_gap=None, falcon_from=0.0, falcon_x=0.1, pair=True, from_sun=True, circle=0.9, feint=True,
          dance=("fish", "eight"), kind="pier", perch=92, home=270, strays=(2, 3, 3, 4, 5, 6)),

    place(name="The Long Reeds", look="reeds", sky=FROST, roost=15800,
          goal="Bring them home.",
          story=("Midwinter. Every flock the storm scattered comes down the frozen river tonight.",
                 "The Long Reeds are close. Fly, and bring them home."),
          wires=((200, 2200),), pools=((2600, 5200), (9200, 14800)), squalls=((5900, 7500),),
          winds=((2400, 3900, 235), (7900, 9400, 210)),
          courses=((3600, 9, 250, 24, 60), (9800, 12, 235, 30, 110)),
          roll=0.5, base=610, falcon_from=0.55, falcon_x=0.66, light0=0.3, seconds=215, remnant=70,
          dance=("ring", "tall", "eight"), home=260, snow=True, finale=True, stray_gap=(420, 700)),
)
