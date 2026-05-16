# Memetic Advanced Experiments

## Scope

- Goal: try all requested Memetic GA-SA upgrades and save both what was tried and the result.
- Requested upgrades:
  - incremental-score local search
  - clause/variable occurrence caching
  - path relinking between top elites
  - multi-run memetic intensification on only the unsolved hardest instances
- Benchmark seed policy: fixed benchmark-style single seed per instance.
- Matrices used:
  - hard matrix: `r = 4.3, 6.0` for `n = 100, 150, 200`
  - representative full matrix: `r = 3.0, 4.3, 6.0` for `n = 100, 150, 200`

## Variants tried

- `baseline_like`: Approximate previous lighter memetic behavior without incremental local search, path relinking, or hard-case multi-run.
- `incremental_local`: Enable incremental-score local search and cached candidate scoring only.
- `incremental_plus_relink`: Enable incremental local search plus elite path relinking, but no hard-case multi-run.
- `full_stack_hard_only_relink`: Enable all requested upgrades: incremental local search, occurrence caching, hard-only path relinking, and hard-case multi-run intensification.

## Hard-matrix summary

- `baseline_like`: mean satisfaction `97.988%`, mean runtime `5.255s`, full satisfactions `0/6`
- `incremental_local`: mean satisfaction `97.981%`, mean runtime `6.097s`, full satisfactions `0/6`
- `incremental_plus_relink`: mean satisfaction `97.954%`, mean runtime `6.328s`, full satisfactions `0/6`
- `full_stack_hard_only_relink`: mean satisfaction `98.164%`, mean runtime `12.732s`, full satisfactions `0/6`

## Full-matrix summary

- `baseline_like`: mean satisfaction `98.658%`, mean runtime `4.377s`, full satisfactions `3/9`
- `full_stack_hard_only_relink`: mean satisfaction `98.776%`, mean runtime `9.767s`, full satisfactions `3/9`

## Conclusion

- The retained winner from this experiment set is `full_stack_hard_only_relink`.
- Compared with `baseline_like`, it improves full-matrix mean satisfaction from `98.658%` to `98.776%`.
- The runtime cost rises from `4.377s` to `9.767s`.
- The full-satisfaction count on the full matrix stays at `3/9`.
- Incremental scoring and occurrence caching are kept because they enable richer local search behavior without large per-flip recomputation.
- Hard-only path relinking is kept because applying it everywhere was not worthwhile on easier instances.
- Hard-case multi-run intensification is kept only for dense unsolved cases because that is where extra runs are most justified.

## Post-alignment verification

- Follow-up check: reran only the hard unsolved family (`r = 4.3, 6.0` for `n = 100, 150, 200`) after aligning the solver's built-in hard-case defaults to the retained documented settings.
- Saved verification artifacts:
  - `results/comparison/memetic_post_alignment_hardcases.json`
  - `results/final_results_memetic_advanced_push/memetic_post_alignment_hardcases.json`
- Verified built-in defaults in the rerun:
  - `hardcase_generation_scale = 1.2`
  - `hardcase_sa_scale = 1.25`
- Post-alignment hard-matrix result:
  - mean satisfaction `98.153%`
  - mean runtime `20.970s`
  - full satisfactions `0/6`
- Compared with the earlier saved `full_stack_hard_only_relink` hard-matrix summary (`98.164%`, `12.732s`, `0/6`), this verification does not show an improvement.
- Conclusion from the follow-up:
  - keep the default-alignment fix for consistency across code and documentation,
  - but treat the original advanced-push result as the stronger saved experiment outcome,
  - and do not claim that the alignment rerun improves the hard instances.
