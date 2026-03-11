"""
Filter Panel Component for TutorCloud Global Dashboard

Provides 16 database-driven filters with cascading dropdowns.
All filter options are fetched from the database dynamically.
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.utils.database import DatabaseManager
from src.config.settings import settings
from utils.filter_labels import (
    label_mapper,
    MANAGEMENT_LABELS,
    BOARD_SEC_LABELS,
    BOARD_HSEC_LABELS,
    MEDIUM_INSTR_LABELS,
    SCHOOL_CATEGORY_LABELS,
    SCHOOL_TYPE_LABELS,
    RURAL_URBAN_LABELS
)


class FilterPanel:
    """
    16-filter panel with DB-driven options and cascading behavior
    
    Filters:
    1. State (multiselect)
    2. District (cascading, depends on state)
    3. Block/Taluk (cascading, depends on district)
    4. Management Type (multiselect)
    5. School Category (multiselect)
    6. School Type (multiselect)
    7. Rural/Urban (checkbox)
    8. Secondary Board (multiselect)
    9. Higher Secondary Board (multiselect)
    10. Medium of Instruction (multiselect)
    11. Shift School (checkbox)
    12. Minority School (checkbox)
    13. Residential School (checkbox)
    14. CWSN (checkbox)
    15. School ID (text)
    16. Pincode (text)
    """
    
    def __init__(self, db: DatabaseManager, page_key: str):
        """
        Initialize filter panel
        
        Args:
            db: DatabaseManager instance
            page_key: Unique key for this page (to avoid widget key conflicts)
        """
        self.db = db
        self.page_key = page_key
        
        # Initialize session state for filters
        if f'filters_{page_key}' not in st.session_state:
            st.session_state[f'filters_{page_key}'] = {}
    
    def _get_states(self) -> List[str]:
        """Fetch all states from database"""
        query = """
            SELECT DISTINCT state 
            FROM india_2024_25.school_profile_1 
            WHERE state IS NOT NULL 
            ORDER BY state
        """
        result = self.db.execute_query(query)
        return [row[0] for row in result] if result else []
    
    def _get_districts(self, states: Optional[List[str]] = None) -> List[str]:
        """
        Fetch districts (optionally filtered by states)
        
        Args:
            states: List of states to filter by
        """
        query = """
            SELECT DISTINCT district 
            FROM india_2024_25.school_profile_1 
            WHERE district IS NOT NULL
        """
        params = []
        
        if states and len(states) > 0:
            placeholders = ','.join(['%s'] * len(states))
            query += f" AND state IN ({placeholders})"
            params = states
        
        query += " ORDER BY district"
        
        result = self.db.execute_query(query, tuple(params) if params else None)
        return [row[0] for row in result] if result else []
    
    def _get_blocks(self, districts: Optional[List[str]] = None) -> List[str]:
        """
        Fetch blocks (optionally filtered by districts)
        
        Args:
            districts: List of districts to filter by
        """
        query = """
            SELECT DISTINCT block 
            FROM india_2024_25.school_profile_1 
            WHERE block IS NOT NULL AND block != ''
        """
        params = []
        
        if districts and len(districts) > 0:
            placeholders = ','.join(['%s'] * len(districts))
            query += f" AND district IN ({placeholders})"
            params = districts
        
        query += " ORDER BY block"
        
        result = self.db.execute_query(query, tuple(params) if params else None)
        return [row[0] for row in result] if result else []
    
    def render(self, collapsible: bool = True) -> Dict:
        """
        Render the filter panel
        
        Args:
            collapsible: If True, render in collapsible expanders
        
        Returns:
            Dictionary with selected filter values
        """
        filters = {}
        
        if collapsible:
            # Geographic Filters
            with st.expander("🌍 Geographic Filters", expanded=True):
                filters.update(self._render_geographic_filters())
            
            # School Type Filters
            with st.expander("🏫 School Type Filters", expanded=False):
                filters.update(self._render_school_type_filters())
            
            # Board/Academic Filters
            with st.expander("📚 Board & Academic Filters", expanded=False):
                filters.update(self._render_board_filters())
            
            # Special Features
            with st.expander("⭐ Special Features", expanded=False):
                filters.update(self._render_special_filters())
            
            # Search by ID
            with st.expander("🔍 Search by Identifier", expanded=False):
                filters.update(self._render_search_filters())
        else:
            # Render all filters without expanders
            st.subheader("🎛️ Filters")
            filters.update(self._render_geographic_filters())
            st.divider()
            filters.update(self._render_school_type_filters())
            st.divider()
            filters.update(self._render_board_filters())
            st.divider()
            filters.update(self._render_special_filters())
            st.divider()
            filters.update(self._render_search_filters())
        
        # Filter action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Apply Filters", key=f"apply_{self.page_key}", use_container_width=True):
                st.session_state[f'filters_{self.page_key}'] = filters
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear All", key=f"clear_{self.page_key}", use_container_width=True):
                st.session_state[f'filters_{self.page_key}'] = {}
                st.rerun()
        
        return filters
    
    def _render_geographic_filters(self) -> Dict:
        """Render geographic filters with cascading"""
        filters = {}
        
        # State filter
        states = self._get_states()
        selected_states = st.multiselect(
            "State",
            options=states,
            key=f"state_{self.page_key}",
            help="Select one or more states"
        )
        if selected_states:
            filters['state'] = selected_states
        
        # District filter (cascading)
        districts = self._get_districts(selected_states if selected_states else None)
        selected_districts = st.multiselect(
            "District",
            options=districts,
            key=f"district_{self.page_key}",
            help="Select one or more districts" + (" (filtered by selected states)" if selected_states else "")
        )
        if selected_districts:
            filters['district'] = selected_districts
        
        # Block filter (cascading)
        blocks = self._get_blocks(selected_districts if selected_districts else None)
        selected_blocks = st.multiselect(
            "Block/Taluk",
            options=blocks,
            key=f"block_{self.page_key}",
            help="Select one or more blocks/taluks" + (" (filtered by selected districts)" if selected_districts else "")
        )
        if selected_blocks:
            filters['block'] = selected_blocks
        
        return filters
    
    def _render_school_type_filters(self) -> Dict:
        """Render school type filters"""
        filters = {}
        
        # Management Type
        mgmt_options = [(code, label) for code, label in MANAGEMENT_LABELS.items()]
        selected_mgmt = st.multiselect(
            "Management Type",
            options=[code for code, _ in mgmt_options],
            format_func=lambda x: dict(mgmt_options)[x],
            key=f"management_{self.page_key}",
            help="Government, Private, Aided, etc."
        )
        if selected_mgmt:
            filters['managment'] = selected_mgmt  # Note: typo in DB column name
        
        # School Category
        cat_options = [(code, label) for code, label in SCHOOL_CATEGORY_LABELS.items()]
        selected_cat = st.multiselect(
            "School Category",
            options=[code for code, _ in cat_options],
            format_func=lambda x: dict(cat_options)[x],
            key=f"category_{self.page_key}",
            help="Primary, Secondary, Higher Secondary, etc."
        )
        if selected_cat:
            filters['school_category'] = selected_cat
        
        # School Type (Boys/Girls/Co-ed)
        type_options = [(code, label) for code, label in SCHOOL_TYPE_LABELS.items()]
        selected_type = st.multiselect(
            "School Type",
            options=[code for code, _ in type_options],
            format_func=lambda x: dict(type_options)[x],
            key=f"school_type_{self.page_key}",
            help="Boys Only, Girls Only, Co-educational"
        )
        if selected_type:
            filters['school_type'] = selected_type
        
        # Rural/Urban
        rural_urban_options = [(code, label) for code, label in RURAL_URBAN_LABELS.items()]
        selected_rural_urban = st.multiselect(
            "Location Type",
            options=[code for code, _ in rural_urban_options],
            format_func=lambda x: dict(rural_urban_options)[x],
            key=f"rural_urban_{self.page_key}",
            help="Rural or Urban"
        )
        if selected_rural_urban:
            filters['rural_urban'] = selected_rural_urban
        
        return filters
    
    def _render_board_filters(self) -> Dict:
        """Render board and academic filters"""
        filters = {}
        
        # Secondary Board
        board_sec_options = label_mapper.get_board_sec_options()
        selected_board_sec = st.multiselect(
            "Secondary Board (Class 9-10)",
            options=[code for code, _ in board_sec_options],
            format_func=lambda x: dict(board_sec_options)[x],
            key=f"board_sec_{self.page_key}",
            help="CBSE, State Board, ICSE, etc."
        )
        if selected_board_sec:
            filters['aff_board_sec'] = selected_board_sec
        
        # Higher Secondary Board
        board_hsec_options = label_mapper.get_board_hsec_options()
        selected_board_hsec = st.multiselect(
            "Higher Secondary Board (Class 11-12)",
            options=[code for code, _ in board_hsec_options],
            format_func=lambda x: dict(board_hsec_options)[x],
            key=f"board_hsec_{self.page_key}",
            help="CBSE, State Board, ISC, etc."
        )
        if selected_board_hsec:
            filters['aff_board_hsec'] = selected_board_hsec
        
        # Medium of Instruction
        medium_options = label_mapper.get_medium_options()
        selected_medium = st.multiselect(
            "Medium of Instruction",
            options=[code for code, _ in medium_options],
            format_func=lambda x: dict(medium_options)[x],
            key=f"medium_{self.page_key}",
            help="Hindi, English, Regional languages, etc."
        )
        if selected_medium:
            filters['medium_instr1'] = selected_medium
        
        return filters
    
    def _render_special_filters(self) -> Dict:
        """Render special feature filters"""
        filters = {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.checkbox("Shift School", key=f"shift_{self.page_key}"):
                filters['shift_school'] = 1
            
            if st.checkbox("Minority School", key=f"minority_{self.page_key}"):
                filters['minority_school'] = 1
        
        with col2:
            if st.checkbox("Residential School", key=f"resi_{self.page_key}"):
                filters['resi_school'] = 1
            
            if st.checkbox("CWSN (Special Needs)", key=f"cwsn_{self.page_key}"):
                filters['special_school_for_cwsn'] = 1
        
        return filters
    
    def _render_search_filters(self) -> Dict:
        """Render search by ID filters"""
        filters = {}
        
        # School ID
        school_id = st.text_input(
            "School ID",
            key=f"school_id_{self.page_key}",
            help="Enter school pseudocode",
            placeholder="e.g., 9462665"
        )
        if school_id:
            filters['pseudocode'] = school_id
        
        # Pincode
        pincode = st.text_input(
            "Pincode",
            key=f"pincode_{self.page_key}",
            help="Enter 6-digit pincode",
            placeholder="e.g., 560001",
            max_chars=10
        )
        if pincode:
            filters['pincode'] = pincode
        
        return filters
    
    def get_applied_filters(self) -> Dict:
        """Get currently applied filters"""
        return st.session_state.get(f'filters_{self.page_key}', {})
    
    def render_filter_summary(self) -> None:
        """Render a summary of applied filters"""
        filters = self.get_applied_filters()
        
        if not filters:
            st.info("ℹ️ No filters applied. Showing all data.")
            return
        
        st.caption("**Active Filters:**")
        
        filter_tags = []
        for key, value in filters.items():
            if isinstance(value, list):
                filter_tags.append(f"{key}: {', '.join(map(str, value))}")
            else:
                filter_tags.append(f"{key}: {value}")
        
        st.caption(" | ".join(filter_tags))
