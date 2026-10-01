import json
import re

from src.models import TaggedFact, WebResearchResult
from src.prompts.prompts import WEB_RESEARCH_SYSTEM, WEB_RESEARCH_USER
from src.providers.base import WebResearchProvider

_WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


class ClaudeWebResearchProvider(WebResearchProvider):
    def __init__(self, ai_client):
        self._client = ai_client

    def research(self, company_name: str, website_url: str | None) -> WebResearchResult:
        website_hint = f"Their website: {website_url}" if website_url else ""
        prompt = WEB_RESEARCH_USER.format(company_name=company_name, website_hint=website_hint)
        try:
            raw = self._client.call_with_tools(
                messages=[{"role": "user", "content": prompt}],
                tools=[_WEB_SEARCH_TOOL],
                system_prompt=WEB_RESEARCH_SYSTEM,
            )
            data = json.loads(_extract_json(raw))
        except Exception:
            return WebResearchResult(company_name=company_name)

        company_description = None
        desc_text = data.get("company_description", "")
        if desc_text:
            company_description = TaggedFact(value=desc_text, source="PUBLIC_FACT")

        recent_news = []
        for item in (data.get("recent_news") or [])[:5]:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            url = item.get("url", "") if isinstance(item, dict) else ""
            if text:
                recent_news.append(TaggedFact(value=text, source="PUBLIC_FACT", evidence=url or None))

        technology_signals = []
        for item in (data.get("technology_signals") or [])[:5]:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            url = item.get("url", "") if isinstance(item, dict) else ""
            if text:
                technology_signals.append(TaggedFact(value=text, source="PUBLIC_FACT", evidence=url or None))

        source_urls = [u for u in (data.get("source_urls") or []) if isinstance(u, str)]

        return WebResearchResult(
            company_name=company_name,
            company_description=company_description,
            recent_news=recent_news,
            technology_signals=technology_signals,
            source_urls=source_urls,
        )


def _extract_json(raw: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    return match.group(1).strip() if match else raw.strip()
