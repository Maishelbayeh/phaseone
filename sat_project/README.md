# 3-SAT Local Search (Hill Climbing) — Educational Project

## Overview

This repository implements a **random 3-SAT generator** and a **stochastic hill climbing** solver that maximizes the number of satisfied clauses (a Max-SAT style objective). There is **no** external SAT oracle: evaluation and search are implemented in pure Python.

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

**Hill climbing** starts from a random assignment, repeatedly **flips one variable** that **strictly increases** merit, and stops at a **local optimum**, full satisfaction, or an iteration budget. **Random restarts** re-sample the start when a plateau ends, reducing dependence on a single unlucky initialization. **Ties** among equally good improving flips are broken uniformly at random.

### Limitations (good to mention orally)

- Hill climbing is **incomplete** for SAT/Max-SAT: it may stop below the global optimum.
- Near the **phase transition** region of random 3-SAT (`m/n ≈ 4.26`), instances are **hard**; a simple local search may rarely hit full satisfaction even when the instance is satisfiable.
- Reported runtime scales with **neighbor evaluations** (on the order of **per-iteration × n × m** in this implementation).

## Reproducibility

- Instance generation uses `random.Random(random_seed)` in `sat_generator.py`.
- Search stochasticity (starts, tie-breaking) uses a dedicated solver seed in `hill_climbing.py`.
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

Exact numbers depend on seeds and the stochastic search.

## Oral pitch (short)

You can say: *“I generate random 3-CNF formulas with controlled density, represent literals and clauses in Python, and score assignments by counting satisfied clauses. I optimize with hill climbing over single-variable flips, add random restarts to escape local optima, and measure runtime vs. `n` for three density ratios. The plots show how fast merit improves in one run and how wall-clock time grows with problem size.”*
