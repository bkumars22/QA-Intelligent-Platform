import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ArrowLeft } from 'lucide-react';
import {
  getProjects,
  getTestRuns,
  getDefects,
  getRiskScores,
  getMcpStatus,
} from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { SeverityBadge } from '../components/SeverityBadge';
import { AutomationTab } from '../components/AutomationTab';
import { McpConfigPanel } from '../components/McpConfigPanel';
import type {
  TestRun,
  Defect,
  RiskScore,
  McpStatus,
  DefectSeverity,
  DefectStatus,
} from '../types';

type Tab = 'overview' | 'test-runs' | 'defects' | 'coverage-gaps' | 'mcp-status' | 'automation';

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'test-runs', label: 'Test Runs' },
  { id: 'defects', label: 'Defects' },
  { id: 'coverage-gaps', label: 'Coverage Gaps' },
  { id: 'automation', label: '⚡ Automation' },
  { id: 'mcp-status', label: 'MCP Status' },
];

function durationStr(run: TestRun): string {
  if (!run.completedAt) return '—';
  const ms = new Date(run.completedAt).getTime() - new Date(run.startedAt).getTime();
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [severityFilter, setSeverityFilter] = useState<DefectSeverity | 'ALL'>('ALL');
  const [statusFilter, setStatusFilter] = useState<DefectStatus | 'ALL'>('ALL');
  const [generatedForFile, setGeneratedForFile] = useState<string | null>(null);
  const { data: projects = [] } = useQuery({ queryKey: ['projects'], queryFn: getProjects });
  const project = projects.find((p) => p.id === projectId);

  const { data: testRuns = [] } = useQuery<TestRun[]>({
    queryKey: ['test-runs', projectId],
    queryFn: () => getTestRuns(projectId),
    enabled: !!projectId,
    refetchInterval: 15_000,
  });

  const firstRunId = testRuns[0]?.id ?? null;

  const { data: defects = [] } = useQuery<Defect[]>({
    queryKey: ['defects', firstRunId],
    queryFn: () => getDefects(firstRunId!),
    enabled: firstRunId !== null,
  });

  const { data: riskScores = [] } = useQuery<RiskScore[]>({
    queryKey: ['risk-scores', projectId],
    queryFn: () => getRiskScores(projectId),
    enabled: !!projectId,
  });

  const { data: mcpStatuses = [] } = useQuery<McpStatus[]>({
    queryKey: ['mcp-status', projectId],
    queryFn: () => getMcpStatus(projectId),
    enabled: !!projectId,
    refetchInterval: 60_000,
  });

  // Build risk trend from test runs
  const riskTrendData = testRuns
    .filter((r) => r.riskScore !== undefined)
    .slice()
    .reverse()
    .map((r) => ({
      date: new Date(r.startedAt).toLocaleDateString(),
      risk: Math.round((r.riskScore ?? 0) * 100),
    }));

  const filteredDefects = defects.filter((d) => {
    const bySeverity = severityFilter === 'ALL' || d.severity === severityFilter;
    const byStatus = statusFilter === 'ALL' || d.status === statusFilter;
    return bySeverity && byStatus;
  });

  const sortedRisk = [...riskScores].sort((a, b) => b.riskScore - a.riskScore);

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to="/projects"
          className="text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Back to projects"
        >
          <ArrowLeft size={20} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{project?.name ?? `Project #${projectId}`}</h1>
          {project?.repoUrl && (
            <a
              href={project.repoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              {project.repoUrl}
            </a>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-1" aria-label="Project tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-brand-600 text-brand-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab: Overview */}
      {activeTab === 'overview' && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Risk Score Trend</h2>
          {riskTrendData.length === 0 ? (
            <div className="flex items-center justify-center h-40 text-sm text-gray-400">
              No risk trend data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={riskTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
                <Tooltip formatter={(v) => [`${String(v)}%`, 'Risk Score']} />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={{ fill: '#2563eb', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      )}

      {/* Tab: Test Runs */}
      {activeTab === 'test-runs' && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-base font-semibold text-gray-900">Test Runs</h2>
          </div>
          {testRuns.length === 0 ? (
            <div className="px-6 py-8 text-sm text-gray-400">No test runs yet</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs font-medium text-gray-500 uppercase tracking-wide bg-gray-50">
                  <th className="px-6 py-3 text-left">Run ID</th>
                  <th className="px-6 py-3 text-left">Status</th>
                  <th className="px-6 py-3 text-left">Started</th>
                  <th className="px-6 py-3 text-left">Duration</th>
                  <th className="px-6 py-3 text-left">Defects</th>
                  <th className="px-6 py-3 text-left" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {testRuns.map((run) => (
                  <tr key={run.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-3 font-mono text-gray-700">#{run.id}</td>
                    <td className="px-6 py-3">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-6 py-3 text-gray-500">
                      {new Date(run.startedAt).toLocaleString()}
                    </td>
                    <td className="px-6 py-3 text-gray-500">{durationStr(run)}</td>
                    <td className="px-6 py-3 font-medium text-gray-700">{run.defectCount}</td>
                    <td className="px-6 py-3">
                      <Link
                        to={`/test-runs/${run.id}`}
                        className="text-brand-600 hover:text-brand-700 text-xs font-medium"
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Tab: Defects */}
      {activeTab === 'defects' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as DefectSeverity | 'ALL')}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none"
            >
              <option value="ALL">All Severities</option>
              <option value="P0">P0 Critical</option>
              <option value="P1">P1 High</option>
              <option value="P2">P2 Medium</option>
              <option value="P3">P3 Low</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as DefectStatus | 'ALL')}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
              <option value="WONT_FIX">Won't Fix</option>
            </select>
            <span className="text-sm text-gray-500">
              {filteredDefects.length} defect{filteredDefects.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="bg-white rounded-xl border border-gray-200">
            {filteredDefects.length === 0 ? (
              <div className="px-6 py-8 text-sm text-gray-400">No defects match the filters</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {filteredDefects.map((defect) => (
                  <Link
                    key={defect.id}
                    to={`/defects/${defect.id}`}
                    className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 transition-colors"
                  >
                    <SeverityBadge severity={defect.severity} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{defect.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{defect.description}</p>
                    </div>
                    <StatusBadge status={defect.status} />
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Coverage Gaps */}
      {activeTab === 'coverage-gaps' && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-base font-semibold text-gray-900">Coverage Gaps — Files by Risk Score</h2>
          </div>
          {sortedRisk.length === 0 ? (
            <div className="px-6 py-8 text-sm text-gray-400">No risk data available</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {sortedRisk.map((rs) => {
                const pct = Math.round(rs.riskScore * 100);
                const barColor = rs.riskScore > 0.7 ? 'bg-red-500' : rs.riskScore > 0.4 ? 'bg-yellow-400' : 'bg-green-500';
                return (
                  <div key={rs.id} className="px-6 py-4 flex items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-mono text-gray-700 truncate">{rs.filePath}</p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                          <div className={`${barColor} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-xs text-gray-500 w-8 text-right">{pct}%</span>
                      </div>
                    </div>
                    {rs.anomalyFlag && (
                      <span className="shrink-0 text-xs font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded">
                        ANOMALY
                      </span>
                    )}
                    <button
                      onClick={() => {
                        setGeneratedForFile(rs.filePath);
                        setActiveTab('automation');
                      }}
                      className="shrink-0 px-3 py-1.5 text-xs font-medium text-brand-600 border border-brand-200 hover:bg-brand-50 rounded-lg transition-colors"
                    >
                      Generate Tests
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab: Automation */}
      {activeTab === 'automation' && (
        <AutomationTab projectId={projectId} projectRepoUrl={project?.repoUrl} suggestedFile={generatedForFile} />
      )}

      {/* Tab: MCP Status */}
      {activeTab === 'mcp-status' && (
        <McpConfigPanel statuses={mcpStatuses} projectId={projectId} />
      )}
    </div>
  );
}
