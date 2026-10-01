#!/usr/bin/env python3
"""
Generate a self-contained HTML QA preview of cached competitor intelligence reports.

Usage (from repo root):
    python competitor_intelligence/export_qa_html.py
"""

import json
from html import escape
from pathlib import Path

BASE = Path(__file__).parent
CSS_PATH = BASE.parent / "app" / "components" / "_theme.css"
OUT_PATH = BASE / "qa_preview.html"

e = escape

REPORTS = [
    {
        "mode": "CA",
        "type": "competitor",
        "file": BASE / "outputs/ca/competitor_alphasense_20260921_160034.json",
    },
    {
        "mode": "CA",
        "type": "competitor",
        "file": BASE / "outputs/ca/competitor_ravenpack_20260921_154537.json",
    },
    {
        "mode": "CA",
        "type": "product",
        "file": BASE / "outputs/ca/market_social_media_analytics_s_factor_20260921_172545.json",
        "label": "Social Media Analytics (S-Factor)",
    },
    {
        "mode": "BW",
        "type": "competitor",
        "file": BASE / "outputs/bridgewise/competitor_danelfin_20260922_155536.json",
    },
    {
        "mode": "BW",
        "type": "product",
        "file": BASE / "outputs/bridgewise/market_ai_equity_ratings_20260922_155204.json",
        "label": "AI Equity Ratings",
    },
]


def section_header(title: str) -> str:
    return f'<div class="section-header"><p class="section-header__title">{e(title)}</p></div>'


def render_list(items: list) -> str:
    if not items:
        return '<p style="color:var(--ca-text-muted);font-size:0.875rem;margin:0.25rem 0;">None identified</p>'
    return "<ul>" + "".join(f"<li>{e(str(item))}</li>" for item in items) + "</ul>"


def render_profile(profile: dict) -> str:
    parts = []

    metrics = [
        ("Company Size", profile.get("company_size") or "Unknown"),
        ("Founded",      profile.get("founded") or "Unknown"),
        ("Headquarters", profile.get("headquarters") or "Unknown"),
        ("Market Cap",   profile.get("market_cap") or "Private / N/A"),
    ]
    parts.append('<div class="metric-grid">' + "".join(
        f'<div class="metric-box"><p class="metric-label">{e(label)}</p>'
        f'<p class="metric-value">{e(str(val))}</p></div>'
        for label, val in metrics
    ) + "</div>")
    parts.append("<hr>")

    if profile.get("about"):
        parts.append(section_header("About"))
        parts.append(f'<p>{e(profile["about"])}</p>')

    if profile.get("mission_statement"):
        parts.append(section_header("Mission Statement"))
        parts.append(f'<blockquote>{e(profile["mission_statement"])}</blockquote>')

    if profile.get("additional_locations"):
        parts.append(section_header("Additional Locations"))
        parts.append(render_list(profile["additional_locations"]))

    products = profile.get("products", [])
    if products:
        parts.append(section_header("Products"))
        for product in products:
            label = e(product.get("name", ""))
            if product.get("launched"):
                label += f' <span style="color:var(--ca-text-muted);font-weight:400;">(launched {e(product["launched"])})</span>'
            inner = []
            if product.get("target_audience"):
                inner.append(f'<p><strong>Target Audience:</strong> {e(product["target_audience"])}</p>')
            if product.get("primary_users"):
                inner.append(f'<p><strong>Primary Users:</strong> {e(product["primary_users"])}</p>')
            if product.get("coverage"):
                inner.append(f'<p><strong>Coverage:</strong> {e(product["coverage"])}</p>')
            if product.get("use_cases"):
                inner.append(f'<p><strong>Use Cases:</strong></p>{render_list(product["use_cases"])}')
            if product.get("deliverable_formats"):
                inner.append(f'<p><strong>Deliverable Formats:</strong> {e(", ".join(product["deliverable_formats"]))}</p>')
            if product.get("source_url"):
                inner.append(f'<p><a href="{e(product["source_url"])}" target="_blank">Source &rarr;</a></p>')
            parts.append(
                f'<details class="expander">'
                f'<summary class="expander__summary">{label}</summary>'
                f'<div class="expander__body">{"".join(inner) or "<p>No details available.</p>"}</div>'
                f'</details>'
            )

    if profile.get("recent_news"):
        parts.append(section_header("Recent News"))
        parts.append(render_list(profile["recent_news"]))

    return "".join(parts)


