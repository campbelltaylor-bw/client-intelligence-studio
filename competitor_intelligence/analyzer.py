import json
import re

import anthropic

from competitor_intelligence.models import (
    AudienceOverlap,
    BattleCard,
    CompetitiveAnalysis,
    CompetitiveGaps,
    CompetitorProfile,
    ObjectionHandler,
    ProductComparison,
)
from competitor_intelligence.prompts import (
    BATTLE_CARD_SYSTEM,
    BATTLE_CARD_USER,
    COMPETITIVE_ANALYSIS_SYSTEM,
    COMPETITIVE_ANALYSIS_USER,
)


class CompetitorAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def analyze(
        self,
        profile: CompetitorProfile,
        our_profile_text: str,
        our_company_name: str = "Context Analytics",
        our_company_short: str = "CA",
    ) -> CompetitiveAnalysis:
        competitor_json = profile.model_dump_json(indent=2)
        system = COMPETITIVE_ANALYSIS_SYSTEM.format(our_company_name=our_company_name)
        prompt = COMPETITIVE_ANALYSIS_USER.format(
            company_name=profile.company_name,
            our_company_name=our_company_name,
            our_profile_text=our_profile_text,
            competitor_profile_json=competitor_json,
        )
        with self._client.messages.stream(
            model=self._model,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            raw = stream.get_final_message().content[0].text

        data = json.loads(_extract_json(raw))
        return _parse_analysis(data)


def generate_battle_card(
    api_key: str,
    model: str,
    company_name: str,
    analysis: CompetitiveAnalysis,
    our_company_name: str = "Context Analytics",
    our_company_short: str = "CA",
) -> BattleCard:
    system = BATTLE_CARD_SYSTEM.format(our_company_name=our_company_name)
    prompt = BATTLE_CARD_USER.format(
        company_name=company_name,
        our_company_name=our_company_name,
        our_company_short=our_company_short,
        analysis_json=analysis.model_dump_json(indent=2),
    )
    client = anthropic.Anthropic(api_key=api_key)
    try:
        with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            raw = stream.get_final_message().content[0].text
        data = json.loads(_extract_json(raw))
        return _parse_battle_card(data)
    except Exception:
        return BattleCard(
            positioning_statement="Battle card generation failed — re-run to retry.",
        )


def _parse_battle_card(data: dict) -> BattleCard:
    raw_handlers = data.get("objection_handlers") or []
    handlers = []
    for h in raw_handlers:
        if not isinstance(h, dict):
            continue
        handlers.append(ObjectionHandler(
            objection=h.get("objection", ""),
            response=h.get("response", ""),
        ))
    return BattleCard(
        positioning_statement=data.get("positioning_statement", ""),
        top_differentiators=[str(d) for d in (data.get("top_differentiators") or [])],
        objection_handlers=handlers,
        when_ca_wins=[str(s) for s in (data.get("when_ca_wins") or [])],
        when_they_win=[str(s) for s in (data.get("when_they_win") or [])],
        discovery_questions=[str(q) for q in (data.get("discovery_questions") or [])],
    )


def _extract_json(raw: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    return match.group(1).strip() if match else raw.strip()


def _parse_analysis(data: dict) -> CompetitiveAnalysis:
    raw_comparisons = data.get("product_comparisons") or []
    comparisons = []
    for c in raw_comparisons:
        if not isinstance(c, dict):
            continue
        comparisons.append(ProductComparison(
            our_product=c.get("our_product") or "",
            their_product=c.get("their_product") or "",
            overlap_summary=c.get("overlap_summary") or "",
            differentiator=c.get("differentiator") or "",
        ))

    raw_overlap = data.get("audience_overlap") or {}
    overlap = AudienceOverlap(
        shared_segments=[str(s) for s in (raw_overlap.get("shared_segments") or [])],
        our_exclusive_segments=[str(s) for s in (raw_overlap.get("our_exclusive_segments") or [])],
        their_exclusive_segments=[str(s) for s in (raw_overlap.get("their_exclusive_segments") or [])],
    )

    raw_gaps = data.get("gaps") or {}
    gaps = CompetitiveGaps(
        we_cover_they_dont=[str(g) for g in (raw_gaps.get("we_cover_they_dont") or [])],
        they_cover_we_dont=[str(g) for g in (raw_gaps.get("they_cover_we_dont") or [])],
    )

    return CompetitiveAnalysis(
        executive_summary=data.get("executive_summary", ""),
        product_comparisons=comparisons,
        audience_overlap=overlap,
        our_strengths=[str(s) for s in (data.get("our_strengths") or [])],
        their_strengths=[str(s) for s in (data.get("their_strengths") or [])],
        gaps=gaps,
    )
