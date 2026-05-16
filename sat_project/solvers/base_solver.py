from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from evaluator import evaluate_maxsat_assignment
from utils import CNFFormula


@dataclass(frozen=True)
class SolverResult:
    algorithm_name: str
    best_assignment: Tuple[bool, ...]
    best_satisfied_clauses: int
    total_clauses: int
    satisfaction_rate: float
    fully_satisfied: bool
    runtime_seconds: float
    iterations_used: int
    best_history: Tuple[int, ...]
    runtime_history: Tuple[float, ...]
    parameter_summary: Dict[str, Any]


class BaseSolver(ABC):
    algorithm_name: str

    @abstractmethod
    def solve(self, formula: CNFFormula, config: Mapping[str, Any]) -> SolverResult:
        raise NotImplementedError


def normalize_result(
    *,
    algorithm_name: str,
    assignment: Sequence[bool],
    runtime_seconds: float,
    iterations_used: int,
    best_history: Sequence[int],
    runtime_history: Sequence[float],
    parameter_summary: Mapping[str, Any],
    formula: CNFFormula,
) -> SolverResult:
    evaluation = evaluate_maxsat_assignment(formula, list(assignment))
    return SolverResult(
        algorithm_name=algorithm_name,
        best_assignment=tuple(bool(v) for v in assignment),
        best_satisfied_clauses=evaluation.satisfied_clauses_count,
        total_clauses=evaluation.total_clauses,
        satisfaction_rate=evaluation.satisfaction_rate,
        fully_satisfied=evaluation.fully_satisfied,
        runtime_seconds=float(runtime_seconds),
        iterations_used=int(iterations_used),
        best_history=tuple(int(v) for v in best_history),
        runtime_history=tuple(float(v) for v in runtime_history),
        parameter_summary=dict(parameter_summary),
    )
