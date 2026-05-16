# Formal Solver Choice Analysis

## Scope

- Dataset: top-level `data/instances/*.json` only.
- Compared solvers: `Enhanced SA`, `Genetic Algorithm`, `Memetic GA-SA`.
- Goal: decide the best practical choice for your formal benchmark set.

## Overall Ranking

- `Genetic Algorithm`: mean satisfaction `99.313%`, full satisfaction `8/30`, mean runtime `11.947s`, mean unsatisfied `8.100`

## Best Choice

- Best quality: `Genetic Algorithm`
- Best full-satisfaction rate: `Genetic Algorithm`
- Fastest: `Genetic Algorithm`
- Best overall tradeoff: `Genetic Algorithm`

## Interpretation

- The recommended default on this formal dataset is `Genetic Algorithm` because it is also the top quality option.
- `Genetic Algorithm` remains the speed baseline.

## Hardest Cases

- `3sat_n500_r6.json` / `Genetic Algorithm`: satisfaction `98.300%`, full satisfaction `0/2`, runtime `29.491s`
- `3sat_n100_r6.json` / `Genetic Algorithm`: satisfaction `98.333%`, full satisfaction `0/2`, runtime `15.872s`
- `3sat_n200_r6.json` / `Genetic Algorithm`: satisfaction `98.500%`, full satisfaction `0/2`, runtime `18.041s`
- `3sat_n50_r6.json` / `Genetic Algorithm`: satisfaction `98.667%`, full satisfaction `0/2`, runtime `6.585s`
- `3sat_n150_r6.json` / `Genetic Algorithm`: satisfaction `98.722%`, full satisfaction `0/2`, runtime `12.958s`
- `3sat_n50_r4.3.json` / `Genetic Algorithm`: satisfaction `99.070%`, full satisfaction `0/2`, runtime `6.054s`
- `3sat_n500_r4.3.json` / `Genetic Algorithm`: satisfaction `99.186%`, full satisfaction `0/2`, runtime `22.869s`
- `3sat_n100_r4.3.json` / `Genetic Algorithm`: satisfaction `99.535%`, full satisfaction `0/2`, runtime `10.730s`
- `3sat_n150_r4.3.json` / `Genetic Algorithm`: satisfaction `99.690%`, full satisfaction `0/2`, runtime `10.151s`
- `3sat_n200_r4.3.json` / `Genetic Algorithm`: satisfaction `99.826%`, full satisfaction `0/2`, runtime `13.322s`
