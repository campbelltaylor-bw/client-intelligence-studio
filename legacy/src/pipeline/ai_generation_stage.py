from src.models import (
    BlogRecommendation,
    ClientFacingOutputs,
    CRMAccount,
    InternalBrief,
    OutreachEmail,
    ProductRecommendation,
    TaggedFact,
    WebResearchResult,
)


def run_ai_generation_stage(
    crm_data: CRMAccount | None,
    web_research: WebResearchResult,
    product_recommendations: list[ProductRecommendation],
    blog_recommendations: list[BlogRecommendation],
    ai_generator,  # callable: (crm, web, products, blogs) -> (InternalBrief, ClientFacingOutputs)
) -> tuple[InternalBrief, ClientFacingOutputs]:
    return ai_generator(crm_data, web_research, product_recommendations, blog_recommendations)


def stub_ai_generator(
    crm_data: CRMAccount | None,
    web_research: WebResearchResult,
    product_recommendations: list[ProductRecommendation],
    blog_recommendations: list[BlogRecommendation],
) -> tuple[InternalBrief, ClientFacingOutputs]:
    """Hardcoded stub used in M2 tests — replaced by real Claude calls in M3."""
    company = web_research.company_name

    crm_highlights = []
    if crm_data:
        if crm_data.industry:
            crm_highlights.append(crm_data.industry)
        crm_highlights.extend(crm_data.products_discussed[:2])

    key_opportunities = [
        TaggedFact(
            value=f"Potential fit for {product_recommendations[0].product_name}" if product_recommendations else "No products matched",
            source="AI_INFERENCE",
        )
    ]

    brief = InternalBrief(
        account_summary=f"[STUB] {company} is a target account with interest in alternative data.",
        crm_highlights=crm_highlights,
        key_opportunities=key_opportunities,
        risks_and_gaps=["[STUB] Budget sensitivity unknown", "[STUB] Decision timeline not confirmed"],
    )

    stub_emails = [
        OutreachEmail(
            audience="Portfolio Manager",
            subject=f"[STUB] How Context Analytics supports {company}",
            body=f"[STUB] Hi,\n\nI wanted to reach out regarding how Context Analytics could support {company} with alternative data and sentiment signals.\n\nBest,\nYour Name",
        ),
        OutreachEmail(
            audience="Quantitative Analyst",
            subject=f"[STUB] Data infrastructure for {company}",
            body=f"[STUB] Hi,\n\nI wanted to connect about the quantitative data capabilities Context Analytics offers that could complement your models at {company}.\n\nBest,\nYour Name",
        ),
        OutreachEmail(
            audience="Risk Officer",
            subject=f"[STUB] Risk signal coverage for {company}",
            body=f"[STUB] Hi,\n\nI wanted to discuss how Context Analytics risk and sentiment signals could support {company}'s monitoring workflows.\n\nBest,\nYour Name",
        ),
    ]

    client_out = ClientFacingOutputs(
        outreach_email=f"[STUB] Hi,\n\nI wanted to reach out regarding how Context Analytics could support {company}...\n\nBest,\nYour Name",
        meeting_prep_brief=f"## [STUB] Meeting Prep: {company}\n\n**Key topics:** Alternative data adoption, sentiment signals.\n",
        blog_recommendations=blog_recommendations[:3],
        outreach_emails=stub_emails,
    )

    return brief, client_out
