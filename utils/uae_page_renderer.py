# utils/uae_page_renderer.py  ── v3.0 ── Full UAE Dashboard
# Matches India dashboard UI/UX exactly (Home + State Dashboard + Analytics)
# 
# Renders inside pages/1_Home.py, pages/2_State_Dashboard.py, pages/4_Analytics.py
# based on st.session_state["selected_region"] == "UAE"

import io
import os
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

/* ── Loading overlay ── */
.stSpinner > div { display: none !important; }
</style>
"""

# ─── DB connection params ─────────────────────────────────────────────────────
_DB_PARAMS = dict(
    host=os.getenv("DB_HOST", "localhost"),
    dbname=os.getenv("DB_NAME", os.getenv("DB_DATABASE", "tutorcloud_db")),
    user=os.getenv("DB_USER", "tutorcloud_admin"),
    password=os.getenv("DB_PASSWORD", ""),
    port=int(os.getenv("DB_PORT", "5432")),
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


# ---------------------------------------------------------------------------
# [MV_PATCH_v3] curriculum-aware KPI  ←  DO NOT REMOVE THIS LINE
# ---------------------------------------------------------------------------
def _mv_curriculum_kpi(academic_year: str,
                        curriculum_val: str,
                        emirate_val: str | None = None,
                        edtype_val: str | None  = None) -> dict:
    """
    Query uae.mv_uae_curriculum_kpi and return a dict with curriculum-scoped
    KPI values.  Returns None if the MV doesn't exist (graceful fallback).

    Keys returned
    -------------
    school_count, student_count, teacher_count, staff_count,
    female_students, male_students, emirati_students, resident_students,
    female_teachers, male_teachers, emirati_teachers, resident_teachers,
    student_teacher_ratio, students_per_school,
    has_enrollment_data, has_teacher_data, row_count
    """
    wheres  = ["academic_year = %s", "curriculum_en = %s"]
    params  = [academic_year, curriculum_val]
    if emirate_val and emirate_val not in ("All", "", None):
        wheres.append("region_en = %s")
        params.append(emirate_val)
    if edtype_val and edtype_val not in ("All", "", None):
        wheres.append("education_type = %s")
        params.append(edtype_val)
    where_sql = " AND ".join(wheres)

    agg_sql = f"""
        SELECT
            COALESCE(SUM(school_count),   0)               AS school_count,
            SUM(student_count)                             AS student_count,
            SUM(teacher_count)                             AS teacher_count,
            SUM(staff_count)                               AS staff_count,
            SUM(female_students)                           AS female_students,
            SUM(male_students)                             AS male_students,
            SUM(emirati_students)                          AS emirati_students,
            SUM(resident_students)                         AS resident_students,
            SUM(female_teachers)                           AS female_teachers,
            SUM(male_teachers)                             AS male_teachers,
            SUM(emirati_teachers)                          AS emirati_teachers,
            SUM(resident_teachers)                         AS resident_teachers,
            BOOL_OR(has_enrollment_data)                   AS has_enrollment_data,
            BOOL_OR(has_teacher_data)                      AS has_teacher_data,
            COUNT(*)                                       AS row_count
        FROM uae.mv_uae_curriculum_kpi
        WHERE {where_sql}
    """
    try:
        rows = _q(agg_sql, params)
        if rows is None or rows.empty:  # MV_HELPER_FIX_v3d – DataFrame-safe empty check
            return None
        r = rows.iloc[0]  # MV_HELPER_FIX_v3d – first row of DataFrame
        # Unpack named columns into a list so existing r[N] indexing is preserved
        import math as _math
        def _sv(v):
            """SQL NULL (pandas NaN/None) → Python None."""
            if v is None:
                return None
            if isinstance(v, float) and _math.isnan(v):
                return None
            return v
        r = [
            _sv(r["school_count"]),        # r[0]
            _sv(r["student_count"]),        # r[1]
            _sv(r["teacher_count"]),        # r[2]
            _sv(r["staff_count"]),          # r[3]
            _sv(r["female_students"]),      # r[4]
            _sv(r["male_students"]),        # r[5]
            _sv(r["emirati_students"]),     # r[6]
            _sv(r["resident_students"]),    # r[7]
            _sv(r["female_teachers"]),      # r[8]
            _sv(r["male_teachers"]),        # r[9]
            _sv(r["emirati_teachers"]),     # r[10]
            _sv(r["resident_teachers"]),    # r[11]
            _sv(r["has_enrollment_data"]),  # r[12]
            _sv(r["has_teacher_data"]),     # r[13]
            _sv(r["row_count"]),            # r[14]
        ]
        return {
            "school_count":       int(r[0]  or 0),
            "student_count":      r[1],          # None if no enr data
            "teacher_count":      r[2],          # None if no tch data
            "staff_count":        r[3],
            "female_students":    r[4],
            "male_students":      r[5],
            "emirati_students":   r[6],
            "resident_students":  r[7],
            "female_teachers":    r[8],
            "male_teachers":      r[9],
            "emirati_teachers":   r[10],
            "resident_teachers":  r[11],
            "has_enrollment_data": bool(r[12]),
            "has_teacher_data":   bool(r[13]),
            "row_count":          int(r[14] or 0),
        }
    except Exception as _exc:  # MV_HELPER_FIX_v3d
        print(f"[_mv_curriculum_kpi ERROR] {_exc}")
        return None          # MV not available – caller falls back gracefully

def _tbl_cols(table: str) -> list:
    """Return column list for a UAE table.
    NOT cached at this level — caching empty results caused a 1-hour
    blind-spot when DB was briefly unavailable at startup (KeyError: 'region_en').
    Results are still fast because _direct_q uses a short-lived psycopg2 pool.
    """
    df = _direct_q(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='uae' AND table_name=%s ORDER BY ordinal_position",
        [table]
    )
    cols = df["column_name"].tolist() if not df.empty else []
    # Warn in sidebar if DB returned nothing (helps diagnose connection issues)
    if not cols:
        try:
            st.sidebar.warning(f"⚠️ UAE schema: table '{table}' not found. Check DB connection.")
        except Exception:
            pass
    return cols


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


def _fmt_ptr_ratio(ptr_ratio) -> str:
    """Format an already-computed PTR ratio as integer X:1."""
    try:
        if ptr_ratio is None or pd.isna(ptr_ratio):
            return "N/A"
        ptr_ratio = float(ptr_ratio)
        if ptr_ratio <= 0:
            return "N/A"
        return f"{int(round(ptr_ratio))}:1"
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
    c1.download_button("📥 Download CSV", csv,
                       file_name=f"uae_{prefix}.csv",
                       mime="text/csv", key=f"csv_{prefix}")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=prefix[:31])
    c2.download_button("📊 Download Excel", buf.getvalue(),
                       file_name=f"uae_{prefix}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key=f"xl_{prefix}")


# ─── Sidebar filters ──────────────────────────────────────────────────────────

def _build_sidebar_filters() -> dict:
    """UAE sidebar – same look as India's sidebar filters."""
    try:
        enr_cols = _tbl_cols("uae_fact_enrollment")
        sch_cols = _tbl_cols("uae_fact_schools")
        tch_cols = _tbl_cols("uae_fact_teachers_emirate")
        pf_cols  = _tbl_cols("uae_fact_pass_fail")

        emirate_col    = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
        edu_type_col   = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type")
        sch_edu_type_col = _pick_col(sch_cols, "education_type", "school_type", "edu_type", "type")
        tch_edu_type_col = _pick_col(tch_cols, "education_type", "school_type", "edu_type", "type")
        pf_edu_type_col  = _pick_col(pf_cols,  "education_type", "school_type", "edu_type", "type")
        gender_col     = _pick_col(enr_cols, "gender", "student_gender")
        nat_col        = _pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality")
        cycle_col      = _pick_col(pf_cols,  "cycle", "education_cycle", "grade_level")
        curriculum_col = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")

        def _union_distinct_year(table_col_pairs):
            vals = []
            seen = set()
            for _tbl, _col in table_col_pairs:
                if not _col:
                    continue
                try:
                    for _v in _distinct(_tbl, _col):
                        _s = str(_v).strip() if _v is not None else ""
                        if _s and _s not in seen:
                            seen.add(_s)
                            vals.append(_s)
                except Exception:
                    pass
            return sorted(vals, key=lambda x: x.lower())


        def _sel(label, opts, key):
            all_opts = ["All"] + [str(x) for x in opts if x]
            return st.sidebar.selectbox(label, all_opts, key=key)

        filters = {}
        if emirate_col:
            opts = _distinct("uae_fact_enrollment", emirate_col)
            filters["emirate"] = {"col": emirate_col, "val": _sel("🏙️ Emirate", opts, "uae_emirate")}
        if edu_type_col:
            opts = _union_distinct_year([
                ("uae_fact_enrollment", edu_type_col),
                ("uae_fact_schools", sch_edu_type_col),
                ("uae_fact_teachers_emirate", tch_edu_type_col),
                ("uae_fact_pass_fail", pf_edu_type_col),
            ])
            filters["education_type"] = {"col": edu_type_col, "val": _sel("📚 Education Type", opts, "uae_edu_type")}
        if gender_col:
            opts = _distinct("uae_fact_enrollment", gender_col)
            filters["gender"] = {
                "col": gender_col,
                "val": _sel("👤 Gender", opts, "uae_gender"),
                "apply_to": [
                    "uae_fact_enrollment",
                    "uae_fact_student_nationalities",
                    "uae_fact_student_scores",
                    "uae_fact_pass_fail",
                ],
            }
        if nat_col:
            opts = _distinct("uae_fact_enrollment", nat_col)
            filters["nationality"] = {"col": nat_col, "val": _sel("🌍 Nationality Category", opts, "uae_nat")}
        if curriculum_col:
            opts = _distinct("uae_fact_schools", curriculum_col)
            filters["curriculum"] = {"col": curriculum_col, "val": _sel("📖 Curriculum", opts, "uae_curr")}

        # Curriculum cross-filter: look up which emirates have the
        # selected curriculum, then add an IN-list so enrollment/
        # teacher queries also scope to only those emirates.
        if "curriculum" in filters and filters["curriculum"]["val"] != "All":
            try:
                _cv  = filters["curriculum"]["val"]
                _cc  = filters["curriculum"]["col"]
                _emc = _pick_col(_tbl_cols("uae_fact_schools"),
                                  "region_en", "emirate", "emirate_en", "region")
                if _emc:
                    _df_ce = _q(
                        f"SELECT DISTINCT {_emc} FROM uae.uae_fact_schools "
                        f"WHERE academic_year=%s AND {_cc}=%s",
                        [UAE_YEAR, _cv]
                    )
                    if not _df_ce.empty:
                        _ems = [str(e) for e in _df_ce.iloc[:, 0].tolist() if e]
                        if _ems:
                            filters["_curriculum_emirate"] = {
                                "col": _emc, "val": _ems, "op": "in"
                            }
            except Exception:
                pass  # non-fatal: cross-filter best-effort

        # Show active filters in sidebar
        active = [
            v["val"]
            for k, v in filters.items()
            if not str(k).startswith("_") and v["val"] != "All"
        ]
        if active:
            st.sidebar.markdown("---")
            st.sidebar.markdown("**✅ Active Filters**")
            for a in active:
                st.sidebar.markdown(f"- {a}")
        return filters

    except Exception as ex:
        st.sidebar.warning(f"⚠️ UAE filter error: {ex}")
        return {}


