# UAE Regional Dashboard – Setup Guide
## Overview
This README documents the required steps to create the UAE Regional Dashboard,
connecting to the same PostgreSQL instance as the India Global Dashboard.

## Prerequisites
- PostgreSQL running at localhost:5432 (Docker container: tutorcloud-postgres)
- Redis running (Docker container: tutorcloud-redis)
- Python venv at ~/tutorcloud/tutorcloud-global-dashboard/venv
- Streamlit running on port 8501

## Database Connection
Reuse the existing connection pool from code_mappings.py:
```python
from code_mappings import get_db_connection, release_db_connection, get_db_engine
```

## UAE-Specific DB Tables (to verify)
Run the following to check available UAE tables:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name ILIKE '%uae%'
ORDER BY table_name;
```

## New Page File
Create: pages/5_🇦🇪_UAE_Dashboard.py
Follow the same pattern as pages/2_📊_State_Dashboard.py

## Required Imports (UAE page)
```python
import streamlit as st
import pandas as pd
from code_mappings import get_db_connection, release_db_connection, get_db_engine
from ui_styles import apply_global_styles, COLORS
from ui_components import render_kpi_card, render_header
```

## Connection Pool Notes
- Pool: min=2, max=10 (defined in code_mappings.py)
- Always call release_db_connection(conn) after use
- Use get_db_engine() for pd.read_sql() calls (avoids SQLAlchemy warning)
- First connection ~14-20 ms; subsequent ~0 ms (pooled)

## UAE Dashboard Sections (Planned)
1. Emirates Overview – KPI cards by emirate
2. School Distribution – maps and charts
3. Grade Enrollment Analysis
4. Performance Metrics

## config/ YAML
Add UAE-specific config to config/ directory following existing YAML patterns.

## Checklist Before Launch
- [ ] UAE tables verified in PostgreSQL
- [ ] UAE page file created and tested
- [ ] Navigation entry in app.py updated
- [ ] Load time tested (<3 s first load, <1 s filter change)
