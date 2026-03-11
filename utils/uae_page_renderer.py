# utils/uae_page_renderer.py
# UAE dashboard rendering functions - integrated into existing 3-page navigation
# Academic year fixed to 2024-2025 | No year-over-year comparisons
# Renders inside Home / State Dashboard / Analytics pages based on session_state.selected_region

import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from utils.uae_connector import UAEConnector
except ImportError:
    UAEConnector = None

# ─── palette & constants ──────────────────────────────────────────────────────
UAE_YEAR = "2024-2025"

UAE_COLORS = {
    "primary":   "#006400",   # UAE green
    "secondary": "#C8102E",   # UAE red
    "accent":    "#FFD700",   # gold
    "neutral":   "#4A4A4A",
    "bg":        "#F5F7FA",
    "card_bg":   "#FFFFFF",
}

CHART_PALETTE = [
    "#006400", "#C8102E", "#FFD700", "#1E90FF",
    "#FF8C00", "#8B008B", "#20B2AA", "#DC143C",
]

# ─── CSS (mirrors India dashboard style) ─────────────────────────────────────
UAE_CSS = """
<style>
.uae-kpi-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 20px 18px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,.08);
    border-left: 5px solid #006400;
    margin-bottom: 12px;
}
.uae-kpi-label { font-size: 13px; color: #666; font-weight: 500; margin-bottom: 4px; }
.uae-kpi-value { font-size: 28px; font-weight: 700; color: #006400; }
.uae-kpi-sub   { font-size: 12px; color: #888; margin-top: 4px; }
.uae-section-header {
    font-size: 17px; font-weight: 700; color: #006400;
    border-bottom: 2px solid #FFD700;
    padding-bottom: 6px; margin: 18px 0 12px 0;
}
.uae-flag-banner {
    background: linear-gradient(135deg, #006400 0%, #008000 50%, #C8102E 100%);
    color: white; padding: 14px 20px; border-radius: 10px;
    font-size: 20px; font-weight: 700; margin-bottom: 16px;
    display: flex; align-items: center; gap: 10px;
}
.uae-info-box {
    background: #EAF4EA; border-left: 4px solid #006400;
    padding: 10px 14px; border-radius: 6px;
    font-size: 13px; color: #333; margin: 8px 0;
}
</style>
"""

# ─── helpers ─────────────────────────────────────────────────────────────────

def _q(sql: str, params=None) -> pd.DataFrame:
    """Direct psycopg2 query – no UAEConnector dependency."""
    return _direct_q(sql, params)


def _fmt(n) -> str:
    """Format large numbers with commas."""
    try:
        n = int(n)
        if n >= 1_000_000:
            return f"{n/1_000_000:.2f}M"
        if n >= 1_000:
            return f"{n:,}"
        return str(n)
    except Exception:
        return str(n)


def _export_buttons(df: pd.DataFrame, prefix: str):
    """CSV + Excel download buttons below a dataframe."""
    if df.empty:
        return
    c1, c2, _ = st.columns([1, 1, 4])
    csv = df.to_csv(index=False).encode()
    c1.download_button(
        "Export CSV", csv,
        file_name=f"uae_{prefix}.csv", mime="text/csv", key=f"csv_{prefix}"
    )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=prefix[:31])
    c2.download_button(
        "Export Excel", buf.getvalue(),
        file_name=f"uae_{prefix}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"xl_{prefix}"
    )


# ─── column-name discovery (handles schema drift) ────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _tbl_cols(table: str) -> list:
    # Uses _direct_q (no session_state) – safe inside @st.cache_data
    df = _direct_q(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='uae' AND table_name=%s ORDER BY ordinal_position",
        [table]
    )
    return df["column_name"].tolist() if not df.empty else []


def _pick_col(cols: list, *candidates) -> str:
    """Return the first candidate found in cols, or '' if none."""
    for c in candidates:
        if c in cols:
            return c
    return ""


# ─── session-state-FREE direct query (used inside @st.cache_data fns) ─────────
# @st.cache_data functions MUST NOT access st.session_state (Streamlit restriction).
# _direct_q uses a fresh psycopg2 connection each call so it is safe to cache.
_DB_PARAMS = dict(
    host="localhost", dbname="tutorcloud_db",
    user="tutorcloud_admin", password="TutorCloud2024!Secure"
)


def _direct_q(sql: str, params=None) -> pd.DataFrame:
    """Lightweight psycopg2 query – no session_state dependency."""
    try:
        import psycopg2
        with psycopg2.connect(**_DB_PARAMS) as conn:
            return pd.read_sql_query(sql, conn, params=params or [])
    except Exception as e:
        return pd.DataFrame()


# ─── sidebar filters ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _distinct(table: str, col: str) -> list:
    # Uses _direct_q (no session_state) – safe inside @st.cache_data
    if not col:
        return []
    try:
        df = _direct_q(
            f"SELECT DISTINCT {col} FROM uae.{table} "
            f"WHERE academic_year=%s AND {col} IS NOT NULL ORDER BY {col}",
            [UAE_YEAR]
        )
        return df.iloc[:, 0].tolist() if not df.empty else []
    except Exception:
        return []


