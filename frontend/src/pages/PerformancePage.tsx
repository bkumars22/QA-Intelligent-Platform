import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { AlertTriangle, CheckCircle2, ExternalLink, Loader2, Play } from 'lucide-react';
import {
  runPerformanceTest, getPerformanceRunStatus, getPerformanceResults,
  isDemoMode, type PerformanceResult,
} from '../services/api';

// Sample data illustrating the shape of real Locust output (see
// performance-testing/metrics_analyzer.py's PerfMetrics) — shown only
// until a system has real results in performance_test_results.
interface PerfResult {
  endpoint: string;
  p50: number;
  p95: number;
  p99: number;
  rps: number;
  errorRate: number;
}

const SAMPLE_RESULTS: Record<string, PerfResult[]> = {
  QAIP: [
    { endpoint: '/api/projects/[id]/risk-scores', p50: 42, p95: 78, p99: 105, rps: 62.4, errorRate: 0.12 },
    { endpoint: '/api/dashboard/stats', p50: 108, p95: 215, p99: 310, rps: 41.2, errorRate: 0.05 },
    { endpoint: '/api/automation/projects/[id]/executions', p50: 84, p95: 168, p99: 240, rps: 33.8, errorRate: 0.31 },
    { endpoint: '/api/projects/[id]/run-analysis', p50: 31, p95: 68, p99: 95, rps: 71.6, errorRate: 0.08 },
  ],
  ARIA: [
    { endpoint: '/api/sessions/[id]/chat', p50: 620, p95: 980, p99: 1400, rps: 12.3, errorRate: 0.10 },
    { endpoint: '/api/progress/student/[id]', p50: 45, p95: 92, p99: 130, rps: 38.6, errorRate: 0.02 },
    { endpoint: '/api/homework/solve', p50: 2100, p95: 3400, p99: 4200, rps: 3.1, errorRate: 0.28 },
  ],
};

const DEFAULT_HOSTS: Record<string, string> = {
  QAIP: 'https://testmind-production.up.railway.app',
  ARIA: '',
};

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

function resultsToPerfResult(results: PerformanceResult[]): PerfResult[] {
  return results.map((r) => ({
    endpoint: r.endpoint,
    p50: r.p50Ms,
    p95: r.p95Ms,
    p99: r.p99Ms,
    rps: r.requestsPerSec,
    errorRate: r.errorRatePct,
  }));
}

