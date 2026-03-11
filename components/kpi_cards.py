"""
KPI Cards Component for TutorCloud Global Dashboard

Reusable metric display cards with icons, colors, and trend indicators.
"""

import streamlit as st
from typing import Optional
from utils.grade_helpers import format_large_number, format_percentage


def render_kpi_card(
    title: str,
    value: any,
    icon: str = "📊",
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None,
    format_type: str = "number"
) -> None:
    """
    Render a single KPI card
    
    Args:
        title: Card title
        value: Main value to display
        icon: Emoji icon
        delta: Optional change/trend text
        delta_color: "normal", "inverse", or "off"
        help_text: Optional help text on hover
        format_type: "number", "percentage", "decimal"
    """
    # Format value based on type
    if format_type == "number":
        display_value = format_large_number(value, short=True)
    elif format_type == "percentage":
        display_value = format_percentage(value)
    elif format_type == "decimal":
        try:
            display_value = f"{float(value):.1f}"
        except:
            display_value = str(value)
    elif format_type == "text":
        display_value = str(value)
    else:
        display_value = str(value)
    
    # Render metric
    st.metric(
        label=f"{icon} {title}",
        value=display_value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def render_kpi_row(kpis: list) -> None:
    """
    Render a row of KPI cards
    
    Args:
        kpis: List of dicts with KPI parameters
              Example: [
                  {'title': 'Schools', 'value': 1471473, 'icon': '🏫'},
                  {'title': 'Students', 'value': 246932680, 'icon': '👨‍🎓'}
              ]
    """
    num_kpis = len(kpis)
    cols = st.columns(num_kpis)
    
    for idx, kpi in enumerate(kpis):
        with cols[idx]:
            render_kpi_card(**kpi)


def render_grade_level_card(
    level_name: str,
    total: int,
    boys: int,
    girls: int,
    ptr: Optional[float] = None,
    compact: bool = False
) -> None:
    """
    Render enrollment card for a grade level
    
    Args:
        level_name: Grade level name (e.g., "Primary (Class 1-5)")
        total: Total enrollment
        boys: Boys enrollment
        girls: Girls enrollment
        ptr: Pupil-Teacher Ratio (optional)
        compact: If True, use compact layout
    """
    if compact:
        # Compact version for state comparison
        st.markdown(f"**{level_name}**")
        st.caption(f"Total: {format_large_number(total, short=True)}")
        st.caption(f"Boys: {format_large_number(boys, short=True)} | Girls: {format_large_number(girls, short=True)}")
        if ptr:
            st.caption(f"PTR: {round(ptr)}:1")
    else:
        # Full version with container
        with st.container():
            st.markdown(f"### {level_name}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total",
                    format_large_number(total, short=True),
                    help=f"Total enrollment: {total:,}"
                )
            
            with col2:
                st.metric(
                    "👦 Boys",
                    format_large_number(boys, short=True),
                    help=f"Boys: {boys:,}"
                )
            
            with col3:
                st.metric(
                    "👧 Girls",
                    format_large_number(girls, short=True),
                    help=f"Girls: {girls:,}"
                )
            
            with col4:
                if ptr:
                    st.metric(
                        "PTR",
                        f"{round(ptr)}:1",
                        help="Pupil-Teacher Ratio"
                    )
                else:
                    st.metric("PTR", "N/A")


def render_state_comparison_column(
    state_name: str,
    data: dict,
    show_districts: bool = True
) -> None:
    """
    Render a single column in state comparison
    
    Args:
        state_name: Name of the state
        data: Dict with state data structure:
            {
                'overview': {'schools': X, 'students': Y, 'ptr': Z},
                'pre_primary': {'total': X, 'boys': Y, 'girls': Z, 'ptr': P},
                'primary': {...},
                'middle': {...},
                'high': {...},
                'top_districts': [('District1', students), ...]
            }
        show_districts: Whether to show top districts
    """
    st.markdown(f"### {state_name}")
    st.divider()
    
    # Overview
    st.markdown("**📊 OVERVIEW**")
    overview = data.get('overview', {})
    st.metric("Schools", format_large_number(overview.get('schools', 0), short=True))
    st.metric("Students", format_large_number(overview.get('students', 0), short=True))
    st.metric("PTR", f"{overview.get('ptr', 0):.1f}" if overview.get('ptr') else "N/A")
    
    st.divider()
    
    # Grade levels
    for level_key, level_label in [
        ('pre_primary', '📈 PRE-PRIMARY'),
        ('primary', '📚 PRIMARY'),
        ('middle', '🎓 MIDDLE SCHOOL'),
        ('high', '🏫 HIGH SCHOOL')
    ]:
        if level_key in data:
            st.markdown(f"**{level_label}**")
            level_data = data[level_key]
            
            st.caption(f"Total: {format_large_number(level_data.get('total', 0), short=True)}")
            st.caption(f"Boys: {format_large_number(level_data.get('boys', 0), short=True)}")
            st.caption(f"Girls: {format_large_number(level_data.get('girls', 0), short=True)}")
            
            if level_data.get('ptr'):
                st.caption(f"PTR: {level_data['ptr']:.1f}")
            
            st.divider()
    
    # Top districts
    if show_districts and 'top_districts' in data:
        st.markdown("**🏆 TOP 5 DISTRICTS**")
        for idx, (district, students) in enumerate(data['top_districts'][:5], 1):
            st.caption(f"{idx}. {district}: {format_large_number(students, short=True)}")


def render_summary_stats_row(stats: dict) -> None:
    """
    Render a row of summary statistics (for School Explorer, etc.)
    
    Args:
        stats: Dict with stats
            Example: {
                'schools_found': 12458,
                'total_students': 1820000,
                'avg_ptr': 23.5,
                'rural_pct': 78.2
            }
    """
    st.markdown("### 📊 Summary Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Schools Found",
            format_large_number(stats.get('schools_found', 0)),
            help="Number of schools matching filters"
        )
    
    with col2:
        st.metric(
            "Total Students",
            format_large_number(stats.get('total_students', 0), short=True),
            help="Total student enrollment"
        )
    
    with col3:
        st.metric(
            "Avg PTR",
            f"{stats.get('avg_ptr', 0):.1f}" if stats.get('avg_ptr') else "N/A",
            help="Average Pupil-Teacher Ratio"
        )
    
    with col4:
        rural_pct = stats.get('rural_pct', 0)
        st.metric(
            "Rural Schools",
            f"{rural_pct:.1f}%" if rural_pct else "N/A",
            help="Percentage of rural schools"
        )


def render_info_card(title: str, content: str, icon: str = "ℹ️", type: str = "info") -> None:
    """
    Render an info/warning/success card
    
    Args:
        title: Card title
        content: Card content (markdown supported)
        icon: Emoji icon
        type: "info", "warning", "success", "error"
    """
    if type == "info":
        st.info(f"{icon} **{title}**\n\n{content}")
    elif type == "warning":
        st.warning(f"{icon} **{title}**\n\n{content}")
    elif type == "success":
        st.success(f"{icon} **{title}**\n\n{content}")
    elif type == "error":
        st.error(f"{icon} **{title}**\n\n{content}")
