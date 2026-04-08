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
            New Zealand dashboard foundation connected to processed official datasets.
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
    st.markdown("# 🏠 TutorCloud Global Dashboard")
    st.markdown("**National K-12 Education Overview - New Zealand**")
    st.markdown("---")

    bundle = _load_nz_home_bundle()
    if not bundle.get("ok"):
        st.error("NZ Home data files are missing. Please complete the processed NZ pipeline first.")
        st.code("\n".join(bundle.get("missing", [])))
        _render_source_links()
        _render_nz_footer()
        return

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("TOTAL REGIONS", _fmt_int(bundle["total_regions"]))
    with c2:
        st.metric("TOTAL SCHOOLS", _fmt_int(bundle["total_schools"]))
    with c3:
        st.metric("TOTAL STUDENTS", _fmt_int(bundle["total_students"]))
    with c4:
        st.metric(f"TOTAL TEACHERS ({bundle['teacher_year']} HC)", _fmt_int(bundle["total_teacher_headcount"]))
    with c5:
        st.metric("PTR (FTTE OVERLAP)", _fmt_float(bundle["ptr_ftte"], 2))
    with c6:
        st.metric("STUDENTS / SCHOOL", _fmt_float(bundle["students_per_school"], 1))

    st.caption(
        f"Students use 2025 School Rolls. Teachers use {bundle['teacher_year']} regular teacher data. "
        f"PTR is calculated only on the rolls-teacher overlap set "
        f"({_fmt_int(bundle['overlap_students'])} students across {_fmt_int(bundle['overlap_schools'])} schools)."
    )

    d1, d2, d3 = st.columns(3)
    with d1:
        st.metric("GEOCODED ROLL SCHOOLS", _fmt_int(bundle["mapped_schools"]))
    with d2:
        st.metric("GEOCODED STUDENTS FOR MAPS", _fmt_int(bundle["mapped_students"]))
    with d3:
        st.metric(f"TOTAL TEACHER FTTE ({bundle['teacher_year']})", _fmt_float(bundle["total_teacher_ftte"], 1))

    left, right = st.columns(2)

    with left:
        st.markdown("### 📍 Top Regional Councils by Students")
        reg = bundle["regional_chart"].copy()
        if not reg.empty and "total_students_2025" in reg.columns:
            reg = reg.sort_values("total_students_2025", ascending=True)
            fig_reg = px.bar(
                reg,
                x="total_students_2025",
                y="regional_council",
                orientation="h",
                text="total_students_2025",
                color="total_students_2025",
                color_continuous_scale="Blues",
            )
            fig_reg.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_reg.update_layout(
                height=460,
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                xaxis_title="Students (2025)",
                yaxis_title="",
            )
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.info("Regional council chart data is not available yet.")

    with right:
        st.markdown("### 🏙️ Top Territorial Authorities by Students")
        ta = bundle["ta_chart"].copy()
        if not ta.empty and "total_students_2025" in ta.columns:
            ta = ta.sort_values("total_students_2025", ascending=True)
            ta["label"] = ta["territorial_authority"].astype(str)
            fig_ta = px.bar(
                ta,
                x="total_students_2025",
                y="label",
                orientation="h",
                text="total_students_2025",
                color="regional_council" if "regional_council" in ta.columns else None,
            )
            fig_ta.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_ta.update_layout(
                height=460,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Students (2025)",
                yaxis_title="",
                legend_title_text="Regional Council",
            )
            st.plotly_chart(fig_ta, use_container_width=True)
        else:
            st.info("Territorial authority chart data is not available yet.")

    st.markdown("### 📋 Coverage & Method Notes")
    st.markdown(
        f"""
- National students KPI uses the cleaned 2025 school-roll fact table: **{_fmt_int(bundle["total_students"])}** students.
- Geographic charts use canonically matched school geography from the NZ schools directory: **{_fmt_int(bundle["mapped_students"])}** mapped students.
- Teacher metrics use **{bundle["teacher_year"]}** regular teacher headcount / FTTE only.
- PTR shown here is **FTTE overlap PTR**, not a full all-schools national PTR.
        """
    )

    _render_source_links()
    _render_nz_footer()


