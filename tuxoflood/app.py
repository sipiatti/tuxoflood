"""TuxoFlood pygame application: menu, level select, play, results, stats, help, settings."""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import threading

import pygame

from . import __version__, theme
from .audio import Audio
from .flood import LAST_TABLE_LEVEL, LEVEL_TABLE, Level, level_def, new_level, score_breakdown, solve, stars
from .i18n import set_lang, tr
from .resources import font, icon_path, image
from .storage import Store
from .ui import (Button, IconButton, Particles, Slider, Snow, card, draw_background, ease_out_back, fmt_time, mix,
                 rainbow_title, symbol, symbol_ink, text, wrap)

W, H = theme.WIDTH, theme.HEIGHT
COLOR_KEYS = {getattr(pygame, f"K_{ch}"): i for i, ch in enumerate(theme.COLOR_KEYS)}
COLOR_KEYS.update({getattr(pygame, f"K_KP{d}"): (d - 1) % 10 for d in range(10)})


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def stars_row(surf, center, n, size=34, gap=6, t=None):
    total = 3 * size + 2 * gap
    x = center[0] - total // 2
    for i in range(3):
        s = size
        if t is not None:
            s = int(size * ease_out_back(min(1.0, max(0.0, (t - 0.35 * i) / 0.4)))) if i < n else size
        img = image("icons/star.png" if i < n else "icons/star_empty.png", max(1, s))
        cx = x + i * (size + gap) + size // 2
        surf.blit(img, img.get_rect(center=(cx, center[1])))


# ===================================================================== scenes
class Scene:
    music: str | None = "menu"      # background track for this scene (None = keep current)

    def __init__(self, app: "App"):
        self.app = app
        self.buttons: list[Button] = []
        self.t = 0.0

    def handle(self, event):
        for b in self.buttons:
            if b.handle(event):
                return True
        return False

    def update(self, dt):
        self.t += dt
        for b in self.buttons:
            b.update(dt)
        self.refresh_audio_buttons()

    def draw(self, surf):
        for b in self.buttons:
            b.draw(surf)

    def audio_buttons(self, positions, size=52):
        """Round music / effects / settings (/ help) buttons."""
        app = self.app
        out = [IconButton(positions[0], "icons/music.png", theme.BTN_MINT, app.toggle_music, size, tr("tip_music")),
               IconButton(positions[1], "icons/speaker.png", theme.BTN_BLUE, app.toggle_sfx, size, tr("tip_sfx")),
               IconButton(positions[2], "icons/gear.png", theme.BTN_PURPLE,
                          lambda: app.goto(SettingsScene(app, self)), size, tr("tip_settings"))]
        if len(positions) > 3:
            out.append(IconButton(positions[3], "icons/question.png", theme.BTN_ORANGE,
                                  lambda: app.goto(HelpScene(app, self)), size, tr("tip_help")))
        self.sound_btns = out
        self.buttons += out
        return out

    def refresh_audio_buttons(self):
        btns = getattr(self, "sound_btns", None)
        if not btns:
            return
        a = self.app.audio
        btns[0].icon = "icons/music_off.png" if a.music_muted else "icons/music.png"
        btns[0].colors = theme.BTN_GREY if a.music_muted else theme.BTN_MINT
        btns[1].icon = "icons/speaker_off.png" if a.sfx_muted else "icons/speaker.png"
        btns[1].colors = theme.BTN_GREY if a.sfx_muted else theme.BTN_BLUE

    def on_language(self):
        """Called after a language switch; scenes rebuild their labels."""


