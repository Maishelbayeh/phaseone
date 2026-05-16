from __future__ import annotations

import csv
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from sat_generator import load_instance_formula_from_file
from utils import CNFFormula

from complexity_analysis import (
    build_complexity_summary_rows,
    run_empirical_scaling,
    save_complexity_csv,
)
from publication_plots import create_publication_plots
from report_builder import build_markdown_report
from solvers.base_solver import SolverResult
from solvers.registry import build_solver_registry


@dataclass(frozen=True)
class PerRunResult:
    algorithm_name: str
    instance_name: str
    run_id: int
    random_seed: int
    best_satisfied_clauses: int
    total_clauses: int
    satisfaction_rate: float
    unsatisfied_clauses: int
    runtime_seconds: float
    iterations_used: int
    fully_satisfied: bool


def _generate_seeds(
    *,
    runs_per_solver: int,
    base_seed: int,
    seed_mode: str,
    solver_count: int,
    same_seed_list_for_all: bool,
) -> List[List[int]]:
    if runs_per_solver < 1:
        raise ValueError("runs_per_solver must be at least 1.")
    if seed_mode not in {"incremental", "random"}:
        raise ValueError("seed_mode must be 'incremental' or 'random'.")

    rng = random.Random(base_seed)
    if seed_mode == "incremental":
        shared = [base_seed + i for i in range(runs_per_solver)]
    else:
        shared = [rng.randint(0, 2_147_483_647) for _ in range(runs_per_solver)]

    if same_seed_list_for_all:
        return [list(shared) for _ in range(solver_count)]

    all_lists: List[List[int]] = []
    for solver_index in range(solver_count):
        if seed_mode == "incremental":
            offset = solver_index * 100_003
            all_lists.append([seed + offset for seed in shared])
        else:
            solver_rng = random.Random(base_seed + solver_index * 997)
            all_lists.append([solver_rng.randint(0, 2_147_483_647) for _ in range(runs_per_solver)])
    return all_lists


