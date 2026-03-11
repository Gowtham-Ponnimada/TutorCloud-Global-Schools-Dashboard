"""
pages/5_🇦🇪_UAE_Dashboard.py
UAE Dashboard — TutorCloud Global Schools Dashboard

ARCHITECTURE NOTES:
─────────────────────────────────────────────────────────────
• India dashboard (2_📊_State_Dashboard.py) is UNTOUCHED.
• This page runs in PARALLEL on the same Streamlit app.
• Shared modules used:   ui_styles.py (load_styles)
                         ui_components.py (header/footer)
• UAE-only modules used: utils/uae_connector.py  (all SQL)
                         utils/uae_utils.py       (charts/KPI)
• No st.set_page_config() here — app.py owns that.
• Connected to region selector via session_state when ready:
      st.session_state.selected_region == "UAE"
─────────────────────────────────────────────────────────────
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

# ── Shared app-level imports (same as India page) ─────────────────────────────
try:
    from ui_styles import load_styles          # shared CSS — India CSS untouched
    from ui_components import render_header, render_footer   # shared header/footer
    SHARED_UI = True
except ImportError:
    SHARED_UI = False                          # graceful fallback during dev

# ── UAE-only imports ──────────────────────────────────────────────────────────
try:
    from utils.uae_connector import (
        get_uae_kpi_summary,
        get_uae_available_years,
        get_uae_available_regions,
        get_uae_available_edu_types,
        get_uae_enrollment_by_emirate,
        get_uae_enrollment_trend,
        get_uae_enrollment_by_edu_type,
        get_uae_schools_by_emirate,
        get_uae_schools_by_curriculum,
        get_uae_schools_curriculum_detail,
        get_uae_teachers_by_emirate,
        get_uae_student_teacher_ratio,
        get_uae_teachers_by_subject,
        get_uae_teacher_trend,
        get_uae_pass_rates_by_emirate,
        get_uae_pass_rates_trend,
        get_uae_pass_rates_by_cycle,
        get_uae_scores_by_subject,
        get_uae_nationality_diversity,
        get_uae_nationality_trend,
        uae_db_health_check,
    )
    from utils.uae_utils import (
        uae_kpi_card, uae_page_header, uae_section_header,
        uae_sidebar, uae_dev_banner, uae_setup_warning,
        bar_h, donut, line_trend, treemap_chart, perf_bar,
        fmt, fmt_pct, pct, UAE,
    )
    MODULES_OK = True
except ImportError as e:
    st.error(f"UAE module import error: {e}")
    MODULES_OK = False

# ── Apply shared styles (same call as India page) ─────────────────────────────
if SHARED_UI:
    load_styles()

# ── Shared header (same component India uses) ─────────────────────────────────
if SHARED_UI:
    render_header(region="UAE")   # passes region so header can show 🇦🇪 badge

# ── DB health check ───────────────────────────────────────────────────────────
if MODULES_OK:
    health = uae_db_health_check()
    if health.get("status") != "ok" or health.get("uae_fact_enrollment", 0) == 0:
        uae_setup_warning()
        if SHARED_UI: render_footer()
        st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────
if MODULES_OK:
    years     = get_uae_available_years()
    regions   = get_uae_available_regions()
    edu_types = get_uae_available_edu_types()
    sel_year, sel_region, sel_edu = uae_sidebar(years, regions, edu_types)

    # ── Dev banner (remove when UAE goes live in region selector) ─────────────
    # uae_dev_banner()   # Uncomment during dev, remove on go-live

# ── Load KPI data ─────────────────────────────────────────────────────────────
kpi_df = get_uae_kpi_summary()
cur    = kpi_df[kpi_df["academic_year"] == sel_year]
prev   = kpi_df[kpi_df["academic_year"] != sel_year].head(1)

def kval(col):
    return int(cur[col].values[0])   if not cur.empty  and col in cur.columns  else 0
def kprev(col):
    return int(prev[col].values[0])  if not prev.empty and col in prev.columns else 0
def kdelta(col):
    return kval(col) - kprev(col)    if not prev.empty else None

# ── Page header banner ────────────────────────────────────────────────────────
uae_page_header(
    title    = "UAE Schools Dashboard",
    subtitle = "Ministry of Education · General Education Statistics",
    year     = sel_year,
)

# ── KPI row — 6 cards (matches India card HTML/CSS structure exactly) ─────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: uae_kpi_card("Total Students Enrolled",  fmt(kval("total_students")),    kdelta("total_students"),    icon="🎓")
with c2: uae_kpi_card("Total Schools",             fmt(kval("total_schools")),     kdelta("total_schools"),     icon="🏫")
with c3: uae_kpi_card("Total Teachers",            fmt(kval("total_teachers")),    kdelta("total_teachers"),    icon="👨‍🏫")
with c4: uae_kpi_card("🇦🇪 Emirati Students",    fmt(kval("emirati_students")),  kdelta("emirati_students"),  icon="🇦🇪", border_color=UAE["green"])
with c5: uae_kpi_card("Resident Students",         fmt(kval("resident_students")), kdelta("resident_students"), icon="🌍",  border_color=UAE["gold"])
with c6: uae_kpi_card("Unique Nationalities",      fmt(kval("unique_nationalities")), None,                     icon="🗺️",  border_color=UAE["blue"])

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TABS — same structure as India's State Dashboard
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "🏫 Schools",
    "👨‍🏫 Teachers",
    "📈 Performance",
    "🌍 Demographics",
])

# ─── helper: apply region filter ─────────────────────────────────────────────
def maybe_filter_region(df, col="region_en"):
    if sel_region == "All Emirates": return df
    return df[df[col] == sel_region].copy()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    uae_section_header(f"📊 Enrollment Overview — {sel_year}")

    enr_emirate = maybe_filter_region(
        get_uae_enrollment_by_emirate()[
            get_uae_enrollment_by_emirate()["academic_year"] == sel_year
        ]
    )
    trend_df = get_uae_enrollment_trend()

    col_l, col_r = st.columns([2, 1])

    with col_l:
        # Enrollment by emirate — horizontal bar
        if not enr_emirate.empty:
            st.plotly_chart(
                bar_h(enr_emirate, x="total_students", y="region_en",
                      title=f"📍 Students Enrolled by Emirate ({sel_year})",
                      color_scale=["#b3e5b3", UAE["green"]], height=420),
                use_container_width=True,
            )

    with col_r:
        # Gender donut
        total  = kval("total_students")
        female = kval("female_students")
        male   = kval("male_students")
        st.plotly_chart(
            donut(["Female","Male"], [female, male], "👫 Gender Split",
                  colors=[UAE["red"], UAE["blue"]],
                  center_text=f"<b>{fmt(total)}</b><br>Total",
                  height=290),
            use_container_width=True,
        )
        # Emirati vs Resident donut
        st.plotly_chart(
            donut(["Emirati","Resident"],
                  [kval("emirati_students"), kval("resident_students")],
                  "🇦🇪 Emirati vs Resident",
                  colors=[UAE["green"], UAE["gold"]], height=290),
            use_container_width=True,
        )

    # Enrollment trend
    uae_section_header("📈 Enrollment Trend (2020–2025)")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.plotly_chart(
            line_trend(trend_df, "academic_year", "total_students",
                       "Total Students Enrolled", color=UAE["green"], height=300),
            use_container_width=True,
        )
    with col_t2:
        # Public vs Private trend
        import plotly.graph_objects as go
        fig_sec = go.Figure()
        fig_sec.add_trace(go.Scatter(
            x=trend_df["academic_year"], y=trend_df["public_sector"],
            name="Public", mode="lines+markers",
            line=dict(color=UAE["green"], width=3), marker=dict(size=7),
        ))
        fig_sec.add_trace(go.Scatter(
            x=trend_df["academic_year"],
            y=trend_df["total_students"] - trend_df["public_sector"],
            name="Private/Other", mode="lines+markers",
            line=dict(color=UAE["blue"], width=3), marker=dict(size=7),
        ))
        fig_sec.update_layout(
            title="Public vs Private Enrollment Trend",
            plot_bgcolor="white", height=300,
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig_sec, use_container_width=True)

    # Education type breakdown
    uae_section_header("🏫 Students by Education Type")
    edu_df = get_uae_enrollment_by_edu_type(sel_year)
    if not edu_df.empty:
        st.plotly_chart(
            bar_h(edu_df, x="total_students", y="education_type",
                  title=f"Education Type Breakdown ({sel_year})",
                  color_scale=["#bbdefb", UAE["blue"]], height=320),
            use_container_width=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SCHOOLS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    uae_section_header(f"🏫 Schools — {sel_year}")

    sch_emirate  = get_uae_schools_by_emirate(sel_year)
    sch_curr     = get_uae_schools_by_curriculum(sel_year)

    # Summary metrics
    tot_schools = sch_emirate["total_schools"].sum() if not sch_emirate.empty else 0
    girls_total = sch_emirate["girls_schools"].sum() if not sch_emirate.empty else 0
    boys_total  = sch_emirate["boys_schools"].sum()  if not sch_emirate.empty else 0
    coedu_total = sch_emirate["coedu_schools"].sum() if not sch_emirate.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🏫 Total Schools",  fmt(tot_schools))
    m2.metric("👧 Girls Schools",  fmt(girls_total),  f"{pct(girls_total,tot_schools):.0f}%")
    m3.metric("👦 Boys Schools",   fmt(boys_total),   f"{pct(boys_total,tot_schools):.0f}%")
    m4.metric("👫 Co-Ed Schools",  fmt(coedu_total),  f"{pct(coedu_total,tot_schools):.0f}%")

    st.divider()
    col_sa, col_sb = st.columns(2)

    with col_sa:
        if not sch_emirate.empty:
            st.plotly_chart(
                bar_h(sch_emirate, "total_schools", "region_en",
                      f"🏫 Schools by Emirate ({sel_year})",
                      color_scale=["#b3e5b3", UAE["green"]], height=400),
                use_container_width=True,
            )
    with col_sb:
        if not sch_curr.empty:
            st.plotly_chart(
                bar_h(sch_curr.head(12), "total_schools", "curriculum_en",
                      "📚 Schools by Curriculum (Top 12)",
                      color_scale=["#bbdefb", UAE["blue"]], height=400),
                use_container_width=True,
            )

    # Gender type pie
    uae_section_header("👫 School Gender Type")
    col_sc, col_sd = st.columns([1, 2])
    with col_sc:
        st.plotly_chart(
            donut(["Girls", "Boys", "Co Edu"],
                  [girls_total, boys_total, coedu_total],
                  "School Gender Type",
                  colors=[UAE["red"], UAE["blue"], UAE["green"]], height=320),
            use_container_width=True,
        )
    with col_sd:
        # Curriculum detail table
        sch_detail = get_uae_schools_curriculum_detail()
        yr_detail  = sch_detail[sch_detail["academic_year"] == sel_year]
        if not yr_detail.empty:
            top_curr = (yr_detail.groupby("curriculum_en")["total_schools"]
                        .sum().reset_index()
                        .sort_values("total_schools", ascending=False)
                        .head(10))
            top_curr.columns = ["Curriculum", "Schools"]
            st.dataframe(top_curr, hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TEACHERS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    uae_section_header(f"👨‍🏫 Teachers & Staff — {sel_year}")

    tch_emirate = get_uae_teachers_by_emirate()
    tch_yr      = tch_emirate[tch_emirate["academic_year"] == sel_year]
    rat_all     = get_uae_student_teacher_ratio()
    rat_yr      = rat_all[rat_all["academic_year"] == sel_year]
    tch_trend   = get_uae_teacher_trend()
    tsub        = get_uae_teachers_by_subject(sel_year, sel_region if sel_region != "All Emirates" else None)

    # Summary metrics
    tot_tch    = tch_yr["total_teachers"].sum()  if not tch_yr.empty else 0
    tot_staff  = tch_yr["total_staff"].sum()     if not tch_yr.empty else 0
    emirati_t  = tch_yr["emirati_teachers"].sum()if not tch_yr.empty else 0
    resident_t = tch_yr["resident_teachers"].sum()if not tch_yr.empty else 0

    t1, t2, t3, t4 = st.columns(4)
    t1.metric("👨‍🏫 Total Teachers",  fmt(tot_tch))
    t2.metric("👥 Total Staff",        fmt(tot_staff))
    t3.metric("🇦🇪 Emirati Teachers", fmt(emirati_t),  f"{pct(emirati_t,tot_tch):.0f}%")
    t4.metric("🌍 Resident Teachers",  fmt(resident_t), f"{pct(resident_t,tot_tch):.0f}%")

    st.divider()
    col_ta, col_tb = st.columns(2)

    with col_ta:
        if not tch_yr.empty:
            st.plotly_chart(
                bar_h(tch_yr, "total_teachers", "region_en",
                      f"👨‍🏫 Teachers by Emirate ({sel_year})",
                      color_scale=["#bbdefb", UAE["blue"]], height=400),
                use_container_width=True,
            )
    with col_tb:
        if not rat_yr.empty:
            st.plotly_chart(
                bar_h(rat_yr, "ratio", "region_en",
                      "📐 Student : Teacher Ratio",
                      color_scale=["#c8e6c9", UAE["red"]], height=400),
                use_container_width=True,
            )

    # Emirati vs Resident + Subject breakdown
    uae_section_header("Nationality & Subject Breakdown")
    col_tc, col_td = st.columns([1, 2])

    with col_tc:
        st.plotly_chart(
            donut(["Emirati","Resident"], [emirati_t, resident_t],
                  "🇦🇪 Teacher Nationality",
                  colors=[UAE["green"], UAE["gold"]], height=300),
            use_container_width=True,
        )

    with col_td:
        if not tsub.empty:
            st.plotly_chart(
                bar_h(tsub.head(15), "total_teachers", "subject_en",
                      f"📖 Top Subjects by Teacher Count ({sel_year})",
                      color_scale=["#bbdefb", UAE["blue"]], height=420),
                use_container_width=True,
            )

    # Teacher trend
    uae_section_header("📈 Teacher Count Trend")
    if not tch_trend.empty:
        import plotly.graph_objects as go
        fig_tt = go.Figure()
        fig_tt.add_trace(go.Scatter(
            x=tch_trend["academic_year"], y=tch_trend["total_teachers"],
            name="Total Teachers", mode="lines+markers",
            line=dict(color=UAE["blue"], width=3), marker=dict(size=7),
        ))
        fig_tt.add_trace(go.Scatter(
            x=tch_trend["academic_year"], y=tch_trend["emirati_teachers"],
            name="Emirati Teachers", mode="lines+markers",
            line=dict(color=UAE["green"], width=2, dash="dot"), marker=dict(size=6),
        ))
        fig_tt.update_layout(plot_bgcolor="white", height=280,
                              legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig_tt, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    uae_section_header(f"📈 Academic Performance — {sel_year}")

    pf_emirate = get_uae_pass_rates_by_emirate(sel_year)
    pf_cycle   = get_uae_pass_rates_by_cycle(sel_year)
    pf_trend   = get_uae_pass_rates_trend()
    sub_scores = get_uae_scores_by_subject(
        sel_year, sel_region if sel_region != "All Emirates" else None
    )

    col_pa, col_pb = st.columns(2)

    with col_pa:
        if not pf_emirate.empty:
            st.plotly_chart(
                perf_bar(pf_emirate, "avg_pass_rate", "region_en",
                         f"✅ Avg Pass Rate by Emirate ({sel_year})",
                         range_color=(70, 100), height=400),
                use_container_width=True,
            )

    with col_pb:
        # Pass rate by cycle
        if not pf_cycle.empty:
            cycle_summary = (pf_cycle.groupby("cycle")["avg_pass_rate"]
                             .mean().reset_index()
                             .sort_values("avg_pass_rate", ascending=True))
            st.plotly_chart(
                perf_bar(cycle_summary, "avg_pass_rate", "cycle",
                         f"📚 Pass Rate by Cycle ({sel_year})",
                         range_color=(70, 100), height=400),
                use_container_width=True,
            )

    # Pass rate trend
    uae_section_header("📈 Pass Rate Trend (2020–2024)")
    if not pf_trend.empty:
        trend_overall = (pf_trend.groupby("academic_year")["avg_pass_rate"]
                         .mean().reset_index().sort_values("academic_year"))
        st.plotly_chart(
            line_trend(trend_overall, "academic_year", "avg_pass_rate",
                       "National Average Pass Rate", color=UAE["green"], height=280),
            use_container_width=True,
        )

    # Emirati vs Expat pass rate
    uae_section_header("🇦🇪 Emirati vs Expat Pass Rate")
    col_pc, col_pd = st.columns(2)

    with col_pc:
        if not pf_trend.empty:
            import plotly.graph_objects as go
            pf_nat = (pf_trend.groupby(["academic_year","nationality_cat"])["avg_pass_rate"]
                      .mean().reset_index())
            fig_pn = go.Figure()
            for nat, color in [("Emirati", UAE["green"]), ("Expat", UAE["gold"])]:
                d = pf_nat[pf_nat["nationality_cat"] == nat]
                fig_pn.add_trace(go.Scatter(
                    x=d["academic_year"], y=d["avg_pass_rate"],
                    name=nat, mode="lines+markers",
                    line=dict(color=color, width=3), marker=dict(size=7),
                ))
            fig_pn.update_layout(plot_bgcolor="white", height=280,
                                  title="Emirati vs Expat Pass Rate Trend",
                                  legend=dict(orientation="h", y=-0.25))
            st.plotly_chart(fig_pn, use_container_width=True)

    with col_pd:
        # Subject scores
        if not sub_scores.empty:
            st.plotly_chart(
                perf_bar(sub_scores.head(15), "avg_pass_rate", "subject_en",
                         f"📖 Pass Rate by Subject ({sel_year})",
                         range_color=(60, 100), height=420),
                use_container_width=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — DEMOGRAPHICS
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    uae_section_header("🌍 Student Nationality & Demographics")

    nat_df   = get_uae_nationality_diversity()
    nat_years = sorted(nat_df["academic_year"].unique().tolist(), reverse=True)
    # Use latest available year (nationalities go up to 2023-2024)
    nat_yr_sel = nat_years[0] if nat_years else sel_year
    nat_yr     = nat_df[nat_df["academic_year"] == nat_yr_sel].copy()

    # Headline metrics
    total_nat = nat_yr["student_count"].sum()
    uae_nat   = nat_yr[nat_yr["nationality_en"]=="United Arab Emirates"]["student_count"].sum()
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("🌍 Total Students",       fmt(total_nat))
    n2.metric("🇦🇪 UAE Nationals",      fmt(uae_nat),          f"{pct(uae_nat,total_nat):.1f}%")
    n3.metric("✈️  International",        fmt(total_nat-uae_nat), f"{pct(total_nat-uae_nat,total_nat):.1f}%")
    n4.metric("📊 Unique Nationalities",  nat_yr["nationality_en"].nunique())

    st.divider()
    col_na, col_nb = st.columns([2, 1])

    with col_na:
        top20 = nat_yr[nat_yr["rank_in_year"] <= 20].sort_values("student_count", ascending=True)
        if not top20.empty:
            st.plotly_chart(
                bar_h(top20, "student_count", "nationality_en",
                      f"🌍 Top 20 Student Nationalities ({nat_yr_sel})",
                      color_scale=["#bbdefb", UAE["green"]], height=540),
                use_container_width=True,
            )

    with col_nb:
        top10 = nat_yr[nat_yr["rank_in_year"] <= 10]
        if not top10.empty:
            st.plotly_chart(
                treemap_chart(top10, "nationality_en", "student_count",
                              "pct_of_total",
                              f"Top 10 Nationalities — {nat_yr_sel}", height=400),
                use_container_width=True,
            )

    # UAE nationals trend
    uae_section_header("📈 UAE Nationals Trend (2017–2024)")
    uae_trend = get_uae_nationality_trend("United Arab Emirates")
    if not uae_trend.empty:
        st.plotly_chart(
            line_trend(uae_trend, "academic_year", "student_count",
                       "UAE National Students Over Time",
                       color=UAE["green"], height=270),
            use_container_width=True,
        )

    # Top 5 expat nationalities
    uae_section_header("🌐 Top International Nationalities")
    expat = nat_yr[nat_yr["nationality_en"] != "United Arab Emirates"].head(10)
    if not expat.empty:
        st.plotly_chart(
            bar_h(expat.sort_values("student_count", ascending=True),
                  "student_count", "nationality_en",
                  "Top International Nationalities (excl. UAE)",
                  color_scale=["#fff3e0", UAE["gold"]], height=370),
            use_container_width=True,
        )


# ── Shared footer (same component India uses) ─────────────────────────────────
if SHARED_UI:
    render_footer()
else:
    st.divider()
    st.markdown(
        "<div style='text-align:center;color:#9e9e9e;font-size:0.75rem'>"
        "🇦🇪 UAE Dashboard · TutorCloud Global Schools Platform · "
        "Ministry of Education UAE Open Data · 2024-2025</div>",
        unsafe_allow_html=True,
    )
