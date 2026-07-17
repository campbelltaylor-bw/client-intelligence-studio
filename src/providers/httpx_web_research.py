import re
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx

from src.models import TaggedFact, WebResearchResult
from src.providers.base import WebResearchProvider

_HEADERS = {"User-Agent": "ClientIntelligenceStudio/1.0 (internal research tool)"}


class HttpxWebResearchProvider(WebResearchProvider):
    def __init__(self, max_pages: int = 3):
        self._max_pages = max_pages

    def research(self, company_name: str, website_url: str | None) -> WebResearchResult:
        facts: list[TaggedFact] = []
        source_urls: list[str] = []

        if website_url:
            pages_fetched = 0
            urls_to_fetch = [website_url]

            for url in urls_to_fetch:
                if pages_fetched >= self._max_pages:
                    break
                if not self._robots_allowed(url):
                    continue
                text = self._fetch_text(url)
                if text:
                    facts.append(TaggedFact(
                        value=text[:1000],
                        source="PUBLIC_FACT",
                        evidence=url,
                    ))
                    source_urls.append(url)
                    pages_fetched += 1

        description = facts[0] if facts else TaggedFact(
            value=f"No public web content retrieved for {company_name}.",
            source="PUBLIC_FACT",
        )

        return WebResearchResult(
            company_name=company_name,
            company_description=description,
            recent_news=facts[1:],
            source_urls=source_urls,
        )

    def _robots_allowed(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(_HEADERS["User-Agent"], url)
        except Exception:
            return True  # allow on error, don't block

    def _fetch_text(self, url: str) -> str:
        try:
            resp = httpx.get(url, headers=_HEADERS, timeout=10, follow_redirects=True)
            resp.raise_for_status()
            # Strip HTML tags naively
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:2000]
        except Exception:
            return ""
