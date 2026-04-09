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


def _inject_au_home_css() -> None:
    st.markdown(
        """
        <style>
        /* India Home visual shell */
        .main {
            background-color: #F5F7FA;
            padding: 1rem;
        }

        .stApp {
            background: #F5F7FA;
        }

        [data-testid="stSidebar"] {
            background: white;
            color: #1f1f1f;
            border-right: 1px solid #E0E0E0;
        }

        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label {
            color: #1f1f1f !important;
        }

        div[data-baseweb="select"] {
            color: #1f1f1f !important;
            background: white !important;
        }

        div[data-baseweb="select"] * {
            color: #1f1f1f !important;
        }

        .stSelectbox div[role="button"],
        .stSelectbox div[role="button"] * {
            color: #1f1f1f !important;
        }

        div[data-baseweb="popover"] {
            background: white !important;
        }

        ul[role="listbox"] li {
            color: #1f1f1f !important;
            background: white !important;
            padding: 0.5rem 1rem;
        }

        ul[role="listbox"] li:hover {
            background: #0068C9 !important;
            color: white !important;
        }

        /* India metric card styling */
        [data-testid="stMetric"] {
            background: white;
            padding: 1.25rem;
            border-radius: 8px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            margin-bottom: 1rem;
        }

        [data-testid="stMetricLabel"] {
            font-size: 1.5rem !important;
            color: #616161 !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            max-width: none !important;
            min-width: max-content !important;
        }

        [data-testid="stMetricDelta"] {
            font-size: 1.5rem !important;
            font-weight: 600 !important;
        }

        /* India chart/table shell */
        [data-testid="stPlotlyChart"] {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            margin-bottom: 1.5rem;
        }

        [data-testid="stDataFrame"] {
            background: white;
            border-radius: 8px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            padding: 1rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            margin-bottom: 1.5rem;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            background: white;
        }

        th {
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #1565C0;
        }

        td {
            padding: 0.75rem;
            border-bottom: 1px solid #E0E0E0;
            color: #424242;
        }

        tr:hover {
            background-color: #F5F7FA;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .stButton > button {
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }

        .stButton > button:hover {
            background: linear-gradient(135deg, #1976d2 0%, #1565C0 100%);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }

        .stDownloadButton > button {
            background: linear-gradient(135deg, #43A047 0%, #388E3C 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
        }

        hr {
            margin: 2rem 0;
            border: none;
            border-top: 2px solid #E0E0E0;
        }

        .au-top-title,
        .au-top-rule,
        .au-section-hero,
        .au-section-icon,
        .au-section-title,
        .au-subsection-title,
        .au-subsection-subtitle,
        .au-grid-gap {
            all: unset;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_au_css() -> None:
    st.markdown(
        f"""
        <style>
        .main {{
            background-color: #F5F7FA;
            padding: 1rem;
        }}

        .stApp {{
            background: #F5F7FA;
        }}

        [data-testid="stMetric"] {{
            background: white;
            padding: 1.25rem;
            border-radius: 8px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            margin-bottom: 1rem;
        }}

        [data-testid="stMetricLabel"] {{
            font-size: 1.5rem !important;
            color: #616161;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        [data-testid="stMetricValue"] {{
            font-size: 1.5rem !important;
            font-weight: 700;
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            max-width: none !important;
            min-width: max-content !important;
        }}

        [data-testid="stPlotlyChart"] {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            margin-bottom: 1.5rem;
        }}

        [data-testid="stDataFrame"] {{
            background: white;
            border-radius: 8px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            padding: 1rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            margin-bottom: 1.5rem;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            background: white;
        }}

        th {{
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white;
            padding: 0.75rem;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #1565C0;
        }}

        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #E0E0E0;
            color: #424242;
        }}

        tr:hover {{
            background-color: #F5F7FA;
        }}

        .main-header {{
            font-size: 1.5rem !important;
            font-weight: 700;
            color: #1f1f1f;
            border-bottom: 3px solid #1e88e5;
            padding-bottom: 0.5rem;
            margin-bottom: 0.35rem;
        }}

        .sub-header {{
            font-size: 1rem;
            color: #616161;
            margin-bottom: 1.25rem;
        }}

        .section-header {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #1565C0;
            background: #E3F2FD;
            padding: 8px 14px;
            border-radius: 6px;
            margin: 18px 0 12px 0;
            border-left: 4px solid #1e88e5;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.5rem;
        }}

        .stTabs [data-baseweb="tab"] {{
            background: white;
            border: 2px solid #1e88e5;
            border-radius: 8px 8px 0 0;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            color: #1565C0;
        }}

        .stTabs [aria-selected="true"] {{
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white;
        }}

        .stButton > button {{
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }}

        .stDownloadButton > button {{
            background: linear-gradient(135deg, #43A047 0%, #388E3C 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
        }}

        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #1e88e5 0%, #1976d2 100%);
            color: white;
        }}

        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label {{
            color: white !important;
        }}

        div[data-baseweb="select"] {{
            color: #1f1f1f !important;
            background: white !important;
        }}

        div[data-baseweb="select"] * {{
            color: #1f1f1f !important;
        }}

        .stSelectbox div[role="button"],
        .stSelectbox div[role="button"] * {{
            color: #1f1f1f !important;
        }}

        div[data-baseweb="popover"] {{
            background: white !important;
        }}

        ul[role="listbox"] li {{
            color: #1f1f1f !important;
            background: white !important;
            padding: 0.5rem 1rem;
        }}

        ul[role="listbox"] li:hover {{
            background: #0068C9 !important;
            color: white !important;
        }}

        .au-top-title,
        .au-top-rule,
        .au-section-hero,
        .au-section-icon,
        .au-section-title,
        .au-subsection-title,
        .au-subsection-subtitle,
        .au-grid-gap {{
            all: unset;
        }}

        .au-kpi-card {{
            background: white;
            padding: 1.25rem;
            border-radius: 8px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            margin-bottom: 1rem;
            display: block;
        }}

        .au-kpi-label {{
            font-size: 1.5rem !important;
            color: #616161;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: block;
            margin-bottom: 0.35rem;
        }}

        .au-kpi-value {{
            font-size: 1.5rem !important;
            font-weight: 700;
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            display: block;
            white-space: nowrap;
        }}
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
                st.metric(
                    label=str(card.get("label", "")),
                    value=str(card.get("value", "")),
                )
        if i + per_row < len(cards):
            st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)


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
    state = st.sidebar.selectbox("🗺️ Select State/Territory", state_options, index=state_options.index(default_state) if default_state in state_options else 0, key="au_state_filter") if state_options else None
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
    out = df.copy()
    if "school_id" not in out.columns:
        out["school_id"] = range(1, len(out) + 1)
    if "total_students" not in out.columns:
        out["total_students"] = 0
    if "fte_teaching_staff" not in out.columns:
        out["fte_teaching_staff"] = 0
    grp = out.groupby("district_name", dropna=False).agg(
        total_schools=("school_id", pd.Series.nunique),
        total_students=("total_students", "sum"),
        total_teachers=("fte_teaching_staff", "sum"),
    ).reset_index()
    grp["ptr_ratio"] = grp.apply(
        lambda r: (r["total_students"] / r["total_teachers"]) if _num(r["total_teachers"]) > 0 else None,
        axis=1
    )
    grp["PTR"] = grp["ptr_ratio"].apply(_fmt_ptr)
    return grp.sort_values(["total_students", "total_schools"], ascending=[False, False], na_position="last")


