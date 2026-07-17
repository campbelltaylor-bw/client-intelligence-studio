import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# On Streamlit Community Cloud, secrets are in st.secrets, not os.environ.
# Inject them so the rest of the config can use os.getenv() uniformly.
try:
    import streamlit as st
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass


class AppConfig(BaseModel):
    anthropic_api_key: str
    use_mock_data: bool = True
    # CRM_REPOSITORY overrides use_mock_data for the CRM provider only.
    # Values: "mock" | "monday"
    crm_repository: str = "mock"

    # Monday.com credentials — prefer MONDAY_API_TOKEN, fall back to MONDAY_API_KEY
    monday_api_token: str = ""
    monday_api_key: str = ""       # kept for backward compat
    monday_board_id: str = ""
    monday_api_version: str = "2026-01"

    # Configurable column IDs (stable Monday column IDs, not titles).
    # Override with MONDAY_COL_* env vars when your board uses different IDs.
    monday_col_industry: str = "industry"
    monday_col_company_size: str = "company_size"
    monday_col_products_discussed: str = "products_discussed"
    monday_col_open_questions: str = "open_questions"
    monday_col_open_followups: str = "open_followups"

    # Web research provider config.
    # Values: "mock" | "httpx" | "claude"
    # WEB_RESEARCH_PROVIDER env var takes precedence; otherwise derives from use_mock_data.
    web_research_provider: str = "mock"

    # Blog repository config.
    # Values: "mock" | "csv" | "google_sheets"
    # BLOG_REPOSITORY env var takes precedence; otherwise derives from use_mock_data.
    blog_repository: str = "mock"
    google_sheet_id: str = ""
    google_sheet_range: str = "'Blog Categories'!A:G"
    google_credentials_path: str = ""
    google_cache_ttl_seconds: int = 300

    model: str = "claude-sonnet-4-6"
    max_web_pages: int = 3
    blog_catalog_path: str = "data/blog_catalog.csv"
    product_catalog_path: str = "data/context_analytics_products.yaml"
    mock_monday_path: str = "data/mock_monday_accounts.json"
    mock_web_research_path: str = "data/mock_web_research.json"
    outputs_dir: str = "outputs"

    @property
    def effective_monday_token(self) -> str:
        """Return the best available Monday API token."""
        return self.monday_api_token or self.monday_api_key


def get_config() -> AppConfig:
    config_path = Path("config/config.yaml")
    yaml_settings: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            yaml_settings = yaml.safe_load(f) or {}

    missing: list[str] = []
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    use_mock_data = yaml_settings.get("use_mock_data", True)

    # Determine CRM repository.  CRM_REPOSITORY env var takes precedence;
    # otherwise derive from use_mock_data for backward compat.
    crm_repository_env = os.getenv("CRM_REPOSITORY", "").lower()
    if crm_repository_env in ("mock", "monday"):
        crm_repository = crm_repository_env
    else:
        crm_repository = "mock" if use_mock_data else "monday"

    # Determine web research provider.
    # Priority: WEB_RESEARCH_PROVIDER env var > config.yaml > use_mock_data fallback
    _valid_web = ("mock", "httpx", "claude")
    web_provider_env = os.getenv("WEB_RESEARCH_PROVIDER", "").lower()
    if web_provider_env in _valid_web:
        web_research_provider = web_provider_env
    elif yaml_settings.get("web_research_provider", "").lower() in _valid_web:
        web_research_provider = yaml_settings["web_research_provider"].lower()
    else:
        web_research_provider = "mock" if use_mock_data else "claude"

    # Determine blog repository.  BLOG_REPOSITORY env var takes precedence;
    # otherwise derive from use_mock_data for backward compat.
    blog_repository_env = os.getenv("BLOG_REPOSITORY", "").lower()
    if blog_repository_env in ("mock", "csv", "google_sheets"):
        blog_repository = blog_repository_env
    else:
        blog_repository = "mock" if use_mock_data else "csv"

    # Prefer MONDAY_API_TOKEN; fall back to MONDAY_API_KEY
    monday_api_token = os.getenv("MONDAY_API_TOKEN", "") or os.getenv("MONDAY_API_KEY", "")
    monday_board_id = os.getenv("MONDAY_BOARD_ID", "")

    if not anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY")

    if crm_repository == "monday":
        if not monday_api_token:
            missing.append("MONDAY_API_TOKEN")
        if not monday_board_id:
            missing.append("MONDAY_BOARD_ID")

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return AppConfig(
        anthropic_api_key=anthropic_api_key,
        use_mock_data=use_mock_data,
        crm_repository=crm_repository,
        web_research_provider=web_research_provider,
        blog_repository=blog_repository,
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        google_sheet_range=os.getenv("GOOGLE_SHEET_RANGE", "'Blog Categories'!A:G"),
        google_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
        google_cache_ttl_seconds=int(os.getenv("GOOGLE_CACHE_TTL_SECONDS", "300")),
        monday_api_token=monday_api_token,
        monday_api_key=os.getenv("MONDAY_API_KEY", ""),
        monday_board_id=monday_board_id,
        monday_api_version=os.getenv("MONDAY_API_VERSION", "2026-01"),
        monday_col_industry=os.getenv("MONDAY_COL_INDUSTRY", "industry"),
        monday_col_company_size=os.getenv("MONDAY_COL_COMPANY_SIZE", "company_size"),
        monday_col_products_discussed=os.getenv("MONDAY_COL_PRODUCTS", "products_discussed"),
        monday_col_open_questions=os.getenv("MONDAY_COL_QUESTIONS", "open_questions"),
        monday_col_open_followups=os.getenv("MONDAY_COL_FOLLOWUPS", "open_followups"),
        model=yaml_settings.get("model", "claude-sonnet-4-6"),
        max_web_pages=yaml_settings.get("max_web_pages", 3),
        blog_catalog_path=yaml_settings.get("blog_catalog_path", "data/blog_catalog.csv"),
        product_catalog_path=yaml_settings.get("product_catalog_path", "data/context_analytics_products.yaml"),
        mock_monday_path=yaml_settings.get("mock_monday_path", "data/mock_monday_accounts.json"),
        mock_web_research_path=yaml_settings.get("mock_web_research_path", "data/mock_web_research.json"),
        outputs_dir=yaml_settings.get("outputs_dir", "outputs"),
    )
