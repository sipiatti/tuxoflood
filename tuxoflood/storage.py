"""Persist progress (unlocked levels, best results), statistics, high scores and settings as JSON.

Location: $TUXOFLOOD_DATA_DIR, else $XDG_DATA_HOME/tuxoflood, else ~/.local/share/tuxoflood
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

MAX_HIGHSCORES = 10
MAX_CAMPAIGN_BACKUPS = 5


def data_dir() -> Path:
    env = os.environ.get("TUXOFLOOD_DATA_DIR")
    if env:
        return Path(env)
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "tuxoflood"


def _empty_stats() -> dict:
    return {"played": 0, "won": 0, "lost": 0, "moves": 0, "cells": 0, "seconds": 0.0, "par_or_better": 0,
            "streak": 0, "best_streak": 0}


def default_save() -> dict:
    return {
        "version": 1,
        "unlocked": 1,            # highest level that may be started
        "levels": {},             # "n": {"best": score, "stars": 1..3, "moves": fewest moves, "wins": k}
        "stats": _empty_stats(),
        "highscores": [],         # [{"score", "level", "moves", "limit", "par", "stars", "date"}]
        "campaign_backups": [],   # earlier campaigns cleared by "New game": [{"date", "unlocked", "levels"}]
        "settings": {"lang": "hu", "fullscreen": False, "music_volume": 0.5, "sfx_volume": 0.8,
                     "music_muted": False, "sfx_muted": False, "colorblind": False, "assist": False,
                     "animations": True},
    }


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or data_dir() / "progress.json"
        self.data = default_save()
        self.load()

    def load(self) -> None:
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(loaded, dict):
            return
        base = default_save()
        loaded_settings = dict(loaded.get("settings") or {})
        # 0.1.0 pre-release saves had a "preview" setting that defaulted to on; it is now the
        # opt-in "assist" setting, so the old value is dropped and the assist starts off.
        loaded_settings.pop("preview", None)
        base["settings"].update(loaded_settings)
        base["stats"].update(loaded.get("stats") or {})
        try:
            base["unlocked"] = max(1, int(loaded.get("unlocked", 1)))
        except (TypeError, ValueError):
            pass
        if isinstance(loaded.get("levels"), dict):
            base["levels"] = {str(k): v for k, v in loaded["levels"].items() if isinstance(v, dict)}
        if isinstance(loaded.get("highscores"), list):
            base["highscores"] = loaded["highscores"][:MAX_HIGHSCORES]
        if isinstance(loaded.get("campaign_backups"), list):
            base["campaign_backups"] = [b for b in loaded["campaign_backups"]
                                        if isinstance(b, dict)][-MAX_CAMPAIGN_BACKUPS:]
        self.data = base

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            pass

    @property
    def settings(self) -> dict:
        return self.data["settings"]

    @property
    def unlocked(self) -> int:
        return self.data["unlocked"]

    def level_info(self, n: int) -> dict:
        return self.data["levels"].get(str(n), {})

    def has_progress(self) -> bool:
        """True once the campaign has moved past a fresh start (something to continue or to lose)."""
        return self.data["unlocked"] > 1 or bool(self.data["levels"])

    def reset_campaign(self) -> Path | None:
        """Start the campaign again from level 1.

        Clears unlocked levels and the per-level bests/stars; keeps lifetime statistics, the high-score
        list and the settings. The old campaign is kept inside the save ("campaign_backups") and the
        whole previous file is copied to progress.json.bak-YYYYmmdd-HHMMSS. Returns that backup path
        (None if there was no file yet or it could not be copied).
        """
        backup = None
        if self.path.exists():
            backup = self.path.with_name(f"{self.path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
            try:
                shutil.copy2(self.path, backup)
            except OSError:
                backup = None
        if self.has_progress():
            lst = self.data.setdefault("campaign_backups", [])
            lst.append({"date": time.strftime("%Y-%m-%d %H:%M:%S"), "unlocked": self.data["unlocked"],
                        "levels": self.data["levels"]})
            del lst[:-MAX_CAMPAIGN_BACKUPS]
        self.data["unlocked"] = 1
        self.data["levels"] = {}
        self.save()
        return backup

    def total_score(self) -> int:
        return sum(int(v.get("best", 0)) for v in self.data["levels"].values())

    def record_win(self, level: int, score: int, moves: int, limit: int, par: int, stars: int,
                   seconds: float, cells: int, assisted: bool = False) -> dict:
        """Returns {"new_best": bool, "top": bool, "unlocked": bool}."""
        st = self.data["stats"]
        st["played"] += 1
        st["won"] += 1
        st["moves"] += moves
        st["cells"] += cells
        st["seconds"] = round(st.get("seconds", 0.0) + seconds, 1)
        st["streak"] += 1
        st["best_streak"] = max(st["best_streak"], st["streak"])
        if moves <= par and not assisted:
            st["par_or_better"] += 1
        info = self.data["levels"].setdefault(str(level), {})
        new_best = score > info.get("best", 0)
        info["best"] = max(score, info.get("best", 0))
        info["stars"] = max(stars, info.get("stars", 0))
        info["moves"] = min(moves, info.get("moves", moves))
        info["wins"] = info.get("wins", 0) + 1
        unlocked = level + 1 > self.data["unlocked"]
        self.data["unlocked"] = max(self.data["unlocked"], level + 1)
        entry = {"score": score, "level": level, "moves": moves, "limit": limit, "par": par, "stars": stars,
                 "date": time.strftime("%Y-%m-%d")}
        if assisted:
            entry["assist"] = True
        lst = self.data["highscores"]
        lst.append(entry)
        lst.sort(key=lambda e: (-e["score"], -e["level"]))
        del lst[MAX_HIGHSCORES:]
        top = any(e is entry for e in lst)
        self.save()
        return {"new_best": new_best, "top": top, "unlocked": unlocked}

    def record_loss(self, moves: int, seconds: float, cells: int) -> None:
        st = self.data["stats"]
        st["played"] += 1
        st["lost"] += 1
        st["moves"] += moves
        st["cells"] += cells
        st["seconds"] = round(st.get("seconds", 0.0) + seconds, 1)
        st["streak"] = 0
        self.save()