def render_nz_state_dashboard() -> None:
    inject_professional_css()
    st.markdown('<div class="main-header">📊 State Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">New Zealand regional and territorial authority analysis</div>', unsafe_allow_html=True)

    bundle = _load_nz_state_school_frame()
    if not bundle.get("ok"):
        st.error("NZ State Dashboard data files are missing.")
        st.code("\n".join(bundle.get("missing", [])))
        _render_source_links()
        _render_nz_footer()
        return

    df = bundle["df"].copy()
    teacher_year = bundle["teacher_year"]
    roll_year = bundle["roll_year"]

    st.caption(
        f"Students use {roll_year} School Rolls. Teachers use {teacher_year} regular teacher data where available. "
        f"PTR is shown only where teacher FTTE exists."
    )

    f1, f2, f3, f4, f5 = st.columns(5)

    region_options = ["All"] + sorted([x for x in df["regional_council"].dropna().astype(str).unique().tolist() if x])
    selected_region = f1.selectbox("Regional Council", region_options, index=0)

    ta_base = df.copy()
    if selected_region != "All":
        ta_base = ta_base[ta_base["regional_council"] == selected_region]

    ta_options = ["All"] + sorted([x for x in ta_base["territorial_authority"].dropna().astype(str).unique().tolist() if x])
    selected_ta = f2.selectbox("Territorial Authority", ta_options, index=0)

    type_options = ["All"] + sorted([x for x in df["school_type"].dropna().astype(str).unique().tolist() if x])
    selected_type = f3.selectbox("School Type", type_options, index=0)

    authority_options = ["All"] + sorted([x for x in df["authority"].dropna().astype(str).unique().tolist() if x])
    selected_authority = f4.selectbox("Authority", authority_options, index=0)

    gender_options = ["All"] + sorted([x for x in df["gender"].dropna().astype(str).unique().tolist() if x])
    selected_gender = f5.selectbox("Gender", gender_options, index=0)

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

    if filtered.empty:
        st.warning("No records match the current NZ State Dashboard filters.")
        _render_source_links()
        _render_nz_footer()
        return

    total_regions = int(filtered["regional_council"].nunique())
    total_tas = int(filtered["territorial_authority"].nunique())
    total_schools = int(filtered["school_id"].nunique())
    total_students = float(filtered["total_students"].fillna(0).sum())
    total_teacher_ftte = float(filtered["teacher_ftte"].fillna(0).sum())
    total_teacher_headcount = float(filtered["teacher_headcount"].fillna(0).sum())

    ptr_ftte = total_students / total_teacher_ftte if total_teacher_ftte else None
    students_per_school = total_students / total_schools if total_schools else None

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("REGIONS", _fmt_int(total_regions))
    with c2:
        st.metric("TERRITORIAL AUTHORITIES", _fmt_int(total_tas))
    with c3:
        st.metric("SCHOOLS", _fmt_int(total_schools))
    with c4:
        st.metric("STUDENTS", _fmt_int(total_students))
    with c5:
        st.metric(f"TEACHER FTTE ({teacher_year})", _fmt_float(total_teacher_ftte, 1))
    with c6:
        st.metric("PTR (FTTE)", _fmt_float(ptr_ftte, 2))

    d1, d2, d3 = st.columns(3)
    with d1:
        st.metric(f"TEACHER HEADCOUNT ({teacher_year})", _fmt_int(total_teacher_headcount))
    with d2:
        st.metric("STUDENTS / SCHOOL", _fmt_float(students_per_school, 1))
    with d3:
        st.metric("SCHOOLS WITH TEACHER DATA", _fmt_int(filtered.loc[filtered["teacher_ftte"].notna(), "school_id"].nunique()))

    left, right = st.columns(2)

    with left:
        st.markdown("### 🏙️ Top Territorial Authorities in Current Selection")
        ta_summary = (
            filtered.groupby(["territorial_authority", "regional_council"], dropna=False)
            .agg(total_students=("total_students", "sum"))
            .reset_index()
            .sort_values("total_students", ascending=False)
            .head(12)
            .sort_values("total_students", ascending=True)
        )
        if not ta_summary.empty:
            fig_ta = px.bar(
                ta_summary,
                x="total_students",
                y="territorial_authority",
                orientation="h",
                text="total_students",
                color="regional_council",
            )
            fig_ta.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_ta.update_layout(
                height=500,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title=f"Students ({roll_year})",
                yaxis_title="",
                legend_title_text="Regional Council",
            )
            st.plotly_chart(fig_ta, use_container_width=True)
        else:
            st.info("No territorial authority summary available for this selection.")

    with right:
        st.markdown("### 🏫 Student Distribution by School Type")
        type_summary = (
            filtered.groupby("school_type", dropna=False)
            .agg(
                total_students=("total_students", "sum"),
                schools=("school_id", "nunique")
            )
            .reset_index()
            .sort_values("total_students", ascending=False)
            .head(12)
            .sort_values("total_students", ascending=True)
        )
        if not type_summary.empty:
            fig_type = px.bar(
                type_summary,
                x="total_students",
                y="school_type",
                orientation="h",
                text="total_students",
                color="schools",
                color_continuous_scale="Tealgrn",
            )
            fig_type.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_type.update_layout(
                height=500,
                margin=dict(l=10, r=10, t=10, b=10),
                coloraxis_showscale=False,
                xaxis_title=f"Students ({roll_year})",
                yaxis_title="",
            )
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("No school-type summary available for this selection.")

    st.markdown("### 🏫 School Directory and Performance Detail")
    display_cols = [
        "school_id", "school_name", "regional_council", "territorial_authority",
        "education_region", "school_type", "authority", "gender",
        "urban_rural", "sa2_name", "total_students", "teacher_headcount",
        "teacher_ftte", "ptr_ftte"
    ]
    display_cols = [c for c in display_cols if c in filtered.columns]

    table_df = filtered[display_cols].copy().sort_values(
        ["total_students", "school_name"], ascending=[False, True]
    )

    st.dataframe(table_df, use_container_width=True, hide_index=True)

    csv_data = table_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download filtered NZ state dashboard data (CSV)",
        data=csv_data,
        file_name="nz_state_dashboard_filtered.csv",
        mime="text/csv",
    )

    _render_source_links()
    _render_nz_footer()


def render_nz_analytics() -> None:
    inject_professional_css()
    st.markdown('<div class="main-header">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">New Zealand analytics foundation connected</div>', unsafe_allow_html=True)
    st.warning("New Zealand Analytics routing is now connected. Geographic Maps, Performance Metrics, Comparative Analysis, and Custom Reports will be built on the official NZ source model next.")
    tabs = st.tabs(["🗺️ Geographic Maps", "🎯 Performance Metrics", "🔍 Comparative Analysis", "📝 Custom Reports"])
    with tabs[0]:
        st.info("Geographic layer will be built from Regional Council, Territorial Authority, and SA2 / school profile data.")
    with tabs[1]:
        st.info("Performance metrics will use school rolls, teacher headcount / FTTE, school counts, and derived PTR calculations.")
    with tabs[2]:
        st.info("Comparative analysis will support region-vs-region and territorial-authority comparisons.")
    with tabs[3]:
        st.info("Custom reports will be built after the NZ transformed fact tables are loaded.")
    _render_source_links()
    _render_nz_footer()
