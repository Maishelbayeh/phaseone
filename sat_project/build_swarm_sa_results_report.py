from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
SOURCE_JSON = ROOT / "results" / "comparison" / "sa_ga_swarm_memetic_swarmsa_medium.json"
TARGET_DIR = ROOT / "results" / "final_results_swarm_sa"
PLOTS_DIR = TARGET_DIR / "plots"

ALGORITHM_ORDER = [
    "Simulated Annealing",
    "Genetic Algorithm",
    "Binary Swarm (BSGO)",
    "Memetic GA-SA",
    "Swarm-SA Hybrid",
]
COLORS = {
    "Simulated Annealing": "#1f77b4",
    "Genetic Algorithm": "#2ca02c",
    "Binary Swarm (BSGO)": "#9467bd",
    "Memetic GA-SA": "#d62728",
    "Swarm-SA Hybrid": "#ff7f0e",
}
INSTANCE_ORDER = [
    "3sat_n100_r3.json",
    "3sat_n100_r4.3.json",
    "3sat_n100_r6.json",
    "3sat_n150_r3.json",
    "3sat_n150_r4.3.json",
    "3sat_n150_r6.json",
    "3sat_n200_r3.json",
    "3sat_n200_r4.3.json",
    "3sat_n200_r6.json",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def copy_source_files() -> None:
    if SOURCE_JSON.exists():
        shutil.copy2(SOURCE_JSON, TARGET_DIR / SOURCE_JSON.name)


def write_per_run_csv(rows: list[dict]) -> None:
    path = TARGET_DIR / "sa_ga_swarm_memetic_swarmsa_medium.csv"
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=[
                "instance",
                "n",
                "ratio",
                "algorithm_name",
                "best_satisfied",
                "total_clauses",
                "satisfaction_rate",
                "runtime_seconds",
                "iterations_used",
                "fully_satisfied",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "instance": row["instance"],
                    "n": row["n"],
                    "ratio": row["ratio"],
                    "algorithm_name": row["algorithm_name"],
                    "best_satisfied": row["best_satisfied"],
                    "total_clauses": row["total_clauses"],
                    "satisfaction_rate": row["satisfaction_rate"],
                    "runtime_seconds": row["runtime_seconds"],
                    "iterations_used": row["iterations_used"],
                    "fully_satisfied": row["fully_satisfied"],
                }
            )


def ordered_summary_rows(summary: list[dict]) -> list[dict]:
    return sorted(summary, key=lambda row: ALGORITHM_ORDER.index(row["algorithm_name"]))


def overall_bar(summary: list[dict], metric_key: str, ylabel: str, filename: str) -> None:
    ordered = ordered_summary_rows(summary)
    names = [row["algorithm_name"] for row in ordered]
    values = []
    for row in ordered:
        value = row[metric_key]
        if metric_key == "mean_satisfaction_rate":
            value *= 100.0
        values.append(value)
    plt.figure(figsize=(10, 5.5))
    plt.bar(names, values, color=[COLORS[name] for name in names])
    plt.ylabel(ylabel)
    plt.title(ylabel)
    plt.xticks(rotation=18, ha="right")
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=160)
    plt.close()


def scatter_runtime_vs_quality(rows: list[dict]) -> None:
    plt.figure(figsize=(9.5, 6))
    for algorithm in ALGORITHM_ORDER:
        algo_rows = [row for row in rows if row["algorithm_name"] == algorithm]
        plt.scatter(
            [row["runtime_seconds"] for row in algo_rows],
            [100.0 * row["satisfaction_rate"] for row in algo_rows],
            label=algorithm,
            color=COLORS[algorithm],
            s=70,
            alpha=0.8,
        )
    plt.xlabel("Runtime (seconds)")
    plt.ylabel("Satisfaction rate (%)")
    plt.title("Runtime vs Satisfaction Rate")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "runtime_vs_satisfaction.png", dpi=160)
    plt.close()


def plot_by_ratio(data: dict, metric_key: str, ylabel: str, filename: str) -> None:
    ratios = [3.0, 4.3, 6.0]
    plt.figure(figsize=(10, 6))
    for algorithm in ALGORITHM_ORDER:
        y_values = []
        for ratio in ratios:
            row = next(item for item in data[str(ratio)] if item["algorithm_name"] == algorithm)
            value = row[metric_key]
            if metric_key == "mean_satisfaction_rate":
                value *= 100.0
            y_values.append(value)
        plt.plot(ratios, y_values, marker="o", linewidth=2, label=algorithm, color=COLORS[algorithm])
    plt.xlabel("Clause density ratio (m/n)")
    plt.ylabel(ylabel)
    plt.title(f"{ylabel} by clause density")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=160)
    plt.close()


