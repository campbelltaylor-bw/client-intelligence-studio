from datetime import datetime

from src.models import (
    BlogRecommendation,
    ClientFacingOutputs,
    CRMAccount,
    InternalBrief,
    PipelineInput,
    PipelineOutput,
    ProductRecommendation,
    WebResearchResult,
)


def run_assembly_stage(
    pipeline_input: PipelineInput,
    crm_data: CRMAccount | None,
    web_research: WebResearchResult,
    product_recommendations: list[ProductRecommendation],
    internal_brief: InternalBrief,
    client_facing: ClientFacingOutputs,
    model_used: str,
) -> PipelineOutput:
    _validate_no_crm_leak(client_facing, crm_data)

    return PipelineOutput(
        input=pipeline_input,
        crm_data=crm_data,
        web_research=web_research,
        product_recommendations=product_recommendations,
        internal=internal_brief,
        client_facing=client_facing,
        generated_at=datetime.utcnow(),
        model_used=model_used,
    )


def _validate_no_crm_leak(client_facing: ClientFacingOutputs, crm_data: CRMAccount | None) -> None:
    """Raise if any known CRM fact value appears verbatim in client-facing text."""
    if not crm_data:
        return

    crm_values = set()
    for field in [crm_data.open_followups, crm_data.past_conversations]:
        for fact in field:
            # Only flag longer strings (>40 chars) to avoid false positives on short words
            if len(fact.value) > 40:
                crm_values.add(fact.value.lower())

    client_text = (client_facing.outreach_email + client_facing.meeting_prep_brief).lower()
    for val in crm_values:
        if val in client_text:
            raise ValueError(
                f"CRM_FACT leaked into client-facing output: '{val[:60]}...'\n"
                "Review the prompt templates in src/prompts/prompts.py."
            )
