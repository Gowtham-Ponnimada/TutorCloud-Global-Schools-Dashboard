# utils/uae_page_renderer.py  ── v3.0 ── Full UAE Dashboard
# Matches India dashboard UI/UX exactly (Home + State Dashboard + Analytics)
# Academic year: 2024-2025 (fixed – no YoY comparisons)
# Renders inside pages/1_Home.py, pages/2_State_Dashboard.py, pages/4_Analytics.py
# based on st.session_state["selected_region"] == "UAE"

import io
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# India professional CSS (same look as India dashboard)
try:
    from ui_styles import inject_professional_css as _inject_css
except ImportError:
    _inject_css = None

# ─── UAE palette & constants ──────────────────────────────────────────────────
UAE_YEAR = "2024-2025"

UAE_COLORS = {
    "primary":   "#006400",
    "secondary": "#C8102E",
    "accent":    "#FFD700",
    "neutral":   "#4A4A4A",
    "bg":        "#F5F7FA",
    "card_bg":   "#FFFFFF",
}

CHART_PALETTE = [
    "#006400", "#C8102E", "#FFD700", "#1E90FF",
    "#FF8C00", "#8B008B", "#20B2AA", "#DC143C",
    "#2E8B57", "#B8860B",
]

# ─── CSS (mirrors India dashboard style with UAE national colours) ────────────
UAE_CSS = """
<style>
/* ── UAE KPI cards (match India card style with UAE colours) ── */
[data-testid="stMetric"] {
    background-color: white;
    padding: 1.2rem;
    border-radius: 12px;
    border: 3px solid #006400;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transition: transform 0.2s, box-shadow 0.2s;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.12);
}
[data-testid="stMetricValue"] {
    font-size: clamp(1.3rem, 3vw, 2rem) !important;
    font-weight: 700;
    color: #006400;
    overflow: visible !important;
    white-space: nowrap !important;
}
[data-testid="stMetricLabel"] {
    font-size: clamp(0.7rem, 2vw, 0.9rem);
    font-weight: 600;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
/* ── Section headers ── */
.uae-section-header {
    font-size: 17px; font-weight: 700; color: #006400;
    border-bottom: 2px solid #FFD700;
    padding-bottom: 6px; margin: 20px 0 14px 0;
}
/* ── Flag banner ── */
.uae-flag-banner {
    background: linear-gradient(135deg, #006400 0%, #008000 50%, #C8102E 100%);
    color: white; padding: 14px 22px; border-radius: 10px;
    font-size: 20px; font-weight: 700; margin-bottom: 16px;
    display: flex; align-items: center; gap: 10px;
}
/* ── Info box ── */
.uae-info-box {
    background: #EAF4EA; border-left: 4px solid #006400;
    padding: 12px 16px; border-radius: 6px;
    font-size: 13px; color: #333; margin: 8px 0;
}
/* ── Nav cards (match India Explore More section) ── */
.uae-nav-card {
    background-color: white;
    padding: 1.5rem; border-radius: 12px;
    border: 3px solid #006400;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    cursor: pointer; transition: all 0.3s ease;
    text-decoration: none; display: block; height: 100%;
}
.uae-nav-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
    border-color: #C8102E;
}
/* ── Main header (same as India) ── */
.main-header {
    font-size: clamp(1.5rem, 4vw, 2.2rem);
    font-weight: 700; color: #006400;
    padding-bottom: 8px; margin-bottom: 4px;
}
.sub-header {
    font-size: 1rem; color: #555; margin-bottom: 20px;
}
/* ── Section header (same as India) ── */
.section-header {
    font-size: 1.1rem; font-weight: 700;
    color: #006400; background: #EAF4EA;
    padding: 8px 14px; border-radius: 6px;
    margin: 18px 0 12px 0;
    border-left: 4px solid #006400;
}
/* ── Sidebar UAE marker ── */
.uae-sidebar-badge {
    background: linear-gradient(90deg,#006400,#C8102E);
    color: white; border-radius: 6px; padding: 4px 10px;
    font-size: 12px; font-weight: 700; margin-bottom: 8px;
    display: inline-block;
}
/* ── Loading overlay ── */
.stSpinner > div { display: none !important; }
</style>
"""

# ─── DB connection params ─────────────────────────────────────────────────────
_DB_PARAMS = dict(
    host="localhost", dbname="tutorcloud_db",
    user="tutorcloud_admin", password="TutorCloud2024!Secure"
)


# ─── Core query helpers ───────────────────────────────────────────────────────

def _direct_q(sql: str, params=None) -> pd.DataFrame:
    """RealDictCursor psycopg2 query – bypasses pandas DBAPI2 restriction."""
    try:
        import psycopg2, psycopg2.extras
        with psycopg2.connect(**_DB_PARAMS) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or [])
                rows = cur.fetchall()
                if not rows:
                    cols = [d[0] for d in cur.description] if cur.description else []
                    return pd.DataFrame(columns=cols)
                return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        print(f"[UAE _direct_q ERROR] {e}")
        return pd.DataFrame()


def _q(sql: str, params=None) -> pd.DataFrame:
    return _direct_q(sql, params)


@st.cache_data(ttl=3600, show_spinner=False)
def _tbl_cols(table: str) -> list:
    df = _direct_q(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='uae' AND table_name=%s ORDER BY ordinal_position",
        [table]
    )
    return df["column_name"].tolist() if not df.empty else []


def _pick_col(cols: list, *candidates) -> str:
    for c in candidates:
        if c in cols:
            return c
    return ""


@st.cache_data(ttl=3600, show_spinner=False)
def _distinct(table: str, col: str) -> list:
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


def _fmt(n) -> str:
    """Format integer with comma separators – matches India format_number()."""
    try:
        n = int(n)
        return f"{n:,}"
    except Exception:
        return str(n)


def _fmt_ptr(students, teachers) -> str:
    """Format PTR as integer ratio string – matches India format_ptr()."""
    try:
        if teachers and int(teachers) > 0:
            ratio = round(students / teachers)
            return f"{ratio}:1"
        return "N/A"
    except Exception:
        return "N/A"


def _fmt_dec(val, decimals=2) -> str:
    """Format a float to N decimal places."""
    try:
        return f"{float(val):.{decimals}f}"
    except Exception:
        return "N/A"


