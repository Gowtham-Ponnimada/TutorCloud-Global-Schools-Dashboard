"""
TutorCloud Global Dashboard - Home Page (Polished Final v3.0)
Version 3.0 - Professional Cards + Clickable Navigation + Silent Loading
Date: 2026-02-18

All issues resolved:
- Individual card styling with blue borders
- Charts with no cutoff (increased margins)
- Clickable navigation to State Dashboard & Analytics
- Silent background loading (no spinner popups)
"""

import streamlit as st
import sys
import pandas as pd
import plotly.express as px
from ui_styles import render_region_badge

# Add parent directory to path for imports
sys.path.insert(0, '.')

# Import code mappings
from code_mappings import (
    get_db_connection,
    SCHEMA,
    TABLE_SCHOOL_PROFILE,
    TABLE_ENROLLMENT_SECONDARY as TABLE_ENROLLMENT,
    TABLE_TEACHER,
    COL_STATE_NAME,
    format_number,
    format_ptr
)

# Import UI components
from ui_components import (
    COLORS,
    CHART_COLORS_GRADIENT
)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="TutorCloud - National Overview",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="auto"
)

# ── Region bootstrap v_final (DIAGNOSE_AND_FIX_PERMANENT) ───────────────────
# Single authoritative region bootstrap.  render_region_badge() called ONCE.
# Do not add additional render_region_badge() calls elsewhere in this file.
try:
    from ui_styles import render_region_badge as _render_rb
except ImportError:
    _render_rb = None

if _render_rb:
    _render_rb()

from utils.uae_page_renderer import render_uae_home
_current_region = st.session_state.get("selected_region", "India")
if _current_region == "UAE":
    render_uae_home()
    st.stop()
