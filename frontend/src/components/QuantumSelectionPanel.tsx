import { useState } from 'react';
import { Atom, Loader2, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

const AI_ENGINE = import.meta.env.VITE_AI_ENGINE_URL ?? 'http://localhost:8001';

// Example tests, hand-picked to illustrate the tradeoff: two share a
// coverage tag (redundancy penalty applies), one is expensive relative
// to a tight budget.
const EXAMPLE_TESTS = [
  { id: 'login_valid_credentials', defect_rate: 0.9, exec_time: 2, coverage_tags: ['login'] },
  { id: 'login_invalid_password', defect_rate: 0.6, exec_time: 1, coverage_tags: ['login'] },
  { id: 'checkout_apply_promo', defect_rate: 0.8, exec_time: 3, coverage_tags: ['checkout'] },
  { id: 'checkout_out_of_stock', defect_rate: 0.7, exec_time: 4, coverage_tags: ['checkout'] },
  { id: 'reports_export_csv', defect_rate: 0.5, exec_time: 2, coverage_tags: ['reports'] },
  { id: 'reports_filter_by_date', defect_rate: 0.4, exec_time: 1, coverage_tags: ['reports'] },
];

interface QuantumTestCase {
  id: string;
  defect_rate: number;
  exec_time: number;
  coverage_tags: string[];
}

interface TrustEvaluation {
  shot_consistency: number;
  classical_agreement: number;
  hardware_calibration: number;
  overall_trust: number;
  recommendation: 'use_quantum_result' | 'fall_back_to_classical';
}

interface SelectionResult {
  selected_tests: string[];
  method: 'classical' | 'quantum_assisted';
  trust_evaluation?: TrustEvaluation;
  note?: string;
  report: string;
}

export function QuantumSelectionPanel() {
  const [testsJson, setTestsJson] = useState(JSON.stringify(EXAMPLE_TESTS, null, 2));
  const [timeBudget, setTimeBudget] = useState('6');
  const [result, setResult] = useState<SelectionResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const runSelection = async () => {
    setError('');
    setResult(null);

    let tests: QuantumTestCase[];
    try {
      tests = JSON.parse(testsJson);
    } catch (e) {
      setError(`Invalid JSON: ${(e as Error).message}`);
      return;
    }

    const budget = parseFloat(timeBudget);
    if (!Number.isFinite(budget) || budget <= 0) {
      setError('Time budget must be a positive number.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${AI_ENGINE}/quantum/select-tests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tests, time_budget: budget }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `Request failed (${res.status})`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(
        `${(e as Error).message} — is the ai-engine service running at ${AI_ENGINE}? ` +
        `This feature calls it directly and has no demo-mode mock (see quantum_test_selection/README.md).`
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="text-base font-semibold text-gray-900 mb-1 flex items-center gap-2">
        <Atom size={16} /> Quantum-Assisted Test Selection
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        Given a set of tests and a CI time budget, picks the subset maximizing defect-detection
        coverage. Runs on a local quantum simulator (no IBM Quantum account needed) with a classical
        baseline always computed alongside it as the correctness check — a low-trust quantum result
        automatically falls back to the classical answer. Real IBM Quantum hardware is wired in but
        intentionally not connected here; that's the next real step, not implied by this demo.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div className="md:col-span-2">
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Tests (id, defect_rate 0-1, exec_time minutes, coverage_tags)
          </label>
          <textarea
            value={testsJson}
            onChange={e => setTestsJson(e.target.value)}
            rows={10}
            className="w-full px-3 py-2 text-xs font-mono border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none"
            spellCheck={false}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Time budget (minutes)</label>
          <input
            type="number"
            min="0"
            step="0.5"
            value={timeBudget}
            onChange={e => setTimeBudget(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none mb-3"
          />
          <button
            onClick={() => void runSelection()}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-60"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Atom size={14} />}
            {loading ? 'Selecting…' : 'Select Tests'}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-1.5 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-3">
          <XCircle size={12} className="shrink-0 mt-0.5" /> {error}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm">
            {result.method === 'quantum_assisted' ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                <Atom size={11} /> Quantum-assisted result used
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                Classical result used
              </span>
            )}
            {result.note && (
              <span className="inline-flex items-center gap-1 text-xs text-amber-700">
                <AlertCircle size={12} /> {result.note}
              </span>
            )}
          </div>

          {result.trust_evaluation && (
            <div className="grid grid-cols-4 gap-2 text-xs">
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-2">
                <p className="text-gray-500">Shot consistency</p>
                <p className="font-semibold text-gray-900">{result.trust_evaluation.shot_consistency}</p>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-2">
                <p className="text-gray-500">Classical agreement</p>
                <p className="font-semibold text-gray-900">{result.trust_evaluation.classical_agreement}</p>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-2">
                <p className="text-gray-500">HW calibration</p>
                <p className="font-semibold text-gray-900">{result.trust_evaluation.hardware_calibration}</p>
              </div>
              <div className={`border rounded-lg p-2 ${
                result.trust_evaluation.recommendation === 'use_quantum_result'
                  ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'
              }`}>
                <p className="text-gray-500">Overall trust</p>
                <p className="font-semibold text-gray-900 flex items-center gap-1">
                  {result.trust_evaluation.recommendation === 'use_quantum_result'
                    ? <CheckCircle2 size={12} className="text-green-600" />
                    : <AlertCircle size={12} className="text-amber-600" />}
                  {result.trust_evaluation.overall_trust}
                </p>
              </div>
            </div>
          )}

          <pre className="text-xs bg-[#1e1e2e] text-[#cdd6f4] p-4 rounded-lg overflow-x-auto whitespace-pre-wrap">
            {result.report}
          </pre>
        </div>
      )}
    </div>
  );
}
