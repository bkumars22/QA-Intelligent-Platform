"""
Azure OpenAI provider — optional alternative to Groq for defect explanations.

Activated when AZURE_OPENAI_API_KEY is set; falls back to Groq otherwise
(see _llm_explain in agents/pipeline_agent.py). Mirrors the existing _llm()
call shape (system + user prompt -> text) so it drops into that one call
site without changing any other pipeline stage.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Iterator

from openai import AzureOpenAI

logger = logging.getLogger("qaip.providers.azure_openai")

# Approximate Azure OpenAI GPT-4o pricing (USD per 1M tokens). The deployment
# name is customer-chosen and doesn't tell us the underlying model, so this is
# a best-effort estimate for the cost dashboard rather than an exact figure —
# same tradeoff SCIP's AIMO wiring made for its Haiku cost table.
DEFAULT_COST_PER_1M_INPUT = 2.50
DEFAULT_COST_PER_1M_OUTPUT = 10.00


@dataclass
class CompletionResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


def is_configured() -> bool:
    """True when AZURE_OPENAI_API_KEY is set — the routing switch other modules check."""
    return bool(os.getenv("AZURE_OPENAI_API_KEY"))


class AzureOpenAIProvider:
    """
    Thin wrapper around openai.AzureOpenAI matching the codebase's existing
    Groq call shape (system + user prompt -> text), plus streaming, token
    usage, and cost calculation.
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ):
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY", "")
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

        if not (self.api_key and self.endpoint and self.deployment):
            raise ValueError(
                "AzureOpenAIProvider requires AZURE_OPENAI_API_KEY, "
                "AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_DEPLOYMENT_NAME"
            )

        self._client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens / 1_000_000 * DEFAULT_COST_PER_1M_INPUT
            + completion_tokens / 1_000_000 * DEFAULT_COST_PER_1M_OUTPUT
        )

    def complete(
        self,
        prompt: str,
        system: str = "You are an expert QA engineer.",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> CompletionResult:
        """Non-streaming chat completion. Raises on failure — caller decides fallback."""
        resp = self._client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        return CompletionResult(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=self.estimate_cost(prompt_tokens, completion_tokens),
        )

    def stream(
        self,
        prompt: str,
        system: str = "You are an expert QA engineer.",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> Iterator[str]:
        """Yield text deltas as they arrive."""
        resp_stream = self._client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        for chunk in resp_stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
