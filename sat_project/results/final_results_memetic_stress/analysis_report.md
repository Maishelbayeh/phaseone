# Memetic GA-SA Stress-Test Report

## Overall Health

- `Memetic GA-SA (Classic refine)`: mean satisfaction `98.690%`, mean runtime `19.333s`, full satisfaction rate `11.11%`, worst runtime `45.002s`, worst satisfaction `97.333%`
- `Memetic GA-SA (Enhanced SA refine)`: mean satisfaction `99.420%`, mean runtime `26.493s`, full satisfaction rate `33.33%`, worst runtime `53.658s`, worst satisfaction `98.333%`

## Breakdown Detection

- `Memetic GA-SA (Classic refine)` first problematic `n`: `{'mean_satisfaction_rate': 0.9880103359173127, 'mean_runtime_seconds': 8.769932633343464, 'full_satisfaction_success_rate': 0.3333333333333333, 'mean_unsatisfied_clauses': 6.666666666666667, 'run_count': 3, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 18.81917869998142, 'worst_satisfaction_rate': 0.9733333333333334, 'algorithm_name': 'Memetic GA-SA (Classic refine)', 'n': 100}`
- `Memetic GA-SA (Classic refine)` first problematic `r`: `{'mean_satisfaction_rate': 0.9979629629629629, 'mean_runtime_seconds': 5.330770866712555, 'full_satisfaction_success_rate': 0.3333333333333333, 'mean_unsatisfied_clauses': 1.0, 'run_count': 3, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 9.79058640007861, 'worst_satisfaction_rate': 0.9955555555555555, 'algorithm_name': 'Memetic GA-SA (Classic refine)', 'ratio': 3.0}`
- `Memetic GA-SA (Classic refine)` hardest `(n, r)` region: `{'mean_satisfaction_rate': 0.9733333333333334, 'mean_runtime_seconds': 18.81917869998142, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 16.0, 'run_count': 1, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 18.81917869998142, 'worst_satisfaction_rate': 0.9733333333333334, 'algorithm_name': 'Memetic GA-SA (Classic refine)', 'n': 100, 'ratio': 6.0}`
- `Memetic GA-SA (Enhanced SA refine)` first problematic `n`: `{'mean_satisfaction_rate': 0.9936692506459948, 'mean_runtime_seconds': 15.68818473330854, 'full_satisfaction_success_rate': 0.3333333333333333, 'mean_unsatisfied_clauses': 3.6666666666666665, 'run_count': 3, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 28.248035999946296, 'worst_satisfaction_rate': 0.9833333333333333, 'algorithm_name': 'Memetic GA-SA (Enhanced SA refine)', 'n': 100}`
- `Memetic GA-SA (Enhanced SA refine)` first problematic `r`: `{'mean_satisfaction_rate': 0.9974160206718345, 'mean_runtime_seconds': 36.198636966679864, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 1.6666666666666667, 'run_count': 3, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 52.913819700013846, 'worst_satisfaction_rate': 0.9968992248062015, 'algorithm_name': 'Memetic GA-SA (Enhanced SA refine)', 'ratio': 4.3}`
- `Memetic GA-SA (Enhanced SA refine)` hardest `(n, r)` region: `{'mean_satisfaction_rate': 0.9833333333333333, 'mean_runtime_seconds': 28.248035999946296, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 10.0, 'run_count': 1, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 28.248035999946296, 'worst_satisfaction_rate': 0.9833333333333333, 'algorithm_name': 'Memetic GA-SA (Enhanced SA refine)', 'n': 100, 'ratio': 6.0}`

## Region Summary

- `Memetic GA-SA (Classic refine)` easiest region: `{'mean_satisfaction_rate': 1.0, 'mean_runtime_seconds': 0.2108222000533715, 'full_satisfaction_success_rate': 1.0, 'mean_unsatisfied_clauses': 0.0, 'run_count': 1, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 0.2108222000533715, 'worst_satisfaction_rate': 1.0, 'algorithm_name': 'Memetic GA-SA (Classic refine)', 'n': 100, 'ratio': 3.0}`
- `Memetic GA-SA (Classic refine)` hardest region: `{'mean_satisfaction_rate': 0.9733333333333334, 'mean_runtime_seconds': 18.81917869998142, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 16.0, 'run_count': 1, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 18.81917869998142, 'worst_satisfaction_rate': 0.9733333333333334, 'algorithm_name': 'Memetic GA-SA (Classic refine)', 'n': 100, 'ratio': 6.0}`
- `Memetic GA-SA (Enhanced SA refine)` easiest region: `{'mean_satisfaction_rate': 1.0, 'mean_runtime_seconds': 0.11819750000722706, 'full_satisfaction_success_rate': 1.0, 'mean_unsatisfied_clauses': 0.0, 'run_count': 1, 'full_satisfaction_count': 1, 'worst_runtime_seconds': 0.11819750000722706, 'worst_satisfaction_rate': 1.0, 'algorithm_name': 'Memetic GA-SA (Enhanced SA refine)', 'n': 100, 'ratio': 3.0}`
- `Memetic GA-SA (Enhanced SA refine)` hardest region: `{'mean_satisfaction_rate': 0.9833333333333333, 'mean_runtime_seconds': 28.248035999946296, 'full_satisfaction_success_rate': 0.0, 'mean_unsatisfied_clauses': 10.0, 'run_count': 1, 'full_satisfaction_count': 0, 'worst_runtime_seconds': 28.248035999946296, 'worst_satisfaction_rate': 0.9833333333333333, 'algorithm_name': 'Memetic GA-SA (Enhanced SA refine)', 'n': 100, 'ratio': 6.0}`