def _export_buttons(df: pd.DataFrame, prefix: str):
    if df.empty:
        return
    c1, c2, _ = st.columns([1, 1, 4])
    csv = df.to_csv(index=False).encode()
    c1.download_button("⬇ Export CSV", csv,
                       file_name=f"uae_{prefix}.csv",
                       mime="text/csv", key=f"csv_{prefix}")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=prefix[:31])
    c2.download_button("⬇ Export Excel", buf.getvalue(),
                       file_name=f"uae_{prefix}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key=f"xl_{prefix}")


# ─── Sidebar filters ──────────────────────────────────────────────────────────

def _build_sidebar_filters() -> dict:
    """UAE sidebar – same look as India's sidebar filters."""
    try:
        enr_cols = _tbl_cols("uae_fact_enrollment")
        sch_cols = _tbl_cols("uae_fact_schools")
        pf_cols  = _tbl_cols("uae_fact_pass_fail")

        emirate_col    = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
        edu_type_col   = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type")
        gender_col     = _pick_col(enr_cols, "gender", "student_gender")
        nat_col        = _pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality")
        cycle_col      = _pick_col(pf_cols,  "cycle", "education_cycle", "grade_level")
        curriculum_col = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")

        st.sidebar.markdown("---")
        st.sidebar.markdown(
            '<span class="uae-sidebar-badge">🇦🇪 UAE Filters</span>',
            unsafe_allow_html=True
        )
        st.sidebar.caption(f"Academic Year: **{UAE_YEAR}** (fixed)")

        def _sel(label, opts, key):
            all_opts = ["All"] + [str(x) for x in opts if x]
            return st.sidebar.selectbox(label, all_opts, key=key)

        filters = {}
        if emirate_col:
            opts = _distinct("uae_fact_enrollment", emirate_col)
            filters["emirate"] = {"col": emirate_col, "val": _sel("🏙️ Emirate", opts, "uae_emirate")}
        if edu_type_col:
            opts = _distinct("uae_fact_enrollment", edu_type_col)
            filters["edu_type"] = {"col": edu_type_col, "val": _sel("📚 Education Type", opts, "uae_edu_type")}
        if gender_col:
            opts = _distinct("uae_fact_enrollment", gender_col)
            filters["gender"] = {"col": gender_col, "val": _sel("👤 Gender", opts, "uae_gender")}
        if nat_col:
            opts = _distinct("uae_fact_enrollment", nat_col)
            filters["nationality"] = {"col": nat_col, "val": _sel("🌍 Nationality Category", opts, "uae_nat")}
        if cycle_col:
            opts = _distinct("uae_fact_pass_fail", cycle_col)
            filters["cycle"] = {"col": cycle_col, "val": _sel("🎓 Education Cycle", opts, "uae_cycle")}
        if curriculum_col:
            opts = _distinct("uae_fact_schools", curriculum_col)
            filters["curriculum"] = {"col": curriculum_col, "val": _sel("📖 Curriculum", opts, "uae_curr")}

        # Show active filters in sidebar
        active = [v["val"] for v in filters.values() if v["val"] != "All"]
        if active:
            st.sidebar.markdown("---")
            st.sidebar.markdown("**✅ Active Filters**")
            for a in active:
                st.sidebar.markdown(f"- {a}")
        return filters

    except Exception as ex:
        st.sidebar.warning(f"⚠️ UAE filter error: {ex}")
        return {}


def _where_clause(filters: dict, table_alias: str = "", allowed_cols: list = None) -> tuple:
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


# ══════════════════════════════════════════════════════════════════════════════
# 1. HOME PAGE  ── mirrors India Home exactly
# ══════════════════════════════════════════════════════════════════════════════

def render_uae_home():
    if _inject_css:
        _inject_css()
    st.markdown(UAE_CSS, unsafe_allow_html=True)

    # ── Header (matches India: main-header + sub-header) ──────────────────────
    st.markdown('<div class="main-header">🇦🇪 UAE Education Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">National K-12 Education Overview — Academic Year 2024–2025</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    # No sidebar filters on Home page (matches India Home)
    filters = {}  # empty – no sidebar filtering on Home

    # ── Gather column names ────────────────────────────────────────────────────
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    sch_cols    = _tbl_cols("uae_fact_schools")
    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    gender_col  = _pick_col(enr_cols, "gender", "student_gender")

    where, params = _where_clause(filters, allowed_cols=enr_cols)

    # ─────────────────────────────────────────────────────────────────────────
    # KPI SECTION  ── 6 metrics in 2 rows (same structure as India)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("## 📊 National Overview")

    # Row 1: Emirates, Schools, Students
    col1, col2, col3 = st.columns(3)

    # Emirates count
    em_count = 0
    if emirate_col:
        df = _q(f"SELECT COUNT(DISTINCT {emirate_col}) FROM uae.uae_fact_enrollment WHERE academic_year=%s",
                [UAE_YEAR])
        em_count = int(df.iloc[0, 0]) if not df.empty else 0

    # Total schools
    total_sch = 0
    if sch_cnt_col:
        sch_where, sch_params = _where_clause(filters, allowed_cols=sch_cols)
        df = _q(f"SELECT COALESCE(SUM({sch_cnt_col}),0) FROM uae.uae_fact_schools WHERE academic_year=%s{sch_where}",
                [UAE_YEAR] + sch_params)
        total_sch = int(df.iloc[0, 0]) if not df.empty else 0

    # Total students
    total_enr = 0
    if enr_cnt_col:
        df = _q(f"SELECT COALESCE(SUM({enr_cnt_col}),0) FROM uae.uae_fact_enrollment WHERE academic_year=%s{where}",
                [UAE_YEAR] + params)
        total_enr = int(df.iloc[0, 0]) if not df.empty else 0

    with col1:
        st.metric("TOTAL EMIRATES", str(em_count), help="Emirates with data coverage (2024-25)")
    with col2:
        st.metric("TOTAL SCHOOLS", _fmt(total_sch), help="Registered schools (2024-25)")
    with col3:
        st.metric("TOTAL STUDENTS", _fmt(total_enr), help="Total enrolled students (2024-25)")

    # Row 2: Teachers, PTR, Students/School
    col4, col5, col6 = st.columns(3)

    # Total teachers
    total_tch = 0
    if tch_cnt_col:
        tch_where, tch_params = _where_clause(filters, allowed_cols=tch_cols)
        df = _q(f"SELECT COALESCE(SUM({tch_cnt_col}),0) FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{tch_where}",
                [UAE_YEAR] + tch_params)
        total_tch = int(df.iloc[0, 0]) if not df.empty else 0

    # PTR – integer ratio matching India format_ptr()
    ptr_str = _fmt_ptr(total_enr, total_tch)

    # Students per school – whole number with commas, matching India
    sps_str = "N/A"
    if total_sch > 0 and total_enr > 0:
        sps_str = _fmt(int(round(total_enr / total_sch)))

    # % Female
    pct_female = None
    if gender_col and enr_cnt_col:
        df = _q(
            f"SELECT {gender_col}, SUM({enr_cnt_col}) AS cnt FROM uae.uae_fact_enrollment "
            f"WHERE academic_year=%s GROUP BY {gender_col}", [UAE_YEAR]
        )
        if not df.empty:
            df.columns = ["gender", "cnt"]
            total_g = df["cnt"].sum()
            fem = df[df["gender"].str.lower().str.startswith("f", na=False)]["cnt"].sum()
            if total_g > 0:
                pct_female = round(fem / total_g * 100, 1)

    with col4:
        st.metric("TOTAL TEACHERS", _fmt(total_tch), help="Total registered teachers (2024-25)")
    with col5:
        st.metric("PTR (NATIONAL)", ptr_str, help="Pupil-Teacher Ratio (2024-25)")
    with col6:
        st.metric("STUDENTS/SCHOOL", sps_str, help="Average students per school (2024-25)")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # CHART 1: Enrollment by Emirate  (= India's "Top 10 States by School Count")
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("## 🏆 Enrollment by Emirate")
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
                color="students", color_continuous_scale=[
                    "#EAF4EA", "#006400"],
                text="students",
                labels={"emirate": "Emirate", "students": "Students"},
            )
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                              marker_line_color="white", marker_line_width=1.5)
            fig.update_layout(
                height=480, plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family="Segoe UI", size=11),
                showlegend=False,
                xaxis=dict(showgrid=False, title="", tickfont=dict(size=11), tickangle=-45),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Students"),
                margin=dict(l=70, r=50, t=50, b=150),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            _export_buttons(df.rename(columns={"emirate": "Emirate", "students": "Students"}),
                            "home_emirate_enrollment")

    # ─────────────────────────────────────────────────────────────────────────
    # CHART 2: Schools by Emirate  (= India's "Top 20 States by Student Enrollment")
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("## 🏫 Schools by Emirate")
    if emirate_col and sch_cnt_col:
        sch_em_col = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
        if sch_em_col:
            sch_where, sch_params = _where_clause(filters, allowed_cols=sch_cols)
            df_sch = _q(
                f"SELECT {sch_em_col} AS emirate, SUM({sch_cnt_col}) AS schools "
                f"FROM uae.uae_fact_schools WHERE academic_year=%s{sch_where} "
                f"GROUP BY {sch_em_col} ORDER BY schools DESC",
                [UAE_YEAR] + sch_params
            )
            if not df_sch.empty:
                fig2 = px.bar(
                    df_sch, x="emirate", y="schools",
                    color="schools",
                    color_continuous_scale=["#FFF0F0", "#C8102E"],
                    text="schools",
                    labels={"emirate": "Emirate", "schools": "Schools"},
                )
                fig2.update_traces(texttemplate="%{text:,.0f}", textposition="outside",
                                   marker_line_color="white", marker_line_width=1.5)
                fig2.update_layout(
                    height=480, plot_bgcolor="white", paper_bgcolor="white",
                    font=dict(family="Segoe UI", size=11),
                    showlegend=False,
                    xaxis=dict(showgrid=False, title="", tickfont=dict(size=11), tickangle=-45),
                    yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Schools"),
                    margin=dict(l=70, r=50, t=50, b=150),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
                _export_buttons(df_sch.rename(columns={"emirate": "Emirate", "schools": "Schools"}),
                                "home_emirate_schools")

    # ─────────────────────────────────────────────────────────────────────────
    # CHART 3: Gender distribution donut
    # ─────────────────────────────────────────────────────────────────────────
    if gender_col and enr_cnt_col:
        st.markdown("## 👥 Student Gender Distribution")
        df_g = _q(
            f"SELECT {gender_col} AS gender, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {gender_col}",
            [UAE_YEAR] + params
        )
        if not df_g.empty:
            fig_g = px.pie(
                df_g, names="gender", values="students",
                color_discrete_sequence=["#006400", "#C8102E", "#FFD700"],
                hole=0.45, title="Gender Distribution (2024-25)"
            )
            fig_g.update_layout(height=300, margin=dict(t=40, b=20))
            g1, g2 = st.columns([1, 2])
            g1.plotly_chart(fig_g, use_container_width=True)
            g2.dataframe(
                df_g.rename(columns={"gender": "Gender", "students": "Students"})
                    .assign(Share=lambda d: (d["Students"] / d["Students"].sum() * 100).round(1).astype(str) + "%"),
                use_container_width=True
            )

    # ─────────────────────────────────────────────────────────────────────────
    # KEY INSIGHTS  (mirrors India's Key Insights section exactly)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("## 💡 Key Insights")
    ins1, ins2, ins3 = st.columns(3)
    with ins1:
        st.info(f"""
**📚 School Coverage**

UAE has **{_fmt(total_sch)}** schools serving
**{_fmt(total_enr)}** students across
**{em_count}** Emirates.
        """)
    with ins2:
        st.success(f"""
**👨‍🏫 Teaching Staff**

With **{_fmt(total_tch)}** teachers nationwide,
the national PTR stands at **{ptr_str}**,
reflecting the student-to-teacher ratio.
        """)
    with ins3:
        st.info(f"""
**🏫 School Size**

On average, each UAE school serves
**{sps_str}** students —
reflecting the scale of UAE's education institutions.
        """)

    # ─────────────────────────────────────────────────────────────────────────
    # EXPLORE MORE navigation cards (mirrors India exactly)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("## 🧭 Explore More")
    nav1, nav2 = st.columns(2)
    with nav1:
        st.markdown("""
<a href="/State_Dashboard?region=UAE" target="_blank" style="
    display:inline-block; width:100%; padding:1rem;
    background:linear-gradient(135deg,#006400 0%,#008000 100%);
    color:white!important; text-align:center; text-decoration:none!important;
    border-radius:8px; font-weight:700; font-size:1.1rem;
    box-shadow:0 4px 12px rgba(0,0,0,.2); border:3px solid #006400;
    transition:all 0.3s ease;">
    📊 Emirates Dashboard
</a>
""", unsafe_allow_html=True)
        st.markdown("""
<div style="padding:0.5rem;color:#757575;font-size:.9rem;">
Drill into emirate-level data with advanced filtering.
<ul style="margin-top:.5rem;">
    <li>Filter by emirate, curriculum, gender</li>
    <li>Compare across education types</li>
    <li>Export detailed reports</li>
</ul>
</div>
""", unsafe_allow_html=True)
    with nav2:
        st.markdown("""
<a href="/Analytics?region=UAE" target="_blank" style="
    display:inline-block; width:100%; padding:1rem;
    background:linear-gradient(135deg,#C8102E 0%,#990000 100%);
    color:white!important; text-align:center; text-decoration:none!important;
    border-radius:8px; font-weight:700; font-size:1.1rem;
    box-shadow:0 4px 12px rgba(0,0,0,.2); border:3px solid #C8102E;
    transition:all 0.3s ease;">
    📈 UAE Analytics
</a>
""", unsafe_allow_html=True)
        st.markdown("""
<div style="padding:0.5rem;color:#757575;font-size:.9rem;">
Interactive analytics with geographic maps and custom reports.
<ul style="margin-top:.5rem;">
    <li>Geographic distribution charts</li>
    <li>Comparative emirate analysis</li>
    <li>Custom report builder</li>
</ul>
</div>
""", unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:#757575;font-size:.85rem;'>"
        "<strong>TutorCloud Global Dashboard</strong> — UAE Education Data 2024-25 | "
        "© 2026 TutorCloud. All rights reserved.</div>",
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. STATE DASHBOARD (UAE = Emirates)  ── mirrors India State Dashboard
# ══════════════════════════════════════════════════════════════════════════════

def render_uae_state_dashboard():
    if _inject_css:
        _inject_css()
    st.markdown(UAE_CSS, unsafe_allow_html=True)

    st.markdown('<div class="main-header">📊 UAE State Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Comprehensive Emirate-Level Analysis — Academic Year 2024–2025</div>',
        unsafe_allow_html=True
    )

    filters = _build_sidebar_filters()

    # ── KPI overview row (mirrors India State Overview) ────────────────────────
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    sch_cols    = _tbl_cols("uae_fact_schools")
    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    gender_col  = _pick_col(enr_cols, "gender", "student_gender")

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols)
    where_sch, params_sch = _where_clause(filters, allowed_cols=sch_cols)
    where_tch, params_tch = _where_clause(filters, allowed_cols=tch_cols)

    # Compute KPIs
    total_enr = 0
    male_enr  = 0
    female_enr = 0
    if enr_cnt_col:
        df = _q(
            f"SELECT COALESCE(SUM({enr_cnt_col}),0) AS total "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr}",
            [UAE_YEAR] + params_enr
        )
        total_enr = int(df.iloc[0, 0]) if not df.empty else 0

        if gender_col:
            df_g = _q(
                f"SELECT {gender_col} AS g, SUM({enr_cnt_col}) AS cnt "
                f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr} "
                f"GROUP BY {gender_col}", [UAE_YEAR] + params_enr
            )
            if not df_g.empty:
                df_g.columns = ["g", "cnt"]
                male_enr   = int(df_g[df_g["g"].str.lower().str.startswith("m", na=False)]["cnt"].sum())
                female_enr = int(df_g[df_g["g"].str.lower().str.startswith("f", na=False)]["cnt"].sum())

    total_sch = 0
    if sch_cnt_col:
        df = _q(
            f"SELECT COALESCE(SUM({sch_cnt_col}),0) FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch}",
            [UAE_YEAR] + params_sch
        )
        total_sch = int(df.iloc[0, 0]) if not df.empty else 0

    total_tch = 0
    if tch_cnt_col:
        df = _q(
            f"SELECT COALESCE(SUM({tch_cnt_col}),0) FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where_tch}",
            [UAE_YEAR] + params_tch
        )
        total_tch = int(df.iloc[0, 0]) if not df.empty else 0

    ptr_str = _fmt_ptr(total_enr, total_tch)

    # Display KPI row
    st.markdown('<div class="section-header">📊 Overview — UAE 2024-25</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("🏫 Total Schools",   _fmt(total_sch))
    with k2: st.metric("🎓 Total Students",  _fmt(total_enr))
    with k3: st.metric("👨‍🏫 Total Teachers", _fmt(total_tch))
    with k4: st.metric("📊 National PTR",    ptr_str)

    k5, k6 = st.columns(2)
    with k5: st.metric("👦 Male Students",   _fmt(male_enr))
    with k6: st.metric("👧 Female Students", _fmt(female_enr))

    st.markdown("---")

    # ── 5 Tabs (matching India's tab structure) ────────────────────────────────
    tabs = st.tabs([
        "📊 Overview",
        "🏫 Schools",
        "👨‍🏫 Teachers",
        "📈 Performance",
        "🌍 Demographics",
    ])

    with tabs[0]:
        _uae_tab_overview(filters)
    with tabs[1]:
        _uae_tab_schools(filters)
    with tabs[2]:
        _uae_tab_teachers(filters)
    with tabs[3]:
        _uae_tab_performance(filters)
    with tabs[4]:
        _uae_tab_demographics(filters)


# ── Tab 1: Overview ────────────────────────────────────────────────────────────

def _uae_tab_overview(filters):
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    gender_col  = _pick_col(enr_cols, "gender", "student_gender")
    edu_col     = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type", "education_level")
    nat_col     = _pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality")

    where, params = _where_clause(filters, allowed_cols=enr_cols)

    # Emirate-wise enrollment bar
    st.markdown('<div class="uae-section-header">📊 Emirate-wise Enrollment</div>', unsafe_allow_html=True)
    if emirate_col and enr_cnt_col:
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col} ORDER BY students DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(df, x="emirate", y="students",
                         color="students", color_continuous_scale=["#EAF4EA", "#006400"],
                         text="students",
                         labels={"emirate": "Emirate", "students": "Students"})
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=360,
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(t=30, b=80))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "overview_emirate_enr")

    # Education-type stacked bar
    if edu_col and enr_cnt_col and emirate_col:
        st.markdown('<div class="uae-section-header">📚 Enrollment by Education Type per Emirate</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {emirate_col} AS emirate, {edu_col} AS edu_type, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col}, {edu_col} ORDER BY emirate, students DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(df, x="emirate", y="students", color="edu_type",
                         barmode="stack", color_discrete_sequence=CHART_PALETTE,
                         labels={"emirate": "Emirate", "students": "Students", "edu_type": "Education Type"})
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=380,
                              margin=dict(t=30, b=80))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "overview_edu_type")

    # Gender grouped bar by emirate
    if gender_col and enr_cnt_col and emirate_col:
        st.markdown('<div class="uae-section-header">👥 Gender Distribution by Emirate</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {emirate_col} AS emirate, {gender_col} AS gender, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col}, {gender_col} ORDER BY emirate",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(df, x="emirate", y="students", color="gender",
                         barmode="group", color_discrete_sequence=["#006400", "#C8102E"],
                         labels={"emirate": "Emirate", "students": "Students"})
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=360,
                              margin=dict(t=30, b=80))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "overview_gender_emirate")

    # Nationality pie
    if nat_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">🌍 Emirati vs Expatriate Students</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {nat_col} AS nationality, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where} "
            f"GROUP BY {nat_col} ORDER BY students DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            c1, c2 = st.columns(2)
            fig = px.pie(df, names="nationality", values="students", hole=0.4,
                         color_discrete_sequence=CHART_PALETTE)
            c1.plotly_chart(fig, use_container_width=True)
            c2.dataframe(
                df.rename(columns={"nationality": "Nationality", "students": "Students"})
                  .assign(Share=(df["students"] / df["students"].sum() * 100).round(1).astype(str) + "%"),
                use_container_width=True
            )
            _export_buttons(df, "overview_nationality")


