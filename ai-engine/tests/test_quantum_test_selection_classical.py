"""
Step 1 verification (per this module's own build order: verify the
classical baseline alone first, against small hand-checkable examples,
before anything quantum touches it).

Run with:  pytest tests/test_quantum_test_selection_classical.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantum_test_selection.classical_baseline import classical_test_selection, score_selection


def _t(id_, defect_rate, exec_time, tags):
    return {"id": id_, "defect_rate": defect_rate, "exec_time": exec_time, "coverage_tags": set(tags)}


class TestScoreSelection:
    def test_no_overlap_no_penalty(self):
        subset = [_t("A", 0.5, 2, {"login"}), _t("B", 0.4, 3, {"checkout"})]
        assert score_selection(subset) == 0.9

    def test_full_overlap_penalized_once(self):
        subset = [_t("A", 0.5, 2, {"login"}), _t("B", 0.3, 2, {"login"})]
        # detection 0.8, one shared tag between the two -> penalty 0.1*1
        assert round(score_selection(subset), 5) == 0.7

    def test_penalty_order_independent(self):
        """The running-set trick must total the same regardless of
        subset ordering -- this is an exact identity, not a heuristic."""
        a, b, c = _t("A", 0.5, 1, {"x", "y"}), _t("B", 0.3, 1, {"y", "z"}), _t("C", 0.2, 1, {"x", "z"})
        assert score_selection([a, b, c]) == score_selection([c, b, a]) == score_selection([b, a, c])

    def test_empty_subset_scores_zero(self):
        assert score_selection([]) == 0.0


class TestClassicalTestSelectionBruteForce:
    """Hand-verified: A={0.5,2,{login}}, B={0.3,2,{login}}, C={0.4,3,{checkout}},
    budget=5. Every subset's score computed by hand in this test's docstring-equivalent
    comment below; {A,C} at score 0.9 is the unique best choice that fits the budget.

    {A}: time=2, score=0.5      {B}: time=2, score=0.3      {C}: time=3, score=0.4
    {A,B}: time=4, score=0.7    {A,C}: time=5, score=0.9    {B,C}: time=5, score=0.7
    {A,B,C}: time=7 > 5, excluded entirely.
    """

    def _tests(self):
        return [_t("A", 0.5, 2, {"login"}), _t("B", 0.3, 2, {"login"}), _t("C", 0.4, 3, {"checkout"})]

    def test_picks_the_hand_verified_optimal_subset(self):
        result = classical_test_selection(self._tests(), time_budget=5)
        assert set(result["selected_tests"]) == {"A", "C"}
        assert round(result["score"], 5) == 0.9
        assert result["method"] == "classical"

    def test_tiny_budget_forces_single_cheapest_test(self):
        result = classical_test_selection(self._tests(), time_budget=2)
        # Only A or B fit alone (time=2 each); A has the higher defect_rate.
        assert result["selected_tests"] == ["A"]
        assert result["score"] == 0.5

    def test_budget_of_zero_selects_nothing(self):
        result = classical_test_selection(self._tests(), time_budget=0)
        assert result["selected_tests"] == []
        assert result["score"] == 0.0

    def test_empty_test_list(self):
        result = classical_test_selection([], time_budget=10)
        assert result["selected_tests"] == []
        assert result["score"] == 0.0

    def test_generous_budget_still_excludes_pure_redundancy(self):
        """Two tests with IDENTICAL coverage and the same defect_rate:
        selecting both nets a redundancy penalty with zero detection
        upside over selecting the single cheaper one twice -- but since
        each test can only be selected once, both being selected must
        still beat selecting just one (0.5+0.5-0.1=0.9 > 0.5), so both
        SHOULD be selected here; this exercises the penalty math against
        a case worth checking by hand rather than assuming."""
        tests = [_t("A", 0.5, 1, {"x"}), _t("B", 0.5, 1, {"x"})]
        result = classical_test_selection(tests, time_budget=2)
        assert set(result["selected_tests"]) == {"A", "B"}
        assert round(result["score"], 5) == 0.9


class TestClassicalTestSelectionGreedyFallback:
    """>20 tests routes to the greedy path -- _greedy_selection didn't
    exist at all in this module's original design sketch (referenced,
    never defined); these tests are its actual verification."""

    def _large_suite(self, n=25):
        # Every test has a unique tag (no redundancy interactions) so the
        # optimal answer is knowable: greedily fill the budget with the
        # highest defect_rate-per-exec_time tests.
        return [_t(f"T{i}", defect_rate=1.0 + i * 0.01, exec_time=1.0, tags={f"tag{i}"}) for i in range(n)]

    def test_never_exceeds_the_time_budget(self):
        tests = self._large_suite(25)
        result = classical_test_selection(tests, time_budget=10)
        selected_ids = set(result["selected_tests"])
        total_time = sum(t["exec_time"] for t in tests if t["id"] in selected_ids)
        assert total_time <= 10

    def test_picks_the_highest_value_tests_when_untagged_conflicts(self):
        """With disjoint tags (no redundancy penalty) and equal
        exec_time, greedy-by-marginal-density degenerates to
        greedy-by-defect_rate -- so the top-10 highest defect_rate tests
        (T15..T24) is the exactly correct answer here, not just 'close'."""
        tests = self._large_suite(25)
        result = classical_test_selection(tests, time_budget=10)
        expected = {f"T{i}" for i in range(15, 25)}
        assert set(result["selected_tests"]) == expected

    def test_zero_budget_on_a_large_suite_selects_nothing(self):
        result = classical_test_selection(self._large_suite(25), time_budget=0)
        assert result["selected_tests"] == []

    def test_uses_greedy_method_label(self):
        result = classical_test_selection(self._large_suite(21), time_budget=5)
        assert result["method"] == "classical"  # method label is the same; routing is internal
