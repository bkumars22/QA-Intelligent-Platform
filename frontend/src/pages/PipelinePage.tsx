import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Eye, Loader2, Workflow, Zap } from 'lucide-react';
import { pipelineApi } from '../services/pipelineApi';
import type { PipelineRun } from '../services/pipelineApi';
import PipelineProgressLive from '../components/PipelineProgressLive';

const AI_ENGINE = import.meta.env.VITE_AI_ENGINE_URL ?? 'http://localhost:8001';

// ────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────

function isRunning(status: string): boolean {
  return status.startsWith('STAGE_');
}

interface PipelineStatusBadgeProps {
  status: string;
}

function PipelineStatusBadge({ status }: PipelineStatusBadgeProps) {
  if (status === 'AWAITING_APPROVAL') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
        Awaiting Review
      </span>
    );
  }
  if (status === 'COMPLETED') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
        Completed
      </span>
    );
  }
  if (status === 'FAILED') {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
        Failed
      </span>
    );
  }
  if (isRunning(status)) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-600 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600" />
        </span>
        Running
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
      {status}
    </span>
  );
}

function StageBadge({ stage }: { stage: number }) {
  return (
    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold bg-brand-100 text-brand-700">
      {stage}
    </span>
  );
}

// ────────────────────────────────────────────────────────────
// Page
// ────────────────────────────────────────────────────────────

