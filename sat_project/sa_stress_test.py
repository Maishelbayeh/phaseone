from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from benchmark_generator import generate_sa_stress_instances, records_to_rows
from config import (
    SA_BREAKDOWN_THRESHOLDS,
    SA_STRESS_DENSITY_RATIOS,
    SA_STRESS_INSTANCE_DIR,
    SA_STRESS_INSTANCES_PER_CELL,
    SA_STRESS_PLOTS_DIR,
    SA_STRESS_RESULTS_DIR,
    SA_STRESS_SOLVER_RUNS_PER_INSTANCE,
    SA_STRESS_VARIABLE_COUNTS,
    baseline_sa_defaults,
    enhanced_sa_defaults,
)
from plotting import (
    plot_boxplots_by_group,
    plot_heatmap,
    plot_metric_vs_group,
    plot_runtime_vs_satisfaction_scatter,
)
from report_builder import build_sa_stress_report
from sa_analysis import save_csv, save_json
from sa_scaling_analysis import (
    compute_global_health,
    detect_breakdown,
    easiest_and_hardest_regions,
    hardest_instances,
    pair_matrix_rows,
    summarize_rows,
)
from sat_generator import load_instance_formula_from_file
from simulated_annealing import simulated_annealing_search


@dataclass(frozen=True)
class StressRunRecord:
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
    configs = [("Simulated Annealing (Baseline)", baseline_sa_defaults(n))]
    if include_enhanced:
        configs.append(("Simulated Annealing (Enhanced)", enhanced_sa_defaults(n)))
    return configs


