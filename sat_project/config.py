"""
Shared configuration helpers for the enhanced simulated annealing workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"
COMPARISON_DIR = RESULTS_DIR / "comparison"
SA_RESULTS_DIR = RESULTS_DIR / "final_results_sa_enhanced"
SA_PLOTS_DIR = SA_RESULTS_DIR / "plots"
INSTANCE_ROOT = PROJECT_ROOT.parent / "data" / "instances"
SA_STRESS_INSTANCE_DIR = INSTANCE_ROOT / "sa_stress"
SA_STRESS_RESULTS_DIR = RESULTS_DIR / "final_results_sa_stress"
SA_STRESS_PLOTS_DIR = SA_STRESS_RESULTS_DIR / "plots"
MEMETIC_STRESS_RESULTS_DIR = RESULTS_DIR / "final_results_memetic_stress"
MEMETIC_STRESS_PLOTS_DIR = MEMETIC_STRESS_RESULTS_DIR / "plots"
FORMAL_COMPARE_RESULTS_DIR = RESULTS_DIR / "final_results_formal_solver_choice"
FORMAL_COMPARE_PLOTS_DIR = FORMAL_COMPARE_RESULTS_DIR / "plots"

SA_REPRESENTATIVE_MATRIX: List[Tuple[str, int, float]] = [
    ("3sat_n100_r3.json", 100, 3.0),
    ("3sat_n100_r4.3.json", 100, 4.3),
    ("3sat_n100_r6.json", 100, 6.0),
    ("3sat_n150_r3.json", 150, 3.0),
    ("3sat_n150_r4.3.json", 150, 4.3),
    ("3sat_n150_r6.json", 150, 6.0),
    ("3sat_n200_r3.json", 200, 3.0),
    ("3sat_n200_r4.3.json", 200, 4.3),
    ("3sat_n200_r6.json", 200, 6.0),
]

SA_HARD_MATRIX: List[Tuple[str, int, float]] = [
    item for item in SA_REPRESENTATIVE_MATRIX if item[2] >= 4.3
]


def benchmark_seed(n: int, ratio: float, *, offset: int = 0) -> int:
    return 101 + 7 * 100_003 + n * 37 + int(round(ratio * 100)) + offset


def baseline_sa_defaults(n: int) -> Dict[str, Any]:
    return {
        "mode": "baseline",
        "max_iterations": max(3000, 50 * n),
        "initial_temperature": 12.0,
        "cooling_rate": 0.997,
        "min_temperature": 0.001,
    }


def enhanced_sa_defaults(n: int) -> Dict[str, Any]:
    return {
        "mode": "enhanced",
        "max_iterations": max(2500, 45 * n),
        "initial_temperature": 24.0,
        "cooling_rate": 0.9975,
        "min_temperature": 0.0005,
        "restart_count": 2,
        "restart_initialization_strategy": "polarity",
        "elite_restart_transfer": True,
        "elite_restart_perturbation": max(2, n // 30),
        "unsatisfied_focus_probability": 0.6,
        "candidate_pool_size": max(10, n // 10),
        "multi_bit_flip_probability": 0.04,
        "max_multi_flip_size": 2,
        "stagnation_multi_bit_boost": 0.15,
        "stagnation_limit": max(30, int(0.7 * n)),
        "reheat_multiplier": 1.5,
        "max_reheats": 4,
        "adaptive_cooling": True,
        "adaptive_cooling_bonus": 0.0007,
        "adaptive_cooling_penalty": 0.0025,
        "intensification_threshold": 0.98,
        "intensification_focus_probability": 0.94,
        "intensification_cooling_bonus": 0.0009,
        "mini_hill_climb_steps": max(10, int(0.33 * n)),
        "history_bias_strength": 0.72,
        "polarity_bias_strength": 0.7,
    }


def genetic_algorithm_defaults(n: int) -> Dict[str, Any]:
    return {
        "population_size": max(70, min(120, n)),
        "max_generations": max(320, min(700, 2 * n)),
        "crossover_rate": 0.9,
        "mutation_rate": min(0.06, 4.0 / max(n, 1)),
        "elite_count": 2,
        "crossover_mode": "uniform",
        "tournament_size": 3,
        "local_search_every": 4,
        "local_search_steps": max(30, n // 6),
        "local_search_noise_probability": 0.12,
        "annealing_temperature": 2.2,
        "annealing_cooling": 0.992,
        "annealing_trials": 2,
        "annealing_unsatisfied_focus_probability": 0.8,
        "intensification_threshold": 0.99,
        "intensification_focus_probability": 0.92,
        "intensification_local_steps_multiplier": 2.5,
        "intensification_noise_probability": 0.08,
        "intensification_temperature_scale": 0.6,
        "stagnation_limit": 28,
        "reheat_multiplier": 1.5,
        "initialization_strategy": "polarity",
        "polarity_bias_strength": 0.7,
        "multi_bit_mutation_probability": 0.03,
        "max_multi_bit_mutation_size": 3,
        "stagnation_multi_bit_boost": 0.12,
        "finish_attempts": 6,
        "finish_perturbation": max(2, n // 25),
        "finish_local_search_steps": max(80, int(0.5 * n)),
        "finish_noise_probability": 0.12,
        "finish_temperature_scale": 0.4,
        "finish_annealing_trials": 12,
        "finish_with_enhanced_sa": True,
        "finish_sa_max_iterations": min(1500, 8 * n),
    }


SA_TUNING_SPACE: Dict[str, Tuple[Any, ...]] = {
    "initial_temperature": (8.0, 12.0, 14.0, 18.0, 24.0),
    "cooling_rate": (0.996, 0.997, 0.9975, 0.998, 0.9985),
    "min_temperature": (0.0002, 0.0005, 0.001, 0.002),
    "max_iterations_scale": (45, 55, 65, 80),
    "unsatisfied_focus_probability": (0.6, 0.72, 0.8, 0.9),
    "stagnation_limit_scale": (0.35, 0.5, 0.7),
    "reheat_multiplier": (1.35, 1.5, 1.6, 1.8),
    "max_reheats": (2, 3, 4, 5),
    "restart_count": (2, 3, 4),
    "intensification_threshold": (0.98, 0.985, 0.99),
    "multi_bit_flip_probability": (0.04, 0.08, 0.12, 0.18),
    "mini_hill_climb_steps_scale": (0, 0.1, 0.2, 0.33),
    "candidate_pool_divisor": (8, 10, 12),
    "restart_initialization_strategy": ("random", "polarity", "history"),
    "elite_restart_transfer": (False, True),
}

SA_STRESS_VARIABLE_COUNTS: Tuple[int, ...] = (100, 150, 200, 300, 400, 500, 700, 1000)
SA_STRESS_DENSITY_RATIOS: Tuple[float, ...] = (3.0, 4.3, 6.0, 8.0, 10.0)
SA_STRESS_INSTANCES_PER_CELL = 5
SA_STRESS_SOLVER_RUNS_PER_INSTANCE = 5

SA_BREAKDOWN_THRESHOLDS: Dict[str, float] = {
    "full_satisfaction_success_rate": 0.5,
    "mean_satisfaction_rate_warn": 0.99,
    "mean_satisfaction_rate_fail": 0.98,
    "mean_runtime_seconds": 5.0,
    "mean_unsatisfied_clauses": 10.0,
}


def memetic_ga_sa_classic_defaults(n: int) -> Dict[str, Any]:
    return {
        "population_size": 56,
        "max_generations": 220,
        "crossover_rate": 0.88,
        "mutation_rate": min(0.04, 2.0 / max(n, 1)),
        "elite_count": 2,
        "tournament_size": 3,
        "local_search_every": 10,
        "local_search_top_k": 2,
        "sa_max_iterations": min(900, max(350, 4 * n)),
        "sa_patience": max(60, n // 2),
        "stagnation_limit": 28,
        "restart_fraction": 0.2,
        "intensify_fraction": 0.8,
        "intensify_mutation_scale": 4.0,
        "incremental_local_steps": 2,
        "incremental_candidate_pool": max(40, n // 3),
        "sa_focus_unsatisfied_probability": 0.7,
        "sa_refinement_mode": "classic",
        "path_relink_every": 10,
        "path_relink_top_k": 3,
        "path_relink_max_steps": max(20, min(60, n // 2)),
        "path_relink_only_hardcases": True,
        "hardcase_ratio_threshold": 4.3,
        "hardcase_multi_run_attempts": 2,
        "hardcase_generation_scale": 1.2,
        "hardcase_sa_scale": 1.25,
        "lamarckian": True,
    }


def memetic_ga_sa_enhanced_defaults(n: int) -> Dict[str, Any]:
    config = memetic_ga_sa_classic_defaults(n)
    config.update(
        {
            "sa_refinement_mode": "enhanced",
            "sa_initial_temperature": 24.0,
            "sa_cooling_rate": 0.9975,
            "sa_min_temperature": 0.0005,
            "sa_restart_count": 1,
            "sa_candidate_pool_size": max(10, n // 10),
            "sa_multi_bit_flip_probability": 0.04,
            "sa_reheat_multiplier": 1.5,
            "sa_max_reheats": 2,
            "sa_adaptive_cooling": True,
            "sa_intensification_threshold": 0.98,
            "sa_mini_hill_climb_steps": max(10, int(0.2 * n)),
            "sa_elite_restart_transfer": True,
        }
    )
    return config


def binary_swarm_defaults(n: int) -> Dict[str, Any]:
    return {
        "population_size": 64,
        "max_iterations": max(240, 2 * n),
        "w_inertia_start": 0.9,
        "w_inertia_end": 0.4,
        "c_cognitive": 1.35,
        "c_social": 2.05,
        "velocity_clamp": 4.0,
        "local_search_every": 10,
        "local_search_top_k": 2,
        "stagnation_limit": 35,
        "max_restarts": 2,
        "annealing_temperature": 2.2,
        "annealing_cooling": 0.995,
        "annealing_trials": 3,
        "sa_refine_iterations": min(240, max(80, 2 * n)),
        "reheat_multiplier": 1.5,
        "diversify_fraction": 0.3,
        "refine_focus_probability": 0.85,
        "refine_walksat_steps": max(40, n // 6),
        "refine_walksat_noise_probability": 0.12,
        "intensification_threshold": 0.99,
        "intensify_local_search_every": 2,
        "intensify_top_k": 3,
        "intensify_sa_scale": 2.0,
        "finish_attempts": 6,
        "finish_perturbation": max(2, n // 25),
        "finish_walksat_steps": max(120, int(0.6 * n)),
        "finish_walksat_noise_probability": 0.12,
        "finish_anneal_trials": 18,
        "finish_temperature_scale": 0.4,
        "finish_with_enhanced_sa": True,
        "finish_sa_max_iterations": min(1800, 10 * n),
    }
