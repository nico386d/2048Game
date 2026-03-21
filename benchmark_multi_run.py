#!/usr/bin/env python3
"""
Benchmark script to run each depth multiple times and collect statistics.
Runs depths 2-5, each 10 times, measuring score and time.
"""

import time
import statistics
from typing import List, Dict
from game_engine import SIZE, new_grid, add_random_tile, can_move, apply_move
from ai_player import AIConfig, best_move


def run_game(config: AIConfig) -> Dict:
    """Run a single game and return score, num_moves, max_tile, and time."""
    grid = new_grid()
    grid = add_random_tile(grid)
    grid = add_random_tile(grid)
    
    score = 0
    num_moves = 0
    move_times: List[float] = []
    
    while can_move(grid):
        start = time.perf_counter()
        move = best_move(grid, config)
        elapsed = time.perf_counter() - start
        move_times.append(elapsed)
        
        result = apply_move(grid, move)
        score += result.score_gain
        
        if result.changed:
            grid = add_random_tile(result.grid)
            num_moves += 1
        else:
            break
    
    max_tile = max(grid[r][c] for r in range(SIZE) for c in range(SIZE))
    total_time = sum(move_times)
    avg_time_per_move = total_time / num_moves if num_moves > 0 else 0
    
    return {
        "score": score,
        "num_moves": num_moves,
        "max_tile": max_tile,
        "time_total": total_time,
        "avg_time_per_move": avg_time_per_move
    }


def benchmark_depth(depth: int, num_runs: int = 10) -> Dict:
    """Run multiple games at a specific depth and return statistics."""
    config = AIConfig(depth=depth)
    results = []
    
    print(f"\n{'='*60}")
    print(f"Benchmarking Depth {depth} ({num_runs} runs)")
    print(f"{'='*60}")
    
    for run in range(1, num_runs + 1):
        result = run_game(config)
        results.append(result)
        print(f"Run {run:2d}: Score={result['score']:6d}, Moves={result['num_moves']:3d}, "
              f"Max Tile={result['max_tile']:5d}, Time={result['time_total']:7.2f}s, "
              f"Avg/Move={result['avg_time_per_move']:6.4f}s")
    
    # Calculate statistics
    scores = [r["score"] for r in results]
    moves = [r["num_moves"] for r in results]
    times = [r["time_total"] for r in results]
    times_per_move = [r["avg_time_per_move"] for r in results]
    max_tiles = [r["max_tile"] for r in results]
    
    stats = {
        "depth": depth,
        "num_runs": num_runs,
        "score_mean": statistics.mean(scores),
        "score_stdev": statistics.stdev(scores) if len(scores) > 1 else 0,
        "score_min": min(scores),
        "score_max": max(scores),
        "moves_mean": statistics.mean(moves),
        "moves_stdev": statistics.stdev(moves) if len(moves) > 1 else 0,
        "time_mean": statistics.mean(times),
        "time_stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "time_per_move_mean": statistics.mean(times_per_move),
        "time_per_move_stdev": statistics.stdev(times_per_move) if len(times_per_move) > 1 else 0,
        "max_tile_mean": statistics.mean(max_tiles),
    }
    
    return stats


def main():
    """Run benchmarks for depths 2-5."""
    depths = [2, 3, 4, 5]
    runs_per_depth = 10
    
    all_stats = []
    
    for depth in depths:
        try:
            stats = benchmark_depth(depth, runs_per_depth)
            all_stats.append(stats)
        except KeyboardInterrupt:
            print(f"\nInterrupted at depth {depth}")
            break
    
    # Summary table
    print(f"\n\n{'='*100}")
    print("SUMMARY STATISTICS")
    print(f"{'='*100}")
    print(f"{'Depth':<6} {'Score':>10} {'±':>4} {'Moves':>8} {'±':>4} {'Time(s)':>10} {'±':>6} {'Time/Move':>8}")
    print(f"{'-'*100}")
    
    for stats in all_stats:
        print(f"{stats['depth']:<6} {stats['score_mean']:>10.0f} {stats['score_stdev']:>4.0f} "
              f"{stats['moves_mean']:>8.1f} {stats['moves_stdev']:>4.1f} "
              f"{stats['time_mean']:>10.2f} {stats['time_stdev']:>6.2f} "
              f"{stats['time_per_move_mean']:>8.4f}")
    
    # Save to file
    with open("BENCHMARK_MULTI_RUN.txt", "w") as f:
        f.write("BENCHMARK RESULTS - Multiple Runs Per Depth\n")
        f.write(f"Runs per depth: {runs_per_depth}\n")
        f.write(f"{'='*100}\n\n")
        
        for stats in all_stats:
            f.write(f"Depth {stats['depth']}:\n")
            f.write(f"  Score:        {stats['score_mean']:.0f} ± {stats['score_stdev']:.0f} (min={stats['score_min']}, max={stats['score_max']})\n")
            f.write(f"  Moves:        {stats['moves_mean']:.1f} ± {stats['moves_stdev']:.1f}\n")
            f.write(f"  Time Total:   {stats['time_mean']:.2f} ± {stats['time_stdev']:.2f} seconds\n")
            f.write(f"  Time/Move:    {stats['time_per_move_mean']:.4f} ± {stats['time_per_move_stdev']:.4f} seconds\n")
            f.write(f"  Max Tile:     {stats['max_tile_mean']:.0f} (average)\n\n")
    
    print(f"\nResults saved to BENCHMARK_MULTI_RUN.txt")


if __name__ == "__main__":
    main()
