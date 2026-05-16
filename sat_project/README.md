# 3-SAT / MAX-SAT Metaheuristics — Educational Project

## Overview

This repository implements a **random 3-SAT generator** and multiple **MAX-SAT metaheuristics** that maximize the number of satisfied clauses. There is **no** external SAT oracle: evaluation and search are implemented in pure Python.

The main solvers currently documented and used in the project are:

- **Hill Climbing (HC)** with random restarts
- **Simulated Annealing (SA)**
- **Genetic Algorithm (GA)**
- **Memetic GA-SA**
- **Binary Swarm Optimization (BSGO)**
- **Swarm-SA Hybrid**
- **Hybrid BSGO-GA**

The coursework grid sweeps:

- **Variables:** `n ∈ {50, 100, …, 500}` (step 50)
- **Clause density:** `m/n ∈ {3.0, 4.3, 6.0}` with `m = round(ratio · n)`

For each setting, the code records satisfied-clause count, full satisfaction flag, iterations, runtime, and optional assignment data.

## SAT, 3-SAT, and CNF (short)

- **SAT:** Given a Boolean formula, is there an assignment of variables making the formula **True**?
- **CNF (Conjunctive Normal Form):** The formula is an **AND of clauses**; each clause is an **OR of literals**.
- **3-SAT:** Each clause has **exactly three literals** (here, on **distinct** variables).

A **literal** is a variable or its negation. A clause is **satisfied** if **at least one** literal is True. The formula is **fully satisfied** if **every** clause is satisfied.

## Project layout

| File | Role |
|------|------|
| `main.py` | Demo run, optional full experiment via `--full`, or GUI via `--gui` |
| `gui.py` | Desktop control panel (Tkinter) for parameters and batch runs |
| `utils.py` | Shared types: `Literal`, `CNFFormula`, validation helpers |
| `sat_generator.py` | Random 3-SAT instance generation with seeds |
| `evaluator.py` | Truth evaluation, satisfied-clause counts, merit / rates |
| `hill_climbing.py` | Hill climbing + **random restarts** + tie-breaking |
| `simulated_annealing.py` | Simulated annealing local search |
| `solvers/genetic_algorithm.py` | Standalone genetic algorithm solver |
| `solvers/memetic_ga_sa.py` | Memetic GA with bounded SA refinement on elites |
| `solvers/binary_swarm_solver.py` | Standalone binary swarm / binary PSO-style solver |
| `solvers/swarm_sa_solver.py` | Swarm + SA hybrid with periodic SA refinement on elite particles |
| `hybrid_bsgo_ga.py` | Hybrid BSGO + GA solver |
| `experiments.py` | Batch runner, CSV/JSON export |
| `plotting.py` | Convergence + runtime-vs-`n` figures |
| `results/data/` | Saved `experiment_results.csv` / `.json` |
| `results/plots/` | Output PNG plots |

## How to run

Create a virtual environment (recommended), install dependencies, then run from the `sat_project` directory so imports resolve.

```bash
cd sat_project
pip install -r requirements.txt
python main.py
```

- **GUI (parameters + batch):** opens a window to edit `n`, densities, seeds, iteration limits, and to run the full grid with a progress bar:

```bash
python gui.py
```

or:

```bash
python main.py --gui
```

- **Demo only (fast):** prints a small-instance summary and writes `results/plots/demo_convergence.png`.
- **Full grid + complexity plot:**

```bash
python main.py --full
```

This writes:

- `results/data/experiment_results.csv`
- `results/data/experiment_results.json`
- `results/plots/runtime_vs_num_variables.png`

(See also the demo convergence figure path printed in the console.)

## Merit (fitness) and plots

- **Merit** is the **number of satisfied clauses** under the current best assignment.
- **Convergence plot:** step index vs. best merit so far (initial point + updates after improving flips / restart snapshots).
- **Complexity plot:** `n` on the x-axis, average runtime per `(n, ratio)` cell on the y-axis, **one curve per density ratio** (`3`, `4.3`, `6`).

Runtime is **empirical wall-clock** (`time.perf_counter`); it reflects Python loops and instance size, not asymptotic notation alone.

## Algorithm notes

