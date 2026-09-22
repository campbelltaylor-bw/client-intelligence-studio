from __future__ import annotations

from io import BytesIO

from fpdf import FPDF

from competitor_intelligence.models import CompetitorReport

# ── Colour palette ────────────────────────────────────────────────────────────
_CA_BLUE = (30, 80, 162)
_CA_DARK = (15, 23, 42)
_CA_MUTED = (100, 116, 139)
_CA_LIGHT_BG = (241, 245, 249)
_WHITE = (255, 255, 255)


def _s(text: str) -> str:
    """Sanitize text to latin-1 safe characters for core PDF fonts."""
    if not text:
        return ""
    for src, dst in [
        ("—", "-"), ("–", "-"),
        ("‘", "'"), ("’", "'"),
        ("“", '"'), ("”", '"'),
        ("•", "*"), ("·", "*"),
        ("…", "..."),
        (" ", " "),
    ]:
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _PDF(FPDF):
    _company: str = ""
    _generated: str = ""

    def _pw(self) -> float:
        """Printable width (between margins)."""
        return self.w - self.l_margin - self.r_margin

    def _go_left(self, indent: float = 0) -> None:
        """Reset x to left margin + indent."""
        self.set_x(self.l_margin + indent)

    def header(self) -> None:
        self.set_fill_color(*_CA_BLUE)
        self.rect(0, 0, 210, 10, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_WHITE)
        self.set_y(2)
        self._go_left()
        self.cell(self._pw(), 6, "Context Analytics - Competitor Intelligence", align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*_CA_DARK)
        self.set_y(14)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_CA_MUTED)
        self._go_left()
        self.cell(self._pw() - 20, 5, f"{_s(self._company)} - {self._generated} - For internal use only", align="L")
        self.cell(20, 5, f"Page {self.page_no()}", align="R")

    # ── Layout helpers ────────────────────────────────────────────────────────

    def section_title(self, text: str) -> None:
        self.ln(4)
        self.set_fill_color(*_CA_BLUE)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 10)
        self._go_left()
        self.cell(self._pw(), 7, f"  {_s(text)}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*_CA_DARK)
        self.ln(2)

    def sub_heading(self, text: str) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_CA_BLUE)
        self._go_left()
        self.cell(self._pw(), 5, _s(text), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*_CA_DARK)

    def body(self, text: str, indent: float = 0) -> None:
        self.set_font("Helvetica", "", 9)
        self._go_left(indent)
        self.multi_cell(self._pw() - indent, 5, _s(text))
        self.ln(1)

    def bullet(self, text: str, indent: float = 4) -> None:
        self.set_font("Helvetica", "", 9)
        self._go_left(indent)
        self.multi_cell(self._pw() - indent, 5, f"*  {_s(text)}")

    def kv_row(self, label: str, value: str) -> None:
        label_w = 40
        self._go_left()
        self.set_font("Helvetica", "B", 9)
        self.cell(label_w, 5, _s(label), new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", "", 9)
        self.multi_cell(self._pw() - label_w, 5, _s(value) if value else "-")

    def shaded_box(self, text: str) -> None:
        self.set_fill_color(*_CA_LIGHT_BG)
        self.set_font("Helvetica", "I", 9)
        self._go_left()
        self.multi_cell(self._pw(), 6, _s(text), fill=True, border=0)
        self.ln(2)

    def divider(self) -> None:
        self.set_draw_color(*_CA_MUTED)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)


# ── Public entry point ────────────────────────────────────────────────────────

def generate_pdf(report: CompetitorReport) -> bytes:
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 14, 15)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf._company = report.competitor_profile.company_name
    pdf._generated = report.generated_at.strftime("%b %d, %Y")

    _cover(pdf, report)
    _profile_section(pdf, report)
    _analysis_section(pdf, report)
    battle_card = getattr(report, "battle_card", None)
    if battle_card:
        _battle_card_section(pdf, battle_card, report.competitor_profile.company_name)
    _sources_section(pdf, report)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ── Sections ──────────────────────────────────────────────────────────────────

