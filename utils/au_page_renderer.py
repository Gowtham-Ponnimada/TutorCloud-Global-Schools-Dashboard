from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from au_phase1_final_load import db_engine
from services.au_dashboard_service import AUDashboardService

# Optional shared colors from app; safe fallback if unavailable
try:
    from ui_components import COLORS as APP_COLORS
except Exception:
    APP_COLORS = {}

# -----------------------------
# THEME / INDIA-PARITY TOKENS
# -----------------------------
THEME = {
    "primary": APP_COLORS.get("primary", "#F59E0B"),
    "secondary": APP_COLORS.get("secondary", "#6366F1"),
    "success": APP_COLORS.get("success", "#10B981"),
    "danger": APP_COLORS.get("danger", "#EF4444"),
    "info": APP_COLORS.get("info", "#8B5CF6"),
    "girls": APP_COLORS.get("girls", "#EC4899"),
    "boys": APP_COLORS.get("boys", "#3B82F6"),
    "bg": "#F8FAFC",
    "card_bg": "#FFFFFF",
    "text": "#111827",
    "muted": "#6B7280",
    "border": "#E5E7EB",
    "grid": "#F3F4F6",
}

INDIA_COLOR_TOKENS = {
    "Total Students": THEME["primary"],
    "Girls": THEME["girls"],
    "Boys": THEME["boys"],
    "Schools": THEME["success"],
    "FTE Teaching Staff": THEME["info"],
    "Student-Teacher Ratio": THEME["secondary"],
    "Weighted Avg ICSEA": "#7C3AED",
    "Weighted Indigenous %": "#EF4444",
    "Weighted LBOTE %": "#14B8A6",
    "Government": "#2563EB",
    "Catholic": "#F59E0B",
    "Independent": "#10B981",
}

KPI_TITLES = {
    "schools": "Total Schools",
    "total_students": "Total Students",
    "girls_students": "Girls",
    "boys_students": "Boys",
    "fte_teaching_staff": "FTE Teaching Staff",
    "student_teacher_ratio": "Student-Teacher Ratio",
    "weighted_avg_icsea": "Weighted Avg ICSEA",
    "weighted_indigenous_pct": "Weighted Indigenous %",
    "weighted_lbote_yes_pct": "Weighted LBOTE %",
    "weighted_lbote_pct": "Weighted LBOTE %",
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
    "fte_teaching_staff": "FTE Teaching Staff",
    "student_teacher_ratio": "Student-Teacher Ratio",
    "weighted_avg_icsea": "Weighted Avg ICSEA",
    "weighted_indigenous_pct": "Weighted Indigenous %",
    "weighted_lbote_yes_pct": "Weighted LBOTE %",
    "grade_code": "Grade Code",
    "grade_label": "Grade Label",
    "enrolled_students": "Enrolled Students",
}

LEGEND_LABELS = {
    "girls_students": "Girls",
    "boys_students": "Boys",
    "total_students": "Total Students",
    "schools": "Schools",
    "school_count": "Schools",
    "fte_teaching_staff": "FTE Teaching Staff",
    "student_teacher_ratio": "Student-Teacher Ratio",
    "weighted_avg_icsea": "Weighted Avg ICSEA",
    "weighted_indigenous_pct": "Weighted Indigenous %",
    "weighted_lbote_yes_pct": "Weighted LBOTE %",
    "government": "Government",
    "catholic": "Catholic",
    "independent": "Independent",
    "govt": "Government",
}

INT_LIKE_COLUMNS = {
    "schools",
    "total_students",
    "girls_students",
    "boys_students",
    "enrolled_students",
}

FLOAT_1_COLUMNS = {
    "fte_teaching_staff",
}

FLOAT_2_COLUMNS = {
    "student_teacher_ratio",
    "weighted_avg_icsea",
    "weighted_indigenous_pct",
    "weighted_lbote_yes_pct",
    "weighted_lbote_pct",
}


