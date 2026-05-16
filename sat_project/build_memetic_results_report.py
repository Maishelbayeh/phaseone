from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
SOURCE_JSON = ROOT / "results" / "comparison" / "memetic_vs_sa_ga_hybrid_medium.json"
LEGACY_JSON = ROOT / "results" / "comparison" / "saved_hybrid_bsgo_ga_before_memetic.json"
TARGET_DIR = ROOT / "results" / "final_results_memetic_ga_sa"
PLOTS_DIR = TARGET_DIR / "plots"

ALGORITHM_ORDER = [
    "Memetic GA-SA",
    "Simulated Annealing",
    "Genetic Algorithm",
    "Hybrid BSGO-GA",
]
COLORS = {
    "Memetic GA-SA": "#d62728",
    "Simulated Annealing": "#1f77b4",
    "Genetic Algorithm": "#2ca02c",
    "Hybrid BSGO-GA": "#9467bd",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dirs() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def write_per_run_csv(rows: list[dict]) -> None:
    path = TARGET_DIR / "memetic_vs_sa_ga_hybrid_medium.csv"
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


def copy_source_files() -> None:
    for source in [SOURCE_JSON, LEGACY_JSON]:
        if source.exists():
            shutil.copy2(source, TARGET_DIR / source.name)


def overall_bar(summary: list[dict], metric_key: str, ylabel: str, filename: str) -> None:
    ordered = sorted(summary, key=lambda row: ALGORITHM_ORDER.index(row["algorithm_name"]))
    names = [row["algorithm_name"] for row in ordered]
    values = [
        100.0 * row[metric_key] if metric_key == "mean_satisfaction_rate" else row[metric_key]
        for row in ordered
    ]
    plt.figure(figsize=(9, 5))
    plt.bar(names, values, color=[COLORS[name] for name in names])
    plt.ylabel(ylabel)
    plt.title(ylabel)
    plt.xticks(rotation=15, ha="right")
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / filename, dpi=160)
    plt.close()


def scatter_runtime_vs_quality(rows: list[dict]) -> None:
    plt.figure(figsize=(9, 6))
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
    instance_order = [
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
    x_positions = list(range(len(instance_order)))
    width = 0.2
    offsets = [-1.5, -0.5, 0.5, 1.5]

    plt.figure(figsize=(14, 6))
    for offset, algorithm in zip(offsets, ALGORITHM_ORDER):
        values = []
        for instance in instance_order:
            row = next(item for item in rows if item["instance"] == instance and item["algorithm_name"] == algorithm)
            values.append(100.0 * row["satisfaction_rate"])
        shifted = [x + offset * width for x in x_positions]
        plt.bar(shifted, values, width=width, label=algorithm, color=COLORS[algorithm])

    plt.xticks(x_positions, instance_order, rotation=40, ha="right")
    plt.ylabel("Satisfaction rate (%)")
    plt.title("Per-instance quality comparison")
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "per_instance_quality.png", dpi=160)
    plt.close()