def _build_sidebar_filters() -> dict:
    """
    Render UAE sidebar filters and return a dict of selected values.
    All filters default to 'All' (no filter applied).
    """
    enr_cols  = _tbl_cols("uae_fact_enrollment")
    sch_cols  = _tbl_cols("uae_fact_schools")
    pf_cols   = _tbl_cols("uae_fact_pass_fail")

    emirate_col     = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    edu_type_col    = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type")
    gender_col      = _pick_col(enr_cols, "gender", "student_gender")
    nat_col         = _pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality")
    cycle_col       = _pick_col(pf_cols,  "cycle", "education_cycle", "grade_level")
    curriculum_col  = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**🇦🇪 UAE Filters**")
    st.sidebar.caption(f"Academic Year: **{UAE_YEAR}** (fixed)")

    def _sel(label, opts, key):
        all_opts = ["All"] + [str(x) for x in opts if x]
        return st.sidebar.selectbox(label, all_opts, key=key)

    filters = {}

    if emirate_col:
        opts = _distinct("uae_fact_enrollment", emirate_col)
        filters["emirate"] = {"col": emirate_col, "val": _sel("Emirate", opts, "uae_emirate")}

    if edu_type_col:
        opts = _distinct("uae_fact_enrollment", edu_type_col)
        filters["edu_type"] = {"col": edu_type_col, "val": _sel("Education Type", opts, "uae_edu_type")}

    if gender_col:
        opts = _distinct("uae_fact_enrollment", gender_col)
        filters["gender"] = {"col": gender_col, "val": _sel("Gender", opts, "uae_gender")}

    if nat_col:
        opts = _distinct("uae_fact_enrollment", nat_col)
        filters["nationality"] = {"col": nat_col, "val": _sel("Nationality", opts, "uae_nat")}

    if cycle_col:
        opts = _distinct("uae_fact_pass_fail", cycle_col)
        filters["cycle"] = {"col": cycle_col, "val": _sel("Education Cycle", opts, "uae_cycle")}

    if curriculum_col:
        opts = _distinct("uae_fact_schools", curriculum_col)
        filters["curriculum"] = {"col": curriculum_col, "val": _sel("Curriculum", opts, "uae_curr")}

    return filters


def _where_clause(filters: dict, table_alias: str = "", allowed_cols: list = None) -> tuple:
    """Build a parameterised WHERE fragment from the filters dict."""
    parts, params = [], []
    prefix = f"{table_alias}." if table_alias else ""
    for _, finfo in filters.items():
        col = finfo["col"]
        val = finfo["val"]
        if val == "All":
            continue
        if allowed_cols is not None and col not in allowed_cols:
            continue
        parts.append(f"{prefix}{col} = %s")
        params.append(val)
    clause = (" AND " + " AND ".join(parts)) if parts else ""
    return clause, params


# ═══════════════════════════════════════════════════════════════════════════════
# 1. HOME PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_uae_home():
    st.markdown(UAE_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="uae-flag-banner">'
        '\U0001f1e6\U0001f1ea UAE Education Overview &mdash; Academic Year 2024&ndash;2025'
        '</div>',
        unsafe_allow_html=True
    )

    filters = _build_sidebar_filters()

    enr_cols = _tbl_cols("uae_fact_enrollment")
    sch_cols = _tbl_cols("uae_fact_schools")

    emirate_col  = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col  = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cnt_col  = _pick_col(sch_cols, "school_count", "num_schools", "count")

    where, params = _where_clause(filters, allowed_cols=enr_cols)

    # ── KPI row ──────────────────────────────────────────────────────────────
    kpi_cols = st.columns(4)

    # Total enrollment
    if enr_cnt_col:
        df = _q(
            f"SELECT COALESCE(SUM({enr_cnt_col}),0) AS val FROM uae.uae_fact_enrollment "
            f"WHERE academic_year=%s{where}",
            [UAE_YEAR] + params
        )
        total_enr = int(df.iloc[0, 0]) if not df.empty else 0
    else:
        total_enr = 0

    # Total schools
    if sch_cnt_col:
        sch_where, sch_params = _where_clause(filters, allowed_cols=sch_cols)
        df = _q(
            f"SELECT COALESCE(SUM({sch_cnt_col}),0) AS val FROM uae.uae_fact_schools "
            f"WHERE academic_year=%s{sch_where}",
            [UAE_YEAR] + sch_params
        )
        total_sch = int(df.iloc[0, 0]) if not df.empty else 0
    else:
        total_sch = 0

    # Emirate count
    em_count = 0
    if emirate_col:
        df = _q(
            f"SELECT COUNT(DISTINCT {emirate_col}) FROM uae.uae_fact_enrollment "
            f"WHERE academic_year=%s", [UAE_YEAR]
        )
        em_count = int(df.iloc[0, 0]) if not df.empty else 0

    # Gender parity (% female)
    gender_col = _pick_col(enr_cols, "gender", "student_gender")
    pct_female = None
    if gender_col and enr_cnt_col:
        df = _q(
            f"SELECT {gender_col}, SUM({enr_cnt_col}) AS cnt FROM uae.uae_fact_enrollment "
            f"WHERE academic_year=%s GROUP BY {gender_col}",
            [UAE_YEAR]
        )
        if not df.empty:
            df.columns = ["gender", "cnt"]
            total_g = df["cnt"].sum()
            fem = df[df["gender"].str.lower().str.startswith("f", na=False)]["cnt"].sum()
            if total_g > 0:
                pct_female = round(fem / total_g * 100, 1)

    with kpi_cols[0]:
        st.markdown(
            f'<div class="uae-kpi-card">'
            f'<div class="uae-kpi-label">Total Enrollment</div>'
            f'<div class="uae-kpi-value">{_fmt(total_enr)}</div>'
            f'<div class="uae-kpi-sub">Students 2024-25</div>'
            f'</div>', unsafe_allow_html=True
        )
    with kpi_cols[1]:
        st.markdown(
            f'<div class="uae-kpi-card" style="border-left-color:#C8102E">'
            f'<div class="uae-kpi-label">Total Schools</div>'
            f'<div class="uae-kpi-value">{_fmt(total_sch)}</div>'
            f'<div class="uae-kpi-sub">Registered 2024-25</div>'
            f'</div>', unsafe_allow_html=True
        )
    with kpi_cols[2]:
        st.markdown(
            f'<div class="uae-kpi-card" style="border-left-color:#FFD700">'
            f'<div class="uae-kpi-label">Emirates</div>'
            f'<div class="uae-kpi-value">{em_count}</div>'
            f'<div class="uae-kpi-sub">Coverage</div>'
            f'</div>', unsafe_allow_html=True
        )
    with kpi_cols[3]:
        val = f"{pct_female}%" if pct_female is not None else "N/A"
        st.markdown(
            f'<div class="uae-kpi-card" style="border-left-color:#1E90FF">'
            f'<div class="uae-kpi-label">Female Students</div>'
            f'<div class="uae-kpi-value">{val}</div>'
            f'<div class="uae-kpi-sub">Gender parity 2024-25</div>'
            f'</div>', unsafe_allow_html=True
        )

    st.markdown("---")

    # ── Emirate enrollment bar ────────────────────────────────────────────────
    if emirate_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">Enrollment by Emirate</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col} ORDER BY students DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(
                df, x="emirate", y="students", color="emirate",
                color_discrete_sequence=CHART_PALETTE,
                labels={"emirate": "Emirate", "students": "Students"},
                title="Student Enrollment by Emirate (2024-25)"
            )
            fig.update_layout(showlegend=False, plot_bgcolor="#FFF",
                              paper_bgcolor="#FFF", height=350)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df.rename(columns={"emirate": "Emirate", "students": "Students"}), "home_emirate_enrollment")

    # ── Gender split donut ───────────────────────────────────────────────────
    if gender_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">Student Gender Distribution</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {gender_col} AS gender, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {gender_col}",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.pie(
                df, names="gender", values="students",
                color_discrete_sequence=["#006400", "#C8102E", "#FFD700"],
                hole=0.45, title="Gender Distribution"
            )
            fig.update_layout(height=320)
            col1, col2 = st.columns([1, 2])
            col1.plotly_chart(fig, use_container_width=True)
            col2.dataframe(
                df.rename(columns={"gender": "Gender", "students": "Students"})
                  .assign(Share=lambda d: (d["Students"] / d["Students"].sum() * 100).round(1).astype(str) + "%"),
                use_container_width=True
            )

    # ── Schools by curriculum ────────────────────────────────────────────────
    curr_col = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")
    if curr_col and sch_cnt_col:
        st.markdown('<div class="uae-section-header">Schools by Curriculum</div>', unsafe_allow_html=True)
        sch_where, sch_params = _where_clause(filters, allowed_cols=sch_cols)
        df = _q(
            f"SELECT {curr_col} AS curriculum, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{sch_where} "
            f"GROUP BY {curr_col} ORDER BY schools DESC LIMIT 15",
            [UAE_YEAR] + sch_params
        )
        if not df.empty:
            fig = px.bar(
                df, x="schools", y="curriculum", orientation="h",
                color="curriculum", color_discrete_sequence=CHART_PALETTE,
                labels={"curriculum": "Curriculum", "schools": "Schools"},
                title="Schools by Curriculum Type"
            )
            fig.update_layout(showlegend=False, plot_bgcolor="#FFF",
                              paper_bgcolor="#FFF", height=max(300, len(df)*28))
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. STATE DASHBOARD (UAE = Emirates)
# ═══════════════════════════════════════════════════════════════════════════════

