"""QAIP RAG ingest pipeline.

Three ingestion paths:
  1. ingest_test_case   — store a generated test case for a file
  2. ingest_defect      — store a defect (title + description + fix)
  3. ingest_run_result  — store a complete agent run summary
  4. ingest_jira_story  — store a Jira story so future test gen understands intent

Each document is embedded and stored in pgvector.
On the next run, retrieve_context() pulls the top-k most relevant past
test cases/defects for each coverage-gap file, feeding them to the LLM
as few-shot examples. Tests improve sprint-over-sprint.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .embedder import embed
from .vector_store import upsert, ensure_schema

logger = logging.getLogger("rag.ingest")


def _safe_upsert(content: str, source_type: str, source_id: str, project_id: str, metadata: dict) -> bool:
    try:
        embedding = embed(content)
        result = upsert(
            content=content,
            embedding=embedding,
            source_type=source_type,
            source_id=source_id,
            project_id=str(project_id),
            metadata=metadata,
        )
        return result is not None
    except Exception as exc:
        logger.warning("ingest %s/%s failed: %s", source_type, source_id, exc)
        return False


def ingest_test_case(
    project_id: int | str,
    file_path: str,
    test_code: str,
    language: str = "typescript",
    sprint: int | None = None,
) -> bool:
    """Store a generated test case. Key text = file_path + first 2000 chars of test_code."""
    if not test_code or not file_path:
        return False

    content = f"File: {file_path}\nLanguage: {language}\n\nTest code:\n{test_code[:2000]}"
    source_id = f"tc:{project_id}:{file_path}"
    metadata: dict[str, Any] = {
        "file_path": file_path,
        "language": language,
        "project_id": str(project_id),
    }
    if sprint is not None:
        metadata["sprint"] = sprint

    return _safe_upsert(content, "test_case", source_id, str(project_id), metadata)


def ingest_defect(
    project_id: int | str,
    title: str,
    severity: str,
    description: str,
    file_path: str = "",
    fix_summary: str = "",
) -> bool:
    """Store a defect record for future few-shot defect detection."""
    content_parts = [
        f"Defect: {title}",
        f"Severity: {severity}",
        f"Description: {description}",
    ]
    if file_path:
        content_parts.insert(0, f"File: {file_path}")
    if fix_summary:
        content_parts.append(f"Fix: {fix_summary}")

    content = "\n".join(content_parts)
    source_id = f"defect:{project_id}:{title[:60]}"
    metadata: dict[str, Any] = {
        "title": title,
        "severity": severity,
        "file_path": file_path,
        "project_id": str(project_id),
    }
    return _safe_upsert(content, "defect", source_id, str(project_id), metadata)


def ingest_run_result(
    project_id: int | str,
    run_id: str,
    repo_url: str,
    commit_sha: str,
    risk_scores: list[dict],
    coverage_gaps: list[dict],
    generated_tests: list[dict],
    defects: list[dict],
) -> int:
    """Store a complete run summary. Returns number of documents ingested."""
    ingested = 0

    # 1. Ingest each generated test case
    for tc in generated_tests:
        ok = ingest_test_case(
            project_id=project_id,
            file_path=tc.get("file_path", ""),
            test_code=tc.get("test_code", ""),
            language=tc.get("language", "typescript"),
        )
        if ok:
            ingested += 1

    # 2. Ingest each defect
    for d in defects:
        ok = ingest_defect(
            project_id=project_id,
            title=d.get("title", ""),
            severity=d.get("severity", "P2"),
            description=d.get("description", ""),
            file_path=d.get("file_path", ""),
            fix_summary=d.get("ai_explanation", "")[:500] if d.get("ai_explanation") else "",
        )
        if ok:
            ingested += 1

    # 3. Ingest the run-level summary
    top_risk = sorted(risk_scores, key=lambda r: r.get("score", 0), reverse=True)[:5]
    run_summary = (
        f"Run ID: {run_id}\n"
        f"Repo: {repo_url}\n"
        f"Commit: {commit_sha[:8]}\n"
        f"Coverage gaps: {len(coverage_gaps)}\n"
        f"Tests generated: {len(generated_tests)}\n"
        f"Defects found: {len(defects)}\n"
        f"Top risk files: {', '.join(r.get('file_path','') for r in top_risk)}"
    )
    ok = _safe_upsert(
        content=run_summary,
        source_type="run_result",
        source_id=f"run:{run_id}",
        project_id=str(project_id),
        metadata={"run_id": run_id, "commit_sha": commit_sha[:8], "project_id": str(project_id)},
    )
    if ok:
        ingested += 1

    logger.info("Ingested %d documents for run %s (project %s)", ingested, run_id, project_id)
    return ingested


def ingest_jira_story(
    project_id: int | str,
    story_key: str,
    title: str,
    description: str,
    acceptance_criteria: str = "",
    story_type: str = "Story",
) -> bool:
    """Store a Jira story so test generation understands the business intent."""
    content_parts = [
        f"Jira {story_type}: {story_key}",
        f"Title: {title}",
        f"Description: {description[:1000]}",
    ]
    if acceptance_criteria:
        content_parts.append(f"Acceptance criteria:\n{acceptance_criteria[:500]}")

    content = "\n".join(content_parts)
    source_id = f"jira:{project_id}:{story_key}"
    metadata: dict[str, Any] = {
        "story_key": story_key,
        "story_type": story_type,
        "project_id": str(project_id),
    }
    return _safe_upsert(content, "jira_story", source_id, str(project_id), metadata)
