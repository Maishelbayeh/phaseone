from __future__ import annotations
import math

import random
import time
from copy import copy
from typing import Any, List, Mapping, Optional, Tuple

from evaluator import compute_solution_merit
from sa_enhanced import AssignmentState, FormulaCache
from simulated_annealing import simulated_annealing_search
from utils import CNFFormula, TruthAssignment

from .base_solver import BaseSolver, SolverResult, normalize_result


def _random_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    return [rng.choice((False, True)) for _ in range(num_variables)]


def _accept_with_temperature(delta: int, temperature: float, rng: random.Random) -> bool:
    if delta >= 0:
        return True
    if temperature <= 1e-12:
        return False
    return rng.random() < math.exp(max(-60.0, delta / temperature))


def _pick_unsatisfied_clause_index(
    state: AssignmentState, rng: random.Random, *, max_attempts: int = 30
) -> Optional[int]:
    m = state.cache.formula.num_clauses
    if m <= 0:
        return None
    for _ in range(max_attempts):
        idx = rng.randrange(m)
        if state.clause_true_counts[idx] == 0:
            return idx
    return None


def _pick_clause_variable(
    state: AssignmentState, clause_index: int, rng: random.Random
) -> int:
    variables = list(state.cache.clause_variables[clause_index])
    rng.shuffle(variables)
    best_variable = variables[0]
    best_delta = -10**9
    for variable in variables:
        delta, _, break_count = state.flip_stats(variable)
        score = delta * 1000 - break_count
        if score > best_delta:
            best_delta = score
            best_variable = variable
    return best_variable


def _annealed_refine_state(
    state: AssignmentState,
    temperature: float,
    rng: random.Random,
    *,
    trials: int,
    unsatisfied_focus_probability: float,
) -> int:
    n = state.cache.formula.num_variables
    for _ in range(max(1, trials)):
        use_focus = rng.random() < unsatisfied_focus_probability
        if use_focus:
            clause_index = _pick_unsatisfied_clause_index(state, rng)
            if clause_index is not None:
                variable_index = _pick_clause_variable(state, clause_index, rng)
            else:
                variable_index = rng.randrange(n)
        else:
            variable_index = rng.randrange(n)
        delta, _, _ = state.flip_stats(variable_index)
        if _accept_with_temperature(delta, temperature, rng):
            state.apply_flip(variable_index)
    return state.merit


def _walksat_refine_state(
    state: AssignmentState,
    rng: random.Random,
    *,
    steps: int,
    noise_probability: float,
) -> int:
    if steps <= 0:
        return state.merit
    m = state.cache.formula.num_clauses
    if m <= 0:
        return state.merit
    for _ in range(steps):
        if state.merit >= m:
            break
        clause_index = _pick_unsatisfied_clause_index(state, rng)
        if clause_index is None:
            break
        variables = list(state.cache.clause_variables[clause_index])
        if not variables:
            continue
        if rng.random() < noise_probability:
            variable_index = rng.choice(variables)
            state.apply_flip(variable_index)
            continue
        best_variable = variables[0]
        best_score = -10**9
        rng.shuffle(variables)
        for variable in variables:
            delta, _, break_count = state.flip_stats(variable)
            score = delta * 1000 - break_count
            if score > best_score:
                best_score = score
                best_variable = variable
        state.apply_flip(best_variable)
    return state.merit


