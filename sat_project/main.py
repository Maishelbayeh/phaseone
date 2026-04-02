"""
Entry point for the educational 3-SAT hill climbing project.

Runs a small, fast demonstration by default, then optionally executes the full
experimental grid and produces plots.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments import (
    run_experiment_grid,
    run_single_experiment,
    save_records_csv,
    save_records_json,
)
from hill_climbing import hill_climb_with_random_restarts
from plotting import plot_convergence_history, plot_runtime_vs_num_variables
from sat_generator import compute_clause_count_from_density, generate_random_3sat


PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = RESULTS_DIR / "data"
PLOTS_DIR = RESULTS_DIR / "plots"


def run_small_demo() -> None:
    """
    Quick sanity demo on a tiny formula so beginners see end-to-end behavior.

    Prints the formula size, merit trajectory length, and whether SAT was found.
    """
    print("=== Demo: small random 3-SAT instance ===")
    num_variables = 20
    ratio = 4.3
    num_clauses = compute_clause_count_from_density(num_variables, ratio)
    generation_seed = 123
    solver_seed = 456

    formula = generate_random_3sat(
        num_variables=num_variables,
        num_clauses=num_clauses,
        random_seed=generation_seed,
    )
    print(f"n = {num_variables}, m = {num_clauses}, m/n ~ {num_clauses / num_variables:.2f}")

    result = hill_climb_with_random_restarts(
        formula,
        max_iterations_per_restart=300,
        max_random_restarts=5,
        random_seed=solver_seed,
    )

    print(f"Best merit (satisfied clauses): {result.best_merit} / {result.total_clauses}")
    print(f"Fully satisfied: {result.fully_satisfied}")
    print(f"Iterations (improving flips): {result.iterations_used}")
    print(f"Random restarts used: {result.restart_count}")
    print(f"Runtime: {result.runtime_seconds:.4f} s")
    print(f"Merit history length (steps recorded): {len(result.merit_history)}")
    print()

    demo_convergence_path = PLOTS_DIR / "demo_convergence.png"
    plot_convergence_history(
        result.merit_history,
        result.total_clauses,
        output_path=demo_convergence_path,
        title="Demo run: convergence of best merit",
    )
    print(f"Saved convergence plot: {demo_convergence_path}")
    print()


def run_full_pipeline() -> None:
    """Execute the coursework grid, save tables, and render scaling plot."""
    print("=== Full experiment grid (may take several minutes) ===")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    records = run_experiment_grid(
        base_seed=42,
        max_random_restarts=8,
        instances_per_cell=1,
    )

    csv_path = DATA_DIR / "experiment_results.csv"
    json_path = DATA_DIR / "experiment_results.json"
    save_records_csv(records, csv_path)
    save_records_json(records, json_path)
    print(f"Wrote CSV:  {csv_path}")
    print(f"Wrote JSON: {json_path}")

    complexity_plot_path = PLOTS_DIR / "runtime_vs_num_variables.png"
    plot_runtime_vs_num_variables(
        records,
        output_path=complexity_plot_path,
        title="Hill climbing runtime vs. n (mean per grid cell)",
    )
    print(f"Saved complexity plot: {complexity_plot_path}")
    print("Done.")
    print()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="3-SAT hill climbing experiments (educational).")
    parser.add_argument(
        "--full",
        action="store_true",
        help="After the demo, run the full n × density grid and save plots.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the Tkinter control panel to edit parameters interactively.",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    if arguments.gui:
        import gui as gui_module

        gui_module.main()
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    run_small_demo()

    if arguments.full:
        run_full_pipeline()
    else:
        print("Tip: use ``python main.py --full`` to run the complete experiment suite.")


if __name__ == "__main__":
    main()
