from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt


def _style_for_paper() -> None:
    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.labelsize": 13,
            "axes.titlesize": 14,
            "legend.fontsize": 11,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "figure.dpi": 180,
            "savefig.dpi": 220,
        }
    )


def _save_all_formats(fig: plt.Figure, base_path: Path, *, with_title: bool = True) -> List[str]:
    stem = base_path.stem if with_title else f"{base_path.stem}_notitle"
    outputs: List[str] = []
    for ext in ("png", "svg", "pdf"):
        file_path = base_path.with_name(f"{stem}.{ext}")
        fig.savefig(file_path, bbox_inches="tight")
        outputs.append(str(file_path))
    return outputs


def _group_by_solver(per_run_rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in per_run_rows:
        grouped[str(row["algorithm_name"])].append(row)
    return grouped


def _mean_history(histories: Sequence[Tuple[Tuple[int, ...], Tuple[float, ...]]]) -> Tuple[List[int], List[float]]:
    if not histories:
        return [], []
    max_len = max(len(h[0]) for h in histories)
    mean_best: List[float] = [0.0] * max_len
    mean_runtime: List[float] = [0.0] * max_len
    for best_hist, runtime_hist in histories:
        last_best = best_hist[-1] if best_hist else 0
        last_time = runtime_hist[-1] if runtime_hist else 0.0
        for idx in range(max_len):
            value_best = best_hist[idx] if idx < len(best_hist) else last_best
            value_time = runtime_hist[idx] if idx < len(runtime_hist) else last_time
            mean_best[idx] += value_best
            mean_runtime[idx] += value_time
    count = float(len(histories))
    return [int(round(v / count)) for v in mean_best], [v / count for v in mean_runtime]


def create_publication_plots(
    *,
    per_run_rows: Sequence[Mapping[str, Any]],
    summary_rows: Sequence[Mapping[str, Any]],
    solver_histories: Mapping[str, List[Tuple[Tuple[int, ...], Tuple[float, ...]]]],
    scaling_rows: Sequence[Mapping[str, Any]],
    output_dir: Path,
    save_title_variants: bool = True,
) -> List[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    _style_for_paper()
    written: List[str] = []
    grouped = _group_by_solver(per_run_rows)
    solver_names = [str(row["algorithm_name"]) for row in summary_rows]

    # 1) Runtime comparison with error bars.
    fig1, ax1 = plt.subplots(figsize=(10.5, 6.2))
    runtime_means = [float(row["mean_runtime"]) for row in summary_rows]
    runtime_err = [float(row["std_runtime"]) for row in summary_rows]
    ax1.bar(solver_names, runtime_means, yerr=runtime_err, capsize=5, color="#4C78A8")
    ax1.set_xlabel("Solver")
    ax1.set_ylabel("Mean runtime (seconds)")
    ax1.set_title("Runtime Comparison Across Solvers")
    ax1.grid(axis="y", linestyle=":", alpha=0.5)
    ax1.tick_params(axis="x", rotation=24)
    fig1.tight_layout()
    written.extend(_save_all_formats(fig1, output_dir / "runtime_comparison", with_title=True))
    if save_title_variants:
        ax1.set_title("")
        written.extend(_save_all_formats(fig1, output_dir / "runtime_comparison", with_title=False))
    plt.close(fig1)

    # 2) Satisfaction-rate bar.
    fig2, ax2 = plt.subplots(figsize=(10.5, 6.2))
    sat_means = [100.0 * float(row["mean_satisfaction_rate"]) for row in summary_rows]
    ax2.bar(solver_names, sat_means, color="#59A14F")
    ax2.set_xlabel("Solver")
    ax2.set_ylabel("Mean satisfaction rate (%)")
    ax2.set_ylim(0.0, 100.0)
    ax2.set_title("Satisfaction Rate Comparison")
    ax2.grid(axis="y", linestyle=":", alpha=0.5)
    ax2.tick_params(axis="x", rotation=24)
    fig2.tight_layout()
    written.extend(_save_all_formats(fig2, output_dir / "satisfaction_rate_comparison", with_title=True))
    if save_title_variants:
        ax2.set_title("")
        written.extend(_save_all_formats(fig2, output_dir / "satisfaction_rate_comparison", with_title=False))
    plt.close(fig2)

    # 3) Best satisfied clauses boxplot.
    fig3, ax3 = plt.subplots(figsize=(10.5, 6.2))
    data = [[float(r["best_satisfied_clauses"]) for r in grouped[name]] for name in solver_names]
    ax3.boxplot(data, labels=solver_names, showmeans=True)
    ax3.set_xlabel("Solver")
    ax3.set_ylabel("Best satisfied clauses")
    ax3.set_title("Best Satisfied Clauses Distribution")
    ax3.grid(axis="y", linestyle=":", alpha=0.4)
    ax3.tick_params(axis="x", rotation=24)
    fig3.tight_layout()
    written.extend(_save_all_formats(fig3, output_dir / "best_satisfied_clauses_boxplot", with_title=True))
    if save_title_variants:
        ax3.set_title("")
        written.extend(_save_all_formats(fig3, output_dir / "best_satisfied_clauses_boxplot", with_title=False))
    plt.close(fig3)

    # 4) Runtime vs satisfaction scatter.
    fig4, ax4 = plt.subplots(figsize=(10.5, 6.2))
    markers = ["o", "s", "^", "D", "v", "P", "X"]
    for idx, solver_name in enumerate(solver_names):
        rows = grouped.get(solver_name, [])
        x = [float(r["runtime_seconds"]) for r in rows]
        y = [100.0 * float(r["satisfaction_rate"]) for r in rows]
        ax4.scatter(x, y, alpha=0.8, marker=markers[idx % len(markers)], label=solver_name)
    ax4.set_xlabel("Runtime (seconds)")
    ax4.set_ylabel("Satisfaction rate (%)")
    ax4.set_title("Runtime vs Satisfaction")
    ax4.grid(True, linestyle=":", alpha=0.45)
    ax4.legend()
    fig4.tight_layout()
    written.extend(_save_all_formats(fig4, output_dir / "runtime_vs_satisfaction_scatter", with_title=True))
    if save_title_variants:
        ax4.set_title("")
        written.extend(_save_all_formats(fig4, output_dir / "runtime_vs_satisfaction_scatter", with_title=False))
    plt.close(fig4)

    # 5) Convergence plot (mean history).
    fig5, ax5 = plt.subplots(figsize=(10.8, 6.2))
    for solver_name in solver_names:
        mean_best, _mean_runtime = _mean_history(solver_histories.get(solver_name, []))
        if not mean_best:
            continue
        ax5.plot(range(len(mean_best)), mean_best, linewidth=2.0, label=solver_name)
    ax5.set_xlabel("Iteration / generation")
    ax5.set_ylabel("Best satisfied clauses")
    ax5.set_title("Convergence Curves (Averaged)")
    ax5.grid(True, linestyle=":", alpha=0.45)
    ax5.legend()
    fig5.tight_layout()
    written.extend(_save_all_formats(fig5, output_dir / "convergence_plot", with_title=True))
    if save_title_variants:
        ax5.set_title("")
        written.extend(_save_all_formats(fig5, output_dir / "convergence_plot", with_title=False))
    plt.close(fig5)

    # 6) Empirical scaling plot.
    if scaling_rows:
        by_solver_size: Dict[str, Dict[float, List[float]]] = defaultdict(lambda: defaultdict(list))
        for row in scaling_rows:
            name = str(row["algorithm_name"])
            size = float(row["size_n_plus_m"])
            by_solver_size[name][size].append(float(row["runtime_seconds"]))
        fig6, ax6 = plt.subplots(figsize=(10.8, 6.2))
        for solver_name in solver_names:
            solver_map = by_solver_size.get(solver_name, {})
            if not solver_map:
                continue
            sizes = sorted(solver_map.keys())
            runtimes = [mean(solver_map[s]) for s in sizes]
            ax6.plot(sizes, runtimes, marker="o", linewidth=2.0, label=solver_name)
        ax6.set_xlabel("Instance size (n + m)")
        ax6.set_ylabel("Runtime (seconds)")
        ax6.set_title("Empirical Runtime Scaling")
        ax6.grid(True, linestyle=":", alpha=0.45)
        ax6.legend()
        fig6.tight_layout()
        written.extend(_save_all_formats(fig6, output_dir / "empirical_scaling_plot", with_title=True))
        if save_title_variants:
            ax6.set_title("")
            written.extend(_save_all_formats(fig6, output_dir / "empirical_scaling_plot", with_title=False))
        plt.close(fig6)

    # 7) Efficiency plot (quality-speed tradeoff).
    fig7, ax7 = plt.subplots(figsize=(10.5, 6.2))
    for idx, solver_name in enumerate(solver_names):
        rows = grouped.get(solver_name, [])
        x = [float(r["runtime_seconds"]) for r in rows]
        y = [float(r["best_satisfied_clauses"]) for r in rows]
        ax7.scatter(x, y, alpha=0.75, marker=markers[idx % len(markers)], label=solver_name)
    ax7.set_xlabel("Runtime (seconds)")
    ax7.set_ylabel("Satisfied clauses")
    ax7.set_title("Efficiency Plot: Quality vs Runtime")
    ax7.grid(True, linestyle=":", alpha=0.45)
    ax7.legend()
    fig7.tight_layout()
    written.extend(_save_all_formats(fig7, output_dir / "efficiency_plot", with_title=True))
    if save_title_variants:
        ax7.set_title("")
        written.extend(_save_all_formats(fig7, output_dir / "efficiency_plot", with_title=False))
    plt.close(fig7)

    # 8) Normalized runtime and quality.
    fig8, ax8 = plt.subplots(figsize=(10.5, 6.2))
    runtime_values = [float(row["mean_runtime"]) for row in summary_rows]
    quality_values = [float(row["mean_satisfaction_rate"]) for row in summary_rows]
    min_rt, max_rt = min(runtime_values), max(runtime_values)
    min_q, max_q = min(quality_values), max(quality_values)
    normalized_runtime = [
        0.0 if max_rt == min_rt else (value - min_rt) / (max_rt - min_rt) for value in runtime_values
    ]
    normalized_quality = [
        0.0 if max_q == min_q else (value - min_q) / (max_q - min_q) for value in quality_values
    ]
    x_positions = range(len(solver_names))
    width = 0.38
    ax8.bar([x - width / 2 for x in x_positions], normalized_runtime, width=width, label="Normalized runtime")
    ax8.bar([x + width / 2 for x in x_positions], normalized_quality, width=width, label="Normalized satisfaction")
    ax8.set_xticks(list(x_positions))
    ax8.set_xticklabels(solver_names, rotation=24)
    ax8.set_ylabel("Normalized score [0, 1]")
    ax8.set_title("Normalized Runtime and Satisfaction Comparison")
    ax8.grid(axis="y", linestyle=":", alpha=0.45)
    ax8.legend()
    fig8.tight_layout()
    written.extend(_save_all_formats(fig8, output_dir / "normalized_comparison_plot", with_title=True))
    if save_title_variants:
        ax8.set_title("")
        written.extend(_save_all_formats(fig8, output_dir / "normalized_comparison_plot", with_title=False))
    plt.close(fig8)

    # 9) Mean iteration count.
    fig9, ax9 = plt.subplots(figsize=(10.5, 6.2))
    iteration_means = [
        mean(float(r["iterations_used"]) for r in grouped.get(name, [])) if grouped.get(name) else 0.0
        for name in solver_names
    ]
    ax9.bar(solver_names, iteration_means, color="#F28E2B")
    ax9.set_xlabel("Solver")
    ax9.set_ylabel("Mean iterations / generations")
    ax9.set_title("Iteration Count Comparison")
    ax9.grid(axis="y", linestyle=":", alpha=0.45)
    ax9.tick_params(axis="x", rotation=24)
    fig9.tight_layout()
    written.extend(_save_all_formats(fig9, output_dir / "iteration_count_comparison", with_title=True))
    if save_title_variants:
        ax9.set_title("")
        written.extend(_save_all_formats(fig9, output_dir / "iteration_count_comparison", with_title=False))
    plt.close(fig9)

    return written
