import streamlit as st

from app.components.ui import empty_state, section_header, source_label_html
from src.models import (
    BlogRecommendation,
    InternalBrief,
    OutreachEmail,
    ProductRecommendation,
    TaggedFact,
    WebResearchResult,
)


def render_tagged_fact(fact: TaggedFact) -> None:
    evidence_html = (
        f'<span class="ca-fact-row__evidence">Evidence: {fact.evidence}</span>'
        if fact.evidence
        else ""
    )
    st.markdown(
        f'<div class="ca-fact-row">'
        f"{source_label_html(fact.source)}"
        f'<div style="flex:1;">'
        f'<span class="ca-fact-row__value">{fact.value}</span>'
        f"{evidence_html}"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_product_recommendations(products: list[ProductRecommendation]) -> None:
    section_header("Product Recommendations")
    if not products:
        empty_state(
            "No product recommendations",
            "No matching products were found for this account profile.",
        )
        return
    for i, rec in enumerate(products, 1):
        score_pct = int(rec.relevance_score * 100)
        with st.expander(f"{i}. {rec.product_name}", expanded=False):
            st.markdown(
                f'<div class="ca-relevance-wrap">'
                f'<span class="ca-relevance-label">Relevance</span>'
                f'<div class="ca-relevance-track">'
                f'<div class="ca-relevance-fill" style="width:{score_pct}%"></div>'
                f"</div>"
                f'<span class="ca-relevance-pct">{score_pct}%</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Use Case:** {rec.use_case}")
            st.markdown(f"**Rationale:** {rec.reason}")


def render_internal_brief(brief: InternalBrief) -> None:
    st.markdown(
        '<div class="ca-internal-banner">INTERNAL ONLY — Do not share with clients</div>',
        unsafe_allow_html=True,
    )

    section_header("Account Summary")
    st.markdown(brief.account_summary)

    if brief.crm_highlights:
        section_header("CRM Highlights")
        for fact in brief.crm_highlights:
            render_tagged_fact(fact)

    if brief.key_opportunities:
        section_header("Key Opportunities")
        for fact in brief.key_opportunities:
            render_tagged_fact(fact)

    if brief.risks_and_gaps:
        section_header("Risks and Gaps")
        for risk in brief.risks_and_gaps:
            st.markdown(f"- {risk}")


def render_web_research(web: WebResearchResult) -> None:
    section_header("Company Overview")
    if web.company_description:
        render_tagged_fact(web.company_description)
    else:
        empty_state("No company description", "No public description was retrieved for this account.")

    if web.recent_news:
        section_header("Recent News")
        for n in web.recent_news:
            render_tagged_fact(n)

    if web.technology_signals:
        section_header("Technology Signals")
        for s in web.technology_signals:
            render_tagged_fact(s)

    if web.source_urls:
        section_header("Sources")
        for url in web.source_urls:
            st.markdown(f"- {url}")


def render_blog_recommendations(
    blogs: list[BlogRecommendation],
    catalog: list[dict] | None = None,
) -> None:
    section_header("Blog Recommendations")
    if not blogs:
        empty_state(
            "No blog recommendations",
            "No matching research content was found for this account.",
        )
        return

    # Build a URL -> metadata lookup from the full catalog when available.
    meta_by_url: dict[str, dict] = {}
    if catalog:
        for entry in catalog:
            url = entry.get("Link to Blog", "").strip()
            if url:
                meta_by_url[url] = entry

    for blog in blogs:
        score_pct = int(blog.relevance_score * 100)
        with st.expander(blog.title, expanded=False):
            st.markdown(
                f'<div class="ca-relevance-wrap">'
                f'<span class="ca-relevance-label">Relevance</span>'
                f'<div class="ca-relevance-track">'
                f'<div class="ca-relevance-fill" style="width:{score_pct}%"></div>'
                f"</div>"
                f'<span class="ca-relevance-pct">{score_pct}%</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Why relevant:** {blog.reason}")
            st.markdown(f"[Read post]({blog.url})")

            meta = meta_by_url.get(blog.url, {})
            meta_items: list[str] = []
            if meta.get("Blog Category"):
                meta_items.append(f"**Category:** {meta['Blog Category']}")
            if meta.get("Data Source"):
                meta_items.append(f"**Data Source:** {meta['Data Source']}")
            if meta.get("Application"):
                meta_items.append(f"**Application:** {meta['Application']}")
            if meta.get("Asset Class"):
                meta_items.append(f"**Asset Class:** {meta['Asset Class']}")
            if meta.get("Post Date"):
                meta_items.append(f"**Published:** {meta['Post Date']}")
            if meta_items:
                st.markdown("  \n".join(meta_items))


def render_outreach_emails(
    emails: list[OutreachEmail],
    fallback_email: str = "",
) -> None:
    """Render audience-specific outreach email variants.

    Shows one tab per audience when ``emails`` is non-empty.
    Falls back to a single editable text area when it is empty.
    """
    section_header("Outreach Emails", "Review and personalize before use. No automatic email delivery.")
    st.markdown(
        '<div class="ca-info-banner">'
        "These drafts are generated from public research only. "
        "Review, edit, and personalize before sending."
        "</div>",
        unsafe_allow_html=True,
    )

    if not emails:
        st.text_area(
            label="Email content",
            value=fallback_email,
            height=340,
            key="outreach_email_fallback",
            label_visibility="collapsed",
        )
        return

    tab_labels = [e.audience for e in emails]
    tabs = st.tabs(tab_labels)
    for tab, email in zip(tabs, emails):
        with tab:
            st.markdown(
                f'<p style="font-size:0.75rem;font-weight:600;color:#475569;'
                f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.25rem;">'
                f"Subject</p>"
                f'<p style="font-size:0.9375rem;font-weight:600;color:#0f172a;'
                f'margin:0 0 1rem;">{email.subject}</p>',
                unsafe_allow_html=True,
            )
            st.text_area(
                label="Email body",
                value=email.body,
                height=320,
                key=f"email_{email.audience.lower().replace(' ', '_')}",
                label_visibility="collapsed",
            )


def render_meeting_prep(brief: str) -> None:
    section_header("Meeting Preparation Brief")
    st.markdown(brief)