def _where_clause(filters: dict, table_alias: str = "", allowed_cols: list = None, table_name: str = "") -> tuple:
    """Build SQL WHERE additions from the filters dict.
    Supports op='in' for list-based IN clauses (curriculum cross-filter).
    For cross-table filtering, tries exact column match then root-word match.

    UAE_GENDER_SCOPE_FIX_v2:
    Student gender is sourced from enrollment, so it must not map onto
    school_gender / teacher_gender in non-student tables.
    """
    parts, params = [], []
    prefix = f"{table_alias}." if table_alias else ""
    for _, finfo in filters.items():
        col = finfo["col"]
        val = finfo["val"]

        apply_to = finfo.get("apply_to")
        if table_name and apply_to and table_name not in apply_to:
            continue

        if finfo.get("op") == "in":
            if allowed_cols is not None and col not in allowed_cols:
                continue
            if isinstance(val, list) and val:
                placeholders = ",".join(["%s"] * len(val))
                parts.append(f"{prefix}{col} IN ({placeholders})")
                params.extend(val)
            continue

        if val == "All":
            continue

        if allowed_cols is not None:
            if col not in allowed_cols:
                root_words = set(col.replace("_en", "").replace("_cat", "").split("_"))
                alt_col = next(
                    (c for c in (allowed_cols or [])
                     if any(w in c for w in root_words) and len(w) > 2),
                    None
                )
                if alt_col:
                    col = alt_col
                else:
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
    st.markdown("# 🏠 TutorCloud Global Dashboard")
    st.markdown("**National K-12 Education Overview - UAE 2024-2025**")
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

    where, params = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")

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
        sch_where, sch_params = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")
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
        st.metric("TOTAL EMIRATES", str(em_count), help="States with data coverage")
    with col2:
        st.metric("TOTAL SCHOOLS", _fmt(total_sch), help="Total Schools")
    with col3:
        st.metric("TOTAL STUDENTS", _fmt(total_enr), help="Total Students")

    # Row 2: Teachers, PTR, Students/School
    col4, col5, col6 = st.columns(3)

    # Total teachers
    total_tch = 0
    if tch_cnt_col:
        tch_where, tch_params = _where_clause(filters, allowed_cols=tch_cols, table_name="uae_fact_teachers_emirate")
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
        st.metric("TOTAL TEACHERS", _fmt(total_tch), help="Total Teachers")
    with col5:
        st.metric("PTR (NATIONAL)", ptr_str, help="PTR")
    with col6:
        st.metric("STUDENTS/SCHOOL", sps_str, help="Students/School")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHART 1: Top Emirates by School Count
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("## 🏫 Top Emirates by School Count")
    if emirate_col and sch_cnt_col:
        sch_em_col = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
        if sch_em_col:
            sch_where, sch_params = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")
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
                fig2.update_traces(
                    texttemplate="%{text:,.0f}",
                    textposition="outside",
                    marker_line_color="white",
                    marker_line_width=1.5
                )
                fig2.update_layout(
                    height=480,
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(family="Segoe UI", size=11),
                    showlegend=False,
                    xaxis=dict(showgrid=False, title="", tickfont=dict(size=11), tickangle=-45),
                    yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Schools"),
                    margin=dict(l=70, r=50, t=50, b=150),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ─────────────────────────────────────────────────────────────────────────
    # CHART 2: Top Emirates by Student Enrollment
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("## 🏆 Top Emirates by Student Enrollment")
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
                color="students",
                color_continuous_scale=["#EAF4EA", "#006400"],
                text="students",
                labels={"emirate": "Emirate", "students": "Students"},
            )
            fig.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside",
                marker_line_color="white",
                marker_line_width=1.5
            )
            fig.update_layout(
                height=480,
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(family="Segoe UI", size=11),
                showlegend=False,
                xaxis=dict(showgrid=False, title="", tickfont=dict(size=11), tickangle=-45),
                yaxis=dict(showgrid=True, gridcolor="#F0F0F0", title="Students"),
                margin=dict(l=70, r=50, t=50, b=150),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ─────────────────────────────────────────────────────────────────────────
    # KEY INSIGHTS
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
    📊 State Dashboard
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
    📈 Analytics
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
    st.markdown('---')
    st.markdown(
        "<div style='text-align: center; color: #757575; font-size: clamp(0.8rem, 2vw, 0.9rem);'><p><strong>TutorCloud Global Dashboard</strong></p><p>© 2026 TutorCloud. All rights reserved.</p></div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. STATE DASHBOARD (UAE = Emirates)  ── mirrors India State Dashboard
# ══════════════════════════════════════════════════════════════════════════════

def _uae_scalar_value(sql: str, params=None, default=0):
    df = _q(sql, params)
    if df is None or df.empty:
        return default
    try:
        value = df.iloc[0, 0]
        if pd.isna(value):
            return default
        return value
    except Exception:
        return default


def _uae_overview_metrics(filters: dict) -> dict:
    enr_cols = _tbl_cols("uae_fact_enrollment")
    sch_cols = _tbl_cols("uae_fact_schools")
    tch_cols = _tbl_cols("uae_fact_teachers_emirate")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    gender_col = _pick_col(enr_cols, "gender", "student_gender")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    sch_em_col = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")
    where_sch, params_sch = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")
    where_tch, params_tch = _where_clause(filters, allowed_cols=tch_cols, table_name="uae_fact_teachers_emirate")

    total_students = int(_uae_scalar_value(
        f"SELECT COALESCE(SUM({enr_cnt_col}),0) FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr}",
        [UAE_YEAR] + params_enr,
        0,
    )) if enr_cnt_col else 0

    total_schools = int(_uae_scalar_value(
        f"SELECT COALESCE(SUM({sch_cnt_col}),0) FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch}",
        [UAE_YEAR] + params_sch,
        0,
    )) if sch_cnt_col else 0

    total_teachers = int(_uae_scalar_value(
        f"SELECT COALESCE(SUM({tch_cnt_col}),0) FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where_tch}",
        [UAE_YEAR] + params_tch,
        0,
    )) if tch_cnt_col else 0

    if gender_col and enr_cnt_col:
        df_gender = _q(
            f"SELECT {gender_col} AS gender, SUM({enr_cnt_col}) AS students FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr} GROUP BY {gender_col}",
            [UAE_YEAR] + params_enr,
        )
    else:
        df_gender = pd.DataFrame()

    male_students = int(df_gender[df_gender['gender'].astype(str).str.lower().str.startswith('m', na=False)]['students'].sum()) if not df_gender.empty else 0
    female_students = int(df_gender[df_gender['gender'].astype(str).str.lower().str.startswith('f', na=False)]['students'].sum()) if not df_gender.empty else 0

    total_districts = int(_uae_scalar_value(
        f"SELECT COUNT(DISTINCT {sch_em_col}) FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch}",
        [UAE_YEAR] + params_sch,
        0,
    )) if sch_em_col else 0

    return {
        'total_schools': total_schools,
        'schools_with_enrollment': total_schools if total_students > 0 else 0,
        'total_districts': total_districts,
        'total_students': total_students,
        'male_students': male_students,
        'female_students': female_students,
        'total_teachers': total_teachers,
        'state_ptr': _fmt_ptr(total_students, total_teachers),
    }


def _uae_emirate_analysis(filters: dict) -> pd.DataFrame:
    enr_cols = _tbl_cols("uae_fact_enrollment")
    sch_cols = _tbl_cols("uae_fact_schools")
    tch_cols = _tbl_cols("uae_fact_teachers_emirate")

    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    sch_em_col = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    tch_em_col = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")
    where_sch, params_sch = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")
    where_tch, params_tch = _where_clause(filters, allowed_cols=tch_cols, table_name="uae_fact_teachers_emirate")

    df_enr = _q(
        f"SELECT {emirate_col} AS emirate, SUM({enr_cnt_col}) AS total_students FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr} GROUP BY {emirate_col}",
        [UAE_YEAR] + params_enr,
    ) if emirate_col and enr_cnt_col else pd.DataFrame(columns=['emirate', 'total_students'])

    df_sch = _q(
        f"SELECT {sch_em_col} AS emirate, SUM({sch_cnt_col}) AS total_schools FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch} GROUP BY {sch_em_col}",
        [UAE_YEAR] + params_sch,
    ) if sch_em_col and sch_cnt_col else pd.DataFrame(columns=['emirate', 'total_schools'])

    df_tch = _q(
        f"SELECT {tch_em_col} AS emirate, SUM({tch_cnt_col}) AS total_teachers FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where_tch} GROUP BY {tch_em_col}",
        [UAE_YEAR] + params_tch,
    ) if tch_em_col and tch_cnt_col else pd.DataFrame(columns=['emirate', 'total_teachers'])

    frames = [df for df in [df_enr, df_sch, df_tch] if not df.empty]
    if not frames:
        return pd.DataFrame()
    out = frames[0]
    for frame in frames[1:]:
        out = out.merge(frame, on='emirate', how='outer')
    out = out.fillna(0)
    out['ptr_ratio'] = out.apply(
        lambda r: (
            float(r['total_students']) / float(r['total_teachers'])
            if float(r.get('total_teachers', 0) or 0) > 0 else None
        ),
        axis=1
    )
    out['PTR'] = out['ptr_ratio'].apply(_fmt_ptr_ratio)
    return out.sort_values(['total_students', 'total_schools'], ascending=[False, False])


def _uae_education_type_breakdown(filters: dict) -> pd.DataFrame:
    enr_cols = _tbl_cols("uae_fact_enrollment")
    edu_col = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type")
    gender_col = _pick_col(enr_cols, "gender", "student_gender")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")
    if not edu_col or not enr_cnt_col:
        return pd.DataFrame()
    select_gender = f", {gender_col} AS gender" if gender_col else ""
    group_gender = f", {gender_col}" if gender_col else ""
    df = _q(
        f"SELECT {edu_col} AS education_type{select_gender}, SUM({enr_cnt_col}) AS students FROM uae.uae_fact_enrollment WHERE academic_year=%s{where_enr} GROUP BY {edu_col}{group_gender} ORDER BY students DESC",
        [UAE_YEAR] + params_enr,
    )
    return df


def _uae_school_directory_summary(filters: dict) -> pd.DataFrame:
    sch_cols = _tbl_cols("uae_fact_schools")
    emirate_col = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    curr_col = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")
    level_col = _pick_col(sch_cols, "school_level", "level", "education_level", "cycle")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    where_sch, params_sch = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")
    if not sch_cnt_col:
        return pd.DataFrame()
    emirate_sel = f"{emirate_col} AS emirate," if emirate_col else ""
    curriculum_sel = f"{curr_col} AS curriculum," if curr_col else ""
    level_sel = f"{level_col} AS school_level," if level_col else ""
    group_cols = [c for c in [emirate_col, curr_col, level_col] if c]
    if not group_cols:
        return pd.DataFrame()
    df = _q(
        f"SELECT {emirate_sel}{curriculum_sel}{level_sel} SUM({sch_cnt_col}) AS total_schools FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch} GROUP BY {', '.join(group_cols)} ORDER BY total_schools DESC",
        [UAE_YEAR] + params_sch,
    )
    return df


def _render_footer():
    st.markdown("""
        <div style='text-align: center; padding: 20px; margin-top: 40px; border-top: 1px solid #e0e0e0;'>
        <p style='margin: 0; color: #666; font-size: 0.95rem;'>TutorCloud Global Dashboard</p>
        <p style='margin: 5px 0 0 0; color: #666; font-size: 0.95rem;'>© 2026 TutorCloud. All rights reserved.</p>
        </div>
        """, unsafe_allow_html=True)

def render_uae_state_dashboard():
    _inject_css()

    st.markdown("# 📊 State Dashboard")
    st.markdown("**Regional Education Overview - UAE**")

    filters = _build_sidebar_filters()

    overview = _uae_overview_metrics(filters)
    district_df = _uae_emirate_analysis(filters)
    edu_df = _uae_education_type_breakdown(filters)

    def _pick_col(df, *candidates):
        if df is None or len(df) == 0:
            return None
        cols = set(df.columns)
        for c in candidates:
            if c in cols:
                return c
        return None

    def _safe_num(v, digits=2):
        try:
            return f"{float(v):,.{digits}f}"
        except Exception:
            return "N/A"

    selected_emirate = (
        filters.get("emirate")
        or filters.get("region_en")
        or filters.get("emirate_en")
        or "UAE"
    )
    overview_title = selected_emirate if selected_emirate not in [None, "", "All"] else "UAE"

    # India-style active filters in sidebar
    active_filters = []
    for key, label in [
        ("emirate", "Emirate"),
        ("education_type", "Education Type"),
        ("gender", "Gender"),
        ("nationality_category", "Nationality Category"),
        ("curriculum", "Curriculum"),
    ]:
        val = filters.get(key)
        if val not in [None, "", "All", []]:
            active_filters.append(f"{label}: {val}")

    if active_filters:
        st.sidebar.markdown("### Active Filters")
        for item in active_filters:
            st.sidebar.markdown(f"- {item}")

    # India-style KPI count: 6 only
    total_schools = overview.get("total_schools", 0)
    schools_with_enrollment = overview.get("schools_with_enrollment", overview.get("schools_with_students", 0))
    total_districts = overview.get("total_districts", overview.get("districts", 0))
    total_students = overview.get("total_students", 0)
    total_teachers = overview.get("total_teachers", 0)
    ptr_value = overview.get("ptr", overview.get("state_ptr", overview.get("ptr_national", None)))

    st.markdown(f"## 📊 Overview: {overview_title}")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    c1.metric("🏫 Total Schools", _fmt(total_schools))
    c2.metric("🎓 Schools with Enrollment", _fmt(schools_with_enrollment))
    c3.metric("🗺️ Districts", _fmt(total_districts))
    c4.metric("📊 State PTR", overview.get("state_ptr", "N/A"))
    c5.metric("👥 Total Students", _fmt(total_students))
    c6.metric("👨‍🏫 Total Teachers", _fmt(total_teachers))

    # India-equivalent enrollment slot
    st.markdown("## 📚 Enrollment Analysis")
    if edu_df is not None and len(edu_df) > 0:
        label_col = _pick_col(edu_df, "education_type", "school_type", "curriculum", "category")
        value_col = _pick_col(edu_df, "total_students", "students", "student_count", "enrollment")
        color_col = _pick_col(edu_df, "gender", "category", "education_type")

        if label_col and value_col:
            fig_edu = px.bar(
                edu_df,
                x=label_col,
                y=value_col,
                color=color_col if color_col in edu_df.columns and color_col != label_col else None,
                title="Enrollment Analysis",
                labels={label_col: "Category", value_col: "Students"},
            )
            fig_edu.update_layout(height=450, xaxis_tickangle=-35)
            st.plotly_chart(fig_edu, use_container_width=True)
        else:
            st.info("Enrollment analysis is not available for the current selection.")
    else:
        st.info("Enrollment analysis is not available for the current selection.")

    # India-equivalent district section
    st.markdown("## 📍 District-Level PTR Analysis")
    if district_df is not None and len(district_df) > 0:
        district_col = _pick_col(district_df, "district_name", "district", "emirate", "region_en", "region")
        schools_col = _pick_col(district_df, "total_schools", "schools", "school_count")
        students_col = _pick_col(district_df, "total_students", "students", "student_count")
        teachers_col = _pick_col(district_df, "total_teachers", "teachers", "teacher_count")
        ptr_col = _pick_col(district_df, "ptr", "state_ptr", "district_ptr")

        chart_df = district_df.copy()
        if schools_col and schools_col in chart_df.columns:
            chart_df[schools_col] = pd.to_numeric(chart_df[schools_col], errors="coerce")
            chart_df = chart_df.sort_values(schools_col, ascending=False).head(20)

        if district_col and ptr_col and district_col in chart_df.columns and ptr_col in chart_df.columns:
            chart_df[ptr_col] = pd.to_numeric(chart_df[ptr_col], errors="coerce")
            fig_district = px.bar(
                chart_df,
                x=district_col,
                y=ptr_col,
                title="Top 20 Districts by School Count",
                hover_data=[c for c in [schools_col, students_col, teachers_col] if c in chart_df.columns],
                labels={district_col: "District", ptr_col: "PTR"},
            )
            fig_district.update_layout(height=450, xaxis_tickangle=-45)
            st.plotly_chart(fig_district, use_container_width=True)

        display_df = district_df.copy()
        if ptr_col and ptr_col in display_df.columns:
            display_df[ptr_col] = pd.to_numeric(display_df[ptr_col], errors="coerce").apply(_fmt_ptr_ratio)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.download_button(
            label="📥 Download District Data (CSV)",
            data=display_df.to_csv(index=False).encode("utf-8"),
            file_name="uae_state_dashboard_district_data.csv",
            mime="text/csv",
        )
    else:
        st.info("District-level PTR analysis is not available for the current selection.")

    # India-equivalent conditional lower-level section
    if overview_title not in [None, "", "All", "UAE"]:
        st.markdown(f"## 🏘️ Curriculum-Level Analysis: {overview_title}")

        lower_src = _uae_school_directory_summary(filters)
        curriculum_col = _pick_col(lower_src, "curriculum", "Curriculum")
        schools_col = _pick_col(lower_src, "total_schools", "Total Schools")
        emirate_col_lower = _pick_col(lower_src, "emirate", "Emirate", "District")

        if lower_src is not None and not lower_src.empty and curriculum_col and schools_col:
            working = lower_src.copy()

            if emirate_col_lower and emirate_col_lower in working.columns:
                working = working[working[emirate_col_lower].astype(str) == str(overview_title)]

            if working.empty:
                st.info("No curriculum-level data available for the selected filters.")
            else:
                lower_df = (
                    working.groupby(curriculum_col, dropna=False)[schools_col]
                    .sum()
                    .reset_index()
                )
                lower_df.columns = ["Curriculum", "Total Schools"]
                lower_df["Curriculum"] = lower_df["Curriculum"].astype(str)
                lower_df["Total Schools"] = pd.to_numeric(lower_df["Total Schools"], errors="coerce").fillna(0)

                total_students = []
                total_teachers = []

                for curriculum_name in lower_df["Curriculum"]:
                    try:
                        kpi = _mv_curriculum_kpi(UAE_YEAR, curriculum_name, emirate_val=overview_title)
                    except Exception:
                        kpi = {}

                    students = (
                        kpi.get("total_students",
                        kpi.get("students",
                        kpi.get("student_count",
                        kpi.get("enrollment", 0))))
                    )
                    teachers = (
                        kpi.get("total_teachers",
                        kpi.get("teachers",
                        kpi.get("teacher_count", 0)))
                    )

                    try:
                        students = float(students or 0)
                    except Exception:
                        students = 0.0

                    try:
                        teachers = float(teachers or 0)
                    except Exception:
                        teachers = 0.0

                    total_students.append(students)
                    total_teachers.append(teachers)

                lower_df["Total Students"] = total_students
                lower_df["Total Teachers"] = total_teachers
                lower_df["PTR"] = lower_df.apply(
                    lambda r: round(r["Total Students"] / r["Total Teachers"], 2) if r["Total Teachers"] else None,
                    axis=1
                )
                lower_df["ptr_formatted"] = lower_df["PTR"].apply(_fmt_ptr_ratio)

                display_lower_df = lower_df[["Curriculum", "Total Schools", "Total Students", "Total Teachers", "PTR"]].copy()
                display_lower_df["PTR"] = display_lower_df["PTR"].apply(_fmt_ptr_ratio)
                st.dataframe(display_lower_df, use_container_width=True, hide_index=True)

                chart_df = lower_df.dropna(subset=["PTR"]).copy()
                chart_df["ptr_formatted"] = chart_df["PTR"].apply(_fmt_ptr_ratio)
                chart_df = chart_df.sort_values(["Total Schools", "PTR"], ascending=[False, False])

                if len(chart_df) > 1:
                    fig_lower = px.bar(
                        chart_df.head(20),
                        x="Curriculum",
                        y="PTR",
                        title=f"Curriculum PTR Comparison in {overview_title} (Top 20 by School Count)",
                        labels={"Curriculum": "Curriculum", "PTR": "Pupil-Teacher Ratio"},
                        color="PTR",
                        color_continuous_scale="RdYlGn_r",
                        custom_data=["ptr_formatted"]
                    )
                    fig_lower.update_traces(
                        hovertemplate="<b>%{x}</b><br>PTR: %{customdata[0]}<extra></extra>",
                        text=chart_df.head(20)["ptr_formatted"],
                        textposition="outside"
                    )
                    fig_lower.update_layout(
                        xaxis_tickangle=-45,
                        margin=dict(l=60, r=40, t=80, b=120),
                        plot_bgcolor="white",
                        paper_bgcolor="white"
                    )
                    st.plotly_chart(fig_lower, use_container_width=True, config={"displayModeBar": False})

                csv_lower = display_lower_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Curriculum Data (CSV)",
                    data=csv_lower,
                    file_name=f"curriculum_analysis_{str(overview_title).lower().replace(' ', '_')}.csv",
                    mime="text/csv",
                    key="download_curriculum"
                )
        else:
            st.info("No curriculum-level data available for the selected filters.")
    else:
        st.markdown("## 🏘️ Curriculum-Level Analysis")
        st.info("Select a specific Emirate to view curriculum-level analysis.")

    _render_footer()

def _uae_tab_overview(filters):
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    emirate_col = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    gender_col  = _pick_col(enr_cols, "gender", "student_gender")
    edu_col     = _pick_col(enr_cols, "education_type", "school_type", "edu_type", "type", "education_level")
    nat_col     = _pick_col(enr_cols, "nationality_cat", "nationality_category", "nationality")

    where, params = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")

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
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont_size=11)
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=400,
                              showlegend=False, coloraxis_showscale=False,
                              xaxis=dict(tickangle=-45),
                              margin=dict(l=60, r=220, t=80, b=120))
            fig.update_traces(hovertemplate="<b>%{y}</b><br>PTR: %{text}<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)

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


# ── Tab 2: Schools ─────────────────────────────────────────────────────────────

def _uae_tab_schools(filters):
    sch_cols    = _tbl_cols("uae_fact_schools")
    emirate_col = _pick_col(sch_cols, "region_en", "emirate", "emirate_en", "region")
    sch_cnt_col = _pick_col(sch_cols, "school_count", "num_schools", "count")
    curr_col    = _pick_col(sch_cols, "curriculum_en", "curriculum", "curriculum_type")
    gender_col  = _pick_col(sch_cols, "gender", "school_gender")
    level_col   = _pick_col(sch_cols, "school_level", "level", "education_level", "cycle")

    where, params = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")

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
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont_size=11)
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=400,
                              showlegend=False, coloraxis_showscale=False,
                              xaxis=dict(tickangle=-45),
                              margin=dict(l=60, r=220, t=80, b=120))
            st.plotly_chart(fig, use_container_width=True)

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


