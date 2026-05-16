# Solver Comparison Report

- Instance: `3sat_n100_r3.json`
- Total run records: 30

## Main Findings

1. **Best solution quality**: Tabu Search (mean satisfaction rate=1.0000).
2. **Fastest solver**: Simulated Annealing (mean runtime=0.1902 s).
3. **Best speed-quality tradeoff**: Simulated Annealing.
4. **Standalone GA vs Hybrid BSGO-GA**: Genetic Algorithm: mean satisfaction=0.9980, mean runtime=2.4588s; Hybrid BSGO-GA: mean satisfaction=0.9967, mean runtime=6.9673s.
5. **Standalone Swarm vs Hybrid BSGO-GA**: Binary Swarm (BSGO): mean satisfaction=0.9520, mean runtime=4.3062s; Hybrid BSGO-GA: mean satisfaction=0.9967, mean runtime=6.9673s.
6. **Runtime scaling observations**: Empirical scaling (log-log runtime slope) range: 1.406 to 4.032 across compared solvers.
7. **Estimated time complexity (implementation-level)** is listed in `complexity_summary.csv` and should be cited as practical/implementation estimates, not formal bounds.

## Suggested Paper Wording

In our implementation-level comparison on MAX-SAT instances, the algorithms exhibit a clear quality-runtime tradeoff. Population-based methods generally improve satisfaction quality at higher computational cost, while trajectory-based methods remain faster. The standalone Genetic Algorithm and pure binary swarm baseline allow direct attribution of gains from hybridization in Hybrid BSGO-GA. We report both estimated implementation-level complexity and empirical runtime scaling with increasing instance size to avoid overstating formal asymptotic claims.

## Best Parameters Snapshot

- **Hill Climbing**: seed=457 params={'max_iterations_per_restart': 1200, 'max_random_restarts': 10, 'random_seed': 457}
- **Simulated Annealing**: seed=457 params={'max_iterations': 2800, 'initial_temperature': 10.0, 'cooling_rate': 0.995, 'min_temperature': 0.01, 'random_seed': 457}
- **Tabu Search**: seed=456 params={'max_iterations': 2800, 'tabu_tenure': 10, 'random_seed': 456}
- **Hybrid BSGO-GA**: seed=456 params={'population_size': 90, 'max_iterations': 200, 'crossover_rate': 0.85, 'mutation_rate': 0.02, 'c_coefficient': 0.72, 'random_seed': 456}
- **Genetic Algorithm**: seed=456 params={'population_size': 96, 'max_generations': 200, 'crossover_rate': 0.9, 'mutation_rate': 0.02, 'elite_count': 2, 'crossover_mode': 'two_point', 'tournament_size': 3, 'random_seed': 456}
- **Binary Swarm (BSGO)**: seed=459 params={'population_size': 96, 'max_iterations': 200, 'c_parameter': 0.72, 'random_seed': 459, 'method': 'pure_binary_sgo'}

## Summary Statistics

| Solver | Mean Sat Rate | Best Sat Rate | Mean Runtime (s) | Rank |
|---|---:|---:|---:|---:|
| Tabu Search | 1.0000 | 1.0000 | 2.1151 | 1 |
| Simulated Annealing | 0.9993 | 1.0000 | 0.1902 | 2 |
| Genetic Algorithm | 0.9980 | 1.0000 | 2.4588 | 3 |
| Hill Climbing | 0.9967 | 1.0000 | 2.4984 | 4 |
| Hybrid BSGO-GA | 0.9967 | 0.9967 | 6.9673 | 5 |
| Binary Swarm (BSGO) | 0.9520 | 0.9600 | 4.3062 | 6 |

## Complexity Notes

| Solver | Estimated complexity | Empirical slope | Fit (R^2) |
|---|---|---:|---:|
| Hill Climbing | O(I * n * m) with random restarts folded into I | 2.935 | 0.999 |
| Simulated Annealing | O(I * m) | 1.406 | 0.964 |
| Tabu Search | O(I * n * m) | 4.032 | 0.992 |
| Hybrid BSGO-GA | O(I * P * n * m) | 2.024 | 0.995 |
| Genetic Algorithm | O(I * P * m) | 1.865 | 0.998 |
| Binary Swarm (BSGO) | O(I * P * m) | 1.901 | 0.999 |
