from __future__ import annotations

import csv
import math
import shutil
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
COMPARISON_DIR = ROOT / "results" / "comparison"
FINAL_DIR = ROOT / "results" / "final_results"
PLOTS_DIR = FINAL_DIR / "plots"

SNAPSHOT_ROWS = [
    {"instance": "3sat_n100_r3.json", "n": 100, "ratio": 3.0, "algorithm": "Hill Climbing", "best": 296, "total": 300, "runtime": 3.206},
    {"instance": "3sat_n100_r3.json", "n": 100, "ratio": 3.0, "algorithm": "Simulated Annealing", "best": 300, "total": 300, "runtime": 0.524},
    {"instance": "3sat_n100_r3.json", "n": 100, "ratio": 3.0, "algorithm": "Genetic Algorithm", "best": 297, "total": 300, "runtime": 2.947},
    {"instance": "3sat_n100_r3.json", "n": 100, "ratio": 3.0, "algorithm": "Binary Swarm (BSGO)", "best": 297, "total": 300, "runtime": 9.212},
    {"instance": "3sat_n100_r3.json", "n": 100, "ratio": 3.0, "algorithm": "Hybrid BSGO-GA", "best": 298, "total": 300, "runtime": 19.562},
    {"instance": "3sat_n100_r4.3.json", "n": 100, "ratio": 4.3, "algorithm": "Hill Climbing", "best": 425, "total": 430, "runtime": 8.118},
    {"instance": "3sat_n100_r4.3.json", "n": 100, "ratio": 4.3, "algorithm": "Simulated Annealing", "best": 425, "total": 430, "runtime": 2.074},
    {"instance": "3sat_n100_r4.3.json", "n": 100, "ratio": 4.3, "algorithm": "Genetic Algorithm", "best": 427, "total": 430, "runtime": 5.443},
    {"instance": "3sat_n100_r4.3.json", "n": 100, "ratio": 4.3, "algorithm": "Binary Swarm (BSGO)", "best": 422, "total": 430, "runtime": 9.084},
    {"instance": "3sat_n100_r4.3.json", "n": 100, "ratio": 4.3, "algorithm": "Hybrid BSGO-GA", "best": 424, "total": 430, "runtime": 18.442},
    {"instance": "3sat_n100_r6.json", "n": 100, "ratio": 6.0, "algorithm": "Hill Climbing", "best": 582, "total": 600, "runtime": 7.080},
    {"instance": "3sat_n100_r6.json", "n": 100, "ratio": 6.0, "algorithm": "Simulated Annealing", "best": 589, "total": 600, "runtime": 1.455},
    {"instance": "3sat_n100_r6.json", "n": 100, "ratio": 6.0, "algorithm": "Genetic Algorithm", "best": 586, "total": 600, "runtime": 5.005},
    {"instance": "3sat_n100_r6.json", "n": 100, "ratio": 6.0, "algorithm": "Binary Swarm (BSGO)", "best": 584, "total": 600, "runtime": 10.645},
    {"instance": "3sat_n100_r6.json", "n": 100, "ratio": 6.0, "algorithm": "Hybrid BSGO-GA", "best": 579, "total": 600, "runtime": 20.013},
    {"instance": "3sat_n150_r3.json", "n": 150, "ratio": 3.0, "algorithm": "Hill Climbing", "best": 445, "total": 450, "runtime": 7.678},
    {"instance": "3sat_n150_r3.json", "n": 150, "ratio": 3.0, "algorithm": "Simulated Annealing", "best": 449, "total": 450, "runtime": 1.457},
    {"instance": "3sat_n150_r3.json", "n": 150, "ratio": 3.0, "algorithm": "Genetic Algorithm", "best": 449, "total": 450, "runtime": 5.801},
    {"instance": "3sat_n150_r3.json", "n": 150, "ratio": 3.0, "algorithm": "Binary Swarm (BSGO)", "best": 447, "total": 450, "runtime": 12.247},
    {"instance": "3sat_n150_r3.json", "n": 150, "ratio": 3.0, "algorithm": "Hybrid BSGO-GA", "best": 447, "total": 450, "runtime": 25.256},
    {"instance": "3sat_n150_r4.3.json", "n": 150, "ratio": 4.3, "algorithm": "Hill Climbing", "best": 632, "total": 645, "runtime": 16.720},
    {"instance": "3sat_n150_r4.3.json", "n": 150, "ratio": 4.3, "algorithm": "Simulated Annealing", "best": 638, "total": 645, "runtime": 2.191},
    {"instance": "3sat_n150_r4.3.json", "n": 150, "ratio": 4.3, "algorithm": "Genetic Algorithm", "best": 637, "total": 645, "runtime": 15.118},
    {"instance": "3sat_n150_r4.3.json", "n": 150, "ratio": 4.3, "algorithm": "Binary Swarm (BSGO)", "best": 636, "total": 645, "runtime": 24.229},
    {"instance": "3sat_n150_r4.3.json", "n": 150, "ratio": 4.3, "algorithm": "Hybrid BSGO-GA", "best": 635, "total": 645, "runtime": 50.912},
    {"instance": "3sat_n150_r6.json", "n": 150, "ratio": 6.0, "algorithm": "Hill Climbing", "best": 875, "total": 900, "runtime": 24.322},
    {"instance": "3sat_n150_r6.json", "n": 150, "ratio": 6.0, "algorithm": "Simulated Annealing", "best": 886, "total": 900, "runtime": 2.860},
    {"instance": "3sat_n150_r6.json", "n": 150, "ratio": 6.0, "algorithm": "Genetic Algorithm", "best": 877, "total": 900, "runtime": 10.900},
    {"instance": "3sat_n150_r6.json", "n": 150, "ratio": 6.0, "algorithm": "Binary Swarm (BSGO)", "best": 879, "total": 900, "runtime": 24.606},
    {"instance": "3sat_n150_r6.json", "n": 150, "ratio": 6.0, "algorithm": "Hybrid BSGO-GA", "best": 874, "total": 900, "runtime": 44.434},
    {"instance": "3sat_n200_r3.json", "n": 200, "ratio": 3.0, "algorithm": "Hill Climbing", "best": 594, "total": 600, "runtime": 20.458},
    {"instance": "3sat_n200_r3.json", "n": 200, "ratio": 3.0, "algorithm": "Simulated Annealing", "best": 599, "total": 600, "runtime": 2.039},
    {"instance": "3sat_n200_r3.json", "n": 200, "ratio": 3.0, "algorithm": "Genetic Algorithm", "best": 596, "total": 600, "runtime": 7.742},
    {"instance": "3sat_n200_r3.json", "n": 200, "ratio": 3.0, "algorithm": "Binary Swarm (BSGO)", "best": 593, "total": 600, "runtime": 22.702},
    {"instance": "3sat_n200_r3.json", "n": 200, "ratio": 3.0, "algorithm": "Hybrid BSGO-GA", "best": 598, "total": 600, "runtime": 36.704},
    {"instance": "3sat_n200_r4.3.json", "n": 200, "ratio": 4.3, "algorithm": "Hill Climbing", "best": 845, "total": 860, "runtime": 31.007},
    {"instance": "3sat_n200_r4.3.json", "n": 200, "ratio": 4.3, "algorithm": "Simulated Annealing", "best": 853, "total": 860, "runtime": 2.873},
    {"instance": "3sat_n200_r4.3.json", "n": 200, "ratio": 4.3, "algorithm": "Genetic Algorithm", "best": 855, "total": 860, "runtime": 10.659},
    {"instance": "3sat_n200_r4.3.json", "n": 200, "ratio": 4.3, "algorithm": "Binary Swarm (BSGO)", "best": 849, "total": 860, "runtime": 30.456},
    {"instance": "3sat_n200_r4.3.json", "n": 200, "ratio": 4.3, "algorithm": "Hybrid BSGO-GA", "best": 847, "total": 860, "runtime": 52.316},
    {"instance": "3sat_n200_r6.json", "n": 200, "ratio": 6.0, "algorithm": "Hill Climbing", "best": 1165, "total": 1200, "runtime": 46.572},
    {"instance": "3sat_n200_r6.json", "n": 200, "ratio": 6.0, "algorithm": "Simulated Annealing", "best": 1174, "total": 1200, "runtime": 3.985},
    {"instance": "3sat_n200_r6.json", "n": 200, "ratio": 6.0, "algorithm": "Genetic Algorithm", "best": 1172, "total": 1200, "runtime": 15.982},
    {"instance": "3sat_n200_r6.json", "n": 200, "ratio": 6.0, "algorithm": "Binary Swarm (BSGO)", "best": 1161, "total": 1200, "runtime": 50.852},
    {"instance": "3sat_n200_r6.json", "n": 200, "ratio": 6.0, "algorithm": "Hybrid BSGO-GA", "best": 1169, "total": 1200, "runtime": 80.624},
    {"instance": "3sat_n500_r3.json", "n": 500, "ratio": 3.0, "algorithm": "Hill Climbing", "best": 1476, "total": 1500, "runtime": 133.299},
    {"instance": "3sat_n500_r3.json", "n": 500, "ratio": 3.0, "algorithm": "Simulated Annealing", "best": 1487, "total": 1500, "runtime": 4.356},
    {"instance": "3sat_n500_r3.json", "n": 500, "ratio": 3.0, "algorithm": "Genetic Algorithm", "best": 1486, "total": 1500, "runtime": 21.125},
    {"instance": "3sat_n500_r3.json", "n": 500, "ratio": 3.0, "algorithm": "Binary Swarm (BSGO)", "best": 1443, "total": 1500, "runtime": 86.707},
    {"instance": "3sat_n500_r3.json", "n": 500, "ratio": 3.0, "algorithm": "Hybrid BSGO-GA", "best": 1478, "total": 1500, "runtime": 293.246},
]

