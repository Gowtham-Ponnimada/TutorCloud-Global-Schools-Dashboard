from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from au_phase1_final_load import db_engine
from services.au_dashboard_service import AUDashboardService

try:
    from ui_components import COLORS
except Exception:
    COLORS = {
        "primary": "#1E88E5",
        "secondary": "#1565C0",
        "success": "#2E7D32",
        "warning": "#F9A825",
        "danger": "#C62828",
        "info": "#00838F",
        "lighter": "#E3F2FD",
        "medium": "#5F6B7A",
    }

THEME = {
    "girls": "#EC4899",
    "boys": "#3B82F6",
    "schools": "#14B8A6",
    "students": COLORS["primary"],
    "ratio": "#F59E0B",
    "icsea": "#8B5CF6",
    "indigenous": "#EF4444",
    "lbote": "#10B981",
    "card_bg": "#FFFFFF",
    "page_bg": "#F5F7FA",
    "border": COLORS["primary"],
}


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


def _inject_india_parity_css() -> None:
    st.markdown(
        f"""
        <style>
        .main {{
            background-color: {THEME['page_bg']};
            padding: 1rem;
        }}

        .block-container {{
            padding-top: 1.2rem;
        }}

        .stMetric {{
            background-color: {THEME['card_bg']};
            border: 3px solid {THEME['border']};
            border-radius: 12px;
            padding: 0.8rem 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        [data-testid="stMetric"] {{
            background-color: {THEME['card_bg']};
            border: 3px solid {THEME['border']};
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        [data-testid="stMetricValue"] {{
            color: {COLORS['primary']};
            font-weight: 700;
        }}

        [data-testid="stMetricLabel"] {{
            color: {COLORS['medium']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }}

        .au-main-header {{
            font-size: 2rem;
            font-weight: 700;
            color: {COLORS['primary']};
            margin-bottom: 0.35rem;
        }}

        .au-sub-header {{
            font-size: 1rem;
            color: {COLORS['medium']};
            margin-bottom: 1.5rem;
        }}

        .au-section-card {{
            background: white;
            border: 3px solid {COLORS['primary']};
            border-radius: 12px;
            padding: 1.25rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}

        .au-section-title {{
            color: {COLORS['primary']};
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }}

        .stDataFrame {{
            border-radius: 12px;
            overflow: hidden;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='au-main-header'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='au-sub-header'>{subtitle}</div>", unsafe_allow_html=True)


def _render_metric_row(summary: dict) -> None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Schools", _fmt_int(summary.get("schools")))
    c2.metric("Total Students", _fmt_int(summary.get("total_students")))
    c3.metric("Girls", _fmt_int(summary.get("girls_students")))
    c4.metric("Boys", _fmt_int(summary.get("boys_students")))
    c5.metric("Student-Teacher Ratio", _fmt_float(summary.get("student_teacher_ratio"), 2))


def _rename_state_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={
        "state_name": "State",
        "state_abbr": "State Code",
        "schools": "Total Schools",
        "total_students": "Total Students",
        "girls_students": "Girls",
        "boys_students": "Boys",
        "fte_teaching_staff": "FTE Teaching Staff",
        "student_teacher_ratio": "Student-Teacher Ratio",
        "weighted_avg_icsea": "Weighted Avg ICSEA",
        "weighted_indigenous_pct": "Weighted Indigenous %",
        "weighted_lbote_yes_pct": "Weighted LBOTE Yes %",
    })


def _rename_district_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={
        "state_name": "State",
        "state_abbr": "State Code",
        "district_id": "District ID",
        "district_name": "District / LGA",
        "schools": "Total Schools",
        "total_students": "Total Students",
        "girls_students": "Girls",
        "boys_students": "Boys",
        "fte_teaching_staff": "FTE Teaching Staff",
        "student_teacher_ratio": "Student-Teacher Ratio",
    })


def _rename_school_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={
        "school_id": "School ID",
        "school_name": "School Name",
        "state_abbr": "State Code",
        "state_name": "State",
        "district_name": "District / LGA",
        "suburb": "Suburb",
        "postcode": "Postcode",
        "management_type": "Management Type",
        "school_level": "School Level",
        "delivery_model": "Delivery Model",
        "total_students": "Total Students",
        "girls_students": "Girls",
        "boys_students": "Boys",
    })


def _rename_grade_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={
        "grade_code": "Grade Code",
        "grade_label": "Grade",
        "grade_sort_order": "Sort Order",
        "enrolled_students": "Enrolled Students",
    })


def _clean_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in out.columns:
        if col.lower() in {"delivery model", "total students", "girls", "boys", "fte teaching staff",
                           "student-teacher ratio", "weighted avg icsea", "weighted indigenous %",
                           "weighted lbote yes %"}:
            out[col] = out[col].where(pd.notnull(out[col]), None)
    return out


def _plot_grouped_students_by_state(state_df: pd.DataFrame) -> None:
    if state_df.empty:
        return

    chart_df = state_df[["State", "Girls", "Boys"]].copy()
    melted = chart_df.melt(id_vars="State", var_name="Legend", value_name="Students")

    fig = px.bar(
        melted,
        x="State",
        y="Students",
        color="Legend",
        barmode="group",
        color_discrete_map={
            "Girls": THEME["girls"],
            "Boys": THEME["boys"],
        },
        title="Student Distribution by State",
    )
    fig.update_layout(
        legend_title_text="Legend",
        xaxis_title="State",
        yaxis_title="Students",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _plot_total_students_by_state(state_df: pd.DataFrame) -> None:
    if state_df.empty:
        return

    fig = px.bar(
        state_df,
        x="State",
        y="Total Students",
        color_discrete_sequence=[THEME["students"]],
        title="Total Students by State",
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title="State",
        yaxis_title="Total Students",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _plot_schools_by_state(state_df: pd.DataFrame) -> None:
    if state_df.empty:
        return

    fig = px.bar(
        state_df,
        x="State",
        y="Total Schools",
        color_discrete_sequence=[THEME["schools"]],
        title="Total Schools by State",
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title="State",
        yaxis_title="Total Schools",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _plot_ratio_by_state(state_df: pd.DataFrame) -> None:
    if state_df.empty:
        return

    fig = px.bar(
        state_df,
        x="State",
        y="Student-Teacher Ratio",
        color_discrete_sequence=[THEME["ratio"]],
        title="Student-Teacher Ratio by State",
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title="State",
        yaxis_title="Student-Teacher Ratio",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def _plot_indigenous_lbote_by_state(state_df: pd.DataFrame) -> None:
    if state_df.empty:
        return

    chart_df = state_df[["State", "Weighted Indigenous %", "Weighted LBOTE Yes %"]].copy()
    melted = chart_df.melt(id_vars="State", var_name="Legend", value_name="Percent")

    fig = px.bar(
        melted,
        x="State",
        y="Percent",
        color="Legend",
        barmode="group",
        color_discrete_map={
            "Weighted Indigenous %": THEME["indigenous"],
            "Weighted LBOTE Yes %": THEME["lbote"],
        },
        title="Weighted Indigenous % vs Weighted LBOTE Yes %",
    )
    fig.update_layout(
        legend_title_text="Legend",
        xaxis_title="State",
        yaxis_title="Percent",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_au_home() -> None:
    _inject_india_parity_css()
    svc = _get_service()

    summary = svc.get_national_summary()
    states = svc.get_state_kpis()

    _render_header(
        "🇦🇺 Australia — National Overview",
        "ACARA 2025 school profile, location, and enrolment analytics",
    )
    _render_metric_row(summary)

    state_df = pd.DataFrame(states)
    state_df = _rename_state_columns(state_df) if not state_df.empty else state_df
    state_df = _clean_display_df(state_df)

    st.markdown("<div class='au-section-card'><div class='au-section-title'>State KPI Summary</div>", unsafe_allow_html=True)
    if not state_df.empty:
        st.dataframe(state_df, use_container_width=True, hide_index=True)
    else:
        st.info("No Australia state KPI data available.")
    st.markdown("</div>", unsafe_allow_html=True)

    if not state_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            _plot_total_students_by_state(state_df)
        with c2:
            _plot_grouped_students_by_state(state_df)


def render_au_state_dashboard() -> None:
    _inject_india_parity_css()
    svc = _get_service()
    states = svc.get_state_kpis()

    _render_header(
        "🇦🇺 Australia — State Dashboard",
        "State, district and school-level drilldown aligned to India dashboard styling",
    )

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

    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("State", state_row.get("state_name", "N/A"))
    s2.metric("Total Schools", _fmt_int(state_row.get("schools")))
    s3.metric("Total Students", _fmt_int(state_row.get("total_students")))
    s4.metric("FTE Teaching Staff", _fmt_float(state_row.get("fte_teaching_staff"), 2))
    s5.metric("Student-Teacher Ratio", _fmt_float(state_row.get("student_teacher_ratio"), 2))

    district_rows = svc.get_district_kpis(selected_state)
    district_df = pd.DataFrame(district_rows)
    district_df = _rename_district_columns(district_df) if not district_df.empty else district_df
    district_df = _clean_display_df(district_df)

    st.markdown("<div class='au-section-card'><div class='au-section-title'>District KPI Summary</div>", unsafe_allow_html=True)
    if not district_df.empty:
        st.dataframe(district_df, use_container_width=True, hide_index=True)
    else:
        st.info("No district KPI rows available for this state.")
    st.markdown("</div>", unsafe_allow_html=True)

    if not district_df.empty and "District / LGA" in district_df.columns and "Total Students" in district_df.columns:
        chart_df = district_df[["District / LGA", "Total Students"]].copy().head(20)
        fig = px.bar(
            chart_df,
            x="District / LGA",
            y="Total Students",
            color_discrete_sequence=[THEME["students"]],
            title=f"Top Districts by Total Students — {selected_state}",
        )
        fig.update_layout(
            showlegend=False,
            xaxis_title="District / LGA",
            yaxis_title="Total Students",
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    school_rows = svc.get_schools(state_name=selected_state, limit=100, offset=0)
    school_df = pd.DataFrame(school_rows)
    school_df = _rename_school_columns(school_df) if not school_df.empty else school_df
    school_df = _clean_display_df(school_df)

    st.markdown("<div class='au-section-card'><div class='au-section-title'>Top Schools</div>", unsafe_allow_html=True)
    if not school_df.empty:
        st.dataframe(school_df, use_container_width=True, hide_index=True)
    else:
        st.info("No school rows available for the selected state.")
    st.markdown("</div>", unsafe_allow_html=True)

    if school_rows:
        options = {
            f'{row["school_name"]} ({row["school_id"]})': row["school_id"]
            for row in school_rows
        }
        selected_school_label = st.selectbox(
            "Select School for Detail",
            ["None"] + list(options.keys()),
            index=0,
            key="au_state_school_detail_select",
        )

        if selected_school_label != "None":
            school_id = options[selected_school_label]
            school = svc.get_school_detail(school_id)
            grades = svc.get_grade_enrollment(school_id)

            st.markdown("<div class='au-section-card'><div class='au-section-title'>School Detail</div>", unsafe_allow_html=True)
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("School Name", school.get("school_name", "N/A"))
            d2.metric("School ID", school.get("school_id", "N/A"))
            d3.metric("Management Type", school.get("management_type", "N/A"))
            d4.metric("School Level", school.get("school_level", "N/A"))

            e1, e2, e3, e4 = st.columns(4)
            e1.metric("State", school.get("state_name", "N/A"))
            e2.metric("District / LGA", school.get("district_name", "N/A"))
            e3.metric("Suburb", school.get("suburb", "N/A"))
            e4.metric("Postcode", school.get("postcode", "N/A"))

            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Total Students", _fmt_int(school.get("total_students")))
            f2.metric("Girls", _fmt_int(school.get("girls_students")))
            f3.metric("Boys", _fmt_int(school.get("boys_students")))
            f4.metric("FTE Teaching Staff", _fmt_float(school.get("fte_teaching_staff"), 2))

            grades_df = pd.DataFrame(grades)
            grades_df = _rename_grade_columns(grades_df) if not grades_df.empty else grades_df
            grades_df = _clean_display_df(grades_df)

            st.markdown("#### Grade Enrollment")
            if not grades_df.empty:
                st.dataframe(grades_df, use_container_width=True, hide_index=True)

                chart_df = grades_df[["Grade", "Enrolled Students"]].copy().fillna(0)
                fig = px.bar(
                    chart_df,
                    x="Grade",
                    y="Enrolled Students",
                    color_discrete_sequence=[THEME["schools"]],
                    title="Grade Enrollment Distribution",
                )
                fig.update_layout(
                    showlegend=False,
                    xaxis_title="Grade",
                    yaxis_title="Enrolled Students",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    margin=dict(l=20, r=20, t=60, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No grade enrollment rows available for this school.")

            st.caption("Schools with missing enrollment totals are displayed as N/A when totals are not reported in source data.")
            st.markdown("</div>", unsafe_allow_html=True)


def render_au_analytics() -> None:
    _inject_india_parity_css()
    svc = _get_service()

    summary = svc.get_national_summary()
    states = svc.get_state_kpis()

    _render_header(
        "🇦🇺 Australia — Analytics",
        "Comparative analytics with India-style KPI cards, legends, charts and grid formatting",
    )
    _render_metric_row(summary)

    state_df = pd.DataFrame(states)
    state_df = _rename_state_columns(state_df) if not state_df.empty else state_df
    state_df = _clean_display_df(state_df)

    if state_df.empty:
        st.warning("No Australia analytics data available.")
        return

    c1, c2 = st.columns(2)
    with c1:
        _plot_total_students_by_state(state_df)
    with c2:
        _plot_schools_by_state(state_df)

    c3, c4 = st.columns(2)
    with c3:
        _plot_ratio_by_state(state_df)
    with c4:
        _plot_indigenous_lbote_by_state(state_df)

    st.markdown("<div class='au-section-card'><div class='au-section-title'>Analytics Grid</div>", unsafe_allow_html=True)
    st.dataframe(state_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
