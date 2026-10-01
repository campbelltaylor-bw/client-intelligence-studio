import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from app.components.output_renderer import (
    render_blog_recommendations,
    render_internal_brief,
    render_outreach_emails,
    render_product_recommendations,
    render_web_research,
)
from app.components.ui import render_app_header, render_metric_row, section_header, status_badge_html
from src.models import PipelineOutput

_LOGO_PATH = "assets/context_analytics_logo.png"


def _load_blog_catalog_for_display(config) -> list[dict]:
    """Load the blog catalog and cache in session state.
    Returns an empty list on any error — non-fatal, used only for metadata display.
    """
    cache_key = "blog_catalog_for_display"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    try:
        from src.pipeline.runner import _build_blog_provider
        provider = _build_blog_provider(config)
        rows = provider.load()

        st.session_state["blog_catalog_stats"] = getattr(provider, "load_stats", None)
        st.session_state[cache_key] = rows
        return rows
    except Exception:
        st.session_state[cache_key] = []
        st.session_state["blog_catalog_stats"] = None
        return []


def _render_blog_catalog_panel(config) -> list[dict]:
    """Render research library source, load stats, and refresh control.
    Returns the current catalog for use by the blog recommendations renderer.
    """
    repo = getattr(config, "blog_repository", "mock")
    repo_state_map = {
        "google_sheets": ("Google Sheets", "connected"),
        "csv": ("CSV Catalog", "connected"),
        "mock": ("Mock Data", "mock"),
    }
    repo_label, repo_state = repo_state_map.get(repo, (repo, "mock"))

    col_left, col_right = st.columns([5, 2])
    with col_left:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:0.5rem;'
            f'font-size:0.8125rem;color:#475569;padding:0.25rem 0;">'
            f"Research library: {status_badge_html(repo_label, repo_state)}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_right:
        if st.button("Refresh library", key="refresh_blog_catalog", help="Reload research library"):
            st.session_state.pop("blog_catalog_for_display", None)
            st.session_state.pop("blog_catalog_stats", None)
            try:
                from src.pipeline.runner import _build_blog_provider
                provider = _build_blog_provider(config)
                if hasattr(provider, "refresh"):
                    provider.refresh()
            except Exception:
                pass
            st.rerun()

    catalog = _load_blog_catalog_for_display(config)
    stats = st.session_state.get("blog_catalog_stats")

    if stats is not None:
        render_metric_row([
            {"label": "Research items", "value": stats.valid},
            {"label": "Skipped rows", "value": stats.skipped},
            {"label": "Duplicates", "value": stats.duplicates},
        ])
        if stats.warnings:
            with st.expander(f"Validation notes ({len(stats.warnings)})"):
                for w in stats.warnings:
                    st.caption(w)
    elif catalog:
        st.caption(f"{len(catalog)} research items loaded.")

    return catalog


def render() -> None:
    output: PipelineOutput = st.session_state.pipeline_output

    # Load config for header status badges (non-fatal if it fails).
    try:
        from src.config import get_config
        config = get_config()
    except Exception:
        config = None

    render_app_header(
        logo_path=_LOGO_PATH,
        title=output.input.company_name,
        subtitle=(
            f"Intelligence Report  ·  "
            f"Generated {output.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
        ),
        config=config,
    )

    account_type = "Existing Account" if not output.input.is_new_prospect else "New Prospect"
    render_metric_row([
        {"label": "Account Type", "value": account_type},
        {"label": "Products Matched", "value": len(output.product_recommendations)},
        {"label": "Blogs Matched", "value": len(output.client_facing.blog_recommendations)},
        {"label": "Model", "value": output.model_used},
    ])

    st.markdown("<div style='margin-top:0.75rem;'>", unsafe_allow_html=True)
    if st.button("Run Another Account", type="tertiary", key="back"):
        st.session_state.page = "select"
        st.session_state.pipeline_output = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    internal_tab, research_tab, products_tab, email_tab = st.tabs([
        "Internal Brief",
        "Web Research",
        "Products",
        "Outreach Email",
    ])

    with internal_tab:
        render_internal_brief(output.internal)

    with research_tab:
        render_web_research(output.web_research)

    with products_tab:
        render_product_recommendations(output.product_recommendations)

        st.markdown("<div style='margin-top:1.5rem;'>", unsafe_allow_html=True)
        section_header("Research Library")
        if config is not None:
            catalog = _render_blog_catalog_panel(config)
        else:
            catalog = []
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1.25rem;'>", unsafe_allow_html=True)
        render_blog_recommendations(output.client_facing.blog_recommendations, catalog=catalog)
        st.markdown("</div>", unsafe_allow_html=True)

    with email_tab:
        render_outreach_emails(
            output.client_facing.outreach_emails,
            fallback_email=output.client_facing.outreach_email,
        )
