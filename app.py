import streamlit as st

st.session_state.pop('_badge_rendered', None)

# TutorCloud Global Dashboard — Multi-Region
# Region routing and readiness are controlled by page-level renderers.

pages = [
    st.Page("pages/1_🏠_Home.py",            title="Home"),
    st.Page("pages/2_📊_State_Dashboard.py", title="State Dashboard"),
    st.Page("pages/4_📈_Analytics.py",       title="Analytics"),
]

pg = st.navigation(pages)
pg.run()
