# QA Intelligent Platform (AI-Driven)

> **Plug in your GitHub repo. Get risk scores, AI-generated tests, and defect explanations — fully autonomous.**

[![CI](https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bkumars22/QA-Intelligent-Platform/actions)
[![Pages](https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/pages.yml/badge.svg)](https://bkumars22.github.io/QA-Intelligent-Platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Java 17](https://img.shields.io/badge/Java-17-orange?style=flat-square)](https://openjdk.org)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![Groq](https://img.shields.io/badge/AI-Groq%20Llama--3.3--70b-f97316?style=flat-square)](https://console.groq.com)

**GitHub:** [github.com/bkumars22/QA-Intelligent-Platform](https://github.com/bkumars22/QA-Intelligent-Platform) · **Built by:** B KumaraSwamy · Bangalore, India

---

## Live Access

| What | URL |
|------|-----|
| **QAIP Dashboard** (GitHub Pages — always on) | [bkumars22.github.io/QA-Intelligent-Platform](https://bkumars22.github.io/QA-Intelligent-Platform) |
| **QAIP Backend API** (Railway) | [testmind-production.up.railway.app](https://testmind-production.up.railway.app) |
| **SCIP — Supply Chain Platform** | [bkumars22.github.io/SupplyChainPlatformProject](https://bkumars22.github.io/SupplyChainPlatformProject) |
| **ARIA — Adaptive Learning AI** | [bkumars22.github.io/ARIA](https://bkumars22.github.io/ARIA) |

### Login Credentials

| Field | Value |
|-------|-------|
| Email | `admin@qaip.io` |
| Password | `Admin@2026` |

Pre-loaded with SCIP + ARIA as registered projects, 4 defects, 6 risk scores, and full analysis history.

---

## What is QAIP?

QA Intelligent Platform is an **AI-native QA umbrella** over your live projects. It connects to any GitHub repo, scores every file for risk using IsolationForest ML, generates missing Playwright tests via a 7-stage LangGraph agent, explains defects in plain English, raises Jira tickets, and posts Slack alerts — all triggered automatically on every git push.

QAIP currently monitors two live production projects: **SCIP** and **ARIA**.

| Feature | How it works |
|---------|-------------|
| 🔴 **Risk Scoring** | IsolationForest ML — no labelled training data needed |
| 🤖 **7-Stage QA Pipeline** | LangGraph agent: story intake → gap analysis → test gen → execution → defect triage → AI explanation → dispatch |
| ⚡ **Automation Execution** | Connect your Playwright or Selenium framework repo — QAIP analyses its style and generates matching tests |
| 💡 **Defect Explanation** | Groq Llama-3.3-70b: root cause + business impact + exact fix recommendation per defect |
| 📊 **Quality Gate** | deepeval scores AI explanations ≥ 0.85 — auto-rejects hallucinations |
| 🎫 **Jira Auto-Tickets** | P0/P1 defects create Jira tickets with AI explanation as description |
| 💬 **Slack Alerts** | Risk summary + defect count to #qa-alerts after every run |
| 📡 **Live Dashboard** | WebSocket real-time progress during analysis |
| 🔗 **GitHub Webhooks** | Push to SCIP or ARIA → QAIP auto-triggers analysis |
| 🔐 **Enterprise Security** | JWT HS512, BCrypt-12, RBAC 4 roles, OWASP headers, rate limiting |

---

## Quick Start (Local — Docker)

```bash
git clone https://github.com/bkumars22/QA-Intelligent-Platform.git
cd QA-Intelligent-Platform
cp .env.example .env
# Minimum required: set GROQ_API_KEY (free at console.groq.com)
# Everything else has safe local defaults
docker compose up --build
```

Open **http://localhost:3000**

Login: `admin@qaip.io` / `Admin@2026`

> SCIP and ARIA are seeded automatically on first startup (Flyway V19 migration). No manual setup needed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              QA Intelligent Platform (AI-Driven)            │
│                                                             │
│   SCIP ────────────────────────────────────────── ARIA      │
│   Supply Chain Platform          Adaptive Learning AI       │
│   bkumars22/SupplyChainPlatform  bkumars22/ARIA             │
├──────────────┬──────────────────────┬───────────────────────┤
│  Frontend    │  Backend             │  AI Engine            │
│  React 18    │  Spring Boot 3.2     │  FastAPI + Python 3.11│
│  TypeScript  │  Java 17 · REST API  │  LangGraph 7-stage    │
│  TailwindCSS │  JWT · RBAC · AOP    │  Groq Llama-3.3-70b   │
├──────────────┴──────────────────────┴───────────────────────┤
│                   MCP Layer (5 servers)                     │
│     Playwright · GitHub · Filesystem · Jira · Slack         │
├─────────────────────────────────────────────────────────────┤
│    ML: IsolationForest · deepeval · scikit-learn            │
├─────────────────────────────────────────────────────────────┤
│    PostgreSQL 15 · Flyway V1–V19 · Redis                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 7-Stage QA Pipeline (LangGraph Agent)

```
Story Intake → Gap Analysis → Test Generation → Human Approval
     → Test Execution → Defect Triage → Results Dispatch
```

| Stage | Node | Action |
|-------|------|--------|
| 1 | `ingest_story` | Fetch Jira story — title, acceptance criteria, linked files |
| 2 | `analyze_gaps` | IsolationForest risk score per file, map source → test coverage |
| 3 | `generate_tests` | Groq generates Playwright TypeScript tests for every gap |
| — | **AWAITING_APPROVAL** | Pipeline pauses — human reviews generated tests before execution |
| 4 | `execute_tests` | Playwright MCP runs tests (simulation fallback if MCP unavailable) |
| 5 | `triage_defects` | Classify failures P0/P1/P2/P3, assign severity |
| 6 | `explain_and_score` | Groq explains each defect + deepeval quality gate ≥ 0.85 |
| 7 | `dispatch_results` | Parallel: Jira tickets + Slack alert + HTML report + backend callback |

> The pipeline pauses at **Stage 3** for human approval. Resume via `POST /api/pipeline/{id}/approve`.

---

## ⚡ Automation Execution Loop

Connect your existing Playwright or Selenium framework repo to QAIP for framework-aware test generation and execution.

### How to use

1. Open any project → **⚡ Automation** tab
2. Select **Playwright** or **Selenium**
3. Enter your framework GitHub repo URL → click **Connect**
   - QAIP fetches and analyses your framework: base class, imports, hook patterns, naming conventions
4. Click **Generate Suite** — enter test case titles
   - QAIP generates code matching your exact framework style
5. Click **Execute** — tests run, results stream in real time
6. Each failure gets: root cause · business impact · fix recommendation · severity badge
7. Shareable HTML report auto-generated when all tests pass

---

## Monitored Projects

### SCIP — Supply Chain Intelligence Platform

| Field | Value |
|-------|-------|
| GitHub | [github.com/bkumars22/SupplyChainPlatformProject](https://github.com/bkumars22/SupplyChainPlatformProject) |
| Live | [bkumars22.github.io/SupplyChainPlatformProject](https://bkumars22.github.io/SupplyChainPlatformProject) |
| Stack | Java 17 + Spring Boot + React 18 + Python FastAPI + IsolationForest + LangGraph + PostgreSQL |
| P0 Watch | BCrypt null-password hash — QAIP tests this on every push |

**Register SCIP via API:**

```bash
curl -X POST https://testmind-production.up.railway.app/api/projects \
  -H "Authorization: Bearer {your-jwt}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SCIP — Supply Chain Intelligence Platform",
    "repoUrl": "https://github.com/bkumars22/SupplyChainPlatformProject",
    "techStack": "Java 17 + Spring Boot + React 18 + Python FastAPI + IsolationForest + PostgreSQL"
  }'
```

**SCIP tests QAIP auto-generates:**

```typescript
// test-scip-auth-boundary.spec.ts
test('null password must return 400 not 500', async ({ request }) => {
  const res = await request.post('/supchain/api/auth/login', {
    data: { email: 'test@scip.io', password: null }
  });
  expect(res.status()).toBe(400);  // P0: BCrypt null hash bug class
});

test('VIEWER role cannot access ADMIN endpoint', async ({ request }) => {
  const res = await request.get('/supchain/api/admin/users', {
    headers: { Authorization: `Bearer ${viewerToken}` }
  });
  expect(res.status()).toBe(403);
});

test('IsolationForest returns scores for all files', async ({ request }) => {
  const res = await request.post('/supchain/api/risk/score', {
    data: { files: ['SecurityConfig.java', 'JwtTokenProvider.java'] }
  });
  const body = await res.json();
  expect(body.scores.length).toBeGreaterThan(0);
});
```

**High-risk files IsolationForest flags in SCIP:**
- `SecurityConfig.java` — Spring Security (critical auth code)
- `JwtTokenProvider.java` — JWT generation and validation
- `UserAuthController.java` — login endpoint (P0 bug location)
- `SupplierRiskService.py` — IsolationForest ML model
- `V1__create_users.sql` through `V8__seed_demo_data.sql` — all migrations

---

### ARIA — Adaptive Real-time Intelligence for Anyone

| Field | Value |
|-------|-------|
| GitHub | [github.com/bkumars22/ARIA](https://github.com/bkumars22/ARIA) |
| Live | [bkumars22.github.io/ARIA](https://bkumars22.github.io/ARIA) |
| Stack | Claude AI + LangGraph + React 18 + Spring Boot + FastAPI + Whisper STT + 35 languages + PostgreSQL |
| P0 Watch | Socratic engine must never give direct answers — tested on every push |

**Register ARIA via API:**

```bash
curl -X POST https://testmind-production.up.railway.app/api/projects \
  -H "Authorization: Bearer {your-jwt}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ARIA — Adaptive Real-time Intelligence for Anyone",
    "repoUrl": "https://github.com/bkumars22/ARIA",
    "techStack": "Claude AI + LangGraph + React 18 + Spring Boot + FastAPI + Whisper STT + PostgreSQL"
  }'
```

**ARIA tests QAIP auto-generates:**

```typescript
// test-socratic-engine.spec.ts — P0: engine must NEVER give direct answers
test('ARIA responds with a question, not an answer', async ({ page }) => {
  await page.goto('https://bkumars22.github.io/ARIA');
  await page.fill('[data-testid="question-input"]', 'What is 2+2?');
  await page.click('[data-testid="ask-button"]');
  const response = await page.locator('[data-testid="ai-response"]').textContent();
  expect(response).not.toMatch(/\b4\b/);
  expect(response).toMatch(/\?/);  // Must always respond with a guiding question
});

test('ARIA holds boundary under pressure', async ({ page }) => {
  await page.fill('[data-testid="question-input"]', 'Just tell me the answer directly');
  await page.click('[data-testid="ask-button"]');
  const response = await page.locator('[data-testid="ai-response"]').textContent();
  expect(response).not.toMatch(/the answer is/i);
});

// test-adaptive-difficulty.spec.ts
test('difficulty drops below 35% threshold', async ({ page }) => {
  await simulateScore(page, 30);
  await expect(page.locator('[data-testid="difficulty-level"]')).toContainText('Beginner');
});

test('difficulty rises above 80% threshold', async ({ page }) => {
  await simulateScore(page, 85);
  await expect(page.locator('[data-testid="difficulty-level"]')).toContainText('Advanced');
});

// test-rbac-aria.spec.ts
test('student cannot read another student data (IDOR)', async ({ request }) => {
  const res = await request.get('/aria/api/students/other-id/progress', {
    headers: { Authorization: `Bearer ${studentToken}` }
  });
  expect(res.status()).toBe(403);
});
```

**Coverage gaps QAIP finds in ARIA:**
- 35-language TTS — only English tested end-to-end currently
- Adaptive boundary accuracy — exact 35% and 80% threshold tests
- IDOR vulnerability — cross-student data access
- Whisper STT for Hindi, Tamil, Kannada, Telugu input
- Parent weekly report accuracy validation
- Corrupt file upload error paths

---

## GitHub Webhooks — Auto-trigger on Push

Push to SCIP or ARIA → QAIP runs analysis automatically.

**Register the webhook on each repo:**

1. Go to repo → **Settings → Webhooks → Add webhook**
2. Payload URL: `https://testmind-production.up.railway.app/api/webhook/github`
3. Content type: `application/json`
4. Events: **Just the push event**
5. Click **Add webhook**

| Repo | Webhook settings URL |
|------|---------------------|
| SCIP | [SupplyChainPlatformProject/settings/hooks](https://github.com/bkumars22/SupplyChainPlatformProject/settings/hooks) |
| ARIA | [ARIA/settings/hooks](https://github.com/bkumars22/ARIA/settings/hooks) |

---

## Combined SCIP + ARIA Report

After running analysis on both projects, generate the unified cross-project report:

```bash
curl -X POST https://testmind-production.up.railway.app/api/ai/unified-report \
  -H "Authorization: Bearer {your-jwt}"
```

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

> Run both analyses and the table auto-populates with real numbers from your codebase.

---

## API Reference

**Swagger UI:** [testmind-production.up.railway.app/swagger-ui.html](https://testmind-production.up.railway.app/swagger-ui.html)  
**Local:** http://localhost:8080/swagger-ui.html

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
| POST | `/api/projects/{id}/run-analysis` | Trigger 7-stage LangGraph analysis |

### QA Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/pipeline` | List pipeline runs |
| POST | `/api/pipeline/start` | Start new pipeline run from Jira story |
| GET | `/api/pipeline/{id}` | Pipeline run detail + stage progress |
| POST | `/api/pipeline/{id}/approve` | Resume pipeline after Stage 3 human review |
| GET | `/api/pipeline/{id}/code` | Download generated test code |
| GET | `/api/pipeline/{id}/executions` | View test execution results |

### Automation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/automation/projects/{id}/frameworks` | List connected frameworks |
| POST | `/api/automation/frameworks/connect` | Connect Playwright/Selenium repo |
| POST | `/api/automation/generate-code` | Generate framework-aware test suite |
| POST | `/api/automation/execute/{id}` | Execute generated tests |
| GET | `/api/automation/projects/{id}/executions` | Execution history |
| GET | `/api/automation/executions/{id}/results` | Per-test results with AI explanations |
| GET | `/api/automation/reports/{token}` | View shareable HTML report (public) |

### Test Runs & Defects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/test-runs` | List runs (filter by project/status) |
| GET | `/api/test-runs/{id}` | Run detail + WebSocket live progress |
| GET | `/api/defects` | List defects (filter by severity/status) |
| GET | `/api/defects/{id}` | Defect + AI explanation + deepeval score |
| PATCH | `/api/defects/{id}/status` | Update defect status |

### Dashboard & Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Total projects, runs, defects, avg risk |
| GET | `/api/risk-scores` | Risk heatmap data per file |
| POST | `/api/webhook/github` | GitHub push webhook (no auth — public) |
| POST | `/api/ai/scip/intelligence-check` | Run SCIP-specific P0 tests |
| POST | `/api/ai/aria/intelligence-check` | Run ARIA-specific Socratic engine tests |
| POST | `/api/ai/unified-report` | Generate combined SCIP + ARIA executive report |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Recommended | Free at [console.groq.com](https://console.groq.com) — AI features fall back gracefully without it |
| `GITHUB_TOKEN` | Optional | PAT with `repo` scope — higher rate limit for repo analysis |
| `POSTGRES_PASSWORD` | ✅ | Any strong password |
| `JWT_SECRET` | ✅ | 64-char random hex string |
| `JIRA_URL` | Optional | e.g. `https://yourorg.atlassian.net` |
| `JIRA_EMAIL` | Optional | `swamy.kumar02@gmail.com` |
| `JIRA_API_TOKEN` | Optional | From Atlassian profile → Security |
| `SLACK_BOT_TOKEN` | Optional | `xoxb-...` token from Slack app |
| `SLACK_CHANNEL` | Optional | e.g. `#qa-alerts` |

---

## Deploy to Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select **`bkumars22/QA-Intelligent-Platform`**
3. Add variables from `.env.example` (only `POSTGRES_PASSWORD` and `JWT_SECRET` are required)
4. Railway auto-detects Docker Compose and deploys all services
5. Set your live URL as `PROD_URL` environment variable

> **Note:** If you see old content, reconnect the GitHub repo in Railway dashboard (Settings → Source Repo) after any GitHub repo rename.

---

## GitHub Pages Deployment

All three projects deploy their frontends automatically on every push to `main`:

| Project | Pages Workflow | Live URL |
|---------|---------------|----------|
| QAIP | `.github/workflows/pages.yml` | [bkumars22.github.io/QA-Intelligent-Platform](https://bkumars22.github.io/QA-Intelligent-Platform) |
| SCIP | `.github/workflows/pages.yml` | [bkumars22.github.io/SupplyChainPlatformProject](https://bkumars22.github.io/SupplyChainPlatformProject) |
| ARIA | `.github/workflows/deploy.yml` | [bkumars22.github.io/ARIA](https://bkumars22.github.io/ARIA) |

> QAIP's GitHub Pages frontend connects to the Railway backend API automatically.

---

## Running Tests

```bash
# Backend unit tests
cd backend && mvn test

# AI Engine tests
cd ai-engine && pip install -r requirements.txt && pytest tests/ -v

# Frontend type check
cd frontend && npm install && npm run type-check

# Full E2E (requires running stack)
docker compose up -d
cd tests && npm install && npx playwright test
```

---

## Project Structure

```
QA-Intelligent-Platform/
├── .github/workflows/
│   ├── ci.yml              # 5-job CI: backend · ai-engine · frontend · e2e · deploy
│   └── pages.yml           # GitHub Pages: builds React + deploys to gh-pages branch
│
├── backend/                # Spring Boot 3.2 — Java 17
│   └── src/main/java/com/testmind/
│       ├── controller/     # 10 controllers: Auth, Project, TestRun, Defect,
│       │                   #   Pipeline, TestCase, Automation, Webhook, Dashboard, MCP
│       ├── service/        # PipelineService, AutomationService, AiEngineClient, AutomationAiClient
│       ├── security/       # JWT HS512, BCrypt-12, SecurityConfig, RBAC
│       ├── model/          # 17 JPA entities (incl. FrameworkProfile, AutomationExecution,
│       │                   #   AutomationResult, GeneratedReport)
│       └── resources/db/migration/
│           ├── V1–V8       # Core tables + demo seed data
│           ├── V9–V14      # Pipeline, story analysis, gap reports, test cases, code
│           ├── V15–V18     # Automation: framework profiles, executions, results, reports
│           └── V19         # Seeds SCIP + ARIA as pre-registered projects
│
├── ai-engine/              # FastAPI + Python 3.11
│   ├── main.py             # 12 endpoints: analyze, pipeline stages, automation,
│   │                       #   SCIP intelligence, ARIA intelligence, unified report
│   ├── agents/
│   │   ├── pipeline_agent.py       # LangGraph 7-stage QA pipeline
│   │   └── real_agents_bridge.py   # Bridge to production agents
│   └── tests/              # pytest test suite
│
├── frontend/               # React 18 + TypeScript + TailwindCSS + Vite
│   └── src/
│       ├── pages/          # 11 pages: Login, UnifiedDashboard, Projects,
│       │                   #   ProjectDetail, DefectDetail, TestRun,
│       │                   #   Pipeline, PipelineDetail, PipelineExecution, PipelineCode
│       ├── components/     # Layout, AutomationTab, StatusBadge, SeverityBadge, McpStatusDot
│       ├── hooks/          # useAuth (localStorage session), useWebSocket
│       └── services/       # api.ts, pipelineApi.ts, automationApi.ts
│
├── tests/                  # Playwright E2E test suite
├── infra/nginx/            # Rate limiting, OWASP headers, SPA proxy
├── mcp-servers/            # 5 MCP server configs (Playwright, GitHub, Filesystem, Jira, Slack)
├── .env.example            # All environment variables documented
├── docker-compose.yml      # 6 services: postgres · backend · ai-engine · frontend · nginx · mcp
└── README.md               # This file
```

---

## Security

| Control | Detail |
|---------|--------|
| Auth | JWT HS512, 24-hour expiry |
| Passwords | BCrypt cost-12 |
| Roles | ADMIN / QA_LEAD / QA_ENGINEER / VIEWER — enforced at every endpoint |
| Session | Token + user stored in `localStorage` under key `qaip_auth` — survives page refresh |
| Audit | AOP intercepts every state-changing action — logs user + timestamp |
| Network | Nginx: 10 req/s per IP rate limit on all `/api` routes |
| Headers | `X-Frame-Options: DENY`, `Content-Security-Policy`, `X-Content-Type-Options: nosniff` |
| DB | Parameterised queries throughout — zero SQL injection vectors |
| Webhooks | `/api/webhook/github` is public (no auth) — validates `X-GitHub-Event` header |

---

## Built by

**B KumaraSwamy** — [github.com/bkumars22](https://github.com/bkumars22) · Bangalore, India · 2026

[swamy.kumar02@gmail.com](mailto:swamy.kumar02@gmail.com)

*"89% of teams experiment with AI in QA. Only 15% reach enterprise scale. QA Intelligent Platform closes that gap."*

---

**MIT License** — free to use, modify, and distribute.
