# ai_player.py
from __future__ import annotations
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Tuple, List

from game_engine import SIZE, legal_moves, apply_move, spawn_successors

Grid = Tuple[Tuple[int, ...], ...]

SNAKE_WEIGHTS = (
    (4**15, 4**14, 4**13, 4**12),
    (4**8,  4**9,  4**10,  4**11 ),
    (4**7,  4**6,  4**5,  4**4 ),
    (4**0,  4**1,  4**2,  4**3 ),
)


@dataclass
class AIConfig:
    depth: int = 3
    w_empty: float = 200.0
    w_grid: float = 1.0
    w_smooth: float = 0.05
    w_max_edge_penalty: float = 200.0  # punish max in middle


def _log2(v: int) -> float:
    return math.log(v, 2) if v > 0 else 0.0


def _count_empty(g: Grid) -> int:
    return sum(1 for r in range(SIZE) for c in range(SIZE) if g[r][c] == 0)


def _max_tile(g: Grid) -> int:
    return max(g[r][c] for r in range(SIZE) for c in range(SIZE))


def _smoothness(g: Grid) -> float:
    """
    Penalize big jumps between neighbors in log space.
    Lower is better (we subtract it in eval).
    """
    s = 0.0
    for r in range(SIZE):
        for c in range(SIZE):
            v = g[r][c]
            if v == 0:
                continue
            lv = _log2(v)
            if r + 1 < SIZE and g[r + 1][c] != 0:
                s += abs(lv - _log2(g[r + 1][c]))
            if c + 1 < SIZE and g[r][c + 1] != 0:
                s += abs(lv - _log2(g[r][c + 1]))
    return s


def _monotonicity(g: Grid) -> float:
    """
    Reward rows/cols that are consistently increasing or decreasing (in log space).
    We take the best direction per row/col.
    """
    score = 0.0

    # rows
    for r in range(SIZE):
        inc = 0.0
        dec = 0.0
        for c in range(SIZE - 1):
            a = _log2(g[r][c])
            b = _log2(g[r][c + 1])
            if a <= b:
                inc += b - a
            else:
                dec += a - b
        score -= min(inc, dec)  # lower change in one direction is better

    # cols
    for c in range(SIZE):
        inc = 0.0
        dec = 0.0
        for r in range(SIZE - 1):
            a = _log2(g[r][c])
            b = _log2(g[r + 1][c])
            if a <= b:
                inc += b - a
            else:
                dec += a - b
        score -= min(inc, dec)

    return score


def _corner_bonus(g: Grid) -> float:
    """
    Reward if max tile is in a corner.
    """
    mx = _max_tile(g)
    corners = (g[0][0], g[0][SIZE - 1], g[SIZE - 1][0], g[SIZE - 1][SIZE - 1])
    return 1.0 if mx in corners else 0.0


def evaluate(g: Grid, cfg: AIConfig) -> float:
    empty = _count_empty(g)
    gridw = _grid_weight_score(g)
    smooth = _smoothness(g)
    block = _blocking_penalty(g)

    return (
        cfg.w_grid * gridw
        + cfg.w_empty * empty
        - 5.0 * smooth
        - 200.0 * block
    )


def best_move(grid: Grid, cfg: AIConfig) -> str:
    """
    Returns one of: "L","R","U","D".
    Uses expectimax with depth-limited search.
    """

    @lru_cache(maxsize=200000)
    def exp_value(g: Grid, depth: int, player_turn: bool) -> float:
        moves = legal_moves(g)
        if depth <= 0 or not moves:
            return evaluate(g, cfg)

        if player_turn:
            # Max node: choose best move
            best = -1e18
            for m in moves:
                res = apply_move(g, m)
                # after player move -> chance node
                v = exp_value(res.grid, depth - 1, False)
                if v > best:
                    best = v
            return best
        else:
            # Chance node: average over tile spawns
            total = 0.0
            for p, g2 in spawn_successors(g):
                total += p * exp_value(g2, depth - 1, True)
            return total

    moves = legal_moves(grid)
    if not moves:
        return "L"  # arbitrary

    best_m = moves[0]
    best_v = -1e18
    for m in moves:
        res = apply_move(grid, m)
        v = exp_value(res.grid, cfg.depth - 1, False)
        if v > best_v:
            best_v = v
            best_m = m

    return best_m


# weighting

def _grid_weight_score(g: Grid) -> float:
    s = 0.0
    for r in range(SIZE):
        for c in range(SIZE):
            v = g[r][c]
            if v:
                s += SNAKE_WEIGHTS[r][c] * _log2(v)
    return s

def _max_tile_in_middle_penalty(g: Grid) -> float:
    mx = _max_tile(g)
    # edge cells = r==0 or r==3 or c==0 or c==3
    for r in range(SIZE):
        for c in range(SIZE):
            if g[r][c] == mx:
                if r in (0, SIZE-1) or c in (0, SIZE-1):
                    return 0.0
                return 1.0
    return 0.0

def _blocking_penalty(g: Grid) -> float:
    """
    Penalize when a small tile blocks a large one in snake direction.
    """
    penalty = 0.0
    for r in range(SIZE):
        for c in range(SIZE - 1):
            if g[r][c] < g[r][c + 1]:
                penalty += 1
    return penalty