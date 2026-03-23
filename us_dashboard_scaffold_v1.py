from __future__ import annotations

from pathlib import Path
from datetime import datetime
import py_compile

REPO = Path('/home/noagedevadmin/tutorcloud/tutorcloud-global-dashboard')
UTILS = REPO / 'utils'
PAGES = REPO / 'pages'
MARKER = '# US_DASHBOARD_SCAFFOLD_V1'
TS = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

US_RENDERER = r'''from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

# US_DASHBOARD_SCAFFOLD_V1

US_REGION = "United States"
DASHBOARD_YEAR = "2024-2025"

US_COLORS = {
    "blue": "#1F4E79",
    "teal": "#0F766E",
    "green": "#2E7D32",
    "gold": "#D97706",
    "red": "#B42318",
    "gray": "#667085",
    "border": "#D0D5DD",
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


def _table_count(table: str) -> int:
    df = _q(f"SELECT COUNT(*) AS c FROM {table}")
    if df.empty:
        return 0
    return int(df.iloc[0]["c"] or 0)


def _fmt(v) -> str:
    try:
        if v is None or pd.isna(v):
            return "0"
        return f"{int(round(float(v))):,}"
    except Exception:
        return "0"


def _fmt_num(v) -> str:
    return _fmt(v)


def _fmt_ratio(v) -> str:
    try:
        if v is None or pd.isna(v):
            return "—"
        return f"{float(v):.2f}"
    except Exception:
        return "—"


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


def _base_where(filters: dict, include_state=True, include_district=True, include_level=True):
    clauses = ["school_year = %s"]
    params = [DASHBOARD_YEAR]
    if include_state and filters.get("state") and filters["state"] != "All":
        clauses.append("state_name = %s")
        params.append(filters["state"])
    districts = [x for x in (filters.get("districts") or []) if x]
    if include_district and districts:
        clauses.append("district_name = ANY(%s)")
        params.append(districts)
    levels = [x for x in (filters.get("school_levels") or []) if x]
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


def _districts(state_name: str) -> list[str]:
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


def _school_levels(state_name: str = "All") -> list[str]:
    if state_name and state_name != "All":
        df = _q(
            "SELECT DISTINCT school_level FROM us.dim_schools WHERE school_year = %s AND state_name = %s AND school_level IS NOT NULL ORDER BY school_level",
            [DASHBOARD_YEAR, state_name],
        )
    else:
        df = _q(
            "SELECT DISTINCT school_level FROM us.dim_schools WHERE school_year = %s AND school_level IS NOT NULL ORDER BY school_level",
            [DASHBOARD_YEAR],
        )
    return [str(x) for x in df["school_level"].tolist() if str(x) != "None"] if not df.empty else []


def _build_sidebar_filters() -> dict:
    with st.sidebar:
        st.markdown("## 🇺🇸 US Filters")
        st.caption("Directory-only · 2024–2025")
        state_opts = ["All"] + _states()
        state = st.selectbox("State", state_opts, index=0, key="us_state")
        district_opts = _districts(state)
        districts = st.multiselect("District", district_opts, key="us_districts")
        level_opts = _school_levels(state)
        school_levels = st.multiselect("School Level", level_opts, key="us_levels")
        return {
            "state": state,
            "districts": districts,
            "school_levels": school_levels,
        }


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
    st.plotly_chart(fig, use_container_width=True)


def _plot_pie(df: pd.DataFrame, names: str, values: str, title: str):
    if df is None or df.empty:
        st.info(f"No data available for {title}.")
        return
    fig = px.pie(df, names=names, values=values, hole=0.55, title=title, color_discrete_sequence=px.colors.qualitative.Safe)
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=10, r=10, t=55, b=10), font=dict(family="Segoe UI"))
    st.plotly_chart(fig, use_container_width=True)


def _national_summary() -> dict:
    states = _table_count("us.dim_states")
    districts = _table_count("us.dim_districts")
    schools = _table_count("us.dim_schools")
    avg_schools_per_state = round(schools / states, 2) if states else 0
    avg_districts_per_state = round(districts / states, 2) if states else 0
    distinct_levels = _q("SELECT COUNT(DISTINCT school_level) AS c FROM us.dim_schools WHERE school_year = %s AND school_level IS NOT NULL", [DASHBOARD_YEAR])
    levels = int(distinct_levels.iloc[0]["c"] or 0) if not distinct_levels.empty else 0
    return {
        "states": states,
        "districts": districts,
        "schools": schools,
        "avg_schools_per_state": avg_schools_per_state,
        "avg_districts_per_state": avg_districts_per_state,
        "school_levels": levels,
    }


def _top_states_by_schools(limit: int = 10) -> pd.DataFrame:
    return _q(
        "SELECT state_name, school_count FROM us.dim_states WHERE school_year = %s ORDER BY school_count DESC, state_name LIMIT %s",
        [DASHBOARD_YEAR, limit],
    )


def _school_level_mix(filters: dict | None = None) -> pd.DataFrame:
    filters = filters or {}
    where, params = _base_where(filters)
    return _q(
        f"SELECT COALESCE(school_level, 'Unknown') AS school_level, COUNT(DISTINCT school_id) AS school_count FROM us.dim_schools {where} GROUP BY 1 ORDER BY school_count DESC, school_level",
        params,
    )


def _top_districts(filters: dict | None = None, limit: int = 15) -> pd.DataFrame:
    filters = filters or {}
    where, params = _base_where(filters)
    params = params + [limit]
    return _q(
        f"SELECT district_name, COUNT(DISTINCT school_id) AS school_count FROM us.dim_schools {where} GROUP BY 1 ORDER BY school_count DESC, district_name LIMIT %s",
        params,
    )


def _state_kpis(filters: dict) -> dict:
    where, params = _base_where(filters)
    df = _q(
        f"SELECT COUNT(DISTINCT school_id) AS schools, COUNT(DISTINCT district_id) AS districts, COUNT(DISTINCT city) AS cities FROM us.dim_schools {where}",
        params,
    )
    if df.empty:
        return {"schools": 0, "districts": 0, "cities": 0}
    row = df.iloc[0].fillna(0)
    return {
        "schools": int(row.get("schools", 0)),
        "districts": int(row.get("districts", 0)),
        "cities": int(row.get("cities", 0)),
    }


def _schools_by_city(filters: dict, limit: int = 15) -> pd.DataFrame:
    where, params = _base_where(filters)
    params = params + [limit]
    return _q(
        f"SELECT COALESCE(city, 'Unknown') AS city, COUNT(DISTINCT school_id) AS school_count FROM us.dim_schools {where} GROUP BY 1 ORDER BY school_count DESC, city LIMIT %s",
        params,
    )


def _grade_span_distribution(filters: dict) -> pd.DataFrame:
    where, params = _base_where(filters)
    return _q(
        f"SELECT CONCAT(COALESCE(low_grade, '?'), ' → ', COALESCE(high_grade, '?')) AS grade_span, COUNT(DISTINCT school_id) AS school_count FROM us.dim_schools {where} GROUP BY 1 ORDER BY school_count DESC, grade_span LIMIT 20",
        params,
    )


def _directory_table(filters: dict, limit: int = 500) -> pd.DataFrame:
    where, params = _base_where(filters)
    params = params + [limit]
    return _q(
        f"SELECT school_name, district_name, state_name, city, school_level, low_grade, high_grade, zip_code FROM us.dim_schools {where} ORDER BY state_name, district_name, school_name LIMIT %s",
        params,
    )


def _comparison_frame(left_state: str, right_state: str) -> pd.DataFrame:
    sql = """
    SELECT state_name, COUNT(DISTINCT school_id) AS school_count, COUNT(DISTINCT district_id) AS district_count, COUNT(DISTINCT city) AS city_count
    FROM us.dim_schools
    WHERE school_year = %s AND state_name = ANY(%s)
    GROUP BY 1
    ORDER BY state_name
    """
    return _q(sql, [DASHBOARD_YEAR, [left_state, right_state]])


def render_us_home():
    _inject_css()
    summary = _national_summary()

    st.markdown("<div class='us-title'>🇺🇸 United States Education Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>Directory-only national overview using NCES 2024–2025 preliminary school and LEA directory data.</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-note'>This US dashboard currently uses only 2024–2025 directory data. Enrollment, teacher/staff, performance, and FRPL fact layers are intentionally not shown yet.</div>", unsafe_allow_html=True)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("States/Jurisdictions", _fmt(summary["states"]))
    c2.metric("Districts", _fmt(summary["districts"]))
    c3.metric("Schools", _fmt(summary["schools"]))
    c4.metric("School Levels", _fmt(summary["school_levels"]))
    c5.metric("Schools / State", _fmt_ratio(summary["avg_schools_per_state"]))
    c6.metric("Districts / State", _fmt_ratio(summary["avg_districts_per_state"]))

    left, right = st.columns(2)
    with left:
        _plot_bar(_top_states_by_schools(10), "state_name", "school_count", "Top 10 States by School Count")
    with right:
        _plot_pie(_school_level_mix({"state": "All", "districts": [], "school_levels": []}), "school_level", "school_count", "School Level Mix")

    st.markdown("### Key Insights")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Network coverage:** {summary['schools']:,} schools across {summary['states']:,} states and jurisdictions.")
    with col2:
        st.success(f"**District landscape:** {summary['districts']:,} districts are represented in the 2024–2025 directory file.")
    with col3:
        st.warning("**Current scope:** This release is intentionally directory-only. Fact-based KPIs will appear after enrollment/staff/performance layers are loaded.")

    st.markdown("### Explore More")
    nav1, nav2 = st.columns(2)
    with nav1:
        st.markdown("<div class='us-card'><h4>📊 State Dashboard</h4><p>Filter by state, district, and school level and inspect directory structure.</p></div>", unsafe_allow_html=True)
    with nav2:
        st.markdown("<div class='us-card'><h4>📈 Analytics</h4><p>Compare states, export custom directory reports, and review coverage analytics.</p></div>", unsafe_allow_html=True)


def render_us_state_dashboard():
    _inject_css()
    filters = _build_sidebar_filters()

    title_state = filters.get("state") if filters.get("state") and filters.get("state") != "All" else "All States"
    st.markdown(f"<div class='us-title'>📊 US State Dashboard — {title_state}</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>State-level directory exploration for 2024–2025.</div>", unsafe_allow_html=True)

    k = _state_kpis(filters)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Schools", _fmt(k["schools"]))
    c2.metric("Districts", _fmt(k["districts"]))
    c3.metric("Cities", _fmt(k["cities"]))
    c4.metric("Enrollment", "Directory only")
    c5.metric("Teachers", "Directory only")
    c6.metric("Performance", "Directory only")

    t1, t2, t3, t4 = st.tabs(["Overview", "Schools", "Districts", "Directory"])

    with t1:
        left, right = st.columns(2)
        with left:
            _plot_pie(_school_level_mix(filters), "school_level", "school_count", "School Level Mix")
        with right:
            _plot_bar(_schools_by_city(filters), "city", "school_count", "Top Cities by School Count", orientation="h")

        st.markdown("### Scope Notes")
        st.markdown(
            "<div class='us-note'>This view is built entirely from NCES directory data. Metrics that require enrollment, staff, lunch, or assessment facts are intentionally held back until those datasets are loaded.</div>",
            unsafe_allow_html=True,
        )

    with t2:
        _plot_bar(_grade_span_distribution(filters), "grade_span", "school_count", "Top Grade-Span Configurations", orientation="h")
        df = _directory_table(filters, limit=100)
        st.dataframe(df, use_container_width=True, height=420)
        _export_buttons(df, "us_directory_schools_filtered")

    with t3:
        df = _top_districts(filters, 25)
        _plot_bar(df, "district_name", "school_count", "Top Districts by School Count", orientation="h")
        st.dataframe(df, use_container_width=True, height=420)
        _export_buttons(df, "us_directory_districts_filtered")

    with t4:
        df = _directory_table(filters, limit=500)
        st.dataframe(df, use_container_width=True, height=500)
        _export_buttons(df, "us_directory_master_extract")


def render_us_analytics():
    _inject_css()
    st.markdown("<div class='us-title'>📈 US Analytics</div>", unsafe_allow_html=True)
    st.markdown("<div class='us-subtitle'>Directory-only analytics for the 2024–2025 US dashboard.</div>", unsafe_allow_html=True)

    tabs = st.tabs(["🗺️ Geographic Coverage", "🔍 Comparative Analysis", "📝 Custom Reports", "📦 Data Readiness"])

    with tabs[0]:
        df = _top_states_by_schools(25)
        _plot_bar(df, "state_name", "school_count", "States by School Count", orientation="h")
        _export_buttons(df, "us_states_by_school_count_2024_2025")

    with tabs[1]:
        states = _states()
        if len(states) >= 2:
            c1, c2 = st.columns(2)
            with c1:
                left_state = st.selectbox("State A", states, index=0, key="us_cmp_a")
            with c2:
                right_state = st.selectbox("State B", states, index=1 if len(states) > 1 else 0, key="us_cmp_b")
            cmp_df = _comparison_frame(left_state, right_state)
            st.dataframe(cmp_df, use_container_width=True)
            _export_buttons(cmp_df, "us_state_comparison_2024_2025")
        else:
            st.info("Not enough state records available for comparison.")

    with tabs[2]:
        states = ["All"] + _states()
        selected_state = st.selectbox("Filter report by state", states, index=0, key="us_report_state")
        district_opts = _districts(selected_state)
        selected_districts = st.multiselect("Filter report by district", district_opts, key="us_report_districts")
        selected_levels = st.multiselect("Filter report by school level", _school_levels(selected_state), key="us_report_levels")
        filters = {"state": selected_state, "districts": selected_districts, "school_levels": selected_levels}
        df = _directory_table(filters, 1000)
        st.dataframe(df, use_container_width=True, height=500)
        _export_buttons(df, "us_custom_directory_report_2024_2025")

    with tabs[3]:
        readiness = _q("SELECT * FROM us.vw_dashboard_readiness ORDER BY table_name")
        st.dataframe(readiness, use_container_width=True)
        st.markdown(
            "<div class='us-note'><strong>Current mode:</strong> Directory-only. The US dashboard is live on dimension tables first, following a staged build approach similar to the established India/UAE multi-page renderer pattern.</div>",
            unsafe_allow_html=True,
        )
'''


