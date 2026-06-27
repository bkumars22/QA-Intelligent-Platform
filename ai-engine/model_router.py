"""
ModelRouter — Level 4 AI Architect Component
Intelligently selects the best model based on task complexity, cost budget, and latency SLA.

Routing logic:
  FAST   → Groq llama-3.1-8b-instant       (simple lookups, quick summaries)
  MEDIUM → Groq llama-3.3-70b-versatile    (analysis, test generation, defect explanation)
  HEAVY  → Groq llama-3.3-70b-versatile    (multi-step reasoning, cross-project reports)
  VISION → Groq llama-3.2-90b-vision-preview (image/document analysis)

Cost model (approx per 1M tokens):
  llama-3.1-8b-instant       → $0.05 input / $0.08 output
  llama-3.3-70b-versatile    → $0.59 input / $0.79 output
  llama-3.2-90b-vision       → $0.90 input / $0.90 output
  claude-sonnet-4-6          → $3.00 input / $15.00 output  (premium fallback)
"""

from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("qaip.model_router")

# ── Model definitions ─────────────────────────────────────────────────────────

class ModelTier(str, Enum):
    FAST   = "fast"
    MEDIUM = "medium"
    HEAVY  = "heavy"
    VISION = "vision"


@dataclass
class ModelSpec:
    model_id: str
    provider: str          # "groq" | "anthropic"
    tier: ModelTier
    cost_per_1m_input:  float   # USD
    cost_per_1m_output: float   # USD
    max_tokens: int
    avg_latency_ms: int         # rough estimate


MODEL_REGISTRY: dict[ModelTier, ModelSpec] = {
    ModelTier.FAST: ModelSpec(
        model_id="llama-3.1-8b-instant",
        provider="groq",
        tier=ModelTier.FAST,
        cost_per_1m_input=0.05,
        cost_per_1m_output=0.08,
        max_tokens=8192,
        avg_latency_ms=400,
    ),
    ModelTier.MEDIUM: ModelSpec(
        model_id="llama-3.3-70b-versatile",
        provider="groq",
        tier=ModelTier.MEDIUM,
        cost_per_1m_input=0.59,
        cost_per_1m_output=0.79,
        max_tokens=32768,
        avg_latency_ms=1800,
    ),
    ModelTier.HEAVY: ModelSpec(
        model_id="llama-3.3-70b-versatile",
        provider="groq",
        tier=ModelTier.HEAVY,
        cost_per_1m_input=0.59,
        cost_per_1m_output=0.79,
        max_tokens=32768,
        avg_latency_ms=2500,
    ),
    ModelTier.VISION: ModelSpec(
        model_id="llama-3.2-90b-vision-preview",
        provider="groq",
        tier=ModelTier.VISION,
        cost_per_1m_input=0.90,
        cost_per_1m_output=0.90,
        max_tokens=8192,
        avg_latency_ms=2200,
    ),
}

# Baseline: "what if we always used HEAVY?" — used to compute savings %
BASELINE_MODEL = MODEL_REGISTRY[ModelTier.HEAVY]


# ── Task type → tier mapping ──────────────────────────────────────────────────

TASK_TIER_MAP: dict[str, ModelTier] = {
    # Quick, structural tasks
    "health_check":         ModelTier.FAST,
    "classify":             ModelTier.FAST,
    "extract_json":         ModelTier.FAST,
    "summarise_short":      ModelTier.FAST,
    "detect_subject":       ModelTier.FAST,

    # Standard analysis tasks
    "explain_defect":       ModelTier.MEDIUM,
    "generate_tests":       ModelTier.MEDIUM,
    "risk_analysis":        ModelTier.MEDIUM,
    "framework_analysis":   ModelTier.MEDIUM,
    "generate_report":      ModelTier.MEDIUM,
    "socratic_teach":       ModelTier.MEDIUM,
    "homework_solve":       ModelTier.MEDIUM,
    "assess_student":       ModelTier.MEDIUM,
    "supply_chain_risk":    ModelTier.MEDIUM,
    "org_intelligence":     ModelTier.MEDIUM,

    # Complex multi-step tasks
    "unified_report":       ModelTier.HEAVY,
    "cross_project_audit":  ModelTier.HEAVY,
    "langgraph_agent":      ModelTier.HEAVY,
    "deep_risk_scoring":    ModelTier.HEAVY,

    # Vision tasks
    "document_explain":     ModelTier.VISION,
    "homework_from_image":  ModelTier.VISION,
}


# ── Complexity scorer ─────────────────────────────────────────────────────────

