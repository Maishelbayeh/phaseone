"""
Hybrid Binary Social Group Optimization + Genetic Algorithm for MAX-SAT / CNF.

Improving phase follows a gbest-guided BSGO-style update on continuous auxiliaries,
sigmoid stochastic binarization, and strict improvement acceptance per particle.
Evolution applies tournament selection, two-point crossover, mutation, elite local
search, and stagnation-triggered diversity injection.
"""

from __future__ import annotations

import math
import random
import time
from copy import copy
from dataclasses import dataclass
from typing import List, Optional, Tuple

from evaluator import compute_solution_merit, is_formula_fully_satisfied
from utils import CNFFormula, TruthAssignment


@dataclass(frozen=True)
class HybridBsgoGaResult:
    """Same shape as other solvers so the GUI and batch runner can treat it uniformly."""

    best_assignment: Tuple[bool, ...]
    best_merit: int
    total_clauses: int
    fully_satisfied: bool
    iterations_used: int
    restart_count: int
    runtime_seconds: float
    merit_history: Tuple[int, ...]
    runtime_history: Tuple[float, ...]


def _random_binary_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    return [rng.choice((False, True)) for _ in range(num_variables)]


def _v_shape_transfer(velocity: float) -> float:
    return abs(math.tanh(velocity))


def _accept_with_temperature(delta: int, temperature: float, rng: random.Random) -> bool:
    if delta >= 0:
        return True
    if temperature <= 1e-12:
        return False
    return rng.random() < math.exp(max(-60.0, delta / temperature))


def _annealed_single_flip(
    formula: CNFFormula,
    assignment: TruthAssignment,
    current_merit: int,
    temperature: float,
    rng: random.Random,
    *,
    trials: int,
) -> Tuple[TruthAssignment, int]:
    candidate = copy(assignment)
    candidate_merit = current_merit
    for _ in range(max(1, trials)):
        bit_index = rng.randrange(formula.num_variables)
        candidate[bit_index] = not candidate[bit_index]
        neighbor_merit = compute_solution_merit(formula, candidate)
        if _accept_with_temperature(neighbor_merit - candidate_merit, temperature, rng):
            candidate_merit = neighbor_merit
        else:
            candidate[bit_index] = not candidate[bit_index]
    return candidate, candidate_merit


def _local_search_flip(
    formula: CNFFormula, assignment: TruthAssignment, rng: random.Random
) -> Tuple[TruthAssignment, int]:
    current_merit = compute_solution_merit(formula, assignment)
    best_merit = current_merit
    best_index = -1

    indices = list(range(formula.num_variables))
    rng.shuffle(indices)
    for index in indices:
        assignment[index] = not assignment[index]
        candidate_merit = compute_solution_merit(formula, assignment)
        if candidate_merit > best_merit:
            best_merit = candidate_merit
            best_index = index
        assignment[index] = not assignment[index]

    if best_index >= 0:
        assignment[best_index] = not assignment[best_index]
    return assignment, best_merit


