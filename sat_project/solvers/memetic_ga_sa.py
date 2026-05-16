from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from simulated_annealing import simulated_annealing_search
from utils import CNFFormula, TruthAssignment

from .base_solver import BaseSolver, SolverResult, normalize_result


def _random_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    return [rng.choice((False, True)) for _ in range(num_variables)]


@dataclass(frozen=True)
class FormulaCache:
    formula: CNFFormula
    occurrences_by_variable: Tuple[Tuple[Tuple[int, bool], ...], ...]
    clause_variables: Tuple[Tuple[int, ...], ...]
    density_ratio: float

    @classmethod
    def build(cls, formula: CNFFormula) -> "FormulaCache":
        occurrences: List[List[Tuple[int, bool]]] = [[] for _ in range(formula.num_variables)]
        clause_variables: List[Tuple[int, ...]] = []
        for clause_index, clause in enumerate(formula.clauses):
            variables: List[int] = []
            for literal in clause:
                occurrences[literal.variable_index].append(
                    (clause_index, not literal.is_negated)
                )
                variables.append(literal.variable_index)
            clause_variables.append(tuple(dict.fromkeys(variables)))
        density = 0.0 if formula.num_variables == 0 else formula.num_clauses / formula.num_variables
        return cls(
            formula=formula,
            occurrences_by_variable=tuple(tuple(items) for items in occurrences),
            clause_variables=tuple(clause_variables),
            density_ratio=density,
        )


@dataclass
class AssignmentState:
    cache: FormulaCache
    assignment: TruthAssignment
    clause_true_counts: List[int]
    merit: int

    @classmethod
    def from_assignment(cls, cache: FormulaCache, assignment: Sequence[bool]) -> "AssignmentState":
        clause_true_counts = [0] * cache.formula.num_clauses
        merit = 0
        for clause_index, clause in enumerate(cache.formula.clauses):
            count = 0
            for literal in clause:
                if bool(assignment[literal.variable_index]) == (not literal.is_negated):
                    count += 1
            clause_true_counts[clause_index] = count
            if count > 0:
                merit += 1
        return cls(cache=cache, assignment=[bool(v) for v in assignment], clause_true_counts=clause_true_counts, merit=merit)

    def clone(self) -> "AssignmentState":
        return AssignmentState(
            cache=self.cache,
            assignment=list(self.assignment),
            clause_true_counts=list(self.clause_true_counts),
            merit=self.merit,
        )

    def unsatisfied_clause_indices(self) -> List[int]:
        return [
            clause_index
            for clause_index, true_count in enumerate(self.clause_true_counts)
            if true_count == 0
        ]

    def flip_delta(self, variable_index: int) -> int:
        current_value = self.assignment[variable_index]
        delta = 0
        for clause_index, literal_true_when_var_true in self.cache.occurrences_by_variable[variable_index]:
            before_true = current_value == literal_true_when_var_true
            after_true = (not current_value) == literal_true_when_var_true
            if before_true == after_true:
                continue
            old_count = self.clause_true_counts[clause_index]
            new_count = old_count + (1 if after_true else -1)
            if old_count == 0 and new_count > 0:
                delta += 1
            elif old_count > 0 and new_count == 0:
                delta -= 1
        return delta

    def apply_flip(self, variable_index: int) -> int:
        delta = self.flip_delta(variable_index)
        current_value = self.assignment[variable_index]
        for clause_index, literal_true_when_var_true in self.cache.occurrences_by_variable[variable_index]:
            before_true = current_value == literal_true_when_var_true
            after_true = (not current_value) == literal_true_when_var_true
            if before_true == after_true:
                continue
            self.clause_true_counts[clause_index] += 1 if after_true else -1
        self.assignment[variable_index] = not current_value
        self.merit += delta
        return delta


@dataclass
class AttemptOutcome:
    best_assignment: TruthAssignment
    best_merit: int
    best_history: List[int]
    runtime_history: List[float]
    iterations_used: int
    refinement_calls: int
    local_search_steps: int
    path_relink_calls: int
    path_relink_improvements: int


