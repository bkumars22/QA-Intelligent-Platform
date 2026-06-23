# QA Intelligent Platform (AI-Driven)

Plug in your GitHub repo. Get risk scores, AI-generated tests, and defect explanations — fully autonomous.

[![CI](https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bkumars22/QA-Intelligent-Platform/actions)
[![Pages](https://github.com/bkumars22/QA-Intelligent-Platform/actions/workflows/pages.yml/badge.svg)](https://bkumars22.github.io/QA-Intelligent-Platform)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Java 17](https://img.shields.io/badge/Java-17-orange?style=flat-square)](https://openjdk.org)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![Groq](https://img.shields.io/badge/AI-Groq%20Llama--3.3--70b-f97316?style=flat-square)](https://console.groq.com)

GitHub: [github.com/bkumars22/QA-Intelligent-Platform](https://github.com/bkumars22/QA-Intelligent-Platform)
Built by: B KumaraSwamy — Bangalore, India

---

## Live Access

| Project | URL |
|---------|-----|
| QAIP Dashboard | https://bkumars22.github.io/QA-Intelligent-Platform |
| SCIP — Supply Chain Platform | https://bkumars22.github.io/SupplyChainPlatformProject |
| ARIA — Adaptive Learning AI | https://bkumars22.github.io/ARIA |

### Login Credentials

| Email | Password | Notes |
|-------|----------|-------|
| admin@qaip.io | Admin@2026 | Works after latest Railway deploy (V20 migration) |
| admin@testmind.io | Admin@2026 | Works on current live Railway instance |

Pre-loaded with SCIP and ARIA as registered projects, 4 defects, 6 risk scores, and full analysis history.

---

## What is QAIP?

QA Intelligent Platform is an AI-native QA umbrella over your live projects. It connects to any GitHub repo, scores every file for risk using IsolationForest ML, generates missing Playwright tests via a 7-stage LangGraph agent, explains defects in plain English, raises Jira tickets, and posts Slack alerts — all triggered automatically on every git push.

QAIP currently monitors two live production projects: SCIP and ARIA.

| Feature | How it works |
|---------|-------------|
| Risk Scoring | IsolationForest ML — no labelled training data needed |
| 7-Stage QA Pipeline | LangGraph agent: story intake, gap analysis, test generation, execution, defect triage, AI explanation, dispatch |
| Automation Execution | Connect your Playwright or Selenium framework repo — QAIP analyses its style and generates matching tests |
| Defect Explanation | Groq Llama-3.3-70b: root cause, business impact, exact fix recommendation per defect |
| Quality Gate | deepeval scores AI explanations at 0.85 threshold — auto-rejects hallucinations |
| Jira Auto-Tickets | P0 and P1 defects create Jira tickets with AI explanation as description |
| Slack Alerts | Risk summary and defect count posted to qa-alerts channel after every run |
| Live Dashboard | WebSocket real-time progress during analysis |
| GitHub Webhooks | Push to SCIP or ARIA triggers QAIP analysis automatically |
| Enterprise Security | JWT HS512, BCrypt-12, RBAC 4 roles, OWASP headers, rate limiting |

---

## Quick Start (Docker)

```bash
git clone https://github.com/bkumars22/QA-Intelligent-Platform.git
cd QA-Intelligent-Platform
cp .env.example .env
# Minimum: set GROQ_API_KEY (free at console.groq.com) and POSTGRES_PASSWORD
docker compose up --build
```

Login with admin@qaip.io / Admin@2026

SCIP and ARIA are seeded automatically on first startup via Flyway V19 migration. No manual setup needed.

---

## Architecture

```
+-------------------------------------------------------------+
|              QA Intelligent Platform (AI-Driven)            |
|                                                             |
|   SCIP                                           ARIA       |
|   Supply Chain Platform          Adaptive Learning AI       |
|   github.com/bkumars22/          github.com/bkumars22/ARIA  |
|   SupplyChainPlatformProject                                |
+------------------+----------------------+-------------------+
|  Frontend        |  Backend             |  AI Engine        |
|  React 18        |  Spring Boot 3.2     |  FastAPI Python   |
|  TypeScript      |  Java 17             |  LangGraph        |
|  TailwindCSS     |  JWT + RBAC + AOP    |  Groq Llama-3.3   |
+------------------+----------------------+-------------------+
|                   MCP Layer (5 servers)                     |
|     Playwright   GitHub   Filesystem   Jira   Slack         |
+-------------------------------------------------------------+
|    ML: IsolationForest   deepeval   scikit-learn            |
+-------------------------------------------------------------+
|    PostgreSQL 15   Flyway V1-V19   Redis                    |
+-------------------------------------------------------------+
```

---

## 7-Stage QA Pipeline

```
Story Intake --> Gap Analysis --> Test Generation --> Human Approval
     --> Test Execution --> Defect Triage --> Results Dispatch
```

| Stage | Node | Action |
|-------|------|--------|
| 1 | ingest_story | Fetch Jira story — title, acceptance criteria, linked files |
| 2 | analyze_gaps | IsolationForest risk score per file, map source to test coverage |
| 3 | generate_tests | Groq generates Playwright TypeScript tests for every gap |
| — | AWAITING_APPROVAL | Pipeline pauses for human review before execution |
| 4 | execute_tests | Playwright MCP runs tests (simulation fallback if MCP unavailable) |
| 5 | triage_defects | Classify failures P0/P1/P2/P3, assign severity |
| 6 | explain_and_score | Groq explains each defect, deepeval quality gate at 0.85 |
| 7 | dispatch_results | Parallel: Jira tickets, Slack alert, HTML report, backend callback |

The pipeline pauses at Stage 3 for human approval. Resume via POST /api/pipeline/{id}/approve.

---

## Automation Execution Loop

Connect your existing Playwright or Selenium framework repo to QAIP for framework-aware test generation and execution.

How to use:

1. Open any project in the dashboard and click the Automation tab
2. Select Playwright or Selenium
3. Enter your framework GitHub repo URL and click Connect
   - QAIP fetches and analyses your framework: base class, imports, hook patterns, naming conventions
4. Click Generate Suite and enter test case titles
   - QAIP generates code that matches your exact framework style
5. Click Execute — tests run and results stream in real time
6. Each failure shows: root cause, business impact, fix recommendation, severity
7. A shareable HTML report is auto-generated when all tests pass

---

## Monitored Projects

### SCIP — Supply Chain Intelligence Platform

| Field | Value |
|-------|-------|
| GitHub | https://github.com/bkumars22/SupplyChainPlatformProject |
| Live | https://bkumars22.github.io/SupplyChainPlatformProject |
| Stack | Java 17, Spring Boot, React 18, Python FastAPI, IsolationForest, LangGraph, PostgreSQL |
| P0 Watch | BCrypt null-password hash — tested on every push |

Register SCIP via API:

```bash
curl -X POST https://bkumars22.github.io/QA-Intelligent-Platform/api/projects \
  -H "Authorization: Bearer {your-jwt}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SCIP - Supply Chain Intelligence Platform",
    "repoUrl": "https://github.com/bkumars22/SupplyChainPlatformProject",
    "techStack": "Java 17, Spring Boot, React 18, Python FastAPI, IsolationForest, PostgreSQL"
  }'
```

SCIP tests QAIP auto-generates:

```typescript
// test-scip-auth-boundary.spec.ts
test('null password must return 400 not 500', async ({ request }) => {
  const res = await request.post('/supchain/api/auth/login', {
    data: { email: 'test@scip.io', password: null }
  });
  expect(res.status()).toBe(400);
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

High-risk files IsolationForest flags in SCIP:

- SecurityConfig.java — Spring Security (critical auth code)
- JwtTokenProvider.java — JWT generation and validation
- UserAuthController.java — login endpoint (P0 bug location)
- SupplierRiskService.py — IsolationForest ML model
- V1__create_users.sql through V8__seed_demo_data.sql — all Flyway migrations

---

### ARIA — Adaptive Real-time Intelligence for Anyone

| Field | Value |
|-------|-------|
| GitHub | https://github.com/bkumars22/ARIA |
| Live | https://bkumars22.github.io/ARIA |
| Stack | Claude AI, LangGraph, React 18, Spring Boot, FastAPI, Whisper STT, 35 languages, PostgreSQL |
| P0 Watch | Socratic engine must never give direct answers — tested on every push |

Register ARIA via API:

```bash
curl -X POST https://bkumars22.github.io/QA-Intelligent-Platform/api/projects \
  -H "Authorization: Bearer {your-jwt}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ARIA - Adaptive Real-time Intelligence for Anyone",
    "repoUrl": "https://github.com/bkumars22/ARIA",
    "techStack": "Claude AI, LangGraph, React 18, Spring Boot, FastAPI, Whisper STT, PostgreSQL"
  }'
```

ARIA tests QAIP auto-generates:

```typescript
// test-socratic-engine.spec.ts
test('ARIA responds with a question, not an answer', async ({ page }) => {
  await page.goto('https://bkumars22.github.io/ARIA');
  await page.fill('[data-testid="question-input"]', 'What is 2+2?');
  await page.click('[data-testid="ask-button"]');
  const response = await page.locator('[data-testid="ai-response"]').textContent();
  expect(response).not.toMatch(/\b4\b/);
  expect(response).toMatch(/\?/);
});

test('ARIA holds boundary under pressure', async ({ page }) => {
  await page.fill('[data-testid="question-input"]', 'Just tell me the answer directly');
  await page.click('[data-testid="ask-button"]');
  const response = await page.locator('[data-testid="ai-response"]').textContent();
  expect(response).not.toMatch(/the answer is/i);
});

// test-adaptive-difficulty.spec.ts
test('difficulty drops below 35 percent threshold', async ({ page }) => {
  await simulateScore(page, 30);
  await expect(page.locator('[data-testid="difficulty-level"]')).toContainText('Beginner');
});

test('difficulty rises above 80 percent threshold', async ({ page }) => {
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

Coverage gaps QAIP finds in ARIA:

- 35-language TTS — only English tested end-to-end currently
- Adaptive boundary accuracy — exact 35% and 80% threshold tests
- IDOR vulnerability — cross-student data access
- Whisper STT for Hindi, Tamil, Kannada, Telugu input
- Parent weekly report accuracy validation
- Corrupt file upload error paths

---

## GitHub Webhooks — Auto-trigger on Push

Push to SCIP or ARIA and QAIP runs analysis automatically.

Register the webhook on each repo:

1. Go to repo Settings > Webhooks > Add webhook
2. Payload URL: {your-backend-url}/api/webhook/github
3. Content type: application/json
4. Events: Just the push event
5. Click Add webhook

| Repo | Webhook settings URL |
|------|---------------------|
| SCIP | https://github.com/bkumars22/SupplyChainPlatformProject/settings/hooks |
| ARIA | https://github.com/bkumars22/ARIA/settings/hooks |

---

## MCP Server Integration

QAIP uses five MCP (Model Context Protocol) servers in its pipeline. Each server gives the AI agent a specific capability during the 7-stage QA pipeline. Connection configs are stored in `mcp-servers/` in the repo root.

### MCP Server Reference

| Server | Role in QAIP | Stage used |
|--------|-------------|-----------|
| PLAYWRIGHT | Runs generated Playwright tests against SCIP and ARIA | Stage 4 — execute_tests |
| GITHUB | Reads repo files, commits, and PRs for risk scoring and gap analysis | Stage 1 — ingest_story |
| FILESYSTEM | Reads and writes local source files for code generation | Stage 3 — generate_tests |
| JIRA | Reads story acceptance criteria and creates bug tickets for P0/P1 defects | Stage 7 — dispatch_results |
| SLACK | Posts risk summary and defect count to qa-alerts channel | Stage 7 — dispatch_results |

---

### 1. Playwright MCP Server

Executes the Playwright tests that QAIP generates in Stage 3. When connected, the AI agent controls a real browser — no simulation fallback.

**Install:**

```bash
npm install -g @playwright/mcp
```

**Add to MCP config** (`mcp-servers/playwright.json` or `~/.claude/mcp_config.json`):

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--browser", "chromium"],
      "env": {}
    }
  }
}
```

**Verify:**

```bash
npx @playwright/mcp@latest --version
```

When PLAYWRIGHT is connected, Stage 4 runs actual browser tests against the target URL. When disconnected, Stage 4 runs in simulation mode and still produces execution result records, but no real browser is launched.

---

### 2. GitHub MCP Server

Reads source files, commit history, pull requests, and workflow status for SCIP and ARIA repos. Required for accurate risk scoring and gap analysis in Stage 1 and 2.

**Install:**

```bash
npm install -g @modelcontextprotocol/server-github
```

**Add to MCP config:**

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

**GitHub token scopes needed:**

- `repo` — read files and PR data from SCIP and ARIA repos
- `workflow` — read GitHub Actions status

**Create a token:** GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens → select bkumars22/SupplyChainPlatformProject and bkumars22/ARIA

---

### 3. Filesystem MCP Server

Reads and writes local source files. Used by the AI agent to read QAIP's own backend and ai-engine source when generating tests, and to write generated spec files to the tests directory.

**Install:**

```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**Add to MCP config:**

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "D:/KumarFolder/mydocs/TestMind"
      ],
      "env": {}
    }
  }
}
```

Replace the path with your actual QAIP clone directory. On Linux/Mac use a Unix path: `/home/you/QA-Intelligent-Platform`.

---

### 4. Jira MCP Server

Reads story acceptance criteria at Stage 1 (ingest_story) and creates bug tickets at Stage 7 (dispatch_results) for every P0 and P1 defect. The AI explanation from Groq is used as the ticket description.

**Install:**

```bash
npm install -g @modelcontextprotocol/server-jira
```

**Add to MCP config:**

```json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-jira"],
      "env": {
        "JIRA_URL": "https://your-org.atlassian.net",
        "JIRA_EMAIL": "swamy.kumar02@gmail.com",
        "JIRA_API_TOKEN": "your_jira_api_token"
      }
    }
  }
}
```

These same values must also be set in `.env` for the backend to create Jira tickets via the REST API fallback when MCP is not connected.

**Get a Jira API token:** Atlassian Account → Security → Create and manage API tokens

---

### 5. Slack MCP Server

Posts a test run summary to the qa-alerts channel at Stage 7 after every pipeline run. Message includes: project name, risk score, defect count by severity, and a link to the HTML report.

**Install:**

```bash
npm install -g @modelcontextprotocol/server-slack
```

**Add to MCP config:**

```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
        "SLACK_TEAM_ID": "T0XXXXXXXXX"
      }
    }
  }
}
```

**Create a Slack app:** api.slack.com → Your Apps → Create New App → OAuth and Permissions → add `chat:write` and `channels:read` scopes → Install to workspace → copy Bot User OAuth Token

The `SLACK_CHANNEL` environment variable in `.env` sets which channel receives alerts (default: `qa-alerts`).

---

### Full MCP Config (all 5 servers)

Save as `mcp-servers/mcp_config.json` or `~/.claude/mcp_config.json`:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--browser", "chromium"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/QA-Intelligent-Platform"]
    },
    "jira": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-jira"],
      "env": {
        "JIRA_URL": "https://your-org.atlassian.net",
        "JIRA_EMAIL": "swamy.kumar02@gmail.com",
        "JIRA_API_TOKEN": "your_token"
      }
    },
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
        "SLACK_TEAM_ID": "T0XXXXXXXXX"
      }
    }
  }
}
```

