import pytest
from pydantic import ValidationError

from src.models import (
    BlogRecommendation,
    ClientFacingOutputs,
    CRMAccount,
    InternalBrief,
    PipelineInput,
    PipelineOutput,
    ProductRecommendation,
    TaggedFact,
    WebResearchResult,
)


def test_tagged_fact_crm():
    fact = TaggedFact(value="Hedge Fund", source="CRM_FACT", evidence="Monday CRM field")
    assert fact.source == "CRM_FACT"
    assert fact.evidence == "Monday CRM field"


def test_tagged_fact_public():
    fact = TaggedFact(value="Founded 2011", source="PUBLIC_FACT")
    assert fact.evidence is None


def test_tagged_fact_invalid_source():
    with pytest.raises(ValidationError):
        TaggedFact(value="x", source="MADE_UP")


def test_crm_account_minimal():
    account = CRMAccount(company_name="Acme Fund")
    assert account.company_name == "Acme Fund"
    assert account.products_discussed == []
    assert account.open_followups == []


def test_crm_account_full():
    account = CRMAccount(
        company_name="Meridian Capital",
        industry=TaggedFact(value="Hedge Fund", source="CRM_FACT"),
        products_discussed=[TaggedFact(value="News Sentiment", source="CRM_FACT")],
        open_followups=[TaggedFact(value="Send case study", source="CRM_FACT")],
        monday_item_id="mock-001",
    )
    assert len(account.products_discussed) == 1
    assert account.monday_item_id == "mock-001"


def test_web_research_result():
    result = WebResearchResult(
        company_name="Acme Fund",
        company_description=TaggedFact(value="A quant hedge fund", source="PUBLIC_FACT"),
        recent_news=[TaggedFact(value="Raised $500M", source="PUBLIC_FACT", evidence="Reuters")],
    )
    assert result.company_name == "Acme Fund"
    assert len(result.recent_news) == 1


def test_blog_recommendation_requires_reason():
    blog = BlogRecommendation(
        title="Sentiment Alpha",
        url="https://example.com/blog",
        reason="Matches client's long/short equity focus and interest in sentiment signals",
        relevance_score=0.9,
    )
    assert blog.reason != ""


def test_blog_recommendation_score_bounds():
    with pytest.raises(ValidationError):
        BlogRecommendation(title="x", url="https://x.com", reason="y", relevance_score=1.5)


def test_product_recommendation_requires_reason():
    rec = ProductRecommendation(
        product_name="News Sentiment Scores",
        use_case="Alpha signal for long/short book",
        reason="Client is a quant long/short fund actively evaluating alternative data (CRM_FACT)",
        relevance_score=0.85,
    )
    assert rec.reason != ""


def test_internal_brief():
    brief = InternalBrief(
        account_summary="Strong prospect with active quant team",
        crm_highlights=[TaggedFact(value="Demo completed Nov 2024", source="CRM_FACT")],
        key_opportunities=[TaggedFact(value="API integration", source="AI_INFERENCE")],
        risks_and_gaps=["Budget sensitivity flagged in CRM notes"],
    )
    assert len(brief.crm_highlights) == 1


def test_client_facing_outputs_no_crm_fields():
    outputs = ClientFacingOutputs(
        outreach_email="Hi, I wanted to reach out...",
        meeting_prep_brief="## Meeting Prep\n\nKey topics...",
        blog_recommendations=[
            BlogRecommendation(
                title="Sentiment Blog",
                url="https://x.com/blog",
                reason="Relevant to their equity strategy",
                relevance_score=0.8,
            )
        ],
    )
    # ClientFacingOutputs has no crm_data or crm_highlights field — structural guarantee
    assert not hasattr(outputs, "crm_data")
    assert not hasattr(outputs, "crm_highlights")


def test_pipeline_input_new_prospect():
    inp = PipelineInput(
        company_name="New Prospect LLC",
        is_new_prospect=True,
        website_url="https://newprospect.com",
    )
    assert inp.monday_item_id is None


def test_pipeline_input_existing_account():
    inp = PipelineInput(
        company_name="Meridian Capital",
        is_new_prospect=False,
        monday_item_id="mock-001",
    )
    assert inp.website_url is None
    assert inp.monday_item_id == "mock-001"


def test_pipeline_output_structure():
    from datetime import datetime

    inp = PipelineInput(company_name="Acme", is_new_prospect=True)
    web = WebResearchResult(company_name="Acme")
    brief = InternalBrief(account_summary="Strong prospect")
    client_out = ClientFacingOutputs(
        outreach_email="Hello...",
        meeting_prep_brief="## Meeting Prep",
    )
    output = PipelineOutput(
        input=inp,
        web_research=web,
        internal=brief,
        client_facing=client_out,
    )
    assert output.model_used == "claude-sonnet-4-6"
    assert isinstance(output.generated_at, datetime)
    assert output.crm_data is None
