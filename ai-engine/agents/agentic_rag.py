"""
QAIP Agentic RAG — Corrective RAG (CRAG) pattern.

Graph:
  question → plan_queries → retrieve → grade_docs
      → [sufficient?] yes → generate → check_grounding → done
                      no  → rewrite_query → retrieve (max 2 hops)

Each node is traced via LangSmith when LANGCHAIN_API_KEY is set.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import TypedDict

from groq import Groq
from langgraph.graph import StateGraph, END

from langsmith_utils import trace_node
from rag.retriever import query as rag_query
from rag.embedder import embed
from rag import ragas_eval, eval_store

logger = logging.getLogger("qaip.agentic_rag")

_GROQ_KEY = os.getenv("GROQ_API_KEY", "")
_FAST_MODEL = "llama-3.1-8b-instant"
_SMART_MODEL = "llama-3.3-70b-versatile"
_MAX_HOPS = 2          # max retrieval iterations before giving up
_MIN_RELEVANT = 2      # min docs graded RELEVANT before generating


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class RAGState(TypedDict):
    question:        str
    project_id:      int
    source_type:     str | None    # optional filter: test_case | defect | jira_story
    sub_queries:     list[str]
    retrieved_docs:  list[dict]
    graded_docs:     list[dict]    # each doc + relevance: "yes"|"no"
    rewritten_query: str
    generation:      str
    is_grounded:     bool
    answer:          str
    sources:         list[dict]
    hop_count:       int
    trace:           list[dict]    # observability: what happened each hop
    error:           str


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------

def _llm(system: str, user: str, model: str = _FAST_MODEL, max_tokens: int = 512) -> str:
    client = Groq(api_key=_GROQ_KEY)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.0,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Node 1 — plan_queries
# ---------------------------------------------------------------------------

@trace_node("rag_plan_queries")
def plan_queries(state: RAGState) -> RAGState:
    """Decompose the question into 1–3 targeted sub-queries."""
    logger.info("[RAG] plan_queries: %s", state["question"])
    state["trace"].append({"node": "plan_queries", "ts": time.time()})

    prompt = f"""You are a search query planner for a QA knowledge base.
The knowledge base contains: test cases, defect reports, Jira stories, run results.

Question: {state["question"]}

Break this into 1-3 specific search queries that will retrieve the most useful documents.
Return ONLY a JSON array of strings. Example: ["query 1", "query 2"]"""

    try:
        raw = _llm("Return only valid JSON.", prompt, model=_FAST_MODEL, max_tokens=200)
        # Extract JSON array
        import re
        m = re.search(r"\[.*?\]", raw, re.DOTALL)
        queries = json.loads(m.group() if m else f'["{state["question"]}"]')
        state["sub_queries"] = [q for q in queries if isinstance(q, str)][:3]
    except Exception as exc:
        logger.warning("[RAG] plan_queries fallback: %s", exc)
        state["sub_queries"] = [state["question"]]

    state["trace"][-1]["sub_queries"] = state["sub_queries"]
    return state


# ---------------------------------------------------------------------------
# Node 2 — retrieve
# ---------------------------------------------------------------------------

@trace_node("rag_retrieve")
def retrieve(state: RAGState) -> RAGState:
    """Retrieve docs for each sub-query, deduplicate by content hash."""
    logger.info("[RAG] retrieve: hop=%d, queries=%s", state["hop_count"], state["sub_queries"])
    state["trace"].append({"node": "retrieve", "ts": time.time(), "hop": state["hop_count"]})

    seen_hashes: set[int] = {hash(d["content"]) for d in state.get("retrieved_docs", [])}
    new_docs: list[dict] = []

    active_queries = [state["rewritten_query"]] if state["rewritten_query"] else state["sub_queries"]

    for q in active_queries:
        try:
            results = rag_query(
                project_id=state["project_id"],
                question=q,
                top_k=4,
                source_type=state.get("source_type"),
            )
            for doc in results:
                h = hash(doc["content"])
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    new_docs.append({**doc, "query_used": q})
        except Exception as exc:
            logger.warning("[RAG] retrieve sub-query failed: %s", exc)

    state["retrieved_docs"] = (state.get("retrieved_docs") or []) + new_docs
    state["trace"][-1]["new_docs_count"] = len(new_docs)
    return state


# ---------------------------------------------------------------------------
# Node 3 — grade_docs
# ---------------------------------------------------------------------------

@trace_node("rag_grade_docs")
def grade_docs(state: RAGState) -> RAGState:
    """Grade each retrieved doc for relevance to the original question."""
    logger.info("[RAG] grade_docs: %d docs", len(state["retrieved_docs"]))
    state["trace"].append({"node": "grade_docs", "ts": time.time()})

    graded: list[dict] = []
    question = state["question"]

    for doc in state["retrieved_docs"]:
        content_preview = doc["content"][:400]
        prompt = f"""Is this document relevant to the question?