- **Hill Climbing** starts from a random assignment, repeatedly **flips one variable** that **strictly increases** merit, and stops at a **local optimum**, full satisfaction, or an iteration budget. **Random restarts** reduce dependence on one unlucky start. Ties among equally good improving flips are broken uniformly at random.
- **Simulated Annealing** also uses single-variable flips, but it may accept a worse move with a probability controlled by temperature. This helps it escape local optima.
- **Genetic Algorithm** evolves a population of truth assignments using tournament selection, crossover, mutation, and elitism.
- **Memetic GA-SA** keeps the GA population for exploration, then periodically applies bounded SA only to the top few elite individuals. This adds fast local refinement without the heavy cost of refining the whole population every generation.
- **Binary Swarm (BSGO)** uses a binary PSO-style update with particle memory, global-best guidance, and periodic local search refinement.
- **Swarm-SA Hybrid** keeps a swarm outer loop, then applies explicit bounded SA to the top particle set every few iterations. This is a more direct swarm-plus-SA design than the baseline swarm solver.
- **Hybrid BSGO-GA** combines a swarm-style improving phase with a GA-style reproduction phase.

## Recent Changes And Why

This section summarizes the recent solver-tuning changes made in the codebase and the reason for each one.

### 1. Hill Climbing

**What changed**

- The solver logic in `hill_climbing.py` was **not changed**.
- The main default values used across the project were kept at:
  - `max_iterations_per_restart = 1000`
  - `max_random_restarts = 10`

**Why**

- Focused benchmark runs on representative instances showed that larger restart counts or deeper per-restart budgets usually **did not improve the final merit** on the tested hard cases.
- Higher values mostly increased runtime:
  - On `3sat_n100_r4.3.json`, `423/430` was reached by the old and deeper settings, but the original setting was faster.
  - On `3sat_n100_r6.json`, `583/600` was again matched by deeper settings, but with significantly more runtime.
- Because of that, the existing Hill Climbing defaults already gave the best **quality/runtime tradeoff** among the tested options.

### 2. Simulated Annealing

**What changed**

- Updated defaults in `simulated_annealing.py` and project entry points to:
  - `max_iterations = max(3000, 50 * n)`
  - `initial_temperature = 12.0`
  - `cooling_rate = 0.997`
  - `min_temperature = 0.001`

**Why**

- The older schedule was faster, but it cooled too aggressively on harder instances.
- The tuned schedule keeps the search exploratory for longer and improves end-game refinement.
- Benchmark signal:
  - On `3sat_n100_r6.json`, old-style settings gave `587/600`, while the tuned schedule reached `589/600`.
  - On `3sat_n100_r4.3.json`, the tuned schedule improved some seeds from the mid-`424-426` range and remained competitive.
- This was the clearest improvement among the single-solution methods, so the README and defaults were updated accordingly.

### 3. Genetic Algorithm

**What changed**

- The algorithm implementation in `solvers/genetic_algorithm.py` was **not changed**.
- After testing multiple variants, the practical defaults were kept close to the original:
  - `population_size = 56`
  - `max_generations = 220`
  - `crossover_rate = 0.88`
  - `mutation_rate = min(0.04, 2 / n)`
  - `elite_count = 2`
  - `tournament_size = 3`
  - `crossover_mode = two_point`

**Why**

- Larger populations and more generations were tested, but they did not consistently improve results.
- Example outcomes:
  - On `3sat_n100_r4.3.json`, the current-style GA reached `426/430`, while some larger variants dropped to `424/430`.
  - On `3sat_n100_r6.json`, the current default tied the best tested merit at `587/600` with lower runtime than more expensive variants.
- So the current GA settings remained the strongest overall tested configuration.

### 4. Binary Swarm Optimization

**What changed**

- The upgraded `solvers/binary_swarm_solver.py` now uses a stronger default configuration:
  - `population_size = 60`
  - `max_iterations = 360`
  - `w_inertia = 0.72`
  - `c_cognitive = 1.6`
  - `c_social = 1.8`
  - `local_search_every = 8`
  - `stagnation_limit = 45`
  - `max_restarts = 3`
- Backward compatibility with the old `c_parameter` input was kept, but it now maps to the inertia-style weight.

**Why**

- On harder instances, the stronger social/cognitive pull and slightly larger swarm improved quality.
- Benchmark signal:
  - On `3sat_n100_r4.3.json`, the old-style setting produced `417/430`, while the tuned setting reached `423/430`.
  - On another seed of the same instance, the old setting gave `419/430`, while the tuned setting reached `421/430`.
  - On `3sat_n100_r6.json`, the old setting gave `580/600`, while the tuned setting reached `587/600`.
