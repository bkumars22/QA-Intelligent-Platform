"""
Step 3 verification: QAOA against the Qiskit Aer SIMULATOR, never real
hardware, per this module's own build order. QAOA+COBYLA is a heuristic,
stochastic optimizer -- these tests don't assert "the globally optimal
bitstring every time" the way the hand-verified classical/QUBO tests
could, but they DO verify the pipeline is actually solving the intended
problem: the solver's own reported objective_value must match an
independent x^T Q x computation for the SAME returned selection (catches
any bug in how a solver bitstring gets mapped back to test IDs), and a
trivially-easy 1-variable problem must converge to its one obviously
correct answer.

Run with:  pytest tests/test_quantum_test_selection_solver.py -v
(Real network/quantum calls: none -- everything here is local simulation.)
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantum_test_selection.qubo import build_qubo, qubo_objective_value
from quantum_test_selection.quantum_solver import solve_with_simulator


def _t(id_, defect_rate, exec_time, tags):
    return {"id": id_, "defect_rate": defect_rate, "exec_time": exec_time, "coverage_tags": set(tags)}


class TestSolveWithSimulator:
    def test_trivial_single_test_converges_to_the_only_sensible_answer(self):
        """One test, clearly worth selecting (high defect_rate, tiny
        exec_time relative to a generous budget) -- x=1 must minimize
        the QUBO; there is no other bitstring to confuse this with."""
        tests = [_t("A", 0.9, 1, set())]
        qubo = build_qubo(tests, time_budget=10)
        result = solve_with_simulator(qubo, reps=1, shots=512, maxiter=30)
        assert result["selected_tests"] == ["A"]

    def test_objective_value_matches_independent_computation(self):
        """The solver's own reported objective_value for whatever it
        selected must equal x^T Q x computed independently for that same
        selection -- this is the real check: it would catch a bug where
        result.x's bit order didn't line up with test_ids, for example."""
        tests = [_t("A", 0.5, 2, {"login"}), _t("B", 0.3, 2, {"login"}), _t("C", 0.4, 3, {"checkout"})]
        qubo = build_qubo(tests, time_budget=5)
        result = solve_with_simulator(qubo, reps=2, shots=1024, maxiter=60)

        mask = [1 if tid in result["selected_tests"] else 0 for tid in qubo["test_ids"]]
        independently_computed = qubo_objective_value(qubo, mask)
        assert round(result["objective_value"], 5) == round(independently_computed, 5)

    def test_selected_tests_are_a_subset_of_input_ids(self):
        tests = [_t("A", 0.5, 2, {"login"}), _t("B", 0.3, 2, {"login"}), _t("C", 0.4, 3, {"checkout"})]
        qubo = build_qubo(tests, time_budget=5)
        result = solve_with_simulator(qubo, reps=1, shots=512, maxiter=30)
        assert set(result["selected_tests"]).issubset({"A", "B", "C"})

    def test_shot_distribution_has_nonzero_mass_and_valid_values(self):
        """NOTE, discovered empirically: MinimumEigenOptimizer's
        result.samples probabilities do NOT sum to 1.0 -- they reflect
        SamplingVQE's internal eigenstate weighting at the optimizer's
        final parameters, not a simple renormalized shot histogram. That
        turns out not to matter for the trust layer (trust.py computes
        max(dist)/sum(dist), a ratio that's scale-invariant regardless of
        the total), but a test asserting sum==1.0 would be asserting
        something that was never true and isn't required to be."""
        tests = [_t("A", 0.5, 2, {"login"}), _t("B", 0.3, 2, {"login"})]
        qubo = build_qubo(tests, time_budget=5)
        result = solve_with_simulator(qubo, reps=1, shots=512, maxiter=30)

        dist = result["raw_shot_distribution"]
        assert len(dist) > 0
        assert all(p >= 0.0 for p in dist.values())
        assert sum(dist.values()) > 0

    def test_backend_used_reports_the_local_simulator_not_real_hardware(self):
        tests = [_t("A", 0.9, 1, set())]
        qubo = build_qubo(tests, time_budget=10)
        result = solve_with_simulator(qubo, reps=1, shots=256, maxiter=20)
        assert "aer" in result["backend_used"].lower() or "simulator" in result["backend_used"].lower()

    def test_method_label_is_quantum_assisted(self):
        tests = [_t("A", 0.9, 1, set())]
        qubo = build_qubo(tests, time_budget=10)
        result = solve_with_simulator(qubo, reps=1, shots=256, maxiter=20)
        assert result["method"] == "quantum_assisted"
