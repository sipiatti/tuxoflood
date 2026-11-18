import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from tuxoflood import audio as audio_mod  # noqa: E402
from tuxoflood.audio import MUSIC_TRACKS, SOUND_NAMES, Audio  # noqa: E402
from tuxoflood.resources import ASSETS  # noqa: E402
from tuxoflood.storage import Store  # noqa: E402


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TUXOFLOOD_DATA_DIR", str(tmp_path))
    yield
    if pygame.mixer.get_init():
        pygame.mixer.quit()


def test_audio_assets_exist_and_are_small():
    total = 0
    for name in SOUND_NAMES:
        p = ASSETS / "sounds" / f"{name}.wav"
        assert p.is_file()
        total += p.stat().st_size
    for rel in MUSIC_TRACKS.values():
        p = ASSETS / rel
        assert p.is_file() and p.read_bytes()[:4] == b"OggS"
        total += p.stat().st_size
    assert total < 5 * 1024 * 1024


def test_audio_settings_persist(tmp_path):
    st = Store(tmp_path / "s.json")
    a = Audio(st.data["settings"], enable=False)
    a.set_music_volume(0.3)
    a.set_sfx_volume(1.7)
    a.toggle_music()
    a.toggle_sfx()
    st.save()
    again = Store(tmp_path / "s.json").data["settings"]
    assert again["music_volume"] == 0.3 and again["sfx_volume"] == 1.0
    assert again["music_muted"] is True and again["sfx_muted"] is True


def test_no_audio_device_runs_silently(monkeypatch):
    def boom(*a, **k):
        raise pygame.error("No available audio device")

    monkeypatch.setattr(audio_mod.pygame.mixer, "init", boom)
    monkeypatch.setattr(audio_mod.pygame.mixer, "get_init", lambda: None)
    a = Audio({}, enable=True)
    assert a.available is False and a.sounds == {}
    a.play("flood")
    a.play_music("menu")
    a.toggle_music()
    a.toggle_sfx()
    a.duck(1.0)
    a.update(2.0)
