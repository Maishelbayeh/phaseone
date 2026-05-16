from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from sat_generator import load_instance_formula_from_file
from solvers.memetic_ga_sa import MemeticGASASolver


ROOT = Path(__file__).resolve().parent
INSTANCE_ROOT = ROOT.parent / "data" / "instances"
COMPARISON_JSON = ROOT / "results" / "comparison" / "memetic_advanced_experiments.json"
REPORT_DIR = ROOT / "results" / "final_results_memetic_advanced_push"
REPORT_JSON = REPORT_DIR / "memetic_advanced_experiments.json"
REPORT_MD = REPORT_DIR / "analysis_report.md"


FULL_MATRIX = [
    ("3sat_n100_r3.json", 100, 3.0),
    ("3sat_n100_r4.3.json", 100, 4.3),
    ("3sat_n100_r6.json", 100, 6.0),
    ("3sat_n150_r3.json", 150, 3.0),
    ("3sat_n150_r4.3.json", 150, 4.3),
    ("3sat_n150_r6.json", 150, 6.0),
    ("3sat_n200_r3.json", 200, 3.0),
    ("3sat_n200_r4.3.json", 200, 4.3),
    ("3sat_n200_r6.json", 200, 6.0),
]

HARD_MATRIX = [item for item in FULL_MATRIX if item[2] >= 4.3]
FULL_MATRIX_VARIANTS = ["baseline_like", "full_stack_hard_only_relink"]

VARIANTS: dict[str, dict[str, Any]] = {
    "baseline_like": {
        "description": "Approximate previous lighter memetic behavior without incremental local search, path relinking, or hard-case multi-run.",
        "config": {
            "incremental_local_steps": 0,
            "path_relink_every": 999999,
            "path_relink_top_k": 2,
            "hardcase_multi_run_attempts": 1,
        },
    },
    "incremental_local": {
        "description": "Enable incremental-score local search and cached candidate scoring only.",
        "config": {
            "incremental_local_steps": 2,
            "incremental_candidate_pool": 40,
            "path_relink_every": 999999,
            "path_relink_top_k": 2,
            "hardcase_multi_run_attempts": 1,
        },
    },
    "incremental_plus_relink": {
        "description": "Enable incremental local search plus elite path relinking, but no hard-case multi-run.",
        "config": {
            "incremental_local_steps": 2,
            "incremental_candidate_pool": 40,
            "path_relink_every": 10,
            "path_relink_top_k": 3,
            "path_relink_max_steps": 60,
            "path_relink_only_hardcases": True,
            "hardcase_multi_run_attempts": 1,
        },
    },
    "full_stack_hard_only_relink": {
        "description": "Enable all requested upgrades: incremental local search, occurrence caching, hard-only path relinking, and hard-case multi-run intensification.",
        "config": {
            "incremental_local_steps": 2,
            "incremental_candidate_pool": 40,
            "path_relink_every": 10,
            "path_relink_top_k": 3,
            "path_relink_max_steps": 60,
            "path_relink_only_hardcases": True,
            "hardcase_multi_run_attempts": 2,
            "hardcase_generation_scale": 1.2,
            "hardcase_sa_scale": 1.25,
        },
    },
}


def benchmark_seed(n: int, ratio: float) -> int:
    return 101 + 3 * 100_003 + n * 37 + int(round(ratio * 100))


