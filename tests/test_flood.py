"""Rules, generator, solver, level table and scoring (pure Python)."""
import random

import pytest

from tuxoflood import theme
from tuxoflood.flood import (LAST_TABLE_LEVEL, LEVEL_TABLE, MAX_COLORS, Board, Level, level_def, move_limit,
                             new_level, random_board, score_breakdown, solve, solve_beam, solve_best, stars,
                             verify_solution, warning_threshold)


def board(rows):
    n = len(rows)
    cells = [int(ch) for row in rows for ch in row]
    return Board(cells, n, max(cells) + 1)


def test_initial_region_is_connected_corner_area():
    b = board(["001", "011", "222"])
    assert b.region == {0, 1, 3}
    assert b.color == 0 and not b.solved()


def test_flood_absorbs_adjacent_same_colour_only():
    b = board(["0012", "1102", "2222", "0000"])
    gained = b.flood(1)
    assert set(gained) == {2, 4, 5}
    assert b.region == {0, 1, 2, 4, 5}
    assert b.cells[6] == 0                 # the old colour next to the region is not absorbed
    assert all(b.cells[i] == 1 for i in b.region)
    assert b.cells[12] == 0                # far away 0s stay 0


def test_region_growth_chains_through_new_cells():
    b = board(["01", "12"])
    b.flood(1)
    assert b.region == {0, 1, 2}
    b.flood(2)
    assert b.solved()


def test_same_colour_is_a_noop_and_bad_colour_raises():
    b = board(["01", "10"])
    assert b.flood(0) == []
    with pytest.raises(ValueError):
        b.flood(5)


def test_gain_matches_flood_and_has_no_duplicates():
    rng = random.Random(3)
    for _ in range(40):
        b = random_board(9, 5, rng)
        for c in range(5):
            g = b.gain(c)
            assert len(g) == len(set(g))
            cp = b.copy()
            assert set(cp.flood(c)) == set(g)
        b.flood((b.color + 1) % 5)


def test_win_detection():
    b = board(["000", "000", "001"])
    assert not b.solved()
    b.flood(1)
    assert b.solved() and b.colors_left() == set()


def test_distance_from_corner_is_bfs_inside_region():
    b = board(["000", "110", "000"])
    d = b.distance_from_corner()
    assert d[0] == 0 and d[2] == 2 and d[8] == 4 and d[6] == 6
    assert 3 not in d


def test_random_board_uses_every_colour_and_is_deterministic():
    for size, colors in ((6, 3), (14, 8), (26, 16)):
        a = random_board(size, colors, random.Random(5))
        b = random_board(size, colors, random.Random(5))
        assert a.cells == b.cells
        assert set(a.cells) == set(range(colors))
        assert not a.solved()
    with pytest.raises(ValueError):
        random_board(5, 17, random.Random(1))


def test_level_table_grows_and_caps_at_16_colours():
    assert MAX_COLORS == 16
    sizes = [d.size for d in LEVEL_TABLE]
    colors = [d.colors for d in LEVEL_TABLE]
    assert sizes == sorted(sizes) and colors == sorted(colors)
    assert colors[0] == 3 and max(colors) == 16 and LEVEL_TABLE[-1].colors == 16
    assert sizes[0] == 6 and sizes[-1] == 26
    slacks = [d.slack for d in LEVEL_TABLE]
    assert slacks == sorted(slacks, reverse=True)
    assert len(theme.FLOOD_COLORS) == 16 and len(set(theme.FLOOD_COLORS)) == 16
    assert len(theme.COLOR_KEYS) == 16


def test_endless_levels_repeat_last_row():
    assert level_def(LAST_TABLE_LEVEL + 1) == LEVEL_TABLE[-1]
    assert level_def(500) == LEVEL_TABLE[-1]
    assert level_def(0) == LEVEL_TABLE[0]


def test_palette_colours_are_distinct_enough():
    cols = theme.FLOOD_COLORS
    for i in range(16):
        for j in range(i + 1, 16):
            d = sum((a - b) ** 2 for a, b in zip(cols[i], cols[j])) ** 0.5
            assert d > 40, (i, j, d)


