"""
Australia page renderer scaffold.

This file is intentionally minimal and designed to be merged into the
existing TutorCloud renderer pattern while keeping India as the UI/UX contract.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

AU_FILTER_BINDINGS = {
    "school_year": {"label": "School Year", "field": "ds.school_year", "default": "2025", "all_value": "All"},
    "state_name": {"label": "State/Territory", "field": "ds.state_name", "default": "All", "all_value": "All"},
    "district_name": {"label": "District / LGA", "field": "ds.district_name", "default": "All", "all_value": "All"},
    "suburb": {"label": "Suburb / Locality", "field": "ds.suburb", "default": "All", "all_value": "All"},
    "management_type": {"label": "School Management", "field": "COALESCE(ds.management_type, 'Unknown')", "default": "All", "all_value": "All"},
    "school_level": {"label": "School Level", "field": "COALESCE(ds.school_level, 'Unknown')", "default": "All", "all_value": "All"},
    "remoteness": {"label": "Remoteness", "field": "COALESCE(ds.abs_remoteness_area_name, 'Unknown')", "default": "All", "all_value": "All"},
    "governing_body": {"label": "Governing Body", "field": "COALESCE(ds.governing_body, 'Unknown')", "default": "All", "all_value": "All"},
    "postcode": {"label": "Postcode", "field": "COALESCE(ds.postcode, 'Unknown')", "default": "All", "all_value": "All"},
    "school_name": {"label": "School Name", "field": "ds.school_name", "default": "", "all_value": ""},
}

AU_FILTER_CASCADE = {
    "state_name": ["district_name", "suburb", "governing_body", "postcode", "school_name"],
    "district_name": ["suburb", "postcode", "school_name"],
    "management_type": ["school_level", "remoteness", "governing_body", "school_name"],
    "school_level": ["remoteness", "governing_body", "school_name"],
}


def _base_where_au(filters: Dict[str, Any] | None = None, alias: str = "ds") -> Tuple[str, list]:
    filters = filters or {}
    clauses = [f"{alias}.school_year = %s"]
    params = [filters.get("school_year", "2025")]

    for key, col in [
        ("state_name", f"{alias}.state_name"),
        ("district_name", f"{alias}.district_name"),
        ("suburb", f"{alias}.suburb"),
    ]:
        value = filters.get(key)
        if value and value != "All":
            clauses.append(f"{col} = %s")
            params.append(value)

    for key, col in [
        ("management_type", f"COALESCE({alias}.management_type, 'Unknown')"),
        ("school_level", f"COALESCE({alias}.school_level, 'Unknown')"),
        ("remoteness", f"COALESCE({alias}.abs_remoteness_area_name, 'Unknown')"),
        ("governing_body", f"COALESCE({alias}.governing_body, 'Unknown')"),
        ("postcode", f"COALESCE({alias}.postcode, 'Unknown')"),
    ]:
        value = filters.get(key)
        if value and value != "All":
            clauses.append(f"{col} = %s")
            params.append(value)

    school_name = (filters.get("school_name") or "").strip()
    if school_name:
        clauses.append(f"{alias}.school_name ILIKE %s")
        params.append(f"%{school_name}%")

    return " AND ".join(clauses), params


def au_kpi_sql(filters: Dict[str, Any] | None = None) -> Tuple[str, list]:
    where_sql, params = _base_where_au(filters, alias="ds")
    sql = f"""
    SELECT
        COUNT(DISTINCT ds.school_id) AS total_schools,
        COALESCE(SUM(fs.total_students), 0) AS total_students,
        COALESCE(SUM(fs.girls_students), 0) AS girls_students,
        COALESCE(SUM(fs.boys_students), 0) AS boys_students,
        COALESCE(SUM(fs.fte_teaching_staff), 0) AS fte_teaching_staff,
        CASE
            WHEN COALESCE(SUM(fs.fte_teaching_staff), 0) > 0
            THEN ROUND(SUM(fs.total_students)::numeric / SUM(fs.fte_teaching_staff), 4)
            ELSE NULL
        END AS student_teacher_ratio
    FROM au.dim_schools ds
    LEFT JOIN au.fact_school_totals fs
      ON ds.school_year = fs.school_year
     AND ds.school_id = fs.school_id
    WHERE {where_sql}
    """
    return sql, params


def au_state_summary_sql(filters: Dict[str, Any] | None = None) -> Tuple[str, list]:
    where_sql, params = _base_where_au(filters, alias="ds")
    sql = f"""
    SELECT
        ds.state_name,
        COUNT(DISTINCT ds.school_id) AS schools,
        COALESCE(SUM(fs.total_students), 0) AS total_students,
        COALESCE(SUM(fs.fte_teaching_staff), 0) AS fte_teaching_staff
    FROM au.dim_schools ds
    LEFT JOIN au.fact_school_totals fs
      ON ds.school_year = fs.school_year
     AND ds.school_id = fs.school_id
    WHERE {where_sql}
    GROUP BY ds.state_name
    ORDER BY total_students DESC, ds.state_name
    """
    return sql, params


def au_district_summary_sql(filters: Dict[str, Any] | None = None) -> Tuple[str, list]:
    where_sql, params = _base_where_au(filters, alias="ds")
    sql = f"""
    SELECT
        ds.state_name,
        ds.district_name,
        COUNT(DISTINCT ds.school_id) AS schools,
        COALESCE(SUM(fs.total_students), 0) AS total_students
    FROM au.dim_schools ds
    LEFT JOIN au.fact_school_totals fs
      ON ds.school_year = fs.school_year
     AND ds.school_id = fs.school_id
    WHERE {where_sql}
    GROUP BY ds.state_name, ds.district_name
    ORDER BY total_students DESC, ds.state_name, ds.district_name
    """
    return sql, params


def au_school_directory_sql(filters: Dict[str, Any] | None = None) -> Tuple[str, list]:
    where_sql, params = _base_where_au(filters, alias="ds")
    sql = f"""
    SELECT
        ds.school_name,
        ds.state_name,
        ds.district_name,
        ds.suburb,
        ds.postcode,
        ds.management_type,
        ds.school_level,
        ds.year_range,
        ds.total_students,
        ds.girls_students,
        ds.boys_students,
        ds.fte_teaching_staff,
        ds.student_teacher_ratio,
        ds.icsea,
        ds.governing_body,
        ds.school_url
    FROM au.dim_schools ds
    WHERE {where_sql}
    ORDER BY ds.school_name
    """
    return sql, params


def render_au_page_placeholder() -> str:
    return (
        "Australia renderer scaffold ready. Bind this file into the existing Streamlit page layout, "
        "reuse India tab order, and point widgets to AU_FILTER_BINDINGS / AU_FILTER_CASCADE."
    )