## Hard Instance Lists

- Top 10 hardest instances:
  - `3sat_n100_r6_i00.json` / `Memetic GA-SA (Classic refine)`: satisfaction `97.333%`, unsatisfied `16`, runtime `18.819s`
  - `3sat_n200_r6_i00.json` / `Memetic GA-SA (Classic refine)`: satisfaction `97.667%`, unsatisfied `28`, runtime `45.002s`
  - `3sat_n150_r6_i00.json` / `Memetic GA-SA (Classic refine)`: satisfaction `97.778%`, unsatisfied `20`, runtime `32.383s`
  - `3sat_n100_r6_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: satisfaction `98.333%`, unsatisfied `10`, runtime `28.248s`
  - `3sat_n200_r4.3_i00.json` / `Memetic GA-SA (Classic refine)`: satisfaction `98.372%`, unsatisfied `14`, runtime `32.338s`
  - `3sat_n150_r6_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: satisfaction `98.556%`, unsatisfied `13`, runtime `53.658s`
  - `3sat_n150_r4.3_i00.json` / `Memetic GA-SA (Classic refine)`: satisfaction `98.605%`, unsatisfied `9`, runtime `22.185s`
  - `3sat_n200_r6_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: satisfaction `98.667%`, unsatisfied `16`, runtime `46.999s`
  - `3sat_n100_r4.3_i00.json` / `Memetic GA-SA (Classic refine)`: satisfaction `99.070%`, unsatisfied `4`, runtime `7.280s`
  - `3sat_n150_r3_i00.json` / `Memetic GA-SA (Classic refine)`: satisfaction `99.556%`, unsatisfied `2`, runtime `5.991s`
- Top 10 slowest instances:
  - `3sat_n150_r6_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: runtime `53.658s`, satisfaction `98.556%`
  - `3sat_n200_r4.3_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: runtime `52.914s`, satisfaction `99.767%`
  - `3sat_n200_r6_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: runtime `46.999s`, satisfaction `98.667%`
  - `3sat_n200_r6_i00.json` / `Memetic GA-SA (Classic refine)`: runtime `45.002s`, satisfaction `97.667%`
  - `3sat_n150_r4.3_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: runtime `36.984s`, satisfaction `99.690%`
  - `3sat_n150_r6_i00.json` / `Memetic GA-SA (Classic refine)`: runtime `32.383s`, satisfaction `97.778%`
  - `3sat_n200_r4.3_i00.json` / `Memetic GA-SA (Classic refine)`: runtime `32.338s`, satisfaction `98.372%`
  - `3sat_n100_r6_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: runtime `28.248s`, satisfaction `98.333%`
  - `3sat_n150_r4.3_i00.json` / `Memetic GA-SA (Classic refine)`: runtime `22.185s`, satisfaction `98.605%`
  - `3sat_n100_r6_i00.json` / `Memetic GA-SA (Classic refine)`: runtime `18.819s`, satisfaction `97.333%`
- Top 10 near-miss instances:
  - `3sat_n200_r3_i00.json` / `Memetic GA-SA (Classic refine)`: unsatisfied `1`, satisfaction `99.833%`, runtime `9.791s`
  - `3sat_n100_r4.3_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: unsatisfied `1`, satisfaction `99.767%`, runtime `18.698s`
  - `3sat_n200_r4.3_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: unsatisfied `2`, satisfaction `99.767%`, runtime `52.914s`
  - `3sat_n150_r4.3_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: unsatisfied `2`, satisfaction `99.690%`, runtime `36.984s`
  - `3sat_n150_r3_i00.json` / `Memetic GA-SA (Classic refine)`: unsatisfied `2`, satisfaction `99.556%`, runtime `5.991s`
  - `3sat_n100_r4.3_i00.json` / `Memetic GA-SA (Classic refine)`: unsatisfied `4`, satisfaction `99.070%`, runtime `7.280s`
  - `3sat_n150_r4.3_i00.json` / `Memetic GA-SA (Classic refine)`: unsatisfied `9`, satisfaction `98.605%`, runtime `22.185s`
  - `3sat_n100_r6_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: unsatisfied `10`, satisfaction `98.333%`, runtime `28.248s`
  - `3sat_n150_r6_i00.json` / `Memetic GA-SA (Enhanced SA refine)`: unsatisfied `13`, satisfaction `98.556%`, runtime `53.658s`
  - `3sat_n200_r4.3_i00.json` / `Memetic GA-SA (Classic refine)`: unsatisfied `14`, satisfaction `98.372%`, runtime `32.338s`
