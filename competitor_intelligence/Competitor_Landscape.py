import json
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

st.set_page_config(
    page_title="Competitor Landscape",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject shared theme
_css_path = Path(__file__).parent.parent / "app" / "components" / "_theme.css"
if _css_path.exists():
    st.markdown(f"<style>{_css_path.read_text()}</style>", unsafe_allow_html=True)

# Session state
for _key in ("report", "running", "from_cache", "suggest_name", "suggest_url", "company_mode"):
    if _key not in st.session_state:
        st.session_state[_key] = None

if st.session_state.company_mode is None:
    st.session_state.company_mode = "ca"

# watchlist_path is resolved per mode via _config.watchlist_path


def _get_config(mode: str):
    try:
        from competitor_intelligence.config import load_config as _load_config
        return _load_config(company_mode=mode)
    except ValueError as _cfg_err:
        st.error(str(_cfg_err))
        st.stop()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_cached(company_name: str, config):
    slug = re.sub(r"[^a-z0-9]+", "_", company_name.lower()).strip("_")
    matches = sorted(config.outputs_dir.glob(f"competitor_{slug}_*.json"))
    if not matches:
        return None
    try:
        from competitor_intelligence.models import CompetitorReport
        return CompetitorReport.model_validate_json(matches[-1].read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_researched(company_name: str, config) -> bool:
    slug = re.sub(r"[^a-z0-9]+", "_", company_name.lower()).strip("_")
    return bool(list(config.outputs_dir.glob(f"competitor_{slug}_*.json")))


def _list_recent_searches(config) -> list[tuple[str, datetime, Path]]:
    results, seen = [], set()
    for path in sorted(config.outputs_dir.glob("competitor_*.json"), reverse=True)[:20]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            name = data["competitor_profile"]["company_name"]
            dt = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
            if name.lower() not in seen:
                seen.add(name.lower())
                results.append((name, dt, path))
        except Exception:
            continue
    return results[:8]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Company mode toggle
    _mode_label = st.radio(
        "View as",
        options=["Context Analytics", "Bridgewise"],
        horizontal=True,
        key="mode_radio",
    )
    _new_mode = "ca" if _mode_label == "Context Analytics" else "bridgewise"
    if _new_mode != st.session_state.company_mode:
        st.session_state.company_mode = _new_mode
        st.session_state.report = None
        st.session_state.from_cache = None
        st.rerun()

    _config = _get_config(st.session_state.company_mode)

    st.markdown("---")

    # Logo
    _logo = _config.logo_path
    if _logo and Path(_logo).exists():
        st.image(str(_logo), width=150)
    st.markdown("---")

    company_name = st.text_input("Company name", placeholder="e.g. AlphaSense")
    website_url = st.text_input("Website URL (optional)", placeholder="https://alpha-sense.com")
    include_product_search = st.checkbox(
        "Search for product equivalents",
        value=False,
        help="Runs a second targeted search for competitor products matching our product categories. Adds ~30-60s.",
    )
    run_button = st.button("Research Competitor", type="primary", use_container_width=True)

    # Add competitor expander
    with st.expander("+ Add competitor to watchlist"):
        new_name = st.text_input("Company name", key="add_name")
        new_url = st.text_input("Website", key="add_url")
        new_cat = st.selectbox("Category", key="add_cat", options=[
            "Financial NLP & Sentiment",
            "News Sentiment & NLP",
            "Document Intelligence",
            "Alt-Data Discovery",
            "Alt-Data Marketplace",
            "Consumer & Transaction Data",
            "Private Company & Alternative Assets",
            "Quantitative Alt-Data",
            "AI Investment Ratings",
            "Other",
        ])
        new_why = st.text_area("Why relevant (1-2 sentences)", key="add_why", height=80)
        if st.button("Add to watchlist", key="add_btn", use_container_width=True):
            from competitor_intelligence.watchlist import add_to_watchlist
            if new_name.strip():
                ok = add_to_watchlist(_config.watchlist_path, new_name, new_url, new_cat, new_why)
                if ok:
                    st.success(f"{new_name.strip()} added.")
                else:
                    st.warning(f"{new_name.strip()} is already on the watchlist.")
            else:
                st.warning("Please enter a company name.")

    # Recent searches (scoped to current mode's outputs)
    recent = _list_recent_searches(_config)
    if recent:
        st.markdown("---")
        st.markdown('<p class="ca-nav-section-label">Recent Searches</p>', unsafe_allow_html=True)
        for r_name, r_dt, r_path in recent:
            label = f"{r_name}  ·  {r_dt.strftime('%b %d')}"
            if st.button(label, key=f"recent_{r_name}", use_container_width=True):
                from competitor_intelligence.models import CompetitorReport
                st.session_state.report = CompetitorReport.model_validate_json(
                    r_path.read_text(encoding="utf-8")
                )
                st.session_state.from_cache = True
                st.rerun()

    st.markdown("---")
    st.markdown(
        '<div class="ca-sidebar-about">'
        f"<p>Enter a competitor's name to generate a structured profile and side-by-side "
        f"comparison against {_config.our_company_name} products and audience.</p>"
        "<p>All outputs require human review before use.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Header ────────────────────────────────────────────────────────────────────
def _header(our_company_name: str) -> None:
    st.markdown(
        '<div class="ca-header">'
        '<div class="ca-header__brand"><div class="ca-header__text-block">'
        '<p class="ca-header__title">Competitor Landscape</p>'
        f'<p class="ca-header__subtitle">Powered by Claude web search · {our_company_name}</p>'
        "</div></div></div>",
        unsafe_allow_html=True,
    )


_header(_config.our_company_name)


# ── Research runner ───────────────────────────────────────────────────────────
def _run_research(name: str, url: str | None, product_search: bool = False) -> None:
    from competitor_intelligence.analyzer import CompetitorAnalyzer, generate_battle_card
    from competitor_intelligence.models import CompetitorReport
    from competitor_intelligence.profile_loader import load_our_profile
    from competitor_intelligence.researcher import CompetitorResearcher

    our_company_name = _config.our_company_name
    our_company_short = _config.our_company_short

    try:
        with st.status(f"Researching {name}...", expanded=True) as status:
            st.write("Searching the web for company info, products, and recent news...")
            researcher = CompetitorResearcher(api_key=_config.anthropic_api_key, model=_config.research_model)
            profile = researcher.research(name, url or None)

            n_products = len(profile.products)

            if product_search:
                st.write("Searching for product-specific equivalents...")
                import yaml as _yaml
                _pd = _yaml.safe_load(_config.products_yaml_path.read_text(encoding="utf-8"))
                _our_cats = [
                    c.get("category") or c.get("name", "")
                    for c in (_pd.get("product_categories") or _pd.get("products") or [])
                ]
                extra = researcher.research_products(profile.company_name, _our_cats, our_company_name=our_company_name)
                existing = {p.name.lower() for p in profile.products}
                new_prods = [p for p in extra if p.name.lower() not in existing]
                if new_prods:
                    profile = profile.model_copy(update={"products": profile.products + new_prods})
                    n_products = len(profile.products)

            st.write(
                f"Found {n_products} product(s). "
                f"Loading {our_company_name} reference profile..."
            )
            our_text, files_loaded = load_our_profile(
                products_yaml_path=_config.products_yaml_path,
                our_profile_dir=_config.our_profile_dir,
            )

            st.write(
                f"Loaded {len(files_loaded)} reference file(s). "
                "Running comparative analysis..."
            )
            analyzer = CompetitorAnalyzer(api_key=_config.anthropic_api_key, model=_config.model)
            analysis = analyzer.analyze(
                profile,
                our_text,
                our_company_name=our_company_name,
                our_company_short=our_company_short,
            )

            st.write("Generating sales battle card...")
            battle_card = generate_battle_card(
                _config.anthropic_api_key,
                _config.model,
                name,
                analysis,
                our_company_name=our_company_name,
                our_company_short=our_company_short,
            )

            st.write("Saving report...")
            report = CompetitorReport(
                competitor_profile=profile,
                competitive_analysis=analysis,
                battle_card=battle_card,
                model_used=_config.model,
                our_profile_files_loaded=files_loaded,
            )
            _save_report(report, _config.outputs_dir)

            status.update(
                label=f"Done — {n_products} product(s) found.",
                state="complete",
                expanded=False,
            )

        st.session_state.report = report
        st.session_state.from_cache = False

    except Exception as exc:
        st.error(f"Research failed: {exc}")
        with st.expander("Error details"):
            st.code(traceback.format_exc())


def _save_report(report, outputs_dir: Path) -> None:
    slug = re.sub(r"[^a-z0-9]+", "_", report.competitor_profile.company_name.lower()).strip("_")
    timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")
    path = outputs_dir / f"competitor_{slug}_{timestamp}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


# ── Watchlist card trigger (fires before run_button so rerun resolves it) ────
if st.session_state.get("suggest_name"):
    _suggest_name = st.session_state.suggest_name
    _suggest_url = st.session_state.suggest_url or None
    st.session_state.suggest_name = None
    st.session_state.suggest_url = None
    cached = _load_cached(_suggest_name, _config)
    if cached:
        st.session_state.report = cached
        st.session_state.from_cache = True
    else:
        st.session_state.report = None
        st.session_state.from_cache = False
        _run_research(_suggest_name, _suggest_url, product_search=include_product_search)

# ── Manual search trigger ─────────────────────────────────────────────────────
elif run_button and company_name.strip():
    cached = _load_cached(company_name.strip(), _config)
    if cached:
        st.session_state.report = cached
        st.session_state.from_cache = True
    else:
        st.session_state.report = None
        st.session_state.from_cache = False
        _run_research(company_name.strip(), website_url.strip() or None, product_search=include_product_search)
elif run_button:
    st.warning("Please enter a company name.")

# ── Display report or watchlist ───────────────────────────────────────────────
if st.session_state.report:
    from competitor_intelligence import renderer
    from competitor_intelligence.models import CompetitorReport

    report: CompetitorReport = st.session_state.report

    # Cache banner + re-run button
    if st.session_state.from_cache:
        age = report.generated_at.strftime("%b %d, %Y at %H:%M UTC")
        col_banner, col_btn = st.columns([5, 1])
        with col_banner:
            st.markdown(
                f'<div class="ca-info-banner">Loaded from cache — researched {age}</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Re-run", type="secondary"):
                st.session_state.from_cache = False
                st.session_state.report = None
                _run_research(
                    report.competitor_profile.company_name,
                    report.competitor_profile.website,
                    product_search=include_product_search,
                )
                st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Competitor Profile",
        "Comparative Analysis",
        "Battle Card",
        "Sources & Export",
    ])

    with tab1:
        renderer.render_competitor_profile(report.competitor_profile)

    with tab2:
        renderer.render_comparative_analysis(report.competitive_analysis)

    with tab3:
        _battle_card = getattr(report, "battle_card", None)
        if _battle_card is not None:
            renderer.render_battle_card(_battle_card, company_short=_config.our_company_short)
        else:
            st.info("This report was generated before the Battle Card feature.")
            if st.button("Generate Battle Card", type="primary"):
                from competitor_intelligence.analyzer import generate_battle_card
                with st.spinner(f"Generating battle card for {report.competitor_profile.company_name}..."):
                    bc = generate_battle_card(
                        _config.anthropic_api_key,
                        _config.model,
                        report.competitor_profile.company_name,
                        report.competitive_analysis,
                        our_company_name=_config.our_company_name,
                        our_company_short=_config.our_company_short,
                    )
                report = report.model_copy(update={"battle_card": bc})
                _save_report(report, _config.outputs_dir)
                st.session_state.report = report
                st.rerun()

    with tab4:
        renderer.render_sources_and_export(report)

else:
    from competitor_intelligence import renderer
    from competitor_intelligence.watchlist import (
        add_to_watchlist,
        discover_competitors,
        load_watchlist,
    )

    watchlist = load_watchlist(_config.watchlist_path)

    # Discover more button
    col_hdr, col_disc = st.columns([4, 1])
    with col_disc:
        if st.button("Discover more with AI", key="discover", use_container_width=True):
            existing_names = [c["name"] for c in watchlist]
            with st.spinner("Asking Claude for suggestions..."):
                suggestions = discover_competitors(
                    _config.anthropic_api_key,
                    _config.model,
                    existing_names,
                    company_mode=_config.company_mode,
                    our_company_name=_config.our_company_name,
                )
            added = 0
            for s in suggestions:
                if add_to_watchlist(
                    _config.watchlist_path,
                    s.get("name", ""),
                    s.get("website", ""),
                    s.get("category", ""),
                    s.get("why_relevant", ""),
                ):
                    added += 1
            if added:
                st.success(f"Added {added} new competitor(s) to the watchlist.")
                st.rerun()
            else:
                st.info("No new competitors found — all suggestions are already on the watchlist.")

    renderer.render_watchlist(
        watchlist,
        lambda name: _is_researched(name, _config),
        company_name=_config.our_company_name,
    )