# ── Tab 2: Schools ─────────────────────────────────────────────────────────────

def _uae_tab_schools(filters):
    sch_cols    = _tbl_cols("uae_fact_schools")
    emirate_col = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    curr_col    = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")
    gender_col  = _pick_col(sch_cols, "gender", "school_gender")
    level_col   = _pick_col(sch_cols, "school_level", "level", "education_level", "cycle")

    where, params = _where_clause(filters, allowed_cols=sch_cols)

    # Schools by emirate
    st.markdown('<div class="uae-section-header">🏫 School Count by Emirate</div>', unsafe_allow_html=True)
    if emirate_col and sch_cnt_col:
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col} ORDER BY schools DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(df, x="emirate", y="schools",
                         color="schools", color_continuous_scale=["#FFF0F0", "#C8102E"],
                         text="schools", labels={"emirate": "Emirate", "schools": "Schools"})
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340,
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(t=30, b=80))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "schools_emirate")

    # Schools by curriculum
    if curr_col and sch_cnt_col:
        st.markdown('<div class="uae-section-header">📖 Schools by Curriculum</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {curr_col} AS curriculum, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where} "
            f"GROUP BY {curr_col} ORDER BY schools DESC LIMIT 15",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(df, x="schools", y="curriculum", orientation="h",
                         color="schools", color_continuous_scale=["#EAF4EA", "#006400"],
                         labels={"curriculum": "Curriculum", "schools": "Schools"})
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(300, len(df) * 32),
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(l=180, t=30))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "schools_curriculum")

    # Schools by gender (pie)
    if gender_col and sch_cnt_col:
        st.markdown('<div class="uae-section-header">🚻 Schools by Gender Type</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {gender_col} AS gender, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where} "
            f"GROUP BY {gender_col}", [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.pie(df, names="gender", values="schools", hole=0.4,
                         color_discrete_sequence=["#006400", "#C8102E", "#FFD700"])
            c1, c2 = st.columns([1, 2])
            c1.plotly_chart(fig, use_container_width=True)
            c2.dataframe(df.rename(columns={"gender": "Gender", "schools": "Schools"}),
                         use_container_width=True)

    # Curriculum × Emirate heatmap
    if curr_col and emirate_col and sch_cnt_col:
        st.markdown('<div class="uae-section-header">🗂️ Curriculum × Emirate Matrix</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {emirate_col} AS emirate, {curr_col} AS curriculum, SUM({sch_cnt_col}) AS schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col}, {curr_col}",
            [UAE_YEAR] + params
        )
        if not df.empty:
            pivot = df.pivot_table(index="curriculum", columns="emirate",
                                   values="schools", aggfunc="sum", fill_value=0)
            fig = px.imshow(pivot, color_continuous_scale="Greens",
                            labels={"color": "Schools"},
                            title="Schools per Curriculum per Emirate")
            fig.update_layout(height=max(300, len(pivot) * 30))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "schools_heatmap")


# ── Tab 3: Teachers ────────────────────────────────────────────────────────────

def _uae_tab_teachers(filters):
    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")
    emirate_col = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    gender_col  = _pick_col(tch_cols, "gender", "teacher_gender")
    nat_col     = _pick_col(tch_cols, "nationality_cat", "nationality_category", "nationality")

    where, params = _where_clause(filters, allowed_cols=tch_cols)

    # Teachers by emirate
    st.markdown('<div class="uae-section-header">👨‍🏫 Teacher Count by Emirate</div>', unsafe_allow_html=True)
    if emirate_col and tch_cnt_col:
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({tch_cnt_col}) AS teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where} "
            f"GROUP BY {emirate_col} ORDER BY teachers DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(df, x="emirate", y="teachers",
                         color="teachers", color_continuous_scale=["#FFFACD", "#FFD700"],
                         text="teachers", labels={"emirate": "Emirate", "teachers": "Teachers"})
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340,
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(t=30, b=80))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "teachers_emirate")

    # PTR by emirate
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    enr_em_col  = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    if emirate_col and tch_cnt_col and enr_em_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">📐 Pupil-Teacher Ratio (PTR) by Emirate</div>', unsafe_allow_html=True)
        df_t = _q(f"SELECT {emirate_col} AS emirate, SUM({tch_cnt_col}) AS teachers "
                  f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s GROUP BY {emirate_col}",
                  [UAE_YEAR])
        df_e = _q(f"SELECT {enr_em_col} AS emirate, SUM({enr_cnt_col}) AS students "
                  f"FROM uae.uae_fact_enrollment WHERE academic_year=%s GROUP BY {enr_em_col}",
                  [UAE_YEAR])
        if not df_t.empty and not df_e.empty:
            df_ptr = df_e.merge(df_t, on="emirate", how="inner")
            df_ptr["PTR"] = (df_ptr["students"] / df_ptr["teachers"]).apply(
                lambda x: int(round(x)) if pd.notna(x) and x > 0 else 0)
            df_ptr = df_ptr.sort_values("PTR", ascending=False)
            fig = px.bar(df_ptr, x="PTR", y="emirate", orientation="h",
                         color="PTR", color_continuous_scale="RdYlGn_r",
                         labels={"emirate": "Emirate", "PTR": "Students per Teacher"},
                         text="PTR")
            fig.update_traces(texttemplate="%{text:d}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340,
                              margin=dict(l=120, t=30))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df_ptr[["emirate", "students", "teachers", "PTR"]], "ptr_emirate")

    # Teacher gender split
    if gender_col and tch_cnt_col:
        st.markdown('<div class="uae-section-header">🚻 Teacher Gender Distribution</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {gender_col} AS gender, SUM({tch_cnt_col}) AS teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where} "
            f"GROUP BY {gender_col}", [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.pie(df, names="gender", values="teachers", hole=0.4,
                         color_discrete_sequence=["#006400", "#C8102E"])
            c1, c2 = st.columns(2)
            c1.plotly_chart(fig, use_container_width=True)
            c2.dataframe(df.rename(columns={"gender": "Gender", "teachers": "Teachers"}),
                         use_container_width=True)

    # Teacher nationality
    if nat_col and tch_cnt_col:
        st.markdown('<div class="uae-section-header">🌍 Teacher Nationality Distribution</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {nat_col} AS nationality, SUM({tch_cnt_col}) AS teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where} "
            f"GROUP BY {nat_col} ORDER BY teachers DESC",
            [UAE_YEAR] + params
        )
        if not df.empty:
            fig = px.bar(df, x="teachers", y="nationality", orientation="h",
                         color="teachers", color_continuous_scale=["#EAF4EA", "#006400"],
                         labels={"nationality": "Nationality", "teachers": "Teachers"})
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(300, len(df) * 32),
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(l=160, t=30))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "teachers_nationality")