class DemoBoard:
    """Small self-playing flood board for the main menu."""

    def __init__(self, size=9, colors=5, seed=4):
        self.size, self.colors = size, colors
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        from .flood import random_board
        self.board = random_board(self.size, self.colors, self.rng)
        self.plan = solve(self.board, 2)
        self.timer = 1.2
        self.flash: dict[int, float] = {}

    def update(self, dt):
        self.timer -= dt
        for k in list(self.flash):
            self.flash[k] -= dt
            if self.flash[k] <= 0:
                del self.flash[k]
        if self.timer <= 0:
            if self.board.solved():
                self.reset()
                return
            c = self.plan.pop(0)
            for i in self.board.flood(c):
                self.flash[i] = 0.35
            self.timer = 0.55 if self.plan else 2.2

    def draw(self, surf, rect, t):
        rect = pygame.Rect(rect)
        card(surf, rect.inflate(20, 20), radius=24)
        cell = rect.w / self.size
        for i, col in enumerate(self.board.cells):
            r, c = divmod(i, self.size)
            base = theme.FLOOD_COLORS[col]
            if i in self.flash:
                base = mix(base, theme.WHITE, self.flash[i] / 0.35 * 0.6)
            pygame.draw.rect(surf, base, (rect.x + c * cell + 1, rect.y + r * cell + 1, cell - 2, cell - 2),
                             border_radius=max(2, int(cell // 4)))
        img = image("penguins/penguin_happy.png", int(cell * 1.9))
        surf.blit(img, img.get_rect(center=(rect.x + cell * 0.4, rect.y + cell * 0.2 + math.sin(t * 3) * 3)))


class MenuNav:
    """Keyboard focus for a column/row of buttons: arrows / Tab move, Enter / Space press the focused one.

    The focused button is shown exactly like a mouse-hovered one; moving the mouse hands control back.
    """

    PREV = (pygame.K_UP, pygame.K_LEFT)
    NEXT = (pygame.K_DOWN, pygame.K_RIGHT)

    def __init__(self, buttons, default: int = 0):
        self.buttons = buttons
        self.default = default
        self.focus: int | None = None

    def _show(self):
        for i, b in enumerate(self.buttons):
            b.hover = i == self.focus

    def move(self, d: int):
        n = len(self.buttons)
        start = self.default if self.focus is None else self.focus
        self.focus = start if self.focus is None and d else (start + d) % n
        if Button.on_hover:
            Button.on_hover()
        self._show()

    def draw(self, surf, t: float = 0.0):
        """Keyboard focus ring (only while the keyboard is in charge)."""
        if self.focus is None:
            return
        b = self.buttons[self.focus]
        r = b.rect.move(0, -int(b._lift)).inflate(14, 14)
        r.h += 6
        pulse = 0.5 + 0.5 * math.sin(t * 6)
        pygame.draw.rect(surf, mix(theme.TEXT, theme.WHITE, 0.15 * pulse), r, width=4, border_radius=b.radius + 7)

    def handle(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.focus = None
            return False
        if event.type != pygame.KEYDOWN:
            return False
        if event.key in self.PREV or (event.key == pygame.K_TAB and event.mod & pygame.KMOD_SHIFT):
            self.move(-1)
            return True
        if event.key in self.NEXT or event.key == pygame.K_TAB:
            self.move(1)
            return True
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            b = self.buttons[self.default if self.focus is None else self.focus]
            if b.action:
                if Button.on_click:
                    Button.on_click()
                b.action()
            return True
        return False


class ConfirmDialog:
    """Modal yes / cancel card drawn on top of a scene. "Cancel" has the keyboard focus by default."""

    def __init__(self, title: str, lines: list[str], on_yes, on_cancel, note: str | None = None):
        self.title, self.lines, self.note = title, lines, note
        self.on_yes, self.on_cancel = on_yes, on_cancel
        self.t = 0.0
        y = 430
        self.yes_btn = Button((W // 2 - 230, y, 210, 58), tr("yes"), theme.BTN_ORANGE, icon="icons/restart.png",
                              action=on_yes)
        self.cancel_btn = Button((W // 2 + 20, y, 210, 58), tr("cancel"), theme.BTN_MINT, action=on_cancel)
        self.buttons = [self.yes_btn, self.cancel_btn]
        self.nav = MenuNav(self.buttons, default=1)
        self.nav.focus = 1          # the safe choice is visibly selected from the start
        self.nav._show()

    def handle(self, event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.on_cancel()
            return True
        if self.nav.handle(event):
            return True
        for b in self.buttons:
            if b.handle(event):
                return True
        return True      # modal: nothing reaches the scene behind

    def update(self, dt):
        self.t += dt
        for b in self.buttons:
            b.update(dt)

    def draw(self, surf):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((70, 50, 110, 150))
        surf.blit(v, (0, 0))
        box = pygame.Rect(W // 2 - 340, 170, 680, 360)
        card(surf, box, radius=30)
        rainbow_title(surf, self.title, 50, (W // 2, 218), self.t, wave=3)
        y = 278
        f = font(24, "bold")
        for line in self.lines:
            for part in wrap(line, f, box.w - 80):
                text(surf, part, 24, theme.TEXT, "bold", center=(W // 2, y))
                y += 32
        if self.note:
            text(surf, self.note, 20, theme.TEXT_SOFT, "bold", center=(W // 2, y + 8))
        for b in self.buttons:
            b.draw(surf)
        self.nav.draw(surf, self.t)


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.demo = DemoBoard()
        self.confirm: ConfirmDialog | None = None
        self.build()

    def build(self):
        app = self.app
        st = app.store
        x, w, h, step = W // 2 - 190, 380, 54, 64
        lvl = st.unlocked
        items = []
        if st.has_progress():
            items.append(Button((0, 0, w, h), tr("continue_level", n=lvl), theme.BTN_PINK,
                                action=lambda: app.start_level(lvl)))
            items.append(Button((0, 0, w, h), tr("new_game"), theme.BTN_ORANGE, icon="icons/restart.png", size=28,
                                action=self.ask_new_game))
        else:
            items.append(Button((0, 0, w, h), tr("new_game_fresh"), theme.BTN_PINK, action=lambda: app.start_level(1)))
        items += [
            Button((0, 0, w, h), tr("levels"), theme.BTN_MINT, icon="icons/palette.png",
                   action=lambda: app.goto(LevelSelectScene(app))),
            Button((0, 0, w, h), tr("howto"), theme.BTN_BLUE, action=lambda: app.goto(HelpScene(app, self))),
            Button((0, 0, w, h), tr("stats"), theme.BTN_YELLOW, icon="icons/star.png",
                   action=lambda: app.goto(StatsScene(app, self))),
            Button((0, 0, w, h), tr("quit"), theme.BTN_PURPLE, action=app.quit),
        ]
        y0 = 300 if len(items) == 5 else 280
        for i, b in enumerate(items):
            b.rect.topleft = (x, y0 + i * (step if len(items) == 6 else 70))
        self.menu_buttons = items
        self.nav = MenuNav(items)
        self.buttons = list(items)
        self.audio_buttons([(W - 166, 46), (W - 106, 46), (W - 46, 46)])

    # ------------------------------------------------------------ new game
    def ask_new_game(self):
        st = self.app.store
        self.confirm = ConfirmDialog(tr("confirm_title"), [tr("confirm_text")], self.do_new_game, self.cancel_new_game,
                                     note=tr("confirm_keep"))
        self.confirm.lines.append(tr("confirm_now", n=st.unlocked, p=st.total_score()))

    def cancel_new_game(self):
        self.confirm = None

    def do_new_game(self):
        self.confirm = None
        self.app.store.reset_campaign()
        self.app.start_level(1)

    def on_language(self):
        self.build()

    def update(self, dt):
        super().update(dt)
        self.demo.update(dt)
        if self.confirm:
            self.confirm.update(dt)

    def draw(self, surf):
        rainbow_title(surf, "TuxoFlood", 118, (W // 2, 130), self.t)
        text(surf, tr("subtitle"), 28, theme.TEXT_SOFT, "bold", center=(W // 2, 222))
        self.demo.draw(surf, (70, 330, 270, 270), self.t)
        # penguin floating on a little wave on the right
        bob = math.sin(self.t * 2.2) * 8
        img = image("penguins/penguin_float.png", 200)
        surf.blit(img, img.get_rect(midbottom=(W - 200, 600 + bob)))
        for k in range(3):
            pts = [(W - 360 + x, 610 + k * 18 + math.sin(self.t * 2 + x / 30 + k) * 5) for x in range(0, 330, 10)]
            pygame.draw.lines(surf, mix(theme.FLOOD_COLORS[2], theme.WHITE, 0.25 + 0.2 * k), False, pts, 6)
        super().draw(surf)
        self.nav.draw(surf, self.t)
        total = self.app.store.total_score()
        if total:
            text(surf, tr("total_score", n=total), 22, theme.TEXT_SOFT, "medium", center=(W // 2, H - 22))
        text(surf, f"v{__version__}", 18, theme.TEXT_SOFT, "medium", midright=(W - 16, H - 20))
        if self.confirm:
            self.confirm.draw(surf)

    def handle(self, event):
        if self.confirm:
            return self.confirm.handle(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.quit()
            return True
        if self.nav.handle(event):
            return True
        return super().handle(event)


class LevelSelectScene(Scene):
    PER_PAGE = 24
    COLS = 6

    def __init__(self, app):
        super().__init__(app)
        self.page = (min(app.store.unlocked, self.max_level()) - 1) // self.PER_PAGE
        self.hover = None
        self.build()

    def max_level(self):
        """Show the whole table, and endless levels up to the highest unlocked one."""
        return max(LAST_TABLE_LEVEL, self.app.store.unlocked)

    def pages(self):
        return max(1, math.ceil(self.max_level() / self.PER_PAGE))

    def build(self):
        self.buttons = [Button((W // 2 - 130, H - 80, 260, 60), tr("back"), theme.BTN_PINK, action=self.leave),
                        IconButton((54, 380), "icons/arrow_left.png", theme.BTN_BLUE, lambda: self.flip(-1), 64),
                        IconButton((W - 54, 380), "icons/arrow_right.png", theme.BTN_BLUE, lambda: self.flip(1), 64)]
        self.audio_buttons([(W - 166, 46), (W - 106, 46), (W - 46, 46)])

    def on_language(self):
        self.build()

    def flip(self, d):
        self.page = (self.page + d) % self.pages()

    def leave(self):
        self.app.goto(MenuScene(self.app))

    def tile_rect(self, idx):
        c, r = idx % self.COLS, idx // self.COLS
        return pygame.Rect(118 + c * 176, 110 + r * 128, 160, 114)

    def tile_at(self, pos):
        start = self.page * self.PER_PAGE
        for k in range(self.PER_PAGE):
            n = start + k + 1
            if n > self.max_level():
                break
            if self.tile_rect(k).collidepoint(pos):
                return n
        return None

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.leave()
                return True
            if event.key in (pygame.K_LEFT, pygame.K_PAGEUP):
                self.flip(-1)
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
                self.flip(1)
                return True
        if event.type == pygame.MOUSEWHEEL:
            self.flip(-1 if event.y > 0 else 1)
            return True
        if event.type == pygame.MOUSEMOTION:
            n = self.tile_at(event.pos)
            if n != self.hover and n is not None and n <= self.app.store.unlocked:
                self.app.audio.play("hover")
            self.hover = n
        if super().handle(event):
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            n = self.tile_at(event.pos)
            if n is not None:
                if n <= self.app.store.unlocked:
                    self.app.audio.play("click")
                    self.app.start_level(n)
                else:
                    self.app.audio.play("denied")
                return True
        return False

    def draw(self, surf):
        rainbow_title(surf, tr("levels_title"), 60, (W // 2, 54), self.t, wave=3)
        st = self.app.store
        start = self.page * self.PER_PAGE
        for k in range(self.PER_PAGE):
            n = start + k + 1
            if n > self.max_level():
                break
            r = self.tile_rect(k)
            ld = level_def(n)
            locked = n > st.unlocked
            info = st.level_info(n)
            hov = self.hover == n and not locked
            if hov:
                r = r.move(0, -3)
            col = theme.FLOOD_COLORS[(n - 1) % 16]
            face = (236, 230, 246) if locked else mix(col, theme.WHITE, 0.55 if not hov else 0.4)
            card(surf, r, color=face, radius=20, border=theme.CARD_BORDER if locked else col, shadow=5)
            if locked:
                surf.blit(image("icons/lock.png", 48), image("icons/lock.png", 48).get_rect(center=(r.centerx, r.y + 44)))
                text(surf, tr("level_short", n=n), 22, theme.TEXT_SOFT, "black", center=(r.centerx, r.bottom - 22))
                continue
            text(surf, tr("level_short", n=n), 40, theme.WHITE, "black", center=(r.centerx, r.y + 34),
                 outline=mix(col, theme.TEXT, 0.45), outline_w=3)
            label = tr("endless") if n > LAST_TABLE_LEVEL else tr("level_info", s=ld.size, c=ld.colors)
            text(surf, label, 18, theme.TEXT, "bold", center=(r.centerx, r.y + 68))
            stars_row(surf, (r.centerx, r.bottom - 22), info.get("stars", 0), 24, 3)
        if self.pages() > 1:
            text(surf, tr("page", a=self.page + 1, b=self.pages()), 24, theme.TEXT_SOFT, "black",
                 center=(W - 54, 440))
        last = LEVEL_TABLE[-1]
        text(surf, tr("endless_info", n=LAST_TABLE_LEVEL, s=last.size, c=last.colors), 19, theme.TEXT_SOFT, "bold",
             center=(W // 2, H - 104))
        super().draw(surf)


# ======================================================================= play
BOARD_AREA = pygame.Rect(34, 86, 616, 616)
PANEL = pygame.Rect(686, 76, 572, 632)
PALETTE_RECT = pygame.Rect(PANEL.x, 286, PANEL.w, 300)
FLOOD_ANIM = 0.22          # seconds for one cell to change colour


class Floater:
    def __init__(self, msg, color, x, y, size=30):
        self.msg, self.color, self.x, self.y, self.size, self.t = msg, color, x, y, size, 0.0


class Generator:
    """Builds a level (board + solver par) on a worker thread so the UI never freezes."""

    def __init__(self, number: int, seed: int | None, sync: bool = False):
        self.result: Level | None = None
        self.error: BaseException | None = None
        if sync:
            self._run(number, seed)
        else:
            self.thread = threading.Thread(target=self._run, args=(number, seed), daemon=True)
            self.thread.start()

    def _run(self, number, seed):
        try:
            self.result = new_level(number, seed)
        except BaseException as e:     # pragma: no cover - surfaced in the UI thread
            self.error = e


class PlayScene(Scene):
    music = "game"

    def __init__(self, app, number: int = 1, seed: int | None = None, sync: bool = False):
        super().__init__(app)
        self.number = number
        self.defn = level_def(number)
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.gen = Generator(number, self.seed, sync)
        self.level: Level | None = None
        self.overlay = None
        self.finished = False
        self.elapsed = 0.0
        self.particles = Particles()
        self.floaters: list[Floater] = []
        self.toast = None
        self.hover_color: int | None = None
        self.mouse = (-100, -100)
        self.preview: list[int] = []
        self._preview_key = None
        self.warned = False
        self.assist_used = False     # the assist was on at some point during this board
        self.mood = ("", 0.0)
        self.finish_delay = None
        self.shake = 0.0
        self.palette_btns: list[tuple[pygame.Rect, int]] = []
        self.build_buttons()
        self._check_ready()

    # ---------------------------------------------------------------- setup
    def build_buttons(self):
        app = self.app
        y = PANEL.bottom - 40
        self.buttons = [
            Button((PANEL.x + 14, y - 30, 196, 58), tr("restart"), theme.BTN_ORANGE, icon="icons/restart.png", size=24,
                   action=self.restart, tooltip=tr("tip_restart")),
            Button((PANEL.x + 222, y - 30, 160, 58), tr("pause"), theme.BTN_PURPLE, icon="icons/pause.png", size=24,
                   action=self.pause),
        ]
        self.cb_btn = IconButton((PANEL.right - 140, y), "icons/eye.png", theme.BTN_BLUE, self.toggle_colorblind, 54,
                                 tr("tip_colorblind"))
        self.buttons.append(self.cb_btn)
        self.buttons.append(IconButton((PANEL.right - 76, y), "icons/question.png", theme.BTN_ORANGE,
                                       lambda: app.goto(HelpScene(app, self)), 54, tr("tip_help")))
        self.audio_buttons([(W - 166, 38), (W - 106, 38), (W - 46, 38)], size=48)

    def on_language(self):
        self.build_buttons()

    def _check_ready(self):
        if self.level is None and self.gen.result is not None:
            self._begin(self.gen.result)

    def _begin(self, level: Level):
        self.level = level
        b = level.board
        self.cell = BOARD_AREA.w // b.size
        px = self.cell * b.size
        self.board_rect = pygame.Rect(0, 0, px, px)
        self.board_rect.center = BOARD_AREA.center
        n = len(b.cells)
        self.shown = list(b.cells)                # colour each cell is drawn with (animated)
        self.anim_from = list(b.cells)
        self.anim_start: list[float | None] = [None] * n
        self.anim_end = 0.0
        self.anim_cells: list[int] = []
        self.dirty = True
        self.board_surf = pygame.Surface(self.board_rect.size, pygame.SRCALPHA)
        self._layout_palette()
        self.app.audio.play("start")

    def _layout_palette(self):
        k = self.level.board.colors
        cols = k if k <= 6 else math.ceil(k / 2)
        rows = 1 if k <= 6 else 2
        gap = 10
        size = min(84, (PALETTE_RECT.w - 40 - gap * (cols - 1)) // cols)
        total_w = cols * size + gap * (cols - 1)
        total_h = rows * size + gap * (rows - 1)
        x0 = PALETTE_RECT.centerx - total_w // 2
        y0 = PALETTE_RECT.y + 50 + (PALETTE_RECT.h - 60 - total_h) // 2
        self.palette_btns = []
        for i in range(k):
            r, c = divmod(i, cols)
            self.palette_btns.append((pygame.Rect(x0 + c * (size + gap), y0 + r * (size + gap), size, size), i))

    # --------------------------------------------------------------- actions
    @property
    def assist_on(self) -> bool:
        return bool(self.app.store.settings.get("assist", False))

    @property
    def colorblind(self) -> bool:
        return bool(self.app.store.settings.get("colorblind"))

    def toggle_colorblind(self):
        s = self.app.store.settings
        s["colorblind"] = not s.get("colorblind", False)
        self.app.store.save()
        self.dirty = True

    def restart(self):
        """New board on the same level (a board in progress counts as lost if moves were made)."""
        if self.level is not None and not self.finished and self.level.moves > 0:
            self.app.store.record_loss(self.level.moves, self.elapsed, len(self.level.board.region))
        self.finished = True
        self.app.start_level(self.number)

    def pause(self):
        if self.overlay is None and not self.finished:
            self.overlay = PauseOverlay(self.app, self)

    def cell_at(self, pos) -> int | None:
        if self.level is None or not self.board_rect.collidepoint(pos):
            return None
        c = (pos[0] - self.board_rect.x) // self.cell
        r = (pos[1] - self.board_rect.y) // self.cell
        n = self.level.board.size
        if 0 <= r < n and 0 <= c < n:
            return r * n + c
        return None

    def palette_at(self, pos) -> int | None:
        for rect, i in self.palette_btns:
            if rect.collidepoint(pos):
                return i
        return None

    def pick(self, color: int) -> bool:
        """Play a colour (from a button, a board cell or a key). Returns True if a move was made."""
        lv = self.level
        if lv is None or self.finished or self.overlay is not None:
            return False
        if color >= lv.board.colors:
            return False
        old_cells = list(lv.board.cells)
        before_colors = lv.board.colors_left()
        gained = lv.play(color)
        if gained is None:
            self.app.audio.play("denied")
            self.shake = 0.25
            return False
        self._start_wave(old_cells)
        n = len(gained)
        after_colors = lv.board.colors_left()
        big = max(6, len(lv.board.cells) // 25)
        a = self.app.audio
        if before_colors - after_colors - {color} and not lv.won:
            a.play("combo")
            self.say(tr("colour_gone"), theme.GOOD)
        if n >= big * 2:
            a.play("splash")
            self._float(tr("great") + f" +{n}", (255, 140, 60), 36)
            self.mood = ("_happy", 1.4)
        elif n >= big:
            a.play("splash", 0.8)
            self._float(tr("nice") + f" +{n}", theme.GOOD, 32)
            self.mood = ("_happy", 1.0)
        else:
            a.play("flood")
            if n:
                self._float(f"+{n}", theme.TEXT, 26)
        if lv.won:
            self.finished = True
            self.finish_delay = max(0.4, self.anim_end - self.t + 0.35)
        elif lv.lost:
            self.finished = True
            self.finish_delay = max(0.5, self.anim_end - self.t + 0.4)
            self.mood = ("_sad", 99)
        elif lv.warning():
            a.play("warning", 1.0 if not self.warned else 0.55)
            if not self.warned:
                self.say(tr("few_moves"), theme.WARN)
            self.warned = True
        self._preview_key = None
        return True

    def _start_wave(self, old_cells):
        """Region cells change colour in a wave spreading from the top-left corner."""
        b = self.level.board
        animate = self.app.store.settings.get("animations", True)
        dist = b.distance_from_corner()
        far = max(dist.values()) or 1
        step = min(0.03, 0.75 / far)
        for i, d in dist.items():
            if old_cells[i] != b.cells[i] or self.shown[i] != b.cells[i]:
                self.anim_from[i] = self.shown[i] if self.anim_start[i] is not None else old_cells[i]
                self.anim_start[i] = self.t + d * step if animate else self.t - 1
        self.anim_end = self.t + (far * step if animate else 0) + FLOOD_ANIM
        self.dirty = True

    def _float(self, msg, color, size=28):
        x = self.board_rect.x + 60
        y = self.board_rect.y + 30
        self.floaters.append(Floater(msg, color, x, y, size))

    def say(self, msg, color=theme.TEXT, dur=1.8):
        self.toast = (msg, color, dur, dur)

    # ---------------------------------------------------------------- events
    def handle(self, event):
        if self.overlay is not None:
            return self.overlay.handle(event)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.pause()
                return True
            if event.key == pygame.K_n:
                self.restart()
                return True
            if event.key == pygame.K_c:
                self.toggle_colorblind()
                return True
            if event.key in COLOR_KEYS and not event.mod & (pygame.KMOD_CTRL | pygame.KMOD_ALT):
                self.pick(COLOR_KEYS[event.key])
                return True
        if event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
            hc = None
            cell = self.cell_at(event.pos)
            if cell is not None:
                hc = self.level.board.cells[cell]
            else:
                p = self.palette_at(event.pos)
                if p is not None:
                    if p != self.hover_color:
                        self.app.audio.play("hover", 0.6)
                    hc = p
            self.hover_color = hc
        if super().handle(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.level is not None:
            p = self.palette_at(event.pos)
            if p is not None:
                self.pick(p)
                return True
            cell = self.cell_at(event.pos)
            if cell is not None:
                self.pick(self.level.board.cells[cell])
                return True
        return False

    # ---------------------------------------------------------------- update
    def update(self, dt):
        if self.overlay is not None:
            self.overlay.update(dt)
            if isinstance(self.overlay, PauseOverlay):
                return
        super().update(dt)
        self._check_ready()
        if self.gen.error is not None:          # pragma: no cover
            raise self.gen.error
        self.particles.update(dt)
        for f in self.floaters:
            f.t += dt
            f.y -= 40 * dt
        self.floaters = [f for f in self.floaters if f.t < 1.3]
        if self.toast:
            msg, col, left, dur = self.toast
            self.toast = (msg, col, left - dt, dur) if left - dt > 0 else None
        self.shake = max(0.0, self.shake - dt)
        mood, left = self.mood
        if left < 90:
            self.mood = (mood, left - dt) if left - dt > 0 else ("", 0.0)
        if self.level is None:
            return
        if not self.finished:
            self.elapsed += dt
        if self.anim_cells or self.t <= self.anim_end + 0.05:
            self.dirty = True
        if self.finish_delay is not None:
            self.finish_delay -= dt
            if self.finish_delay <= 0:
                self.finish_delay = None
                self.app.level_finished(self)
        # optional assist: preview of what the hovered colour would swallow (off by default)
        assist = self.assist_on
        if assist and not self.finished:
            self.assist_used = True
        key = (self.hover_color, self.level.moves, assist)
        if key != self._preview_key:
            self._preview_key = key
            show = assist and not self.finished
            self.preview = self.level.board.gain(self.hover_color) if (show and self.hover_color is not None) else []

    # ------------------------------------------------------------------ draw
    def draw(self, surf):
        if self.level is None:
            self.draw_loading(surf)
            super().draw(surf)
            return
        self.draw_topbar(surf)
        self.draw_board(surf)
        self.draw_panel(surf)
        super().draw(surf)
        self.cb_btn.colors = theme.BTN_BLUE if self.colorblind else theme.BTN_GREY
        for f in self.floaters:
            a = 1 - f.t / 1.3
            text(surf, f.msg, f.size, mix(theme.WHITE, f.color, min(1.0, a * 2)), "black", center=(f.x + 40, f.y),
                 outline=theme.WHITE, outline_w=3)
        if self.toast:
            msg, col, left, dur = self.toast
            pop = ease_out_back(min(1.0, (dur - left) / 0.3))
            r = pygame.Rect(0, 0, int((font(28).size(msg)[0] + 50) * pop), 56)
            r.center = (BOARD_AREA.centerx, BOARD_AREA.bottom - 50)
            if r.w > 20:
                card(surf, r, radius=28, border=col)
                if pop > 0.8:
                    text(surf, msg, 28, col, "black", center=(r.centerx, r.centery + 2))
        self.particles.draw(surf)
        if self.overlay is not None:
            self.overlay.draw(surf)

    def draw_loading(self, surf):
        card(surf, BOARD_AREA, radius=26)
        text(surf, tr("generating"), 34, theme.TEXT, "black", center=(BOARD_AREA.centerx, BOARD_AREA.centery + 90))
        for i in range(8):
            a = self.t * 4 + i * math.tau / 8
            c = theme.FLOOD_COLORS[i]
            pygame.draw.circle(surf, c, (BOARD_AREA.centerx + math.cos(a) * 46, BOARD_AREA.centery - 20 + math.sin(a) * 46),
                               9 + 3 * math.sin(self.t * 5 + i))
        img = image("penguins/penguin.png", 70)
        surf.blit(img, img.get_rect(center=(BOARD_AREA.centerx, BOARD_AREA.centery - 20)))

    def draw_topbar(self, surf):
        d = self.defn
        rect = text(surf, tr("level_hud", n=self.number), 40, theme.WHITE, "black", midleft=(96, 38),
                    outline=(255, 120, 160), outline_w=3)
        text(surf, tr("board_hud", s=d.size, c=d.colors), 24, theme.TEXT_SOFT, "bold", midleft=(rect.right + 18, 40))
        text(surf, tr("elapsed", t=fmt_time(self.elapsed)), 20, theme.TEXT_SOFT, "medium",
             midright=(W - 210, 40))

    def _cell_rect(self, i):
        n = self.level.board.size
        r, c = divmod(i, n)
        return pygame.Rect(c * self.cell, r * self.cell, self.cell, self.cell)

    def _render_board(self):
        b = self.level.board
        s = self.board_surf
        s.fill((0, 0, 0, 0))
        cell = self.cell
        gap = 1 if cell < 20 else 2
        rad = max(2, cell // 4)
        cb = self.colorblind
        sym = int(cell * 0.5)
        region = b.region
        animating = []
        for i in range(len(b.cells)):
            target = b.cells[i]
            st = self.anim_start[i]
            pop = 0.0
            if st is not None:
                p = (self.t - st) / FLOOD_ANIM
                if p >= 1:
                    self.anim_start[i] = None
                    col = theme.FLOOD_COLORS[target]
                    show_idx = target
                elif p <= 0:
                    col = theme.FLOOD_COLORS[self.anim_from[i]]
                    show_idx = self.anim_from[i]
                    animating.append(i)
                else:
                    col = mix(theme.FLOOD_COLORS[self.anim_from[i]], theme.FLOOD_COLORS[target], ease_out(p))
                    col = mix(col, theme.WHITE, 0.35 * math.sin(math.pi * p))
                    pop = math.sin(math.pi * p)
                    show_idx = target if p > 0.5 else self.anim_from[i]
                    animating.append(i)
            else:
                col = theme.FLOOD_COLORS[target]
                show_idx = target
            self.shown[i] = show_idx
            if i in region:
                # the flooded area is drawn seamless, like one big lake
                r = self._cell_rect(i)
                pygame.draw.rect(s, col, r)
            else:
                r = self._cell_rect(i).inflate(-gap * 2, -gap * 2)
                if pop:
                    r = r.inflate(int(gap * 2 * pop), int(gap * 2 * pop))
                pygame.draw.rect(s, col, r, border_radius=rad)
            if cell >= 14 and i not in region:
                hl = mix(col, theme.WHITE, 0.35)
                pygame.draw.line(s, hl, (r.x + rad, r.y + 2), (r.right - rad, r.y + 2), max(1, cell // 14))
            if cb:
                ink = symbol_ink(theme.FLOOD_COLORS[show_idx])
                img = symbol(show_idx, sym, ink)
                s.blit(img, img.get_rect(center=r.center))
        self.anim_cells = animating
        self.dirty = False

    def draw_board(self, surf):
        lv = self.level
        frame = self.board_rect.inflate(22, 22)
        dx = int(math.sin(self.shake * 60) * 6 * self.shake / 0.25) if self.shake else 0
        card(surf, frame.move(dx, 0), radius=22, border=theme.CARD_BORDER)
        if self.dirty:
            self._render_board()
        surf.blit(self.board_surf, self.board_rect.move(dx, 0))
        # hover preview: pulsing white outline on every cell the colour would swallow
        if self.preview:
            pulse = 0.5 + 0.5 * math.sin(self.t * 7)
            ov = pygame.Surface(self.board_rect.size, pygame.SRCALPHA)
            w = 2 if self.cell < 20 else 3
            rad = max(2, self.cell // 4)
            for i in self.preview:
                r = self._cell_rect(i).inflate(-2, -2)
                pygame.draw.rect(ov, (255, 255, 255, int(60 + 70 * pulse)), r, border_radius=rad)
                pygame.draw.rect(ov, (*theme.TEXT, int(150 + 90 * pulse)), r, w, border_radius=rad)
            surf.blit(ov, self.board_rect.move(dx, 0))
        # the penguin sits on the starting corner
        mood = self.mood[0]
        if lv.won and self.t >= self.anim_end:
            name = "penguin_float"
        elif lv.warning() and not mood:
            name = "penguin_sad"
        else:
            name = "penguin" + mood if mood else "penguin"
        size = max(56, min(96, int(self.cell * 1.8)))
        bob = math.sin(self.t * 3) * 3 + (abs(math.sin(self.t * 9)) * 8 if mood == "_happy" else 0)
        img = image(f"penguins/{name}.png", size)
        surf.blit(img, img.get_rect(center=(self.board_rect.x + 4 + dx, self.board_rect.y - 2 - bob)))

    def draw_panel(self, surf):
        lv = self.level
        # ---- moves card
        mc = pygame.Rect(PANEL.x, PANEL.y, PANEL.w, 192)
        warn = lv.warning() or lv.lost
        card(surf, mc, radius=26, border=theme.WARN if warn else theme.CARD_BORDER)
        pulse = 1 + (0.06 * math.sin(self.t * 10) if warn and not lv.over else 0)
        col = theme.WARN if warn else theme.TEXT
        surf.blit(image("icons/steps.png", 54), (mc.x + 22, mc.y + 18))
        f = int(46 * pulse)
        text(surf, tr("moves_hud", n=lv.moves, m=lv.limit), f, col, "black", midleft=(mc.x + 88, mc.y + 46))
        # bar of used moves
        bar = pygame.Rect(mc.x + 26, mc.y + 86, mc.w - 52, 26)
        pygame.draw.rect(surf, (236, 230, 248), bar, border_radius=13)
        frac = lv.moves / max(1, lv.limit)
        fill = bar.copy()
        fill.w = max(bar.h, int(bar.w * frac)) if lv.moves else 0
        bcol = theme.WARN if warn else mix(theme.FLOOD_COLORS[2], theme.FLOOD_COLORS[4], frac)
        if fill.w:
            pygame.draw.rect(surf, bcol, fill, border_radius=13)
        # par marker
        px = bar.x + int(bar.w * lv.par / max(1, lv.limit))
        pygame.draw.line(surf, theme.TEXT, (px, bar.y - 6), (px, bar.bottom + 6), 3)
        star = image("icons/star.png", 22)
        surf.blit(star, star.get_rect(center=(px, bar.y - 14)))
        left = lv.moves_left
        msg = tr("moves_left_1") if left == 1 else tr("moves_left", n=left)
        text(surf, msg, 24, col, "bold", midleft=(mc.x + 28, mc.y + 140))
        text(surf, tr("par_hud", n=lv.par), 22, theme.TEXT_SOFT, "bold", midright=(mc.right - 28, mc.y + 140))
        pct = int(100 * len(lv.board.region) / len(lv.board.cells))
        text(surf, tr("filled", p=pct), 20, theme.TEXT_SOFT, "bold", midleft=(mc.x + 28, mc.y + 170))
        if self.assist_used:
            text(surf, tr("assist_hud"), 18, theme.WARN, "bold", midright=(mc.right - 28, mc.y + 170))
        # ---- palette card
        card(surf, PALETTE_RECT, radius=26)
        text(surf, tr("colors_title"), 26, theme.TEXT, "black", midleft=(PALETTE_RECT.x + 24, PALETTE_RECT.y + 28))
        current = lv.board.color
        left_colors = lv.board.colors_left()
        for rect, i in self.palette_btns:
            base = theme.FLOOD_COLORS[i]
            hover = self.hover_color == i and rect.collidepoint(self.mouse)
            r = rect.move(0, -3 if hover else 0)
            is_cur = i == current
            gone = i not in left_colors and not is_cur
            pygame.draw.rect(surf, theme.SHADOW, rect.move(0, 5), border_radius=16)
            face = mix(base, theme.WHITE, 0.55) if (gone or is_cur) else base
            pygame.draw.rect(surf, mix(base, theme.TEXT, 0.25), r.move(0, 3), border_radius=16)
            pygame.draw.rect(surf, mix(face, theme.WHITE, 0.15) if hover else face, r, border_radius=16)
            gl = pygame.Surface((r.w - 14, r.h // 3), pygame.SRCALPHA)
            pygame.draw.rect(gl, (255, 255, 255, 80), gl.get_rect(), border_radius=8)
            surf.blit(gl, (r.x + 7, r.y + 5))
            if hover:
                pygame.draw.rect(surf, mix(base, theme.TEXT, 0.55), r.inflate(8, 8), 4, border_radius=19)
            if self.colorblind:
                img = symbol(i, int(r.w * 0.42), symbol_ink(face))
                surf.blit(img, img.get_rect(center=r.center))
            key = theme.COLOR_KEYS[i].upper()
            text(surf, key, max(14, r.w // 4), theme.WHITE, "black", topleft=(r.x + 6, r.y + 1),
                 outline=mix(base, theme.TEXT, 0.5), outline_w=2)
            if is_cur:
                img = image("penguins/penguin.png", int(r.w * 0.7))
                surf.blit(img, img.get_rect(center=(r.centerx, r.centery + 4)))
            elif hover and self.preview and self.assist_on:
                text(surf, f"+{len(self.preview)}", max(16, r.w // 3), theme.WHITE, "black",
                     center=(r.centerx, r.bottom - r.h // 4), outline=theme.TEXT, outline_w=2)


# =================================================================== overlays
class Overlay:
    def __init__(self, app, play: PlayScene):
        self.app = app
        self.play = play
        self.buttons: list[Button] = []
        self.t = 0.0

    def handle(self, event):
        for b in self.buttons:
            if b.handle(event):
                return True
        return True

    def update(self, dt):
        self.t += dt
        for b in self.buttons:
            b.update(dt)

    def veil(self, surf, alpha=150):
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((70, 50, 110, alpha))
        surf.blit(v, (0, 0))


class PauseOverlay(Overlay):
    def __init__(self, app, play):
        super().__init__(app, play)
        x = W // 2 - 160
        self.buttons = [
            Button((x, 236, 320, 58), tr("continue"), theme.BTN_MINT, action=self.close),
            Button((x, 304, 320, 58), tr("restart"), theme.BTN_ORANGE, icon="icons/restart.png", action=play.restart),
            Button((x, 372, 320, 58), tr("settings"), theme.BTN_PURPLE, icon="icons/gear.png",
                   action=lambda: app.goto(SettingsScene(app, play))),
            Button((x, 440, 320, 58), tr("howto"), theme.BTN_BLUE, action=lambda: app.goto(HelpScene(app, play))),
            Button((x, 508, 320, 58), tr("menu"), theme.BTN_PINK, icon="icons/home.png", action=self.to_menu),
        ]

    def close(self):
        self.play.overlay = None

    def to_menu(self):
        self.play.overlay = None
        self.app.leave_play(self.play)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.close()
            return True
        return super().handle(event)

    def draw(self, surf):
        self.veil(surf)
        card(surf, (W // 2 - 220, 140, 440, 450), radius=30)
        rainbow_title(surf, tr("paused"), 54, (W // 2, 190), self.t, wave=3)
        for b in self.buttons:
            b.draw(surf)


class ResultOverlay(Overlay):
    """Level complete (won=True) or out of moves (won=False)."""

    def __init__(self, app, play, won: bool, points: dict | None = None, info: dict | None = None):
        super().__init__(app, play)
        self.won = won
        self.points = points or {}
        self.info = info or {}
        self.stars = stars(play.level.moves, play.level.limit, play.level.par, play.assist_used) if won else 0
        self.particles = Particles()
        self.unlock_played = False
        x = W // 2
        if won:
            for i in range(3):
                self.particles.confetti(W // 2 + (i - 1) * 260, 250, 70)
            self.buttons = [
                Button((x - 330, 560, 220, 62), tr("menu"), theme.BTN_PURPLE, icon="icons/home.png",
                       action=lambda: app.goto(MenuScene(app))),
                Button((x - 100, 560, 200, 62), tr("replay"), theme.BTN_ORANGE, size=26,
                       action=lambda: app.start_level(play.number)),
                Button((x + 110, 560, 240, 62), tr("next_level"), theme.BTN_PINK, size=28,
                       action=lambda: app.start_level(play.number + 1)),
            ]
        else:
            self.buttons = [
                Button((x - 290, 540, 270, 62), tr("menu"), theme.BTN_PURPLE, icon="icons/home.png",
                       action=lambda: app.goto(MenuScene(app))),
                Button((x + 20, 540, 270, 62), tr("retry"), theme.BTN_PINK, icon="icons/restart.png",
                       action=lambda: app.start_level(play.number)),
            ]

    def update(self, dt):
        super().update(dt)
        self.particles.update(dt)
        if self.won and random.random() < dt * 30:
            self.particles.rain(random.uniform(0, W))
        if self.won and self.info.get("unlocked") and not self.unlock_played and self.t > 1.6:
            self.unlock_played = True
            self.app.audio.play("unlock")

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.app.start_level(self.play.number + 1 if self.won else self.play.number)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_n:
            self.app.start_level(self.play.number)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.goto(MenuScene(self.app))
            return True
        return super().handle(event)

    def draw(self, surf):
        self.veil(surf, 120)
        pop = ease_out_back(min(1.0, self.t / 0.5))
        panel = pygame.Rect(0, 0, int(720 * (0.8 + 0.2 * pop)), int(560 * (0.8 + 0.2 * pop)))
        panel.center = (W // 2, 360)
        card(surf, panel, radius=34, border=theme.CARD_BORDER if self.won else theme.WARN)
        lv = self.play.level
        title = tr("complete") if self.won else tr("out_of_moves")
        rainbow_title(surf, title, 70, (W // 2, panel.y + 62), self.t, wave=4)
        if self.won:
            stars_row(surf, (W // 2, panel.y + 130), self.stars, 52, 10, self.t)
            text(surf, tr("result_moves", n=lv.moves, m=lv.limit, p=lv.par), 22, theme.TEXT, "bold",
                 center=(W // 2, panel.y + 182))
            rows = [(tr("sc_base"), self.points.get("base", 0)),
                    (tr("sc_unused", n=lv.moves_left), self.points.get("unused", 0)),
                    (tr("sc_par"), self.points.get("par", 0))]
            y = panel.y + 222
            for label, v in rows:
                text(surf, label, 22, theme.TEXT_SOFT, "bold", midleft=(W // 2 - 200, y))
                text(surf, f"+{v}", 24, theme.TEXT, "black", midright=(W // 2 + 200, y))
                y += 32
            pygame.draw.line(surf, theme.CARD_BORDER, (W // 2 - 200, y - 12), (W // 2 + 200, y - 12), 3)
            text(surf, tr("sc_total"), 30, theme.TEXT, "black", midleft=(W // 2 - 200, y + 14))
            text(surf, str(self.points.get("total", 0)), 40, (255, 140, 60), "black", midright=(W // 2 + 200, y + 14),
                 outline=theme.WHITE, outline_w=3)
            notes = []
            if self.play.assist_used:
                notes.append((tr("assist_used"), theme.WARN))
            if lv.moves < lv.par and not self.play.assist_used:
                notes.append((tr("beat_par"), (255, 140, 60)))
            if self.info.get("new_best"):
                notes.append((tr("new_best"), theme.GOOD))
            if self.info.get("unlocked"):
                notes.append((tr("unlocked", n=self.play.number + 1), (90, 120, 230)))
            for k, (msg, col) in enumerate(notes[:2]):
                text(surf, msg, 21, col, "black", center=(W // 2, y + 56 + k * 26))
            text(surf, tr("time_stat", t=fmt_time(self.play.elapsed)), 17, theme.TEXT_SOFT, "medium",
                 center=(W // 2, panel.bottom - 122))
            img = image("penguins/penguin_float.png", 140)
            bounce = abs(math.sin(self.t * 4)) * 14
            surf.blit(img, img.get_rect(midbottom=(panel.x + 90, panel.y + 300 - bounce)))
            img2 = pygame.transform.flip(image("penguins/penguin_happy.png", 120), True, False)
            surf.blit(img2, img2.get_rect(midbottom=(panel.right - 90, panel.y + 300 - abs(math.sin(self.t * 4 + 1)) * 14)))
        else:
            text(surf, tr("out_text", n=self.play.number), 26, theme.TEXT, "bold", center=(W // 2, panel.y + 136))
            pct = int(100 * len(lv.board.region) / len(lv.board.cells))
            text(surf, tr("result_moves", n=lv.moves, m=lv.limit, p=lv.par), 22, theme.TEXT_SOFT, "bold",
                 center=(W // 2, panel.y + 176))
            text(surf, tr("result_left", p=pct, c=len(lv.board.colors_left())), 22, theme.TEXT_SOFT, "bold",
                 center=(W // 2, panel.y + 208))
            img = image("penguins/penguin_sad.png", 170)
            surf.blit(img, img.get_rect(center=(W // 2, panel.y + 330 + math.sin(self.t * 2) * 4)))
            text(surf, tr("time_stat", t=fmt_time(self.play.elapsed)), 17, theme.TEXT_SOFT, "medium",
                 center=(W // 2, panel.bottom - 122))
        for b in self.buttons:
            b.draw(surf)
        self.particles.draw(surf)


# ===================================================================== others
class StatsScene(Scene):
    def __init__(self, app, back=None):
        super().__init__(app)
        self.back = back
        self.buttons = [Button((W // 2 - 130, H - 86, 260, 62), tr("back"), theme.BTN_PINK, action=self.leave)]

    def leave(self):
        self.app.goto(self.back if isinstance(self.back, Scene) else MenuScene(self.app))

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.leave()
            return True
        return super().handle(event)

    def draw(self, surf):
        rainbow_title(surf, tr("stats_title"), 60, (W // 2, 54), self.t, wave=3)
        store = self.app.store
        st = store.data["stats"]
        card(surf, (60, 104, 540, 506), radius=28)
        rows = [("st_played", st["played"]), ("st_won", st["won"]), ("st_lost", st["lost"]),
                ("st_par", st["par_or_better"]), ("st_streak", st["best_streak"]),
                ("st_unlocked", store.unlocked), ("st_moves", st["moves"]), ("st_cells", st["cells"]),
                ("st_time", fmt_time(st.get("seconds", 0)) if st.get("seconds", 0) < 3600 else
                 f"{int(st['seconds'] // 3600)}:{fmt_time(st['seconds'] % 3600)}"),
                ("st_total", store.total_score())]
        for i, (key, v) in enumerate(rows):
            y = 134 + i * 47
            if i < len(rows) - 1:
                pygame.draw.line(surf, theme.CARD_BORDER, (84, y + 23), (576, y + 23), 2)
            text(surf, tr(key), 22, theme.TEXT, "bold", midleft=(88, y))
            text(surf, str(v), 26, (255, 140, 60) if key == "st_total" else theme.TEXT, "black", midright=(572, y))
        card(surf, (640, 104, 580, 506), radius=28)
        text(surf, tr("top_scores"), 30, theme.TEXT, "black", center=(930, 140))
        hs = store.data.get("highscores", [])
        if not hs:
            text(surf, tr("no_scores"), 22, theme.TEXT_SOFT, "medium", center=(930, 340))
            img = image("penguins/penguin_happy.png", 120)
            surf.blit(img, img.get_rect(center=(930, 450)))
        for i, e in enumerate(hs[:10]):
            y = 186 + i * 41
            text(surf, f"{i + 1}.", 22, theme.TEXT_SOFT, "black", midright=(694, y))
            text(surf, str(e["score"]), 24, (255, 140, 60), "black", midleft=(706, y))
            text(surf, tr("hs_line", lv=e["level"], m=e["moves"], lim=e["limit"]), 18, theme.TEXT, "medium",
                 midleft=(800, y))
            stars_row(surf, (1050, y), int(e.get("stars", 1)), 18, 2)
            text(surf, e.get("date", ""), 15, theme.TEXT_SOFT, "medium", midright=(1204, y))
        super().draw(surf)


class HelpScene(Scene):
    music = None
    KEYS = [("h_goal", "h_goal_t"), ("h_move", "h_move_t"), ("h_limit", "h_limit_t"), ("h_score", "h_score_t"),
            ("h_levels", "h_levels_t"), ("h_menu", "h_menu_t"), ("h_mouse", "h_mouse_t"), ("h_keys", "h_keys_t")]

    def __init__(self, app, back: Scene | None = None):
        super().__init__(app)
        self.back = back
        self.buttons = [Button((W // 2 - 120, H - 70, 240, 56), tr("ok"), theme.BTN_MINT, action=self.leave)]
        self.mini = DemoBoard(6, 4, seed=8)

    def leave(self):
        self.app.goto(self.back or MenuScene(self.app))

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.leave()
            return True
        return super().handle(event)

    def update(self, dt):
        super().update(dt)
        self.mini.update(dt)

    def draw(self, surf):
        rainbow_title(surf, tr("help_title"), 60, (W // 2, 50), self.t, wave=3)
        card(surf, (40, 90, W - 80, 548), radius=28)
        y = 102
        colors = theme.TITLE_COLORS
        f = font(18, "medium")
        for i, (head, body) in enumerate(self.KEYS):
            col = colors[i % len(colors)]
            pygame.draw.circle(surf, col, (80, y + 12), 11)
            text(surf, tr(head), 22, col, "black", midleft=(104, y + 12))
            lines = wrap(tr(body), f, W - 400)
            for j, line in enumerate(lines[:3]):
                text(surf, line, 18, theme.TEXT, "medium", midleft=(104, y + 33 + j * 19))
            y += 35 + 19 * min(3, len(lines))
        self.text_bottom = y
        text(surf, tr("h_credit"), 16, theme.TEXT_SOFT, "bold", center=(W // 2, 622))
        self.mini.draw(surf, (W - 270, 160, 190, 190), self.t)
        for i in range(8):
            r = pygame.Rect(W - 290 + i * 28, 400, 24, 24)
            pygame.draw.rect(surf, theme.FLOOD_COLORS[i], r, border_radius=6)
            img = symbol(i, 14, symbol_ink(theme.FLOOD_COLORS[i]))
            surf.blit(img, img.get_rect(center=r.center))
        for i in range(8, 16):
            r = pygame.Rect(W - 290 + (i - 8) * 28, 430, 24, 24)
            pygame.draw.rect(surf, theme.FLOOD_COLORS[i], r, border_radius=6)
            img = symbol(i, 14, symbol_ink(theme.FLOOD_COLORS[i]))
            surf.blit(img, img.get_rect(center=r.center))
        super().draw(surf)


class SettingsScene(Scene):
    """Music / effects volume + mute, language, fullscreen, colour-blind symbols, preview, animation."""
    music = None

    def __init__(self, app, back: Scene | None = None):
        super().__init__(app)
        self.back = back
        self.build()

    def build(self):
        app = self.app
        a = app.audio
        x0 = 460
        self.music_slider = Slider((x0, 180, 400, 18), a.music_volume, theme.BTN_MINT, self._music_vol)
        self.sfx_slider = Slider((x0, 258, 400, 18), a.sfx_volume, theme.BTN_BLUE, self._sfx_vol)
        self.sliders = [self.music_slider, self.sfx_slider]
        self.music_btn = IconButton((930, 189), "icons/music.png", theme.BTN_MINT, app.toggle_music, 54, "M")
        self.sfx_btn = IconButton((930, 267), "icons/speaker.png", theme.BTN_BLUE, app.toggle_sfx, 54, "S")
        bx, bw = W // 2 - 260, 520
        self.lang_btn = Button((bx, 306, bw, 48), "", theme.BTN_ORANGE, icon="icons/globe.png", size=24,
                               action=self._lang)
        self.fs_btn = Button((bx, 360, bw, 48), "", theme.BTN_PURPLE, size=24, action=app.toggle_fullscreen)
        self.cb_btn = Button((bx, 414, bw, 48), "", theme.BTN_BLUE, icon="icons/eye.png", size=24,
                             action=lambda: self._flip("colorblind"))
        self.pv_btn = Button((bx, 468, bw, 48), "", theme.BTN_MINT, size=22, action=lambda: self._flip("assist"))
        self.an_btn = Button((bx, 522, bw, 48), "", theme.BTN_YELLOW, icon="icons/drop.png", size=24,
                             action=lambda: self._flip("animations"))
        self.buttons = [self.music_btn, self.sfx_btn, self.lang_btn, self.fs_btn, self.cb_btn, self.pv_btn,
                        self.an_btn, Button((W // 2 - 110, H - 86, 220, 52), tr("done"), theme.BTN_PINK,
                                            action=self.leave)]
        self.sound_btns = []

    def _music_vol(self, v):
        self.app.audio.set_music_volume(v)
        self.app.store.save()

    def _sfx_vol(self, v):
        self.app.audio.set_sfx_volume(v)
        self.app.audio.play("flood")
        self.app.store.save()

    def _flip(self, key):
        s = self.app.store.settings
        s[key] = not s.get(key, key == "animations")
        self.app.store.save()
        if isinstance(self.back, PlayScene):
            self.back.dirty = True
            self.back._preview_key = None

    def _lang(self):
        s = self.app.store.settings
        s["lang"] = "en" if s.get("lang", "hu") == "hu" else "hu"
        set_lang(s["lang"])
        self.app.store.save()
        self.build()
        if self.back:
            self.back.on_language()
            if isinstance(self.back, PlayScene) and self.back.overlay is not None:
                self.back.overlay = PauseOverlay(self.app, self.back) \
                    if isinstance(self.back.overlay, PauseOverlay) else self.back.overlay

    def leave(self):
        self.app.store.save()
        self.app.goto(self.back or MenuScene(self.app))

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.leave()
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            self._flip("colorblind")
            return True
        for sl in self.sliders:
            if sl.handle(event):
                return True
        return super().handle(event)

    def update(self, dt):
        super().update(dt)
        a, st = self.app.audio, self.app.store.settings
        self.music_slider.value = a.music_volume
        self.sfx_slider.value = a.sfx_volume
        self.music_btn.icon = "icons/music_off.png" if a.music_muted else "icons/music.png"
        self.music_btn.colors = theme.BTN_GREY if a.music_muted else theme.BTN_MINT
        self.sfx_btn.icon = "icons/speaker_off.png" if a.sfx_muted else "icons/speaker.png"
        self.sfx_btn.colors = theme.BTN_GREY if a.sfx_muted else theme.BTN_BLUE
        self.lang_btn.label = tr("language")

        def onoff(k, default):
            return tr("on") if st.get(k, default) else tr("off")
        self.fs_btn.label = tr("fullscreen", v=onoff("fullscreen", False))
        self.fs_btn.colors = theme.BTN_PURPLE if st.get("fullscreen") else theme.BTN_GREY
        self.cb_btn.label = tr("colorblind", v=onoff("colorblind", False))
        self.cb_btn.colors = theme.BTN_BLUE if st.get("colorblind") else theme.BTN_GREY
        self.pv_btn.label = tr("assist", v=onoff("assist", False))
        self.pv_btn.colors = theme.BTN_MINT if st.get("assist", False) else theme.BTN_GREY
        self.an_btn.label = tr("animations", v=onoff("animations", True))
        self.an_btn.colors = theme.BTN_YELLOW if st.get("animations", True) else theme.BTN_GREY

    def draw(self, surf):
        rainbow_title(surf, tr("settings"), 60, (W // 2, 56), self.t, wave=3)
        card(surf, (200, 112, W - 400, 512), radius=30)
        a = self.app.audio
        for label, sl, muted, y in ((tr("music"), self.music_slider, a.music_muted, 189),
                                    (tr("sfx"), self.sfx_slider, a.sfx_muted, 267)):
            text(surf, label, 30, theme.TEXT, "black", midleft=(250, y))
            sl.draw(surf, dim=muted)
            pct = tr("muted") if muted else f"{int(round(sl.value * 100))} %"
            text(surf, pct, 19, theme.TEXT_SOFT, "medium", center=(sl.rect.centerx, y + 28))
        if not a.available:
            text(surf, tr("no_audio"), 20, theme.WRONG, "bold", center=(W // 2, 140))
        super().draw(surf)
        if self.app.store.settings.get("assist", False):
            text(surf, tr("assist_note"), 18, theme.WARN, "bold", center=(W // 2, 598))
        text(surf, tr("keys_settings"), 18, theme.TEXT_SOFT, "medium", center=(W // 2, H - 11))


# ======================================================================= app
class App:
    def __init__(self, headless: bool = False, fullscreen: bool | None = None, audio: bool = True):
        if headless:
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
            os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption("TuxoFlood")
        try:
            pygame.display.set_icon(pygame.image.load(str(icon_path())))
        except pygame.error:
            pass
        self.store = Store()
        set_lang(self.store.settings.get("lang", "hu"))
        self.audio = Audio(self.store.settings, enable=audio)
        Button.on_hover = lambda: self.audio.play("hover")
        Button.on_click = lambda: self.audio.play("click")
        fs = self.store.settings.get("fullscreen", False) if fullscreen is None else fullscreen
        self.screen = self._set_mode(fs)
        self.clock = pygame.time.Clock()
        self.snow = Snow()
        self.sync_levels = headless          # tests/screenshots build boards synchronously
        self.scene: Scene = MenuScene(self)
        self.audio.play_music(self.scene.music)
        self.running = True

    def _set_mode(self, fullscreen: bool):
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        try:
            return pygame.display.set_mode((W, H), flags)
        except pygame.error:
            return pygame.display.set_mode((W, H))

    # ------------------------------------------------------------ flow
    def goto(self, scene: Scene):
        self.scene = scene
        if scene.music:
            self.audio.play_music(scene.music)

    def start_level(self, number: int, seed: int | None = None):
        number = max(1, min(int(number), self.store.unlocked))
        self.goto(PlayScene(self, number, seed, sync=self.sync_levels))

    def leave_play(self, play: PlayScene):
        """Back to the menu from a running board; a started board counts as lost."""
        if play.level is not None and not play.finished and play.level.moves > 0:
            play.finished = True
            self.store.record_loss(play.level.moves, play.elapsed, len(play.level.board.region))
        self.goto(MenuScene(self))

    def level_finished(self, play: PlayScene):
        lv = play.level
        cells = len(lv.board.region)
        self.audio.duck(3.0)
        if lv.won:
            assisted = play.assist_used
            pts = score_breakdown(lv.defn, lv.moves, lv.limit, lv.par, assisted)
            info = self.store.record_win(play.number, pts["total"], lv.moves, lv.limit, lv.par,
                                         stars(lv.moves, lv.limit, lv.par, assisted), play.elapsed, cells, assisted)
            self.audio.play("victory")
            play.overlay = ResultOverlay(self, play, True, pts, info)
        else:
            self.store.record_loss(lv.moves, play.elapsed, cells)
            self.audio.play("defeat")
            play.overlay = ResultOverlay(self, play, False)

    def toggle_music(self):
        self.audio.toggle_music()
        self.store.save()

    def toggle_sfx(self):
        self.audio.toggle_sfx()
        self.store.save()

    def toggle_fullscreen(self):
        s = self.store.settings
        s["fullscreen"] = not s.get("fullscreen", False)
        self.store.save()
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            self.screen = self._set_mode(s["fullscreen"])

    def quit(self):
        self.running = False

    # ------------------------------------------------------------ loop
    def step(self, dt: float, events=()):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                self.toggle_music()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_s and not event.mod & pygame.KMOD_CTRL:
                self.toggle_sfx()
            else:
                self.scene.handle(event)
        self.audio.update(dt)
        self.snow.update(dt)
        self.scene.update(dt)
        draw_background(self.screen, self.snow)
        self.scene.draw(self.screen)

    def run(self):
        while self.running:
            dt = min(self.clock.tick(theme.FPS) / 1000.0, 0.1)
            self.step(dt, pygame.event.get())
            pygame.display.flip()
        self.store.save()
        self.audio.shutdown()
        pygame.quit()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tuxoflood", description="TuxoFlood – pingvines színkitöltő játék")
    parser.add_argument("--fullscreen", action="store_true", help="teljes képernyő / fullscreen")
    parser.add_argument("--mute", action="store_true", help="hang nélkül (nem nyitja meg a hangeszközt) / no audio")
    parser.add_argument("--lang", choices=("hu", "en"), help="nyelv / language")
    parser.add_argument("--version", action="version", version=f"TuxoFlood {__version__}")
    args = parser.parse_args(argv)
    app = App(fullscreen=True if args.fullscreen else None, audio=not args.mute)
    if args.lang:
        app.store.settings["lang"] = args.lang
        set_lang(args.lang)
        app.scene = MenuScene(app)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
