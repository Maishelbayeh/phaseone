from __future__ import annotations

from typing import Any, Dict, Mapping

from hill_climbing import hill_climb_with_random_restarts
from hybrid_bsgo_ga import hybrid_bsgo_ga_search
from simulated_annealing import simulated_annealing_search
from tabu_search import tabu_search_solve
from utils import CNFFormula

from .base_solver import BaseSolver, SolverResult, normalize_result
from .binary_swarm_solver import BinarySwarmSolver
from .genetic_algorithm import GeneticAlgorithmSolver
from .memetic_ga_sa import MemeticGASASolver
from .swarm_sa_solver import SwarmSASolver


class HillClimbingSolver(BaseSolver):
    algorithm_name = "Hill Climbing"

    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        max_iterations_per_restart = int(config.get("max_iterations_per_restart", max(500, 10 * formula.num_variables)))
        max_random_restarts = int(config.get("max_random_restarts", 10))
        random_seed = config.get("random_seed", None)
        legacy = hill_climb_with_random_restarts(
            formula,
            max_iterations_per_restart=max_iterations_per_restart,
            max_random_restarts=max_random_restarts,
            random_seed=random_seed,
        )
        return normalize_result(
            algorithm_name=self.algorithm_name,
            assignment=legacy.best_assignment,
            runtime_seconds=legacy.runtime_seconds,
            iterations_used=legacy.iterations_used,
            best_history=legacy.merit_history,
            runtime_history=legacy.runtime_history,
            parameter_summary={
                "max_iterations_per_restart": max_iterations_per_restart,
                "max_random_restarts": max_random_restarts,
                "random_seed": random_seed,
            },
            formula=formula,
        )


