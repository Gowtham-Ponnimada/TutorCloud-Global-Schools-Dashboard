"""
Grade Level Utilities for TutorCloud Global Dashboard

Handles grade-level groupings, enrollment calculations, and PTR computations.
Based on discovered schema: c1_b, c1_g, c2_b, c2_g, etc.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging


# Grade level column mappings (based on schema discovery)
GRADE_LEVEL_COLUMNS = {
    'pre_primary': {
        'boys': ['cpp_b'],
        'girls': ['cpp_g'],
        'label': 'Pre-Primary (CPP-UKG)',
        'short_label': 'Pre-Primary'
    },
    'primary': {
        'boys': ['c1_b', 'c2_b', 'c3_b', 'c4_b', 'c5_b'],
        'girls': ['c1_g', 'c2_g', 'c3_g', 'c4_g', 'c5_g'],
        'label': 'Primary (Class 1-5)',
        'short_label': 'Primary'
    },
    'middle': {
        'boys': ['c6_b', 'c7_b', 'c8_b'],
        'girls': ['c6_g', 'c7_g', 'c8_g'],
        'label': 'Middle School (Class 6-8)',
        'short_label': 'Middle'
    },
    'high': {
        'boys': ['c9_b', 'c10_b', 'c11_b', 'c12_b'],
        'girls': ['c9_g', 'c10_g', 'c11_g', 'c12_g'],
        'label': 'High School (Class 9-12)',
        'short_label': 'High School'
    }
}


class GradeLevelCalculator:
    """
    Calculate enrollment and PTR at different grade levels
    
    Features:
    - Pre-Primary, Primary, Middle, High School groupings
    - Boys/Girls/Total enrollment
    - PTR calculations
    - Percentage distributions
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_enrollment_by_level(
        self,
        enrollment_data: pd.DataFrame,
        teacher_count: Optional[int] = None
    ) -> Dict[str, Dict[str, any]]:
        """
        Calculate enrollment by grade level
        
        Args:
            enrollment_data: DataFrame with enrollment columns (c1_b, c1_g, etc.)
            teacher_count: Total teachers (optional, for PTR calculation)
        
        Returns:
            Dict with structure:
            {
                'pre_primary': {'total': X, 'boys': Y, 'girls': Z, 'ptr': P},
                'primary': {...},
                'middle': {...},
                'high': {...}
            }
        """
        results = {}
        
        for level, columns in GRADE_LEVEL_COLUMNS.items():
            boys_cols = columns['boys']
            girls_cols = columns['girls']
            
            # Calculate totals
            boys_total = 0
            girls_total = 0
            
            for col in boys_cols:
                if col in enrollment_data.columns:
                    boys_total += enrollment_data[col].fillna(0).sum()
            
            for col in girls_cols:
                if col in enrollment_data.columns:
                    girls_total += enrollment_data[col].fillna(0).sum()
            
            total = boys_total + girls_total
            
            # Calculate PTR if teacher count provided
            ptr = None
            if teacher_count and teacher_count > 0 and total > 0:
                ptr = round(total / teacher_count, 1)
            
            results[level] = {
                'total': int(total),
                'boys': int(boys_total),
                'girls': int(girls_total),
                'ptr': ptr,
                'label': columns['label'],
                'short_label': columns['short_label']
            }
        
        return results
    
    def calculate_total_enrollment(self, enrollment_data: pd.DataFrame) -> Dict[str, int]:
        """
        Calculate total enrollment (all levels combined)
        
        Args:
            enrollment_data: DataFrame with enrollment columns
        
        Returns:
            Dict with total, boys, girls
        """
        all_boys_cols = []
        all_girls_cols = []
        
        for level, columns in GRADE_LEVEL_COLUMNS.items():
            all_boys_cols.extend(columns['boys'])
            all_girls_cols.extend(columns['girls'])
        
        boys_total = 0
        girls_total = 0
        
        for col in all_boys_cols:
            if col in enrollment_data.columns:
                boys_total += enrollment_data[col].fillna(0).sum()
        
        for col in all_girls_cols:
            if col in enrollment_data.columns:
                girls_total += enrollment_data[col].fillna(0).sum()
        
        return {
            'total': int(boys_total + girls_total),
            'boys': int(boys_total),
            'girls': int(girls_total)
        }
    
    def calculate_ptr(self, students: int, teachers: int) -> Optional[float]:
        """
        Calculate Pupil-Teacher Ratio
        
        Args:
            students: Number of students
            teachers: Number of teachers
        
        Returns:
            PTR as float or None if invalid
        """
        if teachers > 0 and students >= 0:
            return round(students / teachers, 1)
        return None
    
    def get_grade_level_labels(self) -> List[str]:
        """Get list of grade level labels in order"""
        return [
            GRADE_LEVEL_COLUMNS['pre_primary']['label'],
            GRADE_LEVEL_COLUMNS['primary']['label'],
            GRADE_LEVEL_COLUMNS['middle']['label'],
            GRADE_LEVEL_COLUMNS['high']['label']
        ]
    
    def get_grade_level_short_labels(self) -> List[str]:
        """Get list of short grade level labels"""
        return [
            GRADE_LEVEL_COLUMNS['pre_primary']['short_label'],
            GRADE_LEVEL_COLUMNS['primary']['short_label'],
            GRADE_LEVEL_COLUMNS['middle']['short_label'],
            GRADE_LEVEL_COLUMNS['high']['short_label']
        ]


