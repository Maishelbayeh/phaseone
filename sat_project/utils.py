"""
Shared types and small helpers for the 3-SAT local search project.

This module keeps literal, clause, and formula representations in one place
so every other module imports the same definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, NamedTuple, Sequence, Tuple


class Literal(NamedTuple):
    """
    One literal in a Boolean CNF clause.

    Attributes:
        variable_index: Zero-based index of the variable (0 .. n-1).
        is_negated: If True, the literal is negation of the variable (NOT x).
    """

    variable_index: int
    is_negated: bool


# A CNF clause is a disjunction (OR) of one or more literals.
Clause = Tuple[Literal, ...]


@dataclass(frozen=True)
class CNFFormula:
    """
    A propositional formula in conjunctive normal form (CNF).

    Attributes:
        num_variables: Number of Boolean variables (n). Variables are indexed 0..n-1.
        clauses: Tuple of clauses; each clause is a tuple of literals (OR).
                 The whole formula is the AND of all clauses.

    Note:
        Clause length may vary (general CNF / MAX-SAT). Random 3-SAT generation
        still produces exactly three literals per clause; use ``validate_3sat_formula``
        after generation when strict 3-SAT invariants are required.
    """

    num_variables: int
    clauses: Tuple[Clause, ...]

    @property
    def num_clauses(self) -> int:
        """Total number of clauses (often denoted m)."""
        return len(self.clauses)


# A complete truth assignment: assignment[i] is the truth value of variable i.
TruthAssignment = List[bool]


def validate_formula(formula: CNFFormula, *, min_literals_per_clause: int = 1) -> None:
    """
    Check structural invariants of a CNF / MAX-SAT formula.

    Args:
        formula: Formula to validate.
        min_literals_per_clause: Minimum literals per clause (default 1).

    Raises:
        ValueError: If num_variables is invalid or any clause is malformed.
    """
    if formula.num_variables < 1:
        raise ValueError("num_variables must be at least 1.")

    for clause_index, clause in enumerate(formula.clauses):
        if len(clause) < min_literals_per_clause:
            raise ValueError(
                f"Clause {clause_index} must contain at least {min_literals_per_clause} "
                f"literal(s); got {len(clause)}."
            )

        for literal in clause:
            if not (0 <= literal.variable_index < formula.num_variables):
                raise ValueError(
                    f"Clause {clause_index}: variable_index {literal.variable_index} "
                    f"out of range for n={formula.num_variables}."
                )


def validate_3sat_formula(formula: CNFFormula) -> None:
    """
    Strict 3-SAT checks: each clause has exactly three literals on distinct variables.

    Raises:
        ValueError: If any clause violates 3-SAT structure.
    """
    for clause_index, clause in enumerate(formula.clauses):
        if len(clause) != 3:
            raise ValueError(
                f"Clause {clause_index} must contain exactly 3 literals; got {len(clause)}."
            )

        seen_variables: set[int] = set()
        for literal in clause:
            if not (0 <= literal.variable_index < formula.num_variables):
                raise ValueError(
                    f"Clause {clause_index}: variable_index {literal.variable_index} "
                    f"out of range for n={formula.num_variables}."
                )
            if literal.variable_index in seen_variables:
                raise ValueError(
                    f"Clause {clause_index}: variable {literal.variable_index} "
                    "appears more than once (must be 3 distinct variables)."
                )
            seen_variables.add(literal.variable_index)


def assignment_from_indices(
    num_variables: int, true_variables: Sequence[int]
) -> TruthAssignment:
    """
    Build a truth assignment where listed indices are True and others False.

    Useful for quick manual tests.
    """
    assignment: TruthAssignment = [False] * num_variables
    for index in true_variables:
        if not (0 <= index < num_variables):
            raise ValueError(f"Variable index {index} out of range.")
        assignment[index] = True
    return assignment