def _group_metrics(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if df is None or df.empty or col not in df.columns:
        return pd.DataFrame()
    out = df.copy()
    if "school_id" not in out.columns:
        out["school_id"] = range(1, len(out) + 1)
    if "total_students" not in out.columns:
        out["total_students"] = 0
    if "fte_teaching_staff" not in out.columns:
        out["fte_teaching_staff"] = 0
    grp = out.groupby(col, dropna=False).agg(
        total_schools=("school_id", pd.Series.nunique),
        total_students=("total_students", "sum"),
        total_teachers=("fte_teaching_staff", "sum"),
    ).reset_index()
    grp["ptr"] = grp.apply(
        lambda r: (r["total_students"] / r["total_teachers"]) if _num(r["total_teachers"]) > 0 else None,
        axis=1
    )
    grp["PTR"] = grp["ptr"].apply(_fmt_ptr)
    return grp.sort_values(["total_students", "total_schools"], ascending=[False, False], na_position="last")


def _analytics_aggregate(df: pd.DataFrame, states_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    total_schools = 0
    total_students = 0
    total_teachers = 0

    if states_df is not None and not states_df.empty:
        if "schools" in states_df.columns:
            total_schools = _num(states_df["schools"].fillna(0).sum())
        elif "school_id" in states_df.columns:
            total_schools = states_df["school_id"].nunique()

        if "total_students" in states_df.columns:
            total_students = _num(states_df["total_students"].fillna(0).sum())

        if "fte_teaching_staff" in states_df.columns:
            total_teachers = _num(states_df["fte_teaching_staff"].fillna(0).sum())

    if (total_schools == 0 or total_students == 0) and df is not None and not df.empty:
        if total_schools == 0:
            total_schools = df["school_id"].nunique() if "school_id" in df.columns else len(df)
        if total_students == 0 and "total_students" in df.columns:
            total_students = _num(df["total_students"].fillna(0).sum())
        if total_teachers == 0 and "fte_teaching_staff" in df.columns:
            total_teachers = _num(df["fte_teaching_staff"].fillna(0).sum())

    ptr = round(total_students / total_teachers) if total_teachers > 0 else None
    return {
        "total_schools": total_schools,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "ptr": ptr
    }


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
    schools = _num(agg_data.get("total_schools"))
    students = _num(agg_data.get("total_students"))
    teachers = _num(agg_data.get("total_teachers"))
    ptr = agg_data.get("ptr")
    sps = round(students / schools, 2) if schools > 0 else None
    tps = round(teachers / schools, 2) if schools > 0 and teachers > 0 else None

    cards = [
        {"label": "Total Schools", "value": _fmt_int(schools)},
        {"label": "Total Students", "value": _fmt_int(students)},
        {"label": "Total Teachers", "value": _fmt_int(teachers)},
        {"label": "PTR", "value": _fmt_ptr(ptr) if ptr is not None else "N/A"},
        {"label": "Students per School", "value": _fmt_float(sps, 2) if sps is not None else "N/A"},
        {"label": "Teachers per School", "value": _fmt_float(tps, 2) if tps is not None else "N/A"},
    ]
    _render_kpi_cards(cards, per_row=3)


# -----------------------------
# RENDERERS
# -----------------------------

def render_au_home() -> None:
    # FINAL_UI_CLEANUP_PARITY_PATCH_V1
    # HOME_PARITY_PATCH_V1
    _inject_au_home_css()
    svc = _get_service()
    summary = svc.get_national_summary() or {}
    states_df = _safe_state_df()

    total_states = states_df["state_name"].nunique() if not states_df.empty and "state_name" in states_df.columns else 0
    total_schools = summary.get("schools")
    total_students = summary.get("total_students")
    total_teachers = summary.get("fte_teaching_staff")
    ptr_value = summary.get("student_teacher_ratio")
    students_per_school = round(_num(total_students) / _num(total_schools)) if _num(total_schools) > 0 else None

    st.markdown('<div class="main-header">🏠 TutorCloud Global Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">National K-12 Education Overview - Australia 2025</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("## 📊 National Overview")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c1.metric("🗺️ Total States/Territories", _fmt_int(total_states))
    c2.metric("🏫 Total Schools", _fmt_int(total_schools))
    c3.metric("👥 Total Students", _fmt_int(total_students))
    c4.metric("👨‍🏫 Total Teachers", _fmt_int(total_teachers))
    c5.metric("📊 National PTR", _fmt_ptr(ptr_value))
    c6.metric("🏫 Students per School", _fmt_int(students_per_school) if students_per_school is not None else "N/A")

    st.markdown("## 🏆 Top 10 States/Territories by School Count")
    if not states_df.empty and {'state_name', 'schools'}.issubset(states_df.columns):
        df_sch = states_df.sort_values('schools', ascending=False).head(10).copy()
        fig = px.bar(
            df_sch,
            x='state_name',
            y='schools',
            labels={'schools': 'Total Schools', 'state_name': ''},
            color='schools',
            color_continuous_scale=['#E3F2FD', '#1E88E5'],
            text='schools',
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside', marker_line_color='white', marker_line_width=1.5, textfont_size=11)
        fig.update_layout(height=480, plot_bgcolor='white', paper_bgcolor='white', font={'family': 'Segoe UI', 'size': 11}, xaxis_tickangle=-45, showlegend=False, xaxis=dict(showgrid=False, title='', tickfont=dict(size=10)), yaxis=dict(showgrid=True, gridcolor='#F0F0F0', title='Total Schools'), margin=dict(l=70, r=50, t=50, b=150), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("## 📚 Top 20 States/Territories by Student Enrollment")
    if not states_df.empty and {'state_name', 'total_students'}.issubset(states_df.columns):
        df_std = states_df.sort_values('total_students', ascending=False).head(20).copy()
        fig = px.bar(
            df_std,
            x='state_name',
            y='total_students',
            labels={'total_students': 'Total Students', 'state_name': ''},
            color='total_students',
            color_continuous_scale=['#E3F2FD', '#1E88E5'],
            text='total_students',
        )
        fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside', marker_line_color='white', marker_line_width=1.5, textfont_size=10)
        fig.update_layout(height=480, plot_bgcolor='white', paper_bgcolor='white', font={'family': 'Segoe UI', 'size': 10}, xaxis_tickangle=-45, showlegend=False, xaxis=dict(showgrid=False, title='', tickfont=dict(size=9)), yaxis=dict(showgrid=True, gridcolor='#F0F0F0', title='Total Students'), margin=dict(l=70, r=50, t=50, b=150), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("## 💡 Key Insights")
    i1, i2, i3 = st.columns(3)
    with i1:
        st.info(f"""
        **📚 School Coverage**

        Australia has **{_fmt_int(total_schools)}** schools serving **{_fmt_int(total_students)}** students across **{_fmt_int(total_states)}** states and territories.
        """)
    with i2:
        st.success(f"""
        **👨‍🏫 Teaching Staff**

        With **{_fmt_int(total_teachers)}** teachers nationwide, the national PTR stands at **{_fmt_ptr(ptr_value)}**, indicating the student-to-teacher ratio.
        """)
    with i3:
        st.warning(f"""
        **🏫 School Size**

        Average school size is **{_fmt_int(students_per_school) if students_per_school is not None else 'N/A'}** students per school, with variation across states and territories.
        """)

    st.markdown("## 🧭 Explore More")
    nav1, nav2 = st.columns(2)
    with nav1:
        st.markdown("""
        <a href="/State_Dashboard?region=Australia" target="_blank" style="
            display: inline-block;
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white !important;
            text-align: center;
            text-decoration: none !important;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1.1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            border: 3px solid #1e88e5;
        ">
            📊 State Dashboard
        </a>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style='padding: 0.5rem; color: #757575; font-size: 0.9rem;'>
        Drill down into state, district, and local-area data with advanced filtering.
        <ul style='margin-top: 0.5rem;'>
            <li>Filter by school level and management type</li>
            <li>Compare across states and territories</li>
            <li>Export detailed reports</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    with nav2:
        st.markdown("""
        <a href="/Analytics?region=Australia" target="_blank" style="
            display: inline-block;
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white !important;
            text-align: center;
            text-decoration: none !important;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1.1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            border: 3px solid #1e88e5;
        ">
            📈 Analytics
        </a>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style='padding: 0.5rem; color: #757575; font-size: 0.9rem;'>
        Interactive analytics with geographic maps, performance metrics, and custom reports.
        <ul style='margin-top: 0.5rem;'>
            <li>Geographic heatmaps</li>
            <li>Comparative analysis</li>
            <li>Custom report builder</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #757575; font-size: clamp(0.8rem, 2vw, 0.9rem);'><p><strong>TutorCloud Global Dashboard</strong></p><p>© 2026 TutorCloud. All rights reserved.</p></div>",
        unsafe_allow_html=True,
    )

def render_au_state_dashboard() -> None:
    # STATE_DASHBOARD_PARITY_PATCH_V1
    _inject_au_css()
    st.markdown('<div class="main-header">📊 State Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive State-Level Analysis with Advanced Filters</div>', unsafe_allow_html=True)

    states_df = _safe_state_df()
    if states_df.empty:
        st.warning("No Australia state data is available.")
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Filters")

    state_options = states_df["state_name"].dropna().tolist() if "state_name" in states_df.columns else []
    default_state = st.session_state.get("au_selected_state", state_options[0] if state_options else None)
    if default_state not in state_options and state_options:
        default_state = state_options[0]
    selected_state = st.sidebar.selectbox(
        "🗺️ Select State/Territory",
        state_options,
        index=state_options.index(default_state) if default_state in state_options else 0,
        key="au_state_filter_parity",
    ) if state_options else None
    st.session_state["au_selected_state"] = selected_state
    try:
        if selected_state:
            st.query_params["state"] = selected_state
    except Exception:
        pass

    districts_df = _safe_district_df(selected_state) if selected_state else pd.DataFrame()
    district_options = ["All"] + sorted([x for x in districts_df.get("district_name", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_district = st.sidebar.selectbox("🏘️ Select District", district_options, index=0, key="au_district_filter_parity")

    base_school_df = _safe_school_df(
        state_name=selected_state,
        district_name=None if selected_district == "All" else selected_district,
        management_type=None,
        school_level=None,
        delivery_model=None,
        search=None,
        limit=20000,
        offset=0,
    )

    suburb_options = ["All"]
    if not base_school_df.empty and "suburb" in base_school_df.columns:
        suburb_options += sorted([x for x in base_school_df["suburb"].dropna().astype(str).unique().tolist() if x])
    selected_suburb = st.sidebar.selectbox("📍 Select Suburb", suburb_options, index=0, key="au_suburb_filter_parity")

    filters_meta = _get_service().get_filter_options() or {}
    levels = filters_meta.get("school_levels", []) or []
    managements = filters_meta.get("management_types", []) or []
    school_levels = st.sidebar.multiselect("📚 School Level", levels, default=[], key="au_level_filter_parity")
    management_groups = st.sidebar.multiselect("🏛️ Management Type", managements, default=[], key="au_mgmt_filter_parity")
    search = st.sidebar.text_input("🔎 Search School", value="", key="au_search_filter_parity")

    filter_payload = {
        "state_name": selected_state,
        "district_name": None if selected_district == "All" else selected_district,
        "management_type": management_groups[0] if len(management_groups) == 1 else None,
        "management_groups": management_groups,
        "school_level": school_levels[0] if len(school_levels) == 1 else None,
        "school_levels": school_levels,
        "delivery_model": None,
        "search": search or None,
        "limit": 20000,
        "offset": 0,
    }

    filtered_base = _apply_school_filters(base_school_df, filter_payload)
    if search and not filtered_base.empty and "school_name" in filtered_base.columns:
        filtered_base = filtered_base[filtered_base["school_name"].astype(str).str.contains(search, case=False, na=False)]

    schools_df = filtered_base.copy()
    if selected_suburb != "All" and not schools_df.empty and "suburb" in schools_df.columns:
        schools_df = schools_df[schools_df["suburb"].astype(str) == str(selected_suburb)]

    active_filters = []
    if selected_state:
        active_filters.append(f"State/Territory: {selected_state}")
    if selected_district != "All":
        active_filters.append(f"District: {selected_district}")
    if selected_suburb != "All":
        active_filters.append(f"Suburb: {selected_suburb}")
    if school_levels:
        active_filters.append("School Level: " + ", ".join(school_levels))
    if management_groups:
        active_filters.append("Management Type: " + ", ".join(management_groups))
    if search:
        active_filters.append(f"Search: {search}")
    if active_filters:
        st.sidebar.markdown("### Active Filters")
        for item in active_filters:
            st.sidebar.markdown(f"- {item}")

    overview = _aggregate_state_overview(schools_df)
    title_state = selected_state or "Australia"
    if selected_district != "All":
        title_state = f"{title_state} / {selected_district}"
    if selected_suburb != "All":
        title_state = f"{title_state} / {selected_suburb}"

    st.markdown(f'<div class="section-header">📊 Overview: {title_state}</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c1.metric("🏫 Total Schools", _fmt_int(overview.get("total_schools", 0)))
    c2.metric("🎓 Schools with Enrollment", _fmt_int(overview.get("schools_with_enrollment", 0)))
    c3.metric("🗺️ Districts", _fmt_int(overview.get("total_districts", 0)))
    c4.metric("📊 State PTR", overview.get("state_ptr", "N/A"))
    c5.metric("👥 Total Students", _fmt_int(overview.get("total_students", 0)))
    c6.metric("👨‍🏫 Total Teachers", _fmt_int(overview.get("total_teachers", 0)))

    st.markdown('<div class="section-header">📚 Grade-Level Enrollment</div>', unsafe_allow_html=True)
    grade_df = _fetch_grade_enrollment(filter_payload)
    if not grade_df.empty:
        fig = px.bar(grade_df, x="grade_label", y="enrolled_students", color_discrete_sequence=[INDIA_UI["students"]])
        fig = _style_chart(fig, title="Grade-Level Enrollment", x_title="Grade", y_title="Students", height=380)
        st.plotly_chart(fig, use_container_width=True)
        _display_df(grade_df)
    else:
        st.info("No grade enrollment data available for current filters.")

    st.markdown('<div class="section-header">📍 District-Level PTR Analysis</div>', unsafe_allow_html=True)
    district_df = _district_analysis(schools_df)
    if not district_df.empty:
        display_district_df = district_df[[c for c in ["district_name", "total_schools", "total_students", "total_teachers", "PTR"] if c in district_df.columns]].copy()
        display_district_df.columns = ["District", "Total Schools", "Total Students", "Total Teachers", "PTR"]
        _display_df(display_district_df)
        fig = px.bar(
            district_df.head(20),
            x="district_name",
            y="ptr_ratio",
            color="ptr_ratio",
            color_continuous_scale="RdYlGn_r",
            custom_data=["PTR"],
        )
        fig.update_traces(hovertemplate="<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>")
        fig = _style_chart(fig, title="District PTR Comparison (Top 20 by School Count)", x_title="District", y_title="PTR", height=420)
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("📥 Download District Data (CSV)", display_district_df.to_csv(index=False), f"district_analysis_{selected_state or 'australia'}.csv", "text/csv")
    else:
        st.info("No district-level data available for the selected filters.")

    if selected_district != "All":
        st.markdown(f'<div class="section-header">🏘️ Suburb-Level PTR Analysis: {selected_district}</div>', unsafe_allow_html=True)
        suburb_df = pd.DataFrame()
        if not filtered_base.empty and "suburb" in filtered_base.columns:
            suburb_src = filtered_base.copy()
            if "school_id" not in suburb_src.columns:
                suburb_src["school_id"] = range(1, len(suburb_src) + 1)
            if "total_students" not in suburb_src.columns:
                suburb_src["total_students"] = 0
            if "fte_teaching_staff" not in suburb_src.columns:
                suburb_src["fte_teaching_staff"] = 0
            suburb_df = suburb_src.groupby("suburb", dropna=False).agg(
                total_schools=("school_id", pd.Series.nunique),
                total_students=("total_students", "sum"),
                total_teachers=("fte_teaching_staff", "sum"),
            ).reset_index()
            suburb_df["ptr_ratio"] = suburb_df.apply(
                lambda r: (r["total_students"] / r["total_teachers"]) if _num(r["total_teachers"]) > 0 else None,
                axis=1,
            )
            suburb_df["PTR"] = suburb_df["ptr_ratio"].apply(_fmt_ptr)
            suburb_df = suburb_df.sort_values(["total_schools", "total_students"], ascending=[False, False], na_position="last")
        if not suburb_df.empty:
            display_suburb_df = suburb_df[["suburb", "total_schools", "total_students", "total_teachers", "PTR"]].copy()
            display_suburb_df.columns = ["Suburb", "Total Schools", "Total Students", "Total Teachers", "PTR"]
            _display_df(display_suburb_df)
            fig_suburb = px.bar(
                suburb_df.head(20),
                x="suburb",
                y="ptr_ratio",
                color="ptr_ratio",
                color_continuous_scale="RdYlGn_r",
                custom_data=["PTR"],
            )
            fig_suburb.update_traces(hovertemplate="<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>")
            fig_suburb = _style_chart(fig_suburb, title=f"Suburb PTR Comparison in {selected_district} (Top 20 by School Count)", x_title="Suburb", y_title="PTR", height=420)
            st.plotly_chart(fig_suburb, use_container_width=True)
            st.download_button("📥 Download Suburb Data (CSV)", display_suburb_df.to_csv(index=False), f"suburb_analysis_{selected_state or 'australia'}.csv", "text/csv")
        else:
            st.info("No suburb-level data available for the selected district.")

    st.markdown('<div class="section-header">🏫 School Directory</div>', unsafe_allow_html=True)
    school_cols = [c for c in ["school_id", "school_name", "district_name", "suburb", "postcode", "management_type", "school_level", "delivery_model", "total_students", "fte_teaching_staff", "student_teacher_ratio"] if c in schools_df.columns]
    display_df = schools_df[school_cols].copy() if school_cols else schools_df.copy()
    if not display_df.empty and "total_students" in display_df.columns:
        display_df = display_df.sort_values("total_students", ascending=False, na_position="last")
    _display_df(display_df)
    if not display_df.empty:
        st.download_button("📥 Download School Directory CSV", display_df.to_csv(index=False), f"school_directory_{selected_state or 'australia'}.csv", "text/csv")

def render_au_analytics() -> None:
    # ANALYTICS_PARITY_PATCH_V1
    _inject_au_css()
    st.markdown('<div class="main-header">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enhanced Analytics: Maps, Metrics, Comparison & Reports</div>', unsafe_allow_html=True)

    base_states_df = _safe_state_df()
    if base_states_df.empty:
        st.warning("No Australia analytics data is available.")
        return

    filters = {"state_name": None, "district_name": None}
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
    states_df = base_states_df.copy()
    if filters.get("state_name"):
        states_df = states_df[states_df["state_name"] == filters["state_name"]].copy()

    tabs = st.tabs(["🗺️ Geographic Maps", "🎯 Performance Metrics", "🔍 Comparative Analysis", "📝 Custom Reports"])

    with tabs[0]:
        st.markdown("### 🗺️ Geographic Heatmaps")
        st.markdown("Interactive maps showing PTR, enrollment density by state/district")
        c1, c2 = st.columns([1, 3])
        with c1:
            metric_choice = st.selectbox(
                "Select Metric to Visualize",
                ["PTR (Pupil-Teacher Ratio)", "Students per School", "Total Students", "Total Schools"],
                key="au_map_metric",
            )
        with c2:
            level = st.radio("Level", ["State", "District"], horizontal=True, key="au_map_level")

        if level == "State":
            df_map = base_states_df.copy()
            if not df_map.empty:
                df_map = df_map.rename(columns={"schools": "total_schools", "fte_teaching_staff": "total_teachers", "student_teacher_ratio": "ptr"})
                if "students_per_school" not in df_map.columns and "total_students" in df_map.columns and "total_schools" in df_map.columns:
                    df_map["students_per_school"] = df_map.apply(lambda r: round(_num(r.get("total_students")) / _num(r.get("total_schools")), 2) if _num(r.get("total_schools")) > 0 else None, axis=1)
            location_col = "state_name"
        else:
            states = base_states_df["state_name"].dropna().tolist() if "state_name" in base_states_df.columns else []
            selected_state = st.selectbox("Select State", states, key="au_map_state_select") if states else None
            df_map = _safe_district_df(selected_state) if selected_state else pd.DataFrame()
            if not df_map.empty:
                df_map = df_map.rename(columns={"schools": "total_schools", "fte_teaching_staff": "total_teachers", "student_teacher_ratio": "ptr"})
                if "students_per_school" not in df_map.columns and "total_students" in df_map.columns and "total_schools" in df_map.columns:
                    df_map["students_per_school"] = df_map.apply(lambda r: round(_num(r.get("total_students")) / _num(r.get("total_schools")), 2) if _num(r.get("total_schools")) > 0 else None, axis=1)
            location_col = "district_name"

        metric_map = {
            "PTR (Pupil-Teacher Ratio)": "ptr",
            "Students per School": "students_per_school",
            "Total Students": "total_students",
            "Total Schools": "total_schools",
        }
        metric_col = metric_map[metric_choice]

        if not df_map.empty and metric_col in df_map.columns:
            df_chart = df_map.sort_values(metric_col, ascending=False).head(20).copy()
            if metric_col == "ptr":
                df_chart["ptr_formatted"] = df_chart[metric_col].apply(_fmt_ptr)
                fig = px.bar(
                    df_chart,
                    x=location_col,
                    y=metric_col,
                    title=f"{metric_choice} by {level} (Top 20)",
                    labels={metric_col: metric_choice, location_col: level},
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
                    title=f"{metric_choice} by {level} (Top 20)",
                    labels={metric_col: metric_choice, location_col: level},
                    color=metric_col,
                    color_continuous_scale="Viridis",
                )
            fig.update_layout(xaxis_tickangle=-45, showlegend=True, margin=dict(l=60, r=40, t=80, b=120))
            st.plotly_chart(fig, use_container_width=True)
            table_df = df_map.copy()
            if "ptr" in table_df.columns:
                table_df["ptr"] = table_df["ptr"].apply(_fmt_ptr)
            _display_df(table_df)
        else:
            st.warning("No data available for selected filters")

    with tabs[1]:
        st.markdown("#### 📊 Key Performance Indicators")
        filter_state = st.selectbox("Select State (All for National)", ["All"] + base_states_df["state_name"].dropna().tolist(), key="au_perf_state")
        if filter_state != "All":
            perf_districts = _safe_district_df(filter_state)
            district_options = perf_districts.get("district_name", pd.Series(dtype=str)).dropna().tolist() if not perf_districts.empty else []
            filter_district = st.selectbox("Select District (All for State)", ["All"] + district_options, key="au_perf_district")
        else:
            perf_districts = pd.DataFrame()
            filter_district = "All"

        if filter_state == "All":
            perf_df = base_states_df.rename(columns={"schools": "total_schools", "fte_teaching_staff": "total_teachers", "student_teacher_ratio": "ptr"}).copy()
            agg_data = {
                "total_schools": _num(perf_df["total_schools"].sum()) if "total_schools" in perf_df.columns else 0,
                "total_students": _num(perf_df["total_students"].sum()) if "total_students" in perf_df.columns else 0,
                "total_teachers": _num(perf_df["total_teachers"].sum()) if "total_teachers" in perf_df.columns else 0,
            }
        elif filter_district == "All":
            perf_df = _safe_district_df(filter_state).rename(columns={"schools": "total_schools", "fte_teaching_staff": "total_teachers", "student_teacher_ratio": "ptr"}).copy()
            agg_data = {
                "total_schools": _num(perf_df["total_schools"].sum()) if "total_schools" in perf_df.columns else 0,
                "total_students": _num(perf_df["total_students"].sum()) if "total_students" in perf_df.columns else 0,
                "total_teachers": _num(perf_df["total_teachers"].sum()) if "total_teachers" in perf_df.columns else 0,
            }
        else:
            perf_df = _safe_district_df(filter_state).rename(columns={"schools": "total_schools", "fte_teaching_staff": "total_teachers", "student_teacher_ratio": "ptr"}).copy()
            perf_df = perf_df[perf_df["district_name"].str.upper() == filter_district.upper()] if not perf_df.empty else pd.DataFrame()
            row = perf_df.iloc[0].to_dict() if not perf_df.empty else {}
            agg_data = {
                "total_schools": row.get("total_schools", 0),
                "total_students": row.get("total_students", 0),
                "total_teachers": row.get("total_teachers", 0),
            }
        agg_data["ptr"] = round(_num(agg_data["total_students"]) / _num(agg_data["total_teachers"])) if _num(agg_data["total_teachers"]) > 0 else None
        _render_metric_cards_overview(agg_data)
        if filter_state == "All":
            table_df = base_states_df.rename(columns={"schools": "total_schools", "fte_teaching_staff": "total_teachers", "student_teacher_ratio": "ptr"})
        elif filter_district == "All":
            table_df = _safe_district_df(filter_state).rename(columns={"schools": "total_schools", "fte_teaching_staff": "total_teachers", "student_teacher_ratio": "ptr"})
        else:
            table_df = perf_df
        if not table_df.empty:
            _display_df(table_df)

    with tabs[2]:
        st.markdown("### 🔍 Comparative Analysis Tool")
        st.markdown("Compare two locations side-by-side across all key metrics")
        comp_level = st.radio("Comparison Level", ["State vs State", "District vs District"], horizontal=True, key="au_comp_level")
        col1, col2 = st.columns(2)
        if comp_level == "State vs State":
            states = base_states_df["state_name"].dropna().tolist() if "state_name" in base_states_df.columns else []
            with col1:
                st.markdown("#### 📍 Location 1")
                state1 = st.selectbox("State", states, key="au_comp_state1")
            with col2:
                st.markdown("#### 📍 Location 2")
                state2 = st.selectbox("State", states, key="au_comp_state2")
            if st.button("🔄 Compare", type="primary", key="au_comp_btn"):
                comparison = _comparison_df_state(base_states_df, state1, state2)
                if not comparison.empty:
                    st.dataframe(comparison, use_container_width=True, hide_index=True)
                    st.download_button("📥 Download Comparison CSV", comparison.to_csv(index=False), f"comparison_{state1}_vs_{state2}.csv", "text/csv")
        else:
            states = base_states_df["state_name"].dropna().tolist() if "state_name" in base_states_df.columns else []
            with col1:
                st.markdown("#### 📍 Location 1")
                state1 = st.selectbox("State", states, key="au_comp_dist_state1")
                districts1 = _safe_district_df(state1).get("district_name", pd.Series(dtype=str)).dropna().tolist() if state1 else []
                district1 = st.selectbox("District", districts1, key="au_comp_district1") if districts1 else None
            with col2:
                st.markdown("#### 📍 Location 2")
                state2 = st.selectbox("State", states, key="au_comp_dist_state2")
                districts2 = _safe_district_df(state2).get("district_name", pd.Series(dtype=str)).dropna().tolist() if state2 else []
                district2 = st.selectbox("District", districts2, key="au_comp_district2") if districts2 else None
            if st.button("🔄 Compare", type="primary", key="au_comp_dist_btn") and district1 and district2:
                comparison = _comparison_df_district(state1, district1, state2, district2)
                if not comparison.empty:
                    st.dataframe(comparison, use_container_width=True, hide_index=True)
                    st.download_button("📥 Download Comparison CSV", comparison.to_csv(index=False), f"comparison_{district1}_vs_{district2}.csv", "text/csv")

    with tabs[3]:
        st.markdown("### 📝 Custom Report Builder")
        st.markdown("Build custom reports with flexible dimensions and metrics")
        st.markdown("#### Step 1: Select Dimensions")
        dimensions = st.multiselect(
            "Choose grouping dimensions",
            ["State", "District", "Management", "School Level", "Delivery Model"],
            default=["State"],
            key="au_report_dims",
        )
        st.markdown("#### Step 2: Select Metrics")
        metrics = st.multiselect(
            "Choose metrics to include",
            ["Schools", "Students", "Teachers", "PTR"],
            default=["Schools", "Students", "PTR"],
            key="au_report_metrics",
        )
        if st.button("📊 Generate Report", type="primary", key="au_generate_report"):
            if not dimensions or not metrics:
                st.warning("Please select at least one dimension and one metric")
            elif schools_df.empty:
                st.warning("No data found for selected criteria")
            else:
                dim_map = {
                    "State": "state_name",
                    "District": "district_name",
                    "Management": "management_type",
                    "School Level": "school_level",
                    "Delivery Model": "delivery_model",
                }
                report_df = schools_df.copy()
                if "school_id" not in report_df.columns:
                    report_df["school_id"] = range(1, len(report_df) + 1)
                if "total_students" not in report_df.columns:
                    report_df["total_students"] = 0
                if "fte_teaching_staff" not in report_df.columns:
                    report_df["fte_teaching_staff"] = 0
                group_cols = [dim_map[d] for d in dimensions if dim_map[d] in report_df.columns]
                if not group_cols:
                    st.warning("Selected dimensions are not available")
                else:
                    agg = report_df.groupby(group_cols, dropna=False).agg(
                        total_schools=("school_id", pd.Series.nunique),
                        total_students=("total_students", "sum"),
                        total_teachers=("fte_teaching_staff", "sum"),
                    ).reset_index()
                    agg["ptr"] = agg.apply(lambda r: round(_num(r["total_students"]) / _num(r["total_teachers"])) if _num(r["total_teachers"]) > 0 else None, axis=1)
                    cols_to_show = group_cols.copy()
                    if "Schools" in metrics:
                        cols_to_show.append("total_schools")
                    if "Students" in metrics:
                        cols_to_show.append("total_students")
                    if "Teachers" in metrics:
                        cols_to_show.append("total_teachers")
                    if "PTR" in metrics:
                        cols_to_show.append("ptr")
                    display_df = agg[cols_to_show].copy()
                    st.success(f"Report generated successfully! ({len(display_df)} rows)")
                    _display_df(display_df)
                    st.download_button("📥 Download CSV", display_df.to_csv(index=False), "au_custom_report.csv", "text/csv")
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                        display_df.to_excel(writer, index=False, sheet_name="Report")
                    buffer.seek(0)
                    st.download_button("📊 Download Excel", buffer.getvalue(), "au_custom_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# === INDIA_PARITY_OVERRIDE_AU ===

def _au_unique_values(df: pd.DataFrame, col: str) -> list[str]:
    if df is None or df.empty or col not in df.columns:
        return []
    vals = []
    for raw in df[col].fillna('').tolist():
        text_val = str(raw).strip()
        if text_val and text_val.lower() != 'nan' and text_val not in vals:
            vals.append(text_val)
    return sorted(vals, key=lambda x: x.lower())


def _state_sidebar_filters(states_df: pd.DataFrame) -> Dict[str, Any]:
    st.sidebar.markdown('---')
    st.sidebar.markdown('### 🔍 Apply Filters')
    state_options = _au_unique_values(states_df, 'state_name')
    if not state_options:
        return {}

    state = st.sidebar.selectbox('🗺️ Select State/Territory', state_options, key='au_state_filter_exact')
    district_options = ['All'] + _au_unique_values(_safe_district_df(state), 'district_name')
    district = st.sidebar.selectbox('🏘️ Select District', district_options, index=0, key=f'au_district_filter_exact_{state}')

    scope_df = _safe_school_df(
        state_name=state,
        district_name=None if district == 'All' else district,
        management_type=None,
        school_level=None,
        delivery_model=None,
        search=None,
        limit=50000,
        offset=0,
    )

    block_options = ['All'] + _au_unique_values(scope_df, 'suburb')
    block_name = st.sidebar.selectbox('🏘️ Select Suburb', block_options, index=0, key=f'au_block_filter_exact_{state}_{district}')

    location_options = ['All'] + _au_unique_values(scope_df, 'postcode')
    location_value = 'All'

    school_type_options = _au_unique_values(scope_df, 'school_level')
    management_options = _au_unique_values(scope_df, 'management_type')
    board_options = _au_unique_values(scope_df, 'delivery_model')

    school_type_new = st.sidebar.multiselect('📖 School Level', school_type_options, default=[], help='Uses available Australia school-level values.', key=f'au_school_type_exact_{state}')
    management_groups = st.sidebar.multiselect('🏛️ Management Type', management_options, default=[], key=f'au_management_exact_{state}')
    boards = []

    active_filters = []
    for val in [state, None if district == 'All' else district, None if block_name == 'All' else block_name, None if location_value == 'All' else location_value]:
        if val:
            active_filters.append(val)
    active_filters.extend([f'Management: {x}' for x in management_groups])
    active_filters.extend([f'School Level: {x}' for x in school_type_new])
    if active_filters:
        st.sidebar.markdown('---')
        st.sidebar.markdown('### ✅ Active Filters')
        for item in active_filters:
            st.sidebar.markdown(f'- {item}')

    return {
        'state_name': state,
        'district_name': None if district == 'All' else district,
        'block_name': None if block_name == 'All' else block_name,
        'location_value': None if location_value == 'All' else location_value,
        'school_type_new': school_type_new,
        'management_groups': management_groups,
        'school_levels': school_type_new,
        'boards': boards,
        'search': None,
        'limit': 50000,
        'offset': 0,
    }


def _au_apply_exact_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if filters.get('block_name') and 'suburb' in out.columns:
        out = out[out['suburb'].astype(str).str.upper() == str(filters['block_name']).upper()]
    if filters.get('location_value') and 'postcode' in out.columns:
        out = out[out['postcode'].astype(str).str.upper() == str(filters['location_value']).upper()]
    if filters.get('management_groups') and 'management_type' in out.columns:
        out = out[out['management_type'].isin(filters['management_groups'])]
    if filters.get('school_type_new') and 'school_level' in out.columns:
        out = out[out['school_level'].isin(filters['school_type_new'])]
    if filters.get('boards') and 'delivery_model' in out.columns and out['delivery_model'].notna().any():
        out = out[out['delivery_model'].isin(filters['boards'])]
    return out


def _au_block_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or 'suburb' not in df.columns:
        return pd.DataFrame()
    out = df.copy()
    if 'school_id' not in out.columns:
        out['school_id'] = range(1, len(out) + 1)
    if 'total_students' not in out.columns:
        out['total_students'] = 0
    if 'fte_teaching_staff' not in out.columns:
        out['fte_teaching_staff'] = 0
    grp = out.groupby('suburb', dropna=False).agg(
        total_schools=('school_id', pd.Series.nunique),
        total_students=('total_students', 'sum'),
        total_teachers=('fte_teaching_staff', 'sum'),
    ).reset_index().rename(columns={'suburb': 'block'})
    grp['ptr_ratio'] = grp.apply(lambda r: (r['total_students'] / r['total_teachers']) if _num(r['total_teachers']) > 0 else None, axis=1)
    grp['PTR'] = grp['ptr_ratio'].apply(_fmt_ptr)
    return grp.sort_values(['total_students', 'total_schools'], ascending=[False, False], na_position='last')


def render_au_state_dashboard() -> None:
    _inject_au_css()
    st.markdown('<div class="main-header">📊 State Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive State-Level Analysis with Advanced Filters</div>', unsafe_allow_html=True)

    states_df = _safe_state_df()
    if states_df.empty:
        st.warning('No Australia state data is available.')
        return

    filters = _state_sidebar_filters(states_df)
    if not filters.get('state_name'):
        st.info('👈 Please select a State/UT from the sidebar to view data')
        return

    schools_seed = _safe_school_df(
        state_name=filters.get('state_name'),
        district_name=filters.get('district_name'),
        management_type=None,
        school_level=None,
        delivery_model=None,
        search=filters.get('search'),
        limit=filters.get('limit', 50000),
        offset=0,
    )
    schools_df = _au_apply_exact_filters(schools_seed, filters)
    if schools_df.empty:
        st.warning('No data available for selected filters')
        return

    overview = _aggregate_state_overview(schools_df)
    st.markdown(f'<div class="section-header">📊 Overview: {filters.get("state_name")}</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('🏫 Total Schools', _fmt_int(overview.get('total_schools', 0)))
    with col2:
        st.metric('🎓 Schools with Enrollment', _fmt_int(overview.get('schools_with_enrollment', 0)))
    with col3:
        st.metric('🗺️ Districts', _fmt_int(overview.get('total_districts', 0)))
    with col4:
        st.metric('📊 State PTR', overview.get('state_ptr', 'N/A'))
    col5, col6 = st.columns(2)
    with col5:
        st.metric('👥 Total Students', _fmt_int(overview.get('total_students', 0)))
    with col6:
        st.metric('👨‍🏫 Total Teachers', _fmt_int(overview.get('total_teachers', 0)))

    st.markdown('<div class="section-header">📚 Grade-Level Enrollment</div>', unsafe_allow_html=True)
    grade_df = _fetch_grade_enrollment(filters)
    if not grade_df.empty:
        fig_grades = px.bar(grade_df, x='grade_label', y='enrolled_students', color_discrete_sequence=[INDIA_UI['students']])
        fig_grades = _style_chart(fig_grades, title='Grade-Level Enrollment', x_title='Grade', y_title='Students', height=380)
        st.plotly_chart(fig_grades, use_container_width=True)
        _display_df(grade_df)
    else:
        st.info('No grade enrollment data available for current filters.')

    st.markdown('<div class="section-header">📍 District-Level PTR Analysis</div>', unsafe_allow_html=True)
    district_df = _district_analysis(schools_df)
    if not district_df.empty:
        display_df = district_df[[c for c in ['district_name', 'total_schools', 'total_students', 'total_teachers', 'PTR'] if c in district_df.columns]].copy()
        display_df.columns = ['District', 'Total Schools', 'Total Students', 'Total Teachers', 'PTR']
        _display_df(display_df)
        fig_ptr = px.bar(district_df.head(20), x='district_name', y='ptr_ratio', color='ptr_ratio', color_continuous_scale='RdYlGn_r', custom_data=['PTR'])
        fig_ptr.update_traces(hovertemplate='<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>')
        fig_ptr = _style_chart(fig_ptr, title='District PTR Comparison (Top 20 by School Count)', x_title='District', y_title='PTR', height=420)
        st.plotly_chart(fig_ptr, use_container_width=True)
        st.download_button('📥 Download District Data (CSV)', display_df.to_csv(index=False), f'district_analysis_{str(filters.get("state_name")).lower().replace(" ", "_")}.csv', 'text/csv')
    else:
        st.info('No district-level data available for the selected filters.')

    if filters.get('district_name'):
        st.markdown(f'<div class="section-header">🏘️ Block/Taluk-Level PTR Analysis: {filters.get("district_name")}</div>', unsafe_allow_html=True)
        block_df = _au_block_analysis(schools_df)
        if not block_df.empty:
            display_block_df = block_df[[c for c in ['block', 'total_schools', 'total_students', 'total_teachers', 'PTR'] if c in block_df.columns]].copy()
            display_block_df.columns = ['Block/Taluk', 'Total Schools', 'Total Students', 'Total Teachers', 'PTR']
            _display_df(display_block_df)
            fig_block = px.bar(block_df.head(20), x='block', y='ptr_ratio', color='ptr_ratio', color_continuous_scale='RdYlGn_r', custom_data=['PTR'])
            fig_block.update_traces(hovertemplate='<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>')
            fig_block = _style_chart(fig_block, title=f'Block/Taluk PTR Comparison in {filters.get("district_name")} (Top 20)', x_title='Block/Taluk', y_title='PTR', height=420)
            st.plotly_chart(fig_block, use_container_width=True)
            st.download_button('📥 Download Block/Taluk Data (CSV)', display_block_df.to_csv(index=False), f'block_analysis_{str(filters.get("district_name")).lower().replace(" ", "_")}.csv', 'text/csv', key='au_download_block_exact')
        else:
            st.info('No block-level data available for the selected district.')

    st.markdown('<div class="section-header">🏫 School Directory</div>', unsafe_allow_html=True)
    school_cols = [c for c in ['school_id', 'school_name', 'district_name', 'suburb', 'postcode', 'management_type', 'school_level', 'delivery_model', 'total_students', 'fte_teaching_staff', 'student_teacher_ratio'] if c in schools_df.columns]
    directory_df = schools_df[school_cols].copy() if school_cols else schools_df.copy()
    if 'student_teacher_ratio' in directory_df.columns:
        directory_df['student_teacher_ratio'] = directory_df['student_teacher_ratio'].apply(_fmt_ptr)
        directory_df = directory_df.rename(columns={'student_teacher_ratio': 'PTR'})
    _display_df(directory_df)

    st.markdown('---')
    st.markdown("""
        <div style='text-align: center; padding: 20px; margin-top: 40px; border-top: 1px solid #e0e0e0;'>
        <p style='margin: 0; color: #666; font-size: 0.95rem;'>TutorCloud Global Dashboard</p>
        <p style='margin: 5px 0 0 0; color: #666; font-size: 0.95rem;'>© 2026 TutorCloud. All rights reserved.</p>
        </div>
    """, unsafe_allow_html=True)
