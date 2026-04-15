"""
Desktop control panel (Tkinter) for tuning 3-SAT generation and hill climbing.

Runs heavy work in background threads so the window stays responsive.
Uses only the Python standard library (tkinter).
"""

from __future__ import annotations

import queue
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk, messagebox, scrolledtext, filedialog
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple

from experiments import (
    SingleRunRecord,
)
from hill_climbing import hill_climb_with_random_restarts
from simulated_annealing import simulated_annealing_search
from tabu_search import tabu_search_solve
from plotting import (
    plot_convergence_history,
    plot_runtime_vs_num_variables,
    plot_satisfied_clauses_vs_num_variables,
    plot_satisfaction_rate_vs_num_variables,
)
from sat_generator import load_instance_formula_from_file


PROJECT_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "results"
DATA_DIR = RESULTS_DIR / "data"
PLOTS_DIR = RESULTS_DIR / "plots"


def _parse_int_list(text: str, *, minimum_value: int = 3) -> List[int]:
    """Parse comma-separated integers (e.g. ``50, 100, 150``)."""
    cleaned = text.replace(";", ",")
    parts = [segment.strip() for segment in cleaned.split(",") if segment.strip()]
    if not parts:
        raise ValueError("List is empty.")
    values: List[int] = []
    for part in parts:
        values.append(int(part))
        if values[-1] < minimum_value:
            raise ValueError(f"Each n must be >= {minimum_value}. Got {values[-1]}.")
    return values


def _parse_float_list(text: str) -> List[float]:
    """Parse comma-separated floats (e.g. ``3, 4.3, 6``)."""
    cleaned = text.replace(";", ",")
    parts = [segment.strip() for segment in cleaned.split(",") if segment.strip()]
    if not parts:
        raise ValueError("List is empty.")
    return [float(part) for part in parts]


