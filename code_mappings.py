"""
TutorCloud Global Dashboard - Code Mappings and Database Configuration
Version B.7 FINAL - VERIFIED with actual database schema
Schema: india_2024_25
Production Ready - 2026-02-11
Database columns VERIFIED via information_schema
"""

import psycopg2
from psycopg2 import pool as psycopg2_pool
import threading

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'tutorcloud_db',
    'user': 'tutorcloud_admin',
    'password': 'TutorCloud2024!Secure'
}

# ================================================================
# PooledConnection wrapper (Performance Optimization 2026-02-25)
# Transparently intercepts conn.close() → pool.putconn()
# All existing conn.cursor(), pd.read_sql(q, conn), conn.close()
# calls in every page continue to work with ZERO code changes.
# ================================================================
class _PooledConnection:
    """Proxy that returns connection to pool when close() is called."""
    __slots__ = ('_conn', '_pool')

    def __init__(self, conn, pool):
        object.__setattr__(self, '_conn', conn)
        object.__setattr__(self, '_pool', pool)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, '_conn'), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, '_conn'), name, value)

    def cursor(self, *args, **kwargs):
        return object.__getattribute__(self, '_conn').cursor(*args, **kwargs)

    def close(self):
        """Intercept close() — return to pool instead of destroying."""
        conn = object.__getattribute__(self, '_conn')
        pool = object.__getattribute__(self, '_pool')
        if pool is not None:
            try:
                pool.putconn(conn)
                return
            except Exception:
                pass
        try:
            conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ── Pool singleton (thread-safe) ──────────────────────────────
_pool_lock        = threading.Lock()
_connection_pool  = None

def _get_pool():
    """Return shared pool; create on first call (thread-safe)."""
    global _connection_pool
    with _pool_lock:
        if _connection_pool is None:
            try:
                _connection_pool = psycopg2_pool.ThreadedConnectionPool(
                    minconn=2, maxconn=10, **DB_CONFIG
                )
                print("✅ DB connection pool initialised (min=2, max=10)")
            except Exception as e:
                print(f"⚠️  Pool init failed: {e} — using direct connections")
                _connection_pool = None
    return _connection_pool

def get_db_connection():
    """
    Return a DB connection wrapped in _PooledConnection.
    • conn.close()       → returns to pool (not destroyed)
    • conn.cursor()      → delegates to real connection
    • pd.read_sql(q,conn)→ works via __getattr__ delegation
    Falls back to direct psycopg2.connect() if pool unavailable.
    """
    pool = _get_pool()
    if pool:
        try:
            raw = pool.getconn()
            return _PooledConnection(raw, pool)
        except Exception as e:
            print(f"⚠️  Pool.getconn failed: {e} — falling back to direct connect")
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return None


def release_db_connection(conn):
    """
    Return a pooled connection back to the pool.
    _PooledConnection.close() calls putconn() transparently,
    so conn.close() is equally valid.
    """
    if conn is None:
        return
    try:
        conn.close()   # _PooledConnection.close() → putconn()
    except Exception:
        pass

# ============================================================================
# SCHEMA AND TABLE NAMES
# ============================================================================

SCHEMA = 'india_2024_25'
TABLE_SCHOOL_PROFILE = 'school_profile_1'
TABLE_ENROLLMENT = 'enrollment_detail_1'
TABLE_ENROLLMENT_SECONDARY = 'enrollment_detail_2'
TABLE_TEACHER = 'teacher_data'

# Enrollment constants
ENROLLMENT_ITEM_GROUP_PRIMARY = 1  # For enrollment_detail_1
ENROLLMENT_ITEM_ID_PRIMARY = 1     # For enrollment_detail_1
ENROLLMENT_SECONDARY_ITEM_GROUP = 8  # For enrollment_detail_2

# ============================================================================
# COLUMN NAMES - VERIFIED FROM DATABASE
# ============================================================================
# Verified via: SELECT column_name FROM information_schema.columns 
#               WHERE table_schema='india_2024_25' AND table_name='school_profile_1'
# Date: 2026-02-11
# ============================================================================

# School Profile Columns (VERIFIED)
COL_PSEUDOCODE = 'pseudocode'
COL_STATE_NAME = 'state'              # ✅ VERIFIED EXISTS
COL_DISTRICT_NAME = 'district'        # ✅ VERIFIED EXISTS
COL_BLOCK_NAME = 'block'              # ✅ VERIFIED EXISTS
COL_SCHOOL_TYPE = 'school_type'       # ✅ VERIFIED EXISTS
COL_MANAGEMENT = 'managment'          # ✅ VERIFIED EXISTS (typo in DB)
COL_RURAL_URBAN = 'rural_urban'       # ✅ VERIFIED EXISTS

