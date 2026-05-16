from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from config import (
    COMPARISON_DIR,
    INSTANCE_ROOT,
    SA_HARD_MATRIX,
    SA_REPRESENTATIVE_MATRIX,
    SA_RESULTS_DIR,
    SA_TUNING_SPACE,
    baseline_sa_defaults,
    benchmark_seed,
    enhanced_sa_defaults,
)
from sa_analysis import (
    create_sa_analysis_artifacts,
    dataclass_sequence_to_dicts,
    result_to_focus_payload,
    save_csv,
    save_json,
    summarize_runs,
)
from sat_generator import load_instance_formula_from_file
from simulated_annealing import simulated_annealing_search


@dataclass(frozen=True)
class SettingEvaluation:
    setting_label: str
    config: Dict[str, Any]
    mean_satisfaction_rate: float
    full_satisfaction_count: int
    mean_runtime_seconds: float
    success_rate: float
    runtime_to_success: float
    run_count: int


def _sample_enhanced_config(n: int, rng: random.Random) -> Dict[str, Any]:
    config = enhanced_sa_defaults(n)
    config.update(
        {
            "initial_temperature": rng.choice(SA_TUNING_SPACE["initial_temperature"]),
            "cooling_rate": rng.choice(SA_TUNING_SPACE["cooling_rate"]),
            "min_temperature": rng.choice(SA_TUNING_SPACE["min_temperature"]),
            "max_iterations": max(2500, int(rng.choice(SA_TUNING_SPACE["max_iterations_scale"]) * n)),
            "unsatisfied_focus_probability": rng.choice(SA_TUNING_SPACE["unsatisfied_focus_probability"]),
            "stagnation_limit": max(30, int(rng.choice(SA_TUNING_SPACE["stagnation_limit_scale"]) * n)),
            "reheat_multiplier": rng.choice(SA_TUNING_SPACE["reheat_multiplier"]),
            "max_reheats": rng.choice(SA_TUNING_SPACE["max_reheats"]),
            "restart_count": rng.choice(SA_TUNING_SPACE["restart_count"]),
            "intensification_threshold": rng.choice(SA_TUNING_SPACE["intensification_threshold"]),
            "multi_bit_flip_probability": rng.choice(SA_TUNING_SPACE["multi_bit_flip_probability"]),
            "mini_hill_climb_steps": max(
                0, int(rng.choice(SA_TUNING_SPACE["mini_hill_climb_steps_scale"]) * n)
            ),
            "candidate_pool_size": max(
                8, n // int(rng.choice(SA_TUNING_SPACE["candidate_pool_divisor"]))
            ),
            "restart_initialization_strategy": rng.choice(
                SA_TUNING_SPACE["restart_initialization_strategy"]
            ),
            "elite_restart_transfer": rng.choice(
                SA_TUNING_SPACE["elite_restart_transfer"]
            ),
        }
    )
    return config


def _setting_is_better(candidate: SettingEvaluation, current: SettingEvaluation | None) -> bool:
    if current is None:
        return True
    candidate_key = (
        candidate.full_satisfaction_count,
        candidate.success_rate,
        candidate.mean_satisfaction_rate,
        -candidate.mean_runtime_seconds,
    )
    current_key = (
        current.full_satisfaction_count,
        current.success_rate,
        current.mean_satisfaction_rate,
        -current.mean_runtime_seconds,
    )
    return candidate_key > current_key


