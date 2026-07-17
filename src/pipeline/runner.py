import json
from datetime import datetime
from pathlib import Path

from src.config import AppConfig
from src.models import PipelineInput, PipelineOutput
from src.pipeline.ai_generation_stage import run_ai_generation_stage, stub_ai_generator
from src.pipeline.assembly_stage import run_assembly_stage
from src.pipeline.blog_match_stage import run_blog_match_stage
from src.pipeline.crm_stage import run_crm_stage
from src.pipeline.product_match_stage import run_product_match_stage
from src.pipeline.research_stage import run_research_stage
from src.providers.mock_blog_catalog import MockBlogCatalogProvider
from src.providers.mock_monday import MockMondayProvider
from src.providers.mock_web_research import MockWebResearchProvider


def _stub_blog_scorer(company_profile: str, blogs: list[dict]):
    from src.models import BlogRecommendation
    results = []
    for blog in blogs[:3]:
        results.append(
            BlogRecommendation(
                title=blog.get("Blog Title", "Unknown"),
                url=blog.get("Link to Blog", ""),
                reason=f"[STUB] Matched based on relevance to {company_profile[:40]}...",
                relevance_score=0.75,
            )
        )
    return results


def _stub_product_scorer(company_profile: str, products: list[dict]):
    from src.models import ProductRecommendation
    results = []
    for product in products[:3]:
        results.append(
            ProductRecommendation(
                product_name=product.get("name", "Unknown"),
                use_case=product.get("use_cases", ["General use"])[0] if product.get("use_cases") else "General use",
                reason=f"[STUB] Product matches profile based on {company_profile[:40]}...",
                relevance_score=0.70,
            )
        )
    return results


def _save_output(output: PipelineOutput, outputs_dir: str) -> None:
    Path(outputs_dir).mkdir(parents=True, exist_ok=True)
    safe_name = output.input.company_name.replace(" ", "_").replace("/", "-")[:40]
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = Path(outputs_dir) / f"{safe_name}_{timestamp}.json"
    with open(path, "w") as f:
        f.write(output.model_dump_json(indent=2))


def _build_web_provider(config: AppConfig, ai_client=None):
    """Select and instantiate the web research provider based on web_research_provider config."""
    if config.web_research_provider == "claude" and ai_client:
        from src.providers.claude_web_research import ClaudeWebResearchProvider
        return ClaudeWebResearchProvider(ai_client)
    if config.web_research_provider == "httpx":
        from src.providers.httpx_web_research import HttpxWebResearchProvider
        return HttpxWebResearchProvider(max_pages=config.max_web_pages)
    return MockWebResearchProvider(config.mock_web_research_path)


def _build_blog_provider(config: AppConfig):
    """Select and instantiate the blog provider based on blog_repository config."""
    if config.blog_repository == "google_sheets":
        try:
            from src.providers.google_sheets_blog_catalog import (
                GoogleSheetsBlogRepository,
                GoogleSheetsError,
            )
            return GoogleSheetsBlogRepository(
                spreadsheet_id=config.google_sheet_id,
                sheet_range=config.google_sheet_range,
                credentials_path=config.google_credentials_path or None,
                cache_ttl_seconds=config.google_cache_ttl_seconds,
            )
        except GoogleSheetsError:
            # Fall back to CSV when Google Sheets is misconfigured at init time.
            from src.providers.csv_blog_catalog import CSVBlogCatalogProvider
            return CSVBlogCatalogProvider(config.blog_catalog_path)
    if config.blog_repository == "csv":
        from src.providers.csv_blog_catalog import CSVBlogCatalogProvider
        return CSVBlogCatalogProvider(config.blog_catalog_path)
    return MockBlogCatalogProvider(config.blog_catalog_path)


def _build_crm_provider(config: AppConfig):
    """Select and instantiate the CRM provider based on crm_repository."""
    if config.crm_repository == "monday":
        from src.providers.real_monday import MondayCRMProvider
        return MondayCRMProvider(
            token=config.effective_monday_token,
            board_id=config.monday_board_id,
            api_version=config.monday_api_version,
            col_map={
                "industry": config.monday_col_industry,
                "company_size": config.monday_col_company_size,
                "products_discussed": config.monday_col_products_discussed,
                "open_questions": config.monday_col_open_questions,
                "open_followups": config.monday_col_open_followups,
            },
        )
    return MockMondayProvider(config.mock_monday_path)


def run_pipeline(pipeline_input: PipelineInput, config: AppConfig | None = None) -> PipelineOutput:
    if config is None:
        config = AppConfig(anthropic_api_key="stub", use_mock_data=True)

    crm_provider = _build_crm_provider(config)
    blog_provider = _build_blog_provider(config)

    use_claude = bool(config.anthropic_api_key and config.anthropic_api_key != "stub")

    if use_claude:
        from src.ai_client import AnthropicClient
        from src.pipeline.claude_scorers import make_ai_generator, make_blog_scorer, make_product_scorer
        ai_client = AnthropicClient(api_key=config.anthropic_api_key, model=config.model)
        blog_scorer = make_blog_scorer(ai_client)
        product_scorer = make_product_scorer(ai_client)
        ai_generator = make_ai_generator(ai_client)
    else:
        ai_client = None
        blog_scorer = _stub_blog_scorer
        product_scorer = _stub_product_scorer
        ai_generator = stub_ai_generator

    web_provider = _build_web_provider(config, ai_client)

    # Stage 1: CRM
    crm_data = run_crm_stage(pipeline_input, crm_provider)

    # Stage 2: Web research
    web_research = run_research_stage(pipeline_input, web_provider)

    # Stage 3: Blog matching — fall back to CSV if Google Sheets fails at load time
    try:
        blog_recommendations = run_blog_match_stage(crm_data, web_research, blog_provider, blog_scorer)
    except Exception as blog_exc:
        from src.providers.google_sheets_blog_catalog import GoogleSheetsError
        if isinstance(blog_exc, GoogleSheetsError) and config.blog_repository == "google_sheets":
            from src.providers.csv_blog_catalog import CSVBlogCatalogProvider
            fallback = CSVBlogCatalogProvider(config.blog_catalog_path)
            blog_recommendations = run_blog_match_stage(crm_data, web_research, fallback, blog_scorer)
        else:
            raise

    # Stage 4: Product matching
    product_recommendations = run_product_match_stage(
        crm_data, web_research, config.product_catalog_path, product_scorer
    )

    # Stage 5: AI generation
    internal_brief, client_facing = run_ai_generation_stage(
        crm_data, web_research, product_recommendations, blog_recommendations, ai_generator
    )

    # Stage 6: Assembly
    output = run_assembly_stage(
        pipeline_input=pipeline_input,
        crm_data=crm_data,
        web_research=web_research,
        product_recommendations=product_recommendations,
        internal_brief=internal_brief,
        client_facing=client_facing,
        model_used=config.model,
    )

    _save_output(output, config.outputs_dir)
    return output


def list_crm_accounts(config: AppConfig | None = None) -> list[dict]:
    if config is None:
        config = AppConfig(anthropic_api_key="stub", use_mock_data=True)
    provider = _build_crm_provider(config)
    return provider.list_accounts()
