"""
Step 3: QAOA-based optimization over a QUBO (qubo.py), run against
Qiskit's local Aer simulator by default -- real IBM Quantum hardware is
a separate, explicit opt-in (solve_with_real_hardware below), never the
default path, per this module's own build order ("confirm the full
pipeline logic works correctly before introducing real quantum hardware
noise as a variable").

A real, non-obvious gap found while building this: QAOA's ansatz
circuit must be transpiled to the target backend's basis gates before
Aer's SamplerV2 can run it -- passing the sampler alone (as the original
design sketch did) fails with `AerError: unknown instruction: QAOA`,
because the sampler receives the untranspiled QAOAAnsatz circuit
literally, not its assembled gate sequence. Fixed by passing a
transpiler (a preset pass manager targeting the actual backend) into
QAOA's own `transpiler` parameter.
"""
from __future__ import annotations

from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager


def _build_quadratic_program(qubo_data: dict) -> QuadraticProgram:
    qp = QuadraticProgram()
    n = len(qubo_data["test_ids"])
    for i in range(n):
        qp.binary_var(f"x{i}")
    qp.minimize(quadratic=qubo_data["Q_matrix"])
    return qp


def _shot_distribution_from_samples(samples) -> dict[str, float]:
    """
    MinimumEigenOptimizer's result.samples gives one SolutionSample per
    distinct bitstring, each with a `probability` -- but these values do
    NOT sum to 1.0 (verified empirically; they reflect SamplingVQE's
    internal eigenstate weighting at the optimizer's final parameters,
    not a renormalized shot histogram). That's fine for this dict's only
    consumer (trust.py's shot_consistency = max/sum), which is
    scale-invariant, but don't treat this as a true probability
    distribution for any purpose that needs one.
    """
    return {"".join(str(int(bit)) for bit in sample.x): sample.probability for sample in samples}


def solve_with_simulator(qubo_data: dict, reps: int = 2, shots: int = 1024, maxiter: int = 50) -> dict:
    """The default, always-available quantum-assisted path -- Qiskit
    Aer's local simulator, no IBM account or network access needed."""
    qp = _build_quadratic_program(qubo_data)
    backend = AerSimulator()
    transpiler = generate_preset_pass_manager(optimization_level=1, backend=backend)
    sampler = SamplerV2(default_shots=shots)

    qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter), reps=reps, transpiler=transpiler)
    result = MinimumEigenOptimizer(qaoa).solve(qp)

    selected = [qubo_data["test_ids"][i] for i, val in enumerate(result.x) if val == 1]

    return {
        "selected_tests": selected,
        "objective_value": float(result.fval),
        "raw_shot_distribution": _shot_distribution_from_samples(result.samples),
        "backend_used": backend.name,
        "method": "quantum_assisted",
    }


def solve_with_real_hardware(qubo_data: dict, reps: int = 2, shots: int = 1024, maxiter: int = 50) -> dict:
    """
    Real IBM Quantum hardware -- explicit opt-in only, never the default.
    Needs a real IBM Quantum account/token already saved via
    QiskitRuntimeService.save_account() beforehand (see this module's
    README) -- imports qiskit_ibm_runtime lazily so the simulator path
    above never requires it or a network connection at all.
    """
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime import SamplerV2 as RuntimeSamplerV2

    qp = _build_quadratic_program(qubo_data)
    service = QiskitRuntimeService()
    backend = service.least_busy(operational=True, simulator=False)
    transpiler = generate_preset_pass_manager(optimization_level=1, backend=backend)
    sampler = RuntimeSamplerV2(mode=backend, options={"default_shots": shots})

    qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter), reps=reps, transpiler=transpiler)
    result = MinimumEigenOptimizer(qaoa).solve(qp)

    selected = [qubo_data["test_ids"][i] for i, val in enumerate(result.x) if val == 1]

    return {
        "selected_tests": selected,
        "objective_value": float(result.fval),
        "raw_shot_distribution": _shot_distribution_from_samples(result.samples),
        "backend_used": backend.name,
        "method": "quantum_assisted",
    }
