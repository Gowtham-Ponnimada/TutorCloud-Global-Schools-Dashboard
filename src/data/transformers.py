"""
=============================================================================
DATA TRANSFORMERS - TUTORCLOUD GLOBAL DASHBOARD
=============================================================================
Transform raw database values into user-friendly formats
Calculations: PTR, percentages, growth rates, aggregations
Label mapping: Codes to human-readable names
=============================================================================
"""

from typing import Dict, List, Any, Optional, Union
from decimal import Decimal
import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataTransformer:
    """
    Transform raw database values into user-friendly formats
    """
    
    # Label mappings for various codes
    RURAL_URBAN_LABELS = {
        1: "Rural",
        2: "Urban",
        3: "Unknown"
    }
    
    MANAGEMENT_LABELS = {
        1: "Department of Education",
        2: "Tribal/Social Welfare Dept",
        3: "Local Body",
        4: "Private Aided",
        5: "Private Unaided",
        6: "Others",
        7: "Central Government",
        8: "Unrecognized",
        90: "Madarsa Recognized",
        91: "Madarsa Unrecognized"
    }
    
    MANAGEMENT_GROUPS = {
        1: "Government",
        2: "Government",
        3: "Government",
        4: "Private Aided",
        5: "Private Unaided",
        6: "Others",
        7: "Government",
        8: "Others",
        90: "Others",
        91: "Others"
    }
    
    BOARD_LABELS = {
        0: "Not Applicable",
        1: "CBSE",
        2: "State Board",
        3: "ICSE",
        4: "International Board",
        5: "NIOS",
        6: "Other State Board",
        7: "Madrasa Board",
        8: "Sanskrit Board",
        9: "Others"
    }
    
    MEDIUM_LABELS = {
        0: "Not Applicable",
        1: "English",
        2: "Hindi",
        3: "Urdu",
        4: "Telugu",
        5: "Bengali",
        6: "Marathi",
        7: "Tamil",
        8: "Gujarati",
        9: "Kannada",
        10: "Malayalam",
        11: "Odia",
        12: "Punjabi",
        13: "Assamese",
        14: "Sanskrit",
        15: "Kashmiri",
        16: "Nepali",
        17: "Sindhi",
        18: "Konkani",
        19: "Manipuri",
        20: "Bodo",
        21: "Dogri",
        22: "Maithili",
        23: "Santali",
        24: "Others"
    }
    
    SCHOOL_TYPE_LABELS = {
        1: "Boys Only",
        2: "Girls Only",
        3: "Co-educational"
    }
    
    SHIFT_LABELS = {
        1: "Morning",
        2: "Afternoon/Evening",
        3: "Both",
        9: "Unknown"
    }
    
    MINORITY_LABELS = {
        1: "Yes",
        2: "No"
    }
    
    RESIDENTIAL_LABELS = {
        0: "Not Applicable",
        1: "Fully Residential",
        2: "Partially Residential",
        3: "Day School"
    }
    
    CWSN_LABELS = {
        0: "Not Applicable",
        1: "Yes",
        2: "No"
    }
    
    SCHOOL_CATEGORY_LABELS = {
        1: "Primary Only (1-5)",
        2: "Upper Primary Only (6-8)",
        3: "Higher Secondary Only (9-12)",
        4: "Primary with Upper Primary (1-8)",
        5: "Primary with Upper Primary and Secondary/HSec (1-10/12)",
        6: "Upper Primary with Secondary/HSec (6-10/12)",
        7: "Secondary/HSec Only (9-10/12)",
        8: "Pre-Primary Only",
        9: "Pre-Primary with Primary",
        10: "Pre-Primary with Primary and Upper Primary (Pre-1-8)"
    }
    
    def __init__(self):
        """Initialize DataTransformer"""
        logger.info("DataTransformer initialized")
    
    # =========================================================================
    # CALCULATIONS
    # =========================================================================
    
    def calculate_ptr(
        self,
        students: Union[int, float, pd.Series],
        teachers: Union[int, float, pd.Series]
    ) -> Union[float, pd.Series]:
        """
        Calculate Pupil-Teacher Ratio (PTR)
        
        Args:
            students: Number of students
            teachers: Number of teachers
            
        Returns:
            PTR value(s)
        """
        if isinstance(students, pd.Series) and isinstance(teachers, pd.Series):
            # Handle division by zero
            return students.div(teachers.replace(0, pd.NA)).round(2)
        else:
            if teachers == 0 or teachers is None:
                return None
            return round(students / teachers, 2)
    
    def calculate_percentage(
        self,
        part: Union[int, float, pd.Series],
        total: Union[int, float, pd.Series]
    ) -> Union[float, pd.Series]:
        """
        Calculate percentage
        
        Args:
            part: Part value
            total: Total value
            
        Returns:
            Percentage value(s)
        """
        if isinstance(part, pd.Series) and isinstance(total, pd.Series):
            # Handle division by zero
            return (part.div(total.replace(0, pd.NA)) * 100).round(2)
        else:
            if total == 0 or total is None:
                return None
            return round((part / total) * 100, 2)
    
    def calculate_growth_rate(
        self,
        current: Union[int, float],
        previous: Union[int, float]
    ) -> Optional[float]:
        """
        Calculate growth rate percentage
        
        Args:
            current: Current value
            previous: Previous value
            
        Returns:
            Growth rate percentage
        """
        if previous == 0 or previous is None:
            return None
        return round(((current - previous) / previous) * 100, 2)
    
    # =========================================================================
    # LABEL MAPPING
    # =========================================================================
    
    def map_labels(
        self,
        values: Union[int, List[int], pd.Series],
        label_map: Dict[int, str],
        default: str = "Unknown"
    ) -> Union[str, List[str], pd.Series]:
        """
        Map numeric codes to labels
        
        Args:
            values: Code value(s)
            label_map: Mapping dictionary
            default: Default label for unknown codes
            
        Returns:
            Mapped label(s)
        """
        if isinstance(values, pd.Series):
            return values.map(label_map).fillna(default)
        elif isinstance(values, list):
            return [label_map.get(v, default) for v in values]
        else:
            return label_map.get(values, default)
    
    def apply_label_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all label mappings to a DataFrame
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with labels added
        """
        df = df.copy()
        
        # Rural/Urban
        if 'rural_urban' in df.columns:
            df['area_type'] = self.map_labels(df['rural_urban'], self.RURAL_URBAN_LABELS)
        
        # Management
        if 'managment' in df.columns:  # Note: typo in actual column name
            df['management_name'] = self.map_labels(df['managment'], self.MANAGEMENT_LABELS)
            df['management_group'] = self.map_labels(df['managment'], self.MANAGEMENT_GROUPS)
        
        # Board Affiliation
        if 'aff_board_sec' in df.columns:
            df['board_secondary'] = self.map_labels(df['aff_board_sec'], self.BOARD_LABELS)
        
        if 'aff_board_hsec' in df.columns:
            df['board_higher_secondary'] = self.map_labels(df['aff_board_hsec'], self.BOARD_LABELS)
        
        # Medium of Instruction
        if 'medium_instr1' in df.columns:
            df['medium_primary'] = self.map_labels(df['medium_instr1'], self.MEDIUM_LABELS)
        
        # School Type
        if 'school_type' in df.columns:
            df['school_type_name'] = self.map_labels(df['school_type'], self.SCHOOL_TYPE_LABELS)
        
        # School Category
        if 'school_category' in df.columns:
            df['category_name'] = self.map_labels(df['school_category'], self.SCHOOL_CATEGORY_LABELS)
        
        # Shift
        if 'shift_school' in df.columns:
            df['shift_type'] = self.map_labels(df['shift_school'], self.SHIFT_LABELS)
        
        # Minority
        if 'minority_school' in df.columns:
            df['minority_status'] = self.map_labels(df['minority_school'], self.MINORITY_LABELS)
        
        # Residential
        if 'resi_school' in df.columns:
            df['residential_type'] = self.map_labels(df['resi_school'], self.RESIDENTIAL_LABELS)
        
        # CWSN
        if 'special_school_for_cwsn' in df.columns:
            df['cwsn_school'] = self.map_labels(df['special_school_for_cwsn'], self.CWSN_LABELS)
        
        return df
    
    # =========================================================================
    # FORMATTING
    # =========================================================================
    
    def format_number(self, value: Union[int, float, None]) -> str:
        """
        Format number with commas
        
        Args:
            value: Number to format
            
        Returns:
            Formatted string
        """
        if value is None or pd.isna(value):
            return "N/A"
        
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return str(value)
    
    def format_percentage(self, value: Union[float, None], decimals: int = 2) -> str:
        """
        Format percentage value
        
        Args:
            value: Percentage value
            decimals: Number of decimal places
            
        Returns:
            Formatted string
        """
        if value is None or pd.isna(value):
            return "N/A"
        
        try:
            return f"{float(value):.{decimals}f}%"
        except (ValueError, TypeError):
            return str(value)
    
    def format_decimal(self, value: Union[float, None], decimals: int = 2) -> str:
        """
        Format decimal value
        
        Args:
            value: Decimal value
            decimals: Number of decimal places
            
        Returns:
            Formatted string
        """
        if value is None or pd.isna(value):
            return "N/A"
        
        try:
            return f"{float(value):.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)
    
    # =========================================================================
    # DATA TYPE CONVERSIONS
    # =========================================================================
    
    def to_numeric(
        self,
        value: Any,
        default: Optional[float] = None
    ) -> Optional[float]:
        """
        Convert value to numeric
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Numeric value or default
        """
        try:
            if isinstance(value, (int, float, Decimal)):
                return float(value)
            elif isinstance(value, str):
                return float(value.replace(',', ''))
            else:
                return default
        except (ValueError, TypeError, AttributeError):
            return default
    
    def to_integer(
        self,
        value: Any,
        default: Optional[int] = None
    ) -> Optional[int]:
        """
        Convert value to integer
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Integer value or default
        """
        numeric = self.to_numeric(value)
        if numeric is not None:
            return int(numeric)
        return default
    
    # =========================================================================
    # AGGREGATIONS
    # =========================================================================
    
    def aggregate_enrollment(
        self,
        df: pd.DataFrame,
        group_by: Union[str, List[str]]
    ) -> pd.DataFrame:
        """
        Aggregate enrollment data
        
        Args:
            df: Input DataFrame
            group_by: Column(s) to group by
            
        Returns:
            Aggregated DataFrame
        """
        agg_dict = {
            'boys': 'sum',
            'girls': 'sum',
            'total': 'sum'
        }
        
        # Add optional columns if they exist
        if 'sc_boys' in df.columns:
            agg_dict.update({
                'sc_boys': 'sum',
                'sc_girls': 'sum',
                'st_boys': 'sum',
                'st_girls': 'sum',
                'obc_boys': 'sum',
                'obc_girls': 'sum'
            })
        
        result = df.groupby(group_by).agg(agg_dict).reset_index()
        
        # Calculate percentages
        result['girls_percentage'] = self.calculate_percentage(
            result['girls'],
            result['total']
        )
        
        return result
    
    def aggregate_schools(
        self,
        df: pd.DataFrame,
        group_by: Union[str, List[str]]
    ) -> pd.DataFrame:
        """
        Aggregate school counts
        
        Args:
            df: Input DataFrame
            group_by: Column(s) to group by
            
        Returns:
            Aggregated DataFrame
        """
        return df.groupby(group_by).size().reset_index(name='school_count')


# Convenience functions
def calculate_ptr(students: int, teachers: int) -> Optional[float]:
    """Calculate PTR"""
    transformer = DataTransformer()
    return transformer.calculate_ptr(students, teachers)


def calculate_percentage(part: float, total: float) -> Optional[float]:
    """Calculate percentage"""
    transformer = DataTransformer()
    return transformer.calculate_percentage(part, total)


def format_number(value: Union[int, float]) -> str:
    """Format number with commas"""
    transformer = DataTransformer()
    return transformer.format_number(value)
