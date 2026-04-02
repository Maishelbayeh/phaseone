"""
Hill climbing local search for Max-SAT style optimization on 3-CNF.

Stochastic hill climbing with optional random restarts mitigates local optima:
when no single-variable flip improves the merit, a new random assignment can
escape plateaus and suboptimal basins.
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
    """Outcome of running hill climbing (with optional restarts) on one formula."""

    best_assignment: Tuple[bool, ...]
    """Best truth assignment found (immutable tuple for safety)."""

    best_merit: int
    """Number of satisfied clauses under best_assignment."""

    total_clauses: int
    """m — for comparing best_merit to full satisfaction."""

    fully_satisfied: bool
    """True iff best_merit equals total_clauses."""

    iterations_used: int
    """Total hill-climbing iterations (neighbor sweeps) across all restarts."""

    restart_count: int
    """How many random restarts were actually started (including the first)."""

    runtime_seconds: float
    """Wall-clock search time using ``time.perf_counter``."""

    merit_history: Tuple[int, ...]
    """
    After each recorded step, the global best merit seen so far.

    The first entry is the merit of the initial random assignment before any
    neighbor move. Later entries include updates after each improving move
    cycle and after each new restart's initial evaluation.
    """


def _random_truth_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    """Create a uniformly random truth assignment."""
    return [rng.choice((False, True)) for _ in range(num_variables)]


def _record_global_best(
    assignment: TruthAssignment,
    merit: int,
    global_best_merit: int,
    global_best_assignment: Optional[TruthAssignment],
) -> Tuple[int, TruthAssignment]:
    """Update stored global best if this assignment is strictly better."""
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
    """Compute merit if assignment[flip_variable_index] were toggled (mutates briefly, then restores)."""
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
    Find variable indices whose flip strictly increases satisfied clause count.

    If several flips achieve the same best improvement, one index is chosen
    uniformly at random (stochastic tie-breaking adds diversity).

    Returns:
        Index to flip, or None if no strictly improving flip exists (local optimum).
    """
    best_merit_after_flip = current_merit
    candidate_indices: List[int] = []

    for variable_index in range(formula.num_variables):
        merit_if_flipped = _merit_after_flip(formula, assignment, variable_index)
        if merit_if_flipped > best_merit_after_flip:
            best_merit_after_flip = merit_if_flipped
            candidate_indices = [variable_index]
        elif merit_if_flipped == best_merit_after_flip and merit_if_flipped > current_merit:
            # Tie among improving moves at the same uplift — keep all tied winners.
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
    Greedy hill climbing: repeatedly move to a best improving one-bit neighbor.

    Stops an inner climb when:
        1. All clauses are satisfied, or
        2. No improving neighbor exists (local optimum), or
        3. max_iterations_per_restart inner iterations have been performed.

    If random restarts are enabled (max_random_restarts > 1), starts a new
    random assignment when the inner climb ends without full satisfaction,
    until global cap on restarts or a satisfying assignment is found.

    Args:
        formula: The 3-CNF instance.
        max_iterations_per_restart: Maximum neighbor-sweep cycles per restart.
        max_random_restarts: Number of independent random starting points
            (each executes a full inner climb until local stop).
        random_seed: Seed for reproducibility of the search stochasticity.

    Returns:
        HillClimbingResult with best assignment found and diagnostic traces.
    """
    if max_iterations_per_restart < 1:
        raise ValueError("max_iterations_per_restart must be at least 1.")
    if max_random_restarts < 1:
        raise ValueError("max_random_restarts must be at least 1.")

    rng = random.Random(random_seed)
    start_time = time.perf_counter()

    history: List[int] = []
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
    )