# ── Tab 4: Performance ─────────────────────────────────────────────────────────

def _uae_tab_performance(filters):
    pf_cols     = _tbl_cols("uae_fact_pass_fail")
    emirate_col = _pick_col(pf_cols, "region_en", "emirate", "emirate_en", "region")
    cycle_col   = _pick_col(pf_cols, "cycle", "education_cycle", "grade_level")
    pass_col    = _pick_col(pf_cols, "pass_count", "passed", "pass_students")
    fail_col    = _pick_col(pf_cols, "fail_count", "failed", "fail_students")
    pass_pct    = _pick_col(pf_cols, "pass_rate", "pass_percentage", "pct_pass")

    sc_cols      = _tbl_cols("uae_fact_student_scores")
    subj_col_sc  = _pick_col(sc_cols, "subject", "subject_en", "subject_name")
    avg_col      = _pick_col(sc_cols, "avg_score", "average_score", "mean_score", "score")
    em_sc_col    = _pick_col(sc_cols, "region_en", "emirate", "emirate_en", "region")

    where_pf, params_pf = _where_clause(filters, allowed_cols=pf_cols)
    where_sc, params_sc = _where_clause(filters, allowed_cols=sc_cols)

    # Pass/Fail by emirate
    st.markdown('<div class="uae-section-header">📊 Pass / Fail by Emirate</div>', unsafe_allow_html=True)
    if emirate_col and (pass_col or pass_pct):
        agg_expr = (f"SUM({pass_col}) AS passed, SUM({fail_col}) AS failed"
                    if pass_col and fail_col
                    else f"AVG({pass_pct}) AS pass_rate")
        df = _q(
            f"SELECT {emirate_col} AS emirate, {agg_expr} "
            f"FROM uae.uae_fact_pass_fail WHERE academic_year=%s{where_pf} "
            f"GROUP BY {emirate_col} ORDER BY emirate",
            [UAE_YEAR] + params_pf
        )
        if not df.empty:
            if "passed" in df.columns:
                df_m = df.melt("emirate", value_vars=["passed", "failed"],
                               var_name="result", value_name="students")
                fig = px.bar(df_m, x="emirate", y="students", color="result",
                             barmode="stack",
                             color_discrete_sequence=["#006400", "#C8102E"],
                             labels={"emirate": "Emirate", "students": "Students", "result": "Result"})
            else:
                fig = px.bar(df, x="emirate", y="pass_rate",
                             color="pass_rate", color_continuous_scale="Greens",
                             text="pass_rate",
                             labels={"emirate": "Emirate", "pass_rate": "Pass Rate (%)"})
                fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=360,
                              margin=dict(t=30, b=80))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "pass_fail_emirate")

    # Pass/Fail by cycle
    if cycle_col and (pass_col or pass_pct):
        st.markdown('<div class="uae-section-header">🎓 Pass / Fail by Education Cycle</div>', unsafe_allow_html=True)
        agg_expr = (f"SUM({pass_col}) AS passed, SUM({fail_col}) AS failed"
                    if pass_col and fail_col
                    else f"AVG({pass_pct}) AS pass_rate")
        df = _q(
            f"SELECT {cycle_col} AS cycle, {agg_expr} "
            f"FROM uae.uae_fact_pass_fail WHERE academic_year=%s{where_pf} "
            f"GROUP BY {cycle_col} ORDER BY {cycle_col}",
            [UAE_YEAR] + params_pf
        )
        if not df.empty:
            if "passed" in df.columns:
                df_m = df.melt("cycle", value_vars=["passed", "failed"],
                               var_name="result", value_name="students")
                fig = px.bar(df_m, x="cycle", y="students", color="result",
                             barmode="group",
                             color_discrete_sequence=["#006400", "#C8102E"])
            else:
                fig = px.bar(df, x="cycle", y="pass_rate",
                             color_discrete_sequence=["#1E90FF"])
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340,
                              margin=dict(t=30, b=60))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "pass_fail_cycle")

    # Pass rate heatmap (cycle × emirate)
    if emirate_col and cycle_col and (pass_pct or pass_col):
        st.markdown('<div class="uae-section-header">🗂️ Pass Rate Heatmap (Emirate × Cycle)</div>', unsafe_allow_html=True)
        rate_expr = (f"ROUND(SUM({pass_col})*100.0/NULLIF(SUM({pass_col})+SUM({fail_col}),0),1)"
                     if pass_col and fail_col
                     else f"AVG({pass_pct})")
        df = _q(
            f"SELECT {emirate_col} AS emirate, {cycle_col} AS cycle, {rate_expr} AS rate "
            f"FROM uae.uae_fact_pass_fail WHERE academic_year=%s{where_pf} "
            f"GROUP BY {emirate_col}, {cycle_col}",
            [UAE_YEAR] + params_pf
        )
        if not df.empty:
            try:
                pivot = df.pivot_table(index="cycle", columns="emirate", values="rate",
                                       aggfunc="mean", fill_value=0)
                fig = px.imshow(pivot, color_continuous_scale="RdYlGn",
                                labels={"color": "Pass Rate (%)"},
                                zmin=0, zmax=100)
                fig.update_layout(height=max(300, len(pivot) * 35))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

    # Average scores by subject
    if subj_col_sc and avg_col:
        st.markdown('<div class="uae-section-header">📖 Average Scores by Subject</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {subj_col_sc} AS subject, AVG({avg_col}) AS avg_score "
            f"FROM uae.uae_fact_student_scores WHERE academic_year=%s{where_sc} "
            f"GROUP BY {subj_col_sc} ORDER BY avg_score DESC",
            [UAE_YEAR] + params_sc
        )
        if not df.empty:
            df["avg_score"] = df["avg_score"].round(1)
            fig = px.bar(df, x="avg_score", y="subject", orientation="h",
                         color="avg_score", color_continuous_scale="Greens",
                         text="avg_score",
                         labels={"subject": "Subject", "avg_score": "Avg Score"})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(300, len(df) * 32),
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(l=160, t=30))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "avg_scores_subject")

    # Average scores by emirate
    if em_sc_col and avg_col:
        st.markdown('<div class="uae-section-header">🏙️ Average Scores by Emirate</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {em_sc_col} AS emirate, AVG({avg_col}) AS avg_score "
            f"FROM uae.uae_fact_student_scores WHERE academic_year=%s{where_sc} "
            f"GROUP BY {em_sc_col} ORDER BY avg_score DESC",
            [UAE_YEAR] + params_sc
        )
        if not df.empty:
            df["avg_score"] = df["avg_score"].round(1)
            fig = px.bar(df, x="emirate", y="avg_score",
                         color="avg_score", color_continuous_scale=["#FFFACD", "#FFD700"],
                         text="avg_score",
                         labels={"emirate": "Emirate", "avg_score": "Avg Score"})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340,
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(t=30, b=80))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "avg_scores_emirate")


