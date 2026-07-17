import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Client Intelligence Studio",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.components.ui import inject_theme, render_nav_sidebar

inject_theme()

# Session state initialization
if "pipeline_output" not in st.session_state:
    st.session_state.pipeline_output = None
if "pipeline_input" not in st.session_state:
    st.session_state.pipeline_input = None
if "page" not in st.session_state:
    st.session_state.page = "select"

render_nav_sidebar(current_page=st.session_state.page)

# Route to active page
if st.session_state.page == "select":
    from app.views import account_selection
    account_selection.render()
elif st.session_state.page == "report":
    if st.session_state.pipeline_output is None:
        st.warning("No report generated yet. Please select an account first.")
        st.session_state.page = "select"
        st.rerun()
    from app.views import intelligence_report
    intelligence_report.render()
