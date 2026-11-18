"""Colours (light pastel theme) and layout constants."""
WIDTH, HEIGHT = 1280, 720
FPS = 60

BG_TOP = (255, 241, 250)
BG_BOTTOM = (222, 240, 255)
TEXT = (72, 58, 112)
TEXT_SOFT = (124, 110, 160)
WHITE = (255, 255, 255)
CARD = (255, 255, 255)
CARD_BORDER = (226, 214, 246)
SHADOW = (190, 170, 220)
WRONG = (255, 92, 120)
GOOD = (52, 170, 110)
HINT_GLOW = (255, 214, 10)

# 16 flood colours: cheerful, light, but clearly distinct from each other.  The
# first six (used on the early levels) are the most different ones.  Each
# colour also has a symbol for colour-blind mode (see app.SYMBOLS).
FLOOD_COLORS = [
    (255, 117, 160),   # 1  pink
    (255, 184, 64),    # 2  orange-yellow
    (92, 184, 255),    # 3  sky blue
    (102, 206, 118),   # 4  green
    (178, 132, 250),   # 5  violet
    (250, 236, 110),   # 6  lemon
    (240, 86, 86),     # 7  red
    (72, 210, 200),    # 8  teal
    (175, 128, 92),    # 9  cocoa
    (86, 110, 226),    # 10 indigo
    (196, 236, 92),    # 11 lime
    (255, 196, 170),   # 12 peach
    (228, 94, 210),    # 13 magenta
    (158, 160, 182),   # 14 slate grey
    (176, 236, 226),   # 15 ice mint
    (228, 200, 255),   # 16 lilac
]
COLOR_KEYS = "1234567890qwerty"     # keyboard shortcut of every colour (11..16 = Q W E R T Y)

SNOW = (250, 252, 255)
BOARD_FRAME = (255, 255, 255)
WARN = (255, 80, 110)

# button colour pairs (face, shadow/edge)
BTN_PINK = ((255, 143, 171), (214, 92, 128))
BTN_BLUE = ((116, 185, 255), (66, 132, 214))
BTN_MINT = ((107, 214, 160), (52, 160, 110))
BTN_YELLOW = ((255, 209, 102), (222, 160, 40))
BTN_PURPLE = ((178, 145, 255), (128, 96, 214))
BTN_ORANGE = ((255, 170, 110), (222, 120, 60))
BTN_GREY = ((214, 206, 232), (170, 158, 200))

TITLE_COLORS = [(255, 112, 150), (255, 160, 70), (240, 190, 30), (80, 200, 120),
                (70, 160, 255), (150, 110, 255), (255, 110, 200)]
CONFETTI = [(255, 112, 150), (255, 190, 70), (110, 214, 160), (100, 180, 255),
            (180, 140, 255), (255, 230, 90), (120, 230, 230)]
