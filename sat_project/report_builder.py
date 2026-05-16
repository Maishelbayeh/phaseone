from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List, Mapping, Sequence


def _pick_best_quality(summary_rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return max(summary_rows, key=lambda row: (float(row["mean_satisfaction_rate"]), float(row["max_best_satisfied_clauses"])))


def _pick_fastest(summary_rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return min(summary_rows, key=lambda row: float(row["mean_runtime"]))


def _pick_tradeoff(summary_rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    def score(row: Mapping[str, Any]) -> float:
        runtime = max(1e-9, float(row["mean_runtime"]))
        quality = float(row["mean_satisfaction_rate"])
        return quality / runtime

    return max(summary_rows, key=score)


def _compare_rows(summary_rows: Sequence[Mapping[str, Any]], name_a: str, name_b: str) -> str:
    row_map = {str(r["algorithm_name"]): r for r in summary_rows}
    if name_a not in row_map or name_b not in row_map:
        return f"Comparison between {name_a} and {name_b} was not available in this run."
    a = row_map[name_a]
    b = row_map[name_b]
    a_quality = float(a["mean_satisfaction_rate"])
    b_quality = float(b["mean_satisfaction_rate"])
    a_runtime = float(a["mean_runtime"])
    b_runtime = float(b["mean_runtime"])
    return (
        f"{name_a}: mean satisfaction={a_quality:.4f}, mean runtime={a_runtime:.4f}s; "
        f"{name_b}: mean satisfaction={b_quality:.4f}, mean runtime={b_runtime:.4f}s."
    )


def build_markdown_report(
    *,
    instance_name: str,
    per_run_rows: Sequence[Mapping[str, Any]],
    summary_rows: Sequence[Mapping[str, Any]],
    complexity_rows: Sequence[Mapping[str, Any]],
    best_params: Mapping[str, Mapping[str, Any]],
) -> str:
    if not summary_rows:
        return "# Solver Comparison Report\n\nNo results were produced."

    best_quality = _pick_best_quality(summary_rows)
    fastest = _pick_fastest(summary_rows)
    tradeoff = _pick_tradeoff(summary_rows)

    scaling_text = "Empirical scaling was computed from available instance-size runs."
    if complexity_rows:
        exponents = [float(row["empirical_scaling_exponent_loglog"]) for row in complexity_rows]
        scaling_text = (
            "Empirical scaling (log-log runtime slope) range: "
            f"{min(exponents):.3f} to {max(exponents):.3f} across compared solvers."
        )

    lines: List[str] = [
        "# Solver Comparison Report",
        "",
        f"- Instance: `{instance_name}`",
        f"- Total run records: {len(per_run_rows)}",
        "",
        "## Main Findings",
        "",
        f"1. **Best solution quality**: {best_quality['algorithm_name']} "
        f"(mean satisfaction rate={float(best_quality['mean_satisfaction_rate']):.4f}).",
        f"2. **Fastest solver**: {fastest['algorithm_name']} "
        f"(mean runtime={float(fastest['mean_runtime']):.4f} s).",
        f"3. **Best speed-quality tradeoff**: {tradeoff['algorithm_name']}.",
        "4. **Standalone GA vs Hybrid BSGO-GA**: "
        + _compare_rows(summary_rows, "Genetic Algorithm", "Hybrid BSGO-GA"),
        "5. **Standalone Swarm vs Hybrid BSGO-GA**: "
        + _compare_rows(summary_rows, "Binary Swarm (BSGO)", "Hybrid BSGO-GA"),
        "6. **Runtime scaling observations**: " + scaling_text,
        "7. **Estimated time complexity (implementation-level)** is listed in `complexity_summary.csv` and should be cited as practical/implementation estimates, not formal bounds.",
        "",
        "## Suggested Paper Wording",
        "",
        (
            "In our implementation-level comparison on MAX-SAT instances, the algorithms exhibit a clear "
            "quality-runtime tradeoff. Population-based methods generally improve satisfaction quality at "
            "higher computational cost, while trajectory-based methods remain faster. The standalone Genetic "
            "Algorithm and pure binary swarm baseline allow direct attribution of gains from hybridization in "
            "Hybrid BSGO-GA. We report both estimated implementation-level complexity and empirical runtime "
            "scaling with increasing instance size to avoid overstating formal asymptotic claims."
        ),
        "",
        "## Best Parameters Snapshot",
        "",
    ]

    for solver_name, payload in best_params.items():
        params = payload.get("params", {})
        lines.append(f"- **{solver_name}**: seed={payload.get('random_seed')} params={params}")

    lines.append("")
    lines.append("## Summary Statistics")
    lines.append("")
    lines.append("| Solver | Mean Sat Rate | Best Sat Rate | Mean Runtime (s) | Rank |")
    lines.append("|---|---:|---:|---:|---:|")
    for row in sorted(summary_rows, key=lambda r: int(r["relative_rank"])):
        lines.append(
            f"| {row['algorithm_name']} | {float(row['mean_satisfaction_rate']):.4f} | "
            f"{float(row['best_satisfaction_rate']):.4f} | {float(row['mean_runtime']):.4f} | "
            f"{int(row['relative_rank'])} |"
        )

    if complexity_rows:
        lines.append("")
        lines.append("## Complexity Notes")
        lines.append("")
        lines.append("| Solver | Estimated complexity | Empirical slope | Fit (R^2) |")
        lines.append("|---|---|---:|---:|")
        for row in complexity_rows:
            lines.append(
                f"| {row['algorithm_name']} | {row['estimated_time_complexity']} | "
                f"{float(row['empirical_scaling_exponent_loglog']):.3f} | {float(row['empirical_fit_r2']):.3f} |"
            )

    lines.append("")
    return "\n".join(lines)


def build_sa_stress_report(
    *,
    overall_summary: Mapping[str, Any],
    algorithm_summaries: Sequence[Mapping[str, Any]],
    breakdown: Mapping[str, Any],
    region_summary: Mapping[str, Any],
    hard_instance_report: Mapping[str, Any],
    title: str = "Simulated Annealing Stress-Test Report",
) -> str:
    lines: List[str] = [f"# {title}", "", "## Overall Health", ""]
    for row in algorithm_summaries:
        lines.append(
            f"- `{row['algorithm_name']}`: mean satisfaction `{100.0 * float(row['overall_mean_satisfaction_rate']):.3f}%`, "
            f"mean runtime `{float(row['overall_mean_runtime_seconds']):.3f}s`, "
            f"full satisfaction rate `{100.0 * float(row['overall_full_satisfaction_rate']):.2f}%`, "
            f"worst runtime `{float(row['worst_case_runtime_seconds']):.3f}s`, "
            f"worst satisfaction `{100.0 * float(row['worst_case_satisfaction_rate']):.3f}%`"
        )
    lines.extend(["", "## Breakdown Detection", ""])
    for algorithm_name, payload in breakdown.items():
        lines.append(f"- `{algorithm_name}` first problematic `n`: `{payload.get('first_problematic_n')}`")
        lines.append(f"- `{algorithm_name}` first problematic `r`: `{payload.get('first_problematic_r')}`")
        lines.append(f"- `{algorithm_name}` hardest `(n, r)` region: `{payload.get('hardest_region')}`")
    lines.extend(["", "## Region Summary", ""])
    for algorithm_name, payload in region_summary.items():
        lines.append(f"- `{algorithm_name}` easiest region: `{payload.get('easiest_region')}`")
        lines.append(f"- `{algorithm_name}` hardest region: `{payload.get('hardest_region')}`")
    lines.extend(["", "## Hard Instance Lists", "", "- Top 10 hardest instances:"])
    for row in hard_instance_report.get("hardest_instances", []):
        lines.append(
            f"  - `{row['instance_name']}` / `{row['algorithm_name']}`: satisfaction `{100.0 * float(row['satisfaction_rate']):.3f}%`, "
            f"unsatisfied `{row['unsatisfied_clauses']}`, runtime `{float(row['runtime_seconds']):.3f}s`"
        )
    lines.append("- Top 10 slowest instances:")
    for row in hard_instance_report.get("slowest_instances", []):
        lines.append(
            f"  - `{row['instance_name']}` / `{row['algorithm_name']}`: runtime `{float(row['runtime_seconds']):.3f}s`, "
            f"satisfaction `{100.0 * float(row['satisfaction_rate']):.3f}%`"
        )
    lines.append("- Top 10 near-miss instances:")
    for row in hard_instance_report.get("near_miss_instances", []):
        lines.append(
            f"  - `{row['instance_name']}` / `{row['algorithm_name']}`: unsatisfied `{row['unsatisfied_clauses']}`, "
            f"satisfaction `{100.0 * float(row['satisfaction_rate']):.3f}%`, runtime `{float(row['runtime_seconds']):.3f}s`"
        )
    lines.append("")
    return "\n".join(lines)
