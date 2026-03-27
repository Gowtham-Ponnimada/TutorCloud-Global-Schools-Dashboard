from pathlib import Path

TARGET = Path("utils/us_page_renderer.py")

old_imports = '''import io
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
'''

new_imports = '''import io
import os
from decimal import Decimal
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
'''

insert_after_fmt_ptr = '''def _fmt_ptr(v) -> str:
    try:
        if v is None or pd.isna(v) or float(v) <= 0:
            return "N/A"
        return f"{int(round(float(v)))}:1"
    except Exception:
        return "N/A"
'''

helper_block = '''def _fmt_ptr(v) -> str:
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
    st.dataframe(display_df, **kwargs)
'''

old_plot_bar = '''def _plot_bar(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v", color: str | None = None):
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
'''

new_plot_bar = '''def _plot_bar(df: pd.DataFrame, x: str, y: str, title: str, orientation: str = "v", color: str | None = None):
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
'''

old_export = '''def _export_buttons(
    df: pd.DataFrame,
    prefix: str,
    csv_label: str = "📥 Download CSV",
    excel_label: str = "📊 Download Excel",
):
    if df is None or df.empty:
        return
    csv_data = df.to_csv(index=False).encode("utf-8")
    with io.BytesIO() as bio:
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="data")
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
'''

new_export = '''def _export_buttons(
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
'''

old_sidebar = '''def _build_sidebar_filters() -> dict:
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
'''

new_sidebar = '''def _build_sidebar_filters() -> dict:
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

        return {
            "state": state,
            "district": district,
            "districts": [district] if district != "All" else [],
            "cities": cities,
            "school_levels": school_levels,
            "school_types": school_types,
            "district_types": district_types,
        }
'''

old_base_where = '''def _base_where(filters: dict | None = None, alias: str = "ds"):
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
'''

new_base_where = '''def _base_where(filters: dict | None = None, alias: str = "ds"):
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
    return " WHERE " + " AND ".join(clauses), params
'''

old_directory_cols = '''    SELECT
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
'''

new_directory_cols = '''    SELECT
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
'''

old_district_kpi = '''def _district_kpi_table(filters: dict, limit: int = 50) -> pd.DataFrame:
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
'''

new_district_kpi = '''def _district_kpi_table(filters: dict, limit: int = 50) -> pd.DataFrame:
    params: list = [DASHBOARD_YEAR]
    clauses = ["school_year = %s"]
    if filters.get("state") and filters["state"] != "All":
        clauses.append("state_name = %s")
        params.append(filters["state"])
    sql = f"""
    SELECT district_name, total_schools, schools_with_enrollment, total_students, total_teachers, ptr
    FROM {SCHEMA}.vw_district_kpis_2024_2025
    WHERE {' AND '.join(clauses)}
    ORDER BY total_schools DESC NULLS LAST, district_name
    LIMIT %s
    """
    params.append(limit)
    return _q(sql, params)
'''

old_state_metric = '''def _state_metric_frame(school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
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
'''

new_state_metric = '''def _state_metric_frame(school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
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
'''

old_comparison = '''def _comparison_frame(left_state: str, right_state: str) -> pd.DataFrame:
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
'''

new_comparison = '''def _comparison_frame(left_state: str, right_state: str) -> pd.DataFrame:
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
'''

old_district_comparison = '''def _district_comparison_frame(left_state: str, left_district: str, right_state: str, right_district: str) -> pd.DataFrame:
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
'''

new_district_comparison = '''def _district_comparison_frame(left_state: str, left_district: str, right_state: str, right_district: str) -> pd.DataFrame:
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
'''

old_custom_report = '''def _custom_report(dimensions: list[str], metrics: list[str], filters: dict) -> pd.DataFrame:
    dim_map = {
        "State": ("ds.state_name", "state_name"),
        "District": ("ds.district_name", "district_name"),
        "Location (City)": ("ds.city", "city"),
        "School Type": ("ds.sch_type_text", "school_type"),
        "District Type": ("dd.lea_type_text", "district_type"),
        "School Category": ("ds.school_level", "school_category"),
        "Charter": ("ds.charter_text", "charter_text"),
        "Virtual": ("ds.virtual_text", "virtual_text"),
    }
    metric_map = {
        "Schools": "COUNT(DISTINCT ds.school_id) AS total_schools",
        "Students": "COALESCE(SUM(f.total_students), 0) AS total_students",
        "Teachers": "COALESCE(SUM(f.total_teachers), 0) AS total_teachers",
        "PTR": "CASE WHEN COALESCE(SUM(f.total_teachers), 0) > 0 THEN ROUND(SUM(f.total_students) / SUM(f.total_teachers), 2) END AS ptr",
        "Students/School": "CASE WHEN COUNT(DISTINCT ds.school_id) > 0 THEN ROUND(SUM(f.total_students) / COUNT(DISTINCT ds.school_id), 2) END AS students_per_school",
    }
'''

