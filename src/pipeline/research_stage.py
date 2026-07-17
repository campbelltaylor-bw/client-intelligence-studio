from src.models import PipelineInput, WebResearchResult
from src.providers.base import WebResearchProvider


def run_research_stage(pipeline_input: PipelineInput, web_provider: WebResearchProvider) -> WebResearchResult:
    return web_provider.research(pipeline_input.company_name, pipeline_input.website_url)
