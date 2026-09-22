import re

import streamlit as st

from competitor_intelligence.models import (
    BattleCard,
    CompetitiveAnalysis,
    CompetitorProfile,
    CompetitorReport,
)


def render_competitor_profile(profile: CompetitorProfile) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Company Size", profile.company_size or "Unknown")
    c2.metric("Founded", profile.founded or "Unknown")
    c3.metric("Headquarters", profile.headquarters or "Unknown")
    c4.metric("Market Cap", profile.market_cap or "Private / N/A")

    st.markdown("---")
    _section_header("About")
    st.markdown(profile.about or "_No description found._")

    if profile.mission_statement:
        _section_header("Mission Statement")
        st.markdown(f"> {profile.mission_statement}")

    if profile.additional_locations:
        _section_header("Additional Locations")
        st.markdown("\n".join(f"- {loc}" for loc in profile.additional_locations))

    if profile.products:
        _section_header("Products")
        for product in profile.products:
            label = product.name
            if product.launched:
                label += f" (launched {product.launched})"
            with st.expander(label):
                if product.target_audience:
                    st.markdown(f"**Target Audience:** {product.target_audience}")
                if product.primary_users:
                    st.markdown(f"**Primary Users:** {product.primary_users}")
                if product.coverage:
                    st.markdown(f"**Coverage:** {product.coverage}")
                if product.use_cases:
                    st.markdown("**Use Cases:**")
                    st.markdown("\n".join(f"- {u}" for u in product.use_cases))
                if product.deliverable_formats:
                    st.markdown(f"**Deliverable Formats:** {', '.join(product.deliverable_formats)}")
                if product.source_url:
                    st.markdown(f"[Source]({product.source_url})")

    if profile.recent_news:
        _section_header("Recent News")
        for item in profile.recent_news:
            st.markdown(f"- {item}")


def render_comparative_analysis(analysis: CompetitiveAnalysis) -> None:
    _section_header("Executive Summary")
    st.markdown(
        f'<div class="ca-info-banner">{analysis.executive_summary}</div>',
        unsafe_allow_html=True,
    )

    if analysis.product_comparisons:
        _section_header("Product Comparison")
        for comp in analysis.product_comparisons:
            their_label = comp.their_product if comp.their_product else "_No equivalent_"
            html = f"""
<div class="ca-card">
  <p class="ca-card__label">Our Product vs. Theirs</p>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:0.75rem;">
    <div>
      <strong style="font-size:0.9375rem;">{comp.our_product}</strong>
    </div>
    <div>
      <strong style="font-size:0.9375rem;">{their_label}</strong>
    </div>
  </div>
  <p class="ca-card__body"><strong>Overlap:</strong> {comp.overlap_summary}</p>
  <p class="ca-card__body" style="margin-top:0.375rem;"><strong>Differentiator:</strong> {comp.differentiator}</p>
</div>"""
            st.markdown(html, unsafe_allow_html=True)

    _section_header("Audience Overlap")
    ao = analysis.audience_overlap
    col_shared, col_ours, col_theirs = st.columns(3)
    with col_shared:
        st.markdown("**Shared Segments**")
        if ao.shared_segments:
            st.markdown("\n".join(f"- {s}" for s in ao.shared_segments))
        else:
            st.caption("None identified")
    with col_ours:
        st.markdown("**Our Exclusive Segments**")
        if ao.our_exclusive_segments:
            st.markdown("\n".join(f"- {s}" for s in ao.our_exclusive_segments))
        else:
            st.caption("None identified")
    with col_theirs:
        st.markdown("**Their Exclusive Segments**")
        if ao.their_exclusive_segments:
            st.markdown("\n".join(f"- {s}" for s in ao.their_exclusive_segments))
        else:
            st.caption("None identified")

    st.markdown("---")
    col_our_str, col_their_str = st.columns(2)
    with col_our_str:
        _section_header("Our Strengths")
        if analysis.our_strengths:
            st.markdown("\n".join(f"- {s}" for s in analysis.our_strengths))
        else:
            st.caption("None identified")
    with col_their_str:
        _section_header("Their Strengths")
        if analysis.their_strengths:
            st.markdown("\n".join(f"- {s}" for s in analysis.their_strengths))
        else:
            st.caption("None identified")

    st.markdown("---")
    _section_header("Coverage Gaps")
    col_gap_ours, col_gap_theirs = st.columns(2)
    with col_gap_ours:
        st.markdown("**We cover, they don't**")
        if analysis.gaps.we_cover_they_dont:
            st.markdown("\n".join(f"- {g}" for g in analysis.gaps.we_cover_they_dont))
        else:
            st.caption("None identified")
    with col_gap_theirs:
        st.markdown("**They cover, we don't**")
        if analysis.gaps.they_cover_we_dont:
            st.markdown("\n".join(f"- {g}" for g in analysis.gaps.they_cover_we_dont))
        else:
            st.caption("None identified")


