import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChevronDown, ChevronRight, Save, RotateCcw, Check, AlertCircle,
} from 'lucide-react';
import { configureMcp } from '../services/api';
import type { McpStatus, McpServerType } from '../types';

// ─── Per-server field definitions ────────────────────────────────────────────

interface FieldDef {
  key: string;
  label: string;
  placeholder: string;
  type: 'text' | 'url' | 'password' | 'select';
  options?: string[];
  secret?: boolean;
  required?: boolean;
}

const SERVER_FIELDS: Record<McpServerType, FieldDef[]> = {
  PLAYWRIGHT: [
    { key: 'baseUrl', label: 'Base URL', placeholder: 'https://your-app.example.com', type: 'url', required: true },
    { key: 'headless', label: 'Headless Mode', placeholder: '', type: 'select', options: ['true', 'false'] },
    { key: 'timeout', label: 'Timeout (ms)', placeholder: '30000', type: 'text' },
    { key: 'workers', label: 'Parallel Workers', placeholder: '2', type: 'text' },
    { key: 'retries', label: 'Retries on Failure', placeholder: '1', type: 'text' },
  ],
  GITHUB: [
    { key: 'repoUrl', label: 'Repository URL', placeholder: 'https://github.com/org/repo', type: 'url', required: true },
    { key: 'branch', label: 'Branch', placeholder: 'main', type: 'text', required: true },
    { key: 'githubToken', label: 'GitHub PAT (Personal Access Token)', placeholder: 'ghp_...', type: 'password', secret: true },
  ],
  FILESYSTEM: [
    { key: 'rootPath', label: 'Root Path', placeholder: '/workspace/project', type: 'text', required: true },
    { key: 'allowedExtensions', label: 'Allowed Extensions', placeholder: '.ts,.java,.py', type: 'text' },
    { key: 'excludePaths', label: 'Exclude Paths', placeholder: 'node_modules,target,.git', type: 'text' },
  ],
  JIRA: [
    { key: 'jiraBaseUrl', label: 'Jira Base URL', placeholder: 'https://yourorg.atlassian.net', type: 'url', required: true },
    { key: 'jiraProject', label: 'Project Key', placeholder: 'PROJ', type: 'text', required: true },
    { key: 'jiraToken', label: 'Jira API Token', placeholder: 'ATATT3x...', type: 'password', secret: true },
  ],
  SLACK: [
    { key: 'slackWebhookUrl', label: 'Webhook URL', placeholder: 'https://hooks.slack.com/services/...', type: 'url', required: true },
    { key: 'slackChannel', label: 'Channel', placeholder: '#qa-alerts', type: 'text' },
    { key: 'notifyOnFailure', label: 'Notify on Failure', placeholder: '', type: 'select', options: ['true', 'false'] },
  ],
};

const SERVER_ICONS: Record<McpServerType, string> = {
  PLAYWRIGHT: 'PW',
  GITHUB: 'GH',
  FILESYSTEM: 'FS',
  JIRA: 'JR',
  SLACK: 'SL',
};

const SERVER_COLORS: Record<McpServerType, string> = {
  PLAYWRIGHT: 'bg-purple-100 text-purple-700',
  GITHUB: 'bg-gray-100 text-gray-700',
  FILESYSTEM: 'bg-amber-100 text-amber-700',
  JIRA: 'bg-blue-100 text-blue-700',
  SLACK: 'bg-green-100 text-green-700',
};

// ─── Single server card ───────────────────────────────────────────────────────

