"""
Random 3-SAT instance generation.

Each generated clause uses three distinct variables from {0,..,n-1} and
each literal is independently negated with probability one half.
"""

from __future__ import annotations

import random
from pathlib import Path
import json
from typing import List, Optional, Sequence, Tuple

try:
    random  # touch to keep import order tools from flagging reordering
    from .utils import (  # type: ignore
        CNFFormula,
        Clause,
        Literal,
        validate_formula,
        validate_3sat_formula,
    )
except Exception:
    # Fallback for running this file directly (not as package module).
    from utils import (  # type: ignore
        CNFFormula,
        Clause,
        Literal,
        validate_formula,
        validate_3sat_formula,
    )


def _sample_clause(num_variables: int, rng: random.Random) -> Clause:
    """
    Draw one random 3-literal clause: three distinct variables, random signs.

    Args:
        num_variables: Number of variables n (must be at least 3).
        rng: Random number generator instance for reproducibility.

    Returns:
        A tuple of three Literal objects.
    """
    chosen_indices = rng.sample(range(num_variables), k=3)
    literals: List[Literal] = []
    for variable_index in chosen_indices:
        is_negated = rng.choice((False, True))
        literals.append(Literal(variable_index=variable_index, is_negated=is_negated))
    return (literals[0], literals[1], literals[2])


def generate_random_3sat(
    num_variables: int,
    num_clauses: int,
    *,
    random_seed: Optional[int] = None,
) -> CNFFormula:
    """
    Generate a random 3-SAT CNF formula.

    Args:
        num_variables: Number of variables n (must be >= 3 so each clause can
            contain 3 distinct variables).
        num_clauses: Number of clauses m (must be >= 1).
        random_seed: If set, passed to ``random.Random`` for repeatable instances.

    Returns:
        A validated CNFFormula instance.

    Raises:
        ValueError: If inputs are out of range or structurally impossible.
    """
    if num_variables < 3:
        raise ValueError("num_variables must be at least 3 for 3-SAT (distinct vars per clause).")
    if num_clauses < 1:
        raise ValueError("num_clauses must be at least 1.")

    rng = random.Random(random_seed)
    clauses: List[Clause] = [
        _sample_clause(num_variables=num_variables, rng=rng) for _ in range(num_clauses)
    ]

    formula = CNFFormula(num_variables=num_variables, clauses=tuple(clauses))
    validate_3sat_formula(formula)
    return formula


def compute_clause_count_from_density(num_variables: int, clause_density_ratio: float) -> int:
    """
    Compute m = round(ratio * n), at least 1, for experiment grid cells.

    Args:
        num_variables: n
        clause_density_ratio: m/n (e.g. 3.0, 4.3, 6.0)

    Returns:
        Integer clause count m.
    """
    if num_variables < 1:
        raise ValueError("num_variables must be positive.")
    if clause_density_ratio <= 0:
        raise ValueError("clause_density_ratio must be positive.")

    if num_variables < 3:
        # Cannot form valid 3-SAT; caller should skip or use n >= 3.
        return max(1, int(round(clause_density_ratio * num_variables)))

    raw = round(clause_density_ratio * num_variables)
    return max(1, int(raw))


# =========================
# Assignment-specific API
# =========================

# Project root is one level above this file (sat_project/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_INSTANCES_DIR = _PROJECT_ROOT / "data" / "instances"


def _formula_to_literal_ints(formula: CNFFormula) -> List[List[int]]:
    """
    Convert internal representation (0-based variables + negation flag)
    to assignment-specified JSON encoding:
      - positive integer k means x_k (1-based)
      - negative integer -k means ¬x_k (1-based)
    """
    encoded: List[List[int]] = []
    for clause in formula.clauses:
        ints: List[int] = []
        for literal in clause:
            one_based = literal.variable_index + 1
            ints.append(-one_based if literal.is_negated else one_based)
        encoded.append(ints)
    return encoded


def _instance_filename(n: int, ratio: float, *, instance_index: Optional[int] = None) -> str:
    """
    Build file name using compact ratio formatting.
    Single-instance:  3sat_n100_r4.3.json
    Multi-instance:   3sat_n100_r4.3_i07.json  (zero-padded index)
    """
    ratio_token = f"{ratio:g}"
    if instance_index is None:
        return f"3sat_n{n}_r{ratio_token}.json"
    return f"3sat_n{n}_r{ratio_token}_i{instance_index:02d}.json"


def generate_3sat_instance(n: int, ratio: float, seed: int = 42) -> dict:
    """
    Generate one random 3-SAT instance (deterministic given n, ratio, seed).
    Returns a dict ready to be serialized per assignment spec.
    """
    if n < 3:
        raise ValueError("n must be at least 3 for valid 3-SAT (3 distinct vars per clause).")
    m = compute_clause_count_from_density(n, ratio)
    formula = generate_random_3sat(num_variables=n, num_clauses=m, random_seed=seed)
    clauses_as_ints = _formula_to_literal_ints(formula)
    payload = {
        "n": n,
        "m": m,
        "ratio": float(ratio),
        "clauses": clauses_as_ints,
    }
    return payload


