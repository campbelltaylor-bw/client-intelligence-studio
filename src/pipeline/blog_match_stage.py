from src.models import BlogRecommendation, CRMAccount, WebResearchResult
from src.providers.base import BlogCatalogProvider


def run_blog_match_stage(
    crm_data: CRMAccount | None,
    web_research: WebResearchResult,
    blog_provider: BlogCatalogProvider,
    ai_scorer,  # callable: (company_profile_text, blogs) -> list[BlogRecommendation]
) -> list[BlogRecommendation]:
    blogs = blog_provider.load()
    company_profile = _build_profile_text(crm_data, web_research)
    return ai_scorer(company_profile, blogs)


def _build_profile_text(crm_data: CRMAccount | None, web_research: WebResearchResult) -> str:
    lines = [f"Company: {web_research.company_name}"]
    if web_research.company_description:
        lines.append(f"Description: {web_research.company_description.value}")
    if crm_data:
        if crm_data.industry:
            lines.append(f"Industry (CRM): {crm_data.industry.value}")
        if crm_data.company_size:
            lines.append(f"Size (CRM): {crm_data.company_size.value}")
        if crm_data.products_discussed:
            products = "; ".join(p.value for p in crm_data.products_discussed)
            lines.append(f"Products Discussed (CRM): {products}")
    if web_research.recent_news:
        news = "; ".join(n.value for n in web_research.recent_news[:3])
        lines.append(f"Recent News: {news}")
    if web_research.technology_signals:
        signals = "; ".join(s.value for s in web_research.technology_signals[:3])
        lines.append(f"Technology Signals: {signals}")
    return "\n".join(lines)