@pytest.mark.parametrize("level", [1, 4, 8, 12, 16, 20, 23])
def test_solver_solutions_are_valid(level):
    ld = level_def(level)
    for seed in range(3):
        b = random_board(ld.size, ld.colors, random.Random(seed))
        for sol in (solve(b, 1), solve(b, 2), solve_beam(b), solve_best(b)):
            assert verify_solution(b, sol)
            assert all(sol[k] != sol[k + 1] for k in range(len(sol) - 1))
        assert len(solve_best(b)) <= min(len(solve(b, 1)), len(solve(b, 2)))


def test_solver_par_is_sane():
    # every move must remove a colour or grow the area, so par >= colours - 1; and it is far from silly
    for level in (3, 9, 15, 22):
        ld = level_def(level)
        b = random_board(ld.size, ld.colors, random.Random(level))
        par = len(solve_best(b))
        assert ld.colors - 1 <= par <= ld.size * ld.colors // 2


def test_solver_optimal_on_tiny_board():
    b = board(["01", "21"])
    assert len(solve_best(b)) == 2


def test_move_limit_always_leaves_room():
    for ld in LEVEL_TABLE:
        for par in (1, 5, 20, 90):
            lim = move_limit(par, ld)
            assert lim >= par + 1
            assert lim <= par * 1.4 + 1


def test_new_level_is_winnable_within_limit():
    for n in (1, 6, 11, 18, 24):
        lv = new_level(n, seed=n)
        assert lv.limit > lv.par == len(lv.solution)
        replay = Level(n, lv.board.copy(), lv.par, lv.limit)
        for c in lv.solution:
            assert replay.play(c) is not None
        assert replay.won and not replay.lost and replay.moves <= replay.limit


def test_losing_when_moves_run_out():
    lv = new_level(5, seed=1)
    b = lv.board
    while not lv.over:
        lv.play((b.color + 1) % b.colors if b.color != 0 else 1 % b.colors)
        # alternate between two colours so the board is (almost surely) not finished
        lv.play(0 if b.color != 0 else 1)
    assert lv.moves == lv.limit and lv.lost and not lv.won
    assert lv.play(2) is None          # no moves after the end
    assert lv.moves == lv.limit


def test_same_colour_move_is_refused_and_not_counted():
    lv = new_level(2, seed=4)
    assert lv.play(lv.board.color) is None
    assert lv.moves == 0


def test_warning_threshold():
    assert warning_threshold(8) == 3
    assert warning_threshold(100) == 15
    lv = new_level(9, seed=2)
    lv.moves = lv.limit - warning_threshold(lv.limit) - 1
    assert not lv.warning()
    lv.moves += 1
    assert lv.warning()


def test_scoring():
    ld = level_def(5)                       # 10x10, 5 colours
    s = score_breakdown(ld, moves=14, limit=18, par=14)
    assert s == {"base": 500, "unused": 4 * 35, "par": 250, "total": 500 + 140 + 250}
    beat = score_breakdown(ld, 12, 18, 14)
    assert beat["par"] == 250 + 2 * 125 and beat["total"] > s["total"]
    worse = score_breakdown(ld, 18, 18, 14)
    assert worse["unused"] == 0 and worse["par"] == 0 and worse["total"] == 500
    assert score_breakdown(level_def(23), 90, 94, 87)["base"] == 26 * 16 * 10


def test_assist_removes_par_bonus_and_stars():
    ld = level_def(5)
    plain = score_breakdown(ld, 12, 18, 14)
    helped = score_breakdown(ld, 12, 18, 14, assisted=True)
    assert helped["par"] == 0 and helped["base"] == plain["base"] and helped["unused"] == plain["unused"]
    assert helped["total"] == plain["total"] - plain["par"]
    assert stars(10, 18, 14, assisted=True) == 0


def test_stars():
    assert stars(14, 18, 14) == 3
    assert stars(10, 18, 14) == 3
    assert stars(16, 18, 14) == 2
    assert stars(17, 18, 14) == 1
    assert stars(8, 8, 6) in (1, 2)
