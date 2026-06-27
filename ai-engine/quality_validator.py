"""
QualityValidator — Level 4 AI Architect Component
Validates AI-generated output quality across all projects.

Metrics:
  - Completeness   : were all required sections present?
  - Relevance      : does the answer address the question?
  - Hallucination  : does the answer invent facts not in context?
  - Structure      : is the output properly structured (JSON / steps / bullets)?
  - Confidence     : self-reported or inferred confidence score

Used as a quality gate in CI/CD: deploy blocked if avg_score < QUALITY_THRESHOLD.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("qaip.quality_validator")

QUALITY_THRESHOLD = 0.75   # minimum acceptable score to pass CI gate


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class QualityResult:
    score:         float                   # 0.0 – 1.0 overall
    passed:        bool                    # score >= QUALITY_THRESHOLD
    breakdown:     dict[str, float]        # per-metric scores
    flags:         list[str] = field(default_factory=list)   # problems found
    suggestions:   list[str] = field(default_factory=list)   # improvement hints

    def as_dict(self) -> dict[str, Any]:
        return {
            "score":       round(self.score, 3),
            "passed":      self.passed,
            "threshold":   QUALITY_THRESHOLD,
            "breakdown":   {k: round(v, 3) for k, v in self.breakdown.items()},
            "flags":       self.flags,
            "suggestions": self.suggestions,
        }


# ── Validators ────────────────────────────────────────────────────────────────

def _completeness(response: str, required_sections: list[str]) -> tuple[float, list[str]]:
    """Check that all required sections appear in the response."""
    if not required_sections:
        return 1.0, []
    found  = [s for s in required_sections if s.lower() in response.lower()]
    missing = [s for s in required_sections if s not in found]
    score   = len(found) / len(required_sections)
    flags   = [f"Missing section: '{s}'" for s in missing]
    return score, flags


def _relevance(response: str, question: str) -> float:
    """
    Simple keyword overlap relevance score.
    Production: replace with sentence-transformer cosine similarity.
    """
    if not question or not response:
        return 1.0
    q_words = set(re.findall(r'\w{4,}', question.lower()))
    r_words = set(re.findall(r'\w{4,}', response.lower()))
    if not q_words:
        return 1.0
    overlap = len(q_words & r_words) / len(q_words)
    return min(1.0, overlap * 1.5)   # scale up — overlap of ~0.5 should be ~0.75


def _hallucination(response: str, context: str) -> tuple[float, list[str]]:
    """
    Detect claims that are not supported by the provided context.
    Uses high-confidence assertion patterns as risk signals.
    Production: replace with NLI (Natural Language Inference) model.
    """
    if not context:
        return 1.0, []   # no context to validate against

    flags = []

    # Look for strong unsupported claims (heuristic)
    strong_claims = re.findall(
        r'\b(always|never|guaranteed|100%|proven|definitely|certainly|impossible)\b',
        response, re.IGNORECASE
    )
    if strong_claims:
        flags.append(f"Strong claim words without evidence: {strong_claims[:3]}")

    # Check if specific numbers in the response appear in context
    response_nums = set(re.findall(r'\b\d{4,}\b', response))
    context_nums  = set(re.findall(r'\b\d{4,}\b', context))
    invented_nums = response_nums - context_nums
    if len(invented_nums) > 2:
        flags.append(f"Numbers in response not found in context: {list(invented_nums)[:3]}")

    # Penalty: each flag reduces score
    score = max(0.0, 1.0 - len(flags) * 0.25)
    return score, flags


def _structure(response: str, expected_format: str) -> tuple[float, list[str]]:
    """Validate that the response follows the expected format."""
    flags = []
    if expected_format == "json":
        try:
            import json
            # Find JSON block
            m = re.search(r'\{[\s\S]+\}|\[[\s\S]+\]', response)
            if not m:
                flags.append("Expected JSON but no JSON object/array found")
                return 0.4, flags
            json.loads(m.group())
            return 1.0, []
        except Exception as e:
            flags.append(f"Malformed JSON: {e}")
            return 0.3, flags

    elif expected_format == "steps":
        has_numbered = bool(re.search(r'^\s*\d+[\.\)]\s', response, re.MULTILINE))
        has_bullets  = bool(re.search(r'^\s*[-•*]\s', response, re.MULTILINE))
        if not has_numbered and not has_bullets:
            flags.append("Expected numbered/bulleted steps but found prose only")
            return 0.6, flags
        return 1.0, []

    elif expected_format == "sections":
        headers = re.findall(r'^#{1,3}\s+.+|^\*\*.+\*\*', response, re.MULTILINE)
        if len(headers) < 2:
            flags.append("Expected multiple sections/headers but found fewer than 2")
            return 0.7, flags
        return 1.0, []

    return 1.0, []   # unknown format — pass


def _length(response: str, min_words: int = 20, max_words: int = 2000) -> tuple[float, list[str]]:
    """Check response length is within acceptable bounds."""
    wc = len(response.split())
    if wc < min_words:
        return 0.4, [f"Response too short: {wc} words (min {min_words})"]
    if wc > max_words:
        return 0.85, [f"Response very long: {wc} words (max {max_words}) — may be verbose"]
    return 1.0, []


# ── Public validator ──────────────────────────────────────────────────────────

def validate(
    response:          str,
    task_type:         str         = "generic",
    question:          str         = "",
    context:           str         = "",
    required_sections: list[str]   = None,
    expected_format:   str         = "",
    min_words:         int         = 20,
) -> QualityResult:
    """
    Validate an AI response and return a QualityResult.

    Args:
        response:          The AI-generated text to evaluate.
        task_type:         Human label for logging ("explain_defect", "generate_tests", etc.)
        question:          The original question/prompt.
        context:           Source context used to generate the response (for hallucination check).
        required_sections: List of sections that must appear in the response.
        expected_format:   "json" | "steps" | "sections" | "" (none).
        min_words:         Minimum acceptable word count.
    """
    if required_sections is None:
        required_sections = []

    all_flags: list[str] = []
    all_suggestions: list[str] = []

    # Run each metric
    comp_score, comp_flags = _completeness(response, required_sections)
    relev_score            = _relevance(response, question)
    hall_score, hall_flags = _hallucination(response, context)
    struct_score, str_flags = _structure(response, expected_format)
    len_score, len_flags   = _length(response, min_words)

    all_flags.extend(comp_flags + hall_flags + str_flags + len_flags)

    # Weighted average
    breakdown = {
        "completeness":   comp_score,
        "relevance":      relev_score,
        "hallucination":  hall_score,
        "structure":      struct_score,
        "length":         len_score,
    }
    weights = {
        "completeness": 0.30,
        "relevance":    0.25,
        "hallucination": 0.25,
        "structure":    0.12,
        "length":       0.08,
    }
    overall = sum(breakdown[k] * weights[k] for k in breakdown)

    # Generate improvement suggestions
    if comp_score < 0.8 and required_sections:
        all_suggestions.append("Include all required sections in the response.")
    if relev_score < 0.6:
        all_suggestions.append("Make the response more directly relevant to the question asked.")
    if hall_score < 0.75:
        all_suggestions.append("Avoid strong absolute claims — ground assertions in provided context.")
    if struct_score < 0.7:
        all_suggestions.append(f"Format the output as requested: {expected_format or 'structured text'}.")

    result = QualityResult(
        score=overall,
        passed=overall >= QUALITY_THRESHOLD,
        breakdown=breakdown,
        flags=all_flags,
        suggestions=all_suggestions,
    )

    logger.info(
        "[QualityValidator/%s] score=%.3f passed=%s flags=%d",
        task_type, overall, result.passed, len(all_flags)
    )
    return result


# ── Task-specific presets ─────────────────────────────────────────────────────

def validate_defect_explanation(response: str, defect_title: str = "") -> QualityResult:
    return validate(
        response=response,
        task_type="explain_defect",
        question=defect_title,
        required_sections=["What broke", "Why it matters", "Root cause", "Steps to reproduce", "Suggested fix"],
        expected_format="sections",
        min_words=80,
    )


def validate_generated_tests(response: str, file_path: str = "") -> QualityResult:
    return validate(
        response=response,
        task_type="generate_tests",
        question=file_path,
        required_sections=["test(", "expect(", "describe("],
        expected_format="",
        min_words=30,
    )


def validate_risk_analysis(response: str) -> QualityResult:
    return validate(
        response=response,
        task_type="risk_analysis",
        required_sections=["risk", "score", "recommendation"],
        expected_format="sections",
        min_words=50,
    )


def validate_unified_report(response: str) -> QualityResult:
    return validate(
        response=response,
        task_type="unified_report",
        required_sections=["SCIP", "ARIA", "summary"],
        expected_format="sections",
        min_words=100,
    )