class SimulatedAnnealingSolver(BaseSolver):
    algorithm_name = "Simulated Annealing"

    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        max_iterations = int(config.get("max_iterations", max(2500, 45 * formula.num_variables)))
        initial_temperature = float(config.get("initial_temperature", 24.0))
        cooling_rate = float(config.get("cooling_rate", 0.9975))
        min_temperature = float(config.get("min_temperature", 0.0005))
        random_seed = config.get("random_seed", None)
        mode = str(config.get("mode", "enhanced"))
        restart_count = int(config.get("restart_count", 2))
        restart_initialization_strategy = str(config.get("restart_initialization_strategy", "polarity"))
        elite_restart_transfer = bool(config.get("elite_restart_transfer", True))
        elite_restart_perturbation = int(config.get("elite_restart_perturbation", max(2, formula.num_variables // 30)))
        unsatisfied_focus_probability = float(config.get("unsatisfied_focus_probability", 0.6))
        candidate_pool_size = int(config.get("candidate_pool_size", max(10, formula.num_variables // 10)))
        multi_bit_flip_probability = float(config.get("multi_bit_flip_probability", 0.04))
        max_multi_flip_size = int(config.get("max_multi_flip_size", 2))
        stagnation_multi_bit_boost = float(config.get("stagnation_multi_bit_boost", 0.15))
        stagnation_limit = int(config.get("stagnation_limit", max(30, int(0.7 * formula.num_variables))))
        reheat_multiplier = float(config.get("reheat_multiplier", 1.5))
        max_reheats = int(config.get("max_reheats", 4))
        adaptive_cooling = bool(config.get("adaptive_cooling", True))
        adaptive_cooling_bonus = float(config.get("adaptive_cooling_bonus", 0.0007))
        adaptive_cooling_penalty = float(config.get("adaptive_cooling_penalty", 0.0025))
        intensification_threshold = float(config.get("intensification_threshold", 0.98))
        intensification_focus_probability = float(config.get("intensification_focus_probability", 0.94))
        intensification_cooling_bonus = float(config.get("intensification_cooling_bonus", 0.0009))
        mini_hill_climb_steps = int(config.get("mini_hill_climb_steps", max(10, int(0.33 * formula.num_variables))))
        polarity_bias_strength = float(config.get("polarity_bias_strength", 0.7))
        history_bias_strength = float(config.get("history_bias_strength", 0.72))
        legacy = simulated_annealing_search(
            formula,
            max_iterations=max_iterations,
            initial_temperature=initial_temperature,
            cooling_rate=cooling_rate,
            min_temperature=min_temperature,
            random_seed=random_seed,
            mode=mode,
            restart_count=restart_count,
            restart_initialization_strategy=restart_initialization_strategy,
            elite_restart_transfer=elite_restart_transfer,
            elite_restart_perturbation=elite_restart_perturbation,
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
        )
        return normalize_result(
            algorithm_name=self.algorithm_name,
            assignment=legacy.best_assignment,
            runtime_seconds=legacy.runtime_seconds,
            iterations_used=legacy.iterations_used,
            best_history=legacy.merit_history,
            runtime_history=legacy.runtime_history,
            parameter_summary={
                "mode": mode,
                "max_iterations": max_iterations,
                "initial_temperature": initial_temperature,
                "cooling_rate": cooling_rate,
                "min_temperature": min_temperature,
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
                "iteration_of_best": legacy.iteration_of_best,
                "iteration_of_full_satisfaction": legacy.iteration_of_full_satisfaction,
                "reheat_count": legacy.reheat_count,
                "accepted_worse_moves": legacy.accepted_worse_moves,
                "accepted_better_moves": legacy.accepted_better_moves,
                "accepted_equal_moves": legacy.accepted_equal_moves,
                "number_of_unsatisfied_focused_moves": legacy.number_of_unsatisfied_focused_moves,
                "random_seed": random_seed,
            },
            formula=formula,
        )


class TabuSearchSolver(BaseSolver):
    algorithm_name = "Tabu Search"

    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        max_iterations = int(config.get("max_iterations", max(2000, 30 * formula.num_variables)))
        tabu_tenure = int(config.get("tabu_tenure", max(8, formula.num_variables // 10)))
        random_seed = config.get("random_seed", None)
        legacy = tabu_search_solve(
            formula,
            max_iterations=max_iterations,
            tabu_tenure=tabu_tenure,
            random_seed=random_seed,
        )
        return normalize_result(
            algorithm_name=self.algorithm_name,
            assignment=legacy.best_assignment,
            runtime_seconds=legacy.runtime_seconds,
            iterations_used=legacy.iterations_used,
            best_history=legacy.merit_history,
            runtime_history=legacy.runtime_history,
            parameter_summary={
                "max_iterations": max_iterations,
                "tabu_tenure": tabu_tenure,
                "random_seed": random_seed,
            },
            formula=formula,
        )


class HybridBsgoGaSolver(BaseSolver):
    algorithm_name = "Hybrid BSGO-GA"

    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        n = formula.num_variables
        population_size = int(config.get("population_size", max(36, min(90, max(60, n // 2)))))
        max_iterations = int(config.get("max_iterations", max(200, 2 * n)))
        crossover_rate = float(config.get("crossover_rate", 0.92))
        mutation_rate = float(config.get("mutation_rate", min(0.04, 2.0 / max(n, 1))))
        c_coefficient = float(config.get("c_coefficient", 0.72))
        w_inertia = float(config.get("w_inertia", 0.72))
        c_cognitive = float(config.get("c_cognitive", 1.35))
        c_social = float(config.get("c_social", 1.75))
        tournament_size = int(config.get("tournament_size", 3))
        stagnation_limit = int(config.get("stagnation_limit", 30))
        local_search_elite = bool(config.get("local_search_elite", True))
        annealing_temperature = float(config.get("annealing_temperature", 2.4))
        annealing_cooling = float(config.get("annealing_cooling", 0.994))
        annealing_trials = int(config.get("annealing_trials", 2))
        reheat_multiplier = float(config.get("reheat_multiplier", 1.4))
        random_seed = config.get("random_seed", None)
        legacy = hybrid_bsgo_ga_search(
            formula,
            population_size=population_size,
            max_iterations=max_iterations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            c_coefficient=c_coefficient,
            w_inertia=w_inertia,
            c_cognitive=c_cognitive,
            c_social=c_social,
            tournament_size=tournament_size,
            stagnation_limit=stagnation_limit,
            local_search_elite=local_search_elite,
            annealing_temperature=annealing_temperature,
            annealing_cooling=annealing_cooling,
            annealing_trials=annealing_trials,
            reheat_multiplier=reheat_multiplier,
            random_seed=random_seed,
        )
        return normalize_result(
            algorithm_name=self.algorithm_name,
            assignment=legacy.best_assignment,
            runtime_seconds=legacy.runtime_seconds,
            iterations_used=legacy.iterations_used,
            best_history=legacy.merit_history,
            runtime_history=legacy.runtime_history,
            parameter_summary={
                "population_size": population_size,
                "max_iterations": max_iterations,
                "crossover_rate": crossover_rate,
                "mutation_rate": mutation_rate,
                "c_coefficient": c_coefficient,
                "w_inertia": w_inertia,
                "c_cognitive": c_cognitive,
                "c_social": c_social,
                "tournament_size": tournament_size,
                "stagnation_limit": stagnation_limit,
                "local_search_elite": local_search_elite,
                "annealing_temperature": annealing_temperature,
                "annealing_cooling": annealing_cooling,
                "annealing_trials": annealing_trials,
                "reheat_multiplier": reheat_multiplier,
                "random_seed": random_seed,
            },
            formula=formula,
        )


def build_solver_registry() -> Dict[str, BaseSolver]:
    return {
        "hill_climbing": HillClimbingSolver(),
        "simulated_annealing": SimulatedAnnealingSolver(),
        "tabu_search": TabuSearchSolver(),
        "hybrid_bsgo_ga": HybridBsgoGaSolver(),
        "genetic_algorithm": GeneticAlgorithmSolver(),
        "memetic_ga_sa": MemeticGASASolver(),
        "binary_swarm_solver": BinarySwarmSolver(),
        "swarm_sa_solver": SwarmSASolver(),
    }
