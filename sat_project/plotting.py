"""
Matplotlib helpers for convergence curves and scaling (complexity) plots.

Figures are saved under ``results/plots/`` as high-resolution PNG files.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

# Use a non-interactive backend so plotting from worker threads does not try to open GUI windows.
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np

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


def plot_runtime_over_steps(
    runtime_history: Sequence[float],
    *,
    output_path: Path,
    title: str = "Runtime over search steps",
) -> None:
    """
    Plot cumulative elapsed runtime (seconds) versus recorded search steps.

    Args:
        runtime_history: Cumulative elapsed seconds at each recorded step.
        output_path: Where to save the PNG (parent folders created if needed).
        title: Figure title.
    """
    if not runtime_history:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    steps = list(range(len(runtime_history)))
    plt.figure(figsize=(9, 5))
    plt.plot(
        steps,
        list(runtime_history),
        marker="o",
        markersize=3,
        linewidth=1.5,
        label="Cumulative runtime",
    )
    plt.xlabel("Step index")
    plt.ylabel("Elapsed runtime (seconds)")
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_satisfaction_rate_over_runtime(
    runtime_history: Sequence[float],
    merit_history: Sequence[int],
    total_clauses: int,
    *,
    output_path: Path,
    title: str = "Satisfaction rate over runtime",
) -> None:
    """
    Plot satisfaction rate (%) versus cumulative elapsed runtime.

    Args:
        runtime_history: Cumulative elapsed seconds at each recorded step.
        merit_history: Best merit values aligned with ``runtime_history``.
        total_clauses: Total number of clauses (m) used to compute percent.
        output_path: Where to save the PNG (parent folders created if needed).
        title: Figure title.
    """
    if not runtime_history or not merit_history or total_clauses <= 0:
        return

    length = min(len(runtime_history), len(merit_history))
    if length == 0:
        return

    x_values = list(runtime_history[:length])
    y_values = [(100.0 * merit) / total_clauses for merit in merit_history[:length]]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, 5))
    plt.plot(
        x_values,
        y_values,
        marker="o",
        markersize=3,
        linewidth=1.5,
        label="Satisfaction rate",
    )
    plt.xlabel("Elapsed runtime (seconds)")
    plt.ylabel("Satisfaction rate (%)")
    plt.ylim(0.0, 100.0)
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_multi_satisfaction_rate_over_runtime(
    curves: Sequence[Tuple[str, Sequence[float], Sequence[int], int]],
    *,
    output_path: Path,
    title: str,
) -> None:
    """
    Overlay multiple algorithms on one chart: satisfaction rate (%) vs elapsed seconds.

    Each tuple is ``(label, runtime_history, merit_history, total_clauses)``.
    Histories should be time-aligned like the single-algorithm plots from the GUI.
    """
    if not curves:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 5.5))
    distinct_colors = ("#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b")

    plotted = 0
    for index, (label, runtime_history, merit_history, total_clauses) in enumerate(curves):
        if total_clauses <= 0 or not runtime_history or not merit_history:
            continue
        length = min(len(runtime_history), len(merit_history))
        if length == 0:
            continue
        x_values = list(runtime_history[:length])
        y_values = [(100.0 * merit) / total_clauses for merit in merit_history[:length]]
        color = distinct_colors[index % len(distinct_colors)]
        mark_stride = max(1, length // 60)
        plt.plot(
            x_values,
            y_values,
            linewidth=1.8,
            markersize=3,
            marker="o",
            markevery=mark_stride,
            label=label,
            color=color,
        )
        plotted += 1

    if plotted == 0:
        plt.close()
        return

    plt.xlabel("Elapsed runtime (seconds)")
    plt.ylabel("Satisfaction rate (%)")
    plt.ylim(0.0, 100.0)
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend(loc="best")
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


def plot_temperature_history(
    temperature_history: Sequence[float],
    *,
    output_path: Path,
    title: str = "SA temperature over iterations",
) -> None:
    if not temperature_history:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, 5))
    plt.plot(range(len(temperature_history)), list(temperature_history), linewidth=1.5)
    plt.xlabel("Iteration")
    plt.ylabel("Temperature")
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_move_acceptance_categories(
    accepted_move_history: Sequence[str],
    *,
    output_path: Path,
    title: str = "Accepted move categories over time",
) -> None:
    if not accepted_move_history:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    better_counts: List[int] = []
    equal_counts: List[int] = []
    worse_counts: List[int] = []
    better = 0
    equal = 0
    worse = 0
    for category in accepted_move_history:
        if category == "better":
            better += 1
        elif category == "equal":
            equal += 1
        elif category == "worse":
            worse += 1
        better_counts.append(better)
        equal_counts.append(equal)
        worse_counts.append(worse)

    steps = list(range(len(accepted_move_history)))
    plt.figure(figsize=(9, 5))
    plt.plot(steps, better_counts, label="Accepted better", linewidth=1.5)
    plt.plot(steps, equal_counts, label="Accepted equal", linewidth=1.5)
    plt.plot(steps, worse_counts, label="Accepted worse", linewidth=1.5)
    plt.xlabel("Iteration")
    plt.ylabel("Cumulative accepted moves")
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_restart_satisfaction_histogram(
    satisfaction_rates: Sequence[float],
    *,
    output_path: Path,
    title: str = "Final satisfaction across restarts",
) -> None:
    if not satisfaction_rates:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    percentages = [100.0 * rate for rate in satisfaction_rates]
    bins = min(10, max(4, len(percentages)))
    plt.hist(percentages, bins=bins, color="#4c72b0", edgecolor="black", alpha=0.8)
    plt.xlabel("Final satisfaction rate (%)")
    plt.ylabel("Restart count")
    plt.title(title)
    plt.grid(True, linestyle=":", alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_success_rate_by_setting(
    setting_labels: Sequence[str],
    success_rates: Sequence[float],
    *,
    output_path: Path,
    title: str = "Full satisfaction success rate by setting",
) -> None:
    if not setting_labels or not success_rates:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(max(9, len(setting_labels) * 0.8), 5))
    percentages = [100.0 * rate for rate in success_rates]
    positions = list(range(len(setting_labels)))
    plt.bar(positions, percentages, color="#55a868")
    plt.xticks(positions, setting_labels, rotation=35, ha="right")
    plt.ylabel("Success rate (%)")
    plt.title(title)
    plt.ylim(0.0, max(100.0, max(percentages, default=0.0) * 1.1))
    plt.grid(True, axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _save_png_svg(fig: plt.Figure, base_path: Path) -> List[Path]:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    outputs = []
    for ext in ("png", "svg"):
        file_path = base_path.with_suffix(f".{ext}")
        fig.savefig(file_path, dpi=180, bbox_inches="tight")
        outputs.append(file_path)
    return outputs


def _group_by_algorithm(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["algorithm_name"])].append(row)
    return grouped


def plot_metric_vs_group(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_key: str,
    metric_key: str,
    y_label: str,
    title: str,
    output_base_path: Path,
) -> List[Path]:
    grouped = _group_by_algorithm(rows)
    fig, ax = plt.subplots(figsize=(10, 5.6))
    for algorithm_name, algorithm_rows in grouped.items():
        sorted_rows = sorted(algorithm_rows, key=lambda row: float(row[group_key]))
        x_values = [float(row[group_key]) for row in sorted_rows]
        y_values = [float(row[metric_key]) for row in sorted_rows]
        ax.plot(x_values, y_values, marker="o", linewidth=1.8, label=algorithm_name)
    ax.set_xlabel(group_key)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, linestyle=":", alpha=0.55)
    ax.legend()
    fig.tight_layout()
    outputs = _save_png_svg(fig, output_base_path)
    plt.close(fig)
    return outputs


def plot_runtime_vs_satisfaction_scatter(
    rows: Sequence[Mapping[str, Any]],
    *,
    output_base_path: Path,
    title: str,
) -> List[Path]:
    grouped = _group_by_algorithm(rows)
    fig, ax = plt.subplots(figsize=(10, 5.8))
    markers = ("o", "s", "^", "D", "v")
    for idx, (algorithm_name, algorithm_rows) in enumerate(grouped.items()):
        ax.scatter(
            [float(row["runtime_seconds"]) for row in algorithm_rows],
            [100.0 * float(row["satisfaction_rate"]) for row in algorithm_rows],
            alpha=0.75,
            marker=markers[idx % len(markers)],
            label=algorithm_name,
        )
    ax.set_xlabel("Runtime (seconds)")
    ax.set_ylabel("Satisfaction rate (%)")
    ax.set_title(title)
    ax.grid(True, linestyle=":", alpha=0.55)
    ax.legend()
    fig.tight_layout()
    outputs = _save_png_svg(fig, output_base_path)
    plt.close(fig)
    return outputs


def plot_boxplots_by_group(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_key: str,
    metric_key: str,
    title: str,
    y_label: str,
    output_base_path: Path,
) -> List[Path]:
    grouped_values: Dict[float, List[float]] = defaultdict(list)
    for row in rows:
        grouped_values[float(row[group_key])].append(float(row[metric_key]))
    ordered_keys = sorted(grouped_values.keys())
    fig, ax = plt.subplots(figsize=(max(9, len(ordered_keys) * 0.9), 5.8))
    ax.boxplot([grouped_values[key] for key in ordered_keys], labels=[str(key) for key in ordered_keys], showmeans=True)
    ax.set_xlabel(group_key)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    outputs = _save_png_svg(fig, output_base_path)
    plt.close(fig)
    return outputs


def plot_heatmap(
    rows: Sequence[Mapping[str, Any]],
    *,
    value_key: str,
    title: str,
    output_base_path: Path,
    value_label: str,
) -> List[Path]:
    ratios = sorted({float(row["ratio"]) for row in rows})
    sizes = sorted({int(row["n"]) for row in rows})
    grid = np.full((len(sizes), len(ratios)), np.nan)
    for row in rows:
        size_index = sizes.index(int(row["n"]))
        ratio_index = ratios.index(float(row["ratio"]))
        grid[size_index, ratio_index] = float(row[value_key])
    fig, ax = plt.subplots(figsize=(10, 6.2))
    image = ax.imshow(grid, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(ratios)))
    ax.set_xticklabels([str(r) for r in ratios])
    ax.set_yticks(range(len(sizes)))
    ax.set_yticklabels([str(n) for n in sizes])
    ax.set_xlabel("Clause density ratio r")
    ax.set_ylabel("Variables n")
    ax.set_title(title)
    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label(value_label)
    fig.tight_layout()
    outputs = _save_png_svg(fig, output_base_path)
    plt.close(fig)
    return outputs
