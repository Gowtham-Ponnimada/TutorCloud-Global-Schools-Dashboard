from pathlib import Path

TARGET = Path("utils/us_page_renderer.py")

old_export = '''def _export_buttons(df: pd.DataFrame, prefix: str):
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
'''

new_export = '''def _export_buttons(
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

old_custom_report = '''def _custom_report(dimensions: list[str], metrics: list[str], filters: dict) -> pd.DataFrame:
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
'''

new_custom_report = '''def _custom_report(dimensions: list[str], metrics: list[str], filters: dict) -> pd.DataFrame:
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
'''

old_comparison_export = '        _export_buttons(cmp_df, "us_comparison_2024_2025")\n'
new_comparison_export = '        _export_buttons(cmp_df, "us_comparison_2024_2025", csv_label="📥 Download Comparison CSV", excel_label="📊 Download Excel")\n'

old_custom_ui = '''    with tabs[3]:
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

new_custom_ui = '''    with tabs[3]:
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

old_home_label = '    c1.metric("TOTAL STATES/JURISDICTIONS", _fmt_int(summary.get("total_states")))\n'
new_home_label = '    c1.metric("TOTAL STATES/UTs", _fmt_int(summary.get("total_states")))\n'


def main():
    if not TARGET.exists():
        raise SystemExit(f"Target file not found: {TARGET}")
    original = TARGET.read_text(encoding="utf-8")
    text = original

    replacements = [
        (old_export, new_export, "export button helper"),
        (old_custom_report, new_custom_report, "custom report helper"),
        (old_comparison_export, new_comparison_export, "comparison export call"),
        (old_custom_ui, new_custom_ui, "custom reports UI block"),
        (old_home_label, new_home_label, "home KPI label"),
    ]

    for old, new, label in replacements:
        if old not in text:
            raise SystemExit(f"Could not find {label} to replace.")
        text = text.replace(old, new, 1)

    backup = TARGET.with_name(TARGET.name + ".bak_analytics_reports_export_parity_v1")
    backup.write_text(original, encoding="utf-8")
    TARGET.write_text(text, encoding="utf-8")
    print(f"Backup created: {backup}")
    print(f"Updated: {TARGET}")


if __name__ == "__main__":
    main()
