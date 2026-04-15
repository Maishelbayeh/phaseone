"""
Matplotlib helpers for convergence curves and scaling (complexity) plots.

Figures are saved under ``results/plots/`` as high-resolution PNG files.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

# Use a non-interactive backend so plotting from worker threads does not try to open GUI windows.
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

from experiments import SingleRunRecord


def plot_convergence_history(
    merit_history: Sequence[int],
    total_clauses: int,
    *,
    output_path: Path,
    title: str = "Hill climbing: best merit vs. step",
) -> None:
    """
    Line plot of global-best satisfied clause count over search steps.

    Args:
        merit_history: Values recorded after initial assignment and each update.
        total_clauses: m (shown as a horizontal reference when < max merit).
        output_path: Where to save the PNG (parent folders created if needed).
        title: Figure title
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    steps = list(range(len(merit_history)))
    plt.figure(figsize=(9, 5))
    plt.plot(steps, list(merit_history), marker="o", markersize=3, linewidth=1.5, label="Best merit (satisfied clauses)")

    if total_clauses > 0:
        plt.axhline(
            y=total_clauses,
            color="green",
            linestyle="--",
            linewidth=1,
            label=f"Full satisfaction (m={total_clauses})",
        )

    plt.xlabel("Step index (initial + after each improving move / restart snapshot)")
    plt.ylabel("Merit: satisfied clauses")
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _average_runtime_by_n_and_ratio(
    records: Iterable[SingleRunRecord],
) -> Dict[Tuple[float, int], float]:
    """
    Average ``runtime_seconds`` when multiple rows exist per (ratio, n).
    """
    sums: Dict[Tuple[float, int], float] = defaultdict(float)
    counts: Dict[Tuple[float, int], int] = defaultdict(int)

    for record in records:
        key = (record.clause_density_ratio, record.num_variables)
        sums[key] += record.runtime_seconds
        counts[key] += 1

    averages: Dict[Tuple[float, int], float] = {}
    for key, total_time in sums.items():
        averages[key] = total_time / counts[key]
    return averages


def _group_records_by_ratio_and_n(
    records: Iterable[SingleRunRecord],
) -> Dict[Tuple[float, int], List[SingleRunRecord]]:
    grouped: Dict[Tuple[float, int], List[SingleRunRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.clause_density_ratio, record.num_variables)].append(record)
    return grouped


def plot_runtime_vs_num_variables(
    records: Sequence[SingleRunRecord],
    *,
    output_path: Path,
    title: str = "Empirical runtime vs. number of variables",
) -> None:
    """
    One curve per clause-density ratio: n on x-axis, mean runtime on y-axis.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    averages = _average_runtime_by_n_and_ratio(records)
    ratios = sorted({record.clause_density_ratio for record in records})

    plt.figure(figsize=(9, 5))
    for ratio in ratios:
        points = [
            (num_variables, averages[(ratio, num_variables)])
            for num_variables in sorted(
                {record.num_variables for record in records if record.clause_density_ratio == ratio}
            )
        ]
        if not points:
            continue
        x_values = [value[0] for value in points]
        y_values = [value[1] for value in points]
        plt.plot(
            x_values,
            y_values,
            marker="s",
            linewidth=1.8,
            label=f"m/n = {ratio}",
        )

    plt.xlabel("Number of variables (n)")
    plt.ylabel("Mean runtime (seconds)")
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend(title="Clause density")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_satisfied_clauses_vs_num_variables(
    records: Sequence[SingleRunRecord],
    *,
    output_path: Path,
    title: str = "Satisfied clauses vs. number of variables",
) -> None:
    """
    One curve per clause-density ratio: n on x-axis, mean satisfied clauses on y-axis.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grouped = _group_records_by_ratio_and_n(records)
    ratios = sorted({record.clause_density_ratio for record in records})

    plt.figure(figsize=(9, 5))
    for ratio in ratios:
        candidate_ns = sorted(
            {record.num_variables for record in records if record.clause_density_ratio == ratio}
        )
        points = []
        for num_variables in candidate_ns:
            group_key = (ratio, num_variables)
            group_records = grouped.get(group_key, [])
            if group_records:
                points.append((num_variables, mean(r.satisfied_clauses for r in group_records)))
        if not points:
            continue
        x_values = [value[0] for value in points]
        y_values = [value[1] for value in points]
        plt.plot(
            x_values,
            y_values,
            marker="o",
            linewidth=1.8,
            label=f"m/n = {ratio}",
        )

    plt.xlabel("Number of variables (n)")
    plt.ylabel("Mean satisfied clauses")
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend(title="Clause density")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_satisfaction_rate_vs_num_variables(
    records: Sequence[SingleRunRecord],
    *,
    output_path: Path,
    title: str = "Satisfaction rate vs. number of variables",
) -> None:
    """
    One curve per clause-density ratio: n on x-axis, mean satisfaction rate (%) on y-axis.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grouped = _group_records_by_ratio_and_n(records)
    ratios = sorted({record.clause_density_ratio for record in records})

    plt.figure(figsize=(9, 5))
    for ratio in ratios:
        candidate_ns = sorted(
            {record.num_variables for record in records if record.clause_density_ratio == ratio}
        )
        points = []
        for num_variables in candidate_ns:
            group_key = (ratio, num_variables)
            group_records = grouped.get(group_key, [])
            if group_records:
                mean_rate_percent = 100.0 * mean(r.satisfaction_rate for r in group_records)
                points.append((num_variables, mean_rate_percent))
        if not points:
            continue
        x_values = [value[0] for value in points]
        y_values = [value[1] for value in points]
        plt.plot(
            x_values,
            y_values,
            marker="D",
            linewidth=1.8,
            label=f"m/n = {ratio}",
        )

    plt.xlabel("Number of variables (n)")
    plt.ylabel("Mean satisfaction rate (%)")
    plt.title(title)
    plt.ylim(0.0, 100.0)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend(title="Clause density")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()
