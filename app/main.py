import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

st.set_page_config(
    page_title="Client Intelligence Studio",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.components.ui import inject_theme, render_nav_sidebar

inject_theme()

# Password gate
if not st.session_state.get("authenticated"):
    st.title("Client Intelligence Studio")
    pwd = st.text_input("Password", type="password")
    if st.button("Sign in"):
        import os
        app_password = os.environ.get("APP_PASSWORD")
        if app_password and pwd == app_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()

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