# Additional columns (to be used if needed - not yet verified)
COL_SCHOOL_NAME = 'schname'           # ⚠️  Not verified - placeholder
COL_BOARD = 'board'                   # ⚠️  Not verified - placeholder

# Enrollment Columns (Pre-Primary to Class 12)
COL_CPP_B = 'cpp_b'  # Pre-Primary Boys
COL_CPP_G = 'cpp_g'  # Pre-Primary Girls
COL_C1_B = 'c1_b'    # Class 1 Boys
COL_C1_G = 'c1_g'    # Class 1 Girls
COL_C2_B = 'c2_b'
COL_C2_G = 'c2_g'
COL_C3_B = 'c3_b'
COL_C3_G = 'c3_g'
COL_C4_B = 'c4_b'
COL_C4_G = 'c4_g'
COL_C5_B = 'c5_b'
COL_C5_G = 'c5_g'
COL_C6_B = 'c6_b'
COL_C6_G = 'c6_g'
COL_C7_B = 'c7_b'
COL_C7_G = 'c7_g'
COL_C8_B = 'c8_b'
COL_C8_G = 'c8_g'
COL_C9_B = 'c9_b'
COL_C9_G = 'c9_g'
COL_C10_B = 'c10_b'
COL_C10_G = 'c10_g'
COL_C11_B = 'c11_b'
COL_C11_G = 'c11_g'
COL_C12_B = 'c12_b'
COL_C12_G = 'c12_g'

# Teacher Columns
COL_TOTAL_TEACHERS = 'total_tch'

# ============================================================================
# CODE MAPPINGS
# ============================================================================

# School Type Mapping
SCHOOL_TYPE_MAP = {
    1: 'Primary Only (1-5)',
    2: 'Upper Primary Only (6-8)',
    3: 'Secondary/Sr. Secondary (9-12)',
    4: 'Primary with Upper Primary (1-8)',
    5: 'Upper Primary with Secondary (6-10)',
    6: 'Primary to Secondary (1-10)',
    7: 'Upper Primary with Sr. Secondary (6-12)',
    8: 'Primary to Sr. Secondary (1-12)',
    10: 'Pre-Primary Only',
    11: 'Pre-Primary with Primary (PP-5)',
    12: 'Pre-Primary with Upper Primary (PP-8)'
}

# Management Mapping
MANAGEMENT_MAP = {
    1: 'Department of Education',
    2: 'Tribal Welfare Department',
    3: 'Local Body',
    4: 'Private Aided',
    5: 'Private Unaided',
    6: 'Others',
    7: 'Central Government',
    89: 'Sainik School',
    90: 'Railway School',
    91: 'Central Tibetan School',
    92: 'Madarsa (Recognized)',
    93: 'Social Welfare Department',
    94: 'Ministry of Labour',
    95: 'Kendriya Vidyalaya',
    96: 'Jawahar Navodaya Vidyalaya',
    97: 'Other Central Govt. School',
    101: 'Madarsa (Unrecognized)',
    102: 'State Government'
}

# Board Mapping
BOARD_MAP = {
    0: 'Not Applicable',
    1: 'CBSE',
    2: 'State Board',
    3: 'ICSE',
    4: 'International Baccalaureate',
    5: 'NIOS',
    6: 'IGCSE',
    7: 'Others',
    8: 'Anglo Indian',
    9: 'Other International Board'
}

# Rural/Urban Mapping
RURAL_URBAN_MAP = {
    1: 'Rural',
    2: 'Urban'
}

# Grade Level Mapping
GRADE_LEVELS = {
    'cpp': 'Pre-Primary',
    'c1': 'Class 1',
    'c2': 'Class 2',
    'c3': 'Class 3',
    'c4': 'Class 4',
    'c5': 'Class 5',
    'c6': 'Class 6',
    'c7': 'Class 7',
    'c8': 'Class 8',
    'c9': 'Class 9',
    'c10': 'Class 10',
    'c11': 'Class 11',
    'c12': 'Class 12'
}

# ============================================================================
# REVERSE MAPPINGS (for lookups)
# ============================================================================

SCHOOL_TYPE_REVERSE = {v: k for k, v in SCHOOL_TYPE_MAP.items()}
MANAGEMENT_REVERSE = {v: k for k, v in MANAGEMENT_MAP.items()}
BOARD_REVERSE = {v: k for k, v in BOARD_MAP.items()}
RURAL_URBAN_REVERSE = {v: k for k, v in RURAL_URBAN_MAP.items()}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_ptr(ptr_value):
    """
    Format PTR value as 'X:1'
    Args:
        ptr_value: float or int PTR ratio
    Returns:
        Formatted string like '24:1' or 'N/A'
    """
    try:
        if ptr_value is None or ptr_value == 0:
            return 'N/A'
        return f"{int(round(ptr_value))}:1"
    except:
        return 'N/A'

