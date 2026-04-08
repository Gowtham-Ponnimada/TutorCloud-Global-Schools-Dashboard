import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from ui_styles import inject_professional_css

NZ_SOURCES = {
    "schools_directory": "https://www.educationcounts.govt.nz/directories/list-of-nz-schools",
    "schools_directory_api": "https://www.educationcounts.govt.nz/directories/school-directory-api",
    "school_rolls": "https://www.educationcounts.govt.nz/statistics/school-rolls",
    "teacher_numbers": "https://www.educationcounts.govt.nz/statistics/teacher-numbers",
    "number_of_schools": "https://www.educationcounts.govt.nz/statistics/number-of-schools",
    "know_your_region": "https://www.educationcounts.govt.nz/know-your-region",
}

BASE_DIR = Path(__file__).resolve().parent.parent
NZ_DATA_DIR = BASE_DIR / "data" / "nz" / "processed"


def _fmt_int(value) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except Exception:
        return "—"


def _fmt_float(value, digits: int = 2) -> str:
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "—"


def _render_nz_footer():
    st.markdown(
        """
        <div style='text-align:center;color:#757575;font-size:.85rem;margin-top:2rem;'>
            <strong>TutorCloud Global Dashboard</strong><br>
            © 2026 TutorCloud. All rights reserved.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_source_links():
    st.markdown("### 🔗 Official New Zealand Data Sources")
    st.markdown(
        f"""
- [New Zealand Schools Directory]({NZ_SOURCES["schools_directory"]})
- [Schools Directory API]({NZ_SOURCES["schools_directory_api"]})
- [School Rolls]({NZ_SOURCES["school_rolls"]})
- [Teacher Numbers]({NZ_SOURCES["teacher_numbers"]})
- [Number of Schools]({NZ_SOURCES["number_of_schools"]})
- [Know Your Region]({NZ_SOURCES["know_your_region"]})
        """
    )


@st.cache_data(show_spinner=False)
def _load_nz_home_bundle():
    dim_path = NZ_DATA_DIR / "nz_dim_schools.csv"
    rolls_path = NZ_DATA_DIR / "nz_fact_school_rolls_2025.csv"
    teachers_path = NZ_DATA_DIR / "nz_fact_teachers_latest.csv"
    regional_path = NZ_DATA_DIR / "nz_agg_regional_council_summary_latest.csv"
    ta_path = NZ_DATA_DIR / "nz_agg_territorial_authority_summary_latest.csv"

    required = [dim_path, rolls_path, teachers_path, regional_path, ta_path]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        return {"ok": False, "missing": missing}

    dim = pd.read_csv(dim_path, dtype={"school_id": str})
    rolls = pd.read_csv(rolls_path, dtype={"school_id": str})
    teachers = pd.read_csv(teachers_path, dtype={"school_id": str})
    regional = pd.read_csv(regional_path)
    ta = pd.read_csv(ta_path)

    if "total_students" in rolls.columns:
        rolls["total_students"] = pd.to_numeric(rolls["total_students"], errors="coerce")

    for col in ["teacher_headcount", "teacher_ftte", "teacher_year"]:
        if col in teachers.columns:
            teachers[col] = pd.to_numeric(teachers[col], errors="coerce")

    total_regions = int(
        regional.loc[
            regional["regional_council"].fillna("").astype(str).str.strip().ne("Area Outside Region"),
            "regional_council"
        ].nunique()
    )
    total_schools = int(dim["school_id"].nunique())
    total_students = float(rolls["total_students"].fillna(0).sum())
    total_teacher_headcount = float(teachers["teacher_headcount"].fillna(0).sum())
    total_teacher_ftte = float(teachers["teacher_ftte"].fillna(0).sum())
    teacher_year = int(teachers["teacher_year"].dropna().max())

    overlap = rolls[["school_id", "total_students"]].merge(
        teachers[["school_id", "teacher_headcount", "teacher_ftte"]],
        on="school_id",
        how="inner",
    )
    overlap_students = float(overlap["total_students"].fillna(0).sum())
    overlap_teacher_headcount = float(overlap["teacher_headcount"].fillna(0).sum())
    overlap_teacher_ftte = float(overlap["teacher_ftte"].fillna(0).sum())
    overlap_schools = int(overlap["school_id"].nunique())

    ptr_ftte = overlap_students / overlap_teacher_ftte if overlap_teacher_ftte else None
    students_per_school = total_students / total_schools if total_schools else None

    regional_chart = regional.copy()
    regional_chart = regional_chart[
        regional_chart["regional_council"].fillna("").astype(str).str.strip().ne("Area Outside Region")
    ].copy()
    if "total_students_2025" in regional_chart.columns:
        regional_chart = regional_chart.sort_values("total_students_2025", ascending=False).head(10)

    ta_chart = ta.copy()
    if "total_students_2025" in ta_chart.columns:
        ta_chart = ta_chart.sort_values("total_students_2025", ascending=False).head(10)

    mapped_students = float(regional.get("total_students_2025", pd.Series(dtype=float)).fillna(0).sum())
    mapped_schools = float(regional.get("schools_with_rolls", pd.Series(dtype=float)).fillna(0).sum())

    return {
        "ok": True,
        "dim": dim,
        "rolls": rolls,
        "teachers": teachers,
        "regional": regional,
        "ta": ta,
        "regional_chart": regional_chart,
        "ta_chart": ta_chart,
        "total_regions": total_regions,
        "total_schools": total_schools,
        "total_students": total_students,
        "total_teacher_headcount": total_teacher_headcount,
        "total_teacher_ftte": total_teacher_ftte,
        "teacher_year": teacher_year,
        "ptr_ftte": ptr_ftte,
        "students_per_school": students_per_school,
        "overlap_students": overlap_students,
        "overlap_schools": overlap_schools,
        "mapped_students": mapped_students,
        "mapped_schools": mapped_schools,
    }


@st.cache_data(show_spinner=False)
def _load_nz_state_school_frame():
    dim_path = NZ_DATA_DIR / "nz_dim_schools.csv"
    rolls_path = NZ_DATA_DIR / "nz_fact_school_rolls_2025.csv"
    teachers_path = NZ_DATA_DIR / "nz_fact_teachers_latest.csv"

    required = [dim_path, rolls_path, teachers_path]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        return {"ok": False, "missing": missing}

    dim = pd.read_csv(dim_path, dtype={"school_id": str})
    rolls = pd.read_csv(rolls_path, dtype={"school_id": str})
    teachers = pd.read_csv(teachers_path, dtype={"school_id": str})

    dim_cols = [
        "school_id", "school_name", "regional_council", "territorial_authority",
        "education_region", "school_type", "authority", "gender",
        "sa2_code", "sa2_name", "latitude", "longitude", "urban_rural",
        "equity_index"
    ]
    dim = dim[[c for c in dim_cols if c in dim.columns]].copy()

    rolls_cols = ["school_id", "total_students"]
    teachers_cols = ["school_id", "teacher_year", "teacher_headcount", "teacher_ftte"]

    rolls = rolls[[c for c in rolls_cols if c in rolls.columns]].copy()
    teachers = teachers[[c for c in teachers_cols if c in teachers.columns]].copy()

    for c in ["regional_council", "territorial_authority", "education_region", "school_type", "authority", "gender", "urban_rural", "sa2_name"]:
        if c in dim.columns:
            dim[c] = dim[c].fillna("").astype(str).str.strip()

    for c in ["latitude", "longitude", "equity_index"]:
        if c in dim.columns:
            dim[c] = pd.to_numeric(dim[c], errors="coerce")

    if "total_students" in rolls.columns:
        rolls["total_students"] = pd.to_numeric(rolls["total_students"], errors="coerce")

    for c in ["teacher_year", "teacher_headcount", "teacher_ftte"]:
        if c in teachers.columns:
            teachers[c] = pd.to_numeric(teachers[c], errors="coerce")

    df = dim.merge(rolls, on="school_id", how="left").merge(teachers, on="school_id", how="left")

    df["ptr_ftte"] = df["total_students"] / df["teacher_ftte"]
    df.loc[df["teacher_ftte"].fillna(0) <= 0, "ptr_ftte"] = pd.NA

    df["students_per_school"] = df["total_students"]

    teacher_year = int(df["teacher_year"].dropna().max()) if "teacher_year" in df.columns and df["teacher_year"].notna().any() else None

    return {
        "ok": True,
        "df": df,
        "teacher_year": teacher_year,
        "roll_year": 2025,
    }



def _fmt_ptr_ratio(ptr_ratio) -> str:
    try:
        if ptr_ratio is None or pd.isna(ptr_ratio):
            return "N/A"
        ptr_ratio = float(ptr_ratio)
        if ptr_ratio <= 0:
            return "N/A"
        return f"{int(round(ptr_ratio))}:1"
    except Exception:
        return "N/A"

def render_nz_home() -> None:
    inject_professional_css()

    st.markdown(
        """
        <div class="main-header">
            <h1>🇳🇿 New Zealand Education Dashboard</h1>
            <p>National overview of schools, students, teachers, and geography-aligned education metrics for New Zealand.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bundle = _load_nz_home_bundle()
    if not bundle.get("ok", False):
        st.error("NZ Home data could not be loaded. Check the processed NZ CSV files.")
        _render_nz_footer()
        return

    def _pick_col(df: pd.DataFrame, candidates: list[str]):
        if df is None or df.empty:
            return None
        cols = set(df.columns)
        for c in candidates:
            if c in cols:
                return c
        return None

    st.markdown("## 📊 National Overview")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("TOTAL REGIONS", _fmt_int(bundle["total_regions"]))
    c2.metric("TOTAL SCHOOLS", _fmt_int(bundle["total_schools"]))
    c3.metric("TOTAL STUDENTS", _fmt_int(bundle["total_students"]))
    c4.metric(f"TOTAL TEACHERS ({bundle['teacher_year']} HC)", _fmt_int(bundle["total_teacher_headcount"]))
    c5.metric("PTR (FTTE OVERLAP)", _fmt_ptr_ratio(bundle["ptr_ftte"]))
    c6.metric("STUDENTS / SCHOOL", _fmt_float(bundle["students_per_school"], 1) if bundle["students_per_school"] is not None else "N/A")

    st.caption(
        "Students use 2025 school rolls. Teacher metrics use the latest teacher dataset available in the processed NZ files "
        f"({bundle['teacher_year']} in the current bundle). PTR is FTTE-overlap based."
    )

    s1, s2, s3 = st.columns(3)
    s1.metric("GEOCODED ROLL SCHOOLS", _fmt_int(bundle["mapped_schools"]))
    s2.metric("GEOCODED STUDENTS FOR MAPS", _fmt_int(bundle["mapped_students"]))
    s3.metric("TOTAL TEACHER FTE", _fmt_float(bundle["total_teacher_ftte"], 2))

    regional_chart = bundle.get("regional_chart", pd.DataFrame())
    ta_chart = bundle.get("ta_chart", pd.DataFrame())
    regional_full = bundle.get("regional", pd.DataFrame())

    left, right = st.columns(2)

    if regional_chart is not None and not regional_chart.empty:
        region_label_col = _pick_col(regional_chart, ["regional_council", "region", "name"])
        region_value_col = _pick_col(regional_chart, ["total_students_2025", "total_students", "students", "mapped_students"])
        if region_label_col and region_value_col:
            fig_reg = px.bar(
                regional_chart,
                x=region_value_col,
                y=region_label_col,
                orientation="h",
                title="Top Regional Councils by Students",
                color=region_value_col,
                color_continuous_scale="Blues",
            )
            fig_reg.update_layout(height=430, yaxis={"categoryorder": "total ascending"})
            left.plotly_chart(fig_reg, use_container_width=True)
        else:
            left.info("Regional student chart columns were not available in the NZ Home bundle.")
    else:
        left.info("No regional student chart data is available for NZ Home.")

    if ta_chart is not None and not ta_chart.empty:
        ta_label_col = _pick_col(ta_chart, ["territorial_authority", "ta_name", "name"])
        ta_value_col = _pick_col(ta_chart, ["total_students_2025", "total_students", "students", "mapped_students"])
        if ta_label_col and ta_value_col:
            fig_ta = px.bar(
                ta_chart,
                x=ta_value_col,
                y=ta_label_col,
                orientation="h",
                title="Top Territorial Authorities by Students",
                color=ta_value_col,
                color_continuous_scale="Tealgrn",
            )
            fig_ta.update_layout(height=430, yaxis={"categoryorder": "total ascending"})
            right.plotly_chart(fig_ta, use_container_width=True)
        else:
            right.info("Territorial authority chart columns were not available in the NZ Home bundle.")
    else:
        right.info("No territorial authority chart data is available for NZ Home.")

    st.markdown("### Top Regional Councils by School Count")

    if regional_full is not None and not regional_full.empty:
        school_region_col = _pick_col(regional_full, ["regional_council", "region", "name"])
        school_count_col = _pick_col(regional_full, ["total_schools", "schools", "school_count", "schools_in_directory", "schools_total"])
        if school_region_col and school_count_col:
            school_count_df = regional_full[[school_region_col, school_count_col]].copy()
            school_count_df = school_count_df.dropna().sort_values(school_count_col, ascending=False).head(10)
            fig_school_count = px.bar(
                school_count_df,
                x=school_count_col,
                y=school_region_col,
                orientation="h",
                title="Top Regional Councils by School Count",
                color=school_count_col,
                color_continuous_scale="Purples",
            )
            fig_school_count.update_layout(height=430, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_school_count, use_container_width=True)
        else:
            st.info("Regional school-count columns were not available in the NZ Home bundle.")
    else:
        st.info("No regional school-count summary is available for NZ Home.")

    top_region_text = "Regional comparison data is available in the charts above."
    if regional_chart is not None and not regional_chart.empty:
        rl = _pick_col(regional_chart, ["regional_council", "region", "name"])
        rv = _pick_col(regional_chart, ["total_students_2025", "total_students", "students", "mapped_students"])
        if rl and rv:
            top_row = regional_chart.iloc[0]
            top_region_text = f"{top_row[rl]} currently leads the national regional ranking with {_fmt_int(top_row[rv])} mapped students."

    st.markdown("## 💡 Key Insights")
    i1, i2, i3 = st.columns(3)

    i1.markdown(
        f"""
        <div style="background:#ffffff;border:1px solid #dbeafe;border-radius:14px;padding:18px;min-height:180px;">
            <div style="font-size:1.05rem;font-weight:700;color:#1e3a8a;margin-bottom:10px;">📚 School Coverage</div>
            <div style="font-size:0.95rem;color:#374151;line-height:1.55;">
                New Zealand Home currently covers <strong>{_fmt_int(bundle['total_schools'])}</strong> schools in the directory,
                with <strong>{_fmt_int(bundle['mapped_schools'])}</strong> geocoded roll schools supporting map-ready analytics.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    i2.markdown(
        f"""
        <div style="background:#ffffff;border:1px solid #dcfce7;border-radius:14px;padding:18px;min-height:180px;">
            <div style="font-size:1.05rem;font-weight:700;color:#166534;margin-bottom:10px;">👨‍🏫 Teaching Staff</div>
            <div style="font-size:0.95rem;color:#374151;line-height:1.55;">
                Teacher reporting currently uses the <strong>{bundle['teacher_year']}</strong> NZ teacher dataset,
                with <strong>{_fmt_int(bundle['total_teacher_headcount'])}</strong> headcount and
                <strong>{_fmt_float(bundle['total_teacher_ftte'], 2)}</strong> FTTE in the processed national bundle.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    i3.markdown(
        f"""
        <div style="background:#ffffff;border:1px solid #ede9fe;border-radius:14px;padding:18px;min-height:180px;">
            <div style="font-size:1.05rem;font-weight:700;color:#5b21b6;margin-bottom:10px;">🏫 School Size</div>
            <div style="font-size:0.95rem;color:#374151;line-height:1.55;">
                Average students per school are currently <strong>{_fmt_float(bundle['students_per_school'], 1) if bundle['students_per_school'] is not None else 'N/A'}</strong>.
                {top_region_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## 🧭 Explore More")
    e1, e2 = st.columns(2)

    e1.markdown(
        """
        <a href="/State_Dashboard?region=New%20Zealand" target="_self" style="text-decoration:none;">
            <div style="background:linear-gradient(135deg,#0ea5e9,#2563eb);color:white;border-radius:16px;padding:22px;min-height:150px;">
                <div style="font-size:1.15rem;font-weight:800;margin-bottom:10px;">📊 State Dashboard</div>
                <div style="font-size:0.97rem;line-height:1.5;">
                    Explore regional council, territorial authority, school type, authority, and gender-level NZ drilldowns.
                </div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

    e2.markdown(
        """
        <a href="/Analytics?region=New%20Zealand" target="_self" style="text-decoration:none;">
            <div style="background:linear-gradient(135deg,#10b981,#059669);color:white;border-radius:16px;padding:22px;min-height:150px;">
                <div style="font-size:1.15rem;font-weight:800;margin-bottom:10px;">📈 Analytics</div>
                <div style="font-size:0.97rem;line-height:1.5;">
                    Open NZ Geographic Maps, Performance Metrics, Comparative Analysis, and Custom Reports.
                </div>
            </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

    _render_nz_footer()


def render_nz_state_dashboard() -> None:
    inject_professional_css()

    st.markdown("# 📊 State Dashboard")
    st.markdown("**Regional Education Overview - New Zealand**")

    bundle = _load_nz_state_school_frame()
    if not bundle.get("ok", False):
        st.error("NZ state dashboard data could not be loaded.")
        _render_nz_footer()
        return

    df = bundle.get("df", pd.DataFrame()).copy()
    if df.empty:
        st.warning("No NZ state dashboard data is available.")
        _render_nz_footer()
        return

    for col in [
        "regional_council", "territorial_authority", "sa2_name", "urban_rural",
        "school_type", "authority", "gender", "education_region", "school_name"
    ]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str).str.strip()

    for col in ["school_id", "total_students", "teacher_headcount", "teacher_ftte"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # -------------------------
    # Sidebar filters (India-style structure: 8 controls)
    # -------------------------
    st.sidebar.markdown("## Filters")

    region_options = ["All"] + sorted([x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_region = st.sidebar.selectbox("🗺️ Select Regional Council", region_options, index=0, key="nz_state_region")

    district_base = df.copy()
    if selected_region != "All" and "regional_council" in district_base.columns:
        district_base = district_base[district_base["regional_council"] == selected_region]

    ta_options = ["All"] + sorted([x for x in district_base.get("territorial_authority", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_ta = st.sidebar.selectbox("🏘️ Select Territorial Authority", ta_options, index=0, key="nz_state_ta")

    block_base = district_base.copy()
    if selected_ta != "All" and "territorial_authority" in block_base.columns:
        block_base = block_base[block_base["territorial_authority"] == selected_ta]

    sa2_options = ["All"] + sorted([x for x in block_base.get("sa2_name", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_sa2 = st.sidebar.selectbox("📍 Select SA2", sa2_options, index=0, key="nz_state_sa2")

    urban_options = ["All"] + sorted([x for x in df.get("urban_rural", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_urban = st.sidebar.selectbox("🌆 Location", urban_options, index=0, key="nz_state_urban")

    school_type_options = ["All"] + sorted([x for x in df.get("school_type", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_school_type = st.sidebar.selectbox("📖 School Type", school_type_options, index=0, key="nz_state_school_type")

    authority_options = ["All"] + sorted([x for x in df.get("authority", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_authority = st.sidebar.selectbox("🏛️ Management Type", authority_options, index=0, key="nz_state_authority")

    gender_options = ["All"] + sorted([x for x in df.get("gender", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_gender = st.sidebar.selectbox("👥 Gender", gender_options, index=0, key="nz_state_gender")

    education_region_options = ["All"] + sorted([x for x in df.get("education_region", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x])
    selected_education_region = st.sidebar.selectbox("🧭 Education Region", education_region_options, index=0, key="nz_state_education_region")

    filtered = df.copy()
    if selected_region != "All" and "regional_council" in filtered.columns:
        filtered = filtered[filtered["regional_council"] == selected_region]
    if selected_ta != "All" and "territorial_authority" in filtered.columns:
        filtered = filtered[filtered["territorial_authority"] == selected_ta]
    if selected_sa2 != "All" and "sa2_name" in filtered.columns:
        filtered = filtered[filtered["sa2_name"] == selected_sa2]
    if selected_urban != "All" and "urban_rural" in filtered.columns:
        filtered = filtered[filtered["urban_rural"] == selected_urban]
    if selected_school_type != "All" and "school_type" in filtered.columns:
        filtered = filtered[filtered["school_type"] == selected_school_type]
    if selected_authority != "All" and "authority" in filtered.columns:
        filtered = filtered[filtered["authority"] == selected_authority]
    if selected_gender != "All" and "gender" in filtered.columns:
        filtered = filtered[filtered["gender"] == selected_gender]
    if selected_education_region != "All" and "education_region" in filtered.columns:
        filtered = filtered[filtered["education_region"] == selected_education_region]

    # -------------------------
    # Sidebar active filters (India-like behavior)
    # -------------------------
    active_filters = []
    if selected_region != "All":
        active_filters.append(f"Regional Council: {selected_region}")
    if selected_ta != "All":
        active_filters.append(f"Territorial Authority: {selected_ta}")
    if selected_sa2 != "All":
        active_filters.append(f"SA2: {selected_sa2}")
    if selected_urban != "All":
        active_filters.append(f"Location: {selected_urban}")
    if selected_school_type != "All":
        active_filters.append(f"School Type: {selected_school_type}")
    if selected_authority != "All":
        active_filters.append(f"Management Type: {selected_authority}")
    if selected_gender != "All":
        active_filters.append(f"Gender: {selected_gender}")
    if selected_education_region != "All":
        active_filters.append(f"Education Region: {selected_education_region}")

    if active_filters:
        st.sidebar.markdown("### Active Filters")
        for item in active_filters:
            st.sidebar.markdown(f"- {item}")

    # -------------------------
    # KPI cards (6 only, India-like)
    # -------------------------
    total_schools = int(filtered["school_id"].nunique()) if "school_id" in filtered.columns else len(filtered)
    schools_with_enrollment = int(filtered.loc[pd.to_numeric(filtered.get("total_students", 0), errors="coerce").fillna(0) > 0, "school_id"].nunique()) if "school_id" in filtered.columns and "total_students" in filtered.columns else 0
    total_tas = int(filtered["territorial_authority"].nunique()) if "territorial_authority" in filtered.columns else 0
    total_students = float(pd.to_numeric(filtered.get("total_students", 0), errors="coerce").fillna(0).sum()) if "total_students" in filtered.columns else 0
    total_teachers = float(pd.to_numeric(filtered.get("teacher_headcount", 0), errors="coerce").fillna(0).sum()) if "teacher_headcount" in filtered.columns else 0
    ptr_value = (total_students / total_teachers) if total_teachers > 0 else None

    st.markdown("## 📊 Overview")
    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)

    c1.metric("🏫 Total Schools", _fmt_int(total_schools))
    c2.metric("🎓 Schools with Enrollment", _fmt_int(schools_with_enrollment))
    c3.metric("🗺️ Territorial Authorities", _fmt_int(total_tas))
    c4.metric("📊 PTR", _fmt_ptr_ratio(ptr_value))
    c5.metric("👥 Total Students", _fmt_int(total_students))
    c6.metric("👨‍🏫 Total Teachers", _fmt_int(total_teachers))

    # -------------------------
    # Enrollment analysis (India slot equivalent)
    # -------------------------
    st.markdown("## 📚 Enrollment Analysis")

    enrollment_df = pd.DataFrame()
    if not filtered.empty and {"school_type", "gender", "total_students"}.issubset(filtered.columns):
        enrollment_df = (
            filtered.groupby(["school_type", "gender"], dropna=False, as_index=False)
            .agg(total_students=("total_students", "sum"))
        )

    if not enrollment_df.empty:
        fig_enrollment = px.bar(
            enrollment_df,
            x="school_type",
            y="total_students",
            color="gender",
            barmode="group",
            title="Enrollment by School Type and Gender",
            labels={
                "school_type": "School Type",
                "total_students": "Total Students",
                "gender": "Gender",
            },
        )
        fig_enrollment.update_layout(height=450)
        st.plotly_chart(fig_enrollment, use_container_width=True)
    else:
        st.info("Enrollment analysis is not available for the current selection.")

    # -------------------------
    # Territorial Authority PTR Analysis (India district equivalent)
    # -------------------------
    st.markdown("## 📍 Territorial Authority PTR Analysis")

    ta_summary = pd.DataFrame()
    if not filtered.empty and "territorial_authority" in filtered.columns:
        ta_summary = (
            filtered.groupby("territorial_authority", dropna=False, as_index=False)
            .agg(
                total_schools=("school_id", "nunique"),
                total_students=("total_students", "sum"),
                total_teachers=("teacher_headcount", "sum"),
            )
        )
        ta_summary["ptr"] = pd.NA
        valid_ta = pd.to_numeric(ta_summary["total_teachers"], errors="coerce").fillna(0) > 0
        ta_summary.loc[valid_ta, "ptr"] = (
            pd.to_numeric(ta_summary.loc[valid_ta, "total_students"], errors="coerce")
            / pd.to_numeric(ta_summary.loc[valid_ta, "total_teachers"], errors="coerce")
        )
        ta_summary = ta_summary.sort_values("total_schools", ascending=False).head(20)

    if not ta_summary.empty:
        fig_ta = px.bar(
            ta_summary,
            x="territorial_authority",
            y="ptr",
            title="Top 20 Territorial Authorities by School Count",
            hover_data=["total_schools", "total_students", "total_teachers"],
            labels={
                "territorial_authority": "Territorial Authority",
                "ptr": "PTR",
                "total_schools": "Total Schools",
                "total_students": "Total Students",
                "total_teachers": "Total Teachers",
            },
        )
        fig_ta.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig_ta, use_container_width=True)

        ta_display = ta_summary.copy()
        if "ptr" in ta_display.columns:
            ta_display["ptr"] = pd.to_numeric(ta_display["ptr"], errors="coerce").apply(_fmt_ptr_ratio)
        st.dataframe(ta_display, use_container_width=True, hide_index=True)

        st.download_button(
            label="📥 Download Territorial Authority Data (CSV)",
            data=ta_display.to_csv(index=False).encode("utf-8"),
            file_name="nz_state_dashboard_ta_data.csv",
            mime="text/csv",
        )
    else:
        st.info("Territorial Authority PTR analysis is not available for the current selection.")

    # -------------------------
    # SA2 PTR Analysis (India block/taluk equivalent)
    # -------------------------
    st.markdown("## 🏘️ SA2 PTR Analysis")

    sa2_summary = pd.DataFrame()
    if selected_ta != "All" and not filtered.empty and "sa2_name" in filtered.columns:
        sa2_summary = (
            filtered.groupby("sa2_name", dropna=False, as_index=False)
            .agg(
                total_schools=("school_id", "nunique"),
                total_students=("total_students", "sum"),
                total_teachers=("teacher_headcount", "sum"),
            )
        )
        sa2_summary["ptr"] = pd.NA
        valid_sa2 = pd.to_numeric(sa2_summary["total_teachers"], errors="coerce").fillna(0) > 0
        sa2_summary.loc[valid_sa2, "ptr"] = (
            pd.to_numeric(sa2_summary.loc[valid_sa2, "total_students"], errors="coerce")
            / pd.to_numeric(sa2_summary.loc[valid_sa2, "total_teachers"], errors="coerce")
        )
        sa2_summary = sa2_summary.sort_values("total_schools", ascending=False).head(20)

    if selected_ta == "All":
        st.info("Select a Territorial Authority to view SA2-level PTR analysis.")
    elif not sa2_summary.empty:
        fig_sa2 = px.bar(
            sa2_summary,
            x="sa2_name",
            y="ptr",
            title=f"Top 20 SA2 Areas in {selected_ta} by School Count",
            hover_data=["total_schools", "total_students", "total_teachers"],
            labels={
                "sa2_name": "SA2",
                "ptr": "PTR",
                "total_schools": "Total Schools",
                "total_students": "Total Students",
                "total_teachers": "Total Teachers",
            },
        )
        fig_sa2.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig_sa2, use_container_width=True)

        sa2_display = sa2_summary.copy()
        if "ptr" in sa2_display.columns:
            sa2_display["ptr"] = pd.to_numeric(sa2_display["ptr"], errors="coerce").apply(_fmt_ptr_ratio)
        st.dataframe(sa2_display, use_container_width=True, hide_index=True)

        st.download_button(
            label="📥 Download SA2 Data (CSV)",
            data=sa2_display.to_csv(index=False).encode("utf-8"),
            file_name="nz_state_dashboard_sa2_data.csv",
            mime="text/csv",
        )
    else:
        st.info("SA2-level PTR analysis is not available for the current selection.")

    _render_nz_footer()

@st.cache_data(show_spinner=False)
def _load_nz_analytics_school_frame():
    """
    Build a stable NZ analytics school-level frame.
    Prefer the cleaned NZ state bundle and enrich geo fields from nz_dim_schools.csv
    when latitude/longitude are missing or sparse.
    """
    import pandas as pd

    state_bundle = _load_nz_state_school_frame()

    if isinstance(state_bundle, dict):
        df = state_bundle.get("df")
    else:
        df = state_bundle

    if df is None:
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception:
            return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    for col in [
        "school_name",
        "regional_council",
        "territorial_authority",
        "school_type",
        "authority",
        "gender",
    ]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    for col in [
        "school_id",
        "latitude",
        "longitude",
        "total_students",
        "teacher_headcount",
        "teacher_ftte",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    need_geo = (
        "latitude" not in df.columns or
        "longitude" not in df.columns or
        df["latitude"].notna().sum() == 0 or
        df["longitude"].notna().sum() == 0
    )

    if need_geo:
        try:
            dim_path = NZ_DATA_DIR / "nz_dim_schools.csv"
            if dim_path.exists():
                dim = pd.read_csv(dim_path)

                rename_map = {}
                for c in dim.columns:
                    lc = str(c).strip().lower()
                    if lc in ("school_id", "schoolid", "school_no", "school number", "school_number"):
                        rename_map[c] = "school_id"
                    elif lc in ("school_name", "name", "school"):
                        rename_map[c] = "school_name"
                    elif lc in ("latitude", "lat"):
                        rename_map[c] = "latitude"
                    elif lc in ("longitude", "lon", "lng", "long"):
                        rename_map[c] = "longitude"
                    elif lc in ("regional_council", "regional council", "region"):
                        rename_map[c] = "regional_council"
                    elif lc in ("territorial_authority", "territorial authority", "ta"):
                        rename_map[c] = "territorial_authority"
                    elif lc in ("school_type", "type"):
                        rename_map[c] = "school_type"
                    elif lc == "authority":
                        rename_map[c] = "authority"
                    elif lc == "gender":
                        rename_map[c] = "gender"

                dim = dim.rename(columns=rename_map)

                keep_cols = [
                    c for c in [
                        "school_id",
                        "school_name",
                        "latitude",
                        "longitude",
                        "regional_council",
                        "territorial_authority",
                        "school_type",
                        "authority",
                        "gender",
                    ]
                    if c in dim.columns
                ]

                if keep_cols:
                    dim = dim[keep_cols].copy()

                    if "school_id" in dim.columns:
                        dim["school_id"] = pd.to_numeric(dim["school_id"], errors="coerce")

                    for c in ["latitude", "longitude"]:
                        if c in dim.columns:
                            dim[c] = pd.to_numeric(dim[c], errors="coerce")

                    if "school_id" in df.columns and "school_id" in dim.columns:
                        geo_cols = [c for c in dim.columns if c != "school_id"]
                        df = df.merge(dim, on="school_id", how="left", suffixes=("", "_dim"))

                        for c in geo_cols:
                            dim_col = f"{c}_dim"
                            if dim_col in df.columns:
                                if c not in df.columns:
                                    df[c] = df[dim_col]
                                else:
                                    df[c] = df[c].where(
                                        df[c].notna() & (df[c].astype(str).str.strip() != ""),
                                        df[dim_col],
                                    )
                                df.drop(columns=[dim_col], inplace=True)
        except Exception:
            pass

    for col in ["latitude", "longitude", "total_students", "teacher_headcount", "teacher_ftte"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "teacher_ftte" in df.columns and "total_students" in df.columns:
        df["ptr_ftte"] = pd.NA
        valid = (
            pd.to_numeric(df["teacher_ftte"], errors="coerce").fillna(0) > 0
        ) & pd.to_numeric(df["total_students"], errors="coerce").notna()
        df.loc[valid, "ptr_ftte"] = (
            pd.to_numeric(df.loc[valid, "total_students"], errors="coerce")
            / pd.to_numeric(df.loc[valid, "teacher_ftte"], errors="coerce")
        )
    else:
        df["ptr_ftte"] = pd.NA

    preferred = [
        "school_id",
        "school_name",
        "regional_council",
        "territorial_authority",
        "school_type",
        "authority",
        "gender",
        "latitude",
        "longitude",
        "total_students",
        "teacher_headcount",
        "teacher_ftte",
        "ptr_ftte",
    ]
    existing = [c for c in preferred if c in df.columns]
    others = [c for c in df.columns if c not in existing]
    return df[existing + others]



def render_nz_analytics() -> None:
    inject_professional_css()

    st.markdown("# 📈 Analytics Dashboard")
    st.markdown("**Advanced Educational Analytics - New Zealand**")

    df = _load_nz_analytics_school_frame()
    if df is None or df.empty:
        st.error("NZ analytics data could not be loaded.")
        _render_nz_footer()
        return

    for col in [
        "regional_council", "territorial_authority", "school_type",
        "authority", "gender", "urban_rural", "education_region", "school_name"
    ]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str).str.strip()

    for col in ["school_id", "total_students", "teacher_headcount", "teacher_ftte", "ptr_ftte"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "teacher_headcount" in df.columns:
        df["teachers_per_school_proxy"] = df["teacher_headcount"]
    else:
        df["teachers_per_school_proxy"] = pd.NA

    tabs = st.tabs([
        "🗺️ Geographic Maps",
        "🎯 Performance Metrics",
        "🔍 Comparative Analysis",
        "📝 Custom Reports"
    ])

    # =========================================================
    # TAB 1: Geographic Maps (India-style structure)
    # =========================================================
    with tabs[0]:
        metric_label = st.selectbox(
            "Select Metric to Visualize",
            ["PTR", "Students per School", "Total Students", "Total Schools"],
            index=0,
            key="nz_analytics_geo_metric"
        )

        level = st.radio(
            "Level",
            ["Regional Council", "Territorial Authority"],
            horizontal=True,
            key="nz_analytics_geo_level"
        )

        selected_region = "All"
        if level == "Territorial Authority":
            region_options = ["All"] + sorted([
                x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x
            ])
            selected_region = st.selectbox(
                "Select Regional Council",
                region_options,
                index=0,
                key="nz_analytics_geo_region"
            )

        geo_df = df.copy()
        if level == "Territorial Authority" and selected_region != "All" and "regional_council" in geo_df.columns:
            geo_df = geo_df[geo_df["regional_council"] == selected_region]

        entity_col = "regional_council" if level == "Regional Council" else "territorial_authority"
        if entity_col not in geo_df.columns:
            st.warning("Geographic data is not available for the selected level.")
        else:
            summary = (
                geo_df.groupby(entity_col, dropna=False, as_index=False)
                .agg(
                    total_schools=("school_id", "nunique"),
                    total_students=("total_students", "sum"),
                    total_teachers=("teacher_headcount", "sum"),
                )
            )

            summary["ptr"] = pd.NA
            valid_ptr = pd.to_numeric(summary["total_teachers"], errors="coerce").fillna(0) > 0
            summary.loc[valid_ptr, "ptr"] = (
                pd.to_numeric(summary.loc[valid_ptr, "total_students"], errors="coerce")
                / pd.to_numeric(summary.loc[valid_ptr, "total_teachers"], errors="coerce")
            )

            summary["students_per_school"] = pd.NA
            valid_sps = pd.to_numeric(summary["total_schools"], errors="coerce").fillna(0) > 0
            summary.loc[valid_sps, "students_per_school"] = (
                pd.to_numeric(summary.loc[valid_sps, "total_students"], errors="coerce")
                / pd.to_numeric(summary.loc[valid_sps, "total_schools"], errors="coerce")
            )

            metric_map = {
                "PTR": "ptr",
                "Students per School": "students_per_school",
                "Total Students": "total_students",
                "Total Schools": "total_schools",
            }
            metric_col = metric_map[metric_label]

            chart_df = summary.copy()
            chart_df[metric_col] = pd.to_numeric(chart_df[metric_col], errors="coerce")
            chart_df = chart_df.dropna(subset=[metric_col]).sort_values(metric_col, ascending=False).head(20)

            if chart_df.empty:
                st.info("No data is available for the selected metric and level.")
            else:
                fig_geo = px.bar(
                    chart_df,
                    x=entity_col,
                    y=metric_col,
                    title=f"Top 20 {level}s by {metric_label}",
                    hover_data=["total_schools", "total_students", "total_teachers"],
                    labels={
                        entity_col: level,
                        metric_col: metric_label,
                        "total_schools": "Total Schools",
                        "total_students": "Total Students",
                        "total_teachers": "Total Teachers",
                    },
                )
                fig_geo.update_layout(height=460, xaxis_tickangle=-45)
                st.plotly_chart(fig_geo, use_container_width=True)

                display_df = chart_df.copy()
                for c in ["ptr", "students_per_school"]:
                    if c in display_df.columns:
                        display_df[c] = pd.to_numeric(display_df[c], errors="coerce").round(2)

                display_df = display_df.rename(columns={
                    entity_col: level,
                    "total_schools": "Total Schools",
                    "total_students": "Total Students",
                    "total_teachers": "Total Teachers",
                    "ptr": "PTR",
                    "students_per_school": "Students per School",
                })
                st.dataframe(display_df, use_container_width=True, hide_index=True)

    # =========================================================
    # TAB 2: Performance Metrics (India-style structure)
    # =========================================================
    with tabs[1]:
        region_options = ["All"] + sorted([
            x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x
        ])
        selected_region = st.selectbox(
            "Select Regional Council (All for National)",
            region_options,
            index=0,
            key="nz_perf_region"
        )

        district_base = df.copy()
        if selected_region != "All" and "regional_council" in district_base.columns:
            district_base = district_base[district_base["regional_council"] == selected_region]

        ta_options = ["All"] + sorted([
            x for x in district_base.get("territorial_authority", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x
        ])
        selected_ta = st.selectbox(
            "Select Territorial Authority (All for Regional)",
            ta_options,
            index=0,
            key="nz_perf_ta"
        )

        perf_df = df.copy()
        if selected_region != "All" and "regional_council" in perf_df.columns:
            perf_df = perf_df[perf_df["regional_council"] == selected_region]
        if selected_ta != "All" and "territorial_authority" in perf_df.columns:
            perf_df = perf_df[perf_df["territorial_authority"] == selected_ta]

        total_schools = int(perf_df["school_id"].nunique()) if "school_id" in perf_df.columns else len(perf_df)
        total_students = float(pd.to_numeric(perf_df.get("total_students", 0), errors="coerce").fillna(0).sum()) if "total_students" in perf_df.columns else 0
        total_teachers = float(pd.to_numeric(perf_df.get("teacher_headcount", 0), errors="coerce").fillna(0).sum()) if "teacher_headcount" in perf_df.columns else 0
        ptr_value = (total_students / total_teachers) if total_teachers > 0 else None
        students_per_school = (total_students / total_schools) if total_schools > 0 else None
        teachers_per_school = (total_teachers / total_schools) if total_schools > 0 else None

        c1, c2, c3 = st.columns(3)
        c4, c5, c6 = st.columns(3)

        c1.metric("Total Schools", _fmt_int(total_schools))
        c2.metric("Total Students", _fmt_int(total_students))
        c3.metric("Total Teachers", _fmt_int(total_teachers))
        c4.metric("PTR", _fmt_ptr_ratio(ptr_value))
        c5.metric("Students per School", _fmt_float(students_per_school, 2) if students_per_school is not None else "N/A")
        c6.metric("Teachers per School", _fmt_float(teachers_per_school, 2) if teachers_per_school is not None else "N/A")

    # =========================================================
    # TAB 3: Comparative Analysis (India-style structure)
    # =========================================================
    with tabs[2]:
        compare_level = st.radio(
            "Comparison Level",
            ["Regional Council vs Regional Council", "Territorial Authority vs Territorial Authority"],
            key="nz_compare_level"
        )

        def _summarize(df_in):
            total_schools = int(df_in["school_id"].nunique()) if "school_id" in df_in.columns else len(df_in)
            total_students = float(pd.to_numeric(df_in.get("total_students", 0), errors="coerce").fillna(0).sum()) if "total_students" in df_in.columns else 0
            total_teachers = float(pd.to_numeric(df_in.get("teacher_headcount", 0), errors="coerce").fillna(0).sum()) if "teacher_headcount" in df_in.columns else 0
            ptr = (total_students / total_teachers) if total_teachers > 0 else None
            students_per_school = (total_students / total_schools) if total_schools > 0 else None
            return {
                "Total Schools": total_schools,
                "Total Students": total_students,
                "Total Teachers": total_teachers,
                "PTR": ptr,
                "Students/School": students_per_school,
            }

        comparison_rows = []
        compare_label_a = None
        compare_label_b = None

        if compare_level == "Regional Council vs Regional Council":
            region_options = sorted([
                x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x
            ])
            col1, col2 = st.columns(2)
            region_a = col1.selectbox("Location A", region_options, index=0, key="nz_compare_region_a")
            region_b = col2.selectbox("Location B", region_options, index=min(1, len(region_options)-1), key="nz_compare_region_b")

            if st.button("Compare", key="nz_compare_btn_region"):
                compare_label_a = region_a
                compare_label_b = region_b
                df_a = df[df["regional_council"] == region_a].copy()
                df_b = df[df["regional_council"] == region_b].copy()
                summary_a = _summarize(df_a)
                summary_b = _summarize(df_b)

                for metric in ["Total Schools", "Total Students", "Total Teachers", "PTR", "Students/School"]:
                    comparison_rows.append({
                        "Metric": metric,
                        "Location A": summary_a[metric],
                        "Location B": summary_b[metric],
                    })

        else:
            region_options = sorted([
                x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x
            ])

            c1, c2 = st.columns(2)
            region_a = c1.selectbox("Region A", region_options, index=0, key="nz_compare_ta_region_a")
            region_b = c2.selectbox("Region B", region_options, index=min(1, len(region_options)-1), key="nz_compare_ta_region_b")

            ta_options_a = sorted([
                x for x in df.loc[df["regional_council"] == region_a, "territorial_authority"].dropna().astype(str).unique().tolist() if x
            ])
            ta_options_b = sorted([
                x for x in df.loc[df["regional_council"] == region_b, "territorial_authority"].dropna().astype(str).unique().tolist() if x
            ])

            c3, c4 = st.columns(2)
            ta_a = c3.selectbox("Location A", ta_options_a, index=0, key="nz_compare_ta_a")
            ta_b = c4.selectbox("Location B", ta_options_b, index=min(1, len(ta_options_b)-1) if ta_options_b else 0, key="nz_compare_ta_b")

            if st.button("Compare", key="nz_compare_btn_ta"):
                compare_label_a = ta_a
                compare_label_b = ta_b
                df_a = df[(df["regional_council"] == region_a) & (df["territorial_authority"] == ta_a)].copy()
                df_b = df[(df["regional_council"] == region_b) & (df["territorial_authority"] == ta_b)].copy()
                summary_a = _summarize(df_a)
                summary_b = _summarize(df_b)

                for metric in ["Total Schools", "Total Students", "Total Teachers", "PTR", "Students/School"]:
                    comparison_rows.append({
                        "Metric": metric,
                        "Location A": summary_a[metric],
                        "Location B": summary_b[metric],
                    })

        if comparison_rows:
            comparison_df = pd.DataFrame(comparison_rows)
            for c in ["Location A", "Location B"]:
                comparison_df[c] = pd.to_numeric(comparison_df[c], errors="ignore")
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)

            st.download_button(
                label="Download Comparison CSV",
                data=comparison_df.to_csv(index=False).encode("utf-8"),
                file_name="nz_analytics_comparison.csv",
                mime="text/csv",
            )
        else:
            st.info("Choose comparison inputs and click Compare.")

    # =========================================================
    # TAB 4: Custom Reports (India-style structure)
    # =========================================================
    with tabs[3]:
        dimension_options = [
            "Regional Council",
            "Territorial Authority",
            "Management",
            "School Type",
            "Location",
        ]
        metric_options = [
            "Schools",
            "Students",
            "Teachers",
            "PTR",
        ]

        selected_dimensions = st.multiselect(
            "Choose grouping dimensions",
            dimension_options,
            default=["Regional Council"],
            key="nz_report_dimensions"
        )

        selected_metrics = st.multiselect(
            "Choose metrics to include",
            metric_options,
            default=["Schools", "Students"],
            key="nz_report_metrics"
        )

        generate_report = st.button("Generate Report", key="nz_generate_report")

        if generate_report:
            if not selected_dimensions:
                st.warning("Select at least one grouping dimension.")
            elif not selected_metrics:
                st.warning("Select at least one metric.")
            else:
                dimension_map = {
                    "Regional Council": "regional_council",
                    "Territorial Authority": "territorial_authority",
                    "Management": "authority",
                    "School Type": "school_type",
                    "Location": "urban_rural",
                }
                metric_map = {
                    "Schools": "schools",
                    "Students": "students",
                    "Teachers": "teachers",
                    "PTR": "ptr",
                }

                group_cols = [dimension_map[d] for d in selected_dimensions if dimension_map[d] in df.columns]
                if not group_cols:
                    st.warning("Selected grouping dimensions are not available in the current dataset.")
                else:
                    report = (
                        df.groupby(group_cols, dropna=False, as_index=False)
                        .agg(
                            schools=("school_id", "nunique"),
                            students=("total_students", "sum"),
                            teachers=("teacher_headcount", "sum"),
                        )
                    )

                    if "PTR" in selected_metrics:
                        report["ptr"] = pd.NA
                        valid = pd.to_numeric(report["teachers"], errors="coerce").fillna(0) > 0
                        report.loc[valid, "ptr"] = (
                            pd.to_numeric(report.loc[valid, "students"], errors="coerce")
                            / pd.to_numeric(report.loc[valid, "teachers"], errors="coerce")
                        )

                    keep_cols = group_cols + [metric_map[m] for m in selected_metrics if metric_map[m] in report.columns]
                    report = report[keep_cols].copy()

                    rename_map = {
                        "regional_council": "Regional Council",
                        "territorial_authority": "Territorial Authority",
                        "authority": "Management",
                        "school_type": "School Type",
                        "urban_rural": "Location",
                        "schools": "Schools",
                        "students": "Students",
                        "teachers": "Teachers",
                        "ptr": "PTR",
                    }
                    report = report.rename(columns=rename_map)

                    if "PTR" in report.columns:
                        report["PTR"] = pd.to_numeric(report["PTR"], errors="coerce").apply(_fmt_ptr_ratio)

                    st.dataframe(report, use_container_width=True, hide_index=True)

                    st.download_button(
                        label="Download CSV",
                        data=report.to_csv(index=False).encode("utf-8"),
                        file_name="nz_analytics_custom_report.csv",
                        mime="text/csv",
                    )

                    try:
                        from io import BytesIO
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine="openpyxl") as writer:
                            report.to_excel(writer, index=False, sheet_name="Report")
                        st.download_button(
                            label="Download Excel",
                            data=output.getvalue(),
                            file_name="nz_analytics_custom_report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                    except Exception:
                        st.info("Excel export is unavailable in the current environment.")

    _render_nz_footer()
