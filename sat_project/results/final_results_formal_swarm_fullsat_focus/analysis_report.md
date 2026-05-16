# Formal Solver Choice Analysis

## Scope

- Dataset: top-level `data/instances/*.json` only.
- Compared solvers: `Enhanced SA`, `Genetic Algorithm`, `Memetic GA-SA`.
- Goal: decide the best practical choice for your formal benchmark set.

## Overall Ranking

- `Binary Swarm (BSGO)`: mean satisfaction `99.318%`, full satisfaction `10/30`, mean runtime `12.987s`, mean unsatisfied `7.633`

## Best Choice

- Best quality: `Binary Swarm (BSGO)`
- Best full-satisfaction rate: `Binary Swarm (BSGO)`
- Fastest: `Binary Swarm (BSGO)`
- Best overall tradeoff: `Binary Swarm (BSGO)`

## Interpretation

- The recommended default on this formal dataset is `Binary Swarm (BSGO)` because it is also the top quality option.
- `Binary Swarm (BSGO)` remains the speed baseline.

## Hardest Cases

- `3sat_n500_r6.json` / `Binary Swarm (BSGO)`: satisfaction `98.417%`, full satisfaction `0/2`, runtime `51.926s`
- `3sat_n100_r6.json` / `Binary Swarm (BSGO)`: satisfaction `98.417%`, full satisfaction `0/2`, runtime `5.895s`
- `3sat_n150_r6.json` / `Binary Swarm (BSGO)`: satisfaction `98.611%`, full satisfaction `0/2`, runtime `9.610s`
- `3sat_n200_r6.json` / `Binary Swarm (BSGO)`: satisfaction `98.667%`, full satisfaction `0/2`, runtime `18.834s`
- `3sat_n50_r6.json` / `Binary Swarm (BSGO)`: satisfaction `98.667%`, full satisfaction `0/2`, runtime `3.922s`
- `3sat_n50_r4.3.json` / `Binary Swarm (BSGO)`: satisfaction `99.070%`, full satisfaction `0/2`, runtime `2.511s`
- `3sat_n100_r4.3.json` / `Binary Swarm (BSGO)`: satisfaction `99.186%`, full satisfaction `0/2`, runtime `5.286s`
- `3sat_n500_r4.3.json` / `Binary Swarm (BSGO)`: satisfaction `99.326%`, full satisfaction `0/2`, runtime `35.772s`
- `3sat_n200_r4.3.json` / `Binary Swarm (BSGO)`: satisfaction `99.593%`, full satisfaction `0/2`, runtime `14.750s`
- `3sat_n150_r4.3.json` / `Binary Swarm (BSGO)`: satisfaction `99.845%`, full satisfaction `1/2`, runtime `10.203s`