Question: {question}
Document: {content_preview}

Answer with JSON only: {{"relevant": "yes"}} or {{"relevant": "no"}}"""
        try:
            raw = _llm("Return only valid JSON.", prompt, model=_FAST_MODEL, max_tokens=20)
            import re
            m = re.search(r'\{"relevant":\s*"(yes|no)"\}', raw)
            relevance = m.group(1) if m else "no"
        except Exception:
            relevance = "no"

        graded.append({**doc, "relevance": relevance})

    state["graded_docs"] = graded
    relevant_count = sum(1 for d in graded if d["relevance"] == "yes")
    state["trace"][-1]["relevant_count"] = relevant_count
    return state


# ---------------------------------------------------------------------------
# Routing condition: enough relevant docs?
# ---------------------------------------------------------------------------

def _route_after_grade(state: RAGState) -> str:
    relevant = [d for d in state["graded_docs"] if d["relevance"] == "yes"]
    if len(relevant) >= _MIN_RELEVANT:
        return "generate"
    if state["hop_count"] >= _MAX_HOPS:
        return "generate"   # force generation even with thin context
    return "rewrite_query"


# ---------------------------------------------------------------------------
# Node 4 — rewrite_query
# ---------------------------------------------------------------------------

@trace_node("rag_rewrite_query")
def rewrite_query(state: RAGState) -> RAGState:
    """Rewrite the query to improve retrieval on the next hop."""
    logger.info("[RAG] rewrite_query (hop %d)", state["hop_count"])
    state["hop_count"] += 1
    state["trace"].append({"node": "rewrite_query", "ts": time.time(), "hop": state["hop_count"]})

    context_hints = ""
    if state["graded_docs"]:
        # Give the rewriter a hint about what was retrieved but wasn't relevant
        irrelevant_samples = [d["content"][:150] for d in state["graded_docs"] if d["relevance"] == "no"][:2]
        if irrelevant_samples:
            context_hints = "\nPreviously retrieved (not relevant):\n" + "\n".join(irrelevant_samples)

    prompt = f"""The original question did not retrieve enough relevant documents.

Original question: {state["question"]}
{context_hints}

Rewrite the question to be more specific and likely to match QA knowledge-base documents
(test cases, defects, Jira stories). Return ONLY the rewritten query string."""

    try:
        rewritten = _llm("You are a search query optimizer.", prompt, model=_FAST_MODEL, max_tokens=100)
        state["rewritten_query"] = rewritten.strip('"').strip()
    except Exception as exc:
        logger.warning("[RAG] rewrite_query failed: %s", exc)
        state["rewritten_query"] = state["question"]

    state["trace"][-1]["rewritten_to"] = state["rewritten_query"]
    return state


# ---------------------------------------------------------------------------
# Node 5 — generate
# ---------------------------------------------------------------------------

@trace_node("rag_generate")
def generate(state: RAGState) -> RAGState:
    """Generate an answer grounded in the relevant retrieved docs."""
    logger.info("[RAG] generate from %d relevant docs", sum(1 for d in state["graded_docs"] if d["relevance"] == "yes"))
    state["trace"].append({"node": "generate", "ts": time.time()})

    relevant_docs = [d for d in state["graded_docs"] if d["relevance"] == "yes"]
    if not relevant_docs:
        # Fall back to all graded docs if nothing was marked relevant
        relevant_docs = state["graded_docs"][:3]

    context_blocks: list[str] = []
    sources: list[dict] = []
    for i, doc in enumerate(relevant_docs, 1):
        meta = doc.get("metadata", {})
        sim = doc.get("similarity", 0)
        src_type = doc.get("source_type", "unknown")
        context_blocks.append(f"[Source {i}] ({src_type}, similarity={sim:.2f})\n{doc['content'][:600]}")
        sources.append({
            "index": i,
            "source_type": src_type,
            "file_path": meta.get("file_path", ""),
            "similarity": round(sim, 3),
            "content_preview": doc["content"][:200],
        })

    context = "\n\n".join(context_blocks)

    system = (
        "You are a QA knowledge assistant. "
        "Answer ONLY from the provided sources. "
        "If the sources don't contain enough information, say so clearly. "
        "Cite sources by number [1], [2], etc."
    )
    user = f"""Question: {state["question"]}

Sources:
{context}

Provide a clear, concise answer citing the relevant sources."""

    try:
        state["generation"] = _llm(system, user, model=_SMART_MODEL, max_tokens=1024)
    except Exception as exc:
        logger.warning("[RAG] generate LLM failed: %s", exc)
        state["generation"] = f"Answer generation failed: {exc}"

    state["sources"] = sources
    return state


# ---------------------------------------------------------------------------
# Node 6 — check_grounding
# ---------------------------------------------------------------------------

@trace_node("rag_check_grounding")
def check_grounding(state: RAGState) -> RAGState:
    """Verify the generation is grounded in retrieved docs (no hallucination)."""
    logger.info("[RAG] check_grounding")
    state["trace"].append({"node": "check_grounding", "ts": time.time()})

    if not state["generation"] or not state["graded_docs"]:
        state["is_grounded"] = False
        state["answer"] = state["generation"]
        return state

    sources_summary = "\n".join(
        d["content"][:200] for d in state["graded_docs"] if d["relevance"] == "yes"
    )[:1500]

    prompt = f"""Does this answer only contain information present in the provided sources?

