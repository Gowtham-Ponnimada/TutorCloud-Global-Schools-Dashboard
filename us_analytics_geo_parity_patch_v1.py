from pathlib import Path

TARGET = Path("utils/us_page_renderer.py")

old_state_block = '''def _state_metric_frame() -> pd.DataFrame:
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
'''

new_state_block = '''def _state_metric_frame(school_year: str = DASHBOARD_YEAR) -> pd.DataFrame:
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
'''

old_geo_block = '''    with tabs[0]:
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
'''

new_geo_block = '''    with tabs[0]:
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
'''


def main():
    if not TARGET.exists():
        raise SystemExit(f"Target file not found: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")

    if old_state_block not in text:
        raise SystemExit("Could not find existing _state_metric_frame block to replace.")
    text = text.replace(old_state_block, new_state_block, 1)

    if old_geo_block not in text:
        raise SystemExit("Could not find existing Geographic Maps block to replace.")
    text = text.replace(old_geo_block, new_geo_block, 1)

    backup = TARGET.with_name(TARGET.name + ".bak_geo_parity_v1")
    backup.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
    TARGET.write_text(text, encoding="utf-8")
    print(f"Backup created: {backup}")
    print(f"Updated: {TARGET}")


if __name__ == "__main__":
    main()