ALGORITHM_ORDER = [
    "Simulated Annealing",
    "Genetic Algorithm",
    "Hill Climbing",
    "Binary Swarm (BSGO)",
    "Hybrid BSGO-GA",
]
COLORS = {
    "Simulated Annealing": "#1f77b4",
    "Genetic Algorithm": "#2ca02c",
    "Hill Climbing": "#9467bd",
    "Binary Swarm (BSGO)": "#ff7f0e",
    "Hybrid BSGO-GA": "#d62728",
}


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def write_snapshot_csv() -> None:
    path = FINAL_DIR / "available_benchmark_snapshot.csv"
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=["instance", "n", "ratio", "algorithm", "best", "total", "satisfaction_rate", "runtime"],
        )
        writer.writeheader()
        for row in SNAPSHOT_ROWS:
            writer.writerow(
                {
                    **row,
                    "satisfaction_rate": row["best"] / row["total"],
                }
            )


def plot_ratio_lines(ratio: float, metric: str, ylabel: str, filename: str) -> None:
    plt.figure(figsize=(10, 6))
    rows = [row for row in SNAPSHOT_ROWS if math.isclose(row["ratio"], ratio)]
    xs = sorted({row["n"] for row in rows})
    for algorithm in ALGORITHM_ORDER:
        algo_rows = [row for row in rows if row["algorithm"] == algorithm]
        if not algo_rows:
            continue
        x_values = [row["n"] for row in sorted(algo_rows, key=lambda item: item["n"])]
        if metric == "satisfaction_rate":
            y_values = [100.0 * row["best"] / row["total"] for row in sorted(algo_rows, key=lambda item: item["n"])]
        else:
            y_values = [row["runtime"] for row in sorted(algo_rows, key=lambda item: item["n"])]
        plt.plot(x_values, y_values, marker="o", linewidth=2, label=algorithm, color=COLORS[algorithm])
    plt.xticks(xs)
    plt.xlabel("Number of variables (n)")
    plt.ylabel(ylabel)
    plt.title(f"Ratio r={ratio}: {ylabel} vs n")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=160)
    plt.close()


