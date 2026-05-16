"""
Entry point for the educational 3-SAT hill climbing project.

Runs a small, fast demonstration by default, then optionally executes the full
experimental grid and produces plots.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmark_formal_solver_choice import run_formal_solver_choice_benchmark
from experiments import (
    run_experiment_grid,
    run_single_experiment,
    save_records_csv,
    save_records_json,
)
from hill_climbing import hill_climb_with_random_restarts
from memetic_stress_test import run_memetic_stress_test
from plotting import plot_convergence_history, plot_runtime_vs_num_variables
from sa_stress_test import run_sa_stress_test
from sat_generator import compute_clause_count_from_density, generate_random_3sat
from sa_tuning import run_tuning


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
    parser.add_argument(
        "--sa-compare",
        action="store_true",
        help="Run baseline vs enhanced simulated annealing tuning/comparison artifacts.",
    )
    parser.add_argument(
        "--sa-trials",
        type=int,
        default=8,
        help="Number of enhanced SA settings sampled when --sa-compare is used.",
    )
    parser.add_argument(
        "--sa-matrix",
        choices=("representative", "hard"),
        default="representative",
        help="Benchmark matrix used by --sa-compare.",
    )
    parser.add_argument(
        "--sa-runs-per-instance",
        type=int,
        default=1,
        help="Independent runs per instance for --sa-compare.",
    )
    parser.add_argument(
        "--sa-stress-test",
        action="store_true",
        help="Run the large SA stress-test benchmark framework.",
    )
    parser.add_argument(
        "--sa-stress-instances-per-cell",
        type=int,
        default=5,
        help="Generated instances per (n, r) cell for --sa-stress-test.",
    )
    parser.add_argument(
        "--sa-stress-runs-per-instance",
        type=int,
        default=5,
        help="Independent solver runs per instance for --sa-stress-test.",
    )
    parser.add_argument(
        "--sa-stress-baseline-only",
        action="store_true",
        help="When used with --sa-stress-test, skip enhanced SA and run baseline only.",
    )
    parser.add_argument(
        "--memetic-stress-test",
        action="store_true",
        help="Run the large Memetic GA-SA stress-test benchmark framework.",
    )
    parser.add_argument(
        "--memetic-stress-instances-per-cell",
        type=int,
        default=5,
        help="Generated instances per (n, r) cell for --memetic-stress-test.",
    )
    parser.add_argument(
        "--memetic-stress-runs-per-instance",
        type=int,
        default=5,
        help="Independent solver runs per instance for --memetic-stress-test.",
    )
    parser.add_argument(
        "--memetic-stress-classic-only",
        action="store_true",
        help="When used with --memetic-stress-test, skip enhanced-SA refinement and run classic Memetic GA-SA only.",
    )
    parser.add_argument(
        "--formal-solver-choice",
        action="store_true",
        help="Compare enhanced SA, GA, and Memetic GA-SA on top-level data/instances files.",
    )
    parser.add_argument(
        "--formal-runs-per-solver",
        type=int,
        default=1,
        help="Independent runs per solver for --formal-solver-choice.",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    if arguments.gui:
        import gui as gui_module

        gui_module.main()
        return

    if arguments.sa_compare:
        run_tuning(
            trials=max(1, arguments.sa_trials),
            matrix_name=arguments.sa_matrix,
            runs_per_instance=max(1, arguments.sa_runs_per_instance),
            base_seed=42,
        )
        print("Saved enhanced SA comparison artifacts under results/comparison and results/final_results_sa_enhanced.")
        return

    if arguments.sa_stress_test:
        run_sa_stress_test(
            instances_per_cell=max(1, arguments.sa_stress_instances_per_cell),
            solver_runs_per_instance=max(1, arguments.sa_stress_runs_per_instance),
            include_enhanced=not arguments.sa_stress_baseline_only,
            base_seed=42,
        )
        print("Saved SA stress-test artifacts under results/final_results_sa_stress.")
        return

    if arguments.memetic_stress_test:
        run_memetic_stress_test(
            instances_per_cell=max(1, arguments.memetic_stress_instances_per_cell),
            solver_runs_per_instance=max(1, arguments.memetic_stress_runs_per_instance),
            include_enhanced=not arguments.memetic_stress_classic_only,
            base_seed=42,
        )
        print("Saved Memetic GA-SA stress-test artifacts under results/final_results_memetic_stress.")
        return

    if arguments.formal_solver_choice:
        run_formal_solver_choice_benchmark(
            runs_per_solver=max(1, arguments.formal_runs_per_solver),
            base_seed=42,
        )
        print("Saved formal solver-choice comparison artifacts under results/final_results_formal_solver_choice.")
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
