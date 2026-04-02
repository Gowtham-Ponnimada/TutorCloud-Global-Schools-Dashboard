from __future__ import annotations

import re
from io import BytesIO
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

from au_phase1_final_load import db_engine
from services.au_dashboard_service import AUDashboardService

try:
    from ui_components import COLORS as APP_COLORS
except Exception:
    APP_COLORS = {}


INDIA_UI = {
    "primary_blue": APP_COLORS.get("primary", "#1E88E5"),
    "primary_blue_dark": APP_COLORS.get("secondary", "#1565C0"),
    "page_bg": "#F5F7FA",
    "card_bg": "#FFFFFF",
    "text": "#1F2937",
    "muted": "#7A7A7A",
    "border": APP_COLORS.get("primary", "#1E88E5"),
    "shadow": "0 2px 8px rgba(30, 136, 229, 0.08)",
    "girls": "#EC4899",
    "boys": "#3B82F6",
    "schools": "#14B8A6",
    "students": APP_COLORS.get("primary", "#1E88E5"),
    "teachers": APP_COLORS.get("primary", "#1E88E5"),
    "ptr": APP_COLORS.get("primary", "#1E88E5"),
    "icsea": "#8B5CF6",
    "indigenous": "#EF4444",
    "lbote": "#10B981",
    "government": "#2563EB",
    "catholic": "#F59E0B",
    "independent": "#10B981",
}

COLUMN_TITLES = {
    "school_year": "School Year",
    "state_name": "State",
    "state_abbr": "State Abbr",
    "district_name": "District",
    "school_id": "School ID",
    "school_name": "School Name",
    "suburb": "Suburb",
    "postcode": "Postcode",
    "management_type": "Management Type",
    "school_level": "School Level",
    "delivery_model": "Delivery Model",
    "schools": "Total Schools",
    "schools_with_enrollment": "Schools With Enrollment",
    "total_districts": "Total Districts",
    "total_students": "Total Students",
    "girls_students": "Female Students",
    "boys_students": "Male Students",
    "fte_teaching_staff": "Total Teachers",
    "student_teacher_ratio": "PTR",
    "ptr_ratio": "PTR Ratio",
    "PTR": "PTR",
    "weighted_avg_icsea": "Avg ICSEA",
    "weighted_indigenous_pct": "Indigenous %",
    "weighted_lbote_yes_pct": "LBOTE %",
    "grade_code": "Grade Code",
    "grade_label": "Grade",
    "enrolled_students": "Students",
}

INT_LIKE_COLUMNS = {
    "schools", "schools_with_enrollment", "total_districts", "total_students",
    "girls_students", "boys_students", "enrolled_students", "fte_teaching_staff"
}
FLOAT_2_COLUMNS = {"weighted_avg_icsea", "weighted_indigenous_pct", "weighted_lbote_yes_pct"}


def _get_service() -> AUDashboardService:
    svc = st.session_state.get("_au_dashboard_service")
    if svc is None:
        svc = AUDashboardService(db_engine(), school_year="2025")
        st.session_state["_au_dashboard_service"] = svc
    return svc


def _to_dataframe(rows: Any) -> pd.DataFrame:
    if rows is None:
        return pd.DataFrame()
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    try:
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


def _safe_state_df() -> pd.DataFrame:
    return _to_dataframe(_get_service().get_state_kpis())


def _safe_district_df(state_name: str) -> pd.DataFrame:
    return _to_dataframe(_get_service().get_district_kpis(state_name))


def _safe_school_df(**filters) -> pd.DataFrame:
    return _to_dataframe(_get_service().get_schools(**filters))


def _is_missing(v: Any) -> bool:
    try:
        return pd.isna(v)
    except Exception:
        return v is None


def _num(v: Any) -> float:
    if _is_missing(v):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def _fmt_int(v: Any) -> str:
    if _is_missing(v):
        return "N/A"
    try:
        return f"{int(round(float(v))):,}"
    except Exception:
        return str(v)


def _fmt_float(v: Any, digits: int = 2) -> str:
    if _is_missing(v):
        return "N/A"
    try:
        return f"{float(v):,.{digits}f}"
    except Exception:
        return str(v)


def _fmt_pct(v: Any, digits: int = 2) -> str:
    if _is_missing(v):
        return "N/A"
    try:
        return f"{float(v):,.{digits}f}%"
    except Exception:
        return str(v)


