# Final Results Analysis

## What this folder contains

- `available_benchmark_snapshot.csv`: current no-rerun snapshot built from the latest completed benchmark outputs.
- Copied legacy comparison artifacts from `results/comparison/`.
- New plots in `plots/` that compare the five tuned algorithms across the available size and ratio points.

## Important scope note

- This package was built **without rerunning** the benchmark suite.
- The new size-by-ratio plots use the latest available snapshot points for:
  - `n = 100, 150, 200` at `r = 3, 4.3, 6`
  - `n = 500` at `r = 3`
- Existing legacy comparison files still provide multi-run data and extra plots, but they were produced from older saved runs.

## Main picture

- `Simulated Annealing` is the strongest overall solver in the available data.
- `Genetic Algorithm` is the best population-based standalone method.
- `Hill Climbing` is a solid baseline but scales badly as `n` grows because it evaluates many one-bit neighbors.
- `Binary Swarm (BSGO)` improved over older versions, but it is still usually behind SA and GA in the current project.
- `Hybrid BSGO-GA` is competitive in solution quality, but it is much more expensive in runtime and still does not clearly dominate GA.

## Why Hybrid is not yet combining the best of GA and BSGO

- Yes: the current evidence says the hybrid still needs improvement.
- The hybrid is **not** consistently stronger than both parents.
- In the available snapshot:
  - it is usually slower than GA by a large margin,
  - it often fails to beat SA on quality,
  - and it does not clearly inherit the strongest exploitation behavior from GA plus the strongest guided movement from the improved BSGO.

## Interpreting the plots

- `r3_satisfaction_vs_n.png`: easy density; almost all methods are strong, but runtime differences become very visible.
- `r4_3_satisfaction_vs_n.png`: near the phase transition; this is where solver differences matter most.
- `r6_satisfaction_vs_n.png`: dense hard cases; SA and GA separate more clearly from HC and BSGO.
- `snapshot_runtime_vs_satisfaction.png`: global quality-vs-cost picture from the available snapshot.
- `snapshot_gap_from_best.png`: per-instance distance from the best observed method on each available instance.

## Suggested conclusion

- Recommend `Simulated Annealing` as the default general-purpose solver.
- Recommend `Genetic Algorithm` as the main evolutionary/population alternative.
- Keep `Hill Climbing` as a baseline and explanatory algorithm.
- Treat `Binary Swarm (BSGO)` and `Hybrid BSGO-GA` as research/experimental methods that still need another tuning pass.
