/**
 * TraceViewerPanel — OpenTelemetry distributed trace viewer.
 *
 * Polls GET /telemetry/traces every 5 s and renders:
 *  • Live metrics strip (requests, avg latency, block rate, RAGAS avg)
 *  • List of recent traces with duration, status, span count
 *  • Per-trace waterfall diagram — each span as a coloured bar
 *    (width = fraction of parent duration, left offset = start offset)
 */
import { useState, useEffect, useCallback } from 'react'
import { Activity, ChevronDown, ChevronRight, RefreshCw, Zap, Shield, Brain } from 'lucide-react'

const AI_ENGINE = import.meta.env.VITE_AI_ENGINE_URL ?? 'http://localhost:8001'
const POLL_MS   = 5_000

// ── Types ─────────────────────────────────────────────────────────────────────

interface OtelSpan {
  name:            string
  span_id:         string
  parent_span_id:  string | null
  start_offset_ms: number
  duration_ms:     number
  status:          string
  attributes:      Record<string, unknown>
}

interface OtelTrace {
  trace_id:       string
  root_op:        string
  start_time_iso: string
  duration_ms:    number
  status:         string
  span_count:     number
  spans:          OtelSpan[]
}

interface MetricsData {
  rag:         { requests_total: number; blocked_total: number; block_rate_pct: number; avg_latency_ms: number; avg_hops: number }
  guardrails:  { checks_total: number; blocked_total: number; block_rate_pct: number }
  memory:      { operations_total: number }
  ragas:       { evals_total: number; avg_overall: number | null; avg_faithfulness: number | null; recent_50_scores: number[] }
  analyze:     { requests_total: number }
  otel_available: boolean
  otel_backend:   string
}

// ── Span colour by name prefix ───────────────────────────────────────────────

const SPAN_COLOR: Record<string, string> = {
  'rag.pipeline':       'bg-blue-600',
  'rag.plan':           'bg-blue-400',
  'rag.retrieve':       'bg-cyan-500',
  'rag.grade':          'bg-indigo-400',
  'rag.generate':       'bg-violet-500',
  'rag.check':          'bg-purple-400',
  'rag.rewrite':        'bg-sky-400',
  'guardrails':         'bg-red-500',
  'memory':             'bg-purple-600',
  'GET ':               'bg-slate-500',
  'POST ':              'bg-slate-500',
}

function spanColor(name: string): string {
  for (const [prefix, cls] of Object.entries(SPAN_COLOR)) {
    if (name.startsWith(prefix)) return cls
  }
  return 'bg-slate-500'
}

function spanCategory(name: string): string {
  if (name.startsWith('rag.'))        return 'RAG'
  if (name.startsWith('guardrails'))  return 'Guardrails'
  if (name.startsWith('memory'))      return 'Memory'
  return 'HTTP'
}

// ── Waterfall ─────────────────────────────────────────────────────────────────