def _fmt_ptr(v: Any) -> str:
    if _is_missing(v):
        return "N/A"
    try:
        return f"{int(round(float(v)))}:1"
    except Exception:
        return str(v)


def _normalize_label(label: str) -> str:
    s = str(label).strip()
    if s in COLUMN_TITLES:
        return COLUMN_TITLES[s]
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    return s.title().replace("Ptr", "PTR")


def _format_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    for col in out.columns:
        if col in {"student_teacher_ratio", "PTR"}:
            out[col] = out[col].apply(_fmt_ptr)
        elif col in INT_LIKE_COLUMNS:
            out[col] = out[col].apply(_fmt_int)
        elif col in FLOAT_2_COLUMNS:
            if "pct" in col:
                out[col] = out[col].apply(lambda x: _fmt_pct(x, 2))
            else:
                out[col] = out[col].apply(lambda x: _fmt_float(x, 2))
        else:
            out[col] = out[col].apply(lambda x: "N/A" if _is_missing(x) else x)
    out.columns = [_normalize_label(c) for c in out.columns]
    return out


def _display_df(df: pd.DataFrame, *, use_container_width: bool = True, hide_index: bool = True) -> None:
    st.dataframe(_format_dataframe_for_display(df), use_container_width=use_container_width, hide_index=hide_index)


