"""
TestMind — 7-node LangGraph agent.

Nodes (in order):
  1. fetch_codebase     — pull changed files from GitHub
  2. score_risk         — IsolationForest anomaly & risk scoring
  3. identify_gaps      — find files with no corresponding test
  4. generate_tests     — LLM-generated Playwright TS tests
  5. detect_defects     — static + heuristic defect detection
  6. explain_and_score  — LLM explanations with consistency scoring
  7. dispatch_results   — save report, Jira, Slack, backend callback
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from typing import TypedDict

import httpx
import numpy as np
import requests
from github import Github, GithubException
from groq import Groq
from langgraph.graph import END, StateGraph
from sklearn.ensemble import IsolationForest

from langsmith_utils import trace_node
from risk_explainer import explain as shap_explain
import cost_tracker

logger = logging.getLogger("testmind.agent")

# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    run_id: str
    project_id: int
    repo_url: str
    github_token: str
    commit_sha: str
    file_list: list[dict]          # [{path, content, diff, lines_changed}]
    risk_scores: list[dict]        # [{file_path, score, anomaly_flag}]
    coverage_gaps: list[dict]      # [{file_path, has_test, priority}]
    rag_context: list[dict]        # [{file_path, examples: str}] — injected by retrieve_context
    generated_tests: list[dict]    # [{file_path, test_code, language}]
    defects: list[dict]            # [{title, severity, description, stack_trace}]
    explained_defects: list[dict]  # defects + ai_explanation + consistency_score
    generated_fixes: list[dict]    # [{file_path, defect_title, severity, fix_diff}] — CodegenerateAgent output
    pr_results: list[dict]         # [{file_path, defect_title, branch, status, pr_url, tests_passed, why}] — audit trail
    dispatch_results: dict
    error: str
    status: str
    user_id: str                  # AIMO span attribution — set to str(project_id)
    prompt_tokens: int            # accumulated across all Groq calls in this run
    completion_tokens: int
    cost_usd: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _groq_client() -> Groq:
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def _capture_usage(state: AgentState, model: str, resp, task_type: str) -> None:
    """Accumulate token usage + cost onto state (read by @aimo_trace) and log
    to QAIP's own cost dashboard. These LangGraph nodes call Groq directly
    and previously recorded no cost data anywhere."""
    usage = getattr(resp, "usage", None)
    prompt_tokens     = usage.prompt_tokens     if usage else 0
    completion_tokens = usage.completion_tokens if usage else 0
    evt = cost_tracker.record(
        project="QAIP", task_type=task_type, model_id=model,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
    )
    state["prompt_tokens"]     = state.get("prompt_tokens", 0) + prompt_tokens
    state["completion_tokens"] = state.get("completion_tokens", 0) + completion_tokens
    state["cost_usd"]          = state.get("cost_usd", 0.0) + evt.cost_usd


def _repo_name_from_url(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    return "/".join(parts[-2:])


def _retry(fn, retries: int = 3, delay: float = 2.0):
    """Call *fn* up to *retries* times, sleeping *delay* seconds between tries."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            logger.warning("Attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Node 1 — fetch_codebase
# ---------------------------------------------------------------------------
def fetch_codebase(state: AgentState) -> AgentState:
    state["status"] = "FETCHING_CODE"
    logger.info("[%s] fetch_codebase started", state["run_id"])

    try:
        def _fetch():
            gh = Github(state["github_token"])
            repo_name = _repo_name_from_url(state["repo_url"])
            repo = gh.get_repo(repo_name)

            commit = repo.get_commit(state["commit_sha"])
            parent_sha = commit.parents[0].sha if commit.parents else None

            file_list: list[dict] = []
            for f in commit.files:
                path: str = f.filename
                diff: str = f.patch or ""
                lines_changed: int = (f.additions or 0) + (f.deletions or 0)

                # Read current file content (skip deleted files)
                content = ""
                if f.status != "removed":
                    try:
                        file_obj = repo.get_contents(path, ref=state["commit_sha"])
                        if isinstance(file_obj, list):
                            file_obj = file_obj[0]
                        raw = file_obj.decoded_content
                        content = raw.decode("utf-8", errors="replace")
                    except GithubException as ge:
                        logger.warning("Could not fetch content for %s: %s", path, ge)

                file_list.append(
                    {
                        "path": path,
                        "content": content,
                        "diff": diff,
                        "lines_changed": lines_changed,
                    }
                )

            return file_list

        state["file_list"] = _retry(_fetch, retries=3, delay=3.0)
        logger.info("[%s] fetch_codebase fetched %d files", state["run_id"], len(state["file_list"]))

    except Exception as exc:
        logger.exception("[%s] fetch_codebase failed: %s", state["run_id"], exc)
        state["error"] = f"fetch_codebase: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Node 2 — score_risk
# ---------------------------------------------------------------------------
def _extract_features(file_info: dict) -> list[float]:
    """Return a fixed-length feature vector for one file."""
    content: str = file_info.get("content", "")
    lines = content.splitlines()

    lines_changed = float(file_info.get("lines_changed", 0))
    file_size_kb = len(content.encode("utf-8")) / 1024.0
    import_count = float(
        sum(
            1 for ln in lines
            if re.match(r"^\s*(import |from .+ import )", ln) or re.search(r"\brequire\(", ln)
        )
    )
    function_count = float(
        len(re.findall(r"\bdef \w+|\bfunction \w+|=>\s*\{|\basync function\b", content))
    )
    content_lower = content.lower()
    has_auth_code = float(
        any(kw in content_lower for kw in ["auth", "login", "password", "token", "jwt", "oauth"])
    )
    has_db_code = float(
        any(
            kw in content
            for kw in ["SELECT", "INSERT", "UPDATE", "DELETE", "repository", ".save(", ".find(", ".delete("]
        )
    )
    test_coverage_delta = 0.0  # placeholder — requires external coverage reports

    return [
        lines_changed,
        file_size_kb,
        import_count,
        function_count,
        has_auth_code,
        has_db_code,
        test_coverage_delta,
    ]


