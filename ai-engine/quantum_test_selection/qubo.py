"""
Step 2: QUBO (Quadratic Unconstrained Binary Optimization) formulation --
the bridge between "which tests to run" and a form both quantum annealers
and QAOA (gate-based, used in quantum_solver.py) can consume.

Q encodes, for binary selection variables x_0..x_{n-1}:

    minimize   x^T Q x
             = -sum_i defect_rate_i * x_i                      (reward high-value tests)
             + sum_{i<j} 0.1 * overlap(i,j) * x_i * x_j         (penalize redundant coverage, once per pair)
             + penalty_weight * (sum_i exec_time_i * x_i / time_budget) ** 2   (soft budget penalty)

The budget term is built by adding penalty_weight*t_i*t_j/budget^2 to
EVERY (i, j) pair, including j<i and i==j -- this is not double-counting
by accident: x^T Q x sums Q[i][j] and Q[j][i] separately for every
unordered pair, so assigning the SAME value to both entries is exactly
how you encode the (sum_i t_i x_i)^2 expansion's cross term
(2 * t_i * t_j for i != j) as a QUBO. The redundancy term, by contrast,
is written to only the upper triangle (j > i) since it's meant to
contribute once per pair -- these are two different, both-correct
conventions living in the same matrix, not an inconsistency.

QUBO has no native way to express "total time MUST NOT exceed budget"
as a hard constraint -- only this kind of soft, squared penalty. That
means a solved QUBO result can still violate the budget outright, which
is exactly the kind of thing this module's trust layer (trust.py) and
pipeline (pipeline.py) must check for explicitly, never assume away.
"""
from __future__ import annotations

import numpy as np

from quantum_test_selection.classical_baseline import TestCase


def build_qubo(tests: list[TestCase], time_budget: float, penalty_weight: float = 2.0) -> dict:
    if time_budget <= 0:
        raise ValueError(f"time_budget must be positive to build a QUBO penalty term, got {time_budget}")

    n = len(tests)
    Q = np.zeros((n, n))

    for i in range(n):
        Q[i][i] -= tests[i]["defect_rate"]

    for i in range(n):
        for j in range(i + 1, n):
            overlap = len(tests[i]["coverage_tags"] & tests[j]["coverage_tags"])
            if overlap > 0:
                Q[i][j] += 0.1 * overlap

    for i in range(n):
        for j in range(n):
            Q[i][j] += penalty_weight * tests[i]["exec_time"] * tests[j]["exec_time"] / (time_budget ** 2)

    return {"Q_matrix": Q, "test_ids": [t["id"] for t in tests], "time_budget": time_budget}


def qubo_objective_value(qubo_data: dict, selection_mask: list[int]) -> float:
    """
    x^T Q x for a given 0/1 selection -- used both to unit-test that
    build_qubo() actually represents what its docstring claims (by
    manually computing the expected value for a small, hand-checked
    case) and, later, to confirm a solver's returned bitstring produces
    the objective value the solver itself reported.
    """
    x = np.array(selection_mask, dtype=float)
    return float(x @ qubo_data["Q_matrix"] @ x)


def selected_time(tests: list[TestCase], selection_mask: list[int]) -> float:
    """Actual total exec_time for a selection -- the ground truth the soft
    budget penalty can never guarantee on its own; always check this
    directly rather than trusting the QUBO's penalty term kept it in bounds."""
    return sum(t["exec_time"] for t, x in zip(tests, selection_mask) if x == 1)
