"""
Verifies that CRM facts do not appear in client-facing output.

The check looks for known CRM-only strings (conversation notes, internal follow-ups)
that should never be visible to external clients. This is a safety test — if it fails,
the prompt templates or assembly stage need to be reviewed.
"""

import pytest

from src.models import PipelineInput
from src.pipeline.runner import run_pipeline

# Strings from mock CRM data that are internal-only and must not appear in client-facing text.
INTERNAL_ONLY_STRINGS = [
    "open follow-ups",
    "monday crm",
    "conversation notes",
    "schedule technical deep-dive call with their quant team",
    "send case study on sentiment-driven alpha",
    "cto joined",
    "flagged concern about data licensing costs",
]


@pytest.fixture
def existing_account_output():
    inp = PipelineInput(
        company_name="Meridian Capital Partners",
        is_new_prospect=False,
        monday_item_id="mock-001",
    )
    return run_pipeline(inp)


def test_outreach_email_no_crm_internal_strings(existing_account_output):
    email_lower = existing_account_output.client_facing.outreach_email.lower()
    for s in INTERNAL_ONLY_STRINGS:
        assert s.lower() not in email_lower, (
            f"Internal CRM string found in outreach email: '{s}'"
        )


def test_meeting_brief_no_crm_internal_strings(existing_account_output):
    brief_lower = existing_account_output.client_facing.meeting_prep_brief.lower()
    for s in INTERNAL_ONLY_STRINGS:
        assert s.lower() not in brief_lower, (
            f"Internal CRM string found in meeting brief: '{s}'"
        )


def test_blog_recommendations_no_crm_internal_strings(existing_account_output):
    for blog in existing_account_output.client_facing.blog_recommendations:
        reason_lower = blog.reason.lower()
        for s in INTERNAL_ONLY_STRINGS:
            assert s.lower() not in reason_lower, (
                f"Internal CRM string found in blog reason: '{s}'"
            )


def test_all_facts_have_valid_source_tags(existing_account_output):
    valid_sources = {"CRM_FACT", "PUBLIC_FACT", "AI_INFERENCE"}
    output = existing_account_output

    facts_to_check = []
    if output.crm_data:
        if output.crm_data.industry:
            facts_to_check.append(output.crm_data.industry)
        facts_to_check.extend(output.crm_data.products_discussed)
        facts_to_check.extend(output.crm_data.open_questions)
    if output.web_research.company_description:
        facts_to_check.append(output.web_research.company_description)
    facts_to_check.extend(output.web_research.recent_news)
    facts_to_check.extend(output.internal.crm_highlights)
    facts_to_check.extend(output.internal.key_opportunities)

    for fact in facts_to_check:
        assert fact.source in valid_sources, f"Invalid source tag: {fact.source}"


def test_crm_facts_only_in_internal_not_client_facing(existing_account_output):
    output = existing_account_output
    # Internal brief is allowed to have CRM_FACT — verify it does for an existing account
    crm_sources = {f.source for f in output.internal.crm_highlights}
    assert "CRM_FACT" in crm_sources, "Internal brief should contain CRM_FACT highlights"

    # Client-facing outputs should not have crm_data or crm_highlights fields at all
    assert not hasattr(output.client_facing, "crm_data")
    assert not hasattr(output.client_facing, "crm_highlights")
