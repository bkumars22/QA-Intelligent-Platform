"""
RAGAS-style evaluation for QAIP's RAG pipeline.

Implements 4 metrics using only Groq (LLM) + our existing embedder:

  faithfulness       — claims in answer supported by context   (0-1)
  answer_relevancy   — how well the answer addresses the question (0-1)
  context_precision  — fraction of retrieved chunks that are useful (0-1)
  context_recall     — fraction of ground-truth statements in context (0-1,
                        requires ground_truth; omitted when not provided)

Public entry point:
  evaluate(question, answer, contexts, ground_truth=None) → EvalResult dict
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

import numpy as np
from groq import Groq

logger = logging.getLogger("rag.ragas_eval")

_GROQ_KEY  = os.getenv("GROQ_API_KEY", "")
_FAST      = "llama-3.1-8b-instant"
_SMART     = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _llm(system: str, user: str, model: str = _FAST, max_tokens: int = 512) -> str:
    client = Groq(api_key=_GROQ_KEY)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.0,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Metric 1 — Faithfulness
# ---------------------------------------------------------------------------

def _extract_claims(answer: str) -> list[str]:
    """Break answer into atomic factual claims."""
    prompt = f"""Break the following answer into individual atomic factual claims.
Return a JSON array of strings, one string per claim. Maximum 10 claims.

Answer:
{answer[:1500]}

Return only valid JSON: ["claim 1", "claim 2", ...]"""
    try:
        raw = _llm("Return only valid JSON.", prompt, model=_FAST, max_tokens=600)
        m = re.search(r"\[.*?\]", raw, re.DOTALL)
        claims = json.loads(m.group()) if m else []
        return [c for c in claims if isinstance(c, str)][:10]
    except Exception as exc:
        logger.warning("extract_claims failed: %s", exc)
        # Fallback: treat each sentence as a claim
        sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
        return [s for s in sentences if len(s) > 10][:8]


def _is_supported(claim: str, context: str) -> bool:
    """Check if a single claim is entailed by the context."""
    prompt = f"""Is the following claim fully supported by the provided context?

Claim: {claim}

Context:
{context[:1200]}

Answer with JSON only: {{"supported": true}} or {{"supported": false}}"""
    try:
        raw = _llm("Return only valid JSON.", prompt, model=_FAST, max_tokens=20)
        m = re.search(r'"supported":\s*(true|false)', raw)
        return m.group(1) == "true" if m else False
    except Exception:
        return False


def faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """Score 0-1: fraction of answer claims supported by retrieved contexts."""
    if not answer.strip() or not contexts:
        return 0.0
    claims = _extract_claims(answer)
    if not claims:
        return 1.0   # nothing to verify → assume grounded
    full_context = "\n\n".join(c[:400] for c in contexts)[:2000]
    supported = sum(1 for c in claims if _is_supported(c, full_context))
    score = round(supported / len(claims), 4)
    logger.debug("faithfulness: %d/%d claims supported → %.4f", supported, len(claims), score)
    return score


# ---------------------------------------------------------------------------
# Metric 2 — Answer Relevancy
# ---------------------------------------------------------------------------

def answer_relevancy(question: str, answer: str, n_questions: int = 3) -> float:
    """
    Score 0-1: cosine similarity between the original question and N reverse-engineered
    questions generated from the answer.  High score = answer directly addresses question.
    """
    from rag.embedder import embed  # lazy import to avoid circular deps at module load

    if not answer.strip():
        return 0.0

    prompt = f"""Given only the following answer, generate {n_questions} questions that this
answer is a good response to. Return a JSON array of strings.

Answer: {answer[:800]}

