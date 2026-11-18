"""Hungarian (default) and English UI strings."""
from __future__ import annotations

LANGS = ("hu", "en")
_lang = "hu"

S = {
    # menu
    "subtitle": ("Színes pingvináradat – töltsd ki a jégmezőt egy színnel!",
                 "A colourful penguin flood – fill the ice field with one colour!"),
    "play": ("Játék", "Play"),
    "play_level": ("Játék: {n}. szint", "Play: level {n}"),
    "levels": ("Szintek", "Levels"),
    "continue_level": ("Folytatás: {n}. szint", "Continue: level {n}"),
    "new_game": ("Új játék (1. szinttől)", "New game (from level 1)"),
    "new_game_fresh": ("Új játék", "New game"),
    "confirm_title": ("Új játék", "New game"),
    "confirm_text": ("Biztosan előröl kezded? A feloldott szintek és pontok törlődnek.",
                     "Start over from level 1? Unlocked levels and scores will be cleared."),
    "confirm_keep": ("A statisztika, a ranglista és a beállítások megmaradnak.",
                     "Your statistics, high-score list and settings are kept."),
    "confirm_now": ("Most: {n}. szint · {p} pont", "Now: level {n} · {p} points"),
    "yes": ("Igen", "Yes"),
    "cancel": ("Mégse", "Cancel"),
    "howto": ("Hogyan játssz?", "How to play"),
    "stats": ("Statisztika", "Statistics"),
    "quit": ("Kilépés", "Quit"),
    "menu": ("Menü", "Menu"),
    "back": ("Vissza", "Back"),
    "done": ("Kész", "Done"),
    "ok": ("Értem!", "Got it!"),
    "continue": ("Folytatás", "Resume"),
    "total_score": ("Összpontszám: {n}", "Total score: {n}"),
    # level select
    "levels_title": ("Válassz szintet!", "Choose a level!"),
    "level_n": ("{n}. szint", "Level {n}"),
    "level_short": ("{n}.", "{n}"),
    "level_info": ("{s}×{s} · {c} szín", "{s}×{s} · {c} colours"),
    "endless": ("Végtelen", "Endless"),
    "endless_info": ("A {n}. szinttől minden pálya {s}×{s}, {c} színnel – meddig bírod?",
                     "From level {n} on every board is {s}×{s} with {c} colours – how far can you go?"),
    "locked": ("Zárva", "Locked"),
    "page": ("{a} / {b}", "{a} / {b}"),
    # play
    "level_hud": ("{n}. szint", "Level {n}"),
    "moves_hud": ("Lépés: {n} / {m}", "Moves: {n} / {m}"),
    "moves_left": ("Még {n} lépés", "{n} moves left"),
    "moves_left_1": ("Utolsó lépés!", "Last move!"),
    "par_hud": ("Pingvinrekord: {n}", "Penguin par: {n}"),
    "board_hud": ("{s}×{s} · {c} szín", "{s}×{s} · {c} colours"),
    "filled": ("Elárasztva: {p}%", "Flooded: {p}%"),
    "colors_title": ("Színek", "Colours"),
    "restart": ("Új pálya", "New board"),
    "pause": ("Szünet", "Pause"),
    "paused": ("Szünet", "Paused"),
    "generating": ("Pálya készül…", "Making the board…"),
    "few_moves": ("Kevés lépés maradt!", "Few moves left!"),
    "nice": ("Szép!", "Nice!"),
    "great": ("Hatalmas!", "Huge!"),
    "colour_gone": ("Egy szín eltűnt!", "A colour is gone!"),
    "elapsed": ("Idő: {t}", "Time: {t}"),
    "tip_colorblind": ("Szimbólumok (C)", "Symbols (C)"),
    "tip_restart": ("Új pálya (N)", "New board (N)"),
    "tip_pause": ("Szünet (P / Esc)", "Pause (P / Esc)"),
    # results
    "complete": ("Pálya kész!", "Level complete!"),
    "out_of_moves": ("Elfogytak a lépések!", "Out of moves!"),
    "out_text": ("A {n}. szint elveszett – próbáld újra egy új pályán!",
                 "Level {n} is lost – try again on a new board!"),
    "result_moves": ("{n} / {m} lépés · pingvinrekord: {p}", "{n} / {m} moves · penguin par: {p}"),
    "result_left": ("Kitöltve: {p}% · maradt {c} szín", "Flooded: {p}% · {c} colours left"),
    "sc_base": ("Pályapont", "Board points"),
    "sc_unused": ("Megmaradt lépések ({n})", "Unused moves ({n})"),
    "sc_par": ("Pingvinrekord-bónusz", "Penguin par bonus"),
    "sc_total": ("Összesen", "Total"),
    "new_best": ("Új egyéni csúcs ezen a szinten!", "New personal best on this level!"),
    "unlocked": ("Feloldva: {n}. szint!", "Unlocked: level {n}!"),
    "beat_par": ("Megverted a pingvinrekordot!", "You beat the penguin par!"),
    "next_level": ("Következő szint", "Next level"),
    "retry": ("Újra", "Try again"),
    "replay": ("Új pálya", "New board"),
    "time_stat": ("Idő: {t} (csak statisztika)", "Time: {t} (just for stats)"),
    # stats
    "stats_title": ("Statisztika", "Statistics"),
    "st_played": ("Lejátszott pályák", "Boards played"),
    "st_won": ("Kész pályák", "Boards completed"),
    "st_lost": ("Elfogyott lépések", "Ran out of moves"),
    "st_par": ("Pingvinrekord vagy jobb", "At or under par"),
    "st_streak": ("Leghosszabb sorozat", "Best streak"),
    "st_unlocked": ("Legmagasabb szint", "Highest level"),
    "st_moves": ("Összes lépés", "Total moves"),
    "st_cells": ("Elárasztott mezők", "Cells flooded"),
    "st_time": ("Játékidő", "Time played"),
    "st_total": ("Összpontszám", "Total score"),
    "top_scores": ("Legjobb pályák", "Best boards"),
    "no_scores": ("Még nincs kész pálya – rajta!", "No boards completed yet – go for it!"),
    "hs_line": ("{lv}. szint · {m}/{lim} lépés", "level {lv} · {m}/{lim} moves"),
    # settings
    "settings": ("Beállítások", "Settings"),
    "music": ("Zene", "Music"),
    "sfx": ("Hangok", "Sounds"),
    "muted": ("némítva", "muted"),
    "language": ("Nyelv: Magyar", "Language: English"),
    "fullscreen": ("Teljes képernyő: {v}", "Fullscreen: {v}"),
    "colorblind": ("Színtévesztő mód (szimbólumok): {v}", "Colour-blind mode (symbols): {v}"),
    "assist": ("Könnyítés (mutatja, mit nyelnél el): {v}", "Assist (shows what you'd swallow): {v}"),
    "assist_note": ("Könnyítéssel a pálya nem ér csillagot és pingvinrekord-bónuszt.",
                    "With the assist on, a board earns no stars and no par bonus."),
    "assist_used": ("Könnyítéssel: nincs csillag és pingvinrekord-bónusz", "Assist used: no stars and no par bonus"),
    "assist_hud": ("Könnyítés BE", "Assist ON"),
    "animations": ("Áradás-animáció: {v}", "Flood animation: {v}"),
    "on": ("BE", "ON"),
    "off": ("KI", "OFF"),
    "no_audio": ("Nem található hangeszköz – a játék hang nélkül fut.", "No audio device found – the game runs silently."),
    "keys_settings": ("M: zene · S: hangok · C: szimbólumok · F11: teljes képernyő",
                      "M: music · S: sounds · C: symbols · F11: fullscreen"),
    "tip_music": ("Zene (M)", "Music (M)"),
    "tip_sfx": ("Hangok (S)", "Sounds (S)"),
    "tip_settings": ("Beállítások", "Settings"),
    "tip_help": ("Súgó", "Help"),
    # help
    "help_title": ("Hogyan játssz?", "How to play"),
    "h_goal": ("A cél", "The goal"),
    "h_goal_t": ("A pingvin a bal felső sarokból indul. Töltsd ki az egész pályát egyetlen színnel!",
                 "The penguin starts in the top-left corner. Fill the whole board with a single colour!"),
    "h_move": ("Egy lépés", "One move"),
    "h_move_t": ("Válassz színt: a te területed átszíneződik, és elnyeli az összes szomszédos, ugyanolyan színű mezőt.",
                 "Pick a colour: your area takes that colour and swallows every touching cell of the same colour."),
    "h_limit": ("Lépéskorlát", "Move limit"),
    "h_limit_t": ("Minden pályán korlátos a lépések száma. Ha elfogynak, mielőtt kész lennél, a szint elveszett, "
                  "és új pályán kezdheted újra. Időkorlát nincs, nyugodtan gondolkodj!",
                  "Every board has a move limit. If you run out before it is full, the level is lost and you start "
                  "again on a new board. There is no time limit – take your time!"),
    "h_score": ("Pontozás", "Scoring"),
    "h_score_t": ("Pályapont + bónusz minden megmaradt lépésért + pingvinrekord-bónusz, ha legfeljebb annyi lépés "
                  "kellett, mint a gépi megoldásnak. 3 csillag: pingvinrekord vagy jobb.",
                  "Board points + a bonus for every unused move + a par bonus if you needed no more moves than the "
                  "computer's solution. 3 stars: par or better."),
    "h_levels": ("Szintek", "Levels"),
    "h_levels_t": ("Szintenként nő a pálya (6×6-tól 26×26-ig) és a színek száma (3-tól 16-ig), a tartaléklépés pedig fogy.",
                   "Every level the board grows (6×6 up to 26×26), the colours too (3 up to 16), and spare moves shrink."),
    "h_menu": ("Főmenü", "Main menu"),
    "h_menu_t": ("Folytatás: a következő szinttől. Új játék (1. szinttől): előröl, a feloldott szintek és pontok "
                 "törlődnek – a statisztika, a ranglista és a beállítások megmaradnak. ↑ ↓ / Tab + Enter is működik.",
                 "Continue: from your next level. New game (from level 1): starts over, unlocked levels and scores are "
                 "cleared – statistics, high scores and settings are kept. ↑ ↓ / Tab + Enter work too."),
    "h_mouse": ("Egér", "Mouse"),
    "h_mouse_t": ("Kattints egy színgombra vagy a pálya bármelyik mezőjére. A beállításokban bekapcsolható "
                  "Könnyítés megmutatja, mit nyelnél el, de akkor nincs csillag és pingvinrekord-bónusz.",
                  "Click a colour button or any cell on the board. The optional Assist setting shows what you would "
                  "swallow, but then the board earns no stars and no par bonus."),
    "h_keys": ("Billentyűk", "Keys"),
    "h_keys_t": ("1–9, 0, Q W E R T Y: színek · N: új pálya · C: szimbólumok · P / Esc: szünet · M / S: zene / hangok · F11",
                 "1–9, 0, Q W E R T Y: colours · N: new board · C: symbols · P / Esc: pause · M / S: music / sounds · F11"),
    "h_credit": ("A klasszikus „Flood-It” típusú játékok ihlették – minden kép, hang és zene saját.",
                 "Inspired by classic “Flood-It” style games – all art, sounds and music are original."),
}


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGS else "hu"


def lang() -> str:
    return _lang


def tr(key: str, **kw) -> str:
    pair = S.get(key)
    if pair is None:
        return key
    s = pair[0] if _lang == "hu" else pair[1]
    return s.format(**kw) if kw else s
