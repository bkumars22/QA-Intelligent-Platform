"""
Unit tests for the Azure OpenAI provider and its routing into pipeline_agent's
Stage 5 defect explanation (_llm_explain), with mocked Azure/Groq clients —
no real API keys required.

Run with:  pytest tests/test_azure_provider.py -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from providers.azure_provider import AzureOpenAIProvider, is_configured


AZURE_ENV = {
    "AZURE_OPENAI_API_KEY": "fake-key",
    "AZURE_OPENAI_ENDPOINT": "https://fake.openai.azure.com/",
    "AZURE_OPENAI_DEPLOYMENT_NAME": "fake-gpt4o",
    "AZURE_OPENAI_API_VERSION": "2024-02-01",
}


def _make_azure_response(text: str, prompt_tokens: int = 100, completion_tokens: int = 50) -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = prompt_tokens
    resp.usage.completion_tokens = completion_tokens
    return resp


def _make_groq_response(text: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestIsConfigured:
    def test_false_when_no_key(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        assert is_configured() is False

    def test_true_when_key_set(self, monkeypatch):
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake-key")
        assert is_configured() is True


class TestAzureOpenAIProvider:
    def test_requires_all_config(self, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
        monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT_NAME", raising=False)
        with pytest.raises(ValueError):
            AzureOpenAIProvider()

    @patch("providers.azure_provider.AzureOpenAI")
    def test_complete_returns_text_and_usage(self, mock_azure_class, monkeypatch):
        for k, v in AZURE_ENV.items():
            monkeypatch.setenv(k, v)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_azure_response(
            '{"root_cause": "x", "severity": "P1"}', prompt_tokens=200, completion_tokens=40
        )
        mock_azure_class.return_value = mock_client

        provider = AzureOpenAIProvider()
        result = provider.complete("explain this failure")

        assert result.text == '{"root_cause": "x", "severity": "P1"}'
        assert result.prompt_tokens == 200
        assert result.completion_tokens == 40
        assert result.cost_usd > 0

    @patch("providers.azure_provider.AzureOpenAI")
    def test_complete_uses_deployment_as_model(self, mock_azure_class, monkeypatch):
        for k, v in AZURE_ENV.items():
            monkeypatch.setenv(k, v)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_azure_response("ok")
        mock_azure_class.return_value = mock_client

        AzureOpenAIProvider().complete("prompt")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "fake-gpt4o"


class TestLlmExplainRouting:
    """_llm_explain lives in agents.pipeline_agent — Stage 5 only."""

    @patch("agents.pipeline_agent._groq")
    def test_falls_back_to_groq_when_azure_not_configured(self, mock_groq_factory, monkeypatch):
        monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response("groq explanation")
        mock_groq_factory.return_value = mock_client

        from agents.pipeline_agent import _llm_explain
        result = _llm_explain("explain this")

        assert result == "groq explanation"
        mock_client.chat.completions.create.assert_called_once()

    @patch("agents.pipeline_agent._groq")
    @patch("providers.azure_provider.AzureOpenAI")
    def test_uses_azure_when_configured(self, mock_azure_class, mock_groq_factory, monkeypatch):
        for k, v in AZURE_ENV.items():
            monkeypatch.setenv(k, v)
        mock_azure_client = MagicMock()
        mock_azure_client.chat.completions.create.return_value = _make_azure_response("azure explanation")
        mock_azure_class.return_value = mock_azure_client

        from agents.pipeline_agent import _llm_explain
        result = _llm_explain("explain this")

        assert result == "azure explanation"
        mock_azure_client.chat.completions.create.assert_called_once()
        mock_groq_factory.assert_not_called()

    @patch("agents.pipeline_agent._groq")
    @patch("providers.azure_provider.AzureOpenAI")
    def test_falls_back_to_groq_when_azure_call_fails(self, mock_azure_class, mock_groq_factory, monkeypatch):
        for k, v in AZURE_ENV.items():
            monkeypatch.setenv(k, v)
        mock_azure_client = MagicMock()
        mock_azure_client.chat.completions.create.side_effect = Exception("Azure rate limited")
        mock_azure_class.return_value = mock_azure_client

        mock_groq_client = MagicMock()
        mock_groq_client.chat.completions.create.return_value = _make_groq_response("groq fallback explanation")
        mock_groq_factory.return_value = mock_groq_client

        from agents.pipeline_agent import _llm_explain
        result = _llm_explain("explain this")

        assert result == "groq fallback explanation"
        mock_groq_client.chat.completions.create.assert_called_once()