def render_uae_state_dashboard():
    st.markdown(UAE_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="uae-flag-banner">'
        '\U0001f1e6\U0001f1ea UAE State Dashboard &mdash; Academic Year 2024&ndash;2025'
        '</div>',
        unsafe_allow_html=True
    )

    filters = _build_sidebar_filters()

    tabs = st.tabs([
        "\U0001f4ca Overview",
        "\U0001f3eb Schools",
        "\U0001f468\u200d\U0001f3eb Teachers",
        "\U0001f4c8 Performance",
        "\U0001f30d Demographics",
    ])

    # ── TAB 1: Overview ───────────────────────────────────────────────────────
    with tabs[0]:
        _uae_tab_overview(filters)

    # ── TAB 2: Schools ────────────────────────────────────────────────────────
    with tabs[1]:
        _uae_tab_schools(filters)

    # ── TAB 3: Teachers ───────────────────────────────────────────────────────
    with tabs[2]:
        _uae_tab_teachers(filters)

    # ── TAB 4: Performance ────────────────────────────────────────────────────
    with tabs[3]:
        _uae_tab_performance(filters)

    # ── TAB 5: Demographics ───────────────────────────────────────────────────
    with tabs[4]:
        _uae_tab_demographics(filters)


# ── Sub-renderers for each State Dashboard tab ───────────────────────────────

