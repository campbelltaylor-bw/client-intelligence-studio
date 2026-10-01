from src.models import CRMAccount, PipelineInput
from src.providers.base import CRMProvider


def run_crm_stage(pipeline_input: PipelineInput, crm_provider: CRMProvider) -> CRMAccount | None:
    if pipeline_input.is_new_prospect or not pipeline_input.monday_item_id:
        return None
    return crm_provider.get_account(pipeline_input.monday_item_id)