def _evaluate_setting(
    *,
    setting_label: str,
    config_builder: callable,
    matrix: Sequence[tuple[str, int, float]],
    runs_per_instance: int,
) -> tuple[SettingEvaluation, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for instance_name, n, ratio in matrix:
        formula = load_instance_formula_from_file(INSTANCE_ROOT / instance_name)
        for run_id in range(runs_per_instance):
            seed = benchmark_seed(n, ratio, offset=run_id)
            config = dict(config_builder(n))
            result = simulated_annealing_search(formula, random_seed=seed, **config)
            rows.append(
                {
                    "setting_label": setting_label,
                    "instance_name": instance_name,
                    "n": n,
                    "ratio": ratio,
                    "run_id": run_id,
                    "random_seed": seed,
                    "mode": result.mode,
                    "best_satisfied_clauses": result.best_merit,
                    "total_clauses": result.total_clauses,
                    "satisfaction_rate": 0.0 if result.total_clauses == 0 else result.best_merit / result.total_clauses,
                    "runtime_seconds": result.runtime_seconds,
                    "iterations_used": result.iterations_used,
                    "fully_satisfied": result.fully_satisfied,
                    "restart_count": result.restart_count,
                    "iteration_of_best": result.iteration_of_best,
                    "iteration_of_full_satisfaction": result.iteration_of_full_satisfaction,
                    "reheat_count": result.reheat_count,
                    "accepted_worse_moves": result.accepted_worse_moves,
                    "accepted_better_moves": result.accepted_better_moves,
                    "accepted_equal_moves": result.accepted_equal_moves,
                    "number_of_unsatisfied_focused_moves": result.number_of_unsatisfied_focused_moves,
                    "config_json": json.dumps(config, sort_keys=True),
                }
            )
    summary = summarize_runs(rows)
    evaluation = SettingEvaluation(
        setting_label=setting_label,
        config=dict(config_builder(matrix[0][1] if matrix else 100)),
        mean_satisfaction_rate=float(summary["mean_satisfaction_rate"]),
        full_satisfaction_count=int(summary["full_satisfaction_count"]),
        mean_runtime_seconds=float(summary["mean_runtime_seconds"]),
        success_rate=float(summary["success_rate"]),
        runtime_to_success=float(summary["runtime_to_success"]),
        run_count=int(summary["run_count"]),
    )
    return evaluation, rows


def _evaluate_config_across_matrix(
    *,
    setting_label: str,
    config_by_n: Mapping[int, Dict[str, Any]],
    matrix: Sequence[tuple[str, int, float]],
    runs_per_instance: int,
) -> tuple[SettingEvaluation, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for instance_name, n, ratio in matrix:
        formula = load_instance_formula_from_file(INSTANCE_ROOT / instance_name)
        config = dict(config_by_n[n])
        for run_id in range(runs_per_instance):
            seed = benchmark_seed(n, ratio, offset=run_id)
            result = simulated_annealing_search(formula, random_seed=seed, **config)
            rows.append(
                {
                    "setting_label": setting_label,
                    "instance_name": instance_name,
                    "n": n,
                    "ratio": ratio,
                    "run_id": run_id,
                    "random_seed": seed,
                    "mode": result.mode,
                    "best_satisfied_clauses": result.best_merit,
                    "total_clauses": result.total_clauses,
                    "satisfaction_rate": 0.0 if result.total_clauses == 0 else result.best_merit / result.total_clauses,
                    "runtime_seconds": result.runtime_seconds,
                    "iterations_used": result.iterations_used,
                    "fully_satisfied": result.fully_satisfied,
                    "restart_count": result.restart_count,
                    "iteration_of_best": result.iteration_of_best,
                    "iteration_of_full_satisfaction": result.iteration_of_full_satisfaction,
                    "reheat_count": result.reheat_count,
                    "accepted_worse_moves": result.accepted_worse_moves,
                    "accepted_better_moves": result.accepted_better_moves,
                    "accepted_equal_moves": result.accepted_equal_moves,
                    "number_of_unsatisfied_focused_moves": result.number_of_unsatisfied_focused_moves,
                    "config_json": json.dumps(config, sort_keys=True),
                }
            )
    summary = summarize_runs(rows)
    exemplar_config = dict(next(iter(config_by_n.values()))) if config_by_n else {}
    evaluation = SettingEvaluation(
        setting_label=setting_label,
        config=exemplar_config,
        mean_satisfaction_rate=float(summary["mean_satisfaction_rate"]),
        full_satisfaction_count=int(summary["full_satisfaction_count"]),
        mean_runtime_seconds=float(summary["mean_runtime_seconds"]),
        success_rate=float(summary["success_rate"]),
        runtime_to_success=float(summary["runtime_to_success"]),
        run_count=int(summary["run_count"]),
    )
    return evaluation, rows


def run_tuning(
    *,
    trials: int,
    matrix_name: str,
    runs_per_instance: int,
    base_seed: int,
) -> dict[str, Any]:
    matrix = SA_HARD_MATRIX if matrix_name == "hard" else SA_REPRESENTATIVE_MATRIX
    rng = random.Random(base_seed)
    ns = sorted({n for _, n, _ in matrix})

    baseline_config_by_n = {n: baseline_sa_defaults(n) for n in ns}
    baseline_eval, baseline_rows = _evaluate_config_across_matrix(
        setting_label="baseline",
        config_by_n=baseline_config_by_n,
        matrix=matrix,
        runs_per_instance=runs_per_instance,
    )

    best_eval: SettingEvaluation | None = None
    best_rows: list[dict[str, Any]] = []
    tuning_evaluations: list[SettingEvaluation] = []
    trial_rows_all: list[dict[str, Any]] = []

    for trial_index in range(trials):
        config_by_n = {n: _sample_enhanced_config(n, rng) for n in ns}
        evaluation, rows = _evaluate_config_across_matrix(
            setting_label=f"enhanced_trial_{trial_index + 1}",
            config_by_n=config_by_n,
            matrix=matrix,
            runs_per_instance=runs_per_instance,
        )
        tuning_evaluations.append(evaluation)
        trial_rows_all.extend(rows)
        if _setting_is_better(evaluation, best_eval):
            best_eval = evaluation
            best_rows = rows

    if best_eval is None:
        raise RuntimeError("No enhanced SA setting was evaluated.")

    focus_instance = next((item for item in matrix if item[2] >= 4.3), matrix[0])
    focus_formula = load_instance_formula_from_file(INSTANCE_ROOT / focus_instance[0])
    focus_config = dict(enhanced_sa_defaults(focus_instance[1]))
    focus_config.update(best_eval.config)
    focus_result = simulated_annealing_search(
        focus_formula,
        random_seed=benchmark_seed(focus_instance[1], focus_instance[2]),
        **focus_config,
    )

    comparison_per_run = baseline_rows + best_rows
    comparison_payload = {
        "per_run": comparison_per_run,
        "baseline_summary": summarize_runs(baseline_rows),
        "enhanced_summary": summarize_runs(best_rows),
    }

    tuning_trial_rows = [
        {
            "setting_label": evaluation.setting_label,
            "mean_satisfaction_rate": evaluation.mean_satisfaction_rate,
            "full_satisfaction_count": evaluation.full_satisfaction_count,
            "mean_runtime_seconds": evaluation.mean_runtime_seconds,
            "success_rate": evaluation.success_rate,
            "runtime_to_success": evaluation.runtime_to_success,
            "run_count": evaluation.run_count,
            "config_json": json.dumps(evaluation.config, sort_keys=True),
        }
        for evaluation in tuning_evaluations
    ]

    result_payload = {
        "matrix_name": matrix_name,
        "runs_per_instance": runs_per_instance,
        "base_seed": base_seed,
        "baseline_evaluation": asdict(baseline_eval),
        "best_enhanced_evaluation": asdict(best_eval),
        "comparison": comparison_payload,
        "tuning_trials": tuning_trial_rows,
        "focus_instance": {
            "instance_name": focus_instance[0],
            "n": focus_instance[1],
            "ratio": focus_instance[2],
        },
    }

    COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
    SA_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    save_csv(comparison_per_run, COMPARISON_DIR / "sa_baseline_vs_enhanced_per_run.csv")
    save_json(comparison_payload, COMPARISON_DIR / "sa_baseline_vs_enhanced_comparison.json")
    save_csv(tuning_trial_rows, COMPARISON_DIR / "sa_enhanced_tuning_trials.csv")
    save_json(result_payload, COMPARISON_DIR / "sa_enhanced_tuning_summary.json")
    save_json(
        {
            "best_enhanced_setting": asdict(best_eval),
            "baseline_setting": asdict(baseline_eval),
        },
        COMPARISON_DIR / "sa_best_config_or_params.json",
    )

    create_sa_analysis_artifacts(
        output_dir=SA_RESULTS_DIR,
        comparison_payload=comparison_payload,
        tuning_trials=tuning_trial_rows,
        best_enhanced_setting=asdict(best_eval),
        focus_result=result_to_focus_payload(
            instance_name=focus_instance[0],
            result={
                "best_merit": focus_result.best_merit,
                "total_clauses": focus_result.total_clauses,
                "restart_count": focus_result.restart_count,
                "reheat_count": focus_result.reheat_count,
                "accepted_better_moves": focus_result.accepted_better_moves,
                "accepted_equal_moves": focus_result.accepted_equal_moves,
                "accepted_worse_moves": focus_result.accepted_worse_moves,
                "merit_history": focus_result.merit_history,
                "temperature_history": focus_result.temperature_history,
                "accepted_move_history": focus_result.accepted_move_history,
                "final_satisfaction_rates": focus_result.final_satisfaction_rates,
                "restart_summaries": dataclass_sequence_to_dicts(focus_result.restart_summaries),
            },
        ),
    )
    save_json(
        {
            "focus_instance": focus_instance[0],
            "focus_config": focus_config,
            "restart_summaries": dataclass_sequence_to_dicts(focus_result.restart_summaries),
            "parameter_summary": focus_result.parameter_summary,
        },
        SA_RESULTS_DIR / "focus_run_details.json",
    )
    return result_payload


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tune and compare baseline versus enhanced simulated annealing."
    )
    parser.add_argument("--trials", type=int, default=8, help="Enhanced SA settings sampled.")
    parser.add_argument(
        "--matrix",
        choices=("representative", "hard"),
        default="representative",
        help="Benchmark matrix to use for tuning and comparison.",
    )
    parser.add_argument(
        "--runs-per-instance",
        type=int,
        default=1,
        help="Independent solver runs per benchmark instance.",
    )
    parser.add_argument("--base-seed", type=int, default=42, help="Master RNG seed.")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    payload = run_tuning(
        trials=max(1, args.trials),
        matrix_name=args.matrix,
        runs_per_instance=max(1, args.runs_per_instance),
        base_seed=args.base_seed,
    )
    print(COMPARISON_DIR / "sa_enhanced_tuning_summary.json")
    print(SA_RESULTS_DIR / "analysis_report.md")
    print(json.dumps(payload["best_enhanced_evaluation"], indent=2))


if __name__ == "__main__":
    main()