# ── Tab 5: Demographics ────────────────────────────────────────────────────────

def _uae_tab_demographics(filters):
    nat_cols    = _tbl_cols("uae_fact_student_nationalities")
    nat_col     = _pick_col(nat_cols, "nationality", "nationality_en", "country", "country_en")
    cnt_col     = _pick_col(nat_cols, "student_count", "count", "students")
    emirate_col_nat = _pick_col(nat_cols, "region_en", "emirate", "emirate_en", "region")

    enr_cols     = _tbl_cols("uae_fact_enrollment")
    enr_em_col   = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col  = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    nat_cat_col  = _pick_col(enr_cols, "nationality_cat", "nationality_category")

    where_nat, params_nat = _where_clause(filters, allowed_cols=nat_cols)
    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols)

    # Top 20 nationalities horizontal bar
    st.markdown('<div class="uae-section-header">🏅 Top 20 Student Nationalities in UAE Schools</div>', unsafe_allow_html=True)
    if nat_col and cnt_col:
        df = _q(
            f"SELECT {nat_col} AS nationality, SUM({cnt_col}) AS students "
            f"FROM uae.uae_fact_student_nationalities WHERE academic_year=%s{where_nat} "
            f"GROUP BY {nat_col} ORDER BY students DESC LIMIT 20",
            [UAE_YEAR] + params_nat
        )
        if not df.empty:
            fig = px.bar(df, x="students", y="nationality", orientation="h",
                         color="students", color_continuous_scale="Greens",
                         text="students",
                         labels={"nationality": "Nationality", "students": "Students"})
            fig.update_traces(texttemplate="%{text:,}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(400, len(df) * 26),
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(l=160, t=30))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "top_nationalities")

    # Nationality treemap
    if nat_col and cnt_col:
        st.markdown('<div class="uae-section-header">🌳 Student Nationality Diversity (Treemap)</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {nat_col} AS nationality, SUM({cnt_col}) AS students "
            f"FROM uae.uae_fact_student_nationalities WHERE academic_year=%s{where_nat} "
            f"GROUP BY {nat_col} ORDER BY students DESC LIMIT 30",
            [UAE_YEAR] + params_nat
        )
        if not df.empty:
            fig = px.treemap(df, path=["nationality"], values="students",
                             color="students", color_continuous_scale="Greens")
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

    # Nationality by emirate stacked bar
    if emirate_col_nat and nat_col and cnt_col:
        st.markdown('<div class="uae-section-header">🗺️ Top Nationalities by Emirate</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {emirate_col_nat} AS emirate, {nat_col} AS nationality, SUM({cnt_col}) AS students "
            f"FROM uae.uae_fact_student_nationalities WHERE academic_year=%s{where_nat} "
            f"GROUP BY {emirate_col_nat}, {nat_col} ORDER BY emirate, students DESC",
            [UAE_YEAR] + params_nat
        )
        if not df.empty:
            # Keep only top 8 nationalities to avoid clutter
            top_nats = df.groupby("nationality")["students"].sum().nlargest(8).index.tolist()
            df_filt = df[df["nationality"].isin(top_nats)].copy()
            if not df_filt.empty:
                fig = px.bar(df_filt, x="emirate", y="students", color="nationality",
                             barmode="stack", color_discrete_sequence=CHART_PALETTE,
                             labels={"emirate": "Emirate", "students": "Students"})
                fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=400,
                                  margin=dict(t=30, b=80))
                st.plotly_chart(fig, use_container_width=True)

    # Emirati vs Expat from enrollment
    if nat_cat_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">🇦🇪 Emirati vs Expatriate Split (Enrollment)</div>', unsafe_allow_html=True)
        df = _q(
            f"SELECT {nat_cat_col} AS nationality_cat, SUM({enr_cnt_col}) AS students "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr} "
            f"GROUP BY {nat_cat_col} ORDER BY students DESC",
            [UAE_YEAR] + params_enr
        )
        if not df.empty:
            c1, c2 = st.columns([1, 2])
            fig = px.pie(df, names="nationality_cat", values="students", hole=0.45,
                         color_discrete_sequence=["#006400", "#C8102E", "#FFD700", "#1E90FF"])
            c1.plotly_chart(fig, use_container_width=True)
            c2.dataframe(
                df.rename(columns={"nationality_cat": "Category", "students": "Students"})
                  .assign(Share=(df["students"] / df["students"].sum() * 100).round(1).astype(str) + "%"),
                use_container_width=True
            )
            _export_buttons(df, "demographics_nat_cat")