def _uae_tab_overview(filters):
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    gender_col  = _pick_col(enr_cols, "gender", "student_gender")
    edu_col     = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type", "education_level")
    nat_col     = _pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality")

    where, params = _where_clause(filters, allowed_cols=enr_cols)

    st.markdown('<div class="uae-section-header">Emirate-wise Enrollment</div>', unsafe_allow_html=True)

    if emirate_col and enr_cnt_col:
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col} ORDER BY students DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(
                df, x="emirate", y="students",
                color_discrete_sequence=["#006400"],
                text="students",
                labels={"emirate": "Emirate", "students": "Students"},
                title="Total Enrollment by Emirate"
            )
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=360)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "overview_emirate")

    # Education-type split
    if edu_col and enr_cnt_col and emirate_col:
        st.markdown('<div class="uae-section-header">Enrollment by Education Type per Emirate</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {emirate_col} AS emirate, {edu_col} AS edu_type, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col}, {edu_col} ORDER BY emirate, students DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(
                df, x="emirate", y="students", color="edu_type",
                barmode="stack", color_discrete_sequence=CHART_PALETTE,
                labels={"emirate": "Emirate", "students": "Students", "edu_type": "Education Type"},
                title="Enrollment by Education Type"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=380)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "overview_edu_type")

    # Gender across emirates
    if gender_col and enr_cnt_col and emirate_col:
        st.markdown('<div class="uae-section-header">Gender Distribution by Emirate</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {emirate_col} AS emirate, {gender_col} AS gender, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col}, {gender_col} ORDER BY emirate, students DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(
                df, x="emirate", y="students", color="gender",
                barmode="group", color_discrete_sequence=["#006400", "#C8102E"],
                labels={"emirate": "Emirate", "students": "Students"},
                title="Gender Distribution across Emirates"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=360)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "overview_gender_emirate")

    # Nationality mix
    if nat_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">Emirati vs Expatriate Students</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {nat_col} AS nationality, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {nat_col} ORDER BY students DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            c1, c2 = st.columns(2)
            fig = px.pie(
                df, names="nationality", values="students", hole=0.4,
                color_discrete_sequence=CHART_PALETTE,
                title="Nationality Category Split"
            )
            c1.plotly_chart(fig, use_container_width=True)
            c2.dataframe(
                df.rename(columns={"nationality": "Nationality", "students": "Students"})
                  .assign(
                      Share=(df["students"] / df["students"].sum() * 100).round(1).astype(str) + "%"
                  ),
                use_container_width=True
            )
            _export_buttons(df, "overview_nationality")


def _uae_tab_schools(filters):
    sch_cols     = _tbl_cols("uae_fact_schools")
    emirate_col  = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    sch_cnt_col  = _pick_col(sch_cols, "school_count", "num_schools", "count")
    curr_col     = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")
    gender_col   = _pick_col(sch_cols, "gender", "school_gender")
    level_col    = _pick_col(sch_cols, "school_level", "level", "education_level", "cycle")

    where, params = _where_clause(filters, allowed_cols=sch_cols)

    st.markdown('<div class="uae-section-header">School Count by Emirate</div>', unsafe_allow_html=True)
    if emirate_col and sch_cnt_col:
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col} ORDER BY schools DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(
                df, x="emirate", y="schools",
                color_discrete_sequence=["#C8102E"],
                text="schools",
                labels={"emirate": "Emirate", "schools": "Schools"},
                title="Number of Schools by Emirate"
            )
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "schools_emirate")

    if curr_col and sch_cnt_col:
        st.markdown('<div class="uae-section-header">Schools by Curriculum</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {curr_col} AS curriculum, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where} "
            f"GROUP BY {curr_col} ORDER BY schools DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(
                df, x="curriculum", y="schools",
                color_discrete_sequence=CHART_PALETTE,
                labels={"curriculum": "Curriculum", "schools": "Schools"},
                title="Schools by Curriculum Type"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              xaxis_tickangle=-30, height=360)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "schools_curriculum")

    if gender_col and sch_cnt_col:
        st.markdown('<div class="uae-section-header">Schools by Gender</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {gender_col} AS gender, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where} "
            f"GROUP BY {gender_col}",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.pie(
                df, names="gender", values="schools", hole=0.4,
                color_discrete_sequence=["#006400", "#C8102E", "#FFD700"],
                title="Schools by Gender Type"
            )
            c1, _ = st.columns([1, 2])
            c1.plotly_chart(fig, use_container_width=True)

    # Curriculum × Emirate heatmap
    if curr_col and emirate_col and sch_cnt_col:
        st.markdown('<div class="uae-section-header">Curriculum × Emirate Matrix</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {emirate_col} AS emirate, {curr_col} AS curriculum, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col}, {curr_col}",
            [UAE_YEAR] + params
        )
        if not df.empty:
            pivot = df.pivot_table(index="curriculum", columns="emirate",
                                   values="schools", aggfunc="sum", fill_value=0)
            fig = px.imshow(
                pivot, color_continuous_scale="Greens",
                labels={"color": "Schools"},
                title="Schools per Curriculum per Emirate"
            )
            fig.update_layout(height=max(300, len(pivot)*28))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "schools_curriculum_emirate")


def _uae_tab_teachers(filters):
    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")
    emirate_col = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    gender_col  = _pick_col(tch_cols, "gender", "teacher_gender")
    nat_col     = _pick_col(tch_cols, "nationality_cat", "nationality_category", "nationality")
    subj_col    = _pick_col(tch_cols, "subject", "subject_en", "teaching_subject")

    # Try uae_fact_teachers_subject if emirate table is sparse
    tch_subj_cols = _tbl_cols("uae_fact_teachers_subject") or []

    where, params = _where_clause(filters, allowed_cols=tch_cols)

    st.markdown('<div class="uae-section-header">Teachers by Emirate</div>', unsafe_allow_html=True)
    if emirate_col and tch_cnt_col:
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({tch_cnt_col}) AS teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col} ORDER BY teachers DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(
                df, x="emirate", y="teachers",
                color_discrete_sequence=["#FFD700"],
                text="teachers",
                labels={"emirate": "Emirate", "teachers": "Teachers"},
                title="Teacher Count by Emirate"
            )
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "teachers_emirate")

    # PTR
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    enr_em_col  = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")

    if emirate_col and tch_cnt_col and enr_em_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">Pupil-Teacher Ratio (PTR) by Emirate</div>', unsafe_allow_html=True)
        df_t = _q(
            f"SELECT {emirate_col} AS emirate, SUM({tch_cnt_col}) AS teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s "
            f"GROUP BY {emirate_col}", [UAE_YEAR]
        )
        df_e = _q(
            f"SELECT {enr_em_col} AS emirate, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s "
            f"GROUP BY {enr_em_col}", [UAE_YEAR]
        )
        if not df_t.empty and not df_e.empty:
            df_ptr = df_e.merge(df_t, on="emirate", how="inner")
            df_ptr["PTR"] = (df_ptr["students"] / df_ptr["teachers"]).round(1)
            df_ptr = df_ptr.sort_values("PTR", ascending=False)
            fig = px.bar(
                df_ptr, x="PTR", y="emirate", orientation="h",
                color="PTR", color_continuous_scale="RdYlGn_r",
                labels={"emirate": "Emirate", "PTR": "Students per Teacher"},
                title="Pupil-Teacher Ratio by Emirate"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df_ptr[["emirate", "students", "teachers", "PTR"]], "ptr_emirate")

    # Teachers by gender
    if gender_col and tch_cnt_col:
        st.markdown('<div class="uae-section-header">Teacher Gender Distribution</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {gender_col} AS gender, SUM({tch_cnt_col}) AS teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where} "
            f"GROUP BY {gender_col}",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.pie(
                df, names="gender", values="teachers", hole=0.4,
                color_discrete_sequence=["#006400", "#C8102E"],
                title="Teacher Gender Split"
            )
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig, use_container_width=True)
            c2.dataframe(df.rename(columns={"gender": "Gender", "teachers": "Teachers"}),
                         use_container_width=True)


