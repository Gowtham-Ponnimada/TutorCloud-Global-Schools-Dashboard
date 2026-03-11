"""
Utils package for TutorCloud Global Dashboard

Core utility modules for caching, refresh, export, and helpers.
"""

from utils.cache_manager import cache_manager, CacheManager
from utils.refresh_manager import refresh_manager, RefreshManager
from utils.export_manager import export_manager, ExportManager
from utils.grade_helpers import (
    grade_calculator,
    GradeLevelCalculator,
    format_number,
    format_large_number,
    safe_divide,
    calculate_percentage,
    format_percentage,
    GRADE_LEVEL_COLUMNS
)
from utils.filter_labels import (
    label_mapper,
    FilterLabelMapper,
    MANAGEMENT_LABELS,
    MANAGEMENT_GROUPS,
    BOARD_SEC_LABELS,
    BOARD_HSEC_LABELS,
    MEDIUM_INSTR_LABELS,
    SCHOOL_CATEGORY_LABELS,
    SCHOOL_TYPE_LABELS,
    RURAL_URBAN_LABELS
)

__all__ = [
    # Managers
    'cache_manager',
    'CacheManager',
    'refresh_manager',
    'RefreshManager',
    'export_manager',
    'ExportManager',
    
    # Grade calculator
    'grade_calculator',
    'GradeLevelCalculator',
    'GRADE_LEVEL_COLUMNS',
    
    # Formatters
    'format_number',
    'format_large_number',
    'safe_divide',
    'calculate_percentage',
    'format_percentage',
    
    # Label mapper
    'label_mapper',
    'FilterLabelMapper',
    'MANAGEMENT_LABELS',
    'MANAGEMENT_GROUPS',
    'BOARD_SEC_LABELS',
    'BOARD_HSEC_LABELS',
    'MEDIUM_INSTR_LABELS',
    'SCHOOL_CATEGORY_LABELS',
    'SCHOOL_TYPE_LABELS',
    'RURAL_URBAN_LABELS'
]

# Region Manager
from utils.region_manager import RegionManager, get_region_manager, get_current_schema, get_region_config

__all__ = [
    'RegionManager',
    'get_region_manager', 
    'get_current_schema',
    'get_region_config',
]