def format_number(number):
    """
    Format large numbers with commas
    Args:
        number: int or float
    Returns:
        Formatted string like '1,234,567'
    """
    try:
        if number is None:
            return '0'
        return f"{int(number):,}"
    except:
        return '0'

def get_filter_options(mapping_dict):
    """
    Get list of filter options from a mapping dictionary
    Args:
        mapping_dict: Dictionary like SCHOOL_TYPE_MAP
    Returns:
        List of keys (codes) from the mapping
    """
    return list(mapping_dict.keys())

def get_label_from_code(code, mapping_dict):
    """
    Get label from code using mapping dictionary
    Args:
        code: int code value
        mapping_dict: Dictionary like SCHOOL_TYPE_MAP
    Returns:
        Label string or 'Unknown' if not found
    """
    return mapping_dict.get(code, 'Unknown')

# ============================================================================
# SQL QUERY TEMPLATES
# ============================================================================

# Enrollment sum template (all grades)
SQL_ENROLLMENT_SUM = """
COALESCE({col_prefix}.cpp_b, 0) + COALESCE({col_prefix}.cpp_g, 0) +
COALESCE({col_prefix}.c1_b, 0) + COALESCE({col_prefix}.c1_g, 0) +
COALESCE({col_prefix}.c2_b, 0) + COALESCE({col_prefix}.c2_g, 0) +
COALESCE({col_prefix}.c3_b, 0) + COALESCE({col_prefix}.c3_g, 0) +
COALESCE({col_prefix}.c4_b, 0) + COALESCE({col_prefix}.c4_g, 0) +
COALESCE({col_prefix}.c5_b, 0) + COALESCE({col_prefix}.c5_g, 0) +
COALESCE({col_prefix}.c6_b, 0) + COALESCE({col_prefix}.c6_g, 0) +
COALESCE({col_prefix}.c7_b, 0) + COALESCE({col_prefix}.c7_g, 0) +
COALESCE({col_prefix}.c8_b, 0) + COALESCE({col_prefix}.c8_g, 0) +
COALESCE({col_prefix}.c9_b, 0) + COALESCE({col_prefix}.c9_g, 0) +
COALESCE({col_prefix}.c10_b, 0) + COALESCE({col_prefix}.c10_g, 0) +
COALESCE({col_prefix}.c11_b, 0) + COALESCE({col_prefix}.c11_g, 0) +
COALESCE({col_prefix}.c12_b, 0) + COALESCE({col_prefix}.c12_g, 0)
"""

# Male students sum template
SQL_MALE_STUDENTS_SUM = """
COALESCE({col_prefix}.cpp_b, 0) +
COALESCE({col_prefix}.c1_b, 0) + COALESCE({col_prefix}.c2_b, 0) +
COALESCE({col_prefix}.c3_b, 0) + COALESCE({col_prefix}.c4_b, 0) +
COALESCE({col_prefix}.c5_b, 0) + COALESCE({col_prefix}.c6_b, 0) +
COALESCE({col_prefix}.c7_b, 0) + COALESCE({col_prefix}.c8_b, 0) +
COALESCE({col_prefix}.c9_b, 0) + COALESCE({col_prefix}.c10_b, 0) +
COALESCE({col_prefix}.c11_b, 0) + COALESCE({col_prefix}.c12_b, 0)
"""

# Female students sum template
SQL_FEMALE_STUDENTS_SUM = """
COALESCE({col_prefix}.cpp_g, 0) +
COALESCE({col_prefix}.c1_g, 0) + COALESCE({col_prefix}.c2_g, 0) +
COALESCE({col_prefix}.c3_g, 0) + COALESCE({col_prefix}.c4_g, 0) +
COALESCE({col_prefix}.c5_g, 0) + COALESCE({col_prefix}.c6_g, 0) +
COALESCE({col_prefix}.c7_g, 0) + COALESCE({col_prefix}.c8_g, 0) +
COALESCE({col_prefix}.c9_g, 0) + COALESCE({col_prefix}.c10_g, 0) +
COALESCE({col_prefix}.c11_g, 0) + COALESCE({col_prefix}.c12_g, 0)
"""

# ============================================================================
# FILTER CONDITIONS BUILDER
# ============================================================================

