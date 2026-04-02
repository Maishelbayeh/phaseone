"""
Desktop control panel (Tkinter) for tuning 3-SAT generation and hill climbing.

Runs heavy work in background threads so the window stays responsive.
Uses only the Python standard library (tkinter).
"""

from __future__ import annotations

import queue
import threading
import traceback
from pathlib import Path
from tkinter import ttk, messagebox, scrolledtext, filedialog
import tkinter as tk
from typing import List, Optional, Tuple

from experiments import (
    DEFAULT_CLAUSE_DENSITY_RATIOS,
    DEFAULT_VARIABLE_COUNTS,
    SingleRunRecord,
    run_single_experiment,
    save_records_csv,
    save_records_json,
)
from hill_climbing import hill_climb_with_random_restarts
from plotting import plot_convergence_history, plot_runtime_vs_num_variables
from sat_generator import compute_clause_count_from_density, load_instance_formula, load_instance_formula_from_file


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
    """Main window: two tabs for single instance vs. batch grid."""

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=10)
        self.master.title("3-SAT Hill Climbing — Control Panel")
        self.master.minsize(640, 520)
        self.grid(row=0, column=0, sticky="nsew")
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)

        self._work_queue: queue.Queue[Tuple[str, object]] = queue.Queue()
        self._batch_total_cells = 0
        self._batch_completed = 0

        notebook = ttk.Notebook(self)
        notebook.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        single_tab = ttk.Frame(notebook, padding=8)
        batch_tab = ttk.Frame(notebook, padding=8)
        notebook.add(single_tab, text="Single run")
        notebook.add(batch_tab, text="Batch grid")

        self._build_single_run_tab(single_tab)
        self._build_batch_tab(batch_tab)

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

    def _build_single_run_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(parent, text="Select SAT Instance").grid(row=row, column=0, sticky="w", pady=2)
        self.single_instance_path = tk.StringVar(value="")
        self.single_instance_combo = ttk.Combobox(parent, textvariable=self.single_instance_path, width=48, state="readonly")
        self.single_instance_combo.grid(row=row, column=1, sticky="ew", pady=2)
        self.single_instance_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_instance_selected())

        row += 1
        browse_frame = ttk.Frame(parent)
        browse_frame.grid(row=row, column=0, columnspan=2, sticky="w")
        ttk.Button(browse_frame, text="Browse…", command=self._on_browse_instance).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Button(browse_frame, text="Refresh", command=self._refresh_instance_list).grid(row=0, column=1, sticky="w")

        row += 1
        info = ttk.LabelFrame(parent, text="Instance details", padding=6)
        info.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        for c in range(2):
            info.columnconfigure(c, weight=1)
        self.info_n = tk.StringVar(value="-")
        self.info_m = tk.StringVar(value="-")
        self.info_ratio = tk.StringVar(value="-")
        ttk.Label(info, text="n =").grid(row=0, column=0, sticky="e")
        ttk.Label(info, textvariable=self.info_n).grid(row=0, column=1, sticky="w")
        ttk.Label(info, text="m =").grid(row=1, column=0, sticky="e")
        ttk.Label(info, textvariable=self.info_m).grid(row=1, column=1, sticky="w")
        ttk.Label(info, text="ratio =").grid(row=2, column=0, sticky="e")
        ttk.Label(info, textvariable=self.info_ratio).grid(row=2, column=1, sticky="w")

        # Solver settings (kept)

        row += 1
        ttk.Label(parent, text="Solver seed").grid(row=row, column=0, sticky="w", pady=2)
        self.single_solver_seed = tk.StringVar(value="456")
        ttk.Entry(parent, textvariable=self.single_solver_seed, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(parent, text="Max iterations / restart").grid(row=row, column=0, sticky="w", pady=2)
        self.single_max_iter = tk.StringVar(value="500")
        ttk.Entry(parent, textvariable=self.single_max_iter, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        ttk.Label(parent, text="Max random restarts").grid(row=row, column=0, sticky="w", pady=2)
        self.single_max_restarts = tk.StringVar(value="8")
        ttk.Entry(parent, textvariable=self.single_max_restarts, width=14).grid(row=row, column=1, sticky="w", pady=2)

        row += 1
        btn = ttk.Button(parent, text="Run single instance", command=self._on_run_single)
        btn.grid(row=row, column=0, columnspan=2, pady=10, sticky="w")

        row += 1
        hint = (
            "Loads the selected pre-generated instance from disk, runs hill climbing, "
            "and saves a convergence plot under results/plots/."
        )
        ttk.Label(parent, text=hint, wraplength=560, justify="left").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )

        # Populate instance list initially
        self._refresh_instance_list()

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
            "Runs hill climbing on all pre-generated instances found in the selected dataset folder. "
            "Writes results/batch_results.csv and results/plots/batch_runtime_vs_num_variables.png."
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
        # Search common locations for instances
        candidates: List[str] = []
        for base in (PROJECT_ROOT.parent / "data" / "instances", PROJECT_ROOT / "data" / "instances", PROJECT_ROOT / "instances"):
            if base.exists():
                for path in base.rglob("3sat_*.json"):
                    # Build display text: n=?, m=?, filename
                    try:
                        import json
                        with path.open("r", encoding="utf-8") as f:
                            data = json.load(f)
                        n = int(data.get("n", 0))
                        m = int(data.get("m", 0))
                        label = f"n={n} | m={m} | file: {path.name}"
                    except Exception:
                        label = f"file: {path.name}"
                    candidates.append(f"{label}||{str(path)}")
        candidates.sort()
        display_values = [entry.split("||", 1)[0] for entry in candidates]
        self._instance_choices = candidates
        self.single_instance_combo["values"] = display_values
        if display_values and not self.single_instance_path.get():
            self.single_instance_combo.current(0)
            self._on_instance_selected()

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

    def _on_browse_instance(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select SAT Instance JSON",
            filetypes=[("JSON files", "*.json")],
            initialdir=str((PROJECT_ROOT.parent / "data" / "instances"))
        )
        if file_path:
            # Set selection directly
            try:
                import json
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                n = int(data.get("n", 0))
                m = int(data.get("m", 0))
                label = f"n={n} | m={m} | file: {Path(file_path).name}"
            except Exception:
                label = f"file: {Path(file_path).name}"
            entry = f"{label}||{file_path}"
            self._instance_choices = getattr(self, "_instance_choices", [])
            self._instance_choices.append(entry)
            self.single_instance_combo["values"] = [e.split("||", 1)[0] for e in self._instance_choices]
            self.single_instance_path.set(label)
            self._on_instance_selected()

    def _on_instance_selected(self) -> None:
        # Update info panel from selected entry
        display = self.single_instance_path.get()
        entry = None
        for item in getattr(self, "_instance_choices", []):
            if item.startswith(display + "||"):
                entry = item
                break
        if entry is None:
            self.info_n.set("-")
            self.info_m.set("-")
            self.info_ratio.set("-")
            return
        file_path = entry.split("||", 1)[1]
        try:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            n = int(data.get("n", 0))
            m = int(data.get("m", 0))
            ratio = (m / n) if n else 0.0
            self.info_n.set(str(n))
            self.info_m.set(str(m))
            self.info_ratio.set(f"{ratio:.3f}")
            self._selected_instance_path = file_path
        except Exception:
            self.info_n.set("-")
            self.info_m.set("-")
            self.info_ratio.set("-")
            self._selected_instance_path = ""

    def _on_run_single(self) -> None:
        try:
            selected_path = getattr(self, "_selected_instance_path", "")
            if not selected_path:
                messagebox.showerror("No instance selected", "Please select a SAT instance first.")
                return
            # Load to extract n/m for display and to build formula
            import json
            with open(selected_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            num_variables = int(data["n"])
            num_clauses = int(data["m"])
            solver_seed = int(self.single_solver_seed.get().strip())
            max_iterations = int(self.single_max_iter.get().strip())
            max_restarts = int(self.single_max_restarts.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid numbers in all single-run fields.")
            return

        if num_variables < 3 or num_clauses < 1:
            messagebox.showerror("Invalid n", "n must be at least 3 for 3-SAT.")
            return
        if max_iterations < 1 or max_restarts < 1:
            messagebox.showerror("Invalid search limits", "Iterations and restarts must be at least 1.")
            return

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        PLOTS_DIR.mkdir(parents=True, exist_ok=True)

        self._set_status("Running single instance…")
        self._append_log(f"--- Single run started on: {Path(selected_path).name} ---")

        def worker() -> None:
            try:
                formula = load_instance_formula_from_file(selected_path)
                result = hill_climb_with_random_restarts(
                    formula,
                    max_iterations_per_restart=max_iterations,
                    max_random_restarts=max_restarts,
                    random_seed=solver_seed,
                )

                plot_path = PLOTS_DIR / "gui_single_convergence.png"
                plot_convergence_history(
                    result.merit_history,
                    result.total_clauses,
                    output_path=plot_path,
                    title=f"Single run (n={num_variables}, m={num_clauses}, ratio={num_clauses / num_variables:.3f})",
                )

                lines = [
                    f"n={num_variables}, m={num_clauses}, m/n ~ {num_clauses / num_variables:.4f}",
                    f"Satisfied clauses: {result.best_merit} / {result.total_clauses}",
                    f"Fully satisfied: {result.fully_satisfied}",
                    f"Iterations (improving flips): {result.iterations_used}",
                    f"Restarts used: {result.restart_count}",
                    f"Runtime: {result.runtime_seconds:.4f} s",
                    f"Convergence plot: {plot_path}",
                ]
                for line in lines:
                    self._work_queue.put(("log", line))

                self._work_queue.put(("status", "Single run finished."))
                self._work_queue.put(("done", f"Saved plot:\n{plot_path}"))
            except Exception as exc:
                self._work_queue.put(("log", traceback.format_exc()))
                self._work_queue.put(("status", "Error."))
                self._work_queue.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_run_batch(self) -> None:
        try:
            # We still read restart/iteration settings from the UI
            max_restarts = int(self.batch_max_restarts.get().strip())
        except ValueError as exc:
            messagebox.showerror("Invalid input", "Max random restarts must be an integer.")
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
        self._set_status("Running batch on saved instances…")
        self._append_log(f"--- Batch started ({len(instance_files)} instances) ---")

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

                        # Determine iteration budget
                        iter_budget = per_restart if per_restart is not None else max(400, 15 * n)

                        # Load formula and run solver
                        formula = load_instance_formula_from_file(str(file_path))
                        result = hill_climb_with_random_restarts(
                            formula,
                            max_iterations_per_restart=iter_budget,
                            max_random_restarts=max_restarts,
                            random_seed=42 + completed,  # deterministic but varies across instances
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
                                random_seed=42 + completed,
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

                # Write CSV summary
                output_csv = RESULTS_DIR / "batch_results.csv"
                with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
                    fieldnames = [
                        "source_file",
                        "instance_file",
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

                # Save a runtime plot so users get an image artifact for the batch run.
                if runtime_records:
                    batch_plot_path = PLOTS_DIR / "batch_runtime_vs_num_variables.png"
                    plot_runtime_vs_num_variables(
                        runtime_records,
                        output_path=batch_plot_path,
                        title="Hill climbing runtime vs. n (batch instances)",
                    )
                    self._work_queue.put(("log", f"Plot: {batch_plot_path}"))
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
