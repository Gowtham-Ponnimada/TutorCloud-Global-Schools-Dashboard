"""
UI Styles Module - Complete Professional CSS with Working Dropdown Fix
Includes: Metric cards, borders, responsive design, working JavaScript dropdown fix
"""

import streamlit as st
import streamlit.components.v1 as components

def inject_professional_css():
    """Inject complete professional CSS and working JavaScript dropdown fix"""

    # Complete CSS with all features
    st.markdown("""
    <style>
    /* ===== GLOBAL STYLES ===== */
    .main {
        background-color: #F5F7FA;
        padding: 1rem;
    }

    /* ===== HIDE STREAMLIT BRANDING ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* because those approaches break the native collapsedControl button  */
    /* Hide individual branding children */

    
    

    /* ===== RESPONSIVE SIDEBAR ===== */
    /* Mobile  (<= 768 px) — sidebar collapses, toggle accessible        */
    @media (max-width: 768px) {
        section[data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 240px !important;
            max-width: 280px !important;
        }
        section[data-testid="stSidebar"][aria-expanded="false"] {
            min-width: 0px  !important;
            width:     0px  !important;
        }
        /* Keep hamburger/toggle always tappable on mobile */
        
    }
    /* Tablet (769 – 1024 px) */
    @media (min-width: 769px) and (max-width: 1024px) {
        section[data-testid="stSidebar"] {
            min-width: 210px !important;
            max-width: 260px !important;
        }
    }
    /* Laptop / Desktop (> 1024 px) — full sidebar */
    @media (min-width: 1025px) {
        section[data-testid="stSidebar"] {
            min-width: 240px !important;
        }
    }

    /* ===== METRIC CARDS WITH BORDERS ===== */
    [data-testid="stMetric"] {
        background: white;
        padding: 1.25rem;
        border-radius: 8px;
        border: 1px solid rgba(49, 51, 63, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 1rem;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1.5rem !important;
        color: #616161;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700;
        background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: none !important;
        min-width: max-content !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 1.5rem !important;
        font-weight: 600;
    }

    /* ===== CHART CONTAINERS WITH PROPER BORDERS ===== */
    [data-testid="stPlotlyChart"] {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid rgba(49, 51, 63, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
    }

    /* ===== HEADERS ===== */
    h1, h2, h3, h4, h5, h6 {
        color: #1f1f1f;
        font-weight: 700;
        margin-bottom: 1rem;
    }

    h1 { 
        font-size: 1.5rem !important;
        border-bottom: 3px solid #1e88e5;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
    }
    
    h2 { 
        font-size: 1.5rem !important;
        color: #1565C0;
    }
    
    h3 { 
        font-size: 1.5rem !important;
        color: #1976d2;
    }

    /* ===== PARAGRAPHS & TEXT ===== */
    p, .stMarkdown {
        color: #424242;
        line-height: 1.6;
    }

    /* ===== ALERTS ===== */
    .stAlert {
        background-color: #E3F2FD;
        color: #1565C0;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid rgba(49, 51, 63, 0.2);
        margin-bottom: 1rem;
    }

    /* ===== DATA TABLES WITH BORDERS ===== */
    [data-testid="stDataFrame"] {
        background: white;
        border-radius: 8px;
        border: 1px solid rgba(49, 51, 63, 0.2);
        padding: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
    }

    /* Table styling */
    table {
        border-collapse: collapse;
        width: 100%;
        background: white;
    }

    th {
        background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
        color: white;
        padding: 0.75rem;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid #1565C0;
    }

    td {
        padding: 0.75rem;
        border-bottom: 1px solid #E0E0E0;
        color: #424242;
    }

    tr:hover {
        background-color: #F5F7FA;
    }
    
    tr:last-child td {
        border-bottom: none;
    }

    /* ===== BUTTONS ===== */
    .stButton > button {
        background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #1976d2 0%, #1565C0 100%);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
        transform: translateY(-2px);
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, #43A047 0%, #388E3C 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }

    /* ===== DIVIDERS ===== */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 2px solid #E0E0E0;
    }

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e88e5 0%, #1976d2 100%);
        color: white;
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white;
    }

    /* ===== COLUMNS & CONTAINERS ===== */
    [data-testid="column"] {
        padding: 0.5rem;
    }
    
    .stContainer {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid rgba(49, 51, 63, 0.2);
        margin-bottom: 1.5rem;
    }

    /* ===== EXPANDERS ===== */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-radius: 8px;
        padding: 1rem;
        font-weight: 600;
        color: #1565C0;
        border: 2px solid #1e88e5;
    }

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        background: white;
        border: 2px solid #1e88e5;
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: #1565C0;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e88e5 0%, #1976d2 100%);
        color: white;
    }

    /* ===== RESPONSIVE ADJUSTMENTS ===== */
    @media (max-width: 768px) {
        .main {
            padding: 0.5rem;
        }

        [data-testid="stPlotlyChart"],
        [data-testid="stDataFrame"],
        [data-testid="stMetric"] {
            padding: 1rem;
            margin-bottom: 1rem;
        }

        font-size: 1.5rem !important;
        font-size: 1.5rem !important;
        font-size: 1.5rem !important;
        
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
    }

    @media (min-width: 769px) and (max-width: 1024px) {
        .main {
            padding: 0.75rem;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
    }

    @media (min-width: 1025px) and (max-width: 1440px) {
        .main {
            padding: 1rem;
        }
    }

    @media (min-width: 1441px) {
        .main {
            padding: 1.5rem;
            max-width: 1600px;
            margin: 0 auto;
        }
    }

    /* ===== DROPDOWN VISIBILITY FIX - CSS ===== */
    
    /* Target the select container */
    div[data-baseweb="select"] {
        color: #1f1f1f !important;
        background: white !important;
    }
    
    /* Target all text inside select */
    div[data-baseweb="select"] * {
        color: #1f1f1f !important;
    }
    
    /* Target the selected value specifically */
    div[data-baseweb="select"] [class*="SingleValue"] {
        color: #1f1f1f !important;
    }
    
    /* Target the input container */
    div[data-baseweb="select"] [class*="ValueContainer"] {
        color: #1f1f1f !important;
    }
    
    /* Streamlit selectbox wrapper */
    .stSelectbox {
        color: #1f1f1f !important;
    }
    
    .stSelectbox * {
        color: #1f1f1f !important;
    }
    
    /* Force on div with role="button" inside selectbox */
    .stSelectbox div[role="button"] {
        color: #1f1f1f !important;
    }
    
    .stSelectbox div[role="button"] * {
        color: #1f1f1f !important;
    }

    /* Dropdown menu options */
    div[data-baseweb="popover"] {
        background: white !important;
    }
    
    ul[role="listbox"] li {
        color: #1f1f1f !important;
        background: white !important;
        padding: 0.5rem 1rem;
    }
    
    ul[role="listbox"] li:hover {
        background: #0068C9 !important;
        color: white !important;
    }
    
    /* Input placeholder text */
    div[data-baseweb="select"] input::placeholder {
        color: #808080 !important;
    }

    /* Radio buttons styling */
    [data-testid="stRadio"] label {
        color: #1f1f1f;
        font-weight: 500;
    }


    /* ===== MOBILE FONT OVERRIDES (≤768px) — PERF_FIX ===== */
    @media (max-width: 768px) {
        /* Metric value labels — scale down on small screens */
        [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"],
        .metric-value,
        .metric-label {
            font-size: 1.1rem !important;
        }
        /* Section / page headers */
        .main-header {
            font-size: 1.3rem !important;
        }
        .sub-header {
            font-size: 0.9rem !important;
        }
        /* KPI card values */
        .card-value {
            font-size: 1.2rem !important;
        }
        /* Prevent horizontal scroll on mobile */
        .main .block-container {
            padding-left:  0.75rem !important;
            padding-right: 0.75rem !important;
            overflow-x:    hidden !important;
        }
    }
    /* ===== END MOBILE FONT OVERRIDES ===== */
        /* KPI-LABEL-FIX — allow metric labels to wrap on long text (e.g. State Dashboard) */
    [data-testid="stMetricLabel"] p,
    [data-testid="stMetricLabel"] label {
        white-space: normal   !important;
        overflow:    visible  !important;
        text-overflow: clip   !important;
        font-size:  0.70rem   !important;
        line-height: 1.25     !important;
        max-height:  2.6em    !important;   /* max 2 lines */
    }
    /* END KPI-LABEL-FIX */
    </style>
    """, unsafe_allow_html=True)

    # Working JavaScript fix using components.html
    components.html("""
    <script>
    (function() {
        // Function to apply fix to all dropdowns
        function fixDropdownText() {
            const selectors = [
                'div[data-baseweb="select"]',
                '.stSelectbox',
                'div[data-testid*="stSelectbox"]'
            ];

            selectors.forEach(selector => {
                const elements = parent.document.querySelectorAll(selector);
                elements.forEach(el => {
                    // Apply inline styles (highest specificity)
                    el.style.setProperty('color', '#1f1f1f', 'important');
                    
                    // Apply to all children
                    const children = el.querySelectorAll('*');
                    children.forEach(child => {
                        child.style.setProperty('color', '#1f1f1f', 'important');
                    });
                });
            });
        }

        // Run fix multiple times to catch async content
        setTimeout(fixDropdownText, 100);
        setTimeout(fixDropdownText, 500);
        setTimeout(fixDropdownText, 1000);
        setTimeout(fixDropdownText, 2000);

        // Watch for DOM changes
        const observer = new MutationObserver(fixDropdownText);
        observer.observe(parent.document.body, {
            childList: true,
            subtree: true
        });

        console.log('✅ Complete dropdown fix applied');
    })();
    </script>
    """, height=0)








