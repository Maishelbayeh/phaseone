from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

from plotting import (
    plot_convergence_history,
    plot_move_acceptance_categories,
    plot_restart_satisfaction_histogram,
    plot_success_rate_by_setting,
    plot_temperature_history,
)


def save_csv(rows: Iterable[Mapping[str, Any]], path: Path) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=list(rows_list[0].keys()))
        writer.writeheader()
        writer.writerows(rows_list)


def save_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=2)


def _render_summary_line(label: str, summary: Mapping[str, Any]) -> str:
    return (
        f"- `{label}`: mean satisfaction `{100.0 * float(summary['mean_satisfaction_rate']):.3f}%`, "
        f"full satisfactions `{int(summary['full_satisfaction_count'])}/{int(summary['run_count'])}`, "
        f"mean runtime `{float(summary['mean_runtime_seconds']):.3f}s`, "
        f"success rate `{100.0 * float(summary['success_rate']):.2f}%`, "
        f"runtime-to-success `{float(summary['runtime_to_success']):.3f}`"
    )


def build_sa_report(data: Mapping[str, Any]) -> str:
    tuning_trials = data["tuning_trials"]
    comparison = data["comparison"]
    best_setting = data["best_enhanced_setting"]
    focus_run = data["focus_run"]
    lines = [
        "# Enhanced SA Analysis",
        "",
        "## Scope",
        "",
        "- Goal: improve Simulated Annealing to maximize the probability of full satisfaction, not only average clause satisfaction.",
        "- Comparison modes: baseline single-run SA versus enhanced restart-aware SA.",
        f"- Tuning trials evaluated: `{len(tuning_trials)}` enhanced settings plus one baseline reference.",
        f"- Benchmark instances: `{len(comparison['per_run'])}` total solver-instance runs.",
        "",
        "## Comparison Summary",
        "",
        _render_summary_line("baseline", comparison["baseline_summary"]),
        _render_summary_line("enhanced_best", comparison["enhanced_summary"]),
        "",
        "## Best Enhanced Setting",
        "",
        f"- Winning label: `{best_setting['setting_label']}`",
        f"- Config: `{json.dumps(best_setting['config'], sort_keys=True)}`",
        "",
        "## Focus Run Diagnostics",
        "",
        f"- Focus instance: `{focus_run['instance_name']}`",
        f"- Best merit: `{focus_run['best_satisfied_clauses']}/{focus_run['total_clauses']}`",
        f"- Restart count used: `{focus_run['restart_count']}`",
        f"- Reheats used: `{focus_run['reheat_count']}`",
        f"- Accepted better/equal/worse moves: `{focus_run['accepted_better_moves']}` / `{focus_run['accepted_equal_moves']}` / `{focus_run['accepted_worse_moves']}`",
        "",
        "## Notes",
        "",
        "- The enhanced mode biases proposals toward unsatisfied clauses, adds reheating, and uses multiple restart strategies with optional elite transfer.",
        "- Success-rate plots should be interpreted together with runtime-to-success, because the more aggressive settings can improve hit rate at extra cost.",
    ]
    return "\n".join(lines) + "\n"


def create_sa_analysis_artifacts(
    *,
    output_dir: Path,
    comparison_payload: Mapping[str, Any],
    tuning_trials: Sequence[Mapping[str, Any]],
    best_enhanced_setting: Mapping[str, Any],
    focus_result: Mapping[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    report_payload = {
        "tuning_trials": list(tuning_trials),
        "comparison": comparison_payload,
        "best_enhanced_setting": dict(best_enhanced_setting),
        "focus_run": dict(focus_result),
    }
    save_json(report_payload, output_dir / "sa_enhanced_analysis.json")
    (output_dir / "analysis_report.md").write_text(
        build_sa_report(report_payload),
        encoding="utf-8",
    )

    plot_convergence_history(
        focus_result["best_history"],
        focus_result["total_clauses"],
        output_path=plots_dir / "best_fitness_over_iterations.png",
        title="Enhanced SA: best fitness over iterations",
    )
    plot_temperature_history(
        focus_result["temperature_history"],
        output_path=plots_dir / "temperature_over_iterations.png",
        title="Enhanced SA: temperature over iterations",
    )
    plot_move_acceptance_categories(
        focus_result["accepted_move_history"],
        output_path=plots_dir / "accepted_move_categories_over_time.png",
        title="Enhanced SA: accepted move categories",
    )
    plot_restart_satisfaction_histogram(
        focus_result["final_satisfaction_rates"],
        output_path=plots_dir / "final_satisfaction_histogram.png",
        title="Enhanced SA: final satisfaction across restarts",
    )
    plot_success_rate_by_setting(
        [trial["setting_label"] for trial in tuning_trials],
        [float(trial["success_rate"]) for trial in tuning_trials],
        output_path=plots_dir / "full_satisfaction_success_rate_by_setting.png",
        title="Enhanced SA: full satisfaction success rate by setting",
    )


def result_to_focus_payload(
    *,
    instance_name: str,
    result: Mapping[str, Any],
) -> Mapping[str, Any]:
    restart_summaries = result.get("restart_summaries", [])
    final_satisfaction_rates = result.get("final_satisfaction_rates", [])
    focus_summary = restart_summaries[0] if restart_summaries else {}
    return {
        "instance_name": instance_name,
        "best_satisfied_clauses": int(result["best_merit"]),
        "total_clauses": int(result["total_clauses"]),
        "restart_count": int(result["restart_count"]),
        "reheat_count": int(result["reheat_count"]),
        "accepted_better_moves": int(result["accepted_better_moves"]),
        "accepted_equal_moves": int(result["accepted_equal_moves"]),
        "accepted_worse_moves": int(result["accepted_worse_moves"]),
        "best_history": list(result["merit_history"]),
        "temperature_history": list(result["temperature_history"]),
        "accepted_move_history": list(result["accepted_move_history"]),
        "final_satisfaction_rates": list(final_satisfaction_rates),
        "first_restart_summary": focus_summary,
    }


def summarize_runs(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    if not rows:
        return {
            "mean_satisfaction_rate": 0.0,
            "full_satisfaction_count": 0,
            "mean_runtime_seconds": 0.0,
            "success_rate": 0.0,
            "runtime_to_success": 0.0,
            "run_count": 0,
        }
    mean_satisfaction_rate = mean(float(row["satisfaction_rate"]) for row in rows)
    mean_runtime_seconds = mean(float(row["runtime_seconds"]) for row in rows)
    full_count = sum(1 for row in rows if bool(row["fully_satisfied"]))
    run_count = len(rows)
    success_rate = full_count / run_count
    runtime_to_success = mean_runtime_seconds / max(success_rate, 1e-9)
    return {
        "mean_satisfaction_rate": mean_satisfaction_rate,
        "full_satisfaction_count": full_count,
        "mean_runtime_seconds": mean_runtime_seconds,
        "success_rate": success_rate,
        "runtime_to_success": runtime_to_success,
        "run_count": run_count,
    }


def dataclass_sequence_to_dicts(items: Sequence[Any]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]