class SatControlApp(ttk.Frame):
    """Main window: solver tabs for single run and one batch tab."""

    @dataclass(frozen=True)
    class SolverParameterSpec:
        key: str
        label: str
        default_value: str
        min_value: Optional[float] = None
        max_value: Optional[float] = None
        integer_only: bool = True

    @dataclass(frozen=True)
    class SolverUiSpec:
        key: str
        title: str
        button_text: str
        solver_display_name: str
        hint: str
        parameters: Tuple["SatControlApp.SolverParameterSpec", ...]

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=10)
        self.master.title("3-SAT Local Search — Control Panel")
        self.master.minsize(640, 520)
        self.grid(row=0, column=0, sticky="nsew")
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)

        self._work_queue: queue.Queue[Tuple[str, object]] = queue.Queue()
        self._batch_total_cells = 0
        self._batch_completed = 0
        self._instance_choices: List[str] = []
        self._solver_tab_state: Dict[str, Dict[str, Any]] = {}

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        hill_tab = ttk.Frame(notebook, padding=8)
        simulated_annealing_tab = ttk.Frame(notebook, padding=8)
        tabu_tab = ttk.Frame(notebook, padding=8)
        batch_tab = ttk.Frame(notebook, padding=8)
        notebook.add(hill_tab, text="Hill Climbing")
        notebook.add(simulated_annealing_tab, text="Simulated Annealing")
        notebook.add(tabu_tab, text="Tabu Search")
        notebook.add(batch_tab, text="Batch grid")

        self._build_solver_tab(
            hill_tab,
            self.SolverUiSpec(
                key="hill_climbing",
                title="Select SAT Instance",
                button_text="Run hill climbing",
                solver_display_name="Hill Climbing",
                hint=(
                    "Loads the selected pre-generated instance from disk, runs hill climbing, "
                    "and saves a convergence plot under results/plots/."
                ),
                parameters=(
                    self.SolverParameterSpec("solver_seed", "Solver seed", "456", min_value=0),
                    self.SolverParameterSpec(
                        "max_iterations_per_restart",
                        "Max iterations / restart",
                        "500",
                        min_value=1,
                    ),
                    self.SolverParameterSpec(
                        "max_random_restarts",
                        "Max random restarts",
                        "8",
                        min_value=1,
                    ),
                ),
            ),
            on_run=self._on_run_hill_climbing,
        )
        self._build_solver_tab(
            simulated_annealing_tab,
            self.SolverUiSpec(
                key="simulated_annealing",
                title="Select SAT Instance",
                button_text="Run simulated annealing",
                solver_display_name="Simulated Annealing",
                hint=(
                    "Loads the selected pre-generated instance from disk, runs simulated annealing, "
                    "and saves a convergence plot under results/plots/."
                ),
                parameters=(
                    self.SolverParameterSpec("solver_seed", "Solver seed", "456", min_value=0),
                    self.SolverParameterSpec("max_iterations", "Max iterations", "2000", min_value=1),
                    self.SolverParameterSpec("initial_temperature", "Initial temperature", "10.0", min_value=0.000001, integer_only=False),
                    self.SolverParameterSpec("cooling_rate", "Cooling rate", "0.995", min_value=0.000001, max_value=0.999999, integer_only=False),
                    self.SolverParameterSpec("min_temperature", "Minimum temperature", "0.01", min_value=0.000001, integer_only=False),
                ),
            ),
            on_run=self._on_run_simulated_annealing,
        )
        self._build_solver_tab(
            tabu_tab,
            self.SolverUiSpec(
                key="tabu_search",
                title="Select SAT Instance",
                button_text="Run tabu search",
                solver_display_name="Tabu Search",
                hint=(
                    "Loads the selected pre-generated instance from disk, runs tabu search, "
                    "and saves a convergence plot under results/plots/."
                ),
                parameters=(
                    self.SolverParameterSpec("solver_seed", "Solver seed", "456", min_value=0),
                    self.SolverParameterSpec("max_iterations", "Max iterations", "2000", min_value=1),
                    self.SolverParameterSpec("tabu_tenure", "Tabu tenure", "12", min_value=1),
                ),
            ),
            on_run=self._on_run_tabu_search,
        )
        self._build_batch_tab(batch_tab)

        self._refresh_instance_list()

        log_frame = ttk.LabelFrame(self, text="Log", padding=6)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.rowconfigure(1, weight=2)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=14, wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        status = ttk.Label(self, text="Ready.", relief=tk.SUNKEN, anchor="w")
        status.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.status_var = tk.StringVar(value="Ready.")
        status.configure(textvariable=self.status_var)

        self.after(150, self._poll_work_queue)

    def _build_solver_tab(
        self,
        parent: ttk.Frame,
        solver_spec: SolverUiSpec,
        *,
        on_run: Callable[[], None],
    ) -> None:
        parent.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(parent, text=solver_spec.title).grid(row=row, column=0, sticky="w", pady=2)
        instance_path = tk.StringVar(value="")
        instance_combo = ttk.Combobox(parent, textvariable=instance_path, width=48, state="readonly")
        instance_combo.grid(row=row, column=1, sticky="ew", pady=2)
        instance_combo.bind("<<ComboboxSelected>>", lambda _e, key=solver_spec.key: self._on_instance_selected(key))

        row += 1
        browse_frame = ttk.Frame(parent)
        browse_frame.grid(row=row, column=0, columnspan=2, sticky="w")
        ttk.Button(
            browse_frame,
            text="Browse…",
            command=lambda key=solver_spec.key: self._on_browse_instance(key),
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Button(browse_frame, text="Refresh", command=self._refresh_instance_list).grid(row=0, column=1, sticky="w")

        row += 1
        info = ttk.LabelFrame(parent, text="Instance details", padding=6)
        info.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        for c in range(2):
            info.columnconfigure(c, weight=1)
        info_n = tk.StringVar(value="-")
        info_m = tk.StringVar(value="-")
        info_ratio = tk.StringVar(value="-")
        ttk.Label(info, text="n =").grid(row=0, column=0, sticky="e")
        ttk.Label(info, textvariable=info_n).grid(row=0, column=1, sticky="w")
        ttk.Label(info, text="m =").grid(row=1, column=0, sticky="e")
        ttk.Label(info, textvariable=info_m).grid(row=1, column=1, sticky="w")
        ttk.Label(info, text="ratio =").grid(row=2, column=0, sticky="e")
        ttk.Label(info, textvariable=info_ratio).grid(row=2, column=1, sticky="w")

        parameter_vars: Dict[str, tk.StringVar] = {}
        for parameter in solver_spec.parameters:
            row += 1
            ttk.Label(parent, text=parameter.label).grid(row=row, column=0, sticky="w", pady=2)
            variable = tk.StringVar(value=parameter.default_value)
            parameter_vars[parameter.key] = variable
            ttk.Entry(parent, textvariable=variable, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        btn = ttk.Button(parent, text=solver_spec.button_text, command=on_run)
        btn.grid(row=row, column=0, columnspan=2, pady=10, sticky="w")

        row += 1
        ttk.Label(parent, text=solver_spec.hint, wraplength=560, justify="left").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )

        self._solver_tab_state[solver_spec.key] = {
            "spec": solver_spec,
            "instance_path": instance_path,
            "instance_combo": instance_combo,
            "selected_instance_path": "",
            "info_n": info_n,
            "info_m": info_m,
            "info_ratio": info_ratio,
            "parameters": parameter_vars,
        }

    def _build_batch_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(parent, text="Dataset folder (pre-generated instances)").grid(row=row, column=0, sticky="w", pady=2)
        row += 1

        dataset_frame = ttk.Frame(parent)
        dataset_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        dataset_frame.columnconfigure(0, weight=1)

        self.batch_dataset_dir = tk.StringVar(value=str((PROJECT_ROOT.parent / "data" / "instances")))
        ttk.Entry(dataset_frame, textvariable=self.batch_dataset_dir, width=60).grid(row=0, column=0, sticky="ew")
        ttk.Button(dataset_frame, text="Browse…", command=self._on_browse_dataset_folder).grid(row=0, column=1, sticky="w", padx=(6, 0))

        row += 1
        ttk.Label(parent, text="Found instances:").grid(row=row, column=0, sticky="w", pady=2)
        self.batch_dataset_count_var = tk.StringVar(value="0")
        ttk.Label(parent, textvariable=self.batch_dataset_count_var).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(parent, text="Algorithm").grid(row=row, column=0, sticky="w", pady=2)
        self.batch_algorithm = tk.StringVar(value="Hill Climbing")
        self.batch_algorithm_combo = ttk.Combobox(
            parent,
            textvariable=self.batch_algorithm,
            values=("Hill Climbing", "Simulated Annealing", "Tabu Search"),
            state="readonly",
            width=24,
        )
        self.batch_algorithm_combo.grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(parent, text="Solver base seed").grid(row=row, column=0, sticky="w", pady=2)
        self.batch_solver_base_seed = tk.StringVar(value="42")
        ttk.Entry(parent, textvariable=self.batch_solver_base_seed, width=14).grid(
            row=row, column=1, sticky="w", pady=2
        )

        row += 1
        ttk.Label(parent, text="Max iterations / restart (blank = auto)").grid(
            row=row, column=0, sticky="w", pady=2
        )
        self.batch_max_iter = tk.StringVar(value="")
        ttk.Entry(parent, textvariable=self.batch_max_iter, width=14).grid(
            row=row, column=1, sticky="w", pady=2
        )

        row += 1
        ttk.Label(parent, text="Max random restarts").grid(row=row, column=0, sticky="w", pady=2)
        self.batch_max_restarts = tk.StringVar(value="8")
        ttk.Entry(parent, textvariable=self.batch_max_restarts, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(parent, text="Initial temperature (SA)").grid(row=row, column=0, sticky="w", pady=2)
        self.batch_initial_temperature = tk.StringVar(value="10.0")
        ttk.Entry(parent, textvariable=self.batch_initial_temperature, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(parent, text="Cooling rate (SA)").grid(row=row, column=0, sticky="w", pady=2)
        self.batch_cooling_rate = tk.StringVar(value="0.995")
        ttk.Entry(parent, textvariable=self.batch_cooling_rate, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(parent, text="Minimum temperature (SA)").grid(row=row, column=0, sticky="w", pady=2)
        self.batch_min_temperature = tk.StringVar(value="0.01")
        ttk.Entry(parent, textvariable=self.batch_min_temperature, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(parent, text="Tabu tenure (Tabu)").grid(row=row, column=0, sticky="w", pady=2)
        self.batch_tabu_tenure = tk.StringVar(value="12")
        ttk.Entry(parent, textvariable=self.batch_tabu_tenure, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        btn = ttk.Button(parent, text="Run full grid", command=self._on_run_batch)
        btn.grid(row=row, column=0, columnspan=2, pady=10, sticky="w")

        row += 1
        self.batch_progress = ttk.Progressbar(parent, mode="determinate", maximum=100, value=0)
        self.batch_progress.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        # Batch UI: visible progress info (not just logs)
        row += 1
        info_frame = ttk.Frame(parent)
        info_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(2, 6))
        for c in range(2):
            info_frame.columnconfigure(c, weight=1)
        self.batch_current_file_var = tk.StringVar(value="-")
        self.batch_progress_text_var = tk.StringVar(value="Completed 0 / 0")
        self.batch_last_result_var = tk.StringVar(value="—")
        ttk.Label(info_frame, text="Current instance:").grid(row=0, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.batch_current_file_var).grid(row=0, column=1, sticky="w")
        ttk.Label(info_frame, text="Progress:").grid(row=1, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.batch_progress_text_var).grid(row=1, column=1, sticky="w")
        ttk.Label(info_frame, text="Last result:").grid(row=2, column=0, sticky="w")
        ttk.Label(info_frame, textvariable=self.batch_last_result_var).grid(row=2, column=1, sticky="w")

        row += 1
        hint = (
            "Runs the selected algorithm (Hill Climbing, Simulated Annealing, or Tabu Search) "
            "on all pre-generated instances in the selected dataset folder. Writes "
            "results/batch_results_<algorithm>.csv plus runtime and satisfaction plots in results/plots/."
        )
        ttk.Label(parent, text=hint, wraplength=560, justify="left").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )

        # Initial count preview
        self._refresh_dataset_preview()

    def _append_log(self, text: str) -> None:
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _poll_work_queue(self) -> None:
        try:
            while True:
                kind, payload = self._work_queue.get_nowait()
                if kind == "log":
                    self._append_log(str(payload))
                elif kind == "status":
                    self._set_status(str(payload))
                elif kind == "batch_progress":
                    completed, total = payload  # type: ignore[misc]
                    self._batch_completed = int(completed)
                    self._batch_total_cells = int(total)
                    if total > 0:
                        self.batch_progress["maximum"] = total
                        self.batch_progress["value"] = completed
                    self.batch_progress_text_var.set(f"Completed {self._batch_completed} / {self._batch_total_cells}")
                elif kind == "batch_file":
                    self.batch_current_file_var.set(str(payload))
                elif kind == "batch_last_result":
                    self.batch_last_result_var.set(str(payload))
                elif kind == "error":
                    messagebox.showerror("Error", str(payload))
                elif kind == "done":
                    messagebox.showinfo("Finished", str(payload))
        except queue.Empty:
            pass
        self.after(150, self._poll_work_queue)

    def _refresh_instance_list(self) -> None:
        """Search common locations and update all solver tabs."""
        candidates: List[str] = []
        search_roots = (
            PROJECT_ROOT.parent / "data" / "instances",
            PROJECT_ROOT / "data" / "instances",
            PROJECT_ROOT / "instances",
        )
        for base in search_roots:
            if base.exists():
                for path in base.rglob("3sat_*.json"):
                    try:
                        n, m = self._read_instance_size(path)
                        label = f"n={n} | m={m} | file: {path.name}"
                    except Exception:
                        label = f"file: {path.name}"
                    candidates.append(f"{label}||{str(path)}")

        candidates = sorted(set(candidates))
        self._instance_choices = candidates
        display_values = [entry.split("||", 1)[0] for entry in candidates]

        for solver_key in self._solver_tab_state:
            state = self._solver_tab_state[solver_key]
            combo: ttk.Combobox = state["instance_combo"]  # type: ignore[assignment]
            selected_var: tk.StringVar = state["instance_path"]  # type: ignore[assignment]
            combo["values"] = display_values

            if not display_values:
                state["selected_instance_path"] = ""
                self._update_instance_info_labels(solver_key, "-", "-", "-")
                continue

            if selected_var.get() not in display_values:
                combo.current(0)
                selected_var.set(display_values[0])

            self._on_instance_selected(solver_key)

    def _refresh_dataset_preview(self) -> None:
        dataset_dir = Path(str(self.batch_dataset_dir.get()).strip())
        if dataset_dir.exists():
            count = sum(1 for _ in dataset_dir.rglob("3sat_*.json"))
            self.batch_dataset_count_var.set(f"{count}")
        else:
            self.batch_dataset_count_var.set("0")

    def _on_browse_dataset_folder(self) -> None:
        folder = filedialog.askdirectory(
            title="Select dataset folder (contains 3sat_*.json)",
            initialdir=str(PROJECT_ROOT.parent / "data" / "instances"),
        )
        if folder:
            self.batch_dataset_dir.set(folder)
            self._refresh_dataset_preview()

    def _on_browse_instance(self, solver_key: str) -> None:
        file_path = filedialog.askopenfilename(
            title="Select SAT Instance JSON",
            filetypes=[("JSON files", "*.json")],
            initialdir=str((PROJECT_ROOT.parent / "data" / "instances"))
        )
        if file_path:
            try:
                n, m = self._read_instance_size(Path(file_path))
                label = f"n={n} | m={m} | file: {Path(file_path).name}"
            except Exception:
                label = f"file: {Path(file_path).name}"

            entry = f"{label}||{file_path}"
            if entry not in self._instance_choices:
                self._instance_choices.append(entry)
            self._instance_choices = sorted(set(self._instance_choices))

            state = self._solver_tab_state[solver_key]
            selected_var: tk.StringVar = state["instance_path"]  # type: ignore[assignment]
            selected_var.set(label)
            self._refresh_instance_list()
            self._on_instance_selected(solver_key)

    def _on_instance_selected(self, solver_key: str) -> None:
        state = self._solver_tab_state[solver_key]
        selected_var: tk.StringVar = state["instance_path"]  # type: ignore[assignment]
        display = selected_var.get()

        entry = None
        for item in self._instance_choices:
            if item.startswith(display + "||"):
                entry = item
                break

        if entry is None:
            state["selected_instance_path"] = ""
            self._update_instance_info_labels(solver_key, "-", "-", "-")
            return

        file_path = entry.split("||", 1)[1]
        try:
            n, m = self._read_instance_size(Path(file_path))
            ratio = (m / n) if n else 0.0
            self._update_instance_info_labels(solver_key, str(n), str(m), f"{ratio:.3f}")
            state["selected_instance_path"] = file_path
        except Exception:
            state["selected_instance_path"] = ""
            self._update_instance_info_labels(solver_key, "-", "-", "-")

    def _read_instance_size(self, instance_path: Path) -> Tuple[int, int]:
        import json

        with instance_path.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
        return int(data.get("n", 0)), int(data.get("m", 0))

    def _update_instance_info_labels(self, solver_key: str, n_value: str, m_value: str, ratio_value: str) -> None:
        state = self._solver_tab_state[solver_key]
        info_n_var: tk.StringVar = state["info_n"]  # type: ignore[assignment]
        info_m_var: tk.StringVar = state["info_m"]  # type: ignore[assignment]
        info_ratio_var: tk.StringVar = state["info_ratio"]  # type: ignore[assignment]
        info_n_var.set(n_value)
        info_m_var.set(m_value)
        info_ratio_var.set(ratio_value)

    def _read_solver_int(self, solver_key: str, parameter_key: str, parameter_label: str) -> int:
        state = self._solver_tab_state[solver_key]
        parameter_vars: Dict[str, tk.StringVar] = state["parameters"]  # type: ignore[assignment]
        try:
            return int(parameter_vars[parameter_key].get().strip())
        except ValueError as exc:
            raise ValueError(f"{parameter_label} must be an integer.") from exc

    def _read_solver_float(self, solver_key: str, parameter_key: str, parameter_label: str) -> float:
        state = self._solver_tab_state[solver_key]
        parameter_vars: Dict[str, tk.StringVar] = state["parameters"]  # type: ignore[assignment]
        try:
            return float(parameter_vars[parameter_key].get().strip())
        except ValueError as exc:
            raise ValueError(f"{parameter_label} must be a number.") from exc

    def _load_selected_instance_for_solver(self, solver_key: str) -> Tuple[str, int, int]:
        state = self._solver_tab_state[solver_key]
        selected_path = str(state.get("selected_instance_path", ""))
        if not selected_path:
            raise ValueError("Please select a SAT instance first.")

        num_variables, num_clauses = self._read_instance_size(Path(selected_path))
        if num_variables < 3 or num_clauses < 1:
            raise ValueError("The selected SAT instance is invalid for 3-SAT.")
        return selected_path, num_variables, num_clauses

    def _on_run_hill_climbing(self) -> None:
        solver_key = "hill_climbing"
        try:
            selected_path, num_variables, num_clauses = self._load_selected_instance_for_solver(solver_key)
            solver_seed = self._read_solver_int(solver_key, "solver_seed", "Solver seed")
            max_iterations = self._read_solver_int(
                solver_key,
                "max_iterations_per_restart",
                "Max iterations / restart",
            )
            max_restarts = self._read_solver_int(solver_key, "max_random_restarts", "Max random restarts")

            if max_iterations < 1:
                raise ValueError("Max iterations / restart must be at least 1.")
            if max_restarts < 1:
                raise ValueError("Max random restarts must be at least 1.")
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        def run_solver(formula: Any) -> Any:
            return hill_climb_with_random_restarts(
                formula,
                max_iterations_per_restart=max_iterations,
                max_random_restarts=max_restarts,
                random_seed=solver_seed,
            )

        self._run_single_solver(
            solver_name="Hill Climbing",
            selected_path=selected_path,
            num_variables=num_variables,
            num_clauses=num_clauses,
            plot_file_name="gui_hill_climbing_convergence.png",
            run_solver=run_solver,
            iterations_label="Iterations (improving flips)",
        )

    def _on_run_simulated_annealing(self) -> None:
        solver_key = "simulated_annealing"
        try:
            selected_path, num_variables, num_clauses = self._load_selected_instance_for_solver(solver_key)
            solver_seed = self._read_solver_int(solver_key, "solver_seed", "Solver seed")
            max_iterations = self._read_solver_int(solver_key, "max_iterations", "Max iterations")
            initial_temperature = self._read_solver_float(
                solver_key,
                "initial_temperature",
                "Initial temperature",
            )
            cooling_rate = self._read_solver_float(solver_key, "cooling_rate", "Cooling rate")
            min_temperature = self._read_solver_float(solver_key, "min_temperature", "Minimum temperature")

            if max_iterations < 1:
                raise ValueError("Max iterations must be at least 1.")
            if initial_temperature <= 0.0:
                raise ValueError("Initial temperature must be greater than 0.")
            if cooling_rate <= 0.0 or cooling_rate >= 1.0:
                raise ValueError("Cooling rate must be between 0 and 1.")
            if min_temperature <= 0.0:
                raise ValueError("Minimum temperature must be greater than 0.")
            if min_temperature >= initial_temperature:
                raise ValueError("Minimum temperature must be less than initial temperature.")
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        def run_solver(formula: Any) -> Any:
            return simulated_annealing_search(
                formula,
                max_iterations=max_iterations,
                initial_temperature=initial_temperature,
                cooling_rate=cooling_rate,
                min_temperature=min_temperature,
                random_seed=solver_seed,
            )

        self._run_single_solver(
            solver_name="Simulated Annealing",
            selected_path=selected_path,
            num_variables=num_variables,
            num_clauses=num_clauses,
            plot_file_name="gui_simulated_annealing_convergence.png",
            run_solver=run_solver,
            iterations_label="Iterations",
        )

    def _on_run_tabu_search(self) -> None:
        solver_key = "tabu_search"
        try:
            selected_path, num_variables, num_clauses = self._load_selected_instance_for_solver(solver_key)
            solver_seed = self._read_solver_int(solver_key, "solver_seed", "Solver seed")
            max_iterations = self._read_solver_int(solver_key, "max_iterations", "Max iterations")
            tabu_tenure = self._read_solver_int(solver_key, "tabu_tenure", "Tabu tenure")

            if max_iterations < 1:
                raise ValueError("Max iterations must be at least 1.")
            if tabu_tenure < 1:
                raise ValueError("Tabu tenure must be at least 1.")
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        def run_solver(formula: Any) -> Any:
            return tabu_search_solve(
                formula,
                max_iterations=max_iterations,
                tabu_tenure=tabu_tenure,
                random_seed=solver_seed,
            )

        self._run_single_solver(
            solver_name="Tabu Search",
            selected_path=selected_path,
            num_variables=num_variables,
            num_clauses=num_clauses,
            plot_file_name="gui_tabu_search_convergence.png",
            run_solver=run_solver,
            iterations_label="Iterations",
        )

    def _run_single_solver(
        self,
        *,
        solver_name: str,
        selected_path: str,
        num_variables: int,
        num_clauses: int,
        plot_file_name: str,
        run_solver: Callable[[Any], Any],
        iterations_label: str,
    ) -> None:
        ratio = num_clauses / num_variables if num_variables else 0.0

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        PLOTS_DIR.mkdir(parents=True, exist_ok=True)

        self._set_status(f"Running {solver_name}...")
        self._append_log(f"--- {solver_name} started on: {Path(selected_path).name} ---")

        def worker() -> None:
            if not selected_path:
                self._work_queue.put(("error", "No instance selected."))
                self._work_queue.put(("status", "Error."))
                return

            try:
                formula = load_instance_formula_from_file(selected_path)
                result = run_solver(formula)

                plot_path = PLOTS_DIR / plot_file_name
                plot_convergence_history(
                    result.merit_history,
                    result.total_clauses,
                    output_path=plot_path,
                    title=f"{solver_name} (n={num_variables}, m={num_clauses}, ratio={ratio:.3f})",
                )

                lines = [
                    f"[{solver_name}] n={num_variables}, m={num_clauses}, m/n ~ {ratio:.4f}",
                    f"[{solver_name}] Satisfied clauses: {result.best_merit} / {result.total_clauses}",
                    f"[{solver_name}] Fully satisfied: {result.fully_satisfied}",
                    f"[{solver_name}] {iterations_label}: {result.iterations_used}",
                    f"[{solver_name}] Restarts used: {result.restart_count}",
                    f"[{solver_name}] Runtime: {result.runtime_seconds:.4f} s",
                    f"[{solver_name}] Convergence plot: {plot_path}",
                ]
                for line in lines:
                    self._work_queue.put(("log", line))

                self._work_queue.put(("status", f"{solver_name} finished."))
                self._work_queue.put(("done", f"{solver_name} plot saved:\n{plot_path}"))
            except Exception as exc:
                self._work_queue.put(("log", traceback.format_exc()))
                self._work_queue.put(("status", "Error."))
                self._work_queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_run_batch(self) -> None:
        try:
            algorithm_name = self.batch_algorithm.get().strip()
            base_solver_seed = int(self.batch_solver_base_seed.get().strip())
            max_restarts = int(self.batch_max_restarts.get().strip())
        except ValueError as exc:
            messagebox.showerror("Invalid input", "Solver base seed and max random restarts must be integers.")
            return

        max_iter_raw = self.batch_max_iter.get().strip()
        if max_iter_raw == "":
            per_restart = None
        else:
            try:
                per_restart = int(max_iter_raw)
            except ValueError:
                messagebox.showerror("Invalid input", "Max iterations must be an integer or blank.")
                return
            if per_restart < 1:
                messagebox.showerror("Invalid input", "Max iterations must be at least 1.")
                return

        try:
            batch_initial_temperature = float(self.batch_initial_temperature.get().strip())
            batch_cooling_rate = float(self.batch_cooling_rate.get().strip())
            batch_min_temperature = float(self.batch_min_temperature.get().strip())
            batch_tabu_tenure = int(self.batch_tabu_tenure.get().strip())
        except ValueError:
            messagebox.showerror(
                "Invalid input",
                "SA fields must be numeric and tabu tenure must be an integer.",
            )
            return

        if batch_initial_temperature <= 0.0:
            messagebox.showerror("Invalid input", "Initial temperature must be greater than 0.")
            return
        if batch_cooling_rate <= 0.0 or batch_cooling_rate >= 1.0:
            messagebox.showerror("Invalid input", "Cooling rate must be between 0 and 1.")
            return
        if batch_min_temperature <= 0.0:
            messagebox.showerror("Invalid input", "Minimum temperature must be greater than 0.")
            return
        if batch_min_temperature >= batch_initial_temperature:
            messagebox.showerror(
                "Invalid input",
                "Minimum temperature must be less than initial temperature.",
            )
            return
        if batch_tabu_tenure < 1:
            messagebox.showerror("Invalid input", "Tabu tenure must be at least 1.")
            return
        if max_restarts < 1:
            messagebox.showerror("Invalid input", "Max random restarts must be at least 1.")
            return

        algorithm_key = algorithm_name.lower().replace(" ", "_")
        if algorithm_key not in ("hill_climbing", "simulated_annealing", "tabu_search"):
            messagebox.showerror("Invalid input", f"Unsupported algorithm: {algorithm_name}")
            return

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PLOTS_DIR.mkdir(parents=True, exist_ok=True)

        # Scan chosen dataset folder for supported instance files
        dataset_dir = Path(str(self.batch_dataset_dir.get()).strip())
        if not dataset_dir.exists():
            messagebox.showerror("Invalid dataset folder", "Please select a valid dataset directory containing 3sat_*.json.")
            return

        instance_files = sorted(set(dataset_dir.rglob("3sat_*.json")))
        if not instance_files:
            messagebox.showerror("No instances found", "Could not find any JSON instances (3sat_*.json) in the selected folder.")
            return

        self.batch_progress["value"] = 0
        self.batch_progress["maximum"] = max(len(instance_files), 1)
        self._batch_total_cells = len(instance_files)
        self._batch_completed = 0
        self._set_status(f"Running {algorithm_name} batch...")
        self._append_log(f"--- Batch started with {algorithm_name} ({len(instance_files)} instances) ---")

        def worker() -> None:
            try:
                import csv, json
                completed = 0
                results_rows: List[dict] = []
                runtime_records: List[SingleRunRecord] = []

                for file_path in instance_files:
                    n = 0
                    m = 0
                    ratio = 0.0
                    parsed_seed = ""
                    try:
                        with file_path.open("r", encoding="utf-8") as f:
                            data = json.load(f)

                        clauses = data.get("clauses", [])
                        if not isinstance(clauses, list):
                            clauses = []

                        if "n" in data and data["n"] is not None:
                            n = int(data["n"])
                        else:
                            max_abs_lit = 0
                            for clause in clauses:
                                for lit in clause:
                                    max_abs_lit = max(max_abs_lit, abs(int(lit)))
                            n = max_abs_lit

                        m = int(data["m"]) if "m" in data and data["m"] is not None else int(len(clauses))
                        ratio = float(data.get("ratio", (m / n) if n else 0.0))
                        parsed_seed = data.get("seed", "")

                        self._work_queue.put(("log", f"Running instance {file_path.name} ..."))
                        self._work_queue.put(("batch_file", file_path.name))

                        max_iterations = per_restart if per_restart is not None else max(400, 15 * n)
                        solver_seed = base_solver_seed + completed

                        formula = load_instance_formula_from_file(str(file_path))
                        if algorithm_key == "hill_climbing":
                            result = hill_climb_with_random_restarts(
                                formula,
                                max_iterations_per_restart=max_iterations,
                                max_random_restarts=max_restarts,
                                random_seed=solver_seed,
                            )
                        elif algorithm_key == "simulated_annealing":
                            result = simulated_annealing_search(
                                formula,
                                max_iterations=max_iterations,
                                initial_temperature=batch_initial_temperature,
                                cooling_rate=batch_cooling_rate,
                                min_temperature=batch_min_temperature,
                                random_seed=solver_seed,
                            )
                        else:
                            result = tabu_search_solve(
                                formula,
                                max_iterations=max_iterations,
                                tabu_tenure=batch_tabu_tenure,
                                random_seed=solver_seed,
                            )

                        self._work_queue.put(
                            (
                                "log",
                                "Finished "
                                f"{file_path.name}: satisfied {result.best_merit}/{result.total_clauses} "
                                f"(fully_satisfied={bool(result.fully_satisfied)}) | runtime={result.runtime_seconds:.4f}s "
                                f"| iterations={result.iterations_used} | restarts={result.restart_count}",
                            )
                        )
                        self._work_queue.put(
                            (
                                "batch_last_result",
                                f"satisfied {result.best_merit}/{result.total_clauses} "
                                f"| fully_satisfied={bool(result.fully_satisfied)} "
                                f"| runtime={result.runtime_seconds:.4f}s",
                            )
                        )

                        row = {
                            "source_file": str(file_path),
                            "instance_file": file_path.name,
                            "algorithm": algorithm_name,
                            "n": n,
                            "m": m,
                            "ratio": round(ratio, 6),
                            "satisfied_clauses": result.best_merit,
                            "fully_satisfied": bool(result.fully_satisfied),
                            "iterations": result.iterations_used,
                            "restarts": result.restart_count,
                            "runtime_seconds": result.runtime_seconds,
                            "parsed_n": n,
                            "parsed_m": m,
                            "parsed_ratio": round(ratio, 6),
                            "parsed_seed": parsed_seed if parsed_seed is not None else "",
                        }
                        results_rows.append(row)

                        # Create a record for plotting runtime vs. n using the same dataclass
                        # as the rest of the project.
                        satisfaction_rate = (result.best_merit / result.total_clauses) if result.total_clauses else 0.0
                        best_assignment_repr = json.dumps(list(bool(v) for v in result.best_assignment))
                        runtime_records.append(
                            SingleRunRecord(
                                num_variables=n,
                                clause_density_ratio=ratio,
                                num_clauses=m,
                                satisfied_clauses=result.best_merit,
                                total_clauses=result.total_clauses,
                                fully_satisfied=bool(result.fully_satisfied),
                                satisfaction_rate=satisfaction_rate,
                                iterations=result.iterations_used,
                                runtime_seconds=result.runtime_seconds,
                                random_seed=solver_seed,
                                restart_count=result.restart_count,
                                best_assignment_repr=best_assignment_repr,
                            )
                        )
                    except Exception as run_exc:
                        self._work_queue.put(("log", f"Error on {file_path.name}: {run_exc}"))
                        results_rows.append(
                            {
                                "source_file": str(file_path),
                                "instance_file": file_path.name,
                                "algorithm": algorithm_name,
                                "n": n,
                                "m": m,
                                "ratio": round(ratio, 6),
                                "satisfied_clauses": "",
                                "fully_satisfied": "",
                                "iterations": "",
                                "restarts": "",
                                "runtime_seconds": "",
                                "parsed_n": n,
                                "parsed_m": m,
                                "parsed_ratio": round(ratio, 6),
                                "parsed_seed": parsed_seed if parsed_seed is not None else "",
                            }
                        )
                    finally:
                        completed += 1
                        self._work_queue.put(("batch_progress", (completed, len(instance_files))))

                output_csv = RESULTS_DIR / f"batch_results_{algorithm_key}.csv"
                with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
                    fieldnames = [
                        "source_file",
                        "instance_file",
                        "algorithm",
                        "n",
                        "m",
                        "ratio",
                        "satisfied_clauses",
                        "fully_satisfied",
                        "iterations",
                        "restarts",
                        "runtime_seconds",
                        "parsed_n",
                        "parsed_m",
                        "parsed_ratio",
                        "parsed_seed",
                    ]
                    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    writer.writeheader()
                    for row in results_rows:
                        writer.writerow(row)

                self._work_queue.put(("log", f"CSV: {output_csv}"))

                if runtime_records:
                    batch_plot_path = PLOTS_DIR / f"batch_runtime_vs_num_variables_{algorithm_key}.png"
                    plot_runtime_vs_num_variables(
                        runtime_records,
                        output_path=batch_plot_path,
                        title=f"{algorithm_name} runtime vs. n (batch instances)",
                    )
                    self._work_queue.put(("log", f"Plot: {batch_plot_path}"))

                    satisfied_plot_path = PLOTS_DIR / f"batch_satisfied_vs_num_variables_{algorithm_key}.png"
                    plot_satisfied_clauses_vs_num_variables(
                        runtime_records,
                        output_path=satisfied_plot_path,
                        title=f"{algorithm_name} satisfied clauses vs. n (batch instances)",
                    )
                    self._work_queue.put(("log", f"Plot: {satisfied_plot_path}"))

                    rate_plot_path = PLOTS_DIR / f"batch_satisfaction_rate_vs_num_variables_{algorithm_key}.png"
                    plot_satisfaction_rate_vs_num_variables(
                        runtime_records,
                        output_path=rate_plot_path,
                        title=f"{algorithm_name} satisfaction rate vs. n (batch instances)",
                    )
                    self._work_queue.put(("log", f"Plot: {rate_plot_path}"))
                self._work_queue.put(("status", "Batch finished."))
                self._work_queue.put(("done", f"Saved {len(results_rows)} results to:\n{output_csv}"))
            except Exception as exc:
                self._work_queue.put(("log", traceback.format_exc()))
                self._work_queue.put(("status", "Batch failed."))
                self._work_queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    """Launch the  application."""
    root = tk.Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    SatControlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