# ══════════════════════════════════════════════════════════════════════════════
# 3. ANALYTICS PAGE  ── mirrors India Analytics page exactly
# ══════════════════════════════════════════════════════════════════════════════

def render_uae_analytics():
    if _inject_css:
        _inject_css()
    st.markdown(UAE_CSS, unsafe_allow_html=True)

    st.markdown('<div class="main-header">📈 UAE Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Interactive Analytics — Academic Year 2024–2025</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="uae-flag-banner">🇦🇪 UAE Analytics — Academic Year 2024–2025</div>',
        unsafe_allow_html=True
    )

    # No sidebar filters on Analytics page (matches India Analytics)
    filters = {}  # empty – filters are inline per tab, not sidebar

    tabs = st.tabs([
        "🗺️ Geographic Maps",
        "🎯 Performance Metrics",
        "🔍 Comparative Analysis",
        "📝 Custom Reports",
    ])

    with tabs[0]:
        _uae_analytics_geo(filters)
    with tabs[1]:
        _uae_analytics_perf(filters)
    with tabs[2]:
        _uae_analytics_compare(filters)
    with tabs[3]:
        _uae_analytics_custom(filters)


# ── Analytics Tab 1: Geographic Analysis (mirrors India "Geographic Maps") ─────

def _uae_analytics_geo(filters):
    st.markdown('<div class="uae-section-header">🗺️ Geographic Distribution</div>', unsafe_allow_html=True)

    enr_cols    = _tbl_cols("uae_fact_enrollment")
    sch_cols    = _tbl_cols("uae_fact_schools")
    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    sch_em_col  = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    tch_em_col  = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols)
    where_sch, params_sch = _where_clause(filters, allowed_cols=sch_cols)
    where_tch, params_tch = _where_clause(filters, allowed_cols=tch_cols)

    # Metric selector (same as India)
    metric_choice = st.selectbox(
        "📊 Select Metric to Visualize",
        ["PTR (Pupil-Teacher Ratio)", "Students per School", "Total Students", "Total Schools"],
        key="uae_geo_metric"
    )

    if metric_choice == "Total Students" and emirate_col and enr_cnt_col:
        df = _q(
            f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS value "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr} "
            f"GROUP BY {emirate_col} ORDER BY value DESC",
            [UAE_YEAR] + params_enr
        )
        y_label = "Total Students"

    elif metric_choice == "Total Schools" and sch_em_col and sch_cnt_col:
        df = _q(
            f"SELECT {sch_em_col} AS emirate, SUM({sch_cnt_col}) AS value "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch} "
            f"GROUP BY {sch_em_col} ORDER BY value DESC",
            [UAE_YEAR] + params_sch
        )
        y_label = "Total Schools"

    elif metric_choice == "Total Teachers" and tch_em_col and tch_cnt_col:
        df = _q(
            f"SELECT {tch_em_col} AS emirate, SUM({tch_cnt_col}) AS value "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where_tch} "
            f"GROUP BY {tch_em_col} ORDER BY value DESC",
            [UAE_YEAR] + params_tch
        )
        y_label = "Total Teachers"

    elif metric_choice == "Students per School" and emirate_col and enr_cnt_col and sch_em_col and sch_cnt_col:
        df_e2 = _q(
            f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS total_enr "
            f"FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr} "
            f"GROUP BY {emirate_col}",
            [UAE_YEAR] + params_enr
        )
        df_s2 = _q(
            f"SELECT {sch_em_col} AS emirate, SUM({sch_cnt_col}) AS total_sch "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch} "
            f"GROUP BY {sch_em_col}",
            [UAE_YEAR] + params_sch
        )
        if not df_e2.empty and not df_s2.empty:
            df = df_e2.merge(df_s2, on="emirate")
            df["value"] = (df["total_enr"] / df["total_sch"]).apply(
                lambda x: int(round(x)) if pd.notna(x) and x > 0 else 0)
            df = df[["emirate", "value"]].sort_values("value", ascending=False)
        else:
            df = pd.DataFrame()
        y_label = "Students per School"

    elif metric_choice == "PTR (Pupil-Teacher Ratio)":
        df_t = _q(f"SELECT {_pick_col(tch_cols,'region_en','emirate','emirate_en','region')} AS emirate, "
                  f"SUM({tch_cnt_col}) AS teachers "
                  f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s GROUP BY 1", [UAE_YEAR])
        df_e = _q(f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS students "
                  f"FROM uae.uae_fact_enrollment WHERE academic_year=%s GROUP BY 1", [UAE_YEAR])
        if not df_t.empty and not df_e.empty:
            df = df_e.merge(df_t, on="emirate")
            df["value"] = (df["students"] / df["teachers"]).apply(
                lambda x: int(round(x)) if pd.notna(x) and x > 0 else 0)
            df = df[["emirate", "value"]].sort_values("value", ascending=False)
        else:
            df = pd.DataFrame()
        y_label = "PTR (Students per Teacher)"
    else:
        df = pd.DataFrame()
        y_label = metric_choice

    if not df.empty if isinstance(df, pd.DataFrame) else False:
        color_scale = "RdYlGn_r" if "PTR" in metric_choice else "Viridis"
        fig = px.bar(
            df, x="emirate", y="value",
            color="value", color_continuous_scale=color_scale,
            text="value",
            labels={"emirate": "Emirate", "value": y_label}
        )
        fig.update_traces(
            texttemplate="%{text:d}" if "PTR" in metric_choice else "%{text:,.0f}",
            textposition="outside"
        )
        fig.update_layout(
            height=480, plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False, coloraxis_showscale=False,
            font=dict(family="Segoe UI", size=11),
            margin=dict(l=60, r=350, t=80, b=120),
            xaxis=dict(tickfont=dict(size=11), tickangle=-45),
            yaxis=dict(title=y_label)
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown("### 📋 Raw Data Table")
        st.dataframe(
            df.rename(columns={"emirate": "Emirate", "value": y_label}),
            use_container_width=True
        )
        _export_buttons(df.rename(columns={"emirate": "Emirate", "value": y_label}), "geo_analysis")


# ── Analytics Tab 2: Performance Analytics (mirrors India "Performance Metrics") ─

def _uae_analytics_perf(filters):
    st.markdown('<div class="uae-section-header">🎯 Performance Metrics</div>', unsafe_allow_html=True)

    enr_cols    = _tbl_cols("uae_fact_enrollment")
    sch_cols    = _tbl_cols("uae_fact_schools")
    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")
    sc_cols     = _tbl_cols("uae_fact_student_scores")
    pf_cols     = _tbl_cols("uae_fact_pass_fail")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    avg_col     = _pick_col(sc_cols, "avg_score", "average_score", "mean_score", "score")
    subj_col    = _pick_col(sc_cols, "subject", "subject_en", "subject_name")
    pass_col    = _pick_col(pf_cols, "pass_count", "passed", "pass_students")
    fail_col    = _pick_col(pf_cols, "fail_count", "failed", "fail_students")
    pass_pct    = _pick_col(pf_cols, "pass_rate", "pass_percentage", "pct_pass")

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols)
    where_sch, params_sch = _where_clause(filters, allowed_cols=sch_cols)
    where_tch, params_tch = _where_clause(filters, allowed_cols=tch_cols)

    # State selector (Emirate filter for performance drill-down)
    emirate_list = _distinct("uae_fact_enrollment", emirate_col) if emirate_col else []
    sel_emirate = st.selectbox("🏙️ Select Emirate (or All)",
                               ["All"] + emirate_list, key="uae_perf_emirate")

    # KPI cards (mirrors India's 6 KPI cards in Performance tab)
    total_enr = total_sch = total_tch = 0
    ptr = sps = tps = None

    q_where = f" AND {emirate_col} = %s" if sel_emirate != "All" and emirate_col else ""
    q_params_enr = ([UAE_YEAR] + params_enr + ([sel_emirate] if q_where else []))
    q_params_sch = ([UAE_YEAR] + params_sch + ([sel_emirate] if q_where else []))
    q_params_tch = ([UAE_YEAR] + params_tch + ([sel_emirate] if q_where else []))

    if enr_cnt_col:
        df = _q(f"SELECT COALESCE(SUM({enr_cnt_col}),0) FROM uae.uae_fact_enrollment "
                f"WHERE academic_year=%s{where_enr}{q_where}", q_params_enr)
        total_enr = int(df.iloc[0, 0]) if not df.empty else 0
    if sch_cnt_col:
        df = _q(f"SELECT COALESCE(SUM({sch_cnt_col}),0) FROM uae.uae_fact_schools "
                f"WHERE academic_year=%s{where_sch}{q_where}", q_params_sch)
        total_sch = int(df.iloc[0, 0]) if not df.empty else 0
    tch_em_col = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    if tch_cnt_col:
        df = _q(f"SELECT COALESCE(SUM({tch_cnt_col}),0) FROM uae.uae_fact_teachers_emirate "
                f"WHERE academic_year=%s{where_tch}{q_where}", q_params_tch)
        total_tch = int(df.iloc[0, 0]) if not df.empty else 0

    if total_tch > 0:
        ptr = int(round(total_enr / total_tch))
    if total_sch > 0:
        sps = int(round(total_enr / total_sch))
    if total_sch > 0 and total_tch > 0:
        tps = round(total_tch / total_sch, 2)

    st.markdown('<div class="section-header">📊 Key Metrics</div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    with k1: st.metric("🏫 Total Schools",   _fmt(total_sch))
    with k2: st.metric("🎓 Total Students",  _fmt(total_enr))
    with k3: st.metric("👨‍🏫 Total Teachers", _fmt(total_tch))

    k4, k5, k6 = st.columns(3)
    ptr_color = "normal" if ptr and ptr < 30 else "inverse"
    with k4: st.metric("📐 PTR", f"{ptr}:1" if ptr else "N/A", delta_color=ptr_color)
    with k5: st.metric("📚 Students/School",        _fmt(sps) if sps else "N/A")
    with k6: st.metric("🏫 Teachers/School",        f"{tps:.2f}" if tps else "N/A")

    # Avg scores by subject bar
    if subj_col and avg_col:
        st.markdown('<div class="uae-section-header">📖 Average Score by Subject</div>', unsafe_allow_html=True)
        where_sc, params_sc = _where_clause(filters, allowed_cols=sc_cols)
        em_sc_col = _pick_col(sc_cols, "region_en", "emirate", "emirate_en", "region")
        q_where_sc = f" AND {em_sc_col} = %s" if sel_emirate != "All" and em_sc_col else ""
        df = _q(
            f"SELECT {subj_col} AS subject, AVG({avg_col}) AS avg_score "
            f"FROM uae.uae_fact_student_scores WHERE academic_year=%s{where_sc}{q_where_sc} "
            f"GROUP BY {subj_col} ORDER BY avg_score DESC",
            [UAE_YEAR] + params_sc + ([sel_emirate] if q_where_sc else [])
        )
        if not df.empty:
            df["avg_score"] = df["avg_score"].round(1)
            fig = px.bar(df, x="avg_score", y="subject", orientation="h",
                         color="avg_score", color_continuous_scale="Greens",
                         text="avg_score", labels={"subject": "Subject", "avg_score": "Avg Score"})
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(300, len(df) * 32),
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(l=160, t=30))
            st.plotly_chart(fig, use_container_width=True)
            _export_buttons(df, "perf_scores_subject")

    # Pass rate summary
    if pass_col or pass_pct:
        st.markdown('<div class="uae-section-header">✅ Pass Rate Summary</div>', unsafe_allow_html=True)
        pf_em_col = _pick_col(pf_cols, "region_en", "emirate", "emirate_en", "region")
        where_pf, params_pf = _where_clause(filters, allowed_cols=pf_cols)
        q_where_pf = f" AND {pf_em_col} = %s" if sel_emirate != "All" and pf_em_col else ""
        rate_expr = (f"ROUND(SUM({pass_col})*100.0/NULLIF(SUM({pass_col})+SUM({fail_col}),0),1)"
                     if pass_col and fail_col else f"AVG({pass_pct})")
        df = _q(
            f"SELECT ROUND({rate_expr}::numeric,1) AS pass_rate "
            f"FROM uae.uae_fact_pass_fail WHERE academic_year=%s{where_pf}{q_where_pf}",
            [UAE_YEAR] + params_pf + ([sel_emirate] if q_where_pf else [])
        )
        if not df.empty and not df.iloc[0, 0] is None:
            rate = float(df.iloc[0, 0])
            st.metric("🏆 Overall Pass Rate", f"{rate:.1f}%")


# ── Analytics Tab 3: Comparative Analysis (mirrors India "Comparative Analysis") ─

def _uae_analytics_compare(filters):
    st.markdown('<div class="uae-section-header">🔍 Emirate Comparison</div>', unsafe_allow_html=True)

    enr_cols    = _tbl_cols("uae_fact_enrollment")
    sch_cols    = _tbl_cols("uae_fact_schools")
    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")
    sc_cols     = _tbl_cols("uae_fact_student_scores")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    avg_col     = _pick_col(sc_cols, "avg_score", "average_score", "mean_score", "score")
    sch_em_col  = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    tch_em_col  = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    sc_em_col   = _pick_col(sc_cols, "region_en", "emirate", "emirate_en", "region")

    emirate_list = _distinct("uae_fact_enrollment", emirate_col) if emirate_col else []

    if len(emirate_list) < 2:
        st.info("ℹ️ At least 2 emirates required for comparison.")
        return

    cmp1, cmp2 = st.columns(2)
    with cmp1:
        sel_a = st.selectbox("🏙️ Emirate A", emirate_list, key="uae_cmp_a")
    with cmp2:
        default_b = emirate_list[1] if len(emirate_list) > 1 else emirate_list[0]
        sel_b = st.selectbox("🏙️ Emirate B",
                             [e for e in emirate_list if e != sel_a] or emirate_list,
                             key="uae_cmp_b")

    def _get_metrics(emirate):
        enr = sch = tch = avg_sc = 0
        if enr_cnt_col and emirate_col:
            df = _q(f"SELECT COALESCE(SUM({enr_cnt_col}),0) FROM uae.uae_fact_enrollment "
                    f"WHERE academic_year=%s AND {emirate_col}=%s", [UAE_YEAR, emirate])
            enr = int(df.iloc[0, 0]) if not df.empty else 0
        if sch_cnt_col and sch_em_col:
            df = _q(f"SELECT COALESCE(SUM({sch_cnt_col}),0) FROM uae.uae_fact_schools "
                    f"WHERE academic_year=%s AND {sch_em_col}=%s", [UAE_YEAR, emirate])
            sch = int(df.iloc[0, 0]) if not df.empty else 0
        if tch_cnt_col and tch_em_col:
            df = _q(f"SELECT COALESCE(SUM({tch_cnt_col}),0) FROM uae.uae_fact_teachers_emirate "
                    f"WHERE academic_year=%s AND {tch_em_col}=%s", [UAE_YEAR, emirate])
            tch = int(df.iloc[0, 0]) if not df.empty else 0
        if avg_col and sc_em_col:
            df = _q(f"SELECT AVG({avg_col}) FROM uae.uae_fact_student_scores "
                    f"WHERE academic_year=%s AND {sc_em_col}=%s", [UAE_YEAR, emirate])
            avg_sc = round(float(df.iloc[0, 0]), 1) if not df.empty and df.iloc[0, 0] else 0
        ptr = int(round(enr / tch)) if tch > 0 else None
        sps = int(round(enr / sch)) if sch > 0 else None
        return {"Total Students": enr, "Total Schools": sch, "Total Teachers": tch,
                "PTR": ptr, "Students/School": sps}

    m_a = _get_metrics(sel_a)
    m_b = _get_metrics(sel_b)

    # Side-by-side comparison table
    rows = []
    for k in m_a:
        va = m_a[k]; vb = m_b[k]
        if va is None and vb is None:
            continue
        def _fmt_cell(k, v):
            if v is None:
                return "N/A"
            if k == "PTR":
                try: return f"{int(round(float(v)))}:1"
                except: return "N/A"
            if k == "Students/School":
                try: return _fmt(int(round(float(v))))
                except: return "N/A"
            if isinstance(v, (int, float)):
                return _fmt(int(v))
            return str(v)
        rows.append({"Metric": k, sel_a: _fmt_cell(k, va), sel_b: _fmt_cell(k, vb)})

    if rows:
        df_cmp = pd.DataFrame(rows)
        st.dataframe(df_cmp, use_container_width=True)
        _export_buttons(df_cmp, "comparison")

    # Bar chart comparison (numeric metrics only)
    numeric_keys = [k for k in m_a if isinstance(m_a[k], (int, float)) and m_a[k] is not None
                    and k not in ("PTR", "Students/School")]
    if numeric_keys:
        st.markdown('<div class="uae-section-header">📊 Side-by-Side Comparison</div>', unsafe_allow_html=True)
        df_bar = pd.DataFrame({
            "Metric": numeric_keys * 2,
            "Emirate": [sel_a] * len(numeric_keys) + [sel_b] * len(numeric_keys),
            "Value": [m_a[k] for k in numeric_keys] + [m_b[k] for k in numeric_keys],
        })
        fig = px.bar(df_bar, x="Metric", y="Value", color="Emirate",
                     barmode="group", color_discrete_sequence=["#006400", "#C8102E"],
                     text="Value")
        fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=380,
                          margin=dict(t=30, b=60))
        st.plotly_chart(fig, use_container_width=True)