@trace_node("score_risk")
def score_risk(state: AgentState) -> AgentState:
    state["status"] = "SCORING_RISK"
    logger.info("[%s] score_risk started", state["run_id"])

    try:
        file_list = state.get("file_list", [])
        if not file_list:
            state["risk_scores"] = []
            return state

        feature_matrix = np.array([_extract_features(f) for f in file_list], dtype=float)

        # Replace NaN/Inf just in case
        feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)

        clf = IsolationForest(
            contamination=0.1,
            n_estimators=100,
            random_state=42,
        )
        clf.fit(feature_matrix)

        predictions = clf.predict(feature_matrix)       # 1=normal, -1=anomaly
        raw_scores = clf.decision_function(feature_matrix)  # higher = more normal

        # Normalize raw_scores to [0, 1] where 1 = highest risk
        min_s, max_s = raw_scores.min(), raw_scores.max()
        if max_s > min_s:
            normalized = (max_s - raw_scores) / (max_s - min_s)
        else:
            normalized = np.zeros_like(raw_scores)

        # SHAP explainability — one call covers all files
        shap_explanations = shap_explain(clf, feature_matrix, normalized)

        risk_scores: list[dict] = []
        for i, f in enumerate(file_list):
            risk_scores.append(
                {
                    "file_path": f["path"],
                    "score": round(float(normalized[i]), 4),
                    "anomaly_flag": bool(predictions[i] == -1),
                    "features": {
                        "lines_changed": int(feature_matrix[i][0]),
                        "file_size_kb": round(float(feature_matrix[i][1]), 2),
                        "import_count": int(feature_matrix[i][2]),
                        "function_count": int(feature_matrix[i][3]),
                        "has_auth_code": bool(feature_matrix[i][4]),
                        "has_db_code": bool(feature_matrix[i][5]),
                    },
                    **shap_explanations[i],   # shap_values, shap_top, shap_sentence, shap_method
                }
            )

        state["risk_scores"] = sorted(risk_scores, key=lambda x: x["score"], reverse=True)
        logger.info("[%s] score_risk complete, top score=%.4f", state["run_id"], risk_scores[0]["score"] if risk_scores else 0)

    except Exception as exc:
        logger.exception("[%s] score_risk failed: %s", state["run_id"], exc)
        state["error"] = f"score_risk: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Node 3 — identify_gaps
# ---------------------------------------------------------------------------
_TEST_PATTERNS = re.compile(
    r"(test_|_test\.|\.spec\.|\.test\.|__tests__|/tests/|/test/)",
    re.IGNORECASE,
)


def _has_test_file(file_path: str, all_paths: set[str]) -> bool:
    """Return True if a corresponding test file exists anywhere in the changed set."""
    stem = re.sub(r"\.[^.]+$", "", os.path.basename(file_path))
    for p in all_paths:
        if _TEST_PATTERNS.search(p) and stem.lower() in p.lower():
            return True
    return False


def identify_gaps(state: AgentState) -> AgentState:
    state["status"] = "IDENTIFYING_GAPS"
    logger.info("[%s] identify_gaps started", state["run_id"])

    try:
        file_list = state.get("file_list", [])
        risk_scores = state.get("risk_scores", [])

        risk_map = {r["file_path"]: r["score"] for r in risk_scores}
        all_paths = {f["path"] for f in file_list}

        gaps: list[dict] = []
        for f in file_list:
            path = f["path"]
            # Skip files that ARE test files themselves
            if _TEST_PATTERNS.search(path):
                continue

            score = risk_map.get(path, 0.0)
            has_test = _has_test_file(path, all_paths)

            if not has_test and score > 0.3:
                gaps.append(
                    {
                        "file_path": path,
                        "has_test": False,
                        "priority": score,
                        "risk_score": score,
                    }
                )

        gaps.sort(key=lambda x: x["priority"], reverse=True)
        state["coverage_gaps"] = gaps[:10]
        logger.info("[%s] identify_gaps found %d gaps", state["run_id"], len(state["coverage_gaps"]))

    except Exception as exc:
        logger.exception("[%s] identify_gaps failed: %s", state["run_id"], exc)
        state["error"] = f"identify_gaps: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Node 3.5 — retrieve_context  (RAG: pulls similar test cases from pgvector)
# ---------------------------------------------------------------------------

def retrieve_context(state: AgentState) -> AgentState:
    """Retrieve similar past test cases for each coverage-gap file.

    Injects them into state["rag_context"] as pre-formatted few-shot
    examples. If RAG is unavailable the state is left unchanged and
    generate_tests falls back to zero-shot generation.
    """
    state["status"] = "RETRIEVING_CONTEXT"
    logger.info("[%s] retrieve_context started", state["run_id"])

    try:
        from rag.retriever import retrieve_for_file, format_few_shot_examples
        from rag.vector_store import ensure_schema

        ensure_schema()

        gaps = state.get("coverage_gaps", [])
        rag_context: list[dict] = []

        for gap in gaps[:5]:
            file_path = gap.get("file_path", "")
            if not file_path:
                continue
            retrieved = retrieve_for_file(
                project_id=state["project_id"],
                file_path=file_path,
                top_k=3,
            )
            examples = format_few_shot_examples(retrieved)
            rag_context.append({"file_path": file_path, "examples": examples, "retrieved_count": len(retrieved)})
            logger.info("[%s] RAG: %d examples for %s", state["run_id"], len(retrieved), file_path)

        state["rag_context"] = rag_context

    except Exception as exc:
        logger.warning("[%s] retrieve_context failed (non-fatal): %s", state["run_id"], exc)
        state["rag_context"] = []

    return state