def plot_overall_snapshot_scatter() -> None:
    plt.figure(figsize=(10, 6))
    for algorithm in ALGORITHM_ORDER:
        algo_rows = [row for row in SNAPSHOT_ROWS if row["algorithm"] == algorithm]
        plt.scatter(
            [row["runtime"] for row in algo_rows],
            [100.0 * row["best"] / row["total"] for row in algo_rows],
            s=60,
            alpha=0.8,
            label=algorithm,
            color=COLORS[algorithm],
        )
    plt.xlabel("Runtime (seconds)")
    plt.ylabel("Satisfaction rate (%)")
    plt.title("Available Benchmark Snapshot: Runtime vs Satisfaction")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "snapshot_runtime_vs_satisfaction.png", dpi=160)
    plt.close()


def plot_gap_from_best() -> None:
    plt.figure(figsize=(11, 6))
    instance_order = sorted({row["instance"] for row in SNAPSHOT_ROWS}, key=lambda name: (float(name.split("_r")[1].replace(".json", "")), int(name.split("_n")[1].split("_")[0])))
    x_positions = range(len(instance_order))
    width = 0.16
    offsets = [-2, -1, 0, 1, 2]

    for offset, algorithm in zip(offsets, ALGORITHM_ORDER):
        values = []
        for instance in instance_order:
            instance_rows = [row for row in SNAPSHOT_ROWS if row["instance"] == instance]
            best_value = max(row["best"] / row["total"] for row in instance_rows)
            algo_row = next(row for row in instance_rows if row["algorithm"] == algorithm)
            gap = 100.0 * (best_value - algo_row["best"] / algo_row["total"])
            values.append(gap)
        shifted_x = [x + offset * width for x in x_positions]
        plt.bar(shifted_x, values, width=width, label=algorithm, color=COLORS[algorithm])

    plt.xticks(list(x_positions), instance_order, rotation=45, ha="right")
    plt.ylabel("Gap from instance best (%)")
    plt.title("How far each algorithm is from the best result on each available instance")
    plt.grid(True, axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "snapshot_gap_from_best.png", dpi=160)
    plt.close()


