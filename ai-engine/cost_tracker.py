"""
CostTracker — Level 4 AI Architect Component
Logs every AI call with token usage, cost, model, task type, and project.
Provides a cost dashboard API with savings vs baseline computation.

Storage: in-memory (production would use PostgreSQL with a cost_events table)
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Any

logger = logging.getLogger("qaip.cost_tracker")

# ── Cost per model (USD per 1M tokens) ───────────────────────────────────────

MODEL_COSTS: dict[str, dict[str, float]] = {
    "llama-3.1-8b-instant":           {"input": 0.05,  "output": 0.08},
    "llama-3.3-70b-versatile":        {"input": 0.59,  "output": 0.79},
    "llama-3.2-90b-vision-preview":   {"input": 0.90,  "output": 0.90},
    "claude-sonnet-4-6":              {"input": 3.00,  "output": 15.00},
    "claude-opus-4-8":                {"input": 15.00, "output": 75.00},
}

BASELINE_MODEL = "llama-3.3-70b-versatile"  # "always-heavy" baseline for savings %


# ── Event dataclass ───────────────────────────────────────────────────────────

@dataclass
class CostEvent:
    timestamp:        float
    project:          str
    task_type:        str
    model_id:         str
    prompt_tokens:    int
    completion_tokens: int
    cost_usd:         float
    baseline_cost_usd: float
    saved_usd:        float
    latency_ms:       int


# ── In-memory store ───────────────────────────────────────────────────────────

_events: list[CostEvent] = []


def _compute_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = MODEL_COSTS.get(model_id, MODEL_COSTS[BASELINE_MODEL])
    return (
        prompt_tokens     / 1_000_000 * rates["input"] +
        completion_tokens / 1_000_000 * rates["output"]
    )


# ── Public API ────────────────────────────────────────────────────────────────

def record(
    project:           str,
    task_type:         str,
    model_id:          str,
    prompt_tokens:     int,
    completion_tokens: int,
    latency_ms:        int = 0,
) -> CostEvent:
    """Record one AI call and return the event."""
    cost          = _compute_cost(model_id, prompt_tokens, completion_tokens)
    baseline_cost = _compute_cost(BASELINE_MODEL, prompt_tokens, completion_tokens)
    saved         = max(0.0, baseline_cost - cost)

    evt = CostEvent(
        timestamp=time.time(),
        project=project,
        task_type=task_type,
        model_id=model_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost,
        baseline_cost_usd=baseline_cost,
        saved_usd=saved,
        latency_ms=latency_ms,
    )
    _events.append(evt)

    logger.info(
        "[%s/%s] model=%s tokens=%d+%d cost=$%.5f saved=$%.5f",
        project, task_type, model_id,
        prompt_tokens, completion_tokens,
        cost, saved,
    )
    return evt


def dashboard(project: str | None = None) -> dict[str, Any]:
    """
    Return a cost dashboard payload.
    If project is given, filter to that project only.
    """
    evts = [e for e in _events if project is None or e.project == project]
    if not evts:
        return {
            "total_calls": 0,
            "total_cost_usd": 0.0,
            "total_saved_usd": 0.0,
            "savings_pct": 0.0,
            "by_project": {},
            "by_model": {},
            "by_task": {},
            "recent_events": [],
        }

    total_cost     = sum(e.cost_usd          for e in evts)
    total_baseline = sum(e.baseline_cost_usd for e in evts)
    total_saved    = sum(e.saved_usd         for e in evts)
    savings_pct    = (total_saved / total_baseline * 100) if total_baseline > 0 else 0.0

    # Aggregate by project
    by_project: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0, "saved_usd": 0.0})
    for e in evts:
        by_project[e.project]["calls"]     += 1
        by_project[e.project]["cost_usd"]  += e.cost_usd
        by_project[e.project]["saved_usd"] += e.saved_usd

    # Aggregate by model
    by_model: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0})
    for e in evts:
        by_model[e.model_id]["calls"]    += 1
        by_model[e.model_id]["cost_usd"] += e.cost_usd

    # Aggregate by task
    by_task: dict[str, dict] = defaultdict(lambda: {"calls": 0, "cost_usd": 0.0})
    for e in evts:
        by_task[e.task_type]["calls"]    += 1
        by_task[e.task_type]["cost_usd"] += e.cost_usd

    # Recent 20 events
    recent = [
        {
            "timestamp": e.timestamp,
            "project":   e.project,
            "task":      e.task_type,
            "model":     e.model_id,
            "tokens":    e.prompt_tokens + e.completion_tokens,
            "cost_usd":  round(e.cost_usd, 6),
            "saved_usd": round(e.saved_usd, 6),
            "latency_ms": e.latency_ms,
        }
        for e in reversed(evts[-20:])
    ]

    return {
        "total_calls":     len(evts),
        "total_cost_usd":  round(total_cost, 6),
        "total_saved_usd": round(total_saved, 6),
        "savings_pct":     round(savings_pct, 1),
        "baseline_model":  BASELINE_MODEL,
        "by_project":      {k: {kk: round(vv, 6) if isinstance(vv, float) else vv
                                for kk, vv in v.items()} for k, v in by_project.items()},
        "by_model":        {k: {kk: round(vv, 6) if isinstance(vv, float) else vv
                                for kk, vv in v.items()} for k, v in by_model.items()},
        "by_task":         {k: {kk: round(vv, 6) if isinstance(vv, float) else vv
                                for kk, vv in v.items()} for k, v in by_task.items()},
        "recent_events":   recent,
    }


def reset():
    """Clear all events (for testing)."""
    _events.clear()