export function PerformancePage() {
  const [tab, setTab] = useState<'Overview' | 'Load Tests' | 'Thresholds'>('Overview');
  const [system, setSystem] = useState<'QAIP' | 'ARIA'>('QAIP');
  const [host, setHost] = useState(DEFAULT_HOSTS.QAIP);
  const [dispatchedAt, setDispatchedAt] = useState<string | null>(null);
  const demoMode = isDemoMode();
  const queryClient = useQueryClient();

  useEffect(() => {
    setHost(DEFAULT_HOSTS[system]);
  }, [system]);

  const { data: liveResults = [] } = useQuery<PerformanceResult[]>({
    queryKey: ['performance-results', system],
    queryFn: () => getPerformanceResults(system),
  });

  const runMutation = useMutation({
    mutationFn: () => runPerformanceTest({ system, host }),
    onSuccess: (res) => {
      if (res.dispatched && res.dispatchedAt) {
        setDispatchedAt(res.dispatchedAt);
      }
    },
  });

  const { data: runStatus } = useQuery({
    queryKey: ['performance-run-status', dispatchedAt],
    queryFn: () => getPerformanceRunStatus(dispatchedAt as string),
    enabled: dispatchedAt !== null,
    refetchInterval: (query) => (query.state.data?.status === 'completed' ? false : 5000),
  });

  useEffect(() => {
    if (runStatus?.status === 'completed') {
      void queryClient.invalidateQueries({ queryKey: ['performance-results', system] });
    }
  }, [runStatus?.status, system, queryClient]);

  const isRunning = dispatchedAt !== null && runStatus?.status !== 'completed';
  const results: PerfResult[] = liveResults.length > 0
    ? resultsToPerfResult(liveResults)
    : SAMPLE_RESULTS[system];
  const usingSampleData = liveResults.length === 0;

  const avgP95 = results.length
    ? Math.round(results.reduce((a, r) => a + r.p95, 0) / results.length)
    : 0;
  const maxError = results.length
    ? Math.max(...results.map((r) => r.errorRate)).toFixed(2)
    : '0.00';

  const trend = liveResults.length > 0
    ? [...liveResults]
        .sort((a, b) => a.testedAt.localeCompare(b.testedAt))
        .map((r) => ({ date: r.testedAt.slice(0, 10), p95: r.p95Ms }))
    : [
        { date: '2026-07-01', p95: 46 },
        { date: '2026-07-08', p95: 58 },
        { date: '2026-07-16', p95: 68 },
      ];

  const tabs: Array<'Overview' | 'Load Tests' | 'Thresholds'> = ['Overview', 'Load Tests', 'Thresholds'];

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Performance</h1>
          <p className="text-sm text-gray-500 mt-1">
            Load-test QAIP and ARIA's backend APIs via the Performance Gate workflow.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {(['QAIP', 'ARIA'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSystem(s)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold border transition-colors ${
                system === s
                  ? 'bg-white border-blue-200 text-blue-600 shadow-sm'
                  : 'border-transparent text-gray-500 hover:bg-white hover:border-gray-200'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex items-end gap-3 flex-wrap">
        <div className="flex-1 min-w-[240px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">Target host</label>
          <input
            type="text"
            value={host}
            onChange={(e) => setHost(e.target.value)}
            placeholder="https://..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
        </div>
        <button
          onClick={() => {
            setDispatchedAt(null);
            runMutation.mutate();
          }}
          disabled={demoMode || !host || isRunning || runMutation.isPending}
          title={demoMode ? 'Running load tests is disabled in demo mode' : undefined}
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold px-4 py-2.5 rounded-lg transition-colors"
        >
          {isRunning || runMutation.isPending ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {isRunning || runMutation.isPending ? 'Running…' : 'Run load test'}
        </button>
      </div>

      {demoMode && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          <span className="font-semibold">Demo mode:</span>
          <span>Running load tests is disabled to protect the showcase environment.</span>
        </div>
      )}

      {runMutation.data && !runMutation.data.dispatched && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-800">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{runMutation.data.message}</span>
        </div>
      )}

      {runStatus?.status === 'completed' && (
        <div
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm border ${
            runStatus.conclusion === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {runStatus.conclusion === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          <span>Run finished: {runStatus.conclusion}.</span>
          {runStatus.runUrl && (
            <a href={runStatus.runUrl} target="_blank" rel="noopener noreferrer" className="underline">
              View on GitHub
            </a>
          )}
        </div>
      )}

      {usingSampleData && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          <span className="font-semibold">Sample data:</span>
          <span>
            No load test has been run for {system} yet — these numbers illustrate the shape of real
            output. Click "Run load test" above, or trigger the workflow directly on GitHub.
          </span>
        </div>
      )}

      <div className="flex gap-4 flex-wrap">
        <StatCard icon={CheckCircle2} iconColor="text-emerald-500" value={results.length} label="Endpoints Tracked" />
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
            <div className="text-gray-900 font-semibold mb-4">
              P95 Latency Trend{usingSampleData ? ' (sample)' : ''}
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trend}>
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
            <div className="text-gray-900 font-semibold mb-4">
              P95 Latency by Endpoint{usingSampleData ? ' (sample)' : ''}
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={results} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#64748B', fontSize: 12 }} axisLine={{ stroke: '#CBD5E1' }} tickLine={false} />
                <YAxis type="category" dataKey="endpoint" width={220} tick={{ fill: '#334155', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#fff', border: '1px solid #E2E8F0', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: number) => [`${v}ms`, 'P95']}
                />
                <Bar dataKey="p95" radius={[0, 6, 6, 0]}>
                  {results.map((r, i) => (
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
              {results.map((r) => (
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

      {!demoMode && (
        <div className="flex items-center gap-4">
          <a
            href={GITHUB_ACTIONS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-brand-600 text-sm font-medium hover:underline"
          >
            <ExternalLink size={13} />
            Open the Performance Gate workflow
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
      )}
    </div>
  );
}