def _candidate_variables(
    state: AssignmentState,
    rng: random.Random,
    max_candidates: int,
) -> List[int]:
    variables: List[int] = []
    seen: set[int] = set()
    unsatisfied = state.unsatisfied_clause_indices()
    rng.shuffle(unsatisfied)
    for clause_index in unsatisfied:
        for variable_index in state.cache.clause_variables[clause_index]:
            if variable_index not in seen:
                seen.add(variable_index)
                variables.append(variable_index)
                if len(variables) >= max_candidates:
                    return variables
    if len(variables) < max_candidates:
        fallback = list(range(state.cache.formula.num_variables))
        rng.shuffle(fallback)
        for variable_index in fallback:
            if variable_index not in seen:
                variables.append(variable_index)
                if len(variables) >= max_candidates:
                    break
    return variables


def _incremental_local_search(
    state: AssignmentState,
    *,
    max_steps: int,
    max_candidates: int,
    rng: random.Random,
) -> Tuple[TruthAssignment, int, int]:
    working = state.clone()
    steps_used = 0
    for _ in range(max_steps):
        best_delta = 0
        best_variables: List[int] = []
        for variable_index in _candidate_variables(working, rng, max_candidates):
            delta = working.flip_delta(variable_index)
            if delta > best_delta:
                best_delta = delta
                best_variables = [variable_index]
            elif delta == best_delta and delta > 0:
                best_variables.append(variable_index)
        if best_delta <= 0 or not best_variables:
            break
        working.apply_flip(rng.choice(best_variables))
        steps_used += 1
        if working.merit >= working.cache.formula.num_clauses:
            break
    return list(working.assignment), working.merit, steps_used


def _bounded_simulated_annealing_refine(
    state: AssignmentState,
    *,
    max_iterations: int,
    max_no_improve: int,
    focus_unsatisfied_probability: float,
    rng: random.Random,
) -> Tuple[TruthAssignment, int]:
    current = state.clone()
    best = state.clone()
    temperature = 8.0
    min_temperature = 0.001
    cooling_rate = 0.995

    iterations = 0
    no_improve_steps = 0
    while iterations < max_iterations and temperature > min_temperature:
        unsatisfied = current.unsatisfied_clause_indices()
        if unsatisfied and rng.random() < focus_unsatisfied_probability:
            clause_index = rng.choice(unsatisfied)
            flip_index = rng.choice(state.cache.clause_variables[clause_index])
        else:
            flip_index = rng.randrange(state.cache.formula.num_variables)
        delta_merit = current.flip_delta(flip_index)

        accept = False
        if delta_merit >= 0:
            accept = True
        else:
            acceptance_probability = math.exp(max(-60.0, delta_merit / max(temperature, 1e-12)))
            if rng.random() < acceptance_probability:
                accept = True

        if accept:
            current.apply_flip(flip_index)
            if current.merit > best.merit:
                best = current.clone()
                no_improve_steps = 0
            else:
                no_improve_steps += 1
        else:
            no_improve_steps += 1

        iterations += 1
        if best.merit >= state.cache.formula.num_clauses and state.cache.formula.num_clauses > 0:
            break
        if no_improve_steps >= max_no_improve:
            break
        temperature *= cooling_rate

    return list(best.assignment), best.merit