def _cover(pdf: _PDF, report: CompetitorReport) -> None:
    pdf.add_page()
    p = report.competitor_profile

    pdf.set_fill_color(*_CA_BLUE)
    pdf.rect(0, 10, 210, 50, "F")
    pdf.set_y(22)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*_WHITE)
    pdf._go_left()
    pdf.cell(pdf._pw(), 10, _s(p.company_name), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf._go_left()
    pdf.cell(pdf._pw(), 7, "Competitor Intelligence Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf._go_left()
    pdf.cell(pdf._pw(), 6, f"Generated {report.generated_at.strftime('%B %d, %Y')} - Context Analytics", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_CA_DARK)
    pdf.set_y(70)

    metrics = [
        ("Company Size", p.company_size or "-"),
        ("Founded", p.founded or "-"),
        ("Headquarters", p.headquarters or "-"),
        ("Market Cap", p.market_cap or "-"),
    ]
    box_w = pdf._pw() / len(metrics)
    y0 = pdf.get_y()
    for i, (label, value) in enumerate(metrics):
        x = pdf.l_margin + i * box_w
        pdf.set_fill_color(*_CA_LIGHT_BG)
        pdf.rect(x, y0, box_w - 2, 18, "F")
        pdf.set_xy(x + 1, y0 + 2)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_CA_MUTED)
        pdf.cell(box_w - 4, 4, label.upper())
        pdf.set_xy(x + 1, y0 + 7)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_CA_DARK)
        pdf.multi_cell(box_w - 4, 5, _s(value))
    pdf.set_y(y0 + 22)

    if p.about:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_CA_DARK)
        pdf._go_left()
        pdf.multi_cell(pdf._pw(), 5, _s(p.about))

    if p.website:
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*_CA_MUTED)
        pdf._go_left()
        pdf.cell(pdf._pw(), 5, _s(p.website))
        pdf.set_text_color(*_CA_DARK)


def _profile_section(pdf: _PDF, report: CompetitorReport) -> None:
    pdf.add_page()
    pdf.section_title("Competitor Profile")
    p = report.competitor_profile

    if p.mission_statement:
        pdf.sub_heading("Mission Statement")
        pdf.shaded_box(p.mission_statement)

    if p.additional_locations:
        pdf.sub_heading("Additional Locations")
        pdf.body(", ".join(p.additional_locations))

    if p.products:
        pdf.sub_heading("Products")
        for prod in p.products:
            label = prod.name + (f"  (launched {prod.launched})" if prod.launched else "")
            pdf.set_font("Helvetica", "B", 9)
            pdf._go_left()
            pdf.cell(pdf._pw(), 5, _s(label), new_x="LMARGIN", new_y="NEXT")
            if prod.target_audience:
                pdf.kv_row("  Audience:", prod.target_audience)
            if prod.primary_users:
                pdf.kv_row("  Users:", prod.primary_users)
            if prod.coverage:
                pdf.kv_row("  Coverage:", prod.coverage)
            if prod.deliverable_formats:
                pdf.kv_row("  Formats:", ", ".join(prod.deliverable_formats))
            if prod.use_cases:
                pdf.set_font("Helvetica", "B", 8)
                pdf._go_left(2)
                pdf.cell(pdf._pw() - 2, 5, "  Use Cases:", new_x="LMARGIN", new_y="NEXT")
                for uc in prod.use_cases:
                    pdf.bullet(uc, indent=8)
            pdf.ln(2)

    if p.recent_news:
        pdf.section_title("Recent News")
        for item in p.recent_news:
            pdf.bullet(item)


