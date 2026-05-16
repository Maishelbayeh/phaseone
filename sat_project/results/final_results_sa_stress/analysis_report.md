# Simulated Annealing Stress-Test Report

## Overall Health

- `Simulated Annealing (Baseline)`: mean satisfaction `97.565%`, mean runtime `10.795s`, full satisfaction rate `2.50%`, worst runtime `35.612s`, worst satisfaction `94.620%`
- `Simulated Annealing (Enhanced)`: mean satisfaction `98.422%`, mean runtime `4.345s`, full satisfaction rate `12.50%`, worst runtime `14.865s`, worst satisfaction `96.050%`

## Breakdown Detection

- `Simulated Annealing (Baseline)` first problematic `n`: `{'mean_satisfaction_rate': 0.9844682170542636, 'mean_runtime_seconds': 1.7654658199986444, 'full_satisfaction_success_rate': 0.2, 'mean_unsatisfied_clauses': 12.8, 'run_count': 5, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 2.8138008000096306, 'worst_satisfaction_rate': 0.968, 'algorithm_name': 'Simulated Annealing (Baseline)', 'n': 100}`
- `Simulated Annealing (Baseline)` first problematic `r`: `{'mean_satisfaction_rate': 0.9931755952380952, 'mean_runtime_seconds': 5.379711325003882, 'full_satisfaction_success_rate': 0.125, 'mean_unsatisfied_clauses': 13.25, 'run_count': 8, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 10.966618799953721, 'worst_satisfaction_rate': 0.9816666666666667, 'algorithm_name': 'Simulated Annealing (Baseline)', 'ratio': 3.0}`
- `Simulated Annealing (Baseline)` hardest `(n, r)` region: `{'mean_satisfaction_rate': 0.9462, 'mean_runtime_seconds': 35.612300899927504, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 538.0, 'run_count': 1, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 35.612300899927504, 'worst_satisfaction_rate': 0.9462, 'algorithm_name': 'Simulated Annealing (Baseline)', 'n': 1000, 'ratio': 10.0}`
- `Simulated Annealing (Enhanced)` first problematic `n`: `{'mean_satisfaction_rate': 0.9849182170542635, 'mean_runtime_seconds': 0.5759170199744403, 'full_satisfaction_success_rate': 0.2, 'mean_unsatisfied_clauses': 12.4, 'run_count': 5, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 0.9970126999542117, 'worst_satisfaction_rate': 0.969, 'algorithm_name': 'Simulated Annealing (Enhanced)', 'n': 100}`
- `Simulated Annealing (Enhanced)` first problematic `r`: `{'mean_satisfaction_rate': 0.9954166666666666, 'mean_runtime_seconds': 3.312427725031739, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 8.625, 'run_count': 8, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 7.9826920999912545, 'worst_satisfaction_rate': 0.9922480620155039, 'algorithm_name': 'Simulated Annealing (Enhanced)', 'ratio': 4.3}`
- `Simulated Annealing (Enhanced)` hardest `(n, r)` region: `{'mean_satisfaction_rate': 0.9605, 'mean_runtime_seconds': 2.5536878999555483, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 79.0, 'run_count': 1, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 2.5536878999555483, 'worst_satisfaction_rate': 0.9605, 'algorithm_name': 'Simulated Annealing (Enhanced)', 'n': 200, 'ratio': 10.0}`

## Region Summary

- `Simulated Annealing (Baseline)` easiest region: `{'mean_satisfaction_rate': 1.0, 'mean_runtime_seconds': 0.6657985000638291, 'full_satisfaction_success_rate': 1.0, 'mean_unsatisfied_clauses': 0.0, 'run_count': 1, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 0.6657985000638291, 'worst_satisfaction_rate': 1.0, 'algorithm_name': 'Simulated Annealing (Baseline)', 'n': 100, 'ratio': 3.0}`
- `Simulated Annealing (Baseline)` hardest region: `{'mean_satisfaction_rate': 0.9462, 'mean_runtime_seconds': 35.612300899927504, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 538.0, 'run_count': 1, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 35.612300899927504, 'worst_satisfaction_rate': 0.9462, 'algorithm_name': 'Simulated Annealing (Baseline)', 'n': 1000, 'ratio': 10.0}`
- `Simulated Annealing (Enhanced)` easiest region: `{'mean_satisfaction_rate': 1.0, 'mean_runtime_seconds': 0.016039000009186566, 'full_satisfaction_success_rate': 1.0, 'mean_unsatisfied_clauses': 0.0, 'run_count': 1, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 0.016039000009186566, 'worst_satisfaction_rate': 1.0, 'algorithm_name': 'Simulated Annealing (Enhanced)', 'n': 100, 'ratio': 3.0}`
- `Simulated Annealing (Enhanced)` hardest region: `{'mean_satisfaction_rate': 0.9605, 'mean_runtime_seconds': 2.5536878999555483, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 79.0, 'run_count': 1, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 2.5536878999555483, 'worst_satisfaction_rate': 0.9605, 'algorithm_name': 'Simulated Annealing (Enhanced)', 'n': 200, 'ratio': 10.0}`

