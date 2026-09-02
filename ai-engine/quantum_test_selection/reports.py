"""
Step 6: show the tradeoff, not just the answer -- what got selected,
what got left out, and, if the quantum path was tried, whether it was
actually trusted enough to use.

The warning line reuses `result["note"]` verbatim (set by pipeline.py)
rather than hardcoding a second, similarly-worded string here -- the
original design sketch had the report's warning text drift slightly
from the pipeline's own note ("trust threshold not met" vs. "did not
meet trust threshold"), which is exactly the kind of duplication that
goes stale the next time either string gets edited alone.
"""
from __future__ import annotations

from quantum_test_selection.classical_baseline import TestCase


def generate_selection_report(result: dict, all_tests: list[TestCase]) -> str:
    selected = set(result["selected_tests"])
    excluded = [t for t in all_tests if t["id"] not in selected]

    trust_score = result.get("trust_evaluation", {}).get("overall_trust", "N/A")
    warning_line = f"\n⚠ {result['note']}" if result.get("note") else ""

    return (
        f"Test Selection Report\n"
        f"Method: {result['method']}\n"
        f"Trust Score: {trust_score}\n"
        f"\n"
        f"Selected: {len(selected)} of {len(all_tests)} tests\n"
        f"Coverage retained: {sum(t['defect_rate'] for t in all_tests if t['id'] in selected):.2f}\n"
        f"Coverage sacrificed: {sum(t['defect_rate'] for t in excluded):.2f}\n"
        f"Time saved: {sum(t['exec_time'] for t in excluded):.1f} minutes"
        f"{warning_line}\n"
    )