def render_analysis(analysis: dict, company_short: str) -> str:
    parts = []

    if analysis.get("executive_summary"):
        parts.append(section_header("Executive Summary"))
        parts.append(f'<div class="ca-info-banner">{e(analysis["executive_summary"])}</div>')

    comparisons = analysis.get("product_comparisons", [])
    if comparisons:
        parts.append(section_header("Product Comparison"))
        for comp in comparisons:
            their = e(comp["their_product"]) if comp.get("their_product") else "<em>No equivalent</em>"
            parts.append(
                f'<div class="ca-card">'
                f'<p class="ca-card__label">Our Product vs. Theirs</p>'
                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:0.75rem;">'
                f'<div><strong style="font-size:0.9375rem;">{e(comp.get("our_product",""))}</strong></div>'
                f'<div><strong style="font-size:0.9375rem;">{their}</strong></div>'
                f'</div>'
                f'<p class="ca-card__body"><strong>Overlap:</strong> {e(comp.get("overlap_summary",""))}</p>'
                f'<p class="ca-card__body" style="margin-top:0.375rem;">'
                f'<strong>Differentiator:</strong> {e(comp.get("differentiator",""))}</p>'
                f'</div>'
            )

    ao = analysis.get("audience_overlap", {})
    parts.append(section_header("Audience Overlap"))
    parts.append(
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;">'
        f'<div><strong>Shared Segments</strong>{render_list(ao.get("shared_segments",[]))}</div>'
        f'<div><strong>Our Exclusive Segments</strong>{render_list(ao.get("our_exclusive_segments",[]))}</div>'
        f'<div><strong>Their Exclusive Segments</strong>{render_list(ao.get("their_exclusive_segments",[]))}</div>'
        f'</div>'
    )
    parts.append("<hr>")

    parts.append(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">'
        f'<div>{section_header("Our Strengths")}{render_list(analysis.get("our_strengths",[]))}</div>'
        f'<div>{section_header("Their Strengths")}{render_list(analysis.get("their_strengths",[]))}</div>'
        f'</div>'
    )
    parts.append("<hr>")

    gaps = analysis.get("gaps", {})
    parts.append(section_header("Coverage Gaps"))
    parts.append(
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">'
        f'<div><strong>We cover, they don\'t</strong>{render_list(gaps.get("we_cover_they_dont",[]))}</div>'
        f'<div><strong>They cover, we don\'t</strong>{render_list(gaps.get("they_cover_we_dont",[]))}</div>'
        f'</div>'
    )

    return "".join(parts)


def render_battle_card(bc: dict, company_short: str) -> str:
    parts = []

    parts.append(
        f'<div class="ca-info-banner" style="font-size:1.05rem;font-weight:600;">'
        f'{e(bc.get("positioning_statement",""))}</div>'
    )

    diffs = bc.get("top_differentiators", [])
    if diffs:
        parts.append(section_header("Top Differentiators"))
        cols = "".join(
            f'<div class="ca-card" style="flex:1;min-width:180px;">'
            f'<p class="ca-card__label" style="font-size:1.5rem;font-weight:700;color:var(--ca-accent);margin-bottom:0.5rem;">{i + 1:02d}</p>'
            f'<p class="ca-card__body">{e(diff)}</p></div>'
            for i, diff in enumerate(diffs)
        )
        parts.append(f'<div style="display:flex;gap:0.75rem;flex-wrap:wrap;">{cols}</div>')

    handlers = bc.get("objection_handlers", [])
    if handlers:
        parts.append(section_header("Objection Handlers"))
        for h in handlers:
            parts.append(
                f'<details class="expander">'
                f'<summary class="expander__summary">&ldquo;{e(h.get("objection",""))}&rdquo;</summary>'
                f'<div class="expander__body"><p>{e(h.get("response",""))}</p></div>'
                f'</details>'
            )

    wins = bc.get("when_ca_wins", [])
    loses = bc.get("when_they_win", [])
    if wins or loses:
        parts.append(section_header(f"When {company_short} Wins / When They Win"))
        parts.append(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">'
            f'<div><strong>When {e(company_short)} Wins</strong>{render_list(wins)}</div>'
            f'<div><strong>When They Win</strong>{render_list(loses)}</div>'
            f'</div>'
        )

    questions = bc.get("discovery_questions", [])
    if questions:
        parts.append(section_header("Discovery Questions"))
        for i, q in enumerate(questions, 1):
            parts.append(
                f'<div style="background:var(--ca-bg-raised);border-radius:6px;'
                f'padding:0.6rem 0.9rem;margin-bottom:0.4rem;">'
                f'<strong style="color:var(--ca-accent);">{i}.</strong> {e(q)}</div>'
            )

    return "".join(parts)