export function PipelinePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // For listing, default projectId = 0 means all (server can handle)
  const [filterProjectId, setFilterProjectId] = useState<number>(1);
  const [showForm, setShowForm] = useState(false);
  const [formProjectId, setFormProjectId] = useState('');
  const [formJiraStoryId, setFormJiraStoryId] = useState('');

  // V2 live analysis state
  const [showV2, setShowV2]           = useState(false);
  const [v2RepoUrl, setV2RepoUrl]     = useState('');
  const [v2Token, setV2Token]         = useState('');
  const [v2ProjectId, setV2ProjectId] = useState('1');
  const [v2CommitSha, setV2CommitSha] = useState('HEAD');
  const [v2RunId, setV2RunId]         = useState<string | null>(null);
  const [v2Starting, setV2Starting]   = useState(false);
  const [v2Error, setV2Error]         = useState('');

  async function handleStartV2(e: React.FormEvent) {
    e.preventDefault();
    setV2Starting(true);
    setV2Error('');
    setV2RunId(null);
    try {
      const res = await fetch(`${AI_ENGINE}/analyze/v2`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: parseInt(v2ProjectId, 10),
          repo_url: v2RepoUrl,
          github_token: v2Token,
          commit_sha: v2CommitSha || 'HEAD',
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setV2RunId(data.run_id);
    } catch (err: unknown) {
      setV2Error(err instanceof Error ? err.message : 'Failed to start v2 analysis');
    } finally {
      setV2Starting(false);
    }
  }

  const { data: runs = [], isLoading } = useQuery<PipelineRun[]>({
    queryKey: ['pipeline-runs', filterProjectId],
    queryFn: () => pipelineApi.list(filterProjectId),
    refetchInterval: (query) =>
      (query.state.data as PipelineRun[] | undefined)?.some((r) => isRunning(r.status))
        ? 5_000
        : false,
  });

  const startMutation = useMutation({
    mutationFn: pipelineApi.start,
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-runs'] });
      navigate(`/pipeline/${run.id}`);
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const pid = parseInt(formProjectId, 10);
    if (!pid || !formJiraStoryId.trim()) return;
    startMutation.mutate({ projectId: pid, jiraStoryId: formJiraStoryId.trim() });
  }

  return (
    <div className="p-6 md:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Workflow size={22} className="text-brand-600" />
            <h1 className="text-2xl font-bold text-gray-900">QA Pipeline</h1>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Autonomous 7-stage QA from Jira story to CI/CD
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowV2((v) => !v); setShowForm(false); }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-white text-sm font-medium hover:bg-slate-700 transition-colors"
          >
            <Zap size={16} />
            Live Analysis (v2)
          </button>
          <button
            onClick={() => { setShowForm((v) => !v); setShowV2(false); }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            <Plus size={16} />
            Start New Pipeline
          </button>
        </div>
      </div>

      {/* Inline form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">New Pipeline Run</h2>
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-700 mb-1">Project ID</label>
              <input
                type="number"
                min={1}
                required
                value={formProjectId}
                onChange={(e) => setFormProjectId(e.target.value)}
                placeholder="e.g. 1"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-700 mb-1">Jira Story ID</label>
              <input
                type="text"
                required
                value={formJiraStoryId}
                onChange={(e) => setFormJiraStoryId(e.target.value)}
                placeholder="e.g. PROJ-123"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <button
              type="submit"
              disabled={startMutation.isPending}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-60 transition-colors whitespace-nowrap"
            >
              {startMutation.isPending && <Loader2 size={15} className="animate-spin" />}
              Start Pipeline
            </button>
          </form>
          {startMutation.isError && (
            <p className="text-sm text-red-600 mt-3">
              Failed to start pipeline. Please check your inputs and try again.
            </p>
          )}
        </div>
      )}

      {/* V2 Live Analysis panel */}
      {showV2 && (
        <div className="bg-slate-900 rounded-xl border border-slate-700 p-6 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Zap size={16} className="text-blue-400" />
            Live Analysis — v2 (parallel pipeline + SSE streaming)
          </h2>
          {!v2RunId ? (
            <form onSubmit={handleStartV2} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">GitHub Repo URL</label>
                <input
                  type="url"
                  required
                  value={v2RepoUrl}
                  onChange={(e) => setV2RepoUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">GitHub Token</label>
                <input
                  type="password"
                  value={v2Token}
                  onChange={(e) => setV2Token(e.target.value)}
                  placeholder="ghp_… (optional for public repos)"
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Project ID</label>
                <input
                  type="number"
                  min={1}
                  required
                  value={v2ProjectId}
                  onChange={(e) => setV2ProjectId(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Commit SHA</label>
                <input
                  type="text"
                  value={v2CommitSha}
                  onChange={(e) => setV2CommitSha(e.target.value)}
                  placeholder="HEAD or full SHA"
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="sm:col-span-2 flex items-center gap-3">
                <button
                  type="submit"
                  disabled={v2Starting}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60 transition-colors"
                >
                  {v2Starting && <Loader2 size={15} className="animate-spin" />}
                  Start v2 Analysis
                </button>
                {v2Error && <span className="text-sm text-red-400">{v2Error}</span>}
              </div>
            </form>
          ) : (
            <div className="space-y-3">
              <PipelineProgressLive
                runId={v2RunId}
                onDone={() => {
                  queryClient.invalidateQueries({ queryKey: ['pipeline-runs'] });
                }}
              />
              <button
                onClick={() => { setV2RunId(null); setV2Error(''); }}
                className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                ← Start another analysis
              </button>
            </div>
          )}
        </div>
      )}

      {/* Project filter */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium text-gray-700">Filter by Project ID:</label>
        <input
          type="number"
          min={1}
          value={filterProjectId}
          onChange={(e) => setFilterProjectId(parseInt(e.target.value, 10) || 1)}
          className="w-24 border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={28} className="animate-spin text-brand-600" />
          </div>
        ) : runs.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-400">
            No pipeline runs found for project {filterProjectId}.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-xs font-medium text-gray-500 uppercase tracking-wide">
                  <th className="px-6 py-3 text-left">ID</th>
                  <th className="px-6 py-3 text-left">Story ID</th>
                  <th className="px-6 py-3 text-left">Summary</th>
                  <th className="px-6 py-3 text-left">Stage</th>
                  <th className="px-6 py-3 text-left">Status</th>
                  <th className="px-6 py-3 text-left">Started</th>
                  <th className="px-6 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-3 font-mono text-gray-700">#{run.id}</td>
                    <td className="px-6 py-3 font-medium text-gray-900">{run.jiraStoryId}</td>
                    <td className="px-6 py-3 text-gray-600 max-w-xs truncate" title={run.jiraSummary}>
                      {run.jiraSummary || '—'}
                    </td>
                    <td className="px-6 py-3">
                      <StageBadge stage={run.currentStage} />
                    </td>
                    <td className="px-6 py-3">
                      <PipelineStatusBadge status={run.status} />
                    </td>
                    <td className="px-6 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {new Date(run.startedAt).toLocaleString()}
                    </td>
                    <td className="px-6 py-3">
                      <button
                        onClick={() => navigate(`/pipeline/${run.id}`)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <Eye size={13} />
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
