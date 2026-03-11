"""
=============================================================================
CONFIGURATION SETTINGS MANAGER
=============================================================================
Loads and validates configuration from environment variables and YAML files
=============================================================================
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Application settings loaded from environment and config files"""
    
    # -------------------------------------------------------------------------
    # APPLICATION SETTINGS
    # -------------------------------------------------------------------------
    APP_NAME: str = Field(default="TutorCloud Global Education Dashboard")
    APP_VERSION: str = Field(default="1.0.0")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production")
    
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8050)
    WORKERS: int = Field(default=4)
    
    # -------------------------------------------------------------------------
    # DATABASE SETTINGS
    # -------------------------------------------------------------------------
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="tutorcloud_db")
    DB_USER: str = Field(default="tutorcloud_admin")
    DB_PASSWORD: str = Field(default="")
    DB_SCHEMA: str = Field(default="india_2024_25")  # DEPRECATED: Use region_manager.get_current_schema() instead
    
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)
    DB_POOL_TIMEOUT: int = Field(default=30)
    DB_POOL_RECYCLE: int = Field(default=3600)
    DB_QUERY_TIMEOUT: int = Field(default=30)
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL"""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    # -------------------------------------------------------------------------
    # REDIS CACHE SETTINGS
    # -------------------------------------------------------------------------
    REDIS_ENABLED: bool = Field(default=False)
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: str = Field(default="")
    
    CACHE_ENABLED: bool = Field(default=True)
    CACHE_DEFAULT_TIMEOUT: int = Field(default=300)
    CACHE_MV_TIMEOUT: int = Field(default=3600)
    
    # -------------------------------------------------------------------------
    # LOGGING SETTINGS
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: Path = Field(default=LOGS_DIR / "tutorcloud.log")
    LOG_MAX_BYTES: int = Field(default=10485760)
    LOG_BACKUP_COUNT: int = Field(default=5)
    LOG_FORMAT: str = Field(default="json")
    
    @field_validator("LOG_FILE", mode="before")
    @classmethod
    def resolve_log_path(cls, v):
        """Ensure log file path is absolute"""
        if isinstance(v, str):
            return Path(v)
        return v
    
    # -------------------------------------------------------------------------
    # DASHBOARD SETTINGS - MULTI-REGION SUPPORT
    # -------------------------------------------------------------------------
    DEFAULT_REGION: str = Field(default="India")  # Default region on startup
    DEFAULT_ACADEMIC_YEAR: str = Field(default="2024-25")  # Fallback academic year
    
    # IMPORTANT: Always use region_manager.get_current_schema() for dynamic schema selection
    # DB_SCHEMA above is DEPRECATED for multi-region deployments
    
    MV_REFRESH_INTERVAL: int = Field(default=3600)
    METRICS_REFRESH_INTERVAL: int = Field(default=300)
    
    DEFAULT_PAGE_SIZE: int = Field(default=50)
    MAX_PAGE_SIZE: int = Field(default=1000)
    MAX_EXPORT_ROWS: int = Field(default=100000)
    
    # -------------------------------------------------------------------------
    # FEATURE FLAGS
    # -------------------------------------------------------------------------
    ENABLE_CACHING: bool = Field(default=True)
    ENABLE_EXPORT: bool = Field(default=True)
    ENABLE_MAPS: bool = Field(default=True)
    ENABLE_COMPARISON: bool = Field(default=True)
    ENABLE_ADVANCED_FILTERS: bool = Field(default=True)
    ENABLE_SCHOOL_SEARCH: bool = Field(default=True)
    
    # -------------------------------------------------------------------------
    # GEOSPATIAL SETTINGS
    # -------------------------------------------------------------------------
    GEOJSON_PATH: Path = Field(default=DATA_DIR / "geojson")
    ENABLE_DISTRICT_MAPS: bool = Field(default=True)
    ENABLE_BLOCK_MAPS: bool = Field(default=False)
    
    # -------------------------------------------------------------------------
    # SECURITY SETTINGS
    # -------------------------------------------------------------------------
    ENABLE_AUTH: bool = Field(default=False)
    JWT_SECRET_KEY: str = Field(default="")
    JWT_EXPIRY_HOURS: int = Field(default=24)
    ALLOWED_ORIGINS: str = Field(default="*")
    
    # -------------------------------------------------------------------------
    # MONITORING SETTINGS
    # -------------------------------------------------------------------------
    ENABLE_MONITORING: bool = Field(default=False)
    SENTRY_DSN: str = Field(default="")
    GOOGLE_ANALYTICS_ID: str = Field(default="")
    
    # -------------------------------------------------------------------------
    # MULTI-REGION SETTINGS
    # -------------------------------------------------------------------------
    REGIONS: str = Field(default="India,USA,Australia,New Zealand,UAE")
    DEFAULT_TIMEZONE: str = Field(default="Asia/Kolkata")
    
    @property
    def REGIONS_LIST(self) -> List[str]:
        """Parse regions as list"""
        return [r.strip() for r in self.REGIONS.split(",")]
    
    # -------------------------------------------------------------------------
    # API SETTINGS (Future)
    # -------------------------------------------------------------------------
    API_ENABLED: bool = Field(default=False)
    API_RATE_LIMIT: int = Field(default=100)
    API_KEY: str = Field(default="")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"
    
    # -------------------------------------------------------------------------
    # YAML CONFIGURATION LOADERS
    # -------------------------------------------------------------------------
    _app_config: Optional[Dict[str, Any]] = None
    _db_config: Optional[Dict[str, Any]] = None
    
    def load_app_config(self) -> Dict[str, Any]:
        """Load application configuration from YAML"""
        if self._app_config is None:
            config_path = CONFIG_DIR / "app.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    self._app_config = yaml.safe_load(f)
            else:
                self._app_config = {}
        return self._app_config
    
    def load_db_config(self) -> Dict[str, Any]:
        """Load database configuration from YAML"""
        if self._db_config is None:
            config_path = CONFIG_DIR / "database.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    self._db_config = yaml.safe_load(f)
            else:
                self._db_config = {}
        return self._db_config
    
    def get_region_config(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific region"""
        app_config = self.load_app_config()
        regions = app_config.get("regions", [])
        for region in regions:
            if region.get("id") == region_id:
                return region
        return None
    
    def get_enabled_regions(self) -> List[Dict[str, Any]]:
        """Get list of enabled regions"""
        app_config = self.load_app_config()
        regions = app_config.get("regions", [])
        return [r for r in regions if r.get("enabled", False)]


# Global settings instance
settings = Settings()
