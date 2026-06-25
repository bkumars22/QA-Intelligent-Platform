import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Zap, Link2, CheckCircle2, XCircle, Play,
  Download, Copy, ChevronDown, ChevronRight, FolderOpen,
} from 'lucide-react';
import { automationApi } from '../services/automationApi';
import type { FrameworkProfile, AutomationExecution, AutomationResult } from '../services/automationApi';
import { FrameworkExplorer } from './FrameworkExplorer';

// ─── Framework type cards ─────────────────────────────────────────────────────
type FwType = 'PLAYWRIGHT' | 'SELENIUM';

const FW_CARDS: { type: FwType; icon: string; title: string; desc: string }[] = [
  {
    type: 'PLAYWRIGHT',
    icon: '🎭',
    title: 'Playwright TypeScript',
    desc: 'Modern browser automation, fast execution, built-in assertions',
  },
  {
    type: 'SELENIUM',
    icon: '☕',
    title: 'Selenium Java',
    desc: 'Enterprise-grade, legacy app support, broad browser coverage',
  },
];

function statusDot(status: FrameworkProfile['status']) {
  if (status === 'CONNECTED') return <span className="h-2.5 w-2.5 rounded-full bg-green-500 inline-block" />;
  if (status === 'FAILED') return <span className="h-2.5 w-2.5 rounded-full bg-red-500 inline-block" />;
  if (status === 'ANALYSING') return <span className="h-2.5 w-2.5 rounded-full bg-yellow-400 animate-pulse inline-block" />;
  return <span className="h-2.5 w-2.5 rounded-full bg-gray-300 inline-block" />;
}

function execStatusBadge(status: AutomationExecution['status']) {
  const map: Record<string, string> = {
    PASSED: 'bg-green-100 text-green-700',
    FAILED: 'bg-red-100 text-red-700',
    RUNNING: 'bg-blue-100 text-blue-700',
    QUEUED: 'bg-gray-100 text-gray-600',
    ERROR: 'bg-orange-100 text-orange-700',
  };
  return `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${map[status] ?? 'bg-gray-100 text-gray-600'}`;
}

