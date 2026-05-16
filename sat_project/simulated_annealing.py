"""Simulated annealing solvers for MAX-SAT, including baseline and enhanced modes."""

from __future__ import annotations

import math
import random
import time
from copy import copy
from typing import Optional

from evaluator import compute_solution_merit
from sa_enhanced import SimulatedAnnealingResult, run_enhanced_simulated_annealing
from utils import CNFFormula, TruthAssignment


def _random_truth_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    return [rng.choice((False, True)) for _ in range(num_variables)]


def baseline_simulated_annealing_search(
    formula: CNFFormula,
    *,
    max_iterations: Optional[int] = None,
    initial_temperature: float = 12.0,
    cooling_rate: float = 0.997,
    min_temperature: float = 0.001,
    random_seed: Optional[int] = None,
    initial_assignment: Optional[TruthAssignment] = None,
) -> SimulatedAnnealingResult:
    """Original single-run SA behavior kept for baseline comparisons."""
    if max_iterations is None:
        max_iterations = max(3000, 50 * formula.num_variables)
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
    current_assignment = (
        [bool(value) for value in initial_assignment]
        if initial_assignment is not None
        else _random_truth_assignment(formula.num_variables, rng)
    )
    current_merit = compute_solution_merit(formula, current_assignment)

    best_assignment = copy(current_assignment)
    best_merit = current_merit
    temperature = initial_temperature

    history = [best_merit]
    runtime_history = [0.0]
    temperature_history = [temperature]
    accepted_move_history = ["start"]
    iterations_used = 0
    iteration_of_best = 0

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
            if delta_merit > 0:
                accepted_move_history.append("better")
            elif delta_merit == 0:
                accepted_move_history.append("equal")
            else:
                accepted_move_history.append("worse")
            if current_merit > best_merit:
                best_merit = current_merit
                best_assignment = copy(current_assignment)
                iteration_of_best = iterations_used + 1
        else:
            accepted_move_history.append("rejected")
            current_assignment[flip_index] = not current_assignment[flip_index]

        iterations_used += 1
        history.append(best_merit)
        runtime_history.append(time.perf_counter() - start_time)
        temperature_history.append(temperature)
        if best_merit == formula.num_clauses:
            break

        temperature *= cooling_rate

    elapsed = time.perf_counter() - start_time
    accepted_better = sum(1 for item in accepted_move_history if item == "better")
    accepted_equal = sum(1 for item in accepted_move_history if item == "equal")
    accepted_worse = sum(1 for item in accepted_move_history if item == "worse")
    iteration_of_full_satisfaction = iteration_of_best if best_merit == formula.num_clauses else None
    return SimulatedAnnealingResult(
        best_assignment=tuple(best_assignment),
        best_merit=best_merit,
        total_clauses=formula.num_clauses,
        fully_satisfied=best_merit == formula.num_clauses,
        iterations_used=iterations_used,
        restart_count=1,
        runtime_seconds=elapsed,
        merit_history=tuple(history),
        runtime_history=tuple(runtime_history),
        temperature_history=tuple(temperature_history),
        iteration_of_best=iteration_of_best,
        iteration_of_full_satisfaction=iteration_of_full_satisfaction,
        reheat_count=0,
        accepted_worse_moves=accepted_worse,
        accepted_better_moves=accepted_better,
        accepted_equal_moves=accepted_equal,
        number_of_unsatisfied_focused_moves=0,
        restart_summaries=(),
        final_satisfaction_rates=(
            0.0 if formula.num_clauses == 0 else best_merit / formula.num_clauses,
        ),
        accepted_move_history=tuple(accepted_move_history),
        mode="baseline",
        parameter_summary={
            "mode": "baseline",
            "max_iterations": max_iterations,
            "initial_temperature": initial_temperature,
            "cooling_rate": cooling_rate,
            "min_temperature": min_temperature,
            "random_seed": random_seed,
        },
    )


