import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { FolderKanban, PlayCircle, Bug, TrendingUp } from 'lucide-react';
import { getDashboardStats, getProjects, getTestRuns, getDefects, getRiskHeatmap } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { SeverityBadge } from '../components/SeverityBadge';
import type { DashboardStats, RiskScore, TestRun, Defect, DefectSeverity } from '../types';
import RiskExplainPanel from '../components/RiskExplainPanel';
import type { RiskScoreEntry } from '../components/RiskExplainPanel';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  colorClass: string;
  bgClass: string;
}

function StatCard({ title, value, icon, colorClass, bgClass }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-4">
      <div className={`flex items-center justify-center w-12 h-12 rounded-xl ${bgClass}`}>
        <span className={colorClass}>{icon}</span>
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500 mt-0.5">{title}</p>
      </div>
    </div>
  );
}

function RiskBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score > 0.7 ? 'bg-red-500' : score > 0.4 ? 'bg-yellow-400' : 'bg-green-500';
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-600 w-8 text-right">{pct}%</span>
    </div>
  );
}

const SEVERITY_COLORS: Record<DefectSeverity, string> = {
  P0: '#dc2626',
  P1: '#f97316',
  P2: '#eab308',
  P3: '#3b82f6',
};

export function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    refetchInterval: 30_000,
  });

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });

  // Fetch test runs for the first project to show on dashboard
  const firstProjectId = projects[0]?.id ?? null;

  const { data: testRuns = [] } = useQuery<TestRun[]>({
    queryKey: ['test-runs', firstProjectId],
    queryFn: () => getTestRuns(firstProjectId!),
    enabled: firstProjectId !== null,
  });

  const firstRunId = testRuns[0]?.id ?? null;

  const { data: defects = [] } = useQuery<Defect[]>({
    queryKey: ['defects', firstRunId],
    queryFn: () => getDefects(firstRunId!),
    enabled: firstRunId !== null,
  });

  const { data: riskScores = [] } = useQuery<RiskScore[]>({
    queryKey: ['risk-heatmap', firstProjectId],
    queryFn: () => getRiskHeatmap(firstProjectId!),
    enabled: firstProjectId !== null,
  });

  // Build severity distribution for pie chart
  const severityCounts = defects.reduce<Record<DefectSeverity, number>>(
    (acc, d) => { acc[d.severity] = (acc[d.severity] ?? 0) + 1; return acc; },
    { P0: 0, P1: 0, P2: 0, P3: 0 }
  );
  const pieData = (Object.keys(severityCounts) as DefectSeverity[])
    .filter((k) => severityCounts[k] > 0)
    .map((k) => ({ name: k, value: severityCounts[k], color: SEVERITY_COLORS[k] }));

  const sortedRisk = [...riskScores].sort((a, b) => b.riskScore - a.riskScore).slice(0, 10);
  const recentRuns = testRuns.slice(0, 5);

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Overview of your QA intelligence platform</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="Total Projects"
          value={stats?.totalProjects ?? '—'}
          icon={<FolderKanban size={22} />}
          colorClass="text-brand-600"
          bgClass="bg-brand-50"
        />
        <StatCard
          title="Active Test Runs"
          value={stats?.activeTestRuns ?? '—'}
          icon={<PlayCircle size={22} />}
          colorClass="text-orange-600"
          bgClass="bg-orange-50"
        />
        <StatCard
          title="Open Defects"
          value={stats?.openDefects ?? '—'}
          icon={<Bug size={22} />}
          colorClass="text-red-600"
          bgClass="bg-red-50"
        />
        <StatCard
          title="Avg Risk Score"
          value={stats ? `${Math.round(stats.avgRiskScore * 100)}%` : '—'}
          icon={<TrendingUp size={22} />}
          colorClass="text-green-600"
          bgClass="bg-green-50"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Risk Heatmap + SHAP Explanations */}
        <div className="bg-slate-900 rounded-xl border border-slate-700 p-6">
          <h2 className="text-base font-semibold text-white mb-1">Risk Heatmap</h2>
          <p className="text-xs text-slate-500 mb-4">Click a file to see SHAP feature attribution</p>
          <RiskExplainPanel
            riskScores={sortedRisk.map((rs): RiskScoreEntry => ({
              file_path:    rs.filePath,
              score:        rs.riskScore,
              anomaly_flag: rs.anomalyFlag,
              features:     {},
            }))}
            maxShow={8}
          />
        </div>

        {/* Defect severity donut */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Defect Severity Distribution</h2>
          {pieData.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-sm text-gray-400">
              No defect data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend
                  formatter={(value) => (
                    <span className="text-xs text-gray-600">{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Recent Test Runs */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">Recent Test Runs</h2>
        </div>
        {recentRuns.length === 0 ? (
          <div className="px-6 py-8 text-sm text-gray-400">No test runs found</div>
        ) : (
          <div className="divide-y divide-gray-50">
            <div className="grid grid-cols-5 px-6 py-2 text-xs font-medium text-gray-500 uppercase tracking-wide">
              <span>Run ID</span>
              <span>Triggered By</span>
              <span>Status</span>
              <span>Started</span>
              <span>Defects</span>
            </div>
            {recentRuns.map((run) => (
              <div key={run.id} className="grid grid-cols-5 px-6 py-3 items-center text-sm">
                <span className="font-mono text-gray-700">#{run.id}</span>
                <span className="text-gray-600 truncate">{run.triggeredBy}</span>
                <StatusBadge status={run.status} />
                <span className="text-gray-500 text-xs">
                  {new Date(run.startedAt).toLocaleString()}
                </span>
                <span className="inline-flex items-center gap-1">
                  {run.defectCount > 0 && (
                    <SeverityBadge severity="P1" />
                  )}
                  <span className="text-gray-700 font-medium">{run.defectCount}</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
