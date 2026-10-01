"""
Source badge compatibility shim.

The canonical implementation is in app.components.ui.source_label_html().
This module is retained so existing imports of badge_html() continue to work.
"""

import streamlit as st

from app.components.ui import source_label_html
from src.models import SourceTag


def badge_html(tag: SourceTag) -> str:
    """Return an HTML source attribution badge string.

    Delegates to source_label_html() in the central UI module.
    """
    return source_label_html(tag)


def render_badge(tag: SourceTag) -> None:
    """Render a source attribution badge inline via st.markdown()."""
    st.markdown(source_label_html(tag), unsafe_allow_html=True)
