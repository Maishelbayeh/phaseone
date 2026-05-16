from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from sat_generator import load_instance_formula_from_file
from solvers.registry import build_solver_registry


INSTANCE_DIR = Path(__file__).resolve().parent.parent / "data" / "instances"
OUTPUT_PATH = Path(__file__).resolve().parent / "results" / "comparison" / "full_benchmark_results.json"
SOLVER_KEYS = [
    "hill_climbing",
    "simulated_annealing",
    "genetic_algorithm",
    "binary_swarm_solver",
    "hybrid_bsgo_ga",
]
BASE_SEED = 101


def benchmark_config(solver_key: str, n: int, seed: int) -> Dict[str, Any]:
    if solver_key == "hill_climbing":
        if n <= 100:
            iter_cap = 500
            restarts = 5
        elif n <= 200:
            iter_cap = 350
            restarts = 4
        else:
            iter_cap = 200
            restarts = 2
        return {
            "max_iterations_per_restart": iter_cap,
            "max_random_restarts": restarts,
            "random_seed": seed,
        }
    if solver_key == "simulated_annealing":
        return {
            "max_iterations": 2500 if n <= 100 else 4000 if n <= 200 else 6000,
            "initial_temperature": 12.0,
            "cooling_rate": 0.997,
            "min_temperature": 0.001,
            "random_seed": seed,
        }
    if solver_key == "genetic_algorithm":
        return {
            "population_size": 48 if n <= 100 else 56 if n <= 200 else 64,
            "max_generations": 180 if n <= 100 else 220 if n <= 200 else 240,
            "crossover_rate": 0.88,
            "mutation_rate": min(0.03, 2.0 / max(n, 1)),
            "elite_count": 2,
            "crossover_mode": "two_point",
            "tournament_size": 3,
            "random_seed": seed,
        }
    if solver_key == "binary_swarm_solver":
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
            "c_parameter": 0.9,
            "random_seed": seed,
        }
    if solver_key == "hybrid_bsgo_ga":
        return {
            "population_size": 48 if n <= 100 else 56 if n <= 200 else 60,
            "max_iterations": 160 if n <= 100 else 200 if n <= 200 else 220,
            "crossover_rate": 0.92,
            "mutation_rate": min(0.04, 2.0 / max(n, 1)),
            "c_coefficient": 0.72,
            "tournament_size": 3,
            "stagnation_limit": 30,
            "local_search_elite": True,
            "random_seed": seed,
        }
    return {"random_seed": seed}


def summarize_group(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    summary.sort(key=lambda r: (-r["mean_satisfaction_rate"], r["mean_runtime_seconds"]))
    return summary


def extract_meta(instance_name: str) -> Dict[str, Any]:
    match = re.match(r"3sat_n(\d+)_r([0-9.]+)\.json", instance_name)
    if not match:
        return {"n": None, "ratio": None}
    return {"n": int(match.group(1)), "ratio": float(match.group(2))}


def main() -> None:
    registry = build_solver_registry()
    instance_paths = sorted(INSTANCE_DIR.glob("3sat_*.json"))
    per_run: List[Dict[str, Any]] = []

    for index, instance_path in enumerate(instance_paths):
        formula = load_instance_formula_from_file(instance_path)
        meta = extract_meta(instance_path.name)
        n = formula.num_variables
        for solver_offset, solver_key in enumerate(SOLVER_KEYS):
            solver = registry[solver_key]
            seed = BASE_SEED + index * 997 + solver_offset * 100_003
            config = benchmark_config(solver_key, n, seed)
            result = solver.solve(formula, config)
            per_run.append(
                {
                    "instance": instance_path.name,
                    "n": meta["n"],
                    "ratio": meta["ratio"],
                    "algorithm_name": result.algorithm_name,
                    "solver_key": solver_key,
                    "seed": seed,
                    "best_satisfied": result.best_satisfied_clauses,
                    "total_clauses": result.total_clauses,
                    "satisfaction_rate": result.satisfaction_rate,
                    "runtime_seconds": result.runtime_seconds,
                    "iterations_used": result.iterations_used,
                    "fully_satisfied": result.fully_satisfied,
                    "parameter_summary": result.parameter_summary,
                }
            )
            print(
                f"{instance_path.name} | {result.algorithm_name} | "
                f"{result.best_satisfied_clauses}/{result.total_clauses} | "
                f"{result.runtime_seconds:.3f}s",
                flush=True,
            )

    by_instance: Dict[str, List[Dict[str, Any]]] = {}
    for instance_path in instance_paths:
        subset = [row for row in per_run if row["instance"] == instance_path.name]
        by_instance[instance_path.name] = summarize_group(subset)

    by_n: Dict[str, List[Dict[str, Any]]] = {}
    for n_value in sorted({row["n"] for row in per_run}):
        subset = [row for row in per_run if row["n"] == n_value]
        by_n[str(n_value)] = summarize_group(subset)

    by_ratio: Dict[str, List[Dict[str, Any]]] = {}
    for ratio_value in sorted({row["ratio"] for row in per_run}):
        subset = [row for row in per_run if row["ratio"] == ratio_value]
        by_ratio[str(ratio_value)] = summarize_group(subset)

    overall = summarize_group(per_run)
    output = {
        "instance_count": len(instance_paths),
        "solver_keys": SOLVER_KEYS,
        "overall": overall,
        "by_instance": by_instance,
        "by_n": by_n,
        "by_ratio": by_ratio,
        "per_run": per_run,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUTPUT_PATH}")
    print(json.dumps({"overall": overall, "by_n": by_n, "by_ratio": by_ratio}, indent=2))


if __name__ == "__main__":
    main()
