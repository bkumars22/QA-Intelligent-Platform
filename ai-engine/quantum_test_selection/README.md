# Quantum-Assisted Test Selection Optimization

Given N generated tests and a limited CI/CD time budget, pick the subset
to actually run that maximizes defect-detection coverage without
exceeding the budget — a real, NP-hard combinatorial optimization
problem. A classical baseline is always computed and is the correctness
benchmark; a quantum-assisted (QAOA) alternative is explored on top of
it, gated behind a mandatory trust evaluation that falls back to the
classical answer automatically whenever the quantum result isn't
trustworthy enough to use.

This is a genuinely new, isolated module — nothing outside
`quantum_test_selection/` and its own test files was touched to build
it.

## Files

| file | what it does |
|---|---|
| `classical_baseline.py` | Exact brute-force for ≤20 tests, a real greedy approximation above that. The correctness benchmark, not a fallback of last resort. |
| `qubo.py` | Formulates selection as QUBO (`x^T Q x`): reward defect detection, penalize redundant coverage, soft-penalize exceeding the budget. |
| `quantum_solver.py` | QAOA via Qiskit — `solve_with_simulator()` (default, local, no account needed) and `solve_with_real_hardware()` (explicit opt-in, needs a real IBM Quantum account). |
| `trust.py` | The actual point of this module: scores a quantum result on shot consistency, agreement with the classical baseline, and hardware calibration, and recommends falling back to classical below a 0.7 trust threshold. |
| `pipeline.py` | Ties it together — classical always runs; quantum + trust only kick in at 5+ tests; quantum only ever gets used above the trust threshold. |
| `reports.py` | Human-readable tradeoff report: what was selected, what was sacrificed, time saved, and — if applicable — why a quantum result got discarded. |

## Verified so far (everything except real hardware)

Built and tested in the order this module's own design brief specified:
classical baseline (hand-verified small cases) → QUBO (hand-verified
against the same cases, cross-checked two independent ways) → QAOA
against the **Aer simulator** (no IBM account needed) → trust layer
(including the explicit required test: a deliberately noisy shot
distribution correctly triggers a classical fallback) → pipeline
integration (a real, unmocked end-to-end run against the simulator, plus
mocked tests forcing both trust branches deterministically) → reports.
54 tests, all passing, no mocked LLM/network calls anywhere in this
module (QAOA runs are real local simulation, not stubbed).

**Real IBM Quantum hardware is NOT connected or verified.**
`solve_with_real_hardware()` exists and is wired into `pipeline.py`
behind `use_real_hardware=True` (default `False`), but has not been run
against actual hardware — that needs your own free IBM Quantum account
and a saved API token, which is out of scope for this session. See
"Connecting to real hardware" below when you're ready for that step.

## Real, non-obvious things found while building this

- **QAOA's ansatz circuit must be transpiled before Aer's `SamplerV2`
  can run it.** Passing the sampler alone (as this module's original
  design sketch did) fails with `AerError: unknown instruction: QAOA`
  — you must pass a `transpiler` (a preset pass manager targeting the
  actual backend) into `QAOA(...)`, or the untranspiled ansatz circuit
  gets sent to the simulator literally.
- **`MinimumEigenOptimizer`'s `result.samples` probabilities do not sum
  to 1.0.** They reflect `SamplingVQE`'s internal eigenstate weighting
  at the optimizer's final parameters, not a renormalized shot
  histogram. This turns out not to matter for `trust.py` (its
  `shot_consistency = max / sum` is scale-invariant regardless of the
  total), but don't treat this dict as a true probability distribution
  for anything else.
- **The QUBO's soft budget penalty can make the "optimal" quantum
  answer meaningfully more conservative than the classical hard-
  constraint optimum**, depending on `penalty_weight` — in one real run
  against a 3-test example, the classical baseline's true optimum used
  the full budget (score 0.9), while the QUBO's own minimum favored
  selecting a single, cheaper test instead. This isn't a bug in either
  implementation; it's an inherent property of encoding a hard
  constraint as a soft, squared penalty in QUBO form, and it's exactly
  why `trust.py`'s classical-agreement check — not an assumption that
  quantum and classical will naturally agree — is load-bearing here.
- Two functions referenced in this module's original design sketch were
  never actually defined there: `_greedy_selection` (the >20-test
  fallback path) and `_get_backend_calibration_score` (the hardware-
  calibration trust factor). Both are implemented for real here — see
  their docstrings for the reasoning, especially calibration scoring's
  honest limitation (a backend NAME string alone can't carry real
  live calibration data; a simulator gets a perfect score by
  construction, a named real backend gets a clearly-labeled
  conservative default).
- A real division-by-zero gap: `build_qubo()` divided by
  `time_budget ** 2` unconditionally in the original sketch. Guarded
  with a clear `ValueError` for `time_budget <= 0`.

## Connecting to real hardware (not yet done)

1. Create a free account at [quantum.ibm.com](https://quantum.ibm.com) and copy your API token.
2. **Do not paste the token into a chat session or commit it anywhere.** Set it as an environment variable and run, once, locally:
   ```python
   from qiskit_ibm_runtime import QiskitRuntimeService
   QiskitRuntimeService.save_account(token="...", overwrite=True)
   ```
   This saves it to your local Qiskit config, not this repo.
3. Install `qiskit-ibm-runtime` (not in `requirements.txt` — only needed for this opt-in path).
4. Call `select_tests_for_execution(tests, budget, use_real_hardware=True)`, or `quantum_solver.solve_with_real_hardware()` directly.
5. Compare the real-hardware result's `trust_evaluation` against a simulator run on the same input — expect a lower `hardware_calibration` component (it returns the same conservative `0.5` default documented above, since it's a bare name string) and expect real queue wait times, which the free tier does not exempt you from.