def backup(path: Path):
    if path.exists():
        backup_path = path.with_suffix(path.suffix + f'.bak_us_scaffold_{TS}')
        backup_path.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')


def patch_file(path: Path, old: str, new: str):
    text = path.read_text(encoding='utf-8')
    if new in text:
        return False
    if old not in text:
        raise RuntimeError(f'Expected block not found in {path}')
    text = text.replace(old, new, 1)
    if MARKER not in text:
        text += '\n' + MARKER + '\n'
    path.write_text(text, encoding='utf-8')
    return True


def main():
    UTILS.mkdir(parents=True, exist_ok=True)
    backup(UTILS / 'us_page_renderer.py')
    (UTILS / 'us_page_renderer.py').write_text(US_RENDERER, encoding='utf-8')

    home = PAGES / '1_🏠_Home.py'
    state_dash = PAGES / '2_📊_State_Dashboard.py'
    analytics = PAGES / '4_📈_Analytics.py'

    backup(home)
    backup(state_dash)
    backup(analytics)

    patch_file(
        home,
        'from utils.uae_page_renderer import render_uae_home',
        'from utils.uae_page_renderer import render_uae_home\nfrom utils.us_page_renderer import render_us_home',
    )
    patch_file(
        home,
        '_current_region = st.session_state.get("selected_region", "India")\nif _current_region == "UAE":\n    render_uae_home()\n    st.stop()',
        '_current_region = st.session_state.get("selected_region", "India")\nif _current_region == "UAE":\n    render_uae_home()\n    st.stop()\nelif _current_region == "United States":\n    render_us_home()\n    st.stop()',
    )

    patch_file(
        state_dash,
        'from utils.uae_page_renderer import render_uae_state_dashboard',
        'from utils.uae_page_renderer import render_uae_state_dashboard\nfrom utils.us_page_renderer import render_us_state_dashboard',
    )
    patch_file(
        state_dash,
        '_current_region = st.session_state.get("selected_region", "India")\nif _current_region == "UAE":\n    render_uae_state_dashboard()\n    st.stop()\nelif _current_region != "India":',
        '_current_region = st.session_state.get("selected_region", "India")\nif _current_region == "UAE":\n    render_uae_state_dashboard()\n    st.stop()\nelif _current_region == "United States":\n    render_us_state_dashboard()\n    st.stop()\nelif _current_region != "India":',
    )

    patch_file(
        analytics,
        'from utils.uae_page_renderer import render_uae_analytics',
        'from utils.uae_page_renderer import render_uae_analytics\nfrom utils.us_page_renderer import render_us_analytics',
    )
    patch_file(
        analytics,
        '_current_region = st.session_state.get("selected_region", "India")\nif _current_region == "UAE":\n    render_uae_analytics()\n    st.stop()',
        '_current_region = st.session_state.get("selected_region", "India")\nif _current_region == "UAE":\n    render_uae_analytics()\n    st.stop()\nelif _current_region == "United States":\n    render_us_analytics()\n    st.stop()',
    )

    py_compile.compile(str(UTILS / 'us_page_renderer.py'), doraise=True)
    py_compile.compile(str(home), doraise=True)
    py_compile.compile(str(state_dash), doraise=True)
    py_compile.compile(str(analytics), doraise=True)

    print('US dashboard scaffold generated successfully.')
    print('Updated: utils/us_page_renderer.py')
    print('Patched: pages/1_🏠_Home.py')
    print('Patched: pages/2_📊_State_Dashboard.py')
    print('Patched: pages/4_📈_Analytics.py')
    print('Next: restart Streamlit and test the United States region.')


if __name__ == '__main__':
    main()