def format_number(num: any, precision: int = 0) -> str:
    """
    Format number with Indian numbering system (Lakhs, Crores)
    
    Args:
        num: Number to format
        precision: Decimal places for large numbers
    
    Returns:
        Formatted string (e.g., "1.47M", "24.5", "1.2K")
    """
    try:
        num = float(num)
    except (ValueError, TypeError):
        return "N/A"
    
    if num >= 10000000:  # 1 Crore = 10 Million
        return f"{num / 10000000:.{precision}f}Cr"
    elif num >= 100000:  # 1 Lakh = 100 Thousand
        return f"{num / 100000:.{precision}f}L"
    elif num >= 1000000:  # 1 Million
        return f"{num / 1000000:.{precision}f}M"
    elif num >= 1000:
        return f"{num / 1000:.{precision}f}K"
    elif precision > 0:
        return f"{num:.{precision}f}"
    else:
        return f"{int(num):,}"


def format_large_number(num: any, short: bool = False) -> str:
    """
    Format large numbers with commas or short notation
    
    Args:
        num: Number to format
        short: If True, use K/M/Cr notation
    
    Returns:
        Formatted string
    """
    try:
        num = float(num)
    except (ValueError, TypeError):
        return "N/A"
    
    if short:
        return format_number(num, precision=1)
    else:
        return f"{int(num):,}"


def safe_divide(numerator: any, denominator: any, default: any = None) -> Optional[float]:
    """
    Safely divide two numbers
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value if division fails
    
    Returns:
        Result or default value
    """
    try:
        num = float(numerator)
        den = float(denominator)
        if den == 0:
            return default
        return num / den
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def calculate_percentage(part: any, total: any, precision: int = 1) -> Optional[float]:
    """
    Calculate percentage safely
    
    Args:
        part: Part value
        total: Total value
        precision: Decimal places
    
    Returns:
        Percentage or None
    """
    result = safe_divide(part, total)
    if result is not None:
        return round(result * 100, precision)
    return None


def format_percentage(value: any, precision: int = 1) -> str:
    """
    Format percentage value
    
    Args:
        value: Percentage value (0-100)
        precision: Decimal places
    
    Returns:
        Formatted string with % symbol
    """
    try:
        val = float(value)
        return f"{val:.{precision}f}%"
    except (ValueError, TypeError):
        return "N/A"


# Global calculator instance
grade_calculator = GradeLevelCalculator()
