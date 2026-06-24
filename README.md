# QA Intelligent Platform (AI-Driven) — QAIP

> Plug in your GitHub repo. Get risk scores, AI-generated tests, and defect explanations — fully autonomous. Now with RAG memory: tests improve every sprint.

[![CI](https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bkumars22/QA-Intelligent-Platform/actions)
[![Pages](https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/pages.yml/badge.svg)](https://bkumars22.github.io/QA-Intelligent-Platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Java 17](https://img.shields.io/badge/Java-17-orange?style=flat-square)](https://openjdk.org)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![Groq](https://img.shields.io/badge/AI-Groq%20Llama--3.3--70b-f97316?style=flat-square)](https://console.groq.com)
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

### Login Credentials

| Email | Password | Role |
|-------|----------|------|
| admin@qaip.io | Admin@2026 | Admin |
| dev@qaip.io | Dev@2026 | Developer |

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
8. **Stores everything in RAG** so the next sprint starts smarter

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

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    QAIP System                          │
│                                                         │
│  React 18 Frontend ──► Spring Boot 3.3 Backend          │
│       (GitHub Pages)       (Railway)                    │
│                              │                          │
│                    PostgreSQL + pgvector                 │
│                    (Railway managed)                    │
│                              │                          │
│                    Python AI Engine                     │
│                    (FastAPI + LangGraph)                │
│                              │                          │
│              ┌───────────────┼───────────────┐          │
│         Groq API       pgvector RAG      GitHub API     │
│      (Llama-3.3-70b)  (384-dim vecs)   (code fetch)    │
└─────────────────────────────────────────────────────────┘
```

### LangGraph Pipeline (8 nodes)

```
fetch_codebase
     │
score_risk          ← IsolationForest anomaly detection
     │
identify_gaps       ← files with no test coverage
     │
retrieve_context    ← NEW: pgvector RAG, similar past tests
     │
generate_tests      ← Groq Llama + RAG few-shot examples
     │
detect_defects      ← pattern-based vulnerability scanning
     │
explain_and_score   ← AI root-cause analysis per defect
     │
dispatch_results    ← saves to PostgreSQL, triggers auto-ingest
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS |
| Backend | Spring Boot 3.3, Java 17, JWT auth |
| AI Engine | Python 3.11, FastAPI, LangGraph |
| LLM | Groq API — Llama-3.3-70b-versatile (free) |
| RAG | pgvector + sentence-transformers all-MiniLM-L6-v2 |
| Database | PostgreSQL 15 (Railway) + Flyway migrations (V1–V22) |
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
GITHUB_TOKEN=ghp_...                   # GitHub PAT for repo access
ANTHROPIC_API_KEY=sk-ant-...           # Optional: Claude for explain
EMBED_MODEL=all-MiniLM-L6-v2          # Default embedding model
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

---

## All Live Projects

| Platform | Description | Live URL |
|----------|-------------|---------|
| **QAIP** | QA Intelligent Platform | **https://bkumars22.github.io/QA-Intelligent-Platform** |
| **SCIP** | Supply Chain Intelligence | https://bkumars22.github.io/SupplyChainPlatformProject |
| **ARIA** | Free AI Tutor (35 languages) | https://bkumars22.github.io/ARIA |
| **ZENTRAVIX** | Org Intelligence Platform | https://bkumars22.github.io/ZENTRAVIX |
