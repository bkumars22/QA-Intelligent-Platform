import { useState, useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { AlertTriangle, CheckCircle2, ExternalLink } from 'lucide-react';

// Sample data illustrating the shape of real Locust output (see
// performance-testing/metrics_analyzer.py's PerfMetrics). There is no
// backend endpoint yet that serves live performance-test results into
// the UI (performance_test_results table has no reader endpoint) — this
// tab shows fixtures, not live numbers, until that's built.
interface PerfResult {
  endpoint: string;
  p50: number;
  p95: number;
  p99: number;
  rps: number;
  errorRate: number;
}

const SAMPLE_RESULTS: PerfResult[] = [
  { endpoint: '/api/projects/[id]/risk-scores', p50: 42, p95: 78, p99: 105, rps: 62.4, errorRate: 0.12 },
  { endpoint: '/api/dashboard/stats', p50: 108, p95: 215, p99: 310, rps: 41.2, errorRate: 0.05 },
  { endpoint: '/api/automation/projects/[id]/executions', p50: 84, p95: 168, p99: 240, rps: 33.8, errorRate: 0.31 },
  { endpoint: '/api/projects/[id]/run-analysis', p50: 31, p95: 68, p99: 95, rps: 71.6, errorRate: 0.08 },
];

const SAMPLE_TREND = [
  { date: '2026-07-01', p95: 46 },
  { date: '2026-07-08', p95: 58 },
  { date: '2026-07-16', p95: 68 },
];

// Real thresholds from performance-testing/metrics_analyzer.py — these
// are not sample data, they're the actual gate the CI job enforces.
const THRESHOLDS = { p95IncreasePct: 20, errorRateMaxPct: 1.0, throughputDecreasePct: 15 };

const ACCENT = '#2563EB';

const GITHUB_ACTIONS_URL =
  'https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/performance.yml';
const DOCS_URL =
  'https://github.com/bkumars22/QA-Intelligent-Platform/blob/main/performance-testing/README.md';

function StatCard({
  icon: Icon, iconColor, value, label,
}: { icon: typeof CheckCircle2; iconColor: string; value: string | number; label: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-5 py-4 flex items-center gap-3 flex-1 min-w-[150px] shadow-sm">
      <Icon size={18} className={iconColor} />
      <div>
        <div className="text-2xl font-bold text-gray-900 leading-tight">{value}</div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    </div>
  );
}

export function PerformancePage() {
  const [tab, setTab] = useState<'Overview' | 'Load Tests' | 'Thresholds'>('Overview');

  const avgP95 = useMemo(
    () => Math.round(SAMPLE_RESULTS.reduce((a, r) => a + r.p95, 0) / SAMPLE_RESULTS.length),
    []
  );
  const maxError = useMemo(
    () => Math.max(...SAMPLE_RESULTS.map((r) => r.errorRate)).toFixed(2),
    []
  );

  const tabs: Array<'Overview' | 'Load Tests' | 'Thresholds'> = ['Overview', 'Load Tests', 'Thresholds'];

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Performance</h1>
        <p className="text-sm text-gray-500 mt-1">
          Load-test results and regression thresholds for QAIP's backend API.
        </p>
      </div>

      <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
        <span className="font-semibold">Sample data:</span>
        <span>
          These numbers illustrate the shape of real Locust output — there's no live backend
          feeding this tab yet. Run <code className="bg-amber-100 px-1 rounded">performance-testing/locustfile.py</code>{' '}
          locally, or trigger the Performance Gate workflow below, to generate real results.
        </span>
      </div>

      <div className="flex gap-4 flex-wrap">
        <StatCard icon={CheckCircle2} iconColor="text-emerald-500" value={SAMPLE_RESULTS.length} label="Endpoints Tracked" />
        <StatCard icon={AlertTriangle} iconColor="text-amber-500" value={`${maxError}%`} label="Max Error Rate" />
        <StatCard icon={CheckCircle2} iconColor="text-emerald-500" value={`${avgP95}ms`} label="Avg P95" />
      </div>

      <div className="flex items-center gap-6 border-b border-gray-200">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
              tab === t ? 'border-brand-600 text-brand-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Overview' && (
        <>
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <div className="text-gray-900 font-semibold mb-4">P95 Latency Trend (sample)</div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={SAMPLE_TREND}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" tick={{ fill: '#64748B', fontSize: 12 }} axisLine={{ stroke: '#CBD5E1' }} tickLine={false} />
                <YAxis tick={{ fill: '#64748B', fontSize: 12 }} axisLine={{ stroke: '#CBD5E1' }} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`${v}ms`, 'P95']}
                />
                <Line type="monotone" dataKey="p95" stroke={ACCENT} strokeWidth={2.5} dot={{ r: 4, fill: ACCENT }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <div className="text-gray-900 font-semibold mb-4">P95 Latency by Endpoint (sample)</div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={SAMPLE_RESULTS} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#64748B', fontSize: 12 }} axisLine={{ stroke: '#CBD5E1' }} tickLine={false} />
                <YAxis type="category" dataKey="endpoint" width={220} tick={{ fill: '#334155', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`${v}ms`, 'P95']}
                />
                <Bar dataKey="p95" radius={[0, 6, 6, 0]}>
                  {SAMPLE_RESULTS.map((r, i) => (
                    <Cell key={i} fill={r.p95 > 200 ? '#E11D48' : ACCENT} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {tab === 'Load Tests' && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase tracking-wide bg-gray-50">
                <th className="text-left px-5 py-3 font-semibold">Endpoint</th>
                <th className="text-left px-5 py-3 font-semibold">P50</th>
                <th className="text-left px-5 py-3 font-semibold">P95</th>
                <th className="text-left px-5 py-3 font-semibold">P99</th>
                <th className="text-left px-5 py-3 font-semibold">Req/s</th>
                <th className="text-left px-5 py-3 font-semibold">Error %</th>
              </tr>
            </thead>
            <tbody>
              {SAMPLE_RESULTS.map((r) => (
                <tr key={r.endpoint} className="border-t border-gray-100">
                  <td className="px-5 py-3 font-mono text-xs text-gray-700">{r.endpoint}</td>
                  <td className="px-5 py-3 text-gray-500">{r.p50}ms</td>
                  <td className="px-5 py-3 text-gray-900 font-semibold">{r.p95}ms</td>
                  <td className="px-5 py-3 text-gray-500">{r.p99}ms</td>
                  <td className="px-5 py-3 text-gray-500">{r.rps}</td>
                  <td className={`px-5 py-3 font-semibold ${r.errorRate > 1 ? 'text-rose-600' : 'text-emerald-600'}`}>
                    {r.errorRate}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'Thresholds' && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <div className="text-gray-900 font-semibold mb-4">Gate thresholds</div>
          <p className="text-xs text-gray-500 mb-4">
            Enforced by <code className="bg-gray-100 px-1 rounded">performance-testing/metrics_analyzer.py</code> —
            these are the real values, not samples.
          </p>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <span className="text-gray-600">Max P95 latency increase</span>
              <span className="font-semibold text-gray-900">{THRESHOLDS.p95IncreasePct}%</span>
            </div>
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <span className="text-gray-600">Max error rate</span>
              <span className="font-semibold text-gray-900">{THRESHOLDS.errorRateMaxPct}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Max throughput decrease</span>
              <span className="font-semibold text-gray-900">{THRESHOLDS.throughputDecreasePct}%</span>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-4">
        <a
          href={GITHUB_ACTIONS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-brand-600 text-sm font-medium hover:underline"
        >
          <ExternalLink size={13} />
          Run the Performance Gate workflow
        </a>
        <a
          href={DOCS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-brand-600 text-sm font-medium hover:underline"
        >
          <ExternalLink size={13} />
          View performance testing docs
        </a>
      </div>
    </div>
  );
}
