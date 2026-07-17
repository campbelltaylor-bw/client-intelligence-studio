"""
Central UI module for Client Intelligence Studio.

All design tokens, CSS injection, and reusable HTML component helpers live here.
Business logic and data models are never imported from this module.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal

import streamlit as st

# ---------------------------------------------------------------------------
# Theme injection
# ---------------------------------------------------------------------------

_THEME_CSS_PATH = Path(__file__).parent / "_theme.css"


def inject_theme() -> None:
    """Inject the complete CSS design system into the Streamlit page.

    Call once at the top of app/main.py immediately after st.set_page_config().
    Reads _theme.css from the same directory as this module.
    """
    if _THEME_CSS_PATH.exists():
        css = _THEME_CSS_PATH.read_text()
    else:
        css = ""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# App header
# ---------------------------------------------------------------------------

def render_app_header(
    logo_path: str | Path,
    title: str,
    subtitle: str,
    config=None,
) -> None:
    """Render the main page header: logo + title + subtitle (left), status badges (right).

    Parameters
    ----------
    logo_path:
        Path to context_analytics_logo.png. Fails gracefully if missing.
    title:
        Primary heading text (company name or app name).
    subtitle:
        One-line descriptor or timestamp rendered below the title.
    config:
        AppConfig instance. If provided, renders CRM/AI/Research status badges.
    """
    logo_col, title_col, status_col = st.columns([1, 5, 2])

    with logo_col:
        p = Path(logo_path)
        if p.exists():
            st.image(str(p), width=120)

    with title_col:
        st.markdown(
            f'<div class="ca-header__text-block">'
            f'<p class="ca-header__title">{title}</p>'
            f'<p class="ca-header__subtitle">{subtitle}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if config is not None:
        with status_col:
            crm_label = "Monday.com" if getattr(config, "crm_repository", "mock") == "monday" else "Mock CRM"
            crm_state: StatusState = (
                "connected" if getattr(config, "crm_repository", "mock") == "monday" else "mock"
            )
            ai_state: StatusState = "connected" if getattr(config, "anthropic_api_key", "") else "disconnected"
            blog_label = (
                "Google Sheets"
                if getattr(config, "blog_repository", "mock") == "google_sheets"
                else ("CSV" if getattr(config, "blog_repository", "mock") == "csv" else "Mock Data")
            )
            blog_state: StatusState = (
                "connected"
                if getattr(config, "blog_repository", "mock") in ("google_sheets", "csv")
                else "mock"
            )
            st.markdown(
                f'<div class="ca-header__status">'
                f'{status_badge_html(crm_label, crm_state)}'
                f'{status_badge_html("AI", ai_state)}'
                f'{status_badge_html(blog_label, blog_state)}'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<hr style="margin:0.75rem 0 1.5rem;">', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

def render_nav_sidebar(current_page: Literal["select", "report"]) -> None:
    """Render the sidebar: logo and footer disclaimer only."""
    logo_path = Path("assets/context_analytics_logo.png")
    if logo_path.exists():
        st.sidebar.markdown('<div class="ca-sidebar-logo">', unsafe_allow_html=True)
        st.sidebar.image(str(logo_path), width=150)
        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    st.sidebar.markdown(
        '<div class="ca-sidebar-footer">'
        "<p>All generated content requires human review before use.</p>"
        "<p>No automatic email delivery.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Connection status in sidebar
# ---------------------------------------------------------------------------

def render_connection_status(config) -> None:
    """Render CRM, AI, and Research Library status indicators inside the sidebar."""
    crm_state: StatusState = (
        "connected" if getattr(config, "crm_repository", "mock") == "monday" else "mock"
    )
    ai_state: StatusState = "connected" if getattr(config, "anthropic_api_key", "") else "disconnected"
    blog_repo = getattr(config, "blog_repository", "mock")
    blog_state: StatusState = "connected" if blog_repo in ("google_sheets", "csv") else "mock"

    crm_label = "Monday.com" if crm_state == "connected" else "Mock CRM"
    blog_label = {"google_sheets": "Google Sheets", "csv": "CSV"}.get(blog_repo, "Mock Data")

    st.sidebar.markdown(
        '<div class="ca-connection-list">'
        f"{status_badge_html(crm_label, crm_state)}"
        f'{status_badge_html("AI Model", ai_state)}'
        f"{status_badge_html(blog_label, blog_state)}"
        "</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Status badge HTML helper
# ---------------------------------------------------------------------------

StatusState = Literal["connected", "warning", "disconnected", "mock"]


def status_badge_html(label: str, state: StatusState) -> str:
    """Return an HTML status indicator pill string.

    Parameters
    ----------
    label:
        Short display text, e.g. "CRM", "AI Model".
    state:
        One of "connected", "warning", "disconnected", "mock".
        Controls color (green / amber / red / gray).

    Returns
    -------
    str
        An HTML ``<span>`` element ready for use in ``st.markdown(..., unsafe_allow_html=True)``.
    """
    return (
        f'<span class="status-indicator status-indicator--{state}">{label}</span>'
    )


# ---------------------------------------------------------------------------
# Source label HTML helper
# ---------------------------------------------------------------------------

def source_label_html(tag: str) -> str:
    """Return an HTML source attribution label badge string.

    Replaces the pill-style badge from source_badge.py with a more restrained
    monospace label (3px radius, bordered, 10px uppercase).

    Parameters
    ----------
    tag:
        One of "CRM_FACT", "PUBLIC_FACT", "AI_INFERENCE".

    Returns
    -------
    str
        An HTML ``<span>`` element ready for use in ``st.markdown(..., unsafe_allow_html=True)``.

    Example
    -------
    >>> st.markdown(f"{source_label_html(fact.source)} {fact.value}", unsafe_allow_html=True)
    """
    _MAP = {
        "CRM_FACT": ("CRM Fact", "source-badge--crm"),
        "PUBLIC_FACT": ("Public Fact", "source-badge--public"),
        "AI_INFERENCE": ("AI Inference", "source-badge--ai"),
    }
    text, cls = _MAP.get(tag, ("Unknown", "source-badge--unknown"))
    return f'<span class="source-badge {cls}">{text}</span>'


# ---------------------------------------------------------------------------
# Section header
# ---------------------------------------------------------------------------

def section_header(title: str, subtitle: str | None = None) -> None:
    """Render a section heading with an accent-colored bottom border.

    Parameters
    ----------
    title:
        Primary section label.
    subtitle:
        Optional supporting caption in muted text below the title.
    """
    sub_html = (
        f'<p class="section-header__subtitle">{subtitle}</p>' if subtitle else ""
    )
    st.markdown(
        f'<div class="section-header">'
        f'<p class="section-header__title">{title}</p>'
        f"{sub_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

def empty_state(title: str, detail: str) -> None:
    """Render a centered dashed-border placeholder for zero-data conditions.

    Parameters
    ----------
    title:
        Short heading, e.g. "No recommendations found".
    detail:
        Explanatory text, e.g. "Run the pipeline to generate product matches."
    """
    st.markdown(
        f'<div class="empty-state">'
        f'<p class="empty-state__title">{title}</p>'
        f'<p class="empty-state__detail">{detail}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Error state
# ---------------------------------------------------------------------------

def error_state(title: str, detail: str) -> None:
    """Render a styled inline error block with a red left-border accent.

    Use inside tab panels for structural error placement.
    For top-level config errors, st.error() is still appropriate.

    Parameters
    ----------
    title:
        Error label, e.g. "Pipeline failed".
    detail:
        Additional context such as the exception message (sanitized).
    """
    st.markdown(
        f'<div class="error-state">'
        f'<p class="error-state__title">{title}</p>'
        f'<p class="error-state__detail">{detail}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Loading state
# ---------------------------------------------------------------------------

def loading_state(message: str) -> None:
    """Render a styled inline loading placeholder.

    For actual blocking work, wrap the work in ``with st.spinner(message):``
    instead. This function is for declarative, static placeholders.

    Parameters
    ----------
    message:
        Descriptive text, e.g. "Loading research library..."
    """
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:0.625rem;'
        f"padding:1rem 0;color:#64748b;font-size:0.875rem;font-family:var(--ca-font);\">"
        f"<span>{message}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Metric row
# ---------------------------------------------------------------------------

def render_metric_row(metrics: list[dict]) -> None:
    """Render a horizontal row of st.metric() cards.

    Parameters
    ----------
    metrics:
        List of dicts with keys:
        - ``label`` (str): displayed above the value
        - ``value`` (str | int | float): the primary KPI
        - ``delta`` (str | None, optional): delta annotation

    Example
    -------
    >>> render_metric_row([
    ...     {"label": "Account Type", "value": "Existing Account"},
    ...     {"label": "Products Matched", "value": 4},
    ...     {"label": "Model", "value": "claude-sonnet-4-6"},
    ... ])
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(
                label=m["label"],
                value=m["value"],
                delta=m.get("delta"),
            )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _encode_image(path: str | Path) -> str:
    """Base64-encode an image file for use in data-URI HTML embedding.

    Parameters
    ----------
    path:
        Absolute or relative path to an image file.

    Returns
    -------
    str
        Base64-encoded bytes as an ASCII string.

    Raises
    ------
    FileNotFoundError
        If the file at ``path`` does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {p}")
    return base64.b64encode(p.read_bytes()).decode()
