import streamlit as st

# TutorCloud Global Dashboard — Multi-Region
# India: ✅ Live  |  UAE: ✅ Live  |  USA / AUS / NZ: Coming Soon

pages = [
    st.Page("pages/1_🏠_Home.py",            title="Home"),
    st.Page("pages/2_📊_State_Dashboard.py", title="State Dashboard"),
    st.Page("pages/4_📈_Analytics.py",       title="Analytics"),
]

pg = st.navigation(pages)
pg.run()
