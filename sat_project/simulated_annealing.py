"""
Simulated annealing local search for Max-SAT optimization on 3-CNF formulas.
"""

from __future__ import annotations

import math
import random
import time
from copy import copy
from dataclasses import dataclass
from typing import List, Optional, Tuple

from evaluator import compute_solution_merit
from utils import CNFFormula, TruthAssignment


@dataclass(frozen=True)
class SimulatedAnnealingResult:
    """Outcome of one simulated annealing run on a formula."""

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


def simulated_annealing_search(
    formula: CNFFormula,
    *,
    max_iterations: int,
    initial_temperature: float,
    cooling_rate: float,
    min_temperature: float,
    random_seed: Optional[int] = None,
) -> SimulatedAnnealingResult:
    """
    Simulated annealing using one-variable random neighbor moves.

    The solver always accepts improving moves, and may accept worsening moves
    according to the Boltzmann probability exp(delta / temperature).
    """
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1.")
    if initial_temperature <= 0.0:
        raise ValueError("initial_temperature must be > 0.")
    if cooling_rate <= 0.0 or cooling_rate >= 1.0:
        raise ValueError("cooling_rate must be in (0, 1).")
    if min_temperature <= 0.0:
        raise ValueError("min_temperature must be > 0.")
    if min_temperature >= initial_temperature:
        raise ValueError("min_temperature must be less than initial_temperature.")

    rng = random.Random(random_seed)
    start_time = time.perf_counter()

    current_assignment = _random_truth_assignment(formula.num_variables, rng)
    current_merit = compute_solution_merit(formula, current_assignment)

    best_assignment = copy(current_assignment)
    best_merit = current_merit
    temperature = initial_temperature

    history: List[int] = [best_merit]
    iterations_used = 0

    while iterations_used < max_iterations and temperature > min_temperature:
        flip_index = rng.randrange(formula.num_variables)
        current_assignment[flip_index] = not current_assignment[flip_index]
        neighbor_merit = compute_solution_merit(formula, current_assignment)

        delta_merit = neighbor_merit - current_merit
        should_accept = False
        if delta_merit >= 0:
            should_accept = True
        else:
            acceptance_probability = math.exp(delta_merit / max(temperature, 1e-12))
            if rng.random() < acceptance_probability:
                should_accept = True

        if should_accept:
            current_merit = neighbor_merit
            if current_merit > best_merit:
                best_merit = current_merit
                best_assignment = copy(current_assignment)
        else:
            current_assignment[flip_index] = not current_assignment[flip_index]

        iterations_used += 1
        history.append(best_merit)
        if best_merit == formula.num_clauses:
            break

        temperature *= cooling_rate

    elapsed = time.perf_counter() - start_time
    return SimulatedAnnealingResult(
        best_assignment=tuple(best_assignment),
        best_merit=best_merit,
        total_clauses=formula.num_clauses,
        fully_satisfied=best_merit == formula.num_clauses,
        iterations_used=iterations_used,
        restart_count=1,
        runtime_seconds=elapsed,
        merit_history=tuple(history),
    )
