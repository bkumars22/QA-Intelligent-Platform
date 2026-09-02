"""
Step 5 verification: the classical baseline must run on EVERY call
(Important Requirement #2), quantum is skipped entirely below
_MIN_TESTS_FOR_QUANTUM, and the trust-gated branch (use quantum vs. fall
back to classical) is verified deterministically via mocking -- QAOA is
stochastic, so forcing both branches reliably needs controlled trust
scores, not hoping a real run lands on each side. One real, unmocked
end-to-end run (against the Aer simulator, still no real hardware) is
also included so the actual wiring between all 4 modules is proven, not
just each mocked boundary.

Run with:  pytest tests/test_quantum_test_selection_pipeline.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch

from quantum_test_selection.classical_baseline import classical_test_selection
from quantum_test_selection.pipeline import select_tests_for_execution


def _t(id_, defect_rate, exec_time, tags):
    return {"id": id_, "defect_rate": defect_rate, "exec_time": exec_time, "coverage_tags": set(tags)}


def _small_suite(n):
    return [_t(f"T{i}", 0.5 + i * 0.01, 1.0, {f"tag{i}"}) for i in range(n)]


class TestSkipsQuantumBelowThreshold:
    def test_fewer_than_five_tests_returns_pure_classical_no_trust_evaluation(self):
        tests = _small_suite(4)
        result = select_tests_for_execution(tests, time_budget=10)
        assert result["method"] == "classical"
        assert "trust_evaluation" not in result
        assert "note" not in result

    def test_matches_calling_classical_directly(self):
        tests = _small_suite(3)
        direct = classical_test_selection(tests, time_budget=5)
        via_pipeline = select_tests_for_execution(tests, time_budget=5)
        assert via_pipeline == direct


class TestClassicalAlwaysRunsRegardlessOfQuantumOutcome:
    """Important Requirement #2: the classical baseline must run for
    EVERY request, not just as a fallback -- verified here by confirming
    it's called even on the path that ultimately uses the quantum
    result (not just the path that falls back to it)."""

    def test_classical_baseline_is_computed_even_when_quantum_result_is_used(self):
        tests = _small_suite(6)
        fake_quantum_result = {
            "selected_tests": ["T0", "T1"],
            "raw_shot_distribution": {"11": 1.0},
            "backend_used": "aer_simulator",
            "method": "quantum_assisted",
        }
        with patch("quantum_test_selection.pipeline.classical_test_selection") as mock_classical, \
             patch("quantum_test_selection.pipeline.solve_with_simulator", return_value=fake_quantum_result):
            mock_classical.return_value = {"selected_tests": ["T0", "T1"], "score": 1.0, "method": "classical"}
            select_tests_for_execution(tests, time_budget=10)
            mock_classical.assert_called_once()


class TestTrustGatedBranching:
    def test_high_trust_returns_quantum_result_with_trust_evaluation(self):
        tests = _small_suite(6)
        fake_quantum_result = {
            "selected_tests": ["T0", "T1"],
            "raw_shot_distribution": {"110000": 1.0},
            "backend_used": "aer_simulator",
            "method": "quantum_assisted",
        }
        # classical baseline will be computed for real; force it to agree
        # fully with the fake quantum result so trust evaluates high.
        with patch("quantum_test_selection.pipeline.solve_with_simulator", return_value=fake_quantum_result), \
             patch("quantum_test_selection.pipeline.classical_test_selection",
                   return_value={"selected_tests": ["T0", "T1"], "score": 1.0, "method": "classical"}):
            result = select_tests_for_execution(tests, time_budget=10)

        assert result["method"] == "quantum_assisted"
        assert "trust_evaluation" in result
        assert result["trust_evaluation"]["recommendation"] == "use_quantum_result"
        assert "note" not in result

    def test_low_trust_falls_back_to_classical_with_note_and_trust_attached(self):
        tests = _small_suite(6)
        fake_quantum_result = {
            "selected_tests": ["T5"],  # disagrees entirely with classical below
            "raw_shot_distribution": {f"{i:06b}": 0.01 for i in range(50)},  # deliberately noisy/flat
            "backend_used": "aer_simulator",
            "method": "quantum_assisted",
        }
        with patch("quantum_test_selection.pipeline.solve_with_simulator", return_value=fake_quantum_result), \
             patch("quantum_test_selection.pipeline.classical_test_selection",
                   return_value={"selected_tests": ["T0", "T1"], "score": 1.0, "method": "classical"}):
            result = select_tests_for_execution(tests, time_budget=10)

        assert result["method"] == "classical"
        assert result["note"] == "Quantum result available but did not meet trust threshold"
        assert "trust_evaluation" in result
        assert result["trust_evaluation"]["recommendation"] == "fall_back_to_classical"

    def test_never_presents_a_quantum_result_without_trust_attached(self):
        """Important Requirement #1, checked directly: whichever branch
        wins, trust_evaluation must be present once n >= the quantum
        threshold -- there is no code path that returns a
        quantum-influenced answer silently."""
        tests = _small_suite(6)
        for backend_fake in (
            {"selected_tests": ["T0"], "raw_shot_distribution": {"1": 1.0}, "backend_used": "aer_simulator", "method": "quantum_assisted"},
        ):
            with patch("quantum_test_selection.pipeline.solve_with_simulator", return_value=backend_fake):
                result = select_tests_for_execution(tests, time_budget=10)
            assert "trust_evaluation" in result


class TestRealEndToEndOnSimulator:
    """No mocking -- proves the actual wiring between classical_baseline,
    qubo, quantum_solver (Aer simulator), and trust all work together for
    real. Still no real IBM hardware involved anywhere."""

    def test_full_pipeline_runs_without_error_and_returns_a_well_formed_result(self):
        tests = _small_suite(6)
        result = select_tests_for_execution(tests, time_budget=4.0)

        assert result["method"] in ("classical", "quantum_assisted")
        assert "trust_evaluation" in result
        assert isinstance(result["selected_tests"], list)
        assert set(result["selected_tests"]).issubset({t["id"] for t in tests})
        if result["method"] == "classical":
            assert result["note"] == "Quantum result available but did not meet trust threshold"
