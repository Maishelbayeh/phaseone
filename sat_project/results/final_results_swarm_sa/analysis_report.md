# SA / GA / Swarm / Hybrids Analysis

## Scope

- Benchmark file: `sa_ga_swarm_memetic_swarmsa_medium.json`
- Instances: `n = 100, 150, 200`
- Ratios: `r = 3.0, 4.3, 6.0`
- Compared solvers:
  - `Simulated Annealing`
  - `Genetic Algorithm`
  - `Binary Swarm (BSGO)`
  - `Memetic GA-SA`
  - `Swarm-SA Hybrid`

## Main conclusions

- `Simulated Annealing` remains the fastest strong solver and the best practical default.
- The tuned `Memetic GA-SA` is much faster than its older heavy version because the expensive step was repeated bounded SA on multiple elites with a large fixed budget.
- The new memetic version reduces cost by using adaptive SA budgets, early stopping inside SA, and restart-style diversity recovery.
- `Swarm-SA Hybrid` is the explicit swarm-plus-SA method requested for comparison.
- The new `Swarm-SA Hybrid` is stronger than plain swarm in local intensification, but it still needs to justify its extra cost against `SA` and the tuned memetic solver.

## Overall ranking

- `Simulated Annealing`: mean satisfaction `99.097%`, mean runtime `2.13s`, mean iterations `2928.1`
- `Genetic Algorithm`: mean satisfaction `98.575%`, mean runtime `30.93s`, mean iterations `220.0`
- `Binary Swarm (BSGO)`: mean satisfaction `98.161%`, mean runtime `24.10s`, mean iterations `219.0`
- `Memetic GA-SA`: mean satisfaction `98.723%`, mean runtime `11.66s`, mean iterations `203.3`
- `Swarm-SA Hybrid`: mean satisfaction `97.851%`, mean runtime `16.33s`, mean iterations `220.0`

## Why Memetic GA-SA time dropped

- The earlier heavy version paid too much for elite refinement:
  - too many SA calls,
  - too many SA iterations per call,
  - too little early stopping once refinement stopped improving.
- The tuned version reduces runtime using:
  - adaptive SA iteration budgets,
  - SA patience-based early stop,
  - fewer useful refinement calls instead of always spending the full budget,
  - controlled population refresh when the GA stalls.

## Why Swarm-SA is separate from Binary Swarm

- `Binary Swarm (BSGO)` stays as the tuned swarm baseline.
- `Swarm-SA Hybrid` uses a swarm outer loop with explicit periodic SA refinement on elite particles.
- This makes the comparison clearer:
  - `Swarm` = tuned population movement baseline,
  - `Swarm-SA` = swarm plus stronger local refinement.

## Recommended use

- Use `Simulated Annealing` when you want the best speed and still high solution quality.
- Use `Memetic GA-SA` when you want a stronger GA+SA hybrid without the old runtime explosion.
- Use `Binary Swarm (BSGO)` as the improved swarm baseline.
- Use `Swarm-SA Hybrid` when you specifically want to study swarm plus local annealing, not when you only want the fastest practical solver.