# ---------------------------------------------------------------------------
# Node 4 — generate_tests  (RAG-enhanced: uses retrieved few-shot examples)
# ---------------------------------------------------------------------------
_SYSTEM_GENERATE = (
    "You are a senior QA engineer. Generate production-quality Playwright TypeScript tests.\n"
    "Rules:\n"
    "1. Test happy path\n"
    "2. Test error path\n"
    "3. Test edge cases\n"
    "4. Use Page Object Model pattern\n"
    "5. Include meaningful assertions\n"
    "6. Tests must be executable — not examples\n"
    "7. If past test examples are provided, match their style, imports, and fixture patterns\n"
    "8. Return ONLY the TypeScript code, no explanation"
)


@trace_node("generate_tests")
def generate_tests(state: AgentState) -> AgentState:
    state["status"] = "GENERATING_TESTS"
    logger.info("[%s] generate_tests started", state["run_id"])

    try:
        gaps = state.get("coverage_gaps", [])
        file_map = {f["path"]: f for f in state.get("file_list", [])}
        rag_map = {ctx["file_path"]: ctx["examples"] for ctx in state.get("rag_context", []) if ctx.get("examples")}
        client = _groq_client()
        generated: list[dict] = []

        for gap in gaps[:5]:
            file_path = gap["file_path"]
            file_info = file_map.get(file_path, {})
            content = file_info.get("content", "")

            # Prepend RAG few-shot examples when available
            rag_examples = rag_map.get(file_path, "")
            rag_section = f"\n\n{rag_examples}\n\n" if rag_examples else ""

            user_prompt = (
                f"Generate Playwright TypeScript tests for this file:\n\n"
                f"File: {file_path}\n\n"
                f"Content:\n{content[:3000]}"
                f"{rag_section}"
            )

            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": _SYSTEM_GENERATE},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=2048,
                )
                _capture_usage(state, "llama-3.3-70b-versatile", response, "generate_tests")
                test_code = response.choices[0].message.content.strip()
            except Exception as llm_exc:
                logger.warning("[%s] LLM call failed for %s: %s", state["run_id"], file_path, llm_exc)
                test_code = f"// LLM generation failed for {file_path}: {llm_exc}"

            generated.append(
                {
                    "file_path": file_path,
                    "test_code": test_code,
                    "language": "typescript",
                    "rag_examples_used": bool(rag_examples),
                }
            )
            logger.info("[%s] Generated tests for %s (RAG=%s)", state["run_id"], file_path, bool(rag_examples))

        state["generated_tests"] = generated

        # ── Auto-ingest this run's test cases back into RAG ──
        try:
            from rag.ingest import ingest_run_result
            ingest_run_result(
                project_id=state["project_id"],
                run_id=state["run_id"],
                repo_url=state["repo_url"],
                commit_sha=state["commit_sha"],
                risk_scores=state.get("risk_scores", []),
                coverage_gaps=state.get("coverage_gaps", []),
                generated_tests=generated,
                defects=[],  # defects added later by dispatch_results
            )
            logger.info("[%s] Auto-ingested test cases into RAG", state["run_id"])
        except Exception as ingest_exc:
            logger.warning("[%s] RAG auto-ingest failed (non-fatal): %s", state["run_id"], ingest_exc)

    except Exception as exc:
        logger.exception("[%s] generate_tests failed: %s", state["run_id"], exc)
        state["error"] = f"generate_tests: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Node 5 — detect_defects
# ---------------------------------------------------------------------------
_SQL_INJECTION_RE = re.compile(
    r'f".*SELECT|f\'.*SELECT|".*\+.*WHERE|\'.*\+.*WHERE|format\(.*SELECT',
    re.IGNORECASE,
)
_NULL_DEREF_RE = re.compile(r"\.\w+\s*\(.*\)\s*\.\w+", re.IGNORECASE)
_MISSING_TRY_RE = re.compile(
    r"(requests\.|httpx\.|urllib\.)(get|post|put|delete|patch)\(",
)
_BAD_COMMENT_RE = re.compile(r"#\s*(TODO|FIXME|HACK|XXX|BUG)\b", re.IGNORECASE)


def _try_parse_python(content: str) -> str | None:
    """Return a syntax-error string if the content is invalid Python, else None."""
    try:
        ast.parse(content)
        return None
    except SyntaxError as se:
        return str(se)


def _try_parse_js(content: str) -> str | None:
    """Very basic JS syntax check — bracket balance."""
    opens = content.count("{") + content.count("(") + content.count("[")
    closes = content.count("}") + content.count(")") + content.count("]")
    if abs(opens - closes) > 5:
        return f"Possible unbalanced brackets: opens={opens}, closes={closes}"
    return None