def _analysis_section(pdf: _PDF, report: CompetitorReport) -> None:
    pdf.add_page()
    pdf.section_title("Competitive Analysis")
    a = report.competitive_analysis

    pdf.sub_heading("Executive Summary")
    pdf.shaded_box(a.executive_summary)

    if a.product_comparisons:
        pdf.sub_heading("Product Comparisons")
        for comp in a.product_comparisons:
            their = comp.their_product or "No equivalent"
            pdf.set_font("Helvetica", "B", 9)
            pdf._go_left()
            pdf.cell(pdf._pw(), 5, _s(f"{comp.our_product}  vs.  {their}"), new_x="LMARGIN", new_y="NEXT")
            pdf.kv_row("  Overlap:", comp.overlap_summary)
            pdf.kv_row("  Differentiator:", comp.differentiator)
            pdf.ln(2)

    pdf.sub_heading("Audience Overlap")
    ao = a.audience_overlap
    col_w3 = pdf._pw() / 3
    y0 = pdf.get_y()
    for i, (hdr, items) in enumerate(zip(
        ["Shared Segments", "Our Exclusive", "Their Exclusive"],
        [ao.shared_segments, ao.our_exclusive_segments, ao.their_exclusive_segments],
    )):
        x = pdf.l_margin + i * col_w3
        pdf.set_xy(x, y0)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w3 - 2, 5, hdr)
        pdf.set_xy(x, y0 + 5)
        pdf.set_font("Helvetica", "", 8)
        for item in (items or ["None identified"]):
            pdf.set_x(x)
            pdf.multi_cell(col_w3 - 2, 4, f"* {_s(item)}")
    pdf.set_y(pdf.get_y() + 4)
    pdf.divider()

    col_w2 = pdf._pw() / 2
    y1 = pdf.get_y()
    for i, (hdr, items) in enumerate([
        ("Our Strengths", a.our_strengths),
        ("Their Strengths", a.their_strengths),
    ]):
        x = pdf.l_margin + i * col_w2
        pdf.set_xy(x, y1)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_w2 - 2, 5, hdr)
        pdf.set_xy(x, y1 + 5)
        pdf.set_font("Helvetica", "", 8)
        for item in (items or ["None identified"]):
            pdf.set_x(x)
            pdf.multi_cell(col_w2 - 2, 4, f"* {_s(item)}")
    pdf.set_y(pdf.get_y() + 4)
    pdf.divider()

    pdf.sub_heading("Coverage Gaps")
    y2 = pdf.get_y()
    for i, (hdr, items) in enumerate([
        ("We cover, they don't", a.gaps.we_cover_they_dont),
        ("They cover, we don't", a.gaps.they_cover_we_dont),
    ]):
        x = pdf.l_margin + i * col_w2
        pdf.set_xy(x, y2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(col_w2 - 2, 5, _s(hdr))
        pdf.set_xy(x, y2 + 5)
        pdf.set_font("Helvetica", "", 8)
        for item in (items or ["None identified"]):
            pdf.set_x(x)
            pdf.multi_cell(col_w2 - 2, 4, f"* {_s(item)}")
    pdf.set_y(pdf.get_y() + 4)


def _battle_card_section(pdf: _PDF, battle_card, company_name: str) -> None:
    pdf.add_page()
    pdf.section_title(f"Battle Card - vs. {company_name}")

    pdf.sub_heading("Positioning Statement")
    pdf.shaded_box(battle_card.positioning_statement)

    if battle_card.top_differentiators:
        pdf.sub_heading("Top Differentiators")
        for i, diff in enumerate(battle_card.top_differentiators, 1):
            pdf._go_left()
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*_CA_BLUE)
            pdf.cell(8, 5, f"{i:02d}", new_x="RIGHT", new_y="TOP")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*_CA_DARK)
            pdf.multi_cell(pdf._pw() - 8, 5, _s(diff))
        pdf.ln(2)

    if battle_card.objection_handlers:
        pdf.sub_heading("Objection Handlers")
        for handler in battle_card.objection_handlers:
            pdf._go_left()
            pdf.set_font("Helvetica", "BI", 9)
            pdf.set_text_color(*_CA_MUTED)
            pdf.multi_cell(pdf._pw(), 5, f'Q: "{_s(handler.objection)}"')
            pdf._go_left(4)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*_CA_DARK)
            pdf.multi_cell(pdf._pw() - 4, 5, f"A: {_s(handler.response)}")
            pdf.ln(2)

    col_w2 = pdf._pw() / 2
    y0 = pdf.get_y()
    for i, (hdr, items, color) in enumerate([
        ("When CA Wins", battle_card.when_ca_wins, _CA_BLUE),
        ("When They Win", battle_card.when_they_win, _CA_MUTED),
    ]):
        x = pdf.l_margin + i * col_w2
        pdf.set_xy(x, y0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*color)
        pdf.cell(col_w2 - 2, 5, hdr)
        pdf.set_text_color(*_CA_DARK)
        pdf.set_xy(x, y0 + 5)
        pdf.set_font("Helvetica", "", 8)
        for item in (items or ["-"]):
            pdf.set_x(x)
            pdf.multi_cell(col_w2 - 2, 4, f"* {_s(item)}")
    pdf.set_y(pdf.get_y() + 4)

    if battle_card.discovery_questions:
        pdf.sub_heading("Discovery Questions")
        for i, q in enumerate(battle_card.discovery_questions, 1):
            pdf._go_left()
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*_CA_BLUE)
            pdf.cell(6, 5, f"{i}.", new_x="RIGHT", new_y="TOP")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*_CA_DARK)
            pdf.multi_cell(pdf._pw() - 6, 5, _s(q))


def _sources_section(pdf: _PDF, report: CompetitorReport) -> None:
    pdf.add_page()
    pdf.section_title("Sources & Metadata")

    pdf.sub_heading("Sources Cited")
    if report.competitor_profile.source_urls:
        for url in report.competitor_profile.source_urls:
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*_CA_BLUE)
            pdf._go_left()
            pdf.multi_cell(pdf._pw(), 4, _s(url))
        pdf.set_text_color(*_CA_DARK)
    else:
        pdf.body("No sources recorded.")

    pdf.ln(4)
    pdf.sub_heading("Our Profile Files Loaded")
    if report.our_profile_files_loaded:
        for fname in report.our_profile_files_loaded:
            pdf.bullet(fname)
    else:
        pdf.body("None.")

    pdf.ln(4)
    pdf.sub_heading("Report Metadata")
    pdf.kv_row("Generated:", report.generated_at.strftime("%Y-%m-%d %H:%M UTC"))
    pdf.kv_row("Model:", report.model_used)