- The cost is a higher runtime, but the quality gain on harder cases was large enough to justify the change.

### 5. Registry, GUI, And Comparison Defaults

**What changed**

- The following files were aligned so they all use the tuned defaults consistently:
  - `solvers/registry.py`
  - `gui.py`
  - `compare_all_solvers.py`
  - `complexity_analysis.py`

**Why**

- Without this step, the codebase would have mixed defaults:
  - one value in the solver file,
  - another in the GUI,
  - another in comparison scripts.
- Aligning these entry points ensures that:
  - direct solver calls,
  - registry-based runs,
  - GUI runs,
  - comparison scripts,
  - and scaling analysis

all reflect the same tuned behavior.

### 6. Hybrid BSGO-GA

**What changed**

- The hybrid solver in `hybrid_bsgo_ga.py` was upgraded to use:
  - `population_size = 60`
  - `max_iterations = 250`
  - `crossover_rate = 0.92`
  - `mutation_rate = min(0.04, 2 / n)` when not provided explicitly
  - `c_coefficient = 0.72`
  - `tournament_size = 3`
  - `stagnation_limit = 30`
  - `local_search_elite = True`
- The implementation now includes:
  - two-point crossover instead of a simpler one-point-only default
  - local search on the elite individual each generation
  - stagnation detection with partial restart by re-randomizing the worst half
  - a stronger balance between the BSGO improving phase and the GA evolution phase

**Why**

- The hybrid solver is meant to combine:
  - swarm-style guided improvement
  - population diversity
  - recombination from GA
  - local refinement on elite solutions
- Adding elite local search improves exploitation near high-quality regions.
- Two-point crossover preserves useful building blocks better than simple one-point crossover in many binary optimization settings.
- Stagnation recovery reduces the chance that the whole population collapses around one mediocre basin.
- The higher crossover rate keeps the hybrid more exploratory while the improving phase and elite local search preserve intensification.

**Comparison role**

- In the project comparison pipeline, the hybrid solver is the method intended to sit between:
  - the simpler standalone local-search methods such as HC and SA
  - the standalone population methods such as GA and Binary Swarm
- It is useful when you want one algorithm that mixes:
  - directed improvement,
  - recombination,
  - and diversity recovery

inside the same search loop.

## Current Recommended Defaults

For the current project version, the recommended defaults are:

- **Hill Climbing**
  - `max_iterations_per_restart = 1000`
  - `max_random_restarts = 10`
- **Simulated Annealing**
  - `max_iterations = max(3000, 50 * n)`
  - `initial_temperature = 12.0`
  - `cooling_rate = 0.997`
  - `min_temperature = 0.001`
- **Genetic Algorithm**
  - `population_size = 56`
  - `max_generations = 220`
  - `crossover_rate = 0.88`
  - `mutation_rate = min(0.04, 2 / n)`
  - `elite_count = 2`
  - `tournament_size = 3`
  - `crossover_mode = two_point`
- **Memetic GA-SA**
  - `population_size = 56`
  - `max_generations = 220`
  - `crossover_rate = 0.88`
  - `mutation_rate = min(0.04, 2 / n)`
  - `elite_count = 2`
  - `tournament_size = 3`
  - `local_search_every = 10`
  - `local_search_top_k = 2`
  - `sa_max_iterations = min(900, max(350, 4 * n))`
  - `sa_patience = max(60, n / 2)`
  - `stagnation_limit = 28`
  - `restart_fraction = 0.2`
  - `intensify_fraction = 0.8`
  - `intensify_mutation_scale = 4.0`
  - `incremental_local_steps = 2`
  - `incremental_candidate_pool = max(40, n / 3)`
  - `sa_focus_unsatisfied_probability = 0.7`
  - `path_relink_every = 10`
  - `path_relink_top_k = 3`
  - `path_relink_max_steps = max(20, min(60, n / 2))`
  - `path_relink_only_hardcases = True`
  - `hardcase_ratio_threshold = 4.3`
  - `hardcase_multi_run_attempts = 2`
  - `hardcase_generation_scale = 1.2`
  - `hardcase_sa_scale = 1.25`
  - `lamarckian = True`
- **Binary Swarm**
  - `population_size = 60`
  - `max_iterations = 360`
  - `w_inertia = 0.72`
  - `c_cognitive = 1.6`
  - `c_social = 1.8`
  - `local_search_every = 8`
  - `stagnation_limit = 45`
  - `max_restarts = 3`
