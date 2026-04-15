"""
Tabu search local solver for Max-SAT optimization on 3-CNF formulas.
"""

from __future__ import annotations

import random
import time
from copy import copy
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from evaluator import compute_solution_merit
from utils import CNFFormula, TruthAssignment


@dataclass(frozen=True)
class TabuSearchResult:
    """Outcome of one tabu search run on a formula."""

    best_assignment: Tuple[bool, ...]
    best_merit: int
    total_clauses: int
    fully_satisfied: bool
    iterations_used: int
    restart_count: int
    runtime_seconds: float
    merit_history: Tuple[int, ...]


def _random_truth_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    return [rng.choice((False, True)) for _ in range(num_variables)]


def tabu_search_solve(
    formula: CNFFormula,
    *,
    max_iterations: int,
    tabu_tenure: int,
    random_seed: Optional[int] = None,
) -> TabuSearchResult:
    """
    Tabu search with one-variable neighborhoods and aspiration criterion.

    A move is tabu if its variable is currently in the tabu list, unless it
    beats the global best merit (aspiration).
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1.")
    if tabu_tenure < 1:
        raise ValueError("tabu_tenure must be at least 1.")

    rng = random.Random(random_seed)
    start_time = time.perf_counter()

    current_assignment = _random_truth_assignment(formula.num_variables, rng)
    current_merit = compute_solution_merit(formula, current_assignment)
    best_assignment = copy(current_assignment)
    best_merit = current_merit

    tabu_until_iteration: Dict[int, int] = {}
    history: List[int] = [best_merit]
    iterations_used = 0

    for iteration in range(1, max_iterations + 1):
        selected_variable_index: Optional[int] = None
        selected_neighbor_merit = -1

        for variable_index in range(formula.num_variables):
            current_assignment[variable_index] = not current_assignment[variable_index]
            merit_if_flipped = compute_solution_merit(formula, current_assignment)
            current_assignment[variable_index] = not current_assignment[variable_index]

            tabu_expiration = tabu_until_iteration.get(variable_index, 0)
            is_tabu = iteration <= tabu_expiration
            is_aspired = merit_if_flipped > best_merit
            if is_tabu and not is_aspired:
                continue

            if merit_if_flipped > selected_neighbor_merit:
                selected_neighbor_merit = merit_if_flipped
                selected_variable_index = variable_index
            elif merit_if_flipped == selected_neighbor_merit and selected_variable_index is not None:
                if rng.random() < 0.5:
                    selected_variable_index = variable_index

        if selected_variable_index is None:
            break

        current_assignment[selected_variable_index] = not current_assignment[selected_variable_index]
        current_merit = selected_neighbor_merit
        tabu_until_iteration[selected_variable_index] = iteration + tabu_tenure

        if current_merit > best_merit:
            best_merit = current_merit
            best_assignment = copy(current_assignment)

        iterations_used = iteration
        history.append(best_merit)
        if best_merit == formula.num_clauses:
            break

    elapsed = time.perf_counter() - start_time
    return TabuSearchResult(
        best_assignment=tuple(best_assignment),
        best_merit=best_merit,
        total_clauses=formula.num_clauses,
        fully_satisfied=best_merit == formula.num_clauses,
        iterations_used=iterations_used,
        restart_count=1,
        runtime_seconds=elapsed,
        merit_history=tuple(history),
    )