def plot_memetic_gain(rows: list[dict]) -> None:
    instance_order = [
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
    baselines = ["Simulated Annealing", "Genetic Algorithm", "Hybrid BSGO-GA"]
    plt.figure(figsize=(14, 6))
    width = 0.25
    offsets = [-1, 0, 1]
    for offset, baseline in zip(offsets, baselines):
        gains = []
        for instance in instance_order:
            memetic = next(
                item for item in rows if item["instance"] == instance and item["algorithm_name"] == "Memetic GA-SA"
            )
            other = next(item for item in rows if item["instance"] == instance and item["algorithm_name"] == baseline)
            gains.append(memetic["best_satisfied"] - other["best_satisfied"])
        shifted = [i + offset * width for i in range(len(instance_order))]
        plt.bar(shifted, gains, width=width, label=f"Memetic - {baseline}", alpha=0.9)
    plt.axhline(0.0, color="black", linewidth=1)
    plt.xticks(range(len(instance_order)), instance_order, rotation=40, ha="right")
    plt.ylabel("Satisfied-clause gain")
    plt.title("Memetic GA-SA improvement over baselines")
    plt.grid(axis="y", alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "memetic_gain_vs_baselines.png", dpi=160)
    plt.close()


def write_report(current: dict, legacy: dict) -> None:
    current_overall = {row["algorithm_name"]: row for row in current["overall"]}
    legacy_overall = {row["algorithm_name"]: row for row in legacy["overall"]}
    memetic = current_overall["Memetic GA-SA"]
    sa = current_overall["Simulated Annealing"]
    ga = current_overall["Genetic Algorithm"]
    hybrid = current_overall["Hybrid BSGO-GA"]

    text = f"""# Memetic GA-SA Results Analysis

## Scope

- Benchmark file: `memetic_vs_sa_ga_hybrid_medium.json`
- Instances: `n = 100, 150, 200`
- Ratios: `r = 3.0, 4.3, 6.0`
- Compared solvers:
  - `Simulated Annealing`
  - `Genetic Algorithm`
  - `Memetic GA-SA`
  - `Hybrid BSGO-GA`

## Main conclusion

- `Memetic GA-SA` is the best solver in this benchmark by solution quality.
- `Simulated Annealing` is still by far the best solver by runtime efficiency.
- `Memetic GA-SA` is clearly better than plain `GA`.
- `Memetic GA-SA` is also clearly better than the current `Hybrid BSGO-GA`.

## Overall ranking

- `Memetic GA-SA`: mean satisfaction `{100.0 * memetic["mean_satisfaction_rate"]:.3f}%`, mean runtime `{memetic["mean_runtime_seconds"]:.2f}s`, full satisfactions `{memetic["full_satisfy_count"]}/9`
- `Simulated Annealing`: mean satisfaction `{100.0 * sa["mean_satisfaction_rate"]:.3f}%`, mean runtime `{sa["mean_runtime_seconds"]:.2f}s`, full satisfactions `{sa["full_satisfy_count"]}/9`
- `Genetic Algorithm`: mean satisfaction `{100.0 * ga["mean_satisfaction_rate"]:.3f}%`, mean runtime `{ga["mean_runtime_seconds"]:.2f}s`
- `Hybrid BSGO-GA`: mean satisfaction `{100.0 * hybrid["mean_satisfaction_rate"]:.3f}%`, mean runtime `{hybrid["mean_runtime_seconds"]:.2f}s`

## What improved compared with the old heavy hybrid benchmark

- Old saved `Hybrid BSGO-GA` mean satisfaction: `{100.0 * legacy_overall["Hybrid BSGO-GA"]["mean_satisfaction_rate"]:.3f}%`
- New `Memetic GA-SA` mean satisfaction: `{100.0 * memetic["mean_satisfaction_rate"]:.3f}%`
- Old saved `Hybrid BSGO-GA` mean runtime: `{legacy_overall["Hybrid BSGO-GA"]["mean_runtime_seconds"]:.2f}s`
- New `Memetic GA-SA` mean runtime: `{memetic["mean_runtime_seconds"]:.2f}s`
- This means the new memetic design improves both quality and runtime compared with the old heavy hybrid snapshot.

## Why Memetic GA-SA works better

- `GA` provides population diversity and recombination.
- `SA` provides strong local refinement and very effective escape from weak local structure.
- Refining only top elites every few generations keeps the method memetic without paying the cost of refining the entire population every generation.
- This selective design is much lighter than the previous `Hybrid BSGO-GA`.

## Why SA is still important

- `Simulated Annealing` is still the best practical default when runtime matters.
- The quality gap between `Memetic GA-SA` and `SA` is real, but small compared with the runtime gap.
- On hard instances the memetic solver often gains a few additional satisfied clauses, but it pays tens of seconds more.

## Swarm status

- `Binary Swarm (BSGO)` is not included in this new benchmark because the focus here is the new memetic solver.
- Based on the earlier saved benchmark snapshot, swarm is still behind `SA`, `GA`, and now also behind `Memetic GA-SA`.
- So no, the current swarm is not yet the strongest version you can reach.

## Recommended use

- Use `Simulated Annealing` when you want the best speed and still excellent quality.
- Use `Memetic GA-SA` when you want the best solution quality and can afford more runtime.
- Use `Genetic Algorithm` as the simpler population baseline.
- Treat `Hybrid BSGO-GA` as an older heavy hybrid that is now outperformed by the memetic solver.
"""
    (TARGET_DIR / "analysis_report.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    current = load_json(SOURCE_JSON)
    legacy = load_json(LEGACY_JSON)
    rows = current["per_run"]

    copy_source_files()
    write_per_run_csv(rows)
    overall_bar(current["overall"], "mean_satisfaction_rate", "Mean satisfaction rate (%)", "overall_satisfaction_bar.png")
    overall_bar(current["overall"], "mean_runtime_seconds", "Mean runtime (seconds)", "overall_runtime_bar.png")
    scatter_runtime_vs_quality(rows)
    plot_by_ratio(current["by_ratio"], "mean_satisfaction_rate", "Mean satisfaction rate (%)", "quality_by_ratio.png")
    plot_by_ratio(current["by_ratio"], "mean_runtime_seconds", "Mean runtime (seconds)", "runtime_by_ratio.png")
    plot_by_n(current["by_n"], "mean_satisfaction_rate", "Mean satisfaction rate (%)", "quality_by_size.png")
    plot_by_n(current["by_n"], "mean_runtime_seconds", "Mean runtime (seconds)", "runtime_by_size.png")
    plot_per_instance_quality(rows)
    plot_memetic_gain(rows)
    write_report(current, legacy)
    print(TARGET_DIR)


if __name__ == "__main__":
    main()
