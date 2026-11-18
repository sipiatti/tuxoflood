import json

from tuxoflood.storage import MAX_HIGHSCORES, Store, data_dir


def test_data_dir_env(tmp_path, monkeypatch):
    monkeypatch.setenv("TUXOFLOOD_DATA_DIR", str(tmp_path / "x"))
    assert data_dir() == tmp_path / "x"
    monkeypatch.delenv("TUXOFLOOD_DATA_DIR")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    assert data_dir() == tmp_path / "xdg" / "tuxoflood"


def test_win_unlocks_and_persists(tmp_path):
    p = tmp_path / "p.json"
    st = Store(p)
    assert st.unlocked == 1
    info = st.record_win(1, 300, 6, 8, 6, 3, 12.5, 36)
    assert info == {"new_best": True, "top": True, "unlocked": True}
    again = Store(p)
    assert again.unlocked == 2
    assert again.level_info(1) == {"best": 300, "stars": 3, "moves": 6, "wins": 1}
    assert again.data["stats"]["won"] == 1 and again.data["stats"]["par_or_better"] == 1
    # a worse replay keeps the best values
    info = again.record_win(1, 200, 7, 8, 6, 2, 3.0, 36)
    assert info["new_best"] is False and info["unlocked"] is False
    assert again.level_info(1)["best"] == 300 and again.level_info(1)["stars"] == 3
    assert again.total_score() == 300


def test_loss_resets_streak(tmp_path):
    st = Store(tmp_path / "p.json")
    st.record_win(1, 100, 5, 8, 5, 3, 1, 36)
    st.record_win(2, 100, 5, 8, 5, 3, 1, 36)
    st.record_loss(8, 4.0, 10)
    s = Store(tmp_path / "p.json").data["stats"]
    assert (s["played"], s["won"], s["lost"], s["streak"], s["best_streak"]) == (3, 2, 1, 0, 2)
    assert s["moves"] == 18 and s["seconds"] == 6.0


def test_highscores_are_capped_and_sorted(tmp_path):
    st = Store(tmp_path / "p.json")
    for k in range(15):
        st.record_win(k + 1, 100 * k, 5, 8, 5, 3, 1, 36)
    hs = st.data["highscores"]
    assert len(hs) == MAX_HIGHSCORES
    assert [e["score"] for e in hs] == sorted((e["score"] for e in hs), reverse=True)


def test_corrupt_or_odd_save_is_ignored(tmp_path):
    p = tmp_path / "p.json"
    p.write_text("{nope", encoding="utf-8")
    assert Store(p).data["settings"]["lang"] == "hu"
    p.write_text(json.dumps([1, 2]), encoding="utf-8")
    assert Store(p).unlocked == 1
    p.write_text(json.dumps({"unlocked": "x", "settings": {"lang": "en"}}), encoding="utf-8")
    s = Store(p)
    assert s.unlocked == 1 and s.settings["lang"] == "en" and s.settings["colorblind"] is False


def test_old_preview_setting_is_migrated_to_assist_off(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"settings": {"preview": True, "colorblind": True}}), encoding="utf-8")
    s = Store(p)
    assert "preview" not in s.settings and s.settings["assist"] is False and s.settings["colorblind"] is True
    s.save()
    assert "preview" not in json.loads(p.read_text(encoding="utf-8"))["settings"]


def test_assisted_win_is_marked(tmp_path):
    st = Store(tmp_path / "p.json")
    st.record_win(1, 100, 5, 8, 5, 0, 1, 36, assisted=True)
    assert st.data["stats"]["par_or_better"] == 0
    assert st.data["highscores"][0]["assist"] is True and st.level_info(1)["stars"] == 0


def test_reset_campaign_keeps_stats_highscores_settings(tmp_path):
    st = Store(tmp_path / "progress.json")
    st.settings["lang"] = "en"
    st.record_win(1, 300, 5, 8, 5, 3, 12.0, 36)
    st.record_win(2, 500, 6, 9, 6, 3, 15.0, 49)
    stats, tops = dict(st.data["stats"]), list(st.data["highscores"])
    assert st.has_progress()
    bak = st.reset_campaign()
    assert bak is not None and bak.exists() and json.loads(bak.read_text())["unlocked"] == 3
    again = Store(tmp_path / "progress.json")
    assert again.unlocked == 1 and again.data["levels"] == {} and not again.has_progress()
    assert again.data["stats"] == stats and again.data["highscores"] == tops
    assert again.settings["lang"] == "en"
    b = again.data["campaign_backups"]
    assert len(b) == 1 and b[0]["unlocked"] == 3 and b[0]["levels"]["2"]["best"] == 500


def test_reset_campaign_fresh_and_backup_cap(tmp_path):
    st = Store(tmp_path / "progress.json")
    assert not st.has_progress()
    assert st.reset_campaign() is None              # no file yet: nothing to copy
    assert st.data["campaign_backups"] == []         # nothing worth keeping
    for k in range(8):
        st.record_win(1, 100 + k, 5, 8, 5, 3, 1.0, 36)
        st.reset_campaign()
    assert len(Store(tmp_path / "progress.json").data["campaign_backups"]) == 5
