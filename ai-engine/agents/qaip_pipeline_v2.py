"""
QAIP v2 LangGraph pipeline.

Improvements over v1:
  1. Parallel execution — score_risk and identify_gaps_v2 fan out from
     fetch_codebase simultaneously, then fan in via merge_risk_gaps.
  2. SSE streaming — every node emits node_start / node_done events via
     stream_bus so the React frontend can show live progress.
  3. PostgreSQL checkpointing — interrupted runs resume from the last
     completed node when re-invoked with the same thread_id (run_id).

Graph topology:
                    ┌─ score_risk ────────────┐
  fetch_codebase ───┤                         ├─ merge_risk_gaps ─ retrieve_context ─ …
                    └─ identify_gaps_v2 ───────┘
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Callable

from langgraph.graph import StateGraph, END

from agents.langgraph_agent import (
    AgentState,
    _TEST_PATTERNS,
    _has_test_file,
    fetch_codebase,
    score_risk,
    retrieve_context,
    generate_tests,
    detect_defects,
    explain_and_score,
    dispatch_results,
)
import stream_bus
from aimo_trace import aimo_trace

logger = logging.getLogger("testmind.pipeline_v2")


# ---------------------------------------------------------------------------
# Node streaming wrapper
# ---------------------------------------------------------------------------

def _wrap(fn: Callable, node_name: str) -> Callable:
    """Emit node_start / node_done SSE events around every node call."""
    def wrapper(state: AgentState) -> AgentState:
        run_id = state.get("run_id", "")
        stream_bus.push(run_id, {"event": "node_start", "node": node_name, "ts": time.time()})
        try:
            result = fn(state)
            stream_bus.push(run_id, {
                "event": "node_done",
                "node": node_name,
                "status": result.get("status", "ok"),
                "ts": time.time(),
            })
            return result
        except Exception as exc:
            stream_bus.push(run_id, {
                "event": "node_error",
                "node": node_name,
                "error": str(exc),
                "ts": time.time(),
            })
            raise
    wrapper.__name__ = fn.__name__
    return wrapper


def _instrument(fn: Callable, node_name: str) -> Callable:
    """Compose AIMO observability with QAIP's own SSE node streaming."""
    return aimo_trace(node_name, pipeline="QAIP")(_wrap(fn, node_name))


# ---------------------------------------------------------------------------
# New node: identify_gaps_v2  (parallel-safe — no dependency on risk_scores)
# ---------------------------------------------------------------------------

def identify_gaps_v2(state: AgentState) -> AgentState:
    """Identify coverage gaps using file heuristics only.

    Runs in parallel with score_risk; merge_risk_gaps enriches the priority
    field with the actual ML risk score once both branches join.
    """
    state["status"] = "IDENTIFYING_GAPS"
    logger.info("[%s] identify_gaps_v2 started", state["run_id"])

    try:
        file_list = state.get("file_list", [])
        all_paths = {f["path"] for f in file_list}
        gaps: list[dict] = []

        for f in file_list:
            path = f["path"]
            if _TEST_PATTERNS.search(path):
                continue

            has_test = _has_test_file(path, all_paths)
            if not has_test:
                content_len = len(f.get("content", ""))
                diff_lines = f.get("lines_changed", 0)
                # Heuristic priority: larger + recently changed files first
                heuristic_score = min(content_len / 5000, 0.8) + min(diff_lines / 200, 0.2)
                if heuristic_score > 0.05:
                    gaps.append({
                        "file_path": path,
                        "has_test": False,
                        "priority": round(heuristic_score, 3),
                        "risk_score": 0.0,  # placeholder; filled by merge_risk_gaps
                    })

        gaps.sort(key=lambda x: x["priority"], reverse=True)
        state["coverage_gaps"] = gaps[:10]
        logger.info("[%s] identify_gaps_v2: %d gaps (heuristic)", state["run_id"], len(gaps))

    except Exception as exc:
        logger.exception("[%s] identify_gaps_v2 failed: %s", state["run_id"], exc)
        state["error"] = f"identify_gaps_v2: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Fan-in node: merge_risk_gaps
# ---------------------------------------------------------------------------

