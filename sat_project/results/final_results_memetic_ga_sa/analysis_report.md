# Memetic GA-SA Results Analysis

## Scope

- Benchmark file: `memetic_vs_sa_ga_hybrid_medium.json`
- Instances: `n = 100, 150, 200`
- Ratios: `r = 3.0, 4.3, 6.0`
- Compared solvers:
  - `Simulated Annealing`
  - `Genetic Algorithm`
  - `Memetic GA-SA`
  - `Hybrid BSGO-GA`

## Main conclusion

- `Memetic GA-SA` is the best solver in this benchmark by solution quality.
- `Simulated Annealing` is still by far the best solver by runtime efficiency.
- `Memetic GA-SA` is clearly better than plain `GA`.
- `Memetic GA-SA` is also clearly better than the current `Hybrid BSGO-GA`.

## Overall ranking

- `Memetic GA-SA`: mean satisfaction `99.283%`, mean runtime `39.34s`, full satisfactions `3/9`
- `Simulated Annealing`: mean satisfaction `99.097%`, mean runtime `1.89s`, full satisfactions `1/9`
- `Genetic Algorithm`: mean satisfaction `98.575%`, mean runtime `25.80s`
- `Hybrid BSGO-GA`: mean satisfaction `98.353%`, mean runtime `50.15s`

## What improved compared with the old heavy hybrid benchmark

- Old saved `Hybrid BSGO-GA` mean satisfaction: `98.353%`
- New `Memetic GA-SA` mean satisfaction: `99.283%`
- Old saved `Hybrid BSGO-GA` mean runtime: `70.39s`
- New `Memetic GA-SA` mean runtime: `39.34s`
- This means the new memetic design improves both quality and runtime compared with the old heavy hybrid snapshot.

## Why Memetic GA-SA works better

- `GA` provides population diversity and recombination.
- `SA` provides strong local refinement and very effective escape from weak local structure.
- Refining only top elites every few generations keeps the method memetic without paying the cost of refining the entire population every generation.
- This selective design is much lighter than the previous `Hybrid BSGO-GA`.

## Why SA is still important

- `Simulated Annealing` is still the best practical default when runtime matters.
- The quality gap between `Memetic GA-SA` and `SA` is real, but small compared with the runtime gap.
- On hard instances the memetic solver often gains a few additional satisfied clauses, but it pays tens of seconds more.

## Swarm status

- `Binary Swarm (BSGO)` is not included in this new benchmark because the focus here is the new memetic solver.
- Based on the earlier saved benchmark snapshot, swarm is still behind `SA`, `GA`, and now also behind `Memetic GA-SA`.
- So no, the current swarm is not yet the strongest version you can reach.

## Recommended use

- Use `Simulated Annealing` when you want the best speed and still excellent quality.
- Use `Memetic GA-SA` when you want the best solution quality and can afford more runtime.
- Use `Genetic Algorithm` as the simpler population baseline.
- Treat `Hybrid BSGO-GA` as an older heavy hybrid that is now outperformed by the memetic solver.
