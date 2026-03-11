"""
=============================================================================
QUERY BUILDER V2 - TUTORCLOUD GLOBAL DASHBOARD
=============================================================================
Builds all SQL queries using ACTUAL schema
Column names based on schema discovery:
- Enrollment: c1_b, c1_g, c2_b, c2_g, etc.
- Teacher: total_tch
- Management: managment (typo in schema)
- MVs: actual column names from discovery
=============================================================================
"""

from typing import Dict, List, Tuple, Any, Optional
from src.utils.logger import get_logger
from src.utils.filters import FilterManager

logger = get_logger(__name__)


class QueryBuilderV2:
    """
    Build SQL queries based on actual database schema
    """
    
    def __init__(self, schema: str = "india_2024_25"):
        """Initialize QueryBuilderV2"""
        self.schema = schema
        self.filter_mgr = FilterManager()
        logger.info(f"QueryBuilderV2 initialized with schema: {schema}")
    
    # =========================================================================
    # HELPER: Calculate total enrollment
    # =========================================================================
    
    def _build_enrollment_sum(self, table_alias_ed1: str = "ed1", table_alias_ed2: str = "ed2") -> str:
        """
        Build SUM expression for total enrollment using actual column names
        
        Actual columns: cpp_b, cpp_g, c1_b, c1_g, c2_b, c2_g, ..., c12_b, c12_g
        """
        return f"""
            (COALESCE({table_alias_ed1}.cpp_b, 0) + COALESCE({table_alias_ed1}.cpp_g, 0) +
             COALESCE({table_alias_ed1}.c1_b, 0) + COALESCE({table_alias_ed1}.c1_g, 0) +
             COALESCE({table_alias_ed1}.c2_b, 0) + COALESCE({table_alias_ed1}.c2_g, 0) +
             COALESCE({table_alias_ed1}.c3_b, 0) + COALESCE({table_alias_ed1}.c3_g, 0) +
             COALESCE({table_alias_ed1}.c4_b, 0) + COALESCE({table_alias_ed1}.c4_g, 0) +
             COALESCE({table_alias_ed1}.c5_b, 0) + COALESCE({table_alias_ed1}.c5_g, 0) +
             COALESCE({table_alias_ed1}.c6_b, 0) + COALESCE({table_alias_ed1}.c6_g, 0) +
             COALESCE({table_alias_ed1}.c7_b, 0) + COALESCE({table_alias_ed1}.c7_g, 0) +
             COALESCE({table_alias_ed1}.c8_b, 0) + COALESCE({table_alias_ed1}.c8_g, 0) +
             COALESCE({table_alias_ed2}.c9_b, 0) + COALESCE({table_alias_ed2}.c9_g, 0) +
             COALESCE({table_alias_ed2}.c10_b, 0) + COALESCE({table_alias_ed2}.c10_g, 0) +
             COALESCE({table_alias_ed2}.c11_b, 0) + COALESCE({table_alias_ed2}.c11_g, 0) +
             COALESCE({table_alias_ed2}.c12_b, 0) + COALESCE({table_alias_ed2}.c12_g, 0))
        """
    
    # =========================================================================
    # MATERIALIZED VIEW QUERIES (Simple & Fast)
    # =========================================================================
    
    def get_national_summary(self) -> Tuple[str, List[Any]]:
        """Get national summary from materialized view"""
        query = f"""
            SELECT *
            FROM {self.schema}.mv_kpi_all_india;
        """
        return query, []
    
    def get_state_summary(self, filters: Dict[str, Any] = None) -> Tuple[str, List[Any]]:
        """Get state-level summary from materialized view"""
        filters = filters or {}
        
        where_clause, params = self.filter_mgr.build_where_clause(filters, table_alias="mv")
        
        query = f"""
            SELECT *
            FROM {self.schema}.mv_kpi_state mv
        """
        
        if where_clause:
            query += f"\n            WHERE {where_clause}"
        
        query += "\n            ORDER BY total_students DESC;"
        
        return query, params
    
    def get_district_summary(self, filters: Dict[str, Any] = None) -> Tuple[str, List[Any]]:
        """Get district-level summary from materialized view"""
        filters = filters or {}
        
        where_clause, params = self.filter_mgr.build_where_clause(filters, table_alias="mv")
        
        query = f"""
            SELECT *
            FROM {self.schema}.mv_kpi_district mv
        """
        
        if where_clause:
            query += f"\n            WHERE {where_clause}"
        
        query += "\n            ORDER BY state, district;"
        
        return query, params
    
    # =========================================================================
    # BLOCK-LEVEL QUERIES (Calculated)
    # =========================================================================
    
    def get_block_summary(self, filters: Dict[str, Any] = None) -> Tuple[str, List[Any]]:
        """Get block-level summary"""
        filters = filters or {}
        
        where_clause, params = self.filter_mgr.build_where_clause(filters, table_alias="sp1")
        
        enrollment_sum = self._build_enrollment_sum()
        
        query = f"""
            SELECT
                sp1.state,
                sp1.district,
                sp1.block,
                COUNT(DISTINCT sp1.pseudocode) as total_schools,
                SUM({enrollment_sum}) as total_students,
                SUM(COALESCE(td.total_tch, 0)) as total_teachers,
                CASE
                    WHEN SUM(COALESCE(td.total_tch, 0)) > 0 THEN
                        ROUND(SUM({enrollment_sum})::NUMERIC / SUM(COALESCE(td.total_tch, 0)), 2)
                    ELSE NULL
                END as pupil_teacher_ratio
            FROM {self.schema}.school_profile_1 sp1
            LEFT JOIN {self.schema}.enrollment_detail_1 ed1 ON sp1.pseudocode = ed1.pseudocode AND ed1.item_group = 1
            LEFT JOIN {self.schema}.enrollment_detail_2 ed2 ON sp1.pseudocode = ed2.pseudocode AND ed2.item_group = 1
            LEFT JOIN {self.schema}.teacher_data td ON sp1.pseudocode = td.pseudocode
        """
        
        if where_clause:
            query += f"\n            WHERE {where_clause}"
        
        query += """
            GROUP BY sp1.state, sp1.district, sp1.block
            ORDER BY sp1.state, sp1.district, sp1.block;
        """
        
        return query, params
    
    # =========================================================================
    # SCHOOL SEARCH
    # =========================================================================
    
    def search_schools(self, filters: Dict[str, Any] = None, limit: int = 100) -> Tuple[str, List[Any]]:
        """Search schools with filters"""
        filters = filters or {}
        
        where_clause, params = self.filter_mgr.build_where_clause(filters, table_alias="sp1")
        
        enrollment_sum = self._build_enrollment_sum()
        
        query = f"""
            SELECT
                sp1.pseudocode,
                sp1.state,
                sp1.district,
                sp1.block,
                sp1.lgd_vill_name as village_name,
                sp1.school_category,
                sp1.managment as management,
                sp1.school_type,
                sp1.rural_urban,
                sp1.aff_board_sec,
                sp1.aff_board_hsec,
                sp1.medium_instr1,
                
                SUM({enrollment_sum}) as total_students,
                COALESCE(td.total_tch, 0) as total_teachers,
                
                CASE
                    WHEN COALESCE(td.total_tch, 0) > 0 THEN
                        ROUND(SUM({enrollment_sum})::NUMERIC / COALESCE(td.total_tch, 1), 2)
                    ELSE NULL
                END as pupil_teacher_ratio
                
            FROM {self.schema}.school_profile_1 sp1
            LEFT JOIN {self.schema}.enrollment_detail_1 ed1 ON sp1.pseudocode = ed1.pseudocode AND ed1.item_group = 1
            LEFT JOIN {self.schema}.enrollment_detail_2 ed2 ON sp1.pseudocode = ed2.pseudocode AND ed2.item_group = 1
            LEFT JOIN {self.schema}.teacher_data td ON sp1.pseudocode = td.pseudocode
        """
        
        if where_clause:
            query += f"\n            WHERE {where_clause}"
        
        query += f"""
            GROUP BY sp1.pseudocode, sp1.state, sp1.district, sp1.block,
                     sp1.lgd_vill_name, sp1.school_category, sp1.managment,
                     sp1.school_type, sp1.rural_urban, sp1.aff_board_sec,
                     sp1.aff_board_hsec, sp1.medium_instr1, td.total_tch
            ORDER BY sp1.state, sp1.district, sp1.pseudocode
            LIMIT {limit};
        """
        
        return query, params
    
    # =========================================================================
    # COMPARISON QUERIES
    # =========================================================================
    
    def get_management_comparison(self, filters: Dict[str, Any] = None) -> Tuple[str, List[Any]]:
        """Compare Government vs Private schools"""
        filters = filters or {}
        
        where_clause, params = self.filter_mgr.build_where_clause(filters, table_alias="sp1")
        
        enrollment_sum = self._build_enrollment_sum()
        
        query = f"""
            SELECT
                CASE
                    WHEN sp1.managment IN (1, 2, 3, 7) THEN 'Government'
                    WHEN sp1.managment = 4 THEN 'Private Aided'
                    WHEN sp1.managment = 5 THEN 'Private Unaided'
                    ELSE 'Others'
                END as management_group,
                COUNT(DISTINCT sp1.pseudocode) as total_schools,
                SUM({enrollment_sum}) as total_students,
                SUM(COALESCE(td.total_tch, 0)) as total_teachers,
                CASE
                    WHEN SUM(COALESCE(td.total_tch, 0)) > 0 THEN
                        ROUND(SUM({enrollment_sum})::NUMERIC / SUM(COALESCE(td.total_tch, 0)), 2)
                    ELSE NULL
                END as avg_ptr
            FROM {self.schema}.school_profile_1 sp1
            LEFT JOIN {self.schema}.enrollment_detail_1 ed1 ON sp1.pseudocode = ed1.pseudocode AND ed1.item_group = 1
            LEFT JOIN {self.schema}.enrollment_detail_2 ed2 ON sp1.pseudocode = ed2.pseudocode AND ed2.item_group = 1
            LEFT JOIN {self.schema}.teacher_data td ON sp1.pseudocode = td.pseudocode
        """
        
        if where_clause:
            query += f"\n            WHERE {where_clause}"
        
        query += """
            GROUP BY management_group
            ORDER BY total_students DESC;
        """
        
        return query, params
    
    def get_rural_urban_comparison(self, filters: Dict[str, Any] = None) -> Tuple[str, List[Any]]:
        """Compare rural vs urban schools using materialized view (faster, no memory issues)"""
        filters = filters or {}
        
        # Use pre-aggregated MV instead of scanning 1.47M rows
        query = f"""
            SELECT
                'Rural' as area_type,
                rural_schools as total_schools,
                NULL as total_students,
                NULL as total_teachers,
                NULL as avg_ptr
            FROM {self.schema}.mv_kpi_all_india
            
            UNION ALL
            
            SELECT
                'Urban' as area_type,
                urban_schools as total_schools,
                NULL as total_students,
                NULL as total_teachers,
                NULL as avg_ptr
            FROM {self.schema}.mv_kpi_all_india
            
            ORDER BY total_schools DESC;
        """
        
        # No filters needed for national-level comparison
        return query, []
    
    # =========================================================================
    # PTR DISTRIBUTION
    # =========================================================================
    
    def get_ptr_distribution(self, filters: Dict[str, Any] = None) -> Tuple[str, List[Any]]:
        """Get PTR distribution by state"""
        filters = filters or {}
        
        where_clause, params = self.filter_mgr.build_where_clause(filters, table_alias="mv")
        
        query = f"""
            SELECT 
                state,
                pupil_teacher_ratio as ptr,
                total_schools,
                total_students,
                total_teachers
            FROM {self.schema}.mv_kpi_state mv
        """
        
        if where_clause:
            query += f"\n            WHERE {where_clause}"
        
        query += "\n            ORDER BY pupil_teacher_ratio DESC;"
        
        return query, params


# Convenience functions
def build_query(query_type: str, filters: Dict[str, Any] = None, **kwargs) -> Tuple[str, List[Any]]:
    """Build a query by type"""
    builder = QueryBuilderV2()
    
    if query_type == "national_summary":
        return builder.get_national_summary()
    elif query_type == "state_summary":
        return builder.get_state_summary(filters)
    elif query_type == "district_summary":
        return builder.get_district_summary(filters)
    elif query_type == "block_summary":
        return builder.get_block_summary(filters)
    elif query_type == "school_search":
        return builder.search_schools(filters, kwargs.get('limit', 100))
    elif query_type == "management_comparison":
        return builder.get_management_comparison(filters)
    elif query_type == "rural_urban_comparison":
        return builder.get_rural_urban_comparison(filters)
    elif query_type == "ptr_distribution":
        return builder.get_ptr_distribution(filters)
    else:
        raise ValueError(f"Unknown query type: {query_type}")
