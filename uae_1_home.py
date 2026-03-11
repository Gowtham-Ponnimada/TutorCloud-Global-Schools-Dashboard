"""
=================================================================
  pages/uae_1_home.py  ──  UAE Home Page
  
  Mirrors India's  pages/1_🏠_Home.py  structure
  ─────────────────────────────────────────────
  • Welcome banner with UAE flag & branding
  • KPI summary cards (total schools, students, emirates)
  • Quick-access tiles linking to Emirates Dashboard & Analytics
  • Data source status (shows Demo until ETL loads real data)
  • Completely independent from all India pages
=================================================================
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path

# ── Safe utility imports ──────────────────────────────────
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
# DATA  (live DB → demo fallback)
# ──────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_uae_home_kpis() -> dict:
    """Returns headline KPIs. Falls back to demo values."""
    if _DB_OK:
        try:
            conn = get_db_connection()
            try:
                df = pd.read_sql("""
                    SELECT
                        COUNT(*)                                    AS total_schools,
                        COALESCE(SUM(e.total_students),0)           AS total_students,
                        COUNT(DISTINCT s.emirate)                   AS emirate_count,
                        COUNT(*) FILTER(WHERE s.school_type='Private') AS private_schools,
                        COUNT(*) FILTER(WHERE s.school_type='Government') AS govt_schools,
                        ROUND(100.0*COUNT(*)
                            FILTER(WHERE i.overall_rating='Outstanding')
                            /NULLIF(COUNT(*),0),1)                  AS outstanding_pct
                    FROM uae_schools s
                    LEFT JOIN uae_enrollment e ON s.school_id=e.school_id
                    LEFT JOIN uae_inspection  i ON s.school_id=i.school_id
                    WHERE s.is_active=TRUE
                """, conn)
            finally:
                release_db_connection(conn)
            if not df.empty and df.iloc[0]["total_schools"] > 0:
                row = df.iloc[0]
                return {
                    "total_schools":  int(row["total_schools"]),
                    "total_students": int(row["total_students"]),
                    "emirate_count":  int(row["emirate_count"]),
                    "private_schools":int(row["private_schools"]),
                    "govt_schools":   int(row["govt_schools"]),
                    "outstanding_pct":float(row["outstanding_pct"] or 0),
                    "is_demo": False,
                }
        except Exception:
            pass

    # Demo values (KHDA 2024-25 aggregates)
    return {
        "total_schools":  1_312,
        "total_students": 1_260_000,
        "emirate_count":  7,
        "private_schools": 794,
        "govt_schools":   518,
        "outstanding_pct": 18.5,
        "is_demo": True,
    }

@st.cache_data(ttl=3600, show_spinner=False)
def get_emirate_school_counts() -> pd.DataFrame:
    """School counts per emirate for the home sparkbar."""
    if _DB_OK:
        try:
            conn = get_db_connection()
            try:
                df = pd.read_sql("""
                    SELECT emirate, COUNT(*) AS schools
                    FROM uae_schools WHERE is_active=TRUE
                    GROUP BY emirate ORDER BY schools DESC
                """, conn)
            finally:
                release_db_connection(conn)
            if not df.empty:
                return df
        except Exception:
            pass
    # Demo fallback (published 2024-25 estimates)
    return pd.DataFrame({
        "emirate": ["Abu Dhabi","Dubai","Sharjah","Ajman",
                    "Ras Al Khaimah","Fujairah","Umm Al Quwain"],
        "schools": [302, 216, 107, 64, 45, 35, 12],
    })

# ──────────────────────────────────────────────────────────
# RENDER
# ──────────────────────────────────────────────────────────
def main():
    kpis   = get_uae_home_kpis()
    em_df  = get_emirate_school_counts()

    # ── Banner ────────────────────────────────────────────
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#00732F 0%,#1a472a 60%,#C8102E 100%);
                    border-radius:16px;padding:32px 40px;margin-bottom:24px">
          <h1 style="color:white;margin:0;font-size:2.2rem">
            🇦🇪 TutorCloud UAE
          </h1>
          <p style="color:rgba(255,255,255,.85);margin:8px 0 0;font-size:1.1rem">
            School Intelligence Platform &nbsp;·&nbsp; Knowledge &amp; Human
            Development Authority Data &nbsp;·&nbsp; Academic Year 2024-25
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if kpis["is_demo"]:
        st.info(
            "ℹ️ **Demo Mode** — Showing published KHDA 2024-25 aggregates. "
            "Run `02_etl_uae_to_postgres.py` after downloading CSVs for live data.",
            icon="🇦🇪",
        )

    # ── KPI cards ─────────────────────────────────────────
    _c = ("background:{bg};border:1px solid {border};border-radius:12px;"
          "padding:20px 14px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.07)")
    kpi_rows = [
        (f"{kpis['total_schools']:,}",  "🏫 Total Schools",       "#00732F","#e8f5e9"),
        (f"{kpis['total_students']:,.0f}","👩‍🎓 Total Students",    "#1565C0","#e3f2fd"),
        (f"{kpis['emirate_count']}",    "🏙️ Emirates",            "#6a1b9a","#f3e5f5"),
        (f"{kpis['private_schools']:,}","🏢 Private Schools",      "#C8102E","#fce4ec"),
        (f"{kpis['govt_schools']:,}",   "🏛️ Govt Schools",        "#e65100","#fff3e0"),
        (f"{kpis['outstanding_pct']:.1f}%","🌟 Outstanding",       "#1b5e20","#f1f8e9"),
    ]
    cols = st.columns(len(kpi_rows))
    for col, (val, label, color, bg) in zip(cols, kpi_rows):
        with col:
            st.markdown(
                f"<div style='{_c.format(bg=bg, border=color)}'>"
                f"<div style='font-size:26px;font-weight:700;color:{color}'>{val}</div>"
                f"<div style='font-size:12px;color:#555;margin-top:4px'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Emirates bar + quick links ─────────────────────────
    col_chart, col_links = st.columns([3, 2])

    with col_chart:
        st.markdown("#### 🏙️ Schools by Emirate")
        fig = px.bar(
            em_df, x="schools", y="emirate", orientation="h",
            color="schools",
            color_continuous_scale=["#c8f5c8", "#00732F"],
            text="schools",
            labels={"schools": "Schools", "emirate": ""},
            height=310,
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            coloraxis_showscale=False,
            margin={"t": 0, "b": 0, "l": 0, "r": 40},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_links:
        st.markdown("#### 🚀 Quick Access")
        tiles = [
            ("📊", "Emirates Dashboard",
             "School distribution, performance ratings & curriculum mix by emirate",
             "#e8f5e9", "#00732F"),
            ("📈", "Analytics",
             "Enrollment trends, inspection score trends & data deep-dives",
             "#e3f2fd", "#1565C0"),
        ]
        for icon, title, desc, bg, color in tiles:
            st.markdown(
                f"<div style='background:{bg};border:1px solid {color};"
                f"border-radius:12px;padding:16px 18px;margin-bottom:12px'>"
                f"<div style='font-size:20px;font-weight:700;color:{color}'>"
                f"{icon} {title}</div>"
                f"<div style='font-size:13px;color:#555;margin-top:4px'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.caption("Use the 🌍 **Select Region** dropdown to switch to India.")

    # ── Data source status ─────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📂 Data Source Status")
    src_data = {
        "Source": ["KHDA Dubai (Private Schools)", "MOE (All Emirates)",
                   "Bayanat.ae (GE Public/Private)", "ADEK (Abu Dhabi)"],
        "Status": ["⬇️ Download XLSX" if kpis["is_demo"] else "✅ Loaded",
                   "⬇️ Download XLSX" if kpis["is_demo"] else "✅ Loaded",
                   "⬇️ Download CSV"  if kpis["is_demo"] else "✅ Loaded",
                   "📋 Manual export" if kpis["is_demo"] else "✅ Loaded"],
        "URL": [
            "https://web.khda.gov.ae/KHDA/media/KHDA/DubaiPrivateSchoolsOpenData.xlsx",
            "https://www.moe.gov.ae/En/OpenData/pages/home.aspx",
            "https://admin.bayanat.ae/Home/DatasetInfo?dID=1dHDH5iN6ADu2-M-NAE0n8aY1PCoxgGM7hVVP6E86TI",
            "https://www.adek.gov.ae/en/Education-System/Private-Schools",
        ],
    }
    st.dataframe(
        pd.DataFrame(src_data),
        use_container_width=True,
        hide_index=True,
        column_config={"URL": st.column_config.LinkColumn("Download URL")},
    )

    st.caption(
        "Once CSVs are downloaded, run: "
        "`cd ~/tutorcloud/etl && python 02_etl_uae_to_postgres.py`"
    )

if __name__ == "__main__":
    main()