class GeneticAlgorithmSolver(BaseSolver):
    algorithm_name = "Genetic Algorithm"

    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        population_size = int(config.get("population_size", 56))
        max_generations = int(config.get("max_generations", 220))
        crossover_rate = float(config.get("crossover_rate", 0.88))
        base_mutation_rate = float(
            config.get("mutation_rate", min(0.04, 2.0 / max(formula.num_variables, 1)))
        )
        elite_count = int(config.get("elite_count", 2))
        random_seed: Optional[int] = config.get("random_seed", None)
        crossover_mode = str(config.get("crossover_mode", "uniform")).strip().lower()
        tournament_size = int(config.get("tournament_size", 3))
        local_search_every = int(config.get("local_search_every", 5))
        local_search_steps = int(config.get("local_search_steps", max(12, formula.num_variables // 10)))
        local_search_noise_probability = float(config.get("local_search_noise_probability", 0.15))
        annealing_temperature = float(config.get("annealing_temperature", 2.2))
        annealing_cooling = float(config.get("annealing_cooling", 0.992))
        annealing_trials = int(config.get("annealing_trials", 2))
        annealing_unsatisfied_focus_probability = float(
            config.get("annealing_unsatisfied_focus_probability", 0.7)
        )
        intensification_threshold = float(config.get("intensification_threshold", 0.99))
        intensification_focus_probability = float(config.get("intensification_focus_probability", 0.9))
        intensification_local_steps_multiplier = float(
            config.get("intensification_local_steps_multiplier", 2.5)
        )
        intensification_noise_probability = float(config.get("intensification_noise_probability", 0.08))
        intensification_temperature_scale = float(config.get("intensification_temperature_scale", 0.6))
        stagnation_limit = int(config.get("stagnation_limit", 24))
        reheat_multiplier = float(config.get("reheat_multiplier", 1.5))
        initialization_strategy = str(config.get("initialization_strategy", "polarity")).strip().lower()
        polarity_bias_strength = float(config.get("polarity_bias_strength", 0.7))
        multi_bit_mutation_probability = float(config.get("multi_bit_mutation_probability", 0.02))
        max_multi_bit_mutation_size = int(config.get("max_multi_bit_mutation_size", 3))
        stagnation_multi_bit_boost = float(config.get("stagnation_multi_bit_boost", 0.12))
        finish_attempts = int(config.get("finish_attempts", 6))
        finish_perturbation = int(config.get("finish_perturbation", max(2, formula.num_variables // 25)))
        finish_local_search_steps = int(
            config.get("finish_local_search_steps", max(80, int(0.5 * formula.num_variables)))
        )
        finish_noise_probability = float(config.get("finish_noise_probability", 0.12))
        finish_temperature_scale = float(config.get("finish_temperature_scale", 0.4))
        finish_annealing_trials = int(config.get("finish_annealing_trials", 12))
        finish_with_enhanced_sa = bool(config.get("finish_with_enhanced_sa", False))
        finish_sa_max_iterations = int(config.get("finish_sa_max_iterations", min(1500, 8 * formula.num_variables)))

        if population_size < 4:
            raise ValueError("population_size must be at least 4.")
        if max_generations < 1:
            raise ValueError("max_generations must be at least 1.")
        if not (0.0 <= crossover_rate <= 1.0):
            raise ValueError("crossover_rate must be in [0, 1].")
        if not (0.0 <= base_mutation_rate <= 1.0):
            raise ValueError("mutation_rate must be in [0, 1].")
        if elite_count < 1 or elite_count >= population_size:
            raise ValueError("elite_count must be in [1, population_size - 1].")
        if crossover_mode not in {"one_point", "two_point", "uniform"}:
            raise ValueError("crossover_mode must be one_point, two_point, or uniform.")
        if tournament_size < 2:
            raise ValueError("tournament_size must be at least 2.")
        if local_search_every < 1:
            raise ValueError("local_search_every must be at least 1.")
        if local_search_steps < 0:
            raise ValueError("local_search_steps must be at least 0.")
        if not (0.0 <= local_search_noise_probability <= 1.0):
            raise ValueError("local_search_noise_probability must be in [0, 1].")
        if annealing_temperature <= 0.0:
            raise ValueError("annealing_temperature must be > 0.")
        if not (0.0 < annealing_cooling < 1.0):
            raise ValueError("annealing_cooling must be in (0, 1).")
        if annealing_trials < 1:
            raise ValueError("annealing_trials must be at least 1.")
        if not (0.0 <= annealing_unsatisfied_focus_probability <= 1.0):
            raise ValueError("annealing_unsatisfied_focus_probability must be in [0, 1].")
        if not (0.0 <= intensification_threshold <= 1.0):
            raise ValueError("intensification_threshold must be in [0, 1].")
        if not (0.0 <= intensification_focus_probability <= 1.0):
            raise ValueError("intensification_focus_probability must be in [0, 1].")
        if intensification_local_steps_multiplier <= 0.0:
            raise ValueError("intensification_local_steps_multiplier must be > 0.")
        if not (0.0 <= intensification_noise_probability <= 1.0):
            raise ValueError("intensification_noise_probability must be in [0, 1].")
        if intensification_temperature_scale <= 0.0:
            raise ValueError("intensification_temperature_scale must be > 0.")
        if stagnation_limit < 1:
            raise ValueError("stagnation_limit must be at least 1.")
        if reheat_multiplier < 1.0:
            raise ValueError("reheat_multiplier must be at least 1.")
        if initialization_strategy not in {"random", "polarity"}:
            raise ValueError("initialization_strategy must be random or polarity.")
        if not (0.0 <= polarity_bias_strength <= 1.0):
            raise ValueError("polarity_bias_strength must be in [0, 1].")
        if not (0.0 <= multi_bit_mutation_probability <= 1.0):
            raise ValueError("multi_bit_mutation_probability must be in [0, 1].")
        if max_multi_bit_mutation_size < 1:
            raise ValueError("max_multi_bit_mutation_size must be at least 1.")
        if stagnation_multi_bit_boost < 0.0:
            raise ValueError("stagnation_multi_bit_boost must be >= 0.")
        if finish_attempts < 0:
            raise ValueError("finish_attempts must be at least 0.")
        if finish_perturbation < 0:
            raise ValueError("finish_perturbation must be at least 0.")
        if finish_local_search_steps < 0:
            raise ValueError("finish_local_search_steps must be at least 0.")
        if not (0.0 <= finish_noise_probability <= 1.0):
            raise ValueError("finish_noise_probability must be in [0, 1].")
        if finish_temperature_scale <= 0.0:
            raise ValueError("finish_temperature_scale must be > 0.")
        if finish_annealing_trials < 0:
            raise ValueError("finish_annealing_trials must be at least 0.")
        if finish_sa_max_iterations < 0:
            raise ValueError("finish_sa_max_iterations must be at least 0.")

        rng = random.Random(random_seed)
        n = formula.num_variables
        m = formula.num_clauses
        start_time = time.perf_counter()
        cache = FormulaCache.build(formula)

        def make_initial() -> TruthAssignment:
            if initialization_strategy == "random":
                return [rng.choice((False, True)) for _ in range(n)]
            assignment: TruthAssignment = []
            for variable_index in range(n):
                prefer_true = cache.positive_occurrences[variable_index] >= cache.negative_occurrences[variable_index]
                if rng.random() < polarity_bias_strength:
                    assignment.append(bool(prefer_true))
                else:
                    assignment.append(rng.choice((False, True)))
            return assignment

        population: List[TruthAssignment] = [make_initial() for _ in range(population_size)]
        fitness = [compute_solution_merit(formula, individual) for individual in population]

        best_idx = max(range(population_size), key=lambda i: fitness[i])
        best_assignment = copy(population[best_idx])
        best_fitness = fitness[best_idx]
        best_history = [best_fitness]
        runtime_history = [0.0]
        temperature = annealing_temperature
        stagnation_counter = 0

        def tournament_select() -> TruthAssignment:
            candidates = [rng.randrange(population_size) for _ in range(tournament_size)]
            winner = max(candidates, key=lambda idx: fitness[idx])
            return copy(population[winner])

        def crossover(parent_a: TruthAssignment, parent_b: TruthAssignment) -> TruthAssignment:
            if n < 2 or rng.random() >= crossover_rate:
                return copy(parent_a if rng.random() < 0.5 else parent_b)
            if crossover_mode == "uniform":
                child: TruthAssignment = []
                for bit_index in range(n):
                    child.append(parent_a[bit_index] if rng.random() < 0.5 else parent_b[bit_index])
                return child
            if crossover_mode == "one_point" or n < 3:
                cut = rng.randrange(1, n)
                return parent_a[:cut] + parent_b[cut:]
            cut1 = rng.randrange(1, n - 1)
            cut2 = rng.randrange(cut1 + 1, n)
            return parent_a[:cut1] + parent_b[cut1:cut2] + parent_a[cut2:]

        generations_used = 0
        for generation in range(max_generations):
            generations_used = generation + 1
            is_intensifying = (
                m > 0
                and best_fitness < m
                and (float(best_fitness) / float(m)) >= intensification_threshold
            )
            effective_temperature = (
                max(0.05, temperature * intensification_temperature_scale)
                if is_intensifying
                else temperature
            )
            effective_anneal_focus = (
                intensification_focus_probability
                if is_intensifying
                else annealing_unsatisfied_focus_probability
            )
            effective_local_steps = (
                int(round(local_search_steps * intensification_local_steps_multiplier))
                if is_intensifying
                else local_search_steps
            )
            effective_local_noise = (
                intensification_noise_probability if is_intensifying else local_search_noise_probability
            )

            ranked_indices = sorted(range(population_size), key=lambda i: fitness[i], reverse=True)
            next_population: List[TruthAssignment] = []
            next_fitness: List[int] = []

            for elite_rank, idx in enumerate(ranked_indices[:elite_count]):
                elite = copy(population[idx])
                elite_fitness = fitness[idx]
                elite_state = AssignmentState.from_assignment(cache, elite)
                if (
                    (elite_rank == 0 and (generation + 1) % local_search_every == 0)
                    or (is_intensifying and elite_rank < min(2, elite_count))
                ):
                    _walksat_refine_state(
                        elite_state,
                        rng,
                        steps=effective_local_steps,
                        noise_probability=effective_local_noise,
                    )
                else:
                    _annealed_refine_state(
                        elite_state,
                        effective_temperature,
                        rng,
                        trials=annealing_trials,
                        unsatisfied_focus_probability=effective_anneal_focus,
                    )
                elite = elite_state.assignment
                elite_fitness = elite_state.merit
                next_population.append(elite)
                next_fitness.append(elite_fitness)

            adaptive_mutation_rate = min(
                0.2,
                base_mutation_rate
                * (1.0 + 1.5 * min(stagnation_counter, stagnation_limit) / stagnation_limit),
            )

            while len(next_population) < population_size:
                parent_a = tournament_select()
                parent_b = tournament_select()
                child = crossover(parent_a, parent_b)
                child_state = AssignmentState.from_assignment(cache, child)
                for bit_idx in range(n):
                    if rng.random() < adaptive_mutation_rate:
                        child_state.apply_flip(bit_idx)
                multi_prob = min(
                    1.0,
                    multi_bit_mutation_probability
                    + stagnation_multi_bit_boost * min(stagnation_counter, stagnation_limit) / stagnation_limit,
                )
                if rng.random() < multi_prob:
                    flips = max(2, min(max_multi_bit_mutation_size, n))
                    for bit_idx in rng.sample(range(n), flips):
                        child_state.apply_flip(bit_idx)
                _annealed_refine_state(
                    child_state,
                    effective_temperature,
                    rng,
                    trials=annealing_trials,
                    unsatisfied_focus_probability=effective_anneal_focus,
                )
                next_population.append(child_state.assignment)
                next_fitness.append(child_state.merit)

            population = next_population[:population_size]
            fitness = next_fitness[:population_size]

            iteration_best_idx = max(range(population_size), key=lambda i: fitness[i])
            iteration_best = fitness[iteration_best_idx]
            if iteration_best > best_fitness:
                best_fitness = iteration_best
                best_assignment = copy(population[iteration_best_idx])
                stagnation_counter = 0
            else:
                stagnation_counter += 1

            if stagnation_counter >= stagnation_limit:
                ranked_indices = sorted(range(population_size), key=lambda i: fitness[i], reverse=True)
                replace_count = max(1, population_size // 4)
                for idx in ranked_indices[-replace_count:]:
                    population[idx] = make_initial()
                    fitness[idx] = compute_solution_merit(formula, population[idx])
                temperature = max(annealing_temperature, temperature * reheat_multiplier)
                stagnation_counter = 0
                iteration_best_idx = max(range(population_size), key=lambda i: fitness[i])
                iteration_best = fitness[iteration_best_idx]
                if iteration_best > best_fitness:
                    best_fitness = iteration_best
                    best_assignment = copy(population[iteration_best_idx])

            best_history.append(best_fitness)
            runtime_history.append(time.perf_counter() - start_time)
            if best_fitness >= m and m > 0:
                break
            temperature = max(0.05, temperature * annealing_cooling)

        finish_used = 0
        if m > 0 and best_fitness < m and finish_attempts > 0:
            finish_temperature = max(0.05, annealing_temperature * finish_temperature_scale)
            for attempt in range(finish_attempts):
                finish_used = attempt + 1
                state = AssignmentState.from_assignment(cache, best_assignment)
                if finish_perturbation > 0 and n > 0:
                    flips = max(1, min(n, finish_perturbation))
                    for variable_index in rng.sample(range(n), flips):
                        state.apply_flip(variable_index)
                _walksat_refine_state(
                    state,
                    rng,
                    steps=finish_local_search_steps,
                    noise_probability=finish_noise_probability,
                )
                if finish_annealing_trials > 0 and state.merit < m:
                    _annealed_refine_state(
                        state,
                        finish_temperature,
                        rng,
                        trials=finish_annealing_trials,
                        unsatisfied_focus_probability=max(0.9, annealing_unsatisfied_focus_probability),
                    )
                if state.merit > best_fitness:
                    best_fitness = state.merit
                    best_assignment = copy(state.assignment)
                    best_history.append(best_fitness)
                    runtime_history.append(time.perf_counter() - start_time)
                if best_fitness >= m:
                    break

        finish_sa_used = False
        if (
            m > 0
            and best_fitness < m
            and finish_with_enhanced_sa
            and finish_sa_max_iterations > 0
        ):
            sa_result = simulated_annealing_search(
                formula,
                mode="enhanced",
                max_iterations=finish_sa_max_iterations,
                random_seed=rng.randrange(1, 1_000_000_000),
                restart_count=1,
                elite_restart_transfer=False,
                initial_assignment=best_assignment,
            )
            finish_sa_used = True
            if int(sa_result.best_merit) > best_fitness:
                best_fitness = int(sa_result.best_merit)
                best_assignment = list(sa_result.best_assignment)
                best_history.append(best_fitness)
                runtime_history.append(time.perf_counter() - start_time)

        return normalize_result(
            algorithm_name=self.algorithm_name,
            assignment=best_assignment,
            runtime_seconds=time.perf_counter() - start_time,
            iterations_used=generations_used,
            best_history=best_history,
            runtime_history=runtime_history,
            parameter_summary={
                "population_size": population_size,
                "max_generations": max_generations,
                "crossover_rate": crossover_rate,
                "mutation_rate": base_mutation_rate,
                "elite_count": elite_count,
                "crossover_mode": crossover_mode,
                "tournament_size": tournament_size,
                "local_search_every": local_search_every,
                "local_search_steps": local_search_steps,
                "local_search_noise_probability": local_search_noise_probability,
                "annealing_temperature": annealing_temperature,
                "annealing_cooling": annealing_cooling,
                "annealing_trials": annealing_trials,
                "annealing_unsatisfied_focus_probability": annealing_unsatisfied_focus_probability,
                "intensification_threshold": intensification_threshold,
                "intensification_focus_probability": intensification_focus_probability,
                "intensification_local_steps_multiplier": intensification_local_steps_multiplier,
                "intensification_noise_probability": intensification_noise_probability,
                "intensification_temperature_scale": intensification_temperature_scale,
                "stagnation_limit": stagnation_limit,
                "reheat_multiplier": reheat_multiplier,
                "initialization_strategy": initialization_strategy,
                "polarity_bias_strength": polarity_bias_strength,
                "multi_bit_mutation_probability": multi_bit_mutation_probability,
                "max_multi_bit_mutation_size": max_multi_bit_mutation_size,
                "stagnation_multi_bit_boost": stagnation_multi_bit_boost,
                "finish_attempts": finish_attempts,
                "finish_used": finish_used,
                "finish_perturbation": finish_perturbation,
                "finish_local_search_steps": finish_local_search_steps,
                "finish_noise_probability": finish_noise_probability,
                "finish_temperature_scale": finish_temperature_scale,
                "finish_annealing_trials": finish_annealing_trials,
                "finish_with_enhanced_sa": finish_with_enhanced_sa,
                "finish_sa_max_iterations": finish_sa_max_iterations,
                "finish_sa_used": finish_sa_used,
                "random_seed": random_seed,
                "method": "ga_with_annealed_refinement",
            },
            formula=formula,
        )
