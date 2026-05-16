# Formal Solver Choice Analysis

## Scope

- Dataset: top-level `data/instances/*.json` only.
- Compared solvers: `Enhanced SA`, `Genetic Algorithm`, `Memetic GA-SA`.
- Goal: decide the best practical choice for your formal benchmark set.

## Overall Ranking

- `Genetic Algorithm`: mean satisfaction `99.062%`, full satisfaction `6/30`, mean runtime `10.908s`, mean unsatisfied `12.467`

## Best Choice

- Best quality: `Genetic Algorithm`
- Best full-satisfaction rate: `Genetic Algorithm`
- Fastest: `Genetic Algorithm`
- Best overall tradeoff: `Genetic Algorithm`

## Interpretation

- The recommended default on this formal dataset is `Genetic Algorithm` because it is also the top quality option.
- `Genetic Algorithm` remains the speed baseline.

## Hardest Cases

- `3sat_n500_r6.json` / `Genetic Algorithm`: satisfaction `97.183%`, full satisfaction `0/2`, runtime `29.683s`
- `3sat_n200_r6.json` / `Genetic Algorithm`: satisfaction `98.042%`, full satisfaction `0/2`, runtime `14.320s`
- `3sat_n100_r6.json` / `Genetic Algorithm`: satisfaction `98.083%`, full satisfaction `0/2`, runtime `14.192s`
- `3sat_n150_r6.json` / `Genetic Algorithm`: satisfaction `98.167%`, full satisfaction `0/2`, runtime `13.078s`
- `3sat_n500_r4.3.json` / `Genetic Algorithm`: satisfaction `98.465%`, full satisfaction `0/2`, runtime `20.452s`
- `3sat_n50_r6.json` / `Genetic Algorithm`: satisfaction `98.667%`, full satisfaction `0/2`, runtime `7.034s`
- `3sat_n50_r4.3.json` / `Genetic Algorithm`: satisfaction `99.070%`, full satisfaction `0/2`, runtime `4.939s`
- `3sat_n150_r4.3.json` / `Genetic Algorithm`: satisfaction `99.457%`, full satisfaction `0/2`, runtime `9.951s`
- `3sat_n100_r4.3.json` / `Genetic Algorithm`: satisfaction `99.535%`, full satisfaction `0/2`, runtime `10.860s`
- `3sat_n200_r4.3.json` / `Genetic Algorithm`: satisfaction `99.709%`, full satisfaction `0/2`, runtime `10.849s`
