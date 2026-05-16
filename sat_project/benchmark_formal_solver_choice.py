from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from config import (
    FORMAL_COMPARE_PLOTS_DIR,
    FORMAL_COMPARE_RESULTS_DIR,
    genetic_algorithm_defaults,
    enhanced_sa_defaults,
    memetic_ga_sa_enhanced_defaults,
)
from plotting import (
    plot_boxplots_by_group,
    plot_heatmap,
    plot_metric_vs_group,
    plot_runtime_vs_satisfaction_scatter,
)
from sat_generator import load_instance_formula_from_file
from solvers.registry import build_solver_registry


INSTANCE_ROOT = Path(__file__).resolve().parent.parent / "data" / "instances"
INSTANCE_PATTERN = re.compile(r"3sat_n(?P<n>\d+)_r(?P<r>[0-9.]+)\.json$")


@dataclass(frozen=True)
class FormalRunRow:
    instance_name: str
    n: int
    ratio: float
    m: int
    solver_key: str
    algorithm_name: str
    run_id: int
    random_seed: int
    best_satisfied_clauses: int
    total_clauses: int
    satisfaction_rate: float
    unsatisfied_clauses: int
    runtime_seconds: float
    iterations_used: int
    fully_satisfied: bool


def _save_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows_list[0].keys()))
        writer.writeheader()
        writer.writerows(rows_list)


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_formal_instances() -> List[dict[str, Any]]:
    instances: List[dict[str, Any]] = []
    for path in sorted(INSTANCE_ROOT.glob("3sat_n*_r*.json")):
        match = INSTANCE_PATTERN.match(path.name)
        if not match:
            continue
        instances.append(
            {
                "path": path,
                "instance_name": path.name,
                "n": int(match.group("n")),
                "ratio": float(match.group("r")),
            }
        )
    instances.sort(key=lambda item: (item["n"], item["ratio"]))
    return instances


def _solver_configs(n: int) -> List[tuple[str, Dict[str, Any]]]:
    return [
        ("simulated_annealing", enhanced_sa_defaults(n)),
        ("genetic_algorithm", genetic_algorithm_defaults(n)),
        ("memetic_ga_sa", memetic_ga_sa_enhanced_defaults(n)),
    ]