function WaterfallRow({ span, parentDuration }: { span: OtelSpan; parentDuration: number }) {
  const [open, setOpen] = useState(false)
  const pct     = parentDuration > 0 ? Math.min(100, (span.duration_ms / parentDuration) * 100) : 100
  const leftPct = parentDuration > 0 ? (span.start_offset_ms / parentDuration) * 100 : 0
  const isRoot  = !span.parent_span_id
  const color   = spanColor(span.name)
  const hasAttrs = Object.keys(span.attributes).length > 0

  return (
    <div className={`${isRoot ? '' : 'pl-4 border-l border-slate-700'}`}>
      <div
        className={`flex items-center gap-2 py-1.5 ${hasAttrs ? 'cursor-pointer' : ''}`}
        onClick={() => hasAttrs && setOpen(o => !o)}
      >
        {/* Name */}
        <div className="w-44 shrink-0 flex items-center gap-1 min-w-0">
          {hasAttrs
            ? (open ? <ChevronDown size={10} className="text-slate-500 shrink-0" /> : <ChevronRight size={10} className="text-slate-500 shrink-0" />)
            : <span className="w-3 shrink-0" />}
          <span className="text-xs text-slate-300 truncate font-mono" title={span.name}>{span.name}</span>
        </div>
        {/* Bar */}
        <div className="flex-1 relative h-4 bg-slate-800 rounded overflow-hidden">
          <div
            className={`absolute top-0 h-full rounded ${color} opacity-80`}
            style={{ left: `${leftPct}%`, width: `${Math.max(pct, 1)}%` }}
          />
        </div>
        {/* Duration */}
        <span className="w-16 text-right text-xs text-slate-400 font-mono shrink-0">
          {span.duration_ms >= 1000 ? `${(span.duration_ms / 1000).toFixed(1)}s` : `${span.duration_ms}ms`}
        </span>
        {/* Status */}
        <span className={`w-12 text-right text-xs font-semibold shrink-0 ${span.status === 'ERROR' ? 'text-red-400' : 'text-green-500'}`}>
          {span.status}
        </span>
      </div>
      {open && hasAttrs && (
        <div className="pl-7 pb-1">
          <div className="bg-slate-800/60 rounded-lg px-3 py-2 space-y-0.5">
            {Object.entries(span.attributes).map(([k, v]) => (
              <div key={k} className="flex gap-2 text-xs">
                <span className="text-slate-500 w-36 shrink-0 truncate">{k}</span>
                <span className="text-slate-300 font-mono">{String(v)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TraceRow({ trace }: { trace: OtelTrace }) {
  const [open, setOpen] = useState(false)
  const isError  = trace.status === 'ERROR'
  const timeStr  = new Date(trace.start_time_iso).toLocaleTimeString()

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-800/50 transition-colors"
      >
        {/* Trace ID */}
        <span className="font-mono text-xs text-slate-500 w-20 shrink-0">{trace.trace_id.slice(0, 8)}…</span>
        {/* Root op */}
        <span className={`flex-1 text-xs font-semibold ${spanColor(trace.root_op).replace('bg-', 'text-').replace('-600', '-400').replace('-500', '-400')}`}>
          {trace.root_op}
        </span>
        {/* Time */}
        <span className="text-xs text-slate-500 w-20 text-right shrink-0">{timeStr}</span>
        {/* Duration */}
        <span className="text-xs text-slate-300 font-mono w-16 text-right shrink-0">
          {trace.duration_ms >= 1000 ? `${(trace.duration_ms / 1000).toFixed(2)}s` : `${trace.duration_ms}ms`}
        </span>
        {/* Status */}
        <span className={`text-xs font-bold w-14 text-right shrink-0 ${isError ? 'text-red-400' : 'text-green-500'}`}>
          {trace.status}
        </span>
        {/* Span count */}
        <span className="text-xs text-slate-600 w-14 text-right shrink-0">{trace.span_count} spans</span>
        {open ? <ChevronDown size={12} className="text-slate-500 shrink-0" /> : <ChevronRight size={12} className="text-slate-500 shrink-0" />}
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-slate-700 pt-3 space-y-0.5">
          {/* Column headers */}
          <div className="flex items-center gap-2 mb-2">
            <span className="w-44 text-xs text-slate-600">Span</span>
            <span className="flex-1 text-xs text-slate-600">Timeline</span>
            <span className="w-16 text-right text-xs text-slate-600">Duration</span>
            <span className="w-12 text-right text-xs text-slate-600">Status</span>
          </div>
          {trace.spans.map((span) => (
            <WaterfallRow key={span.span_id} span={span} parentDuration={trace.duration_ms} />
          ))}
        </div>
      )}
    </div>
  )
}

// ── Metrics strip ─────────────────────────────────────────────────────────────

function MetricTile({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-slate-800 rounded-lg px-4 py-3 text-center">
      <div className={`text-lg font-bold ${color ?? 'text-white'}`}>{value}</div>
      <div className="text-slate-400 text-xs mt-0.5">{label}</div>
      {sub && <div className="text-slate-600 text-xs mt-0.5">{sub}</div>}
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function TraceViewerPanel() {
  const [traces,  setTraces]  = useState<OtelTrace[]>([])
  const [metrics, setMetrics] = useState<MetricsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)

  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const [traceRes, metricRes] = await Promise.all([
        fetch(`${AI_ENGINE}/telemetry/traces?limit=20`),
        fetch(`${AI_ENGINE}/telemetry/metrics`),
      ])
      if (traceRes.ok) {
        const d = await traceRes.json()
        setTraces(d.traces ?? [])
      }
      if (metricRes.ok) {
        setMetrics(await metricRes.json())
      }
      setLastFetch(new Date())
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchAll()
    const t = setInterval(fetchAll, POLL_MS)
    return () => clearInterval(t)
  }, [fetchAll])

  const ragas50 = metrics?.ragas.recent_50_scores ?? []
  const ragas50Max = ragas50.length > 0 ? Math.max(...ragas50) : 1

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-700 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Activity size={15} className="text-green-400" />
            OpenTelemetry Traces
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Distributed spans · in-memory exporter
            {lastFetch && ` · updated ${lastFetch.toLocaleTimeString()}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {metrics?.otel_available === false && (
            <span className="text-xs text-amber-400 bg-amber-900/30 border border-amber-700/40 px-2 py-1 rounded">
              OTel SDK not installed
            </span>
          )}
          <button
            onClick={fetchAll}
            disabled={loading}
            className="p-1.5 text-slate-400 hover:text-slate-200 disabled:opacity-40 transition-colors"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Metrics strip */}
        {metrics && (
          <div className="space-y-3">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Zap size={11} /> Live Metrics
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
              <MetricTile label="RAG Requests" value={String(metrics.rag.requests_total)} />
              <MetricTile label="Avg Latency"  value={`${metrics.rag.avg_latency_ms}ms`}
                color={metrics.rag.avg_latency_ms > 3000 ? 'text-amber-400' : 'text-green-400'} />
              <MetricTile label="Avg Hops"     value={String(metrics.rag.avg_hops)}
                color={metrics.rag.avg_hops >= 2 ? 'text-amber-400' : 'text-white'} />
              <MetricTile label="Block Rate"   value={`${metrics.guardrails.block_rate_pct}%`}
                sub={`${metrics.guardrails.blocked_total} blocked`}
                color={metrics.guardrails.block_rate_pct > 10 ? 'text-red-400' : 'text-green-400'} />
              <MetricTile label="RAGAS Avg"
                value={metrics.ragas.avg_overall !== null ? `${Math.round((metrics.ragas.avg_overall) * 100)}%` : '—'}
                color={metrics.ragas.avg_overall !== null && metrics.ragas.avg_overall >= 0.75 ? 'text-green-400' : 'text-amber-400'} />
              <MetricTile label="Memory Ops"   value={String(metrics.memory.operations_total)}
                color="text-purple-400" />
            </div>

            {/* RAGAS sparkline */}
            {ragas50.length > 0 && (
              <div>
                <div className="text-xs text-slate-600 mb-1">RAGAS overall — last {ragas50.length} evals</div>
                <div className="flex items-end gap-0.5 h-8">
                  {ragas50.map((s, i) => (
                    <div
                      key={i}
                      title={`${Math.round(s * 100)}%`}
                      className={`flex-1 rounded-sm ${s >= 0.75 ? 'bg-green-500' : s >= 0.5 ? 'bg-amber-400' : 'bg-red-500'}`}
                      style={{ height: `${Math.max(15, (s / ragas50Max) * 100)}%`, opacity: 0.85 }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Trace list */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Activity size={11} /> Recent Traces ({traces.length})
          </div>
          {traces.length === 0 && !loading && (
            <div className="text-slate-600 text-xs text-center py-8">
              <Activity size={24} className="mx-auto mb-2 text-slate-700" />
              No traces yet — send a RAG query to generate spans.
            </div>
          )}
          {traces.map((trace) => (
            <TraceRow key={trace.trace_id} trace={trace} />
          ))}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 pt-2 border-t border-slate-700/50">
          {[
            { label: 'RAG Pipeline',  cls: 'bg-blue-600' },
            { label: 'Retrieval',     cls: 'bg-cyan-500' },
            { label: 'Generation',    cls: 'bg-violet-500' },
            { label: 'Guardrails',    cls: 'bg-red-500' },
            { label: 'Memory (Zep)',  cls: 'bg-purple-600' },
            { label: 'HTTP',          cls: 'bg-slate-500' },
          ].map(({ label, cls }) => (
            <span key={label} className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className={`w-2.5 h-2.5 rounded-sm ${cls}`} />
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
