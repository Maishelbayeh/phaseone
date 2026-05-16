from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from benchmark_generator import generate_sa_stress_instances, records_to_rows
from config import (
    MEMETIC_STRESS_PLOTS_DIR,
    MEMETIC_STRESS_RESULTS_DIR,
    SA_BREAKDOWN_THRESHOLDS,
    SA_STRESS_DENSITY_RATIOS,
    SA_STRESS_INSTANCE_DIR,
    SA_STRESS_INSTANCES_PER_CELL,
    SA_STRESS_SOLVER_RUNS_PER_INSTANCE,
    SA_STRESS_VARIABLE_COUNTS,
    memetic_ga_sa_classic_defaults,
    memetic_ga_sa_enhanced_defaults,
)
from report_builder import build_sa_stress_report
from sa_analysis import save_csv, save_json
from sa_stress_test import (
    _aggregate_algorithm_health,
    _breakdown_by_algorithm,
    _create_plots,
    _regions_by_algorithm,
)
from sa_scaling_analysis import hardest_instances, summarize_rows
from sat_generator import load_instance_formula_from_file
from solvers.memetic_ga_sa import MemeticGASASolver


@dataclass(frozen=True)
class MemeticStressRunRecord:
    instance_name: str
    n: int
    m: int
    ratio: float
    generator_seed: int
    solver_seed: int
    algorithm_name: str
    best_satisfied_clauses: int
    total_clauses: int
    satisfaction_rate: float
    unsatisfied_clauses: int
    runtime_seconds: float
    iterations_used: int
    fully_satisfied: bool
    iteration_of_best: int | None


def _algorithm_configs(n: int, *, include_enhanced: bool) -> List[tuple[str, Dict[str, Any]]]:
    configs = [("Memetic GA-SA (Classic refine)", memetic_ga_sa_classic_defaults(n))]
    if include_enhanced:
        configs.append(("Memetic GA-SA (Enhanced SA refine)", memetic_ga_sa_enhanced_defaults(n)))
    return configs


def _iteration_of_best(best_history: Sequence[int]) -> int | None:
    if not best_history:
        return None
    best_value = max(best_history)
    for index, value in enumerate(best_history):
        if value == best_value:
            return index
    return None


