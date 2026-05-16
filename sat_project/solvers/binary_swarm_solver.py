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


def _v_shape_transfer(velocity: float) -> float:
    return abs(math.tanh(velocity))


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


def _pick_clause_variable(state: AssignmentState, clause_index: int, rng: random.Random) -> int:
    variables = list(state.cache.clause_variables[clause_index])
    rng.shuffle(variables)
    best_variable = variables[0]
    best_score = -10**9
    for variable in variables:
        delta, _, break_count = state.flip_stats(variable)
        score = delta * 1000 - break_count
        if score > best_score:
            best_score = score
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
            state.apply_flip(rng.choice(variables))
            continue
        rng.shuffle(variables)
        best_variable = variables[0]
        best_score = -10**9
        for variable in variables:
            delta, _, break_count = state.flip_stats(variable)
            score = delta * 1000 - break_count
            if score > best_score:
                best_score = score
                best_variable = variable
        state.apply_flip(best_variable)
    return state.merit


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


def _refine_assignment(
    cache: FormulaCache,
    start_assignment: TruthAssignment,
    start_merit: int,
    *,
    rng: random.Random,
    temperature: float,
    anneal_trials: int,
    focus_probability: float,
    walksat_steps: int,
    walksat_noise_probability: float,
) -> Tuple[TruthAssignment, int]:
    state = AssignmentState.from_assignment(cache, start_assignment)
    state.merit = start_merit
    if walksat_steps > 0:
        _walksat_refine_state(
            state,
            rng,
            steps=walksat_steps,
            noise_probability=walksat_noise_probability,
        )
    _annealed_refine_state(
        state,
        temperature,
        rng,
        trials=anneal_trials,
        unsatisfied_focus_probability=focus_probability,
    )
    return state.assignment, state.merit


def _perturb_assignment(
    assignment: TruthAssignment, *, flip_count: int, rng: random.Random
) -> TruthAssignment:
    candidate = copy(assignment)
    if not candidate:
        return candidate
    actual_flip_count = min(len(candidate), max(1, flip_count))
    for index in rng.sample(range(len(candidate)), actual_flip_count):
        candidate[index] = not candidate[index]
    return candidate


