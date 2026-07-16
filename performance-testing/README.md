# Performance Testing

Locust-based load testing for QAIP's backend API, with a regression gate
that compares each run against the last known-good baseline. Nothing here
is wired into `ci.yml` or `deploy-railway.yml` automatically — see
"Wiring into CI" below for why, and how to opt in.

## What's here

- `locustfile.py` — simulated traffic against QAIP's real backend routes:
  login, dashboard stats, project risk scores, automation execution
  history, and (least frequently, since it's the heaviest call) triggering
  an AI analysis run. Endpoints were checked against the actual controllers
  in `backend/src/main/java/com/testmind/controller/` — not guessed.
- `metrics_analyzer.py` — parses Locust's `--csv` output, checks P95
  latency / throughput / error rate against `baseline.json`, and fails
  (non-zero exit) if a regression exceeds the thresholds in
  `REGRESSION_THRESHOLDS`. Updates the baseline only on a clean pass.
- `../backend/src/main/resources/db/migration/V24__add_performance_test_results.sql`
  — a `performance_test_results` table for historical trend tracking.
  **Nothing currently writes to this table** — `metrics_analyzer.py` only
  reads/writes the local `baseline.json` file. Wiring runs into this table
  (e.g. a small `POST /api/performance-results` endpoint, following the
  same pattern as AIPQ's `bct_results` receiver) would be a natural next
  step if you want a trend dashboard, but wasn't built here since it's
  beyond what a CSV-diffing gate needs to function.

## Prerequisites

You need a load-test user account that already exists in the target
environment (login only, no auto-provisioning) with at least one project
under it, so `get_risk_score`/`get_dashboard`/etc. have something to hit:

```
locust -f locustfile.py --host http://localhost:8080 \
    --test-email you@example.com --test-password yourpassword
```

Omitting `--test-email`/`--test-password` falls back to
`loadtest@qaip.internal` / `loadtest-password`, which won't exist unless
you create that account yourself first.

## Run locally (interactive UI)

```
pip install locust
locust -f locustfile.py --host http://localhost:8080
```
Opens a web UI at http://localhost:8089 to configure user count and watch
live charts.

## Run headless

```
locust -f locustfile.py --host http://localhost:8080 \
    --headless --users 50 --spawn-rate 10 --run-time 5m \
    --csv=results/perf_run

python metrics_analyzer.py results/perf_run_stats.csv baseline.json
```

## Wiring into CI

`.github/workflows/performance.yml` runs the same steps as a manually
triggered (`workflow_dispatch`) GitHub Actions job — it asks for a target
host as an input rather than assuming one, because QAIP doesn't have a
dedicated staging environment (per `deploy-railway.yml`, the only Railway
target is production). Load-testing production with 50-200 concurrent
simulated users is a real-traffic, real-cost action against a live
service, so it's opt-in per run rather than automatic on every push.

If you want it to actually gate deploys, add `needs: performance-gate`
(or trigger it via `workflow_run`) to the `deploy` job in `ci.yml`
yourself once you've run it manually a few times and are comfortable with
what it does to the target host — that edits an existing file, which
wasn't done here on purpose.

You'll need two repo secrets for the CI job to log in:
`PERF_TEST_EMAIL` and `PERF_TEST_PASSWORD`, for a load-test account that
already exists in the target environment.

## Corrections made vs. the originally drafted files

The pasted draft assumed endpoints and a migration number that didn't
match this codebase:

| Draft assumed | Actually is |
|---|---|
| `POST /api/suppliers/{sha}/risk` | `GET /api/projects/{id}/risk-scores` (no `/suppliers` route exists in QAIP — that's a SCIP/supply-chain path) |
| `GET /api/dashboard/summary` | `GET /api/dashboard/stats` |
| `GET /api/automation/executions?limit=20` | `GET /api/automation/projects/{id}/executions` (project-scoped) |
| `POST /api/ai/analyze` | `POST /api/projects/{id}/run-analysis` (202, returns `runId`) |
| Login response field `token` | `accessToken` (`AuthResponse.java`) |
| Migration `V25__...` | `V24__...` — real migrations top out at `V23__add_github_token_to_framework_profile.sql` |
| CI job `needs: [deploy-core-services]` in `ci-cd/deploy.yml` | No such workflow/job exists; real CI is `ci.yml` (`backend-test`, `ai-engine-test`, `frontend-test`, `e2e-test`, `deploy`) |