def _uae_tab_performance(filters):
    pf_cols     = _tbl_cols("uae_fact_pass_fail")
    emirate_col = _pick_col(pf_cols, "region_en", "emirate", "emirate_en", "region")
    cycle_col   = _pick_col(pf_cols, "cycle", "education_cycle", "grade_level")
    pass_col    = _pick_col(pf_cols, "pass_count", "passed", "pass_students")
    fail_col    = _pick_col(pf_cols, "fail_count", "failed", "fail_students")
    pass_pct    = _pick_col(pf_cols, "pass_rate", "pass_percentage", "pct_pass")

    sc_cols     = _tbl_cols("uae_fact_student_scores")
    subj_col_sc = _pick_col(sc_cols, "subject", "subject_en", "subject_name")
    avg_col     = _pick_col(sc_cols, "avg_score", "average_score", "mean_score", "score")
    em_sc_col   = _pick_col(sc_cols, "region_en", "emirate", "emirate_en", "region")

    where_pf, params_pf = _where_clause(filters, allowed_cols=pf_cols)

    st.markdown('<div class="uae-section-header">Pass / Fail Rates by Emirate</div>', unsafe_allow_html=True)
    if emirate_col and (pass_col or pass_pct):
        df = _q(
            f"SELECT {emirate_col} AS emirate, "
            + (f"SUM({pass_col}) AS passed, SUM({fail_col}) AS failed " if pass_col and fail_col else
               f"AVG({pass_pct}) AS pass_rate ")
            + f"FROM uae.uae_fact_pass_fail WHERE academic_year=%s{where_pf} "
            f"GROUP BY {emirate_col} ORDER BY emirate",
            [UAE_YEAR] + params_pf
        )
        if not df.empty:
            if "passed" in df.columns:
                df_m = df.melt("emirate", value_vars=["passed", "failed"],
                               var_name="result", value_name="students")
                fig = px.bar(
                    df_m, x="emirate", y="students", color="result",
                    barmode="stack",
                    color_discrete_sequence=["#006400", "#C8102E"],
                    labels={"emirate": "Emirate", "students": "Students"},
                    title="Pass vs Fail by Emirate"
                )
            else:
                fig = px.bar(
                    df, x="emirate", y="pass_rate",
                    color_discrete_sequence=["#006400"],
                    labels={"emirate": "Emirate", "pass_rate": "Pass Rate (%)"},
                    title="Pass Rate by Emirate"
                )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=360)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "pass_fail_emirate")

    if cycle_col and (pass_col or pass_pct):
        st.markdown('<div class="uae-section-header">Pass / Fail by Education Cycle</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {cycle_col} AS cycle, "
            + (f"SUM({pass_col}) AS passed, SUM({fail_col}) AS failed " if pass_col and fail_col else
               f"AVG({pass_pct}) AS pass_rate ")
            + f"FROM uae.uae_fact_pass_fail WHERE academic_year=%s{where_pf} "
            f"GROUP BY {cycle_col} ORDER BY {cycle_col}",
            [UAE_YEAR] + params_pf
        )
        if not df.empty:
            if "passed" in df.columns:
                df_m = df.melt("cycle", value_vars=["passed", "failed"],
                               var_name="result", value_name="students")
                fig = px.bar(
                    df_m, x="cycle", y="students", color="result",
                    barmode="group", color_discrete_sequence=["#006400", "#C8102E"],
                    title="Pass vs Fail by Cycle"
                )
            else:
                fig = px.bar(df, x="cycle", y="pass_rate",
                             color_discrete_sequence=["#1E90FF"],
                             title="Pass Rate by Education Cycle")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "pass_fail_cycle")

    # Average scores by subject
    if subj_col_sc and avg_col:
        st.markdown('<div class="uae-section-header">Average Scores by Subject</div>', unsafe_allow_html=True)
        where_sc, params_sc = _where_clause(filters, allowed_cols=sc_cols)
        df = _q(
            f"SELECT {subj_col_sc} AS subject, AVG({avg_col}) AS avg_score "
            f"FROM uae.uae_fact_student_scores WHERE academic_year=%s{where_sc} "
            f"GROUP BY {subj_col_sc} ORDER BY avg_score DESC",
            [UAE_YEAR] + params_sc
        )
        if not df.empty:
            df["avg_score"] = df["avg_score"].round(1)
            fig = px.bar(
                df, x="avg_score", y="subject", orientation="h",
                color="avg_score", color_continuous_scale="Greens",
                labels={"subject": "Subject", "avg_score": "Avg Score"},
                title="Average Student Score by Subject"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(300, len(df)*28))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "avg_scores_subject")

    # Scores by emirate
    if em_sc_col and avg_col:
        st.markdown('<div class="uae-section-header">Average Scores by Emirate</div>', unsafe_allow_html=True)
        where_sc, params_sc = _where_clause(filters, allowed_cols=sc_cols)
        df = _q(
            f"SELECT {em_sc_col} AS emirate, AVG({avg_col}) AS avg_score "
            f"FROM uae.uae_fact_student_scores WHERE academic_year=%s{where_sc} "
            f"GROUP BY {em_sc_col} ORDER BY avg_score DESC",
            [UAE_YEAR] + params_sc
        )
        if not df.empty:
            df["avg_score"] = df["avg_score"].round(1)
            fig = px.bar(
                df, x="emirate", y="avg_score",
                color_discrete_sequence=["#FFD700"],
                text="avg_score",
                labels={"emirate": "Emirate", "avg_score": "Avg Score"},
                title="Average Score by Emirate"
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "avg_scores_emirate")


