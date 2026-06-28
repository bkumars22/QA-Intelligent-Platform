import { useState } from 'react'
import { ChevronDown, ChevronRight, AlertTriangle, ShieldCheck } from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────────

export interface ShapTop {
  feature: string
  label:   string
  value:   number
}

export interface RiskScoreEntry {
  file_path:      string
  score:          number
  anomaly_flag:   boolean
  features:       Record<string, number | boolean>
  shap_values?:   Record<string, number>
  shap_top?:      ShapTop[]
  shap_sentence?: string
  shap_method?:   string
}

interface Props {
  riskScores: RiskScoreEntry[]
  maxShow?:   number
}

// ── Helpers ────────────────────────────────────────────────────────────────

function riskColor(score: number): string {
  if (score > 0.7) return 'text-red-400'
  if (score > 0.4) return 'text-yellow-400'
  return 'text-green-400'
}

function riskBg(score: number): string {
  if (score > 0.7) return 'border-red-800 bg-red-950/30'
  if (score > 0.4) return 'border-yellow-800 bg-yellow-950/20'
  return 'border-green-900 bg-green-950/20'
}

function shapColor(val: number): string {
  return val > 0 ? 'bg-red-500' : 'bg-green-500'
}

function shapTextColor(val: number): string {
  return val > 0 ? 'text-red-400' : 'text-green-400'
}

const MAX_BAR = 0.6  // clip bar width at this absolute SHAP value

function ShapBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(Math.abs(value) / MAX_BAR, 1) * 100
  const sign = value > 0 ? '+' : ''
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400 w-28 shrink-0 truncate" title={label}>{label}</span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${shapColor(value)}`}
          style={{ width: `${pct}%`, opacity: 0.85 }}
        />
      </div>
      <span className={`text-xs font-mono w-12 text-right shrink-0 ${shapTextColor(value)}`}>
        {sign}{value.toFixed(3)}
      </span>
    </div>
  )
}

// ── File card ─────────────────────────────────────────────────────────────

function FileRiskCard({ entry }: { entry: RiskScoreEntry }) {
  const [open, setOpen] = useState(false)
  const pct = Math.round(entry.score * 100)
  const hasShap = Boolean(entry.shap_values && Object.keys(entry.shap_values).length > 0)
  const fileName = entry.file_path.split('/').slice(-2).join('/')

  return (
    <div className={`border rounded-xl overflow-hidden ${riskBg(entry.score)}`}>
      {/* Summary row */}
      <button
        onClick={() => hasShap && setOpen(o => !o)}
        className={`w-full px-4 py-3 flex items-center gap-3 ${hasShap ? 'cursor-pointer hover:bg-white/5' : 'cursor-default'}`}
      >
        {/* Risk icon */}
        <div className="shrink-0">
          {entry.anomaly_flag
            ? <AlertTriangle size={16} className="text-red-400" />
            : <ShieldCheck size={16} className="text-green-400" />}
        </div>

        {/* File path */}
        <span className="flex-1 text-xs font-mono text-slate-300 text-left truncate" title={entry.file_path}>
          {fileName}
        </span>

        {/* Score pill */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-20 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${entry.score > 0.7 ? 'bg-red-500' : entry.score > 0.4 ? 'bg-yellow-400' : 'bg-green-500'}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className={`text-sm font-bold w-10 text-right ${riskColor(entry.score)}`}>{pct}%</span>
        </div>

        {/* Expand toggle */}
        {hasShap && (
          open ? <ChevronDown size={14} className="text-slate-500 shrink-0" />
               : <ChevronRight size={14} className="text-slate-500 shrink-0" />
        )}
      </button>

      {/* SHAP explanation panel */}
      {open && hasShap && entry.shap_values && (
        <div className="px-4 pb-4 border-t border-slate-700/60 pt-3 space-y-3">
          {/* Plain-English sentence */}
          {entry.shap_sentence && (
            <p className="text-xs text-slate-400 italic">{entry.shap_sentence}</p>
          )}

          {/* All feature bars */}
          <div className="space-y-1.5">
            {Object.entries(entry.shap_values)
              .filter(([, v]) => Math.abs(v) > 0.001)
              .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
              .map(([feature, value]) => {
                const label = {
                  lines_changed:       'Large diff',
                  file_size_kb:        'Large file',
                  import_count:        'Many imports',
                  function_count:      'Many functions',
                  has_auth_code:       'Auth code',
                  has_db_code:         'DB operations',
                  test_coverage_delta: 'Coverage delta',
                }[feature] ?? feature
                return <ShapBar key={feature} label={label} value={value} />
              })}
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 pt-1">
            <span className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-3 h-1.5 bg-red-500 rounded-full inline-block" /> increases risk
            </span>
            <span className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-3 h-1.5 bg-green-500 rounded-full inline-block" /> reduces risk
            </span>
            {entry.shap_method && (
              <span className="text-xs text-slate-600 ml-auto">{entry.shap_method}</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main panel ─────────────────────────────────────────────────────────────

export default function RiskExplainPanel({ riskScores, maxShow = 10 }: Props) {
  const [showAll, setShowAll] = useState(false)

  const sorted = [...riskScores].sort((a, b) => b.score - a.score)
  const visible = showAll ? sorted : sorted.slice(0, maxShow)
  const anomalyCount = sorted.filter(r => r.anomaly_flag).length

  if (riskScores.length === 0) {
    return (
      <div className="text-slate-500 text-sm text-center py-8">
        No risk scores available. Run a v2 analysis to see SHAP explanations.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header KPIs */}
      <div className="flex items-center gap-4 text-xs text-slate-400 pb-1">
        <span>{sorted.length} files scored</span>
        {anomalyCount > 0 && (
          <span className="text-red-400 font-semibold">{anomalyCount} anomalies</span>
        )}
        <span className="ml-auto text-slate-600">
          Click a file to see SHAP feature attribution
        </span>
      </div>

      {/* File cards */}
      <div className="space-y-2">
        {visible.map(entry => (
          <FileRiskCard key={entry.file_path} entry={entry} />
        ))}
      </div>

      {/* Show more */}
      {sorted.length > maxShow && (
        <button
          onClick={() => setShowAll(v => !v)}
          className="w-full text-xs text-slate-500 hover:text-slate-300 py-2 transition-colors"
        >
          {showAll ? '▲ Show fewer' : `▼ Show ${sorted.length - maxShow} more files`}
        </button>
      )}
    </div>
  )
}
