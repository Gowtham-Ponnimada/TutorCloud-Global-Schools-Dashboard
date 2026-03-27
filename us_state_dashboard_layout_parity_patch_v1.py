from pathlib import Path

TARGET = Path("utils/us_page_renderer.py")

insert_after = '''def _district_kpi_table(filters: dict, limit: int = 50) -> pd.DataFrame:
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

insert_block = '''def _district_kpi_table(filters: dict, limit: int = 50) -> pd.DataFrame:
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
'''

old_render = '''def render_us_state_dashboard():
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
'''

new_render = '''def render_us_state_dashboard():
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

    k = _state_dashboard_kpis(filters)
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c1.metric("TOTAL SCHOOLS", _fmt_int(k.get("total_schools")))
    c2.metric("SCHOOLS WITH ENROLLMENT", _fmt_int(k.get("schools_with_enrollment")))
    c3.metric("DISTRICTS", _fmt_int(k.get("total_districts")))
    c4.metric("STATE PTR", _fmt_ptr(k.get("ptr")))
    c5.metric("TOTAL STUDENTS", _fmt_int(k.get("total_students")))
    c6.metric("TOTAL TEACHERS", _fmt_int(k.get("total_teachers")))

    st.markdown("### 📚 Grade-Level Enrollment Analysis")
    enrollment_df = _grade_enrollment(filters)
    chart_left, chart_right = st.columns(2)
    with chart_left:
        _plot_bar(enrollment_df, "grade", "total_students", "Grade-wise Enrollment")
    with chart_right:
        city_mix_df = _schools_by_city(filters)
        _plot_bar(city_mix_df, "city", "school_count", "Top Cities by School Count", orientation="h")
    if not enrollment_df.empty:
        st.dataframe(
            enrollment_df.rename(columns={"grade": "Grade", "total_students": "Total Students"}),
            use_container_width=True,
            hide_index=True,
        )
        _export_buttons(enrollment_df, "us_grade_enrollment_2024_2025")

    st.markdown("### 📍 District-Level Analysis")
    district_df = _district_kpi_table(filters, 100)
    if not district_df.empty:
        district_chart = district_df.copy()
        if "ptr" in district_chart.columns:
            district_chart = district_chart[district_chart["ptr"].notna()].copy()
        _plot_bar(district_chart.head(25), "district_name", "ptr", "District-Level PTR Analysis", orientation="h")
        st.dataframe(district_df, use_container_width=True, hide_index=True)
        _export_buttons(district_df, "us_district_kpis_2024_2025")
    else:
        st.info("No district-level data available for the selected filters.")

    if filters.get("district") and filters.get("district") != "All":
        st.markdown("### 🏘️ City-Level Analysis")
        city_df = _city_kpi_table(filters, 100)
        if not city_df.empty:
            city_chart = city_df.copy()
            if "ptr" in city_chart.columns:
                city_chart = city_chart[city_chart["ptr"].notna()].copy()
            if not city_chart.empty:
                _plot_bar(city_chart.head(25), "city", "ptr", "City-Level PTR Analysis", orientation="h")
            else:
                _plot_bar(city_df.head(25), "city", "total_schools", "City-Level School Coverage", orientation="h")
            st.dataframe(city_df, use_container_width=True, hide_index=True)
            _export_buttons(city_df, "us_city_kpis_2024_2025")
        else:
            st.info("No city-level data available for the selected district.")

    st.markdown("### 🏫 School Directory")
    mix = _school_level_mix(filters)
    if not mix.empty:
        st.dataframe(
            mix.rename(columns={"school_level": "School Level", "school_count": "School Count"}),
            use_container_width=True,
            hide_index=True,
        )
        _export_buttons(mix, "us_school_level_mix_2024_2025")

    directory_df = _directory_table(filters, 1000)
    st.dataframe(directory_df, use_container_width=True, height=520, hide_index=True)
    _export_buttons(directory_df, "us_directory_extract_2024_2025")

    _render_footer()
'''


def main():
    if not TARGET.exists():
        raise SystemExit(f"Target file not found: {TARGET}")

    original = TARGET.read_text(encoding="utf-8")
    text = original

    if insert_after not in text:
        raise SystemExit("Could not find district KPI helper block to extend.")
    text = text.replace(insert_after, insert_block, 1)

    if old_render not in text:
        raise SystemExit("Could not find render_us_state_dashboard block to replace.")
    text = text.replace(old_render, new_render, 1)

    backup = TARGET.with_name(TARGET.name + ".bak_state_layout_parity_v1")
    backup.write_text(original, encoding="utf-8")
    TARGET.write_text(text, encoding="utf-8")
    print(f"Backup created: {backup}")
    print(f"Updated: {TARGET}")


if __name__ == "__main__":
    main()