- **Swarm-SA Hybrid**
  - `population_size = 52`
  - `max_iterations = 220` for the medium benchmark family
  - `w_inertia_start = 0.92`
  - `w_inertia_end = 0.45`
  - `c_cognitive = 1.25`
  - `c_social = 2.1`
  - `velocity_clamp = 4.0`
  - `local_search_every = 10`
  - `local_search_top_k = 1`
  - `sa_max_iterations = min(450, max(180, 2 * n))`
  - `sa_patience = max(60, n / 2)`
  - `stagnation_limit = 24`
  - `max_restarts = 0`
  - `diversify_fraction = 0.25`
  - `lamarckian = True`
- **Hybrid BSGO-GA**
  - `population_size = 60`
  - `max_iterations = 250`
  - `crossover_rate = 0.92`
  - `mutation_rate = min(0.04, 2 / n)`
  - `c_coefficient = 0.72`
  - `tournament_size = 3`
  - `stagnation_limit = 30`
  - `local_search_elite = True`

## Full Analysis Summary

This section consolidates the main analysis and conclusions produced during the full tuning and benchmarking work for this project.

### Benchmark scope used for tuning

- A full rerun across every saved instance and every heavy solver configuration became too expensive once the stronger hybrid and annealed population methods were added.
- To keep the analysis practical while still representative, focused reruns were done on a medium benchmark matrix:
  - `n = 100, 150, 200`
  - `m/n = 3.0, 4.3, 6.0`
- The `r = 4.3` region was especially important because it is close to the random 3-SAT phase transition and shows algorithm differences more clearly.
- Earlier and later conclusions were then cross-checked against the saved reports in:
  - `results/final_results/analysis_report.md`
  - `results/final_results_memetic_ga_sa/analysis_report.md`

### What was learned from tuning each solver

- **Hill Climbing**
  - The implementation was kept unchanged on purpose.
  - Extra restart depth and larger per-restart budgets usually increased runtime more than final quality.
  - It remains a good teaching baseline, but not the best performer on larger or harder cases.

- **Simulated Annealing**
  - SA was the clearest winner among the single-solution methods after tuning.
  - The slower cooling schedule improved hard-instance performance by keeping exploration alive longer.
  - Across the project analysis, SA repeatedly gave the best overall quality/runtime tradeoff.

- **Genetic Algorithm**
  - The standalone GA worked best with moderate population size and moderate generation count.
  - Larger, heavier settings did not reliably improve the final merit.
  - GA stayed the best standalone population-based baseline before the memetic solver was added.

- **Binary Swarm (BSGO)**
  - The swarm solver was substantially improved relative to the early version through proper PSO-style movement, personal best memory, V-shaped transfer, local search, and restart handling.
  - These changes raised solution quality on harder instances enough to justify the extra cost.
  - Even after improvement, the overall conclusion stayed the same: BSGO is better than before, but it still trails SA and usually also trails GA on the current benchmark evidence.

- **Hybrid BSGO-GA**
  - The old hybrid was improved through stronger crossover, elite local search, and stagnation-triggered diversification.
  - This made the hybrid more competitive, but also more expensive.
  - The hybrid still did not clearly combine the best behavior of GA and BSGO strongly enough to dominate both parents.

### Why the project moved from heavy hybridization to a memetic design

- After adding SA-style refinement, reheating, and diversification ideas into multiple population solvers, a clear pattern appeared:
  - quality sometimes improved,
  - but runtime increased too much.
- That evidence showed that adding more SA everywhere was not the best design direction.
- The better approach was selective local refinement:
  - keep GA for exploration and diversity,
  - apply SA only to a few strong elites,
  - do it periodically instead of every generation.
- This directly motivated the new `Memetic GA-SA` solver.

### Memetic GA-SA final conclusion

- `Memetic GA-SA` became the best solver in the later focused benchmark by solution quality.
- The design is intentionally lighter than the older heavy hybrid:
  - GA handles population search,
  - bounded SA refines only top elites,
  - Lamarckian replacement keeps improvements when they help.
