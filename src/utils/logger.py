"""
=============================================================================
LOGGER MODULE - TUTORCLOUD GLOBAL DASHBOARD
=============================================================================
Centralized logging system with rotation, monitoring, and structured output
=============================================================================
"""

import logging
import logging.handlers
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from functools import wraps
import time


class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        
        Args:
            record: LogRecord instance
            
        Returns:
            JSON formatted log string
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'duration'):
            log_data['duration_ms'] = record.duration
        if hasattr(record, 'query'):
            log_data['query'] = record.query
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Colored console formatter for better readability
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors
        
        Args:
            record: LogRecord instance
            
        Returns:
            Colored formatted log string
        """
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build log message
        log_msg = f"{timestamp} | {record.levelname:8s} | {record.name:20s} | {record.getMessage()}"
        
        # Add extra info if present
        if hasattr(record, 'duration'):
            log_msg += f" | ⏱️  {record.duration:.2f}ms"
        
        # Add exception info if present
        if record.exc_info:
            log_msg += f"\n{self.formatException(record.exc_info)}"
        
        return log_msg


class TutorCloudLogger:
    """
    Centralized logger for TutorCloud Dashboard
    """
    
    _instances: Dict[str, logging.Logger] = {}
    _initialized: bool = False
    
    @classmethod
    def initialize(
        cls,
        log_dir: str = 'logs',
        log_level: str = 'INFO',
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
        enable_console: bool = True,
        enable_json: bool = False
    ):
        """
        Initialize the logging system
        
        Args:
            log_dir: Directory for log files
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Maximum size per log file (bytes)
            backup_count: Number of backup files to keep
            enable_console: Enable console output
            enable_json: Enable JSON formatting for file logs
        """
        if cls._initialized:
            return
        
        # Create log directory
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Get log level
        level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler (colored)
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(ColoredConsoleFormatter())
            root_logger.addHandler(console_handler)
        
        # File handler - All logs (rotating)
        all_log_file = log_path / 'tutorcloud_all.log'
        all_handler = logging.handlers.RotatingFileHandler(
            all_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        all_handler.setLevel(level)
        
        if enable_json:
            all_handler.setFormatter(JsonFormatter())
        else:
            all_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        root_logger.addHandler(all_handler)
        
        # File handler - Error logs only (rotating)
        error_log_file = log_path / 'tutorcloud_error.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        if enable_json:
            error_handler.setFormatter(JsonFormatter())
        else:
            error_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s\n'
                    'File: %(pathname)s:%(lineno)d\n'
                    'Function: %(funcName)s\n'
                    '%(message)s\n',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        root_logger.addHandler(error_handler)
        
        # Time-based rotating handler - Daily logs
        daily_log_file = log_path / 'tutorcloud_daily.log'
        daily_handler = logging.handlers.TimedRotatingFileHandler(
            daily_log_file,
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding='utf-8'
        )
        daily_handler.setLevel(level)
        daily_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        root_logger.addHandler(daily_handler)
        
        cls._initialized = True
        
        # Log initialization
        init_logger = cls.get_logger('logger.init')
        init_logger.info(f"Logging system initialized")
        init_logger.info(f"Log directory: {log_path.absolute()}")
        init_logger.info(f"Log level: {log_level}")
        init_logger.info(f"Console output: {enable_console}")
        init_logger.info(f"JSON format: {enable_json}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create a logger instance
        
        Args:
            name: Logger name (typically module name)
            
        Returns:
            Logger instance
            
        Example:
            logger = TutorCloudLogger.get_logger(__name__)
            logger.info("Processing started")
        """
        if not cls._initialized:
            cls.initialize()
        
        if name not in cls._instances:
            cls._instances[name] = logging.getLogger(name)
        
        return cls._instances[name]


def log_execution_time(func):
    """
    Decorator to log function execution time
    
    Example:
        @log_execution_time
        def process_data():
            # ... processing logic
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = TutorCloudLogger.get_logger(func.__module__)
        
        start_time = time.time()
        logger.info(f"Starting: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000  # Convert to ms
            
            # Create a log record with duration
            logger.info(
                f"Completed: {func.__name__}",
                extra={'duration': duration}
            )
            
            return result
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(
                f"Failed: {func.__name__} - {str(e)}",
                exc_info=True,
                extra={'duration': duration}
            )
            raise
    
    return wrapper


def log_database_query(query: str, params: Optional[tuple] = None, duration: Optional[float] = None):
    """
    Log database query execution
    
    Args:
        query: SQL query string
        params: Query parameters
        duration: Execution time in milliseconds
        
    Example:
        log_database_query(
            "SELECT * FROM schools WHERE state = %s",
            ('KARNATAKA',),
            duration=45.23
        )
    """
    logger = TutorCloudLogger.get_logger('database.query')
    
    # Truncate long queries
    query_display = query[:200] + "..." if len(query) > 200 else query
    
    extra = {'query': query}
    if duration is not None:
        extra['duration'] = duration
    
    logger.debug(
        f"Query executed: {query_display}",
        extra=extra
    )


def log_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
):
    """
    Log API request
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint
        status_code: HTTP status code
        duration: Request duration in milliseconds
        user_id: User ID (optional)
        request_id: Request ID for tracing (optional)
        
    Example:
        log_api_request('GET', '/api/kpi/national', 200, 123.45, user_id='user123')
    """
    logger = TutorCloudLogger.get_logger('api.request')
    
    extra = {'duration': duration}
    if user_id:
        extra['user_id'] = user_id
    if request_id:
        extra['request_id'] = request_id
    
    logger.info(
        f"{method} {endpoint} - {status_code}",
        extra=extra
    )


# Convenience function
def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance (convenience function)
    
    Args:
        name: Logger name (uses caller's module name if not provided)
        
    Returns:
        Logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Hello, world!")
    """
    if name is None:
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get('__name__', 'unknown')
    
    return TutorCloudLogger.get_logger(name or 'tutorcloud')