# ── Tab 3: Teachers ────────────────────────────────────────────────────────────

def _uae_tab_teachers(filters):
    tch_cols    = _tbl_cols("uae_fact_teachers_emirate")
    emirate_col = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    tch_cnt_col = _pick_col(tch_cols, "teacher_count", "num_teachers", "count", "teachers")
    gender_col  = _pick_col(tch_cols, "gender", "teacher_gender")
    nat_col     = _pick_col(tch_cols, "nationality_cat", "nationality_category", "nationality")

    where, params = _where_clause(filters, allowed_cols=tch_cols, table_name="uae_fact_teachers_emirate")

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
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont_size=11)
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=400,
                              showlegend=False, coloraxis_showscale=False,
                              xaxis=dict(tickangle=-45),
                              margin=dict(l=60, r=220, t=80, b=120))
            st.plotly_chart(fig, use_container_width=True)

    # PTR by emirate
    enr_cols    = _tbl_cols("uae_fact_enrollment")
    enr_em_col  = _pick_col(enr_cols, "region_en", "emirate", "emirate_en", "region")
    enr_cnt_col = _pick_col(enr_cols, "student_count", "enrollment_count", "students", "count")
    if emirate_col and tch_cnt_col and enr_em_col and enr_cnt_col:
        st.markdown('<div class="uae-section-header">📐 PTR (PTR) by Emirate</div>', unsafe_allow_html=True)
        df_t = _q(f"SELECT {emirate_col} AS emirate, SUM({tch_cnt_col}) AS teachers "
                  f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s GROUP BY {emirate_col}",
                  [UAE_YEAR])
        df_e = _q(f"SELECT {enr_em_col} AS emirate, SUM({enr_cnt_col}) AS students "
                  f"FROM uae.uae_fact_enrollment WHERE academic_year=%s GROUP BY {enr_em_col}",
                  [UAE_YEAR])
        if not df_t.empty and not df_e.empty:
            df_ptr = df_e.merge(df_t, on="emirate", how="inner")
            df_ptr["PTR"] = (df_ptr["students"] / df_ptr["teachers"]).apply(
                lambda x: float(x) if pd.notna(x) and x > 0 else None)
            df_ptr["ptr_formatted"] = df_ptr["PTR"].apply(_fmt_ptr_ratio)
            df_ptr = df_ptr.sort_values("PTR", ascending=False)
            fig = px.bar(df_ptr, x="PTR", y="emirate", orientation="h",
                         color="PTR", color_continuous_scale="RdYlGn_r",
                         labels={"emirate": "Emirate", "PTR": "Students per Teacher"},
                         text="ptr_formatted")
            fig.update_traces(
                texttemplate="%{text}",
                textposition="outside",
                customdata=df_ptr[["ptr_formatted"]].values,
                hovertemplate="<b>%{y}</b><br>PTR: %{customdata[0]}<extra></extra>"
            )
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=340,
                              margin=dict(l=120, t=30))
            st.plotly_chart(fig, use_container_width=True)

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

    where_pf, params_pf = _where_clause(filters, allowed_cols=pf_cols, table_name="uae_fact_pass_fail")
    where_sc, params_sc = _where_clause(filters, allowed_cols=sc_cols, table_name="uae_fact_student_scores")

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
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=400,
                              xaxis=dict(tickangle=-45),
                              margin=dict(l=60, r=220, t=80, b=120))
            st.plotly_chart(fig, use_container_width=True)

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
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", textfont_size=11)
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=400,
                              showlegend=False, coloraxis_showscale=False,
                              xaxis=dict(tickangle=-45),
                              margin=dict(l=60, r=220, t=80, b=120))
            st.plotly_chart(fig, use_container_width=True)


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

    where_nat, params_nat = _where_clause(filters, allowed_cols=nat_cols, table_name="uae_fact_student_nationalities")
    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")

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
            fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont_size=11)
            fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF",
                              height=max(400, len(df) * 26),
                              showlegend=False, coloraxis_showscale=False,
                              margin=dict(l=160, t=30))
            st.plotly_chart(fig, use_container_width=True)

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