def detect_defects(state: AgentState) -> AgentState:
    state["status"] = "DETECTING_DEFECTS"
    logger.info("[%s] detect_defects started", state["run_id"])

    try:
        file_list = state.get("file_list", [])
        risk_map = {r["file_path"]: r for r in state.get("risk_scores", [])}
        defects: list[dict] = []

        for f in file_list:
            path = f["path"]
            content = f.get("content", "")
            risk_info = risk_map.get(path, {})
            risk_score = risk_info.get("score", 0.0)

            # --- P0: SQL injection patterns
            if _SQL_INJECTION_RE.search(content):
                defects.append(
                    {
                        "title": f"Potential SQL injection in {path}",
                        "severity": "P0",
                        "description": (
                            "Detected string interpolation inside SQL query. "
                            "This can expose the application to SQL injection attacks."
                        ),
                        "stack_trace": "",
                        "file_path": path,
                    }
                )

            # --- P0: auth code with no token validation
            if risk_info.get("features", {}).get("has_auth_code") and "verify" not in content.lower() and "validate" not in content.lower():
                defects.append(
                    {
                        "title": f"Missing token/credential validation in {path}",
                        "severity": "P0",
                        "description": (
                            "File contains authentication-related code but no explicit "
                            "token verification or credential validation was detected."
                        ),
                        "stack_trace": "",
                        "file_path": path,
                    }
                )

            # --- P1: missing error handling around HTTP calls
            if _MISSING_TRY_RE.search(content):
                # Check if the call is inside a try block
                call_match = _MISSING_TRY_RE.search(content)
                if call_match:
                    start = max(0, call_match.start() - 200)
                    snippet = content[start: call_match.start()]
                    if "try:" not in snippet and "try {" not in snippet:
                        defects.append(
                            {
                                "title": f"Unhandled HTTP call in {path}",
                                "severity": "P1",
                                "description": (
                                    "HTTP client call detected without surrounding try/except. "
                                    "Network failures will cause unhandled exceptions."
                                ),
                                "stack_trace": "",
                                "file_path": path,
                            }
                        )

            # --- P1: syntax errors
            if path.endswith(".py"):
                syntax_err = _try_parse_python(content)
                if syntax_err:
                    defects.append(
                        {
                            "title": f"Python syntax error in {path}",
                            "severity": "P1",
                            "description": f"File failed ast.parse(): {syntax_err}",
                            "stack_trace": syntax_err,
                            "file_path": path,
                        }
                    )
            elif path.endswith((".js", ".ts", ".jsx", ".tsx")):
                js_err = _try_parse_js(content)
                if js_err:
                    defects.append(
                        {
                            "title": f"Possible JS/TS syntax issue in {path}",
                            "severity": "P1",
                            "description": js_err,
                            "stack_trace": "",
                            "file_path": path,
                        }
                    )

            # --- P2: DB code with no rollback/transaction handling
            if risk_info.get("features", {}).get("has_db_code") and "rollback" not in content.lower() and "transaction" not in content.lower():
                defects.append(
                    {
                        "title": f"Database write without transaction handling in {path}",
                        "severity": "P2",
                        "description": (
                            "File contains DB write operations but no rollback or "
                            "explicit transaction boundary was detected."
                        ),
                        "stack_trace": "",
                        "file_path": path,
                    }
                )

            # --- P3: TODO/FIXME in high-risk files
            if risk_score > 0.3 and _BAD_COMMENT_RE.search(content):
                matches = _BAD_COMMENT_RE.findall(content)
                defects.append(
                    {
                        "title": f"Unresolved {', '.join(set(matches))} comments in high-risk file {path}",
                        "severity": "P3",
                        "description": (
                            f"Found {len(matches)} unresolved comment marker(s) in a file "
                            f"with risk score {risk_score:.2f}. These may indicate incomplete logic."
                        ),
                        "stack_trace": "",
                        "file_path": path,
                    }
                )

        state["defects"] = defects
        logger.info("[%s] detect_defects found %d defects", state["run_id"], len(defects))

    except Exception as exc:
        logger.exception("[%s] detect_defects failed: %s", state["run_id"], exc)
        state["error"] = f"detect_defects: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Node 6 — explain_and_score
# ---------------------------------------------------------------------------
_EXPLAIN_SECTIONS = [
    "what broke",
    "why it matters",
    "root cause",
    "steps to reproduce",
    "suggested fix",
]


def _consistency_score(explanation: str) -> float:
    lower = explanation.lower()
    return round(sum(0.2 for s in _EXPLAIN_SECTIONS if s in lower), 2)