- A later tuning pass improved stagnation handling by rebuilding much of the refreshed population as broader mutated clones around the best-known assignment instead of using only random replacement.
- Reported mean results on the focused medium benchmark were:
  - `Memetic GA-SA`: `99.283%` mean satisfaction, `39.34s` mean runtime, `3/9` full satisfactions
  - `Simulated Annealing`: `99.097%` mean satisfaction, `1.89s` mean runtime, `1/9` full satisfactions
  - `Genetic Algorithm`: `98.575%` mean satisfaction, `25.80s` mean runtime
  - `Hybrid BSGO-GA`: `98.353%` mean satisfaction, `50.15s` mean runtime
- So the memetic solver improved solution quality over plain GA and over the older heavy hybrid, while also beating the old heavy hybrid in runtime.
- In a later representative rerun of only `Memetic GA-SA` on `n = 100, 150, 200` and `r = 3.0, 4.3, 6.0` with fixed benchmark-style seeds, the tuned restart-intensification version reached about `98.757%` mean satisfaction in about `9.54s` mean runtime with `1/9` full satisfactions.
- That later tuning improved the practical runtime profile while keeping quality near the earlier memetic level, but it still did not achieve full satisfaction on every representative hard instance, so universal full satisfiability remains an open goal.

### Old hybrid versus new memetic solver

- Before adding the memetic solver, the previous hybrid benchmark snapshot was intentionally preserved in `results/comparison/saved_hybrid_bsgo_ga_before_memetic.json`.
- That preserved comparison matters because it shows the design shift clearly:
  - old heavy `Hybrid BSGO-GA` mean satisfaction: `98.353%`
  - old heavy `Hybrid BSGO-GA` mean runtime: `70.39s`
  - new `Memetic GA-SA` mean satisfaction: `99.283%`
  - new `Memetic GA-SA` mean runtime: `39.34s`
- In other words, the memetic solver did not just replace the old hybrid conceptually; it improved both quality and practical runtime in the saved benchmark package.

### Final solver ranking and recommendation

- **Best quality solver:** `Memetic GA-SA`
- **Best practical default:** `Simulated Annealing`
- **Best simple population baseline:** `Genetic Algorithm`
- **Best teaching baseline:** `Hill Climbing`
- **Improved but still unfinished research direction:** `Binary Swarm (BSGO)`
- **Older heavy hybrid now superseded by the memetic design:** `Hybrid BSGO-GA`

### Interpreting the project conclusion correctly

- If the goal is the strongest overall everyday solver, choose `Simulated Annealing`.
- If the goal is the highest solution quality and more runtime is acceptable, choose `Memetic GA-SA`.
- If the goal is to study a simpler evolutionary approach, use `Genetic Algorithm`.
- If the goal is to compare against a simple deterministic-style local-search baseline, keep `Hill Climbing`.
- If the goal is future improvement work, the most open research target is still `Binary Swarm (BSGO)`, because it improved a lot but still does not look like the strongest version achievable yet.

### Saved analysis artifacts

- Pre-memetic consolidated report: `results/final_results/analysis_report.md`
- Memetic comparison report: `results/final_results_memetic_ga_sa/analysis_report.md`
- SA vs GA vs Swarm vs Memetic vs Swarm-SA report: `results/final_results_swarm_sa/analysis_report.md`
- Advanced memetic experiment comparison data: `results/comparison/memetic_advanced_experiments.json`
- Post-alignment hard-case verification data: `results/comparison/memetic_post_alignment_hardcases.json`
- Advanced memetic experiment report: `results/final_results_memetic_advanced_push/analysis_report.md`
- Post-alignment hard-case verification copy: `results/final_results_memetic_advanced_push/memetic_post_alignment_hardcases.json`
- Saved old hybrid snapshot before memetic replacement: `results/comparison/saved_hybrid_bsgo_ga_before_memetic.json`
- Focused memetic benchmark data: `results/comparison/memetic_vs_sa_ga_hybrid_medium.json`
- Generated memetic plots and report package: `results/final_results_memetic_ga_sa/`
- Generated advanced memetic experiment package: `results/final_results_memetic_advanced_push/`
- Generated Swarm-SA plots and report package: `results/final_results_swarm_sa/`
- Main Swarm-SA plots:
  - `results/final_results_swarm_sa/plots/overall_satisfaction_bar.png` : overall mean satisfaction comparison across the five solvers
  - `results/final_results_swarm_sa/plots/overall_runtime_bar.png` : overall mean runtime comparison across the five solvers
  - `results/final_results_swarm_sa/plots/overall_iterations_bar.png` : overall mean iteration or generation count comparison
  - `results/final_results_swarm_sa/plots/runtime_vs_satisfaction.png` : quality-versus-cost scatter plot for all benchmark runs
  - `results/final_results_swarm_sa/plots/convergence_plot.png` : mean convergence history using the saved best-history traces
  - `results/final_results_swarm_sa/plots/per_instance_quality.png` : per-instance satisfaction comparison for each benchmark case
  - `results/final_results_swarm_sa/plots/per_instance_runtime.png` : per-instance runtime comparison for the exact saved benchmark rows
  - `results/final_results_swarm_sa/plots/per_instance_iterations.png` : per-instance iteration or generation comparison for the exact saved benchmark rows
  - `results/final_results_swarm_sa/plots/quality_by_ratio.png` : mean satisfaction grouped by clause density ratio
  - `results/final_results_swarm_sa/plots/runtime_by_ratio.png` : mean runtime grouped by clause density ratio
  - `results/final_results_swarm_sa/plots/iterations_by_ratio.png` : mean iteration count grouped by clause density ratio
  - `results/final_results_swarm_sa/plots/quality_by_size.png` : mean satisfaction grouped by problem size
  - `results/final_results_swarm_sa/plots/runtime_by_size.png` : mean runtime grouped by problem size
  - `results/final_results_swarm_sa/plots/iterations_by_size.png` : mean iteration count grouped by problem size