def render_sources(report: dict) -> str:
    parts = []

    source_urls = report.get("competitor_profile", {}).get("source_urls", [])
    parts.append(section_header("Sources Cited"))
    if source_urls:
        parts.append("<ul>" + "".join(
            f'<li><a href="{e(url)}" target="_blank">{e(url)}</a></li>'
            for url in source_urls
        ) + "</ul>")
    else:
        parts.append('<p style="color:var(--ca-text-muted);">No sources recorded.</p>')

    files = report.get("our_profile_files_loaded", [])
    parts.append(section_header("Our Profile Files Loaded"))
    if files:
        parts.append("<ul>" + "".join(f'<li><code>{e(f)}</code></li>' for f in files) + "</ul>")
    else:
        parts.append('<p style="color:var(--ca-text-muted);">No profile files loaded.</p>')

    generated = report.get("generated_at", "")
    model = report.get("model_used", "")
    if generated or model:
        parts.append("<hr>")
        if generated:
            parts.append(f'<p style="font-size:0.8125rem;color:var(--ca-text-muted);">Generated: {e(str(generated))}</p>')
        if model:
            parts.append(f'<p style="font-size:0.8125rem;color:var(--ca-text-muted);">Model: <code>{e(model)}</code></p>')

    return "".join(parts)


def render_market_scan(entries: list, label: str) -> str:
    parts = []
    parts.append(
        f'<p style="color:var(--ca-text-secondary);margin-bottom:1.5rem;">'
        f'Product landscape scan for <strong>{e(label)}</strong>. {len(entries)} entries found.</p>'
    )

    if not entries:
        parts.append(
            '<div class="empty-state">'
            '<p class="empty-state__title">No entries found</p>'
            '<p class="empty-state__detail">The scan returned no results.</p>'
            '</div>'
        )
        return "".join(parts)

    cards = []
    for entry in entries:
        website = entry.get("website", "")
        website_html = (
            f'<a href="{e(website)}" target="_blank" style="font-size:0.8125rem;">{e(website)}</a>'
            if website else ""
        )
        product_html = (
            f'<p class="ca-card__label" style="margin-bottom:0.25rem;">{e(entry["product"])}</p>'
            if entry.get("product") else ""
        )
        desc_html = (
            f'<p class="ca-card__body" style="margin-bottom:0.5rem;">{e(entry["description"])}</p>'
            if entry.get("description") else ""
        )
        audience_html = (
            f'<p style="font-size:0.8125rem;color:var(--ca-text-muted);margin-bottom:0.25rem;">'
            f'<strong>Audience:</strong> {e(entry["target_audience"])}</p>'
            if entry.get("target_audience") else ""
        )
        cards.append(
            f'<div class="ca-card">'
            f'<p class="ca-card__title">{e(entry.get("company",""))}</p>'
            f'{product_html}{desc_html}{audience_html}{website_html}'
            f'</div>'
        )

    parts.append(
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;">'
        + "".join(cards) +
        f'</div>'
    )
    return "".join(parts)


def render_competitor_report(data: dict, company_short: str, panel_idx: int) -> str:
    profile = data.get("competitor_profile", {})
    analysis = data.get("competitive_analysis", {})
    bc = data.get("battle_card")

    sections = [
        ("Profile",              render_profile(profile)),
        ("Comparative Analysis", render_analysis(analysis, company_short)),
        ("Battle Card",          render_battle_card(bc, company_short) if bc
                                 else '<p style="color:var(--ca-text-muted);">No battle card generated.</p>'),
        ("Sources",              render_sources(data)),
    ]

    nav = "".join(
        f'<button class="inner-tab" onclick="switchInner(this,\'p{panel_idx}s{j}\')"'
        f'{" data-active" if j == 0 else ""}>{e(title)}</button>'
        for j, (title, _) in enumerate(sections)
    )
    panes = "".join(
        f'<div id="p{panel_idx}s{j}" class="inner-pane{"" if j == 0 else " hidden"}">{content}</div>'
        for j, (_, content) in enumerate(sections)
    )
    return f'<div class="inner-tabs">{nav}</div>{panes}'