@trace_node("explain_and_score")
def explain_and_score(state: AgentState) -> AgentState:
    state["status"] = "EXPLAINING_DEFECTS"
    logger.info("[%s] explain_and_score started", state["run_id"])

    try:
        defects = state.get("defects", [])
        client = _groq_client()
        explained: list[dict] = []

        system_prompt = "You are a QA expert. Explain defects clearly for developers."

        for defect in defects:
            user_prompt = (
                f"Explain this defect:\n"
                f"Title: {defect['title']}\n"
                f"Severity: {defect['severity']}\n"
                f"Description: {defect['description']}\n\n"
                "Provide:\n"
                "1. What broke\n"
                "2. Why it matters\n"
                "3. Root cause hypothesis\n"
                "4. Steps to reproduce\n"
                "5. Suggested fix"
            )

            explanation = ""
            score = 0.0
            try:
                for attempt in range(2):
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=1024,
                    )
                    _capture_usage(state, "llama-3.3-70b-versatile", response, "explain_and_score")
                    explanation = response.choices[0].message.content.strip()
                    score = _consistency_score(explanation)
                    if score >= 0.85:
                        break
                    # If score < 0.85 on first attempt, retry once with stricter prompt
                    user_prompt = (
                        user_prompt
                        + "\n\nIMPORTANT: Your previous response was missing some sections. "
                        "Ensure ALL 5 sections are clearly labeled and present."
                    )
                    logger.info(
                        "[%s] Consistency score %.2f < 0.85, retrying explanation for '%s'",
                        state["run_id"],
                        score,
                        defect["title"],
                    )

            except Exception as llm_exc:
                logger.warning(
                    "[%s] LLM explanation failed for '%s': %s",
                    state["run_id"],
                    defect["title"],
                    llm_exc,
                )
                explanation = f"Explanation unavailable: {llm_exc}"
                score = 0.0

            explained.append(
                {
                    **defect,
                    "ai_explanation": explanation,
                    "consistency_score": score,
                }
            )

        state["explained_defects"] = explained
        logger.info("[%s] explain_and_score complete, %d defects explained", state["run_id"], len(explained))

    except Exception as exc:
        logger.exception("[%s] explain_and_score failed: %s", state["run_id"], exc)
        state["error"] = f"explain_and_score: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Node 6.5 — generate_fixes (CodegenerateAgent: proposes patches for defects)
# ---------------------------------------------------------------------------
_SYSTEM_CODEGEN = (
    "You are a senior software engineer. Given a defect and the file it occurs in, "
    "produce a minimal fix.\n"
    "Rules:\n"
    "1. Fix ONLY the defect described — do not refactor unrelated code\n"
    "2. Return a unified diff (---/+++ headers, @@ hunks) against the file as shown\n"
    "3. Keep the change as small as possible while fully resolving the defect\n"
    "4. Return ONLY the diff, no explanation"
)


@trace_node("generate_fixes")
def generate_fixes(state: AgentState) -> AgentState:
    """CodegenerateAgent — proposes a patch for each high-severity defect."""
    state["status"] = "GENERATING_FIXES"
    logger.info("[%s] generate_fixes started", state["run_id"])

    try:
        explained_defects = state.get("explained_defects", [])
        file_map = {f["path"]: f for f in state.get("file_list", [])}
        client = _groq_client()

        to_fix = [d for d in explained_defects if d.get("severity") in ("P0", "P1")][:5]
        fixes: list[dict] = []

        for defect in to_fix:
            file_path = defect.get("file_path", "")
            file_info = file_map.get(file_path, {})
            content = file_info.get("content", "")
            if not content:
                continue

            user_prompt = (
                f"Defect: {defect['title']}\n"
                f"Severity: {defect['severity']}\n"
                f"Description: {defect['description']}\n"
                f"Root cause / explanation: {defect.get('ai_explanation', '')[:1500]}\n\n"
                f"File: {file_path}\n\n"
                f"Content:\n{content[:3000]}"
            )

            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": _SYSTEM_CODEGEN},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                )
                _capture_usage(state, "llama-3.3-70b-versatile", response, "generate_fixes")
                fix_diff = response.choices[0].message.content.strip()
            except Exception as llm_exc:
                logger.warning("[%s] Fix generation failed for %s: %s", state["run_id"], file_path, llm_exc)
                fix_diff = f"// Fix generation failed for {file_path}: {llm_exc}"

            fixes.append(
                {
                    "file_path": file_path,
                    "defect_title": defect["title"],
                    "severity": defect["severity"],
                    "fix_diff": fix_diff,
                }
            )
            logger.info("[%s] Generated fix for %s (%s)", state["run_id"], file_path, defect["severity"])

        state["generated_fixes"] = fixes
        logger.info("[%s] generate_fixes complete, %d fixes proposed", state["run_id"], len(fixes))

    except Exception as exc:
        logger.exception("[%s] generate_fixes failed: %s", state["run_id"], exc)
        state["error"] = f"generate_fixes: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Node 6.6 — apply_and_verify_fixes (CodegenerateAgent: clone, patch, retest, PR)
# ---------------------------------------------------------------------------
# Rollback story: a fix NEVER touches the target branch directly. Each one is
# applied on its own auto-fix/<run>-<slug> branch and only reaches GitHub as
# an open PR — nothing is auto-merged. To undo: close the PR (repo is
# untouched) or, if already merged, `git revert` the merge commit like any
# other change. This is why no separate "undo" mechanism is implemented here.

_SUBPROJECT_TEST_CMDS: dict[str, list[str]] = {
    "ai-engine": ["python", "-m", "pytest", "-q"],
    "backend": ["mvnw.cmd" if os.name == "nt" else "./mvnw", "-q", "test"],
}


def _sanitize(text: str) -> str:
    """Strip anything that looks like a token from text before it hits logs/audit records."""
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        text = text.replace(token, "***")
    return text[:800]


