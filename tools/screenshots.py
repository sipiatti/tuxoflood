#!/usr/bin/env python3
"""Render screenshots of every screen headlessly (SDL dummy driver).

    python3 tools/screenshots.py [OUTPUT_DIR]      (default: ./screenshots)
"""
import os
import sys
import tempfile
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["TUXOFLOOD_DATA_DIR"] = tempfile.mkdtemp(prefix="tuxoflood-shots-")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from tuxoflood import app as A  # noqa: E402
from tuxoflood.i18n import set_lang  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
OUT.mkdir(parents=True, exist_ok=True)
app = A.App(headless=True, audio=False)


def run(seconds, events=()):
    events = list(events)
    steps = max(1, int(seconds * 60))
    for i in range(steps):
        app.step(1 / 60, events if i == 0 else ())


def shot(name):
    pygame.image.save(app.screen, str(OUT / f"{name}.png"))
    print("saved", name)


def motion(pos):
    return [pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))]


def cell_center(play, i):
    n = play.level.board.size
    r, c = divmod(i, n)
    return (play.board_rect.x + c * play.cell + play.cell // 2, play.board_rect.y + r * play.cell + play.cell // 2)


# some progress so the menu / level select look lived-in
st = app.store
st.data["unlocked"] = 9
for n, (score, stars) in enumerate([(320, 3), (410, 3), (560, 2), (700, 3), (820, 1), (990, 2), (1180, 3), (1300, 2)], 1):
    st.data["levels"][str(n)] = {"best": score, "stars": stars, "moves": 10, "wins": 1}

app.goto(A.MenuScene(app))
run(2.6)
shot("01_menu")
menu = app.scene
menu.ask_new_game()
run(0.8)
shot("19_new_game_confirm")
menu.cancel_new_game()
# keyboard focus on "New game"
run(0.3, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="")] * 2)
shot("20_menu_keyboard_focus")
app.goto(A.LevelSelectScene(app))
run(0.4, motion((10, 10)))
shot("02_levels")

# small level, mid-game, hovering a colour button (assist off: only the button is highlighted)
play = A.PlayScene(app, 3, seed=7, sync=True)
app.goto(play)
run(0.3)
for c in play.level.solution[:4]:
    play.pick(c)
    run(0.9)
lv = play.level
nxt = play.level.solution[4] if len(play.level.solution) > 4 else 0
rect = [r for r, i in play.palette_btns if i == nxt][0]
run(0.3, motion(rect.center))
shot("03_small_level_hover")

# large 16-colour level mid-wave
play = A.PlayScene(app, 23, seed=3, sync=True)
app.goto(play)
run(0.3)
for c in play.level.solution[:30]:
    play.pick(c)
    run(0.05)
run(0.25)
shot("04_large_16_colours_wave")
run(1.2, motion((10, 10)))
shot("05_large_16_colours")

# colour-blind mode
app.store.settings["colorblind"] = True
play = A.PlayScene(app, 16, seed=5, sync=True)
app.goto(play)
run(0.3)
for c in play.level.solution[:8]:
    play.pick(c)
    run(0.5)
run(0.8, motion((10, 10)))
shot("06_colorblind")
app.store.settings["colorblind"] = False

# few moves left warning
play = A.PlayScene(app, 7, seed=11, sync=True)
app.goto(play)
run(0.2)
lv = play.level
lv.moves = lv.limit - 3
play.pick(play.level.solution[0])
run(0.5)
shot("07_few_moves_warning")
# out of moves
while not lv.over:
    c = (lv.board.color + 1) % lv.board.colors
    play.pick(c)
    run(0.1)
run(3.0)
shot("08_out_of_moves")

# level complete
play = A.PlayScene(app, 5, seed=2, sync=True)
app.goto(play)
run(0.2)
for c in play.level.solution:
    play.pick(c)
    run(0.15)
run(3.2)
shot("09_level_complete")

play = A.PlayScene(app, 4, seed=1, sync=True)
app.goto(play)
run(0.3)
play.pause()
run(0.4)
shot("10_pause")

app.goto(A.SettingsScene(app, A.MenuScene(app)))
run(0.6)
shot("11_settings")
app.goto(A.HelpScene(app, A.MenuScene(app)))
run(2.0)
shot("12_help")
app.goto(A.StatsScene(app, A.MenuScene(app)))
run(0.6)
shot("13_stats")

# optional assist: preview on the board, and the win screen without stars / par bonus
app.store.settings["assist"] = True
play = A.PlayScene(app, 3, seed=7, sync=True)
app.goto(play)
run(0.3)
for c in play.level.solution[:4]:
    play.pick(c)
    run(0.9)
nxt = play.level.solution[4]
rect = [r for r, i in play.palette_btns if i == nxt][0]
run(0.3, motion(rect.center))
shot("16_assist_preview")
for c in play.level.solution[4:]:
    play.pick(c)
    run(0.15)
run(3.2)
shot("17_assist_win")
app.goto(A.SettingsScene(app, A.MenuScene(app)))
run(0.6)
shot("18_settings_assist_on")
app.store.settings["assist"] = False

app.store.settings["lang"] = "en"
set_lang("en")
play = A.PlayScene(app, 12, seed=9, sync=True)
app.goto(play)
run(0.3)
for c in play.level.solution[:10]:
    play.pick(c)
    run(0.4)
run(1.0)
shot("14_game_english")
app.goto(A.HelpScene(app, A.MenuScene(app)))
run(0.6)
shot("15_help_english")
menu = A.MenuScene(app)
app.goto(menu)
run(0.5)
menu.ask_new_game()
run(0.8)
shot("21_new_game_confirm_english")
set_lang("hu")
app.store.settings["lang"] = "hu"
saved = (app.store.data["unlocked"], app.store.data["levels"])
app.store.data["unlocked"], app.store.data["levels"] = 1, {}
app.goto(A.MenuScene(app))
run(1.0)
shot("22_menu_fresh_save")
app.store.data["unlocked"], app.store.data["levels"] = saved
print("ok")
