import json
import re
from pathlib import Path

import yaml


def load_watchlist(path: Path) -> list[dict]:
    """Load competitors_to_watch.yaml. Returns [] if missing or malformed."""
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data.get("competitors") or []
    except Exception:
        return []


def add_to_watchlist(
    path: Path,
    name: str,
    website: str = "",
    category: str = "",
    why_relevant: str = "",
) -> bool:
    """Append a new competitor to the watchlist YAML.

    Returns True if added, False if already present (case-insensitive name match).
    """
    if not name.strip():
        return False

    existing = load_watchlist(path)
    existing_names = {c.get("name", "").lower() for c in existing}
    if name.strip().lower() in existing_names:
        return False

    new_entry = {
        "name": name.strip(),
        "website": website.strip(),
        "category": category.strip() or "Other",
        "why_relevant": why_relevant.strip(),
    }
    existing.append(new_entry)

    path.write_text(
        yaml.dump({"competitors": existing}, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return True


_COMPANY_DISCOVER_CONTEXT = {
    "ca": {
        "description": (
            "Context Analytics, a financial alternative data company specializing in: "
            "social media sentiment (S-Factor scores), machine-readable SEC and global regulatory "
            "filings, quantitative news feeds, podcast data, private company data, and "
            "AI-generated summaries — all targeting institutional investors such as hedge funds "
            "and asset managers."
        ),
        "categories": (
            "Financial NLP & Sentiment | News Sentiment & NLP | Alt-Data Discovery | "
            "Alt-Data Marketplace | Consumer & Transaction Data | "
            "Private Company & Alternative Assets | Quantitative Alt-Data | Document Intelligence"
        ),
        "focus": (
            "social/news sentiment, NLP on filings, alt-data feeds for quant strategies, "
            "podcast/audio data, private company intelligence, or AI summaries for finance"
        ),
    },
    "bridgewise": {
        "description": (
            "Bridgewise, an AI investment intelligence company specializing in: AI-generated "
            "buy/hold/sell equity ratings for 10,000+ global stocks, white-label embedded "
            "investment intelligence for retail brokerage platforms, and AI-powered research "
            "tools for wealth managers, RIAs, and family offices."
        ),
        "categories": (
            "AI Investment Ratings | Embedded Financial Intelligence | AI Portfolio Tools | "
            "Wealth Tech Intelligence | Retail Brokerage AI | Fundamental Data Providers"
        ),
        "focus": (
            "AI-generated equity ratings or scores, white-label investment intelligence for "
            "brokerages, AI-powered stock analysis for retail investors or advisors, or "
            "embedded fintech data for wealth management platforms"
        ),
    },
}


def discover_competitors(
    api_key: str,
    model: str,
    existing_names: list[str],
    company_mode: str = "ca",
    our_company_name: str = "Context Analytics",
) -> list[dict]:
    """Ask Claude to suggest 5 new competitors not already in the watchlist.

    Returns a list of dicts with keys: name, website, category, why_relevant.
    """
    import anthropic

    ctx = _COMPANY_DISCOVER_CONTEXT.get(company_mode, _COMPANY_DISCOVER_CONTEXT["ca"])
    names_str = ", ".join(existing_names) if existing_names else "none yet"

    system = f"You are a competitive intelligence researcher for {ctx['description']}"

    user = f"""Suggest exactly 5 competitor companies NOT already in this list: {names_str}.

Focus on companies that overlap with at least one of {our_company_name}'s core offerings:
{ctx['focus']}.

Return ONLY a JSON array with no markdown fences:
[
  {{
    "name": "Company Name",
    "website": "https://...",
    "category": "one of: {ctx['categories']}",
    "why_relevant": "1-2 sentences on the overlap with {our_company_name}'s products"
  }}
]"""

    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        raw = stream.get_final_message().content[0].text

    cleaned = _extract_json(raw)
    try:
        suggestions = json.loads(cleaned)
        if isinstance(suggestions, list):
            return [s for s in suggestions if isinstance(s, dict) and s.get("name")]
    except Exception:
        pass
    return []


def _extract_json(raw: str) -> str:
    import re
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    return match.group(1).strip() if match else raw.strip()
