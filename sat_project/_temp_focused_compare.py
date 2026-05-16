from __future__ import annotations
import json
from pathlib import Path
from statistics import mean

from sat_generator import load_instance_formula_from_file
from solvers.registry import build_solver_registry

base = Path('../data/instances')
instances = [
    '3sat_n50_r3.json',
    '3sat_n100_r4.3.json',
    '3sat_n100_r6.json',
]
solver_keys = [
    'hill_climbing',
    'simulated_annealing',
    'genetic_algorithm',
    'binary_swarm_solver',
    'hybrid_bsgo_ga',
]
seeds = [101, 202]
registry = build_solver_registry()
rows = []

for instance_name in instances:
    formula = load_instance_formula_from_file(base / instance_name)
    for solver_key in solver_keys:
        solver = registry[solver_key]
        for seed in seeds:
            result = solver.solve(formula, {'random_seed': seed})
            rows.append({
                'instance': instance_name,
                'solver_key': solver_key,
                'algorithm_name': result.algorithm_name,
                'seed': seed,
                'best_satisfied': result.best_satisfied_clauses,
                'total_clauses': result.total_clauses,
                'satisfaction_rate': result.satisfaction_rate,
                'runtime_seconds': result.runtime_seconds,
                'iterations_used': result.iterations_used,
                'fully_satisfied': result.fully_satisfied,
                'params': result.parameter_summary,
            })

by_instance = {}
for instance_name in instances:
    inst_rows = [r for r in rows if r['instance'] == instance_name]
    grouped = {}
    for row in inst_rows:
        grouped.setdefault(row['algorithm_name'], []).append(row)
    summary = []
    for algo_name, algo_rows in grouped.items():
        summary.append({
            'algorithm_name': algo_name,
            'mean_best_satisfied': mean(r['best_satisfied'] for r in algo_rows),
            'max_best_satisfied': max(r['best_satisfied'] for r in algo_rows),
            'mean_satisfaction_rate': mean(r['satisfaction_rate'] for r in algo_rows),
            'mean_runtime_seconds': mean(r['runtime_seconds'] for r in algo_rows),
            'mean_iterations_used': mean(r['iterations_used'] for r in algo_rows),
            'full_satisfy_count': sum(1 for r in algo_rows if r['fully_satisfied']),
        })
    summary.sort(key=lambda r: (-r['mean_satisfaction_rate'], r['mean_runtime_seconds']))
    by_instance[instance_name] = summary

overall_grouped = {}
for row in rows:
    overall_grouped.setdefault(row['algorithm_name'], []).append(row)

overall = []
for algo_name, algo_rows in overall_grouped.items():
    overall.append({
        'algorithm_name': algo_name,
        'mean_best_satisfied': mean(r['best_satisfied'] for r in algo_rows),
        'mean_satisfaction_rate': mean(r['satisfaction_rate'] for r in algo_rows),
        'mean_runtime_seconds': mean(r['runtime_seconds'] for r in algo_rows),
        'mean_iterations_used': mean(r['iterations_used'] for r in algo_rows),
        'full_satisfy_count': sum(1 for r in algo_rows if r['fully_satisfied']),
        'runs': len(algo_rows),
    })
overall.sort(key=lambda r: (-r['mean_satisfaction_rate'], r['mean_runtime_seconds']))

output = {
    'instances': instances,
    'seeds': seeds,
    'overall': overall,
    'by_instance': by_instance,
    'per_run': rows,
}

out_path = Path('results/comparison/focused_comparison_results.json')
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(output, indent=2), encoding='utf-8')
print(out_path.resolve())
print(json.dumps({'overall': overall, 'by_instance': by_instance}, indent=2))