def merge_risk_gaps(state: AgentState) -> AgentState:
    """Merge ML risk scores into coverage gaps after the parallel branches join."""
    state["status"] = "MERGING"
    logger.info("[%s] merge_risk_gaps: enriching %d gaps with %d risk scores",
                state["run_id"], len(state.get("coverage_gaps", [])),
                len(state.get("risk_scores", [])))

    risk_map = {r["file_path"]: r["score"] for r in state.get("risk_scores", [])}
    enriched: list[dict] = []

    for gap in state.get("coverage_gaps", []):
        ml_score = risk_map.get(gap["file_path"], gap["priority"])
        enriched.append({
            **gap,
            "risk_score": round(ml_score, 3),
            "priority": round((ml_score + gap["priority"]) / 2, 3),
        })

    enriched.sort(key=lambda x: x["priority"], reverse=True)
    state["coverage_gaps"] = enriched

    # Drop any gaps below the 0.3 ML threshold (mirrors v1 behaviour)
    state["coverage_gaps"] = [g for g in enriched if g["priority"] >= 0.15][:10]
    return state


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph_v2(checkpointer=None):
    """
    Build the v2 graph with parallel branches and SSE wrappers.

    Pass a LangGraph checkpointer to enable PostgreSQL resume.
    """
    g = StateGraph(AgentState)

    g.add_node("fetch_codebase",   _instrument(fetch_codebase,    "fetch_codebase"))
    g.add_node("score_risk",       _instrument(score_risk,        "score_risk"))
    g.add_node("identify_gaps",    _instrument(identify_gaps_v2,  "identify_gaps"))
    g.add_node("merge_risk_gaps",  _instrument(merge_risk_gaps,   "merge_risk_gaps"))
    g.add_node("retrieve_context", _instrument(retrieve_context,  "retrieve_context"))
    g.add_node("generate_tests",   _instrument(generate_tests,    "generate_tests"))
    g.add_node("detect_defects",   _instrument(detect_defects,    "detect_defects"))
    g.add_node("explain_and_score",_instrument(explain_and_score, "explain_and_score"))
    g.add_node("dispatch_results", _instrument(dispatch_results,  "dispatch_results"))

    g.set_entry_point("fetch_codebase")

    # Fan-out: both branches run in parallel
    g.add_edge("fetch_codebase", "score_risk")
    g.add_edge("fetch_codebase", "identify_gaps")

    # Fan-in: merge_risk_gaps waits for both branches
    g.add_edge("score_risk",     "merge_risk_gaps")
    g.add_edge("identify_gaps",  "merge_risk_gaps")

    # Sequential tail
    for src, dst in [
        ("merge_risk_gaps",    "retrieve_context"),
        ("retrieve_context",   "generate_tests"),
        ("generate_tests",     "detect_defects"),
        ("detect_defects",     "explain_and_score"),
        ("explain_and_score",  "dispatch_results"),
    ]:
        g.add_edge(src, dst)

    g.add_edge("dispatch_results", END)

    compile_kwargs: dict = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return g.compile(**compile_kwargs)


# ---------------------------------------------------------------------------
# Checkpointer factory (lazy, singleton)
# ---------------------------------------------------------------------------

_checkpointer = None


def get_checkpointer():
    """Return a PostgresSaver when DATABASE_URL is set, else None."""
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.info("DATABASE_URL not set — checkpointing disabled")
        return None

    try:
        from langgraph.checkpoint.postgres import PostgresSaver  # type: ignore
        saver = PostgresSaver.from_conn_string(db_url)
        saver.setup()   # create langgraph_checkpoint_* tables if absent
        _checkpointer = saver
        logger.info("PostgreSQL checkpointer ready")
    except Exception as exc:
        logger.warning("Could not init PostgresSaver (%s) — checkpointing disabled", exc)
        _checkpointer = None

    return _checkpointer


# Pipeline node order for the UI (used by the frontend to render the DAG)
PIPELINE_NODES = [
    {"id": "fetch_codebase",    "label": "Fetch Codebase",    "parallel": False},
    {"id": "score_risk",        "label": "Score Risk",         "parallel": True,  "branch": "A"},
    {"id": "identify_gaps",     "label": "Identify Gaps",      "parallel": True,  "branch": "B"},
    {"id": "merge_risk_gaps",   "label": "Merge & Rank",       "parallel": False},
    {"id": "retrieve_context",  "label": "RAG Context",        "parallel": False},
    {"id": "generate_tests",    "label": "Generate Tests",     "parallel": False},
    {"id": "detect_defects",    "label": "Detect Defects",     "parallel": False},
    {"id": "explain_and_score", "label": "Explain & Score",    "parallel": False},
    {"id": "dispatch_results",  "label": "Dispatch Results",   "parallel": False},
]