def _formal_memetic_defaults(n: int, *, speed_mode: str) -> Dict[str, Any]:
    config = memetic_ga_sa_enhanced_defaults(n)
    if speed_mode == "full":
        return config
    config = dict(config)
    if n >= 400:
        config["population_size"] = min(int(config.get("population_size", 56)), 40)
        config["max_generations"] = min(int(config.get("max_generations", 220)), 120)
        config["local_search_every"] = max(int(config.get("local_search_every", 10)), 15)
        config["sa_max_iterations"] = min(int(config.get("sa_max_iterations", 900)), 450)
        config["incremental_candidate_pool"] = min(int(config.get("incremental_candidate_pool", max(40, n // 3))), 90)
        config["path_relink_every"] = max(int(config.get("path_relink_every", 10)), 20)
        config["hardcase_multi_run_attempts"] = 1
        config["hardcase_sa_scale"] = min(float(config.get("hardcase_sa_scale", 1.25)), 1.0)
    elif n >= 250:
        config["max_generations"] = min(int(config.get("max_generations", 220)), 160)
        config["sa_max_iterations"] = min(int(config.get("sa_max_iterations", 900)), 650)
        config["incremental_candidate_pool"] = min(int(config.get("incremental_candidate_pool", max(40, n // 3))), 120)
        config["hardcase_multi_run_attempts"] = 1
    return config


def _formal_ga_defaults(n: int, *, speed_mode: str) -> Dict[str, Any]:
    config = genetic_algorithm_defaults(n)
    if speed_mode == "full":
        return config
    config = dict(config)
    config["annealing_trials"] = 1
    if n >= 150:
        config["population_size"] = min(int(config.get("population_size", 96)), 72)
        config["max_generations"] = min(int(config.get("max_generations", 2 * n)), 300)
    if n >= 400:
        config["population_size"] = min(int(config.get("population_size", 96)), 60)
        config["max_generations"] = min(int(config.get("max_generations", 2 * n)), 320)
        config["local_search_every"] = max(int(config.get("local_search_every", 5)), 10)
    elif n >= 250:
        config["max_generations"] = min(int(config.get("max_generations", 2 * n)), 420)
    return config


def _formal_solver_configs(n: int, *, memetic_speed_mode: str) -> List[tuple[str, Dict[str, Any]]]:
    return [
        ("simulated_annealing", enhanced_sa_defaults(n)),
        ("genetic_algorithm", _formal_ga_defaults(n, speed_mode=memetic_speed_mode)),
        ("memetic_ga_sa", _formal_memetic_defaults(n, speed_mode=memetic_speed_mode)),
    ]


def _select_solver_configs(
    n: int,
    *,
    memetic_speed_mode: str,
    solver_keys: Sequence[str],
) -> List[tuple[str, Dict[str, Any]]]:
    wanted = {str(key).strip().lower() for key in solver_keys if str(key).strip()}
    configs = _formal_solver_configs(n, memetic_speed_mode=memetic_speed_mode)
    if not wanted:
        return configs
    return [(key, cfg) for key, cfg in configs if key in wanted]



def _summarize(rows: Sequence[Mapping[str, Any]], group_keys: Sequence[str]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple, List[Mapping[str, Any]]] = {}
    for row in rows:
        key = tuple(row[name] for name in group_keys)
        grouped.setdefault(key, []).append(row)
    summary: List[Dict[str, Any]] = []
    for key, group in sorted(grouped.items()):
        payload: Dict[str, Any] = {
            "mean_satisfaction_rate": mean(float(row["satisfaction_rate"]) for row in group),
            "mean_runtime_seconds": mean(float(row["runtime_seconds"]) for row in group),
            "mean_unsatisfied_clauses": mean(float(row["unsatisfied_clauses"]) for row in group),
            "full_satisfaction_rate": mean(1.0 if bool(row["fully_satisfied"]) else 0.0 for row in group),
            "full_satisfaction_count": sum(1 for row in group if bool(row["fully_satisfied"])),
            "run_count": len(group),
            "best_satisfaction_rate": max(float(row["satisfaction_rate"]) for row in group),
            "worst_satisfaction_rate": min(float(row["satisfaction_rate"]) for row in group),
            "worst_runtime_seconds": max(float(row["runtime_seconds"]) for row in group),
        }
        for name, value in zip(group_keys, key):
            payload[name] = value
        summary.append(payload)
    return summary


def _overall_summary(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return _summarize(rows, ("algorithm_name",))


def _find_best_choice(overall_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    best_quality = max(overall_rows, key=lambda row: float(row["mean_satisfaction_rate"]))
    best_full = max(overall_rows, key=lambda row: (float(row["full_satisfaction_rate"]), float(row["mean_satisfaction_rate"])))
    fastest = min(overall_rows, key=lambda row: float(row["mean_runtime_seconds"]))
    best_tradeoff = max(
        overall_rows,
        key=lambda row: (
            float(row["full_satisfaction_rate"]),
            float(row["mean_satisfaction_rate"]),
            -float(row["mean_runtime_seconds"]),
        ),
    )
    return {
        "best_quality": best_quality,
        "best_full_satisfaction": best_full,
        "fastest": fastest,
        "best_tradeoff": best_tradeoff,
    }


def _render_report(
    *,
    overall_rows: Sequence[Mapping[str, Any]],
    by_n: Sequence[Mapping[str, Any]],
    by_ratio: Sequence[Mapping[str, Any]],
    by_instance: Sequence[Mapping[str, Any]],
    best_choice: Mapping[str, Any],
) -> str:
    lines = [
        "# Formal Solver Choice Analysis",
        "",
        "## Scope",
        "",
        "- Dataset: top-level `data/instances/*.json` only.",
        "- Compared solvers: `Enhanced SA`, `Genetic Algorithm`, `Memetic GA-SA`.",
        "- Goal: decide the best practical choice for your formal benchmark set.",
        "",
        "## Overall Ranking",
        "",
    ]
    ordered = sorted(overall_rows, key=lambda row: (-float(row["mean_satisfaction_rate"]), float(row["mean_runtime_seconds"])))
    for row in ordered:
        lines.append(
            f"- `{row['algorithm_name']}`: mean satisfaction `{100.0 * float(row['mean_satisfaction_rate']):.3f}%`, "
            f"full satisfaction `{int(row['full_satisfaction_count'])}/{int(row['run_count'])}`, "
            f"mean runtime `{float(row['mean_runtime_seconds']):.3f}s`, "
            f"mean unsatisfied `{float(row['mean_unsatisfied_clauses']):.3f}`"
        )
    lines.extend(
        [
            "",
            "## Best Choice",
            "",
            f"- Best quality: `{best_choice['best_quality']['algorithm_name']}`",
            f"- Best full-satisfaction rate: `{best_choice['best_full_satisfaction']['algorithm_name']}`",
            f"- Fastest: `{best_choice['fastest']['algorithm_name']}`",
            f"- Best overall tradeoff: `{best_choice['best_tradeoff']['algorithm_name']}`",
            "",
            "## Interpretation",
            "",
        ]
    )

    if best_choice["best_tradeoff"]["algorithm_name"] == best_choice["best_quality"]["algorithm_name"]:
        lines.append(
            f"- The recommended default on this formal dataset is `{best_choice['best_tradeoff']['algorithm_name']}` because it is also the top quality option."
        )
    else:
        lines.append(
            f"- `{best_choice['best_quality']['algorithm_name']}` gives the strongest quality, but `{best_choice['best_tradeoff']['algorithm_name']}` gives the best balance of quality and runtime."
        )
    lines.append(
        f"- `{best_choice['fastest']['algorithm_name']}` remains the speed baseline."
    )

    hardest_instances = sorted(
        by_instance,
        key=lambda row: (
            float(row["mean_satisfaction_rate"]),
            float(row["full_satisfaction_rate"]),
            -float(row["mean_runtime_seconds"]),
        ),
    )[:10]
    lines.extend(["", "## Hardest Cases", ""])
    for row in hardest_instances:
        lines.append(
            f"- `{row['instance_name']}` / `{row['algorithm_name']}`: satisfaction `{100.0 * float(row['mean_satisfaction_rate']):.3f}%`, "
            f"full satisfaction `{int(row['full_satisfaction_count'])}/{int(row['run_count'])}`, runtime `{float(row['mean_runtime_seconds']):.3f}s`"
        )

    return "\n".join(lines) + "\n"


def _load_rows_from_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        for raw in reader:
            row: Dict[str, Any] = dict(raw)
            row["n"] = int(row["n"])
            row["ratio"] = float(row["ratio"])
            row["m"] = int(row["m"])
            row["run_id"] = int(row["run_id"])
            row["random_seed"] = int(row["random_seed"])
            row["best_satisfied_clauses"] = int(row["best_satisfied_clauses"])
            row["total_clauses"] = int(row["total_clauses"])
            row["satisfaction_rate"] = float(row["satisfaction_rate"])
            row["unsatisfied_clauses"] = int(row["unsatisfied_clauses"])
            row["runtime_seconds"] = float(row["runtime_seconds"])
            row["iterations_used"] = int(row["iterations_used"])
            row["fully_satisfied"] = str(row["fully_satisfied"]).strip().lower() in ("1", "true", "yes")
            rows.append(row)
    return rows


def run_formal_solver_choice_benchmark(
    *,
    runs_per_solver: int = 1,
    base_seed: int = 42,
    output_dir: Path = FORMAL_COMPARE_RESULTS_DIR,
    memetic_speed_mode: str = "practical",
    resume_from_per_run: bool = False,
    solver_keys: Sequence[str] = ("simulated_annealing", "genetic_algorithm", "memetic_ga_sa"),
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    per_run_path = output_dir / "formal_solver_choice_per_run.csv"
    if resume_from_per_run and per_run_path.exists():
        rows = _load_rows_from_csv(per_run_path)
    else:
        registry = build_solver_registry()
        instances = _load_formal_instances()

        per_run_path.parent.mkdir(parents=True, exist_ok=True)
        per_run_file = per_run_path.open("w", newline="", encoding="utf-8")
        per_run_writer = csv.DictWriter(per_run_file, fieldnames=list(FormalRunRow.__dataclass_fields__.keys()))
        per_run_writer.writeheader()

        for instance in instances:
            formula = load_instance_formula_from_file(instance["path"])
            selected = _select_solver_configs(
                instance["n"],
                memetic_speed_mode=memetic_speed_mode,
                solver_keys=solver_keys,
            )
            for solver_index, (solver_key, config) in enumerate(selected):
                solver = registry[solver_key]
                for run_id in range(runs_per_solver):
                    seed = (
                        base_seed
                        + instance["n"] * 100_003
                        + int(round(instance["ratio"] * 100)) * 503
                        + solver_index * 7_919
                        + run_id
                    )
                    run_config = dict(config)
                    run_config["random_seed"] = seed
                    print(
                        f"[formal] instance={instance['instance_name']} solver={solver_key} run={run_id + 1}/{runs_per_solver}",
                        flush=True,
                    )
                    result = solver.solve(formula, run_config)
                    row = asdict(
                        FormalRunRow(
                            instance_name=instance["instance_name"],
                            n=instance["n"],
                            ratio=instance["ratio"],
                            m=formula.num_clauses,
                            solver_key=solver_key,
                            algorithm_name=result.algorithm_name,
                            run_id=run_id + 1,
                            random_seed=seed,
                            best_satisfied_clauses=result.best_satisfied_clauses,
                            total_clauses=result.total_clauses,
                            satisfaction_rate=result.satisfaction_rate,
                            unsatisfied_clauses=result.total_clauses - result.best_satisfied_clauses,
                            runtime_seconds=result.runtime_seconds,
                            iterations_used=result.iterations_used,
                            fully_satisfied=result.fully_satisfied,
                        )
                    )
                    rows.append(row)
                    per_run_writer.writerow(row)
                    per_run_file.flush()

        per_run_file.close()

    overall_rows = _overall_summary(rows)
    by_n = _summarize(rows, ("algorithm_name", "n"))
    by_ratio = _summarize(rows, ("algorithm_name", "ratio"))
    by_instance = _summarize(rows, ("algorithm_name", "instance_name", "n", "ratio"))
    best_choice = _find_best_choice(overall_rows)

    _save_csv(output_dir / "formal_solver_choice_overall.csv", overall_rows)
    _save_csv(output_dir / "formal_solver_choice_by_n.csv", by_n)
    _save_csv(output_dir / "formal_solver_choice_by_ratio.csv", by_ratio)
    _save_csv(output_dir / "formal_solver_choice_by_instance.csv", by_instance)
    _save_json(
        output_dir / "formal_solver_choice_summary.json",
        {
            "overall": overall_rows,
            "by_n": by_n,
            "by_ratio": by_ratio,
            "by_instance": by_instance,
            "best_choice": best_choice,
        },
    )

    plot_metric_vs_group(
        by_n,
        group_key="n",
        metric_key="mean_satisfaction_rate",
        y_label="Mean satisfaction rate",
        title="Formal data: mean satisfaction vs n",
        output_base_path=plots_dir / "mean_satisfaction_vs_n",
    )
    plot_metric_vs_group(
        by_ratio,
        group_key="ratio",
        metric_key="mean_satisfaction_rate",
        y_label="Mean satisfaction rate",
        title="Formal data: mean satisfaction vs ratio",
        output_base_path=plots_dir / "mean_satisfaction_vs_ratio",
    )
    plot_metric_vs_group(
        by_n,
        group_key="n",
        metric_key="mean_runtime_seconds",
        y_label="Mean runtime (seconds)",
        title="Formal data: mean runtime vs n",
        output_base_path=plots_dir / "mean_runtime_vs_n",
    )
    plot_metric_vs_group(
        by_ratio,
        group_key="ratio",
        metric_key="mean_runtime_seconds",
        y_label="Mean runtime (seconds)",
        title="Formal data: mean runtime vs ratio",
        output_base_path=plots_dir / "mean_runtime_vs_ratio",
    )
    plot_metric_vs_group(
        by_n,
        group_key="n",
        metric_key="full_satisfaction_rate",
        y_label="Full satisfaction rate",
        title="Formal data: full satisfaction rate vs n",
        output_base_path=plots_dir / "full_satisfaction_rate_vs_n",
    )
    plot_metric_vs_group(
        by_ratio,
        group_key="ratio",
        metric_key="full_satisfaction_rate",
        y_label="Full satisfaction rate",
        title="Formal data: full satisfaction rate vs ratio",
        output_base_path=plots_dir / "full_satisfaction_rate_vs_ratio",
    )
    plot_runtime_vs_satisfaction_scatter(
        rows,
        output_base_path=plots_dir / "runtime_vs_satisfaction",
        title="Formal data: runtime vs satisfaction",
    )
    plot_boxplots_by_group(
        rows,
        group_key="n",
        metric_key="satisfaction_rate",
        title="Formal data: satisfaction by n",
        y_label="Satisfaction rate",
        output_base_path=plots_dir / "satisfaction_boxplot_by_n",
    )
    plot_boxplots_by_group(
        rows,
        group_key="n",
        metric_key="runtime_seconds",
        title="Formal data: runtime by n",
        y_label="Runtime (seconds)",
        output_base_path=plots_dir / "runtime_boxplot_by_n",
    )

    for algorithm_name in sorted({str(row["algorithm_name"]) for row in by_instance}):
        token = algorithm_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        rows_for_algorithm = [row for row in by_instance if str(row["algorithm_name"]) == algorithm_name]
        plot_heatmap(
            rows_for_algorithm,
            value_key="mean_satisfaction_rate",
            title=f"{algorithm_name}: satisfaction heatmap",
            output_base_path=plots_dir / f"{token}_satisfaction_heatmap",
            value_label="Mean satisfaction rate",
        )
        plot_heatmap(
            rows_for_algorithm,
            value_key="full_satisfaction_rate",
            title=f"{algorithm_name}: full satisfaction heatmap",
            output_base_path=plots_dir / f"{token}_full_satisfaction_heatmap",
            value_label="Full satisfaction rate",
        )
        plot_heatmap(
            rows_for_algorithm,
            value_key="mean_runtime_seconds",
            title=f"{algorithm_name}: runtime heatmap",
            output_base_path=plots_dir / f"{token}_runtime_heatmap",
            value_label="Mean runtime (seconds)",
        )

    (output_dir / "analysis_report.md").write_text(
        _render_report(
            overall_rows=overall_rows,
            by_n=by_n,
            by_ratio=by_ratio,
            by_instance=by_instance,
            best_choice=best_choice,
        ),
        encoding="utf-8",
    )

    return {
        "overall": overall_rows,
        "by_n": by_n,
        "by_ratio": by_ratio,
        "by_instance": by_instance,
        "best_choice": best_choice,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare enhanced SA, GA, and Memetic GA-SA on formal data instances.")
    parser.add_argument("--runs-per-solver", type=int, default=1)
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--memetic-speed-mode", choices=("practical", "full"), default="practical")
    parser.add_argument("--resume-from-per-run", action="store_true")
    parser.add_argument(
        "--solvers",
        type=str,
        default="simulated_annealing,genetic_algorithm,memetic_ga_sa",
    )
    parser.add_argument("--output-dir", type=str, default="")
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    solver_keys = [item.strip() for item in str(args.solvers).split(",") if item.strip()]
    output_dir = FORMAL_COMPARE_RESULTS_DIR
    if str(args.output_dir).strip():
        output_dir = Path(str(args.output_dir)).resolve()
    payload = run_formal_solver_choice_benchmark(
        runs_per_solver=max(1, args.runs_per_solver),
        base_seed=args.base_seed,
        memetic_speed_mode=str(args.memetic_speed_mode),
        resume_from_per_run=bool(args.resume_from_per_run),
        solver_keys=solver_keys,
        output_dir=output_dir,
    )
    print(output_dir / "analysis_report.md")
    print(json.dumps(payload["best_choice"], indent=2))


if __name__ == "__main__":
    main()
