"""
=============================================================================
LOGGER CONFIGURATION - TUTORCLOUD GLOBAL DASHBOARD
=============================================================================
Configuration and initialization for the logging system
=============================================================================
"""

import os
from pathlib import Path
from typing import Optional

from src.utils.logger import TutorCloudLogger


class LogConfig:
    """
    Logger configuration manager
    """
    
    # Default configuration
    DEFAULT_LOG_DIR = 'logs'
    DEFAULT_LOG_LEVEL = 'INFO'
    DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
    DEFAULT_BACKUP_COUNT = 5
    DEFAULT_ENABLE_CONSOLE = True
    DEFAULT_ENABLE_JSON = False
    
    @classmethod
    def from_env(cls) -> dict:
        """
        Load logger configuration from environment variables
        
        Environment variables:
            LOG_DIR: Log directory path (default: 'logs')
            LOG_LEVEL: Logging level (default: 'INFO')
            LOG_MAX_BYTES: Maximum log file size in bytes (default: 10MB)
            LOG_BACKUP_COUNT: Number of backup files (default: 5)
            LOG_CONSOLE: Enable console output (default: True)
            LOG_JSON: Enable JSON formatting (default: False)
            
        Returns:
            Configuration dictionary
        """
        return {
            'log_dir': os.getenv('LOG_DIR', cls.DEFAULT_LOG_DIR),
            'log_level': os.getenv('LOG_LEVEL', cls.DEFAULT_LOG_LEVEL),
            'max_bytes': int(os.getenv('LOG_MAX_BYTES', cls.DEFAULT_MAX_BYTES)),
            'backup_count': int(os.getenv('LOG_BACKUP_COUNT', cls.DEFAULT_BACKUP_COUNT)),
            'enable_console': os.getenv('LOG_CONSOLE', str(cls.DEFAULT_ENABLE_CONSOLE)).lower() == 'true',
            'enable_json': os.getenv('LOG_JSON', str(cls.DEFAULT_ENABLE_JSON)).lower() == 'true',
        }
    
    @classmethod
    def from_settings(cls, settings) -> dict:
        """
        Load logger configuration from settings object
        
        Args:
            settings: Settings object
            
        Returns:
            Configuration dictionary
        """
        return {
            'log_dir': getattr(settings, 'LOG_DIR', cls.DEFAULT_LOG_DIR),
            'log_level': 'DEBUG' if getattr(settings, 'DEBUG', False) else cls.DEFAULT_LOG_LEVEL,
            'max_bytes': getattr(settings, 'LOG_MAX_BYTES', cls.DEFAULT_MAX_BYTES),
            'backup_count': getattr(settings, 'LOG_BACKUP_COUNT', cls.DEFAULT_BACKUP_COUNT),
            'enable_console': getattr(settings, 'LOG_CONSOLE', cls.DEFAULT_ENABLE_CONSOLE),
            'enable_json': getattr(settings, 'LOG_JSON', cls.DEFAULT_ENABLE_JSON),
        }
    
    @classmethod
    def initialize_logging(
        cls,
        settings=None,
        log_dir: Optional[str] = None,
        log_level: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize logging system with configuration
        
        Args:
            settings: Settings object (optional)
            log_dir: Override log directory
            log_level: Override log level
            **kwargs: Additional configuration options
            
        Example:
            # Initialize from settings
            LogConfig.initialize_logging(settings)
            
            # Initialize with overrides
            LogConfig.initialize_logging(
                log_dir='custom_logs',
                log_level='DEBUG'
            )
        """
        # Load configuration
        if settings:
            config = cls.from_settings(settings)
        else:
            config = cls.from_env()
        
        # Apply overrides
        if log_dir:
            config['log_dir'] = log_dir
        if log_level:
            config['log_level'] = log_level
        config.update(kwargs)
        
        # Initialize logger
        TutorCloudLogger.initialize(**config)


def setup_logging(settings=None):
    """
    Quick setup function for logging
    
    Args:
        settings: Settings object (optional)
        
    Example:
        from src.utils.log_config import setup_logging
        from src.config.settings import settings
        
        setup_logging(settings)
    """
    LogConfig.initialize_logging(settings)


def setup_development_logging():
    """
    Setup logging for development environment
    - DEBUG level
    - Console output enabled
    - JSON disabled for readability
    """
    TutorCloudLogger.initialize(
        log_dir='logs',
        log_level='DEBUG',
        enable_console=True,
        enable_json=False
    )


def setup_production_logging():
    """
    Setup logging for production environment
    - INFO level
    - Console output disabled
    - JSON enabled for parsing
    """
    TutorCloudLogger.initialize(
        log_dir='/var/log/tutorcloud',
        log_level='INFO',
        enable_console=False,
        enable_json=True
    )


def setup_testing_logging():
    """
    Setup logging for testing environment
    - WARNING level (less verbose)
    - Console output only
    """
    TutorCloudLogger.initialize(
        log_dir='logs/tests',
        log_level='WARNING',
        enable_console=True,
        enable_json=False,
        max_bytes=1 * 1024 * 1024,  # 1 MB
        backup_count=2
    )
