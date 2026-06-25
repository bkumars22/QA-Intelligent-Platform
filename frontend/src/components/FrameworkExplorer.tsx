import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Folder, FileCode, ChevronRight, ChevronDown,
  Play, RefreshCw,
} from 'lucide-react';
import { automationApi } from '../services/automationApi';
import type { FrameworkProfile, FileNode, AutomationExecution } from '../services/automationApi';
import { useQueryClient } from '@tanstack/react-query';

// ─── FileTree ─────────────────────────────────────────────────────────────────

function FileTree({
  nodes,
  selected,
  onSelect,
}: {
  nodes: FileNode[];
  selected: string | null;
  onSelect: (n: FileNode) => void;
}) {
  const [openDirs, setOpenDirs] = useState<Set<string>>(new Set());

  const roots = nodes.filter(n => !n.parent && n.type === 'dir');
  const topFiles = nodes.filter(n => !n.parent && n.type === 'file');

  function renderNode(n: FileNode) {
    const isDir = n.type === 'dir';
    const isOpen = openDirs.has(n.path);
    const children = nodes.filter(c => c.parent === n.name);
    const isSelected = selected === n.path;

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

  const [selectedNode, setSelectedNode] = useState<FileNode | null>(null);
  const [displayContent, setDisplayContent] = useState('');

  // File tree
  const { data: nodes = [], isLoading: treeLoading } = useQuery({
    queryKey: ['file-tree', profile.id],
    queryFn: () => automationApi.getFileTree(profile.id),
  });

  // File content (read-only)
  const { data: fileData, isLoading: contentLoading } = useQuery({
    queryKey: ['file-content', profile.id, selectedNode?.path],
    queryFn: () => automationApi.getFileContent(profile.id, selectedNode!.path),
    enabled: !!selectedNode && selectedNode.type === 'file',
  });

  useEffect(() => {
    if (fileData) {
      setDisplayContent(fileData.content);
    }
  }, [fileData]);

  // Execute all tests
  const execAllMut = useMutation({
    mutationFn: () => automationApi.executeFromFramework(profile.id, [], true),
    onSuccess: (exec) => onExecution(exec),
  });

  const specFiles = nodes.filter(n => n.type === 'file' && n.name.endsWith('.spec.ts'));
  const totalTests = specFiles.length * 4;

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
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">read-only</span>
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
            <FileTree nodes={nodes} selected={selectedNode?.path ?? null} onSelect={setSelectedNode} />
          )}
        </div>

        {/* Right panel — read-only viewer */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {!selectedNode ? (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <FileCode size={32} className="mx-auto mb-2 opacity-30" />
                <p className="text-sm">Select a file to view</p>
                <p className="text-xs mt-1 text-gray-300">{specFiles.length} spec files · est. {totalTests}+ tests</p>
              </div>
            </div>
          ) : (
            <>
              {/* File path bar */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 bg-gray-50">
                <span className="text-xs font-mono text-gray-600">{selectedNode.path}</span>
                <span className="text-xs text-gray-400 italic">read-only view</span>
              </div>

              {/* Code viewer */}
              {contentLoading ? (
                <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
              ) : (
                <textarea
                  value={displayContent}
                  readOnly
                  spellCheck={false}
                  className="flex-1 w-full px-4 py-3 font-mono text-xs bg-[#1e1e2e] text-[#cdd6f4] resize-none focus:outline-none leading-relaxed cursor-default select-text"
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
          {specFiles.length} spec files connected · execute all tests via QAIP runner
        </div>
        <button
          onClick={() => execAllMut.mutate()}
          disabled={execAllMut.isPending}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-800 text-white rounded-lg hover:bg-gray-900 disabled:opacity-60"
        >
          <Play size={12} /> {execAllMut.isPending ? 'Running…' : 'Execute All'}
        </button>
      </div>
    </div>
  );
}
