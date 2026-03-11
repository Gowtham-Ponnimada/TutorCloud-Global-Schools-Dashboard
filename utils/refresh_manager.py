"""
Refresh Manager for TutorCloud Global Dashboard

Handles manual and automatic data refresh functionality.
Integrates with CacheManager for cache invalidation.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Callable
import time

from utils.cache_manager import cache_manager


class RefreshManager:
    """
    Manages data refresh operations
    
    Features:
    - Manual refresh with cache invalidation
    - Auto-refresh with configurable intervals
    - Last updated timestamp tracking
    - Refresh callbacks for page-specific logic
    """
    
    def __init__(self):
        """Initialize refresh state in Streamlit session"""
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = {}
        if 'auto_refresh_enabled' not in st.session_state:
            st.session_state.auto_refresh_enabled = False
        if 'auto_refresh_interval' not in st.session_state:
            st.session_state.auto_refresh_interval = 60  # Default 60 seconds
    
    def manual_refresh(self, page_name: str, invalidate_pattern: Optional[str] = None) -> None:
        """
        Perform manual refresh
        
        Args:
            page_name: Name of the page being refreshed
            invalidate_pattern: Pattern to match for cache invalidation (None = clear all)
        """
        # Invalidate cache
        if invalidate_pattern:
            count = cache_manager.invalidate(invalidate_pattern)
            st.toast(f"🔄 Refreshed! Cleared {count} cached queries.", icon="✅")
        else:
            cache_manager.clear_all()
            st.toast("🔄 Complete refresh! All cache cleared.", icon="✅")
        
        # Update last refresh timestamp
        st.session_state.last_refresh[page_name] = datetime.now()
        
        # Force Streamlit rerun
        st.rerun()
    
    def get_last_refresh(self, page_name: str) -> Optional[datetime]:
        """
        Get last refresh timestamp for a page
        
        Args:
            page_name: Name of the page
            
        Returns:
            Datetime of last refresh or None
        """
        return st.session_state.last_refresh.get(page_name)
    
    def get_last_refresh_text(self, page_name: str) -> str:
        """
        Get human-readable last refresh text
        
        Args:
            page_name: Name of the page
            
        Returns:
            Text like "Last updated: 2 minutes ago"
        """
        last_refresh = self.get_last_refresh(page_name)
        
        if last_refresh is None:
            return "Last updated: Just now"
        
        time_diff = datetime.now() - last_refresh
        
        if time_diff < timedelta(minutes=1):
            return "Last updated: Just now"
        elif time_diff < timedelta(hours=1):
            minutes = int(time_diff.total_seconds() / 60)
            return f"Last updated: {minutes} minute{'s' if minutes != 1 else ''} ago"
        elif time_diff < timedelta(days=1):
            hours = int(time_diff.total_seconds() / 3600)
            return f"Last updated: {hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = time_diff.days
            return f"Last updated: {days} day{'s' if days != 1 else ''} ago"
    
    def enable_auto_refresh(self, interval: int = 60) -> None:
        """
        Enable auto-refresh
        
        Args:
            interval: Refresh interval in seconds
        """
        st.session_state.auto_refresh_enabled = True
        st.session_state.auto_refresh_interval = interval
    
    def disable_auto_refresh(self) -> None:
        """Disable auto-refresh"""
        st.session_state.auto_refresh_enabled = False
    
    def is_auto_refresh_enabled(self) -> bool:
        """Check if auto-refresh is enabled"""
        return st.session_state.auto_refresh_enabled
    
    def get_auto_refresh_interval(self) -> int:
        """Get current auto-refresh interval in seconds"""
        return st.session_state.auto_refresh_interval
    
    def render_refresh_controls(self, page_name: str, invalidate_pattern: Optional[str] = None) -> None:
        """
        Render refresh controls in the UI
        
        Args:
            page_name: Name of the current page
            invalidate_pattern: Pattern for cache invalidation
        """
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.caption(self.get_last_refresh_text(page_name))
        
        with col2:
            # Auto-refresh toggle
            auto_refresh = st.checkbox(
                "Auto-refresh",
                value=self.is_auto_refresh_enabled(),
                key=f"auto_refresh_{page_name}"
            )
            
            if auto_refresh != self.is_auto_refresh_enabled():
                if auto_refresh:
                    self.enable_auto_refresh()
                else:
                    self.disable_auto_refresh()
        
        with col3:
            # Manual refresh button
            if st.button("🔄 Refresh", key=f"refresh_btn_{page_name}"):
                self.manual_refresh(page_name, invalidate_pattern)
        
        # Auto-refresh interval selector (if enabled)
        if self.is_auto_refresh_enabled():
            interval = st.selectbox(
                "Refresh every:",
                options=[30, 60, 300, 600],
                format_func=lambda x: f"{x//60} minute{'s' if x//60 != 1 else ''}" if x >= 60 else f"{x} seconds",
                index=1,  # Default to 60 seconds
                key=f"refresh_interval_{page_name}"
            )
            
            if interval != self.get_auto_refresh_interval():
                st.session_state.auto_refresh_interval = interval
    
    def auto_refresh_if_enabled(self, page_name: str) -> None:
        """
        Check if auto-refresh should trigger and execute
        
        Args:
            page_name: Name of the current page
        """
        if not self.is_auto_refresh_enabled():
            return
        
        last_refresh = self.get_last_refresh(page_name)
        interval = self.get_auto_refresh_interval()
        
        if last_refresh is None:
            # First load, set timestamp
            st.session_state.last_refresh[page_name] = datetime.now()
            return
        
        time_since_refresh = (datetime.now() - last_refresh).total_seconds()
        
        if time_since_refresh >= interval:
            # Time to refresh
            cache_manager.clear_all()
            st.session_state.last_refresh[page_name] = datetime.now()
            st.rerun()
    
    def render_compact_controls(self, page_name: str, invalidate_pattern: Optional[str] = None) -> None:
        """
        Render compact refresh controls (for sidebar or tight spaces)
        
        Args:
            page_name: Name of the current page
            invalidate_pattern: Pattern for cache invalidation
        """
        st.caption(self.get_last_refresh_text(page_name))
        
        if st.button("🔄 Refresh Data", key=f"compact_refresh_{page_name}", use_container_width=True):
            self.manual_refresh(page_name, invalidate_pattern)


# Global refresh manager instance
refresh_manager = RefreshManager()