def build_html(reports_data: list) -> str:
    css = CSS_PATH.read_text() if CSS_PATH.exists() else ""

    nav_items = []
    panels = []

    for i, (meta, data) in enumerate(reports_data):
        mode = meta["mode"]
        rtype = meta["type"]
        mode_cls = "badge-ca" if mode == "CA" else "badge-bw"
        type_label = "Competitor" if rtype == "competitor" else "Product Scan"
        company_short = "CA" if mode == "CA" else "BW"

        if rtype == "competitor":
            name = data.get("competitor_profile", {}).get("company_name", "Unknown")
            content = render_competitor_report(data, company_short, i)
        else:
            label = meta.get("label", "Product Scan")
            name = label
            raw = data
            entries = raw if isinstance(raw, list) else raw.get("entries", [])
            content = render_market_scan(entries, label)

        nav_items.append(
            f'<button class="tab-btn" onclick="switchTab({i})" id="tab-{i}"'
            f'{" data-active" if i == 0 else ""}>'
            f'{e(name)}'
            f'<span class="badge {mode_cls}">{e(mode)}</span>'
            f'<span class="badge badge-type">{e(type_label)}</span>'
            f'</button>'
        )
        panels.append(
            f'<div id="panel-{i}" class="tab-panel{"" if i == 0 else " hidden"}">{content}</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Competitor Intelligence — QA Preview</title>
<style>
{css}

/* QA Preview layout */
*, *::before, *::after {{ box-sizing: border-box; }}

body {{
  margin: 0;
  padding: 0;
  background: var(--ca-bg-page, #f8fafc);
  font-family: var(--ca-font, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
  color: var(--ca-text-primary, #0f172a);
}}

.page-header {{
  background: var(--ca-bg-surface, #fff);
  border-bottom: 1px solid var(--ca-border, #e2e8f0);
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}}

.page-header h1 {{
  font-size: 1.125rem !important;
  font-weight: 700 !important;
  margin: 0 0 2px !important;
  letter-spacing: -0.01em !important;
}}

.page-header__sub {{
  font-size: 0.8125rem;
  color: var(--ca-text-muted, #94a3b8);
  margin: 0;
}}

.tab-nav {{
  background: var(--ca-bg-surface, #fff);
  border-bottom: 1px solid var(--ca-border, #e2e8f0);
  padding: 0 2rem;
  display: flex;
  gap: 0;
  overflow-x: auto;
  position: sticky;
  top: 0;
  z-index: 10;
}}

.tab-btn {{
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0.75rem 1rem;
  font-family: inherit;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--ca-text-secondary, #475569);
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  transition: color 0.15s, border-color 0.15s;
  line-height: 1;
}}

.tab-btn:hover {{ color: var(--ca-text-primary, #0f172a); }}

.tab-btn[data-active] {{
  color: var(--ca-accent, #2563eb);
  border-bottom-color: var(--ca-accent, #2563eb);
  font-weight: 600;
}}

.tab-panel {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 2rem 2.5rem 4rem;
}}

.tab-panel.hidden {{ display: none; }}

.badge {{
  font-size: 0.5625rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 2px 5px;
  border-radius: 3px;
  border: 1px solid;
  line-height: 1;
}}

.badge-ca {{
  color: #1e40af;
  background: #eff6ff;
  border-color: #bfdbfe;
}}

.badge-bw {{
  color: #166534;
  background: #f0fdf4;
  border-color: #bbf7d0;
}}

.badge-type {{
  color: var(--ca-text-muted, #94a3b8);
  background: var(--ca-bg-raised, #f1f5f9);
  border-color: var(--ca-border, #e2e8f0);
}}

/* Inner section tabs */
.inner-tabs {{
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--ca-border, #e2e8f0);
  margin-bottom: 1.75rem;
}}

.inner-tab {{
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  padding: 0.5rem 0.875rem;
  font-family: inherit;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--ca-text-secondary, #475569);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}}

.inner-tab:hover {{ color: var(--ca-text-primary, #0f172a); }}

.inner-tab[data-active] {{
  color: var(--ca-accent, #2563eb);
  border-bottom-color: var(--ca-accent, #2563eb);
  font-weight: 600;
}}

.inner-pane.hidden {{ display: none; }}

/* Metrics */
.metric-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-bottom: 1.25rem;
}}

.metric-box {{
  background: var(--ca-bg-surface, #fff);
  border: 1px solid var(--ca-border, #e2e8f0);
  border-radius: var(--ca-radius-lg, 10px);
  padding: 0.875rem 1.125rem;
  box-shadow: var(--ca-shadow, 0 1px 3px rgba(15,23,42,0.08));
}}

.metric-label {{
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--ca-text-secondary, #475569);
  margin: 0 0 0.25rem;
}}

.metric-value {{
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--ca-text-primary, #0f172a);
  margin: 0;
  letter-spacing: -0.02em;
}}

/* Expanders */
.expander {{
  border: 1px solid var(--ca-border, #e2e8f0);
  border-radius: var(--ca-radius, 6px);
  background: var(--ca-bg-surface, #fff);
  margin-bottom: 0.5rem;
  box-shadow: var(--ca-shadow, 0 1px 3px rgba(15,23,42,0.08));
  overflow: hidden;
}}

.expander__summary {{
  padding: 0.75rem 1rem;
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  color: var(--ca-text-primary, #0f172a);
  list-style: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  user-select: none;
}}

.expander__summary::-webkit-details-marker {{ display: none; }}

.expander__summary::before {{
  content: "›";
  font-size: 1.25rem;
  color: var(--ca-text-muted, #94a3b8);
  transition: transform 0.15s;
  flex-shrink: 0;
}}

details[open] > .expander__summary::before {{ transform: rotate(90deg); }}

.expander__body {{
  padding: 0.75rem 1rem 1rem;
  border-top: 1px solid var(--ca-border, #e2e8f0);
  font-size: 0.875rem;
  color: var(--ca-text-secondary, #475569);
  line-height: 1.6;
}}

.expander__body p {{ margin: 0.25rem 0; }}
.expander__body ul {{ margin: 0.25rem 0; padding-left: 1.5rem; }}

blockquote {{
  border-left: 3px solid var(--ca-accent, #2563eb);
  margin: 0.5rem 0 1rem;
  padding: 0.5rem 1rem;
  color: var(--ca-text-secondary, #475569);
  font-style: italic;
  background: var(--ca-accent-subtle, #eff6ff);
  border-radius: 0 var(--ca-radius, 6px) var(--ca-radius, 6px) 0;
}}

ul {{ padding-left: 1.5rem; margin: 0.5rem 0; }}
li {{ margin-bottom: 0.25rem; font-size: 0.9375rem; line-height: 1.6; color: var(--ca-text-primary, #0f172a); }}

p {{ margin: 0 0 0.75rem; line-height: 1.65; font-size: 0.9375rem; }}

code {{
  font-family: var(--ca-font-mono, monospace);
  font-size: 0.8125rem;
  background: var(--ca-bg-raised, #f1f5f9);
  padding: 1px 4px;
  border-radius: 3px;
  color: var(--ca-text-secondary, #475569);
}}

a {{ color: var(--ca-accent, #2563eb); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

hr {{
  border: none;
  border-top: 1px solid var(--ca-border, #e2e8f0);
  margin: 1.25rem 0;
}}

strong {{ color: var(--ca-text-primary, #0f172a); }}
</style>
</head>
<body>

<div class="page-header">
  <div>
    <h1>Competitor Intelligence — QA Preview</h1>
    <p class="page-header__sub">5 cached examples &middot; CA and Bridgewise modes &middot; Internal review only</p>
  </div>
  <span class="ca-internal-banner" style="margin:0;flex-shrink:0;">Internal &amp; Confidential</span>
</div>

<nav class="tab-nav">{"".join(nav_items)}</nav>

{"".join(panels)}

<script>
function switchTab(idx) {{
  document.querySelectorAll('.tab-btn').forEach(function(b, i) {{
    if (i === idx) b.setAttribute('data-active', '');
    else b.removeAttribute('data-active');
  }});
  document.querySelectorAll('.tab-panel').forEach(function(p, i) {{
    if (i === idx) p.classList.remove('hidden');
    else p.classList.add('hidden');
  }});
}}

function switchInner(btn, paneId) {{
  var panel = btn.closest('.tab-panel');
  panel.querySelectorAll('.inner-tab').forEach(function(b) {{
    b.removeAttribute('data-active');
  }});
  btn.setAttribute('data-active', '');
  panel.querySelectorAll('.inner-pane').forEach(function(p) {{
    p.classList.add('hidden');
  }});
  document.getElementById(paneId).classList.remove('hidden');
}}
</script>

</body>
</html>"""


def main() -> None:
    reports_data = []
    for meta in REPORTS:
        path = meta["file"]
        if not path.exists():
            print(f"WARNING: {path} not found — skipping")
            continue
        data = json.loads(path.read_text())
        reports_data.append((meta, data))

    if not reports_data:
        print("No reports found. Exiting.")
        return

    html = build_html(reports_data)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Written: {OUT_PATH}")
    print(f"  {len(reports_data)} reports included")
    print(f"  {len(html):,} bytes")


if __name__ == "__main__":
    main()
