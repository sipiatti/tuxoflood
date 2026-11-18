"""TuxoFlood rules: board, flooding, generator, solver, level table, scoring (pure Python, no pygame).

The player's flooded region starts in the top-left corner.  Picking a colour
recolours the region; every orthogonally adjacent cell of that colour joins it.
The level is won when the whole board is one colour, and lost when the move
limit is used up before that.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

MAX_COLORS = 16


# ------------------------------------------------------------------ levels
@dataclass(frozen=True)
class LevelDef:
    size: int       # board is size x size
    colors: int     # number of colours used
    slack: float    # extra moves on top of the solver's solution, as a fraction


# (size, colours, slack).  Board size and colour count grow together; the
# spare moves shrink from +40 % to +8 %.  After the last row the game goes
# on endlessly with the last row's settings (new board every level).
LEVEL_TABLE: tuple[LevelDef, ...] = tuple(LevelDef(*row) for row in (
    (6, 3, 0.40), (7, 3, 0.38), (8, 4, 0.36), (9, 4, 0.34),
    (10, 5, 0.32), (11, 5, 0.30), (12, 6, 0.28), (13, 6, 0.26),
    (14, 7, 0.24), (14, 8, 0.22), (15, 8, 0.20), (16, 9, 0.19),
    (17, 10, 0.18), (18, 10, 0.17), (18, 11, 0.16), (19, 12, 0.15),
    (20, 12, 0.14), (21, 13, 0.13), (22, 14, 0.12), (23, 14, 0.11),
    (24, 15, 0.10), (25, 16, 0.09), (26, 16, 0.08),
))
LAST_TABLE_LEVEL = len(LEVEL_TABLE)


def level_def(level: int) -> LevelDef:
    """Level numbers start at 1; levels beyond the table repeat the last row (endless)."""
    level = max(1, int(level))
    return LEVEL_TABLE[min(level, LAST_TABLE_LEVEL) - 1]


def move_limit(solver_moves: int, ld: LevelDef) -> int:
    """Maximum moves allowed: the solver's solution plus a shrinking slack (always ≥ +1)."""
    return solver_moves + max(1, round(solver_moves * ld.slack))


# ------------------------------------------------------------------ board
class Board:
    """A size×size grid of colour indices (0..colors-1) with the flood region anchored at (0, 0)."""

    def __init__(self, cells: list[int], size: int, colors: int):
        if len(cells) != size * size:
            raise ValueError("cells must have size*size entries")
        self.size = size
        self.colors = colors
        self.cells = list(cells)
        self.region: set[int] = set()
        self._grow()

    # ---- geometry
    def neighbors(self, i: int):
        n = self.size
        r, c = divmod(i, n)
        if r > 0:
            yield i - n
        if r < n - 1:
            yield i + n
        if c > 0:
            yield i - 1
        if c < n - 1:
            yield i + 1

    def at(self, r: int, c: int) -> int:
        return self.cells[r * self.size + c]

    @property
    def color(self) -> int:
        """Current colour of the flooded region."""
        return self.cells[0]

    # ---- flooding
    def _grow(self) -> list[int]:
        """Add every cell connected to the region with the region colour; returns the new cells (BFS order)."""
        col = self.cells[0]
        if not self.region:
            self.region = {0}
            stack = [0]
            added = [0]
        else:
            stack = list(self.region)
            added = []
        region = self.region
        cells = self.cells
        while stack:
            i = stack.pop()
            for j in self.neighbors(i):
                if j not in region and cells[j] == col:
                    region.add(j)
                    added.append(j)
                    stack.append(j)
        return added

    def gain(self, color: int) -> list[int]:
        """Cells that picking ``color`` would add to the region (without changing the board)."""
        if color == self.color:
            return []
        region, cells = self.region, self.cells
        seen: set[int] = set()
        out: list[int] = []
        stack: list[int] = []
        for i in region:
            for j in self.neighbors(i):
                if j not in region and j not in seen and cells[j] == color:
                    seen.add(j)
                    stack.append(j)
        out.extend(stack)
        while stack:
            i = stack.pop()
            for j in self.neighbors(i):
                if j not in region and j not in seen and cells[j] == color:
                    seen.add(j)
                    out.append(j)
                    stack.append(j)
        return out

    def flood(self, color: int) -> list[int]:
        """Recolour the region to ``color``; returns the newly absorbed cells. No-op for the current colour."""
        if not 0 <= color < self.colors:
            raise ValueError("bad colour")
        if color == self.color:
            return []
        for i in self.region:
            self.cells[i] = color
        return self._grow()

    def solved(self) -> bool:
        return len(self.region) == len(self.cells)

    def colors_left(self) -> set[int]:
        return {self.cells[i] for i in range(len(self.cells)) if i not in self.region}

    def distance_from_corner(self) -> dict[int, int]:
        """BFS distance (inside the region) from the top-left cell, for the wave animation."""
        dist = {0: 0}
        frontier = [0]
        while frontier:
            nxt = []
            for i in frontier:
                for j in self.neighbors(i):
                    if j in self.region and j not in dist:
                        dist[j] = dist[i] + 1
                        nxt.append(j)
            frontier = nxt
        return dist

    def copy(self) -> "Board":
        b = Board.__new__(Board)
        b.size, b.colors, b.cells, b.region = self.size, self.colors, list(self.cells), set(self.region)
        return b


