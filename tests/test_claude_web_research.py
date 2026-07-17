"""Tests for ClaudeWebResearchProvider — real API never called."""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.providers.claude_web_research import ClaudeWebResearchProvider, _extract_json


def _make_client(raw_response: str):
    client = MagicMock()
    client.call_with_tools.return_value = raw_response
    return client


_VALID_PAYLOAD = {
    "company_description": "Acme Fund is a quant long/short hedge fund with $4B AUM.",
    "recent_news": [
        {"text": "Acme Fund reported 22% return in Q1 2025.", "url": "https://example.com/news1"},
        {"text": "Acme hired new CTO from Two Sigma.", "url": "https://example.com/news2"},
    ],
    "technology_signals": [
        {"text": "Job posting: Senior Data Engineer (Python, Kafka).", "url": "https://example.com/jobs"},
    ],
    "source_urls": ["https://acmefund.com", "https://example.com/news1"],
}


class TestSuccessfulResearch:
    def test_returns_webresearchresult(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        provider = ClaudeWebResearchProvider(client)
        result = provider.research("Acme Fund", None)
        assert result.company_name == "Acme Fund"

    def test_company_description_populated(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert result.company_description is not None
        assert "quant" in result.company_description.value

    def test_recent_news_populated(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert len(result.recent_news) == 2
        assert "Q1 2025" in result.recent_news[0].value

    def test_technology_signals_populated(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert len(result.technology_signals) == 1
        assert "Data Engineer" in result.technology_signals[0].value

    def test_source_urls_populated(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert "https://acmefund.com" in result.source_urls

    def test_all_facts_tagged_public_fact(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert result.company_description.source == "PUBLIC_FACT"
        for fact in result.recent_news:
            assert fact.source == "PUBLIC_FACT"
        for fact in result.technology_signals:
            assert fact.source == "PUBLIC_FACT"

    def test_evidence_url_set_from_item(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert result.recent_news[0].evidence == "https://example.com/news1"

    def test_strips_markdown_fences(self):
        wrapped = f"```json\n{json.dumps(_VALID_PAYLOAD)}\n```"
        client = _make_client(wrapped)
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert result.company_description is not None

    def test_website_url_hint_passed_to_client(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        ClaudeWebResearchProvider(client).research("Acme Fund", "https://acmefund.com")
        call_args = client.call_with_tools.call_args
        prompt = call_args[1]["messages"][0]["content"] if call_args[1] else call_args[0][0][0]["content"]
        assert "https://acmefund.com" in prompt

    def test_no_website_url_omits_hint(self):
        client = _make_client(json.dumps(_VALID_PAYLOAD))
        ClaudeWebResearchProvider(client).research("Acme Fund", None)
        call_args = client.call_with_tools.call_args
        prompt = call_args[1]["messages"][0]["content"] if call_args[1] else call_args[0][0][0]["content"]
        assert "Their website:" not in prompt


class TestRobustness:
    def test_json_parse_failure_returns_empty_result(self):
        client = _make_client("This is not JSON at all.")
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert result.company_name == "Acme Fund"
        assert result.company_description is None
        assert result.recent_news == []

    def test_empty_response_returns_empty_result(self):
        client = _make_client("")
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert result.company_name == "Acme Fund"

    def test_missing_optional_fields_dont_crash(self):
        minimal = {"company_description": "A fund."}
        client = _make_client(json.dumps(minimal))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert result.company_description.value == "A fund."
        assert result.recent_news == []
        assert result.technology_signals == []

    def test_news_items_capped_at_5(self):
        payload = dict(_VALID_PAYLOAD)
        payload["recent_news"] = [{"text": f"news {i}", "url": ""} for i in range(10)]
        client = _make_client(json.dumps(payload))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert len(result.recent_news) <= 5

    def test_string_items_in_lists_handled(self):
        payload = {
            "company_description": "A fund.",
            "recent_news": ["Just a string item", "Another string"],
            "technology_signals": [],
            "source_urls": [],
        }
        client = _make_client(json.dumps(payload))
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert len(result.recent_news) == 2
        assert result.recent_news[0].value == "Just a string item"
        assert result.recent_news[0].evidence is None

    def test_call_with_tools_exception_returns_empty(self):
        client = MagicMock()
        client.call_with_tools.side_effect = RuntimeError("network error")
        result = ClaudeWebResearchProvider(client).research("Acme Fund", None)
        assert result.company_name == "Acme Fund"
        assert result.company_description is None


class TestExtractJson:
    def test_plain_json_passthrough(self):
        raw = '{"key": "value"}'
        assert _extract_json(raw) == raw

    def test_strips_json_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        assert _extract_json(raw) == '{"key": "value"}'

    def test_strips_plain_fence(self):
        raw = '```\n{"key": "value"}\n```'
        assert _extract_json(raw) == '{"key": "value"}'


class TestRunnerIntegration:
    def test_build_web_provider_returns_claude_provider(self):
        from src.pipeline.runner import _build_web_provider
        from src.providers.claude_web_research import ClaudeWebResearchProvider

        config = MagicMock()
        config.web_research_provider = "claude"
        ai_client = MagicMock()
        provider = _build_web_provider(config, ai_client)
        assert isinstance(provider, ClaudeWebResearchProvider)

    def test_build_web_provider_returns_mock_when_no_client(self):
        from src.providers.mock_web_research import MockWebResearchProvider
        from src.pipeline.runner import _build_web_provider

        config = MagicMock()
        config.web_research_provider = "claude"
        config.mock_web_research_path = "data/mock_web_research.json"
        provider = _build_web_provider(config, ai_client=None)
        assert isinstance(provider, MockWebResearchProvider)

    def test_build_web_provider_mock_repository(self):
        from src.providers.mock_web_research import MockWebResearchProvider
        from src.pipeline.runner import _build_web_provider

        config = MagicMock()
        config.web_research_provider = "mock"
        config.mock_web_research_path = "data/mock_web_research.json"
        provider = _build_web_provider(config, ai_client=MagicMock())
        assert isinstance(provider, MockWebResearchProvider)