def plot_by_n(data: dict, metric_key: str, ylabel: str, filename: str) -> None:
    sizes = [100, 150, 200]
    plt.figure(figsize=(10, 6))
    for algorithm in ALGORITHM_ORDER:
        y_values = []
        for n_value in sizes:
            row = next(item for item in data[str(n_value)] if item["algorithm_name"] == algorithm)
            value = row[metric_key]
            if metric_key == "mean_satisfaction_rate":
                value *= 100.0
            y_values.append(value)
        plt.plot(sizes, y_values, marker="o", linewidth=2, label=algorithm, color=COLORS[algorithm])
    plt.xlabel("Number of variables (n)")
    plt.ylabel(ylabel)
    plt.title(f"{ylabel} by problem size")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=160)
    plt.close()


def plot_per_instance_quality(rows: list[dict]) -> None:
    x_positions = list(range(len(INSTANCE_ORDER)))
    width = 0.16
    offsets = [-2, -1, 0, 1, 2]

    plt.figure(figsize=(15, 6))
    for offset, algorithm in zip(offsets, ALGORITHM_ORDER):
        values = []
        for instance in INSTANCE_ORDER:
            row = next(item for item in rows if item["instance"] == instance and item["algorithm_name"] == algorithm)
            values.append(100.0 * row["satisfaction_rate"])
        shifted = [x + offset * width for x in x_positions]
        plt.bar(shifted, values, width=width, label=algorithm, color=COLORS[algorithm])

    plt.xticks(x_positions, INSTANCE_ORDER, rotation=40, ha="right")
    plt.ylabel("Satisfaction rate (%)")
    plt.title("Per-instance quality comparison")
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "per_instance_quality.png", dpi=160)
    plt.close()


def plot_per_instance_metric(
    rows: list[dict], metric_key: str, ylabel: str, title: str, filename: str
) -> None:
    x_positions = list(range(len(INSTANCE_ORDER)))
    width = 0.16
    offsets = [-2, -1, 0, 1, 2]

    plt.figure(figsize=(15, 6))
    for offset, algorithm in zip(offsets, ALGORITHM_ORDER):
        values = []
        for instance in INSTANCE_ORDER:
            row = next(item for item in rows if item["instance"] == instance and item["algorithm_name"] == algorithm)
            value = row[metric_key]
            if metric_key == "satisfaction_rate":
                value = 100.0 * value
            values.append(value)
        shifted = [x + offset * width for x in x_positions]
        plt.bar(shifted, values, width=width, label=algorithm, color=COLORS[algorithm])

    plt.xticks(x_positions, INSTANCE_ORDER, rotation=40, ha="right")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=160)
    plt.close()


def plot_convergence(rows: list[dict]) -> None:
    plt.figure(figsize=(10.5, 6))
    for algorithm in ALGORITHM_ORDER:
        histories = [row["best_history"] for row in rows if row["algorithm_name"] == algorithm]
        if not histories:
            continue
        max_len = max(len(history) for history in histories)
        averaged = []
        for idx in range(max_len):
            values = []
            for history in histories:
                values.append(history[idx] if idx < len(history) else history[-1])
            averaged.append(mean(values))
        plt.plot(range(len(averaged)), averaged, linewidth=2, label=algorithm, color=COLORS[algorithm])
    plt.xlabel("Iteration / generation")
    plt.ylabel("Best satisfied clauses")
    plt.title("Mean convergence by solver")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "convergence_plot.png", dpi=160)
    plt.close()