elif _current_region != "India":
    st.markdown(
        "<div style='text-align:center;padding:80px 20px'>"
        "<h1>🌍 Coming Soon</h1>"
        "<p style='font-size:1.1rem;color:#666'>"
        "This region is not yet available. Select <strong>India</strong> to continue.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()
# ── End region bootstrap ─────────────────────────────────────────────────────


# ============================================================================
# PROFESSIONAL CARD-BASED CSS
# ============================================================================

def inject_card_css():
    """Inject professional card-based CSS with individual borders"""
    css = f"""
    <style>
    /* ===== GLOBAL STYLES ===== */
    .main {{
        background-color: #F5F7FA;
        padding: 1rem;
    }}
    
    /* ===== HIDE STREAMLIT LOADING SPINNER ===== */
    .stSpinner > div {{
        display: none !important;
    }}
    
    /* ===== RESPONSIVE TYPOGRAPHY ===== */
    h1 {{
        color: {COLORS['primary']};
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 600;
        padding-bottom: 10px;
        margin-bottom: 20px;
        font-size: clamp(1.5rem, 4vw, 2.5rem);
    }}
    
    h2 {{
        color: {COLORS['primary']};
        font-size: clamp(1.2rem, 3vw, 1.5rem);
        font-weight: 600;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: none;
    }}
    
    /* ===== INDIVIDUAL KPI CARDS WITH BORDERS ===== */
    [data-testid="stMetric"] {{
        background-color: white;
        padding: 1.2rem;
        border-radius: 12px;
        border: 3px solid {COLORS['primary']};
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    
    [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }}
    
    [data-testid="stMetricValue"] {{
        font-size: clamp(1.3rem, 3vw, 2rem) !important;
        font-weight: 700;
        color: {COLORS['primary']};
        overflow: visible !important;
        white-space: nowrap !important;
    }}
    
    [data-testid="stMetricLabel"] {{
        font-size: clamp(0.7rem, 2vw, 0.9rem);
        font-weight: 600;
        color: {COLORS['medium']};
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }}
    
    /* ===== SECTION CONTAINERS (CARDS) ===== */
    .dashboard-card {{
        background-color: white;
        padding: 2rem;
        border-radius: 12px;
        border: 3px solid {COLORS['primary']};
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
    }}
    
    .dashboard-card h2 {{
        color: {COLORS['primary']};
        font-weight: 600;
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid {COLORS['lighter']};
    }}
    
    /* ===== CLICKABLE NAVIGATION CARDS ===== */
    .nav-card {{
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 3px solid {COLORS['primary']};
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: block;
        height: 100%;
    }}
    
    .nav-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        border-color: {COLORS['secondary']};
    }}
    
    .nav-card h3 {{
        color: {COLORS['primary']};
        font-weight: 600;
        margin-bottom: 0.5rem;
    }}
    
    .nav-card p {{
        color: {COLORS['medium']};
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
    }}
    
    .nav-card ul {{
        color: {COLORS['medium']};
        font-size: 0.9rem;
        margin-left: 1rem;
    }}
    
    /* ===== INFO CARDS (Key Insights) ===== */
    .stAlert {{
        border-radius: 12px;
        border: 3px solid;
        font-size: clamp(0.85rem, 2vw, 0.95rem);
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    
    /* ===== MOBILE: Stack everything ===== */
    @media (max-width: 480px) {{
        [data-testid="stHorizontalBlock"] {{
            flex-direction: column !important;
            gap: 1rem;
        }}
        
        [data-testid="stHorizontalBlock"] > div {{
            width: 100% !important;
            margin-bottom: 0;
        }}
        
        .dashboard-card {{
            padding: 1.2rem;
        }}
        
        [data-testid="stMetric"] {{
            padding: 1rem;
        }}
    }}
    
    /* ===== TABLET: 2-column layout ===== */
    @media (min-width: 481px) and (max-width: 768px) {{
        [data-testid="stMetricValue"] {{
            font-size: 1.5rem !important;
        }}
    }}
    
    /* ===== LAPTOP: 3-column layout ===== */
    @media (min-width: 769px) and (max-width: 1024px) {{
        [data-testid="stMetricValue"] {{
            font-size: 1.7rem !important;
        }}
    }}
    
    /* ===== DESKTOP: Full layout ===== */
    @media (min-width: 1025px) {{
        [data-testid="stMetricValue"] {{
            font-size: 2rem !important;
        }}
    }}
    
    /* ===== HIDE MOBILE HINT ON DESKTOP ===== */
    .mobile-nav-hint {{
        display: none;
    }}
    
    @media (max-width: 480px) {{
        .mobile-nav-hint {{
            display: block;
            background-color: {COLORS['info']};
            color: white;
            padding: 0.6rem;
            text-align: center;
            border-radius: 8px;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }}
    }}
    
    /* ===== DIVIDER ===== */
    hr {{
        margin: 2rem 0;
        border: none;
        border-top: 2px solid {COLORS['lighter']};
    }}
    
    /* ===== RESPONSIVE COLUMNS ===== */
    @media (max-width: 768px) {{
        [data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
        }}
    }}
    
    /* ===== MOBILE: Hide sidebar by default ===== */
    @media (max-width: 768px) {{
        section[data-testid="stSidebar"] {{
            width: 0px !important;
        }}
        
        section[data-testid="stSidebar"][aria-expanded="true"] {{
            width: 80vw !important;
        }}
    }}
    
    /* ===== LOADING OVERLAY (Silent background loading) ===== */
    .loading-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.7);
        z-index: 9999;
        display: none;
        pointer-events: none;
    }}
    
    .loading-overlay.active {{
        display: block;
        pointer-events: all;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_card_css()
@st.cache_data(ttl=3600, show_spinner=False)
def get_national_summary():
    """Fetch national-level summary statistics."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        query = f"""
        WITH enrollment_data AS (
            SELECT
                e.pseudocode,
                SUM(
                    COALESCE(e.cpp_b, 0) + COALESCE(e.cpp_g, 0) +
                    COALESCE(e.c1_b, 0) + COALESCE(e.c1_g, 0) +
                    COALESCE(e.c2_b, 0) + COALESCE(e.c2_g, 0) +
                    COALESCE(e.c3_b, 0) + COALESCE(e.c3_g, 0) +
                    COALESCE(e.c4_b, 0) + COALESCE(e.c4_g, 0) +
                    COALESCE(e.c5_b, 0) + COALESCE(e.c5_g, 0) +
                    COALESCE(e.c6_b, 0) + COALESCE(e.c6_g, 0) +
                    COALESCE(e.c7_b, 0) + COALESCE(e.c7_g, 0) +
                    COALESCE(e.c8_b, 0) + COALESCE(e.c8_g, 0) +
                    COALESCE(e.c9_b, 0) + COALESCE(e.c9_g, 0) +
                    COALESCE(e.c10_b, 0) + COALESCE(e.c10_g, 0) +
                    COALESCE(e.c11_b, 0) + COALESCE(e.c11_g, 0) +
                    COALESCE(e.c12_b, 0) + COALESCE(e.c12_g, 0)
                ) AS total_students
            FROM {SCHEMA}.{TABLE_ENROLLMENT} e
            GROUP BY e.pseudocode
        ),
        teacher_data AS (
            SELECT
                pseudocode,
                MAX(COALESCE(total_tch, 0)) AS total_teachers
            FROM {SCHEMA}.{TABLE_TEACHER}
            GROUP BY pseudocode
        )
        SELECT
            COUNT(DISTINCT sp.pseudocode) AS total_schools,
            COUNT(DISTINCT sp.{COL_STATE_NAME}) AS total_states,
            COALESCE(SUM(ed.total_students), 0) AS total_students,
            COALESCE(SUM(td.total_teachers), 0) AS total_teachers,
            CASE 
                WHEN SUM(td.total_teachers) > 0 
                THEN ROUND(SUM(ed.total_students)::numeric / SUM(td.total_teachers), 0)
                ELSE NULL 
            END AS ptr,
            CASE 
                WHEN COUNT(DISTINCT sp.pseudocode) > 0 
                THEN ROUND(SUM(ed.total_students)::numeric / COUNT(DISTINCT sp.pseudocode), 0)
                ELSE 0 
            END AS students_per_school
        FROM {SCHEMA}.{TABLE_SCHOOL_PROFILE} sp
        LEFT JOIN enrollment_data ed ON sp.pseudocode = ed.pseudocode
        LEFT JOIN teacher_data td ON sp.pseudocode = td.pseudocode
        """
        
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return {
                'total_schools': result[0],
                'total_states': result[1],
                'total_students': result[2],
                'total_teachers': result[3],
                'ptr': result[4],
                'students_per_school': result[5]
            }
        return None
    except Exception as e:
        st.error(f"Error fetching national summary: {str(e)}")
        if conn:
            conn.close()
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def get_top_states_by_schools(limit=10):
    """Fetch top states by school count."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        query = f"""
        SELECT
            UPPER(sp.{COL_STATE_NAME}) as state,
            COUNT(DISTINCT sp.pseudocode) AS total_schools
        FROM {SCHEMA}.{TABLE_SCHOOL_PROFILE} sp
        WHERE sp.{COL_STATE_NAME} IS NOT NULL
        GROUP BY UPPER(sp.{COL_STATE_NAME})
        ORDER BY total_schools DESC
        LIMIT %s
        """
        
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching top states: {str(e)}")
        if conn:
            conn.close()
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_top_states_by_students(limit=20):
    """Fetch top 20 states by student enrollment."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        query = f"""
        WITH enrollment_data AS (
            SELECT
                e.pseudocode,
                SUM(
                    COALESCE(e.cpp_b, 0) + COALESCE(e.cpp_g, 0) +
                    COALESCE(e.c1_b, 0) + COALESCE(e.c1_g, 0) +
                    COALESCE(e.c2_b, 0) + COALESCE(e.c2_g, 0) +
                    COALESCE(e.c3_b, 0) + COALESCE(e.c3_g, 0) +
                    COALESCE(e.c4_b, 0) + COALESCE(e.c4_g, 0) +
                    COALESCE(e.c5_b, 0) + COALESCE(e.c5_g, 0) +
                    COALESCE(e.c6_b, 0) + COALESCE(e.c6_g, 0) +
                    COALESCE(e.c7_b, 0) + COALESCE(e.c7_g, 0) +
                    COALESCE(e.c8_b, 0) + COALESCE(e.c8_g, 0) +
                    COALESCE(e.c9_b, 0) + COALESCE(e.c9_g, 0) +
                    COALESCE(e.c10_b, 0) + COALESCE(e.c10_g, 0) +
                    COALESCE(e.c11_b, 0) + COALESCE(e.c11_g, 0) +
                    COALESCE(e.c12_b, 0) + COALESCE(e.c12_g, 0)
                ) AS total_students
            FROM {SCHEMA}.{TABLE_ENROLLMENT} e
            GROUP BY e.pseudocode
        )
        SELECT
            UPPER(sp.{COL_STATE_NAME}) as state,
            COALESCE(SUM(ed.total_students), 0) AS total_students
        FROM {SCHEMA}.{TABLE_SCHOOL_PROFILE} sp
        LEFT JOIN enrollment_data ed ON sp.pseudocode = ed.pseudocode
        WHERE sp.{COL_STATE_NAME} IS NOT NULL
        GROUP BY UPPER(sp.{COL_STATE_NAME})
        ORDER BY total_students DESC
        LIMIT %s
        """
        
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching top states by enrollment: {str(e)}")
        if conn:
            conn.close()
        return pd.DataFrame()

# ============================================================================
# MAIN DASHBOARD LAYOUT
# ============================================================================

# Page Header
st.markdown("# 🏠 TutorCloud Global Dashboard")
st.markdown("**National K-12 Education Overview - India 2024-25**")
st.markdown("---")

# Mobile Navigation Hint (only on phones)
st.markdown(
    '<div class="mobile-nav-hint">📱 Tap menu icon (☰) to navigate</div>',
    unsafe_allow_html=True
)

# Fetch data silently (no spinner popup)
summary = get_national_summary()
df_top_schools = get_top_states_by_schools(limit=10)
df_top_students = get_top_states_by_students(limit=20)

if summary:
    # ========================================================================
    # SECTION 1: NATIONAL OVERVIEW (INDIVIDUAL BORDERED KPI CARDS)
    # ========================================================================
    
    st.markdown("## 📊 National Overview")
    
    # Row 1: States & Schools & Students
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="TOTAL STATES/UTs",
            value=f"{summary['total_states']}"
        )
    
    with col2:
        st.metric(
            label="TOTAL SCHOOLS",
            value=f"{summary['total_schools']:,}"
        )
    
    with col3:
        st.metric(
            label="TOTAL STUDENTS",
            value=f"{summary['total_students']:,}"
        )
    
    # Row 2: Teachers & PTR & Students/School
    col4, col5, col6 = st.columns(3)
    
    with col4:
        st.metric(
            label="TOTAL TEACHERS",
            value=f"{summary['total_teachers']:,}"
        )
    
    with col5:
        st.metric(
            label="PTR (NATIONAL)",
            value=f"{int(summary['ptr'])}:1" if summary['ptr'] else "N/A"
        )
    
    with col6:
        st.metric(
            label="STUDENTS/SCHOOL",
            value=f"{summary['students_per_school']:,}"
        )
    
    # ========================================================================
    # SECTION 2: TOP 10 STATES BY SCHOOL COUNT
    # ========================================================================
    
    st.markdown("## 🏆 Top 10 States by School Count")
    
    if not df_top_schools.empty:
        # Chart with NO CUTOFF (extra margin)
        fig = px.bar(
            df_top_schools,
            x='state',
            y='total_schools',
            labels={'total_schools': 'Total Schools', 'state': ''},
            color='total_schools',
            color_continuous_scale=CHART_COLORS_GRADIENT,
            text='total_schools'
        )
        
        fig.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside',
            marker_line_color='white',
            marker_line_width=1.5,
            textfont_size=11
        )
        
        fig.update_layout(
            height=480,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'family': 'Segoe UI', 'color': COLORS['dark'], 'size': 11},
            xaxis_tickangle=-45,
            showlegend=False,
            xaxis=dict(
                showgrid=False,
                title='',
                tickmode='linear',
                tickfont=dict(size=10)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=COLORS['lightest'],
                title='Total Schools',
                titlefont=dict(size=12)
            ),
            margin=dict(l=70, r=50, t=50, b=150)  # Extra bottom margin (150px)
        )
        
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    
    # ========================================================================
    # SECTION 3: TOP 20 STATES BY STUDENT ENROLLMENT
    # ========================================================================
    
    st.markdown("## 📚 Top 20 States by Student Enrollment")
    
    if not df_top_students.empty:
        # Chart with NO CUTOFF (extra margin)
        fig = px.bar(
            df_top_students,
            x='state',
            y='total_students',
            labels={'total_students': 'Total Students', 'state': ''},
            color='total_students',
            color_continuous_scale=CHART_COLORS_GRADIENT,
            text='total_students'
        )
        
        fig.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside',
            marker_line_color='white',
            marker_line_width=1.5,
            textfont_size=10
        )
        
        fig.update_layout(
            height=480,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font={'family': 'Segoe UI', 'color': COLORS['dark'], 'size': 10},
            xaxis_tickangle=-45,
            showlegend=False,
            xaxis=dict(
                showgrid=False,
                title='',
                tickmode='linear',
                tickfont=dict(size=9)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=COLORS['lightest'],
                title='Total Students',
                titlefont=dict(size=12)
            ),
            margin=dict(l=70, r=50, t=50, b=150)  # Extra bottom margin (150px)
        )
        
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    
    # ========================================================================
    # SECTION 4: KEY INSIGHTS
    # ========================================================================
    
    st.markdown("## 💡 Key Insights")
    
    insight_col1, insight_col2, insight_col3 = st.columns(3)
    
    with insight_col1:
        st.info(f"""
        **📚 School Coverage**
        
        India has **{summary['total_schools']:,}** schools serving **{summary['total_students']:,}** students across **{summary['total_states']}** states and union territories.
        """)
    
    with insight_col2:
        st.success(f"""
        **👨‍🏫 Teaching Staff**
        
        With **{summary['total_teachers']:,}** teachers nationwide, the national PTR stands at **{int(summary['ptr'])}:1**, indicating the student-to-teacher ratio.
        """)
    
    with insight_col3:
        st.warning(f"""
        **🏫 School Size**
        
        Average school size is **{summary['students_per_school']:,}** students per school, with significant variation across states and regions.
        """)
    
    # ========================================================================
    # SECTION 5: EXPLORE MORE (CLICKABLE NAVIGATION CARDS)
    # ========================================================================
    
    st.markdown("## 🧭 Explore More")
    
    nav_col1, nav_col2 = st.columns(2)
    
    with nav_col1:
        # State Dashboard link - opens in new tab
        st.markdown("""
        <a href="/State_Dashboard?region=India" target="_blank" style="
            display: inline-block;
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white !important;
            text-align: center;
            text-decoration: none !important;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1.1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            border: 3px solid #1e88e5;
        ">
            📊 State Dashboard
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style='padding: 0.5rem; color: #757575; font-size: 0.9rem;'>
        Drill down into state, district, and block-level data with advanced filtering.
        <ul style='margin-top: 0.5rem;'>
            <li>Filter by school type, management, board</li>
            <li>Compare across regions</li>
            <li>Export detailed reports</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with nav_col2:
        # Analytics link - opens in new tab
        st.markdown("""
        <a href="/Analytics?region=India" target="_blank" style="
            display: inline-block;
            width: 100%;
            padding: 1rem;
            background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
            color: white !important;
            text-align: center;
            text-decoration: none !important;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1.1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            border: 3px solid #1e88e5;
        ">
            📈 Analytics
        </a>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style='padding: 0.5rem; color: #757575; font-size: 0.9rem;'>
        Interactive analytics with geographic maps, performance metrics, and custom reports.
        <ul style='margin-top: 0.5rem;'>
            <li>Geographic heatmaps</li>
            <li>Comparative analysis</li>
            <li>Custom report builder</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.error("❌ Unable to load national statistics. Please check database connection.")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #757575; font-size: clamp(0.8rem, 2vw, 0.9rem);'>"
    "<p><strong>TutorCloud Global Dashboard</strong></p>"
    "<p>© 2026 TutorCloud. All rights reserved.</p>"
    "</div>",
    unsafe_allow_html=True
)