new_custom_report = '''def _custom_report(dimensions: list[str], metrics: list[str], filters: dict) -> pd.DataFrame:
    dim_map = {
        "State": ("ds.state_name", "state_name"),
        "District": ("ds.district_name", "district_name"),
        "Location (City)": ("ds.city", "city"),
        "School Type": ("ds.sch_type_text", "school_type"),
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
'''

old_custom_ui = '''    with tabs[3]:
        st.markdown("#### 📝 Custom Reports")
        dimensions = st.multiselect(
            "Choose dimensions",
            ["State", "District", "Location (City)", "School Type", "District Type", "School Category", "Charter", "Virtual"],
            default=["State"],
            key="us_report_dims",
        )
        metrics = st.multiselect(
            "Choose metrics",
            ["Schools", "Students", "Teachers", "PTR", "Students/School"],
            default=["Schools", "Students", "PTR"],
            key="us_report_metrics",
        )
        report_state = st.selectbox("Filter by State", ["All"] + _states(), index=0, key="us_report_state")
        report_districts = st.multiselect("Filter by District", _districts(report_state), key="us_report_districts")
        report_levels = st.multiselect("Filter by School Category", _school_levels(report_state), key="us_report_levels")
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
            _export_buttons(report_df, "us_custom_report_2024_2025", csv_label="📥 Download CSV", excel_label="📊 Download Excel")
        else:
            st.info("Select at least one dimension and one metric to generate a custom report.")
'''

new_custom_ui = '''    with tabs[3]:
        st.markdown("#### 📝 Custom Reports")
        dimensions = st.multiselect(
            "Choose Dimensions",
            ["State", "District", "Location (City)", "School Type", "District Type", "School Category"],
            default=["State"],
            key="us_report_dims",
        )
        metrics = st.multiselect(
            "Choose Metrics",
            ["Schools", "Students", "Teachers", "PTR", "Students/School"],
            default=["Schools", "Students", "PTR"],
            key="us_report_metrics",
        )
        report_state = st.selectbox("Filter by State", ["All"] + _states(), index=0, key="us_report_state")
        report_districts = st.multiselect("Filter by District", _districts(report_state), key="us_report_districts")
        report_levels = st.multiselect("Filter by School Category", _school_levels(report_state), key="us_report_levels")
        report_filters = {
            "state": report_state,
            "districts": report_districts,
            "school_levels": report_levels,
        }
        if dimensions and metrics:
            report_df = _custom_report(dimensions, metrics, report_filters)
            _render_dataframe(report_df, use_container_width=True, height=520, hide_index=True)
            _export_buttons(report_df, "us_custom_report_2024_2025", csv_label="📥 Download CSV", excel_label="📊 Download Excel")
        else:
            st.info("Select at least one dimension and one metric to generate a custom report.")
'''

old_geo_df_cols = '''            display_cols = [c for c in [location_col, "state_name", "county_name", "district_name", "total_schools", "total_students", "total_teachers", "students_per_school", "ptr"] if c in df_map.columns]
            st.dataframe(df_map[display_cols], use_container_width=True, hide_index=True)
            _export_buttons(df_map, export_prefix)
'''

new_geo_df_cols = '''            display_cols = _dedupe_keep_order([c for c in [location_col, "state_name", "county_name", "district_name", "total_schools", "total_students", "total_teachers", "students_per_school", "ptr"] if c in df_map.columns])
            _render_dataframe(df_map[display_cols], use_container_width=True, hide_index=True)
            _export_buttons(df_map[display_cols], export_prefix)
'''


def main():
    if not TARGET.exists():
        raise SystemExit(f"Target file not found: {TARGET}")

    original = TARGET.read_text(encoding="utf-8")
    text = original

    replacements = [
        (old_imports, new_imports, "imports"),
        (insert_after_fmt_ptr, helper_block, "format helper insertion point"),
        (old_plot_bar, new_plot_bar, "plot bar helper"),
        (old_export, new_export, "export buttons"),
        (old_sidebar, new_sidebar, "sidebar filters"),
        (old_base_where, new_base_where, "base where"),
        (old_directory_cols, new_directory_cols, "directory columns"),
        (old_district_kpi, new_district_kpi, "district KPI table"),
        (old_state_metric, new_state_metric, "state metric frame"),
        (old_comparison, new_comparison, "state comparison frame"),
        (old_district_comparison, new_district_comparison, "district comparison frame"),
        (old_custom_report, new_custom_report, "custom report helper"),
        (old_custom_ui, new_custom_ui, "custom reports UI"),
        (old_geo_df_cols, new_geo_df_cols, "analytics geographic dataframe block"),
    ]

    for old, new, label in replacements:
        if old not in text:
            raise SystemExit(f"Could not find {label} to replace.")
        text = text.replace(old, new, 1)

    text = text.replace("st.dataframe(", "_render_dataframe(")

    backup = TARGET.with_name(TARGET.name + ".bak_cleanup_and_error_fix_v1")
    backup.write_text(original, encoding="utf-8")
    TARGET.write_text(text, encoding="utf-8")
    print(f"Backup created: {backup}")
    print(f"Updated: {TARGET}")


if __name__ == "__main__":
    main()