def write_report(current: dict) -> None:
    overall = {row["algorithm_name"]: row for row in current["overall"]}
    sa = overall["Simulated Annealing"]
    ga = overall["Genetic Algorithm"]
    swarm = overall["Binary Swarm (BSGO)"]
    memetic = overall["Memetic GA-SA"]
    swarm_sa = overall["Swarm-SA Hybrid"]

    text = f"""# SA / GA / Swarm / Hybrids Analysis

## Scope

- Benchmark file: `sa_ga_swarm_memetic_swarmsa_medium.json`
- Instances: `n = 100, 150, 200`
- Ratios: `r = 3.0, 4.3, 6.0`
- Compared solvers:
  - `Simulated Annealing`
  - `Genetic Algorithm`
  - `Binary Swarm (BSGO)`
  - `Memetic GA-SA`
  - `Swarm-SA Hybrid`

## Main conclusions

- `Simulated Annealing` remains the fastest strong solver and the best practical default.
- The tuned `Memetic GA-SA` is much faster than its older heavy version because the expensive step was repeated bounded SA on multiple elites with a large fixed budget.
- The new memetic version reduces cost by using adaptive SA budgets, early stopping inside SA, and restart-style diversity recovery.
- `Swarm-SA Hybrid` is the explicit swarm-plus-SA method requested for comparison.
- The new `Swarm-SA Hybrid` is stronger than plain swarm in local intensification, but it still needs to justify its extra cost against `SA` and the tuned memetic solver.

## Overall ranking

- `Simulated Annealing`: mean satisfaction `{100.0 * sa["mean_satisfaction_rate"]:.3f}%`, mean runtime `{sa["mean_runtime_seconds"]:.2f}s`, mean iterations `{sa["mean_iterations_used"]:.1f}`
- `Genetic Algorithm`: mean satisfaction `{100.0 * ga["mean_satisfaction_rate"]:.3f}%`, mean runtime `{ga["mean_runtime_seconds"]:.2f}s`, mean iterations `{ga["mean_iterations_used"]:.1f}`
- `Binary Swarm (BSGO)`: mean satisfaction `{100.0 * swarm["mean_satisfaction_rate"]:.3f}%`, mean runtime `{swarm["mean_runtime_seconds"]:.2f}s`, mean iterations `{swarm["mean_iterations_used"]:.1f}`
- `Memetic GA-SA`: mean satisfaction `{100.0 * memetic["mean_satisfaction_rate"]:.3f}%`, mean runtime `{memetic["mean_runtime_seconds"]:.2f}s`, mean iterations `{memetic["mean_iterations_used"]:.1f}`
- `Swarm-SA Hybrid`: mean satisfaction `{100.0 * swarm_sa["mean_satisfaction_rate"]:.3f}%`, mean runtime `{swarm_sa["mean_runtime_seconds"]:.2f}s`, mean iterations `{swarm_sa["mean_iterations_used"]:.1f}`

## Why Memetic GA-SA time dropped

- The earlier heavy version paid too much for elite refinement:
  - too many SA calls,
  - too many SA iterations per call,
  - too little early stopping once refinement stopped improving.
- The tuned version reduces runtime using:
  - adaptive SA iteration budgets,
  - SA patience-based early stop,
  - fewer useful refinement calls instead of always spending the full budget,
  - controlled population refresh when the GA stalls.

## Why Swarm-SA is separate from Binary Swarm

- `Binary Swarm (BSGO)` stays as the tuned swarm baseline.
- `Swarm-SA Hybrid` uses a swarm outer loop with explicit periodic SA refinement on elite particles.
- This makes the comparison clearer:
  - `Swarm` = tuned population movement baseline,
  - `Swarm-SA` = swarm plus stronger local refinement.

## Recommended use

- Use `Simulated Annealing` when you want the best speed and still high solution quality.
- Use `Memetic GA-SA` when you want a stronger GA+SA hybrid without the old runtime explosion.
- Use `Binary Swarm (BSGO)` as the improved swarm baseline.
- Use `Swarm-SA Hybrid` when you specifically want to study swarm plus local annealing, not when you only want the fastest practical solver.
"""
    (TARGET_DIR / "analysis_report.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    current = load_json(SOURCE_JSON)
    rows = current["per_run"]

    copy_source_files()
    write_per_run_csv(rows)
    overall_bar(current["overall"], "mean_satisfaction_rate", "Mean satisfaction rate (%)", "overall_satisfaction_bar.png")
    overall_bar(current["overall"], "mean_runtime_seconds", "Mean runtime (seconds)", "overall_runtime_bar.png")
    overall_bar(current["overall"], "mean_iterations_used", "Mean iterations / generations", "overall_iterations_bar.png")
    scatter_runtime_vs_quality(rows)
    plot_by_ratio(current["by_ratio"], "mean_satisfaction_rate", "Mean satisfaction rate (%)", "quality_by_ratio.png")
    plot_by_ratio(current["by_ratio"], "mean_runtime_seconds", "Mean runtime (seconds)", "runtime_by_ratio.png")
    plot_by_ratio(current["by_ratio"], "mean_iterations_used", "Mean iterations / generations", "iterations_by_ratio.png")
    plot_by_n(current["by_n"], "mean_satisfaction_rate", "Mean satisfaction rate (%)", "quality_by_size.png")
    plot_by_n(current["by_n"], "mean_runtime_seconds", "Mean runtime (seconds)", "runtime_by_size.png")
    plot_by_n(current["by_n"], "mean_iterations_used", "Mean iterations / generations", "iterations_by_size.png")
    plot_per_instance_quality(rows)
    plot_per_instance_metric(
        rows,
        "runtime_seconds",
        "Runtime (seconds)",
        "Per-instance runtime comparison",
        "per_instance_runtime.png",
    )
    plot_per_instance_metric(
        rows,
        "iterations_used",
        "Iterations / generations",
        "Per-instance iteration comparison",
        "per_instance_iterations.png",
    )
    plot_convergence(rows)
    write_report(current)
    print(TARGET_DIR)


if __name__ == "__main__":
    main()
