"""
=============================================================================
FILTER MANAGER - TUTORCLOUD GLOBAL DASHBOARD
=============================================================================
Handles all filtering logic for queries
Based on ACTUAL schema discovery
=============================================================================
"""

from typing import Dict, List, Any, Tuple, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FilterManager:
    """
    Manages filter configurations and WHERE clause generation
    Based on actual database schema
    """
    
    # Management groups based on actual codes
    MANAGEMENT_GROUPS = {
        'government': [1, 2, 3, 7],  # Dept of Education, Tribal, Local Body, Central
        'private_aided': [4],
        'private_unaided': [5],
        'others': [6, 8, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 102]
    }
    
    def __init__(self):
        """Initialize FilterManager"""
        logger.info("FilterManager initialized")
    
    def build_where_clause(
        self,
        filters: Dict[str, Any],
        table_alias: str = "sp1"
    ) -> Tuple[str, List[Any]]:
        """
        Build WHERE clause from filters
        
        Args:
            filters: Dictionary of filter conditions
            table_alias: Table alias for column references
            
        Returns:
            Tuple of (where_clause, params_list)
        """
        where_parts = []
        params = []
        
        # State filter (multi-select)
        if filters.get('state'):
            states = filters['state'] if isinstance(filters['state'], list) else [filters['state']]
            placeholders = ', '.join(['%s'] * len(states))
            where_parts.append(f"{table_alias}.state IN ({placeholders})")
            params.extend(states)
        
        # District filter (multi-select, cascading)
        if filters.get('district'):
            districts = filters['district'] if isinstance(filters['district'], list) else [filters['district']]
            placeholders = ', '.join(['%s'] * len(districts))
            where_parts.append(f"{table_alias}.district IN ({placeholders})")
            params.extend(districts)
        
        # Block filter (multi-select, cascading)
        if filters.get('block'):
            blocks = filters['block'] if isinstance(filters['block'], list) else [filters['block']]
            placeholders = ', '.join(['%s'] * len(blocks))
            where_parts.append(f"{table_alias}.block IN ({placeholders})")
            params.extend(blocks)
        
        # Rural/Urban filter
        if filters.get('rural_urban'):
            rural_urban = filters['rural_urban'] if isinstance(filters['rural_urban'], list) else [filters['rural_urban']]
            placeholders = ', '.join(['%s'] * len(rural_urban))
            where_parts.append(f"{table_alias}.rural_urban IN ({placeholders})")
            params.extend(rural_urban)
        
        # Management filter (using actual column name: managment)
        if filters.get('management'):
            management = filters['management'] if isinstance(filters['management'], list) else [filters['management']]
            placeholders = ', '.join(['%s'] * len(management))
            where_parts.append(f"{table_alias}.managment IN ({placeholders})")
            params.extend(management)
        
        # Management group filter
        if filters.get('management_group'):
            groups = filters['management_group'] if isinstance(filters['management_group'], list) else [filters['management_group']]
            all_codes = []
            for group in groups:
                all_codes.extend(self.MANAGEMENT_GROUPS.get(group, []))
            if all_codes:
                placeholders = ', '.join(['%s'] * len(all_codes))
                where_parts.append(f"{table_alias}.managment IN ({placeholders})")
                params.extend(all_codes)
        
        # School Category filter
        if filters.get('school_category'):
            categories = filters['school_category'] if isinstance(filters['school_category'], list) else [filters['school_category']]
            placeholders = ', '.join(['%s'] * len(categories))
            where_parts.append(f"{table_alias}.school_category IN ({placeholders})")
            params.extend(categories)
        
        # School Type filter (Boys/Girls/Co-ed)
        if filters.get('school_type'):
            types = filters['school_type'] if isinstance(filters['school_type'], list) else [filters['school_type']]
            placeholders = ', '.join(['%s'] * len(types))
            where_parts.append(f"{table_alias}.school_type IN ({placeholders})")
            params.extend(types)
        
        # Board Affiliation - Secondary
        if filters.get('aff_board_sec'):
            boards = filters['aff_board_sec'] if isinstance(filters['aff_board_sec'], list) else [filters['aff_board_sec']]
            placeholders = ', '.join(['%s'] * len(boards))
            where_parts.append(f"{table_alias}.aff_board_sec IN ({placeholders})")
            params.extend(boards)
        
        # Board Affiliation - Higher Secondary
        if filters.get('aff_board_hsec'):
            boards = filters['aff_board_hsec'] if isinstance(filters['aff_board_hsec'], list) else [filters['aff_board_hsec']]
            placeholders = ', '.join(['%s'] * len(boards))
            where_parts.append(f"{table_alias}.aff_board_hsec IN ({placeholders})")
            params.extend(boards)
        
        # Medium of Instruction
        if filters.get('medium_instr1'):
            mediums = filters['medium_instr1'] if isinstance(filters['medium_instr1'], list) else [filters['medium_instr1']]
            placeholders = ', '.join(['%s'] * len(mediums))
            where_parts.append(f"{table_alias}.medium_instr1 IN ({placeholders})")
            params.extend(mediums)
        
        # Shift School
        if filters.get('shift_school'):
            shifts = filters['shift_school'] if isinstance(filters['shift_school'], list) else [filters['shift_school']]
            placeholders = ', '.join(['%s'] * len(shifts))
            where_parts.append(f"{table_alias}.shift_school IN ({placeholders})")
            params.extend(shifts)
        
        # Minority School
        if filters.get('minority_school') is not None:
            where_parts.append(f"{table_alias}.minority_school = %s")
            params.append(filters['minority_school'])
        
        # Residential School
        if filters.get('resi_school'):
            resi = filters['resi_school'] if isinstance(filters['resi_school'], list) else [filters['resi_school']]
            placeholders = ', '.join(['%s'] * len(resi))
            where_parts.append(f"{table_alias}.resi_school IN ({placeholders})")
            params.extend(resi)
        
        # CWSN Special School
        if filters.get('special_school_for_cwsn') is not None:
            where_parts.append(f"{table_alias}.special_school_for_cwsn = %s")
            params.append(filters['special_school_for_cwsn'])
        
        # Pseudocode (school ID)
        if filters.get('pseudocode'):
            where_parts.append(f"{table_alias}.pseudocode = %s")
            params.append(filters['pseudocode'])
        
        # Pincode
        if filters.get('pincode'):
            where_parts.append(f"{table_alias}.pincode = %s")
            params.append(filters['pincode'])
        
        # Build final WHERE clause
        if where_parts:
            where_clause = " AND ".join(where_parts)
        else:
            where_clause = ""
        
        return where_clause, params
    
    def get_available_states(self, schema: str = "india_2024_25") -> List[str]:
        """Get list of available states"""
        # This would query the database, but for now return empty
        return []
    
    def get_districts_for_state(self, state: str, schema: str = "india_2024_25") -> List[str]:
        """Get list of districts for a state"""
        return []
    
    def get_blocks_for_district(self, state: str, district: str, schema: str = "india_2024_25") -> List[str]:
        """Get list of blocks for a district"""
        return []


# Convenience function
def build_filters(filters: Dict[str, Any], table_alias: str = "sp1") -> Tuple[str, List[Any]]:
    """Build WHERE clause from filters"""
    fm = FilterManager()
    return fm.build_where_clause(filters, table_alias)