def _aggregate_algorithm_health(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_algorithm: Dict[str, List[Mapping[str, Any]]] = {}
    for row in rows:
        by_algorithm.setdefault(str(row["algorithm_name"]), []).append(row)
    output: List[Dict[str, Any]] = []
    for algorithm_name, algorithm_rows in by_algorithm.items():
        payload = {"algorithm_name": algorithm_name}
        payload.update(compute_global_health(algorithm_rows))
        output.append(payload)
    return sorted(output, key=lambda row: str(row["algorithm_name"]))


def _breakdown_by_algorithm(
    summary_by_n: Sequence[Mapping[str, Any]],
    summary_by_r: Sequence[Mapping[str, Any]],
    summary_by_pair: Sequence[Mapping[str, Any]],
    *,
    thresholds: Mapping[str, float],
) -> Dict[str, Any]:
    algorithms = sorted({str(row["algorithm_name"]) for row in summary_by_pair})
    output: Dict[str, Any] = {}
    for algorithm_name in algorithms:
        output[algorithm_name] = detect_breakdown(
            summary_by_n=[row for row in summary_by_n if str(row["algorithm_name"]) == algorithm_name],
            summary_by_r=[row for row in summary_by_r if str(row["algorithm_name"]) == algorithm_name],
            summary_by_pair=[row for row in summary_by_pair if str(row["algorithm_name"]) == algorithm_name],
            thresholds=thresholds,
        )
    return output


def _regions_by_algorithm(summary_by_pair: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    algorithms = sorted({str(row["algorithm_name"]) for row in summary_by_pair})
    return {
        algorithm_name: easiest_and_hardest_regions(
            [row for row in summary_by_pair if str(row["algorithm_name"]) == algorithm_name]
        )
        for algorithm_name in algorithms
    }


def _create_plots(
    *,
    per_run_rows: Sequence[Mapping[str, Any]],
    summary_by_n: Sequence[Mapping[str, Any]],
    summary_by_r: Sequence[Mapping[str, Any]],
    summary_by_pair: Sequence[Mapping[str, Any]],
    output_dir: Path,
) -> List[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    for path in plot_metric_vs_group(
        summary_by_n,
        group_key="n",
        metric_key="full_satisfaction_success_rate",
        y_label="Full satisfaction success rate",
        title="Full satisfaction success rate vs n",
        output_base_path=output_dir / "full_success_rate_vs_n",
    ):
        written.append(str(path))
    for path in plot_metric_vs_group(
        summary_by_r,
        group_key="ratio",
        metric_key="full_satisfaction_success_rate",
        y_label="Full satisfaction success rate",
        title="Full satisfaction success rate vs clause density",
        output_base_path=output_dir / "full_success_rate_vs_ratio",
    ):
        written.append(str(path))
    for path in plot_metric_vs_group(
        summary_by_n,
        group_key="n",
        metric_key="mean_satisfaction_rate",
        y_label="Mean satisfaction rate",
        title="Mean satisfaction rate vs n",
        output_base_path=output_dir / "mean_satisfaction_vs_n",
    ):
        written.append(str(path))
    for path in plot_metric_vs_group(
        summary_by_r,
        group_key="ratio",
        metric_key="mean_satisfaction_rate",
        y_label="Mean satisfaction rate",
        title="Mean satisfaction rate vs clause density",
        output_base_path=output_dir / "mean_satisfaction_vs_ratio",
    ):
        written.append(str(path))
    for path in plot_metric_vs_group(
        summary_by_n,
        group_key="n",
        metric_key="mean_runtime_seconds",
        y_label="Mean runtime (seconds)",
        title="Mean runtime vs n",
        output_base_path=output_dir / "mean_runtime_vs_n",
    ):
        written.append(str(path))
    for path in plot_metric_vs_group(
        summary_by_r,
        group_key="ratio",
        metric_key="mean_runtime_seconds",
        y_label="Mean runtime (seconds)",
        title="Mean runtime vs clause density",
        output_base_path=output_dir / "mean_runtime_vs_ratio",
    ):
        written.append(str(path))

    algorithms = sorted({str(row["algorithm_name"]) for row in summary_by_pair})
    for algorithm_name in algorithms:
        token = algorithm_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        algorithm_pair_rows = pair_matrix_rows(summary_by_pair, algorithm_name=algorithm_name)
        for path in plot_heatmap(
            algorithm_pair_rows,
            value_key="mean_satisfaction_rate",
            title=f"{algorithm_name}: satisfaction heatmap",
            output_base_path=output_dir / f"{token}_satisfaction_heatmap",
            value_label="Mean satisfaction rate",
        ):
            written.append(str(path))
        for path in plot_heatmap(
            algorithm_pair_rows,
            value_key="full_satisfaction_success_rate",
            title=f"{algorithm_name}: full satisfaction heatmap",
            output_base_path=output_dir / f"{token}_full_success_heatmap",
            value_label="Full satisfaction success rate",
        ):
            written.append(str(path))
        for path in plot_heatmap(
            algorithm_pair_rows,
            value_key="mean_runtime_seconds",
            title=f"{algorithm_name}: runtime heatmap",
            output_base_path=output_dir / f"{token}_runtime_heatmap",
            value_label="Mean runtime (seconds)",
        ):
            written.append(str(path))

    for path in plot_runtime_vs_satisfaction_scatter(
        per_run_rows,
        output_base_path=output_dir / "runtime_vs_satisfaction_scatter",
        title="Runtime vs satisfaction rate",
    ):
        written.append(str(path))
    for path in plot_boxplots_by_group(
        per_run_rows,
        group_key="n",
        metric_key="satisfaction_rate",
        title="Satisfaction rate grouped by n",
        y_label="Satisfaction rate",
        output_base_path=output_dir / "satisfaction_rate_boxplot_by_n",
    ):
        written.append(str(path))
    for path in plot_boxplots_by_group(
        per_run_rows,
        group_key="n",
        metric_key="runtime_seconds",
        title="Runtime grouped by n",
        y_label="Runtime (seconds)",
        output_base_path=output_dir / "runtime_boxplot_by_n",
    ):
        written.append(str(path))
    return written


def run_sa_stress_test(
    *,
    variable_counts: Sequence[int] = SA_STRESS_VARIABLE_COUNTS,
    density_ratios: Sequence[float] = SA_STRESS_DENSITY_RATIOS,
    instances_per_cell: int = SA_STRESS_INSTANCES_PER_CELL,
    solver_runs_per_instance: int = SA_STRESS_SOLVER_RUNS_PER_INSTANCE,
    include_enhanced: bool = True,
    base_seed: int = 42,
    instance_dir: Path = SA_STRESS_INSTANCE_DIR,
    output_dir: Path = SA_STRESS_RESULTS_DIR,
    thresholds: Mapping[str, float] = SA_BREAKDOWN_THRESHOLDS,
) -> Dict[str, Any]:
    generated_instances = generate_sa_stress_instances(
        output_dir=instance_dir,
        variable_counts=variable_counts,
        density_ratios=density_ratios,
        instances_per_cell=instances_per_cell,
        base_seed=base_seed,
    )

    run_rows: List[Dict[str, Any]] = []
    for instance in generated_instances:
        formula = load_instance_formula_from_file(instance.file_path)
        for algorithm_name, config in _algorithm_configs(instance.n, include_enhanced=include_enhanced):
            for run_id in range(solver_runs_per_instance):
                solver_seed = (
                    instance.generator_seed
                    + run_id * 1_000_003
                    + (17 if "Enhanced" in algorithm_name else 0)
                )
                result = simulated_annealing_search(formula, random_seed=solver_seed, **config)
                row = StressRunRecord(
                    instance_name=instance.instance_name,
                    n=instance.n,
                    m=instance.m,
                    ratio=instance.ratio,
                    generator_seed=instance.generator_seed,
                    solver_seed=solver_seed,
                    algorithm_name=algorithm_name,
                    best_satisfied_clauses=result.best_merit,
                    total_clauses=result.total_clauses,
                    satisfaction_rate=0.0 if result.total_clauses == 0 else result.best_merit / result.total_clauses,
                    unsatisfied_clauses=result.total_clauses - result.best_merit,
                    runtime_seconds=result.runtime_seconds,
                    iterations_used=result.iterations_used,
                    fully_satisfied=result.fully_satisfied,
                    iteration_of_best=result.iteration_of_best,
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
        output_dir=SA_STRESS_PLOTS_DIR,
    )

    save_json(records_to_rows(generated_instances), output_dir / "generated_instances_manifest.json")
    save_csv(run_rows, output_dir / "sa_stress_per_run.csv")
    save_csv(summary_by_n, output_dir / "sa_stress_summary_by_n.csv")
    save_csv(summary_by_r, output_dir / "sa_stress_summary_by_ratio.csv")
    save_csv(summary_by_pair, output_dir / "sa_stress_summary_by_n_ratio.csv")
    save_json(
        {
            "breakdown": breakdown,
            "regions": region_summary,
            "hardest_reports": hard_report,
            "algorithm_health": algorithm_health,
        },
        output_dir / "sa_stress_hard_regions.json",
    )

    report_text = build_sa_stress_report(
        overall_summary={},
        algorithm_summaries=algorithm_health,
        breakdown=breakdown,
        region_summary=region_summary,
        hard_instance_report=hard_report,
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
    save_json(payload, output_dir / "sa_stress_summary.json")
    return payload


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Large-scale stress test for Simulated Annealing.")
    parser.add_argument("--instances-per-cell", type=int, default=SA_STRESS_INSTANCES_PER_CELL)
    parser.add_argument("--solver-runs-per-instance", type=int, default=SA_STRESS_SOLVER_RUNS_PER_INSTANCE)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--baseline-only", action="store_true")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    payload = run_sa_stress_test(
        instances_per_cell=max(1, args.instances_per_cell),
        solver_runs_per_instance=max(1, args.solver_runs_per_instance),
        include_enhanced=not args.baseline_only,
        base_seed=args.base_seed,
    )
    print(SA_STRESS_RESULTS_DIR / "analysis_report.md")
    print(json.dumps(payload["algorithm_health"], indent=2))


if __name__ == "__main__":
    main()