def _uae_tab_demographics(filters):
    nat_cols    = _tbl_cols("uae_fact_student_nationalities")
    nat_col     = _pick_col(nat_cols, "nationality", "nationality_en", "country", "country_en")
    cnt_col     = _pick_col(nat_cols, "student_count", "count", "students")
    emirate_col = _pick_col(nat_cols, "region_en", "emirate", "emirate_en", "region")

    enr_cols     = _tbl_cols("uae_fact_enrollment")
    enr_em_col   = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col  = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    nat_cat_col  = _pick_col(enr_cols, "nationality_cat", "nationality_category")

    where_nat, params_nat = _where_clause(filters, allowed_cols=nat_cols)
    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols)

    st.markdown('<div class="uae-section-header">Top 20 Nationalities in UAE Schools</div>', unsafe_allow_html=True)
    if nat_col and cnt_col:
        df = _q(
            f"SELECT {nat_col} AS nationality, SUM({cnt_col}) AS students "
            f"FROM uae.uae_fact_student_nationalities WHERE academic_year=%s{where_nat} "
            f"GROUP BY {nat_col} ORDER BY students DESC LIMIT 20",
            [UAE_YEAR] + params_nat
        )
        if not df.empty:
            fig = px.bar(
                df, x="students", y="nationality", orientation="h",
                color="students", color_continuous_scale="Greens",
                labels={"nationality": "Nationality", "students": "Students"},
                title="Top 20 Student Nationalities"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(400, len(df)*22))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "nationalities_top20")

    # Emirati vs Expatriate by emirate
    if enr_em_col and nat_cat_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">Emirati vs Expatriate by Emirate</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {enr_em_col} AS emirate, {nat_cat_col} AS nat_cat, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr} "
            f"GROUP BY {enr_em_col}, {nat_cat_col} ORDER BY emirate",
            [UAE_YEAR] + params_enr
        )
        if not df.empty:
            fig = px.bar(
                df, x="emirate", y="students", color="nat_cat",
                barmode="stack", color_discrete_sequence=["#006400", "#C8102E", "#FFD700"],
                labels={"emirate": "Emirate", "students": "Students", "nat_cat": "Nationality"},
                title="Emirati vs Expatriate Students per Emirate"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=380)
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "demographics_nationality_emirate")

    # Country-level diversity treemap
    if nat_col and cnt_col:
        st.markdown('<div class="uae-section-header">Student Nationality Diversity (Treemap)</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {nat_col} AS nationality, SUM({cnt_col}) AS students "
            f"FROM uae.uae_fact_student_nationalities WHERE academic_year=%s "
            f"GROUP BY {nat_col} ORDER BY students DESC LIMIT 30",
            [UAE_YEAR]
        )
        if not df.empty:
            fig = px.treemap(
                df, path=["nationality"], values="students",
                color="students", color_continuous_scale="Greens",
                title="Nationality Diversity Treemap (Top 30)"
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ANALYTICS PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_uae_analytics():
    st.markdown(UAE_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="uae-flag-banner">'
        '\U0001f1e6\U0001f1ea UAE Analytics &mdash; Academic Year 2024&ndash;2025'
        '</div>',
        unsafe_allow_html=True
    )

    filters = _build_sidebar_filters()

    tabs = st.tabs([
        "\U0001f5fa Geographic Analysis",
        "\U0001f4c8 Performance Analytics",
        "\U0001f4ca Comparative Analysis",
        "\U0001f4dd Custom Report",
    ])

    with tabs[0]:
        _uae_analytics_geo(filters)
    with tabs[1]:
        _uae_analytics_perf(filters)
    with tabs[2]:
        _uae_analytics_compare(filters)
    with tabs[3]:
        _uae_analytics_custom(filters)


def _uae_analytics_geo(filters):
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cols    = _tbl_cols("uae_fact_schools")
    sch_em_col  = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")

    where_e, params_e = _where_clause(filters, allowed_cols=enr_cols)
    where_s, params_s = _where_clause(filters, allowed_cols=sch_cols)

    st.markdown('<div class="uae-section-header">Geographic Distribution of Enrollment</div>', unsafe_allow_html=True)

    if emirate_col and enr_cnt_col:
        df_enr = _q(
            f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_e} "
            f"GROUP BY {emirate_col} ORDER BY students DESC",
            [UAE_YEAR] + params_e
        )
        if not df_enr.empty:
            fig = px.treemap(
                df_enr, path=["emirate"], values="students",
                color="students", color_continuous_scale="Greens",
                title="Student Enrollment per Emirate (Treemap)"
            )
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df_enr, "geo_enrollment")

    if sch_em_col and sch_cnt_col:
        st.markdown('<div class="uae-section-header">School Distribution by Emirate</div>', unsafe_allow_html=True)
        df_sch = _q(
            f"SELECT {sch_em_col} AS emirate, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where_s} "
            f"GROUP BY {sch_em_col} ORDER BY schools DESC",
            [UAE_YEAR] + params_s
        )
        if not df_sch.empty:
            fig = px.bar(
                df_sch, x="schools", y="emirate", orientation="h",
                color="schools", color_continuous_scale="Reds",
                labels={"emirate": "Emirate", "schools": "Schools"},
                title="School Count by Emirate"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(260, len(df_sch)*34))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df_sch, "geo_schools")


