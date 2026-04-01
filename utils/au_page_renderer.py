from __future__ import annotations

import pandas as pd
import streamlit as st

from au_phase1_final_load import db_engine
from services.au_dashboard_service import AUDashboardService


@st.cache_resource
def _get_service() -> AUDashboardService:
    return AUDashboardService(db_engine(), school_year="2025")


def _fmt_int(value):
    if value is None:
        return "N/A"
    try:
        return f"{int(value):,}"
    except Exception:
        return str(value)


def _fmt_float(value, digits=2):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return str(value)


def _fmt_pct(value, digits=2):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):,.{digits}f}%"
    except Exception:
        return str(value)


def _summary_cards(summary: dict) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Schools", _fmt_int(summary.get("schools")))
    c2.metric("Students", _fmt_int(summary.get("total_students")))
    c3.metric("Girls", _fmt_int(summary.get("girls_students")))
    c4.metric("Boys", _fmt_int(summary.get("boys_students")))
    c5.metric("Student-Teacher Ratio", _fmt_float(summary.get("student_teacher_ratio"), 2))


def render_au_home() -> None:
    svc = _get_service()
    summary = svc.get_national_summary()
    states = svc.get_state_kpis()

    st.markdown("## 🇦🇺 Australia — National Overview")
    st.caption("ACARA 2025 school profile, location, and enrolment analytics")

    _summary_cards(summary)

    st.markdown("### State KPI Summary")
    state_df = pd.DataFrame(states)
    if not state_df.empty:
        cols = [
            "state_name",
            "state_abbr",
            "schools",
            "total_students",
            "girls_students",
            "boys_students",
            "fte_teaching_staff",
            "student_teacher_ratio",
            "weighted_avg_icsea",
            "weighted_indigenous_pct",
            "weighted_lbote_yes_pct",
        ]
        state_df = state_df[cols]
        st.dataframe(state_df, use_container_width=True, hide_index=True)

        chart_df = state_df[["state_name", "total_students"]].copy().set_index("state_name")
        st.bar_chart(chart_df)
    else:
        st.info("No Australia state KPI data available.")


def render_au_state_dashboard() -> None:
    svc = _get_service()
    states = svc.get_state_kpis()

    st.markdown("## 🇦🇺 Australia — State Dashboard")
    st.caption("State and district performance overview")

    if not states:
        st.warning("No Australia state data available.")
        return

    state_names = [row["state_name"] for row in states]
    default_state = "New South Wales" if "New South Wales" in state_names else state_names[0]

    if "au_selected_state" not in st.session_state:
        st.session_state["au_selected_state"] = default_state

    selected_state = st.selectbox(
        "Select State",
        state_names,
        index=state_names.index(st.session_state.get("au_selected_state", default_state)),
        key="au_state_dashboard_select",
    )
    st.session_state["au_selected_state"] = selected_state

    state_row = next((row for row in states if row["state_name"] == selected_state), {})
    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("State", state_row.get("state_name", "N/A"))
    d2.metric("Schools", _fmt_int(state_row.get("schools")))
    d3.metric("Students", _fmt_int(state_row.get("total_students")))
    d4.metric("FTE Staff", _fmt_float(state_row.get("fte_teaching_staff"), 2))
    d5.metric("STR", _fmt_float(state_row.get("student_teacher_ratio"), 2))

    st.markdown("### District KPIs")
    district_rows = svc.get_district_kpis(selected_state)
    district_df = pd.DataFrame(district_rows)
    if not district_df.empty:
        st.dataframe(district_df, use_container_width=True, hide_index=True)

        if "district_name" in district_df.columns and "total_students" in district_df.columns:
            chart_df = district_df[["district_name", "total_students"]].copy().head(20).set_index("district_name")
            st.bar_chart(chart_df)
    else:
        st.info("No district KPI rows available for this state.")

    st.markdown("### Top Schools")
    school_rows = svc.get_schools(state_name=selected_state, limit=100, offset=0)
    school_df = pd.DataFrame(school_rows)
    if not school_df.empty:
        st.dataframe(school_df, use_container_width=True, hide_index=True)
        st.caption("Schools with missing totals are displayed as N/A in detailed views.")
    else:
        st.info("No school rows available for the selected state.")


def render_au_analytics() -> None:
    svc = _get_service()
    summary = svc.get_national_summary()
    states = svc.get_state_kpis()

    st.markdown("## 🇦🇺 Australia — Analytics")
    st.caption("Comparative state analytics and AU-wide KPI views")

    _summary_cards(summary)

    state_df = pd.DataFrame(states)
    if state_df.empty:
        st.warning("No Australia analytics data available.")
        return

    st.markdown("### Students by State")
    chart1 = state_df[["state_name", "total_students"]].copy().set_index("state_name")
    st.bar_chart(chart1)

    st.markdown("### Schools by State")
    chart2 = state_df[["state_name", "schools"]].copy().set_index("state_name")
    st.bar_chart(chart2)

    st.markdown("### Student-Teacher Ratio by State")
    chart3 = state_df[["state_name", "student_teacher_ratio"]].copy().set_index("state_name")
    st.bar_chart(chart3)

    st.markdown("### State Analytics Table")
    state_df["weighted_indigenous_pct_display"] = state_df["weighted_indigenous_pct"].apply(_fmt_pct)
    state_df["weighted_lbote_yes_pct_display"] = state_df["weighted_lbote_yes_pct"].apply(_fmt_pct)
    st.dataframe(state_df, use_container_width=True, hide_index=True)