def simulated_annealing_search(
    formula: CNFFormula,
    *,
    max_iterations: Optional[int] = None,
    initial_temperature: float = 24.0,
    cooling_rate: float = 0.9975,
    min_temperature: float = 0.0005,
    random_seed: Optional[int] = None,
    mode: str = "enhanced",
    unsatisfied_focus_probability: float = 0.6,
    candidate_pool_size: Optional[int] = None,
    multi_bit_flip_probability: float = 0.04,
    max_multi_flip_size: int = 2,
    stagnation_multi_bit_boost: float = 0.15,
    stagnation_limit: Optional[int] = None,
    reheat_multiplier: float = 1.5,
    max_reheats: int = 4,
    adaptive_cooling: bool = True,
    adaptive_cooling_bonus: float = 0.0007,
    adaptive_cooling_penalty: float = 0.0025,
    restart_count: int = 2,
    restart_initialization_strategy: str = "polarity",
    elite_restart_transfer: bool = True,
    elite_restart_perturbation: Optional[int] = None,
    intensification_threshold: float = 0.98,
    intensification_focus_probability: float = 0.94,
    intensification_cooling_bonus: float = 0.0009,
    mini_hill_climb_steps: Optional[int] = None,
    polarity_bias_strength: float = 0.7,
    history_bias_strength: float = 0.72,
    initial_assignment: Optional[TruthAssignment] = None,
) -> SimulatedAnnealingResult:
    """
    Backward-compatible SA entry point.

    `mode="baseline"` preserves the original one-run random-neighbor implementation.
    `mode="enhanced"` enables focused moves, reheating, restart transfer, and
    late-stage intensification aimed at increasing the chance of full satisfaction.
    """
    if max_iterations is None:
        max_iterations = max(2500, 45 * formula.num_variables) if mode != "baseline" else max(3000, 50 * formula.num_variables)
    if candidate_pool_size is None:
        candidate_pool_size = max(10, formula.num_variables // 10)
    if stagnation_limit is None:
        stagnation_limit = max(30, int(0.7 * formula.num_variables))
    if elite_restart_perturbation is None:
        elite_restart_perturbation = max(2, formula.num_variables // 30)
    if mini_hill_climb_steps is None:
        mini_hill_climb_steps = max(10, int(0.33 * formula.num_variables))

    if mode == "baseline":
        return baseline_simulated_annealing_search(
            formula,
            max_iterations=max_iterations,
            initial_temperature=initial_temperature,
            cooling_rate=cooling_rate,
            min_temperature=min_temperature,
            random_seed=random_seed,
            initial_assignment=initial_assignment,
        )

    result = run_enhanced_simulated_annealing(
        formula,
        max_iterations=max_iterations,
        initial_temperature=initial_temperature,
        cooling_rate=cooling_rate,
        min_temperature=min_temperature,
        random_seed=random_seed,
        restart_count=restart_count,
        restart_initialization_strategy=restart_initialization_strategy,
        unsatisfied_focus_probability=unsatisfied_focus_probability,
        candidate_pool_size=candidate_pool_size,
        multi_bit_flip_probability=multi_bit_flip_probability,
        max_multi_flip_size=max_multi_flip_size,
        stagnation_multi_bit_boost=stagnation_multi_bit_boost,
        stagnation_limit=stagnation_limit,
        reheat_multiplier=reheat_multiplier,
        max_reheats=max_reheats,
        adaptive_cooling=adaptive_cooling,
        adaptive_cooling_bonus=adaptive_cooling_bonus,
        adaptive_cooling_penalty=adaptive_cooling_penalty,
        intensification_threshold=intensification_threshold,
        intensification_focus_probability=intensification_focus_probability,
        intensification_cooling_bonus=intensification_cooling_bonus,
        mini_hill_climb_steps=mini_hill_climb_steps,
        polarity_bias_strength=polarity_bias_strength,
        history_bias_strength=history_bias_strength,
        elite_restart_transfer=elite_restart_transfer,
        elite_restart_perturbation=elite_restart_perturbation,
        initial_assignment=initial_assignment,
    )
    parameter_summary = {
        "mode": "enhanced",
        "max_iterations": max_iterations,
        "initial_temperature": initial_temperature,
        "cooling_rate": cooling_rate,
        "min_temperature": min_temperature,
        "random_seed": random_seed,
        "restart_count": restart_count,
        "restart_initialization_strategy": restart_initialization_strategy,
        "elite_restart_transfer": elite_restart_transfer,
        "elite_restart_perturbation": elite_restart_perturbation,
        "unsatisfied_focus_probability": unsatisfied_focus_probability,
        "candidate_pool_size": candidate_pool_size,
        "multi_bit_flip_probability": multi_bit_flip_probability,
        "max_multi_flip_size": max_multi_flip_size,
        "stagnation_multi_bit_boost": stagnation_multi_bit_boost,
        "stagnation_limit": stagnation_limit,
        "reheat_multiplier": reheat_multiplier,
        "max_reheats": max_reheats,
        "adaptive_cooling": adaptive_cooling,
        "adaptive_cooling_bonus": adaptive_cooling_bonus,
        "adaptive_cooling_penalty": adaptive_cooling_penalty,
        "intensification_threshold": intensification_threshold,
        "intensification_focus_probability": intensification_focus_probability,
        "intensification_cooling_bonus": intensification_cooling_bonus,
        "mini_hill_climb_steps": mini_hill_climb_steps,
        "polarity_bias_strength": polarity_bias_strength,
        "history_bias_strength": history_bias_strength,
    }
    return SimulatedAnnealingResult(
        best_assignment=result.best_assignment,
        best_merit=result.best_merit,
        total_clauses=result.total_clauses,
        fully_satisfied=result.fully_satisfied,
        iterations_used=result.iterations_used,
        restart_count=result.restart_count,
        runtime_seconds=result.runtime_seconds,
        merit_history=result.merit_history,
        runtime_history=result.runtime_history,
        temperature_history=result.temperature_history,
        iteration_of_best=result.iteration_of_best,
        iteration_of_full_satisfaction=result.iteration_of_full_satisfaction,
        reheat_count=result.reheat_count,
        accepted_worse_moves=result.accepted_worse_moves,
        accepted_better_moves=result.accepted_better_moves,
        accepted_equal_moves=result.accepted_equal_moves,
        number_of_unsatisfied_focused_moves=result.number_of_unsatisfied_focused_moves,
        restart_summaries=result.restart_summaries,
        final_satisfaction_rates=result.final_satisfaction_rates,
        accepted_move_history=result.accepted_move_history,
        mode="enhanced",
        parameter_summary=parameter_summary,
    )
