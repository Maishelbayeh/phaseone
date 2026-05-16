"""
Random search over solver hyperparameters on one CNF instance (e.g. data/instances JSON).

Goal: find parameter sets that maximize satisfied clauses and (when possible) reach full
satisfaction. This does **not** guarantee SAT: hard random 3-SAT near the phase transition
(m/n ~ 4.26) is often infeasible for simple local search in reasonable time.

Usage (from ``sat_project/``)::

    python tune_parameters.py --instance ../data/instances/3sat_n100_r4.3.json
    python tune_parameters.py --instance path/to.json --trials 50 --base-seed 1

Writes ``results/data/tuning_best_params.json`` with best-found settings per algorithm.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hill_climbing import hill_climb_with_random_restarts
from hybrid_bsgo_ga import hybrid_bsgo_ga_search
from simulated_annealing import simulated_annealing_search
from sat_generator import load_instance_formula_from_file
from tabu_search import tabu_search_solve
from utils import CNFFormula


@dataclass
class TrialRecord:
    algorithm: str
    random_seed: int
    params: Dict[str, Any]
    best_merit: int
    total_clauses: int
    fully_satisfied: bool
    runtime_seconds: float
    iterations_used: int


def _is_better(candidate: TrialRecord, current: Optional[TrialRecord]) -> bool:
    if current is None:
        return True
    if candidate.fully_satisfied and not current.fully_satisfied:
        return True
    if current.fully_satisfied and not candidate.fully_satisfied:
        return False
    if candidate.best_merit > current.best_merit:
        return True
    if candidate.best_merit < current.best_merit:
        return False
    if candidate.runtime_seconds < current.runtime_seconds:
        return True
    return False


def _sample_hill_climbing_params(n: int, rng: random.Random) -> Dict[str, Any]:
    low = max(250, 5 * n)
    high = max(2500, 60 * n)
    if low >= high:
        high = low + 500
    return {
        "max_iterations_per_restart": rng.randint(low, high),
        "max_random_restarts": rng.randint(4, min(48, max(8, n // 4))),
    }


def _sample_simulated_annealing_params(n: int, rng: random.Random) -> Dict[str, Any]:
    t0 = rng.choice([0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0])
    cooling = rng.choice([0.985, 0.99, 0.992, 0.995, 0.997, 0.998, 0.999])
    tmin = rng.choice([0.0005, 0.001, 0.005, 0.01, 0.02, 0.05])
    if tmin >= t0 * 0.5:
        tmin = t0 * 0.01
    low_iter = max(1500, 15 * n)
    high_iter = max(8000, 120 * n)
    if low_iter >= high_iter:
        high_iter = low_iter + 2000
    return {
        "max_iterations": rng.randint(low_iter, high_iter),
        "initial_temperature": t0,
        "cooling_rate": cooling,
        "min_temperature": tmin,
    }


def _sample_tabu_params(n: int, rng: random.Random) -> Dict[str, Any]:
    low_iter = max(2000, 20 * n)
    high_iter = max(12000, 200 * n)
    if low_iter >= high_iter:
        high_iter = low_iter + 3000
    t_low = max(4, min(n // 40, 15))
    t_high = max(t_low + 2, min(n // 2, 80))
    return {
        "max_iterations": rng.randint(low_iter, high_iter),
        "tabu_tenure": rng.randint(t_low, t_high),
    }


def _sample_hybrid_bsgo_params(n: int, rng: random.Random) -> Dict[str, Any]:
    pop_lo = max(12, min(24, n // 2))
    pop_hi = max(pop_lo + 4, min(96, max(n // 5, 40)))
    gen_lo = max(80, n // 2)
    gen_hi = max(gen_lo + 50, min(2500, 15 * n))
    mut_hi = min(0.08, max(2.0 / max(n, 1), 0.005))
    mut_lo = min(mut_hi * 0.25, mut_hi * 0.5)
    return {
        "population_size": rng.randint(pop_lo, pop_hi),
        "max_iterations": rng.randint(gen_lo, gen_hi),
        "crossover_rate": round(rng.uniform(0.55, 0.95), 3),
        "mutation_rate": round(rng.uniform(mut_lo, mut_hi), 5),
        "c_coefficient": round(rng.uniform(0.35, 0.92), 3),
    }


def _run_trial(
    formula: CNFFormula,
    algorithm: str,
    params: Dict[str, Any],
    random_seed: int,
) -> TrialRecord:
    if algorithm == "hill_climbing":
        r = hill_climb_with_random_restarts(formula, random_seed=random_seed, **params)
    elif algorithm == "simulated_annealing":
        r = simulated_annealing_search(formula, random_seed=random_seed, **params)
    elif algorithm == "tabu_search":
        r = tabu_search_solve(formula, random_seed=random_seed, **params)
    elif algorithm == "hybrid_bsgo_ga":
        r = hybrid_bsgo_ga_search(formula, random_seed=random_seed, **params)
    else:
        raise ValueError(algorithm)

    return TrialRecord(
        algorithm=algorithm,
        random_seed=random_seed,
        params=dict(params),
        best_merit=r.best_merit,
        total_clauses=r.total_clauses,
        fully_satisfied=bool(r.fully_satisfied),
        runtime_seconds=float(r.runtime_seconds),
        iterations_used=int(r.iterations_used),
    )


def tune_algorithm(
    formula: CNFFormula,
    algorithm: str,
    trials: int,
    rng: random.Random,
) -> Tuple[Optional[TrialRecord], List[TrialRecord]]:
    n = formula.num_variables
    history: List[TrialRecord] = []
    best: Optional[TrialRecord] = None
    for _ in range(trials):
        seed = rng.randint(0, 2_147_483_647)
        if algorithm == "hill_climbing":
            params = _sample_hill_climbing_params(n, rng)
        elif algorithm == "simulated_annealing":
            params = _sample_simulated_annealing_params(n, rng)
        elif algorithm == "tabu_search":
            params = _sample_tabu_params(n, rng)
        elif algorithm == "hybrid_bsgo_ga":
            params = _sample_hybrid_bsgo_params(n, rng)
        else:
            raise ValueError(algorithm)

        rec = _run_trial(formula, algorithm, params, seed)
        history.append(rec)
        if _is_better(rec, best):
            best = rec
        if rec.fully_satisfied:
            break
    return best, history


def _print_strategy_guide(n: int, m: int) -> None:
    ratio = m / n if n else 0.0
    lines = [
        "",
        "--- How to interpret results ---",
        f"Instance shape: n={n}, m={m}, m/n ~ {ratio:.3f}.",
    ]
    if 4.0 <= ratio <= 4.5:
        lines.append(
            "This density is near the random 3-SAT phase transition: instances are typically "
            "very hard; full satisfaction with hill climbing / SA / tabu / population heuristics "
            "is uncommon unless n is small or the instance is easy."
        )
    elif ratio < 3.5:
        lines.append("Relatively under-constrained: local search often reaches very high merit; full SAT is more plausible.")
    else:
        lines.append("High density: many constraints; try large iteration budgets and many hill-climbing restarts.")

    lines.extend(
        [
            "",
            "General tuning hints:",
            "  Hill climbing: increase max_random_restarts first, then max_iterations_per_restart.",
            "  Simulated annealing: more max_iterations; slower cooling (closer to 1); T0 a few times m.",
            "  Tabu: tenure often ~ n/10 .. n/3; raise max_iterations if merit plateaus early.",
            "  Hybrid BSGO-GA: larger population and more generations; mutation ~ O(1/n); c in [0.5, 0.85].",
        ]
    )
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Random-search solver parameters on one CNF JSON instance.")
    parser.add_argument(
        "--instance",
        type=str,
        required=True,
        help="Path to instance JSON (3sat_*.json with clauses in 1-based literal form).",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=24,
        help="Random configurations tested per algorithm (default: 24).",
    )
    parser.add_argument(
        "--base-seed",
        type=int,
        default=42,
        help="Master RNG seed for sampling parameter sets and per-trial seeds.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Optional JSON path for best params (default: results/data/tuning_best_params.json).",
    )
    args = parser.parse_args()

    trials = max(1, args.trials)
    instance_path = Path(args.instance)
    if not instance_path.is_file():
        print(f"Error: file not found: {instance_path}", file=sys.stderr)
        sys.exit(1)

    formula = load_instance_formula_from_file(instance_path)
    n, m = formula.num_variables, formula.num_clauses
    rng = random.Random(args.base_seed)

    algorithms = ("hill_climbing", "simulated_annealing", "tabu_search", "hybrid_bsgo_ga")
    summary: Dict[str, Any] = {
        "instance": str(instance_path.resolve()),
        "n": n,
        "m": m,
        "trials_per_algorithm": trials,
        "base_seed": args.base_seed,
        "best": {},
    }

    print(f"Tuning on {instance_path.name} (n={n}, m={m}), {trials} trials per algorithm...")
    for algo in algorithms:
        best, _hist = tune_algorithm(formula, algo, trials, rng)
        if best is None:
            continue
        summary["best"][algo] = {
            "random_seed": best.random_seed,
            "params": best.params,
            "best_merit": best.best_merit,
            "total_clauses": best.total_clauses,
            "fully_satisfied": best.fully_satisfied,
            "runtime_seconds": best.runtime_seconds,
            "iterations_used": best.iterations_used,
        }
        print(
            f"  [{algo}] best merit {best.best_merit}/{best.total_clauses} "
            f"fully_satisfied={best.fully_satisfied} runtime={best.runtime_seconds:.3f}s "
            f"seed={best.random_seed} params={best.params}"
        )

    out_path = Path(args.output) if args.output else Path(__file__).resolve().parent / "results" / "data" / "tuning_best_params.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nWrote: {out_path}")

    print("\n--- Suggested values for the GUI (best random-search trial) ---")
    display_names = {
        "hill_climbing": "Hill Climbing",
        "simulated_annealing": "Simulated Annealing",
        "tabu_search": "Tabu Search",
        "hybrid_bsgo_ga": "Hybrid BSGO-GA",
    }
    for algo, entry in summary["best"].items():
        print(f"\n{display_names.get(algo, algo)}:")
        print(f"  Solver seed: {entry['random_seed']}")
        for key, value in entry["params"].items():
            print(f"  {key}: {value}")

    _print_strategy_guide(n, m)


if __name__ == "__main__":
    main()