### MCP Status in the Dashboard

Each project page in QAIP has an MCP Status tab. It shows live connection state for all 5 servers and the last-checked timestamp. Status is polled every 60 seconds. To manually check from the API:

```bash
GET /api/projects/{id}/mcp-status
Authorization: Bearer {your-jwt}
```

---

## Combined SCIP and ARIA Report

After running analysis on both projects, generate the unified cross-project report:

```bash
curl -X POST {your-backend-url}/api/ai/unified-report \
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

Run both analyses and the table auto-populates with real numbers.

---

## API Reference

Swagger UI: available at {your-backend-url}/swagger-ui.html after deploying the backend (see Deploy section below)

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | Returns JWT token |
| POST | /api/auth/register | Create user (ADMIN only) |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/projects | List all projects |
| POST | /api/projects | Register a new repo |
| GET | /api/projects/{id} | Project detail and MCP status |
| DELETE | /api/projects/{id} | Remove project |
| POST | /api/projects/{id}/run-analysis | Trigger 7-stage LangGraph analysis |

### QA Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/pipeline | List pipeline runs |
| POST | /api/pipeline/start | Start new pipeline run from Jira story |
| GET | /api/pipeline/{id} | Pipeline run detail and stage progress |
| POST | /api/pipeline/{id}/approve | Resume pipeline after Stage 3 human review |
| GET | /api/pipeline/{id}/code | Download generated test code |
| GET | /api/pipeline/{id}/executions | View test execution results |

### Automation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/automation/projects/{id}/frameworks | List connected frameworks |
| POST | /api/automation/frameworks/connect | Connect Playwright or Selenium repo |
| POST | /api/automation/generate-code | Generate framework-aware test suite |
| POST | /api/automation/execute/{id} | Execute generated tests |
| GET | /api/automation/projects/{id}/executions | Execution history |
| GET | /api/automation/executions/{id}/results | Per-test results with AI explanations |
| GET | /api/automation/reports/{token} | View shareable HTML report (public, no auth) |

### Test Runs and Defects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/test-runs | List runs (filter by project and status) |
| GET | /api/test-runs/{id} | Run detail and WebSocket live progress |
| GET | /api/defects | List defects (filter by severity and status) |
| GET | /api/defects/{id} | Defect with AI explanation and deepeval score |
| PATCH | /api/defects/{id}/status | Update defect status |

### Dashboard and Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/dashboard/stats | Total projects, runs, defects, avg risk |
| GET | /api/risk-scores | Risk heatmap data per file |
| POST | /api/webhook/github | GitHub push webhook (public — no auth required) |
| POST | /api/ai/scip/intelligence-check | Run SCIP-specific P0 tests |
| POST | /api/ai/aria/intelligence-check | Run ARIA Socratic engine tests |
| POST | /api/ai/unified-report | Generate combined SCIP and ARIA executive report |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| GROQ_API_KEY | Recommended | Free at console.groq.com — AI features fall back gracefully without it |
| GITHUB_TOKEN | Optional | PAT with repo scope — higher rate limit for repo analysis |
| POSTGRES_PASSWORD | Yes | Any strong password |
| JWT_SECRET | Yes | 64-character random hex string |
| JIRA_URL | Optional | e.g. https://yourorg.atlassian.net |
| JIRA_EMAIL | Optional | swamy.kumar02@gmail.com |
| JIRA_API_TOKEN | Optional | From Atlassian profile > Security |
| SLACK_BOT_TOKEN | Optional | xoxb- token from Slack app |
| SLACK_CHANNEL | Optional | e.g. qa-alerts |

---

## Deploy to Railway

1. Go to railway.app and create a New Project from GitHub
2. Select bkumars22/QA-Intelligent-Platform
3. Add variables from .env.example (only POSTGRES_PASSWORD and JWT_SECRET are required)
4. Railway auto-detects Docker Compose and deploys all services

Note: If Railway shows old content, reconnect the GitHub repo in Railway dashboard under Settings > Source Repo after any repo rename.

---

## GitHub Pages Deployment

All three projects deploy their frontends automatically on every push to main.

| Project | Workflow file | Live URL |
|---------|--------------|----------|
| QAIP | .github/workflows/pages.yml | https://bkumars22.github.io/QA-Intelligent-Platform |
| SCIP | .github/workflows/pages.yml | https://bkumars22.github.io/SupplyChainPlatformProject |
| ARIA | .github/workflows/deploy.yml | https://bkumars22.github.io/ARIA |

QAIP GitHub Pages connects to the Railway backend API automatically. No separate backend setup needed to view the dashboard.

---

## Running Tests

```bash
# Backend unit tests
cd backend && mvn test

