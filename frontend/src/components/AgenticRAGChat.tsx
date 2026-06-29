import { useState, useRef, useEffect } from 'react'
import { Search, ChevronDown, ChevronRight, Loader2, AlertCircle, CheckCircle, Brain } from 'lucide-react'
import { RAGASBadge } from './RAGASMetricsPanel'
import GuardrailsStatusBadge from './GuardrailsStatusBadge'

const AI_ENGINE = import.meta.env.VITE_AI_ENGINE_URL ?? 'http://localhost:8001'

// ── Types ──────────────────────────────────────────────────────────────────

interface Source {
  index:           number
  source_type:     string
  file_path:       string
  similarity:      number
  content_preview: string
}

interface TraceNode {
  node:          string
  ts:            number
  sub_queries?:  string[]
  rewritten_to?: string
  hop?:          number
  new_docs_count?: number
  relevant_count?: number
  is_grounded?:  boolean
}

interface GuardrailsInfo {
  passed:          boolean
  rail_triggered?: string | null
  risk_score?:     number
  blocked_reason?: string | null
  input_latency?:  number
  output_latency?: number
  latency_ms?:     number
}

interface MemoryInfo {
  session_id:   string
  saved:        boolean
  context_used: boolean
  backend:      string
}

interface RAGResult {
  answer:        string
  sources:       Source[]
  sub_queries:   string[]
  hops:          number
  is_grounded:   boolean
  trace:         TraceNode[]
  ragas_metrics: Record<string, number> | null
  blocked?:      boolean
  guardrails?:   GuardrailsInfo | null
  memory?:       MemoryInfo | null
}

interface Message {
  role:    'user' | 'assistant'
  content: string
  result?: RAGResult
  loading?: boolean
}

interface Props {
  projectId: number
  sessionId?: string
}

// ── Helpers ────────────────────────────────────────────────────────────────

const SOURCE_TYPE_COLOR: Record<string, string> = {
  test_case:   'bg-blue-900/40 text-blue-300 border-blue-700',
  defect:      'bg-red-900/40 text-red-300 border-red-700',
  jira_story:  'bg-purple-900/40 text-purple-300 border-purple-700',
  run_result:  'bg-green-900/40 text-green-300 border-green-700',
}

function simPct(s: number) {
  const pct = Math.round(s * 100)
  const bar = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-400' : 'bg-slate-500'
  return { pct, bar }
}

// ── Source card ────────────────────────────────────────────────────────────

