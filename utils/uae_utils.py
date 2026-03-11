"""
utils/uae_utils.py
UAE-specific utility functions — TutorCloud Global Schools Dashboard

Shared helpers for formatting, charting, and KPI rendering.
Mirrors the pattern of existing ui_components.py but UAE-specific.
India's utilities are untouched.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ── UAE colour palette (flag-inspired + TutorCloud blue) ─────────────────────
UAE = {
    "green":     "#00732F",   # UAE flag green
    "red":       "#EF3340",   # UAE flag red
    "black":     "#000000",   # UAE flag black stripe
    "white":     "#FFFFFF",
    "gold":      "#C09A3A",   # accent gold
    "blue":      "#1e88e5",   # TutorCloud blue (shared with India)
    "bg":        "#F8F9FA",
    "card_bg":   "#FFFFFF",
    "text_muted":"#616161",
}

# Gradient for KPI card left border
GRADIENT_GREEN = f"linear-gradient(135deg, {UAE['green']} 0%, #009444 100%)"

# Chart colour sequences
EMIRATE_SEQ = px.colors.qualitative.Set2
GREEN_SCALE  = ["#c8e6c9", UAE["green"]]
BLUE_SCALE   = ["#bbdefb",  UAE["blue"]]
PERF_SCALE   = ["#EF3340", "#FFF176", "#00732F"]   # red→yellow→green


# ── Number formatters ─────────────────────────────────────────────────────────

def fmt(n) -> str:
    """559743 → '559,743'   |   None / NaN → 'N/A'"""
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "N/A"
    return f"{int(n):,}"


def fmt_pct(n, decimals: int = 1) -> str:
    """87.456 → '87.5%'"""
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "N/A"
    return f"{float(n):.{decimals}f}%"


def pct(num, denom) -> float:
    if not denom: return 0.0
    return round(float(num) * 100 / float(denom), 1)


# ── KPI card  (matches India's card style exactly, UAE left-border colour) ────

def uae_kpi_card(label: str, value: str, delta=None,
                  delta_label: str = "vs prev year",
                  icon: str = "📊",
                  border_color: str = None):
    """
    Renders one KPI metric card.
    Left-border colour defaults to UAE green.
    Identical HTML structure to India's kpi_card so shared CSS applies.
    """
    bc = border_color or UAE["green"]
    delta_html = ""
    if delta is not None:
        arrow = "▲" if delta >= 0 else "▼"
        color = "#00C851" if delta >= 0 else "#FF4444"
        delta_html = (
            f'<p style="color:{color};font-size:0.75rem;margin:2px 0 0">'
            f'{arrow} {fmt(abs(delta))} {delta_label}</p>'
        )
    st.markdown(f"""
        <div style="
            background:{UAE['card_bg']};
            border-radius:12px;
            padding:18px 20px;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);
            border-left:4px solid {bc};
            min-height:110px;">
            <p style="font-size:0.70rem;color:{UAE['text_muted']};font-weight:600;
                      text-transform:uppercase;letter-spacing:0.5px;
                      margin:0;white-space:normal;line-height:1.25">{icon} {label}</p>
            <p style="font-size:1.5rem;font-weight:700;
                      background:linear-gradient(135deg,{UAE['blue']} 0%,#1976d2 100%);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      background-clip:text;margin:6px 0">{value}</p>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)


# ── UAE page header banner ────────────────────────────────────────────────────

def uae_page_header(title: str, subtitle: str, year: str):
    st.markdown(f"""
        <div style="
            background:linear-gradient(135deg,{UAE['green']} 0%,#009444 100%);
            padding:20px 28px;border-radius:14px;margin-bottom:20px;
            box-shadow:0 4px 12px rgba(0,115,47,0.3)">
            <div style="display:flex;align-items:center;gap:12px">
                <span style="font-size:2rem">🇦🇪</span>
                <div>
                    <h1 style="color:white;margin:0;font-size:1.8rem;font-weight:700">{title}</h1>
                    <p style="color:rgba(255,255,255,0.85);margin:4px 0 0;font-size:0.9rem">
                        {subtitle} · Academic Year <b>{year}</b>
                    </p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# ── Section subheader (shared look with India) ────────────────────────────────

def uae_section_header(text: str):
    st.markdown(f"""
        <h3 style="color:{UAE['green']};border-bottom:2px solid {UAE['green']};
                   padding-bottom:6px;margin-top:20px">{text}</h3>
    """, unsafe_allow_html=True)


# ── "Not yet connected" banner (shown while India is live, UAE is in dev) ─────

def uae_dev_banner():
    st.info(
        "🔧 **UAE Dashboard is under active development.** "
        "India dashboard remains live and unaffected. "
        "This page will connect to the region selector once UAE data is verified.",
        icon="🇦🇪"
    )


# ── ETL not run yet warning ───────────────────────────────────────────────────

def uae_setup_warning():
    st.warning("""
    ⚠️ **UAE database tables not loaded yet.**
    Run the ETL pipeline first:
    ```bash
    psql -U postgres -d tutorcloud -f uae_schema_ddl.sql
    python3 uae_etl_pipeline.py
    ```
    """)


# ── Chart builders ────────────────────────────────────────────────────────────

def bar_h(df, x: str, y: str, title: str,
          color_scale=None, text_col: str = None,
          height: int = 400) -> go.Figure:
    """Horizontal bar chart — reused across all UAE tabs."""
    cs = color_scale or GREEN_SCALE
    text = text_col or x
    fig = px.bar(
        df.sort_values(x, ascending=True),
        x=x, y=y, orientation="h",
        color=x, color_continuous_scale=cs,
        title=title, text=text,
    )
    fig.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
    )
    fig.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        height=height,
        plot_bgcolor="white",
        margin=dict(l=10, r=60, t=50, b=10),
    )
    return fig


def donut(labels, values, title: str, colors: list = None,
          center_text: str = None, height: int = 320) -> go.Figure:
    """Donut / pie chart — reused across all UAE tabs."""
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker_colors=colors or [UAE["green"], UAE["red"], UAE["gold"], UAE["blue"]],
    ))
    annotations = []
    if center_text:
        annotations.append(dict(
            text=center_text, x=0.5, y=0.5,
            font_size=13, showarrow=False
        ))
    fig.update_layout(
        title=title,
        annotations=annotations,
        height=height,
        showlegend=True,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def line_trend(df, x: str, y: str, title: str,
               color: str = None, height: int = 300) -> go.Figure:
    """Line chart for trend data."""
    fig = px.line(
        df, x=x, y=y,
        markers=True,
        title=title,
        color_discrete_sequence=[color or UAE["green"]],
    )
    fig.update_traces(line_width=3, marker_size=8)
    fig.update_layout(
        plot_bgcolor="white",
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig


def treemap_chart(df, path_col: str, value_col: str,
                  color_col: str, title: str, height: int = 420) -> go.Figure:
    """Treemap for nationality diversity."""
    fig = px.treemap(
        df,
        path=[path_col],
        values=value_col,
        color=color_col,
        color_continuous_scale=["#c8e6c9", UAE["green"]],
        title=title,
    )
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def perf_bar(df, x: str, y: str, title: str,
             range_color=(70, 100), height: int = 400) -> go.Figure:
    """Performance/pass-rate bar — red→yellow→green scale."""
    fig = px.bar(
        df.sort_values(x, ascending=True),
        x=x, y=y, orientation="h",
        color=x,
        color_continuous_scale=PERF_SCALE,
        range_color=list(range_color),
        title=title,
        text=x,
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        coloraxis_showscale=True,
        height=height,
        plot_bgcolor="white",
        margin=dict(l=10, r=60, t=50, b=10),
    )
    return fig


# ── Sidebar builder ───────────────────────────────────────────────────────────

def uae_sidebar(years: list, regions: list, edu_types: list) -> tuple:
    """
    Renders UAE sidebar filters.
    Returns (selected_year, selected_region, selected_edu_type).
    Called ONLY from the UAE page — India sidebar is untouched.
    """
    with st.sidebar:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/"
            "Flag_of_the_United_Arab_Emirates.svg/320px-Flag_of_the_United_Arab_Emirates.svg.png",
            width=110,
        )
        st.markdown("### 🇦🇪 UAE Filters")
        st.divider()

        sel_year = st.selectbox(
            "📅 Academic Year",
            years,
            index=0,
            key="uae_year",
        )
        sel_region = st.selectbox(
            "🏙️ Emirate",
            regions,
            index=0,
            key="uae_region",
        )
        sel_edu = st.selectbox(
            "🏫 Education Type",
            edu_types,
            index=0,
            key="uae_edu_type",
        )

        st.divider()
        st.caption("📊 Data: UAE Ministry of Education")
        st.caption("🔗 [MoE Open Data Portal](https://moe.gov.ae/Ar/OpenData)")
        st.caption("📅 Last dataset: 09 Mar 2026")

    return sel_year, sel_region, sel_edu