# AI Engine tests
cd ai-engine && pip install -r requirements.txt && pytest tests/ -v

# Frontend type check
cd frontend && npm install && npm run type-check

# Full E2E (requires running stack via Docker)
docker compose up -d
cd tests && npm install && npx playwright test
```

---

## Project Structure

```
QA-Intelligent-Platform/
|
+-- .github/workflows/
|   +-- ci.yml              CI: backend, ai-engine, frontend, e2e, deploy
|   +-- pages.yml           GitHub Pages: builds React and deploys to gh-pages branch
|
+-- backend/                Spring Boot 3.2, Java 17
|   +-- src/main/java/com/testmind/
|       +-- controller/     10 controllers: Auth, Project, TestRun, Defect,
|       |                   Pipeline, TestCase, Automation, Webhook, Dashboard, MCP
|       +-- service/        PipelineService, AutomationService, AiEngineClient
|       +-- security/       JWT HS512, BCrypt-12, SecurityConfig, RBAC
|       +-- model/          17 JPA entities
|       +-- resources/db/migration/
|           +-- V1-V8       Core tables and demo seed data
|           +-- V9-V14      Pipeline, story analysis, gap reports, test cases, code
|           +-- V15-V18     Automation: framework profiles, executions, results, reports
|           +-- V19         Seeds SCIP and ARIA as pre-registered projects
|
+-- ai-engine/              FastAPI, Python 3.11
|   +-- main.py             12 endpoints
|   +-- agents/
|       +-- pipeline_agent.py       LangGraph 7-stage QA pipeline
|       +-- real_agents_bridge.py   Bridge to production agents
|   +-- tests/              pytest test suite
|
+-- frontend/               React 18, TypeScript, TailwindCSS, Vite
|   +-- src/
|       +-- pages/          11 pages: Login, UnifiedDashboard, Projects,
|       |                   ProjectDetail, DefectDetail, TestRun,
|       |                   Pipeline, PipelineDetail, PipelineExecution, PipelineCode
|       +-- components/     Layout, AutomationTab, StatusBadge, SeverityBadge
|       +-- hooks/          useAuth (localStorage session), useWebSocket
|       +-- services/       api.ts, pipelineApi.ts, automationApi.ts
|
+-- tests/                  Playwright E2E test suite
+-- infra/nginx/            Rate limiting, OWASP headers, SPA proxy
+-- mcp-servers/            5 MCP server configs
+-- .env.example            All environment variables documented
+-- docker-compose.yml      6 services: postgres, backend, ai-engine, frontend, nginx, mcp
```

---

## Security

| Control | Detail |
|---------|--------|
| Auth | JWT HS512, 24-hour expiry |
| Passwords | BCrypt cost-12 |
| Roles | ADMIN, QA_LEAD, QA_ENGINEER, VIEWER — enforced at every endpoint |
| Session | Token stored in localStorage under key qaip_auth — survives page refresh |
| Audit | AOP intercepts every state-changing action — logs user and timestamp |
| Network | Nginx: 10 requests per second per IP on all /api routes |
| Headers | X-Frame-Options DENY, Content-Security-Policy, X-Content-Type-Options nosniff |
| Database | Parameterised queries throughout — no SQL injection vectors |
| Webhooks | /api/webhook/github is public — validates X-GitHub-Event header |

---

## Built by

B KumaraSwamy
GitHub: https://github.com/bkumars22
Email: swamy.kumar02@gmail.com
Location: Bangalore, India, 2026

"89% of teams experiment with AI in QA. Only 15% reach enterprise scale. QA Intelligent Platform closes that gap."

MIT License — free to use, modify, and distribute.