def _slugify_branch(run_id: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "fix"
    return f"auto-fix/{run_id[:8]}-{slug}"


def _clone_repo(repo_url: str, github_token: str, commit_sha: str, dest: str) -> None:
    owner_repo = _repo_name_from_url(repo_url)
    auth_url = f"https://{github_token}@github.com/{owner_repo}.git"
    subprocess.run(
        ["git", "clone", "--quiet", auth_url, dest],
        check=True, timeout=120, capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", commit_sha],
        cwd=dest, check=True, timeout=60, capture_output=True, text=True,
    )


def _apply_diff(repo_dir: str, diff_text: str) -> tuple[bool, str]:
    patch_path = os.path.join(repo_dir, ".qaip_fix.patch")
    with open(patch_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(diff_text if diff_text.endswith("\n") else diff_text + "\n")
    try:
        result = subprocess.run(
            ["git", "apply", "--whitespace=fix", ".qaip_fix.patch"],
            cwd=repo_dir, capture_output=True, text=True, timeout=30,
        )
    finally:
        if os.path.exists(patch_path):
            os.remove(patch_path)
    if result.returncode != 0:
        return False, result.stderr
    return True, ""


def _run_tests(repo_dir: str, file_path: str) -> tuple[bool | None, str]:
    """Return (passed, output). passed=None means no test runner is mapped for this path."""
    subdir = file_path.split("/", 1)[0]
    cmd = _SUBPROJECT_TEST_CMDS.get(subdir)
    if cmd is None:
        return None, f"no automated test runner mapped for '{subdir}/' — review manually"

    try:
        result = subprocess.run(
            cmd, cwd=os.path.join(repo_dir, subdir),
            capture_output=True, text=True, timeout=300,
        )
        output = (result.stdout[-1500:] + result.stderr[-1500:])
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "test run timed out after 300s"
    except Exception as exc:
        return False, str(exc)


def _open_pr(repo_url: str, github_token: str, branch: str, base_branch: str, title: str, body: str) -> str:
    gh = Github(github_token)
    repo = gh.get_repo(_repo_name_from_url(repo_url))
    pr = repo.create_pull(title=title, body=body, head=branch, base=base_branch)
    return pr.html_url


@trace_node("apply_and_verify_fixes")
def apply_and_verify_fixes(state: AgentState) -> AgentState:
    """CodegenerateAgent — clones the real repo, applies each proposed fix on its
    own branch, re-runs that subproject's real test suite, and only opens a PR
    (never a direct commit to the target branch) when tests pass."""
    state["status"] = "APPLYING_FIXES"
    logger.info("[%s] apply_and_verify_fixes started", state["run_id"])

    fixes = [
        f for f in state.get("generated_fixes", [])
        if not f.get("fix_diff", "").startswith("// Fix generation failed")
    ]
    if not fixes:
        state["pr_results"] = []
        return state

    repo_url = state["repo_url"]
    github_token = state["github_token"]
    commit_sha = state["commit_sha"]
    explanation_map = {d["title"]: d.get("ai_explanation", "") for d in state.get("explained_defects", [])}

    try:
        default_branch = Github(github_token).get_repo(_repo_name_from_url(repo_url)).default_branch
    except Exception as exc:
        logger.warning("[%s] Could not resolve default branch, assuming 'main': %s", state["run_id"], _sanitize(str(exc)))
        default_branch = "main"

    pr_results: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="qaip_autofix_") as tmp_dir:
        try:
            _clone_repo(repo_url, github_token, commit_sha, tmp_dir)
        except Exception as exc:
            logger.warning("[%s] Clone failed, no fixes applied: %s", state["run_id"], _sanitize(str(exc)))
            state["pr_results"] = [{"status": "clone_failed", "detail": _sanitize(str(exc))}]
            return state

        for fix in fixes:
            file_path = fix["file_path"]
            defect_title = fix["defect_title"]
            branch = _slugify_branch(state["run_id"], defect_title)
            why = explanation_map.get(defect_title, "")

            entry: dict = {
                "file_path": file_path,
                "defect_title": defect_title,
                "severity": fix.get("severity", ""),
                "branch": branch,
                "why": why[:800],
            }

            try:
                subprocess.run(["git", "checkout", "--quiet", commit_sha], cwd=tmp_dir, check=True, timeout=30, capture_output=True, text=True)
                subprocess.run(["git", "checkout", "--quiet", "-b", branch], cwd=tmp_dir, check=True, timeout=30, capture_output=True, text=True)
            except Exception as exc:
                entry["status"] = "branch_failed"
                entry["detail"] = _sanitize(str(exc))
                pr_results.append(entry)
                continue

            applied, apply_err = _apply_diff(tmp_dir, fix["fix_diff"])
            if not applied:
                entry["status"] = "apply_failed"
                entry["detail"] = _sanitize(apply_err)
                pr_results.append(entry)
                logger.info("[%s] Fix for %s did not apply cleanly, skipped", state["run_id"], file_path)
                continue

            passed, test_output = _run_tests(tmp_dir, file_path)
            entry["tests_passed"] = passed

            if passed is False:
                entry["status"] = "tests_failed"
                entry["detail"] = _sanitize(test_output)
                pr_results.append(entry)
                logger.info("[%s] Fix for %s failed retest, skipped", state["run_id"], file_path)
                continue

            try:
                subprocess.run(["git", "add", file_path], cwd=tmp_dir, check=True, timeout=15, capture_output=True, text=True)
                subprocess.run(
                    ["git", "-c", "user.email=qaip-bot@local", "-c", "user.name=QAIP CodegenerateAgent",
                     "commit", "--quiet", "-m", f"Auto-fix: {defect_title}"],
                    cwd=tmp_dir, check=True, timeout=15, capture_output=True, text=True,
                )
                subprocess.run(["git", "push", "--quiet", "origin", branch], cwd=tmp_dir, check=True, timeout=60, capture_output=True, text=True)
            except Exception as exc:
                entry["status"] = "push_failed"
                entry["detail"] = _sanitize(str(exc))
                pr_results.append(entry)
                continue

            verify_line = (
                "Verification: existing test suite passed after the fix."
                if passed else
                "Verification: no automated test runner mapped for this path — review manually."
            )
            body = (
                f"Automated fix proposed by QAIP CodegenerateAgent.\n\n"
                f"**Defect:** {defect_title} (`{fix.get('severity', '')}`)\n"
                f"**File:** `{file_path}`\n\n"
                f"**Why:**\n{why or 'See linked run report.'}\n\n"
                f"{verify_line}\n\n"
                f"To roll back: close this PR without merging — the target branch is untouched. "
                f"If already merged, `git revert` this PR's merge commit."
            )
            try:
                pr_url = _open_pr(repo_url, github_token, branch, default_branch,
                                   title=f"Auto-fix: {defect_title}", body=body)
                entry["status"] = "pr_opened"
                entry["pr_url"] = pr_url
                logger.info("[%s] Opened PR for %s: %s", state["run_id"], file_path, pr_url)
            except Exception as exc:
                entry["status"] = "pr_failed"
                entry["detail"] = _sanitize(str(exc))

            pr_results.append(entry)

    state["pr_results"] = pr_results
    logger.info("[%s] apply_and_verify_fixes complete: %d result(s)", state["run_id"], len(pr_results))
    return state


# ---------------------------------------------------------------------------
# Node 7 — dispatch_results
# ---------------------------------------------------------------------------
_JIRA_SEVERITY_MAP = {"P0": "Highest", "P1": "High", "P2": "Medium", "P3": "Low"}


def _save_report(state: AgentState) -> str:
    run_id = state["run_id"]
    report = {
        "run_id": run_id,
        "project_id": state["project_id"],
        "repo_url": state["repo_url"],
        "commit_sha": state["commit_sha"],
        "risk_scores": state.get("risk_scores", []),
        "coverage_gaps": state.get("coverage_gaps", []),
        "generated_tests": state.get("generated_tests", []),
        "defects": state.get("defects", []),
        "explained_defects": state.get("explained_defects", []),
        "generated_fixes": state.get("generated_fixes", []),
        "pr_results": state.get("pr_results", []),
    }
    path = f"/tmp/testmind_report_{run_id}.json"
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
        logger.info("[%s] Report saved to %s", run_id, path)
    except Exception as exc:
        logger.warning("[%s] Could not save report: %s", run_id, exc)
        path = ""
    return path


def _create_jira_tickets(state: AgentState) -> dict:
    jira_url = os.getenv("JIRA_URL", "").rstrip("/")
    jira_token = os.getenv("JIRA_API_TOKEN", "")
    jira_project = os.getenv("JIRA_PROJECT_KEY", "QA")
    jira_email = os.getenv("JIRA_EMAIL", "")

    if not jira_url or not jira_token:
        return {"jira": "skipped — JIRA_URL or JIRA_API_TOKEN not set"}

    created: list[str] = []
    failed: list[str] = []

    high_priority = [
        d for d in state.get("explained_defects", []) if d.get("severity") in ("P0", "P1")
    ]

    for defect in high_priority:
        payload = {
            "fields": {
                "project": {"key": jira_project},
                "summary": f"[TESTMIND-{defect['severity']}] {defect['title']}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": defect.get("ai_explanation", defect.get("description", "")),
                                }
                            ],
                        }
                    ],
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": _JIRA_SEVERITY_MAP.get(defect["severity"], "Medium")},
                "labels": ["testmind", "ai-detected", defect["severity"].lower()],
            }
        }

        try:
            resp = requests.post(
                f"{jira_url}/rest/api/3/issue",
                json=payload,
                auth=(jira_email, jira_token),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10,
            )
            if resp.status_code in (200, 201):
                issue_key = resp.json().get("key", "?")
                created.append(issue_key)
                logger.info("[%s] Created Jira issue %s", state["run_id"], issue_key)
            else:
                failed.append(f"{defect['title']} — HTTP {resp.status_code}")
                logger.warning("[%s] Jira ticket creation failed: %s %s", state["run_id"], resp.status_code, resp.text)
        except Exception as exc:
            failed.append(f"{defect['title']} — {exc}")
            logger.warning("[%s] Jira request error: %s", state["run_id"], exc)

    return {"jira": {"created": created, "failed": failed}}


