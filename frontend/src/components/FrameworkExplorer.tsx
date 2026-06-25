import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Folder, FileCode, ChevronRight, ChevronDown,
  Save, Plus, Play, RefreshCw, Check, AlertCircle,
} from 'lucide-react';
import { automationApi } from '../services/automationApi';
import type { FrameworkProfile, FileNode, AutomationExecution } from '../services/automationApi';

// ─── helpers ──────────────────────────────────────────────────────────────────

function extractTestNames(code: string): string[] {
  const re = /\btest\s*\(\s*['"`]([\s\S]+?)['"`]/g;
  const names: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(code)) !== null) names.push(m[1]);
  return names;
}

function newTestSkeleton(fileName: string): string {
  const base = fileName.replace(/\.spec\.ts$/, '').replace(/[-_]/g, ' ');
  return `\n  test('${base} — new test case', async ({ page }) => {\n    // TODO: add your assertions\n    await expect(page.locator('body')).toBeVisible();\n  });\n`;
}

// ─── FileTree ─────────────────────────────────────────────────────────────────

function FileTree({
  nodes,
  selected,
  onSelect,
  newFiles,
}: {
  nodes: FileNode[];
  selected: string | null;
  onSelect: (n: FileNode) => void;
  newFiles: Set<string>;
}) {
  const [openDirs, setOpenDirs] = useState<Set<string>>(new Set());

  const roots = nodes.filter(n => !n.parent && n.type === 'dir');
  const topFiles = nodes.filter(n => !n.parent && n.type === 'file');

  function renderNode(n: FileNode) {
    const isDir = n.type === 'dir';
    const isOpen = openDirs.has(n.path);
    const children = nodes.filter(c => c.parent === n.name);
    const isSelected = selected === n.path;
    const isNew = newFiles.has(n.path);

    return (
      <div key={n.path}>
        <button
          onClick={() => {
            if (isDir) {
              setOpenDirs(prev => {
                const s = new Set(prev);
                s.has(n.path) ? s.delete(n.path) : s.add(n.path);
                return s;
              });
            } else {
              onSelect(n);
            }
          }}
          className={`w-full text-left flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg transition-colors ${
            isSelected ? 'bg-brand-100 text-brand-800 font-medium' : 'text-gray-700 hover:bg-gray-100'
          }`}
        >
          {isDir ? (
            <>
              {isOpen ? <ChevronDown size={13} className="shrink-0 text-gray-400" /> : <ChevronRight size={13} className="shrink-0 text-gray-400" />}
              <Folder size={13} className="shrink-0 text-amber-500" />
            </>
          ) : (
            <>
              <span className="w-3.5 shrink-0" />
              <FileCode size={13} className="shrink-0 text-blue-500" />
            </>
          )}
          <span className="truncate">{n.name}</span>
          {isNew && <span className="ml-auto text-[9px] font-bold text-green-600 bg-green-100 px-1 rounded">NEW</span>}
        </button>
        {isDir && isOpen && children.length > 0 && (
          <div className="ml-4 border-l border-gray-200 pl-1">
            {children.map(c => renderNode(c))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="text-sm">
      {roots.map(n => renderNode(n))}
      {topFiles.map(n => renderNode(n))}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function FrameworkExplorer({
  profile,
  onExecution,
}: {
  profile: FrameworkProfile;
  onExecution: (exec: AutomationExecution) => void;
}) {
  const qc = useQueryClient();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [selectedNode, setSelectedNode] = useState<FileNode | null>(null);
  const [editedContent, setEditedContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [currentSha, setCurrentSha] = useState('');
  const [newTestNames, setNewTestNames] = useState<string[]>([]);
  const [newFiles, setNewFiles] = useState<Set<string>>(new Set());
  const [saveOk, setSaveOk] = useState(false);
  const [saveErr, setSaveErr] = useState('');

  // File tree
  const { data: nodes = [], isLoading: treeLoading } = useQuery({
    queryKey: ['file-tree', profile.id],
    queryFn: () => automationApi.getFileTree(profile.id),
  });

  // File content
  const { data: fileData, isLoading: contentLoading } = useQuery({
    queryKey: ['file-content', profile.id, selectedNode?.path],
    queryFn: () => automationApi.getFileContent(profile.id, selectedNode!.path),
    enabled: !!selectedNode && selectedNode.type === 'file',
  });

  useEffect(() => {
    if (fileData) {
      setOriginalContent(fileData.content);
      setEditedContent(fileData.content);
      setCurrentSha(fileData.sha);
      setSaveOk(false);
      setSaveErr('');
    }
  }, [fileData]);

  // Save mutation
  const saveMut = useMutation({
    mutationFn: () => automationApi.saveFileContent(profile.id, {
      path: selectedNode!.path,
      content: editedContent,
      sha: currentSha,
      commitMessage: `feat: update ${selectedNode!.name} via QAIP`,
    }),
    onSuccess: (result) => {
      // Track newly added tests
      const before = extractTestNames(originalContent);
      const after = extractTestNames(editedContent);
      const added = after.filter(t => !before.includes(t));
      if (added.length > 0) {
        setNewTestNames(prev => [...new Set([...prev, ...added])]);
        setNewFiles(prev => new Set([...prev, selectedNode!.path]));
      }
      setOriginalContent(editedContent);
      setCurrentSha(result.sha);
      setSaveOk(true);
      setSaveErr('');
      setTimeout(() => setSaveOk(false), 3000);
      qc.invalidateQueries({ queryKey: ['file-tree', profile.id] });
    },
    onError: (e: Error) => setSaveErr(e.message),
  });

  // Execute mutations
  const execAllMut = useMutation({
    mutationFn: () => automationApi.executeFromFramework(profile.id, [], true),
    onSuccess: (exec) => onExecution(exec),
  });

  const execNewMut = useMutation({
    mutationFn: () => automationApi.executeFromFramework(profile.id, newTestNames, false),
    onSuccess: (exec) => onExecution(exec),
  });

  function addTestCase() {
    if (!selectedNode) return;
    const skeleton = newTestSkeleton(selectedNode.name);
    const lastBrace = editedContent.lastIndexOf('});');
    const insertAt = lastBrace !== -1 ? lastBrace : editedContent.length;
    const next = editedContent.slice(0, insertAt) + skeleton + editedContent.slice(insertAt);
    setEditedContent(next);
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
        textareaRef.current.focus();
      }
    }, 50);
  }

  const isDirty = editedContent !== originalContent;
  const specFiles = nodes.filter(n => n.type === 'file' && n.name.endsWith('.spec.ts'));
  const totalTests = specFiles.length * 4; // rough estimate for display

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <FileCode size={15} className="text-brand-600" />
          <span className="text-sm font-semibold text-gray-900">Framework Explorer</span>
          <span className="text-xs text-gray-500">
            {profile.repoUrl.replace('https://github.com/', '')} · {profile.branch}
          </span>
        </div>
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ['file-tree', profile.id] })}
          className="p-1.5 rounded hover:bg-gray-200 text-gray-500"
          title="Refresh file tree"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      <div className="flex" style={{ minHeight: '420px' }}>
        {/* Left panel — file tree */}
        <div className="w-56 shrink-0 border-r border-gray-200 p-2 overflow-y-auto" style={{ maxHeight: '580px' }}>
          {treeLoading ? (
            <div className="text-xs text-gray-400 p-3">Loading files…</div>
          ) : nodes.length === 0 ? (
            <div className="text-xs text-gray-400 p-3">No test files found</div>
          ) : (
            <FileTree nodes={nodes} selected={selectedNode?.path ?? null} onSelect={setSelectedNode} newFiles={newFiles} />
          )}
        </div>

        {/* Right panel — editor */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedNode ? (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <FileCode size={32} className="mx-auto mb-2 opacity-30" />
                <p className="text-sm">Select a file to view or edit</p>
                <p className="text-xs mt-1 text-gray-300">{specFiles.length} spec files · est. {totalTests}+ tests</p>
              </div>
            </div>
          ) : (
            <>
              {/* File path bar */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 bg-gray-50">
                <span className="text-xs font-mono text-gray-600">{selectedNode.path}</span>
                <div className="flex items-center gap-2">
                  {isDirty && (
                    <span className="text-xs text-amber-600 font-medium">Unsaved changes</span>
                  )}
                  {saveOk && (
                    <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                      <Check size={11} /> Saved to GitHub
                    </span>
                  )}
                  {saveErr && (
                    <span className="flex items-center gap-1 text-xs text-red-600">
                      <AlertCircle size={11} /> {saveErr.slice(0, 40)}
                    </span>
                  )}
                  {selectedNode.name !== 'auth.ts' && selectedNode.name !== 'playwright.config.ts' && (
                    <button
                      onClick={addTestCase}
                      className="flex items-center gap-1 text-xs px-2.5 py-1 bg-brand-600 text-white rounded-lg hover:bg-brand-700"
                    >
                      <Plus size={11} /> Add Test Case
                    </button>
                  )}
                  <button
                    onClick={() => saveMut.mutate()}
                    disabled={!isDirty || saveMut.isPending}
                    className="flex items-center gap-1 text-xs px-2.5 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                  >
                    <Save size={11} /> {saveMut.isPending ? 'Saving…' : 'Save to GitHub'}
                  </button>
                </div>
              </div>

              {/* Code editor */}
              {contentLoading ? (
                <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
              ) : (
                <textarea
                  ref={textareaRef}
                  value={editedContent}
                  onChange={e => setEditedContent(e.target.value)}
                  spellCheck={false}
                  className="flex-1 w-full px-4 py-3 font-mono text-xs bg-[#1e1e2e] text-[#cdd6f4] resize-none focus:outline-none leading-relaxed"
                  style={{ minHeight: '340px', tabSize: 2 }}
                />
              )}
            </>
          )}
        </div>
      </div>

      {/* Execute bar */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
        <div className="text-xs text-gray-500">
          {newTestNames.length > 0
            ? <span className="text-green-700 font-medium">{newTestNames.length} new test{newTestNames.length > 1 ? 's' : ''} added this session</span>
            : <span>Edit any spec file and save to track new tests</span>
          }
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => execAllMut.mutate()}
            disabled={execAllMut.isPending}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-800 text-white rounded-lg hover:bg-gray-900 disabled:opacity-60"
          >
            <Play size={12} /> {execAllMut.isPending ? 'Running…' : 'Execute All'}
          </button>
          <button
            onClick={() => execNewMut.mutate()}
            disabled={newTestNames.length === 0 || execNewMut.isPending}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-60 disabled:cursor-not-allowed"
            title={newTestNames.length === 0 ? 'Add and save new tests first' : `Run: ${newTestNames.join(', ')}`}
          >
            <Play size={12} /> {execNewMut.isPending ? 'Running…' : `Execute Newly Added${newTestNames.length > 0 ? ` (${newTestNames.length})` : ''}`}
          </button>
        </div>
      </div>

      {/* New test names preview */}
      {newTestNames.length > 0 && (
        <div className="px-4 pb-3">
          <p className="text-xs font-medium text-gray-500 mb-1">Newly added tests queued for execution:</p>
          <div className="flex flex-wrap gap-1">
            {newTestNames.map(t => (
              <span key={t} className="inline-flex items-center gap-1 text-xs bg-green-50 border border-green-200 text-green-800 px-2 py-0.5 rounded-full">
                <Check size={9} /> {t}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