# -- Region selector (v4d - sidebar + HTML display badge) -------------------
# render_region_badge v4d -- sidebar selector, try/except dedup
#
# Why sidebar?
#   CSS `position: fixed` on Streamlit WIDGET containers is broken by
#   Streamlit's own `transform: translateY()` wrappers.
#   st.sidebar widgets live in a SEPARATE DOM tree -- no transform
#   ancestors -> always visible, works in every Streamlit version.
#
# Dedup strategy (v4d):
#   render_region_badge() may be called 3x per page from legacy code.
#   Using threading.current_thread().ident (v4c) FAILS because Streamlit's
#   thread pool reuses threads across script runs: thread ID added on run 1
#   is still present on run 2, causing the selectbox to be skipped every
#   run after the first (dropdown appears then immediately disappears).
#
#   FIX: try/except StreamlitAPIException.
#   DuplicateWidgetID only fires on the 2ND+ call within ONE script run.
#   First call: widget renders normally -> selectbox visible every run.
#   2nd+ call: exception caught silently -> no crash, no duplicate.
#
# Streamlit version compatibility:
#   >= 1.27 : st.query_params (dict-like, read/write)
#   <  1.27 : st.experimental_get_query_params() / set_query_params()

REGION_OPTIONS = [
    ("India",         "\U0001f1ee\U0001f1f3"),   # flag
    ("UAE",           "\U0001f1e6\U0001f1ea"),   # flag
    ("Australia",     "\U0001f1e6\U0001f1fa"),   # flag
    ("New Zealand",   "\U0001f1f3\U0001f1ff"),   # flag
    ("United States", "\U0001f1fa\U0001f1f8"),   # flag
]
_VALID_REGIONS = [r[0] for r in REGION_OPTIONS]


