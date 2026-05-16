from __future__ import annotations

from dataclasses import dataclass
from tkinter import ttk
import tkinter as tk
from typing import Dict


@dataclass
class ComparisonTabState:
    instance_var: tk.StringVar
    runs_var: tk.StringVar
    base_seed_var: tk.StringVar
    seed_mode_var: tk.StringVar
    same_seed_var: tk.BooleanVar
    include_scaling_var: tk.BooleanVar
    selected_solver_vars: Dict[str, tk.BooleanVar]
    summary_tree: ttk.Treeview
    per_run_tree: ttk.Treeview


def build_solver_checkbox_frame(parent: ttk.Frame, selected_solver_vars: Dict[str, tk.BooleanVar]) -> None:
    frame = ttk.LabelFrame(parent, text="Solvers to include", padding=6)
    frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(6, 6))
    for index, (key, var) in enumerate(selected_solver_vars.items()):
        label = key.replace("_", " ").title().replace("Bsgo", "BSGO").replace("Ga", "GA")
        ttk.Checkbutton(frame, text=label, variable=var).grid(row=index // 3, column=index % 3, sticky="w", padx=4, pady=3)