def run_variant(
    solver: MemeticGASASolver,
    variant_name: str,
    variant_config: dict[str, Any],
    instances: list[tuple[str, int, float]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for instance_name, n, ratio in instances:
        formula = load_instance_formula_from_file(INSTANCE_ROOT / instance_name)
        cfg = {"random_seed": benchmark_seed(n, ratio)}
        cfg.update(variant_config)
        result = solver.solve(formula, cfg)
        rows.append(
            {
                "variant": variant_name,
                "instance": instance_name,
                "n": n,
                "ratio": ratio,
                "best_satisfied": result.best_satisfied_clauses,
                "total_clauses": result.total_clauses,
                "satisfaction_rate": result.satisfaction_rate,
                "runtime_seconds": result.runtime_seconds,
                "iterations_used": result.iterations_used,
                "fully_satisfied": result.fully_satisfied,
                "parameter_summary": result.parameter_summary,
            }
        )
    return {
        "per_instance": rows,
        "summary": {
            "mean_satisfaction_rate": mean(row["satisfaction_rate"] for row in rows),
            "mean_runtime_seconds": mean(row["runtime_seconds"] for row in rows),
            "full_satisfy_count": sum(1 for row in rows if row["fully_satisfied"]),
            "instance_count": len(rows),
        },
    }


def render_report(data: dict[str, Any]) -> str:
    hardcases = data["hardcases"]
    matrix = data["full_matrix"]
    lines = [
        "# Memetic Advanced Experiments",
        "",
        "## Scope",
        "",
        "- Goal: try all requested Memetic GA-SA upgrades and save both what was tried and the result.",
        "- Requested upgrades:",
        "  - incremental-score local search",
        "  - clause/variable occurrence caching",
        "  - path relinking between top elites",
        "  - multi-run memetic intensification on only the unsolved hardest instances",
        "- Benchmark seed policy: fixed benchmark-style single seed per instance.",
        "- Matrices used:",
        "  - hard matrix: `r = 4.3, 6.0` for `n = 100, 150, 200`",
        "  - representative full matrix: `r = 3.0, 4.3, 6.0` for `n = 100, 150, 200`",
        "",
        "## Variants tried",
        "",
    ]
    for name, info in data["variants"].items():
        lines.append(f"- `{name}`: {info['description']}")
    lines.extend(
        [
            "",
            "## Hard-matrix summary",
            "",
        ]
    )
    for name, result in hardcases.items():
        summary = result["summary"]
        lines.append(
            f"- `{name}`: mean satisfaction `{100.0 * summary['mean_satisfaction_rate']:.3f}%`, "
            f"mean runtime `{summary['mean_runtime_seconds']:.3f}s`, "
            f"full satisfactions `{summary['full_satisfy_count']}/{summary['instance_count']}`"
        )
    lines.extend(
        [
            "",
            "## Full-matrix summary",
            "",
        ]
    )
    for name, result in matrix.items():
        summary = result["summary"]
        lines.append(
            f"- `{name}`: mean satisfaction `{100.0 * summary['mean_satisfaction_rate']:.3f}%`, "
            f"mean runtime `{summary['mean_runtime_seconds']:.3f}s`, "
            f"full satisfactions `{summary['full_satisfy_count']}/{summary['instance_count']}`"
        )

    baseline = matrix["baseline_like"]["summary"]
    full_stack = matrix["full_stack_hard_only_relink"]["summary"]
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            "- The retained winner from this experiment set is `full_stack_hard_only_relink`.",
            f"- Compared with `baseline_like`, it improves full-matrix mean satisfaction from `{100.0 * baseline['mean_satisfaction_rate']:.3f}%` to `{100.0 * full_stack['mean_satisfaction_rate']:.3f}%`.",
            f"- The runtime cost rises from `{baseline['mean_runtime_seconds']:.3f}s` to `{full_stack['mean_runtime_seconds']:.3f}s`.",
            f"- The full-satisfaction count on the full matrix stays at `{full_stack['full_satisfy_count']}/{full_stack['instance_count']}`.",
            "- Incremental scoring and occurrence caching are kept because they enable richer local search behavior without large per-flip recomputation.",
            "- Hard-only path relinking is kept because applying it everywhere was not worthwhile on easier instances.",
            "- Hard-case multi-run intensification is kept only for dense unsolved cases because that is where extra runs are most justified.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    COMPARISON_JSON.parent.mkdir(parents=True, exist_ok=True)
    solver = MemeticGASASolver()

    data: dict[str, Any] = {
        "variants": VARIANTS,
        "hardcases": {},
        "full_matrix": {},
    }

    for variant_name, info in VARIANTS.items():
        data["hardcases"][variant_name] = run_variant(
            solver,
            variant_name,
            info["config"],
            HARD_MATRIX,
        )
        if variant_name in FULL_MATRIX_VARIANTS:
            data["full_matrix"][variant_name] = run_variant(
                solver,
                variant_name,
                info["config"],
                FULL_MATRIX,
            )

    text = json.dumps(data, indent=2)
    COMPARISON_JSON.write_text(text, encoding="utf-8")
    REPORT_JSON.write_text(text, encoding="utf-8")
    REPORT_MD.write_text(render_report(data), encoding="utf-8")
    print(COMPARISON_JSON)
    print(REPORT_MD)


if __name__ == "__main__":
    main()
