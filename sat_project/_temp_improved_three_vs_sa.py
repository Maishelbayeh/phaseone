from __future__ import annotations
import json
import re
from pathlib import Path
from statistics import mean

from sat_generator import load_instance_formula_from_file
from solvers.registry import build_solver_registry

ROOT = Path(__file__).resolve().parent
INSTANCE_DIR = ROOT.parent / 'data' / 'instances'
OUTPUT_PATH = ROOT / 'results' / 'comparison' / 'improved_three_vs_sa.json'
SOLVER_KEYS = ['simulated_annealing', 'genetic_algorithm', 'binary_swarm_solver', 'hybrid_bsgo_ga']
BASE_SEED = 101


def meta(instance_name: str):
    match = re.match(r'3sat_n(\d+)_r([0-9.]+)\.json', instance_name)
    return int(match.group(1)), float(match.group(2))


def solver_config(key: str, n: int, seed: int):
    if key == 'simulated_annealing':
        return {
            'max_iterations': max(3000, 50 * n),
            'initial_temperature': 12.0,
            'cooling_rate': 0.997,
            'min_temperature': 0.001,
            'random_seed': seed,
        }
    if key == 'genetic_algorithm':
        return {
            'population_size': 56 if n <= 200 else 64,
            'max_generations': 220 if n <= 200 else 240,
            'crossover_rate': 0.88,
            'mutation_rate': min(0.04, 2.0 / max(n, 1)),
            'elite_count': 2,
            'crossover_mode': 'two_point',
            'tournament_size': 3,
            'local_search_every': 5,
            'annealing_temperature': 2.2,
            'annealing_cooling': 0.992,
            'annealing_trials': 2,
            'stagnation_limit': 24,
            'reheat_multiplier': 1.5,
            'random_seed': seed,
        }
    if key == 'binary_swarm_solver':
        return {
            'population_size': 60 if n <= 200 else 64,
            'max_iterations': 360 if n <= 200 else 300,
            'w_inertia': 0.72,
            'c_cognitive': 1.6,
            'c_social': 1.8,
            'local_search_every': 8,
            'stagnation_limit': 45 if n <= 200 else 36,
            'max_restarts': 3 if n <= 200 else 2,
            'annealing_temperature': 2.4,
            'annealing_cooling': 0.995,
            'annealing_trials': 2,
            'reheat_multiplier': 1.35,
            'random_seed': seed,
        }
    if key == 'hybrid_bsgo_ga':
        return {
            'population_size': 60 if n <= 200 else 64,
            'max_iterations': 250 if n <= 200 else 220,
            'crossover_rate': 0.92,
            'mutation_rate': min(0.04, 2.0 / max(n, 1)),
            'c_coefficient': 0.72,
            'w_inertia': 0.72,
            'c_cognitive': 1.35,
            'c_social': 1.75,
            'tournament_size': 3,
            'stagnation_limit': 30,
            'local_search_elite': True,
            'annealing_temperature': 2.4,
            'annealing_cooling': 0.994,
            'annealing_trials': 2,
            'reheat_multiplier': 1.4,
            'random_seed': seed,
        }
    return {'random_seed': seed}


registry = build_solver_registry()
per_run = []
for instance_path in sorted(INSTANCE_DIR.glob('3sat_*.json')):
    formula = load_instance_formula_from_file(instance_path)
    n, ratio = meta(instance_path.name)
    for offset, key in enumerate(SOLVER_KEYS):
        seed = BASE_SEED + offset * 100003 + n * 37 + int(ratio * 100)
        result = registry[key].solve(formula, solver_config(key, n, seed))
        row = {
            'instance': instance_path.name,
            'n': n,
            'ratio': ratio,
            'solver_key': key,
            'algorithm_name': result.algorithm_name,
            'best_satisfied': result.best_satisfied_clauses,
            'total_clauses': result.total_clauses,
            'satisfaction_rate': result.satisfaction_rate,
            'runtime_seconds': result.runtime_seconds,
            'iterations_used': result.iterations_used,
            'fully_satisfied': result.fully_satisfied,
            'parameter_summary': result.parameter_summary,
        }
        per_run.append(row)
        print(f"{instance_path.name} | {result.algorithm_name} | {result.best_satisfied_clauses}/{result.total_clauses} | {result.runtime_seconds:.3f}s", flush=True)


def summarize(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(row['algorithm_name'], []).append(row)
    summary = []
    for algorithm_name, algo_rows in grouped.items():
        summary.append({
            'algorithm_name': algorithm_name,
            'runs': len(algo_rows),
            'mean_best_satisfied': mean(r['best_satisfied'] for r in algo_rows),
            'mean_satisfaction_rate': mean(r['satisfaction_rate'] for r in algo_rows),
            'mean_runtime_seconds': mean(r['runtime_seconds'] for r in algo_rows),
            'max_best_satisfied': max(r['best_satisfied'] for r in algo_rows),
            'full_satisfy_count': sum(1 for r in algo_rows if r['fully_satisfied']),
        })
    summary.sort(key=lambda r: (-r['mean_satisfaction_rate'], r['mean_runtime_seconds']))
    return summary

by_ratio = {}
for ratio in sorted({row['ratio'] for row in per_run}):
    by_ratio[str(ratio)] = summarize([row for row in per_run if row['ratio'] == ratio])

by_n = {}
for n in sorted({row['n'] for row in per_run}):
    by_n[str(n)] = summarize([row for row in per_run if row['n'] == n])

output = {
    'overall': summarize(per_run),
    'by_ratio': by_ratio,
    'by_n': by_n,
    'per_run': per_run,
}
OUTPUT_PATH.write_text(json.dumps(output, indent=2), encoding='utf-8')
print(f"SAVED {OUTPUT_PATH}")
