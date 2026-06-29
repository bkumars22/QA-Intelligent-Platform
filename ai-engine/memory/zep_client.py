"""
Zep memory layer for QAIP Agentic RAG.

When ZEP_API_KEY is set → uses Zep Cloud (zep-cloud SDK).
Otherwise             → falls back to InMemorySessionStore (in-process, lost on restart).

Public API (both paths):
  ensure_session(session_id, user_id=None)
  add_messages(session_id, question, answer)
  get_context(session_id)  → {"context": str, "facts": list[str], "messages": list[dict]}
  search(session_id, query, top_k=5) → list[dict]
  delete_session(session_id)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger("qaip.memory.zep")

_ZEP_API_KEY = os.getenv("ZEP_API_KEY", "")
_MAX_MESSAGES = 50   # per session in fallback store


# ── In-process fallback ───────────────────────────────────────────────────────

class InMemorySessionStore:
    """Zero-dependency session memory — survives per process only."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def ensure_session(self, session_id: str, user_id: str | None = None) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "session_id": session_id,
                "user_id":    user_id or session_id,
                "messages":   [],
                "created_at": time.time(),
            }

    def add_messages(self, session_id: str, question: str, answer: str) -> None:
        self.ensure_session(session_id)
        msgs = self._sessions[session_id]["messages"]
        msgs.append({"role": "user",      "content": question, "ts": time.time()})
        msgs.append({"role": "assistant", "content": answer,   "ts": time.time()})
        # Trim to last _MAX_MESSAGES (keep most recent)
        if len(msgs) > _MAX_MESSAGES:
            self._sessions[session_id]["messages"] = msgs[-_MAX_MESSAGES:]

    def get_context(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._sessions:
            return {"context": "", "facts": [], "messages": []}
        msgs = self._sessions[session_id]["messages"]
        last_pairs = msgs[-10:]   # last 5 turns
        context_lines = []
        for m in last_pairs:
            prefix = "User" if m["role"] == "user" else "Assistant"
            context_lines.append(f"{prefix}: {m['content'][:300]}")
        context = "\n".join(context_lines) if context_lines else ""
        return {
            "context":  context,
            "facts":    [],
            "messages": [{"role": m["role"], "content": m["content"]} for m in last_pairs],
        }

    def search(self, session_id: str, query: str, top_k: int = 5) -> list[dict]:
        if session_id not in self._sessions:
            return []
        q = query.lower()
        hits = []
        for m in self._sessions[session_id]["messages"]:
            if any(word in m["content"].lower() for word in q.split()):
                hits.append({
                    "role":    m["role"],
                    "content": m["content"],
                    "score":   1.0,
                })
        return hits[:top_k]

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def session_info(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._sessions:
            return {"exists": False}
        s = self._sessions[session_id]
        return {
            "exists":        True,
            "session_id":    session_id,
            "message_count": len(s["messages"]),
            "created_at":    s["created_at"],
        }


# ── Zep Cloud wrapper ─────────────────────────────────────────────────────────

class ZepCloudClient:
    """Thin wrapper around zep-cloud SDK with graceful error handling."""

    def __init__(self, api_key: str):
        from zep_cloud.client import Zep as _Zep
        from zep_cloud import Message as _Msg
        self._Zep = _Zep
        self._Msg = _Msg
        self._client = _Zep(api_key=api_key)
        logger.info("[zep] connected to Zep Cloud")

    def ensure_session(self, session_id: str, user_id: str | None = None) -> None:
        try:
            self._client.memory.add_session(
                session_id=session_id,
                user_id=user_id or session_id,
            )
        except Exception as exc:
            # Session may already exist — Zep returns error on duplicate add
            if "already exists" not in str(exc).lower():
                logger.warning("[zep] ensure_session error (ignored): %s", exc)

    def add_messages(self, session_id: str, question: str, answer: str) -> None:
        try:
            self.ensure_session(session_id)
            self._client.memory.add(
                session_id=session_id,
                messages=[
                    self._Msg(role="user",      role_type="user",      content=question),
                    self._Msg(role="assistant", role_type="assistant", content=answer),
                ],
            )
        except Exception as exc:
            logger.warning("[zep] add_messages error (non-fatal): %s", exc)

    def get_context(self, session_id: str) -> dict[str, Any]:
        try:
            self.ensure_session(session_id)
            mem = self._client.memory.get(session_id=session_id)
            facts = [f.fact for f in (mem.relevant_facts or []) if hasattr(f, "fact")]
            messages = [
                {"role": m.role_type or m.role, "content": m.content}
                for m in (mem.messages or [])
                if m.content
            ]
            return {
                "context":  mem.context or "",
                "facts":    facts,
                "messages": messages,
            }
        except Exception as exc:
            logger.warning("[zep] get_context error: %s", exc)
            return {"context": "", "facts": [], "messages": []}

    def search(self, session_id: str, query: str, top_k: int = 5) -> list[dict]:
        try:
            results = self._client.memory.search_sessions(
                text=query,
                search_scope="messages",
                limit=top_k,
            )
            return [
                {"role": r.message.role_type if r.message else "unknown",
                 "content": r.message.content if r.message else "",
                 "score": r.score or 0.0,
                 "session_id": r.session_id}
                for r in (results.results or [])
            ]
        except Exception as exc:
            logger.warning("[zep] search error: %s", exc)
            return []

    def delete_session(self, session_id: str) -> None:
        try:
            self._client.memory.delete(session_id=session_id)
        except Exception as exc:
            logger.warning("[zep] delete_session error (non-fatal): %s", exc)

    def session_info(self, session_id: str) -> dict[str, Any]:
        try:
            mem = self._client.memory.get(session_id=session_id)
            return {
                "exists":        True,
                "session_id":    session_id,
                "message_count": len(mem.messages or []),
                "context":       mem.context or "",
                "facts":         [f.fact for f in (mem.relevant_facts or []) if hasattr(f, "fact")],
            }
        except Exception as exc:
            return {"exists": False, "error": str(exc)}


# ── Singleton factory ─────────────────────────────────────────────────────────

_client: ZepCloudClient | InMemorySessionStore | None = None


def get_client() -> ZepCloudClient | InMemorySessionStore:
    global _client
    if _client is not None:
        return _client

    if _ZEP_API_KEY:
        try:
            _client = ZepCloudClient(api_key=_ZEP_API_KEY)
            return _client
        except ImportError:
            logger.warning("[zep] zep-cloud not installed — falling back to in-memory store")
        except Exception as exc:
            logger.warning("[zep] Zep Cloud init failed (%s) — falling back to in-memory store", exc)

    _client = InMemorySessionStore()
    logger.info("[zep] using in-memory session store (ZEP_API_KEY not set or zep-cloud not installed)")
    return _client


def get_backend_name() -> str:
    c = get_client()
    return "zep_cloud" if isinstance(c, ZepCloudClient) else "in_memory"
