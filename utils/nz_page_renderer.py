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
    c5.metric("PTR (FTTE OVERLAP)", _fmt_float(bundle["ptr_ftte"], 2) if bundle["ptr_ftte"] is not None else "N/A")
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

    st.markdown(
        """
        <div class="main-header">
            <h1>📊 New Zealand State Dashboard</h1>
            <p>Regional council and territorial authority drilldowns for schools, students, and teacher metrics across New Zealand.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bundle = _load_nz_state_school_frame()
    if not bundle.get("ok", False):
        st.error("NZ state dashboard data could not be loaded. Check the processed NZ files.")
        _render_nz_footer()
        return

    df = bundle.get("df", pd.DataFrame()).copy()
    teacher_year = bundle.get("teacher_year")
    roll_year = bundle.get("roll_year", 2025)

    if df.empty:
        st.warning("NZ state dashboard data frame is empty.")
        _render_nz_footer()
        return

    for col in ["school_id", "total_students", "teacher_headcount", "teacher_ftte", "ptr_ftte"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["regional_council", "territorial_authority", "school_type", "authority", "gender", "school_name"]:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str).str.strip()

    st.caption(
        f"Students use {roll_year} school rolls. Teacher metrics use the latest teacher dataset available in the processed NZ bundle "
        f"({teacher_year} where available). PTR values are FTTE-overlap based."
    )

    # -------------------------
    # Filters
    # -------------------------
    f1, f2, f3, f4, f5 = st.columns(5)

    region_options = ["All"] + sorted([x for x in df["regional_council"].dropna().astype(str).unique().tolist() if x])
    selected_region = f1.selectbox("Regional Council", region_options, index=0, key="nz_state_region_filter")

    ta_base = df.copy()
    if selected_region != "All":
        ta_base = ta_base[ta_base["regional_council"] == selected_region]

    ta_options = ["All"] + sorted([x for x in ta_base["territorial_authority"].dropna().astype(str).unique().tolist() if x])
    selected_ta = f2.selectbox("Territorial Authority", ta_options, index=0, key="nz_state_ta_filter")

    type_options = ["All"] + sorted([x for x in df["school_type"].dropna().astype(str).unique().tolist() if x])
    selected_type = f3.selectbox("School Type", type_options, index=0, key="nz_state_type_filter")

    authority_options = ["All"] + sorted([x for x in df["authority"].dropna().astype(str).unique().tolist() if x])
    selected_authority = f4.selectbox("Authority", authority_options, index=0, key="nz_state_authority_filter")

    gender_options = ["All"] + sorted([x for x in df["gender"].dropna().astype(str).unique().tolist() if x])
    selected_gender = f5.selectbox("Gender", gender_options, index=0, key="nz_state_gender_filter")

    filtered = df.copy()
    if selected_region != "All":
        filtered = filtered[filtered["regional_council"] == selected_region]
    if selected_ta != "All":
        filtered = filtered[filtered["territorial_authority"] == selected_ta]
    if selected_type != "All":
        filtered = filtered[filtered["school_type"] == selected_type]
    if selected_authority != "All":
        filtered = filtered[filtered["authority"] == selected_authority]
    if selected_gender != "All":
        filtered = filtered[filtered["gender"] == selected_gender]

    # -------------------------
    # Active Filters
    # -------------------------
    active_filters = []
    if selected_region != "All":
        active_filters.append(f"Regional Council: {selected_region}")
    if selected_ta != "All":
        active_filters.append(f"Territorial Authority: {selected_ta}")
    if selected_type != "All":
        active_filters.append(f"School Type: {selected_type}")
    if selected_authority != "All":
        active_filters.append(f"Authority: {selected_authority}")
    if selected_gender != "All":
        active_filters.append(f"Gender: {selected_gender}")

    if active_filters:
        st.markdown("### ✅ Active Filters")
        af_cols = st.columns(min(3, len(active_filters)))
        for idx, label in enumerate(active_filters):
            af_cols[idx % len(af_cols)].markdown(
                f"""
                <div style="background:#f8fafc;border:1px solid #dbeafe;border-radius:12px;padding:10px 12px;margin-bottom:8px;">
                    <div style="font-size:0.92rem;color:#1f2937;font-weight:600;">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -------------------------
    # KPI calculations
    # -------------------------
    total_regions = int(filtered["regional_council"].nunique()) if "regional_council" in filtered.columns else 0
    total_tas = int(filtered["territorial_authority"].nunique()) if "territorial_authority" in filtered.columns else 0
    total_schools = int(filtered["school_id"].nunique()) if "school_id" in filtered.columns else len(filtered)
    total_students = float(filtered["total_students"].fillna(0).sum()) if "total_students" in filtered.columns else 0
    total_teacher_ftte = float(filtered["teacher_ftte"].fillna(0).sum()) if "teacher_ftte" in filtered.columns else 0
    total_teacher_headcount = float(filtered["teacher_headcount"].fillna(0).sum()) if "teacher_headcount" in filtered.columns else 0
    schools_with_teacher_data = int(filtered.loc[filtered["teacher_ftte"].fillna(0) > 0, "school_id"].nunique()) if {"teacher_ftte", "school_id"}.issubset(filtered.columns) else 0
    ptr_ftte = (total_students / total_teacher_ftte) if total_teacher_ftte > 0 else None
    students_per_school = (total_students / total_schools) if total_schools > 0 else None

    st.markdown("## 📊 Overview")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("REGIONS", _fmt_int(total_regions))
    k2.metric("TERRITORIAL AUTHORITIES", _fmt_int(total_tas))
    k3.metric("SCHOOLS", _fmt_int(total_schools))
    k4.metric("STUDENTS", _fmt_int(total_students))
    k5.metric("TEACHER FTTE", _fmt_float(total_teacher_ftte, 2))
    k6.metric("PTR (FTTE)", _fmt_float(ptr_ftte, 2) if ptr_ftte is not None else "N/A")

    k7, k8, k9 = st.columns(3)
    k7.metric("TEACHER HEADCOUNT", _fmt_int(total_teacher_headcount))
    k8.metric("STUDENTS / SCHOOL", _fmt_float(students_per_school, 1) if students_per_school is not None else "N/A")
    k9.metric("SCHOOLS WITH TEACHER DATA", _fmt_int(schools_with_teacher_data))

    # -------------------------
    # Territorial Authority summary
    # -------------------------
    ta_summary = pd.DataFrame()
    if not filtered.empty and "territorial_authority" in filtered.columns:
        ta_summary = (
            filtered.groupby(["regional_council", "territorial_authority"], dropna=False, as_index=False)
            .agg(
                schools=("school_id", "nunique"),
                total_students=("total_students", "sum"),
                teacher_headcount=("teacher_headcount", "sum"),
                teacher_ftte=("teacher_ftte", "sum"),
            )
        )
        ta_summary["ptr_ftte"] = pd.NA
        valid_ptr = pd.to_numeric(ta_summary["teacher_ftte"], errors="coerce").fillna(0) > 0
        ta_summary.loc[valid_ptr, "ptr_ftte"] = (
            pd.to_numeric(ta_summary.loc[valid_ptr, "total_students"], errors="coerce")
            / pd.to_numeric(ta_summary.loc[valid_ptr, "teacher_ftte"], errors="coerce")
        )
        ta_summary["students_per_school"] = pd.NA
        valid_sps = pd.to_numeric(ta_summary["schools"], errors="coerce").fillna(0) > 0
        ta_summary.loc[valid_sps, "students_per_school"] = (
            pd.to_numeric(ta_summary.loc[valid_sps, "total_students"], errors="coerce")
            / pd.to_numeric(ta_summary.loc[valid_sps, "schools"], errors="coerce")
        )
        ta_summary = ta_summary.sort_values("total_students", ascending=False)

    # -------------------------
    # School type summary
    # -------------------------
    school_type_summary = pd.DataFrame()
    if not filtered.empty and "school_type" in filtered.columns:
        school_type_summary = (
            filtered.groupby("school_type", dropna=False, as_index=False)
            .agg(
                schools=("school_id", "nunique"),
                total_students=("total_students", "sum"),
                teacher_ftte=("teacher_ftte", "sum"),
            )
            .sort_values("total_students", ascending=False)
        )

    # -------------------------
    # Authority summary
    # -------------------------
    authority_summary = pd.DataFrame()
    if not filtered.empty and "authority" in filtered.columns:
        authority_summary = (
            filtered.groupby("authority", dropna=False, as_index=False)
            .agg(
                schools=("school_id", "nunique"),
                total_students=("total_students", "sum"),
                teacher_headcount=("teacher_headcount", "sum"),
                teacher_ftte=("teacher_ftte", "sum"),
            )
            .sort_values("teacher_ftte", ascending=False)
        )

    # -------------------------
    # Charts
    # -------------------------
    c1, c2 = st.columns(2)

    if not ta_summary.empty:
        ta_top = ta_summary.head(15).copy()
        fig_ta_students = px.bar(
            ta_top,
            x="total_students",
            y="territorial_authority",
            orientation="h",
            color="regional_council",
            title="Top Territorial Authorities in Current Selection",
            labels={"total_students": "Students", "territorial_authority": "Territorial Authority"},
        )
        fig_ta_students.update_layout(height=460, yaxis={"categoryorder": "total ascending"})
        c1.plotly_chart(fig_ta_students, use_container_width=True)
    else:
        c1.info("No territorial authority student summary is available for the current selection.")

    if not school_type_summary.empty:
        fig_school_type = px.bar(
            school_type_summary,
            x="school_type",
            y="total_students",
            color="schools",
            title="Student Distribution by School Type",
            labels={"school_type": "School Type", "total_students": "Students", "schools": "Schools"},
        )
        fig_school_type.update_layout(height=460)
        c2.plotly_chart(fig_school_type, use_container_width=True)
    else:
        c2.info("No school-type summary is available for the current selection.")

    c3, c4 = st.columns(2)

    if not ta_summary.empty:
        ptr_df = ta_summary.copy()
        ptr_df["ptr_ftte"] = pd.to_numeric(ptr_df["ptr_ftte"], errors="coerce")
        ptr_df = ptr_df.dropna(subset=["ptr_ftte"]).sort_values("ptr_ftte", ascending=False).head(15)
        if not ptr_df.empty:
            fig_ptr = px.bar(
                ptr_df,
                x="ptr_ftte",
                y="territorial_authority",
                orientation="h",
                color="teacher_ftte",
                title="PTR (FTTE) by Territorial Authority",
                labels={"ptr_ftte": "PTR (FTTE)", "territorial_authority": "Territorial Authority", "teacher_ftte": "Teacher FTTE"},
            )
            fig_ptr.update_layout(height=460, yaxis={"categoryorder": "total ascending"})
            c3.plotly_chart(fig_ptr, use_container_width=True)
        else:
            c3.info("No territorial-authority PTR values are available for the current selection.")
    else:
        c3.info("No territorial-authority PTR summary is available for the current selection.")

    if not authority_summary.empty:
        fig_auth = px.bar(
            authority_summary,
            x="authority",
            y="teacher_ftte",
            color="total_students",
            title="Teacher FTTE by Authority",
            labels={"authority": "Authority", "teacher_ftte": "Teacher FTTE", "total_students": "Students"},
        )
        fig_auth.update_layout(height=460)
        c4.plotly_chart(fig_auth, use_container_width=True)
    else:
        c4.info("No authority summary is available for the current selection.")

    # -------------------------
    # Summary tables
    # -------------------------
    st.markdown("### Territorial Authority Summary")
    if not ta_summary.empty:
        ta_display = ta_summary.copy()
        for col in ["teacher_ftte", "ptr_ftte", "students_per_school"]:
            if col in ta_display.columns:
                ta_display[col] = pd.to_numeric(ta_display[col], errors="coerce").round(2)
        st.dataframe(ta_display, use_container_width=True, hide_index=True)

        ta_csv = ta_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download territorial authority summary (CSV)",
            data=ta_csv,
            file_name="nz_state_dashboard_ta_summary.csv",
            mime="text/csv",
        )
    else:
        st.info("No territorial authority summary table is available for the current selection.")

    st.markdown("### Authority Summary")
    if not authority_summary.empty:
        auth_display = authority_summary.copy()
        if "teacher_ftte" in auth_display.columns:
            auth_display["teacher_ftte"] = pd.to_numeric(auth_display["teacher_ftte"], errors="coerce").round(2)
        st.dataframe(auth_display, use_container_width=True, hide_index=True)
    else:
        st.info("No authority summary table is available for the current selection.")

    if not school_type_summary.empty:
        school_type_csv = school_type_summary.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download school type summary (CSV)",
            data=school_type_csv,
            file_name="nz_state_dashboard_school_type_summary.csv",
            mime="text/csv",
        )

    # -------------------------
    # School detail table
    # -------------------------
    st.markdown("### School Detail")
    detail_cols = [
        c for c in [
            "school_name",
            "regional_council",
            "territorial_authority",
            "school_type",
            "authority",
            "gender",
            "total_students",
            "teacher_headcount",
            "teacher_ftte",
            "ptr_ftte",
        ] if c in filtered.columns
    ]
    detail_df = filtered[detail_cols].copy() if detail_cols else filtered.copy()

    if "ptr_ftte" in detail_df.columns:
        detail_df["ptr_ftte"] = pd.to_numeric(detail_df["ptr_ftte"], errors="coerce").round(2)
    if "teacher_ftte" in detail_df.columns:
        detail_df["teacher_ftte"] = pd.to_numeric(detail_df["teacher_ftte"], errors="coerce").round(2)
    if "total_students" in detail_df.columns:
        detail_df = detail_df.sort_values("total_students", ascending=False)

    st.dataframe(detail_df, use_container_width=True, hide_index=True)

    school_csv = detail_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download filtered NZ state dashboard data (CSV)",
        data=school_csv,
        file_name="nz_state_dashboard_filtered.csv",
        mime="text/csv",
    )

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

    st.markdown(
        """
        <div class="main-header">
            <h1>📈 New Zealand Analytics Dashboard</h1>
            <p>Geographic maps, performance metrics, comparative analysis, and custom reporting for New Zealand schools.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df = _load_nz_analytics_school_frame()
    if df.empty:
        st.error(
            "NZ analytics data could not be loaded. Ensure the processed NZ files exist and the NZ state school frame builds successfully."
        )
        _render_nz_footer()
        return

    st.caption(
        "Students use 2025 school rolls. Teacher metrics use the latest teacher dataset (2024 where available). "
        "PTR values are FTTE-overlap based and shown only where teacher FTTE exists."
    )

    tabs = st.tabs([
        "🗺️ Geographic Maps",
        "🎯 Performance Metrics",
        "🔍 Comparative Analysis",
        "📝 Custom Reports"
    ])

    with tabs[0]:
        st.markdown("## 🗺️ Geographic Maps")

        f1, f2, f3, f4, f5 = st.columns(5)

        region_options = ["All"] + sorted(
            [x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        selected_region = f1.selectbox(
            "Regional Council",
            region_options,
            index=0,
            key="nz_analytics_geo_region",
        )

        ta_base = df.copy()
        if selected_region != "All" and "regional_council" in ta_base.columns:
            ta_base = ta_base[ta_base["regional_council"] == selected_region]

        ta_options = ["All"] + sorted(
            [x for x in ta_base.get("territorial_authority", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        selected_ta = f2.selectbox(
            "Territorial Authority",
            ta_options,
            index=0,
            key="nz_analytics_geo_ta",
        )

        type_options = ["All"] + sorted(
            [x for x in df.get("school_type", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        selected_type = f3.selectbox(
            "School Type",
            type_options,
            index=0,
            key="nz_analytics_geo_type",
        )

        authority_options = ["All"] + sorted(
            [x for x in df.get("authority", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        selected_authority = f4.selectbox(
            "Authority",
            authority_options,
            index=0,
            key="nz_analytics_geo_authority",
        )

        gender_options = ["All"] + sorted(
            [x for x in df.get("gender", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        selected_gender = f5.selectbox(
            "Gender",
            gender_options,
            index=0,
            key="nz_analytics_geo_gender",
        )

        filtered = df.copy()

        if selected_region != "All" and "regional_council" in filtered.columns:
            filtered = filtered[filtered["regional_council"] == selected_region]
        if selected_ta != "All" and "territorial_authority" in filtered.columns:
            filtered = filtered[filtered["territorial_authority"] == selected_ta]
        if selected_type != "All" and "school_type" in filtered.columns:
            filtered = filtered[filtered["school_type"] == selected_type]
        if selected_authority != "All" and "authority" in filtered.columns:
            filtered = filtered[filtered["authority"] == selected_authority]
        if selected_gender != "All" and "gender" in filtered.columns:
            filtered = filtered[filtered["gender"] == selected_gender]

        geo_df = filtered.copy()
        if "latitude" in geo_df.columns and "longitude" in geo_df.columns:
            geo_df = geo_df.dropna(subset=["latitude", "longitude"])
        else:
            geo_df = pd.DataFrame()

        k1, k2, k3, k4 = st.columns(4)
        mapped_schools = int(geo_df["school_id"].nunique()) if not geo_df.empty and "school_id" in geo_df.columns else 0
        mapped_students = float(geo_df["total_students"].fillna(0).sum()) if not geo_df.empty and "total_students" in geo_df.columns else 0
        mapped_tas = int(geo_df["territorial_authority"].nunique()) if not geo_df.empty and "territorial_authority" in geo_df.columns else 0
        mapped_ftte = float(geo_df["teacher_ftte"].fillna(0).sum()) if not geo_df.empty and "teacher_ftte" in geo_df.columns else 0

        k1.metric("MAPPED SCHOOLS", _fmt_int(mapped_schools))
        k2.metric("MAPPED STUDENTS", _fmt_int(mapped_students))
        k3.metric("MAPPED TERRITORIAL AUTHORITIES", _fmt_int(mapped_tas))
        k4.metric("MAPPED TEACHER FTTE", _fmt_float(mapped_ftte, 2))

        if geo_df.empty:
            st.info("No geocoded schools are available for the current analytics map selection.")
        else:
            map_df = geo_df.copy()
            if "total_students" in map_df.columns:
                map_df["marker_size"] = map_df["total_students"].fillna(0).clip(lower=1)
            else:
                map_df["marker_size"] = 1

            hover_cols = []
            for c in ["regional_council", "territorial_authority", "school_type", "authority", "gender", "total_students", "teacher_ftte", "ptr_ftte"]:
                if c in map_df.columns:
                    hover_cols.append(c)

            color_col = "school_type" if "school_type" in map_df.columns else None

            fig = px.scatter_mapbox(
                map_df,
                lat="latitude",
                lon="longitude",
                hover_name="school_name" if "school_name" in map_df.columns else None,
                hover_data=hover_cols,
                color=color_col,
                size="marker_size",
                size_max=22,
                zoom=4.3,
                height=560,
                mapbox_style="open-street-map",
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                legend_title_text="School Type" if color_col == "school_type" else "",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Filtered School Extract")

        display_cols = [
            c for c in [
                "school_name",
                "regional_council",
                "territorial_authority",
                "school_type",
                "authority",
                "gender",
                "total_students",
                "teacher_headcount",
                "teacher_ftte",
                "ptr_ftte",
                "latitude",
                "longitude",
            ] if c in filtered.columns
        ]

        table_df = filtered[display_cols].copy() if display_cols else filtered.copy()

        if "ptr_ftte" in table_df.columns:
            table_df["ptr_ftte"] = pd.to_numeric(table_df["ptr_ftte"], errors="coerce").round(2)
        if "teacher_ftte" in table_df.columns:
            table_df["teacher_ftte"] = pd.to_numeric(table_df["teacher_ftte"], errors="coerce").round(2)

        st.dataframe(table_df, use_container_width=True, hide_index=True)

        csv_data = table_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download filtered NZ analytics school extract (CSV)",
            data=csv_data,
            file_name="nz_analytics_geographic_maps_filtered_school_extract.csv",
            mime="text/csv",
        )

    with tabs[1]:
        st.markdown("### Performance Metrics")

        pf1, pf2, pf3, pf4, pf5 = st.columns(5)

        perf_region_options = ["All"] + sorted(
            [x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        perf_region = pf1.selectbox(
            "Regional Council",
            perf_region_options,
            index=0,
            key="nz_analytics_perf_region",
        )

        perf_ta_base = df.copy()
        if perf_region != "All" and "regional_council" in perf_ta_base.columns:
            perf_ta_base = perf_ta_base[perf_ta_base["regional_council"] == perf_region]

        perf_ta_options = ["All"] + sorted(
            [x for x in perf_ta_base.get("territorial_authority", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        perf_ta = pf2.selectbox(
            "Territorial Authority",
            perf_ta_options,
            index=0,
            key="nz_analytics_perf_ta",
        )

        perf_type_options = ["All"] + sorted(
            [x for x in df.get("school_type", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        perf_type = pf3.selectbox(
            "School Type",
            perf_type_options,
            index=0,
            key="nz_analytics_perf_type",
        )

        perf_authority_options = ["All"] + sorted(
            [x for x in df.get("authority", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        perf_authority = pf4.selectbox(
            "Authority",
            perf_authority_options,
            index=0,
            key="nz_analytics_perf_authority",
        )

        perf_gender_options = ["All"] + sorted(
            [x for x in df.get("gender", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        perf_gender = pf5.selectbox(
            "Gender",
            perf_gender_options,
            index=0,
            key="nz_analytics_perf_gender",
        )

        perf_df = df.copy()
        if perf_region != "All" and "regional_council" in perf_df.columns:
            perf_df = perf_df[perf_df["regional_council"] == perf_region]
        if perf_ta != "All" and "territorial_authority" in perf_df.columns:
            perf_df = perf_df[perf_df["territorial_authority"] == perf_ta]
        if perf_type != "All" and "school_type" in perf_df.columns:
            perf_df = perf_df[perf_df["school_type"] == perf_type]
        if perf_authority != "All" and "authority" in perf_df.columns:
            perf_df = perf_df[perf_df["authority"] == perf_authority]
        if perf_gender != "All" and "gender" in perf_df.columns:
            perf_df = perf_df[perf_df["gender"] == perf_gender]

        total_schools = int(perf_df["school_id"].nunique()) if "school_id" in perf_df.columns else len(perf_df)
        total_students = float(perf_df["total_students"].fillna(0).sum()) if "total_students" in perf_df.columns else 0
        total_ftte = float(perf_df["teacher_ftte"].fillna(0).sum()) if "teacher_ftte" in perf_df.columns else 0
        total_hc = float(perf_df["teacher_headcount"].fillna(0).sum()) if "teacher_headcount" in perf_df.columns else 0
        ptr_ftte = (total_students / total_ftte) if total_ftte > 0 else None
        students_per_school = (total_students / total_schools) if total_schools > 0 else None

        k1, k2, k3 = st.columns(3)
        k4, k5, k6 = st.columns(3)

        k1.metric("SCHOOLS", _fmt_int(total_schools))
        k2.metric("STUDENTS", _fmt_int(total_students))
        k3.metric("TEACHER FTTE", _fmt_float(total_ftte, 2))
        k4.metric("PTR (FTTE)", _fmt_float(ptr_ftte, 2) if ptr_ftte is not None else "N/A")
        k5.metric("STUDENTS / SCHOOL", _fmt_float(students_per_school, 1) if students_per_school is not None else "N/A")
        k6.metric("TEACHER HEADCOUNT", _fmt_int(total_hc))

        c1, c2 = st.columns(2)

        if not perf_df.empty and {"school_type", "total_students"}.issubset(perf_df.columns):
            school_type_summary = (
                perf_df.groupby("school_type", dropna=False, as_index=False)
                .agg(
                    total_students=("total_students", "sum"),
                    schools=("school_id", "nunique") if "school_id" in perf_df.columns else ("school_type", "size")
                )
                .sort_values("total_students", ascending=False)
            )
            fig_type = px.bar(
                school_type_summary,
                x="school_type",
                y="total_students",
                color="schools",
                title="Students by School Type",
                labels={"school_type": "School Type", "total_students": "Students", "schools": "Schools"},
            )
            fig_type.update_layout(height=420)
            c1.plotly_chart(fig_type, use_container_width=True)
        else:
            c1.info("No school-type student distribution is available for the current selection.")

        if not perf_df.empty and {"regional_council", "total_students"}.issubset(perf_df.columns):
            region_summary = (
                perf_df.groupby("regional_council", dropna=False, as_index=False)
                .agg(
                    total_students=("total_students", "sum"),
                    teacher_ftte=("teacher_ftte", "sum") if "teacher_ftte" in perf_df.columns else ("total_students", "sum")
                )
                .sort_values("total_students", ascending=False)
                .head(15)
            )
            fig_region = px.bar(
                region_summary,
                x="regional_council",
                y="total_students",
                color="teacher_ftte" if "teacher_ftte" in region_summary.columns else None,
                title="Students by Regional Council",
                labels={"regional_council": "Regional Council", "total_students": "Students", "teacher_ftte": "Teacher FTTE"},
            )
            fig_region.update_layout(height=420)
            c2.plotly_chart(fig_region, use_container_width=True)
        else:
            c2.info("No regional student distribution is available for the current selection.")

        c3, c4 = st.columns(2)

        if not perf_df.empty and {"regional_council", "total_students", "teacher_ftte"}.issubset(perf_df.columns):
            ptr_region = (
                perf_df.groupby("regional_council", dropna=False, as_index=False)
                .agg(
                    total_students=("total_students", "sum"),
                    teacher_ftte=("teacher_ftte", "sum"),
                )
            )
            ptr_region = ptr_region[ptr_region["teacher_ftte"].fillna(0) > 0].copy()
            if not ptr_region.empty:
                ptr_region["ptr_ftte"] = ptr_region["total_students"] / ptr_region["teacher_ftte"]
                ptr_region = ptr_region.sort_values("ptr_ftte", ascending=False).head(15)
                fig_ptr = px.bar(
                    ptr_region,
                    x="regional_council",
                    y="ptr_ftte",
                    color="teacher_ftte",
                    title="PTR (FTTE) by Regional Council",
                    labels={"regional_council": "Regional Council", "ptr_ftte": "PTR (FTTE)", "teacher_ftte": "Teacher FTTE"},
                )
                fig_ptr.update_layout(height=420)
                c3.plotly_chart(fig_ptr, use_container_width=True)
            else:
                c3.info("No PTR (FTTE) values are available for the current regional selection.")
        else:
            c3.info("No PTR (FTTE) regional summary is available for the current selection.")

        if not perf_df.empty and {"authority", "teacher_ftte"}.issubset(perf_df.columns):
            authority_summary = (
                perf_df.groupby("authority", dropna=False, as_index=False)
                .agg(
                    teacher_ftte=("teacher_ftte", "sum"),
                    total_students=("total_students", "sum") if "total_students" in perf_df.columns else ("teacher_ftte", "sum")
                )
                .sort_values("teacher_ftte", ascending=False)
            )
            fig_auth = px.bar(
                authority_summary,
                x="authority",
                y="teacher_ftte",
                color="total_students",
                title="Teacher FTTE by Authority",
                labels={"authority": "Authority", "teacher_ftte": "Teacher FTTE", "total_students": "Students"},
            )
            fig_auth.update_layout(height=420)
            c4.plotly_chart(fig_auth, use_container_width=True)
        else:
            c4.info("No authority-level teacher summary is available for the current selection.")

        st.markdown("### Performance Metrics Table")

        perf_table_cols = [
            c for c in [
                "school_name",
                "regional_council",
                "territorial_authority",
                "school_type",
                "authority",
                "gender",
                "total_students",
                "teacher_headcount",
                "teacher_ftte",
                "ptr_ftte",
            ] if c in perf_df.columns
        ]

        perf_table = perf_df[perf_table_cols].copy() if perf_table_cols else perf_df.copy()

        if "total_students" in perf_table.columns:
            perf_table = perf_table.sort_values("total_students", ascending=False)
        if "ptr_ftte" in perf_table.columns:
            perf_table["ptr_ftte"] = pd.to_numeric(perf_table["ptr_ftte"], errors="coerce").round(2)
        if "teacher_ftte" in perf_table.columns:
            perf_table["teacher_ftte"] = pd.to_numeric(perf_table["teacher_ftte"], errors="coerce").round(2)

        st.dataframe(perf_table, use_container_width=True, hide_index=True)

        perf_csv = perf_table.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download NZ analytics performance metrics table (CSV)",
            data=perf_csv,
            file_name="nz_analytics_performance_metrics.csv",
            mime="text/csv",
        )

    with tabs[2]:
        st.markdown("### Comparative Analysis")

        csel1, csel2, csel3 = st.columns(3)

        compare_level = csel1.selectbox(
            "Comparison Level",
            [
                "Regional Council vs Regional Council",
                "Territorial Authority vs Territorial Authority",
            ],
            index=0,
            key="nz_analytics_compare_level",
        )

        scope_region_options = ["All"] + sorted(
            [x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        scope_region = csel2.selectbox(
            "Scope Regional Council",
            scope_region_options,
            index=0,
            key="nz_analytics_compare_scope_region",
        )

        compare_note = (
            "Compare two regional councils or two territorial authorities using the filtered NZ school, student, and teacher data. "
            "Students use 2025 rolls; PTR uses FTTE-overlap where teacher FTTE exists."
        )
        csel3.markdown(
            f"""
            <div style="padding-top: 0.4rem;">
                <div style="font-size:0.82rem;color:#6b7280;font-weight:600;">Comparison Notes</div>
                <div style="font-size:0.9rem;color:#374151;line-height:1.35;">{compare_note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        base_cmp = df.copy()
        if scope_region != "All" and "regional_council" in base_cmp.columns:
            base_cmp = base_cmp[base_cmp["regional_council"] == scope_region]

        if compare_level == "Regional Council vs Regional Council":
            label_col = "regional_council"
            compare_title = "Regional Council Comparison"
        else:
            label_col = "territorial_authority"
            compare_title = "Territorial Authority Comparison"

        compare_options = sorted(
            [x for x in base_cmp.get(label_col, pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )

        if len(compare_options) < 2:
            st.info("Not enough locations are available for comparison under the current selection.")
        else:
            loc1_col, loc2_col = st.columns(2)
            location_a = loc1_col.selectbox(
                "Location A",
                compare_options,
                index=0,
                key="nz_analytics_compare_location_a",
            )
            default_b_index = 1 if len(compare_options) > 1 else 0
            location_b = loc2_col.selectbox(
                "Location B",
                compare_options,
                index=default_b_index,
                key="nz_analytics_compare_location_b",
            )

            def _cmp_summary(frame: pd.DataFrame, label: str) -> dict:
                schools = int(frame["school_id"].nunique()) if "school_id" in frame.columns else len(frame)
                students = float(frame["total_students"].fillna(0).sum()) if "total_students" in frame.columns else 0
                teacher_hc = float(frame["teacher_headcount"].fillna(0).sum()) if "teacher_headcount" in frame.columns else 0
                teacher_ftte = float(frame["teacher_ftte"].fillna(0).sum()) if "teacher_ftte" in frame.columns else 0
                ptr_ftte = (students / teacher_ftte) if teacher_ftte > 0 else None
                students_per_school = (students / schools) if schools > 0 else None
                territorial_authorities = int(frame["territorial_authority"].nunique()) if "territorial_authority" in frame.columns else None

                return {
                    "Location": label,
                    "Schools": schools,
                    "Students": students,
                    "Teacher Headcount": teacher_hc,
                    "Teacher FTTE": teacher_ftte,
                    "PTR (FTTE)": ptr_ftte,
                    "Students / School": students_per_school,
                    "Territorial Authorities": territorial_authorities,
                }

            frame_a = base_cmp[base_cmp[label_col] == location_a].copy()
            frame_b = base_cmp[base_cmp[label_col] == location_b].copy()

            summary_a = _cmp_summary(frame_a, location_a)
            summary_b = _cmp_summary(frame_b, location_b)

            if location_a == location_b:
                st.warning("Location A and Location B are the same. Select two different locations for a meaningful comparison.")

            k1, k2, k3 = st.columns(3)
            k4, k5, k6 = st.columns(3)

            k1.metric(f"{location_a} — Students", _fmt_int(summary_a["Students"]))
            k2.metric(f"{location_b} — Students", _fmt_int(summary_b["Students"]))
            student_delta = summary_b["Students"] - summary_a["Students"]
            k3.metric("Student Delta (B - A)", _fmt_int(student_delta))

            k4.metric(
                f"{location_a} — PTR (FTTE)",
                _fmt_float(summary_a["PTR (FTTE)"], 2) if summary_a["PTR (FTTE)"] is not None else "N/A"
            )
            k5.metric(
                f"{location_b} — PTR (FTTE)",
                _fmt_float(summary_b["PTR (FTTE)"], 2) if summary_b["PTR (FTTE)"] is not None else "N/A"
            )
            ptr_delta = (
                summary_b["PTR (FTTE)"] - summary_a["PTR (FTTE)"]
                if summary_a["PTR (FTTE)"] is not None and summary_b["PTR (FTTE)"] is not None
                else None
            )
            k6.metric("PTR Delta (B - A)", _fmt_float(ptr_delta, 2) if ptr_delta is not None else "N/A")

            chart_rows = []
            for metric in ["Schools", "Students", "Teacher Headcount", "Teacher FTTE", "PTR (FTTE)", "Students / School"]:
                chart_rows.append({"Metric": metric, "Location": location_a, "Value": summary_a[metric]})
                chart_rows.append({"Metric": metric, "Location": location_b, "Value": summary_b[metric]})

            chart_df = pd.DataFrame(chart_rows)
            chart_df["Value"] = pd.to_numeric(chart_df["Value"], errors="coerce")

            fig_cmp = px.bar(
                chart_df,
                x="Metric",
                y="Value",
                color="Location",
                barmode="group",
                title=compare_title,
                labels={"Metric": "Metric", "Value": "Value"},
            )
            fig_cmp.update_layout(height=460)
            st.plotly_chart(fig_cmp, use_container_width=True)

            comparison_table = pd.DataFrame({
                "Metric": ["Schools", "Students", "Teacher Headcount", "Teacher FTTE", "PTR (FTTE)", "Students / School"],
                f"{location_a}": [
                    summary_a["Schools"],
                    summary_a["Students"],
                    summary_a["Teacher Headcount"],
                    summary_a["Teacher FTTE"],
                    summary_a["PTR (FTTE)"],
                    summary_a["Students / School"],
                ],
                f"{location_b}": [
                    summary_b["Schools"],
                    summary_b["Students"],
                    summary_b["Teacher Headcount"],
                    summary_b["Teacher FTTE"],
                    summary_b["PTR (FTTE)"],
                    summary_b["Students / School"],
                ],
            })

            comparison_table["Delta (B - A)"] = (
                pd.to_numeric(comparison_table[f"{location_b}"], errors="coerce")
                - pd.to_numeric(comparison_table[f"{location_a}"], errors="coerce")
            )

            for col in comparison_table.columns[1:]:
                comparison_table[col] = pd.to_numeric(comparison_table[col], errors="coerce").round(2)

            st.markdown("### Comparison Table")
            st.dataframe(comparison_table, use_container_width=True, hide_index=True)

            cmp_csv = comparison_table.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download NZ analytics comparison table (CSV)",
                data=cmp_csv,
                file_name="nz_analytics_comparison_table.csv",
                mime="text/csv",
            )

    with tabs[3]:
        st.markdown("### Custom Reports")

        st.caption(
            "Build grouped NZ reports from the filtered school-level dataset. "
            "Students use 2025 school rolls; teacher metrics use the latest teacher dataset available in the processed NZ files. "
            "PTR is FTTE-overlap based."
        )

        dim_options = {
            "Regional Council": "regional_council",
            "Territorial Authority": "territorial_authority",
            "School Type": "school_type",
            "Authority": "authority",
            "Gender": "gender",
        }

        metric_options = {
            "Schools": "schools",
            "Students": "students",
            "Teacher Headcount": "teacher_headcount",
            "Teacher FTTE": "teacher_ftte",
            "PTR (FTTE)": "ptr_ftte",
            "Students / School": "students_per_school",
        }

        r1, r2, r3 = st.columns([2.2, 2.2, 1.1])

        selected_dim_labels = r1.multiselect(
            "Report Dimensions",
            list(dim_options.keys()),
            default=["Regional Council", "Territorial Authority"],
            key="nz_analytics_custom_dimensions",
        )

        selected_metric_labels = r2.multiselect(
            "Report Metrics",
            list(metric_options.keys()),
            default=["Schools", "Students", "Teacher FTTE", "PTR (FTTE)"],
            key="nz_analytics_custom_metrics",
        )

        row_limit = r3.selectbox(
            "Row Limit",
            [100, 250, 500, 1000],
            index=2,
            key="nz_analytics_custom_row_limit",
        )

        f1, f2, f3 = st.columns(3)

        custom_region_options = ["All"] + sorted(
            [x for x in df.get("regional_council", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        custom_region = f1.selectbox(
            "Scope Regional Council",
            custom_region_options,
            index=0,
            key="nz_analytics_custom_scope_region",
        )

        custom_type_options = ["All"] + sorted(
            [x for x in df.get("school_type", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        custom_type = f2.selectbox(
            "Scope School Type",
            custom_type_options,
            index=0,
            key="nz_analytics_custom_scope_type",
        )

        custom_authority_options = ["All"] + sorted(
            [x for x in df.get("authority", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
        )
        custom_authority = f3.selectbox(
            "Scope Authority",
            custom_authority_options,
            index=0,
            key="nz_analytics_custom_scope_authority",
        )

        report_base = df.copy()

        if custom_region != "All" and "regional_council" in report_base.columns:
            report_base = report_base[report_base["regional_council"] == custom_region]
        if custom_type != "All" and "school_type" in report_base.columns:
            report_base = report_base[report_base["school_type"] == custom_type]
        if custom_authority != "All" and "authority" in report_base.columns:
            report_base = report_base[report_base["authority"] == custom_authority]

        if report_base.empty:
            st.info("No data is available for the current custom report selection.")
        elif not selected_metric_labels:
            st.warning("Select at least one metric to generate a custom report.")
        else:
            selected_group_cols = [dim_options[label] for label in selected_dim_labels]

            def _build_report(frame: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
                if group_cols:
                    report = (
                        frame.groupby(group_cols, dropna=False, as_index=False)
                        .agg(
                            schools=("school_id", "nunique") if "school_id" in frame.columns else (group_cols[0], "size"),
                            students=("total_students", "sum") if "total_students" in frame.columns else (group_cols[0], "size"),
                            teacher_headcount=("teacher_headcount", "sum") if "teacher_headcount" in frame.columns else (group_cols[0], "size"),
                            teacher_ftte=("teacher_ftte", "sum") if "teacher_ftte" in frame.columns else (group_cols[0], "size"),
                        )
                    )
                else:
                    report = pd.DataFrame([{
                        "schools": int(frame["school_id"].nunique()) if "school_id" in frame.columns else len(frame),
                        "students": float(frame["total_students"].fillna(0).sum()) if "total_students" in frame.columns else 0,
                        "teacher_headcount": float(frame["teacher_headcount"].fillna(0).sum()) if "teacher_headcount" in frame.columns else 0,
                        "teacher_ftte": float(frame["teacher_ftte"].fillna(0).sum()) if "teacher_ftte" in frame.columns else 0,
                    }])

                report["ptr_ftte"] = pd.NA
                if "teacher_ftte" in report.columns and "students" in report.columns:
                    valid_mask = pd.to_numeric(report["teacher_ftte"], errors="coerce").fillna(0) > 0
                    report.loc[valid_mask, "ptr_ftte"] = (
                        pd.to_numeric(report.loc[valid_mask, "students"], errors="coerce")
                        / pd.to_numeric(report.loc[valid_mask, "teacher_ftte"], errors="coerce")
                    )

                report["students_per_school"] = pd.NA
                if "schools" in report.columns and "students" in report.columns:
                    school_mask = pd.to_numeric(report["schools"], errors="coerce").fillna(0) > 0
                    report.loc[school_mask, "students_per_school"] = (
                        pd.to_numeric(report.loc[school_mask, "students"], errors="coerce")
                        / pd.to_numeric(report.loc[school_mask, "schools"], errors="coerce")
                    )

                return report

            report_df = _build_report(report_base, selected_group_cols)

            metric_col_order = [metric_options[m] for m in selected_metric_labels]
            output_cols = selected_group_cols + metric_col_order
            output_cols = [c for c in output_cols if c in report_df.columns]

            final_report = report_df[output_cols].copy()

            sort_metric = None
            for candidate in ["students", "schools", "teacher_ftte", "teacher_headcount", "ptr_ftte", "students_per_school"]:
                if candidate in final_report.columns:
                    sort_metric = candidate
                    break

            if sort_metric is not None:
                final_report = final_report.sort_values(sort_metric, ascending=False)

            final_report = final_report.head(row_limit).copy()

            rename_map = {
                "regional_council": "Regional Council",
                "territorial_authority": "Territorial Authority",
                "school_type": "School Type",
                "authority": "Authority",
                "gender": "Gender",
                "schools": "Schools",
                "students": "Students",
                "teacher_headcount": "Teacher Headcount",
                "teacher_ftte": "Teacher FTTE",
                "ptr_ftte": "PTR (FTTE)",
                "students_per_school": "Students / School",
            }
            final_report = final_report.rename(columns=rename_map)

            for col in ["Teacher FTTE", "PTR (FTTE)", "Students / School"]:
                if col in final_report.columns:
                    final_report[col] = pd.to_numeric(final_report[col], errors="coerce").round(2)

            st.markdown("### Custom Report Output")
            st.dataframe(final_report, use_container_width=True, hide_index=True)

            report_csv = final_report.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download NZ analytics custom report (CSV)",
                data=report_csv,
                file_name="nz_analytics_custom_report.csv",
                mime="text/csv",
            )

            st.markdown("### Filtered School Extract")

            extract_cols = [
                c for c in [
                    "school_name",
                    "regional_council",
                    "territorial_authority",
                    "school_type",
                    "authority",
                    "gender",
                    "total_students",
                    "teacher_headcount",
                    "teacher_ftte",
                    "ptr_ftte",
                ] if c in report_base.columns
            ]

            extract_df = report_base[extract_cols].copy() if extract_cols else report_base.copy()

            if "ptr_ftte" in extract_df.columns:
                extract_df["ptr_ftte"] = pd.to_numeric(extract_df["ptr_ftte"], errors="coerce").round(2)
            if "teacher_ftte" in extract_df.columns:
                extract_df["teacher_ftte"] = pd.to_numeric(extract_df["teacher_ftte"], errors="coerce").round(2)

            if "total_students" in extract_df.columns:
                extract_df = extract_df.sort_values("total_students", ascending=False)

            extract_df = extract_df.head(row_limit).copy()

            st.dataframe(extract_df, use_container_width=True, hide_index=True)

            extract_csv = extract_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download filtered NZ analytics school extract (custom reports CSV)",
                data=extract_csv,
                file_name="nz_analytics_custom_reports_filtered_school_extract.csv",
                mime="text/csv",
            )

    _render_nz_footer()
