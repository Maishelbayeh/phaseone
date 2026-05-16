from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from sat_generator import load_instance_formula_from_file
from solvers.registry import build_solver_registry


ROOT = Path(__file__).resolve().parent
INSTANCE_DIR = ROOT.parent / "data" / "instances"
OUTPUT_PATH = ROOT / "results" / "comparison" / "sa_ga_swarm_memetic_swarmsa_medium.json"
SOLVER_KEYS = [
    "simulated_annealing",
    "genetic_algorithm",
    "binary_swarm_solver",
    "memetic_ga_sa",
    "swarm_sa_solver",
]
INSTANCE_NAMES = [
    "3sat_n100_r3.json",
    "3sat_n100_r4.3.json",
    "3sat_n100_r6.json",
    "3sat_n150_r3.json",
    "3sat_n150_r4.3.json",
    "3sat_n150_r6.json",
    "3sat_n200_r3.json",
    "3sat_n200_r4.3.json",
    "3sat_n200_r6.json",
]
BASE_SEED = 101


def meta(instance_name: str) -> tuple[int, float]:
    match = re.match(r"3sat_n(\d+)_r([0-9.]+)\.json", instance_name)
    assert match is not None
    return int(match.group(1)), float(match.group(2))


def solver_config(key: str, n: int, seed: int) -> Dict[str, Any]:
    if key == "simulated_annealing":
        return {
            "max_iterations": max(3000, 50 * n),
            "initial_temperature": 12.0,
            "cooling_rate": 0.997,
            "min_temperature": 0.001,
            "random_seed": seed,
        }
    if key == "genetic_algorithm":
        return {
            "population_size": 56,
            "max_generations": 220,
            "crossover_rate": 0.88,
            "mutation_rate": min(0.03, 2.0 / max(n, 1)),
            "elite_count": 2,
            "crossover_mode": "two_point",
            "tournament_size": 3,
            "local_search_every": 5,
            "annealing_temperature": 2.2,
            "annealing_cooling": 0.992,
            "annealing_trials": 2,
            "stagnation_limit": 24,
            "reheat_multiplier": 1.5,
            "random_seed": seed,
        }
    if key == "binary_swarm_solver":
        return {
            "population_size": 56,
            "max_iterations": max(280, 2 * n),
            "w_inertia_start": 0.9,
            "w_inertia_end": 0.4,
            "c_cognitive": 1.35,
            "c_social": 2.05,
            "velocity_clamp": 4.0,
            "local_search_every": 10,
            "local_search_top_k": 2,
            "stagnation_limit": 35,
            "max_restarts": 2,
            "annealing_temperature": 2.2,
            "annealing_cooling": 0.995,
            "annealing_trials": 3,
            "sa_refine_iterations": min(240, max(80, 2 * n)),
            "reheat_multiplier": 1.5,
            "diversify_fraction": 0.3,
            "random_seed": seed,
        }
    if key == "memetic_ga_sa":
        return {
            "population_size": 56,
            "max_generations": 220,
            "crossover_rate": 0.88,
            "mutation_rate": min(0.04, 2.0 / max(n, 1)),
            "elite_count": 2,
            "tournament_size": 3,
            "local_search_every": 10,
            "local_search_top_k": 2,
            "sa_max_iterations": min(900, max(350, 4 * n)),
            "sa_patience": max(60, n // 2),
            "stagnation_limit": 28,
            "restart_fraction": 0.2,
            "lamarckian": True,
            "random_seed": seed,
        }
    if key == "swarm_sa_solver":
        return {
            "population_size": 52,
            "max_iterations": 220 if n <= 200 else 280,
            "w_inertia_start": 0.92,
            "w_inertia_end": 0.45,
            "c_cognitive": 1.25,
            "c_social": 2.1,
            "velocity_clamp": 4.0,
            "local_search_every": 10,
            "local_search_top_k": 1,
            "sa_max_iterations": min(450, max(180, 2 * n)),
            "sa_patience": max(60, n // 2),
            "stagnation_limit": 24,
            "max_restarts": 0,
            "diversify_fraction": 0.25,
            "lamarckian": True,
            "random_seed": seed,
        }
    return {"random_seed": seed}


def summarize(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["algorithm_name"], []).append(row)

    summary: List[Dict[str, Any]] = []
    for algorithm_name, algo_rows in grouped.items():
        summary.append(
            {
                "algorithm_name": algorithm_name,
                "runs": len(algo_rows),
                "mean_best_satisfied": mean(r["best_satisfied"] for r in algo_rows),
                "max_best_satisfied": max(r["best_satisfied"] for r in algo_rows),
                "mean_satisfaction_rate": mean(r["satisfaction_rate"] for r in algo_rows),
                "mean_runtime_seconds": mean(r["runtime_seconds"] for r in algo_rows),
                "mean_iterations_used": mean(r["iterations_used"] for r in algo_rows),
                "full_satisfy_count": sum(1 for r in algo_rows if r["fully_satisfied"]),
            }
        )
    summary.sort(key=lambda row: (-row["mean_satisfaction_rate"], row["mean_runtime_seconds"]))
    return summary


def main() -> None:
    registry = build_solver_registry()
    per_run: List[Dict[str, Any]] = []

    for instance_name in INSTANCE_NAMES:
        formula = load_instance_formula_from_file(INSTANCE_DIR / instance_name)
        n, ratio = meta(instance_name)
        for offset, key in enumerate(SOLVER_KEYS):
            seed = BASE_SEED + offset * 100_003 + n * 37 + int(round(ratio * 100))
            result = registry[key].solve(formula, solver_config(key, n, seed))
            row = {
                "instance": instance_name,
                "n": n,
                "ratio": ratio,
                "solver_key": key,
                "algorithm_name": result.algorithm_name,
                "best_satisfied": result.best_satisfied_clauses,
                "total_clauses": result.total_clauses,
                "satisfaction_rate": result.satisfaction_rate,
                "runtime_seconds": result.runtime_seconds,
                "iterations_used": result.iterations_used,
                "fully_satisfied": result.fully_satisfied,
                "parameter_summary": result.parameter_summary,
                "best_history": list(result.best_history),
                "runtime_history": list(result.runtime_history),
            }
            per_run.append(row)
            print(
                f"{instance_name} | {result.algorithm_name} | "
                f"{result.best_satisfied_clauses}/{result.total_clauses} | "
                f"{result.runtime_seconds:.3f}s | iter={result.iterations_used}",
                flush=True,
            )

    by_ratio: Dict[str, List[Dict[str, Any]]] = {}
    for ratio in sorted({row["ratio"] for row in per_run}):
        by_ratio[str(ratio)] = summarize([row for row in per_run if row["ratio"] == ratio])

    by_n: Dict[str, List[Dict[str, Any]]] = {}
    for n in sorted({row["n"] for row in per_run}):
        by_n[str(n)] = summarize([row for row in per_run if row["n"] == n])

    output = {
        "solver_keys": SOLVER_KEYS,
        "overall": summarize(per_run),
        "by_ratio": by_ratio,
        "by_n": by_n,
        "per_run": per_run,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"SAVED {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