# ── Analytics Tab 4: Custom Report (mirrors India "Custom Reports") ─────────────

def _uae_analytics_custom(filters):
    st.markdown('<div class="uae-section-header">📝 Custom Report Builder</div>', unsafe_allow_html=True)

    enr_cols = _tbl_cols("uae_fact_enrollment")
    sch_cols = _tbl_cols("uae_fact_schools")
    tch_cols = _tbl_cols("uae_fact_teachers_emirate")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    edu_col     = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type")
    gender_col  = _pick_col(enr_cols, "gender", "student_gender")
    nat_col     = _pick_col(enr_cols, "nationality_cat", "nationality_category")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    curr_col    = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")

    # Available dimensions
    dim_options = {}
    if emirate_col: dim_options["Emirate"] = ("uae_fact_enrollment", emirate_col)
    if edu_col:     dim_options["Education Type"] = ("uae_fact_enrollment", edu_col)
    if gender_col:  dim_options["Gender"] = ("uae_fact_enrollment", gender_col)
    if nat_col:     dim_options["Nationality Category"] = ("uae_fact_enrollment", nat_col)
    if curr_col:    dim_options["Curriculum"] = ("uae_fact_schools", curr_col)

    # Available metrics
    metric_options = {}
    if enr_cnt_col: metric_options["Total Students"] = ("uae_fact_enrollment", enr_cnt_col)
    if sch_cnt_col: metric_options["Total Schools"] = ("uae_fact_schools", sch_cnt_col)
    if tch_cnt_col: metric_options["Total Teachers"] = ("uae_fact_teachers_emirate", tch_cnt_col)
    if enr_cnt_col and tch_cnt_col: metric_options["PTR"] = ("computed", None)  # derived metric

    c1, c2 = st.columns(2)
    with c1:
        sel_dims = st.multiselect(
            "📐 Group By (Dimensions)",
            options=list(dim_options.keys()),
            default=["Emirate"] if "Emirate" in dim_options else [],
            key="uae_custom_dims"
        )
    with c2:
        sel_metrics = st.multiselect(
            "📊 Metrics to Include",
            options=list(metric_options.keys()),
            default=list(metric_options.keys())[:2],
            key="uae_custom_metrics"
        )

    if not sel_dims or not sel_metrics:
        st.info("ℹ️ Select at least one dimension and one metric to build your report.")
        return

    # Build query for enrollment-based dimensions
    enr_dims = [dim_options[d] for d in sel_dims if dim_options[d][0] == "uae_fact_enrollment"]

    if not enr_dims:
        st.warning("Select an enrollment-based dimension (Emirate, Education Type, Gender, Nationality).")
        return

    dim_cols = [f"{col} AS {label.lower().replace(' ', '_')}"
                for label, (_, col) in
                [(d, dim_options[d]) for d in sel_dims if dim_options[d][0] == "uae_fact_enrollment"]]
    group_cols = [col for _, col in enr_dims]

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols)

    select_parts = dim_cols.copy()
    need_students = ("Total Students" in sel_metrics or "PTR" in sel_metrics) and enr_cnt_col
    need_teachers = ("Total Teachers" in sel_metrics or "PTR" in sel_metrics) and tch_cnt_col
    need_schools  = "Total Schools" in sel_metrics and sch_cnt_col

    if need_students:
        select_parts.append(f"SUM({enr_cnt_col}) AS total_students")

    query = (
        f"SELECT {', '.join(select_parts)} "
        f"FROM uae.uae_fact_enrollment "
        f"WHERE academic_year=%s{where_enr} "
        f"GROUP BY {', '.join(group_cols)} "
        f"ORDER BY {group_cols[0]}"
    )
    df = _q(query, [UAE_YEAR] + params_enr)

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    # Merge Schools data if needed
    sch_em_col2 = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    if need_schools and sch_em_col2:
        where_sch2, params_sch2 = _where_clause(filters, allowed_cols=sch_cols)
        df_smerge = _q(
            f"SELECT {sch_em_col2} AS __dim__, SUM({sch_cnt_col}) AS total_schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch2} "
            f"GROUP BY {sch_em_col2}",
            [UAE_YEAR] + params_sch2
        )
        if not df_smerge.empty:
            df_smerge = df_smerge.rename(columns={"__dim__": group_cols[0]})
            df = df.merge(df_smerge, on=group_cols[0], how="left")

    # Merge Teachers data if needed (Total Teachers or PTR)
    tch_em_col2 = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    if need_teachers and tch_em_col2:
        where_tch2, params_tch2 = _where_clause(filters, allowed_cols=tch_cols)
        df_tmerge = _q(
            f"SELECT {tch_em_col2} AS __dim__, SUM({tch_cnt_col}) AS total_teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where_tch2} "
            f"GROUP BY {tch_em_col2}",
            [UAE_YEAR] + params_tch2
        )
        if not df_tmerge.empty:
            df_tmerge = df_tmerge.rename(columns={"__dim__": group_cols[0]})
            df = df.merge(df_tmerge, on=group_cols[0], how="left")

    # Compute PTR if requested
    if "PTR" in sel_metrics and "total_students" in df.columns and "total_teachers" in df.columns:
        df["ptr"] = df.apply(
            lambda r: int(round(r["total_students"] / r["total_teachers"]))
            if pd.notna(r.get("total_teachers")) and r.get("total_teachers", 0) > 0
            else None, axis=1
        )

    # Drop helper columns not selected
    if "total_students" in df.columns and "Total Students" not in sel_metrics:
        df = df.drop(columns=["total_students"], errors="ignore")
    if "total_teachers" in df.columns and "Total Teachers" not in sel_metrics:
        df = df.drop(columns=["total_teachers"], errors="ignore")

    # Rename columns for display
    col_renames = {}
    for d in sel_dims:
        _, col = dim_options[d]
        alias = d.lower().replace(" ", "_")
        col_renames[alias] = d
        col_renames[col]   = d
    col_renames.update({"total_students": "Total Students",
                        "total_schools":  "Total Schools",
                        "total_teachers": "Total Teachers",
                        "ptr":            "PTR"})
    df = df.rename(columns=col_renames)

    # Format PTR column if present
    if "PTR" in df.columns:
        df["PTR"] = df["PTR"].apply(lambda v: f"{int(v)}:1" if pd.notna(v) else "N/A")

    st.markdown(f"**{len(df)} rows** returned")
    st.dataframe(df, use_container_width=True)

    # Auto chart: bar if numeric column present
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    if cat_cols and num_cols:
        fig = px.bar(
            df.head(30), x=cat_cols[0], y=num_cols[0],
            color=num_cols[0], color_continuous_scale="Greens",
            text=num_cols[0],
            labels={cat_cols[0]: cat_cols[0], num_cols[0]: num_cols[0]}
        )
        fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig.update_layout(
            plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=400,
            showlegend=False, coloraxis_showscale=False,
            margin=dict(t=30, b=80),
            xaxis=dict(tickangle=-30)
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    _export_buttons(df, "custom_report")