def hybrid_bsgo_ga_search(
    formula: CNFFormula,
    *,
    population_size: int = 60,
    max_iterations: int = 250,
    crossover_rate: float = 0.92,
    mutation_rate: Optional[float] = None,
    c_coefficient: float = 0.72,
    w_inertia: float = 0.72,
    c_cognitive: float = 1.35,
    c_social: float = 1.75,
    tournament_size: int = 3,
    stagnation_limit: int = 30,
    local_search_elite: bool = True,
    annealing_temperature: float = 2.4,
    annealing_cooling: float = 0.994,
    annealing_trials: int = 2,
    reheat_multiplier: float = 1.4,
    random_seed: Optional[int] = None,
) -> HybridBsgoGaResult:
    """
    Run the hybrid BSGO-GA on a CNF formula (any clause length).

    Args:
        formula: CNF instance.
        population_size: Swarm / population count.
        max_iterations: Outer generations (improving + evolution per generation).
        crossover_rate: Probability of crossover when breeding.
        mutation_rate: Per-bit flip probability after crossover.
        c_coefficient: Compatibility knob kept for older configs.
        w_inertia: Inertia weight for the PSO-like improving phase.
        c_cognitive: Pull toward each particle's personal best.
        c_social: Pull toward the global best.
        tournament_size: Parent selection pressure.
        stagnation_limit: Generations without improvement before re-diversifying.
        local_search_elite: Whether to refine the current elite every generation.
        annealing_temperature: Initial temperature for SA-style worsening acceptance.
        annealing_cooling: Multiplicative cooling factor.
        annealing_trials: Number of SA-style random flips when refining offspring.
        reheat_multiplier: Temperature boost after stagnation.
        random_seed: Optional RNG seed.

    Returns:
        Best binary assignment found plus histories for plotting.
    """
    if population_size < 2:
        raise ValueError("population_size must be at least 2.")
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1.")
    if not (0.0 <= crossover_rate <= 1.0):
        raise ValueError("crossover_rate must be in [0, 1].")
    if not (0.0 < c_coefficient <= 2.0):
        raise ValueError("c_coefficient should be in (0, 2] for stability.")
    if not (0.0 < w_inertia <= 2.0):
        raise ValueError("w_inertia should be in (0, 2].")
    if c_cognitive < 0.0:
        raise ValueError("c_cognitive must be non-negative.")
    if c_social < 0.0:
        raise ValueError("c_social must be non-negative.")
    if tournament_size < 2:
        raise ValueError("tournament_size must be at least 2.")
    if stagnation_limit < 1:
        raise ValueError("stagnation_limit must be at least 1.")

    rng = random.Random(random_seed)
    n = formula.num_variables
    m = formula.num_clauses
    if mutation_rate is None:
        mutation_rate = min(0.04, 2.0 / max(n, 1))
    if not (0.0 <= mutation_rate <= 1.0):
        raise ValueError("mutation_rate must be in [0, 1].")
    if annealing_temperature <= 0.0:
        raise ValueError("annealing_temperature must be > 0.")
    if not (0.0 < annealing_cooling < 1.0):
        raise ValueError("annealing_cooling must be in (0, 1).")
    if annealing_trials < 1:
        raise ValueError("annealing_trials must be at least 1.")
    if reheat_multiplier < 1.0:
        raise ValueError("reheat_multiplier must be at least 1.")

    population: List[TruthAssignment] = [
        _random_binary_assignment(n, rng) for _ in range(population_size)
    ]
    fitness: List[int] = [compute_solution_merit(formula, individual) for individual in population]
    velocities: List[List[float]] = [
        [rng.uniform(-2.0, 2.0) for _ in range(n)] for _ in range(population_size)
    ]
    personal_best = [copy(individual) for individual in population]
    personal_best_fitness = list(fitness)

    best_index = max(range(population_size), key=lambda index: fitness[index])
    global_best: TruthAssignment = copy(population[best_index])
    global_best_merit = fitness[best_index]

    merit_history: List[int] = [global_best_merit]
    runtime_history: List[float] = [0.0]
    start_time = time.perf_counter()
    restarts_used = 1
    temperature = annealing_temperature

    def record() -> None:
        merit_history.append(global_best_merit)
        runtime_history.append(time.perf_counter() - start_time)

    def tournament_select() -> TruthAssignment:
        contestants = rng.sample(range(population_size), min(tournament_size, population_size))
        winner = max(contestants, key=lambda index: fitness[index])
        return copy(population[winner])

    def two_point_crossover(parent_a: TruthAssignment, parent_b: TruthAssignment) -> TruthAssignment:
        if n < 3:
            return copy(parent_a)
        cut1, cut2 = sorted(rng.sample(range(1, n), 2))
        return parent_a[:cut1] + parent_b[cut1:cut2] + parent_a[cut2:]

    stagnation_counter = 0
    previous_best = global_best_merit
    generations_run = 0
    for generation in range(max_iterations):
        generations_run = generation + 1

        # --- Phase 1: BSGO improving step ---
        for particle_index in range(population_size):
            particle = population[particle_index]
            old_bits = copy(particle)
            old_merit = fitness[particle_index]
            for dimension in range(n):
                current_value = 1.0 if particle[dimension] else 0.0
                pbest_value = 1.0 if personal_best[particle_index][dimension] else 0.0
                gbest_value = 1.0 if global_best[dimension] else 0.0
                velocities[particle_index][dimension] = (
                    w_inertia * velocities[particle_index][dimension]
                    + c_coefficient * c_cognitive * rng.random() * (pbest_value - current_value)
                    + c_social * rng.random() * (gbest_value - current_value)
                )
                if rng.random() < _v_shape_transfer(velocities[particle_index][dimension]):
                    particle[dimension] = not particle[dimension]

            candidate_merit = compute_solution_merit(formula, particle)
            if not _accept_with_temperature(candidate_merit - old_merit, temperature, rng):
                population[particle_index] = old_bits
                particle = population[particle_index]
                candidate_merit = old_merit

            fitness[particle_index] = candidate_merit
            if candidate_merit > personal_best_fitness[particle_index]:
                personal_best[particle_index] = copy(particle)
                personal_best_fitness[particle_index] = candidate_merit
            if candidate_merit > global_best_merit:
                global_best = copy(particle)
                global_best_merit = candidate_merit

        # --- Phase 2: GA evolution ---
        ranked_indices = sorted(range(population_size), key=lambda index: fitness[index], reverse=True)
        new_population: List[TruthAssignment] = []
        new_fitness: List[int] = []
        new_velocities: List[List[float]] = []

        elite = copy(population[ranked_indices[0]])
        elite_merit = fitness[ranked_indices[0]]
        if local_search_elite:
            elite, elite_merit = _local_search_flip(formula, elite, rng)
        else:
            elite, elite_merit = _annealed_single_flip(
                formula,
                elite,
                elite_merit,
                temperature,
                rng,
                trials=annealing_trials,
            )
        if elite_merit > global_best_merit:
            global_best = copy(elite)
            global_best_merit = elite_merit
        new_population.append(elite)
        new_fitness.append(elite_merit)
        new_velocities.append([rng.uniform(-1.0, 1.0) for _ in range(n)])
        if population_size > 1:
            runner_up = copy(population[ranked_indices[1]])
            runner_up_merit = fitness[ranked_indices[1]]
            runner_up, runner_up_merit = _annealed_single_flip(
                formula,
                runner_up,
                runner_up_merit,
                temperature,
                rng,
                trials=annealing_trials,
            )
            new_population.append(runner_up)
            new_fitness.append(runner_up_merit)
            new_velocities.append([rng.uniform(-1.0, 1.0) for _ in range(n)])

        while len(new_population) < population_size:
            parent_a = tournament_select()
            parent_b = tournament_select()
            if rng.random() < crossover_rate and n >= 3:
                child = two_point_crossover(parent_a, parent_b)
            else:
                child = copy(parent_a if rng.random() < 0.5 else parent_b)

            for bit_index in range(n):
                if rng.random() < mutation_rate:
                    child[bit_index] = not child[bit_index]
            child_merit = compute_solution_merit(formula, child)
            child, child_merit = _annealed_single_flip(
                formula,
                child,
                child_merit,
                temperature,
                rng,
                trials=annealing_trials,
            )
            new_population.append(child)
            new_fitness.append(child_merit)
            new_velocities.append([rng.uniform(-1.0, 1.0) for _ in range(n)])

        population = new_population[:population_size]
        fitness = new_fitness[:population_size]
        velocities = new_velocities[:population_size]

        best_index = max(range(population_size), key=lambda index: fitness[index])
        if fitness[best_index] > global_best_merit:
            global_best = copy(population[best_index])
            global_best_merit = fitness[best_index]
            stagnation_counter = 0
        else:
            stagnation_counter += 1

        for particle_index in range(population_size):
            if fitness[particle_index] > personal_best_fitness[particle_index]:
                personal_best[particle_index] = copy(population[particle_index])
                personal_best_fitness[particle_index] = fitness[particle_index]

        record()
        if global_best_merit >= m and m > 0:
            break

        if global_best_merit > previous_best:
            previous_best = global_best_merit
            stagnation_counter = 0

        if stagnation_counter >= stagnation_limit:
            stagnation_counter = 0
            restarts_used += 1
            sorted_by_fitness = sorted(range(population_size), key=lambda index: fitness[index])
            cutoff = population_size // 2
            for index in sorted_by_fitness[:cutoff]:
                population[index] = _random_binary_assignment(n, rng)
                fitness[index] = compute_solution_merit(formula, population[index])
                velocities[index] = [rng.uniform(-2.0, 2.0) for _ in range(n)]
                personal_best[index] = copy(population[index])
                personal_best_fitness[index] = fitness[index]
            temperature = max(annealing_temperature, temperature * reheat_multiplier)
        temperature = max(0.05, temperature * annealing_cooling)

    elapsed = time.perf_counter() - start_time
    return HybridBsgoGaResult(
        best_assignment=tuple(global_best),
        best_merit=global_best_merit,
        total_clauses=m,
        fully_satisfied=is_formula_fully_satisfied(formula, global_best),
        iterations_used=generations_run,
        restart_count=restarts_used,
        runtime_seconds=elapsed,
        merit_history=tuple(merit_history),
        runtime_history=tuple(runtime_history),
    )
