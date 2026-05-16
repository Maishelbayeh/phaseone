"""
Hill climbing solver for 3-SAT / Max-SAT style search.

The idea is simple:
- Start from a random assignment
- Keep flipping one variable if it improves the score
- If stuck, restart from a new random assignment
"""

from __future__ import annotations

import random
import time
from copy import copy
from dataclasses import dataclass
from typing import List, Optional, Tuple

from evaluator import compute_solution_merit, is_formula_fully_satisfied
from utils import CNFFormula, TruthAssignment


@dataclass(frozen=True)
class HillClimbingResult:
    """Final result and run stats for one hill-climbing solve."""

    best_assignment: Tuple[bool, ...]
    """Best assignment we found (stored as tuple so it cannot be mutated later)."""

    best_merit: int
    """How many clauses are satisfied by best_assignment."""

    total_clauses: int
    """Total number of clauses in the formula."""

    fully_satisfied: bool
    """True when all clauses are satisfied."""

    iterations_used: int
    """Total improving moves across all restarts."""

    restart_count: int
    """How many starts were attempted (first run counts as one)."""

    runtime_seconds: float
    """Wall-clock runtime in seconds."""

    merit_history: Tuple[int, ...]
    """Best-so-far merit after each recorded step (used for convergence plots)."""

    runtime_history: Tuple[float, ...]
    """Cumulative runtime aligned with merit_history (seconds)."""


def _random_truth_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    """Build a random True/False assignment for all variables."""
    return [rng.choice((False, True)) for _ in range(num_variables)]


def _record_global_best(
    assignment: TruthAssignment,
    merit: int,
    global_best_merit: int,
    global_best_assignment: Optional[TruthAssignment],
) -> Tuple[int, TruthAssignment]:
    """Update the global best snapshot if the current assignment is better."""
    if merit > global_best_merit:
        return merit, copy(assignment)
    if global_best_assignment is None:
        return merit, copy(assignment)
    return global_best_merit, global_best_assignment


def _merit_after_flip(
    formula: CNFFormula,
    assignment: TruthAssignment,
    flip_variable_index: int,
) -> int:
    """Try one flip, score it, then flip back to restore original state."""
    assignment[flip_variable_index] = not assignment[flip_variable_index]
    merit = compute_solution_merit(formula, assignment)
    assignment[flip_variable_index] = not assignment[flip_variable_index]
    return merit


def _select_best_improving_neighbor(
    formula: CNFFormula,
    assignment: TruthAssignment,
    current_merit: int,
    rng: random.Random,
) -> Optional[int]:
    """
    Pick one of the best improving one-bit moves.

    Returns:
        Variable index to flip, or None if no improving move exists.
    """
    best_merit_after_flip = current_merit
    candidate_indices: List[int] = []

    for variable_index in range(formula.num_variables):
        merit_if_flipped = _merit_after_flip(formula, assignment, variable_index)
        if merit_if_flipped > best_merit_after_flip:
            best_merit_after_flip = merit_if_flipped
            candidate_indices = [variable_index]
        elif merit_if_flipped == best_merit_after_flip and merit_if_flipped > current_merit:
            # Same improvement as current best: keep it as another candidate.
            candidate_indices.append(variable_index)

    if not candidate_indices:
        return None

    return rng.choice(candidate_indices)


def hill_climb_with_random_restarts(
    formula: CNFFormula,
    *,
    max_iterations_per_restart: int,
    max_random_restarts: int,
    random_seed: Optional[int] = None,
) -> HillClimbingResult:
    """
    Run greedy hill climbing with optional random restarts.

    Each restart does:
    - Start from a random assignment
    - Repeatedly choose a best improving flip
    - Stop when solved, stuck, or iteration budget is reached

    Args:
        formula: 3-CNF formula to optimize.
        max_iterations_per_restart: Move limit per restart.
        max_random_restarts: Number of random starting points.
        random_seed: Optional seed for reproducible random choices.

    Returns:
        Best solution found plus metadata (runtime, iterations, history, ...).
    """
    if max_iterations_per_restart < 1:
        raise ValueError("max_iterations_per_restart must be at least 1.")
    if max_random_restarts < 1:
        raise ValueError("max_random_restarts must be at least 1.")

    rng = random.Random(random_seed)
    start_time = time.perf_counter()

    history: List[int] = []
    runtime_history: List[float] = []
    global_best_merit = -1
    global_best_assignment: Optional[TruthAssignment] = None
    total_iterations = 0
    restarts_started = 0

    for _restart_index in range(max_random_restarts):
        restarts_started += 1
        current_assignment = _random_truth_assignment(formula.num_variables, rng)
        current_merit = compute_solution_merit(formula, current_assignment)

        global_best_merit, global_best_assignment = _record_global_best(
            current_assignment, current_merit, global_best_merit, global_best_assignment
        )
        history.append(global_best_merit)
        runtime_history.append(time.perf_counter() - start_time)

        if is_formula_fully_satisfied(formula, current_assignment):
            break

        inner_iterations = 0
        while inner_iterations < max_iterations_per_restart:
            flip_index = _select_best_improving_neighbor(
                formula, current_assignment, current_merit, rng
            )

            if flip_index is None:
                break

            current_assignment[flip_index] = not current_assignment[flip_index]
            current_merit = compute_solution_merit(formula, current_assignment)
            inner_iterations += 1
            total_iterations += 1

            global_best_merit, global_best_assignment = _record_global_best(
                current_assignment, current_merit, global_best_merit, global_best_assignment
            )
            history.append(global_best_merit)
            runtime_history.append(time.perf_counter() - start_time)

            if current_merit == formula.num_clauses:
                break

        if global_best_merit == formula.num_clauses:
            break

    elapsed = time.perf_counter() - start_time

    assert global_best_assignment is not None

    return HillClimbingResult(
        best_assignment=tuple(global_best_assignment),
        best_merit=global_best_merit,
        total_clauses=formula.num_clauses,
        fully_satisfied=global_best_merit == formula.num_clauses,
        iterations_used=total_iterations,
        restart_count=restarts_started,
        runtime_seconds=elapsed,
        merit_history=tuple(history),
        runtime_history=tuple(runtime_history),
    )
