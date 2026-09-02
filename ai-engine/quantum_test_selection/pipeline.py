"""
Step 5: the integration point tying classical_baseline.py, qubo.py,
quantum_solver.py, and trust.py together into one entry point.

The classical baseline runs on EVERY call, not as a rarely-used
fallback -- it's also the correctness check the quantum path is
measured against (Important Requirement #2). Real IBM Quantum hardware
is opt-in (`use_real_hardware=True`) and OFF by default: this module's
own build order puts "connect to real hardware" strictly last, after
everything else is verified against the simulator, so making the
simulator the default here (not real hardware, as the module's original
design sketch assumed once an IBM account existed) keeps that ordering
true even after this integration point exists.
"""
from __future__ import annotations

from quantum_test_selection.classical_baseline import TestCase, classical_test_selection
from quantum_test_selection.qubo import build_qubo
from quantum_test_selection.quantum_solver import solve_with_simulator
from quantum_test_selection.trust import evaluate_quantum_trust

# Below this many tests, the classical brute-force is exact, instant,
# and cheaper than building a QUBO + running QAOA at all.
_MIN_TESTS_FOR_QUANTUM = 5


def select_tests_for_execution(
    generated_tests: list[TestCase],
    time_budget: float,
    use_real_hardware: bool = False,
) -> dict:
    classical_result = classical_test_selection(generated_tests, time_budget)

    if len(generated_tests) < _MIN_TESTS_FOR_QUANTUM:
        return classical_result

    qubo = build_qubo(generated_tests, time_budget)

    if use_real_hardware:
        from quantum_test_selection.quantum_solver import solve_with_real_hardware
        quantum_result = solve_with_real_hardware(qubo)
    else:
        quantum_result = solve_with_simulator(qubo)

    trust = evaluate_quantum_trust(quantum_result, classical_result, quantum_result["raw_shot_distribution"])

    if trust["recommendation"] == "use_quantum_result":
        return {**quantum_result, "trust_evaluation": trust}

    return {
        **classical_result,
        "trust_evaluation": trust,
        "note": "Quantum result available but did not meet trust threshold",
    }