def _uae_analytics_perf(filters):
    pf_cols     = _tbl_cols("uae_fact_pass_fail")
    emirate_col = _pick_col(pf_cols, "region_en", "emirate", "emirate_en", "region")
    subj_col    = _pick_col(pf_cols, "subject", "subject_en")
    cycle_col   = _pick_col(pf_cols, "cycle", "education_cycle")
    pass_col    = _pick_col(pf_cols, "pass_count", "passed", "pass_students")
    fail_col    = _pick_col(pf_cols, "fail_count", "failed", "fail_students")
    pass_pct    = _pick_col(pf_cols, "pass_rate", "pass_percentage", "pct_pass")

    sc_cols      = _tbl_cols("uae_fact_student_scores")
    subj_col_sc  = _pick_col(sc_cols, "subject", "subject_en", "subject_name")
    cycle_col_sc = _pick_col(sc_cols, "cycle", "education_cycle")
    avg_col      = _pick_col(sc_cols, "avg_score", "average_score", "mean_score", "score")
    em_sc_col    = _pick_col(sc_cols, "region_en", "emirate", "emirate_en", "region")

    where_pf, params_pf = _where_clause(filters, allowed_cols=pf_cols)
    where_sc, params_sc = _where_clause(filters, allowed_cols=sc_cols)

    st.markdown('<div class="uae-section-header">Pass Rate Heatmap: Emirate × Cycle</div>', unsafe_allow_html=True)
    if emirate_col and cycle_col and (pass_pct or (pass_col and fail_col)):
        metric = pass_pct if pass_pct else f"pass_count::float/(pass_count+fail_count)*100"
        df = _q(
            f"SELECT {emirate_col} AS emirate, {cycle_col} AS cycle, "
            f"AVG({pass_pct if pass_pct else pass_col}) AS rate "
            f"FROM uae.uae_fact_pass_fail WHERE academic_year=%s{where_pf} "
            f"GROUP BY {emirate_col}, {cycle_col}",
            [UAE_YEAR] + params_pf
        )
        if not df.empty:
            pivot = df.pivot_table(index="emirate", columns="cycle",
                                   values="rate", aggfunc="mean")
            fig = px.imshow(
                pivot, color_continuous_scale="RdYlGn",
                labels={"color": "Pass Rate"},
                title="Pass Rate Heatmap (Emirate x Education Cycle)"
            )
            fig.update_layout(height=max(280, len(pivot)*40))
            st.plotly_chart(fig, use_container_width=True)

    if subj_col and (pass_pct or pass_col):
        st.markdown('<div class="uae-section-header">Performance by Subject</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {subj_col} AS subject, "
            f"AVG({pass_pct if pass_pct else pass_col}) AS rate "
            f"FROM uae.uae_fact_pass_fail WHERE academic_year=%s{where_pf} "
            f"AND {subj_col} IS NOT NULL "
            f"GROUP BY {subj_col} ORDER BY rate DESC",
            [UAE_YEAR] + params_pf
        )
        if not df.empty:
            df["rate"] = df["rate"].round(1)
            fig = px.bar(
                df, x="rate", y="subject", orientation="h",
                color="rate", color_continuous_scale="RdYlGn",
                labels={"subject": "Subject", "rate": "Pass Rate / Count"},
                title="Performance by Subject"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(300, len(df)*26))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "perf_subject")


