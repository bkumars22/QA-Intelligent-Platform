"""
QA Intelligent Platform (AI-Driven) — AI Engine FastAPI entry point.

Endpoints:
  POST /analyze          — trigger full 7-node LangGraph agent
  GET  /status/{run_id}  — poll run status
  POST /explain          — explain a single defect
  POST /generate-tests   — generate tests for a specific file
  GET  /health           — health check
"""

import os
import uuid
import time
import asyncio
import logging
from collections import defaultdict
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from groq import Groq

from agents.langgraph_agent import build_graph, AgentState

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("testmind.main")

# ---------------------------------------------------------------------------
# Rate-limiting state (in-memory, per IP)
# ---------------------------------------------------------------------------
_rate_limit_window: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 20   # requests
RATE_LIMIT_TTL = 60   # seconds


def _check_rate_limit(ip: str) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.monotonic()
    window = _rate_limit_window[ip]
    # Drop timestamps older than TTL
    _rate_limit_window[ip] = [t for t in window if now - t < RATE_LIMIT_TTL]
    if len(_rate_limit_window[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_window[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# In-memory run-status store
# ---------------------------------------------------------------------------
run_store: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TestMind AI Engine",
    description="LangGraph-powered QA intelligence service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_origin_regex=r"https://(.*\.railway\.app|.*\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate-limit middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Max 20 requests/min per IP."},
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    project_id: int = Field(..., description="TestMind project ID")
    repo_url: str = Field(..., description="Full GitHub repository URL")
    github_token: str = Field(..., description="GitHub personal access token")
    commit_sha: str = Field(..., description="Commit SHA to analyse")


class AnalyzeResponse(BaseModel):
    run_id: str
    status: str
    message: str


class ExplainRequest(BaseModel):
    title: str
    severity: str
    description: str
    stack_trace: str = ""


class ExplainResponse(BaseModel):
    ai_explanation: str
    consistency_score: float


class GenerateTestsRequest(BaseModel):
    file_path: str
    content: str
    language: str = "typescript"


class GenerateTestsResponse(BaseModel):
    file_path: str
    test_code: str
    language: str


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------
def _run_agent(run_id: str, initial_state: AgentState) -> None:
    """Execute the LangGraph graph synchronously in a background thread."""
    try:
        run_store[run_id]["status"] = "RUNNING"
        graph = build_graph()
        final_state: AgentState = graph.invoke(initial_state)

        run_store[run_id].update(
            {
                "status": final_state.get("status", "COMPLETED"),
                "error": final_state.get("error", ""),
                "risk_scores": final_state.get("risk_scores", []),
                "coverage_gaps": final_state.get("coverage_gaps", []),
                "generated_tests": final_state.get("generated_tests", []),
                "defects": final_state.get("defects", []),
                "explained_defects": final_state.get("explained_defects", []),
                "dispatch_results": final_state.get("dispatch_results", {}),
            }
        )
    except Exception as exc:
        logger.exception("Agent run %s failed: %s", run_id, exc)
        run_store[run_id]["status"] = "FAILED"
        run_store[run_id]["error"] = str(exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "model": "llama-3.3-70b-versatile"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: AnalyzeRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())

    initial_state: AgentState = {
        "run_id": run_id,
        "project_id": payload.project_id,
        "repo_url": payload.repo_url,
        "github_token": payload.github_token,
        "commit_sha": payload.commit_sha,
        "file_list": [],
        "risk_scores": [],
        "coverage_gaps": [],
        "generated_tests": [],
        "defects": [],
        "explained_defects": [],
        "dispatch_results": {},
        "error": "",
        "status": "QUEUED",
    }

    run_store[run_id] = {
        "run_id": run_id,
        "project_id": payload.project_id,
        "status": "QUEUED",
        "error": "",
    }

    background_tasks.add_task(_run_agent, run_id, initial_state)

    logger.info("Queued run %s for project %s", run_id, payload.project_id)
    return AnalyzeResponse(
        run_id=run_id,
        status="QUEUED",
        message="Analysis queued. Poll /status/{run_id} for progress.",
    )


@app.get("/status/{run_id}")
async def get_status(run_id: str):
    record = run_store.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found.")
    return record


@app.post("/explain", response_model=ExplainResponse)
async def explain_defect(payload: ExplainRequest):
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    system_prompt = "You are a QA expert. Explain defects clearly for developers."
    user_prompt = (
        f"Explain this defect:\n"
        f"Title: {payload.title}\n"
        f"Severity: {payload.severity}\n"
        f"Description: {payload.description}\n"
        f"Stack Trace:\n{payload.stack_trace}\n\n"
        "Provide:\n"
        "1. What broke\n"
        "2. Why it matters\n"
        "3. Root cause hypothesis\n"
        "4. Steps to reproduce\n"
        "5. Suggested fix"
    )

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        explanation = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception("Groq call failed in /explain: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}")

    # Score: check all 5 sections present
    sections = ["What broke", "Why it matters", "Root cause", "Steps to reproduce", "Suggested fix"]
    score = sum(0.2 for s in sections if s.lower() in explanation.lower())

    return ExplainResponse(ai_explanation=explanation, consistency_score=round(score, 2))


@app.post("/generate-tests", response_model=GenerateTestsResponse)
async def generate_tests(payload: GenerateTestsRequest):
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    system_prompt = (
        "You are a senior QA engineer. Generate production-quality Playwright TypeScript tests.\n"
        "Rules:\n"
        "1. Test happy path\n"
        "2. Test error path\n"
        "3. Test edge cases\n"
        "4. Use Page Object Model pattern\n"
        "5. Include meaningful assertions\n"
        "6. Tests must be executable — not examples\n"
        "7. Return ONLY the TypeScript code, no explanation"
    )
    user_prompt = (
        f"Generate Playwright TypeScript tests for this file:\n\n"
        f"File: {payload.file_path}\n\n"
        f"Content:\n{payload.content[:3000]}"
    )

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        test_code = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.exception("Groq call failed in /generate-tests: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}")

    return GenerateTestsResponse(
        file_path=payload.file_path,
        test_code=test_code,
        language=payload.language,
    )