def _solver_config_defaults(solver_key: str, formula: CNFFormula) -> Dict[str, Any]:
    n = formula.num_variables
    if solver_key == "hill_climbing":
        return {"max_iterations_per_restart": max(500, 10 * n), "max_random_restarts": 10}
    if solver_key == "simulated_annealing":
        return {
            "mode": "enhanced",
            "max_iterations": max(2500, 45 * n),
            "initial_temperature": 24.0,
            "cooling_rate": 0.9975,
            "min_temperature": 0.0005,
            "restart_count": 2,
            "restart_initialization_strategy": "polarity",
            "elite_restart_transfer": True,
            "elite_restart_perturbation": max(2, n // 30),
            "unsatisfied_focus_probability": 0.6,
            "candidate_pool_size": max(10, n // 10),
            "multi_bit_flip_probability": 0.04,
            "max_multi_flip_size": 2,
            "stagnation_multi_bit_boost": 0.15,
            "stagnation_limit": max(30, int(0.7 * n)),
            "reheat_multiplier": 1.5,
            "max_reheats": 4,
            "adaptive_cooling": True,
            "adaptive_cooling_bonus": 0.0007,
            "adaptive_cooling_penalty": 0.0025,
            "intensification_threshold": 0.98,
            "intensification_focus_probability": 0.94,
            "intensification_cooling_bonus": 0.0009,
            "mini_hill_climb_steps": max(10, int(0.33 * n)),
            "polarity_bias_strength": 0.7,
            "history_bias_strength": 0.72,
        }
    if solver_key == "tabu_search":
        return {"max_iterations": max(2000, 28 * n), "tabu_tenure": max(10, n // 10)}
    if solver_key == "hybrid_bsgo_ga":
        return {
            "population_size": max(28, min(90, n)),
            "max_iterations": max(160, 2 * n),
            "crossover_rate": 0.92,
            "mutation_rate": min(0.04, 2.0 / max(n, 1)),
            "c_coefficient": 0.72,
        }
    if solver_key == "genetic_algorithm":
        return {
            "population_size": max(40, min(96, n)),
            "max_generations": max(180, 2 * n),
            "crossover_rate": 0.88,
            "mutation_rate": min(0.03, 2.0 / max(n, 1)),
            "elite_count": 2,
            "crossover_mode": "two_point",
            "tournament_size": 3,
        }
    if solver_key == "memetic_ga_sa":
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
            "intensify_fraction": 0.8,
            "intensify_mutation_scale": 4.0,
            "incremental_local_steps": 2,
            "incremental_candidate_pool": max(40, n // 3),
            "sa_focus_unsatisfied_probability": 0.7,
            "sa_refinement_mode": "enhanced",
            "sa_initial_temperature": 24.0,
            "sa_cooling_rate": 0.9975,
            "sa_min_temperature": 0.0005,
            "sa_restart_count": 1,
            "sa_candidate_pool_size": max(10, n // 10),
            "sa_multi_bit_flip_probability": 0.04,
            "sa_reheat_multiplier": 1.5,
            "sa_max_reheats": 2,
            "sa_adaptive_cooling": True,
            "sa_intensification_threshold": 0.98,
            "sa_mini_hill_climb_steps": max(10, int(0.2 * n)),
            "sa_elite_restart_transfer": True,
            "path_relink_every": 10,
            "path_relink_top_k": 3,
            "path_relink_max_steps": max(20, min(60, n // 2)),
            "path_relink_only_hardcases": True,
            "hardcase_ratio_threshold": 4.3,
            "hardcase_multi_run_attempts": 2,
            "hardcase_generation_scale": 1.2,
            "hardcase_sa_scale": 1.25,
            "lamarckian": True,
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
        }
    if solver_key == "swarm_sa_solver":
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
        }
    return {}


def _compute_summary(rows: Sequence[PerRunResult]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[PerRunResult]] = {}
    for row in rows:
        grouped.setdefault(row.algorithm_name, []).append(row)

    summary: List[Dict[str, Any]] = []
    for solver_name, solver_rows in grouped.items():
        rates = [r.satisfaction_rate for r in solver_rows]
        runtimes = [r.runtime_seconds for r in solver_rows]
        satisfied = [r.best_satisfied_clauses for r in solver_rows]
        unsatisfied = [r.unsatisfied_clauses for r in solver_rows]
        full_count = sum(1 for r in solver_rows if r.fully_satisfied)

        summary.append(
            {
                "algorithm_name": solver_name,
                "mean_best_satisfied_clauses": mean(satisfied),
                "max_best_satisfied_clauses": max(satisfied),
                "mean_satisfaction_rate": mean(rates),
                "best_satisfaction_rate": max(rates),
                "mean_runtime": mean(runtimes),
                "median_runtime": median(runtimes),
                "std_runtime": pstdev(runtimes) if len(runtimes) > 1 else 0.0,
                "mean_unsatisfied_clauses": mean(unsatisfied),
                "full_satisfiability_count": full_count,
                "runs": len(solver_rows),
            }
        )

    ranked = sorted(summary, key=lambda row: (-row["mean_satisfaction_rate"], row["mean_runtime"]))
    rank_map = {row["algorithm_name"]: rank + 1 for rank, row in enumerate(ranked)}
    for row in summary:
        row["relative_rank"] = rank_map[row["algorithm_name"]]
    summary.sort(key=lambda row: row["relative_rank"])
    return summary


def _save_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows_list[0].keys()))
        writer.writeheader()
        writer.writerows(rows_list)


def run_comparison_pipeline(
    *,
    formula: CNFFormula,
    instance_name: str,
    output_root: Path,
    selected_solver_keys: Sequence[str],
    runs_per_solver: int,
    base_seed: int,
    seed_mode: str,
    same_seed_list_for_all: bool,
    scaling_instance_paths: Optional[Sequence[Path]] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    def log(message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)

    registry = build_solver_registry()
    solver_keys = [key for key in selected_solver_keys if key in registry]
    if not solver_keys:
        raise ValueError("No valid solvers selected.")

    output_root.mkdir(parents=True, exist_ok=True)
    plot_dir = output_root / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)

    seed_lists = _generate_seeds(
        runs_per_solver=runs_per_solver,
        base_seed=base_seed,
        seed_mode=seed_mode,
        solver_count=len(solver_keys),
        same_seed_list_for_all=same_seed_list_for_all,
    )
    total_runs = len(solver_keys) * runs_per_solver
    completed_runs = 0
    log(
        f"[Compare] Starting comparison: {len(solver_keys)} solvers x {runs_per_solver} run(s) "
        f"= {total_runs} total runs."
    )

    per_run: List[PerRunResult] = []
    solver_histories: Dict[str, List[Tuple[Tuple[int, ...], Tuple[float, ...]]]] = {}
    best_params: Dict[str, Dict[str, Any]] = {}

    for solver_index, solver_key in enumerate(solver_keys):
        solver = registry[solver_key]
        seeds = seed_lists[solver_index]
        defaults = _solver_config_defaults(solver_key, formula)
        log(f"[Compare] Solver start: {solver.algorithm_name} ({len(seeds)} run(s)).")
        for run_idx, seed in enumerate(seeds, start=1):
            config = dict(defaults)
            config["random_seed"] = seed
            log(
                f"[Compare] Running {solver.algorithm_name} | run {run_idx}/{len(seeds)} | seed={seed} ..."
            )
            result: SolverResult = solver.solve(formula, config)
            unsatisfied = max(0, result.total_clauses - result.best_satisfied_clauses)
            per_run.append(
                PerRunResult(
                    algorithm_name=result.algorithm_name,
                    instance_name=instance_name,
                    run_id=run_idx,
                    random_seed=seed,
                    best_satisfied_clauses=result.best_satisfied_clauses,
                    total_clauses=result.total_clauses,
                    satisfaction_rate=result.satisfaction_rate,
                    unsatisfied_clauses=unsatisfied,
                    runtime_seconds=result.runtime_seconds,
                    iterations_used=result.iterations_used,
                    fully_satisfied=result.fully_satisfied,
                )
            )
            solver_histories.setdefault(result.algorithm_name, []).append((result.best_history, result.runtime_history))
            previous = best_params.get(result.algorithm_name)
            if previous is None or result.satisfaction_rate > float(previous["satisfaction_rate"]):
                best_params[result.algorithm_name] = {
                    "satisfaction_rate": result.satisfaction_rate,
                    "best_satisfied_clauses": result.best_satisfied_clauses,
                    "runtime_seconds": result.runtime_seconds,
                    "random_seed": seed,
                    "params": dict(result.parameter_summary),
                }
            completed_runs += 1
            log(
                f"[Compare] Done {solver.algorithm_name} run {run_idx}/{len(seeds)}: "
                f"{result.best_satisfied_clauses}/{result.total_clauses} "
                f"({100.0 * result.satisfaction_rate:.2f}%), runtime={result.runtime_seconds:.3f}s "
                f"[{completed_runs}/{total_runs}]"
            )
        log(f"[Compare] Solver finished: {solver.algorithm_name}.")

    summary_rows = _compute_summary(per_run)
    per_run_csv = output_root / "per_run_results.csv"
    summary_csv = output_root / "summary_results.csv"
    _save_csv(per_run_csv, (asdict(row) for row in per_run))
    _save_csv(summary_csv, summary_rows)
    log("[Compare] Saved per-run and summary CSV files.")

    scaling_rows: List[Dict[str, Any]] = []
    if scaling_instance_paths:
        log(f"[Compare] Empirical scaling started on {len(scaling_instance_paths)} instance(s).")
        scaling_rows = run_empirical_scaling(
            instance_paths=scaling_instance_paths,
            solver_keys=solver_keys,
            runs_per_instance=1,
            base_seed=base_seed + 900_001,
            progress_callback=progress_callback,
        )
        log(f"[Compare] Empirical scaling finished ({len(scaling_rows)} rows).")

    complexity_rows = build_complexity_summary_rows(solver_names=[registry[key].algorithm_name for key in solver_keys], scaling_rows=scaling_rows)
    complexity_csv = output_root / "complexity_summary.csv"
    save_complexity_csv(complexity_rows, complexity_csv)
    log("[Compare] Saved complexity summary CSV.")

    best_json_path = output_root / "best_config_or_params.json"
    with best_json_path.open("w", encoding="utf-8") as file_obj:
        json.dump(best_params, file_obj, indent=2)
    log("[Compare] Saved best parameter snapshot JSON.")

    log("[Compare] Generating publication plots (PNG/SVG/PDF)...")
    plot_paths = create_publication_plots(
        per_run_rows=[asdict(row) for row in per_run],
        summary_rows=summary_rows,
        solver_histories=solver_histories,
        scaling_rows=scaling_rows,
        output_dir=plot_dir,
        save_title_variants=True,
    )
    log(f"[Compare] Publication plots generated ({len(plot_paths)} files).")

    report_path = output_root / "comparison_report.md"
    report_text = build_markdown_report(
        instance_name=instance_name,
        per_run_rows=[asdict(row) for row in per_run],
        summary_rows=summary_rows,
        complexity_rows=complexity_rows,
        best_params=best_params,
    )
    report_path.write_text(report_text, encoding="utf-8")
    log("[Compare] Report markdown generated.")
    log("[Compare] Comparison pipeline complete.")

    return {
        "per_run_rows": [asdict(row) for row in per_run],
        "summary_rows": summary_rows,
        "complexity_rows": complexity_rows,
        "plot_paths": plot_paths,
        "per_run_csv": str(per_run_csv),
        "summary_csv": str(summary_csv),
        "complexity_csv": str(complexity_csv),
        "best_params_json": str(best_json_path),
        "report_path": str(report_path),
    }


def select_scaling_instances_from_directory(instance_path: Path, *, max_files: int = 8) -> List[Path]:
    root = instance_path.parent
    candidates = sorted(root.rglob("3sat_*.json"))
    if not candidates:
        return [instance_path]
    formulas: List[Tuple[int, int, Path]] = []
    for path in candidates:
        try:
            formula = load_instance_formula_from_file(path)
        except Exception:
            continue
        formulas.append((formula.num_variables, formula.num_clauses, path))
    formulas.sort(key=lambda item: (item[0], item[1], item[2].name))
    selected: List[Path] = []
    seen_n: set[int] = set()
    for n, _m, path in formulas:
        if n in seen_n:
            continue
        selected.append(path)
        seen_n.add(n)
        if len(selected) >= max_files:
            break
    if instance_path not in selected:
        selected.append(instance_path)
    return sorted(set(selected))