def score_complexity(prompt: str) -> ModelTier:
    """
    Heuristic complexity scoring when task_type is not specified.
    Returns the recommended tier based on prompt characteristics.
    """
    words    = prompt.split()
    length   = len(words)
    has_code = any(kw in prompt for kw in ["def ", "class ", "function ", "import ", "SELECT ", "FROM "])
    has_multi_step = any(kw in prompt.lower() for kw in [
        "compare", "analyse", "evaluate", "cross-project", "unified", "across all",
        "explain why", "root cause", "architectural", "design"
    ])

    if length < 40 and not has_multi_step:
        return ModelTier.FAST
    if length > 300 or has_multi_step or has_code:
        return ModelTier.HEAVY
    return ModelTier.MEDIUM


# ── Router ────────────────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    model_spec:   ModelSpec
    task_type:    str
    tier:         ModelTier
    reason:       str
    estimated_cost_usd: float = 0.0     # filled in after call


class ModelRouter:
    """
    Central model router shared across QAIP, ARIA, SCIP, ZENTRAVIX.
    Selects the optimal model for each AI task to minimise cost while
    maintaining quality above the configured threshold.
    """

    def __init__(self, project: str = "QAIP"):
        self.project      = project
        self._session_decisions: list[RoutingDecision] = []

    def route(
        self,
        task_type: str | None = None,
        prompt:    str        = "",
        urgent:    bool       = False,
        has_image: bool       = False,
    ) -> RoutingDecision:
        """
        Select the best model for the task.

        Args:
            task_type: Known task name from TASK_TIER_MAP (optional).
            prompt:    The prompt text (used for auto-scoring if task_type unknown).
            urgent:    If True, prefer lower-latency models.
            has_image: If True, force VISION tier.
        """
        if has_image:
            tier   = ModelTier.VISION
            reason = "Image input detected → vision model required"
        elif task_type and task_type in TASK_TIER_MAP:
            tier   = TASK_TIER_MAP[task_type]
            reason = f"Task type '{task_type}' maps to {tier.value} tier"
        elif prompt:
            tier   = score_complexity(prompt)
            reason = f"Auto-scored prompt ({len(prompt.split())} words) → {tier.value} tier"
        else:
            tier   = ModelTier.MEDIUM
            reason = "Default fallback → medium tier"

        # Urgent override: downgrade HEAVY → MEDIUM for speed
        if urgent and tier == ModelTier.HEAVY:
            tier   = ModelTier.MEDIUM
            reason += " [urgent: downgraded to medium for latency]"

        spec = MODEL_REGISTRY[tier]
        decision = RoutingDecision(
            model_spec=spec,
            task_type=task_type or "auto",
            tier=tier,
            reason=reason,
        )
        self._session_decisions.append(decision)
        logger.info(
            "[%s] ModelRouter → %s (%s) | %s",
            self.project, spec.model_id, tier.value, reason
        )
        return decision

    def record_cost(self, decision: RoutingDecision, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate and record the actual cost for a completed call."""
        spec = decision.model_spec
        cost = (
            prompt_tokens     / 1_000_000 * spec.cost_per_1m_input  +
            completion_tokens / 1_000_000 * spec.cost_per_1m_output
        )
        decision.estimated_cost_usd = cost

        # Compute savings vs always-HEAVY baseline
        baseline_cost = (
            prompt_tokens     / 1_000_000 * BASELINE_MODEL.cost_per_1m_input  +
            completion_tokens / 1_000_000 * BASELINE_MODEL.cost_per_1m_output
        )
        saved = baseline_cost - cost
        if saved > 0:
            pct = (saved / baseline_cost) * 100
            logger.info(
                "[%s] Cost: $%.6f (saved $%.6f / %.1f%% vs always-heavy)",
                self.project, cost, saved, pct
            )
        return cost

    def session_summary(self) -> dict[str, Any]:
        """Return a summary of all routing decisions made this session."""
        total_cost  = sum(d.estimated_cost_usd for d in self._session_decisions)
        tier_counts: dict[str, int] = {}
        for d in self._session_decisions:
            tier_counts[d.tier.value] = tier_counts.get(d.tier.value, 0) + 1

        return {
            "project":       self.project,
            "total_calls":   len(self._session_decisions),
            "tier_breakdown": tier_counts,
            "total_cost_usd": round(total_cost, 6),
            "decisions": [
                {
                    "task_type": d.task_type,
                    "model":     d.model_spec.model_id,
                    "tier":      d.tier.value,
                    "reason":    d.reason,
                    "cost_usd":  round(d.estimated_cost_usd, 6),
                }
                for d in self._session_decisions
            ],
        }


# ── Singleton per project ─────────────────────────────────────────────────────

_routers: dict[str, ModelRouter] = {}

def get_router(project: str = "QAIP") -> ModelRouter:
    if project not in _routers:
        _routers[project] = ModelRouter(project=project)
    return _routers[project]
