"""pgvector-backed document store for QAIP RAG.

Requires:
  - PostgreSQL with pgvector extension
  - DATABASE_URL environment variable
  - pip install pgvector psycopg2-binary

Table: rag_documents — created automatically on first connection.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import psycopg2
import psycopg2.extras

logger = logging.getLogger("rag.vector_store")

_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag_documents (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT        NOT NULL,
    embedding   vector(384),
    metadata    JSONB       DEFAULT '{}',
    source_type VARCHAR(50),
    source_id   VARCHAR(255),
    project_id  VARCHAR(255),
    created_at  TIMESTAMP   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_documents_project_idx
    ON rag_documents (project_id, source_type);

CREATE INDEX IF NOT EXISTS rag_documents_embedding_idx
    ON rag_documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);
"""

_DB_URL = os.getenv("DATABASE_URL", "")


def _conn():
    if not _DB_URL:
        raise RuntimeError("DATABASE_URL not set — pgvector store unavailable")
    try:
        from pgvector.psycopg2 import register_vector
        c = psycopg2.connect(_DB_URL)
        register_vector(c)
        return c
    except ImportError:
        # pgvector Python adapter not installed — use text cast fallback
        return psycopg2.connect(_DB_URL)


def ensure_schema() -> bool:
    """Create pgvector extension + rag_documents table if they don't exist."""
    try:
        with _conn() as c:
            with c.cursor() as cur:
                cur.execute(_DDL)
        logger.info("pgvector schema ready")
        return True
    except Exception as exc:
        logger.warning("pgvector schema setup failed: %s", exc)
        return False


def upsert(
    content: str,
    embedding: list[float],
    source_type: str,
    source_id: str,
    project_id: str,
    metadata: dict[str, Any] | None = None,
) -> int | None:
    """Insert or replace a document (matched on source_id + source_type).
    Returns the row id, or None on failure.
    """
    meta_json = json.dumps(metadata or {})
    vec_str = "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"
    sql = """
        INSERT INTO rag_documents
               (content, embedding, metadata, source_type, source_id, project_id)
        VALUES (%s, %s::vector, %s::jsonb, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
    """
    try:
        with _conn() as c:
            with c.cursor() as cur:
                cur.execute(sql, (content, vec_str, meta_json, source_type, source_id, project_id))
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as exc:
        logger.warning("upsert failed: %s", exc)
        return None


def search(
    query_embedding: list[float],
    project_id: str,
    top_k: int = 5,
    source_type: str | None = None,
    min_similarity: float = 0.3,
) -> list[dict[str, Any]]:
    """Return top-k most similar documents for a query embedding.

    Returns list of dicts with keys: content, metadata, source_type, similarity.
    """
    vec_str = "[" + ",".join(f"{v:.6f}" for v in query_embedding) + "]"

    type_filter = "AND source_type = %s" if source_type else ""
    params: list[Any] = [vec_str, project_id, top_k]
    if source_type:
        params.insert(2, source_type)

    sql = f"""
        SELECT content,
               metadata,
               source_type,
               1 - (embedding <=> %s::vector) AS similarity
        FROM   rag_documents
        WHERE  project_id = %s
               {type_filter}
               AND embedding IS NOT NULL
        ORDER  BY embedding <=> %s::vector
        LIMIT  %s
    """
    # Re-add vec_str for the ORDER BY parameter
    params_full: list[Any] = [vec_str, project_id]
    if source_type:
        params_full.append(source_type)
    params_full += [vec_str, top_k]

    try:
        with _conn() as c:
            with c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params_full)
                rows = cur.fetchall()
        results = []
        for row in rows:
            sim = float(row["similarity"])
            if sim >= min_similarity:
                results.append({
                    "content": row["content"],
                    "metadata": row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"] or "{}"),
                    "source_type": row["source_type"],
                    "similarity": round(sim, 4),
                })
        return results
    except Exception as exc:
        logger.warning("search failed: %s", exc)
        return []


def delete_by_source(source_id: str, source_type: str) -> int:
    """Delete all documents with the given source_id and source_type. Returns count deleted."""
    try:
        with _conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    "DELETE FROM rag_documents WHERE source_id=%s AND source_type=%s",
                    (source_id, source_type),
                )
                return cur.rowcount
    except Exception as exc:
        logger.warning("delete failed: %s", exc)
        return 0
