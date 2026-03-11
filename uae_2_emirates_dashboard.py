"""
=================================================================
  pages/uae_2_emirates_dashboard.py  ──  UAE Emirates Dashboard
  
  Mirrors India's  pages/2_📊_State_Dashboard.py
  ─────────────────────────────────────────────
  Sidebar filters: Emirate · School Type · Curriculum · Rating
  Tab 1 · Overview   : map + school count bar + type donut
  Tab 2 · Enrollment : students by emirate/type bar charts
  Tab 3 · Performance: KHDA/ADEK rating distribution & heatmap
  Tab 4 · Curriculum : curriculum mix stacked bar & bubble chart
  Tab 5 · School List: searchable table + CSV export
=================================================================
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# ── Safe imports ──────────────────────────────────────────
_DB_OK = False
try:
    _ROOT = Path(__file__).parent.parent
    sys.path.insert(0, str(_ROOT))
    sys.path.insert(0, str(_ROOT / "src"))
    from src.utils.database import get_db_connection, release_db_connection
    _DB_OK = True
except Exception:
    try:
        from utils.database import get_db_connection, release_db_connection
        _DB_OK = True
    except Exception:
        pass

try:
    import ui_styles  # noqa
except Exception:
    pass

# ──────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────
RATING_ORDER  = ["Outstanding","Very Good","Good","Acceptable","Weak"]
RATING_COLOR  = {
    "Outstanding":"#2e7d32","Very Good":"#558b2f",
    "Good":"#f9a825","Acceptable":"#e65100","Weak":"#b71c1c",
}
RATING_SCORE  = {"Outstanding":5,"Very Good":4,"Good":3,"Acceptable":2,"Weak":1}

# ──────────────────────────────────────────────────────────
# DEMO DATA  (KHDA 2024-25 published aggregates)
# ──────────────────────────────────────────────────────────
def _demo() -> pd.DataFrame:
    rows = [
        # (emirate, type, curriculum, rating, students, lat, lon)
        ("Dubai","Private","UK","Outstanding",2800,25.2048,55.2708),
        ("Dubai","Private","American","Very Good",3200,25.1980,55.2793),
        ("Dubai","Private","Indian","Good",4100,25.2460,55.3100),
        ("Dubai","Government","Ministry of Education","Very Good",1200,25.2000,55.3200),
        ("Dubai","Private","International Baccalaureate","Outstanding",1800,25.1150,55.1950),
        ("Dubai","Private","French","Good",2100,25.2300,55.3000),
        ("Dubai","Private","German","Good",1100,25.2150,55.2800),
        ("Dubai","Private","American","Outstanding",2900,25.0657,55.1713),
        ("Abu Dhabi","Private","American","Very Good",2400,24.4539,54.3773),
        ("Abu Dhabi","Government","Ministry of Education","Good",800,24.4700,54.3900),
        ("Abu Dhabi","Private","UK","Outstanding",3100,24.4310,54.4360),
        ("Abu Dhabi","Private","Indian","Good",1900,24.5000,54.4000),
        ("Abu Dhabi","Government","Ministry of Education","Good",750,24.4620,54.3500),
        ("Abu Dhabi","Private","IB","Very Good",1600,24.4180,54.3250),
        ("Sharjah","Private","UK","Good",1800,25.3462,55.4209),
        ("Sharjah","Government","Ministry of Education","Good",600,25.3550,55.4300),
        ("Sharjah","Private","American","Acceptable",1400,25.3370,55.4100),
        ("Sharjah","Private","Indian","Good",1100,25.3600,55.4400),
        ("Ajman","Private","Indian","Good",1600,25.4052,55.5136),
        ("Ajman","Government","Ministry of Education","Good",500,25.4100,55.5200),
        ("Fujairah","Private","Indian","Good",1200,25.1288,56.3265),
        ("Fujairah","Government","Ministry of Education","Acceptable",400,25.1350,56.3300),
        ("Ras Al Khaimah","Private","Ministry of Education","Good",900,25.7889,31.9991),
        ("Ras Al Khaimah","Government","Ministry of Education","Acceptable",300,25.7950,32.0050),
        ("Umm Al Quwain","Private","UK","Good",700,25.5647,55.5539),
    ]
    df = pd.DataFrame(rows,columns=[
        "emirate","school_type","curriculum","overall_rating",
        "total_students","latitude","longitude"])
    df["school_id"]      = range(1,len(df)+1)
    df["rating_score"]   = df["overall_rating"].map(RATING_SCORE)
    df["name_en"]        = df.apply(
        lambda r: f"{r.emirate} {r.curriculum} School {r.name+1}",axis=1)
    df["zone"]           = df["emirate"]
    df["grade_range"]    = "KG1-G12"
    df["inspection_year"]= "2023-2024"
    df["inspecting_body"]= df["emirate"].map(
        lambda e: "KHDA" if e=="Dubai" else ("ADEK" if e=="Abu Dhabi" else "MOE"))
    df["source"]         = "DEMO"
    return df

# ──────────────────────────────────────────────────────────
# DATA LOADER
# ──────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_data() -> tuple[pd.DataFrame, bool]:
    if not _DB_OK:
        return _demo(), True
    try:
        conn = get_db_connection()
        try:
            df = pd.read_sql("""
                SELECT s.school_id, s.name_en, s.emirate, s.zone,
                       s.school_type, s.curriculum, s.grade_range,
                       s.latitude, s.longitude, s.source,
                       COALESCE(e.total_students,0)          AS total_students,
                       COALESCE(e.academic_year,'2024-2025') AS academic_year,
                       i.overall_rating, i.rating_score,
                       i.inspection_year, i.inspecting_body
                FROM uae_schools s
                LEFT JOIN uae_enrollment e ON s.school_id=e.school_id
                LEFT JOIN uae_inspection  i ON s.school_id=i.school_id
                WHERE s.is_active=TRUE
                ORDER BY s.emirate, s.name_en
            """, conn)
        finally:
            release_db_connection(conn)
        if not df.empty:
            return df, False
    except Exception:
        pass
    return _demo(), True

# ──────────────────────────────────────────────────────────
# SIDEBAR  (UAE-specific filters, no conflict with India keys)
# ──────────────────────────────────────────────────────────
def sidebar_filters(df_raw: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### 🇦🇪 Dashboard Filters")

    sel_em = st.sidebar.multiselect(
        "🏙️ Emirate",
        sorted(df_raw["emirate"].dropna().unique()),
        default=sorted(df_raw["emirate"].dropna().unique()),
        key="uae_em_filter",
    )
    sel_type = st.sidebar.multiselect(
        "🏫 School Type",
        sorted(df_raw["school_type"].dropna().unique()),
        default=sorted(df_raw["school_type"].dropna().unique()),
        key="uae_stype_filter",
    )
    sel_curr = st.sidebar.multiselect(
        "📚 Curriculum",
        sorted(df_raw["curriculum"].dropna().unique()),
        default=sorted(df_raw["curriculum"].dropna().unique()),
        key="uae_curr_filter",
    )
    avail = [r for r in RATING_ORDER if r in df_raw["overall_rating"].values]
    sel_rating = st.sidebar.multiselect(
        "🏆 Inspection Rating",
        avail, default=avail,
        key="uae_rating_filter",
    )

    df = df_raw.copy()
    if sel_em:     df = df[df["emirate"].isin(sel_em)]
    if sel_type:   df = df[df["school_type"].isin(sel_type)]
    if sel_curr:   df = df[df["curriculum"].isin(sel_curr)]
    if sel_rating and "overall_rating" in df.columns:
        df = df[df["overall_rating"].isin(sel_rating)]
    return df

# ──────────────────────────────────────────────────────────
# KPI ROW
# ──────────────────────────────────────────────────────────
def render_kpis(df: pd.DataFrame):
    n_schools  = df["school_id"].nunique()
    n_students = int(df["total_students"].sum())
    out_pct    = (
        f"{100*(df['overall_rating']=='Outstanding').sum()/max(n_schools,1):.0f}%"
        if "overall_rating" in df.columns else "N/A"
    )
    top_em = (
        df.groupby("emirate")["rating_score"].mean().idxmax()
        if "rating_score" in df.columns and df["rating_score"].notna().any()
        else "N/A"
    )
    top_curr = df["curriculum"].value_counts().idxmax() if df["curriculum"].notna().any() else "N/A"
    avg_stu  = f"{n_students//max(n_schools,1):,}"

    _c = ("background:{bg};border:1px solid {bdr};border-radius:12px;"
          "padding:18px 10px;text-align:center")
    data = [
        (f"{n_schools:,}", "🏫 Schools",    "#00732F","#e8f5e9"),
        (f"{n_students:,}","👩‍🎓 Students",  "#1565C0","#e3f2fd"),
        (out_pct,          "🌟 Outstanding", "#1b5e20","#f1f8e9"),
        (top_em,           "🏆 Top Emirate", "#C8102E","#fce4ec"),
        (top_curr,         "📚 Top Curriculum","#6a1b9a","#f3e5f5"),
        (avg_stu,          "📊 Avg/School",  "#e65100","#fff3e0"),
    ]
    for col,(val,lbl,color,bg) in zip(st.columns(len(data)), data):
        col.markdown(
            f"<div style='{_c.format(bg=bg,bdr=color)}'>"
            f"<div style='font-size:24px;font-weight:700;color:{color}'>{val}</div>"
            f"<div style='font-size:11px;color:#555;margin-top:3px'>{lbl}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ──────────────────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────────────────
def tab_overview(df):
    c1,c2 = st.columns([3,2])
    with c1:
        st.markdown("#### 📍 School Locations")
        if df["latitude"].notna().any():
            fig = px.scatter_mapbox(
                df.dropna(subset=["latitude","longitude"]),
                lat="latitude",lon="longitude",
                color="school_type",
                color_discrete_map={"Private":"#C8102E","Government":"#00732F"},
                hover_name="name_en",
                hover_data={"curriculum":True,"overall_rating":True,
                            "total_students":True,"latitude":False,"longitude":False},
                zoom=5.5, center={"lat":24.2,"lon":54.5},
                mapbox_style="carto-positron", height=400,
            )
            fig.update_layout(margin=dict(r=0,t=0,l=0,b=0),
                              legend=dict(orientation="h",y=-0.08))
            st.plotly_chart(fig, use_container_width=True)
        else:
            ec=(df.groupby("emirate")["school_id"].nunique()
                .sort_values().reset_index())
            ec.columns=["emirate","schools"]
            fig=px.bar(ec,x="schools",y="emirate",orientation="h",
                       color="schools",
                       color_continuous_scale=["#c8f5c8","#00732F"],
                       text="schools",height=380,
                       labels={"schools":"Schools","emirate":""})
            fig.update_traces(textposition="outside")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### Schools by Emirate")
        em=(df.groupby("emirate")["school_id"].nunique()
            .reset_index().sort_values("school_id",ascending=False))
        em.columns=["emirate","schools"]
        fig2=px.bar(em,x="schools",y="emirate",orientation="h",
                    color="schools",
                    color_continuous_scale=["#c8f5c8","#00732F"],
                    text="schools",height=260,
                    labels={"schools":"Schools","emirate":""})
        fig2.update_traces(textposition="outside")
        fig2.update_layout(coloraxis_showscale=False,margin=dict(t=0,b=0))
        st.plotly_chart(fig2, use_container_width=True)

        tc=df.groupby("school_type")["school_id"].nunique()
        fig3=go.Figure(go.Pie(
            labels=tc.index,values=tc.values,hole=0.5,
            marker_colors=["#00732F","#C8102E"]))
        fig3.update_layout(height=210,margin=dict(t=10,b=10,l=10,r=10),
                           legend=dict(orientation="h",y=-0.15))
        st.plotly_chart(fig3, use_container_width=True)


def tab_enrollment(df):
    c1,c2=st.columns(2)
    with c1:
        enr=(df.groupby("emirate")["total_students"]
             .sum().reset_index().sort_values("total_students",ascending=False))
        fig=px.bar(enr,x="emirate",y="total_students",
                   color="total_students",
                   color_continuous_scale=["#bbdefb","#1565C0"],
                   text=enr["total_students"].apply(lambda x:f"{x:,}"),
                   title="Students by Emirate",
                   labels={"total_students":"Students","emirate":""})
        fig.update_traces(textposition="outside")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        enr2=(df.groupby(["emirate","school_type"])["total_students"]
              .sum().reset_index())
        fig2=px.bar(enr2,x="emirate",y="total_students",color="school_type",
                    color_discrete_map={"Private":"#C8102E","Government":"#00732F"},
                    barmode="group",
                    title="Govt vs Private Students",
                    labels={"total_students":"Students","emirate":""})
        fig2.update_layout(legend=dict(orientation="h",y=-0.2))
        st.plotly_chart(fig2, use_container_width=True)

    n=df["school_id"].nunique(); s=int(df["total_students"].sum())
    m1,m2,m3=st.columns(3)
    m1.metric("📊 Total Students",f"{s:,}")
    m2.metric("🏫 Total Schools",f"{n:,}")
    m3.metric("👩‍🎓 Avg/School",f"{s//max(n,1):,}")


def tab_performance(df):
    if "overall_rating" not in df or df["overall_rating"].isna().all():
        st.info("Load KHDA/ADEK inspection data to see performance metrics.")
        return
    c1,c2=st.columns(2)
    with c1:
        rc=(df["overall_rating"].value_counts()
            .reindex(RATING_ORDER).dropna().reset_index())
        rc.columns=["rating","count"]
        fig=px.bar(rc,x="rating",y="count",color="rating",
                   color_discrete_map=RATING_COLOR,text="count",
                   title="Inspection Rating Distribution",
                   labels={"rating":"","count":"Schools"})
        fig.update_layout(showlegend=False)
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        heat=(df.groupby(["emirate","overall_rating"])["school_id"]
              .nunique().reset_index()
              .pivot(index="emirate",columns="overall_rating",values="school_id")
              .reindex(columns=RATING_ORDER).fillna(0))
        fig2=px.imshow(heat,color_continuous_scale="YlGn",
                       aspect="auto",title="Rating Heatmap by Emirate",
                       labels={"color":"Schools"})
        st.plotly_chart(fig2, use_container_width=True)

    sc=(df.groupby("emirate")["rating_score"].mean().reset_index()
        .rename(columns={"rating_score":"avg"})
        .sort_values("avg",ascending=False))
    fig3=px.bar(sc,x="emirate",y="avg",
                color="avg",color_continuous_scale=["#fff9c4","#1b5e20"],
                text=sc["avg"].apply(lambda x:f"{x:.2f}"),
                title="Avg Inspection Score by Emirate (5=Outstanding)",
                range_y=[0,5.5],
                labels={"avg":"Avg Score","emirate":""})
    fig3.add_hline(y=4,line_dash="dot",line_color="blue",
                   annotation_text="Very Good (4.0)")
    fig3.add_hline(y=3,line_dash="dot",line_color="orange",
                   annotation_text="Good (3.0)")
    fig3.update_layout(coloraxis_showscale=False)
    fig3.update_traces(textposition="outside")
    st.plotly_chart(fig3, use_container_width=True)


def tab_curriculum(df):
    if df["curriculum"].isna().all():
        st.info("Curriculum data not available yet.")
        return
    c1,c2=st.columns(2)
    with c1:
        cc=(df.groupby("curriculum")["school_id"].nunique()
            .sort_values(ascending=False).head(12).reset_index())
        cc.columns=["curriculum","schools"]
        fig=px.bar(cc,x="schools",y="curriculum",orientation="h",
                   color="schools",color_continuous_scale=["#e8f5e9","#1b5e20"],
                   text="schools",title="Top Curricula",
                   labels={"schools":"Schools","curriculum":""})
        fig.update_traces(textposition="outside")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        top8=cc["curriculum"].head(8).tolist()
        ce=(df[df["curriculum"].isin(top8)]
            .groupby(["emirate","curriculum"])["school_id"]
            .nunique().reset_index())
        ce.columns=["emirate","curriculum","schools"]
        fig2=px.bar(ce,x="emirate",y="schools",color="curriculum",
                    barmode="stack",title="Curriculum Mix by Emirate",
                    labels={"schools":"Schools","emirate":""})
        fig2.update_layout(legend=dict(orientation="h",y=-0.3,font=dict(size=10)))
        st.plotly_chart(fig2, use_container_width=True)

    if "rating_score" in df.columns and df["rating_score"].notna().any():
        cr=(df.groupby("curriculum")
            .agg(schools=("school_id","nunique"),avg=("rating_score","mean"),
                 students=("total_students","sum"))
            .reset_index().query("schools>=2")
            .sort_values("avg",ascending=False).head(12))
        fig3=px.scatter(cr,x="avg",y="curriculum",size="students",color="avg",
                        color_continuous_scale="YlGn",range_x=[1,5.5],
                        title="Curriculum Quality vs Enrollment",
                        labels={"avg":"Avg Score","curriculum":"","students":"Students"})
        st.plotly_chart(fig3, use_container_width=True)


def tab_school_list(df):
    search=st.text_input("🔍 Search school name",
                         placeholder="e.g. British, Dubai, American...",
                         key="uae_ed_search")
    d=df.copy()
    if search:
        d=d[d["name_en"].str.contains(search,case=False,na=False)]
    show=[c for c in["name_en","emirate","school_type","curriculum",
                      "overall_rating","total_students","grade_range","zone"]
          if c in d.columns]
    tbl=d[show].copy()
    tbl.columns=[c.replace("_"," ").title() for c in show]
    _icon={"Outstanding":"🟢","Very Good":"🔵","Good":"🟡","Acceptable":"🟠","Weak":"🔴"}
    if "Overall Rating" in tbl.columns:
        tbl["Overall Rating"]=tbl["Overall Rating"].apply(
            lambda r:f"{_icon.get(str(r),'⚪')} {r}" if pd.notna(r) else "—")
    if "Total Students" in tbl.columns:
        tbl["Total Students"]=tbl["Total Students"].apply(
            lambda x:f"{int(x):,}" if pd.notna(x) and x>0 else "—")
    st.markdown(f"**{len(tbl):,} schools** match filters")
    st.dataframe(tbl,use_container_width=True,height=460,hide_index=True)
    st.download_button("⬇️ Download CSV",d.to_csv(index=False).encode(),
                       "uae_schools.csv","text/csv")

# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────
def main():
    st.markdown(
        "<h1 style='color:#00732F;margin-bottom:0'>"
        "🇦🇪 Emirates Dashboard</h1>"
        "<p style='color:#888;margin-top:2px'>"
        "School Intelligence · KHDA &amp; MOE Data · 2024-25</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    df_raw, is_demo = load_data()
    if is_demo:
        st.info(
            "ℹ️ **Demo Mode** — Illustrative data based on KHDA 2024-25 aggregates. "
            "Download CSVs and run the ETL pipeline to load live data.",
            icon="🇦🇪",
        )

    df = sidebar_filters(df_raw)
    if df.empty:
        st.warning("No data matches the selected filters.")
        return

    render_kpis(df)
    st.markdown("<br>", unsafe_allow_html=True)

    t1,t2,t3,t4,t5=st.tabs([
        "🗺️ Overview","👩‍🎓 Enrollment",
        "🏆 Performance","📚 Curriculum","📋 School List"])
    with t1: tab_overview(df)
    with t2: tab_enrollment(df)
    with t3: tab_performance(df)
    with t4: tab_curriculum(df)
    with t5: tab_school_list(df)

    st.markdown("---")
    st.caption(
        ("⚠️ Demo mode · Based on KHDA 2024-25 published reports"
         if is_demo else
         f"Live data · KHDA/MOE/Bayanat.ae · {pd.Timestamp.now().strftime('%d %b %Y')}")
    )

if __name__ == "__main__":
    main()
