from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from sat_generator import load_instance_formula_from_file
from solvers.memetic_ga_sa import MemeticGASASolver


ROOT = Path(__file__).resolve().parent
INSTANCE_ROOT = ROOT.parent / "data" / "instances"
COMPARISON_JSON = ROOT / "results" / "comparison" / "memetic_post_alignment_hardcases.json"
REPORT_DIR = ROOT / "results" / "final_results_memetic_advanced_push"
REPORT_JSON = REPORT_DIR / "memetic_post_alignment_hardcases.json"

HARD_MATRIX = [
    ("3sat_n100_r4.3.json", 100, 4.3),
    ("3sat_n100_r6.json", 100, 6.0),
    ("3sat_n150_r4.3.json", 150, 4.3),
    ("3sat_n150_r6.json", 150, 6.0),
    ("3sat_n200_r4.3.json", 200, 4.3),
    ("3sat_n200_r6.json", 200, 6.0),
]


def benchmark_seed(n: int, ratio: float) -> int:
    return 101 + 3 * 100_003 + n * 37 + int(round(ratio * 100))


def main() -> None:
    COMPARISON_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    solver = MemeticGASASolver()
    rows: list[dict[str, Any]] = []
    for instance_name, n, ratio in HARD_MATRIX:
        formula = load_instance_formula_from_file(INSTANCE_ROOT / instance_name)
        seed = benchmark_seed(n, ratio)
        result = solver.solve(formula, {"random_seed": seed})
        rows.append(
            {
                "instance": instance_name,
                "n": n,
                "ratio": ratio,
                "random_seed": seed,
                "best_satisfied": result.best_satisfied_clauses,
                "total_clauses": result.total_clauses,
                "satisfaction_rate": result.satisfaction_rate,
                "runtime_seconds": result.runtime_seconds,
                "iterations_used": result.iterations_used,
                "fully_satisfied": result.fully_satisfied,
                "parameter_summary": result.parameter_summary,
            }
        )

    data = {
        "scope": "Post-alignment verification of Memetic GA-SA built-in defaults on the hard unsolved instance family.",
        "matrix": HARD_MATRIX,
        "summary": {
            "mean_satisfaction_rate": mean(row["satisfaction_rate"] for row in rows),
            "mean_runtime_seconds": mean(row["runtime_seconds"] for row in rows),
            "full_satisfy_count": sum(1 for row in rows if row["fully_satisfied"]),
            "instance_count": len(rows),
        },
        "per_instance": rows,
    }

    text = json.dumps(data, indent=2)
    COMPARISON_JSON.write_text(text, encoding="utf-8")
    REPORT_JSON.write_text(text, encoding="utf-8")
    print(COMPARISON_JSON)
    print(REPORT_JSON)


if __name__ == "__main__":
    main()
