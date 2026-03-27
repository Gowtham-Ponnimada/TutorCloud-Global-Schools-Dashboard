from pathlib import Path

TARGET = Path("utils/us_page_renderer.py")

old_grade_fn = '''def _grade_enrollment(filters: dict) -> pd.DataFrame:
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
'''

new_grade_fn = '''def _grade_enrollment(filters: dict) -> pd.DataFrame:
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
'''

old_enrollment_section = '''    st.markdown("### 📚 Grade-Level Enrollment Analysis")
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
'''

new_enrollment_section = '''    st.markdown("### 📚 Grade-Level Enrollment (Boys vs Girls)")
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
        st.dataframe(
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
                custom_data=["ptr"],
            )
            fig_district.update_traces(
                hovertemplate="<b>%{x}</b><br>PTR: %{customdata[0]:.2f}<extra></extra>"
            )
            fig_district.update_layout(xaxis_tickangle=-45, margin=dict(l=60, r=40, t=80, b=120))
            st.plotly_chart(fig_district, use_container_width=True, config={"displayModeBar": False})
        display_district_df = district_df[[c for c in ["district_name", "total_schools", "total_students", "total_teachers", "ptr"] if c in district_df.columns]].copy()
        display_district_df.columns = ["District", "Total Schools", "Total Students", "Total Teachers", "PTR"]
        if "PTR" in display_district_df.columns:
            display_district_df["PTR"] = display_district_df["PTR"].apply(_fmt_ptr)
        st.dataframe(display_district_df, use_container_width=True, hide_index=True)
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
                    custom_data=["ptr"],
                )
                fig_city.update_traces(
                    hovertemplate="<b>%{x}</b><br>PTR: %{customdata[0]:.2f}<extra></extra>"
                )
                fig_city.update_layout(xaxis_tickangle=-45, margin=dict(l=60, r=40, t=80, b=120))
                st.plotly_chart(fig_city, use_container_width=True, config={"displayModeBar": False})
            display_city_df = city_df[[c for c in ["city", "total_schools", "total_students", "total_teachers", "ptr"] if c in city_df.columns]].copy()
            display_city_df.columns = ["City", "Total Schools", "Total Students", "Total Teachers", "PTR"]
            if "PTR" in display_city_df.columns:
                display_city_df["PTR"] = display_city_df["PTR"].apply(_fmt_ptr)
            st.dataframe(display_city_df, use_container_width=True, hide_index=True)
            _export_buttons(display_city_df, "us_city_kpis_2024_2025")
        else:
            st.info("No city-level data available for the selected district.")
'''


def main():
    if not TARGET.exists():
        raise SystemExit(f"Target file not found: {TARGET}")
    original = TARGET.read_text(encoding="utf-8")
    text = original

    replacements = [
        (old_grade_fn, new_grade_fn, "grade enrollment helper"),
        (old_enrollment_section, new_enrollment_section, "state dashboard analysis section"),
    ]

    for old, new, label in replacements:
        if old not in text:
            raise SystemExit(f"Could not find {label} to replace.")
        text = text.replace(old, new, 1)

    backup = TARGET.with_name(TARGET.name + ".bak_state_analysis_parity_v1")
    backup.write_text(original, encoding="utf-8")
    TARGET.write_text(text, encoding="utf-8")
    print(f"Backup created: {backup}")
    print(f"Updated: {TARGET}")


if __name__ == "__main__":
    main()
