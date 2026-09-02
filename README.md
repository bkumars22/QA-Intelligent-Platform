# QA Intelligent Platform (AI-Driven) — QAIP

> Plug in your GitHub repo. Get risk scores, AI-generated tests, and defect explanations — fully autonomous. Now with RAG memory: tests improve every sprint.

[![CI](https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bkumars22/QA-Intelligent-Platform/actions)
[![Pages](https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/pages.yml/badge.svg)](https://bkumars22.github.io/QA-Intelligent-Platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Java 17](https://img.shields.io/badge/Java-17-orange?style=flat-square)](https://openjdk.org)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![Groq](https://img.shields.io/badge/AI-Groq%20Llama--3.3--70b-f97316?style=flat-square)](https://console.groq.com)
[![Azure OpenAI](https://img.shields.io/badge/AI-Azure%20OpenAI%20(optional)-0078d4?style=flat-square)](https://azure.microsoft.com/products/ai-services/openai-service)
[![RAG](https://img.shields.io/badge/RAG-pgvector%20%2B%20sentence--transformers-8b5cf6?style=flat-square)](https://github.com/bkumars22/QA-Intelligent-Platform)

GitHub: [github.com/bkumars22/QA-Intelligent-Platform](https://github.com/bkumars22/QA-Intelligent-Platform)
Built by: B KumaraSwamy — Bangalore, India

---

## Live Access

| Project | URL |
|---------|-----|
| **QAIP Dashboard** | **https://bkumars22.github.io/QA-Intelligent-Platform** |
| SCIP — Supply Chain Platform | https://bkumars22.github.io/SupplyChainPlatformProject |
| ARIA — Adaptive Learning AI | https://bkumars22.github.io/ARIA |
| ZENTRAVIX — Org Intelligence | https://bkumars22.github.io/ZENTRAVIX |

**A note on the live demo's AI features:** the Agentic RAG chat, Hybrid
Search, and Quantum-Assisted Test Selection panels call the `ai-engine`
Python service directly from your browser (`VITE_AI_ENGINE_URL`, no
demo-mode mock) — the deployed GitHub Pages site doesn't currently run
that service anywhere public, so those specific panels will show a
"Failed to fetch" error there. Everything else on the live demo
(dashboard, project browsing, Automation tab's framework connect/
explorer/execution history, MCP config) works fully. To try the
AI-engine features, run `ai-engine` locally (`uvicorn main:app`,
`cd ai-engine`) alongside the frontend — see `ai-engine/quantum_test_selection/README.md`
for the quantum selection feature specifically.

---

## What QAIP Does

QAIP is a **fully autonomous QA intelligence engine** that:

1. **Fetches your GitHub repository** at any commit
2. **Scores file-level risk** using IsolationForest anomaly detection
3. **Identifies coverage gaps** — files with no corresponding test
4. **Retrieves similar past tests** from RAG memory (sprint-over-sprint learning)
5. **Generates Playwright TypeScript tests** using Groq Llama-3.3-70b, informed by historical patterns
6. **Detects defects** by scanning changed files for vulnerability patterns
7. **Explains defects** with AI root-cause analysis and severity scoring
8. **Generates a fix** (CodegenerateAgent) for each P0/P1 defect as a unified diff
9. **Applies, retests, and PRs the fix** — clones the repo, applies the patch on its own branch, re-runs the real test suite, and only opens a PR if it passes. Nothing is ever auto-merged.
10. **Stores everything in RAG** (and every fix attempt in a queryable audit trail) so the next sprint starts smarter

---

## RAG Memory — Sprint-over-Sprint Learning

QAIP now learns from every run. After Sprint 1, it knows which test patterns worked. By Sprint 5, it generates production-quality tests that match your codebase's exact style.

```
Sprint 1 → Zero-shot test generation (baseline)
Sprint 2 → Retrieves Sprint 1 patterns → better tests
Sprint 5 → Knows your patterns, imports, fixtures → excellent tests
```

### How it works

```
Coverage Gap File
       ↓
[retrieve_context node] — pgvector cosine search
       ↓
Top-3 similar past test cases (few-shot examples)
       ↓
[generate_tests node] — LLM sees examples + file content
       ↓
Better test code → stored back into RAG
```

### RAG API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /rag/ingest` | Store any document (test case, defect, Jira story) |
| `POST /rag/query` | NL search over all stored QAIP data |
| `POST /rag/ingest-jira` | Store a Jira story so test gen understands intent |

---

## CodegenerateAgent — Auto-Fix, Retest, PR

For every P0/P1 defect `explain_and_score` finds, QAIP proposes and verifies an actual fix —
not just a suggestion, a tested one:

```
Defect + AI explanation
       ↓
[generate_fixes node] — Groq proposes a unified diff
       ↓
[apply_and_verify_fixes node]
  1. clone the repo at that commit, on a fresh auto-fix/<run>-<slug> branch
  2. apply the diff
  3. re-run that subproject's real test suite (pytest / mvnw test)
  4. tests pass → push branch, open a PR
     tests fail / patch doesn't apply → stop, nothing is pushed
```

Nothing is ever committed to the target branch directly. Rollback is structural: close the PR
and the repo is untouched, or `git revert` the merge commit if it was already merged. Every
attempt — opened, failed, or skipped — is recorded for audit at `POST/GET /api/autofix-audit`
and browsable on the **Auto-Fix Audit** dashboard page.

---

## Architecture

```

                    QAIP System                          
                                                         
  React 18 Frontend  Spring Boot 3.3 Backend          
       (GitHub Pages)       (Railway)                    
                                                        
                    PostgreSQL + pgvector                 
                    (Railway managed)                    
                                                        
                    Python AI Engine                     
                    (FastAPI + LangGraph)                
                                                        
                        
         Groq API       pgvector RAG      GitHub API     
      (Llama-3.3-70b)  (384-dim vecs)   (code fetch)    

```

### LangGraph Pipeline (10 nodes)

```
fetch_codebase
     
score_risk              ← IsolationForest anomaly detection
     
identify_gaps           ← files with no test coverage
     
retrieve_context        ← pgvector RAG, similar past tests
     
generate_tests          ← Groq Llama + RAG few-shot examples
     
detect_defects          ← pattern-based vulnerability scanning
     
explain_and_score       ← AI root-cause analysis per defect
     
generate_fixes          ← CodegenerateAgent: Groq proposes a diff for each P0/P1 defect
     
apply_and_verify_fixes  ← clone, apply patch, re-run real tests, PR only if they pass
     
dispatch_results        ← saves to PostgreSQL, triggers auto-ingest + audit trail
```

> Scaling idea for higher commit volume: [hybrid cloud architecture proposal](docs/architecture/hybrid-cloud-proposal/README.md) (Kafka + serverless AI inference) — a design reference, not implemented.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS |
| Backend | Spring Boot 3.3, Java 17, JWT auth |
| AI Engine | Python 3.11, FastAPI, LangGraph |
| LLM | Groq API — Llama-3.3-70b-versatile (free, default) + Azure OpenAI (optional, defect explanations) |
| RAG | pgvector + sentence-transformers all-MiniLM-L6-v2 |
| Database | PostgreSQL 15 (Railway) + Flyway migrations (V1–V26) |
| Testing | Playwright TypeScript, JUnit 5, Testcontainers |
| CI/CD | GitHub Actions → Railway (backend), GitHub Pages (frontend) |

---

## Flyway Migrations

| Version | Description |
|---------|-------------|
| V1–V9 | Core schema: projects, test_runs, defects, risk_scores, pipeline_runs |
| V10–V18 | Story analysis, gap reports, generated tests, automation |
| V19–V21 | Seed data: SCIP/ARIA projects, admin users |
| **V22** | **RAG tables: pgvector extension, qaip_memory, rag_documents, scip_supplier_memory, aria_textbook_memory, aria_student_progress, zentravix_org_knowledge** |
| V23 | Add `github_token` to `framework_profiles` |
| V24 | `performance_test_results` — historical load-test trend data |
| V25 | Add `system` column to `performance_test_results` (multi-project support) |
| **V26** | **`autofix_audit` — CodegenerateAgent auto-fix attempt history** |

---

## MCP Servers

QAIP exposes Model Context Protocol servers for Claude integration:

```json
{
  "mcpServers": {
    "qaip": {
      "command": "npx",
      "args": ["@qaip/mcp-server"],
      "env": { "QAIP_API_URL": "https://testmind-production.up.railway.app" }
    }
  }
}
```

---

## Environment Variables

```env
DATABASE_URL=postgresql://...           # Railway PostgreSQL
GROQ_API_KEY=gsk_...                   # Free at console.groq.com
GITHUB_TOKEN=ghp_...                   # Needs repo + PR scope — CodegenerateAgent pushes branches and opens PRs
ANTHROPIC_API_KEY=sk-ant-...           # Optional: Claude for explain
EMBED_MODEL=all-MiniLM-L6-v2          # Default embedding model
BACKEND_URL=http://backend:8080       # Where the AI engine posts run results + autofix audit
```

---

## Local Development

```bash
# Backend
cd backend && ./mvnw spring-boot:run

# AI Engine
cd ai-engine
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Frontend
cd frontend && npm install && npm start
```
## Cost Optimisation — Rs.50 → Rs.8 per run (84% reduction)

When QAIP was first built, every pipeline node called Claude AI:
- Test generation → Claude
- Gap analysis → Claude  
- Failure explanation → Claude
- Report generation → Claude

**Result: Rs.50 per run. Not sustainable.**

### Three changes that fixed it:

**1. Model routing**
Groq (free tier, fast) for test generation — variance acceptable.
Claude only for defect explanations — faithfulness is business-critical,
validated by deepeval at 85% threshold.

**2. Prompt compression**
LangSmith tracing revealed Node 3 was sending the full Jira story
(~4,000 tokens) when only acceptance criteria were needed (~800 tokens).
- Node 3 latency: 42 seconds → 8 seconds
- Cost: dropped proportionally

**3. RAG context selection**
pgvector stores every previously-generated test case.
Each sprint retrieves 3 similar past tests and builds on proven patterns.
Fewer tokens sent. Better tests generated.

**Final result: Rs.50 → Rs.8 per run. 84% reduction.
deepeval faithfulness held at 94.2% throughout.**
---
## All Live Projects

| Platform      | Description                  | Live URL                                                  |
| ------------- | ----------------------------- | ---------------------------------------------------------- |
| **QAIP**      | QA Intelligent Platform       | **<https://bkumars22.github.io/QA-Intelligent-Platform>**  |
| **SCIP**      | Supply Chain Intelligence     | <https://bkumars22.github.io/SupplyChainPlatformProject>   |
| **ARIA**      | Free AI Tutor (35 languages)  | <https://bkumars22.github.io/ARIA>                         |
| **ZENTRAVIX** | Org Intelligence Platform     | <https://bkumars22.github.io/ZENTRAVIX>                    |

----

### Demo Access
Contact swamy.kumar02@gmail.com for demo credentials
Or use the guest view at the live dashboard link above
