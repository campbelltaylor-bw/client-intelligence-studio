import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import yaml

st.set_page_config(page_title="Product Landscape", page_icon=None, layout="wide")

_css_path = Path(__file__).parent.parent.parent / "app" / "components" / "_theme.css"
if _css_path.exists():
    st.markdown(f"<style>{_css_path.read_text()}</style>", unsafe_allow_html=True)

try:
    from competitor_intelligence.config import load_config
    _mode = st.session_state.get("company_mode") or "ca"
    _config = load_config(company_mode=_mode)
except ValueError as _e:
    st.error(str(_e))
    st.stop()

from competitor_intelligence.models import MarketEntry
from competitor_intelligence.researcher import CompetitorResearcher

_products_data = yaml.safe_load(_config.products_yaml_path.read_text(encoding="utf-8"))
_categories = [
    {
        "name": c["category"],
        "description": (c.get("description") or "").strip(),
    }
    for c in _products_data.get("product_categories", [])
]

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="ca-header">'
    '<div class="ca-header__brand"><div class="ca-header__text-block">'
    '<p class="ca-header__title">Product Landscape</p>'
    f'<p class="ca-header__subtitle">Find all companies competing in a {_config.our_company_name} product category</p>'
    "</div></div></div>",
    unsafe_allow_html=True,
)

# ── Category selector ──────────────────────────────────────────────────────────
selected_name = st.selectbox(
    f"Select a {_config.our_company_name} product category",
    options=[c["name"] for c in _categories],
)
selected_desc = next((c["description"] for c in _categories if c["name"] == selected_name), "")
slug = re.sub(r"[^a-z0-9]+", "_", selected_name.lower()).strip("_")

if selected_desc:
    st.markdown(
        f'<div class="ca-info-banner" style="margin-bottom:1rem;">{selected_desc}</div>',
        unsafe_allow_html=True,
    )


# ── Cache helpers ──────────────────────────────────────────────────────────────
def _load_cached(slug: str):
    matches = sorted(_config.outputs_dir.glob(f"market_{slug}_*.json"))
    if not matches:
        return None, None
    try:
        data = json.loads(matches[-1].read_text(encoding="utf-8"))
        entries = [MarketEntry(**e) for e in data.get("entries", [])]
        return entries, data.get("scanned_at", "")
    except Exception:
        return None, None


def _save_cache(slug: str, category: str, entries: list) -> None:
    now = datetime.now(timezone.utc)
    path = _config.outputs_dir / f"market_{slug}_{now.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(
        json.dumps(
            {
                "category": category,
                "scanned_at": now.strftime("%b %d, %Y at %H:%M UTC"),
                "entries": [e.model_dump() for e in entries],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


# ── Scan trigger ───────────────────────────────────────────────────────────────
cached_entries, cached_at = _load_cached(slug)

if cached_entries:
    st.markdown(
        f'<div class="ca-info-banner">Loaded from cache — scanned {cached_at}</div>',
        unsafe_allow_html=True,
    )
    col_rescan, _ = st.columns([1, 5])
    with col_rescan:
        do_scan = st.button("Re-scan", type="secondary", use_container_width=True)
    entries = cached_entries if not do_scan else None
else:
    do_scan = st.button("Scan Market", type="primary")
    entries = None

if do_scan:
    researcher = CompetitorResearcher(api_key=_config.anthropic_api_key, model=_config.research_model)
    with st.status(f"Scanning market for '{selected_name}'...", expanded=True) as status:
        st.write("Searching for companies and products in this space...")
        entries = researcher.scan_market(selected_name, selected_desc, our_company_name=_config.our_company_name)
        _save_cache(slug, selected_name, entries)
        status.update(
            label=f"Done — {len(entries)} companies found.",
            state="complete",
            expanded=False,
        )


# ── Results ────────────────────────────────────────────────────────────────────
def _render_entries(entries: list) -> None:
    st.markdown(f"### {len(entries)} companies in this space")
    cols = st.columns(3)
    for i, entry in enumerate(entries):
        with cols[i % 3]:
            product_line = (
                f'<p class="ca-card__label" style="margin-bottom:0.25rem;">{entry.product}</p>'
                if entry.product else ""
            )
            audience_line = (
                f'<p class="ca-card__body" style="color:var(--ca-text-muted);font-size:0.8rem;'
                f'margin-top:0.25rem;">{entry.target_audience}</p>'
                if entry.target_audience else ""
            )
            website_line = (
                f'<a href="{entry.website}" target="_blank" '
                f'style="font-size:0.8rem;color:var(--ca-primary);">{entry.website}</a>'
                if entry.website else ""
            )
            st.markdown(
                f'<div class="ca-card" style="min-height:140px;">'
                f'<p class="ca-card__title" style="margin-bottom:0.2rem;">{entry.company}</p>'
                f'{product_line}'
                f'<p class="ca-card__body">{entry.description or ""}</p>'
                f'{audience_line}'
                f'{website_line}'
                f'</div>',
                unsafe_allow_html=True,
            )


if entries:
    _render_entries(entries)
elif not do_scan and not cached_entries:
    st.markdown(
        '<div class="empty-state">'
        '<p class="empty-state__title">No scan yet</p>'
        '<p class="empty-state__detail">Select a product category above and click '
        '"Scan Market" to find companies competing in that space.</p>'
        "</div>",
        unsafe_allow_html=True,
    )
