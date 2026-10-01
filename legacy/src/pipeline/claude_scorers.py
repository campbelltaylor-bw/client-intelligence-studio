"""
Real Claude-powered scoring and generation functions.
These replace the stub functions in runner.py when real AI is enabled.
"""
import json
import re

from src.ai_client import AnthropicClient
from src.models import (
    BlogRecommendation,
    ClientFacingOutputs,
    CRMAccount,
    InternalBrief,
    ProductRecommendation,
    TaggedFact,
    WebResearchResult,
)
from src.prompts.prompts import (
    BLOG_SCORING_SYSTEM,
    BLOG_SCORING_USER,
    INTERNAL_BRIEF_SYSTEM,
    INTERNAL_BRIEF_USER,
    MEETING_PREP_SYSTEM,
    MEETING_PREP_USER,
    MULTI_EMAIL_SYSTEM,
    MULTI_EMAIL_USER,
    OUTREACH_EMAIL_SYSTEM,
    OUTREACH_EMAIL_USER,
    PRODUCT_SCORING_SYSTEM,
    PRODUCT_SCORING_USER,
)


def _extract_json(raw: str) -> str:
    """Strip markdown code fences if Claude wrapped the JSON."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    return match.group(1).strip() if match else raw.strip()


def make_blog_scorer(client: AnthropicClient):
    def score_blogs(company_profile: str, blogs: list[dict]) -> list[BlogRecommendation]:
        blogs_formatted = "\n".join(
            f"- Title: {b.get('Blog Title', '')} | Category: {b.get('Blog Category', '')} "
            f"| Application: {b.get('Application', '')} | Asset Class: {b.get('Asset Class', '')} "
            f"| URL: {b.get('Link to Blog', '')}"
            for b in blogs
        )
        prompt = BLOG_SCORING_USER.format(
            company_profile=company_profile,
            blogs_formatted=blogs_formatted,
        )
        raw = client.call([{"role": "user", "content": prompt}], system_prompt=BLOG_SCORING_SYSTEM)
        data = json.loads(_extract_json(raw))
        return [BlogRecommendation(**item) for item in data[:3]]
    return score_blogs


def make_product_scorer(client: AnthropicClient):
    def score_products(company_profile: str, products: list[dict]) -> list[ProductRecommendation]:
        products_formatted = "\n".join(
            f"- Name: {p.get('name', '')} | Description: {p.get('description', '')} "
            f"| Use Cases: {', '.join(p.get('use_cases', []))} "
            f"| Target Segments: {', '.join(p.get('target_segments', []))}"
            for p in products
        )
        prompt = PRODUCT_SCORING_USER.format(
            company_profile=company_profile,
            products_formatted=products_formatted,
        )
        raw = client.call([{"role": "user", "content": prompt}], system_prompt=PRODUCT_SCORING_SYSTEM)
        data = json.loads(_extract_json(raw))
        return [ProductRecommendation(**item) for item in data[:3]]
    return score_products


def _summarize_crm(crm_data: CRMAccount | None) -> str:
    if not crm_data:
        return "No CRM data available (new prospect)."
    lines = []
    if crm_data.industry:
        lines.append(f"Industry: {crm_data.industry.value}")
    if crm_data.company_size:
        lines.append(f"Size: {crm_data.company_size.value}")
    if crm_data.products_discussed:
        lines.append("Products Discussed:")
        for p in crm_data.products_discussed:
            lines.append(f"  - {p.value}")
    if crm_data.open_questions:
        lines.append("Open Client Questions:")
        for q in crm_data.open_questions:
            lines.append(f"  - {q.value}")
    if crm_data.open_followups:
        lines.append("Open Follow-Ups:")
        for f in crm_data.open_followups:
            lines.append(f"  - {f.value}")
    if crm_data.past_conversations:
        lines.append("Conversation History:")
        for c in crm_data.past_conversations:
            lines.append(f"  - {c.value}")
    return "\n".join(lines) if lines else "No CRM details."


def _summarize_web(web: WebResearchResult) -> str:
    lines = []
    if web.company_description:
        lines.append(f"Description: {web.company_description.value}")
    if web.recent_news:
        lines.append("Recent News:")
        for n in web.recent_news:
            lines.append(f"  - {n.value}")
    if web.technology_signals:
        lines.append("Technology Signals:")
        for s in web.technology_signals:
            lines.append(f"  - {s.value}")
    return "\n".join(lines) if lines else "No public web research available."


def _summarize_products(products: list[ProductRecommendation]) -> str:
    if not products:
        return "No product recommendations."
    return "\n".join(
        f"- {p.product_name}: {p.use_case} — {p.reason}" for p in products
    )


def _summarize_blogs(blogs: list[BlogRecommendation]) -> str:
    if not blogs:
        return "No blog recommendations."
    return "\n".join(f"- {b.title}: {b.reason}" for b in blogs)


_FETCH_HEADERS = {"User-Agent": "ClientIntelligenceStudio/1.0 (internal research tool)"}


def _fetch_blog_content(blogs: list[BlogRecommendation]) -> dict[str, str]:
    """Fetch and extract text from each blog URL.

    Returns url -> text (up to 1500 chars). Failures are silently skipped —
    blog content enriches emails but is not required.
    """
    import re

    import httpx

    content: dict[str, str] = {}
    for blog in blogs:
        if not blog.url:
            continue
        try:
            resp = httpx.get(blog.url, headers=_FETCH_HEADERS, timeout=8, follow_redirects=True)
            resp.raise_for_status()
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text).strip()
            content[blog.url] = text[:1500]
        except Exception:
            pass
    return content


def _summarize_blogs_with_content(
    blogs: list[BlogRecommendation],
    content: dict[str, str],
) -> str:
    if not blogs:
        return "No blog recommendations."
    parts = []
    for b in blogs:
        snippet = content.get(b.url, "")
        entry = f"Title: {b.title}\nURL: {b.url}\nWhy relevant: {b.reason}"
        if snippet:
            entry += f"\nContent excerpt: {snippet[:600]}"
        parts.append(entry)
    return "\n\n".join(parts)


def make_ai_generator(client: AnthropicClient):
    def generate(
        crm_data: CRMAccount | None,
        web_research: WebResearchResult,
        product_recommendations: list[ProductRecommendation],
        blog_recommendations: list[BlogRecommendation],
    ) -> tuple[InternalBrief, ClientFacingOutputs]:
        from src.models import OutreachEmail

        company = web_research.company_name
        crm_summary = _summarize_crm(crm_data)
        web_summary = _summarize_web(web_research)
        products_summary = _summarize_products(product_recommendations)
        blogs_summary = _summarize_blogs(blog_recommendations)

        # Fetch blog article content to enrich email generation
        blog_content = _fetch_blog_content(blog_recommendations)
        blogs_with_content = _summarize_blogs_with_content(blog_recommendations, blog_content)

        # Internal brief
        internal_md = client.call(
            [{"role": "user", "content": INTERNAL_BRIEF_USER.format(
                company_name=company,
                crm_summary=crm_summary,
                web_summary=web_summary,
                products_summary=products_summary,
            )}],
            system_prompt=INTERNAL_BRIEF_SYSTEM,
        )

        # Multi-audience outreach emails — one Claude call returns 3 variants as JSON
        raw_emails = client.call(
            [{"role": "user", "content": MULTI_EMAIL_USER.format(
                company_name=company,
                web_summary=web_summary,
                products_summary=products_summary,
                blogs_with_content=blogs_with_content,
            )}],
            system_prompt=MULTI_EMAIL_SYSTEM,
        )

        outreach_emails: list[OutreachEmail] = []
        try:
            email_data = json.loads(_extract_json(raw_emails))
            outreach_emails = [OutreachEmail(**e) for e in email_data if isinstance(e, dict)]
        except Exception:
            pass  # fall back to single-email below

        # Backward-compat single email: derived from first variant or re-generated on parse failure
        if outreach_emails:
            email_md = f"**Subject:** {outreach_emails[0].subject}\n\n{outreach_emails[0].body}"
        else:
            email_md = client.call(
                [{"role": "user", "content": OUTREACH_EMAIL_USER.format(
                    company_name=company,
                    web_summary=web_summary,
                    products_summary=products_summary,
                    blogs_summary=blogs_summary,
                )}],
                system_prompt=OUTREACH_EMAIL_SYSTEM,
            )

        # Meeting prep brief (no CRM data passed)
        meeting_md = client.call(
            [{"role": "user", "content": MEETING_PREP_USER.format(
                company_name=company,
                web_summary=web_summary,
                products_summary=products_summary,
                blogs_summary=blogs_summary,
            )}],
            system_prompt=MEETING_PREP_SYSTEM,
        )

        crm_highlights = []
        if crm_data:
            if crm_data.industry:
                crm_highlights.append(crm_data.industry)
            crm_highlights.extend(crm_data.products_discussed)
            crm_highlights.extend(crm_data.open_followups)

        brief = InternalBrief(
            account_summary=internal_md,
            crm_highlights=crm_highlights,
            key_opportunities=[
                TaggedFact(
                    value=f"Product opportunity: {p.product_name} — {p.use_case}",
                    source="AI_INFERENCE",
                    evidence=p.reason,
                )
                for p in product_recommendations
            ],
            risks_and_gaps=[],
        )

        client_out = ClientFacingOutputs(
            outreach_email=email_md,
            meeting_prep_brief=meeting_md,
            blog_recommendations=blog_recommendations[:3],
            outreach_emails=outreach_emails,
        )

        return brief, client_out

    return generate
