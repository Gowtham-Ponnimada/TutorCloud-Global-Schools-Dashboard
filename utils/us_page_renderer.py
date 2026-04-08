from __future__ import annotations

import io
import os
from decimal import Decimal
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



def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered



def _pretty_text_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if not isinstance(value, str):
        return value
    cleaned = " ".join(value.split())
    if not cleaned:
        return cleaned
    if cleaned.isupper() and any(ch.isalpha() for ch in cleaned) and len(cleaned) > 3:
        return cleaned.title()
    return cleaned



def _pretty_col_name(col: str) -> str:
    name = str(col).replace("_", " ").strip().title()
    replacements = {
        "Ptr": "PTR",
        "Uts": "UTs",
        "Id": "ID",
        "Zip": "ZIP",
        "Nces": "NCES",
        "Us": "US",
        "Pk": "PK",
        "Kg": "KG",
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name



def _clean_dataframe(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    out = df.copy()
    if columns is not None:
        cols = [c for c in _dedupe_keep_order(columns) if c in out.columns]
        out = out[cols]
    out = out.loc[:, ~out.columns.duplicated()].copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(_pretty_text_value)
    out = out.rename(columns=lambda c: _pretty_col_name(c))
    return out



def _render_dataframe(df: pd.DataFrame, **kwargs):
    display_df = _clean_dataframe(df)
    try:
        st.dataframe(display_df, **kwargs)
    except Exception:
        fallback_df = display_df.copy()
        fallback_df = fallback_df.loc[:, ~fallback_df.columns.duplicated()].copy()
        for col in fallback_df.columns:
            fallback_df[col] = fallback_df[col].map(
                lambda v: float(v) if isinstance(v, Decimal) else _pretty_text_value(v)
            )
        st.dataframe(fallback_df, **kwargs)


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


def _us_school_level_label(value):
    value = "" if value is None else str(value).strip()
    return {"1": "Elementary", "2": "Secondary", "3": "Combined"}.get(value, value or "Unknown")


def _us_school_type_label(value):
    value = "" if value is None else str(value).strip()
    return {
        "1": "Regular Elementary or Secondary",
        "2": "Montessori",
        "3": "Special Program Emphasis",
        "4": "Special Education",
        "5": "Vocational/Technical",
        "6": "Alternative",
        "7": "Early Childhood Program/Day Care Center",
        "8": "Other / Unspecified (8)",
        "9": "Other / Unspecified (9)",
    }.get(value, value or "Unknown")



def _delivery_models(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "delivery_model IS NOT NULL", "BTRIM(delivery_model) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT delivery_model FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY delivery_model"
    return _distinct_values(sql, params, "delivery_model")


def _management_types(state_name: str = "All", district_name: str = "All") -> list[str]:
    clauses = ["school_year = %s", "management_type IS NOT NULL", "BTRIM(management_type) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != "All":
        clauses.append("state_name = %s")
        params.append(state_name)
    if district_name and district_name != "All":
        clauses.append("district_name = %s")
        params.append(district_name)
    sql = f"SELECT DISTINCT management_type FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY management_type"
    return _distinct_values(sql, params, "management_type")



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

        delivery_opts = ["All"] + _delivery_models(state, district)
        delivery_model = st.selectbox("School Type", delivery_opts, index=0, key="us_delivery_model")

        management_opts = ["All"] + _management_types(state, district)
        management_index = management_opts.index("Govt") if "Govt" in management_opts else 0
        management_type = st.selectbox("School Management", management_opts, index=management_index, key="us_management_type")

        school_type_opts = _school_types(state, district)
        school_types = st.multiselect("Institution Type", school_type_opts, key="us_school_types")

        district_type_opts = _district_types(state)
        district_types = st.multiselect("District Type", district_type_opts, key="us_district_types")

        level_opts = _school_levels(state, district)
        school_levels = st.multiselect("School Category", level_opts, key="us_levels")

        return {
            "state": state,
            "district": district,
            "districts": [district] if district != "All" else [],
            "cities": cities,
            "delivery_model": delivery_model,
            "management_type": management_type,
            "school_levels": school_levels,
            "school_types": school_types,
            "district_types": district_types,
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
    delivery_model = filters.get("delivery_model")
    if delivery_model and delivery_model != "All":
        clauses.append(f"COALESCE({alias}.delivery_model, 'Unknown') = %s")
        params.append(delivery_model)
    management_type = filters.get("management_type")
    if management_type and management_type != "All":
        clauses.append(f"COALESCE({alias}.management_type, 'Govt') = %s")
        params.append(management_type)
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
    return " WHERE " + " AND ".join(clauses), params


def _export_buttons(
    df: pd.DataFrame,
    prefix: str,
    csv_label: str = "📥 Download CSV",
    excel_label: str = "📊 Download Excel",
):
    if df is None or df.empty:
        return
    export_df = _clean_dataframe(df)
    csv_data = export_df.to_csv(index=False).encode("utf-8")
    with io.BytesIO() as bio:
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            export_df.to_excel(writer, index=False, sheet_name="data")
        xlsx_data = bio.getvalue()
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(csv_label, csv_data, f"{prefix}.csv", "text/csv", use_container_width=True)
    with c2:
        st.download_button(
            excel_label,
            xlsx_data,
            f"{prefix}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def _plot_bar(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v", color: str | None = None):
    if df is None or df.empty:
        st.info(f"No data available for {title}.")
        return
    plot_df = df.copy()
    for col in {x, y, color}:
        if col and col in plot_df.columns and plot_df[col].dtype == object:
            plot_df[col] = plot_df[col].map(_pretty_text_value)
    fig = px.bar(
        plot_df,
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
        WHEN g.grade = 'PK' THEN 0
        WHEN g.grade = 'KG' THEN 1
        WHEN g.grade ~ '^[0-9]+$' THEN 2
        WHEN g.grade IN ('UG','AE') THEN 3
        ELSE 4
      END,
      CASE WHEN g.grade ~ '^[0-9]+$' THEN g.grade::int ELSE 999 END,
      g.grade
    """
    return _q(sql, params)



def _grade_gender_enrollment(filters: dict) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    sql = f"""
    SELECT
        g.grade,
        CASE
            WHEN UPPER(COALESCE(g.sex, '')) IN ('M', 'MALE', 'BOY', 'BOYS') THEN 'Boys'
            WHEN UPPER(COALESCE(g.sex, '')) IN ('F', 'FEMALE', 'GIRL', 'GIRLS') THEN 'Girls'
            ELSE NULL
        END AS gender,
        SUM(g.student_count) AS student_count
    FROM {SCHEMA}.fact_grade_gender_enrollment g
    JOIN {SCHEMA}.dim_schools ds
      ON ds.school_id = g.school_id AND ds.school_year = g.school_year
    {where}
      AND g.total_indicator = 'Education Unit Total'
    GROUP BY g.grade, 2
    HAVING CASE
            WHEN UPPER(COALESCE(g.sex, '')) IN ('M', 'MALE', 'BOY', 'BOYS') THEN 'Boys'
            WHEN UPPER(COALESCE(g.sex, '')) IN ('F', 'FEMALE', 'GIRL', 'GIRLS') THEN 'Girls'
            ELSE NULL
        END IS NOT NULL
    ORDER BY
      CASE
        WHEN g.grade = 'PK' THEN 0
        WHEN g.grade = 'KG' THEN 1
        WHEN g.grade ~ '^[0-9]+$' THEN 2
        WHEN g.grade IN ('UG','AE') THEN 3
        ELSE 4
      END,
      CASE WHEN g.grade ~ '^[0-9]+$' THEN g.grade::int ELSE 999 END,
      g.grade,
      gender
    """
    return _q(sql, params)


def _district_kpi_table(filters: dict, limit: int = 50) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    params = params + [limit]
    sql = f"""
    SELECT
        COALESCE(ds.district_name, 'Unknown') AS district_name,
        COUNT(DISTINCT ds.school_id) AS total_schools,
        COUNT(DISTINCT CASE WHEN f.total_students IS NOT NULL THEN ds.school_id END) AS schools_with_enrollment,
        COALESCE(SUM(f.total_students), 0) AS total_students,
        COALESCE(SUM(f.total_teachers), 0) AS total_teachers,
        CASE
            WHEN COALESCE(SUM(f.total_teachers), 0) > 0
            THEN ROUND(SUM(f.total_students)::numeric / SUM(f.total_teachers), 2)
        END AS ptr
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id
     AND f.school_year = ds.school_year
    {where}
    GROUP BY 1
    ORDER BY total_schools DESC NULLS LAST, district_name
    LIMIT %s
    """
    return _q(sql, params)

def _city_kpi_table(filters: dict, limit: int = 100) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    params = params + [limit]
    sql = f"""
    SELECT
        COALESCE(ds.city, 'Unknown') AS city,
        COUNT(DISTINCT ds.school_id) AS total_schools,
        COUNT(DISTINCT CASE WHEN f.total_students IS NOT NULL THEN ds.school_id END) AS schools_with_enrollment,
        COALESCE(SUM(f.total_students), 0) AS total_students,
        COALESCE(SUM(f.total_teachers), 0) AS total_teachers,
        CASE WHEN COALESCE(SUM(f.total_teachers), 0) > 0 THEN ROUND(SUM(f.total_students)::numeric / SUM(f.total_teachers), 2) END AS ptr
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    {where}
    GROUP BY 1
    ORDER BY total_schools DESC NULLS LAST, city
    LIMIT %s
    """
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
        f.total_students,
        f.total_teachers,
        f.ptr
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
               schools_with_enrollment
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
    params: list = [school_year]
    where = ["ds.school_year = %s", "NULLIF(BTRIM(ds.county_name), '') IS NOT NULL"]
    if state_name and state_name != "All":
        where.append("ds.state_name = %s")
        params.append(state_name)

    location_expr = "ds.county_name" if state_name != "All" else "ds.county_name || ', ' || ds.state_name"

    sql = f"""
    SELECT
        ds.state_name,
        ds.county_name,
        {location_expr} AS location_name,
        COUNT(DISTINCT ds.school_id) AS total_schools,
        COALESCE(SUM(f.total_students), 0) AS total_students,
        COALESCE(SUM(f.total_teachers), 0) AS total_teachers,
        CASE WHEN COALESCE(SUM(f.total_teachers), 0) > 0 THEN ROUND(SUM(f.total_students)::numeric / SUM(f.total_teachers), 2) END AS ptr,
        CASE WHEN COUNT(DISTINCT ds.school_id) > 0 THEN ROUND(SUM(f.total_students)::numeric / COUNT(DISTINCT ds.school_id), 2) END AS students_per_school
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
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
               schools_with_enrollment
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
               schools_with_enrollment
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
        "Location (City)": ("ds.city", "city"),
        "School Type": ("ds.delivery_model", "school_type"),
        "Institution Type": ("ds.sch_type_text", "institution_type"),
        "School Management": ("ds.management_type", "management_type"),
        "District Type": ("dd.lea_type_text", "district_type"),
        "School Category": ("ds.school_level", "school_category"),
    }
    metric_map = {
        "Schools": "COUNT(DISTINCT ds.school_id) AS total_schools",
        "Students": "COALESCE(SUM(f.total_students), 0) AS total_students",
        "Teachers": "COALESCE(SUM(f.total_teachers), 0) AS total_teachers",
        "PTR": "CASE WHEN COALESCE(SUM(f.total_teachers), 0) > 0 THEN ROUND(SUM(f.total_students) / SUM(f.total_teachers), 2) END AS ptr",
        "Students/School": "CASE WHEN COUNT(DISTINCT ds.school_id) > 0 THEN ROUND(SUM(f.total_students) / COUNT(DISTINCT ds.school_id), 2) END AS students_per_school",
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
    LEFT JOIN {SCHEMA}.dim_districts dd ON dd.district_id = ds.district_id AND dd.school_year = ds.school_year
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
    st.info("Public metrics use NCES CCD 2024–2025 universe counts. Private metrics use NCES PSS 2021–2022 PFNLWT-weighted estimates. Combined totals are mixed-year and explicitly tagged.")

    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c1.metric("TOTAL STATES/UTs", _fmt_int(summary.get("total_states")))
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
    st.markdown("<div class='us-subtitle'>Comprehensive state-level analysis with advanced US-equivalent filters.</div>", unsafe_allow_html=True)
    if filters.get("management_type") in ("All", "Private"):
        st.info("School Management includes NCES PSS private-school data from 2021–2022. Public-school data remains CCD 2024–2025. Grade-level enrollment detail remains public-only for now.")
    if filters.get("management_type") in ("All", "Private"):
        st.info("School Management uses NCES CCD 2024–2025 universe counts for Govt/Public schools and NCES PSS 2021–2022 PFNLWT-weighted estimates for Private schools. Grade-level enrollment detail remains public-only for now.")

    k = _state_dashboard_kpis(filters)
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c1.metric("TOTAL SCHOOLS", _fmt_int(k.get("total_schools")))
    c2.metric("SCHOOLS WITH ENROLLMENT", _fmt_int(k.get("schools_with_enrollment")))
    c3.metric("TOTAL DISTRICTS", _fmt_int(k.get("total_districts")))
    c4.metric("STATE PTR", _fmt_ptr(k.get("ptr")))
    c5.metric("TOTAL STUDENTS", _fmt_int(k.get("total_students")))
    c6.metric("TOTAL TEACHERS", _fmt_int(k.get("total_teachers")))

    st.markdown("### 📚 Grade-Level Enrollment (Boys vs Girls)")
    enrollment_df = _grade_enrollment(filters)
    grade_gender_df = _grade_gender_enrollment(filters)
    chart_left, chart_right = st.columns(2)
    with chart_left:
        if not grade_gender_df.empty:
            grade_order = ["PK", "KG", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "UG", "AE"]
            display_map = {"PK": "Pre-K", "KG": "KG", "UG": "Ungraded", "AE": "Adult Ed"}
            chart_df = grade_gender_df.copy()
            chart_df["grade_display"] = chart_df["grade"].map(lambda g: display_map.get(g, str(g)))
            ordered_display = [display_map.get(g, g) for g in grade_order if g in chart_df["grade"].astype(str).unique()]
            fig = px.bar(
                chart_df,
                x="grade_display",
                y="student_count",
                color="gender",
                barmode="group",
                title="Grade-Level Enrollment (Boys vs Girls)",
                category_orders={"grade_display": ordered_display, "gender": ["Boys", "Girls"]},
                color_discrete_map={"Boys": "#3498db", "Girls": "#e74c3c"},
                labels={"grade_display": "Grade", "student_count": "Students", "gender": "Gender"},
            )
            fig.update_layout(
                paper_bgcolor="white",
                plot_bgcolor="white",
                margin=dict(l=10, r=10, t=55, b=10),
                font=dict(family="Segoe UI"),
                legend_title_text="",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            _plot_bar(enrollment_df, "grade", "total_students", "Grade-wise Enrollment")
    with chart_right:
        city_mix_df = _schools_by_city(filters)
        _plot_bar(city_mix_df, "city", "school_count", "Top Cities by School Count", orientation="h")
    if not enrollment_df.empty:
        _render_dataframe(
            enrollment_df.rename(columns={"grade": "Grade", "total_students": "Total Students"}),
            use_container_width=True,
            hide_index=True,
        )
        _export_buttons(enrollment_df, "us_grade_enrollment_2024_2025")

    st.markdown("### 📍 District-Level PTR Analysis")
    district_df = _district_kpi_table(filters, 100)
    if not district_df.empty:
        district_chart = district_df.copy()
        if "ptr" in district_chart.columns:
            district_chart = district_chart[district_chart["ptr"].notna()].copy()
        if not district_chart.empty:
            fig_district = px.bar(
                district_chart.head(20),
                x="district_name",
                y="ptr",
                title="District-Level PTR Analysis (Top 20)",
                labels={"district_name": "District", "ptr": "PTR"},
                color="ptr",
                color_continuous_scale="RdYlGn_r",
                custom_data=["ptr_formatted"],
            )
            fig_district.update_traces(
                hovertemplate="<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>"
            )
            fig_district.update_layout(xaxis_tickangle=-45, margin=dict(l=60, r=40, t=80, b=120))
            st.plotly_chart(fig_district, use_container_width=True, config={"displayModeBar": False})
        display_district_df = district_df[[c for c in ["district_name", "total_schools", "total_students", "total_teachers", "ptr"] if c in district_df.columns]].copy()
        display_district_df.columns = ["District", "Total Schools", "Total Students", "Total Teachers", "PTR"]
        if "PTR" in display_district_df.columns:
            display_district_df["PTR"] = display_district_df["PTR"].apply(_fmt_ptr)
        _render_dataframe(display_district_df, use_container_width=True, hide_index=True)
        _export_buttons(display_district_df, "us_district_kpis_2024_2025")
    else:
        st.info("No district-level data available for the selected filters.")

    if filters.get("district") and filters.get("district") != "All":
        st.markdown(f"### 🏘️ City-Level PTR Analysis: {filters.get('district')}")
        city_df = _city_kpi_table(filters, 100)
        if not city_df.empty:
            city_chart = city_df.copy()
            if "ptr" in city_chart.columns:
                city_chart = city_chart[city_chart["ptr"].notna()].copy()
            if not city_chart.empty:
                fig_city = px.bar(
                    city_chart.head(20),
                    x="city",
                    y="ptr",
                    title="City-Level PTR Analysis (Top 20)",
                    labels={"city": "City", "ptr": "PTR"},
                    color="ptr",
                    color_continuous_scale="RdYlGn_r",
                    custom_data=["ptr_formatted"],
                )
                fig_city.update_traces(
                    hovertemplate="<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>"
                )
                fig_city.update_layout(xaxis_tickangle=-45, margin=dict(l=60, r=40, t=80, b=120))
                st.plotly_chart(fig_city, use_container_width=True, config={"displayModeBar": False})
            display_city_df = city_df[[c for c in ["city", "total_schools", "total_students", "total_teachers", "ptr"] if c in city_df.columns]].copy()
            display_city_df.columns = ["City", "Total Schools", "Total Students", "Total Teachers", "PTR"]
            if "PTR" in display_city_df.columns:
                display_city_df["PTR"] = display_city_df["PTR"].apply(_fmt_ptr)
            _render_dataframe(display_city_df, use_container_width=True, hide_index=True)
            _export_buttons(display_city_df, "us_city_kpis_2024_2025")
        else:
            st.info("No city-level data available for the selected district.")

    st.markdown("### 🏫 School Directory")
    mix = _school_level_mix(filters)
    if not mix.empty:
        _render_dataframe(
            mix.rename(columns={"school_level": "School Level", "school_count": "School Count"}),
            use_container_width=True,
            hide_index=True,
        )
        _export_buttons(mix, "us_school_level_mix_2024_2025")

    directory_df = _directory_table(filters, 1000)
    _render_dataframe(directory_df, use_container_width=True, height=520, hide_index=True)
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
    st.info("School Management defaults to Govt. Private-school rows use NCES PSS 2021–2022; public-school rows use CCD 2024–2025.")
    if selected_year != DASHBOARD_YEAR:
        st.info("US analytics is currently backed by the loaded 2024–2025 NCES dataset. Additional years will appear here after they are ingested.")

    tabs = st.tabs(["🗺️ Geographic Maps", "🎯 Performance Metrics", "🔍 Comparative Analysis", "📝 Custom Reports"])

    with tabs[0]:
        st.markdown("### 🗺️ Geographic Heatmaps")
        st.markdown("Interactive maps showing PTR, enrollment density by state/district")
        col1, col2 = st.columns([1, 3])
        with col1:
            metric_choice = st.selectbox(
                "Select Metric to Visualize",
                ["PTR (Pupil-Teacher Ratio)", "Students per School", "Total Students", "Total Schools"],
                key="us_map_metric",
            )
        with col2:
            level = st.radio("Level", ["State", "District"], horizontal=True, key="us_map_level")

        if level == "State":
            df_map = _state_metric_frame(selected_year).rename(columns={"state_name": "state", "ptr": "ptr", "students_per_school": "students_per_school"})
            location_col = "state"
        else:
            states = _states()
            selected_state = st.selectbox("Select State", states, key="us_map_state_select") if states else None
            df_map = _district_metric_frame(selected_state, selected_year).rename(columns={"location_name": "district"}) if selected_state else pd.DataFrame()
            location_col = "district"

        metric_map = {
            "PTR (Pupil-Teacher Ratio)": "ptr",
            "Students per School": "students_per_school",
            "Total Students": "total_students",
            "Total Schools": "total_schools",
        }
        metric_col = metric_map[metric_choice]
        if not df_map.empty and metric_col in df_map.columns:
            df_chart = df_map.sort_values(metric_col, ascending=False).head(20).copy()
            if metric_col == "ptr":
                df_chart["ptr_formatted"] = df_chart["ptr"].apply(_fmt_ptr)
                fig = px.bar(
                    df_chart,
                    x=location_col,
                    y=metric_col,
                    title=f"{metric_choice} by {level} (Top 20)",
                    labels={metric_col: metric_choice, location_col: level},
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
                    title=f"{metric_choice} by {level} (Top 20)",
                    labels={metric_col: metric_choice, location_col: level},
                    color=metric_col,
                    color_continuous_scale="Viridis",
                )
            fig.update_layout(xaxis_tickangle=-45, showlegend=True, margin=dict(l=60, r=40, t=80, b=120))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            if "ptr" in df_map.columns:
                df_display = df_map.copy()
                df_display["ptr"] = df_display["ptr"].apply(_fmt_ptr)
            else:
                df_display = df_map
            _render_dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.warning("No data available for selected filters")

    with tabs[1]:
        filter_state = st.selectbox("Select State (All for National)", ["All"] + _states(), key="us_perf_state_exact")
        if filter_state != "All":
            districts = _districts(filter_state)
            filter_district = st.selectbox("Select District (All for State)", ["All"] + districts, key="us_perf_district_exact")
        else:
            filter_district = "All"

        if filter_state == "All":
            perf_df = _state_metric_frame(selected_year)
            agg = {
                "total_schools": perf_df["total_schools"].sum() if "total_schools" in perf_df.columns else 0,
                "total_students": perf_df["total_students"].sum() if "total_students" in perf_df.columns else 0,
                "total_teachers": perf_df["total_teachers"].sum() if "total_teachers" in perf_df.columns else 0,
            }
        elif filter_district == "All":
            perf_df = _district_metric_frame(filter_state, selected_year)
            agg = {
                "total_schools": perf_df["total_schools"].sum() if "total_schools" in perf_df.columns else 0,
                "total_students": perf_df["total_students"].sum() if "total_students" in perf_df.columns else 0,
                "total_teachers": perf_df["total_teachers"].sum() if "total_teachers" in perf_df.columns else 0,
            }
        else:
            perf_df = _district_metric_frame(filter_state, selected_year)
            perf_df = perf_df[perf_df["location_name"].str.upper() == filter_district.upper()] if not perf_df.empty else pd.DataFrame()
            row = perf_df.iloc[0].to_dict() if not perf_df.empty else {}
            agg = {
                "total_schools": row.get("total_schools", 0),
                "total_students": row.get("total_students", 0),
                "total_teachers": row.get("total_teachers", 0),
            }
        ptr = round(float(agg["total_students"]) / float(agg["total_teachers"])) if float(agg["total_teachers"] or 0) > 0 else None
        students_per_school = round(float(agg["total_students"]) / float(agg["total_schools"]), 2) if float(agg["total_schools"] or 0) > 0 else None
        teachers_per_school = round(float(agg["total_teachers"]) / float(agg["total_schools"]), 2) if float(agg["total_schools"] or 0) > 0 else None
        st.markdown("#### 📊 Key Performance Indicators")
        k1, k2, k3 = st.columns(3)
        k4, k5, k6 = st.columns(3)
        k1.metric("Total Schools", _fmt_int(agg["total_schools"]))
        k2.metric("Total Students", _fmt_int(agg["total_students"]))
        k3.metric("Total Teachers", _fmt_int(agg["total_teachers"]))
        k4.metric("PTR", _fmt_ptr(ptr))
        k5.metric("Students per School", _fmt_float(students_per_school, 2))
        k6.metric("Teachers per School", _fmt_float(teachers_per_school, 2))
        _render_dataframe(perf_df if not perf_df.empty else pd.DataFrame(), use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown("### 🔍 Comparative Analysis Tool")
        st.markdown("Compare two locations side-by-side across all key metrics")
        comp_level = st.radio("Comparison Level", ["State vs State", "District vs District"], horizontal=True, key="us_comp_level_exact")
        col1, col2 = st.columns(2)
        if comp_level == "State vs State":
            states = _states()
            with col1:
                st.markdown("#### 📍 Location 1")
                left_state = st.selectbox("State", states, key="us_comp_state1_exact")
            with col2:
                st.markdown("#### 📍 Location 2")
                right_state = st.selectbox("State", states, key="us_comp_state2_exact")
            if st.button("🔄 Compare", type="primary", key="us_comp_btn_exact"):
                cmp_df = _comparison_frame(left_state, right_state)
                _render_dataframe(cmp_df, use_container_width=True, hide_index=True)
                _export_buttons(cmp_df, "us_comparison_exact", csv_label="📥 Download Comparison CSV", excel_label="📊 Download Excel")
        else:
            states = _states()
            with col1:
                st.markdown("#### 📍 Location 1")
                left_state = st.selectbox("State", states, key="us_comp_dist_state1_exact")
                left_district = st.selectbox("District", _districts(left_state), key="us_comp_district1_exact")
            with col2:
                st.markdown("#### 📍 Location 2")
                right_state = st.selectbox("State", states, key="us_comp_dist_state2_exact")
                right_district = st.selectbox("District", _districts(right_state), key="us_comp_district2_exact")
            if st.button("🔄 Compare", type="primary", key="us_comp_dist_btn_exact"):
                cmp_df = _district_comparison_frame(left_state, left_district, right_state, right_district)
                _render_dataframe(cmp_df, use_container_width=True, hide_index=True)
                _export_buttons(cmp_df, "us_district_comparison_exact", csv_label="📥 Download Comparison CSV", excel_label="📊 Download Excel")

    with tabs[3]:
        st.markdown("### 📝 Custom Report Builder")
        st.markdown("Build custom reports with flexible dimensions and metrics")
        st.markdown("#### Step 1: Select Dimensions")
        dimensions = st.multiselect(
            "Choose grouping dimensions",
            ["State", "District", "Location (City)", "School Type", "Institution Type", "District Type", "School Category"],
            default=["State"],
            key="us_report_dims_exact",
        )
        st.markdown("#### Step 2: Select Metrics")
        metrics = st.multiselect(
            "Choose metrics to include",
            ["Schools", "Students", "Teachers", "PTR", "Students/School"],
            default=["Schools", "Students", "PTR"],
            key="us_report_metrics_exact",
        )
        report_state = st.selectbox("Filter by State", ["All"] + _states(), key="us_report_state_exact")
        report_delivery_model = st.selectbox("Filter by School Type", ["All"] + _delivery_models(report_state), key="us_report_school_type_exact")
        report_management_opts = ["All"] + _management_types(report_state)
        report_management_type = st.selectbox("Filter by School Management", report_management_opts, index=report_management_opts.index("Govt") if "Govt" in report_management_opts else 0, key="us_report_management_exact")
        report_districts = st.multiselect("Filter by District", _districts(report_state), key="us_report_districts_exact")
        report_levels = st.multiselect("Filter by School Category", _school_levels(report_state), key="us_report_levels_exact")
        if st.button("📊 Generate Report", type="primary", key="us_report_generate_exact"):
            if not dimensions or not metrics:
                st.warning("Please select at least one dimension and one metric")
            else:
                report_filters = {
                    "state": report_state,
                    "delivery_model": report_delivery_model,
                    "management_type": report_management_type,
                    "districts": report_districts,
                    "school_levels": report_levels,
                }
                report_df = _custom_report(dimensions, metrics, report_filters)
                _render_dataframe(report_df, use_container_width=True, height=520, hide_index=True)
                _export_buttons(report_df, "us_custom_report_exact", csv_label="📥 Download CSV", excel_label="📊 Download Excel")

    _render_footer()

def _weight_expr(alias: str = "ds") -> str:
    return f"CASE WHEN COALESCE({alias}.management_type, 'Govt') = 'Private' THEN COALESCE({alias}.pss_final_weight, 1::numeric) ELSE 1::numeric END"

def _weighted_school_sum_raw(alias: str = "ds") -> str:
    return f"SUM({_weight_expr(alias)})"

def _weighted_students_sum_raw(ds_alias: str = "ds", fact_alias: str = "f") -> str:
    return f"SUM(({_weight_expr(ds_alias)}) * COALESCE({fact_alias}.total_students, 0)::numeric)"

def _weighted_teachers_sum_raw(ds_alias: str = "ds", fact_alias: str = "f") -> str:
    return f"SUM(({_weight_expr(ds_alias)}) * COALESCE({fact_alias}.total_teachers, 0)::numeric)"

def _weighted_schools_with_enrollment_raw(ds_alias: str = "ds", fact_alias: str = "f") -> str:
    return f"SUM(CASE WHEN {fact_alias}.total_students IS NOT NULL THEN {_weight_expr(ds_alias)} ELSE 0::numeric END)"

def _national_summary() -> dict:
    school_sum = _weighted_school_sum_raw("ds")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    sql = f'''
    SELECT
        COUNT(DISTINCT ds.state_name) AS total_states,
        ROUND({school_sum}, 0) AS total_schools,
        COUNT(DISTINCT ds.district_id) AS total_districts,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr,
        CASE WHEN COALESCE({school_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({school_sum}, 0), 2) END AS students_per_school
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    WHERE ds.school_year = %s
    '''
    df = _q(sql, [DASHBOARD_YEAR])
    if df.empty:
        return {"total_states": 0, "total_schools": 0, "total_districts": 0, "total_students": 0, "total_teachers": 0, "ptr": None, "students_per_school": None}
    return df.iloc[0].to_dict()

def _top_states_by_schools(limit: int = 10) -> pd.DataFrame:
    school_sum = _weighted_school_sum_raw("ds")
    sql = f'''
    SELECT
        ds.state_name,
        ROUND({school_sum}, 0) AS total_schools
    FROM {SCHEMA}.dim_schools ds
    WHERE ds.school_year = %s
    GROUP BY ds.state_name
    ORDER BY total_schools DESC NULLS LAST, ds.state_name
    LIMIT %s
    '''
    return _q(sql, [DASHBOARD_YEAR, limit])

def _top_states_by_students(limit: int = 20) -> pd.DataFrame:
    student_sum = _weighted_students_sum_raw("ds", "f")
    sql = f'''
    SELECT
        ds.state_name,
        ROUND({student_sum}, 0) AS total_students
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    WHERE ds.school_year = %s
    GROUP BY ds.state_name
    ORDER BY total_students DESC NULLS LAST, ds.state_name
    LIMIT %s
    '''
    return _q(sql, [DASHBOARD_YEAR, limit])

def _school_level_mix(filters: dict | None = None) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    school_sum = _weighted_school_sum_raw("ds")
    sql = f'''
    SELECT
        COALESCE(ds.school_level, 'Unknown') AS school_level,
        ROUND({school_sum}, 0) AS school_count
    FROM {SCHEMA}.dim_schools ds
    {where}
    GROUP BY 1
    ORDER BY school_count DESC, school_level
    '''
    return _q(sql, params)

def _state_dashboard_kpis(filters: dict) -> dict:
    where, params = _base_where(filters, "ds")
    school_sum = _weighted_school_sum_raw("ds")
    enr_school_sum = _weighted_schools_with_enrollment_raw("ds", "f")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    sql = f'''
    SELECT
        ROUND({school_sum}, 0) AS total_schools,
        ROUND({enr_school_sum}, 0) AS schools_with_enrollment,
        COUNT(DISTINCT ds.district_id) AS total_districts,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    {where}
    '''
    df = _q(sql, params)
    if df.empty:
        return {"total_schools": 0, "schools_with_enrollment": 0, "total_districts": 0, "total_students": 0, "total_teachers": 0, "ptr": None}
    return df.iloc[0].to_dict()

def _district_kpi_table(filters: dict, limit: int = 50) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    params = params + [limit]
    school_sum = _weighted_school_sum_raw("ds")
    enr_school_sum = _weighted_schools_with_enrollment_raw("ds", "f")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    sql = f'''
    SELECT
        COALESCE(ds.district_name, 'Unknown') AS district_name,
        ROUND({school_sum}, 0) AS total_schools,
        ROUND({enr_school_sum}, 0) AS schools_with_enrollment,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    {where}
    GROUP BY 1
    ORDER BY total_schools DESC NULLS LAST, district_name
    LIMIT %s
    '''
    return _q(sql, params)

def _city_kpi_table(filters: dict, limit: int = 100) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    params = params + [limit]
    school_sum = _weighted_school_sum_raw("ds")
    enr_school_sum = _weighted_schools_with_enrollment_raw("ds", "f")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    sql = f'''
    SELECT
        COALESCE(ds.city, 'Unknown') AS city,
        ROUND({school_sum}, 0) AS total_schools,
        ROUND({enr_school_sum}, 0) AS schools_with_enrollment,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    {where}
    GROUP BY 1
    ORDER BY total_schools DESC NULLS LAST, city
    LIMIT %s
    '''
    return _q(sql, params)

def _schools_by_city(filters: dict, limit: int = 20) -> pd.DataFrame:
    where, params = _base_where(filters, "ds")
    params = params + [limit]
    school_sum = _weighted_school_sum_raw("ds")
    sql = f'''
    SELECT
        COALESCE(ds.city, 'Unknown') AS city,
        ROUND({school_sum}, 0) AS school_count
    FROM {SCHEMA}.dim_schools ds
    {where}
    GROUP BY 1
    ORDER BY school_count DESC, city
    LIMIT %s
    '''
    return _q(sql, params)

def _state_metric_frame(school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
    school_sum = _weighted_school_sum_raw("ds")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    enr_school_sum = _weighted_schools_with_enrollment_raw("ds", "f")
    sql = f'''
    SELECT
        ds.state_name,
        ROUND({school_sum}, 0) AS total_schools,
        COUNT(DISTINCT ds.district_id) AS total_districts,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr,
        CASE WHEN COALESCE({school_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({school_sum}, 0), 2) END AS students_per_school,
        ROUND({enr_school_sum}, 0) AS schools_with_enrollment
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    WHERE ds.school_year = %s
    GROUP BY ds.state_name
    ORDER BY ds.state_name
    '''
    return _q(sql, [school_year])

def _county_metric_frame(state_name: str = "All", school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
    stage_table = f"stg_sch_directory_{_year_tag(school_year)}"
    county_col = _first_existing_column(stage_table, ["county_name", "coname", "county", "countyname", "county15", "coname15"])
    school_id_col = _first_existing_column(stage_table, ["ncessch", "school_id", "schoolid", "nces_id"])
    if not county_col or not school_id_col:
        return pd.DataFrame()

    county_expr = f"COALESCE(NULLIF(BTRIM(sd.{county_col}::text), ''), 'Unknown')"
    location_expr = county_expr if state_name != "All" else f"{county_expr} || ', ' || ds.state_name"

    params = [school_year]
    where = ["ds.school_year = %s"]
    if state_name and state_name != "All":
        where.append("ds.state_name = %s")
        params.append(state_name)

    school_sum = _weighted_school_sum_raw("ds")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")

    sql = f'''
    SELECT
        ds.state_name,
        {county_expr} AS county_name,
        {location_expr} AS location_name,
        ROUND({school_sum}, 0) AS total_schools,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr,
        CASE WHEN COALESCE({school_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({school_sum}, 0), 2) END AS students_per_school
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    LEFT JOIN {SCHEMA}.{stage_table} sd
      ON BTRIM(COALESCE(sd.{school_id_col}::text, '')) = ds.school_id
    WHERE {' AND '.join(where)}
    GROUP BY 1, 2, 3
    HAVING ROUND({school_sum}, 0) > 0
    ORDER BY total_schools DESC NULLS LAST, location_name
    '''
    return _q(sql, params)

def _district_metric_frame(state_name: str = "All", school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
    params = [school_year]
    clauses = ["ds.school_year = %s"]
    if state_name and state_name != "All":
        clauses.append("ds.state_name = %s")
        params.append(state_name)

    location_expr = "ds.district_name" if state_name != "All" else "ds.district_name || ', ' || ds.state_name"
    school_sum = _weighted_school_sum_raw("ds")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")

    sql = f'''
    SELECT
        ds.state_name,
        ds.district_name,
        {location_expr} AS location_name,
        ROUND({school_sum}, 0) AS total_schools,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr,
        CASE WHEN COALESCE({school_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({school_sum}, 0), 2) END AS students_per_school
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    WHERE {' AND '.join(clauses)}
    GROUP BY ds.state_name, ds.district_name, 3
    ORDER BY total_schools DESC NULLS LAST, ds.state_name, ds.district_name
    '''
    return _q(sql, params)

def _comparison_frame(left_state: str, right_state: str) -> pd.DataFrame:
    school_sum = _weighted_school_sum_raw("ds")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    enr_school_sum = _weighted_schools_with_enrollment_raw("ds", "f")
    sql = f'''
    SELECT
        ds.state_name,
        ROUND({school_sum}, 0) AS total_schools,
        COUNT(DISTINCT ds.district_id) AS total_districts,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr,
        ROUND({enr_school_sum}, 0) AS schools_with_enrollment
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    WHERE ds.school_year = %s AND ds.state_name = ANY(%s)
    GROUP BY ds.state_name
    ORDER BY ds.state_name
    '''
    return _q(sql, [DASHBOARD_YEAR, [left_state, right_state]])

def _district_comparison_frame(left_state: str, left_district: str, right_state: str, right_district: str) -> pd.DataFrame:
    school_sum = _weighted_school_sum_raw("ds")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    enr_school_sum = _weighted_schools_with_enrollment_raw("ds", "f")
    sql = f'''
    SELECT
        ds.state_name,
        ds.district_name,
        ROUND({school_sum}, 0) AS total_schools,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr,
        ROUND({enr_school_sum}, 0) AS schools_with_enrollment
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    WHERE ds.school_year = %s
      AND ((ds.state_name = %s AND ds.district_name = %s) OR (ds.state_name = %s AND ds.district_name = %s))
    GROUP BY ds.state_name, ds.district_name
    ORDER BY ds.state_name, ds.district_name
    '''
    return _q(sql, [DASHBOARD_YEAR, left_state, left_district, right_state, right_district])

def _custom_report(dimensions: list[str], metrics: list[str], filters: dict) -> pd.DataFrame:
    dim_map = {
        "State": ("ds.state_name", "state_name"),
        "District": ("ds.district_name", "district_name"),
        "Location (City)": ("ds.city", "city"),
        "School Type": ("ds.delivery_model", "school_type"),
        "Institution Type": ("ds.sch_type_text", "institution_type"),
        "School Management": ("ds.management_type", "management_type"),
        "District Type": ("dd.lea_type_text", "district_type"),
        "School Category": ("ds.school_level", "school_category"),
    }
    school_sum = _weighted_school_sum_raw("ds")
    student_sum = _weighted_students_sum_raw("ds", "f")
    teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    metric_map = {
        "Schools": f"ROUND({school_sum}, 0) AS total_schools",
        "Students": f"ROUND({student_sum}, 0) AS total_students",
        "Teachers": f"ROUND({teacher_sum}, 0) AS total_teachers",
        "PTR": f"CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr",
        "Students/School": f"CASE WHEN COALESCE({school_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({school_sum}, 0), 2) END AS students_per_school",
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
    sql = f'''
    SELECT {select_dims}, {select_metrics}
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    LEFT JOIN {SCHEMA}.dim_districts dd ON dd.district_id = ds.district_id AND dd.school_year = ds.school_year
    {where}
    GROUP BY {group_expr}
    ORDER BY 1, 2, 3
    LIMIT 1000
    '''
    return _q(sql, params)
# ===== end Build 3 weighted private metrics override =====



# ===== Build 4 county_name override =====
def _county_metric_frame(state_name: str = "All", school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
    params: list = [school_year]
    clauses = [
        "ds.school_year = %s",
        "NULLIF(BTRIM(COALESCE(ds.county_name::text, '')), '') IS NOT NULL"
    ]
    if state_name and state_name != "All":
        clauses.append("ds.state_name = %s")
        params.append(state_name)

    county_expr = "COALESCE(NULLIF(BTRIM(ds.county_name::text), ''), 'Unknown')"
    location_expr = county_expr if state_name != "All" else f"{county_expr} || ', ' || ds.state_name"

    try:
        school_sum = _weighted_school_sum_raw("ds")
        student_sum = _weighted_students_sum_raw("ds", "f")
        teacher_sum = _weighted_teachers_sum_raw("ds", "f")
    except Exception:
        school_sum = "COUNT(DISTINCT ds.school_id)"
        student_sum = "COALESCE(SUM(f.total_students), 0)"
        teacher_sum = "COALESCE(SUM(f.total_teachers), 0)"

    sql = f"""
    SELECT
        ds.state_name,
        {county_expr} AS county_name,
        {location_expr} AS location_name,
        ROUND({school_sum}, 0) AS total_schools,
        ROUND({student_sum}, 0) AS total_students,
        ROUND({teacher_sum}, 0) AS total_teachers,
        CASE WHEN COALESCE({teacher_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({teacher_sum}, 0), 2) END AS ptr,
        CASE WHEN COALESCE({school_sum}, 0) > 0 THEN ROUND(({student_sum}) / NULLIF({school_sum}, 0), 2) END AS students_per_school
    FROM {SCHEMA}.dim_schools ds
    LEFT JOIN {SCHEMA}.fact_school_totals f
      ON f.school_id = ds.school_id AND f.school_year = ds.school_year
    WHERE {' AND '.join(clauses)}
    GROUP BY 1, 2, 3
    HAVING ROUND({school_sum}, 0) > 0
    ORDER BY total_schools DESC NULLS LAST, location_name
    """
    return _q(sql, params)
# ===== end Build 4 county_name override =====

# === INDIA_PARITY_OVERRIDE_US ===
def _us_distinct_from_dim_schools(column: str, state_name: str = 'All', district_name: str = 'All') -> list[str]:
    if column.lower() not in _table_columns('dim_schools'):
        return []
    clauses = ['school_year = %s', f'{column} IS NOT NULL', f"BTRIM({column}) <> ''"]
    params: list = [DASHBOARD_YEAR]
    if state_name and state_name != 'All':
        clauses.append('state_name = %s')
        params.append(state_name)
    if district_name and district_name != 'All' and 'district_name' in _table_columns('dim_schools'):
        clauses.append('district_name = %s')
        params.append(district_name)
    df = _q(f"SELECT DISTINCT {column} AS value FROM {SCHEMA}.dim_schools WHERE {' AND '.join(clauses)} ORDER BY value", params)
    if df.empty or 'value' not in df.columns:
        return []
    return [str(v) for v in df['value'].tolist() if v not in (None, '')]


def _build_sidebar_filters() -> dict:
    with st.sidebar:
        st.markdown('### 🔍 Apply Filters')
        state_opts = _states()
        state = st.selectbox('🗺️ Select State', state_opts, index=0, key='us_state_exact') if state_opts else 'All'

        district_opts = ['All'] + _districts(state)
        district = st.selectbox('🏘️ Select District', district_opts, index=0, key=f'us_district_exact_{state}')

        block_opts = _us_distinct_from_dim_schools('county_name', state, district) or _cities(state, district)
        block_name = st.selectbox('📍 Select County', ['All'] + block_opts, index=0, key=f'us_block_exact_{state}_{district}')

        city_opts = _cities(state, district)
        location_value = st.selectbox('🌆 City', ['All'] + city_opts, index=0, key=f'us_location_exact_{state}_{district}_{block_name}')

        school_type_opts = _school_types(state, district)
        school_type_new = st.multiselect('📖 School Type', school_type_opts, default=[], format_func=_us_school_type_label, key=f'us_school_type_exact_{state}_{district}')

        management_opts = _management_types(state, district)
        management_default = ['Govt'] if 'Govt' in management_opts else []
        management_groups = st.multiselect('🏛️ Management Type', management_opts, default=management_default, key=f'us_management_exact_{state}_{district}')

        level_opts = _school_levels(state, district)
        school_categories = st.multiselect('📚 School Level', level_opts, default=[], format_func=_us_school_level_label, key=f'us_category_exact_{state}_{district}')

        board_opts = _district_types(state)
        boards = st.multiselect('🏛️ District Type', board_opts, default=[], help='Uses available US district-type values.', key=f'us_board_exact_{state}')

        active_filters = [state]
        for val in [district if district != 'All' else None, block_name if block_name != 'All' else None, location_value if location_value != 'All' else None]:
            if val:
                active_filters.append(val)
        active_filters.extend([f'Management: {x}' for x in management_groups])
        active_filters.extend([f'Category: {x}' for x in school_categories])
        active_filters.extend([f'School Type: {_us_school_type_label(x)}' for x in school_type_new])
        active_filters.extend([f'Board: {x}' for x in boards])
        if active_filters:
            st.markdown('---')
            st.markdown('### ✅ Active Filters')
            for item in active_filters:
                st.markdown(f'- {item}')

        return {
            'state': state,
            'district': district,
            'districts': [district] if district != 'All' else [],
            'block_name': None if block_name == 'All' else block_name,
            'location_value': None if location_value == 'All' else location_value,
            'cities': [location_value] if location_value != 'All' else [],
            'delivery_model': 'All',
            'management_type': management_groups[0] if len(management_groups) == 1 else 'All',
            'management_groups': management_groups,
            'school_levels': school_categories,
            'school_categories': school_categories,
            'school_types': school_type_new,
            'school_type_new': school_type_new,
            'district_types': boards,
            'boards': boards,
        }


def _base_where(filters: dict | None = None, alias: str = 'ds'):
    filters = filters or {}
    clauses = [f'{alias}.school_year = %s']
    params: list = [DASHBOARD_YEAR]
    if filters.get('state') and filters['state'] != 'All':
        clauses.append(f'{alias}.state_name = %s')
        params.append(filters['state'])
    districts = [x for x in (filters.get('districts') or []) if x]
    if districts:
        clauses.append(f'{alias}.district_name = ANY(%s)')
        params.append(districts)
    block_name = filters.get('block_name')
    ds_cols = _table_columns('dim_schools')
    if block_name:
        if 'county_name' in ds_cols:
            clauses.append(f"COALESCE(NULLIF(BTRIM({alias}.county_name), ''), 'Unknown') = %s")
            params.append(block_name)
        elif 'city' in ds_cols:
            clauses.append(f"COALESCE(NULLIF(BTRIM({alias}.city), ''), 'Unknown') = %s")
            params.append(block_name)
    location_value = filters.get('location_value')
    cities = [location_value] if location_value else [x for x in (filters.get('cities') or []) if x]
    if cities and 'city' in ds_cols:
        clauses.append(f'{alias}.city = ANY(%s)')
        params.append(cities)
    delivery_model = filters.get('delivery_model')
    if delivery_model and delivery_model != 'All' and 'delivery_model' in ds_cols:
        clauses.append(f"COALESCE({alias}.delivery_model, 'Unknown') = %s")
        params.append(delivery_model)
    management_groups = [x for x in (filters.get('management_groups') or []) if x]
    if management_groups and 'management_type' in ds_cols:
        clauses.append(f"COALESCE({alias}.management_type, 'Govt') = ANY(%s)")
        params.append(management_groups)
    elif filters.get('management_type') and filters['management_type'] != 'All' and 'management_type' in ds_cols:
        clauses.append(f"COALESCE({alias}.management_type, 'Govt') = %s")
        params.append(filters['management_type'])
    levels = [x for x in (filters.get('school_categories') or filters.get('school_levels') or []) if x]
    if levels and 'school_level' in ds_cols:
        clauses.append(f'{alias}.school_level = ANY(%s)')
        params.append(levels)
    school_types = [x for x in (filters.get('school_type_new') or filters.get('school_types') or []) if x]
    if school_types and 'sch_type_text' in ds_cols:
        clauses.append(f"COALESCE({alias}.sch_type_text, 'Unknown') = ANY(%s)")
        params.append(school_types)
    district_types = [x for x in (filters.get('boards') or filters.get('district_types') or []) if x]
    if district_types:
        clauses.append(f"EXISTS (SELECT 1 FROM {SCHEMA}.dim_districts dd WHERE dd.school_year = {alias}.school_year AND dd.district_id = {alias}.district_id AND COALESCE(dd.lea_type_text, 'Unknown') = ANY(%s))")
        params.append(district_types)
    return ' WHERE ' + ' AND '.join(clauses), params


def render_us_state_dashboard():
    _inject_css()
    if not _phase1_ready():
        _render_missing_data_notice()
        return

    filters = _build_sidebar_filters()
    selected_state = filters.get('state') or 'United States'
    st.markdown('<div class="main-header">📊 State Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive State-Level Analysis with Advanced Filters</div>', unsafe_allow_html=True)
    if filters.get('management_groups') and 'Private' in filters.get('management_groups', []):
        st.info('School Management uses NCES CCD 2024–2025 universe counts for Govt/Public schools and NCES PSS 2021–2022 weighted estimates for Private schools. Grade-level enrollment detail remains public-only for now.')

    k = _state_dashboard_kpis(filters)
    st.markdown(f'<div class="section-header">📊 Overview: {selected_state}</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('🏫 Total Schools', _fmt_int(k.get('total_schools')))
    with col2:
        st.metric('🎓 Schools with Enrollment', _fmt_int(k.get('schools_with_enrollment')))
    with col3:
        st.metric('🗺️ Districts', _fmt_int(k.get('total_districts')))
    with col4:
        st.metric('📊 State PTR', _fmt_ptr(k.get('ptr')))
    col5, col6 = st.columns(2)
    with col5:
        st.metric('👥 Total Students', _fmt_int(k.get('total_students')))
    with col6:
        st.metric('👨‍🏫 Total Teachers', _fmt_int(k.get('total_teachers')))

    st.markdown('<div class="section-header">📚 Grade-Level Enrollment (Boys vs Girls)</div>', unsafe_allow_html=True)
    enrollment_df = _grade_enrollment(filters)
    grade_gender_df = _grade_gender_enrollment(filters)
    chart_left, chart_right = st.columns(2)
    with chart_left:
        if not grade_gender_df.empty:
            grade_order = ['PK', 'KG', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'UG', 'AE']
            display_map = {'PK': 'Pre-K', 'KG': 'KG', 'UG': 'Ungraded', 'AE': 'Adult Ed'}
            chart_df = grade_gender_df.copy()
            chart_df['grade_display'] = chart_df['grade'].map(lambda g: display_map.get(g, str(g)))
            ordered_display = [display_map.get(g, g) for g in grade_order if g in chart_df['grade'].astype(str).unique()]
            fig = px.bar(chart_df, x='grade_display', y='student_count', color='gender', barmode='group', title='Grade-Level Enrollment (Boys vs Girls)', category_orders={'grade_display': ordered_display, 'gender': ['Boys', 'Girls']}, color_discrete_map={'Boys': '#3498db', 'Girls': '#e74c3c'}, labels={'grade_display': 'Grade', 'student_count': 'Students', 'gender': 'Gender'})
            fig.update_layout(paper_bgcolor='white', plot_bgcolor='white', margin=dict(l=10, r=10, t=55, b=10), font=dict(family='Segoe UI'), legend_title_text='')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            _plot_bar(enrollment_df, 'grade', 'total_students', 'Grade-wise Enrollment')
    with chart_right:
        city_mix_df = _schools_by_city(filters)
        _plot_bar(city_mix_df, 'city', 'school_count', 'Top Locations by School Count', orientation='h')
    if not enrollment_df.empty:
        export_enrollment_df = enrollment_df.rename(columns={'grade': 'Grade', 'total_students': 'Total Students'})
        _render_dataframe(export_enrollment_df, use_container_width=True, hide_index=True)
        _export_buttons(export_enrollment_df, 'us_grade_enrollment_2024_2025', csv_label='📥 Download CSV', excel_label='📊 Download Excel')

    st.markdown('<div class="section-header">📍 District-Level PTR Analysis</div>', unsafe_allow_html=True)
    district_df = _district_kpi_table(filters, 100)
    if not district_df.empty:
        district_chart = district_df.copy()
        if 'ptr' in district_chart.columns:
            district_chart = district_chart[district_chart['ptr'].notna()].copy()
        if not district_chart.empty:
            district_chart['ptr_formatted'] = district_chart['ptr'].apply(_fmt_ptr)
            fig_district = px.bar(district_chart.head(20), x='district_name', y='ptr', title='District PTR Comparison (Top 20 by School Count)', labels={'district_name': 'District', 'ptr': 'PTR'}, color='ptr', color_continuous_scale='RdYlGn_r', custom_data=['ptr_formatted'])
            fig_district.update_traces(hovertemplate='<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>')
            fig_district.update_layout(xaxis_tickangle=-45, margin=dict(l=60, r=40, t=80, b=120))
            st.plotly_chart(fig_district, use_container_width=True, config={'displayModeBar': False})
        display_district_df = district_df[[c for c in ['district_name', 'total_schools', 'total_students', 'total_teachers', 'ptr'] if c in district_df.columns]].copy()
        display_district_df.columns = ['District', 'Total Schools', 'Total Students', 'Total Teachers', 'PTR']
        display_district_df['PTR'] = display_district_df['PTR'].apply(_fmt_ptr)
        _render_dataframe(display_district_df, use_container_width=True, hide_index=True)
        _export_buttons(display_district_df, 'us_district_kpis_2024_2025', csv_label='📥 Download District Data (CSV)', excel_label='📊 Download Excel')
    else:
        st.info('No district-level data available for the selected filters.')

    if filters.get('district') and filters.get('district') != 'All':
        st.markdown(f'<div class="section-header">🏘️ Block/Taluk-Level PTR Analysis: {filters.get("district")}</div>', unsafe_allow_html=True)
        city_df = _city_kpi_table(filters, 100)
        if not city_df.empty:
            city_chart = city_df.copy()
            city_chart = city_chart[city_chart['ptr'].notna()].copy() if 'ptr' in city_chart.columns else city_chart
            if not city_chart.empty:
                city_chart['ptr_formatted'] = city_chart['ptr'].apply(_fmt_ptr)
                fig_city = px.bar(city_chart.head(20), x='city', y='ptr', title=f'Block/Taluk PTR Comparison in {filters.get("district")} (Top 20)', labels={'city': 'Block/Taluk', 'ptr': 'PTR'}, color='ptr', color_continuous_scale='RdYlGn_r', custom_data=['ptr_formatted'])
                fig_city.update_traces(hovertemplate='<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>')
                fig_city.update_layout(xaxis_tickangle=-45, margin=dict(l=60, r=40, t=80, b=120))
                st.plotly_chart(fig_city, use_container_width=True, config={'displayModeBar': False})
            display_city_df = city_df[[c for c in ['city', 'total_schools', 'total_students', 'total_teachers', 'ptr'] if c in city_df.columns]].copy()
            display_city_df.columns = ['Block/Taluk', 'Total Schools', 'Total Students', 'Total Teachers', 'PTR']
            display_city_df['PTR'] = display_city_df['PTR'].apply(_fmt_ptr)
            _render_dataframe(display_city_df, use_container_width=True, hide_index=True)
            _export_buttons(display_city_df, 'us_city_kpis_2024_2025', csv_label='📥 Download Block/Taluk Data (CSV)', excel_label='📊 Download Excel')
        else:
            st.info('No block-level data available for the selected district.')

    st.markdown('<div class="section-header">🏫 School Directory</div>', unsafe_allow_html=True)
    directory_df = _directory_table(filters, 1000)
    _render_dataframe(directory_df, use_container_width=True, height=520, hide_index=True)
    _export_buttons(directory_df, 'us_directory_extract_2024_2025', csv_label='📥 Download CSV', excel_label='📊 Download Excel')
    _render_footer()
