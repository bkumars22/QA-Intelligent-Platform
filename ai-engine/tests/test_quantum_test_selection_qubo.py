"""
Step 2 verification (per this module's own build order: verify the QUBO
formulation against a few small, manually-checked scenarios BEFORE
running it through any solver). Every expected number below was computed
by hand (see the class docstring) and cross-checked two ways: directly
from the Q matrix's entries, and independently via the plain formula
-detection + redundancy_penalty + penalty_weight*(time/budget)^2 --
both must agree, since agreement between two independently-derived
calculations is what actually earns confidence here, not just "the code
ran and returned a number."

Run with:  pytest tests/test_quantum_test_selection_qubo.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from quantum_test_selection.qubo import build_qubo, qubo_objective_value, selected_time


def _t(id_, defect_rate, exec_time, tags):
    return {"id": id_, "defect_rate": defect_rate, "exec_time": exec_time, "coverage_tags": set(tags)}


class TestBuildQuboHandVerified:
    """
    A={defect_rate=0.5, exec_time=2, tags={login}}
    B={defect_rate=0.3, exec_time=2, tags={login}}
    C={defect_rate=0.4, exec_time=3, tags={checkout}}
    time_budget=5, penalty_weight=2.0 (default)

    By hand: Q[0][0]=-0.18, Q[1][1]=0.02, Q[2][2]=0.32
             Q[0][1]=0.42, Q[1][0]=0.32, Q[0][2]=0.48, Q[2][0]=0.48, Q[1][2]=0.48, Q[2][1]=0.48
    (derivation: diagonal = -defect_rate + penalty_weight*exec_time^2/budget^2;
     off-diagonal = [0.1*tag_overlap if j>i else 0] + penalty_weight*exec_time_i*exec_time_j/budget^2)
    """

    def _tests(self):
        return [_t("A", 0.5, 2, {"login"}), _t("B", 0.3, 2, {"login"}), _t("C", 0.4, 3, {"checkout"})]

    def test_diagonal_entries_match_hand_calculation(self):
        qubo = build_qubo(self._tests(), time_budget=5)
        Q = qubo["Q_matrix"]
        assert round(Q[0][0], 5) == -0.18
        assert round(Q[1][1], 5) == 0.02
        assert round(Q[2][2], 5) == 0.32

    def test_off_diagonal_entries_match_hand_calculation(self):
        qubo = build_qubo(self._tests(), time_budget=5)
        Q = qubo["Q_matrix"]
        assert round(Q[0][1], 5) == 0.42
        assert round(Q[1][0], 5) == 0.32  # asymmetric on purpose -- redundancy term is upper-triangle only
        assert round(Q[0][2], 5) == 0.48
        assert round(Q[2][0], 5) == 0.48
        assert round(Q[1][2], 5) == 0.48
        assert round(Q[2][1], 5) == 0.48

    def test_objective_value_for_AC_matches_formula_independently(self):
        """x=[1,0,1] (A and C selected). Formula:
        -(0.5+0.4) + 0 [no tag overlap] + 2.0*(5/5)**2 = -0.9 + 0 + 2.0 = 1.1"""
        qubo = build_qubo(self._tests(), time_budget=5)
        assert round(qubo_objective_value(qubo, [1, 0, 1]), 5) == 1.10

    def test_objective_value_for_AB_matches_formula_independently(self):
        """x=[1,1,0] (A and B selected, sharing the 'login' tag). Formula:
        -(0.5+0.3) + 0.1*1 [one shared tag] + 2.0*(4/5)**2 = -0.8 + 0.1 + 1.28 = 0.58"""
        qubo = build_qubo(self._tests(), time_budget=5)
        assert round(qubo_objective_value(qubo, [1, 1, 0]), 5) == 0.58

    def test_objective_value_for_empty_selection_is_zero(self):
        qubo = build_qubo(self._tests(), time_budget=5)
        assert qubo_objective_value(qubo, [0, 0, 0]) == 0.0

    def test_test_ids_preserve_input_order(self):
        qubo = build_qubo(self._tests(), time_budget=5)
        assert qubo["test_ids"] == ["A", "B", "C"]


class TestBuildQuboEdgeCases:
    def test_zero_budget_raises_rather_than_dividing_by_zero(self):
        """The original design sketch divided by time_budget**2 unconditionally
        -- a budget of 0 would ZeroDivisionError deep inside numpy instead of
        failing with a clear, actionable message. Guarded explicitly here."""
        with pytest.raises(ValueError, match="time_budget must be positive"):
            build_qubo([_t("A", 0.5, 1, set())], time_budget=0)

    def test_negative_budget_raises(self):
        with pytest.raises(ValueError, match="time_budget must be positive"):
            build_qubo([_t("A", 0.5, 1, set())], time_budget=-5)

    def test_single_test_has_no_off_diagonal_terms(self):
        qubo = build_qubo([_t("A", 0.5, 2, {"login"})], time_budget=5)
        assert qubo["Q_matrix"].shape == (1, 1)

    def test_empty_test_list_produces_empty_matrix(self):
        qubo = build_qubo([], time_budget=5)
        assert qubo["Q_matrix"].shape == (0, 0)
        assert qubo["test_ids"] == []


class TestSelectedTime:
    def test_sums_only_selected_tests(self):
        tests = [_t("A", 0.5, 2, set()), _t("B", 0.3, 3, set()), _t("C", 0.4, 5, set())]
        assert selected_time(tests, [1, 0, 1]) == 7

    def test_all_zero_selection_is_zero_time(self):
        tests = [_t("A", 0.5, 2, set())]
        assert selected_time(tests, [0]) == 0

    def test_matches_the_budget_the_qubo_penalty_targeted(self):
        """A concrete demonstration of this module's own documented gap:
        the QUBO's soft penalty does NOT guarantee the budget is respected
        -- a selection can score well on the QUBO objective while still
        exceeding the actual time_budget, which is exactly why
        selected_time() must be checked directly downstream, never assumed."""
        tests = [_t("A", 0.9, 4, set()), _t("B", 0.9, 4, set())]
        qubo = build_qubo(tests, time_budget=5, penalty_weight=0.01)  # deliberately weak penalty
        both_selected_time = selected_time(tests, [1, 1])
        assert both_selected_time == 8  # exceeds the budget of 5
        # A weak penalty_weight makes the QUBO objective still favor selecting
        # both despite the violation -- proving the penalty alone can't be trusted.
        assert qubo_objective_value(qubo, [1, 1]) < qubo_objective_value(qubo, [1, 0])