def random_board(size: int, colors: int, rng: random.Random) -> Board:
    """Uniform random colours; every colour is guaranteed to appear and the board never starts solved."""
    if not 2 <= colors <= MAX_COLORS:
        raise ValueError("colours must be 2..16")
    n = size * size
    while True:
        cells = [rng.randrange(colors) for _ in range(n)]
        missing = [c for c in range(colors) if c not in cells]
        for c in missing:
            cells[rng.randrange(1, n)] = c
        if len(set(cells)) == colors:
            b = Board(cells, size, colors)
            if not b.solved():
                return b


# ------------------------------------------------------------------ solver
class _Graph:
    """Board compressed into same-colour connected components (fast for the solver)."""

    def __init__(self, board: Board):
        n = len(board.cells)
        comp = [-1] * n
        self.color: list[int] = []
        self.sizes: list[int] = []
        for s in range(n):
            if comp[s] >= 0:
                continue
            cid = len(self.color)
            col = board.cells[s]
            comp[s] = cid
            stack, cnt = [s], 0
            while stack:
                i = stack.pop()
                cnt += 1
                for j in board.neighbors(i):
                    if comp[j] < 0 and board.cells[j] == col:
                        comp[j] = cid
                        stack.append(j)
            self.color.append(col)
            self.sizes.append(cnt)
        self.adj: list[set[int]] = [set() for _ in self.color]
        for i in range(n):
            for j in board.neighbors(i):
                if comp[i] != comp[j]:
                    self.adj[comp[i]].add(comp[j])
        self.start = comp[0]
        self.colors = board.colors


def _frontier(g: _Graph, flooded: set[int]) -> dict[int, set[int]]:
    fr: dict[int, set[int]] = {}
    for a in flooded:
        for b in g.adj[a]:
            if b not in flooded:
                fr.setdefault(g.color[b], set()).add(b)
    return fr


def _apply(g: _Graph, flooded: set[int], fr: dict[int, set[int]], color: int):
    gained = fr.get(color, set())
    nf = set(flooded) | gained
    nfr = {c: set(s) for c, s in fr.items() if c != color}
    for b in gained:
        for x in g.adj[b]:
            if x not in nf:
                nfr.setdefault(g.color[x], set()).add(x)
    return nf, nfr, sum(g.sizes[b] for b in gained)


def _remaining_colors(g: _Graph, flooded: set[int]) -> dict[int, int]:
    out: dict[int, int] = {}
    for cid, col in enumerate(g.color):
        if cid not in flooded:
            out[col] = out.get(col, 0) + g.sizes[cid]
    return out


def solve(board: Board, depth: int = 2, max_moves: int = 10_000) -> list[int]:
    """Good (not optimal) solution: a list of colours that floods the whole board.

    Strategy per move: if some colour can be eliminated from the board entirely,
    do it (largest first); otherwise pick the colour whose best ``depth``-move
    continuation absorbs the most cells, preferring larger frontiers.
    """
    g = _Graph(board)
    flooded = {g.start}
    fr = _frontier(g, flooded)
    total = len(g.color)
    moves: list[int] = []
    while len(flooded) < total and len(moves) < max_moves:
        remaining = _remaining_colors(g, flooded)
        # colour elimination: every remaining component of that colour is on the frontier
        elim = [c for c, s in fr.items() if sum(g.sizes[b] for b in s) == remaining.get(c, -1)]
        if elim:
            best = max(elim, key=lambda c: (remaining[c], -c))
        else:
            best, best_key = None, None
            for c in fr:
                nf, nfr, gained = _apply(g, flooded, fr, c)
                look = 0
                if depth > 1 and nfr:
                    look = max(_apply(g, nf, nfr, c2)[2] for c2 in nfr)
                key = (gained + look, gained, sum(len(s) for s in nfr.values()), -c)
                if best_key is None or key > best_key:
                    best, best_key = c, key
        flooded, fr, _ = _apply(g, flooded, fr, best)
        moves.append(best)
    return moves