def _qp_get(key, default='India'):
    """Read a query param; compatible with Streamlit >= 1.27 and < 1.27."""
    import streamlit as st
    try:
        return st.query_params.get(key, default)
    except AttributeError:
        v = st.experimental_get_query_params().get(key, [default])
        return v[0] if v else default


def _qp_set(**kwargs):
    """Write query params; compatible with Streamlit >= 1.27 and < 1.27."""
    import streamlit as st
    try:
        for k, v in kwargs.items():
            st.query_params[k] = v
    except AttributeError:
        st.experimental_set_query_params(**kwargs)


def render_region_badge():
    import streamlit as st

    # -- 1. Sync session_state — session_state takes priority over query_params.
    #    WHY: In Streamlit 1.54 + st.navigation(), clicking between pages in the
    #    sidebar clears URL query params (?region=UAE disappears). session_state
    #    IS preserved across st.navigation() page changes. So we read session_state
    #    first (user's last explicit choice), fall back to query_params (bookmarked
    #    URL), then default to 'India'.
    _qp_region = _qp_get('region', None)
    _ss_region = st.session_state.get('selected_region', None)

    if _ss_region and _ss_region in _VALID_REGIONS:
        _cur = _ss_region                      # ← session_state wins (persists across nav)
    elif _qp_region and _qp_region in _VALID_REGIONS:
        _cur = _qp_region                      # ← URL bookmark fallback
        st.session_state['selected_region'] = _cur
    else:
        _cur = 'India'                         # ← hard default
        st.session_state['selected_region'] = _cur

    # -- 2. HTML display badge (top-right, fixed, read-only) -------------
    #   Pure HTML div via st.markdown -- no React transform ancestors
    #   -> position:fixed works (proven in v1-v3 badge).
    st.markdown(
        '<div style="'
        'position:fixed;top:0.38rem;right:4.8rem;z-index:1000001;'
        'background:linear-gradient(135deg,#FF9933 0%,#f5f5f5 50%,#138808 100%);'
        'padding:5px 16px;border-radius:20px;'
        'font-size:0.75rem;font-weight:700;color:#1a1a1a;'
        'border:1px solid rgba(0,0,0,.12);'
        'display:flex;align-items:center;gap:6px;'
        'box-shadow:0 2px 10px rgba(0,0,0,.20);'
        'pointer-events:none;user-select:none;white-space:nowrap;'
        f'">&#127757;&nbsp;Region:&nbsp;<strong>{_cur}</strong></div>',
        unsafe_allow_html=True,
    )

    # -- 3. Sidebar region selector (interactive, try/except dedup) ------
    #   try/except correctly handles 2nd+ calls per run without hiding
    #   the widget on subsequent reruns (thread-ID approach was broken).
    try:
        with st.sidebar:
            st.markdown(
                '<style>'
                'div[data-testid="stSidebar"] .tc-region-block {'
                '    padding: 6px 0 8px 0;'
                '    border-top: 1px solid rgba(250,250,250,0.15);'
                '    margin-top: 6px;'
                '}'
                'div[data-testid="stSidebar"] .tc-region-title {'
                '    font-size: 0.78rem; font-weight: 700;'
                '    color: rgba(250,250,250,0.85);'
                '    margin-bottom: 4px; letter-spacing: 0.03rem;'
                '}'
                '</style>'
                '<div class="tc-region-block">'
                '<div class="tc-region-title">&#127757;&nbsp; Select Region</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            _chosen = st.selectbox(
                label='Region',
                options=_VALID_REGIONS,
                index=_VALID_REGIONS.index(_cur),
                key='tc_region_selector',
                label_visibility='collapsed',
            )
    except Exception:
        # DuplicateWidgetID: selectbox already registered this run.
        # Read current value from session_state (set by first call).
        _chosen = st.session_state.get('tc_region_selector', _cur)

    # -- 4. On change: Python-side query_params write + forced rerun -----
    if _chosen != _cur:
        _qp_set(region=_chosen)
        st.session_state['selected_region'] = _chosen
        st.rerun()