class BinarySwarmSolver(BaseSolver):
    algorithm_name = "Binary Swarm (BSGO)"

    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        n = formula.num_variables
        m = formula.num_clauses

        population_size = int(config.get("population_size", 56))
        max_iterations = int(config.get("max_iterations", max(280, 2 * n)))
        # Keep backward compatibility with the previous single c_parameter knob.
        w_inertia_start = float(
            config.get("w_inertia_start", config.get("w_inertia", config.get("c_parameter", 0.9)))
        )
        w_inertia_end = float(config.get("w_inertia_end", 0.4))
        c_cognitive = float(config.get("c_cognitive", 1.35))
        c_social = float(config.get("c_social", 2.05))
        velocity_clamp = float(config.get("velocity_clamp", 4.0))
        local_search_every = int(config.get("local_search_every", 10))
        local_search_top_k = int(config.get("local_search_top_k", 2))
        stagnation_limit = int(config.get("stagnation_limit", 35))
        max_restarts = int(config.get("max_restarts", 2))
        annealing_temperature = float(config.get("annealing_temperature", 2.2))
        annealing_cooling = float(config.get("annealing_cooling", 0.995))
        annealing_trials = int(config.get("annealing_trials", 3))
        sa_refine_iterations = int(config.get("sa_refine_iterations", min(240, max(80, 2 * n))))
        reheat_multiplier = float(config.get("reheat_multiplier", 1.5))
        diversify_fraction = float(config.get("diversify_fraction", 0.3))
        refine_focus_probability = float(config.get("refine_focus_probability", 0.85))
        refine_walksat_steps = int(config.get("refine_walksat_steps", max(40, n // 6)))
        refine_walksat_noise_probability = float(config.get("refine_walksat_noise_probability", 0.12))
        intensification_threshold = float(config.get("intensification_threshold", 0.99))
        intensify_local_search_every = int(config.get("intensify_local_search_every", 2))
        intensify_top_k = int(config.get("intensify_top_k", 3))
        intensify_sa_scale = float(config.get("intensify_sa_scale", 2.0))
        finish_attempts = int(config.get("finish_attempts", 6))
        finish_perturbation = int(config.get("finish_perturbation", max(2, n // 25)))
        finish_walksat_steps = int(config.get("finish_walksat_steps", max(120, int(0.6 * n))))
        finish_walksat_noise_probability = float(config.get("finish_walksat_noise_probability", 0.12))
        finish_anneal_trials = int(config.get("finish_anneal_trials", 18))
        finish_temperature_scale = float(config.get("finish_temperature_scale", 0.4))
        finish_with_enhanced_sa = bool(config.get("finish_with_enhanced_sa", True))
        finish_sa_max_iterations = int(config.get("finish_sa_max_iterations", min(1800, 10 * n)))
        random_seed: Optional[int] = config.get("random_seed", None)

        if population_size < 2:
            raise ValueError("population_size must be at least 2.")
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1.")
        if not (0.0 < w_inertia_start <= 2.5):
            raise ValueError("w_inertia_start must be in (0, 2.5].")
        if not (0.0 < w_inertia_end <= 2.5):
            raise ValueError("w_inertia_end must be in (0, 2.5].")
        if c_cognitive < 0.0:
            raise ValueError("c_cognitive must be non-negative.")
        if c_social < 0.0:
            raise ValueError("c_social must be non-negative.")
        if velocity_clamp <= 0.0:
            raise ValueError("velocity_clamp must be > 0.")
        if local_search_every < 1:
            raise ValueError("local_search_every must be at least 1.")
        if local_search_top_k < 1:
            raise ValueError("local_search_top_k must be at least 1.")
        if stagnation_limit < 1:
            raise ValueError("stagnation_limit must be at least 1.")
        if max_restarts < 0:
            raise ValueError("max_restarts must be at least 0.")
        if annealing_temperature <= 0.0:
            raise ValueError("annealing_temperature must be > 0.")
        if not (0.0 < annealing_cooling < 1.0):
            raise ValueError("annealing_cooling must be in (0, 1).")
        if annealing_trials < 1:
            raise ValueError("annealing_trials must be at least 1.")
        if sa_refine_iterations < 1:
            raise ValueError("sa_refine_iterations must be at least 1.")
        if reheat_multiplier < 1.0:
            raise ValueError("reheat_multiplier must be at least 1.")
        if not (0.0 < diversify_fraction < 1.0):
            raise ValueError("diversify_fraction must be in (0, 1).")
        if not (0.0 <= refine_focus_probability <= 1.0):
            raise ValueError("refine_focus_probability must be in [0, 1].")
        if refine_walksat_steps < 0:
            raise ValueError("refine_walksat_steps must be at least 0.")
        if not (0.0 <= refine_walksat_noise_probability <= 1.0):
            raise ValueError("refine_walksat_noise_probability must be in [0, 1].")
        if not (0.0 <= intensification_threshold <= 1.0):
            raise ValueError("intensification_threshold must be in [0, 1].")
        if intensify_local_search_every < 1:
            raise ValueError("intensify_local_search_every must be at least 1.")
        if intensify_top_k < 1:
            raise ValueError("intensify_top_k must be at least 1.")
        if intensify_sa_scale <= 0.0:
            raise ValueError("intensify_sa_scale must be > 0.")
        if finish_attempts < 0:
            raise ValueError("finish_attempts must be at least 0.")
        if finish_perturbation < 0:
            raise ValueError("finish_perturbation must be at least 0.")
        if finish_walksat_steps < 0:
            raise ValueError("finish_walksat_steps must be at least 0.")
        if not (0.0 <= finish_walksat_noise_probability <= 1.0):
            raise ValueError("finish_walksat_noise_probability must be in [0, 1].")
        if finish_anneal_trials < 0:
            raise ValueError("finish_anneal_trials must be at least 0.")
        if finish_temperature_scale <= 0.0:
            raise ValueError("finish_temperature_scale must be > 0.")
        if finish_sa_max_iterations < 0:
            raise ValueError("finish_sa_max_iterations must be at least 0.")

        rng = random.Random(random_seed)
        start_time = time.perf_counter()
        cache = FormulaCache.build(formula)

        best_history: List[int] = []
        runtime_history: List[float] = []
        global_best_assignment: Optional[TruthAssignment] = None
        global_best_merit = -1
        total_iterations = 0
        restarts_used = 0

        def record() -> None:
            best_history.append(global_best_merit)
            runtime_history.append(time.perf_counter() - start_time)

        for restart_index in range(max_restarts + 1):
            restarts_used = restart_index + 1
            temperature = annealing_temperature
            population: List[TruthAssignment] = []
            if global_best_assignment is not None:
                population.append(copy(global_best_assignment))
                guided_count = min(population_size - 1, max(1, population_size // 5))
                guided_flips = max(1, n // 12)
                for _ in range(guided_count):
                    population.append(
                        _perturb_assignment(global_best_assignment, flip_count=guided_flips, rng=rng)
                    )
            while len(population) < population_size:
                population.append(_random_assignment(n, rng))

            velocities: List[List[float]] = [
                [rng.uniform(-1.5, 1.5) for _ in range(n)] for _ in range(population_size)
            ]
            fitness = [compute_solution_merit(formula, particle) for particle in population]
            personal_best = [copy(particle) for particle in population]
            personal_best_fitness = list(fitness)

            best_index = max(range(population_size), key=lambda index: fitness[index])
            restart_global_best = copy(population[best_index])
            restart_global_best_merit = fitness[best_index]

            if restart_global_best_merit > global_best_merit:
                global_best_merit = restart_global_best_merit
                global_best_assignment = copy(restart_global_best)
            record()

            stagnation_counter = 0
            previous_best = global_best_merit

            for iteration_index in range(max_iterations):
                total_iterations += 1
                progress = iteration_index / max(1, max_iterations - 1)
                inertia = w_inertia_start + (w_inertia_end - w_inertia_start) * progress
                social_best = global_best_assignment if global_best_assignment is not None else restart_global_best
                is_intensifying = (
                    m > 0
                    and global_best_merit < m
                    and (float(global_best_merit) / float(m)) >= intensification_threshold
                )

                for particle_index in range(population_size):
                    particle = population[particle_index]
                    old_particle = copy(particle)
                    old_merit = fitness[particle_index]
                    for dimension in range(n):
                        r1 = rng.random()
                        r2 = rng.random()
                        current_value = 1.0 if particle[dimension] else 0.0
                        pbest_value = 1.0 if personal_best[particle_index][dimension] else 0.0
                        gbest_value = 1.0 if social_best[dimension] else 0.0
                        velocities[particle_index][dimension] = (
                            inertia * velocities[particle_index][dimension]
                            + c_cognitive * r1 * (pbest_value - current_value)
                            + c_social * r2 * (gbest_value - current_value)
                        )
                        velocities[particle_index][dimension] = max(
                            -velocity_clamp,
                            min(velocity_clamp, velocities[particle_index][dimension]),
                        )
                        if rng.random() < _v_shape_transfer(velocities[particle_index][dimension]):
                            particle[dimension] = not particle[dimension]

                    updated_merit = compute_solution_merit(formula, particle)
                    if not _accept_with_temperature(updated_merit - old_merit, temperature, rng):
                        population[particle_index] = old_particle
                        particle = population[particle_index]
                        updated_merit = old_merit
                    fitness[particle_index] = updated_merit

                    if updated_merit > personal_best_fitness[particle_index]:
                        personal_best[particle_index] = copy(particle)
                        personal_best_fitness[particle_index] = updated_merit

                    if updated_merit > restart_global_best_merit:
                        restart_global_best = copy(particle)
                        restart_global_best_merit = updated_merit
                        if updated_merit > global_best_merit:
                            global_best_merit = updated_merit
                            global_best_assignment = copy(restart_global_best)

                if (iteration_index + 1) % (intensify_local_search_every if is_intensifying else local_search_every) == 0:
                    ranked_indices = sorted(
                        range(population_size), key=lambda index: fitness[index], reverse=True
                    )
                    elite_budget = intensify_top_k if is_intensifying else local_search_top_k
                    elite_indices = ranked_indices[: min(elite_budget, population_size)]
                    for elite_rank, index in enumerate(elite_indices):
                        refined_assignment = copy(population[index])
                        refined_merit = fitness[index]
                        effective_sa_trials = (
                            int(round(annealing_trials * intensify_sa_scale))
                            if is_intensifying
                            else annealing_trials
                        )
                        effective_sa_iterations = (
                            int(round(sa_refine_iterations * intensify_sa_scale))
                            if is_intensifying
                            else sa_refine_iterations
                        )
                        effective_walksat_steps = (
                            int(round(refine_walksat_steps * intensify_sa_scale))
                            if is_intensifying
                            else refine_walksat_steps
                        )
                        refined_assignment, refined_merit = _refine_assignment(
                            cache,
                            refined_assignment,
                            refined_merit,
                            rng=rng,
                            temperature=max(0.5, temperature),
                            anneal_trials=min(5 * n, max(1, effective_sa_trials + effective_sa_iterations)),
                            focus_probability=refine_focus_probability,
                            walksat_steps=effective_walksat_steps if elite_rank == 0 else max(0, effective_walksat_steps // 2),
                            walksat_noise_probability=refine_walksat_noise_probability,
                        )
                        if refined_merit > fitness[index]:
                            population[index] = refined_assignment
                            fitness[index] = refined_merit
                            if refined_merit > personal_best_fitness[index]:
                                personal_best[index] = copy(refined_assignment)
                                personal_best_fitness[index] = refined_merit
                        if refined_merit > restart_global_best_merit:
                            restart_global_best = copy(refined_assignment)
                            restart_global_best_merit = refined_merit
                        if refined_merit > global_best_merit:
                            global_best_merit = refined_merit
                            global_best_assignment = copy(refined_assignment)

                    worst_index = min(range(population_size), key=lambda index: fitness[index])
                    kicked_assignment, kicked_merit = _annealed_single_flip(
                        formula,
                        copy(restart_global_best),
                        restart_global_best_merit,
                        max(0.5, temperature),
                        rng,
                        trials=annealing_trials,
                    )
                    if kicked_merit > fitness[worst_index]:
                        population[worst_index] = kicked_assignment
                        fitness[worst_index] = kicked_merit
                        if kicked_merit > personal_best_fitness[worst_index]:
                            personal_best[worst_index] = copy(kicked_assignment)
                            personal_best_fitness[worst_index] = kicked_merit

                record()
                if global_best_merit >= m and m > 0:
                    break

                if global_best_merit > previous_best:
                    stagnation_counter = 0
                    previous_best = global_best_merit
                else:
                    stagnation_counter += 1

                if stagnation_counter == max(1, stagnation_limit // 2):
                    temperature = max(annealing_temperature, temperature * reheat_multiplier)
                    diversify_count = max(1, int(round(population_size * diversify_fraction)))
                    weakest_indices = sorted(
                        range(population_size), key=lambda index: fitness[index]
                    )[:diversify_count]
                    anchor = global_best_assignment if global_best_assignment is not None else restart_global_best
                    guided_count = max(1, diversify_count // 2)
                    guided_flips = max(1, n // 10)
                    for offset, index in enumerate(weakest_indices):
                        if offset < guided_count:
                            population[index] = _perturb_assignment(
                                anchor, flip_count=guided_flips, rng=rng
                            )
                        else:
                            population[index] = _random_assignment(n, rng)
                        velocities[index] = [rng.uniform(-1.0, 1.0) for _ in range(n)]
                        fitness[index] = compute_solution_merit(formula, population[index])
                        personal_best[index] = copy(population[index])
                        personal_best_fitness[index] = fitness[index]
                        if fitness[index] > restart_global_best_merit:
                            restart_global_best = copy(population[index])
                            restart_global_best_merit = fitness[index]
                        if fitness[index] > global_best_merit:
                            global_best_merit = fitness[index]
                            global_best_assignment = copy(population[index])

                if stagnation_counter >= stagnation_limit:
                    break
                temperature = max(0.05, temperature * annealing_cooling)

            if global_best_merit >= m and m > 0:
                break

        finish_used = 0
        finish_sa_used = False
        if global_best_assignment is not None and m > 0 and global_best_merit < m and finish_attempts > 0:
            finish_temperature = max(0.5, annealing_temperature * finish_temperature_scale)
            for attempt in range(finish_attempts):
                finish_used = attempt + 1
                candidate = copy(global_best_assignment)
                if finish_perturbation > 0 and n > 0:
                    candidate = _perturb_assignment(candidate, flip_count=finish_perturbation, rng=rng)
                candidate_merit = compute_solution_merit(formula, candidate)
                candidate, candidate_merit = _refine_assignment(
                    cache,
                    candidate,
                    candidate_merit,
                    rng=rng,
                    temperature=finish_temperature,
                    anneal_trials=finish_anneal_trials,
                    focus_probability=max(0.9, refine_focus_probability),
                    walksat_steps=finish_walksat_steps,
                    walksat_noise_probability=finish_walksat_noise_probability,
                )
                if candidate_merit > global_best_merit:
                    global_best_merit = candidate_merit
                    global_best_assignment = copy(candidate)
                    record()
                if global_best_merit >= m:
                    break

        if (
            global_best_assignment is not None
            and m > 0
            and global_best_merit < m
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
                initial_assignment=global_best_assignment,
            )
            finish_sa_used = True
            if int(sa_result.best_merit) > global_best_merit:
                global_best_merit = int(sa_result.best_merit)
                global_best_assignment = list(sa_result.best_assignment)
                record()

        assert global_best_assignment is not None
        return normalize_result(
            algorithm_name=self.algorithm_name,
            assignment=global_best_assignment,
            runtime_seconds=time.perf_counter() - start_time,
            iterations_used=total_iterations,
            best_history=best_history,
            runtime_history=runtime_history,
            parameter_summary={
                "population_size": population_size,
                "max_iterations": max_iterations,
                "w_inertia": w_inertia_start,
                "w_inertia_start": w_inertia_start,
                "w_inertia_end": w_inertia_end,
                "c_parameter": w_inertia_start,
                "c_cognitive": c_cognitive,
                "c_social": c_social,
                "velocity_clamp": velocity_clamp,
                "local_search_every": local_search_every,
                "local_search_top_k": local_search_top_k,
                "stagnation_limit": stagnation_limit,
                "max_restarts": max_restarts,
                "annealing_temperature": annealing_temperature,
                "annealing_cooling": annealing_cooling,
                "annealing_trials": annealing_trials,
                "sa_refine_iterations": sa_refine_iterations,
                "reheat_multiplier": reheat_multiplier,
                "diversify_fraction": diversify_fraction,
                "refine_focus_probability": refine_focus_probability,
                "refine_walksat_steps": refine_walksat_steps,
                "refine_walksat_noise_probability": refine_walksat_noise_probability,
                "intensification_threshold": intensification_threshold,
                "intensify_local_search_every": intensify_local_search_every,
                "intensify_top_k": intensify_top_k,
                "intensify_sa_scale": intensify_sa_scale,
                "finish_attempts": finish_attempts,
                "finish_used": finish_used,
                "finish_perturbation": finish_perturbation,
                "finish_walksat_steps": finish_walksat_steps,
                "finish_walksat_noise_probability": finish_walksat_noise_probability,
                "finish_anneal_trials": finish_anneal_trials,
                "finish_temperature_scale": finish_temperature_scale,
                "finish_with_enhanced_sa": finish_with_enhanced_sa,
                "finish_sa_max_iterations": finish_sa_max_iterations,
                "finish_sa_used": finish_sa_used,
                "restarts_used": restarts_used,
                "random_seed": random_seed,
                "method": "binary_pso_adaptive_guided",
            },
            formula=formula,
        )
