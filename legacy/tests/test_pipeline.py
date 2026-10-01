import pytest

from src.models import PipelineInput, PipelineOutput
from src.pipeline.runner import run_pipeline


@pytest.fixture
def existing_account_input():
    return PipelineInput(
        company_name="Meridian Capital Partners",
        is_new_prospect=False,
        monday_item_id="mock-001",
    )


@pytest.fixture
def new_prospect_input():
    return PipelineInput(
        company_name="Acme Hedge Fund",
        is_new_prospect=True,
        website_url="https://acmehedge.com",
    )


def test_pipeline_existing_account_runs(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert isinstance(output, PipelineOutput)


def test_pipeline_new_prospect_runs(new_prospect_input):
    output = run_pipeline(new_prospect_input)
    assert isinstance(output, PipelineOutput)


def test_pipeline_existing_account_has_crm_data(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert output.crm_data is not None
    assert output.crm_data.company_name == "Meridian Capital Partners"


def test_pipeline_new_prospect_no_crm_data(new_prospect_input):
    output = run_pipeline(new_prospect_input)
    assert output.crm_data is None


def test_pipeline_has_web_research(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert output.web_research is not None
    assert output.web_research.company_name == "Meridian Capital Partners"


def test_pipeline_has_product_recommendations(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert len(output.product_recommendations) > 0
    for rec in output.product_recommendations:
        assert rec.reason != "", "Every product recommendation must have a reason"
        assert rec.product_name != ""


def test_pipeline_has_blog_recommendations(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert len(output.client_facing.blog_recommendations) > 0
    for blog in output.client_facing.blog_recommendations:
        assert blog.reason != "", "Every blog recommendation must have a reason"
        assert blog.title != ""


def test_pipeline_has_internal_brief(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert output.internal.account_summary != ""


def test_pipeline_has_client_facing_outputs(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert output.client_facing.outreach_email != ""
    assert output.client_facing.meeting_prep_brief != ""


def test_pipeline_three_blog_recommendations_max(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert len(output.client_facing.blog_recommendations) <= 3


def test_pipeline_model_used_recorded(existing_account_input):
    output = run_pipeline(existing_account_input)
    assert output.model_used != ""
