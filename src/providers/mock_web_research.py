import json

from src.models import TaggedFact, WebResearchResult
from src.providers.base import WebResearchProvider


class MockWebResearchProvider(WebResearchProvider):
    def __init__(self, data_path: str = "data/mock_web_research.json"):
        with open(data_path) as f:
            self._data: dict[str, dict] = json.load(f)

    def research(self, company_name: str, website_url: str | None) -> WebResearchResult:
        raw = self._data.get(company_name)
        if not raw:
            return WebResearchResult(
                company_name=company_name,
                company_description=TaggedFact(
                    value=f"No mock web research available for '{company_name}'. This is a new prospect.",
                    source="PUBLIC_FACT",
                ),
            )

        def _fact(d: dict | None) -> TaggedFact | None:
            return TaggedFact(**d) if d else None

        def _facts(lst: list[dict]) -> list[TaggedFact]:
            return [TaggedFact(**d) for d in lst]

        return WebResearchResult(
            company_name=raw["company_name"],
            company_description=_fact(raw.get("company_description")),
            recent_news=_facts(raw.get("recent_news", [])),
            technology_signals=_facts(raw.get("technology_signals", [])),
            source_urls=raw.get("source_urls", []),
        )
