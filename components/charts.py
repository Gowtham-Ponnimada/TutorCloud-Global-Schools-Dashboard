"""
Chart Components for TutorCloud Global Dashboard

Standardized Plotly charts with consistent styling.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List
import streamlit as st


# Color schemes
COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'danger': '#d62728',
    'warning': '#ff9896',
    'info': '#17becf',
    'boys': '#4287f5',
    'girls': '#f542cb',
    'government': '#2ca02c',
    'private': '#ff7f0e',
    'aided': '#9467bd'
}

# Chart template
CHART_TEMPLATE = 'plotly_white'


def render_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    color: Optional[str] = None,
    orientation: str = 'v',
    show_values: bool = True
) -> None:
    """
    Render a bar chart
    
    Args:
        df: DataFrame with data
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        title: Chart title
        x_label: X-axis label (optional)
        y_label: Y-axis label (optional)
        color: Color (hex or color name)
        orientation: 'v' for vertical, 'h' for horizontal
        show_values: Show values on bars
    """
    fig = px.bar(
        df,
        x=x_col if orientation == 'v' else y_col,
        y=y_col if orientation == 'v' else x_col,
        title=title,
        orientation=orientation,
        color_discrete_sequence=[color or COLORS['primary']],
        template=CHART_TEMPLATE
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or y_col,
        showlegend=False,
        height=500
    )
    
    # Show values on bars
    if show_values:
        fig.update_traces(texttemplate='%{y}', textposition='auto')
    
    st.plotly_chart(fig, use_container_width=True)


def render_grouped_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    colors: Optional[List[str]] = None
) -> None:
    """
    Render a grouped bar chart
    
    Args:
        df: DataFrame with data
        x_col: Column name for x-axis (categories)
        y_cols: List of column names for bars
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        colors: List of colors for each bar group
    """
    fig = go.Figure()
    
    if not colors:
        colors = [COLORS['primary'], COLORS['secondary'], COLORS['success'], COLORS['danger']]
    
    for idx, col in enumerate(y_cols):
        fig.add_trace(go.Bar(
            name=col,
            x=df[x_col],
            y=df[col],
            marker_color=colors[idx % len(colors)]
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or "Value",
        barmode='group',
        template=CHART_TEMPLATE,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_stacked_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    colors: Optional[List[str]] = None
) -> None:
    """
    Render a stacked bar chart
    
    Args:
        df: DataFrame with data
        x_col: Column name for x-axis (categories)
        y_cols: List of column names to stack
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        colors: List of colors
    """
    fig = go.Figure()
    
    if not colors:
        colors = [COLORS['boys'], COLORS['girls']]
    
    for idx, col in enumerate(y_cols):
        fig.add_trace(go.Bar(
            name=col,
            x=df[x_col],
            y=df[col],
            marker_color=colors[idx % len(colors)]
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or "Value",
        barmode='stack',
        template=CHART_TEMPLATE,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_pie_chart(
    df: pd.DataFrame,
    values_col: str,
    names_col: str,
    title: str,
    colors: Optional[List[str]] = None,
    show_legend: bool = True
) -> None:
    """
    Render a pie chart
    
    Args:
        df: DataFrame with data
        values_col: Column name for values
        names_col: Column name for labels
        title: Chart title
        colors: List of colors
        show_legend: Show legend
    """
    fig = px.pie(
        df,
        values=values_col,
        names=names_col,
        title=title,
        color_discrete_sequence=colors,
        template=CHART_TEMPLATE
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        showlegend=show_legend,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_donut_chart(
    df: pd.DataFrame,
    values_col: str,
    names_col: str,
    title: str,
    colors: Optional[List[str]] = None
) -> None:
    """
    Render a donut chart
    
    Args:
        df: DataFrame with data
        values_col: Column name for values
        names_col: Column name for labels
        title: Chart title
        colors: List of colors
    """
    fig = px.pie(
        df,
        values=values_col,
        names=names_col,
        title=title,
        color_discrete_sequence=colors,
        template=CHART_TEMPLATE,
        hole=0.4  # Makes it a donut
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=500)
    
    st.plotly_chart(fig, use_container_width=True)


def render_line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    colors: Optional[List[str]] = None
) -> None:
    """
    Render a line chart
    
    Args:
        df: DataFrame with data
        x_col: Column name for x-axis
        y_cols: List of column names for lines
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        colors: List of colors for lines
    """
    fig = go.Figure()
    
    if not colors:
        colors = [COLORS['primary'], COLORS['secondary'], COLORS['success']]
    
    for idx, col in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[col],
            mode='lines+markers',
            name=col,
            line=dict(color=colors[idx % len(colors)], width=2),
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or "Value",
        template=CHART_TEMPLATE,
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_heatmap(
    df: pd.DataFrame,
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    colorscale: str = 'Blues'
) -> None:
    """
    Render a heatmap
    
    Args:
        df: DataFrame with data (index as y, columns as x)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        colorscale: Plotly colorscale name
    """
    fig = go.Figure(data=go.Heatmap(
        z=df.values,
        x=df.columns,
        y=df.index,
        colorscale=colorscale,
        hovertemplate='%{x}<br>%{y}<br>Value: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label or "",
        yaxis_title=y_label or "",
        template=CHART_TEMPLATE,
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_horizontal_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    color: Optional[str] = None,
    top_n: Optional[int] = None
) -> None:
    """
    Render a horizontal bar chart (useful for rankings)
    
    Args:
        df: DataFrame with data
        x_col: Column name for values (horizontal axis)
        y_col: Column name for categories (vertical axis)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        color: Bar color
        top_n: Show only top N items
    """
    # Sort and limit if requested
    plot_df = df.copy()
    if top_n:
        plot_df = plot_df.nlargest(top_n, x_col)
    
    plot_df = plot_df.sort_values(x_col)
    
    fig = go.Figure(go.Bar(
        x=plot_df[x_col],
        y=plot_df[y_col],
        orientation='h',
        marker_color=color or COLORS['primary'],
        text=plot_df[x_col],
        textposition='outside'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label or x_col,
        yaxis_title=y_label or y_col,
        template=CHART_TEMPLATE,
        height=500 + (top_n * 20 if top_n else 0),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
