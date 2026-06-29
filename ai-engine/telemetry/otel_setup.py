"""
OpenTelemetry setup for QAIP AI Engine.

Tracing:
  - InMemorySpanExporter (always) — feeds the /telemetry/traces UI endpoint
  - OTLP gRPC exporter (when OTEL_EXPORTER_OTLP_ENDPOINT is set) — for Jaeger / Tempo
  - FastAPI auto-instrumentation via opentelemetry-instrumentation-fastapi

Metrics (lightweight in-process counters):
  - rag.requests.total, rag.latency_ms, rag.hops
  - guardrails.checks.total, guardrails.blocked.total
  - memory.operations.total
  - ragas.faithfulness, ragas.answer_relevancy (running averages)
  - analyze.requests.total

Public API:
  get_tracer(name)          → opentelemetry.trace.Tracer
  get_recent_traces(limit)  → list[dict] for /telemetry/traces
  record_rag(...)           → update rag metrics
  record_guardrail(...)     → update guardrail metrics
  record_memory_op(...)     → update memory metrics
  record_ragas(...)         → update ragas running averages
  get_metrics_snapshot()    → dict of current metric values
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict, deque
from typing import Any

logger = logging.getLogger("qaip.telemetry")

# ── OpenTelemetry imports (graceful degradation if not installed) ─────────────
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.trace import SpanKind, StatusCode
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    logger.warning("[otel] opentelemetry-sdk not installed — tracing disabled (install opentelemetry-sdk)")

_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
_FASTAPI_INSTRUMENT = os.getenv("OTEL_FASTAPI_INSTRUMENT", "true").lower() == "true"

# ── Tracer setup ──────────────────────────────────────────────────────────────
_in_memory_exporter: Any = None
_tracer_provider:    Any = None

if _OTEL_AVAILABLE:
    _resource = Resource.create({
        "service.name":             os.getenv("OTEL_SERVICE_NAME", "qaip-ai-engine"),
        "service.version":          "2.0.0",
        "deployment.environment":   os.getenv("ENVIRONMENT", "development"),
    })
    _tracer_provider    = TracerProvider(resource=_resource)
    _in_memory_exporter = InMemorySpanExporter()
    _tracer_provider.add_span_processor(SimpleSpanProcessor(_in_memory_exporter))

    if _OTLP_ENDPOINT:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            otlp = OTLPSpanExporter(endpoint=_OTLP_ENDPOINT, insecure=True)
            _tracer_provider.add_span_processor(BatchSpanProcessor(otlp))
            logger.info("[otel] OTLP exporter → %s", _OTLP_ENDPOINT)
        except Exception as exc:
            logger.warning("[otel] OTLP exporter failed (%s) — in-memory only", exc)

    trace.set_tracer_provider(_tracer_provider)
    logger.info("[otel] TracerProvider initialised (in-memory + %s)", "OTLP" if _OTLP_ENDPOINT else "console-only")


def get_tracer(name: str = "qaip"):
    """Return an OTel tracer. Returns a no-op tracer when OTel is not installed."""
    if _OTEL_AVAILABLE:
        return trace.get_tracer(name)
    return _NoopTracer()


def instrument_fastapi(app):
    """Wire OTel FastAPI auto-instrumentation. Call once after app is created."""
    if not _OTEL_AVAILABLE or not _FASTAPI_INSTRUMENT:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app, tracer_provider=_tracer_provider)
        logger.info("[otel] FastAPI auto-instrumented")
    except ImportError:
        logger.warning("[otel] opentelemetry-instrumentation-fastapi not installed — skipping")
    except Exception as exc:
        logger.warning("[otel] FastAPI instrumentation failed: %s", exc)


# ── Trace collection for /telemetry/traces ────────────────────────────────────

_MAX_SPANS = 2000   # cap memory usage

def get_recent_traces(limit: int = 20) -> list[dict]:
    """
    Group finished spans by trace_id and return the most recent `limit` traces.
    Each trace: {trace_id, root_op, start_time_iso, duration_ms, status, span_count, spans[]}.
    """
    if not _OTEL_AVAILABLE or _in_memory_exporter is None:
        return []

    all_spans = _in_memory_exporter.get_finished_spans()

    # Trim oldest spans to keep memory bounded
    if len(all_spans) > _MAX_SPANS:
        _in_memory_exporter.clear()
        return []

    # Group by trace_id
    by_trace: dict[int, list] = defaultdict(list)
    for span in all_spans:
        by_trace[span.context.trace_id].append(span)

    traces = []
    for trace_id, spans in by_trace.items():
        # Sort spans by start time
        spans_sorted = sorted(spans, key=lambda s: s.start_time)
        root = next((s for s in spans_sorted if s.parent is None), spans_sorted[0])
        trace_start   = root.start_time   # nanoseconds
        trace_end     = max(s.end_time for s in spans_sorted)
        duration_ns   = trace_end - trace_start
        duration_ms   = round(duration_ns / 1_000_000, 2)
        trace_id_hex  = format(trace_id, "032x")
        import datetime
        start_iso = datetime.datetime.utcfromtimestamp(trace_start / 1e9).isoformat() + "Z"

        # Build per-span dicts
        span_dicts = []
        for s in spans_sorted:
            offset_ms = round((s.start_time - trace_start) / 1_000_000, 2)
            dur_ms    = round((s.end_time   - s.start_time)  / 1_000_000, 2)
            parent_id = format(s.parent.span_id, "016x") if s.parent else None
            status    = s.status.status_code.name if hasattr(s.status, "status_code") else "OK"
            attrs     = dict(s.attributes) if s.attributes else {}
            span_dicts.append({
                "name":           s.name,
                "span_id":        format(s.context.span_id, "016x"),
                "parent_span_id": parent_id,
                "start_offset_ms": offset_ms,
                "duration_ms":    dur_ms,
                "status":         status,
                "attributes":     attrs,
            })

        root_status = span_dicts[0]["status"] if span_dicts else "OK"
        traces.append({
            "trace_id":       trace_id_hex[:16],
            "root_op":        root.name,
            "start_time_iso": start_iso,
            "duration_ms":    duration_ms,
            "status":         root_status,
            "span_count":     len(span_dicts),
            "spans":          span_dicts,
        })

    # Sort by start_time descending, return last `limit`
    traces.sort(key=lambda t: t["start_time_iso"], reverse=True)
    return traces[:limit]


# ── In-process metrics ────────────────────────────────────────────────────────
_metrics_lock = threading.Lock()
_metrics: dict[str, Any] = {
    "rag_requests_total":    0,
    "rag_blocked_total":     0,
    "rag_latency_ms_sum":    0.0,
    "rag_latency_ms_count":  0,
    "rag_hops_sum":          0,
    "rag_hops_count":        0,
    "guardrails_checks":     0,
    "guardrails_blocked":    0,
    "memory_ops":            0,
    "ragas_overall_sum":     0.0,
    "ragas_overall_count":   0,
    "ragas_faithfulness_sum": 0.0,
    "ragas_ar_sum":          0.0,   # answer relevancy
    "analyze_requests":      0,
}
_recent_ragas: deque = deque(maxlen=50)   # last 50 overall scores


def record_rag(latency_ms: float, hops: int = 0, blocked: bool = False) -> None:
    with _metrics_lock:
        _metrics["rag_requests_total"] += 1
        _metrics["rag_latency_ms_sum"] += latency_ms
        _metrics["rag_latency_ms_count"] += 1
        _metrics["rag_hops_sum"] += hops
        _metrics["rag_hops_count"] += 1
        if blocked:
            _metrics["rag_blocked_total"] += 1


def record_guardrail(blocked: bool) -> None:
    with _metrics_lock:
        _metrics["guardrails_checks"] += 1
        if blocked:
            _metrics["guardrails_blocked"] += 1


def record_memory_op() -> None:
    with _metrics_lock:
        _metrics["memory_ops"] += 1


def record_ragas(scores: dict[str, float]) -> None:
    overall = scores.get("overall", -1)
    if overall < 0:
        return
    with _metrics_lock:
        _metrics["ragas_overall_sum"]     += overall
        _metrics["ragas_overall_count"]   += 1
        _metrics["ragas_faithfulness_sum"] += scores.get("faithfulness", 0)
        _metrics["ragas_ar_sum"]          += scores.get("answer_relevancy", 0)
        _recent_ragas.append(round(overall, 3))


def record_analyze() -> None:
    with _metrics_lock:
        _metrics["analyze_requests"] += 1


def get_metrics_snapshot() -> dict[str, Any]:
    with _metrics_lock:
        m = dict(_metrics)
    n_rag  = m["rag_latency_ms_count"]
    n_rag_h = m["rag_hops_count"]
    n_ragas = m["ragas_overall_count"]
    return {
        "rag": {
            "requests_total":     m["rag_requests_total"],
            "blocked_total":      m["rag_blocked_total"],
            "block_rate_pct":     round(m["rag_blocked_total"] / m["rag_requests_total"] * 100, 1) if m["rag_requests_total"] else 0,
            "avg_latency_ms":     round(m["rag_latency_ms_sum"] / n_rag, 1) if n_rag else 0,
            "avg_hops":           round(m["rag_hops_sum"] / n_rag_h, 2) if n_rag_h else 0,
        },
        "guardrails": {
            "checks_total":   m["guardrails_checks"],
            "blocked_total":  m["guardrails_blocked"],
            "block_rate_pct": round(m["guardrails_blocked"] / m["guardrails_checks"] * 100, 1) if m["guardrails_checks"] else 0,
        },
        "memory": {
            "operations_total": m["memory_ops"],
        },
        "ragas": {
            "evals_total":          n_ragas,
            "avg_overall":          round(m["ragas_overall_sum"] / n_ragas, 3) if n_ragas else None,
            "avg_faithfulness":     round(m["ragas_faithfulness_sum"] / n_ragas, 3) if n_ragas else None,
            "avg_answer_relevancy": round(m["ragas_ar_sum"] / n_ragas, 3) if n_ragas else None,
            "recent_50_scores":     list(_recent_ragas),
        },
        "analyze": {
            "requests_total": m["analyze_requests"],
        },
        "otel_backend":    "in_memory" + ("+otlp" if _OTLP_ENDPOINT else ""),
        "otel_available":  _OTEL_AVAILABLE,
    }


# ── No-op tracer for when OTel is not installed ───────────────────────────────
class _NoopSpan:
    def set_attribute(self, *_): pass
    def record_exception(self, *_): pass
    def set_status(self, *_): pass
    def __enter__(self): return self
    def __exit__(self, *_): pass


class _NoopTracer:
    def start_as_current_span(self, *_, **__): return _NoopSpan()
    def start_span(self, *_, **__): return _NoopSpan()
