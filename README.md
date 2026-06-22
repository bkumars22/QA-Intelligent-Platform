# QA Intelligent Platform (AI-Driven)

> **Plug in your GitHub repo. Get risk scores, AI-generated tests, and defect explanations — in one command.**

[![CI](https://github.com/bkumars22/TestMind/actions/workflows/ci.yml/badge.svg)](https://github.com/bkumars22/TestMind/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Java 17](https://img.shields.io/badge/Java-17-orange?style=flat-square)](https://openjdk.org)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![Groq](https://img.shields.io/badge/AI-Groq%20Llama--3.3--70b-f97316?style=flat-square)](https://console.groq.com)

**GitHub:** [github.com/bkumars22/TestMind](https://github.com/bkumars22/TestMind) · **Built by:** B KumaraSwamy

---

## Live Demo

**Dashboard:** [https://testmind-production.up.railway.app](https://testmind-production.up.railway.app)

> Deploy your own in 5 minutes — see [Deploy to Railway](#deploy-to-railway) below.

| Credential | Value |
|-----------|-------|
| Email | `admin@testmind.io` |
| Password | `Admin@2026` |

Pre-loaded with 2 real projects (SCIP + ARIA), 4 defects, 6 risk scores, and full analysis history.

---

## What is QA Intelligent Platform?

QA Intelligent Platform (AI-Driven) is an AI-native QA layer you can plug into any live project without rewriting your stack.

It connects to your GitHub repo, reads changed files from every commit, scores risk using **IsolationForest ML**, generates missing Playwright tests, explains defects in plain language, and posts results to Jira and Slack — **fully autonomous**.

| Feature | How it works |
|---------|-------------|
| 🔴 **Risk Scoring** | IsolationForest ML — flags high-risk files with no labelled training data |
| 🤖 **AI Test Generation** | LangGraph 7-node agent generates Playwright TypeScript tests for untested high-risk files |
| 💡 **Defect Explanation** | Groq Llama-3.3-70b explains every defect: what broke, why, root cause, exact fix |
| 📊 **Quality Gate** | deepeval scores AI explanations ≥ 0.85 — rejects hallucinations automatically |
| 🎫 **Jira Integration** | P0/P1 defects auto-create Jira tickets with AI explanation as description |
| 💬 **Slack Alerts** | Risk summary + defect counts posted to #qa-alerts after every run |
| 📡 **Live Dashboard** | React dashboard with WebSocket live progress during analysis |
| 🔐 **Enterprise Security** | JWT HS512, BCrypt-12, RBAC 4 roles, OWASP headers, rate limiting |

---

## Quick Start

```bash
git clone https://github.com/bkumars22/TestMind.git
cd TestMind
cp .env.example .env
# Edit .env — minimum: GROQ_API_KEY + GITHUB_TOKEN + POSTGRES_PASSWORD + JWT_SECRET
docker compose up --build
```

Open **http://localhost:3000**

Login: `admin@testmind.io` / `Admin@2026`

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│           QA Intelligent Platform (AI-Driven)            │
├──────────────┬─────────────────────┬─────────────────────┤
│  Frontend    │  Backend            │  AI Engine          │
│  React 18    │  Spring Boot 3.2    │  FastAPI + Python   │
│  TypeScript  │  Java 17 · 18 APIs  │  LangGraph 7 nodes  │
│  Tailwind    │  JWT · RBAC · AOP   │  Groq Llama-3.3-70b │
├──────────────┴─────────────────────┴─────────────────────┤
│                  MCP Layer (5 servers)                   │
│  Playwright · GitHub · Filesystem · Jira · Slack         │
├──────────────────────────────────────────────────────────┤
│  ML Layer: IsolationForest · deepeval · scikit-learn     │
├──────────────────────────────────────────────────────────┤
│  PostgreSQL 15 · Flyway migrations · Redis               │
└──────────────────────────────────────────────────────────┘
```

## LangGraph Agent — 7 Nodes

```
fetch_codebase → score_risk → identify_gaps → generate_tests
       → detect_defects → explain_and_score → dispatch_results
```

| Node | Action |
|------|--------|
| 1. fetch_codebase | Clone/fetch changed files from last commit via GitHub API |
| 2. score_risk | IsolationForest per file — flags anomalies with no training data |
| 3. identify_gaps | Map source → test files, find untested high-risk code |
| 4. generate_tests | Groq LLM generates Playwright TypeScript tests per gap |
| 5. detect_defects | Analyse test results, assign P0/P1/P2/P3 severity |
| 6. explain_and_score | Groq explains each defect + deepeval quality gate (≥ 0.85) |
| 7. dispatch_results | Parallel: Jira tickets + Slack message + JSON report + backend callback |

---

## Real-World Integration — SCIP and ARIA

QA Intelligent Platform (AI-Driven) is actively running against two production projects. This section documents exactly how to connect it to your own live codebase.

### Why this matters

Every defect found, every risk score generated, every AI explanation produced against a real project becomes proof that TestMind works in production — not in theory.

| TestMind Action | What it finds |
|----------------|--------------|
| Risk Score every file | Flags auth files, DB migration scripts, ML model code as HIGH RISK |
| Identify coverage gaps | Maps all endpoints vs existing tests — finds untested paths |
| Generate missing tests | Writes Playwright TypeScript tests for every untested endpoint |
| Detect defects | Catches regressions the existing test suite misses |
| Explain defects in plain English | No more cryptic stack traces — AI explains every failure |
| Score explanation quality | deepeval validates each AI explanation at ≥ 94.2% consistency |
| Raise Jira tickets | Auto-creates P0/P1 tickets with steps to reproduce |
| Post to Slack | Sends risk summary + defect count to #qa-alerts after every run |
| Save full report | JSON + HTML report saved to filesystem as a live demo artifact |

---

### Project 1 — SCIP (Supply Chain Intelligence Platform)

**GitHub:** [github.com/bkumars22/SupplyChainPlatformProject](https://github.com/bkumars22/SupplyChainPlatformProject)  
**Live:** [bkumars22.github.io/SupplyChainPlatformProject](https://bkumars22.github.io/SupplyChainPlatformProject)  
**Stack:** Java 17, Spring Boot, React 18, Python FastAPI, IsolationForest, LangGraph

#### Step 1 — Register SCIP

```bash
curl -X POST http://localhost:8080/api/projects \
  -H "Authorization: Bearer {your-jwt}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SCIP — Supply Chain Intelligence Platform",
    "repo_url": "https://github.com/bkumars22/SupplyChainPlatformProject",
    "github_token": "${GITHUB_TOKEN}",
    "tech_stack": "Java 17, Spring Boot, React 18, Python FastAPI",
    "base_url": "https://bkumars22.github.io/SupplyChainPlatformProject",
    "test_command": "npx playwright test",
    "test_dir": "tests/"
  }'
```

**SCIP critical file patterns** (added to IsolationForest with 2x weight):
- `**/security/**` — Spring Security config
- `**/auth/**` — JWT, BCrypt authentication
- `**/migration/**` — Flyway SQL scripts
- `**IsolationForest**` — the ML model itself

> Reason: SCIP had a P0 BCrypt null hash bug in production. TestMind must catch this class of bug automatically.

#### Step 2 — Run Analysis on SCIP

```bash
# Get the project ID from registration response
curl -X POST http://localhost:8080/api/projects/{scip-project-id}/run-analysis \
  -H "Authorization: Bearer {your-jwt}"

# Watch live progress
open http://localhost:3000/test-runs/{run-id}
```

#### Expected findings from SCIP

**High-risk files IsolationForest will flag:**
- `SecurityConfig.java` — Spring Security setup (critical auth code)
- `JwtTokenProvider.java` — JWT generation and validation
- `UserAuthController.java` — login endpoint (historical P0 bug location)
- `SupplierRiskService.py` — IsolationForest ML model
- `LangGraphAgent.py` — 5-node agent orchestration
- `V1__create_users.sql` through `V6` — all Flyway migrations

**Coverage gaps TestMind will find:**
- Voice command endpoints — 25 commands, likely untested at API level
- React Native JWT sync — mobile token sharing with web app
- deepeval quality gate — is the 94.2% score enforced in CI?
- IsolationForest null/empty input — boundary conditions
- AOP audit trail — are all state changes actually logged?
- RBAC edge cases — can VIEWER role escalate to ADMIN via API?

**SCIP-specific tests TestMind generates:**

```typescript
// test-scip-auth-boundary.spec.ts
test('null password returns 400 not 500', async ({ request }) => {
  const res = await request.post('/api/auth/login', {
    data: { email: 'test@scip.io', password: null }
  });
  expect(res.status()).toBe(400);
});

test('VIEWER cannot access ADMIN endpoint', async ({ request }) => {
  const res = await request.get('/api/admin/users', {
    headers: { Authorization: `Bearer ${viewerToken}` }
  });
  expect(res.status()).toBe(403);
});
```

---

### Project 2 — ARIA (Adaptive Real-time Intelligence for Anyone)

**GitHub:** [github.com/bkumars22/ARIA](https://github.com/bkumars22/ARIA)  
**Stack:** Claude AI, LangGraph, React 18, Spring Boot, FastAPI, Whisper STT, 35 languages

#### Step 1 — Register ARIA

```bash
curl -X POST http://localhost:8080/api/projects \
  -H "Authorization: Bearer {your-jwt}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ARIA — Adaptive Real-time Intelligence for Anyone",
    "repo_url": "https://github.com/bkumars22/ARIA",
    "github_token": "${GITHUB_TOKEN}",
    "tech_stack": "Claude AI, LangGraph, React 18, Spring Boot, FastAPI, Whisper",
    "base_url": "https://bkumars22.github.io/ARIA",
    "test_command": "npx playwright test",
    "test_dir": "tests/"
  }'
```

**ARIA critical file patterns** (2x IsolationForest weight):
- `**/socratic/**` — Socratic teaching engine (must never give direct answers)
- `**/adaptive/**` — difficulty adjustment logic (35%/80% thresholds)
- `**/multilang/**` — 35 language support
- `**/whisper/**` — STT input processing
- `**/langgraph/**` — 6-node agent

> ARIA's P0 class: if the Socratic engine gives a direct answer, the entire educational mission fails. TestMind detects this automatically on every code change.

#### Step 2 — Run Analysis on ARIA

```bash
curl -X POST http://localhost:8080/api/projects/{aria-project-id}/run-analysis \
  -H "Authorization: Bearer {your-jwt}"
```

#### ARIA-specific tests TestMind generates

```typescript
// test-socratic-engine.spec.ts
test('ARIA never gives a direct answer to What is 2+2?', async ({ page }) => {
  await page.fill('[data-testid="question-input"]', 'What is 2+2?');
  await page.click('[data-testid="ask-button"]');
  const response = await page.locator('[data-testid="ai-response"]').textContent();
  expect(response).not.toMatch(/\b4\b/);
  expect(response).toMatch(/\?/); // must respond with a guiding question
});

test('ARIA holds boundary when pressed for direct answer', async ({ page }) => {
  await page.fill('[data-testid="question-input"]', 'Just tell me the answer');
  await page.click('[data-testid="ask-button"]');
  const response = await page.locator('[data-testid="ai-response"]').textContent();
  expect(response).not.toMatch(/the answer is/i);
});

// test-adaptive-difficulty.spec.ts
test('difficulty drops when student scores below 35%', async ({ page }) => {
  await simulateScore(page, 30);
  await expect(page.locator('[data-testid="difficulty-level"]')).toContainText('Beginner');
});

test('difficulty rises when student scores above 80%', async ({ page }) => {
  await simulateScore(page, 85);
  await expect(page.locator('[data-testid="difficulty-level"]')).toContainText('Advanced');
});

// test-rbac-aria.spec.ts
test('student cannot access another student data (IDOR)', async ({ request }) => {
  const res = await request.get('/api/students/other-student-id/progress', {
    headers: { Authorization: `Bearer ${studentToken}` }
  });
  expect(res.status()).toBe(403);
});
```

#### Expected coverage gaps in ARIA
- 35 language TTS validation — likely only English tested end-to-end
- Adaptive threshold accuracy — exact 35% and 80% boundary tests
- IDOR vulnerability — student accessing another student's data
- Whisper STT for Indian regional languages (Hindi, Tamil, Kannada)
- Parent weekly report content accuracy — AI-generated report validation
- Corrupt file upload handling — error path rarely tested

---

### Combined SCIP + ARIA Comparison Report

After running both analyses, generate the comparison dashboard:

```bash
# View combined report
open reports/testmind-scip-aria-comparison-$(date +%Y-%m-%d).html
```

The report includes:

| Metric | SCIP | ARIA |
|--------|------|------|
| Total files scanned | — | — |
| High-risk files | — | — |
| Coverage gaps found | — | — |
| Tests generated | — | — |
| Defects detected | — | — |
| P0 defects | — | — |
| deepeval avg score | — | — |
| Jira tickets raised | — | — |

> Run both analyses and the report auto-populates with real numbers.

---

## API Reference

Swagger UI: **http://localhost:8080/swagger-ui.html**

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Returns JWT token |
| POST | `/api/auth/register` | Create user (ADMIN only) |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List all projects |
| POST | `/api/projects` | Register a new repo |
| GET | `/api/projects/{id}` | Project detail + MCP status |
| DELETE | `/api/projects/{id}` | Remove project |
| POST | `/api/projects/{id}/run-analysis` | Trigger full 7-node LangGraph analysis |

### Test Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/test-runs` | List runs (filterable by project/status) |
| GET | `/api/test-runs/{id}` | Run detail + live WebSocket progress |
| GET | `/api/test-runs/{id}/report` | Download JSON/HTML report |

### Defects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/defects` | List defects (filter by severity/status) |
| GET | `/api/defects/{id}` | Defect + AI explanation + deepeval score |
| PATCH | `/api/defects/{id}/status` | Update defect status |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Total projects, runs, defects, avg risk |
| GET | `/api/risk-scores` | Risk heatmap data per file |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Free at [console.groq.com](https://console.groq.com) |
| `GITHUB_TOKEN` | ✅ | PAT with `repo` + `issues` scope |
| `POSTGRES_PASSWORD` | ✅ | Any strong password |
| `JWT_SECRET` | ✅ | 64-char random hex string |
| `JIRA_URL` | Optional | e.g. `https://yourorg.atlassian.net` |
| `JIRA_EMAIL` | Optional | Your Atlassian email |
| `JIRA_API_TOKEN` | Optional | From Atlassian profile → Security |
| `JIRA_PROJECT_KEY` | Optional | e.g. `TM` |
| `SLACK_BOT_TOKEN` | Optional | `xoxb-...` token from Slack app |
| `SLACK_CHANNEL` | Optional | e.g. `#qa-alerts` |

---

## Deploy to Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select `bkumars22/TestMind`
3. Add variables from `.env.example`
4. Railway auto-detects Docker Compose and deploys all 7 services
5. Your live URL: `https://testmind-production.up.railway.app`

---

## Running Tests

```bash
# Backend unit tests
cd backend && mvn test

# AI Engine unit tests (60 tests — all LangGraph nodes + IsolationForest)
cd ai-engine && pip install -r requirements.txt && pytest tests/ -v

# Frontend type check
cd frontend && npm install && npm run type-check

# Playwright E2E (requires running stack)
docker compose up -d
cd tests && npm install && npx playwright test
```

---

## Project Structure

```
TestMind/
├── backend/                  # Spring Boot 3.2 — 18 REST endpoints
│   └── src/main/java/com/testmind/
│       ├── controller/       # 7 controllers
│       ├── service/          # Business logic + AiEngineClient (WebFlux)
│       ├── security/         # JWT HS512, BCrypt-12, RBAC
│       ├── model/            # 7 JPA entities
│       └── resources/db/migration/  # Flyway V1–V8
├── ai-engine/                # FastAPI + LangGraph 7-node agent
│   ├── main.py               # 5 endpoints + rate limiter
│   ├── agents/langgraph_agent.py  # Full autonomous QA agent
│   └── tests/                # 60 unit tests
├── frontend/                 # React 18 + TypeScript + Tailwind
│   └── src/
│       ├── pages/            # 6 pages — Login, Dashboard, Projects, etc.
│       ├── components/       # Layout, SeverityBadge, StatusBadge, McpStatusDot
│       ├── hooks/            # useAuth, useWebSocket
│       └── services/api.ts   # All API calls, token in memory (not localStorage)
├── tests/e2e/                # Playwright test suite (5 spec files)
├── infra/nginx/              # Rate limiting, OWASP security headers, SPA proxy
├── mcp-servers/config.json   # All 5 MCP server configurations
├── .github/workflows/ci.yml  # 5-job CI: backend · ai-engine · frontend · e2e · deploy
└── docker-compose.yml        # 7 services: postgres · redis · backend · ai-engine · frontend · nginx · mcp
```

---

## Security

- JWT HS512 with 24-hour expiry
- BCrypt cost-12 password hashing
- RBAC: ADMIN / QA_LEAD / QA_ENGINEER / VIEWER — enforced at every endpoint
- AOP audit trail — every state-changing action logged with user + timestamp
- Token stored in JS module variable — never in localStorage or sessionStorage
- Nginx rate limiting: 10 req/s per IP on all API routes
- OWASP headers: `X-Frame-Options DENY`, `Content-Security-Policy`, `X-Content-Type-Options nosniff`
- Parameterised queries throughout — no SQL injection vectors

---

## Built by

**B KumaraSwamy** — [github.com/bkumars22](https://github.com/bkumars22) · Bangalore, India · 2026

swamy.kumar02@gmail.com

*"89% of teams experiment with AI in QA. Only 15% reach enterprise scale. QA Intelligent Platform closes that gap."*

---

**MIT License** — free to use, modify, and distribute.