def render_battle_card(battle_card: BattleCard, company_short: str = "CA") -> None:
    st.markdown(
        f'<div class="ca-info-banner" style="font-size:1.05rem;font-weight:600;">'
        f'{battle_card.positioning_statement}'
        f'</div>',
        unsafe_allow_html=True,
    )

    if battle_card.top_differentiators:
        _section_header("Top Differentiators")
        cols = st.columns(len(battle_card.top_differentiators))
        for i, (col, diff) in enumerate(zip(cols, battle_card.top_differentiators)):
            with col:
                label = f"{i + 1:02d}"
                st.markdown(
                    f'<div class="ca-card" style="height:100%;">'
                    f'<p class="ca-card__label" style="font-size:1.5rem;font-weight:700;'
                    f'color:var(--ca-primary);margin-bottom:0.5rem;">{label}</p>'
                    f'<p class="ca-card__body">{diff}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    if battle_card.objection_handlers:
        _section_header("Objection Handlers")
        for handler in battle_card.objection_handlers:
            with st.expander(f'"{handler.objection}"'):
                st.markdown(handler.response)

    if battle_card.when_ca_wins or battle_card.when_they_win:
        _section_header(f"When {company_short} Wins / When They Win")
        col_wins, col_loses = st.columns(2)
        with col_wins:
            st.markdown(f"**When {company_short} Wins**")
            if battle_card.when_ca_wins:
                st.markdown("\n".join(f"- {s}" for s in battle_card.when_ca_wins))
            else:
                st.caption("None identified")
        with col_loses:
            st.markdown("**When They Win**")
            if battle_card.when_they_win:
                st.markdown("\n".join(f"- {s}" for s in battle_card.when_they_win))
            else:
                st.caption("None identified")

    if battle_card.discovery_questions:
        _section_header("Discovery Questions")
        for i, q in enumerate(battle_card.discovery_questions, 1):
            st.markdown(
                f'<div style="background:var(--ca-bg-secondary,#f7f8fa);border-radius:6px;'
                f'padding:0.6rem 0.9rem;margin-bottom:0.4rem;">'
                f'<strong style="color:var(--ca-primary);">{i}.</strong> {q}'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_sources_and_export(report: CompetitorReport) -> None:
    _section_header("Sources Cited")
    if report.competitor_profile.source_urls:
        for url in report.competitor_profile.source_urls:
            st.markdown(f"- [{url}]({url})")
    else:
        st.caption("No sources recorded.")

    _section_header("Our Profile Files Loaded")
    if report.our_profile_files_loaded:
        for fname in report.our_profile_files_loaded:
            st.markdown(f"- `{fname}`")
    else:
        st.caption("No profile files loaded.")

    _section_header("Export")
    slug = re.sub(r"[^a-z0-9]+", "_", report.competitor_profile.company_name.lower()).strip("_")
    timestamp = report.generated_at.strftime("%Y%m%d_%H%M%S")

    col_pdf, col_json = st.columns(2)
    with col_pdf:
        try:
            from competitor_intelligence.pdf_exporter import generate_pdf
            pdf_bytes = generate_pdf(report)
            st.download_button(
                label="Download PDF report",
                data=pdf_bytes,
                file_name=f"competitor_{slug}_{timestamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        except Exception as _pdf_err:
            st.error(f"PDF generation failed: {_pdf_err}")
    with col_json:
        st.download_button(
            label="Download JSON report",
            data=report.model_dump_json(indent=2),
            file_name=f"competitor_{slug}_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )


def render_watchlist(watchlist: list[dict], is_researched_fn, company_name: str = "Context Analytics") -> None:
    from collections import defaultdict

    _section_header("Competitor Watchlist")
    st.markdown(
        f"Companies in {company_name}'s space. Click **Research** to generate a full profile, "
        "or **Load** to pull from cache. Use the sidebar to add companies or discover new ones with AI."
    )

    if not watchlist:
        st.markdown(
            '<div class="empty-state">'
            '<p class="empty-state__title">Watchlist is empty</p>'
            '<p class="empty-state__detail">Use the sidebar to add a competitor or click '
            '"Discover more with AI" to get suggestions.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        return

    by_category: dict[str, list[dict]] = defaultdict(list)
    for c in watchlist:
        by_category[c.get("category") or "Other"].append(c)

    for category in sorted(by_category):
        st.markdown(f"**{category}**")
        companies = by_category[category]
        cols = st.columns(3)
        for i, company in enumerate(companies):
            researched = is_researched_fn(company.get("name", ""))
            status_html = (
                '<span style="color:var(--ca-green);font-size:0.75rem;font-weight:600;">✓ Researched</span>'
                if researched else
                '<span style="color:var(--ca-text-muted);font-size:0.75rem;">Not yet researched</span>'
            )
            blurb = (company.get("why_relevant") or "")[:130].rstrip()
            if len(company.get("why_relevant") or "") > 130:
                blurb += "..."
            with cols[i % 3]:
                st.markdown(
                    f'<div class="ca-card" style="min-height:140px;margin-bottom:0.25rem;">'
                    f'<p class="ca-card__title" style="margin-bottom:0.25rem;">{company["name"]}</p>'
                    f'<p class="ca-card__body" style="margin-bottom:0.5rem;">{blurb}</p>'
                    f"{status_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                btn_label = "Load cached" if researched else "Research"
                if st.button(btn_label, key=f"wl_{company['name']}", use_container_width=True):
                    st.session_state.suggest_name = company["name"]
                    st.session_state.suggest_url = company.get("website", "")
                    st.rerun()
        st.markdown("")


def _section_header(title: str) -> None:
    st.markdown(
        f'<div class="section-header"><p class="section-header__title">{title}</p></div>',
        unsafe_allow_html=True,
    )
