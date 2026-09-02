"""
Step 4: the trust layer -- non-negotiable, not an add-on. The single
most important rule in this whole module: a quantum-derived selection
is never presented without this evaluation attached, and a low-trust
result is discarded in favor of the classical baseline automatically,
never left for a human to notice on their own (see pipeline.py).

`_get_backend_calibration_score` was referenced but never actually
defined in this module's original design sketch (same kind of gap as
classical_baseline.py's `_greedy_selection`). Implemented here as
honestly as the available information allows: a local Aer simulator is
noiseless by construction, so it gets a perfect calibration score; a
named real IBM backend gets a conservative default, since scoring real
hardware calibration for real needs live backend properties (T1/T2,
gate error rates) from an actual connected service object, which this
function -- given only a backend NAME string, per the original design's
own signature -- cannot query. That's an honest, documented limitation,
not a hidden assumption.
"""
from __future__ import annotations


def _get_backend_calibration_score(backend_name: str) -> float:
    lowered = backend_name.lower()
    if "aer" in lowered or "simulator" in lowered or "fake" in lowered:
        return 1.0  # noiseless by construction
    # A real named IBM backend: without a live service connection and
    # backend.properties() call, there is no real calibration data to
    # read here -- return a deliberately conservative, clearly-labeled
    # default rather than pretending to know the hardware is trustworthy.
    return 0.5


def evaluate_quantum_trust(quantum_result: dict, classical_baseline: dict, shot_distribution: dict) -> dict:
    if not shot_distribution:
        raise ValueError("evaluate_quantum_trust requires a non-empty shot_distribution")

    # Factor 1: shot consistency -- how concentrated is the result
    # distribution on its top answer? Computed as a ratio (max/sum), so
    # it's valid even though these values don't sum to 1.0 (see
    # quantum_solver.py's _shot_distribution_from_samples docstring).
    total = sum(shot_distribution.values())
    shot_consistency_score = (max(shot_distribution.values()) / total) if total > 0 else 0.0

    # Factor 2: classical agreement -- does the quantum answer roughly
    # match the known-correct classical answer?
    overlap = len(set(quantum_result["selected_tests"]) & set(classical_baseline["selected_tests"]))
    agreement_score = overlap / max(len(classical_baseline["selected_tests"]), 1)

    # Factor 3: hardware calibration context.
    calibration_score = _get_backend_calibration_score(quantum_result["backend_used"])

    overall_trust = (shot_consistency_score + agreement_score + calibration_score) / 3

    return {
        "shot_consistency": round(shot_consistency_score, 3),
        "classical_agreement": round(agreement_score, 3),
        "hardware_calibration": round(calibration_score, 3),
        "overall_trust": round(overall_trust, 3),
        "recommendation": "use_quantum_result" if overall_trust > 0.7 else "fall_back_to_classical",
    }
