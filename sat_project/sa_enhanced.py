from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from utils import CNFFormula, TruthAssignment


@dataclass(frozen=True)
class SARestartSummary:
    restart_index: int
    random_seed: int
    initialization_strategy: str
    best_satisfied_clauses: int
    total_clauses: int
    satisfaction_rate: float
    runtime_seconds: float
    iterations_used: int
    iteration_of_best: int
    iteration_of_full_satisfaction: Optional[int]
    fully_satisfied: bool
    reheat_count: int
    accepted_worse_moves: int
    accepted_better_moves: int
    accepted_equal_moves: int
    number_of_unsatisfied_focused_moves: int
    best_history: Tuple[int, ...]
    temperature_history: Tuple[float, ...]
    accepted_move_history: Tuple[str, ...]
    final_assignment: Tuple[bool, ...]


@dataclass(frozen=True)
class SimulatedAnnealingResult:
    best_assignment: Tuple[bool, ...]
    best_merit: int
    total_clauses: int
    fully_satisfied: bool
    iterations_used: int
    restart_count: int
    runtime_seconds: float
    merit_history: Tuple[int, ...]
    runtime_history: Tuple[float, ...]
    temperature_history: Tuple[float, ...] = ()
    iteration_of_best: int = 0
    iteration_of_full_satisfaction: Optional[int] = None
    reheat_count: int = 0
    accepted_worse_moves: int = 0
    accepted_better_moves: int = 0
    accepted_equal_moves: int = 0
    number_of_unsatisfied_focused_moves: int = 0
    restart_summaries: Tuple[SARestartSummary, ...] = ()
    final_satisfaction_rates: Tuple[float, ...] = ()
    accepted_move_history: Tuple[str, ...] = ()
    mode: str = "enhanced"
    parameter_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FormulaCache:
    formula: CNFFormula
    occurrences_by_variable: Tuple[Tuple[Tuple[int, bool], ...], ...]
    clause_variables: Tuple[Tuple[int, ...], ...]
    positive_occurrences: Tuple[int, ...]
    negative_occurrences: Tuple[int, ...]

    @classmethod
    def build(cls, formula: CNFFormula) -> "FormulaCache":
        occurrences: List[List[Tuple[int, bool]]] = [[] for _ in range(formula.num_variables)]
        clause_variables: List[Tuple[int, ...]] = []
        positive_occurrences = [0] * formula.num_variables
        negative_occurrences = [0] * formula.num_variables
        for clause_index, clause in enumerate(formula.clauses):
            variables: List[int] = []
            for literal in clause:
                literal_true_when_var_true = not literal.is_negated
                occurrences[literal.variable_index].append(
                    (clause_index, literal_true_when_var_true)
                )
                variables.append(literal.variable_index)
                if literal_true_when_var_true:
                    positive_occurrences[literal.variable_index] += 1
                else:
                    negative_occurrences[literal.variable_index] += 1
            clause_variables.append(tuple(dict.fromkeys(variables)))
        return cls(
            formula=formula,
            occurrences_by_variable=tuple(tuple(items) for items in occurrences),
            clause_variables=tuple(clause_variables),
            positive_occurrences=tuple(positive_occurrences),
            negative_occurrences=tuple(negative_occurrences),
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
            true_count = 0
            for literal in clause:
                if bool(assignment[literal.variable_index]) == (not literal.is_negated):
                    true_count += 1
            clause_true_counts[clause_index] = true_count
            if true_count > 0:
                merit += 1
        return cls(
            cache=cache,
            assignment=[bool(value) for value in assignment],
            clause_true_counts=clause_true_counts,
            merit=merit,
        )

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

    def flip_stats(self, variable_index: int) -> Tuple[int, int, int]:
        current_value = self.assignment[variable_index]
        make = 0
        break_count = 0
        for clause_index, literal_true_when_var_true in self.cache.occurrences_by_variable[variable_index]:
            before_true = current_value == literal_true_when_var_true
            after_true = (not current_value) == literal_true_when_var_true
            if before_true == after_true:
                continue
            old_count = self.clause_true_counts[clause_index]
            new_count = old_count + (1 if after_true else -1)
            if old_count == 0 and new_count > 0:
                make += 1
            elif old_count > 0 and new_count == 0:
                break_count += 1
        return make - break_count, make, break_count

    def apply_flip(self, variable_index: int) -> int:
        delta, _, _ = self.flip_stats(variable_index)
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


def _clamp_probability(value: float) -> float:
    return max(0.0, min(1.0, value))


def _random_assignment(num_variables: int, rng: random.Random) -> TruthAssignment:
    return [rng.choice((False, True)) for _ in range(num_variables)]


def _polarity_assignment(
    cache: FormulaCache,
    *,
    rng: random.Random,
    strength: float,
) -> TruthAssignment:
    assignment: TruthAssignment = []
    strength = _clamp_probability(strength)
    for variable_index in range(cache.formula.num_variables):
        prefer_true = cache.positive_occurrences[variable_index] >= cache.negative_occurrences[variable_index]
        if rng.random() < strength:
            assignment.append(prefer_true)
        else:
            assignment.append(rng.choice((False, True)))
    return assignment


def _history_guided_assignment(
    cache: FormulaCache,
    *,
    rng: random.Random,
    history_true_scores: Sequence[float],
    history_false_scores: Sequence[float],
    polarity_strength: float,
    history_strength: float,
) -> TruthAssignment:
    assignment: TruthAssignment = []
    polarity_strength = _clamp_probability(polarity_strength)
    history_strength = _clamp_probability(history_strength)
    for variable_index in range(cache.formula.num_variables):
        history_bias = history_true_scores[variable_index] - history_false_scores[variable_index]
        if history_bias > 0.0 and rng.random() < history_strength:
            assignment.append(True)
            continue
        if history_bias < 0.0 and rng.random() < history_strength:
            assignment.append(False)
            continue
        prefer_true = cache.positive_occurrences[variable_index] >= cache.negative_occurrences[variable_index]
        if rng.random() < polarity_strength:
            assignment.append(prefer_true)
        else:
            assignment.append(rng.choice((False, True)))
    return assignment


def _apply_elite_transfer(
    seed_assignment: Sequence[bool],
    *,
    num_variables: int,
    rng: random.Random,
    perturbation_size: int,
) -> TruthAssignment:
    assignment = [bool(value) for value in seed_assignment]
    if num_variables <= 0:
        return assignment
    flips = max(1, min(num_variables, perturbation_size))
    for variable_index in rng.sample(range(num_variables), flips):
        assignment[variable_index] = not assignment[variable_index]
    return assignment


def _update_unsatisfied_history(
    cache: FormulaCache,
    state: AssignmentState,
    history_true_scores: List[float],
    history_false_scores: List[float],
) -> None:
    for clause_index in state.unsatisfied_clause_indices():
        clause = cache.formula.clauses[clause_index]
        for literal in clause:
            if literal.is_negated:
                history_false_scores[literal.variable_index] += 1.0
            else:
                history_true_scores[literal.variable_index] += 1.0


def _candidate_variables_from_unsatisfied(
    state: AssignmentState,
    *,
    rng: random.Random,
    max_candidates: int,
) -> List[int]:
    variables: List[int] = []
    seen: set[int] = set()
    unsatisfied = state.unsatisfied_clause_indices()
    rng.shuffle(unsatisfied)
    for clause_index in unsatisfied:
        clause_vars = list(state.cache.clause_variables[clause_index])
        rng.shuffle(clause_vars)
        for variable_index in clause_vars:
            if variable_index not in seen:
                seen.add(variable_index)
                variables.append(variable_index)
                if len(variables) >= max_candidates:
                    return variables
    return variables


def _candidate_variables(
    state: AssignmentState,
    *,
    rng: random.Random,
    max_candidates: int,
    focused: bool,
) -> List[int]:
    if focused:
        variables = _candidate_variables_from_unsatisfied(
            state, rng=rng, max_candidates=max_candidates
        )
        if variables:
            return variables
    if state.cache.formula.num_variables <= max_candidates:
        variables = list(range(state.cache.formula.num_variables))
        rng.shuffle(variables)
        return variables
    return rng.sample(range(state.cache.formula.num_variables), max_candidates)


def _choose_move_size(
    *,
    base_probability: float,
    max_multi_flip_size: int,
    no_improve_streak: int,
    stagnation_limit: int,
    stagnation_boost: float,
    intensifying: bool,
    rng: random.Random,
) -> int:
    if max_multi_flip_size <= 1:
        return 1
    probability = base_probability
    if no_improve_streak >= max(1, stagnation_limit // 2):
        probability += stagnation_boost
    if intensifying:
        probability *= 0.35
    probability = _clamp_probability(probability)
    if rng.random() >= probability:
        return 1
    upper = max(2, max_multi_flip_size)
    if no_improve_streak >= stagnation_limit:
        return upper
    return rng.randint(2, upper)


def _propose_move(
    state: AssignmentState,
    *,
    rng: random.Random,
    focused_probability: float,
    candidate_pool_size: int,
    multi_bit_flip_probability: float,
    max_multi_flip_size: int,
    stagnation_limit: int,
    stagnation_multi_bit_boost: float,
    no_improve_streak: int,
    intensifying: bool,
) -> Tuple[List[int], int, bool]:
    focused = bool(state.unsatisfied_clause_indices()) and rng.random() < focused_probability
    move_size = _choose_move_size(
        base_probability=multi_bit_flip_probability,
        max_multi_flip_size=max_multi_flip_size,
        no_improve_streak=no_improve_streak,
        stagnation_limit=stagnation_limit,
        stagnation_boost=stagnation_multi_bit_boost,
        intensifying=intensifying,
        rng=rng,
    )

    working = state.clone()
    selected: List[int] = []
    for _ in range(move_size):
        candidates = _candidate_variables(
            working,
            rng=rng,
            max_candidates=max(1, candidate_pool_size),
            focused=focused,
        )
        candidates = [candidate for candidate in candidates if candidate not in selected]
        if not candidates:
            break
        scored = []
        for variable_index in candidates:
            delta, make, break_count = working.flip_stats(variable_index)
            score = delta + 0.15 * make - 0.05 * break_count
            scored.append((score, delta, make, break_count, variable_index))
        scored.sort(reverse=True)
        top = scored[: max(1, min(4, len(scored)))]
        best_score = top[0][0]
        filtered = [item for item in top if item[0] >= best_score - 0.25]
        _, _, _, _, chosen = rng.choice(filtered)
        working.apply_flip(chosen)
        selected.append(chosen)
        if working.merit >= working.cache.formula.num_clauses:
            break

    if not selected:
        fallback = rng.randrange(state.cache.formula.num_variables)
        return [fallback], state.flip_stats(fallback)[0], focused

    return selected, working.merit - state.merit, focused


def _apply_move(state: AssignmentState, flip_indices: Sequence[int]) -> int:
    total_delta = 0
    for flip_index in flip_indices:
        total_delta += state.apply_flip(flip_index)
    return total_delta


def _mini_hill_climb_finish(
    state: AssignmentState,
    *,
    max_steps: int,
    candidate_pool_size: int,
    rng: random.Random,
) -> Tuple[TruthAssignment, int]:
    working = state.clone()
    for _ in range(max_steps):
        candidates = _candidate_variables(
            working,
            rng=rng,
            max_candidates=max(1, candidate_pool_size),
            focused=True,
        )
        best_delta = 0
        best_variables: List[int] = []
        for variable_index in candidates:
            delta, _, _ = working.flip_stats(variable_index)
            if delta > best_delta:
                best_delta = delta
                best_variables = [variable_index]
            elif delta == best_delta and delta > 0:
                best_variables.append(variable_index)
        if best_delta <= 0 or not best_variables:
            break
        working.apply_flip(rng.choice(best_variables))
        if working.merit >= working.cache.formula.num_clauses:
            break
    return list(working.assignment), working.merit


def run_enhanced_simulated_annealing(
    formula: CNFFormula,
    *,
    max_iterations: int,
    initial_temperature: float,
    cooling_rate: float,
    min_temperature: float,
    random_seed: Optional[int],
    restart_count: int,
    restart_initialization_strategy: str,
    unsatisfied_focus_probability: float,
    candidate_pool_size: int,
    multi_bit_flip_probability: float,
    max_multi_flip_size: int,
    stagnation_multi_bit_boost: float,
    stagnation_limit: int,
    reheat_multiplier: float,
    max_reheats: int,
    adaptive_cooling: bool,
    adaptive_cooling_bonus: float,
    adaptive_cooling_penalty: float,
    intensification_threshold: float,
    intensification_focus_probability: float,
    intensification_cooling_bonus: float,
    mini_hill_climb_steps: int,
    polarity_bias_strength: float,
    history_bias_strength: float,
    elite_restart_transfer: bool,
    elite_restart_perturbation: int,
    initial_assignment: Optional[Sequence[bool]] = None,
) -> SimulatedAnnealingResult:
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1.")
    if initial_temperature <= 0.0:
        raise ValueError("initial_temperature must be > 0.")
    if not (0.0 < cooling_rate < 1.0):
        raise ValueError("cooling_rate must be in (0, 1).")
    if min_temperature <= 0.0:
        raise ValueError("min_temperature must be > 0.")
    if min_temperature >= initial_temperature:
        raise ValueError("min_temperature must be less than initial_temperature.")
    if restart_count < 1:
        raise ValueError("restart_count must be at least 1.")
    if candidate_pool_size < 1:
        raise ValueError("candidate_pool_size must be at least 1.")
    if max_multi_flip_size < 1:
        raise ValueError("max_multi_flip_size must be at least 1.")
    if stagnation_limit < 1:
        raise ValueError("stagnation_limit must be at least 1.")
    if reheat_multiplier < 1.0:
        raise ValueError("reheat_multiplier must be >= 1.0.")
    if max_reheats < 0:
        raise ValueError("max_reheats must be >= 0.")
    if mini_hill_climb_steps < 0:
        raise ValueError("mini_hill_climb_steps must be >= 0.")

    cache = FormulaCache.build(formula)
    master_rng = random.Random(random_seed)
    overall_start = time.perf_counter()

    history_true_scores = [0.0] * formula.num_variables
    history_false_scores = [0.0] * formula.num_variables
    restart_summaries: List[SARestartSummary] = []
    combined_best_history = [0]
    combined_runtime_history = [0.0]
    combined_temperature_history = [initial_temperature]
    combined_move_history: List[str] = ["start"]

    global_best_assignment = tuple(_random_assignment(formula.num_variables, master_rng))
    global_best_merit = -1
    global_iteration_of_best = 0
    global_iteration_of_full_satisfaction: Optional[int] = None
    total_iterations_used = 0
    total_reheats = 0
    total_accepted_worse_moves = 0
    total_accepted_better_moves = 0
    total_accepted_equal_moves = 0
    total_unsatisfied_focused_moves = 0
    final_satisfaction_rates: List[float] = []

    for restart_index in range(restart_count):
        restart_seed = master_rng.randint(0, 2_147_483_647)
        rng = random.Random(restart_seed)
        restart_start = time.perf_counter()

        init_strategy = restart_initialization_strategy
        if restart_index == 0 and init_strategy == "history":
            init_strategy = "polarity"

        if restart_index == 0 and initial_assignment is not None:
            init_strategy = "provided_initial_assignment"
            current_assignment = [bool(value) for value in initial_assignment]
        elif elite_restart_transfer and restart_index > 0 and global_best_merit >= 0:
            init_strategy = f"{init_strategy}+elite"
            current_assignment = _apply_elite_transfer(
                global_best_assignment,
                num_variables=formula.num_variables,
                rng=rng,
                perturbation_size=max(1, elite_restart_perturbation),
            )
        elif init_strategy == "polarity":
            current_assignment = _polarity_assignment(
                cache,
                rng=rng,
                strength=polarity_bias_strength,
            )
        elif init_strategy == "history":
            current_assignment = _history_guided_assignment(
                cache,
                rng=rng,
                history_true_scores=history_true_scores,
                history_false_scores=history_false_scores,
                polarity_strength=polarity_bias_strength,
                history_strength=history_bias_strength,
            )
        else:
            current_assignment = _random_assignment(formula.num_variables, rng)

        current_state = AssignmentState.from_assignment(cache, current_assignment)
        best_state = current_state.clone()
        temperature = initial_temperature
        no_improve_streak = 0
        reheat_count = 0
        iteration_of_best = 0
        iteration_of_full_satisfaction: Optional[int] = (
            0 if current_state.merit >= formula.num_clauses else None
        )
        accepted_worse_moves = 0
        accepted_better_moves = 0
        accepted_equal_moves = 0
        unsatisfied_focused_moves = 0
        best_history = [best_state.merit]
        temperature_history = [temperature]
        accepted_move_history = ["start"]

        if best_state.merit >= formula.num_clauses:
            global_best_merit = best_state.merit
            global_best_assignment = tuple(best_state.assignment)
            global_iteration_of_best = total_iterations_used
            global_iteration_of_full_satisfaction = total_iterations_used
            final_satisfaction_rates.append(1.0)
            restart_summaries.append(
                SARestartSummary(
                    restart_index=restart_index,
                    random_seed=restart_seed,
                    initialization_strategy=init_strategy,
                    best_satisfied_clauses=best_state.merit,
                    total_clauses=formula.num_clauses,
                    satisfaction_rate=1.0,
                    runtime_seconds=time.perf_counter() - restart_start,
                    iterations_used=0,
                    iteration_of_best=0,
                    iteration_of_full_satisfaction=0,
                    fully_satisfied=True,
                    reheat_count=0,
                    accepted_worse_moves=0,
                    accepted_better_moves=0,
                    accepted_equal_moves=0,
                    number_of_unsatisfied_focused_moves=0,
                    best_history=tuple(best_history),
                    temperature_history=tuple(temperature_history),
                    accepted_move_history=tuple(accepted_move_history),
                    final_assignment=tuple(best_state.assignment),
                )
            )
            break

        iterations_used = 0
        while iterations_used < max_iterations and temperature > min_temperature:
            current_rate = 0.0 if formula.num_clauses == 0 else current_state.merit / formula.num_clauses
            best_rate = 0.0 if formula.num_clauses == 0 else best_state.merit / formula.num_clauses
            intensifying = max(current_rate, best_rate) >= intensification_threshold
            focused_probability = (
                max(unsatisfied_focus_probability, intensification_focus_probability)
                if intensifying
                else unsatisfied_focus_probability
            )
            move_size_limit = 1 if intensifying else max_multi_flip_size
            flip_indices, delta_merit, focused_move = _propose_move(
                current_state,
                rng=rng,
                focused_probability=focused_probability,
                candidate_pool_size=candidate_pool_size,
                multi_bit_flip_probability=multi_bit_flip_probability,
                max_multi_flip_size=move_size_limit,
                stagnation_limit=stagnation_limit,
                stagnation_multi_bit_boost=stagnation_multi_bit_boost,
                no_improve_streak=no_improve_streak,
                intensifying=intensifying,
            )
            if focused_move:
                unsatisfied_focused_moves += 1

            should_accept = False
            if delta_merit >= 0:
                should_accept = True
            else:
                acceptance_probability = math.exp(max(-60.0, delta_merit / max(temperature, 1e-12)))
                if rng.random() < acceptance_probability:
                    should_accept = True

            if should_accept:
                actual_delta = _apply_move(current_state, flip_indices)
                if actual_delta > 0:
                    accepted_better_moves += 1
                    accepted_move_history.append("better")
                elif actual_delta == 0:
                    accepted_equal_moves += 1
                    accepted_move_history.append("equal")
                else:
                    accepted_worse_moves += 1
                    accepted_move_history.append("worse")

                if current_state.merit > best_state.merit:
                    best_state = current_state.clone()
                    iteration_of_best = iterations_used + 1
                    no_improve_streak = 0
                    if best_state.merit >= formula.num_clauses and iteration_of_full_satisfaction is None:
                        iteration_of_full_satisfaction = iterations_used + 1
                else:
                    no_improve_streak += 1
            else:
                accepted_move_history.append("rejected")
                no_improve_streak += 1

            iterations_used += 1
            best_history.append(best_state.merit)
            temperature_history.append(temperature)

            if best_state.merit >= formula.num_clauses:
                break

            cooling_factor = cooling_rate
            if adaptive_cooling:
                if accepted_move_history[-1] == "better":
                    cooling_factor = min(0.99995, cooling_factor + adaptive_cooling_bonus)
                elif no_improve_streak >= max(1, stagnation_limit // 2):
                    cooling_factor = max(0.90, cooling_factor - adaptive_cooling_penalty)
            if intensifying:
                cooling_factor = min(0.99995, cooling_factor + intensification_cooling_bonus)
            temperature = max(min_temperature, temperature * cooling_factor)

            if (
                no_improve_streak >= stagnation_limit
                and reheat_count < max_reheats
                and best_state.merit < formula.num_clauses
            ):
                temperature = min(initial_temperature, max(temperature, min_temperature) * reheat_multiplier)
                no_improve_streak = 0
                reheat_count += 1
                temperature_history[-1] = temperature

        if mini_hill_climb_steps > 0 and best_state.merit < formula.num_clauses:
            finished_assignment, finished_merit = _mini_hill_climb_finish(
                best_state,
                max_steps=mini_hill_climb_steps,
                candidate_pool_size=candidate_pool_size,
                rng=rng,
            )
            if finished_merit > best_state.merit:
                best_state = AssignmentState.from_assignment(cache, finished_assignment)
                iteration_of_best = iterations_used
                if best_state.merit >= formula.num_clauses and iteration_of_full_satisfaction is None:
                    iteration_of_full_satisfaction = iterations_used
                best_history.append(best_state.merit)
                temperature_history.append(temperature_history[-1] if temperature_history else initial_temperature)
                accepted_move_history.append("mini_hill_climb")

        _update_unsatisfied_history(cache, best_state, history_true_scores, history_false_scores)

        satisfaction_rate = (
            0.0 if formula.num_clauses == 0 else best_state.merit / formula.num_clauses
        )
        final_satisfaction_rates.append(satisfaction_rate)
        restart_runtime = time.perf_counter() - restart_start
        restart_summaries.append(
            SARestartSummary(
                restart_index=restart_index,
                random_seed=restart_seed,
                initialization_strategy=init_strategy,
                best_satisfied_clauses=best_state.merit,
                total_clauses=formula.num_clauses,
                satisfaction_rate=satisfaction_rate,
                runtime_seconds=restart_runtime,
                iterations_used=iterations_used,
                iteration_of_best=iteration_of_best,
                iteration_of_full_satisfaction=iteration_of_full_satisfaction,
                fully_satisfied=best_state.merit >= formula.num_clauses and formula.num_clauses > 0,
                reheat_count=reheat_count,
                accepted_worse_moves=accepted_worse_moves,
                accepted_better_moves=accepted_better_moves,
                accepted_equal_moves=accepted_equal_moves,
                number_of_unsatisfied_focused_moves=unsatisfied_focused_moves,
                best_history=tuple(best_history),
                temperature_history=tuple(temperature_history),
                accepted_move_history=tuple(accepted_move_history),
                final_assignment=tuple(best_state.assignment),
            )
        )

        total_reheats += reheat_count
        total_accepted_worse_moves += accepted_worse_moves
        total_accepted_better_moves += accepted_better_moves
        total_accepted_equal_moves += accepted_equal_moves
        total_unsatisfied_focused_moves += unsatisfied_focused_moves

        restart_offset = combined_runtime_history[-1]
        for step_index, merit in enumerate(best_history[1:], start=1):
            combined_best_history.append(max(combined_best_history[-1], merit))
            combined_runtime_history.append(restart_offset + (restart_runtime * step_index / max(1, len(best_history) - 1)))
        combined_temperature_history.extend(temperature_history[1:])
        combined_move_history.extend(accepted_move_history[1:])

        total_iterations_used += iterations_used
        if best_state.merit > global_best_merit:
            global_best_merit = best_state.merit
            global_best_assignment = tuple(best_state.assignment)
            global_iteration_of_best = total_iterations_used - max(0, iterations_used - iteration_of_best)
            if best_state.merit >= formula.num_clauses and iteration_of_full_satisfaction is not None:
                global_iteration_of_full_satisfaction = (
                    total_iterations_used - max(0, iterations_used - iteration_of_full_satisfaction)
                )

        if best_state.merit >= formula.num_clauses:
            break

    if len(combined_best_history) == 1:
        combined_best_history[0] = max(0, global_best_merit)

    return SimulatedAnnealingResult(
        best_assignment=global_best_assignment,
        best_merit=global_best_merit,
        total_clauses=formula.num_clauses,
        fully_satisfied=global_best_merit >= formula.num_clauses and formula.num_clauses > 0,
        iterations_used=total_iterations_used,
        restart_count=len(restart_summaries),
        runtime_seconds=time.perf_counter() - overall_start,
        merit_history=tuple(combined_best_history),
        runtime_history=tuple(combined_runtime_history),
        temperature_history=tuple(combined_temperature_history),
        iteration_of_best=global_iteration_of_best,
        iteration_of_full_satisfaction=global_iteration_of_full_satisfaction,
        reheat_count=total_reheats,
        accepted_worse_moves=total_accepted_worse_moves,
        accepted_better_moves=total_accepted_better_moves,
        accepted_equal_moves=total_accepted_equal_moves,
        number_of_unsatisfied_focused_moves=total_unsatisfied_focused_moves,
        restart_summaries=tuple(restart_summaries),
        final_satisfaction_rates=tuple(final_satisfaction_rates),
        accepted_move_history=tuple(combined_move_history),
        mode="enhanced",
        parameter_summary={},
    )
