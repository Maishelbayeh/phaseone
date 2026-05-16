from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from sat_generator import load_instance_formula_from_file

from solvers.registry import build_solver_registry


ESTIMATED_COMPLEXITIES: Dict[str, str] = {
    "Hill Climbing": "O(I * n * m) with random restarts folded into I",
    "Simulated Annealing": "O(I * m)",
    "Tabu Search": "O(I * n * m)",
    "Hybrid BSGO-GA": "O(I * P * n * m)",
    "Genetic Algorithm": "O(I * P * m)",
    "Binary Swarm (BSGO)": "O(I * P * m)",
    "Memetic GA-SA": "O(I * P * m + R * SA * m)",
    "Swarm-SA Hybrid": "O(I * P * m + R * SA * m)",
}


def _linear_regression(x_values: Sequence[float], y_values: Sequence[float]) -> Dict[str, float]:
    if len(x_values) < 2:
        return {"slope": 0.0, "intercept": 0.0, "r2": 0.0}
    x_mean = mean(x_values)
    y_mean = mean(y_values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    if denominator == 0:
        return {"slope": 0.0, "intercept": y_mean, "r2": 0.0}
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    y_pred = [intercept + slope * x for x in x_values]
    ss_total = sum((y - y_mean) ** 2 for y in y_values)
    ss_res = sum((y - yp) ** 2 for y, yp in zip(y_values, y_pred))
    r2 = 0.0 if ss_total == 0 else 1.0 - (ss_res / ss_total)
    return {"slope": slope, "intercept": intercept, "r2": r2}


def run_empirical_scaling(
    *,
    instance_paths: Sequence[Path],
    solver_keys: Sequence[str],
    runs_per_instance: int,
    base_seed: int,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[Dict[str, Any]]:
    registry = build_solver_registry()
    rows: List[Dict[str, Any]] = []

    def log(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    def scaling_config(solver_key: str, n: int, seed: int) -> Dict[str, Any]:
        if solver_key == "hill_climbing":
            return {"max_iterations_per_restart": max(120, 4 * n), "max_random_restarts": 3, "random_seed": seed}
        if solver_key == "simulated_annealing":
            return {
                "max_iterations": max(1200, 20 * n),
                "initial_temperature": 12.0,
                "cooling_rate": 0.997,
                "min_temperature": 0.001,
                "random_seed": seed,
            }
        if solver_key == "tabu_search":
            return {"max_iterations": max(400, 8 * n), "tabu_tenure": max(8, n // 12), "random_seed": seed}
        if solver_key == "hybrid_bsgo_ga":
            return {
                "population_size": max(24, min(64, n // 2 if n > 10 else n)),
                "max_iterations": max(80, n // 2),
                "crossover_rate": 0.92,
                "mutation_rate": min(0.04, 2.0 / max(n, 1)),
                "c_coefficient": 0.72,
                "random_seed": seed,
            }
        if solver_key == "genetic_algorithm":
            return {
                "population_size": max(24, min(64, n // 2 if n > 10 else n)),
                "max_generations": max(80, n // 2),
                "crossover_rate": 0.88,
                "mutation_rate": min(0.03, 2.0 / max(n, 1)),
                "elite_count": 2,
                "random_seed": seed,
            }
        if solver_key == "binary_swarm_solver":
            return {
                "population_size": max(32, min(72, max(24, n // 2 if n > 10 else n))),
                "max_iterations": max(120, n),
                "c_parameter": 0.9,
                "random_seed": seed,
            }
        if solver_key == "memetic_ga_sa":
            return {
                "population_size": max(24, min(56, n // 2 if n > 10 else n)),
                "max_generations": max(90, n // 2),
                "crossover_rate": 0.88,
                "mutation_rate": min(0.04, 2.0 / max(n, 1)),
                "elite_count": 2,
                "tournament_size": 3,
                "local_search_every": 12,
                "local_search_top_k": 2,
                "sa_max_iterations": min(500, max(180, 3 * n)),
                "sa_patience": max(50, n // 3),
                "stagnation_limit": 24,
                "restart_fraction": 0.2,
                "random_seed": seed,
            }
        if solver_key == "swarm_sa_solver":
            return {
                "population_size": max(24, min(52, n // 2 if n > 10 else n)),
                "max_iterations": max(90, n),
                "w_inertia_start": 0.92,
                "w_inertia_end": 0.45,
                "c_cognitive": 1.25,
                "c_social": 2.1,
                "velocity_clamp": 4.0,
                "local_search_every": 12,
                "local_search_top_k": 1,
                "sa_max_iterations": min(320, max(140, 2 * n)),
                "sa_patience": max(50, n // 3),
                "stagnation_limit": 22,
                "max_restarts": 0,
                "diversify_fraction": 0.25,
                "random_seed": seed,
            }
        return {"random_seed": seed}

    for solver_index, solver_key in enumerate(solver_keys):
        solver = registry.get(solver_key)
        if solver is None:
            continue
        log(f"[Scaling] Solver start: {solver.algorithm_name}")
        for instance_index, instance_path in enumerate(instance_paths):
            try:
                formula = load_instance_formula_from_file(instance_path)
            except Exception:
                log(f"[Scaling] Skipping unreadable instance: {instance_path.name}")
                continue
            for run_id in range(runs_per_instance):
                seed = base_seed + solver_index * 100_003 + instance_index * 991 + run_id
                try:
                    result = solver.solve(formula, scaling_config(solver_key, formula.num_variables, seed))
                except Exception:
                    log(
                        f"[Scaling] Failed {solver.algorithm_name} on {instance_path.name} "
                        f"(run={run_id + 1}, seed={seed})"
                    )
                    continue
                rows.append(
                    {
                        "algorithm_name": result.algorithm_name,
                        "instance_name": instance_path.name,
                        "n": formula.num_variables,
                        "m": formula.num_clauses,
                        "size_n_plus_m": formula.num_variables + formula.num_clauses,
                        "runtime_seconds": result.runtime_seconds,
                        "satisfaction_rate": result.satisfaction_rate,
                    }
                )
                log(
                    f"[Scaling] {solver.algorithm_name} | {instance_path.name} | "
                    f"runtime={result.runtime_seconds:.3f}s | sat={100.0 * result.satisfaction_rate:.2f}%"
                )
        log(f"[Scaling] Solver finished: {solver.algorithm_name}")
    return rows


def build_complexity_summary_rows(
    *,
    solver_names: Sequence[str],
    scaling_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in scaling_rows:
        grouped.setdefault(str(row["algorithm_name"]), []).append(dict(row))

    rows: List[Dict[str, Any]] = []
    for solver_name in solver_names:
        empirical = grouped.get(solver_name, [])
        if empirical:
            x_vals = [math.log(max(1.0, float(item["size_n_plus_m"]))) for item in empirical]
            y_vals = [math.log(max(1e-9, float(item["runtime_seconds"]))) for item in empirical]
            fit = _linear_regression(x_vals, y_vals)
            exponent = fit["slope"]
            fit_quality = fit["r2"]
            samples = len(empirical)
        else:
            exponent = 0.0
            fit_quality = 0.0
            samples = 0
        rows.append(
            {
                "algorithm_name": solver_name,
                "estimated_time_complexity": ESTIMATED_COMPLEXITIES.get(solver_name, "Implementation-level estimate"),
                "empirical_scaling_exponent_loglog": exponent,
                "empirical_fit_r2": fit_quality,
                "empirical_samples": samples,
                "complexity_note": (
                    "Implementation-level estimated complexity and empirical runtime scaling; "
                    "not a formal proof."
                ),
            }
        )
    return rows


def save_complexity_csv(rows: Iterable[Dict[str, Any]], output_path: Path) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows_list[0].keys()))
        writer.writeheader()
        writer.writerows(rows_list)
