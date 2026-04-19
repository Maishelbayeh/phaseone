## 3-SAT Local Search Control Panel

This repository contains an educational 3-SAT toolkit with a Tkinter GUI for running and comparing local-search solvers on pre-generated instances.

It supports:

- Hill Climbing with random restarts
- Simulated Annealing
- Tabu Search

All generated outputs are saved under `sat_project/results/`.

### Project structure

- `sat_project/gui.py` - main desktop app (single-instance tabs + batch grid tab)
- `sat_project/main.py` - CLI demo and optional full hill-climbing experiment run
- `sat_project/hill_climbing.py` - hill-climbing solver implementation
- `sat_project/simulated_annealing.py` - simulated annealing solver implementation
- `sat_project/tabu_search.py` - tabu search solver implementation
- `sat_project/experiments.py` - experiment utilities and result export
- `sat_project/plotting.py` - convergence and runtime plots
- `data/instances/` - JSON 3-SAT instances (`3sat_*.json`)
- `sat_project/results/` - CSV/JSON outputs and generated plots

### Requirements

- Python 3.10+
- Tkinter support (included in standard Python installers on Windows)
- Install project dependencies from `sat_project/requirements.txt`

### Quick start

From the repo root:

```bash
cd sat_project
pip install -r requirements.txt
python gui.py
```

### Using the GUI

The app includes four tabs:

- `Hill Climbing` - run one selected instance and save convergence output
- `Simulated Annealing` - run one selected instance and save convergence output
- `Tabu Search` - run one selected instance and save convergence output
- `Batch grid` - run a full dataset sweep for the selected algorithm and export CSV + plots

For batch mode, point the dataset path to `data/instances/` (or any folder containing `3sat_*.json` files).

### Typical output files

Single-run convergence plots:

- `sat_project/results/plots/gui_hill_climbing_convergence.png`
- `sat_project/results/plots/gui_simulated_annealing_convergence.png`
- `sat_project/results/plots/gui_tabu_search_convergence.png`

Batch artifacts:

- `sat_project/results/batch_results_hill_climbing.csv`
- `sat_project/results/batch_results_simulated_annealing.csv`
- `sat_project/results/batch_results_tabu_search.csv`
- `sat_project/results/plots/batch_runtime_vs_num_variables_hill_climbing.png`
- `sat_project/results/plots/batch_runtime_vs_num_variables_simulated_annealing.png`
- `sat_project/results/plots/batch_runtime_vs_num_variables_tabu_search.png`

### CLI mode (optional)

You can also run from `sat_project/`:

```bash
python main.py
```

Useful flags:

- `python main.py --gui` opens the GUI
- `python main.py --full` runs the full hill-climbing experiment pipeline and saves data/plots

### Screenshots

![Single Run](./Single_Run.png)
![Batch Run](./Batch_Run.png)

