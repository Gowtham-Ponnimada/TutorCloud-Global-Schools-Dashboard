#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
TARGET = ROOT / 'utils' / 'us_page_renderer.py'

RENDERER = r'''from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

US_REGION = "United States"
DASHBOARD_YEAR = "2024-2025"
SCHEMA = "us"

US_COLORS = {
    "blue": "#1F4E79",
    "teal": "#0F766E",
    "green": "#2E7D32",
    "gold": "#D97706",
    "red": "#B42318",
    "gray": "#667085",
    "border": "#D0D5DD",
    "light": "#EFF6FF",
}


def _load_db_config():
    cfg = {
        "host": os.getenv("DB_HOST", "localhost"),
        "dbname": os.getenv("DB_NAME", os.getenv("DB_DATABASE", "tutorcloud_db")),
        "user": os.getenv("DB_USER", "tutorcloud_admin"),
        "password": os.getenv("DB_PASSWORD", ""),
        "port": int(os.getenv("DB_PORT", "5432")),
    }
    try:
        from utils.uae_page_renderer import _DB_PARAMS  # type: ignore
        if isinstance(_DB_PARAMS, dict):
            for k, v in _DB_PARAMS.items():
                if k in ("host", "dbname", "user", "password", "port") and v not in (None, ""):
                    cfg[k] = v
    except Exception:
        pass
    return cfg


DB_CONFIG = _load_db_config()


def _q(sql: str, params=None) -> pd.DataFrame:
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            return pd.read_sql_query(sql, conn, params=params)
    except Exception:
        return pd.DataFrame()


def _scalar(sql: str, params=None, default=0):
    df = _q(sql, params)
    if df.empty:
        return default
    try:
        return df.iloc[0, 0]
    except Exception:
        return default


def _fmt_int(v) -> str:
    try:
        if v is None or pd.isna(v):
            return "0"
        return f"{int(round(float(v))):,}"
    except Exception:
        return "0"


def _fmt_float(v, digits: int = 2) -> str:
    try:
        if v is None or pd.isna(v):
            return "—"
        return f"{float(v):,.{digits}f}"
    except Exception:
        return "—"


def _fmt_ptr(v) -> str:
    try:
        if v is None or pd.isna(v) or float(v) <= 0:
            return "N/A"
        return f"{int(round(float(v)))}:1"
    except Exception:
        return "N/A"


def _inject_css():
    st.markdown(
        f"""
        <style>
            .us-title {{ font-size: 1.6rem; font-weight: 700; margin-bottom: .25rem; }}
            .us-subtitle {{ color: {US_COLORS['gray']}; margin-bottom: 1rem; }}
            .us-note {{
                background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px;
                padding:.85rem 1rem; margin:.5rem 0 1rem 0;
            }}
            .us-card {{
                background:white; border:1px solid {US_COLORS['border']}; border-left:4px solid {US_COLORS['blue']};
                border-radius:12px; padding:1rem; box-shadow:0 2px 8px rgba(0,0,0,.04); margin-bottom:.75rem;
            }}
            [data-testid="stMetric"] {{
                background:white; border:1px solid {US_COLORS['border']}; border-left:4px solid {US_COLORS['blue']};
                border-radius:12px; padding:.65rem .85rem; box-shadow:0 2px 8px rgba(0,0,0,.04);
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _phase1_ready() -> bool:
    sql = f"""
    SELECT
        COALESCE((SELECT COUNT(*) FROM {SCHEMA}.dim_states WHERE school_year = %s), 0) AS states,
        COALESCE((SELECT COUNT(*) FROM {SCHEMA}.dim_districts WHERE school_year = %s), 0) AS districts,
        COALESCE((SELECT COUNT(*) FROM {SCHEMA}.dim_schools WHERE school_year = %s), 0) AS schools
    """
    df = _q(sql, [DASHBOARD_YEAR, DASHBOARD_YEAR, DASHBOARD_YEAR])
    if df.empty:
        return False
    row = df.iloc[0].fillna(0)
    return int(row.get("states", 0)) > 0 and int(row.get("districts", 0)) > 0 and int(row.get("schools", 0)) > 0


def _render_missing_data_notice():
    st.error("US 2024–2025 NCES marts are not available yet. Run the Final 1a loader before using the US dashboard.")
    st.code(
        """cd /home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard
python3 us_phase1_final_1a_load.py
python3 us_real_data_renderer_patch_v1.py
python3 -m py_compile utils/us_page_renderer.py
pkill -f 'streamlit run' || true
sleep 3
nohup venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &
"""
    )


def _distinct_values(sql: str, params=None, col: str | None = None) -> list[str]:
    df = _q(sql, params)
    if df.empty:
        return []
    use_col = col or df.columns[0]
    vals = []
    for v in df[use_col].tolist():
        if v is None or str(v).strip() in ("", "None", "nan"):
            continue
        vals.append(str(v))
    return vals


def _states() -> list[str]:
    return _distinct_values(
        f"SELECT DISTINCT state_name FROM {SCHEMA}.dim_states WHERE school_year = %s AND state_name IS NOT NULL ORDER BY state_name",
        [DASHBOARD_YEAR],
        "state_name",
    )


def _districts(state_name: str = "All") -> list[str]:
    if state_name and state_name != "All":
        return _distinct_values(
            f"SELECT DISTINCT district_name FROM {SCHEMA}.dim_districts WHERE school_year = %s AND state_name = %s AND district_name IS NOT NULL ORDER BY district_name",
            [DASHBOARD_YEAR, state_name],
            "district_name",
        )
    return _distinct_values(
        f"SELECT DISTINCT district_name FROM {SCHEMA}.dim_districts WHERE school_year = %s AND district_name IS NOT NULL ORDER BY district_name",
        [DASHBOARD_YEAR],
        "district_name",
    )


def _school_levels(state_name: str = "All") -> list[str]:
    if state_name and state_name != "All":
        return _distinct_values(
            f"SELECT DISTINCT school_level FROM {SCHEMA}.dim_schools WHERE school_year = %s AND state_name = %s AND school_level IS NOT NULL ORDER BY school_level",
            [DASHBOARD_YEAR, state_name],
            "school_level",
        )
    return _distinct_values(
        f"SELECT DISTINCT school_level FROM {SCHEMA}.dim_schools WHERE school_year = %s AND school_level IS NOT NULL ORDER BY school_level",
        [DASHBOARD_YEAR],
        "school_level",
    )


def _build_sidebar_filters() -> dict:
    with st.sidebar:
        st.markdown("## 🇺🇸 US Filters")
        st.caption("NCES CCD Final v1a · 2024–2025 only")
        state_opts = ["All"] + _states()
        state = st.selectbox("State", state_opts, index=0, key="us_state")
        district_opts = _districts(state)
        districts = st.multiselect("District", district_opts, key="us_districts")
        level_opts = _school_levels(state)
        school_levels = st.multiselect("School Level", level_opts, key="us_levels")
        charter = st.selectbox("Charter", ["All", "Yes", "No"], index=0, key="us_charter")
        virtual = st.selectbox("Virtual", ["All"] + _distinct_values(
            f"SELECT DISTINCT virtual_text FROM {SCHEMA}.dim_schools WHERE school_year = %s AND virtual_text IS NOT NULL ORDER BY virtual_text",
            [DASHBOARD_YEAR],
            "virtual_text",
        ), index=0, key="us_virtual")
        return {
            "state": state,
            "districts": districts,
            "school_levels": school_levels,
            "charter": charter,
            "virtual": virtual,
        }


def _base_where(filters: dict | None = None, alias: str = "ds"):
    filters = filters or {}
    clauses = [f"{alias}.school_year = %s"]
    params: list = [DASHBOARD_YEAR]
    if filters.get("state") and filters["state"] != "All":
        clauses.append(f"{alias}.state_name = %s")
        params.append(filters["state"])
    districts = [x for x in (filters.get("districts") or []) if x]
    if districts:
        clauses.append(f"{alias}.district_name = ANY(%s)")
        params.append(districts)
    levels = [x for x in (filters.get("school_levels") or []) if x]
    if levels:
        clauses.append(f"{alias}.school_level = ANY(%s)")
        params.append(levels)
    charter = filters.get("charter")
    if charter and charter != "All":
        clauses.append(f"COALESCE({alias}.charter_text, 'No') = %s")
        params.append(charter)
    virtual = filters.get("virtual")
    if virtual and virtual != "All":
        clauses.append(f"COALESCE({alias}.virtual_text, 'Not reported') = %s")
        params.append(virtual)
    return " WHERE " + " AND ".join(clauses), params


def _export_buttons(df: pd.DataFrame, prefix: str):
    if df is None or df.empty:
        return
    csv_data = df.to_csv(index=False).encode("utf-8")
    with io.BytesIO() as bio:
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="data")
        xlsx_data = bio.getvalue()
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Export CSV", csv_data, f"{prefix}.csv", "text/csv", use_container_width=True)
    with c2:
        st.download_button(
            "⬇️ Export Excel",
            xlsx_data,
            f"{prefix}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def _plot_bar(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v", color: str | None = None):
    if df is None or df.empty:
        st.info(f"No data available for {title}.")
        return
    fig = px.bar(
        df,
        x=x if orientation == "v" else y,
        y=y if orientation == "v" else x,
        orientation=orientation,
        color=color,
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=55, b=10),
        font=dict(family="Segoe UI"),
        legend_title_text="",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _national_summary() -> dict:
    sql = f"""
    SELECT
        COUNT(*) AS total_states,
        COALESCE(SUM(school_count), 0) AS total_schools,
        COALESCE(SUM(district_count), 0) AS total_districts,
        COALESCE(SUM(total_students), 0) AS total_students,
        COALESCE(SUM(total_teachers), 0) AS total_teachers,
        CASE WHEN COALESCE(SUM(total_teachers), 0) > 0 THEN ROUND(SUM(total_students) / SUM(total_teachers), 2) END AS ptr,
        CASE WHEN COALESCE(SUM(school_count), 0) > 0 THEN ROUND(SUM(total_students) / SUM(school_count), 2) END AS students_per_school
    FROM {SCHEMA}.dim_states
    WHERE school_year = %s
    """
    df = _q(sql, [DASHBOARD_YEAR])
    if df.empty:
        return {
            "total_states": 0,
            "total_schools": 0,
            "total_districts": 0,
            "total_students": 0,
            "total_teachers": 0,
            "ptr": None,
            "students_per_school": None,
        }
    return df.iloc[0].to_dict()


def _top_states_by_schools(limit: int = 10) -> pd.DataFrame:
    return _q(
        f"SELECT state_name, total_schools FROM {SCHEMA}.vw_state_kpis_2024_2025 WHERE school_year = %s ORDER BY total_schools DESC NULLS LAST, state_name LIMIT %s",
        [DASHBOARD_YEAR, limit],
    )


def _top_states_by_students(limit: int = 20) -> pd.DataFrame:
    return _q(
        f"SELECT state_name, total_students FROM {SCHEMA}.vw_state_kpis_2024_2025 WHERE school_year = %s AND total_students IS NOT NULL ORDER BY total_students DESC NULLS LAST, state_name LIMIT %s",
        [DASHBOARD_YEAR, limit],
    )


def _school_level_mix(filters: dict | None = None) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    return _q(
        f"SELECT COALESCE(ds.school_level, 'Unknown') AS school_level, COUNT(DISTINCT ds.school_id) AS school_count FROM {SCHEMA}.dim_schools ds {where} GROUP BY 1 ORDER BY school_count DESC, school_level",
        params,
    )


def _state_dashboard_kpis(filters: dict) -> dict:
    where, params = _base_where(filters, "ds")
    sql = f"""
    SELECT
        COUNT(DISTINCT ds.school_id) AS total_schools,
        COUNT(DISTINCT CASE WHEN f.total_students IS NOT NULL THEN ds.school_id END) AS schools_with_enrollment,
        COUNT(DISTINCT ds.district_id) AS total_districts,
        COALESCE(SUM(f.total_students), 0) AS total_students,
        COALESCE(SUM(f.total_teachers), 0) AS total_teachers,
        CASE WHEN COALESCE(SUM(f.total_teachers), 0) > 0 THEN ROUND(SUM(f.total_students) / SUM(f.total_teachers), 2) END AS ptr
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    {where}
    """
    df = _q(sql, params)
    if df.empty:
        return {
            "total_schools": 0,
            "schools_with_enrollment": 0,
            "total_districts": 0,
            "total_students": 0,
            "total_teachers": 0,
            "ptr": None,
        }
    return df.iloc[0].to_dict()


def _grade_enrollment(filters: dict) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    sql = f"""
    SELECT
        g.grade,
        SUM(g.student_count) AS total_students
    FROM {SCHEMA}.fact_grade_gender_enrollment g
    JOIN {SCHEMA}.dim_schools ds
      ON ds.school_id = g.school_id AND ds.school_year = g.school_year
    {where}
      AND g.total_indicator = 'Education Unit Total'
    GROUP BY g.grade
    ORDER BY
      CASE
        WHEN g.grade IN ('PK','UG','AE') THEN 0
        WHEN g.grade = 'KG' THEN 1
        WHEN g.grade ~ '^[0-9]+$' THEN 2
        ELSE 3
      END,
      CASE WHEN g.grade ~ '^[0-9]+$' THEN g.grade::int ELSE 999 END,
      g.grade
    """
    return _q(sql, params)


def _district_kpi_table(filters: dict, limit: int = 50) -> pd.DataFrame:
    params: list = [DASHBOARD_YEAR]
    clauses = ["school_year = %s"]
    if filters.get("state") and filters["state"] != "All":
        clauses.append("state_name = %s")
        params.append(filters["state"])
    sql = f"""
    SELECT district_name, total_schools, schools_with_enrollment, total_students, total_teachers, ptr,
           free_lunch_qualified, reduced_price_qualified, direct_certification
    FROM {SCHEMA}.vw_district_kpis_2024_2025
    WHERE {' AND '.join(clauses)}
    ORDER BY total_schools DESC NULLS LAST, district_name
    LIMIT %s
    """
    params.append(limit)
    return _q(sql, params)


def _schools_by_city(filters: dict, limit: int = 20) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    params = params + [limit]
    return _q(
        f"SELECT COALESCE(ds.city, 'Unknown') AS city, COUNT(DISTINCT ds.school_id) AS school_count FROM {SCHEMA}.dim_schools ds {where} GROUP BY 1 ORDER BY school_count DESC, city LIMIT %s",
        params,
    )


def _directory_table(filters: dict, limit: int = 1000) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    params = params + [limit]
    sql = f"""
    SELECT
        ds.school_name,
        ds.district_name,
        ds.state_name,
        ds.city,
        ds.school_level,
        ds.low_grade,
        ds.high_grade,
        ds.charter_text,
        ds.virtual_text,
        f.total_students,
        f.total_teachers,
        f.ptr,
        f.free_lunch_qualified,
        f.reduced_price_qualified
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    {where}
    ORDER BY ds.state_name, ds.district_name, ds.school_name
    LIMIT %s
    """
    return _q(sql, params)


def _state_metric_frame() -> pd.DataFrame:
    return _q(
        f"""
        SELECT state_name, total_schools, total_districts, total_students, total_teachers, ptr,
               free_lunch_qualified, reduced_price_qualified, direct_certification, schools_with_enrollment
        FROM {SCHEMA}.vw_state_kpis_2024_2025
        WHERE school_year = %s
        ORDER BY state_name
        """,
        [DASHBOARD_YEAR],
    )


def _comparison_frame(left_state: str, right_state: str) -> pd.DataFrame:
    return _q(
        f"""
        SELECT state_name, total_schools, total_districts, total_students, total_teachers, ptr,
               schools_with_enrollment, free_lunch_qualified, reduced_price_qualified, direct_certification
        FROM {SCHEMA}.vw_state_kpis_2024_2025
        WHERE school_year = %s AND state_name = ANY(%s)
        ORDER BY state_name
        """,
        [DASHBOARD_YEAR, [left_state, right_state]],
    )


def _district_comparison_frame(left_state: str, left_district: str, right_state: str, right_district: str) -> pd.DataFrame:
    return _q(
        f"""
        SELECT state_name, district_name, total_schools, total_students, total_teachers, ptr,
               schools_with_enrollment, free_lunch_qualified, reduced_price_qualified, direct_certification
        FROM {SCHEMA}.vw_district_kpis_2024_2025
        WHERE school_year = %s
          AND ((state_name = %s AND district_name = %s) OR (state_name = %s AND district_name = %s))
        ORDER BY state_name, district_name
        """,
        [DASHBOARD_YEAR, left_state, left_district, right_state, right_district],
    )


def _custom_report(dimensions: list[str], metrics: list[str], filters: dict) -> pd.DataFrame:
    dim_map = {
        "State": ("ds.state_name", "state_name"),
        "District": ("ds.district_name", "district_name"),
        "City": ("ds.city", "city"),
        "School Level": ("ds.school_level", "school_level"),
        "Charter": ("ds.charter_text", "charter_text"),
        "Virtual": ("ds.virtual_text", "virtual_text"),
    }
    metric_map = {
        "Schools": "COUNT(DISTINCT ds.school_id) AS total_schools",
        "Schools with Enrollment": "COUNT(DISTINCT CASE WHEN f.total_students IS NOT NULL THEN ds.school_id END) AS schools_with_enrollment",
        "Students": "COALESCE(SUM(f.total_students), 0) AS total_students",
        "Teachers": "COALESCE(SUM(f.total_teachers), 0) AS total_teachers",
        "PTR": "CASE WHEN COALESCE(SUM(f.total_teachers), 0) > 0 THEN ROUND(SUM(f.total_students) / SUM(f.total_teachers), 2) END AS ptr",
        "Free Lunch": "COALESCE(SUM(f.free_lunch_qualified), 0) AS free_lunch_qualified",
        "Reduced Price": "COALESCE(SUM(f.reduced_price_qualified), 0) AS reduced_price_qualified",
        "Direct Certification": "COALESCE(SUM(f.direct_certification), 0) AS direct_certification",
    }
    selected_dims = [dim_map[d] for d in dimensions if d in dim_map]
    if not selected_dims:
        return pd.DataFrame()
    selected_metrics = [metric_map[m] for m in metrics if m in metric_map]
    if not selected_metrics:
        return pd.DataFrame()
    group_expr = ", ".join(expr for expr, _ in selected_dims)
    select_dims = ", ".join(f"{expr} AS {alias}" for expr, alias in selected_dims)
    select_metrics = ", ".join(selected_metrics)
    where, params = _base_where(filters, "ds")
    sql = f"""
    SELECT {select_dims}, {select_metrics}
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    {where}
    GROUP BY {group_expr}
    ORDER BY 1, 2, 3
    LIMIT 1000
    """
    return _q(sql, params)


def _render_data_quality_note():
    st.markdown(
        "<div class='us-note'><strong>Data scope:</strong> US KPIs now use NCES CCD Final v1a for 2024–2025 only. Teacher and PTR coverage may vary in a few jurisdictions based on source submission quality, so state and district totals should be interpreted within NCES reporting limits.</div>",
        unsafe_allow_html=True,
    )


def render_us_home():
    _inject_css()
    if not _phase1_ready():
        _render_missing_data_notice()
        return

    summary = _national_summary()

    st.markdown("<div class='us-title'>🇺🇸 United States Education Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>National K–12 overview using NCES CCD Final v1a · 2024–2025 only.</div>", unsafe_allow_html=True)
    _render_data_quality_note()

    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c1.metric("TOTAL STATES/JURISDICTIONS", _fmt_int(summary.get("total_states")))
    c2.metric("TOTAL SCHOOLS", _fmt_int(summary.get("total_schools")))
    c3.metric("TOTAL STUDENTS", _fmt_int(summary.get("total_students")))
    c4.metric("TOTAL TEACHERS", _fmt_int(summary.get("total_teachers")))
    c5.metric("PTR (NATIONAL)", _fmt_ptr(summary.get("ptr")))
    c6.metric("STUDENTS/SCHOOL", _fmt_int(summary.get("students_per_school")))

    left, right = st.columns(2)
    with left:
        _plot_bar(_top_states_by_schools(10), "state_name", "total_schools", "Top 10 States by School Count")
    with right:
        _plot_bar(_top_states_by_students(20), "state_name", "total_students", "Top 20 States by Student Enrollment")

    st.markdown("### 💡 Key Insights")
    i1, i2, i3 = st.columns(3)
    with i1:
        st.info(f"**School Coverage**\n\nThe 2024–2025 US dataset covers **{_fmt_int(summary.get('total_schools'))}** public schools across **{_fmt_int(summary.get('total_states'))}** states and jurisdictions.")
    with i2:
        st.success(f"**Teaching Staff**\n\nThe loaded Final v1a layer includes **{_fmt_int(summary.get('total_teachers'))}** teachers, supporting a national PTR of **{_fmt_ptr(summary.get('ptr'))}** where staff totals are reported.")
    with i3:
        st.warning(f"**School Size**\n\nAverage public school size is **{_fmt_int(summary.get('students_per_school'))}** students per school based on current 2024–2025 CCD totals.")

    st.markdown("### 🧭 Explore More")
    nav1, nav2 = st.columns(2)
    with nav1:
        st.markdown(
            """
            <a href="/State_Dashboard?region=United%20States" target="_blank" style="
                display: inline-block; width: 100%; padding: 1rem; background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
                color: white !important; text-align: center; text-decoration: none !important; border-radius: 8px;
                font-weight: 600; font-size: 1.1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.2); border: 3px solid #1e88e5;">
                📊 State Dashboard
            </a>
            <div style='padding:.5rem;color:#757575;font-size:.9rem;'>
                Drill into state and district totals, grade enrollment, city mix, and school-level directory facts.
            </div>
            """,
            unsafe_allow_html=True,
        )
    with nav2:
        st.markdown(
            """
            <a href="/Analytics?region=United%20States" target="_blank" style="
                display: inline-block; width: 100%; padding: 1rem; background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
                color: white !important; text-align: center; text-decoration: none !important; border-radius: 8px;
                font-weight: 600; font-size: 1.1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.2); border: 3px solid #1e88e5;">
                📈 Analytics
            </a>
            <div style='padding:.5rem;color:#757575;font-size:.9rem;'>
                Review geographic coverage, performance proxies, comparative analysis, and build exportable custom reports.
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_us_state_dashboard():
    _inject_css()
    if not _phase1_ready():
        _render_missing_data_notice()
        return

    filters = _build_sidebar_filters()
    title_state = filters.get("state") if filters.get("state") and filters.get("state") != "All" else "All States"
    st.markdown(f"<div class='us-title'>📊 US State Dashboard — {title_state}</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>State and district analysis using NCES CCD Final v1a · 2024–2025 only.</div>", unsafe_allow_html=True)
    _render_data_quality_note()

    k = _state_dashboard_kpis(filters)
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c1.metric("TOTAL SCHOOLS", _fmt_int(k.get("total_schools")))
    c2.metric("SCHOOLS WITH ENROLLMENT", _fmt_int(k.get("schools_with_enrollment")))
    c3.metric("DISTRICTS", _fmt_int(k.get("total_districts")))
    c4.metric("STATE PTR", _fmt_ptr(k.get("ptr")))
    c5.metric("TOTAL STUDENTS", _fmt_int(k.get("total_students")))
    c6.metric("TOTAL TEACHERS", _fmt_int(k.get("total_teachers")))

    t1, t2, t3, t4 = st.tabs(["Overview", "Enrollment", "District Analysis", "Directory"])

    with t1:
        left, right = st.columns(2)
        with left:
            _plot_bar(_grade_enrollment(filters), "grade", "total_students", "Grade-wise Enrollment")
        with right:
            _plot_bar(_schools_by_city(filters), "city", "school_count", "Top Cities by School Count", orientation="h")
        mix = _school_level_mix(filters)
        if not mix.empty:
            st.dataframe(mix.rename(columns={"school_level": "School Level", "school_count": "School Count"}), use_container_width=True, hide_index=True)
            _export_buttons(mix, "us_school_level_mix_2024_2025")

    with t2:
        enrollment_df = _grade_enrollment(filters)
        st.dataframe(enrollment_df.rename(columns={"grade": "Grade", "total_students": "Total Students"}), use_container_width=True, hide_index=True)
        _export_buttons(enrollment_df, "us_grade_enrollment_2024_2025")

    with t3:
        district_df = _district_kpi_table(filters, 100)
        _plot_bar(district_df.head(25), "district_name", "total_schools", "Top Districts by School Count", orientation="h")
        st.dataframe(district_df, use_container_width=True, hide_index=True)
        _export_buttons(district_df, "us_district_kpis_2024_2025")

    with t4:
        directory_df = _directory_table(filters, 1000)
        st.dataframe(directory_df, use_container_width=True, height=520, hide_index=True)
        _export_buttons(directory_df, "us_directory_extract_2024_2025")


def render_us_analytics():
    _inject_css()
    if not _phase1_ready():
        _render_missing_data_notice()
        return

    st.markdown("<div class='us-title'>📈 US Analytics</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>Analytics and reporting using NCES CCD Final v1a · 2024–2025 only.</div>", unsafe_allow_html=True)
    _render_data_quality_note()

    tabs = st.tabs(["🗺️ Geographic Maps", "🎯 Performance Metrics", "🔍 Comparative Analysis", "📝 Custom Reports"])

    with tabs[0]:
        state_df = _state_metric_frame()
        metric_choice = st.selectbox(
            "Select metric",
            ["total_schools", "total_students", "total_teachers", "ptr", "free_lunch_qualified"],
            format_func=lambda x: x.replace("_", " ").title().replace("Ptr", "PTR"),
            key="us_geo_metric",
        )
        chart_df = state_df.sort_values(metric_choice, ascending=False).head(25)
        _plot_bar(chart_df, "state_name", metric_choice, f"Top States by {metric_choice.replace('_', ' ').title()}", orientation="h")
        st.dataframe(state_df, use_container_width=True, hide_index=True)
        _export_buttons(state_df, "us_state_metrics_2024_2025")

    with tabs[1]:
        perf_state = st.selectbox("Select State (All for National)", ["All"] + _states(), index=0, key="us_perf_state")
        perf_filters = {"state": perf_state, "districts": [], "school_levels": [], "charter": "All", "virtual": "All"}
        perf = _state_dashboard_kpis(perf_filters)
        k1, k2, k3 = st.columns(3)
        k4, k5, k6 = st.columns(3)
        k1.metric("TOTAL SCHOOLS", _fmt_int(perf.get("total_schools")))
        k2.metric("SCHOOLS WITH ENROLLMENT", _fmt_int(perf.get("schools_with_enrollment")))
        k3.metric("DISTRICTS", _fmt_int(perf.get("total_districts")))
        k4.metric("PTR", _fmt_ptr(perf.get("ptr")))
        k5.metric("TOTAL STUDENTS", _fmt_int(perf.get("total_students")))
        k6.metric("TOTAL TEACHERS", _fmt_int(perf.get("total_teachers")))
        perf_table = _district_kpi_table(perf_filters, 100) if perf_state != "All" else _state_metric_frame()
        st.dataframe(perf_table, use_container_width=True, hide_index=True)
        _export_buttons(perf_table, "us_performance_metrics_2024_2025")

    with tabs[2]:
        comp_level = st.radio("Comparison Level", ["State vs State", "District vs District"], horizontal=True, key="us_comp_level")
        if comp_level == "State vs State":
            states = _states()
            c1, c2 = st.columns(2)
            with c1:
                left_state = st.selectbox("State A", states, index=0, key="us_cmp_a")
            with c2:
                right_state = st.selectbox("State B", states, index=1 if len(states) > 1 else 0, key="us_cmp_b")
            cmp_df = _comparison_frame(left_state, right_state)
        else:
            states = _states()
            c1, c2 = st.columns(2)
            with c1:
                left_state = st.selectbox("State A", states, index=0, key="us_cmp_d_a_state")
                left_district = st.selectbox("District A", _districts(left_state), key="us_cmp_d_a")
            with c2:
                right_state = st.selectbox("State B", states, index=1 if len(states) > 1 else 0, key="us_cmp_d_b_state")
                right_district = st.selectbox("District B", _districts(right_state), key="us_cmp_d_b")
            cmp_df = _district_comparison_frame(left_state, left_district, right_state, right_district)
        st.dataframe(cmp_df, use_container_width=True, hide_index=True)
        _export_buttons(cmp_df, "us_comparison_2024_2025")

    with tabs[3]:
        dimensions = st.multiselect(
            "Choose grouping dimensions",
            ["State", "District", "City", "School Level", "Charter", "Virtual"],
            default=["State"],
            key="us_report_dims",
        )
        metrics = st.multiselect(
            "Choose metrics to include",
            ["Schools", "Schools with Enrollment", "Students", "Teachers", "PTR", "Free Lunch", "Reduced Price", "Direct Certification"],
            default=["Schools", "Students", "PTR"],
            key="us_report_metrics",
        )
        report_state = st.selectbox("Filter report by state", ["All"] + _states(), index=0, key="us_report_state")
        report_districts = st.multiselect("Filter report by district", _districts(report_state), key="us_report_districts")
        report_levels = st.multiselect("Filter report by school level", _school_levels(report_state), key="us_report_levels")
        report_filters = {
            "state": report_state,
            "districts": report_districts,
            "school_levels": report_levels,
            "charter": "All",
            "virtual": "All",
        }
        if dimensions and metrics:
            report_df = _custom_report(dimensions, metrics, report_filters)
            st.dataframe(report_df, use_container_width=True, height=520, hide_index=True)
            _export_buttons(report_df, "us_custom_report_2024_2025")
        else:
            st.info("Select at least one dimension and one metric to generate a custom report.")
'''


def main() -> int:
    if not ROOT.exists():
        print(f'ERROR: repo root not found: {ROOT}')
        return 1
    if not TARGET.exists():
        print(f'ERROR: target file not found: {TARGET}')
        return 1
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = TARGET.with_suffix(TARGET.suffix + f'.bak_{ts}')
    backup.write_text(TARGET.read_text(encoding='utf-8'), encoding='utf-8')
    TARGET.write_text(RENDERER, encoding='utf-8')
    print(f'Backup created: {backup}')
    print(f'Updated: {TARGET}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
