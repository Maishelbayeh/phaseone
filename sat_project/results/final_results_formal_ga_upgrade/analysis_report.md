# Formal Solver Choice Analysis

## Scope

- Dataset: top-level `data/instances/*.json` only.
- Compared solvers: `Enhanced SA`, `Genetic Algorithm`, `Memetic GA-SA`.
- Goal: decide the best practical choice for your formal benchmark set.

## Overall Ranking

- `Simulated Annealing`: mean satisfaction `99.328%`, full satisfaction `5/15`, mean runtime `1.230s`, mean unsatisfied `7.867`
- `Genetic Algorithm`: mean satisfaction `98.947%`, full satisfaction `2/15`, mean runtime `14.241s`, mean unsatisfied `12.800`

## Best Choice

- Best quality: `Simulated Annealing`
- Best full-satisfaction rate: `Simulated Annealing`
- Fastest: `Simulated Annealing`
- Best overall tradeoff: `Simulated Annealing`

## Interpretation

- The recommended default on this formal dataset is `Simulated Annealing` because it is also the top quality option.
- `Simulated Annealing` remains the speed baseline.

## Hardest Cases

- `3sat_n500_r6.json` / `Genetic Algorithm`: satisfaction `97.500%`, full satisfaction `0/1`, runtime `34.956s`
- `3sat_n200_r6.json` / `Genetic Algorithm`: satisfaction `97.750%`, full satisfaction `0/1`, runtime `31.437s`
- `3sat_n150_r6.json` / `Genetic Algorithm`: satisfaction `98.000%`, full satisfaction `0/1`, runtime `11.834s`
- `3sat_n100_r6.json` / `Genetic Algorithm`: satisfaction `98.167%`, full satisfaction `0/1`, runtime `10.004s`
- `3sat_n500_r6.json` / `Simulated Annealing`: satisfaction `98.233%`, full satisfaction `0/1`, runtime `4.400s`
- `3sat_n100_r6.json` / `Simulated Annealing`: satisfaction `98.333%`, full satisfaction `0/1`, runtime `0.823s`
- `3sat_n200_r6.json` / `Simulated Annealing`: satisfaction `98.500%`, full satisfaction `0/1`, runtime `2.289s`
- `3sat_n500_r4.3.json` / `Genetic Algorithm`: satisfaction `98.605%`, full satisfaction `0/1`, runtime `28.906s`
- `3sat_n50_r6.json` / `Genetic Algorithm`: satisfaction `98.667%`, full satisfaction `0/1`, runtime `4.457s`
- `3sat_n50_r6.json` / `Simulated Annealing`: satisfaction `98.667%`, full satisfaction `0/1`, runtime `0.585s`
