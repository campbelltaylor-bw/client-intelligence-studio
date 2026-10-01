"""Tests for the UI helper module (app/components/ui.py).

These tests run without a live Streamlit runtime — they only test the
pure-Python helper functions that return HTML strings or read files.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.components.ui import _encode_image, source_label_html, status_badge_html


# ---------------------------------------------------------------------------
# status_badge_html
# ---------------------------------------------------------------------------

class TestStatusBadgeHtml:
    def test_connected_state(self):
        html = status_badge_html("CRM", "connected")
        assert "status-indicator--connected" in html
        assert "CRM" in html

    def test_mock_state(self):
        html = status_badge_html("Mock CRM", "mock")
        assert "status-indicator--mock" in html
        assert "Mock CRM" in html

    def test_disconnected_state(self):
        html = status_badge_html("AI", "disconnected")
        assert "status-indicator--disconnected" in html
        assert "AI" in html

    def test_warning_state(self):
        html = status_badge_html("Research Library", "warning")
        assert "status-indicator--warning" in html
        assert "Research Library" in html

    def test_returns_span_element(self):
        html = status_badge_html("X", "connected")
        assert html.startswith("<span")
        assert html.endswith("</span>")

    def test_label_is_escaped_literally(self):
        html = status_badge_html("Monday.com", "connected")
        assert "Monday.com" in html


# ---------------------------------------------------------------------------
# source_label_html
# ---------------------------------------------------------------------------

class TestSourceLabelHtml:
    def test_crm_fact(self):
        html = source_label_html("CRM_FACT")
        assert "source-badge--crm" in html
        assert "CRM Fact" in html

    def test_public_fact(self):
        html = source_label_html("PUBLIC_FACT")
        assert "source-badge--public" in html
        assert "Public Fact" in html

    def test_ai_inference(self):
        html = source_label_html("AI_INFERENCE")
        assert "source-badge--ai" in html
        assert "AI Inference" in html

    def test_unknown_tag_falls_back(self):
        html = source_label_html("SOMETHING_ELSE")
        assert "source-badge--unknown" in html
        assert "Unknown" in html

    def test_returns_span_element(self):
        html = source_label_html("CRM_FACT")
        assert html.startswith("<span")
        assert html.endswith("</span>")


# ---------------------------------------------------------------------------
# _encode_image
# ---------------------------------------------------------------------------

class TestEncodeImage:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _encode_image(tmp_path / "nonexistent.png")

    def test_existing_file_returns_base64(self, tmp_path):
        img = tmp_path / "logo.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        result = _encode_image(img)
        assert isinstance(result, str)
        assert len(result) > 0
        # Base64 strings contain only alphanumeric + /+=
        import base64
        decoded = base64.b64decode(result)
        assert decoded == img.read_bytes()

    def test_real_logo_encodes(self):
        logo = Path("assets/context_analytics_logo.png")
        if not logo.exists():
            pytest.skip("Logo file not present in test environment.")
        result = _encode_image(logo)
        assert isinstance(result, str)
        assert len(result) > 100  # real image produces non-trivial output


# ---------------------------------------------------------------------------
# source_badge shim (backwards compatibility)
# ---------------------------------------------------------------------------

class TestSourceBadgeShim:
    def test_badge_html_returns_same_as_source_label_html(self):
        from app.components.source_badge import badge_html
        for tag in ("CRM_FACT", "PUBLIC_FACT", "AI_INFERENCE"):
            assert badge_html(tag) == source_label_html(tag)
