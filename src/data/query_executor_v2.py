"""
Query Executor V2 - Simplified for actual schema
"""
import time
from typing import Dict, List, Any, Optional
import pandas as pd

from src.utils.database import DatabaseManager
from src.utils.logger import get_logger
from src.data.queries_v2 import QueryBuilderV2
from src.data.transformers import DataTransformer


class QueryExecutorV2:
    """Execute queries with logging and transformation"""
    
    def __init__(self, db_manager: DatabaseManager, schema: str = "india_2024_25"):
        self.db = db_manager
        self.schema = schema
        self.query_builder = QueryBuilderV2(schema=schema)
        self.transformer = DataTransformer()
        self.logger = get_logger("query_executor")
        
        self.logger.info("Query Executor initialized")
    
    def execute_query(
        self,
        query_name: str,
        filters: Optional[Dict] = None,
        transform: bool = True
    ) -> pd.DataFrame:
        """Execute a named query"""
        start_time = time.time()
        
        self.logger.info(f"Executing query: {query_name}")
        
        try:
            # Build query
            if query_name == "national_summary":
                query, params = self.query_builder.get_national_summary()
            elif query_name == "state_summary":
                query, params = self.query_builder.get_state_summary(filters or {})
            elif query_name == "district_summary":
                query, params = self.query_builder.get_district_summary(filters or {})
            elif query_name == "block_summary":
                query, params = self.query_builder.get_block_summary(filters or {})
            elif query_name == "school_search":
                query, params = self.query_builder.search_schools(filters or {})
            elif query_name == "management_comparison":
                query, params = self.query_builder.get_management_comparison(filters or {})
            elif query_name == "rural_urban_comparison":
                query, params = self.query_builder.get_rural_urban_comparison(filters or {})
            elif query_name == "ptr_distribution":
                query, params = self.query_builder.get_ptr_distribution(filters or {})
            else:
                raise ValueError(f"Unknown query: {query_name}")
            
            # Execute
            df = self.db.execute_dataframe(query, params)
            
            execution_time = (time.time() - start_time) * 1000
            self.logger.info(f"Query returned {len(df)} rows in {execution_time:.2f}ms")
            
            # Transform if requested
            if transform and len(df) > 0:
                df = self.transformer.apply_label_mapping(df)
            
            return df
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.logger.error(f"Query failed: {query_name} after {execution_time:.2f}ms - {str(e)}")
            raise
    
    def get_kpi_summary(
        self,
        level: str = "national",
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Get KPI summary"""
        query_map = {
            "national": "national_summary",
            "state": "state_summary",
            "district": "district_summary",
            "block": "block_summary"
        }
        
        query_name = query_map.get(level, "national_summary")
        df = self.execute_query(query_name, filters, transform=False)
        
        if len(df) == 0:
            return {}
        
        # Get aggregated row
        if level == "national":
            row = df.iloc[0]
        else:
            # Sum for filtered results
            row = df.sum(numeric_only=True)
        
        kpis = {
            "total_schools": int(row.get("total_schools", 0)),
            "total_students": int(row.get("total_students", 0)),
            "total_teachers": int(row.get("total_teachers", 0)),
        }
        
        # Calculate PTR
        if kpis["total_teachers"] > 0:
            kpis["ptr"] = round(kpis["total_students"] / kpis["total_teachers"], 2)
        else:
            kpis["ptr"] = None
        
        # Calculate girls percentage if available
        if "total_girls" in row and "total_students" in row:
            total_girls = int(row.get("total_girls", 0))
            if kpis["total_students"] > 0:
                kpis["girls_percentage"] = round((total_girls / kpis["total_students"]) * 100, 2)
        
        # Add formatted versions
        kpis["total_schools_formatted"] = f"{kpis['total_schools']:,}"
        kpis["total_students_formatted"] = f"{kpis['total_students']:,}"
        kpis["total_teachers_formatted"] = f"{kpis['total_teachers']:,}"
        kpis["ptr_formatted"] = f"{kpis['ptr']:.1f}" if kpis["ptr"] else "N/A"
        
        if "girls_percentage" in kpis:
            kpis["girls_percentage_formatted"] = f"{kpis['girls_percentage']:.1f}%"
        
        return kpis
