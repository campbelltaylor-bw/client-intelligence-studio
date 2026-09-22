import json
import re

import anthropic

from competitor_intelligence.models import CompetitorProduct, CompetitorProfile
from competitor_intelligence.prompts import (
    COMPETITOR_RESEARCH_SYSTEM,
    COMPETITOR_RESEARCH_USER,
    MARKET_LANDSCAPE_SYSTEM,
    MARKET_LANDSCAPE_USER,
    PRODUCT_SEARCH_SYSTEM,
    PRODUCT_SEARCH_USER,
)

_WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}


class CompetitorResearcher:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def research(self, company_name: str, website_url: str | None = None) -> CompetitorProfile:
        website_hint = f"Their website: {website_url}" if website_url else ""
        prompt = COMPETITOR_RESEARCH_USER.format(
            company_name=company_name,
            website_hint=website_hint,
        )

        raw = self._run_tool_loop(prompt)

        if not raw.strip():
            return CompetitorProfile(company_name=company_name)

        try:
            data = json.loads(_extract_json(raw))
            return _parse_profile(data, company_name)
        except Exception:
            return CompetitorProfile(company_name=company_name)

    def scan_market(
        self,
        category_name: str,
        category_description: str,
        our_company_name: str = "Context Analytics",
    ) -> list:
        from competitor_intelligence.models import MarketEntry
        system = MARKET_LANDSCAPE_SYSTEM.format(our_company_name=our_company_name)
        prompt = MARKET_LANDSCAPE_USER.format(
            our_company_name=our_company_name,
            category_name=category_name,
            category_description=(category_description or "").strip(),
        )
        raw = self._run_tool_loop(prompt, system=system)
        try:
            items = json.loads(_extract_json(raw))
            if not isinstance(items, list):
                return []
            return [
                MarketEntry(
                    company=p.get("company", "Unknown"),
                    product=p.get("product"),
                    description=p.get("description"),
                    target_audience=p.get("target_audience"),
                    website=p.get("website"),
                )
                for p in items
                if isinstance(p, dict)
            ]
        except Exception:
            return []

    def research_products(
        self,
        company_name: str,
        ca_product_categories: list[str],
        our_company_name: str = "Context Analytics",
    ) -> list[CompetitorProduct]:
        categories_text = "\n".join(f"- {c}" for c in ca_product_categories)
        prompt = PRODUCT_SEARCH_USER.format(
            company_name=company_name,
            our_company_name=our_company_name,
            ca_product_categories=categories_text,
        )
        raw = self._run_tool_loop(prompt, system=PRODUCT_SEARCH_SYSTEM)
        try:
            items = json.loads(_extract_json(raw))
            if not isinstance(items, list):
                return []
            return [
                CompetitorProduct(
                    name=p.get("name", "Unknown"),
                    launched=p.get("launched"),
                    target_audience=p.get("target_audience"),
                    primary_users=p.get("primary_users"),
                    use_cases=[str(u) for u in (p.get("use_cases") or [])],
                    coverage=p.get("coverage"),
                    deliverable_formats=[str(f) for f in (p.get("deliverable_formats") or [])],
                    source_url=p.get("source_url"),
                )
                for p in items
                if isinstance(p, dict)
            ]
        except Exception:
            return []

    def _run_tool_loop(self, prompt: str, system: str = COMPETITOR_RESEARCH_SYSTEM) -> str:
        msgs: list[dict] = [{"role": "user", "content": prompt}]
        for _ in range(10):
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=8192,
                system=system,
                messages=msgs,
                tools=[_WEB_SEARCH_TOOL],
                betas=["web-search-2025-03-05"],
            )
            texts = [b.text for b in response.content if hasattr(b, "text") and b.type == "text"]
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason == "end_turn" or not tool_uses:
                return " ".join(texts)
            msgs.append({"role": "assistant", "content": response.content})
            msgs.append({
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": tu.id, "content": ""}
                    for tu in tool_uses
                ],
            })
        return ""


def _extract_json(raw: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    return match.group(1).strip() if match else raw.strip()


def _parse_profile(data: dict, company_name: str) -> CompetitorProfile:
    raw_products = data.get("products") or []
    products = []
    for p in raw_products:
        if not isinstance(p, dict):
            continue
        products.append(CompetitorProduct(
            name=p.get("name", "Unknown"),
            launched=p.get("launched"),
            target_audience=p.get("target_audience"),
            primary_users=p.get("primary_users"),
            use_cases=[str(u) for u in (p.get("use_cases") or [])],
            coverage=p.get("coverage"),
            deliverable_formats=[str(f) for f in (p.get("deliverable_formats") or [])],
            source_url=p.get("source_url"),
        ))

    return CompetitorProfile(
        company_name=data.get("company_name") or company_name,
        website=data.get("website"),
        about=data.get("about"),
        company_size=data.get("company_size"),
        headquarters=data.get("headquarters"),
        additional_locations=[str(l) for l in (data.get("additional_locations") or [])],
        founded=data.get("founded"),
        mission_statement=data.get("mission_statement"),
        market_cap=data.get("market_cap"),
        products=products,
        recent_news=[str(n) for n in (data.get("recent_news") or [])[:8]],
        source_urls=[str(u) for u in (data.get("source_urls") or []) if isinstance(u, str)],
    )