// ─── Execution result row ─────────────────────────────────────────────────────
function ResultRow({ r }: { r: AutomationResult }) {
  const [open, setOpen] = useState(false);
  let explanation: Record<string, string> | null = null;
  try { if (r.aiExplanation) explanation = JSON.parse(r.aiExplanation); } catch {}

  return (
    <>
      <tr className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer" onClick={() => setOpen(o => !o)}>
        <td className="px-4 py-2.5 text-sm text-gray-800 flex items-center gap-2">
          {open ? <ChevronDown size={13} className="text-gray-400 shrink-0" /> : <ChevronRight size={13} className="text-gray-400 shrink-0" />}
          {r.testName}
        </td>
        <td className="px-4 py-2.5">
          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
            r.status === 'PASSED' ? 'bg-green-100 text-green-700' : r.status === 'SKIPPED' ? 'bg-gray-100 text-gray-500' : 'bg-red-100 text-red-700'
          }`}>{r.status}</span>
        </td>
        <td className="px-4 py-2.5 text-xs text-gray-500">{r.durationMs != null ? `${r.durationMs}ms` : '—'}</td>
        <td className="px-4 py-2.5">
          {r.jiraTicketKey && (
            <a href={r.jiraTicketUrl ?? '#'} target="_blank" rel="noreferrer"
              className="text-xs text-blue-600 underline" onClick={e => e.stopPropagation()}>
              {r.jiraTicketKey}
            </a>
          )}
        </td>
      </tr>
      {open && (
        <tr className="bg-slate-50">
          <td colSpan={4} className="px-6 py-3">
            {r.errorMessage && (
              <div className="mb-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                <strong>Error:</strong> {r.errorMessage}
              </div>
            )}
            {explanation && (
              <div className="grid grid-cols-2 gap-2 text-xs">
                {(['root_cause', 'business_impact', 'fix_recommendation'] as const).map(k => (
                  <div key={k} className="bg-white border border-gray-200 rounded p-2">
                    <p className="font-semibold text-gray-500 uppercase text-[10px] mb-1">{k.replace(/_/g, ' ')}</p>
                    <p className="text-gray-800">{(explanation as Record<string, string>)[k]}</p>
                  </div>
                ))}
                {explanation.severity && (
                  <div className="bg-white border border-gray-200 rounded p-2">
                    <p className="font-semibold text-gray-500 uppercase text-[10px] mb-1">Severity</p>
                    <span className="inline-flex px-2 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-700">
                      {explanation.severity}
                    </span>
                  </div>
                )}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

// ─── Code panel ───────────────────────────────────────────────────────────────
function CodePanel({ exec }: { exec: AutomationExecution }) {
  const [copied, setCopied] = useState(false);
  const code = exec.generatedCode ?? '';
  const lines = code.split('\n').length;
  const estTime = `~${Math.max(1, Math.round(lines / 10))} min`;

  return (
    <div className="mt-4 border border-gray-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
        <div className="text-xs text-gray-500">{lines} lines · est. execution {estTime}</div>
        <div className="flex gap-2">
          <button
            onClick={() => { void navigator.clipboard.writeText(code).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); }); }}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800"
          >
            <Copy size={12} /> {copied ? 'Copied' : 'Copy'}
          </button>
          <a
            href={`data:text/plain;charset=utf-8,${encodeURIComponent(code)}`}
            download={`${exec.suiteName.replace(/\s+/g, '_')}.${exec.frameworkType === 'PLAYWRIGHT' ? 'spec.ts' : 'Test.java'}`}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800"
          >
            <Download size={12} /> Download
          </a>
        </div>
      </div>
      <pre className="text-xs bg-[#1e1e2e] text-[#cdd6f4] p-4 overflow-x-auto max-h-96 overflow-y-auto leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

// ─── Execution card ───────────────────────────────────────────────────────────
function ExecutionCard({ exec, projectId }: { exec: AutomationExecution; projectId: number }) {
  const [showCode, setShowCode] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const qc = useQueryClient();

  const { data: results = [] } = useQuery({
    queryKey: ['automation-results', exec.id],
    queryFn: () => automationApi.getResults(exec.id),
    enabled: showResults,
  });

  const executeMut = useMutation({
    mutationFn: () => automationApi.execute(exec.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['automation-executions', projectId] }),
  });

  const pct = exec.totalTests > 0 ? Math.round((exec.passed / exec.totalTests) * 100) : 0;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-gray-900 text-sm">{exec.suiteName}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {exec.frameworkType === 'PLAYWRIGHT' ? '🎭 Playwright' : '☕ Selenium'} · {new Date(exec.createdAt).toLocaleString()}
          </p>
        </div>
        <span className={execStatusBadge(exec.status)}>{exec.status}</span>
      </div>

      {exec.totalTests > 0 && (
        <div>
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span>{exec.passed} passed · {exec.failed} failed · {exec.skipped} skipped</span>
            <span className={pct >= 80 ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>{pct}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${pct >= 80 ? 'bg-green-500' : 'bg-red-500'}`} style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {exec.status === 'QUEUED' && (
          <button
            onClick={() => executeMut.mutate()}
            disabled={executeMut.isPending}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-60"
          >
            <Play size={12} /> {executeMut.isPending ? 'Starting…' : 'Execute'}
          </button>
        )}
        {exec.status === 'FAILED' && (
          <button
            onClick={() => executeMut.mutate()}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            <Play size={12} /> Re-run
          </button>
        )}
        {exec.generatedCode && (
          <button
            onClick={() => setShowCode(o => !o)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700"
          >
            <Copy size={12} /> {showCode ? 'Hide Code' : 'View Code'}
          </button>
        )}
        {exec.totalTests > 0 && (
          <button
            onClick={() => setShowResults(o => !o)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700"
          >
            <ChevronDown size={12} /> {showResults ? 'Hide Results' : 'View Results'}
          </button>
        )}
        {exec.reportUrl && (
          <a
            href={exec.reportUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            <Download size={12} /> Report
          </a>
        )}
      </div>

      {showCode && exec.generatedCode && <CodePanel exec={exec} />}

      {showResults && results.length > 0 && (
        <div className="border border-gray-200 rounded-lg overflow-hidden mt-2">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                {['Test', 'Status', 'Duration', 'Jira'].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.map(r => <ResultRow key={r.id} r={r} />)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export function AutomationTab({
  projectId,
  projectRepoUrl,
  suggestedFile,
}: {
  projectId: number;
  projectRepoUrl?: string;
  suggestedFile?: string | null;
}) {
  const qc = useQueryClient();
  const [selectedFw, setSelectedFw] = useState<FwType>('PLAYWRIGHT');
  const [repoUrl, setRepoUrl] = useState(projectRepoUrl ?? '');
  const [branch, setBranch] = useState('main');
  const [githubToken, setGithubToken] = useState('');
  const [suiteName, setSuiteName] = useState('');
  const [testTitles, setTestTitles] = useState('');
  const [genProfileId, setGenProfileId] = useState<number | null>(null);
  const [showGenForm, setShowGenForm] = useState(false);
  const [activeTab, setActiveTab] = useState<'explorer' | 'generate'>('explorer');

  const { data: profiles = [], isLoading: profilesLoading } = useQuery({
    queryKey: ['framework-profiles', projectId],
    queryFn: () => automationApi.getFrameworks(projectId),
    refetchInterval: 5000,
  });

  const { data: executions = [] } = useQuery({
    queryKey: ['automation-executions', projectId],
    queryFn: () => automationApi.getExecutions(projectId),
    refetchInterval: 3000,
  });

  const connectMut = useMutation({
    mutationFn: () => automationApi.connectFramework({
      projectId, frameworkType: selectedFw, repoUrl, branch, githubToken: githubToken || undefined,
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['framework-profiles', projectId] }),
  });

  const genMut = useMutation({
    mutationFn: () => automationApi.generateCode({
      projectId,
      frameworkProfileId: genProfileId!,
      suiteName,
      testCaseTitles: testTitles.split('\n').map(t => t.trim()).filter(Boolean),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['automation-executions', projectId] });
      setShowGenForm(false);
      setSuiteName('');
      setTestTitles('');
    },
  });

  const connectedProfile = profiles.find(p => p.frameworkType === selectedFw && p.status === 'CONNECTED');

  // When arriving from Coverage Gaps "Generate Tests", pre-fill the form
  useEffect(() => {
    if (!suggestedFile) return;
    const fileName = suggestedFile.split('/').pop() ?? suggestedFile;
    const baseName = fileName.replace(/\.(java|py|tsx?|jsx?|cs|rb|go)$/, '');
    setSuiteName(`${baseName} Test Suite`);
    setTestTitles(
      `Verify ${baseName} loads successfully\nVerify ${baseName} with valid credentials\nVerify ${baseName} with invalid input\nVerify ${baseName} access control`
    );
    setShowGenForm(true);
    if (connectedProfile) setGenProfileId(connectedProfile.id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [suggestedFile]);

  return (
    <div className="space-y-6">
      {/* File-specific generation banner */}
      {suggestedFile && (
        <div className="p-3 bg-brand-50 border border-brand-200 rounded-lg flex items-start gap-2 text-sm">
          <Zap size={15} className="text-brand-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-medium text-brand-800">Generating tests for: </span>
            <span className="font-mono text-brand-700 break-all">{suggestedFile}</span>
            <p className="text-xs text-brand-600 mt-0.5">
              Suite name and test titles are pre-filled below. Connect a framework first, then click Generate.
            </p>
          </div>
        </div>
      )}

      {/* Framework selector */}
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Link2 size={16} /> Connect Automation Framework
        </h3>

        {/* Framework cards */}
        <div className="grid grid-cols-2 gap-4 mb-5">
          {FW_CARDS.map(card => {
            const p = profiles.find(pr => pr.frameworkType === card.type);
            return (
              <button
                key={card.type}
                onClick={() => setSelectedFw(card.type)}
                className={`relative text-left p-4 rounded-xl border-2 transition-all ${
                  selectedFw === card.type
                    ? 'border-brand-500 bg-brand-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="text-2xl mb-2">{card.icon}</div>
                  {p && (
                    <div className="flex items-center gap-1.5 text-xs">
                      {statusDot(p.status)}
                      <span className="text-gray-500">{p.status}</span>
                    </div>
                  )}
                </div>
                <p className="font-semibold text-gray-900 text-sm">{card.title}</p>
                <p className="text-xs text-gray-500 mt-1">{card.desc}</p>
              </button>
            );
          })}
        </div>

        {/* Connection form */}
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Framework GitHub Repo URL</label>
            <input
              type="url"
              value={repoUrl}
              onChange={e => setRepoUrl(e.target.value)}
              placeholder="https://github.com/yourorg/your-playwright-framework"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Branch</label>
              <input
                value={branch}
                onChange={e => setBranch(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">GitHub Token (optional)</label>
              <input
                type="password"
                value={githubToken}
                onChange={e => setGithubToken(e.target.value)}
                placeholder="ghp_..."
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none"
              />
            </div>
          </div>
          <button
            onClick={() => connectMut.mutate()}
            disabled={!repoUrl || connectMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            <Zap size={14} />
            {connectMut.isPending ? 'Analysing…' : 'Connect Framework'}
          </button>
          {connectMut.isError && (
            <p className="text-xs text-red-600 flex items-center gap-1">
              <XCircle size={12} /> Connection failed. Check the repo URL and try again.
            </p>
          )}
        </div>

        {/* Connected profile summary */}
        {connectedProfile?.summaryText && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800">
            <div className="flex items-center gap-1.5 font-semibold mb-1">
              <CheckCircle2 size={13} /> Framework connected
            </div>
            <p>{connectedProfile.summaryText}</p>
            {connectedProfile.pageObjectsCount != null && (
              <p className="mt-1 text-green-600">
                {connectedProfile.pageObjectsCount} page objects · {connectedProfile.testFilesCount} test files
              </p>
            )}
          </div>
        )}
      </div>

      {/* Framework explorer + AI generate — tab switcher */}
      {connectedProfile && (
        <div className="space-y-4">
          {/* Tab switcher */}
          <div className="flex gap-1 p-1 bg-gray-100 rounded-xl w-fit">
            <button
              onClick={() => setActiveTab('explorer')}
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors font-medium ${
                activeTab === 'explorer' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <FolderOpen size={13} /> Framework Explorer
            </button>
            <button
              onClick={() => { setActiveTab('generate'); setGenProfileId(connectedProfile.id); setShowGenForm(true); }}
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors font-medium ${
                activeTab === 'generate' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Zap size={13} /> AI Generate New Suite
            </button>
          </div>

          {/* Framework Explorer tab */}
          {activeTab === 'explorer' && (
            <FrameworkExplorer
              profile={connectedProfile}
              onExecution={() => qc.invalidateQueries({ queryKey: ['automation-executions', projectId] })}
            />
          )}

          {/* AI Generate tab */}
          {activeTab === 'generate' && (
            <div className="bg-white border border-gray-200 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                  <Zap size={16} /> Generate Automation Code
                </h3>
                <button
                  onClick={() => { setGenProfileId(connectedProfile.id); setShowGenForm(o => !o); }}
                  className="text-xs px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700"
                >
                  + New Suite
                </button>
              </div>

              {showGenForm && (
                <div className="space-y-3 mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Suite Name</label>
                    <input
                      value={suiteName}
                      onChange={e => setSuiteName(e.target.value)}
                      placeholder="e.g. SCIP Authentication Suite"
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Test case titles (one per line)
                    </label>
                    <textarea
                      value={testTitles}
                      onChange={e => setTestTitles(e.target.value)}
                      rows={5}
                      placeholder={"Login with valid credentials\nLogin with invalid password\nPassword reset flow"}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 outline-none font-mono"
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => genMut.mutate()}
                      disabled={!suiteName || !testTitles || genMut.isPending}
                      className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-60"
                    >
                      <Zap size={12} /> {genMut.isPending ? 'Generating…' : 'Generate'}
                    </button>
                    <button onClick={() => setShowGenForm(false)} className="text-xs px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-100">Cancel</button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Executions */}
      {executions.length > 0 && (
        <div>
          <h3 className="text-base font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Play size={16} /> Execution History
          </h3>
          <div className="space-y-3">
            {executions.map(e => <ExecutionCard key={e.id} exec={e} projectId={projectId} />)}
          </div>
        </div>
      )}

      {!connectedProfile && !profilesLoading && executions.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <Zap size={32} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">Connect your automation framework to get started.</p>
          <p className="text-xs mt-1">Works with SCIP, ARIA, and any project.</p>
        </div>
      )}
    </div>
  );
}
