"""
Filter Label Mappers for TutorCloud Global Dashboard

Maps database codes to human-readable labels.
Based on discovery output from critical_discovery.py
"""

from typing import Dict, List, Optional


# Management codes (21 types) - Based on discovery
MANAGEMENT_LABELS = {
    1: "Government",
    2: "Government (State)",
    3: "Government (Local Body)",
    4: "Aided",
    5: "Private Unaided",
    6: "Other",
    7: "Central Government",
    8: "Unrecognized",
    89: "Madrasa (Recognized)",
    90: "Madrasa (Unrecognized)",
    91: "Sanskrit School (Recognized)",
    92: "Sanskrit School (Unrecognized)",
    93: "Other (Recognized)",
    94: "Other (Unrecognized)",
    95: "Government Aided",
    96: "Partially Aided",
    97: "Private",
    98: "Central Government (Other)",
    99: "Other State Government",
    101: "State Board School",
    102: "Special School"
}

# Management groups for high-level analysis
MANAGEMENT_GROUPS = {
    'Government': [1, 2, 3, 7],
    'Private Aided': [4],
    'Private Unaided': [5],
    'Others': [6, 8, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 101, 102]
}

# Board codes - Secondary (aff_board_sec)
BOARD_SEC_LABELS = {
    0: "No Secondary Section",
    1: "CBSE",
    2: "State Board",
    3: "ICSE",
    4: "International Baccalaureate (IB)",
    5: "NIOS",
    6: "Cambridge",
    7: "State Open School",
    8: "CISCE",
    9: "Others"
}

# Board codes - Higher Secondary (aff_board_hsec)
BOARD_HSEC_LABELS = {
    0: "No Higher Secondary Section",
    1: "CBSE",
    2: "State Board",
    3: "ISC",
    4: "International Baccalaureate (IB)",
    5: "NIOS",
    6: "Cambridge",
    7: "State Open School",
    8: "CISCE",
    9: "Others"
}

# Medium of Instruction codes (20 languages)
MEDIUM_INSTR_LABELS = {
    0: "Not Specified",
    1: "Assamese",
    2: "Bengali",
    3: "Gujarati",
    4: "Hindi",
    5: "Kannada",
    8: "Malayalam",
    9: "Manipuri",
    10: "Marathi",
    12: "Oriya",
    13: "Punjabi",
    14: "Sanskrit",
    16: "Tamil",
    17: "Telugu",
    18: "Urdu",
    19: "English",
    20: "Nepali",
    23: "Arabic",
    24: "Persian",
    25: "Other"
}

# School Category codes (11 types)
SCHOOL_CATEGORY_LABELS = {
    1: "Primary Only (1-5)",
    2: "Primary with Upper Primary (1-8)",
    3: "Upper Primary Only (6-8)",
    4: "Primary to Secondary (1-10)",
    5: "Upper Primary to Secondary (6-10)",
    6: "Secondary Only (9-10)",
    7: "Higher Secondary (1-12)",
    8: "Upper Primary to Higher Secondary (6-12)",
    10: "Secondary to Higher Secondary (9-12)",
    11: "Higher Secondary Only (11-12)",
    12: "Pre-Primary to Higher Secondary"
}

# School Type codes (3 types)
SCHOOL_TYPE_LABELS = {
    1: "Boys Only",
    2: "Girls Only",
    3: "Co-educational"
}

# Rural/Urban codes
RURAL_URBAN_LABELS = {
    1: "Rural",
    2: "Urban"
}

# Shift School codes
SHIFT_SCHOOL_LABELS = {
    0: "No",
    1: "Morning Shift",
    2: "Afternoon Shift",
    3: "Double Shift"
}

# Yes/No codes (for binary features)
YES_NO_LABELS = {
    0: "No",
    1: "Yes"
}


class FilterLabelMapper:
    """
    Maps database codes to human-readable labels
    
    Features:
    - Code to label conversion
    - Label to code conversion
    - Multi-select label generation
    - Group labels (e.g., Management groups)
    """
    
    @staticmethod
    def get_management_label(code: int) -> str:
        """Get management type label from code"""
        return MANAGEMENT_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_management_group(code: int) -> str:
        """Get management group (Government, Private Aided, etc.)"""
        for group, codes in MANAGEMENT_GROUPS.items():
            if code in codes:
                return group
        return "Others"
    
    @staticmethod
    def get_board_sec_label(code: int) -> str:
        """Get secondary board label from code"""
        return BOARD_SEC_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_board_hsec_label(code: int) -> str:
        """Get higher secondary board label from code"""
        return BOARD_HSEC_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_medium_label(code: int) -> str:
        """Get medium of instruction label from code"""
        return MEDIUM_INSTR_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_school_category_label(code: int) -> str:
        """Get school category label from code"""
        return SCHOOL_CATEGORY_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_school_type_label(code: int) -> str:
        """Get school type label from code"""
        return SCHOOL_TYPE_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_rural_urban_label(code: int) -> str:
        """Get rural/urban label from code"""
        return RURAL_URBAN_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_shift_label(code: int) -> str:
        """Get shift school label from code"""
        return SHIFT_SCHOOL_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_yes_no_label(code: int) -> str:
        """Get yes/no label from code"""
        return YES_NO_LABELS.get(code, f"Unknown ({code})")
    
    @staticmethod
    def get_management_options() -> List[tuple]:
        """Get list of (code, label) tuples for management dropdown"""
        return [(code, label) for code, label in MANAGEMENT_LABELS.items()]
    
    @staticmethod
    def get_board_sec_options() -> List[tuple]:
        """Get list of (code, label) tuples for secondary board dropdown"""
        # Exclude 0 (No Secondary Section) from filter options
        return [(code, label) for code, label in BOARD_SEC_LABELS.items() if code != 0]
    
    @staticmethod
    def get_board_hsec_options() -> List[tuple]:
        """Get list of (code, label) tuples for higher secondary board dropdown"""
        # Exclude 0 (No Higher Secondary Section) from filter options
        return [(code, label) for code, label in BOARD_HSEC_LABELS.items() if code != 0]
    
    @staticmethod
    def get_medium_options() -> List[tuple]:
        """Get list of (code, label) tuples for medium dropdown"""
        # Exclude 0 (Not Specified) from filter options
        return [(code, label) for code, label in MEDIUM_INSTR_LABELS.items() if code != 0]
    
    @staticmethod
    def get_school_category_options() -> List[tuple]:
        """Get list of (code, label) tuples for school category dropdown"""
        return [(code, label) for code, label in SCHOOL_CATEGORY_LABELS.items()]
    
    @staticmethod
    def get_school_type_options() -> List[tuple]:
        """Get list of (code, label) tuples for school type dropdown"""
        return [(code, label) for code, label in SCHOOL_TYPE_LABELS.items()]
    
    @staticmethod
    def get_rural_urban_options() -> List[tuple]:
        """Get list of (code, label) tuples for rural/urban dropdown"""
        return [(code, label) for code, label in RURAL_URBAN_LABELS.items()]
    
    @staticmethod
    def labels_to_codes(labels: List[str], mapping: Dict[int, str]) -> List[int]:
        """
        Convert list of labels back to codes
        
        Args:
            labels: List of label strings
            mapping: Code-to-label mapping dict
        
        Returns:
            List of codes
        """
        # Create reverse mapping
        reverse_map = {label: code for code, label in mapping.items()}
        
        codes = []
        for label in labels:
            if label in reverse_map:
                codes.append(reverse_map[label])
        
        return codes


# Global mapper instance
label_mapper = FilterLabelMapper()
