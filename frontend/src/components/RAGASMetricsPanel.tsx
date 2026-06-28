import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, FlaskConical, TrendingUp, Clock } from 'lucide-react'

const AI_ENGINE = import.meta.env.VITE_AI_ENGINE_URL ?? 'http://localhost:8001'

// ── Types ──────────────────────────────────────────────────────────────────

interface EvalRow {
  id:                 number
  question:           string
  answer:             string
  faithfulness:       number | null
  answer_relevancy:   number | null
  context_precision:  number | null
  context_recall:     number | null
  overall:            number | null
  context_count:      number
  is_grounded:        boolean
  eval_duration_ms:   number
  created_at:         string
}

interface AggStats {
  total_evals:            number
  avg_faithfulness:       number | null
  avg_answer_relevancy:   number | null
  avg_context_precision:  number | null
  avg_context_recall:     number | null
  avg_overall:            number | null
  min_overall:            number | null
  max_overall:            number | null
  avg_context_count:      number | null
  grounded_count:         number
  days_window:            number
}

interface Props {
  projectId: number
}

// ── Helpers ────────────────────────────────────────────────────────────────

function scoreColor(v: number | null): string {
  if (v === null || v < 0) return 'text-slate-500'
  if (v >= 0.75) return 'text-emerald-400'
  if (v >= 0.5)  return 'text-yellow-400'
  return 'text-red-400'
}