### Latest follow-up rerun: SA vs GA vs Swarm vs hybrids

- A later follow-up rerun was done specifically to answer a new question:
  - keep `SA`, `GA`, and `Swarm`,
  - speed up `Memetic GA-SA`,
  - add a new explicit `Swarm-SA Hybrid`,
  - then compare those five methods again on the same medium matrix.
- This follow-up used:
  - `n = 100, 150, 200`
  - `m/n = 3.0, 4.3, 6.0`
- The new saved benchmark file is:
  - `results/comparison/sa_ga_swarm_memetic_swarmsa_medium.json`

### What changed in the tuned Memetic GA-SA

- The heavy earlier memetic version was expensive because it spent too much time in elite refinement:
  - too many SA calls,
  - too many SA iterations per call,
  - too little early stopping.
- The newer tuned memetic version reduces runtime by using:
  - adaptive SA iteration budgets,
  - patience-based SA early stop,
  - controlled restart-style diversity when the GA stalls.
- This made the memetic solver much faster, but it also reduced its quality advantage relative to the old heavier version.

### Latest five-solver rerun results

- `Simulated Annealing`: `99.097%` mean satisfaction, `2.13s` mean runtime, `1/9` full satisfactions
- `Memetic GA-SA`: `98.723%` mean satisfaction, `11.66s` mean runtime, `1/9` full satisfactions
- `Genetic Algorithm`: `98.575%` mean satisfaction, `30.93s` mean runtime
- `Binary Swarm (BSGO)`: `98.161%` mean satisfaction, `24.10s` mean runtime
- `Swarm-SA Hybrid`: `97.851%` mean satisfaction, `16.33s` mean runtime

### Interpreting the latest rerun correctly

- This later rerun changes the practical conclusion for the current lighter memetic version:
  - `SA` is still the strongest overall practical solver in this newer comparison.
  - The tuned lighter `Memetic GA-SA` is now a better runtime-quality compromise than before, but it no longer beats `SA` overall.
  - `GA` remains a useful population baseline, but it is slower than the tuned memetic and slower than `SA`.
  - `Binary Swarm (BSGO)` remains improved but still behind `SA`.
  - The new `Swarm-SA Hybrid` is a valid experimental solver, but in this rerun it did not outperform either `SA` or the tuned memetic solver.

### Answer to the “which algorithm can still reach full satisfaction?” question

- The best candidate for further improvement is still `Memetic GA-SA`.
- The reason is not that it only needs more raw iterations; the bigger opportunity is stronger final exploitation:
  - more targeted local refinement near the end of the run,
  - stagnation-triggered intensification on the best elite,
  - and better clause-aware move selection during refinement.
- Simply increasing iteration count can help on some instances, but by itself it usually gives diminishing returns.
- `SA` is already very strong and fast, but `Memetic GA-SA` has the highest upside if the goal is to push closer to full satisfaction more often.

### Latest advanced memetic experiments

