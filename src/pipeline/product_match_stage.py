import yaml

from src.models import CRMAccount, ProductRecommendation, WebResearchResult


def run_product_match_stage(
    crm_data: CRMAccount | None,
    web_research: WebResearchResult,
    product_catalog_path: str,
    ai_scorer,  # callable: (company_profile_text, products) -> list[ProductRecommendation]
) -> list[ProductRecommendation]:
    with open(product_catalog_path) as f:
        catalog = yaml.safe_load(f)
    products = _load_products(catalog)
    company_profile = _build_profile_text(crm_data, web_research)
    return ai_scorer(company_profile, products)


def _load_products(catalog: dict) -> list[dict]:
    """
    Normalise both product catalog formats to the flat dict the scorer expects.

    Old format (product_catalog.yaml):
        products:
          - name: ...
            description: ...
            use_cases: [str, ...]
            target_segments: [str, ...]

    New format (context_analytics_products.yaml):
        product_categories:
          - category: ...
            description: ...
            strategies / use_cases / features / analytics: [...]
    """
    if "products" in catalog:
        return catalog["products"]

    rows = []
    for item in catalog.get("product_categories", []):
        name = item.get("category", "")
        if not name:
            continue

        # Build a rich description from available fields
        desc_parts = [item.get("description", "").strip()]
        feeds = item.get("data_feeds", [])
        if feeds:
            feed_names = [f["name"] for f in feeds if isinstance(f, dict)]
            if feed_names:
                desc_parts.append(f"Data feeds: {', '.join(feed_names)}.")
        key_metric = item.get("key_metric")
        if isinstance(key_metric, dict) and key_metric.get("name"):
            desc_parts.append(
                f"Key metric: {key_metric['name']} — {key_metric.get('description', '')}".strip(" —")
            )
        website = item.get("website", "")
        if website:
            desc_parts.append(f"Learn more: {website}")

        # Extract use-case / strategy names from whichever field exists
        use_cases = _extract_list_names(
            item.get("use_cases")
            or item.get("strategies")
            or item.get("features")
            or item.get("analytics")
            or item.get("delivery_channels")
            or []
        )

        rows.append({
            "name": name,
            "description": " ".join(p for p in desc_parts if p),
            "use_cases": use_cases,
            "target_segments": [],
        })

    return rows


def _extract_list_names(items: list) -> list[str]:
    """Return string labels from a list that may contain strings or dicts."""
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            label = item.get("name") or item.get("description", "")
            if label:
                result.append(label)
    return result


def _build_profile_text(crm_data: CRMAccount | None, web_research: WebResearchResult) -> str:
    lines = [f"Company: {web_research.company_name}"]
    if web_research.company_description:
        lines.append(f"Description: {web_research.company_description.value}")
    if crm_data:
        if crm_data.industry:
            lines.append(f"Industry (CRM_FACT): {crm_data.industry.value}")
        if crm_data.company_size:
            lines.append(f"Size (CRM_FACT): {crm_data.company_size.value}")
        if crm_data.products_discussed:
            products = "; ".join(p.value for p in crm_data.products_discussed)
            lines.append(f"Products Already Discussed (CRM_FACT): {products}")
        if crm_data.open_questions:
            questions = "; ".join(q.value for q in crm_data.open_questions)
            lines.append(f"Open Client Questions (CRM_FACT): {questions}")
    if web_research.recent_news:
        news = "; ".join(n.value for n in web_research.recent_news[:3])
        lines.append(f"Recent News (PUBLIC_FACT): {news}")
    if web_research.technology_signals:
        signals = "; ".join(s.value for s in web_research.technology_signals[:3])
        lines.append(f"Technology Signals (PUBLIC_FACT): {signals}")
    return "\n".join(lines)
