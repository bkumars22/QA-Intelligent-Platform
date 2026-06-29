/**
 * MemoryPanel — displays Zep session memory for the current RAG session.
 *
 * Shows:
 *  • Session context (AI-generated summary of prior conversations)
 *  • Extracted facts
 *  • Recent message pairs
 *  • Semantic / keyword search over session history
 *  • Clear session button
 */
import { useState, useEffect, useCallback } from 'react'
import { Brain, Search, Trash2, RefreshCw, ChevronDown, ChevronRight, Cpu } from 'lucide-react'

const AI_ENGINE = import.meta.env.VITE_AI_ENGINE_URL ?? 'http://localhost:8001'

interface Message {
  role:    'user' | 'assistant'
  content: string
}

interface SessionData {
  session_id:    string
  backend:       string
  context:       string
  facts:         string[]
  messages:      Message[]
  message_count?: number
}

interface SearchResult {
  role:       string
  content:    string
  score:      number
  session_id?: string
}

interface Props {
  sessionId: string
}

function RolePill({ role }: { role: string }) {
  const isUser = role === 'user'
  return (
    <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${isUser ? 'bg-blue-900/40 text-blue-300' : 'bg-slate-700 text-slate-400'}`}>
      {isUser ? 'You' : 'AI'}
    </span>
  )
}

export default function MemoryPanel({ sessionId }: Props) {
  const [data,          setData]          = useState<SessionData | null>(null)
  const [loading,       setLoading]       = useState(false)
  const [searchQuery,   setSearchQuery]   = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null)
  const [searching,     setSearching]     = useState(false)
  const [clearing,      setClearing]      = useState(false)
  const [showMessages,  setShowMessages]  = useState(false)
  const [backend,       setBackend]       = useState<string>('')

  const fetchSession = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const [sessionRes, backendRes] = await Promise.all([
        fetch(`${AI_ENGINE}/memory/session/${sessionId}`),
        fetch(`${AI_ENGINE}/memory/backend`),
      ])
      if (sessionRes.ok) setData(await sessionRes.json())
      if (backendRes.ok) {
        const b = await backendRes.json()
        setBackend(b.backend)
      }
    } catch {}
    setLoading(false)
  }, [sessionId])

  useEffect(() => {
    fetchSession()
  }, [fetchSession])

  async function handleSearch() {
    if (!searchQuery.trim() || !sessionId) return
    setSearching(true)
    try {
      const res = await fetch(`${AI_ENGINE}/memory/session/${sessionId}/search`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ query: searchQuery, top_k: 5 }),
      })
      if (res.ok) {
        const d = await res.json()
        setSearchResults(d.results)
      }
    } catch {}
    setSearching(false)
  }

  async function handleClear() {
    if (!sessionId || clearing) return
    setClearing(true)
    try {
      await fetch(`${AI_ENGINE}/memory/session/${sessionId}`, { method: 'DELETE' })
      setData(null)
      setSearchResults(null)
      setSearchQuery('')
    } catch {}
    setClearing(false)
  }

  const msgCount = data?.message_count ?? data?.messages?.length ?? 0

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Brain size={15} className="text-purple-400" />
            Session Memory
          </h3>
          <div className="flex items-center gap-3 mt-0.5">
            <p className="text-xs text-slate-500">
              {msgCount > 0 ? `${msgCount} message${msgCount !== 1 ? 's' : ''} remembered` : 'No messages yet'}
            </p>
            {backend && (
              <span className={`text-xs px-1.5 py-0.5 rounded border ${
                backend === 'zep_cloud'
                  ? 'bg-purple-900/30 text-purple-400 border-purple-700/50'
                  : 'bg-slate-800 text-slate-500 border-slate-700'
              }`}>
                <Cpu size={9} className="inline mr-1" />
                {backend === 'zep_cloud' ? 'Zep Cloud' : 'In-Memory'}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchSession}
            disabled={loading}
            title="Refresh"
            className="p-1.5 text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={handleClear}
            disabled={clearing || msgCount === 0}
            title="Clear session memory"
            className="p-1.5 text-slate-500 hover:text-red-400 disabled:opacity-30 transition-colors"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      <div className="px-5 py-4 space-y-5">
        {/* Session ID */}
        <div className="font-mono text-xs text-slate-600 truncate" title={sessionId}>
          Session: {sessionId}
        </div>

        {/* Context summary */}
        {data?.context && (
          <div className="space-y-1.5">
            <div className="text-xs font-semibold text-purple-400 uppercase tracking-wider">Context Summary</div>
            <div className="bg-purple-900/10 border border-purple-700/30 rounded-lg p-3 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
              {data.context}
            </div>
          </div>
        )}

        {/* Extracted facts */}
        {data?.facts && data.facts.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
              Extracted Facts ({data.facts.length})
            </div>
            <ul className="space-y-1">
              {data.facts.map((fact, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                  <span className="text-amber-500 shrink-0 mt-0.5">•</span>
                  <span>{fact}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recent messages collapsible */}
        {data?.messages && data.messages.length > 0 && (
          <div className="space-y-1.5">
            <button
              onClick={() => setShowMessages((s) => !s)}
              className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider hover:text-slate-200 transition-colors"
            >
              {showMessages ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
              Recent Turns ({Math.floor(data.messages.length / 2)})
            </button>
            {showMessages && (
              <div className="space-y-2 pl-1">
                {data.messages.slice(-8).map((m, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    <RolePill role={m.role} />
                    <span className="text-slate-400 leading-relaxed line-clamp-3">{m.content}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!loading && (!data || (!data.context && (!data.messages || data.messages.length === 0))) && (
          <div className="text-slate-600 text-xs text-center py-4">
            <Brain size={20} className="mx-auto mb-2 text-slate-700" />
            No memory yet — start chatting and prior context will appear here.
          </div>
        )}

        {/* Search */}
        <div className="space-y-2 pt-2 border-t border-slate-700/50">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Search Memory</div>
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search past conversations…"
              className="flex-1 bg-slate-800 border border-slate-600 text-white rounded-lg px-3 py-1.5 text-xs placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
            <button
              onClick={handleSearch}
              disabled={searching || !searchQuery.trim()}
              className="px-3 rounded-lg bg-purple-600 text-white text-xs hover:bg-purple-700 disabled:opacity-50 transition-colors flex items-center gap-1"
            >
              {searching ? <RefreshCw size={11} className="animate-spin" /> : <Search size={11} />}
            </button>
          </div>

          {searchResults !== null && (
            <div className="space-y-1.5">
              {searchResults.length === 0 && (
                <p className="text-xs text-slate-500 text-center py-2">No matching messages found.</p>
              )}
              {searchResults.map((r, i) => (
                <div key={i} className="bg-slate-800 rounded-lg px-3 py-2 space-y-1">
                  <div className="flex items-center justify-between">
                    <RolePill role={r.role} />
                    <span className="text-xs text-slate-600">{Math.round(r.score * 100)}% match</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed line-clamp-3">{r.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