function McpServerCard({
  status,
  projectId,
}: {
  status: McpStatus;
  projectId: number;
}) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState<Record<string, string>>(status.config ?? {});
  const [savedOk, setSavedOk] = useState(false);
  const [error, setError] = useState('');

  const fields = SERVER_FIELDS[status.serverType];

  const saveMut = useMutation({
    mutationFn: () => configureMcp(projectId, { serverType: status.serverType, config: values }),
    onSuccess: () => {
      // Update mock config in-place for demo mode
      if (status.config) Object.assign(status.config, values);
      setSavedOk(true);
      setError('');
      setEditing(false);
      setTimeout(() => setSavedOk(false), 3000);
      void qc.invalidateQueries({ queryKey: ['mcp-status', projectId] });
    },
    onError: (e: Error) => setError(e.message),
  });

  function reset() {
    setValues(status.config ?? {});
    setEditing(false);
    setError('');
  }

  return (
    <div className={`bg-white rounded-xl border ${status.isActive ? 'border-gray-200' : 'border-red-200'} overflow-hidden`}>
      {/* Card header */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className={`text-xs font-bold px-2 py-0.5 rounded ${SERVER_COLORS[status.serverType]}`}>
            {SERVER_ICONS[status.serverType]}
          </span>
          <div className="text-left">
            <p className="text-sm font-semibold text-gray-900">{status.serverType}</p>
            <p className="text-xs text-gray-400">
              Last checked: {new Date(status.lastChecked).toLocaleTimeString()}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
            status.isActive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full ${status.isActive ? 'bg-green-500' : 'bg-red-500'}`} />
            {status.isActive ? 'Connected' : 'Disconnected'}
          </span>
          {savedOk && <span className="flex items-center gap-1 text-xs text-green-600"><Check size={11} /> Saved</span>}
          {expanded ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
        </div>
      </button>

      {/* Expanded config panel */}
      {expanded && (
        <div className="border-t border-gray-100 px-5 py-4 space-y-3">
          {/* Config fields */}
          <div className="grid grid-cols-1 gap-3">
            {fields.map(f => {
              const val = values[f.key] ?? '';
              const isMasked = f.secret && !editing && val && !val.startsWith('ghp_') && !val.startsWith('ATATT');

              return (
                <div key={f.key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    {f.label}
                    {f.required && <span className="text-red-500 ml-0.5">*</span>}
                  </label>
                  {editing ? (
                    f.type === 'select' ? (
                      <select
                        value={val}
                        onChange={e => setValues(p => ({ ...p, [f.key]: e.target.value }))}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none"
                      >
                        {f.options?.map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    ) : (
                      <input
                        type={f.type === 'password' ? 'text' : f.type}
                        value={val}
                        onChange={e => setValues(p => ({ ...p, [f.key]: e.target.value }))}
                        placeholder={f.placeholder}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none font-mono"
                      />
                    )
                  ) : (
                    <div className="px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg font-mono text-gray-700 min-h-[36px]">
                      {val
                        ? (f.secret ? val.replace(/[^•]/g, c => c === '•' ? '•' : '•') : val)
                        : <span className="text-gray-400 text-xs">Not configured</span>
                      }
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Error message */}
          {error && (
            <div className="flex items-center gap-1.5 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <AlertCircle size={12} /> {error}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-2 pt-1">
            {editing ? (
              <>
                <button
                  onClick={() => saveMut.mutate()}
                  disabled={saveMut.isPending}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-60"
                >
                  <Save size={11} /> {saveMut.isPending ? 'Saving…' : 'Save Configuration'}
                </button>
                <button
                  onClick={reset}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600"
                >
                  <RotateCcw size={11} /> Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => setEditing(true)}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-700"
              >
                Configure
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Exported panel ───────────────────────────────────────────────────────────

export function McpConfigPanel({
  statuses,
  projectId,
}: {
  statuses: McpStatus[];
  projectId: number;
}) {
  const MCP_ORDER: McpServerType[] = ['PLAYWRIGHT', 'GITHUB', 'FILESYSTEM', 'JIRA', 'SLACK'];

  const ordered = MCP_ORDER.map(type =>
    statuses.find(s => s.serverType === type) ?? {
      serverType: type,
      isActive: false,
      lastChecked: new Date().toISOString(),
      config: {},
    }
  );

  const connected = ordered.filter(s => s.isActive).length;

  return (
    <div className="space-y-4">
      {/* Summary row */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900">MCP Server Configuration</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {connected}/{ordered.length} servers connected · Click any server to view or edit configuration
          </p>
        </div>
        <div className="flex items-center gap-2">
          {ordered.map(s => (
            <span
              key={s.serverType}
              className={`h-2.5 w-2.5 rounded-full ${s.isActive ? 'bg-green-500' : 'bg-red-400'}`}
              title={`${s.serverType}: ${s.isActive ? 'Connected' : 'Disconnected'}`}
            />
          ))}
        </div>
      </div>

      {/* Server cards */}
      <div className="space-y-3">
        {ordered.map(s => (
          <McpServerCard key={s.serverType} status={s} projectId={projectId} />
        ))}
      </div>
    </div>
  );
}