def _refine_with_sa(
    state: AssignmentState,
    *,
    max_iterations: int,
    max_no_improve: int,
    focus_unsatisfied_probability: float,
    refinement_mode: str,
    initial_temperature: float,
    cooling_rate: float,
    min_temperature: float,
    restart_count: int,
    candidate_pool_size: int,
    multi_bit_flip_probability: float,
    reheat_multiplier: float,
    max_reheats: int,
    adaptive_cooling: bool,
    intensification_threshold: float,
    mini_hill_climb_steps: int,
    elite_restart_transfer: bool,
    rng: random.Random,
) -> Tuple[TruthAssignment, int]:
    if refinement_mode == "classic":
        return _bounded_simulated_annealing_refine(
            state,
            max_iterations=max_iterations,
            max_no_improve=max_no_improve,
            focus_unsatisfied_probability=focus_unsatisfied_probability,
            rng=rng,
        )

    sa_result = simulated_annealing_search(
        state.cache.formula,
        max_iterations=max_iterations,
        initial_temperature=initial_temperature,
        cooling_rate=cooling_rate,
        min_temperature=min_temperature,
        random_seed=rng.randint(0, 2_147_483_647),
        mode="enhanced",
        restart_count=max(1, restart_count),
        restart_initialization_strategy="polarity",
        elite_restart_transfer=elite_restart_transfer,
        unsatisfied_focus_probability=focus_unsatisfied_probability,
        candidate_pool_size=max(4, candidate_pool_size),
        multi_bit_flip_probability=multi_bit_flip_probability,
        max_multi_flip_size=2,
        stagnation_limit=max(10, max_no_improve),
        reheat_multiplier=reheat_multiplier,
        max_reheats=max_reheats,
        adaptive_cooling=adaptive_cooling,
        intensification_threshold=intensification_threshold,
        intensification_focus_probability=max(focus_unsatisfied_probability, 0.94),
        mini_hill_climb_steps=mini_hill_climb_steps,
        initial_assignment=list(state.assignment),
    )
    return list(sa_result.best_assignment), sa_result.best_merit


def _path_relink_between_elites(
    cache: FormulaCache,
    source_assignment: Sequence[bool],
    target_assignment: Sequence[bool],
    *,
    max_steps: int,
    rng: random.Random,
) -> Tuple[TruthAssignment, int]:
    current = AssignmentState.from_assignment(cache, source_assignment)
    best_assignment = list(current.assignment)
    best_merit = current.merit

    differing = [idx for idx, (a, b) in enumerate(zip(source_assignment, target_assignment)) if bool(a) != bool(b)]
    steps = 0
    while differing and steps < max_steps:
        best_delta: Optional[int] = None
        best_variables: List[int] = []
        for variable_index in differing:
            delta = current.flip_delta(variable_index)
            if best_delta is None or delta > best_delta:
                best_delta = delta
                best_variables = [variable_index]
            elif delta == best_delta:
                best_variables.append(variable_index)
        if not best_variables:
            break
        chosen = rng.choice(best_variables)
        current.apply_flip(chosen)
        steps += 1
        if current.merit > best_merit:
            best_merit = current.merit
            best_assignment = list(current.assignment)
        differing = [idx for idx in differing if current.assignment[idx] != bool(target_assignment[idx])]
        if best_merit >= cache.formula.num_clauses:
            break

    return best_assignment, best_merit


