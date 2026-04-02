from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

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
    "state_name": "State Name",
    "state_abbr": "State Abbr",
    "district_name": "District Name",
    "school_id": "School ID",
    "school_name": "School Name",
    "suburb": "Suburb",
    "postcode": "Postcode",
    "management_type": "Management Type",
    "school_level": "School Level",
    "delivery_model": "Delivery Model",
    "schools": "Schools",
    "total_students": "Total Students",
    "girls_students": "Girls",
    "boys_students": "Boys",
    "fte_teaching_staff": "Total Teachers",
    "student_teacher_ratio": "PTR",
    "weighted_avg_icsea": "Avg ICSEA",
    "weighted_indigenous_pct": "Indigenous %",
    "weighted_lbote_yes_pct": "LBOTE %",
    "grade_code": "Grade Code",
    "grade_label": "Grade Label",
    "enrolled_students": "Enrolled Students",
}

INT_LIKE_COLUMNS = {
    "schools",
    "total_students",
    "girls_students",
    "boys_students",
    "enrolled_students",
    "fte_teaching_staff",
}

FLOAT_2_COLUMNS = {
    "weighted_avg_icsea",
    "weighted_indigenous_pct",
    "weighted_lbote_yes_pct",
}


# -----------------------------
# DATA / SERVICE HELPERS
# -----------------------------
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


def _safe_school_detail(school_id: str) -> Dict[str, Any]:
    detail = _get_service().get_school_detail(school_id)
    return detail or {}


def _safe_grade_df(school_id: str) -> pd.DataFrame:
    return _to_dataframe(_get_service().get_grade_enrollment(school_id))


# -----------------------------
# FORMAT HELPERS
# -----------------------------
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


def _fmt_metric_value(metric_key: str, value: Any) -> str:
    if metric_key in {"total_states", "schools", "total_schools", "students_per_school"}:
        return _fmt_int(value)
    if metric_key in {"total_students", "girls_students", "boys_students", "total_teachers"}:
        return _fmt_int(value)
    if metric_key == "fte_teaching_staff":
        return _fmt_int(value)
    if metric_key == "student_teacher_ratio":
        return _fmt_ptr(value)
    if metric_key == "weighted_avg_icsea":
        return _fmt_float(value, 2)
    if metric_key in {"weighted_indigenous_pct", "weighted_lbote_yes_pct"}:
        return _fmt_pct(value, 2)
    if _is_missing(value):
        return "N/A"
    return str(value)


def _prettify_label(label: str) -> str:
    if label is None:
        return ""
    s = str(label).strip()
    if not s:
        return ""
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    words = []
    for part in s.split(" "):
        low = part.lower()
        if low in {"fte", "icsea", "lbote", "ptr"}:
            words.append(part.upper())
        elif low == "abbr":
            words.append("Abbr")
        else:
            words.append(part.capitalize())
    return " ".join(words)


def _normalize_label(label: str) -> str:
    s = str(label).strip()
    return COLUMN_TITLES.get(s, _prettify_label(s))


def _format_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    for col in out.columns:
        if col == "student_teacher_ratio":
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
    st.dataframe(
        _format_dataframe_for_display(df),
        use_container_width=use_container_width,
        hide_index=hide_index,
    )


