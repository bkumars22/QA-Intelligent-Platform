"""
Step 1: the classical baseline for test selection under a time budget.

This is not a fallback of last resort -- it is the correctness benchmark
every quantum-derived result gets checked against (see trust.py), and it
runs on EVERY request, not just when quantum is unavailable (see
pipeline.py). Selecting the subset of tests that maximizes total defect
detection while penalizing redundant coverage, without exceeding a time
budget, is exactly a budgeted maximum-coverage problem -- NP-hard in
general, but small instances (<=20 tests) are solved exactly here by
brute force, and larger ones by a real greedy approximation.
"""
from __future__ import annotations

from itertools import combinations
from typing import TypedDict


class TestCase(TypedDict):
    id: str
    defect_rate: float
    exec_time: float
    coverage_tags: set[str]


def score_selection(subset: tuple[TestCase, ...] | list[TestCase]) -> float:
    """
    Sum of defect_rate across the subset, minus a redundancy penalty for
    overlapping coverage_tags. The running-set trick below (track tags
    already claimed by an earlier test in the subset, penalize each
    re-occurrence) sums to the same total regardless of iteration order:
    a tag shared by m tests in the subset contributes exactly (m-1) to
    the penalty, however you order the subset -- it isn't an
    approximation of a pairwise count, it's an exact one.
    """
    detection_score = sum(t["defect_rate"] for t in subset)
    seen_tags: set[str] = set()
    redundancy_penalty = 0
    for t in subset:
        redundancy_penalty += len(t["coverage_tags"] & seen_tags)
        seen_tags |= t["coverage_tags"]
    return detection_score - (0.1 * redundancy_penalty)


def _brute_force_selection(tests: list[TestCase], time_budget: float) -> tuple[list[TestCase], float]:
    best_selection: tuple[TestCase, ...] = ()
    best_score = 0.0
    for r in range(1, len(tests) + 1):
        for subset in combinations(tests, r):
            if sum(t["exec_time"] for t in subset) > time_budget:
                continue
            score = score_selection(subset)
            if score > best_score:
                best_score, best_selection = score, subset
    return list(best_selection), best_score


def _greedy_selection(tests: list[TestCase], time_budget: float) -> tuple[list[TestCase], float]:
    """
    Real greedy approximation for suites too large to brute-force
    (>20 tests) -- referenced but never actually implemented in this
    module's original design sketch. Standard greedy for budgeted
    maximum coverage: repeatedly add whichever remaining test gives the
    best MARGINAL score-per-time-unit given what's already selected
    (not a fixed value/weight ratio computed once up front, since
    redundancy penalty makes a test's marginal value depend on what's
    already in the selection), stopping when nothing remaining fits the
    remaining budget or improves the score.
    """
    selected: list[TestCase] = []
    remaining = list(tests)
    used_time = 0.0
    current_score = 0.0

    while remaining:
        best_candidate = None
        best_marginal_density = 0.0
        best_candidate_score = current_score

        for candidate in remaining:
            if used_time + candidate["exec_time"] > time_budget:
                continue
            candidate_score = score_selection(selected + [candidate])
            marginal_gain = candidate_score - current_score
            if marginal_gain <= 0:
                continue
            density = marginal_gain / candidate["exec_time"]
            if density > best_marginal_density:
                best_marginal_density = density
                best_candidate = candidate
                best_candidate_score = candidate_score

        if best_candidate is None:
            break

        selected.append(best_candidate)
        remaining.remove(best_candidate)
        used_time += best_candidate["exec_time"]
        current_score = best_candidate_score

    return selected, current_score


def classical_test_selection(tests: list[TestCase], time_budget: float) -> dict:
    """
    Brute-force for small suites (<=20 tests, exact answer), a real
    greedy approximation above that. This result is both the classical
    answer AND the ground truth the quantum path's trust evaluation
    checks itself against (trust.py) -- it must run every time, not be
    treated as a rarely-used fallback path.
    """
    if len(tests) <= 20:
        selection, score = _brute_force_selection(tests, time_budget)
    else:
        selection, score = _greedy_selection(tests, time_budget)

    return {"selected_tests": [t["id"] for t in selection], "score": score, "method": "classical"}
