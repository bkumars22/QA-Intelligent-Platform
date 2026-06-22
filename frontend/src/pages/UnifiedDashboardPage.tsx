import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Play, ExternalLink, CheckCircle, AlertCircle, Clock, Zap } from 'lucide-react';
import { getProjects, getDashboardStats, triggerAnalysis } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import type { Project } from '../types';

// ─── Single project card ──────────────────────────────────────────────────────
function ProjectCard({ project, accent }: { project: Project; accent: string }) {
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
    : project.repoUrl ?? null;

  const statusColor =
    project.status === 'ACTIVE' ? 'text-green-600 bg-green-50' :
    project.status === 'RUNNING' ? 'text-orange-600 bg-orange-50' :
    'text-gray-500 bg-gray-100';

  const watchNote = isScip
    ? 'P0 watch: BCrypt null-password test'
    : isAria
    ? 'P0 watch: Socratic engine boundary'
    : null;

  return (
    <div className={`bg-white rounded-2xl border-2 ${accent} p-6 flex flex-col gap-5`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-bold text-gray-900 leading-snug">{project.name}</h2>
          <p className="text-xs text-gray-400 mt-1 font-mono truncate">{project.repoUrl}</p>
        </div>
        <span className={`shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full ${statusColor}`}>
          {project.status ?? 'ACTIVE'}
        </span>
      </div>

      {/* Tech stack pill row */}
      <div className="flex flex-wrap gap-1.5">
        {(project.techStack ?? '').split('+').slice(0, 4).map(t => (
          <span key={t} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full">
            {t.trim()}
          </span>
        ))}
      </div>

      {/* P0 watch note */}
      {watchNote && (
        <div className="flex items-center gap-2 text-xs bg-red-50 border border-red-100 text-red-700 rounded-lg px-3 py-2">
          <AlertCircle size={13} className="shrink-0" />
          {watchNote}
        </div>
      )}

      {/* Action buttons */}
      <div className="grid grid-cols-3 gap-2 mt-auto">
        <button
          onClick={() => navigate(`/projects/${project.id}`)}
          className="col-span-2 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-brand-600 text-white rounded-xl text-sm font-medium hover:bg-brand-700 transition-colors"
        >
          <Zap size={14} /> Open Project
        </button>
        <button
          onClick={() => analyseMut.mutate()}
          disabled={analyseMut.isPending}
          className="flex items-center justify-center gap-1 px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          title="Run AI analysis"
        >
          {analyseMut.isPending
            ? <Clock size={14} className="animate-spin" />
            : <Play size={14} />}
        </button>
      </div>

      {/* Live site link */}
      {liveUrl && (
        <a href={liveUrl} target="_blank" rel="noreferrer"
          className="flex items-center justify-center gap-1.5 text-xs text-gray-400 hover:text-brand-600 transition-colors">
          <ExternalLink size={11} /> View live site
        </a>
      )}
    </div>
  );
}

// ─── Dashboard page ───────────────────────────────────────────────────────────
export function UnifiedDashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: getProjects,
  });
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    refetchInterval: 30_000,
  });

  const scip = projects.find(p => p.repoUrl?.includes('SupplyChainPlatformProject'));
  const aria = projects.find(p => p.repoUrl?.includes('ARIA'));
  const others = projects.filter(p => p !== scip && p !== aria);

  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening';

  const CARD_ACCENTS = [
    'border-blue-200',
    'border-purple-200',
    'border-green-200',
    'border-orange-200',
  ];

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {greeting}, {user?.name?.split(' ')[0] ?? 'there'} 👋
        </h1>
        <p className="text-gray-500 mt-1">QA Intelligent Platform — SCIP and ARIA are monitored here.</p>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Projects', value: projects.length, ok: true },
          { label: 'Active Runs', value: stats?.activeTestRuns ?? 0, ok: (stats?.activeTestRuns ?? 0) === 0 },
          { label: 'Open Defects', value: stats?.openDefects ?? 0, ok: (stats?.openDefects ?? 0) === 0 },
          { label: 'Avg Risk', value: stats ? `${Math.round((stats.avgRiskScore ?? 0) * 100)}%` : '—', ok: true },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-center gap-3">
            {s.ok
              ? <CheckCircle size={18} className="text-green-500 shrink-0" />
              : <AlertCircle size={18} className="text-orange-500 shrink-0" />}
            <div>
              <p className="text-xl font-bold text-gray-900 leading-none">{s.value}</p>
              <p className="text-xs text-gray-400 mt-0.5">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* SCIP + ARIA — primary projects */}
      {(scip || aria) && (
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Your Projects</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            {scip && <ProjectCard project={scip} accent="border-blue-200" />}
            {aria && <ProjectCard project={aria} accent="border-purple-200" />}
          </div>
        </section>
      )}

      {/* Other projects */}
      {others.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Other Projects</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {others.map((p, i) => (
              <ProjectCard key={p.id} project={p} accent={CARD_ACCENTS[i % CARD_ACCENTS.length]} />
            ))}
          </div>
        </section>
      )}

      {/* Empty state — no projects at all */}
      {!isLoading && projects.length === 0 && (
        <div className="bg-white rounded-2xl border-2 border-dashed border-gray-200 p-12 text-center">
          <Zap size={36} className="mx-auto text-gray-300 mb-4" />
          <h3 className="text-base font-semibold text-gray-700">No projects yet</h3>
          <p className="text-sm text-gray-400 mt-1 mb-5">
            SCIP and ARIA will appear here automatically after the next deploy.
            You can also add any project manually.
          </p>
          <button
            onClick={() => navigate('/projects')}
            className="px-5 py-2.5 bg-brand-600 text-white rounded-xl text-sm font-medium hover:bg-brand-700"
          >
            + Add Project
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {[1, 2].map(i => (
            <div key={i} className="bg-white rounded-2xl border border-gray-200 p-6 animate-pulse">
              <div className="h-5 bg-gray-100 rounded w-2/3 mb-3" />
              <div className="h-3 bg-gray-100 rounded w-1/2 mb-6" />
              <div className="h-10 bg-gray-100 rounded-xl" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