function ScoreGauge({ label, value, description }: { label: string; value: number | null; description: string }) {
  const pct = value !== null && value >= 0 ? Math.min(value * 100, 100) : null
  const color = value !== null && value >= 0
    ? (value >= 0.75 ? 'bg-emerald-500' : value >= 0.5 ? 'bg-yellow-500' : 'bg-red-500')
    : 'bg-slate-600'

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex flex-col gap-2">
      <p className="text-xs text-slate-400 font-medium">{label}</p>
      <div className="flex items-end gap-2">
        <span className={`text-2xl font-bold tabular-nums ${scoreColor(value)}`}>
          {pct !== null ? `${pct.toFixed(0)}%` : '—'}
        </span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct ?? 0}%` }} />
      </div>
      <p className="text-xs text-slate-600 leading-snug">{description}</p>
    </div>
  )
}

function EvalRowCard({ row }: { row: EvalRow }) {
  const [open, setOpen] = useState(false)
  const ts = new Date(row.created_at).toLocaleString()

  return (
    <div className="border border-slate-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-slate-800/60 transition-colors"
      >
        {/* Overall badge */}
        <span className={`text-sm font-bold tabular-nums w-12 shrink-0 ${scoreColor(row.overall)}`}>
          {row.overall !== null ? `${(row.overall * 100).toFixed(0)}%` : '—'}
        </span>

        {/* Question preview */}
        <p className="flex-1 text-xs text-slate-300 truncate">{row.question}</p>

        {/* Mini score chips */}
        <div className="hidden sm:flex gap-1 shrink-0">
          {[
            ['F', row.faithfulness],
            ['AR', row.answer_relevancy],
            ['CP', row.context_precision],
          ].map(([lbl, val]) => (
            <span key={String(lbl)} className={`text-xs px-1.5 py-0.5 rounded font-mono bg-slate-700 ${scoreColor(val as number | null)}`}>
              {lbl}: {val !== null ? (val as number).toFixed(2) : '—'}
            </span>
          ))}
        </div>

        <span className="text-xs text-slate-600 shrink-0 ml-1">{ts}</span>
        {open ? <ChevronDown size={13} className="text-slate-500 shrink-0" /> : <ChevronRight size={13} className="text-slate-500 shrink-0" />}
      </button>

      {open && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-700 space-y-3">
          {/* Full metric row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              ['Faithfulness',      row.faithfulness],
              ['Ans. Relevancy',    row.answer_relevancy],
              ['Context Precision', row.context_precision],
              ['Context Recall',    row.context_recall],
            ].map(([lbl, val]) => (
              <div key={String(lbl)} className="bg-slate-900 rounded-lg p-2 text-center">
                <p className="text-xs text-slate-500">{String(lbl)}</p>
                <p className={`text-sm font-bold ${scoreColor(val as number | null)}`}>
                  {val !== null && (val as number) >= 0 ? `${((val as number) * 100).toFixed(1)}%` : 'N/A'}
                </p>
              </div>
            ))}
          </div>

          {/* Answer preview */}
          <div>
            <p className="text-xs text-slate-500 mb-1">Answer</p>
            <p className="text-xs text-slate-400 leading-relaxed line-clamp-4">{row.answer}</p>
          </div>

          <div className="flex gap-4 text-xs text-slate-600">
            <span>Contexts: {row.context_count}</span>
            <span>Grounded: {row.is_grounded ? '✓' : '✗'}</span>
            <span>Eval time: {row.eval_duration_ms}ms</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Inline metrics badge (used by AgenticRAGChat) ──────────────────────────

export function RAGASBadge({ metrics }: { metrics: Record<string, number> | null }) {
  if (!metrics) return null
  return (
    <div className="flex gap-1.5 flex-wrap mt-2">
      {[
        ['F', metrics.faithfulness,      'Faithfulness'],
        ['AR', metrics.answer_relevancy, 'Answer Relevancy'],
        ['CP', metrics.context_precision,'Context Precision'],
      ].map(([lbl, val, title]) => (
        <span
          key={String(lbl)}
          title={String(title)}
          className={`text-xs font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 ${scoreColor(val as number)}`}
        >
          {lbl}: {(val as number | null) !== null ? ((val as number) * 100).toFixed(0) + '%' : '—'}
        </span>
      ))}
      <span
        title="Overall RAGAS score"
        className={`text-xs font-mono px-2 py-0.5 rounded bg-slate-700 border border-slate-600 ${scoreColor(metrics.overall)}`}
      >
        Overall: {metrics.overall !== undefined ? (metrics.overall * 100).toFixed(0) + '%' : '—'}
      </span>
    </div>
  )
}

// ── Main panel ─────────────────────────────────────────────────────────────

export default function RAGASMetricsPanel({ projectId }: Props) {
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['ragas-stats', projectId],
    queryFn: async () => {
      const res = await fetch(`${AI_ENGINE}/rag/eval/stats?project_id=${projectId}&days=30`)
      if (!res.ok) throw new Error('Failed to load stats')
      return res.json() as Promise<{ stats: AggStats; days_window: number }>
    },
    refetchInterval: 60_000,
    retry: false,
  })

  const { data: resultsData, isLoading: resultsLoading } = useQuery({
    queryKey: ['ragas-results', projectId],
    queryFn: async () => {
      const res = await fetch(`${AI_ENGINE}/rag/eval/results?project_id=${projectId}&limit=20`)
      if (!res.ok) throw new Error('Failed to load results')
      return res.json() as Promise<{ results: EvalRow[]; count: number }>
    },
    refetchInterval: 60_000,
    retry: false,
  })

  const stats   = statsData?.stats
  const results = resultsData?.results ?? []

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-700 flex items-center gap-2">
        <FlaskConical size={15} className="text-purple-400" />
        <h3 className="text-sm font-bold text-white">RAGAS Evaluation</h3>
        <span className="text-xs text-slate-500">Faithfulness · Answer Relevancy · Context Precision</span>
        {stats && (
          <span className="ml-auto text-xs text-slate-500 flex items-center gap-1">
            <TrendingUp size={11} />
            {stats.total_evals} evals · last {stats.days_window}d
          </span>
        )}
      </div>

      {/* Aggregate score gauges */}
      <div className="px-5 py-4 border-b border-slate-700">
        {statsLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 animate-pulse">
            {[1,2,3,4].map(i => <div key={i} className="h-24 bg-slate-800 rounded-xl" />)}
          </div>
        ) : stats && stats.total_evals > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <ScoreGauge
              label="Faithfulness"
              value={stats.avg_faithfulness}
              description="Claims in answer supported by retrieved context"
            />
            <ScoreGauge
              label="Ans. Relevancy"
              value={stats.avg_answer_relevancy}
              description="How well the answer addresses the question"
            />
            <ScoreGauge
              label="Context Precision"
              value={stats.avg_context_precision}
              description="Fraction of retrieved chunks that were useful"
            />
            <ScoreGauge
              label="Overall"
              value={stats.avg_overall}
              description={`${stats.grounded_count}/${stats.total_evals} responses grounded`}
            />
          </div>
        ) : (
          <p className="text-slate-600 text-sm text-center py-4">
            No evaluations yet — each <code className="text-slate-400">/rag/ask</code> call auto-evaluates.
          </p>
        )}
      </div>

      {/* Recent eval results */}
      <div className="px-5 py-4 space-y-2">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Recent Evaluations</p>
        {resultsLoading ? (
          <div className="space-y-2 animate-pulse">
            {[1,2,3].map(i => <div key={i} className="h-12 bg-slate-800 rounded-xl" />)}
          </div>
        ) : results.length > 0 ? (
          results.map(row => <EvalRowCard key={row.id} row={row} />)
        ) : (
          <p className="text-slate-600 text-sm text-center py-4">
            No evaluation history yet.
          </p>
        )}
      </div>
    </div>
  )
}