def _post_slack(state: AgentState) -> dict:
    slack_token = os.getenv("SLACK_BOT_TOKEN", "")
    slack_channel = os.getenv("SLACK_CHANNEL", "#qa-alerts")

    if not slack_token:
        return {"slack": "skipped — SLACK_BOT_TOKEN not set"}

    explained = state.get("explained_defects", [])
    severity_counts: dict[str, int] = {}
    for d in explained:
        sev = d.get("severity", "?")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    top_risk = state.get("risk_scores", [])[:3]
    top_files = ", ".join(r["file_path"] for r in top_risk) or "N/A"

    text = (
        f":robot_face: *TestMind Analysis Complete*\n"
        f"• *Project:* {state['project_id']}\n"
        f"• *Repo:* {state['repo_url']}\n"
        f"• *Commit:* `{state['commit_sha'][:8]}`\n"
        f"• *Defects:* {', '.join(f'{k}={v}' for k, v in sorted(severity_counts.items())) or 'None'}\n"
        f"• *Top risk files:* {top_files}\n"
        f"• *Coverage gaps:* {len(state.get('coverage_gaps', []))}\n"
        f"• *Tests generated:* {len(state.get('generated_tests', []))}"
    )

    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            json={"channel": slack_channel, "text": text},
            headers={
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            logger.info("[%s] Slack notification sent", state["run_id"])
            return {"slack": "sent"}
        else:
            logger.warning("[%s] Slack error: %s", state["run_id"], data.get("error"))
            return {"slack": f"error: {data.get('error')}"}
    except Exception as exc:
        logger.warning("[%s] Slack request failed: %s", state["run_id"], exc)
        return {"slack": f"failed: {exc}"}


def _post_autofix_audit(state: AgentState) -> dict:
    """Persist this run's auto-fix attempts (pr_results) to the backend's audit
    table so they're queryable later, instead of only living in the per-run
    JSON report. Non-blocking — a failure here never fails the pipeline."""
    pr_results = state.get("pr_results", [])
    if not pr_results:
        return {"autofix_audit": "skipped — no fix attempts this run"}

    backend_url = os.getenv("BACKEND_URL", "http://backend:8080")
    payload = {
        "runId": state["run_id"],
        "projectId": state["project_id"],
        "repoUrl": state["repo_url"],
        "commitSha": state["commit_sha"],
        "entries": [
            {
                "filePath": r.get("file_path", ""),
                "defectTitle": r.get("defect_title", ""),
                "severity": r.get("severity", ""),
                "branch": r.get("branch", ""),
                "why": r.get("why", ""),
                "testsPassed": r.get("tests_passed"),
                "status": r.get("status", ""),
                "prUrl": r.get("pr_url", ""),
                "detail": r.get("detail", ""),
            }
            for r in pr_results
        ],
    }

    try:
        resp = requests.post(f"{backend_url}/api/autofix-audit", json=payload, timeout=15)
        if resp.status_code in (200, 201, 204):
            logger.info("[%s] autofix audit ingested (%d entries)", state["run_id"], len(pr_results))
            return {"autofix_audit": "ok"}
        logger.warning("[%s] autofix audit ingest HTTP %s", state["run_id"], resp.status_code)
        return {"autofix_audit": f"http_{resp.status_code}"}
    except Exception as exc:
        logger.warning("[%s] autofix audit ingest failed: %s", state["run_id"], exc)
        return {"autofix_audit": f"failed: {exc}"}


def _callback_backend(state: AgentState) -> dict:
    backend_url = os.getenv("BACKEND_URL", "http://backend:8080")
    run_id = state["run_id"]

    payload = {
        "defects": state.get("explained_defects", []),
        "risk_scores": state.get("risk_scores", []),
        "status": "COMPLETED",
    }

    try:
        resp = requests.post(
            f"{backend_url}/api/test-runs/{run_id}/complete",
            json=payload,
            timeout=15,
        )
        if resp.status_code in (200, 201, 204):
            logger.info("[%s] Backend callback succeeded", run_id)
            return {"backend": "ok"}
        else:
            logger.warning("[%s] Backend callback HTTP %s", run_id, resp.status_code)
            return {"backend": f"http_{resp.status_code}"}
    except Exception as exc:
        logger.warning("[%s] Backend callback failed: %s", run_id, exc)
        return {"backend": f"failed: {exc}"}


@trace_node("dispatch_results")
def dispatch_results(state: AgentState) -> AgentState:
    state["status"] = "DISPATCHING"
    logger.info("[%s] dispatch_results started", state["run_id"])

    results: dict = {}

    try:
        # a) Save JSON report
        report_path = _save_report(state)
        results["report_path"] = report_path

        # b) Jira tickets (non-blocking)
        jira_result = _create_jira_tickets(state)
        results.update(jira_result)

        # c) Slack notification (non-blocking)
        slack_result = _post_slack(state)
        results.update(slack_result)

        # d) Backend callback (non-blocking)
        backend_result = _callback_backend(state)
        results.update(backend_result)

        # e) Persist auto-fix audit trail (non-blocking)
        audit_result = _post_autofix_audit(state)
        results.update(audit_result)

        state["dispatch_results"] = results
        state["status"] = "COMPLETED"
        logger.info("[%s] dispatch_results complete: %s", state["run_id"], results)

    except Exception as exc:
        logger.exception("[%s] dispatch_results failed: %s", state["run_id"], exc)
        state["error"] = f"dispatch_results: {exc}"
        state["status"] = "FAILED"

    return state


# ---------------------------------------------------------------------------
# Error-routing condition
# ---------------------------------------------------------------------------
def _should_continue(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    return "continue"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("fetch_codebase", fetch_codebase)
    graph.add_node("score_risk", score_risk)
    graph.add_node("identify_gaps", identify_gaps)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_tests", generate_tests)
    graph.add_node("detect_defects", detect_defects)
    graph.add_node("explain_and_score", explain_and_score)
    graph.add_node("generate_fixes", generate_fixes)
    graph.add_node("apply_and_verify_fixes", apply_and_verify_fixes)
    graph.add_node("dispatch_results", dispatch_results)

    graph.set_entry_point("fetch_codebase")

    # Each edge includes an error-routing conditional
    for src, dst in [
        ("fetch_codebase", "score_risk"),
        ("score_risk", "identify_gaps"),
        ("identify_gaps", "retrieve_context"),
        ("retrieve_context", "generate_tests"),
        ("generate_tests", "detect_defects"),
        ("detect_defects", "explain_and_score"),
        ("explain_and_score", "generate_fixes"),
        ("generate_fixes", "apply_and_verify_fixes"),
        ("apply_and_verify_fixes", "dispatch_results"),
    ]:
        graph.add_conditional_edges(
            src,
            _should_continue,
            {"continue": dst, "end": END},
        )

    graph.add_edge("dispatch_results", END)

    return graph.compile()
