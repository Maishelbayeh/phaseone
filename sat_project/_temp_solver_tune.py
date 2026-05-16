from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from hill_climbing import hill_climb_with_random_restarts
from simulated_annealing import simulated_annealing_search
from sat_generator import load_instance_formula_from_file
from solvers.binary_swarm_solver import BinarySwarmSolver
from solvers.genetic_algorithm import GeneticAlgorithmSolver


BASE = Path(__file__).resolve().parent.parent / "data" / "instances"
INSTANCES = [
    "3sat_n50_r3.json",
    "3sat_n100_r4.3.json",
    "3sat_n100_r6.json",
]
SEEDS = [101, 202]


def run_hc():
    configs = [
        ("hc_current", {"max_iterations_per_restart": 1000, "max_random_restarts": 10}),
        ("hc_more_restarts", {"max_iterations_per_restart": 1200, "max_random_restarts": 16}),
        ("hc_deeper", {"max_iterations_per_restart": 1600, "max_random_restarts": 12}),
        ("hc_balanced", {"max_iterations_per_restart": 1400, "max_random_restarts": 14}),
    ]
    return _eval_hc(configs)


def run_sa():
    configs = [
        ("sa_current", {"max_iterations": 3000, "initial_temperature": 10.0, "cooling_rate": 0.995, "min_temperature": 0.01}),
        ("sa_slowcool", {"max_iterations": 5000, "initial_temperature": 12.0, "cooling_rate": 0.997, "min_temperature": 0.001}),
        ("sa_hotter", {"max_iterations": 6000, "initial_temperature": 20.0, "cooling_rate": 0.998, "min_temperature": 0.001}),
        ("sa_balanced", {"max_iterations": 4500, "initial_temperature": 15.0, "cooling_rate": 0.997, "min_temperature": 0.002}),
    ]
    return _eval_sa(configs)


def run_ga():
    configs = [
        ("ga_currentish", {"population_size": 56, "max_generations": 220, "crossover_rate": 0.88, "mutation_rate": 0.02, "elite_count": 2, "crossover_mode": "two_point", "tournament_size": 3}),
        ("ga_more_pop", {"population_size": 72, "max_generations": 260, "crossover_rate": 0.92, "mutation_rate": 0.02, "elite_count": 2, "crossover_mode": "two_point", "tournament_size": 3}),
        ("ga_more_elite", {"population_size": 72, "max_generations": 280, "crossover_rate": 0.92, "mutation_rate": 0.015, "elite_count": 3, "crossover_mode": "two_point", "tournament_size": 4}),
        ("ga_balanced", {"population_size": 64, "max_generations": 260, "crossover_rate": 0.90, "mutation_rate": 0.02, "elite_count": 2, "crossover_mode": "two_point", "tournament_size": 3}),
    ]
    return _eval_ga(configs)


def run_bsgo():
    configs = [
        ("bsgo_current", {"population_size": 50, "max_iterations": 300, "c_parameter": 0.7}),
        ("bsgo_more_social", {"population_size": 60, "max_iterations": 360, "w_inertia": 0.72, "c_cognitive": 1.6, "c_social": 1.8, "local_search_every": 8, "stagnation_limit": 45, "max_restarts": 3}),
        ("bsgo_balanced", {"population_size": 56, "max_iterations": 340, "w_inertia": 0.68, "c_cognitive": 1.4, "c_social": 1.7, "local_search_every": 8, "stagnation_limit": 40, "max_restarts": 3}),
        ("bsgo_deeper", {"population_size": 64, "max_iterations": 400, "w_inertia": 0.70, "c_cognitive": 1.5, "c_social": 1.8, "local_search_every": 6, "stagnation_limit": 50, "max_restarts": 4}),
    ]
    return _eval_bsgo(configs)


def _summarize(rows):
    grouped = {}
    for name, rate, runtime in rows:
        grouped.setdefault(name, []).append((rate, runtime))
    summary = []
    for name, values in grouped.items():
        avg_rate = mean(v[0] for v in values)
        avg_runtime = mean(v[1] for v in values)
        score = avg_rate - 0.015 * avg_runtime
        summary.append(
            {
                "config": name,
                "avg_rate": round(avg_rate, 6),
                "avg_runtime": round(avg_runtime, 6),
                "score": round(score, 6),
            }
        )
    summary.sort(key=lambda item: (-item["score"], -item["avg_rate"], item["avg_runtime"]))
    return summary


def _eval_hc(configs):
    rows = []
    for instance in INSTANCES:
        formula = load_instance_formula_from_file(BASE / instance)
        for seed in SEEDS:
            for name, cfg in configs:
                r = hill_climb_with_random_restarts(formula, random_seed=seed, **cfg)
                rows.append((name, r.best_merit / r.total_clauses, r.runtime_seconds))
    return _summarize(rows)


def _eval_sa(configs):
    rows = []
    for instance in INSTANCES:
        formula = load_instance_formula_from_file(BASE / instance)
        for seed in SEEDS:
            for name, cfg in configs:
                r = simulated_annealing_search(formula, random_seed=seed, **cfg)
                rows.append((name, r.best_merit / r.total_clauses, r.runtime_seconds))
    return _summarize(rows)


def _eval_ga(configs):
    rows = []
    solver = GeneticAlgorithmSolver()
    for instance in INSTANCES:
        formula = load_instance_formula_from_file(BASE / instance)
        for seed in SEEDS:
            for name, cfg in configs:
                r = solver.solve(formula, {**cfg, "random_seed": seed})
                rows.append((name, r.best_satisfied_clauses / r.total_clauses, r.runtime_seconds))
    return _summarize(rows)


def _eval_bsgo(configs):
    rows = []
    solver = BinarySwarmSolver()
    for instance in INSTANCES:
        formula = load_instance_formula_from_file(BASE / instance)
        for seed in SEEDS:
            for name, cfg in configs:
                r = solver.solve(formula, {**cfg, "random_seed": seed})
                rows.append((name, r.best_satisfied_clauses / r.total_clauses, r.runtime_seconds))
    return _summarize(rows)


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "hill_climbing": run_hc(),
                "simulated_annealing": run_sa(),
                "genetic_algorithm": run_ga(),
                "binary_swarm": run_bsgo(),
            },
            indent=2,
        )
    )