Answer: {state["generation"][:500]}

Sources: {sources_summary}

Return JSON only: {{"grounded": true}} or {{"grounded": false}}"""

    try:
        import re
        raw = _llm("Return only valid JSON.", prompt, model=_FAST_MODEL, max_tokens=20)
        m = re.search(r'"grounded":\s*(true|false)', raw)
        state["is_grounded"] = (m.group(1) == "true") if m else True
    except Exception:
        state["is_grounded"] = True   # assume grounded on failure

    # Append grounding status to answer
    grounding_note = "" if state["is_grounded"] else "\n\n⚠️ Note: This answer may contain information not directly in the retrieved sources."
    state["answer"] = state["generation"] + grounding_note
    state["trace"][-1]["is_grounded"] = state["is_grounded"]
    return state


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_agentic_rag_graph():
    g = StateGraph(RAGState)

    g.add_node("plan_queries",     plan_queries)
    g.add_node("retrieve",         retrieve)
    g.add_node("grade_docs",       grade_docs)
    g.add_node("rewrite_query",    rewrite_query)
    g.add_node("generate",         generate)
    g.add_node("check_grounding",  check_grounding)

    g.set_entry_point("plan_queries")
    g.add_edge("plan_queries", "retrieve")
    g.add_edge("retrieve",     "grade_docs")

    # Conditional: enough relevant docs → generate, else → rewrite → retrieve
    g.add_conditional_edges(
        "grade_docs",
        _route_after_grade,
        {"generate": "generate", "rewrite_query": "rewrite_query"},
    )
    g.add_edge("rewrite_query",   "retrieve")    # retry retrieval with rewritten query
    g.add_edge("generate",        "check_grounding")
    g.add_edge("check_grounding", END)

    return g.compile()


_rag_graph = None


def get_rag_graph():
    global _rag_graph
    if _rag_graph is None:
        _rag_graph = build_agentic_rag_graph()
    return _rag_graph


def ask(
    question:     str,
    project_id:   int,
    source_type:  str | None = None,
    run_eval:     bool = True,
) -> dict:
    """Public entry point — run the agentic RAG and return structured result.

    run_eval=True: run RAGAS evaluation after generation and persist to DB.
    """
    initial: RAGState = {
        "question":        question,
        "project_id":      project_id,
        "source_type":     source_type,
        "sub_queries":     [],
        "retrieved_docs":  [],
        "graded_docs":     [],
        "rewritten_query": "",
        "generation":      "",
        "is_grounded":     True,
        "answer":          "",
        "sources":         [],
        "hop_count":       0,
        "trace":           [],
        "error":           "",
    }
    try:
        graph = get_rag_graph()
        final: RAGState = graph.invoke(initial)
    except Exception as exc:
        logger.exception("Agentic RAG failed: %s", exc)
        return {
            "answer":       f"RAG pipeline error: {exc}",
            "sources":      [],
            "sub_queries":  [question],
            "hops":         0,
            "is_grounded":  False,
            "trace":        [],
            "ragas_metrics": None,
        }

    # RAGAS evaluation (Prompt 7) ─────────────────────────────────────────────
    ragas_metrics: dict | None = None
    if run_eval and final.get("answer"):
        try:
            contexts = [
                d["content"]
                for d in final.get("graded_docs", [])
                if d.get("relevance") == "yes"
            ]
            if not contexts:
                contexts = [d["content"] for d in final.get("retrieved_docs", [])[:4]]

            ragas_metrics = ragas_eval.evaluate(
                question=question,
                answer=final["answer"],
                contexts=contexts,
            )
            # Persist to DB (best-effort — don't fail the response on store errors)
            try:
                eval_store.ensure_schema()
                eval_store.save_eval(
                    project_id=project_id,
                    question=question,
                    answer=final["answer"],
                    metrics=ragas_metrics,
                    is_grounded=final.get("is_grounded", True),
                )
            except Exception as db_exc:
                logger.warning("eval_store.save_eval failed (non-fatal): %s", db_exc)
        except Exception as eval_exc:
            logger.warning("RAGAS eval failed (non-fatal): %s", eval_exc)

    return {
        "answer":        final["answer"],
        "sources":       final["sources"],
        "sub_queries":   final["sub_queries"],
        "hops":          final["hop_count"],
        "is_grounded":   final["is_grounded"],
        "trace":         final["trace"],
        "ragas_metrics": ragas_metrics,
    }
