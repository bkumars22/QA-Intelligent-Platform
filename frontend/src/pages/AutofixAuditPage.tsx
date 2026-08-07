import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GitPullRequest, Search, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { autofixApi } from '../services/autofixApi';
import type { AutofixAuditEntry } from '../services/autofixApi';
import { SeverityBadge } from '../components/SeverityBadge';

const STATUS_CONFIG: Record<AutofixAuditEntry['status'], { label: string; className: string }> = {
  pr_opened: { label: 'PR Opened', className: 'bg-green-100 text-green-700' },
  tests_failed: { label: 'Tests Failed', className: 'bg-red-100 text-red-700' },
  apply_failed: { label: 'Patch Did Not Apply', className: 'bg-amber-100 text-amber-700' },
  branch_failed: { label: 'Branch Failed', className: 'bg-gray-100 text-gray-600' },
  push_failed: { label: 'Push Failed', className: 'bg-gray-100 text-gray-600' },
  pr_failed: { label: 'PR Creation Failed', className: 'bg-red-100 text-red-700' },
  clone_failed: { label: 'Clone Failed', className: 'bg-gray-100 text-gray-600' },
};

function AutofixStatusBadge({ status }: { status: AutofixAuditEntry['status'] }) {
  const config = STATUS_CONFIG[status] ?? { label: status, className: 'bg-gray-100 text-gray-600' };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
}

function TestsBadge({ testsPassed }: { testsPassed: boolean | null }) {
  if (testsPassed === null) {
    return <span className="text-xs text-gray-400">not run</span>;
  }
  return testsPassed
    ? <span className="text-xs font-medium text-green-600">passed</span>
    : <span className="text-xs font-medium text-red-600">failed</span>;
}

function AuditRow({ entry }: { entry: AutofixAuditEntry }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <tr className="border-b border-gray-100 hover:bg-gray-50">
        <td className="py-3 pr-4 pl-4 align-top whitespace-nowrap text-xs text-gray-400">
          {new Date(entry.createdAt).toLocaleString()}
        </td>
        <td className="py-3 pr-4 align-top">
          <p className="text-sm font-medium text-gray-800">{entry.defectTitle}</p>
          <p className="text-xs font-mono text-gray-400 mt-0.5">{entry.filePath}</p>
        </td>
        <td className="py-3 pr-4 align-top"><SeverityBadge severity={entry.severity} /></td>
        <td className="py-3 pr-4 align-top"><AutofixStatusBadge status={entry.status} /></td>
        <td className="py-3 pr-4 align-top"><TestsBadge testsPassed={entry.testsPassed} /></td>
        <td className="py-3 pr-4 align-top">
          {entry.prUrl ? (
            <a
              href={entry.prUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"
            >
              <ExternalLink size={12} /> PR
            </a>
          ) : (
            <span className="text-xs text-gray-300">—</span>
          )}
        </td>
        <td className="py-3 align-top">
          <button
            onClick={() => setExpanded(e => !e)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800"
          >
            Why {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </td>
      </tr>
      {expanded && (
        <tr className="border-b border-gray-100 bg-gray-50/60">
          <td colSpan={7} className="py-3 pl-4 pr-4">
            <p className="text-xs text-gray-600 leading-relaxed mb-2">{entry.why || 'No explanation recorded.'}</p>
            {entry.detail && (
              <p className="text-xs font-mono text-gray-500 bg-white border border-gray-200 rounded-lg p-2 whitespace-pre-wrap">
                {entry.detail}
              </p>
            )}
            <p className="text-[11px] text-gray-400 mt-2">
              branch: <span className="font-mono">{entry.branch}</span> · run: <span className="font-mono">{entry.runId}</span>
            </p>
          </td>
        </tr>
      )}
    </>
  );
}

export function AutofixAuditPage() {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [search, setSearch] = useState('');

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['autofix-audit', statusFilter],
    queryFn: () => autofixApi.list(statusFilter ? { status: statusFilter } : undefined),
  });

  const filtered = useMemo(() => {
    if (!search.trim()) return entries;
    const q = search.toLowerCase();
    return entries.filter(
      e => e.filePath.toLowerCase().includes(q) || e.defectTitle.toLowerCase().includes(q)
    );
  }, [entries, search]);

  const openedCount = entries.filter(e => e.status === 'pr_opened').length;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-1">
        <GitPullRequest size={22} className="text-brand-600" />
        <h1 className="text-xl font-bold text-gray-900">Auto-Fix Audit</h1>
      </div>
      <p className="text-sm text-gray-500 mb-6">
        Every fix CodegenerateAgent has attempted — what changed, why, whether the real test suite
        passed, and the PR it opened (or why it didn't). Nothing here was ever committed directly;
        every row is reversible by closing its PR or reverting the merge.
      </p>

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search file or defect…"
            className="pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-lg w-64 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">All statuses</option>
          {Object.entries(STATUS_CONFIG).map(([value, cfg]) => (
            <option key={value} value={value}>{cfg.label}</option>
          ))}
        </select>
        <span className="text-xs text-gray-400 ml-auto">
          {openedCount} PR{openedCount !== 1 ? 's' : ''} opened · {entries.length} attempt{entries.length !== 1 ? 's' : ''} total
        </span>
      </div>

      {isLoading ? (
        <div className="text-center text-gray-400 py-12">Loading auto-fix history…</div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-gray-400 py-12 bg-white rounded-xl border border-gray-200">
          <GitPullRequest size={32} className="mx-auto mb-3 opacity-30" />
          <p>No auto-fix attempts recorded yet.</p>
          <p className="text-xs mt-1">These appear after a pipeline run finds P0/P1 defects.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 text-xs text-gray-400 uppercase tracking-wide">
                <th className="py-2 pr-4 pl-4 font-medium">When</th>
                <th className="py-2 pr-4 font-medium">Defect / File</th>
                <th className="py-2 pr-4 font-medium">Severity</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">Tests</th>
                <th className="py-2 pr-4 font-medium">PR</th>
                <th className="py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(entry => <AuditRow key={entry.id} entry={entry} />)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
