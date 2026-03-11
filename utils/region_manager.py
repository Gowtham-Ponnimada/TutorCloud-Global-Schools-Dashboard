"""
=============================================================================
REGION MANAGER - TUTORCLOUD GLOBAL DASHBOARD
=============================================================================
Manages multi-region configuration and dynamic schema selection
=============================================================================
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import streamlit as st

class RegionManager:
    """Manages region configurations and schema selection"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize RegionManager
        
        Args:
            config_path: Path to regions.yaml config file
        """
        if config_path is None:
            # Default to config/regions.yaml in project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "regions.yaml"
        
        self.config_path = Path(config_path)
        self.regions = {}
        self.load_config()
    
    def load_config(self):
        """Load regions configuration from YAML file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Region config not found: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config or 'regions' not in config:
                raise ValueError("Invalid regions.yaml: missing 'regions' key")
            
            # Store regions by ID for easy lookup
            for region in config['regions']:
                region_id = region.get('id')
                if region_id:
                    self.regions[region_id] = region
                    
        except Exception as e:
            print(f"Error loading region config: {e}")
            self.regions = {}
    
    def get_region_config(self, region_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific region by name
        
        Args:
            region_name: Display name of the region (e.g., 'India', 'USA')
        
        Returns:
            Region configuration dictionary or None
        """
        for region_id, region in self.regions.items():
            if region.get('name') == region_name:
                return region
        return None
    
    def get_region_by_id(self, region_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific region by ID
        
        Args:
            region_id: Region ID (e.g., 'india', 'usa')
        
        Returns:
            Region configuration dictionary or None
        """
        return self.regions.get(region_id)
    
    def get_enabled_regions(self) -> List[Dict[str, Any]]:
        """
        Get list of all enabled regions
        
        Returns:
            List of enabled region configurations
        """
        return [
            region for region in self.regions.values()
            if region.get('enabled', False)
        ]
    
    def get_current_schema(self) -> str:
        """
        Get the schema name for the currently selected region
        
        Returns:
            Schema name (e.g., 'india_2024_25')
        """
        # Get current region from Streamlit session state
        if hasattr(st, 'session_state') and 'current_region' in st.session_state:
            region_name = st.session_state['current_region']
            region_config = self.get_region_config(region_name)
            
            if region_config and 'database' in region_config:
                return region_config['database']['schema']
        
        # Fallback: return first enabled region's schema
        enabled = self.get_enabled_regions()
        if enabled and 'database' in enabled[0]:
            return enabled[0]['database']['schema']
        
        # Final fallback
        return 'india_2024_25'
    
    def get_region_schema(self, region_name: str) -> Optional[str]:
        """
        Get schema name for a specific region
        
        Args:
            region_name: Display name of the region
        
        Returns:
            Schema name or None
        """
        region = self.get_region_config(region_name)
        if region and 'database' in region:
            return region['database']['schema']
        return None
    
    def get_all_region_names(self) -> List[str]:
        """
        Get list of all region names
        
        Returns:
            List of region display names
        """
        return [region.get('name') for region in self.regions.values() if region.get('name')]
    
    def get_enabled_region_names(self) -> List[str]:
        """
        Get list of enabled region names
        
        Returns:
            List of enabled region display names
        """
        return [
            region.get('name') 
            for region in self.get_enabled_regions()
            if region.get('name')
        ]


# Global instance
_region_manager = None


def get_region_manager() -> RegionManager:
    """
    Get or create global RegionManager instance
    
    Returns:
        RegionManager singleton instance
    """
    global _region_manager
    if _region_manager is None:
        _region_manager = RegionManager()
    return _region_manager


def get_current_schema() -> str:
    """
    Convenience function to get current schema
    
    Returns:
        Current schema name
    """
    manager = get_region_manager()
    return manager.get_current_schema()


def get_region_config(region_name: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get region config
    
    Args:
        region_name: Display name of the region
    
    Returns:
        Region configuration dictionary or None
    """
    manager = get_region_manager()
    return manager.get_region_config(region_name)