def _save_instance(payload: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def infer_num_variables_from_clauses(clauses_ints: Sequence[Sequence[int]]) -> int:
    """
    Infer n from 1-based integer literals: n = max abs(literal) over all clauses.

    Raises:
        ValueError: If no positive literal magnitude is found.
    """
    max_abs = 0
    for clause in clauses_ints:
        for lit in clause:
            max_abs = max(max_abs, abs(int(lit)))
    if max_abs < 1:
        raise ValueError("Cannot infer num_variables: clauses contain no literals.")
    return max_abs


def _literal_ints_to_formula(n: int, clauses_ints: Sequence[Sequence[int]]) -> CNFFormula:
    """
    Convert literal encoding (1-based ints, negative for NOT) to ``CNFFormula``.

    Each inner sequence is one clause (OR of literals); clause length may vary.
    """
    clauses: List[Clause] = []
    for clause_index, clause_values in enumerate(clauses_ints):
        if not clause_values:
            raise ValueError(f"Clause {clause_index} is empty (not allowed in CNF).")
        lit_objs: List[Literal] = []
        for raw_value in clause_values:
            value = int(raw_value)
            is_neg = value < 0
            var_one_based = -value if is_neg else value
            if var_one_based < 1:
                raise ValueError(f"Clause {clause_index}: invalid literal encoding {raw_value!r}.")
            var_zero_based = var_one_based - 1
            if var_zero_based >= n:
                raise ValueError(
                    f"Clause {clause_index}: literal {raw_value!r} implies variable index "
                    f"{var_zero_based} but num_variables is n={n}."
                )
            lit_objs.append(Literal(variable_index=var_zero_based, is_negated=is_neg))
        clauses.append(tuple(lit_objs))
    formula = CNFFormula(num_variables=n, clauses=tuple(clauses))
    validate_formula(formula)
    return formula


def formula_from_int_clauses(
    clauses_ints: Sequence[Sequence[int]],
    *,
    num_variables: Optional[int] = None,
) -> CNFFormula:
    """
    Build a ``CNFFormula`` from MAX-SAT style clauses (lists of signed integers).

    Args:
        clauses_ints: Each clause is a sequence of non-zero integers; ``k`` means x_k,
            ``-k`` means NOT x_k (variables are **1-based** in the input).
        num_variables: If omitted, inferred as max |literal| across all clauses.

    Returns:
        Validated formula ready for search / evaluation.
    """
    inferred = infer_num_variables_from_clauses(clauses_ints)
    n = inferred if num_variables is None else int(num_variables)
    if n < 1:
        raise ValueError("num_variables must be at least 1.")
    if n < inferred:
        raise ValueError(
            f"num_variables={n} is smaller than max literal index ({inferred}) inferred from clauses."
        )
    return _literal_ints_to_formula(n, clauses_ints)


def load_instance_formula(n: int, ratio: float) -> CNFFormula:
    """
    Load a saved instance for (n, ratio) from data/instances and parse into CNFFormula.
    Looks for the base (non-indexed) filename per assignment spec.
    """
    file_path = _INSTANCES_DIR / _instance_filename(n, ratio)
    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return _literal_ints_to_formula(int(payload["n"]), payload["clauses"])


def load_instance_formula_from_file(file_path: Path | str) -> CNFFormula:
    """
    Load an instance JSON from an arbitrary path and convert to CNFFormula.
    """
    path_obj = Path(file_path)
    with path_obj.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    clauses = payload.get("clauses")
    if clauses is None:
        raise ValueError(f"Invalid instance file (missing 'clauses'): {path_obj}")

    # Be robust: metadata might be missing; derive n from literals.
    if "n" in payload and payload["n"] is not None:
        n = int(payload["n"])
    else:
        max_abs_lit = 0
        for clause in clauses:
            for lit in clause:
                max_abs_lit = max(max_abs_lit, abs(int(lit)))
        n = max_abs_lit

    return _literal_ints_to_formula(n, clauses)

def generate_all_instances(
    *,
    variable_counts: Sequence[int] = (
        50,
        100,
        150,
        200,
        250,
        300,
        350,
        400,
        450,
        500,
    ),
    clause_density_ratios: Sequence[float] = (3.0, 4.3, 6.0),
    seed: int = 42,
    instances_per_cell: int = 15,
) -> None:
    """
    Loop over all n and ratios, generate instances, and save under data/instances/.
    Skips files that already exist. Prints a summary and the total created count.
    """
    created_count = 0
    summary_lines: List[str] = ["Generated instances:"]

    for n in variable_counts:
        if n < 3:
            # Not valid for 3 distinct variables per clause; skip silently.
            continue
        for ratio in clause_density_ratios:
            m = compute_clause_count_from_density(n, ratio)
            for instance_index in range(instances_per_cell):
                # For exactly one instance per cell, follow assignment base naming without index.
                if instances_per_cell == 1:
                    filename = _instance_filename(n, ratio)
                else:
                    filename = _instance_filename(n, ratio, instance_index=instance_index)
                path = _INSTANCES_DIR / filename
                if path.exists():
                    if instances_per_cell == 1:
                        summary_lines.append(f"n={n} ratio={ratio:g} -> m={m} (skipped, exists)")
                    else:
                        summary_lines.append(
                            f"n={n} ratio={ratio:g} -> m={m} [i={instance_index}] (skipped, exists)"
                        )
                    continue
                # Derive a deterministic seed per (n, ratio, instance) from the base seed
                derived = (
                    seed
                    + n * 1_000_003
                    + int(round(ratio * 10)) * 10_007
                    + instance_index * 100_009
                )
                payload = generate_3sat_instance(n=n, ratio=ratio, seed=derived)
                _save_instance(payload, path)
                created_count += 1
                if instances_per_cell == 1:
                    summary_lines.append(f"n={n} ratio={ratio:g} -> m={m}")
                else:
                    summary_lines.append(f"n={n} ratio={ratio:g} -> m={m} [i={instance_index}]")

    # Print required summary
    for line in summary_lines:
        print(line)
    print(f"\nTotal instances generated: {created_count}")


if __name__ == "__main__":
    # Run the full grid generation when invoked directly.
    generate_all_instances()
