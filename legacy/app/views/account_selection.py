import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from app.components.ui import (
    empty_state,
    error_state,
    render_app_header,
    section_header,
    status_badge_html,
)
from src.models import PipelineInput

_LOGO_PATH = "assets/context_analytics_logo.png"


def _load_config():
    """Return (config, error_message).  error_message is None on success."""
    try:
        from src.config import get_config
        return get_config(), None
    except ValueError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, f"Unexpected configuration error: {exc}"


def _get_crm_provider(config):
    """Instantiate the CRM provider selected by config.crm_repository."""
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
    from src.providers.mock_monday import MockMondayProvider
    return MockMondayProvider(config.mock_monday_path)


def _ensure_accounts_loaded(config) -> bool:
    """Populate st.session_state.crm_accounts if not already present.
    Returns True on success, False on failure (error shown in-place).
    """
    if "crm_accounts" in st.session_state:
        return True

    source_label = "Monday.com" if config.crm_repository == "monday" else "mock data"
    with st.spinner(f"Loading accounts from {source_label}..."):
        try:
            provider = _get_crm_provider(config)
            st.session_state.crm_accounts = provider.list_accounts()
            return True
        except Exception as exc:
            st.error(
                f"Could not load CRM accounts from {source_label}. "
                f"Check your MONDAY_API_TOKEN, MONDAY_BOARD_ID, and network access."
            )
            with st.expander("Error details"):
                st.code(str(exc))
            return False


def render() -> None:
    render_app_header(
        logo_path=_LOGO_PATH,
        title="Client Intelligence Studio",
        subtitle="Generate personalized, evidence-backed collateral for client conversations.",
    )

    section_header("Select a lead or add a new one")

    mode = st.radio(
        "Account type",
        ["Select from Monday CRM", "New lead / company not in Monday"],
        horizontal=True,
        label_visibility="collapsed",
    )

    pipeline_input = None

    if mode == "Select from Monday CRM":
        config, config_error = _load_config()

        if config_error:
            st.error("Configuration error — check your .env file.")
            with st.expander("Details"):
                st.code(config_error)
            st.info(
                "Required: ANTHROPIC_API_KEY in .env. "
                "For live Monday.com data also set MONDAY_API_TOKEN, MONDAY_BOARD_ID, "
                "and CRM_REPOSITORY=monday."
            )
        else:
            crm_state = "connected" if config.crm_repository == "monday" else "mock"
            crm_label = "Monday.com" if config.crm_repository == "monday" else "Mock Data"

            col_left, col_right = st.columns([5, 2])
            with col_left:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:0.5rem;'
                    f'font-size:0.8125rem;color:#475569;padding:0.25rem 0;">'
                    f"CRM source: {status_badge_html(crm_label, crm_state)}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with col_right:
                if st.button("Refresh accounts", help="Reload account list from CRM"):
                    st.session_state.pop("crm_accounts", None)

            if _ensure_accounts_loaded(config):
                accounts = st.session_state.crm_accounts
                if not accounts:
                    empty_state(
                        "No accounts found",
                        "No accounts were returned from the configured CRM board.",
                    )
                else:
                    options = {a["company_name"]: a["monday_item_id"] for a in accounts}
                    selected_name = st.selectbox(
                        f"Select a lead ({len(accounts)} imported from CRM)",
                        list(options.keys()),
                        label_visibility="visible",
                    )
                    st.caption("These are active leads pulled from your CRM board. Select one to generate intelligence collateral.")
                    monday_item_id = options[selected_name]
                    pipeline_input = PipelineInput(
                        company_name=selected_name,
                        is_new_prospect=False,
                        monday_item_id=monday_item_id,
                    )

    else:
        st.caption("Enter a company that isn't in your Monday CRM board. Research will be sourced from the web only.")
        company_name = st.text_input("Company name", placeholder="e.g. Acme Capital Partners")
        website_url = st.text_input("Website URL (optional)", placeholder="https://acmecapital.com")
        if company_name:
            pipeline_input = PipelineInput(
                company_name=company_name,
                is_new_prospect=True,
                website_url=website_url or None,
            )

    st.markdown("<div style='margin-top:1.5rem;'>", unsafe_allow_html=True)

    if pipeline_input:
        if st.button("Run Intelligence Research", type="primary", use_container_width=True):
            _run_pipeline(pipeline_input)
    else:
        st.button(
            "Run Intelligence Research",
            type="primary",
            use_container_width=True,
            disabled=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _run_pipeline(pipeline_input: PipelineInput) -> None:
    import time

    from src.config import get_config
    from src.pipeline.runner import run_pipeline

    section_header("Running Research Pipeline")

    stages = [
        "Loading CRM data",
        "Running web research",
        "Matching blog content",
        "Matching products",
        "Generating AI content",
        "Assembling report",
    ]

    progress = st.progress(0)
    status = st.empty()

    try:
        config = get_config()
    except ValueError as e:
        error_state("Configuration error", str(e))
        st.info("Add your ANTHROPIC_API_KEY to a .env file in the project root.")
        return

    for i, stage in enumerate(stages):
        status.info(f"Stage {i + 1} of {len(stages)}: {stage}")
        progress.progress((i + 1) / len(stages))
        time.sleep(0.1)

    try:
        output = run_pipeline(pipeline_input, config)
        st.session_state.pipeline_output = output
        st.session_state.pipeline_input = pipeline_input
        progress.progress(1.0)
        status.success("Research complete.")
        time.sleep(0.5)
        st.session_state.page = "report"
        st.rerun()
    except Exception as e:
        import traceback
        progress.empty()
        status.empty()
        error_state("Pipeline failed", "An error occurred while running the research pipeline.")
        with st.expander("Error details"):
            st.code(traceback.format_exc())
