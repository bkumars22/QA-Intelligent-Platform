"""
QAIP Serverless AI Inference Layer

Deployed as AWS Lambda (container image) triggered by Kafka events via
Amazon MSK + Lambda event source mapping. This replaces the old
"always-on Python FastAPI container" pattern for AI calls — you only
pay for the seconds this actually runs, and it scales to zero when
there's no PR/commit activity, and to hundreds of concurrent
invocations during a busy merge window.

Cost model: ~$0.0000166667 per GB-second + $0.20 per 1M requests
vs an always-on 1GB container costing ~$700-900/month regardless of load.
"""

import json
import os
import time
import boto3
from anthropic import Anthropic
from isolation_forest_scorer import score_commit_risk  # your existing ML module
from model_router import route_to_model                # your existing ModelRouter

anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
cost_tracker_table = boto3.resource("dynamodb").Table(os.environ["COST_TRACKER_TABLE"])


def handler(event, context):
    """
    Entry point for Lambda. `event` contains a batch of Kafka records
    (base64-encoded) forwarded by the MSK event source mapping.
    """
    results = []

    for record in event.get("records", {}).values():
        for message in record:
            payload = _decode_kafka_message(message)
            result = _process_commit_event(payload)
            results.append(result)

    return {"statusCode": 200, "processed": len(results), "results": results}


def _decode_kafka_message(message: dict) -> dict:
    import base64
    raw = base64.b64decode(message["value"])
    return json.loads(raw)


def _process_commit_event(payload: dict) -> dict:
    """
    Mirrors the QAIP LangGraph pipeline stages, but each stage now
    runs as a fast, stateless function instead of a long-lived process.
    """
    start = time.time()

    # Stage 1 — risk scoring (IsolationForest, unsupervised)
    risk_score = score_commit_risk(
        lines_changed=payload["lines_changed"],
        complexity=payload["complexity"],
        change_frequency=payload["change_frequency"],
    )

    # Stage 2 — route to the cheapest model that can handle this task
    model = route_to_model(task_type=payload["task_type"], risk_score=risk_score)

    # Stage 3 — only call the LLM if risk crosses the threshold
    # (this is the actual cost lever — most commits never reach this stage)
    explanation = None
    if risk_score >= float(os.environ.get("RISK_THRESHOLD", "0.6")):
        response = anthropic_client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"Explain the risk in this commit: {payload['diff_summary']}"
            }],
        )
        explanation = response.content[0].text
        _log_cost(payload["commit_sha"], model, response.usage)

    duration_ms = (time.time() - start) * 1000

    return {
        "commit_sha": payload["commit_sha"],
        "risk_score": risk_score,
        "model_used": model,
        "explanation": explanation,
        "duration_ms": duration_ms,
    }


def _log_cost(commit_sha: str, model: str, usage) -> None:
    cost_tracker_table.put_item(Item={
        "commit_sha": commit_sha,
        "model": model,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "timestamp": int(time.time()),
    })
