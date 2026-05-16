# Formal Solver Choice Analysis

## Scope

- Dataset: top-level `data/instances/*.json` only.
- Compared solvers: `Enhanced SA`, `Genetic Algorithm`, `Memetic GA-SA`.
- Goal: decide the best practical choice for your formal benchmark set.

## Overall Ranking

- `Memetic GA-SA`: mean satisfaction `99.370%`, full satisfaction `5/15`, mean runtime `16.382s`, mean unsatisfied `7.733`
- `Simulated Annealing`: mean satisfaction `99.328%`, full satisfaction `5/15`, mean runtime `1.342s`, mean unsatisfied `7.867`
- `Genetic Algorithm`: mean satisfaction `98.685%`, full satisfaction `2/15`, mean runtime `62.192s`, mean unsatisfied `15.733`

## Best Choice

- Best quality: `Memetic GA-SA`
- Best full-satisfaction rate: `Memetic GA-SA`
- Fastest: `Simulated Annealing`
- Best overall tradeoff: `Memetic GA-SA`

## Interpretation

- The recommended default on this formal dataset is `Memetic GA-SA` because it is also the top quality option.
- `Simulated Annealing` remains the speed baseline.

## Hardest Cases

- `3sat_n500_r6.json` / `Genetic Algorithm`: satisfaction `97.133%`, full satisfaction `0/1`, runtime `198.791s`
- `3sat_n200_r6.json` / `Genetic Algorithm`: satisfaction `97.250%`, full satisfaction `0/1`, runtime `109.126s`
- `3sat_n100_r6.json` / `Genetic Algorithm`: satisfaction `97.833%`, full satisfaction `0/1`, runtime `39.912s`
- `3sat_n150_r6.json` / `Genetic Algorithm`: satisfaction `98.000%`, full satisfaction `0/1`, runtime `82.841s`
- `3sat_n500_r6.json` / `Simulated Annealing`: satisfaction `98.233%`, full satisfaction `0/1`, runtime `4.125s`
- `3sat_n500_r6.json` / `Memetic GA-SA`: satisfaction `98.267%`, full satisfaction `0/1`, runtime `13.279s`
- `3sat_n500_r4.3.json` / `Genetic Algorithm`: satisfaction `98.326%`, full satisfaction `0/1`, runtime `121.814s`
- `3sat_n100_r6.json` / `Simulated Annealing`: satisfaction `98.333%`, full satisfaction `0/1`, runtime `1.488s`
- `3sat_n150_r4.3.json` / `Genetic Algorithm`: satisfaction `98.450%`, full satisfaction `0/1`, runtime `58.106s`
- `3sat_n100_r6.json` / `Memetic GA-SA`: satisfaction `98.500%`, full satisfaction `0/1`, runtime `22.973s`
