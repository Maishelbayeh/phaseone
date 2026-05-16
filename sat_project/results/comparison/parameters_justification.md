# Parameter Justification (Implementation-Level)

This document explains how parameters were selected for each MAX-SAT solver in this project.

## Selection Principles

- Prioritize high solution quality while keeping runtime practical.
- Scale core budget parameters with instance size (`n`) where appropriate.
- Use algorithm-consistent defaults that are stable and reproducible.
- Treat these as implementation-level settings, not globally optimal hyperparameters.

## Solver-Wise Parameter Choices

| Algorithm | Parameter | Default / Rule | Rationale | Expected Effect |
|---|---|---|---|---|
| Hill Climbing | `max_iterations_per_restart` | `max(500, 10n)` | Gives each restart enough local search depth; scales with variables. | Improves local exploitation; runtime rises roughly linearly. |
| Hill Climbing | `max_random_restarts` | `10` | Mitigates local-optima trapping via diversification. | Better quality from exploration; runtime increases with restarts. |
| Simulated Annealing | `max_iterations` | `max(2000, 30n)` | Supports gradual cooling and enough accepted transitions. | Better quality with more iterations; higher runtime. |
| Simulated Annealing | `initial_temperature` | `10.0` | Allows early uphill moves to escape poor basins. | Too low becomes greedy; too high becomes noisy. |
| Simulated Annealing | `cooling_rate` | `0.995` | Balanced cooling speed for quality/runtime. | Slower cooling improves quality but costs time. |
| Simulated Annealing | `min_temperature` | `0.01` | Practical stop point near greedy end-game. | Lower threshold can improve refinement with extra cost. |
| Tabu Search | `max_iterations` | `max(2000, 30n)` | Provides enough trajectory length with tabu constraints. | More search opportunity; increased runtime. |
| Tabu Search | `tabu_tenure` | `max(8, n/10)` (int) | Prevents short cycles without over-blocking moves. | Too small cycles; too large over-constrains. |
| Hybrid BSGO-GA | `population_size` | `max(30, min(90, n))` | Preserves diversity while controlling overhead. | Larger `P` can improve quality; increases runtime. |
| Hybrid BSGO-GA | `max_iterations` | `max(180, 2n)` | Enough improving + evolutionary cycles. | Better convergence, with extra runtime. |
| Hybrid BSGO-GA | `crossover_rate` | `0.85` | Strong recombination for exploitation. | Faster mixing of patterns; too high can disrupt stability. |
| Hybrid BSGO-GA | `mutation_rate` | `min(0.04, 2/n)` | Dimension-aware mutation (`O(1/n)`). | Keeps diversity without excessive randomization. |
| Hybrid BSGO-GA | `c_coefficient` | `0.72` | Moderate swarm/social step magnitude. | High values can destabilize; low values can stagnate. |
| Genetic Algorithm | `population_size` | scaled ~`40..96` | Balances diversity and compute cost in binary search space. | Larger population improves exploration at runtime cost. |
| Genetic Algorithm | `max_generations` | scaled ~`180..2n` | Provides enough evolutionary refinement cycles. | More generations improve quality up to plateau. |
| Genetic Algorithm | `crossover_rate` | `0.90` | Encourages recombination of useful building blocks. | Strong mixing and often faster quality gains. |
| Genetic Algorithm | `mutation_rate` | `min(0.03, 2/n)` | Controls bit-flip noise as dimensionality grows. | Maintains diversity while preserving good schemata. |
| Genetic Algorithm | `elite_count` | `2` | Prevents losing best individuals. | Improves stability and best-so-far monotonicity. |
| Genetic Algorithm | `tournament_size` | `3` | Moderate selection pressure. | Good balance between quality pressure and diversity. |
| Genetic Algorithm | `crossover_mode` | `two_point` (supports one-point) | Often preserves medium-length structures better. | Can improve offspring quality on SAT landscapes. |
| Binary Swarm (BSGO) | `population_size` | scaled ~`36..96` (tab default `42`) | Provides swarm diversity for pure non-hybrid exploration. | Larger swarm improves coverage; higher runtime. |
| Binary Swarm (BSGO) | `max_iterations` | scaled ~`180..2n` (tab default `260`) | Ensures enough improving-phase steps for convergence. | Better quality with longer runs; slower execution. |
| Binary Swarm (BSGO) | `c_parameter` | `0.72` | Stable and sufficiently strong update behavior. | Too high may oscillate; too low may slow progress. |

## Suggested Paper Wording

We selected solver parameters using an implementation-level quality-runtime tradeoff strategy. Iteration and population budgets scale with instance size where needed, while stochastic-control parameters (e.g., cooling rate, tabu tenure, mutation rate, and swarm coefficient) are set to stable mid-range values. Mutation is dimension-aware (`O(1/n)`) to preserve diversity without overwhelming exploitation. These choices are reproducible practical defaults and are not claimed to be globally optimal.
