"""
ui_components.py - TutorCloud Global Dashboard UI Constants
Reconstructed from Home.py v3.0 (2026-02-25)

Provides:
  - COLORS           : brand color palette dictionary
  - CHART_COLORS_GRADIENT : plotly color_continuous_scale gradient
"""

# ============================================================================
# BRAND COLOR PALETTE
# Reconstructed from hardcoded values throughout Home.py v3.0
# ============================================================================

COLORS = {
    # ── Primary brand blue (nav buttons, KPI card borders, headings)
    'primary':    '#1e88e5',

    # ── Secondary dark blue (hover states, active elements)
    'secondary':  '#1565c0',

    # ── Accent lighter blue (gradient mid-point)
    'accent':     '#42a5f5',

    # ── Medium grey (labels, description text, footer text)
    # Confirmed from Home.py lines 687 & 741 hardcoded as #757575
    'medium':     '#757575',

    # ── Dark (chart font color, body text)
    'dark':       '#212121',

    # ── Light grey for backgrounds
    'light':      '#eeeeee',

    # ── Lighter blue (dashboard-card h2 border-bottom, hr dividers)
    'lighter':    '#e3f2fd',

    # ── Lightest (chart grid lines, very subtle backgrounds)
    'lightest':   '#f5f5f5',

    # ── Page background (matches .main background-color in Home.py)
    'background': '#F5F7FA',

    # ── Semantic colors
    'info':       '#1e88e5',   # mobile nav hint bg (confirmed same as primary)
    'success':    '#43a047',   # green (used in st.success)
    'warning':    '#fb8c00',   # amber (used in st.warning)
    'error':      '#e53935',   # red   (used in st.error)

    # ── Pure white
    'white':      '#ffffff',
}


# ============================================================================
# CHART COLOR GRADIENT
# Used as color_continuous_scale in plotly bar charts (Home.py lines 539, 590)
# Blue gradient matching primary brand color #1e88e5
# ============================================================================

CHART_COLORS_GRADIENT = [
    '#e3f2fd',   # lightest blue  (lowest value)
    '#bbdefb',
    '#90caf9',
    '#64b5f6',
    '#42a5f5',
    '#2196f3',
    '#1e88e5',   # primary brand blue
    '#1976d2',
    '#1565c0',   # secondary dark blue
    '#0d47a1',   # darkest blue    (highest value)
]
