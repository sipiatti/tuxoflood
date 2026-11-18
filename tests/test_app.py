"""Headless smoke tests of the pygame front end."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from tuxoflood import app as A  # noqa: E402
from tuxoflood.i18n import S, set_lang, tr  # noqa: E402


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("TUXOFLOOD_DATA_DIR", str(tmp_path))
    a = A.App(headless=True, audio=False)
    yield a
    set_lang("hu")       # (pygame is not quit: cached fonts must stay valid between tests)


def run(app, seconds, events=()):
    events = list(events)
    for k in range(max(1, int(seconds * 60))):
        app.step(1 / 60, events if k == 0 else ())


def click(pos):
    return [pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)),
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1)]


def key(k, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=mod, unicode="")


def test_all_strings_have_both_languages():
    for k, pair in S.items():
        assert len(pair) == 2 and all(pair), k


def test_no_time_limit_texts():
    # the design has a move limit only: help must say so, and no "time up" screen exists
    assert "időkorlát nincs" in S["h_limit_t"][0].lower()
    assert "no time limit" in S["h_limit_t"][1].lower()
    assert not any("time_up" in k for k in S)


def test_every_scene_draws(app):
    menu = A.MenuScene(app)
    for scene in (menu, A.LevelSelectScene(app), A.HelpScene(app, menu), A.SettingsScene(app, menu),
                  A.StatsScene(app, menu)):
        app.goto(scene)
        run(app, 0.3)
    for lang in ("en", "hu"):
        set_lang(lang)
        app.goto(A.MenuScene(app))
        run(app, 0.1)


def test_win_through_palette_clicks(app):
    app.start_level(1, seed=3)
    play = app.scene
    assert isinstance(play, A.PlayScene) and play.level is not None
    run(app, 0.2)
    for c in list(play.level.solution):
        rect = [r for r, i in play.palette_btns if i == c][0]
        run(app, 0.05, click(rect.center))
    assert play.level.won and play.finished
    run(app, 3.0)
    assert isinstance(play.overlay, A.ResultOverlay) and play.overlay.won
    assert app.store.unlocked == 2
    assert app.store.level_info(1)["best"] == play.overlay.points["total"] > 0
    # Enter -> next level
    run(app, 0.1, [key(pygame.K_RETURN)])
    assert isinstance(app.scene, A.PlayScene) and app.scene.number == 2


def test_click_on_board_cell_and_keys(app):
    app.start_level(3, seed=5)
    play = app.scene
    lv = play.level
    target = lv.solution[0]
    cell = next(i for i, c in enumerate(lv.board.cells) if c == target)
    n = lv.board.size
    r, c = divmod(cell, n)
    pos = (play.board_rect.x + c * play.cell + play.cell // 2, play.board_rect.y + r * play.cell + play.cell // 2)
    run(app, 0.1, click(pos))
    assert lv.moves == 1 and lv.board.color == target
    # keyboard: colour 1..9 keys
    other = next(k for k in range(lv.board.colors) if k != lv.board.color)
    run(app, 0.1, [key(pygame.K_1 + other)])
    assert lv.moves == 2 and lv.board.color == other
    # same colour again: refused, not counted
    run(app, 0.1, [key(pygame.K_1 + other)])
    assert lv.moves == 2


def test_letter_keys_pick_colours_11_to_16(app):
    app.store.data["unlocked"] = 30
    app.start_level(23, seed=1)
    play = app.scene
    lv = play.level
    for k, idx in ((pygame.K_q, 10), (pygame.K_y, 15), (pygame.K_0, 9)):
        if lv.board.color != idx:
            before = lv.moves
            run(app, 0.05, [key(k)])
            assert lv.moves == before + 1 and lv.board.color == idx


def test_out_of_moves_loses_and_restart_gives_new_board(app):
    app.start_level(1, seed=8)
    play = app.scene
    lv = play.level
    lv.moves = lv.limit - 1
    # pick a colour that does not finish the board
    c = next(k for k in range(lv.board.colors) if k != lv.board.color and not _would_win(lv, k))
    play.pick(c)
    assert lv.lost
    run(app, 3.0)
    assert isinstance(play.overlay, A.ResultOverlay) and not play.overlay.won
    assert app.store.data["stats"]["lost"] == 1 and app.store.unlocked == 1
    old = lv.board.cells
    run(app, 0.1, [key(pygame.K_RETURN)])      # retry
    nxt = app.scene
    assert isinstance(nxt, A.PlayScene) and nxt is not play and nxt.number == 1
    assert nxt.level.moves == 0 and nxt.level.board.cells != old


def _would_win(lv, k):
    b = lv.board.copy()
    b.flood(k)
    return b.solved()


def _hover_button(app, play, c):
    rect = [r for r, i in play.palette_btns if i == c][0]
    run(app, 0.1, [pygame.event.Event(pygame.MOUSEMOTION, pos=rect.center, rel=(0, 0), buttons=(0, 0, 0))])
    return rect


def test_no_preview_by_default(app):
    assert app.store.settings["assist"] is False
    app.start_level(1, seed=2)
    play = app.scene
    lv = play.level
    c = next(k for k in range(lv.board.colors) if k != lv.board.color and lv.board.gain(k))
    _hover_button(app, play, c)
    assert play.hover_color == c          # the button itself is highlighted ...
    assert play.preview == []             # ... but nothing is marked on the board
    # hovering a board cell does not mark anything either
    cell = next(i for i, k in enumerate(lv.board.cells) if k == c)
    n = lv.board.size
    r, col = divmod(cell, n)
    pos = (play.board_rect.x + col * play.cell + 2, play.board_rect.y + r * play.cell + 2)
    run(app, 0.1, [pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))])
    assert play.preview == [] and not play.assist_used
    # nothing of the preview is drawn: the board pixels are identical with and without hovering
    run(app, 0.5)
    area = play.board_rect.copy()
    area.top += 60                         # skip the bobbing penguin on the start corner
    area.h -= 60
    before = pygame.image.tostring(app.screen.subsurface(area), "RGB")
    _hover_button(app, play, c)
    run(app, 0.05)
    after = pygame.image.tostring(app.screen.subsurface(area), "RGB")
    assert before == after


def test_assist_shows_preview_and_costs_stars(app):
    app.store.settings["assist"] = True
    app.start_level(1, seed=2)
    play = app.scene
    lv = play.level
    c = next(k for k in range(lv.board.colors) if k != lv.board.color and lv.board.gain(k))
    _hover_button(app, play, c)
    assert set(play.preview) == set(lv.board.gain(c)) and play.assist_used
    for k in lv.solution:
        play.pick(k)
    run(app, 3.0)
    ov = play.overlay
    assert ov.won and ov.stars == 0 and ov.points["par"] == 0
    info = app.store.level_info(1)
    assert info["stars"] == 0 and app.store.unlocked == 2
    assert app.store.data["stats"]["par_or_better"] == 0
    assert app.store.data["highscores"][0].get("assist") is True


def test_assist_switched_on_mid_board_still_counts(app):
    app.start_level(1, seed=5)
    play = app.scene
    run(app, 0.1)
    assert not play.assist_used
    s = A.SettingsScene(app, play)
    s._flip("assist")
    app.goto(play)
    run(app, 0.1)
    s._flip("assist")                      # switching it off again does not undo it
    run(app, 0.1)
    assert play.assist_used


def test_colorblind_toggle(app):
    app.start_level(1, seed=2)
    assert app.store.settings["colorblind"] is False
    run(app, 0.1, [key(pygame.K_c)])
    assert app.store.settings["colorblind"] is True
    run(app, 0.2)


def test_pause_and_menu_records_loss(app):
    app.start_level(1, seed=4)
    play = app.scene
    play.pick(next(k for k in range(play.level.board.colors) if k != play.level.board.color))
    run(app, 0.1, [key(pygame.K_p)])
    assert isinstance(play.overlay, A.PauseOverlay)
    moves = play.level.moves
    run(app, 0.1, [key(pygame.K_1)])           # no moves while paused
    assert play.level.moves == moves
    play.overlay.to_menu()
    assert isinstance(app.scene, A.MenuScene)
    assert app.store.data["stats"]["lost"] == 1


def test_elapsed_time_is_only_a_stat(app):
    app.start_level(1, seed=6)
    play = app.scene
    run(app, 5.0)
    assert play.elapsed > 4.5
    assert not play.level.over                   # time alone never ends a level
    for c in play.level.solution:
        play.pick(c)
    run(app, 3.0)
    assert play.overlay.points["total"] > 0


def test_locked_level_cannot_be_started(app):
    app.start_level(7)
    assert app.scene.number == 1


def test_background_generation(app):
    app.sync_levels = False
    app.store.data["unlocked"] = 23
    app.start_level(23)
    play = app.scene
    for _ in range(600):
        run(app, 1 / 60)
        if play.level is not None:
            break
    assert play.level is not None and play.level.board.size == 26 and play.level.board.colors == 16


def test_language_switch(app):
    menu = A.MenuScene(app)
    s = A.SettingsScene(app, menu)
    app.goto(s)
    s._lang()
    assert app.store.settings["lang"] == "en" and tr("levels") == "Levels"
    s._lang()
    assert tr("levels") == "Szintek"


def test_settings_toggles(app):
    s = A.SettingsScene(app, A.MenuScene(app))
    app.goto(s)
    for k, default in (("colorblind", False), ("assist", False), ("animations", True)):
        s._flip(k)
        assert app.store.settings[k] is (not default)
    run(app, 0.2)


def test_main_version(capsys):
    with pytest.raises(SystemExit):
        A.main(["--version"])
    assert "TuxoFlood 0.1.0" in capsys.readouterr().out


# ------------------------------------------------------------------ new game from level 1
def _progress(app):
    st = app.store
    st.record_win(1, 300, 5, 8, 5, 3, 12.0, 36)
    st.record_win(2, 400, 7, 10, 6, 2, 20.0, 49)
    st.record_loss(9, 30.0, 40)
    return st


def _labels(scene):
    return [b.label for b in scene.menu_buttons]


def test_fresh_save_shows_single_new_game(app):
    app.goto(A.MenuScene(app))
    labels = _labels(app.scene)
    assert labels[0] == tr("new_game_fresh")
    assert tr("new_game") not in labels and not any(l.startswith("Folytatás") for l in labels)
    run(app, 0.1, [key(pygame.K_RETURN)])
    assert isinstance(app.scene, A.PlayScene) and app.scene.number == 1


def test_menu_with_progress_has_continue_and_new_game(app):
    _progress(app)
    app.goto(A.MenuScene(app))
    labels = _labels(app.scene)
    assert labels[0] == tr("continue_level", n=3) and labels[1] == tr("new_game")
    # every menu button sits inside the window and they do not overlap
    rects = [b.rect for b in app.scene.menu_buttons]
    assert all(app.screen.get_rect().contains(r) for r in rects)
    assert all(not a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:])
    # Enter without moving the focus still continues from the next level
    run(app, 0.1, [key(pygame.K_RETURN)])
    assert isinstance(app.scene, A.PlayScene) and app.scene.number == 3


def test_new_game_cancel_keeps_progress(app):
    st = _progress(app)
    before = (st.unlocked, dict(st.data["levels"]), dict(st.data["stats"]))
    menu = A.MenuScene(app)
    app.goto(menu)
    run(app, 0.1, click(menu.menu_buttons[1].rect.center))
    assert menu.confirm is not None
    run(app, 0.3)
    run(app, 0.1, click(menu.confirm.cancel_btn.rect.center))
    assert menu.confirm is None and app.scene is menu
    # Escape cancels too, and Enter on the default focus (Cancel) does not reset
    menu.ask_new_game()
    run(app, 0.1, [key(pygame.K_ESCAPE)])
    assert menu.confirm is None and app.running
    menu.ask_new_game()
    run(app, 0.1, [key(pygame.K_RETURN)])
    assert menu.confirm is None and app.scene is menu
    assert (st.unlocked, st.data["levels"], st.data["stats"]) == before
    # while the dialog is open the menu behind it does not react
    menu.ask_new_game()
    run(app, 0.1, click(menu.menu_buttons[0].rect.center))
    assert app.scene is menu and menu.confirm is not None


def test_new_game_confirm_resets_campaign_keeps_stats(app, tmp_path):
    st = _progress(app)
    stats = dict(st.data["stats"])
    tops = list(st.data["highscores"])
    st.settings["colorblind"] = True
    menu = A.MenuScene(app)
    app.goto(menu)
    # keyboard: Down to "New game", Enter opens the dialog, Left to "Yes", Enter confirms
    run(app, 0.05, [key(pygame.K_DOWN), key(pygame.K_DOWN)])
    assert menu.nav.focus == 1 and menu.menu_buttons[1].hover
    run(app, 0.05, [key(pygame.K_RETURN)])
    assert menu.confirm is not None and menu.confirm.nav.default == 1
    run(app, 0.3)
    run(app, 0.05, [key(pygame.K_LEFT), key(pygame.K_RETURN)])
    assert isinstance(app.scene, A.PlayScene) and app.scene.number == 1
    assert st.unlocked == 1 and st.data["levels"] == {} and st.total_score() == 0
    assert st.data["stats"] == stats and st.data["highscores"] == tops
    assert st.settings["colorblind"] is True
    assert st.data["campaign_backups"][-1]["unlocked"] == 3
    assert list(tmp_path.glob("progress.json.bak-*"))
    # after the reset the menu offers a single "New game" again
    app.goto(A.MenuScene(app))
    assert _labels(app.scene)[0] == tr("new_game_fresh")


def test_menu_keyboard_navigation_wraps(app):
    _progress(app)
    menu = A.MenuScene(app)
    app.goto(menu)
    n = len(menu.menu_buttons)
    assert n == 6
    run(app, 0.05, [key(pygame.K_UP)])
    assert menu.nav.focus == n - 1 or menu.nav.focus == 0
    menu.nav.focus = None
    run(app, 0.05, [key(pygame.K_DOWN)])
    assert menu.nav.focus == 0
    run(app, 0.05, [key(pygame.K_TAB, pygame.KMOD_SHIFT)])
    assert menu.nav.focus == n - 1
    run(app, 0.05, [key(pygame.K_TAB)])
    assert menu.nav.focus == 0
    run(app, 0.05, [pygame.event.Event(pygame.MOUSEMOTION, pos=(5, 5), rel=(0, 0), buttons=(0, 0, 0))])
    assert menu.nav.focus is None
    for lang in ("hu", "en"):
        set_lang(lang)
        menu.ask_new_game()
        run(app, 0.1)
        menu.cancel_new_game()


def test_help_text_fits_card(app):
    for lang in ("hu", "en"):
        set_lang(lang)
        h = A.HelpScene(app, A.MenuScene(app))
        app.goto(h)
        run(app, 0.1)
        assert h.text_bottom <= 612, (lang, h.text_bottom)