# -----------------------------
# INDIA-LIKE STYLING
# -----------------------------
def _inject_au_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {INDIA_UI['page_bg']};
        }}
        .au-top-title {{
            text-align: center;
            color: {INDIA_UI['text']};
            font-size: 1.02rem;
            font-weight: 700;
            margin-top: 0.15rem;
            margin-bottom: 0.15rem;
        }}
        .au-top-rule {{
            border: none;
            border-top: 1px solid #E5E7EB;
            margin-top: 0.75rem;
            margin-bottom: 2.2rem;
        }}
        .au-section-hero {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 1.15rem;
        }}
        .au-section-icon {{
            font-size: 1.9rem;
            line-height: 1;
        }}
        .au-section-title {{
            color: {INDIA_UI['text']};
            font-size: 2.05rem;
            font-weight: 800;
            line-height: 1.12;
            margin: 0;
        }}
        .au-subsection-title {{
            color: {INDIA_UI['text']};
            font-size: 1.08rem;
            font-weight: 800;
            margin-top: 0.35rem;
            margin-bottom: 0.15rem;
        }}
        .au-subsection-subtitle {{
            color: {INDIA_UI['muted']};
            font-size: 0.93rem;
            margin-bottom: 0.8rem;
        }}
        .au-kpi-card {{
            background: {INDIA_UI['card_bg']};
            border: 2px solid {INDIA_UI['border']};
            border-radius: 12px;
            padding: 18px 16px 18px 16px;
            box-shadow: {INDIA_UI['shadow']};
            min-height: 94px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .au-kpi-label {{
            color: #7E7E7E;
            font-size: 0.83rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-bottom: 10px;
            line-height: 1.15;
        }}
        .au-kpi-value {{
            color: {INDIA_UI['primary_blue']};
            font-size: 1.98rem;
            font-weight: 800;
            line-height: 1.05;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-variant-numeric: tabular-nums;
        }}
        .au-grid-gap {{
            height: 18px;
        }}
        div[data-testid="stDataFrame"] {{
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #E5E7EB;
            background: white;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_india_style_top_header(title: str) -> None:
    st.markdown(f'<div class="au-top-title">{title}</div>', unsafe_allow_html=True)
    st.markdown('<hr class="au-top-rule"/>', unsafe_allow_html=True)


def _render_india_style_section_header(title: str, icon: str = "📊") -> None:
    st.markdown(
        f'''
        <div class="au-section-hero">
            <div class="au-section-icon">{icon}</div>
            <div class="au-section-title">{title}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def _render_subsection(title: str, subtitle: Optional[str] = None) -> None:
    st.markdown(f'<div class="au-subsection-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="au-subsection-subtitle">{subtitle}</div>', unsafe_allow_html=True)


# -----------------------------
# KPI BUILDERS
# -----------------------------
def _build_home_kpis(summary: Dict[str, Any], states_df: pd.DataFrame) -> List[Dict[str, Any]]:
    total_states = states_df["state_name"].nunique() if not states_df.empty and "state_name" in states_df.columns else 0
    total_students = summary.get("total_students")
    total_schools = summary.get("schools")
    total_teachers = summary.get("fte_teaching_staff")
    ptr = summary.get("student_teacher_ratio")

    students_per_school = None
    try:
        if total_students and total_schools:
            students_per_school = round(float(total_students) / float(total_schools))
    except Exception:
        students_per_school = None

    return [
        {"label": "TOTAL STATES/UTS", "value": _fmt_metric_value("total_states", total_states)},
        {"label": "TOTAL SCHOOLS", "value": _fmt_metric_value("total_schools", total_schools)},
        {"label": "TOTAL STUDENTS", "value": _fmt_metric_value("total_students", total_students)},
        {"label": "TOTAL TEACHERS", "value": _fmt_metric_value("total_teachers", total_teachers)},
        {"label": "PTR (NATIONAL)", "value": _fmt_metric_value("student_teacher_ratio", ptr)},
        {"label": "STUDENTS/SCHOOL", "value": _fmt_metric_value("students_per_school", students_per_school)},
    ]


def _build_state_kpis(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"label": "TOTAL SCHOOLS", "value": _fmt_metric_value("total_schools", metrics.get("schools"))},
        {"label": "TOTAL STUDENTS", "value": _fmt_metric_value("total_students", metrics.get("total_students"))},
        {"label": "TOTAL TEACHERS", "value": _fmt_metric_value("total_teachers", metrics.get("fte_teaching_staff"))},
        {"label": "PTR (STATE)", "value": _fmt_metric_value("student_teacher_ratio", metrics.get("student_teacher_ratio"))},
        {"label": "GIRLS", "value": _fmt_metric_value("girls_students", metrics.get("girls_students"))},
        {"label": "BOYS", "value": _fmt_metric_value("boys_students", metrics.get("boys_students"))},
    ]


def _build_analytics_kpis(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"label": "GIRLS", "value": _fmt_metric_value("girls_students", summary.get("girls_students"))},
        {"label": "BOYS", "value": _fmt_metric_value("boys_students", summary.get("boys_students"))},
        {"label": "AVG ICSEA", "value": _fmt_metric_value("weighted_avg_icsea", summary.get("weighted_avg_icsea"))},
        {"label": "INDIGENOUS %", "value": _fmt_metric_value("weighted_indigenous_pct", summary.get("weighted_indigenous_pct"))},
        {"label": "LBOTE %", "value": _fmt_metric_value("weighted_lbote_yes_pct", summary.get("weighted_lbote_yes_pct"))},
        {"label": "PTR (NATIONAL)", "value": _fmt_metric_value("student_teacher_ratio", summary.get("student_teacher_ratio"))},
    ]


def _render_kpi_cards(cards: List[Dict[str, Any]], per_row: int = 3) -> None:
    if not cards:
        return
    for i in range(0, len(cards), per_row):
        row = cards[i:i + per_row]
        cols = st.columns(per_row)
        for idx, card in enumerate(row):
            with cols[idx]:
                st.markdown(
                    f'''
                    <div class="au-kpi-card">
                        <div class="au-kpi-label">{card['label']}</div>
                        <div class="au-kpi-value">{card['value']}</div>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )
        if i + per_row < len(cards):
            st.markdown('<div class="au-grid-gap"></div>', unsafe_allow_html=True)


# -----------------------------
# AGGREGATION HELPERS
# -----------------------------
def _aggregate_filtered_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df is None or df.empty:
        return {
            "schools": 0,
            "total_students": 0,
            "girls_students": 0,
            "boys_students": 0,
            "fte_teaching_staff": 0,
            "student_teacher_ratio": None,
        }

    schools = df["school_id"].nunique() if "school_id" in df.columns else len(df)
    total_students = _num(df["total_students"].fillna(0).sum()) if "total_students" in df.columns else 0
    girls_students = _num(df["girls_students"].fillna(0).sum()) if "girls_students" in df.columns else None
    boys_students = _num(df["boys_students"].fillna(0).sum()) if "boys_students" in df.columns else None
    teachers = _num(df["fte_teaching_staff"].fillna(0).sum()) if "fte_teaching_staff" in df.columns else 0
    ptr = (total_students / teachers) if teachers and total_students else None

    return {
        "schools": schools,
        "total_students": total_students,
        "girls_students": girls_students,
        "boys_students": boys_students,
        "fte_teaching_staff": teachers,
        "student_teacher_ratio": ptr,
    }


def _group_school_metrics(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if df is None or df.empty or group_col not in df.columns:
        return pd.DataFrame()

    agg_map = {}
    for col in ["total_students", "girls_students", "boys_students", "fte_teaching_staff"]:
        if col in df.columns:
            agg_map[col] = "sum"
    if "school_id" in df.columns:
        agg_map["school_id"] = pd.Series.nunique

    grouped = df.groupby(group_col, dropna=False).agg(agg_map).reset_index()
    if "school_id" in grouped.columns:
        grouped = grouped.rename(columns={"school_id": "schools"})
    else:
        grouped["schools"] = 0

    if "total_students" in grouped.columns and "fte_teaching_staff" in grouped.columns:
        grouped["student_teacher_ratio"] = grouped.apply(
            lambda r: (r["total_students"] / r["fte_teaching_staff"]) if _num(r.get("fte_teaching_staff")) > 0 else None,
            axis=1,
        )

    if group_col == "district_name":
        order_cols = [group_col, "schools", "total_students", "girls_students", "boys_students", "fte_teaching_staff", "student_teacher_ratio"]
    else:
        order_cols = [group_col, "schools", "total_students", "girls_students", "boys_students", "fte_teaching_staff", "student_teacher_ratio"]

    final_cols = [c for c in order_cols if c in grouped.columns]
    grouped = grouped[final_cols]
    if "total_students" in grouped.columns:
        grouped = grouped.sort_values("total_students", ascending=False, na_position="last")
    return grouped


def _weighted_average(df: pd.DataFrame, value_col: str, weight_col: str = "total_students") -> Optional[float]:
    if df is None or df.empty or value_col not in df.columns or weight_col not in df.columns:
        return None
    valid = df[[value_col, weight_col]].dropna()
    if valid.empty:
        return None
    total_weight = valid[weight_col].sum()
    if total_weight == 0:
        return None
    return float((valid[value_col] * valid[weight_col]).sum() / total_weight)


def _analytics_summary_from_states(states_df: pd.DataFrame) -> Dict[str, Any]:
    if states_df is None or states_df.empty:
        return {}
    out = {
        "girls_students": _num(states_df["girls_students"].sum()) if "girls_students" in states_df.columns else None,
        "boys_students": _num(states_df["boys_students"].sum()) if "boys_students" in states_df.columns else None,
        "weighted_avg_icsea": _weighted_average(states_df, "weighted_avg_icsea"),
        "weighted_indigenous_pct": _weighted_average(states_df, "weighted_indigenous_pct"),
        "weighted_lbote_yes_pct": _weighted_average(states_df, "weighted_lbote_yes_pct"),
        "student_teacher_ratio": None,
    }
    if {"total_students", "fte_teaching_staff"}.issubset(set(states_df.columns)):
        students = _num(states_df["total_students"].sum())
        teachers = _num(states_df["fte_teaching_staff"].sum())
        out["student_teacher_ratio"] = (students / teachers) if teachers else None
    return out


# -----------------------------
# CHART STYLING
# -----------------------------
def _style_chart(fig, title: Optional[str] = None, x_title: Optional[str] = None, y_title: Optional[str] = None, height: int = 430):
    fig.update_layout(
        title={
            "text": title or "",
            "x": 0.0,
            "xanchor": "left",
            "font": {"size": 18, "color": INDIA_UI["text"]},
        },
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=height,
        margin=dict(l=8, r=8, t=50, b=8),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            title_text="",
        ),
        font=dict(color=INDIA_UI["text"]),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E5E7EB", title_text=x_title)
    fig.update_yaxes(showgrid=True, gridcolor="#EEF2F7", zeroline=False, title_text=y_title, separatethousands=True)
    return fig


def _render_gender_chart(summary: Dict[str, Any]) -> None:
    chart_df = pd.DataFrame(
        {
            "Category": ["Girls", "Boys"],
            "Students": [summary.get("girls_students", 0) or 0, summary.get("boys_students", 0) or 0],
        }
    )
    fig = px.bar(
        chart_df,
        x="Category",
        y="Students",
        color="Category",
        color_discrete_map={"Girls": INDIA_UI["girls"], "Boys": INDIA_UI["boys"]},
    )
    fig = _style_chart(fig, title="Gender Split", x_title="", y_title="Students", height=370)
    st.plotly_chart(fig, use_container_width=True)


def _render_top_states_by_students(states_df: pd.DataFrame) -> None:
    if states_df.empty or "total_students" not in states_df.columns:
        st.info("No state student data available.")
        return
    df = states_df.sort_values("total_students", ascending=False)
    fig = px.bar(df, x="state_name", y="total_students", color_discrete_sequence=[INDIA_UI["students"]])
    fig = _style_chart(fig, title="State-wise Total Students", x_title="State Name", y_title="Students", height=370)
    st.plotly_chart(fig, use_container_width=True)


def _render_top_states_by_schools(states_df: pd.DataFrame) -> None:
    if states_df.empty or "schools" not in states_df.columns:
        st.info("No state school data available.")
        return
    df = states_df.sort_values("schools", ascending=False).head(10)
    fig = px.bar(df, x="state_name", y="schools", color_discrete_sequence=[INDIA_UI["schools"]])
    fig = _style_chart(fig, title="", x_title="State Name", y_title="Schools", height=420)
    st.plotly_chart(fig, use_container_width=True)


def _render_ptr_chart(states_df: pd.DataFrame) -> None:
    if states_df.empty or "student_teacher_ratio" not in states_df.columns:
        st.info("No PTR data available.")
        return
    df = states_df.sort_values("student_teacher_ratio", ascending=False)
    fig = px.line(df, x="state_name", y="student_teacher_ratio", markers=True)
    fig = _style_chart(fig, title="PTR by State", x_title="State Name", y_title="PTR", height=420)
    fig.update_yaxes(ticksuffix=":1")
    for tr in fig.data:
        try:
            tr.name = "PTR"
            tr.line.color = INDIA_UI["ptr"]
            tr.marker.color = INDIA_UI["ptr"]
            tr.hovertemplate = "State Name=%{x}<br>PTR=%{y:.0f}:1<extra></extra>"
        except Exception:
            pass
    st.plotly_chart(fig, use_container_width=True)


def _render_indicator_chart(states_df: pd.DataFrame) -> None:
    required = {"state_name", "weighted_avg_icsea", "weighted_indigenous_pct", "weighted_lbote_yes_pct"}
    if states_df.empty or not required.issubset(set(states_df.columns)):
        st.info("No indicator data available.")
        return
    df = states_df[["state_name", "weighted_avg_icsea", "weighted_indigenous_pct", "weighted_lbote_yes_pct"]].copy()
    df = df.melt(id_vars="state_name", var_name="Metric", value_name="Value")
    fig = px.line(
        df,
        x="state_name",
        y="Value",
        color="Metric",
        markers=True,
        color_discrete_map={
            "weighted_avg_icsea": INDIA_UI["icsea"],
            "weighted_indigenous_pct": INDIA_UI["indigenous"],
            "weighted_lbote_yes_pct": INDIA_UI["lbote"],
        },
    )
    fig = _style_chart(fig, title="Academic & Demographic Indicators", x_title="State Name", y_title="Value", height=420)
    for tr in fig.data:
        try:
            name = tr.name
            if name == "weighted_avg_icsea":
                tr.name = "Weighted Avg ICSEA"
            elif name == "weighted_indigenous_pct":
                tr.name = "Weighted Indigenous %"
            elif name == "weighted_lbote_yes_pct":
                tr.name = "Weighted LBOTE %"
        except Exception:
            pass
    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
def _render_state_sidebar_filters(states_df: pd.DataFrame) -> Dict[str, Any]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### State Dashboard Filters")

    state_options = states_df["state_name"].dropna().tolist() if "state_name" in states_df.columns else []
    default_state = state_options[0] if state_options else None
    query_state = None
    try:
        query_state = st.query_params.get("state")
    except Exception:
        query_state = None
    if query_state and query_state in state_options:
        default_state = query_state
    if "au_selected_state" in st.session_state and st.session_state["au_selected_state"] in state_options:
        default_state = st.session_state["au_selected_state"]

    selected_state = st.sidebar.selectbox(
        "State",
        state_options,
        index=state_options.index(default_state) if default_state in state_options else 0,
        key="au_sidebar_state",
    ) if state_options else None

    st.session_state["au_selected_state"] = selected_state
    try:
        if selected_state:
            st.query_params["state"] = selected_state
    except Exception:
        pass

    district_df = _safe_district_df(selected_state) if selected_state else pd.DataFrame()
    district_options = sorted([d for d in district_df.get("district_name", pd.Series(dtype=str)).dropna().unique().tolist() if d]) if not district_df.empty else []

    filter_options = _get_service().get_filter_options() or {}
    management_types = filter_options.get("management_types", []) or []
    school_levels = filter_options.get("school_levels", []) or []

    selected_district = st.sidebar.selectbox("District", ["All"] + district_options, key="au_sidebar_district")
    selected_management = st.sidebar.selectbox("Management Type", ["All"] + management_types, key="au_sidebar_mgmt")
    selected_level = st.sidebar.selectbox("School Level", ["All"] + school_levels, key="au_sidebar_level")
    search = st.sidebar.text_input("Search School", value="", key="au_sidebar_search")

    return {
        "state_name": selected_state,
        "district_name": None if selected_district == "All" else selected_district,
        "management_type": None if selected_management == "All" else selected_management,
        "school_level": None if selected_level == "All" else selected_level,
        "delivery_model": None,
        "search": search or None,
        "limit": 20000,
        "offset": 0,
    }


def _render_analytics_sidebar_filters(states_df: pd.DataFrame) -> Dict[str, Any]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Analytics Filters")

    state_options = ["All States"] + (states_df["state_name"].dropna().tolist() if "state_name" in states_df.columns else [])
    selected_state = st.sidebar.selectbox("State Scope", state_options, key="au_analytics_state_scope")

    return {
        "selected_state": None if selected_state == "All States" else selected_state,
    }


# -----------------------------
# PUBLIC RENDER FUNCTIONS
# -----------------------------
def render_au_home() -> None:
    _inject_au_css()
    svc = _get_service()
    summary = svc.get_national_summary() or {}
    states_df = _safe_state_df()

    _render_india_style_top_header("National K-12 Education Overview - Australia 2025")
    _render_india_style_section_header("National Overview", icon="📊")

    home_kpis = _build_home_kpis(summary, states_df)
    _render_kpi_cards(home_kpis, per_row=3)

    st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)

    _render_subsection("🏆 Top 10 States by School Count")
    _render_top_states_by_schools(states_df)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    left, right = st.columns([1, 1])
    with left:
        _render_subsection("National Gender Overview", "Girls and boys student counts for Australia.")
        _render_gender_chart(summary)
    with right:
        _render_subsection("State Distribution", "State-wise student totals across Australia.")
        _render_top_states_by_students(states_df)


def render_au_state_dashboard() -> None:
    _inject_au_css()
    states_df = _safe_state_df()

    _render_india_style_top_header("State-level Education Dashboard - Australia 2025")
    _render_india_style_section_header("State Dashboard", icon="📍")

    if states_df.empty or "state_name" not in states_df.columns:
        st.warning("No Australia state data is available.")
        return

    filters = _render_state_sidebar_filters(states_df)
    selected_state = filters.get("state_name")

    filtered_schools_df = _safe_school_df(**filters)
    filtered_metrics = _aggregate_filtered_metrics(filtered_schools_df)

    state_kpis = _build_state_kpis(filtered_metrics)
    _render_kpi_cards(state_kpis, per_row=3)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    district_summary_df = _group_school_metrics(filtered_schools_df, "district_name") if "district_name" in filtered_schools_df.columns else pd.DataFrame()

    _render_subsection(
        f"District Summary - {selected_state}",
        "Filtered totals update automatically from sidebar selections to match India-style dashboard behavior.",
    )
    _display_df(district_summary_df)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        _render_subsection("Top Districts by Students")
        if not district_summary_df.empty and {"district_name", "total_students"}.issubset(set(district_summary_df.columns)):
            chart_df = district_summary_df.head(15)
            fig = px.bar(chart_df, x="district_name", y="total_students", color_discrete_sequence=[INDIA_UI["students"]])
            fig = _style_chart(fig, title="", x_title="District Name", y_title="Students", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No district student data available.")

    with col2:
        _render_subsection("Top Districts by Schools")
        if not district_summary_df.empty and {"district_name", "schools"}.issubset(set(district_summary_df.columns)):
            chart_df = district_summary_df.head(15)
            fig = px.bar(chart_df, x="district_name", y="schools", color_discrete_sequence=[INDIA_UI["schools"]])
            fig = _style_chart(fig, title="", x_title="District Name", y_title="Schools", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No district school data available.")

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    mgmt_summary_df = _group_school_metrics(filtered_schools_df, "management_type") if "management_type" in filtered_schools_df.columns else pd.DataFrame()
    level_summary_df = _group_school_metrics(filtered_schools_df, "school_level") if "school_level" in filtered_schools_df.columns else pd.DataFrame()

    col3, col4 = st.columns([1, 1])
    with col3:
        _render_subsection("Management Type Distribution")
        if not mgmt_summary_df.empty and {"management_type", "total_students"}.issubset(set(mgmt_summary_df.columns)):
            fig = px.bar(
                mgmt_summary_df,
                x="management_type",
                y="total_students",
                color="management_type",
                color_discrete_map={
                    "Government": INDIA_UI["government"],
                    "Catholic": INDIA_UI["catholic"],
                    "Independent": INDIA_UI["independent"],
                },
            )
            fig = _style_chart(fig, title="", x_title="Management Type", y_title="Students", height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No management distribution available.")

    with col4:
        _render_subsection("School Level Distribution")
        if not level_summary_df.empty and {"school_level", "schools"}.issubset(set(level_summary_df.columns)):
            fig = px.bar(level_summary_df, x="school_level", y="schools", color_discrete_sequence=[INDIA_UI["schools"]])
            fig = _style_chart(fig, title="", x_title="School Level", y_title="Schools", height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No school level distribution available.")

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
    _render_subsection("School Directory")

    school_cols = [
        c for c in [
            "school_id",
            "school_name",
            "district_name",
            "suburb",
            "postcode",
            "management_type",
            "school_level",
            "delivery_model",
            "total_students",
            "fte_teaching_staff",
            "student_teacher_ratio",
        ] if c in filtered_schools_df.columns
    ]
    display_schools_df = filtered_schools_df[school_cols].copy() if school_cols else filtered_schools_df.copy()
    if not display_schools_df.empty and "total_students" in display_schools_df.columns:
        display_schools_df = display_schools_df.sort_values("total_students", ascending=False, na_position="last")
    _display_df(display_schools_df)


def render_au_analytics() -> None:
    _inject_au_css()
    base_states_df = _safe_state_df()

    _render_india_style_top_header("Education Analytics - Australia 2025")
    _render_india_style_section_header("Analytics", icon="📈")

    analytics_filters = _render_analytics_sidebar_filters(base_states_df)
    selected_state = analytics_filters.get("selected_state")

    if selected_state:
        states_df = base_states_df.loc[base_states_df["state_name"] == selected_state].copy()
        schools_df = _safe_school_df(state_name=selected_state, district_name=None, management_type=None, school_level=None, delivery_model=None, search=None, limit=20000, offset=0)
    else:
        states_df = base_states_df.copy()
        schools_df = _safe_school_df(state_name=None, district_name=None, management_type=None, school_level=None, delivery_model=None, search=None, limit=20000, offset=0)

    summary = _analytics_summary_from_states(states_df)
    analytics_kpis = _build_analytics_kpis(summary)
    _render_kpi_cards(analytics_kpis, per_row=3)

    tab1, tab2, tab3, tab4 = st.tabs([
        "Enrollment Analysis",
        "Teachers & PTR",
        "Equity Metrics",
        "Data Tables",
    ])

    with tab1:
        left, right = st.columns([1, 1])
        with left:
            _render_subsection("State-wise Total Students")
            _render_top_states_by_students(states_df)
        with right:
            _render_subsection("Gender Split")
            _render_gender_chart(summary)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        _render_subsection("Management Mix")
        mgmt_summary_df = _group_school_metrics(schools_df, "management_type") if "management_type" in schools_df.columns else pd.DataFrame()
        if not mgmt_summary_df.empty and {"management_type", "total_students"}.issubset(set(mgmt_summary_df.columns)):
            fig = px.bar(
                mgmt_summary_df,
                x="management_type",
                y="total_students",
                color="management_type",
                color_discrete_map={
                    "Government": INDIA_UI["government"],
                    "Catholic": INDIA_UI["catholic"],
                    "Independent": INDIA_UI["independent"],
                },
            )
            fig = _style_chart(fig, title="", x_title="Management Type", y_title="Students", height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No management mix data available.")

    with tab2:
        left, right = st.columns([1, 1])
        with left:
            _render_subsection("PTR by State")
            _render_ptr_chart(states_df)
        with right:
            _render_subsection("Teachers by State")
            if not states_df.empty and {"state_name", "fte_teaching_staff"}.issubset(set(states_df.columns)):
                fig = px.bar(states_df.sort_values("fte_teaching_staff", ascending=False), x="state_name", y="fte_teaching_staff", color_discrete_sequence=[INDIA_UI["teachers"]])
                fig = _style_chart(fig, title="", x_title="State Name", y_title="Total Teachers", height=420)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No teacher data available.")

    with tab3:
        left, right = st.columns([1, 1])
        with left:
            _render_subsection("Academic & Demographic Indicators")
            _render_indicator_chart(states_df)
        with right:
            _render_subsection("State-wise Avg ICSEA")
            if not states_df.empty and {"state_name", "weighted_avg_icsea"}.issubset(set(states_df.columns)):
                fig = px.bar(states_df.sort_values("weighted_avg_icsea", ascending=False), x="state_name", y="weighted_avg_icsea", color_discrete_sequence=[INDIA_UI["icsea"]])
                fig = _style_chart(fig, title="", x_title="State Name", y_title="Avg ICSEA", height=420)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No ICSEA data available.")

    with tab4:
        _render_subsection("State Analytics Grid")
        analytics_cols = [
            c for c in [
                "state_name",
                "schools",
                "total_students",
                "girls_students",
                "boys_students",
                "fte_teaching_staff",
                "student_teacher_ratio",
                "weighted_avg_icsea",
                "weighted_indigenous_pct",
                "weighted_lbote_yes_pct",
            ] if c in states_df.columns
        ]
        display_analytics_df = states_df[analytics_cols].copy() if analytics_cols else states_df.copy()
        if not display_analytics_df.empty and "total_students" in display_analytics_df.columns:
            display_analytics_df = display_analytics_df.sort_values("total_students", ascending=False)
        _display_df(display_analytics_df)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        _render_subsection("Management Summary Table")
        mgmt_summary_df = _group_school_metrics(schools_df, "management_type") if "management_type" in schools_df.columns else pd.DataFrame()
        _display_df(mgmt_summary_df)