def _uae_analytics_compare(filters):
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    sch_cols    = _tbl_cols("uae_fact_schools")
    pf_cols     = _tbl_cols("uae_fact_pass_fail")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_em_col  = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    pf_em_col   = _pick_col(pf_cols,  "region_en", "emirate", "emirate_en", "region")
    pass_pct    = _pick_col(pf_cols,  "pass_rate", "pass_percentage", "pct_pass")
    pass_col    = _pick_col(pf_cols,  "pass_count", "passed")
    fail_col    = _pick_col(pf_cols,  "fail_count", "failed")

    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")
    tch_em_col  = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")

    st.markdown('<div class="uae-section-header">Cross-Emirate Comparison Dashboard</div>', unsafe_allow_html=True)

    # Build multi-metric comparison
    dfs = {}
    if emirate_col and enr_cnt_col:
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS enrollment "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s GROUP BY {emirate_col}",
            [UAE_YEAR]
        )
        if not df.empty:
            dfs["enrollment"] = df

    if sch_em_col and sch_cnt_col:
        df = _q(
            f"SELECT {sch_em_col} AS emirate, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s GROUP BY {sch_em_col}",
            [UAE_YEAR]
        )
        if not df.empty:
            dfs["schools"] = df

    if tch_em_col and tch_cnt_col:
        df = _q(
            f"SELECT {tch_em_col} AS emirate, SUM({tch_cnt_col}) AS teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s GROUP BY {tch_em_col}",
            [UAE_YEAR]
        )
        if not df.empty:
            dfs["teachers"] = df

    if dfs:
        merged = None
        for key, d in dfs.items():
            merged = d if merged is None else merged.merge(d, on="emirate", how="outer")
        if merged is not None:
            merged = merged.fillna(0)
            if "enrollment" in merged.columns and "teachers" in merged.columns:
                merged["PTR"] = (merged["enrollment"] / merged["teachers"]).replace([float("inf")], 0).round(1)
            if "enrollment" in merged.columns and "schools" in merged.columns:
                merged["Students/School"] = (merged["enrollment"] / merged["schools"]).replace([float("inf")], 0).round(1)

            st.dataframe(merged.set_index("emirate"), use_container_width=True)
            _export_buttons(merged, "compare_emirate_metrics")

            numeric_cols = [c for c in merged.columns if c != "emirate"]
            sel = st.selectbox("Select metric to visualise", numeric_cols, key="uae_compare_sel")
            if sel:
                fig = px.bar(
                    merged, x="emirate", y=sel,
                    color_discrete_sequence=["#006400"],
                    text=sel,
                    title=f"{sel} by Emirate (2024-25)"
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=360)
                st.plotly_chart(fig, use_container_width=True)

    # UAE National summary
    st.markdown('<div class="uae-section-header">UAE Country-Level Summary</div>', unsafe_allow_html=True)
    rows = []
    if enr_cnt_col:
        df = _q(f"SELECT SUM({enr_cnt_col}) AS v FROM uae.uae_fact_enrollment WHERE academic_year=%s", [UAE_YEAR])
        if not df.empty:
            rows.append({"Metric": "Total Students", "Value": _fmt(int(df.iloc[0, 0]))})
    if sch_cnt_col:
        df = _q(f"SELECT SUM({sch_cnt_col}) AS v FROM uae.uae_fact_schools WHERE academic_year=%s", [UAE_YEAR])
        if not df.empty:
            rows.append({"Metric": "Total Schools", "Value": _fmt(int(df.iloc[0, 0]))})
    if tch_cnt_col:
        df = _q(f"SELECT SUM({tch_cnt_col}) AS v FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s", [UAE_YEAR])
        if not df.empty:
            rows.append({"Metric": "Total Teachers", "Value": _fmt(int(df.iloc[0, 0]))})
    if rows:
        st.table(pd.DataFrame(rows).set_index("Metric"))


def _uae_analytics_custom(filters):
    st.markdown('<div class="uae-section-header">Custom Report Builder</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="uae-info-box">Select a table and metric below to generate a custom cross-tabulation report.</div>',
        unsafe_allow_html=True
    )

    tables = {
        "Enrollment (uae_fact_enrollment)": "uae_fact_enrollment",
        "Schools (uae_fact_schools)": "uae_fact_schools",
        "Teachers by Emirate (uae_fact_teachers_emirate)": "uae_fact_teachers_emirate",
        "Pass / Fail (uae_fact_pass_fail)": "uae_fact_pass_fail",
        "Student Scores (uae_fact_student_scores)": "uae_fact_student_scores",
        "Nationalities (uae_fact_student_nationalities)": "uae_fact_student_nationalities",
    }

    table_label = st.selectbox("Table", list(tables.keys()), key="uae_custom_table")
    table_name  = tables[table_label]
    cols        = _tbl_cols(table_name)

    if not cols:
        st.info("No columns found for selected table.")
        return

    # Detect numeric cols
    df_types = _q(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema='uae' AND table_name=%s ORDER BY ordinal_position",
        [table_name]
    )
    num_cols = []
    cat_cols = []
    if not df_types.empty:
        for _, row in df_types.iterrows():
            dt = row["data_type"].lower()
            if any(t in dt for t in ["int", "numeric", "float", "double", "real", "decimal"]):
                num_cols.append(row["column_name"])
            elif row["column_name"] != "academic_year":
                cat_cols.append(row["column_name"])

    if not num_cols or not cat_cols:
        st.info("Could not identify numeric / categorical columns in this table.")
        return

    c1, c2 = st.columns(2)
    group_col  = c1.selectbox("Group by (dimension)", cat_cols, key="uae_custom_grp")
    metric_col = c2.selectbox("Metric (numeric)", num_cols, key="uae_custom_metric")
    agg_fn     = st.radio("Aggregation", ["SUM", "AVG", "COUNT", "MAX"], horizontal=True, key="uae_custom_agg")

    if st.button("Generate Report", key="uae_custom_run"):
        where_c, params_c = _where_clause(filters, allowed_cols=cols)
        df = _q(
            f"SELECT {group_col} AS dimension, {agg_fn}({metric_col}) AS value "
            f"FROM uae.{table_name} WHERE academic_year=%s{where_c} "
            f"AND {group_col} IS NOT NULL "
            f"GROUP BY {group_col} ORDER BY value DESC LIMIT 50",
            [UAE_YEAR] + params_c
        )
        if df.empty:
            st.info("No data returned for this combination.")
        else:
            df["value"] = df["value"].round(2) if df["value"].dtype == float else df["value"]
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(
                    df, x="value", y="dimension", orientation="h",
                    color="value", color_continuous_scale="Greens",
                    labels={"dimension": group_col, "value": f"{agg_fn}({metric_col})"},
                    title=f"{agg_fn}({metric_col}) by {group_col}"
                )
                fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                                  height=max(300, len(df)*22))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.dataframe(df.rename(columns={"dimension": group_col, "value": f"{agg_fn}({metric_col})"}),
                             use_container_width=True)
            _export_buttons(df.rename(columns={"dimension": group_col, "value": f"{agg_fn}({metric_col})"}),
                            f"custom_{table_name}_{group_col}")