def build_filter_conditions(filters):
    """
    Build SQL WHERE clause and parameters from filters dictionary
    Args:
        filters: dict with keys like 'state', 'district', 'school_type', etc.
    Returns:
        Tuple of (where_clause, params_list)
    """
    conditions = []
    params = []
    
    if filters.get('state'):
        conditions.append(f"{COL_STATE_NAME} = %s")
        params.append(filters['state'])
    
    if filters.get('district') and filters['district'] != 'All':
        conditions.append(f"{COL_DISTRICT_NAME} = %s")
        params.append(filters['district'])
    
    if filters.get('block') and filters['block'] != 'All':
        conditions.append(f"{COL_BLOCK_NAME} = %s")
        params.append(filters['block'])
    
    if filters.get('school_type') and filters['school_type'] != 'All':
        conditions.append(f"{COL_SCHOOL_TYPE} = %s")
        params.append(filters['school_type'])
    
    if filters.get('management') and filters['management'] != 'All':
        conditions.append(f"{COL_MANAGEMENT} = %s")
        params.append(filters['management'])
    
    if filters.get('board') and filters['board'] != 'All':
        conditions.append(f"{COL_BOARD} = %s")
        params.append(filters['board'])
    
    if filters.get('location') and filters['location'] != 'All':
        conditions.append(f"{COL_RURAL_URBAN} = %s")
        params.append(filters['location'])
    
    where_clause = " AND " + " AND ".join(conditions) if conditions else ""
    
    return where_clause, params

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_state_name(state_name):
    """Validate state name exists"""
    if not state_name or len(state_name.strip()) == 0:
        return False
    return True

def validate_district_name(district_name):
    """Validate district name exists"""
    if not district_name or len(district_name.strip()) == 0:
        return False
    return True

# ============================================================================
# EXPORT LISTS (for star imports)
# ============================================================================

__all__ = [
    # Database
    'DB_CONFIG',
    'get_db_connection',
    
    # Schema/Tables
    'SCHEMA',
    'TABLE_SCHOOL_PROFILE',
    'TABLE_ENROLLMENT',
    'TABLE_ENROLLMENT_SECONDARY',
    'TABLE_TEACHER',
    
    # Constants
    'ENROLLMENT_ITEM_GROUP_PRIMARY',
    'ENROLLMENT_ITEM_ID_PRIMARY',
    'ENROLLMENT_SECONDARY_ITEM_GROUP',
    
    # Column Names
    'COL_PSEUDOCODE',
    'COL_STATE_NAME',
    'COL_DISTRICT_NAME',
    'COL_BLOCK_NAME',
    'COL_SCHOOL_NAME',
    'COL_SCHOOL_TYPE',
    'COL_MANAGEMENT',
    'COL_BOARD',
    'COL_RURAL_URBAN',
    'COL_TOTAL_TEACHERS',
    
    # Mappings
    'SCHOOL_TYPE_MAP',
    'MANAGEMENT_MAP',
    'BOARD_MAP',
    'RURAL_URBAN_MAP',
    'GRADE_LEVELS',
    
    # Reverse Mappings
    'SCHOOL_TYPE_REVERSE',
    'MANAGEMENT_REVERSE',
    'BOARD_REVERSE',
    'RURAL_URBAN_REVERSE',
    
    # Helper Functions
    'format_ptr',
    'format_number',
    'get_filter_options',
    'get_label_from_code',
    'build_filter_conditions',
    'validate_state_name',
    'validate_district_name',
    
    # SQL Templates
    'SQL_ENROLLMENT_SUM',
    'SQL_MALE_STUDENTS_SUM',
    'SQL_FEMALE_STUDENTS_SUM'
]


# ── SQLAlchemy engine (silences pandas DBAPI2 warning) ──────────────────
_db_engine = None
_engine_lock = threading.Lock()


def get_db_engine():
    """
    Return a module-level SQLAlchemy engine.
    Use:  df = pd.read_sql(sql, get_db_engine())
    This silences the psycopg2 DBAPI2 deprecation warning.
    """
    global _db_engine
    if _db_engine is None:
        with _engine_lock:
            if _db_engine is None:
                try:
                    from sqlalchemy import create_engine
                    url = "postgresql+psycopg2://tutorcloud_admin:TutorCloud2024!Secure@localhost:5432/tutorcloud_db"
                    _db_engine = create_engine(
                        url,
                        pool_size=5,
                        max_overflow=5,
                        pool_pre_ping=True,
                        echo=False
                    )
                    print("\u2705 SQLAlchemy engine initialised")
                except Exception as e:
                    print(f"\u26a0\ufe0f  SQLAlchemy engine failed: {e}")
                    return None
    return _db_engine
