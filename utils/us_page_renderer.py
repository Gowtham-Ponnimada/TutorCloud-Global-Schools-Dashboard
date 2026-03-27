from __future__ import annotations

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


def _cities(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "city IS NOT NULL", "BTRIM(city) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT city FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY city"
    return _distinct_values(sql, params, "city")



def _school_levels(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "school_level IS NOT NULL", "BTRIM(school_level) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT school_level FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY school_level"
    return _distinct_values(sql, params, "school_level")



def _school_types(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "sch_type_text IS NOT NULL", "BTRIM(sch_type_text) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT sch_type_text FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY sch_type_text"
    return _distinct_values(sql, params, "sch_type_text")



def _district_types(state_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "lea_type_text IS NOT NULL", "BTRIM(lea_type_text) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    sql = f"SELECT DISTINCT lea_type_text FROM {SCHEMA}.dim_districts WHERE {' AND '.join(clauses)} ORDER BY lea_type_text"
    return _distinct_values(sql, params, "lea_type_text")


def _build_sidebar_filters() -> dict:
    with st.sidebar:
        st.markdown("### US Filters")
        state_opts = ["All"] + _states()
        state = st.selectbox("Select State", state_opts, index=0, key="us_state")

        district_opts = ["All"] + _districts(state)
        district = st.selectbox("Select District", district_opts, index=0, key="us_district")

        city_opts = _cities(state, district)
        cities = st.multiselect("Select City", city_opts, key="us_cities")

        school_type_opts = _school_types(state, district)
        school_types = st.multiselect("School Type", school_type_opts, key="us_school_types")

        district_type_opts = _district_types(state)
        district_types = st.multiselect("District Type", district_type_opts, key="us_district_types")

        level_opts = _school_levels(state, district)
        school_levels = st.multiselect("School Category", level_opts, key="us_levels")

        charter = st.selectbox("Charter", ["All", "Yes", "No"], index=0, key="us_charter")
        virtual = st.selectbox(
            "Virtual",
            ["All"] + _distinct_values(
                f"SELECT DISTINCT virtual_text FROM {SCHEMA}.dim_schools WHERE school_year = %s AND virtual_text IS NOT NULL ORDER BY virtual_text",
                [DASHBOARD_YEAR],
                "virtual_text",
            ),
            index=0,
            key="us_virtual",
        )

        return {
            "state": state,
            "district": district,
            "districts": [district] if district != "All" else [],
            "cities": cities,
            "school_levels": school_levels,
            "school_types": school_types,
            "district_types": district_types,
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
    cities = [x for x in (filters.get("cities") or []) if x]
    if cities:
        clauses.append(f"{alias}.city = ANY(%s)")
        params.append(cities)
    levels = [x for x in (filters.get("school_levels") or []) if x]
    if levels:
        clauses.append(f"{alias}.school_level = ANY(%s)")
        params.append(levels)
    school_types = [x for x in (filters.get("school_types") or []) if x]
    if school_types:
        clauses.append(f"COALESCE({alias}.sch_type_text, 'Unknown') = ANY(%s)")
        params.append(school_types)
    district_types = [x for x in (filters.get("district_types") or []) if x]
    if district_types:
        clauses.append(
            f"EXISTS (SELECT 1 FROM {SCHEMA}.dim_districts dd WHERE dd.school_year = {alias}.school_year AND dd.district_id = {alias}.district_id AND COALESCE(dd.lea_type_text, 'Unknown') = ANY(%s))"
        )
        params.append(district_types)
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


def _state_metric_frame(school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
    return _q(
        f"""
        SELECT state_name, total_schools, total_districts, total_students, total_teachers, ptr,
               CASE WHEN COALESCE(total_schools, 0) > 0 THEN ROUND(total_students::numeric / total_schools, 2) END AS students_per_school,
               free_lunch_qualified, reduced_price_qualified, direct_certification, schools_with_enrollment
        FROM {SCHEMA}.vw_state_kpis_2024_2025
        WHERE school_year = %s
        ORDER BY state_name
        """,
        [school_year],
    )


def _year_tag(school_year: str) -> str:
    return str(school_year).replace("-", "_")


@st.cache_data(show_spinner=False)
def _table_columns(table_name: str) -> set[str]:
    df = _q(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        [SCHEMA, table_name],
    )
    if df.empty or "column_name" not in df.columns:
        return set()
    return {str(v).lower() for v in df["column_name"].tolist() if v is not None}



def _first_existing_column(table_name: str, candidates: list[str]) -> str | None:
    cols = _table_columns(table_name)
    for candidate in candidates:
        if candidate.lower() in cols:
            return candidate.lower()
    return None



def _county_metric_frame(state_name: str = "All", school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
    stage_table = f"stg_sch_directory_{_year_tag(school_year)}"
    county_col = _first_existing_column(stage_table, ["county_name", "coname", "county", "countyname", "county15", "coname15"])
    school_id_col = _first_existing_column(stage_table, ["ncessch", "school_id", "schoolid", "nces_id"])
    if not county_col or not school_id_col:
        return pd.DataFrame()

    county_expr = f"COALESCE(NULLIF(BTRIM(sd.{county_col}::text), ''), 'Unknown')"
    location_expr = county_expr if state_name != "All" else f"{county_expr} || ', ' || ds.state_name"

    params: list = [school_year]
    where = ["ds.school_year = %s"]
    if state_name and state_name != "All":
        where.append("ds.state_name = %s")
        params.append(state_name)

    sql = f"""
    SELECT
        ds.state_name,
        {county_expr} AS county_name,
        {location_expr} AS location_name,
        COUNT(DISTINCT ds.school_id) AS total_schools,
        COALESCE(SUM(f.total_students), 0) AS total_students,
        COALESCE(SUM(f.total_teachers), 0) AS total_teachers,
        CASE WHEN COALESCE(SUM(f.total_teachers), 0) > 0 THEN ROUND(SUM(f.total_students)::numeric / SUM(f.total_teachers), 2) END AS ptr,
        CASE WHEN COUNT(DISTINCT ds.school_id) > 0 THEN ROUND(SUM(f.total_students)::numeric / COUNT(DISTINCT ds.school_id), 2) END AS students_per_school
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    LEFT JOIN {SCHEMA}.{stage_table} sd
      ON BTRIM(COALESCE(sd.{school_id_col}::text, '')) = ds.school_id
    WHERE {' AND '.join(where)}
    GROUP BY 1, 2, 3
    HAVING COUNT(DISTINCT ds.school_id) > 0
    ORDER BY total_schools DESC NULLS LAST, location_name
    """
    return _q(sql, params)



def _district_metric_frame(state_name: str = "All", school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
    params: list = [school_year]
    clauses = ["school_year = %s"]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)

    location_expr = "district_name" if state_name != "All" else "district_name || ', ' || state_name"
    sql = f"""
    SELECT
        state_name,
        district_name,
        {location_expr} AS location_name,
        total_schools,
        total_students,
        total_teachers,
        ptr,
        CASE WHEN COALESCE(total_schools, 0) > 0 THEN ROUND(total_students::numeric / total_schools, 2) END AS students_per_school
    FROM {SCHEMA}.vw_district_kpis_2024_2025
    WHERE {' AND '.join(clauses)}
    ORDER BY total_schools DESC NULLS LAST, state_name, district_name
    """
    return _q(sql, params)


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


def _render_footer():
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; padding: 20px; margin-top: 40px; border-top: 1px solid #e0e0e0;'>
        <p style='margin: 0; color: #666; font-size: 0.95rem;'>TutorCloud Global Dashboard</p>
        <p style='margin: 5px 0 0 0; color: #666; font-size: 0.95rem;'>© 2026 TutorCloud. All rights reserved.</p>
        </div>
        """,
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

    _render_footer()


def render_us_state_dashboard():
    _inject_css()
    if not _phase1_ready():
        _render_missing_data_notice()
        return

    filters = _build_sidebar_filters()
    title_state = filters.get("state") if filters.get("state") and filters.get("state") != "All" else "All States"
    if filters.get("district") and filters.get("district") != "All":
        title_state = f"{title_state} / {filters.get('district')}"
    st.markdown(f"<div class='us-title'>📊 US State Dashboard — {title_state}</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>State and district analysis using NCES CCD Final v1a with US-equivalent filter depth.</div>", unsafe_allow_html=True)

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

    _render_footer()


def _available_school_years() -> list[str]:
    df = _q(
        f"SELECT DISTINCT school_year FROM {SCHEMA}.dim_states WHERE school_year IS NOT NULL ORDER BY school_year DESC"
    )
    if df.empty:
        return [DASHBOARD_YEAR]
    years = [str(v) for v in df["school_year"].tolist() if str(v).strip() and str(v) != "None"]
    return years or [DASHBOARD_YEAR]



def _inject_analytics_parity_css():
    st.markdown(
        """
        <style>
            .breadcrumb-nav {
                font-size: 0.92rem;
                color: #667085;
                margin-bottom: 0.25rem;
            }
            .breadcrumb-nav a {
                color: #1F4E79;
                text-decoration: none;
                font-weight: 600;
            }
            .breadcrumb-nav span {
                color: #475467;
                font-weight: 600;
            }
            .main-header {
                font-size: 2rem;
                font-weight: 700;
                color: #1F4E79;
                margin-bottom: 0.2rem;
                line-height: 1.2;
            }
            .sub-header {
                font-size: 1rem;
                color: #667085;
                margin-bottom: 1.2rem;
            }
            [data-testid="stMetric"] {
                background-color: white !important;
                padding: 1.2rem !important;
                border-radius: 12px !important;
                border: 3px solid #1F4E79 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.55rem !important;
                font-weight: 700 !important;
                color: #1F4E79 !important;
            }
            [data-testid="stMetricLabel"] {
                font-size: 0.88rem !important;
                font-weight: 600 !important;
                color: #667085 !important;
                text-transform: uppercase;
                letter-spacing: 0.4px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_us_analytics():
    _inject_css()
    _inject_analytics_parity_css()
    if not _phase1_ready():
        _render_missing_data_notice()
        return

    year_options = _available_school_years()
    default_year_index = year_options.index(DASHBOARD_YEAR) if DASHBOARD_YEAR in year_options else 0

    top_left, top_right = st.columns([4, 1.25])
    with top_left:
        st.markdown(
            "<div class='breadcrumb-nav'><a href='/?region=United%20States' target='_self'>Home</a> / <span>Analytics</span></div>",
            unsafe_allow_html=True,
        )
    with top_right:
        selected_year = st.selectbox("Academic Year", year_options, index=default_year_index, key="us_analytics_year")

    st.markdown('<div class="main-header">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enhanced Analytics: Maps, Metrics, Comparison & Reports</div>', unsafe_allow_html=True)

    if selected_year != DASHBOARD_YEAR:
        st.info("US analytics is currently backed by the loaded 2024–2025 NCES dataset. Additional years will appear here after they are ingested.")

    tabs = st.tabs(["🗺️ Geographic Maps", "🎯 Performance Metrics", "🔍 Comparative Analysis", "📝 Custom Reports"])

    with tabs[0]:
        st.markdown("### 🗺️ Geographic Heatmaps")
        st.markdown("Interactive maps showing PTR and enrollment intensity by state, county, and district")

        geo_c1, geo_c2, geo_c3 = st.columns([1.3, 1.4, 1.8])
        with geo_c1:
            metric_choice = st.selectbox(
                "Select Metric to Visualize",
                ["PTR (Pupil-Teacher Ratio)", "Students per School", "Total Students", "Total Schools"],
                key="us_geo_metric",
            )
        with geo_c2:
            level_choice = st.radio("Level", ["State", "County", "District"], horizontal=True, key="us_geo_level")
        with geo_c3:
            geo_state = "All"
            if level_choice in ("County", "District"):
                geo_state = st.selectbox("State Filter", ["All"] + _states(), index=0, key="us_geo_state")

        metric_map = {
            "PTR (Pupil-Teacher Ratio)": "ptr",
            "Students per School": "students_per_school",
            "Total Students": "total_students",
            "Total Schools": "total_schools",
        }
        metric_col = metric_map[metric_choice]

        if level_choice == "State":
            df_map = _state_metric_frame(selected_year)
            location_col = "state_name"
            export_prefix = f"us_state_metrics_{selected_year.replace('-', '_')}"
        elif level_choice == "County":
            df_map = _county_metric_frame(geo_state, selected_year)
            location_col = "location_name"
            export_prefix = f"us_county_metrics_{selected_year.replace('-', '_')}"
        else:
            df_map = _district_metric_frame(geo_state, selected_year)
            location_col = "location_name"
            export_prefix = f"us_district_metrics_{selected_year.replace('-', '_')}"

        if df_map.empty:
            if level_choice == "County":
                st.warning("County-level metrics are unavailable because the preserved NCES school directory staging table or county column could not be found.")
            else:
                st.info("No data available for the selected geographic level.")
        else:
            df_chart = df_map.sort_values(metric_col, ascending=False).head(20).copy()
            if metric_col == "ptr":
                df_chart["ptr_formatted"] = df_chart["ptr"].apply(lambda x: f"{int(round(float(x)))}:1" if pd.notna(x) and float(x) > 0 else "N/A")
                fig = px.bar(
                    df_chart,
                    x=location_col,
                    y=metric_col,
                    title=f"{metric_choice} by {level_choice} (Top 20)",
                    labels={metric_col: metric_choice, location_col: level_choice},
                    color=metric_col,
                    color_continuous_scale="RdYlGn_r",
                    custom_data=["ptr_formatted"],
                )
                fig.update_traces(hovertemplate="<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>")
            else:
                fig = px.bar(
                    df_chart,
                    x=location_col,
                    y=metric_col,
                    title=f"{metric_choice} by {level_choice} (Top 20)",
                    labels={metric_col: metric_choice, location_col: level_choice},
                    color=metric_col,
                    color_continuous_scale="Viridis",
                )

            fig.update_layout(
                xaxis_tickangle=-45,
                showlegend=True,
                margin=dict(l=60, r=40, t=80, b=120),
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(family="Segoe UI"),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            display_cols = [c for c in [location_col, "state_name", "county_name", "district_name", "total_schools", "total_students", "total_teachers", "students_per_school", "ptr"] if c in df_map.columns]
            st.dataframe(df_map[display_cols], use_container_width=True, hide_index=True)
            _export_buttons(df_map, export_prefix)

    with tabs[1]:
        perf_state = st.selectbox("Select State (All for National)", ["All"] + _states(), index=0, key="us_perf_state")
        perf_filters = {"state": perf_state, "districts": [], "school_levels": [], "charter": "All", "virtual": "All"}
        perf = _state_dashboard_kpis(perf_filters)

        total_schools = float(perf.get("total_schools") or 0)
        total_students = float(perf.get("total_students") or 0)
        total_teachers = float(perf.get("total_teachers") or 0)
        students_per_school = round(total_students / total_schools, 2) if total_schools > 0 else None
        teachers_per_school = round(total_teachers / total_schools, 2) if total_schools > 0 else None

        st.markdown("#### 📊 Key Performance Indicators")
        k1, k2, k3 = st.columns(3)
        k4, k5, k6 = st.columns(3)
        k1.metric("Total Schools", _fmt_int(total_schools))
        k2.metric("Total Students", _fmt_int(total_students))
        k3.metric("Total Teachers", _fmt_int(total_teachers))
        k4.metric("PTR", _fmt_ptr(perf.get("ptr")))
        k5.metric("Students per School", _fmt_float(students_per_school, 2))
        k6.metric("Teachers per School", _fmt_float(teachers_per_school, 2))

        aux1, aux2 = st.columns(2)
        with aux1:
            st.caption(f"Schools with Enrollment: {_fmt_int(perf.get('schools_with_enrollment'))}")
        with aux2:
            st.caption(f"Districts Covered: {_fmt_int(perf.get('total_districts'))}")

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

    _render_footer()