## Hard Instance Lists

- Top 10 hardest instances:
  - `3sat_n1000_r10_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `94.620%`, unsatisfied `538`, runtime `35.612s`
  - `3sat_n700_r10_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `94.714%`, unsatisfied `370`, runtime `26.395s`
  - `3sat_n1000_r8_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `95.062%`, unsatisfied `395`, runtime `29.684s`
  - `3sat_n200_r10_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `95.600%`, unsatisfied `88`, runtime `7.237s`
  - `3sat_n500_r10_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `95.640%`, unsatisfied `218`, runtime `19.910s`
  - `3sat_n400_r10_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `95.775%`, unsatisfied `169`, runtime `14.905s`
  - `3sat_n200_r10_i00.json` / `Simulated Annealing (Enhanced)`: satisfaction `96.050%`, unsatisfied `79`, runtime `2.554s`
  - `3sat_n700_r8_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `96.125%`, unsatisfied `217`, runtime `27.341s`
  - `3sat_n500_r8_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `96.200%`, unsatisfied `152`, runtime `30.020s`
  - `3sat_n300_r10_i00.json` / `Simulated Annealing (Baseline)`: satisfaction `96.300%`, unsatisfied `111`, runtime `11.398s`
- Top 10 slowest instances:
  - `3sat_n1000_r10_i00.json` / `Simulated Annealing (Baseline)`: runtime `35.612s`, satisfaction `94.620%`
  - `3sat_n500_r8_i00.json` / `Simulated Annealing (Baseline)`: runtime `30.020s`, satisfaction `96.200%`
  - `3sat_n1000_r8_i00.json` / `Simulated Annealing (Baseline)`: runtime `29.684s`, satisfaction `95.062%`
  - `3sat_n700_r8_i00.json` / `Simulated Annealing (Baseline)`: runtime `27.341s`, satisfaction `96.125%`
  - `3sat_n700_r10_i00.json` / `Simulated Annealing (Baseline)`: runtime `26.395s`, satisfaction `94.714%`
  - `3sat_n500_r6_i00.json` / `Simulated Annealing (Baseline)`: runtime `21.937s`, satisfaction `97.133%`
  - `3sat_n1000_r6_i00.json` / `Simulated Annealing (Baseline)`: runtime `20.429s`, satisfaction `96.317%`
  - `3sat_n500_r10_i00.json` / `Simulated Annealing (Baseline)`: runtime `19.910s`, satisfaction `95.640%`
  - `3sat_n700_r6_i00.json` / `Simulated Annealing (Baseline)`: runtime `18.908s`, satisfaction `96.738%`
  - `3sat_n1000_r4.3_i00.json` / `Simulated Annealing (Baseline)`: runtime `15.719s`, satisfaction `97.047%`
- Top 10 near-miss instances:
  - `3sat_n300_r3_i00.json` / `Simulated Annealing (Enhanced)`: unsatisfied `1`, satisfaction `99.889%`, runtime `0.959s`
  - `3sat_n200_r3_i00.json` / `Simulated Annealing (Baseline)`: unsatisfied `1`, satisfaction `99.833%`, runtime `1.809s`
  - `3sat_n100_r4.3_i00.json` / `Simulated Annealing (Enhanced)`: unsatisfied `1`, satisfaction `99.767%`, runtime `0.386s`
  - `3sat_n100_r4.3_i00.json` / `Simulated Annealing (Baseline)`: unsatisfied `1`, satisfaction `99.767%`, runtime `1.418s`
  - `3sat_n300_r3_i00.json` / `Simulated Annealing (Baseline)`: unsatisfied `2`, satisfaction `99.778%`, runtime `3.611s`
  - `3sat_n150_r3_i00.json` / `Simulated Annealing (Baseline)`: unsatisfied `2`, satisfaction `99.556%`, runtime `1.292s`
  - `3sat_n1000_r3_i00.json` / `Simulated Annealing (Enhanced)`: unsatisfied `3`, satisfaction `99.900%`, runtime `3.185s`
  - `3sat_n700_r3_i00.json` / `Simulated Annealing (Enhanced)`: unsatisfied `3`, satisfaction `99.857%`, runtime `2.849s`
  - `3sat_n200_r4.3_i00.json` / `Simulated Annealing (Enhanced)`: unsatisfied `3`, satisfaction `99.651%`, runtime `1.359s`
  - `3sat_n300_r4.3_i00.json` / `Simulated Annealing (Enhanced)`: unsatisfied `4`, satisfaction `99.690%`, runtime `1.441s`
