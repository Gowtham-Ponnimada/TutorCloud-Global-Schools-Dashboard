"""
=============================================================================
DATABASE MANAGER - TUTORCLOUD GLOBAL DASHBOARD
=============================================================================
Handles PostgreSQL database connections, query execution, and connection pooling
=============================================================================
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2 import pool, sql, extras
from psycopg2.extensions import connection as PgConnection, cursor as PgCursor

# Simple logger for now (will integrate with proper logger later)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database connection manager with connection pooling
    """
    
    def __init__(self, settings):
        """
        Initialize database manager with connection pool
        
        Args:
            settings: Settings object with database configuration
        """
        self.settings = settings
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Create connection pool"""
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=self.settings.DB_POOL_SIZE,
                host=self.settings.DB_HOST,
                port=self.settings.DB_PORT,
                database=self.settings.DB_NAME,
                user=self.settings.DB_USER,
                password=self.settings.DB_PASSWORD,
                options=f'-c search_path={self.settings.DB_SCHEMA},public'
            )
            logger.info(f"Database pool initialized: {self.settings.DB_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self) -> PgConnection:
        """
        Get database connection from pool (context manager)
        
        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
        
        Yields:
            psycopg2 connection object
        """
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=None) -> PgCursor:
        """
        Get database cursor (context manager)
        
        Args:
            cursor_factory: Optional cursor factory (e.g., RealDictCursor)
        
        Usage:
            with db.get_cursor() as cur:
                cur.execute("SELECT * FROM table")
                results = cur.fetchall()
        
        Yields:
            psycopg2 cursor object
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Tuple] = None,
        fetch: bool = True
    ) -> Optional[List[Tuple]]:
        """
        Execute a SQL query
        
        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)
            fetch: Whether to fetch results
        
        Returns:
            List of tuples (if fetch=True), None otherwise
        """
        with self.get_cursor() as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            return None
    
    def execute_dict_query(
        self, 
        query: str, 
        params: Optional[Tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query and return results as list of dictionaries
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            List of dictionaries with column names as keys
        """
        with self.get_cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    
    def fetch_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Tuple]:
        """
        Execute query and fetch single result
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            Single row as tuple, or None
        """
        with self.get_cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()
    
    def fetch_one_dict(
        self, 
        query: str, 
        params: Optional[Tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and fetch single result as dictionary
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            Single row as dictionary, or None
        """
        with self.get_cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None
    
    def fetch_all(self, query: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """
        Execute query and fetch all results
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            List of tuples
        """
        return self.execute_query(query, params, fetch=True)
    
    def fetch_all_dict(
        self, 
        query: str, 
        params: Optional[Tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query and fetch all results as dictionaries
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            List of dictionaries
        """
        return self.execute_dict_query(query, params)
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> None:
        """
        Execute query multiple times with different parameters
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        with self.get_cursor() as cur:
            cur.executemany(query, params_list)
    
    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """
        Check if table exists in database
        
        Args:
            table_name: Name of the table
            schema: Schema name (defaults to DB_SCHEMA from settings)
        
        Returns:
            True if table exists, False otherwise
        """
        schema = schema or self.settings.DB_SCHEMA
        query = """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = %s
            );
        """
        result = self.fetch_one(query, (schema, table_name))
        return result[0] if result else False
    
    def get_table_row_count(self, table_name: str, schema: Optional[str] = None) -> int:
        """
        Get row count for a table
        
        Args:
            table_name: Name of the table
            schema: Schema name (defaults to DB_SCHEMA from settings)
        
        Returns:
            Number of rows in the table
        """
        schema = schema or self.settings.DB_SCHEMA
        query = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table_name)
        )
        _conn = self.pool.getconn()
        try:
            result = self.fetch_one(query.as_string(_conn))
        finally:
            self.pool.putconn(_conn)  # PERF_FIX: return connection to pool
        return result[0] if result else 0
    
    def verify_schema(self, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify database schema and return status
        
        Args:
            schema_name: Schema to verify (defaults to settings.DB_SCHEMA if not provided)
        
        Returns:
            Dictionary with verification results
        """
        schema_to_verify = schema_name or self.settings.DB_SCHEMA
        results = {
            "schema_name": schema_to_verify,
            "schema_exists": False,
            "tables": {},
            "materialized_views": {},
            "total_rows": 0,
            "errors": []
        }
        
        try:
            # Check if schema exists
            schema_query = """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.schemata 
                    WHERE schema_name = %s
                );
            """
            schema_exists = self.fetch_one(schema_query, (schema_to_verify,))
            results["schema_exists"] = schema_exists[0] if schema_exists else False
            
            if not results["schema_exists"]:
                results["errors"].append(f"Schema '{schema_to_verify}' does not exist")
                return results
            
            # Check tables - DYNAMIC (accepts table list as parameter for multi-region)
            # For India schema (backward compatibility)
            expected_tables = [
                'school_profile_1',
                'enrollment_detail_1',
                'enrollment_detail_2',
                'teacher_data'
            ]
            
            for table in expected_tables:
                exists = self.table_exists(table, schema=schema_to_verify)
                row_count = 0
                if exists:
                    try:
                        row_count = self.get_table_row_count(table, schema=schema_to_verify)
                        results["total_rows"] += row_count
                    except Exception as e:
                        results["errors"].append(f"Error counting rows in {table}: {e}")
                
                results["tables"][table] = {
                    "exists": exists,
                    "rows": row_count
                }
            
            # Check materialized views - DYNAMIC
            mv_query = """
                SELECT matviewname, schemaname
                FROM pg_matviews
                WHERE schemaname = %s;
            """
            mvs = self.fetch_all(mv_query, (schema_to_verify,))
            
            # For India schema (backward compatibility)
            expected_mvs = ['mv_kpi_all_india', 'mv_kpi_state', 'mv_kpi_district']
            for mv_name in expected_mvs:
                exists = any(mv[0] == mv_name for mv in mvs)
                results["materialized_views"][mv_name] = {"exists": exists}
            
        except Exception as e:
            results["errors"].append(f"Verification error: {e}")
            logger.error(f"Schema verification failed: {e}")
        
        return results
    
    def execute_dataframe(
        self,
        query: str,
        params: Optional[Tuple] = None
    ):
        """
        Execute query and return results as pandas DataFrame
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            pandas DataFrame
        """
        import pandas as pd
        
        try:
            with self.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                logger.info(f"Query returned {len(df)} rows")
                return df
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def close(self):
        """Close all connections in the pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("Database pool closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function for quick database access
def get_database_manager(settings):
    """
    Get database manager instance
    
    Args:
        settings: Settings object
    
    Returns:
        DatabaseManager instance
    """
    return DatabaseManager(settings)
