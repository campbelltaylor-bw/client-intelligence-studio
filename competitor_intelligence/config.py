import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).parent
_PROJECT_ROOT = _HERE.parent

_COMPANY_CONFIGS = {
    "ca": {
        "our_company_name": "Context Analytics",
        "our_company_short": "CA",
        "products_yaml_path": _PROJECT_ROOT / "data" / "context_analytics_products.yaml",
        "our_profile_dir": _HERE / "our_profile",
        "outputs_dir": _HERE / "outputs" / "ca",
        "logo_path": _PROJECT_ROOT / "assets" / "context_analytics_logo.png",
        "watchlist_path": _HERE / "competitors_to_watch.yaml",
    },
    "bridgewise": {
        "our_company_name": "Bridgewise",
        "our_company_short": "Bridgewise",
        "products_yaml_path": _PROJECT_ROOT / "data" / "bridgewise_products.yaml",
        "our_profile_dir": _HERE / "bridgewise_profile",
        "outputs_dir": _HERE / "outputs" / "bridgewise",
        "logo_path": _HERE / "bridgewise_profile" / "Bridgewise-Logo_new.webp",
        "watchlist_path": _HERE / "bridgewise_competitors_to_watch.yaml",
    },
}


@dataclass
class AppConfig:
    anthropic_api_key: str
    company_mode: str = "ca"
    our_company_name: str = "Context Analytics"
    our_company_short: str = "CA"
    model: str = "claude-sonnet-4-6"
    research_model: str = "claude-haiku-4-5-20251001"
    products_yaml_path: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "data" / "context_analytics_products.yaml"
    )
    our_profile_dir: Path = field(
        default_factory=lambda: _HERE / "our_profile"
    )
    outputs_dir: Path = field(
        default_factory=lambda: _HERE / "outputs" / "ca"
    )
    logo_path: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "assets" / "context_analytics_logo.png"
    )
    watchlist_path: Path = field(
        default_factory=lambda: _HERE / "competitors_to_watch.yaml"
    )
    max_research_iterations: int = 10
    max_tokens_research: int = 8192
    max_tokens_analysis: int = 8192


def load_config(company_mode: str = "ca") -> AppConfig:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add it to the .env file in the project root."
        )
    mode = company_mode if company_mode in _COMPANY_CONFIGS else "ca"
    cfg_overrides = _COMPANY_CONFIGS[mode]
    config = AppConfig(
        anthropic_api_key=api_key,
        company_mode=mode,
        our_company_name=cfg_overrides["our_company_name"],
        our_company_short=cfg_overrides["our_company_short"],
        products_yaml_path=cfg_overrides["products_yaml_path"],
        our_profile_dir=cfg_overrides["our_profile_dir"],
        outputs_dir=cfg_overrides["outputs_dir"],
        logo_path=cfg_overrides["logo_path"],
        watchlist_path=cfg_overrides["watchlist_path"],
    )
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    config.our_profile_dir.mkdir(parents=True, exist_ok=True)
    return config
