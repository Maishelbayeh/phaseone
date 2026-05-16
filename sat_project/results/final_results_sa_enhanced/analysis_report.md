# Enhanced SA Analysis

## Scope

- Goal: improve Simulated Annealing to maximize the probability of full satisfaction, not only average clause satisfaction.
- Comparison modes: baseline single-run SA versus enhanced restart-aware SA.
- Tuning trials evaluated: `4` enhanced settings plus one baseline reference.
- Benchmark instances: `18` total solver-instance runs.

## Comparison Summary

- `baseline`: mean satisfaction `98.941%`, full satisfactions `2/9`, mean runtime `1.798s`, success rate `22.22%`, runtime-to-success `8.089`
- `enhanced_best`: mean satisfaction `99.397%`, full satisfactions `4/9`, mean runtime `0.769s`, success rate `44.44%`, runtime-to-success `1.731`

## Best Enhanced Setting

- Winning label: `enhanced_trial_2`
- Config: `{"adaptive_cooling": true, "adaptive_cooling_bonus": 0.0007, "adaptive_cooling_penalty": 0.0025, "candidate_pool_size": 10, "cooling_rate": 0.9975, "elite_restart_perturbation": 3, "elite_restart_transfer": true, "history_bias_strength": 0.72, "initial_temperature": 24.0, "intensification_cooling_bonus": 0.0009, "intensification_focus_probability": 0.94, "intensification_threshold": 0.98, "max_iterations": 4500, "max_multi_flip_size": 2, "max_reheats": 4, "min_temperature": 0.0005, "mini_hill_climb_steps": 33, "mode": "enhanced", "multi_bit_flip_probability": 0.04, "polarity_bias_strength": 0.7, "reheat_multiplier": 1.5, "restart_count": 2, "restart_initialization_strategy": "polarity", "stagnation_limit": 70, "stagnation_multi_bit_boost": 0.15, "unsatisfied_focus_probability": 0.6}`

## Focus Run Diagnostics

- Focus instance: `3sat_n100_r4.3.json`
- Best merit: `427/430`
- Restart count used: `2`
- Reheats used: `8`
- Accepted better/equal/worse moves: `124` / `5658` / `102`

## Notes

- The enhanced mode biases proposals toward unsatisfied clauses, adds reheating, and uses multiple restart strategies with optional elite transfer.
- Success-rate plots should be interpreted together with runtime-to-success, because the more aggressive settings can improve hit rate at extra cost.
