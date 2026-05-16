from __future__ import annotations

import random
import time
from copy import copy
from typing import Any, List, Mapping, Optional

from evaluator import compute_solution_merit
from utils import CNFFormula, TruthAssignment

from .base_solver import BaseSolver, SolverResult, normalize_result
from .binary_swarm_solver import (
    _bounded_simulated_annealing_refine,
    _local_search_flip,
    _perturb_assignment,
    _random_assignment,
    _v_shape_transfer,
)


class SwarmSASolver(BaseSolver):
    algorithm_name = "Swarm-SA Hybrid"

    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        n = formula.num_variables
        m = formula.num_clauses

        population_size = int(config.get("population_size", 52))
        max_iterations = int(config.get("max_iterations", 220 if n <= 200 else 280))
        w_inertia_start = float(config.get("w_inertia_start", 0.92))
        w_inertia_end = float(config.get("w_inertia_end", 0.45))
        c_cognitive = float(config.get("c_cognitive", 1.25))
        c_social = float(config.get("c_social", 2.1))
        velocity_clamp = float(config.get("velocity_clamp", 4.0))
        local_search_every = int(config.get("local_search_every", 10))
        local_search_top_k = int(config.get("local_search_top_k", 1))
        sa_max_iterations = int(config.get("sa_max_iterations", min(450, max(180, 2 * n))))
        sa_patience = int(config.get("sa_patience", max(60, n // 2)))
        stagnation_limit = int(config.get("stagnation_limit", 24))
        max_restarts = int(config.get("max_restarts", 0))
        diversify_fraction = float(config.get("diversify_fraction", 0.25))
        lamarckian = bool(config.get("lamarckian", True))
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
        if sa_max_iterations < 1:
            raise ValueError("sa_max_iterations must be at least 1.")
        if sa_patience < 1:
            raise ValueError("sa_patience must be at least 1.")
        if stagnation_limit < 1:
            raise ValueError("stagnation_limit must be at least 1.")
        if max_restarts < 0:
            raise ValueError("max_restarts must be at least 0.")
        if not (0.0 < diversify_fraction < 1.0):
            raise ValueError("diversify_fraction must be in (0, 1).")

        rng = random.Random(random_seed)
        start_time = time.perf_counter()

        best_history: List[int] = []
        runtime_history: List[float] = []
        global_best_assignment: Optional[TruthAssignment] = None
        global_best_merit = -1
        total_iterations = 0
        restarts_used = 0
        refinement_calls = 0

        def record() -> None:
            best_history.append(global_best_merit)
            runtime_history.append(time.perf_counter() - start_time)

        for restart_index in range(max_restarts + 1):
            restarts_used = restart_index + 1
            population: List[TruthAssignment] = []
            if global_best_assignment is not None:
                population.append(copy(global_best_assignment))
                guided_count = min(population_size - 1, max(1, population_size // 5))
                for _ in range(guided_count):
                    population.append(
                        _perturb_assignment(
                            global_best_assignment, flip_count=max(1, n // 12), rng=rng
                        )
                    )
            while len(population) < population_size:
                population.append(_random_assignment(n, rng))

            velocities = [[rng.uniform(-1.5, 1.5) for _ in range(n)] for _ in range(population_size)]
            fitness = [compute_solution_merit(formula, particle) for particle in population]
            personal_best = [copy(particle) for particle in population]
            personal_best_fitness = list(fitness)

            best_index = max(range(population_size), key=lambda idx: fitness[idx])
            restart_best = copy(population[best_index])
            restart_best_merit = fitness[best_index]

            if restart_best_merit > global_best_merit:
                global_best_merit = restart_best_merit
                global_best_assignment = copy(restart_best)
            record()

            stagnation_counter = 0
            previous_best = global_best_merit

            for iteration_index in range(max_iterations):
                total_iterations += 1
                progress = iteration_index / max(1, max_iterations - 1)
                inertia = w_inertia_start + (w_inertia_end - w_inertia_start) * progress
                social_best = global_best_assignment if global_best_assignment is not None else restart_best

                for particle_index in range(population_size):
                    particle = population[particle_index]
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
                    fitness[particle_index] = updated_merit

                    if updated_merit > personal_best_fitness[particle_index]:
                        personal_best[particle_index] = copy(particle)
                        personal_best_fitness[particle_index] = updated_merit

                    if updated_merit > restart_best_merit:
                        restart_best = copy(particle)
                        restart_best_merit = updated_merit
                        if updated_merit > global_best_merit:
                            global_best_merit = updated_merit
                            global_best_assignment = copy(restart_best)

                if (iteration_index + 1) % local_search_every == 0:
                    ranked_indices = sorted(
                        range(population_size), key=lambda idx: fitness[idx], reverse=True
                    )
                    refine_count = 1 if stagnation_counter < max(1, local_search_every // 2) else local_search_top_k
                    elite_indices = ranked_indices[: min(refine_count, population_size)]
                    for elite_rank, idx in enumerate(elite_indices):
                        refined_assignment = copy(population[idx])
                        refined_merit = fitness[idx]
                        if elite_rank == 0:
                            refined_assignment, refined_merit = _local_search_flip(
                                formula, refined_assignment, rng
                            )
                        refined_assignment, refined_merit = _bounded_simulated_annealing_refine(
                            formula,
                            refined_assignment,
                            refined_merit,
                            max_iterations=min(
                                sa_max_iterations,
                                max(120, n + stagnation_counter * max(10, n // 5)),
                            ),
                            initial_temperature=2.6,
                            cooling_rate=0.995,
                            max_no_improve=sa_patience,
                            rng=rng,
                        )
                        refinement_calls += 1
                        if lamarckian and refined_merit > fitness[idx]:
                            population[idx] = refined_assignment
                            fitness[idx] = refined_merit
                            personal_best[idx] = copy(refined_assignment)
                            personal_best_fitness[idx] = max(personal_best_fitness[idx], refined_merit)
                        if refined_merit > restart_best_merit:
                            restart_best = copy(refined_assignment)
                            restart_best_merit = refined_merit
                        if refined_merit > global_best_merit:
                            global_best_merit = refined_merit
                            global_best_assignment = copy(refined_assignment)

                record()
                if global_best_merit >= m and m > 0:
                    break

                if global_best_merit > previous_best:
                    stagnation_counter = 0
                    previous_best = global_best_merit
                else:
                    stagnation_counter += 1

                if stagnation_counter >= stagnation_limit:
                    weakest_indices = sorted(range(population_size), key=lambda idx: fitness[idx])[
                        : max(1, int(round(population_size * diversify_fraction)))
                    ]
                    anchor = global_best_assignment if global_best_assignment is not None else restart_best
                    for offset, idx in enumerate(weakest_indices):
                        if offset < max(1, len(weakest_indices) // 2):
                            population[idx] = _perturb_assignment(
                                anchor, flip_count=max(1, n // 10), rng=rng
                            )
                        else:
                            population[idx] = _random_assignment(n, rng)
                        velocities[idx] = [rng.uniform(-1.0, 1.0) for _ in range(n)]
                        fitness[idx] = compute_solution_merit(formula, population[idx])
                        personal_best[idx] = copy(population[idx])
                        personal_best_fitness[idx] = fitness[idx]
                    stagnation_counter = 0

            if global_best_merit >= m and m > 0:
                break

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
                "w_inertia_start": w_inertia_start,
                "w_inertia_end": w_inertia_end,
                "c_cognitive": c_cognitive,
                "c_social": c_social,
                "velocity_clamp": velocity_clamp,
                "local_search_every": local_search_every,
                "local_search_top_k": local_search_top_k,
                "sa_max_iterations": sa_max_iterations,
                "sa_patience": sa_patience,
                "stagnation_limit": stagnation_limit,
                "max_restarts": max_restarts,
                "diversify_fraction": diversify_fraction,
                "lamarckian": lamarckian,
                "restarts_used": restarts_used,
                "refinement_calls": refinement_calls,
                "random_seed": random_seed,
                "method": "swarm_with_periodic_sa_refinement",
            },
            formula=formula,
        )
