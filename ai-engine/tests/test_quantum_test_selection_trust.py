"""
Step 4 verification -- including the one test this module's own
"Important Requirements" calls out by name: "construct a scenario with
deliberately noisy/inconsistent shot data, confirm the system correctly
falls back to classical rather than presenting an untrustworthy quantum
result." That's test_deliberately_noisy_shot_data_falls_back_to_classical
below, with every number hand-computed in its docstring.

Run with:  pytest tests/test_quantum_test_selection_trust.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch

import pytest

from quantum_test_selection.trust import evaluate_quantum_trust, _get_backend_calibration_score


class TestGetBackendCalibrationScore:
    def test_simulator_backend_gets_perfect_score(self):
        assert _get_backend_calibration_score("aer_simulator") == 1.0
        assert _get_backend_calibration_score("AerSimulator") == 1.0
        assert _get_backend_calibration_score("fake_manila") == 1.0

    def test_real_hardware_name_gets_conservative_default(self):
        assert _get_backend_calibration_score("ibm_brisbane") == 0.5


class TestEvaluateQuantumTrust:
    """
    Trustworthy case: quantum agrees fully with classical, shot
    distribution concentrated, on a simulator.
      shot_distribution = {"101": 0.6, "010": 0.3, "001": 0.1}  (sums to 1.0)
      shot_consistency = 0.6 / 1.0 = 0.6
      classical_agreement: quantum selected {A,C}, classical selected {A,C} -> overlap=2, agreement=2/2=1.0
      hardware_calibration = 1.0 (aer_simulator)
      overall_trust = (0.6 + 1.0 + 1.0) / 3 = 0.867 -> "use_quantum_result"
    """

    def test_trustworthy_result_recommends_using_quantum(self):
        quantum_result = {"selected_tests": ["A", "C"], "backend_used": "aer_simulator"}
        classical_baseline = {"selected_tests": ["A", "C"]}
        shot_distribution = {"101": 0.6, "010": 0.3, "001": 0.1}

        trust = evaluate_quantum_trust(quantum_result, classical_baseline, shot_distribution)

        assert trust["shot_consistency"] == 0.6
        assert trust["classical_agreement"] == 1.0
        assert trust["hardware_calibration"] == 1.0
        assert trust["overall_trust"] == 0.867
        assert trust["recommendation"] == "use_quantum_result"

    def test_deliberately_noisy_shot_data_falls_back_to_classical(self):
        """
        THE explicit required test. Deliberately noisy/inconsistent shot
        distribution (8 near-equal outcomes, no clear winner) AND zero
        agreement with the classical answer:
          shot_distribution: 8 bitstrings at ~0.05 each, summing to 0.4, max=0.06
          shot_consistency = 0.06 / 0.4 = 0.15
          classical_agreement: quantum picked {B}, classical picked {A,C} -> overlap=0, agreement=0/2=0.0
          hardware_calibration = 1.0 (aer_simulator)
          overall_trust = (0.15 + 0.0 + 1.0) / 3 = 0.383 -> below 0.7 -> "fall_back_to_classical"
        """
        quantum_result = {"selected_tests": ["B"], "backend_used": "aer_simulator"}
        classical_baseline = {"selected_tests": ["A", "C"]}
        noisy_shot_distribution = {
            "100": 0.05, "010": 0.06, "001": 0.04, "110": 0.05,
            "101": 0.05, "011": 0.05, "111": 0.05, "000": 0.05,
        }

        trust = evaluate_quantum_trust(quantum_result, classical_baseline, noisy_shot_distribution)

        assert trust["shot_consistency"] == 0.15
        assert trust["classical_agreement"] == 0.0
        assert trust["overall_trust"] == 0.383
        assert trust["recommendation"] == "fall_back_to_classical"

    def test_partial_agreement_computed_correctly(self):
        """Quantum selected {A, B}, classical selected {A, C} -> overlap=1, agreement=1/2=0.5."""
        quantum_result = {"selected_tests": ["A", "B"], "backend_used": "aer_simulator"}
        classical_baseline = {"selected_tests": ["A", "C"]}
        shot_distribution = {"110": 1.0}

        trust = evaluate_quantum_trust(quantum_result, classical_baseline, shot_distribution)
        assert trust["classical_agreement"] == 0.5

    def test_empty_classical_baseline_does_not_divide_by_zero(self):
        """max(len(classical_baseline['selected_tests']), 1) guards this --
        an empty classical selection (e.g. budget=0) must not crash trust
        evaluation with a ZeroDivisionError."""
        quantum_result = {"selected_tests": [], "backend_used": "aer_simulator"}
        classical_baseline = {"selected_tests": []}
        shot_distribution = {"00": 1.0}

        trust = evaluate_quantum_trust(quantum_result, classical_baseline, shot_distribution)
        assert trust["classical_agreement"] == 0.0  # 0 overlap / max(0,1) = 0, not a crash

    def test_real_hardware_backend_name_lowers_calibration_component(self):
        quantum_result = {"selected_tests": ["A", "C"], "backend_used": "ibm_brisbane"}
        classical_baseline = {"selected_tests": ["A", "C"]}
        shot_distribution = {"101": 1.0}

        trust = evaluate_quantum_trust(quantum_result, classical_baseline, shot_distribution)
        assert trust["hardware_calibration"] == 0.5
        # (1.0 + 1.0 + 0.5) / 3 = 0.833 -- still above threshold despite lower calibration
        assert trust["overall_trust"] == 0.833
        assert trust["recommendation"] == "use_quantum_result"

    def test_empty_shot_distribution_raises_rather_than_crashing_obscurely(self):
        with pytest.raises(ValueError, match="non-empty shot_distribution"):
            evaluate_quantum_trust({"selected_tests": [], "backend_used": "aer_simulator"}, {"selected_tests": []}, {})

    def test_trust_above_threshold_uses_quantum(self):
        """Mean of (1.0, 1.0, 0.4) = 0.8, comfortably above 0.7."""
        quantum_result = {"selected_tests": ["A"], "backend_used": "aer_simulator"}
        classical_baseline = {"selected_tests": ["A"]}
        shot_distribution = {"1": 1.0}

        with patch("quantum_test_selection.trust._get_backend_calibration_score", return_value=0.4):
            trust = evaluate_quantum_trust(quantum_result, classical_baseline, shot_distribution)

        assert trust["overall_trust"] == 0.8
        assert trust["recommendation"] == "use_quantum_result"

    def test_trust_below_threshold_falls_back(self):
        """Mean of (1.0, 1.0, 0.05) = 0.683..., comfortably below 0.7.
        (An earlier version of this test tried to hit exactly 0.7 via
        summed floating-point division -- (0.1+1.0+1.0)/3 evaluates to
        0.7000000000000001 in float64, not 0.7, which made a
        floating-point rounding artifact look like a product bug. This
        version tests the same `> 0.7` design intent with values held
        comfortably away from the boundary instead.)"""
        quantum_result = {"selected_tests": ["A"], "backend_used": "aer_simulator"}
        classical_baseline = {"selected_tests": ["A"]}
        shot_distribution = {"1": 1.0}

        with patch("quantum_test_selection.trust._get_backend_calibration_score", return_value=0.05):
            trust = evaluate_quantum_trust(quantum_result, classical_baseline, shot_distribution)

        assert trust["overall_trust"] < 0.7
        assert trust["recommendation"] == "fall_back_to_classical"
