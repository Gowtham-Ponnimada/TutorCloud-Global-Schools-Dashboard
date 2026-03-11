"""
=============================================================================
TUTORCLOUD GLOBAL DASHBOARD - MAIN APPLICATION
=============================================================================
Entry point for the Dash application
=============================================================================
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from flask_caching import Cache

from config.settings import Settings
from utils.logger import setup_logger
from utils.database import DatabaseManager

# Initialize settings
settings = Settings()

# Setup logger
logger = setup_logger("tutorcloud.main")

# Initialize Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.FONT_AWESOME,
        dbc.icons.BOOTSTRAP,
    ],
    suppress_callback_exceptions=True,
    title=settings.APP_NAME,
    update_title="Loading...",
    meta_tags=[
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1.0, maximum-scale=1.0",
        },
        {
            "name": "description",
            "content": "Comprehensive K-12 education analytics platform",
        },
        {
            "property": "og:title",
            "content": "TutorCloud Global Education Dashboard",
        },
        {
            "property": "og:type",
            "content": "website",
        },
    ],
)

# Configure server
server = app.server
server.secret_key = settings.SECRET_KEY

# Setup caching
if settings.CACHE_ENABLED:
    cache_config = {
        "CACHE_TYPE": "redis" if settings.REDIS_ENABLED else "simple",
        "CACHE_DEFAULT_TIMEOUT": settings.CACHE_DEFAULT_TIMEOUT,
    }
    
    if settings.REDIS_ENABLED:
        cache_config.update({
            "CACHE_REDIS_HOST": settings.REDIS_HOST,
            "CACHE_REDIS_PORT": settings.REDIS_PORT,
            "CACHE_REDIS_DB": settings.REDIS_DB,
            "CACHE_REDIS_PASSWORD": settings.REDIS_PASSWORD,
        })
    
    cache = Cache(server, config=cache_config)
    logger.info(f"Cache initialized: {cache_config['CACHE_TYPE']}")
else:
    cache = None
    logger.warning("Caching is disabled")

# Initialize database manager
db_manager = DatabaseManager(settings)

# App layout will be defined in components/layout.py
from components.layout import create_layout
app.layout = create_layout()

# Register callbacks
from components.callbacks import register_callbacks
register_callbacks(app, db_manager, cache)

# Error handlers
@server.errorhandler(404)
def page_not_found(e):
    return html.Div([
        html.H1("404 - Page Not Found", className="text-danger"),
        html.P("The requested page could not be found."),
    ]), 404

@server.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return html.Div([
        html.H1("500 - Internal Server Error", className="text-danger"),
        html.P("An internal error occurred. Please try again later."),
    ]), 500

# Run application
if __name__ == "__main__":
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    
    app.run_server(
        host=settings.HOST,
        port=settings.PORT,
        debug=settings.DEBUG,
    )
