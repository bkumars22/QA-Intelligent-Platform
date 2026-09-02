"""
Step 6 verification -- hand-checked report content for both the
"quantum result used" and "fell back to classical" cases.

Run with:  pytest tests/test_quantum_test_selection_reports.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantum_test_selection.reports import generate_selection_report


def _t(id_, defect_rate, exec_time):
    return {"id": id_, "defect_rate": defect_rate, "exec_time": exec_time, "coverage_tags": set()}


class TestGenerateSelectionReport:
    def _all_tests(self):
        return [_t("A", 0.5, 2), _t("B", 0.3, 2), _t("C", 0.4, 3)]

    def test_classical_result_without_trust_evaluation(self):
        result = {"selected_tests": ["A", "C"], "score": 0.9, "method": "classical"}
        report = generate_selection_report(result, self._all_tests())

        assert "Method: classical" in report
        assert "Trust Score: N/A" in report
        assert "Selected: 2 of 3 tests" in report
        assert "Coverage retained: 0.90" in report  # 0.5 + 0.4
        assert "Coverage sacrificed: 0.30" in report  # just B
        assert "Time saved: 2.0 minutes" in report  # just B's exec_time
        assert "⚠" not in report

    def test_quantum_result_used_shows_trust_score_and_no_warning(self):
        result = {
            "selected_tests": ["A", "C"],
            "method": "quantum_assisted",
            "trust_evaluation": {"overall_trust": 0.867},
        }
        report = generate_selection_report(result, self._all_tests())

        assert "Method: quantum_assisted" in report
        assert "Trust Score: 0.867" in report
        assert "⚠" not in report

    def test_fallback_result_shows_the_pipelines_own_note_verbatim(self):
        """The warning line must reuse pipeline.py's exact note text, not
        a separately-hardcoded string that could drift out of sync with it."""
        result = {
            "selected_tests": ["A", "B"],
            "method": "classical",
            "trust_evaluation": {"overall_trust": 0.383},
            "note": "Quantum result available but did not meet trust threshold",
        }
        report = generate_selection_report(result, self._all_tests())

        assert "⚠ Quantum result available but did not meet trust threshold" in report

    def test_empty_selection_reports_zero_coverage_retained(self):
        result = {"selected_tests": [], "method": "classical"}
        report = generate_selection_report(result, self._all_tests())

        assert "Selected: 0 of 3 tests" in report
        assert "Coverage retained: 0.00" in report
        assert "Coverage sacrificed: 1.20" in report  # 0.5+0.3+0.4
        assert "Time saved: 7.0 minutes" in report  # 2+2+3

    def test_all_selected_reports_zero_time_saved(self):
        result = {"selected_tests": ["A", "B", "C"], "method": "classical"}
        report = generate_selection_report(result, self._all_tests())

        assert "Coverage sacrificed: 0.00" in report
        assert "Time saved: 0.0 minutes" in report