Return only valid JSON: ["question 1", "question 2", ...]"""
    try:
        raw = _llm("Return only valid JSON.", prompt, model=_FAST, max_tokens=300)
        m = re.search(r"\[.*?\]", raw, re.DOTALL)
        reverse_qs = json.loads(m.group()) if m else []
        reverse_qs = [q for q in reverse_qs if isinstance(q, str)][:n_questions]
    except Exception as exc:
        logger.warning("answer_relevancy reverse question gen failed: %s", exc)
        return 0.5   # neutral fallback

    if not reverse_qs:
        return 0.5

    try:
        orig_emb  = np.array(embed(question))
        sims = []
        for rq in reverse_qs:
            rq_emb = np.array(embed(rq))
            cosine = float(np.dot(orig_emb, rq_emb) / (np.linalg.norm(orig_emb) * np.linalg.norm(rq_emb) + 1e-9))
            sims.append(max(0.0, cosine))
        score = round(float(np.mean(sims)), 4)
        logger.debug("answer_relevancy: %d reverse-qs, mean cos=%.4f", len(sims), score)
        return score
    except Exception as exc:
        logger.warning("answer_relevancy embedding failed: %s", exc)
        return 0.5


# ---------------------------------------------------------------------------
# Metric 3 — Context Precision
# ---------------------------------------------------------------------------

def context_precision(question: str, contexts: list[str]) -> float:
    """
    Score 0-1: fraction of retrieved context chunks that are actually useful
    for answering the question.  Penalises noise in retrieval.
    """
    if not contexts:
        return 0.0

    useful_count = 0
    for ctx in contexts:
        prompt = f"""Is the following text chunk useful for answering this question?

Question: {question}
Chunk: {ctx[:500]}

Answer JSON only: {{"useful": true}} or {{"useful": false}}"""
        try:
            raw = _llm("Return only valid JSON.", prompt, model=_FAST, max_tokens=20)
            m = re.search(r'"useful":\s*(true|false)', raw)
            if m and m.group(1) == "true":
                useful_count += 1
        except Exception:
            pass

    score = round(useful_count / len(contexts), 4)
    logger.debug("context_precision: %d/%d chunks useful → %.4f", useful_count, len(contexts), score)
    return score


# ---------------------------------------------------------------------------
# Metric 4 — Context Recall (requires ground truth)
# ---------------------------------------------------------------------------

def context_recall(question: str, contexts: list[str], ground_truth: str) -> float:
    """
    Score 0-1: fraction of ground-truth statements attributable to retrieved context.
    Only computed when ground_truth is provided.
    """
    if not ground_truth.strip() or not contexts:
        return -1.0   # sentinel: not computed

    full_context = "\n\n".join(c[:400] for c in contexts)[:2000]

    prompt = f"""Given the ground truth answer and the retrieved context, identify which
sentences/claims from the ground truth can be inferred from the context.

Ground truth: {ground_truth[:800]}
Context: {full_context}

Return JSON: {{"attributable": <0-1 fraction of ground truth covered by context>}}"""
    try:
        raw = _llm("Return only valid JSON.", prompt, model=_SMART, max_tokens=50)
        m = re.search(r'"attributable":\s*([\d.]+)', raw)
        score = round(float(m.group(1)), 4) if m else 0.5
        return min(1.0, max(0.0, score))
    except Exception as exc:
        logger.warning("context_recall LLM failed: %s", exc)
        return -1.0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def evaluate(
    question:     str,
    answer:       str,
    contexts:     list[str],
    ground_truth: str | None = None,
) -> dict[str, Any]:
    """
    Run all RAGAS metrics and return a structured result dict.

    Returns:
      {
        faithfulness:       float  (0-1),
        answer_relevancy:   float  (0-1),
        context_precision:  float  (0-1),
        context_recall:     float  (-1 if no ground_truth, else 0-1),
        overall:            float  (mean of available 0-1 metrics),
        context_count:      int,
        eval_duration_ms:   int,
      }
    """
    t0 = time.monotonic()

    f_score  = faithfulness(question, answer, contexts)
    ar_score = answer_relevancy(question, answer)
    cp_score = context_precision(question, contexts)
    cr_score = context_recall(question, contexts, ground_truth or "")

    # Overall: mean of metrics that were actually computed
    available = [f_score, ar_score, cp_score]
    if cr_score >= 0:
        available.append(cr_score)
    overall = round(float(np.mean(available)), 4)

    duration_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "RAGAS eval done in %dms — F=%.3f AR=%.3f CP=%.3f CR=%s OVERALL=%.3f",
        duration_ms, f_score, ar_score, cp_score,
        f"{cr_score:.3f}" if cr_score >= 0 else "N/A",
        overall,
    )

    return {
        "faithfulness":      f_score,
        "answer_relevancy":  ar_score,
        "context_precision": cp_score,
        "context_recall":    cr_score,  # -1 = not computed
        "overall":           overall,
        "context_count":     len(contexts),
        "eval_duration_ms":  duration_ms,
    }
