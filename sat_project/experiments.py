"""
Batch experiment driver: grid over n and clause density, run hill climbing, save results.

Outputs machine-readable summaries under ``results/data/`` for plotting and reports.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence, Tuple

from evaluator import normalized_satisfaction_rate
from hill_climbing import HillClimbingResult, hill_climb_with_random_restarts
from sat_generator import compute_clause_count_from_density, generate_random_3sat
from utils import CNFFormula, TruthAssignment

# --- Experiment grid defaults (project specification) ---

DEFAULT_VARIABLE_COUNTS: Tuple[int, ...] = (
    50,
    100,
    150,
    200,
    250,
    300,
    350,
    400,
    450,
    500,
)

DEFAULT_CLAUSE_DENSITY_RATIOS: Tuple[float, ...] = (3.0, 4.3, 6.0)


@dataclass(frozen=True)
class SingleRunRecord:
    """One row of experimental results for a single formula and solver run."""

    num_variables: int
    clause_density_ratio: float
    num_clauses: int
    satisfied_clauses: int
    total_clauses: int
    fully_satisfied: bool
    satisfaction_rate: float
    iterations: int
    runtime_seconds: float
    random_seed: int
    restart_count: int
    best_assignment_repr: str


def _truth_assignment_to_json(assignment: Sequence[bool]) -> str:
    """Serialize assignment as JSON list of booleans for storage."""
    return json.dumps(list(bool(value) for value in assignment))


def run_single_experiment(
    num_variables: int,
    clause_density_ratio: float,
    *,
    generation_seed: int,
    solver_seed: int,
    max_iterations_per_restart: int,
    max_random_restarts: int,
) -> SingleRunRecord:
    """
    Generate one random 3-SAT instance and solve it with hill climbing.

    Args:
        num_variables: n
        clause_density_ratio: m/n target before rounding
        generation_seed: Seed for CNF generation (reproducible instances)
        solver_seed: Seed for stochastic search
        max_iterations_per_restart: Inner-loop iteration budget
        max_random_restarts: Random restart count for the solver
    """
    if num_variables < 3:
        raise ValueError("Experiments require num_variables >= 3 for valid 3-SAT.")

    num_clauses = compute_clause_count_from_density(num_variables, clause_density_ratio)
    formula: CNFFormula = generate_random_3sat(
        num_variables=num_variables,
        num_clauses=num_clauses,
        random_seed=generation_seed,
    )

    result: HillClimbingResult = hill_climb_with_random_restarts(
        formula,
        max_iterations_per_restart=max_iterations_per_restart,
        max_random_restarts=max_random_restarts,
        random_seed=solver_seed,
    )

    best_as_list: TruthAssignment = list(result.best_assignment)
    satisfaction_rate = normalized_satisfaction_rate(formula, best_as_list)

    return SingleRunRecord(
        num_variables=num_variables,
        clause_density_ratio=clause_density_ratio,
        num_clauses=num_clauses,
        satisfied_clauses=result.best_merit,
        total_clauses=result.total_clauses,
        fully_satisfied=result.fully_satisfied,
        satisfaction_rate=satisfaction_rate,
        iterations=result.iterations_used,
        runtime_seconds=result.runtime_seconds,
        random_seed=solver_seed,
        restart_count=result.restart_count,
        best_assignment_repr=_truth_assignment_to_json(result.best_assignment),
    )


def run_experiment_grid(
    *,
    variable_counts: Sequence[int] = DEFAULT_VARIABLE_COUNTS,
    density_ratios: Sequence[float] = DEFAULT_CLAUSE_DENSITY_RATIOS,
    base_seed: int = 42,
    max_iterations_per_restart: Optional[int] = None,
    max_random_restarts: int = 8,
    instances_per_cell: int = 1,
) -> List[SingleRunRecord]:
    """
    Execute the full project grid: every n, every ratio, optional repeats.

    generation_seed and solver_seed are derived deterministically from base_seed, n,
    ratio index, and instance repeat so runs are reproducible.

    Args:
        variable_counts: Values of n to sweep
        density_ratios: m/n ratios to sweep
        base_seed: Master seed for derivations
        max_iterations_per_restart: If None, scales mildly with n
        max_random_restarts: Random restarts per instance
        instances_per_cell: How many independent formulas per (n, ratio)

    Returns:
        List of records in row order (nested loops: n, ratio, instance).
    """
    records: List[SingleRunRecord] = []
    for num_variables in variable_counts:
        if num_variables < 3:
            continue

        for ratio_index, ratio in enumerate(density_ratios):
            for instance_index in range(instances_per_cell):
                derived = (
                    base_seed
                    + num_variables * 1_000_003
                    + ratio_index * 10_007
                    + instance_index * 100_009
                )
                generation_seed = derived
                solver_seed = derived + 50_000_017

                per_restart = max_iterations_per_restart
                if per_restart is None:
                    per_restart = max(400, 15 * num_variables)

                record = run_single_experiment(
                    num_variables=num_variables,
                    clause_density_ratio=ratio,
                    generation_seed=generation_seed,
                    solver_seed=solver_seed,
                    max_iterations_per_restart=per_restart,
                    max_random_restarts=max_random_restarts,
                )
                records.append(record)

    return records


def save_records_csv(records: Iterable[SingleRunRecord], file_path: Path) -> None:
    """Write experiment records as CSV with a header row."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(record) for record in records]
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with file_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_records_json(records: Iterable[SingleRunRecord], file_path: Path) -> None:
    """Write the same data as pretty-printed JSON (list of dicts)."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload: List[dict[str, Any]] = [asdict(record) for record in records]
    with file_path.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, indent=2)


def load_records_csv(file_path: Path) -> List[SingleRunRecord]:
    """Reload records from CSV (for plotting after the fact)."""
    with file_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        records: List[SingleRunRecord] = []
        for row in reader:
            records.append(
                SingleRunRecord(
                    num_variables=int(row["num_variables"]),
                    clause_density_ratio=float(row["clause_density_ratio"]),
                    num_clauses=int(row["num_clauses"]),
                    satisfied_clauses=int(row["satisfied_clauses"]),
                    total_clauses=int(row["total_clauses"]),
                    fully_satisfied=row["fully_satisfied"].strip().lower() in ("true", "1", "yes"),
                    satisfaction_rate=float(row["satisfaction_rate"]),
                    iterations=int(row["iterations"]),
                    runtime_seconds=float(row["runtime_seconds"]),
                    random_seed=int(row["random_seed"]),
                    restart_count=int(row["restart_count"]),
                    best_assignment_repr=row["best_assignment_repr"],
                )
            )
        return records