def _get_service() -> AUDashboardService:
    """
    No Streamlit cache decorator here by design.
    Keeps app safe from cross-page import/cache issues.
    """
    svc = st.session_state.get("_au_dashboard_service")
    if svc is None:
        svc = AUDashboardService(db_engine(), school_year="2025")
        st.session_state["_au_dashboard_service"] = svc
    return svc


def _inject_au_css() -> None:
    """
    Micro-patch included here:
    - tighter India-like vertical spacing
    - slightly stronger hierarchy for KPI value
    - softer but deeper card shadow
    - closer label/value proportions to India cards
    """
    st.markdown(
        f"""
        <style>
        .au-kpi-card {{
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 14px;
            padding: 14px 16px 12px 16px;
            box-shadow: 0 8px 20px rgba(17, 24, 39, 0.06);
            min-height: 104px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 1px;
        }}
        .au-kpi-label {{
            color: #6B7280;
            font-size: 0.76rem;
            font-weight: 700;
            line-height: 1.15;
            margin-bottom: 6px;
            letter-spacing: 0.1px;
        }}
        .au-kpi-value {{
            color: #111827;
            font-size: 2.0rem;
            font-weight: 800;
            line-height: 1.0;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-variant-numeric: tabular-nums;
            letter-spacing: -0.02em;
        }}
        .au-kpi-sub {{
            color: #6B7280;
            font-size: 0.74rem;
            line-height: 1.15;
            white-space: nowrap;
        }}
        .au-section-title {{
            color: {THEME["text"]};
            font-size: 1.22rem;
            font-weight: 800;
            margin-top: 0.25rem;
            margin-bottom: 0.12rem;
        }}
        .au-section-subtitle {{
            color: {THEME["muted"]};
            font-size: 0.92rem;
            line-height: 1.35;
            margin-bottom: 0.85rem;
        }}
        .au-page-title {{
            color: {THEME["text"]};
            font-size: 1.92rem;
            font-weight: 800;
            line-height: 1.15;
            margin-bottom: 0.12rem;
        }}
        .au-page-subtitle {{
            color: {THEME["muted"]};
            font-size: 0.98rem;
            line-height: 1.4;
            margin-bottom: 0.95rem;
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid {THEME["border"]};
            border-radius: 16px;
            overflow: hidden;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def _prettify_label(label: str) -> str:
    if label is None:
        return ""
    s = str(label).strip()
    if not s:
        return ""
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s)
    parts = s.split(" ")
    out = []
    for part in parts:
        low = part.lower()
        if low in {"fte", "icsea", "lbote"}:
            out.append(part.upper())
        elif low == "pct":
            out.append("%")
        elif low == "abbr":
            out.append("Abbr")
        else:
            out.append(part.capitalize())
    return " ".join(out)


def _normalize_label(label: str) -> str:
    s = str(label).strip()
    if s in COLUMN_TITLES:
        return COLUMN_TITLES[s]
    if s in LEGEND_LABELS:
        return LEGEND_LABELS[s]
    if s.lower() in LEGEND_LABELS:
        return LEGEND_LABELS[s.lower()]
    return _prettify_label(s)


def _normalize_legend_name(name: str) -> str:
    if name is None:
        return ""
    s = str(name).strip()
    if s in LEGEND_LABELS:
        return LEGEND_LABELS[s]
    if s.lower() in LEGEND_LABELS:
        return LEGEND_LABELS[s.lower()]
    return _prettify_label(s)


def _is_missing(v: Any) -> bool:
    try:
        return pd.isna(v)
    except Exception:
        return v is None


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




def _fmt_compact(v: Any, digits: int = 2) -> str:
    if _is_missing(v):
        return "N/A"
    try:
        n = float(v)
        abs_n = abs(n)
        if abs_n >= 1_000_000_000:
            return f"{n / 1_000_000_000:.{digits}f}B"
        if abs_n >= 1_000_000:
            return f"{n / 1_000_000:.{digits}f}M"
        if abs_n >= 1_000:
            return f"{n / 1_000:.{digits}f}K"
        if float(n).is_integer():
            return f"{int(n):,}"
        return f"{n:.{digits}f}"
    except Exception:
        return str(v)


def _kpi_card_label(label: str) -> str:
    mapping = {
        "Total Schools": "Total Schools",
        "Total Students": "Total Students",
        "Girls": "Girls",
        "Boys": "Boys",
        "FTE Teaching Staff": "Teaching Staff",
        "Student-Teacher Ratio": "PTR",
        "Weighted Avg ICSEA": "Avg ICSEA",
        "Weighted Indigenous %": "Indigenous %",
        "Weighted LBOTE %": "LBOTE %",
    }
    return mapping.get(label, label)


def _kpi_card_subtitle(label: str) -> str:
    mapping = {
        "Teaching Staff": "FTE · Australia · 2025",
        "PTR": "Student-Teacher Ratio",
        "Avg ICSEA": "Australia · 2025",
        "Indigenous %": "Australia · 2025",
        "LBOTE %": "Australia · 2025",
    }
    return mapping.get(label, "Australia · 2025")

def _fmt_metric(label: str, value: Any) -> str:
    """
    KPI cards use compact notation to avoid wrapping and better match India-card visual density.
    Tables remain fully formatted elsewhere.
    """
    if label == "Total Schools":
        return _fmt_int(value)
    if label in {"Total Students", "Girls", "Boys"}:
        return _fmt_compact(value, 2)
    if label == "FTE Teaching Staff":
        return _fmt_compact(value, 1)
    if label == "Student-Teacher Ratio":
        return _fmt_float(value, 2)
    if label == "Weighted Avg ICSEA":
        return _fmt_float(value, 2)
    if label in {"Weighted Indigenous %", "Weighted LBOTE %"}:
        return _fmt_pct(value, 2)
    if _is_missing(value):
        return "N/A"
    return str(value)

def _coerce_display_value(v: Any) -> Any:
    if _is_missing(v):
        return "N/A"
    return v


def _format_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    for col in list(out.columns):
        if col in INT_LIKE_COLUMNS:
            out[col] = out[col].apply(_fmt_int)
        elif col in FLOAT_1_COLUMNS:
            out[col] = out[col].apply(lambda x: _fmt_float(x, 1))
        elif col in FLOAT_2_COLUMNS:
            if "pct" in col:
                out[col] = out[col].apply(lambda x: _fmt_pct(x, 2))
            else:
                out[col] = out[col].apply(lambda x: _fmt_float(x, 2))
        else:
            out[col] = out[col].apply(_coerce_display_value)

    out.columns = [_normalize_label(c) for c in out.columns]
    return out


def _display_df(df: pd.DataFrame, *, use_container_width: bool = True, hide_index: bool = True) -> None:
    st.dataframe(
        _format_dataframe_for_display(df),
        use_container_width=use_container_width,
        hide_index=hide_index,
    )


def _normalize_fig_legends_and_colors(fig):
    if fig is None:
        return fig

    for trace in fig.data:
        original_name = getattr(trace, "name", "") or ""
        new_name = _normalize_legend_name(original_name)

        try:
            trace.name = new_name
        except Exception:
            pass
        try:
            trace.legendgroup = new_name
        except Exception:
            pass
        try:
            if getattr(trace, "hovertemplate", None) and original_name:
                trace.hovertemplate = trace.hovertemplate.replace(str(original_name), str(new_name))
        except Exception:
            pass

        color = INDIA_COLOR_TOKENS.get(new_name)
        if color:
            try:
                if hasattr(trace, "marker") and trace.marker is not None:
                    trace.marker.color = color
            except Exception:
                pass
            try:
                if hasattr(trace, "line") and trace.line is not None:
                    trace.line.color = color
            except Exception:
                pass

    return fig


def _style_au_chart(fig, title: Optional[str] = None, x_title: Optional[str] = None, y_title: Optional[str] = None, height: int = 420):
    fig = _normalize_fig_legends_and_colors(fig)

    fig.update_layout(
        title={
            "text": title or "",
            "x": 0.0,
            "xanchor": "left",
            "font": {"size": 18, "color": THEME["text"]},
        },
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=55, b=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            title_text="",
            font=dict(size=12),
        ),
        font=dict(color=THEME["text"]),
    )

    fig.update_xaxes(
        title_text=x_title or None,
        showgrid=False,
        linecolor=THEME["border"],
        tickfont=dict(color="#374151"),
        title_font=dict(color="#374151"),
    )

    fig.update_yaxes(
        title_text=y_title or None,
        showgrid=True,
        gridcolor=THEME["grid"],
        zeroline=False,
        tickfont=dict(color="#374151"),
        title_font=dict(color="#374151"),
        separatethousands=True,
    )

    return fig


def _section_header(title: str, subtitle: Optional[str] = None) -> None:
    st.markdown(f'<div class="au-section-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="au-section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def _page_header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="au-page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="au-page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def _metric_color(label: str) -> str:
    return INDIA_COLOR_TOKENS.get(label, THEME["primary"])


def _render_kpi_cards(kpis: List[tuple], per_row: int = 3) -> None:
    if not kpis:
        return

    for i in range(0, len(kpis), per_row):
        row = kpis[i:i + per_row]
        cols = st.columns(len(row))
        for col, (label, value) in zip(cols, row):
            color = _metric_color(label)
            formatted = _fmt_metric(label, value)
            card_label = _kpi_card_label(label)
            subtitle = _kpi_card_subtitle(card_label)

            col.markdown(
                f"""
                <div class="au-kpi-card" style="border-top: 4px solid {color};">
                    <div class="au-kpi-label">{card_label}</div>
                    <div class="au-kpi-value">{formatted}</div>
                    <div class="au-kpi-sub">{subtitle}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

def _build_primary_kpis(summary: Dict[str, Any]) -> List[tuple]:
    return [
        ("Total Schools", summary.get("schools")),
        ("Total Students", summary.get("total_students")),
        ("Girls", summary.get("girls_students")),
        ("Boys", summary.get("boys_students")),
        ("FTE Teaching Staff", summary.get("fte_teaching_staff")),
        ("Student-Teacher Ratio", summary.get("student_teacher_ratio")),
    ]


def _build_secondary_kpis(summary: Dict[str, Any]) -> List[tuple]:
    return [
        ("Weighted Avg ICSEA", summary.get("weighted_avg_icsea")),
        ("Weighted Indigenous %", summary.get("weighted_indigenous_pct")),
        ("Weighted LBOTE %", summary.get("weighted_lbote_yes_pct", summary.get("weighted_lbote_pct"))),
    ]


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
    svc = _get_service()
    return _to_dataframe(svc.get_state_kpis())


def _safe_district_df(state_name: str) -> pd.DataFrame:
    svc = _get_service()
    return _to_dataframe(svc.get_district_kpis(state_name))


def _safe_school_df(**filters) -> pd.DataFrame:
    svc = _get_service()
    return _to_dataframe(svc.get_schools(**filters))


def _safe_school_detail(school_id: str) -> Dict[str, Any]:
    svc = _get_service()
    detail = svc.get_school_detail(school_id)
    return detail or {}


def _safe_grade_df(school_id: str) -> pd.DataFrame:
    svc = _get_service()
    return _to_dataframe(svc.get_grade_enrollment(school_id))


def _resolve_state(default: Optional[str] = None) -> Optional[str]:
    query_state = None
    try:
        query_state = st.query_params.get("state")
    except Exception:
        query_state = None

    if query_state:
        st.session_state["au_selected_state"] = query_state
        return query_state

    if "au_selected_state" in st.session_state:
        return st.session_state["au_selected_state"]

    return default


def _update_state_query_param(state_name: Optional[str]) -> None:
    if not state_name:
        return
    try:
        st.query_params["state"] = state_name
    except Exception:
        pass


def _render_gender_chart_from_summary(summary: Dict[str, Any], title: str = "Gender Split") -> None:
    gender_df = pd.DataFrame({
        "Metric": ["Girls", "Boys"],
        "Value": [
            summary.get("girls_students", 0) or 0,
            summary.get("boys_students", 0) or 0,
        ],
    })

    fig = px.bar(
        gender_df,
        x="Metric",
        y="Value",
        color="Metric",
        color_discrete_map={
            "Girls": INDIA_COLOR_TOKENS["Girls"],
            "Boys": INDIA_COLOR_TOKENS["Boys"],
        },
    )
    fig = _style_au_chart(fig, title=title, x_title="", y_title="Students", height=360)
    st.plotly_chart(fig, use_container_width=True)


def _render_top_states_students_chart(states_df: pd.DataFrame, title: str = "State-wise Total Students") -> None:
    if states_df.empty or "total_students" not in states_df.columns:
        st.info("No state student data available.")
        return

    chart_df = states_df.copy().sort_values("total_students", ascending=False)
    fig = px.bar(
        chart_df,
        x="state_name",
        y="total_students",
        color_discrete_sequence=[INDIA_COLOR_TOKENS["Total Students"]],
    )
    fig = _style_au_chart(fig, title=title, x_title="State Name", y_title="Total Students")
    st.plotly_chart(fig, use_container_width=True)


def _render_top_states_schools_chart(states_df: pd.DataFrame, title: str = "State-wise Schools") -> None:
    if states_df.empty or "schools" not in states_df.columns:
        st.info("No state school data available.")
        return

    chart_df = states_df.copy().sort_values("schools", ascending=False)
    fig = px.bar(
        chart_df,
        x="state_name",
        y="schools",
        color_discrete_sequence=[INDIA_COLOR_TOKENS["Schools"]],
    )
    fig = _style_au_chart(fig, title=title, x_title="State Name", y_title="Schools")
    st.plotly_chart(fig, use_container_width=True)


def _render_ptr_chart(states_df: pd.DataFrame, title: str = "Student-Teacher Ratio by State") -> None:
    if states_df.empty or "student_teacher_ratio" not in states_df.columns:
        st.info("No student-teacher ratio data available.")
        return

    chart_df = states_df.copy().sort_values("student_teacher_ratio", ascending=False)
    fig = px.line(
        chart_df,
        x="state_name",
        y="student_teacher_ratio",
        markers=True,
    )
    fig = _style_au_chart(fig, title=title, x_title="State Name", y_title="Student-Teacher Ratio")

    for trace in fig.data:
        trace.name = "Student-Teacher Ratio"
        try:
            trace.line.color = INDIA_COLOR_TOKENS["Student-Teacher Ratio"]
        except Exception:
            pass
        try:
            trace.marker.color = INDIA_COLOR_TOKENS["Student-Teacher Ratio"]
        except Exception:
            pass

    st.plotly_chart(fig, use_container_width=True)


def _render_indicator_chart(states_df: pd.DataFrame) -> None:
    required = {"state_name", "weighted_avg_icsea", "weighted_indigenous_pct", "weighted_lbote_yes_pct"}
    if states_df.empty or not required.issubset(set(states_df.columns)):
        st.info("No academic and demographic indicator data available.")
        return

    metric_df = states_df[[
        "state_name",
        "weighted_avg_icsea",
        "weighted_indigenous_pct",
        "weighted_lbote_yes_pct",
    ]].copy()

    metric_df = metric_df.melt(
        id_vars="state_name",
        var_name="Metric",
        value_name="Value",
    )

    fig = px.line(
        metric_df,
        x="state_name",
        y="Value",
        color="Metric",
        markers=True,
        color_discrete_map={
            "weighted_avg_icsea": INDIA_COLOR_TOKENS["Weighted Avg ICSEA"],
            "weighted_indigenous_pct": INDIA_COLOR_TOKENS["Weighted Indigenous %"],
            "weighted_lbote_yes_pct": INDIA_COLOR_TOKENS["Weighted LBOTE %"],
        },
    )
    fig = _style_au_chart(
        fig,
        title="Academic & Demographic Indicators",
        x_title="State Name",
        y_title="Value",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_au_home() -> None:
    _inject_au_css()
    svc = _get_service()

    summary = svc.get_national_summary() or {}
    states_df = _safe_state_df()

    _page_header(
        "Australia · National Overview",
        "Live national and state-level education metrics aligned to the India dashboard visual standard.",
    )

    primary_kpis = _build_primary_kpis(summary)
    _render_kpi_cards(primary_kpis)

    st.markdown("")

    col1, col2 = st.columns([1, 1])
    with col1:
        _section_header("National Gender Overview", "Girls and boys student counts for Australia.")
        _render_gender_chart_from_summary(summary, title="Gender Split")

    with col2:
        _section_header("State Distribution", "State-wise student totals across Australia.")
        _render_top_states_students_chart(states_df, title="State-wise Total Students")

    st.markdown("")
    _section_header("State Performance Snapshot", "Summary grid aligned to India-style headers and formatting.")

    state_cols = [
        c for c in [
            "state_name",
            "state_abbr",
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
    display_states_df = states_df[state_cols].copy() if state_cols else states_df.copy()
    if not display_states_df.empty and "total_students" in display_states_df.columns:
        display_states_df = display_states_df.sort_values("total_students", ascending=False)
    _display_df(display_states_df)

    st.markdown("")
    c1, c2 = st.columns([1, 1])
    with c1:
        _section_header("State-wise Schools", "School counts by jurisdiction.")
        _render_top_states_schools_chart(states_df, title="State-wise Schools")
    with c2:
        _section_header("State-wise PTR", "Student-teacher ratio by jurisdiction.")
        _render_ptr_chart(states_df, title="Student-Teacher Ratio by State")


def render_au_state_dashboard() -> None:
    _inject_au_css()
    svc = _get_service()
    states_df = _safe_state_df()

    _page_header(
        "Australia · State Dashboard",
        "Compare district and school-level metrics within a selected state.",
    )

    if states_df.empty or "state_name" not in states_df.columns:
        st.warning("No Australia state data is available.")
        return

    state_options = states_df["state_name"].dropna().tolist()
    default_state = _resolve_state(default=state_options[0] if state_options else None)
    default_index = state_options.index(default_state) if default_state in state_options else 0

    selected_state = st.selectbox(
        "Select State",
        state_options,
        index=default_index,
        key="au_state_dashboard_selector",
    )
    st.session_state["au_selected_state"] = selected_state
    _update_state_query_param(selected_state)

    selected_state_row = states_df.loc[states_df["state_name"] == selected_state]
    state_summary = selected_state_row.iloc[0].to_dict() if not selected_state_row.empty else {}

    primary_kpis = _build_primary_kpis(state_summary)
    _render_kpi_cards(primary_kpis)

    secondary = _build_secondary_kpis(state_summary)
    _render_kpi_cards(secondary)

    district_df = _safe_district_df(selected_state)
    st.markdown("")
    _section_header(
        f"{selected_state} · District Snapshot",
        "District-level rollups presented with India-style headers and formatting.",
    )

    district_cols = [
        c for c in [
            "district_name",
            "schools",
            "total_students",
            "girls_students",
            "boys_students",
            "fte_teaching_staff",
            "student_teacher_ratio",
            "weighted_avg_icsea",
            "weighted_indigenous_pct",
            "weighted_lbote_yes_pct",
        ] if c in district_df.columns
    ]
    display_district_df = district_df[district_cols].copy() if district_cols else district_df.copy()
    if not display_district_df.empty and "total_students" in display_district_df.columns:
        display_district_df = display_district_df.sort_values("total_students", ascending=False)
    _display_df(display_district_df)

    st.markdown("")
    left, right = st.columns([1, 1])

    with left:
        _section_header("Top Districts by Students", f"Highest student totals in {selected_state}.")
        if not district_df.empty and {"district_name", "total_students"}.issubset(set(district_df.columns)):
            top_districts = district_df.copy().sort_values("total_students", ascending=False).head(15)
            fig = px.bar(
                top_districts,
                x="district_name",
                y="total_students",
                color_discrete_sequence=[INDIA_COLOR_TOKENS["Total Students"]],
            )
            fig = _style_au_chart(fig, title="Top Districts by Students", x_title="District Name", y_title="Total Students")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No district student data available.")

    with right:
        _section_header("Top Districts by Schools", f"Highest school counts in {selected_state}.")
        if not district_df.empty and {"district_name", "schools"}.issubset(set(district_df.columns)):
            top_districts = district_df.copy().sort_values("schools", ascending=False).head(15)
            fig = px.bar(
                top_districts,
                x="district_name",
                y="schools",
                color_discrete_sequence=[INDIA_COLOR_TOKENS["Schools"]],
            )
            fig = _style_au_chart(fig, title="Top Districts by Schools", x_title="District Name", y_title="Schools")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No district school data available.")

    st.markdown("")
    _section_header("School Directory", "Search and filter schools within the selected state.")

    district_options = []
    if "district_name" in district_df.columns:
        district_options = sorted([d for d in district_df["district_name"].dropna().unique().tolist() if d])

    filter_options = svc.get_filter_options() or {}
    management_types = filter_options.get("management_types", []) or []
    school_levels = filter_options.get("school_levels", []) or []

    f1, f2, f3, f4 = st.columns([1.2, 1.0, 1.0, 1.2])

    with f1:
        selected_district = st.selectbox(
            "District",
            ["All"] + district_options,
            index=0,
            key="au_school_filter_district",
        )
    with f2:
        selected_management = st.selectbox(
            "Management Type",
            ["All"] + management_types,
            index=0,
            key="au_school_filter_mgmt",
        )
    with f3:
        selected_level = st.selectbox(
            "School Level",
            ["All"] + school_levels,
            index=0,
            key="au_school_filter_level",
        )
    with f4:
        search = st.text_input("Search School", value="", key="au_school_search")

    school_filters = {
        "state_name": selected_state,
        "district_name": None if selected_district == "All" else selected_district,
        "management_type": None if selected_management == "All" else selected_management,
        "school_level": None if selected_level == "All" else selected_level,
        "delivery_model": None,
        "search": search or None,
        "limit": 250,
        "offset": 0,
    }

    schools_df = _safe_school_df(**school_filters)
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
        ] if c in schools_df.columns
    ]
    display_schools_df = schools_df[school_cols].copy() if school_cols else schools_df.copy()
    if not display_schools_df.empty and "total_students" in display_schools_df.columns:
        display_schools_df = display_schools_df.sort_values("total_students", ascending=False, na_position="last")
    _display_df(display_schools_df)


def render_au_analytics() -> None:
    _inject_au_css()
    svc = _get_service()
    summary = svc.get_national_summary() or {}
    states_df = _safe_state_df()

    _page_header(
        "Australia · Analytics",
        "Comparative analytics for Australia using India-parity labels, legends, colors, and table formatting.",
    )

    secondary_kpis = _build_secondary_kpis(summary)
    _render_kpi_cards(secondary_kpis)

    st.markdown("")

    col1, col2 = st.columns([1, 1])

    with col1:
        _section_header("Academic & Demographic Indicators", "State-wise comparison of ICSEA, Indigenous %, and LBOTE %.")
        _render_indicator_chart(states_df)

    with col2:
        _section_header("Student-Teacher Ratio", "PTR comparison across states and territories.")
        _render_ptr_chart(states_df, title="Student-Teacher Ratio by State")

    st.markdown("")
    col3, col4 = st.columns([1, 1])

    with col3:
        _section_header("States by Total Students", "Ordered highest to lowest.")
        _render_top_states_students_chart(states_df, title="State-wise Total Students")

    with col4:
        _section_header("States by School Count", "School counts by state and territory.")
        _render_top_states_schools_chart(states_df, title="State-wise Schools")

    st.markdown("")
    _section_header("Analytics Grid", "Formatted state-level analytics with India-style titles and values.")

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