def run_memetic_stress_test(
    *,
    variable_counts: Sequence[int] = SA_STRESS_VARIABLE_COUNTS,
    density_ratios: Sequence[float] = SA_STRESS_DENSITY_RATIOS,
    instances_per_cell: int = SA_STRESS_INSTANCES_PER_CELL,
    solver_runs_per_instance: int = SA_STRESS_SOLVER_RUNS_PER_INSTANCE,
    include_enhanced: bool = True,
    base_seed: int = 42,
    instance_dir: Path = SA_STRESS_INSTANCE_DIR,
    output_dir: Path = MEMETIC_STRESS_RESULTS_DIR,
    thresholds: Mapping[str, float] = SA_BREAKDOWN_THRESHOLDS,
) -> Dict[str, Any]:
    generated_instances = generate_sa_stress_instances(
        output_dir=instance_dir,
        variable_counts=variable_counts,
        density_ratios=density_ratios,
        instances_per_cell=instances_per_cell,
        base_seed=base_seed,
    )

    solver = MemeticGASASolver()
    run_rows: List[Dict[str, Any]] = []
    for instance in generated_instances:
        formula = load_instance_formula_from_file(instance.file_path)
        for algorithm_name, config in _algorithm_configs(instance.n, include_enhanced=include_enhanced):
            for run_id in range(solver_runs_per_instance):
                solver_seed = (
                    instance.generator_seed
                    + run_id * 1_000_003
                    + (53 if "Enhanced" in algorithm_name else 0)
                )
                run_config = dict(config)
                run_config["random_seed"] = solver_seed
                result = solver.solve(formula, run_config)
                row = MemeticStressRunRecord(
                    instance_name=instance.instance_name,
                    n=instance.n,
                    m=instance.m,
                    ratio=instance.ratio,
                    generator_seed=instance.generator_seed,
                    solver_seed=solver_seed,
                    algorithm_name=algorithm_name,
                    best_satisfied_clauses=result.best_satisfied_clauses,
                    total_clauses=result.total_clauses,
                    satisfaction_rate=result.satisfaction_rate,
                    unsatisfied_clauses=result.total_clauses - result.best_satisfied_clauses,
                    runtime_seconds=result.runtime_seconds,
                    iterations_used=result.iterations_used,
                    fully_satisfied=result.fully_satisfied,
                    iteration_of_best=_iteration_of_best(result.best_history),
                )
                run_rows.append(asdict(row))

    summary_by_n = summarize_rows(run_rows, group_keys=("algorithm_name", "n"))
    summary_by_r = summarize_rows(run_rows, group_keys=("algorithm_name", "ratio"))
    summary_by_pair = summarize_rows(run_rows, group_keys=("algorithm_name", "n", "ratio"))
    algorithm_health = _aggregate_algorithm_health(run_rows)
    breakdown = _breakdown_by_algorithm(
        summary_by_n,
        summary_by_r,
        summary_by_pair,
        thresholds=thresholds,
    )
    region_summary = _regions_by_algorithm(summary_by_pair)
    hard_report = hardest_instances(run_rows, top_k=10)

    output_dir.mkdir(parents=True, exist_ok=True)
    plots_written = _create_plots(
        per_run_rows=run_rows,
        summary_by_n=summary_by_n,
        summary_by_r=summary_by_r,
        summary_by_pair=summary_by_pair,
        output_dir=MEMETIC_STRESS_PLOTS_DIR,
    )

    save_json(records_to_rows(generated_instances), output_dir / "generated_instances_manifest.json")
    save_csv(run_rows, output_dir / "memetic_stress_per_run.csv")
    save_csv(summary_by_n, output_dir / "memetic_stress_summary_by_n.csv")
    save_csv(summary_by_r, output_dir / "memetic_stress_summary_by_ratio.csv")
    save_csv(summary_by_pair, output_dir / "memetic_stress_summary_by_n_ratio.csv")
    save_json(
        {
            "breakdown": breakdown,
            "regions": region_summary,
            "hardest_reports": hard_report,
            "algorithm_health": algorithm_health,
        },
        output_dir / "memetic_stress_hard_regions.json",
    )

    report_text = build_sa_stress_report(
        overall_summary={},
        algorithm_summaries=algorithm_health,
        breakdown=breakdown,
        region_summary=region_summary,
        hard_instance_report=hard_report,
        title="Memetic GA-SA Stress-Test Report",
    )
    (output_dir / "analysis_report.md").write_text(report_text, encoding="utf-8")

    payload = {
        "instance_count": len(generated_instances),
        "per_run_count": len(run_rows),
        "summary_by_n": summary_by_n,
        "summary_by_ratio": summary_by_r,
        "summary_by_pair": summary_by_pair,
        "algorithm_health": algorithm_health,
        "breakdown": breakdown,
        "regions": region_summary,
        "hardest_reports": hard_report,
        "plots_written": plots_written,
    }
    save_json(payload, output_dir / "memetic_stress_summary.json")
    return payload


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Large-scale stress test for Memetic GA-SA.")
    parser.add_argument("--instances-per-cell", type=int, default=SA_STRESS_INSTANCES_PER_CELL)
    parser.add_argument("--solver-runs-per-instance", type=int, default=SA_STRESS_SOLVER_RUNS_PER_INSTANCE)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--classic-only", action="store_true")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    payload = run_memetic_stress_test(
        instances_per_cell=max(1, args.instances_per_cell),
        solver_runs_per_instance=max(1, args.solver_runs_per_instance),
        include_enhanced=not args.classic_only,
        base_seed=args.base_seed,
    )
    print(MEMETIC_STRESS_RESULTS_DIR / "analysis_report.md")
    print(json.dumps(payload["algorithm_health"], indent=2))


if __name__ == "__main__":
    main()
