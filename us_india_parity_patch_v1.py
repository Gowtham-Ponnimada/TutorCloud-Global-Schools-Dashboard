#!/usr/bin/env python3
from pathlib import Path
import shutil
import textwrap
import py_compile
import sys

ROOT = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
TARGET = ROOT / 'utils' / 'us_page_renderer.py'

RENDERER = r'''from __future__ import annotations

import io
import os

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

US_REGION = "United States"
DASHBOARD_YEAR = "2024-2025"
DIRECTORY_NOTE = "Directory-only · NCES 2024–2025 preliminary school and LEA directory data"

US_COLORS = {
    "blue": "#1F4E79",
    "teal": "#0F766E",
    "green": "#2E7D32",
    "gold": "#D97706",
    "red": "#B42318",
    "gray": "#667085",
    "border": "#D0D5DD",
    "light": "#F8FAFC",
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


def _fmt(v) -> str:
    try:
        if v is None or pd.isna(v):
            return "0"
        return f"{int(round(float(v))):,}"
    except Exception:
        return "0"


def _fmt_float(v, digits: int = 2) -> str:
    try:
        if v is None or pd.isna(v):
            return "0"
        return f"{float(v):,.{digits}f}"
    except Exception:
        return "0"


def _na() -> str:
    return "Directory only"


def _inject_css():
    st.markdown(
        f"""
        <style>
            .us-title {{ font-size: 1.65rem; font-weight: 700; margin-bottom: .2rem; }}
            .us-subtitle {{ color: {US_COLORS['gray']}; margin-bottom: .85rem; }}
            .us-note {{
                background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px;
                padding:.85rem 1rem; margin:.5rem 0 1rem 0;
            }}
            .us-soft-note {{
                background:{US_COLORS['light']}; border:1px dashed {US_COLORS['border']}; border-radius:10px;
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


def _base_where(filters: dict, include_state=True, include_district=True, include_city=True, include_level=True):
    clauses = ["school_year = %s"]
    params = [DASHBOARD_YEAR]
    if include_state and filters.get("state") and filters["state"] != "All":
        clauses.append("state_name = %s")
        params.append(filters["state"])
    if include_district and filters.get("district") and filters["district"] != "All":
        clauses.append("district_name = %s")
        params.append(filters["district"])
    if include_city and filters.get("city") and filters["city"] != "All":
        clauses.append("city = %s")
        params.append(filters["city"])
    levels = [x for x in (filters.get("school_levels") or []) if x and x != "All"]
    if include_level and levels:
        clauses.append("school_level = ANY(%s)")
        params.append(levels)
    return " WHERE " + " AND ".join(clauses), params


def _states() -> list[str]:
    df = _q(
        "SELECT DISTINCT state_name FROM us.dim_states WHERE school_year = %s AND state_name IS NOT NULL ORDER BY state_name",
        [DASHBOARD_YEAR],
    )
    return [str(x) for x in df["state_name"].tolist()] if not df.empty else []


def _districts(state_name: str | None = None) -> list[str]:
    if state_name and state_name != "All":
        df = _q(
            "SELECT DISTINCT district_name FROM us.dim_districts WHERE school_year = %s AND state_name = %s AND district_name IS NOT NULL ORDER BY district_name",
            [DASHBOARD_YEAR, state_name],
        )
    else:
        df = _q(
            "SELECT DISTINCT district_name FROM us.dim_districts WHERE school_year = %s AND district_name IS NOT NULL ORDER BY district_name",
            [DASHBOARD_YEAR],
        )
    return [str(x) for x in df["district_name"].tolist()] if not df.empty else []


def _cities(state_name: str | None = None, district_name: str | None = None) -> list[str]:
    filters = {"state": state_name or "All", "district": district_name or "All", "city": "All", "school_levels": []}
    where, params = _base_where(filters, include_city=False, include_level=False)
    df = _q(
        f"SELECT DISTINCT city FROM us.dim_schools {where} AND city IS NOT NULL ORDER BY city",
        params,
    )
    return [str(x) for x in df["city"].tolist()] if not df.empty else []


def _school_levels(state_name: str | None = None, district_name: str | None = None) -> list[str]:
    filters = {"state": state_name or "All", "district": district_name or "All", "city": "All", "school_levels": []}
    where, params = _base_where(filters, include_city=False, include_level=False)
    df = _q(
        f"SELECT DISTINCT school_level FROM us.dim_schools {where} AND school_level IS NOT NULL ORDER BY school_level",
        params,
    )
    return [str(x) for x in df["school_level"].tolist() if str(x) != "None"] if not df.empty else []


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


def _plot_bar(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v"):
    if df is None or df.empty:
        st.info(f"No data available for {title}.")
        return
    fig = px.bar(
        df,
        x=x if orientation == "v" else y,
        y=y if orientation == "v" else x,
        orientation=orientation,
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=55, b=10),
        font=dict(family="Segoe UI"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def _plot_placeholder(title: str, detail: str):
    st.markdown(f"### {title}")
    st.info(detail)


def _national_summary() -> dict:
    states_df = _q("SELECT COUNT(*) AS c FROM us.dim_states WHERE school_year = %s", [DASHBOARD_YEAR])
    districts_df = _q("SELECT COUNT(*) AS c FROM us.dim_districts WHERE school_year = %s", [DASHBOARD_YEAR])
    schools_df = _q("SELECT COUNT(*) AS c FROM us.dim_schools WHERE school_year = %s", [DASHBOARD_YEAR])
    states = int(states_df.iloc[0]["c"] or 0) if not states_df.empty else 0
    districts = int(districts_df.iloc[0]["c"] or 0) if not districts_df.empty else 0
    schools = int(schools_df.iloc[0]["c"] or 0) if not schools_df.empty else 0
    return {
        "states": states,
        "districts": districts,
        "schools": schools,
    }


def _top_states_by_schools(limit: int = 10) -> pd.DataFrame:
    return _q(
        "SELECT state_name AS state, school_count AS total_schools FROM us.dim_states WHERE school_year = %s ORDER BY school_count DESC, state_name LIMIT %s",
        [DASHBOARD_YEAR, limit],
    )


def _overview_counts(filters: dict) -> dict:
    where, params = _base_where(filters)
    df = _q(
        f"SELECT COUNT(DISTINCT school_id) AS total_schools, COUNT(DISTINCT district_id) AS total_districts, COUNT(DISTINCT city) AS total_cities FROM us.dim_schools {where}",
        params,
    )
    if df.empty:
        return {"total_schools": 0, "total_districts": 0, "total_cities": 0}
    row = df.iloc[0].fillna(0)
    return {
        "total_schools": int(row.get("total_schools", 0)),
        "total_districts": int(row.get("total_districts", 0)),
        "total_cities": int(row.get("total_cities", 0)),
    }


def _school_level_mix(filters: dict) -> pd.DataFrame:
    where, params = _base_where(filters)
    return _q(
        f"SELECT COALESCE(school_level, 'Unknown') AS school_level, COUNT(DISTINCT school_id) AS school_count FROM us.dim_schools {where} GROUP BY 1 ORDER BY school_count DESC, school_level",
        params,
    )


def _district_school_counts(filters: dict, limit: int = 20) -> pd.DataFrame:
    where, params = _base_where(filters, include_district=False, include_city=False)
    params = params + [limit]
    return _q(
        f"SELECT district_name AS district, COUNT(DISTINCT school_id) AS total_schools FROM us.dim_schools {where} AND district_name IS NOT NULL GROUP BY 1 ORDER BY total_schools DESC, district_name LIMIT %s",
        params,
    )


def _city_school_counts(filters: dict, limit: int = 20) -> pd.DataFrame:
    where, params = _base_where(filters, include_city=False)
    params = params + [limit]
    return _q(
        f"SELECT COALESCE(city, 'Unknown') AS city, COUNT(DISTINCT school_id) AS total_schools FROM us.dim_schools {where} GROUP BY 1 ORDER BY total_schools DESC, city LIMIT %s",
        params,
    )


def _directory_table(filters: dict, limit: int = 500) -> pd.DataFrame:
    where, params = _base_where(filters)
    params = params + [limit]
    return _q(
        f"SELECT school_name, district_name, state_name, city, school_level, low_grade, high_grade, zip_code FROM us.dim_schools {where} ORDER BY state_name, district_name, school_name LIMIT %s",
        params,
    )


def _grade_span_table(filters: dict, limit: int = 100) -> pd.DataFrame:
    where, params = _base_where(filters)
    params = params + [limit]
    return _q(
        f"SELECT CONCAT(COALESCE(low_grade, '?'), ' → ', COALESCE(high_grade, '?')) AS grade_span, COUNT(DISTINCT school_id) AS total_schools FROM us.dim_schools {where} GROUP BY 1 ORDER BY total_schools DESC, grade_span LIMIT %s",
        params,
    )


def _district_analysis_placeholder(filters: dict) -> pd.DataFrame:
    df = _district_school_counts(filters, 200)
    if df.empty:
        return df
    out = df.rename(columns={"district": "District", "total_schools": "Total Schools"}).copy()
    out["Total Students"] = "Not loaded"
    out["Total Teachers"] = "Not loaded"
    out["PTR"] = "Not loaded"
    return out[["District", "Total Schools", "Total Students", "Total Teachers", "PTR"]]


def _city_analysis_placeholder(filters: dict) -> pd.DataFrame:
    base_filters = dict(filters)
    base_filters["city"] = "All"
    df = _city_school_counts(base_filters, 200)
    if df.empty:
        return df
    out = df.rename(columns={"city": "City", "total_schools": "Total Schools"}).copy()
    out["Total Students"] = "Not loaded"
    out["Total Teachers"] = "Not loaded"
    out["PTR"] = "Not loaded"
    return out[["City", "Total Schools", "Total Students", "Total Teachers", "PTR"]]


def _state_metrics_table() -> pd.DataFrame:
    return _q(
        "SELECT state_name AS state, district_count AS total_districts, school_count AS total_schools FROM us.dim_states WHERE school_year = %s ORDER BY state_name",
        [DASHBOARD_YEAR],
    )


def _district_metrics_for_state(state_name: str) -> pd.DataFrame:
    return _q(
        "SELECT district_name AS district, school_count AS total_schools FROM us.dim_districts WHERE school_year = %s AND state_name = %s ORDER BY district_name",
        [DASHBOARD_YEAR, state_name],
    )


def _comparison_frame(level: str, left: str, right: str, left_state: str | None = None, right_state: str | None = None) -> pd.DataFrame:
    if level == "state":
        sql = """
        SELECT state_name AS location, district_count AS total_districts, school_count AS total_schools
        FROM us.dim_states
        WHERE school_year = %s AND state_name = ANY(%s)
        ORDER BY location
        """
        df = _q(sql, [DASHBOARD_YEAR, [left, right]])
        if df.empty:
            return df
        out = df.copy()
        out["Total Students"] = "Not loaded"
        out["Total Teachers"] = "Not loaded"
        out["PTR"] = "Not loaded"
        return out.rename(columns={"location": "Location", "total_districts": "Total Districts", "total_schools": "Total Schools"})

    sql = """
    SELECT district_name AS location, school_count AS total_schools
    FROM us.dim_districts
    WHERE school_year = %s AND ((state_name = %s AND district_name = %s) OR (state_name = %s AND district_name = %s))
    ORDER BY location
    """
    df = _q(sql, [DASHBOARD_YEAR, left_state, left, right_state, right])
    if df.empty:
        return df
    out = df.copy()
    out["Total Students"] = "Not loaded"
    out["Total Teachers"] = "Not loaded"
    out["PTR"] = "Not loaded"
    return out.rename(columns={"location": "Location", "total_schools": "Total Schools"})


def _custom_report(dimensions: list[str]) -> pd.DataFrame:
    dim_map = {
        "State": "state_name",
        "District": "district_name",
        "City": "city",
        "School Level": "school_level",
    }
    cols = [dim_map[d] for d in dimensions if d in dim_map]
    if not cols:
        return pd.DataFrame()
    select_clause = ", ".join(cols)
    sql = f"SELECT {select_clause}, COUNT(DISTINCT school_id) AS total_schools FROM us.dim_schools WHERE school_year = %s GROUP BY {select_clause} ORDER BY total_schools DESC LIMIT 1000"
    df = _q(sql, [DASHBOARD_YEAR])
    if df.empty:
        return df
    df = df.rename(columns={c: c.replace("_", " ").title() for c in df.columns})
    return df


def _build_sidebar_filters() -> dict:
    with st.sidebar:
        st.markdown("### 🔍 Apply Filters")
        states = _states()
        selected_state = st.selectbox("🗺️ Select State/UT", options=states if states else ["No states"], key="us_state_filter")
        districts = _districts(selected_state) if selected_state and selected_state != "No states" else []
        selected_district = st.selectbox("🏘️ Select District", options=["All"] + districts, index=0, key=f"us_district_filter_{selected_state}")
        cities = _cities(selected_state, selected_district) if selected_state and selected_state != "No states" else []
        selected_city = st.selectbox("📍 Select City", options=["All"] + cities, index=0, key=f"us_city_filter_{selected_state}_{selected_district}")
        level_opts = _school_levels(selected_state, selected_district)
        selected_levels = st.multiselect(
            "📚 School Category (Grade Level)",
            options=level_opts,
            default=[],
            key=f"us_level_filter_{selected_state}_{selected_district}",
            help="US directory currently supports school-level categories from NCES directory fields.",
        )

        st.selectbox("🌆 Location", options=["Not available in current US directory"], index=0, disabled=True, key="us_disabled_location")
        st.multiselect("📖 School Type", options=["Not available in current US directory"], default=[], disabled=True, key="us_disabled_school_type")
        st.multiselect("🏛️ Management Type", options=["Not available in current US directory"], default=[], disabled=True, key="us_disabled_management")
        st.multiselect("📚 Board Affiliation", options=["Not available in current US directory"], default=[], disabled=True, key="us_disabled_board")

        active_filters = [selected_state] if selected_state and selected_state != "No states" else []
        if selected_district != "All":
            active_filters.append(selected_district)
        if selected_city != "All":
            active_filters.append(selected_city)
        for lvl in selected_levels:
            active_filters.append(f"Level: {lvl}")

        if active_filters:
            st.markdown("---")
            st.markdown("### ✅ Active Filters")
            for item in active_filters:
                st.markdown(f"- {item}")

        return {
            "state": selected_state if selected_state != "No states" else "All",
            "district": selected_district,
            "city": selected_city,
            "school_levels": selected_levels,
        }


def render_us_home():
    _inject_css()
    summary = _national_summary()

    st.markdown("# 🏠 TutorCloud Global Dashboard")
    st.markdown("**National K-12 Education Overview - United States 2024-25**")
    st.markdown("---")
    st.markdown(f"<div class='us-note'><strong>Current US mode:</strong> {DIRECTORY_NOTE}. Layout is aligned to the India dashboard, while unsupported fact-based metrics remain intentionally unavailable until enrollment, teacher, and performance datasets are loaded.</div>", unsafe_allow_html=True)

    st.markdown("## 📊 National Overview")
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    with col1:
        st.metric("TOTAL STATES/UTs", _fmt(summary["states"]))
    with col2:
        st.metric("TOTAL SCHOOLS", _fmt(summary["schools"]))
    with col3:
        st.metric("TOTAL STUDENTS", _na())
    with col4:
        st.metric("TOTAL TEACHERS", _na())
    with col5:
        st.metric("PTR (NATIONAL)", _na())
    with col6:
        st.metric("STUDENTS/SCHOOL", _na())

    st.markdown("## 🏆 Top 10 States by School Count")
    _plot_bar(_top_states_by_schools(10), "state", "total_schools", "Top 10 States by School Count")

    st.markdown("## 📚 Top 20 States by Student Enrollment")
    st.info("Student enrollment facts are not part of the current US directory-only layer. This section is intentionally held until the US enrollment dataset is loaded.")

    st.markdown("## 💡 Key Insights")
    i1, i2, i3 = st.columns(3)
    with i1:
        st.info(f"**📚 School Coverage**\n\nThe US directory includes **{summary['schools']:,}** schools across **{summary['states']:,}** states/jurisdictions and **{summary['districts']:,}** districts.")
    with i2:
        st.warning("**👨‍🏫 Teaching Staff**\n\nTeacher and staffing metrics are not loaded yet for the US build, so national teacher totals and PTR are intentionally withheld.")
    with i3:
        st.warning("**🏫 School Size**\n\nStudents-per-school requires enrollment facts and will be activated once the US fact layer is loaded.")

    st.markdown("## 🧭 Explore More")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <a href="/State_Dashboard?region=United%20States" target="_blank" style="
                display: inline-block; width: 100%; padding: 1rem;
                background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
                color: white !important; text-align: center; text-decoration: none !important;
                border-radius: 8px; font-weight: 600; font-size: 1.1rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2); border: 3px solid #1e88e5;">
                📊 State Dashboard
            </a>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style='padding: 0.5rem; color: #757575; font-size: 0.9rem;'>
            Drill down into state, district, and city-level US directory data with aligned India-style layout.
            <ul style='margin-top: 0.5rem;'>
                <li>Filter by state, district, city, and school level</li>
                <li>Review district structure and directory extracts</li>
                <li>Export filtered directory outputs</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <a href="/Analytics?region=United%20States" target="_blank" style="
                display: inline-block; width: 100%; padding: 1rem;
                background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
                color: white !important; text-align: center; text-decoration: none !important;
                border-radius: 8px; font-weight: 600; font-size: 1.1rem;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2); border: 3px solid #1e88e5;">
                📈 Analytics
            </a>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style='padding: 0.5rem; color: #757575; font-size: 0.9rem;'>
            Interactive analytics aligned to the India tab order, while clearly separating currently unavailable fact-driven metrics.
            <ul style='margin-top: 0.5rem;'>
                <li>Geographic coverage views</li>
                <li>State and district comparison</li>
                <li>Custom report builder</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_us_state_dashboard():
    _inject_css()
    filters = _build_sidebar_filters()
    selected_state = filters.get("state", "All")
    overview = _overview_counts(filters)

    st.markdown('<div class="main-header">📊 State Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive State-Level Analysis with India-aligned layout and directory-only US calculations</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='us-soft-note'><strong>US data scope:</strong> {DIRECTORY_NOTE}. Filter structure follows the India dashboard as closely as possible using currently loaded US fields.</div>", unsafe_allow_html=True)

    if not selected_state or selected_state == "All":
        st.info("👈 Please select a State/UT from the sidebar to view data")
        return

    st.markdown(f"<div class='section-header'>📊 Overview: {selected_state}</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🏫 Total Schools", _fmt(overview["total_schools"]))
    with c2:
        st.metric("🎓 Schools with Enrollment", _na())
    with c3:
        st.metric("🗺️ Districts", _fmt(overview["total_districts"]))
    with c4:
        st.metric("📊 State PTR", _na())

    c5, c6 = st.columns(2)
    with c5:
        st.metric("👥 Total Students", _na())
    with c6:
        st.metric("👨‍🏫 Total Teachers", _na())

    _plot_placeholder(
        "📚 Grade-Level Enrollment (Boys vs Girls)",
        "The India dashboard uses enrollment facts for this chart. The current US build is directory-only, so this section will activate after US enrollment data is loaded.",
    )

    st.markdown("### 🏆 District Structure (Available Now)")
    _plot_bar(_district_school_counts(filters, 20), "district", "total_schools", "Top 20 Districts by School Count", orientation="h")

    st.markdown("### 🏘️ City Structure (Available Now)")
    city_df = _city_school_counts(filters, 20)
    if filters.get("district") == "All":
        st.info("Select a district to narrow the local-area analysis, similar to the India Block/Taluk drill-down.")
    _plot_bar(city_df, "city", "total_schools", "Top 20 Cities by School Count", orientation="h")

    st.markdown("### 📋 District-Level PTR Analysis")
    district_table = _district_analysis_placeholder(filters)
    st.dataframe(district_table, use_container_width=True, height=420)
    _export_buttons(district_table, "us_district_level_analysis_directory_only")

    st.markdown("### 📍 City-Level Directory Analysis")
    city_table = _city_analysis_placeholder(filters)
    st.dataframe(city_table, use_container_width=True, height=420)
    _export_buttons(city_table, "us_city_level_analysis_directory_only")

    st.markdown("### 🏫 Directory Extract")
    directory_df = _directory_table(filters, 250)
    st.dataframe(directory_df, use_container_width=True, height=450)
    _export_buttons(directory_df, "us_directory_filtered_extract")


def render_us_analytics():
    _inject_css()
    st.markdown('<div class="main-header">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enhanced Analytics: Maps, Metrics, Comparison & Reports</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='us-note'><strong>Parity mode:</strong> Tab order and section flow now mirror the India dashboard. Where the US directory dataset does not support India calculations yet, the page shows explicit availability messaging instead of fabricated metrics.</div>", unsafe_allow_html=True)

    tabs = st.tabs([
        "🗺️ Geographic Maps",
        "🎯 Performance Metrics",
        "🔍 Comparative Analysis",
        "📝 Custom Reports",
    ])

    with tabs[0]:
        st.markdown("### 🗺️ Geographic Heatmaps")
        st.markdown("Interactive coverage views aligned with the India dashboard structure")
        col1, col2 = st.columns([1, 3])
        with col1:
            metric_choice = st.selectbox(
                "Select Metric to Visualize",
                ["Total Schools", "PTR (Pupil-Teacher Ratio)", "Total Students", "Total Teachers"],
                key="us_map_metric",
            )
        with col2:
            level = st.radio("Level", ["State", "District"], horizontal=True, key="us_map_level")

        if metric_choice != "Total Schools":
            st.info("Only Total Schools is currently available in the US directory-only layer. Other India-style metrics will activate after the relevant fact tables are loaded.")
        else:
            if level == "State":
                df_map = _state_metrics_table().sort_values("total_schools", ascending=False).head(20)
                _plot_bar(df_map.rename(columns={"state": "State", "total_schools": "Total Schools"}), "State", "Total Schools", "Total Schools by State (Top 20)")
                st.dataframe(df_map.rename(columns=lambda x: x.replace("_", " ").title()), use_container_width=True)
            else:
                states = _states()
                selected_state = st.selectbox("Select State", states, key="us_map_state_select") if states else None
                df_map = _district_metrics_for_state(selected_state) if selected_state else pd.DataFrame()
                _plot_bar(df_map.sort_values("total_schools", ascending=False).head(20), "district", "total_schools", f"Total Schools by District - {selected_state}", orientation="h")
                st.dataframe(df_map.rename(columns=lambda x: x.replace("_", " ").title()), use_container_width=True)

    with tabs[1]:
        st.markdown("### 🎯 Performance Metrics Dashboard")
        states = ["All"] + _states()
        col1, col2 = st.columns(2)
        with col1:
            filter_state = st.selectbox("Select State (All for National)", states, key="us_perf_state")
        with col2:
            districts = ["All"] + (_districts(filter_state) if filter_state != "All" else [])
            filter_district = st.selectbox("Select District (All for State)", districts, key="us_perf_district")

        perf_filters = {
            "state": filter_state,
            "district": filter_district,
            "city": "All",
            "school_levels": [],
        }
        counts = _overview_counts(perf_filters)

        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            st.metric("Total Schools", _fmt(counts["total_schools"]))
        with kpi_cols[1]:
            st.metric("Total Students", _na())
        with kpi_cols[2]:
            st.metric("Total Teachers", _na())
        with kpi_cols[3]:
            st.metric("PTR", _na())

        a1, a2 = st.columns(2)
        with a1:
            st.metric("Students per School", _na())
        with a2:
            st.metric("Teachers per School", _na())

        st.info("This Performance Metrics tab now matches the India tab structure. Numeric performance calculations will populate after US enrollment and teacher fact tables are added.")

    with tabs[2]:
        st.markdown("### 🔍 Comparative Analysis Tool")
        st.markdown("Compare two locations side-by-side across all currently available US directory metrics")
        comp_level = st.radio("Comparison Level", ["State vs State", "District vs District"], horizontal=True, key="us_comp_level")
        col1, col2 = st.columns(2)

        if comp_level == "State vs State":
            states = _states()
            with col1:
                state1 = st.selectbox("State", states, key="us_comp_state1") if states else None
            with col2:
                state2 = st.selectbox("State ", states, index=1 if states and len(states) > 1 else 0, key="us_comp_state2") if states else None
            if state1 and state2:
                cmp_df = _comparison_frame("state", state1, state2)
                st.dataframe(cmp_df, use_container_width=True, hide_index=True)
                _export_buttons(cmp_df, "us_state_comparison_directory_only")
        else:
            states = _states()
            with col1:
                state1 = st.selectbox("State", states, key="us_comp_dist_state1") if states else None
                districts1 = _districts(state1) if state1 else []
                district1 = st.selectbox("District", districts1, key="us_comp_district1") if districts1 else None
            with col2:
                state2 = st.selectbox("State ", states, index=1 if states and len(states) > 1 else 0, key="us_comp_dist_state2") if states else None
                districts2 = _districts(state2) if state2 else []
                district2 = st.selectbox("District ", districts2, key="us_comp_district2") if districts2 else None
            if state1 and district1 and state2 and district2:
                cmp_df = _comparison_frame("district", district1, district2, state1, state2)
                st.dataframe(cmp_df, use_container_width=True, hide_index=True)
                _export_buttons(cmp_df, "us_district_comparison_directory_only")

    with tabs[3]:
        st.markdown("### 📝 Custom Report Builder")
        st.markdown("Build custom reports with the currently available US directory dimensions")
        dimensions = st.multiselect(
            "Choose grouping dimensions",
            ["State", "District", "City", "School Level"],
            default=["State"],
            key="us_report_dims",
        )
        metrics = st.multiselect(
            "Choose metrics to include",
            ["Schools", "Students", "Teachers", "PTR"],
            default=["Schools"],
            key="us_report_metrics",
        )

        if st.button("📊 Generate Report", type="primary", key="us_report_btn"):
            if not dimensions or not metrics:
                st.warning("Please select at least one dimension and one metric")
            else:
                df_report = _custom_report(dimensions)
                if df_report.empty:
                    st.warning("No data found for selected criteria")
                else:
                    if "Students" in metrics:
                        df_report["Total Students"] = "Not loaded"
                    if "Teachers" in metrics:
                        df_report["Total Teachers"] = "Not loaded"
                    if "PTR" in metrics:
                        df_report["PTR"] = "Not loaded"
                    st.success(f"Report generated successfully! ({len(df_report)} rows)")
                    st.dataframe(df_report, use_container_width=True)
                    _export_buttons(df_report, "us_custom_report_directory_only")

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; padding: 20px; margin-top: 20px; border-top: 1px solid #e0e0e0;'>"
        "<p style='margin: 0; color: #666; font-size: 0.95rem;'>TutorCloud Global Dashboard</p>"
        "<p style='margin: 5px 0 0 0; color: #666; font-size: 0.95rem;'>© 2026 TutorCloud. All rights reserved.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
'''


def main() -> int:
    if not TARGET.parent.exists():
        print(f'ERROR: Target directory not found: {TARGET.parent}')
        return 1

    if TARGET.exists():
        backup = TARGET.with_name('us_page_renderer.py.bak_india_parity_v1')
        shutil.copy2(TARGET, backup)
        print(f'Backup created: {backup}')

    TARGET.write_text(textwrap.dedent(RENDERER), encoding='utf-8')

    try:
        py_compile.compile(str(TARGET), doraise=True)
    except Exception as exc:
        print('ERROR: Syntax validation failed for utils/us_page_renderer.py')
        print(exc)
        return 2

    print('SUCCESS: India-parity US renderer written to utils/us_page_renderer.py')
    print('Scope: layout/tabs/KPI order aligned to India; unsupported US fact metrics remain explicit as Directory only.')
    print('Next: restart Streamlit and verify United States Home, State Dashboard, and Analytics pages.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