def solve_beam(board: Board, width: int = 8) -> list[int]:
    """Beam search: keeps the ``width`` most promising positions after every move.

    A position is rated by the cells flooded so far minus 8 per colour still on
    the board; colour elimination is always taken when possible."""
    g = _Graph(board)
    total = len(g.color)
    start = {g.start}
    states = [(start, _frontier(g, start), [], g.sizes[g.start])]
    for _ in range(10_000):
        for flooded, _fr, moves, _cnt in states:
            if len(flooded) == total:
                return moves
        cand = []
        for flooded, fr, moves, cnt in states:
            rem = _remaining_colors(g, flooded)
            elim = [c for c, s in fr.items() if sum(g.sizes[b] for b in s) == rem.get(c, -1)]
            options = [max(elim, key=lambda c: (rem[c], -c))] if elim else sorted(fr)
            for c in options:
                nf, nfr, gained = _apply(g, flooded, fr, c)
                left = len(_remaining_colors(g, nf))
                cand.append((cnt + gained - 8 * left, sum(len(x) for x in nfr.values()), -c, nf, nfr, moves + [c],
                             cnt + gained))
        cand.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        seen: set[frozenset] = set()
        states = []
        for _k, _f, _c, nf, nfr, mv, cnt in cand:
            key = frozenset(nf)
            if key in seen:
                continue
            seen.add(key)
            states.append((nf, nfr, mv, cnt))
            if len(states) >= width:
                break
    raise RuntimeError("beam search did not finish")  # pragma: no cover


def solve_best(board: Board) -> list[int]:
    """Shortest of a few solver variants (greedy, 2-step lookahead, beam search).
    Used for the move limit and the par."""
    sols = [solve(board, 1), solve(board, 2), solve_beam(board)]
    return min(sols, key=len)


def verify_solution(board: Board, moves: list[int]) -> bool:
    b = board.copy()
    for m in moves:
        b.flood(m)
    return b.solved()


# ------------------------------------------------------------------ level instance
@dataclass
class Level:
    number: int
    board: Board
    par: int            # moves of the solver's solution
    limit: int          # maximum moves allowed
    solution: list[int] = field(default_factory=list)
    moves: int = 0

    @property
    def defn(self) -> LevelDef:
        return level_def(self.number)

    @property
    def moves_left(self) -> int:
        return self.limit - self.moves

    @property
    def won(self) -> bool:
        return self.board.solved()

    @property
    def lost(self) -> bool:
        return not self.won and self.moves >= self.limit

    @property
    def over(self) -> bool:
        return self.won or self.lost

    def play(self, color: int) -> list[int] | None:
        """Make a move. Returns the absorbed cells, or None if the move is not allowed
        (game over, or the colour is the region's current colour)."""
        if self.over or color == self.board.color or not 0 <= color < self.board.colors:
            return None
        self.moves += 1
        return self.board.flood(color)

    def warning(self) -> bool:
        """True when few moves are left (red counter + warning sound)."""
        return not self.over and self.moves_left <= warning_threshold(self.limit)


def warning_threshold(limit: int) -> int:
    return max(3, round(limit * 0.15))


def new_level(number: int, seed: int | None = None) -> Level:
    ld = level_def(number)
    rng = random.Random(seed)
    board = random_board(ld.size, ld.colors, rng)
    sol = solve_best(board)
    assert verify_solution(board, sol)
    return Level(number, board, len(sol), move_limit(len(sol), ld), sol)


# ------------------------------------------------------------------ scoring
def score_breakdown(ld: LevelDef, moves: int, limit: int, par: int, assisted: bool = False) -> dict[str, int]:
    """Base for the board + bonus for every unused move + bonus for matching / beating the par.
    With the assist (hover preview) used there is no par bonus. Elapsed time is never part of the score."""
    base = 10 * ld.size * ld.colors
    unused = max(0, limit - moves) * (10 + 5 * ld.colors)
    par_bonus = 0
    if moves <= par and not assisted:
        par_bonus = 50 * ld.colors + (par - moves) * 25 * ld.colors
    return {"base": base, "unused": unused, "par": par_bonus, "total": base + unused + par_bonus}


def stars(moves: int, limit: int, par: int, assisted: bool = False) -> int:
    """3 ★ at or under par, 2 ★ within half of the slack, otherwise 1 ★; no stars with the assist used."""
    if assisted:
        return 0
    if moves <= par:
        return 3
    if moves <= par + max(1, (limit - par) // 2):
        return 2
    return 1