def copy_existing_artifacts() -> None:
    existing_files = [
        COMPARISON_DIR / "summary_results.csv",
        COMPARISON_DIR / "complexity_summary.csv",
        COMPARISON_DIR / "per_run_results.csv",
        COMPARISON_DIR / "focused_comparison_results.json",
        COMPARISON_DIR / "comparison_report.md",
        COMPARISON_DIR / "parameters_justification.md",
        COMPARISON_DIR / "plots" / "convergence_plot.png",
        COMPARISON_DIR / "plots" / "efficiency_plot.png",
        COMPARISON_DIR / "plots" / "empirical_scaling_plot.png",
        COMPARISON_DIR / "plots" / "runtime_comparison.png",
        COMPARISON_DIR / "plots" / "runtime_vs_satisfaction_scatter.png",
        COMPARISON_DIR / "plots" / "satisfaction_rate_comparison.png",
        ROOT / "results" / "plots" / "gui_hill_climbing_convergence.png",
        ROOT / "results" / "plots" / "gui_simulated_annealing_convergence.png",
        ROOT / "results" / "plots" / "gui_hybrid_bsgo_ga_convergence.png",
    ]
    for source in existing_files:
        if source.exists():
            target = FINAL_DIR / source.name
            shutil.copy2(source, target)


def write_analysis_report() -> None:
    report = FINAL_DIR / "analysis_report.md"
    report.write_text(
        """# Final Results Analysis

## What this folder contains

- `available_benchmark_snapshot.csv`: current no-rerun snapshot built from the latest completed benchmark outputs.
- Copied legacy comparison artifacts from `results/comparison/`.
- New plots in `plots/` that compare the five tuned algorithms across the available size and ratio points.

## Important scope note

- This package was built **without rerunning** the benchmark suite.
- The new size-by-ratio plots use the latest available snapshot points for:
  - `n = 100, 150, 200` at `r = 3, 4.3, 6`
  - `n = 500` at `r = 3`
- Existing legacy comparison files still provide multi-run data and extra plots, but they were produced from older saved runs.

## Main picture

- `Simulated Annealing` is the strongest overall solver in the available data.
- `Genetic Algorithm` is the best population-based standalone method.
- `Hill Climbing` is a solid baseline but scales badly as `n` grows because it evaluates many one-bit neighbors.
- `Binary Swarm (BSGO)` improved over older versions, but it is still usually behind SA and GA in the current project.
- `Hybrid BSGO-GA` is competitive in solution quality, but it is much more expensive in runtime and still does not clearly dominate GA.

## Why Hybrid is not yet combining the best of GA and BSGO

- Yes: the current evidence says the hybrid still needs improvement.
- The hybrid is **not** consistently stronger than both parents.
- In the available snapshot:
  - it is usually slower than GA by a large margin,
  - it often fails to beat SA on quality,
  - and it does not clearly inherit the strongest exploitation behavior from GA plus the strongest guided movement from the improved BSGO.

## Interpreting the plots

- `r3_satisfaction_vs_n.png`: easy density; almost all methods are strong, but runtime differences become very visible.
- `r4_3_satisfaction_vs_n.png`: near the phase transition; this is where solver differences matter most.
- `r6_satisfaction_vs_n.png`: dense hard cases; SA and GA separate more clearly from HC and BSGO.
- `snapshot_runtime_vs_satisfaction.png`: global quality-vs-cost picture from the available snapshot.
- `snapshot_gap_from_best.png`: per-instance distance from the best observed method on each available instance.

## Suggested conclusion

- Recommend `Simulated Annealing` as the default general-purpose solver.
- Recommend `Genetic Algorithm` as the main evolutionary/population alternative.
- Keep `Hill Climbing` as a baseline and explanatory algorithm.
- Treat `Binary Swarm (BSGO)` and `Hybrid BSGO-GA` as research/experimental methods that still need another tuning pass.
""",
        encoding="utf-8",
    )


def main() -> None:
    ensure_dirs()
    write_snapshot_csv()
    plot_ratio_lines(3.0, "satisfaction_rate", "Satisfaction rate (%)", "r3_satisfaction_vs_n.png")
    plot_ratio_lines(3.0, "runtime", "Runtime (seconds)", "r3_runtime_vs_n.png")
    plot_ratio_lines(4.3, "satisfaction_rate", "Satisfaction rate (%)", "r4_3_satisfaction_vs_n.png")
    plot_ratio_lines(4.3, "runtime", "Runtime (seconds)", "r4_3_runtime_vs_n.png")
    plot_ratio_lines(6.0, "satisfaction_rate", "Satisfaction rate (%)", "r6_satisfaction_vs_n.png")
    plot_ratio_lines(6.0, "runtime", "Runtime (seconds)", "r6_runtime_vs_n.png")
    plot_overall_snapshot_scatter()
    plot_gap_from_best()
    copy_existing_artifacts()
    write_analysis_report()
    print(FINAL_DIR)


if __name__ == "__main__":
    main()
