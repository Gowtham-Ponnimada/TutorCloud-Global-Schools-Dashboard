#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

ROOT = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
TARGET = ROOT / 'utils' / 'us_page_renderer.py'

HELPER = '''def _available_school_years() -> list[str]:
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


'''

NEW_FUNC = '''def render_us_analytics():
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
'''


def main() -> int:
    if not TARGET.exists():
        print(f'ERROR: target file not found: {TARGET}')
        return 1

    text = TARGET.read_text(encoding='utf-8')
    original = text

    if '_inject_analytics_parity_css' not in text:
        match = re.search(r'def render_us_analytics\(\):\n[\s\S]*\Z', text)
        if not match:
            print('ERROR: render_us_analytics() block not found')
            return 1
        text = text[:match.start()] + HELPER + NEW_FUNC + '\n'
    else:
        text = re.sub(r'def render_us_analytics\(\):\n[\s\S]*\Z', NEW_FUNC + '\n', text)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = TARGET.with_name(TARGET.name + f'.bak_analytics_parity_{ts}')
    backup.write_text(original, encoding='utf-8')
    TARGET.write_text(text, encoding='utf-8')

    print(f'Backup created: {backup}')
    print(f'Patched: {TARGET}')
    print('Applied US Analytics parity updates: year filter, breadcrumb navigation, India-like header, and KPI card styling.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
