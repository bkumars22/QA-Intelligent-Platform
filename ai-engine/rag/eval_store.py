"""
PostgreSQL storage for RAGAS evaluation results.

Table: rag_eval_results — one row per ask() call that was evaluated.

Public API:
  save_eval(project_id, question, answer, metrics, is_grounded) → int|None
  get_recent_evals(project_id, limit=20) → list[dict]
  get_aggregate_stats(project_id, days=30) → dict
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("rag.eval_store")

_DDL = """
CREATE TABLE IF NOT EXISTS rag_eval_results (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          VARCHAR(255),
    question            TEXT,
    answer              TEXT,
    faithfulness        FLOAT,
    answer_relevancy    FLOAT,
    context_precision   FLOAT,
    context_recall      FLOAT,
    overall             FLOAT,
    context_count       INT,
    is_grounded         BOOLEAN,
    eval_duration_ms    INT,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_eval_project_ts_idx
    ON rag_eval_results (project_id, created_at DESC);
"""


def _conn():
    from rag.vector_store import _conn as vs_conn
    return vs_conn()


def ensure_schema() -> bool:
    try:
        conn = _conn()
        with conn.cursor() as cur:
            cur.execute(_DDL)
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.warning("eval_store schema setup failed: %s", exc)
        return False


def save_eval(
    project_id:   int | str,
    question:     str,
    answer:       str,
    metrics:      dict[str, Any],
    is_grounded:  bool = True,
) -> int | None:
    """Persist one RAGAS evaluation result. Returns row id or None on failure."""
    try:
        conn = _conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO rag_eval_results
                  (project_id, question, answer, faithfulness, answer_relevancy,
                   context_precision, context_recall, overall, context_count,
                   is_grounded, eval_duration_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    str(project_id),
                    question[:1000],
                    answer[:2000],
                    metrics.get("faithfulness"),
                    metrics.get("answer_relevancy"),
                    metrics.get("context_precision"),
                    metrics.get("context_recall") if metrics.get("context_recall", -1) >= 0 else None,
                    metrics.get("overall"),
                    metrics.get("context_count", 0),
                    is_grounded,
                    metrics.get("eval_duration_ms", 0),
                ),
            )
            row = cur.fetchone()
        conn.commit()
        conn.close()
        return row[0] if row else None
    except Exception as exc:
        logger.warning("eval_store save_eval failed: %s", exc)
        return None


def get_recent_evals(project_id: int | str, limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent eval rows for a project."""
    try:
        conn = _conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, question, answer, faithfulness, answer_relevancy,
                       context_precision, context_recall, overall,
                       context_count, is_grounded, eval_duration_ms, created_at
                FROM rag_eval_results
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (str(project_id), limit),
            )
            rows = cur.fetchall()
        conn.close()
        cols = [
            "id","question","answer","faithfulness","answer_relevancy",
            "context_precision","context_recall","overall",
            "context_count","is_grounded","eval_duration_ms","created_at",
        ]
        results = []
        for row in rows:
            d = dict(zip(cols, row))
            d["created_at"] = d["created_at"].isoformat() if d["created_at"] else None
            results.append(d)
        return results
    except Exception as exc:
        logger.warning("eval_store get_recent_evals failed: %s", exc)
        return []


def get_aggregate_stats(project_id: int | str, days: int = 30) -> dict[str, Any]:
    """Return mean/min/max for each metric over the last N days."""
    try:
        conn = _conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)                         AS total_evals,
                    AVG(faithfulness)                AS avg_faithfulness,
                    AVG(answer_relevancy)            AS avg_answer_relevancy,
                    AVG(context_precision)           AS avg_context_precision,
                    AVG(context_recall)              AS avg_context_recall,
                    AVG(overall)                     AS avg_overall,
                    MIN(overall)                     AS min_overall,
                    MAX(overall)                     AS max_overall,
                    AVG(context_count)               AS avg_context_count,
                    SUM(CASE WHEN is_grounded THEN 1 ELSE 0 END) AS grounded_count
                FROM rag_eval_results
                WHERE project_id = %s
                  AND created_at >= NOW() - INTERVAL '%s days'
                """,
                (str(project_id), days),
            )
            row = cur.fetchone()
        conn.close()
        if not row:
            return {}
        def _r(v):
            return round(float(v), 4) if v is not None else None
        return {
            "total_evals":           int(row[0]),
            "avg_faithfulness":      _r(row[1]),
            "avg_answer_relevancy":  _r(row[2]),
            "avg_context_precision": _r(row[3]),
            "avg_context_recall":    _r(row[4]),
            "avg_overall":           _r(row[5]),
            "min_overall":           _r(row[6]),
            "max_overall":           _r(row[7]),
            "avg_context_count":     _r(row[8]),
            "grounded_count":        int(row[9]) if row[9] else 0,
            "days_window":           days,
        }
    except Exception as exc:
        logger.warning("eval_store get_aggregate_stats failed: %s", exc)
        return {}
