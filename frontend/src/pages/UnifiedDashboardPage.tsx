import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Play, Bell, ExternalLink, Activity, Shield, Zap } from 'lucide-react';
import { getProjects, getDashboardStats, getRiskScores, triggerAnalysis } from '../services/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { Project, RiskScore } from '../types';

// ─── Platform health bar ──────────────────────────────────────────────────────
function HealthBar({ label, pct }: { label: string; pct: number }) {
  const filled = Math.round(pct / 10);
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-semibold text-white w-12">{label}</span>
      <div className="flex gap-0.5">
        {Array.from({ length: 10 }, (_, i) => (
          <div key={i} className={`w-3 h-3 rounded-sm ${i < filled ? 'bg-green-400' : 'bg-slate-600'}`} />
        ))}
      </div>
      <span className={`text-sm font-bold ${pct >= 90 ? 'text-green-400' : pct >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>
        {pct}% healthy
      </span>
    </div>
  );
}

// ─── Risk heatmap cell ────────────────────────────────────────────────────────
function HeatCell({ score, path }: { score: number; path: string }) {
  const color = score > 0.7 ? 'bg-red-500' : score > 0.4 ? 'bg-yellow-400' : 'bg-green-500';
  return (
    <div
      title={`${path} — ${Math.round(score * 100)}%`}
      className={`w-4 h-4 rounded-sm ${color} opacity-80 hover:opacity-100 cursor-pointer transition-opacity`}
    />
  );
}

// ─── Live activity item ───────────────────────────────────────────────────────
const MOCK_ACTIVITY = [
  { icon: '🔴', project: 'SCIP', msg: 'P1 defect found in SupplierRiskService', time: '2 min ago' },
  { icon: '✅', project: 'ARIA', msg: 'All socratic engine tests passed', time: '15 min ago' },
  { icon: '🔧', project: 'SCIP', msg: 'Auth module tests running…', time: 'now' },
  { icon: '📋', project: 'ARIA', msg: '8 new test cases generated for homework helper', time: '1 hr ago' },
  { icon: '✅', project: 'SCIP', msg: 'BCrypt null-password test PASSED', time: '1 hr ago' },
  { icon: '⚠️', project: 'ARIA', msg: 'Whisper STT Tamil test flagged for review', time: '2 hr ago' },
];

// ─── Project card ─────────────────────────────────────────────────────────────
function ProjectCard({ project }: { project: Project }) {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const analyseMut = useMutation({
    mutationFn: () => triggerAnalysis(project.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });

  const isScip = project.repoUrl?.includes('SupplyChainPlatformProject');
  const isAria = project.repoUrl?.includes('ARIA');
  const liveUrl = isScip
    ? 'https://bkumars22.github.io/SupplyChainPlatformProject'
    : isAria
    ? 'https://bkumars22.github.io/ARIA'
    : null;

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-bold text-gray-900 text-base leading-tight">{project.name}</h3>
          <p className="text-xs text-gray-500 mt-0.5 font-mono truncate max-w-[220px]">{project.repoUrl}</p>
        </div>
        {liveUrl && (
          <a href={liveUrl} target="_blank" rel="noreferrer"
            className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-800">
            <ExternalLink size={12} /> Live
          </a>
        )}
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-3 text-center">
        {[
          { label: 'Tests', value: '—' },
          { label: 'Coverage', value: '—' },
          { label: 'Defects', value: '—' },
        ].map(s => (
          <div key={s.label} className="bg-gray-50 rounded-lg p-2">
            <p className="text-lg font-bold text-gray-900">{s.value}</p>
            <p className="text-xs text-gray-500">{s.label}</p>
          </div>
        ))}
      </div>

      {/* SCIP / ARIA specific risk callouts */}
      {isScip && (
        <div className="flex items-center gap-2 text-xs bg-red-50 border border-red-100 rounded-lg px-3 py-2 text-red-700">
          <Shield size={13} /> P0 watch: BCrypt null hash test active
        </div>
      )}
      {isAria && (
        <div className="flex items-center gap-2 text-xs bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 text-amber-700">
          <Shield size={13} /> P0 watch: Socratic engine must never give direct answers
        </div>
      )}

      <div className="flex gap-2 mt-auto">
        <button
          onClick={() => analyseMut.mutate()}
          disabled={analyseMut.isPending}
          className="flex-1 flex items-center justify-center gap-1.5 text-xs px-3 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-60"
        >
          <Play size={12} /> {analyseMut.isPending ? 'Running…' : 'Run Analysis'}
        </button>
        <button
          onClick={() => navigate(`/projects/${project.id}`)}
          className="flex-1 text-xs px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700"
        >
          View Details
        </button>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export function UnifiedDashboardPage() {
  const { data: projects = [] } = useQuery({ queryKey: ['projects'], queryFn: getProjects });
  const { data: stats } = useQuery({ queryKey: ['dashboard-stats'], queryFn: getDashboardStats, refetchInterval: 30_000 });

  const scip = projects.find(p => p.repoUrl?.includes('SupplyChainPlatformProject'));
  const aria = projects.find(p => p.repoUrl?.includes('ARIA'));
  const combined = projects.length > 0 ? 94 : 0;

  // Collect risk scores from all projects using first available
  const { data: scipRisk = [] } = useQuery({
    queryKey: ['risk-heatmap', scip?.id],
    queryFn: () => getRiskScores(scip!.id),
    enabled: !!scip,
  });
  const { data: ariaRisk = [] } = useQuery({
    queryKey: ['risk-heatmap', aria?.id],
    queryFn: () => getRiskScores(aria!.id),
    enabled: !!aria,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Platform health banner */}
      <div className="bg-[#0f172a] px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-wrap items-center gap-6">
            {scip && <HealthBar label="SCIP" pct={92} />}
            {aria && <HealthBar label="ARIA" pct={98} />}
            <div className="ml-auto flex items-center gap-4 text-sm text-slate-400">
              <span>Combined: <strong className="text-green-400">{combined}%</strong></span>
              <span>Active runs: <strong className="text-white">{stats?.activeTestRuns ?? 0}</strong></span>
              <span>Open defects: <strong className="text-red-400">{stats?.openDefects ?? 0}</strong></span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Projects', value: projects.length, icon: <Activity size={18} />, color: 'text-brand-600', bg: 'bg-brand-50' },
            { label: 'Active Runs', value: stats?.activeTestRuns ?? 0, icon: <Play size={18} />, color: 'text-orange-600', bg: 'bg-orange-50' },
            { label: 'Open Defects', value: stats?.openDefects ?? 0, icon: <Shield size={18} />, color: 'text-red-600', bg: 'bg-red-50' },
            { label: 'Avg Risk', value: stats ? `${Math.round(stats.avgRiskScore * 100)}%` : '—', icon: <Zap size={18} />, color: 'text-green-600', bg: 'bg-green-50' },
          ].map(card => (
            <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl ${card.bg} flex items-center justify-center ${card.color}`}>{card.icon}</div>
              <div>
                <p className="text-xl font-bold text-gray-900">{card.value}</p>
                <p className="text-xs text-gray-500">{card.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Project cards */}
        <div>
          <h2 className="text-base font-bold text-gray-900 mb-3">Projects Under QAIP</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {[scip, aria].filter(Boolean).map(p => <ProjectCard key={p!.id} project={p!} />)}
            {projects.filter(p => p !== scip && p !== aria).map(p => <ProjectCard key={p.id} project={p} />)}
            {projects.length === 0 && (
              <div className="col-span-2 text-center py-12 text-gray-400 bg-white rounded-2xl border border-gray-200">
                <Activity size={32} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm">No projects registered yet. SCIP and ARIA will appear here automatically.</p>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Live activity feed */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-gray-900">Live Activity</h2>
              <span className="flex items-center gap-1 text-xs text-green-600">
                <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" /> Live
              </span>
            </div>
            <div className="space-y-3">
              {MOCK_ACTIVITY.map((a, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="text-base leading-none mt-0.5">{a.icon}</span>
                  <div className="flex-1">
                    <span className="font-semibold text-gray-800">{a.project} — </span>
                    <span className="text-gray-600">{a.msg}</span>
                  </div>
                  <span className="text-gray-400 shrink-0">{a.time}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Combined risk heatmaps */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-sm font-bold text-gray-900 mb-4">Risk Heatmap — All Projects</h2>
            <div className="grid grid-cols-2 gap-6">
              {[
                { label: 'SCIP', data: scipRisk },
                { label: 'ARIA', data: ariaRisk },
              ].map(({ label, data }) => (
                <div key={label}>
                  <p className="text-xs font-semibold text-gray-500 mb-2">{label}</p>
                  {data.length === 0 ? (
                    <p className="text-xs text-gray-400">Run analysis to see risk data</p>
                  ) : (
                    <div className="flex flex-wrap gap-1">
                      {(data as RiskScore[]).slice(0, 40).map((rs, i) => (
                        <HeatCell key={i} score={rs.riskScore} path={rs.filePath} />
                      ))}
                    </div>
                  )}
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                    <span><span className="inline-block w-2 h-2 rounded-sm bg-red-500 mr-1" />High &gt; 70%</span>
                    <span><span className="inline-block w-2 h-2 rounded-sm bg-yellow-400 mr-1" />Mid</span>
                    <span><span className="inline-block w-2 h-2 rounded-sm bg-green-500 mr-1" />Low</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