function SourceCard({ src }: { src: Source }) {
  const [open, setOpen] = useState(false)
  const { pct, bar } = simPct(src.similarity)
  const typeStyle = SOURCE_TYPE_COLOR[src.source_type] ?? 'bg-slate-800 text-slate-300 border-slate-600'

  return (
    <div className={`border rounded-lg overflow-hidden ${typeStyle}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs font-bold shrink-0">[{src.index}]</span>
          <span className="text-xs font-semibold shrink-0 uppercase tracking-wide opacity-70">
            {src.source_type.replace('_', ' ')}
          </span>
          {src.file_path && (
            <span className="text-xs opacity-60 truncate">{src.file_path.split('/').slice(-2).join('/')}</span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <div className="w-12 h-1 bg-black/30 rounded-full overflow-hidden">
            <div className={`h-full ${bar} rounded-full`} style={{ width: `${pct}%` }} />
          </div>
          <span className="text-xs opacity-60">{pct}%</span>
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </div>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-1 text-xs opacity-80 border-t border-current/20">
          <pre className="whitespace-pre-wrap font-mono leading-relaxed">{src.content_preview}</pre>
        </div>
      )}
    </div>
  )
}

// ── Trace panel ───────────────────────────────────────────────────────────

function TracePanel({ trace, hops, isGrounded }: { trace: TraceNode[]; hops: number; isGrounded: boolean }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-3 border border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs text-slate-400 hover:bg-slate-800/50"
      >
        <span className="flex items-center gap-2">
          <span className="font-medium">Retrieval trace</span>
          <span className="text-slate-500">{trace.length} steps · {hops} hop{hops !== 1 ? 's' : ''}</span>
          {isGrounded
            ? <CheckCircle size={12} className="text-green-500" />
            : <AlertCircle size={12} className="text-yellow-400" />}
        </span>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-slate-700">
          {trace.map((t, i) => (
            <div key={i} className="text-xs text-slate-400 flex gap-2 pt-2">
              <span className="font-mono text-slate-500 shrink-0">{t.node}</span>
              {t.sub_queries && (
                <span>→ sub-queries: {t.sub_queries.join(' | ')}</span>
              )}
              {t.rewritten_to && (
                <span>→ rewrote to: <em className="text-slate-300">{t.rewritten_to}</em></span>
              )}
              {t.new_docs_count !== undefined && (
                <span>→ {t.new_docs_count} new docs</span>
              )}
              {t.relevant_count !== undefined && (
                <span>→ {t.relevant_count} relevant</span>
              )}
              {t.is_grounded !== undefined && (
                <span className={t.is_grounded ? 'text-green-400' : 'text-yellow-400'}>
                  → {t.is_grounded ? 'grounded' : 'may contain extrapolation'}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function AgenticRAGChat({ projectId, sessionId: propSessionId }: Props) {
  const [messages, setMessages]     = useState<Message[]>([])
  const [input, setInput]           = useState('')
  const [sourceType, setSourceType] = useState<string>('')
  const [loading, setLoading]       = useState(false)
  const bottomRef    = useRef<HTMLDivElement>(null)
  const ownSessionId = useRef<string>(
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `sess-${Date.now()}-${Math.random().toString(36).slice(2)}`
  )
  const sessionId = propSessionId ?? ownSessionId.current

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send() {
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    setLoading(true)

    const userMsg: Message = { role: 'user', content: q }
    const loadingMsg: Message = { role: 'assistant', content: '', loading: true }
    setMessages(prev => [...prev, userMsg, loadingMsg])

    try {
      const res = await fetch(`${AI_ENGINE}/rag/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question:    q,
          project_id:  projectId,
          source_type: sourceType || null,
          session_id:  sessionId,
        }),
      })
      const data: RAGResult = await res.json()

      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: data.answer, result: data },
      ])
    } catch (err) {
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: 'Error: Could not reach the RAG service. Is the AI engine running?' },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-700 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Search size={15} className="text-blue-400" />
            Agentic RAG
          </h3>
          <div className="flex items-center gap-3 mt-0.5">
            <p className="text-xs text-slate-500">
              Query planning · graded retrieval · self-correction · grounded answers
            </p>
            <span className="flex items-center gap-1 text-xs text-purple-400/80">
              <Brain size={10} />
              {messages.filter(m => m.role === 'user').length > 0 ? `${messages.filter(m => m.role === 'user').length} turns remembered` : 'Memory active'}
            </span>
          </div>
        </div>
        <select
          value={sourceType}
          onChange={e => setSourceType(e.target.value)}
          className="text-xs bg-slate-800 border border-slate-600 text-slate-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All sources</option>
          <option value="test_case">Test cases</option>
          <option value="defect">Defects</option>
          <option value="jira_story">Jira stories</option>
          <option value="run_result">Run results</option>
        </select>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-slate-500 text-sm text-center py-10 space-y-2">
            <Search size={28} className="mx-auto text-slate-600" />
            <p>Ask anything about your QA knowledge base.</p>
            <p className="text-xs">e.g. "What defects were found in the auth module?"<br/>or "Show test patterns for login flows"</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-2' : 'order-1'}`}>
              {msg.role === 'user' ? (
                <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                  {msg.content}
                </div>
              ) : (
                <div className="space-y-3">
                  {msg.loading ? (
                    <div className="flex items-center gap-2 text-slate-400 text-sm px-1">
                      <Loader2 size={14} className="animate-spin" />
                      Planning queries and retrieving…
                    </div>
                  ) : (
                    <>
                      <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                        {msg.content}
                      </div>

                      {msg.result && (
                        <div className="space-y-2 px-1">
                          {/* Sub-queries pill row */}
                          {msg.result.sub_queries.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              <span className="text-xs text-slate-500">searched:</span>
                              {msg.result.sub_queries.map((q, qi) => (
                                <span key={qi} className="text-xs bg-slate-800 border border-slate-700 text-slate-400 rounded-full px-2 py-0.5">
                                  {q.length > 50 ? q.slice(0, 50) + '…' : q}
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Source cards */}
                          {msg.result.sources.length > 0 && (
                            <div className="space-y-1.5">
                              <span className="text-xs text-slate-500">{msg.result.sources.length} sources cited:</span>
                              {msg.result.sources.map(src => (
                                <SourceCard key={src.index} src={src} />
                              ))}
                            </div>
                          )}

                          {/* Guardrails status */}
                          <GuardrailsStatusBadge
                            guardrails={msg.result.guardrails ?? null}
                            blocked={msg.result.blocked}
                          />

                          {/* Memory status badge */}
                          {msg.result.memory && (
                            <div className="flex items-center gap-1.5 text-xs text-purple-400/80">
                              <Brain size={10} />
                              {msg.result.memory.context_used ? 'context recalled' : 'saved to memory'}
                              <span className="text-slate-600">·</span>
                              <span className="text-slate-600">{msg.result.memory.backend === 'zep_cloud' ? 'Zep Cloud' : 'in-memory'}</span>
                            </div>
                          )}

                          {/* RAGAS quality badges */}
                          {msg.result.ragas_metrics && (
                            <RAGASBadge metrics={msg.result.ragas_metrics} />
                          )}

                          {/* Retrieval trace */}
                          {msg.result.trace.length > 0 && (
                            <TracePanel
                              trace={msg.result.trace}
                              hops={msg.result.hops}
                              isGrounded={msg.result.is_grounded}
                            />
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-5 py-4 border-t border-slate-700">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask about test cases, defects, Jira stories… (Enter to send)"
            rows={2}
            className="flex-1 bg-slate-800 border border-slate-600 text-white rounded-xl px-3 py-2 text-sm placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            className="px-4 rounded-xl bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-1.5"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
          </button>
        </div>
        <p className="text-xs text-slate-600 mt-1.5">Enter ↵ to send · Shift+Enter for newline</p>
      </div>
    </div>
  )
}