class MemeticGASASolver(BaseSolver):
    algorithm_name = "Memetic GA-SA"

    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        cache = FormulaCache.build(formula)
        n = formula.num_variables
        m = formula.num_clauses

        population_size = int(config.get("population_size", 56))
        max_generations = int(config.get("max_generations", 220))
        crossover_rate = float(config.get("crossover_rate", 0.88))
        mutation_rate = float(config.get("mutation_rate", min(0.04, 2.0 / max(n, 1))))
        elite_count = int(config.get("elite_count", 2))
        tournament_size = int(config.get("tournament_size", 3))
        local_search_every = int(config.get("local_search_every", 10))
        local_search_top_k = int(config.get("local_search_top_k", 2))
        sa_max_iterations = int(config.get("sa_max_iterations", min(900, max(350, 4 * n))))
        sa_patience = int(config.get("sa_patience", max(60, n // 2)))
        stagnation_limit = int(config.get("stagnation_limit", 28))
        restart_fraction = float(config.get("restart_fraction", 0.2))
        intensify_fraction = float(config.get("intensify_fraction", 0.8))
        intensify_mutation_scale = float(config.get("intensify_mutation_scale", 4.0))
        incremental_local_steps = int(config.get("incremental_local_steps", 2))
        incremental_candidate_pool = int(config.get("incremental_candidate_pool", max(40, n // 3)))
        sa_focus_unsatisfied_probability = float(config.get("sa_focus_unsatisfied_probability", 0.7))
        sa_refinement_mode = str(config.get("sa_refinement_mode", "enhanced"))
        sa_initial_temperature = float(config.get("sa_initial_temperature", 24.0))
        sa_cooling_rate = float(config.get("sa_cooling_rate", 0.9975))
        sa_min_temperature = float(config.get("sa_min_temperature", 0.0005))
        sa_restart_count = int(config.get("sa_restart_count", 1))
        sa_candidate_pool_size = int(config.get("sa_candidate_pool_size", max(10, n // 10)))
        sa_multi_bit_flip_probability = float(config.get("sa_multi_bit_flip_probability", 0.04))
        sa_reheat_multiplier = float(config.get("sa_reheat_multiplier", 1.5))
        sa_max_reheats = int(config.get("sa_max_reheats", 2))
        sa_adaptive_cooling = bool(config.get("sa_adaptive_cooling", True))
        sa_intensification_threshold = float(config.get("sa_intensification_threshold", 0.98))
        sa_mini_hill_climb_steps = int(config.get("sa_mini_hill_climb_steps", max(10, int(0.2 * n))))
        sa_elite_restart_transfer = bool(config.get("sa_elite_restart_transfer", True))
        path_relink_every = int(config.get("path_relink_every", 10))
        path_relink_top_k = int(config.get("path_relink_top_k", 3))
        path_relink_max_steps = int(config.get("path_relink_max_steps", max(20, min(60, n // 2))))
        path_relink_only_hardcases = bool(config.get("path_relink_only_hardcases", True))
        hardcase_ratio_threshold = float(config.get("hardcase_ratio_threshold", 4.3))
        hardcase_multi_run_attempts = int(config.get("hardcase_multi_run_attempts", 2))
        hardcase_generation_scale = float(config.get("hardcase_generation_scale", 1.2))
        hardcase_sa_scale = float(config.get("hardcase_sa_scale", 1.25))
        lamarckian = bool(config.get("lamarckian", True))
        random_seed: Optional[int] = config.get("random_seed", None)

        if population_size < 4:
            raise ValueError("population_size must be at least 4.")
        if max_generations < 1:
            raise ValueError("max_generations must be at least 1.")
        if not (0.0 <= crossover_rate <= 1.0):
            raise ValueError("crossover_rate must be in [0, 1].")
        if not (0.0 <= mutation_rate <= 1.0):
            raise ValueError("mutation_rate must be in [0, 1].")
        if elite_count < 1 or elite_count >= population_size:
            raise ValueError("elite_count must be in [1, population_size - 1].")
        if tournament_size < 2:
            raise ValueError("tournament_size must be at least 2.")
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
        if not (0.0 < restart_fraction < 1.0):
            raise ValueError("restart_fraction must be in (0, 1).")
        if not (0.0 <= intensify_fraction <= 1.0):
            raise ValueError("intensify_fraction must be in [0, 1].")
        if intensify_mutation_scale <= 0.0:
            raise ValueError("intensify_mutation_scale must be > 0.")
        if incremental_local_steps < 0:
            raise ValueError("incremental_local_steps must be >= 0.")
        if incremental_candidate_pool < 1:
            raise ValueError("incremental_candidate_pool must be at least 1.")
        if not (0.0 <= sa_focus_unsatisfied_probability <= 1.0):
            raise ValueError("sa_focus_unsatisfied_probability must be in [0, 1].")
        if sa_refinement_mode not in {"classic", "enhanced"}:
            raise ValueError("sa_refinement_mode must be 'classic' or 'enhanced'.")
        if sa_initial_temperature <= 0.0:
            raise ValueError("sa_initial_temperature must be > 0.")
        if not (0.0 < sa_cooling_rate < 1.0):
            raise ValueError("sa_cooling_rate must be in (0, 1).")
        if sa_min_temperature <= 0.0:
            raise ValueError("sa_min_temperature must be > 0.")
        if sa_min_temperature >= sa_initial_temperature:
            raise ValueError("sa_min_temperature must be less than sa_initial_temperature.")
        if sa_restart_count < 1:
            raise ValueError("sa_restart_count must be at least 1.")
        if sa_candidate_pool_size < 1:
            raise ValueError("sa_candidate_pool_size must be at least 1.")
        if not (0.0 <= sa_multi_bit_flip_probability <= 1.0):
            raise ValueError("sa_multi_bit_flip_probability must be in [0, 1].")
        if sa_reheat_multiplier < 1.0:
            raise ValueError("sa_reheat_multiplier must be >= 1.0.")
        if sa_max_reheats < 0:
            raise ValueError("sa_max_reheats must be >= 0.")
        if not (0.0 <= sa_intensification_threshold <= 1.0):
            raise ValueError("sa_intensification_threshold must be in [0, 1].")
        if sa_mini_hill_climb_steps < 0:
            raise ValueError("sa_mini_hill_climb_steps must be >= 0.")
        if path_relink_every < 1:
            raise ValueError("path_relink_every must be at least 1.")
        if path_relink_top_k < 2:
            raise ValueError("path_relink_top_k must be at least 2.")
        if path_relink_max_steps < 1:
            raise ValueError("path_relink_max_steps must be at least 1.")
        if hardcase_multi_run_attempts < 1:
            raise ValueError("hardcase_multi_run_attempts must be at least 1.")
        if hardcase_generation_scale < 1.0:
            raise ValueError("hardcase_generation_scale must be >= 1.0.")
        if hardcase_sa_scale < 1.0:
            raise ValueError("hardcase_sa_scale must be >= 1.0.")

        rng_seed = 0 if random_seed is None else int(random_seed)
        start_time = time.perf_counter()

        def solve_single_attempt(
            *,
            attempt_seed: int,
            attempt_generations: int,
            attempt_sa_iterations: int,
            attempt_sa_patience: int,
            attempt_local_search_every: int,
            attempt_path_relink_every: int,
        ) -> AttemptOutcome:
            rng = random.Random(attempt_seed)
            attempt_start = time.perf_counter()

            population: List[TruthAssignment] = [
                _random_assignment(n, rng) for _ in range(population_size)
            ]
            fitness: List[int] = [
                AssignmentState.from_assignment(cache, individual).merit for individual in population
            ]

            best_index = max(range(population_size), key=lambda idx: fitness[idx])
            best_assignment = list(population[best_index])
            best_fitness = fitness[best_index]
            best_history = [best_fitness]
            runtime_history = [0.0]
            stagnation_counter = 0
            refinement_calls = 0
            local_search_steps_used = 0
            path_relink_calls = 0
            path_relink_improvements = 0
            generations_used = 0

            def tournament_select() -> TruthAssignment:
                candidates = [rng.randrange(population_size) for _ in range(tournament_size)]
                winner = max(candidates, key=lambda idx: fitness[idx])
                return list(population[winner])

            def crossover(parent_a: TruthAssignment, parent_b: TruthAssignment) -> TruthAssignment:
                if n < 2 or rng.random() >= crossover_rate:
                    return list(parent_a if rng.random() < 0.5 else parent_b)
                if n < 3:
                    cut = rng.randrange(1, n)
                    return parent_a[:cut] + parent_b[cut:]
                cut1 = rng.randrange(1, n - 1)
                cut2 = rng.randrange(cut1 + 1, n)
                return parent_a[:cut1] + parent_b[cut1:cut2] + parent_a[cut2:]

            for generation in range(attempt_generations):
                generations_used = generation + 1
                ranked_indices = sorted(
                    range(population_size), key=lambda idx: fitness[idx], reverse=True
                )
                next_population = [list(population[idx]) for idx in ranked_indices[:elite_count]]

                while len(next_population) < population_size:
                    parent_a = tournament_select()
                    parent_b = tournament_select()
                    child = crossover(parent_a, parent_b)
                    for bit_index in range(n):
                        if rng.random() < mutation_rate:
                            child[bit_index] = not child[bit_index]
                    next_population.append(child)

                population = next_population[:population_size]
                fitness = [
                    AssignmentState.from_assignment(cache, individual).merit
                    for individual in population
                ]

                if (generation + 1) % attempt_local_search_every == 0:
                    ranked_indices = sorted(
                        range(population_size), key=lambda idx: fitness[idx], reverse=True
                    )
                    refine_count = min(local_search_top_k, population_size)
                    if stagnation_counter < max(1, attempt_local_search_every // 2):
                        refine_count = 1
                    for idx in ranked_indices[:refine_count]:
                        state = AssignmentState.from_assignment(cache, population[idx])
                        if incremental_local_steps > 0:
                            local_assignment, local_merit, steps_used = _incremental_local_search(
                                state,
                                max_steps=incremental_local_steps,
                                max_candidates=incremental_candidate_pool,
                                rng=rng,
                            )
                            local_search_steps_used += steps_used
                            if local_merit > fitness[idx]:
                                population[idx] = local_assignment
                                fitness[idx] = local_merit
                                state = AssignmentState.from_assignment(cache, local_assignment)
                        effective_sa_iterations = min(
                            attempt_sa_iterations,
                            max(120, 2 * n + stagnation_counter * max(10, n // 6)),
                        )
                        refined_assignment, refined_merit = _refine_with_sa(
                            state,
                            max_iterations=effective_sa_iterations,
                            max_no_improve=attempt_sa_patience,
                            focus_unsatisfied_probability=sa_focus_unsatisfied_probability,
                            refinement_mode=sa_refinement_mode,
                            initial_temperature=sa_initial_temperature,
                            cooling_rate=sa_cooling_rate,
                            min_temperature=sa_min_temperature,
                            restart_count=sa_restart_count,
                            candidate_pool_size=sa_candidate_pool_size,
                            multi_bit_flip_probability=sa_multi_bit_flip_probability,
                            reheat_multiplier=sa_reheat_multiplier,
                            max_reheats=sa_max_reheats,
                            adaptive_cooling=sa_adaptive_cooling,
                            intensification_threshold=sa_intensification_threshold,
                            mini_hill_climb_steps=sa_mini_hill_climb_steps,
                            elite_restart_transfer=sa_elite_restart_transfer,
                            rng=rng,
                        )
                        refinement_calls += 1
                        if refined_merit > best_fitness:
                            best_fitness = refined_merit
                            best_assignment = list(refined_assignment)
                        if lamarckian and refined_merit > fitness[idx]:
                            population[idx] = list(refined_assignment)
                            fitness[idx] = refined_merit

                if (generation + 1) % attempt_path_relink_every == 0 and population_size >= 2:
                    ranked_indices = sorted(
                        range(population_size), key=lambda idx: fitness[idx], reverse=True
                    )
                    anchor_idx = ranked_indices[0]
                    top_count = min(path_relink_top_k, population_size)
                    for idx in ranked_indices[1:top_count]:
                        relinked_assignment, relinked_merit = _path_relink_between_elites(
                            cache,
                            population[anchor_idx],
                            population[idx],
                            max_steps=path_relink_max_steps,
                            rng=rng,
                        )
                        path_relink_calls += 1
                        if relinked_merit > best_fitness:
                            best_fitness = relinked_merit
                            best_assignment = list(relinked_assignment)
                        if relinked_merit > fitness[idx]:
                            path_relink_improvements += 1
                            population[idx] = list(relinked_assignment)
                            fitness[idx] = relinked_merit

                iteration_best_idx = max(range(population_size), key=lambda idx: fitness[idx])
                iteration_best = fitness[iteration_best_idx]
                if iteration_best > best_fitness:
                    best_fitness = iteration_best
                    best_assignment = list(population[iteration_best_idx])
                    stagnation_counter = 0
                else:
                    stagnation_counter += 1

                if stagnation_counter >= stagnation_limit:
                    ranked_indices = sorted(
                        range(population_size), key=lambda idx: fitness[idx], reverse=True
                    )
                    keep_count = max(
                        elite_count, int(round(population_size * (1.0 - restart_fraction)))
                    )
                    mutated_clones = int(
                        round((population_size - keep_count) * intensify_fraction)
                    )
                    mutation_span = max(
                        1, int(round(intensify_mutation_scale * max(1.0, n * mutation_rate)))
                    )
                    replacement_indices = ranked_indices[keep_count:]
                    for idx in replacement_indices[:mutated_clones]:
                        clone = list(best_assignment)
                        flips = rng.randint(1, mutation_span)
                        for bit_index in rng.sample(range(n), min(flips, n)):
                            clone[bit_index] = not clone[bit_index]
                        population[idx] = clone
                        fitness[idx] = AssignmentState.from_assignment(cache, clone).merit
                    for idx in replacement_indices[mutated_clones:]:
                        population[idx] = _random_assignment(n, rng)
                        fitness[idx] = AssignmentState.from_assignment(cache, population[idx]).merit
                    refreshed_best_idx = max(range(population_size), key=lambda idx: fitness[idx])
                    refreshed_best = fitness[refreshed_best_idx]
                    if refreshed_best > best_fitness:
                        best_fitness = refreshed_best
                        best_assignment = list(population[refreshed_best_idx])
                    stagnation_counter = 0

                best_history.append(best_fitness)
                runtime_history.append(time.perf_counter() - attempt_start)
                if best_fitness >= m and m > 0:
                    break

            return AttemptOutcome(
                best_assignment=best_assignment,
                best_merit=best_fitness,
                best_history=best_history,
                runtime_history=runtime_history,
                iterations_used=generations_used,
                refinement_calls=refinement_calls,
                local_search_steps=local_search_steps_used,
                path_relink_calls=path_relink_calls,
                path_relink_improvements=path_relink_improvements,
            )

        is_hard_instance = cache.density_ratio >= hardcase_ratio_threshold
        effective_base_path_relink_every = path_relink_every
        if path_relink_only_hardcases and not is_hard_instance:
            effective_base_path_relink_every = max_generations + 1
        attempt_configs: List[Tuple[int, int, int, int, int, int]] = [
            (
                rng_seed,
                max_generations,
                sa_max_iterations,
                sa_patience,
                local_search_every,
                effective_base_path_relink_every,
            )
        ]

        if is_hard_instance and hardcase_multi_run_attempts > 1:
            intensified_generations = int(round(max_generations * hardcase_generation_scale))
            intensified_sa = int(round(sa_max_iterations * hardcase_sa_scale))
            intensified_patience = int(round(sa_patience * hardcase_sa_scale))
            intensified_local_search_every = max(6, local_search_every - 2)
            intensified_path_relink_every = max(6, path_relink_every - 2)
            for attempt_index in range(1, hardcase_multi_run_attempts):
                attempt_configs.append(
                    (
                        rng_seed + attempt_index * 101_003,
                        intensified_generations,
                        intensified_sa,
                        intensified_patience,
                        intensified_local_search_every,
                        intensified_path_relink_every,
                    )
                )

        combined_best_history = [0]
        combined_runtime_history = [0.0]
        global_best_merit = -1
        global_best_assignment: TruthAssignment = _random_assignment(n, random.Random(rng_seed))
        attempts_used = 0
        total_iterations_used = 0
        total_refinement_calls = 0
        total_local_search_steps = 0
        total_path_relink_calls = 0
        total_path_relink_improvements = 0
        multi_run_triggered = False

        for attempt_index, (
            attempt_seed,
            attempt_generations,
            attempt_sa_iterations,
            attempt_sa_patience,
            attempt_local_every,
            attempt_path_every,
        ) in enumerate(attempt_configs):
            if attempt_index > 0 and (not is_hard_instance or global_best_merit >= m):
                break
            if attempt_index > 0:
                multi_run_triggered = True
            outcome = solve_single_attempt(
                attempt_seed=attempt_seed,
                attempt_generations=attempt_generations,
                attempt_sa_iterations=attempt_sa_iterations,
                attempt_sa_patience=attempt_sa_patience,
                attempt_local_search_every=attempt_local_every,
                attempt_path_relink_every=attempt_path_every,
            )
            attempts_used += 1
            total_iterations_used += outcome.iterations_used
            total_refinement_calls += outcome.refinement_calls
            total_local_search_steps += outcome.local_search_steps
            total_path_relink_calls += outcome.path_relink_calls
            total_path_relink_improvements += outcome.path_relink_improvements
            if outcome.best_merit > global_best_merit:
                global_best_merit = outcome.best_merit
                global_best_assignment = list(outcome.best_assignment)

            runtime_offset = combined_runtime_history[-1]
            for merit, elapsed in zip(outcome.best_history[1:], outcome.runtime_history[1:]):
                combined_best_history.append(max(combined_best_history[-1], merit, global_best_merit))
                combined_runtime_history.append(runtime_offset + elapsed)

            if global_best_merit >= m:
                break
            if attempt_index == 0 and (not is_hard_instance or hardcase_multi_run_attempts <= 1):
                break

        if len(combined_best_history) == 1:
            combined_best_history = [global_best_merit]
            combined_runtime_history = [0.0]
        else:
            combined_best_history[0] = max(0, combined_best_history[1])

        return normalize_result(
            algorithm_name=self.algorithm_name,
            assignment=global_best_assignment,
            runtime_seconds=time.perf_counter() - start_time,
            iterations_used=total_iterations_used,
            best_history=combined_best_history,
            runtime_history=combined_runtime_history,
            parameter_summary={
                "population_size": population_size,
                "max_generations": max_generations,
                "crossover_rate": crossover_rate,
                "mutation_rate": mutation_rate,
                "elite_count": elite_count,
                "tournament_size": tournament_size,
                "local_search_every": local_search_every,
                "local_search_top_k": local_search_top_k,
                "sa_max_iterations": sa_max_iterations,
                "sa_patience": sa_patience,
                "stagnation_limit": stagnation_limit,
                "restart_fraction": restart_fraction,
                "intensify_fraction": intensify_fraction,
                "intensify_mutation_scale": intensify_mutation_scale,
                "incremental_local_steps": incremental_local_steps,
                "incremental_candidate_pool": incremental_candidate_pool,
                "sa_focus_unsatisfied_probability": sa_focus_unsatisfied_probability,
                "sa_refinement_mode": sa_refinement_mode,
                "sa_initial_temperature": sa_initial_temperature,
                "sa_cooling_rate": sa_cooling_rate,
                "sa_min_temperature": sa_min_temperature,
                "sa_restart_count": sa_restart_count,
                "sa_candidate_pool_size": sa_candidate_pool_size,
                "sa_multi_bit_flip_probability": sa_multi_bit_flip_probability,
                "sa_reheat_multiplier": sa_reheat_multiplier,
                "sa_max_reheats": sa_max_reheats,
                "sa_adaptive_cooling": sa_adaptive_cooling,
                "sa_intensification_threshold": sa_intensification_threshold,
                "sa_mini_hill_climb_steps": sa_mini_hill_climb_steps,
                "sa_elite_restart_transfer": sa_elite_restart_transfer,
                "path_relink_every": path_relink_every,
                "path_relink_top_k": path_relink_top_k,
                "path_relink_max_steps": path_relink_max_steps,
                "path_relink_only_hardcases": path_relink_only_hardcases,
                "hardcase_ratio_threshold": hardcase_ratio_threshold,
                "hardcase_multi_run_attempts": hardcase_multi_run_attempts,
                "hardcase_generation_scale": hardcase_generation_scale,
                "hardcase_sa_scale": hardcase_sa_scale,
                "attempts_used": attempts_used,
                "multi_run_triggered": multi_run_triggered,
                "refinement_calls": total_refinement_calls,
                "local_search_steps": total_local_search_steps,
                "path_relink_calls": total_path_relink_calls,
                "path_relink_improvements": total_path_relink_improvements,
                "lamarckian": lamarckian,
                "random_seed": random_seed,
            },
            formula=formula,
        )