# ══════════════════════════════════════════════════════════════════════════════
# 3. ANALYTICS PAGE  ── mirrors India Analytics page exactly
# ══════════════════════════════════════════════════════════════════════════════


def render_uae_analytics():
    from io import BytesIO

    _inject_css()
    st.markdown('<div class="main-header">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Enhanced Analytics: Maps, Metrics, Comparison & Reports</div>', unsafe_allow_html=True)

    base_filters = _build_sidebar_filters()

    enr_cols = _tbl_cols('uae_fact_enrollment')
    sch_cols = _tbl_cols('uae_fact_schools')
    emirate_col = _pick_col(enr_cols, 'region_en', 'emirate', 'emirate_en', 'region')
    curriculum_col = _pick_col(sch_cols, 'curriculum_en', 'curriculum', 'curriculum_type')

    def _clone_filters():
        out = {}
        for k, v in (base_filters or {}).items():
            out[k] = v.copy() if isinstance(v, dict) else v
        return out

    def _options(table_name, col_name):
        if not col_name:
            return ['All']
        try:
            vals = _distinct(table_name, col_name)
        except Exception:
            vals = []
        clean = [str(v) for v in vals if v not in (None, '', 'All')]
        return ['All'] + sorted(clean)

    emirate_options = _options('uae_fact_enrollment', emirate_col)
    curriculum_options = _options('uae_fact_schools', curriculum_col)

    def _apply_scope(filters=None, emirate='All', curriculum='All'):
        scoped = _clone_filters() if filters is None else filters
        if emirate not in (None, '', 'All') and emirate_col:
            scoped['state'] = {'col': emirate_col, 'val': emirate}
        if curriculum not in (None, '', 'All') and curriculum_col:
            scoped['district'] = {'col': curriculum_col, 'val': curriculum, 'apply_to': ['uae_fact_schools']}
        return scoped

    def _safe_series(df, *candidates):
        col = _pick_col(df, *candidates)
        if col and col in df.columns:
            return df[col]
        return pd.Series([None] * len(df))

    def _as_float(value):
        try:
            return float(str(value).replace(',', '').strip())
        except Exception:
            return 0.0

    def _emirate_frame(local_filters):
        src = _uae_emirate_analysis(local_filters)
        if src is None or src.empty:
            return pd.DataFrame(columns=['Location', 'Total Schools', 'Total Students', 'Total Teachers', 'PTR', 'Students per School', 'Teachers per School'])

        out = pd.DataFrame()
        out['Location'] = _safe_series(src, 'emirate', 'region_en', 'emirate_en').astype(str)
        out['Total Schools'] = pd.to_numeric(_safe_series(src, 'total_schools', 'schools'), errors='coerce').fillna(0)
        out['Total Students'] = pd.to_numeric(_safe_series(src, 'total_students', 'students'), errors='coerce').fillna(0)
        out['Total Teachers'] = pd.to_numeric(_safe_series(src, 'total_teachers', 'teachers'), errors='coerce').fillna(0)
        out['PTR'] = pd.to_numeric(_safe_series(src, 'ptr_ratio', 'PTR', 'ptr'), errors='coerce').apply(_fmt_ptr_ratio)
        out['Students per School'] = out.apply(lambda r: (r['Total Students'] / r['Total Schools']) if r['Total Schools'] else None, axis=1)
        out['Teachers per School'] = out.apply(lambda r: (r['Total Teachers'] / r['Total Schools']) if r['Total Schools'] else None, axis=1)
        out = out.dropna(subset=['Location'])
        return out.sort_values(['Total Students', 'Total Schools'], ascending=[False, False]).reset_index(drop=True)

    def _curriculum_frame(local_filters):
        src = _uae_school_directory_summary(local_filters)
        if src is None or src.empty:
            return pd.DataFrame(columns=['Location', 'Total Schools', 'Total Students', 'Total Teachers', 'PTR', 'Students per School', 'Teachers per School'])

        group_col = _pick_col(src, 'curriculum', 'Curriculum')
        schools_col = _pick_col(src, 'total_schools', 'Total Schools')
        if not group_col or not schools_col:
            return pd.DataFrame(columns=['Location', 'Total Schools', 'Total Students', 'Total Teachers', 'PTR', 'Students per School', 'Teachers per School'])

        out = src.groupby(group_col, dropna=False)[schools_col].sum().reset_index()
        out = out.rename(columns={group_col: 'Location', schools_col: 'Total Schools'})
        out['Location'] = out['Location'].astype(str)
        out['Total Schools'] = pd.to_numeric(out['Total Schools'], errors='coerce').fillna(0)
        out['Total Students'] = 0
        out['Total Teachers'] = 0
        out['PTR'] = None
        out['Students per School'] = None
        out['Teachers per School'] = None
        return out.sort_values('Total Schools', ascending=False).reset_index(drop=True)

    def _metric_view(df, metric_name):
        mapping = {
            'PTR': 'PTR',
            'Students per School': 'Students per School',
            'Total Students': 'Total Students',
            'Total Schools': 'Total Schools',
        }
        col = mapping[metric_name]
        view = df.copy()
        view['Metric Value'] = pd.to_numeric(view[col], errors='coerce').fillna(0)
        ordered = ['Location', 'Metric Value', 'Total Schools', 'Total Students', 'Total Teachers', 'PTR', 'Students per School', 'Teachers per School']
        return view[ordered]

    tabs = st.tabs(["🗺️ Geographic Maps", "🎯 Performance Metrics", "🔍 Comparative Analysis", "📝 Custom Reports"])

    with tabs[0]:
        geo_metric = st.selectbox(
            "Select Metric to Visualize",
            ["PTR", "Students per School", "Total Students", "Total Schools"],
            key="uae_geo_metric_parity"
        )
        geo_level = st.radio(
            "Select Level",
            ["Emirate", "Curriculum"],
            horizontal=True,
            key="uae_geo_level_parity"
        )
        geo_emirate = st.selectbox(
            "Select Emirate",
            emirate_options,
            index=0,
            key="uae_geo_emirate_parity"
        )

        geo_filters = _apply_scope(emirate=geo_emirate)
        base_df = _emirate_frame(geo_filters) if geo_level == "Emirate" else _curriculum_frame(geo_filters)
        view_df = _metric_view(base_df, geo_metric)

        if view_df.empty:
            st.info("No data available for the selected filters.")
        else:
            fig = px.bar(
                view_df.head(20),
                x="Location",
                y="Metric Value",
                color="Metric Value",
                color_continuous_scale="Blues",
                title=f"Top 20 {geo_level}s by {geo_metric}",
            )
            fig.update_layout(
                xaxis_tickangle=-45,
                margin=dict(l=60, r=30, t=80, b=120),
                plot_bgcolor="white",
                paper_bgcolor="white"
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            st.dataframe(view_df, use_container_width=True, hide_index=True)

    with tabs[1]:
        perf_emirate = st.selectbox(
            "Select Emirate",
            emirate_options,
            index=0,
            key="uae_perf_emirate_parity"
        )
        perf_curriculum = st.selectbox(
            "Select Curriculum",
            curriculum_options,
            index=0,
            key="uae_perf_curriculum_parity"
        )

        perf_filters = _apply_scope(emirate=perf_emirate, curriculum=perf_curriculum)
        overview = _uae_overview_metrics(perf_filters) or {}

        total_schools = overview.get('total_schools', 0)
        total_students = overview.get('total_students', 0)
        total_teachers = overview.get('total_teachers', 0)
        ptr_value = overview.get('state_ptr', overview.get('ptr', 'N/A'))

        c1, c2, c3 = st.columns(3)
        c4, c5, c6 = st.columns(3)

        with c1:
            st.metric("🏫 Total Schools", _fmt(total_schools))
        with c2:
            st.metric("👥 Total Students", _fmt(total_students))
        with c3:
            st.metric("👨‍🏫 Total Teachers", _fmt(total_teachers))
        with c4:
            st.metric("📊 PTR", _fmt_ptr_ratio(ptr_value))
        with c5:
            schools_num = _as_float(total_schools)
            students_num = _as_float(total_students)
            st.metric("🎓 Students / School", f"{(students_num / schools_num):,.2f}" if schools_num else "0.00")
        with c6:
            schools_num = _as_float(total_schools)
            teachers_num = _as_float(total_teachers)
            st.metric("🏫 Teachers / School", f"{(teachers_num / schools_num):,.2f}" if schools_num else "0.00")

    with tabs[2]:
        comparison_level = st.radio(
            "Comparison Level",
            ["Emirate vs Emirate", "Curriculum vs Curriculum"],
            horizontal=True,
            key="uae_compare_level_parity"
        )

        if comparison_level == "Emirate vs Emirate":
            compare_options = [x for x in emirate_options if x != 'All']
            label_a = "Select Emirate A"
            label_b = "Select Emirate B"
            compare_df = _emirate_frame(_clone_filters())
        else:
            compare_options = [x for x in curriculum_options if x != 'All']
            label_a = "Select Curriculum A"
            label_b = "Select Curriculum B"
            compare_df = _curriculum_frame(_clone_filters())

        col_a, col_b = st.columns(2)
        with col_a:
            loc_a = st.selectbox(label_a, compare_options, key="uae_compare_a_parity") if compare_options else None
        with col_b:
            remaining = [x for x in compare_options if x != loc_a] or compare_options
            loc_b = st.selectbox(label_b, remaining, key="uae_compare_b_parity") if remaining else None

        if st.button("Compare", key="uae_compare_button_parity"):
            if compare_df.empty or not loc_a or not loc_b:
                st.info("Not enough data available to compare the selected locations.")
            else:
                result = compare_df[compare_df['Location'].isin([loc_a, loc_b])].copy()
                st.dataframe(result, use_container_width=True, hide_index=True)
                st.download_button(
                    "📥 Download Comparison CSV",
                    result.to_csv(index=False),
                    "uae_comparison.csv",
                    "text/csv",
                    key="uae_compare_csv_parity"
                )

    with tabs[3]:
        report_dimensions = st.multiselect(
            "Select Dimensions",
            ["Emirate", "Curriculum", "School Level"],
            default=["Emirate"],
            key="uae_report_dims_parity"
        )
        report_metrics = st.multiselect(
            "Select Metrics",
            ["Total Schools", "Total Students", "Total Teachers", "PTR"],
            default=["Total Schools"],
            key="uae_report_metrics_parity"
        )

        if st.button("Generate Report", key="uae_generate_report_parity"):
            src = _uae_school_directory_summary(_clone_filters())
            if src is None or src.empty:
                st.info("No data available for the selected report dimensions.")
            else:
                dim_map = {
                    "Emirate": _pick_col(src, "emirate", "District"),
                    "Curriculum": _pick_col(src, "curriculum", "Curriculum"),
                    "School Level": _pick_col(src, "school_level", "School Level"),
                }
                group_cols = [dim_map[d] for d in report_dimensions if dim_map.get(d)]
                schools_col = _pick_col(src, "total_schools", "Total Schools")

                if not group_cols:
                    st.info("Please select at least one valid dimension.")
                else:
                    if schools_col:
                        report = src.groupby(group_cols, dropna=False)[schools_col].sum().reset_index()
                    else:
                        report = src[group_cols].drop_duplicates().reset_index(drop=True)

                    rename_map = {v: k for k, v in dim_map.items() if v}
                    report = report.rename(columns=rename_map)
                    if schools_col and schools_col in report.columns and "Total Schools" not in report.columns:
                        report = report.rename(columns={schools_col: "Total Schools"})

                    needs_emirate_metrics = any(m in report_metrics for m in ["Total Students", "Total Teachers", "PTR"])
                    if needs_emirate_metrics and "Emirate" in report.columns:
                        emirate_metrics = _emirate_frame(_clone_filters())
                        if not emirate_metrics.empty:
                            report = report.merge(
                                emirate_metrics.rename(columns={"Location": "Emirate"})[["Emirate", "Total Students", "Total Teachers", "PTR"]],
                                on="Emirate",
                                how="left"
                            )

                    ordered_cols = [c for c in report_dimensions if c in report.columns] + [m for m in report_metrics if m in report.columns]
                    if not ordered_cols:
                        ordered_cols = list(report.columns)

                    report = report[ordered_cols].reset_index(drop=True)
                    st.dataframe(report, use_container_width=True, hide_index=True)

                    st.download_button(
                        "📥 Download CSV",
                        report.to_csv(index=False).encode("utf-8"),
                        "uae_custom_report.csv",
                        "text/csv",
                        key="uae_report_csv_parity"
                    )

                    excel_buffer = BytesIO()
                    try:
                        with pd.ExcelWriter(excel_buffer) as writer:
                            report.to_excel(writer, index=False, sheet_name="Custom Report")
                        st.download_button(
                            "📥 Download Excel",
                            excel_buffer.getvalue(),
                            "uae_custom_report.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="uae_report_excel_parity"
                        )
                    except Exception:
                        pass

    _render_footer()
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

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")
    where_sch, params_sch = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")
    where_tch, params_tch = _where_clause(filters, allowed_cols=tch_cols, table_name="uae_fact_teachers_emirate")

    # Metric selector (same as India)
    metric_choice = st.selectbox(
        "📊 Select Metric to Visualize",
        ["PTR (PTR)", "Students per School", "Total Students", "Total Schools"],
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

    elif metric_choice == "PTR (PTR)":
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
        if "PTR" in metric_choice:
            _ptr_labels = df["value"].apply(_fmt_ptr_ratio)
            fig.update_traces(
                customdata=_ptr_labels,
                texttemplate="%{customdata}",
                hovertemplate="<b>%{x}</b><br>PTR: %{customdata}<extra></extra>",
                textposition="outside"
            )
        else:
            fig.update_traces(
                texttemplate="%{text:,.0f}",
                textposition="outside"
            )
        fig.update_layout(
            height=480, plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False, coloraxis_showscale=False,
            font=dict(family="Segoe UI", size=11),
            margin=dict(l=60, r=50, t=80, b=120),
            xaxis=dict(tickfont=dict(size=11), tickangle=-45),
            yaxis=dict(title=y_label)
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown("### 📋 Raw Data Table")
        st.dataframe(
            df.rename(columns={"emirate": "Emirate", "value": y_label}),
            use_container_width=True
        )


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

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")
    where_sch, params_sch = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")
    where_tch, params_tch = _where_clause(filters, allowed_cols=tch_cols, table_name="uae_fact_teachers_emirate")

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
    st.caption("UAE_PTR_BUILD_20260409_V3")
    k1, k2, k3 = st.columns(3)
    with k1: st.metric("🏫 Total Schools",   _fmt(total_sch))
    with k2: st.metric("🎓 Total Students",  _fmt(total_enr))
    with k3: st.metric("👨‍🏫 Total Teachers", _fmt(total_tch))

    k4, k5, k6 = st.columns(3)
    computed_ptr = (float(total_enr) / float(total_tch)) if (total_tch is not None and float(total_tch) > 0) else None
    ptr_color = "normal" if (computed_ptr is not None and computed_ptr < 30) else "inverse"
    ptr_display = f"{int(round(computed_ptr))}:1" if computed_ptr is not None else "N/A"
    with k4: st.metric("📐 PTR", ptr_display, delta_color=ptr_color)
    with k5: st.metric("📚 Students/School",        _fmt(sps) if sps else "N/A")
    with k6: st.metric("🏫 Teachers/School",        f"{tps:.2f}" if tps else "N/A")

    # Avg scores by subject bar
    if subj_col and avg_col:
        st.markdown('<div class="uae-section-header">📖 Average Score by Subject</div>', unsafe_allow_html=True)
        where_sc, params_sc = _where_clause(filters, allowed_cols=sc_cols, table_name="uae_fact_student_scores")
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
        where_pf, params_pf = _where_clause(filters, allowed_cols=pf_cols, table_name="uae_fact_pass_fail")
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
                try: return _fmt_ptr_ratio(v)
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
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont_size=11)
        fig.update_layout(plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=500,
                          xaxis=dict(tickangle=-45),
                          margin=dict(l=60, r=40, t=80, b=120))
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
    # SELECT aliases raw col (e.g. region_en AS emirate); use alias for Python merge
    _enr_dim_labels = [d for d in sel_dims if dim_options[d][0] == "uae_fact_enrollment"]
    merge_col = _enr_dim_labels[0].lower().replace(' ', '_') if _enr_dim_labels else group_cols[0]

    where_enr, params_enr = _where_clause(filters, allowed_cols=enr_cols, table_name="uae_fact_enrollment")

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
        where_sch2, params_sch2 = _where_clause(filters, allowed_cols=sch_cols, table_name="uae_fact_schools")
        df_smerge = _q(
            f"SELECT {sch_em_col2} AS __dim__, SUM({sch_cnt_col}) AS total_schools "
            f"FROM uae.uae_fact_schools WHERE academic_year=%s{where_sch2} "
            f"GROUP BY {sch_em_col2}",
            [UAE_YEAR] + params_sch2
        )
        if not df_smerge.empty:
            df_smerge = df_smerge.rename(columns={"__dim__": merge_col})
            df = df.merge(df_smerge, on=merge_col, how="left")

    # Merge Teachers data if needed (Total Teachers or PTR)
    tch_em_col2 = _pick_col(tch_cols, "region_en", "emirate", "emirate_en", "region")
    if need_teachers and tch_em_col2:
        where_tch2, params_tch2 = _where_clause(filters, allowed_cols=tch_cols, table_name="uae_fact_teachers_emirate")
        df_tmerge = _q(
            f"SELECT {tch_em_col2} AS __dim__, SUM({tch_cnt_col}) AS total_teachers "
            f"FROM uae.uae_fact_teachers_emirate WHERE academic_year=%s{where_tch2} "
            f"GROUP BY {tch_em_col2}",
            [UAE_YEAR] + params_tch2
        )
        if not df_tmerge.empty:
            df_tmerge = df_tmerge.rename(columns={"__dim__": merge_col})
            df = df.merge(df_tmerge, on=merge_col, how="left")

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
        df["PTR"] = df["PTR"].apply(_fmt_ptr_ratio)

    st.markdown(f"**{len(df)} rows** returned")
    st.dataframe(df, use_container_width=True)

    # Auto chart: bar if numeric column present
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    if cat_cols and num_cols:
        fig = px.bar(
            df.head(30), x=cat_cols[0], y=num_cols[0],
            color=num_cols[0], color_continuous_scale="Viridis",
            text=num_cols[0],
            labels={cat_cols[0]: cat_cols[0], num_cols[0]: num_cols[0]}
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", textfont_size=11)
        fig.update_layout(
            plot_bgcolor="#FFF", paper_bgcolor="#FFF", height=420,
            showlegend=False, coloraxis_showscale=False,
            xaxis=dict(tickangle=-45),
            margin=dict(l=60, r=220, t=80, b=120)
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    _export_buttons(df, "custom_report")

# UAE_FILTER_FRAMEWORK_FIX_v1
# UAE_GENDER_SCOPE_FIX_v2

# === INDIA_PARITY_OVERRIDE_UAE ===
def _uae_exact_multiselect(label: str, opts: list, key: str, help_text: str = '', apply_to: list | None = None, col: str | None = None):
    values = [str(x) for x in opts if str(x).strip()]
    selected = st.sidebar.multiselect(label, values, default=[], help=help_text, key=key)
    if not col:
        return None
    return {'col': col, 'val': selected, 'op': 'in', 'apply_to': apply_to or []}


def _build_sidebar_filters() -> dict:
    try:
        st.sidebar.markdown('---')
        st.sidebar.markdown('### 🔍 Apply Filters')
        enr_cols = _tbl_cols('uae_fact_enrollment')
        sch_cols = _tbl_cols('uae_fact_schools')
        tch_cols = _tbl_cols('uae_fact_teachers_emirate')
        pf_cols = _tbl_cols('uae_fact_pass_fail')

        emirate_col = _pick_col(enr_cols, 'region_en', 'emirate', 'emirate_en', 'region')
        edu_type_col = _pick_col(enr_cols, 'education_type', 'school_type', 'edu_type', 'type')
        curriculum_col = _pick_col(sch_cols, 'curriculum_en', 'curriculum', 'curriculum_type')
        gender_col = _pick_col(enr_cols, 'gender', 'student_gender')
        nat_col = _pick_col(enr_cols, 'nationality_cat', 'nationality_category', 'nationality')
        cycle_col = _pick_col(pf_cols, 'cycle', 'education_cycle', 'grade_level')

        emirates = _distinct('uae_fact_enrollment', emirate_col) if emirate_col else []
        state_value = st.sidebar.selectbox('🗺️ Select Emirate', emirates, key='uae_state_exact') if emirates else None
        curriculum_options = ['All'] + (_distinct('uae_fact_schools', curriculum_col) if curriculum_col else [])
        district_value = st.sidebar.selectbox('🏘️ Select Curriculum', curriculum_options, index=0, key='uae_district_exact') if curriculum_options else 'All'
        education_options = ['All'] + (_distinct('uae_fact_enrollment', edu_type_col) if edu_type_col else [])
        block_value = st.sidebar.selectbox('📍 Select Education Type', education_options, index=0, key='uae_block_exact') if education_options else 'All'
        gender_options = ['All'] + (_distinct('uae_fact_enrollment', gender_col) if gender_col else [])
        location_value = st.sidebar.selectbox('👥 Gender', gender_options, index=0, key='uae_location_exact') if gender_options else 'All'

        filters = {}
        if emirate_col and state_value:
            filters['state'] = {'col': emirate_col, 'val': state_value}
        if curriculum_col and district_value:
            filters['district'] = {'col': curriculum_col, 'val': district_value, 'apply_to': ['uae_fact_schools']}
        if edu_type_col and block_value:
            filters['block'] = {'col': edu_type_col, 'val': block_value}
        if gender_col and location_value:
            filters['location'] = {'col': gender_col, 'val': location_value, 'apply_to': ['uae_fact_enrollment', 'uae_fact_student_scores', 'uae_fact_pass_fail']}
        board_filter = _uae_exact_multiselect('🌐 Nationality Category', _distinct('uae_fact_enrollment', nat_col) if nat_col else [], 'uae_board_exact', 'Uses available UAE nationality-category values.', ['uae_fact_enrollment', 'uae_fact_student_nationalities'], nat_col)
        if board_filter:
            filters['boards'] = board_filter

        active = []
        for key, val in filters.items():
            if str(key).startswith('_'):
                continue
            value = val.get('val')
            if isinstance(value, list):
                active.extend(value)
            elif value not in (None, '', 'All'):
                active.append(str(value))
        if active:
            st.sidebar.markdown('---')
            st.sidebar.markdown('### ✅ Active Filters')
            for item in active:
                st.sidebar.markdown(f'- {item}')
        return filters
    except Exception as ex:
        st.sidebar.warning(f'⚠️ UAE filter error: {ex}')
        return {}
