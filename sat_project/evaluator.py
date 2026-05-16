"""
Evaluation of CNF formulas under a truth assignment.

Merit (fitness) for local search is the number of satisfied clauses.
"""

from __future__ import annotations

from dataclasses import dataclass

from utils import CNFFormula, Literal, TruthAssignment


@dataclass(frozen=True)
class MaxSATEvaluation:
    """Detailed MAX-SAT / CNF evaluation of one complete assignment."""

    satisfied_clauses_count: int
    total_clauses: int
    satisfaction_rate: float
    fully_satisfied: bool


def evaluate_maxsat_assignment(formula: CNFFormula, assignment: TruthAssignment) -> MaxSATEvaluation:
    """
    Compute satisfied clause count, rate, and full satisfaction for an assignment.

    Args:
        formula: CNF formula (any clause length >= 1).
        assignment: assignment[var] is True iff variable var is True.

    Returns:
        Structured evaluation metrics.
    """
    total = formula.num_clauses
    satisfied = count_satisfied_clauses(formula, assignment)
    rate = 0.0 if total == 0 else float(satisfied) / float(total)
    return MaxSATEvaluation(
        satisfied_clauses_count=satisfied,
        total_clauses=total,
        satisfaction_rate=rate,
        fully_satisfied=satisfied == total and total > 0,
    )


def evaluate_literal(literal: Literal, assignment: TruthAssignment) -> bool:
    """
    Evaluate one literal under a complete truth assignment.

    Args:
        literal: The literal (variable index + optional negation).
        assignment: assignment[var] is True iff variable var is True.

    Returns:
        Boolean value of the literal.
    """
    variable_value = assignment[literal.variable_index]
    if literal.is_negated:
        return not variable_value
    return variable_value


def is_clause_satisfied(
    clause: tuple[Literal, ...], assignment: TruthAssignment
) -> bool:
    """
    True iff at least one literal in the clause is True (OR semantics).
    """
    return any(evaluate_literal(literal, assignment) for literal in clause)


def count_satisfied_clauses(formula: CNFFormula, assignment: TruthAssignment) -> int:
    """
    Count how many clauses are satisfied by the given assignment.
    """
    satisfied = 0
    for clause in formula.clauses:
        if is_clause_satisfied(clause, assignment):
            satisfied += 1
    return satisfied


def is_formula_fully_satisfied(formula: CNFFormula, assignment: TruthAssignment) -> bool:
    """
    True iff every clause is satisfied (merit equals total number of clauses).
    """
    return count_satisfied_clauses(formula, assignment) == formula.num_clauses


def compute_solution_merit(formula: CNFFormula, assignment: TruthAssignment) -> int:
    """
    Primary fitness score for hill climbing: number of satisfied clauses.

    This is identical to ``count_satisfied_clauses`` but named for clarity
    in optimization / search code paths.
    """
    return count_satisfied_clauses(formula, assignment)


def normalized_satisfaction_rate(formula: CNFFormula, assignment: TruthAssignment) -> float:
    """
    Optional normalized score in [0, 1]: satisfied_clauses / total_clauses.

    Useful when comparing instances with different m; main logic still uses raw counts.
    """
    if formula.num_clauses == 0:
        return 0.0
    return count_satisfied_clauses(formula, assignment) / formula.num_clauses