- A later focused experiment pass explicitly tried all of these requested ideas inside `Memetic GA-SA`:
  - incremental-score local search
  - clause and variable occurrence caching
  - path relinking between top elites
  - multi-run intensification only on unsolved hard instances
- Four named variants were saved:
  - `baseline_like`
  - `incremental_local`
  - `incremental_plus_relink`
  - `full_stack_hard_only_relink`
- On the hard matrix only (`r = 4.3, 6.0` for `n = 100, 150, 200`), the saved experiment summary was:
  - `baseline_like`: `97.988%` mean satisfaction, `5.255s` mean runtime
  - `incremental_local`: `97.981%` mean satisfaction, `6.097s` mean runtime
  - `incremental_plus_relink`: `97.954%` mean satisfaction, `6.328s` mean runtime
  - `full_stack_hard_only_relink`: `98.164%` mean satisfaction, `12.732s` mean runtime
- On the representative full matrix (`r = 3.0, 4.3, 6.0` for `n = 100, 150, 200`), the most important before-versus-after comparison was:
  - `baseline_like`: `98.658%` mean satisfaction, `4.377s` mean runtime, `3/9` full satisfactions
  - `full_stack_hard_only_relink`: `98.776%` mean satisfaction, `9.767s` mean runtime, `3/9` full satisfactions
- The final conclusion from that pass was:
  - keep incremental scoring and occurrence caching,
  - keep path relinking only on hard cases,
  - keep multi-run intensification only on hard unsolved cases,
  - accept the runtime increase because it buys a measurable quality gain on the hardest formulas without reducing the representative full-satisfaction count.
- A later post-alignment verification reran only the hard unsolved family using the solver's aligned built-in defaults and saved the result in:
  - `results/comparison/memetic_post_alignment_hardcases.json`
  - `results/final_results_memetic_advanced_push/memetic_post_alignment_hardcases.json`
- That follow-up reached `98.153%` mean satisfaction, `20.970s` mean runtime, and `0/6` full satisfactions on the hard matrix.
- So the alignment rerun was useful as a consistency check, but it did not beat the earlier saved `full_stack_hard_only_relink` hard-matrix result of `98.164%` in `12.732s`.

### Limitations (good to mention orally)

- All of these heuristics are **incomplete** for SAT/Max-SAT: they may stop below the global optimum.
- Near the **phase transition** region of random 3-SAT (`m/n ≈ 4.26`), instances are **hard**; a simple local search may rarely hit full satisfaction even when the instance is satisfiable.
- Reported runtime depends on the solver family:
  - HC and SA spend most of their time in repeated neighbor evaluations.
  - GA and BSGO spend most of their time in repeated population evaluations.

## Reproducibility

- Instance generation uses `random.Random(random_seed)` in `sat_generator.py`.
- Search stochasticity (starts, tie-breaking, mutation, PSO/swarm updates) uses dedicated solver seeds in the solver modules.
- The experiment driver derives per-cell seeds from a `base_seed` so the full grid is repeatable.

## Example console output (demo)

After `python main.py`, you should see lines similar to:

```text
=== Demo: small random 3-SAT instance ===
n = 20, m = 86, m/n ≈ 4.30
Best merit (satisfied clauses): … / 86
Fully satisfied: …
…
Saved convergence plot: …/results/plots/demo_convergence.png
```

## Memetic GA-SA Smoke Test

Run this quick fixed-seed check from `sat_project/`:

```bash
python -c "from pathlib import Path; from sat_generator import load_instance_formula_from_file; from solvers.registry import build_solver_registry; formula = load_instance_formula_from_file(Path('../data/instances/3sat_n100_r6.json')); solver = build_solver_registry()['memetic_ga_sa']; result = solver.solve(formula, {'random_seed': 42}); print(result.algorithm_name, result.best_satisfied_clauses, result.total_clauses, f'{result.runtime_seconds:.3f}s')"
```

This confirms the new memetic solver runs through the same normalized benchmark interface used by the comparison pipeline.

Exact numbers depend on seeds and the stochastic search.

## Oral pitch (short)

You can say: *“I generate random 3-CNF formulas with controlled density, represent literals and clauses in Python, and score assignments by counting satisfied clauses. Then I compare several MAX-SAT heuristics: hill climbing, simulated annealing, genetic search, and binary swarm optimization. I tuned their defaults empirically on representative instances and measured both satisfaction quality and runtime.”*
