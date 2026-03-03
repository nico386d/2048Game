# game_engine.py
from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Tuple

SIZE = 4
Move = str  # "L","R","U","D"

@dataclass(frozen=True)
class StepResult:
    grid: Tuple[Tuple[int, ...], ...]
    score_gain: int
    changed: bool

def new_grid() -> Tuple[Tuple[int, ...], ...]:
    return tuple(tuple(0 for _ in range(SIZE)) for _ in range(SIZE))

def to_mutable(grid: Tuple[Tuple[int, ...], ...]) -> List[List[int]]:
    return [list(row) for row in grid]

def to_immutable(grid: List[List[int]]) -> Tuple[Tuple[int, ...], ...]:
    return tuple(tuple(row) for row in grid)

def empty_cells(grid: Tuple[Tuple[int, ...], ...]) -> List[Tuple[int, int]]:
    out = []
    for r in range(SIZE):
        for c in range(SIZE):
            if grid[r][c] == 0:
                out.append((r, c))
    return out

def add_random_tile(grid: Tuple[Tuple[int, ...], ...], rng: random.Random | None = None) -> Tuple[Tuple[int, ...], ...]:
    rng = rng or random
    empties = empty_cells(grid)
    if not empties:
        return grid
    r, c = rng.choice(empties)
    val = 4 if rng.random() < 0.10 else 2
    g = to_mutable(grid)
    g[r][c] = val
    return to_immutable(g)

def can_move(grid: Tuple[Tuple[int, ...], ...]) -> bool:
    if empty_cells(grid):
        return True
    for r in range(SIZE):
        for c in range(SIZE):
            v = grid[r][c]
            if r + 1 < SIZE and grid[r + 1][c] == v:
                return True
            if c + 1 < SIZE and grid[r][c + 1] == v:
                return True
    return False

def compress_and_merge(line: List[int]) -> Tuple[List[int], int, bool]:
    original = list(line)
    nums = [x for x in line if x != 0]
    gained = 0
    merged: List[int] = []
    i = 0
    while i < len(nums):
        if i + 1 < len(nums) and nums[i] == nums[i + 1]:
            val = nums[i] * 2
            merged.append(val)
            gained += val
            i += 2
        else:
            merged.append(nums[i])
            i += 1
    merged += [0] * (SIZE - len(merged))
    return merged, gained, (merged != original)

def move_left(grid: Tuple[Tuple[int, ...], ...]) -> StepResult:
    g = to_mutable(grid)
    changed_any = False
    gained_total = 0
    for r in range(SIZE):
        merged, gained, changed = compress_and_merge(g[r])
        g[r] = merged
        gained_total += gained
        changed_any |= changed
    return StepResult(to_immutable(g), gained_total, changed_any)

def move_right(grid: Tuple[Tuple[int, ...], ...]) -> StepResult:
    g = to_mutable(grid)
    changed_any = False
    gained_total = 0
    for r in range(SIZE):
        rev = list(reversed(g[r]))
        merged, gained, changed = compress_and_merge(rev)
        merged = list(reversed(merged))
        g[r] = merged
        gained_total += gained
        changed_any |= changed
    return StepResult(to_immutable(g), gained_total, changed_any)

def move_up(grid: Tuple[Tuple[int, ...], ...]) -> StepResult:
    g = to_mutable(grid)
    changed_any = False
    gained_total = 0
    for c in range(SIZE):
        col = [g[r][c] for r in range(SIZE)]
        merged, gained, changed = compress_and_merge(col)
        for r in range(SIZE):
            g[r][c] = merged[r]
        gained_total += gained
        changed_any |= changed
    return StepResult(to_immutable(g), gained_total, changed_any)

def move_down(grid: Tuple[Tuple[int, ...], ...]) -> StepResult:
    g = to_mutable(grid)
    changed_any = False
    gained_total = 0
    for c in range(SIZE):
        col = [g[r][c] for r in range(SIZE)]
        rev = list(reversed(col))
        merged, gained, changed = compress_and_merge(rev)
        merged = list(reversed(merged))
        for r in range(SIZE):
            g[r][c] = merged[r]
        gained_total += gained
        changed_any |= changed
    return StepResult(to_immutable(g), gained_total, changed_any)

def apply_move(grid: Tuple[Tuple[int, ...], ...], move: Move) -> StepResult:
    if move == "L":
        return move_left(grid)
    if move == "R":
        return move_right(grid)
    if move == "U":
        return move_up(grid)
    if move == "D":
        return move_down(grid)
    raise ValueError(f"Unknown move: {move}")

def legal_moves(grid: Tuple[Tuple[int, ...], ...]) -> List[Move]:
    moves = []
    for m in ("L", "R", "U", "D"):
        res = apply_move(grid, m)
        if res.changed:
            moves.append(m)
    return moves

def spawn_successors(grid: Tuple[Tuple[int, ...], ...]) -> List[Tuple[float, Tuple[Tuple[int, ...], ...]]]:
    """
    Chance node successors: for each empty cell, place 2 (0.9) or 4 (0.1).
    Each empty cell chosen uniformly.
    """
    empties = empty_cells(grid)
    if not empties:
        return [(1.0, grid)]

    p_cell = 1.0 / len(empties)
    succ = []
    for (r, c) in empties:
        g2 = to_mutable(grid)
        g2[r][c] = 2
        succ.append((p_cell * 0.9, to_immutable(g2)))

        g4 = to_mutable(grid)
        g4[r][c] = 4
        succ.append((p_cell * 0.1, to_immutable(g4)))
    return succ