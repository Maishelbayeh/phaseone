from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Sequence


def _group_rows(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Dict[tuple, List[Mapping[str, Any]]]:
    grouped: Dict[tuple, List[Mapping[str, Any]]] = {}
    for row in rows:
        key = tuple(row[name] for name in keys)
        grouped.setdefault(key, []).append(row)
    return grouped


def summarize_rows(rows: Sequence[Mapping[str, Any]], *, group_keys: Sequence[str]) -> List[Dict[str, Any]]:
    grouped = _group_rows(rows, group_keys)
    output: List[Dict[str, Any]] = []
    for key, group in sorted(grouped.items()):
        mean_satisfaction_rate = mean(float(row["satisfaction_rate"]) for row in group)
        mean_runtime = mean(float(row["runtime_seconds"]) for row in group)
        mean_unsatisfied = mean(float(row["unsatisfied_clauses"]) for row in group)
        full_count = sum(1 for row in group if bool(row["fully_satisfied"]))
        run_count = len(group)
        payload: Dict[str, Any] = {
            "mean_satisfaction_rate": mean_satisfaction_rate,
            "mean_runtime_seconds": mean_runtime,
            "full_satisfaction_success_rate": full_count / run_count,
            "mean_unsatisfied_clauses": mean_unsatisfied,
            "run_count": run_count,
            "full_satisfaction_count": full_count,
            "worst_runtime_seconds": max(float(row["runtime_seconds"]) for row in group),
            "worst_satisfaction_rate": min(float(row["satisfaction_rate"]) for row in group),
        }
        for name, value in zip(group_keys, key):
            payload[name] = value
        output.append(payload)
    return output


def compute_global_health(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}
    return {
        "overall_mean_satisfaction_rate": mean(float(row["satisfaction_rate"]) for row in rows),
        "overall_mean_runtime_seconds": mean(float(row["runtime_seconds"]) for row in rows),
        "overall_full_satisfaction_rate": mean(1.0 if bool(row["fully_satisfied"]) else 0.0 for row in rows),
        "worst_case_runtime_seconds": max(float(row["runtime_seconds"]) for row in rows),
        "worst_case_satisfaction_rate": min(float(row["satisfaction_rate"]) for row in rows),
    }


def detect_breakdown(
    *,
    summary_by_n: Sequence[Mapping[str, Any]],
    summary_by_r: Sequence[Mapping[str, Any]],
    summary_by_pair: Sequence[Mapping[str, Any]],
    thresholds: Mapping[str, float],
) -> Dict[str, Any]:
    def is_problem(row: Mapping[str, Any]) -> bool:
        return (
            float(row["full_satisfaction_success_rate"]) < float(thresholds["full_satisfaction_success_rate"])
            or float(row["mean_satisfaction_rate"]) < float(thresholds["mean_satisfaction_rate_warn"])
            or float(row["mean_runtime_seconds"]) > float(thresholds["mean_runtime_seconds"])
            or float(row["mean_unsatisfied_clauses"]) > float(thresholds["mean_unsatisfied_clauses"])
        )

    problematic_n = [row for row in summary_by_n if is_problem(row)]
    problematic_r = [row for row in summary_by_r if is_problem(row)]
    problematic_pairs = [row for row in summary_by_pair if is_problem(row)]
    hardest_region = None
    if summary_by_pair:
        hardest_region = min(
            summary_by_pair,
            key=lambda row: (
                float(row["mean_satisfaction_rate"]),
                float(row["full_satisfaction_success_rate"]),
                -float(row["mean_runtime_seconds"]),
            ),
        )
    return {
        "first_problematic_n": problematic_n[0] if problematic_n else None,
        "first_problematic_r": problematic_r[0] if problematic_r else None,
        "hardest_region": hardest_region,
        "problematic_pairs": problematic_pairs,
    }


def hardest_instances(rows: Sequence[Mapping[str, Any]], *, top_k: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    rows_list = [dict(row) for row in rows]
    hardest = sorted(
        rows_list,
        key=lambda row: (
            float(row["satisfaction_rate"]),
            -float(row["unsatisfied_clauses"]),
            -float(row["runtime_seconds"]),
        ),
    )[:top_k]
    slowest = sorted(rows_list, key=lambda row: float(row["runtime_seconds"]), reverse=True)[:top_k]
    near_miss = sorted(
        [row for row in rows_list if not bool(row["fully_satisfied"])],
        key=lambda row: (
            float(row["unsatisfied_clauses"]),
            -float(row["satisfaction_rate"]),
            float(row["runtime_seconds"]),
        ),
    )[:top_k]
    return {
        "hardest_instances": hardest,
        "slowest_instances": slowest,
        "near_miss_instances": near_miss,
    }


def easiest_and_hardest_regions(summary_by_pair: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not summary_by_pair:
        return {"easiest_region": None, "hardest_region": None}
    easiest = max(
        summary_by_pair,
        key=lambda row: (
            float(row["full_satisfaction_success_rate"]),
            float(row["mean_satisfaction_rate"]),
            -float(row["mean_runtime_seconds"]),
        ),
    )
    hardest = min(
        summary_by_pair,
        key=lambda row: (
            float(row["full_satisfaction_success_rate"]),
            float(row["mean_satisfaction_rate"]),
            -float(row["mean_runtime_seconds"]),
        ),
    )
    return {"easiest_region": easiest, "hardest_region": hardest}


def pair_matrix_rows(
    summary_by_pair: Sequence[Mapping[str, Any]],
    *,
    algorithm_name: str,
) -> List[Dict[str, Any]]:
    return [
        dict(row)
        for row in summary_by_pair
        if str(row["algorithm_name"]) == algorithm_name
    ]
