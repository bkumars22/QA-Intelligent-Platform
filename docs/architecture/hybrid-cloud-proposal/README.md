# Hybrid Cloud Architecture — Proposal (not implemented)

This folder is a **reference architecture / interview talking-point document**, not
running infrastructure. Nothing here is wired into the real backend, ai-engine, or
deploy pipeline. QAIP's actual current architecture is Railway (single Dockerfile
per service) + Docker Compose for local dev — see the root [README's Architecture
section](../../../README.md#architecture), which matches the real code.

## Why this exists

The proposal sketches how QAIP *could* evolve if commit volume grew to the point
where an always-on AI container becomes wasteful: split the always-on, latency
sensitive parts (webhook intake, CRUD, auth) onto Kubernetes, and move the bursty
AI inference work to pay-per-invocation serverless (AWS Lambda), decoupled by an
event bus (Kafka) so the webhook responds immediately instead of blocking on an
LLM call. `security/` and `terraform/` describe the mTLS/NetworkPolicy and AWS
provisioning that tier would need.

## Naming does not match the real codebase — read this before reusing any of it

The files were written against a generic/template QAIP shape, not this repo's
actual module names. If you ever adapt this for real, these are the concrete
gaps to close first:

| Proposal assumes | Real QAIP has |
|---|---|
| Java package `com.qaip.events` | Real backend package is `com.testmind` — see `backend/src/main/java/com/testmind/controller/WebhookController.java`, which already does the webhook intake this proposal's `CommitEventProducer` would replace |
| `from isolation_forest_scorer import score_commit_risk` | No standalone module — risk scoring is the `score_risk(state)` node inside the LangGraph pipeline in `ai-engine/agents/langgraph_agent.py`, operating on a shared `AgentState`, not three scalar args |
| `from model_router import route_to_model(task_type, risk_score)` | `ai-engine/model_router.py` exports a `ModelRouter` class with a `.route(...)` method (via `get_router()`), not a bare function — and it routes to **Groq** (llama-3.1/3.3) by default, with Claude only as a costed "premium fallback" |
| DynamoDB `cost_tracker` table | `ai-engine/cost_tracker.py` already exists — in-memory `CostTracker`, with its own comment noting production should be Postgres, not DynamoDB |
| Kafka / MSK / Strimzi event bus | No message broker anywhere in this repo currently |
| EKS / Kubernetes / Istio mesh | No Kubernetes manifests outside this folder; `infra/` only holds `nginx/` config for the Docker Compose stack |

## If you actually want to build this

Treat it as a design exercise, not a drop-in: rename the Java package, adapt
`CommitEventProducer` to call through the real `AiEngineClient`/`WebhookController`
flow (or replace it), and rewrite the Lambda handler to call the real
`score_risk`/`ModelRouter`/`CostTracker` APIs instead of the placeholder imports
above. You'd also need to stand up Kafka (or MSK) and a real AWS account before
any of `terraform/main.tf` or `.github-workflow-reference/deploy.yml` could run —
none of that exists yet, so don't `terraform apply` this as-is.
