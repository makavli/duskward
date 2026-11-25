"""Tuning and palette. Units are pixels and seconds; the view is 720 px tall and its width follows the screen."""

H = 720
W_MIN, W_MAX = 1280, 1720          # 16:9 up to about 21:9; a wider screen gets side bars
MAX_DT = 1 / 30                    # a long hitch never moves the world more than this at once
STEP = 1 / 60                      # the tests and the autopilot step at this rate

# The flock. Each step sums the birds per grid cell once; every bird then reads the 3x3 cells around it.
CELL = 36                          # alignment and cohesion
SEP_CELL = 12                      # personal space
V_MIN, V_MAX, V_GATHER = 70, 190, 290
ALIGN = 1.7
COHERE, COHERE_G = 0.6, 2.6        # cruising, gathered
SEPARATE = 460
ATTRACT, ATTRACT_G, ORBIT = 85, 200, 40
FLOOR_GAP = 22                     # birds keep this far above the ground
RIPPLE_SPEED, RIPPLE_BAND, RIPPLE_PUSH, RIPPLE_REACH = 640, 26, 1500, 560

# The player's means
GATHER_DRAIN = 0.24                # stamina a second while gathered
REST, FEED = 0.09, 0.36            # stamina a second in the air, and low over the fields
LOW_BAND = 140                     # "low over the fields": within this height of the ground
RIPPLE_COST, RIPPLE_COOL = 0.12, 1.0
TAP = 0.18                         # a press shorter than this is a ripple; longer is a gather
JOIN_REACH = 120                   # strays lift off when the flock passes this close

# The evening (each place's own light, falcon and sky are in places.py)
NIGHT_LOSS = 0.25                  # a flock caught in the open at night loses this share to the cold

# Colours
LAND = (18, 16, 30)
INK = (24, 20, 34)                 # a starling against the light
SILVER = (178, 178, 206)           # a starling against the dark, catching the last light
GLINT = (244, 206, 128)            # one of the eight
SUN = (255, 236, 190)
CREAM = (246, 238, 222)
AMBER = (240, 196, 120)
FALCON = (46, 48, 66)
CLOUD = (40, 42, 62)
WINDOW = (255, 196, 120)           # house windows, lit as the light goes