def _inject_au_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {INDIA_UI['page_bg']}; }}
        .au-top-title {{ text-align:center; color:{INDIA_UI['text']}; font-size:1.02rem; font-weight:700; margin-top:0.15rem; margin-bottom:0.15rem; }}
        .au-top-rule {{ border:none; border-top:1px solid #E5E7EB; margin-top:0.75rem; margin-bottom:2.2rem; }}
        .au-section-hero {{ display:flex; align-items:center; gap:12px; margin-bottom:1.15rem; }}
        .au-section-icon {{ font-size:1.9rem; line-height:1; }}
        .au-section-title {{ color:{INDIA_UI['text']}; font-size:2.05rem; font-weight:800; line-height:1.12; margin:0; }}
        .au-subsection-title {{ color:{INDIA_UI['text']}; font-size:1.08rem; font-weight:800; margin-top:0.35rem; margin-bottom:0.15rem; }}
        .au-subsection-subtitle {{ color:{INDIA_UI['muted']}; font-size:0.93rem; margin-bottom:0.8rem; }}
        .au-kpi-card {{ background:{INDIA_UI['card_bg']}; border:2px solid {INDIA_UI['border']}; border-radius:12px; padding:18px 16px; box-shadow:{INDIA_UI['shadow']}; min-height:94px; display:flex; flex-direction:column; justify-content:center; }}
        .au-kpi-label {{ color:#7E7E7E; font-size:0.83rem; font-weight:700; letter-spacing:0.07em; text-transform:uppercase; margin-bottom:10px; line-height:1.15; }}
        .au-kpi-value {{ color:{INDIA_UI['primary_blue']}; font-size:1.98rem; font-weight:800; line-height:1.05; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-variant-numeric:tabular-nums; }}
        .au-grid-gap {{ height:18px; }}
        div[data-testid="stDataFrame"] {{ border-radius:12px; overflow:hidden; border:1px solid #E5E7EB; background:white; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_top_header(title: str) -> None:
    st.markdown(f'<div class="au-top-title">{title}</div>', unsafe_allow_html=True)
    st.markdown('<hr class="au-top-rule"/>', unsafe_allow_html=True)


def _render_section_header(title: str, icon: str = "📊") -> None:
    st.markdown(f'''<div class="au-section-hero"><div class="au-section-icon">{icon}</div><div class="au-section-title">{title}</div></div>''', unsafe_allow_html=True)


def _render_subsection(title: str, subtitle: Optional[str] = None) -> None:
    st.markdown(f'<div class="au-subsection-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="au-subsection-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def _render_kpi_cards(cards: List[Dict[str, Any]], per_row: int = 3) -> None:
    if not cards:
        return
    for i in range(0, len(cards), per_row):
        row = cards[i:i+per_row]
        cols = st.columns(per_row)
        for idx, card in enumerate(row):
            with cols[idx]:
                st.markdown(f'''<div class="au-kpi-card"><div class="au-kpi-label">{card['label']}</div><div class="au-kpi-value">{card['value']}</div></div>''', unsafe_allow_html=True)
        if i + per_row < len(cards):
            st.markdown('<div class="au-grid-gap"></div>', unsafe_allow_html=True)


def _style_chart(fig, title: Optional[str] = None, x_title: Optional[str] = None, y_title: Optional[str] = None, height: int = 430):
    fig.update_layout(
        title={"text": title or "", "x": 0.0, "xanchor": "left", "font": {"size": 18, "color": INDIA_UI["text"]}},
        paper_bgcolor="white", plot_bgcolor="white", height=height,
        margin=dict(l=8, r=8, t=50, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, title_text=""),
        font=dict(color=INDIA_UI["text"]),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E5E7EB", title_text=x_title)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F7", zeroline=False, title_text=y_title, separatethousands=True)
    return fig


# -----------------------------
# FILTERS / AGGREGATIONS
# -----------------------------
def _state_sidebar_filters(states_df: pd.DataFrame) -> Dict[str, Any]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Apply Filters")

    state_options = states_df["state_name"].dropna().tolist() if "state_name" in states_df.columns else []
    default_state = st.session_state.get("au_selected_state", state_options[0] if state_options else None)
    if default_state not in state_options and state_options:
        default_state = state_options[0]
    state = st.sidebar.selectbox("🗺️ Select State/UT", state_options, index=state_options.index(default_state) if default_state in state_options else 0, key="au_state_filter") if state_options else None
    st.session_state["au_selected_state"] = state
    try:
        if state:
            st.query_params["state"] = state
    except Exception:
        pass

    districts_df = _safe_district_df(state) if state else pd.DataFrame()
    districts = sorted([x for x in districts_df.get("district_name", pd.Series(dtype=str)).dropna().unique().tolist() if x]) if not districts_df.empty else []
    district = st.sidebar.selectbox("🏘️ Select District", ["All"] + districts, index=0, key=f"au_district_filter_{state}")

    filters_meta = _get_service().get_filter_options() or {}
    managements = filters_meta.get("management_types", []) or []
    levels = filters_meta.get("school_levels", []) or []

    management_groups = st.sidebar.multiselect("🏛️ Management Type", managements, default=[], key=f"au_mgmt_filter_{state}")
    school_levels = st.sidebar.multiselect("📚 School Level", levels, default=[], key=f"au_level_filter_{state}")
    search = st.sidebar.text_input("🔎 Search School", value="", key=f"au_search_filter_{state}")

    return {
        "state_name": state,
        "district_name": None if district == "All" else district,
        "management_type": management_groups[0] if len(management_groups) == 1 else None,
        "management_groups": management_groups,
        "school_level": school_levels[0] if len(school_levels) == 1 else None,
        "school_levels": school_levels,
        "delivery_model": None,
        "search": search or None,
        "limit": 20000,
        "offset": 0,
    }


def _analytics_sidebar_filters(states_df: pd.DataFrame) -> Dict[str, Any]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔬 Analytics Filters")
    state_options = ["All"] + (states_df["state_name"].dropna().tolist() if "state_name" in states_df.columns else [])
    selected_state = st.sidebar.selectbox("State", state_options, key="au_analytics_state")
    selected_district = "All"
    if selected_state != "All":
        ddf = _safe_district_df(selected_state)
        districts = sorted([x for x in ddf.get("district_name", pd.Series(dtype=str)).dropna().unique().tolist() if x]) if not ddf.empty else []
        selected_district = st.sidebar.selectbox("District", ["All"] + districts, key="au_analytics_district")
    return {
        "state_name": None if selected_state == "All" else selected_state,
        "district_name": None if selected_district == "All" else selected_district,
    }


def _apply_school_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if filters.get("management_groups") and "management_type" in out.columns:
        out = out[out["management_type"].isin(filters["management_groups"])]
    if filters.get("school_levels") and "school_level" in out.columns:
        out = out[out["school_level"].isin(filters["school_levels"])]
    return out


def _aggregate_state_overview(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "total_schools": 0,
            "schools_with_enrollment": 0,
            "total_districts": 0,
            "total_students": 0,
            "male_students": 0,
            "female_students": 0,
            "total_teachers": 0,
            "state_ptr": "N/A",
        }
    total_schools = df["school_id"].nunique() if "school_id" in df.columns else len(df)
    schools_with_enrollment = int((df["total_students"].fillna(0) > 0).sum()) if "total_students" in df.columns else 0
    total_districts = df["district_name"].dropna().nunique() if "district_name" in df.columns else 0
    total_students = _num(df["total_students"].fillna(0).sum()) if "total_students" in df.columns else 0
    male_students = _num(df["boys_students"].fillna(0).sum()) if "boys_students" in df.columns else 0
    female_students = _num(df["girls_students"].fillna(0).sum()) if "girls_students" in df.columns else 0
    total_teachers = _num(df["fte_teaching_staff"].fillna(0).sum()) if "fte_teaching_staff" in df.columns else 0
    ptr_ratio = (total_students / total_teachers) if total_teachers > 0 and total_students > 0 else None
    return {
        "total_schools": total_schools,
        "schools_with_enrollment": schools_with_enrollment,
        "total_districts": total_districts,
        "total_students": total_students,
        "male_students": male_students,
        "female_students": female_students,
        "total_teachers": total_teachers,
        "state_ptr": _fmt_ptr(ptr_ratio) if ptr_ratio else "N/A",
        "ptr_ratio": ptr_ratio,
    }


def _district_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "district_name" not in df.columns:
        return pd.DataFrame()
    grp = df.groupby("district_name", dropna=False).agg(
        total_schools=("school_id", pd.Series.nunique),
        total_students=("total_students", "sum"),
        total_teachers=("fte_teaching_staff", "sum"),
    ).reset_index()
    grp["ptr_ratio"] = grp.apply(lambda r: (r["total_students"] / r["total_teachers"]) if _num(r["total_teachers"]) > 0 else None, axis=1)
    grp["PTR"] = grp["ptr_ratio"].apply(_fmt_ptr)
    return grp.sort_values("total_schools", ascending=False)


def _group_metrics(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df is None or df.empty or col not in df.columns:
        return pd.DataFrame()
    grp = df.groupby(col, dropna=False).agg(
        total_schools=("school_id", pd.Series.nunique),
        total_students=("total_students", "sum"),
        total_teachers=("fte_teaching_staff", "sum"),
    ).reset_index()
    grp["ptr"] = grp.apply(lambda r: (r["total_students"] / r["total_teachers"]) if _num(r["total_teachers"]) > 0 else None, axis=1)
    return grp.sort_values("total_schools", ascending=False)


def _analytics_aggregate(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {"total_schools": 0, "total_students": 0, "total_teachers": 0, "ptr": None}
    total_schools = df["school_id"].nunique() if "school_id" in df.columns else len(df)
    total_students = _num(df["total_students"].sum()) if "total_students" in df.columns else 0
    total_teachers = _num(df["fte_teaching_staff"].sum()) if "fte_teaching_staff" in df.columns else 0
    ptr = round(total_students / total_teachers) if total_teachers > 0 else None
    return {"total_schools": total_schools, "total_students": total_students, "total_teachers": total_teachers, "ptr": ptr}


def _comparison_df_state(states_df: pd.DataFrame, state1: str, state2: str) -> pd.DataFrame:
    df1 = states_df[states_df["state_name"].str.upper() == state1.upper()] if not states_df.empty else pd.DataFrame()
    df2 = states_df[states_df["state_name"].str.upper() == state2.upper()] if not states_df.empty else pd.DataFrame()
    if df1.empty or df2.empty:
        return pd.DataFrame()
    d1 = df1.iloc[0]
    d2 = df2.iloc[0]
    sps1 = round(_num(d1.get("total_students")) / _num(d1.get("schools"))) if _num(d1.get("schools")) > 0 else None
    sps2 = round(_num(d2.get("total_students")) / _num(d2.get("schools"))) if _num(d2.get("schools")) > 0 else None
    return pd.DataFrame({
        "Metric": ["Total Schools", "Total Students", "Total Teachers", "PTR", "Students/School"],
        state1: [
            _fmt_int(d1.get("schools")),
            _fmt_int(d1.get("total_students")),
            _fmt_int(d1.get("fte_teaching_staff")),
            _fmt_ptr(d1.get("student_teacher_ratio")),
            _fmt_int(sps1),
        ],
        state2: [
            _fmt_int(d2.get("schools")),
            _fmt_int(d2.get("total_students")),
            _fmt_int(d2.get("fte_teaching_staff")),
            _fmt_ptr(d2.get("student_teacher_ratio")),
            _fmt_int(sps2),
        ],
    })


def _comparison_df_district(state1: str, district1: str, state2: str, district2: str) -> pd.DataFrame:
    df1 = _safe_district_df(state1)
    df1 = df1[df1["district_name"].str.upper() == district1.upper()] if not df1.empty else pd.DataFrame()
    df2 = _safe_district_df(state2)
    df2 = df2[df2["district_name"].str.upper() == district2.upper()] if not df2.empty else pd.DataFrame()
    if df1.empty or df2.empty:
        return pd.DataFrame()
    d1 = df1.iloc[0]
    d2 = df2.iloc[0]
    return pd.DataFrame({
        "Metric": ["Total Schools", "Total Students", "Total Teachers", "PTR"],
        f"{district1} ({state1})": [
            _fmt_int(d1.get("schools")), _fmt_int(d1.get("total_students")), _fmt_int(d1.get("fte_teaching_staff")), _fmt_ptr(d1.get("student_teacher_ratio"))
        ],
        f"{district2} ({state2})": [
            _fmt_int(d2.get("schools")), _fmt_int(d2.get("total_students")), _fmt_int(d2.get("fte_teaching_staff")), _fmt_ptr(d2.get("student_teacher_ratio"))
        ],
    })


def _fetch_grade_enrollment(filters: Dict[str, Any]) -> pd.DataFrame:
    conditions = ["ds.school_year = :school_year"]
    params: Dict[str, Any] = {"school_year": "2025"}

    if filters.get("state_name"):
        conditions.append("ds.state_name = :state_name")
        params["state_name"] = filters["state_name"]
    if filters.get("district_name"):
        conditions.append("ds.district_name = :district_name")
        params["district_name"] = filters["district_name"]
    if filters.get("management_groups"):
        conditions.append("ds.management_type IN :management_groups")
        params["management_groups"] = tuple(filters["management_groups"])
    elif filters.get("management_type"):
        conditions.append("ds.management_type = :management_type")
        params["management_type"] = filters["management_type"]
    if filters.get("school_levels"):
        conditions.append("ds.school_level IN :school_levels")
        params["school_levels"] = tuple(filters["school_levels"])
    elif filters.get("school_level"):
        conditions.append("ds.school_level = :school_level")
        params["school_level"] = filters["school_level"]
    if filters.get("search"):
        conditions.append("ds.school_name ILIKE :search")
        params["search"] = f"%{filters['search']}%"

    sql = f"""
        SELECT
            fge.grade_code,
            fge.grade_label,
            SUM(COALESCE(fge.enrolled_students, 0)) AS enrolled_students
        FROM au.fact_grade_enrollment fge
        JOIN au.dim_schools ds
          ON ds.school_year = fge.school_year
         AND ds.school_id = fge.school_id
        WHERE {' AND '.join(conditions)}
        GROUP BY fge.grade_code, fge.grade_label
        ORDER BY fge.grade_code, fge.grade_label
    """
    try:
        eng = db_engine()
        return pd.read_sql(text(sql), eng, params=params)
    except Exception:
        return pd.DataFrame()


def _render_metric_cards_overview(agg_data: Dict[str, Any]) -> None:
    st.markdown("#### 📊 Key Performance Indicators")
    kpi_cols = st.columns(4)
    with kpi_cols[0]:
        st.metric("Total Schools", _fmt_int(agg_data.get("total_schools")))
    with kpi_cols[1]:
        st.metric("Total Students", _fmt_int(agg_data.get("total_students")))
    with kpi_cols[2]:
        st.metric("Total Teachers", _fmt_int(agg_data.get("total_teachers")))
    with kpi_cols[3]:
        ptr_value = _fmt_ptr(agg_data.get("ptr" if "ptr" in agg_data else "ptr_ratio")) if agg_data.get("ptr" if "ptr" in agg_data else "ptr_ratio") else "N/A"
        st.metric("PTR", ptr_value)
    col1, col2 = st.columns(2)
    with col1:
        schools = _num(agg_data.get("total_schools"))
        students = _num(agg_data.get("total_students"))
        sps = round(students / schools, 2) if schools > 0 else None
        st.metric("Students per School", f"{sps}" if sps is not None else "N/A")
    with col2:
        schools = _num(agg_data.get("total_schools"))
        teachers = _num(agg_data.get("total_teachers"))
        tps = round(teachers / schools, 2) if schools > 0 else None
        st.metric("Teachers per School", f"{tps}" if tps is not None else "N/A")


# -----------------------------
# RENDERERS
# -----------------------------
def render_au_home() -> None:
    _inject_au_css()
    svc = _get_service()
    summary = svc.get_national_summary() or {}
    states_df = _safe_state_df()
    total_states = states_df["state_name"].nunique() if not states_df.empty and "state_name" in states_df.columns else 0
    teachers = summary.get("fte_teaching_staff")
    schools = summary.get("schools")
    students = summary.get("total_students")
    students_per_school = round(_num(students) / _num(schools)) if _num(schools) > 0 else None

    _render_top_header("National K-12 Education Overview - Australia 2025")
    _render_section_header("National Overview", icon="📊")

    cards = [
        {"label": "TOTAL STATES/UTS", "value": _fmt_int(total_states)},
        {"label": "TOTAL SCHOOLS", "value": _fmt_int(schools)},
        {"label": "TOTAL STUDENTS", "value": _fmt_int(students)},
        {"label": "TOTAL TEACHERS", "value": _fmt_int(teachers)},
        {"label": "PTR (NATIONAL)", "value": _fmt_ptr(summary.get("student_teacher_ratio"))},
        {"label": "STUDENTS/SCHOOL", "value": _fmt_int(students_per_school)},
    ]
    _render_kpi_cards(cards, per_row=3)

    st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)
    _render_subsection("🏆 Top 10 States by School Count")
    if not states_df.empty:
        df = states_df.sort_values("schools", ascending=False).head(10)
        fig = px.bar(df, x="state_name", y="schools", color_discrete_sequence=[INDIA_UI["schools"]])
        fig = _style_chart(fig, title="", x_title="State Name", y_title="Schools", height=420)
        st.plotly_chart(fig, use_container_width=True)


def render_au_state_dashboard() -> None:
    _inject_au_css()
    st.markdown('<div class="main-header">📊 State Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive State-Level Analysis with Advanced Filters</div>', unsafe_allow_html=True)

    states_df = _safe_state_df()
    if states_df.empty:
        st.warning("No Australia state data is available.")
        return

    filters = _state_sidebar_filters(states_df)
    schools_df = _apply_school_filters(_safe_school_df(
        state_name=filters.get("state_name"),
        district_name=filters.get("district_name"),
        management_type=None,
        school_level=None,
        delivery_model=None,
        search=filters.get("search"),
        limit=filters.get("limit", 20000),
        offset=0,
    ), filters)

    overview = _aggregate_state_overview(schools_df)
    cards = [
        {"label": "TOTAL SCHOOLS", "value": _fmt_int(overview["total_schools"])},
        {"label": "SCHOOLS WITH ENROLLMENT", "value": _fmt_int(overview["schools_with_enrollment"])},
        {"label": "TOTAL DISTRICTS", "value": _fmt_int(overview["total_districts"])},
        {"label": "TOTAL STUDENTS", "value": _fmt_int(overview["total_students"])},
        {"label": "MALE STUDENTS", "value": _fmt_int(overview["male_students"])},
        {"label": "FEMALE STUDENTS", "value": _fmt_int(overview["female_students"])},
        {"label": "TOTAL TEACHERS", "value": _fmt_int(overview["total_teachers"])},
        {"label": "PTR (STATE)", "value": overview["state_ptr"]},
    ]
    _render_kpi_cards(cards, per_row=4)

    district_df = _district_analysis(schools_df)
    _render_subsection("District PTR Analysis")
    _display_df(district_df[[c for c in ["district_name", "total_schools", "total_students", "total_teachers", "PTR"] if c in district_df.columns]])

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        _render_subsection("District-wise Students")
        if not district_df.empty:
            fig = px.bar(district_df.head(15), x="district_name", y="total_students", color_discrete_sequence=[INDIA_UI["students"]])
            fig = _style_chart(fig, title="", x_title="District", y_title="Students", height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No district data available.")
    with col2:
        _render_subsection("District-wise PTR")
        if not district_df.empty:
            fig = px.line(district_df.head(15), x="district_name", y="ptr_ratio", markers=True)
            fig = _style_chart(fig, title="", x_title="District", y_title="PTR", height=380)
            fig.update_yaxes(ticksuffix=":1")
            for tr in fig.data:
                tr.name = "PTR"
                tr.line.color = INDIA_UI["ptr"]
                tr.marker.color = INDIA_UI["ptr"]
                tr.hovertemplate = "District=%{x}<br>PTR=%{y:.0f}:1<extra></extra>"
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No PTR data available.")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    _render_subsection("Grade-wise Enrollment Breakdown")
    grade_df = _fetch_grade_enrollment(filters)
    if not grade_df.empty:
        fig = px.bar(grade_df, x="grade_label", y="enrolled_students", color_discrete_sequence=[INDIA_UI["students"]])
        fig = _style_chart(fig, title="", x_title="Grade", y_title="Students", height=380)
        st.plotly_chart(fig, use_container_width=True)
        _display_df(grade_df)
    else:
        st.info("No grade enrollment data available for current filters.")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    _render_subsection("School Directory")
    school_cols = [c for c in ["school_id", "school_name", "district_name", "suburb", "postcode", "management_type", "school_level", "total_students", "fte_teaching_staff", "student_teacher_ratio"] if c in schools_df.columns]
    display_df = schools_df[school_cols].copy() if school_cols else schools_df.copy()
    if not display_df.empty and "total_students" in display_df.columns:
        display_df = display_df.sort_values("total_students", ascending=False, na_position="last")
    _display_df(display_df)


def render_au_analytics() -> None:
    _inject_au_css()
    _render_top_header("Education Analytics - Australia 2025")
    _render_section_header("Analytics", icon="📈")

    base_states_df = _safe_state_df()
    filters = _analytics_sidebar_filters(base_states_df)
    school_filters = {
        "state_name": filters.get("state_name"),
        "district_name": filters.get("district_name"),
        "management_type": None,
        "school_level": None,
        "delivery_model": None,
        "search": None,
        "limit": 20000,
        "offset": 0,
    }
    schools_df = _safe_school_df(**school_filters)

    if filters.get("state_name"):
        states_df = base_states_df[base_states_df["state_name"] == filters["state_name"]].copy()
    else:
        states_df = base_states_df.copy()

    agg_data = _analytics_aggregate(schools_df if not schools_df.empty else pd.DataFrame())
    _render_metric_cards_overview(agg_data)

    tabs = st.tabs(["Overview", "District Analysis", "Comparative Analysis", "Custom Reports"])

    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            _render_subsection("State-wise Total Students")
            if not states_df.empty:
                fig = px.bar(states_df.sort_values("total_students", ascending=False), x="state_name", y="total_students", color_discrete_sequence=[INDIA_UI["students"]])
                fig = _style_chart(fig, title="", x_title="State", y_title="Students", height=400)
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            _render_subsection("State-wise Teachers")
            if not states_df.empty:
                fig = px.bar(states_df.sort_values("fte_teaching_staff", ascending=False), x="state_name", y="fte_teaching_staff", color_discrete_sequence=[INDIA_UI["teachers"]])
                fig = _style_chart(fig, title="", x_title="State", y_title="Teachers", height=400)
                st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        _render_subsection("District Analysis")
        selected_state = filters.get("state_name") or (base_states_df["state_name"].iloc[0] if not base_states_df.empty else None)
        district_df = _safe_district_df(selected_state) if selected_state else pd.DataFrame()
        if filters.get("district_name") and not district_df.empty:
            district_df = district_df[district_df["district_name"] == filters["district_name"]]
        _display_df(district_df)
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if not district_df.empty:
            fig = px.bar(district_df.sort_values("total_students", ascending=False).head(20), x="district_name", y="total_students", color_discrete_sequence=[INDIA_UI["students"]])
            fig = _style_chart(fig, title="", x_title="District", y_title="Students", height=420)
            st.plotly_chart(fig, use_container_width=True)

    with tabs[2]:
        st.markdown("### 🔍 Comparative Analysis Tool")
        st.markdown("Compare two locations side-by-side across all key metrics")
        comp_level = st.radio("Comparison Level", ["State vs State", "District vs District"], horizontal=True, key="comp_level")
        col1, col2 = st.columns(2)

        if comp_level == "State vs State":
            states = base_states_df["state_name"].dropna().tolist() if "state_name" in base_states_df.columns else []
            with col1:
                st.markdown("#### 📍 Location 1")
                state1 = st.selectbox("State", states, key="comp_state1")
            with col2:
                st.markdown("#### 📍 Location 2")
                state2 = st.selectbox("State", states, key="comp_state2")
            if st.button("🔄 Compare", type="primary"):
                comparison = _comparison_df_state(base_states_df, state1, state2)
                if not comparison.empty:
                    st.dataframe(comparison.rename(columns=lambda x: x.replace("_", " ").title().replace("Ptr", "PTR")), use_container_width=True, hide_index=True)
                    csv = comparison.to_csv(index=False)
                    st.download_button("📥 Download Comparison CSV", csv, f"comparison_{state1}_vs_{state2}.csv", "text/csv")
        else:
            states = base_states_df["state_name"].dropna().tolist() if "state_name" in base_states_df.columns else []
            with col1:
                st.markdown("#### 📍 Location 1")
                state1 = st.selectbox("State", states, key="comp_dist_state1")
                districts1 = _safe_district_df(state1).get("district_name", pd.Series(dtype=str)).dropna().tolist() if state1 else []
                district1 = st.selectbox("District", districts1, key="comp_district1") if districts1 else None
            with col2:
                st.markdown("#### 📍 Location 2")
                state2 = st.selectbox("State", states, key="comp_dist_state2")
                districts2 = _safe_district_df(state2).get("district_name", pd.Series(dtype=str)).dropna().tolist() if state2 else []
                district2 = st.selectbox("District", districts2, key="comp_district2") if districts2 else None
            if st.button("🔄 Compare", type="primary", key="comp_dist_btn") and district1 and district2:
                comparison = _comparison_df_district(state1, district1, state2, district2)
                if not comparison.empty:
                    st.dataframe(comparison.rename(columns=lambda x: x.replace("_", " ").title().replace("Ptr", "PTR")), use_container_width=True, hide_index=True)

    with tabs[3]:
        st.markdown("### 📝 Custom Report Builder")
        st.markdown("Build custom reports with flexible dimensions and metrics")
        st.markdown("#### Step 1: Select Dimensions")
        dimensions = st.multiselect("Choose grouping dimensions", ["State", "District", "Management", "School Level"], default=["State"], key="report_dims")
        st.markdown("#### Step 2: Select Metrics")
        metrics = st.multiselect("Choose metrics to include", ["Schools", "Students", "Teachers", "PTR"], default=["Schools", "Students", "PTR"], key="report_metrics")

        if st.button("📊 Generate Report", type="primary"):
            if not dimensions or not metrics:
                st.warning("Please select at least one dimension and one metric")
            else:
                with st.spinner("Generating report..."):
                    df_report = schools_df.copy()
                    if df_report.empty:
                        st.warning("No data found for selected criteria")
                    else:
                        dim_map = {
                            "State": "state_name",
                            "District": "district_name",
                            "Management": "management_type",
                            "School Level": "school_level",
                        }
                        group_cols = [dim_map[d] for d in dimensions if dim_map[d] in df_report.columns]
                        if not group_cols:
                            st.warning("Selected dimensions are not available")
                        else:
                            agg = df_report.groupby(group_cols, dropna=False).agg(
                                total_schools=("school_id", pd.Series.nunique),
                                total_students=("total_students", "sum"),
                                total_teachers=("fte_teaching_staff", "sum"),
                            ).reset_index()
                            agg["ptr"] = agg.apply(lambda r: round(r["total_students"] / r["total_teachers"]) if _num(r["total_teachers"]) > 0 else None, axis=1)
                            cols_to_show = group_cols.copy()
                            if "Schools" in metrics:
                                cols_to_show.append("total_schools")
                            if "Students" in metrics:
                                cols_to_show.append("total_students")
                            if "Teachers" in metrics:
                                cols_to_show.append("total_teachers")
                            if "PTR" in metrics:
                                cols_to_show.append("ptr")
                            df_display = agg[cols_to_show]
                            st.success(f"Report generated successfully! ({len(df_display)} rows)")
                            st.dataframe(df_display.rename(columns=lambda x: x.replace("_", " ").title().replace("Ptr", "PTR")), use_container_width=True, hide_index=True)
                            csv = df_display.to_csv(index=False)
                            st.download_button("📥 Download CSV", csv, "custom_report.csv", "text/csv")
                            try:
                                buffer = BytesIO()
                                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                                    df_display.to_excel(writer, index=False, sheet_name="Report")
                                buffer.seek(0)
                                st.download_button("📊 Download Excel", buffer, "custom_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                            except Exception:
                                pass
